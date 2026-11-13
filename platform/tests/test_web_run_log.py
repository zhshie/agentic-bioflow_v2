# Nothing existing: tests of web-run-tasks-log (the log of a failed task on the board); the page, the route GET /run/log and the action
# task_log_view are ours (specs/web-run-tasks-log/test-case.md).
"""web-run-tasks-log. Test cases are named in the comments (TC-001 ...)."""
import html
import json
import re
import sqlite3
import time
import urllib.parse

import pytest

from human_harness import World
from test_web_board import no_cjk, pane, plain, seed

NOW = time.time()
HOUR = 3600
INTERNAL = re.compile(r"Traceback|JobRefused|\bSELECT\b|sqlite|args_json|result_json|deadline_at|Exception|, line \d+|/data/wd")
WD = "/w/ab/cdef12"
WD2 = "/w/cd/345678"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def add_tasks(w, rid, tasks):
    """tasks: [(task_key, name, workdir or None)]"""
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    with con:
        for key, name, wd in tasks:
            con.execute("INSERT INTO failed_tasks (run_id, task_key, name, exit_code, error_message, workdir) VALUES (?,?,?,?,?,?)",
                        (rid, key, name, 137, "boom", wd))
    con.close()


def world(w, status="failed", tasks=((("t1"), "FASTQC", WD),), name="ann-fail", failed=None):
    ann = w.user("ann")
    rid = seed(w, name, status, ann, started=NOW - 3 * HOUR, ended=NOW - 2 * HOUR if status != "running" else None,
               counts=dict(failed=len(tasks) if failed is None else failed))
    add_tasks(w, rid, list(tasks))
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    return ann, c, rid


def log_url(rid, task="FASTQC", which="err", extra=""):
    return "/run/log?run=%s&task=%s&which=%s%s" % (rid, urllib.parse.quote(task, safe=""), which, extra)


def log_jobs(w):
    return w.sql("SELECT * FROM jobs WHERE kind = 'read_task_log' ORDER BY id")


def reply(w, result, state="done"):
    from abf_platform import jobs
    job = log_jobs(w)[-1]
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET state = 'claimed', claimed_at = ? WHERE id = ?", (time.time(), job["id"]))
    con.close()
    code, body = jobs.take_result(w.ip.state_db, job["agent"], job["id"], state, result, time.time)
    assert code == 200 and body["accepted"], (code, body)


def ok(text, truncated=False):
    return {"ok": True, "file": ".command.err", "text": text, "lines": text.count("\n") + 1, "truncated": truncated}


def main(text):
    return re.search(r"<main.*?</main>", text, re.S).group(0)


def mid(text):
    return pane(text, "middle")


def hrefs(fragment):
    return [html.unescape(h) for h in re.findall(r'href="([^"]*)"', fragment)]


# ---- US1: the way in -----------------------------------------------------------------------------------------------------

def test_tc001_tasks_tab_row_has_a_log_link(w):
    # TC-001, tl12
    ann, c, rid = world(w)
    t = mid(c.get("/?run=%s&tab=tasks" % rid).text)
    row = re.findall(r"<tr>.*?</tr>", t, re.S)[-1]
    assert "/run/log?run=%s&task=FASTQC&which=err" % rid in hrefs(row)
    assert "<th>日誌</th>" in t


def test_tc002_no_workdir_is_grey_words(w):
    # TC-002
    ann, c, rid = world(w, tasks=[("t1", "FASTQC", None)])
    row = re.findall(r"<tr>.*?</tr>", mid(c.get("/?run=%s&tab=tasks" % rid).text), re.S)[-1]
    assert "沒有記錄工作資料夾" in row and "/run/log" not in row
    en = re.findall(r"<tr>.*?</tr>", mid(c.get("/?run=%s&tab=tasks&lang=en" % rid).text), re.S)[-1]
    assert "No work directory on record" in en and no_cjk(en)


@pytest.mark.parametrize("status,suffix", [("running", ""), ("failed", "&stage=results")])
def test_tc003_004_logs_tab_lists_failed_tasks_with_three_links(w, status, suffix):
    # TC-003, TC-004 (the logs tab of the running page and of the results page)
    ann, c, rid = world(w, status=status, tasks=[("t1", "FASTQC", WD), ("t2", "TRIM (a)", WD2)])
    if status == "failed":
        rid2 = seed(w, "ann-ok", "succeeded", ann, started=NOW - 3 * HOUR, ended=NOW - 2 * HOUR, counts=dict(failed=2))
        add_tasks(w, rid2, [("t1", "FASTQC", WD), ("t2", "TRIM (a)", WD2)])
        t = mid(c.get("/?run=%s&stage=results&tab=logs" % rid2).text)
    else:
        t = mid(c.get("/?run=%s&tab=logs" % rid).text)
    assert '<section class="soon">' not in t
    links = hrefs(t)
    for name, q in (("FASTQC", "FASTQC"), ("TRIM (a)", "TRIM%20%28a%29")):
        for which in ("err", "out", "log"):
            assert any(h.startswith("/run/log?") and "task=" + q in h and h.endswith("which=" + which) for h in links), (name, which)
    assert [plain(x) for x in re.findall(r"<a\b[^>]*run/log[^>]*>(.*?)</a>", t)][:3] == ["錯誤", "輸出", "全部"]


@pytest.mark.parametrize("stage", ["", "&stage=results"])
def test_tc005_006_no_failed_tasks(w, stage):
    # TC-005, TC-006
    ann = w.user("ann")
    rid = seed(w, "ann-clean", "succeeded" if stage else "running", ann, started=NOW - 3 * HOUR, ended=NOW - 2 * HOUR if stage else None)
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    t = mid(c.get("/?run=%s%s&tab=logs" % (rid, stage)).text)
    t = t.split('<nav class="rtabs">')[1].split("</nav>", 1)[1]      # what sits under the tab strip
    assert "目前沒有失敗任務" in t and "/run/log" not in t and "之後開放" not in t


def test_tc007_008_partial_and_unlisted_notes_match_the_tasks_tab(w):
    # TC-007, TC-008
    ann, c, rid = world(w, failed=3)
    note = lambda tab: re.findall(r'<p class="muted">(.*?)</p>', mid(c.get("/?run=%s&tab=%s" % (rid, tab)).text), re.S)
    assert note("logs") == note("tasks") and "失敗計數 3" in note("logs")[0]
    rid2 = seed(w, "ann-unl", "failed", ann, started=NOW - 3 * HOUR, ended=NOW - 2 * HOUR, counts=dict(failed=2))
    note2 = lambda tab: re.findall(r'<p class="muted">(.*?)</p>', mid(c.get("/?run=%s&tab=%s" % (rid2, tab)).text), re.S)
    assert note2("logs") == note2("tasks") and "失敗計數 2" in note2("logs")[0]


def test_tc047_config_and_metrics_stay_soon(w):
    # TC-047
    ann, c, rid = world(w)
    for tab in ("config", "metrics"):
        assert '<section class="soon">' in mid(c.get("/?run=%s&tab=%s" % (rid, tab)).text)


def is_waiting(text):
    """The waiting page (tl06, ruling 2026-11-07): a Refresh link and the time of the data, and no <meta refresh> (axe: critical)."""
    return ("重新整理" in text or "Refresh" in text) and ("資料時間" in text or "Data as of" in text) and "http-equiv" not in text.lower()


# ---- US2: reading and showing --------------------------------------------------------------------------------------------

def test_tc010_011_012_019_020_first_request_queues_one_job_and_waits(w):
    # TC-010, TC-011, TC-012, TC-019, TC-020, tl06
    ann, c, rid = world(w)
    r = c.get(log_url(rid, extra="&workdir=/evil"))
    assert r.status_code == 200 and is_waiting(r.text) and "Error: out of memory" not in r.text
    [job] = log_jobs(w)
    args = json.loads(job["args_json"])
    assert args["file"] == ".command.err" and args["workdir"] == WD and job["state"] == "queued"
    assert job["compute_env"] == "lab-a"      # queued for the caller's own environment (enqueue_task_log refuses anybody else's)
    c.get(log_url(rid, which="out"))
    c.get(log_url(rid, which="log"))
    assert [json.loads(j["args_json"])["file"] for j in log_jobs(w)] == [".command.err", ".command.out", ".command.log"]
    # the answer arrives (TC-010)
    reply(w, ok("Error: out of memory"), state="done")
    r = c.get(log_url(rid, which="log"))
    assert r.status_code == 200 and "<pre>" in r.text


def test_tc010_failed_task_reason_is_readable_in_the_web_page(w):
    # TC-010: the task's own log link -> loading page -> job done -> the same link shows the task name and the error text
    ann, c, rid = world(w)
    first = c.get(log_url(rid, which="err"))
    assert is_waiting(first.text) and "Error: out of memory" not in first.text
    assert len(log_jobs(w)) == 1
    reply(w, ok("Error: out of memory"), state="done")
    last = c.get(log_url(rid, which="err"))
    assert last.status_code == 200 and "<html" in last.text.lower()
    assert "FASTQC" in last.text and "Error: out of memory" in last.text
    assert re.search(r"<pre>Error: out of memory</pre>", last.text) and 'http-equiv="refresh"' not in last.text
    assert len(log_jobs(w)) == 1          # nobody had to ask again


def test_tc013_014_a_waiting_or_running_job_is_not_doubled(w):
    # TC-013, TC-014, tl07
    ann, c, rid = world(w)
    c.get(log_url(rid))
    assert is_waiting(c.get(log_url(rid)).text) and len(log_jobs(w)) == 1
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET state = 'claimed', claimed_at = ? WHERE kind = 'read_task_log'", (time.time(),))
    con.close()
    assert is_waiting(c.get(log_url(rid)).text) and len(log_jobs(w)) == 1


def test_tc015_to_018_021_the_text_is_a_page_escaped_with_the_same_headers(w):
    # TC-015, TC-016, TC-017, TC-018, TC-021, tl08, tl09
    ann, c, rid = world(w)
    c.get(log_url(rid))
    reply(w, ok("line one\nline two <script>alert(1)</script>", truncated=True))
    r = c.get(log_url(rid))
    assert r.status_code == 200 and "line one" in r.text and "line two" in r.text
    assert re.search(r"<pre>line one\nline two &lt;script&gt;alert\(1\)&lt;/script&gt;</pre>", r.text)
    assert "<script>alert(1)</script>" not in r.text
    assert r.headers["content-type"].startswith("text/html") and "content-disposition" not in r.headers
    from abf_platform import web
    assert r.headers["content-security-policy"] == web._HEADERS["Content-Security-Policy"]      # live-sync: `/` now carries the script; the log page keeps today's policy
    assert "已截斷" in r.text and "FASTQC" in r.text
    assert "Cut" in c.get(log_url(rid, extra="&lang=en")).text


def test_tc022_023_a_fresh_answer_is_reused_and_retry_asks_again(w):
    # TC-022, TC-023
    ann, c, rid = world(w)
    c.get(log_url(rid))
    reply(w, ok("done text"))
    assert "done text" in c.get(log_url(rid)).text and len(log_jobs(w)) == 1
    r = c.get(log_url(rid, extra="&retry=1"))
    assert len(log_jobs(w)) == 2 and "done text" not in r.text and is_waiting(r.text)


def test_tc024_task_key_or_name_are_both_accepted(w):
    # TC-024
    ann, c, rid = world(w, tasks=[("ab/123456", "FASTQC", WD)])
    for ident in ("ab%2F123456", "FASTQC"):
        r = c.get("/run/log?run=%s&task=%s&which=err" % (rid, ident))
        assert r.status_code == 200 and is_waiting(r.text), ident
    assert len(log_jobs(w)) == 1 and json.loads(log_jobs(w)[0]["args_json"])["workdir"] == WD


def test_tc025_a_missing_file_is_said_in_words(w):
    # TC-025
    ann, c, rid = world(w)
    c.get(log_url(rid))
    reply(w, {"ok": False, "error": "not_found", "message": "file not found"}, state="error")
    r = c.get(log_url(rid))
    t = plain(main(r.text))
    assert r.status_code == 200 and "✕" in t and "沒有此檔案" in t and not INTERNAL.search(r.text)


def test_tc026_030_045_agent_offline_is_a_plain_error_page(w):
    # TC-026, TC-030, TC-045, tl10
    ann, c, rid = world(w)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE agents SET last_seen_at = 0")
    con.close()
    r = c.get(log_url(rid))
    t = plain(main(r.text))
    assert r.status_code == 200 and "✕" in t and "代理" in t and "離線" in t and not INTERNAL.search(r.text) and log_jobs(w) == []
    assert any("retry=1" in h for h in hrefs(r.text))


def test_tc027_a_refused_environment_gives_one_sentence(w):
    # TC-027
    ann, c, rid = world(w)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET status = 'disabled'")
    con.close()
    r = c.get(log_url(rid))
    t = plain(main(r.text))
    assert r.status_code == 200 and "✕" in t and not INTERNAL.search(r.text) and log_jobs(w) == []


def test_tc028_029_031_033_049_state_marks_english_and_no_script(w):
    # TC-028, TC-029, TC-031, TC-033, TC-049
    ann, c, rid = world(w)
    pages = {}
    pages["loading"] = c.get(log_url(rid, extra="&lang=en")).text
    reply(w, ok("hello"))
    pages["ready"] = c.get(log_url(rid, extra="&lang=en")).text
    pages["error"] = c.get(log_url(rid, which="foo", extra="&lang=en")).text
    assert "◌" in pages["loading"] and "Reading" in pages["loading"]
    assert "✓" in pages["ready"] and "Loaded" in pages["ready"]
    assert "✕" in pages["error"]
    for name, text in pages.items():
        m = main(text)
        stripped = re.sub(r"<pre>.*?</pre>", "", m, flags=re.S)
        assert no_cjk(re.sub(r"<[^>]+>", " ", stripped)), name
        assert "style=" not in text and "<script" not in text and not re.search(r"\son\w+=", text), name
        assert not re.search(r'(src|href)="(https?:)?//', text), name
        assert text.count("<style>") == 1, name


def test_tc034_tabs_have_no_inline_style_or_external_resource(w):
    # TC-034
    ann, c, rid = world(w)
    for tab in ("tasks", "logs"):
        t = c.get("/?run=%s&tab=%s" % (rid, tab)).text
        from helpers import one_live_script
        assert "style=" not in t and one_live_script(t) and t.count("<style>") == 1      # live-sync: the run page reloads itself
        assert not re.search(r'(src|href)="(https?:)?//', t)


# ---- US3: owners and bad input -------------------------------------------------------------------------------------------

def test_tc037_not_logged_in_is_the_same_as_run_file(w):
    # TC-037, tl01
    ann, c, rid = world(w)
    anon = w.web()
    a = anon.get(log_url(rid), follow_redirects=False)
    b = anon.get("/run/file?run=%s&path=x" % rid, follow_redirects=False)
    assert a.status_code == b.status_code and a.headers.get("location") == b.headers.get("location") and log_jobs(w) == []


def test_tc038_039_040_another_users_run_is_not_found(w):
    # TC-038, TC-039, TC-040, tl02
    from abf_platform import actions
    ann, c, rid = world(w)
    bob = w.user("bob")
    cb = w.web()
    assert w.login(cb, "bob").status_code == 303
    mine = cb.get(log_url(rid))
    nope = cb.get(log_url("id-nothing-here"))
    assert mine.status_code == 404 and nope.status_code == 404 and mine.text == nope.text and log_jobs(w) == []
    got = actions.task_log_view(str(w.ip.index), str(w.ip.state_db), rid, "FASTQC", "err", caller=bob)
    assert got["found"] is False and got["message"] and log_jobs(w) == []


@pytest.mark.parametrize("task,which,code", [("NOPE", "err", "no_task"), ("/etc", "err", "no_task"), ("FASTQC", "foo", "bad_which"),
                                             ("FASTQC", "nextflow", "bad_which"), ("FASTQC", "slurm", "bad_which")])
def test_tc041_042_044_048_bad_task_or_which_queue_nothing(w, task, which, code):
    # TC-041, TC-042, TC-044, TC-048, tl03, tl05
    from abf_platform import actions
    ann, c, rid = world(w)
    got = actions.task_log_view(str(w.ip.index), str(w.ip.state_db), rid, task, which, caller=ann)
    assert got["state"] == "error" and got["code"] == code
    r = c.get(log_url(rid, task=task, which=which, extra="&workdir=/etc"))
    assert r.status_code == 200 and "✕" in r.text and not INTERNAL.search(r.text) and log_jobs(w) == []


def test_tc043_no_workdir_queues_nothing(w):
    # TC-043, tl04
    from abf_platform import actions
    ann, c, rid = world(w, tasks=[("t1", "FASTQC", None)])
    got = actions.task_log_view(str(w.ip.index), str(w.ip.state_db), rid, "FASTQC", "err", caller=ann)
    assert got["state"] == "error" and got["code"] == "no_workdir" and log_jobs(w) == []
    r = c.get(log_url(rid))
    assert "✕" in r.text and "工作資料夾" in r.text and log_jobs(w) == []


def test_tc046_a_succeeded_or_running_task_has_no_log(w):
    # TC-046: only the failed_tasks are listed; a name outside them is refused
    ann, c, rid = world(w)
    t = mid(c.get("/?run=%s&tab=logs" % rid).text)
    assert "SUCCEEDED_TASK" not in t
    r = c.get(log_url(rid, task="SUCCEEDED_TASK"))
    assert "✕" in r.text and log_jobs(w) == []


def test_tc054_the_web_modules_do_not_import_jobs():
    # TC-054, tl12 (the old tc060 check, run on the two modules this task touched)
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent / "abf_platform"
    for name in ("web.py", "web_board.py"):
        src = (root / name).read_text(encoding="utf-8")
        assert not re.search(r"^\s*(from\s+(\.|abf_platform)\s*import\s+[^#\n]*\b(jobs|status|compute_envs|confirm|agents)\b|import\s+abf_platform\.(jobs|status|compute_envs|confirm|agents))", src, re.M), name
