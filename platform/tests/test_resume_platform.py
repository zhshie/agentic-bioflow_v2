# Nothing existing: tests of the platform side of a resume and a relaunch (which runs may, who may, what is shown, what is asked, what is queued); the rules of 009e are ours.
"""009e: build.prepare_resume / prepare_relaunch, the screens, and actions.request_resume / request_relaunch.
Test cases are named in the comments (TC-001 ...), see specs/009e-resume-relaunch/test-case.md."""
import asyncio
import json
import os
import re
import sqlite3
import time

import pytest

from resume_harness import SESSION, FakePerson, Rig
from test_launch_platform import make_confirmation

NOT_FOUND = "找不到這個 run (Run not found): %s"
TOO_OLD = "太久了，這次送出的內容已經清掉，請當成新分析重新送出"
OTHER_SESSION = "11111111-2222-4333-8444-555555555555"


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


@pytest.fixture
def duo(rig):
    from owner_harness import Duo
    return Duo(rig.w)


def first_http(rig, duo, caller, run="x", status="failed", session=SESSION):
    """A first launch through the MCP tool of a user (so its samples lie in the user's folder), handed over, and with its end in the index."""
    out = duo.sent(caller, run=run)
    rig.hand_over(out["job_id"], run)
    rig.set_run(run, status, session)
    return out


def screen_of(person):
    assert len(person.seen) == 1, person.seen
    return person.seen[0]


def refused(out, verb="resume"):
    assert out["ok"] is False and out["sent"] is False, out
    return out["message"]


# ---- US1: a resume: what is built --------------------------------------------------------------------------------------------------

def test_tc001_tc002_tc009_a_resume_keeps_the_folder_and_takes_the_next_name_and_number(rig):
    # TC-001, TC-002, TC-009
    first = rig.first("x", slurm=4711)
    ce, b, row = rig.prepare("resume", "x")
    assert ce == "lab-a"
    assert b["run_folder"] == first["run_folder"] == "/data/w1/runs/x"
    assert b["run_name"] == "x-a2"
    assert b["resume"]["of_run"] == "x" and b["resume"]["of_slurm_job_id"] == 4711 and b["resume"]["attempt"] == 2
    assert row["run_name"] == "x" and row["slurm_job_id"] == 4711


def test_tc006_tc007_tc011_the_samples_and_parameters_are_the_origins_and_the_origin_is_the_first_bundle_as_it_was(rig):
    # TC-006, TC-007, TC-011
    first = rig.first("x")
    first_job = rig.jobs()[0]
    b = rig.prepare("resume", "x")[1]
    assert not ({"samplesheet", "params", "pipeline", "revision", "path_columns"} & set(b))
    assert b["resume"]["origin"] == rig.bundle_of_job(first_job["id"]) == json.loads(json.dumps(first))
    assert list(b["files"]) == ["head-2.sh"]


def test_tc008_a_resume_of_a_resume_still_has_the_bundle_that_made_the_folder_as_its_origin(rig):
    # TC-008
    first = rig.first("x")
    first_job_id = rig.jobs()[0]["id"]
    rig.attempt("resume", "x")
    b = rig.prepare("resume", "x-a2")[1]
    assert b["resume"]["attempt"] == 3 and b["resume"]["of_run"] == "x-a2"
    assert b["resume"]["origin"] == rig.bundle_of_job(first_job_id)
    assert b["run_folder"] == first["run_folder"]


def test_tc004_tc005_a_long_root_name_is_cut_to_make_room_for_the_suffix(rig):
    # TC-004, TC-005
    from abf_platform import jobs
    from abf_station import launch
    root = "r" * 63
    rig.first(root)
    b = rig.prepare("resume", root)[1]
    assert len(b["run_name"]) == 64 and b["run_name"].endswith("-a2") and b["run_name"].startswith("r" * 61)
    assert launch.RUN_NAME.match(b["run_name"])
    jobs.check_run_name(rig.state, b["run_name"])
    con = sqlite3.connect(str(rig.state))
    con.row_factory = sqlite3.Row
    try:
        assert jobs.name_problem(con, b["run_name"], time.time()) is None
    finally:
        con.close()
    rig.attempt("resume", root)
    b3 = rig.prepare("resume", b["run_name"])[1]
    assert len(b3["run_name"]) == 64 and b3["run_name"].endswith("-a3")


def test_tc010_the_session_id_is_the_one_in_the_run_index(rig):
    # TC-010
    rig.first("x", session=OTHER_SESSION)
    assert rig.prepare("resume", "x")[1]["resume"]["session_id"] == OTHER_SESSION


@pytest.mark.parametrize("session", ["sess-x", "", "$(touch c)", "../x", "0b1c2d3e-4f50-4a6b-8c7d-9e0f1a2b3c4d; x"])
def test_tc010_a_session_id_that_is_not_a_uuid_is_not_put_in_a_script(rig, session):
    rig.first("x", session=session)
    out = rig.resume("x", person=FakePerson(True))
    assert out["sent"] is False and rig.counts()[0] == 1, out
    assert re.search(r"session", out["message"])


# ---- the screens ---------------------------------------------------------------------------------------------------------------------

def test_tc014_to_tc018_the_resume_screen_says_what_it_resumes_what_does_not_change_and_the_exact_command(rig):
    # TC-014 (old run, which attempt, Slurm number), TC-015 (the sentence), TC-016 (pipeline, revision, samples), TC-017 (the command), TC-018
    rig.first("x", slurm=4711)
    person = FakePerson(True)
    out = rig.resume("x", person=person)
    assert out["sent"] is True, out
    text = screen_of(person)
    assert "x" in text and "第 2 次" in text and "4711" in text
    assert "這是續跑：同一個資料夾，沿用已完成的 task；樣本和參數不變" in text
    assert "nf-core/ampliseq" in text and "2.18.0" in text and re.search(r"樣本數: 10\b", text)
    command = [ln for ln in text.splitlines() if "nextflow run" in ln]
    assert any(re.search(r"nextflow run .*-resume %s .*-name x-a2 " % SESSION, ln) for ln in command), command
    b = rig.bundle_of_job(out["job_id"])
    last = b["files"]["head-2.sh"].rstrip("\n").split("\n")[-1]
    assert last in text.splitlines(), "the screen shows the last line of head-2.sh as it is"
    assert out["job_id"] and rig.confirmations()[-1]["screen_text"] == text


def test_tc014_the_screen_names_the_new_run_the_folder_and_the_environment(rig):
    rig.first("x")
    person = FakePerson(True)
    rig.resume("x", person=person)
    text = screen_of(person)
    assert "x-a2" in text and "/data/w1/runs/x" in text and "lab-a" in text


def test_tc065_to_tc069_the_relaunch_screen(rig):
    # TC-065 (the sentence), TC-066 (old run, attempt, Slurm), TC-067 (the file blocks of a launch), TC-068, TC-069
    from abf_launch import build
    rig.first("x", slurm=4711)
    person = FakePerson(True)
    out = rig.relaunch("x", person=person)
    assert out["sent"] is True, out
    text = screen_of(person)
    assert "這是原樣重跑：全新資料夾，樣本與參數不變" in text
    assert "x" in text and "第 2 次" in text and "4711" in text
    b = rig.bundle_of_job(out["job_id"])
    plain = build.as_text(build.launch_screen(b, "lab-a"))
    for name in ("samplesheet.csv", "params.yaml", "nextflow.config", "head.sh"):
        assert "== %s" % name in text, name
    for line in plain.splitlines()[1:]:
        assert line in text.splitlines(), line
    assert "nf-core/ampliseq" in text and "2.18.0" in text and re.search(r"樣本數: 10\b", text)
    assert any(re.search(r"exec nextflow run nf-core/ampliseq -r 2\.18\.0 -name x-a2 ", ln) for ln in text.splitlines())


def test_the_resume_screen_has_no_control_characters(rig):
    rig.first("x")
    person = FakePerson(True)
    rig.resume("x", person=person)
    text = screen_of(person)
    assert not re.search(r"[\x00-\x08\x0b-\x1f\x7f]", text)


# ---- US3: a relaunch: what is built ---------------------------------------------------------------------------------------------------

def test_tc056_to_tc058_a_relaunch_is_a_new_folder_under_a_new_name_with_the_same_samples_and_parameters(rig):
    # TC-056, TC-057, TC-058
    first = rig.first("x")
    ce, b, row = rig.prepare("relaunch", "x")
    assert b["run_name"] == "x-a2" and b["run_folder"] == "/data/w1/runs/x-a2" != first["run_folder"]
    assert b["files"]["samplesheet.csv"] == first["files"]["samplesheet.csv"] and b["samplesheet"] == first["samplesheet"]
    assert b["params"] == first["params"] and b["path_columns"] == first["path_columns"]
    assert b["files"]["params.yaml"] == first["files"]["params.yaml"].replace("/runs/x", "/runs/x-a2")
    assert b["pipeline"] == first["pipeline"] and b["revision"] == first["revision"] and b["ce"] == first["ce"]
    assert "-resume" not in b["files"]["head.sh"] and "-name x-a2" in b["files"]["head.sh"] and "nf-x-a2" in b["files"]["head.sh"]


def test_tc059_the_run_token_of_a_relaunch_and_of_a_resume_is_for_the_new_name(rig):
    # TC-059, TC-155: one token for one run name, as for any launch; nothing per attempt
    from abf_platform import jobs, store
    rig.first("x")
    for verb in ("relaunch", "resume"):
        out = rig.ask(verb, "x", person=FakePerson(True))
        assert out["sent"] is True, out
        tokens = rig.w.ip.tokens
        got = jobs.claim(rig.state, "agent-t", time.time, tokens_path=tokens)
        assert got is not None and got["args"]["bundle"]["run_name"] == "x-a2" and got["run_token"]
        con = sqlite3.connect(str(tokens))
        rows = con.execute("SELECT run_name FROM tokens WHERE kind = 'run'").fetchall()
        con.close()
        assert ("x-a2",) in rows
        rig.fail_job(out["job_id"], "refused")      # so that the other kind can be tried at attempt 2 as well
    con = sqlite3.connect(str(rig.w.ip.tokens))
    cols = [r[1] for r in con.execute("PRAGMA table_info(tokens)")]
    con.close()
    assert not [c for c in cols if re.search(r"attempt|parent|resume", c)]


def test_tc060_tc061_tc062_a_relaunch_leaves_the_first_rows_alone_and_records_what_it_is_a_relaunch_of(rig):
    # TC-060, TC-061, TC-062
    first = rig.first("x")
    before = [tuple(r) for r in rig.launches()]
    first_conf = rig.confirmations()[0]
    b = rig.prepare("relaunch", "x")[1]
    assert set(b["relaunch"]) == {"of_run", "attempt", "of_sha256"}
    assert b["relaunch"]["of_run"] == "x" and b["relaunch"]["attempt"] == 2 and b["relaunch"]["of_sha256"] == first_conf["sha256"]
    rig.attempt("relaunch", "x")
    assert [tuple(r) for r in rig.launches()][:1] == before


def test_tc063_a_relaunch_of_a_resume_takes_its_content_from_the_first_bundle(rig):
    # TC-063
    first = rig.first("x")
    first_conf = rig.confirmations()[0]
    rig.attempt("resume", "x")
    b = rig.prepare("relaunch", "x-a2")[1]
    assert b["relaunch"] == {"of_run": "x-a2", "attempt": 3, "of_sha256": first_conf["sha256"]}
    assert b["samplesheet"] == first["samplesheet"] and b["params"] == first["params"]
    assert b["run_name"] == "x-a3" and b["run_folder"] == "/data/w1/runs/x-a3"


def test_a_relaunch_of_a_relaunch_records_the_hash_of_the_launch_that_made_that_folder(rig):
    rig.first("x")
    rig.attempt("relaunch", "x")
    made_it = [c for c in rig.confirmations()][1]
    b = rig.prepare("relaunch", "x-a2")[1]
    assert b["relaunch"]["of_sha256"] == made_it["sha256"] and b["relaunch"]["attempt"] == 3


# ---- US2: which runs ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc041_tc042_a_run_that_succeeded_is_refused(rig, verb):
    # TC-041, TC-042
    rig.first("x", status="succeeded")
    before = rig.counts()
    msg = refused(rig.ask(verb, "x", person=FakePerson(True)))
    assert "已成功" in msg
    if verb == "resume":
        assert "已成功，不需要續跑" in msg
    assert rig.counts() == before


@pytest.mark.parametrize("tc,verb,how", [("TC-043", "resume", "running"), ("TC-044", "resume", "waiting"), ("TC-045", "relaunch", "running"),
                                          ("TC-045", "relaunch", "waiting")])
def test_tc043_to_tc045_a_run_that_is_still_going_or_has_not_started_is_refused(rig, tc, verb, how):
    rig.first("x", status=None, with_run=(how == "running"))
    before = rig.counts()
    assert "還在跑" in refused(rig.ask(verb, "x", person=FakePerson(True)))
    assert rig.counts() == before


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc046_a_failed_run_may_go_to_the_question(rig, verb):
    # TC-046
    rig.first("x", status="failed")
    person = FakePerson(True)
    out = rig.ask(verb, "x", person=person)
    assert out["sent"] is True and len(person.seen) == 1


def test_tc047_a_run_that_was_cancelled_is_a_failed_run(rig):
    # TC-047: the platform wrote only cancel_requested_at; the index says failed
    rig.first("x", status="failed")
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE launches SET cancel_requested_at = ? WHERE run_name = 'x'", (time.time(),))
    con.close()
    out = rig.resume("x", person=FakePerson(True))
    assert out["sent"] is True, out


def test_tc048_a_run_without_a_slurm_number_is_refused(rig):
    # TC-048
    rig.first("x", finish=False)
    rig.set_run("x", "failed")
    before = rig.counts()
    msg = refused(rig.resume("x", person=FakePerson(True)))
    assert "Slurm" in msg
    assert "Slurm" in refused(rig.relaunch("x", person=FakePerson(True)))
    assert rig.counts() == before


def test_tc049_a_run_that_another_agent_launched_is_refused(rig):
    # TC-049
    rig.first("x")
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE launches SET agent = 'agent-zzz' WHERE run_name = 'x'")
    con.close()
    before = rig.counts()
    assert re.search(r"代理|agent", refused(rig.resume("x", person=FakePerson(True))))
    assert re.search(r"代理|agent", refused(rig.relaunch("x", person=FakePerson(True))))
    assert rig.counts() == before


def test_tc050_tc149_a_changed_environment_is_a_new_analysis_and_nothing_is_changed_quietly(rig):
    # TC-050, TC-149: the agent reports another address for the platform (another way back), so the environment is not the one of the
    # first launch; a resume would write another head script than the one the folder was made for
    rig.first("x")
    rig.w.data.register(dict(rig.w.data.facts, endpoint="http://127.0.0.1:9999"))
    before = rig.counts()
    for verb in ("resume", "relaunch"):
        msg = refused(rig.ask(verb, "x", person=FakePerson(True)))
        assert re.search(r"新的?分析", msg) and "launch" in msg, msg
    assert rig.counts() == before


def test_tc050_an_environment_that_is_gone_is_refused(rig):
    rig.first("x")
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE launches SET ce = 'lab-gone' WHERE run_name = 'x'")
    con.close()
    assert "lab-gone" in refused(rig.resume("x", person=FakePerson(True)))


def test_tc051_an_older_attempt_is_refused_and_the_newer_one_is_named(rig):
    # TC-051
    rig.first("x")
    rig.attempt("resume", "x")
    rig.age_requests()           # the repeat of the same call within the life of its request gets the job (TC-085); this is a later one
    before = rig.counts()
    for verb in ("resume", "relaunch"):
        msg = refused(rig.ask(verb, "x", person=FakePerson(True)))
        assert "x-a2" in msg and re.search(r"較新|newer", msg), msg
    assert rig.counts() == before


def test_tc051_an_attempt_that_is_only_asked_for_still_counts_as_newer(rig):
    rig.first("x")
    out = rig.resume("x", person=FakePerson(True))       # queued, not handed over
    assert out["sent"] is True
    msg = refused(rig.relaunch("x", person=FakePerson(True)))
    assert "x-a2" in msg


def test_tc052_an_attempt_whose_job_was_refused_does_not_stand_in_the_way(rig):
    # TC-052
    rig.first("x")
    out = rig.resume("x", person=FakePerson(True))
    rig.fail_job(out["job_id"], "refused")
    person = FakePerson(True)
    again = rig.relaunch("x", person=person)
    assert again["sent"] is True, again
    assert rig.row_of_job(again["job_id"])["attempt"] == 2


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc053_tc054_a_launch_whose_content_was_cleared_cannot_be_resumed_or_relaunched(rig, verb):
    # TC-053, TC-054
    rig.first("x")
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("DELETE FROM jobs WHERE id = (SELECT job_id FROM launches WHERE run_name = 'x')")
    con.close()
    before = rig.counts()
    assert TOO_OLD in refused(rig.ask(verb, "x", person=FakePerson(True)))
    assert rig.counts() == before


def test_tc053_the_real_clean_up_after_seven_days_leads_to_the_same_words(rig):
    # TC-053, TC-152: the prune that exists (7 days after a job finished) removes the job, and the words follow
    from abf_platform import jobs
    assert jobs.PRUNE_AFTER_SECONDS == 7 * 86400
    rig.first("x")
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE jobs SET finished_at = ? WHERE kind = 'launch_nextflow'", (time.time() - 8 * 86400,))
    con.close()
    rig.first("y")                       # any later launch prunes
    assert rig.sql("SELECT COUNT(*) FROM jobs WHERE id = (SELECT job_id FROM launches WHERE run_name = 'x')")[0][0] == 0
    assert TOO_OLD in refused(rig.resume("x", person=FakePerson(True)))


def test_tc152_a_job_finished_six_days_ago_is_kept_and_the_retention_was_not_made_longer(rig):
    # TC-152
    from abf_platform import jobs
    rig.first("x")
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE jobs SET finished_at = ? WHERE kind = 'launch_nextflow'", (time.time() - 6 * 86400,))
    con.close()
    rig.first("y")
    assert rig.sql("SELECT COUNT(*) FROM jobs WHERE id = (SELECT job_id FROM launches WHERE run_name = 'x')")[0][0] == 1
    assert jobs.PRUNE_AFTER_SECONDS == 7 * 86400
    out = rig.resume("x", person=FakePerson(True))
    assert out["sent"] is True


def test_tc055_the_state_is_read_from_the_index_each_time_and_kept_nowhere(rig):
    # TC-055
    rig.first("x", status="failed")
    assert rig.resume("x", person=FakePerson(False))["sent"] is False         # asked, and the person declined
    rig.set_run("x", "succeeded")
    assert "已成功" in refused(rig.resume("x", person=FakePerson(True)))
    rig.set_run("x", "failed")
    assert rig.resume("x", person=FakePerson(True))["sent"] is True
    cols = [r[1] for r in rig.sql("PRAGMA table_info(launches)")]
    assert not [c for c in cols if re.search(r"status|state|phase|result|exit|progress|ended|fail|success", c)]


def test_a_run_that_is_lost_is_not_one_that_has_ended(rig):
    # an index row without a complete and without news is "lost": the platform does not know that it ended, so it does not resume it
    rig.first("x", status=None)
    con = sqlite3.connect(str(rig.index))
    with con:
        con.execute("UPDATE runs SET last_message_at = ? WHERE run_name = 'x'", (time.time() - 100000,))
    con.close()
    assert "還在跑" in refused(rig.resume("x", person=FakePerson(True)))


def test_tc151_a_run_that_was_not_launched_from_this_platform_is_not_found(rig):
    # TC-151
    rig.set_run("outside", "failed")
    before = rig.counts()
    msg = refused(rig.resume("outside", person=FakePerson(True)))
    assert NOT_FOUND % "outside" in msg
    assert NOT_FOUND % "ghost" in refused(rig.relaunch("ghost", person=FakePerson(True)))
    assert rig.counts() == before


# ---- US4: the gate: the same as a launch ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("tc,verb", [("TC-074", "resume"), ("TC-075", "relaunch")])
def test_tc074_tc075_with_no_form_and_no_caller_nobody_can_say_yes(rig, tc, verb):
    rig.first("x")
    before = rig.counts()
    out = rig.ask(verb, "x", caller=None, person=None)
    assert out["ok"] is False and out["sent"] is False and "no one can say yes" in out["message"]
    assert rig.counts() == before
    out = rig.ask(verb, "x", caller=None, person=FakePerson(None))
    assert out["sent"] is False and "no one can say yes" in out["message"]
    assert rig.counts() == before


@pytest.mark.parametrize("tc,verb", [("TC-076", "resume"), ("TC-077", "relaunch")])
def test_tc076_tc077_a_declined_form_voids_the_request_and_queues_nothing(rig, tc, verb):
    rig.first("x")
    person = FakePerson(False)
    out = rig.ask(verb, "x", person=person)
    assert out["sent"] is False and len(person.seen) == 1
    assert len(rig.jobs()) == 1
    assert [c["state"] for c in rig.confirmations()][-1] == "void"
    assert rig.sql("SELECT COUNT(*) FROM launches")[0][0] == 1


@pytest.mark.parametrize("tc,verb", [("TC-078", "resume"), ("TC-079", "relaunch")])
def test_tc078_tc079_a_pending_request_queues_nothing_and_is_no_yes(rig, duo, tc, verb):
    from abf_platform import jobs
    first_http(rig, duo, duo.a)
    out = rig.ask(verb, "x", caller=duo.a, person=FakePerson(None))
    assert out["state"] == "pending" and out["sent"] is False
    pending = rig.confirmations()[-1]
    assert pending["state"] == "pending" and pending["kind"] == "launch" and pending["id"] == out["id"]
    assert len(rig.jobs()) == 1
    with pytest.raises(jobs.JobRefused):
        jobs.enqueue_launch(rig.state, pending["ce_name"], json.loads(pending["bundle_json"]), pending["id"])


@pytest.mark.parametrize("tc,verb", [("TC-080", "resume"), ("TC-081", "relaunch")])
def test_tc080_tc081_a_form_that_the_person_accepts_queues_one_job(rig, tc, verb):
    rig.first("x")
    out = rig.ask(verb, "x", person=FakePerson(True))
    assert out["ok"] is True and out["sent"] is True and out["state"] == "queued" and out["job_id"]
    assert len(rig.jobs()) == 2
    conf = rig.confirmations()[-1]
    assert conf["state"] == "confirmed" and conf["channel"] == "ELICITED" and conf["kind"] == "launch"
    assert rig.sql("SELECT kind FROM jobs WHERE id = ?", (out["job_id"],))[0][0] == "launch_nextflow"


@pytest.mark.parametrize("tc,verb", [("TC-082", "resume"), ("TC-083", "relaunch")])
def test_tc082_tc083_over_http_without_a_form_the_answer_is_pending_with_the_address_of_the_page(rig, duo, tc, verb):
    first_http(rig, duo, duo.a)
    out = rig.ask(verb, "x", caller=duo.a, person=None)
    assert out["ok"] is True and out["sent"] is False and out["state"] == "pending"
    assert re.match(r"^http://127\.0\.0\.1:8789/c/[0-9a-f]{32}$", out["confirmation_url"])
    assert verb in out["message"] and ("`%s`" % verb) in out["message"]
    assert len(rig.jobs()) == 1
    assert out["summary"] == rig.confirmations()[-1]["screen_text"]


def test_tc084_the_same_user_presses_the_button_of_the_page_and_the_job_is_queued(rig, duo):
    # TC-084
    from abf_platform import actions
    first_http(rig, duo, duo.a)
    out = rig.resume("x", caller=duo.a, person=None)
    rid = out["id"]
    _, job_id = actions.approve(rig.state, rid, confirmed_by=actions.PAGE, caller=duo.a)
    assert rig.row_of_job(job_id)["attempt"] == 2
    assert rig.confirmations()[-1]["channel"] == "PAGE"
    again = rig.resume("x", caller=duo.a, person=None)
    assert again["sent"] is True and again["job_id"] == job_id


@pytest.mark.parametrize("tc,verb", [("TC-085", "resume"), ("TC-086", "relaunch")])
def test_tc085_tc086_the_same_request_again_gets_the_job_that_exists(rig, tc, verb):
    rig.first("x")
    out = rig.ask(verb, "x", person=FakePerson(True))
    person = FakePerson(True)
    again = rig.ask(verb, "x", person=person)
    assert again["sent"] is True and again["job_id"] == out["job_id"] and again["id"] == out["id"]
    assert person.seen == [] and len(rig.jobs()) == 2


def test_tc085_the_other_kind_asked_after_a_resume_is_refused_and_names_the_attempt_that_exists(rig):
    rig.first("x")
    out = rig.ask("resume", "x", person=FakePerson(True))
    msg = refused(rig.ask("relaunch", "x", person=FakePerson(True)))
    assert "x-a2" in msg and len(rig.jobs()) == 2, (out, msg)


def test_tc087_a_confirmed_by_that_is_not_one_of_the_three_channels_is_refused_before_a_database_is_opened(tmp_path):
    # TC-087
    from abf_platform import actions, jobs
    nowhere = tmp_path / "nowhere" / "platform.db"
    class Fake:
        name = "TERMINAL"
    for who in (None, "TERMINAL", Fake(), actions._Channel("TERMINAL"), 1):
        with pytest.raises(jobs.JobRefused, match="no human confirmation channel"):
            actions.launch(nowhere, "lab-a", {"run_name": "x-a2", "resume": {}}, confirmed_by=who)
    assert not nowhere.exists() and not nowhere.parent.exists()


def test_tc088_a_third_attempt_asks_again_and_does_not_use_the_second_ones_yes(rig):
    # TC-088
    rig.first("x")
    first_person = FakePerson(True)
    out2 = rig.resume("x", person=first_person)
    rig.hand_over(out2["job_id"], "x-a2")
    rig.set_run("x-a2", "failed")
    person = FakePerson(True)
    out3 = rig.resume("x-a2", person=person)
    assert out3["sent"] is True and len(person.seen) == 1
    assert out3["id"] != out2["id"] and out3["job_id"] != out2["job_id"]
    assert rig.row_of_job(out3["job_id"])["attempt"] == 3
    states = [(c["state"], c["channel"]) for c in rig.confirmations()]
    assert states[-2:] == [("confirmed", "ELICITED")] * 2


def test_a_request_asked_over_http_carries_the_name_of_the_tool_not_launch(rig, duo):
    first_http(rig, duo, duo.a)
    out = rig.relaunch("x", caller=duo.a, person=None)
    assert "`relaunch`" in out["message"] and "`launch`" not in out["message"].replace("`relaunch`", "")
    nobody = rig.resume("x", caller=None, person=None)
    assert "abf-platform resume" in nobody["message"]


# ---- US5: only the owner -----------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("tc,verb", [("TC-098", "resume"), ("TC-099", "relaunch")])
def test_tc098_tc099_the_owner_may_resume_and_relaunch(rig, duo, tc, verb):
    first_http(rig, duo, duo.a)
    out = rig.ask(verb, "x", caller=duo.a, person=FakePerson(True))
    assert out["sent"] is True, out
    row = rig.row_of_job(out["job_id"])
    assert row["user_id"] == duo.a.user_id and row["parent_run"] == "x"


@pytest.mark.parametrize("tc,verb", [("TC-100", "resume"), ("TC-101", "relaunch")])
def test_tc100_tc101_somebody_else_is_told_the_run_is_not_found(rig, duo, tc, verb):
    first_http(rig, duo, duo.a)
    before = rig.counts()
    person = FakePerson(True)
    msg = refused(rig.ask(verb, "x", caller=duo.b, person=person))
    assert NOT_FOUND % "x" in msg
    assert person.seen == [] and rig.counts() == before


def test_tc102_a_run_that_nobody_owns_is_not_found_for_a_user(rig, duo):
    # TC-102
    rig.first("n")
    assert NOT_FOUND % "n" in refused(rig.resume("n", caller=duo.a, person=FakePerson(True)))
    assert NOT_FOUND % "n" in refused(rig.relaunch("n", caller=duo.b, person=FakePerson(True)))


def test_tc103_a_run_of_somebody_else_and_a_run_that_does_not_exist_get_exactly_the_same_words(rig, duo):
    # TC-103
    first_http(rig, duo, duo.a, run="alpha-run")
    mine = refused(rig.resume("alpha-run", caller=duo.b, person=FakePerson(True)))
    none = refused(rig.resume("ghost-run", caller=duo.b, person=FakePerson(True)))
    assert mine.replace("alpha-run", "ghost-run") == none
    mine = refused(rig.relaunch("alpha-run", caller=duo.b, person=FakePerson(True)))
    none = refused(rig.relaunch("ghost-run", caller=duo.b, person=FakePerson(True)))
    assert mine.replace("alpha-run", "ghost-run") == none
    # not even the state of the run, or its Slurm number, is told
    assert not re.search(r"已成功|還在跑|Slurm|失敗|failed", mine)


def test_tc104_nothing_that_lists_shows_somebody_else_that_the_run_exists(rig, duo):
    # TC-104
    from abf_platform import actions
    first_http(rig, duo, duo.a, run="alpha-run")
    runs = actions.list_runs(rig.index, caller=duo.b, platform_path=rig.state)["runs"]
    assert "alpha-run" not in [r["name"] for r in runs]
    assert "alpha-run" in [r["name"] for r in actions.list_runs(rig.index, caller=duo.a, platform_path=rig.state)["runs"]]
    out = rig.resume("alpha-run", caller=duo.b, person=FakePerson(True))
    assert "4" not in re.sub(r"alpha-run|Run not found|找不到這個 run", "", out["message"]) or not re.search(r"\b4[0-9]{3}\b", out["message"])


def test_tc105_tc107_a_yes_made_for_somebody_elses_run_is_refused_at_the_queue_in_the_words_of_a_missing_run(rig, duo):
    # TC-105, TC-107: the bundle of alice's run is confirmed by bob (the parent's user is not the yes's user)
    from abf_platform import actions, jobs
    first_http(rig, duo, duo.a)
    ce, b, _ = rig.prepare("resume", "x", owner=duo.a.user_id)
    before = rig.counts()
    with pytest.raises(jobs.JobRefused, match=re.escape(NOT_FOUND % "x")):
        actions.launch(rig.state, ce, b, confirmed_by=actions.TERMINAL, caller=duo.b)
    ce, rb, _ = rig.prepare("relaunch", "x", owner=duo.a.user_id)
    with pytest.raises(jobs.JobRefused, match=re.escape(NOT_FOUND % "x")):
        actions.launch(rig.state, ce, rb, confirmed_by=actions.TERMINAL, caller=duo.b)
    assert rig.counts() == before


def test_tc107_the_user_of_the_previous_launch_decides_not_the_run_name(rig, duo):
    from abf_platform import actions, jobs
    first_http(rig, duo, duo.a)
    ce, b, _ = rig.prepare("resume", "x", owner=duo.a.user_id)
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE launches SET user_id = ? WHERE run_name = 'x'", (duo.b.user_id,))
    con.close()
    with pytest.raises(jobs.JobRefused, match="找不到這個 run"):
        actions.launch(rig.state, ce, b, confirmed_by=actions.TERMINAL, caller=duo.a)


def test_tc106_a_yes_that_alice_gave_is_not_usable_for_bob(rig, duo):
    # TC-106: the pending request is alice's; bob cannot press its button
    from abf_platform import actions
    first_http(rig, duo, duo.a)
    out = rig.resume("x", caller=duo.a, person=None)
    assert out["state"] == "pending"
    with pytest.raises(actions.NotApproved) as e:
        actions.approve(rig.state, out["id"], confirmed_by=actions.PAGE, caller=duo.b)
    assert e.value.status == "not_yours"
    assert len(rig.jobs()) == 1


def test_the_chain_stays_with_the_owner_even_when_the_terminal_without_a_user_asks(rig, duo):
    # the terminal (no caller) may resume a run of a user; the new row stays that user's, so the user still sees the attempt
    first_http(rig, duo, duo.a)
    out = rig.attempt("resume", "x", caller=None)
    assert rig.row_of_job(out["job_id"])["user_id"] == duo.a.user_id


def test_tc110_tc111_without_users_a_run_with_no_owner_can_be_resumed_by_the_terminal_and_by_stdio(rig):
    # TC-110 (the terminal's own test is in test_resume_entrypoints), TC-111
    rig.first("x")
    person = FakePerson(True)
    out = rig.resume("x", caller=None, person=person)
    assert out["sent"] is True and rig.row_of_job(out["job_id"])["user_id"] is None


# ---- 116b: the upload paths -------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("tc,verb", [("TC-112", "resume"), ("TC-116", "relaunch")])
def test_tc112_tc116_over_http_the_real_paths_are_looked_at_again_and_recorded_in_the_bundle(rig, duo, tc, verb):
    first_http(rig, duo, duo.a)
    out = rig.ask(verb, "x", caller=duo.a, person=FakePerson(True))
    assert out["sent"] is True, out
    b = rig.bundle_of_job(out["job_id"])
    area = str(duo.area(duo.a))
    assert b["upload_paths"]["area"] == os.path.realpath(area) and b["upload_paths"]["paths"]
    assert all(e["real"].startswith(os.path.realpath(area) + os.sep) for e in b["upload_paths"]["paths"])
    # the approved hash covers it
    from abf_platform import common
    assert common.bundle_sha256(b) == rig.sql("SELECT sha256 FROM confirmations WHERE id = ?", (out["id"],))[0][0]
    t = json.loads(json.dumps(b))
    t["upload_paths"]["paths"][0]["real"] = "/x/y"
    assert common.bundle_sha256(t) != common.bundle_sha256(b)


def test_tc117_upload_paths_changed_after_the_yes_are_not_the_content_that_was_confirmed(rig, duo):
    # TC-117
    from abf_platform import actions, confirm, jobs
    first_http(rig, duo, duo.a)
    out = rig.resume("x", caller=duo.a, person=None)
    pending = rig.confirmations()[-1]
    b = json.loads(pending["bundle_json"])
    b["upload_paths"]["paths"][0]["real"] = os.path.join(b["upload_paths"]["area"], "elsewhere.fq")
    con = sqlite3.connect(str(rig.state))
    with con:
        con.execute("UPDATE confirmations SET bundle_json = ? WHERE id = ?", (json.dumps(b), pending["id"]))
    con.close()
    with pytest.raises(confirm.NotApproved, match="內容與顯示時不符"):
        actions.approve(rig.state, pending["id"], confirmed_by=actions.PAGE, caller=duo.a)
    assert len(rig.jobs()) == 1
    # and at the queue
    ce = pending["ce_name"]
    cid = make_confirmation(rig.state, "launch", json.loads(pending["bundle_json"]))
    with pytest.raises(jobs.JobRefused, match="內容與確認時不符"):
        jobs.enqueue_launch(rig.state, ce, b, cid)


@pytest.mark.parametrize("tc,verb", [("TC-113", "resume"), ("TC-114", "relaunch")])
def test_tc113_tc114_a_sample_link_that_now_leads_out_of_the_users_folder_is_refused_before_any_question(rig, duo, tc, verb):
    first_http(rig, duo, duo.a)
    area = duo.area(duo.a)
    (area / "rawdata").mkdir(parents=True, exist_ok=True)
    outside = area.parent / "outside"
    outside.mkdir(exist_ok=True)
    os.symlink(outside, area / "rawdata" / "s01.fastq.gz")
    person = FakePerson(True)
    before = rig.counts()
    msg = refused(rig.ask(verb, "x", caller=duo.a, person=person))
    assert "你自己的上傳資料夾" in msg and str(os.path.realpath(area)) in msg
    assert person.seen == [] and rig.counts() == before
    # and exactly the words of a launch
    from abf_launch import build
    assert build.area_refusal(os.path.realpath(area)).args[0] in msg


def test_tc118_the_terminal_and_stdio_have_no_upload_area_and_no_upload_paths(rig):
    # TC-118
    rig.first("x")
    for verb in ("resume", "relaunch"):
        b = rig.prepare(verb, "x")[1]
        assert "upload_paths" not in b
    out = rig.resume("x", caller=None, person=FakePerson(True))
    assert "upload_paths" not in rig.bundle_of_job(out["job_id"])


def test_a_user_whose_name_cannot_be_a_folder_is_refused_like_a_launch(rig, duo):
    from abf_platform import actions
    first_http(rig, duo, duo.a)
    weird = actions.Caller(duo.a.user_id, "../x", "lab-x")
    out = rig.resume("x", caller=weird, person=FakePerson(True))
    assert out["sent"] is False and "你自己的上傳資料夾" in out["message"]


def test_009e_a_relaunch_name_held_by_another_user_gets_the_uniform_words_with_no_slurm_id_or_state(rig, duo):
    # 116b over relaunch: the generated name sample-a2 is user A's run with Slurm id 7771; B relaunching own run `sample` is told NAME_TAKEN only
    from abf_launch import build
    from abf_platform import jobs
    duo.bobs_environment()
    out_b = duo.sent(duo.b, run="sample", ce_name="b1")
    rig.hand_over(out_b["job_id"], "sample")
    rig.set_run("sample", "failed")
    out_a = duo.sent(duo.a, run="sample-a2")
    rig.hand_over(out_a["job_id"], "sample-a2", slurm=7771)
    rig.set_run("sample-a2", "failed")
    with pytest.raises(build.Refusal) as e:
        rig.prepare("relaunch", "sample", owner=duo.b.user_id)
    assert str(e.value) == jobs.NAME_TAKEN
    msg = refused(rig.relaunch("sample", caller=duo.b, person=FakePerson(True)))
    assert jobs.NAME_TAKEN in msg and "7771" not in msg and "Slurm" not in msg and "failed" not in msg
    # the terminal (no caller) keeps the detailed wording
    with pytest.raises(build.Refusal) as e:
        rig.prepare("relaunch", "sample")
    assert "7771" in str(e.value)
