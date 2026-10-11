# Not Seqera's own capture tooling or Nextflow's test mocks: they are not part of what a clone of this repository has; this is the 40-line recorder that made the nf2510_*.json files, kept so they can be made again.
"""Record what Nextflow 25.10.4 (nf-tower 1.17.5) sends to a tower endpoint (feature 007b, FR-007).

    ABF_NXF2_LAUNCHER=... ABF_NXF2_HOME=... ABF_NXF2_VER=25.10.4 python record_payloads.py <out folder>

The three variables are what tests/platform_test.sh exports for the second pinned pair. The script starts a
throw-away HTTP server on 127.0.0.1 that answers like the receiver does, runs the fixture flows in
platform/tests/fixtures/flows/ against it, and writes one JSON file per scenario in the same shape as the 008
recordings (payloads/*.json), with one more field per request: received_at, the seconds since the first request.
Nothing leaves the machine and nothing talks to Seqera. Personal values (user name, host name, home, checkout and
cache paths, every /work/ path segment, the workflow id) are replaced before anything is written.

Scenarios: nf2510_ok, nf2510_resume (the same pipeline again with -resume, so tasks are cached), nf2510_fail
(a task exits 1, errorReport), nf2510_retry (a task fails once and succeeds on its second attempt, another fails
for good), and nf2510_long_timing (a run of more than four minutes: only the kind and the time of each message
are kept, because a four-minute run sends hundreds of progress messages).
"""
import getpass
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOWS = HERE / "flows"
REPO = HERE.parents[2]
TOKEN = "capturetoken123"
ID = "0123456789abcdef"


class Capture:
    def __init__(self):
        self.requests = []
        self.t0 = None
        self.lock = threading.Lock()
        cap = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _do(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b""
                now = time.time()
                body = None
                if raw:
                    try:
                        body = json.loads(raw)
                    except ValueError:
                        body = None
                with cap.lock:
                    if cap.t0 is None:
                        cap.t0 = now
                    cap.requests.append({"method": self.command, "path": self.path, "body": body,
                                         "received_at": round(now - cap.t0, 3), "auth": self.headers.get("Authorization")})
                if self.path.startswith("/trace/create"):
                    out = {"workflowId": ID}
                elif self.path.startswith("/user-info"):
                    out = {"user": {"id": 1, "userName": "capture"}}
                else:
                    out = {"status": "OK"}
                data = json.dumps(out).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PUT = _do

        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()


def run_flow(flow, launch_dir, port, args=(), cfg=None):
    launch_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for k in list(env):
        if k.startswith(("NXF_", "TOWER_")):
            del env[k]
    env.update({"NXF_HOME": cfg["home"], "NXF_VER": cfg["ver"], "NXF_OFFLINE": "true", "NXF_ANSI_LOG": "false",
                "NXF_DISABLE_CHECK_LATEST": "true", "TOWER_ACCESS_TOKEN": TOKEN})
    cmd = ["bash", cfg["launcher"], "run", str(FLOWS / flow / "main.nf"), "-with-tower", "http://127.0.0.1:%d" % port,
           "-with-trace"] + list(args)
    return subprocess.run(cmd, cwd=str(launch_dir), env=env, capture_output=True, text=True, timeout=900)


def sanitizer(launch_dirs, cache_dir):
    pairs = [(str(d), "/LAUNCH") for d in launch_dirs]
    pairs += [(str(FLOWS), "/REPO/platform/tests/fixtures/flows"), (str(REPO), "/REPO"), (str(cache_dir), "/CACHE"),
              (str(Path.home()), "~"), (socket.gethostname(), "host1")]

    def clean(text):
        for old, new in pairs:
            if old:
                text = text.replace(old, new)
        text = text.replace(getpass.getuser(), "labuser")
        text = re.sub(r"/work/", "/wk/", text)
        text = text.replace(ID, "{id}")
        return text
    return clean


_STATUS = {"COMPLETED": "succeeded", "CACHED": "cached", "FAILED": "failed", "ABORTED": "aborted"}


def expected_from_trace(trace_path):
    """What the run's own trace says: counts per process, in total, and the tasks that failed (the tests' expectation)."""
    lines = Path(trace_path).read_text().splitlines()
    head = lines[0].split("\t")
    rows = [dict(zip(head, ln.split("\t"))) for ln in lines[1:] if ln.strip()]

    def empty():
        return {"total": 0, "succeeded": 0, "cached": 0, "failed": 0, "aborted": 0}

    total, procs, failed = empty(), {}, []
    for r in rows:
        proc = r["name"].split(" ", 1)[0]
        for c in (total, procs.setdefault(proc, empty())):
            c["total"] += 1
            key = _STATUS.get(r["status"])
            if key:
                c[key] += 1
        if r["status"] == "FAILED":
            failed.append({"name": r["name"], "exit": int(r["exit"]), "attempt": r.get("attempt")})
    return {"tasks": total, "processes": procs, "failed_tasks": failed}


def dump(name, header, requests, clean, out, keep_bodies=True):
    rows = []
    for r in requests:
        row = {"method": r["method"], "path": clean(r["path"]), "received_at": r["received_at"]}
        if keep_bodies:
            row["body"] = json.loads(clean(json.dumps(r["body"])))
        else:
            row["kind"] = r["path"].rstrip("/").split("/")[-1]
        rows.append(row)
    text = json.dumps({"_header": header, "requests": rows}, indent=1) + "\n"
    bad = re.search(r"(/home|/work|/scratch|/staging|/lustre)/[A-Za-z][A-Za-z0-9_.-]*/", text)
    assert not bad, "a personal path is left in %s: %s" % (name, bad.group(0))
    (out / (name + ".json")).write_text(text, encoding="utf-8")


def main(out_dir):
    cfg = {"launcher": os.environ["ABF_NXF2_LAUNCHER"], "home": os.environ["ABF_NXF2_HOME"],
           "ver": os.environ["ABF_NXF2_VER"]}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="abf-record-"))
    stamp = time.strftime("%Y-%m-%d")
    base = {"nextflow": cfg["ver"], "nf-tower": "1.17.5", "recorded": stamp,
            "authorization": "Basic base64('@token:' + token); Content-Type application/json; charset=utf-8",
            "sanitized": "labuser<-OS user name, host1<-host name, ~<-home dir, /LAUNCH<-launch dir, /REPO<-repo checkout, "
                         "/CACHE<-tool cache, /wk/<-/work/, workflow id replaced by {id}; received_at is seconds since the first request"}
    dirs = {n: work / n for n in ("ok", "fail", "retry", "long")}
    jobs = {}
    try:
        def scenario(name, flow, extra=(), then=None):
            cap = Capture()
            try:
                p = run_flow(flow, dirs[name], cap.port, extra, cfg)
                mark = len(cap.requests)
                if then:
                    p2 = run_flow(flow, dirs[name], cap.port, then, cfg)
                    return cap, p, p2, mark
                return cap, p, None, mark
            finally:
                cap.stop()

        with ThreadPoolExecutor(4) as ex:
            jobs["ok"] = ex.submit(scenario, "ok", "ok", (), ("-resume",))
            jobs["fail"] = ex.submit(scenario, "fail", "fail")
            jobs["retry"] = ex.submit(scenario, "retry", "retry")
            jobs["long"] = ex.submit(scenario, "long", "long")
            res = {k: v.result() for k, v in jobs.items()}
        clean = sanitizer(list(dirs.values()), cfg["home"])
        cap, p, p2, mark = res["ok"]
        assert p.returncode == 0 and p2.returncode == 0, (p.stdout, p2.stdout, p2.stderr)
        traces = sorted(dirs["ok"].glob("trace-*.txt"), key=lambda q: q.stat().st_mtime)
        dump("nf2510_ok", dict(base, scenario="ok pipeline, three processes, six tasks",
                               expected=expected_from_trace(traces[0])), cap.requests[:mark], clean, out)
        dump("nf2510_resume", dict(base, scenario="the same pipeline again with -resume: every task cached",
                                   expected=expected_from_trace(traces[-1])), cap.requests[mark:], clean, out)
        cap, p, _, _ = res["fail"]
        assert p.returncode != 0
        dump("nf2510_fail", dict(base, scenario="fail pipeline, one task exits 1 with FIXTURE_BOOM_7",
                                 expected=expected_from_trace(next(dirs["fail"].glob("trace-*.txt")))),
             cap.requests, clean, out)
        cap, p, _, _ = res["retry"]
        assert p.returncode != 0
        dump("nf2510_retry", dict(base, scenario="retry pipeline: FLAKY fails once (exit 3) and succeeds on attempt 2, BAD exits 1",
                                  expected=expected_from_trace(next(dirs["retry"].glob("trace-*.txt")))),
             cap.requests, clean, out)
        cap, p, _, _ = res["long"]
        assert p.returncode == 0, (p.stdout, p.stderr)
        dump("nf2510_long_timing", dict(base, scenario="a run of more than four minutes; only kind and time of each message are kept"),
             cap.requests, clean, out, keep_bodies=False)
        print("recorded into", out)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(HERE / "payloads"))
