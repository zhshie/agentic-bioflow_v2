# Nothing existing: tests of guided-launch-2 (the launch page reads the pipeline's own files through the site agent: parameter-table check, latest version,
# workflow-diagram link, samplesheet columns, parameter group table); the page and the route /launch/diagram are ours.
"""guided-launch-2: /launch with the five new blocks, offline. The test cases are named in the comments (TC-001 ...); they are in
specs/guided-launch-2. The two read actions (`pipeline_files`, `latest_release`) are replaced by a fake that gives the answer the site agent would
have given (built with the real `actions._pf_view` from the fixture files), so no job is queued and nothing connects out."""
import base64
import html
import re
import socket

import pytest

from helpers import REPO_ROOT
from test_pipeline_files_action import DIAGRAM, INPUT_TEXT, PNG, SCHEMA_TEXT
from test_web_actions import area_sheet, form_values, login, pending
from test_web_board import no_cjk
from test_web_guided_launch import SEL, ready, rig  # noqa: F401  (rig is a fixture)

NETWORK = "代理連不到 GitHub，請檢查那台機器的網路 (the agent could not reach GitHub; check that machine's network)"
NOT_FOUND = "GitHub 上找不到這個版本需要的檔案，請確認 pipeline 名稱與版本 (the files were not found on GitHub; check the pipeline name and revision)"
REFRESH = '<meta http-equiv="refresh" content="15">'
NEW = "/launch?pipeline=nf-core/ampliseq&src=new"
DIAGRAM_URL = "/launch/diagram?pipeline=nf-core/ampliseq&amp;revision=2.18.0"


def A():
    from abf_platform import actions
    return actions


def good_files(**over):
    a = A()
    out = {"state": "ready", "pipeline": "nf-core/ampliseq", "revision": "2.18.0", "parts": ["schema", "schema_input", "diagram"],
           "checked_at": 1_800_000_000.0, "error": None, "reason": None,
           "schema": a._pf_view("schema", {"status": "ok", "text": SCHEMA_TEXT}),
           "schema_input": a._pf_view("schema_input", {"status": "ok", "text": INPUT_TEXT}), "diagram": dict(DIAGRAM), "image": None}
    out.update(over)
    return out


def loading_files():
    return good_files(state="loading", checked_at=None, schema=None, schema_input=None, diagram=None)


def error_files(code="network", reason=NETWORK):
    return good_files(state="error", error=code, reason=reason, schema=None, schema_input=None, diagram=None)


def good_image(**over):
    out = good_files(parts=["image"], schema=None, schema_input=None, diagram=None, image=dict(DIAGRAM, data_b64=base64.b64encode(PNG).decode()))
    out.update(over)
    return out


def latest(state="ready", source="fetched", revision="2.18.0", **over):
    out = {"state": state, "pipeline": "nf-core/ampliseq", "revision": revision if state == "ready" else None, "source": source,
           "checked_at": 1_800_000_000.0 if state == "ready" else None, "why": None, "error": None}
    out.update(over)
    return out


class Fake:
    def __init__(self):
        self.files, self.image, self.latest = good_files(), good_image(), latest()
        self.pf, self.lr = [], []

    def pipeline_files(self, platform_path, pipeline, revision, *, parts=None, compute_env=None, caller=None, enqueue=True):
        self.pf.append({"pipeline": pipeline, "revision": revision, "parts": parts, "caller": caller, "enqueue": enqueue, "ce": compute_env})
        return self.image if parts == ["image"] else self.files

    def latest_release(self, platform_path, pipeline, *, compute_env=None, caller=None, enqueue=True):
        self.lr.append({"pipeline": pipeline, "caller": caller})
        return self.latest

    def main_calls(self):
        return [c for c in self.pf if c["parts"] != ["image"]]


@pytest.fixture
def fk(monkeypatch):
    f = Fake()
    a = A()
    monkeypatch.setattr(a, "pipeline_files", f.pipeline_files)
    monkeypatch.setattr(a, "latest_release", f.latest_release)

    def no_connect(*args, **kw):      # TC-092: the platform itself never connects out
        raise AssertionError("the platform connected out")
    monkeypatch.setattr(socket.socket, "connect", no_connect)
    return f


def plain_text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def step(text, n):
    """The html of step n, nested <details> included (the groups of step 5 are <details> too)."""
    parts = re.split(r'(?=<details class="gstep )', text)
    mine = [p for p in parts if 'data-step="%d"' % n in p[:120]]
    assert mine, n
    return mine[0]


def row(text, label):
    for m in re.finditer(r'<li class="chk[^"]*">(.*?)</li>', step(text, 1), re.S):
        if label in m.group(1):
            return plain_text(m.group(1))
    return None


def sample_counts():
    return len(groups()), sum(len(g["params"]) for g in groups())


def groups():
    from abf_platform import schema
    return schema.parameter_groups(schema.load(SCHEMA_TEXT))


def input_cols():
    from abf_platform import schema
    return schema.samplesheet_columns(schema.load(INPUT_TEXT))


def get(c, url="", **extra):
    return c.get((url or SEL) + "".join("&%s=%s" % kv for kv in extra.items()))


# ---- US1: step 1 ----------------------------------------------------------------------------------------------------------------------

def test_g01_ready_row_counts(rig, fk):
    # TC-001
    _, c = ready(rig)
    n, m = sample_counts()
    assert row(get(c).text, "讀取管線參數表") == "✓ 讀取管線參數表 讀到 %d 組、%d 個參數" % (n, m)


def test_g01_loading_row_and_refresh(rig, fk):
    # TC-002, TC-010, TC-011
    fk.files = loading_files()
    _, c = ready(rig)
    t = get(c).text
    assert row(t, "讀取管線參數表") == "… 讀取管線參數表 讀取中"
    assert REFRESH in t and "讀取中，頁面每 15 秒自動更新。" in step(t, 1)
    assert "讀取中，頁面將自動更新；請於讀取完成後再填寫參數。" in step(t, 5) and "<textarea" in step(t, 5)      # guided-launch-2b: formal wording


@pytest.mark.parametrize("code,reason,half", [("network", NETWORK, "代理連不到 GitHub，請檢查那台機器的網路"),
                                              ("not_found", NOT_FOUND, "GitHub 上找不到這個版本需要的檔案，請確認 pipeline 名稱與版本")])
def test_g01_error_rows(rig, fk, code, reason, half):
    # TC-003, TC-004, TC-008
    fk.files = error_files(code, reason)
    _, c = ready(rig)
    t = get(c).text
    line = row(t, "讀取管線參數表")
    assert line.startswith("✗ 讀取管線參數表") and half in line and "the agent" not in line and "were not found" not in line
    assert "前置檢查未通過" in step(t, 7) and "✗ 讀取管線參數表" in plain_text(step(t, 7))


def test_g01_schema_not_ok_row(rig, fk):
    # TC-005
    fk.files = good_files(schema={"status": "bad_json", "message": "參數表不是合法的 JSON (the parameter table is not valid JSON)"})
    _, c = ready(rig)
    assert row(get(c).text, "讀取管線參數表") == "✗ 讀取管線參數表 參數表不是合法的 JSON。"


def test_g01_no_refresh_when_all_ready(rig, fk):
    # TC-006, TC-012
    _, c = ready(rig)
    t = get(c).text
    assert "http-equiv" not in t and "讀取中頁面會自動更新" not in t


def test_g01_no_revision(rig, fk):
    # TC-007
    _, c = ready(rig)
    t = c.get("/launch?pipeline=nf-core/ampliseq&src=used").text
    assert row(t, "讀取管線參數表") == "○ 讀取管線參數表 選定版本後檢查"      # guided-launch-2b: formal wording
    assert "　選定版本後檢查" in step(t, 1)
    assert "讀取管線參數表" not in step(t, 7) and fk.main_calls() == []      # the missing revision is a problem of its own; this row is not one


def test_g01_failed_row_does_not_stop_the_send(rig, fk):
    # TC-009, TC-108
    fk.files = error_files()
    _, c = ready(rig)
    before = pending(rig)
    r = c.post("/launch", data=form_values(rig, c, "ann", **{"p.FW_primer": "AAA"}))
    assert r.status_code == 303 and r.headers["location"].startswith("/c/") and pending(rig) == before + 1


def test_g01_nothing_without_a_pipeline(rig, fk):
    # TC-013
    _, c = ready(rig)
    t = c.get("/launch").text
    assert fk.pf == [] and fk.lr == [] and "http-equiv" not in t


# ---- US2: step 2 latest ---------------------------------------------------------------------------------------------------------------

def test_g02_latest_called_once_for_the_caller(rig, fk):
    # TC-014, TC-021, TC-022
    _, c = ready(rig)
    t = c.get(NEW).text
    assert len(fk.lr) == 1 and fk.lr[0]["caller"].name == "ann" and fk.lr[0]["pipeline"] == "nf-core/ampliseq" and fk.pf == []
    two = step(t, 2)
    assert re.search(r'<input [^>]*name="pipeline"', two) and re.search(r'<input [^>]*name="revision"', two)
    assert "搜尋全部 nf-core（尚未開放）" in plain_text(two)      # guided-launch-2b: formal wording


def test_g02_latest_ready_and_link(rig, fk):
    # TC-015, TC-016, TC-017
    _, c = ready(rig)
    two = step(c.get(NEW).text, 2)
    assert "最新版本：2.18.0" in plain_text(two) and "目前無法連線至 GitHub" not in two
    href = re.search(r'<a href="([^"]+)">套用此版本</a>', two).group(1)
    assert "pipeline=nf-core/ampliseq" in href and "revision=2.18.0" in href
    nxt = c.get(html.unescape(href)).text
    assert re.search(r'name="revision" value="2.18.0"', nxt) or 'value="2.18.0"' in step(nxt, 2)


def test_g02_stale_cache(rig, fk):
    # TC-018
    fk.latest = latest(source="stale-cache")
    _, c = ready(rig)
    from abf_platform import web_board
    when = web_board.taipei_time(1_800_000_000.0)
    assert "目前無法連線至 GitHub，以下為 %s 的查詢結果。" % when in plain_text(step(c.get(NEW).text, 2))      # guided-launch-2b: formal wording


def test_g02_latest_loading_and_error(rig, fk):
    # TC-019, TC-020
    fk.latest = latest(state="loading")
    _, c = ready(rig)
    t = c.get(NEW).text
    assert "… 讀取中" in plain_text(step(t, 2)) and REFRESH in t
    fk.latest = latest(state="error", why="沒有可用的 release tag (no usable release tag)", error="no_release")
    t = c.get(NEW).text
    assert "✗ 沒有可用的 release tag。" in plain_text(step(t, 2)) and "no usable" not in t


def test_g02_not_for_the_used_tab_or_with_a_revision(rig, fk):
    # TC-023, TC-024
    _, c = ready(rig)
    c.get("/launch?pipeline=nf-core/ampliseq&src=used")
    c.get(SEL + "&src=new")
    assert fk.lr == []


# ---- US3: step 3 ----------------------------------------------------------------------------------------------------------------------

def test_g03_link_with_name_and_size(rig, fk):
    # TC-025, TC-026, TC-027, TC-043
    _, c = ready(rig)
    t = get(c).text
    three = step(t, 3)
    assert 'href="%s">開啟流程圖</a>' % DIAGRAM_URL in three and "ampliseq_workflow.png" in three and "736 KB" in three      # guided-launch-2b: KB, not bytes
   
    assert 'data-state="done"' in three[:200] and "<img" not in t and "<figure" not in t
    for gone in ("本次值", "將執行的階段", "README"):
        assert gone not in t


def test_g03_none_loading_failed(rig, fk):
    # TC-028, TC-029, TC-030
    _, c = ready(rig)
    fk.files = good_files(diagram={"status": "none"})
    three = step(get(c).text, 3)
    assert "此管線未提供流程圖。" in three and 'data-state="done"' in three[:200] and "開啟流程圖" not in three
    fk.files = loading_files()
    t = get(c).text
    assert 'data-state="later"' in step(t, 3)[:200] and "… 讀取中" in plain_text(step(t, 3)) and REFRESH in t
    fk.files = good_files(diagram={"status": "not_found", "message": "GitHub 上找不到流程圖 (the diagram was not found)"})
    three = step(get(c).text, 3)
    assert 'data-state="later"' in three[:200] and "✗ GitHub 上找不到流程圖。" in plain_text(three)


def test_g03_image_loading_and_failed(rig, fk):
    # TC-031, TC-032
    _, c = ready(rig)
    fk.image = good_image(state="loading", image=None)
    t = get(c).text
    assert "開啟流程圖" not in step(t, 3) and "圖檔讀取中" in step(t, 3) and REFRESH in t
    fk.image = good_image(image={"status": "too_large", "message": "檔案太大，沒有讀 (the files are too large to read)"})
    three = step(get(c).text, 3)
    assert "開啟流程圖" not in three and "✗ 檔案太大，沒有讀。" in plain_text(three)


def test_g03_not_chosen(rig, fk):
    # TC-033
    _, c = ready(rig)
    for url in ("/launch", "/launch?pipeline=nf-core/ampliseq&src=used"):
        three = step(c.get(url).text, 3)
        assert "選定管線與版本後顯示" in three and "之後開放" not in three


def test_g03_calls(rig, fk):
    # TC-034, TC-093, TC-095
    _, c = ready(rig)
    get(c)
    assert [(x["parts"], x["enqueue"], x["caller"].name) for x in fk.pf] == [(None, True, "ann"), (["image"], True, "ann")] and fk.lr == []
    fk.pf.clear()
    fk.files = good_files(diagram={"status": "none"})
    get(c)
    assert len(fk.pf) == 1
    bob = rig.user("bob")
    area_sheet(rig.w, bob)
    fk.pf.clear()
    get(login(rig, "bob"))
    assert fk.pf and {x["caller"].name for x in fk.pf} == {"bob"}


# ---- /launch/diagram ------------------------------------------------------------------------------------------------------------------

DIA = "/launch/diagram?pipeline=nf-core/ampliseq&revision=2.18.0"


def test_g04_png(rig, fk):
    # TC-035, TC-036
    _, c = ready(rig)
    r = c.get(DIA)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content == PNG
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "private, max-age=3600"


def test_g04_svg(rig, fk):
    # TC-037
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"
    fk.image = good_image(image=dict(DIAGRAM, name="x.svg", type="image/svg+xml", data_b64=base64.b64encode(svg).decode()))
    _, c = ready(rig)
    r = c.get(DIA)
    assert r.headers["content-type"].startswith("image/svg+xml") and r.content == svg
    assert r.headers["content-security-policy"] == "default-src 'none'; style-src 'unsafe-inline'"


def test_g04_not_ready_is_404(rig, fk):
    # TC-038, TC-039
    _, c = ready(rig)
    for image in (good_image(state="loading", image=None), good_image(state="error", error="network", reason=NETWORK, image=None),
                  good_image(image={"status": "too_large", "message": "x"}), good_image(image=None)):
        fk.image = image
        r = c.get(DIA)
        assert r.status_code == 404 and r.headers["content-type"].startswith("text/plain") and "<" not in r.text and len(r.text.splitlines()) == 1


def test_g04_login_rules(rig, fk):
    # TC-040, TC-041
    rig.user("ann")
    r = rig.w.web().get(DIA)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    from test_temp_password import login_temp
    c, _, _ = login_temp(rig.w, "ann")
    r = c.get(DIA)
    assert r.status_code == 303 and r.headers["location"] == "/welcome"


def test_g04_caller_and_arguments(rig, fk):
    # TC-042
    rig.user("ann")
    bob = rig.user("bob")
    area_sheet(rig.w, bob)
    c = login(rig, "bob")
    c.get(DIA)
    assert len(fk.pf) == 1 and fk.pf[0]["caller"].name == "bob" and fk.pf[0]["parts"] == ["image"] and fk.pf[0]["enqueue"] is False


# ---- US4: step 4 ----------------------------------------------------------------------------------------------------------------------

def test_g05_table(rig, fk):
    # TC-044 .. TC-049, TC-053
    _, c = ready(rig)
    t = get(c).text
    four = step(t, 4)
    cols = input_cols()
    assert re.findall(r"<th>([^<]*)</th>", re.search(r'<table class="tbl scols">.*?</table>', four, re.S).group(0)) == ["欄名", "說明"]      # guided-launch-2b: no 必填 column
    rows = re.findall(r'<tr class="scol"><td>([^<]*)(<span class="req" title="必填">\*</span>)?</td><td>([^<]*)</td></tr>', four)
    assert [r[0] for r in rows] == [x["name"] for x in cols]
    assert [bool(r[1]) for r in rows] == [bool(x["required"]) for x in cols]      # guided-launch-2b: the red star replaces the ✓ and the —
    assert [html.unescape(r[2]) for r in rows] == [x["description"] for x in cols]
    assert four.index("</select>") < four.index('class="tbl scols"')
    for x in cols:
        assert not x["pattern"] or (html.escape(x["pattern"]) not in t and x["pattern"] not in t)
    assert "樣本名" not in four and "R1" not in four


def test_g05_loading_failed_and_preview(rig, fk):
    # TC-050, TC-051, TC-052
    _, c = ready(rig)
    fk.files = loading_files()
    t = get(c).text
    assert "… 讀取中" in plain_text(step(t, 4)) and REFRESH in t
    fk.files = good_files(schema_input={"status": "bad_json", "message": "樣本表欄位檔不是合法的 JSON (not valid JSON)"})
    four = step(get(c).text, 4)
    assert "✗ 樣本表欄位檔不是合法的 JSON。" in plain_text(four) and "scols" not in four
    assert "預覽與欄位角色（尚未開放）" in plain_text(four)


# ---- US5: step 5 groups ---------------------------------------------------------------------------------------------------------------

def five_of(c):
    return step(get(c).text, 5)


def test_g06_groups_order_and_open(rig, fk):
    # TC-054, TC-055, TC-062, TC-063
    _, c = ready(rig)
    five = five_of(c)
    titles = re.findall(r'<details class="pgroup[^"]*"[^>]*><summary>([^<]*)</summary>', five)
    want = [g["title"] for g in groups() if any(not p["hidden"] for p in g["params"])]
    assert [html.unescape(x) for x in titles[:-1]] == want and "進階" in titles[-1]
    assert len(re.findall(r'<details class="pgroup[^"]*" open>', five)) == 1 and re.search(r'<details class="pgroup" open><summary>%s' % re.escape(want[0]), five)
    assert five.index('class="pgroups"') < five.index("<textarea") and five.index('name="params_from"') < five.index('class="pgroups"')
    assert 'name="route"' not in five      # guided-launch-2b: the three routes are gone


def test_g06_rows_and_widgets(rig, fk):
    # TC-056 .. TC-061
    _, c = ready(rig)
    five = five_of(c)
    allp = {p["name"]: p for g in groups() for p in g["params"]}
    plain = next(p for p in allp.values() if p["types"] == ["string"] and p["has_default"] and not p["enum"] and not p["hidden"]
                 and isinstance(p["default"], str) and p["default"] and "&" not in p["default"] and "<" not in p["default"])
    m = re.search(r'<tr class="prow">(?:(?!</tr>).)*?<td>%s(?:(?!</tr>).)*</tr>' % re.escape(plain["name"]), five, re.S)
    assert m and 'value="%s"' % html.escape(plain["default"]) in m.group(0) and "<input " in m.group(0)      # guided-launch-2b: the default is the value, not a placeholder
    assert 'name="p.%s"' % plain["name"] in m.group(0) and html.escape(plain["description"][:20]) in m.group(0) and "string" in m.group(0)
    enum = next(p for p in allp.values() if p["enum"] and not p["hidden"])
    sel = re.search(r'<select name="p\.%s"[^>]*>(.*?)</select>' % re.escape(enum["name"]), five, re.S).group(1)
    assert re.findall(r'<option value="([^"]*)"', sel) == [""] + [html.escape(str(x)) for x in enum["enum"]]
    boo = next(p for p in allp.values() if p["types"] == ["boolean"] and not p["hidden"])
    sel = re.search(r'<select name="p\.%s"[^>]*>(.*?)</select>' % re.escape(boo["name"]), five, re.S).group(1)
    assert re.findall(r'<option value="([^"]*)"', sel) == ["", "true", "false"]
    num = next(p for p in allp.values() if p["types"][:1] in (["integer"], ["number"]) and not p["hidden"] and not p["enum"])
    assert re.search(r'<input [^>]*name="p\.%s"' % re.escape(num["name"]), five)
    mark = five.index("進階參數（管線預設隱藏）")
    hidden = [p["name"] for p in allp.values() if p["hidden"]]
    assert hidden and all('name="p.%s"' % h in five[mark:] for h in hidden) and not any('name="p.%s"' % h in five[:mark] for h in hidden)
    req = [p["name"] for p in allp.values() if p["required"] and not p["has_default"]]
    marked = re.findall(r'<td>([^<]*)<span class="req" title="必填">\*</span>', five)
    assert req and [html.unescape(x).strip() for x in marked] == req


def test_g06_states(rig, fk):
    # TC-064, TC-065, TC-066
    _, c = ready(rig)
    fk.files = loading_files()
    five = five_of(c)
    assert "… 讀取中" in plain_text(five) and "<textarea" in five and "pgroups" not in five
    fk.files = error_files()
    five = five_of(c)
    assert "✗ 代理連不到 GitHub，請檢查那台機器的網路。" in plain_text(five) and "<textarea" in five
    five = step(c.get("/launch").text, 5)
    assert "參數分組表：讀到參數表後顯示" in five and "之後開放" not in five and "<textarea" in five


# ---- US5: p.* merge -------------------------------------------------------------------------------------------------------------------

TYPES = {"depth": ["integer"], "ratio": ["number"], "flag": ["boolean"], "name": ["string"], "code": ["string"], "mixed": ["integer"]}


def test_g07_pure_function(rig):
    from abf_platform import web_board, web_launch
    t = web_board.STRINGS["zh"]
    merge = web_launch.merge_params
    assert merge("", {"a": "", "b": "  "}, {}) == ""                                         # TC-067
    assert merge("x: 1", {}, {}) == "x: 1"
    assert merge("FW: BBB", {"FW": "AAA"}, {}) == "FW: BBB"                                  # TC-068
    assert merge("", {"depth": "5"}, TYPES) == "depth: 5"                                    # TC-069
    assert merge("", {"ratio": "0.5"}, TYPES) == "ratio: 0.5"                                # TC-070
    assert merge("", {"flag": "true"}, TYPES) == "flag: true" and merge("", {"flag": "false"}, TYPES) == "flag: false"      # TC-071
    assert merge("", {"name": "AAA", "code": "123"}, TYPES).splitlines() == ["name: AAA", 'code: "123"']                    # TC-072
    assert merge("", {"mixed": "abc"}, TYPES) == "mixed: abc"                                # TC-073
    got = merge("", {"depth": "5", "ratio": "0.5", "flag": "true", "name": "AAA", "code": "123"}, TYPES)
    assert web_board.parse_params(got, t)[0] == {"depth": 5, "ratio": 0.5, "flag": True, "name": "AAA", "code": "123"}
    assert merge("a: 1", {"b": "2"}, {}) == "a: 1\nb: 2"
    assert merge("a: 1\n", {"b": "x"}, {}) == "a: 1\nb: x"
    assert web_launch.fields_of({"p.a": "1", "pipeline": "x", "p.": "y", "p.bad key": "z"}) == {"a": "1"}


def box(t):
    return html.unescape(re.search(r'<textarea [^>]*name="params"[^>]*>(.*?)</textarea>', t, re.S).group(1))


def test_g07_get_merges(rig, fk):
    # TC-074, TC-077, TC-078, TC-079
    _, c = ready(rig)
    t = get(c, **{"p.FW_primer": "AAA"}).text      # guided-launch-2b: a filled box of the table stays in its box and is listed in the summary
    assert "FW_primer: AAA" in plain_text(step(t, 7)) and re.search(r'name="p.FW_primer"[^>]*value="AAA"', t) and box(t) == ""
    t = get(c, route="defaults", **{"p.FW_primer": "AAA"}).text                       # TC-077: `route` is ignored now
    assert re.search(r'name="p.FW_primer"[^>]*value="AAA"', t) and "FW_primer: AAA" in plain_text(step(t, 7))
    t = get(c, route="defaults", params="x%3A+1").text                                # TC-078: `route` is ignored now, the typed box stays
    assert box(t) == "x: 1"
    t = get(c, **{"p.FW_primer": "", "p.outdir": ""}).text                           # TC-079
    assert box(t) == ""
    t = get(c, params="FW_primer%3A+BBB", route="custom", **{"p.FW_primer": "AAA"}).text
    assert box(t) == "FW_primer: BBB"


def test_g07_typed_from_the_schema(rig, fk):
    # TC-069 through the page
    _, c = ready(rig)
    allp = {p["name"]: p for g in groups() for p in g["params"]}
    num = next(n for n, p in allp.items() if p["types"][:1] == ["integer"] and not p["enum"])
    assert "%s: 7" % num in plain_text(step(get(c, **{"p." + num: "7"}).text, 7))      # guided-launch-2b: the summary, not the box


class Spy:
    def __init__(self, monkeypatch):
        self.calls = []
        real = A().request_launch

        async def spy(platform_path, **kw):
            self.calls.append(kw)
            return await real(platform_path, **kw)
        monkeypatch.setattr(A(), "request_launch", spy)


def test_g07_post(rig, fk, monkeypatch):
    # TC-075, TC-076, TC-077, TC-079, TC-080, TC-081
    spy = Spy(monkeypatch)
    _, c = ready(rig)
    r = c.post("/launch", data=form_values(rig, c, "ann", **{"p.FW_primer": "AAA", "p.enum_free": "not-in-enum"}))
    assert r.status_code == 303 and spy.calls[-1]["params"] == {"FW_primer": "AAA", "enum_free": "not-in-enum"}      # TC-075, TC-081
    r = c.post("/launch", data=form_values(rig, c, "ann", params="FW_primer: BBB", **{"p.FW_primer": "AAA"}))
    assert r.status_code == 303 and spy.calls[-1]["params"] == {"FW_primer": "BBB"}                                  # TC-076
    r = c.post("/launch", data=form_values(rig, c, "ann", params="a: 1"))
    assert r.status_code == 303 and spy.calls[-1]["params"] == {"a": 1}                                              # TC-080
    r = c.post("/launch", data=form_values(rig, c, "ann", **{"p.x": ""}))
    assert r.status_code == 303 and spy.calls[-1]["params"] is None                                                  # TC-079
    r = c.post("/launch", data=form_values(rig, c, "ann", route="defaults", **{"p.FW_primer": "AAA"}))
    assert r.status_code == 303 and spy.calls[-1]["params"] == {"FW_primer": "AAA"}                                  # TC-077


def test_g07_post_types_from_the_schema(rig, fk, monkeypatch):
    # TC-069 on the send: the types come from the read that never queues a job
    spy = Spy(monkeypatch)
    _, c = ready(rig)
    allp = {p["name"]: p for g in groups() for p in g["params"]}
    num = next(n for n, p in allp.items() if p["types"][:1] == ["integer"] and not p["enum"])
    r = c.post("/launch", data=form_values(rig, c, "ann", **{"p." + num: "7"}))
    assert r.status_code == 303 and spy.calls[-1]["params"] == {num: 7}
    assert all(x["enqueue"] is False for x in fk.pf if x["parts"] is None and x["revision"] == "2.18.0" and x is fk.pf[-1])


# ---- US6: English, limits, words ------------------------------------------------------------------------------------------------------

def test_g08_english_every_state(rig, fk):
    # TC-082 .. TC-087
    _, c = ready(rig)
    seen = []
    bad = {"status": "bad_json", "message": "參數表不是合法的 JSON (the parameter table is not valid JSON)"}
    for files in (good_files(), loading_files(), error_files(), good_files(diagram={"status": "none"}), good_files(schema=bad), good_files(schema_input=bad)):
        fk.files = files
        for image in (good_image(), good_image(state="loading", image=None),
                      good_image(image={"status": "too_large", "message": "檔案太大，沒有讀 (the files are too large to read)"})):
            fk.image = image
            t = get(c, lang="en").text
            seen.append(t)
            assert no_cjk(t)
    assert any("The agent could not reach GitHub" in s for s in seen)       # TC-087
    n, m = sample_counts()
    assert any("Read %d groups, %d parameters" % (n, m) in s for s in seen)
    for latest_ in (latest(), latest(source="stale-cache"), latest(state="loading"), latest(state="error", why="沒有可用的 release tag (no usable release tag)")):
        fk.latest = latest_
        assert no_cjk(c.get(NEW + "&lang=en").text), latest_
    assert "No usable release tag" in c.get(NEW + "&lang=en").text
    fk.latest = latest()
    t = c.get(NEW + "&lang=en").text
    assert "Latest version: 2.18.0" in t and "Apply this version" in t
    fk.files, fk.image = good_files(), good_image()
    t = get(c, lang="en").text
    assert "Advanced parameters (hidden by default in the pipeline)" in t and "Open the workflow diagram" in t and 'title="Required"' in t


def test_g09_limits(rig, fk):
    # TC-088 .. TC-091, TC-096
    from abf_platform import web_board
    _, c = ready(rig)
    for files in (good_files(), loading_files(), error_files()):
        fk.files = files
        for lang in ("", "&lang=en"):
            r = c.get(SEL + lang)
            t = r.text
            assert "<script" not in t and "style=" not in t and len(re.findall(r"<style\b", t)) == 1 and "<link" not in t
            csp = r.headers["content-security-policy"]
            assert csp == "default-src 'none'; style-src %s; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" % web_board.style_source()
    for sel in (".pgroup", ".ptbl", ".scols", ".req"):
        for _, body in re.findall(r"([^{}]*%s[^{}]*)\{([^}]*)\}" % re.escape(sel), web_board.STYLE):
            assert "#" not in body and "rgb" not in body, body


def test_g09_status_lines_have_symbol_and_words(rig, fk):
    # TC-094, TC-097
    _, c = ready(rig)
    for files in (good_files(), loading_files(), error_files()):
        fk.files = files
        for line in re.findall(r'<li class="chk[^"]*">(.*?)</li>', step(get(c).text, 1), re.S):
            text = plain_text(line)
            assert text[0] in "✓✗…○—" and len(text) > 3, text
    three = plain_text(step(get(c).text, 3))
    assert "你" not in three and "!" not in three


def test_g10_one_get_shows_everything(rig, fk):
    # TC-093, TC-098
    _, c = ready(rig)
    t = get(c).text
    assert len(fk.pf) <= 2 and len(fk.lr) == 0
    assert "讀到" in step(t, 1) and "開啟流程圖" in step(t, 3) and "scols" in step(t, 4) and "pgroups" in step(t, 5)


def test_g11_other_pipeline(rig, fk):
    # TC-109
    from abf_platform import schema
    other = (REPO_ROOT / "tests" / "fixtures" / "schema_input" / "rnaseq-3.27.0.json").read_text(encoding="utf-8")
    fk.files = good_files(schema_input=A()._pf_view("schema_input", {"status": "ok", "text": other}))
    _, c = ready(rig)
    four = step(get(c).text, 4)
    names = [x["name"] for x in schema.samplesheet_columns(schema.load(other))]
    assert re.findall(r'<tr class="scol"><td>([^<]*)(?:<span class="req" title="必填">\*</span>)?</td>', four) == names and names != [x["name"] for x in input_cols()]


def test_g12_no_path_in_a_reason(rig, fk):
    # TC-110
    path = "/ho" + "me/x/y/file"      # written in pieces: the scan of test_scope TC-072 bars such a path in this package
    fk.files = error_files(reason="讀不到 %s (cannot read %s)" % (path, path))
    _, c = ready(rig)
    t = get(c).text
    assert path not in t and "…" in row(t, "讀取管線參數表")


def test_g13_missing_agent_sentence(rig):
    # TC-087, TC-110 (the real action, no fake): the refusal of a missing agent reads English first, Chinese in parentheses
    rig.user("ann")      # the first person to exist owns what the setup made; zed owns nothing
    rig.user("zed")
    c = login(rig, "zed")
    en = c.get(SEL + "&lang=en").text
    assert no_cjk(en) and "No online agent of yours" in en
    zh = c.get(SEL).text
    assert "沒有在線的代理，請先啟動你的代理並建立計算環境。" in zh and "start your agent" not in zh


def test_g14_a_refused_form_queues_no_job(rig, fk):
    # TC-080 (a form that is refused makes no request): the page it comes back with only looks, it queues nothing
    _, c = ready(rig)
    fk.pf.clear()
    r = c.post("/launch", data=form_values(rig, c, "ann", run_name=""))
    assert r.status_code == 400 and fk.pf and all(x["enqueue"] is False for x in fk.pf) and "http-equiv" not in r.text
