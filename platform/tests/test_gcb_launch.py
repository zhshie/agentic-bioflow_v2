# Nothing existing: searched Nextflow's google-batch executor, the launch command of the Seqera CLI and nf-core's tower launch tool; they all hand the work to a Seqera service, none gives a local agent a confirmed launch and cancel, so these tests drive our agent with a fake host (no network, no real program).
"""Launching and cancelling on Google Cloud Batch (gcb-launch, C-2).

The agent that sits on the platform host starts Nextflow's head process on that host (the compute is done by Batch virtual
machines). Every test uses fakes for the program runner (`site.run_fixed`), the detached start (`site.start_detached`) and the
signal (`os.kill`); nothing here reaches the network or starts a real program. The TC ids refer to specs/gcb-launch/test-case.md.
No file written here holds a private-key header as one literal: test_gcb_ce builds it from pieces.
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
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from test_gcb_ce import (BEGIN, EMAIL, GCB, KEY_TEXT, PROJECT, create, doc, good_config, ip, jobs_count,  # noqa: F401
                         key_data, register_agent, set_status)

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="permission bits and /proc")
TOKEN = "abf_" + secrets.token_hex(16)     # made at run time: a fixed value of this shape in a tracked file fails tests/credentials_stay_in_settings_test.sh
SHEET = [["sample", "fastq_1", "strandedness"], ["s1", "gs://lab-bucket/x.fastq.gz", "auto"]]
PID = 4242
WORK = "gs://lab-bucket/" + "work"      # the work folder of the environment; written in pieces so that no path in this file looks like a cluster path


def gce(**over):
    """The snapshot of a fully set Google Batch environment, as launch.snapshot_ce gives it."""
    c = {"name": "gcb1", "platform": GCB, "project": PROJECT, "location": "europe-west2", "workDir": "gs://lab-bucket/work",
         "spot": True, "bootDiskSize": "50 GB", "bootDiskImage": "batch-debian", "serviceAccountEmail": EMAIL,
         "network": "default", "subnetwork": "default", "usePrivateAddress": True, "labels": {"team": "lab"}, "maxvCpus": 16,
         "environment": [], "nextflowConfig": "// the user's own text\nprocess.cpus = 2\n", "preRunScript": "", "postRunScript": ""}
    c.update(over)
    return c


class Box:
    """The platform host as the agent sees it: a storage root, a settings file, a key file, and fakes for what it runs."""

    def __init__(self, tmp, monkeypatch):
        from abf_station import gcb_preflight, site
        self.tmp = Path(tmp)
        self.mp = monkeypatch
        self.root = self.tmp / "host"
        self.storage = self.root / "storage"
        self.storage.mkdir(parents=True)
        self.settings = self.root / "deploy" / "config" / "env.yaml"
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text("reach: local\nstorage_root: %s\n" % self.storage)
        self.key = self.root / "gcp-sa.json"
        self.key.write_text(json.dumps(key_data()))
        if sys.platform != "win32":
            self.key.chmod(0o600)
        monkeypatch.setenv("ABF_STATION_GCP_CREDENTIALS", str(self.key))
        monkeypatch.setenv("ABF_STATION_GCB_SETTLE_SECONDS", "0")
        self.java = (0, 'openjdk version "17.0.9" 2023-10-17')
        self.nextflow = (0, "      N E X T F L O W\n      version 25.04.0 build 5953")
        self.gcloud = (0, "")
        self.ps = None                      # (rc, text) or None: the line of the head process
        self.runs = []                      # every fixed program asked for
        self.started = []                   # every detached start
        self.kills = []
        self.exit_code = None               # what poll() says of a started process
        self.out_text = ""
        self.pid = PID
        self.start_error = None
        self.cwd = None
        self.user = "tester"
        self.real_start = getattr(site, "start_detached", None)
        monkeypatch.setattr(site, "run_fixed", self._run_fixed)
        monkeypatch.setattr(site, "start_detached", self._start)
        monkeypatch.setattr(gcb_preflight.shutil, "which", lambda n: "/usr/bin/gcloud" if n == "gcloud" else None)
        monkeypatch.setattr(os, "kill", lambda pid, sig: self.kills.append((pid, sig)))
        self.ctx = SimpleNamespace(site=None, settings_file=str(self.settings), platform_url="http://127.0.0.1:8123",
                                   agent_name="a1", instance_id=None, used_confirmations=set(), job_started=time.monotonic())

    # the fakes
    def _run_fixed(self, argv, env, timeout):
        self.runs.append((list(argv), dict(env or {})))
        prog = argv[0]
        if prog == "java":
            return self.java
        if prog == "nextflow":
            return self.nextflow
        if prog == "gcloud":
            return self.gcloud
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

    # the inputs
    def facts(self, **over):
        f = {"slurm_account": None, "reach": "local", "platform_local": True, "endpoint": "http://127.0.0.1:8123",
             "forward_file": None, "storage_root": str(self.storage), "way_back": None, "platform_public_url": None}
        f.update(over)
        return f

    def bundle(self, run="run-a", **over):
        from abf_station import launch
        kw = dict(ce=gce(), agent="a1", facts=self.facts(), roots=[], run_name=run, pipeline="nf-core/rnaseq", revision="3.14.0",
                  samplesheet=copy.deepcopy(SHEET), params={"genome": "GRCh38"})
        kw.update(over)
        return launch.render_gcb_bundle(**kw)

    def handle(self, job):
        from abf_station import handlers
        return handlers.handle(job, self.ctx)

    def folder(self, run="run-a"):
        return self.storage / "_gcb_runs" / run

    def files_under_storage(self):
        return sorted(str(p.relative_to(self.storage)) for p in self.storage.rglob("*"))

    def cancel_world(self, run="run-a", pid=PID, args=None, owner=None, cwd=None):
        """Make the fake `ps` and /proc agree with a live head process of this run."""
        from abf_station import gcb_launch
        owner = owner or self.user
        args = args if args is not None else "/usr/bin/java -cp x nextflow.cli.Launcher run nf-core/rnaseq -r 3.14.0 -name %s -with-tower http://127.0.0.1:8123" % run
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
    b = {"version": 1, "run_name": run, "slurm_job_id": number, "run_folder": str(box.folder(run)), "agent": "a1", "ce": gce()}
    b.update(over)
    return b


def cancel_job(bundle, **kw):
    return job_of(bundle, kind="cancel_run", conf_kind="cancel", **kw)


def nothing_happened(box):
    assert box.started == []
    assert not (box.storage / "_gcb_runs").exists()
    assert box.kills == []


def config_keys(text):
    """{key: value text} of the `key = value` lines of a gcb.config; comment lines are skipped."""
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
    # TC-001, TC-002, TC-003, TC-004
    b, res = launch_ok(box)
    folder = box.folder()
    assert res["ok"] is True and res["slurm_job_id"] == PID and res["run_name"] == "run-a" and res["run_folder"] == str(folder)
    assert res["message"] == ("已啟動：主控程序編號（pid）%d，run 名稱 run-a，專屬資料夾 %s；Google Batch 的工作與費用從現在開始計"
                              % (PID, folder))
    assert (folder / "head.pid").read_text().strip() == str(PID)
    for name in ("samplesheet.csv", "params.yaml", "nextflow.config", "gcb.config", "head.sh", "tower.token", "head.pid"):
        assert (folder / name).is_file(), name
    if sys.platform != "win32":
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700
        for name in ("tower.token", "head.pid"):
            assert stat.S_IMODE((folder / name).stat().st_mode) == 0o600, name
    assert (folder / "tower.token").read_text() == TOKEN
    assert len(box.started) == 1
    s = box.started[0]
    assert s["argv"] == ["bash", str(folder / "head.sh")] and s["cwd"] == str(folder) and s["out_path"] == str(folder / "head.out")


def test_the_platform_records_the_pid_in_the_launches_row(ip, box):
    # TC-005
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
    return build.prepare_launch(ip.state_db, ce="gcb1", pipeline="nf-core/rnaseq", revision="3.14.0", run_name=run,
                                samplesheet=str(sheet_file(box.tmp)), params={"genome": "GRCh38"}, owner=owner, **kw)


def launch_through_platform(ip, box, run="run-p"):
    """prepare, the human yes, the queue, the agent, the answer: the launches row of the run."""
    from abf_platform import actions, jobs
    register_with_facts(ip, box)
    create(ip, owner_user_id=None)
    set_status(ip, "gcb1", "available")
    ce_name, bundle = prepare(ip, box, run)
    cid, job_id = actions.launch(ip.state_db, ce_name, bundle, confirmed_by=actions.TERMINAL)
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


def test_a_person_must_say_yes_a_gcb_launch_is_never_auto_queued(ip, box, monkeypatch):
    # TC-006, TC-011, TC-012: no job exists before the yes; n, a missing terminal and a refusal leave the jobs table as it was
    import argparse
    from abf_launch import cli, terminal
    register_with_facts(ip, box)
    create(ip)
    set_status(ip, "gcb1", "available")
    n = jobs_count(ip)
    prepare(ip, box)
    assert jobs_count(ip) == n
    monkeypatch.setattr(terminal, "terminal_problem", lambda: None)
    monkeypatch.setattr(terminal, "ask", lambda lines, question: False)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(ip.index))
    args = argparse.Namespace(ce="gcb1", pipeline="nf-core/rnaseq", revision="3.14.0", run_name="run-n", samplesheet=str(sheet_file(box.tmp)),
                              params_file=None, param=["genome=GRCh38"], path_column=None, user=None)
    assert cli.cmd_launch(args) == 1
    assert jobs_count(ip) == n
    monkeypatch.setattr(terminal, "terminal_problem", lambda: "not a terminal")
    assert cli.cmd_launch(args) == 1
    assert jobs_count(ip) == n
    # the only road to a job is the human channel; a model's own call has no such channel
    from abf_platform import actions
    with pytest.raises(Exception):
        actions.launch(ip.state_db, "gcb1", prepare(ip, box, "run-q")[1], confirmed_by="the model says yes")
    assert jobs_count(ip) == n


def test_unconfirmed_gcb_launch_is_refused_and_nothing_is_written_or_started(box):
    # TC-007, TC-008, TC-009, TC-010
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
    # the same confirmation used twice: the first runs, the second is refused and writes nothing more
    state, _ = box.handle(good)
    assert state == "done"
    state, res = box.handle(good)
    assert state == "refused" and len(box.started) == 1


def test_a_changed_bundle_is_refused_by_the_agent(box):
    # TC-013, TC-014, TC-015: a confirmation made for exactly this changed content; only the agent's own rebuild can refuse it
    b = box.bundle()
    changed = copy.deepcopy(b)
    changed["files"]["gcb.config"] = changed["files"]["gcb.config"].replace("europe-west2", "europe-west3")
    other = copy.deepcopy(b)
    other["ce"]["project"] = "other-project-9"
    sheet = copy.deepcopy(b)
    sheet["samplesheet"][1][2] = "reverse"
    for label, bad in (("config", changed), ("project", other), ("samplesheet", sheet)):
        state, res = box.handle(job_of(bad))
        assert state == "refused", (label, res)
        nothing_happened(box)


def test_an_existing_run_folder_is_never_overwritten(box):
    # TC-016
    folder = box.folder()
    folder.mkdir(parents=True)
    (folder / "keep.txt").write_text("mine")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "已存在" in res["message"]
    assert [p.name for p in folder.iterdir()] == ["keep.txt"] and (folder / "keep.txt").read_text() == "mine"
    assert box.started == []


@posix_only
def test_a_link_in_the_run_folder_is_never_followed(box):
    # TC-017: the folder is a link to somewhere else, and a link of the folder's own files would be refused the same way
    target = box.tmp / "elsewhere"
    target.mkdir()
    (target / "head.sh").write_text("untouched")
    folder = box.folder()
    folder.parent.mkdir(parents=True)
    os.symlink(str(target), str(folder))
    state, res = box.handle(job_of(box.bundle()))
    assert state in ("refused", "error") and box.started == []
    assert (target / "head.sh").read_text() == "untouched" and [p.name for p in target.iterdir()] == ["head.sh"]
    # a link in place of one file: O_NOFOLLOW makes the write fail instead of writing through it
    from abf_station import gcb_launch
    victim = box.tmp / "victim.txt"
    victim.write_text("untouched")
    os.symlink(str(victim), str(box.tmp / "link"))
    with pytest.raises(OSError):
        gcb_launch._write_new(str(box.tmp / "link"), b"x")
    assert victim.read_text() == "untouched"


def test_a_write_that_fails_halfway_is_an_error_that_names_the_folder_left_behind(box, monkeypatch):
    # TC-018
    from abf_station import gcb_launch
    real = gcb_launch._write_new
    calls = []

    def flaky(path, data, mode=0o600):
        calls.append(path)
        if len(calls) == 3:
            raise OSError("disk full")
        return real(path, data, mode)
    monkeypatch.setattr(gcb_launch, "_write_new", flaky)
    state, res = box.handle(job_of(box.bundle()))
    assert state == "error" and res["ok"] is False
    assert str(box.folder()) in res["left_on_site"] and str(box.folder()) in res["message"]
    assert box.started == []


def test_a_head_that_dies_at_once_is_reported_with_its_scrubbed_tail(box):
    # TC-019
    box.exit_code = 1
    box.out_text = "Unable to launch\n" + BEGIN + "\nMARKERPRIVATEBODY0123456789abcdef\n"
    state, res = box.handle(job_of(box.bundle()))
    assert state == "error" and res["ok"] is False
    assert "1" in res["message"] and "Unable to launch" in res["message"] and "[hidden]" in res["message"]
    assert "MARKERPRIVATEBODY" not in json.dumps(res) and BEGIN not in json.dumps(res)
    assert (box.folder() / "head.out").exists() and len(box.started) == 1


def test_missing_java_or_nextflow_stops_the_launch_in_plain_words(box):
    # TC-020, TC-021, TC-031
    box.java = (127, "could not start java (FileNotFoundError)")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "Java" in res["message"] and "17" in res["message"]
    nothing_happened(box)
    box.java = (0, 'openjdk version "17.0.9" 2023-10-17')
    box.nextflow = (127, "could not start nextflow (FileNotFoundError)")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "Nextflow" in res["message"]
    nothing_happened(box)
    assert not re.search(r"Traceback|FileNotFoundError", res["message"])


def test_old_java_is_refused(box):
    # TC-022
    box.java = (0, 'openjdk version "11.0.2" 2019-01-15')
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "17" in res["message"] and "Java" in res["message"]
    nothing_happened(box)


def test_too_little_deadline_is_refused(box):
    # TC-023
    state, res = box.handle(job_of(box.bundle(), remaining=5))
    assert state == "refused" and "期限" in res["message"]
    nothing_happened(box)


def test_a_failing_preflight_refuses_the_launch(box):
    # TC-024
    box.gcloud = (1, "PERMISSION_DENIED: the Batch API is not enabled")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "預檢" in res["message"] and "batch_api" in res["message"]
    nothing_happened(box)


@posix_only
def test_a_host_without_proc_is_refused_in_plain_words(box, monkeypatch):
    # TC-026
    from abf_station import gcb_launch
    monkeypatch.setattr(gcb_launch, "_has_proc", lambda: False)
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "Linux" in res["message"] and "WSL" in res["message"]
    nothing_happened(box)


def test_an_agent_that_is_not_on_the_local_host_is_refused(box):
    # TC-027: a bundle built for a remote way back is not what this agent builds from its own (local) settings, and the bundle itself cannot be built
    from abf_station import launch
    with pytest.raises(launch.BundleError):
        box.bundle(facts=box.facts(reach="remote", way_back="forward", platform_local=True, forward_file=str(box.storage / "f")))
    box.settings.write_text("reach: remote\nstorage_root: %s\n" % box.storage)
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "本機" in res["message"] and box.started == []
    nothing_happened(box)


def test_scripts_before_or_after_the_run_are_refused(box):
    # TC-028
    from abf_station import launch
    for key in ("preRunScript", "postRunScript"):
        with pytest.raises(launch.BundleError) as e:
            box.bundle(ce=gce(**{key: "echo hi"}))
        assert launch.NO_SCRIPTS in str(e.value)


def test_a_bare_bucket_work_dir_is_refused_at_launch_with_nextflows_rule(box):
    # TC-029
    from abf_station import launch
    with pytest.raises(launch.BundleError) as e:
        box.bundle(ce=gce(workDir="gs://lab-bucket"))
    assert "子目錄" in str(e.value) and "subdirectory" in str(e.value)


def test_a_launch_that_fails_a_step_is_not_retried(box):
    # TC-030
    box.exit_code = 3
    state, _ = box.handle(job_of(box.bundle()))
    assert state == "error" and len(box.started) == 1
    box.start_error = OSError("cannot start")
    state, res = box.handle(job_of(box.bundle("run-b")))
    assert state == "error" and len(box.started) == 1 and "Traceback" not in res["message"]


def test_a_missing_or_open_or_wrong_project_key_file_stops_the_launch_before_anything_is_written(box):
    # TC-031, TC-086, TC-087, TC-088
    box.key.unlink()
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "金鑰檔" in res["message"]
    nothing_happened(box)
    box.key.write_text(json.dumps(key_data(project_id="another-project-9")))
    if sys.platform != "win32":
        box.key.chmod(0o600)
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "another-project-9" in res["message"]
    nothing_happened(box)
    if sys.platform != "win32":
        box.key.write_text(json.dumps(key_data()))
        box.key.chmod(0o644)
        state, res = box.handle(job_of(box.bundle()))
        assert state == "refused" and "權限" in res["message"]
        nothing_happened(box)


def test_run_folder_is_under_storage_root_and_a_missing_storage_root_is_refused_in_plain_words(box):
    # TC-025, TC-042
    from abf_station import launch
    b = box.bundle()
    assert b["run_folder"] == "%s/_gcb_runs/run-a" % box.storage
    with pytest.raises(launch.BundleError) as e:
        box.bundle(facts=box.facts(storage_root=None))
    assert "storage_root" in str(e.value) and "部署設定檔" in str(e.value)


# ======================================================================================================================
# US2 - the bundle and the files
# ======================================================================================================================

def test_gcb_bundle_has_the_five_files_and_the_expected_keys(box):
    # TC-032
    b = box.bundle()
    assert set(b) == {"version", "agent", "ce", "run_name", "run_folder", "pipeline", "revision", "samplesheet", "params",
                      "path_columns", "tower", "files", "pipeline_source"}
    assert set(b["files"]) == {"samplesheet.csv", "params.yaml", "nextflow.config", "gcb.config", "head.sh"}
    assert set(b["ce"]) == {"name", "platform", "project", "location", "workDir", "spot", "bootDiskSize", "bootDiskImage",
                            "serviceAccountEmail", "network", "subnetwork", "usePrivateAddress", "labels", "maxvCpus",
                            "environment", "nextflowConfig", "preRunScript", "postRunScript"}


def test_gcb_bundle_is_identical_when_built_twice_from_the_same_inputs(box):
    # TC-033: the platform builds it from the facts the agent reported, the agent from its own settings
    from abf_station import launch
    a = box.bundle()
    b = launch.render_gcb_bundle(ce=copy.deepcopy(a["ce"]), agent="a1", facts=launch.own_facts(box.ctx), roots=[], run_name="run-a",
                                 pipeline="nf-core/rnaseq", revision="3.14.0", samplesheet=copy.deepcopy(SHEET),
                                 params={"genome": "GRCh38"}, path_columns=None)
    assert a == b


def test_gcb_config_has_exactly_the_documented_keys(box):
    # TC-034, TC-035, TC-050, TC-112
    cfg = config_keys(box.bundle()["files"]["gcb.config"])
    assert cfg == {
        "process.executor": "'google-batch'",
        "workDir": "'%s/runs/run-a/work'" % WORK,
        "google.project": "'lab-project-1'",
        "google.location": "'europe-west2'",
        "google.batch.spot": "true",
        "google.batch.bootDiskSize": "50.GB",
        "google.batch.bootDiskImage": "'batch-debian'",
        "google.batch.serviceAccountEmail": "'%s'" % EMAIL,
        "google.batch.network": "'default'",
        "google.batch.subnetwork": "'default'",
        "google.batch.usePrivateAddress": "true",
        "process.resourceLabels": "['team': 'lab', 'abf-run': 'run-a']",
        "process.resourceLimits": "[cpus: 16]",
    }
    text = box.bundle()["files"]["gcb.config"]
    for word in ("maxSpotAttempts", "queueSize", "wave", "fusion", "gpu", "accelerator", "workloadIdentity", "template"):
        assert word.lower() not in text.lower(), word
    bare = config_keys(box.bundle(ce=gce(spot=False, bootDiskSize=None, bootDiskImage=None, serviceAccountEmail=None, network=None,
                                         subnetwork=None, usePrivateAddress=False, labels={}, maxvCpus=None))["files"]["gcb.config"])
    assert "google.batch.spot" not in bare and "google.batch.usePrivateAddress" not in bare
    assert set(bare) == {"process.executor", "workDir", "google.project", "google.location", "process.resourceLabels"}


def test_boot_disk_size_is_written_in_nextflow_units(box):
    # TC-036, TC-037
    for given in ("50 GB", "50GB"):
        assert config_keys(box.bundle(ce=gce(bootDiskSize=given))["files"]["gcb.config"])["google.batch.bootDiskSize"] == "50.GB"


def test_max_vcpus_is_written_as_a_per_task_limit_and_the_screen_does_not_call_it_a_total(box):
    # TC-038, TC-067
    from abf_launch import build
    b = box.bundle(ce=gce(maxvCpus=8))
    assert config_keys(b["files"]["gcb.config"])["process.resourceLimits"] == "[cpus: 8]"
    screen = "\n".join(build.launch_screen(b, "gcb1"))
    assert "單一 task 的 cpus 上限" in screen and "總上限" not in screen and "全部 vCPU" not in screen


def test_labels_and_the_run_label_are_written_and_a_long_run_name_is_cut_to_63(box):
    # TC-039, TC-040
    cfg = config_keys(box.bundle(ce=gce(labels={"a": "b", "c": "d"}))["files"]["gcb.config"])
    assert cfg["process.resourceLabels"] == "['a': 'b', 'c': 'd', 'abf-run': 'run-a']"
    long = "r" + "x" * 63
    assert len(long) == 64
    cfg = config_keys(box.bundle(long)["files"]["gcb.config"])
    assert cfg["process.resourceLabels"].endswith("'abf-run': '%s']" % long[:63])


@pytest.mark.parametrize("field,value", [("bootDiskImage", "img'\nprocess.executor = 'local"), ("network", "x'}\nbad = 1"),
                                         ("labels", {"k": "v'\nz = 1"}), ("serviceAccountEmail", "a'b@x.iam.gserviceaccount.com"),
                                         ("project", "lab-project-1'\nx = 'y"), ("location", "europe-west2\nx = 1"),
                                         ("workDir", "gs://lab-bucket/work'\nx = 1"), ("bootDiskSize", "50 GB\nx = 1")])
def test_a_hostile_value_cannot_break_out_of_the_config_text(box, field, value):
    # TC-041
    from abf_station import launch
    with pytest.raises(launch.BundleError):
        box.bundle(ce=gce(**{field: value}))


def test_outdir_and_work_are_per_run_gs_prefixes(box):
    # TC-043
    from test_launch_bundle import parse_yaml
    b = box.bundle()
    y = parse_yaml(b["files"]["params.yaml"])
    assert y["outdir"] == "%s/runs/run-a/results" % WORK
    assert y["input"] == "%s/samplesheet.csv" % b["run_folder"] and y["genome"] == "GRCh38"
    assert config_keys(b["files"]["gcb.config"])["workDir"] == "'%s/runs/run-a/work'" % WORK
    other = config_keys(box.bundle("run-b")["files"]["gcb.config"])["workDir"]
    assert other == "'%s/runs/run-b/work'" % WORK


def test_head_script_is_the_one_that_is_shown_and_run(box):
    # TC-044, TC-045, TC-046, TC-137
    from abf_launch import build
    b, _ = launch_ok(box)
    shown = "\n".join(build.launch_screen(b, "gcb1"))
    script = b["files"]["head.sh"]
    folder = box.folder()
    assert (folder / "head.sh").read_text() == script and box.started[0]["script"] == script
    head = script.splitlines()
    assert head[0] == "#!/bin/bash" and "umask 077" in head[:4] and any(ln.startswith("cd ") and str(folder) in ln for ln in head[:6])
    assert head[-1] == ("exec nextflow run nf-core/rnaseq -r 3.14.0 -name run-a -params-file params.yaml -c nextflow.config "
                        "-c gcb.config -with-tower http://127.0.0.1:8123")
    assert "sbatch" not in script and "#SBATCH" not in script
    # everything that will be written is on the screen, line by line
    for name in ("params.yaml", "nextflow.config", "gcb.config", "head.sh"):
        for ln in b["files"][name].splitlines():
            assert ln in shown, (name, ln)
        assert (folder / name).read_text() == b["files"][name]
    for ln in ("s1,gs://lab-bucket/x.fastq.gz,auto", "sample,fastq_1,strandedness"):
        assert ln in shown
    assert (folder / "samplesheet.csv").read_text() == b["files"]["samplesheet.csv"]


def test_the_key_path_is_only_in_the_process_environment(box, monkeypatch):
    # TC-047, TC-083, TC-084
    monkeypatch.setenv("ABF_PLATFORM_SECRET_THING", "x")
    monkeypatch.setenv("ABF_STATION_OTHER", "y")
    monkeypatch.setenv("TOWER_ACCESS_TOKEN", "from-the-agent")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/somewhere/else.json")
    b, res = launch_ok(box)
    s = box.started[0]
    key = str(box.key)
    assert s["env"]["GOOGLE_APPLICATION_CREDENTIALS"] == key and s["env"]["CLOUDSDK_CORE_DISABLE_PROMPTS"] == "1"
    assert not [k for k in s["env"] if k.upper().startswith("ABF_")] and "TOWER_ACCESS_TOKEN" not in s["env"]
    assert key not in " ".join(s["argv"]) and key not in b["files"]["head.sh"] and key not in json.dumps(b) and key not in json.dumps(res)
    assert key not in (box.folder() / "head.sh").read_text()
    assert ("# credentials: the agent sets GOOGLE_APPLICATION_CREDENTIALS from its own key file; the path is not part of this script"
            in b["files"]["head.sh"].splitlines())
    for _, env in box.runs:
        assert "GOOGLE_APPLICATION_CREDENTIALS" not in env


def test_head_environment_variables_are_exported_and_compute_ones_are_not(box):
    # TC-048
    env = [{"name": "HEAD_ONLY", "value": "h1", "head": True, "compute": False},
           {"name": "COMPUTE_ONLY", "value": "c1", "head": False, "compute": True}]
    b, _ = launch_ok(box, ce=gce(environment=env))
    assert "export HEAD_ONLY=h1" in b["files"]["head.sh"] and "COMPUTE_ONLY" not in b["files"]["head.sh"]
    assert box.started[0]["env"]["HEAD_ONLY"] == "h1" and "COMPUTE_ONLY" not in box.started[0]["env"]
    from abf_station import launch
    for name in ("GOOGLE_APPLICATION_CREDENTIALS", "TOWER_ACCESS_TOKEN", "ABF_X"):
        with pytest.raises(launch.BundleError):
            box.bundle(ce=gce(environment=[{"name": name, "value": "v", "head": True, "compute": False}]))


def test_the_users_nextflow_config_stays_in_its_own_file_and_gcb_config_wins(box):
    # TC-049
    from abf_station import launch
    b = box.bundle()
    nf = b["files"]["nextflow.config"]
    assert nf.startswith("// the user's own text\nprocess.cpus = 2\n") and nf.endswith(launch.OVERWRITE_BLOCK)
    assert "google" not in nf and "user's own text" not in b["files"]["gcb.config"] and "report.overwrite" not in b["files"]["gcb.config"]
    assert b["files"]["head.sh"].splitlines()[-1].index("-c nextflow.config -c gcb.config") > 0


def test_short_network_names_are_written_as_they_are(box):
    # TC-051
    cfg = config_keys(box.bundle(ce=gce(network="default", subnetwork="default"))["files"]["gcb.config"])
    assert cfg["google.batch.network"] == "'default'" and cfg["google.batch.subnetwork"] == "'default'"


def test_samplesheet_paths_must_be_gs_urls_of_the_work_bucket(box):
    # TC-052..TC-059
    from abf_station import launch
    box.bundle()          # gs://lab-bucket/x.fastq.gz is fine
    for cell in ("/home/x.fastq.gz", "s3://lab-bucket/x", "https://lab-bucket/x", "gs://other/x", "gs://lab-bucket/../x"):
        sheet = [["sample", "fastq_1", "strandedness"], ["s1", cell, "auto"]]
        with pytest.raises(launch.BundleError) as e:
            box.bundle(samplesheet=sheet)
        assert "gcloud storage cp" in str(e.value) and "C-6" in str(e.value), cell
    # a non-path column is not judged
    box.bundle(samplesheet=[["sample", "fastq_1", "strandedness"], ["s1", "gs://lab-bucket/x.fastq.gz", "not-a-path/at-all"]])


def test_control_and_bidi_characters_in_a_path_cell_are_refused(box):
    # TC-058
    from abf_station import launch
    for cell in ("gs://lab-bucket/a\x07b", "gs://lab-bucket/a‮b", "gs://lab-bucket/a\tb", "gs://lab-bucket/a b"):
        with pytest.raises(launch.BundleError):
            box.bundle(samplesheet=[["sample", "fastq_1", "strandedness"], ["s1", cell, "auto"]])


def test_params_values_are_not_judged_as_paths(box):
    # TC-060
    b = box.bundle(params={"genome": "GRCh38", "extra": "/data/ref/reference.fa"})
    assert b["params"]["extra"] == "/data/ref/reference.fa"


def test_a_branch_is_not_a_revision(box):
    # TC-061
    from abf_station import launch
    with pytest.raises(launch.BundleError):
        box.bundle(revision="master")


# ======================================================================================================================
# US3 - the screens
# ======================================================================================================================

def test_the_screen_says_google_bills_the_lab_in_its_first_paragraph(box):
    # TC-062, TC-063, TC-064, TC-065, TC-066
    from abf_launch import build
    lines = build.launch_screen(box.bundle(), "gcb1")
    assert lines[0].endswith("送出確認：下面就是會被送出的全部內容 ==")
    sentence = ("| 費用：按下 y 之後，這個 run 會在 Google Cloud 專案 lab-project-1 裡建立 Batch 工作與虛擬機，由 Google 向實驗室的 Google Cloud "
                "帳號收費。主控程序跑在平台主機上，取消請用平台的取消指令。")
    assert lines[1] == sentence
    text = "\n".join(lines)
    assert "由 Google 向實驗室的 Google Cloud 帳號收費" in text
    assert not re.search(r"NT\$|USD|US\$|TWD|[$＄￥¥€£]\s?[0-9]|[0-9]\s?(元|美元|台幣)", text)
    for label in ("管線", "版本", "環境", "代理", "run 名稱", "專屬資料夾", "Google 專案", "區域", "工作目錄", "結果位置", "Spot",
                  "單一 task 的 cpus 上限"):
        assert re.search(r"^\| %s" % re.escape(label), text, re.M), label
    for needle in (WORK + "/runs/run-a/work", WORK + "/runs/run-a/results", "lab-project-1", "europe-west2"):
        assert needle in text
    for title in ("samplesheet.csv", "params.yaml", "nextflow.config", "gcb.config", "head.sh"):
        assert "== %s" % title in text, title
    # the per-task line is only shown when it is set
    plain = "\n".join(build.launch_screen(box.bundle(ce=gce(maxvCpus=None)), "gcb1"))
    assert "單一 task 的 cpus 上限" not in plain


def test_the_cancel_screen_says_pid_and_warns_about_leftover_jobs(box):
    # TC-068
    from abf_launch import build
    lines = build.cancel_screen(cancel_bundle(box), {"cancel_requested_at": None})
    text = "\n".join(lines)
    assert "主控程序編號（pid）: %d" % PID in text and "Slurm" not in text
    assert "Google Cloud Console" in text and "Batch" in text


def test_the_terminal_words_follow_the_environment_type_and_slurm_is_unchanged(ip, box, monkeypatch, capsys):
    # TC-069
    import argparse
    from abf_launch import cli, terminal
    row = {"slurm_job_id": PID, "run_name": "run-a", "run_folder": "/x/run-a"}
    slurm = cli._submitted_line(row)
    assert slurm == "已送出：Slurm 工作編號 4242；run 名稱 run-a；專屬資料夾 /x/run-a。"
    assert cli._submitted_line(row, GCB) == "已啟動：主控程序編號（pid）4242；run 名稱 run-a；專屬資料夾 /x/run-a。"
    # the cancel command, for a gcb run
    run_row = launch_through_platform(ip, box)
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
    assert "主控程序" in out and "Slurm 工作" not in out and "Google Cloud Console" in out


# ======================================================================================================================
# US4 - cancel
# ======================================================================================================================

def test_cancel_sends_one_sigterm_to_exactly_the_verified_process(box):
    # TC-070, TC-071, TC-080
    launch_ok(box)
    box.cancel_world()
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "done" and res["ok"] is True and res["slurm_job_id"] == PID and res["run_name"] == "run-a"
    assert box.kills == [(PID, signal.SIGTERM)]
    assert "請到 Google Cloud Console" in res["message"] and "計費" in res["message"]
    assert [a[0] for a, _ in box.runs if a[0] not in ("java", "nextflow", "gcloud")] == ["ps"]
    assert box.runs[-1][0] == ["ps", "-o", "user=", "-o", "args=", "-p", str(PID)]


def test_cancel_refuses_and_sends_nothing_when_the_process_is_gone_the_owner_differs_the_name_differs_or_the_cwd_differs(box):
    # TC-072, TC-073, TC-074, TC-075
    launch_ok(box)
    box.cancel_world()
    box.ps = (1, "")
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "refused" and "已結束" in res["message"]
    box.cancel_world(owner="someone-else")
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "refused" and "不是你的" in res["message"]
    box.cancel_world(args="/usr/bin/java nextflow.cli.Launcher run x -name run-zzz -with-tower u")
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "refused" and "-name run-a" in res["message"]
    box.cancel_world(args="/usr/bin/java nextflow.cli.Launcher run x -name run-a-longer -with-tower u")
    assert box.handle(cancel_job(cancel_bundle(box)))[0] == "refused"
    box.cancel_world(cwd="/somewhere/else")
    state, res = box.handle(cancel_job(cancel_bundle(box)))
    assert state == "refused" and "資料夾" in res["message"]
    assert box.kills == []


def test_cancel_refuses_when_head_pid_does_not_match_the_bundle(box):
    # TC-076
    launch_ok(box)
    box.cancel_world(pid=9999)
    state, res = box.handle(cancel_job(cancel_bundle(box, number=9999)))
    assert state == "refused" and box.kills == []
    (box.folder() / "head.pid").unlink()
    box.cancel_world()
    assert box.handle(cancel_job(cancel_bundle(box)))[0] == "refused" and box.kills == []


def test_cancel_refuses_an_unconfirmed_or_reused_confirmation(box):
    # TC-077, TC-078, TC-136
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


def test_cancel_does_not_trust_the_folder_in_the_bundle(box):
    # TC-079
    launch_ok(box)
    box.cancel_world()
    elsewhere = box.tmp / "other" / "_gcb_runs" / "run-a"
    state, res = box.handle(cancel_job(cancel_bundle(box, run_folder=str(elsewhere))))
    assert state == "refused" and box.kills == []
    assert box.handle(cancel_job(cancel_bundle(box, run_folder=str(box.folder()) + "/../run-a")))[0] == "refused"
    assert box.kills == []


def test_cancel_request_time_is_recorded_for_a_gcb_run(ip, box):
    # TC-081
    from abf_launch import build
    from abf_platform import actions, jobs
    launch_through_platform(ip, box)
    box.cancel_world("run-p")
    ce_name, bundle, row = build.prepare_cancel(ip.state_db, "run-p")
    cid, job_id = actions.cancel(ip.state_db, ce_name, bundle, confirmed_by=actions.TERMINAL)
    job = jobs.claim(ip.state_db, "a1", time.time, tokens_path=ip.tokens)
    state, result = box.handle(job)
    assert state == "done", result
    jobs.take_result(ip.state_db, "a1", job["id"], state, result, time.time, tokens_path=ip.tokens)
    con = sqlite3.connect(str(ip.state_db))
    assert con.execute("SELECT cancel_requested_at FROM launches WHERE run_name = 'run-p'").fetchone()[0] is not None
    con.close()


def test_cancel_needs_no_available_status(ip, box):
    # TC-082
    from abf_platform import jobs
    launch_through_platform(ip, box)
    for status in ("invalid", "creating"):
        set_status(ip, "gcb1", status, ok=0)
        jobs.check_target(ip.state_db, "gcb1", "cancel_run")
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(ip.state_db, "gcb1", "launch_nextflow")


# ======================================================================================================================
# US5 - the key stays on the host
# ======================================================================================================================

def test_no_marker_of_the_key_file_reaches_a_result_a_message_or_the_database(ip, box):
    # TC-085, TC-089, TC-090
    launch_through_platform(ip, box)
    results = []
    box.exit_code = 2
    box.out_text = "failed\n" + BEGIN + "\nMARKERPRIVATEBODY0123456789abcdef\n"
    results.append(box.handle(job_of(box.bundle("run-x")))[1])
    box.key.unlink()
    results.append(box.handle(job_of(box.bundle("run-y")))[1])
    marker = b"MARKERPRIVATEBODY"
    assert marker not in json.dumps(results).encode()
    blob = Path(str(ip.state_db)).read_bytes()
    assert marker not in blob and BEGIN.encode() not in blob and str(box.key).encode() not in blob
    con = sqlite3.connect(str(ip.state_db))
    cfg = json.loads(con.execute("SELECT config_json FROM compute_envs WHERE name = 'gcb1'").fetchone()[0])
    con.close()
    assert "credentials" not in json.dumps(cfg).lower() and "gcp-lab" not in json.dumps(cfg)


def test_head_out_is_private(box):
    # TC-089: through the real start_detached with a fake Popen
    from abf_station import site

    class FakePopen:
        pid = PID

        def __init__(self, argv, **kw):
            pass

        def poll(self):
            return None
    box.mp.setattr(site, "start_detached", box.real_start)
    box.mp.setattr(site.subprocess, "Popen", FakePopen)
    launch_ok(box)
    out = box.folder() / "head.out"
    assert out.exists()
    if sys.platform != "win32":
        assert stat.S_IMODE(out.stat().st_mode) == 0o600


def test_start_detached_uses_a_fixed_argv_no_shell_and_a_new_session(tmp_path, monkeypatch):
    # TC-134
    from abf_station import site
    seen = {}

    class FakePopen:
        pid = 7

        def __init__(self, argv, **kw):
            seen["argv"], seen["kw"] = argv, kw
    monkeypatch.setattr(site.subprocess, "Popen", FakePopen)
    out = tmp_path / "head.out"
    proc = site.start_detached(["bash", str(tmp_path / "head.sh")], {"A": "1"}, str(tmp_path), str(out))
    kw = seen["kw"]
    assert seen["argv"] == ["bash", str(tmp_path / "head.sh")] and not kw.get("shell") and kw["start_new_session"] is True
    assert kw["stdin"] == subprocess.DEVNULL and kw["env"] == {"A": "1"} and kw["cwd"] == str(tmp_path)
    assert kw["stderr"] == subprocess.STDOUT and proc.pid == 7 and out.exists()
    if sys.platform != "win32":
        assert stat.S_IMODE(out.stat().st_mode) == 0o600
    src = [p for p in (PLATFORM_DIR / "abf_station").glob("*.py") if re.search(r"\bsubprocess\b", p.read_text(encoding="utf-8"))]
    assert [p.name for p in src] == ["site.py"]


# ======================================================================================================================
# US6 - what the platform lets through
# ======================================================================================================================

def available_gcb(ip, name="gcb1", **top):
    register_agent(ip)
    create(ip, name, **top)
    set_status(ip, name, "available")


def test_check_target_lets_launch_and_cancel_through_for_an_available_gcb_environment(ip):
    # TC-093
    from abf_launch import build
    from abf_platform import jobs
    available_gcb(ip)
    jobs.check_target(ip.state_db, "gcb1", "launch_nextflow")
    jobs.check_target(ip.state_db, "gcb1", "cancel_run")
    jobs.check_target(ip.state_db, "gcb1", "preflight")
    assert build.target_problem(ip.state_db, "gcb1", "launch_nextflow") is None


def test_check_target_still_refuses_listing_fetch_and_task_log_in_plain_words(ip):
    # TC-094, TC-095, TC-096
    from abf_platform import jobs
    available_gcb(ip)
    before = jobs_count(ip)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.enqueue_listing(ip.state_db, "gcb1", "/x")
    msgs = [str(e.value)]
    for kind in ("list_site_files", "fetch_run_records", "read_task_log"):
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(ip.state_db, "gcb1", kind)
        msgs.append(str(e.value))
    for m in msgs:
        assert "尚未支援" in m and "C-2" not in m and "set an agent" not in m and "has no agent" not in m
    assert jobs_count(ip) == before


def test_launch_on_a_gcb_environment_that_is_not_available_is_refused(ip):
    # TC-097
    from abf_platform import jobs
    available_gcb(ip)
    for status in ("invalid", "creating", "disabled"):
        set_status(ip, "gcb1", status, ok=0)
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(ip.state_db, "gcb1", "launch_nextflow")


def test_primary_environment_never_auto_picks_google_batch_and_naming_it_works(ip, box):
    # TC-092, TC-098, TC-099
    from abf_launch import build
    register_with_facts(ip, box)
    create(ip)
    set_status(ip, "gcb1", "available")
    assert build.primary_environment(ip.state_db) is None
    assert ip.run("ce", "primary", "gcb1")[0] == 0
    assert build.primary_environment(ip.state_db) is None
    with pytest.raises(build.Refusal):
        build.prepare_launch(ip.state_db, pipeline="nf-core/rnaseq", revision="3.14.0", run_name="run-p",
                             samplesheet=str(sheet_file(box.tmp)), params={})
    name, bundle = prepare(ip, box)
    assert name == "gcb1" and bundle["ce"]["platform"] == GCB
    import inspect
    assert not [p for p in inspect.signature(build.prepare_launch).parameters if re.search(r"cred|key|secret", p, re.I)]


def test_another_users_gcb_environment_and_run_are_not_found_for_launch_and_cancel(ip, box):
    # TC-100, TC-101
    from abf_launch import build
    row = launch_through_platform(ip, box)
    con = sqlite3.connect(str(ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET owner_user_id = 1")
        con.execute("UPDATE agents SET owner_user_id = 1")
        con.execute("UPDATE launches SET user_id = 1 WHERE run_name = 'run-p'")
    con.close()
    with pytest.raises(build.Refusal) as e:
        prepare(ip, box, "run-q", owner=2)
    assert "not found" in str(e.value)
    with pytest.raises(build.Refusal):
        build.prepare_cancel(ip.state_db, "run-p", owner=2)
    assert build.prepare_cancel(ip.state_db, "run-p", owner=1)[0] == "gcb1"


def test_resume_and_relaunch_of_a_gcb_run_are_refused_in_plain_words(ip, box):
    # TC-102, TC-103, TC-104
    from abf_launch import build
    launch_through_platform(ip, box)
    for fn in (build.prepare_resume, build.prepare_relaunch):
        with pytest.raises(build.Refusal) as e:
            fn(ip.state_db, "run-p", index_path=str(ip.index))
        assert "Google Batch 的 run 還不能續跑或原樣重跑（尚未支援）" in str(e.value)
    origin = box.bundle("run-p")
    resume = {"version": 1, "agent": "a1", "ce": origin["ce"], "run_name": "run-p-a2", "run_folder": origin["run_folder"],
              "files": {"head-2.sh": "x\n"},
              "resume": {"of_run": "run-p", "of_slurm_job_id": PID, "session_id": "12345678-1234-1234-1234-123456789abc", "attempt": 2,
                         "origin": origin}}
    started = len(box.started)
    state, res = box.handle(job_of(resume))
    assert state == "refused" and "尚未支援" in res["message"] and len(box.started) == started


def test_fetch_run_records_does_not_list_gcb_config_as_a_record():
    # TC-105
    from abf_station import fetch
    assert "gcb.config" in fetch._NOT_RECORDS


# ======================================================================================================================
# US7 - out of scope, and no step back
# ======================================================================================================================

def test_tool_list_unchanged_and_no_new_web_route(tmp_path):
    # TC-110
    from abf_platform import web
    from abf_platform.mcp_server import build_server
    names = {t.name for t in asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())}
    assert len(names) == 21 and names == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files",
                                          "list_used_pipelines", "read_task_log", "run_outputs", "read_run_file", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation", "launch", "cancel", "resume", "relaunch", "forget"}
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"gcb|google|batch|gcp", getattr(r, "path", ""), re.I) and r.path not in {"/upload", "/upload/{batch}"}]      # web-upload-page: only the two routes this task registered are exempt (ruling 25)


def test_no_gcb_migration_is_needed_and_launches_only_gained_work_cleaned_at(ip):
    # TC-113
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
    # TC-114
    assert "google-cloud" not in (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    for f in list((PLATFORM_DIR / "abf_platform").rglob("*.py")) + list((PLATFORM_DIR / "abf_station").rglob("*.py")) + list(
            (PLATFORM_DIR / "abf_launch").rglob("*.py")):
        assert not re.search(r"^\s*(import|from)\s+(google|boto3|azure)\b", f.read_text(encoding="utf-8"), re.M), f.name


def test_the_slurm_screen_and_bundle_are_byte_identical_to_before():
    # TC-115: digests taken on the base commit of this task, for the fixed input of test_launch_bundle
    from abf_launch import build
    from test_launch_bundle import render
    b = render()
    h = lambda s: hashlib.sha256(s.encode()).hexdigest()
    assert h(json.dumps(b, sort_keys=True)) == "fcad3c22998c75125598565bcbb5ce5382a17f94fbca164d5aec62e6c39cc478"
    assert h("\n".join(build.launch_screen(b, "lab-a"))) == "020a51155f38740c5471798cb642ad1dac266b4aac2ecabb9dba56ba855cd0d4"
    assert h(b["files"]["head.sh"]) == "6432aa66c73d0f515d4475f42f93b6edf1fb4afbe5cd6c3cf2caf1f1ad5d5477"


# ======================================================================================================================
# Constitution and safety net
# ======================================================================================================================

def test_the_launch_allow_list_still_has_one_entry():
    # TC-132
    text = (REPO_ROOT / "tests" / "no_second_run_state_test.sh").read_text(encoding="utf-8")
    block = re.search(r'LAUNCH_ALLOW="\n(.*?)\n"', text, re.S).group(1)
    entries = [ln for ln in block.splitlines() if ln.strip()]
    assert len(entries) == 1 and entries[0].startswith(
        "platform/abf_station/launch.py|platform/tests/test_station_launch.py::test_unconfirmed_launch_is_refused|")


def test_the_platform_package_starts_no_program_and_holds_no_submission_word():
    # TC-109, TC-133, TC-141
    forbidden_everywhere = re.compile(r"\bnohup\b|\bsetsid\b")
    starts = re.compile(r"\bsubprocess\b|\bPopen\b|\bos\.system\b")
    submit = re.compile(r"nextflow\s+run|\bsbatch\b")
    folders = [PLATFORM_DIR / "abf_platform", PLATFORM_DIR / "abf_station"]
    for folder in folders:
        for f in folder.rglob("*.py"):
            code = [ln for ln in f.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#")]
            text = "\n".join(code)
            assert not forbidden_everywhere.search(text), f.name
            if f.name != "site.py":
                assert not starts.search(text), f.name
    assert not (PLATFORM_DIR / "abf_platform" / "local_runner.py").exists()
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        assert not submit.search("\n".join(ln for ln in f.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#"))), f.name
    gl = (PLATFORM_DIR / "abf_station" / "gcb_launch.py").read_text(encoding="utf-8")
    assert not submit.search(gl)
    # the submission word of the head script lives in launch.py only
    assert re.search(r"nextflow run", (PLATFORM_DIR / "abf_station" / "launch.py").read_text(encoding="utf-8"))


# ======================================================================================================================
# Documents
# ======================================================================================================================

def test_docs_describe_the_launch_the_billing_sentence_and_the_requirements():
    # TC-120, TC-121, TC-122, TC-124, TC-125
    d = doc("PLATFORM.md")
    assert "Slurm-like confirmed launch and cancel on the platform host (resume: not yet)" in d
    # aws-launch changed this sentence on purpose (plan A9 d): AWS Batch can run now
    assert "Slurm, Google Cloud Batch, AWS Batch, Azure Batch and Kubernetes can run; the other nine types can be modelled only" in d
    assert "Launching on Google Batch" in d
    section = d[d.index("Launching on Google Batch"):]
    for key in ("process.executor", "workDir", "google.project", "google.location", "google.batch.spot", "google.batch.bootDiskSize",
                "google.batch.bootDiskImage", "google.batch.serviceAccountEmail", "google.batch.network", "google.batch.subnetwork",
                "google.batch.usePrivateAddress", "process.resourceLabels", "process.resourceLimits"):
        assert "`%s`" % key in section, key
    for word in ("Java 17", "Nextflow", "gcloud", "storage_root", "gs://", "由 Google 向實驗室的 Google Cloud 帳號收費", "SIGTERM",
                 "Google Cloud Console", "resume", "per-task"):
        assert word in section, word
    par = doc("SEQERA_PARITY.md")
    row = [ln for ln in par.splitlines() if "`googlebatch-platform`" in ln][0]
    assert "Have (create + check + launch + cancel; resume not yet)" in row and row.rstrip().endswith("[ ] |")
    install = doc("INSTALL.md") + doc("OPERATIONS.md")
    assert "Java 17" in install and "Nextflow" in install and "gcloud" in install
    for text in (d, par, doc("TESTING.md"), install):
        assert not re.findall(r"[a-z0-9-]+@(?!lab-project-1)[a-z0-9-]+\.iam\.gserviceaccount\.com", text)
    t = doc("TESTING.md")
    assert "gcb-launch" in t and "git diff --name-only" in t



# ======================================================================================================================
# cloud-ce-memory-cap (gcb): maxMemoryGB and the merge with the user's own resourceLimits
# ======================================================================================================================

def _cap_limit(box, config_text="", **over):
    ce = gce(nextflowConfig=config_text, **over)
    return config_keys(box.bundle(ce=ce)["files"]["gcb.config"]).get("process.resourceLimits")


def test_cap_original_case_real_failure_and_memory_only(box):
    # TC-010 (original trial case), TC-022 (the user's memory key is kept), TC-013 (memory only), TC-019 (the cpus-only line stays)
    assert _cap_limit(box, maxvCpus=4, maxMemoryGB=6) == "[cpus: 4, memory: 6.GB]"
    assert _cap_limit(box, "process.resourceLimits = [cpus: 4, memory: 6.GB]\n", maxvCpus=4) == "[cpus: 4, memory: 6.GB]"
    assert _cap_limit(box, maxvCpus=None, maxMemoryGB=6) == "[memory: 6.GB]"
    assert _cap_limit(box, maxvCpus=16) == "[cpus: 16]"
    assert box.bundle(ce=gce(maxMemoryGB=6))["ce"]["maxMemoryGB"] == 6
    assert "maxMemoryGB" not in box.bundle()["ce"]


def test_cap_snapshot_ce_and_bad_values(box):
    # TC-017, TC-018
    from abf_station import launch
    view = {"name": "x", "platform": GCB, "config": {"project": PROJECT, "location": "europe-west2", "workDir": "gs://lab-bucket/work"}}
    on = launch.snapshot_ce({"name": "x", "platform": GCB, "config": dict({"project": PROJECT, "location": "europe-west2", "workDir": "gs://lab-bucket/work"}, maxMemoryGB=6)})
    assert on["maxMemoryGB"] == 6 and "maxMemoryGB" not in launch.snapshot_ce(view)
    for bad in (0, 10001, True, "8", 1.5):
        with pytest.raises(launch.BundleError) as e:
            box.bundle(ce=gce(maxMemoryGB=bad))
        assert "maxMemoryGB" in str(e.value), bad


def test_cap_unreadable_user_limits_are_refused_and_no_limit_is_left_alone(box):
    # TC-046, TC-039
    from abf_station import launch
    shapes = ("resourceLimits = [\n  cpus: 4\n]\n", "process.resourceLimits = [cpus: 4]\nprocess.resourceLimits = [cpus: 2]\n",
              "process { resourceLimits { cpus = 4 } }\n", "resourceLimits = [cpus: params.c]\n", "resourceLimits = [cpus: 4, gpus: 1]\n")
    for text in shapes:
        with pytest.raises(launch.BundleError) as e:
            box.bundle(ce=gce(maxvCpus=4, nextflowConfig="// MY-MARKER-LINE\n" + text))
        assert "resourceLimits" in str(e.value) and "MY-MARKER-LINE" not in str(e.value) and "maxMemoryGB" in str(e.value)
    keep = "process.resourceLimits = [cpus: 2, memory: 4.GB]\n"
    b = box.bundle(ce=gce(maxvCpus=None, nextflowConfig=keep))
    assert "resourceLimits" not in b["files"]["gcb.config"] and keep in b["files"]["nextflow.config"]


def test_cap_screen_row_only_when_set(box):
    # TC-056, TC-057
    from abf_launch import build
    on = "\n".join(build.launch_screen(box.bundle(ce=gce(maxMemoryGB=6)), "gcb1"))
    assert "單一 task 的記憶體上限" in on and "單一 task 的 cpus 上限" in on
    assert "記憶體上限" not in "\n".join(build.launch_screen(box.bundle(), "gcb1"))
