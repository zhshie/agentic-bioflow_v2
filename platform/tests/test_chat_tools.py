# Nothing existing: tests of the list of platform tools the browser chat may offer its model (014a); the rule of which tool may be offered is ours.
"""014a: abf_platform.actions.chat_tools. Test cases are named in the comments (TC-001 ...), see specs/014a-chat-backend/test-case.md."""
import ast
import asyncio
import re

import pytest

from helpers import PLATFORM_DIR, tool_json
from human_harness import World
from resume_harness import Rig

CHAT_TOOLS = PLATFORM_DIR / "abf_platform" / "actions" / "chat_tools.py"
BANNED_WORDS = re.compile(r"approve|confirm|confirmed_by|void|yes", re.I)
READ_ONLY = {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"}
REQUESTS = {"launch", "cancel", "resume", "relaunch", "forget"}


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


def chat_tools():
    from abf_platform.actions import chat_tools as m
    return m


def server_tools(tmp_path):
    from abf_platform.mcp_server import build_server
    return asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())


def specs(tmp_path):
    return asyncio.run(chat_tools().tool_specs(str(tmp_path / "index.db"), None))


def offered_by_rule(tools):
    req = chat_tools().REQUEST_TOOLS
    return {t.name for t in tools if (t.annotations is not None and t.annotations.read_only_hint is True) or t.name in req}


def test_tc001_tc034_the_list_is_what_the_server_has_and_is_read_only_or_a_request_tool(tmp_path):
    # TC-001, TC-034
    names = {s["name"] for s in specs(tmp_path)}
    assert names == offered_by_rule(server_tools(tmp_path)) == READ_ONLY | REQUESTS


def test_tc009_every_spec_is_in_the_claude_tool_format(tmp_path):
    # TC-009
    for s in specs(tmp_path):
        assert set(s) == {"name", "description", "input_schema"}, s
        assert isinstance(s["name"], str) and s["name"]
        assert isinstance(s["description"], str) and s["description"]
        assert isinstance(s["input_schema"], dict) and s["input_schema"].get("type") == "object"


def test_tc020_the_list_is_derived_not_copied(tmp_path):
    # TC-020
    by = {t.name: t for t in server_tools(tmp_path)}
    for s in specs(tmp_path):
        assert s["description"] == by[s["name"]].description
        assert s["input_schema"] == by[s["name"]].input_schema


def test_tc021_the_list_is_cached_per_process(tmp_path, monkeypatch):
    # TC-021
    from abf_platform import mcp_server
    first = specs(tmp_path)

    def boom(*a, **k):
        raise AssertionError("the server was built again")
    monkeypatch.setattr(mcp_server, "build_server", boom)
    assert specs(tmp_path) == first


def test_tc002_nothing_in_the_list_can_say_yes(tmp_path):
    # TC-002
    for s in specs(tmp_path):
        assert not BANNED_WORDS.search(s["name"]), s["name"]
        for prop in s["input_schema"].get("properties", {}):
            assert not BANNED_WORDS.search(prop), (s["name"], prop)


def _fake_tool(name, read_only):
    from mcp_types import Tool, ToolAnnotations
    return Tool(name=name, description="x", input_schema={"type": "object", "properties": {}},
                annotations=ToolAnnotations(read_only_hint=read_only))


def test_tc007_an_unclassified_tool_makes_classify_check_raise_and_names_it(tmp_path):
    # TC-007
    tools = list(server_tools(tmp_path)) + [_fake_tool("wipe_everything", False)]
    with pytest.raises(Exception) as e:
        chat_tools().classify_check(tools)
    assert "wipe_everything" in str(e.value)


def test_tc008_the_real_tools_are_all_classified(tmp_path):
    # TC-008
    chat_tools().classify_check(server_tools(tmp_path))


def test_tc007b_tool_specs_also_raises_when_a_new_tool_appears(tmp_path, monkeypatch):
    # TC-007 (the list itself is guarded too: classify_check is not an unused function)
    from abf_platform import mcp_server
    real = mcp_server.build_server

    def with_extra(*a, **k):
        server = real(*a, **k)
        orig = server.list_tools

        async def more():
            return list(await orig()) + [_fake_tool("wipe_everything", False)]
        server.list_tools = more
        return server
    monkeypatch.setattr(mcp_server, "build_server", with_extra)
    with pytest.raises(Exception):
        asyncio.run(chat_tools().tool_specs(str(tmp_path / "fresh.db"), None))


def test_tc025_the_progress_tools_are_offered_and_read_only(tmp_path):
    # TC-025
    by = {t.name: t for t in server_tools(tmp_path)}
    names = {s["name"] for s in specs(tmp_path)}
    for n in ("list_runs", "get_run"):
        assert n in names and by[n].annotations.read_only_hint is True


# ---- the source of the module ------------------------------------------------------------------------------------

def _identifiers(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, ast.alias):
            out.update(n.name.split("."))
            if n.asname:
                out.add(n.asname)
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.update(n.module.split("."))
    return out


def test_tc003_the_module_names_no_yes_channel_and_no_key():
    # TC-003
    src = CHAT_TOOLS.read_text(encoding="utf-8")
    ids = _identifiers(ast.parse(src))
    assert not ids & {"TERMINAL", "ELICITED", "PAGE"}, ids
    # Narrowed 2026-10-19 (plan revision): the one helper `confirm_dialog` legitimately has "confirm" in its name; it only builds a dict.
    # Everything else must still not name approve/confirm, which keeps any import or call of the human channel's functions out.
    assert not [i for i in ids if re.search(r"approve|confirm", i, re.I) and i != "confirm_dialog"], ids
    assert "anthropic" not in ids
    assert "api_key" not in src


def test_tc035_the_module_imports_no_model_provider_and_no_network_client():
    # TC-035
    tree = ast.parse(CHAT_TOOLS.read_text(encoding="utf-8"))
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split(".")[0])
    assert not mods & {"anthropic", "openai", "httpx", "requests", "aiohttp", "urllib", "socket"}, mods


def test_tc005_tc022_tc023_tc024_the_system_prompt():
    # TC-005, TC-022, TC-023, TC-024
    p = chat_tools().CHAT_SYSTEM_PROMPT
    assert isinstance(p, str) and p.strip()
    assert "送出" in p and "確認送出嗎" in p and "按" in p
    assert "資料" in p and "指令" in p
    assert "一句" in p and "工具" in p
    for n in ("list_runs", "get_run", "launch"):
        assert n in p


def test_tc033_tc034_the_prompt_names_the_canvas_reads_and_says_no_banned_word():
    # TC-033, TC-034 (canvas-mcp-read, 13-1)
    p = chat_tools().CHAT_SYSTEM_PROMPT
    line = [l for l in p.splitlines() if "find_module" in l]
    assert len(line) == 1 and "模組" in line[0] and "pipeline" in line[0] and "list_pipelines" in line[0]
    assert not BANNED_WORDS.search(p)


# ---- the request tools only ask ------------------------------------------------------------------------------------

def test_tc004_launch_without_a_person_leaves_one_pending_request_and_no_job(w):
    # TC-004 (as test_tch09_nothing_reaches_the_queue_through_the_tools_without_a_person)
    ann = w.user("ann")
    w.hand_over()
    out = w.launch(caller=ann, run="run-two")
    assert out["sent"] is False and out["state"] == "pending" and out["confirmation_url"] and out["summary"], out
    assert w.jobs() == []
    assert [r["state"] for r in w.confirmations()] == ["pending"]
    out = w.launch(caller=None, run="run-three")
    assert out["sent"] is False
    assert w.jobs() == []


def _pending_shape(**over):
    d = {"sent": False, "state": "pending", "confirmation_url": "/confirm/abc", "summary": "送出 run-x"}
    d.update(over)
    return d


def test_tc050_confirm_dialog_on_a_real_pending_launch_result_and_the_queue_stays_empty(w):
    # TC-050 (plan revision 2026-10-19, item 3 "TC-030")
    ann = w.user("ann")
    w.hand_over()
    out = w.launch(caller=ann, run="run-two")
    d = chat_tools().confirm_dialog("launch", out)
    assert d == {"question": "確認送出嗎？", "tool": "launch", "summary": out["summary"],
                 "confirmation_url": out["confirmation_url"], "buttons": ["確認", "取消"]}, d
    assert w.jobs() == []
    assert [r["state"] for r in w.confirmations()] == ["pending"]


def test_tc051_confirm_dialog_is_none_for_read_only_tools_and_non_pending_results():
    # TC-051 (plan "TC-031")
    cd = chat_tools().confirm_dialog
    for n in READ_ONLY:
        assert cd(n, _pending_shape()) is None, n
    assert cd("launch", _pending_shape(sent=True)) is None
    assert cd("launch", _pending_shape(state="done")) is None
    assert cd("launch", _pending_shape(confirmation_url="")) is None
    assert cd("launch", {"ok": False}) is None


def test_tc052_every_request_tool_gets_a_dialog_and_it_holds_no_yes_value():
    # TC-052 (plan "TC-032")
    cd = chat_tools().confirm_dialog
    for n in chat_tools().REQUEST_TOOLS:
        d = cd(n, _pending_shape())
        assert d and d["tool"] == n and d["buttons"] == ["確認", "取消"], n
        assert set(d) == {"question", "tool", "summary", "confirmation_url", "buttons"}
        assert not [k for k in d if re.search(r"approve|yes|confirmed", k, re.I)], d


def test_tc053_the_source_scan_still_passes_with_the_helper_in_place():
    # TC-053 (plan "TC-033"): confirm_dialog exists and TC-003's narrowed scan accepts it
    assert callable(chat_tools().confirm_dialog)
    test_tc003_the_module_names_no_yes_channel_and_no_key()


def launched(rig, caller, run, status):
    """A first launch by this user through the tool (so its samples lie in the user's folder), handed over, with its end in the index."""
    from human_harness import form_answer
    out = tool_json(rig.w.call("launch", rig.w.in_area(caller, rig.w.choices(run=run)), caller=caller, answer=form_answer()))
    assert out["sent"] is True, out
    rig.hand_over(out["job_id"], run)
    rig.set_run(run, status)
    return out


def test_tc026_cancel_resume_relaunch_without_a_person_only_ask(rig):
    # TC-026
    w = rig.w
    ann = w.user("ann")
    launched(rig, ann, "failed-run", "failed")
    launched(rig, ann, "live-run", None)
    for tool, run in (("cancel", "live-run"), ("resume", "failed-run"), ("relaunch", "failed-run")):
        before = rig.counts()
        out = tool_json(w.call(tool, {"run_name": run}, caller=ann))
        assert out.get("sent") is False and out.get("confirmation_url"), (tool, out)
        after = rig.counts()
        assert after[0] == before[0] and after[2] == before[2], (tool, before, after)   # no job, no launches row
        assert after[1] == before[1] + 1, (tool, before, after)                          # one pending request
        assert rig.sql("SELECT state FROM confirmations ORDER BY created_at DESC, id DESC LIMIT 1")[0][0] == "pending"
    assert not rig.sql("SELECT * FROM jobs WHERE kind = 'cancel_run'")


def test_tc006_forget_without_a_person_deletes_nothing(rig):
    # TC-006
    w = rig.w
    ann = w.user("ann")
    launched(rig, ann, "run-one", "succeeded")

    def tables():
        return ([tuple(r) for r in rig.sql("SELECT * FROM confirmations ORDER BY id")],
                [tuple(r) for r in rig.sql("SELECT * FROM jobs ORDER BY id")])
    before = tables()
    out = tool_json(w.call("forget", {"run_name": "run-one"}, caller=ann))
    assert out["ok"] is False, out
    assert tables() == before


# ---- what this slice must not have built ------------------------------------------------------------------------------

def _py_files():
    for sub in ("abf_platform", "abf_launch", "abf_station"):
        yield from (PLATFORM_DIR / sub).rglob("*.py")


def test_tc030_nothing_in_the_platform_takes_a_model_key(tmp_path):
    # TC-030
    for f in _py_files():
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.arg):
                assert n.arg.lower().replace("_", "") != "apikey", (f, n.arg)
    for s in specs(tmp_path):
        for prop in s["input_schema"].get("properties", {}):
            assert prop.lower().replace("_", "") != "apikey", (s["name"], prop)


def test_tc031_no_anthropic_sdk():
    # TC-031
    for name in ("pyproject.toml", "constraints.txt"):
        assert "anthropic" not in (PLATFORM_DIR / name).read_text(encoding="utf-8").lower(), name
    for f in _py_files():
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Import):
                assert not [a for a in n.names if a.name.split(".")[0] == "anthropic"], f
            elif isinstance(n, ast.ImportFrom):
                assert (n.module or "").split(".")[0] != "anthropic", f


def test_tc033_the_web_app_has_no_chat_route_and_no_key_page(w):
    # TC-033
    def paths(routes):
        for r in routes:
            if hasattr(r, "path"):
                yield r.path
            yield from paths(getattr(r, "routes", None) or [])
    found = list(paths(w.web().app.routes))
    assert found, "no routes found, the scan would pass for nothing"
    assert not [p for p in found if re.search(r"chat|model|apikey|api-key", p, re.I)], found
