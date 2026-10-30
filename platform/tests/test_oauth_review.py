# Nothing existing: tests of the ruling after the #126 code review (plan.md, items 1 to 3): the form channel only for vetted OAuth clients, a truthful consent page, the registration and authorize caps.
"""Spec 009i, ruling after the #126 review. Test cases are named in the comments (R1 form channel, R2 consent text, R3 caps)."""
import json

import pytest

from helpers import tool_json
from human_harness import World, form_answer
from oauth_harness import Rig, Served, http_calls, pat_of, pkce, tokens_rows, tokens_sql

CLAUDE_AI = "https://claude.ai/api/mcp/auth_callback"
EVIL = "https://evil.example/cb"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def rig(w):
    return Rig(w)


def launch_with_form(w, token, caller, run="run-two"):
    seen = []
    with Served(w) as s:
        _, (out,) = http_calls(s.url, token, [("launch", w.in_area(caller, w.choices(run=run)))], answer=form_answer(seen=seen))
    return tool_json(out), seen


# ---- R1: the form channel --------------------------------------------------------------------------------------------

def test_r1_a_client_with_its_own_redirect_cannot_auto_answer_the_form(w, rig):
    # R1-attacker: the redirect is the attacker's host, the session declares elicitation and auto-accepts: pending, a URL, zero jobs
    ann = w.user("ann")
    out = rig.tokens_for("ann", redirect=EVIL)
    j, seen = launch_with_form(w, out["access_token"], ann)
    assert j["sent"] is False and j["state"] == "pending" and "/c/" in j["confirmation_url"]
    assert seen == [] and w.jobs() == []
    assert [c["state"] for c in w.confirmations()] == ["pending"] and not w.sql("SELECT 1 FROM confirmations WHERE channel IS NOT NULL")


@pytest.mark.parametrize("redirects", [
    [CLAUDE_AI, EVIL],                                  # one bad redirect among good ones is enough
    ["https://claude.ai.evil.example/cb"],              # the host must be exactly claude.ai
    ["https://evilclaude.ai/cb"],
    ["https://www.claude.ai/cb"],
    ["https://claude.example/cb"],
])
def test_r1_every_redirect_must_be_allow_listed(w, rig, redirects):
    ann = w.user("ann")
    cid = rig.new_client(redirects)
    out = rig.tokens_for("ann", redirect=redirects[0], client_id=cid)
    j, seen = launch_with_form(w, out["access_token"], ann)
    assert j["state"] == "pending" and seen == [] and w.jobs() == []


@pytest.mark.parametrize("redirect", [CLAUDE_AI, "http://127.0.0.1:33418/cb", "http://localhost:3000/cb", "http://[::1]:5000/cb"])
def test_r1_claude_ai_and_loopback_clients_get_the_form(w, rig, redirect):
    ann = w.user("ann")
    out = rig.tokens_for("ann", redirect=redirect)
    j, seen = launch_with_form(w, out["access_token"], ann)
    assert j["sent"] is True and len(seen) == 1
    assert len(w.jobs("launch_nextflow")) == 1
    assert [c["channel"] for c in w.confirmations() if c["state"] == "confirmed"] == ["ELICITED"]


def test_r1_a_pat_still_gets_the_form(w, rig):
    ann = w.user("ann")
    j, seen = launch_with_form(w, pat_of(w, "ann"), ann)
    assert j["sent"] is True and len(seen) == 1


def test_r1_a_client_that_is_gone_is_not_vetted(w, rig):
    ann = w.user("ann")
    out = rig.tokens_for("ann", redirect=CLAUDE_AI)
    tokens_sql(w, "DELETE FROM oauth_clients")
    j, seen = launch_with_form(w, out["access_token"], ann)
    assert j["state"] == "pending" and seen == [] and w.jobs() == []


def test_r1_the_allow_list_is_a_named_constant():
    from abf_platform import oauth
    assert set(oauth.FORM_REDIRECT_HOSTS) == {"claude.ai", "127.0.0.1", "::1", "localhost"}


# ---- R2: the consent text --------------------------------------------------------------------------------------------

def consent_text(w, rig, redirect):
    path, verifier, cid = rig.start(redirect=redirect)
    rig.log_in("ann")
    return rig.c.get(path).text


def test_r2_the_consent_text_tells_the_truth_for_each_kind_of_client(w, rig):
    w.user("ann")
    listed = consent_text(w, rig, CLAUDE_AI)
    other = consent_text(w, rig, EVIL)
    assert "表單" in listed and "不能代您送出" not in listed
    assert "表單" not in other and "網站" in other and "確認" in other and "不能代您送出" in other


# ---- R3: caps ----------------------------------------------------------------------------------------------------------

def test_r3_the_register_body_is_capped_at_16_kib(w, rig):
    big = {"redirect_uris": [CLAUDE_AI], "client_name": "x", "padding": "p" * 17000}
    before = tokens_rows(w, "SELECT COUNT(*) FROM oauth_clients")[0][0]
    r = rig.c.post("/register", content=json.dumps(big), headers={"content-type": "application/json"})
    assert r.status_code == 413
    ok = rig.c.post("/register", content=json.dumps({"redirect_uris": [CLAUDE_AI], "client_name": "x", "padding": "p" * 8000}),
                    headers={"content-type": "application/json"})
    assert ok.status_code == 201
    assert tokens_rows(w, "SELECT COUNT(*) FROM oauth_clients")[0][0] == before + 1


def test_r3_metadata_fields_are_capped_and_links_are_dropped(w, rig):
    assert rig.register(client_name="n" * 101).status_code == 400
    assert rig.register(client_name="n" * 100).status_code == 201
    assert rig.register([CLAUDE_AI + "/%d" % i for i in range(6)]).status_code == 400
    assert rig.register([CLAUDE_AI + "/%d" % i for i in range(5)]).status_code == 201
    assert rig.register(["https://claude.ai/" + "a" * 500]).status_code == 400
    r = rig.register(logo_uri="https://evil.example/l.png", client_uri="https://evil.example/", tos_uri="https://evil.example/t",
                     policy_uri="https://evil.example/p")
    assert r.status_code == 201
    stored = json.loads(tokens_rows(w, "SELECT info_json FROM oauth_clients WHERE client_id = ?", (r.json()["client_id"],))[0][0])
    for k in ("logo_uri", "client_uri", "tos_uri", "policy_uri"):
        assert not stored.get(k) and not r.json().get(k)


def fill_clients(w, n, exchanged):
    from abf_platform import store
    uid = store.user_id_of(w.ip.tokens, "ann")
    now = w.clock()
    for i in range(n):
        cid = "filler-%d" % i
        tokens_sql(w, "INSERT INTO oauth_clients (client_id, info_json, created_at, last_used_at) VALUES (?, ?, ?, ?)",
                   (cid, json.dumps({"client_id": cid, "redirect_uris": [CLAUDE_AI]}), now, now))
        if exchanged:
            tokens_sql(w, "INSERT INTO tokens (token_hash, created_at, kind, expires_at, user_id, label, grant_id) VALUES (?, ?, 'oauth_access', ?, ?, ?, ?)",
                       ("h-%d" % i, now, now + 3600, uid, cid, "g-%d" % i))


def test_r3_only_clients_that_exchanged_a_code_count_toward_the_cap(w, rig):
    from abf_platform import oauth
    w.user("ann")
    fill_clients(w, oauth.MAX_CLIENTS, exchanged=False)
    assert rig.register().status_code == 201                       # 200 registrations nobody used do not lock the door
    tokens_sql(w, "DELETE FROM oauth_clients")
    fill_clients(w, oauth.MAX_CLIENTS, exchanged=True)
    assert rig.register().status_code == 400                        # 200 in use do


def test_r3_a_client_that_never_exchanged_is_purged_after_a_day(w, rig):
    w.user("ann")
    out = rig.tokens_for("ann", redirect=CLAUDE_AI)
    idle = rig.new_client()
    w.clock.t += 86400 + 1
    verifier, challenge = pkce()
    assert rig.authorize(out["flow"].client_id, challenge, redirect=CLAUDE_AI).status_code == 302
    assert not tokens_rows(w, "SELECT 1 FROM oauth_clients WHERE client_id = ?", (idle,))
    assert tokens_rows(w, "SELECT 1 FROM oauth_clients WHERE client_id = ?", (out["flow"].client_id,))


def pending(w):
    return tokens_rows(w, "SELECT COUNT(*) FROM oauth_requests WHERE decision IS NULL")[0][0]


def test_r3_twenty_pending_requests_per_client(w, rig):
    cid = rig.new_client()
    other = rig.new_client()
    verifier, challenge = pkce()
    for _ in range(20):
        assert rig.authorize(cid, challenge).status_code == 302
    r = rig.authorize(cid, challenge)
    assert r.status_code == 302 and "error=" in r.headers["location"] and "/consent/" not in r.headers["location"]
    assert tokens_rows(w, "SELECT COUNT(*) FROM oauth_requests WHERE client_id = ?", (cid,))[0][0] == 20
    assert "/consent/" in rig.authorize(other, challenge).headers["location"]          # another client is not affected


def test_r3_two_hundred_pending_requests_in_total_and_expired_ones_are_purged(w, rig):
    cid = rig.new_client()
    now = w.clock()
    for i in range(200):
        tokens_sql(w, "INSERT INTO oauth_requests (id, client_id, redirect_uri, redirect_explicit, code_challenge, state, resource, created_at, expires_at) "
                      "VALUES (?, ?, ?, 1, 'c', NULL, NULL, ?, ?)", ("%032x" % i, "other-%d" % (i % 20), CLAUDE_AI, now, now + 600))
    verifier, challenge = pkce()
    r = rig.authorize(cid, challenge)
    assert r.status_code == 302 and "error=" in r.headers["location"] and "/consent/" not in r.headers["location"]
    assert pending(w) == 200
    w.clock.t += 601                                               # all expired: the next /authorize clears them and is served
    assert "/consent/" in rig.authorize(cid, challenge).headers["location"]
    assert tokens_rows(w, "SELECT COUNT(*) FROM oauth_requests")[0][0] == 1


# ---- CI: the errors the provider raises are plain exceptions (the SDK's are frozen dataclasses, and a newer Python sets __traceback__ on raise) ----

def test_r3_the_raised_errors_are_not_frozen():
    from abf_platform import oauth
    for err in (oauth.RegistrationError("invalid_client_metadata", "x"), oauth.AuthorizeError("temporarily_unavailable", "x"),
                oauth.TokenError("invalid_grant", "x")):
        err.__traceback__ = None
        err.note = 1                                   # a frozen dataclass refuses both
        assert isinstance(err, Exception)
