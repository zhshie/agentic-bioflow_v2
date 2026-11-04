# New for mcp-contract-tests: the remote-site tool over a real HTTP transport (past bug: site tools failing under HTTP, the 421 Invalid Host case).
# The server is a child process on a free port, as test_mcp.py::test_tc025 starts it; nothing runs uvicorn in the test process.
"""HTTP-transport contract tests of the MCP server (TC-016..018)."""
import contextlib
import json
import urllib.error
import urllib.request

import pytest

from helpers import free_port, mcp_http_call, pkg_env, start_cli, stop_proc, tool_json, tool_text, wait_port
from resume_harness import Rig


@contextlib.contextmanager
def http_server(tmp_path, monkeypatch):
    """A running `abf-platform mcp --http` on a free port over a world with one environment and no online agent; yields (url, pat, rig)."""
    from abf_platform import store
    rig = Rig(tmp_path, monkeypatch)
    uid = store.create_user(rig.w.ip.tokens, "tc016", "lab")
    pat = store.create_token(rig.w.ip.tokens, kind="pat", user_id=uid)
    import sqlite3
    con = sqlite3.connect(str(rig.state))
    con.execute("UPDATE agents SET last_seen_at = 0")        # no agent of the site is online
    con.commit()
    con.close()
    port = free_port()
    log = tmp_path / "mcp-http.log"
    proc = start_cli(["mcp", "--http", "--port", str(port)], pkg_env(ABF_PLATFORM_DB=rig.w.ip.index), log)
    try:
        try:
            wait_port(port, proc=proc)
        except RuntimeError as e:
            proc.poll()
            raise AssertionError("the HTTP server did not come up (%s); end of its log:\n%s" % (e, log.read_text(errors="replace")[-1500:]))
        yield "http://127.0.0.1:%d/mcp" % port, pat, rig
    finally:
        stop_proc(proc)


def slow_http_call(url, calls, token):
    """mcp_http_call with a patient client: a site tool waits for the agent up to its deadline, longer than the default 5 s read timeout."""
    import asyncio
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    async def go():
        http = httpx2.AsyncClient(headers={"Authorization": "Bearer " + token}, timeout=httpx2.Timeout(120.0))
        async with Client(streamable_http_client(url, http_client=http)) as client:
            return [await client.call_tool(n, a) for n, a in calls]

    return asyncio.run(go())


def test_site_tools_over_http(tmp_path, monkeypatch):
    # TC-016: list_site_files over real HTTP answers (loading / offline), it is not a 500 and not a dropped connection
    with http_server(tmp_path, monkeypatch) as (url, pat, rig):
        outs = slow_http_call(url, [("list_site_files", {"compute_env": "lab-a", "path": "/data"})], pat)
    d = tool_json(outs[0])
    text = tool_text(outs[0])
    assert "Traceback" not in text and 'File "' not in text
    assert d.get("state") in ("loading", "offline", "unavailable", "error", "no_agent", "not_ready", "expired") or d.get("ok") is False or "error" in d, \
        "list_site_files over HTTP gave an unexpected answer: %s" % text[:300]


def test_http_and_inproc_list_the_same_tools(tmp_path, monkeypatch):
    # TC-017: the names offered over HTTP equal the names offered in process
    with http_server(tmp_path, monkeypatch) as (url, pat, rig):
        http_tools, _ = mcp_http_call(url, [], token=pat)
        inproc_tools, _ = rig.w.mcp([])
    assert sorted(t.name for t in http_tools) == sorted(t.name for t in inproc_tools)


def test_http_without_token_is_401(tmp_path, monkeypatch):
    # TC-018: no token, no entry; the body shows no stack
    with http_server(tmp_path, monkeypatch) as (url, pat, rig):
        req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(),
                                     headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req, timeout=10)
        body = e.value.read().decode(errors="replace")
    assert e.value.code == 401
    assert "Traceback" not in body and 'File "' not in body
