# Nothing existing: tests of the formal notice component and the running stage page of spec 011b (read-only); the pages are ours.
"""011b: formal notices and the running stage page. Test cases are named in the comments (TC-R01 ...). Runs are seeded straight into index.db."""
import calendar
import html
import re

import pytest

from helpers import Clock
from human_harness import World
from test_web_board import hrefs, no_cjk, pane, plain, seed, style_of

T0 = calendar.timegm((2023, 11, 14, 0, 0, 0))
NOW = calendar.timegm((2023, 11, 14, 2, 5, 0))
FIVE = ("tasks", "logs", "info", "config", "metrics")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def extra(w, rid, procs=(), tasks=(), last=None):
    """processes [(name, n_running)], failed tasks [(name, exit, message)] and last_message_at for a seeded run."""
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    with con:
        for name, running in procs:
            con.execute("INSERT INTO processes (run_id, name, n_running) VALUES (?,?,?)", (rid, name, running))
        for i, (name, code, msg) in enumerate(tasks):
            con.execute("INSERT INTO failed_tasks (run_id, task_key, name, exit_code, error_message) VALUES (?,?,?,?,?)", (rid, str(i), name, code, msg))
        if last is not None:
            con.execute("UPDATE runs SET last_message_at = ? WHERE id = ?", (last, rid))
    con.close()


def world(w):
    ann = w.user("ann")
    c = w.web(clock=Clock(float(NOW)))
    assert w.login(c, "ann").status_code == 303
    return ann, c


def f1(w, ann, name="f1"):
    rid = seed(w, name, "failed", ann, started=T0, ended=NOW,
               counts=dict(succeeded=5, cached=4, failed=3, aborted=2, running=1, pending=6, submitted=7),
               reason="samplesheet is missing the reverseReads column\nsecond line")
    extra(w, rid, tasks=[("FASTQC (sample2)", 137, "Process exceeded memory\nsecond line"), ("TRIMGALORE (sample3)", 1, "cutadapt failed")])
    return rid


def l1(w, ann, name="l1"):
    rid = seed(w, name, "lost", ann, started=T0)
    extra(w, rid, last=calendar.timegm((2023, 11, 14, 3, 0, 0)))
    return rid


def notices(text):
    return re.findall(r'<article\b[^>]*class="notice[^"]*"[^>]*>.*?</article>', text, re.S)


def fields(notice):
    dl = re.search(r"<dl\b[^>]*>(.*?)</dl>", notice, re.S).group(1)
    return [(plain(a), plain(b)) for a, b in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", dl, re.S)]


def cards(text):
    mid = pane(text, "middle")
    return ([html.unescape(plain(x)) for x in re.findall(r'<h2 class="ct">(.*?)</h2>', mid, re.S)],
            [html.unescape(plain(x)) for x in re.findall(r'<p class="cv">(.*?)</p>', mid, re.S)])


def test_r01_r13_failed_and_lost_notice_fields(w):
    # TC-R01, TC-R02, TC-R03, TC-R04, TC-R05, TC-R06, TC-R08, TC-R09, TC-R10, TC-R13 (web v2: Seqera's fields, on the right, one button)
    ann, c = world(w)
    a, b = f1(w, ann), l1(w, ann)
    t = c.get("/?run=" + a).text
    [n] = notices(t)
    assert "待處理" in plain(n) and 'class="sq"' in n and "分析失敗" not in plain(n)
    assert "10:05" in plain(n) and "11-14" not in plain(n) and "2023-11-14T" not in t
    assert fields(n) == [("步驟", "FASTQC (sample2)"), ("原因", "samplesheet is missing the reverseReads column second line"),
                         ("之後", "續跑（確認頁）")]
    assert "TRIMGALORE" not in n
    assert "之後開放" not in n
    assert len(re.findall(r"<button\b", n)) == 1 and len(re.findall(r"<form\b", n)) == 1          # 012b: a real button that asks
    assert len(re.findall(r"<form\b", t)) == 1 + 3 + 1          # the log-out form, the run page's three buttons, the notice's one
    [m] = notices(c.get("/?run=" + b).text)
    assert fields(m) == [("步驟", "—"), ("原因", "站台沒有回應"), ("之後", "重跑（確認頁）")]
    assert "11:00" in plain(m)


def test_r12_r14_english_and_missing_data(w):
    # TC-R12, TC-R14, TC-R15, TC-R16, TC-R17, TC-R18
    ann, c = world(w)
    a, b = f1(w, ann), l1(w, ann)
    [n] = notices(c.get("/?run=%s&lang=en" % a).text)
    assert "Pending" in plain(n) and 'class="sq"' in n and no_cjk(n)
    assert [x for x, _ in fields(n)] == ["Step", "Reason", "Next"] and fields(n)[2][1] == "Resume (confirmation page)"
    [m] = notices(c.get("/?run=%s&lang=en" % b).text)
    assert no_cjk(m)
    assert fields(m) == [("Step", "—"), ("Reason", "Site not responding"), ("Next", "Re-run (confirmation page)")]
    f2 = seed(w, "f2", "failed", ann, started=T0, ended=NOW)
    [x] = notices(c.get("/?run=%s&lang=en" % f2).text)
    assert fields(x)[0] == ("Step", "—") and fields(x)[1] == ("Reason", "—")
    [y] = notices(c.get("/?run=%s" % f2).text)
    assert fields(y)[0] == ("步驟", "—") and fields(y)[1] == ("原因", "—")


def test_r07_r19_cut_and_missing_time(w):
    # TC-R07, TC-R19
    ann, c = world(w)
    f4 = seed(w, "f4", "failed", ann, started=T0, ended=NOW, reason="A" * 120 + "\nmore")
    [n] = notices(c.get("/?run=" + f4).text)
    assert fields(n)[1][1] == "A" * 80 + "… more"
    f3 = seed(w, "f3", "failed", ann, started=T0)
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    with con:
        con.execute("UPDATE runs SET ended_at = NULL WHERE id = ?", (f3,))
    con.close()
    t = c.get("/?run=" + f3).text
    assert plain(re.search(r'class="when"[^>]*>(.*?)</', notices(t)[0], re.S).group(1)) == "—" and "None" not in t
    # last_message_at is NOT NULL in index.db, so a lost run without it is fed to the component directly (L2)
    from abf_platform import web_board
    failure = {"status_seqera": "unknown", "failed_tasks": [], "failure_reason": None, "log": None, "actions": ["relaunch"]}
    lost = web_board._failure_notice(web_board.STRINGS["zh"], {"id": "x", "name": "l2", "status": "lost", "failure": failure})
    assert plain(re.search(r'class="when"[^>]*>(.*?)</', lost, re.S).group(1)) == "—" and "None" not in lost


def test_r21_no_side_stripes(w):
    # TC-R21
    ann, c = world(w)
    css = style_of(c.get("/?run=" + f1(w, ann)).text)
    rules = [r for r in css.split("}") if ".notice" in r.split("{")[0]]
    assert rules and "ui-monospace" in css
    assert not re.search(r"border-(left|right|inline-start|inline-end)", "}".join(rules))


def test_r30_r36_attention_card_uses_the_component(w):
    # TC-R30, TC-R31, TC-R32, TC-R33, TC-R36 (web v2: there is no attention card; the one notice of the opened run is in the right column)
    ann, c = world(w)
    a, b = f1(w, ann), l1(w, ann)
    seed(w, "u1", "running", ann, started=T0)
    seed(w, "s1", "succeeded", ann, started=T0)
    t = c.get("/?run=" + a).text
    right = pane(t, "right")
    ns = notices(right)
    assert len(ns) == 1 and "<li" not in right and "data-card=" not in t
    assert "l1" not in right and "u1" not in right and "s1" not in right
    assert dict(fields(ns[0]))["步驟"] == "FASTQC (sample2)"     # 012b: not "f1" in n: the buttons' hex tokens can hold it
    assert no_cjk(pane(c.get("/?run=%s&lang=en" % a).text, "right"))
    assert len(notices(c.get("/?run=" + b).text)) == 1 and "f1" not in pane(c.get("/?run=" + b).text, "right")


# What only the f1 run owns: its run id, its failure reason and its two failed tasks (its run name counts as a word).
# A bare "f1" substring is not one of them: the buttons' csrf tokens are hex digests and can hold "f1" by chance.
_F1_MARKERS = ("id-f1", "samplesheet is missing the reverseReads column", "FASTQC (sample2)", "TRIMGALORE (sample3)")


def _f1_in(right):
    """The markers of the f1 run found in a right column (empty list: nothing of f1 is there)."""
    found = ["f1 (as a word)"] if re.search(r"(?<![0-9A-Za-z])f1(?![0-9A-Za-z])", right) else []
    return found + [m for m in _F1_MARKERS if m in right]


def test_r30_r36_a_hex_token_holding_f1_cannot_trip_the_marker(w, monkeypatch):
    # TC-R30, TC-R36: with every csrf token forced to hold "f1", the old two-character check is wrong and the exact one is right
    from abf_platform import web
    ann, c = world(w)
    a, b = f1(w, ann), l1(w, ann)
    real = web._mac
    monkeypatch.setattr(web, "_mac", lambda key, *parts: "f1" * 32 if parts and parts[0] == "csrf" else real(key, *parts))
    right = pane(c.get("/?run=" + b).text, "right")
    assert "f1f1f1f1" in right                                  # the forced token really is in the right column
    assert "f1" in right                                        # so the old check ("f1" not in right) is False on a clean page
    assert _f1_in(right) == []                                  # the exact markers see nothing of the f1 run
    assert len(notices(right)) == 1
    # a real leak is still caught: the f1 run's own right column carries its markers
    own = _f1_in(pane(c.get("/?run=" + a).text, "right"))
    assert {"id-f1", "samplesheet is missing the reverseReads column", "FASTQC (sample2)"} <= set(own)   # the right column shows the first failed task only


def test_r34_empty_attention(w):
    # TC-R34 (web v2: a run that did not fail has no notice)
    ann, c = world(w)
    s1 = seed(w, "s1", "succeeded", ann, started=T0)
    u1 = seed(w, "u1", "running", ann, started=T0)
    for rid in (s1, u1):
        right = pane(c.get("/?run=" + rid).text, "right")
        assert notices(right) == [] and "目前沒有待處理的事" in right


def test_r37_other_users_data_never_shown(w):
    # TC-R37, TC-R100, TC-R101, TC-K05
    ann, c = world(w)
    f1(w, ann)
    bob = w.user("bob")
    b1 = seed(w, "bobsecretrun", "failed", bob, started=T0, ended=NOW, reason="bobsecretreason")
    extra(w, b1, tasks=[("BOBTASK", 1, "bobsecretmsg")])
    for url in ("/", "/?lang=en", "/?run=" + b1, "/?run=nope"):
        t = c.get(url).text
        assert "bobsecret" not in t and "BOBTASK" not in t
    bodies = {c.get("/?run=%s&tab=%s" % (b1, tab)).content for tab in FIVE}
    assert len(bodies) == 1 and c.get("/?run=%s" % b1).status_code == 404
    assert c.get("/?run=nope&tab=info").content in bodies


def test_r40_r44_title_and_cards(w):
    # TC-R40, TC-R41, TC-R43, TC-R44, TC-R53, TC-R54
    ann, c = world(w)
    a = f1(w, ann)
    mid = pane(c.get("/?run=" + a).text, "middle")
    assert "<h1>f1</h1>" in mid and "✗ 失敗" in plain(mid)
    head = re.search(r'<details class="menu"><summary>更多</summary>(.*?)</details>', mid, re.S).group(1)
    assert "續跑" in head and "重跑" in head and "取消" in head and "之後開放" not in head and head.count("<form") == 3 and head.count("<button") == 3     # 012b: real buttons
    assert cards(c.get("/?run=" + a).text) == (["停在", "耗時", "運算環境", "費用"], ["FASTQC (sample2)", "2 小時 5 分", "—", "SU —"])
    en = c.get("/?run=%s&lang=en" % a).text
    assert cards(en) == (["Stopped at", "Duration", "Compute", "Cost"], ["FASTQC (sample2)", "2h 5m", "—", "SU —"])
    assert no_cjk(pane(en, "middle")) and ">Resume</button>" in pane(en, "middle")


def test_r45_r52_current_step_and_duration(w):
    # TC-R45, TC-R46, TC-R47, TC-R48, TC-R51, TC-R52, TC-R59, TC-R63, TC-R64
    ann, c = world(w)

    def val(rid, i, q=""):
        return cards(c.get("/?run=%s%s" % (rid, q)).text)[1][i]
    u1 = seed(w, "u1", "running", ann, started=T0)
    extra(w, u1, procs=[("ALIGN (s1)", 1)])
    u2 = seed(w, "u2", "running", ann, started=T0)
    extra(w, u2, procs=[("CALL (s3)", 1), ("ALIGN (s1)", 1), ("BWA (s2)", 1), ("IDLE", 0)])
    u3 = seed(w, "u3", "running", ann, started=T0)
    assert val(u1, 0) == "ALIGN (s1)" and val(u2, 0) == "ALIGN (s1) 等 2 項" and val(u2, 0, "&lang=en") == "ALIGN (s1) +2 more"
    assert val(u3, 0) == "—" and val(u1, 1) == "2 小時 5 分"
    short = seed(w, "short", "failed", ann, started=T0, ended=T0 + 40)
    assert val(short, 1) == "不到 1 分" and val(short, 1, "&lang=en") == "<1m"
    assert "目前沒有待處理的事" in c.get("/?run=" + u1).text
    assert "Nothing pending" in c.get("/?run=%s&lang=en" % u1).text


def test_r55_r58_tasks_bar_and_legend(w):
    # TC-R55, TC-R56, TC-R57, TC-R58
    ann, c = world(w)
    a = f1(w, ann)
    z = seed(w, "u0", "running", ann, started=T0)
    for q, labels in (("", ["成功", "快取", "失敗", "中止", "執行中", "等待", "已送出"]),
                      ("&lang=en", ["Succeeded", "Cached", "Failed", "Aborted", "Running", "Pending", "Submitted"])):
        mid = pane(c.get("/?run=%s%s" % (a, q)).text, "middle")
        legend = re.search(r'<dl class="counts">(.*?)</dl>', mid, re.S).group(1)
        assert [(plain(x), plain(y)) for x, y in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", legend, re.S)] == \
            list(zip(labels, ["5", "4", "3", "2", "1", "6", "7"]))
        assert "<progress" in mid
    zero = pane(c.get("/?run=" + z).text, "middle")
    assert re.search(r"<progress(?![^>]*\bvalue=)[^>]*>", zero)
    assert [plain(y) for y in re.findall(r"<dd>(.*?)</dd>", re.search(r'<dl class="counts">(.*?)</dl>', zero, re.S).group(1), re.S)] == ["0"] * 7


def test_r60_r78_order_and_tabs(w):
    # TC-R60, TC-R70, TC-R71, TC-R72, TC-R73, TC-R74, TC-R75, TC-R76, TC-R77, TC-R78
    ann, c = world(w)
    a = f1(w, ann)
    mid = pane(c.get("/?run=" + a).text, "middle")
    marks = ["<h1>", 'class="views"', 'class="sumcards"', "<progress", 'class="rtabs"']
    assert [mid.index(m) for m in marks] == sorted(mid.index(m) for m in marks) and "<article" not in mid      # web v2: the notice is on the right
    nav = lambda m: re.search(r'<nav class="rtabs"[^>]*>(.*?)</nav>', m, re.S).group(1)
    links = re.findall(r"<a\b([^>]*)>(.*?)</a>", nav(mid), re.S)
    assert [plain(x) for _, x in links] == ["任務", "日誌", "執行資訊", "設定檔", "指標"]
    assert ["tab=" + k for k in FIVE] == [re.search(r"tab=\w+", h).group(0) for h, _ in links]
    assert all("run=" in h for h, _ in links) and "aria-current" in links[0][0]
    for q in ("&tab=bogus", "&tab=", "&tab=TASKS"):
        r = c.get("/?run=%s%s" % (a, q))
        assert r.status_code == 200 and "FASTQC (sample2)" in r.text
    for i, tab in enumerate(FIVE):
        m = pane(c.get("/?run=%s&tab=%s" % (a, tab)).text, "middle")
        cur = re.findall(r"<a\b[^>]*aria-current[^>]*>(.*?)</a>", nav(m), re.S)
        assert [plain(x) for x in cur] == [plain(links[i][1])]
        t = c.get("/?run=%s&tab=%s&lang=en" % (a, tab)).text
        # every link keeps lang=en except the 中 link of the language switch, which is the one that drops it
        assert [h for h in hrefs(t) if (h.startswith("/?") or h.startswith("/settings")) and "lang=en" not in h] == \
            ["/?run=%s&amp;tab=%s" % (a, tab)], tab
        assert "<script" not in t and not re.search(r"\son\w+=", t)
    t = c.get("/?run=%s&stage=running&tab=info" % a).text
    sw = re.search(r'class="switch">(.*?)</span>', t, re.S).group(1)
    assert all("run=" in h and "stage=running" in h and "tab=info" in h for h in hrefs(sw))
    assert "tab=info" in re.search(r'<ol class="steps".*?</ol>', pane(t, "middle"), re.S).group(0)
    assert [plain(x) for _, x in re.findall(r"<a\b([^>]*)>(.*?)</a>", nav(pane(c.get("/?run=%s&lang=en" % a).text, "middle")), re.S)] == \
        ["Tasks", "Logs", "Run info", "Configuration", "Metrics"]
    assert no_cjk(pane(c.get("/?run=%s&lang=en&tab=tasks" % a).text, "middle"))
    assert no_cjk(pane(c.get("/?run=%s&lang=en&tab=info" % a).text, "middle"))


def test_r79_r92_tab_contents(w):
    # TC-R79, TC-R80, TC-R82, TC-R83, TC-R84, TC-R87, TC-R88, TC-R90, TC-R91, TC-R92, TC-N08
    ann, c = world(w)
    a = f1(w, ann)
    t = pane(c.get("/?run=%s&tab=tasks" % a).text, "middle")
    table = re.search(r"<table\b.*?</table>", t, re.S).group(0)
    rows = [[plain(x) for x in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", r, re.S)] for r in re.findall(r"<tr\b.*?</tr>", table, re.S)]
    assert rows[0] == ["名稱", "結束代碼", "錯誤訊息（第一行）", "工作目錄"]
    assert rows[1] == ["FASTQC (sample2)", "137", "Process exceeded memory", "—"] and rows[2][:3] == ["TRIMGALORE (sample3)", "1", "cutadapt failed"]
    assert "second line" not in table
    for tab in FIVE:
        assert not re.search(r"\b(None|null|undefined)\b", c.get("/?run=%s&tab=%s" % (a, tab)).text)
    u = seed(w, "u1", "running", ann, started=T0)
    text = c.get("/?run=%s&tab=tasks" % u).text
    assert "沒有失敗的任務" in text and "<table" not in text
    assert "No failed tasks" in c.get("/?run=%s&tab=tasks&lang=en" % u).text
    info = plain(pane(c.get("/?run=%s&tab=info" % a).text, "middle"))
    assert "11-14 08:00" in info and "11-14 10:05" in info and a in info and "✗ 失敗" in info
    assert "—" in plain(pane(c.get("/?run=%s&tab=info" % u).text, "middle"))
    for tab in ("logs", "config", "metrics"):
        m = pane(c.get("/?run=%s&tab=%s" % (a, tab)).text, "middle")
        panel = re.search(r'<section class="soon"[^>]*>(.*?)</section>', m, re.S).group(1)
        assert "之後開放" in panel and "<a" not in panel and "<form" not in panel
        en = pane(c.get("/?run=%s&tab=%s&lang=en" % (a, tab)).text, "middle")
        assert "Coming later" in re.search(r'<section class="soon"[^>]*>(.*?)</section>', en, re.S).group(1)


def test_r81_r89_pure_functions():
    # TC-R81, TC-R89 (the pure page function, fed what a later action layer will give)
    from abf_platform import web_board
    t = web_board.STRINGS["zh"]
    task = {"name": "X", "exit_code": 1, "error_message": "m", "workdir": "/w/ab/cdef12"}
    assert "/w/ab/cdef12" in web_board.tab_body(t, "zh", {"id": "i", "name": "n", "status": "failed", "failed_tasks": [task]}, "tasks")
    run = {"id": "i", "name": "n", "status": "failed", "started_at": "2023-11-14T00:00:00Z", "cancel_requested_at": "2023-11-14T01:00:00Z"}
    assert "11-14 09:00" in web_board.tab_body(t, "zh", run, "info")


def test_r103_r114_limits_and_readonly(w):
    # TC-R103, TC-R104, TC-R105, TC-R109, TC-R113, TC-R114, TC-N01, TC-N05
    from abf_platform import web_board
    ann, c = world(w)
    a, b = f1(w, ann), l1(w, ann)
    u = seed(w, "u1", "running", ann, started=T0)
    for rid in (a, b, u):
        for tab in FIVE:
            for q in ("", "&lang=en"):
                r = c.get("/?run=%s&tab=%s%s" % (rid, tab, q))
                t = r.text
                assert len(re.findall(r"<style\b", t)) == 1 and "<link" not in t and "<script" not in t and "style=" not in t
                assert not re.search(r"\son\w+=", t) and not re.search(r"https?://|=\"//", t)
                csp = r.headers["content-security-policy"]
                assert "'unsafe-inline'" not in csp and "script-src" not in csp and web_board.style_source() in csp
                assert len(re.findall(r"<form\b", t)) == 1 + 3 + {a: 1, b: 1, u: 0}[rid]          # 012b: log-out, the run page's three buttons, the notice's one
                assert ("Seq" + "era") not in t and ("Je" + "v") not in t
                assert 'http-equiv="refresh"' in t
                for h in hrefs(t):
                    h = h.replace("&amp;", "&")
                    if h.startswith("/"):
                        assert c.get(h).status_code in (200, 303), h
    assert c.post("/?run=" + a).status_code == 405
    for p in ("/resume", "/rerun", "/relaunch", "/cancel", "/forget", "/run/%s/resume" % a, "/cost"):
        assert c.get(p).status_code == 404 and c.post(p).status_code in (404, 405), p
    assert 'http-equiv="refresh"' not in c.get("/settings").text


def test_r111_r112_stylesheet(w):
    # TC-R111, TC-R112
    ann, c = world(w)
    css = style_of(c.get("/?run=" + f1(w, ann)).text)
    for cls in (".notice", ".sumcards", ".rtabs"):
        assert cls in css
    assert "overflow-wrap:anywhere" in css and "min-width:0" in css and "max-width:900px" in css
    assert set(re.findall(r"font-size:([^;}]+)", css)) <= {"12px", "13px", "15px", "16px", "22px", "inherit"}
    assert set(re.findall(r"border-radius:([^;}]+)", css)) <= {"0", "4px", "6px", "999px"}
    for prop, val in re.findall(r"(?<![-\w])((?:padding|margin|gap|row-gap|column-gap)(?:-(?:top|right|bottom|left))?):([^;}]+)", css):
        for px in re.findall(r"(-?\d+(?:\.\d+)?)px", val):
            assert px in ("0", "4", "8", "12", "16", "24"), (prop, val)


def test_k01_notice_is_recomputed(w):
    # TC-K01
    ann, c = world(w)
    a = f1(w, ann)
    assert len(notices(c.get("/?run=" + a).text)) == 1
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    with con:
        con.execute("UPDATE runs SET final_status = 'succeeded' WHERE id = ?", (a,))
    con.close()
    assert notices(c.get("/?run=" + a).text) == [] and notices(c.get("/").text) == []


def test_n03_n04_other_stages_unchanged(w):
    # TC-N03, TC-N04
    ann, c = world(w)
    a = f1(w, ann)
    s = seed(w, "s1", "succeeded", ann, started=T0)
    for url in ("/?run=%s&stage=launch" % a, "/?run=%s&stage=results&tab=info" % s):
        t = pane(c.get(url).text, "middle")
        assert 'class="rtabs"' not in t and 'class="sumcards"' not in t and "<article" not in t
