# Nothing existing: tests of the platform side of a resume that carries edits (build, screen, actions, MCP, chat, CLI); the rules of resume-edit-params-b are ours.
"""resume-edit-params-b: a resume may carry `params` (keys to change) and `extra_config` (settings text).
Test cases are named in the comments (TC-001 ...), see specs/resume-edit-params-b/test-case.md."""
import asyncio
import copy
import inspect
import json
import re
import time

import pytest

from helpers import tool_json
from human_harness import csrf_of, form_answer, pending_id_of
from launch_harness import Pty, cli_argv
from resume_harness import SESSION, FakePerson, Rig
from test_launch_cli import parts
from test_launch_platform import make_confirmation

QUESTION_RESUME = "確定續跑？(y/N)"
NOT_FOUND = "找不到這個 run (Run not found): %s"
PLAIN_SENTENCE = "這是續跑：同一個資料夾，沿用已完成的 task；樣本和參數不變"
EDITED_SENTENCE = "這是續跑：同一個資料夾；下面的參數與設定有改，用到它們的 task 會重新跑，其餘已完成的 task 沿用"
NOTE_SENTENCE = "這次的改動是疊在第一次送出的參數上，前一次續跑的改動不會帶過來"
START = {"min_reads": 50, "primer": "A"}
MEM = "process.memory = '16 GB'"
CHANGED = "內容與確認時不符"


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


@pytest.fixture
def duo(rig):
    from owner_harness import Duo
    return Duo(rig.w)


def first(rig, run="x", **kw):
    return rig.first(run, params=dict(START), **kw)


def build_resume(rig, run="x", owner=None, area=None, **edits):
    from abf_launch import build
    return build.prepare_resume(rig.state, run, index_path=rig.index, owner=owner, area=area, **edits)


def screen_of(bundle, row):
    from abf_launch import build
    return build.as_text(build.resume_screen(bundle, row))


def ask(rig, run="x", params=None, extra_config=None, caller=None, person=None, remote=False):
    from abf_platform import actions
    return asyncio.run(actions.request_resume(rig.state, run_name=run, params=params, extra_config=extra_config, caller=caller, person=person,
                                              remote=remote, index_path=rig.index))


def refused(out):
    assert out["ok"] is False and out["sent"] is False, out
    return out["message"]


def first_http(rig, duo, caller, run="x", **params):
    out = duo.sent(caller, run=run)
    rig.hand_over(out["job_id"], run)
    rig.set_run(run, "failed", SESSION)
    return out


# ---- build and screen --------------------------------------------------------------------------------------------------------------

def test_prepare_resume_with_params_builds_overrides_and_keeps_the_origin(rig):
    # TC-005, TC-011
    f = first(rig)
    ce, b, row = build_resume(rig, params={"min_reads": 100}, extra_config=MEM)
    assert list(b["files"]) == ["head-2.sh", "params-2.yaml", "extra-2.config"]
    assert b["resume"]["overrides"] == {"params": {"min_reads": 100}, "extra_config": MEM + "\n"}
    for k, v in f.items():
        assert b["resume"]["origin"][k] == v, k
    for name in ("samplesheet.csv", "params.yaml", "nextflow.config", "head.sh"):
        assert name not in b["files"]


@pytest.mark.parametrize("edits,expect", [
    ({"min_reads": 50, "primer": "B"}, {"primer": "B"}),
    ({"min_reads": 50.0}, {"min_reads": 50.0}),
    ({"min_reads": True}, {"min_reads": True}),
    ({"min_reads": "50"}, {"min_reads": "50"})])
def test_a_value_is_unchanged_only_when_type_and_value_are_both_the_same(rig, edits, expect):
    # TC-012
    first(rig)
    _, b, row = build_resume(rig, params=edits)
    assert b["resume"]["overrides"]["params"] == expect
    text = screen_of(b, row)
    assert ("參數 min_reads：" in text) == ("min_reads" in expect)


@pytest.mark.parametrize("edits", [dict(), dict(params={}), dict(extra_config=""), dict(params={}, extra_config=""),
                                   dict(params={"min_reads": 50, "primer": "A"}, extra_config=""), dict(params={"primer": "A"})])
def test_unchanged_values_are_dropped_and_nothing_left_is_a_plain_resume(rig, edits):
    # TC-052; the plain bundle is also kept to its old shape (the golden: nothing of the edits in it)
    from abf_platform import common
    first(rig)
    _, plain, prow = build_resume(rig)
    _, b, row = build_resume(rig, **edits)
    assert common.bundle_sha256(b) == common.bundle_sha256(plain) and b == plain
    assert "overrides" not in b["resume"] and list(b["files"]) == ["head-2.sh"]
    assert set(b) == {"version", "agent", "ce", "run_name", "run_folder", "files", "resume"}
    assert set(b["resume"]) == {"of_run", "of_slurm_job_id", "session_id", "attempt", "origin"}
    assert screen_of(b, row) == screen_of(plain, prow)


@pytest.mark.parametrize("params,extra", [([1], None), ("a=b", None), (None, 5), (None, ["x"])])
def test_params_must_be_a_mapping_and_extra_config_text(rig, params, extra):
    # TC-013
    first(rig)
    person = FakePerson(True)
    before = rig.counts()
    msg = refused(ask(rig, params=params, extra_config=extra, person=person))
    assert ("params" if params is not None else "extra_config") in msg and re.search(r"[一-鿿]", msg) and "must" in msg
    assert person.seen == [] and rig.counts() == before and rig.confirmations() == [c for c in rig.confirmations() if c["state"] != "pending"]


@pytest.mark.parametrize("edits,field,line", [
    ({"params": {"input": "x"}}, "input", None), ({"params": {"outdir": "x"}}, "outdir", None),
    ({"extra_config": "// ok\nincludeConfig 'x.config'\n"}, "extra_config", 2),
    ({"extra_config": 'process.memory = "${x}"'}, "extra_config", 1)])
def test_a_bad_param_or_extra_config_is_a_refusal_that_names_the_field(rig, edits, field, line):
    # TC-014, TC-015
    first(rig)
    person = FakePerson(True)
    before = rig.counts()
    msg = refused(ask(rig, person=person, **edits))
    assert field in msg and msg.startswith("未續跑")
    if line:
        assert "第 %d 行" % line in msg
    assert person.seen == [] and rig.counts() == before
    assert "Traceback" not in msg and "sqlite" not in msg.lower() and "/mnt/" not in msg and "File \"" not in msg


def test_refusals_over_http_do_not_carry_the_token(rig, duo):
    # TC-015
    first_http(rig, duo, duo.a)
    for edits in ({"params": {"input": "x"}}, {"extra_config": "includeConfig 'x'"}, {"params": [1]}):
        out = ask(rig, caller=duo.a, person=None, **edits)
        assert out["sent"] is False and "abf_" not in json.dumps(out)


def test_no_edit_can_remove_a_parameter(rig):
    # TC-016
    first(rig)
    _, b, _ = build_resume(rig, params={"min_reads": 100})
    assert 'primer: "A"' in b["files"]["params-2.yaml"]
    try:
        _, b, _ = build_resume(rig, params={"primer": None})
    except Exception as e:
        from abf_launch import build
        assert isinstance(e, build.Refusal)
    else:
        assert "primer" in b["files"]["params-2.yaml"] and b["resume"]["origin"]["params"]["primer"] == "A"


def test_screen_shows_the_param_diff_the_extra_config_and_the_real_last_line(rig):
    # TC-001, TC-002, TC-003, TC-004, TC-006, TC-007
    first(rig)
    _, b, row = build_resume(rig, params={"min_reads": 100, "new_flag": "on"}, extra_config=MEM)
    text = screen_of(b, row)
    assert "參數 min_reads：50 → 100" in text and "參數 new_flag：（新增）→ on" in text and "參數 primer" not in text
    assert "== extra-2.config ==" in text and MEM in text
    lastline = [ln for ln in b["files"]["head-2.sh"].split("\n") if ln][-1]
    shown = [ln for ln in text.split("\n") if ln.startswith("指令（head-2.sh 的最後一行）")]
    assert len(shown) == 1 and shown[0].endswith(lastline) and "params-2.yaml" in lastline and "-c extra-2.config" in lastline
    order = [text.index(s) for s in ("指令（head-2.sh", "參數 min_reads", "參數 new_flag", "== extra-2.config ==", "接續的 session", "== head-2.sh ==")]
    assert order == sorted(order)
    # only params: no config block and no config file; only a config: no parameter line
    _, b, row = build_resume(rig, params={"min_reads": 100})
    assert "extra-2.config" not in screen_of(b, row) and "extra-2.config" not in b["files"]
    _, b, row = build_resume(rig, extra_config=MEM)
    assert "參數 " not in screen_of(b, row)


def test_screen_swaps_the_fixed_sentence_only_when_overrides_exist(rig):
    # TC-008, TC-053
    first(rig)
    _, plain, prow = build_resume(rig)
    text = screen_of(plain, prow)
    assert PLAIN_SENTENCE in text and "→" not in text and "參數 " not in text and EDITED_SENTENCE not in text and NOTE_SENTENCE not in text
    _, b, row = build_resume(rig, params={"min_reads": 100})
    text = screen_of(b, row)
    assert EDITED_SENTENCE in text and NOTE_SENTENCE in text and "樣本和參數不變" not in text
    from abf_launch import build
    assert build.EDITED_SENTENCE == EDITED_SENTENCE


def test_screen_escapes_control_characters_in_changed_values(rig):
    # TC-009: the screen function is given a bundle whose value holds control characters (the station would refuse them earlier)
    first(rig)
    _, b, row = build_resume(rig, params={"min_reads": 100})
    b = copy.deepcopy(b)
    b["resume"]["overrides"]["params"]["min_reads"] = "a\x1b[31mred\nb\rc"
    text = screen_of(b, row)
    assert "\x1b" not in text and "\r" not in text
    lines = [ln for ln in text.split("\n") if ln.startswith("參數 min_reads")]
    assert len(lines) == 1 and "\\n" in lines[0]


def test_the_resume_screen_finds_its_script_by_attempt_number(rig):
    # TC-010
    first(rig)
    _, b, row = build_resume(rig, params={"min_reads": 100}, extra_config=MEM)
    b = copy.deepcopy(b)
    b["files"] = dict(reversed(list(b["files"].items())))
    text = screen_of(b, row)
    assert text.rstrip("\n").split("== head-2.sh ==")[-1].strip().splitlines()[-1].startswith("nextflow") or "nextflow run" in text.split("== head-2.sh ==")[-1]
    assert text.index("== head-2.sh ==") > text.index("接續的 session")


# ---- 116b and owners -------------------------------------------------------------------------------------------------------------

def test_a_path_param_outside_the_callers_uploads_is_refused_over_http(rig, duo):
    # TC-028
    first_http(rig, duo, duo.a)
    other = duo.area(duo.b) / "secret.txt"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text("x")
    person = FakePerson(True)
    before = rig.counts()
    msg = refused(ask(rig, params={"reference": str(other)}, caller=duo.a, person=person))
    assert "reference" in msg and "上傳資料夾" in msg
    assert person.seen == [] and rig.counts() == before


def test_a_path_param_inside_them_is_recorded_in_upload_paths(rig, duo):
    # TC-029 (a)
    first_http(rig, duo, duo.a)
    mine = duo.area(duo.a) / "ref.txt"
    mine.write_text("x")
    from abf_launch import build
    from abf_platform import actions
    _, b, _ = build_resume(rig, owner=duo.a.user_id, area=actions.caller_area(rig.state, duo.a), params={"reference": str(mine)})
    assert str(mine) in json.dumps(b["upload_paths"])
    _, plain, _ = build_resume(rig, owner=duo.a.user_id, area=actions.caller_area(rig.state, duo.a))
    assert str(mine) not in json.dumps(plain["upload_paths"])


def test_without_an_area_nothing_about_upload_paths_changes(rig):
    # TC-029 (b)
    first(rig)
    _, plain, _ = build_resume(rig)
    _, b, _ = build_resume(rig, params={"reference": "/some/where/ref.txt"})
    assert ("upload_paths" in b) == ("upload_paths" in plain)
    assert b["resume"]["overrides"]["params"] == {"reference": "/some/where/ref.txt"}


def test_an_edited_resume_is_still_owner_only_and_the_words_are_uniform(rig, duo):
    # TC-025, TC-026, TC-027
    first_http(rig, duo, duo.a)
    before = rig.counts()
    edits = dict(params={"min_reads": 100}, extra_config=MEM)
    mine = refused(ask(rig, "x", caller=duo.b, person=FakePerson(True), **edits))
    none = refused(ask(rig, "nope", caller=duo.b, person=FakePerson(True), **edits))
    assert NOT_FOUND % "x" in mine and NOT_FOUND % "nope" in none and mine.replace("x", "nope") == none
    assert rig.counts() == before
    # alice's pending request is invisible and cannot be answered by bob
    out = ask(rig, "x", caller=duo.a, person=None, **edits)
    assert out["state"] == "pending"
    rid = pending_id_of(out["confirmation_url"])
    c = rig.w.web()
    assert rig.w.login(c, "bob").status_code in (200, 303)
    page = c.get("/c/" + rid)
    assert "min_reads" not in page.text and MEM not in page.text and csrf_of(page.text) is None
    assert c.post("/c/" + rid, data={"csrf": "x"}).status_code == 403
    assert [r["state"] for r in rig.confirmations() if r["id"] == rid] == ["pending"] and len(rig.jobs()) == 1


def _patch_origin(monkeypatch, **extra):
    from abf_platform import jobs
    real = jobs.launch_content

    def fake(con, r, job):
        origin, sha = real(con, r, job)
        return dict(origin, **extra), sha
    monkeypatch.setattr(jobs, "launch_content", fake)


def test_composed_and_google_batch_runs_are_still_refused_with_edits(rig, monkeypatch):
    # TC-017
    from abf_launch import build
    first(rig)
    plain = {}
    with monkeypatch.context() as m:
        m.setattr(build, "is_gcb", lambda state, ce: True)
        for label, edits in (("plain", {}), ("edited", dict(params={"min_reads": 100}, extra_config=MEM))):
            msg = refused(ask(rig, person=FakePerson(True), **edits))
            plain.setdefault("gcb", msg)
            assert msg == plain["gcb"], label
    with monkeypatch.context() as m:
        _patch_origin(m, pipeline_source={"kind": "composed"})
        for label, edits in (("plain", {}), ("edited", dict(params={"min_reads": 100}, extra_config=MEM))):
            msg = refused(ask(rig, person=FakePerson(True), **edits))
            plain.setdefault("composed", msg)
            assert msg == plain["composed"], label
    assert plain["gcb"] != plain["composed"] and len(rig.jobs()) == 1


def test_request_resume_and_relaunch_take_only_the_edits_they_should():
    # TC-018, TC-030
    from abf_platform import actions
    assert list(inspect.signature(actions.request_resume).parameters) == [
        "platform_path", "run_name", "params", "extra_config", "caller", "person", "clock", "remote", "index_path"]
    assert list(inspect.signature(actions.request_relaunch).parameters) == [
        "platform_path", "run_name", "caller", "person", "clock", "remote", "index_path"]


# ---- the actions: asking twice, the yes, tampering --------------------------------------------------------------------------------------------

def test_edits_skip_find_attempt_and_a_plain_resume_still_uses_it(rig):
    # TC-019, TC-021, TC-022 (the find is by the edits themselves)
    first(rig)
    out = ask(rig, person=FakePerson(True))
    assert out["sent"] is True
    again = ask(rig, person=FakePerson(True))
    assert again["sent"] is True and again["job_id"] == out["job_id"] and len(rig.jobs()) == 2 and len(rig.confirmations()) == 2
    # an edited call after a plain one is not that plain attempt: it is refused by the "newest only" rule, naming it
    msg = refused(ask(rig, params={"min_reads": 100}, person=FakePerson(True)))
    assert "x-a2" in msg and re.search(r"較新|newer", msg)
    assert len(rig.jobs()) == 2


def test_the_same_edited_resume_twice_is_one_pending_request(rig, duo):
    # TC-020
    first_http(rig, duo, duo.a)
    edits = dict(params={"min_reads": 100}, extra_config=MEM)
    one = ask(rig, caller=duo.a, person=None, **edits)
    two = ask(rig, caller=duo.a, person=None, **edits)
    assert one["state"] == two["state"] == "pending" and one["confirmation_url"] == two["confirmation_url"]
    assert len([c for c in rig.confirmations() if c["state"] == "pending"]) == 1 and len(rig.jobs()) == 1


def test_after_the_yes_the_same_edited_call_gets_the_same_job_and_a_different_one_is_refused(rig):
    # TC-021, TC-022, TC-005
    first(rig)
    edits = dict(params={"min_reads": 100}, extra_config=MEM)
    out = ask(rig, person=FakePerson(True), **edits)
    assert out["sent"] is True and out["state"] == "queued"
    b = rig.bundle_of_job(out["job_id"])
    assert b["resume"]["overrides"] == {"params": {"min_reads": 100}, "extra_config": MEM + "\n"} and len(rig.jobs()) == 2
    person = FakePerson(True)
    same = ask(rig, person=person, **edits)
    assert same["sent"] is True and same["job_id"] == out["job_id"] and person.seen == []
    # the same edits written another way (the unchanged value is left in, a newline is added) are the same attempt
    same = ask(rig, person=FakePerson(True), params={"min_reads": 100, "primer": "A"}, extra_config=MEM + "\n")
    assert same["job_id"] == out["job_id"]
    # other edits: refused by the "newest only" rule, naming the one that exists
    msg = refused(ask(rig, person=FakePerson(True), params={"min_reads": 200}))
    assert "x-a2" in msg and re.search(r"較新|newer", msg)
    assert len(rig.jobs()) == 2 and len(rig.confirmations()) == 2


def test_a_second_different_edit_for_the_same_predecessor_is_refused(rig):
    # TC-022
    first(rig)
    assert ask(rig, person=FakePerson(True), params={"min_reads": 100})["sent"] is True
    msg = refused(ask(rig, person=FakePerson(True), params={"min_reads": 200}))
    assert "x-a2" in msg
    # and the other way round: a plain resume after an edited one is not the edited attempt either
    msg = refused(ask(rig, person=FakePerson(True)))
    assert "x-a2" in msg
    assert len(rig.jobs()) == 2


@pytest.mark.parametrize("path,value", [(("resume", "overrides", "params", "min_reads"), 999),
                                         (("resume", "overrides", "extra_config"), "process.memory = '99 GB'\n"),
                                         (("files", "params-2.yaml"), "min_reads: 1\n"),
                                         (("files", "extra-2.config"), "process.memory = '1 GB'\n")])
def test_the_yes_for_an_edited_resume_is_for_exactly_that_content(rig, path, value):
    # TC-023
    from abf_platform import jobs
    first(rig)
    ce, b, _ = build_resume(rig, params={"min_reads": 100}, extra_config=MEM)
    cid = make_confirmation(rig.state, "launch", b)
    t = copy.deepcopy(b)
    node = t
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(jobs.JobRefused, match=CHANGED):
        jobs.enqueue_launch(rig.state, ce, t, cid)
    assert len(rig.jobs()) == 1
    assert jobs.enqueue_launch(rig.state, ce, b, cid)


def test_nothing_is_written_before_a_yes_and_a_decline_writes_nothing(rig):
    # TC-024
    first(rig)
    before = rig.counts()
    person = FakePerson(False)
    out = ask(rig, params={"min_reads": 100}, extra_config=MEM, person=person)
    assert out["sent"] is False and len(rig.jobs()) == 1 and rig.counts()[0] == before[0] and rig.counts()[2] == before[2]
    assert [c["state"] for c in rig.confirmations() if c["state"] == "confirmed"] == [c["state"] for c in rig.confirmations()[:1]]
    assert len(person.seen) == 1 and "參數 min_reads：50 → 100" in person.seen[0]


def test_a_request_made_before_overrides_existed_is_resumed_as_it_was(rig):
    # TC-054: an unanswered request without `overrides` still gets its yes and its job
    from abf_platform import actions
    first(rig)
    out = ask(rig, person=FakePerson(True))
    b = rig.bundle_of_job(out["job_id"])
    assert "overrides" not in b["resume"] and out["state"] == "queued"
    assert actions.find_approved(rig.state, "launch", b) is not None


def test_request_helpers_add_no_new_names_with_resume_or_relaunch_in_them():
    # TC-031 (the scan of the repository is test_keep_submissions TC-084; this is the layer's own list)
    from abf_platform import actions
    names = sorted(n for n in dir(actions) if re.search(r"resume|relaunch", n, re.I))
    assert names == ["request_relaunch", "request_resume"]


# ---- MCP and chat ----------------------------------------------------------------------------------------------------------------------

def test_mcp_resume_takes_run_name_and_two_optional_fields_and_relaunch_still_only_one(rig):
    # TC-032, TC-033
    tools, _ = rig.w.mcp([])
    t = {x.name: x for x in tools}
    assert sorted(t) == ["cancel", "forget", "get_compute_env", "get_run", "launch", "list_agents", "list_compute_envs", "list_runs",
                         "list_site_files", "list_used_pipelines", "my_usage", "read_task_log", "relaunch", "resume", "run_outputs"]
    yes = {"yes", "y", "confirm", "confirmed", "approve", "approved", "force", "送出", "kind", "command", "script"}
    assert set(t["resume"].input_schema["properties"]) == {"run_name", "params", "extra_config"}
    assert set(t["relaunch"].input_schema["properties"]) == {"run_name"}
    for name in ("resume", "relaunch"):
        assert t[name].input_schema.get("required") == ["run_name"]
        assert not set(t[name].input_schema["properties"]) & yes
        assert t[name].annotations.read_only_hint is False and t[name].annotations.destructive_hint is False
        assert "does not start anything until the person says yes" in t[name].description
    d = t["resume"].description
    assert "params" in d and "extra_config" in d and "process.memory = '16 GB'" in d and "new launch" in d


def test_mcp_resume_with_extra_fields_still_drops_revision_samplesheet_ce_and_session(rig):
    # TC-034
    f = first(rig)
    _, outs = rig.w.mcp([("resume", {"run_name": "x", "params": {"primer": "OTHER"}, "revision": "9.9.9", "samplesheet": "/etc/passwd",
                                      "ce_name": "elsewhere", "session_id": "ffffffff-4f50-4a6b-8c7d-9e0f1a2b3c4d"})], answer=form_answer())
    if outs[0].is_error:
        assert len(rig.jobs()) == 1
        return
    out = tool_json(outs[0])
    if out.get("sent"):
        b = rig.bundle_of_job(out["job_id"])
        assert b["resume"]["overrides"]["params"] == {"primer": "OTHER"}
        assert b["resume"]["origin"]["revision"] == "2.18.0" and b["resume"]["session_id"] == SESSION and "samplesheet" not in b
        assert b["ce"] == f["ce"]
    else:
        assert len(rig.jobs()) == 1


def test_mcp_resume_with_edits_queues_a_job_only_after_the_form_is_accepted(rig, duo):
    # TC-035, TC-036, TC-037
    first(rig)
    seen = []
    args = {"run_name": "x", "params": {"min_reads": 100}, "extra_config": MEM}
    declined = tool_json(rig.w.call("resume", args, answer=form_answer(action="decline", seen=seen)))
    assert declined["sent"] is False and len(rig.jobs()) == 1
    n = rig.counts()
    seen = []
    bad = tool_json(rig.w.call("resume", {"run_name": "x", "params": {"input": "x"}}, answer=form_answer(seen=seen)))      # a refusal is plain words: no form, no request
    assert bad["sent"] is False and "input" in bad["message"] and seen == [] and rig.counts() == n
    seen = []
    out = tool_json(rig.w.call("resume", args, answer=form_answer(seen=seen)))
    assert out["sent"] is True and out["state"] == "queued" and out["job_id"] and len(rig.jobs()) == 2
    assert len(seen) == 1 and "參數 min_reads：50 → 100" in seen[0].message and MEM in seen[0].message and "nextflow run" in seen[0].message


def test_mcp_resume_over_http_without_a_form_answers_pending(rig, duo):
    # TC-036 (b)
    first_http(rig, duo, duo.a)
    out = tool_json(rig.w.call("resume", {"run_name": "x", "params": {"min_reads": 100}}, caller=duo.a))
    assert out["sent"] is False and out["state"] == "pending" and "/c/" in out["confirmation_url"] and len(rig.jobs()) == 1


def test_the_chat_prompt_says_resume_can_carry_params_and_extra_config():
    # TC-038
    from abf_platform.actions import chat_tools
    src = inspect.getsource(chat_tools)
    line = [ln for ln in src.splitlines() if ln.startswith("- resume：")]
    assert len(line) == 1 and "params" in line[0] and "extra_config" in line[0]
    assert sorted(chat_tools.REQUEST_TOOLS) == sorted(["launch", "cancel", "resume", "relaunch", "forget"])


# ---- the command line -----------------------------------------------------------------------------------------------------------------

def test_cli_resume_takes_param_params_file_and_config_file_and_relaunch_does_not():
    # TC-040, TC-041, TC-042
    from abf_platform import cli
    p = cli.build_parser()
    ns = p.parse_args(["resume", "x", "--param", "a=1", "--param", "b=2", "--params-file", "p.yaml", "--config-file", "c.config", "--user", "alice"])
    assert (ns.param, ns.params_file, ns.config_file, ns.user) == (["a=1", "b=2"], "p.yaml", "c.config", "alice")
    for extra in (["--param", "a=b"], ["--params-file", "p.yaml"], ["--config-file", "c.config"]):
        with pytest.raises(SystemExit):
            p.parse_args(["relaunch", "x"] + extra)
    p.parse_args(["relaunch", "x"])
    p.parse_args(["relaunch", "x", "--user", "alice"])
    for verb in ("resume", "relaunch"):
        for bad in (["--yes"], ["-y"], ["--force"], ["--assume-yes"], ["--no-confirm"], ["--y"], ["--params", "a.yaml"], ["--revision", "1"],
                    ["--samplesheet", "s.csv"], ["--ce", "o"], ["--pipeline", "nf-core/x"], ["--run-name", "n"], ["--session", SESSION]):
            with pytest.raises(SystemExit):
                p.parse_args([verb, "x"] + bad)


def test_cli_param_values_are_read_like_launch(tmp_path):
    # TC-043
    from abf_launch import build
    assert build.read_edit_args(None, None, None) == (None, None)
    params, extra = build.read_edit_args(None, ["n=3", "f=true", "s=abc", "x=1.5"], None)
    assert params == {"n": 3, "f": True, "s": "abc", "x": 1.5} and extra is None
    pf = tmp_path / "p.yaml"
    pf.write_text("a: 1\nb: hello\n", encoding="utf-8")
    assert build.read_edit_args(str(pf), None, None)[0] == build.read_params_file(str(pf))
    assert build.read_edit_args(str(pf), ["a=2"], None)[0]["a"] == 2


def test_cli_config_file_that_is_missing_not_utf8_or_too_long_is_refused(tmp_path):
    # TC-044, TC-045
    from abf_launch import build
    ok = tmp_path / "ok.config"
    ok.write_text(MEM + "\n", encoding="utf-8")
    assert build.read_edit_args(None, None, str(ok)) == (None, MEM + "\n")
    edge = tmp_path / "edge.config"
    edge.write_text("//" + "a" * 19998, encoding="utf-8")
    assert len(build.read_edit_args(None, None, str(edge))[1]) == 20000
    for name, data in (("missing.config", None), ("latin.config", b"\xff\xfe\x00bad"), ("long.config", ("//" + "a" * 19999).encode())):
        path = tmp_path / name
        if data is not None:
            path.write_bytes(data)
        with pytest.raises(build.Refusal) as e:
            build.read_edit_args(None, None, str(path))
        assert name in str(e.value)


def start(rig, *extra, run="x", **kw):
    return Pty(cli_argv("resume", run, *extra), kw.pop("env", None) or rig.w.data.env(), **kw)


def test_cli_edited_resume_shows_the_diff_before_the_question(rig, tmp_path):
    # TC-046, TC-047, TC-048
    first(rig)
    conf = tmp_path / "extra.config"
    conf.write_text(MEM + "\n", encoding="utf-8")
    before = rig.counts()
    p = start(rig, "--param", "min_reads=100", "--config-file", str(conf))
    assert p.wait_for(QUESTION_RESUME, 30), p.text()
    time.sleep(0.3)
    lines, asked = parts(p.text(), QUESTION_RESUME)
    text = "\n".join(lines)
    assert "參數 min_reads：50 → 100" in text and "== extra-2.config ==" in text and MEM in text
    assert re.search(r"nextflow run .* -c extra-2.config", text) and EDITED_SENTENCE in text
    assert rig.counts() == before
    p.send("n\n")
    rc, screen = p.finish(30)
    assert rc != 0 and "未送出" in screen and rig.counts() == before
    p = start(rig, "--param", "min_reads=100", "--config-file", str(conf))
    assert p.wait_for(QUESTION_RESUME, 30), p.text()
    p.send("y\n")
    p.finish(60)
    assert len(rig.jobs()) == 2
    b = rig.bundle_of_job(rig.jobs()[-1]["id"])
    assert b["resume"]["overrides"] == {"params": {"min_reads": 100}, "extra_config": MEM + "\n"}
    assert list(b["files"]) == ["head-2.sh", "params-2.yaml", "extra-2.config"]


def test_cli_edited_resume_without_a_terminal_or_with_a_bad_edit_queues_nothing(rig):
    # TC-049, TC-050
    first(rig)
    before = rig.counts()
    p = Pty(["bash", "-c", 'echo y | "$@"', "_"] + cli_argv("resume", "x", "--param", "min_reads=100"), rig.w.data.env())
    rc, screen = p.finish(60)
    assert rc != 0 and "要在終端機上互動回答 y" in screen and "Traceback" not in screen and rig.counts() == before
    p = start(rig, "--param", "input=foo")
    rc, screen = p.finish(30)
    assert rc != 0 and "input" in screen and QUESTION_RESUME not in screen and rig.counts() == before
