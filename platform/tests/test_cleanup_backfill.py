# Nothing existing: tests of the terminal command that offers a clean-up request for runs that succeeded before the offer existed; no earlier test drives `runs offer-cleanup`.
"""cloud-cleanup-backfill: `abf-platform runs offer-cleanup` writes pending `clean_work` requests for runs that already succeeded.

Test cases are named in the comments (TC-001 ...), they come from specs/cloud-cleanup-backfill/test-case.md. Without --apply the command
only previews (ruling 4). The command never confirms and never deletes: the owner presses the button on the confirmation page.
"""
import ast
import json
import time

import pytest

from human_harness import World
from owner_harness import Duo, sql_exec, sql_rows
from helpers import PLATFORM_DIR

PKG = PLATFORM_DIR / "abf_platform"
DAY = 86400.0
CMD = ("runs", "offer-cleanup")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def add(d, name, user, status="succeeded", sid=4242):
    ce = "lab-a" if user != d.b.user_id else "b1"
    """A run in the index, its row in the hand-off record and the confirmation of the launch that holds what was sent."""
    from abf_station import launch as bundle_mod
    from abf_platform import common, compute_envs, store
    view = compute_envs.get(d.state, ce)
    folder = view["config"]["workDir"] + "/runs/" + name
    at = time.time() - 100
    con = store.connect_index(d.w.ip.index)
    try:
        with con:
            con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at) "
                        "VALUES (?, ?, ?, 'live', ?, 1, 2, 3)", ("id-" + name, "s-" + name, name, status))
    finally:
        con.close()
    sql_exec(d.state, "INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, user_id) "
                      "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (name, sid, folder, ce, view["agent"], at, at + 1, user))
    body = {"run_name": name, "run_folder": folder, "ce": bundle_mod.snapshot_ce(view)}
    sql_exec(d.state, "INSERT INTO confirmations (id, sha256, kind, created_at, caller_user_id, state, confirmed_at, bundle_json) "
                      "VALUES (?, ?, 'launch', ?, ?, 'confirmed', ?, ?)",
             ("L-" + name, common.bundle_sha256(body), at, user, at, json.dumps(body)))


def cleans(d):
    return sql_rows(d.state, "SELECT * FROM confirmations WHERE kind = 'clean_work' ORDER BY created_at, id")


def run(d, *args):
    return d.w.ip.run(*CMD, *args)


def three(d):
    d.bobs_environment()
    add(d, "r-a", d.a.user_id)
    add(d, "r-b", d.b.user_id)
    add(d, "r-c", d.a.user_id, status="failed")


def test_all_apply_offers_for_each_succeeded_run(d):
    # TC-001, TC-002, TC-003, TC-004, TC-006, TC-024, TC-025, TC-028, TC-061
    three(d)
    jobs_before = len(sql_rows(d.state, "SELECT * FROM jobs"))
    rc, out = run(d, "--all", "--apply")
    assert rc == 0, out
    rows = cleans(d)
    assert len(rows) == 2 and {r["state"] for r in rows} == {"pending"}
    assert sorted(r["caller_user_id"] for r in rows) == sorted([d.a.user_id, d.b.user_id])
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 4
    assert "r-a: 已提出申請，請 alice 登入網頁在確認頁按送出 (offered; alice presses send on the confirmation page)" in lines
    assert "r-b: 已提出申請，請 bob 登入網頁在確認頁按送出 (offered; bob presses send on the confirmation page)" in lines
    skipped = [ln for ln in lines if ln.startswith("r-c: 略過：")]
    assert len(skipped) == 1 and "沒有成功跑完" in skipped[0]
    assert lines[-1] == "已提出 2 張、略過 1 個 (offered 2, skipped 1)"
    assert len(sql_rows(d.state, "SELECT * FROM jobs")) == jobs_before
    assert not sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'clean_work'")
    assert not sql_rows(d.state, "SELECT * FROM launches WHERE work_cleaned_at IS NOT NULL")


def test_named_run_only(d):
    # TC-005
    three(d)
    rc, out = run(d, "r-a", "--apply")
    assert rc == 0, out
    assert len(cleans(d)) == 1 and cleans(d)[0]["caller_user_id"] == d.a.user_id


def test_user_filter_with_all_and_with_a_name(d):
    # TC-007, TC-008
    three(d)
    rc, out = run(d, "--all", "--user", "alice", "--apply")
    assert rc == 0, out
    assert [r["caller_user_id"] for r in cleans(d)] == [d.a.user_id]
    assert not [ln for ln in out.splitlines() if ln.startswith("r-b: 已提出")]
    rc, out = run(d, "r-b", "--user", "alice", "--apply")
    assert rc == 0 and any(ln.startswith("r-b: 略過：") for ln in out.splitlines())
    assert len(cleans(d)) == 1


def test_the_reason_of_offer_cleanup_is_shown_word_for_word(d, monkeypatch):
    # TC-009
    from abf_platform import actions
    three(d)
    real = actions.offer_cleanup

    def fake(platform_path, index_path, run_name, **kw):
        if run_name == "r-a":
            return {"offered": False, "reason": "quota full"}
        return real(platform_path, index_path, run_name, **kw)
    monkeypatch.setattr(actions, "offer_cleanup", fake)
    rc, out = run(d, "--all", "--apply")
    assert rc == 0, out
    assert "r-a: 略過：quota full" in out.splitlines()
    assert len(cleans(d)) == 1 and cleans(d)[0]["caller_user_id"] == d.b.user_id


def test_all_skipped_still_exits_zero(d):
    # TC-010
    add(d, "r-c", d.a.user_id, status="failed")
    rc, out = run(d, "--all", "--apply")
    assert rc == 0 and out.splitlines()[-1] == "已提出 0 張、略過 1 個 (offered 0, skipped 1)"


def test_bad_input_is_refused_in_plain_words(d):
    # TC-011, TC-012, TC-013, TC-016, TC-017
    three(d)
    for args in (("--apply",), ("r-a", "--all", "--apply"), ("--all", "--user", "nobody", "--apply")):
        rc, out = run(d, *args)
        assert rc == 1 and out.strip() and len(cleans(d)) == 0, (args, out)
        assert "Traceback" not in out and "SELECT" not in out and ".db" not in out
    rc, out = run(d, "--al", "--apply")
    assert rc != 0 and not cleans(d)


def test_unknown_run_and_run_without_owner(d):
    # TC-014, TC-015, TC-060
    add(d, "r-x", None)
    rc, out = run(d, "no-such-run", "--apply")
    assert rc == 0 and "no-such-run: 略過：" in out and "no such run" in out
    rc, out = run(d, "r-x", "--apply")
    assert rc == 0 and "r-x: 略過：" in out and "沒有擁有者" in out
    assert not cleans(d)
    assert sql_rows(d.state, "SELECT user_id FROM launches WHERE run_name = 'r-x'")[0]["user_id"] is None


def test_without_apply_nothing_is_written(d):
    # TC-018, TC-019, TC-020, TC-021, TC-027
    three(d)
    before = (len(sql_rows(d.state, "SELECT * FROM confirmations")), len(sql_rows(d.state, "SELECT * FROM jobs")))
    rc, out = run(d, "--all")
    assert rc == 0 and "r-a: 會提出申請 (would offer)" in out and "r-b: 會提出申請 (would offer)" in out
    assert any(ln.startswith("r-c: 略過：") for ln in out.splitlines()) and "r-c: 會提出" not in out
    rc, out = run(d, "r-a")
    assert rc == 0 and "r-a: 會提出申請" in out
    rc, out = run(d, "--all", "--list")
    assert rc == 0 and "會提出申請" in out
    assert (len(sql_rows(d.state, "SELECT * FROM confirmations")), len(sql_rows(d.state, "SELECT * FROM jobs"))) == before


def test_running_twice_does_not_duplicate(d):
    # TC-022
    three(d)
    run(d, "--all", "--apply")
    first = len(cleans(d))
    rc, out = run(d, "--all", "--apply")
    assert rc == 0 and len(cleans(d)) == first == 2


def test_after_eight_days_a_new_request_is_made(d):
    # TC-023
    from abf_platform import actions
    from helpers import Clock
    add(d, "r-a", d.a.user_id)
    clock = Clock(time.time())
    first = actions.offer_cleanups(d.state, d.w.ip.index, run_names=["r-a"], clock=clock)
    assert first["offered"] == 1
    clock.t += 8 * DAY
    again = actions.offer_cleanups(d.state, d.w.ip.index, run_names=["r-a"], clock=clock)
    assert again["offered"] == 1
    rows = cleans(d)
    assert len(rows) == 2 and len([r for r in rows if r["expires_at"] > clock.t]) == 1


def test_the_command_never_confirms_and_has_no_second_logic():
    # TC-031, TC-033, TC-059
    def fn_src(path, name):
        text = path.read_text(encoding="utf-8")
        node = [n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name == name][0]
        return ast.get_source_segment(text, node)
    cmd = fn_src(PKG / "cli.py", "cmd_runs_offer_cleanup")
    act = fn_src(PKG / "actions" / "__init__.py", "offer_cleanups")
    for src in (cmd, act):
        for word in ("approve", "enqueue", "subprocess", "os.system", "work_cleaned_at"):
            assert word not in src, word
    for word in ("create_pending", "prepare_clean", "latest_launch"):
        assert word not in cmd, word
    users = [p.name for p in PKG.rglob("*.py") if "offer_cleanups(" in p.read_text(encoding="utf-8")]
    assert sorted(users) == ["__init__.py", "cli.py"]


def test_the_output_comes_from_the_action(d, monkeypatch):
    # TC-033
    from abf_platform import actions
    monkeypatch.setattr(actions, "offer_cleanups", lambda *a, **k: {
        "ok": True, "results": [{"run_name": "zz", "offered": False, "reason": "made up", "owner": None}], "offered": 0, "skipped": 1})
    rc, out = run(d, "zz", "--apply")
    assert rc == 0 and "zz: 略過：made up" in out and out.splitlines()[-1] == "已提出 0 張、略過 1 個 (offered 0, skipped 1)"


def test_dry_run_and_the_shape_of_the_answer(d):
    # TC-034, TC-035, TC-036
    import inspect
    from abf_platform import actions
    three(d)
    p = inspect.signature(actions.offer_cleanup).parameters
    assert list(p) == ["platform_path", "index_path", "run_name", "clock", "dry_run"]
    assert p["dry_run"].kind is inspect.Parameter.KEYWORD_ONLY and p["dry_run"].default is False
    idx = d.w.ip.index
    out = actions.offer_cleanup(d.state, idx, "r-a", dry_run=True)
    assert out["offered"] is False and out["would_offer"] is True and not cleans(d)
    assert actions.offer_cleanup(d.state, idx, "r-c", dry_run=True)["would_offer"] is False
    assert set(actions.offer_cleanup(d.state, idx, "r-c")) == {"offered", "reason"}
    assert set(actions.offer_cleanup(d.state, idx, "r-a")) == {"offered", "id"}


def test_one_failing_run_does_not_stop_the_others(d, monkeypatch):
    # TC-037, TC-017
    from abf_platform import actions
    three(d)
    real = actions.offer_cleanup

    def fake(platform_path, index_path, run_name, **kw):
        if run_name == "r-a":
            raise RuntimeError("boom /secret/path")
        return real(platform_path, index_path, run_name, **kw)
    monkeypatch.setattr(actions, "offer_cleanup", fake)
    out = actions.offer_cleanups(d.state, d.w.ip.index, run_names=["r-a", "r-b"])
    by = {r["run_name"]: r for r in out["results"]}
    assert by["r-a"]["offered"] is False and by["r-a"]["reason"] and by["r-b"]["offered"] is True
    rc, text = run(d, "--all", "--apply")
    assert rc == 0 and "Traceback" not in text and "boom" not in text and "/secret" not in text


def test_the_shape_of_offer_cleanups(d):
    # TC-038, TC-039, TC-040, TC-041
    from abf_platform import actions
    three(d)
    add(d, "r-run", d.a.user_id, status="running")
    out = actions.offer_cleanups(d.state, d.w.ip.index, run_names=["r-a", "r-b", "r-a", "nope"], user_id=d.a.user_id)
    assert out["ok"] is True and [r["run_name"] for r in out["results"]] == ["r-a", "r-b", "nope"]
    assert out["offered"] + out["skipped"] == len(out["results"]) == 3
    by = {r["run_name"]: r for r in out["results"]}
    assert set(by["r-a"]) == {"run_name", "offered", "reason", "owner"} and by["r-a"]["owner"] == "alice"
    assert by["r-b"]["reason"] == "not that user's run" and by["nope"]["reason"] == "no such run" and by["nope"]["owner"] is None
    assert len(cleans(d)) == 1
    every = actions.offer_cleanups(d.state, d.w.ip.index, dry_run=True)["results"]
    assert sorted(r["run_name"] for r in every if r["would_offer"]) == ["r-a", "r-b"]
    assert not [r for r in every if r["run_name"] in ("r-c", "r-run") and r["offered"]]


def test_no_new_names_but_the_command_and_its_options():
    # TC-044, TC-047, TC-057, TC-060
    from abf_platform import cli
    parser = cli.build_parser()
    runs = parser._subparsers._group_actions[0].choices["runs"]
    oc = runs._subparsers._group_actions[0].choices["offer-cleanup"]
    opts = {o for a in oc._actions for o in a.option_strings}
    assert opts == {"-h", "--help", "--all", "--user", "--list", "--apply"}
    assert cli.ADOPTING == ("serve", "web", "mcp", "ce")


def test_the_first_line_of_this_file_says_why():
    # TC-049
    first = open(__file__, encoding="utf-8").readline()
    assert first.startswith("# Nothing existing: ") and len(first[len("# Nothing existing: "):].strip()) >= 15
