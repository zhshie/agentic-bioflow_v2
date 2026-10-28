# Nothing existing: tests of the owner-binding follow-up (#116): who may be issued or use an agent token, and how an environment claims an agent nobody owns; the rules are ours.
"""owner-binding: an agent token names its user, an old token without one cannot serve an owned agent, `ce --owner` claims an
agent nobody owns, and `assign_orphans` hands such an agent to the one owner of its environments.
Test cases are named in the comments (TC-001 ...)."""
import asyncio
import hashlib
import sqlite3
import time

import pytest
from starlette.testclient import TestClient

from helpers import all_files_digest
from human_harness import World
from owner_harness import Duo, sql_exec, sql_rows
from station_harness import Inproc

MESSAGE = "This agent belongs to another user"
ASK = "rejected: say whose agent this is with --user NAME (請用 --user 名字 指定這個代理是誰的)"


@pytest.fixture
def w(tmp_path, monkeypatch):
    monkeypatch.setenv("ABF_AGENT_POLL_SECONDS", "0")
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def store():
    from abf_platform import store as s
    return s


def _client(w):
    from abf_platform import receiver
    return TestClient(receiver.create_app(w.ip.index, w.ip.tokens))


def _head(token):
    return {"Authorization": "Bearer " + token}


def _hello(w, token, name):
    return _client(w).post("/agent/hello", json={"name": name, "version": "0.1.0"}, headers=_head(token))


def _poll(w, token, name):
    return _client(w).post("/agent/poll", json={"name": name}, headers=_head(token))


def _result(w, token, name):
    return _client(w).post("/agent/result/1", json={"state": "done", "result": {}}, headers=_head(token))


def _owner(w, name):
    rows = sql_rows(w.ip.state_db, "SELECT owner_user_id FROM agents WHERE name = ?", (name,))
    return rows[0][0] if rows else "no row"


def _agent_tokens(w, name="ag"):
    return sql_rows(w.ip.tokens, "SELECT * FROM tokens WHERE kind = 'agent' AND agent_name = ?", (name,))


def _legacy(w, name="ag"):
    """An agent token without a user (an old one), and the agent says hello with it: the agent exists and nobody owns it."""
    t = store().create_token(w.ip.tokens, kind="agent", agent_name=name)
    assert _hello(w, t, name).status_code == 200
    return t


def _ce(w, name, agent, owner=None, verb="create"):
    flags = ["--agent=%s" % agent]
    if owner:
        flags.append("--owner=%s" % owner)
    if verb == "create":
        return w.ip.run("ce", "create", "--name=%s" % name, "--platform=slurm-platform", "--work-dir=/data/x", "--launch-dir=/data/l",
                        "--head-queue=normal", *flags)
    return w.ip.run("ce", "update", name, *flags)


def _jobs(d):
    return len(sql_rows(d.state, "SELECT * FROM jobs"))


# ---- US1: the token names its user ---------------------------------------------------------------------------------------

def test_agent_token_new_without_user_is_refused_once_a_user_exists(w):
    # TC-001, TC-002, TC-003
    w.user("alice")
    rc, out = w.ip.run("agent-token", "new", "ag")
    assert rc == 1 and "--user" in out and ASK in out
    assert "abf_" not in out
    assert not _agent_tokens(w)


def test_agent_token_new_without_user_is_allowed_when_there_is_no_user(w):
    # TC-004
    rc, out = w.ip.run("agent-token", "new", "ag")
    assert rc == 0 and "abf_" in out and len(_agent_tokens(w)) == 1


def test_agent_token_new_with_a_user_works(w):
    # TC-005
    a = w.user("alice")
    rc, out = w.ip.run("agent-token", "new", "ag", "--user", "alice")
    assert rc == 0 and "abf_" in out
    rows = _agent_tokens(w)
    assert len(rows) == 1 and rows[0]["user_id"] == a.user_id


def test_agent_token_for_an_agent_owned_by_another_user_is_refused_at_issue(w):
    # TC-006, TC-007, TC-008
    a, b = w.user("alice"), w.user("bob")
    ta = store().create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=a.user_id)
    assert _hello(w, ta, "ag").status_code == 200
    before = len(_agent_tokens(w))
    rc, out = w.ip.run("agent-token", "new", "ag", "--user", "bob")
    assert rc != 0 and len(_agent_tokens(w)) == before
    assert "alice" not in out and "another user" in out


def test_a_token_with_no_user_cannot_serve_an_owned_agent(w):
    # TC-009, TC-010, TC-011, TC-012, TC-013, TC-085
    a, b = w.user("alice"), w.user("bob")
    ta = store().create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=a.user_id)
    tb = store().create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=b.user_id)
    assert _hello(w, ta, "ag").status_code == 200
    legacy = store().create_token(w.ip.tokens, kind="agent", agent_name="ag")
    other = _hello(w, tb, "ag")
    assert other.status_code == 403 and other.json() == {"message": MESSAGE}
    for call in (_hello, _poll, _result):
        r = call(w, legacy, "ag")
        assert r.status_code == 403, call
        assert set(r.json()) == set(other.json()) == {"message"} and r.json()["message"] == MESSAGE
    assert _owner(w, "ag") == a.user_id


def test_a_token_with_no_user_still_serves_an_agent_nobody_owns(w):
    # TC-014, TC-015, TC-016
    w.user("alice")
    t = _legacy(w)
    assert _owner(w, "ag") is None
    assert _poll(w, t, "ag").status_code == 200
    assert _result(w, t, "ag").json().get("message") != MESSAGE
    assert _owner(w, "ag") is None


def test_a_token_of_the_owner_still_serves_the_agent(w):
    # TC-019, TC-020
    a = w.user("alice")
    _legacy(w)
    ta = store().create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=a.user_id)
    assert _hello(w, ta, "ag").status_code == 200 and _owner(w, "ag") == a.user_id
    assert _hello(w, ta, "ag").status_code == 200


# ---- US2: an environment claims the agent nobody owns ---------------------------------------------------------------------

def test_ce_create_with_an_owner_claims_an_agent_nobody_owns(d):
    # TC-021, TC-023, TC-024, TC-025, TC-026
    from abf_platform import jobs
    w = d.w
    _legacy(w)
    rc, out = _ce(w, "c1", "ag", "alice")
    assert rc == 0, out
    sql_exec(d.state, "UPDATE compute_envs SET status = 'available', checked_ok = 1 WHERE name = 'c1'")
    assert _owner(w, "ag") == d.a.user_id
    assert "ag" in [x["name"] for x in d.call("list_agents", caller=d.a)["agents"]]
    assert "ag" not in [x["name"] for x in d.call("list_agents", caller=d.b)["agents"]]
    assert jobs.enqueue_listing(d.state, "c1", "/data/x", time.time, caller_user_id=d.a.user_id)
    with pytest.raises(jobs.JobRefused, match="找不到"):
        jobs.enqueue_listing(d.state, "c1", "/data/x", time.time, caller_user_id=d.b.user_id)


def test_ce_update_owner_claims_an_agent_nobody_owns(d):
    # TC-022
    w = d.w
    _legacy(w)
    rc, out = _ce(w, "c1", "agent-t", "alice")
    assert rc == 0, out
    rc, out = _ce(w, "c1", "ag", "alice", verb="update")
    assert rc == 0, out
    assert _owner(w, "ag") == d.a.user_id


def test_ce_create_does_not_claim_an_agent_that_has_an_owner(d):
    # TC-027, TC-028
    rc, out = _ce(d.w, "x1", "agent-t", "bob")
    assert rc != 0 and "belongs to somebody else" in out
    assert _owner(d.w, "agent-t") == d.a.user_id
    assert not sql_rows(d.state, "SELECT * FROM compute_envs WHERE name = 'x1'")


def test_ce_create_for_an_agent_that_never_said_hello_makes_no_agent_row(d):
    # TC-029, TC-030
    rc, out = _ce(d.w, "c1", "ghost", "alice")
    assert rc == 0, out
    assert _owner(d.w, "ghost") == "no row"
    ta = store().create_token(d.w.ip.tokens, kind="agent", agent_name="ghost", user_id=d.a.user_id)
    assert _hello(d.w, ta, "ghost").status_code == 200 and _owner(d.w, "ghost") == d.a.user_id


def test_ce_create_with_no_owner_does_not_claim(tmp_path, monkeypatch):
    # TC-031, TC-032
    ip = Inproc(tmp_path / "ip", monkeypatch)
    from abf_platform import agents
    agents.register(ip.state_db, "ag", "0.1.0", time.time)
    rc, out = ip.create_slurm("c1", agent="ag")
    assert rc == 0, out
    assert sql_rows(ip.state_db, "SELECT owner_user_id FROM agents WHERE name = 'ag'")[0][0] is None
    uid = store().create_user(ip.tokens, "alice", "lab-x")
    store().assign_orphans(ip.state_db, ip.tokens)
    assert sql_rows(ip.state_db, "SELECT owner_user_id FROM compute_envs WHERE name = 'c1'")[0][0] == uid


def test_claiming_is_one_transaction(d, monkeypatch):
    # TC-033
    from abf_platform import compute_envs
    _legacy(d.w)
    real = store().connect_state

    class Proxy:
        def __init__(self, c):
            self.c = c

        def execute(self, sql, *a):
            if str(sql).lstrip().startswith("INSERT INTO compute_envs"):
                raise sqlite3.OperationalError("boom")
            return self.c.execute(sql, *a)

        def __enter__(self):
            self.c.__enter__()
            return self

        def __exit__(self, *a):
            return self.c.__exit__(*a)

        def __getattr__(self, n):
            return getattr(self.c, n)

    with monkeypatch.context() as m:
        m.setattr(store(), "connect_state", lambda *a, **k: Proxy(real(*a, **k)))
        fields = {"name": "c1", "platform": "slurm-platform", "agent": "ag", "owner_user_id": d.a.user_id,
                  "config": {"workDir": "/data/x", "launchDir": "/data/l", "headQueue": "normal"}}
        with pytest.raises(sqlite3.OperationalError):
            compute_envs.create(d.state, fields)
    assert _owner(d.w, "ag") is None
    assert not sql_rows(d.state, "SELECT * FROM compute_envs WHERE name = 'c1'")


def _env_row(d, name, agent, owner):
    sql_exec(d.state, "INSERT INTO compute_envs (name, platform, agent, status, message, is_primary, config_json, created_at, updated_at, owner_user_id) "
                      "VALUES (?, 'slurm-platform', ?, 'available', '', 0, '{}', 1, 1, ?)", (name, agent, owner))


def _unowned_agent(d, name="ag"):
    sql_exec(d.state, "INSERT INTO agents (name, first_seen_at, last_seen_at) VALUES (?, 1, 1)", (name,))


def test_assign_orphans_gives_an_unowned_agent_to_the_owner_of_its_environments(d):
    # TC-034, TC-035, TC-047, TC-048
    _unowned_agent(d)
    _env_row(d, "c1", "ag", d.a.user_id)
    _env_row(d, "c2", "ag", d.a.user_id)
    store().assign_orphans(d.state, d.w.ip.tokens)
    assert _owner(d.w, "ag") == d.a.user_id
    digest = all_files_digest(d.state)
    store().assign_orphans(d.state, d.w.ip.tokens)
    assert _owner(d.w, "ag") == d.a.user_id and all_files_digest(d.state) == digest
    assert "ag" in [x["name"] for x in d.call("list_agents", caller=d.a)["agents"]]
    assert "ag" not in [x["name"] for x in d.call("list_agents", caller=d.b)["agents"]]


def test_assign_orphans_leaves_an_agent_shared_by_two_owners_alone(d):
    # TC-036
    _unowned_agent(d)
    _env_row(d, "c1", "ag", d.a.user_id)
    _env_row(d, "c2", "ag", d.b.user_id)
    store().assign_orphans(d.state, d.w.ip.tokens)
    assert _owner(d.w, "ag") is None


def test_assign_orphans_leaves_an_agent_with_no_environment_alone(d):
    # TC-037
    _unowned_agent(d)
    store().assign_orphans(d.state, d.w.ip.tokens)
    assert _owner(d.w, "ag") is None


def test_assign_orphans_never_gives_an_agent_to_the_owner_of_an_ownerless_environment(d):
    # TC-038, TC-041
    _unowned_agent(d)
    _env_row(d, "c1", "ag", None)
    store().assign_orphans(d.state, d.w.ip.tokens)
    assert _owner(d.w, "ag") is None
    assert sql_rows(d.state, "SELECT owner_user_id FROM compute_envs WHERE name = 'c1'")[0][0] is None


def test_rebuild_still_never_opens_the_platform_or_the_tokens(tmp_path, monkeypatch):
    # TC-039
    ip = Inproc(tmp_path / "ip", monkeypatch)
    from abf_platform import agents
    agents.register(ip.state_db, "ag", "0.1.0", time.time)
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


def test_b_cannot_see_or_use_the_claimed_agent_or_environment(d):
    # TC-042, TC-043, TC-044, TC-045, TC-046, TC-086
    from abf_platform import actions, jobs
    w = d.w
    _legacy(w)
    rc, out = _ce(w, "c1", "ag", "alice")
    assert rc == 0, out
    sql_exec(d.state, "UPDATE compute_envs SET status = 'available', checked_ok = 1 WHERE name = 'c1'")
    d.add_run("r-a", d.a.user_id)
    assert "c1" not in [c["name"] for c in d.call("list_compute_envs", caller=d.b)["compute_envs"]]
    other = d.call("get_compute_env", {"name": "c1"}, caller=d.b)
    missing = d.call("get_compute_env", {"name": "nonesuch"}, caller=d.b)
    assert other["found"] is False and other["message"].replace("c1", "<n>") == missing["message"].replace("nonesuch", "<n>")
    before = _jobs(d)
    out = asyncio.run(actions.list_site_files(d.state, "c1", "/data/x", caller=d.b))
    assert out["ok"] is False and _jobs(d) == before
    got = actions.run_outputs(d.w.ip.index, d.state, "id-r-a", caller=d.b)
    assert got["found"] is False
    with pytest.raises(jobs.JobRefused, match="找不到"):
        jobs.enqueue_listing(d.state, "c1", "/data/x", time.time, caller_user_id=d.b.user_id)
    assert _jobs(d) == before
    # no yes, no job (TC-086)
    d.launch(d.a, ce_name="c1")
    assert _jobs(d) == before


def test_refusals_say_what_to_do_and_leak_no_token_or_other_user(w):
    # TC-082, TC-083, TC-084
    a, b = w.user("alice"), w.user("bob")
    ta = store().create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=a.user_id)
    assert _hello(w, ta, "ag").status_code == 200
    rc1, out1 = w.ip.run("agent-token", "new", "other")
    rc2, out2 = w.ip.run("agent-token", "new", "ag", "--user", "bob")
    assert rc1 != 0 and rc2 != 0
    assert "--user" in out1 and "--user" in out2
    for out in (out1, out2):
        assert "abf_" not in out and ta not in out and "alice" not in out
