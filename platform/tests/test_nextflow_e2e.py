# Nothing existing: end-to-end tests that run the pinned real Nextflow against this folder's receiver; no existing test rig does that.
"""End-to-end tests with the real, pinned Nextflow (feature 008).

Nothing here talks to Seqera: tower.endpoint is always a local address (TC-051) and the PATH given to
Nextflow has no 'tw'. The fixture pipelines need no container and no network.
"""
import datetime
import hashlib
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from abf_platform import status
from e2e_harness import (Env, history, run_name_of, trace_by_process, trace_counts, trace_files, trace_rows,
                         wait_until)
from helpers import (H, all_files_digest, basic_header, db_bytes, db_counts, mcp_call, pkg_env, run_cli,
                     tool_json)


def _epoch(iso):
    return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def _runs_via_mcp(env):
    """list_runs, then get_run for each run, over stdio. Returns {id: get_run result}."""
    _, outs = mcp_call(env, [("list_runs", {})])
    ids = [r["id"] for r in tool_json(outs[0])["runs"]]
    if not ids:
        return {}
    _, outs = mcp_call(env, [("get_run", {"run_id": i}) for i in ids])
    return {i: tool_json(o) for i, o in zip(ids, outs)}


def _by_name(runs, name):
    found = [v for v in runs.values() if v["name"] == name]
    assert len(found) == 1, (name, [v["name"] for v in runs.values()])
    return found[0]


def _tasks(v):
    t = v["tasks"]
    return {k: t[k] for k in ("total", "succeeded", "cached", "failed")}


@pytest.fixture(scope="module")
def world(e2e_cfg, tmp_path_factory):
    """One receiver, three runs: ok, ok again with -resume (same folder), and a failing one."""
    base = tmp_path_factory.mktemp("world")
    env = Env(e2e_cfg, base)
    ok_dir, fail_dir = base / "launch_ok", base / "launch_fail"
    w = {"env": env, "ok_dir": ok_dir, "fail_dir": fail_dir}
    w["ok"] = env.run_nf("ok", ok_dir)
    w["resume"] = env.run_nf("ok", ok_dir, args=["-resume"])
    w["fail"] = env.run_nf("fail", fail_dir)
    time.sleep(1.5)  # the last messages are in before the receiver is asked
    yield w
    env.stop()


def test_tc001_a_succeeded_run_is_recorded_with_nextflows_own_numbers(world):
    # TC-001 (also TC-014: the real Nextflow authenticated with a platform token, and TC-009: it accepted our workflowId)
    p = world["ok"]
    assert p.returncode == 0, p.stdout + p.stderr
    runs = _runs_via_mcp(world["env"].cli_env())
    v = _by_name(runs, p.run_name)
    hist = [h for h in history(world["ok_dir"]) if h["run_name"] == p.run_name][0]
    rows = trace_rows(trace_files(world["ok_dir"])[0])
    assert v["status"] == "succeeded"
    assert v["session_id"] == hist["session"]
    n = len(rows)
    assert n >= 3
    assert v["tasks"]["total"] == v["tasks"]["succeeded"] == n
    assert v["tasks"]["cached"] == 0 and v["tasks"]["failed"] == 0
    assert int(p.t0) - 1 <= _epoch(v["started_at"]) <= _epoch(v["ended_at"]) <= int(p.t1) + 2
    assert v["started_at"].endswith("Z")


def test_tc003_a_failed_run_keeps_the_failed_task_and_its_message(world):
    # TC-003
    p = world["fail"]
    assert p.returncode != 0
    runs = _runs_via_mcp(world["env"].cli_env())
    v = _by_name(runs, p.run_name)
    rows = trace_rows(trace_files(world["fail_dir"])[0])
    failed_rows = [r for r in rows if r["status"] == "FAILED"]
    assert v["status"] == "failed"
    assert [(f["name"], f["exit_code"]) for f in v["failed_tasks"]] == [(r["name"], int(r["exit"])) for r in failed_rows]
    assert v["failed_tasks"][0]["exit_code"] == 1
    assert "FIXTURE_BOOM_7" in v["failed_tasks"][0]["error_message"]
    assert v["tasks"]["succeeded"] == len([r for r in rows if r["status"] == "COMPLETED"])


def test_tc004_resume_is_a_second_run_of_the_same_session(world):
    # TC-004
    runs = _runs_via_mcp(world["env"].cli_env())
    first, second = _by_name(runs, world["ok"].run_name), _by_name(runs, world["resume"].run_name)
    assert first["name"] != second["name"]
    assert first["session_id"] == second["session_id"]
    assert first["id"] != second["id"]
    rows2 = trace_rows(trace_files(world["ok_dir"])[-1])
    assert _tasks(second) == {k: trace_counts(rows2)[k] for k in ("total", "succeeded", "cached", "failed")}
    assert second["tasks"]["cached"] == len(rows2) > 0
    listed = tool_json(mcp_call(world["env"].cli_env(), [("list_runs", {})])[1][0])["runs"]
    assert {first["id"], second["id"]} <= {r["id"] for r in listed}


def test_tc021_per_process_counts_equal_the_trace_grouped_by_process(world):
    # TC-021
    runs = _runs_via_mcp(world["env"].cli_env())
    v = _by_name(runs, world["fail"].run_name)
    want = trace_by_process(trace_rows(trace_files(world["fail_dir"])[0]))
    got = {p["name"]: {k: p[k] for k in ("total", "succeeded", "cached", "failed", "aborted")} for p in v["processes"]}
    assert got == want
    assert v["started_at"] and v["ended_at"]


def test_tc002_a_run_in_flight_shows_the_last_progress_it_received(e2e_cfg, tmp_path):
    # TC-002: the slow pipeline has a task that sleeps about 20 seconds.
    env = Env(e2e_cfg, tmp_path)
    launch = tmp_path / "launch"
    proc = env.start_nf("slow", launch)
    try:
        def last_progress_with_running():
            for _, _, body, _ in reversed(env.recorder.of_kind("progress")):
                pr = body["progress"]
                if pr["running"] >= 1 and pr["succeeded"] >= 3:
                    return body
            return None

        wait_until(last_progress_with_running, timeout=90, what="a progress message with running and finished tasks")
        # read the last recorded progress, ask, and read again: they must agree for the answer to be comparable
        for _ in range(10):
            before = env.recorder.of_kind("progress")[-1][2]["progress"]
            runs = _runs_via_mcp(env.cli_env())
            after = env.recorder.of_kind("progress")[-1][2]["progress"]
            if before == after:
                break
        assert before == after
        (v,) = runs.values()
        assert v["status"] == "running"
        assert v["tasks"]["succeeded"] == before["succeeded"] and v["tasks"]["running"] == before["running"]
        assert v["tasks"]["total"] == before["succeeded"] + before["running"] + before["pending"] + before["submitted"] \
            + before["cached"] + before["failed"] + before["aborted"]
        mid = dict(v["tasks"])
        proc.wait(timeout=120)
        time.sleep(1.5)
        (final,) = _runs_via_mcp(env.cli_env()).values()
        assert final["status"] == "succeeded"
        assert final["tasks"]["succeeded"] == 4 and mid["succeeded"] != final["tasks"]["succeeded"]
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        env.stop()


def test_tc013_a_wrong_token_stops_nextflow_before_it_starts(e2e_cfg, tmp_path):
    # TC-013
    env = Env(e2e_cfg, tmp_path)
    try:
        launch = tmp_path / "launch"
        p = env.run_nf("ok", launch, token="abf_" + "w" * 43)
        assert p.returncode != 0
        out = p.stdout + p.stderr
        assert re.search(r"Unauthorized|401|access token", out, re.I), out
        rows = [r for f in trace_files(launch) for r in trace_rows(f)]
        assert rows == []
        assert db_counts(env.index) == {"runs": 0, "processes": 0, "failed_tasks": 0}
    finally:
        env.stop()


def test_tc041_canaries_in_config_environment_and_params_are_not_stored(e2e_cfg, tmp_path):
    # TC-041
    env = Env(e2e_cfg, tmp_path)
    try:
        launch = tmp_path / "launch"
        launch.mkdir()
        (launch / "nextflow.config").write_text("process.ext.note = 'CFG_CANARY_e41'\nparams.outdir = 'results'\n")
        p = env.run_nf("ok", launch, args=["--access_token", "PARAM_CANARY_e41"],
                       extra_env={"MY_ENV_SECRET": "ENV_CANARY_e41"})
        assert p.returncode == 0, p.stdout + p.stderr
        time.sleep(1.0)
        begin = env.recorder.of_kind("begin")
        assert begin, "the receiver saw no begin"
        sent = begin[0][3].decode()
        # the test has teeth only if Nextflow really sent these
        assert "CFG_CANARY_e41" in sent and "PARAM_CANARY_e41" in sent
        blob = db_bytes(env.index, env.tokens)
        for c in ("CFG_CANARY_e41", "PARAM_CANARY_e41", "ENV_CANARY_e41"):
            assert c.encode() not in blob, c
        (v,) = _runs_via_mcp(env.cli_env()).values()
        assert v["status"] == "succeeded"
    finally:
        env.stop()


def test_tc051_the_endpoint_is_local_and_tw_is_not_needed(world):
    # TC-051 (e2e half)
    env = world["env"]
    assert env.url.startswith("http://127.0.0.1:")
    path = env.nf_env()["PATH"]
    assert shutil.which("tw", path=path) is None
    with pytest.raises(AssertionError):
        env.nf_cmd("ok", endpoint="https://example.org")


# ---------------------------------------------------------------- rebuild (US4)

_COMPARED = ("id", "name", "session_id", "status", "tasks", "processes", "failed_tasks")
# Named on purpose (007b follow-up 3, TC-F3-11): get_run also has "failure_reason", Nextflow's own words from the complete
# message. .nextflow.log does not hold workflow.errorMessage, so a rebuilt run has none; test_tcf3_11 checks both sides.
_NOT_REBUILT = ("failure_reason",)


# Allowed gap between live and rebuilt started_at / ended_at. It was 1 s; CI run 38598019862 (2026-10-14, commit cba254d,
# first attempt) saw started_at differ by 2 s (live 16:33:36Z, rebuilt 16:33:38Z) and passed on rerun. The cause is not
# proven: research.md "Time resolution" explains a 1 s gap only. 3 s covers that 2 s case with margin.
_CLOCK_SLACK_SECONDS = 3


def _compared(v):
    out = {k: v[k] for k in _COMPARED}
    return out


def _same_runs(before, after):
    assert before.keys() == after.keys()
    for i, b in before.items():
        a = after[i]
        assert _compared(a) == _compared(b), i
        # Start and end are whole seconds, but Nextflow writes them from different clock samples in the
        # live message and in its files (research.md, "Time resolution"): they may sit a little apart.
        assert abs(_epoch(a["started_at"]) - _epoch(b["started_at"])) <= _CLOCK_SLACK_SECONDS, (i, a["started_at"], b["started_at"])
        if b["ended_at"]:
            assert abs(_epoch(a["ended_at"]) - _epoch(b["ended_at"])) <= _CLOCK_SLACK_SECONDS, (i, a["ended_at"], b["ended_at"])
        else:
            assert a["ended_at"] == b["ended_at"]


# ---- guard for _same_runs (flaky-time, TC-FT-03/04/06): pure functions, no Nextflow needed.

def _run(started="2026-10-14T16:33:36Z", ended="2026-10-14T16:34:00Z"):
    return {"id": "r1", "name": "n", "session_id": "s", "status": "SUCCEEDED", "tasks": 1, "processes": 1,
            "failed_tasks": 0, "started_at": started, "ended_at": ended}


def _shift(iso, seconds):
    t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")) + datetime.timedelta(seconds=seconds)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_ft03_same_runs_accepts_the_two_second_ci_gap():
    # TC-FT-03: CI run 38598019862 had started_at 16:33:36Z live vs 16:33:38Z rebuilt
    _same_runs({"r1": _run()}, {"r1": _run(started="2026-10-14T16:33:38Z")})
    _same_runs({"r1": _run()}, {"r1": _run(ended="2026-10-14T16:34:02Z")})


@pytest.mark.parametrize("field", ["started_at", "ended_at"])
@pytest.mark.parametrize("gap", [60, _CLOCK_SLACK_SECONDS + 1])
def test_ft04_same_runs_still_fails_on_a_large_gap(field, gap):
    # TC-FT-04 (guard): a gap beyond the slack must still fail, for both fields
    base = _run()
    other = dict(base, **{field: _shift(base[field], gap)})
    with pytest.raises(AssertionError):
        _same_runs({"r1": base}, {"r1": other})


def test_ft06_same_runs_ended_at_none_is_exact():
    # TC-FT-06: one side None must fail (the live side raises AttributeError from _epoch(None); either way the test fails)
    _same_runs({"r1": _run(ended=None)}, {"r1": _run(ended=None)})
    with pytest.raises(AssertionError):
        _same_runs({"r1": _run(ended=None)}, {"r1": _run()})
    with pytest.raises((AssertionError, AttributeError)):
        _same_runs({"r1": _run()}, {"r1": _run(ended=None)})


def _delete_index(env):
    for suffix in ("", "-wal", "-shm", "-journal"):
        q = Path(str(env.index) + suffix)
        if q.exists():
            q.unlink()
    for suffix in ("", "-wal", "-shm", "-journal"):
        assert not Path(str(env.index) + suffix).exists()


def test_tc030_rebuild_gives_back_every_field(world, tmp_path):
    # TC-030
    env = world["env"]
    before = _runs_via_mcp(env.cli_env())
    assert len(before) == 3
    work = tmp_path / "w"
    work.mkdir()
    index = work / "index.db"
    shutil.copy(env.index, index)
    cli_env = pkg_env(ABF_PLATFORM_DB=index, ABF_PLATFORM_TOKENS=env.tokens)
    for suffix in ("", "-wal", "-shm", "-journal"):
        Path(str(index) + suffix).unlink(missing_ok=True)
    assert not index.exists()
    r = run_cli(["rebuild", str(world["ok_dir"]), str(world["fail_dir"])], env=cli_env)
    assert r.returncode == 0, r.stdout + r.stderr
    after = _runs_via_mcp(cli_env)
    assert len(after) == len(before) > 0
    _same_runs(before, after)


def test_tcf3_11_the_live_run_has_nextflows_reason_and_a_rebuilt_one_has_none(world, tmp_path):
    # TC-F3-11: real Nextflow, failing task "FIXTURE_BOOM_7": live get_run says why; rebuild cannot (the log has no
    # errorMessage), so the field is the one that differs and every compared field is still equal (TC-030 stays strict)
    env = world["env"]
    live = _runs_via_mcp(env.cli_env())
    name = world["fail"].run_name
    assert _by_name(live, name)["failure_reason"] == "FIXTURE_BOOM_7"
    assert all("failure_reason" not in v for k, v in live.items() if v["status"] == "succeeded")
    index = tmp_path / "w" / "index.db"
    index.parent.mkdir()
    cli_env = pkg_env(ABF_PLATFORM_DB=index, ABF_PLATFORM_TOKENS=env.tokens)
    r = run_cli(["rebuild", str(world["ok_dir"]), str(world["fail_dir"])], env=cli_env)
    assert r.returncode == 0, r.stdout + r.stderr
    rebuilt = _runs_via_mcp(cli_env)
    assert all(k not in v for v in rebuilt.values() for k in _NOT_REBUILT)
    _same_runs(live, rebuilt)


def test_tc031_nextflows_records_win_over_a_damaged_index(world, tmp_path):
    # TC-031
    import sqlite3
    env = world["env"]
    before = _runs_via_mcp(env.cli_env())
    index = tmp_path / "damaged.db"
    shutil.copy(env.index, index)
    con = sqlite3.connect(str(index))
    con.execute("UPDATE runs SET final_status = NULL, ended_at = NULL, n_succeeded = 999, n_failed = 77")
    con.execute("DELETE FROM failed_tasks")
    con.commit()
    con.close()
    cli_env = pkg_env(ABF_PLATFORM_DB=index, ABF_PLATFORM_TOKENS=env.tokens)
    damaged = _runs_via_mcp(cli_env)
    assert any(v["tasks"]["succeeded"] == 999 for v in damaged.values()), "the damage did not take"
    r = run_cli(["rebuild", str(world["ok_dir"]), str(world["fail_dir"])], env=cli_env)
    assert r.returncode == 0, r.stdout + r.stderr
    _same_runs(before, _runs_via_mcp(cli_env))


def test_tc032_tokens_survive_a_rebuild(world, tmp_path):
    # TC-032
    from starlette.testclient import TestClient
    from abf_platform import receiver
    env = world["env"]
    index = tmp_path / "gone.db"  # there is no old index at all
    assert not index.exists()
    digest = all_files_digest(env.tokens)
    cli_env = pkg_env(ABF_PLATFORM_DB=index, ABF_PLATFORM_TOKENS=env.tokens)
    r = run_cli(["rebuild", str(world["ok_dir"]), str(world["fail_dir"])], env=cli_env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert all_files_digest(env.tokens) == digest, "rebuild touched the token file"
    client = TestClient(receiver.create_app(index, env.tokens))
    body = {"sessionId": "11111111-1111-1111-1111-111111111111", "runName": "after_rebuild", "projectName": "x",
            "instant": 1}
    resp = client.post("/trace/create", json=body, headers={"Authorization": basic_header(env.token)})
    assert resp.status_code < 300


def test_tc033_unusable_folders_are_named_and_counted(world, tmp_path):
    # TC-033
    missing = tmp_path / "does_not_exist"
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0)
    try:
        if os.access(locked, os.R_OK):
            pytest.fail("cannot make an unreadable folder here (running as root?): the case would prove nothing")
        index = tmp_path / "index.db"
        r = run_cli(["rebuild", str(missing), str(locked), str(world["ok_dir"])],
                    env=pkg_env(ABF_PLATFORM_DB=index, ABF_PLATFORM_TOKENS=tmp_path / "t.db"))
    finally:
        locked.chmod(0o700)
    out = r.stdout + r.stderr
    assert r.returncode != 0
    line_missing = [ln for ln in out.splitlines() if str(missing) in ln]
    line_locked = [ln for ln in out.splitlines() if str(locked) in ln]
    assert line_missing and re.search(r"skipp", line_missing[0], re.I) and re.search(r"exist|found", line_missing[0], re.I)
    assert line_locked and re.search(r"skipp", line_locked[0], re.I) and re.search(r"permission|read|access", line_locked[0], re.I)
    assert re.search(r"rebuilt\D+2\b", out, re.I) and re.search(r"skipped\D+2\b", out, re.I), out
    assert db_counts(index)["runs"] == 2


def test_tc034_a_killed_run_is_lost_before_and_after_a_rebuild(e2e_cfg, tmp_path):
    # TC-034
    import datetime as dt
    clock_offset = [0.0]
    env = Env(e2e_cfg, tmp_path, clock=lambda: time.time() + clock_offset[0])
    launch = tmp_path / "launch"
    proc = env.start_nf("slow", launch)
    try:
        wait_until(lambda: [b for _, _, b, _ in env.recorder.of_kind("progress") if b["progress"]["running"] >= 1],
                   timeout=90, what="a running task")
        time.sleep(1.2)
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=30)
        time.sleep(1.0)
        hist = history(launch)
        assert hist[-1]["status"] == "-", hist
        # live rule, three heartbeats and a second later
        (live_id,) = [r["id"] for r in status.list_runs(env.index, time.time())]
        assert status.get_run(env.index, live_id, time.time() + 3 * H + 1)["status"] == "lost"
        # rebuild into a fresh index
        index = tmp_path / "rebuilt.db"
        cli_env = pkg_env(ABF_PLATFORM_DB=index, ABF_PLATFORM_TOKENS=env.tokens)
        r = run_cli(["rebuild", str(launch)], env=cli_env)
        assert r.returncode == 0, r.stdout + r.stderr
        (v,) = _runs_via_mcp(cli_env).values()
        assert v["status"] == "lost"
        assert v["id"] == live_id
        # the last message time is the time of the last line of .nextflow.log
        last = (launch / ".nextflow.log").read_text().splitlines()[-1]
        m = re.match(r"([A-Z][a-z]{2})-(\d\d) (\d\d):(\d\d):(\d\d)\.\d+", last)
        assert m, last
        start = dt.datetime.fromtimestamp(_epoch(v["started_at"]))
        stamp = dt.datetime.strptime("%d %s %s %s:%s:%s" % (start.year, m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)),
                                     "%Y %b %d %H:%M:%S")
        assert abs(_epoch(v["last_message_at"]) - stamp.timestamp()) <= 1
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        env.stop()


# ---------------------------------------------------------------- abort-report-overwrite (the rendered nextflow.config)

_REPORT_CONFIG = ("report.enabled = true\nreport.file = 'pipeline_info/execution_report.html'\n"
                  "timeline.enabled = true\ntimeline.file = 'pipeline_info/execution_timeline.html'\n")


def _platform_config(user_text, with_block):
    """The nextflow.config the platform would write for a compute environment carrying user_text (or only that text)."""
    from test_launch_bundle import ce_snapshot, render
    if with_block:
        return render(ce=ce_snapshot(nextflowConfig=user_text))["files"]["nextflow.config"]
    return user_text


def _aborted_log(e2e_cfg, tmp_path, with_block):
    env = Env(e2e_cfg, tmp_path)
    launch = tmp_path / "launch"
    launch.mkdir()
    (launch / "nextflow.config").write_text(_platform_config(_REPORT_CONFIG, with_block))
    proc = env.start_nf("slow", launch)
    try:
        wait_until(lambda: [b for _, _, b, _ in env.recorder.of_kind("progress") if b["progress"]["running"] >= 1],
                   timeout=90, what="a running task")
        os.killpg(proc.pid, signal.SIGINT)   # the cancel: what scancel / Ctrl-C does to the head job
        proc.wait(timeout=120)
        time.sleep(1.0)
        return (launch / ".nextflow.log").read_text(errors="replace")
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        env.stop()


def test_abort_tc011_without_the_block_an_aborted_run_logs_report_file_already_exists(e2e_cfg, tmp_path):
    # TC-011: the teeth of TC-010 (the cancel really reaches the report writer a second time)
    log = _aborted_log(e2e_cfg, tmp_path, with_block=False)
    assert re.search(r"(Report|Timeline) file already exists", log), log[-3000:]


def test_abort_tc010_with_the_block_an_aborted_run_does_not_log_it(e2e_cfg, tmp_path):
    # TC-010
    log = _aborted_log(e2e_cfg, tmp_path, with_block=True)
    assert "already exists" not in log
    assert "report.overwrite" not in log and "timeline.overwrite" not in log


def test_abort_tc013_with_the_block_a_normal_run_still_writes_both_files(e2e_cfg, tmp_path):
    # TC-013
    env = Env(e2e_cfg, tmp_path)
    try:
        launch = tmp_path / "launch"
        launch.mkdir()
        (launch / "nextflow.config").write_text(_platform_config(_REPORT_CONFIG, True))
        p = env.run_nf("ok", launch)
        assert p.returncode == 0, p.stdout + p.stderr
        for name in ("execution_report.html", "execution_timeline.html"):
            f = launch / "pipeline_info" / name
            assert f.is_file() and f.stat().st_size > 0, name
        log = (launch / ".nextflow.log").read_text(errors="replace")
        assert not [ln for ln in log.splitlines() if " ERROR " in ln and re.search(r"report|timeline", ln, re.I)]
    finally:
        env.stop()
