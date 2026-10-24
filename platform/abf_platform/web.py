# Not Starlette's SessionMiddleware or an OAuth login: they keep the whole session in the cookie, or hand login to another service; this is six routes, a password hash that only a terminal can set, and a cookie whose id is kept as a hash.
"""The confirmation page (spec 009c): where a person presses 送出, as the same user that the AI asked for.

A separate small app (`abf-platform web`), not part of the MCP server's bearer check and not part of the receiver: a browser has no
bearer token and must never be given one. Spec 011a added the first pages that show anything but a login or one request, after web design v1 (DESIGN.md): GET /, the
three-column board (web design v2: left: my runs grouped by project; middle: the five-stage board of one run; right: that run's formal
notice; English with ?lang=en), and GET /settings (every section still to come), read-only and for the logged-in user's own runs only.
The only routes there are:

  GET  /             the board (spec 011a): the run that needs the person most (else the newest), or with ?run=<id> that run, ?stage=<name> its stage, ?tab=<name> a tab of its running stage page (011b), ?lang=en the English page; needs the cookie
  GET  /launch       the launch form (spec 012b), ?from=<run id> fills it from an earlier run of the same person; needs the cookie
  POST /launch       check the form and ASK for the launch (request_launch), then 303 to /c/<id>; the CSRF token of this login
  POST /act/{verb}   resume, relaunch or cancel one run (request_resume, request_relaunch, request_cancel), then 303 to /c/<id>; a refusal is a line on the run's page
  GET  /usage        the cost page (cost-page): SU, cloud used / cap / remaining, one line per analysis; ?month=YYYY-MM, ?lang=en; needs the cookie
  GET  /settings     the settings frame (spec 011a): read-only, every section greyed "coming later"; needs the cookie
  GET  /login        the login form (name + web password)
  POST /login        log in; the password is checked against its scrypt hash; a cookie of 12 hours
  POST /logout       end this browser login
  GET  /c/{rid}      the summary of one pending request, for the user who made it; never changes anything
  POST /c/{rid}      the button: needs the cookie, the same user as the request, and the CSRF token of this login and this request

and, since spec 009i, the authorization server a Claude Desktop connector logs in through (abf_platform.oauth, the SDK's handlers):

  GET  /.well-known/oauth-authorization-server, POST /register, GET|POST /authorize, POST /token, POST /revoke   (the connector's own calls)
  GET  /consent/{rid}   the consent page: who is asking, Allow / Deny; needs this same login, never changes anything
  POST /consent/{rid}   Allow or Deny: needs the cookie and the CSRF token of this login and this request; writes no confirmation

`Authorization: Bearer` is never looked at here: an AI that holds a personal access token cannot log in, cannot read a summary and
cannot press the button. The cookie is `<random id>.<signature>`; only the sha256 of the id is stored (tokens.db, web_sessions).
Everything the page shows is escaped, and a content-security-policy forbids scripts anyway; its style-src is the sha256 of the one
stylesheet (web_board.STYLE). Rendering is in web_board.py; this file keeps the routes and the login.
"""
import hashlib
import hmac
import html
import os
import re
import sqlite3
import tempfile
import time
import urllib.parse
from pathlib import Path

from mcp.server.auth.handlers.metadata import MetadataHandler
from mcp.server.auth.routes import build_metadata, cors_middleware, create_auth_routes
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route

from . import actions, oauth, store, web_board, web_cost

COOKIE = "abf_web"
KEY_FILE = "web_signing.key"
RID = re.compile(r"^[0-9a-f]{32}\Z")
NEXT = re.compile(r"^/(c|consent)/[0-9a-f]{32}\Z")        # where a login may send the browser next: one of this app's own pages
DEFAULT_BASE = "http://127.0.0.1:8789"
FAIL_LIMIT = 5              # failures within FAIL_WINDOW that block one name
IP_FAIL_LIMIT = 20          # failures within FAIL_WINDOW that block one client address (many names from one address)
FAIL_WINDOW = 60.0
MAX_TRACKED = 10000         # names (and addresses) with a live failure window; past this, new ones are refused, no live counter is dropped
MAX_NAME_CHARS = 100
MAX_BODY = 16384
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
_HEADERS = {"Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src %s; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
            % web_board.style_source()}
_PLAIN = {      # the labels of the plain block at the top of the confirmation page
    "zh": {"kind": "種類", "launch": "送出新分析", "resume": "續跑", "relaunch": "重跑", "cancel": "取消", "run": "run 名稱", "pipeline": "管線",
           "version": "版本", "env": "環境", "samples": "樣本數", "folder": "新資料夾", "full": "完整內容（技術細節）"},
    "en": {"kind": "Request", "launch": "New analysis", "resume": "Continue the run", "relaunch": "Re-run", "cancel": "Cancel", "run": "Run name",
           "pipeline": "Pipeline", "version": "Version", "env": "Environment", "samples": "Samples", "folder": "New folder",
           "full": "Full content (technical)"}}
HOME = "/"                  # where a login with no (or a refused) `next` goes: a constant, so there is no open redirect


KEY_MIN_BYTES = 32


def _signing_key(folder):
    """The key that signs cookies and CSRF tokens: made once, written whole to a temporary file and linked into place (so a start
    never sees half a key and two starts end with one key), owner-only, kept next to the databases, never printed. A key file of
    fewer than 32 bytes is refused (ValueError): there is no empty-key path."""
    path = Path(folder) / KEY_FILE
    Path(folder).mkdir(parents=True, exist_ok=True)
    if not path.exists():
        fd, tmp = tempfile.mkstemp(prefix=".key-", dir=str(folder))
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(os.urandom(32).hex().encode("ascii") + b"\n")
            try:
                os.chmod(tmp, 0o600)
            except OSError:
                pass
            try:
                os.link(tmp, str(path))          # atomic, and never replaces a key another start made first
            except FileExistsError:
                pass
            except OSError:
                if not path.exists():
                    os.replace(tmp, str(path))
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    key = path.read_bytes().strip()
    if len(key) < KEY_MIN_BYTES:
        raise ValueError("the signing key file %s has fewer than %d bytes; delete it and start again (簽章金鑰檔太短，拒絕啟動)" % (path, KEY_MIN_BYTES))
    return key


def _mac(key, *parts):
    return hmac.new(key, "\x1f".join(parts).encode("utf-8"), hashlib.sha256).hexdigest()


def _same(a, b):
    """Constant-time equality of two texts as bytes: compare_digest on str raises for a non-ASCII value, which would be a 500."""
    return hmac.compare_digest(str(a).encode("utf-8", "replace"), str(b).encode("utf-8", "replace"))


def _esc(text):
    return html.escape(str(text), quote=True)


def _page(title, body, status=200, form_action=None):
    headers = _HEADERS
    if form_action:        # the consent form ends in a redirect to the connector, which a form-action rule also covers
        headers = dict(_HEADERS, **{"Content-Security-Policy": _HEADERS["Content-Security-Policy"].replace("form-action 'self'", "form-action 'self' " + form_action)})
    return HTMLResponse(web_board.document(title, "<h1>%s</h1>%s" % (_esc(title), body)), status_code=status, headers=headers)


def _login_form(next_path="", message="", status=200):
    note = "<p class=\"bad\">%s</p>" % _esc(message) if message else ""
    nxt = "<input type=\"hidden\" name=\"next\" value=\"%s\">" % _esc(next_path) if next_path else ""
    limit = "（%d 到 %d 個字元 / %d to %d characters）" % (store.MIN_PASSWORD_CHARS, store.MAX_PASSWORD_CHARS,
                                                     store.MIN_PASSWORD_CHARS, store.MAX_PASSWORD_CHARS)
    return _page("登入 (log in)", note + "<p>請用你的姓名與<strong>網頁密碼</strong>登入（網頁密碼不是 AI 用的權杖；它只能在終端機用 "
                 "<code>abf-platform user passwd</code> 設定）。</p><form method=\"post\" action=\"/login\">"
                 "<p><label>姓名 <input name=\"name\" autocomplete=\"username\" required></label></p>"
                 "<p><label>密碼 <input name=\"password\" type=\"password\" autocomplete=\"current-password\" required></label> "
                 "<small>" + _esc(limit) + "</small></p>"
                 + nxt + "<p><button type=\"submit\">登入</button></p></form>", status)


def _form(fields):
    out = urllib.parse.parse_qs(fields, keep_blank_values=True, max_num_fields=50)
    return {k: v[0] for k, v in out.items()}


def create_app(index_path, tokens_path=None, platform_path=None, *, clock=time.time, public_url=None, base_url=None):
    """The confirmation page and the OAuth authorization server as an ASGI app. `clock` and the files are parameters so a test can move
    time and use its own folder. The issuer of the OAuth metadata is `public_url`, else `base_url` (where this app listens), else the default
    loopback address; the SDK refuses a plain-http issuer that is not loopback (ValueError)."""
    tokens_path = tokens_path or store.default_tokens_path(index_path)
    platform_path = actions.platform_path_for(index_path, platform_path)
    key = _signing_key(Path(platform_path).parent)
    parsed = urllib.parse.urlparse(public_url or "")
    secure = parsed.scheme == "https" and (parsed.hostname or "") not in LOOPBACK_HOSTS
    if public_url:
        store.set_meta(platform_path, "web_base_url", public_url.rstrip("/"))     # the MCP server names this address in its answers
    by_name, by_ip = {}, {}          # key -> times of failures inside the window; a key with a live window is never dropped

    def cookie_value(sid):
        return "%s.%s" % (sid, _mac(key, "cookie", sid))

    def session_id(request):
        raw = request.cookies.get(COOKIE) or ""
        sid, dot, sig = raw.partition(".")
        if not dot or not sid or not _same(sig, _mac(key, "cookie", sid)):
            return None
        return sid

    def user_of(request):
        sid = session_id(request)
        return (sid, store.web_session_user(tokens_path, sid, clock())) if sid else (None, None)

    def csrf(sid, rid):
        return _mac(key, "csrf", sid, rid)

    def csrf_token(cookie, rid):
        return csrf(cookie.split(".")[0], rid)

    def recent(table, key, now):
        live = [t for t in table.get(key, ()) if now - t < FAIL_WINDOW]
        if live:
            table[key] = live
        else:
            table.pop(key, None)
        return live

    def no_room(table, key, now):
        """True when `key` would be a new entry and the table is full of live windows (expired ones are removed first)."""
        if key in table or len(table) < MAX_TRACKED:
            return False
        for k in list(table):
            recent(table, k, now)
        return key not in table and len(table) >= MAX_TRACKED

    def same_origin(request):
        """A POST from a browser carries Origin (or at least Referer); it must be this page's own origin or the public address."""
        seen = request.headers.get("origin")
        if seen is None:
            seen = request.headers.get("referer")
        if seen is None:
            return True            # not a browser (a browser always sends one of the two on a POST); the cookie and the CSRF token still apply
        allowed = {request.headers.get("host", "").lower()}
        if parsed.netloc:
            allowed.add(parsed.netloc.lower())
        return urllib.parse.urlparse(seen).netloc.lower() in allowed and seen != "null"

    def foreign(request):
        return _page("來源不符 (wrong origin)", "<p class=\"bad\">這個表單不是從本頁送出的，什麼都沒有改。</p>", 403)

    async def body_of(request):
        raw = b""
        async for chunk in request.stream():
            raw += chunk
            if len(raw) > MAX_BODY:
                break
        return _form(raw[:MAX_BODY].decode("utf-8", errors="replace"))

    async def login_form(request):
        nxt = request.query_params.get("next", "")
        return _login_form(nxt if NEXT.match(nxt) else "")

    async def login_post(request):
        if not same_origin(request):
            return foreign(request)
        form = await body_of(request)
        raw_name = str(form.get("name", ""))
        name = raw_name[:MAX_NAME_CHARS]
        password = str(form.get("password", ""))
        ip = request.client.host if request.client else ""
        nxt = form.get("next", "")
        nxt = nxt if NEXT.match(nxt) else ""
        now = clock()
        if (len(recent(by_name, name, now)) >= FAIL_LIMIT or len(recent(by_ip, ip, now)) >= IP_FAIL_LIMIT
                or no_room(by_name, name, now) or no_room(by_ip, ip, now)):
            return _login_form(nxt, "登入失敗太頻繁，請一分鐘後再試 (too many tries, wait a minute)", 429)
        who = None
        too_long = len(password) > store.MAX_PASSWORD_CHARS or len(raw_name) > MAX_NAME_CHARS
        # The attempt is counted before the slow check, in the same step as the limit check (no await between them), so parallel
        # requests cannot all pass the check while the first is still hashing; a right password takes its own entry back.
        by_name.setdefault(name, []).append(now)
        by_ip.setdefault(ip, []).append(now)
        if not too_long:
            who = await run_in_threadpool(store.check_web_password, tokens_path, name, password)     # scrypt is slow: not on the event loop
        if who is None:
            note = ("密碼最長 %d 個字元，姓名最長 %d (password at most %d characters, name at most %d)"
                    % (store.MAX_PASSWORD_CHARS, MAX_NAME_CHARS, store.MAX_PASSWORD_CHARS, MAX_NAME_CHARS)
                    if too_long else "姓名或密碼不對 (wrong name or password)")
            return _login_form(nxt, note, 401)
        for table, k in ((by_name, name), (by_ip, ip)):
            if now in table.get(k, ()):
                table[k].remove(now)
            if not table.get(k, True):
                table.pop(k, None)
        sid, _ = store.create_web_session(tokens_path, who["user_id"], now)
        response = RedirectResponse(nxt or HOME, status_code=303, headers=_HEADERS)
        response.set_cookie(COOKIE, cookie_value(sid), max_age=int(store.WEB_SESSION_SECONDS), httponly=True, samesite="Strict",
                            secure=secure, path="/")
        return response

    async def logout_post(request):
        if not same_origin(request):
            return foreign(request)
        sid = session_id(request)
        form = await body_of(request)
        if sid and _same(form.get("csrf", ""), csrf(sid, "logout")):
            store.end_web_session(tokens_path, sid)
        response = RedirectResponse("/login", status_code=303, headers=_HEADERS)
        response.delete_cookie(COOKIE, path="/")
        return response

    def view_of(rid, user):
        """(response or None, request description) for a logged-in user and an address."""
        req = actions.describe_request(platform_path, rid, clock=clock)
        if req is None:
            return _page("找不到 (not found)", "<p>沒有這個申請。</p>", 404), None
        if req["caller_user_id"] != user["user_id"]:
            return _page("不是你的申請 (not yours)", "<p class=\"bad\">這個申請不是你送出的，所以這裡不能看也不能按。</p>", 403), None
        return None, req

    def plain_block(rid, lang):
        """The few plain words at the top of the page: what kind of request, which run, pipeline, version, environment, samples, new folder.
        What the action layer does not know is left out, never shown as a dash."""
        facts = actions.request_facts(platform_path, rid)
        if not facts:
            return ""
        t = _PLAIN[lang]
        rows = [(t["kind"], t[facts["what"]])]
        for key, label in (("run_name", "run"), ("pipeline", "pipeline"), ("revision", "version"), ("ce", "env"), ("samples", "samples"),
                           ("folder", "folder")):
            if key in facts:
                rows.append((t[label], facts[key]))
        return "<dl class=\"fields plain\">%s</dl>" % "".join("<dt>%s</dt><dd>%s</dd>" % (_esc(k), _esc(v)) for k, v in rows)

    def state_page(req, sid, rid, lang="zh"):
        title = "送出確認" if req["kind"] == "launch" else "取消確認"
        shown = "<details><summary>%s</summary><pre>%s</pre></details>" % (_PLAIN[lang]["full"], _esc(req["summary"] or ""))
        if req["state"] in ("pending", "confirmed"):
            shown = plain_block(rid, lang) + shown
        if req["state"] == "pending":
            return _page(title, "<p>下面就是會被%s的全部內容。確定了再按「送出」；按了才會排進佇列。</p>%s"
                         "<form method=\"post\" action=\"/c/%s\"><input type=\"hidden\" name=\"csrf\" value=\"%s\">"
                         "<button type=\"submit\">送出</button></form>"
                         % ("送出" if req["kind"] == "launch" else "取消", shown, rid, _esc(csrf(sid, rid))))
        if req["state"] == "confirmed":
            return _page(title, "<p class=\"ok\">已送出。工作編號 %s。</p>%s" % (_esc(req["job_id"]), shown))
        if req["state"] == "expired":
            return _page(title, "<p class=\"bad\">這個申請已逾時（10 分鐘）。請回到 AI 重新送出。</p>")
        return _page(title, "<p class=\"bad\">這個申請已作廢：%s。請回到 AI 重新送出。</p>" % _esc(req["void_reason"] or "-"), 409)

    async def confirm_get(request):
        rid = request.path_params["rid"]
        if not RID.match(rid):
            return _page("找不到 (not found)", "<p>沒有這個網址。</p>", 404)
        sid, user = user_of(request)
        if user is None:
            return _login_form("/c/" + rid)
        answer, req = view_of(rid, user)
        return answer or state_page(req, sid, rid, web_board.pick_lang(request.query_params.get("lang")))

    async def confirm_post(request):
        if not same_origin(request):
            return foreign(request)
        rid = request.path_params["rid"]
        if not RID.match(rid):
            return _page("找不到 (not found)", "<p>沒有這個網址。</p>", 404)
        sid, user = user_of(request)
        if user is None:
            return _login_form("/c/" + rid, "請先登入 (log in first)", 401)
        answer, req = view_of(rid, user)
        if answer is not None:
            return answer
        form = await body_of(request)
        if not _same(form.get("csrf", ""), csrf(sid, rid)):
            return _page("表單已失效", "<p class=\"bad\">這個表單的記號不對或已失效，什麼都沒有送出。請重新整理頁面再按。</p>", 403)
        try:
            _, job_id = actions.approve(platform_path, rid, confirmed_by=actions.PAGE,
                                        caller=actions.Caller(user["user_id"], user["name"], user["lab"]), clock=clock)
        except actions.NotApproved as e:
            if e.status == "already":
                return _page("已送出", "<p class=\"ok\">已送出。工作編號 %s。</p>" % _esc(e.job_id))
            code = {"not_found": 404, "not_yours": 403, "expired": 410}.get(e.status, 409)
            return _page("未送出", "<p class=\"bad\">未送出：%s。請回到 AI 重新送出。</p>" % _esc(e), code)
        return _page("已送出", "<p class=\"ok\">已送出。工作編號 %s。你可以回到 AI，用同樣的參數再呼叫一次，它會告訴你工作編號。</p>" % _esc(job_id))

    def read_runs(caller):
        try:
            return actions.list_runs(index_path, caller=caller, platform_path=platform_path)["runs"]
        except sqlite3.Error:          # an empty or damaged index answers like an empty one; a page is never a 500
            return []

    def read_run(run_id, caller):
        try:
            view = actions.get_run(index_path, run_id, caller=caller, platform_path=platform_path)
        except sqlite3.Error:
            return None
        return None if view.get("found") is False else view

    def read_outputs(run_id, caller, outputs_tab, relist):
        """The output folder of a succeeded run's results stage, from the action (it never waits for the site). Only the Outputs tab asks
        the site; the other tabs only look, for the name of the environment on the card."""
        try:
            return actions.run_outputs(index_path, platform_path, run_id, caller=caller, relist=relist and outputs_tab, enqueue=outputs_tab)
        except sqlite3.Error:
            return None

    async def board_page(sid, user, caller, lang, run_id, stage=None, tab=None, flash=None, code=200, relist=False):
        """The board for one logged-in user: one run's page (the one named, else the one that needs the person most, else the newest;
        an empty page for a person with no run), with `flash` (one plain line of refusal) on it after a refused button."""
        runs = await run_in_threadpool(read_runs, caller)
        selected = None
        outputs = None
        if run_id or runs:
            selected = await run_in_threadpool(read_run, run_id or web_board.default_run(runs), caller)
            if selected is None:        # another person's run and a missing id answer alike, and the page never repeats the id
                return HTMLResponse(web_board.render_not_found(user["name"], lang), status_code=404, headers=_HEADERS)
            if selected["status"] == "succeeded" and web_board.pick_stage(stage, "results") == "results" and not flash:
                outputs = await run_in_threadpool(read_outputs, selected["id"], caller, web_board.pick_results_tab(tab) == "outputs", relist)
        doc = web_board.render_board(user["name"], csrf(sid, "logout"), runs, selected, stage, lang, tab, clock(),
                                     act_csrf=lambda rid: csrf(sid, "act:" + rid), flash=flash, outputs=outputs)
        return HTMLResponse(doc, status_code=code, headers=_HEADERS)

    async def board(request):
        sid, user = user_of(request)
        if user is None:
            return RedirectResponse("/login", status_code=303, headers=_HEADERS)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        lang = web_board.pick_lang(request.query_params.get("lang"))
        return await board_page(sid, user, caller, lang, request.query_params.get("run") or "", request.query_params.get("stage"),
                                request.query_params.get("tab"), relist=request.query_params.get("relist") == "1")

    # ---- spec 012b: write actions from the web. Every route here only ASKS: it calls a request_* action for the logged-in caller and sends
    # the browser to the confirmation page /c/<id>, where the person presses 送出. Nothing is confirmed or queued from here.
    ACT_VERBS = {"resume": actions.request_resume, "relaunch": actions.request_relaunch}

    def to_confirmation(answer):
        """303 to the confirmation page of a request the action layer made (or found already confirmed), else None."""
        if answer.get("ok") and RID.match(str(answer.get("id") or "")):
            return RedirectResponse("/c/" + answer["id"], status_code=303, headers=_HEADERS)
        return None

    async def act_post(request):
        if not same_origin(request):
            return foreign(request)
        verb = request.path_params["verb"]
        sid, user = user_of(request)
        if user is None:
            return RedirectResponse("/login", status_code=303, headers=_HEADERS)
        form = await body_of(request)
        lang = web_board.pick_lang(form.get("lang"))
        run_id = str(form.get("run", ""))[:200]
        if verb not in ("resume", "relaunch", "cancel"):
            return _page("找不到 (not found)", "<p>沒有這個網址。</p>", 404)
        if not _same(form.get("csrf", ""), csrf(sid, "act:" + run_id)):
            return _page("表單已失效 (form expired)", "<p class=\"bad\">%s</p>" % _esc(web_board.STRINGS[lang]["r_form"]), 403)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        view = await run_in_threadpool(read_run, run_id, caller)
        if view is None:
            return HTMLResponse(web_board.render_not_found(user["name"], lang), status_code=404, headers=_HEADERS)
        if verb == "cancel":
            answer = await actions.request_cancel(platform_path, run_name=view["name"], caller=caller, clock=clock)
        else:
            answer = await ACT_VERBS[verb](platform_path, run_name=view["name"], caller=caller, clock=clock, index_path=index_path)
        done = to_confirmation(answer)
        if done is not None:
            return done
        line = web_board.plain_reason(answer.get("message"), lang) + " " + web_board.STRINGS[lang]["r_none"]
        return await board_page(sid, user, caller, lang, run_id, flash=line, code=409)

    def launch_choices(caller):
        sheets = actions.list_samplesheets(platform_path, caller=caller)
        envs = [e["name"] for e in actions.list_compute_envs(platform_path, caller=caller)["compute_envs"]]
        return sheets, envs

    async def launch_page(sid, user, caller, lang, values, errors, notes, source=None, code=200):
        sheets, envs = await run_in_threadpool(launch_choices, caller)
        values = dict(values)
        values.setdefault("samplesheet", sheets[0] if sheets else None)
        values.setdefault("ce_name", envs[0] if envs else None)
        runs = await run_in_threadpool(read_runs, caller)
        doc = web_board.render_launch(user["name"], csrf(sid, "logout"), runs, values, errors, notes, sheets, envs, csrf(sid, "launch"), lang, source)
        return HTMLResponse(doc, status_code=code, headers=_HEADERS)

    async def launch_get(request):
        sid, user = user_of(request)
        if user is None:
            return RedirectResponse("/login", status_code=303, headers=_HEADERS)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        lang = web_board.pick_lang(request.query_params.get("lang"))
        t = web_board.STRINGS[lang]
        origin = request.query_params.get("from") or ""
        values, notes, source = {}, [], None
        if origin:       # quick launch: the boxes of an earlier run of this person, when its content is still kept
            view = await run_in_threadpool(read_run, origin, caller)
            if view is None:
                return HTMLResponse(web_board.render_not_found(user["name"], lang), status_code=404, headers=_HEADERS)
            earlier = await run_in_threadpool(actions.launch_prefill, platform_path, view["name"], caller=caller)
            when = web_board.taipei_time(earlier.get("launched_at"))
            source = (view["id"], view["name"], view["status"], when)
            if earlier.get("kept"):
                values = {"pipeline": earlier.get("pipeline") or "", "revision": earlier.get("revision") or "", "ce_name": earlier.get("ce_name"),
                          "params": web_board.params_text(earlier.get("params"))}
                notes.append(t["l_from"])
            else:
                notes.append(t["l_not_kept"])
        return await launch_page(sid, user, caller, lang, values, [], notes, source)

    async def launch_post(request):
        if not same_origin(request):
            return foreign(request)
        sid, user = user_of(request)
        if user is None:
            return RedirectResponse("/login", status_code=303, headers=_HEADERS)
        form = await body_of(request)
        lang = web_board.pick_lang(form.get("lang"))
        t = web_board.STRINGS[lang]
        if not _same(form.get("csrf", ""), csrf(sid, "launch")):
            return _page("表單已失效 (form expired)", "<p class=\"bad\">%s</p>" % _esc(t["r_form"]), 403)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        sheets, envs = await run_in_threadpool(launch_choices, caller)
        pipeline = str(form.get("pipeline", "")).strip()
        values = {"pipeline": pipeline, "revision": str(form.get("revision", "")).strip(), "run_name": str(form.get("run_name", "")).strip(),
                  "samplesheet": str(form.get("samplesheet", "")), "ce_name": str(form.get("ce_name", "")), "params": str(form.get("params", ""))}
        errors = []
        if not pipeline or not re.match(r"^[A-Za-z0-9._/-]{1,100}\Z", pipeline):
            errors.append(t["e_pipeline"])
        if not values["revision"] or re.search(r"\s", values["revision"]):
            errors.append(t["e_revision"])
        if not values["run_name"]:
            errors.append(t["e_run_name"])
        if values["samplesheet"] not in sheets:
            errors.append(t["e_sheet"])
        if values["ce_name"] not in envs:
            errors.append(t["e_ce"])
        params, bad = web_board.parse_params(values["params"], t)
        errors += bad
        if not errors:
            answer = await actions.request_launch(
                platform_path, pipeline=pipeline if "/" in pipeline else "nf-core/" + pipeline, revision=values["revision"],
                run_name=values["run_name"], samplesheet=values["samplesheet"], ce_name=values["ce_name"], params=params or None,
                caller=caller, clock=clock)
            done = to_confirmation(answer)
            if done is not None:
                return done
            errors.append(web_board.plain_reason(answer.get("message"), lang) + " " + t["r_none"])
        else:
            errors.append(t["e_body"])
        return await launch_page(sid, user, caller, lang, values, errors, [], code=400)

    async def settings(request):
        sid, user = user_of(request)
        if user is None:
            return RedirectResponse("/login", status_code=303, headers=_HEADERS)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        lang = web_board.pick_lang(request.query_params.get("lang"))
        runs = await run_in_threadpool(read_runs, caller)
        return HTMLResponse(web_board.render_settings(user["name"], csrf(sid, "logout"), runs, lang), headers=_HEADERS)


    async def usage_page(request):
        sid, user = user_of(request)
        if user is None:
            return RedirectResponse("/login", status_code=303, headers=_HEADERS)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        lang = web_board.pick_lang(request.query_params.get("lang"))
        month, bad = web_cost.pick_month(request.query_params.get("month"))
        runs = await run_in_threadpool(read_runs, caller)
        try:
            data = await run_in_threadpool(lambda: actions.my_usage(index_path, platform_path, caller=caller, month=month, tokens_path=tokens_path))
        except sqlite3.Error:          # a damaged index answers like an empty month; a page is never a 500
            data = web_cost.empty_usage(month or web_cost.current_month(clock()))
        return HTMLResponse(web_cost.render_usage(user["name"], csrf(sid, "logout"), runs, data, lang, clock(), bad), headers=_HEADERS)


    # ---- the OAuth consent page (spec 009i) -------------------------------------------------------------------------
    issuer = (public_url or base_url or DEFAULT_BASE).rstrip("/")
    provider = oauth.PlatformOAuthProvider(tokens_path, issuer, clock=clock)
    registration = ClientRegistrationOptions(enabled=True, valid_scopes=[oauth.SCOPE], default_scopes=[oauth.SCOPE])
    revocation = RevocationOptions(enabled=True)
    auth_routes = create_auth_routes(provider, AnyHttpUrl(issuer), client_registration_options=registration, revocation_options=revocation)
    # every client here is public (PKCE, no secret): say so in the metadata instead of the SDK's secret-based defaults
    metadata = build_metadata(issuer, None, registration, revocation)
    metadata.token_endpoint_auth_methods_supported = ["none"]
    metadata.revocation_endpoint_auth_methods_supported = ["none"]
    auth_routes = [Route("/.well-known/oauth-authorization-server", endpoint=cors_middleware(MetadataHandler(metadata).handle, ["GET", "OPTIONS"]),
                         methods=["GET", "OPTIONS"]) if r.path == "/.well-known/oauth-authorization-server" else r for r in auth_routes]

    def consent_csrf(sid, rid):
        return csrf(sid, "consent:" + rid)

    def consent_page(info, sid):
        who = info["client_name"] or "(沒有名稱 unnamed)"
        if info["form_ok"]:
            limits = ("<p>允許之後，它可以讀你的 runs，也可以請求送出分析。送出前，它可以在 AI 程式裡跳出「送出」表單，由你本人在表單上按；"
                      "它不能自己代按。 (It can read your runs and ask to launch; the AI app can show you a 送出 form and you press it yourself.)</p>")
        else:
            limits = ("<p>允許之後，它可以讀你的 runs，也可以請求送出分析；但它<strong>不能替你送出</strong>——"
                      "每次送出或取消，都要你本人在這個網站的確認頁按「送出」。 (It can read your runs and ask to launch; it cannot send an analysis: "
                      "each launch or cancel must be confirmed by you on this website.)</p>")
        body = ("<p>名為 <strong>%s</strong> 的連接器（程式代號 %s）要求連到這個平台，並以<strong>你的身分</strong>運作。</p>"
                "<p>它會把你導回：<strong>%s</strong>。如果你不認得這個網站，按「拒絕」。</p>"
                "%s"
                "<form method=\"post\" action=\"/consent/%s\"><input type=\"hidden\" name=\"csrf\" value=\"%s\">"
                "<button type=\"submit\" name=\"decision\" value=\"allow\">允許</button> "
                "<button type=\"submit\" name=\"decision\" value=\"deny\">拒絕</button></form>"
                % (_esc(who), _esc(info["client_id"]), _esc(info["redirect_host"]), limits, info["id"], _esc(consent_csrf(sid, info["id"]))))
        return _page("允許連接器 (allow a connector)", body, form_action=info["redirect_origin"])

    def consent_gone(info):
        if info["decision"] is not None:
            return _page("已處理", "<p>這個申請已經處理過了。請回到連接器重新開始。</p>", 409)
        if info["expired"]:
            return _page("已逾時", "<p class=\"bad\">這個申請已逾時（10 分鐘）。請回到連接器重新開始。</p>", 410)
        return None

    async def consent_get(request):
        rid = request.path_params["rid"]
        info = provider.consent_request(rid) if RID.match(rid) else None
        if info is None:
            return _page("找不到 (not found)", "<p>沒有這個申請。</p>", 404)
        gone = consent_gone(info)
        if gone is not None:
            return gone
        sid, user = user_of(request)
        if user is None:
            return _login_form("/consent/" + rid)
        return consent_page(info, sid)

    async def consent_post(request):
        if not same_origin(request):
            return foreign(request)
        rid = request.path_params["rid"]
        info = provider.consent_request(rid) if RID.match(rid) else None
        if info is None:
            return _page("找不到 (not found)", "<p>沒有這個申請。</p>", 404)
        sid, user = user_of(request)
        if user is None:
            return _login_form("/consent/" + rid, "請先登入 (log in first)", 401)
        form = await body_of(request)
        if not _same(form.get("csrf", ""), consent_csrf(sid, rid)):
            return _page("表單已失效", "<p class=\"bad\">這個表單的記號不對或已失效，什麼都沒有改。請重新整理頁面再按。</p>", 403)
        decision = form.get("decision")
        if decision not in ("allow", "deny"):
            return _page("未處理", "<p class=\"bad\">請按「允許」或「拒絕」。</p>", 400)
        status, location = provider.consent_decide(rid, user["user_id"], decision)
        if location is not None:
            return RedirectResponse(location, status_code=302, headers=_HEADERS)
        gone = consent_gone(provider.consent_request(rid)) if status in ("decided", "expired") else None
        return gone or _page("未處理", "<p class=\"bad\">什麼都沒有改。請回到連接器重新開始。</p>", 403 if status == "user" else 404)

    app = Starlette(routes=[Route("/", board, methods=["GET"]), Route("/settings", settings, methods=["GET"]), Route("/usage", usage_page, methods=["GET"]),
                            Route("/launch", launch_get, methods=["GET"]), Route("/launch", launch_post, methods=["POST"]),
                            Route("/act/{verb}", act_post, methods=["POST"]), Route("/login", login_form, methods=["GET"]), Route("/login", login_post, methods=["POST"]),
                            Route("/logout", logout_post, methods=["POST"]),
                            Route("/c/{rid}", confirm_get, methods=["GET"]), Route("/c/{rid}", confirm_post, methods=["POST"]),
                            Route("/consent/{rid}", consent_get, methods=["GET"]), Route("/consent/{rid}", consent_post, methods=["POST"])]
                    + auth_routes, middleware=[Middleware(oauth.RegisterBodyCap), Middleware(oauth.RegisterRateCap, clock=clock)])
    from starlette.middleware.base import BaseHTTPMiddleware

    async def add_headers(request, call_next):
        """The framework's own 404 and 405 are not made by `_page`: they get the same headers."""
        response = await call_next(request)
        for k, v in _HEADERS.items():
            response.headers.setdefault(k, v)
        return response

    app.add_middleware(BaseHTTPMiddleware, dispatch=add_headers)
    app.state.csrf_token = csrf_token
    return app
