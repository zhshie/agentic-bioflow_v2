# Nothing existing: regression tests for specs/web-chrome-origin (Chrome sends `Origin: null` under Referrer-Policy: no-referrer); the page and its rules are ours.
"""Bug web-chrome-origin: every response says Referrer-Policy: same-origin, so a browser sends a real Origin on a same-origin POST;
"null" and foreign origins stay refused. Test cases are named in the comments (WCO-1 ...)."""
import importlib.util
import os
import subprocess
import sys
import textwrap

import pytest

from helpers import free_port, start_cli, stop_proc, wait_port
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


DRIVER = textwrap.dedent('''
    import sys
    from playwright.sync_api import sync_playwright
    base, name, password, rid = sys.argv[1:5]
    posts = []
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="chrome", headless=True)
        except Exception as e:
            print("NOBROWSER", e)
            sys.exit(77)
        page = b.new_page()
        page.on("response", lambda r: posts.append((r.request.method, r.status)) if r.request.method == "POST" else None)
        page.goto(base + "/login?next=/c/" + rid)
        page.fill("input[name=name]", name)
        page.fill("input[name=password]", password)
        page.click("button[type=submit]")
        page.wait_for_load_state()
        page.click("button[type=submit]")
        page.wait_for_load_state()
        print("POSTS", posts)
        print("BODY", "已送出" in page.content())
        b.close()
''')


def playwright_python():
    cand = os.environ.get("ABF_PLAYWRIGHT_PYTHON")
    if cand:
        return cand
    return sys.executable if importlib.util.find_spec("playwright") else None


def test_wco3_a_real_chrome_logs_in_and_presses_send(w, tmp_path):
    # WCO-3: real Chrome (skipped where there is no playwright or no Chrome); 303 on login, no 403, the request is sent
    py = playwright_python()
    if not py:
        pytest.skip("no python with playwright (set ABF_PLAYWRIGHT_PYTHON)")
    ann = w.user("ann")
    rid = pending(w, ann)
    driver = tmp_path / "drive.py"
    driver.write_text(DRIVER, encoding="utf-8")
    port = free_port()
    proc = start_cli(["web", "--port", str(port)], w.data.env(), tmp_path / "web.log")
    try:
        wait_port(port, proc=proc)
        out = subprocess.run([py, str(driver), "http://127.0.0.1:%d" % port, "ann", PASSWORD, rid], capture_output=True, text=True, timeout=120)
    finally:
        stop_proc(proc)
    if out.returncode == 77:
        pytest.skip("no Chrome: " + out.stdout.strip())
    assert out.returncode == 0, out.stdout + out.stderr
    assert "403" not in out.stdout, out.stdout
    assert "('POST', 303)" in out.stdout and "BODY True" in out.stdout, out.stdout
