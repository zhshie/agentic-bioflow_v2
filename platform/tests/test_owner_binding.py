# Nothing existing: tests of spec 116, who owns an environment, an agent, a run and an upload folder; the rule (a row of somebody else answers like a missing row) is ours.
"""116: every action sees and uses only the caller's own compute environments, agents, runs and files.
Test cases are named in the comments (TC-001 ...), see specs/116-owner-binding/test-case.md."""
import asyncio
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time

import pytest
from starlette.testclient import TestClient

from helpers import PLATFORM_DIR, all_files_digest, free_port, mcp_http_call, pkg_env, start_cli, stop_proc, tool_json, wait_port
from human_harness import PASSWORD, World, csrf_of, form_answer, pending_id_of
from launch_harness import QUESTION_LAUNCH, QUESTION_CANCEL, Pty, cli_argv
from owner_harness import Duo, SHARED, sql_exec, sql_rows
from station_harness import Inproc


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def store():
    from abf_platform import store as s
    return s


def words(text, name):
    """A refusal with the name it was asked about taken out, to compare the words of two refusals."""
    return re.sub(re.escape(name), "<name>", str(text))


# ---- US1: each person sees only their own ---------------------------------------------------------------------------------

def test_tc001_each_person_lists_only_their_own_environments(d):
    # TC-001
    d.bobs_environment()
    assert [c["name"] for c in d.call("list_compute_envs", caller=d.a)["compute_envs"]] == ["lab-a"]
    assert [c["name"] for c in d.call("list_compute_envs", caller=d.b)["compute_envs"]] == ["b1"]


def test_tc002_somebody_elses_environment_answers_like_a_missing_one(d):
    # TC-002
    d.bobs_environment()
    other = d.call("get_compute_env", {"name": "b1"}, caller=d.a)
    missing = d.call("get_compute_env", {"name": "nonesuch"}, caller=d.a)
    assert other["found"] is False and "config" not in other and "agent" not in other
    assert words(other, "b1") == words(missing, "nonesuch")


def test_tc003_each_person_lists_only_their_own_agents(d):
    # TC-003
    d.bobs_environment()
    assert [a["name"] for a in d.call("list_agents", caller=d.a)["agents"]] == ["agent-t"]
    assert [a["name"] for a in d.call("list_agents", caller=d.b)["agents"]] == ["agent-b"]


def test_tc004_each_person_lists_only_the_runs_they_launched(d):
    # TC-004
    d.add_run("r-a", d.a.user_id)
    d.add_run("r-b", d.b.user_id)
    assert d.run_names(d.a) == ["r-a"] and d.run_names(d.b) == ["r-b"]


def test_tc005_somebody_elses_run_answers_like_a_missing_one(d):
    # TC-005
    rid = d.add_run("r-b", d.b.user_id)
    other = d.call("get_run", {"run_id": rid}, caller=d.a)
    missing = d.call("get_run", {"run_id": "id-nonesuch"}, caller=d.a)
    assert other["found"] is False and "tasks" not in other and "status" not in other
    assert words(other, rid) == words(missing, "id-nonesuch")
    assert d.call("get_run", {"run_id": rid}, caller=d.b)["name"] == "r-b"


def test_tc006_the_newest_launch_of_a_name_decides(d):
    # TC-006
    rid = d.add_run("r-x", d.a.user_id)
    d.add_launch_row("r-x", d.b.user_id)
    assert d.call("get_run", {"run_id": rid}, caller=d.b)["name"] == "r-x"
    assert d.call("get_run", {"run_id": rid}, caller=d.a)["found"] is False
    assert d.run_names(d.a) == [] and d.run_names(d.b) == ["r-x"]


def test_tc007_a_run_without_a_launch_row_is_hidden(d):
    # TC-007
    rid = d.add_run("r-old", launch_row=False)
    assert d.run_names(d.a) == [] and d.run_names(d.b) == []
    assert d.call("get_run", {"run_id": rid}, caller=d.a)["found"] is False


def test_tc008_a_run_of_nobody_is_hidden_over_http_mcp_and_the_web(d, w, tmp_path):
    # TC-008
    rid = d.add_run("r-null", None)
    assert d.run_names(d.a) == [] and d.call("get_run", {"run_id": rid}, caller=d.a)["found"] is False
    pat = store().create_token(w.ip.tokens, kind="pat", user_id=d.a.user_id)
    env = pkg_env(ABF_PLATFORM_DB=w.ip.index)
    port = free_port()
    proc = start_cli(["mcp", "--http", "--port", str(port)], env, tmp_path / "mcp.log")
    try:
        wait_port(port, proc=proc)
        _, outs = mcp_http_call("http://127.0.0.1:%d/mcp" % port,
                                [("list_runs", {}), ("get_run", {"run_id": rid}), ("list_compute_envs", {})], token=pat)
    finally:
        stop_proc(proc)
    assert tool_json(outs[0])["runs"] == [] and tool_json(outs[1])["found"] is False
    assert [c["name"] for c in tool_json(outs[2])["compute_envs"]] == ["lab-a"]
    client = w.web()
    assert w.login(client, "alice").status_code == 303        # 011a: a login now lands on the board
    assert client.get("/runs").status_code == 404 and client.get("/c/" + "0" * 32).status_code == 404
    assert "r-null" not in client.get("/").text


def test_tc009_an_environment_and_an_agent_of_nobody_are_hidden(d):
    # TC-009
    d.an_environment_nobody_owns()
    assert [c["name"] for c in d.call("list_compute_envs", caller=d.a)["compute_envs"]] == ["lab-a"]
    assert [a["name"] for a in d.call("list_agents", caller=d.a)["agents"]] == ["agent-t"]
    assert d.call("get_compute_env", {"name": "e0"}, caller=d.a)["found"] is False


def test_tc010_the_terminal_and_stdio_see_everything(d):
    # TC-010
    d.bobs_environment()
    d.an_environment_nobody_owns()
    d.add_run("r-a", d.a.user_id)
    d.add_run("r-b", d.b.user_id)
    d.add_run("r-null", None)
    d.add_run("r-old", launch_row=False)
    assert sorted(c["name"] for c in d.call("list_compute_envs")["compute_envs"]) == ["b1", "e0", "lab-a"]
    assert sorted(a["name"] for a in d.call("list_agents")["agents"]) == ["agent-0", "agent-b", "agent-t"]
    assert d.run_names(None) == ["r-a", "r-b", "r-null", "r-old"]
    assert d.call("get_compute_env", {"name": "e0"})["name"] == "e0"
    rc, out = d.w.ip.run("ce", "list")
    assert rc == 0 and all(n in out for n in ("b1", "e0", "lab-a"))


def test_tc011_the_web_shows_no_list_and_never_somebody_elses_request(d, w):
    # TC-011
    d.bobs_environment()
    out = d.launch(d.a)
    rid = pending_id_of(out["confirmation_url"])
    client = w.web()
    assert w.login(client, "bob").status_code == 303        # 011a: a login now lands on the board
    for path in ("/runs", "/ce", "/compute-envs", "/agents"):
        assert client.get(path).status_code == 404, path
    assert client.get("/").status_code == 200 and rid not in client.get("/").text        # 011a: "/" is the board, which shows no request
    page = client.get("/c/" + rid)
    assert page.status_code == 403 and "run-one" not in page.text and "lab-a" not in page.text


def test_tc012_three_unusable_names_get_the_same_words(d):
    # TC-012
    d.bobs_environment()
    d.an_environment_nobody_owns()
    answers = [words(d.call("get_compute_env", {"name": n}, caller=d.a), n) for n in ("b1", "e0", "nonesuch")]
    assert answers[0] == answers[1] == answers[2]


def test_tc013_the_same_lab_shares_nothing(d):
    # TC-013
    d.bobs_environment()
    assert {u["lab"] for u in sql_rows(d.w.ip.tokens, "SELECT lab FROM users")} == {"lab-x"}
    d.add_run("r-b", d.b.user_id)
    assert d.call("get_compute_env", {"name": "b1"}, caller=d.a)["found"] is False
    assert "agent-b" not in [a["name"] for a in d.call("list_agents", caller=d.a)["agents"]]
    assert d.run_names(d.a) == []
    assert not re.search(r"\b(role|share|shared_with|visibility)\b", " ".join(r["name"] for r in sql_rows(d.state, "SELECT name FROM pragma_table_info('compute_envs')")))


# ---- US2: each person uses only their own ---------------------------------------------------------------------------------

def counts(d):
    return (len(d.w.jobs()), len(d.w.confirmations()), len(sql_rows(d.state, "SELECT * FROM launches")))


def test_tc014_a_launch_on_somebody_elses_environment_is_not_found(d):
    # TC-014
    out = d.launch(d.b, ce_name="lab-a", answer=form_answer())
    assert out["ok"] is False and out["sent"] is False and "找不到" in out["message"]
    assert counts(d) == (0, 0, 0)


def test_tc015_no_environment_of_my_own_means_no_launch(d):
    # TC-015
    out = d.launch(d.b, ce_name=None, answer=form_answer())
    assert out["ok"] is False and out["sent"] is False and "lab-a" not in json.dumps(out)
    assert counts(d) == (0, 0, 0)


def test_tc016_the_environment_chosen_for_me_is_my_own(d):
    # TC-016
    d.bobs_environment(primary=True)
    from abf_platform import compute_envs
    compute_envs.set_primary(d.state, "lab-a")
    out = d.launch(d.b, ce_name=None)
    assert out["ok"] is True and re.search(r"環境: b1(?![a-z0-9])", out["summary"]) and "環境: lab-a" not in out["summary"]
    out = d.launch(d.a, run="run-two", ce_name=None)
    assert out["ok"] is True and "環境: lab-a" in out["summary"] and not re.search(r"環境: b1(?![a-z0-9])", out["summary"])


def test_tc017_primary_is_per_owner(d):
    # TC-017
    from abf_platform import compute_envs
    d.bobs_environment()
    compute_envs.set_primary(d.state, "b1")
    compute_envs.set_primary(d.state, "lab-a")
    assert {c["name"]: c["primary"] for c in compute_envs.list_all(d.state)} == {"lab-a": True, "b1": True}
    assert [c["name"] for c in compute_envs.list_all(d.state, owner=d.b.user_id)] == ["b1"]


def _bundle(d, **kw):
    from abf_launch import build
    sheet = d.w.data.samplesheet(d.w.tmp)
    return build.prepare_launch(d.state, ce=kw.pop("ce", "lab-a"), pipeline="nf-core/ampliseq", revision="2.18.0",
                                run_name=kw.pop("run", "run-q"), samplesheet=str(sheet))[1]


def test_tc018_the_queue_refuses_a_confirmation_of_somebody_else(d):
    # TC-018
    from abf_platform import confirm, jobs
    bundle = _bundle(d)
    before = counts(d)
    with pytest.raises(jobs.JobRefused, match="找不到"):
        confirm.confirm_launch(d.state, "lab-a", bundle, caller_user_id=d.b.user_id, channel="TERMINAL")
    assert counts(d) == before == (0, 0, 0)


def test_tc019_the_queue_refuses_an_environment_whose_agent_is_somebody_elses(d):
    # TC-019
    from abf_platform import confirm, jobs
    bundle = _bundle(d)
    sql_exec(d.state, "UPDATE agents SET owner_user_id = ? WHERE name = 'agent-t'", (d.b.user_id,))
    with pytest.raises(jobs.JobRefused, match="找不到"):
        confirm.confirm_launch(d.state, "lab-a", bundle, caller_user_id=d.a.user_id, channel="TERMINAL")
    assert counts(d) == (0, 0, 0)


def test_tc020_an_environment_of_nobody_is_refused_over_http(d):
    # TC-020
    d.an_environment_nobody_owns()
    out = d.launch(d.a, ce_name="e0", answer=form_answer())
    assert out["ok"] is False and out["sent"] is False and "找不到" in out["message"]
    assert counts(d) == (0, 0, 0)


def test_tc021_tc023_listing_through_an_environment_needs_its_owner(d):
    # TC-021, TC-023
    from abf_platform import jobs
    d.bobs_environment()
    before = len(sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'list_site_files'"))
    with pytest.raises(jobs.JobRefused, match="找不到"):
        jobs.enqueue_listing(d.state, "lab-a", "/data/w1", time.time, caller_user_id=d.b.user_id)
    assert len(sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'list_site_files'")) == before
    assert jobs.enqueue_listing(d.state, "lab-a", "/data/w1", time.time, caller_user_id=d.a.user_id)
    assert jobs.enqueue_listing(d.state, "b1", "/data/w2", time.time, caller_user_id=d.b.user_id)
    assert jobs.enqueue_listing(d.state, "lab-a", "/data/w1", time.time)      # the terminal: no caller, no check
    assert len(sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'list_site_files'")) == before + 3


def test_tc022_my_own_launch_is_queued(d):
    # TC-022
    out = d.sent(d.a)
    assert out["state"] == "queued" and out["job_id"]
    assert len(d.w.jobs("launch_nextflow")) == 1


def test_tc024_somebody_elses_run_cannot_be_cancelled(d):
    # TC-024
    d.w.hand_over("run-one", by=d.a)
    other = d.call("cancel", {"run_name": "run-one"}, caller=d.b, answer=form_answer())
    missing = d.call("cancel", {"run_name": "run-none"}, caller=d.b, answer=form_answer())
    assert other["ok"] is False and other["sent"] is False and "job_id" not in other
    assert words(other, "run-one") == words(missing, "run-none")
    assert d.w.jobs("cancel_run") == []


def test_tc025_a_confirmed_cancel_of_one_is_not_reused_for_another(d):
    # TC-025
    d.w.hand_over("run-one", by=d.a)
    mine = d.call("cancel", {"run_name": "run-one"}, caller=d.a, answer=form_answer())
    assert mine["sent"] is True and len(d.w.jobs("cancel_run")) == 1
    theirs = d.call("cancel", {"run_name": "run-one"}, caller=d.b, answer=form_answer())
    missing = d.call("cancel", {"run_name": "run-none"}, caller=d.b, answer=form_answer())
    assert theirs["sent"] is False and "job_id" not in theirs and theirs["ok"] is False
    assert words(theirs, "run-one") == words(missing, "run-none")
    assert len(d.w.jobs("cancel_run")) == 1


def test_tc026_the_queue_refuses_a_cancel_of_somebody_elses_launch(d):
    # TC-026
    from abf_launch import build
    from abf_platform import confirm, jobs
    d.w.hand_over("run-one", by=d.a)
    _, bundle, _ = build.prepare_cancel(d.state, "run-one")
    with pytest.raises(jobs.JobRefused):
        confirm.confirm_cancel(d.state, "lab-a", bundle, caller_user_id=d.b.user_id, channel="TERMINAL")
    assert d.w.jobs("cancel_run") == []
    assert confirm.confirm_cancel(d.state, "lab-a", bundle, caller_user_id=d.a.user_id, channel="TERMINAL")


def test_tc027_the_terminal_cancel_asks_for_no_account(d, tmp_path):
    # TC-027
    d.w.hand_over("run-one", by=d.a)
    p = Pty(cli_argv("cancel", "run-one"), d.w.data.env())
    assert p.wait_for(QUESTION_CANCEL, 30), p.text()
    assert "--user" not in p.text()
    p.send("y\n")
    rc, screen = p.finish(60)
    jobs = d.w.jobs("cancel_run")
    assert len(jobs) == 1
    assert sql_rows(d.state, "SELECT caller_user_id FROM confirmations WHERE kind = 'cancel'")[0][0] is None


def test_tc028_an_agent_token_can_record_a_user(w):
    # TC-028
    alice = w.user("alice")
    rc, out = w.ip.run("agent-token", "new", "agent-q", "--user", "alice")
    assert rc == 0, out
    token = [ln for ln in out.splitlines() if ln.startswith("abf_")][0]
    got = store().lookup_token(w.ip.tokens, token)
    assert got["user_id"] == alice.user_id and got["kind"] == "agent" and got["agent_name"] == "agent-q"
    plain = store().create_token(w.ip.tokens, kind="agent", agent_name="agent-p")
    assert store().lookup_token(w.ip.tokens, plain)["user_id"] is None
    with pytest.raises(ValueError):
        store().create_token(w.ip.tokens, kind="run", user_id=alice.user_id)
    rc, out = w.ip.run("agent-token", "new", "agent-z", "--user", "nobody")
    assert rc != 0


def _hello(w, token, name):
    from abf_platform import receiver
    client = TestClient(receiver.create_app(w.ip.index, w.ip.tokens))
    return client.post("/agent/hello", json={"name": name, "version": "0.1.0"}, headers={"Authorization": "Bearer " + token})


def _agent_owner(w, name):
    rows = sql_rows(w.ip.state_db, "SELECT owner_user_id FROM agents WHERE name = ?", (name,))
    return rows[0][0] if rows else "no row"


def test_tc029_another_users_agent_token_cannot_take_over_an_agent(w):
    # TC-029
    a, b = w.user("alice"), w.user("bob")
    ta = store().create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=a.user_id)
    tb = store().create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=b.user_id)
    assert _hello(w, ta, "ag").status_code == 200 and _agent_owner(w, "ag") == a.user_id
    wrong = _hello(w, tb, "other")
    refused = _hello(w, tb, "ag")
    assert refused.status_code == 403 and set(refused.json()) == set(wrong.json()) == {"message"}
    assert _agent_owner(w, "ag") == a.user_id


def test_tc030_the_first_owned_token_fills_an_empty_owner(w):
    # TC-030
    a, b = w.user("alice"), w.user("bob")
    legacy = store().create_token(w.ip.tokens, kind="agent", agent_name="ag")
    assert _hello(w, legacy, "ag").status_code == 200 and _agent_owner(w, "ag") is None
    ta = store().create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=a.user_id)
    tb = store().create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=b.user_id)
    assert _hello(w, ta, "ag").status_code == 200 and _agent_owner(w, "ag") == a.user_id
    assert _hello(w, tb, "ag").status_code == 403 and _agent_owner(w, "ag") == a.user_id


def _ce_row(d, name):
    rows = sql_rows(d.state, "SELECT * FROM compute_envs WHERE name = ?", (name,))
    return rows[0] if rows else None


def test_tc031_an_environment_cannot_be_created_on_somebody_elses_agent(d):
    # TC-031
    d.bobs_environment()
    rc, out = d.w.ip.run("ce", "create", "--name=x1", "--platform=slurm-platform", "--work-dir=/data/x", "--head-queue=normal",
                         "--agent=agent-b", "--owner=alice")
    assert rc != 0 and "rejected" in out and _ce_row(d, "x1") is None


def test_tc032_an_environment_cannot_be_rebound_to_somebody_elses_agent(d):
    # TC-032
    d.bobs_environment()
    before = dict(_ce_row(d, "lab-a"))
    rc, out = d.w.ip.run("ce", "update", "lab-a", "--agent=agent-b")
    assert rc != 0 and "rejected" in out and dict(_ce_row(d, "lab-a")) == before


def test_tc033_one_user_owns_what_create_makes(tmp_path, monkeypatch):
    # TC-033
    ip = Inproc(tmp_path / "ip", monkeypatch)
    uid = store().create_user(ip.tokens, "alice", "lab-x")
    rc, out = ip.create_slurm("x1")
    assert rc == 0, out
    assert sql_rows(ip.state_db, "SELECT owner_user_id FROM compute_envs WHERE name = 'x1'")[0][0] == uid


def test_tc034_two_users_need_the_owner_flag(tmp_path, monkeypatch):
    # TC-034
    ip = Inproc(tmp_path / "ip", monkeypatch)
    store().create_user(ip.tokens, "alice", "lab-x")
    bid = store().create_user(ip.tokens, "bob", "lab-x")
    rc, out = ip.create_slurm("x1")
    assert rc != 0 and "--owner" in out and not sql_rows(ip.state_db, "SELECT * FROM compute_envs")
    rc, out = ip.create_slurm("x1", owner="bob")
    assert rc == 0, out
    assert sql_rows(ip.state_db, "SELECT owner_user_id FROM compute_envs")[0][0] == bid
    rc, out = ip.create_slurm("x2", owner="nobody")
    assert rc != 0


def test_tc035_an_owner_can_be_reassigned(d):
    # TC-035
    rc, out = d.w.ip.run("ce", "create", "--name=x1", "--platform=slurm-platform", "--work-dir=/data/x", "--head-queue=normal",
                         "--owner=alice", "--agent=agent-x")
    assert rc == 0, out
    assert d.call("get_compute_env", {"name": "x1"}, caller=d.a)["name"] == "x1"
    rc, out = d.w.ip.run("ce", "update", "x1", "--owner=bob")
    assert rc == 0, out
    assert d.call("get_compute_env", {"name": "x1"}, caller=d.b)["name"] == "x1"
    assert d.call("get_compute_env", {"name": "x1"}, caller=d.a)["found"] is False
    rc, out = d.w.ip.run("ce", "update", "x1", "--owner=nobody")
    assert rc != 0


def test_tc035_reassigned_environment_with_its_registered_agent_is_usable_by_the_new_owner(d):
    # TC-035 (fix round): the environment and its agent are both alice's; one `ce update --owner` hands both to bob
    d.bobs_environment(name="x1", agent="agent-x", owner=d.a.user_id)
    assert d.launch(d.b, run="run-pre", ce_name="x1", answer=form_answer())["sent"] is False
    rc, out = d.w.ip.run("ce", "update", "x1", "--owner=bob")
    assert rc == 0, out
    assert sql_rows(d.state, "SELECT owner_user_id FROM agents WHERE name = 'agent-x'")[0][0] == d.b.user_id
    assert "agent-x" in [a["name"] for a in d.call("list_agents", caller=d.b)["agents"]]
    assert "agent-x" not in [a["name"] for a in d.call("list_agents", caller=d.a)["agents"]]
    out = d.launch(d.b, run="run-two", ce_name="x1", answer=form_answer())
    assert out["ok"] is True and out["sent"] is True, out
    out = d.launch(d.a, run="run-three", ce_name="x1", answer=form_answer())
    assert out["sent"] is False and "找不到" in out["message"]


def test_tc035_reassigning_is_refused_while_the_agent_still_serves_another_environment_of_the_old_owner(d):
    # TC-035 (fix round): the agent has one owner, so it cannot leave alice while another environment of hers uses it
    d.bobs_environment(name="x1", agent="agent-x", owner=d.a.user_id)
    d.bobs_environment(name="x2", agent="agent-x", owner=d.a.user_id)
    rc, out = d.w.ip.run("ce", "update", "x1", "--owner=bob")
    assert rc != 0 and "x2" in out
    assert sql_rows(d.state, "SELECT owner_user_id FROM compute_envs WHERE name = 'x1'")[0][0] == d.a.user_id
    assert sql_rows(d.state, "SELECT owner_user_id FROM agents WHERE name = 'agent-x'")[0][0] == d.a.user_id


def test_tc036_ce_list_names_the_owner(d):
    # TC-036
    d.bobs_environment()
    d.an_environment_nobody_owns()
    rc, out = d.w.ip.run("ce", "list")
    lines = {ln.split()[0]: ln for ln in out.splitlines() if ln.strip()}
    assert "alice" in lines["lab-a"] and "bob" in lines["b1"] and "(none: local only)" in lines["e0"]


def test_tc037_nobody_else_can_say_yes_for_me(d, w):
    # TC-037
    out = d.launch(d.a)
    rid = pending_id_of(out["confirmation_url"])
    client = w.web()
    assert w.login(client, "bob").status_code == 303        # 011a
    page = client.get("/c/" + rid)
    assert page.status_code == 403
    posted = client.post("/c/" + rid, data={"csrf": csrf_of(page.text) or "x"})
    assert posted.status_code == 403
    assert w.jobs("launch_nextflow") == []


# ---- US3: every launch records who sent it ---------------------------------------------------------------------------------

def launch_users(d):
    return [r[0] for r in sql_rows(d.state, "SELECT user_id FROM launches ORDER BY id")]


def test_tc038_a_form_launch_records_the_user(d):
    # TC-038
    d.sent(d.a)
    assert launch_users(d) == [d.a.user_id]


def test_tc039_a_page_launch_records_the_user(d, w):
    # TC-039
    out = d.launch(d.a)
    rid = pending_id_of(out["confirmation_url"])
    client = w.web()
    assert w.login(client, "alice").status_code == 303        # 011a
    page = client.get("/c/" + rid)
    done = client.post("/c/" + rid, data={"csrf": csrf_of(page.text)})
    assert done.status_code == 200 and "已送出" in done.text
    assert launch_users(d) == [d.a.user_id]


def test_tc040_a_refused_enqueue_leaves_no_launch_row(d):
    # TC-040
    from abf_platform import confirm
    bundle = _bundle(d)
    rid = confirm.create_pending(d.state, "launch", "lab-a", bundle, "x", d.b.user_id)
    with pytest.raises(confirm.NotApproved):
        confirm.approve(d.state, rid, "PAGE", d.b.user_id)
    assert counts(d)[0] == 0 and launch_users(d) == []
    assert sql_rows(d.state, "SELECT state FROM confirmations WHERE id = ?", (rid,))[0][0] == "void"


def terminal(d, tmp_path, *extra, answer="y\n", run="run-one"):
    args = d.w.data.launch_args(tmp_path, run=run, extra=extra)
    p = Pty(cli_argv(*args), d.w.data.env())
    if answer is not None:
        assert p.wait_for(QUESTION_LAUNCH, 30), p.text()
        p.send(answer)
    return p.finish(60)


def test_tc041_a_terminal_launch_records_the_named_account(d, tmp_path):
    # TC-041
    rc, screen = terminal(d, tmp_path, "--user", "alice")
    assert len(d.w.jobs("launch_nextflow")) == 1 and launch_users(d) == [d.a.user_id]
    assert sql_rows(d.state, "SELECT caller_user_id FROM confirmations")[0][0] == d.a.user_id


def test_tc042_a_terminal_launch_must_name_an_account_once_users_exist(d, tmp_path):
    # TC-042
    rc, screen = terminal(d, tmp_path, answer=None)
    assert rc != 0 and "--user" in screen and QUESTION_LAUNCH not in screen
    assert counts(d) == (0, 0, 0)


def test_tc043_with_no_users_the_row_stays_null(tmp_path, monkeypatch):
    # TC-043
    from launch_harness import LaunchData
    data = LaunchData(Inproc(tmp_path / "ip", monkeypatch))
    p = Pty(cli_argv(*data.launch_args(tmp_path)), data.env())
    assert p.wait_for(QUESTION_LAUNCH, 30), p.text()
    p.send("y\n")
    p.finish(60)
    assert [r[0] for r in sql_rows(data.ip.state_db, "SELECT user_id FROM launches")] == [None]
    assert len(sql_rows(data.ip.state_db, "SELECT * FROM jobs WHERE kind = 'launch_nextflow'")) == 1


def test_tc044_an_unknown_account_is_refused_before_the_question(d, tmp_path):
    # TC-044
    rc, screen = terminal(d, tmp_path, "--user", "nobody", answer=None)
    assert rc != 0 and QUESTION_LAUNCH not in screen and "nobody" in screen
    assert counts(d) == (0, 0, 0)


def test_tc045_a_terminal_launch_on_somebody_elses_environment_is_not_found(d, tmp_path):
    # TC-045
    d.bobs_environment()
    args = d.w.data.launch_args(tmp_path, extra=("--user", "alice"))
    args[args.index("--ce") + 1] = "b1"
    p = Pty(cli_argv(*args), d.w.data.env())
    rc, screen = p.finish(60)
    assert rc != 0 and QUESTION_LAUNCH not in screen and "找不到" in screen
    assert counts(d) == (0, 0, 0)


def test_tc046_naming_an_account_does_not_let_a_program_answer(d, tmp_path):
    # TC-046
    args = d.w.data.launch_args(tmp_path, extra=("--user", "alice"))
    done = subprocess.run(cli_argv(*args), env=d.w.data.env(), input="y\n", capture_output=True, text=True, timeout=120)
    assert done.returncode != 0 and "終端機" in done.stderr + done.stdout
    assert counts(d) == (0, 0, 0)


def test_tc047_launches_names_the_owner(d):
    # TC-047
    d.add_launch_row("run-mine", d.a.user_id)
    d.add_launch_row("run-old", None)
    rc, out = d.w.ip.run("launches")
    lines = out.splitlines()
    mine = [ln for ln in lines if ln.startswith("run-mine")][0]
    old = [ln for ln in lines if ln.startswith("run-old")][0]
    assert "alice" in mine and "(none: local only)" in old and "alice" not in old


def test_tc048_the_docs_say_the_honest_boundary():
    # TC-048
    root = PLATFORM_DIR.parent
    doc = (root / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    assert re.search(r"whoever has the shell can name any account", doc, re.I)
    assert "指名任何帳號" in doc and "--user" in doc
    assert "116" in (root / "CHANGELOG.md").read_text(encoding="utf-8")


# ---- US4: files stay in my own folder -----------------------------------------------------------------------------------

def test_tc049_a_cell_inside_the_read_roots_but_outside_my_folder_passes(d):
    # TC-049, rewritten by http-launch-site-samplesheet (maintainer ruling 2026-10-23): a cell inside the read roots and outside every upload
    # folder is the environment's business, so it passes; the old test expected a refusal naming the caller's folder.
    out = d.launch(d.a, cells=["%s/x.fq" % SHARED, "%s/y.fq" % SHARED])
    assert out["ok"] is True and out["state"] == "pending" and out["sent"] is False


def test_tc050_a_cell_inside_my_folder_passes(d):
    # TC-050
    out = d.launch(d.a)
    assert out["ok"] is True and out["state"] == "pending" and "rawdata/s01" in out["summary"]


def test_tc051_a_cell_in_somebody_elses_folder_is_refused_without_naming_it(d):
    # TC-051
    d.sheet(d.b)
    out = d.launch(d.a, cells=["%s/y.fq" % d.area(d.b), "%s/z.fq" % d.area(d.b)])
    assert out["ok"] is False and out["sent"] is False
    assert os.path.realpath(d.area(d.a)) in out["message"] and "bob" not in out["message"]
    assert counts(d) == (0, 0, 0)


def test_tc052_a_link_out_of_my_folder_does_not_lead_into_another(d):
    # TC-052
    d.area(d.b).mkdir(parents=True, exist_ok=True)
    d.area(d.a).mkdir(parents=True, exist_ok=True)
    os.symlink(str(d.area(d.b)), str(d.area(d.a) / "link"))
    out = d.launch(d.a, cells=["%s/link/y.fq" % d.area(d.a), "%s/link/z.fq" % d.area(d.a)])
    assert out["ok"] is False and out["sent"] is False and "bob" not in out["message"]
    assert counts(d) == (0, 0, 0)


def test_tc053_the_terminal_and_stdio_keep_the_old_roots(d):
    # TC-053
    from abf_launch import build
    cells = ["%s/x.fq" % SHARED, "%s/y.fq" % SHARED]
    sheet = d.sheet(d.a, cells)
    ce, bundle = build.prepare_launch(d.state, ce="lab-a", pipeline="nf-core/ampliseq", revision="2.18.0", run_name="run-t",
                                      samplesheet=str(sheet))
    assert [r[1] for r in bundle["samplesheet"][1:]] == cells
    out = d.launch(None, answer=form_answer(), sheet=sheet)
    assert out["sent"] is True


def test_tc055_tc056_tc057_listing_the_upload_folders(d):
    # TC-055, TC-056, TC-057
    from abf_platform import actions, store as st
    d.bobs_environment()
    area_a, area_b = d.area(d.a), d.area(d.b)
    sql_exec(d.state, "UPDATE agents SET last_seen_at = ?", (time.time() + 3600,))
    os.environ["ABF_PLATFORM_DEADLINE_LIST_SITE_FILES"] = "0.5"
    try:
        def listing(caller, ce, path):
            n = len(sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'list_site_files'"))
            out = asyncio.run(actions.list_site_files(d.state, ce, path, caller=caller))
            return out, len(sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'list_site_files'")) - n

        out, queued = listing(d.b, "b1", str(area_a))
        assert out["ok"] is False and queued == 0
        out, queued = listing(d.b, "b1", str(d.uploads))
        assert out["ok"] is False and queued == 0
        out, queued = listing(d.a, "lab-a", str(area_a))
        assert queued == 1
        out, queued = listing(d.a, "lab-a", str(area_a / "rawdata"))
        assert queued == 1
        out, queued = listing(d.a, "lab-a", "/data/w1")
        assert queued == 1
        out, queued = listing(d.a, "lab-a", SHARED)
        assert queued == 1
    finally:
        del os.environ["ABF_PLATFORM_DEADLINE_LIST_SITE_FILES"]


def test_tc058_no_folder_of_a_person_is_made_on_the_site(d):
    # TC-058
    out = d.sent(d.a)
    job = d.w.jobs("launch_nextflow")[0]
    bundle = json.loads(job["args_json"])["bundle"]
    assert bundle["run_folder"] == "/data/w1/runs/run-one" and "alice" not in json.dumps(bundle["ce"])
    src = "\n".join(p.read_text(encoding="utf-8") for p in (PLATFORM_DIR / "abf_station").glob("*.py"))
    assert "uploads_root" not in src


# ---- US5: old data and the upgrade ---------------------------------------------------------------------------------------

def old_rows(ip):
    """An environment, an agent and a launch with no owner: the platform before 116 (users added afterwards)."""
    rc, out = ip.create_slurm("x1")
    assert rc == 0, out
    from abf_platform import agents
    agents.register(ip.state_db, "ag", "0.1.0", time.time)
    sql_exec(ip.state_db, "INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at) VALUES ('r-old', '/f', 'x1', 'ag', 1)")


def owners(ip):
    return ([r[0] for r in sql_rows(ip.state_db, "SELECT owner_user_id FROM compute_envs")],
            [r[0] for r in sql_rows(ip.state_db, "SELECT owner_user_id FROM agents")],
            [r[0] for r in sql_rows(ip.state_db, "SELECT user_id FROM launches")])


def test_tc059_one_user_adopts_every_orphan(tmp_path, monkeypatch):
    # TC-059
    ip = Inproc(tmp_path / "ip", monkeypatch)
    old_rows(ip)
    uid = store().create_user(ip.tokens, "alice", "lab-x")
    store().assign_orphans(ip.state_db, ip.tokens)
    assert owners(ip) == ([uid], [uid], [uid])


def test_tc060_two_users_adopt_nothing(tmp_path, monkeypatch):
    # TC-060
    ip = Inproc(tmp_path / "ip", monkeypatch)
    old_rows(ip)
    store().create_user(ip.tokens, "alice", "lab-x")
    store().create_user(ip.tokens, "bob", "lab-x")
    store().assign_orphans(ip.state_db, ip.tokens)
    assert owners(ip) == ([None], [None], [None])
    from abf_platform import actions
    for name in ("alice", "bob"):
        who = actions.Caller(store().user_id_of(ip.tokens, name), name, "lab-x")
        assert actions.list_compute_envs(ip.state_db, caller=who) == {"compute_envs": []}
        assert actions.list_agents(ip.state_db, caller=who) == {"agents": []}
        assert actions.get_compute_env(ip.state_db, "x1", caller=who)["found"] is False


def test_tc061_tc062_the_mark_is_written_only_when_a_user_exists(tmp_path, monkeypatch):
    # TC-061, TC-062
    ip = Inproc(tmp_path / "ip", monkeypatch)
    old_rows(ip)
    digest = all_files_digest(ip.state_db)
    store().assign_orphans(ip.state_db, ip.tokens)
    assert all_files_digest(ip.state_db) == digest and owners(ip) == ([None], [None], [None])
    assert store().get_meta(ip.state_db, "owners_assigned") is None
    store().create_user(ip.tokens, "alice", "lab-x")
    store().assign_orphans(ip.state_db, ip.tokens)
    assert store().get_meta(ip.state_db, "owners_assigned")


def test_tc063_a_second_start_changes_nothing(tmp_path, monkeypatch):
    # TC-063
    ip = Inproc(tmp_path / "ip", monkeypatch)
    old_rows(ip)
    store().create_user(ip.tokens, "alice", "lab-x")
    store().assign_orphans(ip.state_db, ip.tokens)
    digest = all_files_digest(ip.state_db, ip.tokens)
    store().assign_orphans(ip.state_db, ip.tokens)
    assert all_files_digest(ip.state_db, ip.tokens) == digest


@pytest.mark.parametrize("start", ["serve", "mcp", "web", "ce", "launch"])
def test_tc064_every_start_assigns_the_orphans(tmp_path, monkeypatch, start):
    # TC-064
    import uvicorn
    from abf_platform import cli, mcp_server
    ip = Inproc(tmp_path / "ip", monkeypatch)
    old_rows(ip)
    uid = store().create_user(ip.tokens, "alice", "lab-x")
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: None)
    monkeypatch.setattr(mcp_server, "run_stdio", lambda *a, **k: None)
    argv = {"serve": ["serve"], "mcp": ["mcp"], "web": ["web"], "ce": ["ce", "list"],
            "launch": ["launch", "--user", "nobody", "--pipeline", "nf-core/x", "--revision", "2.18.0", "--run-name", "r",
                       "--samplesheet", str(tmp_path / "none.csv")]}[start]
    ip.run(*argv)
    assert owners(ip) == ([uid], [uid], [uid])


def test_tc065_rebuild_never_opens_the_platform_or_the_tokens(tmp_path, monkeypatch):
    # TC-065
    ip = Inproc(tmp_path / "ip", monkeypatch)
    old_rows(ip)
    store().create_user(ip.tokens, "alice", "lab-x")
    stat = lambda p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
    before = (stat(ip.state_db), stat(ip.tokens))
    opened = []
    real = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda p, *a, **k: (opened.append(str(p)), real(p, *a, **k))[1])
    folder = tmp_path / "launch-folder"
    folder.mkdir()
    ip.run("rebuild", str(folder))
    assert not [p for p in opened if "platform.db" in p or "tokens.db" in p], opened
    assert (stat(ip.state_db), stat(ip.tokens)) == before


def test_tc066_a_database_from_before_116_is_upgraded_in_place(tmp_path):
    # TC-066
    db = tmp_path / "platform.db"
    store().connect_state(db).close()
    con = sqlite3.connect(str(db))
    for table, col in (("compute_envs", "owner_user_id"), ("agents", "owner_user_id"), ("launches", "user_id")):
        con.execute("ALTER TABLE %s DROP COLUMN %s" % (table, col))
    con.execute("INSERT INTO compute_envs (name, platform, status, config_json, created_at, updated_at) VALUES ('c', 'slurm-platform', 'available', '{}', 1, 1)")
    con.execute("INSERT INTO agents (name, first_seen_at, last_seen_at) VALUES ('a', 1, 1)")
    con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at) VALUES ('r', '/f', 'c', 'a', 1)")
    con.commit()
    old_cols = [r[1] for r in con.execute("PRAGMA table_info(launches)")]
    assert "user_id" not in old_cols
    con.close()
    store().connect_state(db).close()
    con = sqlite3.connect(str(db))
    cols = [r[1] for r in con.execute("PRAGMA table_info(launches)")]
    assert cols == old_cols + ["user_id"]
    assert "owner_user_id" in [r[1] for r in con.execute("PRAGMA table_info(compute_envs)")]
    assert "owner_user_id" in [r[1] for r in con.execute("PRAGMA table_info(agents)")]
    assert con.execute("SELECT run_name, user_id FROM launches").fetchall() == [("r", None)]
    assert con.execute("SELECT name, owner_user_id FROM compute_envs").fetchall() == [("c", None)]
    digest = all_files_digest(db)
    store().connect_state(db).close()
    assert all_files_digest(db) == digest


def test_tc067_old_runs_are_for_the_terminal_only(d):
    # TC-067
    d.add_run("r-old", None)
    assert d.run_names(d.a) == [] and d.run_names(d.b) == [] and d.run_names(None) == ["r-old"]
    rc, out = d.w.ip.run("launches")
    assert "r-old" in out and "(none: local only)" in out
    client = d.w.web()
    assert d.w.login(client, "alice").status_code == 303 and "r-old" not in client.get("/").text


def test_tc068_no_new_way_to_log_in(w):
    # TC-068
    client = w.web()
    # 009i: the login is still the one name + web password; 011a added the board; the other routes added are the OAuth ones, which log nobody in
    assert {r.path for r in client.app.routes} == {"/", "/settings", "/login", "/logout", "/c/{rid}", "/consent/{rid}", "/authorize", "/token",
                                                   "/register", "/revoke", "/.well-known/oauth-authorization-server",
                                                   "/launch", "/act/{verb}"}      # 012b: the launch form and the three asking buttons; none of them logs anybody in
    page = (PLATFORM_DIR / "abf_platform" / "web.py").read_text(encoding="utf-8")
    assert set(re.findall(r"store\.(\w+)", page)) == {"MAX_PASSWORD_CHARS", "MIN_PASSWORD_CHARS", "WEB_SESSION_SECONDS", "check_web_password",
                                                     "create_web_session", "default_tokens_path", "end_web_session", "set_meta",
                                                     "web_session_user"}
    cli_src = (PLATFORM_DIR / "abf_platform" / "cli.py").read_text(encoding="utf-8")
    assert not re.search(r"openid|saml|ldap", cli_src, re.I)
    assert {m.lower() for m in re.findall(r"oauth\w*", cli_src, re.I)} <= {"oauth", "oauth_revoke", "oauth_command", "oauth_tokens"}      # 009i: only `oauth revoke`
    auth = (PLATFORM_DIR / "abf_platform" / "http_auth.py").read_text(encoding="utf-8")
    assert set(re.findall(r"store\.(\w+)", auth)) == {"lookup_pat", "lookup_oauth_access", "get_meta", "default_tokens_path"}      # 009i: the OAuth lookup


# ---- launch-site-pipeline (M1-02): the three site keys and the site-module bundle are one person's, like the rest -------------------

SITE_NAMES = ("biology/", "NFCORE_AMPLISEQ_HOME", "NFCORE_SITE_CONFIG", "NFCORE_SITE_REFERENCES", "site-module", "pipeline_source",
              "sitePipelines", "siteConfigVars")


def _alice_site_env(d):
    """alice's environment lab-a carries the three keys (written the way `ce create --config-json` stores them)."""
    from test_launch_bundle import SITE_CE
    cfg = json.loads(sql_rows(d.state, "SELECT config_json FROM compute_envs WHERE name = 'lab-a'")[0][0])
    cfg.update(json.loads(json.dumps(SITE_CE)))
    sql_exec(d.state, "UPDATE compute_envs SET config_json = ? WHERE name = 'lab-a'", (json.dumps(cfg),))


def test_tc_ls_50_somebody_elses_site_launch_is_not_readable_and_shows_none_of_its_site_names(d, w):
    # TC-LS-50 (read): bob cannot read alice's launch (bundle, pipeline_source), her request page, her run, or the three keys of her environment
    _alice_site_env(d)
    d.w.hand_over("run-one", by=d.a)
    kept = json.loads(sql_rows(d.state, "SELECT bundle_json FROM confirmations WHERE bundle_json IS NOT NULL")[0][0])
    assert kept["pipeline_source"]["kind"] == "site-module" and "NFCORE_AMPLISEQ_HOME" in kept["files"]["head.sh"]      # there is something to hide
    rid_run = d.add_run("run-one", d.a.user_id, launch_row=False)
    pending = pending_id_of(d.launch(d.a, run="run-two")["confirmation_url"])
    assert d.call("get_compute_env", {"name": "lab-a"}, caller=d.a)["config"]["sitePipelines"][0]["home"] == "NFCORE_AMPLISEQ_HOME"      # alice sees her own
    seen = []
    other = d.call("get_run", {"run_id": rid_run}, caller=d.b)
    missing = d.call("get_run", {"run_id": "id-nonesuch"}, caller=d.b)
    assert other["found"] is False and words(other, rid_run) == words(missing, "id-nonesuch")
    seen.append(other)
    env_other = d.call("get_compute_env", {"name": "lab-a"}, caller=d.b)
    env_missing = d.call("get_compute_env", {"name": "nonesuch"}, caller=d.b)
    assert env_other["found"] is False and "config" not in env_other and words(env_other, "lab-a") == words(env_missing, "nonesuch")
    seen += [env_other, d.call("list_compute_envs", caller=d.b), d.call("list_runs", caller=d.b)]
    for verb in ("resume", "relaunch"):      # these two copy alice's kept bundle: bob is told what he is told about a run that does not exist
        theirs = d.call(verb, {"run_name": "run-one"}, caller=d.b, answer=form_answer())
        none = d.call(verb, {"run_name": "run-none"}, caller=d.b, answer=form_answer())
        assert theirs["ok"] is False and theirs["sent"] is False and "job_id" not in theirs, (verb, theirs)
        assert words(theirs, "run-one") == words(none, "run-none"), (verb, theirs, none)
        seen.append(theirs)
    client = w.web()
    assert w.login(client, "bob").status_code == 303
    page = client.get("/c/" + pending)
    assert page.status_code == 403
    seen.append(page.text)
    text = json.dumps(seen, ensure_ascii=False)
    for name in SITE_NAMES + ("run-two",):
        assert name not in text, name


def test_tc_ls_51_somebody_elses_site_launch_cannot_be_confirmed_or_cancelled_and_nothing_changes(d, w):
    # TC-LS-51 (write): bob cannot say yes to alice's waiting launch, cancel her launched run, or resume it; her records and the queue stay as they are
    _alice_site_env(d)
    d.w.hand_over("run-one", by=d.a)
    pending = pending_id_of(d.launch(d.a, run="run-two")["confirmation_url"])
    before = (sql_rows(d.state, "SELECT id, state, bundle_json, used_at FROM confirmations ORDER BY id"),
              sql_rows(d.state, "SELECT id, kind, state, args_json FROM jobs ORDER BY id"),
              sql_rows(d.state, "SELECT run_name, slurm_job_id, cancel_requested_at, user_id FROM launches ORDER BY id"))
    client = w.web()
    assert w.login(client, "bob").status_code == 303
    page = client.get("/c/" + pending)
    assert page.status_code == 403
    posted = client.post("/c/" + pending, data={"csrf": csrf_of(page.text) or "x"})
    assert posted.status_code == 403
    cancelled = d.call("cancel", {"run_name": "run-one"}, caller=d.b, answer=form_answer())
    missing = d.call("cancel", {"run_name": "run-none"}, caller=d.b, answer=form_answer())
    assert cancelled["ok"] is False and cancelled["sent"] is False and "job_id" not in cancelled
    assert words(cancelled, "run-one") == words(missing, "run-none")
    resumed = d.call("resume", {"run_name": "run-one"}, caller=d.b, answer=form_answer())
    assert resumed["sent"] is False and "job_id" not in resumed
    after = (sql_rows(d.state, "SELECT id, state, bundle_json, used_at FROM confirmations ORDER BY id"),
             sql_rows(d.state, "SELECT id, kind, state, args_json FROM jobs ORDER BY id"),
             sql_rows(d.state, "SELECT run_name, slurm_job_id, cancel_requested_at, user_id FROM launches ORDER BY id"))
    assert [[tuple(r) for r in t] for t in after] == [[tuple(r) for r in t] for t in before]
    assert d.w.jobs("cancel_run") == []
