# Nothing existing: tests of compute environments (the Seqera model), the commands and the read-only MCP tools; the model is ours.
"""Compute environments: create, validate, primary, disable, credentials, MCP views (feature 007)."""
import json
import os
import re
import sqlite3
import time

import pytest

from helpers import (Platform, all_files_digest, db_bytes, free_port, pkg_env, run_cli, start_cli, stop_proc,
                     tool_json, tool_text, wait_port, mcp_call, mcp_http_call, REPO_ROOT, PLATFORM_DIR)
from station_harness import Inproc

CRED = re.compile(r"credential|憑證")
AGENT_SIDE = re.compile(r"agent|代理")

# the 13 types that are modelled and not supported, with fields from specs/007-station-agent/research.md
UNSUPPORTED = {
    "awsbatch-platform": {"workDir": "s3://lab-bucket/work", "region": "eu-west-1", "headQueue": "head-q", "computeQueue": "comp-q"},
    "googlebatch-platform": {"workDir": "gs://lab-bucket/work", "location": "europe-west2", "spot": True},
    "azbatch-platform": {"workDir": "az://lab-container/work", "region": "westeurope", "vmType": "Standard_D4s_v3"},
    "awscloud-platform": {"workDir": "s3://lab-bucket/work", "instanceType": "m5.xlarge"},
    "azcloud-platform": {"workDir": "az://lab-container/work", "instanceType": "Standard_D4s_v3"},
    "googlecloud-platform": {"workDir": "gs://lab-bucket/work", "instanceType": "n2-standard-4", "zone": "europe-west2-a"},
    "k8s-platform": {"workDir": "/mnt/work", "namespace": "nf", "storageClaimName": "pvc-work", "storageMountPath": "/mnt"},
    "eks-platform": {"workDir": "/mnt/work", "clusterName": "lab-eks", "region": "eu-west-1", "namespace": "nf"},
    "gke-platform": {"workDir": "/mnt/work", "clusterName": "lab-gke", "location": "europe-west2", "namespace": "nf"},
    "altair-platform": {"workDir": "/shared/work", "headQueue": "workq", "hostName": "login.example"},
    "lsf-platform": {"workDir": "/shared/work", "headQueue": "normal", "hostName": "login.example"},
    "uge-platform": {"workDir": "/shared/work", "headQueue": "all.q", "hostName": "login.example"},
    "moab-platform": {"workDir": "/shared/work", "headQueue": "batch", "hostName": "login.example"},
}


@pytest.fixture
def ip(tmp_path, monkeypatch):
    return Inproc(tmp_path, monkeypatch)


def online_agent(ip, name="a1", seen=None):
    from abf_platform import agents
    agents.register(ip.state_db, name, "0.1.0", (lambda: seen) if seen is not None else time.time)


def make_available(ip, ce_name, agent="a1", ok=True):
    """Give the environment a preflight verdict the way an agent does: through the agent endpoints."""
    from starlette.testclient import TestClient
    from abf_platform import jobs, receiver, store
    tok = store.create_token(ip.tokens, kind="agent", agent_name=agent)
    client = TestClient(receiver.create_app(ip.index, ip.tokens))
    h = {"Authorization": "Bearer " + tok}
    assert client.post("/agent/hello", json={"name": agent, "version": "0.1.0"}, headers=h).status_code == 200
    jid = jobs.enqueue_preflight(ip.state_db, ce_name, time.time)
    os.environ["ABF_AGENT_POLL_SECONDS"] = "0.5"
    try:
        got = client.post("/agent/poll", json={"name": agent}, headers=h).json()["job"]
    finally:
        del os.environ["ABF_AGENT_POLL_SECONDS"]
    assert got["id"] == jid
    checks = [{"name": "sinfo", "status": "pass" if ok else "fail", "detail": "x"}]
    r = client.post("/agent/result/%d" % jid, json={"state": "done", "result": {"ok": ok, "checks": checks}}, headers=h)
    assert r.status_code == 200


def test_tc024_a_full_slurm_environment_is_stored_field_by_field(ip):
    # TC-024
    rc, out = ip.create(
        "lab-a", description="the lab's cluster", credentials="nchc-ssh", agent="a1", host_name="login.example",
        work_dir="/data/work", launch_dir="/data/launch", head_queue="normal", compute_queue="dev",
        max_queue_size="50", head_job_options="--time=02:00:00", pre_run="module load java",
        post_run="echo finished", env=["NXF_OPTS=-Xmx2g", "compute:SCRATCH_NOTE=tmp", "both:SHARED_NOTE=1"],
        nextflow_config="process.queue = 'normal'\nexecutor.queueSize = 50")
    assert rc == 0, out
    ce = ip.mcp_json("get_compute_env", {"name": "lab-a"})
    assert ce["name"] == "lab-a" and ce["description"] == "the lab's cluster"
    assert ce["platform"] == "slurm-platform" and ce["credentialsId"] == "nchc-ssh" and ce["agent"] == "a1"
    assert ce["primary"] is False and ce["lastUsed"] is None
    assert ce["id"] and ce["dateCreated"] and ce["lastUpdated"]
    assert ce["status"] == "creating" and ce["message"]
    cfg = ce["config"]
    assert cfg["workDir"] == "/data/work" and cfg["launchDir"] == "/data/launch"
    assert cfg["headQueue"] == "normal" and cfg["computeQueue"] == "dev" and cfg["maxQueueSize"] == 50
    assert cfg["hostName"] == "login.example" and cfg["headJobOptions"] == "--time=02:00:00"
    assert cfg["preRunScript"] == "module load java" and cfg["postRunScript"] == "echo finished"
    assert cfg["nextflowConfig"] == "process.queue = 'normal'\nexecutor.queueSize = 50"
    assert cfg["environment"] == [
        {"name": "NXF_OPTS", "value": "-Xmx2g", "head": True, "compute": False},
        {"name": "SCRATCH_NOTE", "value": "tmp", "head": False, "compute": True},
        {"name": "SHARED_NOTE", "value": "1", "head": True, "compute": True}]
    assert b"nchc-ssh" in ip.all_bytes()


def test_tc027_names_are_unique_and_one_to_a_hundred_characters(ip):
    # TC-027
    assert ip.create_slurm("lab-a")[0] == 0
    n = len(ip.rows()["compute_envs"])
    rc, out = ip.create_slurm("lab-a")
    assert rc != 0 and re.search(r"already exists|duplicate|重複", out)
    rc, out = ip.create_slurm("")
    assert rc != 0 and re.search(r"1.*100|長度", out)
    rc, out = ip.create_slurm("x" * 101)
    assert rc != 0 and re.search(r"1.*100|長度", out)
    assert len(ip.rows()["compute_envs"]) == n
    assert ip.create_slurm("y" * 100)[0] == 0
    assert len(ip.rows()["compute_envs"]) == n + 1


def test_tc028_a_missing_name_or_work_dir_is_named_and_leaves_nothing_behind(ip):
    # TC-028
    assert ip.run("ce", "list")[0] == 0
    before = ip.all_bytes()
    rc, out = ip.run("ce", "create", "--platform", "slurm-platform", "--work-dir", "/data/work", "--head-queue", "normal")
    assert rc != 0 and re.search(r"name", out)
    rc, out = ip.create("lab-a", work_dir=None, head_queue="normal")
    assert rc != 0 and re.search(r"workDir|work-dir|work dir", out)
    assert ip.rows()["compute_envs"] == []
    assert ip.all_bytes() == before


@pytest.mark.parametrize("field,flag", [("head queue", "head_queue"), ("compute queue", "compute_queue"),
                                         ("work dir", "work_dir")])
def test_tc029_values_a_shell_would_act_on_are_refused_with_the_field_named(ip, field, flag):
    # TC-029
    bad_queue = ["normal; touch X", "$(id)", "`id`", "q|x", "a b", "", "q&x", "q'x", 'q"x', "q\nx", "a/b", "*", "q>x"]
    bad_path = ["/x; touch X", "/x$(id)", "/x`id`", "/x|y", "/x y", "/x/../y", "relative/path", "", "/x\nrm", "/x*", "/x?",
                "/x>y", "/x'y", "~/x"]
    for value in (bad_queue if "queue" in field else bad_path):
        kw = {"head_queue": "normal", "work_dir": "/data/work", "launch_dir": "/data/launch"}
        kw[flag] = value
        if flag == "compute_queue":
            kw["compute_queue"] = value
        rc, out = ip.create("lab-x", **kw)
        assert rc != 0, (flag, value, out)
        assert re.search(r"head.?queue|compute.?queue|work.?dir|workDir|headQueue|computeQueue", out, re.I), (flag, value, out)
    assert ip.rows().get("compute_envs", []) == []


def test_tc029_good_queue_names_and_absolute_paths_are_accepted(ip):
    # TC-029 (the other side: the rule is not "refuse everything")
    rc, out = ip.create_slurm("lab-a", head_queue="ctest-1.x_y", compute_queue="Dev_2", work_dir="/data/work-dir/v1.2")
    assert rc == 0, out


@pytest.mark.parametrize("platform_id", sorted(UNSUPPORTED))
def test_tc030_the_thirteen_modelled_types_are_stored_as_not_supported(ip, platform_id):
    # TC-030
    rc, out = ip.run("ce", "create", "--name", "ce-" + platform_id, "--platform", platform_id,
                     "--config-json", json.dumps(UNSUPPORTED[platform_id]))
    assert rc == 0, out
    ce = ip.show("ce-" + platform_id)
    assert ce["platform"] == platform_id and ce["status"] == "unsupported"
    assert re.search(r"real account|真的帳號", ce["message"])
    for k, v in UNSUPPORTED[platform_id].items():
        assert ce["config"][k] == v
    docs = (REPO_ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    assert "`%s`" % platform_id in docs, "docs/PLATFORM.md must list the type identifier"


def test_tc032_only_fourteen_types_exist_and_seqera_compute_is_refused_with_its_reason(ip):
    # TC-032
    from abf_platform import compute_envs
    assert len(compute_envs.KINDS) == 14 and "slurm-platform" in compute_envs.KINDS
    assert sorted(set(UNSUPPORTED) | {"slurm-platform"}) == sorted(compute_envs.KINDS)
    for bad in ("nonsense", "seqera-compute", "seqeracompute-platform", "local-platform"):
        rc, out = ip.run("ce", "create", "--name", "x-" + bad, "--platform", bad, "--work-dir", "/data/work")
        assert rc != 0, bad
        assert "slurm-platform" in out and "awsbatch-platform" in out, "the message must list the usable types"
        if bad.startswith("seqera"):
            assert re.search(r"hosted|託管", out) and re.search(r"no counterpart|沒有對應", out)
    assert ip.rows().get("compute_envs", []) == []


def test_tc033_list_and_get_give_the_seqera_shaped_object(ip):
    # TC-033
    assert ip.create_slurm("lab-a", env=["NXF_OPTS=-Xmx2g"], pre_run="module load java", post_run="true",
                           nextflow_config="process.queue = 'normal'", credentials="nchc-ssh")[0] == 0
    listed = ip.mcp_json("list_compute_envs")["compute_envs"]
    one = ip.mcp_json("get_compute_env", {"name": "lab-a"})
    assert len(listed) == 1 and listed[0]["name"] == "lab-a"
    for view in (listed[0], one):
        assert {"id", "name", "description", "platform", "credentialsId", "status", "message", "primary",
                "dateCreated", "lastUpdated", "lastUsed", "config"} <= set(view)
        assert {"workDir", "preRunScript", "postRunScript", "environment", "nextflowConfig"} <= set(view["config"])
        for e in view["config"]["environment"]:
            assert set(e) == {"name", "value", "head", "compute"}
    research = open(str(REPO_ROOT / "specs" / "007-station-agent" / "research.md"), encoding="utf-8").read()
    for name in ("credentialsId", "dateCreated", "lastUpdated", "lastUsed", "workDir", "preRunScript",
                 "postRunScript", "nextflowConfig", "environment"):
        assert name in research, "research.md must record the Seqera field " + name


def test_tc034_exactly_one_primary_and_an_unknown_name_changes_nothing(ip):
    # TC-034
    for n in "ABC":
        assert ip.create_slurm(n)[0] == 0
    assert ip.run("ce", "primary", "A")[0] == 0
    assert ip.run("ce", "primary", "B")[0] == 0
    prim = [e["name"] for e in ip.mcp_json("list_compute_envs")["compute_envs"] if e["primary"]]
    assert prim == ["B"]
    before = ip.rows()
    rc, out = ip.run("ce", "primary", "nope")
    assert rc != 0 and re.search(r"not found|找不到", out) and "nope" in out
    assert ip.rows() == before


def test_tc035_disabling_clears_the_primary_mark_and_blocks_jobs(ip):
    # TC-035
    for n in "BC":
        assert ip.create_slurm(n, agent="a1")[0] == 0
    online_agent(ip)
    assert ip.run("ce", "primary", "B")[0] == 0
    assert ip.run("ce", "disable", "C")[0] == 0
    assert ip.show("B")["primary"] is True
    assert ip.run("ce", "disable", "B")[0] == 0
    envs = {e["name"]: e for e in ip.mcp_json("list_compute_envs")["compute_envs"]}
    assert envs["B"]["status"] == "disabled" and envs["B"]["primary"] is False
    assert not [e for e in envs.values() if e["primary"]]
    jobs_before = ip.rows()["jobs"]
    rc, out = ip.run("ce", "preflight", "B")
    assert rc != 0 and re.search(r"disabled|已停用", out)
    res = ip.mcp_json("list_site_files", {"compute_env": "B", "path": "/data/work"})
    assert res["ok"] is False and re.search(r"disabled|已停用", res["message"])
    assert ip.rows()["jobs"] == jobs_before == []


CANARY = "CANARYsecret9f2c71aa"
KEY_ID = "AKI" + "ACANARYZZ99887766"
SESSION_ID = "ASIACANARYZZ99887766"


@pytest.mark.parametrize("label,flags", [
    ("private key in the Nextflow config", {"nextflow_config": "process.ext.x = '''-----" + "BEGIN OPENSSH PRIVATE KEY-----\n%s'''" % CANARY}),
    ("AKIA key id in an environment value", {"env": ["SOMEVAR=" + KEY_ID]}),
    ("ASIA key id in an environment value", {"env": ["SOMEVAR=" + SESSION_ID]}),
    ("aws_secret_access_key in the Nextflow config", {"nextflow_config": "aws_secret_access_key = " + CANARY}),
    ("a secret named environment variable", {"env": ["AWS_SECRET_ACCESS_KEY=" + CANARY]}),
    ("export TOKEN in the pre-run script", {"pre_run": "export TOKEN=" + CANARY}),
    ("the platform's own token in a value", {"env": ["SOMEVAR=abf_" + CANARY + "0123456789abcdefghij"]}),
    ("a password field", {"config_json": json.dumps({"password": CANARY})}),
    ("a token field", {"config_json": json.dumps({"token": CANARY})}),
    ("a secret field", {"config_json": json.dumps({"secret": CANARY})}),
    ("an apiKey field", {"config_json": json.dumps({"apiKey": CANARY})}),
    ("a nested password field", {"config_json": json.dumps({"extra": {"inner": [{"password": CANARY}]}})}),
])
def test_tc036_credential_shapes_are_refused_and_never_echoed(ip, label, flags):
    # TC-036
    before = ip.rows()
    rc, out = ip.create_slurm("lab-x", **flags)
    assert rc != 0, label
    assert CRED.search(out) and AGENT_SIDE.search(out), out
    assert "CANARY" not in out, "a rejected value must not be echoed back: " + label
    assert b"CANARY" not in ip.all_bytes()
    assert ip.rows() == before


def test_tc037_an_ordinary_slurm_config_is_not_mistaken_for_a_credential(ip):
    # TC-037
    rc, out = ip.create_slurm("lab-a", nextflow_config="process.queue = 'normal'\nexecutor.queueSize = 50",
                              env=["NXF_OPTS=-Xmx2g"], pre_run="module load java", credentials="nchc-ssh")
    assert rc == 0, out


def test_tc038_update_changes_what_is_asked_and_refuses_what_create_refuses(ip):
    # TC-038
    assert ip.create_slurm("lab-a")[0] == 0
    first = ip.show("lab-a")
    time.sleep(0.05)
    rc, out = ip.run("ce", "update", "lab-a", "--work-dir", "/data/work2")
    assert rc == 0, out
    second = ip.show("lab-a")
    assert second["config"]["workDir"] == "/data/work2" and second["lastUpdated"] > first["lastUpdated"]
    for k in ("name", "platform", "dateCreated", "id", "agent"):
        assert second[k] == first[k]
    assert {k: v for k, v in second["config"].items() if k != "workDir"} == \
           {k: v for k, v in first["config"].items() if k != "workDir"}
    for bad in (["--head-queue", "q; rm"], ["--nextflow-config", "-----" + "BEGIN RSA PRIVATE KEY-----\n" + CANARY]):
        rc, out = ip.run("ce", "update", "lab-a", *bad)
        assert rc != 0 and "CANARY" not in out
        assert ip.show("lab-a") == second
    assert ip.run("ce", "update", "missing", "--work-dir", "/data/x")[0] != 0


def test_tc096_only_a_usable_environment_can_be_primary(ip):
    # TC-096
    assert ip.create_slurm("S", agent="a1")[0] == 0
    assert ip.create_slurm("D", agent="a1")[0] == 0
    assert ip.run("ce", "create", "--name", "U", "--platform", "awsbatch-platform",
                  "--config-json", json.dumps(UNSUPPORTED["awsbatch-platform"]))[0] == 0
    make_available(ip, "S")
    assert ip.run("ce", "primary", "S")[0] == 0
    make_available(ip, "D")
    assert ip.run("ce", "disable", "D")[0] == 0
    before = ip.rows()
    digest = ip.all_bytes()
    rc, out = ip.run("ce", "primary", "U")
    assert rc != 0 and re.search(r"unsupported|尚未支援", out) and re.search(r"primary|主要", out)
    rc, out = ip.run("ce", "primary", "D")
    assert rc != 0 and re.search(r"disabled|已停用", out) and re.search(r"primary|主要", out)
    assert ip.rows() == before and ip.all_bytes() == digest
    prim = [e["name"] for e in ip.mcp_json("list_compute_envs")["compute_envs"] if e["primary"]]
    assert prim == ["S"]
    assert ip.run("ce", "enable", "D")[0] == 0
    assert ip.show("D")["status"] == "available"
    assert ip.run("ce", "primary", "D")[0] == 0
    assert [e["name"] for e in ip.mcp_json("list_compute_envs")["compute_envs"] if e["primary"]] == ["D"]


def test_tc059_an_environment_that_is_not_available_cannot_run_a_listing(ip):
    # TC-059
    for n in ("creating", "invalid", "disabled"):
        assert ip.create_slurm(n, agent="a1")[0] == 0
    make_available(ip, "invalid", ok=False)
    make_available(ip, "disabled")
    assert ip.run("ce", "disable", "disabled")[0] == 0
    assert ip.show("creating")["status"] == "creating"
    assert ip.show("invalid")["status"] == "invalid"
    online_agent(ip)
    queued_before = len(ip.rows()["jobs"])
    for n in ("creating", "invalid", "disabled"):
        res = ip.mcp_json("list_site_files", {"compute_env": n, "path": "/data/work"})
        assert res["ok"] is False and re.search(r"status|狀態|disabled|已停用", res["message"]), res
    assert len(ip.rows()["jobs"]) == queued_before


def test_tc072_the_read_only_tools_describe_environments_and_agents(ip):
    # TC-072
    from abf_platform import agents
    assert ip.create_slurm("lab-a", agent="up")[0] == 0 and ip.create_slurm("lab-b", agent="down")[0] == 0
    now = time.time()
    agents.register(ip.state_db, "up", "0.1.0", lambda: now)
    agents.register(ip.state_db, "down", "0.0.9", lambda: now - 3600)
    listed = ip.mcp_json("list_compute_envs")["compute_envs"]
    assert sorted(e["name"] for e in listed) == ["lab-a", "lab-b"]
    ags = {a["name"]: a for a in ip.mcp_json("list_agents")["agents"]}
    assert ags["up"]["status"] == "online" and ags["down"]["status"] == "offline"
    assert ags["up"]["version"] == "0.1.0" and ags["down"]["version"] == "0.0.9"
    assert ags["up"]["last_contact_at"] and ags["down"]["last_contact_at"]
    _, outs = ip.mcp([("get_compute_env", {"name": "missing-env"}), ("list_compute_envs", {})])
    assert not outs[0].is_error
    text = tool_text(outs[0])
    assert "missing-env" in text and re.search(r"not found|找不到", text) and "Traceback" not in text
    assert len(tool_json(outs[1])["compute_envs"]) == 2


def test_tc073_the_read_only_tools_write_nothing_and_show_no_token(ip):
    # TC-073
    from abf_platform import store
    run_token = store.create_token(ip.tokens)
    agent_tok = store.create_token(ip.tokens, kind="agent", agent_name="a1")
    assert ip.create_slurm("lab-a", agent="a1")[0] == 0
    online_agent(ip)
    digest = all_files_digest(ip.index, ip.tokens, ip.state_db)
    import hashlib
    _, outs = ip.mcp([("list_compute_envs", {}), ("get_compute_env", {"name": "lab-a"}), ("list_agents", {}),
                      ("list_runs", {})])
    assert all_files_digest(ip.index, ip.tokens, ip.state_db) == digest
    for o in outs:
        t = tool_text(o)
        for tok in (run_token, agent_tok):
            assert tok not in t and hashlib.sha256(tok.encode()).hexdigest() not in t
        assert "authorization" not in t.lower()


def test_tc071_exactly_six_read_only_tools_over_stdio_and_http(tmp_path):
    # TC-071. 009c: the six read-only tools are still exactly these and still read-only, over stdio and HTTP alike; the server has
    # two more, launch and cancel, which are marked as writing and are looked at in test_human_channel.py
    env = pkg_env(ABF_PLATFORM_DB=tmp_path / "data" / "index.db")
    calls = [("list_compute_envs", {}), ("list_agents", {})]
    tools, via_stdio = mcp_call(env, calls)
    # 009d: HTTP needs a personal access token; only this input changed, the assertions below did not
    from abf_platform import store
    tokens_db = tmp_path / "data" / "tokens.db"
    pat = store.create_token(tokens_db, kind="pat", user_id=store.create_user(tokens_db, "tc071", "lab"))
    port = free_port()
    proc = start_cli(["mcp", "--http", "--port", str(port)], env, tmp_path / "mcp.log")
    try:
        wait_port(port, proc=proc)
        tools_http, via_http = mcp_http_call("http://127.0.0.1:%d/mcp" % port, calls, token=pat)
    finally:
        stop_proc(proc)
    want = ["get_compute_env", "get_run", "list_agents", "list_compute_envs", "list_runs", "list_site_files"]
    for ts in (tools, tools_http):
        assert sorted(t.name for t in ts) == sorted(want + ["launch", "cancel", "forget"])
        for t in [t for t in ts if t.name in want]:
            assert t.annotations is not None and t.annotations.read_only_hint is True
            assert t.annotations.destructive_hint is not True
            assert not re.search(r"launch|cancel|delete|clean|write|create|update|enqueue", t.name)
    for a, b in zip(via_stdio, via_http):
        assert tool_json(a) == tool_json(b)


def test_tc063_no_door_takes_a_job_kind_or_a_command(tmp_path, monkeypatch):
    # TC-063
    from abf_platform import cli, mcp_server
    plat = Platform(tmp_path / "p")
    tok = plat.store.create_token(plat.tokens, kind="agent", agent_name="a1")
    for method in ("POST", "PUT", "DELETE", "GET"):
        for path in ("/jobs", "/job", "/agent/enqueue", "/agent/job", "/agent/jobs", "/enqueue", "/agent/run",
                     "/agent/exec", "/compute-envs", "/ce"):
            for headers in ({}, {"Authorization": "Bearer " + tok}):
                r = plat.client.request(method, path, json={"kind": "preflight", "command": "rm -rf /"}, headers=headers)
                assert r.status_code in (404, 405, 401), (method, path, r.status_code)
    server = mcp_server.build_server(plat.index)
    import asyncio
    from mcp import Client

    async def tools():
        async with Client(server) as c:
            return (await c.list_tools()).tools

    banned = {"command", "cmd", "script", "kind", "shell", "args", "argv", "exec"}
    for t in asyncio.run(tools()):
        assert not (set(t.input_schema.get("properties", {})) & banned), t.name

    seen = []

    def walk(parser, trail):
        for act in parser._actions:
            for opt in getattr(act, "option_strings", []):
                seen.append((trail, opt.lstrip("-")))
            if hasattr(act, "choices") and isinstance(getattr(act, "choices", None), dict):
                for name, sub in act.choices.items():
                    seen.append((trail, name))
                    walk(sub, trail + [name])

    walk(cli.build_parser(), [])
    words = {w for _, w in seen}
    # feature 007b (TC-060): the subcommands are the old ones plus launch, cancel, fetch-records and launches; the words
    # launch and cancel appear nowhere else
    assert not (words & {"command", "cmd", "script", "kind", "shell", "args", "exec", "submit", "enqueue"}), words
    top_level = set(next(a for a in cli.build_parser()._actions if isinstance(getattr(a, "choices", None), dict)).choices)
    assert top_level == {"serve", "token", "agent-token", "ce", "mcp", "rebuild", "launch", "cancel", "fetch-records",
                         "launches", "user", "pat", "web", "runs", "oauth", "forget"}, top_level     # 009c: plus `web`, the confirmation page; 116b: plus `runs`; 009i: plus `oauth` (revoke)
    assert [(trail, w) for trail, w in seen if w in ("launch", "cancel")] == [([], "launch"), ([], "cancel")]
    assert {"ce", "agent-token", "serve", "token", "mcp", "rebuild"} <= words


def test_tc084_no_launch_door_anywhere(tmp_path):
    # TC-084 (doors; the agent's refusal of a launch job is in test_station_fakeplatform.py)
    from abf_platform import cli
    plat = Platform(tmp_path / "p")
    for path in ("/launch", "/agent/launch", "/workflow/launch", "/submit", "/agent/submit"):
        for method in ("POST", "PUT"):
            assert plat.client.request(method, path, json={}).status_code in (404, 405, 401), path
    helptext = cli.build_parser().format_help() + "".join(
        sub.format_help() for a in cli.build_parser()._actions if isinstance(getattr(a, "choices", None), dict)
        for sub in a.choices.values())
    helptext = re.sub(r"launch folders?", "", helptext)  # `rebuild` takes the folders Nextflow was launched in
    # feature 007b (TC-060): the words launch and cancel may stand only as the names of the two new subcommands, and only in
    # these three places: the one list of subcommand names (exactly this list), their two lines in the table of subcommands,
    # and the usage line of each of the two
    names = "{serve,web,token,agent-token,user,pat,oauth,ce,mcp,rebuild,runs,launch,cancel,forget,launches,fetch-records}"    # 009c: plus `web`; 009i: plus `oauth`; 116b: plus `runs`
    assert helptext.count(names) >= 1, "the list of subcommands is exactly the old ones plus the four new ones (and runs, oauth)"
    helptext = helptext.replace(names, names.replace(",launch,cancel,forget,", ","))
    rows = re.findall(r"(?m)^ {4}(launch|cancel) {2,}\S", helptext)
    assert rows == ["launch", "cancel"], rows
    helptext = re.sub(r"(?m)^ {4}(launch|cancel)( {2,}\S)", lambda m: "    " + m.group(2), helptext)
    usages = re.findall(r"(?m)^usage: abf-platform (launch|cancel) ", helptext)
    assert usages == ["launch", "cancel"], usages
    helptext = re.sub(r"(?m)^usage: abf-platform (launch|cancel) ", "usage: abf-platform ", helptext)
    assert not re.search(r"\blaunch\b|\bsubmit\b|\bcancel\b", helptext, re.I)


def test_tc085_the_unsupported_types_never_touch_a_cloud_tool_or_library(ip, tmp_path, monkeypatch):
    # TC-085
    from station_harness import write_exec
    bindir = tmp_path / "bin"
    log = tmp_path / "cloud.log"
    for t in ("aws", "kubectl", "gcloud", "az", "ssh"):
        write_exec(bindir / t, "#!/bin/bash\necho \"$0 $*\" >> '%s'\n" % log)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    for pid, fields in UNSUPPORTED.items():
        rc, out = ip.run("ce", "create", "--name", "ce-" + pid, "--platform", pid, "--config-json", json.dumps(fields))
        assert rc == 0, out
        rc, out = ip.run("ce", "preflight", "ce-" + pid)
        assert rc != 0 and re.search(r"unsupported|not supported|尚未支援", out)
        assert ip.show("ce-" + pid)["status"] == "unsupported"
    assert not log.exists() or log.read_text() == ""
    toml = (PLATFORM_DIR / "pyproject.toml").read_text()
    for lib in ("boto3", "botocore", "azure", "google-cloud", "kubernetes"):
        assert lib not in toml
    for src in list((PLATFORM_DIR / "abf_platform").glob("*.py")) + list((PLATFORM_DIR / "abf_station").glob("*.py")):
        text = src.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(boto3|botocore|azure|google\.cloud|kubernetes)\b", text, re.M), src


def test_tc086_no_web_pages_no_confirmation_page_no_role_tables(tmp_path):
    # TC-086
    plat = Platform(tmp_path / "p")
    tok = plat.store.create_token(plat.tokens, kind="agent", agent_name="a1")
    for p in ("/", "/login", "/oauth/token", "/oauth/authorize", "/confirm", "/confirmation", "/ce", "/compute-envs"):
        assert plat.client.get(p).status_code in (404, 401, 405), p
        assert plat.client.get(p, headers={"Authorization": "Bearer " + tok}).status_code in (404, 405), p
    for db in (plat.index, plat.tokens, plat.dir / "platform.db"):
        assert banned_schema_words(db) == [], db.name


# 009c: the exception to the ban on session and password names, written as exact (database, table, column) triples like the one for
# index.db: the web password's hash and the browser login's table, both in tokens.db (decided by the maintainer 2026-10-17, plan
# "round 2"). A column of any other name or in any other place is still caught. The scan was the body of tc086; it is a function so a
# test (test_human_channel.py) can show that an extra column is still caught.
EXEMPT = {("index.db", "runs", "session_id"),     # added in 06848d0, Nextflow run session, not a web session (maintainer approved 2026-10-17)
          ("tokens.db", "users", "password_hash"),
          ("tokens.db", "web_sessions", "id_hash"), ("tokens.db", "web_sessions", "user_id"),
          ("tokens.db", "web_sessions", "created_at"), ("tokens.db", "web_sessions", "expires_at")}
EXEMPT_TABLES = {("tokens.db", "web_sessions")}


def banned_schema_words(db):
    """The (word, name) pairs of one database file's schema that the ban of tc086 catches."""
    con = sqlite3.connect(str(db))
    names = []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        names += [c[1].lower() for c in con.execute("PRAGMA table_info(%s)" % t) if (db.name, t, c[1].lower()) not in EXEMPT]
        if (db.name, t) not in EXEMPT_TABLES:
            names.append(t.lower())
    con.close()
    # 009d: identity (user, lab) is feature 009 (ADR 0006); roles stay out until 010
    allowed = {"users", "user_id", "caller_user_id", "owner_user_id", "label", "lab", "name", "disabled_at",
               "forgotten_at", "forgotten_by"}    # keep-submissions: "org" sits inside "forgotten"; these name when and by whom content was deleted    # 116: owner_user_id names an owner, not a login
    return [(word, n) for word in ("user", "role", "org", "team", "member", "login", "password", "email", "session", "cookie")
            for n in names if word in n and n not in allowed]


def test_tc039_environments_agents_and_tokens_survive_a_restart_and_a_rebuild(tmp_path):
    # TC-039
    from station_harness import RealPlatform
    import httpx
    plat = RealPlatform(tmp_path)
    try:
        tok = plat.agent_token("a1")
        assert plat.cli(["ce", "create", "--name", "lab-a", "--platform", "slurm-platform", "--work-dir", "/data/work",
                         "--head-queue", "normal", "--credentials", "nchc-ssh", "--agent", "a1"]).returncode == 0
        assert plat.cli(["ce", "primary", "lab-a"]).returncode == 0
        h = {"Authorization": "Bearer " + tok}
        assert httpx.post(plat.url + "/agent/hello", json={"name": "a1", "version": "0.1.0"}, headers=h).status_code == 200
        before = plat.cli(["ce", "show", "lab-a"]).stdout
        agents_before = plat.mcp_json("list_agents")
        plat.stop()
        plat.start()
        assert httpx.post(plat.url + "/agent/hello", json={"name": "a1", "version": "0.1.0"}, headers=h).status_code == 200
        folder = tmp_path / "launch" / ".nextflow"
        folder.mkdir(parents=True)
        (folder / "history").write_text("")
        digest = all_files_digest(plat.tokens, plat.state_db)
        plat.cli(["rebuild", str(tmp_path / "launch")])
        assert all_files_digest(plat.tokens, plat.state_db) == digest, "rebuild touched the token or state file"
        assert json.loads(plat.cli(["ce", "show", "lab-a"]).stdout) == json.loads(before)
        agents_after = plat.mcp_json("list_agents")
        assert [a["name"] for a in agents_after["agents"]] == [a["name"] for a in agents_before["agents"]] == ["a1"]
    finally:
        plat.stop()


def test_tc040_the_new_files_follow_the_008_location_rule(tmp_path):
    # TC-040
    for mode in ("db", "xdg"):
        home, cwd = tmp_path / mode / "home", tmp_path / mode / "cwd"
        home.mkdir(parents=True)
        cwd.mkdir()
        if mode == "db":
            target = tmp_path / mode / "chosen"
            env = pkg_env(HOME=home, ABF_PLATFORM_DB=target / "index.db", XDG_DATA_HOME=tmp_path / mode / "unused")
        else:
            target = tmp_path / mode / "xdg" / "abf-platform"
            env = pkg_env(HOME=home, XDG_DATA_HOME=tmp_path / mode / "xdg")
        r = run_cli(["ce", "create", "--name", "lab-a", "--platform", "slurm-platform", "--work-dir", "/data/work",
                     "--head-queue", "normal"], env=env, cwd=cwd)
        assert r.returncode == 0, r.stdout + r.stderr
        assert run_cli(["agent-token", "new", "a1"], env=env, cwd=cwd).returncode == 0
        names = sorted(p.name for p in target.iterdir())
        assert "platform.db" in names and "tokens.db" in names, names
        assert list(home.iterdir()) == [] and list(cwd.iterdir()) == []
        if mode == "db":
            assert not (tmp_path / mode / "unused").exists()
