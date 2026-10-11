# Nothing existing: shared test helpers for this folder; pytest fixtures and the SDK client are used directly, only the replay and database-scanning glue is ours.
"""Helpers shared by the platform tests (feature 008)."""
import asyncio
import base64
import copy
import datetime
import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_DIR.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
PAYLOADS = FIXTURES / "payloads"

# Heartbeat interval of the pinned Nextflow (research.md: TowerObserver.groovy:60).
H = 60


def load_scenario(name):
    with open(PAYLOADS / (name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def basic_header(token):
    """The header Nextflow 26.04.7 really sends: Basic base64('@token:<token>')."""
    return "Basic " + base64.b64encode(("@token:" + token).encode()).decode()


def bearer_header(token):
    return "Bearer " + token


def iso_with_ms(epoch_float):
    dt = datetime.datetime.fromtimestamp(epoch_float, datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + "%03d+00:00" % (dt.microsecond // 1000)


def variant(name, run_name, session_id, start_epoch):
    """Requests of a recorded scenario, re-labelled as another run starting at start_epoch."""
    sc = copy.deepcopy(load_scenario(name))
    start_iso = iso_with_ms(start_epoch)
    end_iso = iso_with_ms(start_epoch + 2)
    for req in sc["requests"]:
        body = req["body"]
        if req["path"].startswith("/trace/create"):
            body["runName"] = run_name
            body["sessionId"] = session_id
        elif isinstance(body, dict) and "workflow" in body:
            wf = body["workflow"]
            wf["runName"] = run_name
            wf["sessionId"] = session_id
            wf["start"] = start_iso
            if wf.get("complete"):
                wf["complete"] = end_iso
    return sc["requests"]


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


class Platform:
    """The receiver app in process, with its own index and token files."""

    def __init__(self, tmp_path, clock=None):
        from starlette.testclient import TestClient
        from abf_platform import receiver, store

        self.dir = Path(tmp_path)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index = self.dir / "index.db"
        self.tokens = self.dir / "tokens.db"
        self.clock = clock or Clock()
        self.store = store
        self.app = receiver.create_app(self.index, self.tokens, clock=self.clock)
        self.client = TestClient(self.app)

    def new_token(self):
        return self.store.create_token(self.tokens)

    def send(self, method, path, body=None, token=None, scheme="basic", raw=None, headers=None):
        h = dict(headers or {})
        if token is not None:
            h["Authorization"] = basic_header(token) if scheme == "basic" else bearer_header(token)
        if raw is not None:
            h.setdefault("Content-Type", "application/json")
            return self.client.request(method, path, content=raw, headers=h)
        return self.client.request(method, path, json=body, headers=h)

    def replay(self, requests, token, query="", scheme="basic", stop_before=None, only=None):
        """Replay recorded requests in order; returns (workflow id, list of responses)."""
        wid = None
        out = []
        for req in requests:
            kind = req["path"].rstrip("/").split("/")[-1]
            if stop_before and kind == stop_before:
                break
            if only and kind not in only:
                continue
            path = req["path"]
            if "{id}" in path:
                path = path.replace("{id}", wid)
            resp = self.send(req["method"], path + query, req["body"], token=token, scheme=scheme)
            out.append(resp)
            if kind == "create" and resp.status_code < 300:
                wid = resp.json()["workflowId"]
        return wid, out

    def counts(self):
        return db_counts(self.index)

    def advance(self, seconds):
        self.clock.t += seconds


def db_counts(index_path):
    if not Path(index_path).exists():
        return {"runs": 0, "processes": 0, "failed_tasks": 0}
    con = sqlite3.connect(str(index_path))
    try:
        return {t: con.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
                for t in ("runs", "processes", "failed_tasks")}
    finally:
        con.close()


def db_rows(index_path, run_id=None):
    """All rows of the three tables (for 'unchanged' comparisons)."""
    con = sqlite3.connect(str(index_path))
    try:
        out = {}
        for t, col in (("runs", "id"), ("processes", "run_id"), ("failed_tasks", "run_id")):
            q = "SELECT * FROM " + t
            args = ()
            if run_id is not None:
                q += " WHERE " + col + " = ?"
                args = (run_id,)
            out[t] = sorted(map(tuple, con.execute(q + " ORDER BY 1, 2", args).fetchall()), key=repr)
        return out
    finally:
        con.close()


def db_bytes(*paths):
    """Whole content of the database files plus their -wal, -shm and -journal companions."""
    data = b""
    for p in paths:
        for suffix in ("", "-wal", "-shm", "-journal"):
            q = Path(str(p) + suffix)
            if q.exists():
                data += q.read_bytes()
    return data


def all_files_digest(*paths):
    h = hashlib.sha256()
    for p in paths:
        for suffix in ("", "-wal", "-shm", "-journal"):
            q = Path(str(p) + suffix)
            h.update(str(q).encode())
            if q.exists():
                h.update(q.read_bytes())
    return h.hexdigest()


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def pkg_env(**extra):
    """Environment for running 'python -m abf_platform' from the platform folder."""
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("ABF_PLATFORM_"):
            del env[k]
    env["PYTHONPATH"] = str(PLATFORM_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update({k: str(v) for k, v in extra.items()})
    return env


def run_cli(args, env=None, cwd=None, timeout=120):
    return subprocess.run([sys.executable, "-m", "abf_platform"] + list(args), env=env or pkg_env(),
                          cwd=cwd, capture_output=True, text=True, timeout=timeout)


def start_cli(args, env, logfile, cwd=None):
    log = open(logfile, "w")
    proc = subprocess.Popen([sys.executable, "-m", "abf_platform"] + list(args), env=env, cwd=cwd,
                            stdout=log, stderr=subprocess.STDOUT)
    proc._abf_log = log
    return proc


def stop_proc(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    log = getattr(proc, "_abf_log", None)
    if log:
        log.close()


def wait_port(port, host="127.0.0.1", timeout=30, proc=None):
    end = time.time() + timeout
    while time.time() < end:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError("server exited early with code %s" % proc.returncode)
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("port %s did not open" % port)


def non_loopback_address():
    """An address of this machine that is not loopback, or None."""
    cands = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # a UDP connect sends nothing
        cands.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        cands.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    for a in cands:
        if a and not a.startswith("127.") and a != "0.0.0.0":
            return a
    return None


def listening_addresses(port):
    """Local addresses with a listening TCP socket on port, read from /proc (Linux), or None."""
    res = []
    for fn in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lines = open(fn).read().splitlines()[1:]
        except OSError:
            return None
        for ln in lines:
            parts = ln.split()
            addr, state = parts[1], parts[3]
            ip_hex, port_hex = addr.split(":")
            if state == "0A" and int(port_hex, 16) == port:
                res.append(ip_hex)
    return res


def assert_loopback_only(port):
    """127.0.0.1 answers; another address of this machine does not.

    Without a second address, the listening socket's bound address is checked
    instead and the reason is printed, so this never passes silently.
    """
    wait_port(port)
    other = non_loopback_address()
    if other:
        try:
            socket.create_connection((other, port), timeout=3).close()
        except OSError:
            return
        raise AssertionError("port %s answers on %s, not only on loopback" % (port, other))
    print("no non-loopback address on this machine; checking the bound address instead")
    addrs = listening_addresses(port)
    assert addrs, "cannot read the bound address of port %s" % port
    assert all(a in ("0100007F", "00000000000000000000000001000000") for a in addrs), addrs


def tool_json(result):
    """The JSON object a tool call returned (structured content, else the text)."""
    sc = getattr(result, "structured_content", None)
    if sc:
        return sc
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except ValueError:
                return {"text": text}
    return {}


def tool_text(result):
    parts = [getattr(b, "text", "") or "" for b in result.content]
    return "\n".join(parts) + json.dumps(getattr(result, "structured_content", None))


def mcp_stdio_params(env):
    from mcp.client.stdio import StdioServerParameters
    return StdioServerParameters(command=sys.executable, args=["-m", "abf_platform", "mcp"], env=env)


def mcp_call(env, calls, errlog=None):
    """Run tool calls [(name, args)] against 'abf-platform mcp' over stdio; returns (tools, [results])."""
    from mcp import Client

    async def go():
        async with Client(mcp_stdio_params(env)) as client:
            tools = (await client.list_tools()).tools
            outs = []
            for name, args in calls:
                outs.append(await client.call_tool(name, args))
            return tools, outs

    return asyncio.run(go())


def mcp_http_call(url, calls):
    from mcp import Client

    async def go():
        async with Client(url) as client:
            tools = (await client.list_tools()).tools
            outs = []
            for name, args in calls:
                outs.append(await client.call_tool(name, args))
            return tools, outs

    return asyncio.run(go())
