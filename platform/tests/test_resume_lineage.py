# Nothing existing: tests of the hand-off record's three new columns and of the numbering of attempts (spec 009e); the lineage of requests is ours.
"""009e: launches.parent_run / attempt / attempt_kind, written with the job; attempt numbers 2, 3, 4 ...; what the hash binds.
Test cases are named in the comments (TC-119 ...), see specs/009e-resume-relaunch/test-case.md."""
import copy
import sqlite3
import time

import pytest

from resume_harness import FakePerson, Rig
from test_launch_platform import make_confirmation

OLD_COLUMNS = ["id", "run_name", "slurm_job_id", "run_folder", "ce", "agent", "confirmed_at", "submitted_at", "cancel_requested_at",
               "job_id", "user_id"]
NEW_COLUMNS = ["parent_run", "attempt", "attempt_kind"]
# a launches table as it was before 009e (the DDL of 116)
OLD_LAUNCHES = """CREATE TABLE launches (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_name TEXT NOT NULL, slurm_job_id INTEGER, run_folder TEXT NOT NULL, ce TEXT NOT NULL,
    agent TEXT NOT NULL, confirmed_at REAL NOT NULL, submitted_at REAL, cancel_requested_at REAL, job_id INTEGER, user_id INTEGER)"""
CHANGED = "內容與確認時不符"


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


def columns(db):
    con = sqlite3.connect(str(db))
    try:
        return [tuple(r) for r in con.execute("PRAGMA table_info(launches)")]
    finally:
        con.close()


# ---- the columns ---------------------------------------------------------------------------------------------------------------------

def test_tc122_a_first_launch_has_no_parent_no_attempt_and_no_kind(rig):
    # TC-122
    rig.first("x")
    row = rig.launches()[0]
    assert (row["parent_run"], row["attempt"], row["attempt_kind"]) == (None, None, None)


def test_tc122_tc126_a_new_database_has_the_three_columns_last_and_the_old_ones_in_their_order(rig):
    # TC-126 (the part about a new file), TC-122
    names = [c[1] for c in columns(rig.state)] if rig.state.exists() else None
    if names is None:
        rig.first("x")
        names = [c[1] for c in columns(rig.state)]
    assert names == OLD_COLUMNS + NEW_COLUMNS


def test_tc125_tc126_a_platform_db_of_116_is_upgraded_in_place_and_every_row_reads_back(tmp_path):
    # TC-125, TC-126
    from abf_platform import store
    db = tmp_path / "old" / "platform.db"
    db.parent.mkdir()
    con = sqlite3.connect(str(db))
    con.execute(OLD_LAUNCHES)
    con.execute("CREATE INDEX launches_run_name ON launches (run_name)")
    con.execute("INSERT INTO launches VALUES (1, 'r1', 4242, '/w/runs/r1', 'lab-a', 'agent-t', 11.5, 12.5, 13.5, 7, 3)")
    con.execute("INSERT INTO launches VALUES (2, 'r2', NULL, '/w/runs/r2', 'lab-a', 'agent-t', 21.5, NULL, NULL, NULL, NULL)")
    con.commit()
    before = con.execute("SELECT * FROM launches ORDER BY id").fetchall()
    con.close()
    store.connect_state(db).close()
    names = [c[1] for c in columns(db)]
    assert names == OLD_COLUMNS + NEW_COLUMNS
    con = sqlite3.connect(str(db))
    after = con.execute("SELECT * FROM launches ORDER BY id").fetchall()
    con.close()
    assert [r[:len(OLD_COLUMNS)] for r in after] == before
    assert all(r[len(OLD_COLUMNS):] == (None, None, None) for r in after)
    # a fresh file and an upgraded one have the same table
    fresh = tmp_path / "fresh" / "platform.db"
    store.connect_state(fresh).close()
    assert columns(fresh) == columns(db)
    # opening it again changes nothing
    store.connect_state(db).close()
    assert columns(db) == columns(fresh)


def test_tc127_only_resume_and_relaunch_are_kinds_of_attempt(tmp_path):
    # TC-127, on a new file and on an upgraded one
    from abf_platform import store
    fresh = tmp_path / "fresh" / "platform.db"
    store.connect_state(fresh).close()
    old = tmp_path / "old" / "platform.db"
    old.parent.mkdir()
    con = sqlite3.connect(str(old))
    con.execute(OLD_LAUNCHES)
    con.commit()
    con.close()
    store.connect_state(old).close()
    for db in (fresh, old):
        con = sqlite3.connect(str(db))
        ins = "INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, parent_run, attempt, attempt_kind) VALUES ('a', '/f', 'c', 'g', 1, 'p', 2, ?)"
        for kind in ("resume", "relaunch", None):
            con.execute(ins, (kind,))
        for kind in ("retry", "", "RESUME", "launch", "cancel"):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute(ins, (kind,))
        con.close()


# ---- numbering ---------------------------------------------------------------------------------------------------------------------------

def test_tc119_tc123_attempts_are_numbered_2_3_4_across_a_mix_of_resume_and_relaunch(rig):
    # TC-119, TC-123
    rig.first("x")
    rig.attempt("resume", "x")
    rig.attempt("relaunch", "x-a2")
    rig.attempt("resume", "x-a3")
    rows = rig.launches()
    assert [r["run_name"] for r in rows] == ["x", "x-a2", "x-a3", "x-a4"]
    assert [r["attempt"] for r in rows] == [None, 2, 3, 4]
    assert [r["attempt_kind"] for r in rows] == [None, "resume", "relaunch", "resume"]
    assert [r["parent_run"] for r in rows] == [None, "x", "x-a2", "x-a3"]
    # each attempt row is the row of its own job, written with it
    jobs = rig.jobs()
    assert [r["job_id"] for r in rows] == [j["id"] for j in jobs]


def test_tc123_the_three_columns_come_from_the_bundle_in_the_same_step_as_the_job(rig):
    # TC-123
    rig.first("x")
    out = rig.attempt("resume", "x")
    row = rig.row_of_job(out["job_id"])
    b = rig.bundle_of_job(out["job_id"])
    assert (row["parent_run"], row["attempt"], row["attempt_kind"]) == (b["resume"]["of_run"], b["resume"]["attempt"], "resume")
    assert rig.sql("SELECT state FROM jobs WHERE id = ?", (out["job_id"],))[0][0] == "done"


def test_tc120_a_job_that_was_refused_does_not_use_up_a_number(rig):
    # TC-120
    rig.first("x")
    out = rig.resume("x", person=FakePerson(True))
    assert out["sent"] is True
    rig.fail_job(out["job_id"], "refused")
    again = rig.resume("x", person=FakePerson(True))
    assert again["sent"] is True, again
    row = rig.row_of_job(again["job_id"])
    assert (row["run_name"], row["attempt"]) == ("x-a2", 2)


def test_tc120_the_number_after_a_refused_attempt_follows_the_ones_that_stand(rig):
    rig.first("x")
    rig.attempt("resume", "x")                             # x-a2 stands
    out = rig.resume("x-a2", person=FakePerson(True))      # x-a3 is asked
    rig.fail_job(out["job_id"], "refused")
    again = rig.relaunch("x-a2", person=FakePerson(True))
    assert rig.row_of_job(again["job_id"])["attempt"] == 3


def test_tc121_two_attempts_asked_at_the_same_time_the_second_is_refused(rig):
    # TC-121: both were built when the analysis stood at attempt 1, so both say 2
    from abf_platform import actions, jobs
    rig.first("x")
    ce1, b1, _ = rig.prepare("resume", "x")
    ce2, b2, _ = rig.prepare("relaunch", "x")
    assert b1["resume"]["attempt"] == 2 and b2["relaunch"]["attempt"] == 2
    actions.launch(rig.state, ce1, b1, confirmed_by=actions.TERMINAL)
    before = rig.counts()
    with pytest.raises(jobs.JobRefused, match="another attempt was started meanwhile"):
        actions.launch(rig.state, ce2, b2, confirmed_by=actions.TERMINAL)
    assert rig.counts() == before, "the confirmation of the refused one is not left behind either"


def test_tc121_the_same_request_twice_is_one_attempt(rig):
    from abf_platform import actions, jobs
    rig.first("x")
    ce1, b1, _ = rig.prepare("resume", "x")
    actions.launch(rig.state, ce1, b1, confirmed_by=actions.TERMINAL)
    with pytest.raises(jobs.JobRefused, match="another attempt was started meanwhile"):
        actions.launch(rig.state, ce1, copy.deepcopy(b1), confirmed_by=actions.TERMINAL)


def test_tc124_a_launch_that_fails_while_it_is_queued_leaves_no_job_no_confirmation_and_no_row(rig):
    # TC-124: the row is written in the same transaction as the job; a failure on the row takes the job and the yes with it
    from abf_platform import actions
    rig.first("x")
    ce, b, _ = rig.prepare("resume", "x")
    con = sqlite3.connect(str(rig.state))
    con.execute("CREATE TRIGGER boom BEFORE INSERT ON launches WHEN NEW.attempt IS NOT NULL BEGIN SELECT RAISE(ABORT, 'boom'); END")
    con.commit()
    con.close()
    before = rig.counts()
    with pytest.raises(sqlite3.Error):
        actions.launch(rig.state, ce, b, confirmed_by=actions.TERMINAL)
    assert rig.counts() == before
    assert rig.sql("SELECT COUNT(*) FROM launches WHERE attempt IS NOT NULL")[0][0] == 0


def test_tc128_an_attempt_number_that_is_not_one_more_than_the_highest_is_refused(rig):
    # TC-128
    from abf_platform import actions, jobs
    rig.first("x")
    ce, b, _ = rig.prepare("resume", "x")
    for wrong in (1, 3, 7, 0, -1, True, "2", 2.5, None):
        t = copy.deepcopy(b)
        t["resume"]["attempt"] = wrong
        before = rig.counts()
        with pytest.raises(jobs.JobRefused):
            actions.launch(rig.state, ce, t, confirmed_by=actions.TERMINAL)
        assert rig.counts() == before, wrong
    ce, b, _ = rig.prepare("relaunch", "x")
    for wrong in (1, 3, True, None, "2"):
        t = copy.deepcopy(b)
        t["relaunch"]["attempt"] = wrong
        with pytest.raises(jobs.JobRefused):
            actions.launch(rig.state, ce, t, confirmed_by=actions.TERMINAL)
    assert rig.counts()[0] == 1       # only the first launch has a job


def test_tc129_a_parent_that_is_not_in_the_hand_off_record_is_refused(rig):
    # TC-129
    from abf_platform import actions, jobs
    rig.first("x")
    ce, b, _ = rig.prepare("resume", "x")
    t = copy.deepcopy(b)
    t["resume"]["of_run"] = "ghost"
    with pytest.raises(jobs.JobRefused, match="找不到這個 run"):
        actions.launch(rig.state, ce, t, confirmed_by=actions.TERMINAL)
    ce, b, _ = rig.prepare("relaunch", "x")
    t = copy.deepcopy(b)
    t["relaunch"]["of_run"] = "ghost"
    with pytest.raises(jobs.JobRefused, match="找不到這個 run"):
        actions.launch(rig.state, ce, t, confirmed_by=actions.TERMINAL)
    assert rig.counts()[0] == 1


def test_tc129_a_bundle_with_both_a_resume_and_a_relaunch_record_is_refused(rig):
    from abf_platform import actions, jobs
    rig.first("x")
    ce, b, _ = rig.prepare("resume", "x")
    _, b2, _ = rig.prepare("relaunch", "x")
    t = copy.deepcopy(b)
    t["relaunch"] = b2["relaunch"]
    with pytest.raises(jobs.JobRefused):
        actions.launch(rig.state, ce, t, confirmed_by=actions.TERMINAL)


@pytest.mark.parametrize("record", [None, "x", [], {}, {"of_run": "x"}, {"of_run": 3, "attempt": 2}])
def test_tc129_a_resume_or_relaunch_record_of_the_wrong_shape_is_refused(rig, record):
    from abf_platform import actions, jobs
    rig.first("x")
    ce, b, _ = rig.prepare("resume", "x")
    t = copy.deepcopy(b)
    t["resume"] = record
    with pytest.raises(jobs.JobRefused):
        actions.launch(rig.state, ce, t, confirmed_by=actions.TERMINAL)


def test_tc130_the_root_of_an_analysis_is_found_by_following_parent_run_and_there_is_no_analysis_column(rig):
    # TC-130
    from abf_platform import jobs
    rig.first("x")
    rig.attempt("resume", "x")
    rig.attempt("relaunch", "x-a2")
    rig.attempt("resume", "x-a3")
    rig.first("other")
    con = sqlite3.connect(str(rig.state))
    con.row_factory = sqlite3.Row
    try:
        assert jobs.analysis_root(con, "x-a4") == "x"
        assert jobs.analysis_root(con, "x-a3") == "x"
        assert jobs.analysis_root(con, "x") == "x"
        assert jobs.analysis_root(con, "other") == "other"
        names = [r[1] for r in con.execute("PRAGMA table_info(launches)")]
    finally:
        con.close()
    assert "analysis" not in names and not [n for n in names if n.startswith("analysis")]


def test_tc003_the_third_attempt_is_named_after_the_root_and_not_after_the_second(rig):
    # TC-003
    rig.first("x")
    rig.attempt("resume", "x")
    b = rig.prepare("resume", "x-a2")[1]
    assert b["run_name"] == "x-a3" and b["resume"]["attempt"] == 3 and b["resume"]["of_run"] == "x-a2"


# ---- what the hash binds -------------------------------------------------------------------------------------------------------------------

def _setup_two(rig):
    rig.first("x")
    ce, resume_b, _ = rig.prepare("resume", "x")
    _, relaunch_b, _ = rig.prepare("relaunch", "x")
    return ce, resume_b, relaunch_b


@pytest.mark.parametrize("tc,path,value", [
    ("TC-089", ("resume", "attempt"), 3), ("TC-090", ("resume", "of_run"), "y"), ("TC-091", ("resume", "of_slurm_job_id"), 9999),
    ("TC-092", ("resume", "session_id"), "ffffffff-4f50-4a6b-8c7d-9e0f1a2b3c4d"),
    ("TC-093", ("resume", "origin", "params", "primer"), "OTHER"), ("TC-093", ("resume", "origin", "samplesheet", 1, 0), "s99"),
    ("TC-093", ("resume", "origin", "revision"), "2.18.1"), ("TC-093", ("resume", "origin", "files", "params.yaml"), "x: 1\n"),
    ("TC-093", ("resume", "origin", "run_folder"), "/data/w1/runs/other"),
    ("TC-089", ("run_name",), "x-a9"), ("TC-089", ("run_folder",), "/data/w1/runs/other"),
    ("TC-089", ("files", "head-2.sh"), "#!/bin/bash\ntouch /tmp/evil\n")])
def test_tc089_to_tc093_a_resume_changed_after_the_yes_is_not_the_content_that_was_confirmed(rig, tc, path, value):
    from abf_platform import jobs
    rig.first("x")
    ce, b, _ = rig.prepare("resume", "x")
    cid = make_confirmation(rig.state, "launch", b)
    t = copy.deepcopy(b)
    node = t
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(jobs.JobRefused, match=CHANGED):
        jobs.enqueue_launch(rig.state, ce, t, cid)
    assert len(rig.jobs()) == 1        # only the first launch's job
    # and the content as it was is let in
    assert jobs.enqueue_launch(rig.state, ce, b, cid)


@pytest.mark.parametrize("path,value", [(("relaunch", "attempt"), 3), (("relaunch", "of_run"), "y"), (("relaunch", "of_sha256"), "0" * 64),
                                         (("params", "primer"), "OTHER"), (("run_name",), "x-a9")])
def test_tc094_a_relaunch_changed_after_the_yes_is_not_the_content_that_was_confirmed(rig, path, value):
    from abf_platform import jobs
    rig.first("x")
    ce, b, _ = rig.prepare("relaunch", "x")
    cid = make_confirmation(rig.state, "launch", b)
    t = copy.deepcopy(b)
    node = t
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(jobs.JobRefused, match=CHANGED):
        jobs.enqueue_launch(rig.state, ce, t, cid)


def test_tc095_the_yes_for_a_resume_cannot_start_a_relaunch(rig):
    # TC-095
    from abf_platform import jobs
    ce, resume_b, relaunch_b = _setup_two(rig)
    cid = make_confirmation(rig.state, "launch", resume_b)
    with pytest.raises(jobs.JobRefused, match=CHANGED):
        jobs.enqueue_launch(rig.state, ce, relaunch_b, cid)
    assert len(rig.jobs()) == 1


def test_tc095_the_yes_for_a_relaunch_cannot_start_a_resume(rig):
    from abf_platform import jobs
    ce, resume_b, relaunch_b = _setup_two(rig)
    cid = make_confirmation(rig.state, "launch", relaunch_b)
    with pytest.raises(jobs.JobRefused, match=CHANGED):
        jobs.enqueue_launch(rig.state, ce, resume_b, cid)


def test_tc096_the_yes_for_attempt_two_cannot_make_attempt_three(rig):
    # TC-096
    from abf_platform import jobs
    rig.first("x")
    ce, b2, _ = rig.prepare("resume", "x")
    cid = make_confirmation(rig.state, "launch", b2)
    assert jobs.enqueue_launch(rig.state, ce, b2, cid)
    row = rig.launches()[-1]
    rig.hand_over(rig.jobs()[-1]["id"], "x-a2")
    rig.set_run("x-a2", "failed")
    _, b3, _ = rig.prepare("resume", "x-a2")
    assert b3["resume"]["attempt"] == 3
    with pytest.raises(jobs.JobRefused):
        jobs.enqueue_launch(rig.state, ce, b3, cid)                 # the spent yes
    cid_new = make_confirmation(rig.state, "launch", b2)
    with pytest.raises(jobs.JobRefused, match=CHANGED):
        jobs.enqueue_launch(rig.state, ce, b3, cid_new)             # an unspent yes made for attempt 2


def test_tc097_the_yes_for_one_predecessor_cannot_resume_another(rig):
    # TC-097
    from abf_platform import jobs
    rig.first("x")
    rig.first("y")
    ce, bx, _ = rig.prepare("resume", "x")
    _, by, _ = rig.prepare("resume", "y")
    cid = make_confirmation(rig.state, "launch", bx)
    with pytest.raises(jobs.JobRefused, match=CHANGED):
        jobs.enqueue_launch(rig.state, ce, by, cid)
    assert len(rig.jobs()) == 2        # the two first launches


def test_tc078_tc079_a_pending_request_is_no_yes_for_a_resume_or_a_relaunch(rig):
    # TC-078, TC-079: see test_resume_platform for the pending request made through the action; this is the queue's own refusal
    from abf_platform import confirm, jobs
    rig.first("x")
    for verb in ("resume", "relaunch"):
        ce, b, _ = rig.prepare(verb, "x")
        rid = confirm.create_pending(rig.state, "launch", ce, b, "text", None)
        with pytest.raises(jobs.JobRefused, match="還沒有人確認"):
            jobs.enqueue_launch(rig.state, ce, b, rid)
    assert len(rig.jobs()) == 1
