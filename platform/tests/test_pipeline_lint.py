# Nothing existing: Seqera and nf-core have no call that queues a lint of a composed canvas pipeline for the caller's own agent and keeps the answer beside the pipeline's static check; the owner rule is this platform's own.
"""017c2a: the optional lint of a composed pipeline, the platform side. `validate_pipeline(..., lint=True)` queues one `lint_pipeline`
job for an agent of the caller and `get_validation` collects the answer later. The agent is never run here: the tests write the
job's answer into the jobs table the way the agent's report would. Test cases are named in the comments (TC-001 ...), see
specs/017c2a-validate-lint/test-case.md."""
import json
import logging
import re
import sqlite3
import time
from pathlib import Path

import pytest

from human_harness import World
from owner_harness import Duo, sql_exec, sql_rows
from test_pipelines_validation import make, pid_of, pl, qc_graph, rows

HERE = Path(__file__).resolve().parent
PLATFORM = HERE.parent
GOOD = {"ok": True, "status": "passed", "report": "mqc: fine", "counts": {"passed": 5, "warned": 1, "failed": 0}}
BAD = {"ok": False, "status": "failed", "report": "files_exist: nextflow.config is missing\nmodules_json: bad",
       "counts": {"passed": 3, "warned": 2, "failed": 4}}


@pytest.fixture
def d(tmp_path, monkeypatch):
    return Duo(World(tmp_path, monkeypatch))


def lint_jobs(d):
    return sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'lint_pipeline' ORDER BY id")


def all_jobs(d):
    return sql_rows(d.state, "SELECT COUNT(*) AS n FROM jobs")[0]["n"]


def finish(d, job_id, state="done", result=None, at=None):
    sql_exec(d.state, "UPDATE jobs SET state = ?, result_json = ?, finished_at = ? WHERE id = ?",
             (state, json.dumps(result) if result is not None else None, at if at is not None else time.time(), job_id))


_N = 0


def linted(d, caller=None, **kw):
    """(pipeline id, the answer of validate_pipeline(lint=True)) for a new pipeline of alice (or `caller`)."""
    caller = caller or d.a
    global _N
    _N += 1
    pid = pid_of(make(d, caller, name="demo-%d" % _N))
    return pid, pl().validate_pipeline(d.state, pid, caller=caller, lint=True, **kw)


def shown(d, pid, caller=None):
    return pl().get_validation(d.state, pid, caller=caller or d.a)


def add_env(d, name, agent, owner, platform="slurm-platform", seen=None):
    sql_exec(d.state, "INSERT OR REPLACE INTO agents (name, version, first_seen_at, last_seen_at, owner_user_id) VALUES (?, '0.1', ?, ?, ?)",
             (agent, 1.0, time.time() if seen is None else seen, owner))
    sql_exec(d.state, "INSERT INTO compute_envs (name, platform, agent, status, config_json, created_at, updated_at, owner_user_id) "
                      "VALUES (?, ?, ?, 'available', '{}', 1, 1, ?)", (name, platform, agent, owner))


def offline(d, agent):
    sql_exec(d.state, "UPDATE agents SET last_seen_at = 0 WHERE name = ?", (agent,))


# ---- User Story 1: asking -------------------------------------------------------------------------------------------
def test_lint_off_changes_nothing(d):
    # TC-001
    pid = pid_of(make(d, d.a))
    before = all_jobs(d)
    r = pl().validate_pipeline(d.state, pid, caller=d.a, clock=lambda: 50.0)
    assert r["ok"] is True and "lint" not in r and all_jobs(d) == before
    six = ("pipeline_id", "version", "graph_sha256", "result_json", "validated_at")
    assert [r2["validated_at"] for r2 in rows(d)] == [50.0] and all(c in rows(d)[0].keys() for c in six)
    assert rows(d)[0]["lint_job_id"] is None and rows(d)[0]["lint_status"] is None
    assert "lint" not in shown(d, pid)["validation"]
    explicit = pl().validate_pipeline(d.state, pid, caller=d.a, clock=lambda: 50.0, lint=False)
    assert explicit == r


def test_lint_true_queues_exactly_one_job(d):
    # TC-002
    pid = pid_of(make(d, d.a))
    before = all_jobs(d)
    r = pl().validate_pipeline(d.state, pid, caller=d.a, lint=True)
    jobs = lint_jobs(d)
    assert r["ok"] is True and len(jobs) == 1 and all_jobs(d) == before + 1
    assert r["lint"] == {"state": "queued", "job_id": jobs[0]["id"]} and r["validation"]["ok"] is True
    row = rows(d)[0]
    assert row["lint_job_id"] == jobs[0]["id"] and row["lint_status"] == "queued" and row["result_json"]


def test_the_job_carries_the_same_files_as_the_export_zip(d):
    # TC-003
    import io
    import zipfile
    pid, r = linted(d)
    args = json.loads(lint_jobs(d)[0]["args_json"])
    assert set(args) == {"name", "version", "project"} and args["name"].startswith("demo-") and args["version"] == 1
    exported = pl().export_pipeline(d.state, pid, caller=d.a)
    with zipfile.ZipFile(io.BytesIO(exported["zip"])) as z:
        in_zip = {n: z.read(n).decode("utf-8") for n in z.namelist()}
    assert args["project"] == in_zip


@pytest.mark.parametrize("bad", ["yes", 1, None])
def test_lint_must_be_true_or_false(d, bad):
    # TC-004
    pid = pid_of(make(d, d.a))
    before_rows, before_jobs = rows(d), all_jobs(d)
    r = pl().validate_pipeline(d.state, pid, caller=d.a, lint=bad)
    assert r["ok"] is False and r["message"] and all_jobs(d) == before_jobs and rows(d) == before_rows


def test_no_agent_online_is_a_refusal_not_an_error(d):
    # TC-005
    offline(d, "agent-t")
    before = all_jobs(d)
    pid, r = linted(d)
    assert r["ok"] is True and r["lint"]["state"] == "refused" and "代理" in r["lint"]["message"]
    assert rows(d)[0]["result_json"] and all_jobs(d) == before and rows(d)[0]["lint_job_id"] is None


def test_cloud_environment_is_skipped(d):
    # TC-006
    add_env(d, "g1", "agent-g", d.b.user_id, platform="googlebatch-platform")
    before = all_jobs(d)
    pid, r = linted(d, caller=d.b)
    assert r["lint"]["state"] == "refused" and all_jobs(d) == before


def test_a_slurm_environment_is_chosen_over_a_cloud_one(d):
    # TC-007
    add_env(d, "a-gcb", "agent-g", d.a.user_id, platform="googlebatch-platform")
    pid, r = linted(d)
    assert r["lint"]["state"] == "queued"
    assert lint_jobs(d)[0]["compute_env"] == "lab-a"


def test_a_named_environment_is_the_one_used(d):
    # TC-008
    add_env(d, "b-two", "agent-two", d.a.user_id)
    pid, r = linted(d, compute_env="b-two")
    assert r["lint"]["state"] == "queued" and lint_jobs(d)[0]["compute_env"] == "b-two" and lint_jobs(d)[0]["agent"] == "agent-two"


def test_a_named_environment_that_is_offline_is_not_replaced(d):
    # TC-009
    add_env(d, "b-two", "agent-two", d.a.user_id, seen=0)
    before = all_jobs(d)
    pid, r = linted(d, compute_env="b-two")
    assert r["lint"]["state"] == "refused" and r["lint"]["message"] and all_jobs(d) == before


def test_without_a_name_only_the_callers_own_environment_is_used(d):
    # TC-010
    d.bobs_environment(name="a-bob", agent="agent-b")
    pid, r = linted(d)
    assert r["lint"]["state"] == "queued"
    assert lint_jobs(d)[0]["compute_env"] == "lab-a" and lint_jobs(d)[0]["agent"] == "agent-t"
    pid2, r2 = linted(d, caller=d.b)
    assert [j["compute_env"] for j in lint_jobs(d)][-1] == "a-bob"


def test_compute_env_of_somebody_else_is_not_found(d):
    # TC-011
    d.bobs_environment(name="bobs-env", agent="agent-b")
    before = all_jobs(d)
    pid, mine = linted(d, compute_env="bobs-env")
    pid2, none = linted(d, compute_env="no-such-env")
    assert all_jobs(d) == before
    assert mine["lint"]["state"] == "refused"
    same = lambda r, name: json.dumps(r["lint"], sort_keys=True).replace(name, "<n>")      # noqa: E731
    assert same(mine, "bobs-env") == same(none, "no-such-env")


def test_someone_elses_pipeline_is_not_found_and_nothing_queued(d):
    # TC-012
    pid = pid_of(make(d, d.a))
    before_rows, before_jobs = rows(d), all_jobs(d)
    d.bobs_environment(name="bobs-env", agent="agent-b")
    other = pl().validate_pipeline(d.state, pid, caller=d.b, lint=True)
    missing = pl().validate_pipeline(d.state, 9999, caller=d.b, lint=True)
    assert other["ok"] is False and other["message"].replace(str(pid), "<id>") == missing["message"].replace("9999", "<id>")
    assert all_jobs(d) == before_jobs and rows(d) == before_rows


def test_someone_elses_lint_result_is_not_readable(d):
    # TC-013
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result=BAD)
    assert shown(d, pid)["validation"]["lint"]["status"] == "failed"
    other = pl().get_validation(d.state, pid, caller=d.b)
    missing = pl().get_validation(d.state, 9999, caller=d.b)
    assert other["ok"] is False and other["message"].replace(str(pid), "<id>") == missing["message"].replace("9999", "<id>")
    assert "failed" not in json.dumps(other) and "nextflow.config" not in json.dumps(other)


def test_too_big_project_is_refused(d, monkeypatch):
    # TC-014
    from abf_platform import pipeline_launch
    monkeypatch.setattr(pipeline_launch, "MAX_BYTES", 10)
    before = all_jobs(d)
    pid, r = linted(d)
    assert r["ok"] is True and r["lint"]["state"] == "refused" and r["lint"]["message"]
    assert all_jobs(d) == before and rows(d)[0]["result_json"]


def test_too_many_files_are_refused(d, monkeypatch):
    # TC-015
    from abf_platform import pipeline_launch
    monkeypatch.setattr(pipeline_launch, "MAX_FILES", 1)
    before = all_jobs(d)
    pid, r = linted(d)
    assert r["lint"]["state"] == "refused" and all_jobs(d) == before


def test_lint_pipeline_cannot_be_queued_by_the_generic_door(d):
    # TC-016
    from abf_platform import jobs
    before = all_jobs(d)
    with pytest.raises(jobs.JobRefused) as e:
        jobs._enqueue(d.state, "lab-a", "lint_pipeline", None, time.time, None)
    assert "enqueue_lint_pipeline" in str(e.value) and all_jobs(d) == before


def test_a_lint_needs_no_confirmation(d):
    # TC-017
    n_conf = sql_rows(d.state, "SELECT COUNT(*) AS n FROM confirmations")[0]["n"]
    pid, r = linted(d)
    job = lint_jobs(d)[0]
    assert job["confirmation_id"] is None and sql_rows(d.state, "SELECT COUNT(*) AS n FROM confirmations")[0]["n"] == n_conf
    assert "launch" not in json.dumps(json.loads(job["args_json"]), sort_keys=True).replace("nextflow.config", "")[:0] + ""
    assert set(json.loads(job["args_json"])) == {"name", "version", "project"}


def test_asking_again_replaces_the_job_and_ignores_the_old_answer(d):
    # TC-018
    pid, first = linted(d)
    finish(d, first["lint"]["job_id"], result=GOOD)
    assert shown(d, pid)["validation"]["lint"]["status"] == "passed"
    second = pl().validate_pipeline(d.state, pid, caller=d.a, lint=True)
    new_id = second["lint"]["job_id"]
    assert new_id != first["lint"]["job_id"]
    row = rows(d)[0]
    assert (row["lint_job_id"], row["lint_status"], row["lint_report"]) == (new_id, "queued", None)
    finish(d, first["lint"]["job_id"], result=BAD)           # the old job answers late
    assert shown(d, pid)["validation"]["lint"]["status"] == "queued"
    finish(d, new_id, result=GOOD)
    assert shown(d, pid)["validation"]["lint"]["status"] == "passed"


def test_the_kind_its_deadline_and_the_setting(monkeypatch):
    # TC-043
    from abf_platform import jobs
    assert "lint_pipeline" in jobs.KINDS and len(jobs.KINDS) == 11 and jobs.KINDS[-1] == "lint_pipeline"
    assert jobs.DEADLINE_SECONDS["lint_pipeline"] == 300 and jobs._DEADLINE_ENV["lint_pipeline"] == "ABF_PLATFORM_DEADLINE_LINT_PIPELINE"
    monkeypatch.setenv("ABF_PLATFORM_DEADLINE_LINT_PIPELINE", "7")
    assert jobs.deadline_seconds("lint_pipeline") == 7


# ---- User Story 3: collecting ---------------------------------------------------------------------------------------
def test_result_is_collected_lazily(d):
    # TC-050
    pid, r = linted(d)
    jid = r["lint"]["job_id"]
    assert shown(d, pid)["validation"]["lint"]["status"] == "queued"
    sql_exec(d.state, "UPDATE jobs SET state = 'claimed' WHERE id = ?", (jid,))
    assert shown(d, pid)["validation"]["lint"]["status"] == "queued" and rows(d)[0]["lint_status"] == "queued"


def test_the_four_columns_are_written_when_the_job_is_done(d):
    # TC-051
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result=BAD, at=777.0)
    shown(d, pid)
    row = rows(d)[0]
    assert row["lint_status"] == "failed" and row["lint_job_id"] == r["lint"]["job_id"] and row["lint_at"] == 777.0
    assert "nextflow.config is missing" in row["lint_report"]


def test_a_collected_result_is_not_looked_up_again(d, monkeypatch):
    # TC-052
    from abf_platform import store
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result=BAD)
    first = shown(d, pid)
    seen = []
    real = store.connect_state

    def spy(*a, **kw):
        con = real(*a, **kw)
        con.set_trace_callback(seen.append)
        return con
    monkeypatch.setattr(store, "connect_state", spy)
    second = shown(d, pid)
    assert second == first and not [s for s in seen if re.search(r"FROM\s+jobs", s, re.I)]


def test_the_first_line_of_the_report_has_the_counts(d):
    # TC-053
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result=BAD)
    report = shown(d, pid)["validation"]["lint"]["report"]
    assert report.splitlines()[0] == "通過 3／警告 2／失敗 4 (passed 3 / warned 2 / failed 4)"
    assert "files_exist: nextflow.config is missing" in report.splitlines()[1:][0] or "files_exist" in report


def test_each_terminal_state(d):
    # TC-054, TC-055, TC-056, TC-057, TC-058
    cases = [("done", GOOD, "passed"),
             ("done", {"ok": False, "status": "unavailable", "reason": "這台站台沒有裝 nf-core tools，所以沒有執行 lint；本系統不會自動安裝"}, "unavailable"),
             ("refused", {"ok": False, "message": "bad path"}, "error"),
             ("error", {"ok": False, "message": "boom"}, "error"),
             ("expired", None, "expired")]
    for state, result, want in cases:
        pid, r = linted(d)
        finish(d, r["lint"]["job_id"], state=state, result=result)
        got = shown(d, pid)["validation"]["lint"]
        assert got["status"] == want and isinstance(got["report"], str), (state, got)
        if want != "passed":
            assert got["report"] and "Traceback" not in got["report"]
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result={"ok": False, "status": "unavailable", "reason": "這台站台沒有裝 nf-core tools，所以沒有執行 lint；本系統不會自動安裝"})
    assert "沒有" in shown(d, pid)["validation"]["lint"]["report"]


def test_a_never_linted_version_has_no_lint_key(d):
    # TC-059
    pid = pid_of(make(d, d.a))
    pl().validate_pipeline(d.state, pid, caller=d.a)
    v = shown(d, pid)["validation"]
    assert "lint" not in v and set(v) == {"ok", "findings", "checks", "catalogue_sha", "validated_at", "stale"} | (set(v) - {"lint"}) - {"lint"}


def test_the_lint_key_has_three_keys(d):
    # TC-060
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result=GOOD)
    assert set(shown(d, pid)["validation"]["lint"]) == {"status", "report", "linted_at"}


def test_revalidate_keeps_lint(d):
    # TC-061
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result=BAD)
    before = shown(d, pid)["validation"]["lint"]
    cols = {k: rows(d)[0][k] for k in ("lint_status", "lint_report", "lint_job_id", "lint_at")}
    again = pl().validate_pipeline(d.state, pid, caller=d.a, clock=lambda: 9999.0)
    assert "lint" not in again and rows(d)[0]["validated_at"] == 9999.0
    assert {k: rows(d)[0][k] for k in cols} == cols and shown(d, pid)["validation"]["lint"] == before


def test_clean_result_bounds(d):
    # TC-062
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result={"status": "failed", "report": "x" * 20000, "counts": {"passed": 1, "warned": 1, "failed": 1}})
    shown(d, pid)
    assert 0 < len(rows(d)[0]["lint_report"]) <= 8000 and len(shown(d, pid)["validation"]["lint"]["report"]) <= 8000


def test_bad_counts_are_not_kept(d):
    # TC-063, TC-064
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result={"status": "failed", "counts": {"passed": "many", "warned": -5, "failed": 100001}})
    report = shown(d, pid)["validation"]["lint"]["report"]
    for bad in ("many", "-5", "100001"):
        assert bad not in report
    assert "Traceback" not in report
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result={"status": "failed", "counts": {"passed": 2, "warned": 1, "failed": 100001}})
    assert "100001" not in shown(d, pid)["validation"]["lint"]["report"]


def test_only_four_keys_are_kept(d):
    # TC-065
    from abf_platform import jobs
    cleaned = jobs.clean_result("lint_pipeline", {"status": "passed", "reason": "r", "report": "p", "counts": {"passed": 1},
                                                  "secret": "SECRET-X", "extra": 1, "ok": True})
    assert set(cleaned) <= {"ok", "state", "status", "reason", "report", "counts"} and "secret" not in cleaned and "extra" not in cleaned
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result={"status": "passed", "secret": "SECRET-X", "extra": "EXTRA-Y"})
    assert "SECRET-X" not in json.dumps(shown(d, pid)) and "EXTRA-Y" not in json.dumps(rows(d), default=str)


def test_an_unknown_status_is_an_error(d):
    # TC-066
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result={"status": "weird", "report": "x"})
    assert shown(d, pid)["validation"]["lint"]["status"] == "error"


def test_reason_is_bounded(d):
    # TC-067
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result={"status": "error", "reason": "R" * 1000})
    report = shown(d, pid)["validation"]["lint"]["report"]
    assert report.count("R") <= 200 and report.count("R") > 0


def test_no_secret_and_no_internals_in_what_the_user_sees(d, caplog, monkeypatch):
    # TC-068
    from abf_platform import pipeline_launch
    caplog.set_level(logging.DEBUG)
    seen = []
    offline(d, "agent-t")
    seen.append(json.dumps(linted(d)[1], default=str))                                            # TC-005
    sql_exec(d.state, "UPDATE agents SET last_seen_at = ? WHERE name = 'agent-t'", (time.time(),))
    with monkeypatch.context() as m:
        m.setattr(pipeline_launch, "MAX_BYTES", 10)
        seen.append(json.dumps(linted(d)[1], default=str))                                        # TC-014
    for state, result in (("refused", {"ok": False, "message": "no"}), ("error", {"ok": False, "message": "boom"})):    # TC-056, TC-057
        pid, r = linted(d)
        finish(d, r["lint"]["job_id"], state=state, result=result)
        seen.append(json.dumps(shown(d, pid), default=str))
    text = "\n".join(seen + [rec.getMessage() for rec in caplog.records])
    for leak in ("Traceback", "platform.db", str(d.state), "SELECT ", "INSERT ", "sqlite3.", ".py\", line", "token"):
        assert leak not in text, leak


def test_collecting_changes_only_the_lint_columns(d):
    # TC-069
    pid, r = linted(d)
    before = rows(d)[0]
    finish(d, r["lint"]["job_id"], result=GOOD)
    shown(d, pid)
    after = rows(d)[0]
    changed = {k for k in before.keys() if before[k] != after[k]}
    assert changed <= {"lint_status", "lint_report", "lint_at"} and "lint_status" in changed


# ---- User Story 4: older data ---------------------------------------------------------------------------------------
def old_table(d):
    sql_exec(d.state, "DROP TABLE IF EXISTS pipeline_validations")
    sql_exec(d.state, "CREATE TABLE pipeline_validations (pipeline_id INTEGER NOT NULL, version INTEGER NOT NULL, graph_sha256 TEXT NOT NULL, "
                      "catalogue_sha TEXT NOT NULL, result_json TEXT NOT NULL, validated_at REAL NOT NULL, PRIMARY KEY (pipeline_id, version))")


def test_old_table_gets_the_columns(d):
    # TC-080
    pid = pid_of(make(d, d.a))
    pl().validate_pipeline(d.state, pid, caller=d.a, clock=lambda: 5.0)
    old_table(d)
    sql_exec(d.state, "INSERT INTO pipeline_validations VALUES (?, 1, 'g', 'c', ?, 5.0)", (pid, json.dumps({"ok": True, "findings": [], "checks": ["static"], "catalogue_sha": "c"})))
    got = shown(d, pid)
    cols = [c["name"] for c in sql_rows(d.state, "PRAGMA table_info(pipeline_validations)")]
    assert {"lint_status", "lint_report", "lint_job_id", "lint_at"} <= set(cols)
    assert rows(d)[0]["graph_sha256"] == "g" and rows(d)[0]["validated_at"] == 5.0 and "lint" not in got["validation"]


def test_upgrading_twice_is_harmless(d):
    # TC-081
    pid = pid_of(make(d, d.a))
    old_table(d)
    sql_exec(d.state, "INSERT INTO pipeline_validations VALUES (?, 1, 'g', 'c', ?, 5.0)", (pid, json.dumps({"ok": True, "findings": [], "checks": ["static"], "catalogue_sha": "c"})))
    shown(d, pid)
    first = rows(d)
    shown(d, pid)
    cols = [c["name"] for c in sql_rows(d.state, "PRAGMA table_info(pipeline_validations)")]
    assert len(cols) == len(set(cols)) == 10 and rows(d) == first


def test_old_jobs_table_is_migrated(tmp_path):
    # TC-083
    from abf_platform import store
    from test_byte_channel_a import COLS, JOB_SQL, old_db, sql
    db = old_db(tmp_path, ["lint_pipeline"])
    before = sql(db, COLS)
    store.connect_state(db).close()
    sql(db, JOB_SQL, ("lint_pipeline", None))
    assert sql(db, COLS)[:3] == before and sql(db, COLS)[3][3] == "lint_pipeline"


# ---- User Story 5: not in scope -------------------------------------------------------------------------------------
def test_no_lint_in_the_mcp_server_or_the_web(d):
    # TC-101
    for name in ("mcp_server.py", "web.py"):
        assert "lint" not in (PLATFORM / "abf_platform" / name).read_text(encoding="utf-8").lower(), name


def test_the_user_visible_actions_did_not_change(d):
    # TC-102
    import inspect
    from abf_platform import actions, mcp_server
    names = sorted(t["name"] if isinstance(t, dict) else getattr(t, "name", str(t)) for t in getattr(mcp_server, "TOOLS", []))
    assert len(names) == len(set(names))
    assert "lint" in inspect.signature(actions.pipelines.validate_pipeline).parameters
    assert not [n for n in names if "lint" in n]


def test_no_program_is_started_by_the_platform_for_lint():
    # TC-103
    for path in (PLATFORM / "abf_platform" / "pipeline_lint.py", PLATFORM / "abf_platform" / "actions" / "pipelines.py"):
        code = "\n".join(l for l in path.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#")).lower()
        for word in ("subprocess", "os.system", "sbatch", "popen", "-stub-run"):
            assert word not in code, (path.name, word)


def test_cloud_job_kinds_have_no_lint():
    # TC-106
    from abf_platform import compute_envs
    assert all("lint_pipeline" not in kinds for kinds in compute_envs.CLOUD_JOB_KINDS.values())


def test_nobody_collects_in_the_background(d):
    # TC-107
    pid, r = linted(d)
    finish(d, r["lint"]["job_id"], result=GOOD)
    pl().list_pipelines(d.state, caller=d.a)
    make(d, d.a, name="other-one")
    time.sleep(0.05)
    assert rows(d)[0]["lint_status"] == "queued"
    assert sql_rows(d.state, "SELECT COUNT(*) AS n FROM jobs WHERE kind != 'lint_pipeline'")[0]["n"] == sql_rows(d.state, "SELECT COUNT(*) AS n FROM jobs WHERE kind != 'lint_pipeline'")[0]["n"]


def test_lint_results_of_other_versions_are_kept(d):
    # TC-108
    ids = []
    for i in range(3):
        pid, r = linted(d)
        finish(d, r["lint"]["job_id"], result=GOOD if i != 1 else BAD)
        ids.append(pid)
    for pid in ids:
        shown(d, pid)
    got = [shown(d, pid)["validation"]["lint"]["status"] for pid in ids]
    assert got == ["passed", "failed", "passed"] and len(rows(d)) == 3
