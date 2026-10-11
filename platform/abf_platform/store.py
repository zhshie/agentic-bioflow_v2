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
    revoked_at REAL
);
"""

# Compute environments, agents and jobs. Nothing here describes a run: a job is a read-only question
# put to an agent, and the CHECK constraint lets only the two read-only kinds in.
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
    last_seen_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    compute_env TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('preflight', 'list_site_files')),
    args_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('queued', 'claimed', 'done', 'refused', 'error', 'expired')),
    result_json TEXT,
    late_result_json TEXT,
    created_at REAL NOT NULL,
    deadline_at REAL NOT NULL,
    claimed_at REAL,
    finished_at REAL
);
"""


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


def connect_state(path):
    return connect(path, STATE_SCHEMA)


def init_state(path):
    connect_state(path).close()


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


def connect_tokens(path):
    con = connect(path, TOKEN_SCHEMA)
    _migrate_tokens(con)
    return con


def create_token(tokens_path, kind="run", agent_name=None):
    """Make a token, keep only its hash, and return the plain token once."""
    if kind not in ("run", "agent"):
        raise ValueError("token kind must be run or agent")
    if (kind == "agent") != bool(agent_name):
        raise ValueError("an agent token is made for one agent name, and only an agent token has one")
    token = "abf_" + secrets.token_urlsafe(32)
    con = connect_tokens(tokens_path)
    try:
        with con:
            con.execute("INSERT INTO tokens (token_hash, created_at, kind, agent_name) VALUES (?, ?, ?, ?)",
                        (_hash(token), time.time(), kind, agent_name))
    finally:
        con.close()
    return token


def lookup_token(tokens_path, token):
    """{'id', 'kind', 'agent_name'} of a token this platform issued and has not revoked, else None."""
    if not token or not Path(tokens_path).exists():
        return None
    con = connect_tokens(tokens_path)
    try:
        row = con.execute("SELECT id, kind, agent_name FROM tokens WHERE token_hash = ? AND revoked_at IS NULL",
                          (_hash(token),)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def token_id(tokens_path, token):
    """Id of a run token, or None. An agent token is not a run token and never writes a run."""
    row = lookup_token(tokens_path, token)
    return row["id"] if row and row["kind"] == "run" else None


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
