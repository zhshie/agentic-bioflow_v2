# Nothing existing: tests of the clean_work kind and the work_cleaned_at column in platform.db; no earlier test builds an older database and upgrades it.
"""cloud-cleanup-a: the state database learns `clean_work` (confirmation kind and job kind) and `launches.work_cleaned_at`.
Test cases are named in the comments (TC-001 ...), they come from the cloud-cleanup-a spec folder."""
import re
import sqlite3
import threading
from pathlib import Path

import pytest

from helpers import all_files_digest

PKG = Path(__file__).resolve().parents[1] / "abf_platform"

_CONF_COLS = ("id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel')), "
              "created_at REAL NOT NULL, used_at REAL, caller_user_id INTEGER")
_CONF_FULL = "CREATE TABLE confirmations (%s, state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending', 'confirmed', 'void')), " \
             "channel TEXT, confirmed_at REAL, expires_at REAL, ce_name TEXT, bundle_json TEXT, screen_text TEXT, void_reason TEXT, " \
             "forgotten_at REAL, forgotten_by TEXT)" % _CONF_COLS
_CONF_009D = "CREATE TABLE confirmations (%s)" % _CONF_COLS
_JOBS_007 = ("CREATE TABLE jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL, compute_env TEXT NOT NULL, "
             "kind TEXT NOT NULL CHECK (kind IN ('preflight', 'list_site_files')), args_json TEXT NOT NULL, "
             "state TEXT NOT NULL CHECK (state IN ('queued', 'claimed', 'done', 'refused', 'error', 'expired')), result_json TEXT, "
             "late_result_json TEXT, created_at REAL NOT NULL, deadline_at REAL NOT NULL, claimed_at REAL, finished_at REAL)")
_LAUNCH_007 = ("CREATE TABLE launches (id INTEGER PRIMARY KEY AUTOINCREMENT, run_name TEXT NOT NULL UNIQUE, slurm_job_id INTEGER, "
               "run_folder TEXT NOT NULL, ce TEXT NOT NULL, agent TEXT NOT NULL, confirmed_at REAL NOT NULL, submitted_at REAL, "
               "cancel_requested_at REAL)")
_LAUNCH_BASE = ("id INTEGER PRIMARY KEY AUTOINCREMENT, run_name TEXT NOT NULL, slurm_job_id INTEGER, run_folder TEXT NOT NULL, "
                "ce TEXT NOT NULL, agent TEXT NOT NULL, confirmed_at REAL NOT NULL, submitted_at REAL, cancel_requested_at REAL, "
                "job_id INTEGER, user_id INTEGER")
_LAUNCH_ATTEMPT = ", parent_run TEXT, attempt INTEGER, attempt_kind TEXT CHECK (attempt_kind IN ('resume', 'relaunch'))"
OLD_LAUNCHES = "CREATE TABLE launches (%s%s)" % (_LAUNCH_BASE, _LAUNCH_ATTEMPT)
NO_ATTEMPT_LAUNCHES = "CREATE TABLE launches (%s)" % _LAUNCH_BASE

CONF_ROWS = [  # id, sha256, kind, created_at, used_at, caller, state, channel, confirmed_at, expires_at, ce, bundle, screen, void, fat, fby
    ("p1", "s1", "launch", 10.0, None, 7, "pending", "MCP", None, 99.0, "lab-a", '{"a": 1}', "screen one", None, None, None),
    ("c1", "s2", "launch", 11.0, 12.0, 7, "confirmed", "TERMINAL", 11.5, None, "lab-a", None, None, None, 13.0, "7"),
    ("v1", "s3", "cancel", 14.0, None, 8, "void", "MCP", None, 50.0, "lab-b", '{"b": 2}', "screen void", "changed my mind", None, None),
]


def old_jobs(read_task_log=True):
    from abf_platform import store
    ddl = (store._JOBS_TABLE % {"name": "jobs"}).replace(", 'pipeline_files'", "").replace(", 'clean_work'", "")      # release-lookup-job: the older table has no pipeline_files either
    return ddl if read_task_log else ddl.replace(", 'read_task_log'", "")


def make_old(path, confirmations=_CONF_FULL, jobs=None, launches=OLD_LAUNCHES, conf_rows=True, job_rows=True, launch_rows=True):
    """A platform.db as an earlier version left it: only the three tables that change, rows in them, foreign keys off."""
    jobs = jobs or old_jobs()
    con = sqlite3.connect(str(path))
    if confirmations:
        con.execute(confirmations)
    con.execute(jobs)
    con.execute(launches)
    full = confirmations == _CONF_FULL
    if conf_rows and confirmations:
        for r in CONF_ROWS:
            if full:
                con.execute("INSERT INTO confirmations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", r)
            else:
                con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, used_at, caller_user_id) VALUES (?,?,?,?,?,?)", r[:6])
    if job_rows:
        has_conf = "confirmation_id" in jobs
        for kind, cid in (("preflight", None), ("launch_nextflow", "c1"), ("cancel_run", "v1"), ("list_site_files", None)):
            if has_conf:
                con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
                            "VALUES ('a1', 'lab-a', ?, '{}', 'done', 1, 2, ?)", (kind, cid))
            elif kind in ("preflight", "list_site_files"):
                con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                            "VALUES ('a1', 'lab-a', ?, '{}', 'done', 1, 2)", (kind,))
    if launch_rows:
        if launches == _LAUNCH_007:
            con.execute("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at) "
                        "VALUES ('r1', 5, '/f/r1', 'lab-a', 'a1', 3.0, 4.0)")
        else:
            con.execute("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, "
                        "cancel_requested_at, job_id, user_id) VALUES ('r1', 5, '/f/r1', 'lab-a', 'a1', 3.0, 4.0, 6.0, 2, 7)")
            con.execute("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at) "
                        "VALUES ('r2', NULL, '/f/r2', 'lab-b', 'a2', 8.0)")
    con.commit()
    con.close()
    return path


def open_new(path):
    from abf_platform import store
    return store.connect_state(path)


def rows_of(path, table):
    con = sqlite3.connect(str(path))
    try:
        return con.execute("SELECT * FROM %s ORDER BY rowid" % table).fetchall()
    finally:
        con.close()


def cols_of(con, table):
    return [r[1] for r in con.execute("PRAGMA table_info(%s)" % table)]


def check_of(con, table):
    return con.execute("SELECT sql FROM sqlite_master WHERE name = ?", (table,)).fetchone()[0]


def declared_kinds(sql_text):
    m = re.search(r"kind TEXT NOT NULL CHECK \(kind IN \(([^)]*)\)\)", sql_text)
    return re.findall(r"'([a-z_]+)'", m.group(1))


def rootpage(path, name):
    con = sqlite3.connect(str(path))
    try:
        return con.execute("SELECT rootpage FROM sqlite_master WHERE name = ?", (name,)).fetchone()[0]
    finally:
        con.close()


def accepts(con, sql, params=()):
    """True when the insert is let in; always undone."""
    try:
        con.execute("INSERT OR IGNORE INTO confirmations (id, sha256, kind, created_at) VALUES ('probe-c', 'x', 'launch', 1)")
        con.execute(sql, params)
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.rollback()


JOB_SQL = ("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
           "VALUES ('a1', 'x', ?, '{}', ?, 1, 2, ?)")
CONF_SQL = "INSERT INTO confirmations (id, sha256, kind, created_at, state) VALUES ('pr', 'x', ?, 1, ?)"
LAUNCH_SQL = "INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, attempt_kind) VALUES ('r', '/f', 'c', 'a', 1, ?)"

KINDS = ["preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records", "read_task_log", "clean_work", "put_upload",
         "rm", "delete", "clean", "clean_work ", "CLEAN_WORK", ""]


def structure(con):
    """Columns (name, order, type, notnull, default, pk) and what every CHECK lets in, for the three tables that change."""
    out = {t: [tuple(r)[1:] for r in con.execute("PRAGMA table_info(%s)" % t)] for t in ("confirmations", "jobs", "launches")}
    out["conf"] = [(k, s, accepts(con, CONF_SQL, (k, s))) for k in KINDS + ["resume", "relaunch", "retry"] for s in ("pending", "confirmed", "void", "x")]
    out["jobs_probe"] = [(k, s, c, accepts(con, JOB_SQL, (k, s, c))) for k in KINDS for s in ("queued", "expired", "x")
                         for c in (None, "probe-c")]
    out["launch_probe"] = [(a, accepts(con, LAUNCH_SQL, (a,))) for a in ("resume", "relaunch", None, "x", "")]
    return out


# ---- US1: a new database ----------------------------------------------------------------------------------------------
def test_fresh_confirmations_take_clean_work_and_still_refuse_resume_relaunch_retry_and_empty(tmp_path):
    # TC-001, TC-002
    con = open_new(tmp_path / "platform.db")
    for i, kind in enumerate(("launch", "cancel", "clean_work")):
        con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES (?, 'x', ?, 1)", ("k%d" % i, kind))
    assert declared_kinds(check_of(con, "confirmations")) == ["launch", "cancel", "clean_work"]
    before = con.execute("SELECT COUNT(*) FROM confirmations").fetchone()[0]
    for kind in ("resume", "relaunch", "retry", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('bad', 'x', ?, 1)", (kind,))
    assert con.execute("SELECT COUNT(*) FROM confirmations").fetchone()[0] == before
    con.close()


def test_fresh_jobs_take_clean_work_only_with_a_confirmation(tmp_path):
    # TC-003, TC-004, TC-005, TC-006
    con = open_new(tmp_path / "platform.db")
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('c3', 'x', 'clean_work', 1)")
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('c1', 'x', 'launch', 1)")
    con.execute(JOB_SQL, ("clean_work", "queued", "c3"))
    assert declared_kinds(check_of(con, "jobs")) == ["preflight", "list_site_files", "launch_nextflow", "cancel_run",
                                                      "fetch_run_records", "read_task_log", "clean_work", "put_upload", "pipeline_files"]
    n = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    for kind in ("clean_work", "launch_nextflow", "cancel_run"):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(JOB_SQL, (kind, "queued", None))
    assert con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == n
    for kind in ("preflight", "list_site_files", "fetch_run_records", "read_task_log"):
        con.execute(JOB_SQL, (kind, "queued", None))
    assert con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == n + 4
    con.close()


def test_fresh_jobs_still_refuse_rm_delete_clean_and_other_words(tmp_path):
    # TC-007
    con = open_new(tmp_path / "platform.db")
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('c3', 'x', 'clean_work', 1)")
    for kind in ("rm", "delete", "clean", "clean_work ", "CLEAN_WORK", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(JOB_SQL, (kind, "queued", "c3"))
    assert con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    con.close()


def test_launches_has_work_cleaned_at_as_its_last_column_and_it_is_null_by_default(tmp_path):
    # TC-008
    con = open_new(tmp_path / "platform.db")
    assert cols_of(con, "launches") == ["id", "run_name", "slurm_job_id", "run_folder", "ce", "agent", "confirmed_at", "submitted_at",
                                        "cancel_requested_at", "job_id", "user_id", "parent_run", "attempt", "attempt_kind",
                                        "work_cleaned_at"]
    last = [tuple(r) for r in con.execute("PRAGMA table_info(launches)")][-1]
    assert last[2] == "REAL" and last[3] == 0 and last[4] is None
    con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at) VALUES ('r', '/f', 'c', 'a', 1)")
    assert con.execute("SELECT work_cleaned_at FROM launches").fetchone()[0] is None
    con.close()


# ---- US2: an old database ---------------------------------------------------------------------------------------------
def test_old_confirmations_table_is_rebuilt_and_every_row_is_identical(tmp_path):
    # TC-009
    db = make_old(tmp_path / "platform.db")
    before = rows_of(db, "confirmations")
    assert len(before) == 3
    fresh = open_new(tmp_path / "fresh.db")
    fresh_cols = cols_of(fresh, "confirmations")
    fresh.close()
    con = open_new(db)
    assert cols_of(con, "confirmations") == fresh_cols
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('c3', 'x', 'clean_work', 1)")
    con.commit()
    con.close()
    assert rows_of(db, "confirmations")[:3] == before


def test_a_database_before_009c_gets_its_old_rows_marked_confirmed_terminal_not_pending(tmp_path):
    # TC-010
    db = make_old(tmp_path / "platform.db", confirmations=_CONF_009D, job_rows=False)
    con = open_new(db)
    got = con.execute("SELECT id, state, channel, confirmed_at, created_at FROM confirmations").fetchall()
    assert len(got) == 3
    for r in got:
        assert r["state"] == "confirmed" and r["channel"] == "TERMINAL" and r["confirmed_at"] == r["created_at"]
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('c3', 'x', 'clean_work', 1)")
    con.close()


def test_jobs_referencing_the_rebuilt_confirmations_keep_their_ids_and_links(tmp_path):
    # TC-011, TC-012
    db = make_old(tmp_path / "platform.db")
    jobs_before = rows_of(db, "jobs")
    conf_before = {r[0]: r for r in rows_of(db, "confirmations")}
    con = open_new(db)
    assert [tuple(r) for r in con.execute("SELECT * FROM jobs ORDER BY id")][:len(jobs_before)] == jobs_before
    joined = con.execute("SELECT j.id AS jid, j.confirmation_id AS cid, c.* FROM jobs j JOIN confirmations c ON c.id = j.confirmation_id").fetchall()
    assert len(joined) == 2
    for r in joined:
        assert tuple(r)[2:] == conf_before[r["cid"]]
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert [r["table"] for r in con.execute("PRAGMA foreign_key_list(jobs)")] == ["confirmations"]
    con.close()


def test_jobs_sequence_counter_survives(tmp_path):
    # TC-013
    db = make_old(tmp_path / "platform.db")
    raw = sqlite3.connect(str(db))
    raw.execute("DELETE FROM jobs WHERE id = (SELECT MAX(id) FROM jobs)")
    raw.commit()
    seq = raw.execute("SELECT seq FROM sqlite_sequence WHERE name = 'jobs'").fetchone()[0]
    assert seq > raw.execute("SELECT MAX(id) FROM jobs").fetchone()[0]
    raw.close()
    con = open_new(db)
    assert con.execute("SELECT seq FROM sqlite_sequence WHERE name = 'jobs'").fetchone()[0] == seq
    cur = con.execute(JOB_SQL, ("preflight", "queued", None))
    assert cur.lastrowid == seq + 1
    con.close()


@pytest.mark.parametrize("with_read_task_log", [False, True])
def test_a_jobs_table_without_read_task_log_is_upgraded_straight_to_the_newest_kinds_in_one_open(tmp_path, with_read_task_log):
    # TC-014, TC-015
    db = make_old(tmp_path / "platform.db", jobs=old_jobs(read_task_log=with_read_task_log))
    before = rows_of(db, "jobs")
    fresh = open_new(tmp_path / "fresh.db")
    fresh_cols = cols_of(fresh, "jobs")
    fresh.close()
    con = open_new(db)
    assert cols_of(con, "jobs") == fresh_cols
    assert [tuple(r) for r in con.execute("SELECT * FROM jobs ORDER BY id")] == before
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('c3', 'x', 'clean_work', 1)")
    con.execute(JOB_SQL, ("read_task_log", "queued", None))
    con.execute(JOB_SQL, ("clean_work", "queued", "c3"))
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(JOB_SQL, ("clean_work", "queued", None))
    con.close()


def test_a_jobs_table_that_already_has_both_kinds_is_not_rebuilt(tmp_path):
    # TC-016
    db = tmp_path / "platform.db"
    open_new(db).close()
    page = rootpage(db, "jobs")
    digest = all_files_digest(db)
    open_new(db).close()
    assert rootpage(db, "jobs") == page and all_files_digest(db) == digest


def test_a_launches_table_without_the_attempt_columns_and_without_work_cleaned_at_gets_all_four(tmp_path):
    # TC-017
    db = make_old(tmp_path / "platform.db", launches=NO_ATTEMPT_LAUNCHES)
    before = rows_of(db, "launches")
    con = open_new(db)
    assert cols_of(con, "launches")[-4:] == ["parent_run", "attempt", "attempt_kind", "work_cleaned_at"]
    fresh = open_new(tmp_path / "fresh.db")
    assert cols_of(con, "launches") == cols_of(fresh, "launches")
    fresh.close()
    got = [tuple(r) for r in con.execute("SELECT * FROM launches ORDER BY id")]
    for old, new in zip(before, got):
        assert new[:len(old)] == old and new[len(old):] == (None, None, None, None)
    con.close()


def test_old_launches_rows_keep_every_old_value_and_get_null_work_cleaned_at(tmp_path):
    # TC-018
    db = make_old(tmp_path / "platform.db")
    before = rows_of(db, "launches")
    assert len(before) == 2
    con = open_new(db)
    got = [tuple(r) for r in con.execute("SELECT * FROM launches ORDER BY id")]
    assert [g[:-1] for g in got] == before and [g[-1] for g in got] == [None, None]
    con.close()


@pytest.mark.parametrize("old", ["current", "009c", "no_attempt", "007"])
def test_a_new_and_an_upgraded_database_have_the_same_structure_for_confirmations_jobs_and_launches(tmp_path, old):
    # TC-019, TC-020
    kwargs = {"current": {}, "009c": {"confirmations": _CONF_009D, "jobs": old_jobs(read_task_log=False), "launches": NO_ATTEMPT_LAUNCHES},
              "no_attempt": {"launches": NO_ATTEMPT_LAUNCHES},
              "007": {"confirmations": None, "jobs": _JOBS_007, "launches": _LAUNCH_007}}[old]
    db = make_old(tmp_path / "old.db", **kwargs)
    jobs_before = rows_of(db, "jobs")
    up, new = open_new(db), open_new(tmp_path / "new.db")
    assert structure(up) == structure(new)
    got = [tuple(r) for r in up.execute("SELECT * FROM jobs ORDER BY id")]
    assert [g[:len(jobs_before[0])] for g in got] == [r[:len(jobs_before[0])] for r in jobs_before] or old == "007"
    if old == "007":
        assert [(g[0], g[1], g[2], g[3]) for g in got] == [(r[0], r[1], r[2], r[3]) for r in jobs_before]
    up.close()
    new.close()


def test_pending_and_void_requests_made_before_the_upgrade_are_still_found_by_confirm_describe(tmp_path):
    # TC-021
    from abf_platform import confirm
    db = make_old(tmp_path / "platform.db")
    open_new(db).close()
    for rid, state in (("p1", "pending"), ("v1", "void")):
        got = confirm.describe(db, rid, clock=lambda: 20.0)
        assert got is not None and got["state"] == state and got["id"] == rid
    assert confirm.describe(db, "p1", clock=lambda: 20.0)["summary"] == "screen one"
    assert confirm.describe(db, "v1", clock=lambda: 20.0)["kind"] == "cancel"


# ---- US3: again, failing, at once, read-only ------------------------------------------------------------------------
def test_opening_twice_changes_nothing(tmp_path):
    # TC-022, TC-023
    fresh = tmp_path / "fresh.db"
    open_new(fresh).close()
    d = all_files_digest(fresh)
    open_new(fresh).close()
    assert all_files_digest(fresh) == d
    old = make_old(tmp_path / "old.db")
    open_new(old).close()
    d = all_files_digest(old)
    open_new(old).close()
    open_new(old).close()
    assert all_files_digest(old) == d


def test_an_already_new_confirmations_table_is_not_touched(tmp_path):
    # TC-024
    db = make_old(tmp_path / "platform.db")
    open_new(db).close()
    page, digest = rootpage(db, "confirmations"), all_files_digest(db)
    open_new(db).close()
    assert rootpage(db, "confirmations") == page and all_files_digest(db) == digest
    con = sqlite3.connect(str(db))
    assert not con.execute("SELECT 1 FROM sqlite_master WHERE name = 'confirmations_new'").fetchall()
    con.close()


def _boom_on_copied(step):
    if step == "copied":
        raise RuntimeError("injected")


def _with_current_jobs(db, link_to, kind):
    from abf_platform import store
    raw = sqlite3.connect(str(db))
    raw.execute("DROP TABLE jobs")
    raw.execute(store._JOBS_TABLE % {"name": "jobs"})
    raw.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
                "VALUES ('a1', 'lab-a', ?, '{}', 'done', 1, 2, ?)", (kind, link_to))
    raw.commit()
    raw.close()


def test_a_failure_in_the_copy_step_leaves_the_old_table_and_rows_as_they_were_and_foreign_keys_on(tmp_path, monkeypatch):
    # TC-025, TC-026
    from abf_platform import store
    db = make_old(tmp_path / "platform.db")
    _with_current_jobs(db, "c1", "launch_nextflow")      # the jobs table is current, so only the confirmations rebuild reaches the copy step
    before = {t: rows_of(db, t) for t in ("confirmations", "jobs", "launches")}
    monkeypatch.setattr(store, "_migration_step", _boom_on_copied)
    with pytest.raises(RuntimeError):
        store.connect_state(db)
    direct = sqlite3.connect(str(db))
    direct.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(RuntimeError):
        store._migrate_confirmation_kinds(direct)
    assert direct.execute("PRAGMA foreign_keys").fetchone()[0] == 1 and direct.isolation_level == ""
    assert not direct.in_transaction
    direct.close()
    assert {t: rows_of(db, t) for t in ("confirmations", "jobs", "launches")} == before
    chk = sqlite3.connect(str(db))
    assert declared_kinds(check_of(chk, "confirmations")) == ["launch", "cancel"]
    assert not chk.execute("SELECT 1 FROM sqlite_master WHERE name = 'confirmations_new'").fetchall()
    chk.close()
    monkeypatch.undo()
    con = store.connect_state(db)
    assert [tuple(r) for r in con.execute("SELECT * FROM confirmations ORDER BY rowid")] == before["confirmations"]
    assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    con.close()


def test_a_dangling_job_link_stops_the_rebuild_and_rolls_it_back(tmp_path):
    # TC-028
    from abf_platform import store
    db = make_old(tmp_path / "platform.db")
    _with_current_jobs(db, "ghost", "cancel_run")
    before = rows_of(db, "confirmations")
    with pytest.raises(sqlite3.Error):
        store.connect_state(db)
    direct = sqlite3.connect(str(db))
    direct.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.Error):
        store._migrate_confirmation_kinds(direct)
    assert direct.execute("PRAGMA foreign_keys").fetchone()[0] == 1 and not direct.in_transaction
    direct.close()
    assert rows_of(db, "confirmations") == before
    chk = sqlite3.connect(str(db))
    assert declared_kinds(check_of(chk, "confirmations")) == ["launch", "cancel"]
    assert not chk.execute("SELECT 1 FROM sqlite_master WHERE name = 'confirmations_new'").fetchall()
    chk.close()


def test_a_second_connection_opening_at_the_same_time_finds_it_done_and_does_not_fail(tmp_path):
    # TC-027
    db = make_old(tmp_path / "platform.db")
    before = rows_of(db, "confirmations")
    errors, barrier = [], threading.Barrier(2)

    def go():
        try:
            barrier.wait(timeout=10)
            open_new(db).close()
        except BaseException as e:      # noqa: BLE001 - the test reports whatever came out
            errors.append(e)

    threads = [threading.Thread(target=go) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert errors == []
    assert rows_of(db, "confirmations") == before
    up, new = open_new(db), open_new(tmp_path / "new.db")
    assert structure(up) == structure(new)
    up.close()
    new.close()


def test_read_only_open_of_an_old_database_does_not_upgrade_it(tmp_path):
    # TC-029
    from abf_platform import store
    db = make_old(tmp_path / "platform.db")
    digest = all_files_digest(db)
    con = store.open_readonly(db)
    assert len(con.execute("SELECT * FROM confirmations").fetchall()) == 3
    con.close()
    assert all_files_digest(db) == digest
    chk = sqlite3.connect(str(db))
    assert declared_kinds(check_of(chk, "confirmations")) == ["launch", "cancel"]
    assert "work_cleaned_at" not in cols_of(chk, "launches")
    chk.close()


# ---- US4: nothing goes live ------------------------------------------------------------------------------------------
def test_nothing_writes_clean_work_or_work_cleaned_at(tmp_path):
    # TC-030
    for p in sorted(PKG.rglob("*.py")):
        # cloud-cleanup-b (ruling 2): confirm.py and jobs.py now legitimately handle clean_work;
        # jobs.py also records work_cleaned_at. Nothing else may.
        if p.name not in ("store.py", "confirm.py", "jobs.py"):
            text = p.read_text(encoding="utf-8")
            assert "work_cleaned_at" not in text and "clean_work" not in text, p.name
        elif p.name == "confirm.py":
            assert "work_cleaned_at" not in p.read_text(encoding="utf-8"), p.name
    store_text = (PKG / "store.py").read_text(encoding="utf-8")
    for m in re.finditer(r".*work_cleaned_at.*", store_text):
        assert not re.search(r"\b(INSERT|UPDATE|SELECT|DELETE)\b", m.group(0)), m.group(0)
    con = open_new(tmp_path / "platform.db")
    assert con.execute("SELECT COUNT(*) FROM confirmations WHERE kind = 'clean_work'").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'clean_work'").fetchone()[0] == 0
    con.close()


def test_a_new_database_has_the_same_tables_and_indexes_as_before(tmp_path):
    # TC-032
    con = open_new(tmp_path / "platform.db")
    names = sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
    assert names == ["agents", "compute_envs", "confirmations", "jobs", "launches", "launches_run_name", "meta"]
    assert cols_of(con, "jobs") == ["id", "agent", "compute_env", "kind", "args_json", "state", "result_json", "late_result_json",
                                    "created_at", "deadline_at", "claimed_at", "finished_at", "forgotten_at", "forgotten_by",
                                    "confirmation_id"]
    con.close()


def test_the_upgrade_deletes_and_recomputes_nothing(tmp_path):
    # TC-033
    db = make_old(tmp_path / "platform.db")
    raw = sqlite3.connect(str(db))
    raw.execute("UPDATE jobs SET state = 'expired' WHERE kind = 'list_site_files'")
    raw.execute("UPDATE jobs SET state = 'refused' WHERE kind = 'preflight'")
    raw.commit()
    raw.close()
    before = {t: rows_of(db, t) for t in ("confirmations", "jobs", "launches")}
    open_new(db).close()
    after = {t: rows_of(db, t) for t in ("confirmations", "jobs", "launches")}
    assert after["confirmations"] == before["confirmations"] and after["jobs"] == before["jobs"]
    assert [r[:-1] for r in after["launches"]] == before["launches"]


def test_store_source_has_no_subprocess_and_no_forbidden_word():
    # TC-050, TC-051
    text = (PKG / "store.py").read_text(encoding="utf-8")
    for word in ("subprocess", "os.system", "threading", "while True"):
        assert word not in text, word
    assert "rm -rf" not in text and "rmtree" not in text
    assert "_migrate_confirmation_kinds" in text and "_add_cleanup_column" in text
