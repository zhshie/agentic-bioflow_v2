# Nothing existing: tests of guided-launch-1 (the /launch page as seven numbered steps, DESIGN.md v2 screen 5); the page and the read are ours.
"""guided-launch-1: /launch as seven numbered steps, offline. The test cases are named in the comments (TC-001 ...); they are in
specs/guided-launch-1. Runs are launched through the real actions (resume_harness.Rig), not seeded."""
import html
import json
import re
import sqlite3

import pytest

from helpers import tool_json
from resume_harness import Rig
from test_web_actions import area_sheet, form_values, login, pending, rid_of, snapshot
from test_web_board import no_cjk


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


def steps(text):
    """{n: {state, open, html}} for the seven <details> blocks of the page."""
    out = {}
    for m in re.finditer(r'<details class="gstep is-(\w+)" data-step="(\d)" data-state="\w+"( open)?>(.*?)</details>', text, re.S):
        out[int(m.group(2))] = {"state": m.group(1), "open": bool(m.group(3)), "html": m.group(4)}
    return out


def current(text):
    return [n for n, s in steps(text).items() if s["state"] == "current"]


def set_env(rig, name, status=None, message=None, config=None):
    con = sqlite3.connect(str(rig.state))
    with con:
        if status is not None:
            con.execute("UPDATE compute_envs SET status = ? WHERE name = ?", (status, name))
        if message is not None:
            con.execute("UPDATE compute_envs SET message = ? WHERE name = ?", (message, name))
        if config is not None:
            row = con.execute("SELECT config_json FROM compute_envs WHERE name = ?", (name,)).fetchone()
            merged = dict(json.loads(row[0]), **config)
            con.execute("UPDATE compute_envs SET config_json = ? WHERE name = ?", (json.dumps(merged), name))
    con.close()


def drop_key(rig, name, key):
    con = sqlite3.connect(str(rig.state))
    with con:
        row = con.execute("SELECT config_json FROM compute_envs WHERE name = ?", (name,)).fetchone()
        cfg = json.loads(row[0])
        cfg.pop(key, None)
        con.execute("UPDATE compute_envs SET config_json = ? WHERE name = ?", (json.dumps(cfg), name))
    con.close()


def launched(rig, caller, run, pipeline="nf-core/ampliseq", **kw):
    rig.first(run, caller=caller, samplesheet=area_sheet(rig.w, caller), status="failed", pipeline=pipeline, **kw)
    return "id-" + run


def launched_by_other(rig, caller, run, pipeline="nf-core/bobseq", params=None):
    """A launch of a person who is not the owner of lab-a: on their own environment."""
    from abf_launch import build
    from abf_platform import actions
    ce_name = rig.w.env_for(caller)
    ce, bundle = build.prepare_launch(rig.state, ce=ce_name, pipeline=pipeline, revision="2.18.0", run_name=run,
                                      samplesheet=str(area_sheet(rig.w, caller)), params=params or {}, owner=caller.user_id)
    _, job_id = actions.launch(rig.state, ce, bundle, confirmed_by=actions.TERMINAL, caller=caller)
    rig.hand_over(job_id, run)
    rig.set_run(run, "failed")


def ready(rig, name="ann"):
    user = rig.user(name)
    area_sheet(rig.w, user)
    return user, login(rig, name)


SEL = "/launch?pipeline=nf-core/ampliseq&revision=2.18.0"


def test_gl01_seven_numbered_steps(rig):
    # TC-001, TC-002, TC-003, TC-009
    _, c = ready(rig)
    t = c.get("/launch").text
    s = steps(t)
    assert sorted(s) == [1, 2, 3, 4, 5, 6, 7]
    assert re.findall(r'<summary><span class="gno">(\d)</span>', t) == list("1234567")
    titles = re.findall(r'<span class="gttl">([^<]+)</span>', t)
    assert len(titles) == 7 and len(set(titles)) == 7
    assert current(t) == [2] and s[2]["open"] and [n for n in s if s[n]["open"]] == [2]
    assert "選定管線後檢查" in s[1]["html"] and s[1]["state"] != "current"
    assert s[3]["state"] == "later" and "選定管線與版本後顯示" in s[3]["html"]      # guided-launch-2: was 之後開放
    assert all(s[n]["state"] == "later" and not s[n]["open"] for n in (4, 5, 6, 7))


def test_gl01b_one_current_step_and_symbols(rig):
    # TC-004, TC-005
    ann, c = ready(rig)
    rid = launched(rig, ann, "run-a")
    for url in ("/launch", SEL, "/launch?from=" + rid):
        t = c.get(url).text
        s = steps(t)
        assert len(current(t)) == 1 and [n for n in s if s[n]["open"]] == current(t), url
    s = steps(c.get(SEL).text)
    for n, state, sym, word in ((2, "done", "✓", "已完成"), (4, "current", "●", "目前"), (5, "later", "○", "之後")):
        assert s[n]["state"] == state
    t = c.get(SEL).text
    for n, sym, word in ((2, "✓", "已完成"), (4, "●", "目前"), (5, "○", "之後")):
        head = re.search(r'<details class="gstep[^>]*data-step="%d"[^>]*>\s*<summary>.*?<span class="gstate">([^<]*)</span>' % n, t, re.S).group(1)
        assert sym in head and word in head


def test_gl01c_state_comes_from_the_address_only(rig):
    # TC-007
    _, c = ready(rig)
    before = (rig.sql("SELECT count(*) FROM confirmations")[0][0], rig.counts())
    a = c.get(SEL)
    b = c.get(SEL)
    other = login(rig, "ann").get(SEL)
    assert a.text == b.text and [s["state"] for s in steps(a.text).values()] == [s["state"] for s in steps(other.text).values()]
    assert "set-cookie" not in b.headers
    assert (rig.sql("SELECT count(*) FROM confirmations")[0][0], rig.counts()) == before


def test_gl02_used_before_lists_own_launches_newest_first(rig):
    # TC-020, TC-021, TC-022, TC-023, TC-024, TC-025, TC-026, TC-027, TC-028
    ann, bob = rig.user("ann"), rig.user("bob")
    area_sheet(rig.w, ann)
    launched(rig, ann, "run-r1")
    launched(rig, ann, "run-r2", pipeline="nf-core/rnaseq")
    launched(rig, ann, "run-r1b")
    launched_by_other(rig, bob, "run-bob")
    c = login(rig, "ann")
    t = c.get("/launch?src=used").text
    rows = re.findall(r'<tr class="urow">(.*?)</tr>', t, re.S)
    assert len(rows) == 2
    assert "run-r1b" in rows[0] and "run-r1<" not in rows[0] and "rnaseq" in rows[1]
    assert "bobseq" not in t and "run-bob" not in t
    heads = re.findall(r"<th[^>]*>([^<]*)</th>", re.search(r'<table class="tbl used">.*?</table>', t, re.S).group(0))
    assert heads == ["管線", "版本", "上次分析名稱", "上次送出時間", "運算環境"]
    first = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", rows[0], re.S)]
    assert len(first) == 5 and all(first)
    links = [html.unescape(h) for h in re.findall(r'href="([^"]+)"', rows[0])]
    assert "/launch?pipeline=nf-core/ampliseq&revision=2.18.0" in links and "/launch?from=run-r1b" in links
    assert "沿用設定重新分析" in rows[0]      # guided-launch-2b: was the lightning-bolt label
    bt = login(rig, "bob").get("/launch?src=used").text
    assert "bobseq" in bt and "run-r1" not in bt
    assert 'data-tab="used" aria-current' in c.get("/launch").text
    assert 'data-tab="new" aria-current' in c.get("/launch?src=new").text
    from abf_platform import actions
    assert actions.forget(rig.state, rig.index, "run-r2", confirmed_by=actions.TERMINAL, caller=ann)["forgotten"] is True
    assert "rnaseq" not in c.get("/launch?src=used").text


def test_gl02b_no_used_pipeline_opens_the_new_tab(rig):
    # TC-025, TC-029, TC-141
    _, c = ready(rig)
    t = c.get("/launch").text
    assert 'data-tab="new" aria-current' in t
    new = steps(t)[2]["html"]
    assert 'method="get"' not in t and re.search(r'<form class="lform" method="post" action="/launch">.*name="pipeline"', t, re.S)      # guided-launch-2b: the two boxes are in the one form
    assert re.search(r'<input [^>]*name="pipeline"', new) and re.search(r'<input [^>]*name="revision"[^>]*required', new)
    assert "搜尋全部 nf-core（尚未開放）" in new and 'type="search"' not in new


def test_gl02c_values_are_escaped(rig):
    # TC-031
    _, c = ready(rig)
    t = c.get("/launch", params={"pipeline": '"><script>x</script>', "revision": "<b>1</b>"}).text
    assert "<script" not in t and "<b>1</b>" not in t


def test_gl02d_table_comes_from_the_action(rig, monkeypatch):
    # TC-032
    from abf_platform import actions
    fake = {"pipelines": [{"pipeline": "nf-core/fakeone", "revision": "1.0", "run_name": "fake-run-1", "launched_at": 1.0, "ce_name": "ce-x"},
                          {"pipeline": "nf-core/faketwo", "revision": "2.0", "run_name": "fake-run-2", "launched_at": 2.0, "ce_name": "ce-y"}]}
    monkeypatch.setattr(actions, "list_used_pipelines", lambda *a, **k: fake)
    _, c = ready(rig)
    t = c.get("/launch?src=used").text
    assert len(re.findall(r'<tr class="urow">', t)) == 2 and "fake-run-1" in t and "ce-y" in t


def test_gl03_select_marks_step2_done_and_runs_prechecks(rig):
    # TC-006, TC-030, TC-040, TC-041
    _, c = ready(rig)
    t = c.get(SEL).text
    s = steps(t)
    assert s[2]["state"] == "done" and not s[2]["open"] and "nf-core/ampliseq" in s[2]["html"] and "2.18.0" in s[2]["html"]
    assert s[3]["state"] == "later" and current(t) == [4]
    assert len(re.findall(r'<li class="chk (\w+)">', s[1]["html"])) == 5      # guided-launch-2: was 4, the parameter-table row is a real row now
    for word in ("版本已指定", "站台連線", "管線已登記", "有可用樣本表", "讀取管線參數表"):
        assert word in s[1]["html"]
    assert "讀取中" in s[1]["html"]      # guided-launch-2: was 之後開放, the row reads while the agent has not answered
    assert not re.search(r'<li class="chk', steps(c.get("/launch").text)[1]["html"])


def check_of(text, label):
    m = re.search(r'<li class="chk (\w+)"><span class="csym">([^<]*)</span> <span class="clabel">%s</span>(.*?)</li>' % label, steps(text)[1]["html"], re.S)
    return m.group(2), m.group(3)


def test_gl04_registered_check(rig):
    # TC-042, TC-043, TC-044
    _, c = ready(rig)
    set_env(rig, "lab-a", config={"sitePipelines": [{"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "module": "m", "home": "/h"}]})
    assert check_of(c.get(SEL + "&ce_name=lab-a").text, "管線已登記")[0] == "✓"
    assert check_of(c.get("/launch?pipeline=nf-core/ampliseq&revision=9.9.9&ce_name=lab-a").text, "管線已登記")[0] == "✗"
    drop_key(rig, "lab-a", "sitePipelines")
    sym, rest = check_of(c.get(SEL + "&ce_name=lab-a").text, "管線已登記")
    assert sym == "—" and "此環境不需登記" in rest


def test_gl05_site_connection_check(rig):
    # TC-045, TC-046, TC-047, TC-048, TC-049
    _, c = ready(rig)
    set_env(rig, "lab-a", status="available")
    assert check_of(c.get(SEL + "&ce_name=lab-a").text, "站台連線")[0] == "✓"
    set_env(rig, "lab-a", status="invalid", message="agent offline since noon")
    sym, rest = check_of(c.get(SEL + "&ce_name=lab-a").text, "站台連線")
    assert sym == "✗" and "agent offline since noon" in rest
    assert check_of(c.get(SEL).text, "版本已指定")[0] == "✓" and check_of(c.get("/launch?pipeline=nf-core/ampliseq").text, "版本已指定")[0] == "✗"
    assert check_of(c.get(SEL).text, "有可用樣本表")[0] == "✓"
    rig.user("carl")
    assert check_of(login(rig, "carl").get(SEL).text, "有可用樣本表")[0] == "✗"


def test_gl05b_other_peoples_environment_is_not_used(rig):
    # TC-053
    _, c = ready(rig)
    bob = rig.user("bob")
    rig.w.env_for(bob)
    assert "lab-bob" not in c.get(SEL + "&ce_name=lab-bob").text


def test_gl06_quick_launch_prefills_and_goes_to_first_open_step(rig):
    # TC-060, TC-061, TC-062, TC-064
    ann, c = ready(rig)
    rig.user("bob")
    rid = launched(rig, ann, "run-a")
    t = c.get("/launch?from=" + rid).text
    s = steps(t)
    assert [s[n]["state"] for n in (1, 2, 5, 6)] == ["done"] * 4 and s[3]["state"] == "later" and current(t) == [4]
    assert "已帶入該次分析的設定" in t
    assert not re.search(r'<input [^>]*name="run_name"[^>]*value="[^"]', t)
    t2 = c.get("/launch?from=%s&samplesheet=samples.csv" % rid).text
    assert current(t2) == [7] and "primer: AGRG" in html.unescape(steps(t2)[7]["html"])
    by_name = c.get("/launch?from=run-a")
    assert by_name.status_code == 200 and current(by_name.text) == [4]
    theirs = login(rig, "bob")
    a, b = theirs.get("/launch?from=" + rid), theirs.get("/launch?from=nope")
    assert a.status_code == 404 and (a.status_code, a.content) == (b.status_code, b.content)


def box_of(t):
    return html.unescape(re.search(r'<textarea [^>]*name="params"[^>]*>(.*?)</textarea>', t, re.S).group(1))


def test_gl07_param_routes(rig):
    # TC-065, TC-066, TC-067, TC-068, TC-069, TC-070, TC-071, TC-072, TC-073
    ann, c = ready(rig)
    bob = rig.user("bob")
    launched(rig, ann, "run-a", params={"a": 1})
    launched(rig, ann, "run-b", params={"a": 2})
    launched(rig, ann, "run-o", pipeline="nf-core/rnaseq")
    launched_by_other(rig, bob, "run-bob", params={"secret": "zzz"})
    base = SEL + "&ce_name=lab-a&samplesheet=samples.csv"
    five = steps(c.get(base).text)[5]["html"]
    assert 'name="route"' not in five and '<option value="">不沿用</option>' in five      # guided-launch-2b: no radio, the first option is "do not reuse"
    reuse = re.findall(r'<option value="([^"]*)"', re.search(r'<select name="params_from">.*?</select>', five, re.S).group(0))
    assert sorted(x for x in reuse if x) == ["run-a", "run-b"]
    t = c.get(base + "&params_from=run-a").text
    assert "a: 1" in box_of(t) and 'value="nf-core/ampliseq"' in steps(t)[2]["html"] and '<option value="samples.csv" selected>' in steps(t)[4]["html"]      # guided-launch-2b: the choices are in the boxes of steps 2 and 4 (was: hidden fields of step 7)
    assert "已帶入該次分析的設定" not in t
    assert box_of(c.get(base + "&route=defaults&params_from=run-a").text) == box_of(c.get(base + "&params_from=run-a").text)      # guided-launch-2b: `route` is ignored
    assert box_of(c.get(base + "&route=custom&params=x%3A+1%0Ay%3A+2").text) == "x: 1\ny: 2"
    assert "讀取中" in steps(c.get(base).text)[5]["html"] and "尚未開放" not in steps(c.get(base).text)[5]["html"]      # guided-launch-2: was 之後開放
    for bad in ("run-bob", "nope"):
        t = c.get(base + "&params_from=" + bad).text
        assert "此分析的參數無法沿用。" in t and box_of(t) == "" and "zzz" not in t
    assert "此分析的參數無法沿用。" in c.get("/launch?pipeline=nf-core/ampliseq&revision=9.9.9&params_from=run-a").text
    assert "此分析的參數無法沿用。" in c.get(SEL + "&params_from=run-o").text
    en = c.get(base + "&params_from=run-bob&lang=en").text
    assert "The parameters of this analysis cannot be reused." in en and no_cjk(en)


def test_gl08_post_unchanged(rig):
    # TC-085, TC-050, TC-084, TC-051
    ann, c = ready(rig)
    t = c.get(SEL).text
    seven = steps(t)[7]["html"]
    assert re.search(r'<form class="lform" method="post" action="/launch"><input type="hidden" name="csrf"', t)      # guided-launch-2b: the one form holds all the steps
    assert 'name="run_name"' in seven and all('name="run_name"' not in steps(t)[n]["html"] for n in range(1, 7))
    before = pending(rig)
    rid = rid_of(c.post("/launch", data=form_values(rig, c, "ann", params="min_reads: 100")))
    assert pending(rig) == before + 1
    from abf_platform import actions
    req = actions.describe_request(rig.state, rid)
    for word in ("nf-core/ampliseq", "2.18.0", "web-run", "min_reads", "100"):
        assert word in req["summary"], word


def test_gl08b_a_failed_check_does_not_stop_the_page_only_the_action_decides(rig):
    # TC-050, TC-051: the page lists the failed check in step 7 and still posts; the action (as before) is the one that refuses
    _, c = ready(rig)
    set_env(rig, "lab-a", config={"sitePipelines": [{"pipeline": "nf-core/ampliseq", "revision": "1.0.0", "module": "m", "home": "/h"}]})
    t7 = steps(c.get(SEL + "&samplesheet=samples.csv&ce_name=lab-a").text)[7]["html"]
    assert "管線已登記" in t7 and "✗" in t7 and 'method="post" action="/launch"' in c.get(SEL).text
    before = pending(rig)
    r = c.post("/launch", data=form_values(rig, c, "ann"))
    assert r.status_code == 400 and "未送出" in r.text and pending(rig) == before and current(r.text) == [7]


def test_gl09_post_error_rerenders_at_the_failing_step(rig):
    # TC-090, TC-091, TC-092, TC-094
    _, c = ready(rig)
    before = (pending(rig), snapshot(rig))
    r = c.post("/launch", data=form_values(rig, c, "ann", run_name="", params="min_reads: 100"))
    assert r.status_code == 400
    s = steps(r.text)
    assert current(r.text) == [7] and s[7]["open"] and "min_reads: 100" in html.unescape(s[7]["html"])
    assert 'value="nf-core/ampliseq"' in s[2]["html"]      # guided-launch-2b: the pair is in the boxes of step 2 (was: hidden fields of step 7)
    assert (pending(rig), snapshot(rig)) == before
    r = c.post("/launch", data=form_values(rig, c, "ann", run_name="", samplesheet="nope.csv", params="oops"))
    assert r.status_code == 400 and current(r.text) == [4]
    assert "Traceback" not in r.text and "args_json" not in r.text
    r = c.post("/launch", data=form_values(rig, c, "ann", params="oops"))
    assert r.status_code == 400 and current(r.text) == [5]


def test_gl09b_cross_user_post_is_refused(rig):
    # TC-093
    rig.user("ann")
    bob = rig.user("bob")
    cb = login(rig, "bob")
    rig.w.env_for(bob)
    area_sheet(rig.w, bob, "bob-sheet.csv")
    before = pending(rig)
    assert cb.post("/launch", data=form_values(rig, cb, "bob", samplesheet="samples.csv")).status_code == 400
    assert cb.post("/launch", data=form_values(rig, cb, "bob", ce_name="lab-a")).status_code == 400
    assert pending(rig) == before


def test_gl10_no_samplesheet_notice(rig):
    # TC-080, TC-081, TC-082
    ann = rig.user("ann")
    c = login(rig, "ann")
    s = steps(c.get(SEL).text)
    assert "沒有可用的樣本表。" in s[4]["html"] and "尚未上傳樣本表" in s[4]["html"] and "<option" not in s[4]["html"]
    bob = rig.user("bob")
    area_sheet(rig.w, ann, "ann-sheet.csv")
    area_sheet(rig.w, bob, "bob-sheet.csv")
    rig.w.env_for(bob)
    s = steps(c.get(SEL).text)
    assert "ann-sheet.csv" in s[4]["html"] and "bob-sheet.csv" not in s[4]["html"] and "尚未開放" in s[4]["html"]
    assert re.search(r'<option value="lab-a"[^>]*>[^<]*✓', s[6]["html"]) and "lab-bob" not in s[6]["html"]


def test_gl11_english(rig):
    # TC-012, TC-013, TC-125
    ann, c = ready(rig)
    rid = launched(rig, ann, "run-a")
    t = c.get("/launch?lang=en").text
    assert re.findall(r'<span class="gttl">([^<]+)</span>', t) == [
        "Pre-checks", "Pipeline", "Workflow diagram", "Samplesheet", "Parameters", "Compute environment", "Confirm"]
    assert "Previously used pipelines" in t and "Other nf-core pipelines" in t and "Re-run with the same settings" in t
    five = steps(c.get(SEL + "&lang=en").text)[5]["html"]
    assert 'name="route"' not in five and not any(x in five for x in ("①", "②", "③"))      # guided-launch-2b: the three routes are gone
    for url in ("/launch?lang=en", SEL + "&lang=en", "/launch?from=%s&lang=en" % rid, SEL + "&params_from=nope&lang=en"):
        assert no_cjk(c.get(url).text), url
    r = c.post("/launch", data=form_values(rig, c, "ann", run_name="", lang="en"))
    assert r.status_code == 400 and no_cjk(r.text)
    rig.user("zed")
    assert no_cjk(login(rig, "zed").get(SEL + "&lang=en").text)


def test_gl12_constraints_hold(rig):
    # TC-120, TC-121, TC-122, TC-124
    from abf_platform import web_board
    ann, c = ready(rig)
    rid = launched(rig, ann, "run-a")
    pages = []
    for lang in ("", "&lang=en"):
        for url in ("/launch?x=1", SEL, "/launch?from=" + rid, SEL + "&params_from=nope", SEL + "&params_from=run-a"):
            pages.append(c.get(url + lang))
        pages.append(c.post("/launch", data=form_values(rig, c, "ann", run_name="")))
    for r in pages:
        t = r.text
        assert "<script" not in t and not re.search(r"\son\w+=", t) and "style=" not in t and len(re.findall(r"<style\b", t)) == 1 and "<link" not in t
        csp = r.headers["content-security-policy"]
        assert web_board.style_source() in csp and "script-src" not in csp and "'unsafe-inline'" not in csp
        assert "<img" not in t and "<svg" not in t
    zh, en = web_board.STRINGS["zh"], web_board.STRINGS["en"]
    for key, text in zh.items():
        if key.startswith("g_"):
            assert "我" not in text and "你可以試試" not in text, key
    for key, text in en.items():
        if key.startswith("g_"):
            assert not re.search(r"\bI\b|you could try", text), key
    assert {k for k in zh if k.startswith("g_")} == {k for k in en if k.startswith("g_")}


def test_gl12b_fields_are_the_known_ones(rig):
    # TC-010
    ann, c = ready(rig)
    launched(rig, ann, "run-a")
    known = {"csrf", "lang", "pipeline", "revision", "run_name", "samplesheet", "ce_name", "params", "src", "from", "params_from", "ce",
             "shown_pipeline", "shown_revision", "shown_params_from"}      # guided-launch-2b: `route` is gone, the three `shown_*` are new
    for r in (c.get("/launch"), c.get(SEL), c.post("/launch", data=form_values(rig, c, "ann", run_name=""))):
        assert set(re.findall(r'<(?:input|select|textarea) [^>]*name="(\w+)"', r.text)) <= known


def test_gl13_list_used_pipelines_action_and_mcp_match(rig):
    # TC-100, TC-101, TC-102, TC-104, TC-105, TC-106, TC-107, TC-109
    from abf_platform import actions
    ann, bob = rig.user("ann"), rig.user("bob")
    launched(rig, ann, "run-r1")
    launched(rig, ann, "run-r2", pipeline="nf-core/rnaseq")
    launched(rig, ann, "run-r1b")
    got = actions.list_used_pipelines(rig.state, caller=ann)
    assert list(got) == ["pipelines"] and [p["run_name"] for p in got["pipelines"]] == ["run-r1b", "run-r2"]
    assert all(set(p) == {"pipeline", "revision", "run_name", "launched_at", "ce_name"} for p in got["pipelines"])
    assert actions.list_used_pipelines(rig.state, caller=bob) == {"pipelines": []}
    before = rig.counts()
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE jobs SET args_json = '{}'")
    con.close()
    assert [p["pipeline"] for p in actions.list_used_pipelines(rig.state, caller=ann)["pipelines"]] == ["nf-core/ampliseq", "nf-core/rnaseq"]
    assert rig.counts() == before
    tools, _ = rig.w.mcp([])
    tool = [t for t in tools if t.name == "list_used_pipelines"]
    assert len(tool) == 1 and tool[0].annotations.read_only_hint is True
    assert tool_json(rig.w.call("list_used_pipelines", {}, caller=ann)) == actions.list_used_pipelines(rig.state, caller=ann)
    assert tool_json(rig.w.call("list_used_pipelines", {}, caller=bob)) == {"pipelines": []}
    assert actions.forget(rig.state, rig.index, "run-r2", confirmed_by=actions.TERMINAL, caller=ann)["forgotten"] is True
    assert [p["run_name"] for p in actions.list_used_pipelines(rig.state, caller=ann)["pipelines"]] == ["run-r1b"]


def test_gl13b_limit_is_twenty(rig):
    # TC-103
    from abf_platform import actions
    ann = rig.user("ann")
    for i in range(22):
        launched(rig, ann, "run-%02d" % i, pipeline="nf-core/p%02d" % i)
    got = actions.list_used_pipelines(rig.state, caller=ann)["pipelines"]
    assert len(got) == 20 and got[0]["run_name"] == "run-21" and got[-1]["run_name"] == "run-02"
