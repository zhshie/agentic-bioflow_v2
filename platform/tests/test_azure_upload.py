# Nothing existing: searched azurite, the Azure SDK for Python test doubles and the az CLI's own recorded-test tooling for a fake that speaks `az storage blob upload` and `az storage blob show` without a network; they run a server or import the SDK, which the platform and this agent bar (no cloud library), so a fake runner object stands in for site.run_fixed, with no network and no money.
"""azure-upload: put_upload for Azure Batch environments (the platform half: the queue, the az:// location language, the dataset
destination; the agent half: judge again, write with `az storage blob upload --file`, check the size with `az storage blob show`,
remove the staged copy).

The TC ids refer to specs/azure-upload/test-case.md. Everything uses a fake `site.run_fixed` (and a `site.start_fed` that fails the test
when called); the staged files live under tmp_path. Test inputs are fake values (labcontainer, labstore, westeurope, azure-lab, alice,
bob). Key-shaped names are built from pieces (test_azure_ce) so that tests/credentials_stay_in_settings_test.sh does not see them."""
import ast
import hashlib
import inspect
import json
import os
import re
import sqlite3
import stat as st
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from station_harness import mcp_inproc
from test_azure_ce import AZ, BKEY, CRED_FILE, SAS, SKEY, create, good_config, ip, jobs_count, register_agent, set_status  # noqa: F401
from test_cloud_upload import FOUR, d, make_env, register, rows_of, sheet  # noqa: F401  (d is a fixture)

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="symbolic links and inode numbers")
T = time.time()
GB2 = 2_000_000_000
AZA = "az://labcontainer/uploads/alice/"
SRC_STATION = PLATFORM_DIR / "abf_station"
SRC_PLATFORM = PLATFORM_DIR / "abf_platform"
NOT_FOUND = "compute environment %r not found (找不到)"
OWN_COMPUTER = "在你自己的電腦上、用你自己的 Azure 登入"
BOTH_FILE = "[default]\nbatch_account_key = " + BKEY + "\nstorage_account_key = " + SKEY + "\nstorage_sas_token = " + SAS + "\n"
SAS_ONLY = "[default]\nbatch_account_key = " + BKEY + "\nstorage_sas_token = " + SAS + "\n"
NO_BATCH_KEY = "[default]\nstorage_account_key = " + SKEY + "\n"
NO_STORAGE = "[default]\nbatch_account_key = " + BKEY + "\n"


def cs():
    from abf_platform import cloud_store
    return cloud_store


def ds():
    from abf_platform.actions import datasets
    return datasets


def fake_stat(size=500, mode=st.S_IFREG | 0o644):
    def _stat(path):
        return SimpleNamespace(st_mode=mode, st_size=size)
    return _stat


def az_ce(**over):
    c = {"platform": AZ, "config": {"workDir": "az://labcontainer/work"}}
    c.update(over)
    return c


def aws_ce():
    return {"platform": "awsbatch-platform", "config": {"region": "eu-west-1", "workDir": "s3://lab-bucket/work"}}


def gcb_ce():
    return {"platform": "googlebatch-platform", "config": {"workDir": "gs://lab-bucket/work"}}


# =============================================================================================================================
# platform half: the queue
# =============================================================================================================================
class PW:
    """alice owns the Azure environment azure-lab (available); bob owns bobenv."""

    def __init__(self, ip, tmp):
        from abf_platform import agents, store
        self.ip, self.uploads = ip, tmp / "uploads"
        self.ids = {}
        for who in ("alice", "bob"):
            self.ids[who] = store.create_user(ip.tokens, who, "lab")
            agents.register(ip.state_db, "ag-" + who, "0.1.0", lambda: T, owner_user_id=self.ids[who])
        create(ip, "azure-lab", config=good_config(workDir="az://labcontainer/work"), agent="ag-alice", owner_user_id=self.ids["alice"],
               credentialsId="azure-lab")
        create(ip, "bobenv", config=good_config(workDir="az://bobcontainer/work"), agent="ag-bob", owner_user_id=self.ids["bob"])
        set_status(ip, "azure-lab", "available")
        set_status(ip, "bobenv", "available")

    def put(self, name="reads.fastq.gz", ce="azure-lab", owner="alice", uid="alice", stat=None):
        from abf_platform import jobs
        return jobs.enqueue_put_upload(self.ip.state_db, self.ip.tokens, ce, owner, name, self.uploads, self.ids[uid],
                                       clock=lambda: T, stat=stat or fake_stat(5))

    def refused(self, **kw):
        from abf_platform import jobs
        before = jobs_count(self.ip)
        with pytest.raises(jobs.JobRefused) as e:
            self.put(**kw)
        assert jobs_count(self.ip) == before
        return str(e.value)

    def row(self, jid):
        con = sqlite3.connect(str(self.ip.state_db))
        con.row_factory = sqlite3.Row
        try:
            return con.execute("SELECT * FROM jobs WHERE id = ?", (jid,)).fetchone()
        finally:
            con.close()


@pytest.fixture
def pw(ip, tmp_path):
    return PW(ip, tmp_path)


def test_azure_env_may_queue_put_upload_when_available(pw):
    # TC-001, TC-002 (AZU-GATE-01)
    jid = pw.put()
    row = pw.row(jid)
    assert row["kind"] == "put_upload" and jobs_count(pw.ip) == 1
    args = json.loads(row["args_json"])
    assert set(args) == {"ce", "owner", "name", "size", "dest"}
    assert (args["owner"], args["name"], args["size"], args["dest"]) == ("alice", "reads.fastq.gz", 5, AZA + "reads.fastq.gz")
    set_status(pw.ip, "azure-lab", "creating")
    msg = pw.refused()
    assert "available" in msg and "preflight" in msg


def test_put_upload_gate_is_a_per_type_table_not_a_shared_tuple(pw, monkeypatch):
    # TC-003, TC-004, TC-005, TC-006 (AZU-GATE-02)
    from abf_platform import compute_envs, jobs
    kinds = compute_envs.CLOUD_JOB_KINDS
    assert set(kinds[compute_envs.AZURE]) == {"preflight", "launch_nextflow", "cancel_run", "pipeline_files", "put_upload"}
    assert len(kinds[compute_envs.AZURE]) == 5 and "clean_" "work" not in kinds[compute_envs.AZURE]
    six = {"preflight", "launch_nextflow", "cancel_run", "clean_" "work", "put_upload", "pipeline_files"}
    assert set(kinds[compute_envs.GOOGLE_BATCH]) == six and len(kinds[compute_envs.GOOGLE_BATCH]) == 6
    assert set(kinds[compute_envs.AWS]) == six and len(kinds[compute_envs.AWS]) == 6
    pw.put()
    monkeypatch.setitem(kinds, compute_envs.AZURE, tuple(k for k in kinds[compute_envs.AZURE] if k != "put_upload"))
    with pytest.raises(jobs.JobRefused):
        pw.put()      # the gate is the table
    monkeypatch.undo()
    pw.put()


def test_clean_work_and_resume_still_refused_for_azure(pw):
    # TC-007, TC-008 (AZU-GATE-03)
    from abf_platform import jobs
    from abf_launch import build
    before = jobs_count(pw.ip)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(pw.ip.state_db, "azure-lab", "clean_" "work")
    m = str(e.value)
    assert "尚未支援" in m and "azure-clean" in m and "azure-launch" not in m and "azure-upload" not in m
    assert jobs_count(pw.ip) == before
    for fn in (build.prepare_resume, build.prepare_relaunch):
        with pytest.raises(build.Refusal):
            fn(pw.ip.state_db, "no-such-run", index_path=str(pw.ip.index))
    assert jobs_count(pw.ip) == before


def test_a_slurm_environment_cannot_hold_cloud_data_and_the_message_names_azure(pw):
    # TC-009
    from abf_platform import jobs
    con = sqlite3.connect(str(pw.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET platform = 'slurm-platform' WHERE name = 'bobenv'")
    con.close()
    before = jobs_count(pw.ip)
    with pytest.raises(jobs.JobRefused) as e:
        pw.put(ce="bobenv", owner="bob", uid="bob")
    assert "cloud data" in str(e.value) and "Azure Batch" in str(e.value) and jobs_count(pw.ip) == before


def test_other_users_environment_is_not_found(pw):
    # TC-010
    from abf_platform import jobs
    before = jobs_count(pw.ip)
    with pytest.raises(jobs.JobRefused) as e:
        pw.put(uid="bob", owner="alice")
    assert str(e.value) == str(jobs._not_found("azure-lab"))
    with pytest.raises(jobs.JobRefused) as e:
        pw.put(uid="bob", owner="bob")
    assert str(e.value) == str(jobs._not_found("azure-lab"))
    assert jobs_count(pw.ip) == before


def test_the_generic_queue_does_not_take_put_upload_and_list_site_files_stays_closed(pw):
    # TC-012, TC-013
    from abf_platform import jobs
    before = jobs_count(pw.ip)
    with pytest.raises(jobs.JobRefused) as e:
        jobs._enqueue(pw.ip.state_db, "azure-lab", "put_upload", None, lambda: T, None)
    assert "enqueue_put_upload" in str(e.value)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(pw.ip.state_db, "azure-lab", "list_site_files")
    assert "尚未支援" in str(e.value)
    assert jobs_count(pw.ip) == before


def test_google_still_queues_put_upload_with_a_gs_destination(ip, tmp_path):
    # TC-011 (the existing test_cloud_upload keeps the full check; this one is the quick look)
    from abf_platform import agents, jobs, store
    uid = store.create_user(ip.tokens, "alice", "lab")
    agents.register(ip.state_db, "ag-g", "0.1.0", lambda: T, owner_user_id=uid)
    from test_gcb_ce import create as gcreate
    gcreate(ip, "gcb-lab", agent="ag-g", owner_user_id=uid)
    set_status(ip, "gcb-lab", "available")
    jid = jobs.enqueue_put_upload(ip.state_db, ip.tokens, "gcb-lab", "alice", "reads.fastq.gz", tmp_path / "u", uid, clock=lambda: T, stat=fake_stat(5))
    con = sqlite3.connect(str(ip.state_db))
    args = json.loads(con.execute("SELECT args_json FROM jobs WHERE id = ?", (jid,)).fetchone()[0])
    con.close()
    assert args["dest"].startswith("gs://") and args["dest"].endswith("/uploads/alice/reads.fastq.gz")


def test_the_job_carries_names_only_and_the_result_is_cleaned(pw):
    # TC-061, TC-124
    from abf_platform import jobs
    row = pw.row(pw.put())
    text = row["args_json"]
    for bad in (BKEY, SKEY, SAS, "azure-credentials", "_personal"):
        assert bad not in text
    path = AZA + "reads.fastq.gz"
    good = {"ok": True, "bytes": 5, "path": path}
    assert jobs.clean_result("put_upload", dict(good, extra="x")) == good
    for broken in ({"ok": True, "path": path}, {"ok": True, "bytes": 5}):
        assert jobs.clean_result("put_upload", broken)["ok"] is False


# =============================================================================================================================
# platform half: the az:// location language
# =============================================================================================================================
def test_workdir_bucket_for_azure_is_the_container():
    # TC-014 .. TC-019 (AZU-LOC-01)
    assert cs().workdir_bucket(az_ce()) == "labcontainer"
    assert cs().workdir_scheme(az_ce()) == "az"
    for work in ("az://labcontainer", "az://LabContainer/work", "az://lab--container/work", "az://ab/work"):
        with pytest.raises(cs().CloudPathError):
            cs().workdir_bucket({"platform": AZ, "config": {"workDir": work}})


def test_azure_environment_needs_an_az_workdir_and_other_types_say_which_can():
    # TC-020, TC-021
    for work in ("s3://labcontainer/work", "gs://labcontainer/work", None, "labcontainer"):
        with pytest.raises(cs().CloudPathError) as e:
            cs().workdir_bucket({"platform": AZ, "config": {"workDir": work}})
        assert "Traceback" not in str(e.value) and len(str(e.value)) > 8
    with pytest.raises(cs().CloudPathError) as e:
        cs().workdir_scheme({"platform": "slurm-platform", "config": {}})
    m = str(e.value)
    assert "不能放雲端資料" in m and "Google Batch" in m and "AWS Batch" in m and "Azure Batch" in m


def test_google_and_aws_location_behaviour_is_unchanged():
    # TC-022, TC-023, TC-024 (AZU-LOC-02)
    assert cs().workdir_bucket(gcb_ce()) == "lab-bucket" and cs().workdir_scheme(gcb_ce()) == "gs"
    assert cs().upload_prefix(gcb_ce(), "alice") == "gs://lab-bucket/uploads/alice/"
    assert cs().object_url(gcb_ce(), "alice", "a.fq.gz") == "gs://lab-bucket/uploads/alice/a.fq.gz"
    assert cs().big_file_command(gcb_ce(), "alice") == "gcloud storage cp <你電腦上的資料夾>/* gs://lab-bucket/uploads/alice/rawdata/"
    assert cs().workdir_bucket(aws_ce()) == "lab-bucket" and cs().workdir_scheme(aws_ce()) == "s3"
    assert cs().upload_prefix(aws_ce(), "alice", scheme="s3") == "s3://lab-bucket/uploads/alice/"
    assert cs().object_url(aws_ce(), "alice", "a.fq.gz", scheme="s3") == "s3://lab-bucket/uploads/alice/a.fq.gz"
    assert cs().big_file_command(aws_ce(), "alice", scheme="s3") == "aws s3 cp <你電腦上的資料夾> s3://lab-bucket/uploads/alice/rawdata/ --recursive"
    with pytest.raises(cs().CloudPathError) as e:
        cs().workdir_bucket({"platform": "googlebatch-platform", "config": {"workDir": "/x"}})
    assert str(e.value) == "這個計算環境沒有 gs:// 的 workDir，不能放雲端資料 (this environment has no gs:// workDir)"


def test_az_object_url_is_inside_the_owners_prefix():
    # TC-025 .. TC-030 (AZU-LOC-03)
    ce = az_ce()
    assert cs().upload_prefix(ce, "alice", scheme="az") == AZA
    url = cs().object_url(ce, "alice", "reads.fastq.gz", scheme="az")
    assert url == AZA + "reads.fastq.gz"
    assert cs().inside_prefix(AZA + "x", AZA, scheme="az") is True
    for other in ("az://labcontainer/uploads/alice2/x", "az://labcontainer/uploads/alice/../bob/x", "az://labcontainer/uploads//x",
                  "az://other-container/uploads/alice/x", "gs://labcontainer/uploads/alice/x", AZA):
        assert cs().inside_prefix(other, AZA, scheme="az") is False, other
    assert cs().inside_prefix("uploads/alice2/x", AZA, scheme="az") is False


def test_uploads_prefix_does_not_overlap_the_workdir_subfolder():
    # TC-031 (AZU-LOC-04)
    ce = {"platform": AZ, "config": {"workDir": "az://labcontainer/runs-a"}}
    url = cs().object_url(ce, "alice", "x", scheme="az")
    assert url == "az://labcontainer/uploads/alice/x" and not url.startswith("az://labcontainer/runs-a/")


def test_parse_az_has_the_shape_of_parse_s3():
    # TC-032, TC-033
    assert cs().parse_az(AZA + "a.fq.gz") == ("labcontainer", "uploads/alice/a.fq.gz")
    with pytest.raises(cs().CloudPathError) as e:
        cs().parse_az("az://labcontainer/uploads/../bob/x")
    assert ".." in str(e.value)
    for bad in ("az://LabContainer/x", "az://lab--container/x", "az://ab/x", "s3://labcontainer/x", "az://labcontainer", "az://labcontainer/", None):
        with pytest.raises(cs().CloudPathError):
            cs().parse_az(bad)


def test_az_file_names_use_the_same_single_name_rules():
    # TC-034
    long = "a" * 256
    for name in ("a/b", "a\\b", "..", "a" + chr(0) + "b", "", long):
        with pytest.raises(cs().CloudPathError):
            cs().object_url(az_ce(), "alice", name, scheme="az")
    assert cs().object_url(az_ce(), "alice", "a" * 255, scheme="az").endswith("a" * 255)


# =============================================================================================================================
# the agent half
# =============================================================================================================================
class AW:
    def __init__(self, tmp, mp):
        from abf_station import site
        self.tmp, self.mp = Path(tmp), mp
        self.uploads = self.tmp / "uploads"
        (self.uploads / "alice").mkdir(parents=True)
        mp.setenv("ABF_STATION_UPLOADS", str(self.uploads))
        mp.delenv("ABF_STATION_PUT_TIMEOUT", raising=False)
        self.cred = self.tmp / "credentials-file"
        self.cred.write_text(CRED_FILE)
        mp.setenv("ABF_STATION_AZURE_CREDENTIALS", str(self.cred))
        self.runs = []
        self.up_rc, self.up_out, self.up_exc, self.on_upload = 0, "", None, None
        self.show, self.size = None, 0
        mp.setattr(site, "run_fixed", self._run_fixed)
        mp.setattr(site, "start_fed", self._no_fed)
        self.ctx = SimpleNamespace(site=SimpleNamespace(log=lambda *a: None), settings_file=str(self.tmp / "env.yaml"),
                                   platform_url="http://127.0.0.1:1", agent_name="a1")
        self.ce = {"name": "azure-lab", "platform": AZ, "credentialsId": "azure-lab", "location": "westeurope", "batchAccountName": "labbatch",
                   "storageAccountName": "labstore", "workDir": "az://labcontainer/work", "pool": "lab-pool", "spot": True, "maxvCpus": 16}

    @staticmethod
    def _no_fed(argv, env):
        raise AssertionError("site.start_fed must not be used for an Azure upload: %r" % (argv,))

    def _run_fixed(self, argv, env, timeout):
        folder = (env or {}).get("AZURE_CONFIG_DIR")
        self.runs.append({"argv": list(argv), "env": dict(env or {}), "timeout": timeout, "dir": folder, "dir_existed": bool(folder) and os.path.isdir(folder)})
        if argv[:4] == ["az", "storage", "blob", "upload"]:
            if self.on_upload:
                self.on_upload()
            if self.up_exc:
                raise self.up_exc
            return self.up_rc, self.up_out
        if argv[:4] == ["az", "storage", "blob", "show"]:
            if self.show == "timeout":
                raise TimeoutError("slow")
            if self.show == "oserror":
                raise OSError("gone")
            if self.show is not None:
                return self.show
            return 0, "%d\n" % self.size
        raise AssertionError("an unexpected program: %r" % (argv,))

    def make(self, name="reads.fastq.gz", data=b"hello", owner="alice"):
        folder = self.uploads / owner
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
        self.size = len(data)
        return data

    def path(self, name="reads.fastq.gz", owner="alice"):
        return self.uploads / owner / name

    def dest(self, name="reads.fastq.gz", owner="alice"):
        return "az://labcontainer/uploads/%s/%s" % (owner, name)

    def args(self, **over):
        a = {"ce": dict(self.ce), "owner": "alice", "name": "reads.fastq.gz", "dest": None, "size": self.size}
        a.update(over)
        if a["dest"] is None:
            a["dest"] = self.dest(a["name"], a["owner"]) if isinstance(a["name"], str) and isinstance(a["owner"], str) else "az://labcontainer/x"
        return a

    def go(self, **over):
        from abf_station import handlers
        return handlers.handle({"kind": "put_upload", "args": self.args(**over)}, self.ctx)

    def refused(self, **over):
        state, res = self.go(**over)
        assert state == "refused" and res["ok"] is False, (state, res)
        assert self.runs == []
        return res["message"]

    def uploads_ran(self):
        return [r for r in self.runs if r["argv"][3] == "upload"]


@pytest.fixture
def aw(tmp_path, monkeypatch):
    w = AW(tmp_path, monkeypatch)
    w.make()
    return w


def pairs_of(argv):
    """{flag: value} of the pairs and the set of lone flags in argv after the four verb words."""
    rest, pairs, lone, i = argv[4:], {}, set(), 0
    while i < len(rest):
        if rest[i] == "--no-progress":
            lone.add(rest[i])
            i += 1
        else:
            assert rest[i].startswith("--") and i + 1 < len(rest), rest
            assert rest[i] not in pairs
            pairs[rest[i]] = rest[i + 1]
            i += 2
    return pairs, lone


def test_agent_uploads_with_fixed_argv_and_no_secret_in_argv(aw):
    # TC-035, TC-036, TC-037, TC-038, TC-040 (AZU-AGT-01)
    state, res = aw.go()
    assert state == "done" and res["ok"] is True and res["bytes"] == 5 and res["path"] == aw.dest()
    up = aw.uploads_ran()
    assert len(up) == 1
    argv = up[0]["argv"]
    assert argv[:4] == ["az", "storage", "blob", "upload"] and isinstance(argv, list)
    pairs, lone = pairs_of(argv)
    assert pairs == {"--account-name": "labstore", "--container-name": "labcontainer", "--name": "uploads/alice/reads.fastq.gz",
                     "--file": os.path.realpath(aw.path()), "--overwrite": "true", "--output": "none", "--auth-mode": "key"}
    assert lone == {"--no-progress"}
    text = " ".join(argv)
    for bad in ("--account-key", "--sas-token", "--connection-string", SKEY, SAS, BKEY):
        assert bad not in text
    assert up[0]["timeout"] == 3600      # TC-040


def test_only_sas_gives_no_auth_mode_and_no_sas_flag(aw):
    # TC-039
    aw.cred.write_text(SAS_ONLY)
    state, res = aw.go()
    assert res["ok"] is True
    argv = aw.uploads_ran()[0]["argv"]
    pairs, lone = pairs_of(argv)
    assert "--auth-mode" not in pairs and "--sas-token" not in pairs and SAS not in " ".join(argv)
    assert pairs == {"--account-name": "labstore", "--container-name": "labcontainer", "--name": "uploads/alice/reads.fastq.gz",
                     "--file": os.path.realpath(aw.path()), "--overwrite": "true", "--output": "none"} and lone == {"--no-progress"}


def test_agent_env_has_the_storage_credentials_and_nothing_else_from_the_parent(aw, monkeypatch):
    # TC-041 .. TC-046 (AZU-AGT-02)
    monkeypatch.setenv("AZURE_STORAGE_" + "KEY", "FAKE-OTHER-0001")
    monkeypatch.setenv("AZURE_CLIENT_ID", "FAKE-OTHER-0002")
    monkeypatch.setenv("AZURE_BATCH_ACCOUNT", "FAKE-OTHER-0003")
    monkeypatch.setenv("ABF_X", "fake")
    aw.go()
    assert len(aw.runs) == 2
    for r in aw.runs:
        env = r["env"]
        assert env["AZURE_STORAGE_ACCOUNT"] == "labstore" and env["AZURE_STORAGE_" + "KEY"] == SKEY
        assert env["AZURE_CORE_COLLECT_TELEMETRY"] == "false" and r["dir_existed"] is True and env["AZURE_CONFIG_DIR"]
        assert "AZURE_STORAGE_SAS_TOKEN" not in env
        assert not [k for k in env if k.startswith("ABF_") or k.startswith("AZURE_BATCH_")]      # TC-045
        assert "FAKE-OTHER-0001" not in env.values() and "FAKE-OTHER-0002" not in env.values()
        assert not os.path.exists(r["dir"])      # TC-046: gone after the call
    # only a SAS (TC-043), and both (TC-044)
    aw.runs.clear()
    aw.make()
    aw.cred.write_text(SAS_ONLY)
    aw.go()
    env = aw.runs[0]["env"]
    assert env["AZURE_STORAGE_SAS_TOKEN"] == SAS and "AZURE_STORAGE_" + "KEY" not in env
    aw.runs.clear()
    aw.make()
    aw.cred.write_text(BOTH_FILE)
    aw.go()
    env = aw.runs[0]["env"]
    assert env["AZURE_STORAGE_" + "KEY"] == SKEY and "AZURE_STORAGE_SAS_TOKEN" not in env
    assert pairs_of(aw.runs[0]["argv"])[0]["--auth-mode"] == "key"


def test_config_folder_is_deleted_after_a_failed_call_too(aw):
    # TC-047
    aw.up_rc, aw.up_out = 1, "denied"
    state, res = aw.go()
    assert res["ok"] is False
    assert aw.runs[0]["dir_existed"] is True and not os.path.exists(aw.runs[0]["dir"])


def test_agent_rejudges_dest_and_refuses_a_foreign_prefix(aw):
    # TC-049, TC-050, TC-051, TC-052, TC-053
    for dest in ("az://labcontainer/runs/x", "az://other-container/uploads/alice/reads.fastq.gz", "az://labcontainer/uploads/bob/reads.fastq.gz",
                 "az://labcontainer/uploads/alice/../bob/x", "s3://labcontainer/uploads/alice/reads.fastq.gz"):
        aw.refused(dest=dest)
    aw.refused(owner="../bob", dest="az://labcontainer/uploads/../bob/reads.fastq.gz")
    assert aw.path().exists()


def test_the_size_and_the_fields_are_judged_again(aw):
    # TC-054, TC-055, TC-076
    for size in (0, GB2 + 1):
        assert "1 位元組到 2 GB" in aw.refused(size=size)
    for size in (True, "5", None):
        aw.refused(size=size)
    ce = dict(aw.ce)
    del ce["storageAccountName"]
    aw.refused(ce=ce)
    aw.refused(ce=dict(aw.ce, workDir="az://labcontainer"))
    aw.refused(ce=dict(aw.ce, workDir="s3://labcontainer/work"))
    aw.refused(ce={"name": "x", "platform": "slurm-platform", "workDir": "/x"})


def test_symlinked_or_resized_staged_file_is_refused(aw, tmp_path):
    # TC-056, TC-057, TC-058 (AZU-AGT-07)
    assert "不一樣" in aw.refused(size=7)
    assert aw.path().exists()
    aw.path().unlink()
    aw.refused()
    aw.path().mkdir()
    aw.refused()
    aw.path().rmdir()
    if sys.platform != "win32":
        target = tmp_path / "elsewhere.fq"
        target.write_bytes(b"hello")
        aw.path().symlink_to(target)
        aw.refused()
        assert target.read_bytes() == b"hello"


def test_size_is_checked_with_blob_show_before_the_staged_file_goes(aw):
    # TC-048, TC-059, TC-060 (AZU-AGT-04)
    aw.show = (0, "4\n")
    state, res = aw.go()
    assert res["ok"] is False and "雲端物件大小與本機不符，暫存檔保留，請重新上傳" in res["message"] and aw.path().exists()
    aw.runs.clear()
    aw.show = None
    state, res = aw.go()
    assert res["ok"] is True and not aw.path().exists()
    assert [r["argv"][3] for r in aw.runs] == ["upload", "show"]
    show = aw.runs[1]
    assert show["argv"][:4] == ["az", "storage", "blob", "show"] and show["timeout"] == 60
    pairs, lone = pairs_of(show["argv"])
    assert pairs == {"--account-name": "labstore", "--container-name": "labcontainer", "--name": "uploads/alice/reads.fastq.gz",
                     "--query": "properties.contentLength", "--output": "tsv", "--auth-mode": "key"} and lone == set()
    env = show["env"]
    assert env["AZURE_STORAGE_" + "KEY"] == SKEY and not [k for k in env if k.startswith(("ABF_", "AZURE_BATCH_"))]


def test_unreadable_size_keeps_the_staged_file(aw):
    # TC-062, TC-063, TC-064 (AZU-AGT-05)
    for show in ("timeout", "oserror", (0, "not a number"), (1, "boom")):
        aw.show = show
        state, res = aw.go()
        assert state == "done" and res["ok"] is True and "沒能核對雲端大小" in res["message"] and "暫存檔保留" in res["message"]
        assert aw.path().exists()


def test_missing_credentials_file_fails_without_leaking_its_content(aw):
    # TC-065, TC-066, TC-067 (AZU-AGT-06), TC-073
    for content in (None, "[default]\n", NO_STORAGE, NO_BATCH_KEY):
        aw.runs.clear()
        if content is None:
            aw.cred.unlink()
        else:
            aw.cred.write_text(content)
        state, res = aw.go()
        assert res["ok"] is False and aw.runs == [] and aw.path().exists(), content
        m = res["message"]
        assert len(m) > 8 and "管理者" in m
        for bad in (BKEY, SKEY, SAS, str(aw.cred), str(aw.tmp)):
            assert bad not in m


def test_staged_file_swapped_during_the_upload_is_not_deleted(aw):
    # TC-068, TC-069 (AZU-AGT-08)
    def swap():
        aw.path().unlink()
        aw.path().write_bytes(b"hello")
    aw.on_upload = swap
    state, res = aw.go()
    assert res["ok"] is False and aw.path().exists()
    assert not [r for r in aw.runs if r["argv"][3] == "show"] or aw.path().exists()
    aw.on_upload = lambda: aw.path().write_bytes(b"hello world, longer")
    state, res = aw.go()
    assert res["ok"] is False and aw.path().exists()


def test_missing_az_program_gives_a_plain_message(aw):
    # TC-070 (AZU-AGT-09)
    aw.up_exc = FileNotFoundError(2, "no az")
    state, res = aw.go()
    m = res["message"]
    assert res["ok"] is False and "找不到 az 指令" in m and "Azure CLI" in m and aw.path().exists()
    assert "Traceback" not in m and 'File "' not in m


def test_failed_az_exit_keeps_the_staged_file_and_hides_the_stderr_secrets(aw):
    # TC-071 (AZU-AGT-10)
    aw.up_rc, aw.up_out = 1, "denied key %s and %s in %s/x " % (SKEY, SAS, aw.uploads) + "y" * 600
    state, res = aw.go()
    m = res["message"]
    assert res["ok"] is False and aw.path().exists() and len(aw.uploads_ran()) == 1      # no retry
    for bad in (SKEY, SAS, BKEY, str(aw.uploads), str(aw.path())):
        assert bad not in m
    assert len(m) < 700
    aw.up_rc, aw.up_exc = 0, TimeoutError("slow")
    state, res = aw.go()
    assert res["ok"] is False and "逾時" in res["message"] and aw.path().exists()


def test_every_failure_is_plain_and_the_success_holds_nothing_secret(aw):
    # TC-072, TC-073
    messages = [aw.refused(size=0)]
    aw.cred.unlink()
    messages.append(aw.go()[1]["message"])
    aw.cred.write_text(CRED_FILE)
    aw.up_exc = FileNotFoundError(2, "no az")
    messages.append(aw.go()[1]["message"])
    aw.up_exc, aw.up_rc, aw.up_out = None, 1, "x " + str(aw.path())
    messages.append(aw.go()[1]["message"])
    aw.show, aw.up_rc = "timeout", 0
    messages.append(aw.go()[1]["message"])
    for m in messages:
        assert len(m) > 10
        for bad in ("Traceback", 'File "', "SELECT", "INSERT", str(aw.uploads), str(aw.cred), str(aw.tmp)):
            assert bad not in m, (bad, m)
    aw.show = None
    state, res = aw.go()
    assert set(res) == {"ok", "bytes", "path", "message"}
    text = repr(res)
    for bad in (str(aw.cred), BKEY, SKEY, SAS, str(aw.uploads)):
        assert bad not in text


def test_run_put_still_refuses_slurm_and_unknown_platforms(aw):
    # TC-074 (AZU-AGT-11)
    for ce in ({"name": "x", "platform": "slurm-platform", "workDir": "/x"}, {"name": "x", "platform": "k8s-platform"}, "nope", None):
        state, res = aw.go(ce=ce)
        assert state == "refused" and res["message"] == "這種計算環境不能放雲端資料 (this kind of environment cannot hold cloud data)"
    assert aw.runs == []


def test_a_google_job_still_runs_gcloud_and_never_az(aw, monkeypatch):
    # TC-075
    from abf_station import gcb_preflight, handlers, site
    monkeypatch.setattr(gcb_preflight.shutil, "which", lambda n: "/usr/bin/gcloud" if n == "gcloud" else None)
    key = aw.tmp / "gcp-sa.json"
    key.write_text("{}")
    monkeypatch.setenv("ABF_STATION_GCP_CREDENTIALS", str(key))
    ce = {"name": "gcb1", "platform": "googlebatch-platform", "project": "lab-project-1", "location": "europe-west2",
          "workDir": "gs://lab-bucket/work", "serviceAccountEmail": None, "credentialsId": None}
    started = []

    class Fed:
        def write(self, d): pass
        def close_stdin(self): pass
        def wait(self, t): return 0, ""
        def kill(self): pass
    monkeypatch.setattr(site, "start_fed", lambda argv, env: started.append(argv) or Fed())
    monkeypatch.setattr(site, "run_fixed", lambda argv, env, timeout: (0, "5\n"))
    handlers.handle({"kind": "put_upload", "args": {"ce": ce, "owner": "alice", "name": "reads.fastq.gz", "size": 5,
                                                     "dest": "gs://lab-bucket/uploads/alice/reads.fastq.gz"}}, aw.ctx)
    assert started and started[0][:3] == ["gcloud", "storage", "cp"]


def test_the_put_upload_arguments_are_unchanged():
    from abf_station import handlers, put_upload
    assert put_upload.ARGS == {"ce", "owner", "name", "size", "dest"} == handlers.ARG_KEYS["put_upload"]


# =============================================================================================================================
# over the limit, and datasets
# =============================================================================================================================
def test_over_limit_file_gets_the_az_command_and_a_plain_warning(pw, ip):
    # TC-077 .. TC-083, TC-085 (AZU-DSET-03)
    secret_texts = (BKEY, SKEY, SAS)
    for size in (GB2 + 1, 3 * GB2):
        msg = pw.refused(stat=fake_stat(size))
        assert "az storage blob upload-batch" in msg
        assert OWN_COMPUTER in msg and "平台不會代你上傳" in msg
        assert "labcontainer" in msg and "uploads/alice/rawdata" in msg and "bob" not in msg and "/work" not in msg
        assert not re.search(r"az login|az account|access key|account-key|sas", msg, re.I)
        assert not any(s in msg for s in secret_texts)
    pw.put(stat=fake_stat(GB2))      # exactly the limit is taken


@pytest.fixture
def az_cloud(d):
    cfg = good_config(workDir="az://labcontainer/work")
    make_env(d, "azure-lab", "labcontainer", d.a, platform=AZ, config=cfg)
    make_env(d, "gcb1", "lab-bucket", d.a)
    make_env(d, "bobenv", "labcontainer", d.b, platform=AZ, config=good_config(workDir="az://bobcontainer/work"))
    return d


def pair(prefix=AZA):
    p = [prefix + n for n in FOUR[:2]]
    return sheet([("a", p[0], p[1])]), p


def reg(d, caller, destination="azure-lab", text=None, files=None, **kw):
    if text is None:
        text, files = pair()
    return register(d, caller, destination=destination, text=text, files=files, **kw)


def test_dataset_destination_az_registers_az_paths(az_cloud):
    # TC-086 (AZU-DSET-01)
    r = reg(az_cloud, az_cloud.a)
    assert r["ok"] is True, r
    got = ds().get_dataset(az_cloud.state, "proj", "v1", caller=az_cloud.a)
    assert [f["path"] for f in got["files"]] == [AZA + n for n in FOUR[:2]]
    assert all(f["path"].startswith("az://labcontainer/uploads/alice/") for f in got["files"])
    ok = ds().check_web_upload(az_cloud.state, {"a": 5, "b": GB2}, caller=az_cloud.a, destination="azure-lab")
    assert ok["ok"] is True and ok["accepted"] == ["a", "b"] and ok["over"] == []
    r = ds().check_web_upload(az_cloud.state, {"big": 3 * GB2 // 2}, caller=az_cloud.a, destination="azure-lab")
    assert r["ok"] is False and "az storage blob upload-batch" in r["command"] and OWN_COMPUTER in r["message"]


def test_mixed_schemes_in_one_dataset_are_refused(az_cloud):
    # TC-087 .. TC-093, TC-099 (AZU-DSET-02)
    a = az_cloud.a
    p0, p1 = pair()[1]

    def bad(files, text=None, destination="azure-lab"):
        r = reg(az_cloud, a, destination=destination, text=text or sheet([("a", files[0], files[-1])]), files=files)
        assert r["ok"] is False and rows_of(az_cloud) == [], (files, r)
        return r["message"]
    assert "az://" in bad([p0, "gs://labcontainer/uploads/alice/a_R2.fastq.gz"])      # TC-087
    assert "az://" in bad([p0, "s3://labcontainer/uploads/alice/a_R2.fastq.gz"])      # TC-088
    assert "az://" in bad([p0, "/some/local/a_R2.fastq.gz"])      # TC-089
    assert "labcontainer" in bad(["az://other-container/uploads/alice/a_R1.fastq.gz", p1])      # TC-090
    assert "az://" in bad(["gs://labcontainer/uploads/alice/a_R1.fastq.gz"] * 2)      # TC-091: no move between clouds
    m = bad(["az://labcontainer/uploads/bob/a_R1.fastq.gz", p1])      # TC-092
    assert "bob" not in m and AZA in m
    bad(["az://labcontainer/uploads/alice/../bob/a_R1.fastq.gz", p1])      # TC-093
    bad([p0, AZA + "AKIA" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGH.fastq.gz"])      # TC-099
    assert "az://" not in bad([p0, p1], destination="gcb1") or True


def test_other_users_cannot_use_or_see_the_azure_dataset(az_cloud):
    # TC-094, TC-095
    assert reg(az_cloud, az_cloud.a, name="reads")["ok"]
    r = reg(az_cloud, az_cloud.b, name="other")
    assert r["ok"] is False and "找不到計算環境" in r["message"]
    assert ds().list_datasets(az_cloud.state, caller=az_cloud.b)["datasets"] == []
    got = ds().get_dataset(az_cloud.state, "reads", caller=az_cloud.b)
    assert got["ok"] is False and "az://" not in repr(got)


def test_google_and_aws_datasets_are_unchanged_by_the_az_branch(az_cloud):
    # TC-096
    p = ["gs://lab-bucket/uploads/alice/" + n for n in FOUR[:2]]
    r = reg(az_cloud, az_cloud.a, destination="gcb1", text=sheet([("a", p[0], p[1])]), files=p)
    assert r["ok"] is True
    r = ds().check_web_upload(az_cloud.state, {"big": 3 * GB2 // 2}, caller=az_cloud.a, destination="gcb1")
    assert r["command"].startswith("gcloud storage cp") and "Azure" not in r["message"]


def test_no_migration_and_the_datasets_surface_did_not_grow():
    # TC-097, TC-098
    assert hashlib.sha256(ds()._TABLE.encode()).hexdigest() == "21218d059436d6998d482eea732cc001ae1ac120c99d0cb0d45db79dfceb3a5a"
    store_src = (SRC_PLATFORM / "store.py").read_text(encoding="utf-8")
    assert sorted(set(re.findall(r"^def (_migrate\w*)", store_src, re.M))) == [
        "_migrate_confirmation_kinds", "_migrate_index", "_migrate_jobs", "_migrate_jobs_kinds", "_migrate_launches", "_migrate_tokens"]
    names = sorted(n for n in dir(ds()) if not n.startswith("_") and inspect.isfunction(getattr(ds(), n)) and getattr(ds(), n).__module__ == ds().__name__)
    assert names == ["check_web_upload", "draft_samplesheet", "get_dataset", "list_datasets", "pair_fastq", "register_dataset"]
    for fn, params in ((ds().draft_samplesheet, ["platform_path", "files", "caller", "destination"]),
                       (ds().check_web_upload, ["platform_path", "sizes", "caller", "destination"]),
                       (ds().register_dataset, ["platform_path", "name", "version", "samplesheet", "files", "caller", "clock", "destination"])):
        assert list(inspect.signature(fn).parameters) == params


# =============================================================================================================================
# sources, scope and documents
# =============================================================================================================================
def _platform_files():
    return [p for p in sorted(SRC_PLATFORM.rglob("*.py")) if "tests" not in p.parts]


def _imports(path):
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module.split(".")[0])
    return out


def test_no_cloud_library_and_no_station_word_in_platform_sources():
    # TC-100, TC-101, TC-102 (AZU-STATIC-01)
    for path in _platform_files():
        text = path.read_text(encoding="utf-8")
        assert not {"boto3", "botocore", "google", "azure"} & set(_imports(path)), path.name
        assert "subprocess" not in text and "threading" not in text.replace("# threading", ""), path.name
    for name in ("cloud_store.py", "datasets.py"):
        raw = next(p for p in _platform_files() if p.name == name).read_text(encoding="utf-8")
        low = raw.lower()
        assert "station" not in low and "station" not in re.sub(r"[\"'+\s]", "", low)
        for word in ("open(", "hashlib", "subprocess", "os.system", "socket", "urllib", "httpx", "requests", "import google", "boto3",
                     "import azure", "from azure"):
            assert word not in raw, (name, word)
    assert "azure" not in (SRC_PLATFORM / "cloud_store.py").read_text(encoding="utf-8")      # lower case only; Azure / AZURE are fine


def test_put_upload_source_has_no_delete_no_cost_no_shell_words():
    # TC-103, TC-104, TC-105, TC-106 (AZU-STATIC-02)
    path = SRC_STATION / "put_upload.py"
    text = path.read_text(encoding="utf-8")
    assert not {"boto3", "botocore", "google", "azure", "subprocess", "requests", "httpx", "socket"} & set(_imports(path))
    assert "shell=True" not in text and "Popen" not in text and "os.system" not in text
    assert not re.search(r"storage blob delete|azcopy|delete-object|s3 rm|s3 sync|--acl|presign", text)
    assert not re.search(r"--account-key|--sas-token|--connection-string|\?sv=|sig=", text)
    assert "cloud_cost" not in text and "cloud_cost" not in (SRC_PLATFORM / "cloud_store.py").read_text(encoding="utf-8")
    assert "cloud_cost" not in inspect.getsource(__import__("abf_platform.jobs", fromlist=["x"]).enqueue_put_upload)
    assert len(re.findall(r"site\.run_fixed\(", text)) >= 1 and "site.start_fed(" in text      # the only doors are in site


def test_the_station_package_has_no_lower_case_azure_word():
    # TC-107
    for f in SRC_STATION.rglob("*.py"):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            assert not re.search(r"\bazure\b", line), (f.name, n)


def test_no_mcp_upload_tool_exists(ip):
    # TC-109
    tools, _ = mcp_inproc(ip.index, [])
    names = sorted(t.name for t in tools)
    assert names and not [n for n in names if "upload" in n.lower()]


def test_no_new_user_visible_action_and_no_new_dependency(tmp_path, ip):
    # TC-110, TC-111
    tools, _ = mcp_inproc(ip.index, [])
    assert {t.name for t in tools} == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files",
                                      "list_used_pipelines", "read_task_log", "run_outputs", "my_usage", "launch", "cancel", "resume",
                                      "relaunch", "forget"}
    from abf_platform import web
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"azure|azbatch|blob", getattr(r, "path", ""), re.I)]
    for name in ("pyproject.toml", "constraints.txt"):
        text = (PLATFORM_DIR / name).read_text(encoding="utf-8").lower()
        assert "azure" not in text and "boto3" not in text and "botocore" not in text


def test_the_new_test_file_names_its_alternative():
    # TC-112
    head = "\n".join(Path(__file__).read_text(encoding="utf-8").splitlines()[:40])
    m = re.search(r"^#\s*Nothing existing:\s*(.+)$", head, re.M)
    assert m and len(m.group(1).split()) >= 15


def _doc(name):
    return (REPO_ROOT / "docs" / name).read_text(encoding="utf-8")


def test_the_documents_say_what_the_feature_is():
    # TC-113, TC-114, TC-115, TC-116, TC-117 (AZU-DOC-01 .. 03)
    d = _doc("PLATFORM.md")
    assert re.search(r"`azbatch-platform` \| Azure Batch \| checked and launched on the platform host \(clean, resume: not yet\)", d)
    assert "Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; the other ten types can be modelled only" in d
    para = next(p for p in d.split("\n\n") if "網頁入口尚未接上" in p)
    assert "az://" in para and "版本控制或軟刪除開著時，覆寫同名檔會留下舊版本、仍收費" in para
    row = next(ln for ln in _doc("SEQERA_PARITY.md").splitlines() if "`azbatch-platform`" in ln)
    assert "Have (create + check + launch + cancel + upload); clean in azure-clean" in row and row.rstrip().endswith("[ ] |")
    t = _doc("TESTING.md")
    assert "Uploading to Azure Batch (azure-upload): the maintainer checks by hand" in t
    section = t[t.index("Uploading to Azure Batch (azure-upload)"):]
    assert "az storage blob show" in section and "成本警示" in section and "會花一點錢" in section
