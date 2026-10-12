# Nothing existing: tests of this folder's own receiver against what Nextflow 25.10.4 with nf-tower 1.17.5 (the cluster's version) really sent; no off-the-shelf test double speaks the five Nextflow trace requests.
"""The receiver takes what nf-tower 1.17.5 sends (feature 007b, FR-007, TC-028 and TC-029).

The recordings in platform/tests/fixtures/payloads/nf2510_*.json were made by fixtures/record_payloads.py from real runs of
Nextflow 25.10.4 (the second pair pinned in pins.env). Their header carries `expected`, what each run's own trace.txt says.
The 008 recordings of nf-tower 1.28.3 are replayed by test_receiver.py and are not touched.
"""
import copy
import json

import pytest

from abf_platform import common, status
from helpers import Platform, db_bytes, load_scenario

SCENARIOS = ["nf2510_ok", "nf2510_resume", "nf2510_fail", "nf2510_retry"]


def _view(plat, wid):
    return status.get_run(plat.index, wid, plat.clock())


def _final_failures(expected):
    """The failed rows of a trace, minus the tasks that were retried and then completed (they are not failures)."""
    return sorted(f["name"] for f in expected["failed_tasks"] if f["name"] != "FLAKY (1)")


def _check_against_trace(view, expected, success):
    tasks = expected["tasks"]
    assert view["status"] == ("succeeded" if success else "failed")
    assert {k: view["tasks"][k] for k in ("total", "succeeded", "cached", "failed", "aborted")} == tasks
    got = {p["name"]: {k: p[k] for k in ("total", "succeeded", "cached", "failed", "aborted")} for p in view["processes"]}
    assert got == expected["processes"]
    assert sorted(f["name"] for f in view["failed_tasks"]) == _final_failures(expected)


def test_tc028_the_fixtures_are_real_recordings_of_the_pinned_pair():
    # TC-028: header of every recording names both versions; the 1.28.3 ones are still there
    for name in SCENARIOS + ["nf2510_long_timing"]:
        h = load_scenario(name)["_header"]
        assert h["nextflow"] == "25.10.4" and h["nf-tower"] == "1.17.5", name
        assert "sanitized" in h
    assert load_scenario("ok_run")["_header"]["nf-tower"] == "1.28.3"
    kinds = {r["path"].rstrip("/").split("/")[-1] for n in SCENARIOS for r in load_scenario(n)["requests"]}
    assert {"create", "begin", "progress", "complete"} <= kinds


@pytest.mark.parametrize("name,success", [("nf2510_ok", True), ("nf2510_resume", True), ("nf2510_fail", False),
                                          ("nf2510_retry", False)])
def test_tc028_every_request_of_1_17_5_is_accepted_and_the_numbers_are_the_traces(tmp_path, name, success):
    # TC-028: create, begin, progress and complete are accepted; counts per process and the failed tasks match the trace
    sc = load_scenario(name)
    plat = Platform(tmp_path / "p")
    token = plat.new_token()
    wid, resp = plat.replay(sc["requests"], token, query="?workspaceId=1")
    assert all(200 <= r.status_code < 300 for r in resp), [r.status_code for r in resp]
    _check_against_trace(_view(plat, wid), sc["_header"]["expected"], success)


def test_tc028_a_retried_task_is_not_left_in_the_failed_list_and_is_not_counted_twice(tmp_path):
    # TC-028, TC-027 (the receiver half): FLAKY (1) failed on attempt 1 (task id 1) and completed on attempt 2 (task id 5)
    sc = load_scenario("nf2510_retry")
    plat = Platform(tmp_path / "p")
    wid, _ = plat.replay(sc["requests"], plat.new_token())
    v = _view(plat, wid)
    assert [f["name"] for f in v["failed_tasks"]] == ["BAD"], v["failed_tasks"]
    assert "FIXTURE_BOOM_7" in v["failed_tasks"][0]["error_message"]
    flaky = [p for p in v["processes"] if p["name"] == "FLAKY"][0]
    assert (flaky["succeeded"], flaky["failed"]) == (1, 1) and flaky["total"] == 2


def test_tc028_without_an_attempt_field_a_retried_task_does_not_overwrite_or_survive(tmp_path):
    # TC-028: the same recording with every `attempt` removed; and a retry that reuses the task id
    sc = copy.deepcopy(load_scenario("nf2510_retry"))
    for req in sc["requests"]:
        for t in (req["body"].get("tasks") if isinstance(req["body"], dict) else None) or []:
            t.pop("attempt", None)
    plat = Platform(tmp_path / "a")
    wid, resp = plat.replay(sc["requests"], plat.new_token())
    assert all(r.status_code < 300 for r in resp)
    assert [f["name"] for f in _view(plat, wid)["failed_tasks"]] == ["BAD"]

    plat2 = Platform(tmp_path / "b")
    tok = plat2.new_token()
    base = load_scenario("nf2510_ok")["requests"]
    wid, _ = plat2.replay(base, tok, stop_before="progress")
    task = {"taskId": 7, "name": "STEP (1)", "process": "STEP"}
    for st, code in (("FAILED", 3), ("FAILED", 3), ("COMPLETED", 0)):
        body = {"tasks": [dict(task, status=st, exit=code)], "progress": {"failed": 0, "processes": []}}
        assert plat2.send("PUT", "/trace/%s/progress" % wid, body, token=tok).status_code < 300
        shown = [f["name"] for f in _view(plat2, wid)["failed_tasks"]]
        assert shown == (["STEP (1)"] if st == "FAILED" else []), (st, shown)


def test_tc028_unknown_fields_are_ignored_and_secret_looking_params_are_cleared(tmp_path):
    # TC-028: the 008 rules hold for 1.17.5 payloads too
    sc = copy.deepcopy(load_scenario("nf2510_ok"))
    canary = "UNKNOWN_FIELD_VALUE_k4q2"
    secret = "SECRET_PARAM_VALUE_z81x"
    for req in sc["requests"]:
        body = req["body"]
        body["zz_unknown"] = canary
        if "workflow" in body:
            body["workflow"]["zz_inner"] = canary
            if req["path"].endswith("/begin"):
                body["workflow"].setdefault("params", {})["my_api_token"] = secret
        for t in body.get("tasks", []):
            t["zz_task"] = canary
    plat = Platform(tmp_path / "p")
    wid, resp = plat.replay(sc["requests"], plat.new_token())
    assert all(r.status_code < 300 for r in resp)
    _check_against_trace(_view(plat, wid), sc["_header"]["expected"], True)
    blob = db_bytes(plat.index, plat.tokens)
    assert canary.encode() not in blob and secret.encode() not in blob


def test_tc029_the_longest_silence_of_a_four_minute_run_is_shorter_than_the_lost_rule():
    # TC-029: 1.17.5 sends a heartbeat every minute; if a measurement ever shows 180 s or more, 008's lost rule must change
    reqs = load_scenario("nf2510_long_timing")["requests"]
    times = [r["received_at"] for r in reqs]
    assert times == sorted(times) and times[-1] >= 240, "the recording must cover at least four minutes"
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert max(gaps) < common.LOST_AFTER_SECONDS, (max(gaps), common.LOST_AFTER_SECONDS)
    assert [r["kind"] for r in reqs][:2] == ["create", "begin"] and reqs[-1]["kind"] == "complete"


def test_tc029_a_run_that_talks_at_the_recorded_times_is_never_shown_as_lost(tmp_path):
    # TC-029: replay the recorded rhythm on a fake clock and ask `get_run` just before every message
    reqs = load_scenario("nf2510_long_timing")["requests"]
    plat = Platform(tmp_path / "p")
    tok = plat.new_token()
    start = plat.clock()
    ok = load_scenario("nf2510_ok")["requests"]
    wid, _ = plat.replay(ok, tok, stop_before="progress")
    for r in reqs:
        if r["kind"] in ("create", "begin", "complete"):
            continue
        plat.clock.t = start + r["received_at"] - 0.001
        assert _view(plat, wid)["status"] == "running", r
        plat.clock.t = start + r["received_at"]
        resp = plat.send("PUT", "/trace/%s/%s" % (wid, r["kind"]), {"progress": {}}, token=tok)
        assert resp.status_code < 300
    plat.clock.t = start + reqs[-1]["received_at"] + common.LOST_AFTER_SECONDS + 1
    assert _view(plat, wid)["status"] == "lost"
