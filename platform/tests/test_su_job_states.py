# Nothing existing: tests of how su.py counts tasks the scheduler ended (FAILED, TIMEOUT, OOM, NODE_FAIL); the SU formula and rates file are ours.
"""su.py with the end states of a Slurm job (specs/slurm-shim-su, TC-012 ... TC-020, TC-025).

SU rate: UNCONFIRMED. "1 SU = 1 core-hour" is inferred, not stated by NCHC (configs/sites/su_rates.json, key assumption); every amount
below comes from that one file and every assert message that shows money says UNCONFIRMED.
su.py reads only a task's cpus, realtime (ms) and queue, never its status: these tests pin that. The Elapsed-to-milliseconds helper
here lives in the tests, it is not an estimator. The fake sacct text proves only our parsing, not what a real Slurm prints
(docs/PITFALLS.md item 42); the column order is an assumption (欄位順序為假設，未經 nano4 實測).
"""
import json
import os
import re
import shutil
from pathlib import Path

import pytest

import fake_slurm
from helpers import PLATFORM_DIR, REPO_ROOT

RATES_FILE = REPO_ROOT / "configs" / "sites" / "su_rates.json"
SITE = "taiwania3"       # its partitions all have factor 1 in the rates file
H = 3600000
WHY = "(SU rate UNCONFIRMED: 1 SU = 1 core-hour is inferred)"

pytestmark = pytest.mark.skipif(os.name == "nt", reason="the fakes are POSIX sh scripts")


def su_mod():
    from abf_platform import su
    return su


def rates():
    return su_mod().load_rates(RATES_FILE)


def elapsed_ms(text):
    """[D-]HH:MM:SS to milliseconds (test-side helper only)."""
    days, _, rest = text.rpartition("-")
    h, m, s = (int(x) for x in rest.split(":"))
    return (((int(days or 0) * 24 + h) * 60 + m) * 60 + s) * 1000


def tasks_from_sacct(text, has_trace=True):
    """Only the main row of a job (JobID all digits) becomes a task; .batch and .extern are ignored. None when there is no row."""
    tasks = []
    for line in text.splitlines():
        jid, state, _exit, elapsed, ncpus, part = line.split("|")
        if not jid.isdigit():
            continue
        tasks.append({"name": jid, "status": state.split()[0], "cpus": int(ncpus), "queue": part,
                      "realtime": elapsed_ms(elapsed) if has_trace else None})
    return tasks or None


def one(state, elapsed="01:00:00", ncpus=4, has_trace=True, **kw):
    return tasks_from_sacct(fake_slurm.sacct_rows(4242, state, elapsed=elapsed, ncpus=ncpus, **kw), has_trace)


def calc(tasks, r=None):
    return su_mod().su_of_tasks(tasks, SITE, rates() if r is None else r)


def test_completed_and_failed_tasks_are_charged():
    # TC-012
    for state in ("COMPLETED", "FAILED"):
        out = calc(one(state, "01:30:00", 4))
        assert out["su"] == pytest.approx(4 * 1.5), (state, out, WHY)
        assert out["twd_nstc"] == pytest.approx(out["su"] * rates()["nstc_twd_per_su"]), WHY


def test_timeout_task_is_charged_its_full_walltime():
    # TC-013
    tasks = one("TIMEOUT", "02:00:00", 4)
    assert tasks[0]["realtime"] == 7200000
    out = calc(tasks)
    assert out["su"] == pytest.approx(4 * 2), (out, WHY)


def test_oom_task_with_short_realtime_is_still_charged():
    # TC-014
    tasks = one("OUT_OF_MEMORY", "00:00:30", 8)
    out = calc(tasks)
    assert out["su"] is not None and out["su"] > 0, (out, WHY)
    assert out["su"] == pytest.approx(8 * 30 / 3600), (out, WHY)


@pytest.mark.parametrize("tasks", [
    one("NODE_FAIL", has_trace=False),
    tasks_from_sacct(fake_slurm.sacct_rows(4242, fake_slurm.FAILED_NO_TRACE["state"], exit_code=fake_slurm.FAILED_NO_TRACE["exit_code"]),
                     has_trace=fake_slurm.FAILED_NO_TRACE["trace"]),
], ids=["node_fail", "failed_exit_1_0_no_trace"])
def test_nodefail_task_without_realtime_makes_total_unknown(tasks):
    # TC-015
    assert tasks[0]["realtime"] is None
    out = calc(tasks)
    assert out["su"] is None and out["twd_nstc"] is None, out
    assert any("缺 realtime" in r for r in out["unknown_reasons"]), out


def test_batch_and_extern_rows_are_not_extra_tasks():
    # TC-016
    text = fake_slurm.sacct_rows(4242, "COMPLETED", elapsed="01:00:00", ncpus=2, steps=True)
    assert len(text.splitlines()) == 3
    tasks = tasks_from_sacct(text)
    assert len(tasks) == 1 and tasks[0]["name"] == "4242"
    assert calc(tasks)["su"] == pytest.approx(2.0)
    assert calc(tasks)["su"] == calc(tasks_from_sacct(fake_slurm.sacct_rows(4242, "COMPLETED", ncpus=2, steps=False)))["su"]


def test_empty_sacct_gives_unknown_not_zero(tmp_path, monkeypatch):
    # TC-017 (the empty text comes out of the fake sacct itself)
    fs = fake_slurm.install(tmp_path, monkeypatch)
    out_text = fs.run("sacct", "-n", "-P", "-j", "4242", "-o", "JobID,State,ExitCode,Elapsed,AllocCPUS,Partition").stdout
    assert out_text == ""
    out = su_mod().run_su(tmp_path / "none.db", "run-a", SITE, rates(), lambda i, r: tasks_from_sacct(out_text))
    assert out["su"] is None and out["twd_nstc"] is None, out
    assert out["unknown_reasons"] == [su_mod().NOT_STORED]
    assert any(c.startswith("sacct ") for c in fs.calls()) and all(c.split()[0] in ("sacct", "squeue", "sbatch") for c in fs.calls())


def _index(tmp_path, usage):
    from abf_platform import store
    db = tmp_path / "index.db"
    con = store.connect_index(db)
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at, n_succeeded) "
                    "VALUES ('id-run-a', 's', 'run-a', 'live', 'failed', 1790000000, 1790000100, 3, 0)")
        for u in usage:
            con.execute("INSERT INTO task_usage (run_id, task_key, name, status, cpus, realtime_ms, queue) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        ("id-run-a",) + tuple(u))
    con.close()
    return db


def test_failed_and_aborted_rows_in_task_usage_are_counted(tmp_path):
    # TC-018
    db = _index(tmp_path, [("1:1", "A", "FAILED", 2, H, "ct56"), ("2:1", "B", "ABORTED", 4, H // 2, "ct56")])
    rows = su_mod().run_tasks(db, "run-a")
    assert [r["status"] for r in rows] == ["FAILED", "ABORTED"]
    out = su_mod().run_su(db, "run-a", SITE, rates())
    assert out["su"] == pytest.approx(2 * 1 + 4 * 0.5), (out, WHY)


def test_rate_comes_from_the_one_config_value(tmp_path):
    # TC-019
    data = json.loads(RATES_FILE.read_text(encoding="utf-8"))
    data["nstc_twd_per_su"] = 0.5
    copy = tmp_path / "su_rates.json"
    copy.write_text(json.dumps(data), encoding="utf-8")
    tasks = one("COMPLETED", "02:00:00", 4)
    real, changed = calc(tasks), calc(tasks, su_mod().load_rates(copy))
    assert real["su"] == changed["su"] == pytest.approx(8)
    assert changed["twd_nstc"] == pytest.approx(8 * 0.5), WHY
    assert real["twd_nstc"] == pytest.approx(8 * rates()["nstc_twd_per_su"]), WHY
    # no price literal in the new files (built here so this test does not contain it itself)
    literal = "0" + ".08"
    for name in ("fake_slurm.py", "test_fake_slurm_shim.py", "test_su_job_states.py"):
        assert literal not in (Path(__file__).parent / name).read_text(encoding="utf-8"), name


def test_unconfirmed_is_stated():
    # TC-020
    assert "inferred" in rates()["assumption"]
    here = Path(__file__).parent
    for name in ("fake_slurm.py", "test_fake_slurm_shim.py", "test_su_job_states.py"):
        head = (here / name).read_text(encoding="utf-8").split('"""')[1]
        assert "UNCONFIRMED" in head, name
        assert not re.search(r"(?i)1 SU = 1 core-hour (is|was) (confirmed|verified)", head), name
    assert "UNCONFIRMED" in WHY
    assert "欄位順序為假設，未經 nano4 實測" in (here / "test_su_job_states.py").read_text(encoding="utf-8").split('"""')[1]


def test_tests_never_call_real_slurm(tmp_path, monkeypatch):
    # TC-001
    fs = fake_slurm.install(tmp_path, monkeypatch)
    for prog in ("sbatch", "squeue", "sacct"):
        assert Path(shutil.which(prog)).resolve().is_relative_to(tmp_path.resolve())
    fs.set(4242, "TIMEOUT", elapsed="02:00:00")
    text = fs.run("sacct", "-n", "-P", "-X", "-j", "4242", "-o", "JobID,State,ExitCode,Elapsed,AllocCPUS,Partition").stdout
    assert calc(tasks_from_sacct(text))["su"] == pytest.approx(8)
    assert fs.calls() and all(c.split()[0] in ("sacct", "squeue", "sbatch") for c in fs.calls())


@pytest.mark.parametrize("state", ["COMPLETED", "FAILED", "ABORTED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL"])
def test_status_does_not_change_su(state):
    # TC-025: su.py reads cpus, realtime and queue only, never status; and it never calls sacct
    t = {"name": "t", "status": state, "cpus": 4, "realtime": H, "queue": "ct56"}
    base = calc([dict(t, status="COMPLETED")])
    assert calc([t]) == base and base["su"] == pytest.approx(4), WHY
    src = (PLATFORM_DIR / "abf_platform" / "su.py").read_text(encoding="utf-8")
    assert "sacct" not in src and '"status"' not in src.split("def su_of_tasks")[1].split("def usd_rate")[0]
