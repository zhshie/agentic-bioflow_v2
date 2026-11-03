# New for mcp-contract-tests: in-memory contract tests of the write tools (zero side effect on one unconfirmed call) and of one error path per tool.
# The world is the repo's own: resume_harness.Rig (a World with an environment, an agent, and runs made by the terminal's first launch),
# the tools are called with the SDK's in-memory Client, which does not declare elicitation: nobody says yes.
"""Contract tests of the MCP write tools and error paths (TC-009..015)."""
import json

import pytest

from helpers import tool_json, tool_text
from resume_harness import Rig

WRITE_TOOLS = ["cancel", "forget", "launch", "relaunch", "resume"]

# Real write points of the action layer: a call that is only a question must never reach one of them.
FORBIDDEN = [("abf_platform.confirm", "approve"), ("abf_platform.actions", "approve"), ("abf_platform.actions", "launch"),
             ("abf_platform.actions", "cancel"), ("abf_platform.actions", "forget"), ("abf_platform.jobs", "enqueue_confirmed"),
             ("abf_platform.jobs", "enqueue_launch"), ("abf_platform.jobs", "enqueue_cancel")]


def tools_of(index):
    import test_mcp_contract_tools as T
    return T.fetch_tools(index)


def test_write_tools_derived_from_annotations_equal_explicit_list(plat):
    # TC-009
    derived = sorted(t["name"] for t in tools_of(plat.index) if not t["readOnly"])
    assert derived == WRITE_TOOLS, "write tools (readOnlyHint false) differ from the tested list: %s" % derived


def make_rig(tmp_path, monkeypatch):
    rig = Rig(tmp_path, monkeypatch)
    rig.first("run-c", status=None, slurm=4242)        # still running: something to cancel
    rig.first("run-f", status="succeeded")             # finished: something to forget
    rig.first("run-r", status="failed")                # failed: something to resume or relaunch
    return rig


def call_args(rig, tool):
    return {"launch": lambda: rig.w.choices(run="run-new"), "cancel": lambda: {"run_name": "run-c"}, "forget": lambda: {"run_name": "run-f"},
            "resume": lambda: {"run_name": "run-r"}, "relaunch": lambda: {"run_name": "run-r"}}[tool]()


def dump(rig):
    return {t: [tuple(r) for r in rig.sql("SELECT * FROM %s ORDER BY 1" % t)] for t in ("jobs", "launches", "confirmations")}


def one_unconfirmed_call(tmp_path, monkeypatch, tool):
    rig = make_rig(tmp_path, monkeypatch)
    before = dump(rig)
    import importlib
    hits = []
    for mod, name in FORBIDDEN:
        m = importlib.import_module(mod)
        assert hasattr(m, name), "write point %s.%s is gone: update FORBIDDEN" % (mod, name)
        monkeypatch.setattr(m, name, lambda *a, _n=name, **k: hits.append(_n))
    _, outs = rig.w.mcp([(tool, call_args(rig, tool))])
    return rig, before, dump(rig), outs[0], hits


@pytest.mark.parametrize("tool", WRITE_TOOLS)
def test_write_tool_called_once_has_no_side_effect(tmp_path, monkeypatch, tool):
    # TC-010
    rig, before, after, out, hits = one_unconfirmed_call(tmp_path, monkeypatch, tool)
    assert not hits, "%s reached a write point of the action layer: %s" % (tool, hits)
    assert after["jobs"] == before["jobs"], "%s changed the jobs table (a command for the site)" % tool
    assert after["launches"] == before["launches"], "%s changed the launches table" % tool
    old = before["confirmations"]
    assert after["confirmations"][:len(old)] == old or all(r in after["confirmations"] for r in old), "%s changed an old confirmation" % tool
    new = [r for r in after["confirmations"] if r not in old]
    assert len(new) <= 1, "%s made %d confirmations" % (tool, len(new))
    cols = [d[1] for d in rig.sql("PRAGMA table_info(confirmations)")]
    for r in new:
        assert dict(zip(cols, r))["state"] == "pending", "%s left a confirmation that is not pending" % tool
    # nothing was queued for the site and no run's kept content went away
    assert rig.sql("SELECT COUNT(*) FROM jobs WHERE state != 'done'")[0][0] == 0
    assert all(r[0] is None for r in rig.sql("SELECT forgotten_at FROM confirmations"))


@pytest.mark.parametrize("tool", WRITE_TOOLS)
def test_write_tool_reply_says_not_sent(tmp_path, monkeypatch, tool):
    # TC-011
    rig, _, _, out, _ = one_unconfirmed_call(tmp_path, monkeypatch, tool)
    d = tool_json(out)
    text = tool_text(out)
    if tool == "forget":
        assert d.get("forgotten") is False and d.get("ok") is False
    else:
        assert d.get("sent") is False and d.get("ok") is False
    assert "abf-platform" in text or "http" in text, "the answer does not say what to do instead: %s" % text
    for claim in ("已啟動", "已取消", "已刪除", "已送出", "已續跑", "已重跑", "has been started", "was launched", "was cancelled", "was deleted"):
        assert claim not in text


# ---- TC-012..015: one error path per tool --------------------------------------------------------------------------------------------------
# A call that must fail for every tool; None: the tool takes no argument, so it has no input that can fail (its answer is only checked to be clean).
ERROR_INPUTS = {
    "list_runs": None, "list_compute_envs": None, "list_agents": None, "list_used_pipelines": None, "list_pipelines": None,
    "get_run": {"run_id": "nope-run-zz"},
    "get_compute_env": {"name": "no-such-env"},
    "list_site_files": {"compute_env": "no-such-env", "path": "."},
    "my_usage": {"month": "nope-month"},
    "run_outputs": {"run_id": "nope-run-zz"},
    "read_run_file": {"run_id": "nope-run-zz", "path": "nope.txt"},
    "read_task_log": {"run_name": "nope-run-zz", "task": "nope-task", "which": "out"},
    "find_module": {"q": ""},
    "describe_module": {"name": "nope_module_zz"},
    "get_pipeline": {"pipeline_id": 999999},
    "get_validation": {"pipeline_id": 999999},
    "launch": {"pipeline": "nope/pipe", "revision": "0", "run_name": "nope-run-zz", "samplesheet_text": "a,b\n1,2\n", "ce_name": "no-such-env"},
    "cancel": {"run_name": "nope-run-zz"},
    "forget": {"run_name": "nope-run-zz"},
    "resume": {"run_name": "nope-run-zz"},
    "relaunch": {"run_name": "nope-run-zz"},
}

# Product gaps found by this test, one per tool (the message lacks the name of the failed object or a next step). They are listed in the
# ledger for the maintainer; strict, so the day the product is fixed the mark must come off. Nothing under abf_platform/ was changed.
GAPS = {}

# What an answer must not show: stack, internals, paths, secrets.
LEAKS = ["Traceback", 'File "', '.py"', "sqlite3", "SELECT ", "/home", "/tmp", "/var/", "/Users", "/mnt/", "C:\\", "Bearer "]


def raised_error(result):
    d = tool_json(result)
    return bool(result.is_error or d.get("ok") is False or d.get("found") is False or "error" in d or d.get("state") in ("notfound", "no_form"))


def run_error_call(tmp_path, monkeypatch, tool, args):
    from abf_platform import store
    rig = make_rig(tmp_path, monkeypatch)
    uid = store.create_user(rig.w.ip.tokens, "tc012", "lab")
    pat = store.create_token(rig.w.ip.tokens, kind="pat", user_id=uid)
    _, outs = rig.w.mcp([(tool, args)])
    return outs[0], tool_text(outs[0]), pat


def assert_clean(text, pat, tmp_path):
    for bad in LEAKS + [pat, str(tmp_path)]:
        assert bad not in text, "the answer shows %r: %s" % (bad, text[:400])


def test_error_inputs_cover_every_tool(plat):
    # TC-012: nothing escapes the error-path table
    assert sorted(ERROR_INPUTS) == sorted(t["name"] for t in tools_of(plat.index))


@pytest.mark.parametrize("tool", sorted(ERROR_INPUTS))
def test_error_path_is_clean_for_every_tool(tmp_path, monkeypatch, tool):
    # TC-013: whatever the answer says, it shows no stack, SQL, path or secret (no xfail may hide a leak here)
    args = ERROR_INPUTS[tool]
    result, text, pat = run_error_call(tmp_path, monkeypatch, tool, args or {})
    if args is None:
        assert not result.is_error
    assert_clean(text, pat, tmp_path)


@pytest.mark.parametrize("tool", [pytest.param(t, marks=pytest.mark.xfail(strict=True, reason=GAPS[t])) if t in GAPS else t
                                  for t in sorted(ERROR_INPUTS)])
def test_error_path_is_actionable_and_clean(tmp_path, monkeypatch, tool):
    # TC-012 and TC-013: an error that names what failed and says what to do next, with nothing from inside
    args = ERROR_INPUTS[tool]
    result, text, pat = run_error_call(tmp_path, monkeypatch, tool, args or {})
    assert_clean(text, pat, tmp_path)
    if args is None:
        return                              # no argument, no failing input: the answer is an empty list, checked clean above
    assert raised_error(result), "%s did not report the failure: %s" % (tool, text[:300])
    name = next(v for v in args.values() if isinstance(v, str) and v)
    assert name in text, "%s: the message does not name %r: %s" % (tool, name, text[:300])
    assert any(w in text for w in ("請", "用", "先")), "%s: the message does not say what to do next: %s" % (tool, text[:300])


def test_xfail_marks_are_for_known_tools_only(plat):
    # TC-015: a mark for a tool that is gone would hide nothing but would rot
    assert set(GAPS) <= set(ERROR_INPUTS)


@pytest.mark.parametrize("tool", [t for t in sorted(ERROR_INPUTS)])
def test_missing_required_param_is_rejected_without_stack(tmp_path, monkeypatch, tool):
    # TC-014: the SDK refuses a call that leaves out a required argument; the refusal is no stack
    rig = make_rig(tmp_path, monkeypatch)
    schema = next(t for t in tools_of(rig.w.ip.index) if t["name"] == tool)["inputSchema"]
    if not schema.get("required"):
        pytest.skip("%s has no required argument" % tool)
    _, outs = rig.w.mcp([(tool, {})])
    text = tool_text(outs[0])
    assert outs[0].is_error, "%s accepted a call without %s: %s" % (tool, schema["required"], text[:300])
    for bad in ("Traceback", 'File "', '.py"', "sqlite3", "SELECT "):
        assert bad not in text
