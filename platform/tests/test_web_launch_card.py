# Nothing existing: tests of the launch stage card (issue #387); the card is ours, it replaces the grey "coming later" line.
"""launch-stage-card: test cases are named in the comments (TC-001 ...), see specs/launch-stage-card/test-case.md."""
import calendar
import json
import re
import sqlite3
import time
import urllib.parse

import pytest

from human_harness import World
from test_web_board import cjk, no_cjk, pane, plain, seed, style_of
from test_web_live_sync import content, live, names_of, snapshot, version

LAUNCHED = calendar.timegm((2027, 1, 15, 8, 0, 0))      # 2027-01-15 08:00 UTC = 01-15 16:00 in Taipei
JOB = 4417                                              # the platform job number (jobs.id) the confirmation page named
SLURM = 9876543                                         # the site scheduler's number: never shown
PARAMS = {"genome": "GRCh38", "skip_qc": True}
SHEET = [{"sample": "sample", "fastq_1": "fastq_1"}] + [{"sample": "s%d" % i, "fastq_1": "s%d.fq" % i} for i in range(3)]
INTERNAL = ("012b", "016", "011", "017", "#387", "#349", "#339")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def sent(w, name="ann-run", status="running", who="ann", params=PARAMS, sheet=SHEET, pipeline="nf-core/rnaseq", revision="3.14.0",
         job=True, kept=True, job_state="done", result=None, finished=None, owner=None, run_id=None, **kw):
    """A run the platform sent: the run in the index, its hand-off row (confirmed at LAUNCHED), the confirmation that holds what was sent and its job."""
    user = owner or w.user(who)
    rid = seed(w, name, status, user, run_id=run_id, **kw)
    bundle = {"pipeline": pipeline, "revision": revision, "params": dict(params), "samplesheet": sheet, "run_name": name}
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, state, channel, confirmed_at, ce_name, bundle_json, caller_user_id) "
                    "VALUES (?, 'abc', 'launch', ?, 'confirmed', 'WEB', ?, 'lab-a', ?, ?)",
                    ("c-" + name, LAUNCHED - 5, LAUNCHED, json.dumps(bundle) if kept else None, user.user_id))
        con.execute("UPDATE launches SET confirmed_at = ?, slurm_job_id = ?, run_folder = ? WHERE run_name = ?", (LAUNCHED, SLURM, "/f/" + name, name))
        if job:
            con.execute("INSERT INTO jobs (id, agent, compute_env, kind, args_json, state, result_json, created_at, deadline_at, finished_at, confirmation_id) "
                        "VALUES (?, 'agent-t', 'lab-a', 'launch_nextflow', '{}', ?, ?, ?, ?, ?, ?)",
                        (JOB, job_state, json.dumps(result) if result else None, LAUNCHED, w.clock.t + 3600 if job_state in ("queued", "claimed") else LAUNCHED + 60,
                         finished, "c-" + name))
            con.execute("UPDATE launches SET job_id = ? WHERE run_name = ?", (JOB, name))
        else:
            con.execute("UPDATE launches SET job_id = ? WHERE run_name = ?", (JOB + 1, name))
    con.close()
    return user, rid


def forget(w, name):
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET forgotten_at = ?, bundle_json = NULL WHERE id = ?", (time.time(), "c-" + name))
    con.close()


def log_in(w, who="ann"):
    c = w.web()
    assert w.login(c, who).status_code == 303
    return c


def url(rid, lang=""):
    return "/?run=%s&stage=launch%s" % (rid, "&lang=en" if lang else "")


def middle(text):
    return pane(text, "middle")


def card(text, title="送出"):
    m = re.search(r'<section class="card"><h2>%s</h2>(.*?)</section>' % re.escape(title), middle(text), re.S)
    assert m, middle(text)
    return m.group(1)


def rows(text, lang=""):
    return {plain(k): plain(v) for k, v in re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", card(text, "Launch" if lang else "送出"), re.S)}


ZH = ("管線", "版本", "樣本數", "已變更的參數", "送出時間", "工作編號", "狀態")
EN = ("Pipeline", "Version", "Samples", "Changed parameters", "Launched", "Job number", "Status")


def test_tc001_the_card_shows_what_was_sent(w):
    # TC-001
    _, rid = sent(w, status="succeeded")
    c = log_in(w)
    t = c.get(url(rid)).text
    r = rows(t)
    assert list(r) == list(ZH)
    assert r["管線"] == "nf-core/rnaseq" and r["版本"] == "3.14.0" and r["樣本數"] == "3"
    assert "genome: GRCh38" in r["已變更的參數"] and "skip_qc: true" in r["已變更的參數"]
    assert "之後開放" not in card(t) and "該次分析尚未進行至此階段" not in card(t)
    assert re.search(r'<section class="card"><h2>送出</h2>', middle(t))


def test_tc002_english(w):
    # TC-002
    _, rid = sent(w, status="succeeded")
    t = log_in(w).get(url(rid, "en")).text
    r = rows(t, "en")
    assert list(r) == list(EN)
    assert r["Pipeline"] == "nf-core/rnaseq" and r["Version"] == "3.14.0" and r["Samples"] == "3"
    assert "genome: GRCh38" in r["Changed parameters"] and "skip_qc: true" in r["Changed parameters"]
    assert no_cjk(middle(t)), cjk(middle(t))
    assert "Coming later" not in card(t, "Launch")


def test_tc003_the_time_is_the_time_send_was_pressed(w):
    # TC-003
    _, rid = sent(w, status="succeeded")
    c = log_in(w)
    for lang in ("", "en"):
        t = c.get(url(rid, lang)).text
        assert rows(t, lang)["Launched" if lang else "送出時間"] == "01-15 16:00"
    assert "01-15 16:00" in plain(card(c.get("/?run=%s&stage=finished" % rid).text, "來源紀錄"))      # the finished stage shows the same value


def test_tc004_a_fixed_moment_never_relative(w):
    # TC-004
    _, rid = sent(w, status="succeeded")
    c = log_in(w)
    seen = []
    for later in (5 * 60, 3 * 86400):
        w.clock.t = LAUNCHED + later
        c = log_in(w)      # the session of the first look is long over after three days
        for lang in ("", "en"):
            t = c.get(url(rid, lang)).text
            seen.append(rows(t, lang)["Launched" if lang else "送出時間"])
            for word in ("分鐘前", "小時前", "天前", "ago", "minutes", "hours"):
                assert word not in card(t, "Launch" if lang else "送出"), word
    assert set(seen) == {"01-15 16:00"}


def test_tc005_the_job_number_is_the_platform_one(w):
    # TC-005
    _, rid = sent(w, status="succeeded")
    c = log_in(w)
    zh, en = c.get(url(rid)).text, c.get(url(rid, "en")).text
    assert rows(zh)["工作編號"] == str(JOB) and rows(en, "en")["Job number"] == str(JOB)
    for t in (zh, en):
        assert str(SLURM) not in t and "Slurm" not in card(t, "送出" if t is zh else "Launch")


@pytest.mark.parametrize("status,zh,en", [("running", "執行中", "Running"), ("succeeded", "完成", "Done"), ("failed", "失敗", "Failed"), ("lost", "失敗", "Failed")])
def test_tc006_to_tc009_the_status_is_the_one_of_the_header(w, status, zh, en):
    # TC-006, TC-007, TC-008, TC-009, TC-035
    _, rid = sent(w, status=status)
    c = log_in(w)
    t = c.get(url(rid)).text
    assert rows(t)["狀態"] == zh
    assert re.search(r'<span class="badge state-[a-z]+"><span class="sq"></span> %s</span>' % zh, middle(t))
    e = c.get(url(rid, "en")).text
    assert rows(e, "en")["Status"] == en and no_cjk(middle(e))
    assert re.search(r'<span class="badge state-[a-z]+"><span class="sq"></span> %s</span>' % en, middle(e))


def test_tc010_no_queued_word_and_the_waiting_page_is_not_this_card(w):
    # TC-010
    _, rid = sent(w, status="running", job_state="queued")
    c = log_in(w)
    for lang in ("", "en"):
        t = c.get(url(rid, lang)).text
        assert "排隊中" not in t and "Queued" not in t and "queued" not in t.lower().replace("queued_", "")
        assert rows(t, lang)["Status" if lang else "狀態"] in ("執行中", "Running")
    wait = c.get("/?run_name=never-indexed")
    assert wait.status_code in (200, 404) and "工作編號" not in wait.text


def test_tc011_the_refusal_stays_above_and_the_card_does_not_repeat_it(w):
    # TC-011
    reason = "站台目前沒有這個管線的資源"
    ann, rid = sent(w, status="running", job_state="refused", result={"message": reason}, finished=w.clock.t - 60)
    t = log_in(w).get(url(rid)).text
    assert '<section id="refusal">' in t and reason in t.split('<section id="refusal">')[1].split("</section>")[0]
    assert reason not in card(t)
    assert "退回" not in card(t) and "refus" not in card(t).lower()
    assert rows(t)["管線"] == "nf-core/rnaseq"


def test_tc012_english_refusal(w):
    # TC-012
    reason = "The site has no resources for this pipeline."
    _, rid = sent(w, status="running", job_state="refused", result={"message": reason}, finished=w.clock.t - 60)
    t = log_in(w).get(url(rid, "en")).text
    assert '<section id="refusal">' in t and reason in t
    assert reason not in card(t, "Launch") and no_cjk(middle(t))


def test_tc013_a_run_the_platform_did_not_send(w, monkeypatch):
    # TC-013, TC-034 (a run with no hand-off row is nobody's, so its page would be 404: the answer "no record of a launch" is given to the page directly)
    from abf_platform import actions
    ann = w.user("ann")
    rid = seed(w, "foreign", "succeeded", ann)
    monkeypatch.setattr(actions, "launch_prefill", lambda *a, **k: {"found": False, "kept": False})
    c = log_in(w)
    for lang in ("", "en"):
        r = c.get(url(rid, lang))
        assert r.status_code == 200
        cells = rows(r.text, lang)
        assert list(cells) == list(EN if lang else ZH)
        assert [v for k, v in cells.items() if k not in ("Status", "狀態")] == ["—"] * 6, cells
        assert "之後開放" not in card(r.text, "Launch" if lang else "送出") and "Coming later" not in card(r.text, "Launch" if lang else "送出")


def test_tc014_content_deleted_leaves_dashes_a_note_and_the_time(w):
    # TC-014, TC-034
    _, rid = sent(w, status="succeeded")
    forget(w, "ann-run")
    c = log_in(w)
    t = c.get(url(rid)).text
    r = rows(t)
    assert [r[k] for k in ("管線", "版本", "樣本數", "已變更的參數")] == ["—"] * 4 and r["送出時間"] == "01-15 16:00"
    assert "該次送出的內容已不保留。" in card(t)
    e = c.get(url(rid, "en")).text
    assert "The content of this launch is no longer kept." in card(e, "Launch") and no_cjk(middle(e))


def test_tc015_no_changed_parameter(w):
    # TC-015
    _, rid = sent(w, status="succeeded", params={})
    c = log_in(w)
    assert "沿用預設" in rows(c.get(url(rid)).text)["已變更的參數"]
    assert "All parameters use their defaults" in rows(c.get(url(rid, "en")).text, "en")["Changed parameters"]


def test_tc016_no_platform_job_leaves_a_dash_and_no_slurm_number(w):
    # TC-016, TC-034
    _, rid = sent(w, status="succeeded", job=False)
    c = log_in(w)
    r = rows(c.get(url(rid)).text)
    assert r["工作編號"] == "—" and r["管線"] == "nf-core/rnaseq" and r["樣本數"] == "3"
    assert str(SLURM) not in c.get(url(rid)).text


def test_tc017_somebody_elses_run(w):
    # TC-017
    _, rid = sent(w, status="succeeded", who="ann")
    w.user("zed")
    r = log_in(w, "zed").get(url(rid))
    assert r.status_code == 404
    for word in ("nf-core/rnaseq", "3.14.0", "GRCh38", "skip_qc"):
        assert word not in r.text


def test_tc018_downstream_is_still_a_placeholder(w):
    # TC-018
    _, rid = sent(w, status="running")
    c = log_in(w)
    zh = middle(c.get("/?run=%s&stage=downstream" % rid).text)
    en = middle(c.get("/?run=%s&stage=downstream&lang=en" % rid).text)
    assert '<span class="later">之後開放</span>' in zh and '<span class="later">Coming later</span>' in en
    for t in (zh, en):
        assert "GRCh38" not in t and "工作編號" not in t and "Job number" not in t


def test_tc019_finished_stage_not_reached_is_unchanged(w):
    # TC-019
    _, rid = sent(w, status="failed")
    assert "該次分析尚未進行至此階段。" in middle(log_in(w).get("/?run=%s&stage=finished" % rid).text)


@pytest.mark.parametrize("status", ["running", "succeeded", "failed", "lost"])
def test_tc020_no_internal_ticket_numbers(w, status):
    # TC-020
    _, rid = sent(w, status=status)
    c = log_in(w)
    for lang in ("", "en"):
        t = middle(c.get(url(rid, lang)).text)
        for word in INTERNAL:
            assert word not in t, word


def test_tc021_the_stage_strip_is_unchanged(w):
    # TC-021
    _, rid = sent(w, status="running")
    t = middle(log_in(w).get(url(rid)).text)
    cells = re.findall(r'<li\b[^>]*data-step="([a-z]+)"[^>]*>(.*?)</li>', t, re.S)
    assert [s for s, _ in cells] == ["launch", "running", "results", "downstream", "finished"]
    launch = dict(cells)["launch"]
    assert 'aria-current="step"' in launch
    assert all('aria-current="step"' not in v for s, v in cells if s != "launch")
    assert '<span></span><a rel="next" href="/?run=%s&amp;stage=running">' % rid in t.replace("\n", "") or 'rel="next" href="/?run=%s&amp;stage=running"' % rid in t
    assert 'rel="prev"' not in t


def test_tc024_the_card_is_inside_a_live_region_and_follows_the_run(w):
    # TC-024
    _, rid = sent(w, status="running")
    c = log_in(w)
    u = url(rid)
    a = version(c, u).json()
    con = sqlite3.connect(str(w.ip.index))
    with con:
        con.execute("UPDATE runs SET final_status = 'succeeded', ended_at = ? WHERE id = ?", (LAUNCHED + 100, rid))
    con.close()
    b = version(c, u).json()
    assert a != b and a["s"] == "ok" and b["s"] == "ok"
    got = content(c, u, names_of(b)).json()
    regions = [h for h in got["r"].values() if "<h2>送出</h2>" in h]
    assert len(regions) == 1 and "完成" in re.search(r"<dt>狀態</dt><dd>(.*?)</dd>", regions[0], re.S).group(1)
    page = c.get(u).text
    assert "<h2>送出</h2>" in page and page.index("<h2>送出</h2>") > page.index('data-pane="middle"')
    lay = live().layout(page)
    assert any("<h2>送出</h2>" in r["html"] for cont in lay for r in cont["regions"])


def test_tc025_a_look_writes_nothing_and_queues_nothing(w):
    # TC-025
    _, rid = sent(w, status="running")
    c = log_in(w)
    u = url(rid)
    before = snapshot(w)
    count = len(w.sql("SELECT * FROM jobs"))
    for _ in range(3):
        v = version(c, u)
        assert v.status_code == 200
        assert content(c, u, names_of(v.json())).status_code == 200
    assert snapshot(w) == before and len(w.sql("SELECT * FROM jobs")) == count


def classes_in(html_text):
    return {k for m in re.findall(r'class="([^"]*)"', html_text) for k in m.split()}


def test_tc026_only_existing_css_classes(w):
    # TC-026
    from abf_platform import web_board
    _, rid = sent(w, status="running")
    t = log_in(w).get(url(rid)).text
    css = style_of(t)
    assert css == web_board.STYLE
    for k in classes_in(card(t)):
        assert re.search(r"[.]%s(?![\w-])" % re.escape(k), css), k


@pytest.mark.parametrize("state", ["done", "refused"])
def test_tc027_the_card_is_read_only(w, state):
    # TC-027
    _, rid = sent(w, status="running", job_state=state, result={"message": "x"} if state == "refused" else None,
                  finished=w.clock.t - 60 if state == "refused" else None)
    c = log_in(w)
    for lang in ("", "en"):
        inner = card(c.get(url(rid, lang)).text, "Launch" if lang else "送出")
        for tag in ("<form", "<button", "<input", "<script", "<a ", "href=", "http"):
            assert tag not in inner, tag


def test_tc028_the_two_old_placeholder_tests_changed_only_for_launch():
    # TC-028
    from pathlib import Path
    here = Path(__file__).parent
    board = (here / "test_web_board.py").read_text(encoding="utf-8")
    bugs = (here / "test_web_bugs_a.py").read_text(encoding="utf-8")
    assert '("launch", "之後開放")' not in board and '("downstream", "之後開放")' in board and '("finished", "該次分析尚未進行至此階段。")' in board
    assert 'parametrize("stage", ["launch"])' not in bugs and "test_stage_launch_has_its_own_card" in bugs
    for text in (board, bugs):
        assert "xfail" not in text and "pytest.mark.skip" not in text


def test_tc029_secrets_are_masked(w):
    # TC-029
    token = "ghp_" + "x" * 24
    params = {"genome": "GRCh38", "api_token": token, "note": "ghp_" + "y" * 24}
    _, rid = sent(w, status="succeeded", params=params)
    c = log_in(w)
    for lang in ("", "en"):
        t = c.get(url(rid, lang)).text
        assert "ghp_" not in t and token not in t
        cell = rows(t, lang)["Changed parameters" if lang else "已變更的參數"]
        assert "genome: GRCh38" in cell and "api_token" in cell and "note" in cell
        assert re.search(r"api_token: \S+", cell) and re.search(r"note: \S+", cell)


def test_tc030_no_internal_paths_or_hosts(w):
    # TC-030
    _, rid = sent(w, status="succeeded")
    c = log_in(w)
    for lang in ("", "en"):
        t = card(c.get(url(rid, lang)).text, "Launch" if lang else "送出")
        for word in ("/f/ann-run", "agent-t", "lab-a", "bundle", "sha256"):
            assert word not in t, word
        assert "/f/ann-run" not in c.get(url(rid, lang)).text


def test_tc031_a_refusal_with_a_path_and_a_command_stays_out_of_the_card(w):
    # TC-031
    reason = "No slot. Try /work/proj/xyz and then run: rm -rf /work/proj/xyz"
    _, rid = sent(w, status="running", job_state="refused", result={"message": reason}, finished=w.clock.t - 60)
    t = log_in(w).get(url(rid, "en")).text
    inner = card(t, "Launch")
    for word in ("/work/proj/xyz", "rm -rf", "No slot"):
        assert word not in inner
    assert '<section id="refusal">' in t


def test_tc032_markup_is_escaped(w):
    # TC-032
    evil = "<script>alert(1)</script>"
    _, rid = sent(w, status="succeeded", pipeline=evil, params={"a": evil})
    t = log_in(w).get(url(rid)).text
    assert "<script>alert(1)" not in t and "&lt;script&gt;alert(1)&lt;/script&gt;" in card(t)
