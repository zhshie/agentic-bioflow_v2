# Nothing existing: tests of the action layer (spec 009b) - who may import or call it, what it refuses, what it must not change; the rules and the AST scans are ours.
"""The action layer, platform/abf_platform/actions/ (009b): one function per action, behaviour unchanged.

Test cases are named in the comments (TC-A01 ...), see specs/009b-action-layer/test-case.md.
"""
import ast
import asyncio
import inspect
import json
import re
import sqlite3
import time
from pathlib import Path

import pytest

from helpers import Clock, Platform, PLATFORM_DIR, REPO_ROOT
from launch_harness import LaunchData
from station_harness import Inproc
from test_launch_platform import bundle, setup, sql
from test_launch_cli import hand_over
from test_station_platform import state_db

PKG = PLATFORM_DIR / "abf_platform"
SCAN_DIRS = [PLATFORM_DIR / "abf_platform", PLATFORM_DIR / "abf_station", PLATFORM_DIR / "abf_launch"]
REFUSED = "no human confirmation channel"
READ_NAMES = ["list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files"]
ROUTES_V3 = [('/agent/hello', ('POST',)), ('/agent/poll', ('POST',)), ('/agent/result/{jid}', ('POST',)),
             ('/trace/create', ('POST',)), ('/trace/{rid}/begin', ('PUT',)), ('/trace/{rid}/complete', ('PUT',)),
             ('/trace/{rid}/heartbeat', ('PUT',)), ('/trace/{rid}/progress', ('PUT',)), ('/user-info', ('GET', 'HEAD'))]

# The server of the v3 starting point (commit bc9a93b): tool names, descriptions, annotations, input schemas, instructions.
BASELINE = '{"instructions": "Read-only view of Nextflow runs, compute environments and agents. list_runs gives the newest runs first; get_run gives one run with its processes and failed tasks. list_compute_envs and get_compute_env show the compute environments; list_agents shows whether each agent is online; list_site_files lists one folder on the site through an agent (names, sizes and modification times, which go to the model you chose).", "tools": [{"annotations": {"destructive_hint": false, "idempotent_hint": true, "open_world_hint": false, "read_only_hint": true}, "description": "One compute environment by its name, with its config.", "name": "get_compute_env", "schema": {"properties": {"name": {"title": "Name", "type": "string"}}, "required": ["name"], "title": "get_compute_envArguments", "type": "object"}}, {"annotations": {"destructive_hint": false, "idempotent_hint": true, "open_world_hint": false, "read_only_hint": true}, "description": "One run by its id: status, times, task numbers, task numbers per process, and the failed tasks with their exit code and error message; a failed run also has failure_reason, Nextflow\'s own words for why it failed, when it gave any.", "name": "get_run", "schema": {"properties": {"run_id": {"title": "Run Id", "type": "string"}}, "required": ["run_id"], "title": "get_runArguments", "type": "object"}}, {"annotations": {"destructive_hint": false, "idempotent_hint": true, "open_world_hint": false, "read_only_hint": true}, "description": "List the agents that have connected: name, version, online or offline, and the time of their last contact. Offline means no contact for three heartbeats.", "name": "list_agents", "schema": {"properties": {}, "title": "list_agentsArguments", "type": "object"}}, {"annotations": {"destructive_hint": false, "idempotent_hint": true, "open_world_hint": false, "read_only_hint": true}, "description": "List the compute environments: name, type, credential name, status, message, primary, dates and config. A credential itself is never stored, only its name.", "name": "list_compute_envs", "schema": {"properties": {}, "title": "list_compute_envsArguments", "type": "object"}}, {"annotations": {"destructive_hint": false, "idempotent_hint": true, "open_world_hint": false, "read_only_hint": true}, "description": "List the Nextflow runs the platform knows, newest first, each with its name, status (running, succeeded, failed or lost), start time and task numbers.", "name": "list_runs", "schema": {"properties": {}, "title": "list_runsArguments", "type": "object"}}, {"annotations": {"destructive_hint": false, "idempotent_hint": true, "open_world_hint": false, "read_only_hint": true}, "description": "List one folder on the site through the agent of a compute environment: file names, sizes and modification times (these go to the model you chose). The folder must be inside the places the agent may read; at most 500 entries are shown and a cut is said so. Nothing is written or run.", "name": "list_site_files", "schema": {"properties": {"compute_env": {"title": "Compute Env", "type": "string"}, "path": {"title": "Path", "type": "string"}}, "required": ["compute_env", "path"], "title": "list_site_filesArguments", "type": "object"}}]}'


def actions():
    from abf_platform import actions as a
    return a


# ---- the scans (AST), used on the real files and on made-up ones (TC-C05) ----------------------------------------------

def _package_of(rel):
    return list(Path(rel).with_suffix("").parts[:-1])


def imported_names(source, rel):
    """Dotted names a file imports, relative imports resolved against its place (rel is like abf_platform/mcp_server.py).
    `from X import a` gives X and X.a; a call of importlib or __import__ with a string gives that string."""
    tree = ast.parse(source)
    pkg = _package_of(rel)
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            base = pkg[:len(pkg) - (node.level - 1)] if node.level else []
            mod = ".".join(base + ([node.module] if node.module else []))
            out.add(mod)
            for a in node.names:
                out.add(mod + "." + a.name)
        elif isinstance(node, ast.Call):
            f = node.func
            fname = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if fname in ("import_module", "__import__") and node.args and isinstance(node.args[0], ast.Constant):
                out.add(str(node.args[0].value))
    return out


def platform_submodules(source, rel):
    return {n.split(".")[1] for n in imported_names(source, rel) if n.startswith("abf_platform.")}


def imports_confirm(source, rel):
    return any(n == "abf_platform.confirm" or n.startswith("abf_platform.confirm.") for n in imported_names(source, rel))


def action_refs(source, rel):
    """Where a file reaches launch, cancel or TERMINAL of the action layer: from-imports, attribute access on the module
    or on an alias of it, and the bare name TERMINAL."""
    tree = ast.parse(source)
    pkg = _package_of(rel)
    aliases = set()
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = pkg[:len(pkg) - (node.level - 1)] if node.level else []
            mod = ".".join(base + ([node.module] if node.module else []))
            for a in node.names:
                if mod == "abf_platform" and a.name == "actions":
                    aliases.add(a.asname or "actions")
                if mod.startswith("abf_platform.actions") and a.name in ("launch", "cancel", "TERMINAL"):
                    hits.append("from-import " + a.name)
                if mod.startswith("abf_platform.actions") and a.name == "*":
                    hits.append("star import")
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "abf_platform.actions":
                    aliases.add(a.asname or "abf_platform.actions")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("launch", "cancel", "TERMINAL"):
            root = node.value
            dotted = []
            while isinstance(root, ast.Attribute):
                dotted.append(root.attr)
                root = root.value
            if isinstance(root, ast.Name):
                full = ".".join([root.id] + list(reversed(dotted)))
                if full in aliases or node.attr == "TERMINAL":
                    hits.append("attribute " + node.attr)
        elif isinstance(node, ast.Name) and node.id == "TERMINAL":
            hits.append("name TERMINAL")
    return hits


def source_files():
    out = []
    for d in SCAN_DIRS:
        for p in sorted(d.rglob("*.py")):
            out.append((p, p.relative_to(PLATFORM_DIR).as_posix()))
    return out


# ---- US1 ---------------------------------------------------------------------------------------------------------------

def test_tca01_one_function_per_read_action_and_the_first_argument_is_a_path():
    a = actions()
    for name in READ_NAMES:
        fn = getattr(a, name)
        assert callable(fn), name
        params = list(inspect.signature(fn).parameters.values())
        assert params and params[0].kind in (params[0].POSITIONAL_ONLY, params[0].POSITIONAL_OR_KEYWORD), name
        assert re.search(r"path", params[0].name), (name, params[0].name)
    assert inspect.iscoroutinefunction(a.list_site_files)


def _server(index_path, platform_path=None):
    from abf_platform.mcp_server import build_server
    return build_server(index_path, platform_path) if platform_path else build_server(index_path)


def _tools(server):
    return asyncio.run(server.list_tools())


def test_tca02_every_tool_has_a_same_named_action_and_there_are_exactly_the_six_read_ones(tmp_path):
    a = actions()
    names = {t.name for t in _tools(_server(str(tmp_path / "index.db")))}
    assert names == set(READ_NAMES)
    for n in names:
        assert callable(getattr(a, n, None)), n


def test_tca03_default_platform_path_and_explicit_platform_path(tmp_path):
    from abf_platform import store
    a = actions()
    idx = tmp_path / "index.db"
    assert a.platform_path_for(idx) == store.default_platform_path(idx)
    assert a.platform_path_for(idx, tmp_path / "other.db") == tmp_path / "other.db"
    # an environment created next to the index is found by a server that was given only the index
    plat = Platform(tmp_path / "plat", clock=Clock())
    from test_station_platform import make_ce
    make_ce(plat)
    out = asyncio.run(_server(str(plat.index)).call_tool("list_compute_envs", {}))
    assert "lab-a" in str(out)


def test_tca05_an_unknown_run_is_a_plain_answer(tmp_path):
    a = actions()
    plat = Platform(tmp_path / "plat", clock=Clock())
    got = a.get_run(plat.index, "deadbeefdeadbeef")
    assert got == {"found": False, "id": "deadbeefdeadbeef", "message": "Run not found: deadbeefdeadbeef (找不到這個 run)"}
    via_mcp = asyncio.run(_server(str(plat.index)).call_tool("get_run", {"run_id": "deadbeefdeadbeef"}))
    assert "Run not found: deadbeefdeadbeef (找不到這個 run)" in str(via_mcp)


def test_tca06_unknown_compute_env_and_the_list(tmp_path):
    a = actions()
    plat = Platform(tmp_path / "plat", clock=Clock())
    from test_station_platform import make_ce
    make_ce(plat)
    assert a.get_compute_env(state_db(plat), "nope") == {
        "found": False, "name": "nope", "message": "Compute environment not found: nope (找不到這個算力環境)"}
    listed = a.list_compute_envs(state_db(plat))
    assert list(listed) == ["compute_envs"] and [e["name"] for e in listed["compute_envs"]] == ["lab-a"]


def test_tca07_agents_online_or_offline_with_the_clock_taken_inside_actions(tmp_path):
    from abf_platform import agents
    a = actions()
    plat = Platform(tmp_path / "plat", clock=Clock())
    agents.register(state_db(plat), "old", "0.1.0", lambda: time.time() - 100000)
    agents.register(state_db(plat), "fresh", "0.1.0", time.time)
    got = a.list_agents(state_db(plat))
    assert list(got) == ["agents"]
    assert {x["name"]: x["status"] for x in got["agents"]} == {"old": "offline", "fresh": "online"}


def test_tca09_a_listing_that_cannot_be_queued_is_an_answer_not_an_exception(tmp_path):
    a = actions()
    plat, _, _ = setup(tmp_path)
    before = sql(plat, "SELECT COUNT(*) FROM jobs")
    got = asyncio.run(a.list_site_files(state_db(plat), "no-such-env", "/data/w1"))
    assert got["ok"] is False and got["compute_env"] == "no-such-env" and got["path"] == "/data/w1" and got["message"]
    assert sql(plat, "SELECT COUNT(*) FROM jobs") == before


def test_tca10_the_server_is_byte_for_byte_the_one_of_the_starting_point(tmp_path):
    base = json.loads(BASELINE)
    server = _server(str(tmp_path / "index.db"))
    # 009g: the instructions are now the generated routing table (spec 009g, TC-602); the tools half is unchanged.
    from abf_platform import guidance
    assert server.instructions == guidance.routing_instructions()
    for word in ("setup", "launch", "runs", "downstream", "finish", "read-only", "terminal"):
        assert word in server.instructions
    tools = sorted(_tools(server), key=lambda t: t.name)
    got = [{"name": t.name, "description": t.description,
            "annotations": t.annotations.model_dump(exclude_none=True) if t.annotations else None,
            "schema": t.input_schema} for t in tools]
    assert json.loads(json.dumps(got)) == base["tools"]


def _tool_functions():
    tree = ast.parse((PKG / "mcp_server.py").read_text(encoding="utf-8"))
    build = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_server"][0]
    return [n for n in ast.walk(build) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not build]


def test_tca13_each_tool_body_is_one_call_into_actions():
    fns = _tool_functions()
    assert sorted(f.name for f in fns) == sorted(READ_NAMES)
    for f in fns:
        body = list(f.body)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]
        assert len(body) == 1 and isinstance(body[0], ast.Return), f.name
        call = body[0].value
        if isinstance(f, ast.AsyncFunctionDef):
            assert isinstance(call, ast.Await), f.name
            call = call.value
        assert isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute), f.name
        assert isinstance(call.func.value, ast.Name) and call.func.value.id == "actions" and call.func.attr == f.name, f.name
        for node in ast.walk(f):
            assert not isinstance(node, (ast.If, ast.Try, ast.For, ast.While, ast.AsyncFor)), f.name


# ---- US2: the write actions and the one channel ---------------------------------------------------------------------------

def _counts(plat):
    return tuple(sql(plat, "SELECT COUNT(*) FROM " + t)[0][0] for t in ("jobs", "confirmations", "launches"))


def _cancel_bundle(plat, run="run-one"):
    b = bundle(run)
    con = sqlite3.connect(str(state_db(plat)))
    con.execute("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at) "
                "VALUES (?, 4242, ?, 'lab-a', 'a1', ?, ?)", (run, b["run_folder"], time.time(), time.time()))
    con.commit()
    con.close()
    return {"version": 1, "run_name": run, "slurm_job_id": 4242, "run_folder": b["run_folder"], "agent": "a1", "ce": b["ce"]}


def test_tcb01_a_terminal_launch_queues_exactly_one_job_and_one_confirmation(tmp_path):
    from abf_platform import common
    a = actions()
    plat, _, clock = setup(tmp_path)
    before = _counts(plat)
    b = bundle("run-one")
    cid, jid = a.launch(state_db(plat), "lab-a", b, confirmed_by=a.TERMINAL, clock=clock)
    after = _counts(plat)
    assert (after[0] - before[0], after[1] - before[1]) == (1, 1)
    row = sql(plat, "SELECT id, sha256, kind FROM confirmations WHERE id = ?", (cid,))[0]
    assert row[1] == common.bundle_sha256(b) and row[2] == "launch"
    assert sql(plat, "SELECT kind FROM jobs WHERE id = ?", (jid,))[0][0] == "launch_nextflow"


def test_tcb02_a_terminal_cancel_queues_one_cancel(tmp_path):
    a = actions()
    plat, _, clock = setup(tmp_path)
    cb = _cancel_bundle(plat)
    before = _counts(plat)
    cid, jid = a.cancel(state_db(plat), "lab-a", cb, confirmed_by=a.TERMINAL, clock=clock)
    after = _counts(plat)
    assert (after[0] - before[0], after[1] - before[1]) == (1, 1)
    assert sql(plat, "SELECT kind FROM jobs WHERE id = ?", (jid,))[0][0] == "cancel_run"
    assert sql(plat, "SELECT kind FROM confirmations WHERE id = ?", (cid,))[0][0] == "cancel"


def _job_facts(plat, jid):
    return sql(plat, "SELECT kind, state, created_at, deadline_at FROM jobs WHERE id = ?", (jid,))[0]


def test_tcb03_clock_and_deadline_are_passed_down_unchanged(tmp_path):
    from abf_platform import confirm
    a = actions()
    p1, _, c1 = setup(tmp_path / "one")
    p2, _, c2 = setup(tmp_path / "two")
    _, j1 = a.launch(state_db(p1), "lab-a", bundle("run-one"), confirmed_by=a.TERMINAL, clock=c1, deadline_seconds=10)
    _, j2 = confirm.confirm_launch(state_db(p2), "lab-a", bundle("run-one"), clock=c2, deadline_seconds=10)
    assert _job_facts(p1, j1) == _job_facts(p2, j2)
    assert _job_facts(p1, j1)[3] - _job_facts(p1, j1)[2] == 10
    k1, k2 = _cancel_bundle(p1), _cancel_bundle(p2)
    _, cj1 = a.cancel(state_db(p1), "lab-a", k1, confirmed_by=a.TERMINAL, clock=c1, deadline_seconds=10)
    _, cj2 = confirm.confirm_cancel(state_db(p2), "lab-a", k2, clock=c2, deadline_seconds=10)
    assert _job_facts(p1, cj1) == _job_facts(p2, cj2)
    # offline_after is passed down too: with a far-away clock and a short limit both refuse in the same words
    far = Clock(c1.t + 1000)
    with pytest.raises(Exception) as e1:
        a.launch(state_db(p1), "lab-a", bundle("run-two"), confirmed_by=a.TERMINAL, clock=far, offline_after=10)
    with pytest.raises(Exception) as e2:
        confirm.confirm_launch(state_db(p2), "lab-a", bundle("run-two"), clock=far, offline_after=10)
    assert type(e1.value).__name__ == "JobRefused" and str(e1.value) == str(e2.value)


@pytest.mark.parametrize("value", ["yes", True, None, "TERMINAL", "terminal"])
def test_tcb04_to_b06_b09_anything_but_the_terminal_sentinel_is_refused_and_nothing_is_written(tmp_path, value):
    from abf_platform import jobs
    a = actions()
    plat, _, clock = setup(tmp_path)
    before = _counts(plat)
    with pytest.raises(jobs.JobRefused, match=REFUSED):
        a.launch(state_db(plat), "lab-a", bundle("run-one"), confirmed_by=value, clock=clock)
    assert _counts(plat) == before


def test_tcb09_the_sentinel_is_not_a_string_and_its_str_does_not_work(tmp_path):
    from abf_platform import jobs
    a = actions()
    assert not isinstance(a.TERMINAL, str)
    plat, _, clock = setup(tmp_path)
    before = _counts(plat)
    with pytest.raises(jobs.JobRefused, match=REFUSED):
        a.launch(state_db(plat), "lab-a", bundle("run-one"), confirmed_by=str(a.TERMINAL), clock=clock)
    assert _counts(plat) == before


def test_tcb07_a_missing_confirmed_by_writes_nothing(tmp_path):
    a = actions()
    plat, _, clock = setup(tmp_path)
    cb = _cancel_bundle(plat)
    before = _counts(plat)
    with pytest.raises(Exception):
        a.launch(state_db(plat), "lab-a", bundle("run-one"), clock=clock)
    with pytest.raises(Exception):
        a.cancel(state_db(plat), "lab-a", cb, clock=clock)
    assert _counts(plat) == before


@pytest.mark.parametrize("value", ["yes", True, None, "TERMINAL"])
def test_tcb08_a_cancel_is_refused_the_same_way(tmp_path, value):
    from abf_platform import jobs
    a = actions()
    plat, _, clock = setup(tmp_path)
    cb = _cancel_bundle(plat)
    before = _counts(plat)
    with pytest.raises(jobs.JobRefused, match=REFUSED):
        a.cancel(state_db(plat), "lab-a", cb, confirmed_by=value, clock=clock)
    assert _counts(plat) == before


def test_tcb10_the_check_comes_before_any_validation_or_database_access(tmp_path, monkeypatch):
    from abf_platform import jobs
    a = actions()
    missing = tmp_path / "nowhere" / "platform.db"

    def boom(*args, **kw):
        raise AssertionError("a database connection was opened")

    monkeypatch.setattr(sqlite3, "connect", boom)
    with pytest.raises(jobs.JobRefused) as e:
        a.launch(missing, "x", {}, confirmed_by="yes")
    assert str(e.value) == REFUSED
    with pytest.raises(jobs.JobRefused) as e:
        a.cancel(missing, "x", {}, confirmed_by="yes")
    assert str(e.value) == REFUSED
    assert not missing.exists() and not missing.parent.exists()


def test_tcb11_launch_refusals_are_the_old_words_and_leave_nothing(tmp_path):
    from abf_platform import confirm, jobs
    a = actions()
    plat, _, clock = setup(tmp_path)
    # (a) an environment that does not exist
    before = _counts(plat)
    with pytest.raises(jobs.JobRefused) as e1:
        a.launch(state_db(plat), "nope", bundle("run-one"), confirmed_by=a.TERMINAL, clock=clock)
    with pytest.raises(jobs.JobRefused) as e2:
        confirm.confirm_launch(state_db(plat), "nope", bundle("run-one"), clock=clock)
    assert str(e1.value) == str(e2.value) and _counts(plat) == before
    # (a2) an environment whose agent has gone quiet
    with pytest.raises(jobs.JobRefused) as e3:
        a.launch(state_db(plat), "lab-a", bundle("run-one"), confirmed_by=a.TERMINAL, clock=Clock(clock.t + 100000))
    with pytest.raises(jobs.JobRefused) as e4:
        confirm.confirm_launch(state_db(plat), "lab-a", bundle("run-one"), clock=Clock(clock.t + 100000))
    assert str(e3.value) == str(e4.value) and _counts(plat) == before
    # (b) a run name that is already used
    a.launch(state_db(plat), "lab-a", bundle("run-one"), confirmed_by=a.TERMINAL, clock=clock)
    before = _counts(plat)
    with pytest.raises(jobs.JobRefused) as e5:
        a.launch(state_db(plat), "lab-a", bundle("run-one"), confirmed_by=a.TERMINAL, clock=clock)
    with pytest.raises(jobs.JobRefused) as e6:
        confirm.confirm_launch(state_db(plat), "lab-a", bundle("run-one"), clock=clock)
    assert str(e5.value) == str(e6.value) and _counts(plat) == before


def test_tcb12_cancel_refusals_are_the_old_words_and_leave_nothing(tmp_path):
    from abf_platform import confirm, jobs
    a = actions()
    plat, _, clock = setup(tmp_path)
    cb = _cancel_bundle(plat)
    before = _counts(plat)
    other = dict(cb, agent="someone-else")
    with pytest.raises(jobs.JobRefused) as e1:
        a.cancel(state_db(plat), "lab-a", other, confirmed_by=a.TERMINAL, clock=clock)
    with pytest.raises(jobs.JobRefused) as e2:
        confirm.confirm_cancel(state_db(plat), "lab-a", other, clock=clock)
    assert str(e1.value) == str(e2.value) and _counts(plat) == before
    far = Clock(clock.t + 100000)
    with pytest.raises(jobs.JobRefused) as e3:
        a.cancel(state_db(plat), "lab-a", cb, confirmed_by=a.TERMINAL, clock=far)
    with pytest.raises(jobs.JobRefused) as e4:
        confirm.confirm_cancel(state_db(plat), "lab-a", cb, clock=far)
    assert str(e3.value) == str(e4.value) and _counts(plat) == before


# ---- the command line: spies on the action layer ------------------------------------------------------------------------

@pytest.fixture
def data(tmp_path, monkeypatch):
    return LaunchData(Inproc(tmp_path / "ip", monkeypatch))


def _terminal_answers(monkeypatch, answer):
    from abf_launch import terminal
    monkeypatch.setattr(terminal, "terminal_problem", lambda: None)
    monkeypatch.setattr(terminal, "ask", lambda lines, question: answer)


def _spy(monkeypatch, name):
    a = actions()
    calls = []

    def spy(*args, **kw):
        calls.append((args, kw))
        raise AssertionError("actions.%s must not be called" % name)

    monkeypatch.setattr(a, name, spy)
    return calls


def test_tcb14_answering_no_to_a_launch_never_reaches_the_action_layer(data, tmp_path, monkeypatch):
    calls = _spy(monkeypatch, "launch")
    _terminal_answers(monkeypatch, False)
    rc, out = data.ip.run(*data.launch_args(tmp_path))
    assert rc == 1 and "未送出" in out and calls == []
    assert data.snapshot() == (0, 0, 0, 0)


def test_tcb15_without_a_terminal_the_launch_is_refused_before_any_question(data, tmp_path, monkeypatch):
    calls = _spy(monkeypatch, "launch")
    rc, out = data.ip.run(*data.launch_args(tmp_path))
    assert rc != 0 and "沒有任何旗標或環境變數能代替這個回答" in out and calls == []
    assert data.snapshot() == (0, 0, 0, 0)


def test_tcb17_answering_no_to_a_cancel_never_reaches_the_action_layer(data, tmp_path, monkeypatch):
    hand_over(data)
    calls = _spy(monkeypatch, "cancel")
    _terminal_answers(monkeypatch, False)
    rc, out = data.ip.run("cancel", "run-one")
    assert rc == 1 and "未取消" in out and calls == []
    assert (data.count("jobs"), data.count("confirmations")) == (0, 0)


def test_tcb13_answering_yes_calls_the_action_layer_with_the_terminal_sentinel(data, tmp_path, monkeypatch):
    from abf_platform import jobs
    a = actions()
    seen = []

    def stop(*args, **kw):
        seen.append(kw)
        raise jobs.JobRefused("stop here")

    monkeypatch.setattr(a, "launch", stop)
    _terminal_answers(monkeypatch, True)
    rc, out = data.ip.run(*data.launch_args(tmp_path))
    assert rc == 1 and len(seen) == 1 and seen[0]["confirmed_by"] is a.TERMINAL


def _cli_tree():
    return ast.parse((PLATFORM_DIR / "abf_launch" / "cli.py").read_text(encoding="utf-8"))


def test_tcb18_cli_reaches_launch_and_cancel_only_through_actions_after_the_question():
    src = (PLATFORM_DIR / "abf_launch" / "cli.py").read_text(encoding="utf-8")
    assert not imports_confirm(src, "abf_launch/cli.py")
    tree = _cli_tree()
    for fname, action in (("cmd_launch", "launch"), ("cmd_cancel", "cancel")):
        fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fname][0]
        asks = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "ask" and getattr(n.func.value, "id", "") == "terminal"]
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and getattr(n.func.value, "id", "") == "actions" and n.func.attr == action]
        assert asks and len(calls) == 1, fname
        assert calls[0].lineno > min(asks), fname
        kw = {k.arg: k.value for k in calls[0].keywords}
        assert isinstance(kw.get("confirmed_by"), ast.Attribute) and kw["confirmed_by"].attr == "TERMINAL" \
            and kw["confirmed_by"].value.id == "actions", fname


def test_tcb19_the_question_and_the_terminal_check_stay_in_terminal_py():
    from abf_launch import terminal
    assert callable(terminal.terminal_problem) and callable(terminal.ask)
    src = (PLATFORM_DIR / "abf_launch" / "cli.py").read_text(encoding="utf-8")
    assert not re.search(r"\binput\(", src) and "sys.stdin" not in src


# ---- US3: who may import and call what ---------------------------------------------------------------------------------------

def test_tcc01_mcp_server_imports_only_actions_from_the_platform():
    src = (PKG / "mcp_server.py").read_text(encoding="utf-8")
    # 009d: http_auth (the bearer check); 009g: guidance (instructions, prompts, resources). The rule is otherwise unchanged
    assert platform_submodules(src, "abf_platform/mcp_server.py") == {"actions", "guidance", "http_auth"}


def test_tcc02_mcp_server_does_not_mention_launch_cancel_terminal_or_confirm():
    src = (PKG / "mcp_server.py").read_text(encoding="utf-8")
    assert action_refs(src, "abf_platform/mcp_server.py") == []
    assert not re.search(r"confirm\b", src)


def test_tcc03_only_the_action_layer_imports_confirm():
    bad = []
    for p, rel in source_files():
        if rel.startswith("abf_platform/actions/"):
            continue
        if imports_confirm(p.read_text(encoding="utf-8"), rel):
            bad.append(rel)
    assert bad == [] and (PKG / "actions").is_dir()
    assert any(imports_confirm(p.read_text(encoding="utf-8"), rel) for p, rel in source_files()
               if rel.startswith("abf_platform/actions/")), "actions must be where confirm is used"


def test_tcc04_only_the_terminal_cli_and_the_action_layer_reach_launch_cancel_terminal():
    hits = {}
    for p, rel in source_files():
        if rel.startswith("abf_platform/actions/") or rel == "abf_launch/cli.py":
            continue
        found = action_refs(p.read_text(encoding="utf-8"), rel)
        if found:
            hits[rel] = found
    assert hits == {}


def test_tcc05_the_scans_turn_red_on_made_up_offenders():
    assert platform_submodules("from . import jobs\nfrom . import actions\n", "abf_platform/mcp_server.py") == {"jobs", "actions"}
    assert platform_submodules("import abf_platform.store\n", "abf_platform/mcp_server.py") == {"store"}
    assert platform_submodules("from .jobs import x\n", "abf_platform/mcp_server.py") == {"jobs"}
    assert platform_submodules("from . import actions\n", "abf_platform/mcp_server.py") == {"actions"}
    for src, rel in (("from abf_platform import confirm\n", "abf_launch/x.py"),
                     ("from . import confirm\n", "abf_platform/x.py"),
                     ("from .confirm import confirm_launch\n", "abf_platform/x.py"),
                     ("import abf_platform.confirm\n", "abf_station/x.py"),
                     ("from .. import confirm\n", "abf_platform/actions/x.py"),
                     ("import importlib\nimportlib.import_module('abf_platform.confirm')\n", "abf_station/x.py")):
        assert imports_confirm(src, rel), src
    assert not imports_confirm("from . import actions\nfrom . import jobs\n", "abf_platform/x.py")
    for src in ("from abf_platform import actions as a\na.launch(1)\n",
                "from abf_platform import actions\nactions.cancel(1)\n",
                "from abf_platform.actions import TERMINAL\n",
                "from abf_platform.actions import launch as go\n",
                "from . import actions as z\nx = z.TERMINAL\n",
                "import abf_platform.actions\nabf_platform.actions.launch(1)\n"):
        assert action_refs(src, "abf_platform/x.py"), src
    assert action_refs("from . import actions\nactions.list_runs(1)\n", "abf_platform/x.py") == []
    assert action_refs("from abf_station import launch\nlaunch.render_bundle()\n", "abf_platform/x.py") == []


# ---- US4 ---------------------------------------------------------------------------------------------------------------------

def test_tcd01_the_package_is_listed_for_packaging():
    text = (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    listed = set(re.findall(r'"([^"]+)"', re.search(r"^packages\s*=\s*\[(.*?)\]", text, re.S | re.M).group(1)))
    assert "abf_platform.actions" in listed
    for init in PKG.rglob("__init__.py"):
        dotted = ".".join(["abf_platform"] + list(init.parent.relative_to(PKG).parts))
        assert dotted in listed, dotted


def test_tcd03_confirm_says_who_may_call_it_now():
    text = (PKG / "confirm.py").read_text(encoding="utf-8")
    assert "Only the terminal commands (abf_launch) call this module" not in text
    assert "scans for that" not in text
    assert "actions" in text.split('"""')[1]


def test_tcd04_docs_have_an_action_layer_section():
    text = (REPO_ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    m = re.search(r"^#+ [^\n]*Action layer[^\n]*\n(.*?)(?=^#+ |\Z)", text, re.S | re.M | re.I)
    assert m, "no 'Action layer' section"
    body = m.group(1)
    assert "platform/abf_platform/actions" in body and "terminal" in body.lower() and len(body.splitlines()) < 30


def test_tcd05_changelog_has_a_line_for_it():
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = text.split("## 3.0.0-dev")[1]
    assert re.search(r"^- .*009b.*action layer|^- .*action layer.*009b", unreleased, re.I | re.M)


# ---- not in scope ------------------------------------------------------------------------------------------------------------

def test_tce01_no_write_tool_on_the_server(tmp_path):
    names = {t.name for t in _tools(_server(str(tmp_path / "index.db")))}
    assert names == set(READ_NAMES) and not any(re.search(r"launch|cancel|confirm", n) for n in names)


def test_tce02_the_receiver_has_the_routes_of_the_starting_point(tmp_path):
    from abf_platform import receiver
    app = receiver.create_app(tmp_path / "index.db", tmp_path / "tokens.db")
    got = sorted((getattr(r, "path", "?"), tuple(sorted(getattr(r, "methods", None) or []))) for r in app.routes)
    assert got == ROUTES_V3


def test_tce03_no_elicitation_in_the_platform():
    bad = [rel for p, rel in source_files() if "elicit" in p.read_text(encoding="utf-8").lower()]
    assert bad == []


def test_tce04_the_write_actions_take_no_identity():
    a = actions()
    for fn in (a.launch, a.cancel):
        params = inspect.signature(fn).parameters
        # 009d: `caller` (keyword-only, default None) is recorded only; it is never a confirmation
        assert list(params) == ["state_path", "ce_name", "bundle", "confirmed_by", "clock", "deadline_seconds", "offline_after",
                                "caller"]
        assert params["confirmed_by"].kind is inspect.Parameter.KEYWORD_ONLY
        assert params["clock"].kind is inspect.Parameter.KEYWORD_ONLY
        assert params["caller"].kind is inspect.Parameter.KEYWORD_ONLY and params["caller"].default is None


def test_tce05_no_resume_or_retry_in_the_action_layer():
    a = actions()
    assert not [n for n in dir(a) if re.search(r"resume|retry", n)]


def test_tce06_the_action_layer_reads_no_environment_and_no_switch_opens_it(tmp_path, monkeypatch):
    from abf_platform import jobs
    a = actions()
    for p in (PKG / "actions").rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        tree = ast.parse(text)
        assert not any(isinstance(n, ast.Attribute) and n.attr in ("environ", "getenv") for n in ast.walk(tree)), p
        assert not re.search(r"sbatch", text), p
    for k in ("ABF_DEV", "ABF_PLATFORM_DEV", "ABF_PLATFORM_YES", "ABF_YES"):
        monkeypatch.setenv(k, "1")
    plat, _, clock = setup(tmp_path)
    before = _counts(plat)
    with pytest.raises(jobs.JobRefused, match=REFUSED):
        a.launch(state_db(plat), "lab-a", bundle("run-one"), confirmed_by="yes", clock=clock)
    assert _counts(plat) == before


def test_tce07_exactly_the_five_flow_prompts_on_the_server(tmp_path):
    # 009g (TC-603): 009b's prompt-less server is superseded by one prompt per flow skill, text = SKILL.md body.
    server = _server(str(tmp_path / "index.db"))
    prompts = asyncio.run(server.list_prompts())
    flow_dirs = sorted(d.name for d in (REPO_ROOT / "skills").iterdir() if d.is_dir() and d.name != "operational")
    assert sorted(p.name for p in prompts) == flow_dirs == ["downstream", "finish", "launch", "runs", "setup"]
    for name in flow_dirs:
        raw = (REPO_ROOT / "skills" / name / "SKILL.md").read_bytes().decode("utf-8")
        body = raw[raw.index("\n---\n", 3) + len("\n---\n"):]
        res = asyncio.run(server.get_prompt(name))
        assert len(res.messages) == 1 and res.messages[0].content.text == body
