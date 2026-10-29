# Nothing existing: tests of status-squares-3 (every analysis state on the web is a small coloured square plus a word, three states only).
"""status-squares-3: the test cases (TC-001 ...) are named in the comments; they are in the task's specs folder."""
import base64
import hashlib
import re
import time

import pytest

from human_harness import World
from test_web_board import no_cjk, pane, plain, seed, strip_cells, style_of
from test_web_v2_skeleton import left_rows

NOW = time.time()
GLYPHS = "▶✓✗⏸⟳"
WORDS = {"zh": {"running": "執行中", "succeeded": "完成", "failed": "失敗", "lost": "失敗"},
         "en": {"running": "Running", "succeeded": "Done", "failed": "Failed", "lost": "Failed"}}
ORDER = ("running", "succeeded", "failed", "lost")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def four(w):
    ann = w.user("ann")
    ids = {st: seed(w, "s-" + st, st, ann, started=NOW - 3600, counts=dict(succeeded=1, failed=1 if st == "failed" else 0),
                    reason="boom\nreal reason" if st == "failed" else None) for st in ORDER}
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    return c, ids


def q(lang):
    return "&lang=en" if lang == "en" else ""


def status_areas(text):
    """The HTML of the places that show an analysis state: left, right, the head, the step strip and the info table of the middle."""
    mid = pane(text, "middle")
    head = re.search(r'<div class="head">.*?</div>', mid, re.S)
    steps = re.search(r'<ol class="steps".*?</ol>', mid, re.S)
    info = re.search(r'<dl class="fields">.*?</dl>', mid, re.S)
    return [pane(text, "left"), pane(text, "right")] + [m.group(0) for m in (head, steps, info) if m]


def pages(c, ids, lang):
    out = [c.get("/?" + q(lang).lstrip("&")).text]
    for st, rid in ids.items():
        out.append(c.get("/?run=%s%s" % (rid, q(lang))).text)
        out.append(c.get("/?run=%s&tab=info%s" % (rid, q(lang))).text)
        for stage in ("launch", "running", "results", "downstream", "finished"):
            out.append(c.get("/?run=%s&stage=%s%s" % (rid, stage, q(lang))).text)
        out.append(c.get("/launch?from=s-%s%s" % (st, q(lang))).text)
    out.append(c.get("/settings?" + q(lang).lstrip("&")).text)
    return out


def test_ss01_no_state_glyphs(w):
    # TC-016, TC-017, TC-018
    from abf_platform import web_board
    c, ids = four(w)
    for lang in ("zh", "en"):
        for text in pages(c, ids, lang):
            for area in status_areas(text):
                assert not any(g in area for g in GLYPHS), (lang, [g for g in GLYPHS if g in area])
    assert not hasattr(web_board, "SYMBOLS") and not hasattr(web_board, "_sym")
    for lang in ("zh", "en"):                                  # the cost page: its status column (running = square + word)
        usage = pane(c.get("/usage?" + q(lang).lstrip("&")).text, "middle")
        assert "s-running" in usage and not any(g in usage for g in GLYPHS), lang
        assert '<span class="state-running"><span class="sq"></span> %s</span>' % WORDS[lang]["running"] in usage, lang
    t = c.get("/launch?from=s-lost").text
    assert not any(g in re.search(r'<p class="from">.*?</p>', t, re.S).group(0) for g in GLYPHS)


def test_ss02_three_words_with_square(w):
    # TC-001..TC-007, TC-012, TC-013, TC-019, TC-020, TC-021, TC-023
    c, ids = four(w)
    for lang in ("zh", "en"):
        words = WORDS[lang]
        board = c.get("/?" + q(lang).lstrip("&")).text
        rows = left_rows(board)
        for st in ORDER:                                   # square before the name, word on the right, lost shown as failed
            row = [r for r in rows if "s-" + st in r[2]][0]
            assert row[2] == "s-%s %s" % (st, words[st]), row
            html = re.search(r'<a class="(row[^"]*)" href="[^"]*run=%s[^"]*">(.*?)</a>' % ids[st], board, re.S)
            assert html.group(2).index('class="sq"') < html.group(2).index('class="nm"')
            assert "state-" + ("failed" if st == "lost" else st) in html.group(1)
        for st in ORDER:
            css = "failed" if st == "lost" else st
            text = c.get("/?run=%s%s" % (ids[st], q(lang))).text            # the badge of the head: square right before the word
            assert re.search(r'<span class="badge state-%s"><span class="sq"></span> ?%s</span>' % (css, words[st]), text)
            url = "/?run=%s&stage=results&tab=info%s" if st == "succeeded" else "/?run=%s&tab=info%s"
            info = c.get(url % (ids[st], q(lang))).text                     # the info table
            assert re.search(r'<span class="chip state-%s"><span class="sq"></span> ?%s</span>' % (css, words[st]), info), (lang, st)
            for gone in (("失聯", "成功") if lang == "zh" else ("Lost", "Succeeded")):
                assert gone not in text and gone not in info, (lang, st, gone)
            launch = c.get("/launch?from=s-%s%s" % (st, q(lang))).text
            assert re.search(r'<span class="chip state-%s"><span class="sq"></span> ?%s</span>' % (css, words[st]), launch)
            seen = set(x.strip() for x in re.findall(r'class="(?:chip|badge)[^"]*"><span class="sq"></span>([^<]+)<', text + info + launch))
            assert seen <= set(words.values()), seen
    assert "state-lost" not in board


def test_ss02_stage_strip_squares(w):
    # TC-008, TC-009, TC-010, TC-011
    c, ids = four(w)
    sq = lambda cell, kind: ('<span class="state-%s"><span class="sq"></span></span>' % kind) in cell
    cells = strip_cells(c.get("/?run=" + ids["running"]).text)
    assert sq(cells["launch"][1], "succeeded") and sq(cells["running"][1], "running")
    assert all('class="sq"' not in cells[s][1] for s in ("results", "downstream", "finished"))
    for st in ("failed", "lost"):
        cells = strip_cells(c.get("/?run=" + ids[st]).text)
        assert sq(cells["launch"][1], "succeeded") and sq(cells["running"][1], "failed")
        assert all('class="sq"' not in cells[s][1] for s in ("results", "downstream", "finished"))
    cells = strip_cells(c.get("/?run=" + ids["succeeded"]).text)
    assert sq(cells["launch"][1], "succeeded") and sq(cells["running"][1], "succeeded")
    assert all('class="sq"' not in cells[s][1] for s in ("downstream", "finished"))
    for lang, names in (("zh", ["送出", "執行中", "結果", "下游", "完成"]), ("en", ["Launch", "Running", "Results", "Downstream", "Finished"])):
        cells = strip_cells(c.get("/?run=%s%s" % (ids["succeeded"], q(lang))).text)
        assert [plain(cells[s][1]) for s in ("launch", "running", "results", "downstream", "finished")] == names


def test_ss03_unknown_status_grey(w):
    # TC-014, TC-015, TC-019
    from abf_platform import web_board
    for lang, word in (("zh", "未知"), ("en", "Unknown")):
        t = web_board.STRINGS[lang]
        run = {"id": "x", "name": "weird-run", "status": "weird", "started_at": None, "ended_at": None}
        chip = web_board._chip(t, "weird")
        row = web_board._row(t, dict(run, failed_tasks=[]), None, lang)
        info = web_board.tab_body(t, lang, run, "info")
        for html in (chip, info):
            assert re.search(r'<span class="chip state-unknown"><span class="sq"></span> ?%s</span>' % word, html)
        assert 'class="row state-unknown' in row and word in plain(row) and "weird" not in plain(row).replace("weird-run", "")
        for html in (chip, row, info):
            assert "?" not in plain(html).replace("weird-run", "") and not any(g in html for g in GLYPHS)
            for known in ("執行中", "完成", "失敗", "Running", "Done", "Failed"):
                assert known not in plain(html)
    css = style_of(web_board.document("t", ""))
    rule = re.search(r"\.state-unknown\{([^}]*)\}", css).group(1)
    assert "var(--" in rule and "#" not in rule


def test_ss04_lost_detail_kept(w):
    # TC-031, TC-032, TC-033, TC-034, TC-C01
    c, ids = four(w)
    zh = c.get("/?run=" + ids["lost"]).text
    assert "站台無回應" in plain(pane(zh, "right")) and "執行 · 站台無回應" in plain(pane(zh, "left"))
    assert "步驟" in plain(pane(zh, "right")) and "<form" in pane(zh, "right")
    en = c.get("/?run=%s&lang=en" % ids["lost"]).text
    assert "Site not responding" in plain(pane(en, "right")) and "Run · Site not responding" in plain(pane(en, "left"))
    right = pane(c.get("/?run=" + ids["failed"]).text, "right")
    assert "real reason" in right and "<form" in right
    board = c.get("/").text
    for st in ("failed", "lost"):
        assert 'href="/?run=%s"' % ids[st] in board


def test_ss04_notice_level_is_state_square(w):
    # TC-024..TC-030
    c, ids = four(w)
    for lang in ("zh", "en"):
        for st in ("failed", "lost"):
            t = c.get("/?run=%s%s" % (ids[st], q(lang))).text
            assert re.search(r'<span class="level state-failed"><span class="sq"></span> ?%s</span>' % WORDS[lang][st], pane(t, "right"))
            bad = ("失聯", "待處理") if lang == "zh" else ("Lost", "Pending")
            rest = re.sub(r"<dt>Pending</dt>", "", t)
            assert not any(b in rest for b in bad), (lang, st)
        for st in ("running", "succeeded"):
            t = c.get("/?run=%s%s" % (ids[st], q(lang))).text
            assert ("目前無通知" if lang == "zh" else "No notices") in pane(t, "right")
            assert "沒有待處理" not in t and "Nothing pending" not in t


def test_ss04_task_counts(w):
    # TC-022, TC-052
    c, ids = four(w)
    labels = lambda t: re.findall(r"<dt>([^<]+)</dt>\s*<dd>\d+</dd>", pane(t, "middle"))
    zh = labels(c.get("/?run=" + ids["running"]).text)
    en = labels(c.get("/?run=%s&lang=en" % ids["running"]).text)
    assert zh == ["完成", "快取", "失敗", "中止", "執行中", "等待", "已送出"]
    assert en == ["Done", "Cached", "Failed", "Aborted", "Running", "Pending", "Submitted"]


def test_ss05_constraints(w):
    # TC-035, TC-036, TC-037
    c, ids = four(w)
    for lang in ("zh", "en"):
        for text in pages(c, ids, lang):
            assert "<script" not in text and " style=" not in text and not re.search(r"\son[a-z]+=", text) and text.count("<style>") == 1
            if lang == "en":
                assert no_cjk(text)
        resp = c.get("/?run=%s%s" % (ids["failed"], q(lang)))
        digest = "'sha256-%s'" % base64.b64encode(hashlib.sha256(style_of(resp.text).encode()).digest()).decode()
        assert digest in resp.headers["Content-Security-Policy"]


def test_ss05_empty_and_missing(w):
    # TC-046, TC-047
    w.user("ann")
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    t = c.get("/").text
    assert "尚無分析" in t and 'class="sq"' not in t and not any(g in t for g in GLYPHS)
    r = c.get("/?run=nope-id")
    assert r.status_code == 404 and 'class="sq"' not in r.text and "nope-id" not in r.text
