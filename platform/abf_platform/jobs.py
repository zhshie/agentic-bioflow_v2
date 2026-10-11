# Not Celery or RQ: they need a separate broker process; two read-only job kinds in one SQLite table are enough, and the table is not a run state machine.
"""The queue of read-only jobs that agents poll for.

Only `preflight` and `list_site_files` exist (a CHECK constraint in platform.db says so). Every job is
a question put to one agent, with a deadline. A job whose deadline passed is `expired`: it is never
handed out, and an answer that arrives late is kept apart and changes nothing.

Who writes: the command line and the MCP server queue jobs; the receiver hands them out and takes the
answers. Nobody else writes platform.db, and `rebuild` never opens it.
"""
import asyncio
import json
import os
import time

from . import common, compute_envs, store

LIST_LIMIT = 500
PRUNE_AFTER_SECONDS = 7 * 86400
DEADLINE_SECONDS = {"preflight": 180, "list_site_files": 60}
_DEADLINE_ENV = {"preflight": "ABF_PLATFORM_DEADLINE_PREFLIGHT",
                 "list_site_files": "ABF_PLATFORM_DEADLINE_LIST_SITE_FILES"}
KINDS = tuple(DEADLINE_SECONDS)


class JobRefused(Exception):
    """The platform will not queue this job; the text says why."""


def deadline_seconds(kind):
    raw = os.environ.get(_DEADLINE_ENV[kind])
    try:
        value = float(raw) if raw else float(DEADLINE_SECONDS[kind])
    except ValueError:
        value = float(DEADLINE_SECONDS[kind])
    return value if value > 0 else float(DEADLINE_SECONDS[kind])


def check_listing_path(path):
    """The path to list, normalised, or JobRefused. Only its syntax is judged here; the agent also judges
    whether it lies inside the places it may read."""
    problem = compute_envs.path_problem(path)
    if problem:
        raise JobRefused(compute_envs.path_message("path", problem))
    return compute_envs.normalize_path(path)


def _enqueue(state_path, ce_name, kind, listing_path, clock, deadline, offline_after=None):
    if not isinstance(ce_name, str) or not ce_name:
        raise JobRefused("a compute environment name is required")
    if kind == "list_site_files":
        listing_path = check_listing_path(listing_path)
    now = clock()
    seconds = float(deadline) if deadline is not None else deadline_seconds(kind)
    con = store.connect_state(state_path)
    try:
        con.isolation_level = None
        con.execute("BEGIN IMMEDIATE")
        try:
            row = con.execute("SELECT * FROM compute_envs WHERE name = ?", (ce_name,)).fetchone()
            if row is None:
                raise JobRefused("compute environment %r not found (找不到)" % ce_name[:100])
            status = row["status"]
            if status == compute_envs.UNSUPPORTED:
                raise JobRefused("%s is a %s environment: %s" % (ce_name, compute_envs.KINDS.get(row["platform"], "?"),
                                                                  compute_envs.NOT_SUPPORTED_MESSAGE))
            if status == compute_envs.DISABLED:
                raise JobRefused("%s is disabled (已停用), so it accepts no job" % ce_name)
            agent = row["agent"]
            if not agent:
                raise JobRefused("%s has no agent. Set one with `abf-platform ce update %s --agent <name>`." % (ce_name, ce_name))
            seen = con.execute("SELECT last_seen_at FROM agents WHERE name = ?", (agent,)).fetchone()
            limit = common.offline_after_seconds() if offline_after is None else offline_after
            if seen is None or now - seen["last_seen_at"] > limit:
                raise JobRefused("agent %s is offline (代理離線); nothing was queued" % agent)
            if kind == "list_site_files" and status != compute_envs.AVAILABLE:
                raise JobRefused("%s has the status %s, and only an available environment can list files "
                                 "(目前的狀態不能執行工作). Run `abf-platform ce preflight %s` first." % (ce_name, status, ce_name))
            con.execute("DELETE FROM jobs WHERE finished_at IS NOT NULL AND finished_at < ?", (now - PRUNE_AFTER_SECONDS,))
            args = {"ce": compute_envs.snapshot(row)}
            if kind == "list_site_files":
                args["path"] = listing_path
            cur = con.execute(
                "INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                "VALUES (?, ?, ?, ?, 'queued', ?, ?)", (agent, ce_name, kind, json.dumps(args), now, now + seconds))
            job_id = cur.lastrowid
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
        return job_id
    finally:
        con.close()


def enqueue_preflight(state_path, ce_name, clock=time.time, deadline_seconds=None, offline_after=None):
    return _enqueue(state_path, ce_name, "preflight", None, clock, deadline_seconds, offline_after)


def enqueue_listing(state_path, ce_name, listing_path, clock=time.time, deadline_seconds=None, offline_after=None):
    return _enqueue(state_path, ce_name, "list_site_files", listing_path, clock, deadline_seconds, offline_after)


def claim(state_path, agent, clock):
    """Hand the agent its oldest live job, once: the claim is one write inside one transaction."""
    now = clock()
    con = store.connect_state(state_path)
    try:
        con.isolation_level = None
        con.execute("BEGIN IMMEDIATE")
        try:
            row = con.execute("SELECT id, kind, args_json FROM jobs WHERE agent = ? AND state = 'queued' "
                              "AND deadline_at > ? ORDER BY id LIMIT 1", (agent, now)).fetchone()
            if row is not None:
                con.execute("UPDATE jobs SET state = 'claimed', claimed_at = ? WHERE id = ?", (now, row["id"]))
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
        if row is None:
            return None
        return {"id": row["id"], "kind": row["kind"], "args": json.loads(row["args_json"])}
    finally:
        con.close()


_STATES = ("done", "refused", "error")


def _short(text, limit):
    text = str(text)
    return text if len(text) <= limit else text[:limit - 1] + "…"


def clean_result(kind, result):
    """Only what the platform expects, with every text bounded; an agent cannot make the platform store more."""
    if not isinstance(result, dict):
        return {"ok": False, "message": "the agent sent no result"}
    out = {"ok": bool(result.get("ok"))}
    for key in ("message", "error", "note"):
        if isinstance(result.get(key), str):
            out[key] = _short(result[key], 2000 if key == "message" else 300)
    if kind == "preflight":
        checks = []
        for c in (result.get("checks") if isinstance(result.get("checks"), list) else [])[:20]:
            if isinstance(c, dict) and isinstance(c.get("name"), str):
                status = c.get("status") if c.get("status") in ("pass", "fail", "unchecked") else "fail"
                checks.append({"name": _short(c["name"], 40), "status": status, "detail": _short(c.get("detail") or "", 300)})
        out["checks"] = checks
        if any(c["status"] != "pass" for c in checks) or not checks:
            out["ok"] = False
    else:
        for key in ("path",):
            if isinstance(result.get(key), str):
                out[key] = _short(result[key], 1100)
        for key in ("count", "total", "limit"):
            if isinstance(result.get(key), int) and not isinstance(result.get(key), bool):
                out[key] = result[key]
        if isinstance(result.get("truncated"), bool):
            out["truncated"] = result["truncated"]
        entries = []
        for e in (result.get("entries") if isinstance(result.get("entries"), list) else [])[:LIST_LIMIT]:
            if isinstance(e, dict) and isinstance(e.get("name"), str):
                entries.append({"name": _short(e["name"], 1000), "type": _short(e.get("type") or "other", 10),
                                "size": e.get("size") if isinstance(e.get("size"), int) else 0,
                                "modified": _short(e.get("modified") or "", 40)})
        if "entries" in result:
            out["entries"] = entries
    return out


def take_result(state_path, agent, job_id, state, result, clock):
    """Record an agent's answer. Returns (http status, body).

    404 no such job, 403 not this agent's job, 409 not handed out or already answered. An answer that comes
    after the deadline is kept in late_result_json, the job stays expired, and nothing else changes.
    """
    if state not in _STATES:
        return 400, {"message": "state must be one of %s" % ", ".join(_STATES)}
    now = clock()
    con = store.connect_state(state_path)
    try:
        con.isolation_level = None
        con.execute("BEGIN IMMEDIATE")
        try:
            job = con.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if job is None:
                con.execute("ROLLBACK")
                return 404, {"message": "No such job"}
            if job["agent"] != agent:
                con.execute("ROLLBACK")
                return 403, {"message": "This job belongs to another agent"}
            cleaned = clean_result(job["kind"], result)
            if job["state"] == "queued":
                con.execute("ROLLBACK")
                return 409, {"message": "This job was not handed out"}
            if job["state"] in _STATES:
                con.execute("ROLLBACK")
                return 409, {"message": "This job was answered already"}
            if job["state"] == "expired" or now > job["deadline_at"]:
                con.execute("UPDATE jobs SET state = 'expired', late_result_json = ?, finished_at = COALESCE(finished_at, ?) "
                            "WHERE id = ?", (json.dumps({"state": state, "result": cleaned}), now, job_id))
                con.execute("COMMIT")
                return 200, {"accepted": False, "late": True}
            con.execute("UPDATE jobs SET state = ?, result_json = ?, finished_at = ? WHERE id = ?",
                        (state, json.dumps(cleaned), now, job_id))
            if job["kind"] == "preflight" and state == "done":
                compute_envs.apply_preflight(con, job["compute_env"], cleaned["ok"], cleaned.get("checks", []), now)
            con.execute("COMMIT")
            return 200, {"accepted": True, "late": False}
        except BaseException:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
            raise
    finally:
        con.close()


def _read(state_path, job_id):
    con = store.open_readonly(state_path)
    if con is None:
        return None
    try:
        return con.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    finally:
        con.close()


def _expire(state_path, job_id, clock):
    con = store.connect_state(state_path)
    try:
        with con:
            con.execute("UPDATE jobs SET state = 'expired', finished_at = ? WHERE id = ? AND state IN ('queued', 'claimed')",
                        (clock(), job_id))
    finally:
        con.close()


async def wait_for_result(state_path, job_id, clock=time.time, sleep=asyncio.sleep):
    """Wait for the answer to a job, up to its deadline.

    Returns {'state', 'ok', 'message', 'result', 'agent', 'kind'}. When the deadline comes first the job is
    marked expired and the answer says the agent did not answer.
    """
    row = _read(state_path, job_id)
    while (row is not None and row["state"] not in _STATES and row["state"] != "expired"
           and clock() < row["deadline_at"]):
        await sleep(0.25)
        row = _read(state_path, job_id)
    if row is None:
        return {"state": "error", "ok": False, "message": "the job is gone", "result": None, "agent": None, "kind": None}
    if row["state"] in _STATES:
        result = json.loads(row["result_json"]) if row["result_json"] else None
        ok = row["state"] == "done" and bool(result and result.get("ok"))
        message = (result or {}).get("message") or ("done" if ok else row["state"])
        return {"state": row["state"], "ok": ok, "message": message, "result": result, "agent": row["agent"],
                "kind": row["kind"]}
    _expire(state_path, job_id, clock)
    return {"state": "expired", "ok": False, "result": None, "agent": row["agent"], "kind": row["kind"],
            "message": "The agent did not answer (代理沒有回應): agent %s did not finish the %s job in time. "
                       "The job was dropped and will not run later." % (row["agent"], row["kind"])}
