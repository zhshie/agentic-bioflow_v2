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


def group_head(text, stage):
    """The heading text of the right-hand group of one stage."""
    return re.search(r'data-stage="%s"[^>]*>.*?<h3[^>]*>(.*?)</h3>' % stage, text.split("本月費用")[1], re.S).group(1)


# ---- login and the shell --------------------------------------------------------------------------------------------------------

def test_tch01a_no_cookie_goes_to_login(w):
    # TC-H01a
    seed(w, "secret-run", owner=w.user("zed"))
    r = w.web().get("/")
    assert r.status_code == 303 and r.headers["location"] == "/login" and "secret-run" not in r.text


def test_tch01b_h20_h21a_three_panes(w):
    # TC-H01b, TC-H20b, TC-H20c, TC-H20d, TC-H21a
    w.user("ann")
    r = login(w, "ann").get("/")
    assert r.status_code == 200
    for needle in ("我的 run", "選一個 run", "本月費用", "專案與分析（011b）尚未開放", "設定（尚未開放）", "ann"):
        assert needle in r.text, needle
    assert not [h for h in hrefs(r.text) if "settings" in h]


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
    left = login(w, "ann").get("/").text.split("本月費用")[0]
    assert left.index("new-one") < left.index("mid-one") < left.index("old-one")


def test_tch21_stage_strip_and_bodies(w):
    # TC-H21b, TC-H21c, TC-H21d, TC-H21e, TC-H21f, TC-H21g
    ann = w.user("ann")
    rid = seed(w, "run-a", "running", ann, started=1_700_000_000, counts=dict(succeeded=3, running=2, pending=1))
    fid = seed(w, "run-f", "failed", ann, reason="Process terminated with an error exit status (137)")
    c = login(w, "ann")
    t = c.get("/?run=" + rid).text
    order = [t.index("stage=" + s) for s in STAGES]
    assert order == sorted(order)
    assert t.count("→") >= 1
    for needle in ("執行中", "2023-11-14"):
        assert needle in t
    for label in ("succeeded", "running", "pending"):
        assert label in t
    assert "Process terminated with an error exit status (137)" in c.get("/?run=" + fid).text
    for stage, feature in (("launch", "012b"), ("downstream", "016"), ("finished", "013b")):
        body = c.get("/?run=%s&stage=%s" % (rid, stage)).text
        assert "—" in body and feature in body, stage


def test_tch22_groups_and_counts(w):
    # TC-H22a, TC-H22b
    ann = w.user("ann")
    for i in range(2):
        seed(w, "r%d" % i, "running", ann)
    seed(w, "l1", "lost", ann)
    seed(w, "f1", "failed", ann)
    for i in range(3):
        seed(w, "s%d" % i, "succeeded", ann)
    t = login(w, "ann").get("/").text
    right = t.split("本月費用")[1]
    pos = [right.index('data-stage="%s"' % s) for s in STAGES]
    assert pos == sorted(pos)
    assert "4" in group_head(t, "running") and "3" in group_head(t, "results")
    assert "3" not in group_head(t, "running")


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


def test_tch08_states_readable_without_colour(w):
    # TC-H08a, TC-H08b, TC-H08c, TC-H08d, TC-H08e
    ann = w.user("ann")
    for name, st in (("a", "running"), ("b", "succeeded"), ("c", "failed"), ("d", "lost")):
        seed(w, name, st, ann)
    t = login(w, "ann").get("/").text
    classes = {}
    for label, st in (("執行中", "running"), ("成功", "succeeded"), ("失敗", "failed"), ("失聯/暫停", "lost")):
        m = re.search(r'class="([^"]*\bstate-%s\b[^"]*)"[^>]*>[^<]*%s' % (st, re.escape(label)), t)
        assert m, (st, label)
        classes[st] = m.group(1)
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
    left, right = t.split("本月費用")
    assert len(re.findall(r"run\d{3}", left)) == 100 and "還有 150 筆" in left
    assert len(re.findall(r"run\d{3}", right)) == 100 and "還有 150 筆" in right
    assert "250" in group_head(t, "results")


# ---- cost ----------------------------------------------------------------------------------------------------------------------

def test_tch09_cost(w):
    # TC-H09a, TC-H09b, TC-H09c, TC-N03
    ann = w.user("ann")
    seed(w, "x", "running", ann, counts=dict(succeeded=500, running=40))
    t = login(w, "ann").get("/").text
    right = t.split("本月費用")[1]
    assert right.index("NCHC SU —") < right.index('data-stage="launch"')
    assert right.index("雲端 —") < right.index('data-stage="launch"')
    box = re.search(r'data-cost="month"[^>]*>(.*?)</div>', t, re.S).group(1)
    assert not re.search(r"\d", box) and "<a " not in box
    assert box.count("<p") == 2 or box.count("<li") == 2       # two separate lines


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
    assert routes == [("/", ("GET", "HEAD")), ("/c/{rid}", ("GET", "HEAD")), ("/c/{rid}", ("POST",)), ("/login", ("GET", "HEAD")),
                      ("/login", ("POST",)), ("/logout", ("POST",))], routes


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
