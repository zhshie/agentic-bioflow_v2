# Nothing existing: tests for the review findings of PR #115 (specs/009c-human-channel/ledger.md, "Fix round: code review"); the rules are ours.
"""009c fix round, one test per finding. Findings are numbered as in the review: 2 uploads, 3 login throttle, 4 session binding,
5 audit rows, 6 repeated calls, 7 web origin, 8 signing key, 9 pending cap and pruning, 10 reachable address."""
import asyncio
import json
import sqlite3

import pytest

from human_harness import World, csrf_of, form_answer
from helpers import tool_json
from test_human_channel import _approve_on_the_page


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def update(w, text, args=()):
    con = sqlite3.connect(str(w.ip.state_db))
    con.execute(text, args)
    con.commit()
    con.close()


# ---- finding 5: an audit row keeps that a person said yes ---------------------------------------------------------------------

def test_f5_a_queue_refusal_after_a_yes_keeps_the_channel_and_the_time_on_the_void_row(w):
    ann = w.user("ann")

    async def cb(context, params):
        from mcp_types import ElicitResult
        w.hand_over("run-one", slurm=None)
        return ElicitResult(action="accept", content={"送出": True})

    out = w.launch(caller=ann, answer=cb)
    assert out["sent"] is False and w.jobs() == []
    row = w.confirmations()[0]
    assert row["state"] == "void" and row["void_reason"]
    assert row["channel"] == "ELICITED" and row["confirmed_at"] is not None


def test_f5_the_same_on_the_page(w):
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c = w.web()
    w.login(c, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    w.hand_over("run-one", slurm=None)
    c.post("/c/" + rid, data={"csrf": token})
    row = w.confirmations()[0]
    assert row["state"] == "void" and row["channel"] == "PAGE" and row["confirmed_at"] is not None and w.jobs() == []


# ---- finding 6: a repeated call after the agent took the job ---------------------------------------------------------------------

def test_f6_after_the_agent_claimed_the_job_a_repeated_launch_still_returns_it(w):
    ann = w.user("ann")
    first = w.launch(caller=ann)
    _approve_on_the_page(w, "ann", first["id"])
    job_id = w.jobs()[0]["id"]
    update(w, "UPDATE confirmations SET used_at = ?", (w.confirmations()[0]["created_at"] + 1,))
    update(w, "UPDATE jobs SET state = 'claimed'")
    for _ in range(2):
        again = w.launch(caller=ann)
        assert again["sent"] is True and again["job_id"] == job_id
    assert len(w.confirmations()) == 1 and len(w.jobs("launch_nextflow")) == 1


def test_f6_a_confirmed_cancel_is_never_asked_for_twice(w):
    w.hand_over()
    ann, bob = w.user("ann"), w.user("bob")
    first = tool_json(w.call("cancel", {"run_name": "run-one"}, caller=ann, answer=form_answer()))
    assert first["sent"] is True and len(w.jobs("cancel_run")) == 1
    job_id = w.jobs("cancel_run")[0]["id"]
    update(w, "UPDATE confirmations SET used_at = created_at + 1")
    update(w, "UPDATE jobs SET state = 'claimed'")
    for who in (ann, bob):
        again = tool_json(w.call("cancel", {"run_name": "run-one"}, caller=who))
        assert again["sent"] is True and again["job_id"] == job_id
    assert len(w.confirmations()) == 1 and len(w.jobs("cancel_run")) == 1


# ---- finding 9: a cap on open requests, and old rows lose their content -----------------------------------------------------------------

def test_f9_a_caller_has_at_most_ten_open_requests(w):
    ann, bob = w.user("ann"), w.user("bob")
    for i in range(10):
        assert w.launch(caller=ann, run="run-%02d" % i)["sent"] is False
    over = w.launch(caller=ann, run="run-over")
    assert over["ok"] is False and over["sent"] is False and "10" in over["message"]
    assert len([r for r in w.confirmations() if r["caller_user_id"] == ann.user_id]) == 10
    again = w.launch(caller=ann, run="run-03")             # the same content as an open one is that open one, not a new request
    assert again["ok"] is True and again["id"]
    assert w.launch(caller=bob, run="run-over")["ok"] is True


def test_f9_expired_and_void_rows_lose_their_content_after_seven_days(w):
    ann = w.user("ann")
    w.launch(caller=ann, answer=form_answer("decline"), run="run-a")
    old_pending = w.launch(caller=ann, run="run-b")["id"]
    ok = w.launch(caller=ann, answer=form_answer(), run="run-c")
    assert ok["sent"] is True
    day = 86400
    update(w, "UPDATE confirmations SET created_at = created_at - ?, expires_at = expires_at - ? WHERE expires_at IS NOT NULL", (8 * day, 8 * day))
    update(w, "UPDATE confirmations SET created_at = created_at - ? WHERE expires_at IS NULL", (8 * day,))
    fresh = w.launch(caller=ann, run="run-d")["id"]
    rows = {r["id"]: r for r in w.confirmations()}
    for rid in (w.sql("SELECT id FROM confirmations WHERE state = 'void'")[0]["id"], old_pending):
        r = rows[rid]
        assert r["bundle_json"] is None and r["screen_text"] is None
        assert r["sha256"] and r["kind"] == "launch" and r["caller_user_id"] == ann.user_id and r["created_at"] and r["state"]
    assert rows[ok["id"]]["bundle_json"] is not None
    assert rows[fresh]["bundle_json"] is not None
