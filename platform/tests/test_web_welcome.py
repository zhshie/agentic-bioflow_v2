# Nothing existing: /welcome (the page where a temporary-password login sets its own password) is new in this task; the store side is test_temp_password.py.
"""web-change-password: the temporary-password session reaches only /welcome, and /welcome changes the password.
Test case IDs (TC-nnn of the web-change-password contract) are named in the comments. The manual cases (TC-040, 066, 067, 073-076,
085-087) are read from the diff, TESTING.md and the screenshots."""
import logging
import re
import sqlite3
from pathlib import Path

import pytest

from helpers import REPO_ROOT
from human_harness import PASSWORD, World, csrf_of

NEW = "brand-new-pass-ZQ1"
CONF = "confirm-copy-pass-ZQ2"
OLDV = "wrong-old-pass-ZQ3"
WELCOME_TITLE = "設定你自己的密碼 (set your own password)"
ZH = "你用的是管理者給的臨時密碼，它 72 小時內有效、只能用來設定你自己的密碼。設好之後就用新密碼登入。"
EN = ("You are using a one-time temporary password from your administrator. It works for 72 hours and only lets you set your own "
      "password. After that, log in with your new password.")
TOO_MANY = "登入失敗太頻繁，請一分鐘後再試 (too many tries, wait a minute)"
WEB_SRC = (REPO_ROOT / "platform" / "abf_platform" / "web.py").read_text(encoding="utf-8")
HDR = {"origin": "http://testserver"}


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def st():
    from abf_platform import store
    return store


def issue(w, name="ann"):
    return st().issue_temporary_password(w.ip.tokens, name, now=w.clock.t)["password"]


def temp_login(w, name="ann", client=None, extra=None):
    """(client, temporary password, login response): a browser that logged in with a fresh temporary password."""
    t = issue(w, name)
    c = client or w.web()
    data = {"name": name, "password": t}
    data.update(extra or {})
    return c, t, c.post("/login", data=data)


def sid_of(c):
    return c.cookies.get("abf_web").split(".")[0]


def token(w, c, purpose):
    from abf_platform import web
    key = web._signing_key(Path(w.ip.state_db).parent)
    return web._mac(key, "csrf", sid_of(c), purpose)


def send(w, c, old, new=NEW, confirm=None, csrf=None, headers=None, **extra):
    data = {"old": old, "new": new, "confirm": new if confirm is None else confirm,
            "csrf": token(w, c, "welcome") if csrf is None else csrf}
    data.update(extra)
    return c.post("/welcome", data=data, headers=headers or HDR)


def login_status(w, name, password):
    return w.login(w.web(), name, password).status_code


def pw_hash(w, name):
    con = sqlite3.connect(str(w.ip.tokens))
    try:
        return con.execute("SELECT password_hash FROM users WHERE name = ?", (name,)).fetchone()[0]
    finally:
        con.close()


# ---- US1 --------------------------------------------------------------------------------------------------------------

def test_tc001_tc002_tc003_a_temporary_login_goes_to_welcome_whatever_next_says(w):
    # TC-001, TC-002, TC-003
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c, t, r = temp_login(w)
    assert r.status_code == 303 and r.headers["location"] == "/welcome"
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/" in cookie
    for nxt in ("/usage", "/c/" + rid):
        c2, _, r2 = temp_login(w, extra={"next": nxt})
        assert r2.status_code == 303 and r2.headers["location"] == "/welcome", nxt


def test_tc004_an_ordinary_login_keeps_next(w):
    # TC-004
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    r = w.web().post("/login", data={"name": "ann", "password": PASSWORD, "next": "/c/" + rid})
    assert r.status_code == 303 and r.headers["location"] == "/c/" + rid
    r = w.web().post("/login", data={"name": "ann", "password": PASSWORD})
    assert r.status_code == 303 and r.headers["location"] == "/"


# ---- US2 --------------------------------------------------------------------------------------------------------------

def test_tc005_to_tc010_a_temporary_session_is_sent_to_welcome_everywhere(w):
    # TC-005, TC-006, TC-007, TC-008, TC-009, TC-010
    ann = w.user("ann")
    rid = w.launch(caller=ann, run="very-special-run-name")["id"]
    c, t, r = temp_login(w)
    for path in ("/", "/settings", "/usage", "/launch"):
        a = c.get(path)
        assert (a.status_code, a.headers["location"]) == (303, "/welcome"), path
        assert "very-special-run-name" not in a.text
    a = c.post("/launch", data={"csrf": "x"}, headers=HDR)
    assert (a.status_code, a.headers["location"]) == (303, "/welcome")
    for verb in ("resume", "relaunch", "cancel"):
        a = c.post("/act/" + verb, data={"csrf": "x", "run": "very-special-run-name"}, headers=HDR)
        assert (a.status_code, a.headers["location"]) == (303, "/welcome"), verb
    a = c.get("/c/" + rid)
    assert (a.status_code, a.headers["location"]) == (303, "/welcome") and "very-special-run-name" not in a.text
    a = c.post("/c/" + rid, data={"csrf": token(w, c, rid)}, headers=HDR)
    assert (a.status_code, a.headers["location"]) == (303, "/welcome")
    assert w.jobs() == []
    assert w.sql("SELECT state FROM confirmations")[0]["state"] == "pending"


def test_tc011_a_temporary_session_cannot_decide_a_consent_request(w):
    # TC-011
    from oauth_harness import Rig, tokens_rows
    w.user("ann")
    rig = Rig(w)
    path, _, _ = rig.start()
    t = issue(w)
    assert rig.c.post("/login", data={"name": "ann", "password": t}).status_code == 303
    a = rig.c.get(path)
    assert (a.status_code, a.headers["location"]) == (303, "/welcome")
    a = rig.c.post(path, data={"decision": "allow", "csrf": "x"}, headers=HDR)
    assert (a.status_code, a.headers["location"]) == (303, "/welcome")
    assert tokens_rows(w, "SELECT decision FROM oauth_requests")[0]["decision"] is None
    assert tokens_rows(w, "SELECT COUNT(*) AS n FROM oauth_codes")[0]["n"] == 0


def test_tc013_no_cookie_goes_to_login_as_before(w):
    # TC-013
    w.user("ann")
    c = w.web()
    for path in ("/", "/settings", "/usage", "/launch"):
        a = c.get(path)
        assert (a.status_code, a.headers["location"]) == (303, "/login"), path
    for path in ("/launch", "/act/resume"):
        a = c.post(path, data={"csrf": "x"}, headers=HDR)
        assert (a.status_code, a.headers["location"]) == (303, "/login"), path


def test_tc014_no_cookie_on_confirm_and_consent_pages_is_as_before(w):
    # TC-014
    from oauth_harness import Rig
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    rig = Rig(w)
    path, _, _ = rig.start()
    anon = rig.another()
    a = anon.get("/c/" + rid)
    assert a.status_code == 200 and 'name="password"' in a.text
    a = anon.post("/c/" + rid, data={"csrf": "x"}, headers=HDR)
    assert a.status_code == 401 and 'name="password"' in a.text
    a = anon.get(path)
    assert a.status_code == 200 and 'name="password"' in a.text
    a = anon.post(path, data={"decision": "allow", "csrf": "x"}, headers=HDR)
    assert a.status_code == 401 and 'name="password"' in a.text


def test_tc015_tc016_an_expired_or_forged_cookie_goes_to_login(w):
    # TC-015, TC-016
    w.user("ann")
    c, t, r = temp_login(w)
    assert c.get("/").headers["location"] == "/welcome"
    w.clock.t += 72 * 3600 + 5
    a = c.get("/")
    assert (a.status_code, a.headers["location"]) == (303, "/login")
    forged = w.web()
    forged.cookies.set("abf_web", "forged.signature")
    a = forged.get("/")
    assert (a.status_code, a.headers["location"]) == (303, "/login")


def test_tc017_an_ordinary_session_still_sees_the_board(w):
    # TC-017
    ann = w.user("ann")
    w.launch(caller=ann, run="very-special-run-name")
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    assert c.get("/").status_code == 200


def test_tc019_authorize_answers_a_temporary_session_like_nobody(w):
    # TC-019
    from oauth_harness import Rig, pkce
    w.user("ann")
    rig = Rig(w)
    cid = rig.new_client()
    _, challenge = pkce()
    params = {"client_id": cid, "redirect_uri": "https://claude.example/cb", "response_type": "code", "code_challenge": challenge,
              "code_challenge_method": "S256", "state": "s"}
    t = issue(w)
    assert rig.c.post("/login", data={"name": "ann", "password": t}).status_code == 303
    anon = rig.another()

    def shown(r):
        return r.status_code, re.sub(r"/consent/[0-9a-f]{32}", "/consent/X", r.headers.get("location", ""))
    assert shown(rig.c.get("/authorize", params=params)) == shown(anon.get("/authorize", params=params))
    a = rig.c.post("/authorize", data=params, headers=HDR)
    b = anon.post("/authorize", data=params, headers=HDR)
    assert shown(a) == shown(b)


# ---- US3 --------------------------------------------------------------------------------------------------------------

def test_tc021_to_tc026_tc028_tc068_tc069_tc070_tc072_the_page(w):
    # TC-021 .. TC-026, TC-028, TC-068 (initial page), TC-069, TC-070, TC-072
    ann = w.user("ann")
    w.launch(caller=ann, run="very-special-run-name")
    c, t, r = temp_login(w)
    a = c.get("/welcome")
    assert a.status_code == 200
    text = a.text
    assert WELCOME_TITLE in text
    assert ZH in text and EN in text
    fields = re.findall(r"<input[^>]*type=\"password\"[^>]*>", text)
    assert len(fields) == 3
    by_name = {re.search(r'name="(\w+)"', f).group(1): f for f in fields}
    assert set(by_name) == {"old", "new", "confirm"}
    assert 'autocomplete="current-password"' in by_name["old"]
    assert 'autocomplete="new-password"' in by_name["new"] and 'autocomplete="new-password"' in by_name["confirm"]
    for lab in ("目前的臨時密碼", "新密碼", "再輸入一次新密碼"):
        assert lab in text
    m, mx = st().MIN_PASSWORD_CHARS, st().MAX_PASSWORD_CHARS
    assert "（%d 到 %d 個字元 / %d to %d characters）" % (m, mx, m, mx) in text
    assert csrf_of(text) == token(w, c, "welcome")
    assert len(re.findall(r"<button", text)) == 2 and "設定密碼 (set password)" in text
    assert 'action="/logout"' in text and ('name="csrf" value="%s"' % token(w, c, "logout")) in text
    body = re.sub(r"<style>.*?</style>", "", text, flags=re.S)
    for word in ("very-special-run-name", "must_change", "temp_until", "ValueError", "Traceback"):
        assert word not in body, word
    assert "<script" not in text and "style=" not in text and not re.search(r"<[^>]* on\w+=", text)
    assert text.count("<style>") == 1 and not re.search(r"(src|href)=\"https?:", text)
    login = w.web().get("/login")
    h = a.headers
    assert h["cache-control"] == "no-store" and h["x-frame-options"] == "DENY"
    assert h["content-security-policy"] == login.headers["content-security-policy"]

    def frame(s):
        return re.search(r"<style>.*?</style>", s, re.S).group(0), s.split("<main")[0].split("<title>")[0], s.count("<main class=\"narrow\">")
    assert frame(text)[0] == frame(login.text)[0] and frame(text)[1:] == frame(login.text)[1:]


def test_tc027_the_logout_form_works_on_welcome(w):
    # TC-027
    w.user("ann")
    c, t, r = temp_login(w)
    a = c.post("/logout", data={"csrf": token(w, c, "logout")}, headers=HDR)
    assert (a.status_code, a.headers["location"]) == (303, "/login")
    assert "abf_web" in a.headers["set-cookie"]
    c.cookies.clear()
    b = c.get("/welcome")
    assert (b.status_code, b.headers["location"]) == (303, "/login")


def test_tc029_tc030_tc031_other_sessions_on_get(w):
    # TC-029, TC-030, TC-031
    w.user("ann")
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    a = c.get("/welcome")
    assert (a.status_code, a.headers["location"]) == (303, "/")
    a = w.web().get("/welcome")
    assert (a.status_code, a.headers["location"]) == (303, "/login")
    c2, _, _ = temp_login(w)
    w.clock.t += 72 * 3600 + 5
    a = c2.get("/welcome")
    assert (a.status_code, a.headers["location"]) == (303, "/login")


def test_tc032_tc033_tc082_post_without_a_temporary_session(w):
    # TC-032, TC-033, TC-082
    w.user("ann")
    a = w.web().post("/welcome", data={"old": "x", "new": NEW, "confirm": NEW, "csrf": "x"}, headers=HDR)
    assert (a.status_code, a.headers["location"]) == (303, "/login")
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    before = pw_hash(w, "ann")
    a = send(w, c, PASSWORD)
    assert (a.status_code, a.headers["location"]) == (303, "/")
    assert pw_hash(w, "ann") == before and login_status(w, "ann", PASSWORD) == 303


# ---- US4 --------------------------------------------------------------------------------------------------------------

def test_tc034_to_tc037_a_good_change_keeps_the_same_login(w):
    # TC-034, TC-035, TC-036, TC-037
    ann = w.user("ann")
    w.launch(caller=ann, run="very-special-run-name")
    c, t, r = temp_login(w)
    a = send(w, c, t)
    assert (a.status_code, a.headers["location"]) == (303, "/")
    assert "set-cookie" not in a.headers
    b = c.get("/")
    assert b.status_code == 200 and "very-special-run-name" in b.text
    assert login_status(w, "ann", t) == 401
    r = w.login(w.web(), "ann", NEW)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert st().check_web_password(w.ip.tokens, "ann", NEW, now=w.clock.t)["must_change"] is False
    d = c.get("/welcome")
    assert (d.status_code, d.headers["location"]) == (303, "/")


def test_tc038_the_good_change_is_not_counted_as_a_failure(w):
    # TC-038
    w.user("ann")
    c0 = w.web()
    for _ in range(4):
        assert w.login(c0, "ann", "nope nope nope").status_code == 401
    c, t, r = temp_login(w)
    assert send(w, c, t).status_code == 303
    c.post("/logout", data={"csrf": token(w, c, "logout")}, headers=HDR)
    assert w.login(w.web(), "ann", "nope nope nope").status_code == 401


def test_tc039_the_whole_story(w):
    # TC-039
    ann = w.user("ann", password=None)
    w.launch(caller=ann, run="very-special-run-name")
    c, t, r = temp_login(w)
    assert r.headers["location"] == "/welcome"
    assert send(w, c, t).status_code == 303
    assert "very-special-run-name" in c.get("/").text
    c.post("/logout", data={"csrf": token(w, c, "logout")}, headers=HDR)
    assert login_status(w, "ann", NEW) == 303
    assert login_status(w, "ann", t) == 401


# ---- US5 --------------------------------------------------------------------------------------------------------------

def spy(monkeypatch):
    from abf_platform import store
    calls = []
    real = store.change_web_password

    def wrapper(*a, **k):
        calls.append(a)
        return real(*a, **k)
    monkeypatch.setattr(store, "change_web_password", wrapper)
    return calls


def five_free_then_wrong(w, c, make):
    """`make()` five times must not count; then a wrong `old` must still be 401 (not 429)."""
    for _ in range(5):
        make()
    assert send(w, c, OLDV).status_code == 401


def test_tc041_tc042_the_two_new_passwords_differ(w, monkeypatch):
    # TC-041, TC-042
    w.user("ann")
    c, t, _ = temp_login(w)
    calls = spy(monkeypatch)
    a = send(w, c, t, confirm=NEW + "x")
    assert a.status_code == 400 and "兩次輸入的新密碼不一樣 (the two new passwords differ)" in a.text
    assert calls == [] and login_status(w, "ann", t) == 303
    five_free_then_wrong(w, c, lambda: send(w, c, t, confirm=NEW + "x"))


def test_tc043_tc044_a_wrong_current_password(w):
    # TC-043, TC-044
    w.user("ann")
    c, t, _ = temp_login(w)
    a = send(w, c, OLDV)
    assert a.status_code == 401 and "目前的密碼不對" in a.text and login_status(w, "ann", t) == 303
    for _ in range(4):
        assert send(w, c, OLDV).status_code == 401
    assert send(w, c, OLDV).status_code == 429


def test_tc045_tc046_tc047_the_store_refuses_without_counting(w):
    # TC-045, TC-046, TC-047
    w.user("ann")
    c, t, _ = temp_login(w)
    a = send(w, c, t, new=t)
    assert a.status_code == 400 and "新密碼不能跟目前的一樣" in a.text
    five_free_then_wrong(w, c, lambda: send(w, c, t, new=t))
    a = send(w, c, t, new="x" * 7)
    assert a.status_code == 400 and "密碼至少 8 個字元" in a.text
    a = send(w, c, t, new="y" * 1001)
    assert a.status_code == 400 and "密碼最多 1000 個字元" in a.text
    assert login_status(w, "ann", t) == 303
    five_free_then_wrong(w, c, lambda: send(w, c, t, new="x" * 7))


def test_tc048_a_password_changed_meanwhile_is_not_counted(w, monkeypatch):
    # TC-048
    from abf_platform import store
    w.user("ann")
    c, t, _ = temp_login(w)
    msg = "the password was changed meanwhile, log in again (密碼剛被改過，請重新登入)"

    def boom(*a, **k):
        raise ValueError(msg)
    with monkeypatch.context() as m:
        m.setattr(store, "change_web_password", boom)
        a = send(w, c, t)
        assert a.status_code == 400 and "密碼剛被改過，請重新登入" in a.text
        for _ in range(4):
            send(w, c, t)
    assert send(w, c, OLDV).status_code == 401


def test_tc049_a_too_long_current_password_is_counted_and_not_sent_to_the_store(w, monkeypatch):
    # TC-049
    w.user("ann")
    c, t, _ = temp_login(w)
    calls = spy(monkeypatch)
    a = send(w, c, "z" * 1001)
    assert a.status_code == 400 and "密碼最長 1000 個字元" in a.text and calls == []
    for _ in range(4):
        assert send(w, c, "z" * 1001).status_code == 400
    assert send(w, c, OLDV).status_code == 429


def test_tc050_tc051_tc052_a_bad_csrf(w):
    # TC-050, TC-051, TC-052
    w.user("ann")
    c, t, _ = temp_login(w)
    assert send(w, c, t, csrf="nope").status_code == 403
    assert login_status(w, "ann", t) == 303
    five_free_then_wrong(w, c, lambda: send(w, c, t, csrf="nope"))
    a = c.post("/welcome", data={"old": t, "new": NEW, "confirm": NEW}, headers=HDR)
    assert a.status_code == 403 and login_status(w, "ann", t) == 303


def test_tc053_a_foreign_origin(w):
    # TC-053
    w.user("ann")
    c, t, _ = temp_login(w)
    a = send(w, c, t, headers={"origin": "http://evil.example"})
    assert a.status_code == 403 and "來源不符 (wrong origin)" in a.text
    assert login_status(w, "ann", t) == 303


def test_tc054_tc055_tc057_the_limit_is_shared_with_the_login_page(w):
    # TC-054, TC-055, TC-057
    w.user("ann")
    c, t, _ = temp_login(w)
    for _ in range(5):
        assert send(w, c, OLDV).status_code == 401
    a = send(w, c, t)
    assert a.status_code == 429 and TOO_MANY in a.text and 'name="old"' in a.text and login_status(w, "ann", t) == 429
    w.clock.t += 61
    assert send(w, c, t).status_code == 303
    w.user("bob")
    c0 = w.web()
    for _ in range(4):
        assert w.login(c0, "bob", "nope nope nope").status_code == 401
    cb, tb, _ = temp_login(w, "bob")
    assert send(w, cb, OLDV).status_code == 401
    assert send(w, cb, OLDV).status_code == 429


def test_tc056_the_address_limit_is_shared(w):
    # TC-056
    w.user("ann")
    c, t, _ = temp_login(w)
    for i in range(20):
        assert w.login(w.web(), "who%d" % i, "nope nope nope").status_code == 401
    a = send(w, c, t)
    assert a.status_code == 429 and login_status(w, "ann", t) == 429


def test_tc058_tc059_tc060_the_order_of_the_checks(w):
    # TC-058, TC-059, TC-060
    w.user("ann")
    c, t, _ = temp_login(w)
    for _ in range(5):
        send(w, c, OLDV)
    assert send(w, c, t, csrf="nope").status_code == 403
    assert send(w, c, t, confirm=NEW + "x").status_code == 429
    a = send(w, c, t, headers={"origin": "http://evil.example"})
    assert a.status_code == 403 and "來源不符 (wrong origin)" in a.text


def test_tc061_only_the_session_owner_is_ever_changed(w):
    # TC-061
    w.user("ann")
    w.user("bob", password="bobs own password")
    c, t, _ = temp_login(w)
    bob_before, ann_before = pw_hash(w, "bob"), pw_hash(w, "ann")
    a = send(w, c, "bobs own password", name="bob")
    assert a.status_code == 401
    assert pw_hash(w, "bob") == bob_before and pw_hash(w, "ann") == ann_before


def test_tc062_tc063_tc071_nothing_comes_back_and_the_errors_are_plain(w, caplog):
    # TC-062, TC-063, TC-071
    caplog.set_level(logging.DEBUG)
    w.user("ann")
    c, t, login = temp_login(w)
    pages = {}
    pages["differ"] = send(w, c, t, new=NEW, confirm=CONF)
    pages["wrong"] = send(w, c, OLDV)
    pages["same"] = send(w, c, t, new=t, confirm=t)
    pages["shrt7ch"] = send(w, c, t, new="shrt7ch", confirm="shrt7ch")
    pages["long"] = send(w, c, "q" * 1001)
    pages["csrf"] = send(w, c, t, csrf="nope")
    pages["origin"] = send(w, c, t, headers={"origin": "http://evil.example"})
    seen = [login] + list(pages.values())
    for key in ("differ", "wrong", "same", "shrt7ch", "long"):
        text = pages[key].text
        assert not re.search(r'type="password"[^>]*value=', text) and not re.search(r'value="[^"]*"[^>]*type="password"', text), key
        assert text.count('<p class="bad">') == 1 and "<script" not in text and "style=" not in text
        assert pages[key].headers["cache-control"] == "no-store" and "content-security-policy" in pages[key].headers
    for _ in range(6):
        seen.append(send(w, c, OLDV))
    w.clock.t += 61
    seen.append(send(w, c, t, new=NEW, confirm=NEW))
    assert seen[-1].status_code == 303
    secrets = (NEW, CONF, OLDV, "q" * 1001, "shrt7ch")
    for r in seen:
        blob = r.text + r.headers.get("location", "") + r.headers.get("set-cookie", "")
        for s in secrets:
            assert s not in blob
    for s in secrets:
        assert s not in caplog.text


def test_tc071_tc072_the_429_page_is_one_plain_sentence(w):
    # TC-071, TC-072
    w.user("ann")
    c, t, _ = temp_login(w)
    for _ in range(5):
        send(w, c, OLDV)
    a = send(w, c, t)
    assert a.status_code == 429 and '<p class="bad">' + TOO_MANY in a.text
    for word in ("must_change", "temp_until", "ValueError", "Traceback"):
        assert word not in a.text


# ---- US6 --------------------------------------------------------------------------------------------------------------

def test_tc064_tc065_the_login_page_sentence(w):
    # TC-064, TC-065
    text = w.web().get("/login").text
    assert ("請用你的姓名與<strong>網頁密碼</strong>登入（網頁密碼不是 AI 用的權杖；它在平台主機的終端機用 <code>abf-platform user passwd</code> "
            "設定，或用管理者給你的一次性臨時密碼）。") in text
    assert "它只能在終端機用" not in text


# ---- safety net -------------------------------------------------------------------------------------------------------

def test_tc077_a_bearer_token_never_reaches_welcome(w):
    # TC-077
    w.user("ann")
    c, t, _ = temp_login(w)
    anon = w.web()
    hdr = dict(HDR, authorization="Bearer abf_pat_whatever")
    a = anon.get("/welcome", headers=hdr)
    assert (a.status_code, a.headers["location"]) == (303, "/login")
    a = anon.post("/welcome", data={"old": t, "new": NEW, "confirm": NEW, "csrf": "x"}, headers=hdr)
    assert (a.status_code, a.headers["location"]) == (303, "/login")
    assert login_status(w, "ann", t) == 303


def test_tc081_the_settings_page_has_no_way_in(w):
    # TC-081
    w.user("ann")
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    page = c.get("/settings").text
    assert "/welcome" not in page and "改密碼" not in page and 'type="password"' not in page


def test_tc083_there_is_no_forgot_password_door(w):
    # TC-083
    c = w.web()
    for path in ("/forgot", "/reset", "/password", "/passwd", "/account"):
        assert c.get(path).status_code == 404, path
        assert c.post(path, data={"x": "y"}).status_code in (404, 405), path
    page = c.get("/login").text
    assert "忘記密碼" not in page and "寄信" not in page
    w.user("ann")
    c2, _, _ = temp_login(w)
    page = c2.get("/welcome").text
    assert "忘記密碼" not in page and "寄信" not in page
