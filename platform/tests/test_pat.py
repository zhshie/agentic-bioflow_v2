# Nothing existing: tests of the personal access tokens (spec 009d) - users, PATs, the 401 on HTTP MCP, the caller; the rules and the scans are ours.
"""Spec 009d: identity for the MCP server, step one = personal access tokens. Fixtures build every PAT at run time."""
import ast
import asyncio
import dataclasses
import hashlib
import inspect
import re
import socket
import sqlite3
import threading
import time
from pathlib import Path

import httpx
import pytest

from helpers import (Clock, Platform, PLATFORM_DIR, db_bytes, free_port, mcp_call, mcp_http_call, pkg_env, run_cli,
                     start_cli, stop_proc, tool_json, wait_port)
from test_actions_layer import READ_NAMES, WRITE_NAMES, imported_names, platform_submodules, action_refs
from test_launch_platform import bundle, own_all, setup, sql
from test_actions_layer import _cancel_bundle
from test_station_platform import agent_token, bearer, state_db

PKG = PLATFORM_DIR / "abf_platform"
PAT_RE = re.compile(r"abf_pat_[A-Za-z0-9_-]{20,}")


# ---- helpers ------------------------------------------------------------------------------------------------------------

def _env(tmp_path, **extra):
    return pkg_env(ABF_PLATFORM_DB=tmp_path / "data" / "index.db", **extra)


def _tokens(tmp_path):
    return tmp_path / "data" / "tokens.db"


def _store():
    from abf_platform import store
    return store


def _user(tmp_path, name="alice", lab="lab-x"):
    st = _store()
    return st.create_user(_tokens(tmp_path), name, lab)


def _pat(tmp_path, name="alice", lab="lab-x", label=None):
    st = _store()
    uid = _user(tmp_path, name, lab)
    return st.create_token(_tokens(tmp_path), kind="pat", user_id=uid, label=label), uid


def _rows(path, text, args=()):
    con = sqlite3.connect(str(path))
    try:
        return con.execute(text, args).fetchall()
    finally:
        con.close()


def _start_http(tmp_path, env=None):
    port = free_port()
    proc = start_cli(["mcp", "--http", "--port", str(port)], env or _env(tmp_path), tmp_path / "mcp.log")
    wait_port(port, proc=proc)
    return port, proc


INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}


def _post(port, auth=None):
    h = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if auth is not None:
        h["Authorization"] = auth
    if auth is not None and auth != auth.strip():
        return _raw_post(port, auth)     # httpx refuses a header value that ends in a space; a raw request does not
    return httpx.post("http://127.0.0.1:%d/mcp" % port, json=INIT, headers=h, timeout=10)


class _Raw:
    def __init__(self, status_code, headers, text):
        self.status_code, self.headers, self.text = status_code, headers, text


def _raw_post(port, auth):
    import json as _json
    body = _json.dumps(INIT).encode()
    req = ("POST /mcp HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nAccept: application/json, text/event-stream\r\n"
           "Content-Type: application/json\r\nAuthorization: %s\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
           % (port, auth, len(body))).encode() + body
    with socket.create_connection(("127.0.0.1", port), timeout=10) as s:
        s.sendall(req)
        data = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
    head, _, text = data.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    headers = {k.strip().lower(): v.strip() for k, _, v in (ln.partition(":") for ln in lines[1:])}
    return _Raw(int(lines[0].split()[1]), headers, text.decode("latin-1"))


def _assert_401(r):
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


class _Served:
    """The wrapped HTTP app served by uvicorn on a thread of this process, so a test can spy on an action."""

    def __init__(self, index, tokens):
        import uvicorn
        from abf_platform import mcp_server
        self.port = free_port()
        app = mcp_server.build_http_app(index, tokens_path=tokens)
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        wait_port(self.port)
        time.sleep(0.3)
        self.url = "http://127.0.0.1:%d/mcp" % self.port
        return self

    def __exit__(self, *a):
        self.server.should_exit = True
        self.thread.join(timeout=15)


# ---- US1: users and PATs on the terminal ---------------------------------------------------------------------------------

def test_tca01_user_add_then_pat_new_and_the_help_lists_the_commands(tmp_path):
    # TC-A01
    env = _env(tmp_path)
    assert run_cli(["user", "add", "alice", "--lab", "lab-x"], env=env).returncode == 0
    assert run_cli(["pat", "new", "--user", "alice"], env=env).returncode == 0
    h = run_cli(["--help"], env=env)
    assert "user" in h.stdout and "pat" in h.stdout


def test_tca02_pat_new_prints_once_with_the_token_new_wording_and_two_differ(tmp_path):
    # TC-A02
    env = _env(tmp_path)
    run_cli(["user", "add", "alice", "--lab", "lab-x"], env=env)
    a = run_cli(["pat", "new", "--user", "alice"], env=env)
    b = run_cli(["pat", "new", "--user", "alice"], env=env)
    ta, tb = PAT_RE.findall(a.stdout), PAT_RE.findall(b.stdout)
    assert len(ta) == 1 and len(tb) == 1 and ta[0] != tb[0]
    assert len(ta[0]) == len("abf_pat_") + 43      # secrets.token_urlsafe(32) is 43 characters
    assert "shown once and cannot be shown again; only its hash is kept" in a.stdout


def test_tca03_the_label_shows_in_pat_list(tmp_path):
    # TC-A03
    env = _env(tmp_path)
    run_cli(["user", "add", "alice", "--lab", "lab-x"], env=env)
    assert run_cli(["pat", "new", "--user", "alice", "--label", "筆電"], env=env).returncode == 0
    assert run_cli(["pat", "new", "--user", "alice"], env=env).returncode == 0
    out = run_cli(["pat", "list"], env=env)
    assert out.returncode == 0 and "筆電" in out.stdout
    assert _rows(_tokens(tmp_path), "SELECT label FROM tokens WHERE kind = 'pat' ORDER BY id") == [("筆電",), (None,)]


def test_tca04_pat_list_one_row_each_marks_revoked_and_holds_no_value_or_hash(tmp_path):
    # TC-A04
    env = _env(tmp_path)
    run_cli(["user", "add", "alice", "--lab", "lab-x"], env=env)
    p1 = PAT_RE.findall(run_cli(["pat", "new", "--user", "alice"], env=env).stdout)[0]
    p2 = PAT_RE.findall(run_cli(["pat", "new", "--user", "alice"], env=env).stdout)[0]
    ids = [r[0] for r in _rows(_tokens(tmp_path), "SELECT id FROM tokens WHERE kind = 'pat' ORDER BY id")]
    assert run_cli(["pat", "revoke", str(ids[0])], env=env).returncode == 0
    out = run_cli(["pat", "list"], env=env).stdout
    lines = [ln for ln in out.splitlines() if "alice" in ln]
    assert len(lines) == 2
    assert "revoked" in lines[0] and "revoked" not in lines[1].replace("revoked: no", "").replace("not revoked", "")
    for p in (p1, p2):
        assert p not in out and hashlib.sha256(p.encode()).hexdigest() not in out


def test_tca05_the_pat_is_only_a_hash_on_disk_and_the_user_is_in_tokens_db(tmp_path):
    # TC-A05
    env = _env(tmp_path)
    run_cli(["user", "add", "alice-canary", "--lab", "lab-canary"], env=env)
    pat = PAT_RE.findall(run_cli(["pat", "new", "--user", "alice-canary"], env=env).stdout)[0]
    run_cli(["token", "new"], env=env)       # creates index.db's neighbour files as usual
    from abf_platform import store
    store.init_index(tmp_path / "data" / "index.db")
    for f in (_tokens(tmp_path), tmp_path / "data" / "index.db"):
        assert pat.encode() not in db_bytes(f)
    assert hashlib.sha256(pat.encode()).hexdigest() in [r[0] for r in _rows(_tokens(tmp_path), "SELECT token_hash FROM tokens")]
    assert _rows(_tokens(tmp_path), "SELECT name, lab FROM users") == [("alice-canary", "lab-canary")]
    assert b"alice-canary" not in db_bytes(tmp_path / "data" / "index.db")


def test_tca06_pat_revoke_ends_one_pat_and_leaves_the_other(tmp_path):
    # TC-A06
    st = _store()
    pat1, uid = _pat(tmp_path)
    pat2 = st.create_token(_tokens(tmp_path), kind="pat", user_id=uid)
    ids = [r[0] for r in _rows(_tokens(tmp_path), "SELECT id FROM tokens WHERE kind = 'pat' ORDER BY id")]
    r = run_cli(["pat", "revoke", str(ids[0])], env=_env(tmp_path))
    assert r.returncode == 0
    assert st.lookup_pat(_tokens(tmp_path), pat1) is None
    assert st.lookup_pat(_tokens(tmp_path), pat2)["user_id"] == uid


def test_tca07_only_pat_new_prints_the_value(tmp_path):
    # TC-A07
    env = _env(tmp_path)
    outs = [run_cli(["user", "add", "alice", "--lab", "lab-x"], env=env)]
    new = run_cli(["pat", "new", "--user", "alice"], env=env)
    pat = PAT_RE.findall(new.stdout)[0]
    assert pat not in new.stderr
    outs.append(run_cli(["pat", "list"], env=env))
    outs.append(run_cli(["pat", "revoke", "999"], env=env))
    outs.append(run_cli(["pat", "new", "--user", "nobody"], env=env))
    outs.append(run_cli(["user", "add", "alice", "--lab", "other"], env=env))
    port, proc = _start_http(tmp_path, env)
    try:
        assert _post(port, "Bearer " + pat).status_code == 200
        mcp_http_call("http://127.0.0.1:%d/mcp" % port, [("list_runs", {})], token=pat)
        _post(port, "Bearer abf_pat_" + "z" * 43)
        _post(port)
    finally:
        stop_proc(proc)
    for o in outs:
        assert pat not in o.stdout and pat not in o.stderr
    assert pat not in (tmp_path / "mcp.log").read_text(errors="replace")


def test_tca08_an_old_tokens_db_migrates(tmp_path):
    # TC-A08
    st = _store()
    path = _tokens(tmp_path)
    path.parent.mkdir(parents=True)
    con = sqlite3.connect(str(path))
    con.executescript("CREATE TABLE tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, token_hash TEXT NOT NULL UNIQUE, "
                      "created_at REAL NOT NULL);")
    old = "abf_" + "o" * 40
    con.execute("INSERT INTO tokens (token_hash, created_at) VALUES (?, ?)", (hashlib.sha256(old.encode()).hexdigest(), 1.0))
    con.commit()
    con.close()
    assert st.lookup_token(path, old)["kind"] == "run"
    uid = st.create_user(path, "alice", "lab-x")
    pat = st.create_token(path, kind="pat", user_id=uid, label="筆電")
    cols = {r[1] for r in _rows(path, "PRAGMA table_info(tokens)")}
    assert {"user_id", "label"} <= cols
    assert _rows(path, "SELECT name FROM users") == [("alice",)]
    assert st.lookup_pat(path, pat)["name"] == "alice" and st.lookup_token(path, old)["kind"] == "run"


def test_tca09_pat_new_for_an_unknown_user_is_refused_and_creates_nothing(tmp_path):
    # TC-A09
    env = _env(tmp_path)
    r = run_cli(["pat", "new", "--user", "nobody"], env=env)
    assert r.returncode != 0 and len((r.stderr + r.stdout).strip().splitlines()) == 1
    assert not PAT_RE.findall(r.stdout + r.stderr)
    if _tokens(tmp_path).exists():
        assert _rows(_tokens(tmp_path), "SELECT COUNT(*) FROM tokens")[0][0] == 0


def test_tca10_a_second_user_add_with_the_same_name_is_refused(tmp_path):
    # TC-A10
    env = _env(tmp_path)
    assert run_cli(["user", "add", "王小明", "--lab", "lab-1"], env=env).returncode == 0
    r = run_cli(["user", "add", "王小明", "--lab", "lab-2"], env=env)
    assert r.returncode != 0 and len((r.stderr + r.stdout).strip().splitlines()) == 1
    assert _rows(_tokens(tmp_path), "SELECT name, lab FROM users") == [("王小明", "lab-1")]


def test_tca11_no_tool_route_or_action_creates_or_revokes_users_or_pats(tmp_path):
    # TC-A11
    from abf_platform import actions, mcp_server
    tools = asyncio.run(mcp_server.build_server(str(tmp_path / "i.db")).list_tools())
    assert sorted(t.name for t in tools) == sorted(READ_NAMES + WRITE_NAMES)    # 009c: plus launch and cancel
    for t in tools:
        text = t.name + " " + " ".join(t.input_schema.get("properties", {}))
        assert not re.search(r"(^|[\s_])(user|pat|token)s?($|[\s_])", text)
    plat = Platform(tmp_path / "p", clock=Clock())
    assert not [p for p in (getattr(r, "path", "") for r in plat.app.routes) if re.search(r"user$|pat|admin", p)]
    assert not [n for n in dir(actions) if re.search(r"user|pat\b|pat_|token", n, re.I)]


def test_tca12_an_unknown_kind_is_a_value_error_and_writes_nothing(tmp_path):
    # TC-A12
    st = _store()
    with pytest.raises(ValueError):
        st.create_token(_tokens(tmp_path), kind="admin")
    if _tokens(tmp_path).exists():
        assert _rows(_tokens(tmp_path), "SELECT COUNT(*) FROM tokens")[0][0] == 0


# ---- US2: HTTP needs a PAT -----------------------------------------------------------------------------------------------

def test_tcb01_to_b04_b07_every_bad_header_is_401_with_www_authenticate_and_never_echoed(tmp_path):
    # TC-B01, TC-B02, TC-B03, TC-B04, TC-B07
    pat, _ = _pat(tmp_path)
    garbage = "abf_pat_" + "q" * 43
    port, proc = _start_http(tmp_path)
    try:
        bad = [None, "Basic " + pat, "Token " + pat, "Bearer", "Bearer ", "Bearer garbage", "Bearer " + garbage]
        for h in bad:
            r = _post(port, h)
            _assert_401(r)
            blob = r.text + str(dict(r.headers))
            assert pat not in blob and garbage not in blob and "garbage" not in blob.replace("Bearer garbage", "")
    finally:
        stop_proc(proc)


def test_tcb05_a_revoked_pat_is_401_at_once_without_a_restart(tmp_path):
    # TC-B05, TC-B07
    st = _store()
    pat, _ = _pat(tmp_path)
    port, proc = _start_http(tmp_path)
    try:
        assert _post(port, "Bearer " + pat).status_code == 200
        pid = _rows(_tokens(tmp_path), "SELECT id FROM tokens WHERE kind = 'pat'")[0][0]
        assert st.revoke_pat(_tokens(tmp_path), pid) == 1
        r = _post(port, "Bearer " + pat)
        _assert_401(r)
        assert pat not in r.text + str(dict(r.headers))
    finally:
        stop_proc(proc)


def test_tcb06_a_disabled_user_is_401(tmp_path):
    # TC-B06
    pat, uid = _pat(tmp_path)
    con = sqlite3.connect(str(_tokens(tmp_path)))
    con.execute("UPDATE users SET disabled_at = ? WHERE id = ?", (time.time(), uid))
    con.commit()
    con.close()
    port, proc = _start_http(tmp_path)
    try:
        _assert_401(_post(port, "Bearer " + pat))
    finally:
        stop_proc(proc)


def _three_runs(tmp_path):
    from test_mcp import _three_runs as three
    return three(tmp_path)


def test_tcb08_b09_a_valid_pat_gives_the_six_tools_and_the_stdio_answers(tmp_path):
    # TC-B08, TC-B09
    plat, _ = _three_runs(tmp_path)
    tokens = plat.tokens
    st = _store()
    uid = st.create_user(tokens, "alice", "lab-x")
    pat = st.create_token(tokens, kind="pat", user_id=uid)
    from abf_platform import status
    wid = status.list_runs(plat.index, time.time())[0]["id"]
    from helpers import own_runs       # 116: the three runs are alice's, as the hand-off record says, so her HTTP answers are the stdio answers
    own_runs(state_db(plat), uid, [r["name"] for r in status.list_runs(plat.index, time.time())])
    calls = [("list_runs", {}), ("get_run", {"run_id": wid}), ("list_compute_envs", {}), ("list_agents", {})]
    env = pkg_env(ABF_PLATFORM_DB=plat.index)
    _, via_stdio = mcp_call(env, calls)
    port = free_port()
    proc = start_cli(["mcp", "--http", "--port", str(port)], env, tmp_path / "mcp.log")
    try:
        wait_port(port, proc=proc)
        tools, via_http = mcp_http_call("http://127.0.0.1:%d/mcp" % port, calls, token=pat)
    finally:
        stop_proc(proc)
    assert sorted(t.name for t in tools) == sorted(READ_NAMES + WRITE_NAMES)    # 009c: plus launch and cancel
    for a, b in zip(via_stdio, via_http):
        assert tool_json(a) == tool_json(b)


def test_tcb10_stdio_needs_no_token_and_no_user(tmp_path):
    # TC-B10
    plat, _ = _three_runs(tmp_path)
    assert not plat.tokens.exists() or _rows(plat.tokens, "SELECT COUNT(*) FROM tokens WHERE kind = 'pat'")[0][0] == 0
    tools, outs = mcp_call(pkg_env(ABF_PLATFORM_DB=plat.index), [("list_runs", {})])
    assert len(tools) == 8 and len(tool_json(outs[0])["runs"]) == 3    # 009c: six read tools plus launch and cancel


def test_tcb11_without_users_http_starts_says_so_and_answers_401(tmp_path):
    # TC-B11
    port, proc = _start_http(tmp_path)
    try:
        assert proc.poll() is None
        _assert_401(_post(port, "Bearer abf_pat_" + "a" * 43))
        _assert_401(_post(port))
    finally:
        stop_proc(proc)
    log = (tmp_path / "mcp.log").read_text(errors="replace")
    assert re.search(r"no users", log, re.I) and "401" in log


def test_tcb12_a_non_loopback_host_keeps_the_risk_line_and_says_a_token_is_needed(tmp_path):
    # TC-B12
    port = free_port()
    proc = start_cli(["mcp", "--http", "--host", "0.0.0.0", "--port", str(port)], _env(tmp_path), tmp_path / "wide.log")
    try:
        wait_port(port, proc=proc)
    finally:
        stop_proc(proc)
    wide = (tmp_path / "wide.log").read_text(errors="replace")
    assert "WARNING" in wide and re.search(r"token is required", wide)
    port2, proc2 = _start_http(tmp_path)
    stop_proc(proc2)
    assert "WARNING" not in (tmp_path / "mcp.log").read_text(errors="replace")


def test_tcb13_no_flag_or_environment_variable_turns_auth_off(tmp_path):
    # TC-B13
    for flag in ("--no-auth", "--insecure", "--no-token"):
        r = run_cli(["mcp", "--http", flag], env=_env(tmp_path), timeout=30)
        assert r.returncode != 0 and "unrecognized arguments" in r.stderr
    helptext = run_cli(["mcp", "--help"], env=_env(tmp_path)).stdout
    assert not re.search(r"auth|insecure|token", helptext, re.I)
    for name in ("http_auth.py", "mcp_server.py"):
        tree = ast.parse((PKG / name).read_text(encoding="utf-8"))
        assert not any(isinstance(n, ast.Attribute) and n.attr in ("environ", "getenv") for n in ast.walk(tree)), name
        assert not any(isinstance(n, ast.Name) and n.id in ("environ", "getenv") for n in ast.walk(tree)), name
    cli_tree = ast.parse((PKG / "cli.py").read_text(encoding="utf-8"))
    cmd = [n for n in ast.walk(cli_tree) if isinstance(n, ast.FunctionDef) and n.name == "cmd_mcp"][0]
    assert not any(isinstance(n, ast.Attribute) and n.attr in ("environ", "getenv") for n in ast.walk(cmd))


def test_tcb14_the_caller_is_the_one_of_the_request_and_never_left_over(tmp_path, monkeypatch):
    # TC-B14, TC-D02, TC-D03
    from abf_platform import actions
    seen = []

    def spy(platform_path, **kw):
        seen.append(kw.get("caller"))
        return {"agents": []}

    monkeypatch.setattr(actions, "list_agents", spy)
    st = _store()
    tokens = tmp_path / "data" / "tokens.db"
    pa = st.create_token(tokens, kind="pat", user_id=st.create_user(tokens, "alice", "lab-a"))
    pb = st.create_token(tokens, kind="pat", user_id=st.create_user(tokens, "bob", "lab-b"))
    with _Served(tmp_path / "data" / "index.db", tokens) as s:
        mcp_http_call(s.url, [("list_agents", {})], token=pa)
        _assert_401(httpx.post(s.url, json=INIT, headers={"Accept": "application/json, text/event-stream"}))
        mcp_http_call(s.url, [("list_agents", {})], token=pb)
    assert [(c.name, c.lab) for c in seen] == [("alice", "lab-a"), ("bob", "lab-b")]
    assert all(isinstance(c.user_id, int) for c in seen)
    # stdio: the caller is None
    seen.clear()
    from abf_platform.mcp_server import build_server
    asyncio.run(build_server(str(tmp_path / "i.db")).call_tool("list_agents", {}))
    assert seen == [None]


def test_tcb15_tc025_only_its_input_changed():
    # TC-B15 (manual by the reviewer; here only the assertions that must stay)
    text = (PLATFORM_DIR / "tests" / "test_mcp.py").read_text(encoding="utf-8")
    assert 'assert tool_json(a) == tool_json(b)' in text and "assert tool_json(via_http[1])[\"id\"] == wid" in text


# ---- US3: one kind of token, one door -------------------------------------------------------------------------------------

def test_tcc01_c02_a_pat_opens_neither_the_receiver_nor_the_agent_doors(tmp_path):
    # TC-C01, TC-C02
    from helpers import load_scenario
    plat = Platform(tmp_path / "p", clock=Clock())
    st = plat.store
    pat = st.create_token(plat.tokens, kind="pat", user_id=st.create_user(plat.tokens, "alice", "lab-x"))
    before = plat.counts()
    body = load_scenario("ok_run")["requests"][0]["body"]
    for scheme in ("basic", "bearer"):
        assert plat.send("POST", "/trace/create", body, token=pat, scheme=scheme).status_code in (401, 403)
        assert plat.send("GET", "/user-info", token=pat, scheme=scheme).status_code in (401, 403)
    for path in ("/agent/hello", "/agent/poll", "/agent/result/1"):
        r = plat.client.post(path, json={"name": "a1", "state": "done", "result": {}}, headers=bearer(pat))
        assert r.status_code == 401, path
    assert plat.counts() == before
    assert _rows(state_db(plat), "SELECT COUNT(*) FROM agents")[0][0] == 0
    assert _rows(state_db(plat), "SELECT COUNT(*) FROM jobs")[0][0] == 0


@pytest.mark.parametrize("kind", ["run", "agent"])
def test_tcc03_c04_a_run_or_agent_token_is_401_on_mcp(tmp_path, kind):
    # TC-C03, TC-C04
    _user(tmp_path)
    st = _store()
    tok = st.create_token(_tokens(tmp_path), kind=kind, agent_name="a1" if kind == "agent" else None)
    port, proc = _start_http(tmp_path)
    try:
        _assert_401(_post(port, "Bearer " + tok))
    finally:
        stop_proc(proc)


def test_tcc05_lookup_pat_gives_the_four_fields(tmp_path):
    # TC-C05
    st = _store()
    pat, uid = _pat(tmp_path)
    tid = _rows(_tokens(tmp_path), "SELECT id FROM tokens")[0][0]
    assert st.lookup_pat(_tokens(tmp_path), pat) == {"user_id": uid, "name": "alice", "lab": "lab-x", "token_id": tid}


def test_tcc06_lookup_pat_is_none_for_everything_else_and_never_raises(tmp_path):
    # TC-C06
    st = _store()
    t = _tokens(tmp_path)
    pat, uid = _pat(tmp_path)
    revoked = st.create_token(t, kind="pat", user_id=uid)
    st.revoke_pat(t, _rows(t, "SELECT id FROM tokens WHERE token_hash = ?", (hashlib.sha256(revoked.encode()).hexdigest(),))[0][0])
    uid2 = st.create_user(t, "bob", "lab-y")
    dis = st.create_token(t, kind="pat", user_id=uid2)
    con = sqlite3.connect(str(t))
    con.execute("UPDATE users SET disabled_at = 1 WHERE id = ?", (uid2,))
    con.commit()
    con.close()
    run, agent = st.create_token(t), st.create_token(t, kind="agent", agent_name="a1")
    for v in (revoked, dis, "abf_pat_" + "n" * 43, "", None, run, agent):
        assert st.lookup_pat(t, v) is None
    assert st.lookup_pat(t, pat) is not None
    assert st.lookup_pat(tmp_path / "missing.db", pat) is None


# ---- US4: the caller is recorded, never a confirmation --------------------------------------------------------------------

def _caller(uid=7, name="alice", lab="lab-x"):
    from abf_platform.actions import Caller
    return Caller(uid, name, lab)


def test_tcd01_read_actions_take_caller_by_keyword_and_ignore_it(tmp_path):
    # TC-D01
    from abf_platform import actions
    plat = Platform(tmp_path / "p", clock=Clock())
    for name in READ_NAMES:
        p = inspect.signature(getattr(actions, name)).parameters["caller"]
        assert p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is None
    u = _caller()
    assert actions.list_runs(plat.index) == actions.list_runs(plat.index, caller=None) == actions.list_runs(plat.index, caller=u)
    assert actions.list_agents(state_db(plat)) == actions.list_agents(state_db(plat), caller=u)
    assert actions.get_run(plat.index, "x") == actions.get_run(plat.index, "x", caller=u)
    assert actions.list_compute_envs(state_db(plat)) == actions.list_compute_envs(state_db(plat), caller=u)
    assert actions.get_compute_env(state_db(plat), "x") == actions.get_compute_env(state_db(plat), "x", caller=u)


def test_tcd04_caller_is_frozen_with_exactly_three_fields():
    # TC-D04
    c = _caller()
    assert [f.name for f in dataclasses.fields(c)] == ["user_id", "name", "lab"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.name = "mallory"


@pytest.mark.parametrize("fn", ["launch", "cancel"])
def test_tcd05_d06_identity_is_not_a_confirmation(tmp_path, fn):
    # TC-D05, TC-D06
    from abf_platform import actions, jobs
    plat, _, clock = setup(tmp_path)
    b = bundle("run-one") if fn == "launch" else _cancel_bundle(plat)
    before = [sql(plat, "SELECT COUNT(*) FROM " + t)[0][0] for t in ("jobs", "confirmations")]
    with pytest.raises(jobs.JobRefused, match="no human confirmation channel"):
        getattr(actions, fn)(state_db(plat), "lab-a", b, confirmed_by="yes", caller=_caller(), clock=clock)
    assert [sql(plat, "SELECT COUNT(*) FROM " + t)[0][0] for t in ("jobs", "confirmations")] == before


@pytest.mark.parametrize("value", [None, True, "TERMINAL", "<abf_platform.actions.TERMINAL>"])
def test_tcd07_caller_alone_is_refused_before_any_database_is_opened(tmp_path, value):
    # TC-D07
    from abf_platform import actions, jobs
    path = tmp_path / "nowhere" / "platform.db"
    with pytest.raises(jobs.JobRefused):
        actions.launch(path, "lab-a", bundle("run-one"), confirmed_by=value, caller=_caller())
    assert not path.exists() and not path.parent.exists()


def test_tcd08_a_terminal_launch_with_a_caller_records_the_user(tmp_path):
    # TC-D08
    from abf_platform import actions
    plat, _, clock = setup(tmp_path)
    st = _store()
    tokens = tmp_path / "tk.db"
    uid = st.create_user(tokens, "alice", "lab-x")
    u = _caller(uid)
    own_all(plat, uid)      # 116: a caller may use only what is theirs
    before = sql(plat, "SELECT COUNT(*) FROM jobs")[0][0]
    cid, jid = actions.launch(state_db(plat), "lab-a", bundle("run-one"), confirmed_by=actions.TERMINAL, caller=u, clock=clock)
    assert sql(plat, "SELECT COUNT(*) FROM jobs")[0][0] == before + 1
    assert sql(plat, "SELECT caller_user_id FROM confirmations WHERE id = ?", (cid,)) == [(uid,)]
    assert _rows(tokens, "SELECT name FROM users WHERE id = ?", (uid,)) == [("alice",)]


def test_tcd09_a_terminal_cancel_with_a_caller_records_the_user(tmp_path):
    # TC-D09
    from abf_platform import actions
    plat, _, clock = setup(tmp_path)
    cb = _cancel_bundle(plat)
    own_all(plat, 5)        # 116: the environment, its agent and the launch are the caller's own
    before = sql(plat, "SELECT COUNT(*) FROM jobs")[0][0]
    cid, jid = actions.cancel(state_db(plat), "lab-a", cb, confirmed_by=actions.TERMINAL,
                              caller=_caller(5), clock=clock)
    assert sql(plat, "SELECT COUNT(*) FROM jobs")[0][0] == before + 1
    assert sql(plat, "SELECT caller_user_id, kind FROM confirmations WHERE id = ?", (cid,)) == [(5, "cancel")]


def test_tcd10_the_terminal_passes_caller_none_and_the_row_is_null(tmp_path):
    # TC-D10
    from abf_platform import actions
    text = (PLATFORM_DIR / "abf_launch" / "cli.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr in ("launch", "cancel") and getattr(n.func.value, "id", "") == "actions"]
    assert len(calls) == 2
    for c in calls:
        kw = {k.arg: k.value for k in c.keywords}
        if c.func.attr == "cancel":      # 116: a cancel at the terminal still names no account
            assert isinstance(kw.get("caller"), ast.Constant) and kw["caller"].value is None
        else:                            # a launch at the terminal passes the account named with --user, None when there is no user at all
            assert isinstance(kw.get("caller"), ast.Name) and kw["caller"].id == "caller"
    plat, _, clock = setup(tmp_path)
    cid, _ = actions.launch(state_db(plat), "lab-a", bundle("run-one"), confirmed_by=actions.TERMINAL, clock=clock)
    assert sql(plat, "SELECT caller_user_id FROM confirmations WHERE id = ?", (cid,)) == [(None,)]


def test_tcd11_an_old_platform_db_gets_the_column_in_place(tmp_path):
    # TC-D11
    from abf_platform import actions
    plat, _, clock = setup(tmp_path)
    con = sqlite3.connect(str(state_db(plat)))
    con.execute("ALTER TABLE confirmations DROP COLUMN caller_user_id") if "caller_user_id" in [
        r[1] for r in con.execute("PRAGMA table_info(confirmations)")] else None
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('old1', 'ab', 'launch', 1.0)")
    con.commit()
    assert "caller_user_id" not in [r[1] for r in con.execute("PRAGMA table_info(confirmations)")]
    con.close()
    own_all(plat, 9)        # 116: a caller may use only what is theirs
    cid, _ = actions.launch(state_db(plat), "lab-a", bundle("run-one"), confirmed_by=actions.TERMINAL,
                            caller=_caller(9), clock=clock)
    assert sql(plat, "SELECT caller_user_id FROM confirmations WHERE id = 'old1'") == [(None,)]
    assert sql(plat, "SELECT caller_user_id FROM confirmations WHERE id = ?", (cid,)) == [(9,)]


def test_tcd12_the_import_rules(tmp_path):
    # TC-D12
    mcp_src = (PKG / "mcp_server.py").read_text(encoding="utf-8")
    auth_src = (PKG / "http_auth.py").read_text(encoding="utf-8")
    assert platform_submodules(mcp_src, "abf_platform/mcp_server.py") == {"actions", "guidance", "http_auth"}  # 009g adds guidance; 009d's http_auth stays
    assert action_refs(mcp_src, "abf_platform/mcp_server.py") == []
    assert platform_submodules(auth_src, "abf_platform/http_auth.py") == {"store", "actions"}
    names = imported_names(auth_src, "abf_platform/http_auth.py")
    assert {n for n in names if n.startswith("abf_platform.actions")} <= {"abf_platform.actions", "abf_platform.actions.Caller"}
    assert action_refs(auth_src, "abf_platform/http_auth.py") == []


# ---- US5 / not in scope ------------------------------------------------------------------------------------------------------

def test_tcf01_no_authorization_server_in_the_mcp_process_and_a_resource_metadata_challenge_only_with_a_public_url(tmp_path):
    # TC-F01 (009i: the first half is the 009d test as it was; the second half is the new metadata and challenge, TC-A01 and TC-A02)
    pat, _ = _pat(tmp_path)
    port, proc = _start_http(tmp_path)
    try:
        for p in ("/.well-known/oauth-protected-resource", "/.well-known/oauth-authorization-server"):
            r = httpx.get("http://127.0.0.1:%d%s" % (port, p), headers={"Authorization": "Bearer " + pat}, timeout=10)
            assert r.status_code == 404
        r = _post(port)
        assert r.headers["www-authenticate"] == "Bearer" and "resource_metadata" not in r.headers["www-authenticate"]
    finally:
        stop_proc(proc)
    _store().set_meta(tmp_path / "data" / "platform.db", "web_base_url", "https://abf.example")
    port2 = free_port()
    proc2 = start_cli(["mcp", "--http", "--port", str(port2), "--public-url", "https://mcp.example"], _env(tmp_path), tmp_path / "mcp2.log")
    try:
        wait_port(port2, proc=proc2)
        url = "https://mcp.example/.well-known/oauth-protected-resource/mcp"
        assert _post(port2).headers["www-authenticate"] == 'Bearer resource_metadata="%s"' % url
        assert httpx.get("http://127.0.0.1:%d/.well-known/oauth-protected-resource/mcp" % port2, timeout=10).status_code == 200
        r = httpx.get("http://127.0.0.1:%d/.well-known/oauth-authorization-server" % port2, headers={"Authorization": "Bearer " + pat}, timeout=10)
        assert r.status_code == 404           # the authorization server is the web app's, never the MCP process's
    finally:
        stop_proc(proc2)
    assert "AuthSettings" not in (PKG / "mcp_server.py").read_text(encoding="utf-8")


def test_tcf02_no_tls_options_and_the_public_url_is_the_only_new_one():
    # TC-F02 (009i: `public` is allowed, as --public-url, and run_http gains public_url; ssl, cert and tls stay out)
    h = run_cli(["mcp", "--help"]).stdout
    assert not re.search(r"ssl|cert|tls", h, re.I)
    assert {x.lower() for x in re.findall(r"public", h, re.I)} == {"public"} and "--public-url" in h
    src = inspect.getsource(__import__("abf_platform.mcp_server", fromlist=["x"]).run_http)
    assert not re.search(r"ssl|cert", src, re.I) and list(inspect.signature(
        __import__("abf_platform.mcp_server", fromlist=["x"]).run_http).parameters) == ["index_path", "host", "port", "public_url"]


def test_tcf03_f04_the_users_table_has_no_role_and_both_labs_see_the_same(tmp_path):
    # TC-F03, TC-F04
    st = _store()
    t = _tokens(tmp_path)
    p1 = st.create_token(t, kind="pat", user_id=st.create_user(t, "alice", "lab-a"))
    p2 = st.create_token(t, kind="pat", user_id=st.create_user(t, "bob", "lab-b"))
    assert [r[1] for r in _rows(t, "PRAGMA table_info(users)")] == ["id", "name", "lab", "created_at", "disabled_at",
                                                                  "password_hash"]    # 009c: the one new column, the web password hash; still no role
    plat, _ = _three_runs(tmp_path / "x")
    t2 = plat.tokens
    ua, ub = st.create_user(t2, "alice", "lab-a"), st.create_user(t2, "bob", "lab-b")
    q1 = st.create_token(t2, kind="pat", user_id=ua)
    q2 = st.create_token(t2, kind="pat", user_id=ub)
    from test_station_platform import make_ce
    make_ce(plat, owner_user_id=ua)                              # 116: an environment is its owner's
    make_ce(plat, name="lab-b", agent="a2", owner_user_id=ub)
    calls = [(n, {}) for n in ("list_runs", "list_compute_envs", "list_agents")] + [("get_compute_env", {"name": "lab-b"})]
    env = pkg_env(ABF_PLATFORM_DB=plat.index)
    port = free_port()
    proc = start_cli(["mcp", "--http", "--port", str(port)], env, tmp_path / "m.log")
    try:
        wait_port(port, proc=proc)
        _, a = mcp_http_call("http://127.0.0.1:%d/mcp" % port, calls, token=q1)
        _, b = mcp_http_call("http://127.0.0.1:%d/mcp" % port, calls, token=q2)
    finally:
        stop_proc(proc)
    # 116: this was "both labs see the same"; no lab shares anything now: each sees its own environment and neither sees the other's
    assert [e["name"] for e in tool_json(a[1])["compute_envs"]] == ["lab-a"]
    assert [e["name"] for e in tool_json(b[1])["compute_envs"]] == ["lab-b"]
    assert tool_json(a[0]) == tool_json(b[0]) == {"runs": []}      # the three runs have no launch record, so they are nobody's here
    assert tool_json(a[3])["found"] is False and tool_json(b[3])["name"] == "lab-b"


def test_tcf05_a_pat_does_not_expire_and_there_is_no_rotate(tmp_path):
    # TC-F05
    pat, _ = _pat(tmp_path)
    assert _rows(_tokens(tmp_path), "SELECT expires_at FROM tokens WHERE kind = 'pat'") == [(None,)]
    st = _store()
    import os
    os.environ["ABF_PLATFORM_CLOCK_OFFSET"] = str(366 * 86400)
    try:
        assert st.lookup_pat(_tokens(tmp_path), pat) is not None
    finally:
        del os.environ["ABF_PLATFORM_CLOCK_OFFSET"]
    h = run_cli(["pat", "--help"]).stdout
    for word in ("new", "list", "revoke"):
        assert word in h
    assert not re.search(r"rotat|renew|extend", h, re.I)
    u = run_cli(["user", "--help"]).stdout
    assert "add" in u and not re.search(r"disable|remove|delete|edit", u, re.I)


def test_tcd14_tool_bodies_stay_one_call_with_caller_and_read_the_http_auth_context():
    # TC-D14
    tree = ast.parse((PKG / "mcp_server.py").read_text(encoding="utf-8"))
    build = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "build_server"][0]
    tools = [n for n in ast.walk(build) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not build]
    assert len(tools) == 6
    for fn in tools:
        assert len(fn.body) == 1 and isinstance(fn.body[0], ast.Return), fn.name
        call = fn.body[0].value
        call = call.value if isinstance(call, ast.Await) else call
        assert isinstance(call.func, ast.Attribute) and call.func.value.id == "actions" and call.func.attr == fn.name
        kw = {k.arg: k.value for k in call.keywords}
        # 116: the two run tools also say where the hand-off record is (a run is its launcher's), by the one name the server was built with
        assert list(kw) == (["caller", "platform_path"] if fn.name in ("list_runs", "get_run") else ["caller"])
        assert isinstance(kw["caller"], ast.Call) and kw["caller"].func.id == "_caller"
        assert "platform_path" not in kw or (isinstance(kw["platform_path"], ast.Name) and kw["platform_path"].id == "platform_path")
        assert not [n for n in ast.walk(fn) if isinstance(n, (ast.If, ast.Try, ast.For, ast.While))]


def test_tcf06_no_login_routes_and_no_cookie(tmp_path):
    # TC-F06
    plat = Platform(tmp_path / "p", clock=Clock())
    assert not [r.path for r in plat.app.routes if re.search(r"login|logout|session", getattr(r, "path", ""))]
    pat, _ = _pat(tmp_path / "q")
    port, proc = _start_http(tmp_path / "q")
    try:
        for r in (_post(port), _post(port, "Bearer " + pat)):
            assert "set-cookie" not in r.headers
    finally:
        stop_proc(proc)
