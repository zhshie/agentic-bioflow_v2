# Not Starlette's SessionMiddleware or an OAuth login: they keep the whole session in the cookie, or hand login to another service; this is five routes, a password hash that only a terminal can set, and a cookie whose id is kept as a hash.
"""The confirmation page (spec 009c): where a person presses 送出, as the same user that the AI asked for.

A separate small app (`abf-platform web`), not part of the MCP server's bearer check and not part of the receiver: a browser has no
bearer token and must never be given one. The only routes there are:

  GET  /login        the login form (name + web password)
  POST /login        log in; the password is checked against its scrypt hash; a cookie of 12 hours
  POST /logout       end this browser login
  GET  /c/{rid}      the summary of one pending request, for the user who made it; never changes anything
  POST /c/{rid}      the button: needs the cookie, the same user as the request, and the CSRF token of this login and this request

`Authorization: Bearer` is never looked at here: an AI that holds a personal access token cannot log in, cannot read a summary and
cannot press the button. The cookie is `<random id>.<signature>`; only the sha256 of the id is stored (tokens.db, web_sessions).
Everything the page shows is escaped, and a content-security-policy forbids scripts anyway.
"""
import collections
import hashlib
import hmac
import html
import os
import re
import time
import urllib.parse
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route

from . import actions, store

COOKIE = "abf_web"
KEY_FILE = "web_signing.key"
RID = re.compile(r"^[0-9a-f]{32}\Z")
FAIL_LIMIT = 5
FAIL_WINDOW = 60.0
MAX_BODY = 16384
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
_HEADERS = {"Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"}


def _signing_key(folder):
    """The key that signs cookies and CSRF tokens: made once, owner-only, kept next to the databases, never printed."""
    path = Path(folder) / KEY_FILE
    Path(folder).mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_bytes().strip()
    key = os.urandom(32).hex().encode("ascii")
    with os.fdopen(fd, "wb") as f:
        f.write(key + b"\n")
    return key


def _mac(key, *parts):
    return hmac.new(key, "\x1f".join(parts).encode("utf-8"), hashlib.sha256).hexdigest()


def _esc(text):
    return html.escape(str(text), quote=True)


def _page(title, body, status=200):
    doc = ("<!doctype html><html lang=\"zh-Hant\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">"
           "<title>%s</title><style>body{font-family:sans-serif;max-width:60em;margin:1.5em auto;padding:0 1em}"
           "pre{background:#f4f4f4;padding:1em;overflow-x:auto;white-space:pre-wrap}button{font-size:1.1em;padding:.4em 1.2em}"
           ".bad{color:#a00}.ok{color:#070}</style></head><body><h1>%s</h1>%s</body></html>" % (_esc(title), _esc(title), body))
    return HTMLResponse(doc, status_code=status, headers=_HEADERS)


def _login_form(next_path="", message="", status=200):
    note = "<p class=\"bad\">%s</p>" % _esc(message) if message else ""
    nxt = "<input type=\"hidden\" name=\"next\" value=\"%s\">" % _esc(next_path) if next_path else ""
    return _page("登入 (log in)", note + "<p>請用你的姓名與<strong>網頁密碼</strong>登入（網頁密碼不是 AI 用的權杖；它只能在終端機用 "
                 "<code>abf-platform user passwd</code> 設定）。</p><form method=\"post\" action=\"/login\">"
                 "<p><label>姓名 <input name=\"name\" autocomplete=\"username\" required></label></p>"
                 "<p><label>密碼 <input name=\"password\" type=\"password\" autocomplete=\"current-password\" required></label></p>"
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
    failures = collections.defaultdict(list)

    def cookie_value(sid):
        return "%s.%s" % (sid, _mac(key, "cookie", sid))

    def session_id(request):
        raw = request.cookies.get(COOKIE) or ""
        sid, dot, sig = raw.partition(".")
        if not dot or not sid or not hmac.compare_digest(sig, _mac(key, "cookie", sid)):
            return None
        return sid

    def user_of(request):
        sid = session_id(request)
        return (sid, store.web_session_user(tokens_path, sid, clock())) if sid else (None, None)

    def csrf(sid, rid):
        return _mac(key, "csrf", sid, rid)

    def csrf_token(cookie, rid):
        return csrf(cookie.split(".")[0], rid)

    def blocked(name, now):
        recent = [t for t in failures.get(name, ()) if now - t < FAIL_WINDOW]
        if recent:
            failures[name] = recent
        else:
            failures.pop(name, None)
        return len(recent) >= FAIL_LIMIT

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
        form = await body_of(request)
        name = str(form.get("name", ""))[:100]
        password = str(form.get("password", ""))[:1000]
        nxt = form.get("next", "")
        nxt = nxt if nxt.startswith("/c/") and RID.match(nxt[3:]) else ""
        now = clock()
        if blocked(name, now):
            return _login_form(nxt, "登入失敗太頻繁，請一分鐘後再試 (too many tries, wait a minute)", 429)
        who = store.check_web_password(tokens_path, name, password)
        if who is None:
            failures[name].append(now)
            if len(failures) > 2000:
                for old in list(failures)[:1000]:
                    failures.pop(old, None)
            return _login_form(nxt, "姓名或密碼不對 (wrong name or password)", 401)
        sid, _ = store.create_web_session(tokens_path, who["user_id"], now)
        if nxt:
            response = RedirectResponse(nxt, status_code=303, headers=_HEADERS)
        else:
            response = _page("已登入 (logged in)", "<p class=\"ok\">已登入為 %s。請回到 AI 給你的網址按「送出」。</p>"
                             "<form method=\"post\" action=\"/logout\"><input type=\"hidden\" name=\"csrf\" value=\"%s\">"
                             "<button type=\"submit\">登出</button></form>" % (_esc(who["name"]), _esc(csrf(sid, "logout"))))
        response.set_cookie(COOKIE, cookie_value(sid), max_age=int(store.WEB_SESSION_SECONDS), httponly=True, samesite="Strict",
                            secure=secure, path="/")
        return response

    async def logout_post(request):
        sid = session_id(request)
        form = await body_of(request)
        if sid and hmac.compare_digest(str(form.get("csrf", "")), csrf(sid, "logout")):
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
        if not hmac.compare_digest(str(form.get("csrf", "")), csrf(sid, rid)):
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

    app = Starlette(routes=[Route("/login", login_form, methods=["GET"]), Route("/login", login_post, methods=["POST"]),
                            Route("/logout", logout_post, methods=["POST"]),
                            Route("/c/{rid}", confirm_get, methods=["GET"]), Route("/c/{rid}", confirm_post, methods=["POST"])])
    app.state.csrf_token = csrf_token
    return app
