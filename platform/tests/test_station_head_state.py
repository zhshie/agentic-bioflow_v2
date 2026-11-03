# Nothing existing: tests that hand the real agent a fetch_run_records job with a Slurm job number and watch the fake squeue and sacct; the scheduler and the protocol are ours.
"""head-nodefail-detect, the site side: fetch_run_records says what the scheduler knows of the head job, but only when
Nextflow left no completion record. Test cases are named in the comments (TC-007 ... TC-011, TC-020)."""
import re

import pytest

from abf_station import fetch, handlers
from station_harness import FakeSite  # noqa: F401
from test_station_cancel import fetch_job, make_records
from test_station_fakeplatform import agent_on
from test_station_launch import fake, folder, run_job, site  # noqa: F401

DONE = "Execution complete -- Goodbye\n"


def no_completion(site, run="run-a"):
    f = make_records(site, run)
    (f / ".nextflow.log").write_text("Workflow started -- trace file: %s/trace-1.txt\nsome line\n" % f)
    return f


def calls_of(site, prog):
    return [c for c in site.calls() if c.startswith(prog + " ")]


def fetch_with(tmp_path, site, fake, number="654018"):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        return run_job(fake, fetch_job(site, slurm_job_id=number))


@pytest.mark.parametrize("raw,state", [("NODE_FAIL\n", "NODE_FAIL"), ("CANCELLED by 1234\n", "CANCELLED"), ("TIMEOUT\n", "TIMEOUT"),
                                       ("OUT_OF_MEMORY\n", "OUT_OF_MEMORY"), ("node_fail\n", "NODE_FAIL")])
def test_tc007_a_head_without_a_completion_record_reports_the_sacct_state(tmp_path, site, fake, raw, state):
    # TC-007
    no_completion(site)
    site.set("sacct_654018", raw)
    res = fetch_with(tmp_path, site, fake)
    assert res["state"] == "done", res
    assert res["result"]["scheduler"] == {"job_id": "654018", "state": state, "source": "sacct"}
    assert len(calls_of(site, "squeue")) == 1 and len(calls_of(site, "sacct")) == 1


def test_tc008_a_completion_record_wins_and_the_scheduler_is_not_asked(tmp_path, site, fake):
    # TC-008
    f = no_completion(site)
    (f / ".nextflow.log").write_text("Workflow started -- trace file: %s/trace-1.txt\n%s" % (f, DONE))
    site.set("sacct_654018", "NODE_FAIL\n")
    res = fetch_with(tmp_path, site, fake)
    assert res["state"] == "done" and res["result"]["scheduler"] is None, res
    assert calls_of(site, "squeue") == [] and calls_of(site, "sacct") == []


def test_tc009_a_head_still_in_the_queue_is_reported_as_it_is_and_sacct_is_not_asked(tmp_path, site, fake):
    # TC-009
    no_completion(site)
    site.set("squeue_state_654018", "RUNNING\n")
    site.set("sacct_654018", "NODE_FAIL\n")
    res = fetch_with(tmp_path, site, fake)
    assert res["result"]["scheduler"] == {"job_id": "654018", "state": "RUNNING", "source": "squeue"}
    assert calls_of(site, "sacct") == []


@pytest.mark.parametrize("how", ["sacct_fails", "knows_nothing"])
def test_tc010_when_the_scheduler_cannot_say_nothing_is_guessed(tmp_path, site, fake, how):
    # TC-010
    no_completion(site)
    if how == "sacct_fails":
        site.set("sacct_fail", "1")
        site.set("sacct_654018", "NODE_FAIL\n")
    res = fetch_with(tmp_path, site, fake)
    assert res["state"] == "done" and res["result"]["ok"] is True, res
    assert res["result"]["scheduler"] is None
    assert len(res["result"]["files"]) >= 1      # the rest of the fetch still came back


def test_tc010_no_job_number_means_no_question_to_the_scheduler(tmp_path, site, fake):
    # TC-010 (an old platform sends no number)
    no_completion(site)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, fetch_job(site))
    assert res["state"] == "done" and res["result"]["scheduler"] is None
    assert calls_of(site, "squeue") == [] and calls_of(site, "sacct") == []


@pytest.mark.parametrize("number", ["1; rm -x", "12 34", "$(id)", "", "-1", "1" * 11, "abc"])
def test_tc011_a_job_number_that_is_not_digits_is_refused_before_anything_is_run(tmp_path, site, fake, number):
    # TC-011 (a)
    no_completion(site)
    res = fetch_with(tmp_path, site, fake, number=number)
    assert res["state"] == "refused", res
    assert [c for c in site.calls() if c.split(" ")[0] in ("squeue", "sacct", "scancel", "sbatch")] == []
    assert not site.dangerous()


def test_tc011_an_unknown_argument_is_still_refused_and_the_old_keys_are_kept(tmp_path, site, fake):
    # TC-011 (b)
    no_completion(site)
    assert {"ce", "run_name", "run_folder"} <= fetch.ARGS and "slurm_job_id" in fetch.ARGS
    assert handlers.ARG_KEYS["fetch_run_records"] == fetch.ARGS
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, fetch_job(site, slurm_job_id="654018", extra=1))
    assert res["state"] == "refused", res


@pytest.mark.parametrize("raw", [
    "Whatever /srv/x/secret abf_0123456789abcdef0123456789abcdef\n",
    "NODE_FAIL\nsecond line /srv/x/y\n" + "x" * 5000,                     # the first line is the only one that counts, and it is a state
    "/srv/x/.config/token\n",
    "X" * 100000,
    "NODE_FAIL_EXTRA\n",
    "\n\n",
])
def test_tc020_what_sacct_prints_is_not_trusted_and_never_passed_on(tmp_path, site, fake, raw):
    # TC-020
    no_completion(site)
    site.set("sacct_654018", raw)
    res = fetch_with(tmp_path, site, fake)
    assert res["state"] == "done", res
    sched = res["result"]["scheduler"]
    assert sched is None or (sched["state"] in fetch.SLURM_STATES and set(sched) == {"job_id", "state", "source"}), sched
    text = str(res)
    assert "/srv/x" not in text and "abf_0123" not in text and "x" * 50 not in text


def test_tc029_a_log_cut_at_20_mib_is_not_a_completion_record(tmp_path, site, fake):
    # TC-029 (4): a cut log lost its end, so the scheduler is still asked
    f = no_completion(site)
    with open(f / ".nextflow.log", "ab") as h:
        h.truncate(21 * 1024 * 1024)
    site.set("sacct_654018", "NODE_FAIL\n")
    res = fetch_with(tmp_path, site, fake)
    assert res["state"] == "done", res
    assert res["result"]["scheduler"] == {"job_id": "654018", "state": "NODE_FAIL", "source": "sacct"}


def test_adversary_a_resume_in_the_same_folder_does_not_hide_the_first_attempts_node_fail(tmp_path, site, fake):
    # ADVERSARY (11-04 fix round, ruling P): .nextflow.log is the resume's log; the first attempt's rotated log has no completion line
    f = make_records(site, "run-a")
    (f / ".nextflow.log.1").write_text("Workflow started -- trace file: %s/trace-1.txt\nlast line before the node died\n" % f)
    (f / ".nextflow.log").write_text("resume log\n" + DONE)
    site.set("sacct_654018", "NODE_FAIL\n")
    res = fetch_with(tmp_path, site, fake)
    assert res["state"] == "done", res
    assert res["result"]["scheduler"] == {"job_id": "654018", "state": "NODE_FAIL", "source": "sacct"}


def test_adversary_every_attempt_has_its_completion_line_so_the_scheduler_is_not_asked(tmp_path, site, fake):
    f = make_records(site, "run-a")
    (f / ".nextflow.log.1").write_text("first\n" + DONE)
    (f / ".nextflow.log").write_text("resume\n" + DONE)
    site.set("sacct_654018", "NODE_FAIL\n")
    res = fetch_with(tmp_path, site, fake)
    assert res["result"]["scheduler"] is None
    assert calls_of(site, "squeue") == [] and calls_of(site, "sacct") == []


def test_tc034_a_rotated_log_without_a_start_mark_still_asks_the_scheduler(tmp_path, site, fake):
    # TC-034 (ruling P4): the first attempt's log shows no start mark and no completion line; the resume's log has the line. Ask, do not skip.
    f = make_records(site, "run-a")
    (f / ".nextflow.log.1").write_text("the node died here\n")
    (f / ".nextflow.log").write_text("resume log\n" + DONE)
    site.set("sacct_654018", "NODE_FAIL\n")
    res = fetch_with(tmp_path, site, fake)
    assert res["state"] == "done", res
    assert res["result"]["scheduler"] == {"job_id": "654018", "state": "NODE_FAIL", "source": "sacct"}
    assert len(calls_of(site, "squeue")) + len(calls_of(site, "sacct")) >= 1
