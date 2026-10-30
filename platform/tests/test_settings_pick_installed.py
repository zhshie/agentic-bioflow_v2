# Nothing existing: tests of choosing a pipeline version from the list the site reports (specs/settings-pick-installed); the page, the read and the limits are ours.
"""settings-pick-installed: the action that reads the site list, the pick step of POST /settings/pipelines, the reload button and the
four pictures of an environment on the settings page. Test cases are named in the comments (A01 ... K06 of
specs/settings-pick-installed/test-case.md). The station half is in test_station_site_inventory.py."""
import ast
import hashlib
import json
import re
import time

import pytest

from helpers import PLATFORM_DIR
from human_harness import World
from test_web_board import login, pane
from test_web_settings import make_agent, make_env, sql
from test_web_settings_register import (BASE_STYLE_SHA, CJK, FORBIDDEN, above, confirm_data, entries, fields, hidden, mid_of, plain, preflights,
                                        row_block, set_entries, signed, snapshot, step1, step2, tok)

PKG = PLATFORM_DIR / "abf_platform"
AMPLI = {"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "module": "biology/nf-core-ampliseq/2.18.0", "home": "NFCORE_AMPLISEQ_HOME", "home_source": "module"}
RNA = {"pipeline": "nf-core/rnaseq", "revision": "3.14.0", "module": "biology/nf-core-rnaseq/3.14.0", "home": "NFCORE_RNASEQ_HOME", "home_source": "guessed"}
READ_AT = "2026-10-29T08:30:00Z"
CLOUD_PLATFORMS = ("googlebatch-platform", "awsbatch-platform", "azbatch-platform")
GONE_ZH = "站台清單中無此版本，請按「重新讀取站台清單」。"
GONE_EN = 'This version is not in the site list. Press "Reload site list".'
CLOUD_ZH = "此環境每次送出都直接取用 nf-core 官方版本，不需登記管線。"
CLOUD_EN = "This environment uses the nf-core release directly on every run; no pipeline registration is needed."
NONE_ZH = "尚未讀取此站台已安裝的管線。"
NONE_EN = "The pipelines installed on this site have not been read yet."
NOMOD_ZH = "此站台沒有找到已安裝的 nf-core 模組：送出時直接取用 nf-core 官方版本。若管線裝在模組以外的位置，請使用下方「進階：手動填寫」。"
NOMOD_EN = ('No installed nf-core modules were found on this site: runs use the nf-core release directly. '
            'If the pipeline is installed outside the modules, use "Advanced: fill in manually" below.')
ADV_ZH, ADV_EN = "進階：手動填寫（管理者用）", "Advanced: fill in manually (administrators)"
QUEUED = ("✓", "已排入讀取站台清單。", "Reading the site list has been queued.")
NO_AGENT = ("○", "站台代理目前離線，未能讀取站台清單。", "The site agent is offline; the site list could not be read.")
EXPIRED_HINT = "表單驗證碼不符或已失效，未變更任何內容。請重新整理頁面後再試。"
OK_INV = {"status": "ok", "items": [AMPLI, RNA], "read_at": READ_AT}
NEW_KEYS = ["pf_cloud", "pf_pick_label", "pf_guess", "pf_read_at", "pf_reload", "pf_inv_none", "pf_inv_nomod", "pf_inv_error", "pf_adv",
            "pf_pick_gone", "pf_n_inv_queued", "pf_n_inv_no_agent"]


@pytest.fixture
def w(tmp_path, monkeypatch):
    from abf_platform import compute_envs
    world = World(tmp_path, monkeypatch)
    world.base_env = compute_envs.get(world.ip.state_db, "lab-a")
    return world


@pytest.fixture
def ann(w):
    return w.user("ann")


# ---- helpers ----------------------------------------------------------------------------------------------------------------------




def feed(w, inv, ce="lab-a", ok=True):
    """The way an agent reports: a preflight job is queued, claimed and answered, so the result goes through the platform's own cleaning."""
    from abf_platform import jobs
    agent = w.sql("SELECT agent FROM compute_envs WHERE name = ?", (ce,))[0][0]
    w._tick = getattr(w, "_tick", 0) + 3
    t = time.time() + w._tick
    jid = jobs.enqueue_preflight(w.ip.state_db, ce, lambda: t)
    got = jobs.claim(w.ip.state_db, agent, lambda: t)
    assert got and got["id"] == jid
    result = {"ok": ok, "checks": [{"name": "connect", "status": "pass", "detail": "the site answers"}]}
    if inv is not None:
        result["site_inventory"] = inv
    status, body = jobs.take_result(w.ip.state_db, agent, jid, "done", result, lambda: t + 1)
    assert status == 200 and body["accepted"] is True
    return jid


def inv_of(w, caller, ce="lab-a"):
    from abf_platform import actions
    return actions.site_pipeline_inventory(w.ip.state_db, ce=ce, caller=caller)


def make_cloud(w, caller, name="ann-gcb", platform="googlebatch-platform"):
    make_agent(w, caller, "agent-" + name)
    make_env(w, caller, name, "agent-" + name)
    sql(w, "UPDATE compute_envs SET platform = ? WHERE name = ?", (platform, name))
    return name


def uplain(text):
    """plain(), with the entities of the page turned back into the characters a person reads."""
    import html
    return html.unescape(plain(text))


def get(c, lang="zh", **query):
    q = dict(query, **({"lang": "en"} if lang == "en" else {}))
    r = c.get("/settings" + ("?" + "&".join("%s=%s" % kv for kv in q.items()) if q else ""))
    assert r.status_code == 200, r.text[:300]
    return r, mid_of(r.text)


def block_of(w_or_c, mid, ce="lab-a"):
    return row_block(mid, ce)


def forms_of(block):
    return [(m.group(1), m.group(2)) for m in re.finditer(r"<form([^>]*)>(.*?)</form>", block, re.S)]


def options(block):
    import html
    return [(html.unescape(m.group(1)), html.unescape(m.group(2))) for m in re.finditer(r'<option value="([^"]*)">([^<]*)</option>', block)]


def outside_details(block):
    return re.sub(r"<details.*?</details>", "", block, flags=re.S)


def reload_form(block):
    """(action, hidden fields) of the form whose button reloads the site list; the path is not fixed by the contract, the page says it."""
    for attrs, inner in forms_of(block):
        if "重新讀取站台清單" in inner or "Reload site list" in inner:
            action = re.search(r'action="([^"]+)"', attrs).group(1)
            return action, {m.group(1): m.group(2) for m in re.finditer(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', inner)}
    raise AssertionError("no reload form in " + block[:500])


def pick_data(c, pick="nf-core/ampliseq 2.18.0", ce="lab-a", csrf=True, **extra):
    data = {"op": "add", "ce": ce, "pick": pick}
    data.update(extra)
    if csrf is True:
        data["csrf"] = tok(c, "settings-pipeline")
    elif csrf:
        data["csrf"] = csrf
    return data


def post_pick(c, **kw):
    headers = kw.pop("headers", None) or {}
    return c.post("/settings/pipelines", data=pick_data(c, **kw), headers=headers)


def go_pick(c, **kw):
    r = post_pick(c, **kw)
    assert r.status_code == 200, r.text[:300]
    return step2(c, confirm_data(r.text))


def count_jobs(w):
    return len(w.sql("SELECT id FROM jobs"))


# ---- 2. the action layer -----------------------------------------------------------------------------------------------------------

def test_a01_the_latest_list_wins(w, ann):
    # A01
    feed(w, {"status": "ok", "items": [AMPLI], "read_at": "2026-10-29T07:00:00Z"})
    feed(w, OK_INV)
    got = inv_of(w, ann)
    assert got["status"] == "ok" and got["read_at"] == READ_AT and [i["pipeline"] for i in got["items"]] == ["nf-core/ampliseq", "nf-core/rnaseq"]


def test_a02_never_read_is_none(w, ann):
    # A02
    assert inv_of(w, ann) == {"status": "none"}
    feed(w, None)      # a preflight that carried no list does not count
    assert inv_of(w, ann) == {"status": "none"}


def test_a03_a_later_preflight_without_a_list_does_not_hide_it(w, ann):
    # A03
    feed(w, OK_INV)
    feed(w, None, ok=False)
    assert inv_of(w, ann)["status"] == "ok" and len(inv_of(w, ann)["items"]) == 2


def test_a04_another_users_environment_is_not_found(w, ann):
    # A04
    ben = w.user("ben")
    ce = w.env_for(ben)
    feed(w, OK_INV, ce=ce)
    one, two = inv_of(w, ann, ce), inv_of(w, ann, "no-such-env")
    assert one == two and "ampliseq" not in json.dumps(one) and one.get("found") is False
    assert inv_of(w, ben, ce)["status"] == "ok"


def test_a05_reading_changes_nothing(w, ann):
    # A05
    from abf_platform import actions
    feed(w, OK_INV)
    before = snapshot(w)
    assert actions.site_pipeline_inventory(w.ip.state_db, ce="lab-a", caller=ann)["status"] == "ok"
    assert snapshot(w) == before


def test_a06_the_list_survives_the_platforms_own_cleaning(w, ann):
    # A06
    feed(w, OK_INV)
    got = inv_of(w, ann)
    assert got["items"] == [AMPLI, RNA] and got["read_at"] == READ_AT


def test_a06b_the_platform_keeps_only_well_formed_entries(w, ann):
    # A06 (the cleaning: an agent cannot make the platform store more than the shape allows)
    bad = [dict(AMPLI, module="x; rm -rf /"), dict(AMPLI, home="lower"), dict(AMPLI, revision="main"), dict(AMPLI, pipeline="acme/x"), "text", dict(RNA, extra="y")]
    feed(w, {"status": "ok", "items": bad + [RNA], "read_at": READ_AT, "stray": "z"})
    got = inv_of(w, ann)
    assert got["items"] == [RNA] and "stray" not in got
    feed(w, {"status": "weird", "items": [AMPLI]})
    assert inv_of(w, ann)["status"] == "ok" and inv_of(w, ann)["items"] == [RNA]      # an unknown status is not stored


def test_a07_register_with_module_and_home_still_works(w, ann):
    # A07
    from abf_platform import actions
    out = actions.register_site_pipeline(w.ip.state_db, ce="lab-a", confirmed_by=actions.PAGE, caller=ann,
                                         **{k: AMPLI[k] for k in ("pipeline", "revision", "module", "home")})
    assert out["ok"] is True and out["preflight"] == "queued"
    assert entries(w) == [{k: AMPLI[k] for k in ("pipeline", "revision", "module", "home")}]


# ---- 3. the pick step --------------------------------------------------------------------------------------------------------------

def test_b01_b02_pick_shows_what_the_server_found(w, ann):
    # B01, B02
    feed(w, OK_INV)
    c = login(w, "ann")
    before = snapshot(w)
    r = post_pick(c)
    assert r.status_code == 200 and snapshot(w) == before
    text = plain(r.text)
    for label in ("新增", "lab-a", "nf-core/ampliseq", "2.18.0", AMPLI["module"], AMPLI["home"], "模組名稱", "管線資料夾變數"):
        assert label in text, label
    h = confirm_data(r.text)
    f = fields(pipeline=AMPLI["pipeline"], revision=AMPLI["revision"], module=AMPLI["module"], home=AMPLI["home"])
    assert {k: h[k] for k in f} == f
    form = re.search(r'<form[^>]*action="/settings/pipelines/confirm"', r.text)
    assert form and re.search(r'<button[^>]*type="submit"[^>]*>確認</button>', r.text)
    assert re.search(r'<a[^>]*href="/settings[^"]*"[^>]*>返回</a>', r.text)
    assert h["csrf"] == tok(c, "settings-pipeline-confirm:" + hashlib.sha256("\n".join(f[k] for k in ("op", "ce", "pipeline", "revision", "module", "home")).encode()).hexdigest())


def test_b03_a_module_sent_by_the_browser_is_ignored(w, ann):
    # B03
    feed(w, OK_INV)
    c = login(w, "ann")
    before = snapshot(w)
    r = post_pick(c, module="evil", home="EVIL_HOME", pipeline="nf-core/evil", revision="9.9.9")
    assert r.status_code == 200 and snapshot(w) == before
    assert "evil" not in r.text.lower().replace("evil_home", "EVIL_HOME") and "EVIL_HOME" not in r.text
    h = confirm_data(r.text)
    assert h["module"] == AMPLI["module"] and h["home"] == AMPLI["home"] and h["pipeline"] == "nf-core/ampliseq"


def test_b04_a_version_not_in_the_list_is_refused(w, ann):
    # B04
    feed(w, OK_INV)
    c = login(w, "ann")
    before = snapshot(w)
    r = post_pick(c, pick="nf-core/ampliseq 9.9.9")
    assert r.status_code == 400 and snapshot(w) == before
    mid = mid_of(r.text)
    assert "✕" in plain(mid) and GONE_ZH in plain(mid) and "/settings/pipelines/confirm" not in r.text
    above(mid, GONE_ZH, "lab-a")
    en = c.post("/settings/pipelines", data=dict(pick_data(c, pick="nf-core/ampliseq 9.9.9"), lang="en"))
    assert en.status_code == 400 and GONE_EN in uplain(mid_of(en.text))
    assert snapshot(w) == before and preflights(w) == len(w.sql("SELECT id FROM jobs WHERE kind = 'preflight'"))


@pytest.mark.parametrize("state", ["none", "no_module_system", "error", "ok_empty"])
def test_b05_a_list_that_cannot_offer_it(w, ann, state):
    # B05
    if state == "no_module_system":
        feed(w, {"status": "no_module_system", "items": [], "read_at": READ_AT})
    elif state == "error":
        feed(w, {"status": "error", "items": [], "read_at": READ_AT, "reason": "讀不出模組清單 (the module list could not be read)"})
    elif state == "ok_empty":
        feed(w, {"status": "ok", "items": [], "read_at": READ_AT})
    c = login(w, "ann")
    before = snapshot(w)
    r = post_pick(c)
    assert r.status_code == 400 and GONE_ZH in plain(mid_of(r.text)) and snapshot(w) == before


@pytest.mark.parametrize("pick", ["", "nf-core/ampliseq", "nf-core/ampliseq  2.18.0", "nf-core/ampliseq 2.18.0 extra", "nf-core/ampliseq\n2.18.0", " ", "2.18.0",
                                  "nf-core/ampliseq 2.18.0\n"])
def test_b06_a_pick_of_the_wrong_shape(w, ann, pick):
    # B06
    feed(w, OK_INV)
    c = login(w, "ann")
    before = snapshot(w)
    r = post_pick(c, pick=pick)
    if pick == "nf-core/ampliseq 2.18.0\n":      # only trailing white space: the same as the clean one, as every other box of the page
        assert r.status_code == 200
        return
    assert r.status_code == 400 and snapshot(w) == before and "/settings/pipelines/confirm" not in r.text
    assert "Traceback" not in r.text and "sqlite" not in r.text.lower()


def test_b06b_a_missing_pick_and_no_other_box(w, ann):
    # B06 (no pick at all) and B14
    feed(w, OK_INV)
    c = login(w, "ann")
    before = snapshot(w)
    r = c.post("/settings/pipelines", data={"op": "add", "ce": "lab-a", "csrf": tok(c, "settings-pipeline")})
    assert r.status_code == 400 and "為必填" in plain(mid_of(r.text)) and snapshot(w) == before


def test_b07_a_guessed_variable(w, ann):
    # B07
    feed(w, OK_INV)
    c = login(w, "ann")
    h = confirm_data(post_pick(c, pick="nf-core/rnaseq 3.14.0").text)
    assert h["home"] == "NFCORE_RNASEQ_HOME" and h["module"] == RNA["module"]


def test_b08_a_cloud_environment_has_no_list(w, ann):
    # B08
    ce = make_cloud(w, ann)
    c = login(w, "ann")
    before = snapshot(w)
    r = post_pick(c, ce=ce)
    assert r.status_code == 400 and GONE_ZH in plain(mid_of(r.text)) and snapshot(w) == before


def test_b09_another_users_environment(w, ann):
    # B09
    ben = w.user("ben")
    ce = w.env_for(ben)
    feed(w, OK_INV, ce=ce)
    c = login(w, "ann")
    before = snapshot(w)
    one, two = post_pick(c, ce=ce), post_pick(c, ce="no-such-env")
    assert one.status_code == two.status_code == 400
    assert plain(mid_of(one.text)).replace(ce, "X") == plain(mid_of(two.text)).replace("no-such-env", "X")
    assert "<option" not in mid_of(one.text) and snapshot(w) == before and entries(w, ce) == []


def test_b10_csrf_origin_and_login(w, ann):
    # B10
    from abf_platform import store
    feed(w, OK_INV)
    c = login(w, "ann")
    before = snapshot(w)
    for token in (None, "wrong", tok(c, "logout"), tok(c, "settings-inventory")):
        data = pick_data(c, csrf=False)
        if token:
            data["csrf"] = token
        r = c.post("/settings/pipelines", data=data)
        assert r.status_code == 403 and "/settings/pipelines/confirm" not in r.text, token
    r = c.post("/settings/pipelines", data=pick_data(c), headers={"Origin": "http://evil.example"})
    assert r.status_code == 403
    assert snapshot(w) == before
    fresh = w.web()
    r = fresh.post("/settings/pipelines", data=pick_data(c))
    assert r.status_code == 303 and r.headers["location"] == "/login"
    out = store.issue_temporary_password(w.ip.tokens, "ann", now=w.clock.t)
    t = w.web()
    assert w.login(t, "ann", password=out["password"]).status_code == 303
    r = t.post("/settings/pipelines", data=dict(pick_data(c)))
    assert r.status_code == 303 and r.headers["location"] == "/welcome" and snapshot(w) == before


def test_b11_e01_two_presses_and_nothing_typed(w, ann):
    # B11, E01
    feed(w, OK_INV)
    c = login(w, "ann")
    before = preflights(w)
    r = go_pick(c)
    assert r.status_code == 303 and r.headers["location"] == "/settings?notice=added_queued&ce=lab-a#ce-lab-a"
    assert entries(w) == [{k: AMPLI[k] for k in ("pipeline", "revision", "module", "home")}] and preflights(w) == before + 1


def test_b12_the_confirm_step_trusts_only_the_signed_boxes(w, ann):
    # B12
    feed(w, OK_INV)
    c = login(w, "ann")
    data = confirm_data(post_pick(c).text)
    before = snapshot(w)
    for key, value in (("module", "other/module"), ("home", "OTHER_HOME")):
        r = step2(c, dict(data, **{key: value}))
        assert r.status_code == 403
    assert snapshot(w) == before


def test_b13_the_advanced_form_is_unchanged(w, ann):
    # B13
    c = login(w, "ann")
    r = step1(c)
    assert r.status_code == 200 and confirm_data(r.text)["module"] == "biology/nf-core-ampliseq/2.18.0"
    for over, word in (({"module": "biology/../x"}, "模組名稱"), ({"home": "nfcore"}, "管線資料夾變數"), ({"revision": "main"}, "版本"), ({"pipeline": "acme/x"}, "管線")):
        bad = step1(c, **over)
        assert bad.status_code == 400 and word in plain(mid_of(bad.text))
    r = step1(c, fields("remove"))
    assert r.status_code == 303      # removing a version that is not listed


# ---- 4. reload ----------------------------------------------------------------------------------------------------------------------

def reload_post(c, w, ce="lab-a", **over):
    _, mid = get(c)
    action, hid = reload_form(row_block(mid, ce))
    data = dict(hid, **over)
    return c.post(action, data=data), action, hid


def test_r01_r07_reload_queues_one_preflight_and_nothing_else(w, ann):
    # R01, R07
    feed(w, OK_INV)
    set_entries(w, [{k: AMPLI[k] for k in ("pipeline", "revision", "module", "home")}])
    c = login(w, "ann")
    before = snapshot(w)
    jobs_before = count_jobs(w)
    r, action, _ = reload_post(c, w)
    assert r.status_code == 303 and "notice=inv_queued" in r.headers["location"] and "ce=lab-a" in r.headers["location"]
    assert r.headers["location"].endswith("#ce-lab-a")
    assert count_jobs(w) == jobs_before + 1 and w.sql("SELECT kind FROM jobs ORDER BY id DESC LIMIT 1")[0][0] == "preflight"
    after = snapshot(w)
    assert after[0] == before[0] and after[1][:len(before[1])] == before[1]
    assert entries(w) == [{k: AMPLI[k] for k in ("pipeline", "revision", "module", "home")}]
    mid = get(c, notice="inv_queued", ce="lab-a")[1]
    assert "✓ 已排入讀取站台清單。" in plain(mid)
    above(mid, "已排入讀取站台清單。", "lab-a")


def test_r02_no_agent_online(w, ann):
    # R02
    feed(w, OK_INV)
    c = login(w, "ann")
    _, mid = get(c)
    action, hid = reload_form(row_block(mid, "lab-a"))
    sql(w, "UPDATE agents SET last_seen_at = 1000")
    before = count_jobs(w)
    r = c.post(action, data=hid)
    assert r.status_code == 303 and "notice=inv_no_agent" in r.headers["location"] and count_jobs(w) == before
    assert "○ 站台代理目前離線，未能讀取站台清單。" in plain(get(c, notice="inv_no_agent", ce="lab-a")[1])


def test_r03_r04_csrf_and_origin(w, ann):
    # R03, R04
    feed(w, OK_INV)
    c = login(w, "ann")
    _, mid = get(c)
    action, hid = reload_form(row_block(mid, "lab-a"))
    before = snapshot(w)
    for token in (None, "wrong", tok(c, "logout"), tok(c, "settings-pipeline")):
        data = {k: v for k, v in hid.items() if k != "csrf"}
        if token:
            data["csrf"] = token
        r = c.post(action, data=data)
        assert r.status_code == 403 and EXPIRED_HINT in plain(r.text), token
    r = c.post(action, data=hid, headers={"Origin": "http://evil.example"})
    assert r.status_code == 403
    assert snapshot(w) == before


def test_r05_login_required(w, ann):
    # R05
    from abf_platform import store
    feed(w, OK_INV)
    c = login(w, "ann")
    _, mid = get(c)
    action, hid = reload_form(row_block(mid, "lab-a"))
    before = snapshot(w)
    r = w.web().post(action, data=hid)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    out = store.issue_temporary_password(w.ip.tokens, "ann", now=w.clock.t)
    t = w.web()
    assert w.login(t, "ann", password=out["password"]).status_code == 303
    r = t.post(action, data=hid)
    assert r.status_code == 303 and r.headers["location"] == "/welcome" and snapshot(w) == before


def test_r06_another_users_environment(w, ann):
    # R06
    ben = w.user("ben")
    ce = w.env_for(ben)
    feed(w, OK_INV, ce=ce)
    c = login(w, "ann")
    feed(w, OK_INV)
    _, mid = get(c)
    action, hid = reload_form(row_block(mid, "lab-a"))
    before = snapshot(w)
    one = c.post(action, data=dict(hid, ce=ce))
    two = c.post(action, data=dict(hid, ce="no-such-env"))
    assert one.status_code == two.status_code and one.status_code in (400, 404)
    assert plain(one.text).replace(ce, "X") == plain(two.text).replace("no-such-env", "X")
    assert snapshot(w) == before


def test_r08_notice_words(w, ann):
    # R08
    c = login(w, "ann")
    for key, (sym, zh, en) in (("inv_queued", QUEUED), ("inv_no_agent", NO_AGENT)):
        mid = get(c, notice=key, ce="lab-a")[1]
        assert "%s %s" % (sym, zh) in plain(mid)
        above(mid, zh, "lab-a")
        mid_en = get(c, lang="en", notice=key, ce="lab-a")[1]
        assert "%s %s" % (sym, en) in plain(mid_en)
    for bogus in ("bogus", "<script>x</script>"):
        r = c.get("/settings", params={"notice": bogus, "ce": "lab-a"})
        assert r.status_code == 200 and "<script>x" not in r.text and "bogus" not in mid_of(r.text)


# ---- 5. the page ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("platform", CLOUD_PLATFORMS)
def test_d01_a_cloud_environment_has_one_sentence(w, ann, platform):
    # D01
    ce = make_cloud(w, ann, "ann-cloud", platform)
    for lang, line in (("zh", CLOUD_ZH), ("en", CLOUD_EN)):
        _, mid = get(login(w, "ann"), lang)
        block = row_block(mid, ce)
        assert line in plain(block)
        assert "<form" not in block and "<select" not in block and "<details" not in block
        for word in ("重新讀取站台清單", "Reload site list", ADV_ZH, ADV_EN):
            assert word not in block


def test_d02_a_cloud_environment_with_old_entries_keeps_the_remove_buttons(w, ann):
    # D02
    ce = make_cloud(w, ann)
    set_entries(w, [{k: AMPLI[k] for k in ("pipeline", "revision", "module", "home")}, {k: RNA[k] for k in ("pipeline", "revision", "module", "home")}], ce)
    _, mid = get(login(w, "ann"))
    block = row_block(mid, ce)
    forms = forms_of(block)
    assert len(forms) == 2 and all('action="/settings/pipelines"' in a and 'value="remove"' in i for a, i in forms)
    assert "nf-core/ampliseq 2.18.0" in plain(block) and CLOUD_ZH in plain(block) and "<select" not in block


def slurm_block(w, ann, inv=OK_INV, lang="zh", registered=()):
    if inv is not None:
        feed(w, inv)
    if registered:
        set_entries(w, list(registered))
    r, mid = get(login(w, "ann"), lang)
    return r, mid, row_block(mid, "lab-a")


def test_d03_d05_d06_the_dropdown(w, ann):
    # D03, D05, D06
    _, mid, block = slurm_block(w, ann)
    assert re.search(r"<select[^>]*name=\"pick\"[^>]*required|<select[^>]*required[^>]*name=\"pick\"", block)
    assert "站台已安裝的管線版本" in plain(block)
    assert options(block) == [("nf-core/ampliseq 2.18.0", "nf-core/ampliseq 2.18.0"), ("nf-core/rnaseq 3.14.0", "nf-core/rnaseq 3.14.0（變數名稱為推算）")]
    form = [f for f in forms_of(block) if "<select" in f[1]][0]
    assert 'action="/settings/pipelines"' in form[0] and re.search(r'name="op"[^>]*value="add"', form[1])
    plainform = outside_details(block)
    inputs = re.findall(r"<(input|select|textarea)([^>]*)>", plainform)
    visible = [(t, a) for t, a in inputs if 'type="hidden"' not in a]
    assert [t for t, _ in visible] == ["select"]
    assert "模組名稱" not in plain(plainform) and "管線資料夾變數" not in plain(plainform)
    assert "清單讀取於" in plain(plainform) and "重新讀取站台清單" in plainform and ">登記</button>" in plainform


def test_d04_registered_pairs_are_not_listed(w, ann):
    # D04
    _, _, block = slurm_block(w, ann, registered=[{k: AMPLI[k] for k in ("pipeline", "revision", "module", "home")}])
    assert [o[0] for o in options(block)] == ["nf-core/rnaseq 3.14.0"]
    sql(w, "DELETE FROM jobs WHERE 0")
    older = dict({k: AMPLI[k] for k in ("pipeline", "revision", "module", "home")}, revision="2.17.0")
    set_entries(w, [older])
    _, mid = get(login(w, "ann"))
    assert "nf-core/ampliseq 2.18.0" in [o[0] for o in options(row_block(mid, "lab-a"))]


def test_d07_never_read(w, ann):
    # D07
    _, _, block = slurm_block(w, ann, inv=None)
    p = plain(outside_details(block))
    assert NONE_ZH in p and "重新讀取站台清單" in p and "<select" not in block and ">登記</button>" not in outside_details(block)


@pytest.mark.parametrize("inv", [{"status": "no_module_system", "items": [], "read_at": READ_AT}, {"status": "ok", "items": [], "read_at": READ_AT}])
def test_d08_d09_no_module_system_or_an_empty_list(w, ann, inv):
    # D08, D09
    _, _, block = slurm_block(w, ann, inv)
    assert NOMOD_ZH in plain(block) and "<select" not in block


def test_d10_a_failed_read(w, ann):
    # D10
    reason = "<script>x</script> failed"
    _, _, block = slurm_block(w, ann, {"status": "error", "items": [], "read_at": READ_AT, "reason": reason})
    p = plain(outside_details(block))
    assert "✕ 未能讀取站台清單：" in p and "重新讀取站台清單" in p and "<select" not in block
    assert "<script>" not in block and "&lt;script&gt;" in block
    assert "Traceback" not in block and "/home/" not in block


def test_d11_everything_is_already_registered(w, ann):
    # D11
    both = [{k: i[k] for k in ("pipeline", "revision", "module", "home")} for i in (AMPLI, RNA)]
    r, _, block = slurm_block(w, ann, registered=both)
    assert r.status_code == 200 and options(block) == [] and "<select" not in block
    assert "重新讀取站台清單" in block and ADV_ZH in block and "未能" not in block


@pytest.mark.parametrize("inv", [OK_INV, None, {"status": "no_module_system", "items": [], "read_at": READ_AT},
                                 {"status": "error", "items": [], "read_at": READ_AT, "reason": "讀不出模組清單 (the module list could not be read)"}])
def test_d12_the_advanced_form_is_always_there(w, ann, inv):
    # D12
    _, _, block = slurm_block(w, ann, inv)
    m = re.search(r"<details([^>]*)>\s*<summary>(.*?)</summary>(.*?)</details>", block, re.S)
    assert m and "open" not in m.group(1) and ADV_ZH in m.group(2)
    form = forms_of(m.group(3))[0]
    assert 'action="/settings/pipelines"' in form[0] and 'value="add"' in form[1]
    for label in ("管線（例 nf-core/ampliseq）", "版本（例 2.18.0）", "模組名稱（站台 module load 使用的名稱，例 biology/nf-core-ampliseq/2.18.0）",
                  "管線資料夾變數（模組設定的環境變數名稱，例 NFCORE_AMPLISEQ_HOME）"):
        assert label in plain(form[1])
    assert len(re.findall(r"<input[^>]*name=\"(?:pipeline|revision|module|home)\"[^>]*required", form[1])) == 4


def test_d12b_the_remove_buttons_stay_with_the_list(w, ann):
    # D12 (the small remove forms of the registered list)
    _, _, block = slurm_block(w, ann, registered=[{k: AMPLI[k] for k in ("pipeline", "revision", "module", "home")}])
    rem = [f for f in forms_of(outside_details(block)) if 'value="remove"' in f[1]]
    assert len(rem) == 1 and 'action="/settings/pipelines"' in rem[0][0]


def test_d13_d14_the_english_page(w, ann):
    # D13, D14
    from abf_platform import web_settings
    _, mid, block = slurm_block(w, ann, lang="en")
    p = plain(block)
    for word in ("Pipeline version installed on the site", "(variable name is inferred)", "List read at", "Reload site list", ADV_EN, "Register"):
        assert word in p, word
    assert not CJK.search(p)
    ce = make_cloud(w, ann)
    assert CLOUD_EN in plain(row_block(get(login(w, "ann"), "en")[1], ce))
    c = login(w, "ann")
    conf = c.post("/settings/pipelines", data=dict(pick_data(c), lang="en"))
    assert conf.status_code == 200 and not CJK.search(plain(pane(conf.text, "middle"))) and ">Confirm</button>" in conf.text and ">Back</a>" in conf.text
    zh, en = web_settings.STRINGS["zh"], web_settings.STRINGS["en"]
    for key in NEW_KEYS:
        assert zh.get(key) and en.get(key), key
        assert not CJK.search(en[key]), key
    assert en["pf_inv_none"] == NONE_EN and en["pf_inv_nomod"] == NOMOD_EN and en["pf_pick_gone"] == GONE_EN and en["pf_adv"] == ADV_EN


def test_d13b_the_english_states(w, ann):
    # D13 (each state in English)
    for inv, line in ((None, NONE_EN), ({"status": "no_module_system", "items": [], "read_at": READ_AT}, NOMOD_EN),
                      ({"status": "error", "items": [], "read_at": READ_AT, "reason": "讀不出模組清單 (the module list could not be read)"},
                       "✕ Could not read the site list:")):
        _, _, block = slurm_block(w, ann, inv, lang="en")
        assert line in uplain(block) and not CJK.search(uplain(block)), line


def test_d15_no_banned_word_in_the_new_chinese_strings():
    # D15
    from abf_platform import web_settings
    zh = web_settings.STRINGS["zh"]
    for key in NEW_KEYS:
        if key == "pf_pick_gone":      # the plan gives this sentence word for word (it holds 這個, see the note of the contract)
            continue
        assert not [bad for bad in FORBIDDEN if bad in zh[key]], key


def test_d16_buttons_are_fixed_verbs(w, ann):
    # D16
    _, _, block = slurm_block(w, ann, registered=[{k: AMPLI[k] for k in ("pipeline", "revision", "module", "home")}])
    labels = set(re.findall(r"<button[^>]*>(.*?)</button>", block))
    assert labels <= {"登記", "移除", "重新讀取站台清單"} and "重新讀取站台清單" in labels and "登記" in labels
    en = set(re.findall(r"<button[^>]*>(.*?)</button>", slurm_block(w, ann, None, "en")[2]))
    assert en <= {"Register", "Remove", "Reload site list"}


def test_d17_d18_d19_the_limits(w, ann):
    # D17, D18, D19
    import hashlib as h
    from abf_platform import web, web_board
    pages = []
    for inv in (OK_INV, None, {"status": "error", "items": [], "read_at": READ_AT, "reason": "r"}):
        r, mid, block = slurm_block(w, ann, inv)
        pages.append((r, mid, block))
    make_cloud(w, ann)
    pages.append((get(login(w, "ann")) + (None,)))
    c = login(w, "ann")
    pages.append((post_pick(c), None, None))
    pages.append((post_pick(c, pick="nf-core/ampliseq 9.9.9"), None, None))
    _, mid0 = get(c)
    action, hid = reload_form(row_block(mid0, "lab-a"))
    pages.append((c.post(action, data=hid), None, None))
    pages.append((c.post(action, data=dict(hid, csrf="x")), None, None))
    for r, mid, block in pages:
        for k, v in (("Content-Security-Policy", web._HEADERS["Content-Security-Policy"]), ("Cache-Control", "no-store"), ("X-Frame-Options", "DENY")):
            assert r.headers.get(k) == v, (k, r.status_code)
        if mid is not None:
            assert " style=" not in mid and "<script" not in mid and not re.search(r"https?://", mid)
    assert h.sha256(web_board.STYLE.encode("utf-8")).hexdigest() == BASE_STYLE_SHA
    css = web_board.STYLE
    for r, mid, block in pages:
        if block:
            for classes in re.findall(r'class="([^"]+)"', block):
                for cls in classes.split():
                    assert "." + cls in css, cls


def test_d20_state_is_not_colour_alone(w, ann):
    # D20
    _, _, block = slurm_block(w, ann, {"status": "error", "items": [], "read_at": READ_AT, "reason": "讀不出模組清單 (the module list could not be read)"})
    assert re.search(r'<span aria-hidden="true">✕</span> 未能讀取站台清單', block)
    c = login(w, "ann")
    r = c.post("/settings/pipelines", data=pick_data(c, pick="nf-core/x 1.0.0"))
    assert re.search(r'<span aria-hidden="true">✕</span> ' + re.escape(GONE_ZH), r.text)


def test_d21_each_person_sees_only_their_own(w, ann):
    # D21
    ben = w.user("ben")
    ce = w.env_for(ben)
    feed(w, OK_INV)
    feed(w, {"status": "ok", "items": [dict(AMPLI, pipeline="nf-core/bensonly", module="b/nf-core-bensonly/1.0.0", revision="1.0.0")], "read_at": READ_AT}, ce=ce)
    a, b = get(login(w, "ann"))[1], get(login(w, "ben"))[1]
    assert "bensonly" not in a and ce not in a and "ampliseq 2.18.0" in a
    assert "bensonly" in b and 'id="ce-lab-a"' not in b and "nf-core/rnaseq 3.14.0" not in b


def test_d22_no_environment_at_all(w, ann):
    # D22
    sql(w, "DELETE FROM compute_envs")
    r, mid = get(login(w, "ann"))
    assert r.status_code == 200 and "尚無運算環境。" in plain(mid) and "重新讀取" not in mid and "<select" not in mid and "/settings/pipelines" not in mid


def test_d23_each_block_follows_its_own_type(w, ann):
    # D23
    feed(w, OK_INV)
    ce = make_cloud(w, ann)
    _, mid = get(login(w, "ann"), notice="inv_queued", ce="lab-a")
    assert 'id="ce-lab-a"' in mid and 'id="ce-%s"' % ce in mid
    assert "<select" in row_block(mid, "lab-a") and "<select" not in row_block(mid, ce) and CLOUD_ZH in plain(row_block(mid, ce))
    above(mid, "已排入讀取站台清單。", "lab-a")


def test_d24_a_get_writes_nothing(w, ann):
    # D24
    feed(w, OK_INV)
    ce = make_cloud(w, ann)
    c = login(w, "ann")
    before = snapshot(w)
    for q in ("", "?notice=inv_queued&ce=lab-a", "?notice=inv_no_agent&ce=" + ce, "?notice=bogus", "?lang=en"):
        assert c.get("/settings" + q).status_code == 200
    assert snapshot(w) == before


# ---- 6. the two sentences of the maintainer, end to end ------------------------------------------------------------------------------

def test_e02_e03_no_registration_needed_to_launch(w, ann):
    # E02, E03
    from abf_platform import actions, web_board
    ce = make_cloud(w, ann)
    for inv in ({"status": "no_module_system", "items": [], "read_at": READ_AT}, {"status": "ok", "items": [], "read_at": READ_AT}):
        feed(w, inv)
        envs = {e["name"]: e for e in actions.list_compute_envs(w.ip.state_db, caller=ann)["compute_envs"]}
        for name in ("lab-a", ce):      # no entries: the launch is not refused as unregistered (the same reading as the empty list of #259)
            assert not web_board.is_unregistered(envs[name], "nf-core/ampliseq", "2.18.0"), name
    assert "<form" not in row_block(get(login(w, "ann"))[1], ce)


def test_e04_a_manual_registration_when_there_are_no_modules(w, ann):
    # E04
    feed(w, {"status": "no_module_system", "items": [], "read_at": READ_AT})
    c = login(w, "ann")
    r = step1(c)
    assert r.status_code == 200
    assert step2(c, confirm_data(r.text)).status_code == 303 and len(entries(w)) == 1


# ---- not in scope and the constitution --------------------------------------------------------------------------------------------------

def test_x01_no_new_table_no_new_job_kind(w, ann):
    # X01
    feed(w, OK_INV)
    ddl = " ".join(r[0] or "" for r in w.sql("SELECT sql FROM sqlite_master"))
    assert "inventory" not in ddl.lower() and "'preflight'" in ddl


def test_x02_no_mcp_tool(w, ann):
    # X02
    tools, _ = w.mcp([], caller=None)
    names = {t.name for t in tools}
    assert not [n for n in names if "inventory" in n or "site_pipeline" in n or "pick" in n or "reload" in n]


def test_x07_no_outgoing_connection(w, ann, monkeypatch):
    # X07
    import socket

    def no(*a, **k):
        raise AssertionError("an outgoing connection was attempted")
    feed(w, OK_INV)
    monkeypatch.setattr(socket.socket, "connect", no)
    monkeypatch.setattr(socket, "create_connection", no)
    c = login(w, "ann")
    get(c)
    go_pick(c)
    reload_post(c, w)


def test_k01_only_the_second_step_writes():
    # K01
    def own_nodes(fn):
        """The nodes of one function, without those of the functions defined inside it."""
        stack = list(ast.iter_child_nodes(fn))
        while stack:
            node = stack.pop()
            yield node
            if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                stack.extend(ast.iter_child_nodes(node))

    seen_second_step = False
    for name in ("web.py", "web_settings.py"):
        tree = ast.parse((PKG / name).read_text(encoding="utf-8"))
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))]:
            called = {a.attr for a in own_nodes(fn) if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id == "actions"}
            if called & {"register_site_pipeline", "remove_site_pipeline"}:
                assert name == "web.py" and fn.name == "pipelines_confirm_post", fn.name
                seen_second_step = True
            if fn.name == "pipelines_post":
                assert not called & {"register_site_pipeline", "remove_site_pipeline", "reload_site_inventory"}
                assert "site_pipeline_inventory" in called and "check_site_pipeline_change" in called
    assert seen_second_step


def test_k04_nothing_secret_in_the_log(w, ann, caplog):
    # K04
    feed(w, OK_INV)
    c = login(w, "ann")
    with caplog.at_level("DEBUG"):
        post_pick(c)
        post_pick(c, pick="nf-core/ampliseq 9.9.9")
        c.post("/settings/inventory-nope", data={})
    text = caplog.text
    for secret in (c.cookies.get("abf_session") or "zzzz", tok(c, "settings-pipeline")):
        assert secret not in text


def test_the_pinned_cloud_types():
    # D01 (web_settings may not import compute_envs, so it holds the three names itself: they must stay the platform's own)
    from abf_platform import compute_envs, web_settings
    assert tuple(web_settings.CLOUD_TYPES) == tuple(t for t in compute_envs.PLATFORM_HOST_TYPES if t != compute_envs.K8S) == CLOUD_PLATFORMS
