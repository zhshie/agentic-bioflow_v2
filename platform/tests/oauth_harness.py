# Nothing existing: glue for the 009i tests (a web app with the OAuth routes in a test client, a PKCE pair, the whole consent walk, the MCP app served on a thread); no library plays "a connector and the person who clicks Allow".
"""Helpers for the OAuth tests (spec 009i): the authorization server in a test client, the connector side of the flow, the MCP door."""
import base64
import hashlib
import secrets
import sqlite3
import threading
import time
from urllib.parse import parse_qs, urlparse

import httpx

from helpers import free_port, wait_port

BASE = "http://127.0.0.1:8789"          # the issuer the tests use: loopback http is the one http issuer the SDK allows
REDIRECT = "https://claude.example/cb"
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def tokens_rows(w, text, args=()):
    con = sqlite3.connect(str(w.ip.tokens))
    con.row_factory = sqlite3.Row
    try:
        return con.execute(text, args).fetchall()
    finally:
        con.close()


def tokens_sql(w, text, args=()):
    con = sqlite3.connect(str(w.ip.tokens))
    try:
        with con:
            return con.execute(text, args).rowcount
    finally:
        con.close()


def dump(w, *tables):
    """Every row of the named tables of tokens.db, to compare before and after."""
    return {t: [tuple(r) for r in tokens_rows(w, "SELECT * FROM %s ORDER BY 1" % t)] for t in tables}


class Flow:
    """What the connector holds after one walk: the pieces it needs for /token."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def token_form(self, **over):
        form = {"grant_type": "authorization_code", "code": self.code, "code_verifier": self.verifier,
                "client_id": self.client_id, "redirect_uri": self.redirect}
        form.update(over)
        return {k: v for k, v in form.items() if v is not None}


class Rig:
    """The authorization server (the 009c web app with the OAuth routes) in a test client, plus the connector's moves."""

    def __init__(self, w, public_url=None, base_url=BASE, clock=None, client=("127.0.0.1", 50000)):
        from starlette.testclient import TestClient
        from abf_platform import web
        self.w = w
        self.base = base_url
        self.app = web.create_app(w.ip.index, w.ip.tokens, w.ip.state_db, clock=clock or w.clock, public_url=public_url, base_url=base_url)
        self.c = TestClient(self.app, base_url=base_url, follow_redirects=False, client=client)

    def another(self, client=("127.0.0.1", 50001)):
        """A second browser (no cookie) on the same server."""
        from starlette.testclient import TestClient
        return TestClient(self.app, base_url=self.base, follow_redirects=False, client=client)

    # ---- the connector -----------------------------------------------------------------------------------------
    def register(self, redirect_uris=None, c=None, **meta):
        body = {"redirect_uris": redirect_uris or [REDIRECT], "client_name": "Claude", "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"]}
        body.update(meta)
        return (c or self.c).post("/register", json=body)

    def new_client(self, redirect_uris=None, **meta):
        r = self.register(redirect_uris, **meta)
        assert r.status_code == 201, r.text
        return r.json()["client_id"]

    def authorize(self, client_id, challenge, redirect=REDIRECT, state="st-1", c=None, **extra):
        params = {"client_id": client_id, "redirect_uri": redirect, "response_type": "code", "code_challenge": challenge,
                  "code_challenge_method": "S256", "state": state}
        params.update(extra)
        params = {k: v for k, v in params.items() if v is not None}
        return (c or self.c).get("/authorize", params=params)

    def consent_path(self, response):
        assert response.status_code == 302, (response.status_code, response.text)
        loc = urlparse(response.headers["location"])
        assert loc.path.startswith("/consent/"), loc
        return loc.path

    def token(self, form, c=None, headers=None):
        return (c or self.c).post("/token", data=form, headers=headers or {})

    def start(self, client_id=None, redirect=REDIRECT, state="st-1", c=None, **extra):
        """register (unless given) + /authorize: returns (consent path, verifier, client_id)."""
        cid = client_id or self.new_client([redirect])
        verifier, challenge = pkce()
        r = self.authorize(cid, challenge, redirect=redirect, state=state, c=c, **extra)
        return self.consent_path(r), verifier, cid

    # ---- the person ------------------------------------------------------------------------------------------------
    def log_in(self, name, c=None):
        r = self.w.login(c or self.c, name)
        assert r.status_code in (200, 303), r.text
        return r

    def csrf(self, path, c=None):
        from human_harness import csrf_of
        page = (c or self.c).get(path)
        assert page.status_code == 200, page.text
        token = csrf_of(page.text)
        assert token, page.text
        return token

    def decide(self, path, decision="allow", c=None, csrf=None, **extra):
        c = c or self.c
        token = self.csrf(path, c) if csrf is None else csrf
        form = {"csrf": token, "decision": decision}
        form.update(extra)
        return c.post(path, data=form)

    def flow(self, name="ann", redirect=REDIRECT, client_id=None, decision="allow", state="st-1", c=None, **extra):
        """The whole walk up to the code: register, authorize, log in as `name` (if not yet), press Allow. Returns a Flow."""
        c = c or self.c
        path, verifier, cid = self.start(client_id=client_id, redirect=redirect, state=state, c=c, **extra)
        if not c.cookies.get("abf_web"):
            self.log_in(name, c)
        token = self.csrf(path, c)
        r = self.decide(path, decision, c=c, csrf=token)
        assert r.status_code == 302, (r.status_code, r.text)
        loc = urlparse(r.headers["location"])
        q = parse_qs(loc.query)
        return Flow(path=path, csrf=token, verifier=verifier, client_id=cid, redirect=redirect, state=q.get("state", [None])[0],
                    code=q.get("code", [None])[0], error=q.get("error", [None])[0], location=r.headers["location"])

    def tokens_for(self, name="ann", **kw):
        """flow() + /token: the JSON with access_token and refresh_token."""
        f = self.flow(name, **kw)
        r = self.token(f.token_form())
        assert r.status_code == 200, r.text
        out = r.json()
        out["flow"] = f
        return out

    def refresh(self, refresh_token, client_id, **over):
        form = {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": client_id}
        form.update(over)
        return self.token(form)


class Served:
    """The MCP app behind the bearer check, served by uvicorn on a thread of this process (so a test can move the clock)."""

    def __init__(self, w, public_url=None, platform_path=None):
        import uvicorn
        from abf_platform import mcp_server
        self.port = free_port()
        kw = {"public_url": public_url} if public_url else {}
        app = mcp_server.build_http_app(w.ip.index, tokens_path=w.ip.tokens, **kw)
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        wait_port(self.port)
        time.sleep(0.3)
        self.url = "http://127.0.0.1:%d/mcp" % self.port
        self.root = "http://127.0.0.1:%d" % self.port
        return self

    def __exit__(self, *a):
        self.server.should_exit = True
        self.thread.join(timeout=15)

    def post(self, token=None, headers=None, path="/mcp", body=INIT):
        h = dict(MCP_HEADERS)
        if token is not None:
            h["Authorization"] = "Bearer " + token
        h.update(headers or {})
        return httpx.post(self.root + path, json=body, headers=h, timeout=10)


def mcp_post(port, token=None, path="/mcp", method="POST", headers=None, body=INIT):
    h = dict(MCP_HEADERS)
    if token is not None:
        h["Authorization"] = "Bearer " + token
    h.update(headers or {})
    return httpx.request(method, "http://127.0.0.1:%d%s" % (port, path), json=body if method in ("POST", "PUT") else None, headers=h, timeout=10)


def pat_of(w, name):
    from abf_platform import store
    return store.create_token(w.ip.tokens, kind="pat", user_id=store.user_id_of(w.ip.tokens, name))


def table_counts(w):
    return {t: tokens_rows(w, "SELECT COUNT(*) FROM %s" % t)[0][0] for t in ("oauth_requests", "oauth_codes", "tokens", "web_sessions")}
