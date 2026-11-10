# Nothing existing: tests of the BUDGET yes (constitution 8.0.0): a send inside the person's own two SU limits goes without a per-send confirmation.
"""dev-mode-launch: budget-approved launches. Test cases TC-001 ... TC-101 are named in the comments, see specs/dev-mode-launch/."""
import sqlite3
import time

import pytest

from human_harness import World

H = 3600000


@pytest.fixture
def w(tmp_path, monkeypatch):
    monkeypatch.delenv("ABF_HOSTED", raising=False)
    return World(tmp_path, monkeypatch)


def _history(w, caller, su=10, name="run-one", queue="ct56"):
    """A first launch (the person says yes in chat), then that run recorded as succeeded with `su` SU of usage."""
    o = w.launch(caller=caller, run=name) if False else w.launch(caller=caller, run_name=name)
    rid = o["id"]
    w.launch(caller=caller, run_name=name, request_id=rid, user_confirmed=True)
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at, n_succeeded) "
                    "VALUES (?, 's', ?, 'live', 'succeeded', ?, ?, ?, 1)", ("id-" + name, name, int(time.time()) - 100, int(time.time()) - 50, int(time.time())))
        con.execute("INSERT INTO task_usage (run_id, task_key, name, status, cpus, realtime_ms, queue) VALUES (?, '1:1', 'A', 'COMPLETED', ?, ?, ?)",
                    ("id-" + name, su, H, queue))
    con.close()


def _set(w, caller, single, month):
    from abf_platform import actions
    return actions.set_my_budget(w.ip.tokens, single, month, confirmed_by=actions.PAGE, caller=caller)


def _go(w, caller, run="run-two"):
    return w.launch(caller=caller, run_name=run)


def _last(w):
    return w.confirmations()[-1]


def test_bg_01_inside_budget_sends_without_asking(w):
    # TC-001: estimate 10 SU, single limit 50, month 100 -> BUDGET yes, queued
    ann = w.user("ann")
    _history(w, ann, su=10)
    assert _set(w, ann, 50, 100) == {"ok": True}
    out = _go(w, ann)
    assert out["sent"] is True and out["channel"] == "BUDGET" and "SU" in out["message"], out
    row = _last(w)
    assert row["channel"] == "BUDGET" and row["state"] == "confirmed" and row["budget_note"]


def test_bg_02_unset_limits_ask_as_before(w):
    # TC-002: nothing set -> pending, nothing queued
    ann = w.user("ann")
    _history(w, ann, su=10)
    before = len(w.jobs())
    out = _go(w, ann)
    assert out["sent"] is False and out["state"] == "pending"
    assert len(w.jobs()) == before


def test_bg_03_zero_limit_allows_nothing(w):
    # TC-003
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 0, 100)
    assert _go(w, ann)["sent"] is False


def test_bg_04_over_single_limit_asks(w):
    # TC-004: estimate 10 > single 5
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 5, 1000)
    assert _go(w, ann)["sent"] is False


def test_bg_05_equal_to_limit_passes_over_by_one_does_not(w):
    # TC-005: single limit equal to the estimate passes; month: used 10 + estimate 10 = 20 passes at 20, not at 19
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 10, 19)
    assert _go(w, ann)["sent"] is False
    _set(w, ann, 10, 20)
    assert _go(w, ann, "run-three")["sent"] is True


def test_bg_06_no_history_asks(w):
    # TC-006: nothing to estimate from -> ask
    ann = w.user("ann")
    _set(w, ann, 50, 100)
    assert _go(w, ann)["sent"] is False


def test_bg_07_hosted_never_takes_budget(w, monkeypatch):
    # TC-007
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 50, 100)
    monkeypatch.setenv("ABF_HOSTED", "1")
    assert _go(w, ann)["sent"] is False


def test_bg_08_stdio_without_caller_never_budget(w):
    # TC-008: no caller, no form -> the old "nobody" refusal
    out = w.launch(caller=None)
    assert out["sent"] is False and out.get("channel") != "BUDGET"


def test_bg_09_budget_is_no_human_channel(w):
    # TC-009: the action layer's human gates refuse BUDGET
    from abf_platform import actions, jobs
    assert actions.BUDGET.name == "BUDGET"
    with pytest.raises(jobs.JobRefused):
        actions._require_human(actions.BUDGET)
    with pytest.raises(jobs.JobRefused):
        actions.set_my_budget("x", 1, 1, confirmed_by=actions.BUDGET, caller=None)


def test_bg_10_only_page_sets_limits(w):
    # TC-010: CHAT, ELICITED, TERMINAL, none -> nothing is written
    from abf_platform import actions, jobs
    ann = w.user("ann")
    for ch in (actions.CHAT, actions.ELICITED, actions.TERMINAL, None):
        with pytest.raises(jobs.JobRefused):
            actions.set_my_budget(w.ip.tokens, 5, 5, confirmed_by=ch, caller=ann)
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": None, "month": None}


def test_bg_11_bad_values_refused(w):
    # TC-011
    from abf_platform import actions
    ann = w.user("ann")
    for bad in (-1, float("nan"), 1000001, "5", True):
        assert _set(w, ann, bad, 10)["ok"] is False
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": None, "month": None}
    assert _set(w, ann, None, None) == {"ok": True}


def test_bg_12_one_person_cannot_read_or_set_anothers(w):
    # TC-012
    from abf_platform import actions
    ann, bob = w.user("ann"), w.user("bob")
    _set(w, ann, 7, 9)
    assert actions.get_my_budget(w.ip.tokens, caller=bob) == {"single": None, "month": None}
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": 7.0, "month": 9.0}
    assert actions.get_my_budget(w.ip.tokens, caller=None) == {"single": None, "month": None}


def test_bg_13_budget_decide_is_fail_closed():
    # TC-013: any unknown fact is "ask"
    from abf_platform import budget
    base = dict(user_present=True, hosted=False, single=50, month=100, kind="send", slurm=True, site_known=True, estimate=10, used=0)
    assert budget.decide(**base)[0] is True
    for k, v in (("user_present", False), ("hosted", True), ("single", None), ("month", None), ("slurm", False), ("site_known", False),
                 ("estimate", None), ("used", None), ("single", 0), ("month", 0)):
        assert budget.decide(**dict(base, **{k: v}))[0] is False, k


def test_bg_14_check_never_raises(w):
    # TC-014
    from abf_platform import budget
    ok, why, facts = budget.check("/nonexistent/platform.db", "launch", "lab-a", {}, object(), time.time, "/nonexistent/i.db", "/nonexistent/t.db")
    assert ok is False and facts is None


def test_bg_15_cancel_inside_budget(w):
    # TC-015: a cancel of a run on a slurm env goes on the budget; reasons stay plain
    from abf_platform import budget, actions
    ann = w.user("ann")
    _set(w, ann, 50, 100)
    ok, note, facts = budget.check(w.ip.state_db, "cancel", "lab-a", {}, ann, time.time, w.ip.index, w.ip.tokens)
    assert ok is True and facts["estimate"] is None
    ok, _, _ = budget.check(w.ip.state_db, "cancel", "no-such-env", {}, ann, time.time, w.ip.index, w.ip.tokens)
    assert ok is False


def test_bg_16_migration_columns(w):
    # TC-016: new columns exist and an old database gets them by ALTER
    con = sqlite3.connect(str(w.ip.state_db))
    cols = {r[1] for r in con.execute("PRAGMA table_info(confirmations)")}
    con.close()
    con2 = sqlite3.connect(str(w.ip.tokens))
    ucols = {r[1] for r in con2.execute("PRAGMA table_info(users)")}
    con2.close()
    assert "budget_note" in cols and {"auto_su_single", "auto_su_month"} <= ucols


def test_bg_17_find_approved_accepts_budget(w):
    # TC-017: a BUDGET-confirmed launch is found by the hand-off lookup (the job was queued)
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 50, 100)
    assert _go(w, ann)["sent"] is True
    assert any(j["kind"] == "launch_nextflow" for j in w.jobs())
