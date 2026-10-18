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
from launch_harness import Pty, cli_argv

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


def scn(w, ann, name="run-one", final="succeeded", index=True):
    """A run ann launched through a form (a confirmed row with content, a done launch job, a Slurm number), listed in the index."""
    out = w.launch(caller=ann, answer=form_answer(), run=name)
    assert out["sent"] is True, out
    sql_exec(w, "UPDATE launches SET slurm_job_id = 4242, submitted_at = confirmed_at WHERE run_name = ?", (name,))
    sql_exec(w, "UPDATE jobs SET state = 'done', finished_at = ? WHERE id = ?", (time.time(), out["job_id"]))
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


def test_tc016_a_terminal_confirmed_launch_has_only_its_job_copy_cleared(w):
    # TC-016
    ann = w.user("ann")
    now = time.time()
    import secrets
    cid = secrets.token_hex(16)
    bundle = {"version": 1, "run_name": "run-one", "run_folder": "/data/w1/runs/run-one", "agent": "agent-t"}
    sql_exec(w, "INSERT INTO confirmations (id, sha256, kind, created_at, state, channel, confirmed_at) "
                "VALUES (?, 'sha-t', 'launch', ?, 'confirmed', 'TERMINAL', ?)", (cid, now, now))
    sql_exec(w, "INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, finished_at, confirmation_id) "
                "VALUES ('agent-t', 'lab-a', 'launch_nextflow', ?, 'done', ?, ?, ?, ?)",
             (json.dumps({"bundle": bundle, "confirmation_id": cid}), now, now + 300, now, cid))
    jid = w.sql("SELECT id FROM jobs WHERE confirmation_id = ?", (cid,))[0]["id"]
    sql_exec(w, "INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, job_id, user_id) "
                "VALUES ('run-one', 4242, '/data/w1/runs/run-one', 'lab-a', 'agent-t', ?, ?, ?)", (now, jid, ann.user_id))
    add_index_run(w, "run-one")
    r = forget_action(w)
    assert r["ok"] is True, r
    assert job_cleared(w, jid, "run-one")
    assert conf(w, cid)["bundle_json"] is None and conf(w, cid)["forgotten_at"] is None


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
    assert "forget" in by and by["forget"].annotations.destructive_hint is True
    assert not (set(by["forget"].input_schema.get("properties", {})) - {"run_name"})
    for fname, needle in (("test_human_channel.py", '"cancel", "forget", "get_compute_env"'),
                          ("test_guidance.py", '"launch", "cancel", "forget"'),
                          ("test_actions_layer.py", 'WRITE_NAMES = ["launch", "cancel", "forget"]')):
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


def test_tc052_a_run_that_is_not_in_the_index_yet_is_still_starting(w):
    # TC-052
    ann = w.user("ann")
    scn(w, ann, index=False)
    before = tables(w)
    r = forget_tool(w, "run-one", ann, form_answer())
    assert r["ok"] is False and STARTING in r["message"]
    assert tables(w) == before


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


def test_tc062_the_ledger_names_the_hook_point_for_009e():
    # TC-062
    text = (SPEC / "ledger.md").read_text(encoding="utf-8")
    assert "009e" in text and "content deleted by its owner" in text and "內容已被擁有者刪除" in text
    assert "forgotten" in text and "args_json" in text


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


def test_tc074_every_automatic_test_case_is_named_in_a_comment_of_this_file():
    # TC-074
    src = open(__file__, encoding="utf-8").read()
    cases = (SPEC / "test-case.md").read_text(encoding="utf-8")
    ids = sorted(set(re.findall(r"^\| (TC-\d{3}) ", cases, re.M)))
    assert len(ids) == 63
    missing = [i for i in ids if not re.search(r"#[^\n]*\b%s\b" % i, src)]
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
    assert set(confirm.JOB_KIND) == {"launch", "cancel"}
    assert "CHECK (kind IN ('launch', 'cancel'))" in store.STATE_SCHEMA
    assert "forget" not in inspect.getsource(confirm.approve)


def test_tc084_no_resume_or_relaunch_code_came_in():
    # TC-084
    for p in (REPO_ROOT / "platform").rglob("*.py"):
        if "tests" in p.parts:
            continue
        assert not re.search(r"def\s+(resume|relaunch)", p.read_text(encoding="utf-8")), p


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


def test_tc093_the_contract_files_were_not_edited_after_the_contract_commit():
    # TC-093
    r = subprocess.run(["git", "-C", str(REPO_ROOT), "diff", "--name-only", "94554a4", "HEAD", "--", "specs/keep-submissions/plan.md",
                        "specs/keep-submissions/test-case.md", "specs/keep-submissions/test-case-overview.md"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""
