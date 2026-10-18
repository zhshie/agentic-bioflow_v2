# Nothing existing: tests of the consent step of spec 009i (/authorize, the consent page, Allow and Deny); the rules about who may press and what the press makes are ours.
"""Spec 009i, user story 3: only the person who logs in with the web password and presses Allow gets a code. Test cases are named in the comments (TC-C01 ...)."""
import hashlib
import re
import threading
import time
from urllib.parse import urlparse

import pytest

from human_harness import PASSWORD, World
from oauth_harness import BASE, REDIRECT, Rig, Served, dump, pat_of, pkce, table_counts, tokens_rows, tokens_sql


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def rig(w):
    return Rig(w)


def test_tcc01_authorize_stores_a_request_and_sends_the_browser_to_the_consent_page(w, rig):
    # TC-C01
    before = table_counts(w)
    path, verifier, cid = rig.start()
    assert re.fullmatch(r"/consent/[0-9a-f]{32}", path)
    after = table_counts(w)
    assert after["oauth_requests"] == before["oauth_requests"] + 1
    assert (after["oauth_codes"], after["tokens"]) == (before["oauth_codes"], before["tokens"])
    row = tokens_rows(w, "SELECT * FROM oauth_requests")[0]
    assert row["expires_at"] - row["created_at"] == 600 and row["client_id"] == cid and row["decision"] is None


def test_tcc02_a_bad_authorize_is_refused_and_never_redirects_to_an_unchecked_address(w, rig):
    # TC-C02
    cid = rig.new_client()
    verifier, challenge = pkce()
    before = table_counts(w)
    r = rig.authorize("no-such-client", challenge)
    assert r.status_code == 400 and "location" not in r.headers
    for redirect in (REDIRECT + "x", REDIRECT + "/more", "https://other.example/cb", "http://claude.example/cb", "https://claude.example/cb?x=1"):
        r = rig.authorize(cid, challenge, redirect=redirect)
        assert r.status_code == 400 and "location" not in r.headers, redirect
    for extra in ({"code_challenge": None}, {"code_challenge_method": "plain"}, {"response_type": "token"}, {"scope": "admin"}):
        r = rig.authorize(cid, challenge, **extra)
        if r.status_code == 302:           # an error for a checked client and redirect goes back to that redirect, as an error
            assert r.headers["location"].startswith(REDIRECT + "?") and "error=" in r.headers["location"] and "code=" not in r.headers["location"], extra
        else:
            assert r.status_code == 400, (extra, r.status_code)
    assert table_counts(w) == before


def test_tcc03_nobody_logged_in_sees_a_login_form_and_no_allow_button(w, rig):
    # TC-C03
    w.user("ann")
    path, verifier, cid = rig.start()
    before = table_counts(w)
    page = rig.c.get(path)
    assert page.status_code == 200 and 'name="password"' in page.text and "允許" not in page.text and 'name="csrf"' not in page.text
    assert table_counts(w) == before
    assert 'value="%s"' % path in page.text            # the login form carries the way back
    r = rig.c.post("/login", data={"name": "ann", "password": PASSWORD, "next": path})
    assert r.status_code == 303 and r.headers["location"] == path
    assert "允許" in rig.c.get(path).text


def test_tcc04_a_token_never_logs_in_at_the_consent_page(w, rig):
    # TC-C04
    w.user("ann")
    pat = pat_of(w, "ann")
    minted = Rig(w)
    out = minted.tokens_for("ann")
    path, verifier, cid = rig.start()
    before = table_counts(w)
    codes = tokens_rows(w, "SELECT COUNT(*) FROM oauth_codes")[0][0]
    for bearer in (pat, out["access_token"], out["refresh_token"]):
        h = {"Authorization": "Bearer " + bearer}
        page = rig.c.get(path, headers=h)
        assert 'name="password"' in page.text and "允許" not in page.text
        r = rig.c.post(path, data={"csrf": "x", "decision": "allow"}, headers=h)
        assert r.status_code == 401
        r = rig.c.post("/login", data={"name": "ann", "password": bearer, "next": path}, headers=h)
        assert r.status_code == 401 and not r.cookies.get("abf_web")
    assert not rig.c.cookies.get("abf_web")
    assert tokens_rows(w, "SELECT COUNT(*) FROM oauth_codes")[0][0] == codes
    assert table_counts(w)["web_sessions"] == before["web_sessions"]


def test_tcc05_the_page_names_the_connector_the_redirect_host_and_the_limits(w, rig):
    # TC-C05
    w.user("ann")
    cid = rig.new_client(client_name="Claude <b>Desktop</b>&")
    path, verifier, cid = rig.start(client_id=cid)
    rig.log_in("ann")
    first = rig.c.get(path)
    page = first.text
    assert "Claude &lt;b&gt;Desktop&lt;/b&gt;&amp;" in page and "<b>Desktop</b>" not in page
    assert "claude.example" in page and "不能替你送出" in page and "送出" in page
    assert ">允許<" in page and ">拒絕<" in page
    inputs = re.findall(r"<input[^>]*>", page)
    assert [i for i in inputs if 'type="hidden"' not in i] == []                # nothing to type a token into
    assert "form-action 'self' https://claude.example" in first.headers["content-security-policy"]


def test_tcc06_allow_mints_one_code_bound_to_the_person_and_the_request(w, rig):
    # TC-C06
    ann = w.user("ann")
    f = rig.flow("ann", state="state-xyz")
    assert f.location.startswith(REDIRECT + "?") and f.code and f.state == "state-xyz"
    rows = tokens_rows(w, "SELECT * FROM oauth_codes")
    assert len(rows) == 1
    row = rows[0]
    assert row["code_hash"] == hashlib.sha256(f.code.encode()).hexdigest() and f.code not in str(tuple(row))
    assert row["client_id"] == f.client_id and row["redirect_uri"] == REDIRECT and row["user_id"] == ann.user_id
    assert row["code_challenge"] and row["expires_at"] - row["created_at"] == 300 and row["used_at"] is None


def test_tcc07_deny_goes_back_with_access_denied_and_no_code(w, rig):
    # TC-C07
    w.user("ann")
    f = rig.flow("ann", decision="deny", state="s9")
    assert f.error == "access_denied" and f.state == "s9" and f.code is None
    assert table_counts(w)["oauth_codes"] == 0 and tokens_rows(w, "SELECT COUNT(*) FROM tokens WHERE kind LIKE 'oauth_%'")[0][0] == 0
    again = rig.decide(f.path, "allow", csrf=f.csrf)
    assert again.status_code != 302 and table_counts(w)["oauth_codes"] == 0


def test_tcc08_an_allow_without_the_right_csrf_token_does_nothing(w, rig):
    # TC-C08
    w.user("ann")
    w.user("bob")
    path1, _, _ = rig.start()
    path2, _, _ = rig.start()
    rig.log_in("ann")
    other = rig.another()
    rig.log_in("bob", other)
    good2 = rig.csrf(path2)
    stolen = rig.csrf(path2, other)                                     # a token of someone else's login
    for form in ({"decision": "allow"}, {"decision": "allow", "csrf": "wrong"}, {"decision": "allow", "csrf": good2},
                 {"decision": "allow", "csrf": stolen}):
        r = rig.c.post(path1, data=form)
        assert r.status_code == 403, form
    assert table_counts(w)["oauth_codes"] == 0
    assert rig.decide(path1, "allow").status_code == 302 and table_counts(w)["oauth_codes"] == 1      # the person can still press it


def test_tcc09_looking_at_pages_with_allow_in_the_query_changes_nothing(w, rig):
    # TC-C09
    w.user("ann")
    path, verifier, cid = rig.start()
    rig.log_in("ann")
    before = dump(w, "oauth_codes", "tokens", "oauth_requests")
    tokens_before = dump(w, "tokens")
    for url in (path, path + "?allow=1", path + "?approve=true", path + "?code=abc&decision=allow",
                path + "?decision=allow&csrf=" + rig.csrf(path)):
        r = rig.c.get(url)
        assert r.status_code == 200
    assert dump(w, "oauth_codes", "tokens", "oauth_requests") == before
    verifier2, challenge = pkce()
    for _ in range(3):
        rig.authorize(cid, challenge, allow="1", approve="true")
    after = dump(w, "oauth_codes", "tokens")
    assert after["oauth_codes"] == [] and after["tokens"] == tokens_before["tokens"]


def test_tcc10_a_press_from_another_origin_is_refused(w, rig):
    # TC-C10
    w.user("ann")
    path, _, _ = rig.start()
    rig.log_in("ann")
    token = rig.csrf(path)
    r = rig.c.post(path, data={"csrf": token, "decision": "allow"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403 and table_counts(w)["oauth_codes"] == 0


def test_tcc11_a_request_is_decided_once(w, rig):
    # TC-C11
    w.user("ann")
    f = rig.flow("ann")
    assert rig.decide(f.path, "allow", csrf=f.csrf).status_code != 302
    assert table_counts(w)["oauth_codes"] == 1
    path, _, _ = rig.start()
    token = rig.csrf(path)
    assert rig.decide(path, "deny", csrf=token).status_code == 302
    assert rig.decide(path, "allow", csrf=token).status_code != 302 and table_counts(w)["oauth_codes"] == 1
    path, _, _ = rig.start()
    browsers = [rig.another(client=("127.0.0.1", 50100 + i)) for i in range(2)]
    tokens = []
    for b in browsers:
        rig.log_in("ann", b)
        tokens.append(rig.csrf(path, b))
    results = []

    def press(b, token):
        results.append(b.post(path, data={"csrf": token, "decision": "allow"}).status_code)

    threads = [threading.Thread(target=press, args=(b, t)) for b, t in zip(browsers, tokens)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results).count(302) == 1 and table_counts(w)["oauth_codes"] == 2


def test_tcc12_a_request_older_than_ten_minutes_is_dead(w, rig):
    # TC-C12
    w.user("ann")
    path, _, _ = rig.start()
    rig.log_in("ann")
    token = rig.csrf(path)
    w.clock.t += 601
    page = rig.c.get(path)
    assert page.status_code == 410 and "逾時" in page.text
    r = rig.c.post(path, data={"csrf": token, "decision": "allow"})
    assert r.status_code == 410 and table_counts(w)["oauth_codes"] == 0


def test_tcc13_a_disabled_person_cannot_log_in_or_press_allow(w, rig):
    # TC-C13
    w.user("ann")
    path, _, _ = rig.start()
    tokens_sql(w, "UPDATE users SET disabled_at = ? WHERE name = 'ann'", (time.time(),))
    assert w.login(rig.c, "ann").status_code == 401 and not rig.c.cookies.get("abf_web")
    tokens_sql(w, "UPDATE users SET disabled_at = NULL WHERE name = 'ann'")
    rig.log_in("ann")
    token = rig.csrf(path)
    tokens_sql(w, "UPDATE users SET disabled_at = ? WHERE name = 'ann'", (time.time(),))
    r = rig.c.post(path, data={"csrf": token, "decision": "allow"})
    assert r.status_code == 401 and table_counts(w)["oauth_codes"] == 0


def test_tcc14_the_code_belongs_to_whoever_logged_in(w, rig):
    # TC-C14
    ann = w.user("ann")
    bob = w.user("bob")
    f = rig.flow("bob")
    assert tokens_rows(w, "SELECT user_id FROM oauth_codes")[0][0] == bob.user_id != ann.user_id
    out = rig.token(f.token_form()).json()
    assert tokens_rows(w, "SELECT DISTINCT user_id FROM tokens WHERE kind LIKE 'oauth_%'")[0][0] == bob.user_id
    with Served(w) as s:
        assert s.post(out["access_token"]).status_code == 200


def test_tcc15_an_unknown_request_id_is_a_plain_404(w, rig):
    # TC-C15
    w.user("ann")
    fake = "/consent/" + "ab" * 16
    for logged in (False, True):
        if logged:
            rig.log_in("ann")
        assert rig.c.get(fake).status_code == 404
        assert rig.c.post(fake, data={"csrf": "x", "decision": "allow"}).status_code == 404
    assert rig.c.get("/consent/not-a-rid").status_code == 404


def test_tcc16_what_is_posted_with_allow_cannot_change_what_the_code_is_bound_to(w, rig):
    # TC-C16
    ann = w.user("ann")
    w.user("bob")
    other = rig.new_client(["https://other.example/cb"])
    path, verifier, cid = rig.start()
    rig.log_in("ann")
    r = rig.decide(path, "allow", client_id=other, redirect_uri="https://other.example/cb", user_id="999", code_challenge="evil", scope="admin",
                   state="forged")
    assert r.status_code == 302 and r.headers["location"].startswith(REDIRECT + "?") and "forged" not in r.headers["location"]
    row = tokens_rows(w, "SELECT * FROM oauth_codes")[0]
    assert (row["client_id"], row["redirect_uri"], row["user_id"]) == (cid, REDIRECT, ann.user_id) and row["code_challenge"] != "evil"


def test_tcc17_six_tries_in_a_minute_through_the_consent_login_are_locked(w, rig):
    # TC-C17
    w.user("ann")
    path, _, _ = rig.start()
    for _ in range(5):
        assert rig.c.post("/login", data={"name": "ann", "password": "wrong password", "next": path}).status_code == 401
    r = rig.c.post("/login", data={"name": "ann", "password": PASSWORD, "next": path})
    assert r.status_code == 429 and not rig.c.cookies.get("abf_web") and table_counts(w)["oauth_codes"] == 0
