# Nothing existing: tests of the status rule in this folder (running, lost, succeeded, failed); a pure function of the row and the clock.
"""Status rule tests: lost after 3 heartbeats, no background work (feature 008)."""
from abf_platform import status
from helpers import H, all_files_digest, load_scenario


def _until_first_progress(plat, token, name="heartbeat_run"):
    sc = load_scenario(name)
    wid, _ = plat.replay(sc["requests"], token, stop_before="heartbeat")
    return sc, wid


def test_tc005_lost_after_three_heartbeats_and_never_succeeded(plat, token):
    # TC-005: create, begin and one progress; no complete. T is the time of the last message.
    t0 = plat.clock()
    sc, wid = _until_first_progress(plat, token)
    digest = all_files_digest(plat.index, plat.tokens)
    seen = []
    for dt, want in ((10, "running"), (3 * H - 1, "running"), (3 * H + 1, "lost"), (24 * 3600, "lost")):
        v = status.get_run(plat.index, wid, t0 + dt)
        seen.append(v["status"])
        assert v["status"] == want, (dt, v["status"])
        assert v["status"] != "succeeded"
        listed = status.list_runs(plat.index, t0 + dt)
        assert [x["status"] for x in listed] == [want]
    assert all_files_digest(plat.index, plat.tokens) == digest, "a query wrote to the database files"
    assert "succeeded" not in seen


def test_tc006_complete_after_lost_gives_the_final_status(tmp_path):
    # TC-006: a late complete turns lost into succeeded or failed.
    from helpers import Clock, Platform
    for scenario, final in (("ok_run", "succeeded"), ("fail_run", "failed")):
        clock = Clock()
        plat = Platform(tmp_path / scenario, clock=clock)
        token = plat.new_token()
        sc = load_scenario(scenario)
        wid, _ = plat.replay(sc["requests"], token, stop_before="complete")
        clock.t += 3 * H + 30
        assert status.get_run(plat.index, wid, clock())["status"] == "lost"
        complete = [r for r in sc["requests"] if r["path"].endswith("/complete")][0]
        r = plat.send("PUT", complete["path"].replace("{id}", wid), complete["body"], token=token)
        assert r.status_code < 300
        assert status.get_run(plat.index, wid, clock())["status"] == final
        assert status.get_run(plat.index, wid, clock() + 5 * 3600)["status"] == final


def test_a_heartbeat_keeps_the_run_running(plat, token):
    # FR-006: any message resets the silence timer, including a heartbeat.
    t0 = plat.clock()
    sc, wid = _until_first_progress(plat, token)
    plat.clock.t = t0 + 2 * H
    hb = [r for r in sc["requests"] if r["path"].endswith("/heartbeat")][0]
    assert plat.send("PUT", hb["path"].replace("{id}", wid), hb["body"], token=token).status_code < 300
    assert status.get_run(plat.index, wid, t0 + 2 * H + 3 * H - 1)["status"] == "running"
    assert status.get_run(plat.index, wid, t0 + 2 * H + 3 * H + 1)["status"] == "lost"


def test_list_runs_on_a_missing_index_is_empty_and_creates_nothing(tmp_path):
    # Reading must never create the database.
    p = tmp_path / "nothing.db"
    assert status.list_runs(p, 1.0) == []
    assert status.get_run(p, "0123456789abcdef", 1.0) is None
    assert not p.exists()
