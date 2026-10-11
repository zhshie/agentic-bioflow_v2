# Not nf-shard: it keeps runs in Postgres through Prisma and accepts any token; this is two small SQLite files, the index and the token list.
"""The two files the platform keeps.

index.db   the run index. It is an index, not the truth: `rebuild` drops it and builds it
           again from Nextflow's own records.
tokens.db  the accepted tokens, as hashes. `rebuild` never opens it.
"""
import hashlib
import os
import secrets
import sqlite3
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

TOKEN_SCHEMA = """
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL
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


def drop_index_files(path):
    """Delete the index file and its companions. Never touches the token file."""
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            os.unlink(str(path) + suffix)
        except FileNotFoundError:
            pass


def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token(tokens_path):
    """Make a token, keep only its hash, and return the plain token once."""
    token = "abf_" + secrets.token_urlsafe(32)
    import time
    con = connect(tokens_path, TOKEN_SCHEMA)
    try:
        with con:
            con.execute("INSERT INTO tokens (token_hash, created_at) VALUES (?, ?)", (_hash(token), time.time()))
    finally:
        con.close()
    return token


def token_id(tokens_path, token):
    """Id of the token, or None when the platform did not issue it."""
    if not token or not Path(tokens_path).exists():
        return None
    con = connect(tokens_path, TOKEN_SCHEMA)
    try:
        row = con.execute("SELECT id FROM tokens WHERE token_hash = ?", (_hash(token),)).fetchone()
        return row["id"] if row else None
    finally:
        con.close()
