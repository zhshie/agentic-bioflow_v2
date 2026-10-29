# Nothing existing: tests of the pipeline_files kind in the state database and the job queue; no earlier test knows this kind.
"""release-lookup-job, the platform side of the queue (Q-01 to Q-18): the database lets the kind in (with a migration for an older
file), the queue takes it without a confirmation, the agent claims it, and the answer is cleaned to a small allow-list.
Test cases are named in the comments (TC-049 ...). Everything is done at the abf_platform layer with a database and a fake clock."""
import json
import os
import re
import sqlite3
import subprocess
from pathlib import Path

import pytest

from helpers import Clock, PLATFORM_DIR, REPO_ROOT, all_files_digest

T0 = 1_800_000_000.0
EIGHT = ["preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records", "read_task_log", "clean_work", "put_upload"]
PARTS3 = ["schema", "schema_input", "diagram"]


@pytest.fixture
def clock():
    return Clock(T0)


@pytest.fixture
def db(tmp_path):
    from abf_platform import store
    path = tmp_path / "platform.db"
    store.connect_state(path).close()
    return path


def sql(db, text, args=()):
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        with con:
            return con.execute(text, args).fetchall()
    finally:
        con.close()


def add_agent(db, name="a1", owner=1, seen=T0):
    sql(db, "INSERT OR REPLACE INTO agents (name, version, first_seen_at, last_seen_at, owner_user_id) VALUES (?, '0.1', ?, ?, ?)",
        (name, seen, seen, owner))


def add_ce(db, name="ce1", platform="slurm-platform", status="available", agent="a1", owner=1):
    sql(db, "INSERT INTO compute_envs (name, platform, agent, status, config_json, created_at, updated_at, owner_user_id) "
            "VALUES (?, ?, ?, ?, '{}', 1, 1, ?)", (name, platform, agent, status, owner))


def one_env(db, owner=1):
    add_agent(db, "a1", owner)
    add_ce(db, "ce1", owner=owner)


def count_jobs(db, kind="pipeline_files"):
    return sql(db, "SELECT COUNT(*) AS n FROM jobs WHERE kind = ?", (kind,))[0]["n"]


def kinds_of(con):
    text = con.execute("SELECT sql FROM sqlite_master WHERE name = 'jobs'").fetchone()[0]
    m = re.search(r"kind TEXT NOT NULL CHECK \(kind IN \(([^)]*)\)\)", text)
    return re.findall(r"'([a-z_]+)'", m.group(1))


JOB_SQL = ("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
           "VALUES ('a1', 'x', ?, '{}', 'queued', 1, 2, ?)")


def new_con(tmp_path):
    from abf_platform import store
    return store.connect_state(tmp_path / "new.db")


# ---- the database -----------------------------------------------------------------------------------------------------

def test_tc049_the_check_list_ends_with_pipeline_files(tmp_path):
    # TC-049
    con = new_con(tmp_path)
    kinds = kinds_of(con)
    assert kinds[-2:] == ["pipeline_files", "read_run_file"] and kinds.count("pipeline_files") == 1 and kinds[:len(EIGHT)] == EIGHT      # results-files: read_run_file is the tenth, last kind
    con.close()


def test_tc050_look_alike_kinds_are_refused(tmp_path):
    # TC-050
    con = new_con(tmp_path)
    for kind in ("pipeline_file", "pipeline_files ", "PIPELINE_FILES", "tags", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(JOB_SQL, (kind, None))
    assert con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    con.close()


def test_tc051_tc052_the_kind_needs_no_confirmation_and_the_others_still_do(tmp_path):
    # TC-051, TC-052
    con = new_con(tmp_path)
    con.execute(JOB_SQL, ("pipeline_files", None))
    for kind in ("launch_nextflow", "cancel_run", "clean_work"):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(JOB_SQL, (kind, None))
    con.close()


def test_tc053_the_confirmed_kinds_are_the_same_three():
    # TC-053
    from abf_platform import jobs
    assert jobs.CONFIRMED == {"launch_nextflow": "launch", "cancel_run": "cancel", "clean_work": "clean_work"}


def make_older(path, cut=(", 'pipeline_files'",)):
    """A platform.db whose jobs table lacks the new kind (and whatever else `cut` names), with three rows."""
    from abf_platform import store
    store.connect_state(path).close()
    ddl = store._JOBS_TABLE % {"name": "jobs"}
    for piece in cut:
        ddl = ddl.replace(piece, "")
    raw = sqlite3.connect(str(path))
    raw.execute("DROP TABLE jobs")
    raw.execute(ddl)
    for i, kind in enumerate(("preflight", "list_site_files", "fetch_run_records")):
        raw.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, claimed_at, finished_at, result_json) "
                    "VALUES ('a1', 'lab-a', ?, ?, 'done', ?, ?, 5.5, 6.5, '{\"ok\": true}')", (kind, json.dumps({"n": i}), 1.0 + i, 2.0 + i))
    raw.execute("DELETE FROM sqlite_sequence WHERE name = 'jobs'")
    raw.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('jobs', 41)")
    raw.commit()
    raw.close()
    return path


def rows(path):
    con = sqlite3.connect(str(path))
    try:
        return con.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    finally:
        con.close()


def count_copies(monkeypatch):
    from abf_platform import store
    seen = []
    monkeypatch.setattr(store, "_migration_step", lambda step: seen.append(step))
    return seen


def test_tc054_an_older_table_is_upgraded_with_its_rows_and_counter(tmp_path, monkeypatch):
    # TC-054
    from abf_platform import store
    path = make_older(tmp_path / "platform.db")
    before = rows(path)
    con = store.connect_state(path)
    assert rows(path) == before
    assert kinds_of(con)[-2:] == ["pipeline_files", "read_run_file"]
    con.execute(JOB_SQL, ("pipeline_files", None))
    assert con.execute("SELECT MAX(id) FROM jobs").fetchone()[0] == 42
    con.close()


def test_tc055_the_upgraded_table_still_refuses_other_words(tmp_path):
    # TC-055
    from abf_platform import store
    con = store.connect_state(make_older(tmp_path / "platform.db"))
    for kind in ("rm", "launch", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(JOB_SQL, (kind, None))
    con.close()


def test_tc056_it_is_rebuilt_once(tmp_path, monkeypatch):
    # TC-056
    from abf_platform import store
    path = make_older(tmp_path / "platform.db")
    steps = count_copies(monkeypatch)
    store.connect_state(path).close()
    assert steps.count("copied") == 1
    store.connect_state(path).close()
    assert steps.count("copied") == 1


def test_tc057_tc058_a_failure_in_the_middle_changes_nothing_and_the_next_open_works(tmp_path, monkeypatch):
    # TC-057, TC-058
    from abf_platform import store
    path = make_older(tmp_path / "platform.db")
    before = rows(path)

    def boom(step):
        raise RuntimeError("injected")

    monkeypatch.setattr(store, "_migration_step", boom)
    with pytest.raises(RuntimeError):
        store.connect_state(path)
    chk = sqlite3.connect(str(path))
    assert "pipeline_files" not in chk.execute("SELECT sql FROM sqlite_master WHERE name = 'jobs'").fetchone()[0]
    assert not chk.execute("SELECT 1 FROM sqlite_master WHERE name = 'jobs_new'").fetchall()
    chk.close()
    assert rows(path) == before
    monkeypatch.undo()
    con = store.connect_state(path)
    assert kinds_of(con)[-2:] == ["pipeline_files", "read_run_file"] and rows(path) == before
    con.close()


def test_tc059_a_table_without_clean_work_is_upgraded_in_one_go(tmp_path, monkeypatch):
    # TC-059
    from abf_platform import store
    path = make_older(tmp_path / "platform.db", cut=(", 'pipeline_files'", ", 'put_upload'", ", 'clean_work'"))
    steps = count_copies(monkeypatch)
    con = store.connect_state(path)
    assert steps.count("copied") == 1
    assert kinds_of(con)[-2:] == ["pipeline_files", "read_run_file"] and {"clean_work", "put_upload"} <= set(kinds_of(con))
    con.execute(JOB_SQL, ("pipeline_files", None))
    con.close()


# ---- the deadlines and constants ----------------------------------------------------------------------------------------

def test_tc060_the_kind_is_last_in_kinds():
    # TC-060
    from abf_platform import jobs
    assert jobs.KINDS.count("pipeline_files") == 1 and jobs.KINDS[-2:] == ("pipeline_files", "read_run_file")
    assert [k for k in jobs.KINDS if k != "pipeline_files"][:len(EIGHT)] == EIGHT


def test_tc061_tc062_the_deadline(monkeypatch):
    # TC-061, TC-062
    from abf_platform import jobs
    monkeypatch.delenv("ABF_PLATFORM_DEADLINE_PIPELINE_FILES", raising=False)
    assert jobs.deadline_seconds("pipeline_files") == 90
    monkeypatch.setenv("ABF_PLATFORM_DEADLINE_PIPELINE_FILES", "7")
    assert jobs.deadline_seconds("pipeline_files") == 7
    for bad in ("abc", "0", "-5"):
        monkeypatch.setenv("ABF_PLATFORM_DEADLINE_PIPELINE_FILES", bad)
        assert jobs.deadline_seconds("pipeline_files") == 90


def test_tc063_the_cache_constants():
    # TC-063
    from abf_platform import jobs
    assert jobs.TAGS_CACHE_SECONDS == 86400 and jobs.TAGS_CACHE_FILE == "release-tags.json"
    assert jobs.PF_RETRY_SECONDS == 60


# ---- queueing ------------------------------------------------------------------------------------------------------------------

def test_tc064_tc065_a_job_is_queued_without_a_confirmation(db, clock):
    # TC-064, TC-065
    from abf_platform import jobs
    one_env(db)
    jid = jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, clock=clock, caller_user_id=1)
    row = sql(db, "SELECT * FROM jobs WHERE id = ?", (jid,))[0]
    assert row["kind"] == "pipeline_files" and row["state"] == "queued" and row["confirmation_id"] is None
    assert row["deadline_at"] == T0 + 90 and row["compute_env"] == "ce1" and row["agent"] == "a1"
    args = json.loads(row["args_json"])
    assert set(args) == {"repo", "revision", "parts"} and args == {"repo": "nf-core/ampliseq", "revision": "2.18.0", "parts": PARTS3}


def test_a_tags_job_has_a_null_revision_and_parts_are_put_in_the_standard_order(db, clock):
    # TC-065 (the shape for tags), TC-100 (the standard order)
    from abf_platform import jobs
    one_env(db)
    a = jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", None, ["tags"], clock=clock)
    b = jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", ["diagram", "schema"], clock=clock)
    assert json.loads(sql(db, "SELECT args_json FROM jobs WHERE id = ?", (a,))[0][0]) == {"repo": "nf-core/ampliseq", "revision": None, "parts": ["tags"]}
    assert json.loads(sql(db, "SELECT args_json FROM jobs WHERE id = ?", (b,))[0][0])["parts"] == ["schema", "diagram"]


BAD_ARGS = [
    ("", "2.18.0", ["schema"]), ("../x", "2.18.0", ["schema"]), ("a/b/c", "2.18.0", ["schema"]), ("./x", "2.18.0", ["schema"]),
    ("x/.", "2.18.0", ["schema"]), ("nf core/x", "2.18.0", ["schema"]), ("nf-core/ampliseq?x=1", "2.18.0", ["schema"]), (5, "2.18.0", ["schema"]),
    ("ampliseq", "2.18.0", ["schema"]), ("nf-core/ampliseq", "master", ["schema"]), ("nf-core/ampliseq", "3.0.0dev", ["schema"]),
    ("nf-core/ampliseq", None, ["schema"]), ("nf-core/ampliseq", "", ["schema"]), ("nf-core/ampliseq", "A" * 40, ["schema"]),
    ("nf-core/ampliseq", "2.18.0", []), ("nf-core/ampliseq", "2.18.0", ["x"]), ("nf-core/ampliseq", "2.18.0", ["schema", "schema"]),
    ("nf-core/ampliseq", "2.18.0", "schema"), ("nf-core/ampliseq", "2.18.0", None),
    (None, None, ["schema"]), ("nf-core/ampliseq", None, ["catalogue"]), (None, "2.18.0", ["catalogue"]), (None, None, ["catalogue", "schema"]),
]


@pytest.mark.parametrize("repo,revision,parts", BAD_ARGS)
def test_tc066_bad_arguments_queue_nothing(db, clock, repo, revision, parts):
    # TC-066
    from abf_platform import jobs
    one_env(db)
    with pytest.raises(jobs.JobRefused):
        jobs.enqueue_pipeline_files(db, repo, revision, parts, clock=clock)
    assert count_jobs(db) == 0


def test_tc067_tags_with_a_revision_is_refused(db, clock):
    # TC-067
    from abf_platform import jobs
    one_env(db)
    with pytest.raises(jobs.JobRefused):
        jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", ["tags"], clock=clock)
    with pytest.raises(jobs.JobRefused):
        jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", None, ["schema", "tags"], clock=clock)
    assert count_jobs(db) == 0


def alice_world(db):
    add_agent(db, "ag-a", 1, seen=T0 - 100000)      # offline
    add_agent(db, "ag-b", 1)
    add_agent(db, "ag-c", 1)
    add_agent(db, "ag-d", 1)
    add_agent(db, "ag-x", 2)
    add_ce(db, "ce-a", agent="ag-a", owner=1)
    add_ce(db, "ce-b", agent="ag-b", owner=1)
    add_ce(db, "ce-c", agent="ag-c", owner=1, status="creating")
    add_ce(db, "ce-d", agent="ag-d", owner=1, status="disabled")
    add_ce(db, "ce-x", agent="ag-x", owner=2)


def chosen(db, clock, caller=1, compute_env=None):
    from abf_platform import jobs
    jid = jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", ["schema"], clock=clock, caller_user_id=caller, compute_env=compute_env)
    return sql(db, "SELECT compute_env FROM jobs WHERE id = ?", (jid,))[0][0]


def test_tc068_tc069_the_first_online_environment_of_the_caller_is_used(db, clock):
    # TC-068, TC-069
    alice_world(db)
    assert chosen(db, clock, caller=1) == "ce-b"
    sql(db, "UPDATE agents SET last_seen_at = ? WHERE name = 'ag-b'", (T0 - 100000,))
    assert chosen(db, clock, caller=1) == "ce-c"        # an environment that was just made and never checked can be used
    assert chosen(db, clock, caller=2) == "ce-x"


def test_tc070_the_local_terminal_may_use_any_environment(db, clock):
    # TC-070
    add_agent(db, "ag-x", 2)
    add_ce(db, "ce-x", agent="ag-x", owner=2)
    assert chosen(db, clock, caller=None) == "ce-x"


def test_tc071_no_environment_is_a_plain_refusal(db, clock):
    # TC-071
    from abf_platform import jobs
    add_agent(db, "ag-x", 2)
    add_ce(db, "ce-x", agent="ag-x", owner=2)
    add_agent(db, "ag-d", 1)
    add_ce(db, "ce-d", agent="ag-d", owner=1, status="disabled")
    with pytest.raises(jobs.JobRefused) as e:
        jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", ["schema"], clock=clock, caller_user_id=1)
    text = str(e.value)
    assert "no online agent" in text and "沒有在線的代理" in text and "station" not in text and "ssh" not in text
    assert count_jobs(db) == 0


def test_tc072_somebody_elses_environment_answers_like_a_missing_one(db, clock):
    # TC-072
    from abf_platform import jobs
    alice_world(db)
    with pytest.raises(jobs.JobRefused) as other:
        jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", ["schema"], clock=clock, caller_user_id=1, compute_env="ce-x")
    with pytest.raises(jobs.JobRefused) as missing:
        jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", ["schema"], clock=clock, caller_user_id=1, compute_env="ce-nope")
    assert str(other.value).replace("ce-x", "NAME") == str(missing.value).replace("ce-nope", "NAME")
    assert count_jobs(db) == 0


def test_tc073_tc074_a_google_batch_environment_takes_this_kind_only_of_the_read_kinds(db, clock):
    # TC-073, TC-074
    from abf_platform import jobs
    add_agent(db, "ag-g", 1)
    add_ce(db, "gcb1", platform="googlebatch-platform", agent="ag-g", owner=1)
    assert chosen(db, clock, caller=1) == "gcb1"
    for kind in ("list_site_files", "fetch_run_records", "read_task_log"):
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(db, "gcb1", kind, clock=clock)


def test_tc075_tc076_the_agent_claims_the_job_once(db, clock):
    # TC-075, TC-076
    from abf_platform import jobs
    one_env(db)
    add_agent(db, "a2", 1)
    jid = jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, clock=clock, caller_user_id=1)
    assert jobs.claim(db, "a2", clock) is None
    out = jobs.claim(db, "a1", clock)
    assert out["id"] == jid and out["kind"] == "pipeline_files" and "confirmation" not in out and "run_token" not in out
    assert out["remaining"] <= 90
    assert sql(db, "SELECT state FROM jobs WHERE id = ?", (jid,))[0][0] == "claimed"
    assert jobs.claim(db, "a1", clock) is None


# ---- cleaning the answer ----------------------------------------------------------------------------------------------------

def good_result():
    return {"ok": True, "repo": "nf-core/ampliseq", "revision": "2.18.0", "message": "read 5 part(s)",
            "parts": {"schema": {"status": "ok", "text": "{}"}, "schema_input": {"status": "not_found", "message": "gone"},
                      "diagram": {"status": "ok", "name": "ampliseq_workflow.png", "type": "image/png", "size": 12},
                      "image": {"status": "ok", "name": "ampliseq_workflow.png", "type": "image/png", "size": 12, "data_b64": "AAAA"},
                      "tags": {"status": "ok", "text": "abc\trefs/tags/1.0\n"}}}


def clean(result):
    from abf_platform import jobs
    return jobs.clean_result("pipeline_files", result)


def test_tc077_a_good_result_is_kept_as_it_is():
    # TC-077
    result = good_result()
    assert clean(result) == result


def test_tc078_keys_the_platform_does_not_expect_are_dropped():
    # TC-078
    result = good_result()
    result.update(headers={"a": 1}, url="https://x", token="T", stdout="out", entries=[{"name": "x"}], private_key="K", text="top")
    for part in result["parts"].values():
        part.update(headers={"a": 1}, url="https://x", token="T", stdout="out", entries=[1], private_key="K")
    out = clean(result)
    assert out == good_result()
    for key in ("headers", "url", "token", "stdout", "entries", "private_key", "text"):
        assert key not in out
        assert all(key not in part for part in out["parts"].values() if key != "text")


def test_tc079_an_unknown_status_becomes_bad_response():
    # TC-079
    result = good_result()
    result["parts"]["schema"] = {"status": "weird", "text": "{}"}
    assert clean(result)["parts"]["schema"] == {"status": "bad_response"}


def test_tc080_a_text_over_the_limit_becomes_too_large():
    # TC-080
    result = good_result()
    result["parts"]["schema"]["text"] = "x" * 1000001
    assert clean(result)["parts"]["schema"] == {"status": "too_large"}
    result["parts"]["schema"]["text"] = "x" * 1000000
    assert clean(result)["parts"]["schema"]["status"] == "ok"


def test_tc081_picture_data_must_be_base64_and_not_too_long():
    # TC-081
    result = good_result()
    result["parts"]["image"]["data_b64"] = "AAA*!!"
    assert clean(result)["parts"]["image"] == {"status": "bad_response"}
    result = good_result()
    result["parts"]["image"]["data_b64"] = "A" * 2800001
    assert clean(result)["parts"]["image"] == {"status": "bad_response"}


def test_tc082_a_picture_name_must_be_plain():
    # TC-082
    for name in ("../x.png", "a b.png", "x.gif", ""):
        result = good_result()
        result["parts"]["image"]["name"] = name
        assert clean(result)["parts"]["image"] == {"status": "bad_response"}, name
        result = good_result()
        result["parts"]["diagram"]["name"] = name
        assert clean(result)["parts"]["diagram"] == {"status": "bad_response"}, name


def test_tc083_a_picture_type_must_be_png_or_svg():
    # TC-083
    result = good_result()
    result["parts"]["image"]["type"] = "text/html"
    result["parts"]["diagram"]["type"] = "text/html"
    out = clean(result)
    assert "image" not in out["parts"] and "diagram" not in out["parts"] and out["parts"]["schema"]["status"] == "ok"
    result = good_result()
    result["parts"]["diagram"]["type"] = "image/svg+xml"
    result["parts"]["diagram"]["name"] = "x.svg"
    assert clean(result)["parts"]["diagram"]["type"] == "image/svg+xml"


def test_tc084_an_unknown_part_is_dropped_and_the_result_is_not_a_listing():
    # TC-084
    result = good_result()
    result["parts"]["evil"] = {"status": "ok", "text": "x"}
    out = clean(result)
    assert "evil" not in out["parts"] and "entries" not in out
    assert clean({"ok": True, "parts": "nonsense"})["parts"] == {}
    assert clean("nonsense") == {"ok": False, "message": "the agent sent no result"}


def test_a_size_that_is_not_a_number_is_dropped():
    # TC-077 (the size field is bounded like the other platform numbers)
    result = good_result()
    result["parts"]["diagram"]["size"] = "big"
    assert clean(result)["parts"]["diagram"].get("size") is None


# ---- answering ----------------------------------------------------------------------------------------------------------------

def claimed_job(db, clock, agent="a1"):
    from abf_platform import jobs
    jid = jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, clock=clock, caller_user_id=1)
    jobs.claim(db, agent, clock)
    return jid


def test_tc085_a_good_answer_is_stored_cleaned(db, clock):
    # TC-085
    from abf_platform import jobs
    one_env(db)
    jid = claimed_job(db, clock)
    result = good_result()
    result["headers"] = {"x": 1}
    code, body = jobs.take_result(db, "a1", jid, "done", result, clock)
    row = sql(db, "SELECT * FROM jobs WHERE id = ?", (jid,))[0]
    assert code == 200 and body["accepted"] is True and row["state"] == "done"
    assert json.loads(row["result_json"]) == good_result()


def test_tc086_a_second_answer_and_a_wrong_agent(db, clock):
    # TC-086
    from abf_platform import jobs
    one_env(db)
    add_agent(db, "a2", 1)
    jid = claimed_job(db, clock)
    assert jobs.take_result(db, "a2", jid, "done", good_result(), clock)[0] == 403
    assert jobs.take_result(db, "a1", jid, "done", good_result(), clock)[0] == 200
    assert jobs.take_result(db, "a1", jid, "done", good_result(), clock)[0] == 409


def test_tc087_a_late_answer_is_kept_apart(db, clock):
    # TC-087
    from abf_platform import jobs
    one_env(db)
    jid = claimed_job(db, clock)
    clock.t = T0 + 91
    code, body = jobs.take_result(db, "a1", jid, "done", good_result(), clock)
    assert code == 200 and body == {"accepted": False, "late": True}
    assert sql(db, "SELECT state FROM jobs WHERE id = ?", (jid,))[0][0] == "expired"


# ---- reading them back ---------------------------------------------------------------------------------------------------------

def test_tc088_the_newest_job_with_the_same_arguments(db, clock):
    # TC-088
    from abf_platform import jobs
    one_env(db)
    first = jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, clock=clock, caller_user_id=1)
    other = jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", ["schema"], clock=clock, caller_user_id=1)
    second = jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, clock=clock, caller_user_id=1)
    assert jobs.latest_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, 1)["id"] == second > first
    assert jobs.latest_pipeline_files(db, "nf-core/ampliseq", "2.18.0", ["schema"], 1)["id"] == other
    assert jobs.latest_pipeline_files(db, "nf-core/ampliseq", "2.17.0", PARTS3, 1) is None
    got = jobs.latest_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, 1)
    assert set(got) == {"id", "state", "deadline_at", "finished_at", "result"}


def test_tc089_somebody_elses_job_is_never_seen(db, clock):
    # TC-089
    from abf_platform import jobs
    add_agent(db, "ag-x", 2)
    add_ce(db, "ce-x", agent="ag-x", owner=2)
    jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, clock=clock, caller_user_id=2)
    assert jobs.latest_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, 1) is None
    assert jobs.latest_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, 2) is not None
    assert jobs.latest_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, None) is not None      # the local terminal sees all


def test_tc090_nothing_found_is_none_and_nothing_is_written(db):
    # TC-090
    from abf_platform import jobs
    before = all_files_digest(db)
    assert jobs.latest_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, 1) is None
    assert all_files_digest(db) == before


def test_tc091_the_queue_and_store_never_say_station():
    # TC-091: the whole of both files (so the new lines too) has no such word, and no new spelling of it in pieces:
    # the only joined one is the older line of jobs.py that test_scope already knows
    pkg = PLATFORM_DIR / "abf_platform"
    joined = re.compile(r"sta[\"']\s*\+?\s*[\"']tion")
    for name, allowed_joins in (("jobs.py", 1), ("store.py", 0)):
        text = (pkg / name).read_text(encoding="utf-8")
        assert "station" not in text, name
        assert len(joined.findall(text)) <= allowed_joins, name


def test_tc092_an_old_finished_row_is_pruned_when_the_next_job_is_queued(db, clock):
    # TC-092
    from abf_platform import jobs
    one_env(db)
    old = jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, clock=clock, caller_user_id=1)
    sql(db, "UPDATE jobs SET state = 'done', finished_at = ? WHERE id = ?", (T0, old))
    clock.t = T0 + 7 * 86400 + 1
    add_agent(db, "a1", 1, seen=clock.t)      # the agent is still online at the new time
    jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.17.0", PARTS3, clock=clock, caller_user_id=1)
    assert sql(db, "SELECT COUNT(*) FROM jobs WHERE id = ?", (old,))[0][0] == 0


def test_tc180_only_a_job_row_is_written_and_no_confirmation(db, clock):
    # TC-180
    from abf_platform import jobs
    one_env(db)
    before = {t: sql(db, "SELECT COUNT(*) FROM %s" % t)[0][0] for t in ("confirmations", "launches", "compute_envs", "agents")}
    jobs.enqueue_pipeline_files(db, "nf-core/ampliseq", "2.18.0", PARTS3, clock=clock, caller_user_id=1)
    assert {t: sql(db, "SELECT COUNT(*) FROM %s" % t)[0][0] for t in before} == before
    assert count_jobs(db) == 1 and sql(db, "SELECT COUNT(*) FROM jobs")[0][0] == 1
