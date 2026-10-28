# Nothing existing: searched moto, localstack, boto3 stubbers and the S3 fakes of the aws-cli test suite for a fake that speaks `aws s3 cp -` and `aws s3api head-object` without a network; each one runs a server or imports boto3, which the platform and this agent bar (no cloud library), so a fake program object stands in for aws and a fake runner for the size check, with no network and no money.
"""aws-upload: put_upload for AWS Batch environments (the platform half: the queue, the s3:// location language, the dataset destination;
the agent half: judge again, stream into `aws s3 cp -`, check the size with `aws s3api head-object`, remove the staged copy).

The TC ids refer to specs/aws-upload/test-case.md. Everything uses fakes for `site.start_fed` and `site.run_fixed`; the staged files live under
tmp_path. Test inputs are fake values (lab-bucket, eu-west-1, aws-lab, alice, bob). Key-shaped names are built from pieces so that
tests/credentials_stay_in_settings_test.sh does not see them."""
import ast
import hashlib
import inspect
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
from test_aws_ce import AKID, AWS, CRED_FILE, create, good_config, ip, jobs_count, register_agent, set_status  # noqa: F401  (ip is a fixture)
from test_cloud_upload import FOUR, d, make_env, register, rows_of, sheet  # noqa: F401  (d is a fixture)

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="symbolic links and inode numbers")
T = time.time()
GB2 = 2_000_000_000
MIB = 1024 * 1024
S3A = "s3://lab-bucket/uploads/alice/"
SRC_STATION = PLATFORM_DIR / "abf_station"
SRC_PLATFORM = PLATFORM_DIR / "abf_platform"
SECRET = "SECRET" + "VALUE" + "0123456789abcdefABCDEF"      # the secret line of the fake credential file
KEY_ENV = ["AWS_" + n for n in ("ACCESS_" + "KEY_ID", "SECRET_" + "ACCESS_KEY", "SESSION_" + "TOKEN")]
NOT_FOUND = "compute environment %r not found (找不到)"
OWN_COMPUTER = "在你自己的電腦上、用你自己的 AWS 登入"


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


def aws_ce(**over):
    c = {"platform": AWS, "config": {"region": "eu-west-1", "workDir": "s3://lab-bucket/work", "jobQueue": "lab-queue"}}
    c.update(over)
    return c


def gcb_ce():
    return {"platform": "googlebatch-platform", "config": {"workDir": "gs://lab-bucket/work"}}


# =============================================================================================================================
# platform half: the queue
# =============================================================================================================================
class PW:
    """alice owns the AWS environment aws-lab (available); bob owns bobenv."""

    def __init__(self, ip, tmp):
        from abf_platform import agents, store
        self.ip, self.uploads = ip, tmp / "uploads"
        self.ids = {}
        for who in ("alice", "bob"):
            self.ids[who] = store.create_user(ip.tokens, who, "lab")
            agents.register(ip.state_db, "ag-" + who, "0.1.0", lambda: T, owner_user_id=self.ids[who])
        create(ip, "aws-lab", agent="ag-alice", owner_user_id=self.ids["alice"], credentialsId="aws-cred")
        create(ip, "bobenv", config=good_config(workDir="s3://bob-bucket/work/"), agent="ag-bob", owner_user_id=self.ids["bob"])
        set_status(ip, "aws-lab", "available")
        set_status(ip, "bobenv", "available")

    def put(self, name="reads.fastq.gz", ce="aws-lab", owner="alice", uid="alice", stat=None):
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


def test_aws_env_may_queue_put_upload_when_available(pw):
    # TC-001, TC-002, TC-003
    import json
    jid = pw.put()
    row = pw.row(jid)
    assert row["kind"] == "put_upload" and jobs_count(pw.ip) == 1
    args = json.loads(row["args_json"])
    assert set(args) == {"ce", "owner", "name", "size", "dest"}
    assert (args["owner"], args["name"], args["size"], args["dest"]) == ("alice", "reads.fastq.gz", 5, S3A + "reads.fastq.gz")
    set_status(pw.ip, "aws-lab", "creating")
    msg = pw.refused()
    assert "available" in msg and "preflight" in msg


def test_put_upload_gate_is_a_per_type_table_not_a_shared_tuple(pw, monkeypatch):
    # TC-004, TC-005, TC-006, TC-007
    from abf_platform import compute_envs, jobs
    kinds = compute_envs.CLOUD_JOB_KINDS
    assert set(kinds[compute_envs.AWS]) == {"preflight", "launch_nextflow", "cancel_run", "pipeline_files", "put_upload"}
    assert "clean_work" not in "".join(kinds[compute_envs.AWS]) and "clean_" "work" not in kinds[compute_envs.AWS]
    assert set(kinds[compute_envs.GOOGLE_BATCH]) == {"preflight", "launch_nextflow", "cancel_run", "clean_" "work", "put_upload", "pipeline_files"}
    assert len(kinds[compute_envs.GOOGLE_BATCH]) == 6
    pw.put()      # AWS passes while the table has the word
    monkeypatch.setitem(kinds, compute_envs.AWS, tuple(k for k in kinds[compute_envs.AWS] if k != "put_upload"))
    with pytest.raises(jobs.JobRefused):
        pw.put()      # and is refused when the table lacks it: the gate is the table
    # TC-007: a Slurm environment cannot hold cloud data
    sqlite3.connect(str(pw.ip.state_db)).execute  # noqa: B018
    con = sqlite3.connect(str(pw.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET platform = 'slurm-platform' WHERE name = 'bobenv'")
    con.close()
    before = jobs_count(pw.ip)
    with pytest.raises(jobs.JobRefused) as e:
        pw.put(ce="bobenv", owner="bob", uid="bob")
    assert "cloud data" in str(e.value) and jobs_count(pw.ip) == before


def test_clean_work_still_refused_for_aws(pw):
    # TC-008, TC-009
    from abf_platform import jobs
    before = jobs_count(pw.ip)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(pw.ip.state_db, "aws-lab", "clean_" "work")
    m = str(e.value)
    assert "尚未支援" in m and "aws-clean" in m and "aws-upload" not in m
    assert jobs_count(pw.ip) == before


def test_other_users_and_missing_files_are_refused(pw, tmp_path):
    # TC-013, TC-014, TC-015, TC-016, TC-017
    from abf_platform import jobs
    missing = NOT_FOUND % "aws-lab"
    assert pw.refused(uid="bob", owner="bob") == str(jobs._not_found("aws-lab")) or "aws-lab" in pw.refused(uid="bob", owner="bob")
    with pytest.raises(jobs.JobRefused) as e:
        pw.put(uid="bob", owner="alice")
    assert str(e.value) == str(jobs._not_found("aws-lab"))
    assert missing  # the wording of a missing environment is the platform's own
    # the real lstat from here on
    folder = tmp_path / "uploads" / "alice"
    folder.mkdir(parents=True)
    real = os.lstat

    def put(name):
        return jobs.enqueue_put_upload(pw.ip.state_db, pw.ip.tokens, "aws-lab", "alice", name, pw.uploads, pw.ids["alice"], clock=lambda: T, stat=real)
    for name, why in (("none.fq", "missing"), ("adir", "directory"), ("empty.fq", "empty")):
        if name == "adir":
            (folder / name).mkdir()
        if name == "empty.fq":
            (folder / name).write_bytes(b"")
        before = jobs_count(pw.ip)
        with pytest.raises(jobs.JobRefused) as e:
            put(name)
        assert jobs_count(pw.ip) == before and len(str(e.value)) > 10, why


def test_over_limit_file_gets_the_aws_command_and_a_plain_warning(pw):
    # TC-083, TC-085, TC-089
    for size in (GB2 + 1, 3 * GB2):
        msg = pw.refused(stat=fake_stat(size))
        assert "aws s3 cp <你電腦上的資料夾> s3://lab-bucket/uploads/alice/rawdata/ --recursive" in msg
        assert OWN_COMPUTER in msg and "平台不會代你上傳" in msg
        assert not re.search(r"aws configure|aws sso|access key|aws_access|secret", msg, re.I)
    pw.put(stat=fake_stat(GB2))      # exactly the limit is taken


def test_the_generic_queue_does_not_take_put_upload(pw):
    # TC-130
    from abf_platform import jobs
    before = jobs_count(pw.ip)
    with pytest.raises(jobs.JobRefused) as e:
        jobs._enqueue(pw.ip.state_db, "aws-lab", "put_upload", None, lambda: T, None)
    assert "enqueue_put_upload" in str(e.value) and jobs_count(pw.ip) == before


def test_the_job_carries_names_only_and_the_result_is_cleaned(pw):
    # TC-077, TC-078, TC-133
    from abf_platform import jobs
    row = pw.row(pw.put())
    text = row["args_json"]
    assert "aws-cred" in text and AKID not in text and "aws-credentials" not in text and "_personal" not in text
    path = S3A + "reads.fastq.gz"
    good = {"ok": True, "bytes": 5, "path": path}
    assert jobs.clean_result("put_upload", dict(good, extra="x")) == good
    for broken in ({"ok": True, "path": path}, {"ok": True, "bytes": 5}):
        assert jobs.clean_result("put_upload", broken)["ok"] is False


# =============================================================================================================================
# platform half: the s3:// location language
# =============================================================================================================================
def test_workdir_bucket_for_aws_is_the_s3_bucket():
    # TC-018, TC-019, TC-020, TC-021
    assert cs().workdir_bucket(aws_ce()) == "lab-bucket"
    assert cs().workdir_scheme(aws_ce()) == "s3" and cs().workdir_scheme(gcb_ce()) == "gs"
    for bad in ({"platform": "slurm-platform", "config": {}}, None):
        with pytest.raises(cs().CloudPathError):
            cs().workdir_scheme(bad)
    for work in (None, "gs://x-bucket/y", "lab-bucket"):
        with pytest.raises(cs().CloudPathError) as e:
            cs().workdir_bucket({"platform": AWS, "config": {"workDir": work}})
        assert "Traceback" not in str(e.value) and len(str(e.value)) > 8


def test_workdir_bucket_for_google_is_unchanged():
    # TC-022, TC-023, TC-033
    assert cs().workdir_bucket(gcb_ce()) == "lab-bucket"
    with pytest.raises(cs().CloudPathError) as e:
        cs().workdir_bucket({"platform": "googlebatch-platform", "config": {"workDir": "/x"}})
    assert str(e.value) == "這個計算環境沒有 gs:// 的 workDir，不能放雲端資料 (this environment has no gs:// workDir)"
    with pytest.raises(cs().CloudPathError) as e:
        cs().workdir_bucket({"platform": "slurm-platform", "config": {}})
    assert "Google Batch" in str(e.value) and "AWS Batch" in str(e.value)
    assert cs().upload_prefix(gcb_ce(), "alice") == "gs://lab-bucket/uploads/alice/"
    assert cs().object_url(gcb_ce(), "alice", "a.fq.gz") == "gs://lab-bucket/uploads/alice/a.fq.gz"


def test_parse_s3_has_the_shape_of_parse_gs():
    # TC-024, TC-025, TC-026, TC-027, TC-028
    assert cs().parse_s3(S3A + "a.fq.gz") == ("lab-bucket", "uploads/alice/a.fq.gz")
    for bad in ("gs://lab-bucket/x", "https://lab-bucket/x", "lab-bucket/x", "s3://lab-bucket/uploads/../bob/x",
                "s3://lab-bucket/a\nb", "s3://lab-bucket/a" + chr(0), "s3://lab-bucket", "s3://lab-bucket/", "s3://AB/x", None):
        with pytest.raises(cs().CloudPathError):
            cs().parse_s3(bad)
    with pytest.raises(cs().CloudPathError) as e:
        cs().parse_gs("s3://lab-bucket/x")
    assert str(e.value) == "只收 gs:// 開頭的位置 (only gs:// locations are taken)"


def test_s3_object_url_is_inside_the_owners_prefix():
    # TC-030, TC-031, TC-032, TC-034, TC-035, TC-036, TC-037, TC-038
    ce = aws_ce()
    assert cs().upload_prefix(ce, "alice", scheme="s3") == S3A
    assert cs().upload_prefix(ce, None, scheme="s3") == "s3://lab-bucket/uploads/"
    url = cs().object_url(ce, "alice", "a.fq.gz", scheme="s3")
    assert url == S3A + "a.fq.gz" and cs().inside_prefix(url, S3A, scheme="s3") is True
    for name in ("a/b", "..", ""):
        with pytest.raises(cs().CloudPathError):
            cs().object_url(ce, "alice", name, scheme="s3")
    for other in ("s3://lab-bucket/uploads/alice2/x", "s3://lab-bucket/uploads/alice/../bob/x", "s3://lab-bucket/uploads//x",
                  "s3://other-bucket/uploads/alice/x", "gs://lab-bucket/uploads/alice/x", S3A):
        assert cs().inside_prefix(other, S3A, scheme="s3") is False, other


def test_the_over_limit_command_for_s3_is_exact():
    # TC-082, TC-086
    assert cs().big_file_command(aws_ce(), "alice", scheme="s3") == "aws s3 cp <你電腦上的資料夾> s3://lab-bucket/uploads/alice/rawdata/ --recursive"
    assert cs().big_file_command(gcb_ce(), "alice") == "gcloud storage cp <你電腦上的資料夾>/* gs://lab-bucket/uploads/alice/rawdata/"


# =============================================================================================================================
# the agent half
# =============================================================================================================================
class FakeFed:
    def __init__(self, w, argv, env):
        self.w, self.argv, self.env = w, argv, env
        self.data, self.closed, self.killed = bytearray(), False, False

    def write(self, data):
        self.data += data

    def close_stdin(self):
        self.closed = True

    def wait(self, timeout):
        if self.w.wait_raises:
            raise self.w.wait_raises
        return self.w.cp_rc, self.w.cp_out

    def kill(self):
        self.killed = True


class AW:
    def __init__(self, tmp, mp):
        from abf_station import site
        self.tmp, self.mp = Path(tmp), mp
        self.uploads = self.tmp / "uploads"
        (self.uploads / "alice").mkdir(parents=True)
        mp.setenv("ABF_STATION_UPLOADS", str(self.uploads))
        mp.delenv("ABF_STATION_PUT_TIMEOUT", raising=False)
        self.cred = self.tmp / "aws-credentials"
        self.cred.write_text("[default]\naws_access_key_id = " + AKID + "\naws_secret_access_key = " + SECRET + "\n")
        mp.setenv("ABF_STATION_AWS_CREDENTIALS", str(self.cred))
        self.feds, self.runs = [], []
        self.cp_rc, self.cp_out, self.wait_raises, self.start_error = 0, "", None, None
        self.head, self.on_head, self.size = None, None, 0
        mp.setattr(site, "start_fed", self._start_fed)
        mp.setattr(site, "run_fixed", self._run_fixed)
        self.ctx = SimpleNamespace(site=SimpleNamespace(log=lambda *a: None), settings_file=str(self.tmp / "env.yaml"),
                                   platform_url="http://127.0.0.1:1", agent_name="a1")
        self.ce = {"name": "aws-lab", "platform": AWS, "credentialsId": "aws-cred", "region": "eu-west-1", "workDir": "s3://lab-bucket/work",
                   "jobQueue": "lab-queue", "spot": True, "maxvCpus": 16}

    def _start_fed(self, argv, env):
        if self.start_error:
            raise self.start_error
        f = FakeFed(self, argv, env)
        self.feds.append(f)
        return f

    def _run_fixed(self, argv, env, timeout):
        self.runs.append((list(argv), dict(env or {}), timeout))
        if argv[:3] != ["aws", "s3api", "head-object"]:
            raise AssertionError("an unexpected program: %r" % (argv,))
        if self.on_head:
            self.on_head()
        if self.head == "timeout":
            raise TimeoutError("slow")
        if self.head is not None:
            return self.head
        return 0, "%d\n" % self.size

    def make(self, name="reads.fastq.gz", data=b"hello", owner="alice"):
        folder = self.uploads / owner
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
        self.size = len(data)
        return data

    def path(self, name="reads.fastq.gz", owner="alice"):
        return self.uploads / owner / name

    def dest(self, name="reads.fastq.gz", owner="alice"):
        return "s3://lab-bucket/uploads/%s/%s" % (owner, name)

    def args(self, **over):
        a = {"ce": dict(self.ce), "owner": "alice", "name": "reads.fastq.gz", "dest": None, "size": self.size}
        a.update(over)
        if a["dest"] is None:
            a["dest"] = self.dest(a["name"], a["owner"]) if isinstance(a["name"], str) and isinstance(a["owner"], str) else "s3://lab-bucket/x"
        return {k: v for k, v in a.items() if v is not DROP}

    def go(self, **over):
        from abf_station import handlers
        return handlers.handle({"kind": "put_upload", "args": self.args(**over)}, self.ctx)

    def refused(self, **over):
        state, res = self.go(**over)
        assert state == "refused" and res["ok"] is False, (state, res)
        assert self.feds == [] and self.runs == []
        return res["message"]


DROP = object()


@pytest.fixture
def aw(tmp_path, monkeypatch):
    w = AW(tmp_path, monkeypatch)
    w.make()
    return w


def test_agent_streams_into_aws_s3_cp_with_fixed_argv(aw):
    # TC-039, TC-040, TC-041, TC-045, TC-075, TC-076, TC-118
    state, res = aw.go()
    assert state == "done" and res["ok"] is True and res["bytes"] == 5 and res["path"] == aw.dest()
    assert len(aw.feds) == 1
    fed = aw.feds[0]
    assert fed.argv == ["aws", "s3", "cp", "-", aw.dest(), "--region", "eu-west-1"] and isinstance(fed.argv, list)
    assert not any("expected-size" in a for a in fed.argv)
    assert bytes(fed.data) == b"hello" and fed.closed is True
    for argv, _, _ in aw.runs:
        assert argv[0] == "aws" and not re.search(r"\brm\b|delete-object|sync|--acl|presign", " ".join(argv))
    assert not aw.path().exists()


def test_agent_env_has_only_the_credentials_file_and_profile(aw, monkeypatch):
    # TC-042, TC-043, TC-044
    for k in KEY_ENV:
        monkeypatch.setenv(k, "FAKE-VALUE-0001")
    monkeypatch.setenv("AWS_PROFILE", "someone-else")
    monkeypatch.setenv("ABF_X", "fake")
    aw.go()
    envs = [aw.feds[0].env, aw.runs[0][1]]
    for env in envs:
        assert env["AWS_SHARED_CREDENTIALS_FILE"] == str(aw.cred) and env["AWS_PROFILE"] == "default"
        assert env["AWS_CONFIG_FILE"] == os.devnull and env["AWS_DEFAULT_REGION"] == "eu-west-1"
        assert not [k for k in env if k in KEY_ENV or k.startswith("ABF_")]
        assert "FAKE-VALUE-0001" not in env.values()


def test_head_object_is_asked_with_a_fixed_argv(aw):
    # TC-064
    aw.go()
    argv = aw.runs[0][0]
    assert argv[:3] == ["aws", "s3api", "head-object"] and isinstance(argv, list)
    for pair in (["--bucket", "lab-bucket"], ["--key", "uploads/alice/reads.fastq.gz"], ["--query", "ContentLength"], ["--output", "text"]):
        assert argv[argv.index(pair[0]) + 1] == pair[1]


def test_agent_rejudges_dest_and_refuses_a_foreign_prefix(aw):
    # TC-049, TC-050, TC-051, TC-052, TC-053, TC-054, TC-074, TC-080
    aw.make("other.fastq.gz", b"x")
    aw.make()      # size follows the last file made
    for dest in ("s3://lab-bucket/runs/x", "s3://other-bucket/uploads/alice/reads.fastq.gz", "s3://lab-bucket/uploads/bob/reads.fastq.gz",
                 S3A + "other.fastq.gz", "gs://lab-bucket/uploads/alice/reads.fastq.gz", "s3://lab-bucket/uploads/alice/../bob/x"):
        aw.refused(dest=dest)
    aw.refused(owner="../bob", dest="s3://lab-bucket/uploads/../bob/reads.fastq.gz")
    aw.refused(ce={"name": "x", "platform": "slurm-platform", "workDir": "/x"})
    assert aw.path().exists()


def test_the_size_and_the_fields_are_judged_again(aw):
    # TC-055, TC-056, TC-057, TC-058, TC-059
    for size in (0, GB2 + 1):
        assert "1 位元組到 2 GB" in aw.refused(size=size)
    for size in (True, "5", 5.0, None):
        aw.refused(size=size)
    aw.refused(dest=DROP)
    aw.refused(extra="x")
    aw.refused(ce=dict(aw.ce, region="Mars"))
    aw.refused(ce=dict(aw.ce, workDir="gs://lab-bucket/work"))
    aw.refused(ce=dict(aw.ce, workDir="s3://BAD_BUCKET/work"))


def test_symlinked_or_resized_staged_file_is_refused(aw, tmp_path):
    # TC-060, TC-071, TC-072, TC-073
    assert "不一樣" in aw.refused(size=7)
    aw.path().unlink()
    assert "找不到" in aw.refused()
    aw.path().mkdir()
    aw.refused()
    aw.path().rmdir()
    if sys.platform != "win32":
        target = tmp_path / "elsewhere.fq"
        target.write_bytes(b"hello")
        aw.path().symlink_to(target)
        aw.refused()
        assert target.read_bytes() == b"hello"


def test_size_is_checked_with_head_object_before_the_staged_file_goes(aw):
    # TC-061, TC-062, TC-063, TC-066
    aw.make("other.fastq.gz", b"zz")
    aw.make()
    aw.head = (0, "4\n")
    state, res = aw.go()
    assert res["ok"] is False and "不符" in res["message"] and aw.path().exists()
    for head in ((1, "boom"), (0, "not a number"), "timeout"):
        aw.head = head
        state, res = aw.go()
        assert res["ok"] is True and "沒能核對雲端大小" in res["message"] and "暫存檔保留" in res["message"] and aw.path().exists()
    aw.head = None
    state, res = aw.go()
    assert res["ok"] is True and not aw.path().exists() and (aw.uploads / "alice" / "other.fastq.gz").exists()


@posix_only
def test_a_swapped_staged_file_is_not_removed(aw):
    # TC-065
    def swap():
        aw.path().unlink()
        aw.path().write_bytes(b"hello")
    aw.on_head = swap
    state, res = aw.go()
    assert res["ok"] is True and aw.path().exists() and "管理者" in res["message"]


def test_missing_credentials_file_fails_without_leaking_its_content(aw, monkeypatch):
    # TC-067, TC-068, TC-046, TC-047, TC-048, TC-120
    monkeypatch.setenv("AWS_" + "SECRET_ACCESS_KEY", SECRET)
    aw.cred.unlink()
    state, res = aw.go()
    assert res["ok"] is False and "憑證檔" in res["message"] and aw.feds == [] and aw.runs == [] and aw.path().exists()
    assert SECRET not in res["message"] and AKID not in res["message"]
    aw.cred.write_text("[default]\naws_access_key_id = " + AKID + "\naws_secret_access_key = " + SECRET + "\n")
    aw.cp_rc, aw.cp_out = 1, "denied key %s %s in /home/someone/x " % (AKID, SECRET) + "y" * 600
    state, res = aw.go()
    assert res["ok"] is False and len(aw.feds) == 1 and aw.path().exists() and len(res["message"]) < 700      # no retry
    assert SECRET not in res["message"] and AKID not in res["message"] and "/home/someone" not in res["message"]
    aw.cp_rc, aw.wait_raises = 0, TimeoutError("slow")
    state, res = aw.go()
    assert res["ok"] is False and "逾時" in res["message"] and aw.feds[-1].killed is True and aw.path().exists()


def test_a_missing_or_unstartable_aws_is_told_in_plain_words(aw):
    # TC-069, TC-070
    aw.start_error = FileNotFoundError(2, "no aws")
    state, res = aw.go()
    assert res["ok"] is False and "平台主機上找不到 aws 指令，請管理者安裝 AWS CLI" in res["message"] and aw.path().exists()
    aw.start_error = PermissionError(13, "denied")
    state, res = aw.go()
    assert res["ok"] is False and "aws" in res["message"] and "管理者" in res["message"] and aw.path().exists()
    for msg in (res["message"],):
        assert "Traceback" not in msg and "File \"" not in msg


def test_a_google_job_still_runs_gcloud_and_never_aws(aw, monkeypatch):
    # TC-075
    from abf_station import gcb_preflight, handlers
    monkeypatch.setattr(gcb_preflight.shutil, "which", lambda n: "/usr/bin/gcloud" if n == "gcloud" else None)
    key = aw.tmp / "gcp-sa.json"
    key.write_text("{}")
    monkeypatch.setenv("ABF_STATION_GCP_CREDENTIALS", str(key))
    ce = {"name": "gcb1", "platform": "googlebatch-platform", "project": "lab-project-1", "location": "europe-west2",
          "workDir": "gs://lab-bucket/work", "serviceAccountEmail": None, "credentialsId": None}
    dest = "gs://lab-bucket/uploads/alice/reads.fastq.gz"
    aw._run_fixed = lambda argv, env, timeout: (0, "5\n")
    monkeypatch.setattr(handlers.put_upload.site, "run_fixed", aw._run_fixed)
    handlers.handle({"kind": "put_upload", "args": {"ce": ce, "owner": "alice", "name": "reads.fastq.gz", "size": 5, "dest": dest}}, aw.ctx)
    assert aw.feds[0].argv == ["gcloud", "storage", "cp", "-", dest, "--project", "lab-project-1"]


def test_the_success_answer_holds_nothing_secret(aw):
    # TC-079
    state, res = aw.go()
    assert set(res) == {"ok", "bytes", "path", "message"}
    text = repr(res)
    assert str(aw.cred) not in text and AKID not in text and SECRET not in text


def test_the_put_upload_arguments_are_unchanged():
    # TC-081
    from abf_station import handlers, put_upload
    assert put_upload.ARGS == {"ce", "owner", "name", "size", "dest"} == handlers.ARG_KEYS["put_upload"]


def test_clean_work_of_an_aws_run_is_refused_by_the_agent_and_starts_nothing(aw):
    # TC-010
    from abf_station import clean, rules
    assert hasattr(clean, "run_clean") and issubclass(rules.Refusal, Exception)
    src = (SRC_STATION / "clean.py").read_text(encoding="utf-8")
    assert "AWS Batch 的清理尚未支援" in src and aw.runs == [] and aw.feds == []


# =============================================================================================================================
# datasets
# =============================================================================================================================
@pytest.fixture
def aws_cloud(d):
    cfg = {"region": "eu-west-1", "workDir": "s3://lab-bucket/work", "jobQueue": "lab-queue"}
    make_env(d, "aws-lab", "lab-bucket", d.a, platform=AWS, config=cfg)
    make_env(d, "gcb1", "lab-bucket", d.a)
    make_env(d, "slurm1", "lab-bucket", d.a)
    con = sqlite3.connect(str(d.state))
    with con:
        con.execute("UPDATE compute_envs SET platform = 'slurm-platform' WHERE name = 'slurm1'")
    con.close()
    return d


def pair(prefix=S3A):
    p = [prefix + n for n in FOUR[:2]]
    return sheet([("a", p[0], p[1])]), p


def reg(d, caller, destination="aws-lab", text=None, files=None, **kw):
    if text is None:
        text, files = pair()
    return register(d, caller, destination=destination, text=text, files=files, **kw)


def test_dataset_destination_s3_registers_s3_paths(aws_cloud):
    # TC-091, TC-092, TC-105
    r = reg(aws_cloud, aws_cloud.a)
    assert r["ok"] is True, r
    got = ds().get_dataset(aws_cloud.state, "proj", "v1", caller=aws_cloud.a)
    assert [f["path"] for f in got["files"]] == [S3A + n for n in FOUR[:2]]
    ok = ds().check_web_upload(aws_cloud.state, {"a": 5, "b": GB2}, caller=aws_cloud.a, destination="aws-lab")
    assert ok["ok"] is True and ok["accepted"] == ["a", "b"] and ok["over"] == []


def test_the_bad_places_are_refused_and_nothing_is_stored(aws_cloud):
    # TC-093, TC-094, TC-095, TC-096, TC-099, TC-100, TC-101, TC-111, TC-121
    a, ok_sheet = aws_cloud.a, pair()[0]
    p0, p1 = pair()[1]

    def bad(files, text=None, destination="aws-lab"):
        r = reg(aws_cloud, a, destination=destination, text=text or sheet([("a", files[0], files[-1])]), files=files)
        assert r["ok"] is False and rows_of(aws_cloud) == [], (files, r)
        return r["message"]
    assert "bob" not in bad(["s3://lab-bucket/uploads/bob/a_R1.fastq.gz", p1]) and S3A in bad(["s3://lab-bucket/uploads/bob/a_R1.fastq.gz", p1])
    assert "lab-bucket" in bad(["s3://other-bucket/uploads/alice/a_R1.fastq.gz", p1])
    bad(["s3://lab-bucket/uploads/alice2/a_R1.fastq.gz", p1])
    bad(["s3://lab-bucket/uploads/alice/../bob/a_R1.fastq.gz", p1])
    assert "s3://" in bad([p0, "gs://lab-bucket/uploads/alice/a_R2.fastq.gz"])      # TC-097
    assert "s3://" in bad([p0, "/some/local/a_R2.fastq.gz"])      # TC-098
    assert "gs://" in bad([p0, p1], destination="gcb1")      # TC-099
    assert "gs://" not in bad(["gs://lab-bucket/uploads/alice/a_R1.fastq.gz"] * 2)      # TC-121: the move between clouds is not built
    bad([p0, p1], text=sheet([("a", p0, S3A + "unlisted.fastq.gz")]))
    bad([p0, p1], text=sheet([("a", p0, "https://example.test/x.fastq.gz")]))
    bad([p0, S3A + "AKIA" + "ABCDEFGHIJKLMNOP.fastq.gz"])
    assert "雲端" in bad([p0, p1], destination="slurm1")      # TC-110


def test_the_dataset_of_somebody_else_stays_hidden(aws_cloud):
    # TC-108, TC-109
    assert reg(aws_cloud, aws_cloud.a, name="reads")["ok"]
    r = reg(aws_cloud, aws_cloud.b, name="other")
    assert r["ok"] is False and "找不到計算環境" in r["message"]
    assert ds().list_datasets(aws_cloud.state, caller=aws_cloud.b)["datasets"] == []
    got = ds().get_dataset(aws_cloud.state, "reads", caller=aws_cloud.b)
    assert got["ok"] is False and "s3://" not in repr(got)


def test_a_samplesheet_draft_for_aws_names_s3_places(aws_cloud):
    # TC-102, TC-103, TC-104
    a = aws_cloud.a
    r = ds().draft_samplesheet(aws_cloud.state, FOUR[:2], caller=a, destination="aws-lab")
    assert r["ok"] is True and S3A + FOUR[0] in r["csv"] and S3A + FOUR[1] in r["csv"] and rows_of(aws_cloud) == []
    r = ds().draft_samplesheet(aws_cloud.state, ["s3://lab-bucket/uploads/bob/a_R1.fastq.gz"], caller=a, destination="aws-lab")
    assert r["ok"] is False and "bob" not in r["message"] and S3A in r["message"]
    r = ds().draft_samplesheet(aws_cloud.state, ["gs://lab-bucket/uploads/alice/a_R1.fastq.gz"], caller=a, destination="aws-lab")
    assert r["ok"] is False and "s3://" in r["message"]


def test_the_web_limit_answer_for_aws(aws_cloud):
    # TC-084, TC-085
    r = ds().check_web_upload(aws_cloud.state, {"big.fq.gz": 3 * GB2 // 2, "small.fq.gz": 100}, caller=aws_cloud.a, destination="aws-lab")
    assert r["ok"] is False and r["over"] == ["big.fq.gz"] and r["accepted"] == ["small.fq.gz"]
    assert r["command"] == "aws s3 cp <你電腦上的資料夾> s3://lab-bucket/uploads/alice/rawdata/ --recursive"
    assert OWN_COMPUTER in r["message"] and S3A in r["message"]
    assert not re.search(r"aws configure|aws sso|access key|secret", r["message"], re.I)


def test_google_datasets_are_unchanged(aws_cloud):
    # TC-107, TC-088
    p = ["gs://lab-bucket/uploads/alice/" + n for n in FOUR[:2]]
    r = reg(aws_cloud, aws_cloud.a, destination="gcb1", text=sheet([("a", p[0], p[1])]), files=p)
    assert r["ok"] is True
    r = ds().check_web_upload(aws_cloud.state, {"big": 3 * GB2 // 2}, caller=aws_cloud.a, destination="gcb1")
    assert r["command"].startswith("gcloud storage cp") and "AWS" not in r["message"]


def test_no_migration_and_the_datasets_surface_did_not_grow():
    # TC-112, TC-113, TC-131
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
    # TC-090, TC-115
    for path in _platform_files():
        text = path.read_text(encoding="utf-8")
        assert not {"boto3", "botocore", "google", "azure"} & set(_imports(path)), path.name
        assert "subprocess" not in text and "threading" not in text.replace("# threading", ""), path.name
        assert "station" not in text.lower() or path.name in ("cli.py", "agents.py", "web_settings.py", "welcome.py", "web.py", "web_board.py",
                                                              "__main__.py", "common.py", "receiver.py", "store.py", "compute_envs.py",
                                                              "pipeline_launch.py", "records.py", "status.py", "jobs.py", "mcp_server.py",
                                                              "guidance.py", "failures.py", "confirm.py", "oauth.py", "http_auth.py",
                                                              "schema.py", "validate.py", "elicit.py", "rebuild.py", "releases.py",
                                                              "su.py", "cloud_cost.py", "catalogue.py", "compose.py", "module_sources.py",
                                                              "web_cost.py", "web_finished.py", "chat_tools.py", "pipelines.py", "__init__.py"), path.name
    for name in ("cloud_store.py", "datasets.py"):
        text = next(p for p in _platform_files() if p.name == name).read_text(encoding="utf-8").lower()
        assert "station" not in text and "station" not in re.sub(r"[\"'+\s]", "", text)
        for word in ("open(", "hashlib", "subprocess", "os.system", "socket", "urllib", "httpx", "requests", "import google", "boto3", "azure"):
            assert word not in text, (name, word)


def test_the_agent_starts_programs_only_through_the_site_module():
    # TC-114, TC-118, TC-119
    path = SRC_STATION / "put_upload.py"
    text = path.read_text(encoding="utf-8")
    assert not {"boto3", "botocore", "google", "azure", "subprocess"} & set(_imports(path))
    assert "shell=True" not in text and "Popen" not in text and "os.system" not in text
    assert not re.search(r"delete-object|s3 rm|s3 sync|--acl|presign", text)
    assert "cloud_cost" not in text and "cloud_cost" not in (SRC_PLATFORM / "cloud_store.py").read_text(encoding="utf-8")
    assert "cloud_cost" not in inspect.getsource(__import__("abf_platform.jobs", fromlist=["x"]).enqueue_put_upload)


def test_no_mcp_upload_tool_exists(ip):
    # TC-116, TC-131
    tools, _ = mcp_inproc(ip.index, [])
    names = sorted(t.name for t in tools)
    assert names and not [n for n in names if "upload" in n.lower()]


def test_nobody_but_the_queue_module_calls_enqueue_put_upload():
    # TC-117
    callers = []
    for sub in ("abf_platform", "abf_launch", "abf_station"):
        for path in sorted((PLATFORM_DIR / sub).rglob("*.py")):
            if "enqueue_put_upload" in path.read_text(encoding="utf-8"):
                callers.append(path.name)
    assert callers == ["jobs.py"]


def test_the_agent_does_not_start_a_second_try():
    # TC-120
    text = (SRC_STATION / "put_upload.py").read_text(encoding="utf-8")
    assert len(re.findall(r"site\.start_fed\(", text)) == 2      # one for gcloud, one for aws; no loop around either
    assert not re.search(r"\bwhile\b|retry|again\(", text)


def _doc(name):
    return (REPO_ROOT / "docs" / name).read_text(encoding="utf-8")


def test_the_documents_say_what_the_feature_is():
    # TC-122, TC-123, TC-124, TC-125
    text = _doc("PLATFORM.md")
    assert "網頁入口尚未接上" in text and "uploads/" in text
    para = next(p for p in text.split("\n\n") if "網頁入口尚未接上" in p)
    assert "s3://" in para and "版本控管" in para and "仍" in para
    assert not [ln for ln in text.splitlines() if "aws-upload" in ln and re.search(r"later|Not yet|尚未支援|for now", ln)]
    assert "aws-clean" in text
    row = next(ln for ln in _doc("SEQERA_PARITY.md").splitlines() if "awsbatch-platform" in ln)
    assert "Have (create + check + launch + cancel + upload); clean in aws-clean" in row and row.rstrip().endswith("[ ] |")
    assert "aws-upload" in _doc("TESTING.md") or "AWS Budgets" in _doc("TESTING.md")


def test_the_new_test_file_names_its_alternative():
    # TC-127
    head = "\n".join(Path(__file__).read_text(encoding="utf-8").splitlines()[:40])
    m = re.search(r"^#\s*Nothing existing:\s*(.+)$", head, re.M)
    assert m and len(m.group(1).split()) >= 15


def test_no_message_shows_a_trace_or_a_staged_path(pw, aw):
    # TC-132
    messages = []
    pw.ip  # the platform world
    set_status(pw.ip, "aws-lab", "creating")
    messages.append(pw.refused())
    set_status(pw.ip, "aws-lab", "available")
    messages.append(pw.refused(stat=fake_stat(GB2 + 1)))
    aw.cp_rc, aw.cp_out = 1, "x"
    messages.append(aw.go()[1]["message"])
    aw.cp_rc, aw.wait_raises = 0, TimeoutError("slow")
    messages.append(aw.go()[1]["message"])
    aw.wait_raises, aw.start_error = None, FileNotFoundError(2, "no")
    messages.append(aw.go()[1]["message"])
    aw.start_error = PermissionError(13, "no")
    messages.append(aw.go()[1]["message"])
    for m in messages:
        assert len(m) > 10
        for bad in ("Traceback", "File \"", "SELECT", "INSERT", str(aw.uploads), str(pw.uploads)):
            assert bad not in m, (bad, m)
