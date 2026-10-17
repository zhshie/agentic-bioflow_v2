# Nothing existing: tests of the confirmation page of spec 009c (who may press the button, what the page shows, what it refuses); the routes and the rules are ours.
"""009c, user story 4: the page where a person logged in as the same user presses 送出. Test cases are named in the comments (TC-D01 ...)."""
import json
import re
import sqlite3
import subprocess
import sys

import pytest

from helpers import assert_loopback_only, free_port, run_cli, start_cli, stop_proc, wait_port
from human_harness import PASSWORD, World, csrf_of, form_answer, pending_id_of
from test_web_login import cookie_value, sessions


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def logged_in(w, name, client=None):
    client = client or w.web()
    assert w.login(client, name).status_code in (200, 303)
    return client


def pending(w, caller, **over):
    return w.launch(caller=caller, **over)["id"]


def snapshot(w):
    return (w.sql("SELECT * FROM confirmations"), w.sql("SELECT * FROM jobs WHERE kind <> 'preflight'"), w.sql("SELECT * FROM launches"),
            sessions(w))


def test_tcd01_d20_the_owner_presses_send_and_exactly_one_job_is_queued(w):
    # TC-D01, TC-D20
    ann = w.user("ann")
    rid = pending(w, ann)
    c = logged_in(w, "ann")
    page = c.get("/c/" + rid)
    assert page.status_code == 200 and "nf-core/ampliseq" in page.text and 'name="csrf"' in page.text
    r = c.post("/c/" + rid, data={"csrf": csrf_of(page.text)})
    assert r.status_code == 200 and "已送出" in r.text
    assert len(w.jobs("launch_nextflow")) == 1 and str(w.jobs()[0]["id"]) in r.text
    row = w.confirmations()[0]
    assert row["state"] == "confirmed" and row["channel"] == "PAGE" and row["confirmed_at"] and row["caller_user_id"] == ann.user_id


def test_tcd02_the_address_in_the_answer_follows_public_url(w):
    # TC-D02
    ann = w.user("ann")
    w.web(public_url="https://abf.example")
    out = w.launch(caller=ann)
    assert out["confirmation_url"].startswith("https://abf.example/c/") and "再呼叫" in out["message"]


def test_tcd03_looking_at_the_page_changes_nothing(w):
    # TC-D03
    ann = w.user("ann")
    rid = pending(w, ann)
    c = logged_in(w, "ann")
    before = snapshot(w)
    for _ in range(4):
        assert c.get("/c/" + rid).status_code == 200
        c.get("/login")
    assert snapshot(w) == before and w.jobs() == []


def test_tcd04_nobody_logged_in_sees_a_login_and_no_button(w):
    # TC-D04
    rid = pending(w, w.user("ann"))
    c = w.web()
    before = snapshot(w)
    page = c.get("/c/" + rid)
    assert "密碼" in page.text and 'name="csrf"' not in page.text and "nf-core/ampliseq" not in page.text
    assert snapshot(w) == before


def test_tcd05_d22_another_person_sees_nothing_and_cannot_press(w):
    # TC-D05, TC-D22
    ann, bob = w.user("ann"), w.user("bob")
    rid = pending(w, ann)
    own = pending(w, bob, revision="2.17.0")
    c = logged_in(w, "bob")
    page = c.get("/c/" + rid)
    assert "不是你的申請" in page.text and 'name="csrf"' not in page.text
    assert "nf-core/ampliseq" not in page.text and "run-one" not in page.text
    token_of_bob = csrf_of(c.get("/c/" + own).text)
    cookie = cookie_value(c.post("/login", data={"name": "bob", "password": PASSWORD}))
    forged = c.app.state.csrf_token(cookie, rid)
    for token in (token_of_bob, forged, "x"):
        r = c.post("/c/" + rid, data={"csrf": token})
        assert r.status_code == 403 and w.jobs() == []
    assert [x["state"] for x in w.confirmations() if x["id"] == rid] == ["pending"]


def test_tcd06_d07_a_missing_or_wrong_csrf_changes_nothing_and_the_owner_can_still_press(w):
    # TC-D06, TC-D07
    ann = w.user("ann")
    rid = pending(w, ann)
    c = logged_in(w, "ann")
    good = csrf_of(c.get("/c/" + rid).text)
    for data in ({}, {"csrf": ""}, {"csrf": "wrong"}, {"csrf": good + "0"}, {"CSRF": good}):
        assert c.post("/c/" + rid, data=data).status_code == 403
    assert w.jobs() == [] and w.confirmations()[0]["state"] == "pending"
    assert c.post("/c/" + rid, data={"csrf": good}).status_code == 200 and len(w.jobs()) == 1


def test_tcd08_a_token_is_for_one_request_and_one_login(w):
    # TC-D08
    ann, bob = w.user("ann"), w.user("bob")
    one = pending(w, ann)
    two = pending(w, ann, revision="2.17.0")
    a, b = logged_in(w, "ann"), logged_in(w, "bob")
    token_one = csrf_of(a.get("/c/" + one).text)
    token_two = csrf_of(a.get("/c/" + two).text)
    assert token_one != token_two
    assert a.post("/c/" + two, data={"csrf": token_one}).status_code == 403
    bob_own = pending(w, bob, revision="2.16.0")
    token_bob = csrf_of(b.get("/c/" + bob_own).text)
    assert a.post("/c/" + two, data={"csrf": token_bob}).status_code == 403
    assert w.jobs() == []


def test_tcd09_a_second_press_does_nothing_more(w):
    # TC-D09
    rid = pending(w, w.user("ann"))
    c = logged_in(w, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    first = c.post("/c/" + rid, data={"csrf": token})
    second = c.post("/c/" + rid, data={"csrf": token})
    assert "已送出" in first.text and "已送出" in second.text and len(w.jobs("launch_nextflow")) == 1
    assert c.get("/c/" + rid).text.count('name="csrf"') == 0


def test_tcd10_after_ten_minutes_the_page_says_so_and_refuses(w):
    # TC-D10
    rid = pending(w, w.user("ann"))
    c = logged_in(w, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    w.clock.t += 601
    page = c.get("/c/" + rid)
    assert "逾時" in page.text and 'name="csrf"' not in page.text
    r = c.post("/c/" + rid, data={"csrf": token})
    assert r.status_code >= 400 and w.jobs() == []


def test_tcd11_an_invented_address_is_a_404_that_says_nothing(w):
    # TC-D11
    rid = pending(w, w.user("ann"))
    c = logged_in(w, "ann")
    for fake in ("0" * 32, "f" * 32, "x", "1" * 31, "../etc/passwd"):
        assert c.get("/c/" + fake).status_code == 404
        assert c.post("/c/" + fake, data={"csrf": "x"}).status_code == 404
    anon = w.web()
    real, fake = anon.get("/c/" + rid), anon.get("/c/" + "0" * 32)
    assert real.status_code == fake.status_code and real.text.replace(rid, "") == fake.text.replace("0" * 32, "")


def test_tcd12_the_addresses_are_long_random_and_different(w):
    # TC-D12
    # 20 requests, from two people: one person may have at most 10 open requests (review finding 9)
    ann, bob = w.user("ann"), w.user("bob")
    from helpers import tool_json
    ids = []
    for who in (ann, bob):
        calls = [("launch", w.choices(run="run-%02d" % i)) for i in range(10)]
        _, outs = w.mcp(calls, caller=who)
        ids += [tool_json(o)["id"] for o in outs]
    assert len(set(ids)) == 20 and all(re.fullmatch(r"[0-9a-f]{32}", i) for i in ids)


def test_tcd13_d19_what_is_shown_is_the_whole_summary_as_text(w):
    # TC-D13
    ann = w.user("ann")
    note = "<img src=x onerror=alert(1)>&x"      # 116b: no / in it, a value with one is a path now
    out = w.launch(caller=ann, params={"note": note})
    assert out["ok"] is True, out
    c = logged_in(w, "ann")
    page = c.get("/c/" + out["id"])
    assert "<img src=x onerror=alert(1)>" not in page.text and "&lt;img src=x onerror=alert(1)&gt;&amp;x" in page.text
    for needle in ("nf-core/ampliseq", "lab-a", "/data/w1/runs/run-one", "s01", "s10"):
        assert needle in page.text, needle
    assert "script-src" in page.headers["content-security-policy"] or "default-src 'none'" in page.headers["content-security-policy"]


def test_tcd14_extra_form_fields_are_ignored(w):
    # TC-D14
    rid = pending(w, w.user("ann"))
    c = logged_in(w, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    r = c.post("/c/" + rid, data={"csrf": token, "pipeline": "evil/pipeline", "bundle": "{}", "ce_name": "elsewhere", "run_name": "x"})
    assert r.status_code == 200
    job = w.jobs()[0]
    args = json.loads(job["args_json"])
    assert args["bundle_sha256"] == w.confirmations()[0]["sha256"] and args["bundle"]["pipeline"] == "nf-core/ampliseq"
    assert job["compute_env"] == "lab-a"


def test_tcd15_a_cancel_is_named_and_queues_one_cancel(w):
    # TC-D15
    ann = w.user("ann")
    w.hand_over(by=ann)
    from helpers import tool_json
    out = tool_json(w.call("cancel", {"run_name": "run-one"}, caller=ann))
    c = logged_in(w, "ann")
    page = c.get("/c/" + out["id"])
    assert "取消" in page.text and "4242" in page.text
    assert c.post("/c/" + out["id"], data={"csrf": csrf_of(page.text)}).status_code == 200
    assert len(w.jobs("cancel_run")) == 1 and len(w.jobs("launch_nextflow")) == 0


def test_tcd16_the_three_servers_keep_to_their_own_routes(w, tmp_path):
    # TC-D16
    from starlette.testclient import TestClient
    from abf_platform import mcp_server, receiver, store
    ann = w.user("ann")
    pat = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id)
    c = w.web()
    for path in ("/mcp", "/runs", "/trace/create", "/agent/poll", "/user-info"):
        assert c.get(path).status_code in (404, 405)
    rec = TestClient(receiver.create_app(w.ip.index, w.ip.tokens, platform_path=w.ip.state_db))
    mcp = TestClient(mcp_server.build_http_app(w.ip.index, w.ip.tokens))
    for other in (rec, mcp):
        for path in ("/login", "/c/" + "0" * 32, "/logout"):
            assert other.get(path, headers={"Authorization": "Bearer " + pat}).status_code in (401, 404, 405)


def test_tcd17_an_ai_with_only_the_token_cannot_press(w):
    # TC-D17
    from abf_platform import store
    ann = w.user("ann")
    rid = pending(w, ann)
    pat = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id)
    h = {"Authorization": "Bearer " + pat}
    c = w.web()
    for attempt in (lambda: c.get("/c/" + rid, headers=h), lambda: c.post("/c/" + rid, headers=h, data={}),
                    lambda: c.post("/c/" + rid, headers=h, data={"csrf": "made-up"}),
                    lambda: c.post("/login", headers=h, data={"name": "ann", "password": pat}),
                    lambda: c.post("/login", headers=h, data={"name": "ann", "password": ""})):
        r = attempt()
        assert 'name="csrf"' not in r.text and "set-cookie" not in r.headers
    assert w.jobs() == [] and w.confirmations()[0]["state"] == "pending"


def test_tcd18_the_web_command_listens_on_loopback_on_its_own_port(w, tmp_path):
    # TC-D18
    import httpx
    h = run_cli(["web", "--help"]).stdout
    assert "--public-url" in h and "127.0.0.1" in h and "--port" in h
    port = free_port()
    assert port not in (8787, 8788)
    proc = start_cli(["web", "--port", str(port)], w.data.env(), tmp_path / "web.log")
    try:
        wait_port(port, proc=proc)
        assert httpx.get("http://127.0.0.1:%d/login" % port, timeout=10).status_code == 200
        assert httpx.get("http://127.0.0.1:%d/mcp" % port, timeout=10).status_code == 404
        assert_loopback_only(port)
    finally:
        stop_proc(proc)
    from abf_platform import web
    import inspect
    assert "BearerAuth" not in inspect.getsource(web)


def test_tcd19_a_void_request_says_so_and_cannot_be_pressed(w):
    # TC-D19
    ann = w.user("ann")
    out = w.launch(caller=ann, answer=form_answer("decline"))
    rid = out_id = w.confirmations()[0]["id"]
    c = logged_in(w, "ann")
    page = c.get("/c/" + rid)
    assert "作廢" in page.text and 'name="csrf"' not in page.text
    assert c.post("/c/" + rid, data={"csrf": "x"}).status_code >= 400 and w.jobs() == []


def test_tcd21b_a_failed_queue_after_the_press_says_not_sent_and_voids(w):
    # TC-C09 on the page
    ann = w.user("ann")
    rid = pending(w, ann)
    c = logged_in(w, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    w.hand_over("run-one", slurm=None)
    r = c.post("/c/" + rid, data={"csrf": token})
    assert "未送出" in r.text and "重新送出" in r.text and w.jobs() == []
    assert w.confirmations()[0]["state"] == "void" and w.confirmations()[0]["void_reason"]


# ---- out of scope ---------------------------------------------------------------------------------------------------------------

def test_tcg03_web_has_no_tls_option():
    # TC-G03
    h = run_cli(["web", "--help"]).stdout
    assert not re.search(r"ssl|cert|tls|key-?file", h, re.I)
    import inspect
    from abf_platform import cli
    assert not re.search(r"ssl_|certfile|keyfile", inspect.getsource(cli.cmd_web))


def test_tcg04_g05_g06_the_web_app_has_five_routes_and_nothing_else(w):
    # TC-G04, TC-G05, TC-G06
    c = w.web()
    routes = sorted((r.path, tuple(sorted(r.methods))) for r in c.app.routes)
    assert routes == [("/c/{rid}", ("GET", "HEAD")), ("/c/{rid}", ("POST",)), ("/login", ("GET", "HEAD")), ("/login", ("POST",)),
                      ("/logout", ("POST",))], routes
    for path in ("/", "/runs", "/ce", "/compute-envs", "/oauth/token", "/oauth/authorize", "/admin", "/launch", "/submit",
                 "/upload", "/password", "/passwd", "/settings", "/api/launch"):
        assert c.get(path).status_code == 404, path
        assert c.post(path, data={"a": "b"}).status_code in (404, 405), path


def test_tcg02_no_switch_turns_the_confirmation_off():
    # TC-G02
    from helpers import PLATFORM_DIR
    bad = []
    for p in PLATFORM_DIR.rglob("*.py"):
        if "tests" in p.parts:
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            # `runs assign --force` changes the owner of an old run; it confirms nothing. Only these two exact lines, named by content, not by a comment.
            if p.name == "cli.py" and ("to change the owner add --force" in line or 'add_argument("--force", action="store_true", help="change the owner of a run that already has one")' in line):
                continue
            if re.search(r"ABF_[A-Z_]*(DEV|YES|SKIP|NOCONFIRM|AUTO_?CONFIRM|ASSUME)|--(yes|force|no-confirm|assume-yes)\b", line):
                bad.append("%s:%d %s" % (p.name, n, line.strip()))
    assert bad == []


def test_tcg01_no_resume_or_retry_door_in_tools_or_actions(w):
    # TC-G01
    from abf_platform import actions
    tools, _ = w.mcp([])
    assert not [t.name for t in tools if re.search(r"resume|retry|relaunch", t.name)]
    assert not [n for n in dir(actions) if re.search(r"resume|retry|relaunch", n)]


# ---- the constitution's new check: an unconfirmed launch is refused through the tool and through the web ------------------------------

def test_tch09_b_c_nothing_reaches_the_queue_through_the_web_without_the_owner_pressing(w):
    # TC-H09 (b), (c)
    from abf_platform import store
    ann = w.user("ann")
    rid = pending(w, ann)
    w.user("bob")
    pat = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id)
    paths = ["/", "/login", "/logout", "/c/" + rid, "/c/" + "a" * 32, "/c/x", "/confirm", "/launch", "/mcp", "/confirmation"]
    attackers = [lambda c: {}, lambda c: {"headers": {"Authorization": "Bearer " + pat}},
                 lambda c: {"headers": {"Authorization": "Basic " + pat}}, lambda c: {"cookies": {"abf_web": "forged.value"}},
                 lambda c: {"data": {"csrf": "wrong", "name": "ann", "password": "wrong"}}]
    for make in attackers:
        c = w.web()
        for method in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
            for path in paths:
                kw = make(c)
                if "cookies" in kw:
                    c.cookies.set("abf_web", kw.pop("cookies")["abf_web"])
                c.request(method, path, **kw)
    # the other person, logged in, and the owner without a token
    b = logged_in(w, "bob")
    b.post("/c/" + rid, data={})
    o = logged_in(w, "ann")
    o.post("/c/" + rid, data={})
    assert w.jobs() == [] and w.confirmations()[0]["state"] == "pending"
