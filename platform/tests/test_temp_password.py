# Nothing existing: the one-time temporary web password (users.temp_until, its issue, check, change and the terminal command) is new in this task, so no other test file covers it.
"""temp-password: the administrator issues a one-time password at a real terminal; the person must change it at the first web login.
Test case IDs (TC-nnn of specs/temp-password/test-case.md) are named in the comments. The documentation cases are in test_onboarding_doc.py.
The platform's normal way to open tokens.db is store.connect_tokens (TC-056)."""
import logging
import re
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from helpers import REPO_ROOT
from human_harness import PASSWORD, World
from launch_harness import Pty, cli_argv

NEW = "a brand new passphrase"
CHARSET = re.compile(r"[A-Za-z0-9_-]{16}")
WRONG = "the current password is wrong (目前的密碼不對)"
SHORT = "the password must be at least 8 characters (密碼至少 8 個字元)"
LONG = "the password must be at most 1000 characters (密碼最多 1000 個字元)"
DIFFER = "the new password must differ from the current one (新密碼不能跟目前的一樣)"
GHOST = "no such user: ghost (沒有這個使用者)"
STORE_SRC = (REPO_ROOT / "platform" / "abf_platform" / "store.py").read_text(encoding="utf-8")
CLI_SRC = (REPO_ROOT / "platform" / "abf_platform" / "cli.py").read_text(encoding="utf-8")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def st():
    from abf_platform import store
    return store


def q(w, sql, args=()):
    con = sqlite3.connect(str(w.ip.tokens))
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def temp_until(w, name):
    return q(w, "SELECT temp_until FROM users WHERE name = ?", (name,))[0][0]


def hash_of(w, name):
    return q(w, "SELECT password_hash FROM users WHERE name = ?", (name,))[0][0]


def uid_of(w, name):
    return q(w, "SELECT id FROM users WHERE name = ?", (name,))[0][0]


def user_state(w):
    return q(w, "SELECT name, password_hash, temp_until, disabled_at FROM users ORDER BY name")


def sessions(w):
    return q(w, "SELECT id_hash, user_id FROM web_sessions ORDER BY id_hash")


def data_bytes(w):
    out = b""
    for p in Path(w.ip.data).rglob("*"):
        if p.is_file():
            out += p.read_bytes()
    return out


def issue(w, name="ann", now=1000.0):
    return st().issue_temporary_password(w.ip.tokens, name, now=now)


def session_of(w, name, now=1000.0):
    sid, _ = st().create_web_session(w.ip.tokens, uid_of(w, name), now)
    return sid


def err(fn, *a, **k):
    with pytest.raises(ValueError) as e:
        fn(*a, **k)
    return str(e.value)


def temp_by_terminal(w, name="ann", env=None):
    """`abf-platform user passwd NAME --temporary` on a real pseudo-terminal: (exit code, screen, lines)."""
    p = Pty(cli_argv("user", "passwd", name, "--temporary"), env or w.data.env())
    rc, screen = p.finish(60)
    return rc, screen, screen.splitlines()


# ---- US1: issue ----------------------------------------------------------------------------------------------------

def test_tc001_tc002_the_issue_returns_a_16_char_password_and_a_72_hour_end(w):
    # TC-001, TC-002
    w.user("ann")
    out = issue(w)
    assert set(out) == {"password", "expires_at"}
    assert len(out["password"]) == 16 and CHARSET.fullmatch(out["password"])
    assert out["expires_at"] == 1000.0 + 259200
    assert st().TEMP_PASSWORD_SECONDS == 72 * 3600


def test_tc003_tc004_two_issues_differ_and_only_a_hash_is_kept(w):
    # TC-003, TC-004
    w.user("ann")
    a, b = issue(w)["password"], issue(w)["password"]
    assert a != b
    assert re.fullmatch(r"scrypt\$\d+\$\d+\$\d+\$[A-Za-z0-9+/=_-]+\$[A-Za-z0-9+/=_-]+", hash_of(w, "ann"))
    blob = data_bytes(w)
    assert a.encode() not in blob and b.encode() not in blob


def test_tc005_tc006_the_issue_ends_that_users_sessions_only(w):
    # TC-005, TC-006
    w.user("ann")
    w.user("bob")
    session_of(w, "ann")
    session_of(w, "ann", 1001.0)
    bob_sid = session_of(w, "bob")
    bob_before = [r for r in user_state(w) if r[0] == "bob"]
    bob_id = uid_of(w, "bob")
    bob_sessions = [s for s in sessions(w) if s[1] == bob_id]
    issue(w)
    assert [s for s in sessions(w) if s[1] == uid_of(w, "ann")] == []
    assert [r for r in user_state(w) if r[0] == "bob"] == bob_before
    assert [s for s in sessions(w) if s[1] == bob_id] == bob_sessions and len(bob_sessions) == 1
    assert st().web_session_user(w.ip.tokens, bob_sid, 1002.0)["name"] == "bob"


def test_tc007_a_second_issue_replaces_the_first(w):
    # TC-007
    w.user("ann")
    a, b = issue(w)["password"], issue(w)["password"]
    assert st().check_web_password(w.ip.tokens, "ann", a, now=1001.0) is None
    assert st().check_web_password(w.ip.tokens, "ann", b, now=1001.0)["must_change"] is True


def test_tc008_the_old_ordinary_password_stops_working(w):
    # TC-008
    w.user("ann")
    assert st().check_web_password(w.ip.tokens, "ann", PASSWORD)["must_change"] is False
    issue(w)
    assert st().check_web_password(w.ip.tokens, "ann", PASSWORD, now=1001.0) is None


def test_tc009_tc010_an_unknown_user_is_refused_and_nothing_changes(w):
    # TC-009, TC-010
    w.user("ann")
    session_of(w, "ann")
    before = (user_state(w), sessions(w), q(w, "SELECT COUNT(*) FROM users"))
    assert err(st().issue_temporary_password, w.ip.tokens, "ghost") == GHOST
    assert "沒有這個使用者" in GHOST
    assert before == (user_state(w), sessions(w), q(w, "SELECT COUNT(*) FROM users"))


# ---- US2: check ----------------------------------------------------------------------------------------------------

def test_tc011_tc012_tc013_must_change_is_true_only_for_a_temporary_password(w):
    # TC-011, TC-012, TC-013
    w.user("ann")
    w.user("bob")
    t = issue(w)["password"]
    ok = st().check_web_password(w.ip.tokens, "ann", t, now=1001.0)
    assert set(ok) == {"user_id", "name", "lab", "must_change"} and ok["must_change"] is True and ok["name"] == "ann"
    assert st().check_web_password(w.ip.tokens, "bob", PASSWORD)["must_change"] is False
    assert st().check_web_password(w.ip.tokens, "ann", "wrong wrong wrong", now=1001.0) is None


def test_tc014_a_disabled_user_never_passes(w):
    # TC-014
    w.user("ann")
    t = issue(w)["password"]
    con = sqlite3.connect(str(w.ip.tokens))
    with con:
        con.execute("UPDATE users SET disabled_at = 5.0 WHERE name = 'ann'")
    con.close()
    assert st().check_web_password(w.ip.tokens, "ann", t, now=1001.0) is None


def test_tc015_tc016_the_password_ends_at_its_time(w):
    # TC-015, TC-016
    w.user("ann")
    out = issue(w)
    e = out["expires_at"]
    assert st().check_web_password(w.ip.tokens, "ann", out["password"], now=e - 1)["must_change"] is True
    assert st().check_web_password(w.ip.tokens, "ann", out["password"], now=e + 1) is None


def test_tc017_an_expired_and_a_wrong_password_cost_one_hash_each(w, monkeypatch):
    # TC-017
    w.user("ann")
    out = issue(w)
    store = st()
    calls = []
    real = store.password_matches
    monkeypatch.setattr(store, "password_matches", lambda s, p: calls.append(1) or real(s, p))
    assert store.check_web_password(w.ip.tokens, "ann", out["password"], now=out["expires_at"] + 1) is None
    assert len(calls) == 1
    assert store.check_web_password(w.ip.tokens, "ann", "wrong wrong wrong", now=1001.0) is None
    assert len(calls) == 2


def test_tc018_the_terminal_password_is_not_temporary(w):
    # TC-018
    w.user("ann")
    issue(w)
    st().set_web_password(w.ip.tokens, "ann", NEW)
    assert temp_until(w, "ann") is None
    assert st().check_web_password(w.ip.tokens, "ann", NEW)["must_change"] is False


def test_tc019_the_length_messages_of_set_web_password_are_unchanged(w):
    # TC-019
    w.user("ann")
    assert err(st().set_web_password, w.ip.tokens, "ann", "x" * 7) == SHORT
    assert err(st().set_web_password, w.ip.tokens, "ann", "x" * 1001) == LONG


def test_tc020_three_positional_arguments_still_work(w):
    # TC-020
    w.user("ann")
    assert st().check_web_password(w.ip.tokens, "ann", PASSWORD)["name"] == "ann"
    assert st().web_session_user(w.ip.tokens, "no-such", 1.0) is None


# ---- US3: fail-closed -----------------------------------------------------------------------------------------------

def test_tc021_to_tc024_a_session_of_a_temporary_password(w):
    # TC-021, TC-022, TC-023, TC-024
    w.user("ann")
    w.user("bob")
    out = issue(w)
    sid = session_of(w, "ann", 1001.0)
    bsid = session_of(w, "bob", 1001.0)
    store = st()
    assert store.web_session_user(w.ip.tokens, sid, 1002.0) is None
    got = store.web_session_user(w.ip.tokens, sid, 1002.0, allow_must_change=True)
    assert got["must_change"] is True and got["name"] == "ann" and {"user_id", "lab"} <= set(got)
    assert store.web_session_user(w.ip.tokens, bsid, 1002.0)["must_change"] is False
    assert store.web_session_user(w.ip.tokens, bsid, 1002.0, allow_must_change=True)["must_change"] is False
    late = out["expires_at"] + 1
    con = sqlite3.connect(str(w.ip.tokens))
    with con:
        con.execute("UPDATE web_sessions SET expires_at = ?", (late + 100,))
    con.close()
    assert store.web_session_user(w.ip.tokens, sid, late) is None
    assert store.web_session_user(w.ip.tokens, sid, late, allow_must_change=True) is None


def login_temp(w, name="ann"):
    out = issue(w, name, now=w.clock.t)
    c = w.web()
    r = w.login(c, name, out["password"])
    return c, r, out


def test_tc025_a_temporary_login_sees_the_login_page_not_the_board(w):
    # TC-025
    w.user("ann")
    c, r, _ = login_temp(w)
    assert r.status_code == 303
    page = c.get("/")
    assert page.status_code == 303 and page.headers["location"] == "/login"


def test_tc026_a_temporary_login_cannot_press_send(w):
    # TC-026
    from abf_platform import web
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c, r, _ = login_temp(w)
    sid = c.cookies.get("abf_web").split(".")[0]
    key = web._signing_key(Path(w.ip.state_db).parent)
    for csrf in (web._mac(key, "csrf", sid, rid), "x"):
        resp = c.post("/c/" + rid, data={"csrf": csrf})
        assert resp.status_code != 200
    assert w.jobs() == []
    assert w.sql("SELECT state FROM confirmations")[0]["state"] == "pending"


def test_tc027_every_login_route_treats_a_temporary_session_as_no_login(w):
    # TC-027
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c, r, _ = login_temp(w)
    anon = w.web()
    seen = 0
    for route in c.app.routes:
        path = getattr(route, "path", "")
        if path in ("/login", "/logout") or path.startswith("/.well-known") or path in ("/register", "/token", "/revoke"):
            continue
        path = path.replace("{rid}", rid).replace("{verb}", "resume")
        for method in sorted((getattr(route, "methods", None) or {"GET"}) - {"HEAD", "OPTIONS"}):
            kw = {"data": {"csrf": "x"}} if method == "POST" else {}
            a = c.request(method, path, headers={"origin": "http://testserver"}, **kw)
            b = anon.request(method, path, headers={"origin": "http://testserver"}, **kw)
            assert (a.status_code, a.headers.get("location")) == (b.status_code, b.headers.get("location")), (method, path)
            assert "ann" not in a.text or a.status_code >= 300
            seen += 1
    assert seen >= 8
    assert w.jobs() == []


def test_tc028_a_temporary_session_can_log_out(w):
    # TC-028
    from abf_platform import web
    w.user("ann")
    c, r, _ = login_temp(w)
    sid = c.cookies.get("abf_web").split(".")[0]
    assert len(sessions(w)) == 1
    key = web._signing_key(Path(w.ip.state_db).parent)
    resp = c.post("/logout", data={"csrf": web._mac(key, "csrf", sid, "logout")})
    assert resp.status_code == 303 and sessions(w) == []


# ---- US4: change ---------------------------------------------------------------------------------------------------

def test_tc029_to_tc032_a_change_keeps_only_the_given_session(w):
    # TC-029, TC-030, TC-031, TC-032
    w.user("ann")
    t = issue(w)["password"]
    sid = session_of(w, "ann", 1001.0)
    other = session_of(w, "ann", 1002.0)
    out = st().change_web_password(w.ip.tokens, "ann", t, NEW, keep_sid=sid, now=1003.0)
    assert set(out) == {"user_id", "name", "lab"}
    store = st()
    assert store.check_web_password(w.ip.tokens, "ann", t, now=1004.0) is None
    assert store.check_web_password(w.ip.tokens, "ann", NEW, now=1004.0)["must_change"] is False
    assert temp_until(w, "ann") is None
    assert store.web_session_user(w.ip.tokens, sid, 1004.0)["name"] == "ann"
    assert store.web_session_user(w.ip.tokens, other, 1004.0) is None
    store.change_web_password(w.ip.tokens, "ann", NEW, NEW + "2", keep_sid=None, now=1005.0)
    assert sessions(w) == []


def test_tc033_a_foreign_keep_sid_keeps_nothing_of_ann(w):
    # TC-033
    w.user("ann")
    w.user("bob")
    session_of(w, "ann")
    bob = session_of(w, "bob")
    bob_rows = [s for s in sessions(w) if s[1] == uid_of(w, "bob")]
    st().change_web_password(w.ip.tokens, "ann", PASSWORD, NEW, keep_sid=bob, now=1000.0)
    assert [s for s in sessions(w) if s[1] == uid_of(w, "ann")] == []
    assert [s for s in sessions(w) if s[1] == uid_of(w, "bob")] == bob_rows and len(bob_rows) == 1


def test_tc034_tc035_tc036_tc037_every_failed_old_password_gives_one_sentence(w):
    # TC-034, TC-035, TC-036, TC-037
    w.user("ann")
    t = issue(w)["password"]
    h = hash_of(w, "ann")
    tu = temp_until(w, "ann")
    store = st()
    assert err(store.change_web_password, w.ip.tokens, "ann", "not the password", NEW, now=1001.0) == WRONG
    assert err(store.change_web_password, w.ip.tokens, "ghost", t, NEW, now=1001.0) == WRONG
    assert (hash_of(w, "ann"), temp_until(w, "ann")) == (h, tu)
    assert err(store.change_web_password, w.ip.tokens, "ann", t, NEW, now=tu + 1) == WRONG        # TC-037
    assert (hash_of(w, "ann"), temp_until(w, "ann")) == (h, tu)
    con = sqlite3.connect(str(w.ip.tokens))
    with con:
        con.execute("UPDATE users SET disabled_at = 5.0 WHERE name = 'ann'")
    con.close()
    assert err(store.change_web_password, w.ip.tokens, "ann", t, NEW, now=1001.0) == WRONG        # TC-036
    assert hash_of(w, "ann") == h


def test_tc038_a_too_long_old_password_is_not_hashed(w, monkeypatch):
    # TC-038
    w.user("ann")
    store = st()
    calls = []
    monkeypatch.setattr(store, "password_matches", lambda s, p: calls.append(1) or False)
    assert err(store.change_web_password, w.ip.tokens, "ann", "x" * 1001, NEW) == WRONG
    assert calls == []


def test_tc039_to_tc043_the_order_of_the_checks(w):
    # TC-039, TC-040, TC-041, TC-042, TC-043
    w.user("ann")
    c = st().change_web_password
    assert err(c, w.ip.tokens, "ann", "x" * 7, "x" * 7) == SHORT
    assert err(c, w.ip.tokens, "ann", PASSWORD, "x" * 1001) == LONG
    assert err(c, w.ip.tokens, "ann", PASSWORD, None) == SHORT
    assert err(c, w.ip.tokens, "ann", PASSWORD, 12345678) == SHORT
    assert err(c, w.ip.tokens, "ann", PASSWORD, PASSWORD) == DIFFER
    assert err(c, w.ip.tokens, "ann", "a wrong one yes", "a wrong one yes") == DIFFER


@pytest.mark.parametrize("n", [8, 1000])
def test_tc044_tc045_the_new_password_may_be_8_or_1000_characters(w, n):
    # TC-044, TC-045
    w.user("ann")
    new = "n" * n
    st().change_web_password(w.ip.tokens, "ann", PASSWORD, new)
    assert st().check_web_password(w.ip.tokens, "ann", new)["name"] == "ann"


def test_tc046_a_password_changed_meanwhile_is_not_overwritten(w, monkeypatch):
    # TC-046
    w.user("ann")
    store = st()
    real = store.password_matches
    other = "somebody else set this"

    def racing(stored, password):
        ok = real(stored, password)
        store.set_web_password(w.ip.tokens, "ann", other)
        return ok
    monkeypatch.setattr(store, "password_matches", racing)
    msg = err(store.change_web_password, w.ip.tokens, "ann", PASSWORD, NEW)
    assert msg == "the password was changed meanwhile, log in again (密碼剛被改過，請重新登入)" and "changed meanwhile" in msg
    monkeypatch.setattr(store, "password_matches", real)
    assert store.check_web_password(w.ip.tokens, "ann", other)["name"] == "ann"
    assert store.check_web_password(w.ip.tokens, "ann", NEW) is None


def test_tc047_an_ordinary_user_may_change_too(w):
    # TC-047
    w.user("bob")
    st().change_web_password(w.ip.tokens, "bob", PASSWORD, NEW)
    assert temp_until(w, "bob") is None
    assert st().check_web_password(w.ip.tokens, "bob", NEW)["must_change"] is False


def test_tc048_every_error_is_one_bilingual_line_without_the_passwords(w, monkeypatch):
    # TC-048
    w.user("ann")
    store = st()
    old, secret_new = "oldpassword-A1", "newpassword-B2"
    store.set_web_password(w.ip.tokens, "ann", old)
    msgs = [err(store.change_web_password, w.ip.tokens, "ann", "bad-old-pass", secret_new),
            err(store.change_web_password, w.ip.tokens, "ghost", old, secret_new),
            err(store.change_web_password, w.ip.tokens, "ann", old, "x" * 7),
            err(store.change_web_password, w.ip.tokens, "ann", old, "y" * 1001),
            err(store.change_web_password, w.ip.tokens, "ann", old, old)]
    real = store.password_matches

    def racing(stored, password):
        ok = real(stored, password)
        store.set_web_password(w.ip.tokens, "ann", "interloper-pass")
        return ok
    monkeypatch.setattr(store, "password_matches", racing)
    msgs.append(err(store.change_web_password, w.ip.tokens, "ann", old, secret_new))
    for m in msgs:
        assert "\n" not in m and re.search(r"[A-Za-z]", m) and re.search(r"[一-鿿]", m)
        for s in (old, secret_new, "bad-old-pass", "interloper-pass"):
            assert s not in m


# ---- US5: migration ------------------------------------------------------------------------------------------------

OLD_USERS = ("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, lab TEXT NOT NULL, "
             "created_at REAL NOT NULL, disabled_at REAL%s);")
SESSIONS = ("CREATE TABLE web_sessions (id_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at REAL NOT NULL, "
            "expires_at REAL NOT NULL);")


def old_db(path, with_password=False, password_hash=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.executescript(OLD_USERS % (", password_hash TEXT" if with_password else ""))
    con.executescript(SESSIONS)
    if with_password:
        con.execute("INSERT INTO users (name, lab, created_at, password_hash) VALUES ('ann', 'lab-x', 1.0, ?)", (password_hash,))
    else:
        con.execute("INSERT INTO users (name, lab, created_at) VALUES ('ann', 'lab-x', 1.0)")
    con.execute("INSERT INTO web_sessions VALUES ('h', 1, 1.0, 99.0)")
    con.commit()
    con.close()


def dump(path):
    con = sqlite3.connect(str(path))
    try:
        return {t: con.execute("SELECT * FROM %s" % t).fetchall()
                for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()}
    finally:
        con.close()


def cols(path, table="users"):
    con = sqlite3.connect(str(path))
    try:
        return con.execute("PRAGMA table_info(%s)" % table).fetchall()
    finally:
        con.close()


def test_tc049_tc050_an_old_database_gets_the_column_once(tmp_path):
    # TC-049, TC-050
    p = tmp_path / "d" / "tokens.db"
    old_db(p)
    st().connect_tokens(p).close()
    c = cols(p)
    assert c[-1][1] == "temp_until" and c[-1][2].upper() == "REAL"
    d = dump(p)
    assert d["users"] == [(1, "ann", "lab-x", 1.0, None, None, None)] and d["web_sessions"] == [("h", 1, 1.0, 99.0)]
    st().connect_tokens(p).close()
    assert dump(p) == d


def test_tc051_four_threads_upgrading_at_once_do_not_fail(tmp_path):
    # TC-051
    p = tmp_path / "d" / "tokens.db"
    old_db(p)
    barrier, errors = threading.Barrier(4), []

    def go():
        try:
            barrier.wait()
            st().connect_tokens(p).close()
        except Exception as e:      # noqa: BLE001
            errors.append(e)
    ts = [threading.Thread(target=go) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert errors == []
    assert [r[1] for r in cols(p)].count("temp_until") == 1


def test_tc052_tc053_a_database_with_only_password_hash_upgrades_to_the_same_shape(tmp_path):
    # TC-052, TC-053
    a, b = tmp_path / "a" / "tokens.db", tmp_path / "b" / "tokens.db"
    old_db(a, with_password=True)
    st().connect_tokens(a).close()
    assert cols(a)[-1][1] == "temp_until"
    b.parent.mkdir()
    st().connect_tokens(b).close()
    assert cols(a) == cols(b)


def test_tc054_the_new_column_name_passes_the_banned_word_check(tmp_path):
    # TC-054
    import test_station_envs as se
    p = tmp_path / "d" / "tokens.db"
    old_db(p)
    st().connect_tokens(p).close()
    assert se.banned_schema_words(p) == []
    assert not any("temp_until" in str(e) for e in se.EXEMPT)


def test_tc055_the_whole_flow_runs_on_an_upgraded_database(tmp_path):
    # TC-055
    store = st()
    p = tmp_path / "d" / "tokens.db"
    old_db(p)
    store.connect_tokens(p).close()
    out = store.issue_temporary_password(p, "ann", now=1000.0)
    assert store.check_web_password(p, "ann", out["password"], now=1001.0)["must_change"] is True
    store.change_web_password(p, "ann", out["password"], NEW, now=1002.0)
    assert store.check_web_password(p, "ann", NEW, now=1003.0)["must_change"] is False


def test_tc056_an_old_database_with_a_password_opens_intact(tmp_path):
    # TC-056: opened with store.connect_tokens, the platform's normal entrance
    store = st()
    p = tmp_path / "d" / "tokens.db"
    old_db(p, with_password=True, password_hash=store.hash_password(PASSWORD))
    con = store.connect_tokens(p)
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    con.close()
    assert store.check_web_password(p, "ann", PASSWORD)["must_change"] is False
    con = sqlite3.connect(str(p))
    assert con.execute("SELECT temp_until FROM users").fetchone()[0] is None
    con.close()


def test_tc057_web_sessions_columns_do_not_change(tmp_path):
    # TC-057
    p = tmp_path / "d" / "tokens.db"
    old_db(p)
    before = cols(p, "web_sessions")
    st().connect_tokens(p).close()
    assert cols(p, "web_sessions") == before
    assert [r[1] for r in before] == ["id_hash", "user_id", "created_at", "expires_at"]


# ---- US6: the terminal command ----------------------------------------------------------------------------------

def test_tc058_to_tc062_tc068_to_tc071_the_command_shows_the_password_once(w):
    # TC-058, TC-059, TC-060, TC-061, TC-062, TC-068, TC-069, TC-070, TC-071
    w.user("ann", password=None)
    rc, screen, lines = temp_by_terminal(w)
    assert rc == 0, screen
    assert len(lines) == 4, lines
    pw = lines[1]
    assert CHARSET.fullmatch(pw)
    assert screen.count(pw) == 1
    assert lines[0] == "temporary web password of ann (一次性臨時密碼，只顯示這一次):"
    assert "Send it to ann privately" in lines[2] and "72 hours" in lines[2] and "must change it at the first login" in lines[2]
    assert "Shown once and kept nowhere" in lines[3] and "弄丟就重新執行這個指令" in lines[3]
    assert "New web password" not in screen and "Type it again" not in screen
    assert all(pw not in x for x in (lines[0], lines[2], lines[3]))
    r = w.login(w.web(), "ann", pw)
    assert r.status_code == 303
    assert st().check_web_password(w.ip.tokens, "ann", pw)["must_change"] is True
    assert abs(temp_until(w, "ann") - (time.time() + 259200)) < 120
    # TC-069: on the terminal stdout and stderr are one screen; the run without a terminal below keeps them apart
    for (table,) in q(w, "SELECT name FROM sqlite_master WHERE type='table'"):          # TC-070
        for row in q(w, "SELECT * FROM %s" % table):
            for cell in row:
                assert not (isinstance(cell, str) and pw in cell)
    for f in Path(w.tmp).rglob("*"):                                                         # TC-071
        if f.is_file():
            assert pw.encode() not in f.read_bytes(), f


def test_tc063_tc064_tc065_without_a_terminal_nothing_is_issued_or_shown(w):
    # TC-063, TC-064, TC-065
    w.user("ann", password=None)
    before = user_state(w)
    for name in ("ann", "ghost"):
        r = subprocess.run([sys.executable, "-m", "abf_platform", "user", "passwd", name, "--temporary"], input="\n", text=True,
                           capture_output=True, env=w.data.env(), timeout=60)
        out = r.stdout + r.stderr
        assert r.returncode != 0 and "rejected:" in out and "終端機" in out
        assert "temporary web password of" not in out and "Shown once" not in out
        assert "沒有這個使用者" not in out
        assert user_state(w) == before and temp_until(w, "ann") is None


def test_tc066_tc067_an_unknown_user_at_a_terminal(w):
    # TC-066, TC-067
    rc, screen, lines = temp_by_terminal(w, "ghost")
    assert rc != 0 and "沒有這個使用者" in screen and "abf-platform user add" in screen
    assert not re.search(r"(?m)^[A-Za-z0-9_-]{16}\s*$", screen)
    assert q(w, "SELECT COUNT(*) FROM users")[0][0] == 0


@pytest.mark.parametrize("extra", [["--password", "x"], ["x"]])
def test_tc072_tc073_no_flag_and_no_word_gives_the_password(w, extra):
    # TC-072, TC-073
    w.user("ann", password=None)
    r = subprocess.run([sys.executable, "-m", "abf_platform", "user", "passwd", "ann", "--temporary"] + extra, capture_output=True,
                       text=True, env=w.data.env(), timeout=60)
    assert r.returncode != 0
    assert hash_of(w, "ann") is None and temp_until(w, "ann") is None


def test_tc074_an_abbreviated_flag_is_refused(w):
    # TC-074
    w.user("ann", password=None)
    r = subprocess.run([sys.executable, "-m", "abf_platform", "user", "passwd", "ann", "--temp"], capture_output=True, text=True,
                       env=w.data.env(), timeout=60)
    assert r.returncode != 0
    assert hash_of(w, "ann") is None


def test_tc075_the_environment_cannot_give_the_password(w):
    # TC-075
    w.user("ann", password=None)
    v = "ENVVALUE-abcdef"
    rc, screen, lines = temp_by_terminal(w, "ann", w.data.env(ABF_WEB_PASSWORD=v, ABF_PLATFORM_WEB_PASSWORD=v))
    assert rc == 0 and CHARSET.fullmatch(lines[1]) and lines[1] != v and v not in screen


def test_tc076_without_the_flag_it_still_asks_twice(w):
    # TC-076
    w.user("ann", password=None)
    p = Pty(cli_argv("user", "passwd", "ann"), w.data.env())
    assert p.wait_for("New web password for ann:", 30), p.text()
    p.send(NEW + "\n")
    assert p.wait_for("Type it again:", 30), p.text()
    p.send(NEW + "\n")
    rc, screen = p.finish(30)
    assert rc == 0 and st().check_web_password(w.ip.tokens, "ann", NEW)["must_change"] is False


def test_tc077_a_terminal_password_over_a_temporary_one_clears_it(w):
    # TC-077
    w.user("ann")
    issue(w)
    p = Pty(cli_argv("user", "passwd", "ann"), w.data.env())
    assert p.wait_for("New web password", 30)
    p.send(NEW + "\n")
    assert p.wait_for("again", 30)
    p.send(NEW + "\n")
    assert p.finish(30)[0] == 0
    assert temp_until(w, "ann") is None and st().check_web_password(w.ip.tokens, "ann", NEW)["must_change"] is False


def test_tc078_the_help_names_the_flag(w):
    # TC-078
    r = subprocess.run([sys.executable, "-m", "abf_platform", "user", "passwd", "--help"], capture_output=True, text=True,
                       env=w.data.env(), timeout=60)
    assert r.returncode == 0 and "--temporary" in r.stdout


# ---- US8: not done ---------------------------------------------------------------------------------------------

def test_tc099_nothing_returns_an_existing_temporary_password(w):
    # TC-099
    w.user("ann", password=None)
    a = temp_by_terminal(w)[2][1]
    b = temp_by_terminal(w)[2][1]
    assert a != b
    assert st().check_web_password(w.ip.tokens, "ann", a) is None
    assert st().check_web_password(w.ip.tokens, "ann", b)["must_change"] is True
    names = re.findall(r"(?m)^def (\w+)", STORE_SRC)
    assert [n for n in names if "temp" in n.lower()] == ["issue_temporary_password"]


def test_tc100_no_mail_and_no_other_program_in_the_new_code():
    # TC-100
    for src in (CLI_SRC, STORE_SRC):
        assert not re.search(r"(?m)^\s*(import|from)\s+(smtplib|email|subprocess)\b", src)
    body = STORE_SRC[STORE_SRC.index("def issue_temporary_password"):]
    body = body[:body.index("\ndef ", 10)]
    assert "random" not in body.replace("secrets", "") and "logging" not in body and "print(" not in body


def test_tc101_no_forgot_or_reset_entrance():
    # TC-101
    assert not re.search(r'add_parser\("(forgot|reset)', CLI_SRC)
    assert not re.search(r"forgot|reset_password", (REPO_ROOT / "platform" / "abf_platform" / "web.py").read_text(encoding="utf-8"))


def test_tc103_the_length_rules_and_the_hash_are_unchanged():
    # TC-103
    store = st()
    assert store.MIN_PASSWORD_CHARS == 8 and store.MAX_PASSWORD_CHARS == 1000
    assert store.hash_password("some password").startswith("scrypt$")
    assert store.password_matches(store.hash_password("some password"), "some password")


# ---- docstrings ---------------------------------------------------------------------------------------------------

def test_tc094_tc095_the_docstrings_name_the_flag():
    # TC-094, TC-095
    assert "user add|cloud-cap|passwd [--temporary]" in CLI_SRC.splitlines()[1]
    body = CLI_SRC[CLI_SRC.index("def cmd_user_passwd"):]
    body = body[:body.index("\ndef ", 10)]
    assert "no flag can type the person's own password" in body and "`--temporary` makes a one-time one" in body


# ---- the constitution and the safety net ----------------------------------------------------------------------

def test_tc110_tc111_no_password_in_a_log_or_an_exception(w, caplog):
    # TC-110, TC-111
    w.user("ann")
    caplog.set_level(logging.DEBUG)
    store = st()
    out = issue(w)
    pw = out["password"]
    msgs = [err(store.issue_temporary_password, w.ip.tokens, "ghost")]
    store.check_web_password(w.ip.tokens, "ann", pw, now=1001.0)
    msgs.append(err(store.change_web_password, w.ip.tokens, "ann", "wrongwrong1", NEW, now=1001.0))
    msgs.append(err(store.change_web_password, w.ip.tokens, "ann", pw, "short", now=1001.0))
    store.change_web_password(w.ip.tokens, "ann", pw, NEW, now=1001.0)
    text = caplog.text + "\n".join(msgs)
    for s in (pw, NEW, "wrongwrong1"):
        assert s not in text
