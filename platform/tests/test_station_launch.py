# Nothing existing: tests that hand the real agent launch jobs, honest and hostile, through a fake platform and watch a fake site; the protocol and the site are ours.
"""The agent's launch_nextflow job (feature 007b): refusals before anything is written, and what is written when it is allowed."""
import copy
import json
import os
import re
import secrets
import stat
import subprocess
import tarfile
import time
from pathlib import Path

import pytest

from station_harness import FakePlatform, FakeSite, snapshot, snapshot_file
from test_launch_bundle import ce_snapshot, parse_yaml, sbatch_lines, only_template_sbatch, render as render_plain
from test_station_fakeplatform import agent_on, wait_for

ACCT = "ACCT-TEST-7"
TOKEN = "abf_" + secrets.token_hex(16)   # made at run time: a fixed value of this shape in a tracked file fails tests/credentials_stay_in_settings_test.sh


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


def bundle_for(site, fake, run="run-a", agent="agent-f", options="-A %s -c 4 --mem=26G -t 1-00:00:00" % ACCT, **over):
    from abf_station import launch
    env = [{"name": "NXF_SINGULARITY_CACHEDIR", "value": str(site.storage / "cache"), "head": True, "compute": False}]
    ce = ce_snapshot(workDir=str(site.work), launchDir=str(site.launch), headQueue="normal", computeQueue="dev",
                     environment=env, headJobOptions=options, nextflowConfig="process.executor = 'slurm'\n")
    ce.update(over.pop("ce", {}))
    facts = {"slurm_account": ACCT, "reach": "local", "platform_local": True, "endpoint": fake.url, "forward_file": None,
             "storage_root": str(site.storage)}
    facts.update(over.pop("facts", {}))
    roots = [str(site.work), str(site.launch), str(site.storage)]
    kw = dict(ce=ce, agent=agent, facts=facts, roots=roots, run_name=run, pipeline="nf-core/ampliseq", revision="2.18.0",
              samplesheet=[["sample", "fastq_1"], ["s1", str(site.storage / "rawdata" / "s1.fq")]],
              params={"primer": "AGRG", "pacbio": True})
    kw.update(over)
    return launch.render_bundle(**kw)


def job_of(bundle, cid=None, sha=None, kind="launch_nextflow", conf_kind="launch", token=TOKEN, remaining=300, **extra):
    from abf_platform import common
    cid = cid or secrets.token_hex(16)
    sha = sha or common.bundle_sha256(bundle)
    job = {"kind": kind, "args": {"bundle": bundle, "confirmation_id": cid, "bundle_sha256": sha},
           "confirmation": {"id": cid, "sha256": sha, "kind": conf_kind}, "run_token": token, "remaining": remaining}
    job.update(extra)
    return job


def rehash(bundle, **top):
    """A job whose confirmation was made for exactly this (possibly odd) bundle: only the agent's own checks can refuse it."""
    return job_of(bundle, **top)


def run_job(fake, job, timeout=60):
    return fake.wait_result(fake.push_raw(job), timeout)


def folder(site, run="run-a"):
    return site.work / "runs" / run


def nothing_happened(site):
    assert site.calls() == [] or all(c.split()[0] in ("sinfo", "java", "nextflow") for c in site.calls()), site.calls()
    assert not (site.work / "runs").exists()
    assert site.dangerous() == [] and site.destructive() == []
    assert site.guards_intact()


# ---- the one launch path refuses what is not confirmed ------------------------------------------------------------

def test_unconfirmed_launch_is_refused(tmp_path, site, fake):
    # TC-052, TC-053, TC-008: no confirmation, nothing on the site and nothing in the platform's rows. The LAUNCH_ALLOW entry
    # of tests/no_second_run_state_test.sh names this test: it must go red when the check of the confirmation is taken out.
    b = bundle_for(site, fake)
    good = job_of(b)
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        wait_for(lambda: fake.count("hello"))
        for label, job in (("no confirmation id", dict(good, args={"bundle": b, "bundle_sha256": good["args"]["bundle_sha256"]})),
                           ("no confirmation row", {k: v for k, v in good.items() if k != "confirmation"}),
                           ("sha mismatch", dict(good, confirmation=dict(good["confirmation"], sha256="0" * 64))),
                           ("wrong kind", dict(good, confirmation=dict(good["confirmation"], kind="cancel")))):
            res = run_job(fake, job)
            assert res["state"] == "refused", (label, res)
        assert a.alive()
    nothing_happened(site)


def test_unconfirmed_resume_is_refused(tmp_path, site, fake):
    # 009e TC-040: the sibling of test_unconfirmed_launch_is_refused, in the one file that submits. A resume job without a valid confirmation
    # gives no call on the site at all: not the questions to the queue, not the tar, not the sbatch, and the run folder is as it was.
    from resume_harness import make_folder, resume_bundle
    origin, b = resume_bundle(site, fake)
    f = make_folder(origin)
    before = snapshot(f)
    good = job_of(b)
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        wait_for(lambda: fake.count("hello"))
        for label, job in (("no confirmation id", dict(good, args={"bundle": b, "bundle_sha256": good["args"]["bundle_sha256"]})),
                           ("no confirmation row", {k: v for k, v in good.items() if k != "confirmation"}),
                           ("sha mismatch", dict(good, confirmation=dict(good["confirmation"], sha256="0" * 64))),
                           ("wrong kind", dict(good, confirmation=dict(good["confirmation"], kind="cancel"))),
                           ("spent", dict(good, confirmation=dict(good["confirmation"], used_at=12345.0)))):
            res = run_job(fake, job)
            assert res["state"] == "refused", (label, res)
        assert a.alive()
    assert snapshot(f) == before
    assert site.calls() == [] or all(c.split()[0] in ("sinfo", "java", "nextflow") for c in site.calls()), site.calls()
    assert site.dangerous() == [] and site.destructive() == []
    assert site.guards_intact()


@pytest.mark.parametrize("cid", [None, "", 7, ["x"], {"a": 1}, True])
def test_tc008_a_confirmation_id_of_the_wrong_kind_or_none_is_refused(tmp_path, site, fake, cid):
    b = bundle_for(site, fake)
    job = job_of(b)
    job["args"]["confirmation_id"] = cid
    with agent_on(fake, site, tmp_path, name="agent-f"):
        assert run_job(fake, job)["state"] == "refused"
        good = run_job(fake, {"kind": "preflight", "args": {"ce": {"name": "x", "platform": "slurm-platform", "workDir": str(site.work),
                                                                 "launchDir": None, "headQueue": "normal", "computeQueue": None,
                                                                 "readRoots": []}}})
        assert good["state"] == "done", good
    nothing_happened(site)


def test_tc008_unknown_arguments_a_used_confirmation_and_a_confirmation_for_the_other_kind_are_refused(tmp_path, site, fake):
    b = bundle_for(site, fake)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        job = job_of(b)
        job["args"]["cmd"] = "touch x"
        assert run_job(fake, job)["state"] == "refused"
        job = job_of(b)
        job["confirmation"]["used_at"] = 12345.0
        assert run_job(fake, job)["state"] == "refused"
        assert run_job(fake, job_of(b, kind="cancel_run", conf_kind="launch"))["state"] == "refused"
        assert run_job(fake, job_of(b, kind="cancel_run"))["state"] == "refused"  # a launch bundle is no cancel bundle
        job = job_of(b)
        job["confirmation"]["id"] = "another-id"
        assert run_job(fake, job)["state"] == "refused"
    nothing_happened(site)


def tampered(site, fake, how):
    b = bundle_for(site, fake)
    good = job_of(b)
    t = copy.deepcopy(b)
    sha = good["args"]["bundle_sha256"]
    if how == "params":
        t["files"]["params.yaml"] = t["files"]["params.yaml"].replace("AGRG", "AGRX")
    elif how == "samplesheet":
        t["files"]["samplesheet.csv"] = t["files"]["samplesheet.csv"].replace("s1,", "s9,")
        t["samplesheet"][1][0] = "s9"
    elif how == "head":
        t["files"]["head.sh"] = t["files"]["head.sh"] + "touch /tmp/evil\n"
    elif how == "folder":
        t["run_folder"] = t["run_folder"] + "x"
    elif how == "revision":
        t["revision"] = "2.18.1"
    elif how == "ce":
        t["ce"]["computeQueue"] = "other"
    elif how == "account":
        t["account"] = "ACCT-OTHER-9"
    elif how == "config_block":
        # TC-008: the platform's own overwrite block taken out of nextflow.config after the yes
        cfg = t["files"]["nextflow.config"]
        assert "report.overwrite" in cfg
        t["files"]["nextflow.config"] = cfg[:cfg.index("report.overwrite")]
    elif how == "sha":
        sha = sha[:-1] + ("0" if sha[-1] != "0" else "1")
    return dict(good, args={"bundle": t, "confirmation_id": good["args"]["confirmation_id"], "bundle_sha256": sha})


@pytest.mark.parametrize("how", ["params", "samplesheet", "head", "folder", "revision", "ce", "account", "config_block", "sha"])
def test_tc007_a_bundle_changed_after_the_yes_is_refused(tmp_path, site, fake, how):
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, tampered(site, fake, how))
        assert res["state"] == "refused" and re.search(r"不符|mismatch|不一致", res["result"]["message"]), res
        assert a.alive()
    nothing_happened(site)


def test_tc009_a_job_given_twice_is_done_once(tmp_path, site, fake):
    b = bundle_for(site, fake)
    job = job_of(b)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        first = run_job(fake, job)
        assert first["state"] == "done", first
        before = snapshot(folder(site))
        second = run_job(fake, job)
        assert second["state"] == "refused" and re.search(r"已經用過|used already", second["result"]["message"]), second
        assert snapshot(folder(site)) == before
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1


# ---- the agent builds the bundle again ------------------------------------------------------------------------------

@pytest.mark.parametrize("name,mut", [
    ("run name", lambda b: b.update(run_name="Bad")), ("pipeline", lambda b: b.update(pipeline="-hub/x")),
    ("revision", lambda b: b.update(revision="main")), ("path", lambda b: b.update(samplesheet=[["sample", "fastq_1"], ["s", "/etc/passwd"]])),
    ("queue", lambda b: b["ce"].update(headQueue="normal; touch c")), ("agent", lambda b: b.update(agent="agent-other")),
    ("options", lambda b: b["ce"].update(headJobOptions="-c 4 --wrap=touch c")),
    ("outdir", lambda b: b.update(params={"outdir": "/x"})), ("pre-run", lambda b: b["ce"].update(preRunScript="echo hi")),
    ("platform type", lambda b: b["ce"].update(platform="awsbatch-platform"))])
def test_tc011_tc025_the_agent_refuses_values_the_command_line_would_have_refused(tmp_path, site, fake, name, mut):
    b = bundle_for(site, fake)
    mut(b)
    canary = tmp_path / "canary"
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, rehash(b))
        assert res["state"] == "refused", (name, res)
        assert a.alive()
    assert not canary.exists()
    nothing_happened(site)


def test_tc021_a_change_of_the_account_between_the_yes_and_the_run_is_refused(tmp_path, site, fake):
    b = bundle_for(site, fake)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        site.settings.write_text(site.settings.read_text().replace("slurm_account: " + ACCT, "slurm_account: ACCT-CHANGED-3"))
        res = run_job(fake, job_of(b))
        assert res["state"] == "refused" and re.search(r"帳號", res["result"]["message"]), res
    nothing_happened(site)


# ---- a launch that is allowed ----------------------------------------------------------------------------------------

def test_tc012_tc015_tc019_an_allowed_launch_writes_five_private_files_and_submits_once(tmp_path, site, fake):
    b = bundle_for(site, fake)
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, job_of(b))
        assert res["state"] == "done", res
        r = res["result"]
        assert r["ok"] and r["slurm_job_id"] == 4242 and r["run_name"] == "run-a" and r["run_folder"] == str(folder(site))
        out = a.output()
    f = folder(site)
    assert stat.S_IMODE(f.stat().st_mode) == 0o700
    names = sorted(p.name for p in f.iterdir())
    assert names == sorted(["samplesheet.csv", "params.yaml", "nextflow.config", "tower.token", "head.sh"])
    for p in f.iterdir():
        assert stat.S_IMODE(p.stat().st_mode) == 0o600, p.name
    for name, text in b["files"].items():
        assert (f / name).read_bytes() == text.encode("utf-8"), name
    assert (f / "tower.token").read_text() == TOKEN
    # the order on the site: the folder above, one call that makes the folder and unpacks, then sbatch, once
    calls = site.calls()
    sb = [c for c in calls if c.startswith("sbatch")]
    assert len(sb) == 1 and sb[0].split()[1] == str(f / "head.sh")
    assert len([c for c in site.destructive() if c.startswith("tar")]) == 1, site.destructive()
    assert site.scripts() == [b["files"]["head.sh"]]
    only_template_sbatch(site.scripts()[0])
    assert subprocess.run(["bash", "-n", str(f / "head.sh")]).returncode == 0
    # the token is nowhere but in tower.token
    assert TOKEN not in out
    for p in f.iterdir():
        if p.name != "tower.token":
            assert TOKEN not in p.read_text(), p.name
    for c in calls + site.ssh_calls():
        assert TOKEN not in c
    assert TOKEN not in site.scripts()[0]
    assert not [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")]
    assert site.guards_intact()


def _launch_under_umask_022(tmp_path, site, fake):
    """One allowed launch, with an agent whose umask is 022 (the usual one on a login node). Returns the result."""
    site.set("sbatch_out", "1")
    old = os.umask(0o022)
    try:
        with agent_on(fake, site, tmp_path, name="agent-f"):
            return run_job(fake, job_of(bundle_for(site, fake)))
    finally:
        os.umask(old)


def test_tcf3_08_09_no_file_of_the_run_folder_is_wider_than_0700_not_even_the_one_slurm_opens(tmp_path, site, fake):
    # TC-F3-08, TC-F3-09 (TC-047: slurm-*.out was 644 in a 700 folder). The fake sbatch opens slurm-<id>.out with
    # 666 & ~umask of its caller, as Slurm does, and the agent runs under umask 022.
    res = _launch_under_umask_022(tmp_path, site, fake)
    assert res["state"] == "done", res
    f = folder(site)
    assert stat.S_IMODE(f.stat().st_mode) == 0o700
    out = f / "slurm-4242.out"
    assert out.exists(), sorted(p.name for p in f.iterdir())
    assert stat.S_IMODE(out.stat().st_mode) == 0o600, oct(stat.S_IMODE(out.stat().st_mode))
    names = sorted(p.name for p in f.iterdir())
    assert names == sorted(["samplesheet.csv", "params.yaml", "nextflow.config", "tower.token", "head.sh", "slurm-4242.out"])
    for p in f.iterdir():
        mode = stat.S_IMODE(p.stat().st_mode)
        assert mode & 0o077 == 0, (p.name, oct(mode))
        assert mode in ((0o600, 0o700) if p.name == "head.sh" else (0o600,)), (p.name, oct(mode))


def test_tcf3_10_sbatch_is_called_once_with_the_same_argument_under_umask_077(tmp_path, site, fake):
    # TC-F3-10: the umask is what the fake sbatch itself saw, not the text of the command
    res = _launch_under_umask_022(tmp_path, site, fake)
    assert res["state"] == "done", res
    f = folder(site)
    sb = [c for c in site.calls() if c.startswith("sbatch")]
    assert len(sb) == 1 and sb[0].split() == ["sbatch", str(f / "head.sh")], sb
    assert [int(u, 8) for u in site.sbatch_umasks()] == [0o077], site.sbatch_umasks()
    assert res["result"]["message"] == "已送出：Slurm 工作編號 4242，run 名稱 run-a，專屬資料夾 %s" % f


def test_tcf3_30_a_failed_sbatch_leaves_the_folder_and_its_files_no_wider(tmp_path, site, fake):
    # TC-F3-30 (the permission part; the messages are asserted by the existing TC-017 tests)
    site.set("sbatch_fail", "sbatch: error: Invalid account\n")
    old = os.umask(0o022)
    try:
        with agent_on(fake, site, tmp_path, name="agent-f"):
            res = run_job(fake, job_of(bundle_for(site, fake)))
    finally:
        os.umask(old)
    assert res["state"] == "error", res
    f = folder(site)
    assert stat.S_IMODE(f.stat().st_mode) == 0o700
    for p in f.iterdir():
        assert stat.S_IMODE(p.stat().st_mode) & 0o077 == 0, p.name


def test_tc014_hostile_text_is_written_as_text_and_run_by_nothing(tmp_path, site, fake):
    canary = tmp_path / "canary"
    params = {"a": "x'; touch %s; '" % canary, "b": "$(touch %s)" % canary, "c": "`touch %s`" % canary}
    rows = [["sample", "fastq_1"], ["$(touch %s)" % canary, str(site.storage / "rawdata" / "s1.fq")], ["a,b\nc", str(site.storage / "rawdata" / "s1.fq")]]
    b = bundle_for(site, fake, params=params, samplesheet=rows)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        assert run_job(fake, job_of(b))["state"] == "done"
    f = folder(site)
    assert parse_yaml((f / "params.yaml").read_text())["b"] == params["b"]
    import csv, io
    assert list(csv.reader(io.StringIO((f / "samplesheet.csv").read_text()))) == rows
    assert subprocess.run(["bash", "-n", str(f / "head.sh")]).returncode == 0
    assert not canary.exists()


def test_tc013_the_script_the_site_got_runs_nextflow_the_way_seqera_does(tmp_path, site, fake):
    b = bundle_for(site, fake)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        assert run_job(fake, job_of(b))["state"] == "done"
    f = folder(site)
    bindir = tmp_path / "nfbin"
    bindir.mkdir()
    nf = bindir / "nextflow"
    nf.write_text("#!/usr/bin/env python3\nimport json, os, sys\njson.dump({'argv': sys.argv[1:], 'env': dict(os.environ), 'cwd': os.getcwd()}, "
                  "open(os.environ['ABF_TEST_OUT'], 'w'))\n")
    nf.chmod(0o755)
    env = {"PATH": str(bindir) + os.pathsep + os.environ["PATH"], "ABF_TEST_OUT": str(tmp_path / "seen.json")}
    assert subprocess.run(["bash", str(f / "head.sh")], env=env).returncode == 0
    seen = json.load(open(tmp_path / "seen.json"))
    assert seen["argv"] == ["run", "nf-core/ampliseq", "-r", "2.18.0", "-name", "run-a", "-params-file", "params.yaml", "-c",
                            "nextflow.config", "-with-tower", fake.url]
    assert os.path.realpath(seen["cwd"]) == os.path.realpath(str(f))
    assert seen["env"]["SLURM_ACCOUNT"] == ACCT and seen["env"]["TOWER_ACCESS_TOKEN"] == TOKEN
    assert seen["env"]["NXF_SINGULARITY_CACHEDIR"] == str(site.storage / "cache")
    assert "NXF_LOG_FILE" not in seen["env"]


def test_tc016_an_existing_folder_is_refused_and_nothing_in_it_changes(tmp_path, site, fake):
    f = folder(site)
    f.mkdir(parents=True)
    (f / "guard.txt").write_text("guard")
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(bundle_for(site, fake)))
        assert res["state"] == "refused" and re.search(r"已存在|exists", res["result"]["message"]), res
    assert snapshot(f) == before
    assert not [c for c in site.calls() if c.startswith("sbatch")]
    assert not [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")]


def test_tc017_sbatch_failing_is_reported_with_what_is_left_and_never_retried(tmp_path, site, fake):
    site.set("sbatch_fail", "sbatch: error: Batch job submission failed: Invalid account\n")
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(bundle_for(site, fake)))
        assert res["state"] == "error" and not res["result"]["ok"], res
        assert str(folder(site)) in res["result"]["left_on_site"] or str(folder(site)) in res["result"]["message"]
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1
    assert not [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")]
    assert folder(site).is_dir()


def test_tc017_an_unreadable_answer_and_a_number_followed_by_a_dropped_connection_are_told_as_unknown(tmp_path, site, fake):
    site.set("sbatch_garbage", "1")
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(bundle_for(site, fake, run="run-g")))
        assert res["state"] == "error" and re.search(r"可能已送出", res["result"]["message"]), res
        site.clear("sbatch_garbage")
        site.set("sbatch_exit", "255")
        res = run_job(fake, job_of(bundle_for(site, fake, run="run-h")))
        assert res["state"] == "error" and re.search(r"可能已送出", res["result"]["message"]), res
        assert "slurm_job_id" not in res["result"] or res["result"].get("ok") is False
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 2


def test_tc018_the_agent_does_not_submit_when_too_little_of_the_deadline_is_left(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(bundle_for(site, fake), remaining=30))
        assert res["state"] == "refused" and re.search(r"時間|time", res["result"]["message"]), res
    assert not [c for c in site.calls() if c.startswith("sbatch")]
    assert not (site.work / "runs").exists()


def test_tc022_a_preflight_failure_a_read_only_cache_and_an_unset_account_stop_the_launch_before_anything_is_made(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        site.remove("sinfo")
        res = run_job(fake, job_of(bundle_for(site, fake)))
        assert res["state"] == "refused" and "sinfo" in res["result"]["message"], res
        site.restore("sinfo")
        os.chmod(site.storage / "cache", 0o500)
        try:
            res = run_job(fake, job_of(bundle_for(site, fake, run="run-b")))
            assert res["state"] == "refused" and re.search(r"NXF_SINGULARITY_CACHEDIR|快取", res["result"]["message"]), res
        finally:
            os.chmod(site.storage / "cache", 0o700)
    assert not (site.work / "runs").exists()
    assert not [c for c in site.calls() if c.startswith("sbatch")]


def test_tc023_over_local_reach_no_forward_is_opened_and_the_endpoint_is_the_platform(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        assert run_job(fake, job_of(bundle_for(site, fake)))["state"] == "done"
    assert site.ssh_calls() == []
    assert ("-with-tower %s" % fake.url) in site.scripts()[0]


def test_tc073_no_launch_flow_touches_the_guard_files_or_deletes_anything(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        run_job(fake, job_of(bundle_for(site, fake)))
        run_job(fake, tampered(site, fake, "head"))
        site.set("sbatch_fail", "no\n")
        run_job(fake, job_of(bundle_for(site, fake, run="run-z")))
    assert site.guards_intact()
    assert not [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")]


def test_tc065_the_agent_has_no_login_of_its_own_to_offer(tmp_path):
    src = "".join(p.read_text(encoding="utf-8") for p in (Path(__file__).resolve().parents[1] / "abf_station").glob("*.py"))
    assert not re.search(r"getpass|pexpect|paramiko|\botp\b|passphrase", src)


def test_hello_carries_the_facts_a_launch_is_built_from(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        wait_for(lambda: fake.count("hello"))
        hello = [r for r in fake.requests if r[0] == "hello"][0][1]
    f = hello["facts"]
    assert f["slurm_account"] == ACCT and f["reach"] == "local" and f["platform_local"] is True
    assert f["endpoint"] == fake.url and f["storage_root"] == str(site.storage) and f["forward_file"] is None


def test_tc015_a_big_samplesheet_with_chinese_names_is_written_byte_for_byte_and_its_values_stay_off_the_command_lines(tmp_path, site, fake):
    cell, param = "CELLCANARY_77aa31", "PARAMCANARY_5d8e1f"
    raw = str(site.storage / "rawdata" / "s1.fq")
    rows = [["sample", "fastq_1"]] + [["樣本%05d" % i if i != 5 else cell, raw] for i in range(10000)]
    b = bundle_for(site, fake, samplesheet=rows, params={"note": param})
    assert len(b["files"]["samplesheet.csv"].encode("utf-8")) > 1_000_000
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, job_of(b), timeout=120)
        assert res["state"] == "done", res
        out = a.output()
    f = folder(site)
    for name, text in b["files"].items():
        assert (f / name).read_bytes() == text.encode("utf-8"), name
    assert "樣本09999" in (f / "samplesheet.csv").read_text(encoding="utf-8")
    assert len([c for c in site.destructive() if c.startswith("tar")]) == 1, "one call writes all the files"
    assert sorted(p.name for p in f.iterdir()) == sorted(["samplesheet.csv", "params.yaml", "nextflow.config", "tower.token", "head.sh"])
    for canary in (cell, param):
        assert canary not in out and not [c for c in site.calls() + site.ssh_calls() if canary in c]
        assert canary in (f / "samplesheet.csv").read_text() + (f / "params.yaml").read_text()


def test_tc053_a_consistent_bundle_under_the_old_hash_is_refused_for_the_hash_not_for_what_it_says(tmp_path, site, fake):
    # TC-053 (a): the bundle is changed AND built again so that it is internally consistent (the agent's own rebuild-and-compare
    # would accept it); the hash and the confirmation are those of the first one. Only the check of the hash can refuse it.
    old = bundle_for(site, fake, params={"primer": "AGRG", "pacbio": True})
    new = bundle_for(site, fake, params={"primer": "SOMETHING-ELSE", "pacbio": True})
    assert new != old
    good = job_of(old)
    job = dict(good, args={"bundle": new, "confirmation_id": good["args"]["confirmation_id"], "bundle_sha256": good["args"]["bundle_sha256"]})
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job)
        assert res["state"] == "refused" and re.search(r"不符|not the content", res["result"]["message"]), res
    nothing_happened(site)


# ---- abort-report-overwrite: the rendered nextflow.config allows report/timeline overwrite -----------------------------

_OVERWRITE = ["report.overwrite = true", "timeline.overwrite = true"]


def _block_after(user_text, cfg):
    assert cfg.startswith(user_text), (user_text, cfg)
    return cfg[len(user_text):]


def _setting_lines(block):
    return [ln.strip() for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("//")]


def test_abort_tc001_tc002_the_config_ends_with_both_settings_after_the_users_text_verbatim():
    # TC-001, TC-002
    text = "process.executor = 'slurm'\nexecutor.queueSize = 50\n\nprocess.queue = 'normal'\n"
    cfg = render_plain(ce=ce_snapshot(nextflowConfig=text))["files"]["nextflow.config"]
    block = _block_after(text, cfg)
    assert [ln.strip() for ln in cfg.splitlines()][-2:] == _OVERWRITE
    assert _setting_lines(block) == _OVERWRITE


def test_abort_tc003_a_config_without_a_final_newline_gets_the_block_on_a_new_line():
    # TC-003
    text = "process.executor = 'slurm'"
    cfg = render_plain(ce=ce_snapshot(nextflowConfig=text))["files"]["nextflow.config"]
    assert cfg.startswith(text + "\n")
    assert _setting_lines(cfg[len(text):]) == _OVERWRITE


def test_abort_tc004_a_ce_without_a_config_keeps_its_comment_and_gets_the_block():
    # TC-004
    cfg = render_plain(ce=ce_snapshot(nextflowConfig=""))["files"]["nextflow.config"]
    assert cfg.startswith("//") and cfg.endswith("\n")
    assert "no Nextflow config" in cfg.splitlines()[0]
    assert _setting_lines(cfg) == _OVERWRITE


def test_abort_tc005_tc006_the_block_is_commented_and_holds_exactly_the_two_settings():
    # TC-005, TC-006, TC-026 (no path, account or cluster name in the block)
    text = "process.executor = 'slurm'\n"
    block = _block_after(text, render_plain()["files"]["nextflow.config"])
    comments = [ln for ln in block.splitlines() if ln.strip().startswith("//")]
    assert comments and re.search(r"twice", " ".join(comments))
    assert block.lstrip().startswith("//") and block.index("//") < block.index("report.overwrite")
    assert _setting_lines(block) == _OVERWRITE
    for bad in ("report.enabled", "timeline.enabled", "report.file", "/", "nchc", "NCHC"):
        assert bad not in "".join(_setting_lines(block)), bad


def test_abort_tc020_trace_and_dag_are_not_touched():
    # TC-020
    for text in ("process.executor = 'slurm'\n", ""):
        cfg = render_plain(ce=ce_snapshot(nextflowConfig=text))["files"]["nextflow.config"]
        assert "trace.overwrite" not in cfg and "dag.overwrite" not in cfg


def test_abort_tc016_only_launch_py_renders_the_overwrite_settings():
    # TC-016
    root = Path(__file__).resolve().parent.parent
    found = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.py")
                   if "tests" not in p.relative_to(root).parts
                   and re.search(r"report\.overwrite|timeline\.overwrite", p.read_text(encoding="utf-8")))
    assert found == ["abf_station/launch.py"], found


def test_abort_tc009_the_agent_rebuilds_the_same_bundle_with_the_block_and_writes_it_byte_for_byte(tmp_path, site, fake):
    # TC-009
    b = bundle_for(site, fake)
    assert "report.overwrite = true" in b["files"]["nextflow.config"]
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
        assert res["state"] == "done", res
    assert (folder(site) / "nextflow.config").read_bytes() == b["files"]["nextflow.config"].encode("utf-8")


# ---- launch-site-pipeline (M1-02): the agent rebuilds and writes the site-module head script ---------------------------------

from test_launch_bundle import SITE_CE


def test_tc_ls_43_44_45_47_a_site_launch_is_rebuilt_byte_for_byte_and_a_changed_source_is_refused(tmp_path, site, fake):
    # TC-LS-43, TC-LS-47 (pipeline_source lives in the bundle only)
    b = bundle_for(site, fake, ce=SITE_CE)
    assert b["pipeline_source"]["kind"] == "site-module"
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
        assert res["state"] == "done", res
    head = (folder(site) / "head.sh").read_text()
    assert head == b["files"]["head.sh"] and 'module load biology/Nextflow/26.10.0' in head and " -r " not in head
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1


@pytest.mark.parametrize("how", ["source", "modules"])
def test_tc_ls_44_45_a_bundle_changed_after_the_yes_is_refused(tmp_path, site, fake, how):
    b = bundle_for(site, fake, ce=SITE_CE)
    if how == "source":
        b["pipeline_source"] = {"kind": "remote"}
    else:
        b["ce"]["modules"] = b["ce"]["modules"] + ["evil/mod"]
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] != "done", res
    assert not folder(site).exists()
    assert not [c for c in site.calls() if c.startswith("sbatch")]


def test_tc_ls_33_a_bad_module_in_a_confirmed_bundle_is_refused_naming_modules(tmp_path, site, fake):
    b = bundle_for(site, fake, ce=SITE_CE)
    b["ce"]["modules"] = ["a;b"]
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] != "done" and "modules" in json.dumps(res, ensure_ascii=False) and "內容不合規則" in json.dumps(res, ensure_ascii=False)
    assert not folder(site).exists() and not [c for c in site.calls() if c.startswith("sbatch")]


LAUNCHES_COLUMNS = ["id", "run_name", "slurm_job_id", "run_folder", "ce", "agent", "confirmed_at", "submitted_at", "cancel_requested_at",
                    "job_id", "user_id", "parent_run", "attempt", "attempt_kind", "work_cleaned_at"]      # store._LAUNCHES_TABLE, which this task does not touch


def test_tc_ls_27_clean_environment_lets_the_three_keys_through_and_drops_what_it_does_not_know():
    # TC-LS-27
    from abf_station import rules
    ce = {"platform": "slurm-platform", "workDir": "/data/w1", "launchDir": "/data/launch", "headQueue": "normal", "computeQueue": "dev",
          "readRoots": ["/data/storage"], "evil": "rm -rf /", "preRunScript": "x"}
    ce.update(copy.deepcopy(SITE_CE))
    out = rules.clean_environment(ce)
    for k, v in SITE_CE.items():
        assert out[k] == v
    assert "evil" not in out and "preRunScript" not in out
    assert (out["workDir"], out["launchDir"], out["headQueue"], out["computeQueue"], out["readRoots"]) == \
        ("/data/w1", "/data/launch", "normal", "dev", ["/data/storage"])
    base = {k: v for k, v in ce.items() if k not in SITE_CE}      # a snapshot made before the keys: the same judgement as before
    old = rules.clean_environment(base)
    assert (old["workDir"], old["headQueue"], old["computeQueue"]) == ("/data/w1", "normal", "dev")
    assert old["modules"] == [] and old["siteConfigVars"] == [] and old["sitePipelines"] == []
    for bad in (dict(ce, workDir="/"), dict(ce, headQueue="a b"), dict(ce, modules="biology/Nextflow/26.10.0"),
                dict(ce, sitePipelines=[{"pipeline": "x"}])):
        with pytest.raises(rules.Refusal):
            rules.clean_environment(bad)


def test_tc_ls_12_47_a_terminal_launch_with_the_old_arguments_shows_the_site_start_and_keeps_it_in_the_bundle_only(tmp_path, monkeypatch):
    # TC-LS-12 (same arguments as before; the screen the person says yes to has the module lines and the home variable, no -r),
    # TC-LS-47 (the kept bundle_json has pipeline_source; the launches table has the columns it had)
    import sqlite3
    from launch_harness import QUESTION_LAUNCH, LaunchData, Pty, cli_argv
    from station_harness import Inproc
    from test_launch_cli import parts, section, unescape
    data = LaunchData(Inproc(tmp_path / "ip", monkeypatch), config_json=json.dumps(SITE_CE))      # made by the normal `ce create`
    args = data.launch_args(tmp_path)
    assert {a.split("=")[0] for a in args if a.startswith("--")} == {"--ce", "--pipeline", "--revision", "--run-name", "--samplesheet",
                                                                      "--param"}
    assert args[args.index("--pipeline") + 1] == "nf-core/ampliseq" and args[args.index("--revision") + 1] == "2.18.0"
    p = Pty(cli_argv(*args), data.env())
    assert p.wait_for(QUESTION_LAUNCH, 30), p.text()
    lines, _ = parts(p.text(), QUESTION_LAUNCH)
    head = "\n".join(unescape(x) for x in section(lines, "head.sh"))
    assert "module load biology/Nextflow/26.10.0 || exit 1" in head and "module load biology/nf-core-ampliseq/2.18.0 || exit 1" in head
    assert 'exec nextflow run "$NFCORE_AMPLISEQ_HOME"' in head and " -r " not in head
    assert data.snapshot() == (0, 0, 0, 0)      # nothing is made before the yes
    p.send("y\n")
    p.finish(60)
    assert data.count("confirmations") == 1 and data.count("jobs") == 1 and data.count("launches") == 1
    con = sqlite3.connect(str(data.ip.state_db))
    try:
        kept = json.loads(con.execute("SELECT bundle_json FROM confirmations").fetchone()[0])
        cols = [r[1] for r in con.execute("PRAGMA table_info(launches)")]
        sent = json.loads(con.execute("SELECT args_json FROM jobs WHERE kind = 'launch_nextflow'").fetchone()[0])["bundle"]
    finally:
        con.close()
    want = {"kind": "site-module", "module": "biology/nf-core-ampliseq/2.18.0", "home": "NFCORE_AMPLISEQ_HOME"}
    assert kept["pipeline_source"] == want and sent["pipeline_source"] == want
    assert kept["files"]["head.sh"].rstrip("\n") == head.rstrip("\n")      # what the person saw is what was kept
    assert cols == LAUNCHES_COLUMNS, cols      # no pipeline_source column: it lives in bundle_json


def test_tc_ls_41_a_resume_of_a_site_launch_reads_the_module_lines_and_the_home_variable_into_head_2(tmp_path, site, fake):
    # TC-LS-41
    from resume_harness import make_folder, resume_bundle
    origin, b = resume_bundle(site, fake, ce=SITE_CE)
    assert origin["pipeline_source"]["kind"] == "site-module"
    f = make_folder(origin)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1
    head2 = (f / "head-2.sh").read_text()
    assert head2 == b["files"]["head-2.sh"] and site.scripts() == [head2]
    assert "module load biology/Nextflow/26.10.0 || exit 1" in head2 and "module load biology/nf-core-ampliseq/2.18.0 || exit 1" in head2
    assert 'exec nextflow run "$NFCORE_AMPLISEQ_HOME"' in head2 and " -resume " in head2 and " -r " not in head2
    assert (f / "head.sh").read_bytes() == origin["files"]["head.sh"].encode("utf-8")


def test_tc_ls_42_a_run_started_before_the_site_keys_existed_still_resumes_from_the_remote(tmp_path, site, fake):
    # TC-LS-42: an origin and a resume bundle in the shape made before this change (no pipeline_source, no site keys in the environment)
    from resume_harness import make_folder, resume_bundle
    origin, b = resume_bundle(site, fake)
    for doc in (origin, b["resume"]["origin"], b):
        doc.pop("pipeline_source", None)
        for k in ("modules", "siteConfigVars", "sitePipelines"):
            doc["ce"].pop(k)
    assert "pipeline_source" not in b["resume"]["origin"] and "modules" not in b["ce"]
    f = make_folder(origin)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res
    head2 = (f / "head-2.sh").read_text()
    assert " -r 2.18.0 " in head2 and "module load" not in head2 and "NFCORE" not in head2 and " -resume " in head2
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1


def test_tc_ls_52_the_launch_tool_and_the_tool_list_are_those_of_the_base(tmp_path, monkeypatch):
    # TC-LS-52, rewritten by http-launch-site-samplesheet (maintainer ruling 2026-10-23, TC-036): no tool appears or goes, and launch takes the
    # arguments of before plus the optional samplesheet_text; samplesheet becomes optional too (exactly one of the two is given)
    import asyncio
    from mcp import Client
    from abf_platform import mcp_server
    from station_harness import Inproc
    ip = Inproc(tmp_path / "ip", monkeypatch)

    async def listing():
        async with Client(mcp_server.build_server(ip.index)) as c:
            return (await c.list_tools()).tools

    tools = {t.name: t for t in asyncio.run(listing())}
    assert set(tools) == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files",
                          "list_used_pipelines", "read_task_log", "run_outputs", "launch", "cancel", "forget", "resume", "relaunch"}
    schema = tools["launch"].input_schema
    assert set(schema["properties"]) == {"pipeline", "revision", "run_name", "samplesheet", "samplesheet_text", "ce_name", "params", "path_columns"}
    assert sorted(schema["required"]) == ["pipeline", "revision", "run_name"]
    assert schema["properties"]["samplesheet"].get("default") is None and schema["properties"]["samplesheet_text"].get("default") is None


def test_tc_ls_53_the_run_token_is_in_no_bundle_no_script_no_refusal_and_no_log(tmp_path, site, fake):
    # TC-LS-53: the token is only in tower.token; the new module lines and -c lines carry no secret; a refusal and the agent's log do not either
    b = bundle_for(site, fake, ce=SITE_CE)
    assert TOKEN not in json.dumps(b) and TOKEN not in b["files"]["head.sh"]
    bad = bundle_for(site, fake, run="run-bad", ce=SITE_CE)
    bad["ce"]["modules"] = ["a;b"]
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        good = run_job(fake, job_of(b))
        refused = run_job(fake, job_of(bad))
        out = a.output()
    assert good["state"] == "done" and refused["state"] != "done", (good, refused)
    for text in (json.dumps(good), json.dumps(refused, ensure_ascii=False), out):
        assert TOKEN not in text
    assert "modules" in json.dumps(refused, ensure_ascii=False)
    assert TOKEN not in site.scripts()[0] and not [c for c in site.calls() + site.ssh_calls() if TOKEN in c]
    assert (folder(site) / "tower.token").read_text() == TOKEN
