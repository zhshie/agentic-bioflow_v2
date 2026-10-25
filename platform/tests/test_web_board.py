# Nothing existing: tests of the read-only board of spec 011a (web design v1: GET /, GET /settings); the page, its stage rule and its limits are ours.
"""011a: the web shell after web design v1. Test cases are named in the comments (TC-H01a, TC-S10 ...). Runs are seeded straight into index.db and launches."""
import ast
import base64
import calendar
import hashlib
import html as htmllib
import logging
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from helpers import PLATFORM_DIR
from human_harness import PASSWORD, World

WEB = PLATFORM_DIR / "abf_platform" / "web.py"
BOARD = PLATFORM_DIR / "abf_platform" / "web_board.py"
STAGES = ("launch", "running", "results", "downstream", "finished")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def seed(w, name, status="running", owner=None, started=None, counts=None, reason=None, run_id=None, launch_row=True, ended=None):
    """One run in index.db (its status as the page will derive it) and a launches row naming `owner` (a Caller, or None for NULL)."""
    from abf_platform import store
    rid = run_id or "id-" + name
    started = int(started if started is not None else time.time() - 3600)
    c = dict(succeeded=0, cached=0, failed=0, aborted=0, running=0, pending=0, submitted=0)
    c.update(counts or {})
    final = status if status in ("succeeded", "failed") else None
    last = time.time() if status == "running" else (time.time() - 10 ** 6 if status == "lost" else started + 100)
    con = store.connect_index(w.ip.index)
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, final_status, started_at, ended_at, last_message_at, failure_reason,"
                    " n_succeeded, n_cached, n_failed, n_aborted, n_running, n_pending, n_submitted) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (rid, "s-" + rid, name, final, started, (ended if ended is not None else started + 100) if final else None, last, reason,
                     c["succeeded"], c["cached"], c["failed"], c["aborted"], c["running"], c["pending"], c["submitted"]))
    con.close()
    if launch_row:
        con = store.connect_state(w.ip.state_db)
        with con:
            con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)",
                        (name, "/f/" + name, "lab-a", "agent-t", time.time(), owner.user_id if owner is not None else None))
        con.close()
    return rid


def login(w, name):
    c = w.web()
    r = w.login(c, name)
    assert r.status_code == 303, r.text
    return c


def consent_page(w, name):
    """A real OAuth consent page (the same way test_oauth_consent.py gets one), for `name` logged in."""
    from oauth_harness import Rig
    rig = Rig(w)
    path, _verifier, _cid = rig.start()
    rig.log_in(name)
    r = rig.c.get(path)
    assert r.status_code == 200 and "\u5141\u8a31" in r.text, r.text
    return r


def hrefs(text):
    return re.findall(r'href="([^"]*)"', text)


def pane(text, name):
    """The HTML of one of the three columns (data-pane left, middle, right); they follow each other in this order in the page."""
    order = ["left", "middle", "right"]
    rest = text.split('data-pane="%s"' % name)[1]
    for later in order[order.index(name) + 1:]:
        rest = rest.split('data-pane="%s"' % later)[0]
    return rest


def plain(html_text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_text)).strip()


def style_of(text):
    return re.search(r"<style>(.*?)</style>", text, re.S).group(1)


def rows(text):
    """The left-hand run links, in page order."""
    return re.findall(r'<a\b[^>]*class="[^"]*\brow\b[^"]*"[^>]*>.*?</a>', pane(text, "left"), re.S)


def cjk(text):
    return re.findall(r"[　-〿㐀-鿿豈-﫿＀-￯]", text)


def no_cjk(text):
    return cjk(re.sub(r">中<", "><", text)) == []


def strip_cells(text):
    """{stage: (css classes of the cell, whole cell html)} from the five-cell stage strip in the middle column."""
    out = {}
    for m in re.finditer(r'<li\b[^>]*class="([^"]*)"[^>]*data-step="([a-z]+)"[^>]*>(.*?)</li>', pane(text, "middle"), re.S):
        out[m.group(2)] = (m.group(1).split(), m.group(0))
    return out


def epoch(y, mo, d, h, mi):
    return calendar.timegm((y, mo, d, h, mi, 0))


def four(w, ann, prefix="n-"):
    return {st: seed(w, prefix + st, st, ann) for st in ("running", "succeeded", "failed", "lost")}


def bulk(w, owner, n, status, prefix, reason="boom"):
    """n runs of one user in one go (newest first: run<prefix>000 is the newest)."""
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    con2 = store.connect_state(w.ip.state_db)
    now = int(time.time())
    with con, con2:
        for i in range(n):
            name = "%s%03d" % (prefix, i)
            final = status if status in ("succeeded", "failed") else None
            con.execute("INSERT INTO runs (id, session_id, run_name, final_status, started_at, ended_at, last_message_at, failure_reason)"
                        " VALUES (?,?,?,?,?,?,?,?)", ("i-" + name, "s", name, final, now - 10 * i - 10 ** 5, now - 10 * i - 10 ** 5 + 5, now,
                                                      reason if status == "failed" else None))
            con2.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)",
                         (name, "/f", "lab-a", "ag", now, owner.user_id))
    con.close()
    con2.close()


# ---- login and the shell ----------------------------------------------------------------------------------------------------------

def test_tch01a_no_cookie_goes_to_login(w):
    # TC-H01a, TC-S38 (no cookie)
    seed(w, "secret-run", owner=w.user("zed"))
    for path in ("/", "/settings"):
        r = w.web().get(path)
        assert r.status_code == 303 and r.headers["location"] == "/login" and "secret-run" not in r.text


def test_tch02_login_lands_on_root(w):
    # TC-H02a, TC-H02b, TC-H02c
    w.user("ann")
    r = w.web().post("/login", data={"name": "ann", "password": PASSWORD})
    assert r.status_code == 303 and r.headers["location"] == "/" and "請回到 AI" not in r.text
    rid = "a" * 32
    r = w.web().post("/login", data={"name": "ann", "password": PASSWORD, "next": "/c/" + rid})
    assert r.headers["location"] == "/c/" + rid
    for evil in ("//evil", "https://evil.example/", "/c/zz"):
        r = w.web().post("/login", data={"name": "ann", "password": PASSWORD, "next": evil})
        assert r.status_code == 303 and r.headers["location"] == "/", evil


def test_tch20a_newest_first(w):
    # TC-H20a
    ann = w.user("ann")
    now = time.time()
    seed(w, "old-one", owner=ann, started=now - 5000)
    seed(w, "new-one", owner=ann, started=now - 100)
    seed(w, "mid-one", owner=ann, started=now - 2000)
    left = pane(login(w, "ann").get("/").text, "left")
    assert left.index("new-one") < left.index("mid-one") < left.index("old-one")


def test_tcs10_mast(w):
    # TC-S10
    w.user("ann")
    t = login(w, "ann").get("/").text
    top = t[:t.index('data-pane="left"')]
    assert 'class="mast"' in top and top.index("agentic-bioflow") < top.index("SU —") < top.index(">中<") < top.index(">EN<") < top.index("ann")
    assert "登出" not in top and "<form" not in top
    assert re.search(r"\.mast\{[^}]*height:\s*40px", style_of(t))


def test_tcs03_s04_cost_readout(w):
    # TC-S03, TC-S04 (replace TC-H09a, TC-H09b, TC-L17), TC-H09c, TC-L18
    from abf_platform import web_board
    ann = w.user("ann")
    seed(w, "x", "running", ann, counts=dict(succeeded=500, running=40))
    c = login(w, "ann")
    for url, want in (("/", ["SU —", "雲端 US$ —"]), ("/?lang=en", ["SU —", "Cloud US$ —"])):      # cost-page: US dollars, never NT$
        t = c.get(url).text
        top = t[:t.index('data-pane="left"')]
        lines = re.findall(r'<(\w+)\b[^>]*class="[^"]*\bcost\b[^"]*"[^>]*>(.*?)</\1>', top, re.S)
        assert [plain(x[1]) for x in lines] == want, url
        assert all("<" not in x[1] for x in lines)
        assert "<progress" not in top
        links = [h for h in re.findall(r"<a\b.*?</a>", top, re.S) if "SU" in h or "US$" in h]      # cost-page: the two lines are one link to the cost page
        assert len(links) == 1 and links[0].count('class="cost"') == 2 and 'href="/usage%s"' % ("?lang=en" if "lang=en" in url else "") in links[0]
        assert "NT$" not in t
        assert "SU —" not in pane(t, "right") and "NT$" not in pane(t, "right") and "NT$" not in pane(t, "left")
    t = c.get("/").text
    assert "本月費用" not in t and "NCHC" not in t and "NCHC" not in Path(web_board.__file__).read_text(encoding="utf-8")
    assert not re.search(r"\d", plain(re.search(r"<header.*?</header>", t, re.S).group(0)).replace("SU", ""))


def test_tcs11_s12_s13_layout_css(w):
    # TC-S11, TC-S12, TC-S13
    w.user("ann")
    css = style_of(login(w, "ann").get("/").text).replace(" ", "")
    assert "grid-template-columns:272pxminmax(0,1fr)320px" in css
    assert re.search(r"@media\(max-width:1200px\)\{[^@]*grid-template-columns:232pxminmax\(0,1fr\)288px", css)
    m = re.search(r"@media\(max-width:900px\)\{(.*?)\}\}", css + "}}", re.S).group(1)
    assert re.search(r"\.wb\{[^}]*grid-template-columns:1fr", m)
    assert re.search(r"\.main\{[^}]*order:-2", m) and re.search(r"\.rail\{[^}]*order:-1", m)
    assert re.search(r"\.costs[^{]*\{[^}]*display:none", m)


def test_tcs14_s15_s16_tokens(w):
    # TC-S14, TC-S15, TC-S16
    w.user("ann")
    css = style_of(login(w, "ann").get("/").text)
    light = ["#f6f5f2", "#ffffff", "#ecebe6", "#1f2328", "#575e66", "#d6d3cc", "#8f8b82", "#1c5d8a", "#e2edf5",
             "#0b5aa8", "#e3edf9", "#1b6837", "#e2f0e6", "#b0261d", "#fae6e3", "#865700", "#f7edd6"]
    dark = ["#15171a", "#1e2125", "#101214", "#e9e7e2", "#a2a8b0", "#33373d", "#646a73", "#7db8e2", "#1a2c3a", "#9cccf0",
            "#80b6f2", "#15263a", "#78c792", "#14291c", "#f28b81", "#3a1916", "#e2b35e", "#33270e"]
    dark_block = css[css.index("prefers-color-scheme"):]
    root = css[:css.index("prefers-color-scheme")]
    for v in light:
        assert v in root, v
    for v in dark:
        assert v in dark_block, v
    for v in re.findall(r"#[0-9a-fA-F]{3,8}\b", css):
        assert v.lower() in light + dark, v
    assert not re.search(r"\b(rgba?|hsla?)\(", css)
    families = set(re.findall(r"font-family:([^;}]+)", css))
    assert len(families) == 2
    for fam in families:
        assert fam.startswith("ui-monospace") or ("Noto Sans TC" in fam and "Microsoft JhengHei" in fam), fam
    assert set(re.findall(r"font-size:([^;}]+)", css)) <= {"12px", "13px", "15px", "16px", "22px", "inherit"}
    assert set(re.findall(r"border-radius:([^;}]+)", css)) <= {"0", "4px", "6px", "999px"}
    for prop, val in re.findall(r"(?<![-\w])((?:padding|margin|gap|row-gap|column-gap)(?:-(?:top|right|bottom|left))?):([^;}]+)", css):
        for px in re.findall(r"(-?\d+(?:\.\d+)?)px", val):
            assert px in ("0", "4", "8", "12", "16", "24"), (prop, val)


def test_tcs17_one_stylesheet_nothing_external(w):
    # TC-S17
    ann = w.user("ann")
    seed(w, "x", "running", ann)
    c = login(w, "ann")
    for t in (c.get("/").text, c.get("/settings").text, w.web().get("/login").text):
        assert len(re.findall(r"<style\b", t)) == 1 and not re.search(r"<link\b", t, re.I)
        css = style_of(t)
        assert "@import" not in css and "@font-face" not in css and "url(" not in css


def test_tcs31_no_other_platform_names(w):
    # TC-S31 (ADR 0004): neither the pages nor the style sheet name the platforms we replace; spelled by concatenation so the words stay out of the sources
    names = ("Seq" + "era", "Gal" + "axy", "Tow" + "er")
    ann = w.user("ann")
    rid = seed(w, "x", "running", ann)
    seed(w, "bad", "failed", ann, reason="Out of memory")
    c = login(w, "ann")
    for url in ("/", "/?lang=en", "/?run=" + rid, "/settings", "/settings?lang=en"):
        t = c.get(url).text
        assert style_of(t), url  # the style sheet is inline: this covers it too
        for n in names:
            assert n.lower() not in t.lower(), (url, n)


def test_tcs18_focus_outline(w):
    # TC-S18
    w.user("ann")
    css = style_of(login(w, "ann").get("/").text)
    for sel in ("a", "summary"):
        m = re.search(r"%s:focus-visible\{[^}]*outline:\s*(\d+)px solid var\(--focus\)" % sel, css)
        assert m and int(m.group(1)) >= 2, sel
    assert "--focus:#1c5d8a" in css and "--focus:#9cccf0" in css


# ---- the left column --------------------------------------------------------------------------------------------------------------

def test_tcs19_s20_left_column(w):
    # TC-S19, TC-S20 (web v2: "＋ 新分析" on top, lost is shown as Failed, succeeded as 完成)
    ann = w.user("ann")
    long = "L" * 60
    seed(w, long, "succeeded", ann)
    seed(w, "go", "running", ann)
    seed(w, "bad", "failed", ann)
    seed(w, "gone", "lost", ann)
    t = login(w, "ann").get("/").text
    left = pane(t, "left")
    first = re.search(r"<a\b[^>]*>.*?</a>", left, re.S).group(0)
    assert 'href="/launch"' in first and plain(first) == "＋ 新分析"
    assert left.index("＋ 新分析") < left.index("我的 run") < left.index("go") < left.index("設定") < left.index("登出")
    got = {}
    for r in rows(t):
        name = re.search(r"\b(go|bad|gone|L{60})\b", plain(r)).group(1)
        got[name[:4]] = r
    want = {"go": ("▶", "執行中", "running"), "bad": ("✗", "失敗", "failed"), "gone": ("✗", "失敗", "failed"), "LLLL": ("✓", "完成", "succeeded")}  # R10: status text, not stage
    for key, (sym, stage, st) in want.items():
        r = got[key]
        assert 'href="/?run=id-' in r and sym in r and stage in plain(r) and re.search(r'class="[^"]*\bstate-%s\b' % st, r), key
        assert re.search(r'<span\b[^>]*class="[^"]*\bnm\b[^"]*"[^>]*>', r)
    assert re.search(r"\.nm\{[^}]*text-overflow:\s*ellipsis", style_of(t))


def test_tcs21_s22_left_grey_and_settings(w):
    # TC-S21, TC-S22, TC-N11, TC-N18
    ann = w.user("ann")
    seed(w, "r", "running", ann)
    t = login(w, "ann").get("/").text
    left = pane(t, "left")
    anchors = re.findall(r"<a\b.*?</a>", left, re.S)
    for word in ("＋ 新專案", "搜尋專案或分析", "↑ 上傳資料", "資料瀏覽", "儀表板"):
        assert re.search(r'<span class="off">%s <span class="later">之後開放</span></span>' % re.escape(word), left), word
        assert not [a for a in anchors if word in a], word
    assert re.search(r'<a\b[^>]*href="/settings"[^>]*>\s*設定\s*</a>', left)
    forms = re.findall(r"<form\b[^>]*>", left)          # the left column has the log-out form only (the run page's buttons are in the middle)
    assert len(forms) == 1 and 'action="/logout"' in forms[0] and len(re.findall(r"<input\b", left)) == 1
    for banned in ("Launchpad", "Runs", "Datasets", "Studios"):
        assert banned not in t


def test_tcs23_selected_mark(w):
    # TC-S23 (web v2: there is no Now entry; the page always has a selected run, so exactly one left row is marked)
    ann = w.user("ann")
    rid = seed(w, "r", "running", ann)
    seed(w, "other", "succeeded", ann, started=time.time() - 9000)
    c = login(w, "ann")
    here = lambda html_: re.findall(r'<a\b[^>]*class="[^"]*\bhere\b[^"]*"[^>]*>(.*?)</a>', html_, re.S)
    for url in ("/", "/?run=" + rid):
        t = c.get(url).text
        assert len(here(pane(t, "left"))) == 1 and "r" in plain(here(pane(t, "left"))[0]) and "設定" not in plain(here(pane(t, "left"))[0]), url
        assert here(pane(t, "right")) == []
    t = c.get("/settings").text
    assert [plain(x) for x in here(pane(t, "left"))] == ["設定"]


# ---- the right column -------------------------------------------------------------------------------------------------------------

def test_tcs24_s25_right_head(w):
    # TC-S24, TC-S25, TC-N16 (web v2: the right column is "this analysis" only: a head, its notices, one grey line)
    ann = w.user("ann")
    seed(w, "r", "running", ann)
    right = pane(login(w, "ann").get("/").text, "right")
    assert "這個分析的對話 r 目前沒有待處理的事 問這個分析 之後開放" in plain(right)
    assert re.search(r'<span class="off">問這個分析 <span class="later">之後開放</span></span>', right)
    assert not re.search(r"<(a|button|input|form)\b", right)
    for gone in ("分析進度", "聊天", "全部分析", "只顯示你的", "搜尋"):
        assert gone not in right, gone


def test_tcs26_counts_row(w):
    # TC-S26 (web v2: the counts row ▶ / ! / ✓ is gone from the right column)
    ann = w.user("ann")
    for i in range(3):
        seed(w, "r%d" % i, "running", ann)
    seed(w, "f", "failed", ann)
    for i in range(4):
        seed(w, "s%d" % i, "succeeded", ann)
    t = login(w, "ann").get("/").text
    assert "tally" not in t and not re.search(r"[▶!✓]\s*\d", plain(pane(t, "right")))


def test_tch22_l19_l20_groups(w):
    # TC-H22b, TC-L19, TC-L20 (web v2: the groups are the projects of the left column; the right column has no groups)
    ann = w.user("ann")
    for i in range(2):
        seed(w, "r%d" % i, "running", ann)
    seed(w, "l1", "lost", ann)
    seed(w, "f1", "failed", ann)
    for i in range(3):
        seed(w, "s%d" % i, "succeeded", ann)
    t = login(w, "ann").get("/").text
    right = pane(t, "right")
    assert "<details" not in right and "data-stage=" not in right and "全部分析" not in right
    assert re.findall(r"<h3>(.*?)</h3>", pane(t, "left")) == ["未分專案"] and len(rows(t)) == 7


def test_tcs01_ten_runs_at_once(w):
    # TC-S01
    ann = w.user("ann")
    names = []
    for st, n in (("running", 4), ("failed", 2), ("lost", 1), ("succeeded", 3)):
        for i in range(n):
            names.append("job-%s-%d" % (st, i))
            seed(w, names[-1], st, ann)
    t = login(w, "ann").get("/").text
    for n in names:
        assert n in pane(t, "left"), n
    assert "還有" not in t and len(rows(t)) == 10
    assert plain(pane(t, "right")).count("job-") == 1          # web v2: the right column is about the selected run only


def test_tcl21_item_is_one_link(w):
    # TC-L21, TC-H08a to TC-H08e (web v2: each left row is one link; lost looks like failed)
    ann = w.user("ann")
    for name, st in (("a", "running"), ("b", "succeeded"), ("c", "failed"), ("d", "lost")):
        seed(w, name, st, ann)
    t = login(w, "ann").get("/").text
    its = rows(t)
    assert len(its) == 4
    for label, symbol, st, names in (("執行中", "▶", "running", "a"), ("完成", "✓", "succeeded", "b"), ("失敗", "✗", "failed", "cd")):
        hit = [x for x in its if re.search(r'class="[^"]*\bstate-%s\b' % st, x)]
        assert len(hit) == len(names) and all(symbol in x and label in plain(x) and 'href="/?run=id-' in x for x in hit), st
    assert "state-lost" not in t


def test_tcl22_l23_numbers_and_done(w):
    # TC-L22, TC-L23 (web v2: no numbers; newest first, and line 2 of a running row is done / total)
    ann = w.user("ann")
    now = time.time()
    seed(w, "first", "running", ann, started=now - 3000, counts=dict(succeeded=6, cached=2, running=2))
    seed(w, "second", "lost", ann, started=now - 2000)
    seed(w, "third", "running", ann, started=now - 1000)
    t = login(w, "ann").get("/").text
    its = [plain(x) for x in rows(t)]
    assert [x.split()[1] for x in its] == ["third", "second", "first"]
    assert its[2].endswith("執行 · 8 / 10")


def test_tcs27_s28_item_lines(w):
    # TC-S27, TC-S28 (web v2: line 2 is `stage · detail`)
    ann = w.user("ann")
    seed(w, "a-run", "running", ann, counts=dict(succeeded=6, cached=2, running=2))
    seed(w, "b-fail", "failed", ann, counts=dict(succeeded=1, failed=9), reason="exit 137\nlater")
    seed(w, "c-lost", "lost", ann, counts=dict(succeeded=4, pending=6))
    seed(w, "d-ok", "succeeded", ann, counts=dict(succeeded=10))
    seed(w, "e-zero", "running", ann)
    t = login(w, "ann").get("/").text
    got = {re.search(r"[a-e]-\w+", plain(x)).group(0): x for x in rows(t)}
    for key, text in (("a-run", "a-run 執行中 執行 · 8 / 10"), ("b-fail", "b-fail 失敗 執行 · —"), ("c-lost", "c-lost 失敗 執行 · 站台沒有回應"),
                      ("d-ok", "d-ok 完成 結果"), ("e-zero", "e-zero 執行中 執行 · 0 / 0")):
        p = plain(got[key])
        assert text in p, (key, p)
    assert "<progress" not in pane(t, "left") and not re.search(r"\sstyle=", t)


def test_tcl25_l26_failed_key_fact(w):
    # TC-L25, TC-L26, TC-S34 (web v2: the key fact is the Reason of the notice on the right: the last three lines, each cut at REASON_CAP)
    ann = w.user("ann")
    ids = {"long": seed(w, "long", "failed", ann, reason="A" * 80 + "B" * 40 + "\nSECONDLINE"),
           "short": seed(w, "short", "failed", ann, reason="short reason\nmore"),
           "none": seed(w, "none", "failed", ann, reason=None),
           "empty": seed(w, "empty", "failed", ann, reason="")}
    c = login(w, "ann")
    cause = lambda key: plain(re.search(r"<dt>原因</dt>\s*<dd>(.*?)</dd>", pane(c.get("/?run=" + ids[key]).text, "right"), re.S).group(1))
    assert cause("long") == "A" * 80 + "… SECONDLINE" and "B" not in cause("long")
    assert cause("short") == "short reason more"
    assert cause("none") == "—" and cause("empty") == "—"


def test_tcl28_selected_item(w):
    # TC-L28 (web v2: the selected left row is marked `here`; with no ?run= it is the default run)
    from abf_platform import web_board
    ann = w.user("ann")
    now = time.time()
    ids = [seed(w, n, "running", ann, started=now - k) for k, n in ((300, "one"), (200, "two"), (100, "three"))]
    c = login(w, "ann")
    t = c.get("/?run=" + ids[1]).text
    marked = [x for x in rows(t) if re.search(r'class="[^"]*\bhere\b', x)]
    assert len(marked) == 1 and "two" in marked[0]
    marked = [x for x in rows(c.get("/").text) if re.search(r'class="[^"]*\bhere\b', x)]
    assert len(marked) == 1 and "three" in marked[0]
    assert re.search(r"a\.row\.here\{[^}]*background", web_board.STYLE)


def test_tcl29_failed_items_ask_get_run_at_most_100_times(w, monkeypatch):
    # TC-L29 (web v2: the page asks get_run once, for the selected run; the left rows come from list_runs; both with the caller)
    from abf_platform import actions
    ann = w.user("ann")
    bulk(w, ann, 250, "failed", "bad")
    real, calls, lists = actions.get_run, [], []

    def spy(index, run_id, **kw):
        calls.append((run_id, kw))
        return real(index, run_id, **kw)
    real_list = actions.list_runs
    monkeypatch.setattr(actions, "get_run", spy)
    monkeypatch.setattr(actions, "list_runs", lambda *a, **kw: lists.append(kw) or real_list(*a, **kw))
    t = login(w, "ann").get("/").text
    assert len(rows(t)) == 100 and "還有 150 筆" in pane(t, "left")
    assert len({r for r, _ in calls}) == 1 and len(calls) == 1
    assert all(k.get("caller") is not None and k["caller"].user_id == ann.user_id for _, k in calls)
    assert lists and all(k.get("caller") is not None for k in lists)
    assert "boom" in pane(t, "right")


def test_tcl30_numbers_count_all_runs(w):
    # TC-L30, TC-H19b (web v2: no numbers; the left column shows the first 100 and says how many more, the right column only the selected run)
    ann = w.user("ann")
    bulk(w, ann, 250, "succeeded", "ok")
    t = login(w, "ann").get("/").text
    its = rows(t)
    assert len(its) == 100 and "還有 150 筆" in pane(t, "left") and "ok000" in plain(its[0]) and "ok099" in plain(its[99])
    assert plain(pane(t, "right")).count("ok0") == 1


def test_tch19a_left_cap(w):
    # TC-H19a
    ann = w.user("ann")
    bulk(w, ann, 250, "succeeded", "run")
    left = pane(login(w, "ann").get("/").text, "left")
    assert len(re.findall(r">run\d{3}<", left)) == 100 and "還有 150 筆" in left


# ---- stage strip and the middle column --------------------------------------------------------------------------------------------

def test_tch06_stage_of_table():
    # TC-H06a
    from abf_platform import web_board
    assert [web_board.stage_of(s) for s in ("running", "lost", "failed", "succeeded")] == ["running", "running", "running", "results"]


def test_tch06_default_stage(w):
    # TC-H06b, TC-H06c
    ann = w.user("ann")
    s = seed(w, "ok", "succeeded", ann)
    f = seed(w, "bad", "failed", ann)
    c = login(w, "ann")
    assert 'data-current="results"' in c.get("/?run=" + s).text
    assert 'data-current="running"' in c.get("/?run=" + f).text


def test_tch21_stage_bodies(w):
    # TC-H21c, TC-H21d, TC-H21e, TC-H21f, TC-H21g, TC-S46
    ann = w.user("ann")
    a = seed(w, "run-a", "failed", ann, started=epoch(2026, 10, 17, 20, 30), ended=epoch(2026, 10, 18, 1, 12),
             counts=dict(succeeded=11, cached=12, failed=13, aborted=14, running=15, pending=16, submitted=17),
             reason="Process terminated with an error exit status (137)")
    b = seed(w, "run-b", "succeeded", ann, started=epoch(2026, 10, 18, 1, 5), ended=epoch(2026, 10, 18, 1, 6))
    c = login(w, "ann")
    for lang in ("", "&lang=en"):
        mid = plain(pane(c.get("/?run=" + a + lang).text, "middle"))
        assert "10-18 04:30" in mid and "10-18 09:12" in mid, lang
    mid = plain(pane(c.get("/?run=" + a).text, "middle"))
    for label, n in (("成功", 11), ("快取", 12), ("失敗", 13), ("中止", 14), ("執行中", 15), ("等待", 16), ("已送出", 17)):
        assert re.search(r"%s\s*%d(?!\d)" % (label, n), mid), (label, n)
    assert "10-18 09:05" in plain(pane(c.get("/?run=" + b + "&tab=info").text, "middle"))
    assert "Process terminated with an error exit status (137)" in c.get("/?run=" + a).text
    for stage, feature in (("launch", "012b"), ("downstream", "016"), ("finished", "這個 run 還沒到這個階段。")):      # finished-stage: a run that has not succeeded has not reached it
        body = pane(c.get("/?run=%s&stage=%s" % (a, stage)).text, "middle")
        assert "—" in body and feature in body, stage


def test_tcs47_no_raw_iso_time(w):
    # TC-S47
    ann = w.user("ann")
    rid = seed(w, "r", "succeeded", ann, started=1_700_000_000)
    c = login(w, "ann")
    for url in ("/", "/?run=" + rid, "/settings", "/?run=nope"):
        t = c.get(url).text
        assert not re.search(r"\d{4}-\d\d-\d\dT\d\d", t) and not re.search(r"\d\d:\d\d:\d\dZ|\+00:00", t), url


def test_tcl07_to_l13_stage_strip(w):
    # TC-L07, TC-L08, TC-L09, TC-L10, TC-L11, TC-L12, TC-L13
    ann = w.user("ann")
    ids = {st: seed(w, "n-" + st, st, ann) for st in ("running", "succeeded", "failed", "lost")}
    c = login(w, "ann")
    expect = {"running": ["is-done", "is-current", "is-later", "is-later", "is-later"],
              "failed": ["is-done", "is-current is-failed", "is-later", "is-later", "is-later"],
              "lost": ["is-done", "is-current is-failed", "is-later", "is-later", "is-later"],
              "succeeded": ["is-done", "is-done", "is-current", "is-later", "is-later"]}
    for st, want in expect.items():
        cells = strip_cells(c.get("/?run=" + ids[st]).text)
        assert list(cells) == list(STAGES), st
        got = [[k for k in cells[s][0] if k.startswith("is-")] for s in STAGES]
        assert got == [x.split() for x in want], (st, got)
    names = [plain(strip_cells(c.get("/?run=" + ids["running"]).text)[s][1]) for s in STAGES]
    assert [n.replace("✓ ", "") for n in names] == ["送出", "執行中", "結果", "下游", "完成"]
    cells = strip_cells(c.get("/?run=%s&stage=results" % ids["running"]).text)
    assert [[k for k in cells[s][0] if k.startswith("is-")] for s in STAGES] == [[x] for x in expect["running"]]
    assert [s for s in STAGES if 'aria-current="step"' in cells[s][1]] == ["results"]
    for st, own in (("succeeded", "results"), ("failed", "running")):
        cells = strip_cells(c.get("/?run=" + ids[st]).text)
        assert [s for s in STAGES if 'aria-current="step"' in cells[s][1]] == [own]


def test_tcs29_stage_strip_style(w):
    # TC-S29
    ann = w.user("ann")
    rid = seed(w, "r", "succeeded", ann)
    t = login(w, "ann").get("/?run=" + rid).text
    css = style_of(t).replace(" ", "")
    assert re.search(r"\.is-done[^{]*\{[^}]*border-top:3pxsolidvar\(--succeeded\)", css)
    assert re.search(r"\.is-current[^{]*\{[^}]*border-top:3pxsolidvar\(--accent\)", css)
    assert re.search(r"\.is-later[^{]*\{[^}]*border-top:3pxdashed", css)
    cells = strip_cells(t)
    assert all("✓" in plain(cells[s][1]) for s in ("launch", "running")) and "✓" not in plain(cells["results"][1])


def test_tcl14_l15_l16_middle(w):
    # TC-L14, TC-L15, TC-L16
    ann = w.user("ann")
    f = seed(w, "bad-one", "failed", ann, counts=dict(succeeded=11, cached=12, failed=13, aborted=14, running=15, pending=16, submitted=17))
    c = login(w, "ann")
    mid = pane(c.get("/?run=" + f).text, "middle")
    head = re.search(r'<[^>]*class="[^"]*\bstate-failed\b[^"]*"[^>]*>[^<]*</', mid)
    assert head and "✗" in head.group(0) and "失敗" in head.group(0) and mid.index("bad-one") < mid.index(head.group(0))
    # 011b: the page also has the notice's field list (問題／原因／可選動作); the task legend is the dl of class counts
    cells = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", re.search(r'<dl class="counts">(.*?)</dl>', mid, re.S).group(1), re.S)
    assert cells == [("成功", "11"), ("快取", "12"), ("失敗", "13"), ("中止", "14"), ("執行中", "15"), ("等待", "16"), ("已送出", "17")]
    run = pane(c.get("/?run=%s&stage=running" % f).text, "middle")
    prev = re.search(r'<a\b[^>]*rel="prev"[^>]*>(.*?)</a>', run, re.S)
    nxt = re.search(r'<a\b[^>]*rel="next"[^>]*>(.*?)</a>', run, re.S)
    assert "←" in prev.group(1) and "→" in nxt.group(1)
    assert "stage=launch" in prev.group(0) and "run=" + f in prev.group(0)
    assert "stage=results" in nxt.group(0) and "run=" + f in nxt.group(0)


def test_tch08_progress(w):
    # TC-H08f, TC-H08g
    ann = w.user("ann")
    a = seed(w, "p1", "running", ann, counts=dict(succeeded=6, cached=2, running=2))
    z = seed(w, "p0", "running", ann)
    c = login(w, "ann")
    tag = re.search(r"<progress[^>]*>", pane(c.get("/?run=" + a).text, "middle")).group(0)
    assert 'value="8"' in tag and 'max="10"' in tag
    assert "value" not in re.search(r"<progress[^>]*>", pane(c.get("/?run=" + z).text, "middle")).group(0)


def test_tch10_stage_param(w):
    # TC-H10a, TC-H10b, TC-H10c, TC-H10d, TC-H10e, TC-S02
    ann = w.user("ann")
    rid = seed(w, "ok", "succeeded", ann)
    c = login(w, "ann")
    for s in STAGES:
        r = c.get("/?run=%s&stage=%s" % (rid, s))
        assert r.status_code == 200 and 'data-current="%s"' % s in r.text
    for bad in ("evil", "", "<script>", "RUNNING"):
        r = c.get("/", params={"run": rid, "stage": bad})
        assert r.status_code == 200 and 'data-current="results"' in r.text and "<script>" not in r.text, bad
    run = c.get("/?run=%s&stage=running" % rid).text
    assert "stage=launch" in re.search(r'<a[^>]*rel="prev"[^>]*>', run).group(0)
    assert "stage=results" in re.search(r'<a[^>]*rel="next"[^>]*>', run).group(0)
    first = c.get("/?run=%s&stage=launch" % rid).text
    assert 'rel="prev"' not in first and 'rel="next"' in first
    last = c.get("/?run=%s&stage=finished" % rid).text
    assert 'rel="next"' not in last and 'rel="prev"' in last
    r = c.get("/?stage=running")          # web v2: `/` opens the default run, and the stage applies to it
    assert r.status_code == 200 and 'data-current="running"' in r.text and 'data-card=' not in r.text


def test_tch08_states_and_symbols(w):
    # TC-S30, TC-H08a to TC-H08e, TC-L14 (web v2: three states; lost is shown, and styled, as failed)
    ann = w.user("ann")
    ids = four(w, ann)
    c = login(w, "ann")
    t = c.get("/").text
    css = {"running": "running", "succeeded": "succeeded", "failed": "failed", "lost": "failed"}
    labels = {"running": "執行中", "succeeded": "完成", "failed": "失敗", "lost": "失敗"}
    for st, sym in (("running", "▶"), ("succeeded", "✓"), ("failed", "✗"), ("lost", "✗")):
        mine = [r for r in rows(t) if "n-" + st in plain(r)]
        assert len(mine) == 1 and plain(mine[0]).startswith(sym) and labels[st] in plain(mine[0]) and "state-" + css[st] in mine[0]
        mid = pane(c.get("/?run=" + ids[st]).text, "middle")
        assert re.search(r'class="badge state-%s"[^>]*>\s*%s\s' % (css[st], sym), mid)
    for st in ("failed", "lost"):          # 011b/web v2: the formal notice is on the right: the level pill is a square plus 待處理
        right = pane(c.get("/?run=" + ids[st]).text, "right")
        assert 'class="sq"' in right and "待處理" in plain(right) and "state-failed" in right


# ---- the Now page -----------------------------------------------------------------------------------------------------------------

def test_tcs32_s33_s34_now_page(w):
    # TC-S32, TC-S33, TC-S34, TC-S35 (web v2: there is no Now page; `/` opens the newest failed or lost run and its notice is on the right)
    ann = w.user("ann")
    for i in range(2):
        seed(w, "run%d" % i, "running", ann)
    bad1 = seed(w, "bad1", "failed", ann, reason="Out of memory\nsecond")
    bad2 = seed(w, "bad2", "failed", ann)
    gone = seed(w, "gone1", "lost", ann)
    for i in range(3):
        seed(w, "fine%d" % i, "succeeded", ann)
    c = login(w, "ann")
    t = c.get("/").text
    mid = pane(t, "middle")
    assert "<h1>gone1</h1>" in mid and "現在" not in t and "正在跑" not in t and "需要注意" not in t and "data-card=" not in t
    cause = lambda rid: plain(re.search(r"<dt>原因</dt>\s*<dd>(.*?)</dd>", pane(c.get("/?run=" + rid).text, "right"), re.S).group(1))
    assert cause(bad1) == "Out of memory second" and cause(bad2) == "—" and cause(gone) == "站台沒有回應"
    assert len(re.findall(r"<article", pane(t, "right"))) == 1
    assert len(rows(t)) == 8


def test_tcs35_nothing_to_notify(w):
    # TC-S35 (web v2: a run that did not fail has no notice, and the right column says so)
    ann = w.user("ann")
    seed(w, "fine", "succeeded", ann)
    t = login(w, "ann").get("/").text
    right = pane(t, "right")
    assert "<article" not in right and "目前沒有待處理的事" in right


def test_tcs36_cards_are_read_only(w):
    # TC-S36 (web v2: the middle and right columns of the opened run only ask: their forms are POST /act/..., their links stay on the board)
    ann = w.user("ann")
    seed(w, "bad", "failed", ann, reason="boom")
    seed(w, "go", "running", ann)
    t = login(w, "ann").get("/").text
    for part in (pane(t, "middle"), pane(t, "right")):
        forms = re.findall(r"<form\b[^>]*>", part)          # 012b: the buttons are forms that only ask (POST /act/...)
        assert all(re.fullmatch(r'<form class="act" method="post" action="/act/(resume|relaunch|cancel)">', f) for f in forms)
        assert part.count("<button") == len(forms)
        for h in hrefs(part):
            u = urlsplit(htmllib.unescape(h))
            assert (u.path == "/" and "run" in parse_qs(u.query)) or (u.path == "/launch" and "from" in parse_qs(u.query)), h      # the run page's "launch again" link
        for word in ("上傳", "確認", "Resume", "Retry"):
            assert word not in re.sub(r"（確認頁）", "", part)
    assert len(re.findall(r"<form\b", pane(t, "right"))) == 1


def test_tcs37_attention_cap(w):
    # TC-S37 (web v2: 250 failed runs: the left column is capped, the right column has the one notice of the opened run)
    ann = w.user("ann")
    bulk(w, ann, 250, "failed", "bad")
    t = login(w, "ann").get("/").text
    assert len(rows(t)) == 100 and "還有 150 筆" in pane(t, "left") and len(re.findall(r"<article", pane(t, "right"))) == 1


# ---- empty and broken index -------------------------------------------------------------------------------------------------------

def test_tch18_empty_states(w):
    # TC-H18a, TC-H18b, TC-H18c
    w.user("ann")
    c = login(w, "ann")
    r = c.get("/")
    assert r.status_code == 200 and "還沒有" in pane(r.text, "left") and "還沒有分析" in pane(r.text, "middle") and "—" in pane(r.text, "right")
    Path(w.ip.index).write_bytes(b"")
    r = c.get("/")
    assert r.status_code == 200 and "還沒有" in r.text
    Path(w.ip.index).unlink()
    from abf_platform import store
    store.init_index(w.ip.index)
    assert "還沒有" in c.get("/").text
    assert c.get("/settings").status_code == 200


# ---- who sees what ----------------------------------------------------------------------------------------------------------------

def test_tch03_only_own_runs(w):
    # TC-H03a, TC-H03b
    ann, bob = w.user("ann"), w.user("bob")
    seed(w, "ann-run", "running", ann)
    for i in range(5):
        seed(w, "bob-secret-%d" % i, "failed", bob)
    c = login(w, "ann")
    for url in ("/", "/settings"):
        assert "bob-secret" not in c.get(url).text
    t = c.get("/").text
    assert "ann-run" in pane(t, "left") and len(rows(t)) == 1 and "<h1>ann-run</h1>" in pane(t, "middle")


def test_tch04_hidden_submitter(w):
    # TC-H04a, TC-H04b, TC-H04c
    from abf_platform import actions
    w.user("ann")
    w.user("bob")
    seed(w, "orphan-nolaunch", "failed", launch_row=False)
    seed(w, "orphan-nulluser", "running", None)
    for who in ("ann", "bob"):
        assert "orphan-" not in login(w, who).get("/").text
    names = {r["name"] for r in actions.list_runs(w.ip.index, caller=None, platform_path=w.ip.state_db)["runs"]}
    assert {"orphan-nolaunch", "orphan-nulluser"} <= names


def test_tch05_not_mine_looks_missing(w):
    # TC-H05a, TC-H05b, TC-H05c, TC-H05d, TC-S49
    w.user("ann")
    bob = w.user("bob")
    seed(w, "bobs", "running", bob, run_id="bob-run-id")
    c = login(w, "ann")
    other = c.get("/?run=bob-run-id")
    missing = c.get("/?run=does-not-exist")
    assert other.status_code == 404 and missing.status_code == 404 and "bobs" not in other.text
    assert other.content == missing.content
    r = c.get("/", params={"run": "UNIQUE-needle-8841"})
    assert r.status_code == 404 and "UNIQUE-needle-8841" not in r.text
    assert "找不到這個 run" in r.text and 'href="/"' in r.text
    en = c.get("/", params={"run": "UNIQUE-needle-8841", "lang": "en"})
    assert 'href="/?lang=en"' in en.text and "UNIQUE-needle-8841" not in en.text
    assert style_of(r.text) == style_of(c.get("/").text)


def test_tch15_bearer_is_not_a_login(w):
    # TC-H15, TC-S38
    from abf_platform import store
    ann = w.user("ann")
    tok = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id)
    for path in ("/", "/settings"):
        r = w.web().get(path, headers={"Authorization": "Bearer %s" % tok})
        assert r.status_code == 303 and r.headers["location"] == "/login"


# ---- read-only --------------------------------------------------------------------------------------------------------------------

def test_tch11_read_only(w):
    # TC-H11a, TC-H11b, TC-H11c, TC-H11d
    ann = w.user("ann")
    rid = seed(w, "ok", "failed", ann, reason="boom")
    c = login(w, "ann")
    for url in ("/", "/?run=" + rid, "/settings"):
        t = c.get(url).text
        forms = re.findall(r"<form\b[^>]*>", t)
        assert 'action="/logout"' in forms[0]
        assert all(re.fullmatch(r'<form class="act" method="post" action="/act/(resume|relaunch|cancel)">', f) for f in forms[1:])     # 012b
        assert (len(forms) == 1) == (url == "/settings")          # the failed run is on the Now page and on its own page: both have the buttons that ask
        assert t.count("<button") == len(forms)
        assert re.search(r'name="csrf" value="[^"]+"', t)
    assert c.post("/").status_code == 405 and c.post("/settings").status_code == 405
    routes = sorted((r.path, tuple(sorted(r.methods))) for r in c.app.routes)
    assert routes == [("/", ("GET", "HEAD")), ("/.well-known/oauth-authorization-server", ("GET", "HEAD", "OPTIONS")),
                      ("/act/{verb}", ("POST",)),
                      ("/authorize", ("GET", "HEAD", "POST")), ("/c/{rid}", ("GET", "HEAD")), ("/c/{rid}", ("POST",)),
                      ("/consent/{rid}", ("GET", "HEAD")), ("/consent/{rid}", ("POST",)), ("/launch", ("GET", "HEAD")), ("/launch", ("POST",)),
                      ("/login", ("GET", "HEAD")),
                      ("/login", ("POST",)), ("/logout", ("POST",)), ("/register", ("OPTIONS", "POST")),
                      ("/revoke", ("OPTIONS", "POST")), ("/settings", ("GET", "HEAD")), ("/token", ("OPTIONS", "POST")),
                      ("/usage", ("GET", "HEAD"))], routes


def _digest(w):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(w.ip.state_db).parent.rglob("*")) if p.is_file()}


def test_tch11e_k1_a_get_writes_nothing(w):
    # TC-H11e, TC-K1
    ann = w.user("ann")
    rid = seed(w, "ok", "running", ann)
    c = login(w, "ann")
    before, counts = _digest(w), w.counts()
    for _ in range(2):
        for url in ("/", "/?run=" + rid, "/?stage=running", "/?lang=en", "/settings", "/settings?lang=en", "/?run=zzz"):
            c.get(url)
    assert _digest(w) == before and w.counts() == counts


def test_tch12_escaping(w):
    # TC-H12a, TC-H12b, TC-H12c
    ann = w.user("ann")
    nasty = '<script>alert(1)</script>"><b>'
    nid = seed(w, nasty, "running", ann, run_id='x"y\'z<q>')
    fid = seed(w, "f", "failed", ann, reason="<img src=x onerror=1>")
    c = login(w, "ann")
    for url in ("/", "/?lang=en", "/?run=" + nid):
        t = c.get(url).text
        assert "<script>" not in t and "<b>" not in t and "&lt;script&gt;" in t
        assert 'href="/?run=x"y' not in t
        for h in hrefs(t):
            assert "<" not in h and '"' not in h
    f = c.get("/?run=" + fid).text
    assert "<img" not in f and "&lt;img" in f


def test_tch12d_item_fact_is_escaped(w):
    # TC-H12d
    ann = w.user("ann")
    seed(w, "f", "failed", ann, reason="<img src=x onerror=1>\nrest")
    t = login(w, "ann").get("/").text
    assert "<img" not in t and "&lt;img src=x onerror=1&gt;" in pane(t, "right")


def test_tch13_csp_and_markup(w):
    # TC-H13a to TC-H13i, TC-S17
    ann = w.user("ann")
    rid = seed(w, "ok", "running", ann, counts=dict(succeeded=1, running=1))
    c = login(w, "ann")
    pages = [c.get("/"), c.get("/?lang=en"), c.get("/?run=" + rid), c.get("/settings"), c.get("/?run=nope"), w.web().get("/login"),
             c.get("/c/" + "b" * 32), consent_page(w, "ann")]
    for r in pages:
        csp = r.headers["content-security-policy"]
        assert "script-src" not in csp and "'unsafe-inline'" not in csp
        for keep in ("default-src 'none'", "form-action 'self'", "frame-ancestors 'none'", "base-uri 'none'"):
            assert keep in csp
        digest = base64.b64encode(hashlib.sha256(style_of(r.text).encode("utf-8")).digest()).decode()
        assert "style-src 'sha256-%s'" % digest in csp, r.url
    for r in pages:
        t = r.text
        assert "<script" not in t.lower() and not re.search(r"\sstyle=", t) and not re.search(r"\son[a-z]+=", t, re.I)
        assert "http://" not in t and "https://" not in t and not re.search(r"(src|href|action)=\"//", t)


def test_tch17_caller_always_passed():
    # TC-H17
    seen = 0
    for path in (WEB, BOARD):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                f = node.func
                name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if name in ("list_runs", "get_run"):
                    seen += 1
                    kw = {k.arg: k.value for k in node.keywords}
                    assert "caller" in kw, ast.dump(node)
                    assert not (isinstance(kw["caller"], ast.Constant) and kw["caller"].value is None), ast.dump(node)
    assert seen >= 2


def test_tch07_nothing_stored():
    # TC-H07a
    from abf_platform import store
    for schema in (store.SCHEMA, store.STATE_SCHEMA, store.TOKEN_SCHEMA):
        assert not re.search(r"\bstage\b", schema, re.I)
    assert not re.search(r"sqlite3|INSERT|UPDATE|\bopen\(|write_", BOARD.read_text(encoding="utf-8"))


def test_tch14_refresh_only_on_root(w):
    # TC-H14a, TC-H14b
    ann = w.user("ann")
    rid = seed(w, "r", "running", ann)
    c = login(w, "ann")
    for url in ("/", "/?run=" + rid):
        assert '<meta http-equiv="refresh" content="15">' in c.get(url).text
    for p in (w.web().get("/login").text, c.get("/c/" + "b" * 32).text, c.get("/?run=nope").text, c.get("/settings").text):
        assert "http-equiv" not in p


def test_tcs05_no_leaks(w, caplog):
    # TC-S05
    caplog.set_level(logging.DEBUG)
    w.user("ann")
    bob = w.user("bob")
    seed(w, "bobs", "running", bob, run_id="bob-run-id")
    c = login(w, "ann")
    cookie = c.cookies.get("abf_web")
    bodies = [c.get("/?run=bob-run-id").text]
    Path(w.ip.index).write_bytes(b"")
    bodies.append(c.get("/").text)
    Path(w.ip.index).unlink()
    bodies.append(c.get("/").text)
    bodies.append(w.login(w.web(), "ann", "wrong-secret-pw").text)
    fl = w.web()
    for _ in range(5):
        w.login(fl, "bob", "wrong-secret-pw")
    bodies.append(w.login(fl, "bob", PASSWORD).text)
    for t in bodies:
        for bad in ("Traceback", "sqlite", ".db", "web_signing", cookie, "wrong-secret-pw", PASSWORD):
            assert bad not in t, bad
    assert cookie not in caplog.text and "wrong-secret-pw" not in caplog.text and PASSWORD not in caplog.text


# ---- settings, login --------------------------------------------------------------------------------------------------------------

def test_tcs39_s40_s41_s42_settings(w):
    # TC-S39, TC-S40, TC-S41, TC-S42, TC-N14, TC-N12
    ann = w.user("ann")
    seed(w, "r", "running", ann)
    c = login(w, "ann")
    r = c.get("/settings")
    assert r.status_code == 200
    mid = pane(r.text, "middle")
    assert "<h1>設定</h1>" in mid
    assert re.findall(r"<h2>(.*?)</h2>", mid) == ["使用前檢查", "運算環境", "憑證", "密碼與金鑰", "個人", "營運者後台", "角色（老師／學生）"]      # settings-page: the checklist is the first section
    for word in ("AI 模型金鑰", "逐步模式", "開發模式"):
        assert word in mid
    assert mid.count("之後開放") >= 6 and not re.search(r"<(a|form|input|select|textarea|button)\b", mid)
    # TC-N14 / TC-K6 (R8): the second key is named nowhere; spelled by concatenation so the platform-wide safety test stays at 0
    second = "J" + "ev"
    for url in ("/settings", "/settings?lang=en"):
        assert second.lower() not in c.get(url).text.lower()
    assert 'data-pane="left"' in r.text and 'data-pane="right"' in r.text and "<header" in r.text
    for url in ("/settings", "/settings?lang=en"):
        assert not re.search(r"12 小時|12 h\b|12 hours", c.get(url).text, re.I)
    for banned in ("歡迎使用", "第一次使用", "建立第一個專案"):
        assert banned not in r.text and banned not in c.get("/").text


def test_tcs43_s44_login_page(w):
    # TC-S43, TC-S44, TC-N15
    w.user("ann")
    c = w.web()
    r = c.get("/login")
    t = r.text
    assert r.status_code == 200 and len(re.findall(r"<style\b", t)) == 1
    digest = base64.b64encode(hashlib.sha256(style_of(t).encode("utf-8")).digest()).decode()
    assert "style-src 'sha256-%s'" % digest in r.headers["content-security-policy"]
    assert re.findall(r"<input\b[^>]*name=\"(\w+)\"", t) == ["name", "password"]
    assert "checkbox" not in t and "記住" not in t and "Remember" not in t and len(re.findall(r"<button\b", t)) == 1
    bad = w.login(c, "ann", "wrong wrong")
    ghost = w.login(c, "nobody", "wrong wrong")
    assert bad.status_code == 401 and ghost.status_code == 401 and "姓名或密碼不對" in bad.text and "姓名或密碼不對" in ghost.text
    assert "<form" in bad.text and "set-cookie" not in bad.headers and "set-cookie" not in ghost.headers
    for _ in range(5):
        w.login(c, "ann", "wrong wrong")
    r = w.login(c, "ann", PASSWORD)
    assert r.status_code == 429 and "登入失敗太頻繁" in r.text and "set-cookie" not in r.headers


def test_tcs45_confirm_pages_share_the_style(w):
    # TC-S45, TC-N08
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c = login(w, "ann")
    r = c.get("/c/" + rid)
    digest = base64.b64encode(hashlib.sha256(style_of(r.text).encode("utf-8")).digest()).decode()
    assert "style-src 'sha256-%s'" % digest in r.headers["content-security-policy"] and style_of(r.text) == style_of(c.get("/").text)
    assert style_of(c.get("/c/%s?lang=en" % rid).text) == style_of(r.text)      # web-confirm-plain: the English page has its own labels; the stylesheet is the same
    k = consent_page(w, "ann")            # the OAuth consent page carries the same one stylesheet
    kd = base64.b64encode(hashlib.sha256(style_of(k.text).encode("utf-8")).digest()).decode()
    assert k.text.count("<style>") == 1 and style_of(k.text) == style_of(r.text)
    assert "style-src 'sha256-%s'" % kd in k.headers["content-security-policy"]
    assert not re.search(r"\sstyle=", k.text) and "<script" not in k.text.lower()
    assert w.web().get("/login?lang=en").text == w.web().get("/login").text


# ---- language and links -----------------------------------------------------------------------------------------------------------

def seed_three(w, ann):
    return {st: seed(w, "n-" + st, st, ann, counts=dict(succeeded=1, cached=2, failed=3, aborted=4, running=5, pending=6, submitted=7),
                     reason="boom" if st == "failed" else None) for st in ("running", "failed", "succeeded", "lost")}


def test_tcl31_default_is_chinese(w):
    # TC-L31
    ann = w.user("ann")
    ids = seed_three(w, ann)
    t = login(w, "ann").get("/?run=" + ids["running"]).text
    assert "主視窗" in t and "執行中" in t and "之後開放" in t and "登出" in t and 'lang="zh-Hant"' in t
    for word in ("Cached", "Aborted", "Pending", "Submitted"):
        assert word not in t


def test_tcl32_l33_english(w):
    # TC-L32, TC-L33
    ann = w.user("ann")
    ids = seed_three(w, ann)
    c = login(w, "ann")
    for url in ["/?lang=en", "/settings?lang=en"] + ["/?run=%s&lang=en" % i for i in ids.values()]:
        t = c.get(url).text
        assert no_cjk(t), (url, cjk(t))
        assert 'lang="en"' in t
    mid = pane(c.get("/?run=%s&lang=en" % ids["running"]).text, "middle")
    cells = [(a.lower(), b) for a, b in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", mid, re.S)]
    assert cells == [("succeeded", "1"), ("cached", "2"), ("failed", "3"), ("aborted", "4"), ("running", "5"), ("pending", "6"),
                     ("submitted", "7")]


def test_tcl34_english_reason_not_recorded(w):
    # TC-L34 (web v2: with no reason and no failed task the Reason and the Step are a dash)
    ann = w.user("ann")
    seed(w, "nr", "failed", ann, reason=None)
    t = login(w, "ann").get("/?lang=en").text
    right = pane(t, "right")
    assert re.search(r"<dt>Step</dt>\s*<dd>—</dd>\s*<dt>Reason</dt>\s*<dd>—</dd>", right) and no_cjk(right)


def test_tcl35_l36_l37_switch_and_links(w):
    # TC-L35, TC-L36, TC-L37
    ann = w.user("ann")
    rid = seed(w, "r", "running", ann)
    seed(w, "s", "succeeded", ann)
    seed(w, "bad", "failed", ann)
    c = login(w, "ann")
    t = c.get("/?run=%s&stage=results" % rid).text
    en = htmllib.unescape(re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>EN</a>', t).group(1))
    zh = htmllib.unescape(re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>中</a>', t).group(1))
    assert urlsplit(en).path == "/" and parse_qs(urlsplit(en).query) == {"run": [rid], "stage": ["results"], "lang": ["en"]}
    assert urlsplit(zh).path == "/" and parse_qs(urlsplit(zh).query) == {"run": [rid], "stage": ["results"]}
    st = c.get("/settings").text
    assert htmllib.unescape(re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>EN</a>', st).group(1)) == "/settings?lang=en"
    assert htmllib.unescape(re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>中</a>', st).group(1)) == "/settings"
    for url in ("/?run=%s&stage=running&lang=en" % rid, "/settings?lang=en"):
        t = c.get(url).text
        zh_link = htmllib.unescape(re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>中</a>', t).group(1))
        others = [htmllib.unescape(h) for h in hrefs(t)]
        others.remove(zh_link)
        assert len(others) >= 6 and all("lang=en" in h for h in others), [h for h in others if "lang=en" not in h]
    t = c.get("/?run=%s&stage=running" % rid).text
    en_link = htmllib.unescape(re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>EN</a>', t).group(1))
    rest = [htmllib.unescape(h) for h in hrefs(t)]
    rest.remove(en_link)
    assert len(rest) >= 6 and not [h for h in rest if "lang=" in h]


def test_tcl38_data_is_not_translated(w):
    # TC-L38
    ann = w.user("ann")
    rid = seed(w, "大豆根腐", "failed", ann, reason="記憶體不足")
    c = login(w, "ann")
    for url in ("/?lang=en", "/?run=%s&lang=en" % rid):
        t = c.get(url).text
        assert "大豆根腐" in t and "記憶體不足" in t


def test_tcl39_l40_english_404(w):
    # TC-L39, TC-L40
    w.user("ann")
    bob = w.user("bob")
    seed(w, "bobs", "running", bob, run_id="bob-run-id")
    c = login(w, "ann")
    missing = c.get("/?run=nope-xyz-4471&lang=en")
    other = c.get("/?run=bob-run-id&lang=en")
    assert missing.status_code == 404 and other.status_code == 404 and no_cjk(missing.text)
    assert "nope-xyz-4471" not in missing.text
    assert other.content == c.get("/?run=another-missing&lang=en").content


def test_tcl41_odd_lang_values(w):
    # TC-L41
    w.user("ann")
    c = login(w, "ann")
    for v in ("fr", "", "<script>", "EN", "en,zh"):
        for path in ("/", "/settings"):
            r = c.get(path, params={"lang": v})
            assert r.status_code == 200 and 'lang="zh-Hant"' in r.text and "<script>" not in r.text, v


def test_tcl42_string_table():
    # TC-L42
    from abf_platform import web_board
    table = web_board.STRINGS
    assert set(table) == {"zh", "en"} and set(table["zh"]) == set(table["en"])
    assert all(v for lang in table.values() for v in lang.values())
    assert not [k for k, v in table["en"].items() if cjk(v)]


def test_tcl43_english_empty_state(w):
    # TC-L43
    w.user("ann")
    r = login(w, "ann").get("/?lang=en")
    assert r.status_code == 200 and no_cjk(r.text) and "No runs yet" in r.text


def test_tcl44_no_external_url_script_or_style_attribute(w):
    # TC-L44
    ann = w.user("ann")
    ids = seed_three(w, ann)
    c = login(w, "ann")
    w.user("bob")
    empty = login(w, "bob")
    urls = ["/", "/settings", "/?run=" + ids["running"], "/?run=%s&stage=running" % ids["running"], "/?run=nope"]
    urls += [u + ("&" if "?" in u else "?") + "lang=en" for u in urls]
    pages = [(u, c.get(u).text) for u in urls]
    pages += [("empty " + u, empty.get(u).text) for u in ("/", "/?lang=en", "/?run=nope")]
    assert "No runs yet" in empty.get("/?lang=en").text
    for u, t in pages:
        assert not re.search(r"https?://", t) and not re.search(r'(?:href|src|action)="(?:https?:)?//', t), u
        assert "<script" not in t.lower() and not re.search(r"\sstyle=", t) and not re.search(r"\son[a-z]+=", t, re.I), u


def test_tcs48_no_dead_links(w):
    # TC-S48
    ann = w.user("ann")
    ids = four(w, ann)
    w.user("bob")
    bob = login(w, "bob")
    c = login(w, "ann")
    mine = set(ids.values())
    starts = ["/", "/settings", "/?run=nope", "/?lang=en"]
    seen = set()
    for who, client in (("ann", c), ("bob", bob)):
        urls = starts + (["/?run=%s&stage=%s" % (i, s) for i in ids.values() for s in STAGES] if who == "ann" else [])
        for url in urls:
            for h in hrefs(client.get(url).text):
                h = htmllib.unescape(h)
                assert h.startswith("/") and not h.startswith("//"), h
                if (who, h) in seen:
                    continue
                seen.add((who, h))
                assert client.get(h).status_code == 200, h
                rids = parse_qs(urlsplit(h).query).get("run")
                assert not rids or rids[0] in mine, h


# ---- not in this PR ---------------------------------------------------------------------------------------------------------------

def test_tn02_no_detail_logs_or_resume(w):
    # TC-N02
    ann = w.user("ann")
    rid = seed(w, "bad", "failed", ann, reason="boom")
    c = login(w, "ann")
    t = c.get("/?run=" + rid).text
    # 011b: the page has a Logs tab (a grey panel) whose link says tab=logs; links are not what this pin is about, so strip them first
    assert not re.search(r"(?i)resume|restart|/logs|\blogs?\b", re.sub(r'(href|action)="[^"]*"', "", t)) and "boom" in t     # 012b: the buttons post to /act/resume
    for p in ("/runs/" + rid, "/runs/%s/logs" % rid, "/resume", "/restart"):
        assert c.get(p).status_code == 404 and c.post(p).status_code in (404, 405), p


def test_tn04_other_paths_stay_missing(w):
    # TC-N04
    w.user("ann")
    c = login(w, "ann")
    for path in ("/runs", "/ce", "/compute-envs", "/oauth/token", "/oauth/authorize", "/admin", "/submit", "/upload",
                 "/password", "/passwd", "/cost", "/setup", "/api/launch"):
        assert c.get(path).status_code == 404, path
        assert c.post(path, data={"a": "b"}).status_code in (404, 405), path


def test_tn05_no_new_tool_or_action(w):
    # TC-N05
    from abf_platform import actions
    tools, _ = w.mcp([])
    assert sorted(t.name for t in tools) == sorted(["list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents",
                                                    "list_site_files", "list_used_pipelines", "read_task_log", "run_outputs", "my_usage", "launch", "cancel", "forget", "resume", "relaunch"])
    assert not [n for n in dir(actions) if "board" in n]


def test_tn06_no_push_routes(w):
    # TC-N06
    w.user("ann")
    c = login(w, "ann")
    assert not [r.path for r in c.app.routes if re.search(r"ws|stream|events|sse", r.path)]
    assert "<script" not in c.get("/").text


def test_tn09_language_is_not_remembered(w):
    # TC-N09
    ann = w.user("ann")
    seed(w, "r", "running", ann)
    c = login(w, "ann")
    r = c.get("/?lang=en")
    assert "set-cookie" not in r.headers and 'lang="en"' in r.text
    assert 'lang="zh-Hant"' in c.get("/").text


def test_tn10_n13_n17_n19_n20_nothing_beyond_the_plan(w):
    # TC-N10, TC-N13, TC-N17, TC-N19, TC-N20
    ann = w.user("ann")
    rid = seed(w, "r", "running", ann, counts=dict(succeeded=1, running=1))
    c = login(w, "ann")
    for url in ["/", "/settings"] + ["/?run=%s&stage=%s" % (rid, s) for s in STAGES]:
        t = c.get(url).text
        for tag in ("<textarea", "<select", "<iframe", "<table", 'type="radio"', 'type="checkbox"'):
            if tag == "<table" and url == "/settings":      # settings-page ruling 11: only /settings may carry a table (the compute environments)
                continue
            assert tag not in t, (url, tag)
        assert [m for m in re.findall(r"<input\b[^>]*>", t) if 'type="hidden"' not in m or not ('name="csrf"' in m or 'name="run"' in m or 'name="lang"' in m)] == []     # 012b: the buttons carry the run id (and the language)
        assert t.count("<details") - t.count('<details class="menu">') == len(re.findall(r"<details open\b[^>]*data-stage=", pane(t, "right")))
        for h in hrefs(t):
            u = urlsplit(htmllib.unescape(h))
            assert u.path in ("/", "/settings", "/launch", "/usage") and set(parse_qs(u.query)) <= {"run", "stage", "lang", "tab", "from"}, h      # 011b adds ?tab=; 012b the launch page and ?from=
        for word in ("系統自動處理紀錄", "待你決定", "Awaiting you", "拖放", "MultiQC"):     # 011b: 目前步驟／Current step／Metrics now exist
            assert word not in t, (url, word)
    left = pane(c.get("/").text, "left")
    assert not re.search(r"project|analys|專案|分析", " ".join(hrefs(left)), re.I)


def test_tcs50_red_number_matches_attention(w):
    # TC-S50 (web v2: the red number and the Now entry are gone; `/` opens, for each person, the newest failed or lost run of their own, else their newest)
    ann, bob, cyd = w.user("ann"), w.user("bob"), w.user("cyd")
    for i in range(2):
        seed(w, "a-run%d" % i, "running", ann)
    seed(w, "a-bad", "failed", ann)
    seed(w, "a-gone", "lost", ann)
    for i in range(3):
        seed(w, "a-ok%d" % i, "succeeded", ann)
    seed(w, "b-bad", "failed", bob)
    seed(w, "c-ok", "succeeded", cyd)
    seed(w, "c-go", "running", cyd)
    for name, want in (("ann", "a-gone"), ("bob", "b-bad"), ("cyd", "c-go")):
        c = login(w, name)
        for url in ("/", "/settings", "/?lang=en"):
            t = c.get(url).text
            assert 'class="red"' not in t and "Now" not in t and "現在" not in t, (name, url)
        assert "<h1>%s</h1>" % want in pane(c.get("/").text, "middle"), name
    t = login(w, "ann").get("/").text
    assert ".red{" not in style_of(t)


def test_tcs51_no_time_in_right_column(w):
    # TC-S51 (web v2: the right column shows the time of a notice as HH:mm only; the date stays in the middle column)
    ann = w.user("ann")
    s = seed(w, "ok", "succeeded", ann, started=epoch(2026, 10, 17, 20, 30), ended=epoch(2026, 10, 18, 1, 12), counts=dict(succeeded=3))
    g = seed(w, "bad", "failed", ann, started=epoch(2026, 10, 17, 20, 30), ended=epoch(2026, 10, 18, 1, 12))
    c = login(w, "ann")
    p = plain(pane(c.get("/?run=" + g).text, "right"))
    assert "09:12" in p and not re.search(r"\d\d-\d\d \d\d:\d\d", p)
    assert not re.search(r"\d\d:\d\d", plain(pane(c.get("/?run=" + s).text, "right")))
    assert "10-18 09:12" in plain(pane(c.get("/?run=" + s + "&tab=info").text, "middle"))


def test_r10_reason_marker_left_tag_and_wrapping(w):
    # R10-1: a cut reason line ends with the ellipsis after REASON_CAP characters; an exact-80 line is not cut; the Run info tab keeps it all
    ann = w.user("ann")
    full = "A" * 79 + "B" * 40
    seed(w, "cut", "failed", ann, reason=full, run_id="id-cut")
    seed(w, "exact", "failed", ann, reason="E" * 80, run_id="id-exact")
    c = login(w, "ann")
    cause = lambda rid: plain(re.search(r"<dt>原因</dt>\s*<dd>(.*?)</dd>", pane(c.get("/?run=" + rid).text, "right"), re.S).group(1))
    assert cause("id-cut") == "A" * 79 + "B" + "…" and cause("id-exact") == "E" * 80
    assert full in c.get("/?run=id-cut&tab=info").text      # 011b: the whole reason moved to the Run info tab (TC-R11 keeps it off the default tab)
    # R10-2: left tag is the status text, both languages
    bob = w.user("bob")
    for n, st in (("r1", "running"), ("r2", "failed"), ("r3", "succeeded"), ("r4", "lost")):
        seed(w, n, st, bob)
    for lang, want in (("", {"r1": "執行中", "r2": "失敗", "r3": "完成", "r4": "失敗"}),
                       ("?lang=en", {"r1": "Running", "r2": "Failed", "r3": "Succeeded", "r4": "Failed"})):
        page = login(w, "bob").get("/" + lang).text
        for r in rows(page):
            name = re.search(r"\b(r[1-4])\b", plain(r)).group(1)
            assert re.search(r'<span class="stg">%s</span>' % re.escape(want[name]), r), (lang, name)
    # R10-3: the stylesheet lets long names and reasons wrap
    css = style_of(page)
    for cls in (".card", ".reason", ".notice", ".scard"):
        rules = re.findall(r"([^{}]+)\{([^}]*)\}", css)
        assert any(cls in [x.strip() for x in sel.split(",")] and re.search(r"overflow-wrap:\s*anywhere|min-width:\s*0", body)
                   for sel, body in rules), cls
    assert re.search(r"\.fields dd\{[^}]*overflow-wrap:\s*anywhere", css)