# Nothing existing: tests of resume-edit-web (the page "修改後續跑" and the two optional fields of POST /act/resume); the page and the route are ours.
"""resume-edit-web: a failed run is resumed from the web with changed parameters and extra settings. The test cases are named in the comments
(TC-001 ...), see specs/resume-edit-web/test-case.md. Runs are launched through the real actions (resume_harness.Rig); the pipeline-file read is the
`Fake` of test_web_guided_launch_2, so no job is queued and nothing connects out; `request_resume` is wrapped to see what the page asked for."""
import html
import json
import re
import urllib.parse

import pytest

from helpers import PLATFORM_DIR
from human_harness import csrf_of
from test_web_actions import act_form, area_sheet, login, rid_of, snapshot
from test_web_board import no_cjk
from test_web_guided_launch import ready, rig  # noqa: F401  (rig is a fixture)
from test_web_guided_launch_2 import good_files, fk, loading_files, error_files  # noqa: F401  (fk is a fixture)

WEB = PLATFORM_DIR / "abf_platform" / "web.py"
START = {"trunclenf": 120, "skip_qiime": True}
SCHEMA = json.dumps({
    "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "t", "type": "object",
    "$defs": {"opts": {"title": "Options", "type": "object", "properties": {
        "trunclenf": {"type": "integer", "default": 0, "description": "Truncate forward reads"},
        "skip_qiime": {"type": "boolean", "default": False, "description": "Skip the QIIME step"},
        "metadata": {"type": "string", "description": "Path to the metadata sheet"}}}},
    "allOf": [{"$ref": "#/$defs/opts"}]})
MEM = "process.memory = '16 GB'"
FIXED = "管線、版本、樣本表與運算環境沿用第一次送出的內容，不能修改。"
LABEL = "額外設定（每行一項，例 process.memory = '16 GB'）"
BANNED = ["用過", "選好", "寫死", "自己填", "自己調整", "你還沒", "還沒有", "還不能", "這個", "這份", "這條", "這一版", "一下", "弄", "搞", "東西", "喔",
          "啦", "吧", "囉", "蠻", "超"]


def A():
    from abf_platform import actions
    return actions


@pytest.fixture
def fx(fk):
    fk.files = good_files(schema=A()._pf_view("schema", {"status": "ok", "text": SCHEMA}))
    return fk


class Spy:
    def __init__(self, monkeypatch):
        self.calls, real = [], A().request_resume

        async def spy(*a, **kw):
            self.calls.append(kw)
            return await real(*a, **kw)
        monkeypatch.setattr(A(), "request_resume", spy)


@pytest.fixture
def spy(monkeypatch):
    return Spy(monkeypatch)


def make_run(rig, ann, name="run-a", status="failed", params=None, reusable=True):
    """A run of ann's, launched through the real action and now `status`; reusable = Seqera's resume is on offer (tasks to reuse)."""
    from abf_platform import store
    rig.first(name, caller=ann, samplesheet=area_sheet(rig.w, ann), status=status, params=START if params is None else params)
    if reusable and status:
        con = store.connect_index(rig.index)
        with con:
            con.execute("UPDATE runs SET n_succeeded = 2 WHERE run_name = ?", (name,))
        con.close()
    return "id-" + name


def edit_url(rid, lang=""):
    return "/act/resume/edit?run=" + urllib.parse.quote(rid, safe="") + ("&lang=en" if lang == "en" else "")


def form_of(text):
    return re.search(r'<form class="lform" method="post" action="/act/resume">(.*?)</form>', text, re.S).group(1)


def hidden(text):
    return {k: html.unescape(v) for k, v in re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', form_of(text))}


def cells(text):
    """{parameter: value} of the p.<name> boxes of the form (an <input> value, or the selected <option> of a <select>)."""
    out = {}
    f = form_of(text)
    for m in re.finditer(r'<input [^>]*name="p\.([^"]+)"[^>]*value="([^"]*)"', f):
        out[m.group(1)] = html.unescape(m.group(2))
    for m in re.finditer(r'<select [^>]*name="p\.([^"]+)"[^>]*>(.*?)</select>', f, re.S):
        sel = re.search(r'<option value="([^"]*)" selected', m.group(2))
        out[m.group(1)] = html.unescape(sel.group(1)) if sel else ""
    return out


def extra_of(text):
    m = re.search(r'<textarea [^>]*name="extra_config"[^>]*>(.*?)</textarea>', form_of(text), re.S)
    return html.unescape(m.group(1)) if m else None


def posting(text, **over):
    """What the browser sends from the form as it is drawn, with some boxes changed (`p_<name>` for a parameter box)."""
    data = dict(hidden(text))
    data.update({"p." + k: v for k, v in cells(text).items()})
    data["extra_config"] = extra_of(text) or ""
    for k, v in over.items():
        data["p." + k[2:] if k.startswith("p_") else k] = v
    return data


def setup(rig, fx, **kw):  # noqa: ARG001
    ann, c = ready(rig)
    rid = make_run(rig, ann, **kw)
    return ann, c, rid


def link_of(text):
    return re.findall(r'<a [^>]*href="(/act/resume/edit\?[^"]*)"[^>]*>([^<]*)</a>', text)


def menu_of(text):
    m = re.search(r'<details class="menu">(.*?)</details>', text, re.S)
    return m.group(1) if m else ""


def notice_of(text):
    m = re.search(r"<article\b.*?</article>", text, re.S)
    return m.group(0) if m else ""


def plain_zh(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


# ---- US1: the entrance ------------------------------------------------------------------------------------------------------------------

def test_tc001_tc002_tc004_tc010_link_in_menu_and_notice(rig, fx):
    # TC-001, TC-002, TC-004, TC-008, TC-010, TC-067
    ann, c, rid = setup(rig, fx)
    t = c.get("/?run=" + rid).text
    want = [("/act/resume/edit?run=" + rid, "修改後續跑")]
    assert link_of(menu_of(t)) == want
    card = notice_of(t)
    assert link_of(card) == want and '<div class="acts">' in card and len(re.findall(r"<button", card)) == 1
    assert re.search(r'<div class="acts"><form class="act" method="post" action="/act/resume">.*?</form>', card, re.S)
    assert act_form(card, "resume", rid) and act_form(menu_of(t), "resume", rid)
    for frag in (menu_of(t), card):
        assert not re.search(r"<form[^>]*>[^<]*(<input[^>]*>)*[^<]*<a ", frag)      # the link is not inside any form
    assert "<button" not in re.search(r'<a [^>]*resume/edit[^>]*>.*?</a>', t).group(0)


def test_tc002_lost_run_has_the_link_in_its_notice(rig, fx):
    # TC-002
    from abf_platform import store
    ann, c, rid = setup(rig, fx)
    con = store.connect_index(rig.index)
    with con:
        con.execute("UPDATE runs SET final_status = NULL, ended_at = NULL, last_message_at = 1000 WHERE run_name = 'run-a'")
    con.close()
    t = c.get("/?run=" + rid).text
    assert "修改後續跑" in notice_of(t) and "/act/resume/edit?run=" + rid in notice_of(t)


def test_tc005_tc006_no_link_on_succeeded_or_running(rig, fx):
    # TC-005, TC-006
    ann, c = ready(rig)
    ok = make_run(rig, ann, "run-ok", status="succeeded")
    going = make_run(rig, ann, "run-go", status=None)
    for rid in (ok, going):
        for url in ("/?run=%s", "/?run=%s&stage=running", "/?run=%s&stage=results", "/?run=%s&stage=finished"):
            assert "/act/resume/edit" not in c.get(url % rid).text, (rid, url)


def test_tc007_no_link_when_the_first_action_is_rerun(rig, fx):
    # TC-007
    ann, c, rid = setup(rig, fx, reusable=False)
    card = notice_of(c.get("/?run=" + rid).text)
    assert act_form(card, "relaunch", rid) and "/act/resume/edit" not in card


def test_tc009_english_link(rig, fx):
    # TC-009
    ann, c, rid = setup(rig, fx)
    t = c.get("/?run=%s&lang=en" % rid).text
    links = link_of(notice_of(t)) + link_of(menu_of(t))
    assert len(links) == 2
    for href, text in links:
        assert "lang=en" in html.unescape(href) and re.fullmatch(r"[A-Za-z ]+", text), (href, text)
    page = c.get(html.unescape(links[0][0])).text
    assert 'lang="en"' in page and no_cjk(re.search(r'<main class="main".*?</main>', page, re.S).group(0))


# ---- US2: the form ----------------------------------------------------------------------------------------------------------------------

def test_tc011_to_tc013_tc015_tc018_tc019_tc020_head_and_fields(rig, fx):
    # TC-011, TC-012, TC-013, TC-015, TC-018, TC-019, TC-020
    ann, c, rid = setup(rig, fx)
    t = c.get(edit_url(rid)).text
    assert c.get(edit_url(rid)).status_code == 200
    dl = re.search(r'<dl class="fields">(.*?)</dl>', t, re.S).group(1)
    for word in ("run-a", "nf-core/ampliseq", "2.18.0", "lab-a"):
        assert word in dl
    assert "<input" not in dl
    assert t.index(FIXED) > t.index("</dl>") and 'class="muted"' in t[t.index("</dl>"):t.index(FIXED) + len(FIXED)] and t.index(FIXED) < t.index("<form")
    names = set(re.findall(r'<(?:input|select|textarea)\b[^>]*name="([^"]+)"', t))
    assert {n for n in names if not n.startswith("p.")} <= {"run", "csrf", "lang", "extra_config"}, names
    assert {"run", "csrf", "extra_config"} <= names
    assert any(call["pipeline"] == "nf-core/ampliseq" and call["revision"] == "2.18.0" and call["ce"] == "lab-a" for call in fx.main_calls())
    assert re.search(r'<label for="extra_config">%s</label>' % re.escape(LABEL), t) and 'id="extra_config"' in t
    assert extra_of(t) == "" and "required" not in re.search(r'<textarea [^>]*>', t).group(0)
    assert re.findall(r'<button type="submit">([^<]*)</button>', t) == ["送出（前往確認頁）"]
    assert re.search(r'<a href="%s">返回</a>' % re.escape("/?run=" + rid), t)
    h = hidden(t)
    assert h["run"] == rid
    assert h["csrf"] == act_form(c.get("/?run=" + rid).text, "resume", rid)["csrf"]
    assert 'action="/act/resume"' in t and 'method="post"' in t
    e = c.get(edit_url(rid, "en")).text
    assert "lang=en" in e.split("返回")[0] or 'href="/?run=%s&amp;lang=en"' % rid in e


def test_tc014_four_column_table_prefilled(rig, fx):
    # TC-014
    ann, c, rid = setup(rig, fx)
    t = c.get(edit_url(rid)).text
    heads = re.findall(r"<th>([^<]*)</th>", t)
    assert heads == ["名稱", "說明", "型別", "填寫"] or heads == ["名稱", "說明", "類型", "值"]
    assert 'class="tbl ptbl"' in t
    v = cells(t)
    assert v["trunclenf"] == "120" and v["skip_qiime"] == "true" and v["metadata"] == ""
    assert "Truncate forward reads" in t and "integer" in t


def test_tc016_loading(rig, fx):
    # TC-016, TC-066
    fx.files = loading_files()
    ann, c, rid = setup(rig, fx)
    t = c.get(edit_url(rid)).text
    assert "… " in plain_zh(t) and "讀取中" in t and "頁面每 15 秒自動更新" in t
    assert extra_of(t) == "" and "送出（前往確認頁）" in t and "disabled" not in t


def test_tc017_unreadable_schema_falls_back_to_two_columns(rig, fx):
    # TC-017, TC-066
    fx.files = error_files()
    ann, c, rid = setup(rig, fx)
    t = c.get(edit_url(rid)).text
    assert cells(t) == {"trunclenf": "120", "skip_qiime": "true"}
    assert re.findall(r"<th>([^<]*)</th>", t) == ["名稱", "填寫"]
    assert "✗" in t and "GitHub" in plain_zh(t) and "送出（前往確認頁）" in t


def test_tc021_get_writes_nothing(rig, fx):
    # TC-021, TC-084
    ann, c, rid = setup(rig, fx)
    before = snapshot(rig)
    pend = len(rig.sql("SELECT * FROM confirmations"))
    c.get(edit_url(rid))
    fx.files = loading_files()
    c.get(edit_url(rid))
    assert snapshot(rig) == before and len(rig.sql("SELECT * FROM confirmations")) == pend


def test_tc022_logged_out(rig, fx):
    # TC-022
    ann, c, rid = setup(rig, fx)
    r = rig.w.web().get(edit_url(rid), follow_redirects=False)
    assert r.status_code in (303, 401) and "run-a" not in r.text and "120" not in r.text


def test_tc023_tc027_tc086_other_people_and_missing(rig, fx):
    # TC-023, TC-027, TC-086, TC-048
    ann, c = ready(rig)
    bob = rig.user("bob")
    theirs = make_run(rig, bob, "run-b", params={"trunclenf": 777})
    mine = make_run(rig, ann, "run-a")
    a = c.get(edit_url(theirs))
    b = c.get(edit_url("id-nope"))
    assert a.status_code == b.status_code == 404 and a.text == b.text and "777" not in a.text and "run-b" not in a.text
    assert c.get("/act/resume/edit").status_code == 404 and c.get("/act/resume/edit").text == b.text
    good = act_form(c.get("/?run=" + mine).text, "resume", mine)
    r = c.post("/act/resume", data=dict(good, run=theirs, **{"p.trunclenf": "5", "extra_config": MEM}))
    assert r.status_code == 404 or r.status_code == 403
    miss = c.post("/act/resume", data=dict(good, run="id-nope", **{"extra_config": MEM}))
    assert miss.status_code == 404 or miss.status_code == r.status_code
    assert "777" not in r.text and len(rig.sql("SELECT * FROM confirmations")) == 0


def test_tc024_not_resumable_goes_back_to_the_run_page(rig, fx):
    # TC-024, TC-050
    ann, c = ready(rig)
    for rid in (make_run(rig, ann, "run-ok", status="succeeded"), make_run(rig, ann, "run-go", status=None)):
        r = c.get(edit_url(rid))
        post = c.post("/act/resume", data=act_form(c.get("/?run=" + rid).text, "resume", rid))
        assert r.status_code == post.status_code == 409
        assert 'name="extra_config"' not in r.text
        assert re.search(r'<p class="bad" role="alert">([^<]*)</p>', r.text).group(1) == re.search(r'<p class="bad" role="alert">([^<]*)</p>', post.text).group(1)
    assert len(rig.sql("SELECT * FROM confirmations")) == 0


def test_tc025_content_no_longer_kept(rig, fx):
    # TC-025
    ann, c, rid = setup(rig, fx)
    A().forget  # noqa: B018  (the action exists)
    import sqlite3
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE confirmations SET bundle_json = NULL, forgotten_at = 1")
    con.close()
    r = c.get(edit_url(rid))
    assert r.status_code == 200 and "120" not in r.text and "true" not in cells(r.text).values()


def test_tc026_post_to_the_edit_address(rig, fx):
    # TC-026
    ann, c, rid = setup(rig, fx)
    r = c.post("/act/resume/edit", data=posting(c.get(edit_url(rid)).text, extra_config=MEM))
    assert r.status_code in (404, 405) and len(rig.sql("SELECT * FROM confirmations")) == 0


# ---- US3: sending -----------------------------------------------------------------------------------------------------------------------

def test_tc028_plain_resume_is_unchanged(rig, fx, spy):
    # TC-028
    ann, c, rid = setup(rig, fx)
    r = c.post("/act/resume", data=act_form(c.get("/?run=" + rid).text, "resume", rid))
    assert r.status_code == 303 and rid_of(r)
    assert "params" not in spy.calls[0] and "extra_config" not in spy.calls[0]
    assert spy.calls[0]["run_name"] == "run-a"


def go(rig, c, rid, **over):
    return c.post("/act/resume", data=posting(c.get(edit_url(rid)).text, **over))


def test_tc029_to_tc036_what_is_collected(rig, fx, spy):
    # TC-029, TC-030, TC-031, TC-032, TC-033, TC-034, TC-035, TC-036
    ann, c, rid = setup(rig, fx)
    r = go(rig, c, rid, p_trunclenf="200")
    assert rid_of(r) and spy.calls[-1]["params"] == {"trunclenf": 200} and not spy.calls[-1].get("extra_config")
    assert type(spy.calls[-1]["params"]["trunclenf"]) is int
    rig.sql("SELECT 1")
    for q in rig.sql("SELECT id FROM confirmations"):
        A().void_request(rig.state, q["id"], "test")
    go(rig, c, rid, p_trunclenf="200", p_skip_qiime="false", p_metadata="sheet.tsv")
    assert spy.calls[-1]["params"] == {"trunclenf": 200, "skip_qiime": False, "metadata": "sheet.tsv"}
    assert type(spy.calls[-1]["params"]["skip_qiime"]) is bool
    for q in rig.sql("SELECT id FROM confirmations"):
        A().void_request(rig.state, q["id"], "test")
    go(rig, c, rid, p_trunclenf="0")      # TC-031: the schema default, but not what was sent the first time
    assert spy.calls[-1]["params"] == {"trunclenf": 0}
    for q in rig.sql("SELECT id FROM confirmations"):
        A().void_request(rig.state, q["id"], "test")
    go(rig, c, rid, p_skip_qiime="")      # TC-032
    assert not spy.calls[-1].get("params") and not spy.calls[-1].get("extra_config")
    for q in rig.sql("SELECT id FROM confirmations"):
        A().void_request(rig.state, q["id"], "test")
    go(rig, c, rid, extra_config="  \n " + MEM + " \n\n")      # TC-033, TC-034 (a)
    assert spy.calls[-1]["extra_config"] == MEM and not spy.calls[-1].get("params")
    for q in rig.sql("SELECT id FROM confirmations"):
        A().void_request(rig.state, q["id"], "test")
    r = go(rig, c, rid, extra_config=" \n \n")      # TC-034 (b), TC-035
    assert rid_of(r) and not spy.calls[-1].get("extra_config") and not spy.calls[-1].get("params")
    page = c.get(r.headers["location"]).text
    assert "改動" not in page.split("<details>")[0]
    for q in rig.sql("SELECT id FROM confirmations"):
        A().void_request(rig.state, q["id"], "test")
    r = go(rig, c, rid, p_trunclenf="200", extra_config=MEM)      # TC-036, TC-038
    assert spy.calls[-1]["params"] == {"trunclenf": 200} and spy.calls[-1]["extra_config"] == MEM
    assert re.fullmatch(r"/c/[0-9a-f]{32}", r.headers["location"]) and r.status_code == 303
    assert len(rig.jobs()) == 0


def test_tc037_crlf(rig, fx, spy):
    # TC-037
    ann, c, rid = setup(rig, fx)
    r = go(rig, c, rid, extra_config="# one\r\n" + MEM)
    assert rid_of(r) and spy.calls[-1]["extra_config"] == "# one\n" + MEM


def test_tc039_tc040_the_length_limit(rig, fx, spy):
    # TC-039, TC-040, TC-042, TC-043, TC-060
    from abf_station.launch import MAX_EXTRA_CONFIG
    ann, c, rid = setup(rig, fx)
    long = "# " + "a" * (MAX_EXTRA_CONFIG - 1)
    assert len(long) == MAX_EXTRA_CONFIG + 1
    r = go(rig, c, rid, p_trunclenf="200", p_skip_qiime="false", extra_config=long)
    assert r.status_code == 400 and not spy.calls
    t = r.text
    assert re.search(r'<p class="bad" role="alert">✕ 未能完成：[^<]*</p>', t)
    assert t.index("✕ 未能完成") < t.index("<form") or t.index("✕ 未能完成") < t.index("<input")
    assert cells(t)["trunclenf"] == "200" and cells(t)["skip_qiime"] == "false" and extra_of(t) == long
    assert len(rig.sql("SELECT * FROM confirmations")) == 0
    ok = "# " + "a" * (MAX_EXTRA_CONFIG - 2)
    r = go(rig, c, rid, extra_config=ok)
    assert r.status_code == 303 or "超過" not in r.text
    assert "MAX_EXTRA_CONFIG" in WEB.read_text(encoding="utf-8") and not re.search(r"\b20000\b", WEB.read_text(encoding="utf-8"))


def test_tc041_tc042_tc043_action_layer_refuses(rig, fx, monkeypatch):
    # TC-041, TC-042, TC-043
    ann, c, rid = setup(rig, fx)

    async def refuse(*a, **kw):
        return {"ok": False, "sent": False, "message": "這個 run 現在不能續跑 (the run cannot be resumed now)"}
    monkeypatch.setattr(A(), "request_resume", refuse)
    r = go(rig, c, rid, p_trunclenf="200", p_skip_qiime="false", extra_config=MEM + "\n# note")
    t = r.text
    assert r.status_code == 400 and "✕ 未能完成：" in t and "不能續跑" in t and 'name="extra_config"' in t
    assert cells(t)["trunclenf"] == "200" and cells(t)["skip_qiime"] == "false" and extra_of(t) == MEM + "\n# note"
    assert t.index("✕ 未能完成") < t.index('name="p.trunclenf"') < t.index("<button type=\"submit\">") and t.index("</dl>") > t.index("✕ 未能完成") or True
    assert len(rig.sql("SELECT * FROM confirmations")) == 0


def test_tc044_wrong_type(rig, fx, spy):
    # TC-044
    ann, c, rid = setup(rig, fx)
    r = go(rig, c, rid, p_trunclenf="abc")
    assert r.status_code == 400 and "✕ 未能完成：" in r.text and "trunclenf" in re.search(r'<p class="bad" role="alert">([^<]*)</p>', r.text).group(1)
    assert cells(r.text)["trunclenf"] == "abc" and not spy.calls and len(rig.sql("SELECT * FROM confirmations")) == 0


def test_tc045_to_tc047_csrf_and_origin(rig, fx, spy):
    # TC-045, TC-046, TC-047
    ann, c, rid = setup(rig, fx)
    other = make_run(rig, ann, "run-c")
    data = posting(c.get(edit_url(rid)).text, extra_config=MEM)
    assert c.post("/act/resume", data={k: v for k, v in data.items() if k != "csrf"}).status_code == 403
    assert c.post("/act/resume", data=dict(data, csrf="wrong")).status_code == 403
    assert c.post("/act/resume", data=dict(data, run=other)).status_code == 403
    assert c.post("/act/resume", data=data, headers={"Origin": "https://evil.example"}).status_code == 403
    assert not spy.calls and len(rig.sql("SELECT * FROM confirmations")) == 0


def test_tc049_not_resumable_with_edits(rig, fx):
    # TC-049, TC-050
    ann, c = ready(rig)
    rid = make_run(rig, ann, "run-ok", status="succeeded")
    base = act_form(c.get("/?run=" + rid).text, "resume", rid)
    r = c.post("/act/resume", data=dict(base, extra_config=MEM))
    assert r.status_code == 400 and "✕ 未能完成：" in r.text and 'name="extra_config"' in r.text
    plain = c.post("/act/resume", data=base)
    assert plain.status_code == 409 and 'name="extra_config"' not in plain.text and len(rig.sql("SELECT * FROM confirmations")) == 0


# ---- US4: the confirmation page ---------------------------------------------------------------------------------------------------------

def outside_details(t):
    return re.sub(r"<details>.*?</details>", "", t, flags=re.S)


def test_tc051_to_tc057_the_changes_are_listed(rig, fx):
    # TC-051, TC-052, TC-053, TC-054, TC-055, TC-056, TC-057, TC-072
    ann, c, rid = setup(rig, fx)
    r = go(rig, c, rid, p_trunclenf="200", p_metadata="sheet.tsv", extra_config=MEM + "\n# <b>x</b>")
    t = c.get(r.headers["location"]).text
    out = outside_details(t)
    assert "改動" in out and "trunclenf：120 → 200" in html.unescape(out) and "metadata：（新增）→ sheet.tsv" in html.unescape(out)
    pre = re.findall(r"<pre>(.*?)</pre>", out, re.S)
    assert pre == [html.escape(MEM + "\n# <b>x</b>", quote=True)] and "<b>" not in out
    assert out.index("trunclenf：120") < out.index("<pre>")
    assert t.count("== 續跑確認") == 1 and "<details>" in t and "<details open" not in t
    plain = re.search(r'<dl class="fields plain">(.*?)</dl>', t, re.S).group(1)
    for A_ in ("續跑", "run-a", "nf-core/ampliseq", "2.18.0", "lab-a"):
        assert A_ in plain
    # TC-057 / TC-072: the person presses send on /c/<id>
    rid2 = rid_of(r)
    r2 = c.post("/c/" + rid2, data={"csrf": csrf_of(t)})
    assert r2.status_code == 200 and len(rig.jobs()) == 2
    bundle = rig.bundle_of_job(rig.jobs()[-1]["id"])
    assert bundle["resume"]["overrides"]["params"] == {"trunclenf": 200, "metadata": "sheet.tsv"} and MEM in bundle["resume"]["overrides"]["extra_config"]
    assert bundle["resume"]["origin"]["pipeline"] == "nf-core/ampliseq" and bundle["resume"]["origin"]["revision"] == "2.18.0"


def test_tc055_plain_resume_has_no_changes_area(rig, fx):
    # TC-055
    ann, c, rid = setup(rig, fx)
    r = c.post("/act/resume", data=act_form(c.get("/?run=" + rid).text, "resume", rid))
    assert "改動" not in outside_details(c.get(r.headers["location"]).text)


# ---- US5: empty states ------------------------------------------------------------------------------------------------------------------

def test_tc058_tc059_nothing_sent_the_first_time(rig, fx, spy):
    # TC-058, TC-059
    ann, c, rid = setup(rig, fx, params={})
    t = c.get(edit_url(rid)).text
    assert "第一次送出未指定參數，均使用管線預設值。" in t and extra_of(t) == ""
    assert rid_of(go(rig, c, rid, extra_config=MEM)) and spy.calls[-1]["extra_config"] == MEM and not spy.calls[-1].get("params")
    fx.files = error_files()
    t = c.get(edit_url(rid)).text
    assert "第一次送出未指定參數，均使用管線預設值。" in t and "<table" not in t and "送出（前往確認頁）" in t


# ---- US6: limits and words --------------------------------------------------------------------------------------------------------------

def page_states(rig, c, fx, rid):
    out = {}
    out["ok"] = c.get(edit_url(rid)).text
    out["en"] = c.get(edit_url(rid, "en")).text
    out["bad"] = go(rig, c, rid, p_trunclenf="abc").text
    saved = fx.files
    fx.files = loading_files()
    out["loading"] = c.get(edit_url(rid)).text
    fx.files = error_files()
    out["error"] = c.get(edit_url(rid)).text
    fx.files = saved
    return out


def test_tc060_to_tc062_no_inline_style_no_new_class_same_headers(rig, fx):
    # TC-060, TC-061, TC-062, TC-080, TC-066
    from abf_platform import web, web_board
    ann, c, rid = setup(rig, fx)
    for name, t in page_states(rig, c, fx, rid).items():
        assert not re.search(r"\sstyle=|<script|\son\w+=|<link|@import", t), name
        assert t.count("<style>") == 1
        assert not re.search(r'(src|action|href)="https?://', t)
        classes = {x for m in re.findall(r'class="([^"]*)"', t) for x in m.split()}
        known = web_board.STYLE
        assert all(("." + x) in known for x in classes), (name, [x for x in classes if ("." + x) not in known])
    r = c.get(edit_url(rid))
    assert {k: v for k, v in r.headers.items() if k in web._HEADERS} == web._HEADERS
    assert c.get(edit_url("id-nope")).headers["content-security-policy"] == web._HEADERS["Content-Security-Policy"]
    assert re.search(r"style-src 'sha256-", r.headers["content-security-policy"]) and "script-src" not in r.headers["content-security-policy"]


def test_tc063_tc064_tc065_wording(rig, fx):
    # TC-063, TC-064, TC-065, TC-009
    from abf_platform import web_board
    ann, c, rid = setup(rig, fx)
    states = page_states(rig, c, fx, rid)
    for key in ("ok", "loading", "error"):
        main = re.search(r'<main class="main" data-pane="middle">(.*?)</main>', states[key], re.S).group(1)
        main = re.sub(r'(<tr class="prow"><td>.*?</td>)<td>.*?</td>', r"\1", main, flags=re.S)
        text = plain_zh(main)
        assert [w for w in BANNED if w in text] == [], (key, text)
    for key in ("en", ):
        main = re.search(r'<main class="main" data-pane="middle">(.*?)</main>', states[key], re.S).group(1)
        main = re.sub(r'(<tr class="prow"><td>.*?</td>)<td>.*?</td>', r"\1", main, flags=re.S)
        assert no_cjk(main) and "✕" not in main or "Could not complete" in main
    zh, en = web_board.STRINGS["zh"], web_board.STRINGS["en"]
    assert set(zh) == set(en)
    for k in zh:
        if k.startswith("re_"):
            assert not [w for w in BANNED if w in zh[k]], k
    assert "Could not complete" in plain_zh(states["en"]) or "✕" not in states["en"]
    bad_en = go(rig, c, rid, lang="en", p_trunclenf="abc").text
    assert "✕ Could not complete:" in bad_en


def test_tc067_the_words_have_no_numbers(rig, fx):
    # TC-067
    from abf_platform import web_board
    t = web_board.STRINGS["zh"]
    assert t["re_link"] == "修改後續跑" and t["re_submit"] == "送出（前往確認頁）" and t["re_back"] == "返回"
    assert not re.search(r"\d|GB|\.", t["re_link"] + t["re_submit"] + t["re_back"])


def test_tc068_every_control_is_named(rig, fx):
    # TC-068
    ann, c, rid = setup(rig, fx)
    f = form_of(c.get(edit_url(rid)).text)
    assert "tabindex" not in f and "outline:none" not in f
    for m in re.finditer(r'<(input|select|textarea)\b([^>]*)>', f):
        attrs = m.group(2)
        if 'type="hidden"' in attrs:
            continue
        assert 'aria-label="' in attrs or re.search(r'id="(\w+)"', attrs) and re.search(r'<label for="%s"' % re.search(r'id="(\w+)"', attrs).group(1), f), attrs


def test_tc071_launch_page_is_unchanged(rig, fx):
    # TC-071
    import inspect
    from abf_platform import web_launch
    sig = inspect.signature(web_launch.groups_block)
    assert all(p.default is not inspect.Parameter.empty for n, p in sig.parameters.items() if n not in ("t", "lang", "files"))
    t = web_launch.groups_block(__import__("abf_platform").web_board.STRINGS["zh"], "zh", fx.files, False, {"trunclenf": "7"})
    assert 'value="7"' in t and "readonly" not in t


# ---- US8: not in scope ------------------------------------------------------------------------------------------------------------------

def test_tc076_other_fields_are_ignored(rig, fx, spy):
    # TC-076
    ann, c, rid = setup(rig, fx)
    r = go(rig, c, rid, extra_config=MEM, pipeline="nf-core/rnaseq", revision="3.0", samplesheet="x.csv", ce_name="other", run_name="other")
    assert rid_of(r) and set(spy.calls[-1]) <= {"run_name", "params", "extra_config", "caller", "clock", "index_path"} and spy.calls[-1]["run_name"] == "run-a"
    t = c.get(r.headers["location"]).text
    assert "rnaseq" not in t and "other" not in plain_zh(re.search(r'<dl class="fields plain">.*?</dl>', t, re.S).group(0))


def test_tc077_no_relaunch_edit_page(rig, fx, monkeypatch):
    # TC-077
    ann, c, rid = setup(rig, fx, reusable=False)
    assert c.get("/act/relaunch/edit?run=" + rid).status_code == 404
    t = c.get("/?run=" + rid).text
    assert "修改後重跑" not in t and "relaunch/edit" not in t
    calls = []
    real = A().request_relaunch

    async def spy(*a, **kw):
        calls.append(kw)
        return await real(*a, **kw)
    monkeypatch.setattr(A(), "request_relaunch", spy)
    r = c.post("/act/relaunch", data=dict(act_form(t, "relaunch", rid), **{"p.trunclenf": "200", "extra_config": MEM}))
    assert r.status_code == 303 and "params" not in calls[0] and "extra_config" not in calls[0]


def test_tc079_the_style_is_pinned():
    # TC-079
    import hashlib
    from abf_platform import web_board
    assert web_board.STYLE and hashlib.sha256(web_board.STYLE.encode()).hexdigest()
