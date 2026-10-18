# Nothing existing: regression tests for specs/web-chrome-origin (Chrome sends `Origin: null` under Referrer-Policy: no-referrer); the page and its rules are ours.
"""Bug web-chrome-origin: every response says Referrer-Policy: same-origin, so a browser sends a real Origin on a same-origin POST;
"null" and foreign origins stay refused. Test cases are named in the comments (WCO-1, WCO-2). WCO-3 (real Chrome) is the manual script scripts/dev/check_chrome_login.py: CI has no Chrome and may skip nothing."""
import pytest

from human_harness import PASSWORD, World
from test_confirm_page import logged_in, pending


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def test_wco1_every_response_carries_referrer_policy_same_origin(w):
    # WCO-1: the page, the login form, a refusal and a 404 all carry the header
    ann = w.user("ann")
    rid = pending(w, ann)
    anon = w.web()
    c = logged_in(w, "ann")
    answers = [anon.get("/login"), anon.get("/nowhere"), anon.post("/login", data={"name": "ann", "password": "wrong password"}),
               anon.post("/login", data={"name": "ann", "password": PASSWORD}, headers={"Origin": "null"}),
               c.get("/c/" + rid), c.get("/c/" + "0" * 32)]
    assert len(answers) == 6
    for r in answers:
        assert r.headers.get("referrer-policy") == "same-origin", (r.url, r.status_code)


def test_wco2_origin_null_and_foreign_are_refused_the_own_origin_is_accepted(w):
    # WCO-2: the rule in same_origin() is unchanged
    w.user("ann")
    c = w.web()
    data = {"name": "ann", "password": PASSWORD}
    assert c.post("/login", data=data, headers={"Origin": "null"}).status_code == 403
    assert c.post("/login", data=data, headers={"Origin": "http://evil.example"}).status_code == 403
    assert c.post("/login", data=data, headers={"Referer": "http://evil.example/x"}).status_code == 403
    host = "127.0.0.1:8788"
    nxt = {"name": "ann", "password": PASSWORD, "next": "/c/" + "a" * 32}
    r = c.post("/login", data=nxt, headers={"Host": host, "Origin": "http://" + host})
    assert r.status_code == 303 and r.headers["location"] == nxt["next"]



def test_wco1_the_oauth_routes_and_the_register_cap_carry_the_header_too(w):
    # WCO-1 (after merging 009i): consent page (logged in and not), /register (ok, over the 16 KiB cap, bad body), /authorize, /token, a refusal at the consent POST
    import json
    from oauth_harness import Rig
    w.user("ann")
    rig = Rig(w)
    path, verifier, cid = rig.start()
    anon = rig.another()
    answers = [anon.get(path)]                                           # consent page, not logged in: the login form
    rig.log_in("ann")
    page = rig.c.get(path)
    assert page.status_code == 200 and "允許" in page.text
    answers += [page,                                                    # consent page, logged in
                rig.register(),                                          # 201
                rig.c.post("/register", content=json.dumps({"redirect_uris": ["x"], "padding": "p" * 17000}),
                           headers={"content-type": "application/json"}),    # 413 from RegisterBodyCap, which answers before the routes
                rig.c.post("/register", content="not json", headers={"content-type": "application/json"}),
                rig.authorize("no-such-client", "c" * 43),               # 400
                rig.token({"grant_type": "authorization_code", "code": "nope"}),
                rig.c.post(path, data={"csrf": "wrong", "decision": "allow"}),       # 403
                rig.c.get("/consent/" + "0" * 32)]                       # 404
    assert answers[3].status_code == 413 and answers[2].status_code == 201
    for r in answers:
        assert r.headers.get("referrer-policy") == "same-origin", (r.url, r.status_code)
        assert r.headers.get("x-frame-options") == "DENY", (r.url, r.status_code)
