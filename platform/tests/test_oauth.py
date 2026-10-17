# Nothing existing: tests of the minimal OAuth 2.1 of spec 009i (discovery, registration, consent, tokens, the MCP door, the gate that stays shut); the flows and the refusals are ours.
"""Spec 009i: Claude Desktop's custom connector reaches the HTTP MCP server with a web login and one click, not a pasted token.
Test cases are named in the comments (TC-A01 ...), see specs/009i-oauth/test-case.md."""
import json
import re
import sqlite3
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from helpers import free_port, pkg_env, run_cli, start_cli, stop_proc, wait_port
from human_harness import PASSWORD, World, csrf_of
from oauth_harness import BASE, INIT, REDIRECT, Rig, Served, dump, mcp_post, pkce, tokens_rows, tokens_sql

MCP_PUBLIC = "https://mcp.example"
WEB_PUBLIC = "https://abf.example"
PROTECTED = "/.well-known/oauth-protected-resource/mcp"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def rig(w):
    return Rig(w)


def oauth():
    from abf_platform import oauth as module
    return module


def pat_of(w, name):
    from abf_platform import store
    return store.create_token(w.ip.tokens, kind="pat", user_id=store.user_id_of(w.ip.tokens, name))


def mcp_process(w, tmp_path, *args):
    port = free_port()
    env = pkg_env(ABF_PLATFORM_DB=w.ip.index)
    proc = start_cli(["mcp", "--http", "--port", str(port)] + list(args), env, tmp_path / ("mcp-%d.log" % port))
    wait_port(port, proc=proc)
    return port, proc


# ---- US1: the platform announces itself --------------------------------------------------------------------------------

def test_tca01_a02_the_mcp_process_serves_the_resource_metadata_and_the_401_points_to_it(w, tmp_path):
    # TC-A01, TC-A02
    w.user("ann")
    Rig(w, public_url=WEB_PUBLIC, base_url=WEB_PUBLIC)     # the web app writes its address into platform.db
    port, proc = mcp_process(w, tmp_path, "--public-url", MCP_PUBLIC)
    try:
        for r in (mcp_post(port), mcp_post(port, "garbage-token")):
            assert r.status_code == 401
            challenge = r.headers["www-authenticate"]
            m = re.fullmatch(r'Bearer resource_metadata="([^"]+)"', challenge)
            assert m, challenge
            assert m.group(1) == MCP_PUBLIC + PROTECTED
            assert "garbage-token" not in r.text + str(dict(r.headers))
        meta = httpx.get("http://127.0.0.1:%d%s" % (port, PROTECTED), timeout=10)
        assert meta.status_code == 200
        doc = meta.json()
        assert doc["resource"].rstrip("/") == MCP_PUBLIC + "/mcp"
        assert [a.rstrip("/") for a in doc["authorization_servers"]] == [WEB_PUBLIC]
        assert "ann" not in meta.text and "password" not in meta.text.lower()
    finally:
        stop_proc(proc)


def test_tca03_the_web_app_serves_the_authorization_server_metadata_with_s256_only(w):
    # TC-A03
    rig = Rig(w, public_url=WEB_PUBLIC, base_url=WEB_PUBLIC)
    r = rig.c.get("/.well-known/oauth-authorization-server")
    assert r.status_code == 200
    m = r.json()
    base = WEB_PUBLIC
    assert m["issuer"].rstrip("/") == base
    assert m["authorization_endpoint"] == base + "/authorize" and m["token_endpoint"] == base + "/token"
    assert m["registration_endpoint"] == base + "/register" and m["revocation_endpoint"] == base + "/revoke"
    assert m["code_challenge_methods_supported"] == ["S256"]
    assert m["response_types_supported"] == ["code"]
    assert sorted(m["grant_types_supported"]) == ["authorization_code", "refresh_token"]


def test_tca04_nothing_else_on_the_mcp_process_answers_without_a_token(w, tmp_path):
    # TC-A04
    w.user("ann")
    Rig(w, public_url=WEB_PUBLIC, base_url=WEB_PUBLIC)
    port, proc = mcp_process(w, tmp_path, "--public-url", MCP_PUBLIC)
    try:
        ok = mcp_post(port, method="GET", path=PROTECTED)
        assert ok.status_code == 200
        paths = ["/mcp", "/", "/authorize", "/token", "/register", "/revoke", "/.well-known/oauth-authorization-server",
                 "/.well-known/", "/.well-known/oauth-protected-resource", "/.well-known/openid-configuration", PROTECTED + "x",
                 PROTECTED + "/"]
        for path in paths:
            for method in ("GET", "POST", "DELETE"):
                r = mcp_post(port, method=method, path=path)
                assert r.status_code in (401, 404, 405), (method, path, r.status_code)
        for method in ("POST", "PUT", "DELETE"):
            r = mcp_post(port, method=method, path=PROTECTED)
            assert r.status_code in (401, 404, 405), method
        # with a token the other paths are the MCP app's, never an authorization server
        pat = pat_of(w, "ann")
        for path in ("/authorize", "/token", "/register", "/revoke", "/.well-known/oauth-authorization-server"):
            assert mcp_post(port, pat, method="GET", path=path).status_code == 404, path
    finally:
        stop_proc(proc)


def test_tca05_without_a_public_url_the_challenge_stays_bare_and_the_pat_works(w, tmp_path):
    # TC-A05
    w.user("ann")
    pat = pat_of(w, "ann")
    port, proc = mcp_process(w, tmp_path)
    try:
        for token in (None, "wrong-token"):
            r = mcp_post(port, token)
            assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
            assert "wrong-token" not in r.text
        assert mcp_post(port, pat).status_code == 200
        assert mcp_post(port, method="GET", path=PROTECTED).status_code == 401
    finally:
        stop_proc(proc)


def test_tca06_h03_the_receiver_and_the_platform_app_have_no_oauth_routes(tmp_path):
    # TC-A06, TC-H03
    from starlette.testclient import TestClient
    from helpers import Clock, Platform
    plat = Platform(tmp_path / "p", clock=Clock())
    c = TestClient(plat.app)
    for path in ("/.well-known/oauth-authorization-server", "/.well-known/oauth-protected-resource", "/authorize", "/token", "/register",
                 "/revoke", "/oauth/token", "/oauth/authorize", "/consent/" + "a" * 32):
        for method in ("GET", "POST"):
            assert c.request(method, path).status_code in (401, 404, 405), (method, path)
        assert not [r for r in plat.app.routes if getattr(r, "path", "") == path]


def test_tca07_a_plain_http_public_address_is_refused_and_a_loopback_one_serves_its_own_metadata(w):
    # TC-A07
    rc, out = w.ip.run("web", "--public-url", "http://abf.example")
    assert rc == 1 and "https" in out
    loop = Rig(w, public_url="http://127.0.0.1:9123", base_url="http://127.0.0.1:9123")
    assert loop.c.get("/.well-known/oauth-authorization-server").json()["issuer"].rstrip("/") == "http://127.0.0.1:9123"
    unset = Rig(w, base_url=BASE)
    assert unset.c.get("/.well-known/oauth-authorization-server").json()["issuer"].rstrip("/") == BASE


# ---- US2: registration grants nothing -------------------------------------------------------------------------------------

def test_tcb01_a_connector_registers_itself_as_a_public_client(w, rig):
    # TC-B01
    before = len(tokens_rows(w, "SELECT * FROM oauth_clients")) if tokens_rows(w, "SELECT name FROM sqlite_master WHERE name = 'oauth_clients'") else 0
    r = rig.register()
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["client_id"] and not body.get("client_secret")
    assert body["redirect_uris"] == [REDIRECT]
    assert len(tokens_rows(w, "SELECT * FROM oauth_clients")) == before + 1


def test_tcb02_loopback_redirects_are_accepted(w, rig):
    # TC-B02
    for uri in ("http://127.0.0.1:8765/cb", "http://localhost:1/cb", "http://[::1]:9/cb"):
        assert rig.register([uri]).status_code == 201, uri


def test_tcb03_a_redirect_that_is_neither_https_nor_loopback_is_refused_whole(w, rig):
    # TC-B03
    assert rig.register().status_code == 201
    before = dump(w, "oauth_clients")
    for bad in (["http://evil.example/cb"], ["javascript:alert(1)"], ["file:///x"], ["ftp://h/x"], ["claude-no-scheme"],
                ["https://claude.example/cb", "http://evil.example/cb"], ["https://u:p@claude.example/cb"],
                ["https://claude.example/cb#frag"]):
        r = rig.register(bad)
        assert r.status_code == 400, (bad, r.status_code, r.text)
    assert dump(w, "oauth_clients") == before


def test_tcb04_the_two_hundred_and_first_client_is_refused(w, rig):
    # TC-B04
    cid = rig.new_client()
    now = w.clock()
    for i in range(oauth().MAX_CLIENTS - 1):
        tokens_sql(w, "INSERT INTO oauth_clients (client_id, info_json, created_at, last_used_at) VALUES (?, ?, ?, ?)",
                   ("filler-%d" % i, json.dumps({"client_id": "filler-%d" % i, "redirect_uris": [REDIRECT]}), now, now))
    assert tokens_rows(w, "SELECT COUNT(*) FROM oauth_clients")[0][0] == oauth().MAX_CLIENTS == 200
    r = rig.register()
    assert r.status_code == 400, r.text
    assert tokens_rows(w, "SELECT COUNT(*) FROM oauth_clients")[0][0] == 200
    verifier, challenge = pkce()
    assert rig.authorize(cid, challenge).status_code == 302        # an existing client still walks


def test_tcb05_one_address_cannot_register_without_end(w):
    # TC-B05
    mod = oauth()
    assert 0 < mod.REGISTRATIONS_PER_HOUR < mod.MAX_CLIENTS
    rig = Rig(w, client=("203.0.113.9", 1))
    for _ in range(mod.REGISTRATIONS_PER_HOUR):
        assert rig.register().status_code == 201
    assert rig.register().status_code == 429
    other = rig.another(client=("203.0.113.10", 1))
    assert rig.register(c=other).status_code == 201
    w.clock.t += 3601
    assert rig.register().status_code == 201


def test_tcb06_a_client_unused_for_thirty_days_is_gone_and_a_used_one_stays(w, rig):
    # TC-B06
    x = rig.new_client()
    y = rig.new_client()
    w.clock.t += 29 * 86400
    verifier, challenge = pkce()
    assert rig.authorize(y, challenge).status_code == 302                  # Y is used on day 29
    w.clock.t += 86400 + 1                                                  # day 30 and a second since X registered
    assert rig.authorize(x, challenge).status_code == 400
    assert not tokens_rows(w, "SELECT 1 FROM oauth_clients WHERE client_id = ?", (x,))
    assert rig.authorize(y, challenge).status_code == 302


def test_tcb07_a_registration_alone_grants_nothing(w, rig, tmp_path):
    # TC-B07
    w.user("ann")
    before = dump(w, "oauth_codes", "tokens", "users", "web_sessions")
    state_before = (w.sql("SELECT * FROM confirmations"), w.sql("SELECT * FROM jobs WHERE kind <> 'preflight'"))
    cid = rig.new_client()
    verifier, challenge = pkce()
    r = rig.token({"grant_type": "authorization_code", "code": "nothing", "code_verifier": verifier, "client_id": cid, "redirect_uri": REDIRECT})
    assert r.status_code == 400 and "access_token" not in r.text
    with Served(w, public_url=MCP_PUBLIC) as s:
        assert s.post().status_code == 401
    assert dump(w, "oauth_codes", "tokens", "users", "web_sessions") == before
    assert (w.sql("SELECT * FROM confirmations"), w.sql("SELECT * FROM jobs WHERE kind <> 'preflight'")) == state_before


def test_tcb08_no_other_grant_or_response_type_is_registered_or_served(w, rig):
    # TC-B08
    for meta in ({"grant_types": ["implicit"]}, {"grant_types": ["client_credentials"]}, {"grant_types": ["password"]},
                 {"grant_types": ["authorization_code", "implicit"]}, {"response_types": ["token"]},
                 {"grant_types": ["authorization_code", "client_credentials"]}, {"response_types": ["code", "token"]}):
        assert rig.register(**meta).status_code == 400, meta
    cid = rig.new_client()
    for grant in ("implicit", "client_credentials", "password", "urn:ietf:params:oauth:grant-type:jwt-bearer"):
        r = rig.token({"grant_type": grant, "client_id": cid, "username": "ann", "password": PASSWORD, "assertion": "x"})
        assert r.status_code in (400, 401) and r.json()["error"] in ("unsupported_grant_type", "invalid_request", "unauthorized_client"), (grant, r.text)
        assert "access_token" not in r.text
