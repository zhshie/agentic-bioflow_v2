# Nothing existing: searched Celery/RQ job kinds and cloud SDK uploaders; none fits a one-table SQLite queue that must not read bytes or start programs (principle 2), so the new job kind is tested here against our own rules.
"""byte-channel-a: the platform side of a new job kind, `put_upload` (queue, check, migrate, clean the answer).
The TC ids refer to specs/byte-channel-a/test-case.md. A fake `lstat` stands in for the file; no network, no program, no key file."""
import inspect
import json
import re
import sqlite3
import stat as st
import time
from types import SimpleNamespace

import pytest

from helpers import PLATFORM_DIR
from test_gcb_ce import fields, jobs_count, set_status, ip  # noqa: F401  (ip is a fixture)

T = time.time()
UPLOAD_LIMIT = 2_000_000_000
NAME = "reads.fastq.gz"
NOT_FOUND = "compute environment %r not found (找不到)"


def fake_stat(size=500, mode=st.S_IFREG | 0o644, missing=False):
    def _stat(path):
        if missing:
            raise FileNotFoundError(path)
        return SimpleNamespace(st_mode=mode, st_size=size)
    return _stat


class World:
    def __init__(self, ip, tmp):
        from abf_platform import agents, compute_envs, store
        self.ip, self.uploads = ip, tmp / "uploads"
        self.ids = {}
        for who in ("alice", "bob"):
            self.ids[who] = store.create_user(ip.tokens, who, "lab")
            agents.register(ip.state_db, "ag-" + who, "0.1.0", lambda: T, owner_user_id=self.ids[who])
        compute_envs.create(ip.state_db, fields("gcb1", agent="ag-alice", owner_user_id=self.ids["alice"]))
        compute_envs.create(ip.state_db, fields("bobenv", agent="ag-bob", owner_user_id=self.ids["bob"],
                                                config={"project": "lab-project-1", "location": "europe-west2", "workDir": "gs://bob-bucket/work/"}))
        set_status(ip, "gcb1", "available")
        set_status(ip, "bobenv", "available")

    def put(self, name=NAME, ce="gcb1", owner="alice", uid="alice", stat=None, clock=None, **kw):
        from abf_platform import jobs
        uid = self.ids[uid] if uid in self.ids else uid
        return jobs.enqueue_put_upload(self.ip.state_db, self.ip.tokens, ce, owner, name, self.uploads, uid,
                                       clock=clock or (lambda: T), stat=stat or fake_stat(), **kw)

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
def w(ip, tmp_path):
    return World(ip, tmp_path)


def sql(db, text, args=()):
    con = sqlite3.connect(str(db))
    try:
        with con:
            return con.execute(text, args).fetchall()
    finally:
        con.close()


JOB_SQL = ("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
           "VALUES ('a1', 'x', ?, '{}', 'queued', 1, 2, ?)")


def jobs_check(db):
    text = sql(db, "SELECT sql FROM sqlite_master WHERE name = 'jobs'")[0][0]
    return re.findall(r"'([a-z_]+)'", re.search(r"CHECK \(kind IN \(([^)]*)\)\)", text).group(1))


def new_db(tmp_path):
    from abf_platform import store
    db = tmp_path / "platform.db"
    store.connect_state(db).close()
    return db


# ---- US1: the database -------------------------------------------------------------------------------------------------
def test_tc001_tc002_put_upload_needs_no_confirmation_and_odd_kinds_stay_refused(tmp_path):
    # TC-001, TC-002
    db = new_db(tmp_path)
    con = sqlite3.connect(str(db))
    con.execute(JOB_SQL, ("put_upload", None))
    n = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    for kind in ("put", "upload", "put_uploads", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(JOB_SQL, (kind, None))
    assert con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == n
    con.close()


def test_tc003_check_list_is_the_base_list_with_put_upload_last(tmp_path):
    # TC-003
    assert jobs_check(new_db(tmp_path)) == ["preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records",
                                            "read_task_log", "clean_work", "put_upload", "pipeline_files", "read_run_file"]      # release-lookup-job: pipeline_files comes after put_upload; results-files: read_run_file is last


def test_tc004_the_kinds_that_write_still_need_a_confirmation(tmp_path):
    # TC-004
    con = sqlite3.connect(str(new_db(tmp_path)))
    for kind in ("launch_nextflow", "cancel_run", "clean_work"):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(JOB_SQL, (kind, None))
    con.close()


def old_db(tmp_path, cut):
    """A platform.db whose jobs CHECK lacks the kinds named in cut, with three rows (one with a confirmation)."""
    from abf_platform import store
    db = new_db(tmp_path)
    con = sqlite3.connect(str(db))
    text = con.execute("SELECT sql FROM sqlite_master WHERE name = 'jobs'").fetchone()[0]
    old = text
    for kind in cut:
        old = old.replace(", '%s'" % kind, "")
        assert old != text or kind == cut[0]
    assert old != text
    con.execute("ALTER TABLE jobs RENAME TO jobs_cur")
    con.execute(old)
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, state) VALUES ('c1', 'x', 'launch', 1, 'confirmed')")
    for r in (("a1", "lab-a", "preflight", "{}", "done", 1.0, 2.0, None), ("a1", "lab-a", "list_site_files", "{}", "queued", 3.0, 4.0, None),
              ("a1", "lab-a", "launch_nextflow", "{}", "expired", 5.0, 6.0, "c1")):
        con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", r)
    con.execute("DROP TABLE jobs_cur")
    con.commit()
    con.close()
    return db


COLS = "SELECT id, agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id FROM jobs ORDER BY id"


def test_tc005_to_tc008_a_table_without_put_upload_is_upgraded_and_keeps_its_rows(tmp_path):
    # TC-005, TC-006, TC-007, TC-008
    from abf_platform import store
    db = old_db(tmp_path, ["put_upload"])
    before = sql(db, COLS)
    assert len(before) == 3
    store.connect_state(db).close()
    assert sql(db, COLS) == before
    con = sqlite3.connect(str(db))
    con.execute(JOB_SQL, ("preflight", None))
    assert con.execute("SELECT MAX(id) FROM jobs").fetchone()[0] == 4
    con.execute(JOB_SQL, ("put_upload", None))
    for bad in ("rm", "launch", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(JOB_SQL, (bad, None))
    con.close()


def test_tc009_tc010_a_failure_in_the_middle_leaves_the_old_table_and_a_retry_succeeds(tmp_path, monkeypatch):
    # TC-009, TC-010
    from abf_platform import store
    db = old_db(tmp_path, ["put_upload"])
    before = sql(db, COLS)
    old_sql = sql(db, "SELECT sql FROM sqlite_master WHERE name = 'jobs'")

    def boom(step):
        if step == "copied":
            raise RuntimeError("stop")
    monkeypatch.setattr(store, "_migration_step", boom)
    with pytest.raises(RuntimeError):
        store.connect_state(db)
    assert sql(db, COLS) == before and sql(db, "SELECT sql FROM sqlite_master WHERE name = 'jobs'") == old_sql
    monkeypatch.undo()
    store.connect_state(db).close()
    assert sql(db, COLS) == before
    assert "put_upload" in jobs_check(db)


def test_tc011_a_current_table_is_not_rebuilt(tmp_path):
    # TC-011
    from abf_platform import store
    db = new_db(tmp_path)
    sql(db, JOB_SQL, ("put_upload", None))
    snap = (sql(db, "SELECT sql FROM sqlite_master WHERE name = 'jobs'"), sql(db, "SELECT rowid, * FROM jobs"))
    store.connect_state(db).close()
    store.connect_state(db).close()
    assert (sql(db, "SELECT sql FROM sqlite_master WHERE name = 'jobs'"), sql(db, "SELECT rowid, * FROM jobs")) == snap


def test_tc012_tc013_tables_missing_older_kinds_are_also_rebuilt_to_the_newest(tmp_path):
    # TC-012, TC-013 (the older tests test_tc110_* and test_cleanup_store stay as they were)
    from abf_platform import store
    for i, cut in enumerate((["read_task_log", "clean_work", "put_upload"], ["clean_work"], ["read_task_log"])):
        d = tmp_path / str(i)
        d.mkdir()
        db = old_db(d, cut)
        before = sql(db, COLS)
        store.connect_state(db).close()
        assert sql(db, COLS) == before and jobs_check(db)[-3:] == ["put_upload", "pipeline_files", "read_run_file"] and "clean_work" in jobs_check(db)      # release-lookup-job: put_upload before pipeline_files; results-files: read_run_file is last


def test_tc014_only_the_jobs_table_is_rebuilt(tmp_path):
    # TC-014
    from abf_platform import store
    db = old_db(tmp_path, ["put_upload"])
    sql(db, "INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at) VALUES ('r', '/f', 'c', 'a', 1)")
    sql(db, "INSERT INTO agents (name, version, first_seen_at, last_seen_at) VALUES ('a', '1', 1, 1)")
    names = ("confirmations", "launches", "compute_envs", "agents")
    snap = {n: (sql(db, "SELECT sql FROM sqlite_master WHERE name = ?", (n,)), sql(db, "SELECT * FROM " + n)) for n in names}
    store.connect_state(db).close()
    assert {n: (sql(db, "SELECT sql FROM sqlite_master WHERE name = ?", (n,)), sql(db, "SELECT * FROM " + n)) for n in names} == snap


# ---- US2: constants ----------------------------------------------------------------------------------------------------
def test_tc015_tc016_kinds_end_with_put_upload_and_confirmed_is_unchanged():
    # TC-015, TC-016
    from abf_platform import jobs
    assert jobs.KINDS[-3:] == ("put_upload", "pipeline_files", "read_run_file") and jobs.KINDS[:-3] == ("preflight", "list_site_files", "launch_nextflow", "cancel_run",      # release-lookup-job: put_upload before pipeline_files, which is last
                                                                  "fetch_run_records", "read_task_log", "clean_work")
    assert jobs.CONFIRMED == {"launch_nextflow": "launch", "cancel_run": "cancel", "clean_work": "clean_work"}


def test_tc017_tc018_tc019_the_deadline(monkeypatch):
    # TC-017, TC-018, TC-019
    from abf_platform import jobs
    monkeypatch.delenv("ABF_PLATFORM_DEADLINE_PUT_UPLOAD", raising=False)
    assert jobs.deadline_seconds("put_upload") == 3600
    monkeypatch.setenv("ABF_PLATFORM_DEADLINE_PUT_UPLOAD", "7")
    assert jobs.deadline_seconds("put_upload") == 7
    for bad in ("abc", "-1", "0"):
        monkeypatch.setenv("ABF_PLATFORM_DEADLINE_PUT_UPLOAD", bad)
        assert jobs.deadline_seconds("put_upload") == 3600


def test_tc020_tc021_the_upload_limit():
    # TC-020, TC-021
    from abf_platform import cloud_store
    from abf_platform.actions import datasets
    assert cloud_store.UPLOAD_LIMIT == 2_000_000_000 == datasets.WEB_UPLOAD_LIMIT


def test_tc022_the_generic_enqueue_does_not_take_put_upload(w):
    # TC-022
    from abf_platform import jobs
    before = jobs_count(w.ip)
    with pytest.raises(jobs.JobRefused) as e:
        jobs._enqueue(w.ip.state_db, "gcb1", "put_upload", None, lambda: T, None, None, w.ids["alice"])
    assert "enqueue_put_upload" in str(e.value) and jobs_count(w.ip) == before


# ---- US3: queueing -----------------------------------------------------------------------------------------------------
def test_tc023_to_tc029_a_job_carries_only_a_reference(w):
    # TC-023, TC-024, TC-025, TC-026, TC-027, TC-028, TC-029
    from abf_platform import compute_envs
    jid = w.put()
    row = w.row(jid)
    assert row["kind"] == "put_upload" and row["state"] == "queued" and row["confirmation_id"] is None
    assert row["deadline_at"] == T + 3600
    args = json.loads(row["args_json"])
    assert set(args) == {"ce", "owner", "name", "size", "dest"}
    assert (args["owner"], args["name"], args["size"]) == ("alice", NAME, 500)
    assert args["dest"] == "gs://lab-bucket/uploads/alice/reads.fastq.gz"
    con = sqlite3.connect(str(w.ip.state_db))
    con.row_factory = sqlite3.Row
    snap = compute_envs.snapshot(con.execute("SELECT * FROM compute_envs WHERE name = 'gcb1'").fetchone())
    con.close()
    assert args["ce"] == snap and "workDir" in args["ce"]
    whole = json.dumps(dict(row))
    for needle in (str(w.uploads), "gcp-sa", "private_key", "/home"):
        assert needle not in whole


def test_tc030_tc031_the_agent_gets_the_job_without_confirmation_or_run_token(w):
    # TC-030, TC-031
    from abf_platform import jobs
    jid = w.put()
    out = jobs.claim(w.ip.state_db, "ag-alice", lambda: T + 1, tokens_path=w.ip.tokens)
    assert out["id"] == jid and out["kind"] == "put_upload" and "confirmation" not in out and "run_token" not in out
    assert out["remaining"] <= 3600 and w.row(jid)["state"] == "claimed"


def test_tc032_the_same_file_can_be_queued_twice(w):
    # TC-032
    assert w.put() != w.put()


@pytest.mark.parametrize("size", [1, UPLOAD_LIMIT])
def test_tc033_tc034_the_size_edges_that_are_taken(w, size):
    # TC-033, TC-034
    assert json.loads(w.row(w.put(stat=fake_stat(size)))["args_json"])["size"] == size


def test_tc035_only_lstat_is_used_and_no_file_is_needed(w):
    # TC-035
    seen = []

    def spy(path):
        seen.append(str(path))
        return fake_stat()(path)
    w.put(stat=spy)
    assert len(seen) == 1 and not w.uploads.exists()
    from abf_platform import jobs
    src = inspect.getsource(jobs.enqueue_put_upload)
    assert "open(" not in src and "hashlib" not in src and "read(" not in src


def test_tc036_the_caller_cannot_pass_an_address(w):
    # TC-036
    from abf_platform import jobs
    params = inspect.signature(jobs.enqueue_put_upload).parameters
    assert "dest" not in params and "url" not in params
    for key in ("dest", "url"):
        with pytest.raises(TypeError):
            w.put(**{key: "gs://other/uploads/alice/x"})
    assert jobs_count(w.ip) == 0


# ---- US4: refusals -----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("uid", [None, "1", True])
def test_tc037_tc038_a_caller_must_be_a_user_id(w, uid):
    # TC-037, TC-038
    assert w.refused(uid=uid)


def test_tc039_tc040_tc041_tc042_nobody_else_s_prefix_or_environment_and_nothing_leaks(w):
    # TC-039, TC-040, TC-041, TC-042
    missing = NOT_FOUND % "gcb1"
    assert w.refused(owner="bob") == missing                                     # alice's id with bob's name
    other = w.refused(ce="bobenv")
    assert other == NOT_FOUND % "bobenv"
    assert w.refused(ce="nothing") == NOT_FOUND % "nothing"
    assert w.refused(ce="bobenv", stat=fake_stat(missing=True)) == other             # the file's existence is not told
    assert w.refused(ce="bobenv", stat=fake_stat(500)) == other


def test_tc043_a_slurm_environment_is_refused(w):
    # TC-043
    sql(w.ip.state_db, "UPDATE compute_envs SET platform = 'slurm-platform' WHERE name = 'gcb1'")
    assert "Google Batch" in w.refused()


@pytest.mark.parametrize("status", ["unsupported", "disabled", "unchecked", "unavailable"])
def test_tc044_to_tc048_only_an_available_environment_takes_it(w, status):
    # TC-044, TC-045, TC-046, TC-047, TC-048
    set_status(w.ip, "gcb1", status)
    msg = w.refused()
    if status == "unchecked":
        assert "abf-platform ce preflight" in msg
    if status == "unavailable":
        assert "store a file" in msg
    set_status(w.ip, "gcb1", "available")
    assert w.put()


def test_tc049_an_offline_agent_is_named(w):
    # TC-049
    assert "ag-alice" in w.refused(clock=lambda: T + 10_000)


BAD_NAMES = ["", "a/b", "a\\b", "..", ".", "x\x00y", "n" * 256, "x\ny"]


@pytest.mark.parametrize("name", BAD_NAMES)
def test_tc050_tc051_bad_file_names_are_refused_without_echo(w, name):
    # TC-050, TC-051
    msg = w.refused(name=name)
    assert name not in msg or name in ("", ".", "..")
    assert "x\ny" not in msg and "n" * 20 not in msg


def test_tc052_to_tc055_a_file_that_is_not_a_plain_file_inside_the_folder(w, monkeypatch):
    # TC-052, TC-053, TC-054, TC-055
    w.refused(stat=fake_stat(missing=True))
    w.refused(stat=fake_stat(mode=st.S_IFDIR | 0o755))
    w.refused(stat=fake_stat(mode=st.S_IFLNK | 0o777))
    import os
    real = os.path.realpath
    monkeypatch.setattr(os.path, "realpath", lambda p, *a, **k: real(str(w.uploads / "elsewhere" / "x"))
                        if str(p).endswith(NAME) else real(p, *a, **k))
    w.refused()


def test_tc056_tc057_tc058_the_size_limits_and_the_command(w):
    # TC-056, TC-057, TC-058
    assert "空檔案" in w.refused(stat=fake_stat(0))
    msg = w.refused(stat=fake_stat(UPLOAD_LIMIT + 1))
    assert "gcloud storage cp <你電腦上的資料夾>/* gs://lab-bucket/uploads/alice/rawdata/" in msg


def test_tc059_no_refusal_shows_the_upload_folder_sql_or_a_trace(w, monkeypatch):
    # TC-059: every refusal of TC-037..057 is collected, and each one says what happened without leaking
    import os
    msgs = {}
    for uid in (None, "1", True):                                                    # TC-037, TC-038
        msgs["uid=%r" % (uid,)] = w.refused(uid=uid)
    msgs["owner"] = w.refused(owner="bob")                                          # TC-039
    msgs["other env"] = w.refused(ce="bobenv")                                      # TC-040
    msgs["no env"] = w.refused(ce="nothing")                                        # TC-041
    msgs["other env, no file"] = w.refused(ce="bobenv", stat=fake_stat(missing=True))      # TC-042
    for status in ("unsupported", "disabled", "unchecked", "unavailable"):          # TC-044..047
        set_status(w.ip, "gcb1", status)
        msgs["status " + status] = w.refused()
    set_status(w.ip, "gcb1", "available")
    msgs["offline agent"] = w.refused(clock=lambda: T + 10_000)                      # TC-049
    for name in BAD_NAMES:                                                          # TC-050
        msgs["name %r" % name] = w.refused(name=name)
    msgs["missing file"] = w.refused(stat=fake_stat(missing=True))                  # TC-052
    msgs["folder"] = w.refused(stat=fake_stat(mode=st.S_IFDIR | 0o755))              # TC-053
    msgs["symlink"] = w.refused(stat=fake_stat(mode=st.S_IFLNK | 0o777))             # TC-054
    real = os.path.realpath
    with monkeypatch.context() as m:                                                # TC-055
        m.setattr(os.path, "realpath", lambda p, *a, **k: real(str(w.uploads / "elsewhere" / "x"))
                  if str(p).endswith(NAME) else real(p, *a, **k))
        msgs["outside the folder"] = w.refused()
    msgs["empty"] = w.refused(stat=fake_stat(0))                                    # TC-056
    msgs["too big"] = w.refused(stat=fake_stat(UPLOAD_LIMIT + 1))                   # TC-057
    sql(w.ip.state_db, "UPDATE compute_envs SET platform = 'slurm-platform' WHERE name = 'gcb1'")
    msgs["slurm"] = w.refused()                                                     # TC-043
    assert len(msgs) >= 24
    for why, m in msgs.items():
        assert len(m.strip()) >= 12, why                                            # it says something
        assert re.search(r"[一-鿿]|\(.*[a-z]{4}.*\)", m), why                  # in words a person reads
        assert str(w.uploads) not in m and str(w.uploads.parent) not in m, why
        for bad in ("SELECT", "INSERT", "UPDATE", "sqlite", "Traceback", "File \"", "Error(", "\n"):
            assert bad not in m, (why, bad)


# ---- US5: the answer ---------------------------------------------------------------------------------------------------
def clean(result):
    from abf_platform import jobs
    return jobs.clean_result("put_upload", result)


GOOD = {"ok": True, "bytes": 500, "path": "gs://b/uploads/alice/x"}


def test_tc060_tc061_only_the_three_keys_survive():
    # TC-060, TC-061
    assert clean(GOOD) == GOOD
    out = clean(dict(GOOD, stdout="s", key="k", text="t", entries=[{"name": "n"}], private_key="p"))
    assert out == GOOD


def test_tc062_to_tc065_a_success_needs_a_number_and_a_place():
    # TC-062, TC-063, TC-064, TC-065
    assert clean({"ok": True, "path": GOOD["path"]})["ok"] is False
    for bad in (True, -1, "500", 2_000_000_001):
        out = clean({"ok": True, "bytes": bad, "path": GOOD["path"]})
        assert out["ok"] is False and "bytes" not in out
    assert clean({"ok": True, "bytes": 5, "path": 12})["ok"] is False
    assert clean({"ok": True, "bytes": 5})["ok"] is False


def test_tc066_tc067_tc068_texts_are_cut():
    # TC-066, TC-067, TC-068
    assert len(clean(dict(GOOD, path="g" * 1200))["path"]) <= 1100
    assert len(clean(dict(GOOD, message="m" * 5000))["message"]) <= 2000
    out = clean(dict(GOOD, error="e" * 1000, note="n" * 1000))
    assert len(out["error"]) <= 300 and len(out["note"]) <= 300


def test_tc069_a_failure_keeps_its_reason():
    # TC-069
    assert clean({"ok": False, "message": "no"}) == {"ok": False, "message": "no"}


def test_tc074_the_edge_values_are_kept():
    # TC-074
    for n in (0, UPLOAD_LIMIT):
        assert clean(dict(GOOD, bytes=n)) == dict(GOOD, bytes=n)


def test_tc070_to_tc073_take_result_stores_the_cleaned_answer_and_keeps_its_rules(w):
    # TC-070, TC-071, TC-072, TC-073
    from abf_platform import agents, jobs
    jid = w.put()
    jobs.claim(w.ip.state_db, "ag-alice", lambda: T + 1, tokens_path=w.ip.tokens)
    agents.register(w.ip.state_db, "ag-other", "0.1.0", lambda: T)
    assert jobs.take_result(w.ip.state_db, "ag-other", jid, "done", GOOD, lambda: T + 2)[0] == 403
    assert w.row(jid)["state"] == "claimed" and w.row(jid)["result_json"] is None
    assert jobs.take_result(w.ip.state_db, "ag-alice", jid, "done", dict(GOOD, stdout="s"), lambda: T + 2)[0] == 200
    assert json.loads(w.row(jid)["result_json"]) == GOOD
    assert jobs.take_result(w.ip.state_db, "ag-alice", jid, "done", dict(GOOD, bytes=1), lambda: T + 3)[0] == 409
    assert json.loads(w.row(jid)["result_json"]) == GOOD
    late = w.put()
    jobs.claim(w.ip.state_db, "ag-alice", lambda: T + 1, tokens_path=w.ip.tokens)
    code, body = jobs.take_result(w.ip.state_db, "ag-alice", late, "done", GOOD, lambda: T + 99_999)
    assert code == 200 and body["late"] is True and w.row(late)["state"] == "expired"


# ---- US6 / constitution ------------------------------------------------------------------------------------------------
def test_tc076_tc077_the_old_available_messages_keep_their_words(w):
    # TC-076, TC-077
    from abf_platform import jobs
    sql(w.ip.state_db, "UPDATE compute_envs SET platform = 'slurm-platform' WHERE name = 'gcb1'")
    set_status(w.ip, "gcb1", "unavailable")
    with pytest.raises(jobs.JobRefused) as a:
        jobs.enqueue_listing(w.ip.state_db, "gcb1", "/x", clock=lambda: T, caller_user_id=w.ids["alice"])
    assert "list files" in str(a.value)
    with pytest.raises(jobs.JobRefused) as b:                                       # TC-076: the launch keeps "run an analysis"
        jobs.check_target(w.ip.state_db, "gcb1", "launch_nextflow", caller_user_id=w.ids["alice"])
    assert "run an analysis" in str(b.value)


def test_tc080_tc083_the_platform_sources_start_no_program_and_the_new_lines_avoid_the_forbidden_word():
    # TC-080, TC-083
    for name in ("jobs.py", "store.py"):
        text = (PLATFORM_DIR / "abf_platform" / name).read_text(encoding="utf-8")
        assert "gcloud" not in text and "subprocess" not in text


def test_tc091_tc093_the_local_file_is_left_alone_and_one_job_is_one_file(w):
    # TC-091, TC-093
    folder = w.uploads / "alice"
    folder.mkdir(parents=True)
    f = folder / NAME
    f.write_bytes(b"x" * 500)
    from abf_platform import jobs
    before = jobs_count(w.ip)
    args = json.loads(w.row(w.put(stat=jobs.os.lstat))["args_json"])
    assert f.read_bytes() == b"x" * 500 and jobs_count(w.ip) == before + 1
    assert set(args) == {"ce", "owner", "name", "size", "dest"} and args["size"] == 500


def test_tc094_a_preflight_job_is_unchanged(w):
    # TC-094
    from abf_platform import jobs
    jid = jobs.enqueue_preflight(w.ip.state_db, "gcb1", clock=lambda: T)
    assert list(json.loads(w.row(jid)["args_json"])) == ["ce"]
