# Nothing existing: tests of the platform side of launch and cancel (confirmations, hand-off record, run tokens, instance id); the tables and the rules are ours.
"""Platform side of feature 007b, in process with a fake clock: no agent process, no site."""
import json
import re
import sqlite3
import time

import pytest

from helpers import Clock, Platform, all_files_digest, basic_header, db_bytes, load_scenario, PLATFORM_DIR
from test_launch_bundle import inputs as bundle_inputs, facts as bundle_facts, ce_snapshot
from test_station_platform import agent_token, bearer, hello, make_ce, poll, state_db

OLD_STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS compute_envs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, description TEXT, platform TEXT NOT NULL,
    credentials_id TEXT, agent TEXT, status TEXT NOT NULL, message TEXT, is_primary INTEGER NOT NULL DEFAULT 0,
    checked_ok INTEGER, config_json TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL, last_used_at REAL
);
CREATE TABLE IF NOT EXISTS agents (
    name TEXT PRIMARY KEY, version TEXT, first_seen_at REAL NOT NULL, last_seen_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL, compute_env TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('preflight', 'list_site_files')), args_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('queued', 'claimed', 'done', 'refused', 'error', 'expired')),
    result_json TEXT, late_result_json TEXT, created_at REAL NOT NULL, deadline_at REAL NOT NULL, claimed_at REAL, finished_at REAL
);
"""
FACTS = bundle_facts()


@pytest.fixture(autouse=True)
def short_poll(monkeypatch):
    # the long-poll time is shortened with the documented setting
    monkeypatch.setenv("ABF_AGENT_POLL_SECONDS", "0.6")


def bundle(run="run-one", **over):
    from abf_station import launch
    return launch.render_bundle(**bundle_inputs(run_name=run, agent="a1", **over))


def make_confirmation(db, kind, b, sha=None, used=None, cid=None):
    from abf_platform import common
    import secrets
    cid = cid or secrets.token_hex(16)
    con = sqlite3.connect(str(db))
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, used_at, state) VALUES (?, ?, ?, ?, ?, 'confirmed')",
                (cid, sha or common.bundle_sha256(b), kind, time.time(), used))
    con.commit()
    con.close()
    return cid


def setup(tmp_path, clock=None, agent="a1"):
    """A platform in process with one online agent that reported its facts, and one available environment."""
    clock = clock or Clock()
    plat = Platform(tmp_path / "p", clock=clock)
    tok = agent_token(plat, agent)
    r = plat.client.post("/agent/hello", json={"name": agent, "version": "0.1.0", "facts": FACTS}, headers=bearer(tok))
    assert r.status_code == 200
    make_ce(plat, agent=agent, workDir="/data/w1", headJobOptions="-A ACCT-TEST-7 -c 4")
    con = sqlite3.connect(str(state_db(plat)))
    con.execute("UPDATE compute_envs SET status = 'available' WHERE name = 'lab-a'")
    con.commit()
    con.close()
    return plat, tok, clock


def own_all(plat, user_id):
    """116: what the setup made (environments, agents, launch records) belongs to this user, so a caller with this id may use it."""
    con = sqlite3.connect(str(state_db(plat)))
    with con:
        for table, col in (("compute_envs", "owner_user_id"), ("agents", "owner_user_id"), ("launches", "user_id")):
            con.execute("UPDATE %s SET %s = ?" % (table, col), (user_id,))
    con.close()


def sql(plat, text, args=()):
    con = sqlite3.connect(str(state_db(plat)))
    try:
        return con.execute(text, args).fetchall()
    finally:
        con.close()


# ---- TC-051: the upgrade of a platform.db made by 007 ---------------------------------------------------------

def _old_db(path):
    con = sqlite3.connect(str(path))
    con.executescript(OLD_STATE_SCHEMA)
    con.execute("INSERT INTO compute_envs (name, platform, agent, status, config_json, created_at, updated_at) "
                "VALUES ('lab-a', 'slurm-platform', 'a1', 'available', '{\"workDir\": \"/data/w1\"}', 1.0, 2.0)")
    con.execute("INSERT INTO agents (name, version, first_seen_at, last_seen_at) VALUES ('a1', '0.1.0', 1.0, 9.0)")
    con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, result_json, created_at, deadline_at, finished_at) "
                "VALUES ('a1', 'lab-a', 'preflight', '{\"ce\": {}}', 'done', '{\"ok\": true}', 3.0, 4.0, 5.0)")
    con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, late_result_json, created_at, deadline_at) "
                "VALUES ('a1', 'lab-a', 'list_site_files', '{}', 'expired', '{\"late\": 1}', 6.0, 7.0)")
    con.commit()
    rows = {t: con.execute("SELECT * FROM " + t).fetchall() for t in ("compute_envs", "agents", "jobs")}
    con.close()
    return rows


def test_tc051_a_platform_db_made_by_007_is_upgraded_and_keeps_every_row(tmp_path):
    # TC-051
    from abf_platform import store
    db = tmp_path / "platform.db"
    before = _old_db(db)
    store.connect_state(db).close()
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    # 116: the upgrade adds the owner column last, empty; the columns that were there are as they were
    assert [tuple(r)[:len(before["compute_envs"][0])] for r in con.execute("SELECT * FROM compute_envs")] == before["compute_envs"]
    assert [r["owner_user_id"] for r in con.execute("SELECT owner_user_id FROM compute_envs")] == [None]
    old_jobs = [tuple(r)[:12] for r in con.execute("SELECT * FROM jobs ORDER BY id")]
    assert old_jobs == before["jobs"]
    assert [r["confirmation_id"] for r in con.execute("SELECT confirmation_id FROM jobs")] == [None, None]
    agent_row = con.execute("SELECT * FROM agents").fetchone()
    assert (agent_row["name"], agent_row["version"], agent_row["first_seen_at"], agent_row["last_seen_at"]) == before["agents"][0]
    kinds = ("preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records", "read_task_log")
    cids = {"launch_nextflow": make_confirmation(db, "launch", {"run_name": "x"}),
            "cancel_run": make_confirmation(db, "cancel", {"run_name": "x"})}
    for k in kinds:
        con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
                    "VALUES ('a1', 'lab-a', ?, '{}', 'queued', 1, 2, ?)", (k, cids.get(k)))
    for k in ("rm", "sbatch", "scancel", "launch", "cancel", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                        "VALUES ('a1', 'lab-a', ?, '{}', 'queued', 1, 2)", (k,))
    for k in ("launch_nextflow", "cancel_run"):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
                        "VALUES ('a1', 'lab-a', ?, '{}', 'queued', 1, 2, NULL)", (k,))
    con.close()
    # a second opening finds nothing to do and changes nothing
    digest = all_files_digest(db)
    store.connect_state(db).close()
    assert all_files_digest(db) == digest


def test_tc051_an_error_in_the_middle_leaves_the_old_table_whole(tmp_path, monkeypatch):
    # TC-051: the copy fails after the new table is filled
    from abf_platform import store
    db = tmp_path / "platform.db"
    before = _old_db(db)

    def boom(step):
        if step == "copied":
            raise RuntimeError("injected failure")

    monkeypatch.setattr(store, "_migration_step", boom)
    with pytest.raises(RuntimeError):
        store.connect_state(db).close()
    con = sqlite3.connect(str(db))
    assert con.execute("SELECT * FROM jobs ORDER BY id").fetchall() == before["jobs"]
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "jobs_new" not in names
    assert "launch_nextflow" not in con.execute("SELECT sql FROM sqlite_master WHERE name = 'jobs'").fetchone()[0]
    con.close()
    monkeypatch.undo()
    store.connect_state(db).close()  # and it upgrades once the fault is gone
    con = sqlite3.connect(str(db))
    assert con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 2
    con.close()


def test_tc051_a_confirmation_id_belongs_to_one_job_only(tmp_path):
    # TC-051, TC-009
    from abf_platform import store
    db = tmp_path / "platform.db"
    store.connect_state(db).close()
    cid = make_confirmation(db, "launch", {"run_name": "x"})
    con = sqlite3.connect(str(db))
    ins = ("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
           "VALUES ('a1', 'lab-a', 'launch_nextflow', '{}', 'queued', 1, 2, ?)")
    con.execute(ins, (cid,))
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(ins, (cid,))
    con.close()


# ---- TC-055: the hand-off record -------------------------------------------------------------------------------

def test_tc055_launches_holds_the_facts_of_the_handover_and_no_state(tmp_path):
    # TC-055, TC-090
    from abf_platform import store
    db = tmp_path / "platform.db"
    store.connect_state(db).close()
    con = sqlite3.connect(str(db))
    cols = [r[1] for r in con.execute("PRAGMA table_info(launches)")]
    # follow-up 1 (F2): job_id links a row to the launch job it made; run_name is no longer unique, because a launch the agent
    # refused keeps its row and its name can be used again (the plan names this change; the rest of the test is as it was)
    assert sorted(cols) == sorted(["id", "run_name", "slurm_job_id", "run_folder", "ce", "agent", "confirmed_at",
                                   "submitted_at", "cancel_requested_at", "job_id", "user_id",      # 116: user_id, who sent it
                                   "parent_run", "attempt", "attempt_kind"])      # 009e: what a resume or a relaunch is made from, which attempt, which kind (last)
    for c in cols:
        assert not re.search(r"status|state|phase|result|exit|progress|ended", c), c
    unique = [r for r in con.execute("PRAGMA index_list(launches)") if r[2]]
    assert not any([i[2] for i in con.execute("PRAGMA index_info(%s)" % u[1])] == ["run_name"] for u in unique), "run_name may repeat"
    con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at) VALUES ('r', '/f', 'lab-a', 'a1', 1)")
    con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at) VALUES ('r', '/g', 'lab-a', 'a1', 2)")
    con.close()


# ---- TC-010, TC-009: nothing is queued without a confirmation -------------------------------------------------

def _refusals(plat, b, **kw):
    from abf_platform import jobs
    n = len(sql(plat, "SELECT id FROM jobs"))
    with pytest.raises(jobs.JobRefused):
        jobs.enqueue_launch(state_db(plat), "lab-a", b, **kw)
    assert len(sql(plat, "SELECT id FROM jobs")) == n


def test_tc010_tc008_the_public_queue_functions_refuse_a_launch_without_a_matching_confirmation(tmp_path):
    # TC-010, TC-009
    from abf_platform import jobs
    plat, tok, clock = setup(tmp_path)
    b = bundle()
    db = state_db(plat)
    _refusals(plat, b, confirmation_id=None)
    _refusals(plat, b, confirmation_id="")
    _refusals(plat, b, confirmation_id=12)
    _refusals(plat, b, confirmation_id=["x"])
    _refusals(plat, b, confirmation_id="no-such-confirmation")
    _refusals(plat, b, confirmation_id=make_confirmation(db, "cancel", b))                    # the wrong kind
    _refusals(plat, b, confirmation_id=make_confirmation(db, "launch", b, sha="0" * 64))      # another content
    _refusals(plat, b, confirmation_id=make_confirmation(db, "launch", b, used=time.time()))  # already used
    changed = json.loads(json.dumps(b))
    changed["files"]["head.sh"] += "# one more line\n"
    _refusals(plat, changed, confirmation_id=make_confirmation(db, "launch", b))               # content changed after the OK
    good = make_confirmation(db, "launch", b)
    jid = jobs.enqueue_launch(db, "lab-a", b, confirmation_id=good, clock=clock)
    rows = sql(plat, "SELECT kind, confirmation_id, args_json FROM jobs WHERE id = ?", (jid,))
    assert rows[0][0] == "launch_nextflow" and rows[0][1] == good
    args = json.loads(rows[0][2])
    assert set(args) == {"bundle", "confirmation_id", "bundle_sha256"}
    from abf_platform import common
    assert args["bundle_sha256"] == common.bundle_sha256(b) == args["bundle_sha256"]
    # and a confirmation is spent by its job: the same one cannot start a second
    _refusals(plat, b, confirmation_id=good)
    assert len(sql(plat, "SELECT id FROM jobs")) == 1


def test_tc010_cancel_follows_the_same_rule(tmp_path):
    # TC-010
    from abf_platform import jobs
    plat, tok, clock = setup(tmp_path)
    cancel = {"run_name": "run-one", "slurm_job_id": 4242, "run_folder": "/data/w1/runs/run-one", "agent": "a1",
              "ce": ce_snapshot()}
    db = state_db(plat)
    con = sqlite3.connect(str(db))
    con.execute("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at) "
                "VALUES ('run-one', 4242, '/data/w1/runs/run-one', 'lab-a', 'a1', 1, 2)")
    con.commit()
    con.close()
    for cid in (None, "", "nope", make_confirmation(db, "launch", cancel)):
        with pytest.raises(jobs.JobRefused):
            jobs.enqueue_cancel(db, "lab-a", cancel, confirmation_id=cid)
    jid = jobs.enqueue_cancel(db, "lab-a", cancel, confirmation_id=make_confirmation(db, "cancel", cancel), clock=clock)
    assert sql(plat, "SELECT kind FROM jobs WHERE id = ?", (jid,)) == [("cancel_run",)]


def test_tc010_there_is_no_door_for_a_launch_or_a_cancel_and_no_module_that_is_one(tmp_path):
    # TC-010
    plat, tok, clock = setup(tmp_path)
    run_tok = plat.new_token()
    before = (len(sql(plat, "SELECT * FROM jobs")), len(sql(plat, "SELECT * FROM confirmations")),
              len(sql(plat, "SELECT * FROM launches")))
    paths = ["/launch", "/cancel", "/confirm", "/confirmation", "/agent/launch", "/agent/cancel", "/agent/confirm",
             "/jobs", "/runs/abc/cancel", "/api/launch", "/workflow/launch"]
    for method in ("POST", "PUT", "DELETE", "GET"):
        for path in paths:
            for headers in ({}, bearer(tok), bearer(run_tok), {"Authorization": basic_header(run_tok)}):
                r = plat.client.request(method, path, json={"kind": "launch_nextflow", "confirmation_id": "x"}, headers=headers)
                assert r.status_code in (401, 404, 405), (method, path, r.status_code)
    assert before == (len(sql(plat, "SELECT * FROM jobs")), len(sql(plat, "SELECT * FROM confirmations")),
                      len(sql(plat, "SELECT * FROM launches")))
    # 009c: the MCP server and the web page now ask the action layer to make a pending request; they still reach neither the queue nor
    # the confirmation module. The receiver and the agents module never mention confirm or the queue writers, as before.
    for name in ("mcp_server.py", "receiver.py", "agents.py", "web.py"):
        text = (PLATFORM_DIR / "abf_platform" / name).read_text(encoding="utf-8")
        assert not re.search(r"enqueue_launch|enqueue_cancel|confirm_launch|confirm_cancel|confirm\.|import confirm|INSERT INTO "
                             r"(confirmations|jobs|launches)", text), name


def test_tc010_the_mcp_tools_are_six_read_only_ones_and_two_that_ask_a_person_without_a_yes_field(tmp_path, monkeypatch):
    # TC-010, TC-061. 009c: was "still six read-only ones"; launch and cancel are added, may not carry a field that says yes, and
    # the six are as before (read-only, no launch field)
    import asyncio
    from mcp import Client
    from abf_platform import mcp_server
    plat = Platform(tmp_path / "p")

    async def tools():
        async with Client(mcp_server.build_server(plat.index)) as c:
            return (await c.list_tools()).tools

    ts = asyncio.run(tools())
    # 009e: plus resume and relaunch, which are asked the same way and take the name of a run and nothing else
    assert sorted(t.name for t in ts) == ["cancel", "forget", "get_compute_env", "get_run", "launch", "list_agents", "list_compute_envs",
                                          "list_runs", "list_site_files", "read_task_log", "relaunch", "resume"]
    banned = {"confirm", "confirmation", "yes", "y", "launch", "cancel", "kind", "command", "fetch", "run_name", "pipeline"}
    saying_yes = {"confirm", "confirmed", "confirmation", "confirmation_id", "yes", "y", "approve", "approved", "kind", "command"}
    for t in ts:
        if t.name in ("launch", "cancel", "forget", "resume", "relaunch"):
            assert t.annotations.read_only_hint is False
            assert not (set(t.input_schema.get("properties", {})) & saying_yes), t.name
            continue
        assert t.annotations.read_only_hint is True
        # run-diag-tools: read_task_log names the run it reads about (plan, Goal 2: read_task_log(run_name, task, which)); it is the one read-only
        # tool allowed that argument, and it still has no field that could launch, cancel, confirm or name a kind or a command
        allowed = {"run_name"} if t.name == "read_task_log" else set()
        assert not (set(t.input_schema.get("properties", {})) & (banned - allowed)), t.name


# ---- TC-037: the instance id ---------------------------------------------------------------------------------

def test_tc037_the_platform_has_a_random_instance_id_that_survives_a_restart_and_differs_between_platforms(tmp_path):
    from abf_platform import store
    a = Platform(tmp_path / "a")
    ida = store.instance_id(state_db(a))
    assert re.fullmatch(r"[0-9a-f]{32}", ida)
    assert store.instance_id(state_db(a)) == ida
    again = Platform(tmp_path / "a")  # a restart: a new app on the same files
    assert store.instance_id(state_db(again)) == ida
    other = Platform(tmp_path / "b")
    assert store.instance_id(state_db(other)) != ida
    r = a.client.get("/user-info")
    assert r.status_code == 401 and r.headers["X-ABF-Platform"] == ida
    r = a.send("GET", "/user-info", token="abf_" + "z" * 40)
    assert r.status_code == 401 and r.headers["X-ABF-Platform"] == ida
    r = a.send("POST", "/trace/create", {"sessionId": "s", "runName": "r"})
    assert r.status_code == 401 and r.headers["X-ABF-Platform"] == ida
    assert ida.encode() not in db_bytes(a.index, a.tokens), "the id lives in platform.db only"


# ---- agent facts ----------------------------------------------------------------------------------------------

def test_the_agent_facts_of_hello_are_stored_and_bounded(tmp_path):
    # TC-021, TC-024: the account is stored on the agent row; nothing the agent says can make the platform store more
    from abf_platform import agents
    plat, tok, clock = setup(tmp_path)
    got = agents.get_facts(state_db(plat), "a1")
    assert got["slurm_account"] == "ACCT-TEST-7" and got["reach"] == "local" and got["platform_local"] is True
    assert sql(plat, "SELECT slurm_account FROM agents WHERE name = 'a1'") == [("ACCT-TEST-7",)]
    junk = {"slurm_account": "x" * 500, "reach": ["ssh"], "platform_local": "yes", "endpoint": 5, "evil": "x" * 10,
            "forward_file": "y" * 5000}
    r = plat.client.post("/agent/hello", json={"name": "a1", "version": "0.1.0", "facts": junk}, headers=bearer(tok))
    assert r.status_code == 200
    got = agents.get_facts(state_db(plat), "a1")
    assert got["slurm_account"] is None and got["reach"] is None and got["platform_local"] is None
    assert "evil" not in got and got["forward_file"] is None
    # a hello without facts (an older agent, a beat of 007) keeps what was reported before
    plat.client.post("/agent/hello", json={"name": "a1", "version": "0.1.0", "facts": FACTS}, headers=bearer(tok))
    plat.client.post("/agent/hello", json={"name": "a1", "version": "0.1.0"}, headers=bearer(tok))
    assert agents.get_facts(state_db(plat), "a1")["slurm_account"] == "ACCT-TEST-7"
    # and an agent that now says its account is unset is believed
    plat.client.post("/agent/hello", json={"name": "a1", "version": "0.1.0", "facts": dict(FACTS, slurm_account=None)},
                     headers=bearer(tok))
    assert agents.get_facts(state_db(plat), "a1")["slurm_account"] is None


# ---- TC-020, TC-039: the run token -----------------------------------------------------------------------------

def _queue_launch(plat, clock, run="run-one", deadline=None):
    from abf_platform import confirm
    b = bundle(run)
    cid, jid = confirm.confirm_launch(state_db(plat), "lab-a", b, clock=clock)
    return b, cid, jid


def tokens_rows(plat):
    con = sqlite3.connect(str(plat.tokens))
    try:
        return con.execute("SELECT kind, run_name, revoked_at, expires_at FROM tokens WHERE kind = 'run'").fetchall()
    finally:
        con.close()


def create_body(run):
    body = dict(load_scenario("nf2510_ok")["requests"][0]["body"])
    body["runName"] = run
    body["sessionId"] = "sess-" + run
    return body


def test_tc020_a_confirmation_makes_no_token_the_claim_does_and_only_its_hash_is_kept(tmp_path):
    # TC-020 steps 1 to 3
    plat, tok, clock = setup(tmp_path)
    assert tokens_rows(plat) == []
    b, cid, jid = _queue_launch(plat, clock)
    assert tokens_rows(plat) == [], "a queued job has no token yet"
    assert sql(plat, "SELECT used_at FROM confirmations WHERE id = ?", (cid,)) == [(None,)]
    job = poll(plat, tok).json()["job"]
    assert job["id"] == jid and job["kind"] == "launch_nextflow"
    assert job["confirmation"] == {"id": cid, "sha256": sql(plat, "SELECT sha256 FROM confirmations")[0][0], "kind": "launch"}
    plain = job["run_token"]
    assert plain.startswith("abf_") and len(plain) >= 32
    rows = tokens_rows(plat)
    assert len(rows) == 1 and rows[0][1] == "run-one" and rows[0][2] is None
    assert rows[0][3] and rows[0][3] - time.time() > 13.9 * 86400, "expires in 14 days"
    assert sql(plat, "SELECT used_at FROM confirmations WHERE id = ?", (cid,))[0][0] is not None
    blob = db_bytes(plat.index, plat.tokens, state_db(plat))
    assert plain.encode() not in blob, "the plain token is nowhere in a database"
    assert plain not in sql(plat, "SELECT args_json FROM jobs")[0][0]
    again = poll(plat, tok).json()["job"]
    assert again is None, "handed out once"
    assert len(tokens_rows(plat)) == 1
    assert set(json.loads(sql(plat, "SELECT args_json FROM jobs")[0][0])) == {"bundle", "confirmation_id", "bundle_sha256"}


def test_tc020_a_job_that_nobody_claimed_before_its_deadline_leaves_no_token(tmp_path):
    # TC-020 step 2
    from abf_platform import confirm, jobs
    plat, tok, clock = setup(tmp_path)
    b = bundle()
    confirm.confirm_launch(state_db(plat), "lab-a", b, clock=clock, deadline_seconds=10)
    clock.t += 11
    assert poll(plat, tok).json()["job"] is None
    assert tokens_rows(plat) == []


def test_tc020_the_token_is_for_one_run_name_only(tmp_path):
    # TC-020 step 3, TC-039
    plat, tok, clock = setup(tmp_path)
    _queue_launch(plat, clock)
    run_token = poll(plat, tok).json()["job"]["run_token"]
    for scheme in ("basic", "bearer"):
        r = plat.send("POST", "/trace/create", create_body("other-run"), token=run_token, scheme=scheme)
        assert r.status_code in (401, 403), scheme
    assert plat.counts()["runs"] == 0
    r = plat.send("POST", "/trace/create", create_body("run-one"), token=run_token)
    assert r.status_code == 200 and plat.counts()["runs"] == 1
    # a token for A cannot write B's run, and B's token cannot write A's
    other = plat.new_token()
    wid = r.json()["workflowId"]
    assert plat.send("PUT", "/trace/%s/progress" % wid, {"progress": {}}, token=other).status_code in (401, 403)
    # the plain 008 token (no run name) still works for any name, as before
    assert plat.send("POST", "/trace/create", create_body("free-name"), token=other).status_code == 200


@pytest.mark.parametrize("state", ["refused", "error"])
def test_tc020_when_the_agent_refuses_or_fails_the_token_is_revoked(tmp_path, state):
    # TC-020 step 4
    plat, tok, clock = setup(tmp_path)
    _queue_launch(plat, clock)
    job = poll(plat, tok).json()["job"]
    r = plat.client.post("/agent/result/%d" % job["id"], json={"state": state, "result": {"ok": False, "message": "no"}},
                         headers=bearer(tok))
    assert r.status_code == 200
    assert plat.send("POST", "/trace/create", create_body("run-one"), token=job["run_token"]).status_code == 401
    assert tokens_rows(plat)[0][2] is not None


def test_tc020_complete_revokes_the_token_and_the_run_data_stays(tmp_path):
    # TC-020 step 5
    plat, tok, clock = setup(tmp_path)
    _queue_launch(plat, clock)
    job = poll(plat, tok).json()["job"]
    t = job["run_token"]
    sc = load_scenario("nf2510_ok")["requests"]
    # relabel the recording as the run this token is bound to
    from helpers import variant
    reqs = variant("nf2510_ok", "run-one", "sess-run-one", clock())
    wid, resp = plat.replay(reqs, t)
    assert all(x.status_code < 300 for x in resp), [x.status_code for x in resp]
    assert tokens_rows(plat)[0][2] is not None, "revoked by the complete"
    from abf_platform import status
    before = status.get_run(plat.index, wid, clock())
    assert before["status"] == "succeeded"
    assert plat.send("POST", "/trace/create", create_body("run-one"), token=t).status_code == 401
    # follow-up 3 (TC-F3-40): Nextflow may send one more message for the same run after its complete (a second complete of
    # an aborted run); it gets a 2xx and changes nothing. The line used to expect 401. Every other check stays as it was.
    assert plat.send("PUT", "/trace/%s/heartbeat" % wid, {"progress": {}}, token=t).status_code == 200
    assert status.get_run(plat.index, wid, clock()) == before


def test_tc020_fourteen_days_after_issue_the_token_is_refused(tmp_path, monkeypatch):
    # TC-020 step 6 (ABF_PLATFORM_CLOCK_OFFSET moves the clock of the platform's own checks)
    plat, tok, clock = setup(tmp_path)
    _queue_launch(plat, clock)
    t = poll(plat, tok).json()["job"]["run_token"]
    monkeypatch.setenv("ABF_PLATFORM_CLOCK_OFFSET", str(13 * 86400))
    assert plat.send("POST", "/trace/create", create_body("run-one"), token=t).status_code == 200
    monkeypatch.setenv("ABF_PLATFORM_CLOCK_OFFSET", str(14 * 86400 + 60))
    assert plat.send("POST", "/trace/create", create_body("run-one"), token=t).status_code == 401


def test_tc020_a_cancel_does_not_revoke_the_token_because_nextflow_needs_it_to_report_the_end(tmp_path):
    # TC-020 step 7
    from abf_platform import confirm
    plat, tok, clock = setup(tmp_path)
    b, cid, jid = _queue_launch(plat, clock)
    job = poll(plat, tok).json()["job"]
    t = job["run_token"]
    plat.client.post("/agent/result/%d" % jid, json={"state": "done", "result": {
        "ok": True, "slurm_job_id": 4242, "run_name": "run-one", "run_folder": b["run_folder"], "message": "ok"}},
        headers=bearer(tok))
    cancel = {"run_name": "run-one", "slurm_job_id": 4242, "run_folder": b["run_folder"], "agent": "a1", "ce": b["ce"]}
    cc, cj = confirm.confirm_cancel(state_db(plat), "lab-a", cancel, clock=clock)
    cjob = poll(plat, tok).json()["job"]
    assert cjob["kind"] == "cancel_run" and "run_token" not in cjob
    plat.client.post("/agent/result/%d" % cj, json={"state": "done", "result": {"ok": True, "slurm_job_id": 4242,
                                                                               "message": "取消請求已送出"}},
                     headers=bearer(tok))
    assert tokens_rows(plat)[0][2] is None, "still valid after a successful cancel"
    from helpers import variant
    wid, resp = plat.replay(variant("nf2510_fail", "run-one", "sess-run-one", clock()), t)
    assert all(x.status_code < 300 for x in resp)
    assert tokens_rows(plat)[0][2] is not None
    assert plat.send("POST", "/trace/create", create_body("another-run"), token=t).status_code == 401


# ---- the hand-off record is written by results, early and late --------------------------------------------------

def test_the_handover_row_is_written_when_the_job_is_confirmed_and_filled_by_the_answer(tmp_path):
    # TC-012, TC-018 (platform half), FR-009
    plat, tok, clock = setup(tmp_path)
    b, cid, jid = _queue_launch(plat, clock)
    row = sql(plat, "SELECT run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, cancel_requested_at "
                    "FROM launches")
    assert row == [("run-one", None, b["run_folder"], "lab-a", "a1", clock(), None, None)]
    poll(plat, tok)
    answer = {"state": "done", "result": {"ok": True, "slurm_job_id": 4242, "run_name": "run-one", "run_folder": b["run_folder"],
                                          "message": "submitted"}}
    assert plat.client.post("/agent/result/%d" % jid, json=answer, headers=bearer(tok)).json() == {"accepted": True, "late": False}
    row = sql(plat, "SELECT slurm_job_id, submitted_at FROM launches")
    assert row == [(4242, clock())]


def test_tc018_an_answer_after_the_deadline_is_still_applied_to_the_handover_row(tmp_path):
    # TC-018: the head job was submitted, the answer came too late: the number must not be lost
    from abf_platform import jobs
    import asyncio
    plat, tok, clock = setup(tmp_path)
    b, cid, jid = _queue_launch(plat, clock)
    poll(plat, tok)

    async def fake_sleep(s):
        clock.t += s

    out = asyncio.run(jobs.wait_for_result(state_db(plat), jid, clock, sleep=fake_sleep))
    assert out["state"] == "expired"
    late = {"state": "done", "result": {"ok": True, "slurm_job_id": 777, "run_name": "run-one", "run_folder": b["run_folder"]}}
    r = plat.client.post("/agent/result/%d" % jid, json=late, headers=bearer(tok))
    assert r.json() == {"accepted": False, "late": True}
    assert sql(plat, "SELECT slurm_job_id, submitted_at FROM launches")[0][0] == 777
    assert sql(plat, "SELECT submitted_at FROM launches")[0][0] is not None
    assert sql(plat, "SELECT state FROM jobs")[0][0] == "expired"
    assert "777" in sql(plat, "SELECT late_result_json FROM jobs")[0][0]


def test_a_launch_that_failed_leaves_the_row_without_a_submission_and_its_name_can_be_used_again_only_if_it_was_refused(tmp_path):
    # TC-016, TC-017
    from abf_platform import confirm, jobs
    plat, tok, clock = setup(tmp_path)
    b, cid, jid = _queue_launch(plat, clock)
    with pytest.raises(jobs.JobRefused) as e:
        confirm.confirm_launch(state_db(plat), "lab-a", bundle("run-one"), clock=clock)
    assert "run-one" in str(e.value)
    poll(plat, tok)
    plat.client.post("/agent/result/%d" % jid, json={"state": "error", "result": {"ok": False, "message": "sbatch failed"}},
                     headers=bearer(tok))
    assert sql(plat, "SELECT submitted_at FROM launches") == [(None,)]
    with pytest.raises(jobs.JobRefused):
        confirm.confirm_launch(state_db(plat), "lab-a", bundle("run-one"), clock=clock)
    b2, cid2, jid2 = _queue_launch(plat, clock, "run-two")
    poll(plat, tok)
    plat.client.post("/agent/result/%d" % jid2, json={"state": "refused", "result": {"ok": False, "message": "no"}},
                     headers=bearer(tok))
    # refused: nothing was done on the site, so the same name may be tried again
    cid3, jid3 = confirm.confirm_launch(state_db(plat), "lab-a", bundle("run-two"), clock=clock)
    # follow-up 1 (F2): the refused row stays as a fact, and the new try is a second row
    assert jid3 != jid2 and len(sql(plat, "SELECT * FROM launches WHERE run_name = 'run-two'")) == 2


def test_a_confirmed_launch_needs_an_available_environment_an_online_agent_and_a_supported_type(tmp_path):
    # TC-011, TC-063
    from abf_platform import confirm, jobs
    plat, tok, clock = setup(tmp_path)
    con = sqlite3.connect(str(state_db(plat)))
    con.execute("UPDATE compute_envs SET status = 'disabled'")
    con.commit()
    with pytest.raises(jobs.JobRefused):
        confirm.confirm_launch(state_db(plat), "lab-a", bundle(), clock=clock)
    con.execute("UPDATE compute_envs SET status = 'available'")
    con.commit()
    clock.t += 1000
    with pytest.raises(jobs.JobRefused) as e:
        confirm.confirm_launch(state_db(plat), "lab-a", bundle(), clock=clock)
    assert re.search(r"offline|離線", str(e.value))
    assert sql(plat, "SELECT * FROM launches") == [] and sql(plat, "SELECT * FROM confirmations") == []
    con.close()


def test_the_deadlines_are_300_seconds_for_a_launch_and_can_be_shortened(tmp_path, monkeypatch):
    # TC-018
    from abf_platform import jobs
    assert jobs.DEADLINE_SECONDS["launch_nextflow"] == 300
    assert jobs.deadline_seconds("launch_nextflow") == 300
    monkeypatch.setenv("ABF_PLATFORM_DEADLINE_LAUNCH", "7")
    assert jobs.deadline_seconds("launch_nextflow") == 7
    assert set(jobs.KINDS) == {"preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records", "read_task_log"}   # run-diag-tools: plus read_task_log


# ---- TC-036: `abf-platform launches` -----------------------------------------------------------------------------

STATE_WORDS = re.compile(r"執行中|成功|失敗|失聯|已取消|running|succeeded|failed|lost|cancelled|canceled", re.I)


def test_tc036_launches_states_only_facts_and_writes_nothing(tmp_path, monkeypatch):
    # TC-036
    from abf_platform import confirm, jobs
    from helpers import variant
    from station_harness import Inproc
    plat, tok, clock = setup(tmp_path)
    ip = Inproc(tmp_path / "ip", monkeypatch)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(plat.index))
    ip.index, ip.tokens, ip.state_db = plat.index, plat.tokens, state_db(plat)
    b1, c1, j1 = _queue_launch(plat, clock, "run-one")
    poll(plat, tok)
    plat.client.post("/agent/result/%d" % j1, json={"state": "done", "result": {
        "ok": True, "slurm_job_id": 4242, "run_name": "run-one", "run_folder": b1["run_folder"]}}, headers=bearer(tok))
    b2, c2, j2 = _queue_launch(plat, clock, "run-bad")
    poll(plat, tok)
    plat.client.post("/agent/result/%d" % j2, json={"state": "error", "result": {"ok": False, "message": "boom"}},
                     headers=bearer(tok))
    digest = all_files_digest(plat.index, plat.tokens, state_db(plat))
    rc, out = ip.run("launches")
    assert rc == 0
    assert all_files_digest(plat.index, plat.tokens, state_db(plat)) == digest, "the command writes nothing"
    blocks = {}
    for ln in out.splitlines():
        if ln.strip() and not ln.startswith(" "):
            cur = ln.split()[0]
            blocks[cur] = ln + "\n"
        elif ln.strip() and cur in blocks:
            blocks[cur] += ln + "\n"
    assert set(blocks) >= {"run-one", "run-bad"}, out
    assert "4242" in blocks["run-one"] and b1["run_folder"] in blocks["run-one"]
    assert "已送出，尚未收到 Nextflow 事件" in blocks["run-one"]
    assert "已送出" not in blocks["run-bad"], "a launch that was not submitted is not written as submitted"
    assert not STATE_WORDS.search(out), STATE_WORDS.search(out).group(0)
    # a cancel is listed as a fact, in words that are not a state
    cancel = {"run_name": "run-one", "slurm_job_id": 4242, "run_folder": b1["run_folder"], "agent": "a1", "ce": b1["ce"]}
    cc, cj = confirm.confirm_cancel(state_db(plat), "lab-a", cancel, clock=clock)
    poll(plat, tok)
    plat.client.post("/agent/result/%d" % cj, json={"state": "done", "result": {"ok": True, "slurm_job_id": 4242}},
                     headers=bearer(tok))
    rc, out = ip.run("launches")
    assert "取消請求已於" in out and "送出" in out
    assert not STATE_WORDS.search(out)


def test_tc036_after_the_first_event_the_sentence_gives_way_to_get_run_and_returns_when_the_index_is_gone(tmp_path, monkeypatch):
    # TC-036
    from helpers import variant
    from station_harness import Inproc
    from abf_platform import store
    plat, tok, clock = setup(tmp_path)
    ip = Inproc(tmp_path / "ip", monkeypatch)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(plat.index))
    ip.index, ip.tokens, ip.state_db = plat.index, plat.tokens, state_db(plat)
    b, cid, jid = _queue_launch(plat, clock)
    job = poll(plat, tok).json()["job"]
    plat.client.post("/agent/result/%d" % jid, json={"state": "done", "result": {
        "ok": True, "slurm_job_id": 4242, "run_name": "run-one", "run_folder": b["run_folder"]}}, headers=bearer(tok))
    rc, out = ip.run("launches")
    assert "已送出，尚未收到 Nextflow 事件" in out
    r = plat.send("POST", "/trace/create", create_body("run-one"), token=job["run_token"])
    assert r.status_code == 200
    rc, out = ip.run("launches")
    assert "尚未收到" not in out and "get_run" in out and r.json()["workflowId"] in out
    assert not STATE_WORDS.search(out)
    store.drop_index_files(plat.index)
    rc, out = ip.run("launches")
    assert "已送出，尚未收到 Nextflow 事件" in out


def test_tc067_get_run_does_not_change_when_the_handover_rows_do(tmp_path):
    # TC-067, TC-045
    from helpers import variant
    from abf_platform import status
    plat, tok, clock = setup(tmp_path)
    b, cid, jid = _queue_launch(plat, clock)
    job = poll(plat, tok).json()["job"]
    wid, resp = plat.replay(variant("nf2510_fail", "run-one", "sess-run-one", clock()), job["run_token"])
    before = json.dumps(status.get_run(plat.index, wid, clock()), sort_keys=True)
    list_before = json.dumps(status.list_runs(plat.index, clock()), sort_keys=True)
    con = sqlite3.connect(str(state_db(plat)))
    con.execute("UPDATE launches SET slurm_job_id = 999999, submitted_at = 12345, cancel_requested_at = 67890, "
                "run_folder = '/some/where/else'")
    con.commit()
    con.close()
    assert json.dumps(status.get_run(plat.index, wid, clock()), sort_keys=True) == before
    assert json.dumps(status.list_runs(plat.index, clock()), sort_keys=True) == list_before


def test_tc067_the_modules_that_report_a_run_never_open_the_tables_of_the_handover():
    # TC-067, TC-055
    root = PLATFORM_DIR / "abf_platform"
    for name in ("status.py", "rebuild.py", "mcp_server.py", "receiver.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert not re.search(r"launches|confirmations|confirm\b", text), name
    assert not re.search(r"platform_path|default_platform_path|platform\.db", (root / "rebuild.py").read_text(encoding="utf-8")), \
        "rebuild never opens platform.db"
    assert not re.search(r"abf_launch|\.launches", (root / "status.py").read_text(encoding="utf-8"))


def test_tc045_the_platform_writes_no_run_state_called_cancelled_anywhere():
    # TC-045: the word is not a status; `launches` lists a request, Nextflow reports the end
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"['\"](cancelled|canceled|已取消)['\"]", text), f.name


def test_tc061_the_command_line_has_resume_and_relaunch_and_no_retry_and_no_confirm_command():
    # TC-061, TC-062. 009e: was "no resume, no retry, no relaunch and no confirm command". There are now exactly the two commands resume and
    # relaunch, which take the name of a run (and --user) and no flag that says yes; retry, confirm and the flags are still not there.
    from abf_platform import cli
    seen = set()

    def walk(parser, path=()):
        for act in parser._actions:
            for opt in getattr(act, "option_strings", []):
                # 116b: only `runs assign --force` (changes the owner of an old run) is let through; it is not a way to force a launch
                if path == ("runs", "assign") and opt == "--force":
                    continue
                seen.add(opt.lstrip("-"))
            ch = getattr(act, "choices", None)
            if isinstance(ch, dict):
                for name, sub in ch.items():
                    seen.add(name)
                    walk(sub, path + (name,))

    walk(cli.build_parser())
    assert {"launch", "cancel", "resume", "relaunch", "launches", "fetch-records"} <= seen
    assert not (seen & {"retry", "confirm", "yes", "y", "force", "assume-yes", "no-confirm"}), seen


def test_security_f1_every_trace_event_of_a_bound_token_is_for_the_tokens_run_only(tmp_path):
    # begin, progress, heartbeat and complete are bound to the run name of the token, as create is
    plat, tok, clock = setup(tmp_path)
    _queue_launch(plat, clock)
    t = poll(plat, tok).json()["job"]["run_token"]
    r = plat.send("POST", "/trace/create", create_body("run-one"), token=t)
    wid = r.json()["workflowId"]
    # the run row now says another name (damaged index, or a run made another way): the token is not for it
    con = sqlite3.connect(str(plat.index))
    con.execute("UPDATE runs SET run_name = 'some-other-run' WHERE id = ?", (wid,))
    con.commit()
    con.close()
    before = db_bytes(plat.index)
    wf = {"workflow": {"success": True, "exitStatus": 0, "start": "2026-10-11T10:00:00Z"}, "progress": {}}
    for method, path, body in (("PUT", "/trace/%s/begin" % wid, wf), ("PUT", "/trace/%s/progress" % wid, {"progress": {}}),
                               ("PUT", "/trace/%s/heartbeat" % wid, {"progress": {}}), ("PUT", "/trace/%s/complete" % wid, wf)):
        assert plat.send(method, path, body, token=t).status_code == 403, path
    assert db_bytes(plat.index) == before
    assert tokens_rows(plat)[0][2] is None, "a refused complete does not revoke the token"
