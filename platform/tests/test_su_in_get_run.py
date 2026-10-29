# Nothing existing: tests of the per-task usage the receiver keeps and the su get_run shows; the table, the site rule and the gates are this task's.
"""estimate-su-mcp: the receiver keeps each finished task's cpus, realtime and partition, and get_run shows the SU.
Test cases TC-001 ... TC-087 are named in the comments, see specs/estimate-su-mcp/ (the verifier's test case list)."""
import asyncio
import json
import re
import sqlite3
import subprocess
import sys
import time

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT, own_runs

H = 3600000
SU_KEYS = {"su", "twd_nstc", "twd_academic", "unknown_reasons", "site", "usd_approx"}


def _ce(plat_db, name, su_site=None):
    from abf_platform import compute_envs
    cfg = {"workDir": "/data/work", "headQueue": "hq"}
    if su_site is not None:
        cfg["suSite"] = su_site
    compute_envs.create(plat_db, {"name": name, "platform": "slurm-platform", "config": cfg})


def _launch(plat_db, run_name, ce, user=1):
    from abf_platform import store
    con = store.connect_state(plat_db)
    with con:
        con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?, '/f', ?, 'a1', 1, ?)",
                    (run_name, ce, user))
    con.close()


def _world(tmp_path, name="run-a", status="succeeded", succeeded=2, usage=(), ce=None, su_site=None, user=1, launch=True):
    """An index with one run, its usage rows, and a platform.db that says who launched it from which CE.
    usage rows: (task_key, name, status, cpus, realtime_ms, queue)."""
    from abf_platform import store
    db, plat = tmp_path / "index.db", tmp_path / "platform.db"
    con = store.connect_index(db)
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at, n_succeeded) "
                    "VALUES (?, 's', ?, 'live', ?, 1790000000, 1790000100, 3, ?)",
                    ("id-" + name, name, None if status in ("running", "lost") else status, succeeded))
        for u in usage:
            con.execute("INSERT INTO task_usage (run_id, task_key, name, status, cpus, realtime_ms, queue) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        ("id-" + name,) + tuple(u))
    con.close()
    store.connect_state(plat).close()
    if ce:
        _ce(plat, ce, su_site)
    if launch:
        _launch(plat, name, ce or "gone-ce", user)
    return db, plat


def _caller(uid=1):
    from abf_platform import actions
    return actions.Caller(uid, "u%d" % uid, "lab")


def _get(db, plat, name="run-a", uid=1):
    from abf_platform import actions
    return actions.get_run(db, "id-" + name, caller=_caller(uid), platform_path=plat)


TWO = [("1:1", "A", "COMPLETED", 2, 1800000, "ngs92G"), ("2:1", "B", "COMPLETED", 1, H, "ngs92G")]

# TC-083: what an unknown reason may never show a user: a file path, SQL, a stack trace, a token
_LEAKS = re.compile(r"(?i)\b(select|insert|where)\b|sqlite|task_usage|operationalerror|traceback|token|bearer|\.db\b"
                    r"|(?:^|\s)[/\\]\S|[A-Za-z]:[/\\]|\\")


def _leaks(text, *paths):
    """The things in one reason that must not be there (the actual paths of this test included); empty when it is clean."""
    found = [m.group(0) for m in _LEAKS.finditer(text)]
    return found + [str(x) for x in paths if str(x) in text]


def _no_leaks(su, *paths):
    for text in su["unknown_reasons"]:
        assert not _leaks(text, *paths), (text, _leaks(text, *paths))


# ---- receiver --------------------------------------------------------------------------------------------------

def _send(plat, token, tasks):
    if not hasattr(plat, "_wid"):
        plat._wid = plat.send("POST", "/trace/create", {"runName": "r1", "sessionId": "s1", "projectName": "p"},
                              token=token).json()["workflowId"]
    r = plat.send("PUT", "/trace/%s/progress" % plat._wid, {"progress": {}, "tasks": tasks}, token=token)
    assert r.status_code == 200, r.text
    return plat._wid


def _rows(plat, wid):
    con = sqlite3.connect(str(plat.index))
    try:
        return con.execute("SELECT task_key, name, status, cpus, realtime_ms, queue FROM task_usage WHERE run_id = ? ORDER BY task_key",
                           (wid,)).fetchall()
    finally:
        con.close()


def _t(i, name, status, attempt=1, **kw):
    d = {"taskId": i, "attempt": attempt, "name": name, "status": status}
    d.update(kw)
    return d


def test_receiver_keeps_cpus_realtime_queue_of_finished_tasks(plat, token):
    # TC-001, TC-002
    tasks = [_t(1, "A", "COMPLETED", cpus=2, realtime=1800000, queue="ngs92G"), _t(2, "B", "FAILED", cpus=1, realtime=5, queue="ngs7G"),
             _t(3, "C", "RUNNING", cpus=1, realtime=1, queue="q"), _t(4, "D", "CACHED", cpus=1, realtime=1, queue="q"),
             _t(5, "E", "SUBMITTED", cpus=1), _t(6, "F", "ABORTED", cpus=1)]
    wid = _send(plat, token, tasks)
    assert _rows(plat, wid) == [("1:1", "A", "COMPLETED", 2, 1800000, "ngs92G"), ("2:1", "B", "FAILED", 1, 5, "ngs7G")]


def test_a_running_report_neither_writes_nor_deletes_and_a_completed_one_overwrites(plat, token):
    # TC-003, TC-004
    wid = _send(plat, token, [_t(1, "A", "COMPLETED", cpus=2, realtime=1800000, queue="q")])
    _send(plat, token, [_t(1, "A", "RUNNING", cpus=9, realtime=9, queue="z")])
    assert _rows(plat, wid) == [("1:1", "A", "COMPLETED", 2, 1800000, "q")]
    _send(plat, token, [_t(1, "A", "COMPLETED", cpus=2, realtime=3600000, queue="q")])
    assert _rows(plat, wid) == [("1:1", "A", "COMPLETED", 2, 3600000, "q")]


def test_a_retry_keeps_both_attempts(plat, token):
    # TC-005
    wid = _send(plat, token, [_t(7, "A", "FAILED", attempt=1, cpus=1, realtime=1, queue="q"),
                              _t(7, "A", "COMPLETED", attempt=2, cpus=1, realtime=2, queue="q")])
    assert [r[0] for r in _rows(plat, wid)] == ["7:1", "7:2"]


def test_non_numbers_and_non_text_queue_are_stored_as_null(plat, token):
    # TC-006, TC-007
    wid = _send(plat, token, [_t(1, "A", "COMPLETED", cpus="abc", realtime=None, queue=None),
                              _t(2, "B", "COMPLETED", cpus=1, realtime=1, queue=5)])
    assert _rows(plat, wid) == [("1:1", "A", "COMPLETED", None, None, None), ("2:1", "B", "COMPLETED", 1, 1, None)]


# ---- get_run ---------------------------------------------------------------------------------------------------

def test_get_run_has_su_for_a_nano4_run(tmp_path):
    # TC-010, TC-012, TC-075
    db, plat = _world(tmp_path, usage=TWO, ce="n4", su_site="nano4")
    su = _get(db, plat)["su"]
    assert set(su) == SU_KEYS | {"twd"}
    assert su["su"] == pytest.approx(2.0) and su["twd_nstc"] == pytest.approx(0.2) and su["twd_academic"] == pytest.approx(0.4)
    assert su["twd"] == {"nstc": pytest.approx(0.2), "academic": pytest.approx(0.4), "industry": pytest.approx(0.74)}
    assert su["unknown_reasons"] == [] and su["site"] == "nano4"


def test_default_site_run_has_no_twd_key(tmp_path):
    # TC-011, TC-012
    db, plat = _world(tmp_path, succeeded=1, usage=[("1:1", "A", "COMPLETED", 4, 2 * H, "ct56")], ce="plain")
    su = _get(db, plat)["su"]
    assert set(su) == SU_KEYS
    assert su["su"] == pytest.approx(8) and su["twd_nstc"] == pytest.approx(0.64) and su["site"] == "taiwania3"


def test_failed_attempt_counts_too(tmp_path):
    # TC-013
    db, plat = _world(tmp_path, succeeded=1, ce="n4", su_site="nano4",
                      usage=[("1:1", "A", "FAILED", 1, 1800000, "ngs92G"), ("1:2", "A", "COMPLETED", 1, H, "ngs92G")])
    su = _get(db, plat)["su"]
    assert su["su"] == pytest.approx(1.5) and su["twd_nstc"] == pytest.approx(0.15) and su["twd_academic"] == pytest.approx(0.3)


def test_mcp_get_run_is_the_same_action(tmp_path):
    # TC-014 (su-followups TC-020, TC-021): the tool is really called, in process, and what it returns carries su
    from abf_platform.mcp_server import build_server
    db, plat = _world(tmp_path, usage=TWO, ce="n4", su_site="nano4")
    assert "get_run" in {t.name for t in asyncio.run(build_server(db, plat).list_tools())}
    out = asyncio.run(build_server(db, plat).call_tool("get_run", {"run_id": "id-run-a"}))
    su = json.loads(out.content[0].text)["su"]
    assert set(su) == SU_KEYS | {"twd"}
    assert su["su"] == pytest.approx(2.0) and su["twd_nstc"] == pytest.approx(0.2) and su["twd_academic"] == pytest.approx(0.4)
    assert su["twd"] == {"nstc": pytest.approx(0.2), "academic": pytest.approx(0.4), "industry": pytest.approx(0.74)}
    assert su["unknown_reasons"] == [] and su["site"] == "nano4"
    direct = _get(db, plat)["su"]
    assert su["su"] == pytest.approx(direct["su"]) and su["twd"] == direct["twd"] and su["site"] == direct["site"]
    assert direct["su"] == pytest.approx(2.0)


def test_estimate_su_uses_the_site_of_the_run(tmp_path):
    # TC-015
    from abf_platform import actions
    db, plat = _world(tmp_path, usage=TWO, ce="n4", su_site="nano4")
    out = actions.estimate_su(db, "run-a", caller=_caller(), platform_path=plat)
    assert out["su"] == pytest.approx(2.0) and out["twd"]["industry"] == pytest.approx(0.74)


def test_get_run_su_is_null_with_reason_for_an_old_run(tmp_path):
    # TC-020, TC-083
    db, plat = _world(tmp_path, usage=(), launch=False)
    own_runs(plat, 1, ["run-a"])      # the owner row names the CE "lab-a", which is not there, so the default site stands
    su = _get(db, plat)["su"]
    assert su["su"] is None and su["twd_nstc"] is None and su["twd_academic"] is None
    assert su["unknown_reasons"][0].startswith("這個 run 的紀錄沒有保存每個 task 的 cpus、realtime 與分區")
    assert su["site"] == "taiwania3" and "twd" not in su
    for text in su["unknown_reasons"]:
        assert "SELECT" not in text and "Traceback" not in text and "token" not in text.lower()
    assert su["unknown_reasons"]
    _no_leaks(su, tmp_path, db, plat)      # su-followups TC-022


def test_old_run_with_nano4_launch_reports_nano4(tmp_path):
    # TC-021
    db, plat = _world(tmp_path, usage=(), ce="n4", su_site="nano4")
    su = _get(db, plat)["su"]
    assert su["su"] is None and su["unknown_reasons"] and su["site"] == "nano4"


def test_old_index_without_the_table_reads_as_unknown(tmp_path):
    # TC-022, TC-082
    db, plat = _world(tmp_path, usage=TWO, ce="n4", su_site="nano4")
    con = sqlite3.connect(str(db))
    con.execute("DROP TABLE task_usage")
    con.commit()
    con.close()
    before = db.read_bytes()
    su = _get(db, plat)["su"]
    assert su["su"] is None and su["unknown_reasons"]
    _no_leaks(su, tmp_path, db, plat)      # su-followups TC-023
    assert db.read_bytes() == before
    con = sqlite3.connect(str(db))
    assert not con.execute("SELECT name FROM sqlite_master WHERE name = 'task_usage'").fetchall()
    con.close()


def test_one_task_missing_cpus_makes_the_whole_run_unknown(tmp_path):
    # TC-023
    db, plat = _world(tmp_path, ce="n4", su_site="nano4",
                      usage=[("1:1", "A", "COMPLETED", None, H, "ngs92G"), ("2:1", "B", "COMPLETED", 1, H, "ngs92G")])
    su = _get(db, plat)["su"]
    assert su["su"] is None and su["twd_nstc"] is None and su["twd_academic"] is None
    assert any("A" in r and "cpus" in r for r in su["unknown_reasons"])


def test_missing_realtime_and_queue_are_named(tmp_path):
    # TC-024
    db, plat = _world(tmp_path, ce="n4", su_site="nano4",
                      usage=[("1:1", "A", "COMPLETED", 1, None, "ngs92G"), ("2:1", "B", "COMPLETED", 1, H, None)])
    su = _get(db, plat)["su"]
    assert su["su"] is None
    text = " ".join(su["unknown_reasons"])
    assert "realtime" in text and "SU 係數" in text


RUN_ENDED = "run 還沒結束，SU 等它結束後再算 (the run has not ended)"


@pytest.mark.parametrize("status", ["running", "lost"])
def test_running_run_has_no_su_number(tmp_path, status):
    # TC-025, TC-026
    db, plat = _world(tmp_path, status=status, ce="n4", su_site="nano4", usage=TWO)
    con = sqlite3.connect(str(db))
    con.execute("UPDATE runs SET last_message_at = ?", (1 if status == "lost" else time.time(),))
    con.commit()
    con.close()
    out = _get(db, plat)
    assert out["status"] == status
    su = out["su"]
    assert su["su"] is None and su["twd_nstc"] is None and su["twd_academic"] is None
    assert su["unknown_reasons"] == [RUN_ENDED]
    _no_leaks(su, tmp_path, db, plat)      # su-followups TC-024


def test_missing_usage_rows_make_su_unknown(tmp_path):
    # TC-027
    db, plat = _world(tmp_path, succeeded=3, ce="n4", su_site="nano4", usage=TWO)
    su = _get(db, plat)["su"]
    assert su["su"] is None
    assert su["unknown_reasons"] == ["有 1 個成功的 task 沒有用量紀錄 (1 succeeded tasks have no usage record)"]
    _no_leaks(su, tmp_path, db, plat)      # su-followups TC-025


def test_unknown_run_has_no_su_key(tmp_path):
    # TC-028
    from abf_platform import actions
    db, plat = _world(tmp_path, usage=TWO, ce="n4", su_site="nano4")
    out = actions.get_run(db, "nope", caller=_caller(), platform_path=plat)
    assert out["found"] is False and out["id"] == "nope" and "su" not in out


def test_another_users_run_has_no_su(tmp_path):
    # TC-029
    db, plat = _world(tmp_path, usage=TWO, ce="n4", su_site="nano4", user=1)
    out = _get(db, plat, uid=2)
    assert out["found"] is False and "su" not in out and "2.0" not in json.dumps(out)


def test_unreadable_rates_file_gives_null_site(tmp_path, monkeypatch):
    # TC-030
    from abf_platform import su
    db, plat = _world(tmp_path, usage=TWO, ce="n4", su_site="nano4")
    monkeypatch.setattr(su, "RATES_PATH", tmp_path / "missing.json")
    s = _get(db, plat)["su"]
    assert s["su"] is None and s["site"] is None and "費率檔讀不到" in " ".join(s["unknown_reasons"])
    _no_leaks(s, tmp_path, tmp_path / "missing.json", "missing.json", db, plat)      # su-followups TC-026


def test_the_leak_check_can_go_red(tmp_path):
    # su-followups TC-027: the check behind TC-022 .. TC-026 flags each kind of leak and lets a clean reason through
    for bad in ("cannot open %s" % (tmp_path / "x.json"), "SELECT * FROM task_usage", "Traceback (most recent call last)",
                "token abc", "see /var/lib/x", "C:\\Users\\x\\y", "sqlite3.OperationalError: no such table"):
        assert _leaks(bad, tmp_path), bad
    assert not _leaks("費率檔讀不到 (the rates file cannot be read)", tmp_path)


# ---- site ------------------------------------------------------------------------------------------------------

def test_site_of_run_reads_suSite_of_the_ce(tmp_path):
    # TC-040, TC-045, TC-046, TC-047
    from abf_platform import su
    rates = su.load_rates()
    db, plat = _world(tmp_path, ce="n4", su_site="nano4")
    assert su.site_of_run(plat, "run-a", rates) == "nano4"
    assert su.site_of_run(plat, "other", rates) == "taiwania3"
    _ce(plat, "plain")
    _launch(plat, "run-b", "plain")
    assert su.site_of_run(plat, "run-b", rates) == "taiwania3"
    _launch(plat, "run-c", "vanished")
    assert su.site_of_run(plat, "run-c", rates) == "taiwania3"


def test_site_of_run_takes_the_newest_launch(tmp_path):
    # TC-042
    from abf_platform import su
    db, plat = _world(tmp_path, ce="n4", su_site="nano4", launch=False)
    _ce(plat, "plain")
    _launch(plat, "run-a", "plain")
    _launch(plat, "run-a", "n4")
    assert su.site_of_run(plat, "run-a", su.load_rates()) == "nano4"


def test_site_of_run_without_a_platform_db_is_the_default(tmp_path):
    # TC-048
    from abf_platform import su
    assert su.site_of_run(tmp_path / "none.db", "x", su.load_rates()) == "taiwania3"
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"not a database at all" * 50)
    assert su.site_of_run(bad, "x", su.load_rates()) == "taiwania3"


@pytest.mark.parametrize("kind", ["missing", "garbage"])
def test_estimate_su_without_a_readable_platform_db_judges_the_default_site(tmp_path, kind):
    # TC-048 (su-followups TC-030, TC-031): through actions.estimate_su; only taiwania3 knows ct56, so the numbers prove the site
    from abf_platform import actions
    db, _plat = _world(tmp_path, succeeded=1, usage=[("1:1", "A", "COMPLETED", 4, 2 * H, "ct56")], launch=False)
    pf = tmp_path / ("none.db" if kind == "missing" else "bad.db")
    if kind == "garbage":
        pf.write_bytes(b"not a database at all" * 50)
    out = actions.estimate_su(db, "run-a", platform_path=pf)
    assert out["su"] == pytest.approx(8) and out["twd_nstc"] == pytest.approx(0.64)
    assert "twd" not in out


def test_suSite_must_name_a_site_in_the_rates_file():
    # TC-049, TC-051
    from abf_platform import compute_envs
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.clean({"name": "x", "platform": "slurm-platform", "config": {"workDir": "/w", "headQueue": "q", "suSite": "nowhere"}})
    m = str(e.value)
    assert "suSite" in m and "費率檔沒有站點 nowhere" in m and "taiwania3" in m and "nano4" in m and "nchc" in m
    assert "no such site in configs/sites/su_rates.json" in m
    with pytest.raises(compute_envs.CEError) as e2:
        compute_envs.clean({"name": "x", "platform": "slurm-platform",
                            "config": {"workDir": "/w", "headQueue": "q", "suSite": "nowhere", "modules": "notalist"}})
    assert "suSite" in str(e2.value) and "modules" in str(e2.value)


def test_suSite_with_unreadable_rates_file(tmp_path, monkeypatch):
    # TC-050
    from abf_platform import compute_envs, su
    monkeypatch.setattr(su, "RATES_PATH", tmp_path / "missing.json")
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.clean({"name": "x", "platform": "slurm-platform", "config": {"workDir": "/w", "headQueue": "q", "suSite": "nano4"}})
    assert "suSite: 費率檔讀不到，無法確認站點 nano4 (the rates file cannot be read)" in str(e.value)


def test_the_nano4_ce_file_validates_and_snapshot_has_no_suSite():
    # TC-041, TC-043
    from abf_platform import compute_envs
    cfg = json.loads((REPO_ROOT / "configs" / "sites" / "nchc-nano4-ce.json").read_text(encoding="utf-8"))
    assert cfg["suSite"] == "nano4"
    cfg = json.loads(json.dumps(cfg).replace("<site_user>", "someone"))      # the placeholder is filled in on the machine that registers it
    rec = compute_envs.clean({"name": "n4", "platform": "slurm-platform", "config": cfg})
    assert rec["config"]["suSite"] == "nano4"
    assert "suSite" not in json.dumps(compute_envs.snapshot({"name": "n4", "platform": "slurm-platform", "config": rec["config"]}), default=str)


def test_su_and_compute_envs_import_in_either_order():
    # TC-044
    body = "c.clean({'name':'x','platform':'slurm-platform','config':{'workDir':'/w','headQueue':'q','suSite':'nano4'}})"
    for first in ("import abf_platform.su, abf_platform.compute_envs as c;", "import abf_platform.compute_envs as c, abf_platform.su;"):
        r = subprocess.run([sys.executable, "-c", first + body], cwd=str(PLATFORM_DIR), capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


# ---- not in scope ----------------------------------------------------------------------------------------------

def test_tool_list_unchanged(tmp_path):
    # TC-070
    from abf_platform.mcp_server import build_server
    db, plat = _world(tmp_path, usage=TWO, ce="n4", su_site="nano4")
    names = {t.name for t in asyncio.run(build_server(db, plat).list_tools())}
    assert len(names) == 20 and "estimate_su" not in names


def test_list_runs_has_no_su(tmp_path):
    # TC-072
    from abf_platform import actions
    db, plat = _world(tmp_path, usage=TWO, ce="n4", su_site="nano4")
    rows = actions.list_runs(db, caller=_caller(), platform_path=plat)
    rows = rows["runs"] if isinstance(rows, dict) else rows
    assert rows and all("su" not in r for r in rows)


def _rebuilt_run(tmp_path):
    """A launch folder (history, log, trace) with two COMPLETED tasks, rebuilt through rebuild.rebuild; returns (index, platform, run id)."""
    from abf_platform import common, rebuild, store
    folder = tmp_path / "launch"
    (folder / ".nextflow").mkdir(parents=True)
    session = "11111111-2222-3333-4444-555555555555"
    (folder / ".nextflow" / "history").write_text(
        "2026-09-21 10:00:00\t1m\trun-a\tOK\tabcdef\t%s\n" % session, encoding="utf-8")
    (folder / ".nextflow.log").write_text(
        "Sep-21 10:00:00.000 [main] DEBUG nextflow.Session - Session UUID: %s\n"
        "Sep-21 10:00:00.001 [main] DEBUG nextflow.Session - Run name: run-a\n"
        "Sep-21 10:00:00.002 [main] DEBUG nextflow.Session - Workflow started -- trace file: trace.txt\n"
        "Sep-21 10:01:00.000 [main] DEBUG nextflow.Session - Session await > all barriers passed\n" % session, encoding="utf-8")
    (folder / "trace.txt").write_text("task_id\tname\tstatus\texit\n1\tA\tCOMPLETED\t0\n2\tB\tCOMPLETED\t0\n", encoding="utf-8")
    db, plat = tmp_path / "index.db", tmp_path / "platform.db"
    result = rebuild.rebuild([str(folder)], db, out=lambda *_: None)
    assert result.folders == 1
    store.connect_state(plat).close()
    _launch(plat, "run-a", "gone-ce")
    return db, plat, common.run_id(session, "run-a")


def test_a_run_without_usage_rows_stays_unknown(tmp_path):
    # TC-073 (su-followups TC-028, TC-029): a run rebuilt from the launch folder has no usage rows, so it is unknown, with the NOT_STORED sentence
    from abf_platform import actions
    db, plat, rid = _rebuilt_run(tmp_path)
    con = sqlite3.connect(str(db))
    try:
        assert con.execute("SELECT source FROM runs WHERE id = ?", (rid,)).fetchone()[0] == "rebuild"
        assert con.execute("SELECT n_succeeded FROM runs WHERE id = ?", (rid,)).fetchone()[0] > 0
        assert con.execute("SELECT COUNT(*) FROM task_usage WHERE run_id = ?", (rid,)).fetchone()[0] == 0
    finally:
        con.close()
    su = actions.get_run(db, rid, caller=_caller(), platform_path=plat)["su"]
    assert su["su"] is None and su["twd_nstc"] is None and su["twd_academic"] is None
    assert su["unknown_reasons"] == ["這個 run 的紀錄沒有保存每個 task 的 cpus、realtime 與分區 "
                                     "(the run record does not keep each task's cpus, realtime and partition)"]
    assert "沒有用量紀錄" not in " ".join(su["unknown_reasons"]) and "have no usage record" not in " ".join(su["unknown_reasons"])


def test_su_follows_the_stored_realtime(tmp_path):
    # TC-080
    db, plat = _world(tmp_path, succeeded=1, ce="n4", su_site="nano4", usage=[("1:1", "A", "COMPLETED", 2, 2 * H, "ngs92G")])
    assert _get(db, plat)["su"]["su"] == pytest.approx(4.0)
    con = sqlite3.connect(str(db))
    con.execute("UPDATE task_usage SET realtime_ms = ?", (5 * H,))
    con.commit()
    con.close()
    assert _get(db, plat)["su"]["su"] == pytest.approx(10.0)


def test_an_older_index_gets_the_table_when_opened_and_keeps_its_rows(tmp_path):
    # TC-084
    from abf_platform import store
    p = tmp_path / "old.db"
    con = sqlite3.connect(str(p))
    con.executescript(store.SCHEMA)
    con.execute("DROP TABLE task_usage")
    con.execute("INSERT INTO runs (id, session_id, run_name, last_message_at, n_succeeded) VALUES ('i', 's', 'r', 1, 4)")
    con.execute("INSERT INTO failed_tasks (run_id, task_key, name) VALUES ('i', '1:1', 'A')")
    con.commit()
    con.close()
    for _ in range(2):
        con = store.connect_index(p)
        assert con.execute("SELECT name FROM sqlite_master WHERE name = 'task_usage'").fetchone()
        assert con.execute("SELECT n_succeeded FROM runs").fetchone()[0] == 4
        assert con.execute("SELECT COUNT(*) FROM failed_tasks").fetchone()[0] == 1
        con.close()
