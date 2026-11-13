# Nothing existing: tests of live-sync (the one static script that keeps the pages that reloaded every 15 seconds up to date); the script, its two read-only
# routes and the region marks are ours (specs/live-sync/plan.md).
"""live-sync. Test case ids (TC-001 ...) refer to specs/live-sync/test-case.md. The browser cases (TC-001, 004 ... 040) are in scripts/dev/check_live_sync.py.
The script and the two live looks are three real routes of the web app (`/static/live.js`, `/live/version`, `/live/content`); the route pins of other tests gained exactly those three."""
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


def tick(c, seconds=2):
    """The looks have a floor of one second between two asks about the same page: a test that asks twice moves the clock of the app first."""
    clock = getattr(c.app.state, "clock", None)
    if hasattr(clock, "t"):
        clock.t += seconds


def version(c, u, k=None, **kw):
    tick(c)
    params = {"u": u}
    if k:
        params["k"] = k
    return c.get("/live/version?" + urllib.parse.urlencode(params), **kw)


def content(c, u, names):
    tick(c)
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


def no_script_no_sources(r, label):
    csp = r.headers["content-security-policy"]
    assert "script-src" not in csp and "connect-src" not in csp, label
    return csp


def test_tc044_tc046_pages_that_stay_without_a_script(w):
    # TC-044, TC-046
    ann, ids, c, cz = pages_in_scope(w)
    anon = w.web()
    fixed = {"/login": anon, "/settings": c, "/usage": c, "/upload": c, "/?run=%s&stage=downstream" % ids["ok"]: c, "/?run=nothing-at-all": c,
             "/?run_name=ghost": c, "/launch": c, "/launch?pipeline=nf-core/ampliseq": c}
    for url, who in fixed.items():
        r = who.get(url)
        assert r.status_code in (200, 404), url
        t = tags(r.text)
        assert t.scripts == 0 and t.noscript == 0 and "<noscript" not in r.text, url
        assert no_script_no_sources(r, url) in (BASE, IMG), url
    log = c.get("/run/log?run=%s&task=t&which=err" % ids["bad"])
    assert "<script" not in log.text and "<noscript" not in log.text and no_script_no_sources(log, "run log") == BASE
    # the board with a refused-button line is the answer to a POST: no script, no refresh
    r = c.post("/act/cancel", data={"run": ids["ok"], "csrf": c.app.state.csrf_token(c.cookies.get("abf_web"), "act:" + ids["ok"])})
    assert "<script" not in r.text and "<noscript" not in r.text and "refresh" not in r.text and no_script_no_sources(r, "flash board") == BASE


def test_tc046_the_login_and_confirmation_pages_have_no_script_and_todays_policy(w):
    # TC-046: the login page, and the confirmation page of a real launch request
    ann, ids, c, cz = pages_in_scope(w)
    login_page = w.web().get("/login")
    assert "<script" not in login_page.text and "<noscript" not in login_page.text and login_page.headers["content-security-policy"] == BASE
    got = w.launch(caller=ann, run="run-conf")
    assert got.get("id"), got
    for url in ("/c/" + got["id"], "/c/%s?lang=en" % got["id"]):
        r = c.get(url)
        assert r.status_code == 200 and "<script" not in r.text and "<noscript" not in r.text, url
        assert r.headers["content-security-policy"] == BASE, url


def test_tc044_welcome_consent_figure_diagram_and_ready_preview_pages_have_none(w):
    # TC-044: the rest of the pages the contract names
    from test_publish_figure import call, fig, press
    from test_temp_password import login_temp
    from test_web_board import consent_page
    ann, ids, c, cz = pages_in_scope(w)
    ct, _r, _ = login_temp(w, "bob")      # a login made with a temporary password sees /welcome
    welcome = ct.get("/welcome")
    assert welcome.status_code == 200 and "<script" not in welcome.text and "<noscript" not in welcome.text and no_script_no_sources(welcome, "welcome") == BASE
    consent = consent_page(w, "ann")
    assert "<script" not in consent.text and "<noscript" not in consent.text
    no_script_no_sources(consent, "consent")
    press(w, "ann", call(w, ann, ids["ok"], [fig("a.png", PNG)])["request_id"])
    got = call(w, ann, ids["ok"], [fig("b.png", PNG)])
    conf = c.get("/c/" + got["request_id"])
    assert "<script" not in conf.text and "<noscript" not in conf.text and no_script_no_sources(conf, "confirmation") == BASE
    figure = c.get("/run/figure?run=%s&name=a.png" % ids["ok"])
    assert figure.status_code == 200
    csp = no_script_no_sources(figure, "figure")
    assert csp.startswith("sandbox; default-src 'none'")
    diagram = c.get("/launch/diagram?pipeline=nf-core/ampliseq&revision=2.18.0")
    assert diagram.status_code in (200, 404) and "<script" not in diagram.text
    no_script_no_sources(diagram, "diagram")


def test_tc044_ready_preview_pages_have_no_script(w):
    # TC-044: a ready picture page and a ready report page (a report keeps its own sandbox policy, TC-045)
    from test_results_files import world
    from test_web_result_viewer import HTML, PNG as VPNG, answered, purl, ready
    ann, c, rid = world(w)
    pic = ready(w, c, rid, "plot.png", VPNG)
    assert pic.status_code == 200 and "<script" not in pic.text and "<noscript" not in pic.text
    no_script_no_sources(pic, "picture page")
    answered(w, c, rid, "multiqc/multiqc_report.html", HTML)
    rep = c.get(purl(rid, "multiqc/multiqc_report.html"))
    assert rep.status_code == 200 and "<script" not in rep.text and "<noscript" not in rep.text
    no_script_no_sources(rep, "report page")
    assert "frame-src 'self'" in rep.headers["content-security-policy"]


def test_tc045_the_report_policy_is_unchanged():
    # TC-045: the report inside the iframe keeps today's whole policy
    from abf_platform import web, web_preview
    report = web_preview.report_headers(web._HEADERS)["Content-Security-Policy"]
    assert report.startswith("sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' blob:")
    assert "connect-src 'none'" in report and "script-src 'self'" not in report and "connect-src 'self'" not in report


def test_tc045_the_page_policies_are_unchanged():
    # TC-045: the preview page keeps frame-src and img-src; the base sets are today's strings
    from abf_platform import web, web_preview
    assert web._HEADERS["Content-Security-Policy"] == BASE
    assert web.LAUNCH_HEADERS["Content-Security-Policy"] == IMG and web.FINISHED_HEADERS["Content-Security-Policy"] == IMG
    assert web_preview.page_headers(web._HEADERS, "html")["Content-Security-Policy"] == BASE + "; frame-src 'self'"
    assert web_preview.page_headers(web._HEADERS, "png")["Content-Security-Policy"].startswith("default-src 'none'; img-src 'self'; ")


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

def check_regions(text, label):
    """TC-016 on one page: regions do not overlap, every form control (and every form) lies inside exactly one region, names are `<fixed word>-<number>`."""
    lay = live().layout(text)
    spans = sorted((r["start"], r["end"]) for cont in lay for r in cont["regions"])
    assert spans, label
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), "regions overlap: " + label
    controls = [m.start() for m in re.finditer(r"<(form|input|textarea|select|button)\b", text)]
    assert controls, label
    for pos in controls:
        tag = text[pos:text.index(">", pos) + 1]
        if tag.startswith("<form") and ('class="lform"' in tag or 'action="/run/figures/pack"' in tag):
            continue      # a form that is itself a container: the controls inside it are the ones that must each lie in one region
        assert sum(1 for s_, e in spans if s_ <= pos < e) == 1, (label, text[pos:pos + 60])
    for cont in lay:
        assert re.fullmatch(r"[a-z]+", cont["n"]), cont["n"]
        for i, r in enumerate(cont["regions"]):
            assert r["name"] == "%s-%d" % (cont["n"], i) and re.fullmatch(r"[a-z]+-\d+", r["name"]), r["name"]
    return lay


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


def test_tc016_the_launch_edit_and_upload_pages_have_regions_too(tmp_path, monkeypatch):
    # TC-016: the pages that are made of forms
    from test_web_guided_launch import SEL, Rig, ready
    from test_web_guided_launch_2 import Fake, loading_files
    from test_web_resume_edit import A, edit_url, make_run
    from test_web_upload import Up
    (tmp_path / "rig").mkdir()
    r = Rig(tmp_path / "rig", monkeypatch)
    f = Fake()
    f.files = loading_files()
    monkeypatch.setattr(A(), "pipeline_files", f.pipeline_files)
    monkeypatch.setattr(A(), "latest_release", f.latest_release)
    ann, c = ready(r)
    launch = c.get(SEL)
    assert tags(launch.text).scripts == 1
    lay = check_regions(launch.text, "launch")
    assert {"form", "steps"} <= {x["n"] for x in lay}      # the launch form and its six steps are containers of their own
    rid = make_run(r, ann)
    edit = c.get(edit_url(rid))
    assert tags(edit.text).scripts == 1
    assert "form" in {x["n"] for x in check_regions(edit.text, "resume edit")}
    (tmp_path / "up").mkdir()
    up = Up(tmp_path / "up", monkeypatch)
    cu = up.client()
    batch = up.ok(cu)
    prog = cu.get("/upload/" + batch)
    assert tags(prog.text).scripts == 1
    check_regions(prog.text, "upload progress")


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


GOLDEN = {      # made by the code of origin/v3 a4133ab6 (before live-sync) with platform/tests/live_golden.py, see specs/live-sync/ledger.md
    "board": "949cc0accd27e35a", "empty board": "4e08cc15129a935a", "english board": "aff9ccf0f92f637b", "finished stage": "5b2547cf2cbf0528",
    "launch loading": "41b46337ab2f7cb1", "launch plain": "8c290402030193d8", "outputs tab": "5f60e6a387449cae", "results stage": "0ae8e77c99924dae",
    "running stage": "758a040ce54766e6"}


def test_tc063_the_pages_are_the_pages_of_before_but_for_the_three_additions(tmp_path, monkeypatch):
    # TC-063: board, running stage, results stage, Outputs tab, finished stage, empty board and the launch pages, each compared with the digest that origin/v3 made of it
    import live_golden
    from helpers import strip_live
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    seen = {}

    real = live_golden.digest

    def digest_stripped(text):
        return real(strip_live(text))
    monkeypatch.setattr(live_golden, "digest", digest_stripped)
    try:
        seen.update(live_golden.board_digests(World(tmp_path / "a", monkeypatch)))
        seen.update(live_golden.launch_digests(tmp_path / "b", monkeypatch))
    finally:
        monkeypatch.setattr(live_golden, "digest", real)
    assert seen == GOLDEN


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


# ---- TC-061: a look that finds nothing new is quick -------------------------------------------------------------------------------------

def test_tc061_a_look_at_a_page_that_did_not_change_is_answered_at_once_and_whole(w):
    # TC-061: one question, one answer (no stream); a generous bound so that a slow machine does not make it flaky
    ann, bob, ids, c, cb = scene(w)
    u = "/?run=" + ids["run"]
    version(c, u)
    for _ in range(3):
        began = time.monotonic()
        r = version(c, u)
        took = time.monotonic() - began
        assert r.status_code == 200 and r.json()["s"] == "ok" and took < 3.0, took
        assert "content-length" in r.headers and "transfer-encoding" not in r.headers


# ---- S2: the cost of the looks ------------------------------------------------------------------------------------------------------

def test_s2_a_page_asked_about_twice_is_read_once(w, monkeypatch):
    # S2 (a): the version and the content of the same text parse it once
    ann, bob, ids, c, cb = scene(w)
    u = "/?run=" + ids["run"]
    calls = []
    real = live()._layout
    monkeypatch.setattr(live(), "_layout", lambda doc: calls.append(len(doc)) or real(doc))
    live()._MEMO.clear()
    c.get(u)                      # the real page: decorated once
    n = len(calls)
    assert n == 1
    v = version(c, u).json()
    assert content(c, u, names_of(v)[:2]).json()["s"] == "ok"
    assert len(calls) == n, "the look parsed the same text again"


def test_s2_the_floor_of_one_second_and_the_script_is_not_told_to_reload(w):
    # S2 (b): the same login asking the same route about the same page inside a second is told to slow down (429, Retry-After), nothing is run
    ann, bob, ids, c, cb = scene(w)
    u = "/?run=" + ids["run"]
    first = c.get("/live/version?" + urllib.parse.urlencode({"u": u}))
    assert first.status_code == 200
    jobs = len(w.sql("SELECT * FROM jobs"))
    second = c.get("/live/version?" + urllib.parse.urlencode({"u": u}))
    assert second.status_code == 429 and second.headers["retry-after"] == "1" and second.json() == {"s": "slow"}
    assert second.headers["cache-control"] == "private, no-store" and len(w.sql("SELECT * FROM jobs")) == jobs
    other = c.get("/live/version?" + urllib.parse.urlencode({"u": "/?run=" + ids["bad"]}))      # another page is another question
    assert other.status_code == 200
    kind = c.get("/live/content?" + urllib.parse.urlencode({"u": u, "n": "mid-0"}))      # another route is another question
    assert kind.status_code == 200
    c.app.state.clock.t += 1.5
    assert c.get("/live/version?" + urllib.parse.urlencode({"u": u})).status_code == 200
    js = (PLATFORM_DIR / "abf_platform" / "data" / "live.js").read_text(encoding="utf-8")
    assert "429" in js and "slow" in js      # the script treats it as "ask again at the usual time", not as a failure and not as a reload


def test_s2_the_memories_of_the_server_are_bounded():
    # S2 (c): a flood of different keys cannot make the 15-second memory or the 1-second floor grow without end
    recent = live().Recent(cap=50)
    for i in range(1000):
        recent.put(("u", "page-%d" % i), float(i))
    assert len(recent) == 50 and recent.get(("u", "page-999")) == 999.0 and recent.get(("u", "page-0")) is None


def test_s2_the_reload_limit_still_holds_for_a_page_while_others_flood_the_memory(w, monkeypatch):
    # S2 (c): with a tiny memory the newest page keeps its 15-second limit
    ann, bob, ids, c, cb = scene(w)
    u = "/?run=%s&stage=results&tab=outputs" % ids["ok"]
    assert version(c, u).json() == {"s": "reload"}
    assert version(c, u).json()["s"] == "ok"      # 2 seconds later: not again


# ---- N6: a page nested too deeply --------------------------------------------------------------------------------------------------

def test_n6_a_page_nested_too_deeply_goes_out_as_it_was():
    # N6: no 500; the page is sent whole, without the script and with its refresh as it always was
    deep = "<div>" * 3000 + "x" + "</div>" * 3000
    doc = ('<!doctype html><html><head><meta http-equiv="refresh" content="15"></head><body><main class="narrow">%s</main></body></html>' % deep)
    headers = {"Content-Security-Policy": BASE}
    out, given = live().decorate(doc, headers)
    assert out == doc and given == headers
    assert "<script" not in out and "<noscript" not in out and 'http-equiv="refresh"' in out


# ---- N7: the looks ask no more often than today -------------------------------------------------------------------------------------

def test_n7a_the_other_tabs_of_a_succeeded_run_are_not_reloaded_for_a_listing_nobody_asks_for(w):
    # N7 (a): only the Outputs tab asks the site; a look at the Info tab says "ok", never "reload"
    ann, bob, ids, c, cb = scene(w)
    for tab in ("info", "tasks", "logs"):
        v = version(c, "/?run=%s&stage=results&tab=%s" % (ids["ok"], tab))
        assert v.status_code == 200 and v.json()["s"] == "ok", tab
    assert version(c, "/?run=%s&stage=results&tab=outputs" % ids["ok"]).json() == {"s": "reload"}      # the Outputs tab does ask


def test_n7b_a_batch_whose_registration_fails_is_registered_once_per_page_load_not_per_look(tmp_path, monkeypatch):
    # N7 (b): today the registration is tried when the page is loaded; a look never tries it, and the page that shows the failure has no script (so no more reloads)
    from abf_platform.actions import uploads
    from test_web_upload import Up
    up = Up(tmp_path, monkeypatch)
    c = up.client()
    batch = up.ok(c)
    for j in up.jobs():
        up.finish(j["id"])
    tries = []

    def refuse(*a, **kw):
        tries.append(1)
        return {"ok": False, "message": "no"}
    monkeypatch.setattr(uploads, "_register", refuse)
    u = "/upload/" + batch
    for _ in range(4):
        assert version(c, u).status_code == 200
    assert tries == []                      # looks never register
    page = c.get(u)                         # the one real load: one try
    assert len(tries) == 1 and "<script" not in page.text and 'http-equiv="refresh"' not in page.text      # the failure page has no script: nothing reloads it again
    assert tries == [1]


# ---- S1: the ids of the gallery ----------------------------------------------------------------------------------------------------

def test_s1_every_id_of_the_gallery_page_is_unique_and_is_made_of_the_figure_name(w):
    # S1: the id of a figure's tick box and delete form is made of its name (a hash could be made to collide; the delete button would then act on the wrong form)
    from test_publish_figure import call, press
    ann, bob, ids, c, cb = scene(w)
    names = ["a.png", "a-png.png", "a_png.png", "b.png", "x.y.z.png"]
    b64 = __import__("base64").b64encode(PNG).decode()
    press(w, "ann", call(w, ann, ids["ok"], [{"filename": n, "content_base64": b64, "code": "1\n", "params": "k=1"} for n in names])["request_id"])
    page = c.get("/?run=%s&stage=finished" % ids["ok"]).text
    found = re.findall(r'\sid="([^"]+)"', page)
    assert len(found) == len(set(found)), [i for i in found if found.count(i) > 1]
    for n in names:
        assert "pick-" + n in found and "del-" + n in found, n
        assert 'form="del-%s"' % n in page and 'for="pick-%s"' % n in page
    assert len({"pick-" + n for n in names} | {"del-" + n for n in names}) == 2 * len(names)
