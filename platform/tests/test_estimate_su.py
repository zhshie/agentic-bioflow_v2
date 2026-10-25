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
    # E4: T3 general (NRQ) rate; was academic 0.24 + lions.nchc.org.tw/ngs.jsp source (GP1 list, not used now)
    assert d["nstc_twd_per_su"] == 0.08 and d["academic_twd_per_su"] == 0.08 and d["industry_twd_per_su"] == 0.16
    assert d["source"] == "https://iservice.nchc.org.tw/nchc_service/nchc_service_qa.php?target=54"
    assert "lions.nchc.org.tw/ngs.jsp" in d["not_used"] and "1 SU = 1 core-hour" in d["assumption"]


def test_e4_ct56_task_4cpus_2h_is_8_su_and_064_twd():
    # E4
    out = su_mod().su_of_tasks([{"queue": "ct56", "cpus": 4, "realtime": 2 * H}], "taiwania3", su_mod().load_rates())
    assert out["su"] == 8 and abs(out["twd_nstc"] - 0.64) < 1e-9 and out["unknown_reasons"] == []


def test_e4_ct2k_amd_price_unknown():
    # E4
    _unknown(su_mod().su_of_tasks([{"queue": "ct2k-amd", "cpus": 1, "realtime": H}], "taiwania3", su_mod().load_rates()), "ct2k-amd")


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
    assert names == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "list_used_pipelines", "read_task_log",
                     "run_outputs", "launch", "cancel", "resume", "relaunch", "forget"}


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


# ---- US4 Taipei month (plan E2) --------------------------------------------------------------------------------------

import calendar


def _utc(y, mo, d, h, mi, s):
    return calendar.timegm((y, mo, d, h, mi, s))


def _one_run_total(tmp_path, start, month, ended=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    db, plat = _index(tmp_path, [("a-run", 1, start)])
    if ended is not None:
        from abf_platform import store
        con = store.connect_index(db)
        with con:
            con.execute("UPDATE runs SET ended_at = ?", (ended,))
        con.close()
    return _total(db, plat, {"a-run": 8}, 1, month)


def test_tc034_utc_sept_30_16h_is_taipei_october(tmp_path):
    # TC-034
    assert _one_run_total(tmp_path, _utc(2026, 9, 30, 16, 0, 0), "2026-10") == pytest.approx(8)


def test_tc035_utc_sept_30_1559_is_taipei_september(tmp_path):
    # TC-035
    t = _utc(2026, 9, 30, 15, 59, 59)
    assert _one_run_total(tmp_path / "x", t, "2026-10") == 0
    assert _one_run_total(tmp_path / "y", t, "2026-09") == pytest.approx(8)


def test_tc036_utc_oct_31_16h_is_taipei_november(tmp_path):
    # TC-036
    t = _utc(2026, 10, 31, 16, 0, 0)
    assert _one_run_total(tmp_path / "x", t, "2026-10") == 0
    assert _one_run_total(tmp_path / "y", t, "2026-11") == pytest.approx(8)


def test_tc037_month_follows_start_not_end(tmp_path):
    # TC-037: starts Taipei 2026-09-30 22:00 (= UTC 14:00), ends in October
    start = _utc(2026, 9, 30, 14, 0, 0)
    end = _utc(2026, 10, 1, 1, 0, 0)
    assert _one_run_total(tmp_path / "x", start, "2026-09", end) == pytest.approx(8)
    assert _one_run_total(tmp_path / "y", start, "2026-10", end) == 0


def test_tc038_unknown_run_makes_month_unknown(tmp_path):
    # TC-038
    db, plat = _index(tmp_path, [("a-1", 1, OCT), ("a-2", 1, OCT + 86400)])

    def tasks_of(index_path, run_name):
        if run_name == "a-1":
            return [{"queue": "p1", "cpus": 1, "realtime": H * 10 / 1.5}]
        return [{"queue": "p1", "cpus": None, "realtime": 1}]
    assert su_mod().month_total(db, plat, 1, "2026-10", "testsite", rates(), tasks_of) is None


def test_tc039_month_without_runs_is_zero_not_none(tmp_path):
    # TC-039
    db, plat = _index(tmp_path, [("a-sep", 1, SEP)])
    out = _total(db, plat, {"a-sep": 5}, 1, "2026-10")
    assert out == 0 and out is not None


def test_tc040_other_users_unknown_run_does_not_matter(tmp_path):
    # TC-040
    db, plat = _index(tmp_path, [("a-oct", 1, OCT), ("b-oct", 2, OCT)])

    def tasks_of(index_path, run_name):
        if run_name == "b-oct":
            return None
        return [{"queue": "p1", "cpus": 1, "realtime": H * 10 / 1.5}]
    assert su_mod().month_total(db, plat, 1, "2026-10", "testsite", rates(), tasks_of) == pytest.approx(10)


# ---- nano4-site-config (N4-xx, specs/nano4-site-config/test-case.md) ---------------------------------------------------

N4_CE = REPO_ROOT / "configs" / "sites" / "nchc-nano4-ce.json"
N4_CONF = REPO_ROOT / "configs" / "sites" / "nchc-nano4.config"
N4_LEDGER = REPO_ROOT / "specs" / "nano4-site-config" / "ledger.md"


def _real():
    return json.loads(RATES_FILE.read_text(encoding="utf-8"))


def _t(queue, cpus=1, hours=10):
    return {"name": "t", "queue": queue, "cpus": cpus, "realtime": int(hours * H)}


def _close(out, nstc, academic, industry):
    for k, v in (("nstc", nstc), ("academic", academic), ("industry", industry)):
        assert abs(out["twd"][k] - v) < 1e-9, (k, out["twd"])


def test_tc025b_nano4_rates_price_a_ngs_task_at_0_1_twd_per_core_hour():
    # N4-01, N4-02
    for q in ("ngs", "ngs7G"):
        out = su_mod().su_of_tasks([_t(q)], "nano4", _real())
        assert out["su"] == 10 and out["unknown_reasons"] == []
        _close(out, 1.0, 2.0, 3.7)


def test_tc025c_bigmem_factor_7():
    # N4-03, N4-04
    out = su_mod().su_of_tasks([_t("big-mem")], "nano4", _real())
    assert out["su"] == 70
    _close(out, 7.0, 14.0, 25.9)
    out = su_mod().su_of_tasks([_t("ngs"), _t("big-mem")], "nano4", _real())
    assert out["su"] == 80
    _close(out, 8.0, 16.0, 29.6)


def test_n4_05_return_shape():
    # N4-05
    out = su_mod().su_of_tasks([_t("ngs")], "nano4", _real())
    assert set(out) == KEYS | {"twd"} and set(out["twd"]) == {"nstc", "academic", "industry"}
    assert out["twd_nstc"] == out["twd"]["nstc"] and out["twd_academic"] == out["twd"]["academic"]


def test_n4_06_run_su_and_action_agree(tmp_path):
    # N4-06
    from abf_platform import actions
    db, plat = _index(tmp_path, [("run-a", 1, 1_790_000_000)])
    tasks_of = lambda i, r: [_t("big-mem")]
    a = su_mod().run_su(db, "run-a", "nano4", _real(), tasks_of)
    b = actions.estimate_su(db, "run-a", caller=_caller(1), platform_path=plat, site="nano4", rates=_real(), tasks_of=tasks_of)
    assert a == b and a["su"] == 70
    _close(a, 7.0, 14.0, 25.9)


def test_n4_07_nano4_rates_in_the_file():
    # N4-07
    s = _real()["sites"]["nano4"]
    assert s["twd_per_su"] == {"nstc": 0.1, "academic": 0.2, "industry": 0.37}
    assert s["partitions"]["ngs*"]["factor"] == 1 and s["partitions"]["big-mem*"]["factor"] == 7
    assert "twd_per_core_hour" not in s


def test_n4_08_unknown_partition():
    # N4-08
    out = su_mod().su_of_tasks([_t("gpu")], "nano4", _real())
    assert out["su"] is None and "twd" not in out
    assert any("gpu" in r for r in out["unknown_reasons"])
    assert not any("/" in r or "Traceback" in r for r in out["unknown_reasons"])


def _wild(parts):
    return {"nstc_twd_per_su": 0.08, "academic_twd_per_su": 0.24,
            "sites": {"testsite": {"partitions": {k: {"factor": v} for k, v in parts.items()}}}}


def test_n4_09_exact_beats_wildcard():
    # N4-09
    assert calc([_t("ngs7G", hours=1)], _wild({"ngs*": 1, "ngs7G": 3}))["su"] == 3


def test_n4_10_longest_wildcard_wins():
    # N4-10
    assert calc([_t("ngs7G", hours=1)], _wild({"ngs*": 1, "ngs7*": 2}))["su"] == 2


def test_n4_11_t3_has_no_wildcard():
    # N4-11
    out = su_mod().su_of_tasks([_t("ct56x", hours=1)], "taiwania3", _real())
    assert out["su"] is None and any("ct56x" in r for r in out["unknown_reasons"])


def test_n4_12_no_twd_key_without_twd_per_su():
    # N4-12
    out = su_mod().su_of_tasks([_t("ct56", cpus=4, hours=2)], "taiwania3", _real())
    assert set(out) == KEYS and out["su"] == 8 and abs(out["twd_nstc"] - 0.64) < 1e-9
    assert set(calc([_t("p1", hours=1)], rates())) == KEYS


def test_n4_13_default_site_unchanged(tmp_path):
    # N4-13
    from abf_platform import actions
    db, plat = _index(tmp_path, [("run-a", 1, 1_790_000_000)])
    out = actions.estimate_su(db, "run-a", caller=_caller(1), platform_path=plat, rates=_real(),
                              tasks_of=lambda i, r: [_t("ct56", hours=1)])
    assert out["su"] == 1 and "twd" not in out and _real()["default_site"] == "taiwania3"


def _ce():
    return json.loads(N4_CE.read_text(encoding="utf-8"))


def _clean(cfg):
    from abf_platform import compute_envs
    return compute_envs.clean({"name": "nano4", "platform": "slurm-platform", "config": cfg})


def _filled(cfg):
    """The template with its placeholders replaced the way an operator does at `ce create` (10-23 ruling 9)."""
    t = json.dumps(cfg).replace("<site_user>", "abf-test").replace("<nano4 read-only image library>", "/tmp/abf-test/library")
    return json.loads(t)


def test_n4_16_ce_passes_validation():
    # N4-16
    assert isinstance(_ce(), dict)
    _clean(_filled(_ce()))


def test_n4_17_to_20_ce_fields():
    # N4-17, N4-18, N4-19, N4-20
    c = _ce()
    assert c["headQueue"] == "ngsconsole" and c["headJobOptions"] == "-A mst109178 -c 1 --mem=8G -t 2-00:00:00"
    assert c["workDir"] == "/work/<site_user>/runs" and c["readRoots"] == ["/work/<site_user>"]
    assert c["modules"] == ["biology/Nextflow/26.10.0"]
    assert c["siteConfigVars"] == ["NFCORE_SITE_CONFIG"]
    assert c["sitePipelines"] == [{"pipeline": "nf-core/ampliseq", "revision": "2.18.0",
                                   "module": "biology/nf-core-ampliseq/2.18.0", "home": "NFCORE_AMPLISEQ_HOME"}]
    lib = "/work/<site_user>/abf/singularity-lib"
    assert c["environment"] == [
        {"name": "NXF_SINGULARITY_LIBRARYDIR", "value": lib, "head": True, "compute": True},
        {"name": "NXF_SINGULARITY_CACHEDIR", "value": "/work/<site_user>/.singularity", "head": True, "compute": True},
        {"name": "NXF_OPTS", "value": "-Xms512m -Xmx4g", "head": True, "compute": True},
        {"name": "NXF_PLUGINS_DIR", "value": "/work/<site_user>/abf/nxf-plugins", "head": True, "compute": True}]
    from abf_platform import compute_envs
    assert "_comment" not in c and set(c) <= set(compute_envs._SLURM_CONFIG)


def test_n4_21_self_installed_nextflow_variant():
    # N4-21
    c = _filled(_ce())
    c["modules"] = []
    for e in c["environment"]:
        if e["name"] == "NXF_PLUGINS_DIR":
            e["value"] = "/tmp/abf-test/.nextflow/plugins"
    c["environment"] += [
        {"name": "PATH", "value": "/tmp/abf-test/nextflow/bin:$PATH", "head": True, "compute": True}]
    assert [e["name"] for e in c["environment"]].count("NXF_PLUGINS_DIR") == 1
    _clean(c)


def test_n4ce_template_drops_site_references_and_sets_plugins_dir():
    # N4F-01, N4F-02, N4F-03, N4F-04, N4F-08, N4F-12
    raw = N4_CE.read_text(encoding="utf-8")
    c = json.loads(raw)
    assert c["siteConfigVars"] == ["NFCORE_SITE_CONFIG"]
    assert "NFCORE_SITE_REFERENCES" not in raw
    env = c["environment"]
    plug = [e for e in env if e["name"] == "NXF_PLUGINS_DIR"]
    assert len(plug) == 1
    assert plug[0]["value"] == "/work/<site_user>/abf/nxf-plugins" and plug[0]["head"] is True and plug[0]["compute"] is True
    lib = [e for e in env if e["name"] == "NXF_SINGULARITY_LIBRARYDIR"]
    assert len(lib) == 1 and lib[0]["value"] == "/work/<site_user>/abf/singularity-lib"
    assert lib[0]["head"] is True and lib[0]["compute"] is True
    for bad in ("u9613010", "/work/envstack", "<nano4 read-only image library>"):
        assert bad not in raw, bad


def test_n4ce_docs_carry_the_four_fixes():
    # N4F-13, N4F-16, N4F-18, N4F-20, N4F-25
    s = (REPO_ROOT / "docs" / "SETTINGS.md").read_text(encoding="utf-8")
    for needle in ("nf-tower@1.28.2", "ref_taxonomy_storage", "/work/<site_user>/abf/singularity-lib"):
        assert needle in s, needle
    assert re.search(r"file .*HTML|HTML.*file ", s)
    a = (REPO_ROOT / "docs" / "SITE_ADAPTER.md").read_text(encoding="utf-8")
    assert "singularity-lib" in a


def test_n4_22_n4_31_ledger_notes():
    # N4-22, N4-31
    t = N4_LEDGER.read_text(encoding="utf-8")
    for s in ("modules", "PATH=/work/<site_user>/nextflow/bin:$PATH", "NXF_PLUGINS_DIR=/work/<site_user>/.nextflow/plugins",
              "docs/SETTINGS.md", "不需要 migration"):
        assert s in t, s


def test_n4_23_to_28_fallback_config():
    # N4-23 ... N4-28
    t = N4_CONF.read_text(encoding="utf-8")
    assert re.search(r"executor\s*=\s*'slurm'", t)
    m = re.search(r"resourceLimits\s*=\s*\[([^\]]*)\]", t)
    assert m and all(k in m.group(1) for k in ("cpus", "memory", "time"))
    assert re.search(r"singularity\s*\{[^}]*enabled\s*=\s*true[^}]*autoMounts\s*=\s*true", t, re.S)
    assert re.search(r"queue\s*=\s*System\.getenv\('SLURM_PARTITION'\)\s*\?:\s*'ngs", t)
    assert 'clusterOptions = "-A ${SLURM_ACCOUNT}"' in t
    assert not re.search(r"NCHC_BOXES|nchcBox|maxHours", t)


def test_n4_29_ledger_cites_nano4_factors():
    # N4-29
    t = LEDGER.read_text(encoding="utf-8")
    for s in ("ngs*", "big-mem*", "https://iservice.nchc.org.tw/nchc_service/nchc_service_qa.php?target=54",
              "lions.nchc.org.tw/ngs.jsp", "0.56", "0.08"):
        assert s in t, s


def test_n4_32_t3_untouched():
    # N4-32
    d = _real()
    assert d["default_site"] == "taiwania3"
    assert (d["nstc_twd_per_su"], d["academic_twd_per_su"], d["industry_twd_per_su"]) == (0.08, 0.08, 0.16)
    p = d["sites"]["taiwania3"]["partitions"]
    assert all(p[k]["factor"] == 1 for k in ("ctest", "ct56", "ct224", "ct560", "ct2k", "ct8k")) and p["ct2k-amd"]["factor"] is None
    n = d["sites"]["nchc"]["partitions"]
    assert len(n) == 7 and all(v["factor"] is None for v in n.values())


def test_n4_35_estimate_su_signature_unchanged():
    # N4-35
    import inspect
    from abf_platform import actions
    assert list(inspect.signature(actions.estimate_su).parameters) == [
        "index_path", "run_name", "caller", "platform_path", "site", "rates", "tasks_of"]


def test_n4_c1_c4_no_rates_in_code_and_no_credentials():
    # N4-C1, N4-C4
    from abf_platform import compute_envs
    assert not re.search(r"0\.08|0\.24|0\.1\b|0\.2\b|0\.37|ngs\d|big-mem|taiwania|slurm|sbatch|squeue",
                         SU_PY.read_text(encoding="utf-8"), re.I)
    assert compute_envs.credential_findings(_ce(), "") == []


def test_n4_c5_owner_rule_with_nano4(tmp_path):
    # N4-C5
    from abf_platform import actions
    db, plat = _index(tmp_path, [("run-a", 1, 1_790_000_000)])
    kw = dict(platform_path=plat, site="nano4", rates=_real(), tasks_of=lambda i, r: [_t("ngs")])
    mine = actions.estimate_su(db, "run-a", caller=_caller(1), **kw)
    assert mine["su"] == 10 and "twd" in mine
    other = actions.estimate_su(db, "run-a", caller=_caller(2), **kw)
    gone = actions.estimate_su(db, "run-zzz", caller=_caller(2), **kw)
    assert other["found"] is False and "su" not in other and "twd" not in other
    assert other["message"].replace("run-a", "X") == gone["message"].replace("run-zzz", "X")
