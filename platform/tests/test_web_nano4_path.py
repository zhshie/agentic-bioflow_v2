# Nothing existing: tests of the three gaps of the web path to the national HPC (samplesheet upload, the page after Send, the Compute card); no library plays a browser that posts a multipart form to this site.
"""web-nano4-path. TC ids refer to specs/web-nano4-path/test-case.md. Everything runs in process on databases under tmp_path: no network, no site."""
import hashlib
import os
import re
import sqlite3
import time

import pytest

from human_harness import World, csrf_of, form_answer
from owner_harness import sql_exec, sql_rows
from test_clean_page import mask, run_and_request
from test_confirm_page import logged_in
from test_web_board import no_cjk, pane, plain, seed
from test_web_upload import BANNED, BOUNDARY, CTYPE, FETCH, Up, middle, upload_token

SHEET = "sample,fastq_1,fastq_2,strandedness\n" + "".join(
    "s%d,/site/r5/s%d_1.fq.gz,/site/r5/s%d_2.fq.gz,auto\n" % (i, i, i) for i in range(10))
DOC_ZH = "國網環境的資料目前請用指令上傳"


@pytest.fixture
def up(tmp_path, monkeypatch):
    return Up(tmp_path, monkeypatch)


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def slurm_only(up):
    """alice has one available national-HPC environment and nothing else."""
    up.slurm_for_alice()
    sql_exec(up.state, "UPDATE compute_envs SET status = 'invalid' WHERE name = 'gcb1'")


def sheet_form(token, files, boundary=BOUNDARY):
    out = []
    if token is not None:
        out.append(('--%s\r\nContent-Disposition: form-data; name="csrf"\r\n\r\n' % boundary).encode() + token.encode() + b"\r\n")
    for filename, data in files:
        fn = filename if isinstance(filename, bytes) else filename.encode("utf-8")
        data = data if isinstance(data, bytes) else data.encode("utf-8")
        out.append(('--%s\r\nContent-Disposition: form-data; name="sheet"; filename="' % boundary).encode() + fn
                   + b'"\r\nContent-Type: text/csv\r\n\r\n' + data + b"\r\n")
    if not files:      # the browser's empty file box
        out.append(('--%s\r\nContent-Disposition: form-data; name="sheet"; filename=""\r\nContent-Type: application/octet-stream\r\n\r\n\r\n' % boundary).encode())
    out.append(("--%s--\r\n" % boundary).encode())
    return b"".join(out)


def put(up, files, c=None, token=FETCH, query="", headers=None):
    c = c or up.client()
    tok = upload_token(c.get("/upload" + query).text) if token is FETCH else token
    h = {"content-type": CTYPE}
    h.update(headers or {})
    return c.post("/upload" + query, content=sheet_form(tok, files), headers=h)


def sheets_dir(up, who="alice"):
    return up.area(who) / "sheets"


def stored(up, who="alice"):
    d = sheets_dir(up, who)
    return sorted(p.name for p in d.iterdir()) if d.exists() else []


def everything(up):
    return sorted(str(p.relative_to(up.uploads)) for p in up.uploads.rglob("*") if p.is_file())


def launch_options(up, who="alice"):
    return re.findall(r'<option value="(sheets/[^"]*)"', up.client(who).get("/launch").text)


def saved_ok(up, name="s1.csv", data=SHEET, **kw):
    r = put(up, [(name, data)], **kw)
    assert r.status_code == 303, r.text
    return r


# ---------------------------------------------------------------- US1
def test_tc001_slurm_only_page_has_the_sheet_form(up):
    # TC-001
    slurm_only(up)
    r = up.client().get("/upload")
    assert r.status_code == 200
    m = pane(r.text, "middle")
    assert "上傳樣本表（CSV 或 TSV）" in plain(m) and DOC_ZH not in r.text and "沒有可用的運算環境" not in r.text
    forms = re.findall(r"<form\b[^>]*>(.*?)</form>", m, re.S)
    assert len(forms) == 1
    f = forms[0]
    assert len(re.findall(r'type="file"', f)) == 1 and "multiple" not in f and "required" in f and 'name="csrf"' in f
    assert re.search(r'<form[^>]*method="post"[^>]*action="/upload"', m)
    assert "fastq" not in f.lower()


def test_tc002_saved_as_is_and_redirects(up):
    # TC-002
    slurm_only(up)
    r = saved_ok(up)
    loc = r.headers["location"]
    assert loc.split("?")[0] == "/upload" and "notice=sheet_saved" in loc.split("?", 1)[1]
    assert (sheets_dir(up) / "s1.csv").read_bytes() == SHEET.encode()


def test_tc003_success_sentence_before_the_form(up):
    # TC-003
    slurm_only(up)
    loc = saved_ok(up).headers["location"]
    m = pane(up.client().get(loc).text, "middle")
    assert "✓ 已上傳樣本表 sheets/s1.csv，可於「送出新分析」第 4 步選擇。" in plain(m)
    assert m.index("已上傳樣本表") < m.index("<form")
    after = m[m.index("已上傳樣本表"):]
    assert re.search(r'<a [^>]*href="/launch"[^>]*>前往送出新分析</a>', after) and 'type="file"' in m


def test_tc004_launch_lists_the_uploaded_sheets(up):
    # TC-004
    slurm_only(up)
    saved_ok(up, "s1.csv")
    saved_ok(up, "t1.tsv", SHEET.replace(",", "\t"))
    assert launch_options(up) == ["sheets/s1.csv", "sheets/t1.tsv"]


def test_tc005_names_are_cleaned_and_stay_inside_sheets(up):
    # TC-005
    slurm_only(up)
    names = ["my sample 表.csv", "樣本.csv", "a/b.csv", "..hidden.csv", ".csv", ".tsv", "a-b_c.1.tsv"]
    want = ["my_sample__.csv", "__.csv", "a_b.csv", "hidden.csv", "sheet.csv", "sheet.tsv", "a-b_c.1.tsv"]
    before = everything(up)
    for n in names:
        saved_ok(up, n)
    assert stored(up) == sorted(want)
    new = [p for p in everything(up) if p not in before]
    assert all(p.startswith("alice/sheets/") for p in new), new
    assert sorted(launch_options(up)) == sorted("sheets/" + n for n in want)


def test_tc006_same_name_is_numbered_never_overwritten(up):
    # TC-006
    slurm_only(up)
    A, B, C = (SHEET + "x%d,a,b,c\n" % i for i in range(3))
    saved_ok(up, "s1.csv", A)
    r = saved_ok(up, "s1.csv", B)
    assert "s1-2.csv" in r.headers["location"]
    assert "sheets/s1-2.csv" in plain(pane(up.client().get(r.headers["location"]).text, "middle"))
    saved_ok(up, "s1.csv", C)
    d = sheets_dir(up)
    assert (d / "s1.csv").read_text() == A and (d / "s1-2.csv").read_text() == B and (d / "s1-3.csv").read_text() == C


def test_tc007_one_megabyte_limit(up):
    # TC-007
    slurm_only(up)
    head = b"h1,h2,h3\n"
    exact = head + (b"1,2," + b"x" * 94 + b"\n") * 10000
    exact += b"1,2," + b"x" * (1048576 - len(exact) - len(b"1,2,\n")) + b"\n"
    assert len(exact) == 1048576
    r0 = put(up, [("big.csv", exact)])
    assert r0.status_code == 303, error_sentence(r0.text)
    before = everything(up)
    r = put(up, [("big2.csv", exact + b"x")])
    assert r.status_code == 400 and "✕" in r.text and "1 MB" in plain(pane(r.text, "middle"))
    assert everything(up) == before


BAD_CASES = {
    "big": ([("b.csv", b"a,b\n" + b"1,2\n" * 400000)], "1 MB"),
    "ext": ([("notes.txt", SHEET)], ".csv"),
    "utf8": ([("bad.csv", "名稱,值\n樣本,1\n".encode("big5"))], "UTF-8"),
    "ragged": ([("ragged.csv", "a,b,c,d\n1,2,3,4\n1,2,3\n")], "欄數"),
    "header": ([("header_only.csv", "a,b,c\n")], "資料列"),
    "none": ([], "選"),
    "two": ([("a.csv", SHEET), ("b.csv", SHEET)], "一次"),
}


def error_sentence(page):
    found = re.findall(r'<p class="bad">(✕[^<]*)</p>', pane(page, "middle"))
    assert len(found) == 1, found
    return found[0]


def test_tc008_to_tc013_every_refusal_has_its_own_sentence_and_writes_nothing(up):
    # TC-008, TC-009, TC-010, TC-011, TC-012, TC-013
    slurm_only(up)
    before = everything(up)
    seen = {}
    for key, (files, word) in BAD_CASES.items():
        r = put(up, files)
        assert r.status_code == 400, (key, r.status_code)
        s = error_sentence(r.text)
        assert word in s, (key, s)
        seen[key] = s
        m = pane(r.text, "middle")
        assert m.index("✕") < m.index("<form") and "已上傳樣本表" not in r.text and 'type="file"' in m
        assert "登出" in r.text
    assert len(set(seen.values())) == 7
    for name in ("s.xlsx", "sheet"):
        r = put(up, [(name, SHEET)])
        assert r.status_code == 400 and ".csv" in error_sentence(r.text) and ".tsv" in error_sentence(r.text)
    assert everything(up) == before


def test_tc014_csrf_origin_login(up):
    # TC-014
    from test_temp_password import login_temp
    slurm_only(up)
    up.w.user("ann")
    before = everything(up)
    assert put(up, [("s.csv", SHEET)], token=None).status_code == 403
    assert put(up, [("s.csv", SHEET)], token="wrong").status_code == 403
    assert put(up, [("s.csv", SHEET)], headers={"origin": "https://elsewhere.example"}).status_code == 403
    anon = up.anon()
    g = anon.get("/upload")
    assert g.status_code == 303 and g.headers["location"].startswith("/login")
    r = anon.post("/upload", content=sheet_form("x", [("s.csv", SHEET)]), headers={"content-type": CTYPE})
    assert r.status_code == 303 and r.headers["location"].startswith("/login")
    assert everything(up) == before
    c, _, _ = login_temp(up.w)
    for r in (c.get("/upload"), c.post("/upload", content=sheet_form("x", [("s.csv", SHEET)]), headers={"content-type": CTYPE})):
        assert r.status_code == 303 and r.headers["location"] == "/welcome"
    assert everything(up) == before


def test_tc015_nobody_sees_anybody_elses_sheets(up):
    # TC-015
    slurm_only(up)
    up.d.bobs_environment()
    saved_ok(up, "mine.csv")
    c = up.client("bob")
    assert put(up, [("bobs.csv", SHEET)], c=c).status_code == 303
    assert (up.area("bob") / "sheets" / "bobs.csv").exists() and not (up.area("alice") / "sheets" / "bobs.csv").exists()
    assert launch_options(up, "alice") == ["sheets/mine.csv"]
    assert "mine.csv" not in c.get("/launch").text and "bobs.csv" in c.get("/launch").text


def test_tc016_cloud_only_pages_are_what_they_were(up):
    # TC-016 (the hashes are those of the pages of base for a person with a cloud environment only)
    c = up.client()

    def h(t):
        return hashlib.sha256(mask(t).encode()).hexdigest()[:16]
    zh, en = c.get("/upload").text, c.get("/upload?lang=en").text
    assert h(zh) == "a613e122a237e6fa" and h(en) == "c7fb04b4c64f30b4"
    assert 'name="sheet"' not in zh
    assert up.ok()


def test_tc017_both_kinds_cloud_first(up):
    # TC-017
    up.slurm_for_alice()
    m = pane(up.client().get("/upload").text, "middle")
    assert m.index('name="fastq"') < m.index("大檔指令") < m.index('name="sheet"')
    assert len(re.findall(r"<form\b", m)) == 2
    assert up.post().status_code == 303
    assert put(up, [("s.csv", SHEET)]).status_code == 303


def test_tc018_a_national_environment_that_is_not_available_gives_no_sheet_form(up):
    # TC-018
    up.slurm_for_alice()
    sql_exec(up.state, "UPDATE compute_envs SET status = 'invalid' WHERE name = 'nchc1'")
    t = up.client().get("/upload").text
    assert 'name="sheet"' not in t and 'name="fastq"' in t
    assert put(up, [("s.csv", SHEET)]).status_code == 400
    assert stored(up) == []


def test_tc019_no_environment_is_one_sentence_and_a_link(up):
    # TC-019
    sql_exec(up.state, "UPDATE compute_envs SET status = 'invalid' WHERE name = 'gcb1'")
    c = up.client()
    zh = pane(c.get("/upload").text, "middle")
    en_page = c.get("/upload?lang=en").text
    en = pane(en_page, "middle")
    assert "沒有可用的運算環境。請先到設定頁建立並檢查運算環境。" in plain(zh)
    assert "No compute environment is ready. Create and check one on the Settings page first." in plain(en)
    assert 'href="/settings' in zh and 'href="/settings' in en
    for m in (zh, en):
        assert "<form" not in m and 'type="file"' not in m and "<button" not in m
    assert no_cjk(en_page)


def test_tc020_english_sheet_section(up):
    # TC-020
    slurm_only(up)
    t = up.client().get("/upload?lang=en").text
    assert 'name="sheet"' in pane(t, "middle") and no_cjk(t)
    r = put(up, [("s.csv", SHEET)], query="?lang=en")
    assert r.status_code == 303 and "lang=en" in r.headers["location"]
    page = up.client().get(r.headers["location"]).text
    assert no_cjk(page) and "sheets/s.csv" in page and 'href="/launch?lang=en"' in page


def test_tc021_no_fastq_to_a_national_environment(up):
    # TC-021
    slurm_only(up)
    assert 'name="fastq"' not in up.client().get("/upload").text
    r = up.post(ce="nchc1")
    assert r.status_code == 400 and up.jobs() == []


def test_tc022_list_samplesheets_rules_unchanged(up):
    # TC-022
    from abf_platform import actions
    a = up.area("alice")
    (a / "d1" / "d2" / "d3" / "d4").mkdir(parents=True)
    (a / "a.txt").write_text("x")
    (a / ".hidden.csv").write_text("x")
    (a / "d1" / "d2" / "d3" / "d4" / "deep.csv").write_text("x")
    os.symlink(str(up.uploads), str(a / "link.csv"))
    (a / "many").mkdir()
    for i in range(201):
        (a / "many" / ("f%03d.csv" % i)).write_text("x")
    got = actions.list_samplesheets(up.state, caller=up.a)
    assert len(got) == 200 and got[0] == "many/f000.csv" and not any(n in got for n in ("a.txt", ".hidden.csv", "link.csv"))
    assert not any("deep" in n for n in got)


# ---------------------------------------------------------------- US2
def pressed(w, ann, run="web-t1"):
    c = logged_in(w, "ann")
    rid = w.launch(caller=ann, run=run)["id"]
    return c, rid, csrf_of(c.get("/c/" + rid).text)


def test_tc023_after_send(w):
    # TC-023
    ann = w.user("ann")
    c, rid, token = pressed(w, ann)
    r = c.post("/c/" + rid, data={"csrf": token})
    jobs = w.jobs("launch_nextflow")
    assert r.status_code == 200 and len(jobs) == 1
    t = r.text
    a, b = "已送出。工作編號 %s。" % jobs[0]["id"], "站台開始執行後，進度會顯示在分析清單。"
    assert t.index(a) < t.index(b) < t.index("查看進度")
    assert re.search(r'<a [^>]*href="/\?run_name=web-t1"[^>]*>查看進度</a>', t)
    for gone in ("回到 AI", "再呼叫", "用同樣的參數"):
        assert gone not in t
    assert not cjk_free_words(t)


def cjk_free_words(t):
    """English words in the body text (the page after Send is Chinese only)."""
    body = re.sub(r"<[^>]+>", " ", re.sub(r"<style>.*?</style>", "", t, flags=re.S))
    return re.findall(r"\b[A-Za-z]{4,}\b", body.replace("web-t1", ""))


def test_tc024_other_kinds_and_repeat(w):
    # TC-024
    from test_clean_page import launch_and_cancel
    ann = w.user("ann")
    w.clock.t = time.time()
    launch, cancel = launch_and_cancel(w, ann)
    c = logged_in(w, "ann")
    for rid in (launch, cancel):
        token = csrf_of(c.get("/c/" + rid).text)
        r = c.post("/c/" + rid, data={"csrf": token})
        again = c.post("/c/" + rid, data={"csrf": token})
        for page in (r.text, again.text):
            assert "回到 AI" not in page and "已送出。工作編號" in page
            assert re.search(r'<a [^>]*href="/\?run_name=run-(?:one|two)"[^>]*>查看進度</a>', page)
        assert "站台開始執行後，進度會顯示在分析清單。" in r.text


def test_tc025_clean_work_page_is_what_it_was(w):
    # TC-025
    w.clock.t = time.time()
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    r = c.post("/c/" + rid, data={"csrf": csrf_of(c.get("/c/" + rid).text)})
    job = w.sql("SELECT id FROM jobs WHERE kind = 'clean_work'")[0]["id"]
    assert "已送出。工作編號 %s。代理會開始清理這個 run 的中間檔；結果不會被動。" % job in r.text
    assert "查看進度" not in r.text and "站台開始執行後" not in r.text and "回到 AI" not in r.text


def test_tc026_error_pages_say_resubmit(w):
    # TC-026
    ann = w.user("ann")
    w.clock.t = time.time()
    rid = w.launch(caller=ann, run="web-e1")["id"]
    c = logged_in(w, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    w.launch(caller=ann, answer=form_answer("decline"), run="web-e2")
    void_id = [x["id"] for x in w.confirmations() if x["state"] == "void"][0]
    v = c.get("/c/" + void_id)
    assert v.status_code == 409 and "請重新送出。" in v.text and "回到 AI" not in v.text
    w.clock.t += 700
    e = c.get("/c/" + rid)
    assert "10 分鐘" in e.text and "請重新送出。" in e.text and "回到 AI" not in e.text
    p = c.post("/c/" + rid, data={"csrf": token})
    assert p.status_code == 410 and "未送出：" in p.text and "請重新送出。" in p.text and "回到 AI" not in p.text


def test_tc028_run_name_is_the_same_page_as_the_id(w):
    # TC-028
    ann = w.user("ann")
    rid = seed(w, "web-t1", "running", ann)
    c = logged_in(w, "ann")
    a, b = c.get("/?run_name=web-t1"), c.get("/?run=" + rid)
    assert a.status_code == 200 and mask(a.text) == mask(b.text)


def test_tc029_waiting_page(w):
    # TC-029
    ann = w.user("ann")
    w.hand_over(by=ann, run="web-t2")
    c = logged_in(w, "ann")
    r = c.get("/?run_name=web-t2")
    m = pane(r.text, "middle")
    assert r.status_code == 200 and "<h1>web-t2</h1>" in m
    assert "◌ 已送出，等待站台回報執行狀態。頁面每 15 秒自動更新。" in plain(m)
    assert 'http-equiv="refresh" content="15"' in r.text and 'href="/"' in m
    rid = seed(w, "web-t2", "running", None, launch_row=False)
    assert mask(c.get("/?run_name=web-t2").text) == mask(c.get("/?run=" + rid).text)


def test_tc030_not_yours_or_not_there_is_the_plain_404(w):
    # TC-030
    w.user("ann")
    bob = w.user("bob")
    seed(w, "web-bob", "running", bob)
    w.hand_over(by=bob, run="web-bob2")
    c = logged_in(w, "ann")
    base = c.get("/?run=nothing-at-all")
    assert base.status_code == 404
    for name in ("web-bob", "web-bob2", "ghost"):
        r = c.get("/?run_name=" + name)
        assert r.status_code == 404 and r.text == base.text and name not in r.text


def test_tc031_run_param_is_unchanged(w):
    # TC-031
    ann = w.user("ann")
    rid = seed(w, "web-t1", "running", ann)
    c = logged_in(w, "ann")
    assert c.get("/?run=" + rid).status_code == 200
    assert c.get("/?run=web-t1").status_code == 404 and c.get("/?run=nope").status_code == 404


def test_tc032_the_whole_path_without_a_command(up):
    # TC-032
    slurm_only(up)
    w = up.w
    t = up.client().get("/upload").text
    assert 'name="sheet"' in t and DOC_ZH not in t
    page = up.client().get(saved_ok(up, "g1.csv").headers["location"]).text
    assert 'href="/launch"' in page
    assert "sheets/g1.csv" in up.client().get("/launch").text
    c = up.client()
    rid = w.launch(caller=up.a, run="web-t3", ce_name="nchc1")["id"]
    r = c.post("/c/" + rid, data={"csrf": csrf_of(c.get("/c/" + rid).text)})
    assert 'href="/?run_name=web-t3"' in r.text
    waiting = c.get("/?run_name=web-t3")
    assert "等待站台回報" in waiting.text
    seed(w, "web-t3", "running", None, launch_row=False)
    assert "等待站台回報" not in c.get("/?run_name=web-t3").text
    for body in (t, page, r.text, waiting.text):
        assert "回到 AI" not in body and "請用指令上傳" not in body


def test_tc033_mcp_text_is_unchanged():
    # TC-033
    from abf_platform import actions
    assert "用同樣的參數再呼叫" in open(actions.__file__, encoding="utf-8").read()


# ---------------------------------------------------------------- US3
def set_ce(w, name, ce):
    sql_exec(w.ip.state_db, "UPDATE launches SET ce = ? WHERE run_name = ?", (ce, name))


def card(t):
    found = re.findall(r'<h2 class="ct">(?:運算環境|Compute)</h2><p class="cv">([^<]*)</p>', t)
    return found[0] if found else None


def test_tc034_card_shows_the_environment(w):
    # TC-034
    ann = w.user("ann")
    ids = {st: seed(w, "n-" + st, st, ann, counts=dict(succeeded=1)) for st in ("running", "failed", "succeeded")}
    for st in ids:
        set_ce(w, "n-" + st, "nano4")
    c = logged_in(w, "ann")
    for st, rid in ids.items():
        for q in ("", "&lang=en"):
            urls = ["/?run=%s%s" % (rid, q)]
            if st == "succeeded":
                urls += ["/?run=%s&stage=%s%s" % (rid, s, q) for s in ("results", "finished")]
            cards = [card(c.get(u).text) for u in urls]
            assert "nano4" in cards, (st, q, cards)
            assert "—" not in [x for x in cards if x is not None]


def test_tc035_no_launch_record_keeps_the_dash(w):
    # TC-035: a run whose hand-off record names no environment (the page can only be asked for runs of the person, so the record exists but is empty)
    ann = w.user("ann")
    rid = seed(w, "outside", "running", ann)
    set_ce(w, "outside", "")
    t = logged_in(w, "ann").get("/?run=" + rid)
    assert t.status_code == 200 and card(t.text) == "—"
    from abf_platform import web_board
    view = dict(__import__("abf_platform.actions", fromlist=["x"]).get_run(w.ip.index, rid, platform_path=w.ip.state_db))
    assert "compute_env" not in view      # the action's answer is not changed
    assert card(web_board.render_board("ann", "x", [], view, None, "zh", None, time.time())) == "—"


def test_tc036_newest_record_wins(w):
    # TC-036
    ann = w.user("ann")
    rid = seed(w, "twice", "running", ann)
    set_ce(w, "twice", "nano4-old")
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)",
                    ("twice", "/f/twice", "nano4", "agent-t", time.time(), ann.user_id))
    con.close()
    t = logged_in(w, "ann").get("/?run=" + rid).text
    assert card(t) == "nano4" and "nano4-old" not in t


# ---------------------------------------------------------------- common rules
def pages_of(up):
    """The upload pages this task draws, zh and en: the form, the success, the seven refusals."""
    out = []
    slurm_only(up)
    c = up.client()
    for q in ("", "?lang=en"):
        out.append(c.get("/upload" + q).text)
        out.append(c.get(saved_ok(up, "p.csv", query=q).headers["location"]).text)
        for files, _ in BAD_CASES.values():
            out.append(put(up, files, query=q).text)
    return out


def test_tc037_038_039_front_end_rules_and_words(up):
    # TC-037, TC-038, TC-039
    from abf_platform import web_board
    assert len(web_board.STYLE) == 10861
    css = set(re.findall(r"\.([a-z][a-z0-9-]*)", web_board.STYLE))
    for t in pages_of(up):
        assert "style=" not in t and "<script" not in t
        for u in re.findall(r'(?:href|src)="([^"]*)"', t):
            assert u.startswith("/"), u
        for cl in re.findall(r'class="([^"]*)"', pane(t, "middle")):
            for one in cl.split():
                assert one in css or one in ("lbl", "req"), one
        for m in re.findall(r'<p class="(bad|ok)">([^<]*)</p>', t):
            assert re.match(r"[✕✓] \S", m[1]), m
        if 'lang="zh' in t:
            m = plain(pane(t, "middle"))
            for word in BANNED:
                assert word not in m, word
            for inner in ("csrf", "sheet_saved", "Traceback", "Rejected"):
                assert inner not in m


# ---------------------------------------------------------------- constitution
def test_tc042_nothing_is_sent_by_uploading_or_looking(up):
    # TC-042
    slurm_only(up)

    def counts():
        return [len(sql_rows(up.state, "SELECT * FROM %s" % t)) for t in ("confirmations", "jobs", "launches")]
    before = counts()
    saved_ok(up)
    put(up, [("bad.txt", SHEET)])
    up.client().get("/?run_name=web-t9")
    assert counts() == before


def test_tc043_no_new_table_or_column(up):
    # TC-043
    con = sqlite3.connect(str(up.state))
    schema = "\n".join(sorted(r[0] or "" for r in con.execute("select sql from sqlite_master")))
    assert hashlib.sha256(schema.encode()).hexdigest()[:16] == "21226ea8d80fd18d"


def test_tc044_the_sheets_folder_comes_from_the_deployment():
    # TC-044
    from abf_platform import uploads_web
    src = open(uploads_web.__file__, encoding="utf-8").read()
    assert "/work/" not in src and "/home/" not in src
