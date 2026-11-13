# Nothing existing: tests of the web-bugs-a batch (confirm page in English, tasks tab note, run menu, placeholder stages, left-column groups); ours.
"""web-bugs-a: #335 #336 #337 #339 #340 (TC ids in the comments)."""
import re
import sqlite3
import time

import pytest

from human_harness import World, csrf_of
from test_confirm_page import logged_in
from test_clean_page import run_and_request, expire, launch_and_cancel, T0
from test_web_board import seed, pane, login, cjk, no_cjk


@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.clock.t = T0
    return world


def body_of_page(text):
    """The page text without <pre> technical summaries (R7)."""
    return re.sub(r"<pre\b.*?</pre>", "", text, flags=re.S)


def set_project(w, rid, project):
    con = sqlite3.connect(str(w.ip.index))
    with con:
        con.execute("UPDATE runs SET project_name = ? WHERE id = ?", (project, rid))
    con.close()


def set_failed_tasks(w, rid, n):
    con = sqlite3.connect(str(w.ip.index))
    with con:
        for i in range(n):
            con.execute("INSERT INTO failed_tasks (run_id, task_key, name, exit_code, error_message, workdir) VALUES (?,?,?,?,?,?)",
                        (rid, "k%d" % i, "TASK_%d" % i, 1, "boom", "/w/%d" % i))
    con.close()


# ---- #335 ------------------------------------------------------------------------------------------------------------------

def test_confirm_en_title_intro_button(w):
    # TC-001 TC-002 TC-003 TC-004 TC-014 TC-100
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    en = c.get("/c/%s?lang=en" % rid).text
    assert "<h1>Confirm clean-up</h1>" in en and "清理確認" not in en and "以下為將被刪除" not in en
    assert ('Everything that will be deleted is shown below. If it is correct, press "Confirm delete"; '
            'nothing is queued until you press it.') in en.replace("&quot;", '"')
    assert '<button type="submit">Confirm delete</button>' in en
    assert cjk(body_of_page(en)) == []
    zh = c.get("/c/" + rid).text
    assert "<h1>清理確認</h1>" in zh and "以下為將被刪除的全部內容。確認無誤後，請按「確認刪除」；按下後才會排入佇列。" in zh
    form = lambda t: re.findall(r'<form[^>]*>.*?<input[^>]*>', t, re.S)
    assert form(zh) == form(en)           # TC-100: same action and hidden field


def test_confirm_en_launch_and_cancel_pages(w):
    # TC-005 TC-006 TC-007
    w.clock.t = time.time()
    ann = w.user("ann")
    launch, cancel = launch_and_cancel(w, ann)
    c = logged_in(w, "ann")
    for rid, title in ((launch, "Confirm launch"), (cancel, "Confirm cancel")):
        t = c.get("/c/%s?lang=en" % rid).text
        assert "<h1>%s</h1>" % title in t
        assert 'Everything that will be sent is shown below. If it is correct, press "Send"' in t.replace("&quot;", '"')
        assert '<button type="submit">Send</button>' in t
        assert cjk(body_of_page(t)) == []


def test_confirm_en_confirmed_expired_void(w):
    # TC-008 .. TC-013
    from abf_platform import confirm
    w.clock.t = time.time()
    ann = w.user("ann")
    launch, cancel = launch_and_cancel(w, ann)
    c = logged_in(w, "ann")
    token = csrf_of(c.get("/c/" + launch).text)
    assert c.post("/c/" + launch, data={"csrf": token}).status_code == 200
    t = c.get("/c/%s?lang=en" % launch).text
    assert "Sent. Job number" in t and cjk(body_of_page(t)) == []
    assert "已送出。工作編號" in c.get("/c/" + launch).text
    w.clock.t += 700
    t = c.get("/c/%s?lang=en" % cancel).text
    assert "This request has expired (10 minutes). Please send it again." in t and no_cjk(t)
    # clean: 7 days, void
    w2 = w
    rid = run_and_request(w2, ann, "run-b", at=w.clock.t)
    expire(w2, rid)
    t = c.get("/c/%s?lang=en" % rid).text
    assert "This request has expired (7 days) and will not be raised again." in t and no_cjk(t)
    rid = run_and_request(w2, ann, "run-c", at=w.clock.t)
    assert confirm.void(w.ip.state_db, rid, "X-reason")
    t = c.get("/c/%s?lang=en" % rid).text
    assert "This request was voided: X-reason." in t and "Please send it again." not in t and no_cjk(t)
    # non clean void
    w.launch(caller=ann, answer=__import__("human_harness").form_answer("decline"), run="run-three")
    void_id = [x["id"] for x in w.confirmations() if x["state"] == "void"][0]
    t = c.get("/c/%s?lang=en" % void_id).text
    assert re.search(r"This request was voided: .*\. Please send it again\.", t)


def test_confirm_zh_unchanged(w):
    # TC-014
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    t = logged_in(w, "ann").get("/c/" + rid).text
    assert "<h1>清理確認</h1>" in t and "按下後才會排入佇列。" in t


def test_confirm_404_en(w):
    # TC-017 TC-018 TC-019 TC-020 TC-021 TC-022 TC-023 TC-101
    ann, bob = w.user("ann"), w.user("bob")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    r = c.get("/c/doesnotexist?lang=en")
    assert r.status_code == 404 and "<h1>Not found</h1>" in r.text and "No such address." in r.text and cjk(r.text) == []
    r = c.get("/c/doesnotexist")
    assert r.status_code == 404 and "找不到 (not found)" in r.text and "無此網址。" in r.text
    ghost = "0" * len(rid) if re.fullmatch(r"[0-9a-f]+", rid) else rid[:-1] + ("a" if rid[-1] != "a" else "b")
    r = c.get("/c/%s?lang=en" % ghost)
    assert r.status_code == 404 and "<h1>Not found</h1>" in r.text and "No such request." in r.text and cjk(r.text) == []
    assert "無此申請" in c.get("/c/" + ghost).text
    cb = logged_in(w, "bob")
    r = cb.get("/c/%s?lang=en" % rid)
    assert r.status_code == 403 and "<h1>Not yours</h1>" in r.text and cjk(r.text) == []
    assert "That request was not sent by you, so it cannot be viewed or acted on here." in r.text
    assert "非您的申請" in cb.get("/c/" + rid).text
    # TC-101: someone else cannot press
    token = csrf_of(c.get("/c/" + rid).text)
    r = cb.post("/c/%s?lang=en" % rid, data={"csrf": token})
    assert r.status_code == 403 and cjk(r.text) == []
    assert [x["state"] for x in w.confirmations() if x["id"] == rid] == ["pending"]
    # TC-023 post to a bad address
    r = c.post("/c/doesnotexist?lang=en", data={"csrf": token})
    assert r.status_code == 404 and cjk(r.text) == []
    assert "找不到 (not found)" in c.post("/c/doesnotexist", data={"csrf": token}).text
    # TC-022 act route with an unknown verb
    r = c.post("/act/bogus", data={"csrf": token, "run": "x", "lang": "en"})
    assert r.status_code == 404 and cjk(r.text) == []


def test_confirm_no_language_link_and_post_stays_zh(w):
    # TC-025 TC-026
    ann = w.user("ann")
    rid = run_and_request(w, ann)
    c = logged_in(w, "ann")
    en = c.get("/c/%s?lang=en" % rid).text
    assert "<a " not in en.split("</h1>")[1]
    token = csrf_of(en)
    r = c.post("/c/%s?lang=en" % rid, data={"csrf": token})
    assert r.status_code == 200 and "已送出" in r.text


# ---- #336 ------------------------------------------------------------------------------------------------------------------

def run_tab(w, name, lang, tab="tasks"):
    return login(w, "ann").get("/?run=id-%s&stage=running&tab=%s%s" % (name, tab, "&lang=en" if lang == "en" else "")).text


def test_tasks_tab_unlisted_failures_zh_en(w):
    # TC-030 TC-031 TC-032 TC-038 TC-039
    ann = w.user("ann")
    seed(w, "web-test-2", "succeeded", ann, counts={"succeeded": 71, "failed": 4})
    zh = run_tab(w, "web-test-2", "zh")
    assert '<p class="muted">失敗計數 4，但沒有可列出的失敗任務明細；這些失敗可能已被忽略或重試成功。</p>' in zh
    assert "無失敗任務" not in zh and "71 / 75" in zh
    en = run_tab(w, "web-test-2", "en")
    assert ('<p class="muted">The failed count is 4, but no failed task has a recorded detail; '
            'these may have been ignored or retried successfully.</p>') in en
    assert "No failed tasks" not in en and no_cjk(en)


def test_tasks_tab_partial_rows_note(w):
    # TC-033 TC-034
    ann = w.user("ann")
    rid = seed(w, "p4", "succeeded", ann, counts={"succeeded": 71, "failed": 4})
    set_failed_tasks(w, rid, 2)
    zh = run_tab(w, "p4", "zh")
    assert "TASK_0" in zh and "TASK_1" in zh and "無失敗任務" not in zh
    assert re.search(r'<p class="muted">[^<]*列出 2[^<]*計數 4', zh)
    en = run_tab(w, "p4", "en")
    assert re.search(r'<p class="muted">[^<]*2[^<]*4', en) and no_cjk(en)
    rid = seed(w, "p2", "succeeded", ann, counts={"succeeded": 71, "failed": 2})
    set_failed_tasks(w, rid, 2)
    zh = run_tab(w, "p2", "zh")
    assert "TASK_1" in zh and "列出" not in zh and "無失敗任務" not in zh


def test_tasks_tab_zero_failed_unchanged(w):
    # TC-035 TC-036 TC-037
    ann = w.user("ann")
    seed(w, "z0", "succeeded", ann, counts={"succeeded": 5})
    assert "無失敗任務" in run_tab(w, "z0", "zh")
    assert "No failed tasks" in run_tab(w, "z0", "en")
    from abf_platform import web_board
    out = web_board.tab_body(web_board.STRINGS["zh"], "zh", {"status": "succeeded"}, "tasks")
    assert "無失敗任務" in out


# ---- #337 ------------------------------------------------------------------------------------------------------------------

def menu_of(text):
    return re.search(r'<details class="menu">.*?</details>', pane(text, "middle"), re.S).group(0)


def test_menu_succeeded_has_no_action_forms(w):
    # TC-040 .. TC-045 TC-102
    ann = w.user("ann")
    seed(w, "ok1", "succeeded", ann, counts={"succeeded": 3})
    c = login(w, "ann")
    zh = c.get("/?run=id-ok1&stage=running").text
    m = menu_of(zh)
    assert "/act/" not in m and "<form" not in m
    for word in ("續跑", "重跑", "取消"):
        assert word not in m
    assert "沿用設定重新分析" in m and "/launch?from=" in m
    assert 'action="/act/cancel"' not in zh
    en = c.get("/?run=id-ok1&stage=running&lang=en").text
    m = menu_of(en)
    assert "/act/" not in m
    for word in ("Resume", "Re-run", "Cancel"):
        assert word not in m
    assert "/launch?from=" in m


@pytest.mark.parametrize("status", ["failed", "lost", "running"])
def test_menu_failed_lost_running_unchanged(w, status):
    # TC-046 TC-047 TC-048
    ann = w.user("ann")
    seed(w, "m1", status, ann)
    m = menu_of(login(w, "ann").get("/?run=id-m1&stage=running").text)
    assert m.count("<form") == 3 and "續跑" in m and "重跑" in m and "取消" in m


# ---- #339 ------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("stage", ["launch"])      # studios-new-tab: a succeeded run now has a downstream page; the placeholder stays for the others (test_web_downstream.py)
def test_stage_placeholder_launch_downstream(w, stage):
    # TC-050 .. TC-055 TC-058
    ann = w.user("ann")
    seed(w, "s1", "succeeded", ann)
    c = login(w, "ann")
    zh = pane(c.get("/?run=id-s1&stage=%s" % stage).text, "middle")
    assert "012b" not in zh and "016" not in zh
    assert '<span class="later">之後開放</span>' in zh
    en = pane(c.get("/?run=id-s1&stage=%s&lang=en" % stage).text, "middle")
    assert '<span class="later">Coming later</span>' in en and no_cjk(en)
    assert "012b" not in en and "016" not in en


# ---- #340 ------------------------------------------------------------------------------------------------------------------

def test_left_group_script_name_is_no_project(w):
    # TC-060 .. TC-067 TC-069
    ann = w.user("ann")
    for name, project in (("web-test-1", "main.nf"), ("web-test-2", "main.nf"), ("a1", "nf-core/ampliseq"), ("a2", "nf-core/rnaseq"),
                          ("a3", "some/main.nf")):
        set_project(w, seed(w, name, "succeeded", ann), project)
    c = login(w, "ann")
    for lang, none in (("zh", "未分專案"), ("en", "No project")):
        t = c.get("/?lang=en" if lang == "en" else "/").text
        heads = re.findall(r"<h3>(.*?)</h3>", pane(t, "left"))
        assert "main.nf" not in heads
        assert none in heads and heads.count(none) == 1
        assert "nf-core/ampliseq" in heads and "nf-core/rnaseq" in heads and "some/main.nf" in heads
        assert heads[-1] == none


def test_left_group_only_script_names_is_one_group(w):
    # TC-066
    ann = w.user("ann")
    set_project(w, seed(w, "x1", "succeeded", ann), "main.nf")
    t = login(w, "ann").get("/").text
    assert re.findall(r"<h3>(.*?)</h3>", pane(t, "left")) == ["未分專案"]


# ---- shared limits -----------------------------------------------------------------------------------------------------------

def test_page_constraints_after_changes(w):
    # TC-080 .. TC-086 TC-089
    from abf_platform import web_board
    assert set(web_board.STRINGS["zh"]) == set(web_board.STRINGS["en"])
    for k in ("failed_unlisted", "failed_partial"):
        assert k in web_board.STRINGS["zh"]
    ann = w.user("ann")
    seed(w, "q1", "succeeded", ann, counts={"failed": 4})
    c = login(w, "ann")
    for url in ("/?run=id-q1&stage=running&tab=tasks", "/?run=id-q1&stage=launch", "/?run=id-q1&stage=running&tab=tasks&lang=en"):
        r = c.get(url)
        from helpers import live_rules
        assert live_rules(r.text, r.headers["content-security-policy"]) and "style=" not in r.text and r.text.count("<style>") == 1
        assert "default-src" in r.headers["content-security-policy"]
