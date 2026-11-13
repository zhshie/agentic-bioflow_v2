# Nothing existing: no test covers the setting ABF_STUDIO_URL, the frame of RStudio in the downstream page, or `fetch-results --r`; ours.
"""studio-embed: when the deployment setting ABF_STUDIO_URL (a loopback http address with a port) is set, the downstream stage of a succeeded run shows
RStudio in a frame, and only that page's CSP gains `frame-src`. Test case ids (specs/studio-embed/test-case.md) are in the comments. The unit template
and the documents are checked by tests/studio_embed_deploy_test.sh."""
import hashlib
import html
import os
import re
import socket
import subprocess
from pathlib import Path
from urllib.parse import quote

import pytest

from helpers import REPO_ROOT
from human_harness import World
from studio_harness import FakeSite, patch_session
from test_web_board import no_cjk, pane, seed
from test_web_downstream import ROUTES_V3
from test_web_results_outputs import ENTRIES, FOLDER, finish, launch_to, listings

URL = "http://127.0.0.1:8790"
GOLDEN = Path(__file__).resolve().parent / "__golden__"
TODAY = GOLDEN / "studio_embed_today"      # what the downstream page answered at origin/v3 74416bc4, before this feature (TC-022)
BAD_NOT_LOOPBACK = ["https://127.0.0.1:8790", "http://example.com:8790", "http://127.0.0.1.evil.com:8790", "http://localhost.evil.com:8790",
                    "http://127.0.0.1:8790@evil.com", "http://0.0.0.0:8790", "http://[::1]:8790", "http://127.1:8790", "http://2130706433:8790",
                    "ftp://127.0.0.1:8790", "javascript:alert(1)", "//127.0.0.1:8790", "*"]
BAD_SHAPE = ["http://127.0.0.1", "http://127.0.0.1:0", "http://127.0.0.1:99999", "http://127.0.0.1:abc", "http://127.0.0.1:8790/x",
             "http://127.0.0.1:8790?a=1", "http://127.0.0.1:8790#f", "http://u:p@127.0.0.1:8790", "http://127.0.0.1:8790; script-src *",
             "http://127.0.0.1:8790 'unsafe-inline'", "http://127.0.0.1:8790 ", " http://127.0.0.1:8790", "http://127.0.0.1:8790\n",
             "http://127.0.0.1:8790\nhttp://evil.example", "http://127.0.0.1: 8790", "http://127.0.0.1:08790", "http://127.0.0.1:8790/"]
SECRETS = re.compile(r"abf_pat_[A-Za-z0-9]{8,}|Bearer +[A-Za-z0-9_-]{8,}|(?:password|ABF_PAT|token|key)=[^<\s]|sk-[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{8,}|BEGIN [A-Z ]*PRIVATE KEY", re.I)


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    for k in list(os.environ):
        if k.startswith("ABF_"):
            monkeypatch.delenv(k)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(tmp_path / "data" / "index.db"))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    (tmp_path / "home").mkdir()


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path / "world", monkeypatch)


def client(w, studio_url=None, name="ann"):
    from starlette.testclient import TestClient
    from abf_platform import web
    kw = {"studio_url": studio_url} if studio_url is not None else {}
    c = TestClient(web.create_app(w.ip.index, w.ip.tokens, w.ip.state_db, clock=w.clock, **kw), follow_redirects=False)
    assert w.login(c, name).status_code == 303
    return c


def web_downstream_why(studio):
    from abf_platform import web_downstream
    return web_downstream.studio_url(studio)[1]


def succeeded(w, name="ann-done"):
    ann = w.ann = w.user("ann")
    rid = seed(w, name, "succeeded", ann)
    launch_to(w, name, FOLDER)
    return rid


def down(rid, studio=None, lang=False):
    out = "/?run=%s&stage=downstream" % rid
    if studio is not None:
        out += "&studio=" + quote(studio, safe="")
    return out + ("&lang=en" if lang else "")


def iframes(text):
    return re.findall(r"<iframe\b[^>]*>", text)


def attr(tag, name):
    m = re.search(r'\b%s="([^"]*)"' % name, tag)
    return html.unescape(m.group(1)) if m else None


def csp(r):
    return r.headers.get("content-security-policy", "")


def r_pre(text):
    """The two R lines, as text, of the first <pre> that holds them."""
    for m in re.finditer(r"<pre\b[^>]*>(.*?)</pre>", text, re.S):
        body = html.unescape(m.group(1))
        if "eval(parse(text" in body:
            return body.strip().split("\n")
    raise AssertionError("no pre with the R lines")


def run_web(argv, monkeypatch, env=None, capsys=None):
    """cli.main(["web", ...]) with uvicorn and create_app replaced; (rc, create_app kwargs list, uvicorn calls, stderr)."""
    import uvicorn
    from abf_platform import cli, web
    made, ran = [], []
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: ran.append((a, k)))
    monkeypatch.setattr(web, "create_app", lambda *a, **k: made.append(k) or object())
    capsys.readouterr()
    rc = cli.main(["web"] + argv)
    return rc, made, ran, capsys.readouterr().err


# ---- US1: the setting -----------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["http://127.0.0.1:8790", "http://localhost:8790"])
def test_tc001_loopback_value_is_accepted_and_given_to_the_page(value, monkeypatch, capsys):
    # TC-001
    rc, made, ran, err = run_web(["--port", "0"], monkeypatch, {"ABF_STUDIO_URL": value}, capsys)
    assert rc == 0 and len(ran) == 1 and len(made) == 1 and made[0].get("studio_url") == value, err


@pytest.mark.parametrize("value", BAD_NOT_LOOPBACK + BAD_SHAPE)
def test_tc002_tc003_tc004_a_bad_value_stops_the_start_and_says_why(value, monkeypatch, capsys):
    # TC-002 TC-003 TC-004
    rc, made, ran, err = run_web(["--port", "0"], monkeypatch, {"ABF_STUDIO_URL": value}, capsys)
    assert rc == 1 and made == [] and ran == []
    assert "ABF_STUDIO_URL" in err and "rejected" in err and "http://127.0.0.1:" in err
    assert re.search(r"[一-鿿]", err), "the message is in both languages"


@pytest.mark.parametrize("value", [None, ""])
def test_tc005_unset_or_empty_is_no_setting(value, monkeypatch, capsys):
    # TC-005
    rc, made, ran, err = run_web(["--port", "0"], monkeypatch, {} if value is None else {"ABF_STUDIO_URL": value}, capsys)
    assert rc == 0 and len(made) == 1 and made[0].get("studio_url") is None and len(ran) == 1


@pytest.mark.parametrize("env", [{}, {"ABF_STUDIO_URL": "http://127.0.0.1:8790"}])
def test_tc006_the_exec_line_of_the_web_unit_still_parses(env, monkeypatch, capsys):
    # TC-006: the argument list of abf-web.service.in, ${...} expanded, goes to the command line parser; the setting is read inside cmd_web
    unit = (REPO_ROOT / "deploy" / "systemd" / "abf-web.service.in").read_text(encoding="utf-8")
    line = next(l for l in unit.splitlines() if l.startswith("ExecStart="))
    args = line.split("abf-platform web", 1)[1].replace("${ABF_PUBLIC_URL}", "https://abf.example").split()
    assert "ABF_STUDIO_URL" not in line, "abf-web.service.in is not changed"
    rc, made, ran, err = run_web(args, monkeypatch, env, capsys)
    assert rc == 0, err
    assert made[0].get("studio_url") == env.get("ABF_STUDIO_URL")


def test_tc002_the_check_is_in_cmd_web_after_public_url_and_before_create_app():
    # TC-006
    import inspect
    from abf_platform import cli
    src = inspect.getsource(cli.cmd_web)
    assert src.index("--public-url") < src.index("ABF_STUDIO_URL") < src.index("create_app(")


def test_tc002_the_validator_is_pure():
    # TC-002: web_downstream.py imports neither os nor socket (the setting is read in cmd_web)
    from abf_platform import web_downstream
    src = Path(web_downstream.__file__).read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(os|socket|urllib\.request|http\.client)\b", src, re.M)
    assert web_downstream.studio_embed_url("http://127.0.0.1:8790") == ("http://127.0.0.1:8790", None)
    assert web_downstream.studio_embed_url(None) == (None, None) and web_downstream.studio_embed_url("") == (None, None)
    for bad in BAD_NOT_LOOPBACK + BAD_SHAPE:
        got, why = web_downstream.studio_embed_url(bad)
        assert got is None and why, bad


@pytest.mark.parametrize("value", BAD_NOT_LOOPBACK + BAD_SHAPE)
def test_tc002_create_app_refuses_a_bad_value_too(w, value):
    # TC-002: whoever builds the app, no bad value reaches a page or a header
    from abf_platform import web
    with pytest.raises(ValueError):
        web.create_app(w.ip.index, w.ip.tokens, w.ip.state_db, studio_url=value)


# ---- US2: the page --------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["http://127.0.0.1:8790", "http://localhost:8790"])
def test_tc007_one_frame_whose_source_is_the_setting(w, value):
    # TC-007 TC-001
    rid = succeeded(w)
    r = client(w, value).get(down(rid))
    assert r.status_code == 200
    frames = iframes(r.text)
    assert len(frames) == 1 and attr(frames[0], "src") == value and attr(frames[0], "title").strip()
    assert r.text.count("<iframe") == 1


def test_tc008_link_above_the_frame_opens_a_new_tab(w):
    # TC-008
    rid = succeeded(w)
    text = client(w, URL).get(down(rid)).text
    m = re.search(r'<a [^>]*>在新分頁開啟 RStudio</a>', text)
    assert m and attr(m.group(0), "href") == URL and attr(m.group(0), "target") == "_blank" and attr(m.group(0), "rel") == "noopener noreferrer"
    assert m.start() < text.index("<iframe")
    en = client(w, URL).get(down(rid, lang=True)).text
    m = re.search(r'<a [^>]*>Open RStudio in a new tab</a>', en)
    assert m and attr(m.group(0), "href") == URL and m.start() < en.index("<iframe")


@pytest.mark.parametrize("studio", ["https://evil.example/", "http://localhost:8790", "http://127.0.0.1:9999", "javascript:alert(1)", "data:text/html,x"])
def test_tc009_a_studio_query_never_reaches_the_frame(w, studio):
    # TC-009
    rid = succeeded(w)
    r = client(w, URL).get(down(rid, studio))
    assert [attr(f, "src") for f in iframes(r.text)] == [URL]
    assert csp(r).count("frame-src") == 1 and "frame-src %s" % URL in csp(r) and studio not in csp(r)
    assert not re.search(r"<iframe[^>]*%s" % re.escape(studio), r.text)
    if web_downstream_why(studio):
        assert 'role="alert"' in r.text and studio not in html.unescape(re.sub(r"<[^>]+>", " ", r.text)).replace(URL, "")
    assert "%s" % quote(studio, safe="") not in r.text


@pytest.mark.parametrize("lang,words", [(False, ["空白", "尚未啟動", "擋下", "在新分頁開啟 RStudio", "docs/OPERATIONS.md"]),
                                        (True, ["blank", "not started", "blocked", "Open RStudio in a new tab", "docs/OPERATIONS.md"])])
def test_tc010_a_hint_for_a_blank_frame(w, lang, words):
    # TC-010: the platform does not know whether RStudio runs; the page is the same either way and says what to do
    rid = succeeded(w)
    r = client(w, URL).get(down(rid, lang=lang))
    assert r.status_code == 200
    for word in words:
        assert word in r.text, word


def test_tc011_two_r_lines_to_paste(w):
    # TC-011 TC-028 TC-042
    rid = succeeded(w)
    for lang in (False, True):
        lines = r_pre(client(w, URL).get(down(rid, lang=lang)).text)
        assert len(lines) == 2, lines
        one, two = lines
        assert "eval(parse(text" in one and "system2(" in one and "fetch-results" in one and rid in one and "--r" in one
        assert "publish-figure" in two and rid in two
        assert not SECRETS.search("\n".join(lines))


def test_tc012_the_run_id_is_escaped_for_html_and_for_r():
    # TC-012
    from abf_platform import web_downstream
    rid = 'x<b>"y&z\'\\w'
    for lang in ("zh", "en"):
        out = web_downstream.render_downstream(lang, {"id": rid}, None, None, "T", studio_embed=URL)
        assert "<b>" not in out and "x<b" not in out and '"y&z' not in out
        pre = next(m for m in re.finditer(r"<pre\b[^>]*>(.*?)</pre>", out, re.S) if "eval(parse" in m.group(1))
        lines = html.unescape(pre.group(1)).strip().split("\n")
        for line in lines:
            strings = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
            decoded = [re.sub(r"\\(.)", r"\1", s) for s in strings]
            assert rid in decoded, line           # the id is one whole R string, however many quotes and backslashes it holds
            rest = re.sub(r'"(?:[^"\\]|\\.)*"', '""', line)
            assert rest.count("(") == rest.count(")") and "<" not in rest.replace("<-", "")
        if lang == "en":
            assert no_cjk(out)


def test_tc013_the_terminal_commands_are_second_and_folded(w):
    # TC-013
    rid = succeeded(w)
    text = client(w, URL).get(down(rid)).text
    m = re.search(r"<details>(.*?)</details>", text, re.S)
    assert m and "<details open" not in text
    for cmd in ("abf-platform studio-connect --server &lt;平台網址&gt;", "abf-platform fetch-results %s" % rid, "abf-platform publish-figure %s &lt;圖檔&gt;" % rid):
        assert cmd in m.group(1)
    assert text.index("eval(parse(text") < text.index("<details>")
    assert "abf-platform studio-connect" not in text[:text.index("<details>")]


def test_tc014_no_new_style(w):
    # TC-014
    from abf_platform import web_board
    rid = succeeded(w)
    r = client(w, URL).get(down(rid))
    frame = iframes(r.text)[0]
    allow = attr(frame, "allow")
    assert allow and "*" not in allow and not re.search(r"camera|microphone|geolocation", allow)
    assert attr(frame, "referrerpolicy") and attr(frame, "width") == "100%" and int(attr(frame, "height")) >= 600
    assert "style=" not in re.sub(r"<style>.*?</style>", "", r.text, flags=re.S)
    known = set(re.findall(r"\.([A-Za-z][\w-]*)", web_board.STYLE))
    used = {c for m in re.findall(r'class="([^"]*)"', pane(r.text, "middle")) for c in m.split()}
    assert used <= known, used - known
    src = (Path(__file__).resolve().parent / "test_results_files.py").read_text(encoding="utf-8")
    assert hashlib.sha256(web_board.STYLE.encode("utf-8")).hexdigest() == re.search(r'^STYLE_SHA256 = "([0-9a-f]{64})"', src, re.M).group(1)


def test_tc015_no_script_no_refresh_no_new_route(w):
    # TC-015
    rid = succeeded(w)
    c = client(w, URL)
    for lang in (False, True):
        t = c.get(down(rid, lang=lang)).text
        assert "<script" not in t and 'http-equiv="refresh"' not in t
    assert sorted((r.path, tuple(sorted(r.methods or []))) for r in c.app.routes) == sorted(
        ROUTES_V3 + [("/run/figure", ("GET", "HEAD")), ("/run/figure/delete", ("POST",)), ("/run/figures/pack", ("POST",))])


def test_tc016_both_languages(w):
    # TC-016
    from abf_platform import web_downstream
    from test_web_wording_sweep import banned_in
    zh, en = web_downstream.STRINGS["zh"], web_downstream.STRINGS["en"]
    assert set(zh) == set(en) and all(zh[k].strip() and en[k].strip() for k in zh)
    for k in ("embed_link", "embed_title", "embed_blank", "r_note", "terminal_summary"):
        assert k in zh and not banned_in(zh[k], run=False), k
    rid = succeeded(w)
    en_page = client(w, URL).get(down(rid, lang=True)).text
    assert no_cjk(en_page)


def test_tc017_no_frame_on_any_other_state_of_a_run(w):
    # TC-017
    ann = w.user("ann")
    ids = {st: seed(w, "n-" + st, st, ann, reason="boom" if st == "failed" else None) for st in ("running", "failed", "succeeded")}
    launch_to(w, "n-succeeded", FOLDER)
    bob = w.user("bob")
    bob_run = seed(w, "bobs", "succeeded", bob)
    c = client(w, URL)
    for st in ("running", "failed"):
        r = c.get(down(ids[st]))
        assert r.status_code == 200 and iframes(r.text) == [] and "frame-src" not in csp(r)
    for stage in ("results", "running", "finished"):
        r = c.get("/?run=%s&stage=%s" % (ids["succeeded"], stage))
        assert iframes(r.text) == [] and "frame-src" not in csp(r), stage
    for rid in (bob_run, "id-nope"):
        r = c.get(down(rid))
        assert r.status_code == 404 and iframes(r.text) == [] and "frame-src" not in csp(r) and rid not in r.text


def test_tc018_nothing_else_is_added_and_nothing_connects(w, monkeypatch):
    # TC-018
    seen = []
    real_connect, real_ex, real_create, real_addr = socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo
    monkeypatch.setattr(socket.socket, "connect", lambda self, addr, *a: seen.append(addr) or real_connect(self, addr, *a))
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, addr, *a: seen.append(addr) or real_ex(self, addr, *a))
    monkeypatch.setattr(socket, "create_connection", lambda addr, *a, **k: seen.append(addr) or real_create(addr, *a, **k))
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, *a, **k: seen.append((host, port)) or real_addr(host, port, *a, **k))
    rid = succeeded(w)
    c = client(w, URL)
    r = c.get(down(rid))
    assert not [a for a in seen if 8790 in (a if isinstance(a, tuple) else ()) or "8790" in map(str, a if isinstance(a, tuple) else ())], seen
    low = pane(r.text, "middle").lower()
    assert len(iframes(r.text)) == 1 and "jupyter" not in low and "<input" not in low and "<form" not in low
    base = git_base()
    if base:
        changed = git(["diff", "--name-only", base]).split()
        assert not [f for f in changed if f.startswith("platform/abf_station/")]


def git(args):
    return subprocess.run(["git"] + args, cwd=str(REPO_ROOT), capture_output=True, text=True, check=True).stdout


def git_base():
    try:
        return git(["merge-base", "origin/v3", "HEAD"]).strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# ---- US3: the CSP ---------------------------------------------------------------------------------------------------------------------------

def test_tc019_the_csp_of_the_page_gains_one_frame_source(w):
    # TC-019
    from abf_platform import web
    rid = succeeded(w)
    for value in (URL, "http://localhost:8790"):
        r = client(w, value).get(down(rid))
        policy = csp(r)
        assert policy.endswith("; frame-src %s" % value) and policy.count("frame-src") == 1
        assert policy.replace("; frame-src %s" % value, "") == web._HEADERS["Content-Security-Policy"]
        for keep in ("frame-ancestors 'none'", "default-src 'none'", "form-action 'self'", "base-uri 'none'", "style-src 'sha256-"):
            assert keep in policy
        assert "script-src" not in policy and "unsafe-inline" not in policy and "*" not in policy and "'self'" not in policy.split("frame-src")[1]
        assert r.headers["x-frame-options"] == "DENY"


PAGES = ["/", "/settings", "/usage", "/launch", "/upload", "/login", "/nope", "/c/nope", "/consent/nope", "/run/figure", "/run/image", "/run/report",
         "/run/preview", "/run/file", "/run/log"]


def test_tc020_no_other_page_changes(w):
    # TC-020
    rid = succeeded(w)
    ann = w.ann
    running = seed(w, "r1", "running", ann)
    with_setting, without = client(w, URL), client(w)
    paths = PAGES + ["/?run=%s" % running, "/?run=%s&stage=downstream" % running, "/?run=%s&stage=results" % rid, "/?run=%s&stage=results&tab=outputs" % rid,
                     "/?run=%s&stage=finished" % rid, "/?run=%s&stage=running" % rid, "/?run=%s" % rid]
    for path in paths:
        a, b = with_setting.get(path), without.get(path)
        assert dict(a.headers) == dict(b.headers), path
        assert a.status_code == b.status_code, path
        if "/run/preview" not in path:
            assert "frame-src" not in csp(a) and "<iframe" not in a.text, path
    anon = w.web()
    r = anon.get("/login")
    assert "frame-src" not in csp(r) and "<iframe" not in r.text


def test_tc021_the_frame_and_frame_src_go_together(w):
    # TC-021
    rid = succeeded(w)
    c = client(w, URL)
    cases = [down(rid), down(rid, lang=True), down(rid, "javascript:alert(1)"), down(rid, "http://localhost:8790"), down(rid),
             "/?run=%s&stage=results" % rid, "/?run=%s" % rid]
    for path in cases:
        r = c.get(path)
        frames, policy = iframes(r.text), csp(r)
        assert bool(frames) == ("frame-src" in policy), path
        if frames:
            assert re.search(r"frame-src (\S+)", policy).group(1) == attr(frames[0], "src") == URL


# ---- US4: no setting, the page is today's -----------------------------------------------------------------------------------------------

def snap(resp, rid):
    head = "\n".join("%s: %s" % (k, v) for k, v in sorted(resp.headers.items()) if k.lower() != "content-length")
    body = re.sub(r"[0-9a-f]{20,}", "<HEX>", resp.text.replace(rid, "<RUN>"))
    body = re.sub(r"\d\d-\d\d \d\d:\d\d", "<TIME>", body)      # the seeded run is dated by the wall clock
    return "status: %d\n%s\n\n%s" % (resp.status_code, head, body)


@pytest.mark.parametrize("setting", [None, ""])
def test_tc022_without_the_setting_the_page_is_byte_for_byte_today(w, setting):
    # TC-022: eight snapshots made from the code of 74416bc4 before this feature
    rid = succeeded(w)
    c = client(w, setting)
    n = 0
    for read in (False, True):
        if read:
            c.get("/?run=%s&stage=results&tab=outputs" % rid)
            finish(w, listings(w)[-1]["id"], entries=ENTRIES)
        for lang in (False, True):
            for studio in ("", "https://rstudio.example.org/s/abc"):
                name = "%s_%s_%s.txt" % ("read" if read else "unread", "en" if lang else "zh", "studio" if studio else "nostudio")
                got = snap(c.get(down(rid, studio or None, lang)), rid)
                assert got == (TODAY / name).read_text(encoding="utf-8"), name
                assert "frame-src" not in got and "<iframe" not in got
                n += 1
    assert n == 8 and len(list(TODAY.glob("*.txt"))) == 8


def test_tc023_the_two_existing_page_tests_are_unchanged():
    # TC-023
    base = git_base()
    if not base:
        pytest.skip("no origin/v3 to compare with")
    assert git(["diff", base, "--", "platform/tests/test_web_downstream.py", "platform/tests/test_web_result_viewer.py"]) == ""


# ---- US5: fetch-results --r ----------------------------------------------------------------------------------------------------------------

BASE = {"ASV_table.tsv": "id\ts1\ta\t1\n", "counts.tsv": "g\tn\nx\t5\n", "notes.md": "# notes\n", "DATA.TSV": "u\tv\n1\t2\n"}
ASSIGN = re.compile(r'^[A-Za-z][A-Za-z0-9_]* <- read\.(csv|delim)\(.*\)$')


def fetch(argv, capsys):
    from abf_platform import cli
    capsys.readouterr()
    try:
        rc = cli.main(["fetch-results"] + list(argv))
    except SystemExit as e:
        rc = e.code
    out = capsys.readouterr()
    return rc, out.out, out.err


def balanced(line):
    depth, quote_, esc = 0, False, False
    for ch in line:
        if esc:
            esc = False
        elif ch == "\\" and quote_:
            esc = True
        elif ch == '"':
            quote_ = not quote_
        elif not quote_ and ch == "(":
            depth += 1
        elif not quote_ and ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not quote_


def test_tc024_r_prints_only_the_r_code(tmp_path, monkeypatch, capsys):
    # TC-024
    from abf_platform import studio_cli
    monkeypatch.setattr(studio_cli, "POLL_SECONDS", 0.01)
    patch_session(monkeypatch, FakeSite(files=dict(BASE, **{"x.csv": "a,b\n1,2\n"})))
    rc0, out0, err0 = fetch(["run1"], capsys)
    rc1, out1, err1 = fetch(["run1", "--r"], capsys)
    assert rc0 == rc1 == 0, (err0, err1)
    lines = out1.rstrip("\n").split("\n")
    assert lines and all(l.startswith("#") or ASSIGN.match(l) for l in lines), lines
    assert all(balanced(l) for l in lines if not l.startswith("#"))
    code0 = [l for l in out0.split("\n") if ASSIGN.match(l) or l.startswith("# ")]
    assert [l for l in lines if ASSIGN.match(l)] == [l for l in code0 if ASSIGN.match(l)] and any(ASSIGN.match(l) for l in lines)
    assert "已取得" in err1 and "已取得" not in out1, "progress goes to standard error"


@pytest.mark.parametrize("case", ["read_fails", "no_tables", "not_set_up"])
def test_tc025_everything_but_the_code_goes_to_standard_error(case, tmp_path, monkeypatch, capsys):
    # TC-025
    from abf_platform import studio_cli
    monkeypatch.setattr(studio_cli, "POLL_SECONDS", 0.01)
    if case == "read_fails":
        reason = {"found": True, "state": "error", "code": "refused", "reason": "nope"}
        patch_session(monkeypatch, FakeSite(files={"a.tsv": "x\n", "b.tsv": "y\n"}, errors={"a.tsv": reason}))
    elif case == "no_tables":
        patch_session(monkeypatch, FakeSite(files={"notes.md": "# n\n"}))
    rc0, out0, err0 = fetch(["run1"], capsys)
    rc1, out1, err1 = fetch(["run1", "--r"], capsys)
    assert rc1 == rc0 and (case != "not_set_up" or rc1 == 2)
    for line in out1.split("\n"):
        assert not line or line.startswith("#") or ASSIGN.match(line), line
    assert err1.strip(), "the message is on standard error"
    if case == "read_fails":
        assert rc1 == 1


def test_tc026_the_golden_files_change_only_on_the_fetch_results_row():
    # TC-026
    base = git_base()
    if not base:
        pytest.skip("no origin/v3 to compare with")
    for name in ("cli_tree", "cli_help_top"):
        path = "platform/tests/__golden__/%s.txt" % name
        old, new = git(["show", "%s:%s" % (base, path)]), (REPO_ROOT / path).read_text(encoding="utf-8")
        assert old != new, name
        if name == "cli_tree":
            ol, nl = old.split("\n"), new.split("\n")
            assert len(ol) == len(nl) and [i for i, (a, b) in enumerate(zip(ol, nl)) if a != b] == [16]
            assert nl[16].startswith("fetch-results｜run,--dir,--r｜") and "--r" in nl[16]
        else:
            norm = lambda s: re.sub(r"\s+", " ", s)
            assert norm(new).replace(" [--r]", "") == norm(old)
            assert "[--r]" in new
    tree = (REPO_ROOT / "platform/tests/__golden__/cli_tree.txt").read_text(encoding="utf-8")
    old_tree = git(["show", "%s:platform/tests/__golden__/cli_tree.txt" % base])
    pick = lambda t, n: [l for l in t.split("\n") if l.startswith(n + "｜")]
    for other in ("web", "publish-figure", "studio-connect"):
        assert pick(tree, other) == pick(old_tree, other) and pick(tree, other)


def test_tc027_publish_figure_and_the_write_path_are_untouched():
    # TC-027
    base = git_base()
    if not base:
        pytest.skip("no origin/v3 to compare with")
    changed = git(["diff", "--name-only", base]).split()
    for f in ("platform/abf_platform/confirm.py", "platform/abf_platform/store.py", "platform/tests/test_studio_publish.py"):
        assert f not in changed, f
    diff = git(["diff", "-U0", base, "--", "platform/abf_platform/studio_cli.py"])
    assert "publish" not in "\n".join(l for l in diff.split("\n") if l[:1] in "+-" and not l.startswith(("+++", "---"))).lower()


def test_tc028_the_second_line_stands_alone(w):
    # TC-028 TC-042
    rid = succeeded(w)
    two = r_pre(client(w, URL).get(down(rid)).text)[1]
    assert "library(" not in two and "install.packages" not in two
    assert "tempfile(" in two and "dev.copy(" in two and "png" in two and "dev.off()" in two and "publish-figure" in two and rid in two
    assert not re.search(r"--yes|-y\b|confirm|user_confirmed|--code", two) and balanced(two)


# ---- the constitution -----------------------------------------------------------------------------------------------------------------------

def test_tc041_no_secret_shape_in_the_page_or_the_r_output(w, monkeypatch, capsys):
    # TC-041
    rid = succeeded(w)
    c = client(w, URL)
    for lang in (False, True):
        assert not SECRETS.search(c.get(down(rid, lang=lang)).text)
    from abf_platform import studio_cli
    monkeypatch.setattr(studio_cli, "POLL_SECONDS", 0.01)
    patch_session(monkeypatch, FakeSite(files=BASE))
    rc, out, err = fetch(["run1", "--r"], capsys)
    assert not SECRETS.search(out)


def test_tc042_the_page_writes_nothing(w):
    # TC-042
    rid = succeeded(w)
    t = client(w, URL).get(down(rid)).text
    mid = pane(t, "middle")
    assert "<form" not in mid and "method=\"post\"" not in mid.lower() and "<button" not in mid
