# Nothing existing: tests of the web password (set only at a terminal) and of the browser login of spec 009c; the rules (scrypt only, never a PAT, 5 failures a minute, 12 hours) are ours.
"""009c, user story 2: name + web password, a signed cookie of 12 hours. Test cases are named in the comments (TC-B01 ...)."""
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from helpers import free_port, pkg_env, start_cli, stop_proc, wait_port
from human_harness import PASSWORD, World, csrf_of
from launch_harness import Pty, cli_argv

CANARY = "CANARY-pw-7d3f9a1c5b2e4f60"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def set_by_terminal(w, name, first, second=None, env=None):
    """`abf-platform user passwd NAME` on a real pseudo-terminal; the person types `first`, then `second`."""
    p = Pty(cli_argv("user", "passwd", name), env or w.data.env())
    assert p.wait_for("New web password", 30), p.text()
    p.send(first + "\n")
    assert p.wait_for("again", 30), p.text()
    p.send((second if second is not None else first) + "\n")
    return p.finish(30)


def hashes(w):
    con = sqlite3.connect(str(w.ip.tokens))
    try:
        return dict(con.execute("SELECT name, password_hash FROM users").fetchall())
    finally:
        con.close()


def data_bytes(w):
    out = b""
    for p in Path(w.ip.data).rglob("*"):
        if p.is_file():
            out += p.read_bytes()
    return out


def cookie_value(resp):
    m = re.search(r"abf_web=([^;]+)", resp.headers.get("set-cookie", ""))
    return m.group(1) if m else None


def sessions(w):
    con = sqlite3.connect(str(w.ip.tokens))
    try:
        return con.execute("SELECT * FROM web_sessions").fetchall()
    finally:
        con.close()


def pending_for(w, caller):
    return w.launch(caller=caller)["id"]


def test_tcb01_the_password_is_set_on_a_real_terminal_and_never_printed(w):
    # TC-B01
    w.user("ann", password=None)
    rc, screen = set_by_terminal(w, "ann", CANARY)
    assert rc == 0, screen
    assert CANARY not in screen
    client = w.web()
    assert w.login(client, "ann", CANARY).status_code in (200, 303)


def test_tcb02_without_a_terminal_nothing_is_set(w):
    # TC-B02
    w.user("ann", password=None)
    r = subprocess.run([sys.executable, "-m", "abf_platform", "user", "passwd", "ann"], input=(CANARY + "\n") * 2, text=True,
                       capture_output=True, env=w.data.env(), timeout=60)
    assert r.returncode != 0 and "終端機" in r.stdout + r.stderr
    assert hashes(w) == {"ann": None}


def test_tcb03_no_flag_and_no_environment_variable_can_stand_in_for_the_keyboard(w):
    # TC-B03
    w.user("ann", password=None)
    for argv in (["--password", CANARY], ["--password-file", "x"], [CANARY]):
        r = subprocess.run([sys.executable, "-m", "abf_platform", "user", "passwd", "ann"] + argv, capture_output=True, text=True,
                           env=w.data.env(), timeout=60)
        assert r.returncode != 0
    env = w.data.env(ABF_WEB_PASSWORD=CANARY, ABF_PLATFORM_WEB_PASSWORD=CANARY)
    p = Pty(cli_argv("user", "passwd", "ann"), env)
    assert p.wait_for("New web password", 30), p.text()        # it still asks: the variable is not looked at
    p.send("\x04")
    p.send("\x04")
    p.finish(30)
    assert hashes(w) == {"ann": None}


def test_tcb04_two_different_entries_change_nothing(w):
    # TC-B04
    w.user("ann")
    before = hashes(w)
    rc, screen = set_by_terminal(w, "ann", "new password one", "new password two")
    assert rc != 0 and hashes(w) == before
    assert w.login(w.web(), "ann", PASSWORD).status_code in (200, 303)


def test_tcb05_an_unknown_user_is_refused_and_not_created(w):
    # TC-B05
    p = Pty(cli_argv("user", "passwd", "nobody"), w.data.env())
    rc, screen = p.finish(30)
    assert rc != 0 and "沒有這個使用者" in screen
    con = sqlite3.connect(str(w.ip.tokens))
    assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_tcb06_only_a_slow_hash_is_kept_and_each_user_has_a_salt(w):
    # TC-B06
    w.user("ann", password=None)
    w.user("bob", password=None)
    assert set_by_terminal(w, "ann", CANARY)[0] == 0
    assert set_by_terminal(w, "bob", CANARY)[0] == 0
    h = hashes(w)
    for name in ("ann", "bob"):
        assert re.fullmatch(r"scrypt\$\d+\$\d+\$\d+\$[A-Za-z0-9+/=_-]+\$[A-Za-z0-9+/=_-]+", h[name]), h[name]
    assert h["ann"] != h["bob"]
    assert CANARY.encode() not in data_bytes(w)


def test_tcb06_a_short_password_is_refused(w):
    # TC-B06 (a password worth hashing)
    w.user("ann", password=None)
    rc, screen = set_by_terminal(w, "ann", "short")
    assert rc != 0 and hashes(w) == {"ann": None}


def test_tcb07_a_new_password_replaces_the_old_one(w):
    # TC-B07
    w.user("ann")
    assert set_by_terminal(w, "ann", "a brand new passphrase")[0] == 0
    c = w.web()
    assert w.login(c, "ann", PASSWORD).status_code == 401
    assert w.login(c, "ann", "a brand new passphrase").status_code in (200, 303)


def test_tcb08_b09_a_good_login_gives_a_cookie_and_a_session(w):
    # TC-B08, TC-B09
    ann = w.user("ann")
    rid = pending_for(w, ann)
    c = w.web()
    r = w.login(c, "ann")
    assert r.status_code in (200, 303)
    header = r.headers["set-cookie"]
    assert "HttpOnly" in header and "SameSite=Strict" in header and "Max-Age=43200" in header and "Secure" not in header
    rows = sessions(w)
    assert len(rows) == 1 and rows[0][1] == ann.user_id
    page = c.get("/c/" + rid)
    assert page.status_code == 200 and "送出" in page.text and csrf_of(page.text)


def test_tcb10_a_public_https_address_makes_the_cookie_secure(w):
    # TC-B10
    w.user("ann")
    r = w.login(w.web(public_url="https://abf.example"), "ann")
    assert "Secure" in r.headers["set-cookie"]
    r = w.login(w.web(public_url="http://127.0.0.1:8789"), "ann")
    assert "Secure" not in r.headers["set-cookie"]


@pytest.mark.parametrize("name,password", [("ann", "not the password"), ("ghost", "anything at all"), ("bob", ""), ("bob", "x"),
                                          ("ann", "")])
def test_tcb11_to_b13_a_wrong_name_or_password_gets_no_cookie(w, name, password):
    # TC-B11, TC-B12, TC-B13 (bob never set a web password)
    w.user("ann")
    w.user("bob", password=None)
    r = w.login(w.web(), name, password)
    assert r.status_code == 401 and "set-cookie" not in r.headers and sessions(w) == []
    assert password == "" or password not in r.text


def test_tcb14_a_bearer_token_never_logs_into_the_web(w):
    # TC-B14, TC-D17
    from abf_platform import store
    ann = w.user("ann")
    rid = pending_for(w, ann)
    pat = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id)
    h = {"Authorization": "Bearer " + pat}
    c = w.web()
    before = (w.counts(), w.sql("SELECT state FROM confirmations"))
    for r in (c.get("/login", headers=h), c.post("/login", headers=h, data={"name": "", "password": ""}),
              c.post("/login", headers=h, data={"name": "ann", "password": pat}), c.get("/c/" + rid, headers=h),
              c.post("/c/" + rid, headers=h, data={"csrf": "x"}), c.post("/c/" + rid, headers=h, data={})):
        assert "set-cookie" not in r.headers
        assert "送出" not in r.text or r.status_code >= 400 or "name=\"csrf\"" not in r.text
    assert sessions(w) == []
    assert c.get("/c/" + rid, headers=h).text.count('name="csrf"') == 0
    assert before == (w.counts(), w.sql("SELECT state FROM confirmations"))


def test_tcb15_the_token_is_not_a_password(w):
    # TC-B15
    from abf_platform import store
    ann = w.user("ann")
    pat = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id)
    r = w.login(w.web(), "ann", pat)
    assert r.status_code == 401 and "set-cookie" not in r.headers


def test_tcb16_b17_five_failures_a_minute_lock_that_name_only(w):
    # TC-B16, TC-B17
    w.user("ann")
    w.user("bob")
    c = w.web()
    for _ in range(5):
        assert w.login(c, "ann", "wrong wrong").status_code == 401
    r = w.login(c, "ann", PASSWORD)
    assert r.status_code == 429 and "太頻繁" in r.text and "set-cookie" not in r.headers
    assert w.login(c, "bob", PASSWORD).status_code in (200, 303)
    w.clock.t += 61
    assert w.login(c, "ann", PASSWORD).status_code in (200, 303)


def test_tcb18_only_the_hash_of_the_cookie_is_kept_and_it_ends_in_twelve_hours(w):
    # TC-B18
    w.user("ann")
    c = w.web()
    r = w.login(c, "ann")
    value = cookie_value(r)
    raw_id = value.split(".")[0]
    con = sqlite3.connect(str(w.ip.tokens))
    assert [x[1] for x in con.execute("PRAGMA table_info(web_sessions)")] == ["id_hash", "user_id", "created_at", "expires_at"]
    row = con.execute("SELECT * FROM web_sessions").fetchone()
    assert abs(row[3] - row[2] - 12 * 3600) < 0.001 and row[2] == w.clock.t
    blob = data_bytes(w)
    assert raw_id.encode() not in blob and value.encode() not in blob


def test_tcb19_b24_the_cookie_stops_after_twelve_hours_and_not_before(w):
    # TC-B19, TC-B24
    ann = w.user("ann")
    rid = pending_for(w, ann)
    c = w.web()
    w.login(c, "ann")
    csrf = csrf_of(c.get("/c/" + rid).text)
    w.clock.t += 11 * 3600 + 59 * 60
    assert csrf_of(c.get("/c/" + rid).text)
    w.clock.t += 61 + 0.0
    w.clock.t += 0
    expired = c.get("/c/" + rid)
    assert "name=\"csrf\"" not in expired.text and "密碼" in expired.text
    r = c.post("/c/" + rid, data={"csrf": csrf})
    assert r.status_code in (401, 403) and w.jobs() == []
    assert w.sql("SELECT state FROM confirmations")[0]["state"] == "pending"


def test_tcb20_a_changed_or_borrowed_cookie_is_no_login(w):
    # TC-B20
    ann = w.user("ann")
    w.user("bob")
    rid = pending_for(w, ann)
    c1 = w.web()
    value = cookie_value(w.login(c1, "ann"))
    c2 = w.web()
    other = cookie_value(w.login(c2, "bob"))
    id_hash = sessions(w)[0][0]
    tampered = value[:-1] + ("A" if value[-1] != "A" else "B")
    borrowed = other.split(".")[0] + "." + value.split(".", 1)[1]
    for bad in (tampered, borrowed, id_hash, value.split(".")[0], ""):
        fresh = w.web()
        fresh.cookies.set("abf_web", bad)
        page = fresh.get("/c/" + rid)
        assert 'name="csrf"' not in page.text
        assert fresh.post("/c/" + rid, data={"csrf": "x"}).status_code in (401, 403)
    assert w.jobs() == []
    good = w.web()
    good.cookies.set("abf_web", value)
    assert csrf_of(good.get("/c/" + rid).text)


def test_tcb21_the_signing_key_is_in_the_data_folder_owner_only_and_survives_a_restart(w):
    # TC-B21
    ann = w.user("ann")
    rid = pending_for(w, ann)
    before = {p.name for p in Path(w.ip.data).iterdir()}
    c = w.web()
    value = cookie_value(w.login(c, "ann"))
    new = [p for p in Path(w.ip.data).iterdir() if p.name not in before and not p.name.startswith("tokens.db")]
    keys = [p for p in new if p.is_file() and "key" in p.name.lower()]
    assert len(keys) == 1, new
    if os.name == "posix":
        assert (keys[0].stat().st_mode & 0o777) == 0o600
    key = keys[0].read_bytes()
    assert key and key.strip() not in value.encode()
    restarted = w.web()
    restarted.cookies.set("abf_web", value)
    assert csrf_of(restarted.get("/c/" + rid).text)
    tracked = subprocess.run(["git", "ls-files"], cwd=str(Path(__file__).resolve().parents[2]), capture_output=True, text=True).stdout
    assert keys[0].name not in tracked


def test_tcb22_a_web_cookie_opens_no_other_door(w, tmp_path):
    # TC-B22
    import httpx
    from abf_platform import receiver
    from starlette.testclient import TestClient
    w.user("ann")
    c = w.web()
    value = cookie_value(w.login(c, "ann"))
    app = TestClient(receiver.create_app(w.ip.index, w.ip.tokens, platform_path=w.ip.state_db))
    for method, path in (("GET", "/user-info"), ("POST", "/agent/poll"), ("POST", "/trace/create"), ("PUT", "/trace/x/begin"),
                         ("GET", "/mcp"), ("GET", "/login"), ("GET", "/c/" + "0" * 32)):
        r = app.request(method, path, cookies={"abf_web": value}, json={})
        assert r.status_code in (401, 404, 405), (path, r.status_code)
    port = free_port()
    proc = start_cli(["mcp", "--http", "--port", str(port)], w.data.env(), tmp_path / "m.log")
    try:
        wait_port(port, proc=proc)
        r = httpx.post("http://127.0.0.1:%d/mcp" % port, json={}, cookies={"abf_web": value}, timeout=10)
        assert r.status_code == 401
    finally:
        stop_proc(proc)


def test_tcb23_no_password_and_no_cookie_in_what_is_said(w, caplog, capsys):
    # TC-B23
    import logging
    caplog.set_level(logging.DEBUG)
    w.user("ann")
    c = w.web()
    bad = w.login(c, "ann", CANARY)
    good = w.login(c, "ann")
    value = cookie_value(good)
    seen = bad.text + good.text + c.get("/login").text
    out = capsys.readouterr()
    for text in (seen, caplog.text, out.out, out.err):
        assert CANARY not in text and PASSWORD not in text
        assert value.split(".")[0] not in text


def test_tcb25_a_disabled_person_cannot_log_in_and_a_cookie_stops_working(w):
    # TC-B25
    ann = w.user("ann")
    rid = pending_for(w, ann)
    c = w.web()
    w.login(c, "ann")
    csrf = csrf_of(c.get("/c/" + rid).text)
    con = sqlite3.connect(str(w.ip.tokens))
    con.execute("UPDATE users SET disabled_at = ?", (w.clock.t,))
    con.commit()
    con.close()
    assert c.post("/c/" + rid, data={"csrf": csrf}).status_code in (401, 403) and w.jobs() == []
    assert w.login(w.web(), "ann").status_code == 401


def test_tcb26_a_new_password_ends_every_browser_login_at_once(w):
    # TC-B07 and plan ruling 7
    from abf_platform import store
    ann = w.user("ann")
    rid = pending_for(w, ann)
    c = w.web()
    w.login(c, "ann")
    assert sessions(w)
    store.set_web_password(w.ip.tokens, "ann", "a different password")
    assert sessions(w) == []
    assert 'name="csrf"' not in c.get("/c/" + rid).text
