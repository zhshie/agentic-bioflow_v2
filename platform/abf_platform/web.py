# Not Starlette's SessionMiddleware or an OAuth login: they keep the whole session in the cookie, or hand login to another service; this is six routes, a password hash that only a terminal can set, and a cookie whose id is kept as a hash.
"""The confirmation page (spec 009c): where a person presses 送出, as the same user that the AI asked for.

A separate small app (`abf-platform web`), not part of the MCP server's bearer check and not part of the receiver: a browser has no
bearer token and must never be given one. Spec 011a added the first pages that show anything but a login or one request, after web design v1 (DESIGN.md): GET /, the
three-column board (web design v2: left: my runs grouped by project; middle: the five-stage board of one run; right: that run's formal
notice; English with ?lang=en), and GET /settings (every section still to come), read-only and for the logged-in user's own runs only.
The only routes there are:

  GET  /             the board (spec 011a): the run that needs the person most (else the newest), or with ?run=<id> that run, ?stage=<name> its stage, ?tab=<name> a tab of its running stage page (011b), ?lang=en the English page; needs the cookie
  GET  /launch       the launch form (spec 012b), ?from=<run id> fills it from an earlier run of the same person; needs the cookie
  GET  /launch/diagram  the workflow diagram of ?pipeline=&revision= as the image the caller's own agent read from the public repository (guided-launch-2); needs the cookie, 404 as one plain line when it is not there
  POST /launch       check the form and ASK for the launch (request_launch), then 303 to /c/<id>; the CSRF token of this login
  POST /act/{verb}   resume, relaunch or cancel one run (request_resume, request_relaunch, request_cancel), then 303 to /c/<id>; a refusal is a line on the run's page
  GET  /upload       the upload form (web-upload-page): choose a cloud compute environment, name and version the dataset, choose FASTQ files and an optional samplesheet; needs the cookie
  POST /upload       receive the files into a staging folder of the platform host (streamed, 2 GB per file), queue one upload job for each, then 303 to /upload/<batch>; the CSRF token of this login. The person's press of Upload is the yes: no confirmation page
  GET  /upload/{batch}  the progress of one batch of the person's own uploads; when every file is in the bucket it registers the dataset (once)
  GET  /usage        the cost page (cost-page): SU, cloud used / cap / remaining, one line per analysis; ?month=YYYY-MM, ?lang=en; needs the cookie
  GET  /settings     the settings frame (spec 011a): read-only, every section greyed "coming later"; needs the cookie
  GET  /login        the login form (name + web password)
  POST /login        log in; the password is checked against its scrypt hash; a cookie of 12 hours
  POST /logout       end this browser login
  GET  /welcome      the only page a temporary-password login reaches: set your own password (a 303 to / for an ordinary login, to /login for none)
  POST /welcome      set it (old = the temporary password, new, confirm; its own CSRF token; counted in the same failure windows as /login), then 303 to / on the same login
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
import base64
import binascii
import hashlib
import hmac
import html
import os
import re
import secrets
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
from starlette.requests import ClientDisconnect
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from starlette.routing import Route

from . import actions, oauth, store, web_board, web_cost, web_launch, web_settings
from . import uploads_web, web_upload

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
LAUNCH_BODY = 262144      # the launch form (guided-launch-2b): one box for each parameter of the pipeline
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
_HEADERS = {"Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src %s; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
            % web_board.style_source()}
_PLAIN = {      # the labels of the plain block at the top of the confirmation page
    "zh": {"kind": "種類", "launch": "送出新分析", "resume": "續跑", "relaunch": "重跑", "cancel": "取消", "clean_work": "清理中間檔", "run": "分析名稱", "pipeline": "管線",
           "version": "版本", "env": "環境", "samples": "樣本數", "folder": "新資料夾", "work": "要刪除的資料夾", "full": "完整內容（技術細節）"},
    "en": {"kind": "Request", "launch": "New analysis", "resume": "Continue the run", "relaunch": "Re-run", "cancel": "Cancel", "clean_work": "Clean up intermediate files", "run": "Run name",
           "pipeline": "Pipeline", "version": "Version", "env": "Environment", "samples": "Samples", "folder": "New folder", "work": "Folder to delete",
           "full": "Full content (technical)"}}
LAUNCH_HEADERS = dict(_HEADERS, **{      # /launch alone may show pictures, and only our own (guided-launch-2d: the workflow diagram under the pipeline)
    "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src %s; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    % web_board.style_source()})
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
    return _page("登入 (log in)", note + "<p>請以您的姓名與<strong>網頁密碼</strong>登入（網頁密碼不同於 AI 使用的權杖；於平台主機的終端機以 "
                 "<code>abf-platform user passwd</code> 設定，或使用管理者提供的一次性臨時密碼）。</p><form method=\"post\" action=\"/login\">"
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

    def temp_user_of(request):
        """(sid, user) of a login made with a temporary password that is still good; user is None for any other cookie (or none)."""
        sid = session_id(request)
        who = store.web_session_user(tokens_path, sid, clock(), allow_must_change=True) if sid else None
        return sid, (who if who is not None and who["must_change"] else None)

    def to_welcome(request):
        """303 to /welcome for a login made with a temporary password, else None."""
        return RedirectResponse("/welcome", status_code=303, headers=_HEADERS) if temp_user_of(request)[1] is not None else None

    def unauth(request):
        """Where a page that needs a login sends a browser that has none: /welcome for a temporary-password login, else /login."""
        return to_welcome(request) or RedirectResponse("/login", status_code=303, headers=_HEADERS)

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
        return _page("來源不符 (wrong origin)", "<p class=\"bad\">此表單並非由本頁送出，未變更任何內容。</p>", 403)

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
        give_back(name, ip, now)
        sid, _ = store.create_web_session(tokens_path, who["user_id"], now)
        response = RedirectResponse("/welcome" if who["must_change"] else (nxt or HOME), status_code=303, headers=_HEADERS)
        response.set_cookie(COOKIE, cookie_value(sid), max_age=int(store.WEB_SESSION_SECONDS), httponly=True, samesite="Strict",
                            secure=secure, path="/")
        return response

    def give_back(name, ip, now):
        """Take back the failure entry this request counted (a right password, or a refusal that is not a wrong guess)."""
        for table, k in ((by_name, name), (by_ip, ip)):
            if now in table.get(k, ()):
                table[k].remove(now)
            if not table.get(k, True):
                table.pop(k, None)

    def welcome_form(sid, message="", status=200):
        note = "<p class=\"bad\">%s</p>" % _esc(message) if message else ""
        limit = "（%d 到 %d 個字元 / %d to %d characters）" % (store.MIN_PASSWORD_CHARS, store.MAX_PASSWORD_CHARS,
                                                         store.MIN_PASSWORD_CHARS, store.MAX_PASSWORD_CHARS)
        return _page("設定個人密碼 (set your own password)",
                     note + "<p>目前使用的是管理者提供的臨時密碼，效期 72 小時，僅可用於設定個人密碼。設定完成後，請改以新密碼登入。</p>"
                     "<p>You are using a one-time temporary password from your administrator. It works for 72 hours and only lets you set "
                     "your own password. After that, log in with your new password.</p>"
                     "<form method=\"post\" action=\"/welcome\"><input type=\"hidden\" name=\"csrf\" value=\"%s\">"
                     "<p><label>目前的臨時密碼 (current temporary password) <input name=\"old\" type=\"password\" "
                     "autocomplete=\"current-password\" required></label></p>"
                     "<p><label>新密碼 (new password) <input name=\"new\" type=\"password\" autocomplete=\"new-password\" required></label> "
                     "<small>%s</small></p>"
                     "<p><label>再輸入一次新密碼 (new password again) <input name=\"confirm\" type=\"password\" "
                     "autocomplete=\"new-password\" required></label></p>"
                     "<p><button type=\"submit\">設定密碼 (set password)</button></p></form>"
                     "<form method=\"post\" action=\"/logout\"><input type=\"hidden\" name=\"csrf\" value=\"%s\">"
                     "<p><button type=\"submit\">登出 (log out)</button></p></form>"
                     % (_esc(csrf(sid, "welcome")), _esc(limit), _esc(csrf(sid, "logout"))), status)

    def not_temporary(request):
        """Where /welcome sends a browser that is not in a temporary-password login: home for an ordinary login, else /login."""
        sid = session_id(request)
        who = store.web_session_user(tokens_path, sid, clock()) if sid else None
        return RedirectResponse(HOME if who is not None else "/login", status_code=303, headers=_HEADERS)

    async def welcome_get(request):
        sid, user = temp_user_of(request)
        return welcome_form(sid) if user is not None else not_temporary(request)

    async def welcome_post(request):
        if not same_origin(request):
            return foreign(request)
        sid, user = temp_user_of(request)
        if user is None:
            return not_temporary(request)
        form = await body_of(request)
        if not _same(form.get("csrf", ""), csrf(sid, "welcome")):
            return _page("表單已失效", "<p class=\"bad\">表單驗證碼不符或已失效，未變更任何內容。請重新整理頁面後再操作。</p>", 403)
        name = user["name"][:MAX_NAME_CHARS]
        ip = request.client.host if request.client else ""
        now = clock()
        if (len(recent(by_name, name, now)) >= FAIL_LIMIT or len(recent(by_ip, ip, now)) >= IP_FAIL_LIMIT
                or no_room(by_name, name, now) or no_room(by_ip, ip, now)):
            return welcome_form(sid, "登入失敗太頻繁，請一分鐘後再試 (too many tries, wait a minute)", 429)
        old, new, again = str(form.get("old", "")), str(form.get("new", "")), str(form.get("confirm", ""))
        if new != again:
            return welcome_form(sid, "兩次輸入的新密碼不一樣 (the two new passwords differ)", 400)
        # Counted before the slow check, in the same step as the limit check (no await between them), as the login page does.
        by_name.setdefault(name, []).append(now)
        by_ip.setdefault(ip, []).append(now)
        if len(old) > store.MAX_PASSWORD_CHARS:
            return welcome_form(sid, "密碼最長 %d 個字元 (password at most %d characters)" % (store.MAX_PASSWORD_CHARS, store.MAX_PASSWORD_CHARS), 400)
        try:
            await run_in_threadpool(store.change_web_password, tokens_path, user["name"], old, new, keep_sid=sid)
        except ValueError as e:
            message = str(e)
            if "目前的密碼不對" in message:
                return welcome_form(sid, message, 401)
            give_back(name, ip, now)
            return welcome_form(sid, message, 400)
        give_back(name, ip, now)
        return RedirectResponse(HOME, status_code=303, headers=_HEADERS)

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
            return _page("找不到 (not found)", "<p>無此申請。</p>", 404), None
        if req["caller_user_id"] != user["user_id"]:
            return _page("非您的申請 (not yours)", "<p class=\"bad\">該申請並非由您送出，無法在此檢視或操作。</p>", 403), None
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
                           ("folder", "folder"), ("work", "work")):
            if key in facts:
                rows.append((t[label], facts[key]))
        return "<dl class=\"fields plain\">%s</dl>" % "".join("<dt>%s</dt><dd>%s</dd>" % (_esc(k), _esc(v)) for k, v in rows)

    def state_page(req, sid, rid, lang="zh"):
        clean = req["kind"] == "clean_work"
        title = "清理確認" if clean else ("送出確認" if req["kind"] == "launch" else "取消確認")
        shown = "<details><summary>%s</summary><pre>%s</pre></details>" % (_PLAIN[lang]["full"], _esc(req["summary"] or ""))
        if req["state"] in ("pending", "confirmed"):
            shown = plain_block(rid, lang) + shown
        if req["state"] == "pending":
            if clean:
                intro = "<p>以下為將被刪除的全部內容。確認無誤後，請按「確認刪除」；按下後才會排入佇列。</p>"
                button = "Confirm delete" if lang == "en" else "確認刪除"
            else:
                intro = "<p>以下為將被%s的全部內容。確認無誤後，請按「送出」；按下後才會排入佇列。</p>" % ("送出" if req["kind"] == "launch" else "取消")
                button = "送出"
            return _page(title, "%s%s<form method=\"post\" action=\"/c/%s\"><input type=\"hidden\" name=\"csrf\" value=\"%s\">"
                         "<button type=\"submit\">%s</button></form>" % (intro, shown, rid, _esc(csrf(sid, rid)), button))
        if req["state"] == "confirmed":
            return _page(title, "<p class=\"ok\">已送出。工作編號 %s。</p>%s" % (_esc(req["job_id"]), shown))
        if req["state"] == "expired":
            if clean:
                return _page(title, "<p class=\"bad\">該申請已逾時（7 天），不會自動重新提出。</p>")
            return _page(title, "<p class=\"bad\">該申請已逾時（10 分鐘）。請返回 AI 重新送出。</p>")
        if clean:
            return _page(title, "<p class=\"bad\">該申請已作廢：%s。</p>" % _esc(req["void_reason"] or "-"), 409)
        return _page(title, "<p class=\"bad\">該申請已作廢：%s。請返回 AI 重新送出。</p>" % _esc(req["void_reason"] or "-"), 409)

    async def confirm_get(request):
        rid = request.path_params["rid"]
        if not RID.match(rid):
            return _page("找不到 (not found)", "<p>無此網址。</p>", 404)
        sid, user = user_of(request)
        if user is None:
            return to_welcome(request) or _login_form("/c/" + rid)
        answer, req = view_of(rid, user)
        return answer or state_page(req, sid, rid, web_board.pick_lang(request.query_params.get("lang")))

    async def confirm_post(request):
        if not same_origin(request):
            return foreign(request)
        rid = request.path_params["rid"]
        if not RID.match(rid):
            return _page("找不到 (not found)", "<p>無此網址。</p>", 404)
        sid, user = user_of(request)
        if user is None:
            return to_welcome(request) or _login_form("/c/" + rid, "請先登入 (log in first)", 401)
        answer, req = view_of(rid, user)
        if answer is not None:
            return answer
        form = await body_of(request)
        if not _same(form.get("csrf", ""), csrf(sid, rid)):
            return _page("表單已失效", "<p class=\"bad\">表單驗證碼不符或已失效，未送出任何內容。請重新整理頁面後再操作。</p>", 403)
        try:
            _, job_id = actions.approve(platform_path, rid, confirmed_by=actions.PAGE,
                                        caller=actions.Caller(user["user_id"], user["name"], user["lab"]), clock=clock)
        except actions.NotApproved as e:
            if e.status == "already":
                return _page("已送出", "<p class=\"ok\">已送出。工作編號 %s。</p>" % _esc(e.job_id))
            code = {"not_found": 404, "not_yours": 403, "expired": 410}.get(e.status, 409)
            if req["kind"] == "clean_work":
                return _page("未送出", "<p class=\"bad\">未送出：%s。</p>" % _esc(e), code)
            return _page("未送出", "<p class=\"bad\">未送出：%s。請回到 AI 重新送出。</p>" % _esc(e), code)
        if req["kind"] == "clean_work":
            return _page("已送出", "<p class=\"ok\">已送出。工作編號 %s。代理將清理該次分析的中間檔，結果不受影響。</p>" % _esc(job_id))
        return _page("已送出", "<p class=\"ok\">已送出。工作編號 %s。可返回 AI，以相同參數再呼叫一次，將回報工作編號。</p>" % _esc(job_id))

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

    def read_finished(view, caller):
        """What the finished stage shows of how the run was sent: the action `launch_prefill` (reads only)."""
        return actions.launch_prefill(platform_path, view["name"], caller=caller)

    def read_outputs_look(run_id, caller):
        """The output folder as it is now, for the delivery list of the finished stage: it only looks, it never queues a listing."""
        try:
            return actions.run_outputs(index_path, platform_path, run_id, caller=caller, enqueue=False)
        except sqlite3.Error:
            return None

    async def board_page(sid, user, caller, lang, run_id, stage=None, tab=None, flash=None, code=200, relist=False):
        """The board for one logged-in user: one run's page (the one named, else the one that needs the person most, else the newest;
        an empty page for a person with no run), with `flash` (one plain line of refusal) on it after a refused button."""
        runs = await run_in_threadpool(read_runs, caller)
        selected = None
        outputs = None
        finished = None
        if run_id or runs:
            selected = await run_in_threadpool(read_run, run_id or web_board.default_run(runs), caller)
            if selected is None:        # another person's run and a missing id answer alike, and the page never repeats the id
                return HTMLResponse(web_board.render_not_found(user["name"], lang), status_code=404, headers=_HEADERS)
            if selected["status"] == "succeeded" and web_board.pick_stage(stage, "results") == "results" and not flash:
                outputs = await run_in_threadpool(read_outputs, selected["id"], caller, web_board.pick_results_tab(tab) == "outputs", relist)
            if selected["status"] == "succeeded" and web_board.pick_stage(stage, None) == "finished" and not flash:
                finished = await run_in_threadpool(read_finished, selected, caller)
                outputs = await run_in_threadpool(read_outputs_look, selected["id"], caller)
            if selected["status"] == "succeeded":
                asked = (await run_in_threadpool(actions.clean_requests, platform_path, caller=caller, clock=clock)).get(selected["name"])
                if asked:
                    selected["clean_request"] = asked
        doc = web_board.render_board(user["name"], csrf(sid, "logout"), runs, selected, stage, lang, tab, clock(),
                                     act_csrf=lambda rid: csrf(sid, "act:" + rid), flash=flash, outputs=outputs, finished=finished)
        return HTMLResponse(doc, status_code=code, headers=_HEADERS)

    async def board(request):
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
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
            return unauth(request)
        form = await body_of(request)
        lang = web_board.pick_lang(form.get("lang"))
        run_id = str(form.get("run", ""))[:200]
        if verb not in ("resume", "relaunch", "cancel"):
            return _page("找不到 (not found)", "<p>無此網址。</p>", 404)
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
        """The samplesheets and the compute environments the person may choose from: only an environment that is set up (`available`) is offered
        (guided-launch-2d); the settings page is where the others are dealt with."""
        sheets = actions.list_samplesheets(platform_path, caller=caller)
        envs = [e for e in actions.list_compute_envs(platform_path, caller=caller)["compute_envs"] if e.get("status") == "available"]
        return sheets, envs

    def launch_reads(caller, pipeline, revision):
        """The two lists of the guided page: the pipelines used before, and (once a pipeline and revision are chosen) the runs of that pair."""
        used = actions.list_used_pipelines(platform_path, caller=caller)["pipelines"]
        reuse = []
        if pipeline and revision:
            reuse = actions.list_used_pipelines(platform_path, caller=caller, pipeline=pipeline, revision=revision)["pipelines"]
        return used, reuse

    def launch_files(caller, full, revision, ce_name, src, enqueue=True):
        """The pipeline's own files for the guided page (guided-launch-2): on the new-pipeline tab the list of releases (the version drop-down; when
        no revision is chosen yet its newest one is the revision, guided-launch-2d), then what pipeline_files answers for the pair, then (only when
        a diagram is there) the picture. Each call only reads or queues one job; the answer to a POST that did not pass (`enqueue=False`) only
        looks: a form that was refused makes no request, not even this one. Returns (files, image, latest, revision)."""
        files = image = latest = None
        if full and src == "new":
            latest = actions.latest_release(platform_path, full, caller=caller, compute_env=ce_name, enqueue=enqueue)
            if not revision and latest.get("state") == "ready" and latest.get("revision"):
                revision = latest["revision"]
        if full and revision:
            files = actions.pipeline_files(platform_path, full, revision, caller=caller, compute_env=ce_name, enqueue=enqueue)
            diagram = files.get("diagram") if files.get("state") == "ready" else None
            if isinstance(diagram, dict) and diagram.get("status") == "ok":
                image = actions.pipeline_files(platform_path, full, revision, parts=["image"], caller=caller, compute_env=ce_name, enqueue=enqueue)
        return files, image, latest, revision

    async def launch_page(sid, user, caller, lang, values, errors, notes, source=None, code=200, guide=None):
        t = web_board.STRINGS[lang]
        sheets, envs = await run_in_threadpool(launch_choices, caller)
        names = [e["name"] for e in envs]
        values = dict(values)
        values.setdefault("samplesheet", sheets[0] if sheets else None)
        values.setdefault("ce_name", names[0] if names else None)
        guide = dict(guide or {})
        pipeline = (values.get("pipeline") or "").strip()
        revision = (values.get("revision") or "").strip()
        full = pipeline if "/" in pipeline else ("nf-core/" + pipeline if pipeline else "")
        used, _none = await run_in_threadpool(launch_reads, caller, "", "")
        guide["used"] = used
        if guide.get("src") not in ("used", "new"):
            guide["src"] = "used" if used else "new"
        ce = values.get("ce_name") if values.get("ce_name") in names else None
        files, image, latest, chosen = await run_in_threadpool(launch_files, caller, full, revision, ce, guide["src"], not guide.get("post"))
        if chosen != revision:      # the pair was a pipeline alone on the new-pipeline tab: its newest release is the version (guided-launch-2d)
            revision = values["revision"] = chosen
            guide["hint"] = True
        _used, guide["reuse"] = await run_in_threadpool(launch_reads, caller, full, revision)
        if full and revision:
            guide["done"] = set(guide.get("done") or ()) | {3}
        # the boxes of the parameter table hold the default, or what was filled in, or the value of the earlier analysis; the parameters of that
        # analysis that the schema does not know go to the advanced box (guided-launch-2b)
        cells, box = dict(guide.get("cells") or {}), values.get("params", "")
        if guide.get("prefill"):
            known, rest = web_launch.split_prefill(guide["prefill"], files)
            cells = dict(known, **cells)
            if rest and not box.strip():
                box = web_board.params_text(rest)
        values["params"] = box
        guide["cells"] = cells
        guide["sets"] = web_launch.merge_params(box, web_launch.changed_fields(web_launch.cell_values(files, cells), files), web_launch.types_of(files))
        if guide.get("hint") and web_launch.types_of(files):
            notes = list(notes) + [t["g_loaded"] % (full, revision)]
        runs = await run_in_threadpool(read_runs, caller)
        doc = web_board.render_launch(user["name"], csrf(sid, "logout"), runs, values, errors, notes, sheets, envs, csrf(sid, "launch"), lang, source,
                                      guide, files, image, latest)
        return HTMLResponse(doc, status_code=code, headers=LAUNCH_HEADERS)

    async def launch_get(request):
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        lang = web_board.pick_lang(request.query_params.get("lang"))
        t = web_board.STRINGS[lang]
        q = request.query_params
        sheets, envs = await run_in_threadpool(launch_choices, caller)
        names = [e["name"] for e in envs]
        runs = await run_in_threadpool(read_runs, caller)
        given = {k: q.get(k).strip() for k in ("pipeline", "revision", "params_from", "from") if q.get(k, "").strip()}      # `route` of the first cut is ignored
        if "params" in q:
            given["params"] = q.get("params")
        if q.get("samplesheet") in sheets:
            given["samplesheet"] = q.get("samplesheet")
        if (q.get("ce_name") or q.get("ce")) in names:
            given["ce_name"] = q.get("ce_name") or q.get("ce")      # `names` holds the available environments only
        if q.get("src") in ("used", "new"):
            given["src"] = q.get("src")
        values = {k: given[k] for k in ("pipeline", "revision", "samplesheet", "ce_name") if k in given}
        if q.get("run_name", "").strip():
            values["run_name"] = q.get("run_name").strip()
        notes, source, done, prefill = [], None, set(), None
        pvals = web_launch.fields_of(dict(q.items()))      # the boxes of the parameter table, when the address carries any

        def run_name_of(origin):      # the page is asked for a run by its id or by its name
            return next((r["name"] for r in runs if r["id"] == origin), origin)
        origin = given.get("from", "")
        if origin:       # re-run with the same settings: the boxes of an earlier run of this person, when its content is still kept
            name = run_name_of(origin)
            match = next((r for r in runs if r["id"] == origin or r["name"] == origin), None)
            earlier = await run_in_threadpool(actions.launch_prefill, platform_path, name, caller=caller)
            if match is None and not earlier.get("found"):
                return HTMLResponse(web_board.render_not_found(user["name"], lang), status_code=404, headers=_HEADERS)
            when = web_board.taipei_time(earlier.get("launched_at"))
            if match is not None:
                source = (match["id"], match["name"], match["status"], when)
            if earlier.get("kept"):
                for key, value in (("pipeline", earlier.get("pipeline") or ""), ("revision", earlier.get("revision") or ""),
                                   ("ce_name", earlier.get("ce_name") if earlier.get("ce_name") in names else None)):
                    if key not in values and value:
                        values[key] = value
                prefill = earlier.get("params") or {}
                done |= {5} | ({2} if values.get("ce_name") else set())
                notes.append(t["l_from"])
            else:
                notes.append(t["l_not_kept"])
        pipeline, revision = values.get("pipeline", ""), values.get("revision", "")
        if values.get("run_name"):
            done.add(1)
        if "ce_name" in given:
            done.add(2)
        if pipeline and revision:
            done.add(3)
        if "samplesheet" in given:
            done.add(4)
        if "params" in given:
            done.add(5)
        cannot = False
        if given.get("params_from"):
            full = pipeline if "/" in pipeline else "nf-core/" + pipeline
            earlier = await run_in_threadpool(actions.launch_prefill, platform_path, run_name_of(given["params_from"]), caller=caller)
            if pipeline and revision and earlier.get("found") and earlier.get("kept") and earlier.get("pipeline") == full \
                    and earlier.get("revision") == revision:
                prefill = earlier.get("params") or {}
                done.add(5)
            else:
                cannot = True
                given.pop("params_from")
        values["params"] = given.get("params", "")
        guide = {"given": dict(given), "done": done, "cannot_reuse": cannot, "src": given.get("src"), "cells": pvals or None, "prefill": prefill,
                 "hint": bool(pipeline and revision)}
        return await launch_page(sid, user, caller, lang, values, [], notes, source, guide=guide)

    DIAGRAM_TYPES = ("image/png", "image/svg+xml", "image/jpeg", "image/gif")

    async def launch_diagram(request):
        """The picture of the workflow diagram, read by the caller's own agent: only what pipeline_files already holds for this person (no job is
        queued here; GET /launch queued it). Anything else is one plain line with a 404."""
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        pipeline, revision = request.query_params.get("pipeline", "").strip(), request.query_params.get("revision", "").strip()

        def missing():
            return PlainTextResponse(web_board.STRINGS["zh"]["g2_dia_404"], status_code=404, headers=_HEADERS)
        if not pipeline or not revision:
            return missing()
        full = pipeline if "/" in pipeline else "nf-core/" + pipeline
        answer = await run_in_threadpool(lambda: actions.pipeline_files(platform_path, full, revision, parts=["image"], caller=caller, enqueue=False))
        picture = answer.get("image") if answer.get("state") == "ready" else None
        if not isinstance(picture, dict) or picture.get("status") != "ok" or picture.get("type") not in DIAGRAM_TYPES:
            return missing()
        try:
            data = base64.b64decode(str(picture.get("data_b64") or ""), validate=True)
        except (binascii.Error, ValueError):
            return missing()
        headers = dict(_HEADERS, **{"Cache-Control": "private, max-age=3600"})
        if picture["type"] == "image/svg+xml":      # a picture that can carry a script is shown with no script allowed
            headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
        return Response(data, media_type=picture["type"], headers=headers)

    async def launch_body(request):
        """The body of the launch form. Every box of the parameter table comes back (it holds its default), so this form carries far more fields and
        bytes than the other forms of the site; the same read with a larger cap (guided-launch-2b)."""
        raw = b""
        async for chunk in request.stream():
            raw += chunk
            if len(raw) > LAUNCH_BODY:
                break
        out = urllib.parse.parse_qs(raw[:LAUNCH_BODY].decode("utf-8", errors="replace"), keep_blank_values=True, max_num_fields=1000)
        return {k: v[0] for k, v in out.items()}

    async def launch_post(request):
        if not same_origin(request):
            return foreign(request)
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
        form = await launch_body(request)
        lang = web_board.pick_lang(form.get("lang"))
        t = web_board.STRINGS[lang]
        if not _same(form.get("csrf", ""), csrf(sid, "launch")):
            return _page("表單已失效 (form expired)", "<p class=\"bad\">%s</p>" % _esc(t["r_form"]), 403)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        sheets, env_list = await run_in_threadpool(launch_choices, caller)
        envs = [e["name"] for e in env_list]
        pipeline = str(form.get("pipeline", "")).strip()
        chosen = str(form.get("params_from", "")).strip()
        src = str(form.get("src", "")) if form.get("src") in ("used", "new") else None
        values = {"pipeline": pipeline, "revision": str(form.get("revision", "")).strip(), "run_name": str(form.get("run_name", "")).strip(),
                  "samplesheet": str(form.get("samplesheet", "")), "ce_name": str(form.get("ce_name", "")), "params": str(form.get("params", ""))}
        errors, bad = [], set()
        fresh = pipeline != str(form.get("shown_pipeline", "")).strip()      # a pipeline the page was not drawn for: its version is the newest (guided-launch-2d)
        if not pipeline or not re.match(r"^[A-Za-z0-9._/-]{1,100}\Z", pipeline):
            errors.append(t["e_pipeline"])
            bad.add(3)
        if (not values["revision"] and not (fresh and src == "new")) or re.search(r"\s", values["revision"]):
            errors.append(t["e_revision"])
            bad.add(3)
        if not errors and (fresh or values["revision"] != str(form.get("shown_revision", "")).strip()
                           or chosen != str(form.get("shown_params_from", "")).strip()):
            # the page was drawn for another pipeline, version or earlier analysis: this press only loads that table (nothing is sent; the
            # confirmation page stays the only place that queues anything)
            pairs = [("pipeline", pipeline), ("revision", "" if fresh and src == "new" else values["revision"]), ("samplesheet", values["samplesheet"]),
                     ("ce_name", values["ce_name"]), ("run_name", values["run_name"]), ("params_from", chosen), ("src", src),
                     ("lang", "en" if lang == "en" else "")]
            return RedirectResponse("/launch?" + urllib.parse.urlencode([(k, v) for k, v in pairs if v], safe="/"), status_code=303, headers=_HEADERS)
        if not values["run_name"]:
            errors.append(t["e_run_name"])
            bad.add(1)
        if values["ce_name"] not in envs:
            errors.append(t["e_ce"])
            bad.add(2)
        elif 3 not in bad and web_board.is_unregistered(next(e for e in env_list if e["name"] == values["ce_name"]),
                                                      pipeline if "/" in pipeline else "nf-core/" + pipeline, values["revision"]):
            errors.append(t["e_reg"])
            bad.add(3)
        if values["samplesheet"] not in sheets:
            errors.append(t["e_sheet"])
            bad.add(4)
        cells = web_launch.fields_of(form)      # every box of the parameter table as it came back
        pvals = {k: v for k, v in cells.items() if v.strip()}
        merged = values["params"]
        if pvals:      # only the boxes that differ from the pipeline's own default are sent (a read that queues nothing)
            def schema_files():
                full = pipeline if "/" in pipeline else "nf-core/" + pipeline
                return actions.pipeline_files(platform_path, full, values["revision"], caller=caller, enqueue=False)
            files = await run_in_threadpool(schema_files) if pipeline and values["revision"] else None
            merged = web_launch.merge_params(merged, web_launch.changed_fields(pvals, files), web_launch.types_of(files))
        params, problems = web_board.parse_params(merged, t)
        errors += problems
        if problems:
            bad.add(5)
        if not errors:
            answer = await actions.request_launch(
                platform_path, pipeline=pipeline if "/" in pipeline else "nf-core/" + pipeline, revision=values["revision"],
                run_name=values["run_name"], samplesheet=values["samplesheet"], ce_name=values["ce_name"], params=params or None,
                caller=caller, clock=clock)
            done = to_confirmation(answer)
            if done is not None:
                return done
            errors.append(web_board.plain_reason(answer.get("message"), lang) + " " + t["r_none"])
            bad.add(6)
        else:
            errors.append(t["e_body"])
        guide = {"done": {1, 2, 3, 4, 5}, "bad": bad, "post": True, "cells": cells, "src": src, "given": {"params_from": chosen} if chosen else {}}
        return await launch_page(sid, user, caller, lang, values, errors, [], code=400, guide=guide)

    # ---- web-upload-page: the form, the receiving of the files, the progress of a batch. The bytes are only written to a folder of the platform host here
    # (uploads_web); judging, queueing and registering are the two actions start_upload_batch and upload_batch_status. The person's press of Upload is the yes.
    def upload_envs(caller):
        return actions.list_compute_envs(platform_path, caller=caller)["compute_envs"]

    async def upload_page(sid, user, caller, lang, values=None, problem=None, code=200):
        runs = await run_in_threadpool(read_runs, caller)
        envs = await run_in_threadpool(upload_envs, caller)
        return HTMLResponse(web_upload.render_form(user["name"], csrf(sid, "logout"), runs, lang, envs, csrf(sid, "upload"), values, problem),
                            status_code=code, headers=LAUNCH_HEADERS)

    async def upload_get(request):
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        return await upload_page(sid, user, caller, web_board.pick_lang(request.query_params.get("lang")))

    async def upload_post(request):
        if not same_origin(request):
            return foreign(request)
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
        lang = web_board.pick_lang(request.query_params.get("lang"))
        t = web_board.STRINGS[lang]
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        batch = secrets.token_hex(16)
        try:
            area = actions.caller_area(platform_path, caller)
        except Exception:
            return await upload_page(sid, user, caller, lang, problem={"error": "disk"}, code=500)
        incoming = uploads_web.incoming_for(area, batch)

        def gate(fields):
            if not _same(fields.get("csrf", ""), csrf(sid, "upload")):
                raise uploads_web.Rejected(403, "forbidden")

        await run_in_threadpool(uploads_web.sweep, area)
        try:
            got = await uploads_web.receive(request.stream(), request.headers.get("content-type"), incoming, limit=uploads_web.FILE_LIMIT, before_file=gate)
        except uploads_web.Rejected as r:
            if r.kind == "forbidden":
                return _page("表單已失效 (form expired)", "<p class=\"bad\">%s</p>" % _esc(t["r_form"]), 403)
            return await upload_page(sid, user, caller, lang, problem=dict(r.info, error=r.kind), code=r.code)
        except ClientDisconnect:
            return Response(status_code=400, headers=_HEADERS)
        except OSError:
            return await upload_page(sid, user, caller, lang, problem={"error": "disk"}, code=500)
        form = got["fields"]
        if not _same(form.get("csrf", ""), csrf(sid, "upload")):
            uploads_web.discard(incoming)
            return _page("表單已失效 (form expired)", "<p class=\"bad\">%s</p>" % _esc(t["r_form"]), 403)
        values = {"ce": form.get("ce", ""), "name": form.get("name", ""), "version": form.get("version", "")}
        answer = await run_in_threadpool(lambda: actions.start_upload_batch(
            platform_path, tokens_path, caller, batch=batch, ce_name=values["ce"], name=values["name"], version=values["version"],
            files=got["files"], samplesheet=got["samplesheet"], incoming=incoming, clock=clock))
        if answer.get("ok"):
            return RedirectResponse("/upload/" + batch + ("?lang=en" if lang == "en" else ""), status_code=303, headers=_HEADERS)
        return await upload_page(sid, user, caller, lang, values, answer, 413 if answer.get("error") == "too_big" else 400)

    async def upload_batch_get(request):
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        lang = web_board.pick_lang(request.query_params.get("lang"))
        view = await run_in_threadpool(lambda: actions.upload_batch_status(platform_path, caller, request.path_params["batch"], clock=clock))
        if not view.get("found"):
            return HTMLResponse(web_board.render_not_found(user["name"], lang), status_code=404, headers=_HEADERS)
        runs = await run_in_threadpool(read_runs, caller)
        return HTMLResponse(web_upload.render_progress(user["name"], csrf(sid, "logout"), runs, lang, view), headers=LAUNCH_HEADERS)

    async def settings_page(sid, user, caller, lang, flash_of=None, given=None, code=200):
        """The settings page for one logged-in user. `flash_of(envs)` says a notice or a failure; `given` is what a refused form held."""
        runs = await run_in_threadpool(read_runs, caller)
        envs = actions.list_compute_envs(platform_path, caller=caller)["compute_envs"]
        flash = flash_of(envs) if flash_of else None
        lists = {e["name"]: await run_in_threadpool(lambda e=e: actions.site_pipeline_inventory(platform_path, ce=e["name"], caller=caller))
                 for e in envs if e.get("platform") == web_settings.SLURM_TYPE}      # what each Slurm site last reported it has installed (reads only)
        return HTMLResponse(web_settings.render(user["name"], csrf(sid, "logout"), runs, lang, envs, csrf(sid, "settings-pipeline"), flash, given,
                                                lists, csrf(sid, "settings-inventory")),
                            status_code=code, headers=_HEADERS)

    async def settings(request):
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        lang = web_board.pick_lang(request.query_params.get("lang"))
        key, ce = request.query_params.get("notice"), request.query_params.get("ce")
        return await settings_page(sid, user, caller, lang, lambda envs: web_settings.make_flash(envs, "notice", key=key, ce=ce))

    # ---- settings-register-pipeline: register or remove a pipeline version on the person's own compute environment, in two steps.
    # Step one only checks (check_site_pipeline_change reads) and shows what will change; step two, after the person presses the button, is the
    # only place that calls a write action, with the PAGE channel. Nothing is stored between the steps: the token of step two is bound to the boxes.
    PF_BOXES = ("op", "ce", "pipeline", "revision", "module", "home")

    def pf_refused(lang, which):
        t = web_settings.words(lang)
        return _page(t["pf_" + which + "_title"], '<p class="bad">%s</p>' % _esc(t["pf_" + which]), 403)

    def pf_where(ce, lang, notice):
        return "/settings?notice=%s&ce=%s%s#ce-%s" % (notice, urllib.parse.quote(ce, safe=""), "&lang=en" if lang == "en" else "", urllib.parse.quote(ce, safe=""))

    def pf_failed(sid, user, caller, lang, ce, text, given=None):
        return settings_page(sid, user, caller, lang, lambda envs: web_settings.make_flash(envs, "fail", text=text, ce=ce), given, 400)

    async def pipelines_post(request):
        lang = web_board.pick_lang(request.query_params.get("lang"))
        if not same_origin(request):
            return pf_refused(lang, "foreign")
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
        form = await body_of(request)
        lang = web_board.pick_lang(form.get("lang"))
        if not _same(form.get("csrf", ""), csrf(sid, "settings-pipeline")):
            return pf_refused(lang, "expired")
        f = {k: str(form.get(k, "")).strip()[:300] for k in PF_BOXES}
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        t = web_settings.words(lang)
        if f["op"] == "add" and "pick" in form:
            # settings-pick-installed: the person chose "<pipeline> <version>" from the site's own list. The module and the variable are looked up
            # here from the newest list (never taken from the browser); what is not in that list is refused before anything else is asked.
            listed = await run_in_threadpool(lambda: actions.site_pipeline_inventory(platform_path, ce=f["ce"], caller=caller))
            if listed.get("found") is False:      # not the person's own environment: the same words as every other form for a missing one
                return await pf_failed(sid, user, caller, lang, f["ce"], t["pf_fail"] + web_board.plain_reason(listed.get("message"), lang))
            parts = str(form.get("pick", "")).strip()[:300].split(" ")
            chosen = [i for i in (listed.get("items") or []) if listed.get("status") == "ok" and len(parts) == 2 and parts[0] and parts[1]
                      and (i.get("pipeline"), i.get("revision")) == (parts[0], parts[1])]
            if not chosen:
                return await pf_failed(sid, user, caller, lang, f["ce"], t["pf_pick_gone"])
            f.update(pipeline=chosen[0]["pipeline"], revision=chosen[0]["revision"], module=chosen[0]["module"], home=chosen[0]["home"])
        seen = await run_in_threadpool(lambda: actions.check_site_pipeline_change(
            platform_path, op=f["op"], ce=f["ce"], pipeline=f["pipeline"], revision=f["revision"], module=f["module"], home=f["home"], caller=caller))
        if not seen["ok"]:
            line = web_settings.field_error(lang, seen.get("field"), f.get(seen.get("field") or ""))
            return await pf_failed(sid, user, caller, lang, f["ce"], line or t["pf_fail"] + web_board.plain_reason(seen.get("message"), lang),
                                   {f["ce"]: f})
        if seen["gone"]:
            return RedirectResponse(pf_where(f["ce"], lang, "gone"), status_code=303, headers=_HEADERS)
        runs = await run_in_threadpool(read_runs, caller)
        token = csrf(sid, web_settings.purpose_of(f))
        edge = seen["count"] == 0 if f["op"] == "add" else seen["count"] == 1
        return HTMLResponse(web_settings.render_confirm(user["name"], csrf(sid, "logout"), runs, lang, f, token, edge), headers=_HEADERS)

    async def pipelines_confirm_post(request):
        lang = web_board.pick_lang(request.query_params.get("lang"))
        if not same_origin(request):
            return pf_refused(lang, "foreign")
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
        form = await body_of(request)
        lang = web_board.pick_lang(form.get("lang"))
        f = {k: str(form.get(k, "")) for k in PF_BOXES}
        if not _same(form.get("csrf", ""), csrf(sid, web_settings.purpose_of(f))):
            return pf_refused(lang, "expired")
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        t = web_settings.words(lang)
        if f["op"] == "add":
            answer = await run_in_threadpool(lambda: actions.register_site_pipeline(
                platform_path, ce=f["ce"], pipeline=f["pipeline"], revision=f["revision"], module=f["module"], home=f["home"],
                confirmed_by=actions.PAGE, caller=caller))
        elif f["op"] == "remove":
            answer = await run_in_threadpool(lambda: actions.remove_site_pipeline(
                platform_path, ce=f["ce"], pipeline=f["pipeline"], revision=f["revision"], confirmed_by=actions.PAGE, caller=caller))
        else:
            answer = {"ok": False, "message": "動作只能是新增或移除 (the action must be add or remove)"}
        if not answer["ok"]:
            return await pf_failed(sid, user, caller, lang, f["ce"], t["pf_fail"] + web_board.plain_reason(answer.get("message"), lang))
        if f["op"] == "remove":
            notice = "removed" if answer["changed"] else "gone"
        else:
            notice = {"queued": "added_queued", "no_agent": "added_no_agent", "not_checkable": "added_not_checkable"}.get(answer["preflight"],
                                                                                                                         "added_check_refused")
        return RedirectResponse(pf_where(f["ce"], lang, notice), status_code=303, headers=_HEADERS)

    async def inventory_post(request):
        """The button "Reload site list": queue one pre-use check, whose answer carries the list. It changes no setting, so it has no confirmation page."""
        lang = web_board.pick_lang(request.query_params.get("lang"))
        if not same_origin(request):
            return pf_refused(lang, "foreign")
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
        form = await body_of(request)
        lang = web_board.pick_lang(form.get("lang"))
        if not _same(form.get("csrf", ""), csrf(sid, "settings-inventory")):
            return pf_refused(lang, "expired")
        ce = str(form.get("ce", "")).strip()[:300]
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        t = web_settings.words(lang)
        answer = await run_in_threadpool(lambda: actions.reload_site_inventory(platform_path, ce=ce, caller=caller))
        if not answer["ok"]:
            return await pf_failed(sid, user, caller, lang, ce, t["pf_fail"] + web_board.plain_reason(answer.get("message"), lang))
        notice = {"queued": "inv_queued", "no_agent": "inv_no_agent"}.get(answer["preflight"])
        if notice is None:
            return await pf_failed(sid, user, caller, lang, ce, t["pf_fail"] + web_board.plain_reason(answer.get("message") or "", lang))
        return RedirectResponse(pf_where(ce, lang, notice), status_code=303, headers=_HEADERS)

    async def usage_page(request):
        sid, user = user_of(request)
        if user is None:
            return unauth(request)
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
        who = info["client_name"] or "(未命名 unnamed)"
        if info["form_ok"]:
            limits = ("<p>允許後，該連接器可讀取您的分析紀錄，並可請求送出分析。送出前，可在 AI 程式中顯示「送出」表單，由您本人於表單上按下；"
                      "該連接器不能代為按下。 (It can read your runs and ask to launch; the AI app can show you a 送出 form and you press it yourself.)</p>")
        else:
            limits = ("<p>允許後，該連接器可讀取您的分析紀錄，並可請求送出分析；但<strong>不能代您送出</strong>——"
                      "每次送出或取消，都須由您本人於本網站的確認頁按「送出」。 (It can read your runs and ask to launch; it cannot send an analysis: "
                      "each launch or cancel must be confirmed by you on this website.)</p>")
        body = ("<p>名為 <strong>%s</strong> 的連接器（程式代號 %s）要求連線至本平台，並以<strong>您的身分</strong>運作。</p>"
                "<p>連線完成後將導回：<strong>%s</strong>。若不認得該網站，請按「拒絕」。</p>"
                "%s"
                "<form method=\"post\" action=\"/consent/%s\"><input type=\"hidden\" name=\"csrf\" value=\"%s\">"
                "<button type=\"submit\" name=\"decision\" value=\"allow\">允許</button> "
                "<button type=\"submit\" name=\"decision\" value=\"deny\">拒絕</button></form>"
                % (_esc(who), _esc(info["client_id"]), _esc(info["redirect_host"]), limits, info["id"], _esc(consent_csrf(sid, info["id"]))))
        return _page("允許連接器 (allow a connector)", body, form_action=info["redirect_origin"])

    def consent_gone(info):
        if info["decision"] is not None:
            return _page("已處理", "<p>該申請已處理完畢。請返回連接器重新開始。</p>", 409)
        if info["expired"]:
            return _page("已逾時", "<p class=\"bad\">該申請已逾時（10 分鐘）。請返回連接器重新開始。</p>", 410)
        return None

    async def consent_get(request):
        rid = request.path_params["rid"]
        info = provider.consent_request(rid) if RID.match(rid) else None
        if info is None:
            return _page("找不到 (not found)", "<p>無此申請。</p>", 404)
        gone = consent_gone(info)
        if gone is not None:
            return gone
        sid, user = user_of(request)
        if user is None:
            return to_welcome(request) or _login_form("/consent/" + rid)
        return consent_page(info, sid)

    async def consent_post(request):
        if not same_origin(request):
            return foreign(request)
        rid = request.path_params["rid"]
        info = provider.consent_request(rid) if RID.match(rid) else None
        if info is None:
            return _page("找不到 (not found)", "<p>無此申請。</p>", 404)
        sid, user = user_of(request)
        if user is None:
            return to_welcome(request) or _login_form("/consent/" + rid, "請先登入 (log in first)", 401)
        form = await body_of(request)
        if not _same(form.get("csrf", ""), consent_csrf(sid, rid)):
            return _page("表單已失效", "<p class=\"bad\">表單驗證碼不符或已失效，未變更任何內容。請重新整理頁面後再操作。</p>", 403)
        decision = form.get("decision")
        if decision not in ("allow", "deny"):
            return _page("未處理", "<p class=\"bad\">請按「允許」或「拒絕」。</p>", 400)
        status, location = provider.consent_decide(rid, user["user_id"], decision)
        if location is not None:
            return RedirectResponse(location, status_code=302, headers=_HEADERS)
        gone = consent_gone(provider.consent_request(rid)) if status in ("decided", "expired") else None
        return gone or _page("未處理", "<p class=\"bad\">未變更任何內容。請返回連接器重新開始。</p>", 403 if status == "user" else 404)

    app = Starlette(routes=[Route("/", board, methods=["GET"]), Route("/settings", settings, methods=["GET"]),
                            Route("/settings/pipelines", pipelines_post, methods=["POST"]),
                            Route("/settings/pipelines/confirm", pipelines_confirm_post, methods=["POST"]),
                            Route("/settings/inventory", inventory_post, methods=["POST"]), Route("/usage", usage_page, methods=["GET"]),
                            Route("/launch", launch_get, methods=["GET"]), Route("/launch/diagram", launch_diagram, methods=["GET"]),
                            Route("/launch", launch_post, methods=["POST"]),
                            Route("/upload", upload_get, methods=["GET"]), Route("/upload", upload_post, methods=["POST"]),
                            Route("/upload/{batch}", upload_batch_get, methods=["GET"]),
                            Route("/act/{verb}", act_post, methods=["POST"]), Route("/login", login_form, methods=["GET"]), Route("/login", login_post, methods=["POST"]),
                            Route("/logout", logout_post, methods=["POST"]),
                            Route("/welcome", welcome_get, methods=["GET"]), Route("/welcome", welcome_post, methods=["POST"]),
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
