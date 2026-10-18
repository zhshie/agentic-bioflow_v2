# Nothing existing: tests of the SU formula and the estimate_su action (spec: specs/estimate-su); the formula, the rates file and the ownership rule are ours.
"""estimate_su: the SU a run used, from its trace (issue #119). Test cases TC-001 ... TC-C05 are named in the comments,
see specs/estimate-su/test-case.md."""
import asyncio
import json
import re
import sqlite3
import time
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT, own_runs

RATES_FILE = REPO_ROOT / "configs" / "sites" / "su_rates.json"
LEDGER = REPO_ROOT / "specs" / "estimate-su" / "ledger.md"
SU_PY = PLATFORM_DIR / "abf_platform" / "su.py"
H = 3600000     # one hour in milliseconds, the unit of Nextflow's realtime


def rates(p1=1.5, p2=2):
    return {"nstc_twd_per_su": 0.08, "academic_twd_per_su": 0.24,
            "sites": {"testsite": {"partitions": {"p1": {"factor": p1}, "p2": {"factor": p2}}}}}


def two_tasks():
    return [{"name": "A", "queue": "p1", "cpus": 4, "realtime": 2 * H},
            {"name": "B", "queue": "p2", "cpus": 2, "realtime": H // 2}]


def su_mod():
    from abf_platform import su
    return su


def calc(tasks, r=None, site="testsite"):
    return su_mod().su_of_tasks(tasks, site, rates() if r is None else r)


# ---- US1 -----------------------------------------------------------------------------------------------------------

def test_tc001_formula_on_two_tasks():
    # TC-001
    out = calc(two_tasks())
    assert out["su"] == 14 and out["unknown_reasons"] == []


def test_tc002_money():
    # TC-002
    out = calc(two_tasks())
    assert abs(out["twd_nstc"] - 1.12) < 1e-9 and abs(out["twd_academic"] - 3.36) < 1e-9


def test_tc003_factor_comes_from_the_table():
    # TC-003
    assert calc(two_tasks(), rates(p1=3))["su"] == 26


def test_tc004_realtime_is_milliseconds_as_in_the_fixtures():
    # TC-004
    fx = (PLATFORM_DIR / "tests" / "fixtures" / "payloads" / "fail_run.json").read_text(encoding="utf-8")
    assert '"realtime"' in fx       # the field exists in what Nextflow really sent
    assert calc([{"queue": "p1", "cpus": 1, "realtime": 3600000}])["su"] == 1.5


# ---- US2 -----------------------------------------------------------------------------------------------------------

def _unknown(out, *words):
    assert out["su"] is None and out["twd_nstc"] is None and out["twd_academic"] is None
    text = " ".join(out["unknown_reasons"])
    assert out["unknown_reasons"] and all(w in text for w in words), text


def test_tc005_null_factor():
    # TC-005
    _unknown(calc([{"queue": "p1", "cpus": 4, "realtime": 2 * H}], rates(p1=None)), "p1")


def test_tc006_partition_not_in_table():
    # TC-006
    _unknown(calc([{"queue": "p9", "cpus": 1, "realtime": H}]), "p9")


def test_tc007_one_unknown_task_makes_the_total_unknown():
    # TC-007
    tasks = [two_tasks()[0], {"name": "B", "queue": "p2", "cpus": 2, "realtime": H}]
    _unknown(calc(tasks, rates(p2=None)), "p2")


def test_tc008_no_cpus():
    # TC-008
    for t in ({"queue": "p1", "realtime": H}, {"queue": "p1", "cpus": None, "realtime": H}):
        _unknown(calc([t]), "cpus")


def test_tc009_no_realtime():
    # TC-009
    _unknown(calc([{"queue": "p1", "cpus": 1, "realtime": None}]), "realtime")


def test_tc010_every_bad_task_is_listed():
    # TC-010
    out = calc([{"name": "T1", "queue": "p1", "realtime": H}, {"name": "T2", "queue": "p2", "cpus": 1, "realtime": H}], rates(p2=None))
    assert out["su"] is None and len(out["unknown_reasons"]) == 2
    assert "cpus" in out["unknown_reasons"][0] and "p2" in out["unknown_reasons"][1]


def test_tc011_unknown_site():
    # TC-011
    _unknown(calc(two_tasks(), site="nosuchsite"), "nosuchsite")


def test_tc012_rates_file_unreadable(tmp_path):
    # TC-012
    su = su_mod()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    for p in (tmp_path / "missing.json", bad):
        assert su.load_rates(p) is None
        _unknown(su.su_of_tasks(two_tasks(), "testsite", su.load_rates(p)), "費率檔")


def test_tc013_real_rates_file_has_no_factor_for_ngs7G():
    # TC-013
    su = su_mod()
    _unknown(su.su_of_tasks([{"queue": "ngs7G", "cpus": 1, "realtime": H}], "nchc", su.load_rates()), "ngs7G")


# ---- a small index with runs and their owners ---------------------------------------------------------------------

def _index(tmp_path, runs):
    """runs: (name, owner user id, started_at epoch). Returns (index path, platform path)."""
    from abf_platform import store
    db, plat = tmp_path / "index.db", tmp_path / "platform.db"
    con = store.connect_index(db)
    with con:
        for name, _, started in runs:
            con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at) "
                        "VALUES (?, ?, ?, 'live', 'succeeded', ?, ?, 3)", ("id-" + name, "s-" + name, name, started, started + 5))
    con.close()
    store.connect_state(plat).close()
    for name, owner, _ in runs:
        own_runs(plat, owner, [name])
    return db, plat


def _caller(uid):
    from abf_platform import actions
    return actions.Caller(uid, "u%d" % uid, "lab")


KEYS = {"su", "twd_nstc", "twd_academic", "unknown_reasons"}


# ---- US3 -----------------------------------------------------------------------------------------------------------

def test_tc014_tc015_real_run_is_unknown_and_has_exactly_four_fields(tmp_path):
    # TC-014, TC-015
    from abf_platform import actions
    db, plat = _index(tmp_path, [("run-a", 1, 1_790_000_000)])
    out = actions.estimate_su(db, "run-a", caller=_caller(1), platform_path=plat)
    assert set(out) == KEYS
    assert out["su"] is None and out["twd_nstc"] is None and out["twd_academic"] is None
    assert out["unknown_reasons"] and "cpus" in out["unknown_reasons"][0] and "realtime" in out["unknown_reasons"][0]


def test_tc016_action_uses_the_formula(tmp_path, monkeypatch):
    # TC-016
    from abf_platform import actions
    su = su_mod()
    db, plat = _index(tmp_path, [("run-a", 1, 1_790_000_000)])
    monkeypatch.setattr(su, "run_tasks", lambda index_path, run_name: two_tasks())
    out = actions.estimate_su(db, "run-a", caller=_caller(1), platform_path=plat, site="testsite", rates=rates())
    assert out == su.su_of_tasks(two_tasks(), "testsite", rates())
    assert out["su"] == 14 and abs(out["twd_nstc"] - 1.12) < 1e-9 and abs(out["twd_academic"] - 3.36) < 1e-9
    assert out["unknown_reasons"] == []


def test_tc017_tc018_other_users_run_and_missing_run_answer_alike(tmp_path):
    # TC-017, TC-018
    from abf_platform import actions
    db, plat = _index(tmp_path, [("run-b", 2, 1_790_000_000)])
    other = actions.estimate_su(db, "run-b", caller=_caller(1), platform_path=plat)
    assert other["found"] is False and "找不到這個 run" in other["message"] and "su" not in other and "twd_nstc" not in other
    missing = actions.estimate_su(db, "run-zzz", caller=_caller(1), platform_path=plat)
    assert set(missing) == set(other) and missing["message"].replace("run-zzz", "X") == other["message"].replace("run-b", "X")
    assert other["message"] == actions.get_run(db, "run-b", caller=_caller(1), platform_path=plat)["message"]


def test_tc019_no_caller_sees_everything(tmp_path):
    # TC-019
    from abf_platform import actions
    db, plat = _index(tmp_path, [("run-b", 2, 1_790_000_000)])
    out = actions.estimate_su(db, "run-b", platform_path=plat)
    assert out.get("found") is not False and set(out) == KEYS


# ---- US4 -----------------------------------------------------------------------------------------------------------

OCT = 1_792_000_000      # 2026-10-14 UTC
SEP = 1_789_000_000      # 2026-09-10 UTC


def _month_setup(tmp_path):
    runs = [("a-oct1", 1, OCT), ("a-oct2", 1, OCT + 86400), ("a-sep", 1, SEP), ("b-oct", 2, OCT)]
    db, plat = _index(tmp_path, runs)
    sus = {"a-oct1": 10, "a-oct2": 5, "a-sep": 100, "b-oct": 50}
    return db, plat, sus


def _total(db, plat, sus, uid, month="2026-10"):
    def tasks_of(index_path, run_name):
        return [{"queue": "p1", "cpus": 1, "realtime": H * sus[run_name] / 1.5}]
    return su_mod().month_total(db, plat, uid, month, "testsite", rates(), tasks_of)


def test_tc020_tc021_month_total_is_that_users_runs_of_that_month(tmp_path):
    # TC-020, TC-021
    assert time.strftime("%Y-%m", time.gmtime(OCT)) == "2026-10" and time.strftime("%Y-%m", time.gmtime(SEP)) == "2026-09"
    db, plat, sus = _month_setup(tmp_path)
    assert _total(db, plat, sus, 1) == pytest.approx(15)
    assert _total(db, plat, sus, 2) == pytest.approx(50)


def test_tc022_total_is_computed_on_read(tmp_path):
    # TC-022
    db, plat, sus = _month_setup(tmp_path)
    assert _total(db, plat, sus, 1) == pytest.approx(15)
    from abf_platform import store
    con = store.connect_index(db)
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at) "
                    "VALUES ('id-a3', 's3', 'a-oct3', 'live', 'succeeded', ?, ?, 3)", (OCT + 2 * 86400, OCT + 2 * 86400 + 5))
    con.close()
    own_runs(plat, 1, ["a-oct3"])
    sus["a-oct3"] = 7
    assert _total(db, plat, sus, 1) == pytest.approx(22)


def test_month_total_is_unknown_when_a_run_is_unknown(tmp_path):
    db, plat, _ = _month_setup(tmp_path)
    assert su_mod().month_total(db, plat, 1, "2026-10", "testsite", rates()) is None     # real records keep no tasks


# ---- US5 -----------------------------------------------------------------------------------------------------------

def test_tc023_rates_file_money_and_source():
    # TC-023
    d = json.loads(RATES_FILE.read_text(encoding="utf-8"))
    assert d["nstc_twd_per_su"] == 0.08 and d["academic_twd_per_su"] == 0.24
    assert d["source"] == "https://lions.nchc.org.tw/ngs.jsp"
    assert d["source"] in (REPO_ROOT / "docs" / "POSITIONING.md").read_text(encoding="utf-8")


def test_tc024_every_factor_is_null_unless_the_ledger_cites_it():
    # TC-024
    d = json.loads(RATES_FILE.read_text(encoding="utf-8"))
    for site in d["sites"].values():
        for name, p in site["partitions"].items():
            assert p["factor"] is None or name in LEDGER.read_text(encoding="utf-8"), name


def test_tc025_the_seven_queues_of_nchc_config():
    # TC-025
    d = json.loads(RATES_FILE.read_text(encoding="utf-8"))
    conf = (REPO_ROOT / "configs" / "sites" / "nchc.config").read_text(encoding="utf-8")
    queues = re.findall(r"queue:\s*'([^']+)'", conf)
    assert sorted(d["sites"]["nchc"]["partitions"]) == sorted(["ngs7G", "ngs13G", "ngs26G", "ngs53G", "ngs92G", "ngs186G", "ngs372G"]) == sorted(set(queues))


def test_tc026_tc027_tc028_the_ledger_states_the_debts():
    # TC-026, TC-027, TC-028
    t = LEDGER.read_text(encoding="utf-8")
    assert "係數" in t and "su_rates.json" in t and "欠" in t and "lab-agent" in t
    assert "沒有保存" in t and "cpus" in t and "realtime" in t and "未改 receiver" in t
    assert "MCP 工具" in t and "網頁顯示" in t and "012d" in t and "parity" in t


# ---- US6 -----------------------------------------------------------------------------------------------------------

def test_tc029_no_estimate_su_tool(tmp_path):
    # TC-029
    from abf_platform.mcp_server import build_server
    names = {t.name for t in asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())}
    assert names == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files",
                     "launch", "cancel", "resume", "relaunch"}


def test_tc030_no_su_route_on_the_web(tmp_path):
    # TC-030
    from abf_platform import web
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"su|estimate", getattr(r, "path", ""), re.I)]


def test_tc033_no_cloud_cost_in_the_answer():
    # TC-033
    assert set(calc(two_tasks())) == KEYS


# ---- constitution --------------------------------------------------------------------------------------------------

def _tables(db):
    con = sqlite3.connect(str(db))
    try:
        return {t: [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)] for (t,) in
                con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()


def test_tcc02_nothing_is_stored(tmp_path):
    # TC-C02
    from abf_platform import actions
    db, plat, _ = _month_setup(tmp_path)
    before = (_tables(db), _tables(plat), sorted(p.name for p in tmp_path.rglob("*")))
    for _ in range(3):
        actions.estimate_su(db, "a-oct1", caller=_caller(1), platform_path=plat)
        su_mod().month_total(db, plat, 1, "2026-10", "testsite", rates())
    assert (_tables(db), _tables(plat), sorted(p.name for p in tmp_path.rglob("*"))) == before


def test_tcc03_no_scheduler_or_partition_names_in_the_code():
    # TC-C03
    import inspect
    from abf_platform import actions
    text = SU_PY.read_text(encoding="utf-8") + inspect.getsource(actions.estimate_su)
    assert not re.search(r"ngs\d|taiwania|slurm|sbatch|squeue", text, re.I)


def test_tcc04_su_py_says_why_nothing_existing():
    # TC-C04
    head = SU_PY.read_text(encoding="utf-8").splitlines()[:40]
    assert any(re.match(r"# (Nothing existing|Not [^:]+):", l) for l in head)


def test_tcc05_money_rates_are_not_in_the_code():
    # TC-C05
    assert not re.search(r"0\.08|0\.24", SU_PY.read_text(encoding="utf-8"))
