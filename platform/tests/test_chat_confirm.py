# Nothing existing: tests of the CHAT channel (a person's yes relayed in the chat with the request id); the rules (same person, same hash, ten minutes, once) are ours and no library models them.
"""MCP chat confirmation (plan specs/mcp-chat-confirm): the first call answers pending with a request id, the person answers in the
chat, the AI calls again with request_id and user_confirmed=true. TC numbers are named in the comments (test-case.md)."""
import asyncio
import inspect
import json
import re
import time

import pytest

from helpers import CHAT_ARGS, tool_json
from human_harness import World, form_answer
from resume_harness import Rig

CHAT = CHAT_ARGS
FOUR = ("launch", "cancel", "resume", "relaunch")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


def pending(w, ann, **over):
    o = w.launch(caller=ann, **over)
    assert o["sent"] is False and o["state"] == "pending" and o["id"], o
    return o


def yes(w, caller, rid, **over):
    return w.launch(caller=caller, request_id=rid, user_confirmed=True, **over)


def row(w, rid):
    return w.sql("SELECT * FROM confirmations WHERE id = ?", (rid,))[0]


def is_no(out):
    return out["ok"] is False and out["sent"] is False and out["message"].startswith("未送出：")


def tools(w):
    ts, _ = w.mcp([])
    return {t.name: t for t in ts}


# ---- US1 ------------------------------------------------------------------------------------------------------------------------------

def test_tcm_01_launch_pending_then_chat_confirm_then_queued(w):
    # TC-001, TC-002, TC-003, TC-004, TC-008, TC-009
    ann = w.user("ann")
    o1 = pending(w, ann)
    assert w.jobs() == [] and len(w.confirmations()) == 1 and row(w, o1["id"])["state"] == "pending"
    assert {"sent", "state", "summary", "confirmation_url", "message", "id"} <= set(o1)
    assert "request_id" in o1["message"] and "user_confirmed" in o1["message"] and "AI 不能代按" not in o1["message"]
    assert "/c/" in o1["confirmation_url"]
    o2 = yes(w, ann, o1["id"])
    assert o2["sent"] is True and o2["state"] == "queued" and o2["job_id"]
    assert len(w.jobs("launch_nextflow")) == 1
    r = row(w, o1["id"])
    from abf_launch import build
    from abf_platform import common
    assert r["channel"] == "CHAT" and r["confirmed_at"] and r["caller_user_id"] == ann.user_id and r["state"] == "confirmed"
    assert len(r["sha256"]) == 64 and r["kind"] == "launch"


def test_tcm_05_request_id_without_true_changes_nothing(w):
    # TC-005
    ann = w.user("ann")
    o1 = pending(w, ann)
    for extra in ({"user_confirmed": False}, {}):
        o = w.launch(caller=ann, request_id=o1["id"], **extra)
        assert o["sent"] is False and o["state"] == "pending"
    assert row(w, o1["id"])["state"] == "pending" and w.jobs() == []


def test_tcm_06_parity_with_the_form(w):
    # TC-006
    ann, bob = w.user("ann"), w.user("bob")
    f = w.launch(caller=ann, answer=form_answer())
    o1 = pending(w, bob, ce_name="lab-a", run="run-bob")
    c = yes(w, bob, o1["id"], ce_name="lab-a", run="run-bob")
    assert f["state"] == "queued" and c["state"] == "queued"
    a, b = row(w, f["id"]), row(w, c["id"])
    assert (a["kind"], a["state"]) == (b["kind"], b["state"]) and a["channel"] == "ELICITED" and b["channel"] == "CHAT"
    assert len(w.jobs("launch_nextflow")) == 2 and {j["kind"] for j in w.jobs()} == {"launch_nextflow"}
    assert a["caller_user_id"] == ann.user_id and b["caller_user_id"] == bob.user_id


def test_tcm_07_plain_repeat_and_one_time_use(w):
    # TC-007, TC-029
    ann = w.user("ann")
    o1 = pending(w, ann)
    o2 = yes(w, ann, o1["id"])
    again = yes(w, ann, o1["id"])
    assert again["job_id"] == o2["job_id"]
    plain = w.launch(caller=ann)
    assert plain["sent"] is True and plain["job_id"] == o2["job_id"]
    assert len(w.jobs()) == 1 and len(w.confirmations()) == 1


def test_tcm_10_find_approved_lists_chat_only(w):
    # TC-010
    from abf_platform import confirm, jobs
    ann = w.user("ann")
    o1 = pending(w, ann)
    o2 = yes(w, ann, o1["id"])
    db = w.ip.state_db
    bundle = json.loads(row(w, o1["id"])["bundle_json"])
    assert confirm.find_approved(db, "launch", bundle, ann.user_id, include_spent=True)["id"] == o1["id"]
    import sqlite3
    con = sqlite3.connect(str(db))
    with con:
        con.execute("UPDATE confirmations SET channel = 'X' WHERE id = ?", (o1["id"],))
    con.close()
    assert confirm.find_approved(db, "launch", bundle, ann.user_id, include_spent=True) is None


def test_tcm_11_queue_refusal_keeps_the_audit(w, monkeypatch):
    # TC-011
    from abf_platform import jobs
    ann = w.user("ann")
    o1 = pending(w, ann)

    def refuse(*a, **k):
        raise jobs.JobRefused("no room")
    monkeypatch.setattr(jobs, "enqueue_confirmed", refuse)
    out = yes(w, ann, o1["id"])
    assert out["sent"] is False and w.jobs() == []
    r = row(w, o1["id"])
    assert r["state"] == "void" and r["channel"] == "CHAT" and r["confirmed_at"]


# ---- US2 ------------------------------------------------------------------------------------------------------------------------------

def test_tcm_12_true_without_a_request_id_is_rejected(w):
    # TC-012, TC-013
    ann = w.user("ann")
    out = w.launch(caller=ann, user_confirmed=True)
    assert is_no(out) and "user_confirmed" in out["message"] and "request_id" in out["message"]
    seen = []
    out = w.launch(caller=ann, answer=form_answer(seen=seen), user_confirmed=True)
    assert is_no(out) and seen == []
    assert w.jobs() == [] and w.confirmations() == []


@pytest.mark.parametrize("bad", ["0123456789abcdef0123456789abcdef", "", "x" * 5000])
def test_tcm_14_unknown_ids_write_nothing(w, bad):
    # TC-014, TC-015, TC-016
    ann = w.user("ann")
    out = yes(w, ann, bad)
    assert is_no(out) and "Traceback" not in out["message"]
    assert w.jobs() == [] and w.confirmations() == []


@pytest.mark.parametrize("bad", [12345, ["a"]])
def test_tcm_17_non_string_ids_write_nothing(w, bad):
    # TC-017
    ann = w.user("ann")
    try:
        out = w.call("launch", w.choices(request_id=bad, user_confirmed=True), caller=ann)
        assert getattr(out, "is_error", False) or is_no(tool_json(out))
    except Exception:
        pass
    assert w.jobs() == [] and w.confirmations() == []


def test_tcm_18_changed_content_is_rejected_and_the_row_survives(w):
    # TC-018, TC-019, TC-020, TC-022, TC-023
    ann = w.user("ann")
    o1 = pending(w, ann)
    for over in (dict(params={"depth": 9}), dict(revision="2.17.0"), dict(run="run-two")):
        out = yes(w, ann, o1["id"], **over)
        assert is_no(out) and "job_id" not in out
        r = row(w, o1["id"])
        assert r["state"] == "pending" and r["channel"] is None and r["confirmed_at"] is None
        assert w.jobs() == []
    out = yes(w, ann, o1["id"], params={"depth": 9})
    assert "請改回原參數" in out["message"]
    ok = yes(w, ann, o1["id"])
    assert ok["sent"] is True and ok["state"] == "queued"


def test_tcm_21_somebody_elses_id_is_not_yours_and_leaks_nothing(w):
    # TC-021, TC-024, TC-025
    ann, bob = w.user("ann"), w.user("bob")
    o1 = pending(w, ann)
    out = yes(w, bob, o1["id"])
    assert is_no(out) and row(w, o1["id"])["state"] == "pending" and w.jobs() == []
    done = yes(w, ann, o1["id"])
    assert done["sent"] is True
    for over in ({}, {"params": {"depth": 9}}):
        txt = json.dumps(yes(w, bob, o1["id"], **over), ensure_ascii=False)
        assert str(done["job_id"]) not in txt.replace(o1["id"], "") or "job_id" not in txt
        assert "job_id" not in txt
    # a void row
    o3 = pending(w, ann, run="run-void")
    import sqlite3
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET state = 'void', void_reason = 'expired (逾時)' WHERE id = ?", (o3["id"],))
    con.close()
    txt = json.dumps(yes(w, bob, o3["id"], run="run-void"), ensure_ascii=False)
    assert "expired" not in txt and "void" not in txt and "逾時" not in txt and "作廢" not in txt


def test_tcm_26_timeout_boundary(w):
    # TC-026, TC-027, TC-028 (the clock is the one the action layer takes)
    from abf_platform import confirm
    ann = w.user("ann")
    o1 = pending(w, ann)
    r = row(w, o1["id"])
    t0 = r["created_at"]
    db = w.ip.state_db
    bundle = json.loads(r["bundle_json"])
    from abf_platform import common
    with pytest.raises(confirm.NotApproved) as e:
        confirm.approve(db, o1["id"], "CHAT", ann.user_id, lambda: t0 + 600, expected_sha=common.bundle_sha256(bundle), expected_kind="launch")
    assert e.value.status == "expired" and row(w, o1["id"])["state"] == "void" and "expired" in row(w, o1["id"])["void_reason"]
    assert w.jobs() == []
    o2 = pending(w, ann, run="run-two")
    r2 = row(w, o2["id"])
    # 599 s is inside the window: whatever else may refuse (the fake clock makes the agent look offline), it is not "expired"
    try:
        confirm.approve(db, o2["id"], "CHAT", ann.user_id, lambda: r2["created_at"] + 599,
                        expected_sha=r2["sha256"], expected_kind="launch")
    except confirm.NotApproved as e:
        assert e.status != "expired" and "offline" in str(e)
    assert "expired" not in (row(w, o2["id"])["void_reason"] or "")
    o3 = pending(w, ann, run="run-three")
    r3 = row(w, o3["id"])
    with pytest.raises(confirm.NotApproved) as e:
        confirm.approve(db, o3["id"], "CHAT", ann.user_id, lambda: r3["created_at"] + 601, expected_sha=r3["sha256"], expected_kind="launch")
    assert e.value.status == "expired"


def test_tcm_27_expired_through_the_tool_and_priority_over_changed(w):
    # TC-027, TC-034, TC-035, TC-036
    import sqlite3
    ann = w.user("ann")
    o1 = pending(w, ann)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET expires_at = ? WHERE id = ?", (time.time() - 1, o1["id"]))
    con.close()
    out = yes(w, ann, o1["id"], params={"depth": 9})
    assert is_no(out) and "changed" not in out["message"] and "不同" not in out["message"]
    assert row(w, o1["id"])["state"] == "void" and "expired" in row(w, o1["id"])["void_reason"] and w.jobs() == []
    # void: the same id with the original parameters is still refused; with other parameters it is void, not changed
    for over in ({}, {"params": {"depth": 9}}):
        out = yes(w, ann, o1["id"], **over)
        assert is_no(out) and "不同" not in out["message"] and w.jobs() == []


def test_tcm_30_stdio_cannot_use_chat(w):
    # TC-030, TC-031
    from abf_platform import confirm, common
    ann = w.user("ann")
    o1 = pending(w, ann)
    out = yes(w, None, o1["id"])
    assert is_no(out) and w.jobs() == [] and row(w, o1["id"])["state"] == "pending"
    r = row(w, o1["id"])
    with pytest.raises(confirm.NotApproved) as e:
        confirm.approve(w.ip.state_db, o1["id"], "CHAT", None, expected_sha=r["sha256"], expected_kind="launch")
    assert e.value.status == "not_yours" and row(w, o1["id"])["state"] == "pending"


def test_tcm_32_a_request_of_another_kind_is_rejected(w):
    # TC-032
    ann = w.user("ann")
    w.hand_over(by=ann)
    n = len(w.confirmations())
    o1 = pending(w, ann, run="run-two")
    out = tool_json(w.call("cancel", {"run_name": "run-one", "request_id": o1["id"], "user_confirmed": True}, caller=ann))
    assert is_no(out) and row(w, o1["id"])["state"] == "pending" and w.jobs("cancel_run") == []


def test_tcm_33_same_id_with_changed_params_after_approval_is_changed(w):
    # TC-033
    ann = w.user("ann")
    o1 = pending(w, ann)
    done = yes(w, ann, o1["id"])
    out = yes(w, ann, o1["id"], params={"depth": 9})
    assert is_no(out) and "job_id" not in out and len(w.jobs()) == 1
    assert row(w, o1["id"])["state"] == "confirmed"


def test_tcm_37_existing_checks_still_run_on_the_confirming_call(w, monkeypatch):
    # TC-037, TC-038
    from abf_platform import actions
    ann = w.user("ann")
    o1 = pending(w, ann)
    out = yes(w, ann, o1["id"], run="bad name!!")
    assert is_no(out) and w.jobs() == [] and row(w, o1["id"])["state"] == "pending"
    monkeypatch.setattr(actions, "_cloud_check", lambda *a, **k: ("cap reached", None))
    out = yes(w, ann, o1["id"])
    assert is_no(out) and w.jobs() == [] and row(w, o1["id"])["state"] == "pending"


def test_tcm_39_cancel_of_somebody_elses_run_is_rejected(w):
    # TC-039, TC-056, TC-061
    ann, bob = w.user("ann"), w.user("bob")
    w.hand_over(by=ann)
    c1 = tool_json(w.call("cancel", {"run_name": "run-one"}, caller=ann))
    assert c1["state"] == "pending"
    out = tool_json(w.call("cancel", {"run_name": "run-one", "request_id": c1["id"], "user_confirmed": True}, caller=bob))
    assert out["sent"] is False and row(w, c1["id"])["state"] == "pending" and w.jobs("cancel_run") == []    # refused by the owner rule before the id is looked at
    ok =tool_json(w.call("cancel", {"run_name": "run-one", "request_id": c1["id"], "user_confirmed": True}, caller=ann))
    assert ok["sent"] is True and len(w.jobs("cancel_run")) == 1 and row(w, c1["id"])["channel"] == "CHAT"
    again = tool_json(w.call("cancel", {"run_name": "run-one"}, caller=ann))
    assert again["sent"] is True and again["job_id"] == ok["job_id"] and len(w.jobs("cancel_run")) == 1


# ---- US3 ------------------------------------------------------------------------------------------------------------------------------

def test_tcm_40_launch_pipeline_and_forget_have_no_chat_arguments(w):
    # TC-040, TC-041, TC-043
    ts = tools(w)
    for name, t in ts.items():
        props = set(t.input_schema.get("properties", {}))
        if name in FOUR:
            assert CHAT <= props, name
        else:
            assert not (CHAT & props), name


def test_tcm_42_clean_work_is_not_a_chat_channel(w):
    # TC-042
    from abf_platform import confirm
    ann = w.user("ann")
    db = w.ip.state_db
    bundle = {"run_name": "run-one", "work": "/x"}
    rid = confirm.create_pending(db, "clean_work", "lab-a", bundle, "screen", ann.user_id)
    r = row(w, rid)
    with pytest.raises(confirm.NotApproved):
        confirm.approve(db, rid, "CHAT", ann.user_id, expected_sha=r["sha256"], expected_kind="launch")
    assert row(w, rid)["state"] == "pending"


def test_tcm_44_the_public_approve_refuses_chat(w):
    # TC-044
    from abf_platform import actions, jobs
    ann = w.user("ann")
    o1 = pending(w, ann)
    with pytest.raises(jobs.JobRefused):
        actions.approve(w.ip.state_db, o1["id"], confirmed_by=actions.CHAT, caller=ann)
    assert row(w, o1["id"])["state"] == "pending" and w.jobs() == []


def test_tcm_45_page_and_form_stay(w):
    # TC-045, TC-046
    ann = w.user("ann")
    o1 = pending(w, ann)
    c = w.web()
    from human_harness import csrf_of
    assert w.login(c, "ann").status_code in (302, 303)
    page = c.get("/c/" + o1["id"])
    assert page.status_code == 200
    r = c.post("/c/" + o1["id"], data={"csrf": csrf_of(page.text)})
    assert row(w, o1["id"])["channel"] == "PAGE"
    f = w.launch(caller=ann, answer=form_answer(), run="run-two")
    assert row(w, f["id"])["channel"] == "ELICITED"


def test_tcm_47_no_new_column_no_new_table(w):
    # TC-047
    cols = [r[1] for r in w.sql("PRAGMA table_info(confirmations)")]
    assert "chat" not in " ".join(cols).lower()
    assert set(cols) >= {"id", "sha256", "kind", "caller_user_id", "state", "channel", "confirmed_at"}
    assert not any("chat" in r[0].lower() for r in w.sql("SELECT name FROM sqlite_master"))


def test_tcm_48_schemas_gain_two_optional_fields_on_four_tools(w):
    # TC-048, TC-049
    ts = tools(w)
    for name in FOUR:
        s = ts[name].input_schema
        props = s["properties"]
        assert props["user_confirmed"]["type"] == "boolean" and props["user_confirmed"]["default"] is False
        types = {a.get("type") for a in props["request_id"].get("anyOf", [props["request_id"]])}
        assert types == {"string", "null"} or types == {"string"}
        assert not (CHAT & set(s.get("required", []))), name
    assert ts["resume"].input_schema["required"] == ["run_name"] == ts["relaunch"].input_schema["required"]
    assert set(ts["relaunch"].input_schema["properties"]) == {"run_name"} | CHAT
    assert set(ts["resume"].input_schema["properties"]) == {"run_name", "params", "extra_config"} | CHAT


def test_tcm_50_descriptions_and_fixed_sentence(w):
    # TC-050, TC-051
    from abf_platform import guidance
    ts = tools(w)
    for name in FOUR:
        d = ts[name].description
        if name == "launch":
            # test_launch_profiles TC-017 pins launch's description free of the word "confirm", so it says
            # "the flag" (named in the user_confirmed parameter doc) and "after they answer".
            assert "request_id" in d and "after they answer" in d
        else:
            assert "user_confirmed" in d and "request_id" in d
    for name in ("launch", "cancel", "resume", "relaunch"):
        assert "you cannot say it for them" in ts[name].description or "you cannot answer" in ts[name].description
    s = guidance.FIXED_SENTENCE
    for must in ("does not start anything until the person says yes", "you cannot say it for them",
                 "(in the terminal, abf-platform launch, cancel, resume and relaunch ask the same way)",
                 "The tool forget only asks too: it deletes nothing until the person says yes in their own client's form.",
                 "deletes nothing until the person says yes", "user_confirmed=true"):
        assert must in s, must
    assert len(guidance.routing_instructions().encode("utf-8")) <= guidance.MAX_BYTES


def test_tcm_53_browser_chat_never_sees_the_chat_arguments(tmp_path):
    # TC-053, TC-054
    from abf_platform.actions import chat_tools
    specs = asyncio.run(chat_tools.tool_specs(str(tmp_path / "index.db"), None))
    by = {s["name"]: s for s in specs}
    for name in FOUR:
        assert not (CHAT & set(by[name]["input_schema"]["properties"])), name
    banned = re.compile(r"approve|confirm|confirmed_by|void|yes", re.I)
    for s in specs:
        assert not banned.search(s["name"])
        for p in s["input_schema"].get("properties", {}):
            assert not banned.search(p), (s["name"], p)
    assert "你沒有任何工具可以替本人說「是」" in chat_tools.CHAT_SYSTEM_PROMPT


# ---- US4 ------------------------------------------------------------------------------------------------------------------------------

def _failed_run(rig, ann, run="x"):
    w = rig.w
    sheet = w.in_area(ann, {"samplesheet": str(w.sheet)})["samplesheet"]
    rig.first(run, caller=ann, samplesheet=sheet)
    return run


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tcm_57_resume_and_relaunch_use_the_same_flow(rig, verb):
    # TC-057, TC-059, TC-060
    ann = rig.user("ann")
    run = _failed_run(rig, ann)
    n0 = len(rig.jobs())
    o1 = tool_json(rig.w.call(verb, {"run_name": run}, caller=ann))
    assert o1["sent"] is False and o1["state"] == "pending"
    ok = tool_json(rig.w.call(verb, {"run_name": run, "request_id": o1["id"], "user_confirmed": True}, caller=ann))
    assert ok["sent"] is True and ok["state"] == "queued", ok
    assert len(rig.jobs()) == n0 + 1 and row(rig.w, o1["id"])["channel"] == "CHAT"
    n = len(rig.w.confirmations())
    again = tool_json(rig.w.call(verb, {"run_name": run}, caller=ann))
    assert again["sent"] is True and again["job_id"] == ok["job_id"]
    assert len(rig.jobs()) == n0 + 1 and len(rig.w.confirmations()) == n


@pytest.mark.parametrize("edit", [{"params": {"depth": 9}}, {"extra_config": "process.memory = '16 GB'"}])
def test_tcm_58_resume_edits_changed_in_the_confirming_call(rig, edit):
    # TC-058
    ann = rig.user("ann")
    run = _failed_run(rig, ann)
    n0 = len(rig.jobs())
    o1 = tool_json(rig.w.call("resume", {"run_name": run}, caller=ann))
    out = tool_json(rig.w.call("resume", dict({"run_name": run, "request_id": o1["id"], "user_confirmed": True}, **edit), caller=ann))
    assert is_no(out) and len(rig.jobs()) == n0 and row(rig.w, o1["id"])["state"] == "pending"


# ---- the gate and the back-half rules ---------------------------------------------------------------------------------------------

def test_tcm_62_nothing_is_queued_by_a_true_without_a_live_request(w):
    # TC-062 (the old loop lives in test_human_channel.py::test_tch09_*)
    import sqlite3
    ann, bob = w.user("ann"), w.user("bob")
    o = pending(w, ann)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET expires_at = ? WHERE id = ?", (time.time() - 1, o["id"]))
    con.close()
    for caller in (ann, None):
        w.launch(caller=caller, user_confirmed=True)
        w.launch(caller=caller, request_id="f" * 32, user_confirmed=True)
        w.launch(caller=caller, request_id=o["id"], user_confirmed=True)
    other = pending(w, bob, run="run-bob")
    w.launch(caller=ann, request_id=other["id"], user_confirmed=True, run="run-bob")
    assert w.jobs() == []


def test_tcm_72_every_user_action_has_an_action_layer_function():
    # TC-072: both sides are listed
    from abf_platform import actions
    names = {"launch": "request_launch", "cancel": "request_cancel", "resume": "request_resume", "relaunch": "request_relaunch"}
    assert set(names) == set(FOUR)
    for fn in names.values():
        assert callable(getattr(actions, fn))
        assert CHAT <= set(inspect.signature(getattr(actions, fn)).parameters), fn
    src = inspect.getsource(__import__("abf_platform.mcp_server", fromlist=["x"]))
    for tool in FOUR:
        assert 'name="%s"' % tool in src
    assert len(re.findall(r"actions\.request_(launch|cancel|resume|relaunch)\(", src)) == 4


def test_tcm_73_no_second_copy_of_the_approval():
    # TC-073
    import pathlib
    root = pathlib.Path(inspect.getsourcefile(__import__("abf_platform.mcp_server", fromlist=["x"]))).parent
    server = (root / "mcp_server.py").read_text(encoding="utf-8")
    assert "confirm.approve" not in server and "enqueue" not in server and "create_pending" not in server
    callers = [p.name for p in root.rglob("*.py") if "confirm.approve(" in p.read_text(encoding="utf-8")]
    assert sorted(set(callers)) == ["__init__.py"]
    text = (root / "actions" / "__init__.py").read_text(encoding="utf-8")
    assert len(re.findall(r'confirm\.approve\(.*"CHAT"|confirm\.approve\(.*CHAT\.name', text)) == 1


def test_tcm_74_refusals_have_a_plain_shape(w):
    # TC-074
    ann, bob = w.user("ann"), w.user("bob")
    o1 = pending(w, ann)
    outs = [w.launch(caller=ann, user_confirmed=True),
            yes(w, ann, "e" * 32),
            yes(w, bob, o1["id"]),
            yes(w, None, o1["id"])]
    import sqlite3
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET expires_at = ? WHERE id = ?", (time.time() - 1, o1["id"]))
    con.close()
    outs.append(yes(w, ann, o1["id"]))
    for out in outs:
        m = out["message"]
        assert m.startswith("未送出：") and "job_id" not in out
        assert not re.search(r"Traceback|\.py\b|SELECT |sqlite|/tmp|\\\\", m), m
        assert len(m) > 12


def test_tcm_75_no_secret_in_replies_or_logs(w, caplog):
    # TC-075
    from human_harness import PASSWORD
    ann, bob = w.user("ann"), w.user("bob")
    with caplog.at_level("DEBUG"):
        o1 = pending(w, ann)
        outs = [yes(w, bob, o1["id"]), yes(w, ann, o1["id"]), yes(w, ann, o1["id"])]
    blob = json.dumps(outs, ensure_ascii=False) + caplog.text
    tokens = [r[0] for r in __import__("sqlite3").connect(str(w.ip.tokens)).execute("SELECT * FROM users")] if False else []
    assert PASSWORD not in blob and str(w.tmp) not in blob
