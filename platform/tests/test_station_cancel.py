# Nothing existing: tests that hand the real agent cancel and fetch jobs, honest and hostile, through a fake platform and watch a fake scheduler; the protocol and the scheduler are ours.
"""The agent's cancel_run and fetch_run_records jobs (feature 007b)."""
import base64
import os
import re

import pytest

from station_harness import FakePlatform, FakeSite, snapshot
from test_station_fakeplatform import agent_on, wait_for
from test_station_launch import ACCT, bundle_for, fake, folder, job_of, run_job, site  # noqa: F401


def cancel_bundle(site, fake, run="run-a", number=4242, **over):
    b = bundle_for(site, fake, run=run)
    c = {"version": 1, "run_name": run, "slurm_job_id": number, "run_folder": b["run_folder"], "agent": "agent-f", "ce": b["ce"]}
    c.update(over)
    return c


def cancel_job(site, fake, **kw):
    c = cancel_bundle(site, fake, **{k: v for k, v in kw.items() if k in ("run", "number")} or {})
    over = kw.get("over")
    if over:
        c.update(over)
    return job_of(c, kind="cancel_run", conf_kind="cancel")


def launched(site, fake, run="run-a", sid=4242):
    site.set("sbatch_id", str(sid))
    assert run_job(fake, job_of(bundle_for(site, fake, run=run)))["state"] == "done"


def scancels(site):
    return [c for c in site.calls() if c.startswith("scancel")]


def squeues(site):
    return [c for c in site.calls() if c.startswith("squeue")]


def test_tc040_a_confirmed_cancel_asks_the_scheduler_once_and_stops_that_one_job(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        launched(site, fake)
        site.add_job(999, "someone-else", "other", "/elsewhere")
        res = run_job(fake, cancel_job(site, fake))
        assert res["state"] == "done" and res["result"]["ok"], res
        assert "取消請求已送出" in res["result"]["message"]
    assert squeues(site) == ["squeue -h -j 4242 -o %j|%u|%Z"]
    assert scancels(site) == ["scancel 4242"]
    assert site.slurm_jobs() == ["999|someone-else|other|/elsewhere"], "no other job was touched"


@pytest.mark.parametrize("mutate,why", [
    (lambda s: s.set("jobs.tsv", ""), "gone"),
    (lambda s: s.set("jobs.tsv", "4242|nf-other|tester|FOLDER\n"), "name"),
    (lambda s: s.set("jobs.tsv", "4242|nf-run-a|mallory|FOLDER\n"), "user"),
    (lambda s: s.set("jobs.tsv", "4242|nf-run-a|tester|/somewhere/else\n"), "folder"),
    (lambda s: s.set("jobs.tsv", "4242|nf-run-a|tester|FOLDER\n4242|nf-run-a|tester|FOLDER\n"), "two lines"),
    (lambda s: s.set("squeue_fail", "1"), "query failed"),
])
def test_tc042_a_job_that_is_not_this_runs_head_job_is_never_stopped(tmp_path, site, fake, mutate, why):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        launched(site, fake)
        f = str(folder(site))
        jt = site.state / "jobs.tsv"
        mutate(site)
        if jt.exists():
            jt.write_text(jt.read_text().replace("FOLDER", f))
        res = run_job(fake, cancel_job(site, fake))
        assert res["state"] in ("refused", "error") and not res["result"]["ok"], (why, res)
    assert scancels(site) == [], why
    assert len(squeues(site)) == 1, "one question, no retry"


@pytest.mark.parametrize("number", ["123;touch c", "123 456", "-u me", "--name=nf-x", 0, -1, 2 ** 40, "4242", True, 4242.0, None])
def test_tc043_a_job_number_that_is_not_one_plain_decimal_number_reaches_no_command(tmp_path, site, fake, number):
    canary = tmp_path / "c"
    with agent_on(fake, site, tmp_path, name="agent-f"):
        launched(site, fake)
        before = len(site.calls())
        res = run_job(fake, cancel_job(site, fake, number=number))
        assert res["state"] == "refused", res
    assert scancels(site) == [] and len(site.calls()) == before
    assert not canary.exists()


def test_tc043_a_cancel_without_a_confirmation_or_with_a_changed_content_is_refused(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        launched(site, fake)
        before = len(site.calls())
        good = cancel_job(site, fake)
        assert run_job(fake, {k: v for k, v in good.items() if k != "confirmation"})["state"] == "refused"
        t = dict(good, args=dict(good["args"], bundle=dict(good["args"]["bundle"], slurm_job_id=999)))
        assert run_job(fake, t)["state"] == "refused"
        extra = cancel_job(site, fake, over={"signal": "KILL"})
        assert run_job(fake, extra)["state"] == "refused"
    assert len(site.calls()) == before and scancels(site) == []


def test_tc009_a_cancel_given_twice_is_sent_once_even_if_the_job_is_still_listed(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        launched(site, fake)
        site.set("scancel_keep", "1")
        job = cancel_job(site, fake)
        assert run_job(fake, job)["state"] == "done"
        assert run_job(fake, job)["state"] == "refused"
    assert scancels(site) == ["scancel 4242"]


def test_tc044_each_cancel_stops_only_its_own_run(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        launched(site, fake, "run-a", 4242)
        launched(site, fake, "run-b", 4243)
        assert run_job(fake, cancel_job(site, fake, run="run-a", number=4242))["state"] == "done"
        assert run_job(fake, cancel_job(site, fake, run="run-a", number=4242))["state"] == "refused"   # it is gone from the queue
        assert run_job(fake, cancel_job(site, fake, run="run-b", number=4243))["state"] == "done"
    assert scancels(site) == ["scancel 4242", "scancel 4243"]
    assert not [c for c in site.calls() if re.search(r"scancel (-|--)", c)]


@pytest.mark.parametrize("kind", ["scancel", "cancel", "cancel_run ", " cancel_run", "CANCEL_RUN", "Cancel_Run"])
def test_tc046_other_spellings_of_the_kind_are_refused_and_the_next_honest_job_still_works(tmp_path, site, fake, kind):
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        launched(site, fake)
        job = cancel_job(site, fake)
        job["kind"] = kind
        job["cmd"] = "scancel -u tester"
        assert run_job(fake, job)["state"] == "refused"
        assert a.alive()
    assert scancels(site) == []


def test_the_agent_cancels_nothing_for_a_bundle_of_another_agent_or_another_folder(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        launched(site, fake)
        assert run_job(fake, cancel_job(site, fake, over={"agent": "agent-z"}))["state"] == "refused"
        assert run_job(fake, cancel_job(site, fake, over={"run_folder": "/etc"}))["state"] == "refused"
        assert run_job(fake, cancel_job(site, fake, over={"run_name": "../x"}))["state"] == "refused"
    assert scancels(site) == []


# ---- fetch_run_records ------------------------------------------------------------------------------------------

def make_records(site, run="run-a"):
    f = folder(site, run)
    (f / ".nextflow").mkdir(parents=True)
    (f / ".nextflow.log").write_text("x\nWorkflow started -- trace file: %s/trace-1.txt\n" % f)
    (f / ".nextflow.log.1").write_text("old log\n")
    (f / ".nextflow" / "history").write_text("history line\n")
    (f / "trace-1.txt").write_text("task_id\tname\n1\tA\n")
    (f / "tower.token").write_text("SECRET_TOKEN_VALUE")
    (f / "params.yaml").write_text("a: 1\n")
    return f


def fetch_job(site, run="run-a", **over):
    args = {"ce": {"name": "lab-a", "platform": "slurm-platform", "workDir": str(site.work), "launchDir": str(site.launch),
                   "headQueue": "normal", "computeQueue": None, "readRoots": []},
            "run_name": run, "run_folder": str(folder(site, run))}
    args.update(over)
    return {"kind": "fetch_run_records", "args": args}


def names(res):
    return sorted(f["name"] for f in res["result"]["files"])


def test_tc034_only_the_logs_the_history_and_the_named_trace_are_read_and_nothing_is_written(tmp_path, site, fake):
    f = make_records(site)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, fetch_job(site))
    assert res["state"] == "done", res
    assert names(res) == sorted([".nextflow.log", ".nextflow.log.1", ".nextflow/history", "trace-1.txt"])
    got = {x["name"]: base64.b64decode(x["data"]) for x in res["result"]["files"]}
    assert got["trace-1.txt"] == (f / "trace-1.txt").read_bytes()
    assert "SECRET_TOKEN_VALUE" not in str(res) and "params.yaml" not in names(res) and "tower.token" not in names(res)
    assert snapshot(f) == before, "the site folder is untouched"
    assert not [c for c in site.destructive()], site.destructive()
    assert not site.dangerous()


def test_tc035_a_link_a_trace_outside_the_folder_and_a_big_file_are_dealt_with_in_the_open(tmp_path, site, fake):
    f = make_records(site)
    guard = site.storage / "rawdata" / "guard.txt"
    (f / ".nextflow.log.2").symlink_to(guard)
    (f / ".nextflow.log").write_text("Workflow started -- trace file: %s\nWorkflow started -- trace file: ../other.txt\n" % guard)
    big = f / ".nextflow.log.3"
    with open(big, "wb") as h:
        h.truncate(21 * 1024 * 1024)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, fetch_job(site))
    r = res["result"]
    assert res["state"] == "done"
    assert ".nextflow.log.2" not in names(res) and "guard content" not in str(res)
    assert any("符號連結" in x and ".nextflow.log.2" in x for x in r["refused"]), r["refused"]
    assert sum("trace" in x for x in r["refused"]) == 2, r["refused"]
    cut = [x for x in r["files"] if x["name"] == ".nextflow.log.3"][0]
    assert cut["truncated"] is True and len(base64.b64decode(cut["data"])) == 20 * 1024 * 1024
    assert not [x for x in r["files"] if x["name"] in ("tower.token", "params.yaml")]


@pytest.mark.parametrize("over", [{"run_folder": "/etc"}, {"run_name": "../x"}, {"run_name": "run-b"},
                                  {"run_folder": "%WORK%/runs/run-a/.."}, {"extra": 1}])
def test_tc035_a_folder_that_is_not_this_runs_launch_folder_is_refused(tmp_path, site, fake, over):
    make_records(site)
    make_records(site, "run-b")
    over = {k: (v.replace("%WORK%", str(site.work)) if isinstance(v, str) else v) for k, v in over.items()}
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, fetch_job(site, **over))
    assert res["state"] == "refused", res
