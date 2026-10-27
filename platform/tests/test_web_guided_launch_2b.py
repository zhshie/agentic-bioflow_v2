# Nothing existing: tests of guided-launch-2b (the second cut of the /launch page: one form, one button, the defaults in the boxes, red stars, formal wording).
"""guided-launch-2b: /launch with one send button, offline. The test cases are named in the comments (TC-001 ...); they are in
specs/guided-launch-2b. The two read actions are replaced by the `Fake` of test_web_guided_launch_2, so no job is queued and nothing connects out;
`request_launch` is wrapped so a test can see whether it was called, and with what."""
import html
import re
import urllib.parse

import pytest

from test_web_actions import area_sheet, form_values, login, pending, rid_of
from test_web_board import no_cjk
from test_web_guided_launch import SEL, launched, ready, rig  # noqa: F401  (rig is a fixture)
from test_web_guided_launch_2 import (NETWORK, error_files, fk, good_files, groups, input_cols, latest, loading_files,  # noqa: F401  (fk is a fixture)
                                      plain_text, step)

BANNED = ["用過", "選好", "寫死", "自己填", "自己調整", "你還沒", "還沒有", "還不能", "這個", "這份", "這條", "這一版", "一下", "弄", "搞", "東西", "喔",
          "啦", "吧", "囉", "蠻", "超"]
OLD_KEYS = ["選這個管線", "選用這份樣本表", "套用參數", "選用這個環境"]
STAR = '<span class="req" title="必填">*</span>'
STAR_EN = '<span class="req" title="Required">*</span>'
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]


def main_of(text):
    return re.search(r'<main class="main" data-pane="middle">(.*?)</main>', text, re.S).group(1)


def form_of(text):
    return re.search(r'<form class="lform" method="post" action="/launch">(.*?)</form>', main_of(text), re.S).group(1)


def zh_words(page):
    """The Chinese of the main column as the guard reads it: the description cells (the pipeline's own English) are taken out first, the side column
    and the header are not in the main column at all (ruling 12)."""
    body = main_of(page)
    body = re.sub(r'(<tr class="prow"><td>.*?</td>)<td>.*?</td>', r"\1", body, flags=re.S)
    body = re.sub(r'(<tr class="scol"><td>.*?</td>)<td>.*?</td>', r"\1", body, flags=re.S)
    return plain_text(body)


def banned_in(page):
    text = zh_words(page)
    return [w for w in BANNED if w in text]


def cell(text, name):
    m = re.search(r'<(?:input|select) [^>]*name="p\.%s"[^>]*>' % re.escape(name), text)
    return m.group(0) if m else None


def select_html(text, name):
    return re.search(r'<select [^>]*name="%s"[^>]*>.*?</select>' % re.escape(name), text, re.S).group(0)


def selected_of(sel):
    m = re.search(r'<option value="([^"]*)" selected', sel)
    return html.unescape(m.group(1)) if m else None


def hidden_of(text):
    return {k: html.unescape(v) for k, v in re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', form_of(text))}


class Spy:
    def __init__(self, monkeypatch):
        from abf_platform import actions
        self.calls, real = [], actions.request_launch

        async def spy(*a, **kw):
            self.calls.append(kw)
            return await real(*a, **kw)
        monkeypatch.setattr(actions, "request_launch", spy)


@pytest.fixture
def spy(monkeypatch):
    return Spy(monkeypatch)


def post(rig, c, **over):
    return c.post("/launch", data=form_values(rig, c, "ann", **over))


def query_of(response):
    loc = response.headers["location"]
    assert loc.startswith("/launch?"), loc
    return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlsplit(loc).query, keep_blank_values=True).items()}


# ---- US1: one button ------------------------------------------------------------------------------------------------------------------

def test_h01_one_submit_button(rig, fk):
    # TC-001, TC-002, TC-003, TC-004, H01
    ann, c = ready(rig)
    launched(rig, ann, "run-a")
    for url in (SEL, SEL + "&src=new", SEL + "&src=used"):
        t = c.get(url).text
        main = main_of(t)
        assert re.findall(r'<button type="submit">([^<]*)</button>', main) == ["送出（前往確認頁）"], url
        assert len(re.findall(r"<form ", main)) == 1 and 'method="get"' not in main
        for gone in OLD_KEYS:
            assert gone not in t, gone
        f = form_of(t)
        assert 'name="run_name"' in f
        for name in ("samplesheet", "ce_name", "params_from"):
            assert re.search(r'<select [^>]*name="%s"' % name, f), name
        assert re.search(r'<textarea [^>]*name="params"', f) and 'name="p.orf_start"' in f
    f = form_of(c.get(SEL + "&src=new").text)
    assert re.search(r'<input [^>]*name="pipeline"', f) and re.search(r'<input [^>]*name="revision"', f)


def test_h01_kept_links(rig, fk):
    # TC-005, TC-006, TC-007
    ann, c = ready(rig)
    launched(rig, ann, "run-a")
    two = step(c.get(SEL + "&src=used").text, 2)
    assert re.search(r'<a href="/launch\?pipeline=nf-core/ampliseq&amp;revision=2.18.0">選用</a>', two)
    assert re.search(r'<a href="/launch\?from=run-a">沿用設定重新分析</a>', two)
    t = c.get("/launch?pipeline=nf-core/ampliseq&src=new").text
    assert re.search(r'<a href="[^"]*pipeline=nf-core/ampliseq[^"]*revision=2.18.0[^"]*">套用此版本</a>', step(t, 2))
    assert 'data-tab="used"' in t and 'data-tab="new"' in t and "開啟流程圖" in step(c.get(SEL).text, 3)


def test_h01_used_tab_hidden_fields(rig, fk, spy):
    # TC-008, TC-027
    ann, c = ready(rig)
    launched(rig, ann, "run-a")
    t = c.get(SEL + "&src=used").text
    f = form_of(t)
    assert not re.search(r'<input [^>]*name="(pipeline|revision)"', re.sub(r'<input type="hidden"[^>]*>', "", f))
    h = hidden_of(t)
    assert h["pipeline"] == "nf-core/ampliseq" and h["revision"] == "2.18.0"
    r = c.post("/launch", data=dict(h, run_name="web-run", samplesheet="samples.csv", ce_name="lab-a"))
    assert r.status_code == 303 and r.headers["location"].startswith("/c/") and len(spy.calls) == 1


def test_h01_no_sheet_no_env_keep_the_button(rig, fk, spy):
    # TC-009, TC-010
    rig.user("ann")
    c = login(rig, "ann")
    t = c.get(SEL).text
    assert "送出（前往確認頁）" in main_of(t) and "disabled" not in form_of(t)
    r = c.post("/launch", data=dict(hidden_of(t), pipeline="nf-core/ampliseq", revision="2.18.0", run_name="x", samplesheet="", ce_name="lab-a"))
    assert r.status_code == 400 and "樣本表必須從已上傳的檔案中選擇。" in r.text and spy.calls == []
    bob = rig.user("bob")      # the first user owns the only environment
    area_sheet(rig.w, bob)
    c = login(rig, "bob")
    t = c.get(SEL).text
    assert "送出（前往確認頁）" in main_of(t) and "尚無可用的運算環境。" in t
    r = c.post("/launch", data=dict(hidden_of(t), pipeline="nf-core/ampliseq", revision="2.18.0", run_name="x", samplesheet="samples.csv", ce_name=""))
    assert r.status_code == 400 and "運算環境必須是" in r.text and spy.calls == []


def test_h01_english(rig, fk):
    # TC-011
    _, c = ready(rig)
    main = main_of(c.get(SEL + "&lang=en").text)
    assert len(re.findall(r'<button type="submit">([^<]*)</button>', main)) == 1 and no_cjk(main)
    for gone in ("Use this pipeline", "Use this samplesheet", "Apply parameters", "Use this environment"):
        assert gone not in main


# ---- US2: load or send ----------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("over", [{"pipeline": "nf-core/rnaseq"}, {"revision": "3.0.0"}, {"shown_pipeline": "", "shown_revision": ""}])
def test_h02_h03_changed_pair_only_loads(rig, fk, spy, over):
    # TC-012, TC-013, TC-014, TC-137
    _, c = ready(rig)
    before = pending(rig)
    r = post(rig, c, **over)
    assert r.status_code == 303 and r.headers["location"].startswith("/launch?") and spy.calls == [] and pending(rig) == before
    q = query_of(r)
    assert q["pipeline"] == over.get("pipeline", "nf-core/ampliseq") and q["revision"] == over.get("revision", "2.18.0")


def test_h02_location_carries_and_drops(rig, fk, spy):
    # TC-015, TC-016
    _, c = ready(rig)
    r = post(rig, c, pipeline="nf-core/rnaseq", samplesheet="samples.csv", ce_name="lab-a", run_name="my-run", params_from="earlier-run",
             params="x: 1", route="custom", **{"p.orf_start": "9"})
    q = query_of(r)
    assert (q["samplesheet"], q["ce_name"], q["run_name"], q["params_from"]) == ("samples.csv", "lab-a", "my-run", "earlier-run")
    assert not [k for k in q if k.startswith("p.") or k in ("params", "route")] and "lang" not in q
    q = query_of(post(rig, c, pipeline="nf-core/rnaseq", lang="en"))
    assert q["lang"] == "en"


def test_h02_shown_hidden_fields(rig, fk):
    # TC-017
    ann, c = ready(rig)
    launched(rig, ann, "run-a", params={"orf_start": 5})
    h = hidden_of(c.get(SEL + "&params_from=run-a").text)
    assert (h["shown_pipeline"], h["shown_revision"], h["shown_params_from"]) == ("nf-core/ampliseq", "2.18.0", "run-a")
    assert hidden_of(c.get(SEL).text)["shown_params_from"] == ""


def test_h02_loaded_note_and_run_name(rig, fk):
    # TC-018, TC-019, TC-020
    _, c = ready(rig)
    r = post(rig, c, pipeline="nf-core/ampliseq", shown_pipeline="nf-core/rnaseq", run_name="my-run")
    t = c.get(r.headers["location"]).text
    assert '<p class="muted">已載入 nf-core/ampliseq 版本 2.18.0 的參數表，請檢查後再按送出。</p>' in main_of(t)
    assert re.search(r'name="run_name" value="my-run"', t)
    r = post(rig, c, shown_pipeline="nf-core/rnaseq", lang="en")
    assert "lang=en" in r.headers["location"]
    t = c.get(r.headers["location"]).text
    assert "The parameter table of nf-core/ampliseq version 2.18.0 is loaded" in main_of(t) and no_cjk(main_of(t))


def test_h04_matching_pair_sends(rig, fk, spy):
    # TC-021, TC-138
    _, c = ready(rig)
    before = pending(rig)
    rid_of(post(rig, c))
    assert len(spy.calls) == 1 and pending(rig) == before + 1
    k = spy.calls[0]
    assert (k["pipeline"], k["revision"], k["run_name"], k["samplesheet"], k["ce_name"]) == ("nf-core/ampliseq", "2.18.0", "web-run", "samples.csv", "lab-a")


def test_h04_blank_pair_is_a_400(rig, fk, spy):
    # TC-022, TC-023, TC-024
    _, c = ready(rig)
    r = post(rig, c, pipeline="", shown_pipeline="")
    assert r.status_code == 400 and "管線為必填" in r.text
    r = post(rig, c, revision="", shown_revision="x")
    assert r.status_code == 400 and "版本為必填" in r.text
    r = post(rig, c, pipeline="", revision="", shown_pipeline="", shown_revision="")
    assert r.status_code == 400 and "管線為必填" in r.text and "版本為必填" in r.text and spy.calls == []


def test_h04_400_page_then_send(rig, fk, spy):
    # TC-025
    _, c = ready(rig)
    r = post(rig, c, run_name="")
    assert r.status_code == 400
    h = hidden_of(r.text)
    assert (h["shown_pipeline"], h["shown_revision"]) == ("nf-core/ampliseq", "2.18.0")
    rid_of(c.post("/launch", data=dict(h, pipeline="nf-core/ampliseq", revision="2.18.0", run_name="web-run", samplesheet="samples.csv", ce_name="lab-a")))


def test_h04_one_press_from_a_link(rig, fk, spy):
    # TC-026
    ann, c = ready(rig)
    launched(rig, ann, "run-a")
    for n, url in enumerate((SEL, SEL + "&src=used")):
        h = hidden_of(c.get(url).text)
        r = c.post("/launch", data=dict(h, run_name="n-%d" % n, samplesheet="samples.csv", ce_name="lab-a"))
        assert r.status_code == 303 and r.headers["location"].startswith("/c/")
    assert len(spy.calls) == 2


def test_h08_params_from_change_loads(rig, fk, spy):
    # TC-028, TC-029, TC-030
    ann, c = ready(rig)
    launched(rig, ann, "run-a", params={"orf_start": 5})
    r = post(rig, c, params_from="earlier-run", shown_params_from="")
    assert r.status_code == 303 and query_of(r)["params_from"] == "earlier-run" and spy.calls == []
    r = post(rig, c, params_from="", shown_params_from="earlier-run")
    assert r.status_code == 303 and "params_from" not in query_of(r) and spy.calls == []
    rid_of(post(rig, c, params_from="run-a", shown_params_from="run-a"))
    assert len(spy.calls) == 1


def test_csrf_and_origin_do_not_load(rig, fk, spy):
    # TC-139, TC-140
    _, c = ready(rig)
    assert post(rig, c, csrf="wrong", pipeline="nf-core/rnaseq").status_code == 403
    r = c.post("/launch", data=form_values(rig, c, "ann", pipeline="nf-core/rnaseq"), headers={"Origin": "https://evil.example"})
    assert r.status_code == 403 and spy.calls == []


# ---- US3: defaults in the boxes -------------------------------------------------------------------------------------------------------

def test_h05_cells_hold_the_defaults(rig, fk):
    # TC-031 .. TC-037
    _, c = ready(rig)
    five = step(c.get(SEL).text, 5)
    assert 'value="TAA,TAG"' in cell(five, "stop_codons") and 'value="1"' in cell(five, "orf_start")
    assert selected_of(select_html(five, "p.run_pplace")) == "false"
    assert selected_of(select_html(five, "p.decontam_decontaminate_method")) == "auto"
    assert 'value=""' in cell(five, "max_len_asv")
    for name in ("filter_ssu", "ancom"):
        sel = select_html(five, "p." + name)
        assert sel.index('<option value=""') < sel.index("</option>") and selected_of(sel) in (None, "")
        assert re.findall(r'<option value="([^"]*)"', sel)[0] == ""
    assert 'name="route"' not in five and not re.search(r"[①②③]", five) and "自己調整" not in five and "預設值（不帶參數）" not in five
    assert "placeholder" not in five


def test_h05_route_is_ignored(rig, fk):
    # TC-038
    _, c = ready(rig)
    a, b = c.get(SEL + "&route=reuse"), c.get(SEL)
    assert a.status_code == 200 and a.text == b.text


def test_h05_step5_shape(rig, fk):
    # TC-039, TC-040, TC-041, TC-044
    ann, c = ready(rig)
    five = step(c.get(SEL).text, 5)
    assert "此管線版本尚無可沿用的分析。" in five
    launched(rig, ann, "run-a", params={"orf_start": 5})
    five = step(c.get(SEL).text, 5)
    sel = select_html(five, "params_from")
    assert "沿用先前分析的參數" in five and '<option value="">不沿用</option>' in sel
    assert five.index("params_from") < five.index('class="pgroups"') < five.index('name="params"')
    adv = re.search(r'<details class="padv"( open)?><summary>([^<]*)</summary>.*?<textarea [^>]*name="params"', five, re.S)
    assert adv and not adv.group(1) and adv.group(2) == "進階：直接輸入參數（一行一個「名稱: 值」）"


def test_h08_prefill_cells_and_unknown(rig, fk):
    # TC-042, TC-043, TC-059, TC-062
    ann, c = ready(rig)
    launched(rig, ann, "run-a", params={"orf_start": 5, "stop_codons": "TAA,TAG", "custom_unknown": 3})
    t = c.get(SEL + "&params_from=run-a").text
    five = step(t, 5)
    assert 'value="5"' in cell(five, "orf_start") and 'name="p.custom_unknown"' not in five
    box = html.unescape(re.search(r"<textarea[^>]*>(.*?)</textarea>", five, re.S).group(1))
    assert '<details class="padv" open>' in five and "custom_unknown: 3" in box
    seven = plain_text(step(t, 7))
    assert "orf_start: 5" in seven and "stop_codons" not in seven


def test_h08_cannot_reuse(rig, fk):
    # TC-045
    ann, c = ready(rig)
    launched(rig, ann, "run-o", pipeline="nf-core/rnaseq")
    t = c.get(SEL + "&params_from=run-o").text
    assert "此分析的參數無法沿用。" in step(t, 5) and hidden_of(t)["shown_params_from"] == ""


def test_h05_loading_and_error(rig, fk):
    # TC-046, TC-047
    fk.files = loading_files()
    _, c = ready(rig)
    five = step(c.get(SEL).text, 5)
    assert "讀取中，頁面將自動更新；請於讀取完成後再填寫參數。" in plain_text(five) and 'name="p.' not in five and "<textarea" in five
    fk.files = error_files()
    five = step(c.get(SEL).text, 5)
    assert "✗" in plain_text(five) and 'name="p.' not in five and "<textarea" in five


def test_h05_adv_group_title(rig, fk):
    # TC-048
    _, c = ready(rig)
    five = step(c.get(SEL).text, 5)
    adv = re.search(r'<details class="pgroup pgroup-adv"><summary>([^<]*)</summary>(.*?)</details>', five, re.S)
    assert adv.group(1) == "進階參數（管線預設隱藏）" and 'name="p.config_profile_name"' in adv.group(2)


# ---- US4: only the changed ------------------------------------------------------------------------------------------------------------

def sent(spy):
    assert len(spy.calls) == 1
    return spy.calls[0]["params"]


def defaults_form():
    out = {}
    for g in groups():
        for p in g["params"]:
            if p["has_default"]:
                v = p["default"]
                out["p." + p["name"]] = ("true" if v else "false") if isinstance(v, bool) else str(v)
    return out


def test_h06_all_defaults_send_no_params(rig, fk, spy):
    # TC-049, TC-061
    _, c = ready(rig)
    assert "全部使用預設值" in plain_text(step(c.get(SEL).text, 7))
    rid_of(post(rig, c, **defaults_form()))
    assert not sent(spy)


@pytest.mark.parametrize("name,raw,want", [("orf_start", "7", 7), ("run_pplace", "true", True), ("vsearch_cluster_id", "0.9", 0.9),
                                           ("stop_codons", "TAA", "TAA")])
def test_h06_only_the_changed_one(rig, fk, spy, name, raw, want):
    # TC-050, TC-051, TC-052, TC-053
    _, c = ready(rig)
    form = defaults_form()
    form["p." + name] = raw
    rid_of(post(rig, c, **form))
    got = sent(spy)
    assert got == {name: want} and type(got[name]) is type(want)


def test_h07_cleared_cell_is_not_sent(rig, fk, spy):
    # TC-054, TC-055, TC-056, TC-057, TC-058
    _, c = ready(rig)
    form = defaults_form()
    form["p.orf_start"] = ""
    form["p.max_len_asv"] = ""
    rid_of(post(rig, c, **form))
    assert not sent(spy)
    spy.calls.clear()
    rid_of(post(rig, c, **dict(defaults_form(), **{"p.FW_primer": "AAA", "p.stop_codons": "TAA", "params": "stop_codons: ZZZ\nmy_extra: 1"})))
    assert sent(spy) == {"FW_primer": "AAA", "stop_codons": "ZZZ", "my_extra": 1}


def test_h06_without_a_schema(rig, fk, spy):
    # TC-060
    fk.files = loading_files()
    _, c = ready(rig)
    rid_of(post(rig, c, **{"p.FW_primer": "AAA"}))
    assert sent(spy) == {"FW_primer": "AAA"}


# ---- US5: red stars -------------------------------------------------------------------------------------------------------------------

def test_h09_stars(rig, fk):
    # TC-063 .. TC-076
    ann, c = ready(rig)
    launched(rig, ann, "run-a")
    t = c.get(SEL + "&src=new").text
    five = step(t, 5)
    need = [p["name"] for g in groups() for p in g["params"] if p["required"] and not p["has_default"]]
    for g in groups():
        for p in g["params"]:
            m = re.search(r'<tr class="prow"><td>%s(.*?)</td>' % re.escape(p["name"]), five)
            assert m, p["name"]
            assert (STAR in m.group(1)) == (p["name"] in need), p["name"]
    four = step(t, 4)
    assert four.count("* 必填") == 1 and "<th>必填</th>" not in four
    table = re.search(r'<table class="tbl scols">.*?</table>', four, re.S).group(0)
    assert re.findall(r"<th>([^<]*)</th>", table) == ["欄名", "說明"] and "—" not in table and "✓" not in table
    for col in input_cols():
        m = re.search(r'<tr class="scol"><td>%s(.*?)</td>' % re.escape(col["name"]), four)
        assert (STAR in m.group(1)) == bool(col["required"]), col["name"]
    assert five.index("* 必填") < five.index("<table")
    assert not re.search(r'<tr class="prow">[^\n]*?>必填<', five)
    two = step(t, 2)
    assert re.search(r"<label>版本 %s<input" % re.escape(STAR), two) and "請填寫確切版本號，例如 2.18.0" in two
    assert re.search(r"<label>管線（nf-core 名稱） %s<input" % re.escape(STAR), two)
    assert re.search(r"<label>樣本表（從已上傳的檔案中選擇） %s<select" % re.escape(STAR), four)
    assert re.search(r"<label>運算環境 %s<select" % re.escape(STAR), step(t, 6))
    assert re.search(r"<label>分析名稱 %s<input" % re.escape(STAR), step(t, 7))
    assert "沿用先前分析的參數" in five and "req" not in re.search(r"<label>沿用先前分析的參數.*?<select", five, re.S).group(0)
    assert "req" not in re.search(r'<details class="padv"[^>]*>.*?<textarea', five, re.S).group(0)


def test_h09_style():
    # TC-077, TC-078
    import subprocess
    from abf_platform import web_board
    css = web_board.STYLE
    assert re.search(r"\.req\{[^}]*color:var\(--failed\)", css)
    base = subprocess.run(["git", "show", "956e7d2:platform/abf_platform/web_board.py"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert base.returncode == 0
    assert set(re.findall(r"#[0-9a-fA-F]{3,8}\b", css)) <= set(re.findall(r"#[0-9a-fA-F]{3,8}\b", base.stdout))


def test_h12_columns(rig, fk):
    # TC-087, TC-088, TC-089
    from abf_platform import web_board
    _, c = ready(rig)
    t = c.get(SEL).text
    assert "<colgroup>" in step(t, 5) and "style=" not in t
    css = web_board.STYLE
    assert "table-layout:fixed" in css.replace(" ", "") and "@media (max-width:600px){.ptbl thead{display:none}" in css
    cols = re.findall(r'<col class="(\w+)">', step(t, 5))[:5]
    pct = [int(re.search(r"\.ptbl \.%s\{width:(\d+)%%" % k, css).group(1)) for k in cols]
    assert len(pct) == 5 and sum(pct) == 100
    for got, want in zip(pct, (20, 42, 9, 12, 17)):
        assert abs(got - want) <= 2


def test_h09_english(rig, fk):
    # TC-079
    _, c = ready(rig)
    t = c.get(SEL + "&lang=en").text
    assert STAR_EN in step(t, 5) and STAR_EN in step(t, 4) and "* Required" in step(t, 5) and "* Required" in step(t, 4)
    assert no_cjk(main_of(t))


# ---- US6: size ------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("size,want", [(753702, "736 KB"), (500, "500 B"), (2500000, "2.4 MB"), (1023, "1023 B"), (1024, "1 KB"),
                                       (1048576, "1.0 MB")])
def test_h10_size(rig, fk, size, want):
    # TC-080 .. TC-085
    from test_pipeline_files_action import DIAGRAM
    fk.files = good_files(diagram=dict(DIAGRAM, size=size))
    _, c = ready(rig)
    t = c.get(SEL).text
    assert "流程圖檔：ampliseq_workflow.png（%s）" % want in plain_text(step(t, 3)) and "位元組" not in t


def test_h10_english(rig, fk):
    # TC-086
    _, c = ready(rig)
    three = plain_text(step(c.get(SEL + "&lang=en").text, 3))
    assert "(736 KB)" in three and "bytes" not in three and no_cjk(three)


# ---- US7: wording ---------------------------------------------------------------------------------------------------------------------

def pages(rig, fk):
    """{state name: zh page} of every state the guard reads."""
    ann, c = ready(rig)
    launched(rig, ann, "run-a", params={"orf_start": 5})
    out = {"ready": c.get(SEL + "&src=new").text, "used": c.get(SEL + "&src=used").text, "no pipeline": c.get("/launch").text,
           "from": c.get("/launch?from=run-a").text, "reuse": c.get(SEL + "&params_from=run-a").text,
           "no version": c.get("/launch?pipeline=nf-core/ampliseq&src=new").text,
           "loaded": c.get(post(rig, c, shown_pipeline="x").headers["location"]).text, "refused": post(rig, c, run_name="").text}
    fk.latest = latest(source="stale-cache")
    out["stale"] = c.get("/launch?pipeline=nf-core/ampliseq&src=new").text
    fk.files = loading_files()
    out["loading"] = c.get(SEL).text
    fk.files = error_files()
    out["failed"] = c.get(SEL).text
    fk.files = good_files(diagram={"status": "none"})
    out["no diagram"] = c.get(SEL).text
    rig.user("bob")
    out["no sheet"] = login(rig, "bob").get(SEL).text
    return out


def test_h11_no_banned_word(rig, fk):
    # TC-090, TC-101 .. TC-106
    for state, page in pages(rig, fk).items():
        assert banned_in(page) == [], state
        assert "選用這個樣本" not in page and "用過的" not in page, state


def test_h11_no_banned_word_without_env(rig, fk):
    # TC-107
    rig.user("ann")
    bob = rig.user("bob")
    area_sheet(rig.w, bob)
    t = login(rig, "bob").get(SEL).text
    assert banned_in(t) == [] and "尚無可用的運算環境。" in t


def test_h11_english_has_no_cjk(rig, fk):
    # TC-108 .. TC-112
    ann, c = ready(rig)
    launched(rig, ann, "run-a")
    for url in (SEL, SEL + "&src=used", SEL + "&src=new&params_from=run-a", "/launch?pipeline=nf-core/ampliseq&src=new"):
        assert no_cjk(main_of(c.get(url + "&lang=en").text)), url
    assert no_cjk(main_of(post(rig, c, run_name="", lang="en").text))
    fk.files = loading_files()
    assert no_cjk(main_of(c.get(SEL + "&lang=en").text))
    fk.files = error_files("network", NETWORK)
    assert no_cjk(main_of(c.get(SEL + "&lang=en").text))
    rig.user("bob")
    assert no_cjk(main_of(login(rig, "bob").get(SEL + "&lang=en").text))


def test_h11_guard_catches_every_word():
    # TC-113, TC-114
    for w in BANNED:
        page = '<main class="main" data-pane="middle"><p>前%s後</p></main>' % w
        assert banned_in(page) == [w], w
    assert banned_in('<main class="main" data-pane="middle"><p>請依序完成步驟。</p></main>') == []
    page = ('<aside>還沒有 run。</aside><main class="main" data-pane="middle"><table><tr class="prow"><td>x</td><td>Use this 這個</td></tr></table>'
            '<table><tr class="scol"><td>c</td><td>東西</td></tr></table></main>')
    assert banned_in(page) == []
    page = page.replace("</main>", "<p>這個</p></main>")
    assert banned_in(page) == ["這個"]


def test_h11_old_strings_are_gone(rig, fk):
    # TC-091 .. TC-100
    olds = ["用過的", "新管線（全部 nf-core）", "快速送出", "還沒有用過的管線。", "選好管線後檢查", "選好版本後檢查", "選好管線與版本後顯示", "版本（必填，要寫死）",
            "你還沒有上傳樣本表", "你還沒有可用的運算環境。", "run 名稱", "已用這個 run 的內容預填", "沿用哪一次分析", "使用這一版", "位元組", "這條管線沒有提供流程圖。",
            "讀取中頁面會自動更新，請等讀完再填參數。", "送出，到確認頁", "之後開放", "自己調整", "目前連不到 GitHub", "站台已登記這個"]
    got = pages(rig, fk)
    for state, page in got.items():
        for old in olds:
            assert old not in main_of(page), (state, old)
    news = {"used": ["曾使用的管線", "其他 nf-core 管線", "選用", "沿用設定重新分析", "請依序完成步驟 1 至 7。按下「送出」後將進入確認頁，於確認頁再次送出才會排入佇列。"],
            "no pipeline": ["選定管線後檢查", "尚未選擇", "預覽與欄位角色（尚未開放）", "選定管線與版本後顯示", "分析名稱", "送出（前往確認頁）"],
            "no version": ["選定版本後檢查"], "stale": ["套用此版本", "目前無法連線至 GitHub，以下為"],
            "no diagram": ["此管線未提供流程圖。"], "no sheet": ["尚未上傳樣本表，無法啟動分析。", "尚無可用的運算環境。"],
            "ready": ["樣本表（從已上傳的檔案中選擇）"],
            "from": ["已帶入該次分析的設定；樣本表與分析名稱需重新選擇。"], "loading": ["讀取中，頁面將自動更新；請於讀取完成後再填寫參數。"]}
    for state, words in news.items():
        for w in words:
            assert w in plain_text(main_of(got[state])), (state, w)


def test_h11_design_has_the_word_list():
    # TC-115, TC-116
    text = (REPO / "DESIGN.md").read_text(encoding="utf-8")
    section = text[text.index("## 用字"):]
    assert "書面" in section
    for w in BANNED:
        assert w in section, w


# ---- US8: scope -----------------------------------------------------------------------------------------------------------------------

def test_scope_page_limits(rig, fk):
    # TC-119, TC-121, TC-122, TC-124, TC-125, TC-135
    ann, c = ready(rig)
    launched(rig, ann, "run-a")
    for url in (SEL, SEL + "&src=used", "/launch"):
        t = c.get(url).text
        assert "我的 run" in t and "<script" not in t and "<img" not in t and "<figure" not in t and "style=" not in t
        assert len(re.findall(r"<style", t)) + len(re.findall(r'rel="stylesheet"', t)) == 1
    two = step(c.get(SEL + "&src=new").text, 2)
    assert "搜尋全部 nf-core（尚未開放）" in plain_text(two)
    assert not re.search(r'<input [^>]*name="(?!pipeline|revision)\w+"', re.sub(r'<input type="hidden"[^>]*>', "", two))
    assert re.search(r"✓|✗|…|○", plain_text(step(c.get(SEL).text, 1)))


def test_scope_other_schema_gives_other_cells(rig, fk):
    # TC-141: the cells come from the schema the agent read, not from a fixed list
    from abf_platform import actions
    text = ('{"definitions":{"g":{"title":"G","type":"object","properties":{"zeta":{"type":"integer","default":42}}}},'
            '"allOf":[{"$ref":"#/definitions/g"}]}')
    fk.files = good_files(schema=actions._pf_view("schema", {"status": "ok", "text": text}))
    _, c = ready(rig)
    five = step(c.get(SEL).text, 5)
    assert 'value="42"' in cell(five, "zeta") and cell(five, "orf_start") is None
