# Nothing existing: tests of the clean_work kind in the confirmation pipe and the job queue of the platform; no earlier test handles this kind.
"""cloud-cleanup-b: the platform knows `clean_work` (request, 7 days, queue, answer, hand-off record). Nothing builds such a request yet.
Test cases are named in the comments (TC-001 ...), they come from the cloud-cleanup-b spec folder. Everything here is done at the
abf_platform layer with a database and a fake clock; no web page, no agent process."""
import json
import re
import sqlite3
from pathlib import Path

import pytest

from helpers import Clock

PKG = Path(__file__).resolve().parents[1]
T0 = 1_800_000_000.0
DAY = 86400.0


@pytest.fixture
def clock():
    return Clock(T0)


@pytest.fixture
def db(tmp_path, clock):
    from abf_platform import store
    path = tmp_path / "platform.db"
    store.connect_state(path).close()
    return path


def sql(db, text, args=()):
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        with con:
            return con.execute(text, args).fetchall()
    finally:
        con.close()


def add_agent(db, name="a1", owner=1, seen=T0):
    sql(db, "INSERT OR REPLACE INTO agents (name, version, first_seen_at, last_seen_at, owner_user_id) VALUES (?, '0.1', ?, ?, ?)",
        (name, seen, seen, owner))


def add_ce(db, name="ce1", platform="slurm-platform", status="available", agent="a1", owner=1):
    sql(db, "INSERT INTO compute_envs (name, platform, agent, status, config_json, created_at, updated_at, owner_user_id) "
            "VALUES (?, ?, ?, ?, '{}', 1, 1, ?)", (name, platform, agent, status, owner))


def add_launch(db, run="run-one", folder="/data/u1/run-one", sid=4242, user=1, ce="ce1", agent="a1", cleaned=None):
    sql(db, "INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, user_id, work_cleaned_at) "
            "VALUES (?, ?, ?, ?, ?, 1, 2, ?, ?)", (run, sid, folder, ce, agent, user, cleaned))


def bundle(run="run-one", **over):
    b = {"version": 1, "run_name": run, "slurm_job_id": 4242, "run_folder": "/data/u1/" + run, "agent": "a1", "ce": "ce1",
         "work": "/data/u1/%s/work" % run}
    b.update(over)
    return {k: v for k, v in b.items() if v is not None}


@pytest.fixture
def world(db):
    """One online agent, one available Slurm environment, one run of user 1."""
    add_agent(db)
    add_ce(db)
    add_launch(db)
    return db


def pend(db, clock, b=None, caller=1, ce="ce1", kind="clean_work"):
    from abf_platform import confirm
    return confirm.create_pending(db, kind, ce, b or bundle(), "screen", caller, clock=clock)


def conf_row(db, kind, b, state="confirmed", used=None, sha=None, caller=1, cid=None):
    from abf_platform import common
    import secrets
    cid = cid or secrets.token_hex(16)
    sql(db, "INSERT INTO confirmations (id, sha256, kind, created_at, used_at, caller_user_id, state) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cid, sha or common.bundle_sha256(b), kind, T0, used, caller, state))
    return cid


def enqueue(db, clock, b=None, kind="clean_work", cid=None, ce="ce1", caller=1, offline_after=1e9):
    from abf_platform import jobs
    b = b if b is not None else bundle()
    if cid is None:
        cid = conf_row(db, {"clean_work": "clean_work"}.get(kind, kind), b, caller=caller)
    return jobs.transaction(db, lambda con: jobs.enqueue_confirmed(con, ce, kind, b, cid, clock(), 600, offline_after))


def jobs_count(db, kind=None):
    if kind:
        return sql(db, "SELECT COUNT(*) FROM jobs WHERE kind = ?", (kind,))[0][0]
    return sql(db, "SELECT COUNT(*) FROM jobs")[0][0]


def approve(db, clock, rid, caller=1, **kw):
    from abf_platform import confirm
    return confirm.approve(db, rid, "PAGE", caller, clock=clock, offline_after=1e9, **kw)


def job_answered(db, clock, state, result, b=None, claim_agent="a1"):
    """Queue a clean_work job through the pipe, claim it, and take the agent's answer."""
    from abf_platform import jobs
    jid = enqueue(db, clock, b)
    got = jobs.claim(db, claim_agent, clock)
    assert got is not None and got["id"] == jid
    status, body = jobs.take_result(db, claim_agent, jid, state, result, clock)
    return jid, status, body


# ---- US1: the request is not the yes ----------------------------------------------------------------------------------------

def test_tc001_job_kind_map_has_clean_work_and_the_other_two_unchanged():
    # TC-001
    from abf_platform import confirm
    assert confirm.JOB_KIND == {"launch": "launch_nextflow", "cancel": "cancel_run", "clean_work": "clean_work"}


def test_tc002_tc003_a_clean_work_request_lives_seven_days_and_the_others_still_ten_minutes(world, clock):
    # TC-002, TC-003
    from abf_platform import confirm
    rid = pend(world, clock)
    row = sql(world, "SELECT created_at, expires_at FROM confirmations WHERE id = ?", (rid,))[0]
    assert row["expires_at"] - row["created_at"] == 604800
    assert confirm.CLEAN_PENDING_SECONDS == 7 * 86400
    for kind in ("launch", "cancel"):
        rid = pend(world, clock, bundle(kind), kind=kind)
        row = sql(world, "SELECT created_at, expires_at FROM confirmations WHERE id = ?", (rid,))[0]
        assert row["expires_at"] - row["created_at"] == 600


def test_tc004_tc005_same_person_same_content_gets_the_same_request_and_another_person_does_not(world, clock):
    # TC-004, TC-005
    a = pend(world, clock)
    assert pend(world, clock) == a
    b = pend(world, clock, caller=2)
    assert b != a
    assert sql(world, "SELECT COUNT(*) FROM confirmations")[0][0] == 2


def test_tc006_a_pending_clean_request_is_never_a_confirmation_and_no_job_exists_until_the_person_approves(world, clock):
    # TC-006
    before = jobs_count(world)
    rid = pend(world, clock)
    assert jobs_count(world) == before
    assert jobs_count(world, "clean_work") == 0
    assert sql(world, "SELECT state FROM confirmations WHERE id = ?", (rid,))[0][0] == "pending"


def test_tc007_approve_through_page_queues_exactly_one_clean_work_job_with_this_confirmation(world, clock):
    # TC-007
    rid = pend(world, clock)
    got_rid, job_id = approve(world, clock, rid)
    assert got_rid == rid
    jobs = sql(world, "SELECT * FROM jobs WHERE kind = 'clean_work'")
    assert len(jobs) == 1 and jobs[0]["id"] == job_id and jobs[0]["confirmation_id"] == rid
    c = sql(world, "SELECT state, channel FROM confirmations WHERE id = ?", (rid,))[0]
    assert (c["state"], c["channel"]) == ("confirmed", "PAGE")


def test_tc008_approving_twice_gives_already_and_one_job(world, clock):
    # TC-008
    from abf_platform import confirm
    rid = pend(world, clock)
    _, job_id = approve(world, clock, rid)
    with pytest.raises(confirm.NotApproved) as e:
        approve(world, clock, rid)
    assert e.value.status == "already" and e.value.job_id == job_id
    assert jobs_count(world, "clean_work") == 1


def test_tc009_tc010_another_users_request_cannot_be_approved_and_cannot_be_read(world, clock):
    # TC-009, TC-010
    from abf_platform import confirm
    rid = pend(world, clock)
    with pytest.raises(confirm.NotApproved) as e:
        approve(world, clock, rid, caller=2)
    assert e.value.status == "not_yours"
    assert jobs_count(world) == 0
    assert sql(world, "SELECT state FROM confirmations WHERE id = ?", (rid,))[0][0] == "pending"
    assert confirm.open_clean_requests(world, 2, clock=clock) == {}
    assert confirm.describe(world, rid, clock=clock)["caller_user_id"] == 1


def test_tc011_an_expired_clean_request_cannot_be_approved_and_queues_nothing(world, clock):
    # TC-011
    from abf_platform import confirm
    rid = pend(world, clock)
    clock.t = T0 + 7 * DAY + 1
    with pytest.raises(confirm.NotApproved) as e:
        approve(world, clock, rid)
    assert e.value.status == "expired"
    assert jobs_count(world) == 0
    assert sql(world, "SELECT state FROM confirmations WHERE id = ?", (rid,))[0][0] == "void"


def test_tc012_tc013_a_void_or_forgotten_request_cannot_be_approved(world, clock):
    # TC-012, TC-013
    from abf_platform import confirm
    rid = pend(world, clock)
    assert confirm.void(world, rid, "no")
    with pytest.raises(confirm.NotApproved) as e:
        approve(world, clock, rid)
    assert e.value.status == "void"
    other = pend(world, clock, bundle("run-two"))
    confirm.forget_content(world, "run-two")
    with pytest.raises(confirm.NotApproved) as e:
        approve(world, clock, other)
    assert e.value.status == "void"
    assert jobs_count(world) == 0


def test_tc014_tc015_a_clean_work_confirmation_cannot_queue_a_launch_or_a_cancel_and_the_other_way_round(world, clock):
    # TC-014, TC-015
    from abf_platform import jobs
    b = bundle()
    clean = conf_row(world, "clean_work", b)
    for kind in ("launch_nextflow", "cancel_run"):
        with pytest.raises(jobs.JobRefused, match="憑證種類不符"):
            enqueue(world, clock, b, kind=kind, cid=clean)
    for conf_kind in ("launch", "cancel"):
        cid = conf_row(world, conf_kind, b)
        with pytest.raises(jobs.JobRefused, match="憑證種類不符"):
            enqueue(world, clock, b, kind="clean_work", cid=cid)
    assert jobs_count(world) == 0


def test_tc016_facts_of_a_clean_work_request_are_kind_run_and_work_only(world, clock):
    # TC-016, TC-017
    from abf_platform import confirm
    rid = pend(world, clock)
    assert confirm.facts(world, rid) == {"what": "clean_work", "run_name": "run-one", "work": "/data/u1/run-one/work"}
    confirm.forget_content(world, "run-one")
    assert confirm.facts(world, rid) is None


def test_tc018_to_tc021_open_clean_requests_returns_only_my_own_unexpired_pending_ones_with_content(world, clock):
    # TC-018, TC-019, TC-020, TC-021
    from abf_platform import confirm
    a, b = pend(world, clock, bundle("run-a")), pend(world, clock, bundle("run-b"))
    assert confirm.open_clean_requests(world, 1, clock=clock) == {"run-a": a, "run-b": b}
    pend(world, clock, bundle("run-x"), caller=2)                       # somebody else's
    void = pend(world, clock, bundle("run-v"))
    confirm.void(world, void, "x")
    forgotten = pend(world, clock, bundle("run-f"))
    confirm.forget_content(world, "run-f")
    add_launch(world, "run-c", "/data/u1/run-c")
    done = pend(world, clock, bundle("run-c"))
    approve(world, clock, done)
    assert confirm.open_clean_requests(world, 1, clock=clock) == {"run-a": a, "run-b": b}
    assert forgotten not in confirm.open_clean_requests(world, 1, clock=clock).values()
    clock.t = T0 + 7 * DAY + 5                                          # past the time
    assert confirm.open_clean_requests(world, 1, clock=clock) == {}


def test_tc022_forget_clears_clean_work_requests_and_jobs_of_the_run(world, clock):
    # TC-022
    from abf_platform import confirm
    add_launch(world, "run-two", "/data/u1/run-two")
    pending = pend(world, clock, bundle("run-two"))
    other_pending = pend(world, clock, bundle("run-one"))
    jid, _, _ = job_answered(world, clock, "done", {"ok": True, "cleaned": True}, bundle("run-one"))
    confirm.forget_content(world, "run-one")
    j = sql(world, "SELECT args_json, forgotten_at FROM jobs WHERE id = ?", (jid,))[0]
    assert json.loads(j["args_json"]) == {"forgotten": True, "bundle": {"run_name": "run-one"}} and j["forgotten_at"] is not None
    row = sql(world, "SELECT state, bundle_json FROM confirmations WHERE id = ?", (other_pending,))[0]
    assert (row["state"], row["bundle_json"]) == ("void", None)
    row = sql(world, "SELECT state, bundle_json FROM confirmations WHERE id = ?", (pending,))[0]
    assert row["state"] == "pending" and row["bundle_json"] is not None        # another run: untouched


def test_tc023_forget_waits_for_a_queued_clean_work_job(world, clock):
    # TC-023
    from abf_platform import confirm, jobs
    enqueue(world, clock)
    with pytest.raises(jobs.JobRefused, match="還有工作在排隊"):
        confirm.forget_content(world, "run-one")
    assert sql(world, "SELECT COUNT(*) FROM jobs WHERE forgotten_at IS NOT NULL")[0][0] == 0


# ---- US2: the slots ---------------------------------------------------------------------------------------------------------

def test_tc024_tc025_clean_work_does_not_use_the_ten_slots_and_the_ten_do_not_block_it(world, clock):
    # TC-024, TC-025
    from abf_platform import jobs
    for i in range(10):
        pend(world, clock, bundle("l%d" % i), kind="launch")
    pend(world, clock, bundle("c0"))                                    # TC-024
    for i in range(1, 13):
        pend(world, clock, bundle("c%d" % i))
    with pytest.raises(jobs.JobRefused):                                # the old rule is unchanged
        pend(world, clock, bundle("l-eleven"), kind="launch")
    db2 = world.parent / "other.db"
    from abf_platform import store
    store.connect_state(db2).close()
    for i in range(12):
        pend(db2, clock, bundle("c%d" % i))
    for i in range(10):
        pend(db2, clock, bundle("l%d" % i), kind="launch")              # TC-025
    with pytest.raises(jobs.JobRefused):
        pend(db2, clock, bundle("l-eleven"), kind="launch")


def test_tc026_to_tc029_the_clean_limit_is_fifty_each_unexpired_and_per_person(world, clock):
    # TC-026, TC-027, TC-028, TC-029
    from abf_platform import confirm, jobs
    assert confirm.MAX_OPEN_CLEAN == 50
    for i in range(49):
        pend(world, clock, bundle("c%d" % i))
    pend(world, clock, bundle("c49"))                                   # the fiftieth: TC-027
    with pytest.raises(jobs.JobRefused) as e:                           # TC-026
        pend(world, clock, bundle("c50"))
    msg = str(e.value)
    assert "50" in msg and "清理提醒" in msg and "Traceback" not in msg and "SELECT" not in msg
    pend(world, clock, bundle("c0"), caller=2)                        # TC-029
    clock.t = T0 + 7 * DAY + 10                                         # TC-028
    pend(world, clock, bundle("fresh"))


# ---- US3: the queue ---------------------------------------------------------------------------------------------------------

def test_tc030_tc031_tc032_the_deadline_of_clean_work_is_600_and_the_variable_overrides_it(monkeypatch):
    # TC-030, TC-031, TC-032
    from abf_platform import jobs
    monkeypatch.delenv("ABF_PLATFORM_DEADLINE_CLEAN", raising=False)
    assert jobs.DEADLINE_SECONDS["clean_work"] == 600 and jobs.deadline_seconds("clean_work") == 600
    monkeypatch.setenv("ABF_PLATFORM_DEADLINE_CLEAN", "900")
    assert jobs.deadline_seconds("clean_work") == 900
    for bad in ("abc", "0", "-5"):
        monkeypatch.setenv("ABF_PLATFORM_DEADLINE_CLEAN", bad)
        assert jobs.deadline_seconds("clean_work") == 600


def test_tc033_kinds_are_seven_and_clean_work_is_last_and_confirmed_map_has_it():
    # TC-033
    from abf_platform import jobs
    assert jobs.KINDS == ("preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records", "read_task_log", "clean_work", "put_upload")
    assert jobs.CONFIRMED == {"launch_nextflow": "launch", "cancel_run": "cancel", "clean_work": "clean_work"}


def test_tc034_a_clean_work_job_is_refused_without_a_confirmation_at_the_queue_and_at_the_database(world, clock):
    # TC-034, TC-035
    from abf_platform import jobs
    for cid in (None, "", "no-such-id"):
        with pytest.raises(jobs.JobRefused):
            jobs.transaction(world, lambda con, c=cid: jobs.enqueue_confirmed(con, "ce1", "clean_work", bundle(), c, clock(), 600, 1e9))
    assert jobs_count(world) == 0
    with pytest.raises(sqlite3.IntegrityError):
        sql(world, "INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                   "VALUES ('a1', 'ce1', 'clean_work', '{}', 'queued', 1, 2)")


@pytest.mark.parametrize("status", ["available", "invalid"])
def test_tc036_slurm_takes_clean_work_while_available_or_invalid(world, clock, status):
    # TC-036
    sql(world, "UPDATE compute_envs SET status = ?", (status,))
    enqueue(world, clock)
    assert jobs_count(world, "clean_work") == 1


@pytest.mark.parametrize("status", ["disabled", "unsupported"])
def test_tc037_slurm_still_refuses_a_disabled_or_unsupported_environment(world, clock, status):
    # TC-037
    from abf_platform import jobs
    sql(world, "UPDATE compute_envs SET status = ?", (status,))
    with pytest.raises(jobs.JobRefused):
        enqueue(world, clock)
    assert jobs_count(world) == 0


def test_tc038_an_offline_agent_refuses_clean_work_in_plain_words(world, clock):
    # TC-038
    from abf_platform import jobs
    clock.t = T0 + 100000
    with pytest.raises(jobs.JobRefused, match="代理離線") as e:
        enqueue(world, clock, offline_after=60)
    assert "Traceback" not in str(e.value) and jobs_count(world) == 0


@pytest.mark.parametrize("status", ["available", "invalid", "creating"])
def test_tc039_a_google_batch_environment_lets_clean_work_through(db, clock, status):
    # TC-039
    add_agent(db)
    add_ce(db, platform="googlebatch-platform", status=status)
    add_launch(db)
    enqueue(db, clock)
    assert jobs_count(db, "clean_work") == 1


@pytest.mark.parametrize("status", ["unsupported", "disabled"])
def test_tc040_a_google_batch_environment_still_refuses_disabled_or_unsupported(db, clock, status):
    # TC-040
    from abf_platform import jobs
    add_agent(db)
    add_ce(db, platform="googlebatch-platform", status=status)
    add_launch(db)
    with pytest.raises(jobs.JobRefused):
        enqueue(db, clock)
    assert jobs_count(db) == 0


@pytest.mark.parametrize("kind", ["list_site_files", "fetch_run_records", "read_task_log"])
def test_tc041_other_google_batch_job_kinds_are_still_refused(db, clock, kind):
    # TC-041
    from abf_platform import jobs
    add_agent(db)
    add_ce(db, platform="googlebatch-platform")
    with pytest.raises(jobs.JobRefused, match="尚未支援"):
        jobs.transaction(db, lambda con: jobs._target(con, "ce1", kind, clock(), 1e9))


def test_tc042_tc043_a_run_with_no_hand_off_row_or_no_job_number_is_refused_in_plain_words(db, clock):
    # TC-042, TC-043, TC-081
    from abf_platform import jobs
    add_agent(db)
    add_ce(db)
    with pytest.raises(jobs.JobRefused, match="Slurm") as e:
        enqueue(db, clock)
    assert "Traceback" not in str(e.value) and "SELECT" not in str(e.value)
    add_launch(db, sid=None)
    with pytest.raises(jobs.JobRefused, match="Slurm"):
        enqueue(db, clock)
    assert jobs_count(db) == 0


def test_tc044_another_users_run_is_not_there_for_the_caller(world, clock):
    # TC-044
    from abf_platform import jobs
    with pytest.raises(jobs.JobRefused) as e:
        enqueue(world, clock, caller=2)
    assert jobs_count(world) == 0
    sql(world, "UPDATE compute_envs SET owner_user_id = 2")
    sql(world, "UPDATE agents SET owner_user_id = 2")
    with pytest.raises(jobs.JobRefused, match="Slurm") as e2:             # the run is user 1's: to user 2 it is not there
        enqueue(world, clock, caller=2)
    assert jobs_count(world) == 0 and "run-one" in str(e2.value)


def test_tc045_tc046_a_folder_or_a_job_number_that_differs_from_the_record_is_refused(world, clock):
    # TC-045, TC-046, TC-081
    from abf_platform import jobs
    with pytest.raises(jobs.JobRefused) as e:
        enqueue(world, clock, bundle(run_folder="/data/u1/run-onf"))
    assert "Traceback" not in str(e.value)
    with pytest.raises(jobs.JobRefused):
        enqueue(world, clock, bundle(slurm_job_id=4243))
    assert jobs_count(world) == 0


def test_tc047_work_cleaned_at_already_set_is_refused_in_plain_words(db, clock):
    # TC-047, TC-081
    from abf_platform import jobs
    add_agent(db)
    add_ce(db)
    add_launch(db, cleaned=5.0)
    with pytest.raises(jobs.JobRefused, match="清過") as e:
        enqueue(db, clock)
    assert "Traceback" not in str(e.value) and jobs_count(db) == 0


def test_tc048_tc049_tc070_a_bundle_with_other_keys_is_refused(world, clock):
    # TC-048, TC-049, TC-070
    from abf_platform import jobs
    for b in (bundle(paths=["/data/x"]), bundle(work=None), bundle(works=["/a", "/b"]), bundle(version=None)):
        with pytest.raises(jobs.JobRefused):
            enqueue(world, clock, b)
    assert jobs_count(world) == 0


def test_tc050_an_agent_that_is_not_the_environments_agent_is_refused(world, clock):
    # TC-050
    from abf_platform import jobs
    with pytest.raises(jobs.JobRefused, match="a1") as e:
        enqueue(world, clock, bundle(agent="a9"))
    assert "a9" in str(e.value) and jobs_count(world) == 0


# ---- US4: the answer --------------------------------------------------------------------------------------------------------

def test_tc051_tc052_clean_result_keeps_only_the_expected_keys():
    # TC-051, TC-052
    from abf_platform import jobs
    out = jobs.clean_result("clean_work", {"ok": True, "message": "m", "run_name": "run-one", "cleaned": True, "slurm_job_id": 9,
                                           "path": "/x", "left_on_site": "y", "entries": [{"name": "z"}]})
    assert out == {"ok": True, "message": "m", "run_name": "run-one", "cleaned": True}


@pytest.mark.parametrize("value", [1, "true", "yes", False, None])
def test_tc053_only_the_real_true_counts(value):
    # TC-053
    from abf_platform import jobs
    out = jobs.clean_result("clean_work", {"ok": True, "cleaned": value})
    assert out["cleaned"] is False
    assert jobs.clean_result("clean_work", {"ok": True})["cleaned"] is False


def test_tc054_the_texts_are_bounded():
    # TC-054
    from abf_platform import jobs
    out = jobs.clean_result("clean_work", {"ok": True, "message": "x" * 5000, "run_name": "r" * 200, "cleaned": True})
    assert len(out["message"]) <= 2000 and len(out["run_name"]) <= 64


def test_tc055_tc064_only_the_row_of_the_jobs_own_run_and_number_is_written(world, clock):
    # TC-055, TC-064
    sql(world, "DELETE FROM launches")
    add_launch(world, "run-one", "/data/u1/run-one", sid=1111)           # same name, older row, another number
    add_launch(world, "run-two", "/data/u1/run-two", sid=4242)           # another run, same number
    add_launch(world)                                                     # the newest row of run-one: the one the job is about
    jid, status, body = job_answered(world, clock, "done", {"ok": True, "cleaned": True, "run_name": "run-two", "slurm_job_id": 1111})
    assert status == 200 and body["accepted"] is True
    rows = {(r["run_name"], r["slurm_job_id"]): r["work_cleaned_at"] for r in sql(world, "SELECT * FROM launches")}
    assert rows[("run-one", 4242)] == T0
    assert rows[("run-one", 1111)] is None and rows[("run-two", 4242)] is None


@pytest.mark.parametrize("state,result", [
    ("refused", {"ok": False, "cleaned": True}),                         # TC-056
    ("error", {"ok": False, "cleaned": True}),                           # TC-057
    ("done", {"ok": False, "cleaned": True}),                            # TC-058
    ("done", {"ok": True, "cleaned": False}),                            # TC-059
    ("done", {"ok": True}),                                              # TC-059
])
def test_tc056_to_tc060_other_answers_write_nothing_and_do_not_retry(world, clock, state, result):
    # TC-056, TC-057, TC-058, TC-059, TC-060
    job_answered(world, clock, state, result)
    assert sql(world, "SELECT work_cleaned_at FROM launches")[0][0] is None
    assert jobs_count(world, "clean_work") == 1


def test_tc061_a_late_answer_after_the_deadline_is_still_recorded(world, clock):
    # TC-061
    from abf_platform import jobs
    jid = enqueue(world, clock)
    assert jobs.claim(world, "a1", clock)["id"] == jid
    clock.t = T0 + 5000
    status, body = jobs.take_result(world, "a1", jid, "done", {"ok": True, "cleaned": True}, clock)
    assert body == {"accepted": False, "late": True}
    j = sql(world, "SELECT state, late_result_json FROM jobs WHERE id = ?", (jid,))[0]
    assert j["state"] == "expired" and json.loads(j["late_result_json"])["result"]["cleaned"] is True
    assert sql(world, "SELECT work_cleaned_at FROM launches")[0][0] == clock.t


def test_tc062_a_late_answer_for_a_forgotten_job_writes_nothing_and_does_not_fail(world, clock):
    # TC-062
    from abf_platform import confirm, jobs
    jid = enqueue(world, clock)
    jobs.claim(world, "a1", clock)
    sql(world, "UPDATE jobs SET state = 'done', finished_at = 1 WHERE id = ?", (jid,))
    confirm.forget_content(world, "run-one")
    sql(world, "UPDATE jobs SET state = 'expired' WHERE id = ?", (jid,))
    status, body = jobs.take_result(world, "a1", jid, "done", {"ok": True, "cleaned": True}, clock)
    assert status == 200 and body["late"] is True
    assert sql(world, "SELECT work_cleaned_at FROM launches")[0][0] is None


def test_tc063_end_to_end_the_cleaned_answer_is_kept(world, clock):
    # TC-063
    from abf_platform import jobs
    rid = pend(world, clock)
    _, jid = approve(world, clock, rid)
    got = jobs.claim(world, "a1", clock)
    assert got["kind"] == "clean_work" and got["confirmation"]["id"] == rid
    assert sql(world, "SELECT used_at FROM confirmations WHERE id = ?", (rid,))[0][0] is not None
    status, body = jobs.take_result(world, "a1", jid, "done", {"ok": True, "cleaned": True, "message": "ok"}, clock)
    assert body["accepted"] is True
    assert json.loads(sql(world, "SELECT result_json FROM jobs WHERE id = ?", (jid,))[0][0])["cleaned"] is True
    assert sql(world, "SELECT work_cleaned_at FROM launches")[0][0] == T0


# ---- US5: not in scope ------------------------------------------------------------------------------------------------------

def test_tc065_tc066_nothing_builds_a_clean_work_request_and_nothing_acts_by_itself(world, clock):
    # TC-065, TC-066
    from abf_platform import confirm
    rid = pend(world, clock)
    clock.t = T0 + 30 * DAY
    pend(world, clock, bundle("run-other"), kind="launch")               # maintenance runs
    from abf_platform import jobs
    jobs.claim(world, "a1", clock)
    assert sql(world, "SELECT state FROM confirmations WHERE id = ?", (rid,))[0][0] == "pending"
    assert jobs_count(world, "clean_work") == 0
    src = "".join(p.read_text(encoding="utf-8") for p in (PKG / "abf_platform").rglob("*.py"))
    assert len(re.findall(r"create_pending\([^)]*clean_work", src)) == 0 and "request_clean" not in src


def test_tc067_no_new_entry_point_for_clean_work():
    # TC-067
    from abf_platform import jobs
    assert not hasattr(jobs, "enqueue_clean")
    places = [PKG / "abf_platform" / "mcp_server.py", PKG / "abf_platform" / "cli.py", PKG / "abf_launch" / "cli.py"]
    places += list((PKG / "abf_platform" / "actions").glob("*.py")) + list((PKG / "abf_platform").glob("web*.py"))
    assert places and [p.name for p in places if "clean_work" in p.read_text(encoding="utf-8")] == []


def test_tc068_tc076_the_packages_have_no_deletion_code_and_no_program_start():
    # TC-068, TC-076
    forbidden = [r"(?<![a-z])rm -", r"storage rm", r"rmtree", r"\bsubprocess\b", r"\bPopen\b", r"\bos\.system\b", r"\bthreading\b", r"\bThread\(",
                 r"\bsched\b", r"\bcron\b", r"while\s+True", r"asyncio\.create_task"]     # the words of TC-061 are scanned by test_scope (TC-077)
    hits = []
    for pkg in ("abf_platform", "abf_launch"):
        for f in (PKG / pkg).rglob("*.py"):
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                for pat in forbidden:
                    if re.search(pat, line):
                        hits.append("%s:%d %s" % (f.name, n, line.strip()))
    assert hits == []


def test_tc069_launch_and_cancel_keep_their_deadlines_and_ten_minute_requests(world, clock):
    # TC-069
    from abf_platform import jobs, confirm
    assert (jobs.DEADLINE_SECONDS["launch_nextflow"], jobs.DEADLINE_SECONDS["cancel_run"]) == (300, 90)
    assert confirm.PENDING_SECONDS == 600


def test_tc071_the_run_state_is_not_read():
    # TC-071
    for name in ("confirm.py", "jobs.py"):
        assert "final_status" not in (PKG / "abf_platform" / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("state", ["pending", "void", "used", "wrong_hash"])
def test_tc075_a_confirmation_that_is_not_a_yes_for_this_content_queues_nothing(world, clock, state):
    # TC-075
    from abf_platform import jobs
    b = bundle()
    kw = {"pending": dict(state="pending"), "void": dict(state="void"), "used": dict(used=T0), "wrong_hash": dict(sha="0" * 64)}[state]
    cid = conf_row(world, "clean_work", b, **kw)
    with pytest.raises(jobs.JobRefused):
        enqueue(world, clock, b, cid=cid)
    assert jobs_count(world) == 0
