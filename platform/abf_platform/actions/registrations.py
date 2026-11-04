# Nothing existing: Seqera and nf-core keep no per-person record of which pipeline version is registered on which compute environment; the record and its states are this platform's own.
"""Pipeline registrations (pipe-reg-store): one row per (owner, compute environment, pipeline, revision) saying how far that version is in the
registration flow. This slice is only the record and its actions: nothing is checked, installed or tested here (`_start_check` is the hook the
next slice fills), and the environment's own `sitePipelines` list is read and never written. Every function takes the platform path first and
`caller=` (None = the terminal, which sees everything); what belongs to somebody else answers like what does not exist. The table is made the
first time a writer uses it and is not part of `store.STATE_SCHEMA`; a reader never makes it."""
import sqlite3
import time

from .. import compute_envs, store

_TABLE = """
CREATE TABLE IF NOT EXISTS pipeline_registrations (
    id INTEGER PRIMARY KEY,
    owner TEXT NOT NULL,
    compute_env TEXT NOT NULL,
    pipeline TEXT NOT NULL,
    revision TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('site-module','site-fetch','remote')),
    stage TEXT NOT NULL CHECK (stage IN ('checking','preparing','awaiting_test','testing','failed','removed')),
    check_job INTEGER,
    test_run TEXT,
    failed_step TEXT CHECK (failed_step IS NULL OR failed_step IN ('check','prepare','test')),
    reason TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    tested_at REAL,
    UNIQUE (owner, compute_env, pipeline, revision)
);
"""

_NOT_FOUND = "找不到所選的運算環境 (compute environment not found)"
_REG_NOT_FOUND = "找不到此登記紀錄 (registration not found)"
_BAD_NAME = "管線名稱格式不合，須為 nf-core/<名稱> (the pipeline must look like nf-core/<name>: lower-case letters, digits and - only)"
_BAD_REVISION = ("revision 格式不合，須為版本號如 3.26.0 或 40 位的 commit "
                 "(the revision must be a version number such as 3.26.0, or a 40-character commit id)")


def _no(message, field=None):
    return {"ok": False, "field": field, "message": message}


def _owner_key(user_id):
    return "" if user_id is None else str(user_id)


def _caller_id(caller):
    return caller.user_id if caller else None


def _require_human(confirmed_by):
    from . import _require_human as check
    check(confirmed_by)


def _state(row, run_status=None):
    """The state shown to people. This slice has no test analysis, so with no `run_status` it is the stored stage."""
    return row["stage"]


def _start_check(env, row):
    """Hook for pipe-reg-check: nothing is queued in this slice."""
    return None


def _item(row):
    return {"compute_env": row["compute_env"], "pipeline": row["pipeline"], "revision": row["revision"], "source": row["source"],
            "state": _state(row), "reason": row["reason"], "failed_step": row["failed_step"], "test_run": row["test_run"],
            "tested_at": row["tested_at"], "updated_at": row["updated_at"]}


def _source(env):
    return "site-module" if env["platform"] == compute_envs.SUPPORTED else "remote"


def _find_env(platform_path, ce, caller):
    if not isinstance(ce, str) or not ce:
        return None
    return compute_envs.get(platform_path, ce, owner=_caller_id(caller))


def _owner_of(platform_path, env):
    return _owner_key(compute_envs.owners(platform_path).get(env["name"]))


def _rows(platform_path, owner, name):
    """Every row of one environment, removed ones included. Reads only: a database without the table has none."""
    con = store.open_readonly(platform_path)
    if con is None:
        return []
    try:
        return list(con.execute("SELECT * FROM pipeline_registrations WHERE owner = ? AND compute_env = ? ORDER BY id", (owner, name)))
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def _items_of(platform_path, env):
    owner = _owner_of(platform_path, env)
    rows = _rows(platform_path, owner, env["name"])
    out = [_item(r) for r in rows if r["stage"] != "removed"]
    known = {(r["pipeline"], r["revision"]) for r in rows}
    if env["platform"] == compute_envs.SUPPORTED:
        for p in env["config"].get("sitePipelines") or []:
            if not isinstance(p, dict) or not isinstance(p.get("pipeline"), str) or not isinstance(p.get("revision"), str):
                continue
            key = (p["pipeline"], p["revision"])
            if key in known:
                continue
            known.add(key)
            out.append({"compute_env": env["name"], "pipeline": key[0], "revision": key[1], "source": "site-module", "state": "awaiting_test",
                        "reason": None, "failed_step": None, "test_run": None, "tested_at": None, "updated_at": None, "legacy": True})
    return out


def list_pipeline_registrations(platform_path, *, ce=None, caller=None):
    """The registrations of the caller's own compute environments (one environment with `ce`), removed ones left out. A Slurm environment's
    `sitePipelines` entries that have no row at all are added as {"state": "awaiting_test", "legacy": True}; that is read-time only, no row is written.
    Another person's environment answers as a missing one."""
    if ce is None:
        envs = compute_envs.list_all(platform_path, owner=_caller_id(caller))
    else:
        env = _find_env(platform_path, ce, caller)
        if env is None:
            return _no(_NOT_FOUND)
        envs = [env]
    items = []
    for env in envs:
        items.extend(_items_of(platform_path, env))
    return {"ok": True, "items": items}


def list_registered_pipelines(platform_path, *, ce, caller=None):
    """The pipeline versions of one of the caller's environments that are registered (state "registered"). Nothing is derived to that state in
    this slice, so the list is empty for now; entries from the old `sitePipelines` list never count."""
    answer = list_pipeline_registrations(platform_path, ce=ce if isinstance(ce, str) and ce else "", caller=caller)
    if not answer["ok"]:
        return answer
    return {"ok": True, "items": [i for i in answer["items"] if i["state"] == "registered" and not i.get("legacy")]}


def _required(value, field):
    if not isinstance(value, str) or not value:
        return _no("%s 必須填寫 (%s is required)" % (field, field), field)
    return None


def propose_pipeline_registration(platform_path, *, ce, pipeline, revision, confirmed_by=None, caller=None):
    """Record that the caller wants this pipeline version on one of their environments, in state "checking", only after a person's yes through
    `confirmed_by`. The same version again changes nothing; a removed one comes back to "checking". Queues nothing.
    Returns {"ok": True, "changed", "state"} or {"ok": False, "field", "message"}."""
    _require_human(confirmed_by)
    if not isinstance(ce, str) or not ce:
        return _no("請選擇運算環境 (choose a compute environment)", "ce")
    env = _find_env(platform_path, ce, caller)
    if env is None:
        return _no(_NOT_FOUND)
    from . import _SP_NAME
    bad = _required(pipeline, "pipeline")
    if bad:
        return bad
    if not _SP_NAME.match(pipeline):
        return _no(_BAD_NAME, "pipeline")
    bad = _required(revision, "revision")
    if bad:
        return bad
    if not compute_envs._REVISION.match(revision):
        return _no(_BAD_REVISION, "revision")
    owner = _owner_of(platform_path, env)
    now = time.time()
    con = store.connect_state(platform_path)
    try:
        con.executescript(_TABLE)
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT * FROM pipeline_registrations WHERE owner = ? AND compute_env = ? AND pipeline = ? AND revision = ?",
                          (owner, env["name"], pipeline, revision)).fetchone()
        if row is not None and row["stage"] != "removed":
            con.rollback()
            return {"ok": True, "changed": False, "state": _state(row)}
        if row is None:
            con.execute("INSERT INTO pipeline_registrations (owner, compute_env, pipeline, revision, source, stage, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, 'checking', ?, ?)", (owner, env["name"], pipeline, revision, _source(env), now, now))
        else:
            con.execute("UPDATE pipeline_registrations SET stage = 'checking', source = ?, reason = NULL, failed_step = NULL, check_job = NULL, "
                        "test_run = NULL, tested_at = NULL, updated_at = ? WHERE id = ?", (_source(env), now, row["id"]))
        new = con.execute("SELECT * FROM pipeline_registrations WHERE owner = ? AND compute_env = ? AND pipeline = ? AND revision = ?",
                          (owner, env["name"], pipeline, revision)).fetchone()
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    _start_check(env, new)
    return {"ok": True, "changed": True, "state": "checking"}


def remove_pipeline_registration(platform_path, *, ce, pipeline, revision, confirmed_by=None, caller=None):
    """Mark one registration of the caller's as removed, only after a person's yes. A version with no row (including one that exists only in the
    old `sitePipelines` list) is refused; the environment's own list is never touched. Removing twice changes nothing."""
    _require_human(confirmed_by)
    if not isinstance(ce, str) or not ce:
        return _no("請選擇運算環境 (choose a compute environment)", "ce")
    env = _find_env(platform_path, ce, caller)
    if env is None:
        return _no(_NOT_FOUND)
    for value, field in ((pipeline, "pipeline"), (revision, "revision")):
        bad = _required(value, field)
        if bad:
            return bad
    owner = _owner_of(platform_path, env)
    row = next((r for r in _rows(platform_path, owner, env["name"]) if r["pipeline"] == pipeline and r["revision"] == revision), None)
    if row is None:
        return _no(_REG_NOT_FOUND)
    if row["stage"] == "removed":
        return {"ok": True, "changed": False, "state": "removed"}
    con = store.connect_state(platform_path)
    try:
        con.execute("UPDATE pipeline_registrations SET stage = 'removed', updated_at = ? WHERE id = ?", (time.time(), row["id"]))
        con.commit()
    finally:
        con.close()
    return {"ok": True, "changed": True, "state": "removed"}
