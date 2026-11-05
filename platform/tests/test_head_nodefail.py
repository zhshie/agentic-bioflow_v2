# Nothing existing: tests of what the platform shows for a run whose Slurm head job was ended by the scheduler; the run states and the fake index are ours.
"""head-nodefail-detect, the platform side: a `lost` run whose newest finished fetch says the head job ended as NODE_FAIL (or another
bad end) is shown as failed, with the scheduler's word as the reason, and may be resumed or relaunched. Test cases are named in the
comments (TC-001 ... TC-023); see specs/head-nodefail-detect/test-case.md."""
import json
import re
import sqlite3
import time

import pytest

from resume_harness import FakePerson, Rig
from owner_harness import Duo

BAD = ["NODE_FAIL", "BOOT_FAIL", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "FAILED", "DEADLINE", "PREEMPTED", "REVOKED"]
ALIVE = ["RUNNING", "PENDING", "COMPLETING", "REQUEUED", "SUSPENDED", "CONFIGURING"]
SLURM = 654018
FIVE = {"status_seqera", "failed_tasks", "failure_reason", "log", "actions"}
ME = object()      # "the person who owns the lost runs of this file" (owner(rig)); pass None to ask as no one


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


def lost_run(rig, run="x", slurm=SLURM, succeeded=3, caller=ME, status=None):
    """A run that was handed over to Slurm, whose last Nextflow message is long ago and that has no completion record: lost."""
    if caller is ME:
        caller = owner(rig)
    rig.first(run, status=status, slurm=slurm, caller=caller)
    con = sqlite3.connect(str(rig.index))
    with con:
        con.execute("UPDATE runs SET last_message_at = ?, n_succeeded = ? WHERE run_name = ?", (time.time() - 100000, succeeded, run))
    con.close()
    return "id-" + run


def add_fetch(rig, run, scheduler, state="done", age=0, with_key=True, slurm=SLURM):
    """A fetch_run_records job of this run as the platform keeps it, with what the site said about the head job."""
    launch = rig.sql("SELECT * FROM launches WHERE run_name = ? ORDER BY id DESC LIMIT 1", (run,))[0]
    job = rig.sql("SELECT * FROM jobs WHERE id = ?", (launch["job_id"],))[0]
    result = {"ok": True, "files": [], "refused": []}
    if with_key:
        result["scheduler"] = scheduler
    args = {"run_name": run, "slurm_job_id": str(slurm)}
    now = time.time()
    con = sqlite3.connect(str(rig.state))
    with con:
        cur = con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, result_json, created_at, deadline_at, finished_at) "
                          "VALUES (?, ?, 'fetch_run_records', ?, ?, ?, ?, ?, ?)",
                          (job["agent"], job["compute_env"], json.dumps(args), state,
                           json.dumps(result) if state == "done" else None, now - age - 5, now - age + 175,
                           now - age if state == "done" else None))
    con.close()
    return cur.lastrowid


def fact(state, source="sacct", job_id=str(SLURM)):
    return {"job_id": job_id, "state": state, "source": source}


def owner(rig):
    """A real person who owns the lost runs below: only a run a caller owns is asked about (ruling P3)."""
    if not hasattr(rig, "_duo"):
        rig._duo = Duo(rig.w)
    return rig._duo.a


def get(rig, run_id, caller=ME):
    from abf_platform import actions
    caller = owner(rig) if caller is ME else caller
    return actions.get_run(rig.index, run_id, caller=caller, platform_path=rig.state)


def listed(rig, name, caller=ME):
    from abf_platform import actions
    caller = owner(rig) if caller is ME else caller
    rows = actions.list_runs(rig.index, caller=caller, platform_path=rig.state)["runs"]
    return [r for r in rows if r["name"] == name]


def fetch_jobs(rig):
    return rig.sql("SELECT * FROM jobs WHERE kind = 'fetch_run_records' ORDER BY id")


def reason(state, source="sacct", number=SLURM):
    return "Slurm head job %s ended as %s (%s)" % (number, state, source)


# ---- US1 ------------------------------------------------------------------------------------------------------------------------

def test_tc001_tc002_a_lost_run_with_a_nodefail_head_is_failed_and_says_why(rig):
    # TC-001, TC-002 (t1: platform job 78, Slurm 654018)
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"))
    v = get(rig, rid)
    assert v["status"] == "failed"
    assert v["failure"]["failure_reason"] == "Slurm head job 654018 ended as NODE_FAIL (sacct)"
    assert set(v["failure"]) == FIVE
    assert v["failure"]["status_seqera"] == "failed"
    assert v["failure"]["actions"] == ["resume", "relaunch"]


@pytest.mark.parametrize("state", BAD)
@pytest.mark.parametrize("source", ["sacct", "squeue"])
def test_tc003_every_bad_end_of_the_table_is_failed_with_its_own_word(rig, state, source):
    # TC-003
    rid = lost_run(rig)
    add_fetch(rig, "x", fact(state, source))
    v = get(rig, rid)
    assert v["status"] == "failed" and v["failure"]["status_seqera"] == "failed"
    assert v["failure"]["failure_reason"] == reason(state, source)
    assert "resume" in v["failure"]["actions"] and "relaunch" in v["failure"]["actions"]


def test_tc004_the_list_shows_the_same_sentence(rig):
    # TC-004
    lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"))
    (row,) = listed(rig, "x")
    assert row["status"] == "failed"
    assert row["failure"]["failure_reason"] == reason("NODE_FAIL")
    assert get(rig, "id-x")["failure"] == row["failure"]


def test_tc004_the_overlay_is_in_the_action_layer_only():
    # TC-004: the routes and tools call the action layer; none of them knows the scheduler's words
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent / "abf_platform"
    for p in root.rglob("*.py"):
        if p.name in ("jobs.py", "failures.py") or p.parent.name == "actions":
            continue
        text = p.read_text(encoding="utf-8")
        assert "NODE_FAIL" not in text and "head_state" not in text, p


# ---- US2 ------------------------------------------------------------------------------------------------------------------------

def test_tc005_get_run_asks_once_and_list_runs_asks_nothing(rig):
    # TC-005
    rid = lost_run(rig)
    before = rig.sql("SELECT COUNT(*) FROM jobs")[0][0]
    listed(rig, "x")
    assert rig.sql("SELECT COUNT(*) FROM jobs")[0][0] == before
    get(rig, rid)
    get(rig, rid)
    new = rig.sql("SELECT * FROM jobs ORDER BY id")[before:]
    assert [j["kind"] for j in new] == ["fetch_run_records"], [j["kind"] for j in new]
    assert json.loads(new[0]["args_json"])["slurm_job_id"] == str(SLURM)
    listed(rig, "x")
    assert len(fetch_jobs(rig)) == 1


def test_tc005_a_fresh_finished_fetch_is_not_asked_again_but_an_old_one_is(rig):
    # TC-005 (60 seconds)
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("RUNNING", "squeue"), age=10)
    get(rig, rid)
    assert len(fetch_jobs(rig)) == 1
    lost_run(rig, "y", slurm=777)
    add_fetch(rig, "y", fact("RUNNING", "squeue", "777"), age=120, slurm=777)
    get(rig, "id-y")
    assert len(fetch_jobs(rig)) == 3


def test_tc006_the_second_question_sees_what_the_first_one_found(rig):
    # TC-006
    rid = lost_run(rig)
    first = get(rig, rid)
    assert first["status"] == "lost" and first["failure"]["failure_reason"] is None
    (job,) = fetch_jobs(rig)
    result = {"ok": True, "files": [], "refused": [], "scheduler": fact("NODE_FAIL")}
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE jobs SET state = 'done', result_json = ?, finished_at = ? WHERE id = ?", (json.dumps(result), time.time(), job["id"]))
    con.close()
    second = get(rig, rid)
    assert second["status"] == "failed" and "NODE_FAIL" in second["failure"]["failure_reason"]


# ---- US4 ------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("state", ALIVE)
def test_tc012_a_head_that_is_alive_is_not_shown_as_failed(rig, state):
    # TC-012: the run stays as v3 shows it
    rid = lost_run(rig, succeeded=0)
    plain = get(rig, rid)
    add_fetch(rig, "x", fact(state, "squeue"))
    v = get(rig, rid)
    assert v["status"] == "lost" and v["failure"] == plain["failure"]
    assert v["failure"]["failure_reason"] is None and v["failure"]["status_seqera"] == "unknown"
    assert "resume" not in v["failure"]["actions"]
    (row,) = listed(rig, "x")
    assert row["status"] == "lost" and row["failure"] == plain["failure"]


def test_tc013_completed_without_a_record_stays_lost_and_cannot_be_resumed(rig):
    # TC-013
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("COMPLETED"))
    v = get(rig, rid)
    assert v["status"] == "lost" and v["failure"]["status_seqera"] == "unknown"
    assert v["failure"]["failure_reason"] == "Slurm head job 654018 completed but Nextflow left no completion record"
    assert "resume" not in v["failure"]["actions"]
    assert "還在跑" in rig.resume("x", person=FakePerson(True))["message"]


@pytest.mark.parametrize("how", ["other_job", "unknown_state", "too_long", "wrong_type", "lowercase", "no_fields"])
def test_tc014_a_fact_that_does_not_fit_is_ignored(rig, how):
    # TC-014 (a) (b) (c)
    rid = lost_run(rig)
    bad = {"other_job": fact("NODE_FAIL", job_id="1"), "unknown_state": fact("EXPLODED"), "too_long": fact("NODE_FAIL" + "X" * 500),
           "wrong_type": {"job_id": str(SLURM), "state": 7, "source": "sacct"}, "lowercase": fact("node_fail"),
           "no_fields": {"state": "NODE_FAIL"}}[how]
    add_fetch(rig, "x", bad)
    v = get(rig, rid)
    assert v["status"] == "lost" and v["failure"]["failure_reason"] is None
    assert "NODE_FAIL" not in json.dumps(v["failure"]) and "EXPLODED" not in json.dumps(v["failure"])


@pytest.mark.parametrize("newest", [fact("RUNNING", "squeue")])      # a newer None is TC-031 (ruling P2)
def test_tc014_only_the_newest_finished_fetch_counts(rig, newest):
    # TC-014 (d)
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=500)
    add_fetch(rig, "x", newest, age=100)
    v = get(rig, rid)
    assert v["status"] == "lost" and v["failure"]["failure_reason"] is None


def test_tc014_a_fetch_that_has_not_finished_is_no_fact(rig):
    # TC-014
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), state="claimed")
    assert get(rig, rid)["status"] == "lost"


# ---- US5 ------------------------------------------------------------------------------------------------------------------------

def test_tc015_the_gate_lets_a_nodefail_head_through(rig):
    # TC-015
    lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"))
    ce, b, row = rig.prepare("resume", "x")
    assert b["resume"]["of_run"] == "x" and row["slurm_job_id"] == SLURM
    assert rig.resume("x", person=FakePerson(True))["sent"] is True


@pytest.mark.parametrize("which", ["none", "completed", "running", "forged", "null"])
def test_tc016_every_other_lost_run_is_still_refused_with_the_old_sentence(rig, which):
    # TC-016
    lost_run(rig)
    if which == "completed":
        add_fetch(rig, "x", fact("COMPLETED"))
    elif which == "running":
        add_fetch(rig, "x", fact("RUNNING", "squeue"))
    elif which == "forged":
        add_fetch(rig, "x", fact("NODE_FAIL", job_id="9"))
    elif which == "null":
        add_fetch(rig, "x", None)
    out = rig.resume("x", person=FakePerson(True))
    assert out["sent"] is False and "還在跑，或已失去聯絡（lost）" in out["message"]
    out = rig.relaunch("x", person=FakePerson(True))
    assert out["sent"] is False and "lost" in out["message"]


# ---- the constitution and the safety net ------------------------------------------------------------------------------------------

def test_tc017_a_nextflow_record_wins_over_the_scheduler(rig):
    # TC-017
    rig.first("x", status="succeeded", slurm=SLURM, caller=owner(rig))
    add_fetch(rig, "x", fact("NODE_FAIL"))
    v = get(rig, "id-x")
    assert v["status"] == "succeeded" and v["failure"] is None
    assert listed(rig, "x")[0]["status"] == "succeeded"
    rig.first("z", status="failed", slurm=SLURM + 1, caller=owner(rig))
    add_fetch(rig, "z", fact("TIMEOUT", job_id=str(SLURM + 1)), slurm=SLURM + 1)
    assert get(rig, "id-z")["failure"]["failure_reason"] != reason("TIMEOUT", number=SLURM + 1)
    assert len(fetch_jobs(rig)) == 2      # and a succeeded or failed run is never asked about


def test_tc018_nothing_is_written_back_to_the_index(rig):
    # TC-018
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"))
    tables = lambda: sorted(r[0] for r in rig.sql("SELECT name FROM sqlite_master"))      # noqa: E731

    def rows():
        con = sqlite3.connect(str(rig.index))
        try:
            return con.execute("SELECT * FROM runs ORDER BY id").fetchall(), sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master"))
        finally:
            con.close()
    before, t_before = rows(), tables()
    get(rig, rid)
    listed(rig, "x")
    get(rig, rid)
    assert rows() == before and tables() == t_before
    con = sqlite3.connect(str(rig.index))
    assert con.execute("SELECT final_status FROM runs WHERE id = ?", (rid,)).fetchone()[0] is None
    con.close()


def test_tc019_another_user_neither_sees_the_overlay_nor_makes_a_fetch(tmp_path, monkeypatch):
    # TC-019
    rig = Rig(tmp_path, monkeypatch)
    duo = Duo(rig.w)
    lost_run(rig, "x", caller=duo.a)
    add_fetch(rig, "x", fact("NODE_FAIL"))
    before = len(fetch_jobs(rig))
    out = get(rig, "id-x", caller=duo.b)
    assert out["found"] is False and "NODE_FAIL" not in json.dumps(out)
    assert listed(rig, "x", caller=duo.b) == []
    assert len(fetch_jobs(rig)) == before
    assert get(rig, "id-x", caller=duo.a)["status"] == "failed"
    assert len(listed(rig, "x", caller=duo.a)) == 1


# ---- not in scope -------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("how", ["no_fetch", "null_fact"])
def test_tc021_without_a_fact_the_run_is_exactly_what_v3_shows(rig, how):
    # TC-021
    rid = lost_run(rig, succeeded=0)
    if how == "null_fact":
        add_fetch(rig, "x", None)
    v = get(rig, rid)
    assert v["status"] == "lost"
    assert v["failure"] == {"status_seqera": "unknown", "failed_tasks": [], "failure_reason": None, "log": None, "actions": ["relaunch"]}
    assert listed(rig, "x")[0]["status"] == "lost"


def test_tc022_a_launch_the_index_never_heard_of_is_still_not_found(rig):
    # TC-022
    from abf_platform import actions
    owner(rig)
    rig.first("ghost", slurm=SLURM, with_run=False)
    before = rig.sql("SELECT COUNT(*) FROM jobs")[0][0]
    assert actions.get_run(rig.index, "id-ghost", platform_path=rig.state)["found"] is False
    assert listed(rig, "ghost") == []
    assert rig.sql("SELECT COUNT(*) FROM jobs")[0][0] == before
    con = sqlite3.connect(str(rig.index))
    assert con.execute("SELECT COUNT(*) FROM runs WHERE run_name = 'ghost'").fetchone()[0] == 0
    con.close()


def test_tc023_no_new_kind_no_migration_no_new_state(rig):
    # TC-023
    import pathlib
    from abf_platform import jobs
    from abf_station import handlers
    assert jobs.KINDS == handlers.JOB_KINDS
    assert len(jobs.KINDS) == 10
    lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"))
    assert get(rig, "id-x")["status"] in ("failed",)       # shown as the third state of DESIGN.md; no fourth
    root = pathlib.Path(__file__).resolve().parent.parent
    assert not [p for p in root.rglob("migrations/*") if "head" in p.name.lower() and "node" in p.name.lower()]
    assert "sacct" not in (root / "abf_platform" / "store.py").read_text(encoding="utf-8")


# ---- adversarial review fixes (ruling O) ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("how", ["refused", "error", "expired"])
def test_tc026_any_fetch_within_a_minute_stops_a_new_one(rig, how):
    # TC-026 (1): a refused, failed or expired read-back counts like a finished one
    rid = lost_run(rig)
    add_fetch(rig, "x", None, state=how, age=5)
    for _ in range(5):
        get(rig, rid)
    assert len(fetch_jobs(rig)) == 1
    assert get(rig, rid)["status"] == "lost"


def test_tc026_two_simultaneous_get_runs_queue_one(rig):
    # TC-026 (1): the check and the insert are one write
    import threading
    from abf_platform import jobs
    rid = lost_run(rig)
    gate = threading.Barrier(2)
    seen = []

    def one():
        gate.wait()
        seen.append(jobs.ask_head_state(rig.state, "x"))

    ts = [threading.Thread(target=one) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(fetch_jobs(rig)) == 1 and sorted(seen) == [False, True]


def test_tc027_only_the_head_state_path_sends_the_slurm_number(rig):
    # TC-027 (2): an older site agent refuses a job with a key it does not know
    from abf_platform import jobs
    rid = lost_run(rig)
    plain = jobs.enqueue_fetch(rig.state, "x")
    get(rig, rid)      # the plain job is still waiting, so this adds none; ask on a run with no fetch instead
    lost_run(rig, "y", slurm=777)
    get(rig, "id-y")
    args = {j["id"]: json.loads(j["args_json"]) for j in fetch_jobs(rig)}
    assert set(args[plain]) == {"ce", "run_name", "run_folder"}
    (other,) = [a for a in args.values() if a["run_name"] == "y"]
    assert other["slurm_job_id"] == "777"


def test_tc027_a_refused_head_state_query_leaves_the_run_lost_and_is_not_repeated(rig):
    # TC-027 (2)
    rid = lost_run(rig)
    get(rig, rid)
    (job,) = fetch_jobs(rig)
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE jobs SET state = 'refused', result_json = ?, finished_at = ? WHERE id = ?",
                    (json.dumps({"ok": False, "message": "unknown argument"}), time.time(), job["id"]))
    con.close()
    for _ in range(3):
        v = get(rig, rid)
    assert v["status"] == "lost" and len(fetch_jobs(rig)) == 1


def test_tc028_the_fact_is_not_pushed_out_by_other_runs_fetches(rig):
    # TC-028 (3): the limit is applied after the filter by run
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=30)
    lost_run(rig, "y", slurm=777)
    for _ in range(110):
        add_fetch(rig, "y", fact("RUNNING", "squeue", "777"), age=1, slurm=777)
    assert get(rig, rid)["status"] == "failed"
    assert [r["status"] for r in listed(rig, "x")] == ["failed"]


# ---- code-review fixes (ruling P, PR #318) ----------------------------------------------------------------------------------------

def test_tc030_a_plain_fetch_does_not_cover_an_earlier_nodefail_fact(rig):
    # TC-030 (P1): only a read-back that carries the scheduler key and is this run's counts; a plain one (abf-launch fetch) is no answer
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=500)
    add_fetch(rig, "x", None, age=100, with_key=False)
    v = get(rig, rid)
    assert v["status"] == "failed" and v["failure"]["failure_reason"] == reason("NODE_FAIL")
    (row,) = listed(rig, "x")
    assert row["status"] == "failed" and row["failure"]["failure_reason"] == reason("NODE_FAIL")


def test_tc031_a_site_that_could_not_ask_does_not_take_back_a_nodefail_fact(rig):
    # TC-031 (P2): scheduler=None is "no new fact", the run never flips between failed and lost
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=500)
    for n in range(4):
        add_fetch(rig, "x", None, age=300 - 50 * n)
        v = get(rig, rid)
        assert v["status"] == "failed" and v["failure"]["failure_reason"] == reason("NODE_FAIL"), n
        (row,) = listed(rig, "x")
        assert row["status"] == "failed" and row["failure"]["failure_reason"] == reason("NODE_FAIL"), n


def test_tc032_a_known_end_is_not_asked_again_every_minute(rig):
    # TC-032 (P3)
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=120)
    n = len(fetch_jobs(rig))
    assert get(rig, rid)["status"] == "failed"
    assert get(rig, rid)["status"] == "failed"
    assert len(fetch_jobs(rig)) == n


def test_tc033_no_caller_queues_nothing_for_anyone(rig):
    # TC-033 (P3)
    rid = lost_run(rig)
    before = rig.sql("SELECT COUNT(*) FROM jobs")[0][0]
    v = get(rig, rid, caller=None)
    assert v["status"] == "lost"
    assert rig.sql("SELECT COUNT(*) FROM jobs")[0][0] == before and fetch_jobs(rig) == []


# ---- adversary fixes (round 2 of ruling P): the fact outlives the prune and the cut of twenty ------------------------------------

def test_adv4_a_failed_run_stays_failed_after_the_job_prune(rig):
    # ADV-4 (P2; was numbered TC-035, which the contract gave to the merge): the NODE_FAIL read-back older than the prune age is not deleted; the run does not go back to lost
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=8 * 86400)
    lost_run(rig, "y", slurm=777)
    get(rig, "id-y")                       # queues a job on another run: the insert runs the prune
    v = get(rig, rid)
    assert v["status"] == "failed" and v["failure"]["failure_reason"] == reason("NODE_FAIL")
    out = rig.resume("x", person=FakePerson(True))
    assert out.get("sent"), out.get("message")


def test_adv4_old_read_backs_without_an_end_are_still_pruned(rig):
    # ADV-4: only a bad-end fact is kept; a plain or alive answer of that age is deleted as before
    lost_run(rig)
    add_fetch(rig, "x", None, age=8 * 86400, with_key=False)
    add_fetch(rig, "x", fact("RUNNING", "squeue"), age=8 * 86400)
    lost_run(rig, "y", slurm=777)
    get(rig, "id-y")
    assert [r for r in fetch_jobs(rig) if '"x"' in r["args_json"]] == []


def test_adv5_twenty_newer_plain_fetches_do_not_push_the_fact_out(rig):
    # ADV-5 (P1; was numbered TC-036): the cut of twenty counts only answers that asked the scheduler
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=5000)
    for i in range(25):
        add_fetch(rig, "x", None, age=4000 - i)
    v = get(rig, rid)
    assert v["status"] == "failed" and v["failure"]["failure_reason"] == reason("NODE_FAIL")
    assert [r["status"] for r in listed(rig, "x")] == ["failed"]


# ---- adversary round (11-04): one run, one state across get_run, forget, the usage page and the web notice ----

def test_adv1_a_run_shown_failed_can_be_forgotten_like_any_failed_run(rig):
    # ADV-1: get_run says failed (NODE_FAIL), so forget must not say "lost and may still be running"
    from abf_platform import actions
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"))
    assert get(rig, rid)["status"] == "failed"
    code, msg = actions.forget_check(rig.state, rig.index, "x", caller=owner(rig))
    assert code != "refused" or "lost" not in msg


def test_adv1_a_run_still_lost_is_still_refused_by_forget(rig):
    # ADV-1: with no bad end of the head job the run stays lost and forget keeps refusing
    from abf_platform import actions
    lost_run(rig)
    code, msg = actions.forget_check(rig.state, rig.index, "x", caller=owner(rig))
    assert code == "refused" and "lost" in msg
    add_fetch(rig, "x", fact("RUNNING"))
    code, msg = actions.forget_check(rig.state, rig.index, "x", caller=owner(rig))
    assert code == "refused" and "lost" in msg


def test_adv2_the_usage_page_does_not_call_a_failed_run_running(rig):
    # ADV-2: the run page says failed, so the usage page must not say "running / the run has not ended"
    from abf_platform import actions
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"))
    assert get(rig, rid)["status"] == "failed"
    rows = [r for r in actions.my_usage(rig.index, rig.state, caller=owner(rig))["runs"] if r["name"] == "x"]
    assert rows and rows[0]["state"] != "running"
    assert not any("has not ended" in x for x in rows[0]["unknown_reasons"])


def test_adv2_the_usage_page_still_calls_a_lost_run_running(rig):
    # ADV-2: no fact, no change
    from abf_platform import actions
    lost_run(rig)
    rows = [r for r in actions.my_usage(rig.index, rig.state, caller=owner(rig))["runs"] if r["name"] == "x"]
    assert rows and rows[0]["state"] == "running"


def test_adv3_the_failure_notice_of_a_failed_overlay_keeps_a_time(rig):
    # ADV-3: a lost run has no ended_at; the Failed look of it still shows when the last message came
    from abf_platform import web_board
    t = web_board.STRINGS["zh"]
    def when(view):
        return re.search(r'<span class="when">([^<]*)</span>', web_board._failure_notice(t, view)).group(1)
    lost_run(rig, run="y")
    plain = when(get(rig, "id-y"))
    rid = lost_run(rig, run="x")
    add_fetch(rig, "x", fact("NODE_FAIL"))
    v = get(rig, rid)
    assert v["status"] == "failed" and v.get("ended_at") == v.get("last_message_at")      # ruling Q2: the view carries the notice's own time as its end
    assert when(v) == plain != "\u2014"


# ---- ruling Q: a bad end is not for ever; the Ended column of a run shown failed ---------------------------------------------

@pytest.mark.parametrize("alive", ["RUNNING", "PENDING"])
def test_tc037_the_newest_real_answer_wins_over_an_earlier_bad_end(rig, alive):
    # TC-037 (Q1): NODE_FAIL first, then RUNNING/PENDING (Slurm requeued it): back to lost, as a run with no fact at all
    rid = lost_run(rig, succeeded=0)      # nothing to reuse: a plain lost run offers relaunch only
    add_fetch(rig, "x", fact("NODE_FAIL"), age=900)
    add_fetch(rig, "x", fact(alive, "squeue"), age=300)
    plain = lost_run(rig, "y", slurm=777, succeeded=0)
    v = get(rig, rid)
    base = get(rig, plain)
    assert v["status"] == "lost" and v["failure"]["failure_reason"] is None
    assert "resume" not in v["failure"]["actions"] and v["failure"]["actions"] == base["failure"]["actions"]
    row = listed(rig, "x")[0]
    assert row["status"] == "lost" and row["failure"]["failure_reason"] is None
    # the other order shows Failed
    lost_run(rig, "z", slurm=888)
    add_fetch(rig, "z", fact(alive, "squeue", job_id="888"), age=900, slurm=888)
    add_fetch(rig, "z", fact("NODE_FAIL", job_id="888"), age=300, slurm=888)
    assert get(rig, "id-z")["status"] == "failed"


def test_tc042_a_taken_back_bad_end_takes_back_the_resume_gate_too(rig):
    # TC-042 (Q1)
    lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=900)
    add_fetch(rig, "x", fact("RUNNING", "squeue"), age=300)
    assert "還在跑" in rig.resume("x", person=FakePerson(True))["message"]


def test_tc040_a_bad_end_older_than_ten_minutes_is_asked_once_more(rig):
    # TC-040 (Q1)
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=11 * 60)
    n = len(fetch_jobs(rig))
    assert get(rig, rid)["status"] == "failed"
    assert len(fetch_jobs(rig)) == n + 1
    assert json.loads(fetch_jobs(rig)[-1]["args_json"])["slurm_job_id"] == str(SLURM)
    assert get(rig, rid)["status"] == "failed"      # the new answer has not come yet: still failed
    assert len(fetch_jobs(rig)) == n + 1


def test_tc041_a_bad_end_older_than_six_hours_is_not_asked_again(rig):
    # TC-041 (Q1)
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=6 * 3600 + 60)
    n = len(fetch_jobs(rig))
    assert get(rig, rid)["status"] == "failed"
    assert get(rig, rid)["status"] == "failed"
    assert len(fetch_jobs(rig)) == n


def test_tc038_a_run_shown_failed_has_an_end_time_like_the_failure_notice(rig):
    # TC-038 (Q2): no ended_at in the index; every Ended place shows the last message time, never a dash
    from abf_platform import web_board
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"))
    v = get(rig, rid)
    assert v["status"] == "failed" and v["ended_at"] and v["ended_at"] == v["last_message_at"]
    row = listed(rig, "x")[0]
    assert row["status"] == "failed" and row["ended_at"] == v["ended_at"]
    assert web_board._time(row["ended_at"]) != "\u2014"


def test_tc039_the_duration_of_a_run_shown_failed_does_not_grow(rig):
    # TC-039 (Q2)
    from abf_platform import web_board
    t = web_board.STRINGS["zh"]
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"))
    v = get(rig, rid)
    now = time.time()
    assert web_board._duration(t, v, now) == web_board._duration(t, v, now + 3600) != "\u2014"


# ---- adversary round (11-04, on ruling Q): the prune and the six hours -----------------------------------------------------------

def test_adv6_the_prune_does_not_bring_back_a_bad_end_that_a_newer_answer_took_back(rig):
    # ADV-6 (Q1): NODE_FAIL then RUNNING, both older than the prune age: the run must not turn Failed again, nor offer resume
    from abf_platform import jobs
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=8 * 86400 + 600)
    add_fetch(rig, "x", fact("RUNNING", "squeue"), age=8 * 86400)
    lost_run(rig, "y", slurm=777)
    get(rig, "id-y")                       # queues a job on another run: the insert runs the prune
    assert jobs.head_state(rig.state, "x") is None or jobs.head_state(rig.state, "x")["state"] == "RUNNING"
    v = get(rig, rid)
    assert v["status"] == "lost" and v["failure"]["failure_reason"] is None
    assert "還在跑" in rig.resume("x", person=FakePerson(True))["message"]


def test_adv6_a_later_bad_end_after_a_taken_back_one_is_still_kept(rig):
    # ADV-6: NODE_FAIL, RUNNING, NODE_FAIL: the newest bad end survives the prune; the run stays Failed
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=9 * 86400)
    add_fetch(rig, "x", fact("RUNNING", "squeue"), age=8.5 * 86400)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=8 * 86400)
    lost_run(rig, "y", slurm=777)
    get(rig, "id-y")
    assert get(rig, rid)["status"] == "failed"


def test_adv7_the_six_hours_count_from_the_first_bad_answer_not_from_the_last(rig):
    # ADV-7 (Q1): the site keeps saying NODE_FAIL and someone keeps opening the run: the scheduler is not asked after six hours
    from abf_platform import jobs
    lost_run(rig)
    t0 = time.time()
    add_fetch(rig, "x", fact("NODE_FAIL"), age=0)
    asked = []
    for k in range(1, 60):                          # every 11 minutes, 10.8 hours in all
        T = t0 + k * 660
        con = sqlite3.connect(str(rig.state))
        with con:
            con.execute("UPDATE agents SET last_seen_at = ?", (T,))
        con.close()
        if jobs.ask_head_state(rig.state, "x", clock=lambda T=T: T):
            asked.append(k * 660 / 3600)
            con = sqlite3.connect(str(rig.state))
            with con:
                con.execute("UPDATE jobs SET state='done', result_json=?, finished_at=? WHERE state='queued' AND kind='fetch_run_records'",
                            (json.dumps({"ok": True, "files": [], "refused": [], "scheduler": fact("NODE_FAIL")}), T + 30))
            con.close()
    assert asked and max(asked) <= 6.0, asked


def test_adv7_a_new_streak_after_an_alive_answer_gets_its_own_six_hours(rig):
    # ADV-7: NODE_FAIL 7h ago, RUNNING 5h ago, NODE_FAIL 20 minutes ago: the bad end is young again, so it is asked again
    rid = lost_run(rig)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=7 * 3600)
    add_fetch(rig, "x", fact("RUNNING", "squeue"), age=5 * 3600)
    add_fetch(rig, "x", fact("NODE_FAIL"), age=20 * 60)
    n = len(fetch_jobs(rig))
    assert get(rig, rid)["status"] == "failed"
    assert len(fetch_jobs(rig)) == n + 1


# ---- ruling R1: a give-up limit when there is no fact at all ---------------------------------------------------------------------

def _lost_for(rig, hours):
    """lost_run, but silent for `hours`: the last message and the hand-over are both that long ago."""
    rid = lost_run(rig)
    t = time.time() - hours * 3600
    rig.sql("SELECT 1")
    con = sqlite3.connect(str(rig.index))
    with con:
        con.execute("UPDATE runs SET last_message_at = ? WHERE run_name = 'x'", (t,))
    con.close()
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE launches SET submitted_at = ?, confirmed_at = ? WHERE run_name = 'x'", (t, t))
    con.close()
    return rid


@pytest.mark.parametrize("how", ["no_fetch", "only_none"])
def test_tc044_a_run_lost_for_seven_hours_with_no_fact_is_not_asked_again(rig, how):
    # TC-044 (R1)
    from abf_platform import jobs
    rid = _lost_for(rig, 7)
    if how == "only_none":
        add_fetch(rig, "x", None, age=7 * 3600)
    n = len(fetch_jobs(rig))
    for step in range(3):
        v = get(rig, rid)
        assert v["status"] == "lost" and v["failure"]["failure_reason"] is None
        later = time.time() + 120 * (step + 1)
        _agent_online_at(rig, later)      # the agent is online at the moved time, so only the 6-hour limit can say no
        assert jobs.ask_head_state(rig.state, "x", clock=lambda t=later: t, last_message_at=time.time() - 7 * 3600) is False
    assert len(fetch_jobs(rig)) == n


def _agent_online_at(rig, t):
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE agents SET last_seen_at = ?", (t,))
    con.close()


@pytest.mark.parametrize("how", ["no_fetch", "only_none"])
def test_tc044_mutation_without_the_give_up_the_later_steps_ask_again(rig, how, monkeypatch):
    # TC-044 mutation proof (ruling of 11-05): with the 6-hour limit switched off, the moved-clock calls queue a fetch (True),
    # so the steps of the test above really exercise the limit and not an offline agent
    from abf_platform import jobs
    _lost_for(rig, 7)
    if how == "only_none":
        add_fetch(rig, "x", None, age=7 * 3600)
    monkeypatch.setattr(jobs, "BAD_END_GIVE_UP_SECONDS", 10 ** 12)
    later = time.time() + 120
    _agent_online_at(rig, later)
    assert jobs.ask_head_state(rig.state, "x", clock=lambda: later, last_message_at=time.time() - 7 * 3600) is True


def test_tc045_a_run_lost_for_five_hours_is_still_asked_once(rig):
    # TC-045 (R1): the contrast of TC-044
    rid = _lost_for(rig, 5)
    get(rig, rid)
    get(rig, rid)
    assert len(fetch_jobs(rig)) == 1
    assert json.loads(fetch_jobs(rig)[0]["args_json"])["slurm_job_id"] == str(SLURM)


# ---- ruling R2: get_run is no longer marked read-only (it may queue one read of the site) ------------------------------------------

def _mcp_tools(rig):
    import asyncio
    from abf_platform.mcp_server import build_server
    return {t.name: t for t in asyncio.run(build_server(str(rig.index), str(rig.state)).list_tools())}


def test_tc046_get_run_is_marked_not_read_only_and_nothing_else_changed(rig):
    # TC-046 (R2)
    tools = _mcp_tools(rig)
    a = tools["get_run"].annotations
    assert a.read_only_hint is False and a.idempotent_hint is True and a.destructive_hint is False and a.open_world_hint is False
    for name in ("list_runs", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "read_task_log", "run_outputs"):
        assert tools[name].annotations.read_only_hint is True, name
    for name in ("cancel", "forget", "launch", "relaunch", "resume"):
        assert tools[name].annotations.read_only_hint is False, name
    assert tools["cancel"].annotations.destructive_hint is True


def test_tc047_get_run_description_says_a_lost_run_triggers_one_site_query(rig):
    # TC-047 (R2)
    d = _mcp_tools(rig)["get_run"].description
    assert re.search(r"lost", d) and re.search(r"read-only", d) and re.search(r"site", d) and re.search(r"quer", d)
    assert "failure_reason" in d and "failed tasks" in d and "cancel_requested_at" in d


def test_tc048_get_run_stays_a_query_that_needs_no_yes(rig):
    # TC-048 (R2)
    import asyncio
    import importlib
    from helpers import tool_json
    run_id = lost_run(rig, "q48")
    hits = []
    for mod, name in [("abf_platform.confirm", "approve"), ("abf_platform.actions", "approve"), ("abf_platform.actions", "launch"),
                      ("abf_platform.actions", "cancel"), ("abf_platform.actions", "forget"), ("abf_platform.jobs", "enqueue_confirmed"),
                      ("abf_platform.jobs", "enqueue_launch"), ("abf_platform.jobs", "enqueue_cancel")]:
        m = importlib.import_module(mod)
        assert hasattr(m, name), "write point %s.%s is gone" % (mod, name)
        rig.w.monkeypatch.setattr(m, name, lambda *a, _n=name, **k: hits.append(_n))
    before = len(rig.sql("SELECT id FROM jobs"))
    # (a) over MCP with the SDK's in-memory Client (no form support, nobody says yes): the run comes back at once, no write point is reached
    _, outs = rig.w.mcp([("get_run", {"run_id": run_id})], caller=owner(rig))
    assert not outs[0].is_error
    out = tool_json(outs[0])
    assert out.get("id") == run_id and out.get("name") == "q48", out
    assert "confirm" not in json.dumps(out).lower() and "not sent" not in json.dumps(out).lower()      # not the write tools' "asked, waiting for a yes" answer
    assert hits == []
    new = rig.sql("SELECT kind FROM jobs ORDER BY id")[before:]
    assert len(new) <= 1 and all(r["kind"] == "fetch_run_records" for r in new), [r["kind"] for r in new]
    from abf_platform.actions import chat_tools
    assert "get_run" not in chat_tools.REQUEST_TOOLS and chat_tools.REQUEST_TOOLS == {"launch", "launch_pipeline", "cancel", "resume", "relaunch", "forget"}
    names = {s["name"] for s in asyncio.run(chat_tools.tool_specs(str(rig.index), str(rig.state)))}
    assert "get_run" in names
