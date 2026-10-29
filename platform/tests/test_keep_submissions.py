# Nothing existing: tests of the keep-submissions task (a submission's content is kept until its owner deletes it); the rules are ours.
"""keep-submissions: confirmed content is never cleared by time, and `forget` clears one run's content on its owner's yes.
Test cases are named in the comments (TC-001 ...), see specs/keep-submissions/test-case.md."""
import ast
import inspect
import json
import re
import sqlite3
import subprocess
import time

import pytest

from helpers import REPO_ROOT, run_cli, tool_json
from human_harness import World, form_answer
from launch_harness import QUESTION_LAUNCH, LaunchData, Pty, cli_argv
from resume_harness import SESSION, FakePerson, Rig
from station_harness import Inproc

DAY = 86400
WARNING = "刪除後無法復原；這個 run 之後不能再續跑或原樣重跑。紀錄（誰、何時送出）會保留。"
NO_FORM = ("這個客戶端無法跳出確認視窗；請在終端機執行 abf-platform forget <run> "
           "(this client cannot show a confirmation form; use the terminal command)")
STARTING = "這個 run 還在準備中，不能刪除 (the run is still starting)"
QUESTION_FORGET = "確定刪除？(y/N)"
AUDIT = ("id", "sha256", "kind", "created_at", "caller_user_id", "state", "channel", "confirmed_at", "expires_at")
SPEC = REPO_ROOT / "specs" / "keep-submissions"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


@pytest.fixture
def data(tmp_path, monkeypatch):
    return LaunchData(Inproc(tmp_path / "ip", monkeypatch))


def actions():
    from abf_platform import actions as a
    return a


# ---- helpers ---------------------------------------------------------------------------------------------------------------

def sql_exec(w, text, args=()):
    con = sqlite3.connect(str(w.ip.state_db))
    con.execute(text, args)
    con.commit()
    con.close()


def put_row(w, state, age_days=0.0, kind="launch", run="old-run", caller=None, expired_days=None):
    """A confirmation row with its content, made `age_days` ago. A pending one expired `expired_days` ago."""
    import secrets
    now = time.time()
    rid = secrets.token_hex(16)
    bundle = {"run_name": run, "kind": kind}
    created = now - age_days * DAY
    expires = (now - expired_days * DAY) if expired_days is not None else (created + 600 if state == "pending" else None)
    sql_exec(w, "INSERT INTO confirmations (id, sha256, kind, created_at, caller_user_id, state, channel, confirmed_at, expires_at, "
                "ce_name, bundle_json, screen_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'lab-a', ?, ?)",
             (rid, "sha-" + rid[:8], kind, created, caller, state, "ELICITED" if state == "confirmed" else None,
              created if state == "confirmed" else None, expires, json.dumps(bundle), "what the person saw"))
    return rid


def prune(w):
    """Any create_pending runs the prune."""
    from abf_platform import confirm
    confirm.create_pending(w.ip.state_db, "launch", "lab-a", {"run_name": "trigger", "n": time.time()}, "text", None)


def conf(w, rid):
    return w.sql("SELECT * FROM confirmations WHERE id = ?", (rid,))[0]


def audit(row):
    return {k: row[k] for k in AUDIT}


def add_index_run(w, name, final="succeeded", last_message_ago=0):
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    try:
        with con:
            con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at) "
                        "VALUES (?, ?, ?, 'live', ?, 1, 2, ?)", ("id-" + name, "sess-" + name, name, final, time.time() - last_message_ago))
    finally:
        con.close()


def scn(w, ann, name="run-one", final="succeeded", index=True, job_state="done"):
    """A run ann launched through a form (a confirmed row with content, a done launch job, a Slurm number), listed in the index."""
    out = w.launch(caller=ann, answer=form_answer(), run=name)
    assert out["sent"] is True, out
    sql_exec(w, "UPDATE launches SET slurm_job_id = 4242, submitted_at = confirmed_at WHERE run_name = ?", (name,))
    if job_state == "done":
        sql_exec(w, "UPDATE jobs SET state = 'done', finished_at = ? WHERE id = ?", (time.time(), out["job_id"]))
    else:
        sql_exec(w, "UPDATE jobs SET state = ?, finished_at = ? WHERE id = ?",
                 (job_state, time.time() if job_state not in ("queued", "claimed") else None, out["job_id"]))
    if index:
        if final == "lost":
            add_index_run(w, name, None, last_message_ago=10 ** 6)
        elif final == "running":
            add_index_run(w, name, None)
        else:
            add_index_run(w, name, final)
    return out


def add_cancel_job(w, name, state, caller=None):
    """A cancel job (and its confirmation) for the run, in the given state."""
    import secrets
    cid = secrets.token_hex(16)
    bundle = {"version": 1, "run_name": name, "slurm_job_id": 4242}
    now = time.time()
    sql_exec(w, "INSERT INTO confirmations (id, sha256, kind, created_at, caller_user_id, state, channel, confirmed_at, ce_name, "
                "bundle_json, screen_text) VALUES (?, ?, 'cancel', ?, ?, 'confirmed', 'ELICITED', ?, 'lab-a', ?, 'cancel screen')",
             (cid, "sha-" + cid[:8], now, caller, now, json.dumps(bundle)))
    sql_exec(w, "INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
                "VALUES ('agent-t', 'lab-a', 'cancel_run', ?, ?, ?, ?, ?)",
             (json.dumps({"bundle": bundle, "confirmation_id": cid}), state, now, now + 300, cid))
    return cid, w.sql("SELECT id FROM jobs WHERE confirmation_id = ?", (cid,))[0]["id"]


def tables(w):
    """Everything in the two tables that matter, as plain data."""
    return ([tuple(r) for r in w.sql("SELECT * FROM confirmations ORDER BY id")],
            [tuple(r) for r in w.sql("SELECT * FROM jobs ORDER BY id")],
            [tuple(r) for r in w.sql("SELECT * FROM launches ORDER BY id")])


def forget_tool(w, run, caller, answer):
    return tool_json(w.call("forget", {"run_name": run}, caller=caller, answer=answer))


def forget_action(w, run="run-one", caller=None, by=None):
    a = actions()
    return a.forget(w.ip.state_db, w.ip.index, run, confirmed_by=by or a.TERMINAL, caller=caller)


def terminal_forget(w, run, answer):
    p = Pty(cli_argv("forget", run), w.data.env())
    assert p.wait_for(QUESTION_FORGET, 30), p.text()
    shown = p.text()
    if answer is not None:
        p.send(answer)
    rc, text = p.finish(30)
    return rc, shown, text


def cleared(w, rid):
    r = conf(w, rid)
    return r["bundle_json"] is None and r["screen_text"] is None


def job_cleared(w, jid, name):
    return json.loads(w.sql("SELECT args_json FROM jobs WHERE id = ?", (jid,))[0]["args_json"]) == {
        "forgotten": True, "bundle": {"run_name": name}}


# ---- US1: confirmed content is not cleared by time ------------------------------------------------------------------------------

def test_tc001_tc002_a_launch_confirmed_400_days_ago_keeps_its_content_and_audit(w):
    # TC-001, TC-002
    w.user("ann")
    rid = put_row(w, "confirmed", age_days=400)
    before = conf(w, rid)
    prune(w)
    after = conf(w, rid)
    assert after["bundle_json"] == before["bundle_json"] and after["screen_text"] == before["screen_text"] == "what the person saw"
    assert audit(after) == audit(before) and after["state"] == "confirmed"


def test_tc003_a_row_confirmed_8_days_ago_keeps_its_content(w):
    # TC-003
    w.user("ann")
    rid = put_row(w, "confirmed", age_days=8)
    prune(w)
    assert conf(w, rid)["bundle_json"] is not None and conf(w, rid)["screen_text"] is not None


@pytest.mark.parametrize("state,days,gone", [("pending", 8, True), ("pending", 6, False), ("void", 8, True), ("void", 6, False)])
def test_tc004_to_tc007_unsent_rows_lose_their_content_after_seven_days(w, state, days, gone):
    # TC-004 (pending, 8 days), TC-005 (pending, 6 days), TC-006 (void, 8 days), TC-007 (void, 6 days)
    w.user("ann")
    rid = put_row(w, state, age_days=days + (0.01 if state == "pending" else 0), expired_days=days if state == "pending" else None)
    prune(w)
    assert cleared(w, rid) is gone


def test_tc008_the_cleared_unsent_rows_keep_their_audit_columns(w):
    # TC-008
    w.user("ann")
    a = put_row(w, "pending", age_days=8.01, expired_days=8)
    b = put_row(w, "void", age_days=8)
    before = {rid: audit(conf(w, rid)) for rid in (a, b)}
    prune(w)
    for rid in (a, b):
        assert cleared(w, rid)
        assert audit(conf(w, rid)) == before[rid]


def test_tc009_the_constant_says_unsent():
    # TC-009
    from abf_platform import confirm
    assert confirm.KEEP_UNSENT_SECONDS == 7 * 86400
    assert not hasattr(confirm, "KEEP_CONTENT_SECONDS")


def test_tc010_the_two_inverted_tests_assert_confirmed_rows_keep_their_content():
    # TC-010: the pins of R1 now say a confirmed row keeps its content; the unsent half stays as it was
    one = (REPO_ROOT / "platform" / "tests" / "test_review_fixes.py").read_text(encoding="utf-8")
    two = (REPO_ROOT / "platform" / "tests" / "test_review_fixes_2.py").read_text(encoding="utf-8")
    assert 'assert rows[ok["id"]]["bundle_json"] is not None and rows[ok["id"]]["screen_text"] is not None' in one
    assert 'assert r["bundle_json"] is None and r["screen_text"] is None' in one          # the void and pending half is untouched
    assert 'assert rows[rid]["bundle_json"] is not None and rows[rid]["screen_text"] is not None' in two
    assert 'rows[rid]["bundle_json"] is None' not in two


# ---- US2: the owner forgets one run ----------------------------------------------------------------------------------------------

def test_tc011_to_tc014_tc022_the_terminal_forget_clears_content_and_keeps_the_audit(w):
    # TC-011, TC-012, TC-013, TC-014, TC-022 (the terminal has no account and no owner check)
    ann = w.user("ann")
    out = scn(w, ann)
    cid, jid = out["id"], out["job_id"]
    c0 = audit(conf(w, cid))
    j0 = {k: v for k, v in dict(w.sql("SELECT * FROM jobs WHERE id = ?", (jid,))[0]).items()
          if k not in ("args_json", "forgotten_at", "forgotten_by")}
    rc, shown, text = terminal_forget(w, "run-one", "y\n")
    assert rc == 0, text
    assert cleared(w, cid)                                                                                      # TC-011
    assert audit(conf(w, cid)) == c0 and conf(w, cid)["state"] == "confirmed"                                   # TC-012
    assert conf(w, cid)["forgotten_at"] is not None and conf(w, cid)["forgotten_by"] is None                    # TC-013
    row = w.sql("SELECT * FROM jobs WHERE id = ?", (jid,))[0]
    assert row["forgotten_at"] is not None and row["forgotten_by"] is None
    assert job_cleared(w, jid, "run-one")                                                                       # TC-014
    assert {k: v for k, v in dict(row).items() if k not in ("args_json", "forgotten_at", "forgotten_by")} == j0


def test_tc015_a_confirmed_cancel_and_its_job_are_cleared_too(w):
    # TC-015
    ann = w.user("ann")
    scn(w, ann)
    ccid, cjid = add_cancel_job(w, "run-one", "done", caller=ann.user_id)
    c0 = audit(conf(w, ccid))
    r = forget_action(w)
    assert r["ok"] is True, r
    assert cleared(w, ccid) and audit(conf(w, ccid)) == c0
    assert job_cleared(w, cjid, "run-one")
    assert conf(w, ccid)["forgotten_at"] is not None and w.sql("SELECT forgotten_at FROM jobs WHERE id = ?", (cjid,))[0][0] is not None


def test_tc016_a_terminal_confirmed_launch_has_both_copies_cleared(rig):
    # TC-016 (F5: the confirmation of a terminal launch holds the content too; the job holds a copy)
    rig.first("run-one")
    w = rig.w
    cid = w.sql("SELECT id FROM confirmations WHERE channel = 'TERMINAL' AND kind = 'launch'")[0]["id"]
    jid = rig.sql("SELECT id FROM jobs WHERE confirmation_id = ?", (cid,))[0]["id"]
    assert conf(w, cid)["bundle_json"] is not None
    c0 = audit(conf(w, cid))
    r = forget_action(w)
    assert r["ok"] is True, r
    assert cleared(w, cid) and audit(conf(w, cid)) == c0 and conf(w, cid)["forgotten_at"] is not None
    assert job_cleared(w, jid, "run-one") and w.sql("SELECT forgotten_at FROM jobs WHERE id = ?", (jid,))[0][0] is not None


def test_tc017_pending_and_void_requests_of_the_run_are_cleared_and_the_open_one_is_voided(w):
    # TC-017
    ann = w.user("ann")
    w.launch(caller=ann, answer=form_answer("decline"), run="run-one")             # a void launch request naming run-one
    void_id = w.sql("SELECT id FROM confirmations WHERE state = 'void'")[0]["id"]
    scn(w, ann)
    pending = tool_json(w.call("cancel", {"run_name": "run-one"}, caller=ann))["id"]       # no form: an open pending request
    assert conf(w, pending)["state"] == "pending" and conf(w, pending)["bundle_json"] is not None
    assert forget_action(w)["ok"] is True
    for rid in (void_id, pending):
        assert cleared(w, rid) and conf(w, rid)["forgotten_at"] is not None
    assert conf(w, pending)["state"] == "void"


def test_tc018_another_run_is_not_touched(w):
    # TC-018
    ann = w.user("ann")
    scn(w, ann, "run-one")
    other = scn(w, ann, "run-two")
    cj_id, cj_job = add_cancel_job(w, "run-two", "done", caller=ann.user_id)
    before = (conf(w, other["id"]), conf(w, cj_id), w.sql("SELECT * FROM jobs WHERE id = ?", (other["job_id"],))[0],
              w.sql("SELECT * FROM jobs WHERE id = ?", (cj_job,))[0])
    assert forget_action(w, "run-one")["ok"] is True
    after = (conf(w, other["id"]), conf(w, cj_id), w.sql("SELECT * FROM jobs WHERE id = ?", (other["job_id"],))[0],
             w.sql("SELECT * FROM jobs WHERE id = ?", (cj_job,))[0])
    assert [tuple(r) for r in after] == [tuple(r) for r in before]
    assert after[0]["forgotten_at"] is None


def test_tc019_the_terminal_shows_the_warning_and_waits_for_y(w):
    # TC-019
    ann = w.user("ann")
    out = scn(w, ann)
    p = Pty(cli_argv("forget", "run-one"), w.data.env())
    assert p.wait_for(QUESTION_FORGET, 30), p.text()
    assert WARNING in p.text() and "run-one" in p.text()
    assert p.text().rstrip("\n").endswith(QUESTION_FORGET)
    assert not cleared(w, out["id"]), "nothing is cleared before the answer"
    p.send("n\n")
    p.finish(30)


@pytest.mark.parametrize("answer", ["n\n", "\n", "yes\n", "no\n"])
def test_tc020_anything_but_y_clears_nothing(w, answer):
    # TC-020
    ann = w.user("ann")
    out = scn(w, ann)
    before = tables(w)
    rc, shown, text = terminal_forget(w, "run-one", answer)
    assert rc != 0
    assert tables(w) == before and not cleared(w, out["id"])


def test_tc021_forget_takes_no_yes_flag(w):
    # TC-021
    ann = w.user("ann")
    out = scn(w, ann)
    before = tables(w)
    r = run_cli(["forget", "run-one", "--yes"], env=w.data.env(), timeout=60)
    assert r.returncode != 0 and "unrecognized" in (r.stderr + r.stdout)
    assert tables(w) == before and not cleared(w, out["id"])


@pytest.mark.parametrize("final", ["succeeded", "failed", "aborted"])
def test_tc023_tc024_tc025_a_run_in_a_stored_final_status_may_be_forgotten(w, final):
    # TC-023 (succeeded), TC-024 (failed), TC-025 (aborted)
    ann = w.user("ann")
    out = scn(w, ann, final=final)
    r = forget_action(w)
    assert r["ok"] is True, r
    assert cleared(w, out["id"])


def test_tc026_forgetting_twice_says_already_deleted_and_changes_nothing(w):
    # TC-026
    ann = w.user("ann")
    scn(w, ann)
    assert forget_action(w)["ok"] is True
    before = tables(w)
    r = forget_action(w)
    assert "已經刪除過了" in r["message"] and "already deleted" in r["message"]
    assert tables(w) == before


def test_tc027_an_old_platform_db_gains_the_two_columns_and_loses_no_row(tmp_path):
    # TC-027
    from abf_platform import store
    path = tmp_path / "old" / "platform.db"
    store.init_state(path)
    con = sqlite3.connect(str(path))
    for table in ("confirmations", "jobs"):
        for col in ("forgotten_at", "forgotten_by"):
            if col in {r[1] for r in con.execute("PRAGMA table_info(%s)" % table)}:
                con.execute("ALTER TABLE %s DROP COLUMN %s" % (table, col))
    now = time.time()
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, state, bundle_json, screen_text) "
                "VALUES ('c1', 's', 'launch', ?, 'confirmed', '{\"run_name\": \"r\"}', 'screen')", (now,))
    con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
                "VALUES ('a', 'ce', 'launch_nextflow', '{\"bundle\": {}}', 'done', ?, ?, 'c1')", (now, now + 5))
    con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                "VALUES ('a', 'ce', 'preflight', '{}', 'done', ?, ?)", (now, now + 5))
    con.commit()
    old = {t: [tuple(r) for r in con.execute("SELECT * FROM %s ORDER BY 1" % t)] for t in ("confirmations", "jobs")}
    old_cols = {t: [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)] for t in old}
    con.close()
    store.connect_state(path).close()
    con = sqlite3.connect(str(path))
    for t in old:
        cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)]
        assert "forgotten_at" in cols and "forgotten_by" in cols, t
        rows = [tuple(r) for r in con.execute("SELECT %s FROM %s ORDER BY 1" % (", ".join(old_cols[t]), t))]
        assert rows == old[t], t
    con.close()


# ---- US3: over MCP and by other people ----------------------------------------------------------------------------------------

def test_tc030_tc031_somebody_elses_run_and_a_missing_run_answer_the_same_and_nothing_changes(w):
    # TC-030, TC-031
    ann = w.user("ann")
    bob = w.user("bob")
    out = scn(w, ann)
    before = tables(w)
    seen = []
    mine = forget_tool(w, "run-one", bob, form_answer(seen=seen))
    gone = forget_tool(w, "run-999", bob, form_answer(seen=seen))
    assert mine == gone and mine["ok"] is False
    assert "not found" in mine["message"] and "run-one" not in mine["message"]
    assert seen == [] and tables(w) == before and not cleared(w, out["id"])


def test_tc032_tc033_the_owner_forgets_through_a_form_that_shows_the_warning(w):
    # TC-032, TC-033
    ann = w.user("ann")
    out = scn(w, ann)
    seen = []
    r = forget_tool(w, "run-one", ann, form_answer(seen=seen))
    assert r["ok"] is True, r
    assert len(seen) == 1 and WARNING in seen[0].message
    assert cleared(w, out["id"]) and job_cleared(w, out["job_id"], "run-one")
    assert conf(w, out["id"])["forgotten_by"] == str(ann.user_id) and conf(w, out["id"])["forgotten_at"] is not None
    job = w.sql("SELECT * FROM jobs WHERE id = ?", (out["job_id"],))[0]
    assert job["forgotten_by"] == str(ann.user_id) and job["forgotten_at"] is not None


@pytest.mark.parametrize("action", ["decline", "cancel"])
def test_tc034_a_refused_form_clears_nothing_and_writes_no_confirmation(w, action):
    # TC-034
    ann = w.user("ann")
    out = scn(w, ann)
    before = tables(w)
    r = forget_tool(w, "run-one", ann, form_answer(action, content={} if action == "cancel" else None))
    assert r["ok"] is False
    assert tables(w) == before and not cleared(w, out["id"])


def test_tc035_tc036_forget_writes_no_confirmation_row_and_queues_no_job(w):
    # TC-035, TC-036
    ann = w.user("ann")
    scn(w, ann)
    n_conf, n_jobs = len(w.sql("SELECT id FROM confirmations")), len(w.sql("SELECT id FROM jobs"))
    assert forget_tool(w, "run-one", ann, form_answer())["ok"] is True
    assert len(w.sql("SELECT id FROM confirmations")) == n_conf and len(w.sql("SELECT id FROM jobs")) == n_jobs


def test_tc037_an_untrusted_form_is_refused_with_the_terminal_hint_and_writes_nothing(w):
    # TC-037
    ann = w.user("ann")
    scn(w, ann)
    before = tables(w)
    connector = actions().Caller.connector(ann.user_id, "ann", "lab-x", False)
    seen = []
    r = forget_tool(w, "run-one", connector, form_answer(seen=seen))
    assert r["ok"] is False and NO_FORM in r["message"] and "confirmation_url" not in r and "http" not in r["message"]
    assert seen == [] and tables(w) == before


def test_tc038_stdio_without_a_form_is_refused_with_the_same_hint(w):
    # TC-038
    ann = w.user("ann")
    scn(w, ann)
    before = tables(w)
    r = forget_tool(w, "run-one", None, None)
    assert r["ok"] is False and NO_FORM in r["message"]
    assert tables(w) == before


def test_tc039_stdio_with_a_form_may_forget_and_nobody_is_recorded(w):
    # TC-039
    ann = w.user("ann")
    out = scn(w, ann)
    r = forget_tool(w, "run-one", None, form_answer())
    assert r["ok"] is True, r
    assert cleared(w, out["id"]) and conf(w, out["id"])["forgotten_by"] is None and conf(w, out["id"])["forgotten_at"] is not None


def test_tc040_forget_is_a_registered_tool_and_the_fixed_lists_grew_by_it(w):
    # TC-040
    tools, _ = w.mcp([])
    by = {t.name: t for t in tools}
    assert {"forget", "resume", "relaunch"} <= set(by) and by["forget"].annotations.destructive_hint is True
    assert not (set(by["forget"].input_schema.get("properties", {})) - {"run_name"})
    for fname, needle in (("test_human_channel.py", '"cancel", "describe_module", "find_module", "forget", "get_compute_env"'),
                          ("test_guidance.py", '["launch", "launch_pipeline", "cancel", "forget", "resume", "relaunch"]'),
                          ("test_actions_layer.py", 'WRITE_NAMES = ["launch", "launch_pipeline", "cancel", "forget", "resume", "relaunch"]')):
        assert needle in (REPO_ROOT / "platform" / "tests" / fname).read_text(encoding="utf-8"), fname
    assert callable(getattr(actions(), "forget", None))


def test_tc041_only_the_callers_own_requests_are_cleared_over_mcp(w):
    # TC-041
    ann = w.user("ann")
    bob = w.user("bob")
    scn(w, ann)
    mine, _ = add_cancel_job(w, "run-one", "done", caller=ann.user_id)
    theirs = put_row(w, "confirmed", kind="cancel", run="run-one", caller=bob.user_id)
    before = conf(w, theirs)
    assert forget_tool(w, "run-one", ann, form_answer())["ok"] is True
    assert cleared(w, mine)
    assert tuple(conf(w, theirs)) == tuple(before) and conf(w, theirs)["forgotten_at"] is None


# ---- US4: not now -----------------------------------------------------------------------------------------------------------------

def test_tc050_a_running_run_is_refused_in_two_languages_and_nothing_changes(w):
    # TC-050
    ann = w.user("ann")
    scn(w, ann, final="running")
    before = tables(w)
    seen = []
    r = forget_tool(w, "run-one", ann, form_answer(seen=seen))
    assert r["ok"] is False
    assert re.search("[一-鿿]", r["message"]) and re.search("running", r["message"])
    assert seen == [] and tables(w) == before


def test_tc051_a_lost_run_is_refused(w):
    # TC-051
    ann = w.user("ann")
    scn(w, ann, final="lost")
    before = tables(w)
    r = forget_tool(w, "run-one", ann, form_answer())
    assert r["ok"] is False and tables(w) == before


@pytest.mark.parametrize("job_state", ["queued", "claimed"])
def test_tc052_tc056_a_run_whose_launch_job_is_queued_or_claimed_is_still_starting(w, job_state):
    # TC-052 (queued), TC-056 (claimed)
    ann = w.user("ann")
    scn(w, ann, index=False, job_state=job_state)
    before = tables(w)
    r = forget_tool(w, "run-one", ann, form_answer())
    assert r["ok"] is False and STARTING in r["message"]
    assert tables(w) == before


@pytest.mark.parametrize("job_state", ["refused", "error", "expired"])
def test_tc057_tc058_tc059_a_launch_that_ended_without_reaching_the_index_may_be_forgotten(w, job_state):
    # TC-057 (refused), TC-058 (error), TC-059 (expired)
    ann = w.user("ann")
    out = scn(w, ann, index=False, job_state=job_state)
    confirmation = w.sql("SELECT id FROM confirmations WHERE state = 'confirmed' AND kind = 'launch'")[0]["id"]
    before = audit(conf(w, confirmation))
    r = forget_tool(w, "run-one", ann, form_answer())
    assert r["ok"] is True and STARTING not in r["message"], r
    assert cleared(w, confirmation) and audit(conf(w, confirmation)) == before
    assert job_cleared(w, out["job_id"], "run-one")
    assert conf(w, confirmation)["forgotten_at"] is not None


@pytest.mark.parametrize("state", ["queued", "claimed"])
def test_tc053_tc054_a_job_still_queued_or_claimed_blocks_it(w, state):
    # TC-053 (queued), TC-054 (claimed)
    ann = w.user("ann")
    scn(w, ann)
    add_cancel_job(w, "run-one", state, caller=ann.user_id)
    before = tables(w)
    r = forget_tool(w, "run-one", ann, form_answer())
    assert r["ok"] is False and tables(w) == before


def test_tc055_the_terminal_refuses_a_running_run_too(w):
    # TC-055
    ann = w.user("ann")
    scn(w, ann, final="running")
    before = tables(w)
    r = run_cli(["forget", "run-one"], env=w.data.env(), timeout=60)
    assert r.returncode != 0 and QUESTION_FORGET not in r.stdout + r.stderr
    assert tables(w) == before


# ---- US5: nothing breaks afterwards ----------------------------------------------------------------------------------------------

def _expire_launch_job(w, out):
    sql_exec(w, "UPDATE jobs SET state = 'expired', finished_at = ? WHERE id = ?", (time.time(), out["job_id"]))
    sql_exec(w, "UPDATE launches SET slurm_job_id = NULL, submitted_at = NULL WHERE run_name = 'run-one'")


def test_tc060_a_late_answer_for_a_forgotten_launch_job_is_taken(w):
    # TC-060
    from abf_platform import jobs
    ann = w.user("ann")
    out = scn(w, ann)
    _expire_launch_job(w, out)
    assert forget_action(w)["ok"] is True
    code, body = jobs.take_result(w.ip.state_db, "agent-t", out["job_id"], "done", {"ok": True, "slurm_job_id": 777}, time.time,
                                  tokens_path=w.ip.tokens)
    assert code == 200 and body["late"] is True
    assert w.sql("SELECT slurm_job_id FROM launches WHERE run_name = 'run-one'")[0][0] == 777


def test_tc060_a_late_failure_for_a_forgotten_launch_job_still_finds_the_run_name(w):
    # TC-060 (the error path reads the run name and revokes its token)
    from abf_platform import jobs
    ann = w.user("ann")
    out = scn(w, ann)
    _expire_launch_job(w, out)
    assert forget_action(w)["ok"] is True
    code, body = jobs.take_result(w.ip.state_db, "agent-t", out["job_id"], "error", {"ok": False, "message": "x"}, time.time,
                                  tokens_path=w.ip.tokens)
    assert code == 200 and body["late"] is True


def test_tc061_a_late_answer_for_a_forgotten_cancel_job_changes_no_other_run(w):
    # TC-061
    from abf_platform import jobs
    ann = w.user("ann")
    scn(w, ann, "run-one")
    scn(w, ann, "run-two")
    _, cjid = add_cancel_job(w, "run-one", "expired", caller=ann.user_id)
    assert forget_action(w, "run-one")["ok"] is True
    code, body = jobs.take_result(w.ip.state_db, "agent-t", cjid, "done", {"ok": True}, time.time, tokens_path=w.ip.tokens)
    assert code == 200 and body["late"] is True
    assert [r[0] for r in w.sql("SELECT cancel_requested_at FROM launches")] == [None, None]


def test_tc062_the_ledger_records_what_the_follow_up_did():
    # TC-062 (F1 to F5 are done: 009e is merged, so the hook point became real code)
    text = (SPEC / "ledger.md").read_text(encoding="utf-8")
    assert "origin/v3" in text and "內容已被擁有者刪除" in text and "content deleted by its owner" in text
    assert "009e is not on v3" not in text and "none of its code was pulled in" not in text
    for needle in ("F1", "F2", "F3", "F4", "F5"):
        assert re.search(r"- \[x\][^\n]*%s" % needle, text), needle
    assert not re.search(r"- \[ \]", text)


def test_tc063_the_ledger_records_the_owed_web_parity():
    # TC-063
    text = (SPEC / "ledger.md").read_text(encoding="utf-8")
    assert "docs/ROADMAP.md:98" in text and "forget" in text and "web" in text.lower()


# ---- US6: documents --------------------------------------------------------------------------------------------------------------

def _platform_md():
    return (REPO_ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")


def test_tc070_the_retention_paragraph_says_confirmed_content_stays_until_its_owner_deletes_it():
    # TC-070
    text = _platform_md()
    assert "a confirmed request keeps its content until its owner deletes it" in text
    assert "whatever the channel" in text and "terminal" in text.split("whatever the channel", 1)[1][:120]
    assert "void or expired pending request loses its content (bundle and summary) after 7 days" in text
    assert "an expired, void or confirmed request loses its content" not in text


def test_tc071_the_new_action_is_described():
    # TC-071
    text = _platform_md()
    assert "abf-platform forget RUN" in text and "`forget`" in text
    i = text.index("abf-platform forget RUN")
    para = text[i - 1500:i + 2500]
    for needle in ("owner", "running", "cannot be undone", "audit"):
        assert needle in para, needle


def test_tc072_the_job_copy_sentence_now_says_forget_clears_it_too():
    # TC-072
    text = _platform_md()
    i = text.index("the job keeps its own copy of what was queued")
    assert "forget" in text[i:i + 250] and "clears" in text[i:i + 250]


def test_tc073_the_changelog_top_entry_names_the_change():
    # TC-073
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    bullets = [ln for ln in text.split("## 3.0.0-dev", 1)[1].splitlines() if ln.startswith("- ")]
    assert "keep-submissions" in bullets[0] and "forget" in bullets[0] and "confirmed" in bullets[0]


def test_tc064_the_ledger_records_the_three_known_limits():
    # TC-064
    text = (SPEC / "ledger.md").read_text(encoding="utf-8")
    low = text.lower()
    assert "7 days after" in low and "result_json" in text and "late_result_json" in text
    assert "no web delete" in low and "maintainer may revisit" in low
    assert "has its bundle only in the job copy" not in text      # F5: no longer true of a new row
    assert "old" in low and "format" in low


def test_tc065_forget_leaves_the_results_a_job_holds(w):
    # TC-065
    ann = w.user("ann")
    out = scn(w, ann)
    sql_exec(w, "UPDATE jobs SET result_json = ?, late_result_json = ? WHERE id = ?", ('{"ok": true}', '{"late": 1}', out["job_id"]))
    assert forget_tool(w, "run-one", ann, form_answer())["ok"] is True
    row = w.sql("SELECT result_json, late_result_json FROM jobs WHERE id = ?", (out["job_id"],))[0]
    assert (row["result_json"], row["late_result_json"]) == ('{"ok": true}', '{"late": 1}')


def test_tc066_an_old_job_row_goes_but_the_confirmed_content_stays(w):
    # TC-066
    ann = w.user("ann")
    out = scn(w, ann, "run-one")
    confirmation = w.sql("SELECT id FROM confirmations WHERE state = 'confirmed' AND kind = 'launch'")[0]["id"]
    sql_exec(w, "UPDATE jobs SET state = 'done', finished_at = ? WHERE id = ?", (time.time() - 8 * DAY, out["job_id"]))
    scn(w, ann, "run-two")                      # queues a new job, which prunes the finished ones older than seven days
    assert w.sql("SELECT id FROM jobs WHERE id = ?", (out["job_id"],)) == []
    assert not cleared(w, confirmation) and conf(w, confirmation)["bundle_json"] is not None


def test_tc094_tc095_tc104_eleven_tools_and_the_column_names_scan_still_catches_other_names(w):
    # TC-094 (the proof that forgotten_org still fails is in test_station_envs.py), TC-095 (the old lists are compared with v3 by the
    # acceptor), TC-104 (the registered tools: six read, five that only ask, no field that says yes)
    tools, _ = w.mcp([])
    names = sorted(t.name for t in tools)
    assert names == ["cancel", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_validation", "launch", "launch_pipeline", "list_agents", "list_compute_envs", "list_pipelines", "list_runs",
                     "list_site_files", "list_used_pipelines", "my_usage", "read_task_log", "relaunch", "resume", "run_outputs"]
    saying_yes = {"yes", "y", "confirm", "confirmed", "confirmation", "confirmation_id", "approve", "approved", "kind", "command"}
    for t in tools:
        if t.name in ("launch", "launch_pipeline", "cancel", "resume", "relaunch", "forget"):
            assert t.annotations.read_only_hint is False and not (set(t.input_schema.get("properties", {})) & saying_yes), t.name
        else:
            assert t.annotations.read_only_hint is True, t.name


def test_tc074_every_automatic_test_case_is_named_in_a_comment_of_this_file():
    # TC-074 (the cases the acceptor judges from files or git are not asked for here)
    src = open(__file__, encoding="utf-8").read()
    cases = (SPEC / "test-case.md").read_text(encoding="utf-8")
    ids = sorted(set(re.findall(r"^\| (TC-\d{3}) ", cases, re.M)))
    by_reading = {10, 62, 63, 64, 75, 84, 90, 91, 93, 94, 95, 100, 101, 102, 103, 105, 106, 110, 111, 112}
    wanted = [i for i in ids if int(i[3:]) not in by_reading]
    assert len(ids) >= 120 and len(wanted) >= 100
    missing = [i for i in wanted if not re.search(r"#[^\n]*\b%s\b" % i, src)]
    assert missing == []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            assert any(isinstance(n, ast.Assert) for n in ast.walk(node)), node.name


# ---- out of scope ----------------------------------------------------------------------------------------------------------------

def test_tc080_tc092_forget_queues_no_job_and_leaves_the_files_of_the_site(w, tmp_path):
    # TC-080, TC-092
    ann = w.user("ann")
    scn(w, ann)
    site = tmp_path / "site"
    for d in ("rawdata", "results", "analysis"):
        (site / d).mkdir(parents=True)
        (site / d / "guard.txt").write_text("keep " + d)
    n_jobs = [tuple(r) for r in w.sql("SELECT id, kind, state FROM jobs ORDER BY id")]
    assert forget_tool(w, "run-one", ann, form_answer())["ok"] is True
    assert [tuple(r) for r in w.sql("SELECT id, kind, state FROM jobs ORDER BY id")] == n_jobs
    for d in ("rawdata", "results", "analysis"):
        assert (site / d / "guard.txt").read_text() == "keep " + d


def test_tc081_the_run_stays_in_the_run_list(w):
    # TC-081
    ann = w.user("ann")
    scn(w, ann)
    before = tool_json(w.call("get_run", {"run_id": "id-run-one"}, caller=ann))
    assert forget_tool(w, "run-one", ann, form_answer())["ok"] is True
    after = tool_json(w.call("get_run", {"run_id": "id-run-one"}, caller=ann))
    assert after == before and after["status"] == "succeeded"
    assert [r["name"] for r in tool_json(w.call("list_runs", {}, caller=ann))["runs"]] == ["run-one"]


def test_tc082_the_web_has_no_forget_route(w):
    # TC-082
    ann = w.user("ann")
    out = scn(w, ann)
    c = w.web()
    w.login(c, "ann")
    paths = [getattr(r, "path", "") for r in c.app.routes]
    assert not [p for p in paths if "forget" in p or "delete" in p]
    for url in ("/forget/run-one", "/runs/run-one/forget", "/c/%s/forget" % out["id"]):
        assert c.post(url, data={}).status_code in (404, 405)
    assert not cleared(w, out["id"])


def test_tc083_no_new_confirmation_kind_and_approve_knows_nothing_of_forget():
    # TC-083
    from abf_platform import confirm, store
    assert set(confirm.JOB_KIND) == {"launch", "cancel", "clean_work"}
    assert "CHECK (kind IN ('launch', 'cancel', 'clean_work'))" in store.STATE_SCHEMA
    assert "forget" not in inspect.getsource(confirm.approve)


V3_ATTEMPT_NAMES = {"prepare_resume", "prepare_relaunch", "resume_screen", "relaunch_screen", "request_resume", "request_relaunch",
                    "resume_tool", "relaunch_tool", "cmd_resume", "cmd_relaunch", "render_resume_bundle", "render_resume", "run_resume"}


def test_tc084_no_resume_or_relaunch_code_of_our_own_came_in():
    # TC-084: 009e is in; what this task added to it is not a function of its own that resumes or relaunches. Every function whose name
    # says resume or relaunch is one that v3 has; the confirmation flow and the submit file were not touched (no new door).
    found = set()
    for p in (REPO_ROOT / "platform").rglob("*.py"):
        if "tests" in p.parts:
            continue
        found |= {n.name for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and re.search(r"resume|relaunch", n.name)}
    assert found - V3_ATTEMPT_NAMES == set(), found - V3_ATTEMPT_NAMES
    assert not re.search(r"forget\w*\(", inspect.getsource(actions().launch) + inspect.getsource(actions().approve))


# ---- the safety net -------------------------------------------------------------------------------------------------------------

def test_tc090_the_second_state_scan_passes():
    # TC-090
    r = subprocess.run(["bash", str(REPO_ROOT / "tests" / "no_second_run_state_test.sh")], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


def test_tc091_an_unconfirmed_launch_still_queues_nothing(w):
    # TC-091
    ann = w.user("ann")
    out = w.launch(caller=ann)
    assert out["sent"] is False and w.jobs() == []
    assert not [r for r in w.sql("SELECT id FROM confirmations") if conf(w, r["id"])["state"] == "confirmed"]


# Taken from contract commit 4f41759, so the check needs no git history (CI checkouts are shallow and may not skip).
CONTRACT_SHA256 = {
    "specs/keep-submissions/plan.md": "a6725b71e548cb4710408960aabcf342c99f1ac62fc3cd590816ff17e2110159",
    "specs/keep-submissions/test-case.md": "af5d312a0bddf65b58b990c935f3e94c466f51c5ea65f172e7a73f08fae2b7db",
    "specs/keep-submissions/test-case-overview.md": "8aa79ec0a9f72d6028ed1d98bdb9faf9747d7f36d00548caa4413974c6bcf86d",
}


def test_tc093_the_contract_files_were_not_edited_after_the_contract_commit():
    # TC-093
    import hashlib
    for rel, want in CONTRACT_SHA256.items():
        data = (REPO_ROOT / rel).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == want, rel


# ==== follow-up after PR #133: F1 to F5 ==================================================================================================

FORGOTTEN_WORDS = "內容已被擁有者刪除"
TOO_OLD = "太久了，這次送出的內容已經清掉"
NOT_FOUND = "找不到這個 run (Run not found): %s"


def jobs_of(w):
    return [tuple(r) for r in w.sql("SELECT * FROM jobs ORDER BY id")]


def hours_ago(w, job_id, hours):
    sql_exec(w, "UPDATE jobs SET finished_at = ? WHERE id = ?", (time.time() - hours * 3600, job_id))


# ---- US7: catching up with v3 ------------------------------------------------------------------------------------------------------

def test_tc107_the_instructions_name_all_five_tools_and_keep_the_009e_sentence_within_the_limit():
    # TC-107
    from abf_platform import guidance
    text = guidance.routing_instructions()
    for name in ("launch", "cancel", "resume", "relaunch", "forget"):
        assert name in text, name
    assert "A failed run is relaunched with its name alone; a resume may also carry changed parameters and extra resource settings." in text
    assert "deletes nothing until the person says yes" in guidance.FIXED_SENTENCE
    assert len(text.encode("utf-8")) <= guidance.MAX_BYTES


def test_tc108_the_action_names_and_the_command_set_hold_both_sides():
    # TC-108
    a = actions()
    assert callable(a.request_resume) and callable(a.request_relaunch) and callable(a.forget) and callable(a.request_forget)
    from abf_platform import cli
    top = set(next(x for x in cli.build_parser()._actions if isinstance(getattr(x, "choices", None), dict)).choices)
    assert {"resume", "relaunch", "forget", "oauth", "cancel", "launch"} <= top
    text = (REPO_ROOT / "platform" / "tests" / "test_station_envs.py").read_text(encoding="utf-8")
    assert "launch,resume,relaunch,cancel,forget,launches" in text


def test_tc109_an_older_platform_db_gains_the_009e_and_the_forgotten_columns_and_loses_no_row(tmp_path):
    # TC-109
    from abf_platform import store
    path = tmp_path / "old" / "platform.db"
    store.init_state(path)
    con = sqlite3.connect(str(path))
    drops = {"launches": ("parent_run", "attempt", "attempt_kind", "work_cleaned_at"), "confirmations": ("forgotten_at", "forgotten_by"),
             "jobs": ("forgotten_at", "forgotten_by")}
    for table, cols in drops.items():
        for col in cols:
            if col in {r[1] for r in con.execute("PRAGMA table_info(%s)" % table)}:
                con.execute("ALTER TABLE %s DROP COLUMN %s" % (table, col))
    now = time.time()
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, state) VALUES ('c1', 's', 'launch', ?, 'confirmed')", (now,))
    con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at) VALUES ('r', '/f', 'ce', 'a', ?)", (now,))
    con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                "VALUES ('a', 'ce', 'preflight', '{}', 'done', ?, ?)", (now, now + 5))
    con.commit()
    old = {t: [tuple(r) for r in con.execute("SELECT * FROM %s ORDER BY 1" % t)] for t in drops}
    old_cols = {t: [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)] for t in drops}
    con.close()
    store.connect_state(path).close()
    con = sqlite3.connect(str(path))
    for t in drops:
        cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)]
        assert cols[:len(old_cols[t])] == old_cols[t] and cols[len(old_cols[t]):] == list(drops[t]), (t, cols)
        assert [tuple(r) for r in con.execute("SELECT %s FROM %s ORDER BY 1" % (", ".join(old_cols[t]), t))] == old[t], t
    con.close()


def test_tc113_both_allow_lists_survived_the_merge():
    # TC-113
    envs = (REPO_ROOT / "platform" / "tests" / "test_station_envs.py").read_text(encoding="utf-8")
    plat = (REPO_ROOT / "platform" / "tests" / "test_station_platform.py").read_text(encoding="utf-8")
    assert "forgotten_at" in envs and "forgotten_by" in envs and "forgotten_org" in envs
    assert '("launches", "parent_run")' in plat


# ---- US8: a forgotten run cannot be resumed or relaunched --------------------------------------------------------------------------

@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc120_tc121_the_terminal_refuses_a_forgotten_run(rig, verb):
    # TC-120 (resume), TC-121 (relaunch)
    rig.first("x")
    assert forget_action(rig.w, "x")["ok"] is True
    before = tables(rig.w)
    r = run_cli([verb, "x"], env=rig.w.data.env(), timeout=60)
    out = r.stdout + r.stderr
    assert r.returncode != 0 and FORGOTTEN_WORDS in out and TOO_OLD not in out and "Traceback" not in out, out
    assert "找不到" not in out
    assert tables(rig.w) == before


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc122_tc123_the_mcp_tool_refuses_a_forgotten_run(rig, verb):
    # TC-122 (resume), TC-123 (relaunch)
    rig.first("x")
    assert forget_action(rig.w, "x")["ok"] is True
    before = tables(rig.w)
    out = rig.ask(verb, "x", person=FakePerson(True))
    assert out["ok"] is False and out["sent"] is False and FORGOTTEN_WORDS in out["message"] and TOO_OLD not in out["message"], out
    assert tables(rig.w) == before


def test_tc124_the_first_launch_is_forgotten_and_a_later_attempt_is_refused(rig):
    # TC-124
    rig.first("x")
    rig.attempt("resume", "x")                       # x-a2, failed too
    assert forget_action(rig.w, "x")["ok"] is True
    before = tables(rig.w)
    for verb in ("resume", "relaunch"):
        out = rig.ask(verb, "x-a2", person=FakePerson(True))
        assert out["sent"] is False and FORGOTTEN_WORDS in out["message"], (verb, out)
    assert tables(rig.w) == before


def test_tc125_the_run_it_is_made_from_is_forgotten_and_the_first_launch_is_not(rig):
    # TC-125
    rig.first("x")
    rig.attempt("resume", "x")
    assert forget_action(rig.w, "x-a2")["ok"] is True
    first_cid = rig.w.sql("SELECT id FROM confirmations WHERE kind = 'launch' ORDER BY created_at, id")[0]["id"]
    assert not cleared(rig.w, first_cid)
    before = tables(rig.w)
    for verb in ("resume", "relaunch"):
        out = rig.ask(verb, "x-a2", person=FakePerson(True))
        assert out["sent"] is False and FORGOTTEN_WORDS in out["message"], (verb, out)
    assert tables(rig.w) == before


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc126_tc127_a_bundle_made_before_the_forget_is_refused_when_it_is_queued(rig, verb):
    # TC-126 (resume), TC-127 (relaunch)
    from abf_platform import jobs
    rig.first("x")
    ce, bundle, _row = rig.prepare(verb, "x")
    assert forget_action(rig.w, "x")["ok"] is True
    before = tables(rig.w)
    with pytest.raises(jobs.JobRefused) as e:
        actions().launch(rig.state, ce, bundle, confirmed_by=actions().TERMINAL)
    assert FORGOTTEN_WORDS in str(e.value)
    assert tables(rig.w) == before


def test_tc128_somebody_else_gets_not_found_for_a_forgotten_run(rig):
    # TC-128
    from owner_harness import Duo
    duo = Duo(rig.w)
    out = duo.sent(duo.a, run="x")
    rig.hand_over(out["job_id"], "x")
    rig.set_run("x", "failed")
    assert forget_action(rig.w, "x", caller=duo.a, by=actions().ELICITED)["ok"] is True
    for verb in ("resume", "relaunch"):
        theirs = rig.ask(verb, "x", caller=duo.b, person=FakePerson(True))
        nothing = rig.ask(verb, "nope", caller=duo.b, person=FakePerson(True))
        assert theirs["sent"] is False and theirs["message"] == nothing["message"].replace("nope", "x"), (theirs, nothing)
        assert NOT_FOUND % "x" in theirs["message"] and FORGOTTEN_WORDS not in theirs["message"]


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc129_a_forgotten_run_whose_job_is_long_gone_says_deleted_not_too_old(rig, verb):
    # TC-129
    rig.first("x")
    assert forget_action(rig.w, "x")["ok"] is True
    jid = rig.sql("SELECT job_id FROM launches WHERE run_name = 'x'")[0][0]
    hours_ago(rig.w, jid, 8 * 24)
    rig.first("y")                                   # any later launch prunes the finished jobs older than seven days
    assert rig.sql("SELECT COUNT(*) FROM jobs WHERE id = ?", (jid,))[0][0] == 0
    out = rig.ask(verb, "x", person=FakePerson(True))
    assert out["sent"] is False and FORGOTTEN_WORDS in out["message"] and TOO_OLD not in out["message"], out


def test_tc130_another_run_is_not_affected(rig):
    # TC-130
    rig.first("run-one")
    rig.first("run-two")
    assert forget_action(rig.w, "run-one")["ok"] is True
    out = rig.ask("resume", "run-two", person=FakePerson(True))
    assert out["sent"] is True, out

def test_tc131_a_request_waiting_for_the_page_dies_when_the_run_is_forgotten(rig):
    # TC-131
    from owner_harness import Duo
    duo = Duo(rig.w)
    out = duo.sent(duo.a, run="x")
    rig.hand_over(out["job_id"], "x")
    rig.set_run("x", "failed")
    waiting = rig.resume("x", caller=duo.a, person=None)
    assert waiting["state"] == "pending"
    assert forget_action(rig.w, "x", caller=duo.a, by=actions().ELICITED)["ok"] is True
    jobs_before = jobs_of(rig.w)
    with pytest.raises(Exception) as e:
        actions().approve(rig.state, waiting["id"], confirmed_by=actions().PAGE, caller=duo.a)
    assert conf(rig.w, waiting["id"])["state"] == "void" and "void" in str(e.value)          # F10: void at once, not refused at approve
    assert jobs_of(rig.w) == jobs_before


# ---- US9: forget while the launch is still starting ---------------------------------------------------------------------------------

def _launched(w, ann, hours, index=False, final="succeeded"):
    out = scn(w, ann, index=False)
    hours_ago(w, out["job_id"], hours)
    if index:
        add_index_run(w, "run-one", None if final == "running" else final)
    return out


@pytest.mark.parametrize("hours", [1, 23])
def test_tc140_tc141_a_launch_that_went_out_but_is_not_in_the_index_is_still_starting(w, hours):
    # TC-140 (1 hour ago), TC-141 (23 hours ago)
    ann = w.user("ann")
    _launched(w, ann, hours)
    before = tables(w)
    r = forget_tool(w, "run-one", ann, form_answer())
    assert r["ok"] is False and STARTING in r["message"] and "還在準備中，不能刪除" in r["message"], r
    assert tables(w) == before


def test_tc142_after_24_hours_it_is_treated_as_never_having_reached_the_index(w):
    # TC-142
    ann = w.user("ann")
    out = _launched(w, ann, 25)
    r = forget_tool(w, "run-one", ann, form_answer())
    assert r["ok"] is True, r
    assert cleared(w, out["id"]) and conf(w, out["id"])["forgotten_at"] is not None

def test_tc143_once_the_index_sees_the_run_there_is_no_waiting(w):
    # TC-143
    ann = w.user("ann")
    out = _launched(w, ann, 1, index=True)
    assert forget_tool(w, "run-one", ann, form_answer())["ok"] is True
    assert cleared(w, out["id"])


def test_tc144_a_running_run_in_the_index_is_still_refused(w):
    # TC-144
    ann = w.user("ann")
    _launched(w, ann, 1, index=True, final="running")
    before = tables(w)
    r = forget_tool(w, "run-one", ann, form_answer())
    assert r["ok"] is False and "running" in r["message"] and tables(w) == before


@pytest.mark.parametrize("job_state", ["refused", "error", "expired"])
def test_tc145_a_launch_that_just_ended_badly_may_be_forgotten_at_once(w, job_state):
    # TC-145
    ann = w.user("ann")
    out = scn(w, ann, index=False, job_state=job_state)
    hours_ago(w, out["job_id"], 1 / 60)
    r = forget_tool(w, "run-one", ann, form_answer())
    assert r["ok"] is True and STARTING not in r["message"], r
    assert cleared(w, out["id"])


def test_tc146_the_terminal_refuses_a_starting_launch_with_the_same_words(w):
    # TC-146
    ann = w.user("ann")
    _launched(w, ann, 1)
    before = tables(w)
    r = run_cli(["forget", "run-one"], env=w.data.env(), timeout=60)
    assert r.returncode != 0 and "還在準備中" in r.stdout + r.stderr and QUESTION_FORGET not in r.stdout + r.stderr
    assert tables(w) == before


def test_tc097_no_column_but_the_two_and_no_stored_starting_flag():
    # TC-097
    from abf_platform import store
    cols = re.findall(r"forgot\w*|starting\w*|preparing\w*", store.STATE_SCHEMA)
    assert set(cols) <= {"forgotten_at", "forgotten_by"}, cols
    src = inspect.getsource(actions().forget_check)
    assert "24" in src and "finished_at" in src


# ---- US10: any channel keeps its content ----------------------------------------------------------------------------------------------

def terminal_launch(data, tmp_path, run="run-one"):
    p = Pty(cli_argv(*data.launch_args(tmp_path, run=run)), data.env())
    assert p.wait_for(QUESTION_LAUNCH, 30), p.text()
    p.send("y\n")
    p.finish(60)


def cli_rows(data, table, where="1 = 1"):
    con = sqlite3.connect(str(data.ip.state_db))
    con.row_factory = sqlite3.Row
    try:
        return con.execute("SELECT * FROM %s WHERE %s" % (table, where)).fetchall()
    finally:
        con.close()


def test_tc150_tc151_tc161_a_terminal_launch_leaves_its_content_in_the_confirmation(data, tmp_path):
    # TC-150, TC-151, TC-161
    from abf_launch import build
    from abf_platform import common
    base = (len(cli_rows(data, "confirmations")), len(cli_rows(data, "jobs", "kind = 'launch_nextflow'")))
    terminal_launch(data, tmp_path)
    confs = cli_rows(data, "confirmations", "kind = 'launch'")
    jobs_ = cli_rows(data, "jobs", "kind = 'launch_nextflow'")
    assert (len(confs), len(jobs_)) == (base[0] + 1, base[1] + 1)                                 # TC-161: one and one
    c, j = confs[-1], jobs_[-1]
    assert j["confirmation_id"] == c["id"] and c["state"] == "confirmed" and c["channel"] == "TERMINAL"
    sent = json.loads(j["args_json"])["bundle"]
    assert json.loads(c["bundle_json"]) == sent                                                   # TC-150
    assert c["screen_text"] == build.as_text(build.launch_screen(sent, "lab-a"))
    assert common.bundle_sha256(json.loads(c["bundle_json"])) == c["sha256"]                      # TC-151


def test_tc152_a_form_and_a_page_confirmation_keep_their_content_as_before(w):
    # TC-152
    ann = w.user("ann")
    by_form = scn(w, ann, "run-one")
    page = w.launch(caller=ann, run="run-two")
    assert page["sent"] is False
    from human_harness import pending_id_of
    a = actions()
    rid = pending_id_of(page["confirmation_url"])
    a.approve(w.ip.state_db, rid, confirmed_by=a.PAGE, caller=ann)
    for one in (by_form["id"], rid):
        row = conf(w, one)
        assert row["bundle_json"] is not None and row["screen_text"] is not None and row["state"] == "confirmed"


def _terminal_confirmed(w, run="run-one", screen="what the person approved"):
    """A launch confirmed at the terminal (actions.launch with TERMINAL), as abf-platform launch does it."""
    from abf_launch import build
    ce, bundle = build.prepare_launch(w.ip.state_db, ce="lab-a", pipeline="nf-core/ampliseq", revision="2.18.0", run_name=run,
                                      samplesheet=str(w.sheet), params={"primer": "AGRG"})
    cid, jid = actions().launch(w.ip.state_db, ce, bundle, confirmed_by=actions().TERMINAL)
    assert actions().keep_screen(w.ip.state_db, cid, screen) is True
    return cid, jid


def test_tc153_a_terminal_launch_confirmed_400_days_ago_keeps_its_content(w):
    # TC-153
    w.user("ann")
    cid, _ = _terminal_confirmed(w)
    then = time.time() - 400 * DAY
    sql_exec(w, "UPDATE confirmations SET created_at = ?, confirmed_at = ? WHERE id = ?", (then, then, cid))
    prune(w)
    assert conf(w, cid)["bundle_json"] is not None and conf(w, cid)["screen_text"] == "what the person approved"


def test_tc154_the_old_job_goes_after_seven_days_and_the_terminal_confirmation_stays(w):
    # TC-154
    w.user("ann")
    cid, jid = _terminal_confirmed(w, "run-one")
    sql_exec(w, "UPDATE jobs SET state = 'done', finished_at = ? WHERE id = ?", (time.time() - 8 * DAY, jid))
    _terminal_confirmed(w, "run-two")                 # queues a new job, which prunes the finished ones older than seven days
    assert w.sql("SELECT id FROM jobs WHERE id = ?", (jid,)) == []
    assert conf(w, cid)["bundle_json"] is not None and conf(w, cid)["screen_text"] is not None


def test_tc155_a_terminal_run_is_forgotten_in_both_places(rig):
    # TC-155
    rig.first("run-one")
    cid = rig.w.sql("SELECT id FROM confirmations WHERE channel = 'TERMINAL' AND kind = 'launch'")[0]["id"]
    jid = rig.sql("SELECT id FROM jobs WHERE confirmation_id = ?", (cid,))[0]["id"]
    c0 = audit(conf(rig.w, cid))
    assert forget_action(rig.w)["ok"] is True
    assert cleared(rig.w, cid) and audit(conf(rig.w, cid)) == c0 and conf(rig.w, cid)["forgotten_at"] is not None
    assert job_cleared(rig.w, jid, "run-one") and rig.w.sql("SELECT forgotten_at FROM jobs WHERE id = ?", (jid,))[0][0] is not None


def _prune_job_of(rig, run, other):
    jid = rig.sql("SELECT job_id FROM launches WHERE run_name = ?", (run,))[0][0]
    hours_ago(rig.w, jid, 10 * 24)
    rig.first(other)                                  # any later launch prunes
    assert rig.sql("SELECT COUNT(*) FROM jobs WHERE id = ?", (jid,))[0][0] == 0


def test_tc156_a_resume_reads_the_confirmation_when_the_job_is_gone(rig):
    # TC-156
    rig.first("x")
    _prune_job_of(rig, "x", "y")
    out = rig.resume("x", person=FakePerson(True))
    assert out["sent"] is True and TOO_OLD not in out["message"], out


def test_tc157_a_relaunch_reads_the_confirmation_and_keeps_samples_and_parameters(rig):
    # TC-157
    first = rig.first("x")
    _prune_job_of(rig, "x", "y")
    out = rig.relaunch("x", person=FakePerson(True))
    assert out["sent"] is True, out
    sent = rig.bundle_of_job(out["job_id"])
    assert sent["samplesheet"] == first["samplesheet"] and sent["params"] == first["params"] and sent["pipeline"] == first["pipeline"]


def _old_format(rig):
    sql_exec(rig.w, "UPDATE confirmations SET bundle_json = NULL, screen_text = NULL WHERE channel = 'TERMINAL'")


def test_tc158_an_old_format_row_is_read_from_its_job(rig):
    # TC-158
    rig.first("x")
    _old_format(rig)
    out = rig.resume("x", person=FakePerson(True))
    assert out["sent"] is True, out


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc159_tc160_an_old_format_row_whose_job_is_gone_says_too_old(rig, verb):
    # TC-159 (resume), TC-160 (relaunch)
    rig.first("x")
    _old_format(rig)
    sql_exec(rig.w, "DELETE FROM jobs WHERE id = (SELECT job_id FROM launches WHERE run_name = 'x')")
    before = rig.counts()
    out = rig.ask(verb, "x", person=FakePerson(True))
    assert out["sent"] is False and TOO_OLD in out["message"], out
    assert rig.counts() == before


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc096_the_new_refusals_and_the_kept_content_open_no_way_to_send_without_a_yes(rig, verb):
    # TC-096 (the 009e single cases and tests/no_second_run_state_test.sh run with the whole platform suite)
    rig.first("x")
    before = rig.counts()
    declined = rig.ask(verb, "x", person=FakePerson(False))
    assert declined["sent"] is False and (rig.counts()[0], rig.counts()[2]) == (before[0], before[2])      # a declined request leaves one void row, no job
    assert forget_action(rig.w, "x")["ok"] is True
    again = rig.ask(verb, "x", person=FakePerson(True))
    assert again["sent"] is False and FORGOTTEN_WORDS in again["message"] and len(rig.jobs()) == before[0]


# ==== follow-up rulings F7 to F11 ========================================================================================================

def test_tc147_a_launch_whose_job_row_is_gone_may_be_forgotten(w):
    # TC-147 (F7)
    ann = w.user("ann")
    out = scn(w, ann, "run-one", index=False)
    sql_exec(w, "DELETE FROM jobs WHERE id = ?", (out["job_id"],))
    assert w.sql("SELECT COUNT(*) FROM jobs WHERE id = ?", (out["job_id"],))[0][0] == 0
    cid = out["id"]
    c0 = audit(conf(w, cid))
    res = actions().forget(w.ip.state_db, w.ip.index, "run-one", confirmed_by=actions().ELICITED, caller=ann)
    assert res["ok"] is True, res
    assert cleared(w, cid) and conf(w, cid)["forgotten_at"] is not None and audit(conf(w, cid)) == c0


def _failed_run(rig, duo, run):
    out = duo.sent(duo.a, run=run)
    rig.hand_over(out["job_id"], run)
    rig.set_run(run, "failed")


def test_tc132_tc133_forget_voids_the_waiting_resume_and_relaunch_of_that_run_only(rig):
    # TC-132, TC-133 (F10)
    from owner_harness import Duo
    duo = Duo(rig.w)
    _failed_run(rig, duo, "r-one")
    _failed_run(rig, duo, "r-two")
    r1 = rig.resume("r-one", caller=duo.a, person=None)
    r2 = rig.relaunch("r-one", caller=duo.a, person=None)
    keep = rig.resume("r-two", caller=duo.a, person=None)
    assert r1["state"] == r2["state"] == keep["state"] == "pending", (r1, r2, keep)
    res = actions().forget(rig.state, rig.index, "r-one", confirmed_by=actions().ELICITED, caller=duo.a)
    assert res["ok"] is True, res
    for rid in (r1["id"], r2["id"]):                                      # TC-132
        row = conf(rig.w, rid)
        assert row["state"] == "void" and row["bundle_json"] is None and row["screen_text"] is None
        assert row["forgotten_at"] is not None
    row = conf(rig.w, keep["id"])                                         # TC-133
    assert row["state"] == "pending" and row["bundle_json"] is not None and row["forgotten_at"] is None
    actions().approve(rig.state, keep["id"], confirmed_by=actions().PAGE, caller=duo.a)
    assert conf(rig.w, keep["id"])["state"] == "confirmed"


def test_tc114_the_kit_asks_for_five_tools():
    # TC-114 (F8); the old pin is test_tc137 in test_resume_entrypoints.py
    settings = json.loads((REPO_ROOT / "extensions" / "claude-code-kit" / "settings.json").read_text(encoding="utf-8"))
    ask = settings["permissions"]["ask"]
    assert sorted(ask) == sorted("mcp__abf-platform__" + t for t in ("launch", "cancel", "resume", "relaunch", "forget"))


def test_tc115_the_ledger_names_the_two_009e_tests_changed_in_their_setup_only():
    # TC-115 (F9)
    text = (SPEC / "ledger.md").read_text(encoding="utf-8")
    assert "test_resume_platform.py" in text and "TC-053/054" in text and "old_format" in text


def _terminal_cancel(data):
    from test_launch_cli import hand_over
    hand_over(data)
    p = Pty(cli_argv("cancel", "run-one"), data.env())
    assert p.wait_for("確定取消？(y/N)", 30), p.text()
    shown = p.text()
    p.send("y\n")
    p.finish(30)
    return shown


def test_tc162_tc163_tc164_a_terminal_cancel_keeps_its_content(data):
    # TC-162, TC-163, TC-164 (F11)
    from abf_platform import common, confirm
    shown = _terminal_cancel(data)
    c = cli_rows(data, "confirmations", "kind = 'cancel'")[0]
    assert c["state"] == "confirmed" and c["channel"] == "TERMINAL"
    b = json.loads(c["bundle_json"])
    assert b["run_name"] == "run-one" and common.bundle_sha256(b) == c["sha256"]
    assert c["screen_text"] and c["screen_text"].strip().splitlines()[0] in shown          # TC-162
    state = data.ip.state_db
    old = time.time() - 400 * DAY
    con = sqlite3.connect(str(state))
    con.execute("UPDATE confirmations SET created_at = ?, confirmed_at = ? WHERE id = ?", (old, old, c["id"]))
    con.execute("UPDATE jobs SET state = 'done', finished_at = ? WHERE confirmation_id = ?", (time.time() - 8 * DAY, c["id"]))
    con.commit()
    con.close()
    confirm.create_pending(state, "launch", "lab-a", {"run_name": "trigger", "n": time.time()}, "text", None)    # TC-163
    from test_launch_cli import hand_over
    hand_over(data, "run-two", slurm=4343)
    actions().cancel(state, "lab-a", dict(b, run_name="run-two", slurm_job_id=4343), confirmed_by=actions().TERMINAL)    # TC-164: a new job prunes the old
    assert cli_rows(data, "jobs", "confirmation_id = '%s'" % c["id"]) == []
    kept = cli_rows(data, "confirmations", "id = '%s'" % c["id"])[0]
    assert kept["bundle_json"] is not None and kept["screen_text"] is not None


def test_tc165_a_terminal_cancel_is_forgotten_with_its_run(rig):
    # TC-165 (F11)
    from abf_launch import build
    rig.first("run-one")
    ce, bundle, _row = build.prepare_cancel(rig.state, "run-one")
    cid, _jid = actions().cancel(rig.state, ce, bundle, confirmed_by=actions().TERMINAL)
    assert actions().keep_screen(rig.state, cid, "cancel screen") is True
    sql_exec(rig.w, "UPDATE jobs SET state = 'done', finished_at = ? WHERE kind = 'cancel_run'", (time.time(),))
    c0 = audit(conf(rig.w, cid))
    assert forget_action(rig.w, "run-one")["ok"] is True
    assert cleared(rig.w, cid) and audit(conf(rig.w, cid)) == c0 and conf(rig.w, cid)["forgotten_at"] is not None
