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
import time

from abf_launch import build

from .. import agents, compute_envs, confirm, jobs, status, store, su

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
    return {"runs": status.list_runs(index_path, status.now(), names=names)}


def get_run(index_path, run_id, *, caller=None, platform_path=None):
    view = status.get_run(index_path, run_id, status.now())
    if view is not None and caller is not None and view["name"] not in jobs.owned_run_names(
            platform_path_for(index_path, platform_path), caller.user_id):
        view = None
    if view is None:
        return {"found": False, "id": run_id,
                "message": "Run not found: %s (找不到這個 run)" % run_id}
    return view


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
    if site is None and isinstance(rates, dict):
        site = rates.get("default_site")        # the one site the rates file names as the default
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


# ---- write: only after a human's yes -------------------------------------------------------------------------------------

def _require_human(confirmed_by):
    if not (confirmed_by is TERMINAL or confirmed_by is ELICITED or confirmed_by is PAGE):
        raise jobs.JobRefused("no human confirmation channel")


def launch(state_path, ce_name, bundle, *, confirmed_by, clock=time.time, deadline_seconds=None, offline_after=None,
           caller=None):
    """Queue a launch of exactly `bundle`. Returns (confirmation id, job id)."""
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


async def request_launch(platform_path, *, pipeline, revision, run_name, samplesheet, ce_name=None, params=None, path_columns=None,
                         caller=None, person=None, clock=time.time, remote=False):
    """Ask for a launch the way the terminal command does: same choices, same bundle, same screen, same refusals. Writes a pending
    request and asks the person; the answer says whether a job exists. Nothing is queued without a person's yes."""
    if params is not None and not isinstance(params, dict):
        return _no("params 必須是名稱到值的對照 (params must be a mapping)")
    if path_columns is not None and (not isinstance(path_columns, list) or not all(isinstance(c, str) for c in path_columns)):
        return _no("path_columns 必須是文字清單 (path_columns must be a list of names)")
    try:
        raw = area = None
        if caller is not None:         # over HTTP the file must be the caller's own, and is read once; stdio and the terminal read the path as given
            raw = read_confined_samplesheet(platform_path, caller, samplesheet)
            area = caller_area(platform_path, caller)      # and so must every path cell in it (116); the environment must be the caller's too
        ce, bundle = build.prepare_launch(platform_path, ce=ce_name, pipeline=pipeline, revision=revision, run_name=run_name,
                                          samplesheet=samplesheet, params=params, path_columns=path_columns, check_name=False,
                                          samplesheet_raw=raw, owner=_caller_id(caller), area=area)
    except build.Refusal as e:
        return _no("未送出：%s" % e)
    found = confirm.find_approved(platform_path, "launch", bundle, _caller_id(caller), clock, include_spent=True)
    if found:
        return _queued(found["id"], found["job_id"], bundle["run_name"])
    try:
        jobs.check_run_name(platform_path, bundle["run_name"], clock, _caller_id(caller))
    except jobs.JobRefused as e:
        return _no("未送出：%s" % e)
    text = build.as_text(build.launch_screen(bundle, ce))
    return await _ask(platform_path, "launch", ce, bundle, text, bundle["run_name"], caller, person, clock, remote)


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


def void_request(platform_path, request_id, reason):
    """Make a pending request void for good; whether it was pending."""
    return confirm.void(platform_path, request_id, reason)
