# Not Starlette's SessionMiddleware or an OAuth login: they keep the whole session in the cookie, or hand login to another service; this is five routes, a password hash that only a terminal can set, and a cookie whose id is kept as a hash.
"""The confirmation page (spec 009c): where a person presses 送出, as the same user that the AI asked for.

A separate small app (`abf-platform web`), not part of the MCP server's bearer check and not part of the receiver: a browser has no
bearer token and must never be given one. The only routes there are:

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
Everything the page shows is escaped, and a content-security-policy forbids scripts anyway.
"""
import hashlib
import hmac
import html
import os
import re
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

from . import actions, oauth, store

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
_HEADERS = {"Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"}


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
    doc = ("<!doctype html><html lang=\"zh-Hant\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">"
           "<title>%s</title><style>body{font-family:sans-serif;max-width:60em;margin:1.5em auto;padding:0 1em}"
           "pre{background:#f4f4f4;padding:1em;overflow-x:auto;white-space:pre-wrap}button{font-size:1.1em;padding:.4em 1.2em}"
           ".bad{color:#a00}.ok{color:#070}</style></head><body><h1>%s</h1>%s</body></html>" % (_esc(title), _esc(title), body))
    headers = _HEADERS
    if form_action:        # the consent form ends in a redirect to the connector, which a form-action rule also covers
        headers = dict(_HEADERS, **{"Content-Security-Policy": _HEADERS["Content-Security-Policy"].replace("form-action 'self'", "form-action 'self' " + form_action)})
    return HTMLResponse(doc, status_code=status, headers=headers)


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

    app = Starlette(routes=[Route("/login", login_form, methods=["GET"]), Route("/login", login_post, methods=["POST"]),
                            Route("/logout", logout_post, methods=["POST"]),
                            Route("/c/{rid}", confirm_get, methods=["GET"]), Route("/c/{rid}", confirm_post, methods=["POST"]),
                            Route("/consent/{rid}", consent_get, methods=["GET"]), Route("/consent/{rid}", consent_post, methods=["POST"])]
                    + auth_routes, middleware=[Middleware(oauth.RegisterBodyCap), Middleware(oauth.RegisterRateCap, clock=clock)])
    app.state.csrf_token = csrf_token
    return app
