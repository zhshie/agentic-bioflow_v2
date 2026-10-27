# Nothing existing: tests of how the confirmation page and the board show a clean_work request (cloud-cleanup-e); no earlier test builds one.
"""cloud-cleanup-e: the confirmation page knows `clean_work` (title, words, button, 7 days) and the board shows a notice for it.
Test cases are named in the comments (TC-001 ...), they come from specs/cloud-cleanup-e/test-case.md. Nothing in the product builds a
clean_work request yet, so every test makes one with `confirm.create_pending`. Pages of launch and cancel are compared with what the
code printed before this task (a hash of the page with every 32+ hex run, i.e. ids and CSRF tokens, masked)."""
import hashlib
import inspect
import re
import sqlite3
import time

import pytest

from human_harness import World, csrf_of, form_answer
from test_confirm_page import logged_in
from test_web_board import seed, pane, login as board_login

T0 = time.time()           # the agents of the test world were seen "now", so the clock must be now for a press to find them online
FIXED = 1_800_000_000.0   # the board hash tests need a clock that does not move
DAY = 86400.0
WORK = "/data/u1/run-one/work"


@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.clock.t = T0
    return world


def mask(text):
    text = re.sub(r"[0-9a-f]{32,}", "X", text)
    text = re.sub(r"[^\s<>\"']*(?:pytest-|/tmp/)[^\s<>\"']*", "P", text)
    return re.sub(r"\d{9,}", "N", text)


def snap(r):
    return (r.status_code, hashlib.sha256(mask(r.text).encode("utf-8")).hexdigest()[:16])


def tables(w):
    return (w.sql("SELECT * FROM confirmations"), w.sql("SELECT * FROM jobs WHERE kind IN ('launch_nextflow', 'cancel_run', 'clean_work')"))


def clean_request(w, caller, name="run-one"):
    from abf_platform import compute_envs, confirm
    folder = "/data/u1/" + name
    agent = compute_envs.get(w.ip.state_db, "lab-a")["agent"]
    bundle = {"version": 1, "run_name": name, "slurm_job_id": 4242, "run_folder": folder, "agent": agent, "ce": "lab-a", "work": folder + "/work"}
    return confirm.create_pending(w.ip.state_db, "clean_work", "lab-a", bundle, "delete %s" % (folder + "/work"), caller.user_id, clock=w.clock)


def run_and_request(w, owner, name="run-one", status="succeeded", request=True, at=None):
    """A run of `owner` in the index with its hand-off record (a Slurm number), and a pending clean_work request on it. Returns the request id."""
    from abf_platform import compute_envs, store
    at = at or T0
    seed(w, name, status, launch_row=False, started=at - 7200, ended=at - 3600)
    agent = compute_envs.get(w.ip.state_db, "lab-a")["agent"]
    con = store.connect_state(w.ip.state_db)
    with con:
        con.execute("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, user_id) VALUES (?,?,?,?,?,?,?,?)",
                    (name, 4242, "/data/u1/" + name, "lab-a", agent, 1, 2, owner.user_id))
    con.close()
    return clean_request(w, owner, name) if request else None


def expire(w, rid):
    """The seven days are over for this request (its time of ending is moved into the past; a clock jump would end the login too)."""
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET expires_at = ? WHERE id = ?", (T0 - 1, rid))
    con.close()


def two(w):
    return w.user("ann"), w.user("bob")


# ---- US1: the confirmation page --------------------------------------------------------------------------------------------

def test_a_pending_clean_request_page_says_clean_not_cancel_and_has_the_confirm_delete_button(w):
    # TC-001, TC-002, TC-003, TC-006, TC-007, TC-008
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    page = c.get("/c/" + rid)
    t = page.text
    assert page.status_code == 200
    assert "<h1>清理確認</h1>" in t and "取消確認" not in t and "送出確認" not in t
    assert "下面就是會被刪除的全部內容。確定了再按「確認刪除」；按了才會排進佇列。" in t
    assert "會被送出" not in t and "會被取消" not in t
    assert '<button type="submit">確認刪除</button>' in t and '<button type="submit">送出</button>' not in t
    en = c.get("/c/%s?lang=en" % rid).text
    assert '<button type="submit">Confirm delete</button>' in en and "取消確認" not in en
    assert "<dt>Request</dt><dd>Clean up intermediate files</dd>" in en and "<dt>Run name</dt><dd>run-one</dd>" in en
    assert "<dt>Folder to delete</dt><dd>%s</dd>" % WORK in en


def test_the_plain_block_shows_kind_run_name_and_the_folder_to_delete_and_nothing_else(w):
    # TC-004, TC-005
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    t = logged_in(w, "ann").get("/c/" + rid).text
    block = re.search(r'<dl class="fields plain">(.*?)</dl>', t, re.S).group(1)
    assert re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", block) == [("種類", "清理中間檔"), ("run 名稱", "run-one"), ("要刪除的資料夾", WORK)]
    for word in ("管線", "版本", "環境", "樣本數", "新資料夾", "—"):
        assert word not in block
    assert "<dd>-</dd>" not in block


def test_the_expired_and_void_pages_for_clean_work_say_seven_days_and_do_not_say_send_it_again_from_the_ai(w):
    # TC-009, TC-010, TC-065
    from abf_platform import confirm
    ann = w.user("ann")
    rid_void = run_and_request(w, ann, "run-a")
    c = logged_in(w, "ann")
    assert confirm.void(w.ip.state_db, rid_void, "X-reason")
    page = c.get("/c/" + rid_void)
    assert "清理確認" in page.text and "這個申請已作廢：X-reason。" in page.text
    assert "回到 AI" not in page.text and "重新送出" not in page.text
    rid = run_and_request(w, ann, "run-b")
    expire(w, rid)
    for lang in ("zh", "en"):
        t = c.get("/c/%s?lang=%s" % (rid, lang)).text
        assert "清理確認" in t and "這個申請已逾時（7 天），不會自動重新提出。" in t
        assert "10 分鐘" not in t and "回到 AI" not in t
        assert "<form" not in t and "<button" not in t and "<a " not in t.split("</h1>")[1]


def test_the_confirmed_clean_page_says_the_job_number_under_the_clean_title(w):
    # TC-011
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    assert c.post("/c/" + rid, data={"csrf": csrf_of(c.get("/c/" + rid).text)}).status_code == 200
    job = w.sql("SELECT id FROM jobs WHERE kind = 'clean_work'")[0]["id"]
    t = c.get("/c/" + rid).text
    assert "<h1>清理確認</h1>" in t and "已送出。工作編號 %s。" % job in t and "取消確認" not in t


def test_get_changes_nothing_for_a_clean_request(w):
    # TC-012
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    before = tables(w)
    for lang in ("zh", "en"):
        assert c.get("/c/%s?lang=%s" % (rid, lang)).status_code == 200
    assert tables(w) == before and w.confirmations()[0]["state"] == "pending"


# What the pages of launch and cancel printed before this task (hash of the page with ids and tokens masked).
# guided-launch-2 added rules to the one stylesheet (the parameter group table), so every page's hash and BASE_STYLE were pinned again; only the stylesheet differs.
# guided-launch-2b added rules to the same stylesheet (column widths of that table, the advanced box) and took one out (the radio rows), so they were pinned once more; again only the stylesheet differs.
# guided-launch-2c changed four rules (the red star, the step area width, the form width, the field width) and the column widths of the table, so they were pinned a third time; again only the stylesheet differs.
BASE_CONFIRM = {'pending-launch-zh': (200, '1c8fb37271d4b66d'), 'pending-cancel-zh': (200, 'db98fa958f28c58c'),
                'pending-launch-en': (200, '051abaed939e9a02'), 'pending-cancel-en': (200, 'b7bd15bd3a2264d4'),
                'void-zh': (409, '0dc673021f94d8cf'), 'void-en': (409, '0dc673021f94d8cf'),
                'confirmed-launch-zh': (200, 'af9aeb4117b4dedd'), 'confirmed-launch-en': (200, 'ec19ab39eb056e53'),
                'confirmed-cancel-zh': (200, 'c569a7e51635a715'), 'confirmed-cancel-en': (200, '884f185afd503779')}
BASE_EXPIRED = {'expired-launch-zh': (200, 'a59d5aa6d80855ab'), 'expired-cancel-zh': (200, 'ed781224c07f93b7'),
                'expired-launch-en': (200, 'a59d5aa6d80855ab'), 'expired-cancel-en': (200, 'ed781224c07f93b7')}
BASE_POST = {'pressed-launch': (200, '341bf85f24b92d54'), 'pressed-cancel': (200, '825960aaac8f88cc'),
             'late-launch': (410, '11508e27239c4c6b'), 'late-cancel': (410, '11508e27239c4c6b')}
BASE_BOARD = {'succeeded-zh': (200, '30553968fd644805'), 'succeeded-en': (200, 'aef016cefae870bc'),
              'failed-zh': (200, '52d83937ab023505'), 'failed-en': (200, '407b7e3befce5d82'),
              'running-zh': (200, 'aa4d4744533fc152'), 'running-en': (200, 'dd85badea6c866c5')}
BASE_STYLE = '9256cf1707f8f79a'


def launch_and_cancel(w, ann):
    """A pending launch and a pending cancel of ann."""
    from helpers import tool_json
    launch = w.launch(caller=ann)["id"]
    w.hand_over(by=ann, run="run-two")
    cancel = tool_json(w.call("cancel", {"run_name": "run-two"}, caller=ann))["id"]
    return launch, cancel


def test_launch_and_cancel_pages_are_byte_for_byte_what_they_were(w):
    # TC-013, TC-015, TC-016
    w.clock.t = time.time()
    ann = w.user("ann")
    launch, cancel = launch_and_cancel(w, ann)
    c = logged_in(w, "ann")
    got = {}
    for lang in ("zh", "en"):
        for kind, rid in (("launch", launch), ("cancel", cancel)):
            got["pending-%s-%s" % (kind, lang)] = snap(c.get("/c/%s?lang=%s" % (rid, lang)))
    w.launch(caller=ann, answer=form_answer("decline"), run="run-three")
    void_id = [x["id"] for x in w.confirmations() if x["state"] == "void"][0]
    for lang in ("zh", "en"):
        got["void-%s" % lang] = snap(c.get("/c/%s?lang=%s" % (void_id, lang)))
    for kind, rid in (("launch", launch), ("cancel", cancel)):
        token = csrf_of(c.get("/c/" + rid).text)
        assert c.post("/c/" + rid, data={"csrf": token}).status_code == 200
        for lang in ("zh", "en"):
            got["confirmed-%s-%s" % (kind, lang)] = snap(c.get("/c/%s?lang=%s" % (rid, lang)))
    assert got == BASE_CONFIRM, repr(got)


def test_launch_and_cancel_expired_pages_are_byte_for_byte_what_they_were(w):
    # TC-014
    w.clock.t = time.time()
    ann = w.user("ann")
    launch, cancel = launch_and_cancel(w, ann)
    c = logged_in(w, "ann")
    w.clock.t += 700
    got = {}
    for lang in ("zh", "en"):
        for kind, rid in (("launch", launch), ("cancel", cancel)):
            got["expired-%s-%s" % (kind, lang)] = snap(c.get("/c/%s?lang=%s" % (rid, lang)))
    assert got == BASE_EXPIRED, repr(got)


def test_only_the_person_who_has_the_request_can_see_and_press_it(w):
    # TC-017, TC-018, TC-026, TC-027
    ann, bob = two(w)
    rid = run_and_request(w, ann)
    own_token = csrf_of(logged_in(w, "ann").get("/c/" + rid).text)
    before = tables(w)
    b = logged_in(w, "bob")
    page = b.get("/c/" + rid)
    assert page.status_code == 403 and WORK not in page.text and "run-one" not in page.text and "<button" not in page.text
    for token in (own_token, "x"):
        assert b.post("/c/" + rid, data={"csrf": token}).status_code == 403
    anon = w.web()
    r = anon.get("/c/" + rid)
    assert "密碼" in r.text and WORK not in r.text and "<h1>清理確認</h1>" not in r.text
    assert anon.post("/c/" + rid, data={"csrf": "x"}).status_code == 401
    assert tables(w) == before and w.confirmations()[0]["state"] == "pending"


def test_pressing_with_a_wrong_or_missing_csrf_queues_nothing(w):
    # TC-024, TC-025, TC-028
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    good = csrf_of(c.get("/c/" + rid).text)
    before = tables(w)
    for data in ({}, {"csrf": ""}, {"csrf": "wrong"}, {"csrf": good + "0"}):
        r = c.post("/c/" + rid, data=data)
        assert r.status_code == 403 and "表單已失效" in r.text
    r = c.post("/c/" + rid, data={"csrf": good}, headers={"origin": "https://elsewhere.example"})
    assert r.status_code >= 400
    assert tables(w) == before and w.confirmations()[0]["state"] == "pending"


def test_pressing_once_queues_exactly_one_clean_work_job_and_twice_says_already(w):
    # TC-019, TC-020, TC-022, TC-023
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    r = c.post("/c/" + rid, data={"csrf": token})
    jobs = w.sql("SELECT * FROM jobs WHERE kind = 'clean_work'")
    assert r.status_code == 200 and len(jobs) == 1 and jobs[0]["confirmation_id"] == rid
    assert "已送出。工作編號 %s。代理會開始清理這個 run 的中間檔；結果不會被動。" % jobs[0]["id"] in r.text
    assert w.confirmations()[0]["state"] == "confirmed"
    again = c.post("/c/" + rid, data={"csrf": token})
    assert len(w.sql("SELECT * FROM jobs WHERE kind = 'clean_work'")) == 1
    assert "已送出。工作編號 %s。" % jobs[0]["id"] in again.text and "回到 AI" not in again.text


def test_the_pages_after_pressing_never_tell_a_clean_request_to_go_back_to_the_ai(w):
    # TC-021, TC-030, TC-031, TC-032, TC-033, TC-075
    from abf_platform import confirm
    ann, bob = two(w)
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    ok = c.post("/c/" + rid, data={"csrf": token})
    assert "回到 AI" not in ok.text and "再呼叫" not in ok.text
    rid2 = run_and_request(w, ann, "run-b")
    token2 = csrf_of(c.get("/c/" + rid2).text)
    expire(w, rid2)
    gone = c.post("/c/" + rid2, data={"csrf": token2})
    assert gone.status_code == 410 and "未送出：" in gone.text and "回到 AI" not in gone.text and "重新送出" not in gone.text
    rid3 = run_and_request(w, ann, "run-c")
    token3 = csrf_of(c.get("/c/" + rid3).text)
    assert confirm.void(w.ip.state_db, rid3, "R-void")
    bad = c.post("/c/" + rid3, data={"csrf": token3})
    assert bad.status_code == 409 and "未送出：" in bad.text and "R-void" in bad.text
    assert "回到 AI" not in bad.text and "重新送出" not in bad.text
    missing = c.post("/c/" + "0" * 32, data={"csrf": "x"})
    assert missing.status_code == 404 and "回到 AI" not in missing.text
    rid4 = run_and_request(w, bob, "run-d")
    other = c.post("/c/" + rid4, data={"csrf": "x"})
    assert other.status_code == 403 and "回到 AI" not in other.text
    for r in (ok, gone, bad, missing, other):
        for leak in ("Traceback", "SELECT ", "sqlite", "/mnt/", token, token2, token3):
            assert leak not in r.text


def test_the_pages_after_pressing_a_launch_or_a_cancel_are_unchanged(w):
    # TC-034, TC-035, TC-036, TC-037
    from helpers import tool_json
    w.clock.t = time.time()
    ann = w.user("ann")
    launch, cancel = launch_and_cancel(w, ann)
    launch2 = w.launch(caller=ann, run="run-x")["id"]
    w.hand_over(by=ann, run="run-y")
    cancel2 = tool_json(w.call("cancel", {"run_name": "run-y"}, caller=ann))["id"]
    c = logged_in(w, "ann")
    tokens = {rid: csrf_of(c.get("/c/" + rid).text) for rid in (launch, cancel, launch2, cancel2)}
    got = {}
    for name, rid in (("launch", launch), ("cancel", cancel)):
        got["pressed-" + name] = snap(c.post("/c/" + rid, data={"csrf": tokens[rid]}))
    w.clock.t += 700
    for name, rid in (("launch", launch2), ("cancel", cancel2)):
        got["late-" + name] = snap(c.post("/c/" + rid, data={"csrf": tokens[rid]}))
    assert got == BASE_POST, repr(got)


def test_pressing_after_seven_days_queues_nothing(w):
    # TC-029
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    expire(w, rid)
    r = c.post("/c/" + rid, data={"csrf": token})
    assert r.status_code == 410 and w.sql("SELECT * FROM jobs WHERE kind = 'clean_work'") == []


# ---- US3: the board ----------------------------------------------------------------------------------------------------------

def notices(text):
    return re.findall(r'<article class="notice state-succeeded">.*?</article>', pane(text, "right"), re.S)


def board(w, name, lang="zh", run="run-one"):
    c = board_login(w, name)
    return c.get("/?run=id-%s&lang=%s" % (run, lang))


def test_a_succeeded_run_with_my_open_clean_request_shows_one_notice_with_a_link_to_the_confirmation_page(w):
    # TC-038, TC-039, TC-040, TC-041, TC-042, TC-043
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    zh = board(w, "ann")
    n = notices(zh.text)
    assert zh.status_code == 200 and len(n) == 1
    assert "待處理" in n[0] and '<span class="sq"></span>' in n[0] and 'class="level state-succeeded"' in n[0]
    assert "這個 run 已成功；它的中間檔（work）可以清掉，結果不會被動。" in n[0]
    assert "打開確認頁，看清楚要刪的資料夾再決定。" in n[0] and 'class="when"' not in n[0]
    assert re.findall(r'href="([^"]*)"', n[0]) == ["/c/" + rid] and "csrf" not in n[0]
    en = notices(board(w, "ann", "en").text)
    assert len(en) == 1 and re.findall(r'href="([^"]*)"', en[0]) == ["/c/%s?lang=en" % rid]


def test_the_notice_is_a_link_not_a_form_and_has_no_button(w):
    # TC-044, TC-045
    ann = w.user("ann")
    run_and_request(w, ann)
    before = tables(w)
    for lang in ("zh", "en"):
        n = notices(board(w, "ann", lang).text)[0]
        assert not re.search(r"<form|<button|<input", n) and n.count("<a ") == 1
    assert tables(w) == before and w.confirmations()[0]["state"] == "pending"


@pytest.mark.parametrize("status", ["failed", "running", "lost"])
def test_no_notice_for_a_failed_a_running_or_a_lost_run_even_with_an_open_request(w, status):
    # TC-046, TC-047, TC-048
    ann = w.user("ann")
    run_and_request(w, ann, status=status)
    r = board(w, "ann")
    assert r.status_code == 200 and notices(r.text) == [] and "待處理" not in pane(r.text, "right")


def test_no_notice_for_another_users_request_or_run(w):
    # TC-049, TC-050, TC-051
    ann, bob = two(w)
    run_and_request(w, ann, "run-one", request=False)
    clean_request(w, bob, "run-one")
    r = board(w, "ann")
    assert r.status_code == 200 and notices(r.text) == []
    run_and_request(w, bob, "run-bob")
    other = board(w, "ann", run="run-bob")
    assert other.status_code == 404 and "run-bob" not in other.text and "/c/" not in other.text and "待處理" not in other.text
    run_and_request(w, ann, "run-r1", request=False)
    rid2 = run_and_request(w, ann, "run-r2")
    assert notices(board(w, "ann", run="run-r1").text) == []
    assert re.findall(r"/c/([0-9a-f]+)", notices(board(w, "ann", run="run-r2").text)[0]) == [rid2]


def test_no_notice_after_the_request_is_pressed_expired_void_or_forgotten(w):
    # TC-052, TC-053, TC-054, TC-055
    from abf_platform import confirm
    ann = w.user("ann")
    rid = run_and_request(w, ann, "run-p")
    c = logged_in(w, "ann")
    assert c.post("/c/" + rid, data={"csrf": csrf_of(c.get("/c/" + rid).text)}).status_code == 200
    assert notices(board(w, "ann", run="run-p").text) == []
    rid_v = run_and_request(w, ann, "run-v")
    assert len(notices(board(w, "ann", run="run-v").text)) == 1
    assert confirm.void(w.ip.state_db, rid_v, "gone")
    assert notices(board(w, "ann", run="run-v").text) == []
    rid_f = run_and_request(w, ann, "run-f")
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET bundle_json = NULL, screen_text = NULL, forgotten_at = ? WHERE id = ?", (T0, rid_f))
    con.close()
    assert notices(board(w, "ann", run="run-f").text) == []
    rid_e = run_and_request(w, ann, "run-e")
    expire(w, rid_e)
    assert notices(board(w, "ann", run="run-e").text) == []


@pytest.mark.parametrize("status", ["succeeded", "failed", "running"])
def test_a_board_without_any_clean_request_is_byte_for_byte_what_it_was(w, status):
    # TC-056, TC-057, TC-058
    w.clock.t = FIXED
    ann = w.user("ann")
    run_and_request(w, ann, status=status, request=False, at=FIXED)
    if status == "running":
        con = sqlite3.connect(str(w.ip.index))
        with con:
            con.execute("UPDATE runs SET last_message_at = ?", (FIXED - 10,))
        con.close()
    got = {"%s-%s" % (status, lang): snap(board(w, "ann", lang)) for lang in ("zh", "en")}
    assert got == {k: v for k, v in BASE_BOARD.items() if k.startswith(status)}, repr(got)


# ---- US4: the read, the tools, the routes ----------------------------------------------------------------------------------------

def test_clean_requests_is_a_read_that_filters_by_caller_and_is_not_a_tool_or_a_route(w):
    # TC-059, TC-060, TC-061, TC-062, TC-063, TC-071
    from abf_platform import actions
    ann, bob = two(w)
    r1 = run_and_request(w, ann, "run-one")
    r2 = run_and_request(w, ann, "run-two")
    before = tables(w) + (w.sql("SELECT * FROM launches"),)
    assert actions.clean_requests(w.ip.state_db, caller=ann, clock=w.clock) == {"run-one": r1, "run-two": r2}
    assert actions.clean_requests(w.ip.state_db, caller=bob, clock=w.clock) == {}
    assert actions.clean_requests(w.ip.state_db, caller=None, clock=w.clock) == {}
    assert tables(w) + (w.sql("SELECT * FROM launches"),) == before
    tools, _ = w.mcp([])
    assert not [t.name for t in tools if "clean" in t.name] and not hasattr(actions, "request_clean_requests")
    routes = sorted((r.path, tuple(sorted(r.methods or ()))) for r in w.web().app.routes)
    assert not [p for p, _ in routes if "clean" in p]


def test_no_clean_request_is_made_by_looking_around(w):
    # TC-064
    ann = w.user("ann")
    run_and_request(w, ann, request=False)
    c = board_login(w, "ann")
    for path in ("/", "/?run=id-run-one", "/?run=id-run-one&lang=en", "/c/" + "0" * 32):
        c.get(path)
    assert w.sql("SELECT * FROM confirmations WHERE kind = 'clean_work'") == [] and w.sql("SELECT * FROM jobs WHERE kind = 'clean_work'") == []


def test_the_texts_have_no_fee_or_thirty_day_reminder_and_the_style_sheet_is_unchanged(w):
    # TC-066, TC-067
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    words = re.sub(r"<style>.*?</style>", "", c.get("/c/" + rid).text, flags=re.S) + notices(board(w, "ann").text)[0]
    for word in ("費用", "月費", "30 天", "cost", "Cost", "fee"):
        assert word not in words
    css = re.search(r"<style>(.*?)</style>", board(w, "ann").text, re.S).group(1)
    assert hashlib.sha256(css.encode("utf-8")).hexdigest()[:16] == BASE_STYLE


def test_no_inline_style_no_external_resource_and_the_same_headers_as_a_launch_page(w):
    # TC-072, TC-073
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    launch = w.launch(caller=ann, run="run-hdr")["id"]
    c = logged_in(w, "ann")
    ref = c.get("/c/" + launch).headers
    pages = [c.get("/c/" + rid), c.get("/c/%s?lang=en" % rid), board(w, "ann")]
    c.post("/c/" + rid, data={"csrf": csrf_of(pages[0].text)})
    pages += [c.get("/c/" + rid)]
    rid_old = run_and_request(w, ann, "run-old")
    expire(w, rid_old)
    pages += [c.get("/c/" + rid_old)]
    for r in pages:
        assert " style=" not in r.text
        for url in re.findall(r'(?:src|href)="([^"]*)"', r.text):
            assert url.startswith("/") or url.startswith("#"), url
        for h in ("content-security-policy", "x-frame-options", "cache-control", "referrer-policy", "x-content-type-options"):
            assert r.headers[h] == ref[h]


def test_the_web_sources_have_no_program_start():
    # TC-068
    from abf_platform import actions, web, web_board
    for mod in (web, web_board, actions):
        src = inspect.getsource(mod)
        for b in ("subprocess", "os.system", "Popen", "os.exec", "os.spawn"):
            assert b not in src
