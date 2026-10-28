# Nothing existing: tests of registering and removing pipeline versions from the settings page (specs/settings-register-pipeline); the two-step page and its limits are ours.
"""settings-register-pipeline: the write actions, the two-step web form (POST /settings/pipelines then /settings/pipelines/confirm), the
notices and the words. Test cases are named in the comments (A01 ... K07 of specs/settings-register-pipeline/test-case.md)."""
import ast
import hashlib
import json
import re
import socket

import pytest

from helpers import PLATFORM_DIR
from human_harness import World
from test_web_board import login, pane
from test_web_settings import make_agent, make_env, sql

PKG = PLATFORM_DIR / "abf_platform"
BASE_STYLE_SHA = "66b9a8e1a9c6f7d21872668edd5f10a2525c760e44b0e68a7cbeea030a33b862"      # sha256 of web_board.STYLE before this task
GOOD = {"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "module": "biology/nf-core-ampliseq/2.18.0", "home": "NFCORE_AMPLISEQ_HOME"}
OTHER_OLD = {"pipeline": "nf-core/rnaseq", "revision": "3.14.0", "module": "biology/nf-core-rnaseq/3.14.0", "home": "NFCORE_RNASEQ_HOME"}
FORBIDDEN = ["用過", "選好", "寫死", "自己填", "自己調整", "你還沒", "還沒有", "還不能", "這個", "這份", "這條", "這一版", "一下", "弄", "搞", "東西",
             "喔", "啦", "吧", "囉", "蠻", "超"]
CJK = re.compile("[　-鿿＀-￯]")
EMPTY_HINT_ZH = "此環境目前未登記管線：送出時直接取用 nf-core 官方版本。登記第一筆後，只能送出已登記的管線版本。"
EMPTY_HINT_EN = ("No pipelines are registered here: runs use the nf-core release directly. "
                 "Once you register one, only registered pipeline versions can be run here.")
NOTICES = {
    "added_queued": ("✓", "已登記，並已排入使用前檢查。", "Registered. A pre-use check has been queued."),
    "added_no_agent": ("✓", "已登記。站台代理目前離線，使用前檢查將於代理上線後執行。",
                       "Registered. The site agent is offline; the pre-use check will run when it connects."),
    "added_not_checkable": ("✓", "已登記。此運算環境類型不執行使用前檢查。", "Registered. This type of compute environment has no pre-use check."),
    "removed": ("✓", "已移除。", "Removed."),
    "gone": ("○", "此管線版本已不在清單中。", "This pipeline version is no longer registered."),
    "added_check_refused": ("✓", "已登記。使用前檢查未能排入，請稍後於設定頁重新登記以再次檢查。",
                            "Registered. The pre-use check could not be queued; register it again later on the Settings page to retry."),
}


@pytest.fixture
def w(tmp_path, monkeypatch):
    from abf_platform import compute_envs
    world = World(tmp_path, monkeypatch)
    world.base_env = compute_envs.get(world.ip.state_db, "lab-a")
    return world


@pytest.fixture
def ann(w):
    return w.user("ann")


# ---- helpers ------------------------------------------------------------------------------------------------------------------------

def snapshot(w):
    return ([tuple(r) for r in w.sql("SELECT * FROM compute_envs ORDER BY id")], [tuple(r) for r in w.sql("SELECT * FROM jobs ORDER BY id")])


def entries(w, ce="lab-a"):
    row = w.sql("SELECT config_json FROM compute_envs WHERE name = ?", (ce,))
    return json.loads(row[0][0]).get("sitePipelines", []) if row else None


def set_entries(w, items, ce="lab-a"):
    cfg = json.loads(w.sql("SELECT config_json FROM compute_envs WHERE name = ?", (ce,))[0][0])
    cfg["sitePipelines"] = items
    sql(w, "UPDATE compute_envs SET config_json = ? WHERE name = ?", (json.dumps(cfg, sort_keys=True), ce))


def preflights(w):
    return len(w.sql("SELECT id FROM jobs WHERE kind = 'preflight'"))


def register(w, caller, ce="lab-a", by="PAGE", raw=False, **over):
    from abf_platform import actions
    f = dict(GOOD, **over)
    return actions.register_site_pipeline(w.ip.state_db, ce=ce, confirmed_by=(getattr(actions, by) if by in ("TERMINAL", "ELICITED", "PAGE") and not raw else by), caller=caller, **f)


def remove(w, caller, ce="lab-a", by="PAGE", raw=False, **over):
    from abf_platform import actions
    f = {k: v for k, v in dict(GOOD, **over).items() if k in ("pipeline", "revision")}
    return actions.remove_site_pipeline(w.ip.state_db, ce=ce, confirmed_by=(getattr(actions, by) if by in ("TERMINAL", "ELICITED", "PAGE") and not raw else by), caller=caller, **f)


def offline_env(w, caller, name="off-ce", platform=None):
    make_agent(w, caller, "agent-off", online=False)
    make_env(w, caller, name, "agent-off", platform=platform)
    return name


def tok(c, purpose):
    from abf_platform import web
    return c.app.state.csrf_token(c.cookies.get(web.COOKIE), purpose)


def digest(f):
    return hashlib.sha256("\n".join(f[k] for k in ("op", "ce", "pipeline", "revision", "module", "home")).encode("utf-8")).hexdigest()


def fields(op="add", ce="lab-a", **over):
    return dict(dict(GOOD, op=op, ce=ce), **over)


def step1(c, f=None, csrf=True, lang=None, headers=None, **over):
    f = dict(f or fields(), **over)
    data = dict(f)
    if csrf is True:
        data["csrf"] = tok(c, "settings-pipeline")
    elif csrf:
        data["csrf"] = csrf
    if lang:
        data["lang"] = lang
    return c.post("/settings/pipelines", data=data, headers=headers or {})


def hidden(html):
    """The hidden inputs of the form that goes to the confirm route."""
    form = re.search(r'<form[^>]*action="/settings/pipelines/confirm"[^>]*>(.*?)</form>', html, re.S)
    assert form, html[:300]
    return {m.group(1): m.group(2) for m in re.finditer(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', form.group(1))}


def hid(text):
    import html as h
    return h.unescape(text)


def confirm_data(page_html):
    return {k: hid(v) for k, v in hidden(page_html).items()}


def step2(c, data):
    return c.post("/settings/pipelines/confirm", data=data)


def signed(c, f):
    return dict(f, csrf=tok(c, "settings-pipeline-confirm:" + digest(f)))


def plain(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def mid_of(html):
    return pane(html, "middle")


def row_block(mid, ce):
    return re.search(r'<div[^>]*id="ce-%s".*?(?=<div[^>]*id="ce-|</section>)' % re.escape(ce), mid, re.S).group(0)


def go(c, f, op="add"):
    """Both steps; returns the response of the second."""
    r = step1(c, f)
    assert r.status_code == 200, r.text
    return step2(c, confirm_data(r.text))


def above(mid, text, ce):
    """`text` appears after the heading, before the anchor of environment `ce`, and after the anchor of no other one."""
    i, a = mid.index(text), mid.index('id="ce-%s"' % ce)
    assert i < a, "the sentence is not above the row"
    assert 'id="ce-' not in mid[i:a], "another environment's row is between"


# ---- 1. the action layer -----------------------------------------------------------------------------------------------------------

def test_a01_register_writes_and_queues_one_preflight(w, ann):
    # A01
    before = preflights(w)
    out = register(w, ann)
    assert out["ok"] is True and out["preflight"] == "queued"
    assert entries(w) == [GOOD] and preflights(w) == before + 1


def test_a02_the_three_human_channels(w, ann):
    # A02
    for i, by in enumerate(("TERMINAL", "ELICITED", "PAGE")):
        assert register(w, ann, by=by, revision="2.%d.0" % (10 + i))["ok"] is True
    assert len(entries(w)) == 3


@pytest.mark.parametrize("bad", ["missing", None, "PAGE", "fake"])
def test_a03_register_refuses_without_a_human_channel(w, ann, bad):
    # A03
    from abf_platform import actions, jobs
    fake = type("Fake", (), {"name": "PAGE"})()
    before = snapshot(w)
    with pytest.raises(jobs.JobRefused, match="no human confirmation channel"):
        if bad == "missing":
            actions.register_site_pipeline(w.ip.state_db, ce="lab-a", caller=ann, **GOOD)
        else:
            register(w, ann, by=fake if bad == "fake" else bad, raw=True)
    assert snapshot(w) == before


@pytest.mark.parametrize("bad", ["missing", None, "PAGE", "fake"])
def test_a04_remove_refuses_without_a_human_channel(w, ann, bad):
    # A04
    from abf_platform import actions, jobs
    register(w, ann)
    fake = type("Fake", (), {"name": "PAGE"})()
    before = snapshot(w)
    with pytest.raises(jobs.JobRefused, match="no human confirmation channel"):
        if bad == "missing":
            actions.remove_site_pipeline(w.ip.state_db, ce="lab-a", caller=ann, pipeline=GOOD["pipeline"], revision=GOOD["revision"])
        else:
            remove(w, ann, by=fake if bad == "fake" else bad, raw=True)
    assert snapshot(w) == before and entries(w) == [GOOD]


def test_a05_same_pair_replaces(w, ann):
    # A05
    register(w, ann, module="m/one")
    register(w, ann, revision="2.17.0")
    out = register(w, ann, module="m/two")
    assert out["ok"] is True
    got = {(e["pipeline"], e["revision"]): e["module"] for e in entries(w)}
    assert len(entries(w)) == 2 and got[("nf-core/ampliseq", "2.18.0")] == "m/two" and got[("nf-core/ampliseq", "2.17.0")] == GOOD["module"]


def test_a06_other_version_adds(w, ann):
    # A06
    register(w, ann)
    register(w, ann, revision="2.17.0")
    assert len(entries(w)) == 2 and GOOD in entries(w)


def test_a07_only_site_pipelines_changes(w, ann):
    # A07
    from abf_platform import compute_envs
    cfg = dict(w.base_env["config"], modules=["biology/x"], siteConfigVars=["FOO_HOME"])
    sql(w, "UPDATE compute_envs SET config_json = ?, description = 'desc' WHERE name = 'lab-a'", (json.dumps(cfg),))
    before = compute_envs.get(w.ip.state_db, "lab-a")
    register(w, ann)
    after = compute_envs.get(w.ip.state_db, "lab-a")
    for k in ("name", "description", "platform", "credentialsId", "agent", "primary"):
        assert after[k] == before[k]
    assert {k: v for k, v in after["config"].items() if k != "sitePipelines"} == {k: v for k, v in before["config"].items() if k != "sitePipelines"}
    assert after["config"]["sitePipelines"] == [GOOD]
    assert w.sql("SELECT owner_user_id FROM compute_envs WHERE name = 'lab-a'")[0][0] == ann.user_id


def test_a08_remove_one_no_preflight(w, ann):
    # A08
    register(w, ann)
    register(w, ann, revision="2.17.0")
    n = preflights(w)
    out = remove(w, ann)
    assert out == {"ok": True, "changed": True} and preflights(w) == n
    assert [e["revision"] for e in entries(w)] == ["2.17.0"]


def test_a09_remove_missing_changes_nothing(w, ann):
    # A09
    register(w, ann)
    before = snapshot(w)
    assert remove(w, ann, **{"pipeline": "nf-core/rnaseq", "revision": "3.14.0"}) == {"ok": True, "changed": False}
    assert snapshot(w) == before


def test_a10_a11_other_users_environment_is_not_found(w, ann):
    # A10, A11
    ben = w.user("ben")
    ce = w.env_for(ben)
    set_entries(w, [GOOD], ce)
    before = snapshot(w)
    one = register(w, ann, ce=ce)
    gone = register(w, ann, ce="no-such-env")
    assert one["ok"] is False and one == gone
    two = remove(w, ann, ce=ce)
    assert two["ok"] is False and two == remove(w, ann, ce="no-such-env")
    assert snapshot(w) == before and entries(w, ce) == [GOOD]


@pytest.mark.parametrize("over,field", [({"module": "biology/../x"}, "module"), ({"home": "nfcore_home"}, "home"), ({"revision": "main"}, "revision")])
def test_a12_clean_errors_name_the_field(w, ann, over, field):
    # A12
    before = snapshot(w)
    out = register(w, ann, **over)
    assert out["ok"] is False and out["field"] == field and ("sitePipelines[0].%s" % field) in out["message"]
    assert snapshot(w) == before


BAD_NAMES = ["acme/rnaseq", "NF-CORE/x", "nf-core/", "nf-core/-x", "nf-core/" + "a" * 65, "nf-core/x\n"]


@pytest.mark.parametrize("name", BAD_NAMES)
def test_a13_bad_pipeline_names(w, ann, name):
    # A13
    before = snapshot(w)
    out = register(w, ann, pipeline=name)
    assert out["ok"] is False and out["field"] == "pipeline"
    assert snapshot(w) == before


@pytest.mark.parametrize("name", ["nf-core/ampliseq", "nf-core/a1-b2", "nf-core/" + "a" * 64])
def test_a14_good_pipeline_names(w, ann, name):
    # A14
    assert register(w, ann, pipeline=name)["ok"] is True


def test_a15_offline_agent(w, ann):
    # A15
    ce = offline_env(w, ann)
    out = register(w, ann, ce=ce)
    assert out["ok"] is True and out["preflight"] == "no_agent" and entries(w, ce) == [GOOD]


def test_a16_type_without_a_check(w, ann):
    # A16
    ce = offline_env(w, ann, platform="lsf-platform")
    n = preflights(w)
    out = register(w, ann, ce=ce)
    assert out["ok"] is True and out["preflight"] == "not_checkable" and entries(w, ce) == [GOOD] and preflights(w) == n


def test_a17_other_refusal(w, ann, monkeypatch):
    # A17
    from abf_platform import jobs

    def refuse(*a, **k):
        raise jobs.JobRefused("the queue is closed for a reason of its own")
    monkeypatch.setattr(jobs, "enqueue_preflight", refuse)
    out = register(w, ann)
    assert out["ok"] is True and out["preflight"] not in ("queued", "no_agent", "not_checkable") and entries(w) == [GOOD]


def test_a18_check_reads_only(w, ann):
    # A18
    from abf_platform import actions
    register(w, ann, revision="2.17.0")
    before = snapshot(w)
    add = actions.check_site_pipeline_change(w.ip.state_db, op="add", ce="lab-a", caller=ann, **GOOD)
    rem = actions.check_site_pipeline_change(w.ip.state_db, op="remove", ce="lab-a", caller=ann, pipeline="nf-core/ampliseq", revision="2.17.0")
    gone = actions.check_site_pipeline_change(w.ip.state_db, op="remove", ce="lab-a", caller=ann, pipeline="nf-core/rnaseq", revision="3.14.0")
    assert add["ok"] is True and not add.get("gone") and rem["ok"] is True and not rem.get("gone")
    assert gone["ok"] is True and gone["gone"] is True
    assert snapshot(w) == before


def test_a19_check_errors(w, ann):
    # A19
    from abf_platform import actions
    ben = w.user("ben")
    ce = w.env_for(ben)
    before = snapshot(w)
    for over, field in (({"module": "a/../b"}, "module"), ({"home": "low"}, "home"), ({"revision": "main"}, "revision"), ({"pipeline": "acme/x"}, "pipeline")):
        got = actions.check_site_pipeline_change(w.ip.state_db, op="add", ce="lab-a", caller=ann, **dict(GOOD, **over))
        assert got["ok"] is False and got["field"] == field
        assert register(w, ann, **over)["message"] == got["message"]
    nf = actions.check_site_pipeline_change(w.ip.state_db, op="add", ce=ce, caller=ann, **GOOD)
    assert nf["ok"] is False and nf == actions.check_site_pipeline_change(w.ip.state_db, op="add", ce="nope", caller=ann, **GOOD)
    assert snapshot(w) == before


def test_a20_cli_prints_the_same_words(w, ann):
    # A20
    rc, out = w.ip.run("ce", "update", "lab-a", "--description=x")
    assert rc == 0 and "preflight queued (預檢已排入); the status changes when the agent has answered" in out
    from abf_platform import cli, compute_envs
    assert not hasattr(cli, "_queue_first_preflight") or callable(cli._queue_first_preflight)
    assert compute_envs.queue_first_preflight


# ---- 2. web step one ---------------------------------------------------------------------------------------------------------------

def test_b01_b02_step_one_shows_six_items_and_writes_nothing(w, ann):
    # B01, B02
    c = login(w, "ann")
    before = snapshot(w)
    r = step1(c)
    assert r.status_code == 200 and snapshot(w) == before
    text = plain(r.text)
    for label in ("新增", "lab-a", GOOD["pipeline"], GOOD["revision"], GOOD["module"], GOOD["home"], "模組名稱", "管線資料夾變數"):
        assert label in text, label
    h = confirm_data(r.text)
    f = fields()
    assert {k: h[k] for k in f} == f
    assert h["csrf"] == tok(c, "settings-pipeline-confirm:" + digest(f))
    assert re.search(r'<button[^>]*type="submit"[^>]*>確認</button>', r.text)
    back = re.search(r'<a[^>]*href="(/settings[^"]*)"[^>]*>返回</a>', r.text)
    assert back and "<button" not in r.text.split("返回")[0].split("確認</button>")[-1][-40:]


def test_b03_remove_step_one(w, ann):
    # B03
    register(w, ann)
    c = login(w, "ann")
    before = snapshot(w)
    r = step1(c, fields("remove"))
    assert r.status_code == 200 and "移除" in plain(r.text) and snapshot(w) == before and entries(w) == [GOOD]
    assert hidden(r.text)["op"] == "remove"


def test_b04_remove_gone_redirects(w, ann):
    # B04
    c = login(w, "ann")
    before = snapshot(w)
    r = step1(c, fields("remove"))
    assert r.status_code == 303 and r.headers["location"] == "/settings?notice=gone&ce=lab-a#ce-lab-a" and snapshot(w) == before
    mid = mid_of(c.get("/settings?notice=gone&ce=lab-a").text)
    assert "○ 此管線版本已不在清單中。" in plain(mid)
    above(mid, "此管線版本已不在清單中。", "lab-a")


FIELD_WORD = {"module": "模組名稱", "home": "管線資料夾變數", "revision": "版本", "pipeline": "管線"}


@pytest.mark.parametrize("over,field,words", [
    ({"module": "biology/../x"}, "module", ["模組名稱"]),
    ({"home": "nfcore_ampliseq_home"}, "home", ["管線資料夾變數", "大寫字母", "數字", "底線"]),
    ({"revision": "main"}, "revision", ["版本", "發行版本", "40 字元", "分支"]),
    ({"pipeline": "acme/rnaseq"}, "pipeline", ["管線"]),
    ({"pipeline": "NF-CORE/x"}, "pipeline", ["管線"]),
])
def test_b05_to_b09_b19_field_errors(w, ann, over, field, words):
    # B05, B06, B07, B08, B09, B19
    c = login(w, "ann")
    before = snapshot(w)
    f = fields(**over)
    r = step1(c, f)
    assert r.status_code == 400 and snapshot(w) == before and "/settings/pipelines/confirm" not in r.text
    mid = mid_of(r.text)
    sentence = [p for p in re.findall(r'<p[^>]*class="bad"[^>]*>(.*?)</p>', mid, re.S) if "✕" in p]
    assert sentence, mid
    s = plain(sentence[0])
    assert s.startswith("✕") and all(x in s for x in words), s
    above(mid, sentence[0], "lab-a")
    for v in f.values():      # what was typed stays in the form
        assert v.replace("&", "&amp;") in mid, v


@pytest.mark.parametrize("blank", ["pipeline", "revision", "module", "home"])
def test_b10_empty_field(w, ann, blank):
    # B10
    c = login(w, "ann")
    before = snapshot(w)
    r = step1(c, fields(**{blank: ""}))
    assert r.status_code == 400 and snapshot(w) == before and "/settings/pipelines/confirm" not in r.text
    assert FIELD_WORD[blank] in plain(mid_of(r.text))


def test_b10_bad_op_and_missing_ce(w, ann):
    # B10
    c = login(w, "ann")
    before = snapshot(w)
    for f in (fields("delete"), fields(""), {k: v for k, v in fields().items() if k != "ce"}, fields(ce="")):
        r = step1(c, f)
        assert r.status_code == 400 and "/settings/pipelines/confirm" not in r.text
    assert snapshot(w) == before


def test_b11_other_users_environment(w, ann):
    # B11
    ben = w.user("ben")
    ce = w.env_for(ben)
    set_entries(w, [GOOD], ce)
    c = login(w, "ann")
    before = snapshot(w)
    answers = []
    for name in (ce, "no-such-env"):
        for op in ("add", "remove"):
            r = step1(c, fields(op, ce=name))
            assert r.status_code == 400 and "/settings/pipelines/confirm" not in r.text and snapshot(w) == before
            mid = mid_of(r.text)
            assert ce not in mid.replace(name, "") or name == ce and False
            sentence = [p for p in re.findall(r'<p[^>]*class="bad"[^>]*>(.*?)</p>', mid, re.S) if "✕" in p][0]
            assert mid.index(sentence) < mid.index('id="setup"')
            answers.append(re.sub(re.escape(name), "X", plain(sentence)))
    assert len(set(answers)) == 1
    assert "lab-ben" not in plain(step1(c, fields(ce=ce)).text)


def test_b12_csrf_failures(w, ann):
    # B12
    c = login(w, "ann")
    before = snapshot(w)
    for token in (False, "wrong", tok(c, "logout")):
        r = step1(c, csrf=token)
        assert r.status_code == 403 and snapshot(w) == before and "/settings/pipelines/confirm" not in r.text
        text = plain(r.text)
        assert "什麼都沒有改" in text and "重新整理" in text


def test_b13_foreign_origin(w, ann):
    # B13
    c = login(w, "ann")
    before = snapshot(w)
    r = step1(c, headers={"origin": "http://evil.example"})
    assert r.status_code == 403 and snapshot(w) == before and "/settings/pipelines/confirm" not in r.text
    r = c.post("/settings/pipelines/confirm", data=signed(c, fields()), headers={"referer": "http://evil.example/x"})
    assert r.status_code == 403 and entries(w) == []


def test_b14_not_logged_in(w, ann):
    # B14
    c = w.web()
    before = snapshot(w)
    for path in ("/settings/pipelines", "/settings/pipelines/confirm"):
        r = c.post(path, data=dict(fields(), csrf="x"))
        assert r.status_code == 303 and r.headers["location"] == "/login"
    assert snapshot(w) == before


def test_b15_temporary_password(w, ann):
    # B15
    from abf_platform import store
    out = store.issue_temporary_password(w.ip.tokens, "ann", now=w.clock.t)
    c = w.web()
    r = w.login(c, "ann", password=out["password"])
    assert r.status_code == 303
    before = snapshot(w)
    for path in ("/settings/pipelines", "/settings/pipelines/confirm"):
        r = c.post(path, data=dict(fields(), csrf="x"))
        assert r.status_code == 303 and r.headers["location"] == "/welcome"
    assert snapshot(w) == before


def test_b16_b17_b18_first_and_last_sentence(w, ann):
    # B16, B17, B18
    c = login(w, "ann")
    assert EMPTY_HINT_ZH in plain(step1(c, fields()).text)
    assert EMPTY_HINT_EN in plain(step1(c, fields(), lang="en").text)
    set_entries(w, [GOOD])
    assert EMPTY_HINT_ZH not in plain(step1(c, fields("add", revision="2.17.0")).text)
    assert EMPTY_HINT_ZH in plain(step1(c, fields("remove")).text)
    set_entries(w, [GOOD, dict(GOOD, revision="2.17.0")])
    assert EMPTY_HINT_ZH not in plain(step1(c, fields("remove")).text)


def test_b20_english_flow(w, ann):
    # B20
    c = login(w, "ann")
    page = c.get("/settings?lang=en")
    assert not CJK.search(mid_of(page.text))
    err = step1(c, fields(home="low"), lang="en")
    assert err.status_code == 400 and not CJK.search(mid_of(err.text))
    r = step1(c, fields(), lang="en")
    assert r.status_code == 200 and not CJK.search(pane(r.text, "middle")) and ">Confirm</button>" in r.text and ">Back</a>" in r.text
    done = step2(c, confirm_data(r.text))
    assert done.status_code == 303 and "lang=en" in done.headers["location"]
    landed = c.get(done.headers["location"])
    assert "✓ Registered. A pre-use check has been queued." in plain(mid_of(landed.text)) and not CJK.search(mid_of(landed.text))


# ---- 3. web step two ---------------------------------------------------------------------------------------------------------------

def test_c01_confirm_writes_and_queues(w, ann):
    # C01
    c = login(w, "ann")
    n = preflights(w)
    r = go(c, fields())
    assert r.status_code == 303 and r.headers["location"] == "/settings?notice=added_queued&ce=lab-a#ce-lab-a"
    assert entries(w) == [GOOD] and preflights(w) == n + 1
    land = c.get(r.headers["location"])
    above(mid_of(land.text), "✓", "lab-a")
    assert "✓ 已登記，並已排入使用前檢查。" in plain(mid_of(land.text))


def test_c02_confirm_remove(w, ann):
    # C02
    register(w, ann)
    c = login(w, "ann")
    n = preflights(w)
    r = go(c, fields("remove"))
    assert r.status_code == 303 and r.headers["location"] == "/settings?notice=removed&ce=lab-a#ce-lab-a"
    assert entries(w) == [] and preflights(w) == n


@pytest.mark.parametrize("key,value", [("op", "remove"), ("ce", "other"), ("pipeline", "nf-core/rnaseq"), ("revision", "2.17.0"), ("module", "m/x"), ("home", "OTHER_HOME")])
def test_c03_changed_hidden_field(w, ann, key, value):
    # C03
    register(w, ann)
    c = login(w, "ann")
    data = confirm_data(step1(c, fields("add", revision="2.16.0")).text)
    before = snapshot(w)
    data[key] = value
    assert step2(c, data).status_code == 403 and snapshot(w) == before


def test_c04_wrong_purpose(w, ann):
    # C04
    c = login(w, "ann")
    before = snapshot(w)
    f = fields()
    assert step2(c, dict(f, csrf=tok(c, "settings-pipeline"))).status_code == 403
    other = fields(revision="2.17.0")
    assert step2(c, dict(f, csrf=tok(c, "settings-pipeline-confirm:" + digest(other)))).status_code == 403
    assert snapshot(w) == before


def test_c05_csrf_and_origin(w, ann):
    # C05
    c = login(w, "ann")
    before = snapshot(w)
    f = fields()
    assert step2(c, f).status_code == 403
    assert step2(c, dict(f, csrf="bad")).status_code == 403
    assert c.post("/settings/pipelines/confirm", data=signed(c, f), headers={"origin": "http://evil.example"}).status_code == 403
    assert snapshot(w) == before


def test_c06_token_is_bound_to_the_session(w, ann):
    # C06
    w.user("ben")
    ca, cb = login(w, "ann"), login(w, "ben")
    data = confirm_data(step1(ca, fields()).text)
    before = snapshot(w)
    assert step2(cb, data).status_code == 403 and snapshot(w) == before


def test_c07_other_users_environment_at_step_two(w, ann):
    # C07
    w.user("ben")
    cb = login(w, "ben")
    before = snapshot(w)
    r = step2(cb, signed(cb, fields()))
    assert r.status_code == 400 and snapshot(w) == before
    mid = mid_of(r.text)
    assert "✕ 未能完成：" in plain(mid) and mid.index("✕") < mid.index('id="setup"') and "lab-a" not in mid


def test_c08_environment_deleted_meanwhile(w, ann):
    # C08
    c = login(w, "ann")
    data = confirm_data(step1(c, fields()).text)
    sql(w, "DELETE FROM compute_envs WHERE name = 'lab-a'")
    r = step2(c, data)
    assert r.status_code == 400 and "✕ 未能完成：" in plain(mid_of(r.text))


def test_c09_clean_refuses_at_step_two(w, ann):
    # C09, N11
    c = login(w, "ann")
    data = confirm_data(step1(c, fields()).text)
    set_entries(w, [dict(GOOD, revision="1.%d.0" % i) for i in range(100)])
    before = snapshot(w)
    r = step2(c, data)
    assert r.status_code == 400 and snapshot(w) == before
    mid = mid_of(r.text)
    s = plain(re.search(r'<p[^>]*class="bad"[^>]*>(.*?)</p>', mid, re.S).group(1))
    assert s.startswith("✕ 未能完成：") and "sitePipelines" in s
    above(mid, "未能完成", "lab-a")
    en = step2(c, dict(data, lang="en"))
    assert "✕ Not completed:" in plain(mid_of(en.text))


def test_c10_removed_elsewhere_meanwhile(w, ann):
    # C10
    register(w, ann)
    c = login(w, "ann")
    data = confirm_data(step1(c, fields("remove")).text)
    set_entries(w, [])
    r = step2(c, data)
    assert r.status_code == 303 and r.headers["location"] == "/settings?notice=gone&ce=lab-a#ce-lab-a" and entries(w) == []


def test_c11_confirm_twice(w, ann):
    # C11
    c = login(w, "ann")
    data = confirm_data(step1(c, fields()).text)
    assert step2(c, data).status_code == 303
    assert step2(c, data).status_code == 303 and entries(w) == [GOOD]


def test_c12_route_passes_the_page_channel(w, ann, monkeypatch):
    # C12
    from abf_platform import actions
    seen = []
    real = actions.register_site_pipeline

    def spy(*a, **k):
        seen.append(k)
        return real(*a, **k)
    monkeypatch.setattr(actions, "register_site_pipeline", spy)
    c = login(w, "ann")
    go(c, fields())
    assert len(seen) == 1 and seen[0]["confirmed_by"] is actions.PAGE and seen[0]["caller"].user_id == ann.user_id


def test_c13_c14_c15_notice_kinds(w, ann, monkeypatch):
    # C13, C14, C15
    c = login(w, "ann")
    off = offline_env(w, ann)
    r = go(c, fields(ce=off))
    assert r.headers["location"] == "/settings?notice=added_no_agent&ce=off-ce#ce-off-ce" and entries(w, off) == [GOOD]
    assert NOTICES["added_no_agent"][1] in plain(mid_of(c.get(r.headers["location"]).text))
    nc = offline_env_nc(w, ann)
    r = go(c, fields(ce=nc))
    assert r.headers["location"] == "/settings?notice=added_not_checkable&ce=%s#ce-%s" % (nc, nc) and entries(w, nc) == [GOOD]
    from abf_platform import jobs

    def refuse(*a, **k):
        raise jobs.JobRefused("closed")
    monkeypatch.setattr(jobs, "enqueue_preflight", refuse)
    r = go(c, fields())
    assert r.headers["location"] == "/settings?notice=added_check_refused&ce=lab-a#ce-lab-a" and entries(w) == [GOOD]


def offline_env_nc(w, ann):
    make_env(w, ann, "nc-ce", "agent-off", platform="lsf-platform")
    return "nc-ce"


# ---- 4. notices --------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("key", list(NOTICES))
def test_n01_to_n06_notice_sentences(w, ann, key):
    # N01 .. N06
    c = login(w, "ann")
    symbol, zh, en = NOTICES[key]
    mid = mid_of(c.get("/settings?notice=%s&ce=lab-a" % key).text)
    assert "%s %s" % (symbol, zh) in plain(mid)
    above(mid, zh, "lab-a")
    assert "%s %s" % (symbol, en) in plain(mid_of(c.get("/settings?notice=%s&ce=lab-a&lang=en" % key).text))


@pytest.mark.parametrize("value", ["bogus", "<script>x</script>", ""])
def test_n07_unknown_notice(w, ann, value):
    # N07
    c = login(w, "ann")
    from urllib.parse import quote
    r = c.get("/settings?notice=%s&ce=lab-a" % quote(value))
    assert r.status_code == 200 and "bogus" not in r.text and "<script>x" not in r.text
    assert not any(z in r.text for _, z, _ in NOTICES.values())


def test_n08_n09_notice_placement(w, ann):
    # N08, N09
    ben = w.user("ben")
    ce = w.env_for(ben)
    c = login(w, "ann")
    assert 'id="ce-lab-a"' in c.get("/settings").text
    for query in ("notice=removed&ce=%s" % ce, "notice=removed&ce=no-such-env", "notice=removed"):
        mid = mid_of(c.get("/settings?" + query).text)
        assert "已移除。" in plain(mid) and mid.index("已移除。") < mid.index('id="setup"') and ce not in mid


def test_n10_get_never_writes(w, ann):
    # N10
    c = login(w, "ann")
    before = snapshot(w)
    for q in ("", "?notice=added_queued&ce=lab-a", "?notice=zz", "?notice=gone"):
        assert c.get("/settings" + q).status_code == 200
    assert snapshot(w) == before


# ---- 5. page and words -------------------------------------------------------------------------------------------------------------

LABELS_ZH = ["管線（例 nf-core/ampliseq）", "版本（例 2.18.0）", "模組名稱（站台 module load 使用的名稱，例 biology/nf-core-ampliseq/2.18.0）",
             "管線資料夾變數（模組設定的環境變數名稱，例 NFCORE_AMPLISEQ_HOME）"]
LABELS_EN = ["Pipeline (e.g. nf-core/ampliseq)", "Version (e.g. 2.18.0)",
             "Module name (the name used by module load on the site, e.g. biology/nf-core-ampliseq/2.18.0)",
             "Pipeline folder variable (the environment variable the module sets, e.g. NFCORE_AMPLISEQ_HOME)"]


def add_form(block):
    return re.search(r'<form[^>]*action="/settings/pipelines"[^>]*>(?:(?!</form>).)*name="op"[^>]*value="add"(?:(?!</form>).)*</form>', block, re.S).group(0)


def test_d01_d02_d04_d06_form_and_labels(w, ann):
    # D01, D02, D04, D06
    make_agent(w, ann, "agent-off", online=False)
    make_env(w, ann, "second-env", "agent-off")
    c = login(w, "ann")
    for lang, labels, legend, req in (("", LABELS_ZH, "* 必填", "必填"), ("?lang=en", LABELS_EN, "* Required", "Required")):
        mid = mid_of(c.get("/settings" + lang).text)
        for ce in ("lab-a", "second-env"):
            block = row_block(mid, ce)
            form = add_form(block)
            text = plain(form)
            for label in labels:
                assert label in text, label
                assert re.search(r"%s <span class=\"req\" title=\"%s\">\*</span>" % (re.escape(label.replace("&", "&amp;")), req), form), label
            assert legend in plain(block) and block.index(legend) < block.index(form)
            assert len(re.findall(r"<input[^>]*\brequired\b", form)) == 4
            for n in ("pipeline", "revision", "module", "home"):
                assert 'name="%s"' % n in form
            assert "已登記管線" not in form
            assert block.index("<form") >= 0


def test_d03_remove_forms(w, ann):
    # D03
    set_entries(w, [GOOD, OTHER_OLD])
    make_agent(w, ann, "agent-off", online=False)
    make_env(w, ann, "second-env", "agent-off")
    c = login(w, "ann")
    mid = mid_of(c.get("/settings").text)
    block = row_block(mid, "lab-a")
    forms = [f for f in re.findall(r'<form[^>]*action="/settings/pipelines"[^>]*>.*?</form>', block, re.S) if 'value="remove"' in f]
    assert len(forms) == 2
    for form, item in zip(forms, (GOOD, OTHER_OLD)):
        for k, v in item.items():
            assert 'name="%s" value="%s"' % (k, v) in form
        assert ">移除</button>" in form
    assert 'value="remove"' not in row_block(mid, "second-env")


def test_d05_button_words(w, ann):
    # D05
    set_entries(w, [GOOD])
    c = login(w, "ann")
    zh = c.get("/settings").text
    buttons = {plain(b) for b in re.findall(r"<button[^>]*>(.*?)</button>", mid_of(zh), re.S)}
    assert buttons <= {"登記", "移除"} and {"登記", "移除"} <= buttons
    en = {plain(b) for b in re.findall(r"<button[^>]*>(.*?)</button>", mid_of(c.get("/settings?lang=en").text), re.S)}
    assert en == {"Register", "Remove"}
    page = step1(c, fields("remove")).text
    assert {plain(b) for b in re.findall(r"<button[^>]*>(.*?)</button>", mid_of(page), re.S)} == {"確認"} and ">返回</a>" in page


def test_d07_d08_empty_list_hint(w, ann):
    # D07, D08
    c = login(w, "ann")
    assert EMPTY_HINT_ZH in plain(row_block(mid_of(c.get("/settings").text), "lab-a"))
    assert EMPTY_HINT_EN in plain(row_block(mid_of(c.get("/settings?lang=en").text), "lab-a"))
    set_entries(w, [GOOD])
    assert EMPTY_HINT_ZH not in plain(mid_of(c.get("/settings").text))


def test_d09_no_environment(w, ann):
    # D09
    sql(w, "DELETE FROM compute_envs")
    r = login(w, "ann").get("/settings")
    assert r.status_code == 200 and "沒有運算環境。" in mid_of(r.text) and "/settings/pipelines" not in r.text


def all_pages(w, ann):
    c = login(w, "ann")
    set_entries(w, [GOOD])
    pages = [c.get("/settings?notice=removed&ce=lab-a").text, c.get("/settings?notice=gone").text,
             step1(c, fields("add", revision="2.1.0")).text, step1(c, fields(home="low")).text,
             step2(c, signed(c, fields(ce="nope"))).text]
    return c, pages


def test_d10_symbol_and_words(w, ann):
    # D10
    c, pages = all_pages(w, ann)
    assert re.search(r"✓</span> 已移除。", pages[0]) and re.search(r"○</span> 此管線版本已不在清單中。", pages[1])
    assert re.search(r"✕</span> [^<]+", pages[3]) and re.search(r"✕</span> 未能完成：[^<]+", pages[4])
    set_entries(w, [])
    assert "此環境目前未登記管線" in plain(c.get("/settings").text)


def test_d11_d12_d13_constraints(w, ann):
    # D11, D12, D13
    from abf_platform import web, web_board
    c, pages = all_pages(w, ann)
    pages.append(c.get("/settings").text)
    for html in pages:
        assert "style=" not in html.replace("<style>", "") and "<script" not in html and not re.search(r"(src|href|action)=\"https?:", html)
        classes = {x for cls in re.findall(r'class="([^"]*)"', mid_of(html)) for x in cls.split()}
        for cls in classes:
            assert "." + cls in web_board.STYLE, cls
    assert hashlib.sha256(web_board.STYLE.encode("utf-8")).hexdigest() == BASE_STYLE_SHA
    reqs = [c.get("/settings"), step1(c, fields("add", revision="2.1.0")), step1(c, fields(home="low")), step1(c, csrf=False),
            step2(c, signed(c, fields())), step2(c, signed(c, fields(ce="nope"))), step2(c, fields())]
    for r in reqs:
        assert r.headers["content-security-policy"] == web._HEADERS["Content-Security-Policy"]
        assert "img-src" not in r.headers["content-security-policy"] and "form-action 'self'" in r.headers["content-security-policy"]
        assert r.headers["cache-control"] == "no-store" and r.headers["x-frame-options"] == "DENY"


def new_keys():
    from abf_platform import web_settings
    return {k for k in web_settings.STRINGS["zh"] if k.startswith("pf_")}, web_settings.STRINGS


def test_d14_d15_words():
    # D14, D15
    from abf_platform import web_board
    keys, strings = new_keys()
    assert len(keys) >= 20
    for k in keys:
        zh, en = strings["zh"][k], strings["en"].get(k)
        assert en and not CJK.search(en), k
        assert not [x for x in FORBIDDEN if x in zh], (k, zh)
    assert not [x for x in FORBIDDEN if x in web_board.STRINGS["zh"]["g_reg_bad"]]
    assert not CJK.search(web_board.STRINGS["en"]["g_reg_bad"])


def test_d14_pages_and_403_have_no_forbidden_words(w, ann):
    # D14
    c, pages = all_pages(w, ann)
    pages += [step1(c, csrf=False).text, step2(c, fields()).text]
    for html in pages:
        text = plain(re.sub(r"<style>.*?</style>", "", html.split('data-pane="right"')[0].split('data-pane="middle"')[-1], flags=re.S))
        text = text.split("營運者後台")[0]      # the greyed sections below were there before this task
        for x in FORBIDDEN:
            assert x not in text, x


def test_d16_only_this_task_has_forms(w, ann):
    # D16
    c = login(w, "ann")
    r = c.get("/settings")
    mid = mid_of(r.text)
    actions = re.findall(r'<form[^>]*action="([^"]+)"', mid)
    assert actions and set(actions) == {"/settings/pipelines"}
    assert r.text.count('action="/logout"') == 1
    assert c.post("/settings", data={"x": "1"}).status_code == 405
    assert w.web().get("/settings").headers["location"].startswith("/login")


def test_d17_each_sees_only_their_own(w, ann):
    # D17
    ben = w.user("ben")
    ce = w.env_for(ben)
    set_entries(w, [GOOD])
    set_entries(w, [OTHER_OLD], ce)
    ma, mb = mid_of(login(w, "ann").get("/settings").text), mid_of(login(w, "ben").get("/settings").text)
    assert "lab-a" in ma and ce not in ma and "nf-core/ampliseq 2.18.0" in plain(ma) and "nf-core/rnaseq 3.14.0" not in plain(ma)
    assert ce in mb and "lab-a" not in mb and "nf-core/rnaseq 3.14.0" in plain(mb) and "nf-core/ampliseq 2.18.0" not in plain(mb)


def test_d18_launch_hint(w, ann):
    # D18, E02
    set_entries(w, [GOOD])
    c = login(w, "ann")
    r = c.get("/launch?pipeline=nf-core/ampliseq&revision=2.17.0&ce_name=lab-a")
    assert "此管線版本尚未在所選運算環境登記，請先至設定頁登記。" in plain(r.text) and 'href="/settings"' in r.text
    en = c.get("/launch?pipeline=nf-core/ampliseq&revision=2.17.0&ce_name=lab-a&lang=en")
    assert ("This pipeline version is not registered on the selected compute environment. Register it on the Settings page first."
            in plain(en.text))


# ---- 6. empty list meaning and /launch ---------------------------------------------------------------------------------------------

def unregistered_shown(c, revision):
    t = plain(c.get("/launch?pipeline=nf-core/ampliseq&revision=%s&ce_name=lab-a" % revision).text)
    return "尚未在所選運算環境登記" in t


def launch_refused_as_unregistered(c, revision):
    r = c.post("/launch", data={"csrf": tok(c, "launch"), "pipeline": "nf-core/ampliseq", "revision": revision, "run_name": "r1",
                                "ce_name": "lab-a", "samplesheet": "none", "shown_pipeline": "nf-core/ampliseq", "shown_revision": revision})
    return "尚未登記此管線版本" in plain(r.text)


def test_e01_e02_e03_e04_launch_follows_the_list(w, ann):
    # E01, E02, E03, E04
    c = login(w, "ann")
    assert not unregistered_shown(c, "2.18.0") and not launch_refused_as_unregistered(c, "2.18.0")
    go(c, fields())
    assert not unregistered_shown(c, "2.18.0") and not launch_refused_as_unregistered(c, "2.18.0")
    assert unregistered_shown(c, "2.17.0") and launch_refused_as_unregistered(c, "2.17.0")
    go(c, fields(revision="2.17.0"))
    assert not unregistered_shown(c, "2.17.0")
    go(c, fields("remove", revision="2.17.0"))
    go(c, fields("remove"))
    assert not unregistered_shown(c, "2.17.0") and not unregistered_shown(c, "2.9.9") and not launch_refused_as_unregistered(c, "2.9.9")


def test_e05_hint_follows_the_list(w, ann):
    # E05
    c = login(w, "ann")
    go(c, fields())
    assert EMPTY_HINT_ZH not in plain(mid_of(c.get("/settings").text))
    go(c, fields("remove"))
    assert EMPTY_HINT_ZH in plain(mid_of(c.get("/settings").text))


# ---- not in scope -------------------------------------------------------------------------------------------------------------------

def test_x01_only_two_new_routes():
    # X01
    tree = ast.parse((PKG / "web.py").read_text(encoding="utf-8"))
    routes = {(n.args[0].value) for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "Route" and n.args
              and isinstance(n.args[0], ast.Constant)}
    assert {"/settings/pipelines", "/settings/pipelines/confirm"} <= routes
    assert not [r for r in routes if "ce" in r.split("/")[-1] and r.startswith("/settings") and r not in ("/settings/pipelines/confirm",)]


def test_x02_no_outgoing_connection(w, ann, monkeypatch):
    # X02
    def no(*a, **k):
        raise AssertionError("an outgoing connection was attempted")
    monkeypatch.setattr(socket.socket, "connect", no)
    monkeypatch.setattr(socket, "create_connection", no)
    n = len(w.sql("SELECT id FROM jobs"))
    c = login(w, "ann")
    go(c, fields())
    go(c, fields("remove"))
    kinds = [r["kind"] for r in w.sql("SELECT kind FROM jobs ORDER BY id")][n:]
    assert kinds == ["preflight"]
    assert "<select" not in c.get("/settings").text


def test_x04_no_new_mcp_tool():
    # X04
    text = (PKG / "mcp_server.py").read_text(encoding="utf-8")
    assert "site_pipeline" not in text and "register_site" not in text


def test_x05_e_reg_unchanged():
    # X05
    from abf_platform import web_board
    assert web_board.STRINGS["zh"]["e_reg"] == "所選運算環境尚未登記此管線版本，無法送出。"
    assert web_board.STRINGS["en"]["e_reg"] == "The selected compute environment has not registered this pipeline version; nothing was sent."


def test_x06_no_migration_and_old_database_works(w, ann):
    # X06
    tables = {r[0]: [tuple(c)[1] for c in w.sql("PRAGMA table_info(%s)" % r[0])] for r in w.sql("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "site_pipelines" not in tables and "pipeline_registrations" not in tables
    assert "sitePipelines" not in " ".join(" ".join(v) for v in tables.values())
    assert not [p for p in (PLATFORM_DIR / "abf_platform").glob("*migrat*") if "pipeline" in p.read_text(encoding="utf-8").lower()]
    c = login(w, "ann")
    assert go(c, fields()).status_code == 303 and go(c, fields("remove")).status_code == 303


# ---- constitution and safety net ----------------------------------------------------------------------------------------------------

def test_k02_only_step_two_calls_the_write_actions():
    # K02
    src = (PKG / "web.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    callers = set()

    def visit(node, inside):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inside = node.name
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") in ("register_site_pipeline", "remove_site_pipeline"):
            callers.add(inside)
        for child in ast.iter_child_nodes(node):
            visit(child, inside)
    visit(tree, None)
    assert callers == {"pipelines_confirm_post"}
    assert "web_settings" not in "".join(l for l in (PKG / "web_settings.py").read_text(encoding="utf-8").splitlines() if "register_site_pipeline" in l)
    assert "register_site_pipeline" not in (PKG / "web_settings.py").read_text(encoding="utf-8")
    handler = re.search(r'Route\("/settings/pipelines/confirm", (\w+)', src)
    assert handler and handler.group(1) == "pipelines_confirm_post"


def test_k03_k04_parity_lists():
    # K03, K04
    from test_web_parity import INTERNAL, WEB_ONLY, FORBIDDEN_IMPORTS
    assert "寫入需在網頁確認頁確認" in WEB_ONLY["register_site_pipeline"] and "寫入需在網頁確認頁確認" in WEB_ONLY["remove_site_pipeline"]
    assert "check_site_pipeline_change" in INTERNAL or "check_site_pipeline_change" in WEB_ONLY
    for name in ("web.py", "web_settings.py"):
        tree = ast.parse((PKG / name).read_text(encoding="utf-8"))
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and (n.module in (None, "") or n.level) for a in n.names}
        assert not (imported & FORBIDDEN_IMPORTS)


def test_k05_k06_failures_say_what_and_leak_nothing(w, ann, caplog):
    # K05, K06
    c = login(w, "ann")
    cookie = c.cookies.get("abf_web")
    pages = []
    for f in (fields(home="low"), fields(module="a/../b"), fields(ce="nope"), fields("remove", ce="nope")):
        pages.append(step1(c, f))
    pages.append(step1(c, csrf=False))
    pages.append(step2(c, fields()))
    pages.append(step2(c, signed(c, fields(ce="nope"))))
    for r in pages:
        text = r.text
        assert plain(text)
        for bad in ("Traceback", 'File "', "SELECT", "sqlite", str(PLATFORM_DIR), cookie):
            assert bad not in text and bad not in caplog.text, bad
        assert len(re.findall(r'name="csrf"', text)) == len(re.findall(r'name="csrf" value="[0-9a-f]{64}"', text))
