# Nothing existing: tests of 007b follow-up 3 (why a run failed, no 401 for what Nextflow sends after complete); they drive our own receiver with recorded payloads.
"""007b follow-up 3, G1 and G2: the reason Nextflow gave for a failed run, and the messages after `complete`."""
import copy
import json
import time
import sqlite3

import pytest

from abf_platform import status, store
from helpers import Clock, Platform, db_rows, load_scenario, variant

REASON = "failure_reason"

def complete_of(requests):
    return [r for r in requests if r["path"].endswith("/complete")][0]


def replay_with(plat, token, scenario, wf=None, requests=None, **kw):
    """Replay a recording whose complete message has the given workflow fields changed (None value removes the field)."""
    reqs = copy.deepcopy(requests if requests is not None else load_scenario(scenario)["requests"])
    for k, v in (wf or {}).items():
        body = complete_of(reqs)["body"]["workflow"]
        if v is KeyError:
            body.pop(k, None)
        else:
            body[k] = v
    return plat.replay(reqs, token, **kw)


def view(plat, wid):
    return status.get_run(plat.index, wid, plat.clock())


# ---- G1: the reason of a failed run ----------------------------------------------------------------------------------

def test_tcf3_01_a_cancelled_run_says_what_nextflow_said(plat, token):
    # TC-F3-01 (TC-048): 49 of 50 tasks done, one pending, no failed task, complete without an error report
    reqs = copy.deepcopy(load_scenario("nf2510_ok")["requests"])
    comp = complete_of(reqs)["body"]
    comp["progress"] = dict(comp["progress"], succeeded=49, cached=0, failed=0, aborted=0, running=0, pending=1, submitted=0)
    comp["workflow"].update(success=False, exitStatus=1, errorMessage="Execution cancelled by user", errorReport=None)
    wid, resp = plat.replay(reqs, token)
    assert all(r.status_code < 300 for r in resp)
    v = view(plat, wid)
    assert v["status"] == "failed"
    assert v["tasks"]["succeeded"] == 49 and v["tasks"]["pending"] == 1 and v["tasks"]["total"] == 50
    assert v[REASON] == "Execution cancelled by user"
    assert v["failed_tasks"] == []


def test_tcf3_02_the_error_message_first_then_the_first_line_of_the_error_report(tmp_path):
    # TC-F3-02
    for i, (override, want) in enumerate([
            ({}, "FIXTURE_BOOM_7"),
            ({"errorMessage": None}, "Error executing process > 'BAD'"),
            ({"errorMessage": ""}, "Error executing process > 'BAD'"),
            ({"errorMessage": "  \n "}, "Error executing process > 'BAD'")]):
        plat = Platform(tmp_path / str(i), clock=Clock())
        wid, _ = replay_with(plat, plat.new_token(), "fail_run", wf=override)
        assert view(plat, wid)[REASON] == want, override


def test_tcf3_02_a_report_that_starts_with_blank_lines_gives_its_first_non_empty_line(plat, token):
    wid, _ = replay_with(plat, token, "fail_run", wf={"errorMessage": None, "errorReport": "\n\n  Something broke  \nmore\n"})
    assert view(plat, wid)[REASON] == "Something broke"


@pytest.mark.parametrize("name", ["fail_run", "nf2510_fail", "nf2510_retry"])
def test_tcf3_03_the_recorded_failed_runs_carry_the_reason_and_the_same_failed_tasks(tmp_path, name):
    # TC-F3-03
    plat = Platform(tmp_path, clock=Clock())
    wid, _ = plat.replay(load_scenario(name)["requests"], plat.new_token())
    v = view(plat, wid)
    assert v["status"] == "failed" and v[REASON] == "FIXTURE_BOOM_7"
    assert v["failed_tasks"] and "FIXTURE_BOOM_7" in v["failed_tasks"][0]["error_message"]
    assert set(v["failed_tasks"][0]) == {"name", "exit_code", "error_message"}


@pytest.mark.parametrize("name", ["ok_run", "ok_resume", "heartbeat_run", "nf2510_ok", "slow_run", "nf2510_resume"])
def test_tcf3_04_a_succeeded_run_has_no_reason_and_the_list_never_shows_one(tmp_path, name):
    # TC-F3-04: the field is absent (not empty) for a run that did not fail
    plat = Platform(tmp_path, clock=Clock())
    wid, _ = plat.replay(load_scenario(name)["requests"], plat.new_token())
    v = view(plat, wid)
    assert v["status"] == "succeeded" and REASON not in v
    assert all(REASON not in r for r in status.list_runs(plat.index, plat.clock()))


def test_tcf3_04_a_failed_run_in_the_list_has_no_reason_only_get_run_does(plat, token):
    wid, _ = plat.replay(load_scenario("fail_run")["requests"], token)
    assert view(plat, wid)[REASON] == "FIXTURE_BOOM_7"
    assert all(REASON not in r for r in status.list_runs(plat.index, plat.clock()))


def test_tcf3_20_the_reason_keeps_all_255_characters_nextflow_sends_and_a_huge_one_is_bounded(plat, token):
    # TC-F3-20: Nextflow cuts errorMessage at 255 itself; the platform's bound must not be below that
    text = "x" * 255
    wid, r = replay_with(plat, token, "fail_run", wf={"errorMessage": text})
    assert view(plat, wid)[REASON] == text
    plat2 = Platform(plat.dir / "two", clock=Clock())
    wid2, r2 = replay_with(plat2, plat2.new_token(), "fail_run", wf={"errorMessage": "y" * 10000})
    assert all(x.status_code == 200 for x in r2)
    got = view(plat2, wid2)[REASON]
    assert 255 <= len(got) <= store.REASON_MAX_CHARS == 1000
    assert len(json.dumps(view(plat2, wid2))) < 20000


def test_tcf3_21_the_reason_is_one_line_of_printable_text(plat, token):
    # TC-F3-21: "escaped" = every control character (ESC, NUL, CR, LF, tab, DEL) becomes one space, so the value is a single
    # line of printable text and cannot change the shape of what is printed; markup stays as plain text
    nasty = "\x1b[31mred\x1b[0m\r\nline2\x00nul\n\n\n\n<script>alert(1)</script>\x7f end"
    wid, _ = replay_with(plat, token, "fail_run", wf={"errorMessage": nasty})
    got = view(plat, wid)[REASON]
    assert not [c for c in got if ord(c) < 32 or ord(c) == 127], repr(got)
    assert "\n" not in got and "\r" not in got and "\x00" not in got and "\x1b" not in got
    assert "<script>alert(1)</script>" in got and "red" in got and "line2" in got
    assert json.loads(json.dumps(view(plat, wid)))[REASON] == got


@pytest.mark.parametrize("wf", [{"errorMessage": None, "errorReport": None}, {"errorMessage": "", "errorReport": ""},
                                {"errorMessage": KeyError, "errorReport": KeyError}])
def test_tcf3_22_no_reason_from_nextflow_means_no_reason_and_nothing_made_up(plat, token, wf):
    # TC-F3-22
    reqs = copy.deepcopy(load_scenario("nf2510_ok")["requests"])
    complete_of(reqs)["body"]["workflow"].update(success=False, exitStatus=1)
    wid, r = replay_with(plat, token, None, wf=wf, requests=reqs)
    v = view(plat, wid)
    assert v["status"] == "failed" and not v.get(REASON)
    text = json.dumps(v).lower()
    assert "cancel" not in text and "unknown error" not in text


@pytest.mark.parametrize("wf", [{"errorMessage": 42, "errorReport": 7}, {"errorMessage": {"a": 1}, "errorReport": 7},
                                {"errorMessage": ["x"], "errorReport": 7}, {"errorMessage": None, "errorReport": 7}, {"errorMessage": 3.5, "errorReport": ["Error"]}])
def test_tcf3_23_a_wrong_type_does_not_break_the_receiver(plat, token, wf):
    # TC-F3-23: failed_tasks come out as before; the reason is empty
    wid, resp = replay_with(plat, token, "fail_run", wf=wf)
    assert all(r.status_code == 200 for r in resp), [r.status_code for r in resp]
    v = view(plat, wid)
    assert v["status"] == "failed" and not v.get(REASON)


def test_tcf3_63_the_platform_does_not_make_up_a_reason_for_a_cancel(plat, token):
    # TC-F3-63: the reason comes from Nextflow's complete message only; the receiver never reads the launches table
    from abf_platform import receiver
    reqs = copy.deepcopy(load_scenario("nf2510_fail")["requests"])
    complete_of(reqs)["body"]["workflow"].update(errorMessage=None, errorReport=None)
    wid, _ = plat.replay(reqs, token)
    assert not view(plat, wid).get(REASON)
    src = open(receiver.__file__, encoding="utf-8").read().lower()
    assert "launches" not in src and "cancel_requested" not in src and "cancelled by" not in src


def _old_index(path, rows=3):
    """An index.db as main wrote it: the runs table has no failure_reason column."""
    con = sqlite3.connect(str(path))
    schema = store.SCHEMA.replace("    n_submitted INTEGER NOT NULL DEFAULT 0\n);\nCREATE TABLE IF NOT EXISTS processes",
                                  "    n_submitted INTEGER NOT NULL DEFAULT 0\n);\nCREATE TABLE IF NOT EXISTS processes", 1)
    schema = schema.replace("    failure_reason TEXT,\n", "")
    con.executescript(schema)
    now = 1_800_000_000
    for i, (st, ended) in enumerate([("succeeded", now + 5), ("failed", now + 7), (None, None)]):
        con.execute("INSERT INTO runs (id, session_id, run_name, token_id, source, final_status, started_at, ended_at, "
                    "last_message_at, exit_status, n_succeeded, n_failed) VALUES (?, ?, ?, 1, 'live', ?, ?, ?, ?, ?, 3, ?)",
                    ("run%02d" % i, "s%d" % i, "name%d" % i, st, now, ended, now + 9, 1 if st == "failed" else 0, 1 if st == "failed" else 0))
        con.execute("INSERT INTO processes (run_id, name, n_succeeded) VALUES (?, 'P', 3)", ("run%02d" % i,))
    con.execute("INSERT INTO failed_tasks (run_id, task_key, name, exit_code, error_message) VALUES ('run01', '1:1', 'BAD', 1, 'boom')")
    con.commit()
    con.close()


def test_tcf3_12_an_index_made_by_main_is_upgraded_and_keeps_every_row(tmp_path):
    # TC-F3-12
    from abf_platform import receiver
    idx = tmp_path / "index.db"
    _old_index(idx)
    cols = {r[1] for r in sqlite3.connect(str(idx)).execute("PRAGMA table_info(runs)")}
    assert REASON not in cols
    before = db_rows(idx)
    for _ in range(2):   # twice: the upgrade can run again
        receiver.create_app(idx, tmp_path / "tokens.db", clock=Clock())
    con = sqlite3.connect(str(idx))
    cols = [r[1] for r in con.execute("PRAGMA table_info(runs)")]
    assert REASON in cols
    new = con.execute("SELECT * FROM runs ORDER BY id").fetchall()
    con.close()
    i = cols.index(REASON)
    assert [r[i] for r in new] == [None, None, None]
    after = db_rows(idx)
    assert after["processes"] == before["processes"] and after["failed_tasks"] == before["failed_tasks"]
    assert sorted(tuple(r[:i] + r[i + 1:]) for r in new) == sorted(before["runs"])
    # a failed run that completes afterwards gets its reason written
    plat = Platform.__new__(Platform)
    from starlette.testclient import TestClient
    plat.dir, plat.index, plat.tokens, plat.clock, plat.store = tmp_path, idx, tmp_path / "tokens.db", Clock(), store
    plat.app = receiver.create_app(idx, plat.tokens, clock=plat.clock)
    plat.client = TestClient(plat.app)
    wid, _ = plat.replay(load_scenario("fail_run")["requests"], plat.new_token())
    assert view(plat, wid)[REASON] == "FIXTURE_BOOM_7"


def test_tcf3_32_an_old_index_is_read_without_a_crash_and_without_a_write(tmp_path):
    # TC-F3-32: status opens the file read-only, it cannot upgrade it
    idx = tmp_path / "index.db"
    _old_index(idx)
    raw = idx.read_bytes()
    mtime = idx.stat().st_mtime_ns
    v = status.get_run(idx, "run01", 1_800_000_100)
    assert v["status"] == "failed" and REASON not in v and v["failed_tasks"][0]["error_message"] == "boom"
    assert sorted(r["id"] for r in status.list_runs(idx, 1_800_000_100)) == ["run00", "run01", "run02"]
    assert idx.read_bytes() == raw and idx.stat().st_mtime_ns == mtime


# ---- G2: what Nextflow sends after `complete` -------------------------------------------------------------------------
# nf-tower 1.28.3 sends nothing after traceComplete in TowerObserver.onFlowComplete (plugins/nf-tower/.../TowerObserver.groovy
# :257-272, the sender thread is joined first at :261-264). But for a run that was ABORTED (a failed task, a cancel),
# Session.abort() runs shutdown0() -> notifyFlowComplete() (Session.groovy:830, :775, :1091-1093) and the ScriptRunner then
# calls session.destroy() -> shutdown0() -> notifyFlowComplete() again (ScriptRunner.groovy:131-139, :244; Session.groovy:720):
# onFlowComplete runs twice and the second one PUTs `complete` once more. So the message after complete is a second `complete`.
# The tests below also send progress and heartbeat, the other two kinds a late sender could produce.

def bound_token(plat, run="run-one"):
    return store.create_token(plat.tokens, run_name=run)


def finished_run(plat, scenario="nf2510_ok", run="run-one"):
    t = bound_token(plat, run)
    wid, resp = plat.replay(variant(scenario, run, "sess-" + run, plat.clock()), t)
    assert all(r.status_code < 300 for r in resp), [r.status_code for r in resp]
    return t, wid


def late(plat, wid, token, kind):
    if kind == "heartbeat":
        return plat.send("PUT", "/trace/%s/heartbeat" % wid, {"progress": {"running": 9}}, token=token)
    if kind == "progress":
        return plat.send("PUT", "/trace/%s/progress" % wid, {"progress": {"succeeded": 1, "running": 4, "pending": 3},
                                                              "tasks": [{"taskId": 99, "name": "X (1)", "status": "RUNNING", "attempt": 1}]},
                         token=token)
    body = copy.deepcopy(complete_of(variant("nf2510_ok", "run-one", "sess-run-one", plat.clock()))["body"])
    body["workflow"].update(success=False, exitStatus=77, errorMessage="LATE")
    return plat.send("PUT", "/trace/%s/complete" % wid, body, token=token)


KINDS = ("heartbeat", "progress", "complete")


@pytest.mark.parametrize("kind", KINDS)
def test_tcf3_05_06_a_message_after_complete_is_answered_ok_and_changes_nothing(plat, kind):
    # TC-F3-05, TC-F3-06
    t, wid = finished_run(plat)
    rows, shown = db_rows(plat.index), view(plat, wid)
    r = late(plat, wid, t, kind)
    assert r.status_code == 200 and r.json() == {"status": "OK"}, (r.status_code, r.text)
    assert db_rows(plat.index) == rows
    assert view(plat, wid) == shown


def test_tcf3_07_the_token_is_still_marked_revoked_by_the_complete(plat):
    # TC-F3-07: FR-004 "revoked when complete arrives" stays true in the token file
    t, wid = finished_run(plat)
    con = sqlite3.connect(str(plat.tokens))
    assert con.execute("SELECT revoked_at FROM tokens WHERE run_name = 'run-one'").fetchone()[0] is not None
    con.close()


@pytest.mark.parametrize("kind", KINDS)
def test_tcf3_24_a_message_after_a_failed_run_does_not_turn_it_back(plat, kind):
    # TC-F3-24
    t, wid = finished_run(plat, "nf2510_fail")
    before, rows = view(plat, wid), db_rows(plat.index)
    assert before["status"] == "failed" and before["failed_tasks"]
    assert late(plat, wid, t, kind).status_code == 200
    assert view(plat, wid) == before and db_rows(plat.index) == rows


def test_tcf3_25_the_ended_token_cannot_make_a_run(plat):
    # TC-F3-25
    t, wid = finished_run(plat)
    n = plat.counts()["runs"]
    for sid, name in (("sess-new", "run-one"), ("sess-run-one", "other-run"), ("sess-run-one", "run-one")):
        r = plat.send("POST", "/trace/create", {"sessionId": sid, "runName": name}, token=t)
        assert r.status_code in (401, 403), (sid, name, r.status_code)
    r = plat.send("PUT", "/trace/%s/begin" % wid, {"workflow": {"params": {"x": 1}}}, token=t)
    assert r.status_code in (401, 403)
    assert plat.counts()["runs"] == n


def test_tcf3_26_the_ended_token_cannot_touch_another_run(plat):
    # TC-F3-26
    t, wid = finished_run(plat)
    other = bound_token(plat, "run-two")
    wid2, _ = plat.replay(variant("nf2510_ok", "run-two", "sess-run-two", plat.clock()), other, stop_before="complete")
    rows2 = db_rows(plat.index, wid2)
    for kind in KINDS:
        assert late(plat, wid2, t, kind).status_code in (401, 403, 404), kind
    assert db_rows(plat.index, wid2) == rows2 and view(plat, wid2)["status"] == "running"
    n = plat.counts()["runs"]
    assert late(plat, "0123456789abcdef", t, "heartbeat").status_code in (401, 403, 404)
    assert plat.counts()["runs"] == n


def test_tcf3_26_the_door_is_only_for_a_run_that_has_a_complete_on_record(plat):
    # a token that was marked ended while its own run never completed (a stray row) gets no door
    live = bound_token(plat, "run-three")
    wid3, _ = plat.replay(variant("nf2510_ok", "run-three", "sess-run-three", plat.clock()), live, stop_before="complete")
    con = sqlite3.connect(str(plat.tokens))
    con.execute("UPDATE tokens SET revoked_at = ?, ended_at = ? WHERE run_name = 'run-three'", (time.time(), time.time()))
    con.commit()
    con.close()
    assert late(plat, wid3, live, "heartbeat").status_code == 401


def test_tcf3_27_the_door_closes_after_a_fixed_time(plat, monkeypatch):
    # TC-F3-27
    t, wid = finished_run(plat)
    g = store.ENDED_GRACE_SECONDS
    assert 0 < g <= 14 * 86400
    monkeypatch.setenv("ABF_PLATFORM_CLOCK_OFFSET", str(g - 30))
    assert late(plat, wid, t, "heartbeat").status_code == 200
    monkeypatch.setenv("ABF_PLATFORM_CLOCK_OFFSET", str(g + 30))
    for kind in KINDS:
        r = late(plat, wid, t, kind)
        assert r.status_code == 401 and "X-ABF-Platform" in r.headers, kind
    r = plat.send("POST", "/trace/create", {"sessionId": "s", "runName": "run-one"}, token=t)
    assert r.status_code == 401


def test_tcf3_28_other_ways_of_revoking_still_end_a_token_at_once(plat):
    # TC-F3-28: revoke_token and revoke_run_tokens on a live token; an explicit revoke after the complete closes the door
    t = bound_token(plat, "run-a")
    wid, _ = plat.replay(variant("nf2510_ok", "run-a", "sess-run-a", plat.clock()), t, stop_before="complete")
    row = [r for r in sqlite3.connect(str(plat.tokens)).execute("SELECT id FROM tokens WHERE run_name = 'run-a'")][0]
    store.revoke_token(plat.tokens, row[0])
    for kind in ("heartbeat", "progress"):
        assert late(plat, wid, t, kind).status_code == 401
    t2 = bound_token(plat, "run-b")
    wid2, _ = plat.replay(variant("nf2510_ok", "run-b", "sess-run-b", plat.clock()), t2, stop_before="complete")
    assert store.revoke_run_tokens(plat.tokens, "run-b") == 1
    assert late(plat, wid2, t2, "heartbeat").status_code == 401
    t3, wid3 = finished_run(plat, run="run-c")
    assert late(plat, wid3, t3, "heartbeat").status_code == 200
    store.revoke_run_tokens(plat.tokens, "run-c")
    assert late(plat, wid3, t3, "heartbeat").status_code == 401   # an explicit revoke closes the door at once


def test_tcf3_43_82_the_ended_token_reads_nothing_and_a_plain_token_is_not_affected(plat):
    t, wid = finished_run(plat)
    assert plat.send("GET", "/user-info", token=t).status_code == 401
    for bad in (None, "abf_nope"):
        r = plat.send("PUT", "/trace/%s/heartbeat" % wid, {}, token=bad)
        assert r.status_code == 401 and r.json()["message"] == "Unauthorized: missing or unknown access token"
    plain = plat.new_token()
    wid2, _ = plat.replay(variant("nf2510_ok", "run-free", "sess-run-free", plat.clock()), plain)
    assert plat.send("PUT", "/trace/%s/heartbeat" % wid2, {"progress": {}}, token=plain).status_code == 200
