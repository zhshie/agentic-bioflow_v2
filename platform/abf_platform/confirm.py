# Nothing existing: Seqera's launch button and Tower Agent are closed, and no queue library knows a "yes" that is bound to the hash of what was shown; this is the one function that writes one.
"""The user's "yes" to a launch or a cancel, written in the same transaction as the job it allows (features 007b and 009c).

Only the action layer (abf_platform/actions) calls this module (tests/test_actions_layer.py checks the imports). A confirmation row
holds the hash of the canonical content that was shown (common.bundle_sha256); jobs.py refuses to queue a launch or a cancel for any
content whose hash is not in an unspent row of the right kind that a person has confirmed (state = confirmed).

A row gets there in one of two ways:
  - the terminal: the person typed y, and the row is written already confirmed, with its job, in one transaction (confirm_launch,
    confirm_cancel; channel TERMINAL, or ELICITED / PAGE when the action layer is called with those);
  - a pending request (spec 009c): the MCP tool wrote the row as `pending`, with the whole content, the screen and who asked, and
    no job. It stays that way until a person's yes comes through an MCP form or the confirmation page; approve() then flips it
    and queues the job in one transaction. A pending row is never a confirmation, it expires in PENDING_SECONDS, and a void row
    (declined, expired, or a queue that refused after the yes) can never be brought back.
"""
import json
import secrets
import time

from . import common, jobs, store

PENDING_SECONDS = 600
MAX_OPEN_PENDING = 10             # open requests one caller may have at a time
REUSE_MIN_SECONDS = 60             # a repeated call reuses an open request only while more than this is left of it
KEEP_UNSENT_SECONDS = 7 * 86400    # a void request, or a pending one past its time, keeps its content (bundle, screen) this long; its audit columns stay. A confirmed request keeps it until its owner forgets it (forget_content)
JOB_KIND = {"launch": "launch_nextflow", "cancel": "cancel_run"}


class NotApproved(jobs.JobRefused):
    """approve() queued nothing. `status` says why: not_found, not_yours, void, expired, already (a job exists: job_id) or failed."""

    def __init__(self, status, message, job_id=None):
        super().__init__(message)
        self.status = status
        self.job_id = job_id


def _confirm(state_path, ce_name, kind, job_kind, bundle, clock, deadline_seconds, offline_after, caller_user_id, channel):
    now = clock()
    seconds = jobs._seconds(job_kind, deadline_seconds)
    cid = secrets.token_hex(16)

    def work(con):
        con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, caller_user_id, state, channel, confirmed_at) "
                    "VALUES (?, ?, ?, ?, ?, 'confirmed', ?, ?)",
                    (cid, common.bundle_sha256(bundle), kind, now, caller_user_id, channel, now))
        return cid, jobs.enqueue_confirmed(con, ce_name, job_kind, bundle, cid, now, seconds, offline_after)

    return jobs.transaction(state_path, work)


def confirm_launch(state_path, ce_name, bundle, clock=time.time, deadline_seconds=None, offline_after=None,
                   caller_user_id=None, channel="TERMINAL"):
    """Write the confirmation and queue the launch, or neither (JobRefused). Returns (confirmation id, job id)."""
    return _confirm(state_path, ce_name, "launch", "launch_nextflow", bundle, clock, deadline_seconds, offline_after,
                    caller_user_id, channel)


def confirm_cancel(state_path, ce_name, bundle, clock=time.time, deadline_seconds=None, offline_after=None,
                   caller_user_id=None, channel="TERMINAL"):
    return _confirm(state_path, ce_name, "cancel", "cancel_run", bundle, clock, deadline_seconds, offline_after,
                    caller_user_id, channel)


# ---- the pending request -----------------------------------------------------------------------------------------------------

def create_pending(state_path, kind, ce_name, bundle, screen_text, caller_user_id, clock=time.time):
    """Write a pending request for exactly `bundle` and return its id; no job, and nothing a queue would accept. The same person
    asking again for the same content, while the first request has more than REUSE_MIN_SECONDS left, gets the first one back."""
    now = clock()
    sha = common.bundle_sha256(bundle)

    def work(con):
        con.execute("UPDATE confirmations SET bundle_json = NULL, screen_text = NULL WHERE bundle_json IS NOT NULL AND "
                    "((state = 'void' AND created_at < ?) OR (state = 'pending' AND expires_at < ?))",
                    (now - KEEP_UNSENT_SECONDS, now - KEEP_UNSENT_SECONDS))
        old = con.execute("SELECT id FROM confirmations WHERE state = 'pending' AND kind = ? AND sha256 = ? AND caller_user_id IS ? "
                          "AND expires_at > ? ORDER BY created_at DESC LIMIT 1",
                          (kind, sha, caller_user_id, now + REUSE_MIN_SECONDS)).fetchone()
        if old is not None:
            return old["id"]
        open_now = con.execute("SELECT COUNT(*) FROM confirmations WHERE state = 'pending' AND caller_user_id IS ? AND expires_at > ?",
                               (caller_user_id, now)).fetchone()[0]
        if open_now >= MAX_OPEN_PENDING:
            raise jobs.JobRefused("已經有 %d 個等待中的申請，請先處理（按送出或等它逾時）再申請新的 (at most %d open requests per person; "
                                  "finish or wait for the open ones)" % (open_now, MAX_OPEN_PENDING))
        rid = secrets.token_hex(16)
        con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, caller_user_id, state, expires_at, ce_name, bundle_json, "
                    "screen_text) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)",
                    (rid, sha, kind, now, caller_user_id, now + PENDING_SECONDS, ce_name, json.dumps(bundle), screen_text))
        return rid

    return jobs.transaction(state_path, work)


def void(state_path, rid, reason):
    """A pending request that nobody said yes to is void for good. Returns whether it was pending."""
    def work(con):
        return con.execute("UPDATE confirmations SET state = 'void', void_reason = ? WHERE id = ? AND state = 'pending'",
                           (str(reason)[:300], rid)).rowcount

    return bool(jobs.transaction(state_path, work))


def approve(state_path, rid, channel, caller_user_id, clock=time.time, deadline_seconds=None, offline_after=None):
    """A person said yes to pending request `rid` through `channel` (ELICITED or PAGE): flip it and queue its job, in one
    transaction. Returns (rid, job id). NotApproved when the request is not there, is not this caller's, is void or expired, was
    approved already, or when the queue refuses (then the request is void, with the reason).

    The caller must be the one who made the request. Nobody matches nobody only for ELICITED: a local stdio client has no caller
    at all, and the page always has one."""
    now = clock()

    def work(con):
        row = con.execute("SELECT * FROM confirmations WHERE id = ?", (rid,)).fetchone() if isinstance(rid, str) and len(rid) <= 64 else None
        if row is None:
            return "not_found", "no such request (查無此申請)", None
        if row["state"] == "confirmed":
            job = con.execute("SELECT id FROM jobs WHERE confirmation_id = ?", (rid,)).fetchone()
            return "already", "this request was approved already (已送出)", job["id"] if job else None
        if row["state"] == "void":
            return "void", "this request is void (申請已作廢): %s" % (row["void_reason"] or "-"), None
        if row["caller_user_id"] != caller_user_id or (caller_user_id is None and channel != "ELICITED"):
            return "not_yours", "this request was made by somebody else (不是你的申請)", None
        if row["expires_at"] is None or now >= row["expires_at"]:
            con.execute("UPDATE confirmations SET state = 'void', void_reason = 'expired (逾時)' WHERE id = ?", (rid,))
            return "expired", "this request has expired (申請已逾時)", None
        try:
            bundle = json.loads(row["bundle_json"])
        except (TypeError, ValueError):
            bundle = None
        if not isinstance(bundle, dict) or common.bundle_sha256(bundle) != row["sha256"]:
            con.execute("UPDATE confirmations SET state = 'void', void_reason = 'the content does not match its hash' WHERE id = ?", (rid,))
            return "failed", "the content does not match what was shown (內容與顯示時不符)", None
        con.execute("UPDATE confirmations SET state = 'confirmed', channel = ?, confirmed_at = ? WHERE id = ? AND state = 'pending'",
                    (channel, now, rid))
        job_kind = JOB_KIND[row["kind"]]
        con.execute("SAVEPOINT enqueue")
        try:
            job_id = jobs.enqueue_confirmed(con, row["ce_name"], job_kind, bundle, rid, now, jobs._seconds(job_kind, deadline_seconds),
                                            offline_after)
        except jobs.JobRefused as e:
            con.execute("ROLLBACK TO enqueue")
            con.execute("RELEASE enqueue")
            # channel and confirmed_at stay on the void row: a person did say yes, and the audit keeps that
            con.execute("UPDATE confirmations SET state = 'void', void_reason = ? WHERE id = ?",
                        (str(e)[:300], rid))
            return "failed", str(e), None
        con.execute("RELEASE enqueue")
        return "queued", None, job_id

    status, message, job_id = jobs.transaction(state_path, work)
    if status != "queued":
        raise NotApproved(status, message, job_id)
    return rid, job_id


def find_approved(state_path, kind, bundle, caller_user_id, clock=time.time, include_spent=False):
    """{'id', 'job_id'} of a request that this caller got a person's yes for, for exactly this content, that is still alive
    (confirmed through a form or the page, not spent by an agent, not older than PENDING_SECONDS), or None.

    include_spent=True (the repeated tool call) also finds the request after the agent took its job (used_at is set), as long as the
    job was not refused or expired: the answer is then the job that exists, never a new question."""
    con = store.open_readonly(state_path)
    if con is None:
        return None
    try:
        spent = "" if include_spent else "AND c.used_at IS NULL "
        row = con.execute("SELECT c.id AS id, j.id AS job_id FROM confirmations c JOIN jobs j ON j.confirmation_id = c.id "
                          "WHERE c.state = 'confirmed' AND c.channel IN ('ELICITED', 'PAGE') AND c.kind = ? AND c.sha256 = ? "
                          "AND c.caller_user_id IS ? " + spent + "AND c.expires_at > ? "
                          + ("AND j.state NOT IN ('refused', 'expired') " if include_spent else "")
                          + "ORDER BY c.created_at DESC LIMIT 1", (kind, common.bundle_sha256(bundle), caller_user_id, clock())).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def launched_by(state_path, run_name, caller_user_id):
    """Whether the newest launch of `run_name` in the hand-off record was confirmed by this caller (its launch job's confirmation is
    a confirmed row with this caller_user_id). A launch typed at a terminal, one without a job, or somebody else's is not."""
    con = store.open_readonly(state_path)
    if con is None:
        return False
    try:
        row = con.execute("SELECT c.caller_user_id AS caller, c.state AS state FROM launches l LEFT JOIN jobs j ON j.id = l.job_id "
                          "LEFT JOIN confirmations c ON c.id = j.confirmation_id WHERE l.run_name = ? "
                          "ORDER BY l.id DESC LIMIT 1", (run_name,)).fetchone()
        return row is not None and row["state"] == "confirmed" and caller_user_id is not None and row["caller"] == caller_user_id
    finally:
        con.close()


def find_cancel(state_path, bundle, caller_user_id):
    """{'id', 'job_id'} of a cancel of exactly this run that this caller got a yes for and whose job is still queued or running
    (queued or claimed), or None. After the job is done, failed, refused or expired a new cancel asks again."""
    con = store.open_readonly(state_path)
    if con is None:
        return None
    try:
        row = con.execute("SELECT c.id AS id, j.id AS job_id FROM confirmations c JOIN jobs j ON j.confirmation_id = c.id "
                          "WHERE c.state = 'confirmed' AND c.kind = 'cancel' AND c.sha256 = ? AND c.caller_user_id IS ? "
                          "AND j.state IN ('queued', 'claimed') ORDER BY c.created_at DESC LIMIT 1",
                          (common.bundle_sha256(bundle), caller_user_id)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def describe(state_path, rid, clock=time.time):
    """What a person may be told about request `rid`, or None: its kind, who made it, its state (pending, confirmed, void or
    expired), the text that was shown and the job if there is one. Never the bundle. Terminal confirmations are not requests."""
    con = store.open_readonly(state_path)
    if con is None or not isinstance(rid, str) or len(rid) > 64:
        return None
    try:
        row = con.execute("SELECT c.*, (SELECT j.id FROM jobs j WHERE j.confirmation_id = c.id) AS job_id FROM confirmations c "
                          "WHERE c.id = ? AND c.bundle_json IS NOT NULL", (rid,)).fetchone()
    finally:
        con.close()
    if row is None:
        return None
    state = row["state"]
    if state == "pending" and (row["expires_at"] is None or clock() >= row["expires_at"]):
        state = "expired"
    return {"id": row["id"], "kind": row["kind"], "state": state, "caller_user_id": row["caller_user_id"], "channel": row["channel"],
            "summary": row["screen_text"], "job_id": row["job_id"], "void_reason": row["void_reason"],
            "expires_at": row["expires_at"], "created_at": row["created_at"]}


# ---- forgetting: the owner deletes what was sent (keep-submissions) ---------------------------------------------------------------

FORGOTTEN_JOB_KINDS = ("launch_nextflow", "cancel_run")


def forgotten_args(run_name):
    """What the job of a forgotten run keeps in args_json: the run name and a mark, so jobs._apply_handover (a late answer) still
    reads the name. A reader that needs more must see `forgotten` and refuse: 「內容已被擁有者刪除 (content deleted by its owner)」."""
    return {"forgotten": True, "bundle": {"run_name": run_name}}


def _named(text, run_name):
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None
    bundle = data.get("bundle", data) if isinstance(data, dict) else None
    return data if isinstance(bundle, dict) and bundle.get("run_name") == run_name else None


def forget_content(state_path, run_name, forgotten_by=None, only_user=None, clock=time.time, dry_run=False):
    """Clear the content of every row behind one run: the bundle and screen of its confirmations (the launch's, its cancels', its
    pending and void requests, which an open one is voided by) and the copy each of its jobs keeps (args_json). Audit columns stay;
    every row cleared gets forgotten_at and forgotten_by. `only_user` (an HTTP caller) limits the confirmations to that user's own;
    the terminal passes None. Returns how many rows were (or, with dry_run, would be) cleared.

    JobRefused, nothing changed, when a job of the run is still queued or claimed. Rows of other runs are never touched."""
    now = clock()
    by = None if forgotten_by is None else str(forgotten_by)

    def work(con):
        like = "%" + run_name + "%"
        jobs_of_run = [r for r in con.execute("SELECT id, state, args_json FROM jobs WHERE kind IN (?, ?) AND args_json LIKE ?",
                                              FORGOTTEN_JOB_KINDS + (like,)) if _named(r["args_json"], run_name) is not None]
        if any(r["state"] in ("queued", "claimed") for r in jobs_of_run):
            raise jobs.JobRefused("這個 run 還有工作在排隊或進行中，不能刪除 (a job of this run is still queued or running)")
        todo_jobs = [r["id"] for r in jobs_of_run if not _named(r["args_json"], run_name).get("forgotten")]
        ids = {r[0] for r in con.execute("SELECT j.confirmation_id FROM launches l JOIN jobs j ON j.id = l.job_id "
                                         "WHERE l.run_name = ? AND j.confirmation_id IS NOT NULL", (run_name,))}
        for r in con.execute("SELECT id, bundle_json FROM confirmations WHERE bundle_json IS NOT NULL AND bundle_json LIKE ?", (like,)):
            if _named(r["bundle_json"], run_name) is not None:
                ids.add(r["id"])
        todo_conf = [r["id"] for r in con.execute("SELECT id, caller_user_id FROM confirmations WHERE bundle_json IS NOT NULL")
                     if r["id"] in ids and (only_user is None or r["caller_user_id"] == only_user)]
        if dry_run:
            return len(todo_jobs) + len(todo_conf)
        for cid in todo_conf:
            con.execute("UPDATE confirmations SET bundle_json = NULL, screen_text = NULL, forgotten_at = ?, forgotten_by = ?, "
                        "state = CASE WHEN state = 'pending' THEN 'void' ELSE state END, "
                        "void_reason = CASE WHEN state = 'pending' THEN 'forgotten (已刪除)' ELSE void_reason END WHERE id = ?",
                        (now, by, cid))
        for jid in todo_jobs:
            con.execute("UPDATE jobs SET args_json = ?, forgotten_at = ?, forgotten_by = ? WHERE id = ?",
                        (json.dumps(forgotten_args(run_name)), now, by, jid))
        return len(todo_jobs) + len(todo_conf)

    return jobs.transaction(state_path, work)
