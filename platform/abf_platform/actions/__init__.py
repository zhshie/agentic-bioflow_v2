# Nothing existing: the platform's own list of what it can do (read six things, queue a launch or a cancel after a human's yes); no library knows these rules, and this only calls the modules that already hold them.
"""The action layer (spec 009b, ADR 0006; the human channels are spec 009c): one function per action.

Every entry of the platform (the MCP tools, the confirmation page, later the chat) calls these functions and nothing else.
The read actions are the bodies the MCP tools had. launch and cancel check who said yes, then call confirm.py, which writes the
confirmation and the job in one transaction. `confirmed_by` must be one of three objects, each a person's yes through a channel
a person operates: TERMINAL (y typed at the question of abf_launch/cli.py), ELICITED (the form of the person's MCP client, below)
and PAGE (the confirmation page, as the same logged-in user). Anything else is refused before a database is opened.

The MCP tools launch and cancel do not call launch and cancel. They call request_launch and request_cancel, which build the same
bundle and screen as the terminal, write a pending request (no job), and ask the person: through the client's form if it has one
(then approve() runs with ELICITED), else by naming the confirmation page, whose button calls approve() with PAGE. A repeated tool
call finds the yes (find_approved) and returns the job that exists; it never queues a second.

The tools resume and relaunch (spec 009e) are asked the same way, through request_resume and request_relaunch. Their one argument is the
name of a failed run; what is resumed or started again is the first launch's own bundle, so nothing of the analysis can be said again.
They write the same kind of confirmation (a launch) and queue the same kind of job; what tells them apart is the content the hash covers.
"""
import dataclasses
import os
import re
import sqlite3
import time

from abf_launch import build

from .. import agents, common, compute_envs, confirm, failures, jobs, pipeline_launch, status, store, su

NotApproved = confirm.NotApproved


class _Channel:
    """A channel a person's yes came through. The only instances are the three below; a copy or a look-alike is not one of them."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<abf_platform.actions.%s>" % self.name


TERMINAL = _Channel("TERMINAL")
ELICITED = _Channel("ELICITED")
PAGE = _Channel("PAGE")


@dataclasses.dataclass(frozen=True)
class Caller:
    """Who is calling: a user of the platform. None (the default everywhere) is the local terminal or stdio, and it sees and uses
    everything. A caller is never a confirmation; since 116 it also bounds what the action reaches: only the environments, agents,
    runs and upload folder that are the caller's own. What belongs to somebody else, or to nobody, answers like what is missing."""
    user_id: int
    name: str
    lab: str


    @staticmethod
    def connector(user_id, name, lab, form_ok):
        """The caller proven by a connector's token (spec 009i): the same three fields, and whether the client's own form may be shown."""
        return ConnectorCaller(user_id, name, lab, bool(form_ok))


@dataclasses.dataclass(frozen=True)
class ConnectorCaller(Caller):
    form_ok: bool = False


def platform_path_for(index_path, platform_path=None):
    return platform_path or store.default_platform_path(index_path)


# ---- read ------------------------------------------------------------------------------------------------------------

def list_runs(index_path, *, caller=None, platform_path=None):
    names = None
    if caller is not None:      # the runs the caller launched: those whose newest launch record names the caller
        names = jobs.owned_run_names(platform_path_for(index_path, platform_path), caller.user_id)
    path = platform_path_for(index_path, platform_path)
    at = status.now()
    rows = status.list_runs(index_path, at, names=names)
    for row in rows:
        row["failure"] = None
        if row["status"] in ("failed", "lost"):     # the failed tasks live in the full view; the list row stays as it was
            full = status.get_run(index_path, row["id"], at)
            if full is not None:
                asked = jobs.cancel_requested_at(path, row["name"])
                if asked is not None:
                    full["cancel_requested_at"] = common.epoch_iso_ms(asked)
                row["failure"] = failures.summarize(full)
    return {"runs": rows}


RUN_NOT_FOUND_TEXT = "Run not found: %s (找不到這個 run)"


def get_run(index_path, run_id, *, caller=None, platform_path=None):
    view = status.get_run(index_path, run_id, status.now())
    if view is not None and caller is not None and view["name"] not in jobs.owned_run_names(
            platform_path_for(index_path, platform_path), caller.user_id):
        view = None
    if view is None:
        return {"found": False, "id": run_id, "message": RUN_NOT_FOUND_TEXT % run_id}
    asked = jobs.cancel_requested_at(platform_path_for(index_path, platform_path), view["name"])
    if asked is not None:        # a fact about a request that was sent, never a state of the run (the status stays Nextflow's word)
        view["cancel_requested_at"] = common.epoch_iso_ms(asked)
    view["failure"] = failures.summarize(view)
    view["su"] = _su_of_run(index_path, view, platform_path_for(index_path, platform_path))
    return view


def _su_of_run(index_path, view, platform_path):
    """The `su` part of get_run: five fixed keys (and twd when the site has money rates per SU). Unknown, with the reason, when
    the run has not ended or fewer succeeded tasks have a usage row than the run counts; never a partial sum."""
    rates = su.load_rates()
    site = su.site_of_run(platform_path, view["name"], rates)
    if view["status"] in ("running", "lost"):
        out = su._unknown([su.RUN_NOT_ENDED])
    else:
        tasks = su.run_tasks(index_path, view["name"])
        done = sum(1 for t in tasks or () if t.get("status") == "COMPLETED")
        if tasks is not None and done < view["tasks"]["succeeded"]:
            gap = view["tasks"]["succeeded"] - done
            out = su._unknown(["有 %d 個成功的 task 沒有用量紀錄 (%d succeeded tasks have no usage record)" % (gap, gap)])
        else:
            out = su.run_su(index_path, view["name"], site, rates, lambda *_: tasks)
    shown = {k: out[k] for k in ("su", "twd_nstc", "twd_academic", "unknown_reasons")}
    if "twd" in out:
        shown["twd"] = out["twd"]
    shown["site"] = site if isinstance(rates, dict) else None      # no rates file, no site (the reasons say so)
    return shown


def estimate_su(index_path, run_name, *, caller=None, platform_path=None, site=None, rates=None, tasks_of=None):
    """The SU a run used, and what that costs, from its trace. The run must be the caller's own (else the same answer as get_run's
    not found). Unknown (None, with the reasons) when the record lacks what the formula needs; never a guess."""
    view = status.find_run(index_path, run_name, status.now())
    if view is not None and caller is not None and view["name"] not in jobs.owned_run_names(
            platform_path_for(index_path, platform_path), caller.user_id):
        view = None
    if view is None:
        return {"found": False, "id": run_name,
                "message": "Run not found: %s (找不到這個 run)" % run_name}
    rates = rates if rates is not None else su.load_rates()
    if site is None:
        # the site of the compute environment the run was launched on (its suSite), else the rates file's default_site
        site = su.site_of_run(platform_path_for(index_path, platform_path), run_name, rates)
    return su.run_su(index_path, run_name, site, rates, tasks_of)


def list_compute_envs(platform_path, *, caller=None):
    return {"compute_envs": compute_envs.list_all(platform_path, owner=_caller_id(caller))}


def get_compute_env(platform_path, name, *, caller=None):
    view = compute_envs.get(platform_path, name, owner=_caller_id(caller))
    if view is None:
        return {"found": False, "name": name,
                "message": "Compute environment not found: %s (找不到這個算力環境)" % name}
    return view


def list_agents(platform_path, *, caller=None):
    return {"agents": agents.list_agents(platform_path, status.now(), owner=_caller_id(caller))}


_SHEET_SUFFIXES = (".csv", ".tsv")
_SHEET_LIMIT = 200
_SHEET_DEPTH = 3


def list_samplesheets(platform_path, *, caller):
    """The samplesheets the caller may choose for a launch: the .csv and .tsv files below <uploads_root>/<caller name>/, as paths relative
    to that folder (which request_launch reads as inside it). Only the caller's own folder is looked at; a link is not followed and
    not listed. Nothing is created or read; an absent folder is an empty list."""
    try:
        area = caller_area(platform_path, caller)
    except build.Refusal:
        return []
    found = []
    for folder, dirs, files in os.walk(area, followlinks=False):
        depth = 0 if folder == area else len(os.path.relpath(folder, area).split(os.sep))
        dirs[:] = sorted(d for d in dirs if depth < _SHEET_DEPTH and not d.startswith(".") and not os.path.islink(os.path.join(folder, d)))
        for name in sorted(files):
            full = os.path.join(folder, name)
            if name.lower().endswith(_SHEET_SUFFIXES) and not name.startswith(".") and os.path.isfile(full) and not os.path.islink(full):
                found.append(os.path.relpath(full, area).replace(os.sep, "/"))
    return sorted(found)[:_SHEET_LIMIT]


def launch_prefill(platform_path, run_name, *, caller=None):
    """What the caller's own earlier run was sent with, to fill the launch form from it (quick launch, spec 012b): the pipeline, the
    revision, the environment name and the parameters of its first launch, and when it went out. {"found": False} for a run that is not
    the caller's or is not there (the same answer for both); {"found": True, "kept": False} when the content is no longer kept (the owner
    forgot it, or the clean-up took it). Reads only; the samples are never part of it."""
    gone = {"found": False, "kept": False}
    con = store.open_readonly(platform_path)
    if con is None:
        return gone
    try:
        row = jobs.latest_launch(con, run_name) if isinstance(run_name, str) else None
        if row is None or (caller is not None and jobs._col(row, "user_id") != caller.user_id):
            return gone
        out = {"found": True, "kept": False, "launched_at": row["confirmed_at"]}
        if jobs.run_forgotten(con, run_name):
            return out
        now = time.time()
        for r in con.execute("SELECT * FROM launches WHERE run_folder = ? ORDER BY id DESC", (row["run_folder"],)).fetchall():
            if jobs._col(r, "attempt_kind") == "resume":
                continue
            kind, job = jobs.launch_job(con, r, now)
            if kind == "refused":
                continue
            content = jobs.launch_content(con, r, job)
            if content is None:
                return out
            bundle = content[0]
            return dict(out, kept=True, pipeline=bundle.get("pipeline"), revision=bundle.get("revision"), ce_name=row["ce"],
                        params=dict(bundle["params"]) if isinstance(bundle.get("params"), dict) else {})
        return out
    except sqlite3.Error:
        return {"found": True, "kept": False, "launched_at": None}
    finally:
        con.close()


def _inside(path, root):
    """True when path is root or lies below it, compared by whole path components (never by prefix text)."""
    want, base = [p for p in path.split("/") if p], [p for p in root.split("/") if p]
    return want[:len(base)] == base


def _uploads_problem(platform_path, caller, path):
    """The sentence that refuses a listing of somebody else's upload folder, or None. A path inside <uploads_root> is allowed for a
    caller only inside <uploads_root>/<their name>; any other path follows the rule of the environment's read roots. The path is
    judged as written and again with its links followed (116b), so a link cannot lead from anywhere into another folder."""
    if not isinstance(path, str) or compute_envs.path_problem(path):
        return None                       # the queue refuses a path that is not a plain absolute one, in its own words
    root = os.path.abspath(str(store.uploads_root(platform_path)))
    spellings = {compute_envs.normalize_path(root), compute_envs.normalize_path(os.path.realpath(root))}
    own = [compute_envs.normalize_path(os.path.join(s, caller.name)) for s in spellings] if caller.name else []
    for want in {compute_envs.normalize_path(path), compute_envs.normalize_path(os.path.realpath(path))}:
        if any(_inside(want, s) for s in spellings) and not any(_inside(want, o) for o in own):
            return "只能列你自己的上傳資料夾 (you may list only your own uploads folder): %s" % os.path.realpath(os.path.join(root, caller.name))
    return None


async def list_site_files(platform_path, compute_env, path, *, caller=None):
    answer = {"compute_env": compute_env, "path": path}
    if caller is not None:
        problem = _uploads_problem(platform_path, caller, path)
        if problem:
            answer.update(ok=False, message=problem)
            return answer
    try:
        job_id = jobs.enqueue_listing(platform_path, compute_env, path, status.now, caller_user_id=_caller_id(caller))
    except jobs.JobRefused as e:
        answer.update(ok=False, message=str(e))
        return answer
    out = await jobs.wait_for_result(platform_path, job_id, status.now)
    result = out["result"]
    if out["state"] == "done" and result and result.get("ok"):
        answer.update(result)
        answer["path"] = result.get("path", path)
        return answer
    answer.update(ok=False, message=out["message"])
    if result and result.get("error"):
        answer["error"] = result["error"]
    return answer


_OUTPUTS_NO_RUN = "Run not found (找不到這個 run)"      # the same words for a run that is not there and for somebody else's: no id, nothing to tell them apart
_OUTPUTS_NO_LAUNCH = ("不是從平台送出的分析，沒有輸出資料夾紀錄 "
                      "(this analysis was not launched from the platform, so there is no output folder on record)")
_OUTPUTS_NO_ANSWER = "站台沒有回應 (the site did not answer)"
_OUTPUTS_GENERIC = "站台讀不到這個資料夾 (the site could not read this folder)"
_INTERNAL_WORDS = re.compile(r"Traceback|File \"|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|sqlite|args_json|deadline_at|result_json|"
                             r"Exception|, line \d+")


def _outputs_reason(message):
    """The site's own sentence when it is one plain line; a stack, SQL or an internal field name is never passed on."""
    line = next((x.strip() for x in str(message or "").splitlines() if x.strip()), "")
    if not line or _INTERNAL_WORDS.search(str(message)) or compute_envs.looks_like_credential(str(message)):
        return _OUTPUTS_GENERIC
    return line[:300]


def run_outputs(index_path, platform_path, run_id, *, caller=None, relist=False, enqueue=True):
    """What `<run folder>/results` holds, for the run page: the answer of the newest list_site_files job for that folder. It never
    waits for the site (`list_site_files` does, up to 60 seconds, and a page refreshes every 15): with no job for the folder it queues one
    and says `loading`; with `relist` it queues a new one even if there is an answer. `enqueue=False` only looks.
    Returns {state: loading|ready|error|unavailable, path, compute_env, files, listed_at, reason}; a run that is not the caller's or is
    not there answers {found: False, message} and queues nothing."""
    view = status.get_run(index_path, run_id, status.now()) if isinstance(run_id, str) else None
    plat = platform_path_for(index_path, platform_path)
    if view is None or (caller is not None and view["name"] not in jobs.owned_run_names(plat, caller.user_id)):
        return {"found": False, "message": _OUTPUTS_NO_RUN}
    answer = {"state": "unavailable", "path": None, "compute_env": None, "files": [], "listed_at": None, "reason": None}
    con = store.open_readonly(plat)
    launch = None
    if con is not None:
        try:
            launch = jobs.latest_launch(con, view["name"])
        except sqlite3.Error:
            launch = None
        finally:
            con.close()
    folder = launch["run_folder"] if launch is not None and launch["run_folder"] else None
    if folder is None:
        answer["reason"] = _OUTPUTS_NO_LAUNCH
        return answer
    path = folder.rstrip("/") + "/results"
    ce = launch["ce"]
    answer.update(path=path, compute_env=ce, state="loading")
    job = None if relist else jobs.latest_listing(plat, ce, path)
    if job is None:
        if not enqueue:
            return answer
        try:
            jobs.enqueue_listing(plat, ce, path, status.now, caller_user_id=_caller_id(caller))
        except jobs.JobRefused as e:
            answer.update(state="error", reason=str(e))
        return answer
    result = job["result"] or {}
    if job["state"] in ("queued", "claimed"):
        if status.now() > job["deadline_at"]:      # nobody marks it expired when nobody waits: the page says so, and queues nothing
            answer.update(state="error", reason=_OUTPUTS_NO_ANSWER)
        return answer
    if job["state"] == "done" and result.get("ok"):
        files = [{"name": e["name"], "type": e.get("type", "other"), "size": e.get("size", 0), "modified": e.get("modified", "")}
                 for e in result.get("entries") or []]
        answer.update(state="ready", files=files, listed_at=job["finished_at"])
        return answer
    answer.update(state="error", listed_at=job["finished_at"],
                  reason=_OUTPUTS_NO_ANSWER if job["state"] == "expired" else _outputs_reason(result.get("message")))
    return answer


READ_WHICH = "which must be one of err, out, log (which 只能是 err、out、log)"
NO_WORKDIR = "no recorded workdir for this task (沒有記錄到這個任務的工作資料夾)"
LOG_NOT_FOUND = "file not found in the task folder (任務資料夾裡找不到這個檔案)"


async def read_task_log(platform_path, index_path, run_name, task, which, *, caller=None):
    """The end of one log file (.command.err, .command.out or .command.log) of one failed task of a run, read by the agent of
    the run from the task folder the run reported. At most 200 lines and 64 KB, the last ones, and a cut is said. Reads only; the run is
    the caller's own (anything else answers like a run that is not there)."""
    answer = {"run_name": run_name, "task": task, "which": which}

    def refused(message):
        answer.update(ok=False, message=message)
        return answer

    if which not in jobs.LOG_FILES:
        return refused(READ_WHICH)
    run = status.find_run(index_path, run_name, status.now()) if isinstance(run_name, str) else None
    if run is None or (caller is not None and run_name not in jobs.owned_run_names(platform_path, caller.user_id)):
        return refused(RUN_NOT_FOUND_TEXT % run_name)
    view = status.get_run(index_path, run["id"], status.now())
    workdir = next((t.get("workdir") for t in view["failed_tasks"] if t["name"] == task), None) if view else None
    if not workdir:
        return refused(NO_WORKDIR)
    filename = jobs.LOG_FILES[which]
    try:
        job_id = jobs.enqueue_task_log(platform_path, run_name, workdir, filename, status.now, caller_user_id=_caller_id(caller))
    except jobs.JobRefused as e:
        return refused(str(e))
    out = await jobs.wait_for_result(platform_path, job_id, status.now)
    result = out["result"]
    if out["state"] == "done" and result and result.get("ok") and isinstance(result.get("text"), str):
        answer.update(ok=True, file=filename, workdir=workdir, text=result["text"], lines=result.get("lines", 0),
                      truncated=bool(result.get("truncated")))
        if answer["truncated"]:
            answer["note"] = ("truncated (截斷): the end of the file is shown, at most %d lines and %d KB"
                              % (jobs.LOG_MAX_LINES, jobs.LOG_MAX_BYTES // 1024))
        return answer
    if result and result.get("error") == "not_found":
        return refused(LOG_NOT_FOUND)
    refused(out["message"])
    if result and result.get("error"):
        answer["error"] = result["error"]
    return answer


# ---- write: only after a human's yes -------------------------------------------------------------------------------------

def _require_human(confirmed_by):
    if not (confirmed_by is TERMINAL or confirmed_by is ELICITED or confirmed_by is PAGE):
        raise jobs.JobRefused("no human confirmation channel")


def launch(state_path, ce_name, bundle, *, confirmed_by, clock=time.time, deadline_seconds=None, offline_after=None,
           caller=None):
    """Queue a launch of exactly `bundle`. Returns (confirmation id, job id). The confirmation row keeps the bundle until the owner
    forgets the run (keep-submissions); keep_screen adds the text the person was shown."""
    _require_human(confirmed_by)
    return confirm.confirm_launch(state_path, ce_name, bundle, clock=clock, deadline_seconds=deadline_seconds,
                                  offline_after=offline_after, caller_user_id=caller.user_id if caller else None,
                                  channel=confirmed_by.name)


def cancel(state_path, ce_name, bundle, *, confirmed_by, clock=time.time, deadline_seconds=None, offline_after=None,
           caller=None):
    """Queue a cancel of exactly `bundle`. Returns (confirmation id, job id)."""
    _require_human(confirmed_by)
    return confirm.confirm_cancel(state_path, ce_name, bundle, clock=clock, deadline_seconds=deadline_seconds,
                                  offline_after=offline_after, caller_user_id=caller.user_id if caller else None,
                                  channel=confirmed_by.name)


def keep_screen(state_path, confirmation_id, screen_text):
    """Keep, with the confirmation a person gave at the terminal, the text they were shown and said yes to (keep-submissions, F5). It
    writes only that text, only on a confirmed row of the terminal that has none yet; it queues nothing and confirms nothing."""
    return confirm.keep_screen(state_path, confirmation_id, screen_text)


# ---- write, through a pending request: the MCP tools and the confirmation page ---------------------------------------------------------

DEFAULT_WEB_BASE = "http://127.0.0.1:8789"


def _is_loopback_url(url):
    from urllib.parse import urlparse
    return (urlparse(url).hostname or "") in ("127.0.0.1", "localhost", "::1")


def _caller_id(caller):
    return caller.user_id if caller else None


def _no(message):
    return {"ok": False, "sent": False, "message": message}


def _queued(rid, job_id, what):
    return {"ok": True, "sent": True, "state": "queued", "id": rid, "job_id": job_id,
            "message": "已交給代理排隊（工作編號 %s）：%s (queued as job %s)" % (job_id, what, job_id)}


def person_at(ctx):
    """The person behind one MCP tool call (the form of their client), for request_launch and request_cancel."""
    from .. import elicit as forms       # only the MCP server needs the SDK's form; the terminal commands do not load it
    return forms.Person(ctx)


def form_is_trusted(caller):
    """Whether this caller may be shown the client's own form: stdio (None) and a PAT always; a connector's token only when its client
    was vetted when the token was read (see the connector's redirect rule in docs/PLATFORM.md). The rest get the page only."""
    return caller is None or getattr(caller, "form_ok", True)


async def _ask(platform_path, kind, ce_name, bundle, text, what, caller, person, clock, remote=False, tool=None):
    """The yes of a person for a bundle that is built and checked: through the form, else by the page; never by the caller itself.
    `kind` is the kind of confirmation; `tool` is the name the person knows it by (resume, relaunch), the kind when none is given."""
    caller_id = _caller_id(caller)
    form = person is not None and person.can_ask() and form_is_trusted(caller)
    tool = tool or kind
    nobody = ("這裡沒有人可以按「送出」（本機 stdio 的客戶端不能跳出表單）。請改用終端機指令 `abf-platform %s`，或用帶權杖的 HTTP 連線 "
              "(no one can say yes here: use the terminal command, or HTTP with a token)" % tool)
    if caller is None and not form:
        return _no(nobody)
    try:
        rid = confirm.create_pending(platform_path, kind, ce_name, bundle, text, caller_id, clock)
    except jobs.JobRefused as e:
        return _no("未送出：%s" % e)
    if form:
        yes, why = await person.says_yes(text)
        if yes is not None:
            if not yes:
                confirm.void(platform_path, rid, why)
                return _no("未送出：%s (not sent)" % why)
            try:
                _, job_id = confirm.approve(platform_path, rid, ELICITED.name, caller_id, clock)
            except confirm.NotApproved as e:
                if e.status == "already":
                    return _queued(rid, e.job_id, what)
                return _no("未送出：%s。請從 AI 重新送出 (nothing was queued; send it again from the AI)" % e)
            return _queued(rid, job_id, what)
        if caller is None:         # the client claims forms but this call cannot show one, and there is nobody to log in
            confirm.void(platform_path, rid, why)
            return _no(nobody)
    base = store.get_meta(platform_path, "web_base_url") or DEFAULT_WEB_BASE
    url = "%s/c/%s" % (base.rstrip("/"), rid)
    unreachable = ""
    if remote and _is_loopback_url(base):
        unreachable = ("⚠ 這個網址目前只有在平台那台機器上才打得開（%s 是本機位址），你從別的電腦連進來所以打不開。請平台管理者用 "
                       "`abf-platform web --public-url https://<大家打得開的位址>` 設定公開網址（要有 https）。 (this address only opens on the "
                       "platform machine; the administrator must run `abf-platform web --public-url https://<address people can open>`) ")
        unreachable = unreachable % base
    return {"ok": True, "sent": False, "state": "pending", "id": rid, "confirmation_url": url, "summary": text,
            "message": unreachable + "還沒送出 (not sent yet)。請本人打開這個網址、用自己的帳號登入、看過摘要後按「送出」：%s ——按了之後，用同樣的參數再呼叫 `%s` "
                       "一次，就會得到工作編號。AI 不能代按。 (open the address, log in as yourself and press 送出; then call `%s` "
                       "again with the same arguments)" % (url, tool, tool)}


def caller_area(platform_path, caller):
    """The real path of the caller's own upload folder, <uploads_root>/<caller name>: the one area a samplesheet and the path cells
    in it must lie in over HTTP. Symlinks are resolved. build.Refusal when the name cannot be the name of a folder."""
    area = os.path.realpath(os.path.join(str(store.uploads_root(platform_path)), caller.name))
    name = caller.name
    if not name or name in (".", "..") or "/" in name or "\\" in name or chr(0) in name:
        raise build.area_refusal(area)
    return area


def confined_samplesheet(platform_path, caller, samplesheet):
    """The samplesheet of an HTTP caller as a real path inside <uploads_root>/<caller name>/ (a relative path means that folder),
    or build.Refusal. Symlinks are resolved first, so a link cannot lead out. The refusal names the caller's own folder and
    nothing else: not the path that was given, not another folder, not any content."""
    area = os.path.realpath(os.path.join(str(store.uploads_root(platform_path)), caller.name))
    refusal = build.Refusal("samplesheet 必須是你自己上傳資料夾裡的檔案：%s (the samplesheet must be a file inside your own uploads folder)" % area)
    name = caller.name
    if not name or name in (".", "..") or "/" in name or "\\" in name or chr(0) in name:
        raise refusal
    if not isinstance(samplesheet, str) or not samplesheet or chr(0) in samplesheet:
        raise refusal
    joined = samplesheet if os.path.isabs(samplesheet) else os.path.join(area, samplesheet)
    real = os.path.realpath(joined)
    if real == area or not real.startswith(area + os.sep):
        raise refusal
    return real


def read_confined_samplesheet(platform_path, caller, samplesheet):
    """The bytes of the caller's samplesheet, read once: the path is checked (confined_samplesheet), then opened without following a
    link at the end, so a link swapped in after the check is refused and not read. build.Refusal otherwise."""
    real = confined_samplesheet(platform_path, caller, samplesheet)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(real, flags)
    except OSError:
        raise build.Refusal("samplesheet 讀不到，或不是你自己上傳資料夾裡的一般檔案 (cannot read the samplesheet as a plain file in your own uploads folder)")
    with os.fdopen(fd, "rb") as f:
        return f.read()


_MAX_SAMPLESHEET_TEXT = 1024 * 1024        # bytes of UTF-8


def _samplesheet_text_problem(samplesheet, samplesheet_text):
    """Why the way the samplesheet was given cannot be used (exactly one of the file path and the CSV text, the text a non-empty str of at
    most 1 MiB without a NUL), else None. The words are said to the person as they are."""
    if (samplesheet is None) == (samplesheet_text is None):
        return "samplesheet 與 samplesheet_text 只能給一個 (give exactly one of samplesheet and samplesheet_text)"
    if samplesheet_text is None:
        return None
    if not isinstance(samplesheet_text, str):
        return "samplesheet_text 必須是 CSV 文字 (samplesheet_text must be the CSV text as a string)"
    if not samplesheet_text.strip():
        return "samplesheet_text 是空的；請給 CSV 的內容 (samplesheet_text is empty; give the CSV content)"
    if chr(0) in samplesheet_text:
        return "samplesheet_text 含有 NUL 字元，不是 CSV 文字；請檢查內容 (samplesheet_text contains a NUL character)"
    try:
        size = len(samplesheet_text.encode("utf-8"))
    except UnicodeEncodeError:
        return "samplesheet_text 不是有效的文字；請給 UTF-8 的 CSV (samplesheet_text is not valid text; give UTF-8 CSV)"
    if size > _MAX_SAMPLESHEET_TEXT:
        return "samplesheet_text 太大（上限 1 MiB）；請縮小，或改用上傳的檔案 (samplesheet_text is too large: at most 1 MiB)"
    return None


async def request_launch(platform_path, *, pipeline, revision, run_name, samplesheet=None, samplesheet_text=None, ce_name=None, params=None,
                         path_columns=None, caller=None, person=None, clock=time.time, remote=False):
    """Ask for a launch the way the terminal command does: same choices, same bundle, same screen, same refusals. Writes a pending
    request and asks the person; the answer says whether a job exists. Nothing is queued without a person's yes. The samplesheet is
    given as a file (`samplesheet`) or as the CSV itself (`samplesheet_text`, read from memory, never written), exactly one of the two."""
    problem = _samplesheet_text_problem(samplesheet, samplesheet_text)
    if problem:
        return _no("未送出：%s" % problem)
    if params is not None and not isinstance(params, dict):
        return _no("params 必須是名稱到值的對照 (params must be a mapping)")
    if path_columns is not None and (not isinstance(path_columns, list) or not all(isinstance(c, str) for c in path_columns)):
        return _no("path_columns 必須是文字清單 (path_columns must be a list of names)")
    try:
        raw, area = _sheet_and_area(platform_path, samplesheet, samplesheet_text, caller)
        ce, bundle = build.prepare_launch(platform_path, ce=ce_name, pipeline=pipeline, revision=revision, run_name=run_name,
                                          samplesheet=samplesheet, params=params, path_columns=path_columns, check_name=False,
                                          samplesheet_raw=raw, owner=_caller_id(caller), area=area)
    except build.Refusal as e:
        return _no("未送出：%s" % e)
    return await _finish_launch(platform_path, ce, bundle, caller, person, clock, remote)


def _sheet_and_area(platform_path, samplesheet, samplesheet_text, caller):
    """(the samplesheet as bytes or None, the caller's upload area or None) for a launch of either kind. build.Refusal when the file
    is not the caller's own."""
    raw = area = None
    if samplesheet_text is not None:
        raw = samplesheet_text.encode("utf-8")      # no file: the rows come from the text, and the cells are judged as for a file
    if caller is not None:         # over HTTP the file must be the caller's own, and is read once; stdio and the terminal read the path as given
        if raw is None:
            raw = read_confined_samplesheet(platform_path, caller, samplesheet)
        area = caller_area(platform_path, caller)      # a path cell in the upload area must be in it (116); the environment must be the caller's too
    return raw, area


async def _finish_launch(platform_path, ce, bundle, caller, person, clock, remote):
    """The back half of every launch request: the yes that already exists, the run name, the screen, the question. Both entries end here."""
    found = confirm.find_approved(platform_path, "launch", bundle, _caller_id(caller), clock, include_spent=True)
    if found:
        return _queued(found["id"], found["job_id"], bundle["run_name"])
    try:
        jobs.check_run_name(platform_path, bundle["run_name"], clock, _caller_id(caller))
    except jobs.JobRefused as e:
        return _no("未送出：%s" % e)
    text = build.as_text(build.launch_screen(bundle, ce))
    return await _ask(platform_path, "launch", ce, bundle, text, bundle["run_name"], caller, person, clock, remote)


async def request_pipeline_launch(platform_path, *, pipeline_id, version=None, run_name, samplesheet=None, samplesheet_text=None, ce_name=None,
                                  params=None, caller=None, person=None, clock=time.time, remote=False, data=None):
    """Ask for the launch of a saved pipeline of the caller's the way request_launch asks for an nf-core one: the same question, the same
    page, the same hash. The pipeline is named by its number and version (the newest when none is given); the check of today must show
    no error; what is not the caller's answers like what does not exist. `data` is a replacement of the module list, for tests."""
    problem = _samplesheet_text_problem(samplesheet, samplesheet_text)
    if problem:
        return _no("未送出：%s" % problem)
    if params is not None and not isinstance(params, dict):
        return _no("params 必須是名稱到值的對照 (params must be a mapping)")
    try:
        raw, area = _sheet_and_area(platform_path, samplesheet, samplesheet_text, caller)
        ce, bundle = pipeline_launch.prepare(platform_path, pipeline_id=pipeline_id, version=version, run_name=run_name, samplesheet=samplesheet,
                                             samplesheet_raw=raw, ce=ce_name, params=params, caller=caller, area=area, data=data)
    except build.Refusal as e:
        return _no("未送出：%s" % e)
    return await _finish_launch(platform_path, ce, bundle, caller, person, clock, remote)


async def request_cancel(platform_path, *, run_name, caller=None, person=None, clock=time.time, remote=False):
    """Ask for the cancel of one run of this platform, the way the terminal command does."""
    try:
        ce, bundle, row = build.prepare_cancel(platform_path, run_name, owner=_caller_id(caller))
    except build.Refusal as e:
        return _no("未取消：%s" % e)
    if caller is not None and not confirm.launched_by(platform_path, run_name, caller.user_id):
        return _no("未取消：%s 不是你從這個平台送出的（hand-off 紀錄裡沒有你的送出確認）(not launched from this platform by you)" % run_name)
    found = confirm.find_cancel(platform_path, bundle, _caller_id(caller))
    if found:
        return _queued(found["id"], found["job_id"], run_name)
    text = build.as_text(build.cancel_screen(bundle, row))
    return await _ask(platform_path, "cancel", ce, bundle, text, run_name, caller, person, clock, remote)


async def _request_attempt(verb, platform_path, run_name, caller, person, clock, remote, index_path):
    word = build.WORDS[verb]
    caller_id = _caller_id(caller)
    found = confirm.find_attempt(platform_path, run_name, verb, caller_id, clock)
    if found:
        return _queued(found["id"], found["job_id"], found["run_name"])
    prepare, screen = (build.prepare_resume, build.resume_screen) if verb == "resume" else (build.prepare_relaunch, build.relaunch_screen)
    try:
        area = caller_area(platform_path, caller) if caller is not None else None      # over HTTP the samples must still be in the caller's folder (116b)
        ce, bundle, row = prepare(platform_path, run_name, index_path=index_path or store.default_index_path(), owner=caller_id, area=area)
    except build.Refusal as e:
        return _no("未%s：%s" % (word, e))
    text = build.as_text(screen(bundle, row))
    return await _ask(platform_path, "launch", ce, bundle, text, bundle["run_name"], caller, person, clock, remote, tool=verb)


async def request_resume(platform_path, *, run_name, caller=None, person=None, clock=time.time, remote=False, index_path=None):
    """Ask for the resume of a failed or cancelled run of this platform: the same folder, Nextflow goes on where it stopped, the samples and
    parameters of the first launch. The only argument is the name of the run. Nothing is queued without a person's yes."""
    return await _request_attempt("resume", platform_path, run_name, caller, person, clock, remote, index_path)


async def request_relaunch(platform_path, *, run_name, caller=None, person=None, clock=time.time, remote=False, index_path=None):
    """Ask for the relaunch of a failed or cancelled run: a new folder under a new name, the same samples and parameters, from the start."""
    return await _request_attempt("relaunch", platform_path, run_name, caller, person, clock, remote, index_path)


def approve(platform_path, request_id, *, confirmed_by, caller=None, clock=time.time, deadline_seconds=None, offline_after=None):
    """A person said yes to a pending request: through their client's form (ELICITED) or by pressing the button of the page as
    the user who made it (PAGE). Returns (request id, job id); NotApproved when nothing was queued."""
    if not (confirmed_by is ELICITED or confirmed_by is PAGE):
        raise jobs.JobRefused("no human confirmation channel")
    return confirm.approve(platform_path, request_id, confirmed_by.name, _caller_id(caller), clock, deadline_seconds, offline_after)


def find_approved(platform_path, kind, bundle, *, caller=None, clock=time.time):
    """{'id', 'job_id'} of the live yes this caller got for exactly this content, or None."""
    return confirm.find_approved(platform_path, kind, bundle, _caller_id(caller), clock)


def describe_request(platform_path, request_id, *, clock=time.time):
    """What the page may say about a request (its state, its text, its owner, its job), or None; never the bundle."""
    return confirm.describe(platform_path, request_id, clock)


def request_facts(platform_path, request_id):
    """The plain facts of one request for the top of the confirmation page (kind, run name, pipeline, version, environment, samples, new folder), or None."""
    return confirm.facts(platform_path, request_id)


def void_request(platform_path, request_id, reason):
    """Make a pending request void for good; whether it was pending."""
    return confirm.void(platform_path, request_id, reason)


# ---- forget: the owner deletes what a run was sent with (keep-submissions) ---------------------------------------------------------

FORGETTABLE = ("succeeded", "failed", "aborted")      # the stored final statuses; running and lost are not
RUN_NOT_FOUND = "找不到這個 run (run not found)"       # the same words for a run that is not yours and one that is not there (#116)
FORGET_NO_FORM = ("這個客戶端無法跳出確認視窗；請在終端機執行 abf-platform forget <run> "
                  "(this client cannot show a confirmation form; use the terminal command)")
FORGET_STARTING = "這個 run 還在準備中，不能刪除 (the run is still starting)"
FORGET_ALREADY = "已經刪除過了 (already deleted)"


def _forgot(ok, message, forgotten=False, **more):
    return dict(more, ok=ok, forgotten=forgotten, message=message)


FORGET_WAIT_SECONDS = 24 * 3600      # how long a launch that went out may take to show in the run index (F4); worked out from the job, never stored


def _went_out_lately(job):
    finished = job["finished_at"]
    return finished is None or time.time() - finished < FORGET_WAIT_SECONDS


def forget_check(platform_path, index_path, run_name, *, caller=None):
    """(code, message) for forgetting one run: 'ok' (there is content to clear), 'nothing' (already deleted), 'refused' (not now)
    or 'notfound'. Reads only. With a caller (HTTP, or stdio with an account) only that user's own runs are there."""
    con = store.open_readonly(platform_path)
    try:
        launch = jobs.latest_launch(con, run_name) if con is not None and isinstance(run_name, str) else None
        job = (con.execute("SELECT state, finished_at FROM jobs WHERE id = ?", (launch["job_id"],)).fetchone()
               if launch is not None and "job_id" in launch.keys() and launch["job_id"] is not None else None)
    finally:
        if con is not None:
            con.close()
    if launch is None or (caller is not None and run_name not in jobs.owned_run_names(platform_path, caller.user_id)):
        return "notfound", RUN_NOT_FOUND
    seen = [v for v in status.list_runs(index_path, status.now()) if v["name"] == run_name]
    if not seen and job is not None and (job["state"] in ("queued", "claimed") or (job["state"] == "done" and _went_out_lately(job))):
        # R15: "starting" is a launch job still queued or claimed. A launch that ended without ever reaching the index (refused,
        # failed, expired) may be forgotten. F4: so may one whose job went out (done) more than 24 hours ago and the index still does
        # not know; before that the index may only be late. F7: with no job row to read (pruned) the run is treated as never having reached the index.
        return "refused", FORGET_STARTING
    if any(v["status"] == "running" for v in seen):
        return "refused", "這個 run 還在跑，不能刪除 (the run is still running; it cannot be deleted)"
    if any(v["status"] not in FORGETTABLE for v in seen):
        return "refused", "這個 run 失聯了，可能還在叢集上跑，不能刪除 (the run is lost and may still be running; it cannot be deleted)"
    try:
        count = confirm.forget_content(platform_path, run_name, only_user=_caller_id(caller), dry_run=True)
    except jobs.JobRefused as e:
        return "refused", str(e)
    return ("ok", "") if count else ("nothing", FORGET_ALREADY)


def forget(platform_path, index_path, run_name, *, confirmed_by, caller=None, clock=time.time):
    """Clear the content of one run (its confirmations' bundle and screen, and the copy its jobs keep), after a person's yes through
    `confirmed_by`. The audit columns stay, and so do the run and its results. Nothing is queued and no confirmation row is written."""
    _require_human(confirmed_by)
    code, message = forget_check(platform_path, index_path, run_name, caller=caller)
    if code != "ok":
        return _forgot(code == "nothing", message, state=code)
    try:
        count = confirm.forget_content(platform_path, run_name, forgotten_by=_caller_id(caller), only_user=_caller_id(caller), clock=clock)
    except jobs.JobRefused as e:
        return _forgot(False, str(e), state="refused")
    return _forgot(True, "已刪除 %s 送出的內容（%d 筆）；紀錄（誰、何時送出）保留 (deleted the submitted content of %s: %d rows; the record stays)"
                   % (run_name, count, run_name, count), forgotten=True, state="forgotten", cleared=count)


async def request_forget(platform_path, index_path, *, run_name, caller=None, person=None, clock=time.time):
    """Ask the person, in their client's own form, to delete the content of one run. Only the form: a client with no form (or an HTTP
    client whose form is not trusted) is sent to the terminal command, and nothing is written."""
    code, message = forget_check(platform_path, index_path, run_name, caller=caller)
    if code != "ok":
        return _forgot(code == "nothing", message, state=code)
    if not (person is not None and person.can_ask() and form_is_trusted(caller)):
        return _forgot(False, FORGET_NO_FORM, state="no_form")
    yes, why = await person.says_yes(build.as_text(build.forget_screen(run_name)))
    if yes is None:
        return _forgot(False, FORGET_NO_FORM, state="no_form")
    if not yes:
        return _forgot(False, "未刪除：%s (not deleted)" % why, state="declined")
    return forget(platform_path, index_path, run_name, confirmed_by=ELICITED, caller=caller, clock=clock)
