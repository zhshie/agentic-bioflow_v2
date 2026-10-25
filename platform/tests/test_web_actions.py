# Nothing existing: tests of spec 012b (write actions from the web, each through the confirmation page); the pages and routes are ours.
"""012b: Resume / Re-run / Cancel buttons and the launch form. Test cases are named in the comments (TC-001 ...),
see specs/012b-web-actions/test-case.md. Runs are launched through the real actions (resume_harness.Rig), not seeded."""
import ast
import html
import re
import sqlite3
import time

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from human_harness import csrf_of
from resume_harness import Rig
from test_web_board import no_cjk, pane, plain, seed, style_of

WEB = PLATFORM_DIR / "abf_platform" / "web.py"
BOARD = PLATFORM_DIR / "abf_platform" / "web_board.py"
SETTINGS_PAGE = PLATFORM_DIR / "abf_platform" / "web_settings.py"
LEDGER = REPO_ROOT / "specs" / "012b-web-actions" / "ledger.md"
GLYPHS = "▶✓✗⏸⟳✎"


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


def area_sheet(w, caller, name="samples.csv"):
    area = w.ip.state_db.parent / "uploads" / caller.name
    return w.move_into_area(w.sheet, area / name, area)


def run_of(rig, caller, run="run-a", status="failed"):
    """A run of this platform launched by `caller` and now `status` in the index ("failed", "succeeded", None = still running)."""
    rig.first(run, caller=caller, samplesheet=area_sheet(rig.w, caller), status=status)
    return "id-" + run


def login(rig, name):
    c = rig.w.web()
    assert rig.w.login(c, name).status_code == 303
    return c


def launch_csrf(text):
    """The token of the launch form (the first token in a page is the log-out form's)."""
    return re.search(r'<form class="lform"[^>]*><input type="hidden" name="csrf" value="([^"]+)"', text).group(1)


def act_form(text, verb, run_id=None):
    for m in re.finditer(r'<form class="act" method="post" action="/act/%s">(.*?)</form>' % verb, text, re.S):
        fields = {k: html.unescape(v) for k, v in re.findall(r'name="(\w+)" value="([^"]*)"', m.group(1))}
        if run_id is None or fields.get("run") == run_id:
            return fields
    return None


def rid_of(response):
    assert response.status_code == 303, response.text
    m = re.fullmatch(r"/c/([0-9a-f]{32})", response.headers["location"])
    assert m, response.headers["location"]
    return m.group(1)


def request_of(rig, rid):
    from abf_platform import actions
    return actions.describe_request(rig.state, rid)


def confirmed(rig):
    return len(rig.sql("SELECT * FROM confirmations WHERE state = 'confirmed'"))


def snapshot(rig):
    return (len(rig.sql("SELECT * FROM jobs")), confirmed(rig), len(rig.launches()))


def pending(rig):
    return len(rig.sql("SELECT * FROM confirmations WHERE state = 'pending'"))


def two_users(rig):
    return rig.user("ann"), rig.user("bob")


# ---- US1: resume, re-run, cancel -------------------------------------------------------------------------------------------------------

def test_tc001_tc003_each_button_asks_and_redirects_to_the_confirmation_page(rig):
    # TC-001, TC-002, TC-003, TC-005
    ann = rig.user("ann")
    failed = run_of(rig, ann, "run-a")
    again = run_of(rig, ann, "run-c")          # a resume and a re-run of the same run cannot both stand: the second is "a newer attempt exists"
    going = run_of(rig, ann, "run-b", status=None)
    c = login(rig, "ann")
    for verb, rid_, name in (("resume", failed, "run-a"), ("relaunch", again, "run-c")):
        fields = act_form(c.get("/?run=" + rid_).text, verb, rid_)
        assert fields and fields["csrf"]
        rid = rid_of(c.post("/act/" + verb, data=fields))
        req = request_of(rig, rid)
        assert req["state"] == "pending" and req["kind"] == "launch" and req["caller_user_id"] == ann.user_id
        assert name in req["summary"] and (name + "-a2") in req["summary"]
    t = c.get("/?run=" + going).text
    fields = act_form(t, "cancel", going)
    assert fields
    rid = rid_of(c.post("/act/cancel", data=fields))
    req = request_of(rig, rid)
    assert req["state"] == "pending" and req["kind"] == "cancel" and req["caller_user_id"] == ann.user_id and "run-b" in req["summary"]
    for page in (c.get("/?run=" + failed).text, c.get("/?run=" + going).text, c.get("/").text):
        assert "aria-disabled" not in page and 'class="gbtn"' not in page


def test_tc004_notices_carry_real_forms(rig):
    # TC-004 (web v2, ruling 5: the notice is on the right; it has exactly one form, the first of the run's actions)
    from abf_platform import actions
    ann = rig.user("ann")
    failed = run_of(rig, ann)
    c = login(rig, "ann")
    verb = actions.get_run(rig.w.ip.index, failed, caller=ann, platform_path=rig.w.ip.state_db)["failure"]["actions"][0]
    for url in ("/", "/?run=" + failed):
        t = c.get(url).text
        right = pane(t, "right")
        notice = re.search(r"<article\b.*?</article>", right, re.S).group(0)
        assert "之後開放" not in notice and len(re.findall(r"<form\b", notice)) == 1
        assert "<article" not in pane(t, "middle")
        fields = act_form(notice, verb, failed)
        assert fields, (url, verb)
        assert rid_of(c.post("/act/" + verb, data=fields))


def test_tc006_tc058_nothing_is_confirmed_or_queued_before_the_person_presses_send(rig):
    # TC-006, TC-058
    ann = rig.user("ann")
    failed = run_of(rig, ann, "run-a")
    again = run_of(rig, ann, "run-c")
    going = run_of(rig, ann, "run-b", status=None)
    c = login(rig, "ann")
    before = snapshot(rig)
    for verb, rid in (("resume", failed), ("relaunch", again), ("cancel", going)):
        t = c.get("/?run=" + rid).text
        rid_of(c.post("/act/" + verb, data=act_form(t, verb, rid)))
    assert snapshot(rig) == before
    assert pending(rig) == 3


def test_tc007_tc009_the_page_press_makes_the_job(rig):
    # TC-007, TC-008, TC-009
    ann = rig.user("ann")
    failed = run_of(rig, ann, "run-a")
    c = login(rig, "ann")
    t = c.get("/?run=" + failed).text
    rid = rid_of(c.post("/act/resume", data=act_form(t, "resume", failed)))
    page = c.get("/c/" + rid)
    assert page.status_code == 200 and "run-a" in page.text and "送出" in page.text
    jobs_before = len(rig.sql("SELECT * FROM jobs"))
    done = c.post("/c/" + rid, data={"csrf": csrf_of(page.text)})
    assert done.status_code == 200 and "工作編號" in done.text
    jobs = rig.sql("SELECT * FROM jobs ORDER BY id DESC")
    assert len(jobs) == jobs_before + 1 and jobs[0]["kind"] == "launch_nextflow"
    assert "run-a-a2" in jobs[0]["args_json"] and rig.w.sql("SELECT user_id FROM launches ORDER BY id DESC")[0][0] == ann.user_id
    again = run_of(rig, ann, "run-c")
    t = c.get("/?run=" + again).text
    rid = rid_of(c.post("/act/relaunch", data=act_form(t, "relaunch", again)))
    jobs_before = len(rig.sql("SELECT * FROM jobs"))
    assert c.post("/c/" + rid, data={"csrf": csrf_of(c.get("/c/" + rid).text)}).status_code == 200
    assert len(rig.sql("SELECT * FROM jobs")) == jobs_before + 1


def test_tc009_cancel_job_after_the_page_press(rig):
    # TC-009
    ann = rig.user("ann")
    going = run_of(rig, ann, "run-b", status=None)
    c = login(rig, "ann")
    rid = rid_of(c.post("/act/cancel", data=act_form(c.get("/?run=" + going).text, "cancel", going)))
    assert c.post("/c/" + rid, data={"csrf": csrf_of(c.get("/c/" + rid).text)}).status_code == 200
    job = rig.sql("SELECT * FROM jobs WHERE kind = 'cancel_run'")
    assert len(job) == 1 and "run-b" in job[0]["args_json"]


def test_tc010_tc011_no_session_goes_to_login(rig):
    # TC-010, TC-011
    ann = rig.user("ann")
    failed = run_of(rig, ann)
    before = snapshot(rig)
    c = rig.w.web()
    for headers in ({}, {"Authorization": "Bearer abf_" + "a" * 32}):
        for verb in ("resume", "relaunch", "cancel"):
            r = c.post("/act/" + verb, data={"run": failed, "csrf": "x"}, headers=headers)
            assert r.status_code == 303 and r.headers["location"] == "/login", (verb, headers)
    assert snapshot(rig) == before and pending(rig) == 0


def test_tc012_another_users_run_is_not_found(rig):
    # TC-012
    ann, bob = two_users(rig)
    failed = run_of(rig, ann)
    c = login(rig, "bob")
    cookie = c.cookies.get("abf_web")
    before = snapshot(rig)
    for verb in ("resume", "relaunch", "cancel"):
        mine = c.app.state.csrf_token(cookie, "act:" + failed)
        other = c.app.state.csrf_token(cookie, "act:nope")
        a = c.post("/act/" + verb, data={"run": failed, "csrf": mine})
        b = c.post("/act/" + verb, data={"run": "nope", "csrf": other})
        assert a.status_code == 404 and (a.status_code, a.content) == (b.status_code, b.content)
        assert failed not in a.text and "run-a" not in a.text
    assert snapshot(rig) == before and pending(rig) == 0


def test_tc013_tc015_csrf_and_origin(rig):
    # TC-013, TC-014, TC-015
    ann = rig.user("ann")
    failed = run_of(rig, ann)
    c = login(rig, "ann")
    good = act_form(c.get("/?run=" + failed).text, "resume", failed)
    for verb in ("resume", "relaunch", "cancel"):
        assert c.post("/act/" + verb, data={"run": failed}).status_code == 403
        assert c.post("/act/" + verb, data={"run": failed, "csrf": "wrong"}).status_code == 403
        assert c.post("/act/" + verb, data=good, headers={"Origin": "https://evil.example"}).status_code == 403
        assert c.post("/act/" + verb, data=good, headers={"Referer": "https://evil.example/x"}).status_code == 403
    assert pending(rig) == 0


def test_tc016_tc018_refusals_are_one_plain_line(rig):
    # TC-016, TC-017, TC-018, TC-019
    ann = rig.user("ann")
    going = run_of(rig, ann, "run-b", status=None)
    failed = run_of(rig, ann, "run-a")
    c = login(rig, "ann")
    r = c.post("/act/resume", data=act_form(c.get("/?run=" + going).text, "resume", going))
    assert r.status_code != 303 and re.search(r'<p class="bad"[^>]*>[^<]*還在跑[^<]*</p>', r.text)
    from abf_platform import actions
    out = actions.forget(rig.state, rig.index, "run-a", confirmed_by=actions.TERMINAL, caller=ann)
    assert out["forgotten"] is True, out
    fields = act_form(c.get("/?run=" + failed).text, "resume", failed)
    for verb in ("resume", "relaunch"):
        r = c.post("/act/" + verb, data=dict(fields))
        assert r.status_code != 303 and re.search(r'<p class="bad"[^>]*>[^<]*已被擁有者刪除[^<]*</p>', r.text), verb
    assert pending(rig) == 0
    # a run the platform did not launch for this person: seeded, no confirmation of theirs behind it
    other = seed(rig.w, "plain-run", "running", ann)
    r = c.post("/act/cancel", data=act_form(c.get("/?run=" + other).text, "cancel", other))
    assert r.status_code != 303 and 'class="bad"' in r.text
    assert pending(rig) == 0


def test_tc019_refusal_is_clean_and_escaped(rig):
    # TC-019
    ann = rig.user("ann")
    seed(rig.w, "<script>x", "failed", ann)
    c = login(rig, "ann")
    rid = "id-<script>x"
    t = c.get("/?run=" + rid).text
    fields = act_form(t, "resume", rid)
    assert fields
    for q in ("", "en"):
        r = c.post("/act/resume", data=dict(fields, lang=q) if q else fields)
        assert r.status_code != 303 and "<script>" not in r.text and "&lt;script&gt;" in r.text
        flash = re.search(r'<p class="bad"[^>]*>(.*?)</p>', r.text, re.S).group(1)
        for bad in ("Traceback", "SELECT", "sqlite", "/f/", ".py"):
            assert bad not in flash, flash
        assert len(plain(flash)) > 10
    assert pending(rig) == 0


# ---- US2: the launch form --------------------------------------------------------------------------------------------------------------

def form_values(rig, c, name, **over):
    """What a person fills in: an uploaded samplesheet of their own, an environment of their own."""
    t = c.get("/launch").text
    csrf = launch_csrf(t)
    sheet = re.search(r'<select name="samplesheet"[^>]*>.*?<option value="([^"]+)"', t, re.S).group(1)
    ce = re.search(r'<select name="ce_name"[^>]*>.*?<option value="([^"]+)"', t, re.S).group(1)
    data = {"csrf": csrf, "pipeline": "nf-core/ampliseq", "revision": "2.18.0", "run_name": "web-run", "samplesheet": html.unescape(sheet),
            "ce_name": html.unescape(ce), "params": ""}
    data.update(over)
    return data


def test_tc020_the_form_has_the_fields(rig):
    # TC-020, TC-051, TC-052
    ann = rig.user("ann")
    area_sheet(rig.w, ann)
    c = login(rig, "ann")
    t = c.get("/launch").text
    mid = pane(t, "middle") if "data-pane" in t else t
    for name in ("pipeline", "revision", "run_name"):
        assert re.search(r'<input [^>]*name="%s"' % name, t)
    assert re.search(r'<input [^>]*name="revision"[^>]*required', t)
    assert re.search(r'<select name="samplesheet"', t) and re.search(r'<select name="ce_name"', t) and re.search(r'<textarea [^>]*name="params"', t)
    assert 'type="file"' not in t and "multipart" not in t and "<ol" not in t and "<svg" not in t and "<canvas" not in t
    assert len(re.findall(r'<details class="gstep ', mid)) == 7      # guided-launch-1: the page is seven numbered steps (was: no step numbering)


def test_tc021_tc022_choices_are_the_callers_own(rig):
    # TC-021, TC-022
    ann, bob = two_users(rig)
    area_sheet(rig.w, ann, "ann-sheet.csv")
    area_sheet(rig.w, bob, "bob-sheet.csv")
    rig.w.env_for(bob)
    t = login(rig, "ann").get("/launch").text
    assert "ann-sheet.csv" in t and "bob-sheet.csv" not in t
    assert "lab-a" in t and "lab-bob" not in t
    t = login(rig, "bob").get("/launch").text
    assert "bob-sheet.csv" in t and "ann-sheet.csv" not in t
    assert "lab-bob" in t and 'value="lab-a"' not in t


def test_tc023_tc025_a_valid_form_asks_then_the_page_launches(rig):
    # TC-023, TC-024, TC-025
    ann = rig.user("ann")
    area_sheet(rig.w, ann)
    c = login(rig, "ann")
    before = snapshot(rig)
    r = c.post("/launch", data=form_values(rig, c, "ann", params="min_reads: 100\nprimer: AGRG"))
    rid = rid_of(r)
    req = request_of(rig, rid)
    assert req["state"] == "pending" and req["caller_user_id"] == ann.user_id
    for word in ("nf-core/ampliseq", "2.18.0", "web-run", "min_reads", "100", "primer", "AGRG"):
        assert word in req["summary"], word
    assert "pacbio" not in req["summary"]
    assert snapshot(rig) == before
    page = c.get("/c/" + rid)
    assert c.post("/c/" + rid, data={"csrf": csrf_of(page.text)}).status_code == 200
    jobs = rig.sql("SELECT * FROM jobs WHERE kind = 'launch_nextflow'")
    assert len(jobs) == 1 and "web-run" in jobs[0]["args_json"] and rig.w.sql("SELECT user_id FROM launches WHERE run_name = 'web-run'")[0][0] == ann.user_id


def test_tc026_tc028_quick_launch(rig):
    # TC-026, TC-027, TC-028, TC-049
    ann, bob = two_users(rig)
    failed = run_of(rig, ann, "run-a")
    area_sheet(rig.w, ann, "other.csv")
    c = login(rig, "ann")
    t = c.get("/launch?from=" + failed).text
    assert re.search(r'name="pipeline"[^>]*value="nf-core/ampliseq"', t) and re.search(r'name="revision"[^>]*value="2.18.0"', t)
    assert re.search(r'<option value="lab-a" selected', t)
    params = html.unescape(re.search(r'<textarea [^>]*name="params"[^>]*>(.*?)</textarea>', t, re.S).group(1))
    assert "primer: AGRG" in params and "pacbio: true" in params and "depth: 3" in params
    when = rig.sql("SELECT confirmed_at FROM launches WHERE run_name = 'run-a'")[0][0]
    import datetime
    taipei = (datetime.datetime.utcfromtimestamp(when) + datetime.timedelta(hours=8)).strftime("%m-%d %H:%M")
    assert taipei in plain(t)
    theirs = login(rig, "bob")
    a, b = theirs.get("/launch?from=" + failed), theirs.get("/launch?from=nope")
    assert a.status_code == 404 and (a.status_code, a.content) == (b.status_code, b.content) and "AGRG" not in a.text
    from abf_platform import actions
    assert actions.forget(rig.state, rig.index, "run-a", confirmed_by=actions.TERMINAL, caller=ann)["forgotten"] is True
    r = c.get("/launch?from=" + failed)
    assert r.status_code == 200 and "沒有保留" in r.text and "AGRG" not in r.text and "nf-core/ampliseq" not in re.sub(r"<[^>]+>", "", r.text).replace("管線", "")
    assert not re.search(r'name="revision"[^>]*value="[^"]', r.text)


def invalid(rig, c, expect, **over):
    before = (pending(rig), snapshot(rig))
    r = c.post("/launch", data=form_values(rig, c, "ann", **over))
    assert r.status_code != 303 and re.search(r'<p class="bad"[^>]*>', r.text), r.text
    assert expect in r.text, (expect, re.findall(r'<p class="bad"[^>]*>(.*?)</p>', r.text))
    assert (pending(rig), snapshot(rig)) == before
    return r


def test_tc029_tc033_validation_makes_no_request(rig):
    # TC-029, TC-030, TC-031, TC-032, TC-033
    ann, bob = two_users(rig)
    area_sheet(rig.w, ann)
    area_sheet(rig.w, bob, "bob-sheet.csv")
    rig.w.env_for(bob)
    c = login(rig, "ann")
    invalid(rig, c, "版本", revision="")
    invalid(rig, c, "版本", revision="   ")
    invalid(rig, c, "運算環境", ce_name="no-such-env")
    invalid(rig, c, "運算環境", ce_name="lab-bob")
    for sheet in ("bob-sheet.csv", "../bob/bob-sheet.csv", "/etc/passwd", str(rig.w.sheet)):
        invalid(rig, c, "樣本表", samplesheet=sheet)
    invalid(rig, c, "bad", params="bad: [1,2]")
    invalid(rig, c, "nested", params="nested: {a: b}")
    invalid(rig, c, "oops", params="oops")
    run_of(rig, ann, "run-a")
    invalid(rig, c, "已用過", run_name="run-a")


def test_tc034_tc036_login_csrf_origin_on_launch(rig):
    # TC-034, TC-035, TC-036
    ann = rig.user("ann")
    area_sheet(rig.w, ann)
    anon = rig.w.web()
    g = anon.get("/launch")
    assert g.status_code == 303 and g.headers["location"] == "/login"
    p = anon.post("/launch", data={"pipeline": "x"})
    assert p.status_code == 303 and p.headers["location"] == "/login"
    c = login(rig, "ann")
    good = form_values(rig, c, "ann")
    no_token = {k: v for k, v in good.items() if k != "csrf"}
    assert c.post("/launch", data=no_token).status_code == 403
    assert c.post("/launch", data=dict(good, csrf="wrong")).status_code == 403
    assert c.post("/launch", data=good, headers={"Origin": "https://evil.example"}).status_code == 403
    assert pending(rig) == 0


# ---- US3: parity, words, front-end limits ------------------------------------------------------------------------------------------------

def test_tc040_tc041_banned_words_are_nowhere_in_platform():
    # TC-040, TC-041
    banned = ("要你" + "處理", "需要" + "處理")
    hits = []
    for p in PLATFORM_DIR.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".md", ".txt", ".html", ".sh", ".toml", ".json") and ".venv" not in p.parts and "build" not in p.parts:
            text = p.read_text(encoding="utf-8", errors="replace")
            hits += [(p.name, w) for w in banned if w in text]
    assert hits == []


def test_tc042_tc043_pending_pill_and_empty_lines(rig):
    # TC-042, TC-043
    ann = rig.user("ann")
    failed = run_of(rig, ann)
    c = login(rig, "ann")
    for url, word in (("/", "待處理"), ("/?run=" + failed, "待處理"), ("/?lang=en", "Pending"), ("/?run=%s&lang=en" % failed, "Pending")):
        t = c.get(url).text
        assert re.search(r'<span class="level state-failed">.*?%s' % word, t, re.S), url
        assert "需要" + "處理" not in t and "Action needed" not in t
    ok = run_of(rig, ann, "run-ok", status=None)
    t = c.get("/?run=" + ok).text
    assert "目前沒有待處理的事" in t and ("要你" + "處理") not in t
    assert "Nothing pending" in c.get("/?run=%s&lang=en" % ok).text
    assert "—" in c.get("/").text


def test_tc044_tc045_status_is_a_square_plus_a_word_and_no_new_glyph(rig):
    # TC-044, TC-045
    ann = rig.user("ann")
    pages = {"failed": run_of(rig, ann, "run-f"), "succeeded": run_of(rig, ann, "run-s", status="succeeded"),
             "running": run_of(rig, ann, "run-r", status=None)}
    c = login(rig, "ann")
    words = {"failed": "Failed", "succeeded": "Done", "running": "Running"}
    for st, rid in pages.items():
        t = c.get("/launch?from=%s&lang=en" % rid).text
        m = re.search(r'<span class="chip state-%s"><span class="sq"></span> ?%s</span>' % (st, words[st]), t)
        assert m, (st, t[:300])
        assert not any(g in m.group(0) for g in GLYPHS + "?!")
    t = c.get("/?lang=en").text
    pill = re.search(r'<span class="level state-failed"><span class="sq"></span>[^<]*</span>', t).group(0)
    assert '<span class="sq"></span>' in pill and "Pending" in pill and not any(g in pill for g in GLYPHS + "?!")
    ledger = LEDGER.read_text(encoding="utf-8")
    for g in "▶✓✗⏸":
        assert g in ledger


def test_tc046_tc048_new_pages_have_no_script_one_stylesheet_and_both_languages(rig):
    # TC-046, TC-047, TC-048
    from abf_platform import web_board
    ann = rig.user("ann")
    failed = run_of(rig, ann)
    c = login(rig, "ann")
    fields = act_form(c.get("/?run=" + failed).text, "resume", failed)
    urls = ["/launch", "/launch?lang=en", "/launch?from=" + failed, "/?run=" + failed, "/?run=%s&lang=en" % failed, "/"]
    pages = [c.get(u) for u in urls] + [c.post("/launch", data={"csrf": launch_csrf(c.get("/launch").text), "revision": ""}),
                                         c.post("/act/resume", data=dict(fields, run="nope"))]
    for r in pages:
        t = r.text
        assert "<script" not in t and not re.search(r"\son\w+=", t) and "style=" not in t and len(re.findall(r"<style\b", t)) == 1 and "<link" not in t
        csp = r.headers["content-security-policy"]
        assert web_board.style_source() in csp and "script-src" not in csp and "'unsafe-inline'" not in csp
    for u in ("/launch?lang=en", "/launch?from=%s&lang=en" % failed, "/?run=%s&lang=en" % failed):
        t = c.get(u).text
        assert no_cjk(t), (u, re.findall(r"[一-鿿]+", t))
    t = c.get("/?run=%s&lang=en" % failed).text
    for word in ("Resume", "Re-run", "Cancel"):
        assert re.search(r"<button[^>]*>%s</button>" % word, t), word
    en = c.post("/launch", data={"csrf": launch_csrf(c.get("/launch").text), "revision": "", "lang": "en"})
    assert en.status_code != 403 and no_cjk(en.text) and re.search(r'<p class="bad"', en.text)


def test_tc046_english_refusal_has_no_chinese(rig):
    # TC-048
    ann = rig.user("ann")
    going = run_of(rig, ann, "run-b", status=None)
    c = login(rig, "ann")
    fields = act_form(c.get("/?run=%s&lang=en" % going).text, "resume", going)
    assert fields["lang"] == "en"
    r = c.post("/act/resume", data=fields)
    assert r.status_code != 303 and no_cjk(r.text) and re.search(r'<p class="bad"[^>]*>[A-Z][^<]*\. Nothing was sent\.</p>', r.text)


def test_tc050_old_tests_changed_only_in_words_are_in_the_ledger():
    # TC-050
    ledger = LEDGER.read_text(encoding="utf-8")
    for needle in ("test_web_running.py", "test_web_board.py", "test_tc146", "test_tc150", "test_r103"):
        assert needle in ledger, needle


def test_tc051_tc056_nothing_out_of_scope_exists(rig):
    # TC-051, TC-053, TC-054, TC-055, TC-056
    ann = rig.user("ann")
    failed = run_of(rig, ann)
    c = login(rig, "ann")
    paths = {r.path for r in c.app.routes}
    assert not [p for p in paths if re.search(r"upload|cost|chat|forget|samplesheet|delete", p)]
    for p in ("/upload", "/cost", "/chat", "/forget", "/resume", "/rerun", "/relaunch", "/cancel", "/run/%s/resume" % failed):
        assert c.get(p).status_code == 404 and c.post(p).status_code in (404, 405), p
    t = c.get("/?run=" + failed).text
    assert "forget" not in t.lower() and "刪除" not in t and "<textarea" not in t and "<input" in t
    assert "SU —" in t


def test_tc057_the_stylesheet_adds_no_new_values(rig):
    # TC-057
    ann = rig.user("ann")
    css = style_of(login(rig, "ann").get("/launch").text)
    assert set(re.findall(r"font-size:([^;}]+)", css)) <= {"12px", "13px", "15px", "16px", "22px", "inherit"}
    assert set(re.findall(r"border-radius:([^;}]+)", css)) <= {"0", "4px", "6px", "999px"}
    for prop, val in re.findall(r"(?<![-\w])((?:padding|margin|gap|row-gap|column-gap)(?:-(?:top|right|bottom|left))?):([^;}]+)", css):
        for px in re.findall(r"(-?\d+(?:\.\d+)?)px", val):
            assert px in ("0", "4", "8", "12", "16", "24"), (prop, val)
    for sel in re.findall(r"\.sq\{[^}]*\}", css):
        assert not re.search(r"#[0-9a-f]{3,6}", sel), sel      # a colour comes from a token, never a new value


# ---- constitution and safety net -------------------------------------------------------------------------------------------------------

def test_tc059_another_user_cannot_press_send_for_a_web_made_request(rig):
    # TC-059
    ann, bob = two_users(rig)
    failed = run_of(rig, ann)
    c = login(rig, "ann")
    rid = rid_of(c.post("/act/resume", data=act_form(c.get("/?run=" + failed).text, "resume", failed)))
    d = login(rig, "bob")
    cookie = d.cookies.get("abf_web")
    before = len(rig.sql("SELECT * FROM jobs"))
    r = d.post("/c/" + rid, data={"csrf": d.app.state.csrf_token(cookie, rid)})
    assert r.status_code == 403 and len(rig.sql("SELECT * FROM jobs")) == before
    assert d.get("/c/" + rid).status_code == 403


def test_tc060_routes_call_only_the_request_actions():
    # TC-060
    forbidden_imports = {"confirm", "jobs", "compute_envs", "agents", "status"}
    for p in (WEB, BOARD, SETTINGS_PAGE):      # settings-page: web_settings.py is held to the same rule
        tree = ast.parse(p.read_text(encoding="utf-8"))
        called = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "actions"}
        assert not (called & {"launch", "cancel", "forget", "request_forget", "void_request", "find_approved"}), (p.name, called)
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                imports |= {a.name for a in n.names} | set((n.module or "").split("."))
        assert not (imports & forbidden_imports), p.name
    web = ast.parse(WEB.read_text(encoding="utf-8"))
    calls = {}

    def walk(node, inside):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inside = node.name
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "actions":
            calls.setdefault(node.attr, set()).add(inside)
        for child in ast.iter_child_nodes(node):
            walk(child, inside)
    walk(web, None)
    assert calls["approve"] == {"confirm_post"}
    assert {"request_launch", "request_cancel", "request_resume", "request_relaunch"} <= set(calls)
    assert not any(n in calls for n in ("launch", "cancel"))


def test_tc062_no_secret_is_in_any_response(rig, caplog):
    # TC-062
    ann = rig.user("ann")
    failed = run_of(rig, ann)
    c = login(rig, "ann")
    key = (rig.state.parent / "web_signing.key").read_bytes().strip().decode()
    cookie = c.cookies.get("abf_web")
    fields = act_form(c.get("/?run=" + failed).text, "resume", failed)
    responses = [c.get("/launch"), c.get("/?run=" + failed), c.post("/act/resume", data=fields), c.post("/act/resume", data={"run": failed}),
                 c.post("/act/resume", data=dict(fields), headers={"Origin": "https://evil.example"}),
                 c.post("/launch", data={"csrf": launch_csrf(c.get("/launch").text), "revision": ""})]
    from human_harness import PASSWORD
    for r in responses:
        blob = r.text + str(r.headers)
        for secret in (key, cookie.split(".")[0], cookie, PASSWORD):
            assert secret not in blob.replace("set-cookie", "")
    assert key not in caplog.text and PASSWORD not in caplog.text


SCHEMA = {
    'platform.agents': ('name', 'version', 'first_seen_at', 'last_seen_at', 'slurm_account', 'facts_json', 'owner_user_id'),
    'platform.compute_envs': ('id', 'name', 'description', 'platform', 'credentials_id', 'agent', 'status', 'message', 'is_primary', 'checked_ok', 'config_json', 'created_at', 'updated_at', 'last_used_at', 'owner_user_id'),
    'platform.confirmations': ('id', 'sha256', 'kind', 'created_at', 'used_at', 'caller_user_id', 'state', 'channel', 'confirmed_at', 'expires_at', 'ce_name', 'bundle_json', 'screen_text', 'void_reason', 'forgotten_at', 'forgotten_by'),
    'platform.jobs': ('id', 'agent', 'compute_env', 'kind', 'args_json', 'state', 'result_json', 'late_result_json', 'created_at', 'deadline_at', 'claimed_at', 'finished_at', 'forgotten_at', 'forgotten_by', 'confirmation_id'),
    'platform.launches': ('id', 'run_name', 'slurm_job_id', 'run_folder', 'ce', 'agent', 'confirmed_at', 'submitted_at', 'cancel_requested_at', 'job_id', 'user_id', 'parent_run', 'attempt', 'attempt_kind', 'work_cleaned_at'),
    'platform.meta': ('key', 'value'),
    'tokens.oauth_clients': ('client_id', 'info_json', 'created_at', 'last_used_at'),
    'tokens.oauth_codes': ('code_hash', 'grant_id', 'client_id', 'redirect_uri', 'redirect_explicit', 'code_challenge', 'resource', 'user_id', 'created_at', 'expires_at', 'used_at'),
    'tokens.oauth_requests': ('id', 'client_id', 'redirect_uri', 'redirect_explicit', 'code_challenge', 'state', 'resource', 'created_at', 'expires_at', 'decision', 'decided_at'),
    'tokens.tokens': ('id', 'token_hash', 'created_at', 'kind', 'agent_name', 'revoked_at', 'run_name', 'expires_at', 'ended_at', 'user_id', 'label', 'grant_id'),
    'tokens.users': ('id', 'name', 'lab', 'created_at', 'disabled_at', 'password_hash', 'temp_until'),     # temp-password: one new column
    'tokens.web_sessions': ('id_hash', 'user_id', 'created_at', 'expires_at'),
    'tokens.cloud_caps': ('user_id', 'cap_usd', 'set_at'),      # this table is cloud-cost's: one monthly cap per person, set only on the administrator's terminal
}      # the schema as 011b left it, plus the one table above


def test_tc063_no_schema_change(rig):
    # TC-063: no migration, no new table or column (except tokens.cloud_caps, added by cloud-cost; see SCHEMA)
    rig.user("ann")
    got = {}
    for label, path in (("platform", rig.state), ("tokens", rig.w.ip.tokens)):
        con = sqlite3.connect(str(path))
        for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
            got["%s.%s" % (label, name)] = tuple(r[1] for r in con.execute("PRAGMA table_info(%s)" % name))
        con.close()
    assert got == SCHEMA, got
