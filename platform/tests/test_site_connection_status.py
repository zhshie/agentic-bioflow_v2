# Nothing existing: tests of the site-connection state in list_agents / list_compute_envs, the agent name in the connection errors, and the get_run SU reasons; the rules are this task's.
"""mcp-site-connection-status, platform side. TC numbers are in the comments, see the task's test case list."""
import asyncio
import json
import sqlite3
import time

from helpers import Clock, Platform
from test_launch_platform import setup, sql
from test_station_platform import agent_token, bearer, make_ce, state_db

H = 3600000
DOWN = ("No open connection to the site. Log in once in a WSL terminal first (請先在 WSL 終端機登入站台): "
        "ssh -o ControlMaster=yes -o ControlPath=/tmp/cm-nano4 nano4 true")
WSL_SENTENCE = 'Run it in the WSL terminal of the machine running agent "%s" (請在執行 agent「%s」那台機器的 WSL 終端機執行).'


def actions():
    from abf_platform import actions as a
    return a


def say_hello(plat, name, link=None, at="2026-11-07T10:00:00Z", **extra):
    tok = agent_token(plat, name)
    facts = dict({"reach": "ssh"}, **extra)
    if link is not None:
        facts["site_link"] = link
        facts["site_link_at"] = at
    r = plat.client.post("/agent/hello", json={"name": name, "version": "0.1.0", "facts": facts}, headers=bearer(tok))
    assert r.status_code == 200
    return tok


def by_name(items):
    return {x["name"]: x for x in items}


# ---- US1 -------------------------------------------------------------------------------------------------------

def test_clean_facts_site_link_only_three_values():
    # TC-001, TC-002
    from abf_platform import common
    for word in ("open", "closed", "unknown"):
        assert common.clean_facts({"site_link": word})["site_link"] == word
    for bad in ("maybe", 123, "", None, "OPEN", ["open"]):
        assert common.clean_facts({"site_link": bad})["site_link"] is None
    assert common.clean_facts({"site_link_at": "2026-11-07T10:00:00Z"})["site_link_at"] == "2026-11-07T10:00:00Z"


def test_list_agents_reports_site_link_unknown_for_old_agent(tmp_path):
    # TC-005
    plat = Platform(tmp_path / "p", clock=Clock())
    say_hello(plat, "old")
    got = by_name(actions().list_agents(state_db(plat))["agents"])
    assert got["old"]["site_link"] == "unknown"


def test_list_agents_reports_closed_and_open(tmp_path):
    # TC-003, TC-004, TC-007
    plat = Platform(tmp_path / "p", clock=Clock())
    say_hello(plat, "desktop", "closed", "2026-11-07T10:00:01Z")
    say_hello(plat, "desktop-gcb", "open", "2026-11-07T10:00:02Z")
    got = by_name(actions().list_agents(state_db(plat))["agents"])
    assert got["desktop"]["site_link"] == "closed" and got["desktop"]["site_link_at"] == "2026-11-07T10:00:01Z"
    assert got["desktop-gcb"]["site_link"] == "open" and got["desktop-gcb"]["site_link_at"] == "2026-11-07T10:00:02Z"


def test_stale_site_link_becomes_unknown(tmp_path):
    # TC-006
    plat = Platform(tmp_path / "p", clock=Clock())
    say_hello(plat, "desktop", "open")
    con = sqlite3.connect(str(state_db(plat)))
    with con:
        con.execute("UPDATE agents SET last_seen_at = ? WHERE name = 'desktop'", (time.time() - 100000,))
    con.close()
    got = by_name(actions().list_agents(state_db(plat))["agents"])
    assert got["desktop"]["status"] == "offline" and got["desktop"]["site_link"] == "unknown"


def test_list_compute_envs_attaches_site_connection_by_ce_agent(tmp_path):
    # TC-008, TC-009, TC-010
    plat = Platform(tmp_path / "p", clock=Clock())
    say_hello(plat, "desktop", "closed", "2026-11-07T10:00:01Z")
    say_hello(plat, "desktop-gcb", "open", "2026-11-07T10:00:02Z")
    make_ce(plat, name="nano4", agent="desktop")
    make_ce(plat, name="gcb-ce", agent="desktop-gcb")
    make_ce(plat, name="orphan", agent="nobody")
    got = by_name(actions().list_compute_envs(state_db(plat))["compute_envs"])
    assert got["nano4"]["site_connection"] == {"state": "closed", "as_of": "2026-11-07T10:00:01Z", "agent": "desktop"}
    assert got["gcb-ce"]["site_connection"]["state"] == "open" and got["gcb-ce"]["site_connection"]["agent"] == "desktop-gcb"
    assert got["orphan"]["site_connection"]["state"] == "unknown"


def test_listing_connection_is_read_only(tmp_path):
    # TC-011, TC-012
    plat = Platform(tmp_path / "p", clock=Clock())
    say_hello(plat, "desktop", "closed")
    make_ce(plat, name="nano4", agent="desktop")
    before = (sql(plat, "SELECT COUNT(*) FROM jobs"), sql(plat, "SELECT name, last_seen_at FROM agents"))
    actions().list_agents(state_db(plat))
    actions().list_compute_envs(state_db(plat))
    after = (sql(plat, "SELECT COUNT(*) FROM jobs"), sql(plat, "SELECT name, last_seen_at FROM agents"))
    assert before == after and before[0] == [(0,)]


# ---- US2 -------------------------------------------------------------------------------------------------------

def _outputs_world(tmp_path, agent="desktop", ce_agent="desktop", message=DOWN, job_agent=False):
    job_agent = agent if job_agent is False else job_agent      # the agent that ran the listing job (the CE's agent when it was queued)
    from abf_platform import compute_envs, store
    db, pdb = tmp_path / "index.db", tmp_path / "platform.db"
    con = store.connect_index(db)
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at, n_succeeded) "
                    "VALUES ('id-r', 's', 'r', 'live', 'succeeded', 1790000000, 1790000100, 3, 1)")
    con.close()
    store.connect_state(pdb).close()
    rec = {"name": "nano4", "platform": "slurm-platform", "config": {"workDir": "/data/work", "headQueue": "hq"}}
    if ce_agent:
        rec["agent"] = ce_agent
    compute_envs.create(pdb, rec)
    con = store.connect_state(pdb)
    with con:
        con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES ('r', '/f', 'nano4', ?, 1, 1)", (agent or "",))
        con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, result_json, created_at, deadline_at, finished_at) "
                    "VALUES (?, 'nano4', 'list_site_files', ?, 'done', ?, ?, ?, ?)",
                    (job_agent or "", json.dumps({"path": "/f/results"}), json.dumps({"ok": False, "message": message}),
                     time.time(), time.time() + 60, time.time()))
    con.close()
    return db, pdb


def _outputs(db, pdb):
    return actions().run_outputs(db, pdb, "id-r", enqueue=False)


def test_run_outputs_error_names_agent(tmp_path):
    # TC-031, TC-032, TC-035
    got = _outputs(*_outputs_world(tmp_path))
    assert got["state"] == "error"
    assert "desktop" in got["reason"] and "WSL" in got["reason"]
    assert got["reason"].endswith(WSL_SENTENCE % ("desktop", "desktop"))
    assert got["reason"].startswith("No open connection to the site. Log in once in a WSL terminal first")
    assert "ControlPath=/tmp/cm-nano4" in got["reason"]


def test_run_outputs_names_the_agent_of_the_run_not_another(tmp_path):
    # TC-034
    got = _outputs(*_outputs_world(tmp_path, agent="desktop-gcb", ce_agent="desktop"))
    assert 'agent "desktop-gcb"' in got["reason"] and 'agent "desktop"' not in got["reason"]


def test_run_outputs_names_the_agent_that_ran_the_job_after_ce_moved(tmp_path):
    # TC-034 (fix round): launched by desktop-gcb, the CE now belongs to desktop and the listing ran on desktop: the person must be
    # sent to desktop, the machine that reported "No open connection", not to the launch agent
    got = _outputs(*_outputs_world(tmp_path, agent="desktop-gcb", ce_agent="desktop", job_agent="desktop"))
    assert got["reason"].endswith(WSL_SENTENCE % ("desktop", "desktop")) and "desktop-gcb" not in got["reason"]


def _fake_listing(monkeypatch):
    from abf_platform import jobs

    async def fake_wait(*a, **k):
        return {"state": "done", "ok": False, "message": DOWN, "result": {"ok": False, "message": DOWN}}
    monkeypatch.setattr(jobs, "wait_for_result", fake_wait)
    monkeypatch.setattr(jobs, "enqueue_listing", lambda *a, **k: 1)


def _set_ce_agent(plat, value):
    con = sqlite3.connect(str(state_db(plat)))
    with con:
        con.execute("UPDATE compute_envs SET agent = ? WHERE name = 'lab-a'", (value,))
    con.close()


def test_list_site_files_failure_names_agent(tmp_path, monkeypatch):
    # TC-033
    plat, _, _ = setup(tmp_path)
    _fake_listing(monkeypatch)
    got = asyncio.run(actions().list_site_files(state_db(plat), "lab-a", "/data/w1"))
    assert got["ok"] is False
    assert got["message"].startswith("No open connection to the site") and got["message"].endswith(WSL_SENTENCE % ("a1", "a1"))


def test_agent_name_with_odd_chars_not_spliced(tmp_path, monkeypatch):
    # TC-036
    odd = 'my "box"'
    got = _outputs(*_outputs_world(tmp_path, agent=odd, ce_agent=None))
    assert got["reason"] == DOWN
    plat, _, _ = setup(tmp_path / "x")
    _set_ce_agent(plat, odd)
    _fake_listing(monkeypatch)
    ans = asyncio.run(actions().list_site_files(state_db(plat), "lab-a", "/data/w1"))
    assert ans["message"] == DOWN


def test_no_agent_field_leaves_the_message_unchanged(tmp_path, monkeypatch):
    # TC-037, TC-038
    got = _outputs(*_outputs_world(tmp_path, agent=None, ce_agent=None))
    assert got["reason"] == DOWN
    plat, _, _ = setup(tmp_path / "y")
    _set_ce_agent(plat, None)
    _fake_listing(monkeypatch)
    ans = asyncio.run(actions().list_site_files(state_db(plat), "lab-a", "/data/w1"))
    assert ans["message"] == DOWN


def test_other_errors_get_no_wsl_sentence(tmp_path):
    # TC-039
    msg = "路徑被拒 (the path is refused): /data/x"
    got = _outputs(*_outputs_world(tmp_path, message=msg))
    assert got["state"] == "error" and got["reason"] == msg and "WSL" not in got["reason"]


# ---- US3 -------------------------------------------------------------------------------------------------------

def _su_world(tmp_path, usage, su_site="nano4", ce=True):
    from abf_platform import compute_envs, store
    db, pdb = tmp_path / "index.db", tmp_path / "platform.db"
    con = store.connect_index(db)
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at, n_succeeded) "
                    "VALUES ('id-r', 's', 'r', 'live', 'succeeded', 1790000000, 1790000100, 3, ?)", (len(usage),))
        for i, (part, cpus, ms) in enumerate(usage):
            con.execute("INSERT INTO task_usage (run_id, task_key, name, status, cpus, realtime_ms, queue) VALUES ('id-r', ?, ?, 'COMPLETED', ?, ?, ?)",
                        ("%d:1" % i, "T%d" % i, cpus, ms, part))
    con.close()
    store.connect_state(pdb).close()
    if ce:
        cfg = {"workDir": "/data/work", "headQueue": "hq"}
        if su_site:
            cfg["suSite"] = su_site
        compute_envs.create(pdb, {"name": "nano4", "platform": "slurm-platform", "config": cfg})
    con = store.connect_state(pdb)
    with con:
        con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES ('r', '/f', ?, 'a1', 1, 1)",
                    ("nano4" if ce else "gone",))
    con.close()
    return db, pdb


def _get(db, pdb):
    a = actions()
    return a.get_run(db, "id-r", caller=a.Caller(1, "u1", "lab"), platform_path=pdb)["su"]


def test_unknown_reasons_aggregated_by_partition(tmp_path):
    # TC-042, TC-043, TC-045
    parts = ["zz1", "zz2", "zz3", "zz4", "zz5"]
    usage = [(parts[i % 5], 1, H) for i in range(125)]
    su = _get(*_su_world(tmp_path, usage))
    assert su["su"] is None and len(su["unknown_reasons"]) == 5
    for p in parts:
        assert "分區 %s 沒有 SU 係數，共 25 個 task（no SU factor for partition %s: 25 tasks）" % (p, p) in su["unknown_reasons"]
    assert su["site"] == "nano4"


def test_unknown_reasons_sorted_one_line_per_partition(tmp_path):
    # TC-044, TC-046
    su = _get(*_su_world(tmp_path, [("zeta", 1, H), ("alpha", 1, H), ("mid", 1, H), ("alpha", 1, H)]))
    assert [r.split()[1] for r in su["unknown_reasons"]] == ["alpha", "mid", "zeta"]
    one = _get(*_su_world(tmp_path / "o", [("alpha", 1, H)] * 3))
    assert len(one["unknown_reasons"]) == 1


def test_su_site_unset_ce_is_not_taiwania3(tmp_path):
    # TC-047, TC-048, TC-049
    su = _get(*_su_world(tmp_path, [("ngs62g", 1, H)], su_site=None))
    assert su["site"] is None and su["su"] is None
    assert su["unknown_reasons"] == ["計算環境未設定 suSite，無法判定站台（compute environment has no suSite）"]


def test_su_site_from_ce_suSite_nano4(tmp_path):
    # TC-050
    su = _get(*_su_world(tmp_path, [("ngs62g", 2, H)]))
    assert su["site"] == "nano4" and isinstance(su["su"], float) and su["su"] > 0 and su["unknown_reasons"] == []


def test_unknown_partition_still_null_not_guessed(tmp_path):
    # TC-051, TC-052
    assert _get(*_su_world(tmp_path, [("nowhere", 1, H)]))["su"] is None
    assert _get(*_su_world(tmp_path / "m", [("ngs62g", 1, H), ("nowhere", 1, H)]))["su"] is None


def test_ce_gone_keeps_default_site(tmp_path):
    # TC-053
    from abf_platform import su as su_mod
    got = _get(*_su_world(tmp_path, [("ngs62g", 1, H)], ce=False))
    assert got["site"] == su_mod.load_rates()["default_site"]


def test_estimate_su_and_usage_say_no_suSite_like_get_run(tmp_path):
    # TC-047 (fix round): one answer about the site of a run: a CE without suSite is said once, never priced at default_site
    from abf_platform import su as su_mod
    db, pdb = _su_world(tmp_path, [("ngs62g", 1, H)], su_site=None)
    a = actions()
    want = [su_mod.NO_SU_SITE]
    got = a.estimate_su(db, "r", platform_path=pdb)
    assert got["su"] is None and got["unknown_reasons"] == want
    assert a.run_usage(db, "id-r", caller=a.Caller(1, "u1", "lab"), platform_path=pdb)["unknown_reasons"] == want


def test_run_page_never_cuts_the_agent_name(tmp_path):
    # TC-034 (fix round): the web page keeps 300 characters of a reason; a cut must not fall inside the agent sentence and leave a partial name
    from abf_platform import web_board
    long_ssh = "ssh -o ControlMaster=auto -o ControlPath=/home/u/.ssh/cm-%C -o ControlPersist=8h -o ServerAliveInterval=60 site_user_longname@ln01.nano4.nchc.org.tw true"
    for opener in ("", "wsl.exe -e "):
        base = ("No open connection to the site. Log in once in a WSL terminal first (請先在 WSL 終端機登入站台): " + opener + long_ssh)
        new = actions()._with_agent(base, "desktop-gcb")
        for lang in ("zh", "en"):
            shown = web_board.plain_reason(new, lang)
            assert 'agent "desktop"' not in shown and not shown.rstrip("。.").endswith('agent "desktop')
            if "agent" in shown:
                assert 'agent "desktop-gcb"' in shown or 'agent「desktop-gcb」' in shown, shown
            if lang == "zh":
                assert 'agent "desktop-gcb"' in shown and "agent「desktop-gcb」" in shown, shown
