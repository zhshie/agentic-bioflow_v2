# Nothing existing: regression tests for a pending confirmation link across a web restart; no other test restarts the app over a pending request and moves the clock.
"""A pending send-confirmation link (`/c/<id>`) must survive a platform restart (specs/pending-confirm-restart).

"Restart" = a new web app (`w.web()`) over the same folder and files; the old one is dropped. The fake clock `w.clock.t` is put
at an offset from the request's own `created_at`, so the edges (599 / 601 seconds) are exact. Every case is a regression test:
the suspected bug was not proven by a red test, so no platform code was changed.
"""
import logging
import re
from pathlib import Path

import pytest

from human_harness import World, csrf_of
from test_web_login import cookie_value, sessions  # noqa: F401  (sessions kept for symmetry with the login tests)

from abf_platform import confirm, web

EXPIRED = "該申請已逾時（10 分鐘）。請重新送出。"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def key_files(w):
    return [p for p in Path(w.ip.data).iterdir() if p.is_file() and p.name == web.KEY_FILE]


def created_at(w, rid):
    return w.sql("SELECT created_at FROM confirmations WHERE id = ?", (rid,))[0]["created_at"]


def at(w, rid, seconds):
    """Put the fake clock `seconds` after the request was created."""
    w.clock.t = created_at(w, rid) + seconds


def agent_seen_now(w):
    """The agent keeps reporting while the fake clock moves (otherwise the queue refuses for 'agent offline', unrelated to a restart)."""
    import sqlite3
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE agents SET last_seen_at = ?", (w.clock.t,))
    con.close()


def state_of(w, rid):
    return w.sql("SELECT * FROM confirmations WHERE id = ?", (rid,))[0]


def browser(w, cookie):
    c = w.web()
    c.cookies.set("abf_web", cookie)
    return c


def setup_ann(w):
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c = w.web()
    cookie = cookie_value(w.login(c, "ann"))
    return ann, rid, c, cookie


def secrets_of(w, cookie):
    key = key_files(w)[0].read_bytes().strip().decode("latin-1")
    return [key, cookie.split(".", 1)[1] if "." in cookie else cookie]


def test_tc001_tc002_tc003_restart_keeps_pending_and_cookie(w):
    # TC-001, TC-002, TC-003
    ann, rid, c, cookie = setup_ann(w)
    restarted = browser(w, cookie)
    page = restarted.get("/c/" + rid)
    assert page.status_code == 200 and 'name="csrf"' in page.text
    r = restarted.post("/c/" + rid, data={"csrf": csrf_of(page.text)})
    assert r.status_code == 200 and "已送出。工作編號" in r.text
    assert len(w.jobs("launch_nextflow")) == 1
    assert state_of(w, rid)["channel"] == "PAGE"


def test_tc004_tc005_tc006_restart_then_fresh_login_can_confirm(w):
    # TC-004, TC-005, TC-006
    ann, rid, c, cookie = setup_ann(w)
    fresh = w.web()
    first = fresh.get("/c/" + rid)
    assert 'name="next" value="/c/%s"' % rid in first.text and "密碼" in first.text
    assert 'name="csrf"' not in first.text and "找不到" not in first.text
    assert w.jobs() == []
    w.login(fresh, "ann")
    page = fresh.get("/c/" + rid)
    assert page.status_code == 200 and 'name="csrf"' in page.text
    r = fresh.post("/c/" + rid, data={"csrf": csrf_of(page.text)})
    assert "已送出。工作編號" in r.text and len(w.jobs("launch_nextflow")) == 1


def test_tc007_restart_keeps_the_signing_key(w):
    # TC-007
    ann, rid, c, cookie = setup_ann(w)
    before = key_files(w)[0].read_bytes()
    w.web()
    after = key_files(w)
    assert len(after) == 1 and after[0].read_bytes() == before
    assert len([p for p in Path(w.ip.data).iterdir() if "key" in p.name.lower()]) == 1


def test_tc008_a_csrf_from_before_the_restart_is_still_accepted(w):
    # TC-008
    ann, rid, c, cookie = setup_ann(w)
    token = csrf_of(c.get("/c/" + rid).text)
    assert token
    r = browser(w, cookie).post("/c/" + rid, data={"csrf": token})
    assert r.status_code == 200 and "已送出。工作編號" in r.text and len(w.jobs("launch_nextflow")) == 1


def test_tc009_599_seconds_after_the_restart_it_still_sends(w):
    # TC-009
    ann, rid, c, cookie = setup_ann(w)
    restarted = browser(w, cookie)
    token = csrf_of(restarted.get("/c/" + rid).text)
    at(w, rid, confirm.PENDING_SECONDS - 1)
    agent_seen_now(w)
    r = restarted.post("/c/" + rid, data={"csrf": token})
    assert r.status_code == 200 and "已送出。工作編號" in r.text and len(w.jobs("launch_nextflow")) == 1


def test_tc010_tc011_tc012_expired_after_restart_says_so(w):
    # TC-010, TC-011, TC-012
    ann, rid, c, cookie = setup_ann(w)
    token = csrf_of(c.get("/c/" + rid).text)
    restarted = browser(w, cookie)
    at(w, rid, confirm.PENDING_SECONDS + 1)
    page = restarted.get("/c/" + rid)
    assert EXPIRED in page.text and "<button" not in page.text
    r = restarted.post("/c/" + rid, data={"csrf": token})
    assert r.status_code == 410 and "未送出：" in r.text and "請重新送出。" in r.text
    assert w.jobs() == []
    row = state_of(w, rid)
    assert row["state"] == "void" and row["void_reason"] == "expired (逾時)"


def test_tc013_tc014_another_user_is_refused_before_and_after_restart(w):
    # TC-013, TC-014
    ann = w.user("ann")
    w.user("bob")
    rid = w.launch(caller=ann)["id"]
    cb = w.web()
    cookie = cookie_value(w.login(cb, "bob"))
    token = csrf_of(cb.get("/c/" + rid).text) or "x"
    for client in (cb, browser(w, cookie)):
        read = client.get("/c/" + rid)
        assert read.status_code == 403 and 'name="csrf"' not in read.text
        write = client.post("/c/" + rid, data={"csrf": token})
        assert write.status_code == 403
        assert w.jobs() == []
    assert state_of(w, rid)["state"] == "pending"


def test_tc015_same_request_after_restart_with_time_left_is_reused(w):
    # TC-015. (The launch tool reads the real clock, so the request is aged in the database.)
    ann = w.user("ann")
    a = w.launch(caller=ann)["id"]
    _age(w, a, 300)
    w.web()
    assert w.launch(caller=ann)["id"] == a
    assert len(w.confirmations()) == 1


def test_tc016_same_request_after_restart_nearly_expired_is_renewed(w):
    # TC-016
    ann = w.user("ann")
    a = w.launch(caller=ann)["id"]
    _age(w, a, 560)
    w.web()
    b = w.launch(caller=ann)["id"]
    assert b != a and len(w.confirmations()) == 2
    assert state_of(w, a)["state"] == "pending"
    c = w.web()
    ann_cookie = cookie_value(w.login(c, "ann"))
    token = csrf_of(browser(w, ann_cookie).get("/c/" + a).text)
    _age(w, a, 100)      # now past ten minutes
    late = browser(w, ann_cookie)
    assert EXPIRED in late.get("/c/" + a).text
    assert late.post("/c/" + a, data={"csrf": token}).status_code == 410
    assert state_of(w, a)["state"] == "void" and state_of(w, b)["state"] == "pending" and w.jobs() == []


def _age(w, rid, seconds):
    import sqlite3
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET created_at = created_at - ?, expires_at = expires_at - ? WHERE id = ?",
                    (seconds, seconds, rid))
    con.close()


def test_tc017_a_different_folder_is_the_symptom_not_a_bug(w, tmp_path, monkeypatch):
    # TC-017. This is the DEPLOYMENT problem "the new process points at another data folder", not a program bug: a new key,
    # a new database, no such request. Described here, not fixed.
    ann, rid, c, cookie = setup_ann(w)
    other = World(tmp_path / "elsewhere", monkeypatch)
    other.user("ann")
    c2 = other.web()
    c2.cookies.set("abf_web", cookie)
    old = c2.get("/c/" + rid)
    assert 'name="csrf"' not in old.text and "密碼" in old.text
    other.login(c2, "ann")
    gone = c2.get("/c/" + rid)
    assert gone.status_code == 404 and "無此申請" in gone.text
    assert other.jobs() == []
    for text in (old.text, gone.text):
        assert "Traceback" not in text and str(tmp_path) not in text and "SELECT" not in text


def test_tc018_no_secret_in_pages_or_logs(w, caplog):
    # TC-018
    caplog.set_level(logging.DEBUG)
    ann, rid, c, cookie = setup_ann(w)
    pages = []
    r1 = browser(w, cookie)
    p = r1.get("/c/" + rid)
    pages.append(p.text)
    pages.append(r1.post("/c/" + rid, data={"csrf": csrf_of(p.text)}).text)
    fresh = w.web()
    pages.append(fresh.get("/c/" + rid).text)
    w.login(fresh, "ann")
    pages.append(fresh.get("/c/" + rid).text)
    # a second request, for the expired pages
    rid2 = w.launch(caller=ann, run="run-two")["id"]
    c3 = browser(w, cookie)
    tok = csrf_of(c3.get("/c/" + rid2).text)
    at(w, rid2, confirm.PENDING_SECONDS + 1)
    pages.append(c3.get("/c/" + rid2).text)
    gone = c3.post("/c/" + rid2, data={"csrf": tok})
    pages.append(gone.text)
    assert gone.status_code == 410 and "請重新送出。" in gone.text
    everything = "\n".join(pages) + "\n" + caplog.text
    for secret in secrets_of(w, cookie):
        assert secret and secret not in everything
    for text in pages[2:3] + pages[4:]:     # login page, expired page, 410 page: no machine path, no SQL, no stack
        assert "Traceback" not in text and str(w.tmp) not in text and not re.search(r"\bSELECT\b", text)
    assert all("Traceback" not in t for t in pages)


def test_tc019_nothing_is_written_until_ann_presses_send(w):
    # TC-019
    ann, rid, c, cookie = setup_ann(w)
    restarted = browser(w, cookie)
    page = restarted.get("/c/" + rid)
    assert w.jobs() == []
    w.web().get("/login")
    assert w.launch(caller=ann)["id"] == rid and w.jobs() == []
    restarted.post("/c/" + rid, data={"csrf": csrf_of(page.text)})
    assert len(w.jobs("launch_nextflow")) == 1


def test_tc020_the_restart_does_not_restart_the_ten_minutes(w):
    # TC-020
    ann, rid, c, cookie = setup_ann(w)
    at(w, rid, 300)
    restarted = browser(w, cookie)
    assert 'name="csrf"' in restarted.get("/c/" + rid).text
    at(w, rid, 601)
    page = restarted.get("/c/" + rid)
    assert EXPIRED in page.text and "<button" not in page.text
    assert confirm.PENDING_SECONDS == 600
