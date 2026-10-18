# Nothing existing: tests of the platform side of the agent protocol (tokens, hello, poll, result, jobs); the protocol is ours.
"""Agent protocol on the platform side, in process with a fake clock (feature 007)."""
import asyncio
import concurrent.futures
import hashlib
import re
import sqlite3

import pytest

from helpers import (Clock, Platform, all_files_digest, basic_header, db_bytes, load_scenario, pkg_env, run_cli)
from station_harness import snapshot

H = 20  # docs/PLATFORM.md and abf_platform.common.AGENT_HEARTBEAT_SECONDS say the same


def state_db(plat):
    return plat.dir / "platform.db"


def bearer(token):
    return {"Authorization": "Bearer " + token}


def agent_token(plat, name):
    return plat.store.create_token(plat.tokens, kind="agent", agent_name=name)


def hello(plat, token, name="a1", version="0.1.0"):
    return plat.client.post("/agent/hello", json={"name": name, "version": version}, headers=bearer(token))


def poll(plat, token, name="a1"):
    return plat.client.post("/agent/poll", json={"name": name}, headers=bearer(token))


def count(plat, table):
    con = sqlite3.connect(str(state_db(plat)))
    try:
        return con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
    finally:
        con.close()


def make_ce(plat, name="lab-a", agent="a1", owner_user_id=None, **config):
    from abf_platform import compute_envs
    cfg = {"workDir": "/data/work", "launchDir": "/data/launch", "headQueue": "normal"}
    cfg.update(config)
    return compute_envs.create(state_db(plat), {"name": name, "platform": "slurm-platform", "agent": agent,
                                                "config": cfg, "owner_user_id": owner_user_id}, plat.clock)


@pytest.fixture(autouse=True)
def short_poll(monkeypatch):
    # the long-poll time is shortened with the documented setting
    monkeypatch.setenv("ABF_AGENT_POLL_SECONDS", "0.6")


def test_tc002_online_until_three_heartbeats_then_offline_and_a_query_writes_nothing(tmp_path):
    # TC-002
    from abf_platform import agents, common
    assert common.AGENT_HEARTBEAT_SECONDS == H
    clock = Clock()
    plat = Platform(tmp_path / "p", clock=clock)
    tok = agent_token(plat, "a1")
    assert hello(plat, tok).status_code == 200
    t = clock()
    digest = all_files_digest(plat.index, plat.tokens, state_db(plat))
    seen = {}
    for dt in (3 * H - 1, 3 * H + 1):
        views = agents.list_agents(state_db(plat), t + dt)
        assert len(views) == 1
        seen[dt] = views[0]["status"]
    assert seen == {3 * H - 1: "online", 3 * H + 1: "offline"}
    assert all_files_digest(plat.index, plat.tokens, state_db(plat)) == digest


def test_tc007_no_token_or_a_made_up_token_is_401_on_all_three_endpoints(tmp_path):
    # TC-007
    plat = Platform(tmp_path / "p")
    before = (count(plat, "agents"), count(plat, "jobs"))
    for headers in ({}, bearer("abf_" + "x" * 40), bearer("garbage"), {"Authorization": "Basic !!!"}):
        for path in ("/agent/hello", "/agent/poll", "/agent/result/1"):
            r = plat.client.post(path, json={"name": "a1", "state": "done", "result": {}}, headers=headers)
            assert r.status_code == 401, (path, headers, r.status_code)
    assert (count(plat, "agents"), count(plat, "jobs")) == before


def test_tc008_run_tokens_and_agent_tokens_do_not_cross(tmp_path):
    # TC-008
    plat = Platform(tmp_path / "p")
    run_tok = plat.new_token()
    ag_tok = agent_token(plat, "a1")
    before = (count(plat, "agents"), count(plat, "jobs"), plat.counts()["runs"])
    for path in ("/agent/hello", "/agent/poll", "/agent/result/1"):
        r = plat.client.post(path, json={"name": "a1"}, headers=bearer(run_tok))
        assert r.status_code in (401, 403), path
        r = plat.client.post(path, json={"name": "a1"}, headers={"Authorization": basic_header(run_tok)})
        assert r.status_code in (401, 403), path
    body = load_scenario("ok_run")["requests"][0]["body"]
    for scheme in ("basic", "bearer"):
        r = plat.send("POST", "/trace/create", body, token=ag_tok, scheme=scheme)
        assert r.status_code in (401, 403)
        assert plat.send("PUT", "/trace/0123456789abcdef/progress", {"progress": {}}, token=ag_tok,
                         scheme=scheme).status_code in (401, 403)
        assert plat.send("GET", "/user-info", token=ag_tok, scheme=scheme).status_code in (401, 403)
    assert (count(plat, "agents"), count(plat, "jobs"), plat.counts()["runs"]) == before


def test_tc009_a_008_token_file_without_a_kind_column_is_upgraded_and_stays_a_run_token(tmp_path):
    # TC-009
    plat0 = Platform(tmp_path / "seed")  # only to get the schema of the run index
    del plat0
    d = tmp_path / "old"
    d.mkdir()
    token = "abf_" + "o" * 43
    con = sqlite3.connect(str(d / "tokens.db"))
    con.execute("CREATE TABLE tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, token_hash TEXT NOT NULL UNIQUE, "
                "created_at REAL NOT NULL)")
    con.execute("INSERT INTO tokens (token_hash, created_at) VALUES (?, 1.0)",
                (hashlib.sha256(token.encode()).hexdigest(),))
    con.commit()
    con.close()
    plat = Platform(d)
    body = load_scenario("ok_run")["requests"][0]["body"]
    assert plat.send("POST", "/trace/create", body, token=token).status_code < 300
    assert poll(plat, token).status_code in (401, 403)
    cols = [r[1] for r in sqlite3.connect(str(d / "tokens.db")).execute("PRAGMA table_info(tokens)")]
    assert "kind" in cols and "agent_name" in cols
    new = agent_token(plat, "a1")
    assert hello(plat, new).status_code == 200
    r = poll(plat, new)
    assert r.status_code == 200 and r.json()["job"] is None


def test_tc010_agent_tokens_are_shown_once_distinct_hashed_and_survive_a_restart(tmp_path):
    # TC-010
    env = pkg_env(ABF_PLATFORM_DB=tmp_path / "data" / "index.db")
    a = run_cli(["agent-token", "new", "alpha"], env=env)
    b = run_cli(["agent-token", "new", "beta"], env=env)
    assert a.returncode == 0 and b.returncode == 0, a.stderr + b.stderr
    ta = re.findall(r"abf_[A-Za-z0-9_-]{20,}", a.stdout)
    tb = re.findall(r"abf_[A-Za-z0-9_-]{20,}", b.stdout)
    assert len(ta) == 1 and len(tb) == 1 and ta[0] != tb[0]
    assert len(ta[0]) >= 32 and len(tb[0]) >= 32
    blob = db_bytes(tmp_path / "data" / "tokens.db", tmp_path / "data" / "platform.db", tmp_path / "data" / "index.db")
    assert ta[0].encode() not in blob and tb[0].encode() not in blob
    assert hashlib.sha256(ta[0].encode()).hexdigest().encode() in blob
    assert a.stdout.count(ta[0]) == 1 and ta[0] not in a.stderr
    from starlette.testclient import TestClient
    from abf_platform import receiver
    app = receiver.create_app(tmp_path / "data" / "index.db", tmp_path / "data" / "tokens.db")
    client = TestClient(app)
    r = client.post("/agent/hello", json={"name": "alpha", "version": "0.1.0"}, headers=bearer(ta[0]))
    assert r.status_code == 200


def test_tc011_a_token_for_one_name_cannot_say_it_is_another(tmp_path):
    # TC-011
    plat = Platform(tmp_path / "p")
    tok = agent_token(plat, "agent-a")
    r = hello(plat, tok, name="agent-b")
    assert r.status_code in (401, 403)
    r = poll(plat, tok, name="agent-b")
    assert r.status_code in (401, 403)
    con = sqlite3.connect(str(state_db(plat)))
    names = [x[0] for x in con.execute("SELECT name FROM agents")]
    con.close()
    assert "agent-b" not in names
    assert hello(plat, tok, name="agent-a").status_code == 200


def test_tc017_two_connections_polling_at_once_claim_a_job_exactly_once(tmp_path):
    # TC-017
    from abf_platform import jobs
    clock = Clock()
    plat = Platform(tmp_path / "p", clock=clock)
    tok = agent_token(plat, "a1")
    assert hello(plat, tok).status_code == 200
    make_ce(plat)
    job_id = jobs.enqueue_preflight(state_db(plat), "lab-a", clock)
    with concurrent.futures.ThreadPoolExecutor(2) as ex:
        futs = [ex.submit(poll, plat, tok) for _ in range(2)]
        got = [f.result().json()["job"] for f in futs]
    assert sorted(1 if j else 0 for j in got) == [0, 1], got
    claimed = [j for j in got if j][0]
    assert claimed["id"] == job_id and claimed["kind"] == "preflight"
    assert poll(plat, tok).json()["job"] is None
    con = sqlite3.connect(str(state_db(plat)))
    assert con.execute("SELECT state FROM jobs WHERE id = ?", (job_id,)).fetchone()[0] == "claimed"
    con.close()


def test_tc018_a_job_belongs_to_the_agent_of_its_environment(tmp_path):
    # TC-018
    from abf_platform import jobs
    clock = Clock()
    plat = Platform(tmp_path / "p", clock=clock)
    ta, tb = agent_token(plat, "agent-a"), agent_token(plat, "agent-b")
    assert hello(plat, ta, name="agent-a").status_code == 200
    assert hello(plat, tb, name="agent-b").status_code == 200
    make_ce(plat, agent="agent-a")
    job_id = jobs.enqueue_preflight(state_db(plat), "lab-a", clock)
    assert poll(plat, tb, name="agent-b").json()["job"] is None
    con = sqlite3.connect(str(state_db(plat)))
    before = con.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchall()
    r = plat.client.post("/agent/result/%d" % job_id, json={"state": "done", "result": {"ok": True, "checks": []}},
                         headers=bearer(tb))
    assert r.status_code in (403, 404)
    assert con.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchall() == before
    con.close()
    got = poll(plat, ta, name="agent-a").json()["job"]
    assert got and got["id"] == job_id


def test_tc047_an_offline_agent_is_refused_at_once_and_nothing_is_queued(tmp_path):
    # TC-047
    from abf_platform import jobs
    clock = Clock()
    plat = Platform(tmp_path / "p", clock=clock)
    tok = agent_token(plat, "a1")
    assert hello(plat, tok).status_code == 200
    make_ce(plat)
    clock.t += 3 * H + 1
    before = snapshot_rows(plat)
    for call in (lambda: jobs.enqueue_preflight(state_db(plat), "lab-a", clock),
                 lambda: jobs.enqueue_listing(state_db(plat), "lab-a", "/data/work", clock)):
        with pytest.raises(jobs.JobRefused) as e:
            call()
        assert re.search(r"offline|離線", str(e.value)) and "a1" in str(e.value)
    assert snapshot_rows(plat) == before


def snapshot_rows(plat):
    con = sqlite3.connect(str(state_db(plat)))
    try:
        return {t: con.execute("SELECT * FROM " + t).fetchall() for t in ("compute_envs", "agents", "jobs")}
    finally:
        con.close()


def test_tc019_a_late_result_changes_nothing_and_an_expired_job_is_never_handed_out(tmp_path):
    # TC-019 (platform half, with a fake clock; the real-process half is in test_station_e2e.py)
    from abf_platform import jobs
    clock = Clock()
    plat = Platform(tmp_path / "p", clock=clock)
    tok = agent_token(plat, "a1")
    assert hello(plat, tok).status_code == 200
    make_ce(plat)
    # a job that was handed out, then the caller's wait ran out
    jid = jobs.enqueue_preflight(state_db(plat), "lab-a", clock, deadline_seconds=30)
    job = poll(plat, tok).json()["job"]
    assert job["id"] == jid

    async def fake_sleep(s):
        clock.t += s

    out = asyncio.run(jobs.wait_for_result(state_db(plat), jid, clock, sleep=fake_sleep))
    assert out["ok"] is False and re.search(r"did not answer|沒有回應", out["message"])
    assert "a1" in out["message"] and "preflight" in out["message"]
    con = sqlite3.connect(str(state_db(plat)))
    assert con.execute("SELECT state FROM jobs WHERE id = ?", (jid,)).fetchone()[0] == "expired"
    ce_before = con.execute("SELECT status, message, updated_at FROM compute_envs WHERE name = 'lab-a'").fetchone()
    # the agent was busy and answers late, with a verdict that would change the environment
    late = {"state": "done", "result": {"ok": False, "checks": [{"name": "sinfo", "status": "fail", "detail": "late"}]}}
    r = plat.client.post("/agent/result/%d" % jid, json=late, headers=bearer(tok))
    assert r.status_code == 200 and r.json().get("late") is True
    assert con.execute("SELECT status, message, updated_at FROM compute_envs WHERE name = 'lab-a'").fetchone() == ce_before
    assert con.execute("SELECT state FROM jobs WHERE id = ?", (jid,)).fetchone()[0] == "expired"
    assert con.execute("SELECT late_result_json FROM jobs WHERE id = ?", (jid,)).fetchone()[0]
    # a job that nobody claimed before its deadline is not handed out afterwards either
    jid2 = jobs.enqueue_preflight(state_db(plat), "lab-a", clock, deadline_seconds=10)
    clock.t += 11
    assert poll(plat, tok).json()["job"] is None
    assert con.execute("SELECT state FROM jobs WHERE id = ?", (jid2,)).fetchone()[0] in ("queued", "expired")
    con.close()


def test_a_preflight_result_sets_the_environment_status_and_names_every_failure(tmp_path):
    # backs TC-042/043/049 on the platform side: the verdict of the agent is applied in both directions
    from abf_platform import jobs, compute_envs
    clock = Clock()
    plat = Platform(tmp_path / "p", clock=clock)
    tok = agent_token(plat, "a1")
    assert hello(plat, tok).status_code == 200
    make_ce(plat)
    for ok, want in ((False, "invalid"), (True, "available"), (False, "invalid")):
        jid = jobs.enqueue_preflight(state_db(plat), "lab-a", clock)
        assert poll(plat, tok).json()["job"]["id"] == jid
        checks = [{"name": "java", "status": "pass" if ok else "fail", "detail": "Java 11, 17 needed"},
                  {"name": "nextflow", "status": "pass" if ok else "fail", "detail": "not found"}]
        r = plat.client.post("/agent/result/%d" % jid, json={"state": "done", "result": {"ok": ok, "checks": checks}},
                             headers=bearer(tok))
        assert r.status_code == 200
        ce = compute_envs.get(state_db(plat), "lab-a")
        assert ce["status"] == want
        if not ok:
            assert "java" in ce["message"] and "nextflow" in ce["message"]
        clock.t += 5


def test_tc090_the_new_tables_have_no_run_state_and_the_job_kinds_are_locked_in_sql(tmp_path):
    # TC-090 (database half)
    plat = Platform(tmp_path / "p")
    con = sqlite3.connect(str(state_db(plat)))
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    assert {"compute_envs", "agents", "jobs"} <= set(tables)
    for t in tables:
        for col in [c[1].lower() for c in con.execute("PRAGMA table_info(%s)" % t)] + [t]:
            for word in ("run", "workflow", "session", "task", "exit"):
                # feature 007b (TC-060): the hand-off record names a run and its folder, and nothing else here does
                if word == "run" and (t, col) in (("launches", "run_name"), ("launches", "run_folder"), ("launches", "parent_run")):    # 009e: parent_run, the run this one is an attempt of
                    continue
                assert word not in col, (t, col)
    for kind in ("rm", "launch", "scancel", "write_file", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                        "VALUES ('a1', 'x', ?, '{}', 'queued', 1, 2)", (kind,))
    # feature 007b (TC-060): exactly five kinds; the two that write need a confirmation
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('c1', 'x', 'launch', 1)")
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('c2', 'x', 'cancel', 1)")
    for kind, cid in (("preflight", None), ("list_site_files", None), ("launch_nextflow", "c1"), ("cancel_run", "c2"),
                      ("fetch_run_records", None)):
        con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
                    "VALUES ('a1', 'x', ?, '{}', 'queued', 1, 2, ?)", (kind, cid))
    declared = re.search(r"kind TEXT NOT NULL CHECK \(kind IN \(([^)]*)\)\)",
                         con.execute("SELECT sql FROM sqlite_master WHERE name = 'jobs'").fetchone()[0]).group(1)
    assert set(re.findall(r"'([a-z_]+)'", declared)) == {"preflight", "list_site_files", "launch_nextflow", "cancel_run",
                                                         "fetch_run_records"}
    con.close()


def test_job_results_older_than_seven_days_are_pruned_when_a_job_is_queued_never_on_a_read(tmp_path):
    # plan Revision 2, limits
    from abf_platform import jobs, agents
    clock = Clock()
    plat = Platform(tmp_path / "p", clock=clock)
    tok = agent_token(plat, "a1")
    assert hello(plat, tok).status_code == 200
    make_ce(plat)
    jid = jobs.enqueue_preflight(state_db(plat), "lab-a", clock)
    poll(plat, tok)
    plat.client.post("/agent/result/%d" % jid, json={"state": "done", "result": {"ok": True, "checks": []}},
                     headers=bearer(tok))
    clock.t += 8 * 86400
    hello(plat, tok)
    digest = all_files_digest(state_db(plat))
    agents.list_agents(state_db(plat), clock())
    assert all_files_digest(state_db(plat)) == digest
    assert count(plat, "jobs") == 1
    jobs.enqueue_preflight(state_db(plat), "lab-a", clock)
    con = sqlite3.connect(str(state_db(plat)))
    ids = [r[0] for r in con.execute("SELECT id FROM jobs")]
    con.close()
    assert jid not in ids and len(ids) == 1


def test_a_long_poll_waits_for_a_job_and_returns_it_without_waiting_out_the_time(tmp_path, monkeypatch):
    # backs TC-014/TC-015: the poll is an asyncio deadline loop that notices a new job
    import threading
    import time
    from abf_platform import jobs
    monkeypatch.setenv("ABF_AGENT_POLL_SECONDS", "2")
    plat = Platform(tmp_path / "p", clock=lambda: time.time())
    tok = agent_token(plat, "a1")
    assert hello(plat, tok).status_code == 200
    make_ce(plat)
    t0 = time.time()
    r0 = plat.client.post("/agent/poll", json={"name": "a1"}, headers=bearer(tok))
    # nothing queued: the answer is "no job", after the whole poll time
    assert r0.status_code == 200 and r0.json()["job"] is None and time.time() - t0 >= 1.8

    def later():
        time.sleep(0.6)
        jobs.enqueue_preflight(state_db(plat), "lab-a", time.time)

    th = threading.Thread(target=later)
    th.start()
    t1 = time.time()
    r1 = plat.client.post("/agent/poll", json={"name": "a1"}, headers=bearer(tok))
    th.join()
    assert r1.json()["job"]["kind"] == "preflight"
    assert 0.4 <= time.time() - t1 <= 1.6
