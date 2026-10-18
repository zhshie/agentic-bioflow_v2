# Nothing existing: tests of the three-pane read-only page of spec 011a (GET /); the page, its stage rule and its limits are ours.
"""011a: the web shell. Test cases are named in the comments (TC-H01a ...). Runs are seeded straight into index.db and launches."""
import ast
import base64
import hashlib
import re
import time
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR
from human_harness import PASSWORD, World

WEB = PLATFORM_DIR / "abf_platform" / "web.py"
BOARD = PLATFORM_DIR / "abf_platform" / "web_board.py"
STAGES = ("launch", "running", "results", "downstream", "finished")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def seed(w, name, status="running", owner=None, started=None, counts=None, reason=None, run_id=None, launch_row=True):
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
                    (rid, "s-" + rid, name, final, started, started + 100 if final else None, last, reason,
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


def group_head(text, stage):
    """The heading text of the right-hand group of one stage."""
    return re.search(r'data-stage="%s"[^>]*>.*?<h3[^>]*>(.*?)</h3>' % stage, pane(text, "right"), re.S).group(1)


def items(text, stage=None):
    """The right-hand history items (whole-block links), in page order, of one group or of all."""
    right = pane(text, "right")
    if stage:
        right = re.search(r'data-stage="%s"[^>]*>(.*?)</section>' % stage, right, re.S).group(1)
    return re.findall(r'<a\b[^>]*class="[^"]*\bitem\b[^"]*"[^>]*>.*?</a>', right, re.S)


def cjk(text):
    return re.findall(r"[　-〿㐀-鿿豈-﫿＀-￯]", text)


def strip_cells(text):
    """{stage: (css classes of the cell, whole cell html)} from the five-cell stage strip in the middle column."""
    out = {}
    for m in re.finditer(r'<li\b[^>]*class="([^"]*)"[^>]*data-step="([a-z]+)"[^>]*>(.*?)</li>', pane(text, "middle"), re.S):
        out[m.group(2)] = (m.group(1).split(), m.group(0))
    return out


# ---- login and the shell --------------------------------------------------------------------------------------------------------

def test_tch01a_no_cookie_goes_to_login(w):
    # TC-H01a
    seed(w, "secret-run", owner=w.user("zed"))
    r = w.web().get("/")
    assert r.status_code == 303 and r.headers["location"] == "/login" and "secret-run" not in r.text


def test_tcl02_h21a_three_panes(w):
    # TC-L02, TC-H21a (replace TC-H01b), TC-L05, TC-L06 (replace TC-H20b, TC-H20d)
    ann = w.user("ann")
    for n in ("r1", "r2", "r3"):
        seed(w, n, "running", ann)
    r = login(w, "ann").get("/")
    assert r.status_code == 200
    left, mid, right = (pane(r.text, n) for n in ("left", "middle", "right"))
    assert "我的 run" in left and "選一個 run" in mid and "本月 SU — · 雲端 —" in plain(right)
    assert "本月費用" not in r.text and "011b" not in r.text and "尚未開放" not in r.text
    # TC-L05: each run is a link to /?run=<id>; the unbuilt items are grey text outside every link
    assert sorted(re.findall(r'<a\b[^>]*href="/\?run=([^"&]*)"', left)) == ["id-r1", "id-r2", "id-r3"]
    assert "之後開放" in left
    assert not any("之後開放" in a for a in re.findall(r"<a\b.*?</a>", left, re.S))
    # TC-L06: settings is grey text, the logout form is the only form
    foot = left[left.index("設定"):]
    assert "之後開放" in foot and "登出" in foot
    assert not [h for h in hrefs(r.text) if "settings" in h]
    assert len(re.findall(r"<form\b", r.text)) == 1


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


def test_tch21_stage_bodies(w):
    # TC-H21c, TC-H21d, TC-H21e, TC-H21f, TC-H21g
    ann = w.user("ann")
    rid = seed(w, "run-a", "running", ann, started=1_700_000_000, counts=dict(succeeded=3, running=2, pending=1))
    fid = seed(w, "run-f", "failed", ann, reason="Process terminated with an error exit status (137)")
    c = login(w, "ann")
    # TC-H21c: both times verbatim, each count paired with its label, on a run whose end time is known
    done = seed(w, "run-d", "failed", ann, started=1_700_000_000, counts=dict(succeeded=3, running=2, failed=1))
    mid = plain(pane(c.get("/?run=" + done).text, "middle"))
    assert "2023-11-14T22:13:20Z" in mid and "2023-11-14T22:15:00Z" in mid
    for label, n in (("成功", 3), ("執行中", 2), ("失敗", 1), ("快取", 0)):
        assert re.search(r"%s\s*%d(?!\d)" % (label, n), mid), (label, n)
    assert "Process terminated with an error exit status (137)" in c.get("/?run=" + fid).text
    for stage, feature in (("launch", "012b"), ("downstream", "016"), ("finished", "013b")):
        body = pane(c.get("/?run=%s&stage=%s" % (rid, stage)).text, "middle")
        assert "—" in body and feature in body, stage


def test_tcl07_to_l13_stage_strip(w):
    # TC-L07, TC-L08, TC-L09, TC-L10, TC-L11, TC-L12, TC-L13
    ann = w.user("ann")
    ids = {st: seed(w, "n-" + st, st, ann) for st in ("running", "succeeded", "failed", "lost")}
    c = login(w, "ann")
    expect = {"running": ["is-done", "is-current", "is-later", "is-later", "is-later"],
              "failed": ["is-done", "is-current", "is-later", "is-later", "is-later"],
              "lost": ["is-done", "is-current", "is-later", "is-later", "is-later"],
              "succeeded": ["is-done", "is-done", "is-current", "is-later", "is-later"]}
    for st, want in expect.items():
        cells = strip_cells(c.get("/?run=" + ids[st]).text)
        assert list(cells) == list(STAGES), st                                        # TC-L07: five cells in order
        got = [[k for k in cells[s][0] if k.startswith("is-")] for s in STAGES]
        assert got == [[x] for x in want], (st, got)
    names = [plain(strip_cells(c.get("/?run=" + ids["running"]).text)[s][1]) for s in STAGES]
    assert names == ["送出", "執行中", "結果", "下游", "完成"]
    # TC-L12: choosing a stage never changes the classes; only the chosen cell has aria-current
    cells = strip_cells(c.get("/?run=%s&stage=results" % ids["running"]).text)
    assert [[k for k in cells[s][0] if k.startswith("is-")] for s in STAGES] == [[x] for x in expect["running"]]
    assert [s for s in STAGES if 'aria-current="step"' in cells[s][1]] == ["results"]
    # TC-L13: with no stage chosen, the run's own stage is the current step
    for st, own in (("succeeded", "results"), ("failed", "running")):
        cells = strip_cells(c.get("/?run=" + ids[st]).text)
        assert [s for s in STAGES if 'aria-current="step"' in cells[s][1]] == [own]


def test_tcl14_l15_l16_middle(w):
    # TC-L14, TC-L15, TC-L16
    ann = w.user("ann")
    f = seed(w, "bad-one", "failed", ann, counts=dict(succeeded=11, cached=12, failed=13, aborted=14, running=15, pending=16, submitted=17))
    c = login(w, "ann")
    mid = pane(c.get("/?run=" + f).text, "middle")
    head = re.search(r'<[^>]*class="[^"]*\bstate-failed\b[^"]*"[^>]*>[^<]*</', mid)
    assert head and "✗" in head.group(0) and "失敗" in head.group(0) and mid.index("bad-one") < mid.index(head.group(0))
    cells = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", mid, re.S)
    assert cells == [("成功", "11"), ("快取", "12"), ("失敗", "13"), ("中止", "14"), ("執行中", "15"), ("等待", "16"), ("已送出", "17")]
    run = pane(c.get("/?run=%s&stage=running" % f).text, "middle")
    prev = re.search(r'<a\b[^>]*rel="prev"[^>]*>(.*?)</a>', run, re.S)
    nxt = re.search(r'<a\b[^>]*rel="next"[^>]*>(.*?)</a>', run, re.S)
    assert prev.group(1) == "← 上一階段" and nxt.group(1) == "下一階段 →"
    assert "stage=launch" in prev.group(0) and "run=" + f in prev.group(0)
    assert "stage=results" in nxt.group(0) and "run=" + f in nxt.group(0)


def test_tch22_l19_l20_groups_and_counts(w):
    # TC-H22b, TC-L19, TC-L20 (replace TC-H22a)
    ann = w.user("ann")
    for i in range(2):
        seed(w, "r%d" % i, "running", ann)
    seed(w, "l1", "lost", ann)
    seed(w, "f1", "failed", ann)
    for i in range(3):
        seed(w, "s%d" % i, "succeeded", ann)
    t = login(w, "ann").get("/").text
    right = pane(t, "right")
    assert re.findall(r'data-stage="([a-z]+)"', right) == ["running", "results", "later"]
    assert plain(group_head(t, "running")) == "執行中（4）" and plain(group_head(t, "results")) == "結果（3）"
    later = re.search(r'data-stage="later"[^>]*>(.*?)</section>', right, re.S).group(1)
    assert "之後開放" in later and "<a " not in later and "<h3" not in later
    for gone in ("送出（", "下游（", "完成（"):
        assert gone not in right
    names = lambda stage: sorted(re.search(r"\b([rlfs]\d)\b", plain(x)).group(1) for x in items(t, stage))
    assert names("running") == ["f1", "l1", "r0", "r1"] and names("results") == ["s0", "s1", "s2"]

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


def test_tch08_l21_states_readable_without_colour(w):
    # TC-H08a, TC-H08b, TC-H08c, TC-H08d, TC-H08e, TC-L21
    ann = w.user("ann")
    for name, st in (("a", "running"), ("b", "succeeded"), ("c", "failed"), ("d", "lost")):
        seed(w, name, st, ann)
    t = login(w, "ann").get("/").text
    its = items(t)
    assert len(its) == 4
    classes = {}
    for label, symbol, st in (("執行中", "▶", "running"), ("成功", "✓", "succeeded"), ("失敗", "✗", "failed"), ("失聯/暫停", "⏸", "lost")):
        hit = [x for x in its if re.search(r'class="[^"]*\bstate-%s\b' % st, x)]
        assert len(hit) == 1 and symbol + " " + label in plain(hit[0]) and 'href="/?run=id-' in hit[0], (st, label)
        classes[st] = re.search(r'class="([^"]*)"', hit[0]).group(1)
    assert len(set(classes.values())) == 4

def test_tch08_progress(w):
    # TC-H08f, TC-H08g
    ann = w.user("ann")
    a = seed(w, "p1", "running", ann, counts=dict(succeeded=6, cached=2, running=2))
    z = seed(w, "p0", "running", ann)
    c = login(w, "ann")
    tag = re.search(r"<progress[^>]*>", c.get("/?run=" + a).text).group(0)
    assert 'value="8"' in tag and 'max="10"' in tag
    assert "value" not in re.search(r"<progress[^>]*>", c.get("/?run=" + z).text).group(0)


def test_tch10_stage_param(w):
    # TC-H10a, TC-H10b, TC-H10c, TC-H10d, TC-H10e
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


def test_tch14_refresh_only_on_root(w):
    # TC-H14a, TC-H14b
    w.user("ann")
    c = login(w, "ann")
    assert '<meta http-equiv="refresh" content="15">' in c.get("/").text
    for p in (w.web().get("/login").text, c.get("/c/" + "b" * 32).text, c.get("/?run=nope").text):
        assert "http-equiv" not in p


def test_tch18_empty_states(w):
    # TC-H18a, TC-H18b, TC-H18c
    w.user("ann")
    c = login(w, "ann")
    r = c.get("/")
    assert r.status_code == 200 and "還沒有" in r.text                 # no index.db at all
    Path(w.ip.index).write_bytes(b"")
    r = c.get("/")
    assert r.status_code == 200 and "還沒有" in r.text                 # an empty file
    Path(w.ip.index).unlink()
    from abf_platform import store
    store.init_index(w.ip.index)
    assert "還沒有" in c.get("/").text                                 # an index with no run


def test_tch19_long_lists(w):
    # TC-H19a, TC-H19b
    ann = w.user("ann")
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    con2 = store.connect_state(w.ip.state_db)
    now = time.time()
    with con, con2:
        for i in range(250):
            con.execute("INSERT INTO runs (id, session_id, run_name, final_status, started_at, ended_at, last_message_at) VALUES (?,?,?,?,?,?,?)",
                        ("i%03d" % i, "s", "run%03d" % i, "succeeded", int(now) - i, int(now), now))
            con2.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)",
                         ("run%03d" % i, "/f", "lab-a", "ag", now, ann.user_id))
    con.close()
    con2.close()
    t = login(w, "ann").get("/").text
    left, right = pane(t, "left"), pane(t, "right")
    assert len(re.findall(r"run\d{3}", left)) == 100 and "還有 150 筆" in left
    assert len(re.findall(r"run\d{3}", right)) == 100 and "還有 150 筆" in right
    assert "250" in group_head(t, "results")


# ---- cost ----------------------------------------------------------------------------------------------------------------------

def test_tch09_cost(w):
    from abf_platform import web_board
    # TC-H09c, TC-L17, TC-L18, TC-N03 (replace TC-H09a, TC-H09b)
    ann = w.user("ann")
    seed(w, "x", "running", ann, counts=dict(succeeded=500, running=40))
    t = login(w, "ann").get("/").text
    right = pane(t, "right")
    box = re.search(r'data-cost="month"[^>]*>(.*?)</(?:p|div)>', right, re.S).group(1)
    assert plain(box) == "本月 SU — · 雲端 —" and "<a " not in box
    assert right.index('data-cost="month"') < right.index('data-stage="')       # before any group
    assert "本月費用" not in t and "NCHC" not in t and "NCHC" not in Path(web_board.__file__).read_text(encoding="utf-8")


# ---- who sees what ---------------------------------------------------------------------------------------------------------------

def test_tch03_only_own_runs(w):
    # TC-H03a, TC-H03b
    ann, bob = w.user("ann"), w.user("bob")
    seed(w, "ann-run", "running", ann)
    for i in range(5):
        seed(w, "bob-secret-%d" % i, "failed", bob)
    t = login(w, "ann").get("/").text
    assert "bob-secret" not in t and "ann-run" in t
    head = group_head(t, "running")
    assert "1" in head and "5" not in head and "6" not in head


def test_tch04_hidden_submitter(w):
    # TC-H04a, TC-H04b, TC-H04c
    from abf_platform import actions
    w.user("ann")
    w.user("bob")
    seed(w, "orphan-nolaunch", "running", launch_row=False)
    seed(w, "orphan-nulluser", "running", None)
    for who in ("ann", "bob"):
        assert "orphan-" not in login(w, who).get("/").text
    names = {r["name"] for r in actions.list_runs(w.ip.index, caller=None, platform_path=w.ip.state_db)["runs"]}
    assert {"orphan-nolaunch", "orphan-nulluser"} <= names


def test_tch05_not_mine_looks_missing(w):
    # TC-H05a, TC-H05b, TC-H05c, TC-H05d
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


def test_tch15_bearer_is_not_a_login(w):
    # TC-H15
    from abf_platform import store
    ann = w.user("ann")
    tok = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id)
    r = w.web().get("/", headers={"Authorization": "Bearer %s" % tok})
    assert r.status_code == 303 and r.headers["location"] == "/login"


# ---- read-only ------------------------------------------------------------------------------------------------------------------

def test_tch11_read_only(w):
    # TC-H11a, TC-H11b, TC-H11c, TC-H11d, TC-N01, TC-N06
    ann = w.user("ann")
    rid = seed(w, "ok", "failed", ann, reason="boom")
    c = login(w, "ann")
    for url in ("/", "/?run=" + rid):
        t = c.get(url).text
        forms = re.findall(r"<form\b[^>]*>", t)
        assert len(forms) == 1 and 'action="/logout"' in forms[0]
        assert t.count("<button") == 1
        assert re.search(r'name="csrf" value="[^"]+"', t)
    assert c.post("/").status_code == 405
    routes = sorted((r.path, tuple(sorted(r.methods))) for r in c.app.routes)
    # 009i: the OAuth routes and the consent page are the only additions to the six of 011a; none of them is a board or a run page
    assert routes == [("/", ("GET", "HEAD")), ("/.well-known/oauth-authorization-server", ("GET", "HEAD", "OPTIONS")),
                      ("/authorize", ("GET", "HEAD", "POST")), ("/c/{rid}", ("GET", "HEAD")), ("/c/{rid}", ("POST",)),
                      ("/consent/{rid}", ("GET", "HEAD")), ("/consent/{rid}", ("POST",)), ("/login", ("GET", "HEAD")),
                      ("/login", ("POST",)), ("/logout", ("POST",)), ("/register", ("OPTIONS", "POST")),
                      ("/revoke", ("OPTIONS", "POST")), ("/token", ("OPTIONS", "POST"))], routes


def _digest(w):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(w.ip.state_db).parent.rglob("*")) if p.is_file()}


def test_tch11e_k1_a_get_writes_nothing(w):
    # TC-H11e, TC-K1
    ann = w.user("ann")
    rid = seed(w, "ok", "running", ann)
    c = login(w, "ann")
    before, counts = _digest(w), w.counts()
    for _ in range(2):
        for url in ("/", "/?run=" + rid, "/?stage=running", "/?run=zzz"):
            c.get(url)
    assert _digest(w) == before and w.counts() == counts


def test_tch12_escaping(w):
    # TC-H12a, TC-H12b, TC-H12c
    ann = w.user("ann")
    nasty = '<script>alert(1)</script>"><b>'
    seed(w, nasty, "running", ann, run_id='x"y\'z<q>')
    fid = seed(w, "f", "failed", ann, reason="<img src=x onerror=1>")
    c = login(w, "ann")
    t = c.get("/").text
    assert "<script>" not in t and "<b>" not in t and "&lt;script&gt;" in t
    assert 'href="/?run=x"y' not in t
    for h in hrefs(t):
        assert "<" not in h and '"' not in h
    f = c.get("/?run=" + fid).text
    assert "<img" not in f and "&lt;img" in f


def test_tch13_csp_and_markup(w):
    # TC-H13a, TC-H13b, TC-H13c, TC-H13d, TC-H13e, TC-H13f, TC-H13g, TC-H13h, TC-H13i
    ann = w.user("ann")
    rid = seed(w, "ok", "running", ann, counts=dict(succeeded=1, running=1))
    c = login(w, "ann")
    pages = [c.get("/"), c.get("/?run=" + rid), w.web().get("/login"), c.get("/c/" + "b" * 32), c.get("/?run=nope")]
    for r in pages:
        csp = r.headers["content-security-policy"]
        assert "script-src" not in csp and "'unsafe-inline'" not in csp
        for keep in ("default-src 'none'", "form-action 'self'", "frame-ancestors 'none'", "base-uri 'none'"):
            assert keep in csp
        style = re.search(r"<style>(.*?)</style>", r.text, re.S).group(1)
        digest = base64.b64encode(hashlib.sha256(style.encode("utf-8")).digest()).decode()
        assert "style-src 'sha256-%s'" % digest in csp, r.url
    for r in pages[:2]:
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


# ---- not in this PR ---------------------------------------------------------------------------------------------------------------

def test_tn02_no_detail_logs_or_resume(w):
    # TC-N02
    ann = w.user("ann")
    rid = seed(w, "bad", "failed", ann, reason="boom")
    c = login(w, "ann")
    t = c.get("/?run=" + rid).text
    assert not re.search(r"(?i)resume|restart|/logs|\blogs?\b", t) and "boom" in t
    for p in ("/runs/" + rid, "/runs/%s/logs" % rid, "/resume", "/restart"):
        assert c.get(p).status_code == 404 and c.post(p).status_code in (404, 405), p


def test_tn04_other_paths_stay_missing(w):
    # TC-N04
    w.user("ann")
    c = login(w, "ann")
    for path in ("/runs", "/ce", "/compute-envs", "/oauth/token", "/oauth/authorize", "/admin", "/launch", "/submit", "/upload",
                 "/password", "/passwd", "/settings", "/api/launch"):
        assert c.get(path).status_code == 404, path
        assert c.post(path, data={"a": "b"}).status_code in (404, 405), path


def test_tn05_no_new_tool_or_action(w):
    # TC-N05
    from abf_platform import actions
    tools, _ = w.mcp([])
    assert sorted(t.name for t in tools) == sorted(["list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents",
                                                    "list_site_files", "launch", "cancel"])
    assert not [n for n in dir(actions) if "board" in n]


# ---- layout B: top bar, columns, history items, language (plan section "Layout redo", L1 to L9, B1 to B6, C1 to C6) ------------------

def bulk(w, owner, n, status, prefix, reason="boom"):
    """n runs of one user in one go (newest first: run<prefix>000 is the newest); returns the time the newest one started."""
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


def test_tcl01_top_bar(w):
    # TC-L01
    w.user("ann")
    t = login(w, "ann").get("/").text
    top = t[:t.index('data-pane="left"')]
    assert 'class="mast"' in top and "agentic-bioflow" in top and "ann" in top
    assert re.search(r'<a\b[^>]*>中</a>', top) and re.search(r'<a\b[^>]*>EN</a>', top)
    assert top.index("agentic-bioflow") < top.index("ann")


def test_tcl03_l04_stylesheet(w):
    # TC-L03, TC-L04
    from abf_platform import web_board
    css = web_board.STYLE
    assert re.search(r"grid-template-columns:\s*232px\s+1fr\s+272px", css)
    assert re.search(r"@media\s*\(max-width:\s*900px\)", css)
    order = css[css.index("@media (max-width:900px)"):]
    assert re.search(r"\.main\{[^}]*order:-2", order) and re.search(r"\.hist\{[^}]*order:-1", order)      # middle, right, left


def test_tcl22_l23_l27_items(w):
    # TC-L21, TC-L22, TC-L23, TC-L27
    ann = w.user("ann")
    now = time.time()
    seed(w, "first", "running", ann, started=now - 3000, counts=dict(succeeded=6, cached=2, running=2))
    seed(w, "second", "lost", ann, started=now - 2000)
    seed(w, "third", "running", ann, started=now - 1000)
    t = login(w, "ann").get("/").text
    its = [plain(x) for x in items(t, "running")]
    assert [x.split()[0] for x in its] == ["3", "2", "1"]
    assert [x.split()[1] for x in its] == ["third", "second", "first"]
    assert its[2].endswith("▶ 執行中 · 8/10") and its[1].endswith("⏸ 失聯/暫停 · —")


def test_tcl24_succeeded_key_fact_is_the_end_time(w):
    # TC-L24
    ann = w.user("ann")
    rid = seed(w, "fin", "succeeded", ann, started=1_700_000_000)
    c = login(w, "ann")
    item = plain(items(c.get("/").text, "results")[0])
    assert item.endswith("✓ 成功 · 2023-11-14T22:15:00Z")
    assert "2023-11-14T22:15:00Z" in plain(pane(c.get("/?run=" + rid).text, "middle"))


def test_tcl25_l26_failed_key_fact(w):
    # TC-L25, TC-L26
    ann = w.user("ann")
    seed(w, "long", "failed", ann, reason="A" * 80 + "B" * 40 + "\nSECONDLINE")
    seed(w, "short", "failed", ann, reason="short reason\nmore")
    seed(w, "none", "failed", ann, reason=None)
    seed(w, "empty", "failed", ann, reason="")
    its = {re.search(r"\d+ (long|short|none|empty) ", plain(x)).group(1): plain(x) for x in items(login(w, "ann").get("/").text, "running")}
    assert its["long"].endswith("✗ 失敗 · " + "A" * 80) and "B" not in its["long"] and "SECONDLINE" not in its["long"]
    assert its["short"].endswith("✗ 失敗 · short reason")
    assert its["none"].endswith("✗ 失敗 · 原因未記錄") and its["empty"].endswith("✗ 失敗 · 原因未記錄")


def test_tcl28_selected_item(w):
    # TC-L28
    from abf_platform import web_board
    ann = w.user("ann")
    now = time.time()
    ids = [seed(w, n, "running", ann, started=now - k) for k, n in ((300, "one"), (200, "two"), (100, "three"))]
    c = login(w, "ann")
    t = c.get("/?run=" + ids[1]).text
    marked = [x for x in items(t) if re.search(r'class="[^"]*\bhere\b', x)]
    assert len(marked) == 1 and "two" in marked[0]
    assert [x for x in items(c.get("/").text) if re.search(r'class="[^"]*\bhere\b', x)] == []
    assert re.search(r"\.item\.here\{[^}]*outline", web_board.STYLE)


def test_tcl29_failed_items_ask_get_run_at_most_100_times(w, monkeypatch):
    # TC-L29
    from abf_platform import actions
    ann = w.user("ann")
    bulk(w, ann, 250, "failed", "bad")
    real, calls = actions.get_run, []

    def spy(*a, **kw):
        calls.append(kw)
        return real(*a, **kw)
    monkeypatch.setattr(actions, "get_run", spy)
    t = login(w, "ann").get("/").text
    assert len(items(t, "running")) == 100 and "還有 150 筆" in pane(t, "right")
    assert 0 < len(calls) <= 100
    assert all(k.get("caller") is not None and k["caller"].user_id == ann.user_id for k in calls)
    assert "boom" in items(t, "running")[0]


def test_tcl30_numbers_count_all_runs(w):
    # TC-L30
    ann = w.user("ann")
    bulk(w, ann, 250, "succeeded", "ok")
    t = login(w, "ann").get("/").text
    its = items(t, "results")
    assert plain(group_head(t, "results")) == "結果（250）" and len(its) == 100
    assert plain(its[0]).split()[0] == "250" and plain(its[99]).split()[0] == "151"


def test_tch12d_item_fact_is_escaped(w):
    # TC-H12d
    ann = w.user("ann")
    seed(w, "f", "failed", ann, reason="<img src=x onerror=1>\nrest")
    t = login(w, "ann").get("/").text
    assert "<img" not in t and "&lt;img src=x onerror=1&gt;" in items(t, "running")[0]


# ---- language ---------------------------------------------------------------------------------------------------------------------

def seed_three(w, ann):
    return {st: seed(w, "n-" + st, st, ann, counts=dict(succeeded=1, cached=2, failed=3, aborted=4, running=5, pending=6, submitted=7),
                     reason="boom" if st == "failed" else None) for st in ("running", "failed", "succeeded")}


def test_tcl31_default_is_chinese(w):
    # TC-L31
    ann = w.user("ann")
    ids = seed_three(w, ann)
    t = login(w, "ann").get("/?run=" + ids["running"]).text
    assert "執行中" in t and "之後開放" in t and "登出" in t and 'lang="zh-Hant"' in t
    for word in ("Cached", "Aborted", "Pending", "Submitted"):
        assert word not in t


def test_tcl32_l33_english(w):
    # TC-L32, TC-L33
    ann = w.user("ann")
    ids = seed_three(w, ann)
    c = login(w, "ann")
    for st in ids:
        t = c.get("/?run=%s&lang=en" % ids[st]).text
        assert cjk(re.sub(r">中<", "><", t)) == [], (st, cjk(t))
        assert 'lang="en"' in t
    mid = pane(c.get("/?run=%s&lang=en" % ids["running"]).text, "middle")
    cells = [(a.lower(), b) for a, b in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", mid, re.S)]
    assert cells == [("succeeded", "1"), ("cached", "2"), ("failed", "3"), ("aborted", "4"), ("running", "5"), ("pending", "6"),
                     ("submitted", "7")]


def test_tcl34_english_reason_not_recorded(w):
    # TC-L34
    ann = w.user("ann")
    seed(w, "nr", "failed", ann, reason=None)
    t = login(w, "ann").get("/?lang=en").text
    assert plain(items(t, "running")[0]).endswith("reason not recorded")


def test_tcl35_l36_l37_switch_and_links(w):
    # TC-L35, TC-L36, TC-L37
    from urllib.parse import parse_qs, urlsplit
    import html as htmllib
    ann = w.user("ann")
    rid = seed(w, "r", "running", ann)
    seed(w, "s", "succeeded", ann)
    c = login(w, "ann")
    t = c.get("/?run=%s&stage=results" % rid).text
    en = htmllib.unescape(re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>EN</a>', t).group(1))
    zh = htmllib.unescape(re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>中</a>', t).group(1))
    assert urlsplit(en).path == "/" and parse_qs(urlsplit(en).query) == {"run": [rid], "stage": ["results"], "lang": ["en"]}
    assert urlsplit(zh).path == "/" and parse_qs(urlsplit(zh).query) == {"run": [rid], "stage": ["results"]}
    assert not re.search(r"<form\b[^>]*>[^<]*(中|EN)", t)
    # TC-L36: English page: every board link keeps lang=en; the only one that drops it is the 中 link
    t = c.get("/?run=%s&stage=running&lang=en" % rid).text
    others = [htmllib.unescape(h) for h in hrefs(t)]
    zh_en = htmllib.unescape(re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>中</a>', t).group(1))
    others.remove(zh_en)
    assert len(others) >= 8 and all("lang=en" in h for h in others), [h for h in others if "lang=en" not in h]
    # TC-L37: Chinese page: no link carries lang=en except the EN link
    t = c.get("/?run=%s&stage=running" % rid).text
    en_link = htmllib.unescape(re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>EN</a>', t).group(1))
    rest = [htmllib.unescape(h) for h in hrefs(t)]
    rest.remove(en_link)
    assert len(rest) >= 8 and not [h for h in rest if "lang=" in h]


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
    assert missing.status_code == 404 and other.status_code == 404
    assert cjk(re.sub(r">中<", "><", missing.text)) == []
    assert missing.content.replace(b"nope-xyz-4471", b"") == missing.content and "nope-xyz-4471" not in missing.text
    assert other.content == c.get("/?run=another-missing&lang=en").content


def test_tcl41_odd_lang_values(w):
    # TC-L41
    w.user("ann")
    c = login(w, "ann")
    for v in ("fr", "", "<script>", "EN", "en,zh"):
        r = c.get("/", params={"lang": v})
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
    assert r.status_code == 200 and cjk(re.sub(r">中<", "><", r.text)) == [] and "No runs yet" in r.text


def test_tcl44_no_external_url_script_or_style_attribute(w):
    # TC-L44
    ann = w.user("ann")
    ids = seed_three(w, ann)
    c = login(w, "ann")
    w.user("bob")  # no runs: the empty-state page
    empty = login(w, "bob")
    urls = ["/", "/?run=" + ids["running"], "/?run=%s&stage=running" % ids["running"], "/?run=nope"]
    urls += [u + ("&" if "?" in u else "?") + "lang=en" for u in urls]
    pages = [(u, c.get(u).text) for u in urls]
    pages += [("empty " + u, empty.get(u).text) for u in ("/", "/?lang=en", "/?run=nope")]
    assert "No runs yet" in empty.get("/?lang=en").text
    for u, t in pages:
        assert not re.search(r"https?://", t) and not re.search(r'(?:href|src|action)="(?:https?:)?//', t), u
        assert "<script" not in t.lower() and not re.search(r"\sstyle=", t) and not re.search(r"\son[a-z]+=", t, re.I), u


# ---- not in this PR (layout B) ---------------------------------------------------------------------------------------------------

def test_tn08_login_and_confirm_pages_stay_chinese(w):
    # TC-N08
    w.user("ann")
    c = login(w, "ann")
    assert w.web().get("/login?lang=en").text == w.web().get("/login").text
    assert c.get("/c/%s?lang=en" % ("b" * 32)).text == c.get("/c/%s" % ("b" * 32)).text


def test_tn09_language_is_not_remembered(w):
    # TC-N09
    ann = w.user("ann")
    seed(w, "r", "running", ann)
    c = login(w, "ann")
    r = c.get("/?lang=en")
    assert "set-cookie" not in r.headers and 'lang="en"' in r.text
    assert 'lang="zh-Hant"' in c.get("/").text


def test_tn10_n11_nothing_beyond_the_plan(w):
    # TC-N10, TC-N11
    from urllib.parse import parse_qs, urlsplit
    import html as htmllib
    ann = w.user("ann")
    rid = seed(w, "r", "running", ann)
    c = login(w, "ann")
    for url in ("/", "/?run=" + rid):
        t = c.get(url).text
        assert "<textarea" not in t and "<details" not in t and 'type="radio"' not in t
        assert [m for m in re.findall(r"<input\b[^>]*>", t) if 'type="hidden"' not in m or 'name="csrf"' not in m] == []
        for h in hrefs(t):
            u = urlsplit(htmllib.unescape(h))
            assert u.path == "/" and set(parse_qs(u.query)) <= {"run", "stage", "lang"}, h
        left = pane(t, "left")
        assert not re.search(r"project|analys|專案|分析", " ".join(hrefs(left)), re.I)
