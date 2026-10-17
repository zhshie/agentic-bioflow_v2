# Nothing existing: tests that hand the real agent resume and relaunch jobs, honest and hostile, through a fake platform and a fake site with a run folder in it; the protocol and the site are ours.
"""009e: the agent's resume (the existing run folder, nothing but head-N.sh and tower.token written) and relaunch (a launch under a new name).
Test cases are named in the comments (TC-019 ...), see specs/009e-resume-relaunch/test-case.md."""
import copy
import json
import os
import re
import secrets
import stat
import subprocess
from pathlib import Path

import pytest

from resume_harness import OLD_TOKEN, SESSION, make_folder, relaunch_bundle, resume_bundle
from station_harness import FakePlatform, FakeSite, snapshot
from test_station_launch import ACCT, TOKEN, bundle_for, job_of, run_job
from test_station_fakeplatform import agent_on, wait_for

PROXY = "http://login.example:18080"
INSTANCE = "inst-0123456789abcdef"


@pytest.fixture
def site(tmp_path):
    s = FakeSite(tmp_path / "s", account=ACCT, site_user="tester", destructive_log=True)
    (s.storage / "cache").mkdir()
    (s.storage / "rawdata" / "s1.fq").write_text("x")
    return s


@pytest.fixture
def fake():
    f = FakePlatform()
    yield f
    f.stop()


def nothing_changed(site, f, before, allowed_calls=("sinfo", "java", "nextflow", "squeue")):
    """A refusal: no write, no submission, the folder as it was."""
    assert snapshot(f) == before
    assert not [c for c in site.calls() if c.split()[0] not in allowed_calls], site.calls()
    assert site.destructive() == []
    assert site.dangerous() == []
    assert site.guards_intact()


# ---- US1: a resume that is allowed --------------------------------------------------------------------------------------------------------

def test_tc019_tc020_tc021_tc163_tc164_a_resume_checks_then_writes_two_files_once_then_submits_once(tmp_path, site, fake):
    # TC-019 (checks, one tar, one sbatch of head-N.sh), TC-020 (no mkdir, no rm, head.sh not overwritten), TC-021 (the new token, mode 600),
    # TC-163 (only head-N.sh is new and only tower.token is changed), TC-164 (nothing deleted; work/ and .nextflow/ whole)
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, job_of(b))
        out = a.output()
    assert res["state"] == "done", res
    r = res["result"]
    assert r["ok"] and r["slurm_job_id"] == 4242 and r["run_name"] == "run-a-a2" and r["run_folder"] == str(f)
    calls = site.calls()
    kinds = [c.split()[0] for c in calls]
    assert "squeue" in kinds and kinds.index("squeue") < kinds.index("sbatch"), calls
    sb = [c for c in calls if c.startswith("sbatch")]
    assert len(sb) == 1 and sb[0].split()[1] == str(f / "head-2.sh")
    assert len([c for c in site.destructive() if c.startswith("tar")]) == 1, site.destructive()
    assert site.scripts() == [b["files"]["head-2.sh"]], "the script sbatch was given is the one that was shown"
    # TC-020
    assert not [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")]
    assert "mkdir" not in out, "a resume makes no folder"
    assert (f / "head.sh").read_bytes() == origin["files"]["head.sh"].encode("utf-8")
    # TC-021
    assert (f / "tower.token").read_text() == TOKEN != OLD_TOKEN
    assert stat.S_IMODE((f / "tower.token").stat().st_mode) == 0o600
    assert stat.S_IMODE((f / "head-2.sh").stat().st_mode) == 0o600
    assert TOKEN not in out and not [c for c in calls + site.ssh_calls() if TOKEN in c]
    # TC-163, TC-164
    after = snapshot(f)
    assert set(after) - set(before) == {"head-2.sh"}
    assert not set(before) - set(after)
    changed = {k for k in before if after[k] != before[k]}
    assert changed <= {".", "tower.token"}, changed
    assert (f / "work" / "ab" / "task.txt").read_text() == "a finished task that a resume may reuse"
    assert "crazy_darwin" in (f / ".nextflow" / "history").read_text()
    assert site.guards_intact()


def test_tc012_the_script_the_site_got_runs_nextflow_with_resume_and_the_new_name_in_the_old_folder(tmp_path, site, fake):
    # TC-012 / D7: the head script does cd into the folder (so the cache is found) and resumes the session by its id
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        assert run_job(fake, job_of(b))["state"] == "done"
    bindir = tmp_path / "nfbin"
    bindir.mkdir()
    nf = bindir / "nextflow"
    nf.write_text("#!/usr/bin/env python3\nimport json, os, sys\njson.dump({'argv': sys.argv[1:], 'env': dict(os.environ), 'cwd': os.getcwd()}, "
                  "open(os.environ['ABF_TEST_OUT'], 'w'))\n")
    nf.chmod(0o755)
    env = {"PATH": str(bindir) + os.pathsep + os.environ["PATH"], "ABF_TEST_OUT": str(tmp_path / "seen.json")}
    assert subprocess.run(["bash", str(f / "head-2.sh")], env=env).returncode == 0
    seen = json.load(open(tmp_path / "seen.json"))
    assert seen["argv"] == ["run", "nf-core/ampliseq", "-r", "2.18.0", "-resume", SESSION, "-name", "run-a-a2", "-params-file",
                            "params.yaml", "-c", "nextflow.config", "-with-tower", fake.url]
    assert os.path.realpath(seen["cwd"]) == os.path.realpath(str(f))
    assert seen["env"]["TOWER_ACCESS_TOKEN"] == TOKEN and seen["env"]["SLURM_ACCOUNT"] == ACCT


def test_tc022_a_resume_answers_like_a_launch_with_the_new_run_name(tmp_path, site, fake):
    # TC-022
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["result"]["message"] == "已送出：Slurm 工作編號 4242，run 名稱 run-a-a2，專屬資料夾 %s" % f


def test_tc023_a_resume_whose_sbatch_gave_no_clear_answer_is_told_as_unknown_like_a_launch(tmp_path, site, fake):
    # TC-023
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    site.set("sbatch_garbage", "1")
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "error" and re.search(r"可能已送出", res["result"]["message"]), res
    assert str(f) in res["result"]["left_on_site"] and "nf-run-a-a2" in res["result"]["left_on_site"]
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1, "never retried"
    assert not [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")]


def test_a_resume_whose_sbatch_failed_leaves_the_files_and_deletes_nothing(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    site.set("sbatch_fail", "sbatch: error: Invalid account\n")
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "error" and not res["result"]["ok"], res
    assert str(f) in res["result"]["left_on_site"] or str(f) in res["result"]["message"]
    assert (f / "head-2.sh").exists() and (f / "work" / "ab" / "task.txt").exists()
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1


# ---- the checks a resume shares with a launch ------------------------------------------------------------------------------------------------

def test_tc024_a_failed_preflight_stops_a_resume_before_anything_is_written(tmp_path, site, fake):
    # TC-024
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    before = snapshot(f)
    site.remove("sinfo")
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused" and "sinfo" in res["result"]["message"], res
    nothing_changed(site, f, before)


def test_tc025_a_resume_is_not_submitted_when_too_little_of_the_deadline_is_left(tmp_path, site, fake):
    # TC-025
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b, remaining=30))
    assert res["state"] == "refused" and re.search(r"時間|time", res["result"]["message"]), res
    nothing_changed(site, f, before)


def test_tc026_a_container_cache_that_cannot_be_written_stops_a_resume(tmp_path, site, fake):
    # TC-026
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    before = snapshot(f)
    os.chmod(site.storage / "cache", 0o500)
    try:
        with agent_on(fake, site, tmp_path, name="agent-f"):
            res = run_job(fake, job_of(b))
    finally:
        os.chmod(site.storage / "cache", 0o700)
    assert res["state"] == "refused" and re.search(r"NXF_SINGULARITY_CACHEDIR|快取", res["result"]["message"]), res
    nothing_changed(site, f, before)


def test_tc027_a_reverse_forward_that_does_not_answer_stops_a_resume(tmp_path):
    # TC-027: the same hop-by-hop check as a launch, before anything is written
    s = FakeSite(tmp_path / "s2", reach="ssh", account=ACCT, site_user="tester", destructive_log=True)
    (s.storage / "cache").mkdir()
    s.set("instance_id", INSTANCE)
    f = FakePlatform()
    f.hello_reply = dict(f.hello_reply, instance=INSTANCE)
    try:
        env = [{"name": "NXF_SINGULARITY_CACHEDIR", "value": str(s.storage / "cache"), "head": True, "compute": False},
               {"name": "http_proxy", "value": PROXY, "head": True, "compute": True}]
        forward = str(s.storage / "_relay" / "forward_port")
        origin, b = resume_bundle(s, f, ce={"environment": env}, facts={"reach": "ssh", "platform_local": True, "forward_file": forward})
        folder = make_folder(origin)
        before = snapshot(folder)
        s.set("curl_direct", "refused")
        with agent_on(f, s, tmp_path, name="agent-f"):
            res = run_job(f, job_of(b))
        assert res["state"] == "refused" and re.search(r"反向通道沒開", res["result"]["message"]), res
        assert snapshot(folder) == before
        assert not [c for c in s.calls() if c.startswith("sbatch")]
        assert s.destructive() == []
    finally:
        f.stop()


# ---- the checks that are a resume's own, made on the site --------------------------------------------------------------------------------------

NOTHING_CHANGED = r"沒有改動任何東西"


def refused_with_folder(res, f):
    assert res["state"] == "refused", res
    message = res["result"]["message"]
    assert str(f) in message and re.search(NOTHING_CHANGED, message), message


def test_tc028_a_history_whose_session_is_not_the_one_asked_for_is_refused(tmp_path, site, fake):
    # TC-028
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin, session="ffffffff-4f50-4a6b-8c7d-9e0f1a2b3c4d")
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    refused_with_folder(res, f)
    nothing_changed(site, f, before)


def test_tc028_a_folder_without_a_history_is_refused(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin, history=False)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    refused_with_folder(res, f)
    nothing_changed(site, f, before)


def test_tc028_only_the_first_line_with_a_session_counts(tmp_path, site, fake):
    # the first line that has a session id is the one that is compared; a later line with the right one does not rescue it
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin, session="ffffffff-4f50-4a6b-8c7d-9e0f1a2b3c4d")
    with open(f / ".nextflow" / "history", "a") as h:
        h.write("2026-10-18 11:00:00\t1m\tother\tERR\tabc\t%s\tnextflow run x\n" % SESSION)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    refused_with_folder(res, f)
    nothing_changed(site, f, before)


def test_tc028_a_line_before_the_session_without_one_is_skipped(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    text = (f / ".nextflow" / "history").read_text()
    (f / ".nextflow" / "history").write_text("a line with no session id at all\n" + text)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res


@pytest.mark.parametrize("tc,name", [("TC-029", "samplesheet.csv"), ("TC-030", "params.yaml"), ("TC-031", "nextflow.config"),
                                     ("TC-032", "head.sh")])
def test_tc029_to_tc032_an_input_file_that_was_changed_since_the_first_launch_is_refused(tmp_path, site, fake, tc, name):
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    (f / name).write_text((f / name).read_text() + "\n# edited by hand\n")
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    refused_with_folder(res, f)
    nothing_changed(site, f, before)


def test_tc029_an_input_file_that_is_gone_is_refused(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    (f / "params.yaml").unlink()
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    refused_with_folder(res, f)
    nothing_changed(site, f, before)


def test_tc033_an_existing_head_file_of_this_attempt_is_never_overwritten(tmp_path, site, fake):
    # TC-033
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    (f / "head-2.sh").write_text("#!/bin/bash\n# somebody's own\n")
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    refused_with_folder(res, f)
    nothing_changed(site, f, before)
    assert (f / "tower.token").read_text() == OLD_TOKEN


def test_tc034_a_predecessor_that_is_still_in_the_queue_stops_a_resume(tmp_path, site, fake):
    # TC-034
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    site.add_job(7, "nf-run-a", "tester", str(f))
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused" and re.search(r"還在|alive|佇列", res["result"]["message"]), res
    nothing_changed(site, f, before)


def test_tc034_a_queue_that_cannot_be_asked_is_a_refusal_and_not_a_yes(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    site.set("squeue_fail", "1")
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    nothing_changed(site, f, before)


def test_tc034_the_job_of_the_predecessor_is_found_by_its_name_and_the_site_user(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    make_folder(origin)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res
    asked = [c for c in site.calls() if c.startswith("squeue")]
    assert len(asked) == 1 and "-n nf-run-a " in asked[0] + " " and "-u tester" in asked[0], asked


def test_tc035_a_folder_that_is_reached_through_a_link_is_refused(tmp_path, site, fake):
    # TC-035
    origin, b = resume_bundle(site, fake)
    real = site.work / "elsewhere" / "run-a"
    real.parent.mkdir()
    make_folder(origin, where=real)
    (site.work / "runs").mkdir()
    os.symlink(real, origin["run_folder"])
    before = snapshot(real)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    assert str(origin["run_folder"]) in res["result"]["message"] and re.search(NOTHING_CHANGED, res["result"]["message"])
    nothing_changed(site, real, before)


def test_tc035_a_tower_token_that_is_a_link_is_refused(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    target = site.storage / "analysis" / "guard.txt"
    (f / "tower.token").unlink()
    os.symlink(target, f / "tower.token")
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    refused_with_folder(res, f)
    assert site.guards_intact()
    nothing_changed(site, f, before)


# ---- a resume bundle that is not what the agent builds -------------------------------------------------------------------------------------------

def test_tc036_a_run_folder_that_is_not_the_one_of_the_origin_is_refused_even_with_a_matching_hash(tmp_path, site, fake):
    # TC-036: the confirmation is made for exactly this odd bundle, so only the agent's own rebuild can refuse it
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    other = site.work / "runs" / "someone-elses"
    other.mkdir()
    (other / "keep.txt").write_text("not yours")
    t = copy.deepcopy(b)
    t["run_folder"] = str(other)
    before, before_other = snapshot(f), snapshot(other)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(t))
    assert res["state"] == "refused", res
    assert snapshot(f) == before and snapshot(other) == before_other
    assert not [c for c in site.calls() if c.startswith("sbatch")] and site.destructive() == []


@pytest.mark.parametrize("where", ["work-evil", "launch", "elsewhere"])
def test_tc037_a_run_folder_outside_workdir_runs_is_refused(tmp_path, site, fake, where):
    # TC-037: both the bundle and its origin say so, and the confirmation is for exactly that
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    outside = {"work-evil": site.evil / "runs" / "run-a", "launch": site.launch / "run-a", "elsewhere": site.work / "run-a"}[where]
    make_folder(origin, where=outside)
    t = copy.deepcopy(b)
    t["run_folder"] = str(outside)
    t["resume"]["origin"]["run_folder"] = str(outside)
    before, before_out = snapshot(f), snapshot(outside)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(t))
    assert res["state"] == "refused", res
    assert snapshot(f) == before and snapshot(outside) == before_out
    assert not [c for c in site.calls() if c.startswith("sbatch")] and site.destructive() == []


def tampered_resume(b, how):
    t = copy.deepcopy(b)
    if how == "origin-params":
        t["resume"]["origin"]["params"]["primer"] = "OTHER"
    elif how == "origin-samples":
        t["resume"]["origin"]["samplesheet"][1][0] = "s9"
    elif how == "origin-files":
        t["resume"]["origin"]["files"]["head.sh"] += "touch /tmp/evil\n"
    elif how == "origin-revision":
        t["resume"]["origin"]["revision"] = "2.18.1"
    elif how == "session":
        t["resume"]["session_id"] = "ffffffff-4f50-4a6b-8c7d-9e0f1a2b3c4d"
    elif how == "attempt":
        t["resume"]["attempt"] = 3
    elif how == "head":
        t["files"]["head-2.sh"] += "touch /tmp/evil\n"
    elif how == "extra-file":
        t["files"]["evil.sh"] = "touch /tmp/evil\n"
    elif how == "overwrite-head":
        t["files"]["head.sh"] = t["files"].pop("head-2.sh")
    elif how == "new-name":
        t["run_name"] = "another-name"
    elif how == "agent":
        t["agent"] = "agent-other"
    elif how == "no-resume":
        del t["resume"]
    elif how == "no-origin":
        del t["resume"]["origin"]
    elif how == "origin-not-a-dict":
        t["resume"]["origin"] = "x"
    elif how == "resume-not-a-dict":
        t["resume"] = "yes"
    return t


@pytest.mark.parametrize("how", ["origin-params", "origin-samples", "origin-files", "origin-revision", "session", "attempt", "head",
                                 "extra-file", "overwrite-head", "new-name", "agent", "no-resume", "no-origin", "origin-not-a-dict",
                                 "resume-not-a-dict"])
def test_tc038_tc039_a_resume_bundle_changed_after_the_yes_is_refused_by_the_hash(tmp_path, site, fake, how):
    # TC-038 (origin changed), TC-039 (resume block taken out): the confirmation and the hash are those of the unchanged bundle
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    good = job_of(b)
    t = tampered_resume(b, how)
    job = dict(good, args={"bundle": t, "confirmation_id": good["args"]["confirmation_id"], "bundle_sha256": good["args"]["bundle_sha256"]})
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, job)
        assert a.alive()
    assert res["state"] == "refused" and re.search(r"不符|mismatch", res["result"]["message"]), res
    nothing_changed(site, f, before)


@pytest.mark.parametrize("how", ["origin-params", "origin-samples", "origin-files", "origin-revision", "session", "attempt", "head",
                                 "extra-file", "overwrite-head", "new-name", "agent", "no-resume", "no-origin", "origin-not-a-dict",
                                 "resume-not-a-dict"])
def test_tc038_tc039_a_resume_bundle_that_was_confirmed_as_it_is_but_is_not_what_the_agent_builds_is_refused(tmp_path, site, fake, how):
    # the confirmation is made for exactly the odd bundle (hash and all): only the agent's own rebuild and the checks on the site can refuse it
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    t = tampered_resume(b, how)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, job_of(t))
        assert a.alive()
    assert res["state"] == "refused", (how, res)
    nothing_changed(site, f, before)


def test_tc038_an_origin_that_was_changed_consistently_is_refused_because_the_folder_holds_something_else(tmp_path, site, fake):
    # the origin is rebuilt so that it is internally consistent (the agent's rebuild would accept it); the folder was made from another
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    other_origin, other = resume_bundle(site, fake, params={"primer": "SOMETHING-ELSE", "pacbio": True})
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(other))
    refused_with_folder(res, f)
    nothing_changed(site, f, before)


def test_a_resume_bundle_for_another_agent_is_refused(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake, agent="agent-other")
    f = make_folder(origin)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused" and re.search(r"另一個代理|another agent", res["result"]["message"]), res
    nothing_changed(site, f, before)


def test_a_change_of_the_account_between_the_yes_and_the_resume_is_refused(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    before = snapshot(f)
    site.settings.write_text(site.settings.read_text().replace("slurm_account: " + ACCT, "slurm_account: ACCT-CHANGED-3"))
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    nothing_changed(site, f, before)


def test_a_resume_without_a_site_user_cannot_look_for_its_predecessor_and_is_refused(tmp_path, fake):
    s = FakeSite(tmp_path / "nouser", account=ACCT, destructive_log=True)
    (s.storage / "cache").mkdir()
    origin, b = resume_bundle(s, fake)
    f = make_folder(origin)
    before = snapshot(f)
    with agent_on(fake, s, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused" and re.search(r"site_user", res["result"]["message"]), res
    nothing_changed(s, f, before)


def test_a_resume_confirmation_is_spent_once(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    job = job_of(b)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        assert run_job(fake, job)["state"] == "done"
        before = snapshot(f)
        second = run_job(fake, job)
    assert second["state"] == "refused" and re.search(r"已經用過|used already", second["result"]["message"]), second
    assert snapshot(f) == before
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1


# ---- 116b: the paths of an HTTP caller's samples are looked at again at job time -----------------------------------------------------------------

def upload_record(site, swapped=False):
    """The record the platform keeps for a sample in the caller's folder (here: the storage folder stands for it)."""
    given = str(site.storage / "rawdata" / "s1.fq")
    return {"area": str(site.storage), "paths": [{"where": "samplesheet 第 2 列第 2 欄", "given": given, "real": given}]}


def swap_link(site):
    p = site.storage / "rawdata" / "s1.fq"
    p.unlink()
    os.symlink(site.evil, p)      # the sample now leads out of the caller's folder


def test_tc115_a_link_swapped_after_the_yes_stops_a_resume(tmp_path, site, fake):
    # TC-115
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    b["upload_paths"] = upload_record(site)
    swap_link(site)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused" and re.search(r"捷徑|leads somewhere else", res["result"]["message"]), res
    nothing_changed(site, f, before)


def test_tc116_a_resume_with_unmoved_upload_paths_goes_through(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    make_folder(origin)
    b["upload_paths"] = upload_record(site)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res


def test_tc115_a_malformed_upload_record_stops_a_resume(tmp_path, site, fake):
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    b["upload_paths"] = {"area": 7}
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    nothing_changed(site, f, before)


# ---- US3: a relaunch is a launch under a new name ---------------------------------------------------------------------------------------------

def test_tc070_a_relaunch_takes_the_launch_path_one_mkdir_the_files_and_one_sbatch_and_leaves_the_first_folder_alone(tmp_path, site, fake):
    # TC-070, TC-060 (the first folder is as it was), TC-059 (head.sh and tower.token are for the new name)
    origin, b = relaunch_bundle(site, fake)
    first = make_folder(origin)
    before = snapshot(first)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res
    new = site.work / "runs" / "run-a-a2"
    assert res["result"]["run_folder"] == str(new) and res["result"]["run_name"] == "run-a-a2"
    assert sorted(p.name for p in new.iterdir()) == sorted(["samplesheet.csv", "params.yaml", "nextflow.config", "tower.token", "head.sh"])
    assert (new / "head.sh").read_bytes() == b["files"]["head.sh"].encode("utf-8")
    assert "-name run-a-a2" in (new / "head.sh").read_text() and "-resume" not in (new / "head.sh").read_text()
    assert (new / "tower.token").read_text() == TOKEN
    sb = [c for c in site.calls() if c.startswith("sbatch")]
    assert len(sb) == 1 and sb[0].split()[1] == str(new / "head.sh")
    assert len([c for c in site.destructive() if c.startswith("tar")]) == 1
    assert snapshot(first) == before
    assert (first / "tower.token").read_text() == OLD_TOKEN


def test_tc071_a_relaunch_into_a_folder_that_exists_is_refused_and_changes_nothing(tmp_path, site, fake):
    # TC-071
    origin, b = relaunch_bundle(site, fake)
    existing = site.work / "runs" / "run-a-a2"
    existing.mkdir(parents=True)
    (existing / "guard.txt").write_text("guard")
    before = snapshot(existing)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused" and re.search(r"專屬資料夾.*已存在，不覆蓋", res["result"]["message"]), res
    assert snapshot(existing) == before
    assert not [c for c in site.calls() if c.startswith("sbatch")]


def test_tc072_a_relaunch_bundle_is_compared_without_its_relaunch_record_and_its_upload_paths(tmp_path, site, fake):
    # TC-072
    origin, b = relaunch_bundle(site, fake)
    b["upload_paths"] = upload_record(site)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res


def test_tc115_a_link_swapped_after_the_yes_stops_a_relaunch_too(tmp_path, site, fake):
    origin, b = relaunch_bundle(site, fake)
    b["upload_paths"] = upload_record(site)
    swap_link(site)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    assert not (site.work / "runs").exists()


def test_tc073_a_relaunch_whose_samplesheet_is_not_what_the_agent_builds_is_refused(tmp_path, site, fake):
    # TC-073: the confirmation is for exactly this odd bundle; its samplesheet text and rows are changed together
    origin, b = relaunch_bundle(site, fake)
    t = copy.deepcopy(b)
    t["files"]["samplesheet.csv"] = t["files"]["samplesheet.csv"].replace("s1,", "s9,")
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(t))
    assert res["state"] == "refused", res
    assert not (site.work / "runs").exists()
    assert not [c for c in site.calls() if c.startswith("sbatch")]


@pytest.mark.parametrize("how", ["relaunch", "upload_paths"])
def test_a_relaunch_record_is_only_stripped_for_the_comparison_and_stays_in_the_hash(tmp_path, site, fake, how):
    origin, b = relaunch_bundle(site, fake)
    b["upload_paths"] = upload_record(site)
    good = job_of(b)
    t = copy.deepcopy(b)
    if how == "relaunch":
        t["relaunch"]["attempt"] = 9
    else:
        t["upload_paths"]["paths"][0]["real"] = "/x/y"
    job = dict(good, args={"bundle": t, "confirmation_id": good["args"]["confirmation_id"], "bundle_sha256": good["args"]["bundle_sha256"]})
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job)
    assert res["state"] == "refused" and re.search(r"不符|mismatch", res["result"]["message"]), res
    assert not (site.work / "runs").exists()
