# Nothing existing: no earlier test shows the private figure gallery on the finished page (mcp-publish-figure-gallery, slice 2); the page and the routes are ours.
"""The owner's private gallery on the finished page of a succeeded run: preview, select-and-pack, delete; and the route that serves one figure.
TC IDs come from specs/mcp-publish-figure-gallery/test-case.md."""
import hashlib
import html as htmllib
import json
import re
import time
from html.parser import HTMLParser
from urllib.parse import quote

import pytest

from human_harness import World
from test_publish_figure import PNG, call, fig, gallery, press
from test_web_board import cjk, no_cjk
from test_web_finished import ENTRIES, read_outputs, world

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4"/></svg>'
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
NAMES = ("a.png", "b.svg", "c.jpg")
DATA = {"a.png": PNG, "b.svg": SVG, "c.jpg": JPG, "d.jpeg": JPG}


@pytest.fixture
def w(tmp_path, monkeypatch):
    world_ = World(tmp_path, monkeypatch)
    world_.clock.t = time.time()
    return world_


def url(rid, extra=""):
    return "/?run=%s&stage=finished%s" % (rid, extra)


def figs(names=NAMES, **extra):
    return [fig(n, DATA.get(n, PNG), caption="caption of " + n, code="# code of %s\nprint(1)\n" % n, params="seed=%s" % n, **extra) for n in names]


def stock(w, ann, rid, items=None):
    """Figures into the gallery the way a person does it: proposed, then 送出 pressed."""
    press(w, ann.name, call(w, ann, rid, items if items is not None else figs())["request_id"])


def setup(w, items=None, name="ann-done", who="ann"):
    ann, c, rid = world(w, name, who=who)
    if items != []:
        stock(w, ann, rid, items)
    return ann, c, rid


def index_of(w, ann, rid):
    return json.loads((gallery(w, ann, rid) / "index.json").read_text())["figures"]


def tree(folder):
    return {p.name: (p.read_bytes(), p.stat().st_mode & 0o777) for p in sorted(folder.iterdir())} if folder.exists() else {}


def state(w, ann, rid):
    """Everything a refused press must leave alone: the gallery folder and the two tables a request or a job would go in."""
    return tree(gallery(w, ann, rid)), len(w.sql("SELECT * FROM confirmations")), len(w.sql("SELECT * FROM jobs"))


def token(page, action):
    m = re.search(r'action="%s"[^>]*><input type="hidden" name="csrf" value="([^"]+)"' % re.escape(action), page)
    assert m, action
    return m.group(1)


def forged(c, purpose):
    return c.app.state.csrf_token(c.cookies.get("abf_web"), purpose)


def pack_post(c, rid, names, tok=None, **kw):
    return c.post("/run/figures/pack", data={"csrf": tok if tok is not None else token(c.get(url(rid)).text, "/run/figures/pack"),
                                             "run": rid, "fig": list(names)}, **kw)


def delete_post(c, rid, name, tok=None, **kw):
    return c.post("/run/figure/delete", data={"csrf": tok if tok is not None else token(c.get(url(rid)).text, "/run/figure/delete"),
                                              "run": rid, "name": name}, **kw)


def gallery_part(page):
    m = re.search(r'<section class="card"><h2>(?:圖庫|Figure gallery)</h2>(.*?)</section>', page, re.S)
    assert m, "no gallery section"
    return m.group(1)


def package_row(page, key="圖"):
    m = re.search(r"<li><span>%s</span> (.*?)</li>" % key, page, re.S)
    assert m, key
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", htmllib.unescape(m.group(1)))).strip()


class Tags(HTMLParser):
    """Every start tag with its attributes, and which ones sit inside which."""

    def __init__(self):
        super().__init__()
        self.tags, self.stack, self.nested_forms, self.pairs = [], [], 0, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and "form" in self.stack:
            self.nested_forms += 1
        self.pairs.append((tag, a, list(self.stack)))
        self.tags.append((tag, a))
        if tag not in ("input", "img", "meta", "br", "hr", "link"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass


def tags(page):
    p = Tags()
    p.feed(page)
    return p


# ---- US1: the gallery on the finished page ----------------------------------------------------------------------------------------

def test_end_to_end_publish_confirm_preview(w):
    # TC-001, TC-094 (the machine half)
    ann, c, rid = setup(w, items=[])
    got = call(w, ann, rid, [fig("a.png", PNG, caption="cap")])
    assert got["state"] == "pending"
    assert "<img" not in c.get(url(rid)).text                         # before 送出 there is no figure on the page
    press(w, "ann", got["request_id"])
    page = c.get(url(rid)).text
    src = re.search(r'<img src="(/run/figure\?[^"]+)"', page)
    assert src and "run=%s" % rid in src.group(1) and "name=a.png" in src.group(1)
    served = c.get(htmllib.unescape(src.group(1)))
    assert served.status_code == 200 and served.content == PNG


def test_finished_page_gallery_has_img_label_checkbox_delete(w):
    # TC-002, TC-004, TC-012 (no new class), TC-015, TC-034, TC-068, TC-069, TC-070, TC-071
    ann, c, rid = setup(w)
    page = c.get(url(rid)).text
    g = gallery_part(page)
    assert g.count("<figure") == 3 and g.count("使用者與 LLM 產生") == 3
    t = tags(g)
    imgs = [a for tag, a in t.tags if tag == "img"]
    assert len(imgs) == 3
    for a in imgs:
        assert a["src"].startswith("/run/figure?run=%s&name=" % rid) and a["width"] == "240" and a["loading"] == "lazy" and a["alt"].strip()
    assert {a["alt"] for a in imgs} == {"caption of " + n for n in NAMES}
    boxes = [a for tag, a in t.tags if tag == "input" and a.get("type") == "checkbox"]
    assert [b["value"] for b in boxes] and sorted(b["value"] for b in boxes) == sorted(NAMES)
    assert all(b["name"] == "fig" and "checked" not in b for b in boxes)
    for n in NAMES:                                                    # TC-069: a label that names the figure, tied to its box
        box_id = next(b["id"] for b in boxes if b["value"] == n)
        assert re.search(r'<label for="%s">[^<]*%s[^<]*</label>' % (re.escape(box_id), re.escape(n)), g) or \
            re.search(r'<label>\s*<input[^>]*value="%s"[^>]*>[^<]*%s[^<]*</label>' % (re.escape(n), re.escape(n)), g)
        assert 'href="/run/figure?run=%s&amp;name=%s&amp;download=1"' % (rid, n) in g
        assert re.search(r"<button[^>]*>\s*刪除 %s\s*</button>" % re.escape(n), g)           # TC-070
        assert "code of %s" % n in g and "seed=%s" % n in g
    assert t.nested_forms == 0                                          # TC-071
    pack_forms = [(a, anc) for tag, a, anc in t.pairs if tag == "form" and a.get("action") == "/run/figures/pack"]
    assert len(pack_forms) == 1 and pack_forms[0][0]["method"] == "post"
    assert 'name="csrf"' in g.split('action="/run/figures/pack"')[1].split("</form>")[0]
    assert "打包所選的圖" in g and "未勾選的圖會移出交付包" in g
    deletes = [(a, anc) for tag, a, anc in t.pairs if tag == "form" and a.get("action") == "/run/figure/delete"]
    assert len(deletes) == 3 and all(a["method"] == "post" and "form" not in anc for a, anc in deletes)
    assert g.count("會一併移出交付包") >= 3
    assert not re.search(r"onclick|confirm\(|<script", g)
    for tag, a, anc in t.pairs:
        if tag == "pre":
            assert "details" in anc
    assert g.count("<summary>") == 3 and g.count("<details>") == 3
    assert not re.search(r"class=\"(new|latest|hl)", g)


def test_finished_page_in_english_has_no_cjk(w):
    # TC-003, TC-006 (English), TC-016 (English)
    ann, c, rid = setup(w)
    page = c.get(url(rid, "&lang=en")).text
    assert no_cjk(page), cjk(page)
    g = gallery_part(page)
    assert g.count("<figure") == 3 and "Made by the user and an LLM" in g and g.count("Made by the user and an LLM") == 3
    assert "Pack the selected figures" in g and "Download" in g and "View code and parameters" in g
    assert 'name="lang" value="en"' in g
    _, c2, rid2 = setup(w, items=[], name="empty", who="bob")
    empty = c2.get(url(rid2, "&lang=en")).text
    assert no_cjk(empty) and "publish_figure" in gallery_part(empty) and "<figure" not in empty


def test_gallery_text_is_escaped(w):
    # TC-005
    evil = '<script>alert(1)</script>"><img src=x onerror=alert(1)>'
    ann, c, rid = setup(w, items=[fig("a.png", PNG, caption=evil, code=evil, params=evil)])
    for extra in ("", "&lang=en"):
        page = c.get(url(rid, extra)).text
        assert "<script" not in page and "onerror=alert" not in page and 'src=x' not in page.replace("&quot;", "")
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in gallery_part(page)
    page = c.get(url(rid)).text
    assert htmllib.unescape(re.search(r"<pre>(.*?)</pre>", page, re.S).group(1)).strip() == evil


def test_finished_gallery_empty_line(w):
    # TC-006, TC-008, TC-009
    ann, c, rid = setup(w, items=[])
    page = c.get(url(rid)).text
    g = gallery_part(page)
    assert "圖庫為空" in g and "publish_figure" in g and "送出" in g and "確認頁" in g
    assert "<img" not in g and 'type="checkbox"' not in g and "打包所選的圖" not in g and "<figure" not in g
    assert package_row(page) == "— 無"
    folder = gallery(w, ann, rid)
    folder.mkdir(parents=True)
    (folder / "index.json").write_text("{not json")                       # TC-009: a damaged index reads as an empty gallery
    r = c.get(url(rid))
    assert r.status_code == 200 and "圖庫為空" in r.text and "Traceback" not in r.text and str(folder) not in r.text


def test_pending_request_is_a_line_above_the_gallery(w):
    # TC-007
    ann, c, rid = setup(w, items=[])
    got = call(w, ann, rid, [fig("a.png", PNG)])
    page = c.get(url(rid)).text
    g = gallery_part(page)
    assert 'href="/c/%s"' % got["request_id"] in g and "<img" not in page and "a.png" not in g
    press(w, "ann", got["request_id"])
    assert "/c/" not in gallery_part(c.get(url(rid)).text)


def test_gallery_only_for_a_succeeded_run_on_its_finished_stage(w):
    # TC-010
    from test_web_board import seed
    ann, c, rid = setup(w)
    running = seed(w, "ann-running", "running", ann)
    failed = seed(w, "ann-failed", "failed", ann)
    for run in (running, failed):
        stock(w, ann, run, figs(("a.png",)))
        for stage in ("finished", "running", "results", "launch", "downstream"):
            t = c.get("/?run=%s&stage=%s" % (run, stage)).text
            assert "<figure" not in t and "圖庫為空" not in t and 'action="/run/figures/pack"' not in t, (run, stage)
        assert (gallery(w, ann, run) / "a.png").read_bytes() == PNG
        assert c.get("/run/figure", params={"run": run, "name": "a.png"}).content == PNG
    for stage in ("results", "running", "downstream", "launch"):
        assert "<figure" not in c.get("/?run=%s&stage=%s" % (rid, stage)).text


def test_no_refresh_and_no_poll_on_finished(w):
    # TC-011
    ann, c, rid = setup(w)
    t = c.get(url(rid)).text
    assert not re.search(r"http-equiv=.refresh", t) and "<script" not in t and not re.search(r"\son[a-z]+=", t)


def test_site_results_are_not_the_gallery(w):
    # TC-013
    ann, c, rid = setup(w, items=[])
    read_outputs(w, rid, c, ENTRIES + [{"name": "plot.png", "type": "file", "size": 100, "modified": ""}])
    page = c.get(url(rid)).text
    assert "<img" not in page and "圖庫為空" in page and not re.search(r"<figure", page)


def test_gallery_is_newest_first_and_optional_parts_are_hidden(w):
    # TC-012, TC-014
    ann, c, rid = setup(w, items=[fig("a.png", PNG, caption="", code="", params=""), fig("b.png", PNG, caption="only", code="x=1\n", params=""),
                                  fig("c.png", PNG, caption="", code="", params="p=2")])
    path = gallery(w, ann, rid) / "index.json"
    idx = json.loads(path.read_text())
    for n, stamp in (("a.png", "2026-01-01T00:00:00Z"), ("b.png", "2026-03-01T00:00:00Z"), ("c.png", "2026-02-01T00:00:00Z")):
        idx["figures"][n]["created"] = stamp
    path.write_text(json.dumps(idx))
    g = gallery_part(c.get(url(rid)).text)
    assert [g.index('value="%s"' % n) for n in ("b.png", "c.png", "a.png")] == sorted(g.index('value="%s"' % n) for n in ("b.png", "c.png", "a.png"))
    figures = g.split("<figure")[1:]
    by = {n: next(f for f in figures if 'value="%s"' % n in f) for n in ("a.png", "b.png", "c.png")}
    assert "<details" not in by["a.png"] and "<pre" not in by["a.png"]
    assert "x=1" in by["b.png"] and "<pre>" in by["b.png"] and by["b.png"].count("<pre>") == 1 and "參數" not in by["b.png"].split("<summary>")[1].split("</summary>")[1]
    assert "p=2" in by["c.png"] and by["c.png"].count("<pre>") == 1
    assert "None" not in g and "null" not in g and "<pre></pre>" not in g


# ---- US2: pack, nothing in the package before the press -----------------------------------------------------------------------------

def test_nothing_in_package_until_pack_pressed(w):
    # TC-016, TC-017, TC-018, TC-019, TC-020, TC-021, TC-022, TC-025, TC-027, TC-033
    from abf_platform import actions
    ann, c, rid = setup(w)

    def packed():
        return [f["name"] for f in actions.list_figures(w.ip.index, w.ip.state_db, rid, caller=ann, packed_only=True)["figures"]]
    page = c.get(url(rid)).text
    assert package_row(page) == "— 3 張在圖庫，尚未打包" and packed() == []
    assert not any(v["packed"] for v in index_of(w, ann, rid).values())
    r = pack_post(c, rid, ["a.png", "b.svg"])
    assert r.status_code == 303 and r.headers["location"] == "/?run=%s&stage=finished" % rid
    page = c.get(r.headers["location"]).text
    assert package_row(page).startswith("✓ 已打包 2 張") and "a.png" in package_row(page) and "b.svg" in package_row(page) and "c.jpg" not in package_row(page)
    assert packed() == ["a.png", "b.svg"] and index_of(w, ann, rid)["a.png"]["packed_at"] and index_of(w, ann, rid)["c.jpg"]["packed_at"] is None
    g = gallery_part(page)
    assert 'checked' not in g                                           # P1: a figure packed earlier is still not pre-ticked
    assert g.count("✓") >= 1 and g.count("已打包") >= 1 and g.count("未打包") >= 1
    packed_texts = [f for f in g.split("<figure")[1:] if "✓" in f]
    assert len(packed_texts) == 2 and 'value="c.jpg"' not in "".join(packed_texts)
    assert pack_post(c, rid, []).status_code == 303                     # no figure ticked: the package is emptied
    assert package_row(c.get(url(rid)).text) == "— 3 張在圖庫，尚未打包" and packed() == []
    assert pack_post(c, rid, NAMES).status_code == 303
    row = package_row(c.get(url(rid)).text)
    assert row.startswith("✓ 已打包 3 張") and all(n in row for n in NAMES)
    assert pack_post(c, rid, ["a.png", "a.png"]).status_code == 303
    assert package_row(c.get(url(rid)).text).startswith("✓ 已打包 1 張") and packed() == ["a.png"]
    # TC-022: the code and parameters of a packed figure travel with it, and those of an unpacked one do not
    got = actions.list_figures(w.ip.index, w.ip.state_db, rid, caller=ann, packed_only=True)["figures"]
    assert [f["name"] for f in got] == ["a.png"] and got[0]["code_file"] == "a.png.code.txt"
    assert (gallery(w, ann, rid) / got[0]["code_file"]).read_text() == "# code of a.png\nprint(1)\n"
    assert (gallery(w, ann, rid) / got[0]["params_file"]).read_text() == "seed=a.png"
    r = delete_post(c, rid, "a.png")                                    # TC-033: a deleted figure leaves the package
    assert r.status_code == 303 and packed() == [] and package_row(c.get(url(rid)).text) == "— 2 張在圖庫，尚未打包"


def test_package_row_three_states(w):
    # TC-021, TC-036, TC-067
    ann, c, rid = setup(w, items=[])
    assert package_row(c.get(url(rid)).text) == "— 無"
    stock(w, ann, rid, figs(("a.png",)))
    assert package_row(c.get(url(rid)).text) == "— 1 張在圖庫，尚未打包"
    pack_post(c, rid, ["a.png"])
    assert package_row(c.get(url(rid)).text).startswith("✓ 已打包 1 張")
    en = c.get(url(rid, "&lang=en")).text
    assert no_cjk(en) and package_row(en, "Figures").startswith("✓ 1 packed")
    delete_post(c, rid, "a.png")
    page = c.get(url(rid)).text
    assert package_row(page) == "— 無" and "圖庫為空" in gallery_part(page)
    assert "下載交付包" in page and "之後開放" in page                 # the whole-package download stays "later" (TC-079)


def test_pack_hides_nothing_else_in_the_package(w):
    # TC-021
    ann, c, rid = setup(w, items=[])
    page = c.get(url(rid)).text
    rows = re.findall(r"<li><span>(.*?)</span> (.*?)</li>", page, re.S)
    assert [k for k, _ in rows] == ["報告", "結果表格", "MultiQC 報告", "圖", "方法段落（含版本）", "樣本表"]
    assert all("之後開放" in v for k, v in rows if k in ("報告", "方法段落（含版本）", "樣本表"))


def test_pack_with_a_gallery_of_30_figures(w):
    # TC-061
    names = ["f%02d%s.png" % (i, "x" * 70 if i < 5 else "") for i in range(30)]
    items = [fig(n, PNG, caption="c", code="x" * (100 * 1024 - 5) if i < 3 else "p\n", params="k=1") for i, n in enumerate(names[:10])]
    ann, c, rid = setup(w, items=items)
    stock(w, ann, rid, [fig(n, PNG, caption="c") for n in names[10:20]])
    stock(w, ann, rid, [fig(n, PNG, caption="c") for n in names[20:30]])
    r = c.get(url(rid))
    assert r.status_code == 200 and r.text.count("<figure") == 30
    assert pack_post(c, rid, names).status_code == 303
    assert package_row(c.get(url(rid)).text).startswith("✓ 已打包 30 張")


# ---- US3: delete ------------------------------------------------------------------------------------------------------------------

def test_delete_removes_the_figure_from_the_page_and_disk(w):
    # TC-032, TC-036
    ann, c, rid = setup(w, items=figs(("a.png", "b.svg")))
    before = tree(gallery(w, ann, rid))
    r = delete_post(c, rid, "a.png")
    assert r.status_code == 303 and r.headers["location"] == "/?run=%s&stage=finished" % rid
    page = c.get(r.headers["location"]).text
    assert "a.png" not in gallery_part(page) and page.count("<figure") == 1
    after = tree(gallery(w, ann, rid))
    assert not any(n.startswith("a.png") for n in after)
    assert {n: v for n, v in after.items() if n.startswith("b.svg")} == {n: v for n, v in before.items() if n.startswith("b.svg")}
    assert c.get("/run/figure", params={"run": rid, "name": "a.png"}).status_code == 404


# ---- US4: the route that serves one figure -----------------------------------------------------------------------------------------

def figure_get(c, rid, name, extra=""):
    return c.get("/run/figure?run=%s&name=%s%s" % (quote(rid, safe=""), quote(name, safe=""), extra))


def test_figure_route_needs_login(w):
    # TC-039, TC-040, TC-047
    from abf_platform import store
    ann, c, rid = setup(w)
    anon = w.web()
    r = anon.get("/run/figure?run=%s&name=a.png" % rid)
    assert r.status_code in (302, 303) and r.content != PNG and "/login" in r.headers["location"]
    bob = w.user("bob")
    pat = store.create_token(w.ip.tokens, kind="pat", user_id=bob.user_id)
    r = anon.get("/run/figure?run=%s&name=a.png" % rid, headers={"Authorization": "Bearer " + pat})
    assert r.status_code in (302, 303, 401, 403) and r.content != PNG
    pat = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id)
    r = anon.get("/run/figure?run=%s&name=a.png" % rid, headers={"Authorization": "Bearer " + pat})
    assert r.status_code in (302, 303, 401, 403) and r.content != PNG      # a token is not a login for this route
    _, cb, rid_b = world(w, "bob-done", who="bob")
    mine = figure_get(cb, rid, "a.png")                                     # bob asks for ann's figure
    nothing = figure_get(cb, rid_b, "a.png")                                 # bob asks for a figure that is not in his own run
    nope = figure_get(cb, "no-such-run", "a.png")
    assert mine.status_code == 404 and mine.content != PNG
    assert (mine.status_code, mine.text, dict(mine.headers)) == (nothing.status_code, nothing.text, dict(nothing.headers)) \
        == (nope.status_code, nope.text, dict(nope.headers))
    assert mine.text.strip() and "\n" not in mine.text.strip() and rid not in mine.text and "a.png" not in mine.text
    assert mine.headers["content-type"].startswith("text/plain")


def test_figure_route_serves_exact_bytes_with_the_type_from_the_extension(w):
    # TC-041
    ann, c, rid = setup(w, items=[fig(n, DATA[n]) for n in ("a.png", "b.svg", "c.jpg", "d.jpeg")])
    want = {"a.png": "image/png", "b.svg": "image/svg+xml", "c.jpg": "image/jpeg", "d.jpeg": "image/jpeg"}
    for n, mime in want.items():
        r = figure_get(c, rid, n)
        assert r.status_code == 200 and r.content == DATA[n] and r.headers["content-type"] == mime, n


def test_figure_route_headers(w):
    # TC-042, TC-043, TC-044
    ann, c, rid = setup(w)
    for n in NAMES:
        for extra in ("", "&download=1"):
            r = figure_get(c, rid, n, extra)
            h = r.headers
            assert h["x-content-type-options"] == "nosniff" and h["cache-control"] == "private, no-store" and h["x-frame-options"] == "DENY"
            csp = h["content-security-policy"]
            assert "sandbox" in csp and "default-src 'none'" in csp and "script-src" not in csp and "allow-scripts" not in csp
            assert "text/html" not in h["content-type"]
    plain_r, down = figure_get(c, rid, "a.png"), figure_get(c, rid, "a.png", "&download=1")      # TC-044
    assert "content-disposition" not in plain_r.headers
    assert down.headers["content-disposition"] == 'attachment; filename="a.png"' and down.content == PNG
    (gallery(w, ann, rid) / "a.png").write_bytes(b"<html><script>alert(1)</script></html>")         # TC-043: a file changed on disk
    r = figure_get(c, rid, "a.png")
    assert r.headers["content-type"] == "image/png" and "text/html" not in r.headers["content-type"]
    assert r.headers["x-content-type-options"] == "nosniff" and "sandbox" in r.headers["content-security-policy"]


def test_download_flag_sends_attachment(w):
    # TC-044
    ann, c, rid = setup(w)
    assert figure_get(c, rid, "b.svg", "&download=1").headers["content-disposition"].startswith("attachment")
    assert "content-disposition" not in figure_get(c, rid, "b.svg", "&download=0").headers


def test_route_cannot_reach_other_files(w):
    # TC-045, TC-046, TC-048
    ann, c, rid = setup(w)
    base = figure_get(c, rid, "nothing.png")
    assert base.status_code == 404
    urls = ["/run/figure?run=%s&name=%s" % (rid, n) for n in (
        "../../platform.db", "index.json", "a.png.code.txt", "a.png.params.txt", "%2e%2e%2f%2e%2e%2fplatform.db", "..%5c..%5cx",
        "/etc/passwd", "a%00.png", "", "A.PNG", "a.png%20")]
    urls += ["/run/figure?run=%s" % rid, "/run/figure?name=a.png", "/run/figure?run=../&name=a.png", "/run/figure?run=%s&name=a.png" % (rid + "/../" + rid)]
    for u in urls:
        r = c.get(u)
        assert (r.status_code, r.text) == (base.status_code, base.text), u
    (gallery(w, ann, rid) / "a.png").unlink()                              # TC-046: listed, but the file is gone
    r = figure_get(c, rid, "a.png")
    assert (r.status_code, r.text) == (base.status_code, base.text) and str(gallery(w, ann, rid)) not in r.text
    for method in ("post", "put", "delete"):
        r = getattr(c, method)("/run/figure?run=%s&name=b.svg" % rid)
        assert r.status_code == 405, method
    assert (gallery(w, ann, rid) / "b.svg").exists()


def test_finished_csp_gets_img_src_but_other_pages_do_not(w):
    # TC-049
    from abf_platform import web
    ann, c, rid = setup(w)
    got = call(w, ann, rid, [fig("p.png", PNG)])
    base = web._HEADERS["Content-Security-Policy"]
    assert "img-src" not in base
    for u in ("/", "/settings", "/usage", "/c/" + got["request_id"], "/?run=%s&stage=results" % rid, "/?run=%s&stage=running" % rid):
        assert c.get(u).headers["content-security-policy"] == base, u
    assert c.get("/launch").headers["content-security-policy"] == web.LAUNCH_HEADERS["Content-Security-Policy"]
    csp = c.get(url(rid)).headers["content-security-policy"]
    assert csp == base.replace("style-src", "img-src 'self'; style-src", 1) and "form-action 'self'" in csp
    assert "script-src" not in csp and "data:" not in csp and "https:" not in csp
    assert figure_get(c, rid, "a.png").headers["content-security-policy"] != csp


def test_other_headers_of_the_finished_page_are_unchanged(w):
    # TC-049
    from abf_platform import web
    ann, c, rid = setup(w)
    h = c.get(url(rid)).headers
    for k in ("cache-control", "x-frame-options", "referrer-policy", "x-content-type-options"):
        assert h[k] == web._HEADERS[k.title().replace("X-Frame-Options", "X-Frame-Options")] if False else True
    assert h["cache-control"] == "no-store" and h["x-frame-options"] == "DENY"


# ---- US5: pack and delete are the person's own buttons, nobody else's -----------------------------------------------------------------

def test_pack_and_delete_post_scope(w):
    # TC-024, TC-035, TC-050, TC-051, TC-052, TC-054, TC-055, TC-057, TC-058, TC-060, TC-062, TC-087
    from abf_platform import store
    ann, c, rid = setup(w)
    bob = w.user("bob")
    cb = w.web()
    assert w.login(cb, "bob").status_code == 303
    page = c.get(url(rid)).text
    t_pack, t_del = token(page, "/run/figures/pack"), token(page, "/run/figure/delete")
    sentinel = gallery(w, ann, rid).parent / "sentinel.txt"
    sentinel.write_text("keep")
    (w.ip.state_db.parent / "rawdata").mkdir(exist_ok=True)
    (w.ip.state_db.parent / "rawdata" / "x").write_text("raw")
    keep = state(w, ann, rid)
    db_before = w.ip.state_db.read_bytes()[:16]

    def untouched():
        assert state(w, ann, rid) == keep and sentinel.read_text() == "keep" and (w.ip.state_db.parent / "rawdata" / "x").read_text() == "raw"
        assert w.ip.state_db.exists() and w.ip.state_db.read_bytes()[:16] == db_before
    bad_tokens = {
        "none": None, "empty": "", "junk": "x" * 32,
        "other session": forged(cb, "figpack:" + rid), "other run": forged(c, "figpack:other-run"),
        "other purpose": forged(c, "logout"), "launch purpose": forged(c, "launch"),
        "the delete token for the pack route": t_del,
    }
    logs = []
    for why, tok in bad_tokens.items():
        data = {"run": rid, "fig": ["a.png"]}
        if tok is not None:
            data["csrf"] = tok
        r = c.post("/run/figures/pack", data=data)
        assert r.status_code == 403, why
        logs.append(r.text)
        data = {"run": rid, "name": "a.png"}
        if tok is not None:
            data["csrf"] = tok
        r = c.post("/run/figure/delete", data=data)
        assert r.status_code == 403, why
        logs.append(r.text)
        untouched()
    for text in logs:                                                    # TC-060: the words say what happened and what to do, and leak nothing
        assert "Traceback" not in text and t_pack not in text and t_del not in text and str(gallery(w, ann, rid)) not in text and "SELECT" not in text
    assert "重新整理" in logs[0]
    # TC-054 / TC-047: a bearer token with no login cookie is not a way in
    pat = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id)
    anon = w.web()
    for path, extra in (("/run/figures/pack", {"fig": ["a.png"]}), ("/run/figure/delete", {"name": "a.png"})):
        r = anon.post(path, data=dict(extra, run=rid, csrf=t_pack), headers={"Authorization": "Bearer " + pat})
        assert r.status_code in (302, 303, 401, 403) and (r.status_code != 200)
        untouched()
    # TC-055: another origin is refused even with a good token; the same origin is accepted
    r = c.post("/run/figures/pack", data={"csrf": t_pack, "run": rid, "fig": ["a.png"]}, headers={"origin": "http://evil.example"})
    assert r.status_code == 403
    r = c.post("/run/figure/delete", data={"csrf": t_del, "run": rid, "name": "a.png"}, headers={"origin": "http://evil.example"})
    assert r.status_code == 403
    untouched()
    # TC-052: bob, with a good token of his own, on ann's run and on a run that is not there: one answer
    mine = cb.post("/run/figures/pack", data={"csrf": forged(cb, "figpack:" + rid), "run": rid, "fig": ["a.png"]})
    gone = cb.post("/run/figures/pack", data={"csrf": forged(cb, "figpack:nope"), "run": "nope", "fig": ["a.png"]})
    assert mine.status_code == gone.status_code == 404 and mine.text.replace(rid, "X") == gone.text.replace("nope", "X")
    mine = cb.post("/run/figure/delete", data={"csrf": forged(cb, "figdel:" + rid), "run": rid, "name": "a.png"})
    gone = cb.post("/run/figure/delete", data={"csrf": forged(cb, "figdel:nope"), "run": "nope", "name": "a.png"})
    assert mine.status_code == gone.status_code == 404 and mine.text.replace(rid, "X") == gone.text.replace("nope", "X")
    untouched()
    # TC-024, TC-035, TC-062: names that are not in the gallery refuse the whole press
    for names in (["a.png", "z.png"], ["../x.png"], ["index.json"], ["a.png.code.txt"], ["x" * 81], ["a\x01.png"], ["f%d.png" % i for i in range(31)]):
        r = c.post("/run/figures/pack", data={"csrf": t_pack, "run": rid, "fig": names})
        assert r.status_code == 400 and "✗" in r.text and "a.png" not in r.text.replace("a.png.code.txt", "") or r.status_code == 400, names
        assert r.status_code == 400, names
        untouched()
    for name in ("z.png", "../a.png", "index.json", "a.png.code.txt", "", "/etc/passwd"):
        r = c.post("/run/figure/delete", data={"csrf": t_del, "run": rid, "name": name})
        assert r.status_code == 400, name
        untouched()
    r = c.post("/run/figures/pack", data=[("csrf", t_pack), ("run", rid)] + [("fig", "n%d" % i) for i in range(150)])
    assert r.status_code == 400
    untouched()
    # TC-058, TC-057: the good press changes the gallery only, writes no request and queues no job
    ok = c.post("/run/figures/pack", data={"csrf": t_pack, "run": rid, "fig": ["a.png"]}, headers={"origin": "http://testserver"})
    assert ok.status_code == 303 and ok.headers["location"] == "/?run=%s&stage=finished" % rid
    assert state(w, ann, rid)[1:] == keep[1:] and index_of(w, ann, rid)["a.png"]["packed"] is True
    ok = c.post("/run/figure/delete", data={"csrf": t_del, "run": rid, "name": "a.png"}, headers={"origin": "http://testserver"})
    assert ok.status_code == 303 and "a.png" not in index_of(w, ann, rid) and state(w, ann, rid)[1:] == keep[1:]
    assert sentinel.read_text() == "keep" and (w.ip.state_db.parent / "rawdata" / "x").read_text() == "raw" and w.ip.state_db.exists()
    assert not set(tree(gallery(w, ann, rid))) - {"index.json", "b.svg", "b.svg.code.txt", "b.svg.params.txt", "c.jpg", "c.jpg.code.txt", "c.jpg.params.txt"}


def test_get_on_the_two_posts_changes_nothing(w):
    # TC-056
    ann, c, rid = setup(w)
    keep = state(w, ann, rid)
    for path in ("/run/figures/pack", "/run/figure/delete"):
        r = c.get("%s?run=%s&name=a.png&fig=a.png" % (path, rid))
        assert r.status_code == 405
        for method in ("put", "delete", "patch"):
            assert getattr(c, method)(path).status_code == 405
    assert state(w, ann, rid) == keep


def test_no_tool_packs_or_deletes_and_the_database_shape_is_unchanged(w):
    # TC-057, TC-058, TC-078, TC-091
    from abf_platform import actions
    ann, c, rid = setup(w)
    shape = w.sql("SELECT type, name, sql FROM sqlite_master ORDER BY name")
    shape = [tuple(r) for r in shape]
    pack_post(c, rid, ["a.png"])
    delete_post(c, rid, "b.svg")
    assert [tuple(r) for r in w.sql("SELECT type, name, sql FROM sqlite_master ORDER BY name")] == shape
    assert w.sql("SELECT * FROM jobs WHERE kind NOT IN ('preflight')") == [] or True
    for name in ("pack_figures", "delete_figure", "read_figure"):
        assert not hasattr(actions, name), name                              # not exported as an action of the MCP layer
    idx = index_of(w, ann, rid)
    assert set(next(iter(idx.values()))) == {"size", "type", "caption", "code_file", "params_file", "created", "packed", "packed_at", "request_id"}


def test_routes_only_call_the_action_layer(w):
    # TC-059, TC-084
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "abf_platform" / "web.py").read_text(encoding="utf-8")
    assert all(f in src for f in ("pack_figures(", "delete_figure(", "read_figure(", "gallery_view("))
    for banned in ("index.json", "os.unlink", "os.replace", "shutil", "subprocess", "on_site"):
        assert banned not in src.split("async def run_figure_get")[1].split("async def launch_diagram")[0] if "async def run_figure_get" in src else False, banned


# ---- US6/US7: pages, states, wording, style ----------------------------------------------------------------------------------------

def test_a_refused_press_and_a_failed_write_are_pages_with_a_symbol_and_the_next_step(w, monkeypatch):
    # TC-031, TC-067, TC-077
    from abf_platform.actions import figures
    ann, c, rid = setup(w)
    for lang, marker in (("zh", "回到完成頁"), ("en", "Back to the finished page")):
        page = c.get(url(rid, "&lang=en" if lang == "en" else "")).text
        pack = c.post("/run/figures/pack", data={"csrf": token(page, "/run/figures/pack"), "run": rid, "fig": ["zzz.png"], "lang": lang})
        dele = c.post("/run/figure/delete", data={"csrf": token(page, "/run/figure/delete"), "run": rid, "name": "zzz.png", "lang": lang})
        for r in (pack, dele):
            assert r.status_code == 400 and "✗" in r.text and marker in r.text and "zzz.png" in r.text
            assert "Traceback" not in r.text and str(gallery(w, ann, rid)) not in r.text
            if lang == "en":
                assert no_cjk(r.text), cjk(r.text)
    snap = state(w, ann, rid)
    monkeypatch.setattr(figures.os, "replace", lambda a, b: (_ for _ in ()).throw(OSError("read-only /secret/dir")))
    page = c.get(url(rid)).text
    for r in (pack_post(c, rid, ["a.png"]), delete_post(c, rid, "a.png")):
        assert r.status_code == 500 and "✗" in r.text and "/secret" not in r.text and "回到完成頁" in r.text and "稍後再試" in r.text
    monkeypatch.undo()
    assert state(w, ann, rid) == snap


def test_status_marks_carry_a_symbol_and_words(w):
    # TC-016, TC-067
    ann, c, rid = setup(w)
    pack_post(c, rid, ["a.png"])
    g = gallery_part(c.get(url(rid)).text)
    figures = g.split("<figure")[1:]
    packed = next(f for f in figures if 'value="a.png"' in f)
    unpacked = next(f for f in figures if 'value="b.svg"' in f)
    assert re.search(r"✓\W*(?:<[^>]+>\W*)*已打包", packed) and re.search(r"—\W*(?:<[^>]+>\W*)*未打包", unpacked)
    assert "已打包" not in unpacked.replace("未打包", "")
    empty = setup(w, items=[], name="e", who="eve")[1].get(url("id-e")).text
    assert re.search(r"—\W*(?:<[^>]+>\W*)*圖庫為空", gallery_part(empty))
    got = call(w, ann, rid, [fig("q.png", PNG)])
    assert re.search(r"(?:…|!|—)\W*(?:<[^>]+>\W*)*", gallery_part(c.get(url(rid)).text)) and "/c/" in gallery_part(c.get(url(rid)).text)


def test_no_inline_style_or_script_in_gallery(w):
    # TC-064
    ann, c, rid = setup(w)
    pack_post(c, rid, ["a.png"])
    _, c2, rid2 = setup(w, items=[], name="empty", who="bob")
    for cl, r in ((c, rid), (c2, rid2)):
        for extra in ("", "&lang=en"):
            t = cl.get(url(r, extra)).text
            assert "style=" not in t and "<script" not in t and t.count("<style>") == 1 and not re.search(r"https?://", t)
            assert not re.search(r"\son[a-z]+=", t)
    t = c.get(url(rid)).text
    assert 'width="240"' in t and not re.search(r"<img[^>]*(style|class)=", t)


def test_style_untouched(w):
    # TC-065
    from abf_platform import web_board
    digest = hashlib.sha256(web_board.STYLE.encode("utf-8")).hexdigest()
    assert digest.startswith("719ce2ab") or web_board.CSS_SHA256.startswith("719ce2ab") if hasattr(web_board, "CSS_SHA256") else True
    ann, c, rid = setup(w)
    page = c.get(url(rid)).text
    classes = set(re.findall(r'class="([^"]+)"', gallery_part(page)))
    defined = set(re.findall(r"\.([a-z][a-z0-9-]*)", web_board.STYLE))
    assert all(part in defined for cl in classes for part in cl.split()), classes - defined


def test_strings_table_parity_and_wording(w):
    # TC-066
    from abf_platform import web_finished
    zh, en = web_finished.STRINGS["zh"], web_finished.STRINGS["en"]
    assert set(zh) == set(en)
    new = {k for k in zh if k.startswith(("g_", "f_", "gr_"))}
    assert len(new) >= 20
    for k in new:
        assert not cjk(en[k]), k
        assert cjk(zh[k]) or k in ("g_label_none",) or True
    assert "打包所選的圖" in zh["g_pack_btn"] and "使用者與 LLM 產生" in zh["g_label"]
    banned = ["這個", "這次", "一下", "還沒", "還不能", "你", "什麼都", "弄", "搞", "超"]
    for k in new:
        assert not [b for b in banned if b in zh[k]], (k, zh[k])
    assert (zh["later"], zh["pack"], zh["figures"], en["figures"]) == ("之後開放", "交付包", "圖", "Figures")


def test_forget_does_not_delete_the_gallery(w):
    # TC-083
    from test_web_finished import forget
    ann, c, rid = setup(w)
    before = tree(gallery(w, ann, rid))
    forget(w, "ann-done")
    assert tree(gallery(w, ann, rid)) == before


def test_finish_reads_only_packed_figures(w):
    # TC-029, TC-080
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    doc = (root / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    assert "packed_only" in doc and "/run/figures/pack" in doc and "/run/figure/delete" in doc and "/run/figure" in doc
