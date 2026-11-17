# Nothing existing: a confirmed launch that Nextflow has not reported on yet must be visible to list_runs, get_run and the web sidebar.
"""A launch the person confirmed is invisible until Nextflow's first message reaches the index (observed live: list_runs empty, get_run
"Run not found" for 30+ seconds, far longer when the Slurm queue is busy). It is derived at read time from the launches row, its own
job row and the absence of the run in the index; no column, no stored status."""
import re
import sqlite3
import time

import pytest

from helpers import tool_json
from human_harness import World, form_answer
from test_confirm_page import logged_in
from test_web_board import pane, plain, seed


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def listed(w, caller, name=None):
    rows = tool_json(w.call("list_runs", {}, caller=caller))["runs"]
    return rows if name is None else [r for r in rows if r["name"] == name]


def got(w, caller, ident):
    return tool_json(w.call("get_run", {"run_id": ident}, caller=caller))


def sql_exec(w, text, args=()):
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute(text, args)
    con.close()


def test_confirmed_launch_is_listed_and_found_while_nextflow_is_silent(w):
    ann = w.user("ann")
    out = w.launch(caller=ann, answer=form_answer(), run="tp_wait")
    assert out["sent"] is True and out["state"] == "queued"
    rows = listed(w, ann, "tp_wait")
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "waiting"
    assert row["job_id"] == out["job_id"]
    assert row["sent_at"] and re.match(r"\d{4}-\d\d-\d\dT", row["sent_at"])
    assert "排隊" in row["message"] or "等" in row["message"]
    assert "waiting" in row["message"].lower() and "cluster" in row["message"].lower()
    for ident in ("tp_wait", row["id"]):
        one = got(w, ann, ident)
        assert one.get("found") is not False, one
        assert one["name"] == "tp_wait" and one["status"] == "waiting" and one["job_id"] == out["job_id"]
        assert one["sent_at"] == row["sent_at"] and one["message"] == row["message"]


def test_still_waiting_after_slurm_took_it(w):
    ann = w.user("ann")
    w.hand_over(by=ann, run="tp_slurm")
    assert [r["status"] for r in listed(w, ann, "tp_slurm")] == ["waiting"]
    assert got(w, ann, "tp_slurm")["status"] == "waiting"


def test_nextflow_report_takes_over_unchanged(w):
    ann = w.user("ann")
    w.launch(caller=ann, answer=form_answer(), run="tp_up")
    assert listed(w, ann, "tp_up")[0]["status"] == "waiting"
    rid = seed(w, "tp_up", "running", None, launch_row=False)
    rows = listed(w, ann, "tp_up")
    assert [(r["id"], r["status"]) for r in rows] == [(rid, "running")]
    assert "message" not in rows[0] and "job_id" not in rows[0]
    one = got(w, ann, rid)
    assert one["status"] == "running" and "message" not in one
    assert got(w, ann, "tp_up").get("found") is False      # by name, as before: the id is the key once the index has the run


def test_refused_or_failed_to_submit_is_not_waiting(w):
    ann = w.user("ann")
    for name in ("tp_refused", "tp_error", "tp_expired"):
        w.launch(caller=ann, answer=form_answer(), run=name)
    sql_exec(w, "UPDATE jobs SET state = 'refused' WHERE id = (SELECT job_id FROM launches WHERE run_name = 'tp_refused')")
    sql_exec(w, "UPDATE jobs SET state = 'error' WHERE id = (SELECT job_id FROM launches WHERE run_name = 'tp_error')")
    sql_exec(w, "UPDATE jobs SET deadline_at = ? WHERE id = (SELECT job_id FROM launches WHERE run_name = 'tp_expired')", (time.time() - 5,))
    assert listed(w, ann) == []
    for name in ("tp_refused", "tp_error", "tp_expired"):
        assert got(w, ann, name).get("found") is False


def test_only_the_callers_own_launch(w):
    ann, bob = w.user("ann"), w.user("bob")
    w.launch(caller=ann, answer=form_answer(), run="tp_ann")
    assert listed(w, bob) == []
    assert got(w, bob, "tp_ann").get("found") is False
    assert [r["name"] for r in listed(w, ann)] == ["tp_ann"]


def test_newest_first_with_the_index_runs(w):
    ann = w.user("ann")
    seed(w, "tp_old", "succeeded", ann, started=time.time() - 7200)
    w.launch(caller=ann, answer=form_answer(), run="tp_new")
    assert [r["name"] for r in listed(w, ann)] == ["tp_new", "tp_old"]


def test_no_status_column_added(w):
    w.user("ann")
    cols = [r[1] for r in w.sql("PRAGMA table_info(launches)")]
    assert not [c for c in cols if "status" in c or c == "state"]


def test_sidebar_lists_it_with_the_same_words(w):
    ann = w.user("ann")
    w.launch(caller=ann, answer=form_answer(), run="tp_side")
    c = logged_in(w, "ann")
    left = pane(c.get("/").text, "left")
    assert "tp_side" in left and "已送出，等待啟動" in plain(left)
    assert 'href="/?run_name=tp_side"' in left
    left_en = pane(c.get("/?lang=en").text, "left")
    assert "tp_side" in left_en and "Sent, waiting to start" in plain(left_en)
    page = c.get("/?run_name=tp_side")
    assert page.status_code == 200 and "◌ 已送出，等待站台回報執行狀態" in plain(pane(page.text, "middle"))
    seed(w, "tp_side", "running", None, launch_row=False)
    left = pane(c.get("/").text, "left")
    assert left.count(">tp_side<") == 1 and "已送出，等待啟動" not in plain(left)


# ---- review fixes: the home page, an aged launch, a cancel, an id collision -------------------------------------------------------------

def test_home_page_with_a_waiting_newest_entry_is_not_a_run_board(w):
    ann = w.user("ann")
    seed(w, "tp_old", "succeeded", ann, started=time.time() - 7200)
    w.launch(caller=ann, answer=form_answer(), run="tp_new")
    c = logged_in(w, "ann")
    rid = listed(w, ann, "tp_new")[0]["id"]
    for url in ("/", "/?run=tp_new", "/?run=" + rid, "/?run_name=tp_new"):
        r = c.get(url)
        mid = pane(r.text, "middle")
        assert r.status_code == 200, url
        for word in ("/run/resume", "/run/relaunch", "/run/cancel", "Resume", "Relaunch", "stage=", "<form"):
            assert word not in mid, (url, word)
    # with no other run the home page is the empty board, not a board of the waiting launch
    assert "tp_new" in pane(c.get("/").text, "left")


def test_home_page_opens_the_newest_real_run_not_the_waiting_one(w):
    ann = w.user("ann")
    rid = seed(w, "tp_real", "running", ann, started=time.time() - 7200)
    w.launch(caller=ann, answer=form_answer(), run="tp_new")
    c = logged_in(w, "ann")
    assert "tp_real" in plain(pane(c.get("/").text, "middle"))
    assert w.sql("SELECT 1") and rid


def test_a_waiting_entry_is_never_a_source_for_a_resume_or_relaunch(w):
    ann = w.user("ann")
    w.launch(caller=ann, answer=form_answer(), run="tp_src")
    c = logged_in(w, "ann")
    for path in ("/run/resume", "/run/relaunch", "/run/cancel"):
        r = c.post(path, data={"run": "tp_src", "csrf": "x"})
        assert r.status_code in (400, 403, 404, 405), (path, r.status_code)


def test_launch_with_a_slurm_number_that_nextflow_never_reported_ages_out(w):
    ann = w.user("ann")
    w.hand_over(by=ann, run="tp_aged")
    from abf_platform import jobs
    assert [r["status"] for r in listed(w, ann, "tp_aged")] == ["waiting"]
    old = time.time() - jobs.SENT_WAITING_MAX_SECONDS - 60
    sql_exec(w, "UPDATE launches SET confirmed_at = ?, submitted_at = ? WHERE run_name = 'tp_aged'", (old, old))
    assert listed(w, ann, "tp_aged") == []
    assert got(w, ann, "tp_aged").get("found") is False


def test_a_confirmed_cancel_is_not_waiting(w):
    ann = w.user("ann")
    w.hand_over(by=ann, run="tp_cancel")
    assert listed(w, ann, "tp_cancel")
    sql_exec(w, "UPDATE launches SET cancel_requested_at = ? WHERE run_name = 'tp_cancel'", (time.time(),))
    assert listed(w, ann, "tp_cancel") == []
    assert got(w, ann, "tp_cancel").get("found") is False


def test_waiting_id_cannot_collide_with_an_index_id(w):
    ann = w.user("ann")
    w.launch(caller=ann, answer=form_answer(), run="tp_clash")
    seed(w, "another", "running", None, launch_row=False, run_id="tp_clash")      # an index run whose id equals the waiting launch's name
    rows = listed(w, ann)
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    waiting = [r for r in rows if r["status"] == "waiting"]
    assert len(waiting) == 1 and waiting[0]["id"] != "tp_clash"
    assert got(w, ann, waiting[0]["id"])["status"] == "waiting" and got(w, ann, waiting[0]["id"])["name"] == "tp_clash"


def test_list_runs_description_names_waiting(w):
    tools, _ = w.mcp([("list_runs", {})])
    d = [t for t in tools if t.name == "list_runs"][0].description
    assert "waiting" in d
