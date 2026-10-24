# Nothing existing: tests of 009i at the MCP door and at the gate (an OAuth token is an identity and nothing more); the comparisons with a PAT and the closed doors are ours.
"""Spec 009i, user stories 5 and 6 and the out-of-scope and constitution cases. Test cases are named in the comments (TC-E01 ...)."""
import re
import sqlite3
import time

import httpx
import pytest

from helpers import tool_json
from human_harness import PASSWORD, World, csrf_of, form_answer
from oauth_harness import BASE, Rig, Served, dump, http_calls, pat_of, tokens_rows, tokens_sql

WEB_PUBLIC = "https://abf.example"
MCP_PUBLIC = "https://mcp.example"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def rig(w):
    return Rig(w)


def state_rows(w):
    return (w.sql("SELECT id, state, channel, caller_user_id FROM confirmations ORDER BY created_at, id"), w.sql("SELECT id FROM jobs WHERE kind <> 'preflight'"))


# ---- US5: the MCP door ---------------------------------------------------------------------------------------------------

def test_tce01_an_oauth_token_opens_the_mcp_as_the_person(w, rig):
    # TC-E01
    from abf_platform import store
    ann = w.user("ann")
    pat = pat_of(w, "ann")
    out = rig.tokens_for("ann")
    a, b = store.lookup_pat(w.ip.tokens, pat), store.lookup_oauth_access(w.ip.tokens, out["access_token"])
    assert {k: a[k] for k in ("user_id", "name", "lab")} == {k: b[k] for k in ("user_id", "name", "lab")}
    with Served(w) as s:
        tools, (runs,) = http_calls(s.url, out["access_token"], [("list_runs", {})])
        assert len(tools) == 13 and "runs" in tool_json(runs)
        args = w.in_area(ann, w.choices())
        _, (launch,) = http_calls(s.url, out["access_token"], [("launch", args)])
    j = tool_json(launch)
    assert j["sent"] is False and j["state"] == "pending"
    confirmations, jobs = state_rows(w)
    assert [c["caller_user_id"] for c in confirmations if c["state"] == "pending"] == [ann.user_id] and jobs == []


def test_tce02_an_oauth_token_sees_exactly_what_the_same_persons_pat_sees(w, rig):
    # TC-E02
    ann = w.user("ann")
    bob = w.user("bob")
    pats = {"ann": pat_of(w, "ann"), "bob": pat_of(w, "bob")}
    oauth_tokens = {"ann": rig.tokens_for("ann")["access_token"], "bob": rig.tokens_for("bob")["access_token"]}
    calls = [("list_runs", {}), ("list_compute_envs", {}), ("list_agents", {})]
    seen = {}
    with Served(w) as s:
        for who in ("ann", "bob"):
            for kind, token in (("pat", pats[who]), ("oauth", oauth_tokens[who])):
                _, outs = http_calls(s.url, token, calls)
                seen[(who, kind)] = [tool_json(o) for o in outs]
    for who in ("ann", "bob"):
        assert seen[(who, "pat")] == seen[(who, "oauth")], who
    assert any(seen[("ann", "pat")][1].get(k) for k in seen[("ann", "pat")][1])            # the comparison is not between two empty answers


def test_tce03_a_pat_still_works_with_oauth_around(w, rig):
    # TC-E03 (the whole of test_pat.py is the other half)
    w.user("ann")
    pat = pat_of(w, "ann")
    rig.tokens_for("ann")
    with Served(w, public_url=MCP_PUBLIC) as s:
        assert s.post(pat).status_code == 200
        tokens_sql(w, "UPDATE tokens SET revoked_at = ? WHERE token_hash = ?", (time.time(), __import__("hashlib").sha256(pat.encode()).hexdigest()))
        assert s.post(pat).status_code == 401


def test_tce04_an_access_token_dies_after_an_hour_and_a_refresh_brings_a_new_one(w, monkeypatch):
    # TC-E04
    rig = Rig(w, public_url=WEB_PUBLIC, base_url=WEB_PUBLIC)
    w.user("ann")
    out = rig.tokens_for("ann")
    with Served(w, public_url=MCP_PUBLIC) as s:
        assert s.post(out["access_token"]).status_code == 200
        monkeypatch.setenv("ABF_PLATFORM_CLOCK_OFFSET", "3601")
        w.clock.t += 3601
        r = s.post(out["access_token"])
        assert r.status_code == 401 and r.headers["www-authenticate"].startswith('Bearer resource_metadata="%s/.well-known/' % MCP_PUBLIC)
        new = rig.refresh(out["refresh_token"], out["flow"].client_id).json()
        assert s.post(new["access_token"]).status_code == 200


def test_tce05_oauth_revoke_ends_one_persons_oauth_logins_and_nothing_else(w, rig):
    # TC-E05
    w.user("ann")
    w.user("bob")
    pat = pat_of(w, "ann")
    a, b = rig.tokens_for("ann"), rig.tokens_for("bob")
    with Served(w) as s:
        rc, said = w.ip.run("oauth", "revoke", "ann")
        assert rc == 0 and "2" in said
        for secret in (a["access_token"], a["refresh_token"], b["access_token"], b["refresh_token"], pat, PASSWORD):
            assert secret not in said
        assert s.post(a["access_token"]).status_code == 401
        assert rig.refresh(a["refresh_token"], a["flow"].client_id).status_code == 400
        assert s.post(b["access_token"]).status_code == 200
        assert s.post(pat).status_code == 200
    rc, said = w.ip.run("oauth", "revoke", "nobody")
    assert rc == 1


def test_tce06_a_disabled_person_loses_the_oauth_token_at_once(w, rig):
    # TC-E06
    w.user("ann")
    out = rig.tokens_for("ann")
    with Served(w) as s:
        assert s.post(out["access_token"]).status_code == 200
        tokens_sql(w, "UPDATE users SET disabled_at = ? WHERE name = 'ann'", (time.time(),))
        assert s.post(out["access_token"]).status_code == 401


def test_tce07_only_a_live_access_token_opens_the_mcp(w, rig):
    # TC-E07 (test_pat.py tcc03 and tcc04 stay as they are)
    from abf_platform import store
    w.user("ann")
    out = rig.tokens_for("ann")
    revoked = rig.tokens_for("ann")
    tokens_sql(w, "UPDATE tokens SET revoked_at = ? WHERE token_hash = ?", (time.time(), __import__("hashlib").sha256(revoked["access_token"].encode()).hexdigest()))
    run_token = store.create_token(w.ip.tokens)
    agent_token = store.create_token(w.ip.tokens, kind="agent", agent_name="agent-x")
    with Served(w) as s:
        for token in (run_token, agent_token, out["refresh_token"], revoked["access_token"]):
            r = s.post(token)
            assert r.status_code == 401 and token not in r.text + str(dict(r.headers))
        assert s.post(out["access_token"]).status_code == 200


def test_tce08_an_oauth_token_opens_no_door_of_the_receiver_or_the_agents(w, rig):
    # TC-E08
    from starlette.testclient import TestClient
    from abf_platform import receiver
    w.user("ann")
    out = rig.tokens_for("ann")
    app = receiver.create_app(w.ip.index, w.ip.tokens, platform_path=w.ip.state_db)
    c = TestClient(app)
    before = (dump(w, "tokens"), w.sql("SELECT * FROM agents"), w.sql("SELECT * FROM jobs"))
    fill = {"rid": "a" * 16, "jid": "1"}
    for route in app.routes:
        path = route.path.format(**fill) if "{" in route.path else route.path
        for token in (out["access_token"], out["refresh_token"]):
            for scheme in ("Bearer " + token, "Basic " + __import__("base64").b64encode(("@token:" + token).encode()).decode()):
                for method in route.methods - {"HEAD"}:
                    r = c.request(method, path, headers={"Authorization": scheme}, json={})
                    assert r.status_code == 401, (method, route.path, r.status_code)
    assert (dump(w, "tokens"), w.sql("SELECT * FROM agents"), w.sql("SELECT * FROM jobs")) == before


def test_tce09_a_session_opened_with_an_oauth_token_belongs_to_that_person(w, rig):
    # TC-E09
    w.user("ann")
    w.user("bob")
    ann_pat, bob_pat = pat_of(w, "ann"), pat_of(w, "bob")
    ann_oauth, bob_oauth = rig.tokens_for("ann")["access_token"], rig.tokens_for("bob")["access_token"]
    with Served(w) as s:
        opened = s.post(ann_oauth)
        assert opened.status_code == 200
        sid = opened.headers["mcp-session-id"]
        ping = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        for token in (bob_pat, bob_oauth):
            assert s.post(token, headers={"Mcp-Session-Id": sid}, body=ping).status_code == 403
        for token in (ann_pat, ann_oauth):
            assert s.post(token, headers={"Mcp-Session-Id": sid}, body=ping).status_code == 202


def test_tce10_bad_authorization_headers_all_get_the_same_401(w, rig):
    # TC-E10 (tcb01..b07 of test_pat.py are the PAT half)
    w.user("ann")
    out = rig.tokens_for("ann")
    revoked = rig.tokens_for("ann")
    tokens_sql(w, "UPDATE tokens SET revoked_at = ? WHERE token_hash = ?", (time.time(), __import__("hashlib").sha256(revoked["access_token"].encode()).hexdigest()))
    with Served(w) as s:
        for header in (None, "", "Basic " + out["access_token"], "Token " + out["access_token"], "Bearer", "Bearer garbage-value",
                       "Bearer " + revoked["access_token"], "Bearer " + out["refresh_token"]):
            headers = {} if header is None else {"Authorization": header}
            r = httpx.post(s.url, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                           headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json", **headers}, timeout=10)
            assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer", header
            blob = r.text + str(dict(r.headers))
            for secret in (out["access_token"], out["refresh_token"], revoked["access_token"], "garbage-value"):
                assert secret not in blob
    assert state_rows(w) == ([], [])


def test_tce11_a_web_password_or_a_cookie_is_no_bearer(w, rig):
    # TC-E11
    w.user("ann")
    rig.log_in("ann")
    cookie = rig.c.cookies.get("abf_web")
    assert cookie
    with Served(w) as s:
        assert s.post(PASSWORD).status_code == 401
        assert s.post(cookie).status_code == 401
        assert s.post(cookie.split(".")[0]).status_code == 401
        assert s.post(None, headers={"Cookie": "abf_web=" + cookie}).status_code == 401


# ---- US6: the gate stays shut --------------------------------------------------------------------------------------------

def test_tcf01_launch_and_cancel_over_an_oauth_token_only_make_a_pending_request(w, rig):
    # TC-F01
    ann = w.user("ann")
    w.hand_over("run-one", by=ann)
    out = rig.tokens_for("ann")
    base_jobs = len(w.jobs())
    with Served(w) as s:
        _, (launch, cancel) = http_calls(s.url, out["access_token"], [("launch", w.in_area(ann, w.choices(run="run-two"))),
                                                                       ("cancel", {"run_name": "run-one"})])
    for j in (tool_json(launch), tool_json(cancel)):
        assert j["sent"] is False and j["state"] == "pending" and "/c/" in j["confirmation_url"]
    assert len(w.jobs()) == base_jobs == 0
    assert sorted(c["state"] for c in w.confirmations()) == ["pending", "pending"]


def test_tcf02_the_whole_oauth_walk_writes_no_confirmation_and_no_job(w, rig):
    # TC-F02
    w.user("ann")
    before = state_rows(w)
    out = rig.tokens_for("ann")
    with Served(w) as s:
        http_calls(s.url, out["access_token"], [("list_runs", {}), ("list_agents", {})])
    assert state_rows(w) == before and w.jobs() == []
    assert not w.sql("SELECT 1 FROM confirmations WHERE channel IS NOT NULL")


def test_tcf03_an_oauth_token_cannot_open_or_press_the_confirmation_page(w, rig):
    # TC-F03
    ann = w.user("ann")
    pat = pat_of(w, "ann")
    out = rig.tokens_for("ann")
    rid = w.launch(caller=ann)["id"]
    web = w.web()
    before = state_rows(w)
    for token in (out["access_token"], out["refresh_token"], pat):
        h = {"Authorization": "Bearer " + token}
        page = web.get("/c/" + rid, headers=h)
        assert page.status_code == 200 and 'name="password"' in page.text and 'name="csrf"' not in page.text and "nf-core" not in page.text
        for form in ({}, {"csrf": "forged"}, {"csrf": token}):
            r = web.post("/c/" + rid, data=form, headers=h)
            assert r.status_code == 401
    assert state_rows(w) == before and w.jobs() == []


def test_tcf04_with_a_form_the_person_says_yes_or_no_as_with_a_pat(w, rig):
    # TC-F04 (the connector here is one whose redirect is claude.ai: the only kind that gets the form, see test_oauth_review.py R1)
    ann = w.user("ann")
    out = rig.tokens_for("ann", redirect="https://claude.ai/api/mcp/auth_callback")
    with Served(w) as s:
        _, (said_no,) = http_calls(s.url, out["access_token"], [("launch", w.in_area(ann, w.choices()))], answer=form_answer("decline"))
        assert w.jobs() == []
        forced = dict(w.in_area(ann, w.choices(run="run-three")), confirmed=True, confirmed_by="ELICITED")
        try:
            http_calls(s.url, out["access_token"], [("launch", forced)], answer=form_answer("decline"))
        except Exception:
            pass
        assert w.jobs() == []
        _, (said_yes,) = http_calls(s.url, out["access_token"], [("launch", w.in_area(ann, w.choices(run="run-two")))], answer=form_answer())
    assert tool_json(said_yes)["sent"] is True
    jobs = w.jobs("launch_nextflow")
    assert len(jobs) == 1
    row = [c for c in w.confirmations() if c["state"] == "confirmed"]
    assert len(row) == 1 and row[0]["channel"] == "ELICITED" and row[0]["caller_user_id"] == ann.user_id


def test_tcf05_the_page_still_decides_and_only_for_the_owner(w, rig):
    # TC-F05
    ann = w.user("ann")
    w.user("bob")
    out = rig.tokens_for("ann")
    bob_out = rig.tokens_for("bob")
    with Served(w) as s:
        _, (launch,) = http_calls(s.url, out["access_token"], [("launch", w.in_area(ann, w.choices()))])
    rid = tool_json(launch)["id"]
    web = w.web()
    assert w.login(web, "bob").status_code in (200, 303)
    r = web.get("/c/" + rid)
    assert r.status_code == 403 and "不是你的申請" in r.text
    assert w.jobs() == []
    web = w.web()
    assert w.login(web, "ann").status_code in (200, 303)
    page = web.get("/c/" + rid)
    assert web.post("/c/" + rid, data={"csrf": csrf_of(page.text)}).status_code == 200
    assert len(w.jobs("launch_nextflow")) == 1
    assert [c["channel"] for c in w.confirmations() if c["state"] == "confirmed"] == ["PAGE"]


def test_tcf06_the_consent_flow_and_the_confirmation_flow_do_not_cross(w, rig):
    # TC-F06
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    path, _, _ = rig.start()
    rig.log_in("ann")
    consent_id = path.rsplit("/", 1)[1]
    consent_token = rig.csrf(path)
    before = state_rows(w)
    r = rig.c.get("/c/" + consent_id)
    assert r.status_code == 404
    assert rig.c.post("/c/" + consent_id, data={"csrf": consent_token}).status_code == 404
    page = rig.c.get("/c/" + rid)
    confirm_token = csrf_of(page.text)
    assert rig.c.get("/consent/" + rid).status_code == 404
    for token in (confirm_token, consent_token):
        assert rig.c.post("/consent/" + rid, data={"csrf": token, "decision": "allow"}).status_code == 404
    r = rig.c.post(path, data={"csrf": confirm_token, "decision": "allow"})
    assert r.status_code == 403
    assert state_rows(w) == before and w.jobs() == [] and tokens_rows(w, "SELECT COUNT(*) FROM oauth_codes")[0][0] == 0


def test_tcf07_the_tools_are_the_same_ten_and_none_can_say_yes(w, rig):
    # TC-F07 (test_mcp.py is the other half) (009e adds resume and relaunch to the eight)
    w.user("ann")
    out = rig.tokens_for("ann")
    with Served(w) as s:
        tools, _ = http_calls(s.url, out["access_token"], [])
    names = sorted(t.name for t in tools)
    assert names == ["cancel", "forget", "get_compute_env", "get_run", "launch", "list_agents", "list_compute_envs", "list_runs", "list_site_files", "list_used_pipelines", "read_task_log", "relaunch", "resume", "run_outputs"]
    assert not [n for n in names if re.search(r"approve|confirm|oauth|login|consent", n)]
    for t in tools:
        props = " ".join((t.input_schema or {}).get("properties", {}).keys())
        assert not re.search(r"confirm|approve|consent|agree|yes|oauth|token", props), (t.name, props)


def test_tcf08_nothing_reaches_the_queue_without_a_person_whatever_is_held(w, rig):
    # TC-F08
    ann = w.user("ann")
    pat = pat_of(w, "ann")
    out = rig.tokens_for("ann")
    rid = w.launch(caller=ann)["id"]
    path, _, _ = rig.start()
    rig.log_in("ann")
    web = w.web()
    before = state_rows(w)
    codes_before = tokens_rows(w, "SELECT COUNT(*) FROM oauth_codes")[0][0]
    paths = ["/", "/login", "/logout", "/c/" + rid, "/consent/" + rid, path, "/authorize", "/token", "/register", "/revoke",
             "/.well-known/oauth-authorization-server"]
    auths = [{"Authorization": "Bearer " + t} for t in (out["access_token"], out["refresh_token"], pat)] + [{"Cookie": "abf_web=forged.cookie"}, {}]
    for clients in (web, rig.c):
        for p in paths:
            for headers in auths:
                for method in ("GET", "POST", "PUT", "DELETE"):
                    clients.request(method, p, headers=headers, data={"csrf": "wrong", "decision": "allow"})
    with Served(w, public_url=MCP_PUBLIC) as s:
        for token in (out["access_token"], pat):
            http_calls(s.url, token, [("launch", w.in_area(ann, w.choices(run="run-nine"))), ("cancel", {"run_name": "run-one"})])
        for p in ("/mcp", "/authorize", "/token", "/"):
            for method in ("GET", "POST", "DELETE"):
                httpx.request(method, s.root + p, headers={"Authorization": "Bearer " + out["access_token"]}, timeout=10)
    assert w.jobs() == []
    pending = [c for c in w.confirmations() if c["state"] == "confirmed"]
    assert pending == [] and tokens_rows(w, "SELECT COUNT(*) FROM oauth_codes")[0][0] == codes_before
    assert w.sql("SELECT state FROM confirmations WHERE id = ?", (rid,))[0][0] == "pending"


# ---- not in this PR ------------------------------------------------------------------------------------------------------------

def test_tch01_no_tls_option_and_no_certificate_anywhere(w):
    # TC-H01
    from helpers import PLATFORM_DIR, run_cli
    for command in (["web", "--help"], ["mcp", "--help"]):
        help_text = run_cli(command).stdout
        assert not re.search(r"ssl|cert|tls|key-?file", help_text, re.I), command
    for name in ("oauth.py", "web.py", "http_auth.py", "mcp_server.py"):
        src = (PLATFORM_DIR / "abf_platform" / name).read_text(encoding="utf-8")
        assert not re.search(r"ssl_|certfile|keyfile|ssl\.", src), name


def test_tch02_one_scope_only(w, rig):
    # TC-H02
    meta = rig.c.get("/.well-known/oauth-authorization-server").json()
    assert len(meta.get("scopes_supported") or []) <= 1
    for scope in ("admin", "launch", "read write", "mcp admin"):
        assert rig.register(scope=scope).status_code == 400, scope
    cid = rig.new_client()
    from oauth_harness import pkce
    for scope in ("admin", "launch", "read write"):
        r = rig.authorize(cid, pkce()[1], scope=scope)
        assert "code=" not in r.headers.get("location", "") and (r.status_code == 400 or "error=invalid_scope" in r.headers["location"])


def test_tch04_h05_no_other_identity_provider_and_no_password_reset():
    # TC-H04, TC-H05
    from helpers import PLATFORM_DIR
    for name in ("oauth.py", "web.py", "http_auth.py", "mcp_server.py"):
        src = (PLATFORM_DIR / "abf_platform" / name).read_text(encoding="utf-8").lower()
        for word in ("google", "github", "openid", "oidc", "saml", "idp", "forgot", "reset_password", "resetpassword"):
            assert not re.search(r"%s" % word if word in ("idp", "forgot") else word, src), (name, word)


def test_tch05_the_web_and_the_tools_have_no_reset_or_change_password_door(w, rig):
    # TC-H05
    names = sorted(r.path for r in rig.app.routes)
    assert not [n for n in names if re.search(r"reset|forgot|passwd|password", n)], names
    for path in ("/reset", "/forgot", "/password", "/passwd", "/user/passwd", "/account"):
        assert rig.c.get(path).status_code == 404 and rig.c.post(path, data={"a": "b"}).status_code in (404, 405)


def test_tch06_consent_is_asked_every_time(w, rig):
    # TC-H06
    w.user("ann")
    f = rig.flow("ann")
    assert rig.token(f.token_form()).status_code == 200
    from oauth_harness import pkce
    path, verifier, cid = rig.start(client_id=f.client_id)
    page = rig.c.get(path)
    assert page.status_code == 200 and ">允許<" in page.text and not re.search(r"remember|記住", page.text, re.I)
    assert tokens_rows(w, "SELECT COUNT(*) FROM oauth_codes")[0][0] == 1                  # no second code until the person presses it
    assert rig.c.get(path, headers={"X-Remember": "1"}).status_code == 200 and tokens_rows(w, "SELECT COUNT(*) FROM oauth_codes")[0][0] == 1


def test_tch07_no_new_channel(w, rig):
    # TC-H07
    from helpers import PLATFORM_DIR
    w.user("ann")
    rig.tokens_for("ann")
    assert not w.sql("SELECT 1 FROM confirmations")
    for p in list((PLATFORM_DIR / "abf_platform" / "actions").glob("*.py")) + [PLATFORM_DIR / "abf_platform" / n for n in ("confirm.py", "jobs.py")]:
        assert "OAUTH" not in p.read_text(encoding="utf-8").upper(), p
    from abf_platform import actions
    assert {actions.TERMINAL.name, actions.ELICITED.name, actions.PAGE.name} == {"TERMINAL", "ELICITED", "PAGE"}
    assert not [n for n in dir(actions) if n.isupper() and "OAUTH" in n]


# ---- constitution and safety net -----------------------------------------------------------------------------------------------

def test_tci03_i04_no_secret_of_the_flow_is_kept_or_said(w, rig, capsys, caplog):
    # TC-I03, TC-I04
    import logging
    caplog.set_level(logging.DEBUG)
    w.user("ann")
    pages = []
    cid = rig.new_client(client_name="Claude")
    path, verifier, cid = rig.start(client_id=cid)
    pages.append(rig.c.get(path).text)
    rig.log_in("ann")
    page = rig.c.get(path)
    pages.append(page.text)
    cookie = rig.c.cookies.get("abf_web")
    f = rig.flow("ann", client_id=cid)
    bodies = []
    r = rig.token(f.token_form())
    bodies.append(r.text)
    out = r.json()
    r2 = rig.refresh(out["refresh_token"], cid)
    bodies.append(r2.text)
    new = r2.json()
    bodies.append(rig.token(f.token_form()).text)
    bodies.append(rig.c.post("/revoke", data={"token": new["access_token"], "client_id": cid, "client_secret": ""}).text)
    rc, said = w.ip.run("oauth", "revoke", "ann")
    secrets_ = [f.code, out["access_token"], out["refresh_token"], new["access_token"], new["refresh_token"], PASSWORD, cookie]
    seen = capsys.readouterr()
    haystack = "\n".join(pages + [said, seen.out, seen.err, caplog.text])
    for secret in secrets_:
        assert secret and secret not in haystack
    # The replayed-code and revoke answers must not echo any secret (the first two bodies carry tokens by design).
    for body in bodies[2:]:
        for secret in secrets_:
            assert secret not in body
    for secret in (f.code, out["access_token"], out["refresh_token"], new["access_token"], new["refresh_token"]):
        for p in w.ip.data.rglob("*"):
            if p.is_file():
                assert secret.encode() not in p.read_bytes(), p.name
    for row in tokens_rows(w, "SELECT token_hash FROM tokens WHERE kind LIKE 'oauth_%'") + tokens_rows(w, "SELECT code_hash FROM oauth_codes"):
        assert re.fullmatch(r"[0-9a-f]{64}", row[0])
    assert not [t for t in tokens_rows(w, "SELECT * FROM oauth_requests") if f.code in str(tuple(t))]


# ---- the public host behind a tunnel (incident 2026-10-23: 421 Invalid Host header after a good OAuth) -------------------------

def test_mcphost01_a_public_url_host_is_let_through_the_dns_rebinding_check(w):
    # TC-HOST01
    w.user("ann")
    pat = pat_of(w, "ann")
    with Served(w, public_url="https://example.ts.net") as s:
        assert s.post(pat, headers={"Host": "example.ts.net"}).status_code != 421
        assert s.post(pat, headers={"Host": "example.ts.net", "Origin": "https://example.ts.net"}).status_code != 421


def test_mcphost02_another_host_is_still_refused_with_a_public_url(w):
    # TC-HOST02
    w.user("ann")
    pat = pat_of(w, "ann")
    with Served(w, public_url="https://example.ts.net") as s:
        assert s.post(pat, headers={"Host": "evil.com"}).status_code == 421
        assert s.post(pat, headers={"Host": "example.ts.net", "Origin": "https://evil.com"}).status_code == 403


def test_mcphost03_without_a_public_url_the_public_host_is_refused_as_before(w):
    # TC-HOST03
    w.user("ann")
    pat = pat_of(w, "ann")
    with Served(w) as s:
        assert s.post(pat, headers={"Host": "example.ts.net"}).status_code == 421
        assert s.post(pat).status_code != 421
