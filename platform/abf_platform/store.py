# Not nf-shard: it keeps runs in Postgres through Prisma and accepts any token; this is three small SQLite files, the index, the token list and the agent and compute-environment state.
"""The three files the platform keeps.

index.db     the run index. It is an index, not the truth: `rebuild` drops it and builds it
             again from Nextflow's own records.
tokens.db    the accepted tokens, as hashes (run tokens and agent tokens). `rebuild` never opens it.
platform.db  compute environments, agents and the queue of read-only jobs. `rebuild` never opens it.
"""
import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    run_name TEXT NOT NULL,
    token_id INTEGER,
    source TEXT NOT NULL DEFAULT 'live',
    final_status TEXT,
    started_at INTEGER,
    ended_at INTEGER,
    last_message_at REAL NOT NULL,
    project_name TEXT,
    nextflow_version TEXT,
    exit_status INTEGER,
    params_json TEXT,
    n_succeeded INTEGER NOT NULL DEFAULT 0,
    n_cached INTEGER NOT NULL DEFAULT 0,
    n_failed INTEGER NOT NULL DEFAULT 0,
    n_aborted INTEGER NOT NULL DEFAULT 0,
    n_running INTEGER NOT NULL DEFAULT 0,
    n_pending INTEGER NOT NULL DEFAULT 0,
    n_submitted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS processes (
    run_id TEXT NOT NULL,
    name TEXT NOT NULL,
    n_succeeded INTEGER NOT NULL DEFAULT 0,
    n_cached INTEGER NOT NULL DEFAULT 0,
    n_failed INTEGER NOT NULL DEFAULT 0,
    n_aborted INTEGER NOT NULL DEFAULT 0,
    n_running INTEGER NOT NULL DEFAULT 0,
    n_pending INTEGER NOT NULL DEFAULT 0,
    n_submitted INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, name)
);
CREATE TABLE IF NOT EXISTS failed_tasks (
    run_id TEXT NOT NULL,
    task_key TEXT NOT NULL,
    name TEXT NOT NULL,
    exit_code INTEGER,
    error_message TEXT,
    PRIMARY KEY (run_id, task_key)
);
"""

# kind is 'run' (a Nextflow run writes with it) or 'agent' (an agent polls with it).
# Files written by feature 008 have no kind, agent_name or revoked_at: _migrate_tokens adds them.
TOKEN_SCHEMA = """
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL,
    kind TEXT NOT NULL DEFAULT 'run',
    agent_name TEXT,
    revoked_at REAL,
    run_name TEXT,
    expires_at REAL
);
"""

# A run token the platform made when an agent claimed a launch (feature 007b) is for one run name and lives 14 days.
RUN_TOKEN_TTL = 14 * 86400

# Compute environments, agents, jobs, confirmations and the hand-off record. Nothing here describes the state of a
# run: a job is a question or an order put to one agent, a confirmation is the user's "yes" to one content, and a
# launches row is a fact (who was told to launch what, and the number Slurm gave it), never a status.
# The CHECK constraints let exactly five job kinds in, and the two that write (launch_nextflow, cancel_run) only with
# a confirmation. The jobs table has the same columns in the same order whether it was made new or upgraded from 007's.
STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS compute_envs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    platform TEXT NOT NULL,
    credentials_id TEXT,
    agent TEXT,
    status TEXT NOT NULL,
    message TEXT,
    is_primary INTEGER NOT NULL DEFAULT 0,
    checked_ok INTEGER,
    config_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    last_used_at REAL
);
CREATE TABLE IF NOT EXISTS agents (
    name TEXT PRIMARY KEY,
    version TEXT,
    first_seen_at REAL NOT NULL,
    last_seen_at REAL NOT NULL,
    slurm_account TEXT,
    facts_json TEXT
);
CREATE TABLE IF NOT EXISTS confirmations (
    id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel')),
    created_at REAL NOT NULL,
    used_at REAL
);
%(jobs)s
CREATE TABLE IF NOT EXISTS launches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_name TEXT NOT NULL UNIQUE,
    slurm_job_id INTEGER,
    run_folder TEXT NOT NULL,
    ce TEXT NOT NULL,
    agent TEXT NOT NULL,
    confirmed_at REAL NOT NULL,
    submitted_at REAL,
    cancel_requested_at REAL
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_JOBS_TABLE = """CREATE TABLE %(name)s (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    compute_env TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('preflight', 'list_site_files', 'launch_nextflow', 'cancel_run', 'fetch_run_records')),
    args_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('queued', 'claimed', 'done', 'refused', 'error', 'expired')),
    result_json TEXT,
    late_result_json TEXT,
    created_at REAL NOT NULL,
    deadline_at REAL NOT NULL,
    claimed_at REAL,
    finished_at REAL,
    confirmation_id TEXT UNIQUE REFERENCES confirmations(id),
    CHECK (kind NOT IN ('launch_nextflow', 'cancel_run') OR confirmation_id IS NOT NULL)
)"""
STATE_SCHEMA = STATE_SCHEMA % {"jobs": (_JOBS_TABLE % {"name": "IF NOT EXISTS jobs"}) + ";"}
_JOB_COLUMNS = ("id, agent, compute_env, kind, args_json, state, result_json, late_result_json, created_at, deadline_at, "
                "claimed_at, finished_at")


def default_index_path(env=None):
    """ABF_PLATFORM_DB, else ${XDG_DATA_HOME:-~/.local/share}/abf-platform/index.db."""
    env = os.environ if env is None else env
    if env.get("ABF_PLATFORM_DB"):
        return Path(env["ABF_PLATFORM_DB"])
    base = env.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return Path(base) / "abf-platform" / "index.db"


def default_tokens_path(index_path=None, env=None):
    """ABF_PLATFORM_TOKENS, else tokens.db next to the index."""
    env = os.environ if env is None else env
    if env.get("ABF_PLATFORM_TOKENS"):
        return Path(env["ABF_PLATFORM_TOKENS"])
    return Path(index_path or default_index_path(env)).parent / "tokens.db"


def default_platform_path(index_path=None, env=None):
    """ABF_PLATFORM_STATE, else platform.db next to the index."""
    env = os.environ if env is None else env
    if env.get("ABF_PLATFORM_STATE"):
        return Path(env["ABF_PLATFORM_STATE"])
    return Path(index_path or default_index_path(env)).parent / "platform.db"


def connect(path, schema):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(schema)
    return con


def connect_index(path):
    return connect(path, SCHEMA)


def init_index(path):
    connect_index(path).close()


def _migration_step(step):
    """A hook between the steps of the upgrade of platform.db; the tests put a failure here."""


def _migrate_jobs(con):
    """A platform.db made by feature 007 has a jobs table that lets two kinds in and has no confirmation column.

    One transaction: build the new table, copy every row, drop the old one, rename. A failure anywhere rolls the
    whole thing back and the old table is as it was. Another process may have done it first, which is checked
    again once this one holds the write lock.
    """
    row = con.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'jobs'").fetchone()
    if row is None or "launch_nextflow" in row[0]:
        return
    con.isolation_level = None
    con.execute("BEGIN IMMEDIATE")
    try:
        row = con.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'jobs'").fetchone()
        if row is None or "launch_nextflow" in row[0]:
            con.execute("COMMIT")
            return
        con.execute("CREATE TABLE IF NOT EXISTS confirmations (id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, "
                    "kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel')), created_at REAL NOT NULL, used_at REAL)")
        con.execute(_JOBS_TABLE % {"name": "jobs_new"})
        con.execute("INSERT INTO jobs_new (%s) SELECT %s FROM jobs" % (_JOB_COLUMNS, _JOB_COLUMNS))
        _migration_step("copied")
        seq = con.execute("SELECT seq FROM sqlite_sequence WHERE name = 'jobs'").fetchone()
        con.execute("DROP TABLE jobs")
        con.execute("ALTER TABLE jobs_new RENAME TO jobs")
        if seq is not None:
            con.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'jobs'", (seq[0],))
        con.execute("COMMIT")
    except BaseException:
        try:
            con.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        con.isolation_level = ""


def _add_agent_columns(con):
    have = {r[1] for r in con.execute("PRAGMA table_info(agents)")}
    with con:
        for col in ("slurm_account", "facts_json"):
            if col not in have:
                con.execute("ALTER TABLE agents ADD COLUMN %s TEXT" % col)


def connect_state(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        _migrate_jobs(con)
        con.executescript(STATE_SCHEMA)
        _add_agent_columns(con)
    except BaseException:
        con.close()
        raise
    return con


def init_state(path):
    connect_state(path).close()


def instance_id(platform_path):
    """The random id of this platform, made once and kept in platform.db. The receiver names it in the header of
    every 401, so a program that probes a port can tell this platform from something else listening there."""
    con = connect_state(platform_path)
    try:
        with con:
            con.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('instance_id', ?)", (secrets.token_hex(16),))
        return con.execute("SELECT value FROM meta WHERE key = 'instance_id'").fetchone()[0]
    finally:
        con.close()


def open_readonly(path):
    """A read-only connection, or None when the file is not there. Reading never creates a database."""
    path = Path(path)
    if not path.exists():
        return None
    con = sqlite3.connect("%s?mode=ro" % path.resolve().as_uri(), uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def drop_index_files(path):
    """Delete the index file and its companions. Never touches the token file or the platform file."""
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            os.unlink(str(path) + suffix)
        except FileNotFoundError:
            pass


def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _migrate_tokens(con):
    """A token file made by feature 008 has no kind column: add the three columns, old tokens stay run tokens."""
    have = {r[1] for r in con.execute("PRAGMA table_info(tokens)")}
    with con:
        if "kind" not in have:
            con.execute("ALTER TABLE tokens ADD COLUMN kind TEXT NOT NULL DEFAULT 'run'")
        if "agent_name" not in have:
            con.execute("ALTER TABLE tokens ADD COLUMN agent_name TEXT")
        if "revoked_at" not in have:
            con.execute("ALTER TABLE tokens ADD COLUMN revoked_at REAL")
        if "run_name" not in have:
            con.execute("ALTER TABLE tokens ADD COLUMN run_name TEXT")
        if "expires_at" not in have:
            con.execute("ALTER TABLE tokens ADD COLUMN expires_at REAL")


def connect_tokens(path):
    con = connect(path, TOKEN_SCHEMA)
    _migrate_tokens(con)
    return con


def create_token(tokens_path, kind="run", agent_name=None, run_name=None):
    """Make a token, keep only its hash, and return the plain token once.

    With run_name the token is for that one run (the platform makes it when an agent claims a launch): it lives
    RUN_TOKEN_TTL seconds and can only create a run of that name.
    """
    if kind not in ("run", "agent"):
        raise ValueError("token kind must be run or agent")
    if (kind == "agent") != bool(agent_name):
        raise ValueError("an agent token is made for one agent name, and only an agent token has one")
    if run_name is not None and kind != "run":
        raise ValueError("only a run token is for a run name")
    token = "abf_" + secrets.token_urlsafe(32)
    now = time.time()
    con = connect_tokens(tokens_path)
    try:
        with con:
            con.execute("INSERT INTO tokens (token_hash, created_at, kind, agent_name, run_name, expires_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (_hash(token), now, kind, agent_name, run_name, now + RUN_TOKEN_TTL if run_name else None))
    finally:
        con.close()
    return token


def _now():
    """The wall clock plus ABF_PLATFORM_CLOCK_OFFSET seconds, the testing aid status.now() also honours."""
    return time.time() + float(os.environ.get("ABF_PLATFORM_CLOCK_OFFSET") or 0)


def lookup_token(tokens_path, token):
    """{'id', 'kind', 'agent_name', 'run_name'} of a token this platform issued and has neither revoked nor let
    expire, else None."""
    if not token or not Path(tokens_path).exists():
        return None
    con = connect_tokens(tokens_path)
    try:
        row = con.execute("SELECT id, kind, agent_name, run_name FROM tokens WHERE token_hash = ? AND revoked_at IS NULL "
                          "AND (expires_at IS NULL OR expires_at > ?)", (_hash(token), _now())).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def token_id(tokens_path, token):
    """Id of a run token, or None. An agent token is not a run token and never writes a run."""
    row = lookup_token(tokens_path, token)
    return row["id"] if row and row["kind"] == "run" else None


def revoke_token(tokens_path, token_id_):
    """Revoke one token by its id (not by its value); returns how many were live."""
    if not Path(tokens_path).exists():
        return 0
    con = connect_tokens(tokens_path)
    try:
        with con:
            return con.execute("UPDATE tokens SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                               (time.time(), token_id_)).rowcount
    finally:
        con.close()


def revoke_run_tokens(tokens_path, run_name):
    """Revoke every live token made for a run name; returns how many."""
    if not run_name or not Path(tokens_path).exists():
        return 0
    con = connect_tokens(tokens_path)
    try:
        with con:
            return con.execute("UPDATE tokens SET revoked_at = ? WHERE kind = 'run' AND run_name = ? AND revoked_at IS NULL",
                               (time.time(), run_name)).rowcount
    finally:
        con.close()


def revoke_agent_tokens(tokens_path, name):
    """Revoke every live token made for the agent name; returns how many."""
    if not Path(tokens_path).exists():
        return 0
    con = connect_tokens(tokens_path)
    try:
        with con:
            cur = con.execute("UPDATE tokens SET revoked_at = ? WHERE kind = 'agent' AND agent_name = ? "
                              "AND revoked_at IS NULL", (time.time(), name))
            return cur.rowcount
    finally:
        con.close()


def live_agent_names(tokens_path):
    """Names that have at least one live agent token."""
    if not Path(tokens_path).exists():
        return []
    con = connect_tokens(tokens_path)
    try:
        return [r[0] for r in con.execute("SELECT DISTINCT agent_name FROM tokens WHERE kind = 'agent' "
                                          "AND revoked_at IS NULL ORDER BY agent_name")]
    finally:
        con.close()
