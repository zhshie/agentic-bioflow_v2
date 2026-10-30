# Nothing existing: tests of the results files feature (folders in the Outputs tab, one-file download, summary-card links); the page, the route
# GET /run/file, the read_run_file job and its queueing are ours (specs/results-files/test-case.md).
"""results-files, platform and web side. Test cases are named in the comments (TC-001 ...)."""
import base64
import hashlib
import html
import json
import re
import socket
import sqlite3
import time
import urllib.parse

import pytest

from human_harness import World
from test_web_board import cjk, no_cjk, pane, plain, seed

NOW = time.time()
HOUR = 3600
FOLDER = "/data/wd/runs/ann-done"
RESULTS = FOLDER + "/results"
LIMIT = 26214400
BANNED = ["用過", "選好", "寫死", "自己填", "自己調整", "你還沒", "還沒有", "還不能", "這個", "這份", "這條", "這一版", "一下", "弄", "搞", "東西",
          "喔", "啦", "吧", "囉", "蠻"]      # DESIGN.md 用字; the single word 超 is checked apart, because 超過 is the plain word for "more than"
REPORT = "multiqc/multiqc_report.html"
STYLE_SHA256 = "6b2683ae09caee2a0e66778f2cde00e56e9ab500413829cf531c5c27ce8742f3"      # the stylesheet of the base (D13 pins it)
HTML_BYTES = b"<html><script>alert(1)</script>\xff\xfe\x00 binary \x80</html>\n"
INTERNAL = re.compile(r"Traceback|JobRefused|\bSELECT\b|sqlite|args_json|result_json|deadline_at|Exception|, line \d+")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


# ---- builders ---------------------------------------------------------------------------------------------------------

def launch_to(w, run_name, folder):
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE launches SET run_folder = ? WHERE run_name = ?", (folder, run_name))
    con.close()


def world(w, name="ann-done", launch_row=True, folder=None):
    ann = w.user("ann")
    rid = seed(w, name, "succeeded", ann, started=NOW - 3 * HOUR, ended=NOW - 2 * HOUR, counts=dict(succeeded=4), launch_row=launch_row)
    if launch_row:
        launch_to(w, name, folder if folder is not None else "/data/wd/runs/" + name)
    c = w.web()
    assert w.login(c, "ann").status_code == 303
    return ann, c, rid


def outputs_url(rid, path=None, lang=None):
    return "/?run=%s&stage=results&tab=outputs%s%s" % (rid, "&path=" + urllib.parse.quote(path, safe="/") if path is not None else "",
                                                       "&lang=en" if lang == "en" else "")


def file_url(rid, path, extra=""):
    return "/run/file?run=%s&path=%s%s" % (rid, urllib.parse.quote(path, safe="/"), extra)


def listings(w):
    return w.sql("SELECT * FROM jobs WHERE kind = 'list_site_files' ORDER BY id")


def listing_paths(w):
    return [json.loads(r["args_json"])["path"] for r in listings(w)]


def file_jobs(w):
    return w.sql("SELECT * FROM jobs WHERE kind = 'read_run_file' ORDER BY id")


def finish_listing(w, path, entries=None, ok=True, message=None, error=None):
    """Answer the newest list_site_files job whose path is `path` (rows are written as the agent's answer would be stored)."""
    row = [r for r in listings(w) if json.loads(r["args_json"])["path"] == path][-1]
    result = {"ok": ok, "path": path}
    if entries is not None:
        result.update(entries=entries, count=len(entries))
    if message:
        result["message"] = message
    if error:
        result["error"] = error
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET state = ?, result_json = ?, finished_at = ? WHERE id = ?",
                    ("done" if ok else "error", json.dumps(result), time.time(), row["id"]))
    con.close()


def entry(name, kind="file", size=100):
    return {"name": name, "type": kind, "size": size, "modified": "2026-10-20T08:00:00Z"}


def top_entries():
    return [entry("multiqc", "dir", 4096), entry("summary_report", "dir", 4096), entry("overall_summary.tsv", "file", 1292)]


def reply_file(w, state, result, job=None):
    """The agent's answer to the newest read_run_file job, through the real take_result (so clean_result judges it)."""
    from abf_platform import jobs
    job = job or file_jobs(w)[-1]
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET state = 'claimed', claimed_at = ? WHERE id = ?", (time.time(), job["id"]))
    con.close()
    code, body = jobs.take_result(w.ip.state_db, job["agent"], job["id"], state, result, time.time)
    assert code == 200 and body["accepted"], (code, body)


def ok_result(data, name="multiqc_report.html"):
    return {"ok": True, "status": "ok", "name": name, "size": len(data), "b64": base64.b64encode(data).decode("ascii")}


def mid(text):
    return pane(text, "middle")


def crumbs(text):
    m = re.search(r'<nav class="ostat" data-part="crumbs"[^>]*>(.*?)</nav>', mid(text), re.S)
    return m.group(1) if m else None


def table_rows(text):
    body = re.search(r"<tbody>(.*?)</tbody>", mid(text), re.S)
    return re.findall(r"<tr>(.*?)</tr>", body.group(1), re.S) if body else []


def hrefs(fragment):
    return [html.unescape(h) for h in re.findall(r'href="([^"]*)"', fragment)]


def cards(text):
    return re.findall(r'<h2 class="ct">(.*?)</h2><p class="cv">(.*?)</p>', mid(text), re.S)


def card(text, title):
    return [v for k, v in cards(text) if k == title][0]


def card_cells(text):
    """{card word: its html} of the two cells that hold the report links (they sit in the paragraph under the cards)."""
    body = re.search(r'</section><p class="kv">(.*?)</p><nav class="rtabs">', mid(text), re.S).group(1)
    return body


def open_file(w, c, rid, path, answer=None):
    """GET /run/file once (queues the job), answer it, GET again: the second response."""
    first = c.get(file_url(rid, path))
    assert first.status_code == 200
    reply_file(w, "done", answer)
    return c.get(file_url(rid, path))


# ---- US1: folders in the Outputs tab -------------------------------------------------------------------------------------

def test_tc001_folder_names_are_links_and_nested_paths_open(w):
    # TC-001
    ann, c, rid = world(w)
    c.get(outputs_url(rid))
    finish_listing(w, RESULTS, top_entries())
    t = c.get(outputs_url(rid)).text
    links = [h for h in hrefs(mid(t)) if "path=" in h and "/run/file" not in h]
    assert "/?run=%s&stage=results&tab=outputs&path=multiqc" % rid in links
    rows = table_rows(t)
    file_row = [r for r in rows if "overall_summary.tsv" in r][0]
    assert not [h for h in hrefs(file_row) if "tab=outputs" in h], "a file name is not an entering link"
    c.get(outputs_url(rid, "multiqc"))
    assert listing_paths(w)[-1] == RESULTS + "/multiqc"
    finish_listing(w, RESULTS + "/multiqc", [entry("multiqc_data", "dir"), entry("multiqc_report.html", "file", 1292)])
    t = c.get(outputs_url(rid, "multiqc")).text
    assert "multiqc_data" in plain(mid(t))
    assert any(h.endswith("tab=outputs&path=multiqc/multiqc_data") for h in hrefs(mid(t)))
    c.get(outputs_url(rid, "multiqc/multiqc_data"))
    assert listing_paths(w)[-1] == RESULTS + "/multiqc/multiqc_data"


def test_tc002_breadcrumbs_every_part_is_a_link(w):
    # TC-002
    ann, c, rid = world(w)
    c.get(outputs_url(rid, "multiqc/multiqc_data"))
    finish_listing(w, RESULTS + "/multiqc/multiqc_data", [entry("a.txt")])
    t = c.get(outputs_url(rid, "multiqc/multiqc_data")).text
    bar = crumbs(t)
    assert bar is not None and plain(bar) == "results / multiqc / multiqc_data"
    got = hrefs(bar)
    assert len(got) == 3
    assert got[0] == "/?run=%s&stage=results&tab=outputs" % rid and "path=" not in got[0]
    assert got[1] == "/?run=%s&stage=results&tab=outputs&path=multiqc" % rid
    assert got[2].endswith("path=multiqc/multiqc_data")
    root = crumbs(c.get(outputs_url(rid)).text)
    assert root is None or plain(root) == "results"


def test_tc003_download_column_has_a_link_per_file_and_none_for_folders(w):
    # TC-003
    ann, c, rid = world(w)
    c.get(outputs_url(rid, "multiqc"))
    finish_listing(w, RESULTS + "/multiqc", [entry("sub", "dir", 4096), entry("multiqc_report.html", "file", 1292), entry("exact.bin", "file", LIMIT)])
    t = c.get(outputs_url(rid, "multiqc")).text
    head = re.search(r"<thead>(.*?)</thead>", mid(t), re.S).group(1)
    assert [plain(x) for x in re.findall(r"<th>(.*?)</th>", head)] == ["名稱", "類型", "大小", "修改時間", "下載"]
    rows = {plain(r).split(" ")[0]: r for r in table_rows(t)}
    for name in ("multiqc_report.html", "exact.bin"):
        want = "/run/file?run=%s&path=multiqc/%s" % (rid, name)
        assert [h for h in hrefs(rows[name]) if "/run/file" in h] == [want], name
    assert not [h for h in hrefs(rows["sub"]) if "/run/file" in h]


def test_tc004_a_file_over_25_mb_has_no_link(w):
    # TC-004
    ann, c, rid = world(w)
    c.get(outputs_url(rid, "multiqc"))
    finish_listing(w, RESULTS + "/multiqc", [entry("big.bin", "file", LIMIT + 1)])
    t = c.get(outputs_url(rid, "multiqc")).text
    row = table_rows(t)[0]
    assert "超過 25 MB" in plain(row) and not [h for h in hrefs(row) if "/run/file" in h]


def test_tc005_waiting_unreadable_and_empty_subfolders(w):
    # TC-005 (a) waiting, (b) unreadable, (c) empty
    ann, c, rid = world(w)
    t = c.get(outputs_url(rid, "empty")).text
    assert "⟳" in t and "讀取中" in plain(mid(t)) and "每 15 秒自動更新" in plain(mid(t))
    finish_listing(w, RESULTS + "/empty", None, ok=False, error="not_found", message="the folder does not exist on the site")
    t = c.get(outputs_url(rid, "empty")).text
    m = plain(mid(t))
    assert "✗" in t and "無法讀取" in m and "重新讀取" in m and not INTERNAL.search(t)
    assert any("relist=1" in h and "path=empty" in h for h in hrefs(mid(t))), "the Read-again link keeps the folder"
    # (c): a new reading after Read again
    c.get(outputs_url(rid, "empty") + "&relist=1")
    finish_listing(w, RESULTS + "/empty", [])
    t = c.get(outputs_url(rid, "empty")).text
    assert "此資料夾沒有檔案。" in plain(mid(t))


BAD_PATHS = ["..", "multiqc/../x", "/etc", ".hidden", "multiqc/.x", "a" * 513]


@pytest.mark.parametrize("bad", BAD_PATHS)
def test_tc006_a_bad_path_shows_the_first_level_and_a_line_above_the_table(w, bad):
    # TC-006
    ann, c, rid = world(w)
    c.get(outputs_url(rid))
    finish_listing(w, RESULTS, top_entries())
    t = c.get("/", params={"run": rid, "stage": "results", "tab": "outputs", "path": bad}).text
    m = mid(t)
    assert "✕ 路徑不正確" in plain(m)
    assert m.index("路徑不正確") < m.index("<table"), "the line is above the table"
    assert "multiqc" in plain(m)
    assert set(listing_paths(w)) == {RESULTS}, "no listing was queued for the bad path"


def test_tc007_another_users_run_is_not_found_and_nothing_is_queued(w):
    # TC-007
    ann, c, rid = world(w)
    w.user("bob")
    d = w.web()
    assert w.login(d, "bob").status_code == 303
    mine = d.get(outputs_url(rid, "multiqc"))
    missing = d.get(outputs_url("no-such-run", "multiqc"))
    assert mine.status_code == 404 and missing.status_code == 404 and mine.text == missing.text
    assert "multiqc" not in mine.text and listings(w) == []


def test_tc008_the_first_level_keeps_its_columns_and_gets_the_new_one(w):
    # TC-008
    ann, c, rid = world(w)
    t = c.get(outputs_url(rid)).text
    assert "每 15 秒自動更新" in plain(mid(t))
    finish_listing(w, RESULTS, top_entries())
    t = c.get(outputs_url(rid)).text
    head = re.search(r"<thead>(.*?)</thead>", mid(t), re.S).group(1)
    assert [plain(x) for x in re.findall(r"<th>(.*?)</th>", head)] == ["名稱", "類型", "大小", "修改時間", "下載"]
    assert "重新讀取" in plain(mid(t)) and 'http-equiv="refresh"' in t

    cat = w.user("cat")
    rid2 = seed(w, "cat-nofolder", "succeeded", cat, started=NOW - 3 * HOUR, ended=NOW - 2 * HOUR, counts=dict(succeeded=4))
    launch_to(w, "cat-nofolder", "")
    c2 = w.web()
    assert w.login(c2, "cat").status_code == 303
    t = c2.get(outputs_url(rid2)).text
    assert "無輸出資料夾紀錄" in plain(mid(t)) and len(listings(w)) == 1


# ---- US2: downloading one file ---------------------------------------------------------------------------------------------

def test_tc009_010_the_bytes_come_back_as_they_are_and_only_as_a_download(w):
    # TC-009, TC-010
    ann, c, rid = world(w)
    r = open_file(w, c, rid, REPORT, ok_result(HTML_BYTES))
    assert r.status_code == 200 and r.content == HTML_BYTES
    assert r.headers["content-disposition"] == 'attachment; filename="multiqc_report.html"'
    assert r.headers["content-type"] == "application/octet-stream"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "private, no-store"
    assert "text/html" not in r.headers["content-type"]


def test_tc010_an_odd_file_name_stays_inside_the_header(w):
    # TC-010: quotes, backslashes, line breaks and non-ASCII letters cannot break out of the header
    ann, c, rid = world(w)
    name = 'we"ird\\na me;日本.txt'
    r = open_file(w, c, rid, "multiqc/" + name, ok_result(b"x", name))
    cd = r.headers["content-disposition"]
    assert r.status_code == 200 and cd.startswith("attachment;") and "\n" not in cd and '"we"ird' not in cd
    assert r.content == b"x"


def test_tc011_the_first_request_queues_one_job_and_shows_the_waiting_page(w):
    # TC-011
    ann, c, rid = world(w)
    r = c.get(file_url(rid, REPORT))
    rows = file_jobs(w)
    assert len(rows) == 1
    args = json.loads(rows[0]["args_json"])
    assert set(args) == {"ce", "run", "path"} and args["run"] == "ann-done" and args["path"] == REPORT and args["ce"]["name"] == "lab-a"
    assert rows[0]["compute_env"] == "lab-a"
    t = r.text
    assert r.status_code == 200 and 'http-equiv="refresh" content="15' in t
    body = plain(re.search(r"<main.*?</main>", t, re.S).group(0))
    assert body.startswith("◌ 正在向站台取得檔案，頁面每 15 秒自動更新。")
    assert any("tab=outputs" in h for h in hrefs(t)), "a link back to the Outputs tab, under the sentence"
    assert t.index("正在向站台取得檔案") < t.index("tab=outputs")


def test_tc012_an_answer_that_is_there_is_sent_without_a_new_job(w):
    # TC-012
    ann, c, rid = world(w)
    c.get(file_url(rid, REPORT))
    reply_file(w, "done", ok_result(HTML_BYTES))
    for _ in range(2):
        r = c.get(file_url(rid, REPORT))
        assert r.status_code == 200 and r.content == HTML_BYTES
    assert len(file_jobs(w)) == 1


def test_tc013_the_answer_is_kept_for_ten_minutes_and_a_running_job_is_not_doubled(w):
    # TC-013 (c): two requests while the job waits
    ann, c, rid = world(w)
    c.get(file_url(rid, REPORT))
    c.get(file_url(rid, REPORT))
    assert len(file_jobs(w)) == 1
    reply_file(w, "done", ok_result(HTML_BYTES))
    con = sqlite3.connect(str(w.ip.state_db))
    for age, expect_jobs, expect_bytes in ((599, 1, True), (601, 2, False)):         # TC-013 (a) and (b)
        with con:
            con.execute("UPDATE jobs SET finished_at = ? WHERE id = (SELECT MIN(id) FROM jobs WHERE kind = 'read_run_file')", (time.time() - age,))
        r = c.get(file_url(rid, REPORT))
        assert len(file_jobs(w)) == expect_jobs and (r.content == HTML_BYTES) is expect_bytes, age
    con.close()


def test_tc014_a_file_too_large_gets_the_size_and_the_site_path_and_no_bytes(w):
    # TC-014, TC-038
    ann, c, rid = world(w)
    c.get(file_url(rid, "multiqc/big.bin"))
    reply_file(w, "error", {"ok": False, "error": "too_large", "size": 30000000, "message": "too big"})
    r = c.get(file_url(rid, "multiqc/big.bin"))
    t = plain(re.search(r"<main.*?</main>", r.text, re.S).group(0))
    assert r.headers["content-type"].startswith("text/html")
    assert t.startswith("✕ 檔案大小 28.6 MB，超過網頁下載上限 25 MB。請於站台取得：" + RESULTS + "/multiqc/big.bin")
    assert any("tab=outputs" in h for h in hrefs(r.text))


def test_tc015_the_agent_off_or_not_answering_is_said_in_plain_words_with_a_retry(w):
    # TC-015: (a) the agent is offline
    ann, c, rid = world(w)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE agents SET last_seen_at = 0")
    r = c.get(file_url(rid, REPORT))
    t = plain(re.search(r"<main.*?</main>", r.text, re.S).group(0))
    assert "✕" in t and "代理" in t and "重試" in t and not INTERNAL.search(r.text) and file_jobs(w) == []
    assert any("retry=1" in h for h in hrefs(r.text))
    # (b) the job passed its deadline and nobody answered
    with con:
        con.execute("UPDATE agents SET last_seen_at = ?", (time.time(),))
    c.get(file_url(rid, REPORT))
    assert len(file_jobs(w)) == 1
    with con:
        con.execute("UPDATE jobs SET deadline_at = ? WHERE kind = 'read_run_file'", (time.time() - 5,))
    r = c.get(file_url(rid, REPORT))
    t = plain(re.search(r"<main.*?</main>", r.text, re.S).group(0))
    assert "✕" in t and "重試" in t and not INTERNAL.search(r.text) and len(file_jobs(w)) == 1
    # a click on Retry queues a new job
    r = c.get(file_url(rid, REPORT, "&retry=1"))
    assert len(file_jobs(w)) == 2 and "◌" in r.text
    con.close()


def test_tc015_a_site_that_cannot_be_reached_is_an_error_page(w):
    # TC-015
    ann, c, rid = world(w)
    c.get(file_url(rid, REPORT))
    reply_file(w, "error", {"ok": False, "error": "site_unreachable", "message": "The site could not do this (exit code 255)."})
    r = c.get(file_url(rid, REPORT))
    t = plain(re.search(r"<main.*?</main>", r.text, re.S).group(0))
    assert "✕" in t and "重試" in t and not INTERNAL.search(r.text) and r.headers["content-type"].startswith("text/html")


def test_tc016_a_missing_file_says_so_and_links_back(w):
    # TC-016
    ann, c, rid = world(w)
    c.get(file_url(rid, "summary_report/summary_report.html"))
    reply_file(w, "error", {"ok": False, "error": "not_found", "message": "gone"})
    r = c.get(file_url(rid, "summary_report/summary_report.html"))
    assert "站台沒有此檔案" in plain(r.text) and any("tab=outputs" in h for h in hrefs(r.text)) and r.headers["content-type"].startswith("text/html")


def test_tc017_a_folder_is_said_to_be_a_folder(w):
    # TC-017
    ann, c, rid = world(w)
    c.get(file_url(rid, "multiqc"))
    reply_file(w, "error", {"ok": False, "error": "not_a_file", "message": "x"})
    r = c.get(file_url(rid, "multiqc"))
    t = plain(re.search(r"<main.*?</main>", r.text, re.S).group(0))
    assert "資料夾" in t and "不是檔案" in t
    assert any(h.endswith("tab=outputs&path=multiqc") for h in hrefs(r.text))


@pytest.mark.parametrize("bad", ["", "../x", "multiqc/../x", "/etc/passwd", ".hidden", "multiqc/.x", "x" * 513, "a//b", "a/"])
def test_tc018_a_bad_path_is_refused_and_nothing_is_queued(w, bad):
    # TC-018
    ann, c, rid = world(w)
    r = c.get("/run/file", params={"run": rid, "path": bad})
    assert r.status_code == 400 and "路徑不正確" in plain(r.text) and file_jobs(w) == []
    assert r.headers["content-type"].startswith("text/html") and not INTERNAL.search(r.text)


def test_tc019_another_user_and_nobody_get_no_bytes(w):
    # TC-019
    ann, c, rid = world(w)
    c.get(file_url(rid, REPORT))
    reply_file(w, "done", ok_result(HTML_BYTES))
    w.user("bob")
    d = w.web()
    assert w.login(d, "bob").status_code == 303
    mine = d.get(file_url(rid, REPORT))
    missing = d.get(file_url("no-such-run", REPORT))
    assert mine.status_code == 404 and mine.text == missing.text and HTML_BYTES not in mine.content
    anon = w.web().get(file_url(rid, REPORT))
    assert anon.status_code in (302, 303) and anon.headers["location"] in ("/login", "/welcome") and HTML_BYTES not in anon.content
    assert len(file_jobs(w)) == 1, "nobody else queued a job"


def test_tc020_a_run_with_no_launch_record_queues_nothing(w):
    # TC-020: a run whose record names no folder; and a run with no record at all, which is nobody's and a 404 like on every page
    ann, c, rid = world(w, folder="")
    r = c.get(file_url(rid, REPORT))
    assert "✕" in r.text and "送出紀錄" in plain(r.text) and file_jobs(w) == []
    cat = w.user("cat")
    rid2 = seed(w, "cat-norecord", "succeeded", cat, started=NOW - 3 * HOUR, ended=NOW - 2 * HOUR, counts=dict(succeeded=4), launch_row=False)
    d = w.web()
    assert w.login(d, "cat").status_code == 303
    assert d.get(file_url(rid2, REPORT)).status_code == 404 and file_jobs(w) == []


def test_tc021_an_answer_whose_length_does_not_match_is_not_kept_as_a_file(w):
    # TC-021
    from abf_platform import jobs
    data = b"a" * 999
    bad = {"ok": True, "status": "ok", "name": "x.txt", "size": 1000, "b64": base64.b64encode(data).decode()}
    cleaned = jobs.clean_result("read_run_file", bad)
    assert cleaned["ok"] is False and "b64" not in cleaned
    ann, c, rid = world(w)
    c.get(file_url(rid, "x.txt"))
    reply_file(w, "done", bad)
    r = c.get(file_url(rid, "x.txt"))
    assert r.headers["content-type"].startswith("text/html") and "✕" in r.text and "重試" in plain(r.text) and data not in r.content
    stored = file_jobs(w)[0]["result_json"]
    assert base64.b64encode(data).decode() not in stored


def test_clean_result_judges_every_field_of_a_file_answer():
    # TC-021: the platform keeps only what it expects
    from abf_platform import jobs
    data = b"hello"
    good = jobs.clean_result("read_run_file", ok_result(data, "a.txt"))
    assert good["ok"] is True and good["size"] == 5 and base64.b64decode(good["b64"]) == data and good["name"] == "a.txt"
    for broken in (dict(ok_result(data), b64="not base64!"), dict(ok_result(data), size=-1), dict(ok_result(data), size=LIMIT + 1),
                   dict(ok_result(data), name="a/b"), dict(ok_result(data), size="5"), {k: v for k, v in ok_result(data).items() if k != "b64"}):
        assert jobs.clean_result("read_run_file", broken)["ok"] is False, broken
    big = jobs.clean_result("read_run_file", {"ok": False, "error": "too_large", "size": 30000000, "extra": "x"})
    assert big["error"] == "too_large" and big["size"] == 30000000 and "extra" not in big and "b64" not in big


def test_tc022_an_older_database_takes_the_new_kind_and_keeps_its_rows(tmp_path):
    # TC-022
    from abf_platform import jobs, store
    assert "read_run_file" in jobs.KINDS and jobs.DEADLINE_SECONDS["read_run_file"] == 60 and jobs.deadline_seconds("read_run_file") == 60
    db = tmp_path / "platform.db"
    store.connect_state(db).close()
    con = sqlite3.connect(str(db))
    sql_text = con.execute("SELECT sql FROM sqlite_master WHERE name = 'jobs'").fetchone()[0]
    old_sql = sql_text.replace(", 'read_run_file'", "")
    assert old_sql != sql_text
    con.execute("ALTER TABLE jobs RENAME TO jobs_cur")
    con.execute(old_sql)
    rows = [("a1", "lab-a", "preflight", "{}", "done", 1.0, 2.0), ("a1", "lab-a", "list_site_files", "{}", "queued", 3.0, 4.0),
            ("a1", "lab-a", "pipeline_files", "{}", "expired", 5.0, 6.0)]
    for r in rows:
        con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) VALUES (?,?,?,?,?,?,?)", r)
    con.execute("DROP TABLE jobs_cur")
    con.commit()
    cols = "id, agent, compute_env, kind, args_json, state, created_at, deadline_at"
    before = con.execute("SELECT %s FROM jobs ORDER BY id" % cols).fetchall()
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) VALUES ('a1','lab-a','read_run_file','{}','queued',1,2)")
    con.close()
    for _ in range(2):          # twice: upgrading again does no harm
        store.connect_state(db).close()
        con = sqlite3.connect(str(db))
        assert con.execute("SELECT %s FROM jobs ORDER BY id" % cols).fetchall() == before
        con.close()
    con = sqlite3.connect(str(db))
    con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) VALUES ('a1','lab-a','read_run_file','{}','queued',1,2)")
    assert con.execute("SELECT MAX(id) FROM jobs").fetchone()[0] == 4
    for bad in ("rm", "read_run_files", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) VALUES ('a1','lab-a',?,'{}','queued',1,2)", (bad,))
    con.close()


def test_tc022_the_deadline_can_be_set_by_the_environment(monkeypatch):
    # TC-022
    from abf_platform import jobs
    monkeypatch.setenv("ABF_PLATFORM_DEADLINE_READ_RUN_FILE", "120")
    assert jobs.deadline_seconds("read_run_file") == 120


# ---- US3: the summary cards ------------------------------------------------------------------------------------------------

def test_tc023_024_the_two_cards_become_download_links(w):
    # TC-023, TC-024
    ann, c, rid = world(w)
    c.get(outputs_url(rid))
    finish_listing(w, RESULTS, top_entries())
    t = c.get(outputs_url(rid)).text
    cells = card_cells(t)
    links = hrefs(cells)
    assert "/run/file?run=%s&path=multiqc/multiqc_report.html" % rid in links
    assert "/run/file?run=%s&path=summary_report/summary_report.html" % rid in links
    assert 'MultiQC 報告' in plain(cells) and 'href="/run/file?run=%s&amp;path=multiqc/multiqc_report.html"' % rid in cells
    tasks = c.get("/?run=%s&stage=results&tab=tasks" % rid).text          # the cards sit on every tab
    assert "multiqc_report.html" in tasks


def test_tc025_no_such_folder_says_the_pipeline_made_none(w):
    # TC-025
    ann, c, rid = world(w)
    c.get(outputs_url(rid))
    finish_listing(w, RESULTS, [entry("dada2", "dir"), entry("overall_summary.tsv")])
    cells = card_cells(c.get(outputs_url(rid)).text)
    assert plain(cells).count("此管線沒有產生") == 2 and not [h for h in hrefs(cells) if "/run/file" in h]


def test_tc025_a_file_called_multiqc_is_not_a_folder(w):
    # TC-025
    ann, c, rid = world(w)
    c.get(outputs_url(rid))
    finish_listing(w, RESULTS, [entry("multiqc", "file"), entry("summary_report", "link")])
    cells = card_cells(c.get(outputs_url(rid)).text)
    assert plain(cells).count("此管線沒有產生") == 2


def test_tc026_unknown_means_no_link_and_no_claim(w):
    # TC-026: still reading, and a failed reading
    ann, c, rid = world(w)
    cells = card_cells(c.get(outputs_url(rid)).text)
    assert "此管線沒有產生" not in plain(cells) and not [h for h in hrefs(cells) if "/run/file" in h]
    finish_listing(w, RESULTS, None, ok=False, error="not_found", message="no")
    cells = card_cells(c.get(outputs_url(rid)).text)
    assert "此管線沒有產生" not in plain(cells) and not [h for h in hrefs(cells) if "/run/file" in h]


def test_tc037_the_cards_keep_two_greyed_words_and_the_tabs_stay(w):
    # TC-037
    ann, c, rid = world(w)
    c.get(outputs_url(rid))
    finish_listing(w, RESULTS, top_entries())
    t = c.get(outputs_url(rid)).text
    cells = card_cells(t)
    for word in ("指標", "全部下載"):
        assert re.search(r'<span class="off">%s <span class="later">之後開放</span></span>' % word, cells), word
    nav = re.search(r'<nav class="rtabs">(.*?)</nav>', mid(t), re.S).group(1)
    assert [plain(x) for x in re.findall(r"<a [^>]*>(.*?)</a>", nav)] == ["輸出", "執行資訊", "任務", "日誌"]
    assert "<iframe" not in t and "<script" not in t


def test_tc037_038_only_one_new_route_and_no_bulk_download(w):
    # TC-037, TC-038, TC-039
    from starlette.routing import Route
    ann, c, rid = world(w)
    paths = sorted({r.path for r in c.app.routes if isinstance(r, Route)})
    assert "/run/file" in paths
    new = [p for p in paths if "run" in p or "download" in p or "zip" in p or "deliver" in p]
    assert new == ["/run/file"]


# ---- wording: both languages ----------------------------------------------------------------------------------------------

def pages(w, lang):
    """Rendered pages of every new state, in `lang` (zh: no extra query)."""
    ann, c, rid = world(w)
    suffix = "&lang=en" if lang == "en" else ""
    out = {}
    c.get(outputs_url(rid, lang=lang))
    finish_listing(w, RESULTS, top_entries())
    c.get(outputs_url(rid, "multiqc", lang))
    finish_listing(w, RESULTS + "/multiqc", [entry("multiqc_data", "dir"), entry("a.html", "file", 10), entry("big.bin", "file", LIMIT + 1)])
    out["outputs"] = c.get(outputs_url(rid, "multiqc", lang)).text
    out["bad"] = c.get(outputs_url(rid, "..", lang)).text
    c.get(outputs_url(rid, "empty", lang))
    finish_listing(w, RESULTS + "/empty", [])
    out["empty"] = c.get(outputs_url(rid, "empty", lang)).text
    out["waiting"] = c.get(file_url(rid, "multiqc/a.html", suffix)).text
    reply_file(w, "error", {"ok": False, "error": "too_large", "size": 30000000})
    out["too_large"] = c.get(file_url(rid, "multiqc/a.html", suffix)).text
    for code in ("not_found", "not_a_file", "site_unreachable", "not_on_site", "changed"):
        c.get(file_url(rid, "multiqc/" + code, suffix))
        reply_file(w, "error", {"ok": False, "error": code, "message": "m"})
        out[code] = c.get(file_url(rid, "multiqc/" + code, suffix)).text
    out["bad_path"] = c.get("/run/file?run=%s&path=..%s" % (rid, suffix)).text
    return out


def test_tc027_english_pages_have_no_chinese(w):
    # TC-027
    for name, t in pages(w, "en").items():
        assert no_cjk(t), (name, cjk(t))


def test_tc027_044_chinese_pages_use_written_language_and_state_symbols(w):
    # TC-027, TC-044
    got = pages(w, "zh")
    for name, t in got.items():
        main = re.search(r"<main.*?</main>", t, re.S)
        text = plain(mid(t) if 'data-pane="middle"' in t else main.group(0))
        for banned in BANNED:
            assert banned not in text, (name, banned)
        assert "超" not in text.replace("超過", ""), name
        assert "style=" not in t and "<script" not in t and "<iframe" not in t, name
        assert not re.search(r'(src|href|action)="https?://', t), name
        assert len(re.findall(r"<style>", t)) == 1, name
    assert "✕" in plain(got["bad_path"]) and "◌" in plain(got["waiting"]) and "✕" in plain(got["too_large"])
    for code in ("not_found", "not_a_file", "site_unreachable", "not_on_site", "changed"):
        assert "✕" in plain(got[code]), code
    assert "此環境的結果檔不在站台主機上" in plain(got["not_on_site"])
    assert "✕ 路徑不正確" in plain(mid(got["bad"]))
    assert "此資料夾沒有檔案。" in plain(mid(got["empty"]))


def test_tc034_a_cloud_environment_says_the_files_are_not_on_the_site_host(w):
    # TC-034
    ann, c, rid = world(w)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET platform = 'awsbatch-platform' WHERE name = 'lab-a'")
    con.close()
    r = c.get(file_url(rid, REPORT))
    assert "此環境的結果檔不在站台主機上" in plain(r.text) and file_jobs(w) == [] and r.headers["content-type"].startswith("text/html")


# ---- the whole way, and the limits --------------------------------------------------------------------------------------------

def test_tc035_the_maintainers_walk_works_with_links_only(w):
    # TC-035
    ann, c, rid = world(w)
    t = c.get("/?run=%s" % rid).text                                  # the results stage is the default page of a finished run
    assert "輸出" in plain(mid(t))
    c.get(outputs_url(rid))
    finish_listing(w, RESULTS, top_entries())
    t = c.get(outputs_url(rid)).text
    step = [h for h in hrefs(mid(t)) if h.endswith("tab=outputs&path=multiqc")][0]
    c.get(step)
    finish_listing(w, RESULTS + "/multiqc", [entry("multiqc_report.html", "file", len(HTML_BYTES))])
    t = c.get(step).text
    link = [h for r in table_rows(t) for h in hrefs(r) if h.startswith("/run/file")][0]
    assert link == "/run/file?run=%s&path=multiqc/multiqc_report.html" % rid
    first = c.get(link)
    assert "◌" in first.text
    reply_file(w, "done", ok_result(HTML_BYTES))
    final = c.get(link)
    assert final.content == HTML_BYTES
    assert [p for p in re.findall(r"(?:zip|tar|all)", link)] == []


def test_tc039_style_and_csp_are_those_of_the_base(w):
    # TC-039: the sha256 of the stylesheet is the one of the base; every page names the same policy
    from abf_platform import web_board
    assert hashlib.sha256(web_board.STYLE.encode("utf-8")).hexdigest() == STYLE_SHA256
    ann, c, rid = world(w)
    c.get(outputs_url(rid))
    finish_listing(w, RESULTS, top_entries())
    policy = None
    for url in ("/", "/settings", "/usage", outputs_url(rid), file_url(rid, REPORT), file_url(rid, "..")):
        csp = c.get(url).headers["content-security-policy"]
        policy = policy or csp
        assert csp == policy, url
    assert policy == ("default-src 'none'; style-src 'sha256-%s'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
                      % base64.b64encode(hashlib.sha256(web_board.STYLE.encode("utf-8")).digest()).decode())


def test_tc039_no_new_mcp_tool(w):
    # TC-039
    tools, _ = w.mcp([])
    names = {t.name for t in tools}
    assert not [n for n in names if "run_file" in n or "download" in n]


def test_tc041_a_download_asks_for_no_confirmation_and_reaches_nowhere(w, monkeypatch):
    # TC-041
    ann, c, rid = world(w)
    reached = []
    real = socket.socket.connect
    monkeypatch.setattr(socket.socket, "connect", lambda self, *a: reached.append(a) or real(self, *a))
    before = (w.sql("SELECT COUNT(*) FROM confirmations")[0][0], w.sql("SELECT COUNT(*) FROM launches")[0][0])
    c.get(file_url(rid, REPORT))
    reply_file(w, "done", ok_result(HTML_BYTES))
    c.get(file_url(rid, REPORT))
    c.get(file_url(rid, "multiqc/big.bin"))
    reply_file(w, "error", {"ok": False, "error": "too_large", "size": LIMIT + 5})
    c.get(file_url(rid, "multiqc/big.bin"))
    assert reached == []
    assert (w.sql("SELECT COUNT(*) FROM confirmations")[0][0], w.sql("SELECT COUNT(*) FROM launches")[0][0]) == before
    assert {r["kind"] for r in w.sql("SELECT kind FROM jobs")} - {"preflight"} == {"read_run_file"}


def test_tc042_the_route_calls_the_action_and_holds_no_logic_of_its_own():
    # TC-042
    import ast
    from pathlib import Path
    from abf_platform import actions
    src = (Path(actions.__file__).parent.parent / "web.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_file_get"][0]
    called = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "actions"}
    assert called == {"Caller", "run_file"}
    names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    assert not names & {"jobs", "store", "sqlite3", "open", "Path", "base64", "os"}, names & {"jobs", "store", "sqlite3", "open", "Path", "base64", "os"}


def test_tc043_nothing_secret_is_in_a_page_or_a_log(w, caplog):
    # TC-043
    ann, c, rid = world(w)
    cookie = c.cookies.get("abf_web")
    caplog.set_level("DEBUG")
    texts = []
    for state, result in (("error", {"ok": False, "error": "site_unreachable", "message": "Traceback (most recent call last): token=abc123 password=hunter2"}),
                          ("refused", {"ok": False, "message": "the path leads out of the results folder (捷徑指向 results 資料夾之外)"})):
        c.get(file_url(rid, "multiqc/%s.txt" % state))
        reply_file(w, state, result)
        texts.append(c.get(file_url(rid, "multiqc/%s.txt" % state)).text)
    texts.append(c.get(outputs_url(rid, "multiqc")).text)
    for t in texts:
        assert cookie not in t and "hunter2" not in t and "abc123" not in t and not INTERNAL.search(t)
    assert cookie not in caplog.text and "hunter2" not in caplog.text




def test_tc036_045_the_docs_carry_the_section_and_the_manual_steps():
    # TC-036, TC-045
    from pathlib import Path
    docs = Path(__file__).resolve().parents[2] / "docs"
    platform_doc = (docs / "PLATFORM.md").read_text(encoding="utf-8")
    section = platform_doc.split("## 下載結果檔", 1)[1].split("\n## ", 1)[0]
    assert "25 MB" in section and "opens no connection" in section and "read_run_file" in section and "base64" in section
    testing = (docs / "TESTING.md").read_text(encoding="utf-8")
    steps = testing.split("## 結果頁下載 (results-files)", 1)[1].split("\n## ", 1)[0]
    assert "multiqc_report.html" in steps and "390 px" in steps and "web-test-1" in steps
