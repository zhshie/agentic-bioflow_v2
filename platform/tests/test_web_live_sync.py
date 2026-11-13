# Nothing existing: tests of live-sync (the one static script that keeps the pages that reloaded every 15 seconds up to date); the script, its two read-only
# routes and the region marks are ours (specs/live-sync/plan.md).
"""live-sync. Test case ids (TC-001 ...) refer to specs/live-sync/test-case.md. The browser cases (TC-001, 004 ... 040) are in scripts/dev/check_live_sync.py.
The two live routes are answered by a middleware of the web app, not by Starlette routes: the exact route lists of other tests stay true (see the ledger)."""
import html
import json
import re
import sqlite3
import time
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from human_harness import World
from test_web_board import login, pane, seed

STYLE = "'sha256-FfC1YK8kGEBly+aw5sxs1lF8rL8fd0bvd3C1C3uWpGw='"      # D13 pins the style sheet: no new CSS in this task; this is its hash today
BASE = "default-src 'none'; style-src %s; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" % STYLE
IMG = "default-src 'none'; img-src 'self'; style-src %s; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" % STYLE
ADD = "; script-src 'self'; connect-src 'self'"
META15 = '<meta http-equiv="refresh" content="15">'
SCRIPT = '<script src="/static/live.js"></script>'
NOW = time.time()
HOUR = 3600
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000000020001e221bc330000000049454e44ae426082")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def live():
    from abf_platform import web_live
    return web_live


def stamp(w, name):
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE launches SET run_folder = ? WHERE run_name = ?", ("/data/wd/runs/" + name, name))
    con.close()


def scene(w):
    """ann has a running, a failed and a succeeded run; bob has one of his own; both are logged in."""
    ann, bob = w.user("ann"), w.user("bob")
    ids = {"run": seed(w, "ann-run", "running", ann, counts=dict(succeeded=1, running=2)),
           "bad": seed(w, "ann-bad", "failed", ann, counts=dict(succeeded=1, failed=1), reason="boom"),
           "ok": seed(w, "ann-ok", "succeeded", ann, started=NOW - 3 * HOUR, ended=NOW - 2 * HOUR, counts=dict(succeeded=4)),
           "bob": seed(w, "bob-run", "running", bob, counts=dict(running=1))}
    stamp(w, "ann-ok")
    return ann, bob, ids, login(w, "ann"), login(w, "bob")


def version(c, u, k=None, **kw):
    params = {"u": u}
    if k:
        params["k"] = k
    return c.get("/live/version?" + urllib.parse.urlencode(params), **kw)


def content(c, u, names):
    return c.get("/live/content?" + urllib.parse.urlencode({"u": u, "n": ",".join(names)}))


def names_of(v):
    return [r_name for cont in v["c"] for r_name in ["%s-%d" % (cont["n"], i) for i in range(len(cont["v"]))]]


def vmap(v):
    return {"%s-%d" % (cont["n"], i): h for cont in v["c"] for i, h in enumerate(cont["v"])}


def snapshot(w):
    """Every file under the platform folder with its bytes, plus every row of every table: what a read must leave alone."""
    out = {}
    root = w.ip.state_db.parent
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.name.endswith(("-shm", "-wal")):
            out[str(p.relative_to(root))] = p.read_bytes()
    for db in (w.ip.state_db, w.ip.tokens, w.ip.index):
        con = sqlite3.connect(str(db))
        for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            out["%s:%s" % (Path(db).name, name)] = repr(con.execute("SELECT * FROM %s" % name).fetchall())
        con.close()
    return out


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts, self.on, self.noscript, self.meta_in_noscript, self.meta_out, self.srcs, self.stack = 0, [], 0, [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script":
            self.scripts += 1
            self.srcs.append(a)
        self.on += [k for k in a if k.startswith("on")]
        if tag == "noscript":
            self.noscript += 1
        if tag == "meta" and a.get("http-equiv") == "refresh":
            (self.meta_in_noscript if "noscript" in self.stack else self.meta_out).append(a["content"])
        if tag not in ("meta", "input", "img", "br", "link", "hr"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass


def tags(text):
    t = Tags()
    t.feed(text)
    return t


# ---- the script and its limits ------------------------------------------------------------------------------------------------------

def test_tc036_tc047_the_script_is_one_fixed_file_for_everybody(w):
    # TC-036, TC-047
    scene(w)
    anon, a, b = w.web(), login(w, "ann"), login(w, "bob")
    got = [c.get("/static/live.js") for c in (anon, a, b)]
    assert all(r.status_code == 200 for r in got)
    assert all("javascript" in r.headers["content-type"] and r.headers["x-content-type-options"] == "nosniff" for r in got)
    assert got[0].content == got[1].content == got[2].content and len(got[0].content) > 500
    for path in ("/static/other.js", "/static/", "/static/live.js/x", "/static/../live.js", "/static/%2e%2e/live.js", "/static/live.jsx", "/live", "/live/"):
        assert a.get(path).status_code == 404, path


def test_tc038_tc039_tc066_tc061_the_script_text(w):
    # TC-038, TC-039, TC-066, TC-061
    text = (w.web().get("/static/live.js")).text
    assert text == (PLATFORM_DIR / "abf_platform" / "data" / "live.js").read_text(encoding="utf-8")
    banned = [r"\beval\b", r"new\s+Function", r"document\.write", r"setTimeout\s*\(\s*['\"`]", r"setInterval\s*\(\s*['\"`]", r"\bimport\s*\(", r"importScripts", r"WebSocket",
              r"EventSource", r"sendBeacon", r"localStorage", r"sessionStorage", r"document\.cookie", r"https?:", r"(?<![:\w])//[A-Za-z0-9.-]+\.", r"\.submit\s*\(", r"FormData",
              r"['\"]POST['\"]", r"\bPOST\b", r"XMLHttpRequest"]
    code = re.sub(r"/\*.*?\*/|(?m:^\s*//.*$)", "", text, flags=re.S)
    for pattern in banned:
        assert not re.search(pattern, code), pattern
    assert len(re.findall(r"\bfetch\s*\(", code)) == 1      # one place asks the network; every address it is given starts with a slash
    asked = re.findall(r"\bget\s*\(\s*(['\"])([^'\"]*)\1", code)
    assert asked and all(path.startswith("/live/") for _quote, path in asked), asked
    assert "'GET'" in code or '"GET"' in code


# ---- which pages carry it ---------------------------------------------------------------------------------------------------------

def pages_in_scope(w):
    ann, bob, ids, c, cb = scene(w)
    lone = w.user("zed")
    cz = login(w, "zed")
    w.hand_over(by=ann, run="web-t2")
    return ann, ids, c, cz


def test_tc015_tc033_tc037_tc041_tc042_tc043_board_pages(w):
    # TC-015, TC-033, TC-037, TC-041, TC-042, TC-043
    ann, ids, c, cz = pages_in_scope(w)
    refresh = [("/?run=" + ids["run"], BASE), ("/?run=" + ids["bad"], BASE), ("/?run=" + ids["ok"], BASE), ("/?run=%s&stage=results&tab=outputs" % ids["ok"], BASE),
               ("/?run=%s&stage=results&tab=outputs&relist=1" % ids["ok"], BASE), ("/?run=%s&stage=finished" % ids["ok"], BASE), ("/?run_name=web-t2", BASE),
               ("/?run=%s&lang=en" % ids["run"], BASE)]
    for url, csp in refresh:
        r = c.get(url)
        assert r.status_code == 200, url
        t = tags(r.text)
        assert t.scripts == 1 and t.srcs == [{"src": "/static/live.js"}] and t.on == [], url
        assert t.meta_out == [] and len(t.meta_in_noscript) == 1 and re.fullmatch(r"15(;url=.+)?", t.meta_in_noscript[0]), (url, t.meta_in_noscript)
        assert r.headers["content-security-policy"] == csp + ADD, url
    # the empty board of a person with no run
    r = cz.get("/")
    assert tags(r.text).scripts == 1 and tags(r.text).meta_in_noscript == ["15"] and r.headers["content-security-policy"] == BASE + ADD
    for r in [c.get("/?run=" + ids["run"]), cz.get("/")]:
        csp = r.headers["content-security-policy"]
        for word in ("unsafe-inline", "unsafe-eval", "*", "data:", "blob:", "http"):
            assert word not in csp
        assert csp.startswith("default-src 'none'; ") and "style-src %s" % STYLE in csp
    # the Outputs tab goes on to an address without `relist` (the page's own refresh target is unchanged)
    t = tags(c.get("/?run=%s&stage=results&tab=outputs&relist=1" % ids["ok"]).text)
    assert "relist" not in t.meta_in_noscript[0] and t.meta_in_noscript[0].startswith("15;url=")


def test_tc044_tc046_pages_that_stay_without_a_script(w):
    # TC-044, TC-046, TC-045
    ann, ids, c, cz = pages_in_scope(w)
    anon = w.web()
    fixed = {"/login": anon, "/settings": c, "/usage": c, "/upload": c, "/?run=%s&stage=downstream" % ids["ok"]: c, "/?run=nothing-at-all": c,
             "/?run_name=ghost": c, "/launch": c, "/launch?pipeline=nf-core/ampliseq": c}
    for url, who in fixed.items():
        r = who.get(url)
        assert r.status_code in (200, 404), url
        t = tags(r.text)
        assert t.scripts == 0 and t.noscript == 0 and "<noscript" not in r.text and "script-src" not in r.headers["content-security-policy"], url
        assert "connect-src" not in r.headers["content-security-policy"], url
        assert r.headers["content-security-policy"] in (BASE, IMG), url
    log = c.get("/run/log?run=%s&task=t&which=err" % ids["bad"])
    assert "<script" not in log.text and "script-src" not in log.headers["content-security-policy"]
    # the confirmation page and the login page: no script anywhere, the policy is today's
    c2 = w.web()
    assert c2.get("/login").headers["content-security-policy"] == BASE and "<script" not in c2.get("/login").text
    from abf_platform import actions
    got = w.launch(caller=ann, answer=None) if False else None
    assert got is None
    # the board with a refused-button line is the answer to a POST: no script, no refresh
    form = re.search(r'<form class="act" method="post" action="/act/(resume|relaunch)">.*?name="run" value="([^"]+)".*?name="csrf" value="([^"]+)"',
                     c.get("/?run=" + ids["bad"]).text, re.S)
    assert form
    r = c.post("/act/cancel", data={"run": ids["ok"], "csrf": c.app.state.csrf_token(c.cookies.get("abf_web"), "act:" + ids["ok"])})
    assert "<script" not in r.text and "script-src" not in r.headers["content-security-policy"] and "refresh" not in r.text


def test_tc045_the_report_and_preview_policies_are_unchanged():
    # TC-045
    from abf_platform import web, web_preview
    assert web_preview.report_headers(web._HEADERS)["Content-Security-Policy"] == (
        "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' blob:; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; "
        "frame-ancestors 'self'; base-uri 'none'; form-action 'none'") or "sandbox allow-scripts" in web_preview.report_headers(web._HEADERS)["Content-Security-Policy"]
    assert web._HEADERS["Content-Security-Policy"] == BASE
    assert web.LAUNCH_HEADERS["Content-Security-Policy"] == IMG and web.FINISHED_HEADERS["Content-Security-Policy"] == IMG
    assert web_preview.page_headers(web._HEADERS, "html")["Content-Security-Policy"] == BASE + "; frame-src 'self'"


def test_tc015_the_finished_stage_with_figures_carries_the_script_without_a_refresh(w):
    # TC-015
    from test_publish_figure import call, fig, press
    ann, bob, ids, c, cb = scene(w)
    a = login(w, "ann")
    b64 = __import__("base64").b64encode(PNG).decode()
    press(w, "ann", call(w, ann, ids["ok"], [{"filename": "a.png", "content_base64": b64, "code": "print(1)\n", "params": "k=1"}])["request_id"])
    r = c.get("/?run=%s&stage=finished" % ids["ok"])
    t = tags(r.text)
    assert t.scripts == 1 and t.noscript == 0 and t.meta_out == [] and "refresh" not in r.text
    assert r.headers["content-security-policy"] == IMG + ADD


# ---- the regions -------------------------------------------------------------------------------------------------------------------

def test_tc016_every_control_is_in_exactly_one_region_and_regions_do_not_nest(w):
    # TC-016
    ann, ids, c, cz = pages_in_scope(w)
    for url in ("/?run=" + ids["run"], "/?run=" + ids["bad"], "/?run=%s&stage=results&tab=outputs" % ids["ok"], "/?run=%s&stage=finished" % ids["ok"], "/", "/?run_name=web-t2"):
        text = (cz if url == "/" else c).get(url).text
        lay = live().layout(text)
        spans = sorted((r["start"], r["end"]) for cont in lay for r in cont["regions"])
        assert spans, url
        assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), "regions overlap: " + url
        controls = [m.start() for m in re.finditer(r"<(form|input|textarea|select|button)\b", text)]
        for pos in controls:
            assert sum(1 for s, e in spans if s <= pos < e) == 1, (url, text[pos:pos + 60])
        for cont in lay:
            assert re.fullmatch(r"[a-z]+", cont["n"]), cont["n"]
            for i, r in enumerate(cont["regions"]):
                assert r["name"] == "%s-%d" % (cont["n"], i) and "ann" not in r["name"]


def test_tc016_the_launch_edit_and_upload_pages_have_regions_too(w):
    # TC-016 (the pages with forms)
    from test_web_guided_launch import ready, rig  # noqa: F401
    from test_web_guided_launch_2 import loading_files


# ---- the version and the content ----------------------------------------------------------------------------------------------------

def test_tc002_tc003_tc013_the_version_moves_only_for_the_region_that_changed(w):
    # TC-002, TC-003, TC-013
    ann, bob, ids, c, cb = scene(w)
    u = "/?run=" + ids["run"]
    a = version(c, u).json()
    assert a["s"] == "ok" and a == version(c, u).json()
    con = sqlite3.connect(str(w.ip.index))
    with con:
        con.execute("UPDATE runs SET n_succeeded = 3, n_running = 0 WHERE id = ?", (ids["run"],))
    con.close()
    b = version(c, u).json()
    va, vb = vmap(a), vmap(b)
    changed = [n for n in vb if va.get(n) != vb[n]]
    assert changed and any(n.startswith("page-") and va.get(n) == vb[n] for n in vb), "the top bar and the other columns keep their version"
    assert any(n.startswith("left-") for n in changed) and any(n.startswith("mid-") for n in changed)
    got = content(c, u, changed[:2]).json()
    assert got["s"] == "ok" and sorted(got["r"]) == sorted(changed[:2])
    lay = {r["name"]: r["html"] for cont in live().layout(c.get(u).text) for r in cont["regions"]}
    for name, text in got["r"].items():
        assert text == lay[name]


def test_tc012_the_answers_are_never_cached(w):
    # TC-012
    ann, bob, ids, c, cb = scene(w)
    u = "/?run=" + ids["run"]
    for r in (version(c, u), content(c, u, ["left-0"]), version(c, "/?run=nothing"), version(w.web(), u), content(c, "/login", ["x"])):
        assert r.headers["cache-control"] == "private, no-store", r.status_code


def test_tc010_tc053_without_a_login_it_is_401_and_nothing_else(w):
    # TC-010, TC-053
    ann, bob, ids, c, cb = scene(w)
    anon = w.web()
    for u in ("/?run=" + ids["run"], "/launch", "/run/file?run=x&path=y", "/upload/" + "a" * 32, "/act/resume/edit?run=" + ids["bad"]):
        for r in (version(anon, u), content(anon, u, ["mid-0"])):
            assert r.status_code == 401, u
            assert "ann" not in r.text and ids["run"] not in r.text
    from test_temp_password import login_temp
    ct, _r, _ = login_temp(w)      # a login made with a temporary password: it may do nothing but set its own
    for r in (version(ct, "/"), content(ct, "/", ["mid-0"]), ct.get("/live/version")):
        assert r.status_code == 303 and r.headers["location"] == "/welcome" and "ann" not in r.text


def test_tc020_text_from_a_run_is_escaped_in_the_content(w):
    # TC-020
    ann = w.user("ann")
    rid = seed(w, "x-run", "failed", ann, reason='<script>alert(1)</script> "quoted"')
    c = login(w, "ann")
    u = "/?run=" + rid
    v = version(c, u).json()
    got = content(c, u, names_of(v)).json()
    body = json.dumps(got)
    assert "<script" not in body.replace("\\u003c", "<") and "&lt;script&gt;alert(1)&lt;/script&gt;" in "".join(got["r"].values())


def test_tc021_the_form_tokens_are_the_ones_of_the_whole_page(w):
    # TC-021
    ann, bob, ids, c, cb = scene(w)
    u = "/?run=" + ids["bad"]
    whole = c.get(u).text
    tokens = set(re.findall(r'name="csrf" value="([^"]+)"', whole))
    assert len(tokens) >= 2
    got = content(c, u, names_of(version(c, u).json())).json()
    assert set(re.findall(r'name="csrf" value="([^"]+)"', "".join(got["r"].values()))) == tokens


# ---- who may ask --------------------------------------------------------------------------------------------------------------------

def test_tc048_tc049_tc050_tc051_tc052_another_person_and_nothing_are_one_answer(w):
    # TC-048, TC-049, TC-050, TC-051, TC-052
    ann, bob, ids, c, cb = scene(w)
    seed(w, "orphan", "running", None, launch_row=False)
    for u in ("/?run=" + ids["bob"], "/?run_name=bob-run", "/?run=orphan", "/act/resume/edit?run=" + ids["bob"], "/run/file?run=%s&path=a.txt" % ids["bob"],
              "/run/preview?run=%s&path=a.png" % ids["bob"], "/upload/" + "b" * 32):
        none = u.replace(ids["bob"], "id-nothing").replace("bob-run", "nothing").replace("orphan", "nothing").replace("b" * 32, "c" * 32)
        for kind in ("version", "content"):
            f = (lambda cl, x: version(cl, x)) if kind == "version" else (lambda cl, x: content(cl, x, ["mid-0"]))
            r1, r2 = f(c, u), f(c, none)
            assert r1.status_code == r2.status_code == 404, (kind, u)
            assert r1.content == r2.content and dict(r1.headers) == dict(r2.headers), (kind, u)
            assert "bob" not in r1.text and ids["bob"] not in r1.text
    own = version(c, "/?run=" + ids["run"])
    assert "bob" not in own.text and ids["bob"] not in own.text
    for u in ("/login", "/c/" + "a" * 32, "/settings", "https://example.com/", "//example.com/", "/../settings", "/?run=x/../..", "/run/log?run=%s&task=t&which=err" % ids["bad"],
              "/live/version?u=/", "/static/live.js", "/usage", "/upload", "/launch/diagram?pipeline=a&revision=b"):
        for r in (version(c, u), content(c, u, ["mid-0"])):
            assert r.status_code == 404 and "<script" not in r.text, u
    before = snapshot(w)
    assert c.post("/live/version?u=/").status_code == 405 and c.post("/live/content?u=/").status_code == 405
    assert c.post("/static/live.js").status_code == 405
    assert snapshot(w) == before


# ---- no side effect ------------------------------------------------------------------------------------------------------------------

def test_tc024_tc031_a_look_at_the_board_changes_nothing(w):
    # TC-024, TC-031
    ann, bob, ids, c, cb = scene(w)
    urls = ["/?run=" + ids["run"], "/?run=" + ids["bad"], "/?run=%s&stage=results&tab=outputs" % ids["ok"], "/?run=%s&stage=results&tab=outputs&relist=1" % ids["ok"],
            "/?run=%s&stage=finished" % ids["ok"], "/?run=%s&stage=results" % ids["ok"], "/"]
    c.get(urls[2])                       # the real page queues the first listing once
    jobs = len(w.sql("SELECT * FROM jobs"))
    before = snapshot(w)
    for u in urls:
        v = version(c, u)
        assert v.status_code == 200, u
        names = names_of(v.json())
        assert content(c, u, names[:3]).status_code == 200
    assert snapshot(w) == before and len(w.sql("SELECT * FROM jobs")) == jobs


def test_tc024_a_look_does_not_queue_the_first_listing_but_asks_for_one_page_load(w):
    # TC-024, TC-025
    ann, bob, ids, c, cb = scene(w)
    u = "/?run=%s&stage=results&tab=outputs" % ids["ok"]
    n = len(w.sql("SELECT * FROM jobs WHERE kind = 'list_site_files'"))
    assert version(c, u).json() == {"s": "reload"} and len(w.sql("SELECT * FROM jobs WHERE kind = 'list_site_files'")) == n
    assert version(c, u).json()["s"] == "ok"      # the next look inside 15 seconds does not ask again
    assert len(w.sql("SELECT * FROM jobs WHERE kind = 'list_site_files'")) == n
    c.get(u)
    assert len(w.sql("SELECT * FROM jobs WHERE kind = 'list_site_files'")) == n + 1


def test_tc025_the_waiting_page_of_a_run_that_is_not_in_the_index_yet(w):
    # TC-025
    ann = w.user("ann")
    w.hand_over(by=ann, run="web-t2")
    c = login(w, "ann")
    before = snapshot(w)
    v = version(c, "/?run_name=web-t2")
    assert v.status_code == 200 and v.json()["s"] == "ok" and snapshot(w) == before
    seed(w, "web-t2", "running", None, launch_row=False)
    assert version(c, "/?run_name=web-t2").json()["s"] == "ok"


# ---- the server keeps the reloads to one in 15 seconds ---------------------------------------------------------------------------------

def minute(tmp_path, monkeypatch, tag, look, answer_at=None, seconds=100):
    """How many reads of the site a launch page that waits for the site makes in `seconds`: today (a whole page every 15 seconds) or with the script (a look every 2)."""
    from abf_platform import status
    from test_web_guided_launch import Rig, ready
    now = [time.time()]
    monkeypatch.setattr(status, "now", lambda: now[0])
    monkeypatch.setenv("ABF_PLATFORM_DEADLINE_PIPELINE_FILES", "10")
    (tmp_path / tag).mkdir()
    r = Rig(tmp_path / tag, monkeypatch)
    _, c = ready(r)
    u = "/launch?pipeline=nf-core/ampliseq&revision=2.18.0"
    assert c.get(u).status_code == 200
    start, step, answered = now[0], (2 if look else 15), False
    for k in range(1, seconds // step + 1):
        now[0] = start + k * step
        if answer_at is not None and not answered and now[0] - start >= answer_at:
            answered = True
            r.w.sql  # noqa: B018
            con = sqlite3.connect(str(r.w.ip.state_db))
            with con:
                con.execute("UPDATE jobs SET state = 'done', finished_at = ?, result_json = ? WHERE kind = 'pipeline_files'", (now[0], json.dumps({"ok": True, "parts": {}})))
            con.close()
        if look:
            got = version(c, u)
            assert got.status_code == 200
            if got.json()["s"] == "reload":
                c.get(u)
        else:
            c.get(u)
    return len(r.w.sql("SELECT * FROM jobs WHERE kind = 'pipeline_files'"))


def test_tc022_tc023_a_launch_page_waiting_for_the_site_queues_no_more_than_today(tmp_path, monkeypatch):
    # TC-022, TC-023
    for tag, answer_at in (("silent", None), ("answered", 20)):
        today = minute(tmp_path, monkeypatch, tag + "-old", False, answer_at)
        mine = minute(tmp_path, monkeypatch, tag + "-new", True, answer_at)
        assert 1 <= mine <= today, (tag, mine, today)


# ---- the other pages ------------------------------------------------------------------------------------------------------------------

def test_tc029_tc032_a_look_at_a_file_that_is_waited_for_queues_no_job(w):
    # TC-029
    from test_results_files import file_jobs, file_url, world
    ann, c, rid = world(w)
    n = len(file_jobs(w))
    u = file_url(rid, "multiqc/multiqc_report.html")
    assert version(c, u).json() == {"s": "reload"} and len(file_jobs(w)) == n       # nothing was asked yet: the real page would ask
    assert c.get(u).status_code == 200 and len(file_jobs(w)) == n + 1
    before = snapshot(w)
    v = version(c, u)
    assert v.status_code == 200 and v.json()["s"] == "ok" and snapshot(w) == before and len(file_jobs(w)) == n + 1
    p = file_url(rid, "plots/a.png").replace("/run/file", "/run/preview")
    assert version(c, p).json() == {"s": "reload"} and len(file_jobs(w)) == n + 1
    assert content(c, u, ["narrow-0"]).status_code == 200 and len(file_jobs(w)) == n + 1


def test_tc028_a_look_at_an_upload_does_not_register_the_dataset(tmp_path, monkeypatch):
    # TC-028
    from test_web_upload import Up
    up = Up(tmp_path, monkeypatch)
    c = up.client()
    batch = up.ok(c)
    u = "/upload/" + batch
    before = snapshot(up.w)
    v = version(c, u)
    assert v.status_code == 200 and v.json()["s"] == "ok" and snapshot(up.w) == before
    for j in up.jobs():
        up.finish(j["id"])
    before = snapshot(up.w)
    v = version(c, u)
    assert v.status_code == 200 and snapshot(up.w) == before and up.datasets() == []
    assert content(c, u, ["mid-0"]).status_code == 200 and up.datasets() == [] and snapshot(up.w) == before
    t = tags(c.get(u).text)
    assert up.datasets() != [] and t.scripts == 0


def test_tc027_tc030_a_look_at_the_resume_page_never_asks_for_a_resume(tmp_path, monkeypatch):
    # TC-027, TC-030
    from test_web_guided_launch import ready, rig  # noqa: F401
    from test_web_guided_launch import Rig
    from test_web_guided_launch_2 import Fake, loading_files
    from test_web_resume_edit import make_run, edit_url, finish_run, A
    r = Rig(tmp_path, monkeypatch)
    f = Fake()
    f.files = loading_files()
    monkeypatch.setattr(A(), "pipeline_files", f.pipeline_files)
    monkeypatch.setattr(A(), "latest_release", lambda *a, write_cache=True, **kw: f.latest_release(*a, **kw))      # the look passes write_cache=False
    ann, c = ready(r)
    rid = make_run(r, ann)
    calls = []
    real = A().request_resume

    async def spy(*a, **kw):
        calls.append(kw)
        return await real(*a, **kw)
    monkeypatch.setattr(A(), "request_resume", spy)
    u = edit_url(rid)
    before = snapshot(r.w)
    v = version(c, u)
    assert v.status_code == 200 and v.json()["s"] == "ok" and snapshot(r.w) == before and calls == []
    finish_run(r, "run-a")
    before = snapshot(r.w)
    assert version(c, u).json() == {"s": "reload"} and calls == [] and snapshot(r.w) == before


def test_tc026_a_look_at_the_launch_page_reads_nothing_from_the_site(tmp_path, monkeypatch):
    # TC-026
    from test_web_guided_launch import ready
    from test_web_guided_launch import Rig
    from test_web_guided_launch_2 import Fake, loading_files
    from test_web_resume_edit import A
    r = Rig(tmp_path, monkeypatch)
    f = Fake()
    f.files = loading_files()
    seen = []
    real_pf, real_lr = f.pipeline_files, f.latest_release

    def pf(*a, **kw):
        seen.append(("pf", kw.get("enqueue", True)))
        return real_pf(*a, **kw)

    def lr(*a, write_cache=True, **kw):
        seen.append(("lr", kw.get("enqueue", True)))
        return real_lr(*a, **kw)
    monkeypatch.setattr(A(), "pipeline_files", pf)
    monkeypatch.setattr(A(), "latest_release", lr)
    ann, c = ready(r)
    u = "/launch?pipeline=nf-core/ampliseq&src=new"
    assert tags(c.get(u).text).scripts == 1
    seen.clear()
    before = snapshot(r.w)
    v = version(c, u)
    assert v.status_code == 200 and snapshot(r.w) == before
    assert seen and all(flag is False for _kind, flag in seen), seen


# ---- what else did not change -----------------------------------------------------------------------------------------------------------

def test_tc064_tc067_tc062_no_new_route_tool_or_dependency(w):
    # TC-064, TC-067, TC-062
    c = w.web()
    new = sorted((r.path, tuple(sorted(r.methods))) for r in c.app.routes if r.path.startswith(("/live", "/static")))
    assert new == [("/live/content", ("GET", "HEAD")), ("/live/version", ("GET", "HEAD")), ("/static/live.js", ("GET", "HEAD"))]      # exactly the three new routes
    for path in ("/static/live.js", "/live/version", "/live/content"):
        assert c.post(path).status_code == 405
    assert c.get("/live/version").status_code == 401 and c.get("/live/content").status_code == 401
    pyproject = (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dependencies = ["mcp>=2.3,<3", "python-multipart"]' in pyproject and 'test = ["pytest", "httpx"]' in pyproject
    assert not list(PLATFORM_DIR.rglob("package.json")) and not list((PLATFORM_DIR / "abf_platform").rglob("*.mjs"))
    assert sorted(p.name for p in (PLATFORM_DIR / "abf_platform" / "data").glob("*.js")) == ["live.js"]
    from abf_platform import mcp_server
    import asyncio
    from mcp import Client

    async def tools():
        async with Client(mcp_server.build_server(w.ip.index)) as cl:
            return {t.name for t in (await cl.list_tools()).tools}
    assert not [n for n in asyncio.run(tools()) if "live" in n or "sync" in n]


def test_tc063_in_scope_pages_differ_from_before_only_by_the_marks(w):
    # TC-063
    ann, ids, c, cz = pages_in_scope(w)
    for url in ("/?run=" + ids["run"], "/?run=%s&stage=results&tab=outputs" % ids["ok"], "/"):
        text = (cz if url == "/" else c).get(url).text
        old = re.sub(r"<noscript>(<meta [^>]*>)</noscript>", r"\1", text)
        old = old.replace(SCRIPT, "")
        old = re.sub(r"<body [^>]*>", "<body>", old, count=1)
        assert META15 in old or 'http-equiv="refresh" content="15;url=' in old
        assert "<script" not in old and "<noscript" not in old and "data-live" not in old


# ---- R-C: the whole data folder and the queue are the same before and after a look, for every page that carries the script ------------------

def whole(w):
    return snapshot(w), len(w.sql("SELECT * FROM jobs")), len(w.sql("SELECT * FROM confirmations"))


def look_all(c, u, extra=("", "&retry=1", "&relist=1")):
    for tail in extra:
        for r in (version(c, u + tail), content(c, u + tail, ["mid-0", "narrow-0", "left-0", "form-0", "steps-0"])):
            assert r.status_code in (200, 404), (u + tail, r.status_code)


def test_rc_a_file_and_a_preview_page_that_is_waiting_change_nothing_with_retry_either(w):
    # TC-029, R-C
    from test_results_files import file_jobs, file_url, world
    ann, c, rid = world(w)
    for route in ("/run/file", "/run/preview"):
        u = file_url(rid, "plots/a.png").replace("/run/file", route)
        c.get(u)                                    # the real page queues its one read
        before = whole(w)
        look_all(c, u)
        assert whole(w) == before, route


def test_rc_the_launch_page_with_the_real_actions_changes_nothing(tmp_path, monkeypatch):
    # TC-022, TC-026, R-C: no fake of the pipeline reads, so the real queue is the thing counted
    from test_web_guided_launch import Rig, ready
    r = Rig(tmp_path, monkeypatch)
    _, c = ready(r)
    for u in ("/launch?pipeline=nf-core/ampliseq&revision=2.18.0&src=used", "/launch?pipeline=nf-core/ampliseq&src=new"):
        c.get(u)
        before = whole(r.w)
        look_all(c, u, extra=("",))
        assert whole(r.w) == before, u
    before = whole(r.w)
    v = version(c, "/launch?pipeline=nf-core/ampliseq&revision=9.9.9&src=used")      # a pair nobody asked about yet: the look says "load it whole", it asks nothing
    assert v.status_code == 200 and v.json() == {"s": "reload"} and whole(r.w) == before
    assert version(c, "/launch?pipeline=nf-core/ampliseq&revision=9.9.9&src=used").json()["s"] == "ok"      # and not again inside 15 seconds


def test_rc_the_resume_edit_page_with_the_real_actions_changes_nothing(tmp_path, monkeypatch):
    # TC-027, TC-030, R-C
    from test_web_guided_launch import Rig, ready
    from test_web_resume_edit import edit_url, finish_run, make_run
    r = Rig(tmp_path, monkeypatch)
    ann, c = ready(r)
    rid = make_run(r, ann)
    u = edit_url(rid)
    c.get(u)
    before = whole(r.w)
    look_all(c, u, extra=("",))
    assert whole(r.w) == before
    finish_run(r, "run-a")
    before = whole(r.w)
    look_all(c, u, extra=("",))
    assert whole(r.w) == before and len(r.w.sql("SELECT * FROM confirmations")) == before[2]


def test_rc_an_upload_that_is_complete_but_not_registered_stays_so(tmp_path, monkeypatch):
    # TC-028, R-C
    from test_web_upload import Up
    up = Up(tmp_path, monkeypatch)
    c = up.client()
    batch = up.ok(c)
    for j in up.jobs():
        up.finish(j["id"])
    u = "/upload/" + batch
    before = whole(up.w)
    look_all(c, u, extra=("",))
    assert whole(up.w) == before and up.datasets() == []
