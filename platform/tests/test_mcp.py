# Nothing existing: tests of this folder's two read-only MCP tools, driven with the official SDK client over stdio and Streamable HTTP.
"""MCP server tests (feature 008, FR-007)."""
import hashlib
import re
import sys

from abf_platform import status
from helpers import (H, Platform, assert_loopback_only, free_port, load_scenario, mcp_call,
                     mcp_http_call, pkg_env, start_cli, stop_proc, tool_json, tool_text, variant,
                     wait_port)

BASE = 1_790_000_000.0


def _three_runs(tmp_path):
    plat = Platform(tmp_path / "plat", clock=lambda: __import__("time").time())
    token = plat.new_token()
    names = []
    # three runs with different start times, deliberately created out of start order
    for i, (scenario, off) in enumerate((("ok_run", 100), ("fail_run", 300), ("ok_resume", 200))):
        name = "run_%d" % i
        names.append((name, off))
        reqs = variant(scenario, name, "00000000-0000-0000-0000-00000000000%d" % i, BASE + off)
        plat.replay(reqs, token)
    return plat, names


def test_tc020_list_runs_is_newest_first_with_name_status_start_and_progress(tmp_path):
    # TC-020
    plat, names = _three_runs(tmp_path)
    tools, outs = mcp_call(pkg_env(ABF_PLATFORM_DB=plat.index), [("list_runs", {})])
    runs = tool_json(outs[0])["runs"]
    assert [r["name"] for r in runs] == ["run_1", "run_2", "run_0"]
    for r in runs:
        assert r["status"] in ("succeeded", "failed")
        assert r["started_at"]
        assert {"total", "succeeded", "cached", "failed"} <= set(r["tasks"])
    assert runs[0]["status"] == "failed" and runs[1]["tasks"]["cached"] == 7


def test_tc022_unknown_run_id_is_a_clear_answer_not_an_error(tmp_path):
    # TC-022
    plat, _ = _three_runs(tmp_path)
    missing = "deadbeefdeadbeef"
    _, outs = mcp_call(pkg_env(ABF_PLATFORM_DB=plat.index),
                       [("get_run", {"run_id": missing}), ("list_runs", {})])
    assert not outs[0].is_error
    text = tool_text(outs[0])
    assert missing in text and re.search(r"not found|找不到", text)
    assert len(tool_json(outs[1])["runs"]) == 3


def test_tc024_exactly_two_read_only_tools(tmp_path):
    # TC-024 (and the tool half of TC-060)
    plat, _ = _three_runs(tmp_path)
    tools, _ = mcp_call(pkg_env(ABF_PLATFORM_DB=plat.index), [])
    assert sorted(t.name for t in tools) == ["get_run", "list_runs"]
    for t in tools:
        assert t.annotations is not None
        assert t.annotations.read_only_hint is True
        assert t.annotations.destructive_hint is not True
        assert not re.search(r"launch|cancel|delete|clean|write", t.name)


def test_tc025_streamable_http_gives_the_same_answers_on_loopback(tmp_path):
    # TC-025
    plat, _ = _three_runs(tmp_path)
    env = pkg_env(ABF_PLATFORM_DB=plat.index)
    wid = status.list_runs(plat.index, __import__("time").time())[0]["id"]
    calls = [("list_runs", {}), ("get_run", {"run_id": wid}), ("get_run", {"run_id": "deadbeefdeadbeef"})]
    _, via_stdio = mcp_call(env, calls)
    port = free_port()
    proc = start_cli(["mcp", "--http", "--port", str(port)], env, tmp_path / "mcp.log")
    try:
        wait_port(port, proc=proc)
        tools, via_http = mcp_http_call("http://127.0.0.1:%d/mcp" % port, calls)
        assert sorted(t.name for t in tools) == ["get_run", "list_runs"]
        assert_loopback_only(port)
    finally:
        stop_proc(proc)
    for a, b in zip(via_stdio, via_http):
        assert tool_json(a) == tool_json(b)
    assert tool_json(via_http[1])["id"] == wid


def test_tc026_the_mcp_view_uses_the_same_lost_rule(tmp_path):
    # TC-026: a run without complete, the receiver stopped, the clock of the MCP server pushed forward.
    plat = Platform(tmp_path / "plat", clock=lambda: __import__("time").time())
    token = plat.new_token()
    plat.replay(load_scenario("heartbeat_run")["requests"], token, stop_before="heartbeat")
    wid = status.list_runs(plat.index, __import__("time").time())[0]["id"]
    for offset, want in ((20, "running"), (3 * H + 1 + 20, "lost")):
        env = pkg_env(ABF_PLATFORM_DB=plat.index, ABF_PLATFORM_CLOCK_OFFSET=offset)
        _, outs = mcp_call(env, [("list_runs", {}), ("get_run", {"run_id": wid})])
        assert tool_json(outs[0])["runs"][0]["status"] == want
        assert tool_json(outs[1])["status"] == want


def test_tc043_mcp_answers_hold_no_token_and_no_authorization(tmp_path):
    # TC-043 (MCP side)
    plat = Platform(tmp_path / "plat")
    token = plat.new_token()
    wid, _ = plat.replay(load_scenario("fail_run")["requests"], token)
    _, outs = mcp_call(pkg_env(ABF_PLATFORM_DB=plat.index), [("list_runs", {}), ("get_run", {"run_id": wid})])
    hashed = hashlib.sha256(token.encode()).hexdigest()
    for o in outs:
        t = tool_text(o)
        assert token not in t and hashed not in t and "authorization" not in t.lower()


def test_tc044_mcp_stderr_holds_no_token(tmp_path):
    # TC-044 (MCP side): read the server's stderr while it answers a call.
    import asyncio
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from helpers import mcp_stdio_params

    plat = Platform(tmp_path / "plat")
    token = plat.new_token()
    plat.replay(load_scenario("ok_run")["requests"], token)
    err = tmp_path / "mcp.err"

    async def go():
        with open(err, "w") as f:
            async with stdio_client(mcp_stdio_params(pkg_env(ABF_PLATFORM_DB=plat.index)), errlog=f) as (r, w):
                async with ClientSession(r, w) as s:
                    await s.initialize()
                    await s.call_tool("list_runs", {})

    asyncio.run(go())
    text = err.read_text()
    assert token not in text and "authorization" not in text.lower()
