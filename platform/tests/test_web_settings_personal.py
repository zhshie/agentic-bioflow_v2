# Nothing existing: tests of the personal section and the development-mode banner (specs/012a-settings-page); the page and its limits are ours.
"""012a-settings-page: step-by-step and development mode flags, the banner, and the credentials "set / not set" line. Test cases are named in the comments."""
import base64
import hashlib
import re
import sqlite3

import pytest

from human_harness import World
from test_web_board import login, pane, seed
from test_web_settings import CJK, pat

BANNER_ZH = "開發模式已開啟：國網運算不限制 SU"
BANNER_EN = "Development mode is on: NCHC compute has no SU limit"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def mid_of(c, path="/settings"):
    r = c.get(path)
    assert r.status_code == 200
    return r.text, pane(r.text, "middle")


def section(mid, head):
    return re.search(r"<h2>%s</h2>(.*?)</section>" % re.escape(head), mid, re.S).group(1)


def personal(mid, head="個人"):
    return section(mid, head)


def row(mid, label, head="個人"):
    """The <li> of one switch row."""
    for li in re.findall(r"<li[^>]*>(.*?)</li>", personal(mid, head), re.S):
        if label in li:
            return li
    raise AssertionError("no row %s in %s" % (label, personal(mid, head)))


def token(c, key, lang=None):
    """The csrf token of the form of one switch, read from the page the way a browser would."""
    text, mid = mid_of(c, "/settings" + ("?lang=en" if lang == "en" else ""))
    forms = re.findall(r'<form[^>]*action="/settings/personal"[^>]*>(.*?)</form>', mid, re.S)
    for f in forms:
        if 'name="key" value="%s"' % key in f:
            return re.search(r'name="csrf" value="([^"]+)"', f).group(1)
    raise AssertionError("no form for %s" % key)


def post(c, key, on, csrf=None, **extra):
    data = {"csrf": token(c, "dev_mode") if csrf is None else csrf, "key": key, "on": on, "lang": "zh"}
    data.update(extra)
    return c.post("/settings/personal", data=data)


def prefs(w, name):
    con = sqlite3.connect(str(w.ip.tokens))
    try:
        r = con.execute("SELECT step_mode, dev_mode FROM users WHERE name = ?", (name,)).fetchone()
    finally:
        con.close()
    return r


def two_users(w):
    return w.user("ann"), w.user("bob")


# ---- US1 ---------------------------------------------------------------------------------------------------------------------------

def test_personal_section_has_two_switches(w):
    # TC-001, TC-042: two rows, a button each, no grey "coming later" in the section; seven headings in order
    w.user("ann")
    c = login(w, "ann")
    text, mid = mid_of(c)
    sec = personal(mid)
    assert "逐步模式" in sec and "開發模式" in sec and "之後開放" not in sec and sec.count("<button") == 2
    assert re.findall(r"<h2>(.*?)</h2>", mid) == ["使用前檢查", "運算環境", "憑證", "密碼與金鑰", "個人", "營運者後台", "角色（老師／學生）"]


def test_defaults_step_on_dev_off(w):
    # TC-002, TC-003: a new person has step-by-step on and development off
    w.user("ann")
    _, mid = mid_of(login(w, "ann"))
    step, dev = row(mid, "逐步模式"), row(mid, "開發模式")
    assert "✓" in step and "開" in step and "關閉" in step
    assert "—" in dev and "關" in dev and "開啟" in dev and "✓" not in dev


def test_turn_dev_on_persists_and_shows_banner(w):
    # TC-004, TC-005, TC-006, TC-013, TC-014, TC-015
    ann = w.user("ann")
    seed(w, "r1", owner=ann)
    c = login(w, "ann")
    r = post(c, "dev_mode", "1")
    assert r.status_code in (302, 303) and r.headers["location"].startswith("/settings?notice=personal-saved")
    text, mid = mid_of(c, r.headers["location"])
    assert "已儲存。" in text
    dev = row(mid, "開發模式")
    assert "✓" in dev and "關閉" in dev
    for path in ("/", "/settings", "/?run=id-r1"):
        t = c.get(path).text
        assert BANNER_ZH in t and "!" in t
    c2 = w.web()
    w.login(c2, "ann")
    assert BANNER_ZH in c2.get("/").text      # TC-005: still on after a new login


def test_set_each_flag_independently(w):
    # TC-007
    w.user("ann")
    c = login(w, "ann")
    assert post(c, "step_mode", "0").status_code in (302, 303)
    _, mid = mid_of(c)
    assert "—" in row(mid, "逐步模式") and "開啟" in row(mid, "逐步模式")
    assert "開啟" in row(mid, "開發模式") and "✓" not in row(mid, "開發模式")


def test_turn_dev_off(w):
    # TC-008
    w.user("ann")
    c = login(w, "ann")
    post(c, "dev_mode", "1")
    assert post(c, "dev_mode", "0").status_code in (302, 303)
    _, mid = mid_of(c)
    assert "—" in row(mid, "開發模式") and "開啟" in row(mid, "開發模式")


def test_switch_forms_and_one_click_save(w):
    # TC-009, TC-045: one native post form per row with the four hidden boxes; a submit button; the answer is a redirect, not a confirmation page
    w.user("ann")
    c = login(w, "ann")
    _, mid = mid_of(c)
    forms = re.findall(r'<form method="post" action="/settings/personal">(.*?)</form>', personal(mid), re.S)
    assert len(forms) == 2
    for f in forms:
        for name in ("csrf", "key", "on", "lang"):
            assert re.search(r'<input type="hidden" name="%s"' % name, f)
        assert '<button type="submit">' in f
    assert post(c, "dev_mode", "1").status_code in (302, 303)


def test_banner_is_per_person(w):
    # TC-010, TC-019
    two_users(w)
    ca, cb = login(w, "ann"), login(w, "bob")
    post(ca, "dev_mode", "1")
    post(ca, "step_mode", "0")
    for _ in range(2):
        for path in ("/", "/settings"):
            assert BANNER_ZH in ca.get(path).text and BANNER_ZH not in cb.get(path).text
    _, mid = mid_of(cb)
    assert "✓" in row(mid, "逐步模式") and "✓" not in row(mid, "開發模式")


def test_old_database_migrates_to_defaults(w):
    # TC-011: a users table made before the two columns opens, keeps its rows, shows the defaults and then saves
    w.user("ann")
    con = sqlite3.connect(str(w.ip.tokens))
    cols = [r[1] for r in con.execute("PRAGMA table_info(users)")]
    con.execute("PRAGMA foreign_keys=off")
    con.execute("ALTER TABLE users DROP COLUMN step_mode")
    con.execute("ALTER TABLE users DROP COLUMN dev_mode")
    con.commit()
    assert "step_mode" not in [r[1] for r in con.execute("PRAGMA table_info(users)")] and "step_mode" in cols
    con.close()
    c = login(w, "ann")
    _, mid = mid_of(c)
    assert "✓" in row(mid, "逐步模式") and "開啟" in row(mid, "開發模式")
    assert post(c, "dev_mode", "1").status_code in (302, 303)
    assert prefs(w, "ann") == (None, 1) or prefs(w, "ann") == (1, 1)


def test_get_my_settings_reads_only_self(w):
    # TC-012
    from abf_platform import actions
    ann, bob = two_users(w)
    actions.set_my_setting(w.ip.tokens, "dev_mode", True, confirmed_by=actions.PAGE, caller=ann)
    assert actions.get_my_settings(w.ip.tokens, caller=ann) == {"step_mode": True, "dev_mode": True}
    assert actions.get_my_settings(w.ip.tokens, caller=bob) == {"step_mode": True, "dev_mode": False}


# ---- US2 ---------------------------------------------------------------------------------------------------------------------------

def test_banner_on_every_framed_page(w):
    # TC-016
    w.user("ann")
    c = login(w, "ann")
    post(c, "dev_mode", "1")
    for path in ("/launch", "/usage", "/upload"):
        r = c.get(path)
        assert r.status_code == 200 and BANNER_ZH in r.text, path


def test_banner_position_and_count(w):
    # TC-017
    w.user("ann")
    c = login(w, "ann")
    post(c, "dev_mode", "1")
    t = c.get("/").text
    assert t.count(BANNER_ZH) == 1
    assert t.index('class="mast"') < t.index(BANNER_ZH) < t.index('data-pane="left"')


def test_banner_not_shown_when_off(w):
    # TC-018: new person, and a person who turned it on and off again
    ann = w.user("ann")
    seed(w, "r1", owner=ann)
    c = login(w, "ann")
    paths = ("/", "/settings", "/?run=id-r1")
    assert all("開發模式已開啟" not in c.get(p).text for p in paths)
    post(c, "dev_mode", "1")
    post(c, "dev_mode", "0")
    assert all("開發模式已開啟" not in c.get(p).text for p in paths)


def test_step_mode_alone_shows_no_banner(w):
    # TC-022
    w.user("ann")
    c = login(w, "ann")
    post(c, "step_mode", "0")
    assert all("開發模式已開啟" not in c.get(p).text for p in ("/", "/settings"))


def test_state_not_by_colour_alone(w):
    # TC-020, TC-036, TC-044: symbol, word and class together
    ann, bob = two_users(w)
    pat(w, ann, "laptop")
    c = login(w, "ann")
    post(c, "dev_mode", "1")
    text, mid = mid_of(c)
    m = re.search(r'<div class="devbar"[^>]*>(.*?)</div>', text, re.S)
    assert m and "!" in m.group(1) and BANNER_ZH in m.group(1)
    assert "✓" in row(mid, "開發模式") and "開" in re.sub(r"<[^>]+>", "", row(mid, "開發模式"))
    assert re.search(r"✓.*已設定", section(mid, "憑證"), re.S)
    _, bmid = mid_of(login(w, "bob"))
    assert re.search(r"—.*未設定", section(bmid, "憑證"), re.S)
    assert "—" in row(bmid, "開發模式") and "關" in row(bmid, "開發模式")


def test_banner_css_uses_only_existing_tokens(w):
    # TC-021
    w.user("ann")
    c = login(w, "ann")
    post(c, "dev_mode", "1")
    text = c.get("/").text
    assert text.count("<style>") == 1
    css = re.search(r"<style>(.*?)</style>", text, re.S).group(1)
    rules = re.findall(r"[^{}]*\.devbar[^{}]*\{[^}]*\}", css)
    assert rules
    joined = " ".join(rules)
    assert "var(--lost-bg)" in joined and "var(--lost)" in joined
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", joined) and "border-left" not in joined
    pr = re.findall(r"[^{}]*\.pref[^{}]*\{[^}]*\}", css)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", " ".join(pr)) and "border-left" not in " ".join(pr)


# ---- US3 ---------------------------------------------------------------------------------------------------------------------------

def test_post_refused_cases(w):
    # TC-023..TC-026: nothing is written
    w.user("ann")
    c = login(w, "ann")
    good = token(c, "dev_mode")
    assert post(c, "dev_mode", "1", csrf="wrong").status_code == 400
    assert post(c, "role", "1", csrf=good).status_code == 400
    assert post(c, "dev_mode", "maybe", csrf=good).status_code == 400
    assert prefs(w, "ann") in ((None, None), (1, 0))
    assert "開發模式已開啟" not in c.get("/").text
    anon = w.web()
    r = anon.post("/settings/personal", data={"csrf": good, "key": "dev_mode", "on": "1", "lang": "zh"})
    assert r.status_code in (303, 302) or 400 <= r.status_code < 500
    assert prefs(w, "ann") in ((None, None), (1, 0))


def test_set_my_setting_refuses_without_page_channel(w):
    # TC-027
    from abf_platform import actions, jobs
    ann = w.user("ann")
    for value in ("missing", None, "PAGE", "look-alike"):
        kw = {}
        if value != "missing":
            kw["confirmed_by"] = type("Channel", (), {"name": "PAGE"})() if value == "look-alike" else value
        with pytest.raises(jobs.JobRefused):
            actions.set_my_setting(w.ip.tokens, "dev_mode", True, caller=ann, **kw)
    assert actions.get_my_settings(w.ip.tokens, caller=ann)["dev_mode"] is False


def test_refusal_sentence_in_top_flash(w):
    # TC-028: one plain sentence at the top, in the flash place, no new section, no code words
    w.user("ann")
    c = login(w, "ann")
    r = post(c, "role", "1", csrf=token(c, "dev_mode"))
    mid = pane(r.text, "middle")
    assert r.status_code == 400 and re.search(r'<h1>設定</h1><p class="bad">', mid)
    assert len(re.findall(r"<h2>", mid)) == 7 and "Traceback" not in r.text and "role" not in re.search(r'<p class="bad">(.*?)</p>', mid, re.S).group(1)


def test_refusal_keeps_current_values(w):
    # TC-029
    w.user("ann")
    c = login(w, "ann")
    post(c, "step_mode", "0")
    post(c, "dev_mode", "1")
    r = post(c, "dev_mode", "0", csrf="wrong")
    mid = pane(r.text, "middle")
    assert r.status_code == 400
    assert "開啟" in row(mid, "逐步模式") and "關閉" in row(mid, "開發模式")


# ---- US4 ---------------------------------------------------------------------------------------------------------------------------

def test_credentials_say_set_or_not(w):
    # TC-030, TC-031, TC-033, TC-034, TC-058
    ann, bob = two_users(w)
    _, value = pat(w, ann, "laptop")
    ca, cb = login(w, "ann"), login(w, "bob")
    texts = [ca.get(u).text for u in ("/settings", "/")]
    sec = section(pane(texts[0], "middle"), "憑證")
    assert "存取權杖：" in re.sub(r"<[^>]+>", "", sec) and "已設定" in sec and "✓" in sec
    assert "abf-platform token new" in sec and '<p class="off">建立或撤銷權杖 <span class="later">之後開放</span></p>' in sec and "<table" not in sec
    for t in texts:
        assert value not in t and hashlib.sha256(value.encode()).hexdigest() not in t
    bsec = section(pane(cb.get("/settings").text, "middle"), "憑證")
    assert "未設定" in bsec and "已設定" not in bsec and "—" in bsec


def test_credentials_revoked_counts_as_not_set(w):
    # TC-032
    ann = w.user("ann")
    pat(w, ann, "a", revoke=True)
    pat(w, ann, "b", revoke=True)
    _, mid = mid_of(login(w, "ann"))
    assert "未設定" in section(mid, "憑證")


def test_credentials_show_no_token_details(w):
    # TC-035
    ann = w.user("ann")
    pat(w, ann, "lab-label-one")
    pat(w, ann, "lab-label-two")
    text, mid = mid_of(login(w, "ann"))
    sec = section(mid, "憑證")
    assert sec.count("已設定") == 1 and "lab-label" not in text and "<li" not in sec.split("token new")[0]


# ---- US5 ---------------------------------------------------------------------------------------------------------------------------

def test_english(w):
    # TC-037, TC-038, TC-039
    ann, bob = two_users(w)
    pat(w, ann, "laptop")
    ca = login(w, "ann")
    post(ca, "dev_mode", "1")
    post(ca, "step_mode", "0")      # so that both a "Turn off" and a "Turn on" button are on the page
    text, mid = mid_of(ca, "/settings?lang=en")
    assert not CJK.search(mid) and BANNER_EN in text and "!" in text
    sec = personal(mid, "Personal")
    assert "Step-by-step mode" in sec and "Development mode" in sec and "On" in sec and "Turn off" in sec and "Turn on" in sec
    assert re.search(r"✓.*Set", section(mid, "Credentials"), re.S)
    assert not CJK.search(re.search(r'<div class="devbar".*?</div>', text, re.S).group(0))
    assert BANNER_EN in ca.get("/?lang=en").text
    _, bmid = mid_of(login(w, "bob"), "/settings?lang=en")
    assert "Not set" in section(bmid, "Credentials") and "Off" in row(bmid, "Development mode", "Personal")


def test_english_notice_after_save(w):
    # TC-040
    w.user("ann")
    c = login(w, "ann")
    r = post(c, "dev_mode", "1", csrf=token(c, "dev_mode", "en"), lang="en")
    assert r.status_code in (302, 303) and "personal-saved" in r.headers["location"]
    text, mid = mid_of(c, r.headers["location"])
    assert 'class="notice"' in mid and not CJK.search(mid)


def test_no_script_no_inline_style(w):
    # TC-041
    w.user("ann")
    c = login(w, "ann")
    for on in ("0", "1"):
        post(c, "dev_mode", on)
        for path in ("/settings", "/"):
            r = c.get(path)
            assert "<script" not in r.text and "style=" not in r.text and r.text.count("<style>") == 1
            csp = r.headers["content-security-policy"]
            assert csp.startswith("default-src 'none'; style-src 'sha256-") and csp.endswith("form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            digest = base64.b64encode(hashlib.sha256(re.search(r"<style>(.*?)</style>", r.text, re.S).group(1).encode()).digest()).decode()
            assert "'sha256-%s'" % digest in csp


def test_switches_are_native_buttons(w):
    # TC-045
    w.user("ann")
    _, mid = mid_of(login(w, "ann"))
    for f in re.findall(r"<form.*?</form>", personal(mid), re.S):
        assert re.search(r"<button type=\"submit\">[^<]+</button>", f)


# ---- not in scope ------------------------------------------------------------------------------------------------------------------

def strip_personal(text):
    return re.sub(r'<section class="card sec"><h2>個人</h2>.*?</section>', "", text, flags=re.S)


def test_dev_mode_changes_no_su_judgement(w):
    # TC-050: the usage page differs only by the banner
    w.user("ann")
    c = login(w, "ann")
    before = c.get("/usage").text
    post(c, "dev_mode", "1")
    after = c.get("/usage").text
    assert after.replace('<div class="devbar"', "\0", 1) != after
    assert re.sub(r'<div class="devbar".*?</div>', "", after, flags=re.S) == before


def test_step_mode_changes_nothing_else(w):
    # TC-051
    w.user("ann")
    c = login(w, "ann")
    outs = {p: c.get(p).text for p in ("/launch", "/")}
    post(c, "step_mode", "0")
    for p, was in outs.items():
        assert c.get(p).text == was


def test_ai_key_section_unchanged(w):
    # TC-052
    w.user("ann")
    c = login(w, "ann")
    _, mid = mid_of(c)
    assert section(mid, "密碼與金鑰") == '<ul><li><span class="off">AI 模型金鑰 <span class="later">之後開放</span></span></li></ul><p class="muted">金鑰僅儲存於您的瀏覽器，不會傳送至平台。</p>'
    _, en = mid_of(c, "/settings?lang=en")
    assert "The key stays in your browser and is never sent to the platform." in en


def test_no_model_key_input(w):
    # TC-054
    w.user("ann")
    text, mid = mid_of(login(w, "ann"))
    assert "<script" not in text and "localStorage" not in text and "<input" not in section(mid, "密碼與金鑰")


def test_later_items_stay_grey(w):
    # TC-055
    w.user("ann")
    _, mid = mid_of(login(w, "ann"))
    assert "<form" not in section(mid, "憑證") and "<button" not in section(mid, "憑證")
    for head in ("營運者後台", "角色（老師／學生）"):
        assert "之後開放" in section(mid, head) and "<form" not in section(mid, head)


def test_store_adds_only_two_integer_columns(w):
    # TC-059
    from abf_platform import store
    w.user("ann")
    con = sqlite3.connect(str(w.ip.tokens))
    cols = {r[1]: r[2] for r in con.execute("PRAGMA table_info(users)")}
    con.close()
    assert cols["step_mode"] == "INTEGER" and cols["dev_mode"] == "INTEGER"
    assert set(cols) == {"id", "name", "lab", "created_at", "disabled_at", "password_hash", "temp_until", "step_mode", "dev_mode"}


def test_flags_start_no_jobs(w):
    # TC-061
    w.user("ann")
    c = login(w, "ann")
    jobs_before = w.sql("SELECT * FROM jobs")
    conf_before = w.sql("SELECT * FROM confirmations")
    for k, on in (("dev_mode", "1"), ("step_mode", "0"), ("dev_mode", "0"), ("step_mode", "1")):
        post(c, k, on)
    assert w.sql("SELECT * FROM jobs") == jobs_before and w.sql("SELECT * FROM confirmations") == conf_before
