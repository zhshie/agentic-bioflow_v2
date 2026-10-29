# Nothing existing: tests of the results stage (summary cards + Outputs tab, DESIGN.md v2 screen 8); the page and the run_outputs read are ours.
"""results-outputs: test cases are named in the comments (TC-001 ...), see specs/results-outputs/test-case.md."""
import base64
import hashlib
import json
import re
import sqlite3
import time

import pytest

from human_harness import World
from test_web_board import cjk, no_cjk, pane, plain, seed

NOW = time.time()
HOUR = 3600
FOLDER = "/data/wd/runs/ann-done"
ENTRIES = [
    {"name": "zeta.txt", "type": "file", "size": 2048, "modified": "2026-10-20T08:00:00Z"},
    {"name": "multiqc", "type": "dir", "size": 4096, "modified": "2026-10-20T08:01:00Z"},
    {"name": "alpha.tsv", "type": "file", "size": 10, "modified": "2026-10-20T08:02:00Z"},
    {"name": "dada2", "type": "dir", "size": 4096, "modified": "2026-10-20T08:03:00Z"},
]


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def launch_to(w, run_name, folder):
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE launches SET run_folder = ? WHERE run_name = ?", (folder, run_name))
    con.close()


def world(w, name="ann-done", counts=None, **kw):
    ann = w.user("ann")
    rid = seed(w, name, "succeeded", ann, started=NOW - 3 * HOUR, ended=NOW - 2 * HOUR, counts=counts or dict(succeeded=4), **kw)
    launch_to(w, name, "/data/wd/runs/" + name)
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    return ann, c, rid


def url(rid, stage="results", tab=None, extra=""):
    return "/?run=%s&stage=%s%s%s" % (rid, stage, "&tab=" + tab if tab else "", extra)


def listings(w):
    return w.sql("SELECT * FROM jobs WHERE kind = 'list_site_files' ORDER BY id")


def finish(w, job_id, ok=True, entries=None, message=None, state="done", error=None):
    result = {"ok": ok, "path": FOLDER + "/results"}
    if entries is not None:
        result["entries"] = entries
        result["count"] = len(entries)
    if message:
        result["message"] = message
    if error:
        result["error"] = error
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET state = ?, result_json = ?, finished_at = ? WHERE id = ?", (state, json.dumps(result), time.time(), job_id))
    con.close()


def mid(text):
    return pane(text, "middle")


def cards(text):
    return re.findall(r'<h2 class="ct">(.*?)</h2><p class="cv">(.*?)</p>', mid(text), re.S)


def tabs(text):
    nav = re.search(r'<nav class="rtabs">(.*?)</nav>', mid(text), re.S).group(1)
    return [(re.search(r"tab=(\w+)", h).group(1), plain(label), 'aria-current="page"' in a)
            for a, h, label in re.findall(r'(<a href="([^"]*)"[^>]*>(.*?)</a>)', nav, re.S)]


def test_ro01_results_stage_has_cards_and_tabs(w):
    # TC-001, TC-002, TC-003, TC-004, TC-005, TC-006, TC-007, TC-011, TC-012, TC-015
    ann, c, rid = world(w)
    t = c.get(url(rid)).text
    got = cards(t)
    assert len(got) == 4
    assert [k for k, _ in got] == ["完成步驟", "耗時", "運算環境", "費用"]
    assert got[0][1] == "4 / 4" and got[1][1] == "1 小時 0 分" and "lab-a" in got[2][1] and got[3][1] == "SU —"
    assert tabs(t) == [("outputs", "輸出", True), ("info", "執行資訊", False), ("tasks", "任務", False), ("logs", "日誌", False)]
    m = mid(t)
    for word in ("報告", "MultiQC 報告", "指標", "全部下載"):
        assert re.search(r'<span class="off">%s <span class="later">之後開放</span></span>' % word, m), word
    assert "<progress" not in m and '<dl class="counts">' not in m
    assert 'class="sq"' in m and "完成" in plain(m)       # the state of the run is on the same screen (TC-015)
    assert tabs(c.get("/?run=" + rid).text)[0] == ("outputs", "輸出", True)       # TC-007 / TC-016: the default stage is the results


def test_ro01b_other_tabs_reuse_the_running_stage_bodies(w):
    # TC-008, TC-009, TC-010
    ann, c, rid = world(w)
    info = mid(c.get(url(rid, tab="info")).text)
    assert "ann-done" in info and rid in info and 'class="sq"' in info
    assert "沒有失敗的任務" in mid(c.get(url(rid, tab="tasks")).text)
    assert '<section class="soon">' in mid(c.get(url(rid, tab="logs")).text)
    assert listings(w) == []        # only the Outputs tab asks the site


def test_ro01c_not_succeeded_has_no_listing(w):
    # TC-013
    ann = w.user("ann")
    a = seed(w, "ann-run", "running", ann, started=NOW - 100)
    b = seed(w, "ann-bad", "failed", ann, started=NOW - 200)
    c = w.web()
    w.login(c, "ann")
    for rid in (a, b):
        t = c.get(url(rid)).text
        assert "這個 run 還沒到這個階段。" in t and 'class="rtabs"' not in mid(t) and "sumcards" not in mid(t)
    assert listings(w) == []


def test_ro02_first_view_queues_one_listing_and_shows_loading(w):
    # TC-020, TC-021, TC-022, TC-016
    ann, c, rid = world(w)
    t = c.get("/?run=" + rid).text
    rows = listings(w)
    assert len(rows) == 1 and rows[0]["compute_env"] == "lab-a" and json.loads(rows[0]["args_json"])["path"] == FOLDER + "/results"
    assert "⟳" in t and "讀取中" in t and "每 15 秒自動更新" in t
    c.get(url(rid, tab="outputs"))
    assert len(listings(w)) == 1


def test_ro02b_claimed_is_loading_and_latest_launch_wins(w):
    # TC-023, TC-024
    ann, c, rid = world(w)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)",
                    ("ann-done", "/data/wd/runs/ann-done-2", "lab-a", "agent-t", time.time() + 5, ann.user_id))
    con.close()
    c.get(url(rid))
    rows = listings(w)
    assert json.loads(rows[0]["args_json"])["path"] == "/data/wd/runs/ann-done-2/results"
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET state = 'claimed' WHERE id = ?", (rows[0]["id"],))
    con.close()
    assert "讀取中" in c.get(url(rid)).text and len(listings(w)) == 1


def test_ro03_finished_listing_is_shown(w):
    # TC-025, TC-026, TC-027, TC-028, TC-029, TC-082, TC-092
    ann, c, rid = world(w)
    c.get(url(rid))
    finish(w, listings(w)[0]["id"], entries=ENTRIES)
    t = c.get(url(rid)).text
    names = re.findall(r"<td>(?:<a [^>]*>)?<code>(.*?)</code>(?:</a>)?</td>", mid(t))      # results-files: a folder name is a link now
    assert names == ["dada2", "multiqc", "alpha.tsv", "zeta.txt"]
    assert re.search(r"讀取於 \d\d:\d\d", plain(mid(t)))
    assert re.search(r'<a href="[^"]*tab=outputs&amp;relist=1[^"]*">重新讀取</a>', t)
    assert "資料夾" in mid(t) and "檔案" in mid(t) and "2048" in mid(t)
    c.get(url(rid))
    assert len(listings(w)) == 1
    assert "<form" not in mid(t) and "<button" not in mid(t)
    assert not re.search(r"<a [^>]*>[^<]*(alpha|zeta)", mid(t))      # a file name is plain text, not a link (results-files: a folder name is a link, test_results_files)
    assert "全部下載" in mid(t) and 'href="/download' not in t


def test_ro04_empty_folder(w):
    # TC-030
    ann, c, rid = world(w)
    c.get(url(rid))
    finish(w, listings(w)[0]["id"], entries=[])
    t = mid(c.get(url(rid)).text)
    assert "— 這個資料夾是空的" in plain(t) and "<table" not in t and "讀取於" in t and "重新讀取" in t


def test_ro05_error_shows_reason_and_relist(w):
    # TC-031, TC-032, TC-034, TC-040
    ann, c, rid = world(w)
    c.get(url(rid))
    job = listings(w)[0]["id"]
    finish(w, job, ok=False, message="the folder does not exist on the site", state="error", error="not_found")
    t = c.get(url(rid)).text
    assert "✗" in t and "讀不到" in t and "the folder does not exist on the site" in t and "重新讀取" in t
    finish(w, job, ok=False, message='Traceback (most recent call last):\n  File "x.py", line 3\nSELECT * FROM jobs', state="error")
    t = mid(c.get(url(rid)).text)
    for bad in ("Traceback", "SELECT", 'File "', "args_json", "deadline_at"):
        assert bad not in t
    assert "讀不到" in t
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET state = 'expired', result_json = NULL WHERE id = ?", (job,))
    con.close()
    t = mid(c.get(url(rid)).text)
    assert "讀不到" in t and "讀取中" not in t and "站台沒有回應" in t
    assert len(listings(w)) == 1


def test_ro05b_overdue_queued_job_is_an_error_without_a_new_job(w):
    # TC-033
    ann, c, rid = world(w)
    c.get(url(rid))
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET deadline_at = ? WHERE kind = 'list_site_files'", (time.time() - 5,))
    con.close()
    t = mid(c.get(url(rid)).text)
    assert "讀不到" in t and "站台沒有回應" in t and "讀取中" not in t
    assert len(listings(w)) == 1


def test_ro05c_latest_one_wins_and_other_paths_do_not_count(w):
    # TC-038, TC-039, TC-040
    ann, c, rid = world(w)
    c.get(url(rid))
    first = listings(w)[0]["id"]
    finish(w, first, entries=ENTRIES)
    c.get(url(rid, extra="&relist=1"))
    second = listings(w)[1]["id"]
    finish(w, second, ok=False, message="the folder does not exist on the site", state="error")
    assert "讀不到" in c.get(url(rid)).text
    finish(w, second, entries=[])
    assert "這個資料夾是空的" in c.get(url(rid)).text
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET args_json = replace(args_json, '/results', '/other')")      # other path: not used
    con.close()
    assert "讀取中" in c.get(url(rid)).text and len(listings(w)) == 3
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("DELETE FROM jobs WHERE kind = 'list_site_files'")      # TC-038: cleaned up counts as none
    con.close()
    assert "讀取中" in c.get(url(rid)).text and len(listings(w)) == 1
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET compute_env = 'lab-other'")      # same path, other environment: not used
    con.close()
    c.get(url(rid))
    assert len(listings(w)) == 2


def test_ro06_not_launched_from_platform_is_unavailable(w):
    # TC-035, TC-042
    from abf_platform import actions
    ann = w.user("ann")
    rid = seed(w, "ann-plain", "succeeded", ann, started=NOW - HOUR, launch_row=False)
    # the terminal (no caller) sees a run nobody launched through the platform: no record of a folder
    got = actions.run_outputs(w.ip.index, w.ip.state_db, rid)
    assert got["state"] == "unavailable" and got["files"] == [] and "沒有輸出資料夾紀錄" in got["reason"]
    c = w.web()
    w.login(c, "ann")
    # a person's own run has a launch record; give it one that names no folder
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)",
                    ("ann-plain", "", "lab-a", "agent-t", time.time(), ann.user_id))
    con.close()
    t = mid(c.get(url(rid)).text)
    assert "— 沒有輸出資料夾紀錄" in plain(t) and "不是從平台送出的分析，沒有輸出資料夾紀錄" in t
    assert listings(w) == []


def test_ro07_relist_queues_a_new_job_and_refresh_url_has_no_relist(w):
    # TC-036, TC-037, TC-043
    ann, c, rid = world(w)
    c.get(url(rid))
    finish(w, listings(w)[0]["id"], entries=ENTRIES)
    r = c.get(url(rid, tab="outputs", extra="&relist=1&path=/etc"))
    assert len(listings(w)) == 2 and "讀取中" in r.text
    assert json.loads(listings(w)[1]["args_json"])["path"] == FOLDER + "/results"
    refresh = re.search(r'<meta http-equiv="refresh" content="([^"]*)">', r.text).group(1)
    assert refresh.startswith("15;url=") and "relist" not in refresh
    target = refresh.split("url=", 1)[1].replace("&amp;", "&")
    c.get(target)
    assert len(listings(w)) == 2


def test_ro08_owner_rule(w):
    # TC-050, TC-051, TC-052, TC-053
    from abf_platform import actions
    ann, c, rid = world(w)
    bob = w.user("bob")
    got = actions.run_outputs(w.ip.index, w.ip.state_db, rid, caller=bob)
    ghost = actions.run_outputs(w.ip.index, w.ip.state_db, "nope", caller=bob)
    assert got == ghost and got["found"] is False and "files" not in got and "path" not in got
    cb = w.web()
    assert w.login(cb, "bob").status_code == 303
    r = cb.get(url(rid))
    assert r.status_code == 404 and "ann-done" not in r.text
    assert listings(w) == []
    mine = actions.run_outputs(w.ip.index, w.ip.state_db, rid, caller=ann)
    assert mine["state"] == "loading"


def test_ro08b_mcp_tool_matches_the_action(w):
    # TC-053, TC-054: the same read, by the same name, through MCP; bob gets the answer of TC-050 / TC-051
    from helpers import tool_json
    ann, c, rid = world(w)
    bob = w.user("bob")
    tools, _ = w.mcp([])
    tool = [t for t in tools if t.name == "run_outputs"]
    assert len(tool) == 1 and tool[0].annotations.read_only_hint is True       # a read tool: nothing is written or run
    theirs = tool_json(w.call("run_outputs", {"run_id": rid}, caller=bob))
    ghost = tool_json(w.call("run_outputs", {"run_id": "nope"}, caller=bob))
    assert theirs == ghost and theirs["found"] is False and "files" not in theirs and "path" not in theirs
    assert listings(w) == []                                                   # nothing was queued for somebody else's run
    mine = tool_json(w.call("run_outputs", {"run_id": rid}, caller=ann))
    assert mine["state"] == "loading" and mine["path"] == FOLDER + "/results" and len(listings(w)) == 1
    finish(w, listings(w)[0]["id"], entries=ENTRIES)
    done = tool_json(w.call("run_outputs", {"run_id": rid}, caller=ann))
    assert done["state"] == "ready" and sorted(f["name"] for f in done["files"]) == sorted(e["name"] for e in ENTRIES)
    assert len(listings(w)) == 1                                               # asking again did not queue a second question


def test_ro09_page_never_waits_for_the_site(w, monkeypatch):
    # TC-056
    from abf_platform import jobs

    async def boom(*a, **k):
        raise AssertionError("the page waited for the site")
    monkeypatch.setattr(jobs, "wait_for_result", boom)
    ann, c, rid = world(w)
    r = c.get(url(rid))
    assert r.status_code == 200 and "讀取中" in r.text


def test_ro09b_the_page_takes_everything_from_the_action(w, monkeypatch):
    # TC-057
    from abf_platform import actions
    fake = {"state": "ready", "path": "/x/results", "compute_env": "lab-a", "listed_at": 1_000_000.0, "reason": None,
            "files": [{"name": "only-this.txt", "type": "file", "size": 5, "modified": "2026-10-20T08:00:00Z"}]}
    monkeypatch.setattr(actions, "run_outputs", lambda *a, **k: fake)
    ann, c, rid = world(w)
    t = c.get(url(rid)).text
    assert "only-this.txt" in t and listings(w) == []


def test_ro10_english(w):
    # TC-014, TC-076
    ann, c, rid = world(w)
    t = c.get(url(rid) + "&lang=en").text
    assert [x[1] for x in tabs(t)] == ["Outputs", "Run info", "Tasks", "Logs"]
    for word in ("Report", "MultiQC report", "Metrics", "Download all"):
        assert re.search(r'<span class="off">%s <span class="later">Coming later</span></span>' % word, t), word
    assert no_cjk(mid(t)), cjk(mid(t))
    finish(w, listings(w)[0]["id"], entries=ENTRIES)
    t = c.get(url(rid) + "&lang=en").text
    assert no_cjk(mid(t)) and "Read at" in t and "Read again" in t
    finish(w, listings(w)[0]["id"], entries=[])
    assert no_cjk(mid(c.get(url(rid) + "&lang=en").text))
    finish(w, listings(w)[0]["id"], ok=False, message="the folder does not exist on the site", state="error")
    t = c.get(url(rid) + "&lang=en").text
    assert no_cjk(mid(t)) and "Could not read" in t


def states(w, c, rid):
    """The page in each of the four states, zh and en."""
    out = []
    c.get(url(rid))
    job = listings(w)[0]["id"]
    out += [c.get(url(rid) + lang) for lang in ("", "&lang=en")]
    finish(w, job, entries=ENTRIES)
    out += [c.get(url(rid) + lang) for lang in ("", "&lang=en")]
    finish(w, job, entries=[])
    out += [c.get(url(rid) + lang) for lang in ("", "&lang=en")]
    finish(w, job, ok=False, message="the folder does not exist on the site", state="error")
    out += [c.get(url(rid) + lang) for lang in ("", "&lang=en")]
    return out


def test_ro11_constraints_hold(w):
    # TC-070, TC-071, TC-072, TC-073, TC-077
    ann, c, rid = world(w)
    pages = states(w, c, rid) + [c.get(url(rid, tab=x)) for x in ("info", "tasks", "logs")]
    for r in pages:
        assert r.status_code == 200
        assert "<script" not in r.text and "style=" not in r.text
        assert len(re.findall(r"<style>", r.text)) == 1
        style = re.search(r"<style>(.*?)</style>", r.text, re.S).group(1)
        digest = base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
        assert "style-src 'sha256-%s'" % digest in r.headers["content-security-policy"]
        assert re.search(r'<meta http-equiv="refresh" content="15', r.text)
        for inner in ("list_site_files", "compute_env", "Traceback", "args_json"):
            assert inner not in mid(r.text)


def test_ro11b_long_names_wrap_and_no_new_colour(w):
    # TC-074, TC-017
    ann, c, rid = world(w)
    c.get(url(rid))
    finish(w, listings(w)[0]["id"], entries=[{"name": "x" * 200, "type": "file", "size": 1, "modified": "2026-10-20T08:00:00Z"}])
    t = c.get(url(rid)).text
    assert "x" * 200 in t and 'class="tbl otbl"' in t
    assert ".otbl code{overflow-wrap:anywhere}" in t
    from abf_platform import web_board
    new = web_board.STYLE.split(".otbl", 1)[1]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgb|hsl", new)


def test_ro12_nothing_else_is_written(w):
    # TC-059, TC-080, TC-081, TC-083
    ann, c, rid = world(w)
    before = w.sql("SELECT COUNT(*) FROM confirmations")[0][0]
    kinds = {r["kind"] for r in w.sql("SELECT kind FROM jobs")}
    c.get(url(rid))
    c.get(url(rid, extra="&relist=1"))
    assert w.sql("SELECT COUNT(*) FROM confirmations")[0][0] == before
    assert {r["kind"] for r in w.sql("SELECT kind FROM jobs")} == kinds | {"list_site_files"}
    for tab in ("report", "multiqc", "metrics"):
        t = c.get(url(rid, tab=tab)).text
        assert tabs(t)[0][2] is True and "<iframe" not in t and "<textarea" not in mid(t)


def test_ro13_the_station_may_list_the_results_folder(w):
    # TC-044: the run folder is <workDir>/runs/<name>, the results folder below it; both are inside the read roots of the station
    from abf_station import rules
    env = {"workDir": "/data/wd", "launchDir": "/data/launch", "readRoots": []}
    roots = rules.allowed_roots(env, "/nonexistent/settings")
    assert rules.inside(rules.normalize(FOLDER + "/results"), roots)


FAKE = "abf_FAKECREDENTIAL0123456789abcdef"


def test_ro14_nothing_internal_in_the_listing(w, caplog, capsys):
    # TC-093: a fake credential in the environment's config and in the jobs (their args, their answer, the site's own message) is nowhere
    # in the ready page, the error page, the MCP answers, the logs or what was printed
    from helpers import tool_json
    caplog.set_level(0)
    ann, c, rid = world(w)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET config_json = ?, description = ? WHERE name = 'lab-a'",
                    (json.dumps({"workDir": "/data/wd", "launchDir": "/data/launch", "secretNote": FAKE}), "note " + FAKE))
    con.close()
    seen = []

    def look(mcp=True):
        for lang in ("", "&lang=en"):
            r = c.get(url(rid) + lang)
            seen.append(r.text)
            seen.append(str(r.headers))
        if mcp:
            seen.append(json.dumps(tool_json(w.call("run_outputs", {"run_id": rid}, caller=ann))))
    look()
    job = listings(w)[0]["id"]
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET args_json = ? WHERE id = ?", (json.dumps({"path": FOLDER + "/results", "token": FAKE}), job))
    con.close()
    finish(w, job, entries=ENTRIES)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        row = con.execute("SELECT result_json FROM jobs WHERE id = ?", (job,)).fetchone()
        planted = json.loads(row[0])
        planted["token"] = FAKE
        planted["config"] = {"password": FAKE}
        con.execute("UPDATE jobs SET result_json = ? WHERE id = ?", (json.dumps(planted), job))
    con.close()
    look()
    t = mid(c.get(url(rid)).text)
    assert "config" not in t and "token" not in t.lower()
    finish(w, job, ok=False, message="cannot read the folder, token=%s was refused" % FAKE, state="error")
    look()
    finish(w, job, ok=False, message="no access", state="error", error="Traceback ... %s" % FAKE)
    look()
    assert any("no access" in x for x in seen), "the plain reason of the site should still be shown"
    printed = capsys.readouterr()
    for text in seen + [caplog.text, printed.out, printed.err]:
        assert FAKE not in text and "FAKECREDENTIAL" not in text
