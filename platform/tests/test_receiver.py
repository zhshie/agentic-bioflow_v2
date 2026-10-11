# Nothing existing: tests of this folder's own receiver; no off-the-shelf test double speaks the five Nextflow trace requests.
"""Receiver tests: replayed recordings, auth and ownership, bad input (feature 008)."""
import copy
import hashlib
import json

import pytest

from abf_platform import status
from helpers import (H, Platform, basic_header, db_bytes, db_counts, db_rows, load_scenario,
                     variant)

NOW = 1_800_000_000.0


def _view(plat, wid, at=None):
    return status.get_run(plat.index, wid, at if at is not None else plat.clock())


def test_tc007_replay_all_five_kinds_with_workspace_id_and_extra_fields(tmp_path):
    # TC-007: the five recorded kinds are accepted with ?workspaceId=, and unknown fields neither fail nor get stored.
    sc = load_scenario("heartbeat_run")
    kinds = [r["path"].rstrip("/").split("/")[-1] for r in sc["requests"]]
    assert {"create", "begin", "progress", "heartbeat", "complete"} <= set(kinds)

    plain = Platform(tmp_path / "a")
    t1 = plain.new_token()
    wid1, resp1 = plain.replay(sc["requests"], t1)
    assert all(r.status_code < 300 for r in resp1), [r.status_code for r in resp1]

    ws = Platform(tmp_path / "b")
    t2 = ws.new_token()
    wid2, resp2 = ws.replay(sc["requests"], t2, query="?workspaceId=12345")
    assert all(200 <= r.status_code < 300 for r in resp2)
    assert wid1 == wid2
    assert _view(plain, wid1) == _view(ws, wid2)

    canary = "UNKNOWN_FIELD_VALUE_zq81"
    extra = copy.deepcopy(sc["requests"])
    for req in extra:
        body = req["body"]
        body["zz_unknown_field"] = canary
        if "workflow" in body:
            body["workflow"]["zz_unknown_inner"] = canary
        for t in body.get("tasks", []):
            t["zz_unknown_task_field"] = canary
        if isinstance(body.get("progress"), dict):
            body["progress"]["zz_unknown_progress"] = canary
    ex = Platform(tmp_path / "c")
    t3 = ex.new_token()
    wid3, resp3 = ex.replay(extra, t3, query="?workspaceId=12345")
    assert all(200 <= r.status_code < 300 for r in resp3)
    assert _view(ex, wid3) == _view(plain, wid1)
    assert canary.encode() not in db_bytes(ex.index, ex.tokens)


def test_tc008_user_info_is_minimal_and_holds_no_token(plat, token):
    # TC-008
    r = plat.send("GET", "/user-info", token=token)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("user"), dict)
    assert token not in r.text


def test_tc009_create_returns_deterministic_workflow_id(plat, token):
    # TC-009
    sc = load_scenario("ok_run")
    create = sc["requests"][0]["body"]
    r = plat.send("POST", sc["requests"][0]["path"], create, token=token)
    assert r.status_code < 300
    wid = r.json()["workflowId"]
    want = hashlib.sha256((create["sessionId"] + "/" + create["runName"]).encode()).hexdigest()[:16]
    assert wid and wid == want
    begin = sc["requests"][1]
    r2 = plat.send("PUT", begin["path"].replace("{id}", wid), begin["body"], token=token)
    assert r2.status_code < 300
    assert _view(plat, wid)["name"] == create["runName"]


def test_tc010_bad_input_gets_4xx_not_500(plat, token):
    # TC-010
    sc = load_scenario("ok_run")
    wid, _ = plat.replay(sc["requests"], token, stop_before="progress")
    before = plat.counts()
    assert before["runs"] == 1
    bad = [
        ("POST", "/trace/create", b"{not json"),
        ("PUT", "/trace/%s/begin" % wid, b"{not json"),
        ("PUT", "/trace/%s/progress" % wid, b"[1, 2"),
        ("POST", "/trace/create", b""),
        ("PUT", "/trace/%s/complete" % wid, b""),
        ("POST", "/trace/create", b"{}"),
    ]
    for method, path, raw in bad:
        r = plat.send(method, path, token=token, raw=raw)
        assert 400 <= r.status_code < 500, (path, r.status_code)
        assert r.text
    r = plat.send("PUT", "/trace/ffffffffffffffff/progress", {"tasks": [], "progress": {}}, token=token)
    assert 400 <= r.status_code < 500
    assert plat.counts() == before
    # a normal request is still accepted afterwards
    for req in sc["requests"][2:]:
        r = plat.send(req["method"], req["path"].replace("{id}", wid), req["body"], token=token)
        assert r.status_code < 300


def test_tc011_no_authorization_means_401_and_zero_records(plat):
    # TC-011
    before = plat.counts()
    r = plat.send("POST", "/trace/create", load_scenario("ok_run")["requests"][0]["body"])
    assert r.status_code == 401
    assert plat.counts() == before == {"runs": 0, "processes": 0, "failed_tasks": 0}


def test_tc012_wrong_token_is_refused_on_every_endpoint(plat, token):
    # TC-012
    sc = load_scenario("heartbeat_run")
    wid = "0123456789abcdef"
    wrong = "abf_" + "x" * 43
    before = plat.counts()
    for req in sc["requests"]:
        if req["path"].rstrip("/").split("/")[-1] == "progress":
            pass
        r = plat.send(req["method"], req["path"].replace("{id}", wid), req["body"], token=wrong)
        assert r.status_code == 401, req["path"]
    assert plat.send("GET", "/user-info", token=wrong).status_code == 401
    # a Bearer header with the wrong token and a malformed header are refused too
    assert plat.send("GET", "/user-info", token=wrong, scheme="bearer").status_code == 401
    assert plat.send("GET", "/user-info", headers={"Authorization": "Basic !!!"}).status_code == 401
    assert plat.counts() == before == {"runs": 0, "processes": 0, "failed_tasks": 0}


def test_tc014_bearer_and_basic_both_create_a_run(plat, token):
    # TC-014: Basic is what Nextflow 26.04.7 sends: user '@token', password the token.
    assert basic_header(token) == "Basic " + __import__("base64").b64encode(("@token:" + token).encode()).decode()
    one = copy.deepcopy(load_scenario("ok_run")["requests"][0])
    two = copy.deepcopy(load_scenario("fail_run")["requests"][0])
    r1 = plat.send("POST", one["path"], one["body"], token=token, scheme="basic")
    r2 = plat.send("POST", two["path"], two["body"], token=token, scheme="bearer")
    assert r1.status_code < 300 and r2.status_code < 300
    # the first create is only a create; begin makes the run visible with its start time
    assert plat.counts()["runs"] == 2


def test_tc015_a_token_cannot_write_to_another_tokens_run(plat, token):
    # TC-015
    other = plat.new_token()
    sc = load_scenario("heartbeat_run")
    wid, _ = plat.replay(sc["requests"], token, stop_before="complete")
    snapshot = db_rows(plat.index)
    for req in sc["requests"]:
        kind = req["path"].rstrip("/").split("/")[-1]
        if kind in ("progress", "heartbeat", "complete", "begin"):
            r = plat.send(req["method"], req["path"].replace("{id}", wid), req["body"], token=other)
            assert r.status_code in (401, 403), (kind, r.status_code)
    # B cannot take over A's run by creating the same session and run name either
    c = plat.send("POST", sc["requests"][0]["path"], sc["requests"][0]["body"], token=other)
    assert c.status_code in (401, 403)
    assert db_rows(plat.index) == snapshot
    # B's own create works
    mine = variant("ok_run", "other_run", "00000000-0000-0000-0000-00000000b001", NOW)
    wid_b, resp = plat.replay(mine, other)
    assert all(x.status_code < 300 for x in resp)
    assert wid_b != wid


def test_tc016_token_is_stored_only_as_a_hash_and_survives_restart(tmp_path):
    # TC-016
    a = Platform(tmp_path / "p")
    tok = a.new_token()
    r = a.send("POST", "/trace/create", load_scenario("ok_run")["requests"][0]["body"], token=tok)
    assert r.status_code < 300
    blob = db_bytes(a.index, a.tokens)
    assert tok.encode() not in blob
    assert hashlib.sha256(tok.encode()).hexdigest().encode() in db_bytes(a.tokens)
    # a restart is a new app on the same files
    from abf_platform import receiver
    from starlette.testclient import TestClient
    again = TestClient(receiver.create_app(a.index, a.tokens))
    r2 = again.post("/trace/create", json=load_scenario("fail_run")["requests"][0]["body"],
                    headers={"Authorization": basic_header(tok)})
    assert r2.status_code < 300


def test_tc043_no_response_leaks_the_token(plat, token):
    # TC-043 (receiver side): create response, user-info, and every GET path.
    sc = load_scenario("fail_run")
    wid, resp = plat.replay(sc["requests"], token)
    texts = [r.text for r in resp]
    texts.append(plat.send("GET", "/user-info", token=token).text)
    for p in ("/", "/trace/%s" % wid, "/runs", "/user-info"):
        texts.append(plat.send("GET", p, token=token).text)
    hashed = hashlib.sha256(token.encode()).hexdigest()
    for t in texts:
        low = t.lower()
        assert token not in t and hashed not in t and "authorization" not in low


def test_tc060_no_write_paths_exist(plat, token):
    # TC-060: nothing launches, cancels, deletes or writes into work/.
    wid, _ = plat.replay(load_scenario("ok_run")["requests"], token)
    attempts = [("POST", "/launch"), ("DELETE", "/runs/" + wid), ("POST", "/runs/%s/cancel" % wid),
                ("DELETE", "/trace/" + wid), ("PUT", "/work/clean"), ("POST", "/work"),
                ("POST", "/workflow/launch"), ("DELETE", "/workflow/" + wid)]
    for method, path in attempts:
        r = plat.send(method, path, {"x": 1}, token=token)
        assert r.status_code in (404, 405), (method, path, r.status_code)
    assert plat.counts()["runs"] == 1


def test_tc062_no_web_pages_no_login_and_no_user_or_role_columns(plat, token):
    # TC-062
    for p in ("/", "/login", "/oauth/token", "/oauth/access_token", "/index.html"):
        assert plat.send("GET", p, token=token).status_code == 404, p
        assert plat.send("GET", p).status_code in (401, 404), p
    import sqlite3
    plat.replay(load_scenario("ok_run")["requests"], token)
    con = sqlite3.connect(str(plat.index))
    cols = []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        cols += [c[1].lower() for c in con.execute("PRAGMA table_info(%s)" % t)]
        cols.append(t.lower())
    con.close()
    for word in ("user", "role", "org", "team", "member", "login", "password", "email"):
        assert not [c for c in cols if word in c], (word, cols)


def test_progress_updates_counts_and_per_process_numbers(plat, token):
    # Backs TC-002/TC-021 without a real Nextflow: the recorded 'ok' run gives 7 tasks in 3 processes.
    sc = load_scenario("ok_run")
    wid, _ = plat.replay(sc["requests"], token)
    v = _view(plat, wid)
    assert v["status"] == "succeeded"
    assert v["tasks"]["total"] == v["tasks"]["succeeded"] == 7
    assert v["tasks"]["cached"] == 0 and v["tasks"]["failed"] == 0
    assert {p["name"]: p["total"] for p in v["processes"]} == {"GREET": 3, "UPPER": 3, "SUMMARY": 1}
    resumed = load_scenario("ok_resume")
    wid2, _ = plat.replay(resumed["requests"], token)
    v2 = _view(plat, wid2)
    assert v2["tasks"]["cached"] == 7 and v2["tasks"]["succeeded"] == 0 and v2["tasks"]["total"] == 7
    assert wid2 != wid


def test_failed_task_is_recorded_with_exit_code_and_stderr_text(plat, token):
    # Backs TC-003 on the recorded failing run.
    wid, _ = plat.replay(load_scenario("fail_run")["requests"], token)
    v = _view(plat, wid)
    assert v["status"] == "failed"
    assert [(f["name"], f["exit_code"]) for f in v["failed_tasks"]] == [("BAD", 1)]
    assert "FIXTURE_BOOM_7" in v["failed_tasks"][0]["error_message"]
    assert v["tasks"]["succeeded"] == 2 and v["tasks"]["failed"] == 1 and v["tasks"]["total"] == 3
