# Nothing existing: tests of the fake Slurm commands in fake_slurm.py; no maintained tool provides these offline stand-ins.
"""The fake sbatch, squeue and sacct put on PATH (specs/slurm-shim-su, TC-001 ... TC-011, TC-021).

SU rate: UNCONFIRMED (1 SU = 1 core-hour is inferred, not stated by NCHC). These tests touch no rate.
The fakes prove only our own parsing, not what a real Slurm does; the column order is an assumption (欄位順序為假設，未經 nano4 實測).
"""
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

import fake_slurm
from helpers import PLATFORM_DIR

STATES = ["COMPLETED", "FAILED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL"]
SACCT_FULL = ["-n", "-P", "-j", "4242", "-o", "JobID,State,ExitCode,Elapsed,AllocCPUS,Partition"]

pytestmark = pytest.mark.skipif(os.name == "nt", reason="the fakes are POSIX sh scripts")


@pytest.fixture
def fs(tmp_path, monkeypatch):
    return fake_slurm.install(tmp_path, monkeypatch)


def _snapshot(root):
    out = {}
    for p in sorted(Path(root).rglob("*")):
        out[str(p)] = p.stat().st_mtime_ns if p.is_file() else None
    return out


def test_shim_is_first_on_path(fs, tmp_path):
    # TC-001
    for prog in ("sbatch", "squeue", "sacct"):
        found = shutil.which(prog)
        assert found and Path(found).resolve().is_relative_to(tmp_path.resolve()), (prog, found)


def test_path_is_restored_after_the_test(tmp_path):
    # TC-001: self-contained (no reliance on an earlier test): install with its own MonkeyPatch, undo, PATH is clean again
    before = os.environ.get("PATH", "")
    mp = pytest.MonkeyPatch()
    try:
        fake_slurm.install(tmp_path, mp)
        assert "fakeslurm-bin" in os.environ["PATH"]
        assert "ABF_FAKE_SLURM_DIR" in os.environ
    finally:
        mp.undo()
    assert "fakeslurm-bin" not in os.environ.get("PATH", "")
    assert "ABF_FAKE_SLURM_DIR" not in os.environ
    assert os.environ.get("PATH", "") == before


def test_sbatch_prints_job_id_and_logs_call(fs):
    # TC-002
    r = fs.run("sbatch", "--wrap", "true", "-p", "ct56")
    assert r.returncode == 0 and r.stdout.strip() == "Submitted batch job 4242"
    assert any(c.startswith("sbatch ") and "--wrap true -p ct56" in c for c in fs.calls())


@pytest.mark.parametrize("state", STATES)
def test_sacct_state(fs, state):
    # TC-003
    fs.set(4242, state)
    r = fs.run("sacct", "-n", "-P", "-X", "-j", "4242", "-o", "State")
    assert r.returncode == 0 and r.stdout.splitlines() == [state]


def test_sacct_columns_and_states_table(fs):
    # TC-004
    assert fake_slurm.COLUMNS == ("JobID", "State", "ExitCode", "Elapsed", "AllocCPUS", "Partition")
    for s in STATES + ["CANCELLED"]:
        assert fake_slurm.STATES[s]
    assert fake_slurm.STATES["OUT_OF_MEMORY"] == "0:125"
    assert fake_slurm.STATES["TIMEOUT"] == "0:0"
    assert fake_slurm.STATES["FAILED"] == "1:0"
    assert fake_slurm.FAILED_NO_TRACE["exit_code"] == "1:0" and fake_slurm.FAILED_NO_TRACE["trace"] is False
    fs.set(4242, "OUT_OF_MEMORY", elapsed="00:02:03", ncpus=8, partition="ct56")
    r = fs.run("sacct", "-X", *SACCT_FULL)
    assert r.stdout.splitlines() == ["4242|OUT_OF_MEMORY|0:125|00:02:03|8|ct56"]


def test_sacct_cancelled_has_by_uid_tail(fs):
    # TC-004
    fs.set(4242, fake_slurm.CANCELLED_BY)
    r = fs.run("sacct", "-n", "-P", "-X", "-j", "4242", "-o", "State")
    assert r.stdout.strip() == "CANCELLED by 1234"


def test_sacct_multistep_rows(fs):
    # TC-005
    fs.set(4242, "NODE_FAIL")
    full = fs.run("sacct", *SACCT_FULL).stdout.splitlines()
    assert [l.split("|")[0] for l in full] == ["4242", "4242.batch", "4242.extern"]
    assert full[0].split("|")[1] == "NODE_FAIL" and full[1].split("|")[1] == "CANCELLED"
    only = fs.run("sacct", "-X", *SACCT_FULL).stdout.splitlines()
    assert [l.split("|")[0] for l in only] == ["4242"]


def test_squeue_gone_job_prints_nothing(fs):
    # TC-006
    fs.set(4242, "RUNNING", source="squeue")
    assert fs.run("squeue", "-h", "-j", "4242", "-o", "%T").stdout.strip() == "RUNNING"
    fs.set(4242, "PENDING", source="squeue")
    assert fs.run("squeue", "-h", "-j", "4242", "-o", "%T").stdout.strip() == "PENDING"
    r = fs.run("squeue", "-h", "-j", "9999", "-o", "%T")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_sacct_empty_output_is_rc0(fs):
    # TC-007
    r = fs.run("sacct", "-n", "-P", "-X", "-j", "4242", "-o", "State")
    assert r.returncode == 0 and r.stdout == ""


def test_sacct_fail_is_rc1(fs):
    # TC-008
    fs.flag("fail_sacct")
    assert fs.run("sacct", "-n", "-P", "-X", "-j", "4242", "-o", "State").returncode == 1


def test_squeue_invalid_job_is_rc1(fs):
    # TC-008
    fs.flag("invalid_squeue")
    r = fs.run("squeue", "-h", "-j", "4242", "-o", "%T")
    assert r.returncode == 1 and "Invalid job id" in r.stderr


def test_sbatch_fail_is_rc1(fs):
    # TC-008
    fs.flag("fail_sbatch")
    assert fs.run("sbatch", "x.sh").returncode == 1


def test_unconfigured_shim_refuses(fs, monkeypatch):
    # TC-009
    monkeypatch.delenv("ABF_FAKE_SLURM_DIR")
    for prog, args in (("sbatch", ["x.sh"]), ("squeue", ["-j", "1"]), ("sacct", ["-j", "1"])):
        r = fs.run(prog, *args)
        assert r.returncode == 99 and "fake slurm: not configured" in r.stderr


def test_job_id_must_be_digits(fs, tmp_path):
    # TC-010
    before = set(p.name for p in tmp_path.rglob("*"))
    r = fs.run("sacct", "-j", "1; rm -x")
    assert r.returncode == 2
    assert any(c.startswith("sacct ") and "1; rm -x" in c for c in fs.calls())
    after = set(p.name for p in tmp_path.rglob("*"))
    assert after - {"calls.log"} == before - {"calls.log"}


def test_shim_never_writes_outside_tmp(fs, tmp_path, tmp_path_factory):
    # TC-011
    outside = tmp_path_factory.mktemp("outside")
    (outside / "keep").write_text("x")
    cwd = Path(os.getcwd())
    names_before = sorted(p.name for p in cwd.iterdir())
    snap = _snapshot(outside)
    fs.set(4242, "FAILED")
    fs.run("sbatch", "a.sh")
    fs.run("sacct", "-n", "-P", "-j", "4242")
    fs.run("squeue", "-h", "-j", "4242")
    fs.flag("fail_sacct")
    fs.run("sacct", "-j", "4242")
    fs.run("sacct", "-j", "x; touch %s/pwned" % outside)
    assert _snapshot(outside) == snap
    assert sorted(p.name for p in cwd.iterdir()) == names_before


def test_module_docstrings_state_what_is_unconfirmed():
    # TC-020, TC-021
    text = (Path(__file__).parent / "fake_slurm.py").read_text(encoding="utf-8")
    me = Path(__file__).read_text(encoding="utf-8")
    for t in (text, me):
        assert "UNCONFIRMED" in t
    assert "欄位順序為假設，未經 nano4 實測" in text
    assert "not verified" in text and "do not prove" in text
    assert "import station_harness" not in text and "from station_harness" not in text
    assert not re.search(r"(?i)slurm (is|was) verified|已驗證 Slurm", text)
    assert "FAKE_TOOLS" not in text
