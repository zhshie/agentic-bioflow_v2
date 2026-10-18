# Not Celery or RQ: they need a separate broker process; five job kinds in one SQLite table are enough, and the table is not a run state machine.
"""The queue of jobs that agents poll for.

Five kinds exist (a CHECK constraint in platform.db says so): `preflight`, `list_site_files` and `fetch_run_records`
only read; `launch_nextflow` and `cancel_run` write on the site, so a job of those two kinds can only be queued with
a confirmation: a row that a person's yes made (state confirmed: y at the terminal, a form in the MCP client, or the
confirmation page), bound to the hash of the content the user saw. Every job is a question or an order put to one agent, with a deadline. A job whose deadline passed is
`expired` and is never handed out; an answer that arrives late is kept apart, and for a launch or a cancel the one
fact in it (the Slurm number, the time of the request) is still written to the hand-off record, because losing it
would leave a head job on the site that nobody knows about.

Who writes: the command line (through confirm.py for the two that need a confirmation) and the MCP server queue
jobs; the receiver hands them out and takes the answers. Nobody else writes platform.db, and `rebuild` never opens it.
"""
import asyncio
import json
import os
import re
import sqlite3
import time

from . import common, compute_envs, records, store

LIST_LIMIT = 500
PRUNE_AFTER_SECONDS = 7 * 86400
DEADLINE_SECONDS = {"preflight": 180, "list_site_files": 60, "launch_nextflow": 300, "cancel_run": 90,
                    "fetch_run_records": 180}
_DEADLINE_ENV = {"preflight": "ABF_PLATFORM_DEADLINE_PREFLIGHT",
                 "list_site_files": "ABF_PLATFORM_DEADLINE_LIST_SITE_FILES",
                 "launch_nextflow": "ABF_PLATFORM_DEADLINE_LAUNCH",
                 "cancel_run": "ABF_PLATFORM_DEADLINE_CANCEL",
                 "fetch_run_records": "ABF_PLATFORM_DEADLINE_FETCH"}
KINDS = tuple(DEADLINE_SECONDS)
# the two kinds that write on the site, and the kind of confirmation each needs
CONFIRMED = {"launch_nextflow": "launch", "cancel_run": "cancel"}
_RUN_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}\Z")


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


def _not_found(ce_name):
    return JobRefused("compute environment %r not found (找不到)" % ce_name[:100])


def _target(con, ce_name, kind, now, offline_after, caller_user_id=None):
    """The compute environment row of a job's target, after every check that does not depend on the content.

    With a caller (a user id, 116) the environment and its agent must both be that user's own: one that belongs to somebody else, or
    to nobody, is refused in the words of a missing one, before anything else is said about it. None is the local terminal."""
    if not isinstance(ce_name, str) or not ce_name:
        raise JobRefused("a compute environment name is required")
    row = con.execute("SELECT * FROM compute_envs WHERE name = ?", (ce_name,)).fetchone()
    if row is None or (caller_user_id is not None and row["owner_user_id"] != caller_user_id):
        raise _not_found(ce_name)
    if caller_user_id is not None and row["agent"]:
        owned = con.execute("SELECT owner_user_id FROM agents WHERE name = ?", (row["agent"],)).fetchone()
        if owned is not None and owned["owner_user_id"] != caller_user_id:
            raise _not_found(ce_name)
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
    if kind in ("list_site_files", "launch_nextflow") and status != compute_envs.AVAILABLE:
        raise JobRefused("%s has the status %s, and only an available environment can %s (目前的狀態不能執行工作). "
                         "Run `abf-platform ce preflight %s` first." % (
                             ce_name, status, "list files" if kind == "list_site_files" else "run an analysis", ce_name))
    return row


def _insert_job(con, row, kind, args, now, seconds, confirmation_id=None):
    con.execute("DELETE FROM jobs WHERE finished_at IS NOT NULL AND finished_at < ?", (now - PRUNE_AFTER_SECONDS,))
    cur = con.execute(
        "INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
        "VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)",
        (row["agent"], row["name"], kind, json.dumps(args), now, now + seconds, confirmation_id))
    return cur.lastrowid


def transaction(state_path, work):
    """work(con) inside one BEGIN IMMEDIATE transaction on platform.db; returns what work returns."""
    con = store.connect_state(state_path)
    try:
        con.isolation_level = None
        con.execute("BEGIN IMMEDIATE")
        try:
            out = work(con)
            con.execute("COMMIT")
        except BaseException:
            try:
                con.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        return out
    finally:
        con.close()


def check_target(state_path, ce_name, kind, clock=time.time, offline_after=None, caller_user_id=None):
    """Raise JobRefused, in the words enqueue would use, when the environment cannot take a job of this kind now.
    It only reads, so the terminal commands can use it to refuse before they ask the user anything."""
    con = store.open_readonly(state_path)
    if con is None:
        raise JobRefused("this platform has no data yet (還沒有任何環境)")
    try:
        _target(con, ce_name, kind, clock(), offline_after, caller_user_id)
    except sqlite3.OperationalError:
        raise _not_found(ce_name)      # a platform.db made before 116 that no command has opened yet: nobody owns anything in it
    finally:
        con.close()


def _seconds(kind, deadline):
    return float(deadline) if deadline is not None else deadline_seconds(kind)


def _enqueue(state_path, ce_name, kind, listing_path, clock, deadline, offline_after=None, caller_user_id=None):
    """The kinds that need no confirmation and no run: preflight and list_site_files."""
    if kind == "list_site_files":
        listing_path = check_listing_path(listing_path)
    now = clock()
    seconds = _seconds(kind, deadline)

    def work(con):
        row = _target(con, ce_name, kind, now, offline_after, caller_user_id)
        args = {"ce": compute_envs.snapshot(row)}
        if kind == "list_site_files":
            args["path"] = listing_path
        return _insert_job(con, row, kind, args, now, seconds)

    return transaction(state_path, work)


def enqueue_preflight(state_path, ce_name, clock=time.time, deadline_seconds=None, offline_after=None):
    return _enqueue(state_path, ce_name, "preflight", None, clock, deadline_seconds, offline_after)


def enqueue_listing(state_path, ce_name, listing_path, clock=time.time, deadline_seconds=None, offline_after=None,
                    caller_user_id=None):
    return _enqueue(state_path, ce_name, "list_site_files", listing_path, clock, deadline_seconds, offline_after, caller_user_id)


def enqueue_fetch(state_path, run_name, clock=time.time, deadline_seconds=None, offline_after=None):
    """Ask the agent to read Nextflow's own records of one launch back. It only reads, so it needs no confirmation. The
    run must be in the hand-off record: the platform never asks for a folder it did not launch into."""
    now = clock()
    seconds = _seconds("fetch_run_records", deadline_seconds)

    def work(con):
        launch = latest_launch(con, run_name) if isinstance(run_name, str) else None
        if launch is None:
            raise JobRefused("%r was not launched from this platform (不是平台自己送出的), so there is no folder to read"
                             % str(run_name)[:80])
        row = _target(con, launch["ce"], "fetch_run_records", now, offline_after)
        if row["agent"] != launch["agent"]:
            raise JobRefused("run %s was launched through agent %s, not through the agent of %s (%s)" % (
                run_name, launch["agent"], launch["ce"], row["agent"]))
        args = {"ce": compute_envs.snapshot(row), "run_name": launch["run_name"], "run_folder": launch["run_folder"]}
        return _insert_job(con, row, "fetch_run_records", args, now, seconds)

    return transaction(state_path, work)


def _check_confirmation(con, kind, bundle, confirmation_id):
    """The one guard of the two kinds that write: a confirmation of the right kind, not spent, for exactly this content."""
    want = CONFIRMED[kind]
    if not isinstance(confirmation_id, str) or not confirmation_id or len(confirmation_id) > 64:
        raise JobRefused("no confirmation: a %s is queued only after the user answered y on the terminal "
                         "(沒有確認憑證)" % want)
    conf = con.execute("SELECT * FROM confirmations WHERE id = ?", (confirmation_id,)).fetchone()
    if conf is None:
        raise JobRefused("no such confirmation (查無此確認憑證)")
    if conf["kind"] != want:
        raise JobRefused("that confirmation is for a %s, not for a %s (憑證種類不符)" % (conf["kind"], want))
    if conf["state"] != "confirmed":
        raise JobRefused("no person has said yes to that request (還沒有人確認這個申請)")    # 009c: a pending or void request is no yes
    if conf["used_at"] is not None:
        raise JobRefused("that confirmation was used already (憑證已用過)")
    if con.execute("SELECT 1 FROM jobs WHERE confirmation_id = ?", (confirmation_id,)).fetchone():
        raise JobRefused("that confirmation belongs to a job already (憑證已用過)")
    sha = common.bundle_sha256(bundle)
    if conf["sha256"] != sha:
        raise JobRefused("the content is not the content that was confirmed (內容與確認時不符)")
    return sha


def owned_run_names(state_path, user_id):
    """The run names whose newest row of the hand-off record names this user (116): the runs that user launched. A run with no row,
    or whose newest row has no user, is nobody's here. A platform.db made before 116 that no command has opened yet has no user column,
    so it has no owner of anything."""
    con = store.open_readonly(state_path)
    if con is None:
        return set()
    try:
        return {r[0] for r in con.execute("SELECT run_name FROM launches WHERE id IN (SELECT MAX(id) FROM launches GROUP BY run_name) "
                                          "AND user_id = ?", (user_id,))}
    except sqlite3.OperationalError:
        return set()
    finally:
        con.close()


def latest_launch(con, run_name):
    """The newest row of the hand-off record for a run name, or None. A name may have several rows (a refused launch
    leaves its row and the name can be used again); the newest is the one a cancel, a read-back or a report is about."""
    return con.execute("SELECT * FROM launches WHERE run_name = ? ORDER BY id DESC LIMIT 1", (run_name,)).fetchone()


def _col(row, name):
    """A column of a hand-off row, or None when the file is older than the column (a platform.db no command has opened since the upgrade)."""
    return row[name] if name in row.keys() else None


RUN_NOT_FOUND = "找不到這個 run (Run not found): %s"      # what anybody is told of a run that is not theirs, or not there (116, 009e)


FORGOTTEN = "內容已被擁有者刪除 (content deleted by its owner)"      # what a resume or a relaunch of a forgotten run is told (keep-submissions, F2)


def launch_confirmation(con, launch):
    """The confirmation row of one row of the hand-off record, or None. The launch job names it; when the job is gone (the clean-up of
    finished jobs removes it after 7 days) the row is found by what both wrote in the same transaction: a confirmed launch made at
    the very moment the hand-off row says it was confirmed. There is no column that links the two, and none is added."""
    job = None
    if "job_id" in launch.keys() and launch["job_id"] is not None:
        job = con.execute("SELECT confirmation_id FROM jobs WHERE id = ?", (launch["job_id"],)).fetchone()
    if job is not None and job["confirmation_id"]:
        row = con.execute("SELECT * FROM confirmations WHERE id = ?", (job["confirmation_id"],)).fetchone()
        if row is not None:
            return row
    return con.execute("SELECT * FROM confirmations WHERE kind = 'launch' AND state = 'confirmed' AND confirmed_at = ? "
                       "ORDER BY created_at DESC LIMIT 1", (launch["confirmed_at"],)).fetchone()


def _row_forgotten(con, launch):
    conf = launch_confirmation(con, launch)
    if conf is not None and conf["forgotten_at"] is not None:
        return True
    if "job_id" in launch.keys() and launch["job_id"] is not None:
        job = con.execute("SELECT args_json, forgotten_at FROM jobs WHERE id = ?", (launch["job_id"],)).fetchone()
        if job is not None:
            if job["forgotten_at"] is not None:
                return True
            try:
                return bool(json.loads(job["args_json"]).get("forgotten"))
            except (TypeError, ValueError, AttributeError):
                return False
    return False


def run_forgotten(con, run_name):
    """Whether the owner deleted the content of this run, or of any run it was made from (the analysis it belongs to goes back to a first
    launch). Read from the rows themselves: nothing about it is stored under the run. A platform.db that no command has opened since the
    columns were added has nothing forgotten."""
    try:
        seen, name = set(), run_name
        while name is not None and name not in seen:
            seen.add(name)
            rows = con.execute("SELECT * FROM launches WHERE run_name = ? ORDER BY id", (name,)).fetchall()
            if any(_row_forgotten(con, r) for r in rows):
                return True
            name = _col(rows[-1], "parent_run") if rows else None
    except sqlite3.OperationalError:
        return False
    return False


def launch_content(con, launch, job):
    """(bundle, the hash that was confirmed for it) of one row of the hand-off record, or None. The confirmation holds it first (it is kept
    until the owner forgets it); a row made before that holds it only in its launch job, which is cleared 7 days after it finished."""
    conf = launch_confirmation(con, launch)
    if conf is not None and conf["bundle_json"]:
        try:
            bundle = json.loads(conf["bundle_json"])
        except (TypeError, ValueError):
            bundle = None
        if isinstance(bundle, dict):
            return bundle, conf["sha256"]
    if job is not None:
        try:
            args = json.loads(job["args_json"])
            bundle, sha = args["bundle"], args["bundle_sha256"]
        except (TypeError, ValueError, KeyError):
            return None
        if isinstance(bundle, dict) and isinstance(sha, str):
            return bundle, sha
    return None


def analysis_root(con, run_name):
    """The run name that began the analysis `run_name` belongs to: follow parent_run up until a row has none. The root is a first launch.
    There is no column for it; a resume or a relaunch is the same analysis as the run it was made from (ADR 0009)."""
    seen, name = set(), run_name
    while name not in seen:
        seen.add(name)
        try:
            row = con.execute("SELECT parent_run FROM launches WHERE run_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
        except sqlite3.OperationalError:
            return name
        if row is None or row[0] is None:
            return name
        name = row[0]
    return name


def analysis_rows(con, root):
    """Every row of the hand-off record that belongs to the analysis begun by `root`: the root's own and every row that has a parent in it."""
    rows = con.execute("SELECT * FROM launches ORDER BY id").fetchall()
    names, grew = {root}, True
    while grew:
        grew = False
        for r in rows:
            if _col(r, "parent_run") in names and r["run_name"] not in names:
                names.add(r["run_name"])
                grew = True
    return [r for r in rows if r["run_name"] in names]


def standing_attempts(con, run_name, now):
    """(row, attempt number) of every attempt of the analysis of `run_name` that stands: a first launch is attempt 1, and an attempt
    whose launch job was refused by the agent (nothing was done on the site) does not stand, so it does not use up its number."""
    out = []
    for r in analysis_rows(con, analysis_root(con, run_name)):
        if launch_job(con, r, now)[0] == "refused":
            continue
        out.append((r, _col(r, "attempt") or 1))
    return out


def next_attempt(con, run_name, now):
    return max([n for _, n in standing_attempts(con, run_name, now)] or [1]) + 1


def launch_job(con, launch, now):
    """('refused' | 'waiting' | 'unknown', job row or None) for a launch row without a Slurm number: what its own job says.

    Waiting is a job still queued or handed out whose deadline has not passed (the clock decides, not the state column);
    refused is the state `refused`; anything else, and a row with no job to be found, is unknown.
    """
    job = None
    if "job_id" in launch.keys() and launch["job_id"] is not None:
        job = con.execute("SELECT * FROM jobs WHERE id = ?", (launch["job_id"],)).fetchone()
    if job is None:
        return "unknown", None
    if job["state"] == "refused":
        return "refused", job
    if job["state"] in ("queued", "claimed") and job["deadline_at"] > now:
        return "waiting", job
    return "unknown", job


NAME_TAKEN = "this run name is taken; choose another"      # what an HTTP caller is told when the name is somebody else's or nobody's (116b)


def name_problem(con, run_name, now, caller_user_id=None):
    """The sentence that says why a run name cannot be used for a new launch, or None when it can.

    With a caller (a user id, 116b) a name whose newest row is not that user's own gets NAME_TAKEN and nothing else: no Slurm number, no
    state. The names stay unique for everybody, since the run folder is shared on the site. None keeps the detailed words (the terminal).

    It can only when every earlier row of the name has no Slurm job number AND its own launch job was refused by the
    agent (nothing was done on the site). Submitted, still waiting, or unknown: the name stays taken, and the strictest row
    decides. Read-only, so the terminal command can ask it before it asks the person anything.
    """
    rows = con.execute("SELECT * FROM launches WHERE run_name = ? ORDER BY id", (run_name,)).fetchall()
    problem = _name_problem_of(con, rows, run_name, now)
    if problem and caller_user_id is not None:
        newest = rows[-1]
        if "user_id" not in newest.keys() or newest["user_id"] != caller_user_id:
            return NAME_TAKEN
    return problem


def _name_problem_of(con, rows, run_name, now):
    submitted = [r for r in rows if r["slurm_job_id"] is not None]
    if submitted:
        return ("the run name %s was used already (run 名稱已用過)：它已送出過，Slurm 工作編號是 %s；請換一個名稱"
                % (run_name, submitted[-1]["slurm_job_id"]))
    kinds = [launch_job(con, r, now)[0] for r in rows]
    if "unknown" in kinds:
        return ("the run name %s was used already (run 名稱已用過)：上一次送出的結果不明，請先查國網上的專屬資料夾與 nf-%s，"
                "確認沒有留下東西之後換一個名稱" % (run_name, run_name))
    if "waiting" in kinds:
        return ("the run name %s was used already (run 名稱已用過)：上一次送出還在等代理處理，請等它有結果再說，或換一個名稱"
                % run_name)
    return None


def check_run_name(state_path, run_name, clock=time.time, caller_user_id=None):
    """Raise JobRefused, in the words enqueue_confirmed would use, when the run name cannot be used for a new launch."""
    con = store.open_readonly(state_path)
    if con is None:
        return
    try:
        try:
            problem = name_problem(con, run_name, clock(), caller_user_id)
        except sqlite3.Error:
            return
    finally:
        con.close()
    if problem:
        raise JobRefused(problem)


def _lineage(con, bundle, caller_id, now):
    """(parent run, attempt number, 'resume' | 'relaunch', owner) of a launch that is an attempt of an analysis that exists (spec 009e),
    or JobRefused. Inside the caller's transaction, so a number that was free when the question was asked is checked again here.

    The run it is made from must be a run of this caller's (the newest row of its name names the caller): a yes that was made for one
    user cannot be turned onto another user's run, and says so in the words of a missing run. The number must be one more than the
    highest standing attempt: two attempts asked for at the same time cannot both be 2. The terminal without a user may do an attempt of
    any run; the new row keeps the owner of the run it comes from, so the analysis stays one person's."""
    if "resume" in bundle and "relaunch" in bundle:
        raise JobRefused("the content is both a resume and a relaunch (同時是續跑和重跑)")
    akind = "resume" if "resume" in bundle else "relaunch"
    block = bundle[akind]
    parent_name = block.get("of_run") if isinstance(block, dict) else None
    if not isinstance(parent_name, str) or not _RUN_NAME.match(parent_name):
        raise JobRefused("the %s record names no run (%s 沒有指明是哪個 run 的)" % (akind, akind))
    attempt = block.get("attempt")
    if isinstance(attempt, bool) or not isinstance(attempt, int):
        raise JobRefused("the %s record has no attempt number (沒有第幾次)" % akind)
    parent = latest_launch(con, parent_name)
    if parent is None or (caller_id is not None and _col(parent, "user_id") != caller_id):
        raise JobRefused(RUN_NOT_FOUND % parent_name)
    if run_forgotten(con, parent_name):
        raise JobRefused(FORGOTTEN)       # keep-submissions (F2): a yes made before the owner forgot the run cannot start it again
    if attempt != next_attempt(con, parent_name, now):
        raise JobRefused("another attempt was started meanwhile (這個分析在你確認的時候已經有別的一次嘗試); ask again to see where it stands")
    same_folder = bundle.get("run_folder") == parent["run_folder"]
    if same_folder != (akind == "resume"):
        raise JobRefused("a resume goes on in the folder of the run it resumes, and a relaunch in a new one (續跑用原來的資料夾，重跑用新的)")
    return parent_name, attempt, akind, caller_id if caller_id is not None else _col(parent, "user_id")


def enqueue_confirmed(con, ce_name, kind, bundle, confirmation_id, now, seconds, offline_after=None):
    """Inside the caller's transaction. enqueue_launch and enqueue_cancel call it, and so does confirm.py, which writes
    the confirmation in the same transaction. A launch also writes its row of the hand-off record here."""
    if not isinstance(bundle, dict):
        raise JobRefused("the content is not an object")
    sha = _check_confirmation(con, kind, bundle, confirmation_id)
    # whose yes it is (116): the environment and its agent must be that user's own; a yes typed at the terminal has no user and is not checked
    caller_id = con.execute("SELECT caller_user_id FROM confirmations WHERE id = ?", (confirmation_id,)).fetchone()[0]
    lineage = _lineage(con, bundle, caller_id, now) if kind == "launch_nextflow" and ("resume" in bundle or "relaunch" in bundle) else None
    row = _target(con, ce_name, kind, now, offline_after, caller_id)
    run_name = bundle.get("run_name")
    if not isinstance(run_name, str) or not _RUN_NAME.match(run_name) or not isinstance(bundle.get("run_folder"), str):
        raise JobRefused("the content names no run (沒有 run 名稱或專屬資料夾)")
    if bundle.get("agent") != row["agent"]:
        raise JobRefused("the content is for agent %r, not for the agent of %s (%s)" % (
            str(bundle.get("agent"))[:64], ce_name, row["agent"]))
    if kind == "launch_nextflow":
        problem = name_problem(con, run_name, now, caller_id)
        if problem:
            raise JobRefused(problem)
        args = {"bundle": bundle, "confirmation_id": confirmation_id, "bundle_sha256": sha}
        job_id = _insert_job(con, row, kind, args, now, seconds, confirmation_id)
        if lineage is None:
            con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, job_id, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (run_name, bundle["run_folder"], ce_name, row["agent"], now, job_id, caller_id))
        else:
            parent, attempt, akind, owner = lineage
            con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, job_id, user_id, parent_run, attempt, attempt_kind) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (run_name, bundle["run_folder"], ce_name, row["agent"], now, job_id, owner, parent, attempt, akind))
        return job_id
    launch = latest_launch(con, run_name)
    if launch is not None and caller_id is not None and launch["user_id"] != caller_id:
        launch = None      # the run was launched by somebody else (or by nobody): to this caller it is a run that is not there
    if launch is None or launch["slurm_job_id"] is None:
        raise JobRefused("run %s has no Slurm job number in the hand-off record (不是平台自己送出的，或尚未送出)" % run_name)
    args = {"bundle": bundle, "confirmation_id": confirmation_id, "bundle_sha256": sha}
    return _insert_job(con, row, kind, args, now, seconds, confirmation_id)


def enqueue_launch(state_path, ce_name, bundle, confirmation_id, clock=time.time, deadline_seconds=None, offline_after=None):
    """Queue a launch for a confirmation that exists, is unspent and was made for exactly this bundle; else JobRefused."""
    now = clock()
    seconds = _seconds("launch_nextflow", deadline_seconds)
    return transaction(state_path, lambda con: enqueue_confirmed(con, ce_name, "launch_nextflow", bundle, confirmation_id,
                                                                 now, seconds, offline_after))


def enqueue_cancel(state_path, ce_name, bundle, confirmation_id, clock=time.time, deadline_seconds=None, offline_after=None):
    now = clock()
    seconds = _seconds("cancel_run", deadline_seconds)
    return transaction(state_path, lambda con: enqueue_confirmed(con, ce_name, "cancel_run", bundle, confirmation_id,
                                                                 now, seconds, offline_after))


def claim(state_path, agent, clock, tokens_path=None):
    """Hand the agent its oldest live job, once: the claim is one write inside one transaction.

    A job of a confirmed kind is handed out with its confirmation row (the agent checks the hash against its own) and
    the confirmation is marked used. A launch also gets its run token here and nowhere earlier: so a launch that is
    answered n, or never claimed, has no token at all. The plain token is in this reply and in no database."""
    now = clock()
    con = store.connect_state(state_path)
    try:
        con.isolation_level = None
        con.execute("BEGIN IMMEDIATE")
        try:
            row = con.execute("SELECT id, kind, args_json, confirmation_id, deadline_at FROM jobs WHERE agent = ? "
                              "AND state = 'queued' AND deadline_at > ? ORDER BY id LIMIT 1", (agent, now)).fetchone()
            out = None
            if row is not None:
                out = {"id": row["id"], "kind": row["kind"], "args": json.loads(row["args_json"]),
                       "remaining": max(0.0, row["deadline_at"] - now)}
                if row["kind"] in CONFIRMED:
                    conf = con.execute("SELECT * FROM confirmations WHERE id = ?", (row["confirmation_id"],)).fetchone()
                    if conf is None or conf["used_at"] is not None or conf["kind"] != CONFIRMED[row["kind"]] or conf["state"] != "confirmed":
                        con.execute("UPDATE jobs SET state = 'refused', finished_at = ?, result_json = ? WHERE id = ?",
                                    (now, json.dumps({"ok": False, "message": "no usable confirmation (沒有可用的確認憑證)"}),
                                     row["id"]))
                        con.execute("COMMIT")
                        return None
                    con.execute("UPDATE confirmations SET used_at = ? WHERE id = ?", (now, conf["id"]))
                    out["confirmation"] = {"id": conf["id"], "sha256": conf["sha256"], "kind": conf["kind"]}
                    if row["kind"] == "launch_nextflow":
                        if tokens_path is None:
                            raise RuntimeError("a launch is claimed with the token file at hand")
                        out["run_token"] = store.create_token(tokens_path, run_name=out["args"]["bundle"]["run_name"])
                con.execute("UPDATE jobs SET state = 'claimed', claimed_at = ? WHERE id = ?", (now, row["id"]))
            con.execute("COMMIT")
        except BaseException:
            try:
                con.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        return out
    finally:
        con.close()


_STATES = ("done", "refused", "error")


def _short(text, limit):
    text = str(text)
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _int(value, low=0, high=2 ** 31 - 1):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else None


def clean_result(kind, result, stored=None):
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
    elif kind in ("launch_nextflow", "cancel_run"):
        sid = _int(result.get("slurm_job_id"), 1)
        if sid is not None:
            out["slurm_job_id"] = sid
        for key, limit in (("run_name", 64), ("run_folder", 1100), ("left_on_site", 600)):
            if isinstance(result.get(key), str):
                out[key] = _short(result[key], limit)
    elif kind == "fetch_run_records":
        out["files"] = [{"name": f["name"], "size": f["size"], "truncated": f["truncated"]} for f in (stored or {}).get("files", [])]
        out["refused"] = [_short(x, 200) for x in (stored or {}).get("refused", [])][:50]
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


def _apply_handover(con, job, state, cleaned, now):
    """What an answer changes in the hand-off record. Returns the run name whose token is to be revoked, else None.

    A launch that was submitted writes its Slurm number and the time; any other answer to a launch (refused, an error,
    an unknown outcome) revokes the run token, because the run may never start. A cancel that was sent writes the time of
    the request: it is a fact about a request, and no state of the run.
    """
    if job["kind"] == "launch_nextflow":
        run_name = json.loads(job["args_json"])["bundle"]["run_name"]
        sid = cleaned.get("slurm_job_id")
        if state == "done" and cleaned.get("ok") and sid is not None:
            # the row this very job made, not any row of the name
            con.execute("UPDATE launches SET slurm_job_id = ?, submitted_at = COALESCE(submitted_at, ?) WHERE job_id = ?",
                        (sid, now, job["id"]))
            return None
        return run_name
    if job["kind"] == "cancel_run" and state == "done" and cleaned.get("ok"):
        bundle = json.loads(job["args_json"])["bundle"]
        con.execute("UPDATE launches SET cancel_requested_at = ? WHERE run_name = ? AND slurm_job_id = ?",
                    (now, bundle["run_name"], bundle.get("slurm_job_id")))
    return None


def take_result(state_path, agent, job_id, state, result, clock, tokens_path=None, records_dir=None):
    """Record an agent's answer. Returns (http status, body).

    404 no such job, 403 not this agent's job, 409 not handed out or already answered. An answer that comes
    after the deadline is kept in late_result_json and the job stays expired; for a launch or a cancel the fact in it is
    still written to the hand-off record (see _apply_handover).
    """
    if state not in _STATES:
        return 400, {"message": "state must be one of %s" % ", ".join(_STATES)}
    now = clock()
    stored = None
    peek = _read(state_path, job_id)
    if (peek is not None and peek["kind"] == "fetch_run_records" and peek["agent"] == agent and state == "done"
            and peek["state"] in ("claimed", "expired") and records_dir is not None and isinstance(result, dict)):
        stored = records.store_files(records_dir, json.loads(peek["args_json"]).get("run_name"), result.get("files"))
    revoke = None
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
            cleaned = clean_result(job["kind"], result, stored)
            if job["state"] == "queued":
                con.execute("ROLLBACK")
                return 409, {"message": "This job was not handed out"}
            if job["state"] in _STATES:
                con.execute("ROLLBACK")
                return 409, {"message": "This job was answered already"}
            if job["state"] == "expired" or now > job["deadline_at"]:
                con.execute("UPDATE jobs SET state = 'expired', late_result_json = ?, finished_at = COALESCE(finished_at, ?) "
                            "WHERE id = ?", (json.dumps({"state": state, "result": cleaned}), now, job_id))
                revoke = _apply_handover(con, job, state, cleaned, now)
                con.execute("COMMIT")
                body = {"accepted": False, "late": True}
            else:
                con.execute("UPDATE jobs SET state = ?, result_json = ?, finished_at = ? WHERE id = ?",
                            (state, json.dumps(cleaned), now, job_id))
                if job["kind"] == "preflight" and state == "done":
                    compute_envs.apply_preflight(con, job["compute_env"], cleaned["ok"], cleaned.get("checks", []), now)
                revoke = _apply_handover(con, job, state, cleaned, now)
                con.execute("COMMIT")
                body = {"accepted": True, "late": False}
        except BaseException:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
            raise
    finally:
        con.close()
    if revoke and tokens_path is not None:
        store.revoke_run_tokens(tokens_path, revoke)
    return 200, body


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
            "claimed": row["claimed_at"] is not None,
            "message": "The agent did not answer (代理沒有回應): agent %s did not finish the %s job in time. "
                       "The job was dropped and will not run later." % (row["agent"], row["kind"])}
