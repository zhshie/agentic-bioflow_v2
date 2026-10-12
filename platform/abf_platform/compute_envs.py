# Not Seqera Platform's compute environments: they live in Seqera's service; this keeps the same model (type, config, credential name) in a small local SQLite table.
"""Compute environments in the Seqera model: a type, a config, and the NAME of a credential.

Slurm is the only type that can be checked and used. The other 13 types Seqera lists are stored
(their settings, nothing more) with the status `unsupported`: no code runs for them, no cloud
library is imported, and the check and listing refuse them at once. Nothing here holds a
credential: a value that looks like one is refused, and only the credential's name is kept.
"""
import json
import re
import sqlite3
import time

from . import common, store

# platform value (docs.seqera.io, "Available platform values") -> label. the feature's research notes (research.md).
KINDS = {
    "slurm-platform": "Slurm",
    "altair-platform": "PBS Pro",
    "lsf-platform": "IBM Spectrum LSF",
    "uge-platform": "Grid Engine",
    "moab-platform": "Moab",
    "awsbatch-platform": "AWS Batch",
    "awscloud-platform": "AWS Cloud",
    "azbatch-platform": "Azure Batch",
    "azcloud-platform": "Azure Cloud",
    "googlebatch-platform": "Google Cloud Batch",
    "googlecloud-platform": "Google Cloud",
    "k8s-platform": "Kubernetes",
    "eks-platform": "Amazon EKS",
    "gke-platform": "Google GKE",
}
SUPPORTED = "slurm-platform"
SEQERA_COMPUTE = ("seqera-compute", "seqeracompute-platform")

CREATING, AVAILABLE, INVALID, UNSUPPORTED, DISABLED = "creating", "available", "invalid", "unsupported", "disabled"

NOT_SUPPORTED_MESSAGE = ("Not supported yet (尚未支援): a real account is needed to test this type before it can run "
                         "anything (需要一個真的帳號實測). Only its settings are stored.")
CREDENTIAL_ADVICE = ("looks like a credential (像憑證). The platform keeps only the NAME of a credential; keep the "
                     "credential itself on the agent side (憑證要放在代理那邊，平台只記名字).")


class CEError(Exception):
    """A request the platform refuses; the text says why and never repeats a rejected value."""


# ---- rules shared by the fields ----------------------------------------------------------

_NAME = re.compile(r"^[A-Za-z0-9_.-]+\Z")
_QUEUE = re.compile(r"^[A-Za-z0-9_.-]+\Z")
_PATH_CHARS = re.compile(r"^[A-Za-z0-9_./@+=:,-]+\Z")
_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}\Z")
_USER = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\Z")
_CRED_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,99}\Z")
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}\Z")
MAX_PATH = 1024


def path_problem(value):
    """None when value is a plain absolute path; else a short code: type, empty, long, chars, dotdot, relative."""
    if not isinstance(value, str):
        return "type"
    if not value:
        return "empty"
    if len(value) > MAX_PATH:
        return "long"
    if not _PATH_CHARS.match(value):
        return "chars"
    if ".." in value.split("/"):
        return "dotdot"
    if not value.startswith("/"):
        return "relative"
    return None


def path_message(label, problem):
    return {
        "type": "%s must be text" % label,
        "empty": "%s is empty" % label,
        "long": "%s is longer than %d characters" % (label, MAX_PATH),
        "chars": "%s contains characters that are not allowed (含不允許的字元); use letters, digits and _ . / @ + = : , - only" % label,
        "dotdot": "%s contains '..' (含 ..), which is not allowed" % label,
        "relative": "%s must be an absolute path starting with / (a relative path is outside the allowed read roots, "
                    "在允許範圍之外)" % label,
    }[problem]


def normalize_path(value):
    """The path without a trailing slash or repeated slashes. Call it only on a path that has no problem."""
    parts = [p for p in value.split("/") if p and p != "."]
    return "/" + "/".join(parts)


# ---- credentials: refused by shape and by name -------------------------------------------------

_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"aws_secret_access_key\s*[=:]", re.I),
    re.compile(r"abf_[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bexport\s+[A-Za-z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|KEY)[A-Za-z0-9_]*\s*=", re.I),
    re.compile(r"\b(?:password|passwd|secret|api[_-]?key|access[_-]?key|secret[_-]?key|token)\w*\s*[=:]\s*\S", re.I),
]


def looks_like_credential(text):
    return any(p.search(text) for p in _VALUE_PATTERNS)


def credential_findings(obj, where):
    """Field paths (never values) in obj that name a secret or hold something shaped like one."""
    found = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = "%s.%s" % (where, key)
            if common.is_secret_name(key):
                found.append(here)
            else:
                found += credential_findings(value, here)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            if isinstance(value, dict) and "name" in value and "value" in value and common.is_secret_name(value["name"]):
                found.append("%s[%d].name" % (where, i))
            else:
                found += credential_findings(value, "%s[%d]" % (where, i))
    elif isinstance(obj, str):
        if looks_like_credential(obj):
            found.append(where)
    return found


# ---- validation --------------------------------------------------------------------------------

_COMMON_CONFIG = ("workDir", "preRunScript", "postRunScript", "environment", "nextflowConfig")
_SLURM_CONFIG = _COMMON_CONFIG + ("launchDir", "headQueue", "computeQueue", "maxQueueSize", "headJobOptions",
                                  "hostName", "userName", "port", "readRoots")


def _text(config, key, limit):
    v = config.get(key)
    if v is None:
        return
    if not isinstance(v, str):
        raise CEError("%s must be text" % key)
    if len(v) > limit:
        raise CEError("%s is longer than %d characters" % (key, limit))


def _check_environment(config):
    env = config.get("environment")
    if env is None:
        return
    if not isinstance(env, list) or len(env) > 200:
        raise CEError("environment must be a list of {name, value, head, compute}")
    clean = []
    for i, e in enumerate(env):
        if not isinstance(e, dict) or set(e) - {"name", "value", "head", "compute"}:
            raise CEError("environment[%d] must have only name, value, head and compute" % i)
        name, value = e.get("name"), e.get("value", "")
        if not isinstance(name, str) or not _ENV_NAME.match(name):
            raise CEError("environment[%d].name must be a variable name" % i)
        if not isinstance(value, str) or len(value) > 2000:
            raise CEError("environment[%d].value must be text of at most 2000 characters" % i)
        clean.append({"name": name, "value": value, "head": bool(e.get("head", True)),
                      "compute": bool(e.get("compute", False))})
    config["environment"] = clean


def _check_slurm(config):
    unknown = sorted(set(config) - set(_SLURM_CONFIG))
    if unknown:
        raise CEError("unknown setting for a Slurm environment: %s (known: %s)" % (unknown[0], ", ".join(_SLURM_CONFIG)))
    wd = config.get("workDir")
    if wd is None or wd == "":
        raise CEError("workDir is required for a Slurm environment (缺工作資料夾 workDir)")
    p = path_problem(wd)
    if p:
        raise CEError(path_message("workDir", p))
    config["workDir"] = normalize_path(wd)
    if config.get("launchDir") is not None:
        p = path_problem(config["launchDir"])
        if p:
            raise CEError(path_message("launchDir", p))
        config["launchDir"] = normalize_path(config["launchDir"])
    roots = config.get("readRoots")
    if roots is not None:
        if not isinstance(roots, list) or len(roots) > 50:
            raise CEError("readRoots must be a list of absolute paths")
        clean = []
        for r in roots:
            p = path_problem(r)
            if p:
                raise CEError(path_message("readRoots", p))
            clean.append(normalize_path(r))
        config["readRoots"] = clean
    hq = config.get("headQueue")
    if hq is None or hq == "":
        raise CEError("headQueue is required for a Slurm environment (缺主控佇列 headQueue)")
    for key in ("headQueue", "computeQueue"):
        v = config.get(key)
        if v is not None and (not isinstance(v, str) or not _QUEUE.match(v) or ".." in v):
            raise CEError("%s is not a valid queue name: letters, digits, _ . - only (佇列名稱不合法)" % key)
    if config.get("maxQueueSize") is not None:
        v = config["maxQueueSize"]
        if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 100000:
            raise CEError("maxQueueSize must be a whole number from 1 to 100000")
    if config.get("port") is not None:
        v = config["port"]
        if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 65535:
            raise CEError("port must be a whole number from 1 to 65535")
    if config.get("hostName") is not None and (not isinstance(config["hostName"], str) or not _HOST.match(config["hostName"])):
        raise CEError("hostName is not a valid host name")
    if config.get("userName") is not None and (not isinstance(config["userName"], str) or not _USER.match(config["userName"])):
        raise CEError("userName is not a valid user name")
    _text(config, "headJobOptions", 1000)


def _check_other(config):
    """A type that is only modelled: no field schema, only the common checks."""
    for key, value in config.items():
        if not isinstance(key, str) or not key or len(key) > 100:
            raise CEError("a setting name must be 1 to 100 characters")
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            raise CEError("setting %s cannot be stored" % key)
    if len(json.dumps(config)) > 100000:
        raise CEError("the settings are too large")


def clean(fields):
    """Validate a whole record; returns {'name', 'description', 'platform', 'credentials_id', 'agent', 'config'}."""
    name = fields.get("name")
    if not isinstance(name, str) or not 1 <= len(name) <= 100:
        raise CEError("the name must be 1 to 100 characters (名字長度 1 到 100)")
    if not _NAME.match(name):
        raise CEError("the name may use letters, digits, _ . - only")
    platform = fields.get("platform")
    if platform in SEQERA_COMPUTE:
        raise CEError("Seqera Compute is Seqera's own hosted service and has no counterpart here (沒有對應), so it is "
                      "not a type you can create. Types: %s" % ", ".join(KINDS))
    if platform not in KINDS:
        raise CEError("unknown type %r. Types: %s" % (str(platform)[:60], ", ".join(KINDS)))
    desc = fields.get("description")
    if desc is not None and (not isinstance(desc, str) or len(desc) > 1000):
        raise CEError("description must be text of at most 1000 characters")
    cred = fields.get("credentialsId")
    if cred is not None and (not isinstance(cred, str) or not _CRED_NAME.match(cred)):
        raise CEError("credentialsId is the NAME of a credential (letters, digits, _ . : @ -), never the credential itself")
    agent = fields.get("agent")
    if agent is not None and (not isinstance(agent, str) or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z", agent)):
        raise CEError("agent must be an agent name (letters, digits, _ . -)")
    config = fields.get("config")
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise CEError("config must be an object")
    config = json.loads(json.dumps(config))
    # first of all, before any rule that could repeat a value in its message
    bad = [b.lstrip(".") for b in credential_findings({"description": desc, "credentialsId": cred, "config": config}, "")]
    if bad:
        raise CEError("%s %s" % (bad[0], CREDENTIAL_ADVICE))
    for key in ("preRunScript", "postRunScript", "nextflowConfig"):
        _text(config, key, 20000)
    if config.get("workDir") is not None and not isinstance(config.get("workDir"), str):
        raise CEError("workDir must be text")
    _check_environment(config)
    if platform == SUPPORTED:
        _check_slurm(config)
    else:
        _check_other(config)
    return {"name": name, "description": desc, "platform": platform, "credentials_id": cred, "agent": agent,
            "config": config}


# ---- storage -------------------------------------------------------------------------------------

def view(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "platform": row["platform"],
        "credentialsId": row["credentials_id"],
        "agent": row["agent"],
        "status": row["status"],
        "message": row["message"],
        "primary": bool(row["is_primary"]),
        "dateCreated": common.epoch_iso_ms(row["created_at"]),
        "lastUpdated": common.epoch_iso_ms(row["updated_at"]),
        "lastUsed": common.epoch_iso_ms(row["last_used_at"]),
        "config": json.loads(row["config_json"]),
    }


def get(state_path, name):
    """The environment as a dict, or None. Opens the file read-only."""
    con = store.open_readonly(state_path)
    if con is None:
        return None
    try:
        row = con.execute("SELECT * FROM compute_envs WHERE name = ?", (name,)).fetchone()
        return view(row) if row else None
    finally:
        con.close()


def list_all(state_path):
    con = store.open_readonly(state_path)
    if con is None:
        return []
    try:
        return [view(r) for r in con.execute("SELECT * FROM compute_envs ORDER BY id")]
    finally:
        con.close()


def _row(con, name):
    row = con.execute("SELECT * FROM compute_envs WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise CEError("compute environment %r not found (找不到)" % name[:100])
    return row


def create(state_path, fields, clock=time.time):
    rec = clean(fields)
    supported = rec["platform"] == SUPPORTED
    status = CREATING if supported else UNSUPPORTED
    message = ("waiting for the first preflight (等待第一次預檢)" if supported else NOT_SUPPORTED_MESSAGE)
    now = clock()
    con = store.connect_state(state_path)
    try:
        with con:
            try:
                con.execute(
                    "INSERT INTO compute_envs (name, description, platform, credentials_id, agent, status, message, "
                    "is_primary, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
                    (rec["name"], rec["description"], rec["platform"], rec["credentials_id"], rec["agent"], status,
                     message, json.dumps(rec["config"], sort_keys=True), now, now))
            except sqlite3.IntegrityError:
                raise CEError("a compute environment named %r already exists (名字重複)" % rec["name"])
        return view(_row(con, rec["name"]))
    finally:
        con.close()


def update(state_path, name, fields, clock=time.time):
    """Change the given top-level fields and config keys; the result must pass every rule again."""
    con = store.connect_state(state_path)
    try:
        with con:
            row = _row(con, name)
            cur = view(row)
            merged = {"name": cur["name"], "description": cur["description"], "platform": cur["platform"],
                      "credentialsId": cur["credentialsId"], "agent": cur["agent"], "config": dict(cur["config"])}
            for key in ("description", "credentialsId", "agent"):
                if key in fields:
                    merged[key] = fields[key]
            for key, value in (fields.get("config") or {}).items():
                merged["config"][key] = value
            rec = clean(merged)
            con.execute("UPDATE compute_envs SET description = ?, credentials_id = ?, agent = ?, config_json = ?, "
                        "updated_at = ? WHERE name = ?",
                        (rec["description"], rec["credentials_id"], rec["agent"],
                         json.dumps(rec["config"], sort_keys=True), clock(), name))
        return view(_row(con, name))
    finally:
        con.close()


def set_primary(state_path, name, clock=time.time):
    con = store.connect_state(state_path)
    try:
        with con:
            row = _row(con, name)
            if row["status"] == UNSUPPORTED:
                raise CEError("an unsupported environment cannot be primary (尚未支援的環境不能當主要): %s" % name)
            if row["status"] == DISABLED:
                raise CEError("a disabled environment cannot be primary (已停用的環境不能當主要): %s" % name)
            con.execute("UPDATE compute_envs SET is_primary = 0 WHERE is_primary = 1 AND name != ?", (name,))
            con.execute("UPDATE compute_envs SET is_primary = 1, updated_at = ? WHERE name = ?", (clock(), name))
        return view(_row(con, name))
    finally:
        con.close()


def disable(state_path, name, clock=time.time):
    con = store.connect_state(state_path)
    try:
        with con:
            _row(con, name)
            con.execute("UPDATE compute_envs SET status = ?, message = ?, is_primary = 0, updated_at = ? WHERE name = ?",
                        (DISABLED, "disabled (已停用): no new job is accepted", clock(), name))
        return view(_row(con, name))
    finally:
        con.close()


def enable(state_path, name, clock=time.time):
    con = store.connect_state(state_path)
    try:
        with con:
            row = _row(con, name)
            if row["status"] != DISABLED:
                raise CEError("%s is not disabled" % name)
            if row["checked_ok"] == 1:
                status, message = AVAILABLE, "enabled again; the last preflight had passed (重新啟用)"
            else:
                status, message = CREATING, "enabled again; waiting for a preflight (重新啟用，等待預檢)"
            con.execute("UPDATE compute_envs SET status = ?, message = ?, updated_at = ? WHERE name = ?",
                        (status, message, clock(), name))
        return view(_row(con, name))
    finally:
        con.close()


def set_message(state_path, name, message, only_status=None, clock=time.time):
    """Change the message only (the status stays). With only_status the message is written only while the
    environment still has that status, so a verdict that arrived in between is never overwritten."""
    con = store.connect_state(state_path)
    try:
        with con:
            sql = "UPDATE compute_envs SET message = ?, updated_at = ? WHERE name = ?"
            args = [message, clock(), name]
            if only_status:
                sql += " AND status = ?"
                args.append(only_status)
            con.execute(sql, args)
    finally:
        con.close()


def snapshot(row_or_view):
    """What an agent is told about an environment: only what a job needs, never anything else."""
    v = row_or_view if "config" in row_or_view else view(row_or_view)
    c = v["config"]
    return {"name": v["name"], "platform": v["platform"], "workDir": c.get("workDir"), "launchDir": c.get("launchDir"),
            "headQueue": c.get("headQueue"), "computeQueue": c.get("computeQueue"),
            "readRoots": list(c.get("readRoots") or [])}


def verdict_message(ok, checks):
    if ok:
        return "preflight passed (預檢通過): " + ", ".join(c["name"] for c in checks)
    bad = ["%s: %s" % (c["name"], c["detail"]) for c in checks if c["status"] != "pass"]
    return "preflight failed (預檢未通過): " + "; ".join(bad)


def apply_preflight(con, name, ok, checks, now):
    """Record an agent's verdict on the environment, inside the caller's transaction."""
    row = con.execute("SELECT status FROM compute_envs WHERE name = ?", (name,)).fetchone()
    if row is None or row["status"] in (DISABLED, UNSUPPORTED):
        return
    con.execute("UPDATE compute_envs SET status = ?, message = ?, checked_ok = ?, updated_at = ? WHERE name = ?",
                (AVAILABLE if ok else INVALID, verdict_message(ok, checks), 1 if ok else 0, now, name))
