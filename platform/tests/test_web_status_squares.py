# Nothing existing: tests of web-status-squares (coloured square + word for the four states everywhere); the pages and words are ours.
"""web-status-squares: the automatic TCs of specs/web-status-squares (TC-001 .. TC-083). Runs are seeded straight into index.db."""
import base64
import hashlib
import re
import subprocess
from pathlib import Path

import pytest

from human_harness import World
from test_web_board import login, pane, plain, seed, style_of

GLYPHS = "▶✓✗⏸⚡"
WORDS = {"zh": {"running": "執行中", "lost": "待處理", "failed": "失敗", "succeeded": "完成", "weird": "未知"},
         "en": {"running": "Running", "lost": "Pending", "failed": "Failed", "succeeded": "Done", "weird": "Unknown"}}
SQ = '<span class="sq"></span>'
ROOT = Path(__file__).resolve().parents[2]
CJK = re.compile(r"[一-鿿]")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def world(w, extra=()):
    ann = w.user("ann")
    for name, st in (("r1", "running"), ("l1", "lost"), ("f1", "failed"), ("s1", "succeeded")) + tuple(extra):
        seed(w, name, "failed" if st == "weird" else st, ann, reason="boom happened" if st == "failed" else None,
             counts=dict(succeeded=11, cached=12, failed=13, aborted=14, running=15, pending=16, submitted=17))
        if st == "weird":
            from abf_platform import store
            con = store.connect_index(w.ip.index)
            with con:
                con.execute("UPDATE runs SET final_status='weird' WHERE id=?", ("id-" + name,))
            con.close()
    return login(w, "ann")


def lq(lang):
    return "&lang=en" if lang == "en" else ""


def home(c, lang):
    return c.get("/?lang=en" if lang == "en" else "/").text


def all_pages(c, lang, names):
    out = {"now": home(c, lang)}
    for n in names:
        out[n] = c.get("/?run=id-%s%s" % (n, lq(lang))).text
        for st in ("launch", "running", "results", "downstream", "finished"):
            out["%s-%s" % (n, st)] = c.get("/?run=id-%s&stage=%s%s" % (n, st, lq(lang))).text
        for tab in ("tasks", "logs", "info", "config", "metrics"):
            out["%s-%s" % (n, tab)] = c.get("/?run=id-%s&tab=%s%s" % (n, tab, lq(lang))).text
    return out


def visible(t):
    return plain(re.sub(r"<style>.*?</style>", "", t, flags=re.S))


def card(text, which):
    return re.search(r'<section\b[^>]*data-card="%s"[^>]*>(.*?)</section>' % which, pane(text, "middle"), re.S).group(1)


def tally_html(page):
    return re.search(r'<p\b[^>]*class="[^"]*\btally\b[^"]*"[^>]*>(.*?)</p>', pane(page, "right"), re.S).group(1)


def tally_text(page):
    return plain(tally_html(page))


@pytest.mark.parametrize("lang", ["zh", "en"])
def test_tc001_to_008_tc030_to_034_each_state_place_is_square_plus_word(w, lang):
    # TC-001 .. TC-008, TC-030 .. TC-034
    c = world(w)
    for name, st in (("r1", "running"), ("l1", "lost"), ("f1", "failed"), ("s1", "succeeded")):
        page = c.get("/?run=id-%s%s" % (name, lq(lang))).text
        word = WORDS[lang][st]
        left = [r for r in re.findall(r'<a\b[^>]*class="[^"]*\brow\b[^"]*"[^>]*>.*?</a>', pane(page, "left"), re.S) if name in plain(r)]
        assert any(SQ + " " + word in x and "state-" + st in x for x in left), (name, left)
        right = [i for i in re.findall(r'<a\b[^>]*class="[^"]*\bitem\b[^"]*"[^>]*>.*?</a>', pane(page, "right"), re.S) if name in plain(i)]
        assert right and SQ + " " + word in right[0] and "state-" + st in right[0]
        badge = re.search(r'<span class="badge state-%s">(<span class="sq"></span> [^<]*)</span>' % st, pane(page, "middle"))
        assert badge and badge.group(1) == SQ + " " + word
        info = c.get("/?run=id-%s&tab=info%s" % (name, lq(lang))).text
        assert SQ + " " + word in pane(info, "middle")
    now = home(c, lang)
    assert re.search(r'state-running[^>]*>.*?%s %s' % (re.escape(SQ), WORDS[lang]["running"]), card(now, "running"), re.S)
    old = ("成功", "失聯", "暫停") if lang == "zh" else ("Succeeded", "Lost", "Paused")
    allowed = r"與站台失去聯絡|Lost contact with the site|三次心跳沒有回應|問題 失聯|Problem Lost"
    for key, page in all_pages(c, lang, ("r1", "l1", "f1", "s1")).items():
        vis = re.sub(allowed, "", visible(page))
        for g in GLYPHS:
            assert g not in vis, (key, g)
        for o in old:
            assert o not in vis, (key, o)
    assert "Done" in visible(c.get("/?run=id-s1&lang=en").text) or lang == "zh"


@pytest.mark.parametrize("lang", ["zh", "en"])
def test_tc009_tc015_notice_texts_unchanged_and_level_pill_kept(w, lang):
    # TC-009, TC-015
    c = world(w)
    now = home(c, lang)
    title, cause = ("與站台失去聯絡", "三次心跳沒有回應") if lang == "zh" else ("Lost contact with the site", "No heartbeat three times in a row")
    assert title in now and cause in now and "boom happened" in now
    assert re.search(r'<span class="level state-lost">%s %s</span>' % (re.escape(SQ), WORDS[lang]["lost"]), now)
    assert re.search(r'<span class="level state-failed">%s %s</span>' % (re.escape(SQ), WORDS[lang]["lost"]), now)


def test_tc010_tc013_tc067_colours(w):
    # TC-010, TC-013, TC-067
    c = world(w)
    css = style_of(c.get("/").text)
    light = css.split("@media")[0]
    for tok, val in (("running", "#0b5aa8"), ("succeeded", "#1b6837"), ("failed", "#b0261d"), ("lost", "#865700")):
        assert "--%s:%s" % (tok, val) in light
        assert re.search(r"\.state-%s\{--c:var\(--%s\)" % (tok, tok), css)
    assert re.search(r"\.state-unknown\{--c:var\(--(muted|line2)\)", css), "unknown square must be a neutral grey token"
    base = subprocess.run(["git", "show", "220320a:platform/abf_platform/web_board.py"], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8").stdout
    old = set(re.findall(r"#[0-9a-fA-F]{6}", base))
    assert set(re.findall(r"#[0-9a-fA-F]{6}", css)) <= old, "no colour code that the base style sheet did not already have"


@pytest.mark.parametrize("lang", ["zh", "en"])
def test_tc011_tc012_tc014_tc026_unknown_state_and_no_lone_square(w, lang):
    # TC-011, TC-012, TC-014, TC-026
    c = world(w, extra=(("wd", "weird"),))
    word = WORDS[lang]["weird"]
    for key, page in all_pages(c, lang, ("wd", "r1")).items():
        for m in re.finditer(r'<span class="sq[^"]*"></span>([^<]*)', page):
            assert m.group(1).strip(), (key, "lone square")
    page = c.get("/?run=id-wd%s" % lq(lang)).text
    assert re.search(r'state-unknown[^>]*>.*?%s %s' % (re.escape(SQ), word), pane(page, "left"), re.S)
    assert SQ + " " + word in pane(page, "right") and SQ + " " + word in pane(page, "middle")
    assert "?" not in plain(pane(page, "left")) and "?" not in plain(pane(page, "right"))
    want = "執行中 1 待處理 1 失敗 1 完成 1" if lang == "zh" else "Running 1 Pending 1 Failed 1 Done 1"
    assert tally_text(page) == want


def test_tc020_tc021_tc024_tc025_tc027_tally(w):
    # TC-020, TC-021, TC-024, TC-025, TC-027
    ann = w.user("ann")
    for n, st, k in (("a", "running", 1), ("b", "lost", 3), ("c", "succeeded", 1)):
        for i in range(k):
            seed(w, "%s%d" % (n, i), st, ann)
    c = login(w, "ann")
    assert tally_text(home(c, "zh")) == "執行中 1 待處理 3 失敗 0 完成 1"
    en = home(c, "en")
    assert tally_text(en) == "Running 1 Pending 3 Failed 0 Done 1"
    assert not any(g in tally_text(en) for g in GLYPHS + "!")
    parts = re.findall(r'<span class="state-(\w+)">%s ([^<]*)</span>' % re.escape(SQ), tally_html(en))
    assert [p[0] for p in parts] == ["running", "lost", "failed", "succeeded"]
    assert tally_text(c.get("/?run=id-a0").text) == tally_text(home(c, "zh"))


def test_tc022_failed_and_lost_counted_apart(w):
    # TC-022
    ann = w.user("ann")
    for n, st, k in (("a", "running", 2), ("b", "failed", 2), ("c", "lost", 1), ("d", "succeeded", 3)):
        for i in range(k):
            seed(w, "%s%d" % (n, i), st, ann)
    assert tally_text(login(w, "ann").get("/").text) == "執行中 2 待處理 1 失敗 2 完成 3"


@pytest.mark.parametrize("lang,want", [("zh", "執行中 0 待處理 0 失敗 0 完成 0"), ("en", "Running 0 Pending 0 Failed 0 Done 0")])
def test_tc023_empty_tally_keeps_shape(w, lang, want):
    # TC-023
    w.user("ann")
    assert tally_text(home(login(w, "ann"), lang)) == want


def test_tc035_data_value_unchanged(w):
    # TC-035
    c = world(w)
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    assert con.execute("SELECT final_status FROM runs WHERE id='id-s1'").fetchone()[0] == "succeeded"
    con.close()
    assert "Done" in visible(c.get("/?run=id-s1&lang=en").text)


@pytest.mark.parametrize("lang,want", [("zh", ["完成", "快取", "失敗", "中止", "執行中", "等待", "已送出"]),
                                       ("en", ["Done", "Cached", "Failed", "Aborted", "Running", "Pending", "Submitted"])])
def test_tc040_to_042_count_cells(w, lang, want):
    # TC-040, TC-041, TC-042
    c = world(w)
    t = c.get("/?run=id-s1%s" % lq(lang)).text
    cells = re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", re.search(r'<dl class="counts">(.*?)</dl>', t, re.S).group(1))
    assert [a for a, _ in cells] == want and [b for _, b in cells] == ["11", "12", "13", "14", "15", "16", "17"]


def steps(page):
    return {m.group(1): m.group(2) for m in re.finditer(r'<li class="[^"]*" data-step="(\w+)">(.*?)</li>', page, re.S)}


def test_tc050_to_054_stage_bar(w):
    # TC-050 .. TC-054
    c = world(w)
    want = {"s1": {"launch": "succeeded", "running": "succeeded", "results": "succeeded"},
            "r1": {"launch": "succeeded", "running": "running"},
            "f1": {"launch": "succeeded", "running": "failed"},
            "l1": {"launch": "succeeded", "running": "lost"}}
    for name, marks in want.items():
        cells = steps(c.get("/?run=id-%s" % name).text)
        assert list(cells) == ["launch", "running", "results", "downstream", "finished"]
        for stage, cell in cells.items():
            if stage in marks:
                assert re.search(r'<span class="sq state-%s"></span>' % marks[stage], cell), (name, stage, cell)
            else:
                assert "sq" not in cell, (name, stage)
        assert not any(g in "".join(cells.values()) for g in GLYPHS)
    zh = [plain(x) for x in steps(c.get("/?run=id-s1").text).values()]
    en = [plain(x) for x in steps(c.get("/?run=id-s1&lang=en").text).values()]
    assert zh == ["送出", "執行中", "結果", "下游", "完成"] and en == ["Launch", "Running", "Results", "Downstream", "Finished"]


@pytest.mark.parametrize("lang", ["zh", "en"])
def test_tc060_to_064_technical_rules(w, lang):
    # TC-060 .. TC-064
    c = world(w, extra=(("wd", "weird"),))
    for key, page in all_pages(c, lang, ("r1", "wd", "f1")).items():
        assert "<script" not in page and not re.search(r"\son\w+=", page) and 'style="' not in page, key
        assert page.count("<style>") == 1 and "<link" not in page, key
    r = c.get("/?run=id-f1%s" % lq(lang))
    digest = base64.b64encode(hashlib.sha256(style_of(r.text).encode()).digest()).decode()
    assert "sha256-" + digest in r.headers["content-security-policy"]
    from abf_platform import web_board
    assert set(web_board.STRINGS["zh"]) == set(web_board.STRINGS["en"])


def test_tc063_english_page_has_no_chinese(w):
    # TC-063
    c = world(w, extra=(("wd", "weird"),))
    for key, page in all_pages(c, "en", ("r1", "wd", "f1", "l1", "s1")).items():
        assert not CJK.search(visible(page).replace("中", "")), key  # 中 is the language switch


def test_tc070_to_074_docs():
    # TC-070, TC-071, TC-072, TC-074
    d = open(ROOT / "DESIGN.md", encoding="utf-8").read()
    head = re.search(r"^## States.*$", d, re.M).group(0).lower()
    assert "square" in head and "word" in head and "symbol + text + colour" not in head
    states = d.split("## States", 1)[1].split("\n", 2)[1]
    assert not any(g in states for g in "▶✓✗⏸…⟳✎?!") and "square" in states.lower()
    notices = [ln for ln in d.splitlines() if ln.startswith("Box with:")][0]
    pill = notices.split("analysis name")[0]
    assert "symbol + text" not in pill and not any(g in pill for g in "✓⟳?!") and "square" in pill
    t = open(ROOT / "docs" / "TESTING.md", encoding="utf-8").read()
    step3 = [ln for ln in t.splitlines() if ln.startswith("3. Turn a screenshot of step 1 black and white")][0]
    assert not any(g in step3 for g in "▶✓✗⏸") and all(x in step3 for x in ("執行中", "待處理", "失敗", "完成"))


def test_tc080_tc083_files_not_touched():
    # TC-080, TC-083
    base = subprocess.run(["git", "merge-base", "HEAD", "220320a"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "220320a"
    changed = subprocess.run(["git", "diff", "--name-only", base, "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert "platform/abf_platform/store.py" not in changed and "platform/abf_platform/web.py" not in changed
    assert "platform/tests/test_confirm_page.py" not in changed
