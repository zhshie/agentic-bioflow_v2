# Nothing existing: searched Nextflow's azurebatch executor, the launch command of the Seqera CLI and nf-core's tower launch tool; they all hand the work to a Seqera service, none is a local agent that starts the head process with azurebatch after a person's yes and can stop that one process after a second yes, so these tests drive our agent with a fake host (no network, no real program).
"""Launching and cancelling on Azure Batch (azure-launch).

The agent that sits on the platform host starts Nextflow's head process on that host (the compute is done by tasks in an Azure Batch pool
that already exists). Every test uses fakes for the program runner (`site.run_fixed`), the az runner of the preflight
(`azure_preflight._run`), the detached start (`site.start_detached`) and the signal (`os.kill`); nothing here reaches the network or
starts a real program. The TC ids refer to specs/azure-launch/test-case.md. No key-shaped string is written here as one literal:
test_azure_ce builds them from pieces.
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
from test_azure_ce import (AZ, BKEY, CRED, CRED_FILE, SAS, SKEY, Fake, create, fake_az, good_config, ip, jobs_count,  # noqa: F401
                           register_agent, set_status)
from test_gcb_ce import GCB, doc

AWS = "awsbatch-platform"
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="permission bits and /proc")
TOKEN = "abf_" + secrets.token_hex(16)     # made at run time: a fixed value of this shape in a tracked file fails tests/credentials_stay_in_settings_test.sh
CONTAINER = "labcontainer"
WORK = "az://" + CONTAINER + "/work"
SHEET = [["sample", "fastq_1", "strandedness"], ["s1", "az://%s/x.fastq.gz" % CONTAINER, "auto"]]
PID = 4242
SAS_Q = "[default]\nbatch_account_key = " + BKEY + "\nstorage_sas_token = ?" + SAS + "\n"
BOTH = "[default]\nbatch_account_key = " + BKEY + "\nstorage_account_key = " + SKEY + "\nstorage_sas_token = " + SAS + "\n"
NO_BATCH_KEY = "[default]\nstorage_account_key = " + SKEY + "\n"
NO_STORAGE_KEY = "[default]\nbatch_account_key = " + BKEY + "\n"
SECRETS = (BKEY, SKEY, SAS)
BILLING = "由 Azure 向實驗室的 Azure 帳號收費；本系統目前沒有費用預估與上限"
DOC_AZURE = "az" + "ure"      # the station package may not hold the bare word; the tests look for it in pieces too
CONFIG_FILE = "az" + "ure.config"


def zce(**over):
    """The snapshot of a fully set Azure Batch environment, as launch.snapshot_ce gives it."""
    c = {"name": "azure1", "platform": AZ, "location": "westeurope", "batchAccountName": "labbatch", "storageAccountName": "labstore",
         "workDir": WORK, "pool": "lab-pool", "spot": True, "maxvCpus": 16, "environment": [],
         "nextflowConfig": "// the user's own text\nprocess.cpus = 2\n", "preRunScript": "", "postRunScript": ""}
    c.update(over)
    return c


class Box:
    """The platform host as the agent sees it: a storage root, a settings file, a credential file, and fakes for what it runs."""

    def __init__(self, tmp, monkeypatch):
        from abf_station import site
        self.tmp = Path(tmp)
        self.mp = monkeypatch
        self.root = self.tmp / "host"
        self.storage = self.root / "storage"
        self.storage.mkdir(parents=True)
        self.settings = self.root / "deploy" / "config" / "env.yaml"
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text("reach: local\nstorage_root: %s\n" % self.storage)
        self.cred = self.root / "credentials-file"
        self.cred.write_text(CRED_FILE)
        if sys.platform != "win32":
            self.cred.chmod(0o600)
        monkeypatch.setenv("ABF_STATION_AZURE_CREDENTIALS", str(self.cred))
        monkeypatch.setenv("ABF_STATION_GCB_SETTLE_SECONDS", "0")
        self.java = (0, 'openjdk version "17.0.9" 2023-10-17')
        self.nextflow = (0, "      N E X T F L O W\n      version 25.04.0 build 5953")
        self.azcli = (0, "az-cli 2.60.0")
        self.ps = None
        self.runs = []
        self.started = []
        self.kills = []
        self.exit_code = None
        self.out_text = ""
        self.pid = PID
        self.start_error = None
        self.user = "tester"
        self.fake = fake_az(monkeypatch)
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
        if prog == "az":
            return self.azcli
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
        kw = dict(ce=zce(), agent="a1", facts=self.facts(), roots=[], run_name=run, pipeline="nf-core/rnaseq", revision="3.14.0",
                  samplesheet=copy.deepcopy(SHEET), params={"genome": "GRCh38"})
        kw.update(over)
        return launch.render_azure_bundle(**kw)

    def handle(self, job):
        from abf_station import handlers
        return handlers.handle(job, self.ctx)

    def folder(self, run="run-a"):
        return self.storage / "_azure_runs" / run

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
    b = {"version": 1, "run_name": run, "slurm_job_id": number, "run_folder": str(box.folder(run)), "agent": "a1", "ce": zce()}
    b.update(over)
    return b


def cancel_job(bundle, **kw):
    return job_of(bundle, kind="cancel_run", conf_kind="cancel", **kw)


def nothing_happened(box):
    assert box.started == []
    assert not (box.storage / "_azure_runs").exists()
    assert box.kills == []


def config_keys(text):
    """{key: value text} of the `key = value` lines of the Azure config file; comment lines are skipped."""
    out = {}
    for ln in text.splitlines():
        if not ln.strip() or ln.lstrip().startswith("//"):
            continue
        k, eq, v = ln.partition(" = ")
        assert eq, "not a setting line: %r" % ln
        assert k not in out, k
        out[k] = v
    return out


def code_of(path):
    return "\n".join(ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#"))


def register_with_facts(ip, box):
    from abf_platform import agents
    register_agent(ip)
    agents.register(ip.state_db, "a1", "0.1.0", time.time, facts=box.facts())


def sheet_file(tmp, rows=None):
    p = Path(tmp) / "samples.csv"
    p.write_text("\n".join(",".join(r) for r in (rows or SHEET)) + "\n")
    return p


def available_az(ip, name="azure1"):
    register_agent(ip)
    create(ip, name, config=good_config(workDir=WORK, spot=True, maxvCpus=16))
    set_status(ip, name, "available")


def prepare(ip, box, run="run-p", owner=None, **kw):
    from abf_launch import build
    return build.prepare_launch(ip.state_db, ce="azure1", pipeline="nf-core/rnaseq", revision="3.14.0", run_name=run,
                                samplesheet=str(sheet_file(box.tmp)), params={"genome": "GRCh38"}, owner=owner, **kw)


def launch_through_platform(ip, box, run="run-p"):
    """prepare, the human yes, the queue, the agent, the answer: the launches row of the run."""
    from abf_platform import actions, jobs
    register_with_facts(ip, box)
    create(ip, "azure1", config=good_config(workDir=WORK, spot=True, maxvCpus=16))
    set_status(ip, "azure1", "available")
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


# ======================================================================================================================
# US1 - launch after the yes (AZL-RUN, AZL-CONF)
# ======================================================================================================================

def test_launch_writes_head_pid_and_reports_it_as_the_job_number(box):
    # TC-001, TC-002, TC-003, TC-004, TC-005, TC-008 (AZL-RUN-01)
    b, res = launch_ok(box)
    folder = box.folder()
    assert res["ok"] is True and res["slurm_job_id"] == PID and res["run_name"] == "run-a" and res["run_folder"] == str(folder)
    assert res["message"].startswith("已啟動：主控程序編號（pid）%d，run 名稱 run-a，專屬資料夾 %s；Azure Batch 的工作與費用從現在開始計" % (PID, folder))
    assert BILLING in res["message"]
    assert (folder / "head.pid").read_text().strip() == str(PID)
    names = ("samplesheet.csv", "params.yaml", "nextflow.config", CONFIG_FILE, "head.sh", "tower.token", "head.pid")
    for name in names:
        assert (folder / name).is_file(), name
    # head.out is made by the detached start (faked here); its path is asserted below as the out_path argument
    assert not list(folder.glob("results*"))
    if sys.platform != "win32":
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700
        for name in names:
            assert stat.S_IMODE((folder / name).stat().st_mode) == 0o600, name
    assert (folder / "tower.token").read_text() == TOKEN
    assert len(box.started) == 1
    s = box.started[0]
    assert s["argv"] == ["bash", str(folder / "head.sh")] and s["cwd"] == str(folder) and s["out_path"] == str(folder / "head.out")
    from abf_station import azure_launch, gcb_launch
    box.mp.setenv("ABF_STATION_GCB_SETTLE_SECONDS", "7")
    assert gcb_launch._settle_seconds() == 7 and azure_launch._settle_seconds is gcb_launch._settle_seconds


def test_the_platform_records_the_pid_in_the_launches_row(ip, box):
    # TC-006, TC-127
    row = launch_through_platform(ip, box)
    assert row["slurm_job_id"] == PID and row["submitted_at"] is not None


def test_a_person_must_say_yes_an_azure_launch_is_never_auto_queued(ip, box, monkeypatch):
    # TC-007, TC-013, TC-014 (AZL-CONF-02)
    import argparse
    from abf_launch import cli, terminal
    register_with_facts(ip, box)
    create(ip, "azure1", config=good_config(workDir=WORK))
    set_status(ip, "azure1", "available")
    n = jobs_count(ip)
    prepare(ip, box)
    assert jobs_count(ip) == n
    monkeypatch.setattr(terminal, "terminal_problem", lambda: None)
    monkeypatch.setattr(terminal, "ask", lambda lines, question: False)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(ip.index))
    args = argparse.Namespace(ce="azure1", pipeline="nf-core/rnaseq", revision="3.14.0", run_name="run-n", samplesheet=str(sheet_file(box.tmp)),
                              params_file=None, param=["genome=GRCh38"], path_column=None, user=None)
    assert cli.cmd_launch(args) == 1
    assert jobs_count(ip) == n
    monkeypatch.setattr(terminal, "terminal_problem", lambda: "not a terminal")
    assert cli.cmd_launch(args) == 1
    assert jobs_count(ip) == n
    from abf_platform import actions
    with pytest.raises(Exception):
        actions.launch(ip.state_db, "azure1", prepare(ip, box, "run-q")[1], confirmed_by="the model says yes")
    assert jobs_count(ip) == n


def test_unconfirmed_azure_launch_is_refused_and_nothing_is_written_or_started(box):
    # TC-009, TC-010, TC-011, TC-012 (AZL-CONF-01)
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
    changed["files"][CONFIG_FILE] = changed["files"][CONFIG_FILE].replace("westeurope", "northeurope")
    other = copy.deepcopy(b)
    other["ce"]["pool"] = "other-pool"
    sheet = copy.deepcopy(b)
    sheet["samplesheet"][1][2] = "reverse"
    for label, bad in (("config", changed), ("pool", other), ("samplesheet", sheet)):
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
def test_a_link_in_the_run_folder_is_never_followed_and_tower_token_is_never_overwritten(box):
    # TC-008, TC-018
    target = box.tmp / "elsewhere"
    target.mkdir()
    (target / "head.sh").write_text("untouched")
    folder = box.folder()
    folder.parent.mkdir(parents=True)
    os.symlink(str(target), str(folder))
    state, res = box.handle(job_of(box.bundle()))
    assert state in ("refused", "error") and box.started == []
    assert (target / "head.sh").read_text() == "untouched" and [p.name for p in target.iterdir()] == ["head.sh"]
    from abf_station import azure_launch
    victim = box.tmp / "victim.txt"
    victim.write_text("untouched")
    os.symlink(str(victim), str(box.tmp / "link"))
    with pytest.raises(OSError):
        azure_launch._write_new(str(box.tmp / "link"), b"x")
    with pytest.raises(OSError):
        azure_launch._write_new(str(victim), b"x")
    assert victim.read_text() == "untouched"


def test_a_head_that_dies_at_once_is_reported_with_its_scrubbed_tail(box):
    # TC-019 (AZL-RUN-03)
    begin = "-----BEGIN " + "PRIVATE KEY-----"
    box.exit_code = 1
    box.out_text = "Unable to launch\n" + begin + "\nMARKERPRIVATEBODY0123456789abcdef\n"
    state, res = box.handle(job_of(box.bundle()))
    assert state == "error" and res["ok"] is False
    assert "1" in res["message"] and "Unable to launch" in res["message"] and "[hidden]" in res["message"]
    assert "MARKERPRIVATEBODY" not in json.dumps(res) and begin not in json.dumps(res)
    assert (box.folder() / "head.out").exists() and len(box.started) == 1


def test_missing_java_nextflow_or_az_cli_stops_the_launch_in_plain_words(box):
    # TC-020, TC-021, TC-022, TC-023, TC-155 (AZL-CRED-04)
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
    box.azcli = (127, "could not start az (FileNotFoundError)")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "az" in res["message"] and "Azure CLI" in res["message"]
    nothing_happened(box)
    assert not re.search(r"Traceback|FileNotFoundError", res["message"])


def test_too_little_deadline_is_refused(box):
    # TC-024
    state, res = box.handle(job_of(box.bundle(), remaining=5))
    assert state == "refused" and "期限" in res["message"]
    nothing_happened(box)


def test_a_failing_preflight_refuses_the_launch_and_makes_no_folder(box):
    # TC-025 (AZL-RUN-02)
    box.mp.setattr(__import__("abf_station.azure_preflight", fromlist=["x"]), "_run", Fake(replies={"batch": (1, "pool not found")}))
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "預檢" in res["message"] and "pool" in res["message"]
    nothing_happened(box)


@posix_only
def test_a_host_without_proc_is_refused_in_plain_words(box, monkeypatch):
    # TC-026
    from abf_station import azure_launch
    monkeypatch.setattr(azure_launch, "_has_proc", lambda: False)
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "Linux" in res["message"] and "WSL" in res["message"]
    nothing_happened(box)


def test_scripts_before_or_after_the_run_are_refused(box):
    # TC-027
    from abf_station import launch
    for key in ("preRunScript", "postRunScript"):
        with pytest.raises(launch.BundleError) as e:
            box.bundle(ce=zce(**{key: "echo hi"}))
        assert launch.NO_SCRIPTS in str(e.value)


def test_the_agent_must_be_local_and_the_bundle_has_no_account(box):
    # TC-028
    from abf_station import launch
    assert "account" not in box.bundle()
    with pytest.raises(launch.BundleError) as e:
        box.bundle(facts=box.facts(reach="ssh"))
    assert "reach" in str(e.value)


def test_launch_on_an_azure_environment_that_is_not_available_is_refused(ip):
    # TC-029
    from abf_platform import jobs
    available_az(ip)
    jobs.check_target(ip.state_db, "azure1", "launch_nextflow")
    n = jobs_count(ip)
    for status in ("invalid", "creating", "disabled"):
        set_status(ip, "azure1", status, ok=0)
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(ip.state_db, "azure1", "launch_nextflow")
    assert jobs_count(ip) == n


def test_run_folder_is_under_storage_root_in_azure_runs_and_a_missing_storage_root_is_refused(box):
    # TC-004 (AZL-BUNDLE-05)
    from abf_station import launch
    b = box.bundle()
    assert b["run_folder"] == "%s/_azure_runs/run-a" % box.storage
    with pytest.raises(launch.BundleError) as e:
        box.bundle(facts=box.facts(storage_root=None))
    assert "storage_root" in str(e.value) and "部署設定檔" in str(e.value)


# ======================================================================================================================
# US2 - the bundle and the files (AZL-BUNDLE)
# ======================================================================================================================

def test_azure_config_has_exactly_the_documented_keys(box):
    # TC-030, TC-031, TC-032, TC-033, TC-034, TC-035, TC-123 (AZL-BUNDLE-01)
    text = box.bundle("r1")["files"][CONFIG_FILE]
    assert config_keys(text) == {
        "process.executor": "'azurebatch'", "process.queue": "'lab-pool'", "workDir": "'%s/runs/r1/work'" % WORK,
        "azure.batch.accountName": "'labbatch'", "azure.batch.location": "'westeurope'", "azure.storage.accountName": "'labstore'",
        "azure.batch.allowPoolCreation": "false", "azure.batch.autoPoolMode": "false", "process.resourceLimits": "[cpus: 16]"}
    bare = config_keys(box.bundle("r1", ce=zce(maxvCpus=None))["files"][CONFIG_FILE])
    assert "process.resourceLimits" not in bare and len(bare) == 8
    assert config_keys(box.bundle("r2")["files"][CONFIG_FILE])["workDir"] == "'%s/runs/r2/work'" % WORK
    for word in ("accountKey", "sasToken", "managedIdentity", "servicePrincipal", "deletePoolsOnCompletion", "virtualNetwork",
                 "registry", "fusion", "wave", "terminateJobsOnCompletion"):
        assert word.lower() not in text.lower(), word
    assert "environment variables" in text.splitlines()[0] or "environment variable" in text.splitlines()[0]
    for s in SECRETS:
        assert s not in text
    a, b = box.bundle(ce=zce(spot=True)), box.bundle(ce=zce(spot=False))
    assert set(config_keys(a["files"][CONFIG_FILE])) == set(config_keys(b["files"][CONFIG_FILE]))
    assert not [ln for ln in a["files"][CONFIG_FILE].splitlines() if "spot" in ln.lower() and not ln.lstrip().startswith("//")]
    nf = box.bundle("r1")["files"]["nextflow.config"]
    assert "azure.batch" not in nf and "fusion" not in nf.lower()


def test_azure_bundle_has_the_five_files_and_no_credential_content(box):
    # TC-036, TC-037 (AZL-BUNDLE-02)
    b = box.bundle()
    assert set(b["files"]) == {"samplesheet.csv", "params.yaml", "nextflow.config", CONFIG_FILE, "head.sh"}
    assert set(b["ce"]) == {"name", "platform", "location", "batchAccountName", "storageAccountName", "workDir", "pool", "spot",
                            "maxvCpus", "environment", "nextflowConfig"}
    blob = json.dumps(b)
    assert str(box.cred) not in blob and not [s for s in SECRETS if s in blob]


def test_head_script_is_the_one_that_is_shown_and_run(box):
    # TC-038, TC-039, TC-065 (AZL-BUNDLE-03)
    from abf_launch import build
    b, _ = launch_ok(box)
    shown = "\n".join(build.launch_screen(b, "azure1"))
    script = b["files"]["head.sh"]
    folder = box.folder()
    assert (folder / "head.sh").read_text() == script and box.started[0]["script"] == script
    head = script.splitlines()
    assert head[0] == "#!/bin/bash" and head[1].startswith("# credentials:")
    assert head[2] == "umask 077" and head[3].startswith("cd ") and head[3].endswith("|| exit 1") and str(folder) in head[3]
    assert 'export TOWER_ACCESS_TOKEN="$(cat tower.token)"' in head and TOKEN not in script
    assert head[-1] == ("exec nextflow run nf-core/rnaseq -r 3.14.0 -name run-a -params-file params.yaml -c nextflow.config "
                        "-c %s -with-tower http://127.0.0.1:8123" % CONFIG_FILE)
    assert len([ln for ln in head if "nextflow run" in ln]) == 1
    assert str(box.cred) not in script and "sbatch" not in script and "#SBATCH" not in script
    assert not [s for s in SECRETS if s in script]
    for name in ("params.yaml", "nextflow.config", CONFIG_FILE, "head.sh"):
        for ln in b["files"][name].splitlines():
            assert ln in shown, (name, ln)
        assert (folder / name).read_text() == b["files"][name]
    assert (folder / "samplesheet.csv").read_text() == b["files"]["samplesheet.csv"]
    assert "-Dhttp.nonProxyHosts=" in script      # the receiver is on the loopback address


def test_nextflow_run_text_is_only_in_launch_py():
    # TC-039
    hits = [f.name for f in (PLATFORM_DIR / "abf_station").glob("*.py") if re.search(r"nextflow\s+run", code_of(f))]
    assert hits == ["launch.py"]


def test_the_users_nextflow_config_stays_in_its_own_file_and_the_azure_config_wins(box):
    # TC-038
    from abf_station import launch
    b = box.bundle()
    nf = b["files"]["nextflow.config"]
    assert nf.startswith("// the user's own text\nprocess.cpus = 2\n") and nf.endswith(launch.OVERWRITE_BLOCK)
    assert "user's own text" not in b["files"][CONFIG_FILE] and "report.overwrite" not in b["files"][CONFIG_FILE]


def test_samplesheet_paths_must_be_az_urls_of_the_work_container(box):
    # TC-040 .. TC-046 (AZL-BUNDLE-04)
    from abf_station import launch
    box.bundle()
    for cell in ("/home/x.fastq.gz", "s3://lab-bucket/x", "https://labstore.blob.core.windows.net/c/x", "az://other/x",
                 "az://%s/../x" % CONTAINER, "az://%s/a b" % CONTAINER, "gs://lab-bucket/x"):
        sheet = [["sample", "fastq_1", "strandedness"], ["s1", cell, "auto"]]
        with pytest.raises(launch.BundleError) as e:
            box.bundle(samplesheet=sheet)
        m = str(e.value)
        assert "az storage blob" in m and "azcopy" in m and "之後" in m and "自己" in m and CONTAINER in m, cell
    for cell in ("az://%s/a\x07b" % CONTAINER, "az://%s/a‮b" % CONTAINER):
        with pytest.raises(launch.BundleError):
            box.bundle(samplesheet=[["sample", "fastq_1", "strandedness"], ["s1", cell, "auto"]])
    box.bundle(samplesheet=[["sample", "fastq_1", "strandedness"], ["s1", "az://%s/x.fastq.gz" % CONTAINER, "not-a-path/at-all"]])
    # TC-046: the hint is written in two pieces; the source holds no whole upload command
    text = code_of(PLATFORM_DIR / "abf_station" / "launch.py")
    assert not re.search(r"az storage blob upload|azcopy (copy|cp|sync)", text)


@pytest.mark.parametrize("field,value", [("pool", "p'\nprocess.executor = 'local"), ("location", "westeurope'\nx = 1"),
                                         ("workDir", "az://labcontainer/work'\nx = 1"), ("batchAccountName", "lab'\nx = 1"),
                                         ("environment", [{"name": "X", "value": "v'\nz = 1\n}", "head": True}])])
def test_a_hostile_value_cannot_break_out_of_the_config_text(box, field, value):
    # TC-030 (AZL-BUNDLE-01)
    from abf_station import launch
    try:
        b = box.bundle(ce=zce(**{field: value}))
    except launch.BundleError:
        return
    assert set(config_keys(b["files"][CONFIG_FILE])) <= {
        "process.executor", "process.queue", "workDir", "azure.batch.accountName", "azure.batch.location", "azure.storage.accountName",
        "azure.batch.allowPoolCreation", "azure.batch.autoPoolMode", "process.resourceLimits"}


def test_azure_bundle_is_identical_when_built_twice_from_the_same_inputs(box):
    # TC-015
    from abf_station import launch
    a = box.bundle()
    b = launch.render_azure_bundle(ce=copy.deepcopy(a["ce"]), agent="a1", facts=launch.own_facts(box.ctx), roots=[], run_name="run-a",
                                   pipeline="nf-core/rnaseq", revision="3.14.0", samplesheet=copy.deepcopy(SHEET),
                                   params={"genome": "GRCh38"}, path_columns=None)
    assert a == b


def test_head_environment_variables_are_exported_and_compute_ones_are_not(box):
    # TC-056
    env = [{"name": "HEAD_ONLY", "value": "h1", "head": True, "compute": False},
           {"name": "COMPUTE_ONLY", "value": "c1", "head": False, "compute": True}]
    b, _ = launch_ok(box, ce=zce(environment=env))
    assert "export HEAD_ONLY=h1" in b["files"]["head.sh"] and "COMPUTE_ONLY" not in b["files"]["head.sh"]
    assert box.started[0]["env"]["HEAD_ONLY"] == "h1" and "COMPUTE_ONLY" not in box.started[0]["env"]
    from abf_station import launch
    for name in ("AZURE_BATCH_ACCOUNT_KEY", "AZURE_STORAGE_ACCOUNT_KEY", "AZURE_STORAGE_SAS_TOKEN", "AZURE_X", "TOWER_ACCESS_TOKEN", "ABF_X"):
        with pytest.raises(launch.BundleError):
            box.bundle(ce=zce(environment=[{"name": name, "value": "v", "head": True, "compute": False}]))


def test_fetch_run_records_does_not_list_the_azure_config_as_a_record():
    # TC-047
    from abf_station import fetch
    assert CONFIG_FILE in fetch._NOT_RECORDS


def test_resume_and_relaunch_of_an_azure_run_are_refused_in_plain_words(ip, box):
    # TC-048, TC-049, TC-050 (AZL-BUNDLE-06)
    from abf_launch import build
    launch_through_platform(ip, box)
    for fn in (build.prepare_resume, build.prepare_relaunch):
        with pytest.raises(build.Refusal) as e:
            fn(ip.state_db, "run-p", index_path=str(ip.index))
        m = str(e.value)
        assert "Azure Batch 的 run 還不能續跑或原樣重跑（尚未支援）" in m and "AWS" not in m
    origin = box.bundle("run-p")
    resume = {"version": 1, "agent": "a1", "ce": origin["ce"], "run_name": "run-p-a2", "run_folder": origin["run_folder"],
              "files": {"head-2.sh": "x\n"},
              "resume": {"of_run": "run-p", "of_slurm_job_id": PID, "session_id": "12345678-1234-1234-1234-123456789abc", "attempt": 2,
                         "origin": origin}}
    started = len(box.started)
    state, res = box.handle(job_of(resume))
    assert state == "refused" and "尚未支援" in res["message"] and "Azure" in res["message"] and "AWS" not in res["message"]
    assert len(box.started) == started


# ======================================================================================================================
# US3 - the credentials stay on the host (AZL-CRED)
# ======================================================================================================================

def test_head_env_has_only_the_nextflow_credential_names(box, monkeypatch):
    # TC-051, TC-052, TC-055, TC-056 (AZL-CRED-01)
    for k, v in (("ABF_PLATFORM_SECRET_THING", "x"), ("ABF_STATION_OTHER", "y"), ("AZURE_CLIENT_SECRET", "k"), ("AZURE_TENANT_ID", "t"),
                 ("AZURE_BATCH_ACCESS_KEY", "other"), ("AZURE_STORAGE_KEY", "other"), ("TOWER_ACCESS_TOKEN", "from-the-agent")):
        monkeypatch.setenv(k, v)
    b, res = launch_ok(box)
    env = box.started[0]["env"]
    assert env["AZURE_BATCH_ACCOUNT_KEY"] == BKEY and env["AZURE_STORAGE_ACCOUNT_KEY"] == SKEY
    assert "AZURE_STORAGE_SAS_TOKEN" not in env
    assert "AZURE_BATCH_ACCESS_KEY" not in env and "AZURE_STORAGE_KEY" not in env
    assert not [k for k in env if k.upper().startswith("ABF_")]
    assert sorted(k for k in env if k.upper().startswith("AZURE_")) == ["AZURE_BATCH_ACCOUNT_KEY", "AZURE_STORAGE_ACCOUNT_KEY"]
    assert "TOWER_ACCESS_TOKEN" not in env


def test_a_sas_token_loses_its_question_mark_and_the_account_key_wins_when_both_exist(box):
    # TC-053, TC-054 (AZL-CRED-01)
    box.cred.write_text(SAS_Q)
    launch_ok(box)
    env = box.started[0]["env"]
    assert env["AZURE_STORAGE_SAS_TOKEN"] == SAS and "AZURE_STORAGE_ACCOUNT_KEY" not in env and env["AZURE_BATCH_ACCOUNT_KEY"] == BKEY
    box.cred.write_text(BOTH)
    launch_ok(box, "run-b")
    env = box.started[1]["env"]
    assert env["AZURE_STORAGE_ACCOUNT_KEY"] == SKEY and "AZURE_STORAGE_SAS_TOKEN" not in env


def test_credentials_are_never_in_argv_files_results_or_the_database(ip, box):
    # TC-057, TC-058 (AZL-CRED-02)
    launch_through_platform(ip, box)
    results = []
    box.exit_code = 2
    box.out_text = "failed\nMARKER" + "OUT0123456789\n"
    results.append(box.handle(job_of(box.bundle("run-x")))[1])
    box.cred.unlink()
    results.append(box.handle(job_of(box.bundle("run-y")))[1])
    blob = json.dumps(results)
    assert not [s for s in SECRETS if s in blob] and str(box.cred) not in blob
    for s in box.started:
        assert not [k for k in SECRETS if k in " ".join(s["argv"])] and str(box.cred) not in " ".join(s["argv"])
    for p in box.storage.rglob("*"):
        if p.is_file() and p.name != "head.out":
            data = p.read_text(errors="replace")
            assert not [k for k in SECRETS if k in data] and str(box.cred) not in data, p.name
    raw = Path(str(ip.state_db)).read_bytes()
    assert not [s for s in SECRETS if s.encode() in raw] and str(box.cred).encode() not in raw


def test_missing_or_bad_credential_file_stops_the_launch_before_anything_is_written(box):
    # TC-059, TC-060, TC-061, TC-062, TC-063, TC-155 (AZL-CRED-03)
    box.cred.unlink()
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "憑證檔" in res["message"] and "ABF_STATION_AZURE_CREDENTIALS" in res["message"]
    nothing_happened(box)
    if sys.platform != "win32":
        box.cred.write_text(CRED_FILE)
        box.cred.chmod(0o644)
        state, res = box.handle(job_of(box.bundle()))
        assert state == "refused" and "600" in res["message"]
        nothing_happened(box)
        box.cred.chmod(0o600)
    for content, word in ((NO_BATCH_KEY, "batch_account_key"), (NO_STORAGE_KEY, "storage_account_key")):
        box.cred.write_text(content)
        state, res = box.handle(job_of(box.bundle()))
        assert state == "refused" and word in res["message"] and not [s for s in SECRETS if s in json.dumps(res)]
        nothing_happened(box)
    assert str(box.cred) not in json.dumps(res)


def test_the_credential_and_preflight_checks_run_before_the_first_file_is_written(box, monkeypatch):
    # TC-025, TC-059
    from abf_station import azure_preflight
    seen = []
    real = azure_preflight.run_preflight

    def spy(env, cred_path=None, **kw):
        seen.append(os.path.exists(str(box.storage / "_azure_runs")))
        return real(env, cred_path=cred_path, **kw)
    monkeypatch.setattr(azure_preflight, "run_preflight", spy)
    launch_ok(box)
    assert seen == [False]


# ======================================================================================================================
# US4 - the screens (AZL-SCREEN)
# ======================================================================================================================

def test_azure_launch_screen_first_paragraph_states_billing_without_amounts(box):
    # TC-064, TC-065, TC-066, TC-067, TC-068 (AZL-SCREEN-01)
    from abf_launch import build
    b = box.bundle("r1")
    lines = build.launch_screen(b, "azure1")
    assert lines[0].endswith("送出確認：下面就是會被送出的全部內容 ==")
    assert BILLING in lines[1] and build.AZURE_COST == BILLING
    text = "\n".join(lines)
    assert not re.search(r"NT\$|USD|US\$|TWD|[$＄￥¥€£]\s?[0-9]|[0-9]\s?(元|美元|台幣)", text)
    assert text.index(BILLING) < text.index("管線")
    assert build.AZURE_SPOT_NOTE in text
    for needle in (WORK + "/runs/r1/work", WORK + "/runs/r1/results", "lab-pool", "labbatch"):
        assert needle in text
    for title in ("samplesheet.csv", "params.yaml", "nextflow.config", CONFIG_FILE, "head.sh"):
        assert "== %s" % title in text, title
    top = text[:text.index("== head.sh")]
    assert not re.search(r"金鑰檔|憑證檔", top)
    assert "單一 task 的 cpus 上限" in text and "單一 task 的 cpus 上限" not in "\n".join(build.launch_screen(box.bundle(ce=zce(maxvCpus=None)), "azure1"))


def test_the_cancel_screen_says_pid_and_warns_about_leftover_jobs(box):
    # TC-067, TC-069
    from abf_launch import build
    text = "\n".join(build.cancel_screen(cancel_bundle(box), {"cancel_requested_at": None}))
    assert "主控程序編號（pid）: %d" % PID in text and "Slurm" not in text
    assert build.AZURE_CANCEL_NOTE in text and "Azure Portal" in text
    assert not re.search(r"停止計費|不再(收費|計費)|不會再(收費|計費)", text)


def test_cli_wording_switches_only_for_azure(ip, box, monkeypatch, capsys):
    # TC-070, TC-071, TC-072, TC-073 (AZL-SCREEN-03)
    import argparse
    from abf_launch import cli, terminal
    row = {"slurm_job_id": PID, "run_name": "run-a", "run_folder": "/x/run-a"}
    line = cli._submitted_line(row, AZ)
    assert line.startswith("已啟動：主控程序編號（pid）4242；run 名稱 run-a；專屬資料夾 /x/run-a") and "Slurm" not in line
    assert "平台主機" in line and "國網" not in line
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
    assert "主控程序" in out and "Azure Portal" in out and "Slurm" not in out and "squeue" not in out
    assert not re.search(r"停止計費|不再(收費|計費)|Nextflow 收到訊號後會取消", out)


def test_the_slurm_and_gcb_screens_and_bundles_are_byte_identical_to_before():
    # TC-073, TC-112, TC-113, TC-114 (AZL-SCREEN-02)
    from abf_launch import build, cli
    from test_launch_bundle import render
    b = render()
    h = lambda s: hashlib.sha256(s.encode()).hexdigest()
    assert h(json.dumps(b, sort_keys=True)) == "fcad3c22998c75125598565bcbb5ce5382a17f94fbca164d5aec62e6c39cc478"
    assert h("\n".join(build.launch_screen(b, "lab-a"))) == "020a51155f38740c5471798cb642ad1dac266b4aac2ecabb9dba56ba855cd0d4"
    assert h(b["files"]["head.sh"]) == "6432aa66c73d0f515d4475f42f93b6edf1fb4afbe5cd6c3cf2caf1f1ad5d5477"
    row = {"slurm_job_id": PID, "run_name": "run-a", "run_folder": "/x/run-a"}
    assert cli._submitted_line(row) == "已送出：Slurm 工作編號 4242；run 名稱 run-a；專屬資料夾 /x/run-a。"
    assert cli._submitted_line(row, GCB) == "已啟動：主控程序編號（pid）4242；run 名稱 run-a；專屬資料夾 /x/run-a。"
    assert cli._submitted_line(row, AWS) == "已啟動：主控程序編號（pid）4242；run 名稱 run-a；專屬資料夾 /x/run-a。"


def test_no_launch_flag_takes_a_credential(box):
    # TC-156, TC-157
    import inspect
    from abf_launch import build
    assert not [p for p in inspect.signature(build.prepare_launch).parameters if re.search(r"cred|key|secret|token", p, re.I)]
    src = (PLATFORM_DIR / "abf_launch" / "cli.py").read_text(encoding="utf-8")
    assert not re.search(r"add_argument\(\s*[\"']--(cred|key|secret|access)", src)
    for f in (PLATFORM_DIR / "abf_launch").glob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"""["'](java|nextflow|az)["']\s*,\s*["']--?version""", text), f.name


# ======================================================================================================================
# US5 - cancel (AZL-CANCEL)
# ======================================================================================================================

def test_cancel_sends_one_sigterm_to_exactly_the_verified_process_for_azure(box):
    # TC-074, TC-079, TC-080, TC-083 (AZL-CANCEL-01, AZL-CANCEL-02)
    launch_ok(box)
    box.cancel_world()
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "done" and res["ok"] is True and res["slurm_job_id"] == PID and res["run_name"] == "run-a"
    assert box.kills == [(PID, signal.SIGTERM)]
    m = res["message"]
    assert "pid %d" % PID in m and "終止信號" in m and "Azure Portal" in m and "Batch" in m and "自己處理" in m and "費用" in m
    assert not re.search(r"停止計費|不再(收費|計費)|不會再(收費|計費)|Nextflow 會取消", m)
    assert not [r for r in box.runs if r[0][:1] == ["az"] and r[0][1:2] != ["--version"]]      # no az command was run by the cancel


def test_cancel_refuses_and_sends_nothing_when_a_check_fails(box):
    # TC-075, TC-076, TC-077
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


def test_cancel_refuses_when_head_pid_does_not_match_or_the_folder_is_not_an_azure_one(box):
    # TC-077, TC-078, TC-082
    launch_ok(box)
    box.cancel_world(pid=9999)
    state, res = box.handle(cancel_job(cancel_bundle(box, number=9999)))
    assert state == "refused" and box.kills == []
    (box.folder() / "head.pid").unlink()
    box.cancel_world()
    assert box.handle(cancel_job(cancel_bundle(box)))[0] == "refused" and box.kills == []
    other = box.storage / "_aws_runs" / "run-a"
    state, res = box.handle(cancel_job(cancel_bundle(box, run_folder=str(other))))
    assert state == "refused" and box.kills == []


def test_cancel_refuses_an_unconfirmed_or_reused_confirmation(box):
    # TC-082
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


def test_a_run_without_a_pid_cannot_be_cancelled_in_plain_words(ip, box):
    # TC-078
    from abf_launch import build
    launch_through_platform(ip, box)
    con = sqlite3.connect(str(ip.state_db))
    with con:
        con.execute("UPDATE launches SET slurm_job_id = NULL WHERE run_name = 'run-p'")
    con.close()
    with pytest.raises(build.Refusal) as e:
        build.prepare_cancel(ip.state_db, "run-p")
    assert "主控程序編號" in str(e.value) and "Slurm" not in str(e.value)
    assert box.kills == []


def test_cancel_needs_no_available_status(ip, box):
    # TC-029, TC-081
    from abf_platform import jobs
    launch_through_platform(ip, box)
    for status in ("invalid", "creating"):
        set_status(ip, "azure1", status, ok=0)
        jobs.check_target(ip.state_db, "azure1", "cancel_run")
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(ip.state_db, "azure1", "launch_nextflow")


def test_gcb_and_aws_cancel_are_unchanged(box):
    # TC-084 (AZL-CANCEL-03)
    from abf_launch import build
    from abf_station import aws_launch, gcb_launch
    from test_gcb_launch import gce
    cb = {"version": 1, "run_name": "run-a", "slurm_job_id": 4242, "run_folder": "/srv/abf-storage/_gcb_runs/run-a", "agent": "a1", "ce": gce()}
    h = lambda s: hashlib.sha256(s.encode()).hexdigest()
    assert h("\n".join(build.cancel_screen(cb, {"cancel_requested_at": None}))) == \
        "2493a23f2d0eb06e2e093a2ef731a8316bfefb6b292b961026736f9af62a5ef9"
    assert gcb_launch.GCB_CANCEL_REMINDER.startswith("取消請求已送出（主控程序 pid %d）")
    assert aws_launch.CANCEL_REMINDER == "取消請求已送出（主控程序 pid %d）；請到 AWS Console 的 Batch 頁確認 job 都已結束，沒取消乾淨的工作仍會計費"


# ======================================================================================================================
# US6 - what the platform lets through (AZL-GATE)
# ======================================================================================================================

def test_azure_environment_accepts_exactly_preflight_launch_cancel_and_pipeline_files(ip):
    # TC-085, TC-086, TC-087, TC-088, TC-089, TC-090 (AZL-GATE-01)
    from abf_platform import jobs
    available_az(ip)
    before = jobs_count(ip)
    for kind in ("preflight", "launch_nextflow", "cancel_run", "pipeline_files", "put_upload", "clean_work"):      # azure-upload: put_upload; azure-clean: clean_work
        jobs.check_target(ip.state_db, "azure1", kind)
    for kind in ("list_site_files", "fetch_run_records", "read_task_log"):
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(ip.state_db, "azure1", kind)
        m = str(e.value)
        assert "尚未支援" in m and "Azure Batch" in m, (kind, m)
        assert "AWS" not in m and "Google Batch" not in m, (kind, m)
        assert "azure-clean" not in m and "azure-upload" not in m      # azure-clean: no feature name is said any more
    assert jobs_count(ip) == before


def test_aws_and_google_batch_still_accept_their_six_kinds_with_unchanged_refusals(ip):
    # TC-091, TC-092, TC-093 (AZL-GATE-02)
    from abf_platform import jobs
    from test_azure_ce import create as zcreate
    from test_gcb_ce import create as gcreate
    from test_aws_ce import create as acreate
    register_agent(ip)
    acreate(ip)
    gcreate(ip)
    set_status(ip, "aws1", "available")
    set_status(ip, "gcb1", "available")
    for name in ("aws1", "gcb1"):
        for kind in ("preflight", "launch_nextflow", "cancel_run", "pipeline_files", "clean_work", "put_upload"):
            jobs.check_target(ip.state_db, name, kind)
        for kind in ("list_site_files", "fetch_run_records", "read_task_log"):
            with pytest.raises(jobs.JobRefused) as e:
                jobs.check_target(ip.state_db, name, kind)
            if name == "aws1":
                assert str(e.value) == "aws1 is an AWS Batch environment: this job kind is not built for it yet (尚未支援)"
            else:
                assert str(e.value) == "gcb1 is a Google Batch environment: this job kind is not built for it yet (尚未支援)"
    assert zcreate is not None


def test_type_constants_are_as_planned_and_nothing_indexes_them_by_position():
    # TC-094, TC-095, TC-096, TC-097, TC-098 (AZL-GATE-03)
    from abf_platform import compute_envs
    assert compute_envs.PLATFORM_HOST_TYPES == (compute_envs.GOOGLE_BATCH, compute_envs.AWS, compute_envs.AZURE)
    assert compute_envs.CHECK_ONLY_TYPES == ("k8s-platform",)      # k8s-ce
    assert compute_envs.CHECKABLE == (compute_envs.SUPPORTED, compute_envs.GOOGLE_BATCH, compute_envs.AWS, compute_envs.AZURE, "k8s-platform")
    assert set(compute_envs.CLOUD_JOB_KINDS[compute_envs.AZURE]) == {"preflight", "launch_nextflow", "cancel_run", "pipeline_files", "put_upload", "clean_work"}
    for folder in ("abf_platform", "abf_station", "abf_launch"):
        for f in (PLATFORM_DIR / folder).rglob("*.py"):
            assert "PLATFORM_HOST_TYPES[" not in f.read_text(encoding="utf-8"), f.name
    line = [ln for ln in (PLATFORM_DIR / "abf_platform" / "compute_envs.py").read_text(encoding="utf-8").splitlines()
            if ln.startswith("CHECK_ONLY_TYPES")][0]
    assert "新雲端類型先放這裡，只開預檢" in line


def test_cloud_store_knows_az_and_a_dataset_can_go_there(ip):
    # TC-099, TC-100 (AZL-GATE-04; azure-upload changed this on purpose: cloud_store reads az:// now, see test_azure_upload.py)
    from abf_platform import cloud_store
    from abf_platform.actions import datasets
    ce = {"platform": AZ, "config": {"workDir": WORK}}
    assert cloud_store.workdir_scheme(ce) == "az" and cloud_store.workdir_bucket(ce) == CONTAINER
    assert cloud_store.upload_prefix(ce, "run-a", "az") == "az://" + CONTAINER + "/uploads/run-a/"
    available_az(ip)
    place = "az://" + CONTAINER + "/uploads/x.fastq.gz"
    got = datasets.register_dataset(ip.state_db, name="proj", version="v1", samplesheet="sample,fastq_1\ns1,%s\n" % place,
                                    files=[{"path": place}], destination="azure1")
    assert got["ok"] is True
    assert [f["path"] for f in datasets.get_dataset(ip.state_db, "proj", "v1")["files"]] == [place]


def test_clean_work_is_refused_for_azure_and_slurm_cannot_upload_and_nothing_starts(ip, box):
    # TC-101, TC-102, TC-103 (AZL-GATE-05)
    from abf_platform import jobs
    from abf_station import clean, put_upload, rules
    available_az(ip)
    n = jobs_count(ip)
    jobs.check_target(ip.state_db, "azure1", "clean_work")      # azure-clean: it can be queued now (test_azure_clean.py, test_station_clean_azure.py)
    assert jobs_count(ip) == n
    # azure-upload: run_put takes an Azure environment now (test_azure_upload.py); a Slurm environment is still refused
    args = {"ce": {"name": "s1", "platform": "slurm-platform", "workDir": "/x"}, "owner": "u1", "name": "x.fastq.gz",
            "dest": WORK + "/uploads/u1/x.fastq.gz", "size": 10}
    with pytest.raises(rules.Refusal):
        put_upload.run_put({"kind": "put_upload", "args": args}, box.ctx)
    assert box.runs == [] and box.started == []


def test_azure_preflight_is_still_taken_and_handled(ip, box):
    # TC-104, TC-105, TC-124 (AZL-GATE-06)
    from abf_platform import jobs
    from abf_station import azure_preflight
    available_az(ip)
    jobs.check_target(ip.state_db, "azure1", "preflight")
    job = {"kind": "preflight", "args": {"ce": {"name": "azure1", "platform": AZ, "credentialsId": CRED, "location": "westeurope",
                                                 "batchAccountName": "labbatch", "storageAccountName": "labstore",
                                                 "workDir": WORK, "pool": "lab-pool"}}, "remaining": 300}
    state, res = box.handle(job)
    assert state == "done" and [c["name"] for c in res["checks"]] == ["credential_name", "credential_file", "credential_shape", "az", "pool", "storage"]
    assert azure_preflight.TYPE == AZ


def test_primary_environment_never_auto_picks_azure_and_naming_it_works(ip, box):
    # TC-106, TC-107 (AZL-GATE-07)
    from abf_launch import build
    register_with_facts(ip, box)
    create(ip, "azure1", config=good_config(workDir=WORK))
    set_status(ip, "azure1", "available")
    assert build.primary_environment(ip.state_db) is None
    assert ip.run("ce", "primary", "azure1")[0] == 0
    assert build.primary_environment(ip.state_db) is None
    with pytest.raises(build.Refusal):
        build.prepare_launch(ip.state_db, pipeline="nf-core/rnaseq", revision="3.14.0", run_name="run-p",
                             samplesheet=str(sheet_file(box.tmp)), params={})
    name, bundle = prepare(ip, box)
    assert name == "azure1" and bundle["ce"]["platform"] == AZ


def test_another_users_azure_environment_and_run_are_not_found_for_launch_and_cancel(ip, box):
    # TC-108, TC-109
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
    assert build.prepare_cancel(ip.state_db, "run-p", owner=1)[0] == "azure1"


def test_snapshot_of_an_azure_environment_has_the_same_keys_as_before(ip):
    # TC-111
    from abf_platform import compute_envs
    register_agent(ip)
    create(ip, "azure1", config=good_config(workDir=WORK))
    snap = compute_envs.snapshot(compute_envs.get(ip.state_db, "azure1"))
    assert set(snap) == {"name", "platform", "credentialsId", "location", "batchAccountName", "storageAccountName", "workDir", "pool"}
    assert not [s for s in SECRETS if s in json.dumps(snap)]


# ======================================================================================================================
# US7 - out of scope, and no step back
# ======================================================================================================================

def test_a_plain_slurm_bundle_with_its_platform_changed_to_azure_is_not_launched_as_azure(box):
    # TC-110
    from test_launch_bundle import render
    b = copy.deepcopy(render())
    b["ce"]["platform"] = AZ
    state, res = box.handle(job_of(b))
    assert state == "refused" and box.started == []


def test_no_cost_estimate_and_no_other_reads_for_azure():
    # TC-118, TC-119, TC-120
    text = (PLATFORM_DIR / "abf_platform" / "cloud_cost.py").read_text(encoding="utf-8")
    assert not re.search(r"azbatch|\bazure\b|az://", text, re.I)


def test_no_azure_command_that_changes_anything():
    # TC-121, TC-122
    for folder in ("abf_station", "abf_platform", "abf_launch"):
        for f in (PLATFORM_DIR / folder).rglob("*.py"):
            code = code_of(f).replace("\\\n", "")
            assert not re.search(r"batch job (terminate|delete)|batch pool (create|delete|resize)|blob delete|az storage (?!blob (upload|show)\b)", code), f.name      # azure-upload: blob upload and blob show are allowed
    code = code_of(PLATFORM_DIR / "abf_station" / "azure_launch.py")
    assert re.findall(r'\["az", "[^"]+"', code) == ['["az", "--version"']


def test_tool_list_is_still_twelve_and_no_new_web_route(tmp_path):
    # TC-126 (AZL-CONF-05)
    from abf_platform import mcp_server, web
    names = {t.name for t in asyncio.run(mcp_server.build_server(str(tmp_path / "index.db")).list_tools())}
    from_aws = {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "list_used_pipelines",
                "read_task_log", "run_outputs", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation", "launch", "cancel", "resume", "relaunch", "forget"}
    assert len(names) == 20 and names == from_aws
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"azure|batch", getattr(r, "path", ""), re.I) and r.path not in {"/upload", "/upload/{batch}"}]      # web-upload-page: only the two routes this task registered are exempt (ruling 25)


def test_no_migration_is_needed_for_azure_launch(ip):
    # TC-127
    register_agent(ip)
    create(ip, "azure1", config=good_config(workDir=WORK))
    con = sqlite3.connect(str(ip.state_db))
    cols = {t: [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)] for t in ("launches", "jobs", "compute_envs")}
    con.close()
    assert cols["launches"] == ["id", "run_name", "slurm_job_id", "run_folder", "ce", "agent", "confirmed_at", "submitted_at",
                                "cancel_requested_at", "job_id", "user_id", "parent_run", "attempt", "attempt_kind", "work_cleaned_at"]
    assert cols["compute_envs"] == ["id", "name", "description", "platform", "credentials_id", "agent", "status", "message", "is_primary",
                                    "checked_ok", "config_json", "created_at", "updated_at", "last_used_at", "owner_user_id"]


def test_every_azure_refusal_says_what_to_do_and_leaks_nothing(ip, box):
    # TC-155
    from abf_platform import jobs
    available_az(ip)
    messages = []
    for kind in ("list_site_files", "read_task_log"):      # azure-upload: put_upload is taken now; azure-clean: clean_work is taken now
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(ip.state_db, "azure1", kind)
        messages.append(str(e.value))
    box.cred.unlink()
    messages.append(box.handle(job_of(box.bundle()))[1]["message"])
    box.cred.write_text(CRED_FILE)
    box.cred.chmod(0o600)
    box.java = (127, "x")
    messages.append(box.handle(job_of(box.bundle()))[1]["message"])
    for m in messages:
        assert m.strip() and not re.search(r"Traceback|File \"|SELECT |sqlite|\.py\b", m), m
        assert not [s for s in SECRETS if s in m] and str(box.cred) not in m, m


def test_no_cloud_library_is_imported_and_no_new_dependency():
    # TC-125
    toml = (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert "boto3" not in toml and not re.search(r"azure-|\"azure", toml)
    for folder in ("abf_platform", "abf_station", "abf_launch"):
        for f in (PLATFORM_DIR / folder).rglob("*.py"):
            assert not re.search(r"^\s*(import|from)\s+(boto3|botocore|google|%s)\b" % DOC_AZURE, f.read_text(encoding="utf-8"), re.M), f.name


# ======================================================================================================================
# Constitution and safety net (AZL-CONF)
# ======================================================================================================================

def test_the_launch_allow_list_still_has_one_entry():
    # TC-151
    text = (REPO_ROOT / "tests" / "no_second_run_state_test.sh").read_text(encoding="utf-8")
    block = re.search(r'LAUNCH_ALLOW="\n(.*?)\n"', text, re.S).group(1)
    entries = [ln for ln in block.splitlines() if ln.strip()]
    assert len(entries) == 1 and entries[0].startswith(
        "platform/abf_station/launch.py|platform/tests/test_station_launch.py::test_unconfirmed_launch_is_refused|")


def test_the_platform_package_starts_no_program_and_azure_launch_holds_no_submission_word():
    # TC-150, TC-152
    forbidden_everywhere = re.compile(r"\bnohup\b|\bsetsid\b")
    starts = re.compile(r"\bsubprocess\b|\bPopen\b|\bos\.system\b")
    submit = re.compile(r"nextflow\s+run|\bsbatch\b")
    for folder in (PLATFORM_DIR / "abf_platform", PLATFORM_DIR / "abf_station"):
        for f in folder.rglob("*.py"):
            text = code_of(f)
            assert not forbidden_everywhere.search(text), f.name
            if f.name != "site.py":
                assert not starts.search(text), f.name
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        assert not submit.search(code_of(f)), f.name
    al = code_of(PLATFORM_DIR / "abf_station" / "azure_launch.py")
    assert not submit.search(al) and not starts.search(al)


def test_new_files_carry_the_nothing_existing_header():
    # TC-153
    for p in (PLATFORM_DIR / "abf_station" / "azure_launch.py", PLATFORM_DIR / "tests" / "test_azure_launch.py"):
        head = p.read_text(encoding="utf-8").splitlines()[:40]
        line = [ln for ln in head if ln.startswith("# Nothing existing:")]
        assert line and "azurebatch" in line[0], p.name


# ======================================================================================================================
# Documents (AZL-DOC)
# ======================================================================================================================

def test_platform_md_documents_azure_launch():
    # TC-130, TC-131, TC-132, TC-133, TC-134, TC-135, TC-136, TC-141 (AZL-DOC-01)
    d = doc("PLATFORM.md")
    assert "checked and launched on the platform host (upload, clean, resume: not yet)" in d
    assert d.count("Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; Kubernetes can be created and checked on the platform host (launch: not yet); the other nine types can be modelled only") >= 2
    assert "Launching on Azure Batch" in d
    section = d[d.index("Launching on Azure Batch"):]
    section = section[:section.index("\n## ", 5)] if "\n## " in section[5:] else section
    for key in ("process.executor", "process.queue", "workDir", "azure.batch.accountName", "azure.batch.location",
                "azure.storage.accountName", "azure.batch.allowPoolCreation", "azure.batch.autoPoolMode", "process.resourceLimits"):
        assert "`%s`" % key in section, key
    for word in ("Java 17", "Nextflow", "az CLI", "storage_root", "az://", "dockerCompatible", "task slots", "container", "SIGTERM",
                 "Azure Portal", "resume", "per-task", "head process", "由 Azure 向實驗室的 Azure 帳號收費", "ABF_STATION_AZURE_CREDENTIALS"):
        assert word in section, word
    assert "本系統目前沒有費用預估與上限" in section
    assert not re.search(r"NT\$|USD|US\$|TWD", section)
    assert not re.search(r"\b\d{12}\b", section)


def test_seqera_parity_azure_row():
    # TC-137, TC-138 (AZL-DOC-02)
    par = doc("SEQERA_PARITY.md")
    assert "for Azure Batch the same agent runs them (create + check + launch + cancel; resume not yet)" in par
    assert "launch in " + "azure-launch" not in par
    row = [ln for ln in par.splitlines() if "`azbatch-platform`" in ln][0]
    assert "Have (create + check + launch + cancel + upload + clean)" in row and row.rstrip().endswith("[ ] |")


def test_testing_md_has_azure_launch_section_with_manual_steps():
    # TC-139, TC-140, TC-142 .. TC-149 (AZL-DOC-03)
    t = doc("TESTING.md")
    assert "azure-launch" in t
    section = t[t.index("azure-launch"):]
    assert "會花錢、需維護者同意" in section
    for n in range(1, 8):
        assert re.search(r"^\s*%d[.)、]" % n, section, re.M), n
    for word in ("dockerCompatible", "Azure Portal", "ledger", "az batch job terminate"):
        assert word in section, word
    install = doc("INSTALL.md") + doc("OPERATIONS.md")
    assert "Java 17" in install and "Nextflow" in install and "az CLI" in install



# ======================================================================================================================
# cloud-ce-memory-cap (azure): maxMemoryGB and the merge with the user's own resourceLimits
# ======================================================================================================================

def _cap_limit(box, config_text="", **over):
    ce = zce(nextflowConfig=config_text, **over)
    return config_keys(box.bundle(ce=ce)["files"]["azure.config"]).get("process.resourceLimits")


def test_cap_original_case_real_failure_and_memory_only(box):
    # TC-011 (original trial case), TC-023 (the user's memory key is kept), TC-014 (memory only), TC-019 (the cpus-only line stays)
    assert _cap_limit(box, maxvCpus=4, maxMemoryGB=6) == "[cpus: 4, memory: 6.GB]"
    assert _cap_limit(box, "process.resourceLimits = [cpus: 4, memory: 6.GB]\n", maxvCpus=4) == "[cpus: 4, memory: 6.GB]"
    assert _cap_limit(box, maxvCpus=None, maxMemoryGB=6) == "[memory: 6.GB]"
    assert _cap_limit(box, maxvCpus=16) == "[cpus: 16]"
    assert box.bundle(ce=zce(maxMemoryGB=6))["ce"]["maxMemoryGB"] == 6
    assert "maxMemoryGB" not in box.bundle()["ce"]


def test_cap_snapshot_ce_and_bad_values(box):
    # TC-017, TC-018
    from abf_station import launch
    view = {"name": "x", "platform": AZ, "config": {"location": "westeurope", "workDir": WORK}}
    on = launch.snapshot_ce({"name": "x", "platform": AZ, "config": dict({"location": "westeurope", "workDir": WORK}, maxMemoryGB=6)})
    assert on["maxMemoryGB"] == 6 and "maxMemoryGB" not in launch.snapshot_ce(view)
    for bad in (0, 10001, True, "8", 1.5):
        with pytest.raises(launch.BundleError) as e:
            box.bundle(ce=zce(maxMemoryGB=bad))
        assert "maxMemoryGB" in str(e.value), bad


def test_cap_unreadable_user_limits_are_refused_and_no_limit_is_left_alone(box):
    # TC-047, TC-039
    from abf_station import launch
    shapes = ("resourceLimits = [\n  cpus: 4\n]\n", "process.resourceLimits = [cpus: 4]\nprocess.resourceLimits = [cpus: 2]\n",
              "process { resourceLimits { cpus = 4 } }\n", "resourceLimits = [cpus: params.c]\n", "resourceLimits = [cpus: 4, gpus: 1]\n")
    for text in shapes:
        with pytest.raises(launch.BundleError) as e:
            box.bundle(ce=zce(maxvCpus=4, nextflowConfig="// MY-MARKER-LINE\n" + text))
        assert "resourceLimits" in str(e.value) and "MY-MARKER-LINE" not in str(e.value) and "maxMemoryGB" in str(e.value)
    keep = "process.resourceLimits = [cpus: 2, memory: 4.GB]\n"
    b = box.bundle(ce=zce(maxvCpus=None, nextflowConfig=keep))
    assert "resourceLimits" not in b["files"]["azure.config"] and keep in b["files"]["nextflow.config"]


def test_cap_screen_row_only_when_set(box):
    # TC-056, TC-057
    from abf_launch import build
    on = "\n".join(build.launch_screen(box.bundle(ce=zce(maxMemoryGB=6)), "azure1"))
    assert "單一 task 的記憶體上限" in on and "單一 task 的 cpus 上限" in on
    assert "記憶體上限" not in "\n".join(build.launch_screen(box.bundle(), "azure1"))
