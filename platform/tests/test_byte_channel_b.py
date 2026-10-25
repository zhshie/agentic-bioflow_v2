# Nothing existing: searched pytest fixtures for fake subprocess pipes and gcloud emulators; none speaks `gcloud storage cp -`, so a fake program object (FakeFed) and a small sh script stand in for gcloud here, with no network and no real program.
"""byte-channel-b: the agent side of `put_upload` (stream one uploaded file into the person's own cloud prefix, check the cloud size,
remove the staged copy). The TC ids refer to the test cases of this task; BB-nn are the numbers of its plan.
Everything uses fakes for `site.start_fed` and `site.run_fixed`, except the posix tests, which run a real sh script named gcloud."""
import asyncio
import builtins
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import stat as st
import sys
import time
import tracemalloc
from pathlib import Path
from types import SimpleNamespace

import pytest

from helpers import PLATFORM_DIR, db_bytes
from station_harness import mcp_inproc
from test_byte_channel_a import World as PlatWorld
from test_gcb_ce import BEGIN, EMAIL, PROJECT, ip, key_data  # noqa: F401  (ip is a fixture)

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="symbolic links, real pipes and permission bits")
MIB = 1024 * 1024
BUCKET_PREFIX = "gs://lab-bucket/uploads/"
DROP = object()
CANARY_A = "CANARY-A-9f3a51c7"      # in the content of the uploaded file
CANARY_B = "CANARY-B-4d2e88b0"      # in the key file
SRC = PLATFORM_DIR / "abf_station"
T = time.time()
REAL_WHICH = shutil.which


class FakeFed:
    """The program object put_upload gets from site.start_fed: it records, and answers as the scenario says."""

    def __init__(self, w, argv, env):
        self.w, self.argv, self.env = w, argv, env
        self.lengths, self.data, self.closed, self.killed, self.timeouts = [], bytearray(), False, False, []

    def write(self, data):
        w = self.w
        if w.raise_after is not None and len(self.lengths) >= w.raise_after:
            raise BrokenPipeError("gone")
        self.lengths.append(len(data))
        if w.keep:
            self.data += data
        if w.on_write:
            w.on_write(len(self.lengths))

    def close_stdin(self):
        self.closed = True

    def wait(self, timeout):
        self.timeouts.append(timeout)
        if self.w.wait_raises:
            raise self.w.wait_raises
        return self.w.cp_rc, self.w.cp_out

    def kill(self):
        self.killed = True


class World:
    def __init__(self, tmp, mp):
        from abf_station import gcb_preflight, site
        self.tmp, self.mp = Path(tmp), mp
        self.real_start, self.real_run = site.start_fed, site.run_fixed       # the real ones, before the fakes go in
        self.uploads = self.tmp / "uploads"
        self.set_uploads(self.uploads)
        (self.uploads / "alice").mkdir(parents=True, exist_ok=True)
        self.key = self.tmp / "gcp-sa.json"
        self.key.write_text(json.dumps({"type": "service_account", "client_email": EMAIL, "private_key": CANARY_B}))
        mp.setenv("ABF_STATION_GCP_CREDENTIALS", str(self.key))
        mp.delenv("ABF_STATION_PUT_TIMEOUT", raising=False)
        self.feds, self.runs, self.logs = [], [], []
        self.cp_rc, self.cp_out, self.raise_after, self.wait_raises, self.on_write = 0, "", None, None, None
        self.keep, self.start_error = True, None
        self.describe, self.cloud_size, self.on_describe, self.size = None, None, None, 0
        mp.setattr(gcb_preflight.shutil, "which", lambda n: "/usr/bin/gcloud" if n == "gcloud" else None)
        mp.setattr(site, "start_fed", self._start_fed)
        mp.setattr(site, "run_fixed", self._run_fixed)
        self.ctx = SimpleNamespace(site=SimpleNamespace(log=lambda *a: self.logs.append(a)), settings_file=str(self.tmp / "env.yaml"),
                                   platform_url="http://127.0.0.1:1", agent_name="a1")
        self.ce = {"name": "gcb1", "platform": "googlebatch-platform", "project": PROJECT, "location": "europe-west2",
                   "workDir": "gs://lab-bucket/work", "serviceAccountEmail": None, "credentialsId": None}

    def set_uploads(self, path):
        self.uploads = Path(path)
        self.mp.setenv("ABF_STATION_UPLOADS", str(self.uploads))

    # fakes
    def _start_fed(self, argv, env):
        if self.start_error:
            raise self.start_error
        f = FakeFed(self, argv, env)
        self.feds.append(f)
        return f

    def _run_fixed(self, argv, env, timeout):
        self.runs.append((list(argv), dict(env or {}), timeout))
        if argv[:4] != ["gcloud", "storage", "objects", "describe"]:
            raise AssertionError("an unexpected program: %r" % (argv,))
        if self.on_describe:
            self.on_describe()
        if self.describe == "timeout":
            raise TimeoutError("slow")
        if self.describe is not None:
            return self.describe
        return 0, "%d\n" % (self.size if self.cloud_size is None else self.cloud_size)

    # inputs
    def make(self, name="reads.fq", size=None, data=None, owner="alice"):
        folder = self.uploads / owner
        folder.mkdir(parents=True, exist_ok=True)
        if data is None:
            data = os.urandom(size if size is not None else 3 * MIB + 17)
        (folder / name).write_bytes(data)
        self.size = len(data)
        return data

    def path(self, name="reads.fq", owner="alice"):
        return self.uploads / owner / name

    def dest(self, name="reads.fq", owner="alice"):
        return "%s%s/%s" % (BUCKET_PREFIX, owner, name)

    def args(self, **over):
        a = {"ce": dict(self.ce), "owner": "alice", "name": "reads.fq", "dest": None}
        try:
            p = self.uploads / str(a["owner"]) / str(a["name"])
            a["size"] = p.lstat().st_size
        except (OSError, ValueError):
            a["size"] = 1
        a.update(over)
        if a["dest"] is None:
            a["dest"] = self.dest(a["name"], a["owner"])
        return {k: v for k, v in a.items() if v is not DROP}

    def go(self, **over):
        from abf_station import handlers
        return handlers.handle({"kind": "put_upload", "args": self.args(**over)}, self.ctx)

    def snapshot(self):
        out = {}
        for p in sorted(self.uploads.rglob("*")):
            if p.is_file() and not p.is_symlink():
                out[str(p)] = (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
        return out

    def snapshot_of(self, name, owner="alice"):
        p = self.path(name, owner)
        return hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns

    def refused(self, **over):
        """The refusal message; gcloud never started and nothing on disk changed (TC-056)."""
        before = self.snapshot()
        state, res = self.go(**over)
        assert state == "refused" and res["ok"] is False, (state, res)
        assert self.feds == [] and self.runs == []
        assert self.snapshot() == before
        return res["message"]

    def sent(self):
        return b"".join(bytes(f.data) for f in self.feds)


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


# ---- US1: the agent knows the job and streams the file -------------------------------------------------------------------
def test_tc001_put_upload_is_the_last_kind(w):
    # TC-001, BB-01
    from abf_station import handlers
    assert handlers.JOB_KINDS[-1] == "put_upload"
    assert handlers.JOB_KINDS[:-1] == ("preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records",
                                       "read_task_log", "clean_work")


def test_tc002_the_agent_takes_the_keys_the_platform_sends(ip, tmp_path):
    # TC-002, BB-01
    from abf_platform import jobs
    from abf_station import handlers
    aw = PlatWorld(ip, tmp_path)
    (aw.uploads / "alice").mkdir(parents=True)
    (aw.uploads / "alice" / "reads.fq").write_bytes(b"x" * 10)
    jid = jobs.enqueue_put_upload(ip.state_db, ip.tokens, "gcb1", "alice", "reads.fq", aw.uploads, aw.ids["alice"], clock=lambda: T)
    out = jobs.claim(ip.state_db, "ag-alice", lambda: T + 1, tokens_path=ip.tokens)
    assert out["id"] == jid and set(out["args"]) == handlers.ARG_KEYS["put_upload"] == {"ce", "owner", "name", "size", "dest"}


def test_tc003_an_extra_key_is_refused(w):
    # TC-003, BB-02
    from abf_station import handlers
    w.make()
    state, res = handlers.handle({"kind": "put_upload", "args": dict(w.args(), path="/etc/passwd")}, w.ctx)
    assert state == "refused" and re.search(r"not supported|不支援", res["message"]) and w.feds == []


@pytest.mark.parametrize("key", ["ce", "owner", "name", "size", "dest"])
def test_tc004_a_missing_key_is_refused(w, key):
    # TC-004, BB-02
    w.make()
    msg = w.refused(**{key: DROP})
    assert msg and "Traceback" not in msg


def test_tc005_an_unknown_kind_lists_every_kind(w):
    # TC-005, BB-03
    from abf_station import handlers
    state, res = handlers.handle({"kind": "frobnicate", "args": {}}, w.ctx)
    assert state == "refused" and all(k in res["message"] for k in handlers.JOB_KINDS) and "put_upload" in res["message"]


def test_tc006_tc007_tc008_the_good_path(w):
    # TC-006, TC-007, TC-008; BB-04, BB-05
    data = w.make(size=3 * MIB + 17)
    state, res = w.go()
    dest = "gs://lab-bucket/uploads/alice/reads.fq"
    assert state == "done"
    assert res == {"ok": True, "bytes": 3145745, "path": dest,
                   "message": "已上傳 %s（3145745 位元組）；平台主機上的暫存檔已刪除" % dest}
    assert len(w.feds) == 1
    f = w.feds[0]
    assert bytes(f.data) == data and f.closed and not f.killed
    assert f.argv == ["gcloud", "storage", "cp", "-", dest, "--project", "lab-project-1"]


def test_tc009_tc010_the_environment_and_the_key_path(w, monkeypatch):
    # TC-009, TC-010; BB-05
    monkeypatch.setenv("ABF_SOMETHING", "secret-ish")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/elsewhere/key.json")
    w.make(size=1000)
    assert w.go()[0] == "done"
    env = w.feds[0].env
    assert env["CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"] == str(w.key)
    assert not [k for k in env if k.upper().startswith("ABF_")] and "GOOGLE_APPLICATION_CREDENTIALS" not in env
    for argv in [w.feds[0].argv] + [r[0] for r in w.runs]:
        assert all(str(w.key) not in part for part in argv)


def test_tc011_chunks_are_at_most_one_mebibyte(w):
    # TC-011; BB-06
    w.keep = False
    w.make(data=b"abcd" * (10 * MIB))
    assert w.go()[0] == "done"
    assert max(w.feds[0].lengths) <= MIB and sum(w.feds[0].lengths) == 40 * MIB


def test_tc012_the_file_is_never_read_whole(w):
    # TC-012; BB-06
    w.keep = False
    w.make(data=b"abcd" * (10 * MIB))
    tracemalloc.start()
    try:
        state, _ = w.go()
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert state == "done" and peak < 8 * MIB, peak


def test_tc013_the_same_file_twice_overwrites(w):
    # TC-013; BB-07
    for _ in range(2):
        w.make(size=5000)
        assert w.go()[0] == "done"
    assert len(w.feds) == 2 and all("--no-clobber" not in f.argv for f in w.feds)


def fake_gcloud(w, monkeypatch, body, size_line="0"):
    """A real sh script named gcloud first on PATH. It records its arguments in argv.txt; `body` is what it does for `cp`."""
    from abf_station import gcb_preflight, site
    bindir = w.tmp / "bin"
    bindir.mkdir()
    script = bindir / "gcloud"
    script.write_text("#!/bin/sh\ncase \"$2\" in\n  cp)\n    printf '%%s\\n' gcloud \"$@\" > '%s/argv.txt'\n    %s\n    ;;\n"
                      "  objects) echo %s ;;\nesac\n" % (w.tmp, body, size_line))
    script.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setattr(gcb_preflight.shutil, "which", REAL_WHICH)
    monkeypatch.setattr(site, "start_fed", w.real_start)
    monkeypatch.setattr(site, "run_fixed", w.real_run)


@posix_only
def test_tc014_tc015_a_real_pipe_carries_the_bytes(w, monkeypatch):
    # TC-014, TC-015; BB-24
    data = w.make(size=5 * MIB)
    fake_gcloud(w, monkeypatch, "cat > '%s/received.bin'" % w.tmp, size_line=str(5 * MIB))
    state, res = w.go()
    assert state == "done" and res["bytes"] == 5242880 and res["ok"] is True
    assert (w.tmp / "received.bin").read_bytes() == data
    assert (w.tmp / "argv.txt").read_text().splitlines() == ["gcloud", "storage", "cp", "-", w.dest(), "--project", "lab-project-1"]


@posix_only
def test_tc016_a_program_that_quits_early_does_not_hang_the_agent(w, monkeypatch):
    # TC-016; BB-25
    w.make(size=40 * MIB)
    fake_gcloud(w, monkeypatch, "head -c 1024 > /dev/null; echo oops >&2; exit 1")
    t0 = time.monotonic()
    state, res = w.go()
    assert time.monotonic() - t0 < 20 and state == "error" and res["ok"] is False
    assert w.path().exists()


@posix_only
def test_tc017_a_program_that_never_reads_is_killed_at_the_timeout(w, monkeypatch):
    # TC-017; BB-26
    from abf_station import site
    w.make(size=1000)
    fake_gcloud(w, monkeypatch, "exec sleep 60")
    monkeypatch.setenv("ABF_STATION_PUT_TIMEOUT", "1")
    started = []

    def spy(argv, env):
        started.append(w.real_start(argv, env))
        return started[-1]

    monkeypatch.setattr(site, "start_fed", spy)
    state, res = w.go()
    assert state == "error" and res["ok"] is False and "逾時" in res["message"]
    assert started[0]._proc.poll() is not None


@posix_only
def test_tc018_a_noisy_stderr_does_not_stall_the_copy(w, monkeypatch):
    # TC-018; BB-27
    w.make(size=2000)
    fake_gcloud(w, monkeypatch, "cat > /dev/null; head -c 1048576 /dev/zero | tr '\\000' 'Q' >&2", size_line="2000")
    state, res = w.go()
    assert state == "done" and res["ok"] is True and "QQQQ" not in json.dumps(res)


def test_tc019_the_limit_itself_passes(w, monkeypatch):
    # TC-019; BB-18
    from abf_station import put_upload
    w.keep = False
    w.make(size=10)
    real_stat = os.stat(w.path())
    n = 2_000_000_000
    left, nonempty = [n], [0]

    def fake_read(fd, k):
        take = min(k, left[0])
        left[0] -= take
        nonempty[0] += 1 if take else 0
        return bytes(take)

    monkeypatch.setattr(put_upload, "FSTAT", lambda fd: SimpleNamespace(st_mode=st.S_IFREG | 0o644, st_size=n, st_dev=real_stat.st_dev,
                                                                       st_ino=real_stat.st_ino))
    monkeypatch.setattr(put_upload, "READ", fake_read)
    w.cloud_size = n
    state, res = w.go(size=n)
    assert state == "done" and res["bytes"] == n and nonempty[0] == math.ceil(n / MIB) == 1908


def aw_world(ip, tmp_path, w):
    aw = PlatWorld(ip, tmp_path)
    (aw.uploads / "alice").mkdir(parents=True, exist_ok=True)
    w.set_uploads(aw.uploads)
    return aw


def enqueue_claim_handle(ip, aw, w, name="reads.fq"):
    from abf_platform import jobs
    from abf_station import handlers
    jid = jobs.enqueue_put_upload(ip.state_db, ip.tokens, "gcb1", "alice", name, aw.uploads, aw.ids["alice"], clock=lambda: T)
    out = jobs.claim(ip.state_db, "ag-alice", lambda: T + 1, tokens_path=ip.tokens)
    state, res = handlers.handle({"kind": out["kind"], "args": out["args"]}, w.ctx)
    return jid, out, state, res


def test_tc020_the_whole_road_in_one_process(ip, tmp_path, w):
    # TC-020, BB-31
    from abf_platform import jobs
    aw = aw_world(ip, tmp_path, w)
    data = w.make(size=70000)
    jid, out, state, res = enqueue_claim_handle(ip, aw, w)
    assert state == "done"
    assert jobs.take_result(ip.state_db, "ag-alice", jid, state, res, lambda: T + 2)[0] == 200
    final = asyncio.run(jobs.wait_for_result(ip.state_db, jid, clock=lambda: T + 3))
    assert final["ok"] is True and final["result"]["bytes"] == 70000
    assert final["result"]["path"] == "gs://lab-bucket/uploads/alice/reads.fq" and w.sent() == data


# ---- US2: check the cloud size, then remove the staged copy -----------------------------------------------------------------
def test_tc021_the_describe_command(w):
    # TC-021
    w.make(size=1000)
    assert w.go()[0] == "done"
    argv, env, timeout = w.runs[0]
    assert argv == ["gcloud", "storage", "objects", "describe", w.dest(), "--project", "lab-project-1", "--format=value(size)"]
    assert timeout == 60 and env == w.feds[0].env
    assert not [k for k in env if k.upper().startswith("ABF_")] and "GOOGLE_APPLICATION_CREDENTIALS" not in env
    assert "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE" in env and all(str(w.key) not in p for p in argv)


def test_tc022_spaces_around_the_number_are_fine(w):
    # TC-022
    w.make(size=3000)
    w.describe = (0, "  3000\n")
    state, res = w.go()
    assert state == "done" and not w.path().exists() and "已刪除" in res["message"]


def test_tc023_tc024_a_matching_size_removes_only_that_file(w):
    # TC-023, TC-024
    w.make(name="other.fq", size=50)
    w.make(name="x.fq", size=60, owner="bob")
    w.make(size=4000)
    other, bobs = w.snapshot_of("other.fq"), w.snapshot_of("x.fq", "bob")
    state, res = w.go()
    assert state == "done" and res["ok"] is True and "平台主機上的暫存檔已刪除" in res["message"]
    assert not w.path().exists() and (w.uploads / "alice").is_dir() and (w.uploads / "bob").is_dir()
    assert w.snapshot_of("other.fq") == other and w.snapshot_of("x.fq", "bob") == bobs


def test_tc084_the_only_file_goes_and_the_folder_stays(w):
    # TC-084
    w.make(size=100)
    assert w.go()[0] == "done"
    assert list((w.uploads / "alice").iterdir()) == [] and (w.uploads / "alice").is_dir() and w.uploads.is_dir()


def test_tc025_a_different_cloud_size_keeps_the_file(w):
    # TC-025
    data = w.make(size=2000)
    w.cloud_size = 1999
    state, res = w.go()
    assert res["ok"] is False and res["message"] == "雲端物件大小與本機不符，暫存檔保留，請重新上傳"
    assert w.path().read_bytes() == data


def _unknown(w):
    data = w.make(size=2000)
    state, res = w.go()
    assert state == "done" and res["ok"] is True
    assert res["message"] == "已上傳 %s（2000 位元組），但沒能核對雲端大小；暫存檔保留" % w.dest()
    assert w.path().read_bytes() == data


def test_tc026_describe_fails(w):
    # TC-026
    w.describe = (1, "boom")
    _unknown(w)


def test_tc027_describe_times_out(w):
    # TC-027
    w.describe = "timeout"
    _unknown(w)


@pytest.mark.parametrize("text", ["", "abc", "3145745 bytes", "-5", "1e6", "２０００"])
def test_tc028_an_answer_that_is_not_a_plain_number_is_no_answer(w, text):
    # TC-028
    w.describe = (0, text)
    _unknown(w)


def test_tc029_a_swapped_file_is_not_removed(w):
    # TC-029
    w.make(size=2000)

    def swap():
        w.path().unlink()
        w.path().write_bytes(b"a brand new file")

    w.on_describe = swap
    state, res = w.go()
    assert res["ok"] is True and res["message"].endswith("；暫存檔沒刪掉，請管理者清理") and "2000 位元組" in res["message"]
    assert w.path().read_bytes() == b"a brand new file"


@posix_only
def test_tc030_a_link_put_in_the_way_is_not_followed(w):
    # TC-030
    w.make(size=2000)
    outside = w.tmp / "outside.txt"
    outside.write_bytes(b"precious")

    def swap():
        w.path().unlink()
        w.path().symlink_to(outside)

    w.on_describe = swap
    state, res = w.go()
    assert res["ok"] is True and res["message"].endswith("；暫存檔沒刪掉，請管理者清理")
    assert w.path().is_symlink() and outside.read_bytes() == b"precious"


@posix_only
def test_tc031_a_failed_removal_is_no_crash(w, monkeypatch):
    # TC-031
    from abf_station import put_upload

    def deny(path):
        raise PermissionError("read-only folder")

    w.make(size=2000)
    monkeypatch.setattr(put_upload, "UNLINK", deny)
    state, res = w.go()
    assert state == "done" and res["ok"] is True and res["message"].endswith("；暫存檔沒刪掉，請管理者清理")
    assert w.path().exists()


def test_tc032_a_failed_copy_keeps_the_file_and_asks_nothing_more(w):
    # TC-032
    w.make(size=2000)
    before = w.snapshot()
    w.cp_rc, w.cp_out = 1, "ERROR: something"
    state, res = w.go()
    assert state == "error" and res["ok"] is False and w.runs == [] and w.snapshot() == before


@pytest.mark.parametrize("how", ["short", "long"])
def test_tc033_tc035_a_file_that_changes_midway_aborts(w, how):
    # TC-033, TC-035; BB-19
    w.make(size=3 * MIB)
    path = w.path()

    def meddle(n):
        if n == 1:
            if how == "short":
                os.truncate(path, MIB + MIB // 2)
            else:
                with open(path, "ab") as fh:
                    fh.write(b"z" * MIB)

    w.on_write = meddle
    state, res = w.go()
    f = w.feds[0]
    assert state == "error" and res["ok"] is False and f.killed
    assert res["bytes"] == sum(f.lengths) and w.runs == [] and w.path().exists()
    assert "bucket 上可能需要檢查" in res["message"] and w.dest() in res["message"]


def test_tc033_a_reader_that_gives_a_block_too_many(w, monkeypatch):
    # TC-033, BB-19 (the reader side)
    from abf_station import put_upload
    w.make(size=2 * MIB)
    real = os.read
    seen = [0]

    def read(fd, n):
        seen[0] += 1
        return real(fd, n) if seen[0] < 3 else b"q" * n

    monkeypatch.setattr(put_upload, "READ", read)
    state, res = w.go()
    assert state == "error" and w.feds[0].killed and res["bytes"] == 2 * MIB


def test_tc034_tc035_a_wait_that_times_out(w):
    # TC-034, TC-035; BB-23
    w.make(size=2000)
    w.wait_raises = TimeoutError("slow")
    state, res = w.go()
    assert state == "error" and "逾時" in res["message"] and w.feds[0].killed and w.path().exists()
    assert "bucket 上可能需要檢查" in res["message"]


def test_tc036_tc081_no_command_ever_deletes_or_resumes(w):
    # TC-036, TC-081
    w.make(size=2000)
    w.go()
    w.make(size=2000)
    w.cp_rc = 1
    w.go()
    w.make(size=2000)
    w.cp_rc, w.wait_raises = 0, TimeoutError("slow")
    w.go()
    cmds = [f.argv for f in w.feds] + [r[0] for r in w.runs]
    assert all(c[:3] == ["gcloud", "storage", "cp"] or c[:4] == ["gcloud", "storage", "objects", "describe"] for c in cmds)
    flat = {part for c in cmds for part in c}
    assert not flat & {"rm", "delete", "--no-clobber", "-I", "--continue-on-error", "--content-md5", "--hash"}
    assert not [p for p in flat if "resum" in p or "md5" in p or "hash" in p]


# ---- US3: the agent checks again ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("dest", ["gs://lab-bucket/uploads/bob/reads.fq", "gs://other-bucket/uploads/alice/reads.fq",
                                  "gs://lab-bucket/work/x", "gs://lab-bucket/uploads/reads.fq", "gs://lab-bucket/uploads/alice",
                                  "gs://lab-bucket/uploads/alice/", "gs://lab-bucket/uploads/alice/../bob/x",
                                  "gs://lab-bucket/uploads/alice/%2e%2e", "gs://lab-bucket/uploads/alice/re\x07ads.fq",
                                  "s3://lab-bucket/uploads/alice/reads.fq", "https://lab-bucket/uploads/alice/reads.fq",
                                  " gs://lab-bucket/uploads/alice/reads.fq", "gs://lab-bucket/uploads/alice/reads.fq ",
                                  "gs://lab-bucket/uploads/alice/b.fq", 5])
def test_tc037_to_tc041_a_destination_outside_the_own_prefix(w, dest):
    # TC-037..TC-041; BB-08..BB-12
    w.make()
    assert "上傳前綴" in w.refused(dest=dest)


@pytest.mark.parametrize("ce", [{"platform": "slurm-platform"}, {"workDir": "/data/work"}, {"workDir": "gs://Bad_Bucket/work"},
                                {"workDir": "gs://ab/work"}, {"project": "x"}])
def test_tc042_a_bad_environment(w, ce):
    # TC-042; BB-13
    w.make(size=100)
    w.refused(ce=dict(w.ce, **ce))


@pytest.mark.parametrize("field,bad", [("owner", "al/ice"), ("owner", "al\\ice"), ("owner", ".."), ("owner", "a\0b"), ("owner", ""),
                                       ("owner", "a" * 256), ("owner", 5), ("name", "a/b"), ("name", "a\\b"), ("name", ".."),
                                       ("name", "a\0b"), ("name", ""), ("name", "n" * 256), ("name", ["x"])])
def test_tc043_a_bad_owner_or_name_is_refused(w, field, bad):
    # TC-043; BB-14
    w.make()
    msg = w.refused(**{field: bad})
    if isinstance(bad, str) and len(bad) >= 3:
        assert bad not in msg


def test_tc044_a_marker_in_a_bad_value_is_not_echoed(w):
    # TC-044
    for field in ("owner", "name"):
        assert "MARK-9e1f" not in w.refused(**{field: "MARK-9e1f/" + field, "dest": w.dest()})
    assert "MARK-9e1f" not in w.refused(dest="gs://lab-bucket/uploads/MARK-9e1f/x")


def test_tc045_a_tampered_job_is_refused_by_the_agent_itself(ip, tmp_path, w):
    # TC-045; BB-32
    from abf_platform import jobs
    from abf_station import handlers
    aw = aw_world(ip, tmp_path, w)
    w.make(size=500)
    jid = jobs.enqueue_put_upload(ip.state_db, ip.tokens, "gcb1", "alice", "reads.fq", aw.uploads, aw.ids["alice"], clock=lambda: T)
    con = sqlite3.connect(str(ip.state_db))
    args = json.loads(con.execute("SELECT args_json FROM jobs WHERE id = ?", (jid,)).fetchone()[0])
    args["dest"] = "gs://lab-bucket/uploads/bob/reads.fq"
    with con:
        con.execute("UPDATE jobs SET args_json = ? WHERE id = ?", (json.dumps(args), jid))
    con.close()
    out = jobs.claim(ip.state_db, "ag-alice", lambda: T + 1, tokens_path=ip.tokens)
    state, res = handlers.handle({"kind": out["kind"], "args": out["args"]}, w.ctx)
    assert state == "refused" and w.feds == []
    assert jobs.take_result(ip.state_db, "ag-alice", jid, state, res, lambda: T + 2)[0] == 200
    assert asyncio.run(jobs.wait_for_result(ip.state_db, jid, clock=lambda: T + 3))["state"] == "refused"


def test_tc046_another_users_file_is_never_opened(w, monkeypatch):
    # TC-046
    from abf_station import put_upload
    w.make(name="reads.fq", size=100, owner="bob")
    opened = []
    real = os.open
    monkeypatch.setattr(put_upload, "OPEN", lambda p, *a, **k: (opened.append(str(p)), real(p, *a, **k))[1])
    before = w.snapshot_of("reads.fq", "bob")
    w.refused(name="../bob/reads.fq", size=100)
    assert opened == [] and w.snapshot_of("reads.fq", "bob") == before


def test_tc047_no_upload_folder_is_configured(w, monkeypatch):
    # TC-047; BB-15
    w.make(size=100)
    a_file = w.tmp / "plain.txt"
    a_file.write_text("x")
    for value in (None, "relative/path", str(w.tmp / "nope"), str(a_file)):
        if value is None:
            monkeypatch.delenv("ABF_STATION_UPLOADS")
        else:
            monkeypatch.setenv("ABF_STATION_UPLOADS", value)
        assert "ABF_STATION_UPLOADS" in w.refused(size=100)


def test_tc048_a_missing_file_or_a_folder(w):
    # TC-048; BB-16
    w.refused(size=5)
    (w.uploads / "alice" / "reads.fq").mkdir()
    w.refused(size=5)


@posix_only
def test_tc049_a_link_for_a_file_is_not_followed(w, monkeypatch):
    # TC-049; BB-16
    from abf_station import put_upload
    outside = w.tmp / "outside.bin"
    outside.write_bytes(b"s" * 300)
    (w.uploads / "alice" / "reads.fq").symlink_to(outside)
    reads = []
    real = os.read
    monkeypatch.setattr(put_upload, "READ", lambda fd, n: (reads.append(n), real(fd, n))[1])
    w.refused(size=300)
    assert reads == [] and outside.read_bytes() == b"s" * 300


@posix_only
def test_tc050_a_link_for_the_owner_folder_is_not_followed(w):
    # TC-050; BB-16
    elsewhere = w.tmp / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "reads.fq").write_bytes(b"s" * 300)
    (w.uploads / "alice").rmdir()
    (w.uploads / "alice").symlink_to(elsewhere)
    w.refused(size=300)
    assert (elsewhere / "reads.fq").read_bytes() == b"s" * 300


@pytest.mark.parametrize("real_size", [101, 99])
def test_tc051_a_file_that_is_not_the_size_queued(w, real_size):
    # TC-051; BB-17
    w.make(size=real_size)
    assert "重新上傳" in w.refused(size=100)


@pytest.mark.parametrize("size", [0, -1, True, "5", 2_000_000_001, 5.0, None])
def test_tc052_a_size_out_of_bounds(w, size):
    # TC-052; BB-18
    w.make(size=5)
    w.refused(size=size)


def test_tc053_no_gcloud(w, monkeypatch):
    # TC-053; BB-20
    from abf_station import gcb_preflight
    w.make(size=100)
    monkeypatch.setattr(gcb_preflight.shutil, "which", lambda n: None)
    state, res = w.go()
    assert state == "error" and res["ok"] is False and "沒裝 gcloud" in res["message"] and w.feds == []


def test_tc054_no_key_file(w):
    # TC-054; BB-21
    w.make(size=100)
    w.key.unlink()
    for _ in range(2):
        state, res = w.go()
        assert state == "error" and res["ok"] is False and "找不到金鑰檔" in res["message"] and str(w.key) not in json.dumps(res)
        assert w.feds == [] and w.path().exists()
        w.key.mkdir()


def test_tc055_the_key_file_is_never_read(w, monkeypatch):
    # TC-055; BB-21
    w.key.write_text("{ not json " + CANARY_B)
    w.make(size=100)
    opened = []
    real_open = builtins.open
    monkeypatch.setattr(builtins, "open", lambda f, *a, **k: (opened.append(str(f)), real_open(f, *a, **k))[1])
    real_os_open = os.open
    monkeypatch.setattr(os, "open", lambda p, *a, **k: (opened.append(str(p)), real_os_open(p, *a, **k))[1])
    state, res = w.go()
    assert state == "done" and str(w.key) not in opened and CANARY_B not in json.dumps(res)


def test_tc056_a_refusal_never_touches_the_file(w):
    # TC-056 (every refused case above already checks the folder is unchanged; this one is the plain sample)
    data = w.make(size=300)
    w.refused(dest="gs://lab-bucket/uploads/bob/reads.fq")
    assert w.path().read_bytes() == data


def test_tc057_tc058_what_gcloud_says_is_cleaned(w):
    # TC-057, TC-058; BB-22
    w.make(size=100)
    block = BEGIN + "\nMARKERBODYQQ\n-----END PRIVATE KEY" + "-----"
    token = "Ab1" * 13 + "Z"
    w.cp_rc = 1
    w.cp_out = "%s\n%s\nfailed at /home/alice/uploads/reads.fq\n" % (block, token)
    state, res = w.go()
    text = json.dumps(res, ensure_ascii=False)
    assert state == "error" and res["ok"] is False
    assert BEGIN not in text and "MARKERBODYQQ" not in text and token not in text and "/home/alice/uploads" not in text
    assert "[hidden]" in res["message"] and len(res["message"]) < 600


def test_tc057_a_long_output_is_cut(w):
    # TC-057
    w.make(size=100)
    w.cp_rc, w.cp_out = 1, "word " * 2000
    state, res = w.go()
    assert len(res["message"]) < 600


# ---- US4: nothing leaks --------------------------------------------------------------------------------------------------------
def leak_runs(w):
    """Run the success path, the changed-midway path and the failing-with-a-key path; give back every result."""
    out = []
    w.make(data=(CANARY_A.encode() * 70000)[:3 * MIB])
    out.append(w.go())
    w.make(data=(CANARY_A.encode() * 70000)[:3 * MIB])
    path = w.path()
    w.on_write = lambda n: os.truncate(path, MIB + MIB // 2) if n == 1 else None
    out.append(w.go())
    w.on_write = None
    w.make(data=(CANARY_A.encode() * 10)[:100])
    w.cp_rc = 1
    w.cp_out = BEGIN + "\n" + CANARY_B + "\n-----END PRIVATE KEY" + "-----\n" + CANARY_B
    out.append(w.go())
    return out


def test_tc059_tc060_tc062_no_canary_and_no_log(w, capsys):
    # TC-059, TC-060, TC-062; BB-28
    from abf_platform import jobs
    results = leak_runs(w)
    seen = capsys.readouterr()
    pieces = [seen.out, seen.err, json.dumps(w.logs, default=str), json.dumps(results, ensure_ascii=False)]
    pieces += [json.dumps(jobs.clean_result("put_upload", r), ensure_ascii=False) for _, r in results]
    for text in pieces:
        assert CANARY_A not in text and CANARY_B not in text and "private_key" not in text
    assert w.logs == [] and seen.out == "" and seen.err == ""


def test_tc061_tc062_the_platform_database_holds_no_canary(ip, tmp_path, w):
    # TC-061, TC-062; BB-28
    from abf_platform import jobs
    aw = aw_world(ip, tmp_path, w)
    w.make(data=(CANARY_A.encode() * 70)[:900])
    w.cp_rc, w.cp_out = 1, CANARY_B + " " + BEGIN
    jid, out, state, res = enqueue_claim_handle(ip, aw, w)
    assert state == "error"
    assert jobs.take_result(ip.state_db, "ag-alice", jid, state, res, lambda: T + 2)[0] == 200
    dump = db_bytes(ip.state_db, ip.tokens, ip.index)
    assert CANARY_A.encode() not in dump and CANARY_B.encode() not in dump and b"private_key" not in dump


def test_tc063_the_source_of_put_upload():
    # TC-063, BB-29
    text = (SRC / "put_upload.py").read_text(encoding="utf-8")
    for word in ("print(", ".log(", "logging", "subprocess", "shell=True", "os.system", "while", "Thread(", "listen", "bind",
                 "input(", "daemon", "google.cloud", "storage cp"):
        assert word not in text, word
    first = text.splitlines()[0]
    assert first.startswith("# Nothing existing:") and len(first.split(":", 1)[1].strip()) >= 15


def test_tc064_only_site_imports_subprocess():
    # TC-064, BB-30
    importing = [p.name for p in SRC.glob("*.py")
                 if re.search(r"^\s*(import subprocess|from subprocess import)", p.read_text(encoding="utf-8"), re.M)]
    assert importing == ["site.py"]


def test_tc065_the_fed_class_keeps_nothing_and_says_nothing():
    # TC-065; A-2, A-3
    import inspect
    from abf_station import site
    code = inspect.getsource(site.Fed) + inspect.getsource(site.start_fed)
    for word in ("print(", ".log(", "logging", "shell=True", "os.system"):
        assert word not in code, word
    whole = (SRC / "site.py").read_text(encoding="utf-8")
    assert "shlex.quote" in whole and "on_site.sh" in whole
    assert not re.search(r"self\.\w*(data|buf|kept|seen)\w*\s*\+?=", code)


def test_tc066_a_program_that_cannot_start(w):
    # TC-066; A-1
    w.make(size=100)
    w.start_error = FileNotFoundError(2, "No such file", "/secret/place/gcloud")
    state, res = w.go()
    assert state == "error" and res["ok"] is False and res["message"]
    assert "/secret" not in res["message"] and "Traceback" not in res["message"] and w.path().exists()


@posix_only
def test_tc067_close_and_kill_are_safe_twice():
    # TC-067; A-2
    from abf_station import site
    fed = site.start_fed(["sleep", "30"], dict(os.environ))
    fed.close_input()
    fed.close_input()
    fed.kill()
    fed.kill()
    assert fed._proc.poll() is not None and fed._err.closed


@posix_only
def test_tc068_wait_gives_the_code_and_two_thousand_characters():
    # TC-068; A-2
    from abf_station import site
    fed = site.start_fed(["sh", "-c", "head -c 5000 /dev/zero | tr '\\000' 'e' >&2; exit 3"], dict(os.environ))
    fed.close_stdin()
    rc, text = fed.wait(20)
    assert rc == 3 and text == "e" * 2000
    slow = site.start_fed(["sleep", "30"], dict(os.environ))
    with pytest.raises(TimeoutError):
        slow.wait(0.2)
    slow.kill()


def test_tc069_the_new_imports():
    # TC-069; A-3
    import ast
    names = set()
    for node in ast.walk(ast.parse((SRC / "site.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module.split(".")[0])
    assert names == {"os", "shlex", "subprocess", "tempfile", "pathlib"}
    body = (SRC / "put_upload.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(google|boto|azure|requests|httpx|socket)", body, re.M)


def test_tc080_nothing_extra_is_asked_or_hashed(w):
    # TC-080, TC-081
    from abf_station import put_upload
    assert put_upload.ARGS == {"ce", "owner", "name", "size", "dest"} and not [k for k in put_upload.ARGS if "confirm" in k]
    w.make(size=3000)
    assert w.go()[0] == "done"
    text = (SRC / "put_upload.py").read_text(encoding="utf-8")
    assert not re.search(r"hashlib|sha256|md5|crc", text)


def test_tc085_the_generic_queue_refuses_put_upload(ip, tmp_path):
    # TC-085
    from abf_platform import jobs
    PlatWorld(ip, tmp_path)
    with pytest.raises(jobs.JobRefused) as e:
        jobs._enqueue(ip.state_db, "gcb1", "put_upload", None, lambda: T, None)
    assert "enqueue_put_upload" in str(e.value)


def test_tc086_no_chat_tool_can_upload(ip):
    # TC-086
    tools, _ = mcp_inproc(ip.index, [])
    assert tools and not [t.name for t in tools if "upload" in t.name.lower()]


def test_tc087_the_copy_command_text_lives_only_in_cloud_store():
    # TC-087
    holders = sorted(p.name for p in PLATFORM_DIR.glob("abf_*/**/*.py") if "storage cp" in p.read_text(encoding="utf-8"))
    assert holders == ["cloud_store.py"]


def test_tc088_every_failure_speaks_plainly(w):
    # TC-088
    messages = []
    w.make(size=100)
    for over in ({"dest": "gs://x/y"}, {"size": 7}, {"name": "../x"}, {"owner": "bad/owner"}):
        messages.append(w.refused(**over))
    w.cp_rc, w.cp_out = 1, "x"
    messages.append(w.go()[1]["message"])
    w.cp_rc = 0
    w.make(size=100)
    w.wait_raises = TimeoutError("t")
    messages.append(w.go()[1]["message"])
    w.key.unlink()
    messages.append(w.go()[1]["message"])
    for m in messages:
        assert m and not re.search(r"Traceback|SELECT|File \"", m) and str(w.uploads) not in m and str(w.key) not in m
