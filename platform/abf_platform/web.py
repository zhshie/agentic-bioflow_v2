# Not Starlette's SessionMiddleware or an OAuth login: they keep the whole session in the cookie, or hand login to another service; this is six routes, a password hash that only a terminal can set, and a cookie whose id is kept as a hash.
"""The confirmation page (spec 009c): where a person presses 送出, as the same user that the AI asked for.

A separate small app (`abf-platform web`), not part of the MCP server's bearer check and not part of the receiver: a browser has no
bearer token and must never be given one. Spec 011a added the first page that shows anything but a login or one request: GET /, the
three-pane board (my runs, the stage board of one run, all my runs by stage), read-only and for the logged-in user's own runs only.
The only routes there are:

  GET  /             the board (spec 011a): ?run=<id> picks the run of the middle pane, ?stage=<name> its stage; needs the cookie
  GET  /login        the login form (name + web password)
  POST /login        log in; the password is checked against its scrypt hash; a cookie of 12 hours
  POST /logout       end this browser login
  GET  /c/{rid}      the summary of one pending request, for the user who made it; never changes anything
  POST /c/{rid}      the button: needs the cookie, the same user as the request, and the CSRF token of this login and this request

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

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route

from . import actions, store, web_board

COOKIE = "abf_web"
KEY_FILE = "web_signing.key"
RID = re.compile(r"^[0-9a-f]{32}\Z")
FAIL_LIMIT = 5              # failures within FAIL_WINDOW that block one name
IP_FAIL_LIMIT = 20          # failures within FAIL_WINDOW that block one client address (many names from one address)
FAIL_WINDOW = 60.0
MAX_TRACKED = 10000         # names (and addresses) with a live failure window; past this, new ones are refused, no live counter is dropped
MAX_NAME_CHARS = 100
MAX_BODY = 16384
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
_HEADERS = {"Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src %s; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
            % web_board.style_source()}
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


def _page(title, body, status=200):
    return HTMLResponse(web_board.document(title, "<h1>%s</h1>%s" % (_esc(title), body)), status_code=status, headers=_HEADERS)


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


def create_app(index_path, tokens_path=None, platform_path=None, *, clock=time.time, public_url=None):
    """The confirmation page as an ASGI app. `clock` and the files are parameters so a test can move time and use its own folder."""
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
        return _login_form(nxt if RID.match(nxt[3:]) and nxt.startswith("/c/") else "")

    async def login_post(request):
        if not same_origin(request):
            return foreign(request)
        form = await body_of(request)
        raw_name = str(form.get("name", ""))
        name = raw_name[:MAX_NAME_CHARS]
        password = str(form.get("password", ""))
        ip = request.client.host if request.client else ""
        nxt = form.get("next", "")
        nxt = nxt if nxt.startswith("/c/") and RID.match(nxt[3:]) else ""
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

    def state_page(req, sid, rid):
        title = "送出確認" if req["kind"] == "launch" else "取消確認"
        shown = "<pre>%s</pre>" % _esc(req["summary"] or "")
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
        return answer or state_page(req, sid, rid)

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

    async def board(request):
        sid, user = user_of(request)
        if user is None:
            return RedirectResponse("/login", status_code=303, headers=_HEADERS)
        caller = actions.Caller(user["user_id"], user["name"], user["lab"])
        run_id = request.query_params.get("run") or ""
        selected = None
        if run_id:
            selected = await run_in_threadpool(read_run, run_id, caller)
            if selected is None:        # another person's run and a missing id answer alike, and the page never repeats the id
                return _page("找不到 (not found)", "<p>沒有這個 run。</p>", 404)
        runs = await run_in_threadpool(read_runs, caller)
        doc = web_board.render_board(user["name"], csrf(sid, "logout"), runs, selected, request.query_params.get("stage"))
        return HTMLResponse(doc, headers=_HEADERS)

    app = Starlette(routes=[Route("/", board, methods=["GET"]), Route("/login", login_form, methods=["GET"]), Route("/login", login_post, methods=["POST"]),
                            Route("/logout", logout_post, methods=["POST"]),
                            Route("/c/{rid}", confirm_get, methods=["GET"]), Route("/c/{rid}", confirm_post, methods=["POST"])])
    app.state.csrf_token = csrf_token
    return app
