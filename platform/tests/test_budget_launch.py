# Nothing existing: tests of the BUDGET yes (constitution 8.0.0): a send inside the person's own two SU limits goes without a per-send confirmation.
"""dev-mode-launch: budget-approved launches. Test cases TC-001 ... TC-101 are named in the comments, see specs/dev-mode-launch/."""
import json
import re
import sqlite3
import time

import pytest

from human_harness import World

H = 3600000


@pytest.fixture
def w(tmp_path, monkeypatch):
    monkeypatch.delenv("ABF_HOSTED", raising=False)
    return World(tmp_path, monkeypatch)


def _history(w, caller, su=10, name="run-one", queue="ct56", status="succeeded", started=None):
    """A first launch (the person says yes in chat), then that run recorded with this end (succeeded unless said) and `su` SU of usage;
    `started` (seconds since the epoch) is when it started, a moment ago when not given."""
    o = w.launch(caller=caller, run=name) if False else w.launch(caller=caller, run_name=name)
    rid = o["id"]
    w.launch(caller=caller, run_name=name, request_id=rid, user_confirmed=True)
    from abf_platform import store
    t0 = int(time.time()) - 100 if started is None else int(started)
    con = store.connect_index(w.ip.index)
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at, n_succeeded) "
                    "VALUES (?, 's', ?, 'live', ?, ?, ?, ?, 1)", ("id-" + name, name, status, t0, t0 + 50, int(time.time())))
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
    # TC-005 (short form; test_bg_27 checks every field): estimate 10 SU, single limit 50, month 100 -> BUDGET yes, queued
    ann = w.user("ann")
    _history(w, ann, su=10)
    assert _set(w, ann, 50, 100) == {"ok": True}
    out = _go(w, ann)
    assert out["sent"] is True and out["channel"] == "BUDGET" and "SU" in out["message"], out
    row = _last(w)
    assert row["channel"] == "BUDGET" and row["state"] == "confirmed" and row["budget_note"]


def test_bg_02_unset_limits_ask_as_before(w):
    # TC-001: nothing set -> pending, nothing queued (test_bg_25 asks all four kinds)
    ann = w.user("ann")
    _history(w, ann, su=10)
    before = len(w.jobs())
    out = _go(w, ann)
    assert out["sent"] is False and out["state"] == "pending"
    assert len(w.jobs()) == before


def test_bg_03_zero_limit_allows_nothing(w):
    # TC-020: a limit of 0 allows nothing
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 0, 100)
    assert _go(w, ann)["sent"] is False


def test_bg_04_over_single_limit_asks(w):
    # TC-011: the estimate is over the single limit (10 > 5)
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 5, 1000)
    assert _go(w, ann)["sent"] is False


def test_bg_05_equal_to_limit_passes_over_by_one_does_not(w):
    # TC-013, TC-014: single limit equal to the estimate passes; month: used 10 + estimate 10 = 20 passes at 20, not at 19
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 10, 19)
    assert _go(w, ann)["sent"] is False
    _set(w, ann, 10, 20)
    assert _go(w, ann, "run-three")["sent"] is True


def test_bg_06_no_history_asks(w):
    # TC-015: nothing to estimate from -> ask
    ann = w.user("ann")
    _set(w, ann, 50, 100)
    assert _go(w, ann)["sent"] is False


def test_bg_07_hosted_never_takes_budget(w, monkeypatch):
    # TC-039
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 50, 100)
    monkeypatch.setenv("ABF_HOSTED", "1")
    assert _go(w, ann)["sent"] is False


def test_bg_08_stdio_without_caller_never_budget(w):
    # TC-027: no caller, no form -> the old "nobody" refusal, for a launch and for a cancel
    out = w.launch(caller=None)
    assert out["sent"] is False and out.get("channel") != "BUDGET"
    w.hand_over("run-one")
    from helpers import tool_json
    out = tool_json(w.call("cancel", {"run_name": "run-one"}, caller=None))
    assert out["sent"] is False and out.get("channel") != "BUDGET"
    assert not [c for c in w.sql("SELECT channel FROM confirmations") if c["channel"] == "BUDGET"]


def test_bg_09_budget_is_no_human_channel(w):
    # TC-101, TC-044: the action layer's human gates refuse BUDGET
    from abf_platform import actions, jobs
    assert actions.BUDGET.name == "BUDGET"
    with pytest.raises(jobs.JobRefused):
        actions._require_human(actions.BUDGET)
    with pytest.raises(jobs.JobRefused):
        actions.set_my_budget("x", 1, 1, confirmed_by=actions.BUDGET, caller=None)


def test_bg_10_only_page_sets_limits(w):
    # TC-043, TC-044: CHAT, ELICITED, TERMINAL, none -> nothing is written
    from abf_platform import actions, jobs
    ann = w.user("ann")
    for ch in (actions.CHAT, actions.ELICITED, actions.TERMINAL, None):
        with pytest.raises(jobs.JobRefused):
            actions.set_my_budget(w.ip.tokens, 5, 5, confirmed_by=ch, caller=ann)
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": None, "month": None}


def test_bg_11_bad_values_refused(w):
    # TC-045, TC-046, TC-047, TC-049
    from abf_platform import actions
    ann = w.user("ann")
    for bad in (-1, float("nan"), 1000001, "5", True):
        assert _set(w, ann, bad, 10)["ok"] is False
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": None, "month": None}
    assert _set(w, ann, None, None) == {"ok": True}


def test_bg_12_one_person_cannot_read_or_set_anothers(w):
    # TC-051
    from abf_platform import actions
    ann, bob = w.user("ann"), w.user("bob")
    _set(w, ann, 7, 9)
    assert actions.get_my_budget(w.ip.tokens, caller=bob) == {"single": None, "month": None}
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": 7.0, "month": 9.0}
    assert actions.get_my_budget(w.ip.tokens, caller=None) == {"single": None, "month": None}


def test_bg_13_budget_decide_is_fail_closed():
    # TC-016, TC-020, TC-021: any unknown fact is "ask"; a limit of 0 allows nothing, an estimate of 0 included
    from abf_platform import budget
    base = dict(user_present=True, hosted=False, single=50, month=100, kind="send", slurm=True, site_known=True, estimate=10, used=0)
    assert budget.decide(**base)[0] is True
    for k, v in (("user_present", False), ("hosted", True), ("single", None), ("month", None), ("slurm", False), ("site_known", False),
                 ("estimate", None), ("used", None), ("single", 0), ("month", 0)):
        assert budget.decide(**dict(base, **{k: v}))[0] is False, k
    for single, month in ((0, 100), (20, 0)):
        assert budget.decide(**dict(base, single=single, month=month, estimate=0, used=0))[0] is False
        assert budget.decide(**dict(base, single=single, month=month, kind="cancel"))[0] is False      # TC-022


def test_bg_14_check_never_raises(w):
    # TC-019: a database that cannot be read is "ask", never an error
    from abf_platform import budget
    ok, why, facts = budget.check("/nonexistent/platform.db", "launch", "lab-a", {}, object(), time.time, "/nonexistent/i.db", "/nonexistent/t.db")
    assert ok is False and facts is None


def test_bg_15_cancel_inside_budget(w):
    # TC-009, TC-033: a cancel of a run on a slurm env goes on the budget; an environment that cannot be found is asked
    from abf_platform import budget, actions
    ann = w.user("ann")
    _set(w, ann, 50, 100)
    ok, note, facts = budget.check(w.ip.state_db, "cancel", "lab-a", {}, ann, time.time, w.ip.index, w.ip.tokens)
    assert ok is True and facts["estimate"] is None
    ok, _, _ = budget.check(w.ip.state_db, "cancel", "no-such-env", {}, ann, time.time, w.ip.index, w.ip.tokens)
    assert ok is False


def test_bg_16_migration_columns(w):
    # TC-060: the three new columns exist
    con = sqlite3.connect(str(w.ip.state_db))
    cols = {r[1] for r in con.execute("PRAGMA table_info(confirmations)")}
    con.close()
    con2 = sqlite3.connect(str(w.ip.tokens))
    ucols = {r[1] for r in con2.execute("PRAGMA table_info(users)")}
    con2.close()
    assert "budget_note" in cols and {"auto_su_single", "auto_su_month"} <= ucols


def test_bg_17_find_approved_accepts_budget(w):
    # TC-005: a BUDGET-confirmed launch is found by the hand-off lookup (the job was queued)
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 50, 100)
    assert _go(w, ann)["sent"] is True
    assert any(j["kind"] == "launch_nextflow" for j in w.jobs())


def test_bg_18_cloud_env_never_budget(w):
    # TC-029, TC-030, TC-032: a cloud target is asked every time, whatever the numbers
    from abf_platform import budget
    ann = w.user("ann")
    _history(w, ann, su=1)
    _set(w, ann, 1000000, 1000000)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET platform = 'googlebatch-platform' WHERE name = 'lab-a'")
    con.close()
    for kind in ("launch", "cancel"):
        assert budget.check(w.ip.state_db, kind, "lab-a", {"pipeline": "nf-core/ampliseq"}, ann, time.time, w.ip.index, w.ip.tokens)[0] is False
    assert not [c for c in w.confirmations() if c["channel"] == "BUDGET"]


def test_bg_19_forget_and_direct_budget_refused(w):
    # TC-036, TC-037, TC-038: BUDGET fed straight to launch, cancel or forget is refused
    from abf_platform import actions, jobs
    ann = w.user("ann")
    _set(w, ann, 50, 100)
    for call in (lambda: actions.launch(w.ip.state_db, "lab-a", {}, confirmed_by=actions.BUDGET, caller=ann),
                 lambda: actions.cancel(w.ip.state_db, "lab-a", {}, confirmed_by=actions.BUDGET, caller=ann),
                 lambda: actions.forget(w.ip.state_db, w.ip.index, "run-one", confirmed_by=actions.BUDGET, caller=ann)):
        with pytest.raises(jobs.JobRefused) as e:
            call()
        assert "no human confirmation channel" in str(e.value)
    assert w.jobs() == []


def test_bg_20_settings_page_saves_limits_and_shows_them(w, monkeypatch):
    # TC-042, TC-055, TC-057: the page shows "unset", saves with the right csrf only, and shows the numbers
    from abf_platform import actions
    from human_harness import csrf_of
    ann = w.user("ann")
    c = w.web()
    assert w.login(c, "ann").status_code in (302, 303)
    html = c.get("/settings").text
    assert "/settings/budget" in html and "未設定＝每次都問你" in html
    from abf_platform import web_settings
    assert "每次都問你" not in repr(web_settings.STRINGS)      # the words live in web_devmode's table, so test_ce08's digest stands
    token = re.search(r'action="/settings/budget">.*?name="csrf" value="([^"]+)"', html, re.S).group(1)
    r = c.post("/settings/budget", data={"csrf": "bad", "single": "20", "month": "100", "lang": "zh"})
    assert r.status_code == 400 and actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": None, "month": None}
    r = c.post("/settings/budget", data={"csrf": token, "single": "20", "month": "100", "lang": "zh"}, headers={"origin": "http://testserver"})
    assert r.status_code in (302, 303), r.text[:300]
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": 20.0, "month": 100.0}
    html = c.get("/settings").text
    assert 'value="20"' in html and 'value="100"' in html and "未設定＝每次都問你" not in html


def test_bg_21_hosted_page_says_not_enabled(w, monkeypatch):
    # TC-041
    w.user("ann")
    c = w.web()
    w.login(c, "ann")
    assert "此部署不啟用" not in c.get("/settings").text
    monkeypatch.setenv("ABF_HOSTED", "1")
    html = c.get("/settings").text
    assert "/settings/budget" not in html and "此部署不啟用" in html


def test_bg_22_auto_send_list(w, monkeypatch, capsys):
    # TC-063, TC-064, TC-066, TC-067: the daily-summary list, read only
    from abf_platform import cli
    ann = w.user("ann")
    monkeypatch.setenv("ABF_PLATFORM_STATE", str(w.ip.state_db))
    monkeypatch.setenv("ABF_INDEX", str(w.ip.index))
    monkeypatch.setattr("abf_platform.store.default_tokens_path", lambda *a, **k: w.ip.tokens)
    monkeypatch.setattr("abf_platform.store.default_index_path", lambda *a, **k: w.ip.index)
    assert cli.main(["auto-send", "list"]) == 0
    assert "no budget-approved sends" in capsys.readouterr().out
    _history(w, ann, su=10)
    _set(w, ann, 50, 100)
    assert _go(w, ann)["sent"] is True
    before = w.sql("SELECT * FROM confirmations")
    assert cli.main(["auto-send", "list"]) == 0
    line = [l for l in capsys.readouterr().out.splitlines() if "\t" in l]
    assert len(line) == 1
    cols = line[0].split("\t")
    assert len(cols) == 6 and cols[1] == "ann" and cols[2] == "launch" and cols[3] == "run-two" and "estimate 10" in cols[5]
    assert cli.main(["auto-send", "list", "--since", "2999-01-01"]) == 0
    assert "no budget-approved sends" in capsys.readouterr().out
    assert [tuple(r) for r in w.sql("SELECT * FROM confirmations")] == [tuple(r) for r in before]


def test_bg_23_only_the_page_route_calls_the_setters():
    # TC-052, TC-054, TC-093: who may call the setter and who may record BUDGET
    import ast
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / "abf_platform"
    callers = {"set_my_budget": set(), "set_user_budget": set()}
    approvers = set()
    for p in root.rglob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for n in ast.walk(fn):
                if isinstance(n, ast.Call):
                    name = getattr(n.func, "attr", getattr(n.func, "id", ""))
                    if name in callers:
                        callers[name].add((p.name, fn.name))
                    if name == "approve" and any(isinstance(a, ast.Attribute) and a.attr == "name" and getattr(a.value, "id", "") == "BUDGET" for a in n.args):
                        approvers.add((p.name, fn.name))
    assert {f for f, _ in callers["set_my_budget"]} <= {"web.py", "__init__.py"}, callers
    assert {f for f, _ in callers["set_user_budget"]} <= {"__init__.py"}, callers
    assert {fn for _, fn in approvers} <= {"_ask", "_request_attempt"}, approvers
    for forbidden in ("request_forget", "forget", "clean_work", "request_clean_work"):
        assert forbidden not in {fn for _, fn in approvers}


def test_bg_24_old_database_gets_the_new_columns(w):
    # TC-060, TC-061: columns added by ALTER on an old database; opening twice is fine
    from abf_platform import store
    con = sqlite3.connect(str(w.ip.tokens))
    con.execute("ALTER TABLE users DROP COLUMN auto_su_single")
    con.commit()
    con.close()
    store.connect_tokens(str(w.ip.tokens)).close()
    store.connect_tokens(str(w.ip.tokens)).close()
    con = sqlite3.connect(str(w.ip.tokens))
    assert "auto_su_single" in {r[1] for r in con.execute("PRAGMA table_info(users)")}
    con.close()


# ---- the cases of specs/dev-mode-launch/test-case.md that the tests above do not reach -------------------------------------------------

def _budget_rows(w):
    return [c for c in w.sql("SELECT * FROM confirmations ORDER BY created_at, id") if c["channel"] == "BUDGET"]


def _is_pending(out):
    return out["sent"] is False and out.get("state") == "pending" and out.get("channel") != "BUDGET"


def _plain(out):
    """What an AI or a person is told holds no stack, inner path or SQL."""
    text = json.dumps(out, ensure_ascii=False)
    return not any(bad in text for bad in ("Traceback", "abf_platform/", ".py\"", "SELECT ", "sqlite3", "OperationalError"))


def _tasks(w, name, su, queue="ct56"):
    """`su` SU of use for a run that is already in the index."""
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    with con:
        con.execute("INSERT INTO task_usage (run_id, task_key, name, status, cpus, realtime_ms, queue) VALUES (?, '1:1', 'A', 'COMPLETED', ?, ?, ?)",
                    ("id-" + name, su, H, queue))
    con.close()


@pytest.fixture
def r(tmp_path, monkeypatch):
    from resume_harness import Rig
    monkeypatch.delenv("ABF_HOSTED", raising=False)
    return Rig(tmp_path, monkeypatch)


def _scene(r):
    """ann, with what TC-005 names: a succeeded run of the pipeline that used 10 SU, 40 SU more used this month by two failed runs (so 50
    used), and a run that is still going. Returns ann."""
    ann = r.user("ann")
    r.first("run-hist", caller=ann, status="succeeded")
    _tasks(r.w, "run-hist", 10)
    for name, su in (("run-f1", 15), ("run-f2", 15)):
        r.first(name, caller=ann, status="failed")
        _tasks(r.w, name, su)
    r.first("run-live", caller=ann, status=None)
    _tasks(r.w, "run-live", 10)
    return ann


def _four(r, ann):
    """A launch, a resume, a relaunch and a cancel, asked the way an AI asks them (no form, nobody presses anything)."""
    from helpers import tool_json
    return {"launch": r.w.launch(caller=ann, run_name="run-new"),
            "resume": r.resume("run-f1", caller=ann),
            "relaunch": r.relaunch("run-f2", caller=ann),
            "cancel": tool_json(r.w.call("cancel", {"run_name": "run-live"}, caller=ann))}


@pytest.mark.parametrize("dev_mode", [False, True])
def test_bg_25_unset_limits_ask_for_all_four_as_before(r, dev_mode):
    # TC-001, TC-002, TC-073: no limit set -> all four wait for the person, nothing is queued, the rows are plain pending rows;
    # users.dev_mode (012a's personal switch) turned on gives nothing
    ann = _scene(r)
    if dev_mode:
        con = sqlite3.connect(str(r.w.ip.tokens))
        with con:
            con.execute("UPDATE users SET dev_mode = 1 WHERE id = ?", (ann.user_id,))
        con.close()
    jobs_before = [tuple(j) for j in r.w.sql("SELECT * FROM jobs ORDER BY id")]
    rows_before = {c["id"] for c in r.confirmations()}
    outs = _four(r, ann)
    for kind, out in outs.items():
        assert _is_pending(out), (kind, out)
    assert [tuple(j) for j in r.w.sql("SELECT * FROM jobs ORDER BY id")] == jobs_before
    new = [c for c in r.confirmations() if c["id"] not in rows_before]
    assert len(new) == 4 and not _budget_rows(r.w)
    for c in new:
        assert c["state"] == "pending" and c["channel"] is None and c["confirmed_at"] is None and c["budget_note"] is None


@pytest.mark.parametrize("single,month,hosted", [(20, None, False), (None, 100, False), (0, 100, False), (20, 0, False), (20, 100, True)])
def test_bg_26_one_limit_a_zero_limit_or_a_hosted_deployment_asks_for_all_four(r, monkeypatch, single, month, hosted):
    # TC-003, TC-004 (one limit only), TC-022, TC-092 (a 0 limit, cancel included; no third switch), TC-039, TC-040 (ABF_HOSTED)
    ann = _scene(r)
    assert _set(r.w, ann, single, month) == {"ok": True}
    if hosted:
        monkeypatch.setenv("ABF_HOSTED", "1")
    n = len(r.w.sql("SELECT id FROM jobs"))
    for kind, out in _four(r, ann).items():
        assert _is_pending(out), (kind, out)
    assert len(r.w.sql("SELECT id FROM jobs")) == n and not _budget_rows(r.w)


def test_bg_27_launch_inside_budget_every_field(w):
    # TC-005, TC-010, TC-008, TC-076: single 20, month 100, estimate 10, used 50
    from human_harness import PASSWORD, form_answer
    from abf_platform import store
    ann = w.user("ann")
    token = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id, label="t")
    token = token if isinstance(token, str) else token[0]
    _history(w, ann, su=10)
    _history(w, ann, su=40, name="run-bad", status="failed")
    by_form = w.launch(caller=ann, answer=form_answer(), run_name="run-form")
    assert by_form["sent"] is True
    assert _set(w, ann, 20, 100) == {"ok": True}
    n_jobs = len(w.jobs())
    out = _go(w, ann)
    assert out["sent"] is True and out["channel"] == "BUDGET" and out["job_id"], out
    assert set(out) - {"channel"} == set(by_form) - {"channel"}
    assert "在你設定的 SU 額度內，已直接送出。預估 10 SU，你的單次上限 20、本月已用 50／上限 100" in out["message"]
    rows = _budget_rows(w)
    assert len(rows) == 1 and len(w.jobs()) == n_jobs + 1
    row = rows[0]
    assert row["state"] == "confirmed" and row["confirmed_at"] is not None and row["caller_user_id"] == ann.user_id and row["kind"] == "launch"
    for piece in ("estimate 10 SU", "single limit 20", "used this month 50", "monthly limit 100"):
        assert piece in row["budget_note"], row["budget_note"]
    again = _go(w, ann)                                   # TC-008: the same request once more is the same job
    assert again["job_id"] == out["job_id"] and len(_budget_rows(w)) == 1 and len(w.jobs()) == n_jobs + 1
    for text in (json.dumps(out, ensure_ascii=False), row["budget_note"]):      # TC-076
        assert token not in text and PASSWORD not in text


@pytest.mark.parametrize("verb,run", [("resume", "run-f1"), ("relaunch", "run-f2")])
def test_bg_28_resume_and_relaunch_inside_budget(r, verb, run):
    # TC-006, TC-007: the same result as TC-005 for a resume and for a relaunch
    ann = _scene(r)
    assert _set(r.w, ann, 20, 100) == {"ok": True}
    out = r.ask(verb, run, caller=ann)
    assert out["sent"] is True and out["channel"] == "BUDGET" and out["job_id"], out
    assert "預估 10 SU，你的單次上限 20、本月已用 50／上限 100" in out["message"]
    rows = _budget_rows(r.w)
    assert len(rows) == 1
    row = rows[0]
    assert row["state"] == "confirmed" and row["confirmed_at"] is not None and row["caller_user_id"] == ann.user_id
    for piece in ("estimate 10 SU", "single limit 20", "monthly limit 100"):
        assert piece in row["budget_note"], row["budget_note"]


def test_bg_29_cancel_inside_budget_and_owner_rule(r):
    # TC-009: both limits set -> the cancel of the person's own run is recorded as BUDGET; TC-058, TC-059: another person, with a
    # budget of their own, cannot cancel or resume it
    from helpers import tool_json
    ann, bob = _scene(r), r.user("bob")
    assert _set(r.w, ann, 20, 100) == {"ok": True} and _set(r.w, bob, 20, 100) == {"ok": True}
    n = len(r.w.sql("SELECT id FROM jobs"))
    out = tool_json(r.w.call("cancel", {"run_name": "run-live"}, caller=bob))
    assert out["sent"] is False and out.get("state") != "pending" and _plain(out), out
    out = r.resume("run-f1", caller=bob)
    assert out["sent"] is False and out.get("state") != "pending" and _plain(out), out
    assert not _budget_rows(r.w) and len(r.w.sql("SELECT id FROM jobs")) == n
    out = tool_json(r.w.call("cancel", {"run_name": "run-live"}, caller=ann))
    assert out["sent"] is True and out["channel"] == "BUDGET", out
    row = _budget_rows(r.w)[0]
    assert row["kind"] == "cancel" and row["confirmed_at"] is not None and row["caller_user_id"] == ann.user_id
    assert r.w.sql("SELECT 1 FROM jobs WHERE kind = 'cancel_run'")


@pytest.mark.parametrize("estimate,more_used,inside", [(30, 0, False), (10, 85, False), (10, 80, True), (10, 81, False)])
def test_bg_30_over_a_limit_asks_and_says_what_to_do(w, estimate, more_used, inside):
    # TC-011 (estimate 30 over single 20), TC-012 (used 95), TC-014 (90 + 10 = 100 is inside; one more is not), TC-074 (the answer says
    # the person must still say yes and how, with no stack, path or SQL)
    ann = w.user("ann")
    _history(w, ann, su=estimate)
    if more_used:
        _history(w, ann, su=more_used, name="run-bad", status="failed")
    _set(w, ann, 20, 100)
    out = _go(w, ann)
    if inside:
        assert out["sent"] is True and out["channel"] == "BUDGET", out
    else:
        assert _is_pending(out) and not _budget_rows(w) and not w.jobs("launch_nextflow")[2 if more_used else 1:], out
        assert "按「送出」" in out["message"] and out["confirmation_url"] in out["message"] and _plain(out)


def test_bg_31_estimate_equal_to_the_single_limit_with_nothing_used_is_inside(w):
    # TC-013: estimate exactly 20, nothing used this month (the history run is from an earlier month)
    ann = w.user("ann")
    _history(w, ann, su=20, started=time.time() - 70 * 86400)
    _set(w, ann, 20, 100)
    out = _go(w, ann)
    assert out["sent"] is True and out["channel"] == "BUDGET", out
    assert "預估 20 SU，你的單次上限 20、本月已用 0／上限 100" in out["message"]


def _breaks(case, monkeypatch, tmp_path):
    from abf_platform import store, su
    if case == "month unknown":                  # TC-016
        monkeypatch.setattr(su, "month_used_at", lambda *a, **k: None)
    elif case == "su raises":                    # TC-017
        def boom(*a, **k):
            raise RuntimeError("boom at /srv/secret/place")
        monkeypatch.setattr(su, "estimate_launch", boom)
    elif case == "no rates file":                # TC-018
        monkeypatch.setattr(su, "RATES_PATH", tmp_path / "no" / "su_rates.json")
    elif case == "database raises":              # TC-019
        def broken(*a, **k):
            raise sqlite3.OperationalError("disk I/O error")
        monkeypatch.setattr(store, "user_budget", broken)


@pytest.mark.parametrize("case", ["month unknown", "su raises", "no rates file", "database raises"])
def test_bg_32_what_cannot_be_worked_out_asks(w, monkeypatch, tmp_path, case):
    # TC-016, TC-017, TC-018, TC-019, TC-074: fail closed; the person is asked, nothing of the fault is said
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 20, 100)
    n = len(w.jobs())
    _breaks(case, monkeypatch, tmp_path)
    out = _go(w, ann)
    assert _is_pending(out) and len(w.jobs()) == n and not _budget_rows(w), out
    text = json.dumps(out, ensure_ascii=False)
    assert _plain(out) and "boom" not in text and "/srv/secret" not in text and "disk I/O" not in text and "su_rates" not in text
    assert "按「送出」" in out["message"]


def test_bg_33_estimate_is_the_largest_succeeded_run_of_this_pipeline_on_this_site(w):
    # TC-023: succeeded 8, 10, 15 and a failed 50 -> 15; TC-024: another pipeline or another site has no history -> ask
    from abf_platform import budget, compute_envs, su
    ann = w.user("ann")
    for name, n, end in (("h8", 8, "succeeded"), ("h10", 10, "succeeded"), ("h15", 15, "succeeded"), ("h50", 50, "failed")):
        _history(w, ann, su=n, name=name, status=end)
    rates = su.load_rates()
    site = compute_envs.get(w.ip.state_db, "lab-a")["config"].get("suSite") or rates["default_site"]
    assert su.estimate_launch(w.ip.index, w.ip.state_db, ann.user_id, "nf-core/ampliseq", site, rates)["su"] == 15
    assert su.estimate_launch(w.ip.index, w.ip.state_db, ann.user_id, "nf-core/rnaseq", site, rates)["su"] is None
    other = [s for s in rates["sites"] if s != site]
    for s in other[:1]:
        assert su.estimate_launch(w.ip.index, w.ip.state_db, ann.user_id, "nf-core/ampliseq", s, rates)["su"] is None
    _set(w, ann, 20, 1000)
    ok, why, _ = budget.check(w.ip.state_db, "launch", "lab-a", {"pipeline": "nf-core/rnaseq"}, ann, time.time, w.ip.index, w.ip.tokens)
    assert ok is False and why
    out = _go(w, ann)
    assert out["sent"] is True and "estimate 15 SU" in _budget_rows(w)[0]["budget_note"]


def test_bg_34_the_month_is_the_taipei_month_and_only_my_own_use(w):
    # TC-025: 90 SU used on the last day of last month (Taipei) is not this month's; the same use inside this month is, and 90 + 10 = 100
    # still passes while 99 does not. TC-026: another person's use is not mine
    import calendar
    from abf_platform import budget
    ann, bob = w.user("ann"), w.user("bob")
    last_night = calendar.timegm((2026, 10, 31, 15, 30, 0))      # 23:30 on 31 October in Taipei
    first_morning = calendar.timegm((2026, 10, 31, 16, 30, 0))   # 00:30 on 1 November in Taipei (still October in UTC)
    _history(w, ann, su=10, started=calendar.timegm((2026, 9, 1, 0, 0, 0)))
    _history(w, ann, su=90, name="run-big", status="failed", started=last_night)
    _history(w, bob, su=95, name="run-bob", started=first_morning - 600)
    _set(w, ann, 20, 100)
    _set(w, bob, 100, 100)

    def check(month=None):
        if month is not None:
            _set(w, ann, 20, month)
        return budget.check(w.ip.state_db, "launch", "lab-a", {"pipeline": "nf-core/ampliseq"}, ann, lambda: first_morning, w.ip.index, w.ip.tokens)
    ok, _, facts = check()
    assert ok is True and facts["used"] == 0 and facts["estimate"] == 10
    from abf_platform import store
    con = store.connect_index(w.ip.index)
    with con:
        con.execute("UPDATE runs SET started_at = ? WHERE run_name = 'run-big'", (first_morning - 1200,))      # 00:10 on 1 November in Taipei
    con.close()
    ok, _, facts = check()
    assert ok is True and facts["used"] == 90
    assert check(99)[0] is False


def test_bg_35_another_persons_use_does_not_count_at_launch(w):
    # TC-026 through the tool: bob used 95 this month, ann 10; ann's launch with month 100 goes through
    ann, bob = w.user("ann"), w.user("bob")
    _history(w, ann, su=10)
    _history(w, bob, su=95, name="run-bob")
    _set(w, ann, 20, 100)
    _set(w, bob, 20, 100)
    out = _go(w, ann)
    assert out["sent"] is True and out["channel"] == "BUDGET" and "本月已用 10／上限 100" in out["message"], out


def test_bg_36_not_a_slurm_site_and_not_cloud_asks(w):
    # TC-028, TC-030, TC-032: resume and relaunch are checked as a launch; an environment that is neither Slurm nor a cloud one, or a
    # cloud one, never gets a budget yes for any kind
    import inspect
    from abf_platform import actions, budget
    ann = w.user("ann")
    _history(w, ann, su=1)
    _set(w, ann, 1000000, 1000000)
    assert budget.check(w.ip.state_db, "launch", "lab-a", {"pipeline": "nf-core/ampliseq"}, ann, time.time, w.ip.index, w.ip.tokens)[0] is True
    for platform in ("some-other-platform", "googlebatch-platform"):
        con = sqlite3.connect(str(w.ip.state_db))
        with con:
            con.execute("UPDATE compute_envs SET platform = ? WHERE name = 'lab-a'", (platform,))
        con.close()
        for kind in ("launch", "cancel"):
            assert budget.check(w.ip.state_db, kind, "lab-a", {"pipeline": "nf-core/ampliseq"}, ann, time.time, w.ip.index, w.ip.tokens)[0] is False
    assert 'await _ask(platform_path, "launch"' in inspect.getsource(actions._request_attempt)


def test_bg_37_cloud_check_stays_first_and_untouched():
    # TC-031: the cloud money check runs before the request (and so before the budget) and knows nothing of the budget
    import inspect
    from abf_platform import actions
    assert "budget" not in inspect.getsource(actions._cloud_check).lower()
    src = inspect.getsource(actions)
    i = src.index("problem, cost = _cloud_check(")
    j = src.index('await _ask(platform_path, "launch"', i)
    assert "\ndef " not in src[i:j] and "\nasync def " not in src[i:j]      # the same function: the cloud check comes first


def test_bg_38_forget_and_clean_work_still_ask(w):
    # TC-034: request_forget with both limits set waits for the person and the record stays; TC-035, TC-093: no function of the action
    # layer that forgets or clears a work directory names the budget
    import ast
    import asyncio
    import inspect
    from abf_platform import actions
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 20, 100)
    out = asyncio.run(actions.request_forget(w.ip.state_db, w.ip.index, run_name="run-one", caller=ann, person=None))
    assert out.get("sent") is not True and out.get("channel") != "BUDGET" and not _budget_rows(w), out
    from abf_platform import status
    assert status.find_run(w.ip.index, "run-one") is not None
    tree = ast.parse(inspect.getsource(actions))
    seen = 0
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        consts = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        if "forget" in fn.name or "clean" in fn.name or "clean_work" in consts:
            seen += 1
            names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
            assert not ({"BUDGET", "budget", "decide"} & names), fn.name
    assert seen >= 3


def test_bg_39_only_page_channel_and_only_good_values_with_plain_reasons(w):
    # TC-043, TC-044, TC-045, TC-046, TC-047, TC-048, TC-075
    from abf_platform import actions, jobs
    ann = w.user("ann")
    assert _set(w, ann, 20, 100) == {"ok": True}
    kept = {"single": 20.0, "month": 100.0}
    for ch in (actions.ELICITED, actions.TERMINAL, actions.CHAT, actions.BUDGET, None, "PAGE", "yes", object()):
        with pytest.raises(jobs.JobRefused) as e:
            actions.set_my_budget(w.ip.tokens, 5, 5, confirmed_by=ch, caller=ann)
        assert "no human confirmation channel" in str(e.value) and "Traceback" not in str(e.value)
        if ch in (actions.ELICITED, actions.TERMINAL):
            assert "設定頁" in str(e.value)                       # what to do: the person sets it on the settings page
        assert actions.get_my_budget(w.ip.tokens, caller=ann) == kept
    for bad in (-1, -0.5, float("nan"), float("inf"), True, False, "50", "abc", 1000001):
        for single, month in ((bad, 100), (20, bad)):
            out = _set(w, ann, single, month)
            assert out["ok"] is False and "1,000,000" in out["message"] and _plain(out), (bad, out)
            assert actions.get_my_budget(w.ip.tokens, caller=ann) == kept
    assert _set(w, ann, 0, 1000000) == {"ok": True}
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": 0.0, "month": 1000000.0}
    assert _set(w, ann, 1000000, 0) == {"ok": True}
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": 1000000.0, "month": 0.0}


def test_bg_40_clearing_both_limits_asks_again(w):
    # TC-049
    from abf_platform import actions
    ann = w.user("ann")
    _history(w, ann, su=10)
    _set(w, ann, 20, 100)
    assert _set(w, ann, None, None) == {"ok": True}
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": None, "month": None}
    assert _is_pending(_go(w, ann))


def _budget_csrf(html):
    return re.search(r'action="/settings/budget">.*?name="csrf" value="([^"]+)"', html, re.S).group(1)


def test_bg_41_the_page_saves_only_my_own_limits(w):
    # TC-050, TC-051: bob's login cannot change or see ann's numbers; TC-003, TC-004: one box alone may be saved (and then every send asks)
    from abf_platform import actions
    ann, bob = w.user("ann"), w.user("bob")
    _set(w, ann, 20, 100)
    c = w.web()
    w.login(c, "bob")
    html = c.get("/settings").text
    assert 'value="20"' not in html and 'value="100"' not in html and "未設定＝每次都問你" in html
    post = {"csrf": _budget_csrf(html), "single": "7", "month": "9", "lang": "zh", "user_id": str(ann.user_id), "name": "ann", "user": "ann"}
    assert c.post("/settings/budget", data=post, headers={"origin": "http://testserver"}).status_code in (302, 303)
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": 20.0, "month": 100.0}
    assert actions.get_my_budget(w.ip.tokens, caller=bob) == {"single": 7.0, "month": 9.0}
    post = {"csrf": _budget_csrf(c.get("/settings").text), "single": "7", "month": "", "lang": "zh"}
    assert c.post("/settings/budget", data=post, headers={"origin": "http://testserver"}).status_code in (302, 303)
    assert actions.get_my_budget(w.ip.tokens, caller=bob) == {"single": 7.0, "month": None}
    post = {"csrf": _budget_csrf(c.get("/settings").text), "single": "abc", "month": "5", "lang": "zh"}
    bad = c.post("/settings/budget", data=post, headers={"origin": "http://testserver"})
    assert bad.status_code == 400 and "1,000,000" in bad.text and "Traceback" not in bad.text      # TC-075 on the page
    assert actions.get_my_budget(w.ip.tokens, caller=bob) == {"single": 7.0, "month": None}


def test_bg_42_no_tool_flag_or_variable_sets_a_limit(w, monkeypatch):
    # TC-053, TC-068, TC-094: no MCP or chat tool, parameter, environment variable or abf-platform command writes a limit
    import asyncio
    from abf_platform import actions, cli
    from abf_platform.actions import chat_tools
    ann = w.user("ann")
    _history(w, ann, su=10)
    tools, _ = w.mcp([], caller=ann)
    specs = asyncio.run(chat_tools.tool_specs(w.ip.index, w.ip.state_db))
    names = [(t.name, list((getattr(t, "inputSchema", None) or getattr(t, "input_schema", None) or {}).get("properties") or {}), t.description or "")
             for t in tools]
    for s in specs:
        f = s.get("function", s)
        schema = f.get("parameters") or f.get("input_schema") or {}
        names.append((f.get("name", ""), list(schema.get("properties") or {}), f.get("description") or ""))
    assert len(tools) > 5 and specs
    for name, params, words in names:
        for word in [name] + params:
            parts = re.split(r"[_\W]+", word.lower())
            assert not ({"budget", "su", "limit", "limits"} & set(parts)) and "budget" not in word.lower(), (name, word)
        assert "budget" not in words.lower() and "額度內" not in words, name
    for var in ("ABF_AUTO_SU_SINGLE", "ABF_AUTO_SU_MONTH", "ABF_BUDGET", "ABF_SU_BUDGET", "ABF_AUTO_SEND"):
        monkeypatch.setenv(var, "1000")
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": None, "month": None}
    assert _is_pending(_go(w, ann))
    for words in (["auto-send", "set", "20", "100"], ["auto-send", "limit", "20"], ["budget", "set", "20", "100"], ["user", "budget", "ann", "20", "100"]):
        with pytest.raises(SystemExit):
            cli.main(words)
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": None, "month": None}


def test_bg_43_auto_send_list_all_four_kinds_and_history_stays(r, monkeypatch, capsys):
    # TC-063: the four BUDGET sends (launch, resume, relaunch, cancel), one per line, in time order; TC-065: they are still listed after
    # the person clears the limits; TC-067: the list writes nothing; TC-076: no token or password in it
    from human_harness import PASSWORD
    from abf_platform import cli
    ann = _scene(r)
    w = r.w
    monkeypatch.setenv("ABF_PLATFORM_STATE", str(w.ip.state_db))
    monkeypatch.setenv("ABF_INDEX", str(w.ip.index))
    monkeypatch.setattr("abf_platform.store.default_tokens_path", lambda *a, **k: w.ip.tokens)
    monkeypatch.setattr("abf_platform.store.default_index_path", lambda *a, **k: w.ip.index)
    _set(w, ann, 20, 1000)
    for kind, out in _four(r, ann).items():
        assert out["sent"] is True and out["channel"] == "BUDGET", (kind, out)
    rows = _budget_rows(w)
    assert len(rows) == 4

    def snapshot():
        con = sqlite3.connect(str(w.ip.tokens))
        users = con.execute("SELECT * FROM users ORDER BY id").fetchall()
        con.close()
        return ([tuple(x) for x in w.sql("SELECT * FROM confirmations ORDER BY id")], [tuple(x) for x in w.sql("SELECT * FROM jobs ORDER BY id")], users)

    def listed():
        capsys.readouterr()
        assert cli.main(["auto-send", "list"]) == 0
        text = capsys.readouterr().out
        assert PASSWORD not in text
        return [line.split("\t") for line in text.splitlines() if "\t" in line]
    before = snapshot()
    lines = listed()
    assert len(lines) == 4 and all(len(cols) == 6 for cols in lines)
    assert [cols[0] for cols in lines] == sorted(cols[0] for cols in lines)
    assert [cols[4] for cols in lines] == [row["id"] for row in rows]
    assert {cols[1] for cols in lines} == {"ann"} and sorted(cols[2] for cols in lines) == ["cancel", "launch", "launch", "launch"]
    assert {cols[3] for cols in lines} >= {"run-new", "run-live"} and all(cols[5] for cols in lines)
    assert snapshot() == before
    assert _set(w, ann, None, None) == {"ok": True}
    assert [cols[4] for cols in listed()] == [row["id"] for row in rows]


def test_bg_44_samplesheet_seen_is_not_a_run_approval(w):
    # TC-070: the person agreeing to a samplesheet (it is shown in the request) approves no run: the request stays pending, no job;
    # TC-072: over the single limit it still waits; TC-071: inside the limits the yes is the budget's, recorded as BUDGET
    ann = w.user("ann")
    _history(w, ann, su=10)
    n = len(w.jobs())
    first = _go(w, ann)
    assert _is_pending(first) and len(w.jobs()) == n
    assert [c["state"] for c in w.confirmations() if c["id"] == first["id"]] == ["pending"]
    _set(w, ann, 5, 100)
    assert _is_pending(_go(w, ann, "run-three")) and len(w.jobs()) == n and not _budget_rows(w)
    _set(w, ann, 20, 100)
    out = _go(w, ann, "run-four")
    assert out["sent"] is True and out["channel"] == "BUDGET" and len(_budget_rows(w)) == 1


def test_bg_45_other_pages_are_as_they_were(w):
    # TC-069, TC-095: with no limit set only the settings page speaks of the budget; no page has a new banner for it
    ann = w.user("ann")
    _history(w, ann, su=10)
    pending = _go(w, ann)
    c = w.web()
    w.login(c, "ann")
    for path in ("/", "/runs", "/c/%s" % pending["id"]):
        html = c.get(path, follow_redirects=True).text
        assert "預算內免逐次確認" not in html and "/settings/budget" not in html and "auto_su" not in html, path
    assert "預算內免逐次確認" in c.get("/settings").text


def test_bg_46_an_old_database_opens_with_nobody_on_a_budget(w):
    # TC-060, TC-061: an old database (none of the three columns) with a user and a request in it gets the columns, keeps its rows, and
    # every limit reads as not set; opening it again changes nothing
    from abf_platform import actions, store
    ann = w.user("ann")
    _history(w, ann, su=10)
    kept = [tuple(x)[:-1] for x in w.sql("SELECT * FROM confirmations ORDER BY id")]
    assert w.sql("SELECT * FROM confirmations")[0].keys()[-1] == "budget_note"
    for path, table, cols in ((w.ip.tokens, "users", ("auto_su_single", "auto_su_month")), (w.ip.state_db, "confirmations", ("budget_note",))):
        con = sqlite3.connect(str(path))
        for col in cols:
            con.execute("ALTER TABLE %s DROP COLUMN %s" % (table, col))
        con.commit()
        con.close()
    for _ in range(2):
        store.connect_tokens(str(w.ip.tokens)).close()
        store.connect_state(w.ip.state_db).close()
    con = sqlite3.connect(str(w.ip.tokens))
    assert {"auto_su_single", "auto_su_month"} <= {x[1] for x in con.execute("PRAGMA table_info(users)")}
    assert con.execute("SELECT name FROM users").fetchall() == [("ann",)]
    con.close()
    assert [tuple(x)[:-1] for x in w.sql("SELECT * FROM confirmations ORDER BY id")] == kept
    assert all(x["budget_note"] is None for x in w.sql("SELECT * FROM confirmations"))
    assert actions.get_my_budget(w.ip.tokens, caller=ann) == {"single": None, "month": None}
    assert _is_pending(_go(w, ann))
