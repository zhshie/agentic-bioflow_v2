# Nothing existing: tests that canary strings never reach the database; no scanner knows which Nextflow fields count as secret.
"""Metadata-only storage tests (feature 008, FR-008)."""
import copy
import json
import sqlite3

from helpers import db_bytes, load_scenario


def _begin_with(requests, **mutations):
    reqs = copy.deepcopy(requests)
    for r in reqs:
        if r["path"].endswith("/begin"):
            wf = r["body"]["workflow"]
            for k, v in mutations.items():
                if k == "params":
                    wf["params"] = v
                else:
                    wf[k] = v
    return reqs


def _params_of(plat, wid):
    con = sqlite3.connect(str(plat.index))
    try:
        (raw,) = con.execute("SELECT params_json FROM runs WHERE id = ?", (wid,)).fetchone()
    finally:
        con.close()
    return json.loads(raw) if raw else {}


def test_tc040_config_command_line_env_and_secret_params_are_not_stored(plat, token):
    # TC-040
    canaries = ["CFG_CANARY_9f3", "CMD_CANARY_5d1", "ENV_CANARY_2b7", "TOK_CANARY_a1", "PWD_CANARY_a2", "AWS_CANARY_a3"]
    reqs = _begin_with(
        load_scenario("ok_run")["requests"],
        configText="process.ext.note = 'CFG_CANARY_9f3'",
        commandLine="nextflow run x.nf --api_key CMD_CANARY_5d1",
        env={"MY_ENV": "ENV_CANARY_2b7"},
        params={"api_token": "TOK_CANARY_a1", "my_password": "PWD_CANARY_a2",
                "aws_secret_key": "AWS_CANARY_a3", "outdir": "results", "genome": "GRCh38"},
    )
    for r in reqs:
        for t in r["body"].get("tasks", []):
            t["env"] = "X=ENV_CANARY_2b7"
    wid, resp = plat.replay(reqs, token)
    assert all(x.status_code < 300 for x in resp)
    blob = db_bytes(plat.index, plat.tokens)
    for c in canaries:
        assert c.encode() not in blob, c
    params = _params_of(plat, wid)
    for name in ("api_token", "my_password", "aws_secret_key"):
        assert name in params and params[name] is None
    assert params["outdir"] == "results" and params["genome"] == "GRCh38"


def test_tc042_secret_like_names_are_judged_by_name_at_every_level(plat, token):
    # TC-042
    reqs = _begin_with(
        load_scenario("ok_run")["requests"],
        params={"TOKEN": "N1_CANARY", "secretName": "N2_CANARY", "ssh_key_path": "N3_CANARY",
                "Password": "N4_CANARY", "db": {"password": "N5_CANARY", "host": "dbhost"},
                "list": [{"api_key": "N6_CANARY", "n": 3}], "outdir": "out_dir_value"},
    )
    wid, resp = plat.replay(reqs, token)
    assert all(x.status_code < 300 for x in resp)
    assert b"_CANARY" not in db_bytes(plat.index, plat.tokens)
    p = _params_of(plat, wid)
    assert p["outdir"] == "out_dir_value"
    for name in ("TOKEN", "secretName", "ssh_key_path", "Password"):
        assert p[name] is None
    assert p["db"]["password"] is None and p["db"]["host"] == "dbhost"
    assert p["list"][0]["api_key"] is None and p["list"][0]["n"] == 3


def test_a_secret_looking_value_with_an_innocent_name_is_kept(plat, token):
    # Params are judged by name only (plan Revision 2): the value's shape is not looked at.
    reqs = _begin_with(load_scenario("ok_run")["requests"], params={"outdir": "AKIAFAKEVALUE0000"})
    wid, _ = plat.replay(reqs, token)
    assert _params_of(plat, wid)["outdir"] == "AKIAFAKEVALUE0000"
