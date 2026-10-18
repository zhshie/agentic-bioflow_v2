# Nothing existing: tests of the token endpoint of spec 009i (code to tokens, refresh and rotation, revoking); the one-use and who-for rules are ours.
"""Spec 009i, user story 4: a code and a refresh token are each good once and only for the right client. Test cases are named in the comments (TC-D01 ...)."""
import time

import pytest

from human_harness import PASSWORD, World
from oauth_harness import REDIRECT, Rig, Served, pat_of, pkce, tokens_rows, tokens_sql


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def rig(w):
    return Rig(w)


def oauth_rows(w):
    return tokens_rows(w, "SELECT * FROM tokens WHERE kind LIKE 'oauth_%' ORDER BY id")


def test_tcd01_the_code_becomes_an_access_and_a_refresh_token_for_that_person(w, rig):
    # TC-D01
    ann = w.user("ann")
    f = rig.flow("ann")
    r = rig.token(f.token_form())
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["token_type"].lower() == "bearer" and body["expires_in"] == 3600 and body["access_token"] and body["refresh_token"]
    rows = oauth_rows(w)
    assert [x["kind"] for x in rows] == ["oauth_access", "oauth_refresh"]
    assert all(x["user_id"] == ann.user_id and x["label"] == f.client_id for x in rows)
    assert [round(x["expires_at"] - x["created_at"]) for x in rows] == [3600, 30 * 86400]
    import hashlib
    assert [x["token_hash"] for x in rows] == [hashlib.sha256(body[k].encode()).hexdigest() for k in ("access_token", "refresh_token")]
    for p in w.ip.data.rglob("*"):
        if p.is_file():
            blob = p.read_bytes()
            assert body["access_token"].encode() not in blob and body["refresh_token"].encode() not in blob and f.code.encode() not in blob


def test_tcd02_a_wrong_or_missing_verifier_gets_nothing(w, rig):
    # TC-D02
    w.user("ann")
    f = rig.flow("ann")
    for over in ({"code_verifier": "x" * 60}, {"code_verifier": None}):
        r = rig.token(f.token_form(**over))
        assert r.status_code == 400 and "access_token" not in r.text
    assert oauth_rows(w) == []
    assert rig.token(f.token_form()).status_code == 200            # the right verifier still works: a wrong try spent nothing


def test_tcd03_a_used_code_is_dead_and_ends_what_its_first_use_made(w, rig):
    # TC-D03
    w.user("ann")
    f = rig.flow("ann")
    first = rig.token(f.token_form()).json()
    before = len(oauth_rows(w))
    r = rig.token(f.token_form())
    assert r.status_code == 400 and "access_token" not in r.text and len(oauth_rows(w)) == before
    assert all(x["revoked_at"] is not None for x in oauth_rows(w))                      # ruling 2: RFC 6749 4.1.2
    assert rig.refresh(first["refresh_token"], f.client_id).status_code == 400
    with Served(w) as s:
        assert s.post(first["access_token"]).status_code == 401


def test_tcd04_another_clients_code_is_refused_and_leaves_the_owner_alone(w, rig):
    # TC-D04
    w.user("ann")
    f = rig.flow("ann")
    y = rig.new_client()
    r = rig.token(f.token_form(client_id=y))
    assert r.status_code == 400 and oauth_rows(w) == []
    assert rig.token(f.token_form()).status_code == 200


def test_tcd05_a_different_redirect_at_the_token_step_is_refused(w, rig):
    # TC-D05
    w.user("ann")
    other = "https://claude.example/other"
    cid = rig.new_client([REDIRECT, other])
    f = rig.flow("ann", client_id=cid)
    r = rig.token(f.token_form(redirect_uri=other))
    assert r.status_code == 400 and oauth_rows(w) == []
    assert rig.token(f.token_form(redirect_uri=None)).status_code == 400            # it was given explicitly at /authorize, so it must be given again
    assert rig.token(f.token_form()).status_code == 200


def test_tcd06_a_code_dies_after_five_minutes(w, rig):
    # TC-D06
    w.user("ann")
    f = rig.flow("ann")
    w.clock.t += 301
    r = rig.token(f.token_form())
    assert r.status_code == 400 and oauth_rows(w) == []


def test_tcd07_a_refresh_token_is_swapped_for_a_new_pair_and_the_old_one_stops(w, rig):
    # TC-D07
    w.user("ann")
    out = rig.tokens_for("ann")
    cid = out["flow"].client_id
    w.clock.t += 1000
    r = rig.refresh(out["refresh_token"], cid)
    assert r.status_code == 200
    new = r.json()
    assert new["access_token"] != out["access_token"] and new["refresh_token"] != out["refresh_token"] and new["expires_in"] == 3600
    rows = oauth_rows(w)
    assert len(rows) == 4
    newest = rows[-1]
    assert newest["kind"] == "oauth_refresh" and round(newest["expires_at"] - w.clock()) == 30 * 86400
    assert rig.refresh(out["refresh_token"], cid).status_code == 400


def test_tcd08_a_rotated_refresh_token_used_again_is_refused_and_ends_the_family(w, rig):
    # TC-D08
    w.user("ann")
    out = rig.tokens_for("ann")
    cid = out["flow"].client_id
    new = rig.refresh(out["refresh_token"], cid).json()
    before = len(oauth_rows(w))
    r = rig.refresh(out["refresh_token"], cid)
    assert r.status_code == 400 and "access_token" not in r.text and len(oauth_rows(w)) == before
    assert rig.refresh(new["refresh_token"], cid).status_code == 400                    # the stolen-token rule: the whole family is over
    with Served(w) as s:
        assert s.post(new["access_token"]).status_code == 401


def test_tcd09_other_client_expired_and_revoked_refresh_tokens_are_refused(w, rig):
    # TC-D09
    w.user("ann")
    out = rig.tokens_for("ann")
    cid = out["flow"].client_id
    y = rig.new_client()
    assert rig.refresh(out["refresh_token"], y).status_code == 400
    out2 = rig.tokens_for("ann")
    cid2 = out2["flow"].client_id
    rev = rig.tokens_for("ann")
    tokens_sql(w, "UPDATE tokens SET revoked_at = ? WHERE token_hash = ?",
               (w.clock(), __import__("hashlib").sha256(rev["refresh_token"].encode()).hexdigest()))
    assert rig.refresh(rev["refresh_token"], rev["flow"].client_id).status_code == 400
    w.clock.t += 20 * 86400
    assert rig.authorize(cid2, pkce()[1]).status_code == 302 and rig.authorize(cid, pkce()[1]).status_code == 302      # both clients stay in use
    w.clock.t += 10 * 86400 + 1
    assert rig.refresh(out2["refresh_token"], cid2).status_code == 400
    assert rig.refresh(out["refresh_token"], cid).status_code == 400


def test_tcd10_a_disabled_person_cannot_refresh(w, rig):
    # TC-D10
    w.user("ann")
    out = rig.tokens_for("ann")
    tokens_sql(w, "UPDATE users SET disabled_at = ? WHERE name = 'ann'", (time.time(),))
    n = len(oauth_rows(w))
    r = rig.refresh(out["refresh_token"], out["flow"].client_id)
    assert r.status_code == 400 and len(oauth_rows(w)) == n


def test_tcd11_a_web_password_or_a_pat_is_no_grant(w, rig):
    # TC-D11
    w.user("ann")
    pat = pat_of(w, "ann")
    cid = rig.new_client()
    cases = [{"grant_type": "password", "username": "ann", "password": PASSWORD},
             {"grant_type": "authorization_code", "code": PASSWORD, "code_verifier": "v" * 50, "client_id": cid, "redirect_uri": REDIRECT},
             {"grant_type": "authorization_code", "code": "x", "code_verifier": "v" * 50, "client_id": cid, "client_secret": PASSWORD,
              "redirect_uri": REDIRECT},
             {"grant_type": "authorization_code", "code": pat, "code_verifier": "v" * 50, "client_id": cid, "redirect_uri": REDIRECT},
             {"grant_type": "refresh_token", "refresh_token": pat, "client_id": cid},
             {"grant_type": "client_credentials", "client_secret": PASSWORD}]
    for form in cases:
        form.setdefault("client_id", cid)
        r = rig.token(form)
        assert r.status_code in (400, 401) and "access_token" not in r.text, form
    assert oauth_rows(w) == []


def test_tcd12_revoking_a_token_ends_it_at_once(w, rig):
    # TC-D12
    w.user("ann")
    a = rig.tokens_for("ann")
    b = rig.tokens_for("ann")
    with Served(w) as s:
        assert s.post(a["access_token"]).status_code == 200
        r = rig.c.post("/revoke", data={"token": a["access_token"], "client_id": a["flow"].client_id, "client_secret": ""})
        assert r.status_code == 200
        assert s.post(a["access_token"]).status_code == 401
        r = rig.c.post("/revoke", data={"token": b["refresh_token"], "client_id": b["flow"].client_id, "client_secret": ""})
        assert r.status_code == 200
        assert rig.refresh(b["refresh_token"], b["flow"].client_id).status_code == 400
        before = tokens_rows(w, "SELECT COUNT(*), SUM(revoked_at IS NULL) FROM tokens")[0]
        unknown = rig.c.post("/revoke", data={"token": "no-such-token", "client_id": a["flow"].client_id, "client_secret": ""})
        assert unknown.status_code == r.status_code and unknown.text == r.text
        assert tokens_rows(w, "SELECT COUNT(*), SUM(revoked_at IS NULL) FROM tokens")[0] == before


def test_tcd13_one_client_cannot_revoke_anothers_tokens(w, rig):
    # TC-D13
    w.user("ann")
    x = rig.tokens_for("ann")
    y = rig.new_client()
    for token in (x["access_token"], x["refresh_token"]):
        assert rig.c.post("/revoke", data={"token": token, "client_id": y, "client_secret": ""}).status_code == 200
    with Served(w) as s:
        assert s.post(x["access_token"]).status_code == 200
    assert rig.refresh(x["refresh_token"], x["flow"].client_id).status_code == 200


def test_tcd14_pat_commands_do_not_see_oauth_tokens(w, rig):
    # TC-D14
    w.user("ann")
    pat = pat_of(w, "ann")
    out = rig.tokens_for("ann")
    rc, listing = w.ip.run("pat", "list")
    assert rc == 0 and listing.count("ann") == 1                                      # the PAT only
    ids = [x["id"] for x in oauth_rows(w)]
    for token_id in ids:
        rc, said = w.ip.run("pat", "revoke", token_id)
        assert rc == 1 and "no live personal access token" in said
    assert all(x["revoked_at"] is None for x in oauth_rows(w))
    with Served(w) as s:
        assert s.post(out["access_token"]).status_code == 200
