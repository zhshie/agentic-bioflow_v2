# Nothing existing: tests of the downstream stage (studios-new-tab); ours.
"""studios-new-tab: the downstream stage of a succeeded run, with the new-tab link to the person's own Studio (TC ids in the comments)."""
import hashlib
import logging
import re
import sqlite3
from pathlib import Path

import pytest

from human_harness import World
from test_web_board import no_cjk, pane, plain, seed
from test_web_results_outputs import ENTRIES, FOLDER, finish, launch_to, listings

ROOT = Path(__file__).resolve().parent.parent
LOGIN_NODE_SENTENCE = re.compile(r"<p>[^<]*NCHC[^<]*</p>")       # the one sentence that says the platform does not start a Studio on the login node

ROUTES_V3 = [('/', ('GET', 'HEAD')), ('/.well-known/oauth-authorization-server', ('GET', 'HEAD', 'OPTIONS')), ('/act/{verb}', ('POST',)),
             ('/act/{verb}/edit', ('GET', 'HEAD')), ('/authorize', ('GET', 'HEAD', 'POST')), ('/c/{rid}', ('GET', 'HEAD')), ('/c/{rid}', ('POST',)),
             ('/consent/{rid}', ('GET', 'HEAD')), ('/consent/{rid}', ('POST',)), ('/launch', ('GET', 'HEAD')), ('/launch', ('POST',)),
             ('/launch/diagram', ('GET', 'HEAD')), ('/login', ('GET', 'HEAD')), ('/login', ('POST',)), ('/logout', ('POST',)),
             ('/register', ('OPTIONS', 'POST')), ('/revoke', ('OPTIONS', 'POST')), ('/run/file', ('GET', 'HEAD')), ('/run/image', ('GET', 'HEAD')), ('/run/log', ('GET', 'HEAD')), ('/run/preview', ('GET', 'HEAD')), ('/run/report', ('GET', 'HEAD')), ('/settings', ('GET', 'HEAD')),
             ('/settings/inventory', ('POST',)), ('/settings/personal', ('POST',)), ('/settings/pipelines', ('POST',)),
             ('/settings/pipelines/confirm', ('POST',)), ('/token', ('OPTIONS', 'POST')), ('/upload', ('GET', 'HEAD')), ('/upload', ('POST',)),
             ('/upload/{batch}', ('GET', 'HEAD')), ('/usage', ('GET', 'HEAD')), ('/welcome', ('GET', 'HEAD')), ('/welcome', ('POST',))]
ACTIONS_V3 = ['Caller', 'ConnectorCaller', 'approve', 'caller_area', 'cancel', 'check_site_pipeline_change', 'clean_requests', 'confined_samplesheet',
              'describe_request', 'estimate_su', 'find_approved', 'forget', 'forget_check', 'form_is_trusted', 'get_compute_env', 'get_my_settings',
              'get_run', 'keep_screen', 'latest_release', 'launch', 'launch_prefill', 'list_agents', 'list_compute_envs', 'list_pipeline_registrations', 'list_registered_pipelines', 'list_runs',
              'list_samplesheets', 'list_site_files', 'list_used_pipelines', 'my_usage', 'nfcore_catalogue', 'offer_cleanup', 'offer_cleanups',
              'person_at', 'pipeline_files', 'platform_path_for', 'preview_samplesheet', 'propose_pipeline_registration', 'read_confined_samplesheet', 'read_run_file', 'read_task_log',
              'register_site_pipeline', 'reload_site_inventory', 'remove_pipeline_registration', 'remove_site_pipeline', 'request_cancel', 'request_facts', 'request_forget',
              'request_launch', 'request_pipeline_launch', 'request_relaunch', 'request_resume', 'run_environment', 'run_file', 'run_outputs', 'run_usage',
              'set_my_setting', 'site_pipeline_inventory', 'start_upload_batch', 'task_log_view', 'upload_batch_status', 'void_request']

REJECTED = ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,x", "file:///etc/passwd", "ftp://x", "//evil.example",
            "http://user:pw@host/", "http://h/?token=abc", "http://h/?PASSWORD=x", "http://h/?key=abc", "http://h/?secret=abc",
            "https://h/" + "a" * 295, "http://h/a b", "http://h/a\nb", "http://"]


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def logged(w, name="ann"):
    c = w.web()
    assert w.login(c, name).status_code == 303
    return c


def succeeded(w, name="ann-done"):
    ann = w.user("ann")
    rid = seed(w, name, "succeeded", ann)
    launch_to(w, name, FOLDER)
    return rid, logged(w)


def url(rid, studio=None, lang=None):
    from urllib.parse import quote
    out = "/?run=%s&stage=downstream" % rid
    if studio is not None:
        out += "&studio=" + quote(studio, safe="")
    return out + ("&lang=en" if lang else "")


def served_log(caplog):
    """What the platform logged (the test client's own request log is not the platform's)."""
    return " ".join(r.getMessage() for r in caplog.records if not r.name.startswith(("httpx", "httpcore")))


def mid(text):
    return pane(text, "middle")


# ---- TC-001 .. TC-006 ----------------------------------------------------------------------------------------------------------

def test_downstream_succeeded_shows_section_not_placeholder(w):
    # TC-001 TC-002 TC-003 TC-004 TC-005 TC-014
    rid, c = succeeded(w)
    zh = mid(c.get(url(rid)).text)
    card = re.search(r'<section class="card"><h2>下游</h2>.*?</section>', zh, re.S).group(0)
    assert '<span class="later">' not in card
    assert "下游分析於使用者自己的電腦或雲端環境進行，平台不代為執行，也不在 NCHC 登入節點啟動。" in zh
    assert "http://localhost" in zh and "同一台電腦" in zh
    form = re.search(r"<form[^>]*>.*?</form>", zh, re.S).group(0)
    assert 'method="get"' in form and 'action="/"' in form
    assert 'name="run" value="%s"' % rid in form and 'name="stage" value="downstream"' in form and 'name="lang"' not in form
    assert re.search(r'<input type="url"[^>]*name="studio"[^>]*value=""', form) and "開啟連結" in form
    assert "csrf" not in form.lower()
    assert 'role="alert"' not in zh and "target=" not in zh
    # cli-fetch-publish-figure slice 1 (TC-048, TC-049, TC-053): the two commands replace the jupyter and docker lines
    assert "abf-platform studio-connect --server &lt;平台網址&gt;" in zh and "abf-platform fetch-results %s" % rid in zh
    assert "平台不執行腳本" in zh and "請在自己的電腦執行下列指令" in zh
    assert "jupyter lab" not in zh and "docker run" not in zh and "rocker/rstudio" not in zh and "publish-figure" not in zh
    assert "0.0.0.0" not in zh and "-p 8787:8787" not in zh
    assert not re.search(r"<iframe|<img|<script|建議分析|終端機|啟動</button>|停止", card)
    # TC-005: the folder cannot be read yet
    assert "尚未讀取輸出" in zh and 'href="/?run=%s&amp;stage=results&amp;tab=outputs"' % rid in zh and listings(w) == []
    # TC-004: read
    c.get("/?run=%s&stage=results&tab=outputs" % rid)
    finish(w, listings(w)[-1]["id"], entries=ENTRIES)
    n = len(listings(w))
    zh = mid(c.get(url(rid)).text)
    assert "<code>%s/results</code>" % FOLDER in zh and "尚未讀取輸出" not in zh and "拉到自己的電腦" in zh
    assert len(listings(w)) == n
    # TC-002
    en = mid(c.get(url(rid, lang=True)).text)
    en_card = re.search(r'<section class="card"><h2>Downstream</h2>.*?</section>', en, re.S).group(0)
    assert no_cjk(en) and '<span class="later">' not in en_card and "Coming later" not in en_card
    assert 'name="lang" value="en"' in en and 'type="url"' in en and 'name="studio"' in en and "Open link" in en
    assert "abf-platform fetch-results %s" % rid in en and "abf-platform studio-connect --server &lt;platform address&gt;" in en and "<code>%s/results</code>" % FOLDER in en
    assert "jupyter" not in en and "rocker" not in en and "publish-figure" not in en and "The platform does not run scripts" in en


def test_downstream_nonsucceeded_keeps_placeholder(w):
    # TC-006
    ann = w.user("ann")
    ids = [seed(w, "f1", "failed", ann, reason="boom"), seed(w, "r1", "running", ann)]
    c = logged(w)
    for rid in ids:
        zh = mid(c.get(url(rid)).text)
        assert '<span class="later">之後開放</span>' in zh and 'name="studio"' not in zh and "jupyter" not in zh
        assert "fetch-results" not in zh and "studio-connect" not in zh      # TC-052
        en = mid(c.get(url(rid, lang=True)).text)
        assert '<span class="later">Coming later</span>' in en and 'name="studio"' not in en and no_cjk(en)


# ---- TC-007, TC-008, TC-014 ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("studio", ["http://localhost:8787/", "https://rstudio.example.org/s/abc", "https://h/" + "a" * 290,
                                    "http://192.168.1.5:8888/lab", "http://no-such-host.invalid/"])
def test_studio_link_opens_new_tab(w, studio):
    # TC-007 TC-008 TC-014
    assert len(studio) <= 300
    rid, c = succeeded(w)
    r = c.get(url(rid, studio))
    zh = mid(r.text)
    links = re.findall(r"<a [^>]*>", zh)
    new_tab = [a for a in links if "target=" in a]
    assert new_tab == ['<a href="%s" target="_blank" rel="noopener noreferrer">' % studio]
    assert "在新分頁開啟 Studio</a>" in zh and "<code>%s</code>" % studio in zh and "此網址由使用者自行提供，平台不儲存、不檢查其內容。" in zh
    empty = c.get(url(rid))
    for page in (r.text, empty.text):
        assert not re.search(r"<script|<iframe|style=|<img", page) and 'http-equiv="refresh"' not in page
        others = [h for h in re.findall(r'(?:href|src)="([^"]*)"', page) if re.match(r"(https?:)?//", h)]
        assert others == ([studio] if page is r.text else [])
    assert r.headers["content-security-policy"] == c.get("/").headers["content-security-policy"] == empty.headers["content-security-policy"]
    for part in ("default-src 'none'", "form-action 'self'", "frame-ancestors 'none'"):
        assert part in r.headers["content-security-policy"]


# ---- TC-009, TC-010 --------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("lang", [False, True])
@pytest.mark.parametrize("studio", REJECTED)
def test_studio_url_rejected_cases(w, studio, lang, caplog):
    # TC-009
    caplog.set_level(logging.DEBUG)
    rid, c = succeeded(w)
    r = c.get(url(rid, studio, lang))
    assert r.status_code == 200
    m = mid(r.text)
    assert 'target="_blank"' not in r.text
    alerts = re.findall(r'<p class="bad" role="alert">(.*?)</p>', m, re.S)
    assert len(alerts) == 1 and "✗" in alerts[0] and len(plain(alerts[0])) > 8
    if lang:
        assert no_cjk(m)
    for secret in ("token=abc", "pw@", "PASSWORD=x", "key=abc", "secret=abc", "evil.example", "etc/passwd"):
        if secret in studio:
            assert secret not in r.text and secret not in served_log(caplog)


def test_studio_url_is_escaped(w):
    # TC-010
    rid, c = succeeded(w)
    for studio in ['http://h/?a="><script>alert(1)</script>', "http://h/?a=1&b='2'&c=\"3\""]:
        r = c.get(url(rid, studio))
        assert "<script" not in r.text and "&quot;" in mid(r.text)
        if 'target="_blank"' in r.text:
            href = re.search(r'<a href="([^"]*)" target="_blank"', r.text).group(1)
            assert '"' not in href and "<" not in href


# ---- TC-011, TC-012, TC-013 ------------------------------------------------------------------------------------------------------

def dump(w):
    out = {}
    for path in (w.ip.index, w.ip.state_db, w.ip.tokens):
        con = sqlite3.connect(str(path))
        for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
            if name == "web_sessions":
                continue
            rows = con.execute('SELECT * FROM "%s"' % name).fetchall()
            out[(Path(path).name, name)] = hashlib.sha256(repr(sorted(map(repr, rows))).encode()).hexdigest()
        out[(Path(path).name, "schema")] = repr(con.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall())
        con.close()
    return out


def test_nothing_is_stored(w, caplog):
    # TC-011
    from abf_platform import store
    caplog.set_level(logging.DEBUG)
    rid, c = succeeded(w)
    before = dump(w)
    for studio in (None, "https://rstudio.example.org/s/abc-unique", "http://h/?token=hidden-unique"):
        c.get(url(rid, studio))
    assert dump(w) == before
    assert set(store.PREF_DEFAULTS) == {"step_mode", "dev_mode"}
    assert "abc-unique" not in served_log(caplog) and "hidden-unique" not in served_log(caplog)


def test_other_user_and_missing_run_unchanged(w):
    # TC-013
    ann = w.user("ann")
    rid = seed(w, "ann-done", "succeeded", ann)
    w.user("bob")
    c = logged(w, "bob")
    studio = "https://rstudio.example.org/s/abc"
    r = c.get(url(rid, studio))
    assert r.status_code == 404 and studio not in r.text
    r = c.get(url("id-nope", studio))
    assert r.status_code == 404 and studio not in r.text


def test_no_new_route_no_new_action(w):
    # TC-012
    from abf_platform import actions
    app = w.web().app
    assert sorted((r.path, tuple(sorted(r.methods or []))) for r in app.routes) == ROUTES_V3
    names = sorted(n for n in dir(actions) if not n.startswith("_") and callable(getattr(actions, n))
                   and getattr(getattr(actions, n), "__module__", "").startswith("abf_platform.actions"))
    assert names == ACTIONS_V3


def test_style_untouched_and_csp_same(w):
    # TC-008 TC-015
    from abf_platform import web_board
    src = (ROOT.parent / "platform" / "tests" / "test_results_files.py").read_text(encoding="utf-8")
    pinned = re.search(r'^STYLE_SHA256 = "([0-9a-f]{64})"', src, re.M).group(1)
    assert hashlib.sha256(web_board.STYLE.encode("utf-8")).hexdigest() == pinned


def test_no_refresh_on_succeeded_downstream(w):
    # TC-008
    rid, c = succeeded(w)
    for extra in (None, "https://rstudio.example.org/s/abc", "javascript:alert(1)"):
        for lang in (False, True):
            assert 'http-equiv="refresh"' not in c.get(url(rid, extra, lang)).text


# ---- TC-015, TC-016, TC-019 ------------------------------------------------------------------------------------------------------

def test_strings_table_parity_and_wording():
    # TC-016
    from abf_platform import web_downstream as d
    from test_web_wording_sweep import banned_in
    assert set(d.STRINGS["zh"]) == set(d.STRINGS["en"])
    for lang in ("zh", "en"):
        assert all(isinstance(v, str) and v.strip() for v in d.STRINGS[lang].values())
        assert not any("012b" in v or "016" in v for v in d.STRINGS[lang].values())
    assert no_cjk(" ".join(d.STRINGS["en"].values()))
    assert banned_in(" ".join(d.STRINGS["zh"].values())) == []
    src = (ROOT / "abf_platform" / "web_downstream.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(socket|ssl|http|urllib\.request|requests|subprocess|sqlite3|os|pathlib|paramiko)", src, re.M)


def test_board_touches_are_minimal():
    # TC-015
    from abf_platform import web_board
    src = (ROOT / "abf_platform" / "web_board.py").read_text(encoding="utf-8")
    assert len(re.findall(r"^from \. import web_downstream", src, re.M)) == 1
    assert web_board.PLACEHOLDER == ("launch", "downstream")
    import inspect
    for fn in (web_board.render_board, web_board._run_page, web_board._stage_card):
        assert inspect.signature(fn).parameters["studio"].default is None


@pytest.mark.parametrize("lang", [False, True])
def test_wording_in_command_block(w, lang):
    # TC-019
    rid, c = succeeded(w)
    page = mid(c.get(url(rid, None, lang)).text)
    blocks = " ".join(re.findall(r'<pre class="reason">(.*?)</pre>', page, re.S))
    assert "studio-connect" in blocks and "fetch-results" in blocks and "jupyter" not in blocks and "rocker" not in blocks      # TC-049
    assert len(blocks.strip().splitlines()) == 2      # slice 1: the two commands, not the third
    for word in ("password", "token", "AKIA", "sk-", "nchc", "ln01", "sbatch", "srun"):
        assert word.lower() not in blocks.lower()
    rest = LOGIN_NODE_SENTENCE.sub("", page)      # the one sentence that says "not on the NCHC login node" is the only place the name may stand
    for word in ("nchc", "ln01", "sbatch", "srun"):
        assert word not in rest.lower()
    assert len(re.findall(r"<form", page)) == 1 and "<button" in page and page.count("<button") == 1


@pytest.mark.parametrize("lang", ["zh", "en"])
def test_downstream_commands_escape_run_id(lang):
    # TC-051: a run id with < and " cannot make a tag or leave the line
    from abf_platform import web_downstream as d
    page = d.render_downstream(lang, {"id": 'x<b>"y&z'}, None, None, "t")
    assert "<b>" not in page and 'x"y' not in page
    assert "abf-platform fetch-results x&lt;b&gt;&quot;y&amp;z" in page
    if lang == "en":
        assert no_cjk(page)


def test_downstream_strings_for_the_commands_are_in_both_languages_and_pinned_pieces_are_gone():
    # TC-078, TC-049 (the parity and the wording of the whole table are also pinned by test_strings_table_parity_and_wording)
    from abf_platform import web_downstream as d
    assert set(d.STRINGS["zh"]) == set(d.STRINGS["en"])
    assert not hasattr(d, "RM_FLAG") and not hasattr(d, "HOME_RESULTS")
    text = " ".join(d.STRINGS["zh"].values()) + " ".join(d.STRINGS["en"].values())
    assert "jupyter" not in text.lower() and "docker" not in text.lower() and "rocker" not in text.lower()
