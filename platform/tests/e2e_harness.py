# Nothing existing: glue that starts this folder's receiver and the pinned Nextflow together; Nextflow's own test setups know nothing of our receiver.
"""Harness for the end-to-end tests (feature 008): a receiver in a thread, and real Nextflow runs."""
import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from helpers import FIXTURES, PLATFORM_DIR, free_port, pkg_env, run_cli

FLOWS = FIXTURES / "flows"


class Recorder:
    """ASGI wrapper that keeps the raw bodies the receiver was sent."""

    def __init__(self, app):
        self.app = app
        self.requests = []  # (method, path, parsed body or None)
        self.lock = threading.Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT"):
            return await self.app(scope, receive, send)
        chunks = []

        async def tap():
            msg = await receive()
            if msg["type"] == "http.request":
                chunks.append(msg.get("body", b""))
            return msg

        try:
            return await self.app(scope, tap, send)
        finally:
            raw = b"".join(chunks)
            try:
                body = json.loads(raw) if raw else None
            except ValueError:
                body = None
            with self.lock:
                self.requests.append((scope["method"], scope["path"], body, raw))

    def of_kind(self, kind):
        with self.lock:
            return [r for r in self.requests if r[1].rstrip("/").endswith("/" + kind)]


class Env:
    """A receiver on a free local port, its files, and a way to run Nextflow against it."""

    def __init__(self, cfg, tmp_path, clock=None):
        import uvicorn
        from abf_platform import receiver, store

        self.cfg = cfg
        self.dir = Path(tmp_path)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index = self.dir / "data" / "index.db"
        self.tokens = self.dir / "data" / "tokens.db"
        self.index.parent.mkdir(parents=True, exist_ok=True)
        self.token = store.create_token(self.tokens)
        self.recorder = Recorder(receiver.create_app(self.index, self.tokens, clock=clock or time.time))
        self.port = free_port()
        self.url = "http://127.0.0.1:%d" % self.port
        config = uvicorn.Config(self.recorder, host="127.0.0.1", port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        end = time.time() + 30
        while not self.server.started and time.time() < end:
            time.sleep(0.05)
        assert self.server.started, "receiver did not start"

    def stop(self):
        self.server.should_exit = True
        self.thread.join(timeout=20)

    # --- running Nextflow ---------------------------------------------------------
    def nf_env(self, token=None, extra=None):
        # PATH without any 'tw' (TC-051): the runs must work without Seqera's command line tool.
        keep = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d and not os.access(os.path.join(d, "tw"), os.X_OK)]
        env = dict(os.environ)
        for k in list(env):
            if k.startswith(("NXF_", "TOWER_", "ABF_")):
                del env[k]
        env.update({
            "PATH": os.pathsep.join(keep),
            "NXF_HOME": self.cfg["home"],
            "NXF_VER": self.cfg["ver"],
            "NXF_OFFLINE": "true",
            "NXF_ANSI_LOG": "false",
            "NXF_DISABLE_CHECK_LATEST": "true",
            "TOWER_ACCESS_TOKEN": token or self.token,
        })
        env.update(extra or {})
        return env

    def nf_cmd(self, pipeline, args=(), endpoint=None):
        endpoint = endpoint or self.url
        host = urlparse(endpoint).hostname
        assert host in ("127.0.0.1", "localhost", "::1"), "tower.endpoint must be local: " + endpoint
        return ["bash", self.cfg["launcher"], "run", str(FLOWS / pipeline / "main.nf"),
                "-with-tower", endpoint, "-with-trace"] + list(args)

    def run_nf(self, pipeline, launch_dir, args=(), token=None, extra_env=None, timeout=240):
        Path(launch_dir).mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        p = subprocess.run(self.nf_cmd(pipeline, args), cwd=str(launch_dir), env=self.nf_env(token, extra_env),
                           capture_output=True, text=True, timeout=timeout)
        p.t0, p.t1 = t0, time.time()
        p.run_name = run_name_of(p.stdout)
        return p

    def start_nf(self, pipeline, launch_dir, args=(), token=None, extra_env=None):
        Path(launch_dir).mkdir(parents=True, exist_ok=True)
        log = open(Path(launch_dir) / "nf-stdout.txt", "w")
        proc = subprocess.Popen(self.nf_cmd(pipeline, args), cwd=str(launch_dir), env=self.nf_env(token, extra_env),
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        proc._log = log
        return proc

    # --- what Nextflow itself recorded ------------------------------------------------
    def cli_env(self, **extra):
        return pkg_env(ABF_PLATFORM_DB=self.index, ABF_PLATFORM_TOKENS=self.tokens, **extra)


def run_name_of(stdout):
    m = re.search(r"Launching `[^`]*` \[([a-z0-9_]+)\]", stdout)
    return m.group(1) if m else None


def history(launch_dir):
    rows = []
    path = Path(launch_dir) / ".nextflow" / "history"
    for line in path.read_text().splitlines():
        parts = line.split("\t")
        if len(parts) >= 6:
            rows.append({"start": parts[0], "duration": parts[1], "run_name": parts[2], "status": parts[3],
                         "session": parts[5]})
    return rows


def trace_files(launch_dir):
    return sorted(Path(launch_dir).glob("trace-*.txt"), key=lambda p: p.stat().st_mtime)


def trace_rows(path):
    lines = Path(path).read_text().splitlines()
    head = lines[0].split("\t")
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:] if ln.strip()]


def trace_counts(rows):
    c = {"total": len(rows), "succeeded": 0, "cached": 0, "failed": 0, "aborted": 0}
    for r in rows:
        key = {"COMPLETED": "succeeded", "CACHED": "cached", "FAILED": "failed", "ABORTED": "aborted"}.get(r["status"])
        if key:
            c[key] += 1
    return c


def trace_by_process(rows):
    out = {}
    for r in rows:
        proc = r["name"].split(" ", 1)[0]
        c = out.setdefault(proc, {"total": 0, "succeeded": 0, "cached": 0, "failed": 0, "aborted": 0})
        c["total"] += 1
        key = {"COMPLETED": "succeeded", "CACHED": "cached", "FAILED": "failed", "ABORTED": "aborted"}.get(r["status"])
        if key:
            c[key] += 1
    return out


def wait_until(fn, timeout=60, step=0.2, what="condition"):
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(step)
    raise AssertionError("timed out waiting for " + what)
