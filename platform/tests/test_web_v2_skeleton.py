# Nothing existing: tests of the web v2 skeleton (DESIGN.md v2: list on the left, three states, Seqera-style failure notice on the right); the pages are ours.
"""web-v2-skeleton: test cases are named in the comments (TC-001 ...), see specs/web-v2-skeleton/test-case.md. Runs are seeded straight into index.db."""
import base64
import calendar
import hashlib
import re
import time

import pytest

from human_harness import World
from test_web_board import hrefs, no_cjk, pane, plain, seed
from test_web_running import extra

NOW = time.time()
HOUR = 3600
PROJECT_A, PROJECT_B = "nf-core/ampliseq", "nf-core/rnaseq"
REASON = "line one\nline two\n\nline three has 24 GB\nline four\nline five\n"
FAILED_STEP = "NFCORE_AMPLISEQ:DADA2_DENOISING"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def project(w, rid, name):
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    with con:
        con.execute("UPDATE runs SET project_name = ? WHERE id = ?", (name, rid))
    con.close()


def stop_requested(w, run_name):
    from abf_platform import store
    con = store.connect_state(w.ip.state_db)
    with con:
        con.execute("UPDATE launches SET cancel_requested_at = ? WHERE run_name = ?", (NOW, run_name))
    con.close()


def std(w):
    """The standard seed of the test cases: Ann's six runs (newest first) and Bob's one, newer than all of Ann's."""
    ann, bob = w.user("ann"), w.user("bob")
    ids = {}
    ids["running"] = seed(w, "ann-running", "running", ann, started=NOW - 1 * HOUR, counts=dict(succeeded=2, running=1, pending=2))
    project(w, ids["running"], PROJECT_A)
    ids["resume"] = seed(w, "ann-failed-resume", "failed", ann, started=NOW - 2 * HOUR, counts=dict(succeeded=3, failed=1), reason=REASON)
    extra(w, ids["resume"], tasks=[(FAILED_STEP, 137, "Process exceeded memory\nsecond")])
    project(w, ids["resume"], PROJECT_B)
    ids["done"] = seed(w, "ann-done", "succeeded", ann, started=NOW - 3 * HOUR, counts=dict(succeeded=4))
    project(w, ids["done"], PROJECT_A)
    ids["relaunch"] = seed(w, "ann-failed-relaunch", "failed", ann, started=NOW - 4 * HOUR, counts=dict(failed=1), reason="boom\n")
    extra(w, ids["relaunch"], tasks=[("TRIMGALORE (s1)", 1, "cutadapt failed")])
    project(w, ids["relaunch"], PROJECT_B)
    ids["lost"] = seed(w, "ann-lost", "lost", ann, started=NOW - 5 * HOUR)
    ids["stopped"] = seed(w, "ann-cancelled", "failed", ann, started=NOW - 6 * HOUR, counts=dict(succeeded=1, failed=1))
    stop_requested(w, "ann-cancelled")
    ids["bob"] = seed(w, "bob-failed", "failed", bob, started=NOW - 1800, reason="bob reason")
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    return ann, c, ids


def left_rows(text):
    """[(href, class, line 1 text, line 2 text)] of the left column rows, in page order."""
    out = []
    for m in re.finditer(r'<a class="(row[^"]*)" href="([^"]*)">(.*?)</a>', pane(text, "left"), re.S):
        l1 = re.search(r'<span class="r1">(.*?)</span></span>|<span class="r1">(.*)', m.group(3), re.S)
        two = re.search(r'<span class="r2">(.*?)</span>', m.group(3), re.S)
        out.append((m.group(2), m.group(1), plain(m.group(3).split('<span class="r2">')[0]), plain(two.group(1)) if two else ""))
    return out


def groups(text):
    """[(group name, [row names])] of the left column."""
    out = []
    for m in re.finditer(r'<section class="proj"><h3>(.*?)</h3>(.*?)</section>', pane(text, "left"), re.S):
        out.append((plain(m.group(1)), [plain(re.search(r'<span class="nm">(.*?)</span>', r, re.S).group(1))
                                        for r in re.findall(r'<a class="row.*?</a>', m.group(2), re.S)]))
    return out


def h1(text):
    return plain(re.search(r"<h1>(.*?)</h1>", pane(text, "middle"), re.S).group(1))


def right_notices(text):
    return re.findall(r"<article\b.*?</article>", pane(text, "right"), re.S)


def dts(notice):
    return [plain(x) for x in re.findall(r"<dt>(.*?)</dt>", notice, re.S)]


def dd(notice, key):
    return re.search(r"<dt>%s</dt>\s*<dd>(.*?)</dd>" % key, notice, re.S).group(1)


def buttons(text):
    return [plain(x) for x in re.findall(r"<button\b[^>]*>(.*?)</button>", text, re.S)]


def test_v01_root_opens_newest_failed_run(w):
    # TC-001, TC-002, TC-008, TC-009, TC-012, TC-031
    _, c, ids = std(w)
    r = c.get("/")
    assert r.status_code == 200
    assert h1(r.text) == "ann-failed-resume"
    assert "bob-failed" not in r.text
    assert 'data-card=' not in r.text and 'class="red"' not in r.text
    assert "現在" not in r.text and "Now" not in r.text and "正在跑" not in r.text and "需要注意" not in r.text
    rows = left_rows(r.text)
    assert len(rows) == 6 and all("✓" in x[2] or "▶" in x[2] or "✗" in x[2] for x in rows)
    assert [x[0] for x in rows if "here" in x[1].split()] == ["/?run=" + ids["resume"]]
    assert [x for x in rows if "ann-running" in x[2]][0][3] == "執行 · 2 / 5"
    page = c.get("/?run=" + ids["done"]).text
    assert h1(page) == "ann-done"
    assert [x[0] for x in left_rows(page) if "here" in x[1].split()] == ["/?run=" + ids["done"]]


def test_v01b_lost_counts_as_needing_the_person(w):
    # TC-004, TC-005
    ann = w.user("ann")
    seed(w, "ann-running", "running", ann, started=NOW - HOUR)
    seed(w, "ann-done", "succeeded", ann, started=NOW - 2 * HOUR)
    seed(w, "ann-lost", "lost", ann, started=NOW - 3 * HOUR)
    seed(w, "ann-stop", "failed", ann, started=NOW - 4 * HOUR)
    c = w.web()
    w.login(c, "ann")
    assert h1(c.get("/").text) == "ann-lost"
    # two failed runs with the same start: the one list_runs gives first (the later written) wins
    w2 = seed(w, "ann-f-a", "failed", ann, started=NOW - 10)
    w3 = seed(w, "ann-f-b", "failed", ann, started=NOW - 10)
    assert h1(c.get("/").text) == "ann-f-b"


def test_v02_root_without_failed_opens_newest(w):
    # TC-003
    ann = w.user("ann")
    seed(w, "ann-running", "running", ann, started=NOW - HOUR)
    seed(w, "ann-done", "succeeded", ann, started=NOW - 2 * HOUR)
    c = w.web()
    w.login(c, "ann")
    assert h1(c.get("/").text) == "ann-running"


def test_v03_root_empty_state(w):
    # TC-006, TC-007, TC-010, TC-080
    ann, bob = w.user("ann"), w.user("bob")
    seed(w, "bob-failed", "failed", bob, started=NOW - HOUR)
    c = w.web()
    w.login(c, "ann")
    r = c.get("/")
    assert r.status_code == 200
    mid = pane(r.text, "middle")
    assert "還沒有分析" in plain(mid) and "<h1>" not in mid and "bob-failed" not in r.text
    assert re.search(r'<a [^>]*href="/launch"[^>]*>＋ 新分析</a>', mid)
    right = pane(r.text, "right")
    assert "這個分析的對話" in plain(right) and "—" in plain(right) and "<button" not in right and "<form" not in right
    en = c.get("/?lang=en").text
    assert "No analyses yet" in en and no_cjk(en)


def test_v04_only_three_state_words(w):
    # TC-013, TC-014, TC-015, TC-016, TC-017, TC-018, TC-019
    _, c, ids = std(w)
    bad = ("失聯", "暫停", "Lost", "Paused", "⏸", "state-lost")
    for url in ("/", "/?run=" + ids["lost"], "/?run=" + ids["stopped"], "/?run=" + ids["done"], "/?run=%s&tab=info" % ids["lost"]):
        t = c.get(url).text
        assert not any(b in t for b in bad), (url, [b for b in bad if b in t])
    t = c.get("/").text
    word = lambda name: [x for x in left_rows(t) if name in x[2]][0]
    assert "▶ 執行中" in word("ann-running")[2] and "✓ 完成" in word("ann-done")[2]
    for name in ("ann-failed-resume", "ann-lost", "ann-cancelled"):
        assert "✗ 失敗" in word(name)[2], name
    assert "state-failed" in word("ann-lost")[1] and "state-running" in word("ann-running")[1] and "state-succeeded" in word("ann-done")[1]
    for key in ("lost", "stopped", "resume"):
        page = c.get("/?run=" + ids[key]).text
        assert re.search(r'<span class="badge state-failed">✗ 失敗</span>', page)
    en = c.get("/?lang=en").text
    assert "▶ Running" in en and "✓ Succeeded" in en and "✗ Failed" in en
    launch = c.get("/launch?from=%s&lang=en" % ids["done"]).text      # TC-019: the chips of the launch page are not touched
    assert re.search(r'<span class="chip state-succeeded"><span class="sq"></span> ?Done</span>', launch)


def test_v05_left_grouped_by_project(w):
    # TC-020, TC-021, TC-022, TC-024, TC-025..TC-030, TC-032, TC-033, TC-035, TC-036
    ann, c, ids = std(w)
    t = c.get("/").text
    assert groups(t) == [(PROJECT_A, ["ann-running", "ann-done"]), (PROJECT_B, ["ann-failed-resume", "ann-failed-relaunch"]),
                         ("未分專案", ["ann-lost", "ann-cancelled"])]
    second = {name: [x for x in left_rows(t) if name in x[2]][0][3] for name in
              ("ann-running", "ann-failed-resume", "ann-failed-relaunch", "ann-lost", "ann-cancelled", "ann-done")}
    assert second == {"ann-running": "執行 · 2 / 5", "ann-failed-resume": "執行 · " + FAILED_STEP, "ann-failed-relaunch": "執行 · TRIMGALORE (s1)",
                      "ann-lost": "執行 · 站台沒有回應", "ann-cancelled": "執行 · 已取消", "ann-done": "結果"}, second
    for href, cls, l1, l2 in left_rows(t):
        assert re.fullmatch(r"/\?run=id-ann-[a-z-]+", href)
    left = pane(t, "left")
    assert re.search(r'<a [^>]*href="/launch"[^>]*>＋ 新分析</a>', left) and "啟動分析" not in left
    assert re.search(r'href="/settings"', left) and 'action="/logout"' in left and "之後開放" in left
    en = c.get("/?lang=en").text
    assert [g for g, _ in groups(en)][-1] == "No project" and no_cjk(en)
    texts = " ".join(x[3] for x in left_rows(en))
    assert "Cancelled" in texts and "Site not responding" in texts and "Results" in texts and "Run · 2 / 5" in texts
    # no stored project name at all: the run goes to the last group (TC-037), and a failed run with no failed task shows a dash (TC-027)
    seed(w, "ann-newest", "succeeded", ann, started=NOW - 10)
    seed(w, "ann-bare", "failed", ann, started=NOW - 20)
    t2 = c.get("/").text
    assert groups(t2)[-1][0] == "未分專案" and groups(t2)[-1][1][0] == "ann-newest"
    assert [x for x in left_rows(t2) if "ann-bare" in x[2]][0][3] == "執行 · —"
    # group order follows the newest run of each group, not the alphabet (TC-023)
    seed(w, "ann-rna-new", "succeeded", ann, started=NOW - 5)
    project(w, "id-ann-rna-new", PROJECT_B)
    assert [g for g, _ in groups(c.get("/").text)][:2] == [PROJECT_B, PROJECT_A]


def test_v05b_list_cap_and_owner(w):
    # TC-034, TC-035
    from abf_platform import web_board
    ann, bob = w.user("ann"), w.user("bob")
    for i in range(web_board.LIST_CAP + 5):
        seed(w, "ann-r%03d" % i, "succeeded", ann, started=NOW - 1000 - i)
    seed(w, "bob-x", "failed", bob, started=NOW)
    c = w.web()
    w.login(c, "ann")
    t = c.get("/").text
    assert len(left_rows(t)) == web_board.LIST_CAP and "還有 5 筆" in plain(pane(t, "left")) and "bob-x" not in t


def test_v06_right_is_this_analysis_only(w):
    # TC-050, TC-051, TC-052, TC-053, TC-076, TC-077
    _, c, ids = std(w)
    t = c.get("/?run=" + ids["running"]).text
    right = pane(t, "right")
    assert "這個分析的對話" in plain(right) and "ann-running" in plain(right) and "目前沒有待處理的事" in plain(right)
    assert "<article" not in right and "<form" not in right
    for other in ("ann-done", "ann-lost", "ann-failed", "ann-cancelled", "bob"):
        assert other not in right
    assert "全部分析" not in right and "data-stage=" not in right and "✓ 1" not in right
    assert plain(right).endswith("問這個分析 之後開放") and "<textarea" not in right and "<input" not in right
    f = pane(c.get("/?run=" + ids["resume"]).text, "right")
    for other in ("ann-running", "ann-done", "ann-lost", "ann-cancelled", "ann-failed-relaunch"):
        assert other not in f
    assert "Ask about this analysis" in plain(pane(c.get("/?run=%s&lang=en" % ids["running"]).text, "right"))


def test_v07_failure_notice_fields(w):
    # TC-054, TC-055, TC-056, TC-057, TC-059, TC-060, TC-065, TC-066, TC-073, TC-074, TC-075, TC-101
    ann, c, ids = std(w)
    t = c.get("/?run=" + ids["resume"]).text
    [n] = right_notices(t)
    assert re.search(r'<span class="level state-failed"><span class="sq"></span> 待處理</span>', n)
    assert "需要你處理" not in t and "Action needed" not in t
    assert dts(n) == ["步驟", "原因", "之後"]
    assert dd(n, "步驟").strip() == "<code>%s</code>" % FAILED_STEP
    assert [plain(x) for x in dd(n, "原因").split("<br>")] == ["line three has 24 GB", "line four", "line five"]
    assert "line two" not in n and plain(dd(n, "之後")) == "續跑（確認頁）"
    assert plain(re.search(r'class="level[^>]*>.*?</span></span>', n, re.S).group(0)) == "待處理"
    for old in ("問題", "可選動作", "Options", "三次心跳"):
        assert old not in n
    [m] = right_notices(c.get("/?run=" + ids["relaunch"]).text)
    assert plain(dd(m, "之後")) == "重跑（確認頁）"
    # TC-060: a very long last line is cut at REASON_CAP characters
    from abf_platform import web_board
    long = "x" * 200 + "END"
    rid = seed(w, "ann-long", "failed", ann, started=NOW - 5, reason="first\n" + "a" * 100 + "Z")
    [n2] = right_notices(c.get("/?run=" + rid).text)
    shown = plain(dd(n2, "原因"))
    assert "a" * web_board.REASON_CAP in shown and "a" * (web_board.REASON_CAP + 1) not in shown and "Z" not in shown
    # TC-075: the words come from the record only
    a = seed(w, "ann-u1", "failed", ann, started=NOW - 6, reason="UNIQUE-ONE")
    extra(w, a, tasks=[("STEP_ONE", 1, "m")])
    [n3] = right_notices(c.get("/?run=" + a).text)
    assert plain(dd(n3, "原因")) == "UNIQUE-ONE" and plain(dd(n3, "步驟")) == "STEP_ONE"


def test_v07b_time_and_fallback_reasons(w):
    # TC-058, TC-061, TC-062, TC-063, TC-064, TC-067, TC-068
    ann = w.user("ann")
    ended = calendar.timegm((2023, 11, 14, 2, 5, 0))
    a = seed(w, "ann-t", "failed", ann, started=ended - 600, ended=ended, reason="r")
    lost = seed(w, "ann-l", "lost", ann, started=ended - 1200)
    extra(w, lost, last=calendar.timegm((2023, 11, 14, 3, 7, 0)))
    b = seed(w, "ann-e", "failed", ann, started=NOW - 100)
    extra(w, b, tasks=[("STEP", 1, "first line\nsecond line")])
    d = seed(w, "ann-bare", "failed", ann, started=NOW - 200)
    stopped = seed(w, "ann-stop", "failed", ann, started=NOW - 300)
    stop_requested(w, "ann-stop")
    c = w.web()
    w.login(c, "ann")
    assert "10:05" in plain(right_notices(c.get("/?run=" + a).text)[0])
    nl = right_notices(c.get("/?run=" + lost).text)[0]
    assert "11:07" in plain(nl) and plain(dd(nl, "原因")) == "站台沒有回應" and "state-failed" in nl
    assert plain(dd(right_notices(c.get("/?run=" + b).text)[0], "原因")) == "first line"
    nb = right_notices(c.get("/?run=" + d).text)[0]
    assert plain(dd(nb, "原因")) == "—" and plain(dd(nb, "步驟")) == "—"
    assert plain(dd(right_notices(c.get("/?run=" + stopped).text)[0], "原因")) == "已取消"
    en = right_notices(c.get("/?run=%s&lang=en" % lost).text)[0]
    assert plain(dd(en, "Reason")) == "Site not responding"
    assert plain(dd(right_notices(c.get("/?run=%s&lang=en" % stopped).text)[0], "Reason")) == "Cancelled"


def test_v08_exactly_one_button_actions0(w):
    # TC-069, TC-070, TC-071, TC-079
    _, c, ids = std(w)
    for key, verb, word, en in (("resume", "resume", "續跑", "Resume"), ("relaunch", "relaunch", "重跑", "Re-run")):
        right = pane(c.get("/?run=" + ids[key]).text, "right")
        assert len(re.findall(r"<form\b", right)) == 1 and buttons(right) == [word]
        m = re.search(r'<form class="act" method="post" action="/act/(\w+)">(.*?)</form>', right, re.S)
        assert m.group(1) == verb
        fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', m.group(2)))
        r = c.post("/act/" + verb, data=fields)
        assert r.status_code == 303 and re.fullmatch(r"/c/[0-9a-f]{32}", r.headers["location"])
        right_en = pane(c.get("/?run=%s&lang=en" % ids[key]).text, "right")
        assert buttons(right_en) == [en] and 'name="lang" value="en"' in right_en


def test_v09_button_text_is_fixed_verb(w):
    # TC-072, TC-046, TC-048, TC-091
    _, c, ids = std(w)
    for key in ("resume", "relaunch", "lost", "stopped", "running", "done"):
        for lang, ok in (("", {"續跑", "重跑", "取消", "登出"}), ("&lang=en", {"Resume", "Re-run", "Cancel", "Log out"})):
            t = c.get("/?run=%s%s" % (ids[key], lang)).text
            assert set(buttons(t)) <= ok, (key, buttons(t))
            assert not any(re.search(r"\d|GB|\.", b) for b in buttons(t))
            assert "處置" not in t
    mid = pane(c.get("/?run=" + ids["resume"]).text, "middle")
    assert {"resume", "relaunch", "cancel"} <= set(re.findall(r'action="/act/(\w+)"', mid))
    right = pane(c.get("/?run=" + ids["resume"]).text, "right")
    for gone in ("已自動處理", "診斷", "依據", "打包", "下一步"):
        assert gone not in right


def test_v10_lost_and_cancelled_reason(w):
    # TC-061, TC-062, TC-018
    _, c, ids = std(w)
    assert plain(dd(right_notices(c.get("/?run=" + ids["lost"]).text)[0], "原因")) == "站台沒有回應"
    assert plain(dd(right_notices(c.get("/?run=" + ids["stopped"]).text)[0], "原因")) == "已取消"


def test_v11_no_notice_in_middle(w):
    # TC-043, TC-044, TC-045, TC-039, TC-040
    _, c, ids = std(w)
    for key in ("resume", "lost", "running"):
        t = c.get("/?run=" + ids[key]).text
        mid = pane(t, "middle")
        assert 'class="notice' not in mid and "這個分析的通知" not in mid
        assert t.index('data-pane="left"') < t.index('data-pane="middle"') < t.index('data-pane="right"')
    t = c.get("/?run=" + ids["resume"]).text
    mid = pane(t, "middle")
    assert len(re.findall(r'class="scard"', mid)) == 4 and len(re.findall(r'<nav class="rtabs">.*?</nav>', mid, re.S)) == 1
    assert len(re.findall(r"<a [^>]*href=[^>]*>", re.search(r'<nav class="rtabs">.*?</nav>', mid, re.S).group(0))) == 5
    assert "← 上一階段" in mid and "下一階段 →" in mid
    assert re.findall(r'data-step="(\w+)"', mid) == ["launch", "running", "results", "downstream", "finished"]
    assert re.search(r'data-current="results"', c.get("/?run=" + ids["done"]).text)


def test_v12_terminal_switch_is_grey(w):
    # TC-041, TC-042, TC-049, TC-090
    _, c, ids = std(w)
    mid = pane(c.get("/?run=" + ids["resume"]).text, "middle")
    assert re.search(r'<a [^>]*aria-current="page"[^>]*>主視窗</a>', mid)
    assert "終端機" in mid and not re.search(r"<a [^>]*>[^<]*終端機", mid) and re.search(r"終端機\s*<span[^>]*>之後開放</span>", mid)
    en = pane(c.get("/?run=%s&lang=en" % ids["resume"]).text, "middle")
    assert "Terminal" in en and "Coming later" in en
    assert c.get("/terminal").status_code == 404
    assert "<iframe" not in mid and "ttyd" not in mid


def test_v13_owner_rule(w):
    # TC-009, TC-011, TC-035
    _, c, ids = std(w)
    r = c.get("/?run=" + ids["bob"])
    assert r.status_code == 404 and "bob-failed" not in r.text and ids["bob"] not in r.text
    assert "bob" not in c.get("/").text


def test_v14_english(w):
    # TC-017, TC-049, TC-078, TC-086
    _, c, ids = std(w)
    for url in ["/?lang=en"] + ["/?run=%s&lang=en" % i for k, i in ids.items() if k != "bob"]:
        t = c.get(url).text
        assert no_cjk(t), (url, re.findall(r"[　-〿㐀-鿿＀-￯]", t))
    t = c.get("/?run=%s&lang=en" % ids["resume"]).text
    right = pane(t, "right")
    assert "This analysis" in right and dts(right_notices(t)[0]) == ["Step", "Reason", "Next"]
    assert plain(dd(right_notices(t)[0], "Next")) == "Resume (confirmation page)"
    assert re.search(r'<span class="level state-failed"><span class="sq"></span> Pending</span>', right)
    assert plain(dd(right_notices(t)[0], "Reason")) == "line three has 24 GB line four line five"


def test_v15_constraints_hold(w):
    # TC-081, TC-082, TC-083, TC-084, TC-085, TC-089
    ann = w.user("ann")
    c0 = w.web()
    w.login(c0, "ann")
    empty = c0.get("/")
    pages = [empty]
    seed(w, "ann-f", "failed", ann, started=NOW - 10, reason="r")
    pages += [c0.get("/"), c0.get("/?run=id-ann-f")]
    for r in pages:
        t = r.text
        assert "<script" not in t and "style=" not in t and len(re.findall(r"<style>", t)) == 1 and "<link" not in t
        assert '<meta http-equiv="refresh" content="15">' in t
        assert not re.search(r'(src|href)="https?://', t) and "@import" not in t
        css = re.search(r"<style>(.*?)</style>", t, re.S).group(1)
        digest = "'sha256-%s'" % base64.b64encode(hashlib.sha256(css.encode("utf-8")).digest()).decode("ascii")
        assert digest in r.headers["content-security-policy"]
        assert ":focus-visible{outline" in css


def test_v16_project_key(w):
    # TC-038
    from abf_platform import actions
    ann, c, ids = std(w)
    listed = {r["name"]: r for r in actions.list_runs(w.ip.index, caller=ann, platform_path=w.ip.state_db)["runs"]}
    assert listed["ann-running"]["project"] == PROJECT_A and listed["ann-failed-resume"]["project"] == PROJECT_B
    assert "project" in listed["ann-lost"] and listed["ann-lost"]["project"] is None
    got = actions.get_run(w.ip.index, ids["running"], caller=ann, platform_path=w.ip.state_db)
    assert got["project"] == PROJECT_A
    assert actions.get_run(w.ip.index, ids["lost"], caller=ann, platform_path=w.ip.state_db)["project"] is None
