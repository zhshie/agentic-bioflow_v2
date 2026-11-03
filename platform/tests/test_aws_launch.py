# Nothing existing: searched Nextflow's awsbatch executor, the launch command of the Seqera CLI and nf-core's tower launch tool; they all hand the work to a Seqera service, none gives a local agent a confirmed launch and cancel, so these tests drive our agent with a fake host (no network, no real program).
"""Launching and cancelling on AWS Batch (aws-launch).

The agent that sits on the platform host starts Nextflow's head process on that host (the compute is done by Batch jobs). Every test
uses fakes for the program runner (`site.run_fixed`), the aws runner of the preflight (`aws_preflight._run`), the detached start
(`site.start_detached`) and the signal (`os.kill`); nothing here reaches the network or starts a real program. The TC ids refer to
specs/aws-launch/test-case.md. No key-shaped string is written here as one literal: test_aws_ce builds them from pieces.
"""
import asyncio
import copy
import hashlib
import json
import os
import re
import secrets
import signal
import sqlite3
import stat
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from test_aws_ce import (ACCOUNT, AKID, AWS, BUCKET_URL, CRED, CRED_FILE, QUEUE, REGION, Fake, create, fake_aws,  # noqa: F401
                         good_config, ip, jobs_count, register_agent, set_status)
from test_gcb_ce import GCB, doc

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="permission bits and /proc")
TOKEN = "abf_" + secrets.token_hex(16)     # made at run time: a fixed value of this shape in a tracked file fails tests/credentials_stay_in_settings_test.sh
SHEET = [["sample", "fastq_1", "strandedness"], ["s1", "s3://lab-bucket/x.fastq.gz", "auto"]]
PID = 4242
WORK = "s3://lab-bucket/" + "work"
MARKER = "MARKER" + "SECRET0123456789abcdefghij"      # the secret line of CRED_FILE
BILLING = ("| 費用：按下 y 之後，這個 run 會在 AWS 區域 eu-west-1 的 job queue lab-queue 上建立 Batch 工作與運算資源，由 AWS 向實驗室的 AWS 帳號收費。"
           "平台目前還沒有費用預估與上限；實際金額請看 AWS 的帳單。主控程序跑在平台主機上，取消請用平台的取消指令。")


def ace(**over):
    """The snapshot of a fully set AWS Batch environment, as launch.snapshot_ce gives it."""
    c = {"name": "aws1", "platform": AWS, "region": REGION, "workDir": WORK, "jobQueue": QUEUE, "spot": True, "maxvCpus": 16,
         "environment": [], "nextflowConfig": "// the user's own text\nprocess.cpus = 2\n", "preRunScript": "", "postRunScript": ""}
    c.update(over)
    return c


class Box:
    """The platform host as the agent sees it: a storage root, a settings file, a credential file, and fakes for what it runs."""

    def __init__(self, tmp, monkeypatch):
        from abf_station import aws_preflight, site
        self.tmp = Path(tmp)
        self.mp = monkeypatch
        self.root = self.tmp / "host"
        self.storage = self.root / "storage"
        self.storage.mkdir(parents=True)
        self.settings = self.root / "deploy" / "config" / "env.yaml"
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text("reach: local\nstorage_root: %s\n" % self.storage)
        self.cred = self.root / "aws-credentials"
        self.cred.write_text(CRED_FILE)
        if sys.platform != "win32":
            self.cred.chmod(0o600)
        monkeypatch.setenv("ABF_STATION_AWS_CREDENTIALS", str(self.cred))
        monkeypatch.setenv("ABF_STATION_GCB_SETTLE_SECONDS", "0")
        self.java = (0, 'openjdk version "17.0.9" 2023-10-17')
        self.nextflow = (0, "      N E X T F L O W\n      version 25.04.0 build 5953")
        self.awscli = (0, "aws-cli/2.15.0")
        self.ps = None
        self.runs = []
        self.started = []
        self.kills = []
        self.exit_code = None
        self.out_text = ""
        self.pid = PID
        self.start_error = None
        self.user = "tester"
        self.real_start = getattr(site, "start_detached", None)
        self.fake = fake_aws(monkeypatch)
        monkeypatch.setattr(site, "run_fixed", self._run_fixed)
        monkeypatch.setattr(site, "start_detached", self._start)
        monkeypatch.setattr(os, "kill", lambda pid, sig: self.kills.append((pid, sig)))
        self.ctx = SimpleNamespace(site=None, settings_file=str(self.settings), platform_url="http://127.0.0.1:8123",
                                   agent_name="a1", instance_id=None, used_confirmations=set(), job_started=time.monotonic())

    def _run_fixed(self, argv, env, timeout):
        self.runs.append((list(argv), dict(env or {})))
        prog = argv[0]
        if prog == "java":
            return self.java
        if prog == "nextflow":
            return self.nextflow
        if prog == "aws":
            return self.awscli
        if prog == "ps":
            return self.ps if self.ps is not None else (1, "")
        raise AssertionError("an unexpected program: %r" % (argv,))

    def _start(self, argv, env, cwd, out_path):
        if self.start_error:
            raise self.start_error
        rec = {"argv": list(argv), "env": dict(env), "cwd": str(cwd), "out_path": str(out_path)}
        try:
            rec["script"] = Path(argv[1]).read_text()
        except OSError:
            rec["script"] = None
        self.started.append(rec)
        if self.out_text:
            Path(out_path).write_text(self.out_text)
        return SimpleNamespace(pid=self.pid, poll=lambda: self.exit_code)

    def facts(self, **over):
        f = {"slurm_account": None, "reach": "local", "platform_local": True, "endpoint": "http://127.0.0.1:8123",
             "forward_file": None, "storage_root": str(self.storage), "way_back": None, "platform_public_url": None}
        f.update(over)
        return f

    def bundle(self, run="run-a", **over):
        from abf_station import launch
        kw = dict(ce=ace(), agent="a1", facts=self.facts(), roots=[], run_name=run, pipeline="nf-core/rnaseq", revision="3.14.0",
                  samplesheet=copy.deepcopy(SHEET), params={"genome": "GRCh38"})
        kw.update(over)
        return launch.render_aws_bundle(**kw)

    def handle(self, job):
        from abf_station import handlers
        return handlers.handle(job, self.ctx)

    def folder(self, run="run-a"):
        return self.storage / "_aws_runs" / run

    def cancel_world(self, run="run-a", pid=PID, args=None, owner=None, cwd=None):
        from abf_station import gcb_launch
        owner = owner or self.user
        args = args if args is not None else ("/usr/bin/java -cp x nextflow.cli.Launcher run nf-core/rnaseq -r 3.14.0 -name %s "
                                             "-with-tower http://127.0.0.1:8123" % run)
        self.ps = (0, "%s %s\n" % (owner, args))
        self.mp.setattr(gcb_launch, "_current_user", lambda: self.user)
        folder = os.path.realpath(str(self.folder(run))) if cwd is None else cwd
        self.mp.setattr(gcb_launch, "_proc_cwd", lambda p: folder)


@pytest.fixture
def box(tmp_path, monkeypatch):
    return Box(tmp_path, monkeypatch)


def job_of(bundle, cid=None, sha=None, kind="launch_nextflow", conf_kind="launch", token=TOKEN, remaining=300, **extra):
    from abf_platform import common
    cid = cid or secrets.token_hex(16)
    sha = sha or common.bundle_sha256(bundle)
    job = {"kind": kind, "args": {"bundle": bundle, "confirmation_id": cid, "bundle_sha256": sha},
           "confirmation": {"id": cid, "sha256": sha, "kind": conf_kind}, "run_token": token, "remaining": remaining}
    job.update(extra)
    return job


def launch_ok(box, run="run-a", **over):
    b = box.bundle(run, **over)
    state, res = box.handle(job_of(b))
    assert state == "done", res
    return b, res


def cancel_bundle(box, run="run-a", number=PID, **over):
    b = {"version": 1, "run_name": run, "slurm_job_id": number, "run_folder": str(box.folder(run)), "agent": "a1", "ce": ace()}
    b.update(over)
    return b


def cancel_job(bundle, **kw):
    return job_of(bundle, kind="cancel_run", conf_kind="cancel", **kw)


def nothing_happened(box):
    assert box.started == []
    assert not (box.storage / "_aws_runs").exists()
    assert box.kills == []


def config_keys(text):
    """{key: value text} of the `key = value` lines of an aws.config; comment lines are skipped."""
    out = {}
    for ln in text.splitlines():
        if not ln.strip() or ln.lstrip().startswith("//"):
            continue
        k, eq, v = ln.partition(" = ")
        assert eq, "not a setting line: %r" % ln
        assert k not in out, k
        out[k] = v
    return out


# ======================================================================================================================
# US1 - launch after the yes
# ======================================================================================================================

def test_launch_writes_head_pid_and_reports_it_as_the_job_number(box):
    # TC-001, TC-002, TC-003, TC-004, TC-005, TC-008
    b, res = launch_ok(box)
    folder = box.folder()
    assert res["ok"] is True and res["slurm_job_id"] == PID and res["run_name"] == "run-a" and res["run_folder"] == str(folder)
    assert res["message"] == ("已啟動：主控程序編號（pid）%d，run 名稱 run-a，專屬資料夾 %s；AWS Batch 的工作與費用從現在開始計" % (PID, folder))
    assert (folder / "head.pid").read_text().strip() == str(PID)
    for name in ("samplesheet.csv", "params.yaml", "nextflow.config", "aws.config", "head.sh", "tower.token", "head.pid"):      # TC-005
        assert (folder / name).is_file(), name
    assert not list(folder.glob("results*"))
    if sys.platform != "win32":
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700
        for name in ("samplesheet.csv", "params.yaml", "nextflow.config", "aws.config", "head.sh", "tower.token", "head.pid"):
            assert stat.S_IMODE((folder / name).stat().st_mode) == 0o600, name
    assert (folder / "tower.token").read_text() == TOKEN
    assert len(box.started) == 1
    s = box.started[0]
    assert s["argv"] == ["bash", str(folder / "head.sh")] and s["cwd"] == str(folder) and s["out_path"] == str(folder / "head.out")
    # TC-008: the wait after the start comes from the existing variable
    from abf_station import aws_launch, gcb_launch
    box.mp.setenv("ABF_STATION_GCB_SETTLE_SECONDS", "7")
    assert gcb_launch._settle_seconds() == 7 and aws_launch._settle_seconds is gcb_launch._settle_seconds


def test_the_platform_records_the_pid_in_the_launches_row(ip, box):
    # TC-006
    row = launch_through_platform(ip, box)
    assert row["slurm_job_id"] == PID and row["submitted_at"] is not None


def register_with_facts(ip, box):
    from abf_platform import agents
    register_agent(ip)
    agents.register(ip.state_db, "a1", "0.1.0", time.time, facts=box.facts())


def sheet_file(tmp, rows=None):
    p = Path(tmp) / "samples.csv"
    p.write_text("\n".join(",".join(r) for r in (rows or SHEET)) + "\n")
    return p


def prepare(ip, box, run="run-p", owner=None, **kw):
    from abf_launch import build
    return build.prepare_launch(ip.state_db, ce="aws1", pipeline="nf-core/rnaseq", revision="3.14.0", run_name=run,
                                samplesheet=str(sheet_file(box.tmp)), params={"genome": "GRCh38"}, owner=owner, **kw)


def launch_through_platform(ip, box, run="run-p"):
    """prepare, the human yes, the queue, the agent, the answer: the launches row of the run."""
    from abf_platform import actions, jobs
    register_with_facts(ip, box)
    create(ip)
    set_status(ip, "aws1", "available")
    ce_name, bundle = prepare(ip, box, run)
    cid, job_id = actions.launch(ip.state_db, ce_name, bundle, confirmed_by=actions.TERMINAL)
    job = jobs.claim(ip.state_db, "a1", time.time, tokens_path=ip.tokens)
    while job is not None and job["id"] != job_id:      # the first preflight of the new environment may be queued before the launch
        jobs.take_result(ip.state_db, "a1", job["id"], "done", {"ok": True, "checks": []}, time.time, tokens_path=ip.tokens)
        job = jobs.claim(ip.state_db, "a1", time.time, tokens_path=ip.tokens)
    assert job is not None and job["id"] == job_id
    state, result = box.handle(job)
    assert state == "done", result
    code, _ = jobs.take_result(ip.state_db, "a1", job["id"], state, result, time.time, tokens_path=ip.tokens)
    assert code == 200
    con = sqlite3.connect(str(ip.state_db))
    con.row_factory = sqlite3.Row
    try:
        return con.execute("SELECT * FROM launches WHERE run_name = ?", (run,)).fetchone()
    finally:
        con.close()


def test_a_person_must_say_yes_an_aws_launch_is_never_auto_queued(ip, box, monkeypatch):
    # TC-007, TC-013, TC-014
    import argparse
    from abf_launch import cli, terminal
    register_with_facts(ip, box)
    create(ip)
    set_status(ip, "aws1", "available")
    n = jobs_count(ip)
    prepare(ip, box)
    assert jobs_count(ip) == n
    monkeypatch.setattr(terminal, "terminal_problem", lambda: None)
    monkeypatch.setattr(terminal, "ask", lambda lines, question: False)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(ip.index))
    args = argparse.Namespace(ce="aws1", pipeline="nf-core/rnaseq", revision="3.14.0", run_name="run-n", samplesheet=str(sheet_file(box.tmp)),
                              params_file=None, param=["genome=GRCh38"], path_column=None, user=None)
    assert cli.cmd_launch(args) == 1
    assert jobs_count(ip) == n
    monkeypatch.setattr(terminal, "terminal_problem", lambda: "not a terminal")
    assert cli.cmd_launch(args) == 1
    assert jobs_count(ip) == n
    from abf_platform import actions
    with pytest.raises(Exception):
        actions.launch(ip.state_db, "aws1", prepare(ip, box, "run-q")[1], confirmed_by="the model says yes")
    assert jobs_count(ip) == n


def test_unconfirmed_aws_launch_is_refused_and_nothing_is_written_or_started(box):
    # TC-009, TC-010, TC-011, TC-012
    b = box.bundle()
    good = job_of(b)
    cases = (("no confirmation id", dict(good, args={"bundle": b, "bundle_sha256": good["args"]["bundle_sha256"]})),
             ("no confirmation row", {k: v for k, v in good.items() if k != "confirmation"}),
             ("sha mismatch", dict(good, confirmation=dict(good["confirmation"], sha256="0" * 64))),
             ("wrong kind", dict(good, confirmation=dict(good["confirmation"], kind="cancel"))),
             ("spent", dict(good, confirmation=dict(good["confirmation"], used_at=12345.0))))
    for label, job in cases:
        state, res = box.handle(job)
        assert state == "refused", (label, res)
        nothing_happened(box)
    assert box.runs == []
    state, _ = box.handle(good)
    assert state == "done"
    state, res = box.handle(good)
    assert state == "refused" and len(box.started) == 1


def test_a_changed_bundle_is_refused_by_the_agent(box):
    # TC-015, TC-016, TC-017
    b = box.bundle()
    changed = copy.deepcopy(b)
    changed["files"]["aws.config"] = changed["files"]["aws.config"].replace("eu-west-1", "eu-west-2")
    other = copy.deepcopy(b)
    other["ce"]["jobQueue"] = "other-queue"
    sheet = copy.deepcopy(b)
    sheet["samplesheet"][1][2] = "reverse"
    for label, bad in (("config", changed), ("queue", other), ("samplesheet", sheet)):
        state, res = box.handle(job_of(bad))
        assert state == "refused", (label, res)
        nothing_happened(box)


def test_an_existing_run_folder_is_never_overwritten(box):
    # TC-018
    folder = box.folder()
    folder.mkdir(parents=True)
    (folder / "keep.txt").write_text("mine")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "已存在" in res["message"]
    assert [p.name for p in folder.iterdir()] == ["keep.txt"] and (folder / "keep.txt").read_text() == "mine"
    assert box.started == []


@posix_only
def test_a_link_in_the_run_folder_is_never_followed(box):
    # TC-019
    target = box.tmp / "elsewhere"
    target.mkdir()
    (target / "head.sh").write_text("untouched")
    folder = box.folder()
    folder.parent.mkdir(parents=True)
    os.symlink(str(target), str(folder))
    state, res = box.handle(job_of(box.bundle()))
    assert state in ("refused", "error") and box.started == []
    assert (target / "head.sh").read_text() == "untouched" and [p.name for p in target.iterdir()] == ["head.sh"]
    from abf_station import aws_launch
    victim = box.tmp / "victim.txt"
    victim.write_text("untouched")
    os.symlink(str(victim), str(box.tmp / "link"))
    with pytest.raises(OSError):
        aws_launch._write_new(str(box.tmp / "link"), b"x")
    assert victim.read_text() == "untouched"


def test_a_write_that_fails_halfway_is_an_error_that_names_the_folder_left_behind(box, monkeypatch):
    # TC-020
    from abf_station import aws_launch
    real = aws_launch._write_new
    calls = []

    def flaky(path, data, mode=0o600):
        calls.append(path)
        if len(calls) == 3:
            raise OSError("disk full")
        return real(path, data, mode)
    monkeypatch.setattr(aws_launch, "_write_new", flaky)
    state, res = box.handle(job_of(box.bundle()))
    assert state == "error" and res["ok"] is False
    assert str(box.folder()) in res["left_on_site"] and str(box.folder()) in res["message"]
    assert box.folder().is_dir() and box.started == []


def test_a_head_that_dies_at_once_is_reported_with_its_scrubbed_tail(box):
    # TC-021
    begin = "-----BEGIN " + "PRIVATE KEY-----"
    box.exit_code = 1
    box.out_text = "Unable to launch\n" + begin + "\nMARKERPRIVATEBODY0123456789abcdef\n"
    state, res = box.handle(job_of(box.bundle()))
    assert state == "error" and res["ok"] is False
    assert "1" in res["message"] and "Unable to launch" in res["message"] and "[hidden]" in res["message"]
    assert "MARKERPRIVATEBODY" not in json.dumps(res) and begin not in json.dumps(res)
    assert (box.folder() / "head.out").exists() and len(box.started) == 1


def test_missing_java_nextflow_or_aws_cli_stops_the_launch_in_plain_words(box):
    # TC-022, TC-023, TC-024, TC-025, TC-033
    box.java = (127, "could not start java (FileNotFoundError)")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "Java" in res["message"] and "17" in res["message"]
    nothing_happened(box)
    box.java = (0, 'openjdk version "11.0.2" 2019-01-15')
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "17" in res["message"] and "Java" in res["message"]
    nothing_happened(box)
    box.java = (0, 'openjdk version "17.0.9" 2023-10-17')
    box.nextflow = (127, "could not start nextflow (FileNotFoundError)")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "Nextflow" in res["message"]
    nothing_happened(box)
    box.nextflow = (0, "      N E X T F L O W\n      version 25.04.0 build 5953")
    box.awscli = (127, "could not start aws (FileNotFoundError)")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "aws" in res["message"] and "AWS CLI" in res["message"]
    nothing_happened(box)
    assert not re.search(r"Traceback|FileNotFoundError", res["message"])


def test_too_little_deadline_is_refused(box):
    # TC-026
    state, res = box.handle(job_of(box.bundle(), remaining=5))
    assert state == "refused" and "期限" in res["message"]
    nothing_happened(box)


def test_a_failing_preflight_refuses_the_launch(box):
    # TC-027
    box.mp.setattr(__import__("abf_station.aws_preflight", fromlist=["x"]), "_run", Fake(replies={"batch": (1, "AccessDenied")}))
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "預檢" in res["message"] and "job_queue" in res["message"]
    nothing_happened(box)


@posix_only
def test_a_host_without_proc_is_refused_in_plain_words(box, monkeypatch):
    # TC-028
    from abf_station import aws_launch
    monkeypatch.setattr(aws_launch, "_has_proc", lambda: False)
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "Linux" in res["message"] and "WSL" in res["message"]
    nothing_happened(box)


def test_run_folder_is_under_storage_root_in_aws_runs_and_a_missing_storage_root_is_refused(box):
    # TC-004, TC-029
    from abf_station import launch
    b = box.bundle()
    assert b["run_folder"] == "%s/_aws_runs/run-a" % box.storage
    with pytest.raises(launch.BundleError) as e:
        box.bundle(facts=box.facts(storage_root=None))
    assert "storage_root" in str(e.value) and "部署設定檔" in str(e.value)


def test_scripts_before_or_after_the_run_are_refused(box):
    # TC-030
    from abf_station import launch
    for key in ("preRunScript", "postRunScript"):
        with pytest.raises(launch.BundleError) as e:
            box.bundle(ce=ace(**{key: "echo hi"}))
        assert launch.NO_SCRIPTS in str(e.value)


def test_a_bare_bucket_work_dir_is_refused_at_launch_with_nextflows_rule(box):
    # TC-031
    from abf_station import launch
    with pytest.raises(launch.BundleError) as e:
        box.bundle(ce=ace(workDir="s3://lab-bucket"))
    assert "子目錄" in str(e.value) and "subdirectory" in str(e.value)


def test_a_launch_that_fails_a_step_is_not_retried(box):
    # TC-032
    box.exit_code = 3
    state, _ = box.handle(job_of(box.bundle()))
    assert state == "error" and len(box.started) == 1
    box.start_error = OSError("cannot start")
    state, res = box.handle(job_of(box.bundle("run-b")))
    assert state == "error" and len(box.started) == 1 and "Traceback" not in res["message"]


def test_launch_on_an_aws_environment_that_is_not_available_is_refused(ip):
    # TC-034
    from abf_platform import jobs
    register_agent(ip)
    create(ip)
    set_status(ip, "aws1", "available")
    jobs.check_target(ip.state_db, "aws1", "launch_nextflow")
    n = jobs_count(ip)
    for status in ("invalid", "creating", "disabled"):
        set_status(ip, "aws1", status, ok=0)
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(ip.state_db, "aws1", "launch_nextflow")
    assert jobs_count(ip) == n


# ======================================================================================================================
# US2 - the bundle and the files
# ======================================================================================================================

def test_aws_bundle_has_the_five_files_and_the_expected_keys(box):
    # TC-035, TC-036, TC-037, TC-038
    from abf_station import launch
    b = box.bundle()
    g = launch.render_gcb_bundle(ce={"name": "gcb1", "platform": GCB, "project": "lab-project-1", "location": "europe-west2",
                                     "workDir": "gs://lab-bucket/work", "spot": True, "labels": {}, "maxvCpus": 16, "environment": [],
                                     "nextflowConfig": "", "preRunScript": "", "postRunScript": ""},
                                 agent="a1", facts=box.facts(), roots=[], run_name="run-a", pipeline="nf-core/rnaseq", revision="3.14.0",
                                 samplesheet=[["sample", "fastq_1"], ["s1", "gs://lab-bucket/x"]], params={})
    assert set(b) == set(g) - {"account"} if "account" in g else set(b) == set(g)
    assert set(b["files"]) == {"samplesheet.csv", "params.yaml", "nextflow.config", "aws.config", "head.sh"}
    assert set(b["ce"]) == {"name", "platform", "region", "workDir", "jobQueue", "spot", "maxvCpus", "environment", "nextflowConfig"}
    blob = json.dumps(b)
    assert str(box.cred) not in blob and MARKER not in blob and AKID not in blob


def test_aws_config_has_exactly_the_documented_keys(box):
    # TC-039, TC-040, TC-041, TC-148
    text = box.bundle("r1")["files"]["aws.config"]
    assert config_keys(text) == {"process.executor": "'awsbatch'", "process.queue": "'lab-queue'", "aws.region": "'eu-west-1'",
                                 "workDir": "'%s/runs/r1/work'" % WORK, "process.resourceLimits": "[cpus: 16]"}
    for word in ("aws.batch.", "accessKey", "secretKey", "aws.profile", "cliPath", "platformType", "jobRole", "executionRole", "volumes",
                 "maxSpotAttempts", "fusion", "wave"):
        assert word.lower() not in text.lower(), word
    bare = config_keys(box.bundle("r1", ce=ace(maxvCpus=None))["files"]["aws.config"])
    assert set(bare) == {"process.executor", "process.queue", "aws.region", "workDir"}
    nf = box.bundle("r1")["files"]["nextflow.config"]
    assert "aws.batch" not in nf and "fusion" not in nf.lower()


def test_spot_is_a_note_only_and_the_screen_says_aws_decides(box):
    # TC-042, TC-071
    from abf_launch import build
    a, b = box.bundle(ce=ace(spot=True)), box.bundle(ce=ace(spot=False))
    assert a["files"]["aws.config"] == b["files"]["aws.config"] and "spot" not in a["files"]["aws.config"].lower()
    screen = "\n".join(build.launch_screen(a, "aws1"))
    assert "是否 Spot 由 AWS 的 job queue 決定，這個欄位只是備註" in screen


def test_the_users_nextflow_config_stays_in_its_own_file_and_aws_config_wins(box):
    # TC-043
    from abf_station import launch
    b = box.bundle()
    nf = b["files"]["nextflow.config"]
    assert nf.startswith("// the user's own text\nprocess.cpus = 2\n") and nf.endswith(launch.OVERWRITE_BLOCK)
    assert "user's own text" not in b["files"]["aws.config"] and "report.overwrite" not in b["files"]["aws.config"]
    assert "-c nextflow.config -c aws.config" in b["files"]["head.sh"].splitlines()[-1]


def test_outdir_and_work_are_per_run_s3_prefixes(box):
    # TC-044, TC-045, TC-046
    from test_launch_bundle import parse_yaml
    b = box.bundle("r1")
    y = parse_yaml(b["files"]["params.yaml"])
    assert y["outdir"] == "%s/runs/r1/results" % WORK
    assert y["input"] == "%s/samplesheet.csv" % b["run_folder"] and y["genome"] == "GRCh38"
    assert config_keys(b["files"]["aws.config"])["workDir"] == "'%s/runs/r1/work'" % WORK
    assert config_keys(box.bundle("r2")["files"]["aws.config"])["workDir"] == "'%s/runs/r2/work'" % WORK
    assert parse_yaml(box.bundle("r2")["files"]["params.yaml"])["outdir"] == "%s/runs/r2/results" % WORK


def test_samplesheet_paths_must_be_s3_urls_of_the_work_bucket(box):
    # TC-047 .. TC-056
    from abf_station import launch
    box.bundle()
    for cell in ("/home/x.fastq.gz", "gs://lab-bucket/x", "https://lab-bucket/x", "s3://other/x", "s3://lab-bucket/../x",
                 "s3://lab-bucket/a b"):
        sheet = [["sample", "fastq_1", "strandedness"], ["s1", cell, "auto"]]
        with pytest.raises(launch.BundleError) as e:
            box.bundle(samplesheet=sheet)
        assert "aws s3" in str(e.value) and "之後" in str(e.value) and "自己放" in str(e.value), cell
    for cell in ("s3://lab-bucket/a\x07b", "s3://lab-bucket/a‮b"):      # a control character is refused too (by the shared rule)
        with pytest.raises(launch.BundleError):
            box.bundle(samplesheet=[["sample", "fastq_1", "strandedness"], ["s1", cell, "auto"]])
    box.bundle(samplesheet=[["sample", "fastq_1", "strandedness"], ["s1", "s3://lab-bucket/x.fastq.gz", "not-a-path/at-all"]])


@pytest.mark.parametrize("field,value", [("jobQueue", "q'\nprocess.executor = 'local"), ("region", "eu-west-1'\nx = 1"),
                                         ("workDir", "s3://lab-bucket/work'\nx = 1"),
                                         ("environment", [{"name": "X", "value": "v'\nz = 1\n}", "head": True}])])
def test_a_hostile_value_cannot_break_out_of_the_config_text(box, field, value):
    # TC-057
    from abf_station import launch
    try:
        b = box.bundle(ce=ace(**{field: value}))
    except launch.BundleError:
        return
    assert set(config_keys(b["files"]["aws.config"])) <= {"process.executor", "process.queue", "aws.region", "workDir",
                                                           "process.resourceLimits"}


def test_aws_bundle_is_identical_when_built_twice_from_the_same_inputs(box):
    # TC-058
    from abf_station import launch
    a = box.bundle()
    b = launch.render_aws_bundle(ce=copy.deepcopy(a["ce"]), agent="a1", facts=launch.own_facts(box.ctx), roots=[], run_name="run-a",
                                 pipeline="nf-core/rnaseq", revision="3.14.0", samplesheet=copy.deepcopy(SHEET),
                                 params={"genome": "GRCh38"}, path_columns=None)
    assert a == b


def test_head_script_is_the_one_that_is_shown_and_run(box):
    # TC-060, TC-062, TC-063, TC-064, TC-065
    from abf_launch import build
    b, _ = launch_ok(box)
    shown = "\n".join(build.launch_screen(b, "aws1"))
    script = b["files"]["head.sh"]
    folder = box.folder()
    assert (folder / "head.sh").read_text() == script and box.started[0]["script"] == script
    head = script.splitlines()
    assert head[0] == "#!/bin/bash"
    assert head[1] == ("# credentials: the agent sets AWS_SHARED_CREDENTIALS_FILE from its own credentials file; the path is not part of this script")
    assert head[2] == "umask 077" and head[3].startswith("cd ") and head[3].endswith("|| exit 1") and str(folder) in head[3]
    assert 'export TOWER_ACCESS_TOKEN="$(cat tower.token)"' in head and TOKEN not in script
    assert head[-1] == ("exec nextflow run nf-core/rnaseq -r 3.14.0 -name run-a -params-file params.yaml -c nextflow.config "
                        "-c aws.config -with-tower http://127.0.0.1:8123")
    assert str(box.cred) not in script and "sbatch" not in script and "#SBATCH" not in script
    assert not [ln for ln in head if "AWS_SHARED_CREDENTIALS_FILE=" in ln]
    for name in ("params.yaml", "nextflow.config", "aws.config", "head.sh"):
        for ln in b["files"][name].splitlines():
            assert ln in shown, (name, ln)
        assert (folder / name).read_text() == b["files"][name]
    for ln in ("s1,s3://lab-bucket/x.fastq.gz,auto", "sample,fastq_1,strandedness"):
        assert ln in shown
    assert (folder / "samplesheet.csv").read_text() == b["files"]["samplesheet.csv"]


def test_head_environment_variables_are_exported_and_compute_ones_are_not(box):
    # TC-061, TC-098
    env = [{"name": "HEAD_ONLY", "value": "h1", "head": True, "compute": False},
           {"name": "COMPUTE_ONLY", "value": "c1", "head": False, "compute": True}]
    b, _ = launch_ok(box, ce=ace(environment=env))
    assert "export HEAD_ONLY=h1" in b["files"]["head.sh"] and "COMPUTE_ONLY" not in b["files"]["head.sh"]
    assert box.started[0]["env"]["HEAD_ONLY"] == "h1" and "COMPUTE_ONLY" not in box.started[0]["env"]
    assert "-Dhttp.nonProxyHosts=" in b["files"]["head.sh"]      # the receiver is on the loopback address
    from abf_station import launch
    for name in ("AWS_SHARED_CREDENTIALS_FILE", "AWS_ACCESS_KEY_ID", "TOWER_ACCESS_TOKEN", "ABF_X"):
        with pytest.raises(launch.BundleError):
            box.bundle(ce=ace(environment=[{"name": name, "value": "v", "head": True, "compute": False}]))


def test_every_aws_prefixed_environment_name_is_refused(box):
    # TC-020, TC-021, TC-022, TC-023, TC-024, TC-025, TC-026, TC-027, TC-028, TC-029, TC-033, TC-055
    from abf_station import launch
    for name in ("AWS_MAX_ATTEMPTS", "AWS_RETRY_MODE", "AWS_CA_BUNDLE", "AWS_REGION", "aws_profile", "Aws_Whatever", "AWS_"):
        with pytest.raises(launch.BundleError):
            box.bundle(ce=ace(environment=[{"name": name, "value": "v", "head": True, "compute": False}]))
    for name in ("HEAD_ONLY", "MY_AWS_NOTE", "AWSX"):
        box.bundle(ce=ace(environment=[{"name": name, "value": "v", "head": True, "compute": False}]))
    msgs = []
    for name in ("AWS_MAX_ATTEMPTS", "AWS_ACCESS_KEY_ID"):
        with pytest.raises(launch.BundleError) as e:
            box.bundle(ce=ace(environment=[{"name": name, "value": "value-marker-123", "head": True, "compute": False}]))
        assert name in str(e.value) and "value-marker-123" not in str(e.value)
        msgs.append(str(e.value).replace(name, "X"))
    assert msgs[0] == msgs[1]      # same existing sentence


def test_aws_forbidden_env_tuple_is_still_refused_by_name(box):
    # TC-030
    from abf_station import launch
    assert len(launch.AWS_FORBIDDEN_ENV) == 8
    for name in launch.AWS_FORBIDDEN_ENV:
        with pytest.raises(launch.BundleError):
            box.bundle(ce=ace(environment=[{"name": name, "value": "v", "head": True, "compute": False}]))


def test_fetch_run_records_does_not_list_aws_config_as_a_record():
    # TC-066
    from abf_station import fetch
    assert "aws.config" in fetch._NOT_RECORDS


# ======================================================================================================================
# US3 - the screens
# ======================================================================================================================

def test_the_screen_says_aws_bills_the_lab_in_its_first_paragraph(box):
    # TC-067, TC-068, TC-069, TC-070, TC-072, TC-073, TC-074, TC-078, TC-187
    from abf_launch import build
    b = box.bundle("r1")
    lines = build.launch_screen(b, "aws1")
    assert lines[0].endswith("送出確認：下面就是會被送出的全部內容 ==")
    assert lines[1] == BILLING
    text = "\n".join(lines)
    assert not re.search(r"NT\$|USD|US\$|TWD|[$＄￥¥€£]\s?[0-9]|[0-9]\s?(元|美元|台幣)", text)
    for label in ("管線", "版本", "環境", "代理", "run 名稱", "專屬資料夾（本機）", "AWS 區域", "job queue", "工作目錄", "結果位置", "Spot 備註",
                  "單一 task 的 cpus 上限"):
        assert re.search(r"^\| %s" % re.escape(label), text, re.M), label
    for needle in (WORK + "/runs/r1/work", WORK + "/runs/r1/results"):
        assert needle in text
    for title in ("samplesheet.csv", "params.yaml", "nextflow.config", "aws.config", "head.sh"):
        assert "== %s" % title in text, title
    plain = "\n".join(build.launch_screen(box.bundle(ce=ace(maxvCpus=None)), "aws1"))
    assert "單一 task 的 cpus 上限" not in plain
    top = text[:text.index("== head.sh")]      # the head script itself has a comment line that names the credentials file
    assert "費用預估" in text and not re.search(r"credential|金鑰檔|憑證檔", top, re.I)      # TC-078, TC-187: only the fixed sentence, nothing to type in


def test_the_cancel_screen_says_pid_and_warns_about_leftover_jobs(box):
    # TC-075, TC-076
    from abf_launch import build
    text = "\n".join(build.cancel_screen(cancel_bundle(box), {"cancel_requested_at": None}))
    assert "主控程序編號（pid）: %d" % PID in text and "Slurm" not in text
    assert "AWS Console" in text and "Batch" in text and "計費" in text


def test_the_terminal_words_follow_the_environment_type(ip, box, monkeypatch, capsys):
    # TC-077
    import argparse
    from abf_launch import cli, terminal
    row = {"slurm_job_id": PID, "run_name": "run-a", "run_folder": "/x/run-a"}
    assert cli._submitted_line(row, AWS) == "已啟動：主控程序編號（pid）4242；run 名稱 run-a；專屬資料夾 /x/run-a。"
    assert cli._submitted_line(row) == "已送出：Slurm 工作編號 4242；run 名稱 run-a；專屬資料夾 /x/run-a。"
    launch_through_platform(ip, box)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(ip.index))
    monkeypatch.setattr(terminal, "terminal_problem", lambda: None)
    monkeypatch.setattr(terminal, "ask", lambda lines, q: True)
    box.cancel_world("run-p")

    async def done(state, job_id, **kw):
        from abf_platform import jobs
        job = jobs.claim(ip.state_db, "a1", time.time, tokens_path=ip.tokens)
        st, res = box.handle(job)
        jobs.take_result(ip.state_db, "a1", job["id"], st, res, time.time, tokens_path=ip.tokens)
        return {"state": st, "ok": res.get("ok"), "result": res, "message": res.get("message")}
    from abf_platform import jobs
    monkeypatch.setattr(jobs, "wait_for_result", done)
    assert cli.cmd_cancel(argparse.Namespace(run="run-p")) == 0
    out = capsys.readouterr().out
    assert "主控程序" in out and "Slurm 工作" not in out and "AWS Console" in out


def test_no_launch_flag_takes_a_credential(box):
    # TC-187, TC-188: the person names the environment only; the checks of java, nextflow and aws are the agent's
    import inspect
    from abf_launch import build, cli
    assert not [p for p in inspect.signature(build.prepare_launch).parameters if re.search(r"cred|key|secret|token", p, re.I)]
    src = (PLATFORM_DIR / "abf_launch" / "cli.py").read_text(encoding="utf-8")
    assert not re.search(r"add_argument\(\s*[\"']--(cred|key|secret|access)", src)
    for f in (PLATFORM_DIR / "abf_launch").glob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"""["'](java|nextflow|aws)["']\s*,\s*["']--?version""", text), f.name


# ======================================================================================================================
# US4 - cancel
# ======================================================================================================================

def test_cancel_sends_one_sigterm_to_exactly_the_verified_process(box):
    # TC-079, TC-080
    launch_ok(box)
    box.cancel_world()
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "done" and res["ok"] is True and res["slurm_job_id"] == PID and res["run_name"] == "run-a"
    assert box.kills == [(PID, signal.SIGTERM)]
    assert res["message"] == ("取消請求已送出（主控程序 pid %d）；請到 AWS Console 的 Batch 頁確認 job 都已結束，沒取消乾淨的工作仍會計費" % PID)


def test_cancel_refuses_and_sends_nothing_when_the_process_is_gone_the_owner_differs_the_name_differs_or_the_cwd_differs(box):
    # TC-081, TC-082, TC-083, TC-084, TC-085
    launch_ok(box)
    box.cancel_world()
    box.ps = (1, "")
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "refused" and "已結束" in res["message"]
    box.cancel_world()
    box.ps = (0, "tester a\ntester b\n")
    assert box.handle(cancel_job(cancel_bundle(box)))[0] == "refused"
    box.cancel_world(owner="someone-else")
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "refused" and "不是你的" in res["message"]
    box.cancel_world(args="/usr/bin/java nextflow.cli.Launcher run x -name run-zzz -with-tower u")
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "refused" and "-name run-a" in res["message"]
    box.cancel_world(cwd="/somewhere/else")
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "refused" and "資料夾" in res["message"]
    assert box.kills == []


def test_cancel_refuses_when_head_pid_does_not_match_the_bundle(box):
    # TC-086
    launch_ok(box)
    box.cancel_world(pid=9999)
    state, res = box.handle(cancel_job(cancel_bundle(box, number=9999)))
    assert state == "refused" and box.kills == []
    (box.folder() / "head.pid").unlink()
    box.cancel_world()
    assert box.handle(cancel_job(cancel_bundle(box)))[0] == "refused" and box.kills == []


def test_cancel_of_an_aws_run_in_a_gcb_runs_folder_is_refused(box):
    # TC-087, TC-088
    launch_ok(box)
    box.cancel_world()
    other = box.storage / "_gcb_runs" / "run-a"
    state, res = box.handle(cancel_job(cancel_bundle(box, run_folder=str(other))))
    assert state == "refused" and box.kills == []
    # TC-088: the folder of the run does not exist
    state, res = box.handle(cancel_job(cancel_bundle(box, "run-missing")))
    assert state == "refused" and box.kills == [] and res["message"]


def test_cancel_refuses_an_unconfirmed_or_reused_confirmation(box):
    # TC-089
    launch_ok(box)
    box.cancel_world()
    b = cancel_bundle(box)
    good = cancel_job(b)
    for job in (dict(good, args={"bundle": b, "bundle_sha256": good["args"]["bundle_sha256"]}),
                {k: v for k, v in good.items() if k != "confirmation"},
                dict(good, confirmation=dict(good["confirmation"], kind="launch")),
                dict(good, confirmation=dict(good["confirmation"], sha256="0" * 64)),
                dict(good, confirmation=dict(good["confirmation"], used_at=1.0))):
        assert box.handle(job)[0] == "refused"
    assert box.kills == []
    assert box.handle(good)[0] == "done" and len(box.kills) == 1
    assert box.handle(good)[0] == "refused" and len(box.kills) == 1


def test_cancel_needs_no_available_status(ip, box):
    # TC-090
    from abf_platform import jobs
    launch_through_platform(ip, box)
    for status in ("invalid", "creating"):
        set_status(ip, "aws1", status, ok=0)
        jobs.check_target(ip.state_db, "aws1", "cancel_run")
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(ip.state_db, "aws1", "launch_nextflow")


def test_gcb_cancel_after_the_refactor_is_byte_identical(box):
    # TC-139: the digests were taken on the base commit of this task, for fixed inputs
    from abf_launch import build
    from abf_station import gcb_launch, launch
    from test_gcb_launch import gce
    facts = {"slurm_account": None, "reach": "local", "platform_local": True, "endpoint": "http://127.0.0.1:8123", "forward_file": None,
             "storage_root": "/srv/abf-storage", "way_back": None, "platform_public_url": None}
    gsheet = [["sample", "fastq_1", "strandedness"], ["s1", "gs://lab-bucket/x.fastq.gz", "auto"]]
    b = launch.render_gcb_bundle(ce=gce(), agent="a1", facts=facts, roots=[], run_name="run-a", pipeline="nf-core/rnaseq",
                                 revision="3.14.0", samplesheet=gsheet, params={"genome": "GRCh38"})
    cb = {"version": 1, "run_name": "run-a", "slurm_job_id": 4242, "run_folder": "/srv/abf-storage/_gcb_runs/run-a", "agent": "a1", "ce": gce()}
    h = lambda s: hashlib.sha256(s.encode()).hexdigest()
    assert h(json.dumps(b, sort_keys=True)) == "0ea991ec2798537e9c795ee03220cedde089ce4d6daf1d953c2b048ef8f7be2c"
    assert h("\n".join(build.launch_screen(b, "gcb1"))) == "cdb912841e13dd568700d64de29877667f0c1b7c3dceafd75623780bfecf9539"
    assert h("\n".join(build.cancel_screen(cb, {"cancel_requested_at": None}))) == \
        "2493a23f2d0eb06e2e093a2ef731a8316bfefb6b292b961026736f9af62a5ef9"
    assert gcb_launch.GCB_CANCEL_REMINDER.startswith("取消請求已送出（主控程序 pid %d）")


# ======================================================================================================================
# US5 - the credentials stay on the host
# ======================================================================================================================

def test_the_credentials_path_is_only_in_the_process_environment(box, monkeypatch):
    # TC-091, TC-092, TC-093, TC-094, TC-095, TC-096, TC-097
    for k, v in (("ABF_PLATFORM_SECRET_THING", "x"), ("ABF_STATION_OTHER", "y"), ("AWS_ACCESS_KEY_ID", "k"), ("AWS_SECRET_ACCESS_KEY", "s"),
                 ("AWS_SESSION_TOKEN", "t"), ("TOWER_ACCESS_TOKEN", "from-the-agent"), ("AWS_DEFAULT_PROFILE", "other"),
                 ("AWS_SHARED_CREDENTIALS_FILE", "/somewhere/else")):
        monkeypatch.setenv(k, v)
    b, res = launch_ok(box)
    s = box.started[0]
    cred = str(box.cred)
    env = s["env"]
    assert env["AWS_SHARED_CREDENTIALS_FILE"] == cred and env["AWS_PROFILE"] == "default" and env["AWS_CONFIG_FILE"] == os.devnull
    assert env["AWS_DEFAULT_REGION"] == REGION
    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "TOWER_ACCESS_TOKEN", "AWS_DEFAULT_PROFILE"):
        assert k not in env, k
    assert not [k for k in env if k.upper().startswith("ABF_")]
    assert cred not in " ".join(s["argv"]) and cred not in s["cwd"] and cred not in b["files"]["head.sh"] and cred not in json.dumps(b)
    assert cred not in json.dumps(res) and cred not in (box.folder() / "head.sh").read_text()


def test_no_marker_of_the_credentials_file_reaches_a_result_a_message_or_the_database(ip, box):
    # TC-059, TC-099
    launch_through_platform(ip, box)
    results = []
    box.exit_code = 2
    box.out_text = "failed\n" + MARKER + "\n"
    results.append(box.handle(job_of(box.bundle("run-x")))[1])
    box.cred.unlink()
    results.append(box.handle(job_of(box.bundle("run-y")))[1])
    results.append(box.handle(job_of(box.bundle("run-z")))[1])
    blob = json.dumps(results)
    assert MARKER not in blob and AKID not in blob and str(box.cred) not in blob
    raw = Path(str(ip.state_db)).read_bytes()
    assert MARKER.encode() not in raw and AKID.encode() not in raw and str(box.cred).encode() not in raw


def test_a_missing_open_or_malformed_credentials_file_stops_the_launch_before_anything_is_written(box):
    # TC-033, TC-100, TC-101, TC-102
    box.cred.unlink()
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "憑證檔" in res["message"]
    nothing_happened(box)
    if sys.platform != "win32":
        box.cred.write_text(CRED_FILE)
        box.cred.chmod(0o644)
        state, res = box.handle(job_of(box.bundle()))
        assert state == "refused"
        nothing_happened(box)
    box.cred.write_text("[default]\naws_access_key_id = " + AKID + "\n")
    if sys.platform != "win32":
        box.cred.chmod(0o600)
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and AKID not in json.dumps(res)
    nothing_happened(box)


def test_the_credential_and_preflight_checks_run_again_before_the_first_file_is_written(box, monkeypatch):
    # TC-103
    from abf_station import aws_preflight
    seen = []
    real = aws_preflight.run_preflight

    def spy(env, cred_path=None, **kw):
        seen.append(os.path.exists(str(box.storage / "_aws_runs")))
        return real(env, cred_path=cred_path, **kw)
    monkeypatch.setattr(aws_preflight, "run_preflight", spy)
    launch_ok(box)
    assert seen == [False]


# ======================================================================================================================
# US6 - what the platform lets through
# ======================================================================================================================

def available_aws(ip, name="aws1"):
    register_agent(ip)
    create(ip, name)
    set_status(ip, name, "available")


def test_aws_environment_accepts_exactly_preflight_launch_cancel_and_pipeline_files(ip):
    # TC-104, TC-105, TC-106, TC-107, TC-108
    from abf_platform import jobs
    available_aws(ip)
    before = jobs_count(ip)
    for kind in ("launch_nextflow", "cancel_run", "preflight", "pipeline_files", "put_upload", "clean_work"):      # aws-upload: put_upload; aws-clean: clean_work
        jobs.check_target(ip.state_db, "aws1", kind)
    for kind in ("list_site_files", "fetch_run_records", "read_task_log"):
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(ip.state_db, "aws1", kind)
        m = str(e.value)
        assert "尚未支援" in m and "AWS Batch" in m and "Google Batch" not in m and "set an agent" not in m, (kind, m)
        assert "aws-clean" not in m and "aws-upload" not in m          # TC-108 (aws-clean: the generic sentence, same shape as Google's)
    assert jobs_count(ip) == before


def test_google_batch_still_accepts_its_six_kinds_and_nothing_else(ip):
    # TC-109, TC-110
    from abf_platform import jobs
    from test_gcb_ce import create as gcreate
    register_agent(ip)
    gcreate(ip)
    set_status(ip, "gcb1", "available")
    for kind in ("preflight", "launch_nextflow", "cancel_run", "pipeline_files", "clean_work", "put_upload"):
        jobs.check_target(ip.state_db, "gcb1", kind)
    for kind in ("list_site_files", "fetch_run_records", "read_task_log"):
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(ip.state_db, "gcb1", kind)
        assert "尚未支援" in str(e.value) and "Google Batch" in str(e.value)


def test_cloud_store_stays_google_only():
    # TC-111, TC-112 (changed by aws-upload: Google is unchanged, AWS now knows s3://; the name is kept so the history stays findable)
    from abf_platform import cloud_store
    ce = {"platform": AWS, "config": {"workDir": "s3://lab-bucket/work"}}
    assert cloud_store.workdir_bucket(ce) == "lab-bucket"
    assert cloud_store.upload_prefix(ce, "run-a", "s3") == "s3://lab-bucket/uploads/run-a/"
    with pytest.raises(cloud_store.CloudPathError):
        cloud_store.workdir_bucket({"platform": "slurm-platform", "config": {"workDir": "s3://lab-bucket/work"}})
    gce = {"platform": "googlebatch-platform", "config": {"workDir": "gs://lab-bucket/work"}}
    assert cloud_store.upload_prefix(gce, "run-a") == "gs://lab-bucket/uploads/run-a/"


def test_a_dataset_destination_cannot_be_an_aws_environment(ip):
    # TC-113
    from abf_platform import cloud_store
    from abf_launch import build
    available_aws(ip)
    for name in ("workdir_bucket", "upload_prefix"):
        assert hasattr(cloud_store, name)
    # changed by aws-upload: an AWS environment may now be a dataset destination, so put_upload is no longer a refused kind
    assert build.target_problem(ip.state_db, "aws1", "put_upload") is None


def test_put_upload_and_clean_work_are_taken_and_the_agent_no_longer_says_unsupported(ip, box):
    # TC-114, TC-115, TC-147
    from abf_platform import jobs
    from abf_station import clean, rules
    available_aws(ip)
    n = jobs_count(ip)
    for kind in ("put_upload", "clean_work"):      # changed by aws-upload (put_upload) and aws-clean (clean_work): both are taken now
        jobs.check_target(ip.state_db, "aws1", kind)
    with pytest.raises(jobs.JobRefused):
        jobs.enqueue_listing(ip.state_db, "aws1", "/x")
    assert jobs_count(ip) == n
    with pytest.raises(rules.Refusal) as e:
        cb = {"version": 1, "run_name": "run-a", "slurm_job_id": PID, "run_folder": str(box.folder()), "agent": "a1", "ce": ace(),
              "work": WORK + "/runs/run-a/work"}
        clean.run_clean(job_of(cb, kind="clean_work", conf_kind="clean_work"), box.ctx)
    assert "尚未支援" not in str(e.value)      # aws-clean: it is built; this bundle stops at the missing head.pid, before any program
    assert box.runs == []      # TC-147: no program (and so no aws or S3 command) was run


def test_platform_host_types_has_two_entries_and_nothing_indexes_it_by_position():
    # TC-116, TC-117, TC-118, TC-130
    from abf_platform import compute_envs
    from abf_station import launch
    assert compute_envs.PLATFORM_HOST_TYPES == (GCB, AWS, "azbatch-platform", "k8s-platform") and compute_envs.CHECK_ONLY_TYPES == ()      # k8s-launch
    assert compute_envs.CHECKABLE == (compute_envs.SUPPORTED, GCB, AWS, "azbatch-platform", "k8s-platform")
    assert launch.GCB == "googlebatch-platform" and launch.AWS == "awsbatch-platform"
    for folder in ("abf_platform", "abf_station", "abf_launch"):
        for f in (PLATFORM_DIR / folder).rglob("*.py"):
            assert "PLATFORM_HOST_TYPES[" not in f.read_text(encoding="utf-8"), f.name
    line = [ln for ln in (PLATFORM_DIR / "abf_platform" / "compute_envs.py").read_text(encoding="utf-8").splitlines()
            if ln.startswith("CHECK_ONLY_TYPES")][0]
    assert "新雲端類型先放這裡，只開預檢" in line


def test_check_dispatch_sends_each_type_to_its_own_check():
    # TC-119, TC-120, TC-121
    from abf_platform import compute_envs
    from test_aws_ce import fields
    compute_envs.clean(fields())
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.clean(fields(platform=GCB))
    assert "project" in str(e.value)
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.clean(fields(config={"workDir": BUCKET_URL, "jobQueue": QUEUE}))
    assert "region" in str(e.value) and "project" not in str(e.value)


def test_snapshot_of_an_aws_environment_has_no_credential_content(ip):
    # TC-122, TC-123, TC-124
    from abf_platform import compute_envs
    register_agent(ip)
    create(ip, config=good_config(spot=True, maxvCpus=16))
    snap = compute_envs.snapshot(compute_envs.get(ip.state_db, "aws1"))
    assert set(snap) == {"name", "platform", "credentialsId", "region", "workDir", "jobQueue", "spot", "maxvCpus"}
    blob = json.dumps(snap)
    assert AKID not in blob and MARKER not in blob and "BEGIN" not in blob
    # TC-124: the snapshot of a Google Batch environment keeps the keys it had
    from test_gcb_ce import create as gcreate
    gcreate(ip)
    g = compute_envs.snapshot(compute_envs.get(ip.state_db, "gcb1"))
    assert set(g) >= {"name", "platform", "project", "location", "workDir"} and "region" not in g


def test_primary_environment_never_auto_picks_aws_and_naming_it_works(ip, box):
    # TC-126, TC-127
    from abf_launch import build
    register_with_facts(ip, box)
    create(ip)
    set_status(ip, "aws1", "available")
    assert build.primary_environment(ip.state_db) is None
    assert ip.run("ce", "primary", "aws1")[0] == 0
    assert build.primary_environment(ip.state_db) is None
    with pytest.raises(build.Refusal):
        build.prepare_launch(ip.state_db, pipeline="nf-core/rnaseq", revision="3.14.0", run_name="run-p",
                             samplesheet=str(sheet_file(box.tmp)), params={})
    name, bundle = prepare(ip, box)
    assert name == "aws1" and bundle["ce"]["platform"] == AWS


def test_another_users_aws_environment_and_run_are_not_found_for_launch_and_cancel(ip, box):
    # TC-128, TC-129
    from abf_launch import build
    launch_through_platform(ip, box)
    con = sqlite3.connect(str(ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET owner_user_id = 1")
        con.execute("UPDATE agents SET owner_user_id = 1")
        con.execute("UPDATE launches SET user_id = 1 WHERE run_name = 'run-p'")
    con.close()
    n = jobs_count(ip)
    with pytest.raises(build.Refusal) as e:
        prepare(ip, box, "run-q", owner=2)
    assert "not found" in str(e.value)
    with pytest.raises(build.Refusal):
        build.prepare_cancel(ip.state_db, "run-p", owner=2)
    assert jobs_count(ip) == n
    assert build.prepare_cancel(ip.state_db, "run-p", owner=1)[0] == "aws1"


# ======================================================================================================================
# US7 - out of scope, and no step back
# ======================================================================================================================

def test_resume_and_relaunch_of_an_aws_run_are_refused_in_plain_words(ip, box):
    # TC-131, TC-132, TC-133
    from abf_launch import build
    launch_through_platform(ip, box)
    for fn in (build.prepare_resume, build.prepare_relaunch):
        with pytest.raises(build.Refusal) as e:
            fn(ip.state_db, "run-p", index_path=str(ip.index))
        assert "AWS Batch 的 run 還不能續跑或原樣重跑（尚未支援）" in str(e.value)
    origin = box.bundle("run-p")
    resume = {"version": 1, "agent": "a1", "ce": origin["ce"], "run_name": "run-p-a2", "run_folder": origin["run_folder"],
              "files": {"head-2.sh": "x\n"},
              "resume": {"of_run": "run-p", "of_slurm_job_id": PID, "session_id": "12345678-1234-1234-1234-123456789abc", "attempt": 2,
                         "origin": origin}}
    started = len(box.started)
    state, res = box.handle(job_of(resume))
    assert state == "refused" and "尚未支援" in res["message"] and len(box.started) == started


def test_a_plain_slurm_bundle_with_its_platform_changed_to_aws_is_not_launched_as_aws(box):
    # TC-140
    from abf_station import launch
    from test_launch_bundle import render
    b = copy.deepcopy(render())
    b["ce"]["platform"] = AWS
    state, res = box.handle(job_of(b))
    assert state == "refused" and box.started == []
    assert launch.AWS == AWS


def test_the_slurm_and_gcb_screens_and_bundles_are_byte_identical_to_before():
    # TC-134, TC-135, TC-138
    from abf_launch import build
    from test_launch_bundle import render
    b = render()
    h = lambda s: hashlib.sha256(s.encode()).hexdigest()
    assert h(json.dumps(b, sort_keys=True)) == "fcad3c22998c75125598565bcbb5ce5382a17f94fbca164d5aec62e6c39cc478"
    assert h("\n".join(build.launch_screen(b, "lab-a"))) == "020a51155f38740c5471798cb642ad1dac266b4aac2ecabb9dba56ba855cd0d4"
    assert h(b["files"]["head.sh"]) == "6432aa66c73d0f515d4475f42f93b6edf1fb4afbe5cd6c3cf2caf1f1ad5d5477"
    from abf_launch import cli
    row = {"slurm_job_id": PID, "run_name": "run-a", "run_folder": "/x/run-a"}
    assert cli._submitted_line(row) == "已送出：Slurm 工作編號 4242；run 名稱 run-a；專屬資料夾 /x/run-a。"
    assert cli._submitted_line(row, GCB) == "已啟動：主控程序編號（pid）4242；run 名稱 run-a；專屬資料夾 /x/run-a。"


def test_cost_estimates_and_the_other_reads_are_not_built_for_aws():
    # TC-143, TC-153
    text = "\n".join((PLATFORM_DIR / "abf_platform" / f).read_text(encoding="utf-8") for f in ("cloud_cost.py",))
    assert not re.search(r"awsbatch|\baws\b|s3://", text, re.I)
    for f in ("PRICES.json", "cloud_prices.json"):
        p = PLATFORM_DIR / "abf_platform" / f
        if p.exists():
            assert "aws" not in p.read_text(encoding="utf-8").lower()


def test_no_new_write_path_for_aws():
    # TC-144, TC-145, TC-146
    for folder in ("abf_station", "abf_platform", "abf_launch"):
        for f in (PLATFORM_DIR / folder).rglob("*.py"):
            code = "\n".join(ln for ln in f.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#"))
            assert not re.search(r"aws s3 cp|aws s3 rm|aws s3 sync|terminate-job|cancel-job|delete-job-queue", code.replace("\\\n", "")), f.name
    code = (PLATFORM_DIR / "abf_station" / "aws_launch.py").read_text(encoding="utf-8")
    assert re.findall(r'\["aws", "[^"]+"', code) == ['["aws", "--version"']


def test_tool_list_unchanged_and_no_new_web_route(tmp_path):
    # TC-150, TC-185
    from abf_platform import web
    from abf_platform.mcp_server import build_server
    names = {t.name for t in asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())}
    assert len(names) == 21 and names == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files",
                                          "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation", "launch", "cancel", "resume", "relaunch", "forget"}
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"aws|batch|s3", getattr(r, "path", ""), re.I) and r.path not in {"/upload", "/upload/{batch}"}]      # web-upload-page: only the two routes this task registered are exempt (ruling 25)


def test_no_migration_is_needed_for_aws_launch(ip):
    # TC-151
    register_agent(ip)
    create(ip)
    con = sqlite3.connect(str(ip.state_db))
    cols = {t: [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)] for t in ("launches", "jobs", "compute_envs")}
    con.close()
    assert cols["launches"] == ["id", "run_name", "slurm_job_id", "run_folder", "ce", "agent", "confirmed_at", "submitted_at",
                                "cancel_requested_at", "job_id", "user_id", "parent_run", "attempt", "attempt_kind", "work_cleaned_at"]
    assert cols["jobs"] == ["id", "agent", "compute_env", "kind", "args_json", "state", "result_json", "late_result_json", "created_at",
                            "deadline_at", "claimed_at", "finished_at", "forgotten_at", "forgotten_by", "confirmation_id"]
    assert cols["compute_envs"] == ["id", "name", "description", "platform", "credentials_id", "agent", "status", "message", "is_primary",
                                    "checked_ok", "config_json", "created_at", "updated_at", "last_used_at", "owner_user_id"]


def test_no_cloud_library_is_imported_and_no_new_dependency():
    # TC-149
    toml = (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert "boto3" not in toml and "botocore" not in toml
    for f in list((PLATFORM_DIR / "abf_platform").rglob("*.py")) + list((PLATFORM_DIR / "abf_station").rglob("*.py")) + list(
            (PLATFORM_DIR / "abf_launch").rglob("*.py")):
        assert not re.search(r"^\s*(import|from)\s+(boto3|botocore|google|azure)\b", f.read_text(encoding="utf-8"), re.M), f.name


# ======================================================================================================================
# Constitution and safety net
# ======================================================================================================================

def test_the_launch_allow_list_still_has_one_entry():
    # TC-179, TC-180
    text = (REPO_ROOT / "tests" / "no_second_run_state_test.sh").read_text(encoding="utf-8")
    block = re.search(r'LAUNCH_ALLOW="\n(.*?)\n"', text, re.S).group(1)
    entries = [ln for ln in block.splitlines() if ln.strip()]
    assert len(entries) == 1 and entries[0].startswith(
        "platform/abf_station/launch.py|platform/tests/test_station_launch.py::test_unconfirmed_launch_is_refused|")


def test_the_platform_package_starts_no_program_and_holds_no_submission_word():
    # TC-181
    forbidden_everywhere = re.compile(r"\bnohup\b|\bsetsid\b")
    starts = re.compile(r"\bsubprocess\b|\bPopen\b|\bos\.system\b")
    submit = re.compile(r"nextflow\s+run|\bsbatch\b")
    for folder in (PLATFORM_DIR / "abf_platform", PLATFORM_DIR / "abf_station"):
        for f in folder.rglob("*.py"):
            text = "\n".join(ln for ln in f.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#"))
            assert not forbidden_everywhere.search(text), f.name
            if f.name != "site.py":
                assert not starts.search(text), f.name
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        assert not submit.search("\n".join(ln for ln in f.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#"))), f.name
    al = (PLATFORM_DIR / "abf_station" / "aws_launch.py").read_text(encoding="utf-8")
    assert not submit.search("\n".join(ln for ln in al.splitlines() if not ln.lstrip().startswith("#")))
    assert not starts.search(al)


def test_new_files_carry_the_nothing_existing_header():
    # TC-182
    for p in (PLATFORM_DIR / "abf_station" / "aws_launch.py", PLATFORM_DIR / "tests" / "test_aws_launch.py"):
        head = p.read_text(encoding="utf-8").splitlines()[:40]
        assert [ln for ln in head if ln.startswith("# Nothing existing:")], p.name


# ======================================================================================================================
# Documents
# ======================================================================================================================

def test_docs_describe_the_launch_the_billing_sentence_and_the_requirements():
    # TC-156 .. TC-163, TC-170, TC-189
    d = doc("PLATFORM.md")
    assert "Launching on AWS Batch" in d
    section = d[d.index("Launching on AWS Batch"):]
    section = section[:section.index("\n## ", 5)] if "\n## " in section[5:] else section
    for key in ("process.executor", "process.queue", "aws.region", "workDir", "process.resourceLimits"):
        assert "`%s`" % key in section, key
    for word in ("Java 17", "Nextflow", "aws CLI", "storage_root", "s3://", "由 AWS 向實驗室的 AWS 帳號收費", "SIGTERM", "AWS Console",
                 "resume", "per-task", "head process", "AMI", "credential"):
        assert word in section, word
    assert "平台還沒有費用預估與上限" in section or "平台目前還沒有費用預估與上限" in section
    assert re.search(r"not a (total|limit on the total)|not the total|per-task", section)
    par = doc("SEQERA_PARITY.md")
    # TC-167: the AWS bracket near line 84 of SEQERA_PARITY.md
    assert "for AWS Batch the same agent runs them (create + check + launch + cancel; resume not yet)" in par
    row = [ln for ln in par.splitlines() if "`awsbatch-platform`" in ln][0]
    assert "Have (create + check + launch + cancel + upload + clean)" in row and row.rstrip().endswith("[ ] |")
    install = doc("INSTALL.md") + doc("OPERATIONS.md")
    assert "Java 17" in install and "Nextflow" in install and "aws CLI" in install
    t = doc("TESTING.md")
    assert "aws-launch" in t and "git diff --name-only" in t
    for text in (section, par, t):
        assert not re.findall(r"\b\d{12}\b", text)
        assert not re.search(r"NT\$|USD|US\$|TWD", section)
        assert not re.search(r"AKIA[0-9A-Z]{8}|@[a-z0-9-]+\.iam\.", text)



# ======================================================================================================================
# cloud-ce-memory-cap: maxMemoryGB and the merge of the platform's resourceLimits with the user's own
# ======================================================================================================================

def _limit(box, config_text="", **over):
    ce = ace(nextflowConfig=config_text, **over)
    return config_keys(box.bundle(ce=ce)["files"]["aws.config"]).get("process.resourceLimits")


def test_cap_trial_original_case_and_real_failure(box):
    # TC-009, TC-012, TC-015, TC-016, TC-019, TC-020, TC-021
    assert _limit(box, maxvCpus=4, maxMemoryGB=6) == "[cpus: 4, memory: 6.GB]"
    assert _limit(box, "process.resourceLimits = [cpus: 4, memory: 6.GB]\n", maxvCpus=4) == "[cpus: 4, memory: 6.GB]"
    assert _limit(box, maxvCpus=None, maxMemoryGB=6) == "[memory: 6.GB]"
    assert _limit(box, maxvCpus=16) == "[cpus: 16]"
    assert _limit(box, maxvCpus=None) is None
    assert box.bundle(ce=ace(maxMemoryGB=6))["ce"]["maxMemoryGB"] == 6
    assert "maxMemoryGB" not in box.bundle()["ce"]
    assert set(box.bundle()["ce"]) == {"name", "platform", "region", "workDir", "jobQueue", "spot", "maxvCpus", "environment", "nextflowConfig"}


def test_cap_snapshot_ce_carries_the_key_only_when_set(box):
    # TC-017
    from abf_station import launch
    cfg = {"region": REGION, "workDir": WORK, "jobQueue": QUEUE}
    on = launch.snapshot_ce({"name": "a", "platform": AWS, "config": dict(cfg, maxMemoryGB=6)})
    off = launch.snapshot_ce({"name": "a", "platform": AWS, "config": dict(cfg)})
    assert on["maxMemoryGB"] == 6 and "maxMemoryGB" not in off


def test_cap_bad_memory_value_is_refused_before_anything_is_written(box):
    # TC-018
    from abf_station import launch
    for bad in (0, 10001, True, "8", 1.5):
        with pytest.raises(launch.BundleError) as e:
            box.bundle(ce=ace(maxMemoryGB=bad))
        assert "maxMemoryGB" in str(e.value), bad
    nothing_happened(box)


@pytest.mark.parametrize("user, platform, want", [
    ("[cpus: 64]", dict(maxvCpus=4), "[cpus: 4]"),                                              # TC-024
    ("[cpus: 2]", dict(maxvCpus=4), "[cpus: 2]"),                                               # TC-025
    ("[memory: 32.GB]", dict(maxvCpus=None, maxMemoryGB=6), "[memory: 6.GB]"),                  # TC-026
    ("[memory: 4.GB]", dict(maxvCpus=None, maxMemoryGB=6), "[memory: 4.GB]"),                   # TC-027
    ("[time: 48.h]", dict(maxvCpus=4), "[cpus: 4, time: 48.h]"),                                # TC-028
    ("[disk: 200.GB]", dict(maxvCpus=4), "[cpus: 4, disk: 200.GB]"),                            # TC-029
    ("[time: 48.h, disk: 200.GB, memory: 32.GB, cpus: 64]", dict(maxvCpus=4, maxMemoryGB=6),
     "[cpus: 4, memory: 6.GB, disk: 200.GB, time: 48.h]"),                                      # TC-030
    ("[memory: '32 GB']", dict(maxvCpus=None, maxMemoryGB=6), "[memory: 6.GB]"),                # TC-031
    ("[memory: 32768.MB]", dict(maxvCpus=None, maxMemoryGB=6), "[memory: 6.GB]"),               # TC-032
    ("[cpus: 8]", dict(maxvCpus=None, maxMemoryGB=6), "[cpus: 8, memory: 6.GB]"),               # TC-034
])
def test_cap_merge_takes_the_smaller_and_keeps_what_the_user_set(box, user, platform, want):
    got = _limit(box, "process.resourceLimits = %s\n" % user, **platform)
    assert got == want


def test_cap_user_smaller_memory_stays_the_users(box):
    # TC-033
    for mine, mb in (("'2 GB'", 2048), ("512.MB", 512)):
        got = _limit(box, "process.resourceLimits = [memory: %s]\n" % mine, maxvCpus=4, maxMemoryGB=6)
        m = re.match(r"^\[cpus: 4, memory: (.+)\]$", got)
        assert m and "6.GB" not in got
        txt = m.group(1)
        num = float(re.search(r"\d+(?:\.\d+)?", txt).group(0))
        assert num * (1024 if "GB" in txt else 1) == mb


def test_cap_bare_resource_limits_and_commented_line(box):
    # TC-035, TC-036
    got = box.bundle(ce=ace(maxvCpus=4, maxMemoryGB=6, nextflowConfig="resourceLimits = [cpus: 64, memory: 32.GB]\n"))["files"]["aws.config"]
    assert config_keys(got)["process.resourceLimits"] == "[cpus: 4, memory: 6.GB]"
    assert len([ln for ln in got.splitlines() if "resourceLimits" in ln]) == 1
    assert _limit(box, "// process.resourceLimits = [cpus: 2]\n", maxvCpus=4) == "[cpus: 4]"


def test_cap_users_nextflow_config_is_untouched_and_without_platform_limits_nothing_is_written(box):
    # TC-038, TC-039, TC-040, TC-065, TC-066
    for text in ("process.resourceLimits = [cpus: 64, memory: 32.GB]\n", "process.cpus = 2\nprocess.memory = { 4.GB * task.attempt }\n"):
        b = box.bundle(ce=ace(maxvCpus=4, nextflowConfig=text))
        assert b["files"]["nextflow.config"].startswith(text)
    b = box.bundle(ce=ace(maxvCpus=None, maxMemoryGB=None, nextflowConfig="process.resourceLimits = [cpus: 2, memory: 4.GB]\n"))
    assert "resourceLimits" not in b["files"]["aws.config"] and "process.resourceLimits = [cpus: 2, memory: 4.GB]" in b["files"]["nextflow.config"]
    odd = "resourceLimits = [\n  cpus: 4\n]\n"
    b = box.bundle(ce=ace(maxvCpus=None, nextflowConfig=odd))
    assert "resourceLimits" not in b["files"]["aws.config"] and b["files"]["nextflow.config"].startswith(odd)
    assert _limit(box, "process.cpus = 2\nprocess.memory = { 4.GB * task.attempt }\n", maxvCpus=4) == "[cpus: 4]"
    old = ace(spot=True, environment=[{"name": "X", "value": "1", "head": True, "compute": False}], nextflowConfig="process.cpus = 2\n")
    got = box.bundle(ce=old)["ce"]
    assert got["spot"] is True and got["environment"] == old["environment"] and "maxMemoryGB" not in got


UNREADABLE = {
    "multi-line": "resourceLimits = [\n  cpus: 4\n]\n",
    "twice": "process.resourceLimits = [cpus: 4]\nprocess.resourceLimits = [cpus: 2]\n",
    "block": "process { resourceLimits { cpus = 4 } }\n",
    "variable": "resourceLimits = [cpus: params.c]\n",
    "unknown-key": "resourceLimits = [cpus: 4, gpus: 1]\n",
    "float-cpus": "resourceLimits = [cpus: 4.5]\n",
    "quoted-cpus": "resourceLimits = [cpus: '4']\n",
    "no-unit": "resourceLimits = [memory: 6]\n",
    "tb": "resourceLimits = [memory: 6.TB]\n",
    "disk-semicolon": "resourceLimits = [disk: 'a;b']\n",
    "time-shell": "resourceLimits = [time: '$(x)']\n",
    "time-long": "resourceLimits = [time: '" + "a" * 41 + "']\n",
    "nested": "resourceLimits = [cpus: 4, time: [1]]\n",
    "trailing": "resourceLimits = [cpus: 4] ; process.executor = 'local'\n",
}


@pytest.mark.parametrize("name", sorted(UNREADABLE))
def test_cap_unreadable_user_limits_are_refused_before_launch(box, name):
    # TC-041 TC-042 TC-043 TC-044 TC-045 TC-048 TC-049 TC-050 TC-051 TC-052 TC-053 TC-055 TC-069
    from abf_station import launch
    text = "// MY-MARKER-LINE\n" + UNREADABLE[name]
    with pytest.raises(launch.BundleError) as e:
        box.bundle(ce=ace(maxvCpus=4, nextflowConfig=text))
    msg = str(e.value)
    assert "resourceLimits" in msg and "aws1" in msg and "maxvCpus" in msg and "maxMemoryGB" in msg
    assert "cannot merge" in msg and "單行" in msg
    assert "MY-MARKER-LINE" not in msg and UNREADABLE[name].strip() not in msg and "Traceback" not in msg
    assert str(box.tmp) not in msg
    nothing_happened(box)


def test_cap_refused_also_when_only_the_memory_cap_is_set_and_never_when_nothing_is_set(box):
    # TC-054, TC-040
    from abf_station import launch
    with pytest.raises(launch.BundleError):
        box.bundle(ce=ace(maxvCpus=None, maxMemoryGB=6, nextflowConfig=UNREADABLE["multi-line"]))
    box.bundle(ce=ace(maxvCpus=None, nextflowConfig=UNREADABLE["multi-line"]))


def test_cap_every_readable_shape_keeps_every_key_the_user_wrote(box):
    # TC-068
    for body in ("cpus: 64", "memory: 32.GB", "disk: 200.GB", "time: 48.h", "cpus: 64, memory: 32.GB, disk: 200.GB, time: 48.h"):
        got = _limit(box, "process.resourceLimits = [%s]\n" % body, maxvCpus=4, maxMemoryGB=6)
        for key in re.findall(r"(\w+):", body):
            assert "%s:" % key in got, (body, got)
        assert "cpus: 4" in got and "memory: 6.GB" in got


def test_cap_screen_shows_the_memory_row_only_when_set(box):
    # TC-056, TC-057, TC-058
    from abf_launch import build
    on = "\n".join(build.launch_screen(box.bundle(ce=ace(maxMemoryGB=6)), "aws1"))
    assert "單一 task 的記憶體上限" in on and "單一 task 的 cpus 上限" in on
    off = "\n".join(build.launch_screen(box.bundle(), "aws1"))
    assert "記憶體上限" not in off
    merged = "\n".join(build.launch_screen(box.bundle(ce=ace(maxvCpus=4, nextflowConfig="process.resourceLimits = [cpus: 4, memory: 6.GB]\n")), "aws1"))
    assert "process.resourceLimits = [cpus: 4, memory: 6.GB]" in merged


def test_cap_one_shared_function_writes_the_line():
    # TC-037
    src = (PLATFORM_DIR / "abf_station" / "launch.py").read_text(encoding="utf-8")
    assert src.count("\"process.resourceLimits = [%s]\"") == 1
    assert src.count("_resource_limits_line(ce)") >= 3
