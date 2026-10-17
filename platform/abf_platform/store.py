# Not nf-shard: it keeps runs in Postgres through Prisma and accepts any token; this is three small SQLite files, the index, the token list and the agent and compute-environment state.
"""The three files the platform keeps.

index.db     the run index. It is an index, not the truth: `rebuild` drops it and builds it
             again from Nextflow's own records.
tokens.db    the accepted tokens, as hashes (run tokens and agent tokens). `rebuild` never opens it.
platform.db  compute environments, agents and the queue of read-only jobs. `rebuild` never opens it.
"""
import base64
import hashlib
import hmac
import json
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
    failure_reason TEXT,
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

# kind is 'run' (a Nextflow run writes with it), 'agent' (an agent polls with it) or 'pat' (a person's personal access
# token for the MCP server, spec 009d: it has a user_id and opens no other door; users are in the table below).
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
    expires_at REAL,
    ended_at REAL,
    user_id INTEGER,
    label TEXT
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    lab TEXT NOT NULL,
    created_at REAL NOT NULL,
    disabled_at REAL,
    password_hash TEXT
);
CREATE TABLE IF NOT EXISTS web_sessions (
    id_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
"""

# The web password (spec 009c): users.password_hash holds only a scrypt hash with its own salt, written by `abf-platform user passwd`
# on a real terminal and by nothing else; web_sessions holds only the sha256 of a browser login's random id, which lives
# WEB_SESSION_SECONDS. The password never opens the MCP server, and a personal access token never opens the web.
WEB_SESSION_SECONDS = 12 * 3600
MIN_PASSWORD_CHARS = 8
MAX_PASSWORD_CHARS = 1000      # `user passwd` and the login page both stop here; nothing is cut down silently
SCRYPT = (2 ** 14, 8, 1)

# Nextflow can send one more message for a run after its `complete` (an aborted run runs onFlowComplete twice, so a second
# `complete` follows). The token is marked revoked at the complete (revoked_at) and also ended (ended_at); for
# ENDED_GRACE_SECONDS after that it is accepted for ONE thing only: a message for its own, already completed run, which
# the receiver answers OK without writing anything. Every other revoke (revoke_token, revoke_run_tokens, ...) clears
# ended_at, so it ends the token at once.
ENDED_GRACE_SECONDS = 300

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
    used_at REAL,
    caller_user_id INTEGER,
    state TEXT NOT NULL DEFAULT 'confirmed' CHECK (state IN ('pending', 'confirmed', 'void')),
    channel TEXT,
    confirmed_at REAL,
    expires_at REAL,
    ce_name TEXT,
    bundle_json TEXT,
    screen_text TEXT,
    void_reason TEXT
);
%(jobs)s
%(launches)s;
CREATE INDEX IF NOT EXISTS launches_run_name ON launches (run_name);
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
# One row per launch that was confirmed. A run name may have several rows (a launch the agent refused leaves its row, and
# the name can be used again), so run_name is not unique; job_id is the launch job that this very row made, which is how
# a row finds its own answer. The table has the same columns in the same order whether it was made new or upgraded.
_LAUNCHES_TABLE = """CREATE TABLE %(name)s (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_name TEXT NOT NULL,
    slurm_job_id INTEGER,
    run_folder TEXT NOT NULL,
    ce TEXT NOT NULL,
    agent TEXT NOT NULL,
    confirmed_at REAL NOT NULL,
    submitted_at REAL,
    cancel_requested_at REAL,
    job_id INTEGER
)"""
_LAUNCH_COLUMNS = "id, run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, cancel_requested_at"
STATE_SCHEMA = STATE_SCHEMA % {"jobs": (_JOBS_TABLE % {"name": "IF NOT EXISTS jobs"}) + ";",
                               "launches": _LAUNCHES_TABLE % {"name": "IF NOT EXISTS launches"}}
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


def uploads_root(platform_path=None, env=None):
    """The platform setting `uploads_root`: ABF_PLATFORM_UPLOADS, else `uploads` next to platform.db. Over MCP/HTTP a samplesheet
    must be a file inside <uploads_root>/<the caller's name>/."""
    env = os.environ if env is None else env
    if env.get("ABF_PLATFORM_UPLOADS"):
        return Path(env["ABF_PLATFORM_UPLOADS"])
    return Path(platform_path or default_platform_path(None, env)).parent / "uploads"


def connect(path, schema):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(schema)
    return con


REASON_MAX_CHARS = 1000   # Nextflow cuts workflow.errorMessage at 255 itself; the bound only stops a hostile sender


def _migrate_index(con):
    """An index.db made before follow-up 3 has no failure_reason column: add it; every row stays, its reason is NULL."""
    if "failure_reason" not in {r[1] for r in con.execute("PRAGMA table_info(runs)")}:
        try:
            with con:
                con.execute("ALTER TABLE runs ADD COLUMN failure_reason TEXT")
        except sqlite3.OperationalError:
            if "failure_reason" not in {r[1] for r in con.execute("PRAGMA table_info(runs)")}:
                raise   # a second process may have added it first; anything else is a real error


def connect_index(path):
    con = connect(path, SCHEMA)
    _migrate_index(con)
    return con


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


def _launch_job_ids(con, launches):
    """For each old launches row (id, run_name, confirmed_at), the id of the launch job it made, or None.

    The platform wrote a row and its job in one transaction with one clock reading, so the job whose created_at equals the
    row's confirmed_at and whose content names the same run is the row's own; failing that, the newest job of that run
    that no other row has taken (the old table had one row per name, and the old code kept the last job of the name).
    """
    jobs_of = {}
    for j in con.execute("SELECT id, args_json, created_at FROM jobs WHERE kind = 'launch_nextflow' ORDER BY id"):
        try:
            name = json.loads(j[1]).get("bundle", {}).get("run_name")
        except (ValueError, AttributeError):
            continue
        jobs_of.setdefault(name, []).append((j[0], j[2]))
    taken, out = set(), {}
    for rid, name, confirmed in launches:
        cands = [(i, t) for i, t in jobs_of.get(name, []) if i not in taken]
        exact = [i for i, t in cands if t == confirmed]
        pick = exact[-1] if exact else (cands[-1][0] if cands else None)
        if pick is not None:
            taken.add(pick)
        out[rid] = pick
    return out


def _launches_need_upgrade(con):
    cols = [r[1] for r in con.execute("PRAGMA table_info(launches)")]
    return bool(cols) and "job_id" not in cols


def _migrate_launches(con):
    """A platform.db made before the follow-up has a launches table with run_name UNIQUE and no job_id.

    Same shape of work as _migrate_jobs: one transaction, build the new table, copy every row (the ids and the
    AUTOINCREMENT counter too), give each row the job it made, drop the old table, rename. Any failure rolls it all back.
    """
    if not _launches_need_upgrade(con):
        return
    con.isolation_level = None
    con.execute("BEGIN IMMEDIATE")
    try:
        if not _launches_need_upgrade(con):     # another process did it first
            con.execute("COMMIT")
            return
        con.execute(_LAUNCHES_TABLE % {"name": "launches_new"})
        con.execute("INSERT INTO launches_new (%s) SELECT %s FROM launches" % (_LAUNCH_COLUMNS, _LAUNCH_COLUMNS))
        ids = _launch_job_ids(con, con.execute("SELECT id, run_name, confirmed_at FROM launches ORDER BY id").fetchall())
        for rid, jid in ids.items():
            con.execute("UPDATE launches_new SET job_id = ? WHERE id = ?", (jid, rid))
        _migration_step("copied")
        seq = con.execute("SELECT seq FROM sqlite_sequence WHERE name = 'launches'").fetchone()
        con.execute("DROP TABLE launches")
        con.execute("ALTER TABLE launches_new RENAME TO launches")
        if seq is not None:
            con.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'launches'", (seq[0],))
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


def _add_confirmation_column(con):
    """A platform.db made before 009d has no caller_user_id on its confirmations: add it, old rows keep NULL."""
    if "caller_user_id" not in {r[1] for r in con.execute("PRAGMA table_info(confirmations)")}:
        with con:
            con.execute("ALTER TABLE confirmations ADD COLUMN caller_user_id INTEGER")


_CONFIRMATION_COLUMNS = (
    ("state", "TEXT NOT NULL DEFAULT 'confirmed' CHECK (state IN ('pending', 'confirmed', 'void'))"),
    ("channel", "TEXT"), ("confirmed_at", "REAL"), ("expires_at", "REAL"), ("ce_name", "TEXT"), ("bundle_json", "TEXT"),
    ("screen_text", "TEXT"), ("void_reason", "TEXT"))


def _add_confirmation_state(con):
    """A platform.db made before 009c has confirmations that are all a person's yes at a terminal: add the columns of the pending
    request, and mark every old row confirmed through TERMINAL, at the time it was made."""
    if "state" in {r[1] for r in con.execute("PRAGMA table_info(confirmations)")}:
        return
    try:
        with con:
            for name, decl in _CONFIRMATION_COLUMNS:
                con.execute("ALTER TABLE confirmations ADD COLUMN %s %s" % (name, decl))
            con.execute("UPDATE confirmations SET channel = 'TERMINAL', confirmed_at = created_at")
    except sqlite3.OperationalError:
        if "state" not in {r[1] for r in con.execute("PRAGMA table_info(confirmations)")}:
            raise    # a second process may have added them first; anything else is a real error


def connect_state(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        _migrate_jobs(con)
        _migrate_launches(con)
        con.executescript(STATE_SCHEMA)
        _add_agent_columns(con)
        _add_confirmation_column(con)
        _add_confirmation_state(con)
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
        if "ended_at" not in have:
            con.execute("ALTER TABLE tokens ADD COLUMN ended_at REAL")
        if "user_id" not in have:
            con.execute("ALTER TABLE tokens ADD COLUMN user_id INTEGER")
        if "label" not in have:
            con.execute("ALTER TABLE tokens ADD COLUMN label TEXT")
    if "password_hash" not in {r[1] for r in con.execute("PRAGMA table_info(users)")}:
        try:
            with con:
                con.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        except sqlite3.OperationalError:
            if "password_hash" not in {r[1] for r in con.execute("PRAGMA table_info(users)")}:
                raise


def connect_tokens(path):
    con = connect(path, TOKEN_SCHEMA)
    _migrate_tokens(con)
    return con


def create_token(tokens_path, kind="run", agent_name=None, run_name=None, user_id=None, label=None):
    """Make a token, keep only its hash, and return the plain token once.

    With run_name the token is for that one run (the platform makes it when an agent claims a launch): it lives
    RUN_TOKEN_TTL seconds and can only create a run of that name. A 'pat' is for one user (user_id), never expires and
    starts with abf_pat_.
    """
    if kind not in ("run", "agent", "pat"):
        raise ValueError("token kind must be run, agent or pat")
    if (kind == "agent") != bool(agent_name):
        raise ValueError("an agent token is made for one agent name, and only an agent token has one")
    if run_name is not None and kind != "run":
        raise ValueError("only a run token is for a run name")
    if (kind == "pat") != (user_id is not None):
        raise ValueError("a personal access token is made for one user, and only it has a user")
    if label is not None and kind != "pat":
        raise ValueError("only a personal access token has a label")
    token = ("abf_pat_" if kind == "pat" else "abf_") + secrets.token_urlsafe(32)
    now = time.time()
    con = connect_tokens(tokens_path)
    try:
        with con:
            con.execute("INSERT INTO tokens (token_hash, created_at, kind, agent_name, run_name, expires_at, user_id, label) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (_hash(token), now, kind, agent_name, run_name, now + RUN_TOKEN_TTL if run_name else None,
                         user_id, label))
    finally:
        con.close()
    return token


def create_user(tokens_path, name, lab):
    """Add a user and return the id; ValueError when the name is taken (the name is unique)."""
    con = connect_tokens(tokens_path)
    try:
        with con:
            try:
                return con.execute("INSERT INTO users (name, lab, created_at) VALUES (?, ?, ?)",
                                   (name, lab, time.time())).lastrowid
            except sqlite3.IntegrityError:
                raise ValueError("a user named %s exists" % name)
    finally:
        con.close()


def user_id_of(tokens_path, name):
    if not Path(tokens_path).exists():
        return None
    con = connect_tokens(tokens_path)
    try:
        row = con.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
        return row[0] if row else None
    finally:
        con.close()


def has_users(tokens_path):
    if not Path(tokens_path).exists():
        return False
    con = connect_tokens(tokens_path)
    try:
        return con.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0
    finally:
        con.close()


def lookup_pat(tokens_path, token):
    """{'user_id', 'name', 'lab', 'token_id'} of a live personal access token of an enabled user, else None."""
    if not token or not isinstance(token, str) or not Path(tokens_path).exists():
        return None
    con = connect_tokens(tokens_path)
    try:
        row = con.execute("SELECT u.id AS user_id, u.name AS name, u.lab AS lab, t.id AS token_id FROM tokens t "
                          "JOIN users u ON u.id = t.user_id WHERE t.token_hash = ? AND t.kind = 'pat' "
                          "AND t.revoked_at IS NULL AND u.disabled_at IS NULL", (_hash(token),)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def list_pats(tokens_path):
    """One dict per personal access token: id, user, label, created_at, revoked_at. Never the value or the hash."""
    if not Path(tokens_path).exists():
        return []
    con = connect_tokens(tokens_path)
    try:
        return [dict(r) for r in con.execute(
            "SELECT t.id AS id, u.name AS user, t.label AS label, t.created_at AS created_at, t.revoked_at AS revoked_at "
            "FROM tokens t JOIN users u ON u.id = t.user_id WHERE t.kind = 'pat' ORDER BY t.id")]
    finally:
        con.close()


def revoke_pat(tokens_path, token_id_):
    """Revoke one personal access token by id; returns how many were live (0 for an id that is not a PAT)."""
    if not Path(tokens_path).exists():
        return 0
    con = connect_tokens(tokens_path)
    try:
        with con:
            return con.execute("UPDATE tokens SET revoked_at = ? WHERE id = ? AND kind = 'pat' AND revoked_at IS NULL",
                               (time.time(), token_id_)).rowcount
    finally:
        con.close()


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


def lookup_ended_token(tokens_path, token):
    """{'id', 'kind', 'agent_name', 'run_name'} of a run token that a `complete` ended less than ENDED_GRACE_SECONDS ago
    (and that has not expired and was not revoked by anything else), else None. It is good for nothing but the no-op
    answer to a message for its own completed run."""
    if not token or not Path(tokens_path).exists():
        return None
    now = _now()
    con = connect_tokens(tokens_path)
    try:
        row = con.execute("SELECT id, kind, agent_name, run_name FROM tokens WHERE token_hash = ? AND kind = 'run' "
                          "AND run_name IS NOT NULL AND revoked_at IS NOT NULL AND ended_at IS NOT NULL "
                          "AND ? < ended_at + ? AND (expires_at IS NULL OR expires_at > ?)",
                          (_hash(token), now, ENDED_GRACE_SECONDS, now)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def token_id(tokens_path, token):
    """Id of a run token, or None. An agent token is not a run token and never writes a run."""
    row = lookup_token(tokens_path, token)
    return row["id"] if row and row["kind"] == "run" else None


def end_token(tokens_path, token_id_):
    """The token of a run that has completed: revoked now, and ended (the short door of ENDED_GRACE_SECONDS, see above)."""
    if not Path(tokens_path).exists():
        return 0
    con = connect_tokens(tokens_path)
    try:
        with con:
            now = time.time()
            return con.execute("UPDATE tokens SET revoked_at = ?, ended_at = ? WHERE id = ? AND revoked_at IS NULL",
                               (now, now, token_id_)).rowcount
    finally:
        con.close()


def revoke_token(tokens_path, token_id_):
    """Revoke one token by its id (not by its value); returns how many were live. Also closes the door of an ended token."""
    if not Path(tokens_path).exists():
        return 0
    con = connect_tokens(tokens_path)
    try:
        with con:
            con.execute("UPDATE tokens SET ended_at = NULL WHERE id = ?", (token_id_,))
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
            con.execute("UPDATE tokens SET ended_at = NULL WHERE kind = 'run' AND run_name = ?", (run_name,))
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


# ---- the web password and the browser login (spec 009c) ------------------------------------------------------------------

def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _scrypt(password, salt, n, r, p):
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32, maxmem=128 * n * r * 2 + 4 * 1024 * 1024)


def hash_password(password):
    """scrypt$N$r$p$salt$hash: a slow hash with a salt of its own; the password itself is kept nowhere."""
    n, r, p = SCRYPT
    salt = os.urandom(16)
    return "scrypt$%d$%d$%d$%s$%s" % (n, r, p, _b64(salt), _b64(_scrypt(password, salt, n, r, p)))


def password_matches(stored, password):
    try:
        kind, n, r, p, salt, digest = stored.split("$")
        if kind != "scrypt":
            return False
        return hmac.compare_digest(_scrypt(password, _unb64(salt), int(n), int(r), int(p)), _unb64(digest))
    except (ValueError, AttributeError, TypeError):
        return False


def set_web_password(tokens_path, name, password):
    """Set (or replace) a user's web password; every browser login of that user ends in the same transaction.
    ValueError for an unknown user or a password that is too short. The caller is the terminal command: nothing else may call it."""
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_CHARS:
        raise ValueError("the password must be at least %d characters (密碼至少 %d 個字元)" % (MIN_PASSWORD_CHARS, MIN_PASSWORD_CHARS))
    if len(password) > MAX_PASSWORD_CHARS:
        raise ValueError("the password must be at most %d characters (密碼最多 %d 個字元)" % (MAX_PASSWORD_CHARS, MAX_PASSWORD_CHARS))
    stored = hash_password(password)
    con = connect_tokens(tokens_path)
    try:
        with con:
            row = con.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
            if row is None:
                raise ValueError("no such user: %s (沒有這個使用者)" % name)
            con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (stored, row["id"]))
            con.execute("DELETE FROM web_sessions WHERE user_id = ?", (row["id"],))
    finally:
        con.close()


def check_web_password(tokens_path, name, password):
    """{'user_id', 'name', 'lab'} when the name and the web password are right and the user is not disabled, else None. A user who
    has no web password never passes, and every refusal costs the same hashing time."""
    dummy = "scrypt$%d$%d$%d$%s$%s" % (SCRYPT[0], SCRYPT[1], SCRYPT[2], _b64(b"\0" * 16), _b64(b"\0" * 32))
    row = None
    if isinstance(name, str) and isinstance(password, str) and name and Path(tokens_path).exists():
        con = connect_tokens(tokens_path)
        try:
            row = con.execute("SELECT id, name, lab, disabled_at, password_hash FROM users WHERE name = ?", (name,)).fetchone()
        finally:
            con.close()
    stored = row["password_hash"] if row is not None and row["password_hash"] else dummy
    ok = password_matches(stored, password if isinstance(password, str) else "")
    if row is None or not row["password_hash"] or not ok or row["disabled_at"] is not None:
        return None
    return {"user_id": row["id"], "name": row["name"], "lab": row["lab"]}


def create_web_session(tokens_path, user_id, now):
    """A browser login: returns the random id (shown once, kept only as a hash) and when it ends."""
    sid = secrets.token_urlsafe(32)
    con = connect_tokens(tokens_path)
    try:
        with con:
            con.execute("DELETE FROM web_sessions WHERE expires_at <= ?", (now,))
            con.execute("INSERT INTO web_sessions (id_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                        (_hash(sid), user_id, now, now + WEB_SESSION_SECONDS))
    finally:
        con.close()
    return sid, now + WEB_SESSION_SECONDS


def web_session_user(tokens_path, sid, now):
    """{'user_id', 'name', 'lab'} of a live browser login of a user who is not disabled, else None."""
    if not sid or not isinstance(sid, str) or not Path(tokens_path).exists():
        return None
    con = connect_tokens(tokens_path)
    try:
        row = con.execute("SELECT u.id AS user_id, u.name AS name, u.lab AS lab FROM web_sessions s JOIN users u ON u.id = s.user_id "
                          "WHERE s.id_hash = ? AND s.expires_at > ? AND u.disabled_at IS NULL", (_hash(sid), now)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def end_web_session(tokens_path, sid):
    if not sid or not Path(tokens_path).exists():
        return 0
    con = connect_tokens(tokens_path)
    try:
        with con:
            return con.execute("DELETE FROM web_sessions WHERE id_hash = ?", (_hash(sid),)).rowcount
    finally:
        con.close()


# ---- small facts the processes share through platform.db ------------------------------------------------------------------

def set_meta(state_path, key, value):
    con = connect_state(state_path)
    try:
        with con:
            con.execute("INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
    finally:
        con.close()


def get_meta(state_path, key):
    con = open_readonly(state_path)
    if con is None:
        return None
    try:
        row = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None
    finally:
        con.close()
