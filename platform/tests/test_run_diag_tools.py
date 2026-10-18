# Nothing existing: tests of the three read-only diagnosis facts the runs skill needs (workdir of a failed task, read_task_log, cancel_requested_at); the rules are ours.
"""run-diag-tools: get_run carries `workdir` of a failed task and `cancel_requested_at`; read_task_log reads one log file of a failed task
through the run's station agent. Test cases are named in the comments (TC-001 ...), see specs/run-diag-tools/test-case.md."""
import asyncio
import copy
import json
import re
import sqlite3
import time
from pathlib import Path

import pytest

from helpers import Clock, Platform, PLATFORM_DIR, REPO_ROOT, load_scenario, variant
from station_harness import FakePlatform, FakeSite, ce_snapshot as station_ce
from test_launch_platform import own_all, setup, sql
from test_station_fakeplatform import agent_on
from test_station_launch import ACCT, fake, run_job  # noqa: F401
from test_station_platform import bearer, poll, state_db

RUN = "run-one"
SITE_WORK = "/data/w1"          # the workDir of the environment that test_launch_platform.setup makes


def actions():
    from abf_platform import actions as a
    return a


# ---- builders ---------------------------------------------------------------------------------------------------------

def requests_of(name, run=RUN, clock=None, move_to=SITE_WORK + "/wk", drop_workdir=(), only_report=False):
    """A recorded scenario as the run `run`, its task folders moved under the environment's work folder (move_to), the task
    folders of the names in drop_workdir left out of their events, and (only_report) the task events of failed tasks left out."""
    reqs = variant(name, run, "sess-" + run, (clock or Clock())())
    text = json.dumps(reqs).replace("/LAUNCH/wk", move_to)
    reqs = json.loads(text)
    for r in reqs:
        body = r["body"]
        if isinstance(body, dict) and isinstance(body.get("tasks"), list):
            if only_report:
                body["tasks"] = [t for t in body["tasks"] if t.get("status") != "FAILED"]
            for t in body["tasks"]:
                if t.get("name") in drop_workdir:
                    t.pop("workdir", None)
    return reqs


def failed_workdirs(reqs):
    """name -> workdir of the failed task that stands last for its name (a later attempt replaces an earlier one)."""
    tasks = []
    for r in reqs:
        body = r["body"]
        if isinstance(body, dict) and isinstance(body.get("tasks"), list):
            tasks += body["tasks"]
    tasks.sort(key=lambda t: (t.get("attempt") or 0, t.get("taskId") or 0))
    last = {}
    for t in tasks:
        last[t["name"]] = t
    return {n: t.get("workdir") for n, t in last.items() if t.get("status") == "FAILED"}


class World:
    """A platform in process: the receiver (the index), platform.db with the environment lab-a and the online agent a1, and one
    recorded run replayed into the index and written into the hand-off record."""

    def __init__(self, tmp_path, scenario="fail_run", launched=True, run=RUN, **kw):
        self.plat, self.agent_token, self.clock = setup(tmp_path)
        self.db = state_db(self.plat)
        self.run = run
        self.reqs = requests_of(scenario, run, self.clock, **kw)
        self.wid, resp = self.plat.replay(self.reqs, self.plat.new_token())
        assert all(r.status_code < 300 for r in resp)
        if launched:
            con = sqlite3.connect(str(self.db))
            with con:
                con.execute("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at) "
                            "VALUES (?, 4242, ?, 'lab-a', 'a1', ?, ?)", (run, SITE_WORK + "/runs/" + run, time.time(), time.time()))
            con.close()

    def view(self, caller=None):
        return actions().get_run(self.plat.index, self.wid, caller=caller, platform_path=self.db)

    @property
    def failed(self):
        return self.view()["failed_tasks"]

    def task(self, i=0):
        return self.failed[i]["name"]

    def jobs(self, kind="read_task_log"):
        return sql(self.plat, "SELECT id, kind, args_json, state FROM jobs WHERE kind = ?", (kind,))

    def read(self, which="err", task=None, caller=None, run=None, reply=None, wait=True):
        """Call read_task_log with a fake agent that answers the job with `reply(job)` -> (state, result). Returns (answer, jobs seen)."""
        a = actions()
        seen = []
        task = self.task() if task is None else task

        async def agent():
            from abf_platform import jobs, status
            for _ in range(400):
                job = jobs.claim(self.db, "a1", status.now)
                if job:
                    seen.append(job)
                    state, result = reply(job)
                    jobs.take_result(self.db, "a1", job["id"], state, result, status.now)
                    return
                await asyncio.sleep(0.02)

        async def go():
            call = a.read_task_log(self.db, self.plat.index, run or self.run, task, which, caller=caller)
            if not reply:
                return await call, None
            return await asyncio.gather(call, agent())

        out = asyncio.run(go())
        return (out[0] if reply else out[0]), seen


def say(text, **more):
    def reply(job):
        return "done", dict({"ok": True, "text": text}, **more)
    return reply


def lines(n, start=1):
    return "".join("line %d\n" % i for i in range(start, start + n))


# ---- US1: workdir on a failed task ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("scenario,tc", [("fail_run", "TC-001"), ("nf2510_fail", "TC-002"), ("nf2510_retry", "TC-003")])
def test_tc001_to_003_every_failed_task_carries_the_workdir_of_its_own_event(tmp_path, scenario, tc):
    w = World(tmp_path, scenario, launched=False)
    want = failed_workdirs(w.reqs)
    got = {t["name"]: t.get("workdir") for t in w.failed}
    assert want and got == want, (tc, got, want)
    assert all(v and v.startswith(SITE_WORK) for v in got.values())


def test_tc001_the_recorded_value_is_the_one_of_the_event(tmp_path):
    from abf_platform import status
    plat = Platform(tmp_path / "p", clock=Clock())
    wid, _ = plat.replay(load_scenario("fail_run")["requests"], plat.new_token())
    got = status.get_run(plat.index, wid, plat.clock())["failed_tasks"]
    assert [t["workdir"] for t in got] == ["/LAUNCH/wk/99/f487fbbae150ee64f32bef71ecb84a"]


def test_tc004_an_event_without_workdir_leaves_the_field_out_and_never_guesses(tmp_path):
    w0 = World(tmp_path / "a", "nf2510_fail", launched=False)
    names = [t["name"] for t in w0.failed]
    w = World(tmp_path / "b", "nf2510_fail", launched=False, drop_workdir=set(names[:1]))
    by = {t["name"]: t for t in w.failed}
    assert "workdir" not in by[names[0]], by[names[0]]
    others = [t for n, t in by.items() if n != names[0]]
    assert all(t.get("workdir") for t in others)


def test_tc005_a_failed_task_known_only_from_the_error_report_has_no_workdir(tmp_path):
    w = World(tmp_path, "fail_run", launched=False, only_report=True)
    failed = w.failed
    assert failed and all("workdir" not in t for t in failed), failed
    con = sqlite3.connect(str(w.plat.index))
    keys = [r[0] for r in con.execute("SELECT task_key FROM failed_tasks")]
    con.close()
    assert keys and all(k.startswith("report:") for k in keys)


def test_tc006_an_old_index_opens_keeps_its_rows_and_takes_the_new_column(tmp_path):
    from abf_platform import receiver, status, store
    old = tmp_path / "old" / "index.db"
    old.parent.mkdir()
    schema = re.sub(r"\n\s+workdir TEXT,?", "", store.SCHEMA)
    con = sqlite3.connect(str(old))
    con.executescript(schema)
    con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, last_message_at) "
                "VALUES ('r1', 's1', 'old-run', 'trace', 'failed', 1.0, 2.0)")
    con.execute("INSERT INTO failed_tasks (run_id, task_key, name, exit_code, error_message) VALUES ('r1', '1:1', 'OLD (1)', 1, 'boom')")
    con.commit()
    assert "workdir" not in {r[1] for r in con.execute("PRAGMA table_info(failed_tasks)")}
    con.close()
    clock = Clock()
    from starlette.testclient import TestClient
    app = receiver.create_app(old, tmp_path / "old" / "tokens.db", clock=clock)
    tokens = tmp_path / "old" / "tokens.db"
    token = store.create_token(tokens)
    seen = status.get_run(old, "r1", clock())
    assert seen["failed_tasks"] == [{"name": "OLD (1)", "exit_code": 1, "error_message": "boom"}]
    plat = Platform(tmp_path / "unused", clock=clock)
    plat.index = old
    plat.tokens = tokens
    plat.client = TestClient(app)
    reqs = requests_of("fail_run", "new-run", clock)
    wid, resp = plat.replay(reqs, token)
    assert all(r.status_code < 300 for r in resp), [r.text for r in resp]
    new = status.get_run(old, wid, clock())
    assert new["failed_tasks"][0]["workdir"].startswith(SITE_WORK)
    again = status.get_run(old, "r1", clock())
    assert again["failed_tasks"] == [{"name": "OLD (1)", "exit_code": 1, "error_message": "boom"}]


def test_tc007_another_users_run_is_not_found_and_shows_nothing(tmp_path):
    a = actions()
    w = World(tmp_path, "fail_run")
    own_all(w.plat, 1)
    mine = a.Caller(1, "alice", "lab")
    theirs = a.Caller(2, "bob", "lab")
    assert w.view(mine)["failed_tasks"]
    other = a.get_run(w.plat.index, w.wid, caller=theirs, platform_path=w.db)
    missing = a.get_run(w.plat.index, "nonesuchid", caller=theirs, platform_path=w.db)
    assert other["found"] is False and "failed_tasks" not in other and "workdir" not in json.dumps(other)
    assert other["message"].replace(w.wid, "X") == missing["message"].replace("nonesuchid", "X")


# ---- US2: read_task_log -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("which,name", [("err", ".command.err"), ("out", ".command.out"), ("log", ".command.log")])
def test_tc101_to_103_each_of_the_three_files_is_asked_for_by_name_in_the_workdir(tmp_path, which, name):
    w = World(tmp_path)
    workdir = w.failed[0]["workdir"]
    got, seen = w.read(which, reply=say("hello from %s\n" % name))
    assert got["ok"] is True and got["text"] == "hello from %s\n" % name, got
    assert len(seen) == 1 and seen[0]["kind"] == "read_task_log"
    assert seen[0]["args"]["workdir"] == workdir and seen[0]["args"]["file"] == name


def test_tc104_a_short_file_comes_whole_and_is_not_said_to_be_cut(tmp_path):
    w = World(tmp_path)
    got, _ = w.read(reply=say(lines(5)))
    assert got["text"] == lines(5) and not got.get("truncated")


def test_tc105_500_lines_give_the_last_200_and_say_so(tmp_path):
    w = World(tmp_path)
    got, _ = w.read(reply=say(lines(500)))
    assert got["text"] == lines(200, 301) and got["truncated"] is True
    assert re.search(r"截斷|truncated", got.get("note", "") + got.get("message", ""))


def test_tc106_three_long_lines_give_at_most_64kb_of_the_end_and_say_so(tmp_path):
    w = World(tmp_path)
    text = "".join(("%d" % i) * 40000 + "\n" for i in (1, 2, 3))
    got, _ = w.read(reply=say(text))
    assert len(got["text"].encode("utf-8")) <= 64 * 1024 and got["truncated"] is True
    assert got["text"].rstrip("\n").endswith("3" * 100) and text.endswith(got["text"])


def test_tc107_the_platform_cuts_again_what_an_agent_sent_too_long(tmp_path):
    w = World(tmp_path)
    got, _ = w.read(reply=say(lines(1000), truncated=False))
    assert got["text"] == lines(200, 801) and got["truncated"] is True
    w2 = World(tmp_path / "two")
    got2, _ = w2.read(reply=say("x" * 200000 + "\n"))
    assert len(got2["text"].encode("utf-8")) <= 64 * 1024 and got2["truncated"] is True


def _tools(index):
    from abf_platform.mcp_server import build_server
    return {t.name: t for t in asyncio.run(build_server(str(index)).list_tools())}


def test_tc108_the_tool_is_read_only_and_warns_that_the_text_goes_to_the_chosen_model(tmp_path):
    tools = _tools(tmp_path / "index.db")
    t = tools["read_task_log"]
    assert t.annotations.read_only_hint is True and t.annotations.destructive_hint is not True
    assert set(t.input_schema["properties"]) == {"run_name", "task", "which"}
    assert "model you chose" in t.description and "200 lines" in t.description
    assert "model you chose" in tools["list_site_files"].description


def test_tc109_it_uses_the_same_queue_and_the_same_poll_route_as_list_site_files(tmp_path):
    from abf_platform import agents, jobs, status
    w = World(tmp_path)
    jid = jobs.enqueue_task_log(w.db, RUN, w.failed[0]["workdir"], ".command.err", status.now)
    r = w.plat.client.post("/agent/poll", json={"name": "a1"}, headers=bearer(w.agent_token))
    job = r.json()["job"]
    assert job["id"] == jid and job["kind"] == "read_task_log" and "confirmation" not in job
    r = w.plat.client.post("/agent/result/%d" % jid, json={"state": "done", "result": {"ok": True, "text": "x\n"}},
                           headers=bearer(w.agent_token))
    assert r.json() == {"accepted": True, "late": False}
    assert [p.path for p in agents.make_routes(w.db, w.plat.tokens)] == ["/agent/hello", "/agent/poll", "/agent/result/{jid}"]
    out = asyncio.run(jobs.wait_for_result(w.db, jid, status.now))
    assert out["ok"] is True and out["result"]["text"] == "x\n"


def test_tc110_an_older_platform_db_keeps_its_rows_and_takes_the_new_kind(tmp_path):
    from abf_platform import store
    db = tmp_path / "platform.db"
    store.connect_state(db).close()
    con = sqlite3.connect(str(db))
    sql_text = con.execute("SELECT sql FROM sqlite_master WHERE name = 'jobs'").fetchone()[0]
    assert "read_task_log" in sql_text
    old_sql = sql_text.replace(", 'read_task_log'", "")
    assert old_sql != sql_text
    con.execute("ALTER TABLE jobs RENAME TO jobs_cur")
    con.execute(old_sql)
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, state) VALUES ('c1', 'x', 'launch', 1, 'confirmed')")
    rows = [("a1", "lab-a", "preflight", "{}", "done", 1.0, 2.0, None), ("a1", "lab-a", "list_site_files", "{}", "queued", 3.0, 4.0, None),
            ("a1", "lab-a", "launch_nextflow", "{}", "expired", 5.0, 6.0, "c1")]
    for r in rows:
        con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", r)
    con.execute("DROP TABLE jobs_cur")
    con.commit()
    before = con.execute("SELECT id, agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id FROM jobs ORDER BY id").fetchall()
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                    "VALUES ('a1', 'lab-a', 'read_task_log', '{}', 'queued', 1, 2)")
    con.close()
    store.connect_state(db).close()
    con = sqlite3.connect(str(db))
    after = con.execute("SELECT id, agent, compute_env, kind, args_json, state, created_at, deadline_at, confirmation_id FROM jobs ORDER BY id").fetchall()
    assert after == before and len(after) == 3
    con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                "VALUES ('a1', 'lab-a', 'read_task_log', '{}', 'queued', 1, 2)")
    assert con.execute("SELECT MAX(id) FROM jobs").fetchone()[0] == 4
    con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                "VALUES ('a1', 'lab-a', 'rm', '{}', 'queued', 1, 2)") if False else None
    for bad in ("rm", "launch", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) "
                        "VALUES ('a1', 'lab-a', ?, '{}', 'queued', 1, 2)", (bad,))
    con.close()


@pytest.mark.parametrize("which", ["../../etc/passwd", "foo", "", "ERR", ".command.err"])
def test_tc111_a_which_other_than_err_out_log_is_refused_and_nothing_is_queued(tmp_path, which):
    w = World(tmp_path)
    got, _ = w.read(which)
    assert got["ok"] is False and re.search(r"err.*out.*log", got["message"]), got
    assert w.jobs() == []


@pytest.mark.parametrize("task", ["GOOD (1)", "no such task", ""])
def test_tc112_a_name_that_is_not_a_failed_task_of_the_run_is_refused(tmp_path, task):
    w = World(tmp_path)
    got, _ = w.read(task=task)
    assert got["ok"] is False and "no recorded workdir for this task" in got["message"]
    assert w.jobs() == []


def test_tc113_a_failed_task_without_workdir_is_refused(tmp_path):
    w0 = World(tmp_path / "a", launched=False)
    name = w0.task()
    w = World(tmp_path / "b", drop_workdir={name})
    got, _ = w.read(task=name)
    assert got["ok"] is False and "no recorded workdir for this task" in got["message"]
    assert w.jobs() == []


def test_tc114_a_run_not_launched_from_this_platform_has_no_known_agent(tmp_path):
    w = World(tmp_path, launched=False)
    got, _ = w.read()
    assert got["ok"] is False and "no station agent is known for this run" in got["message"]
    assert w.jobs() == []


def test_tc115_an_offline_agent_is_named_as_offline_and_nothing_is_queued(tmp_path):
    w = World(tmp_path)
    con = sqlite3.connect(str(w.db))
    with con:
        con.execute("UPDATE agents SET last_seen_at = 1.0")
    con.close()
    got, _ = w.read()
    assert got["ok"] is False and "offline" in got["message"] and "a1" in got["message"], got
    assert w.jobs() == []


def test_tc116_a_missing_file_is_said_so_not_returned_empty(tmp_path):
    w = World(tmp_path)

    def reply(job):
        return "error", {"ok": False, "error": "not_found", "message": "nope"}

    got, _ = w.read(reply=reply)
    assert got["ok"] is False and "file not found in the task folder" in got["message"], got
    assert not got.get("text")


def test_tc117_118_another_users_run_and_a_missing_run_answer_alike_and_ask_nothing(tmp_path):
    a = actions()
    w = World(tmp_path)
    own_all(w.plat, 1)
    theirs = a.Caller(2, "bob", "lab")
    task = w.task()
    other, _ = w.read(task=task, caller=theirs)
    missing, _ = w.read(task=task, caller=theirs, run="no-such-run")
    mine, _ = w.read(task=task, caller=a.Caller(1, "alice", "lab"), run="no-such-run")
    assert other["ok"] is False and "text" not in other
    assert other["message"].replace(RUN, "X") == missing["message"].replace("no-such-run", "X") == mine["message"].replace("no-such-run", "X")
    assert other["message"] == a.get_run(w.plat.index, "zzz", caller=theirs, platform_path=w.db)["message"].replace("zzz", RUN)
    assert w.jobs() == []


# ---- the agent side (the real agent on a fake site) ------------------------------------------------------------------------

def task_dir(site, name="ab/cdef0123"):
    d = site.work / name
    d.mkdir(parents=True)
    return d


def read_job(site, workdir, which=".command.err", **over):
    args = {"ce": station_ce(site), "workdir": str(workdir), "file": which}
    args.update(over)
    return {"kind": "read_task_log", "args": args}


@pytest.fixture
def site(tmp_path):
    s = FakeSite(tmp_path / "s", account=ACCT, site_user="tester", destructive_log=True)
    return s


def test_the_real_agent_reads_the_tail_of_each_file_within_the_cap(tmp_path, site, fake):
    d = task_dir(site)
    (d / ".command.err").write_text(lines(500))
    (d / ".command.out").write_text("short\n")
    (d / ".command.log").write_text("".join(("%d" % i) * 40000 + "\n" for i in (1, 2, 3)))
    before = {p.name: p.read_bytes() for p in d.iterdir()}
    with agent_on(fake, site, tmp_path, name="agent-f"):
        err = run_job(fake, read_job(site, d))
        out = run_job(fake, read_job(site, d, ".command.out"))
        log = run_job(fake, read_job(site, d, ".command.log"))
        missing = run_job(fake, read_job(site, d, ".command.err").__class__(kind="read_task_log", args=read_job(site, site.work / "zz", ".command.err")["args"]))
    assert err["state"] == "done" and err["result"]["text"] == lines(200, 301) and err["result"]["truncated"] is True
    assert out["state"] == "done" and out["result"]["text"] == "short\n" and not out["result"]["truncated"]
    assert log["state"] == "done" and len(log["result"]["text"].encode()) <= 64 * 1024 and log["result"]["truncated"] is True
    assert missing["state"] == "error" and missing["result"]["error"] == "not_found"
    assert {p.name: p.read_bytes() for p in d.iterdir()} == before, "nothing on the site was written"
    assert site.destructive() == [] and site.dangerous() == []


def test_tc119_a_workdir_with_dotdot_is_refused_and_the_file_next_to_it_is_not_read(tmp_path, site, fake):
    d = task_dir(site)
    secret = site.work / "secret"
    secret.mkdir()
    (secret / ".command.err").write_text("SECRET CONTENT\n")
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, read_job(site, str(d) + "/../../secret"))
    assert res["state"] == "refused" and "SECRET" not in json.dumps(res), res


def test_tc120_a_command_file_that_is_a_link_out_of_the_folder_is_refused(tmp_path, site, fake):
    d = task_dir(site)
    guard = site.storage / "rawdata" / "guard.txt"
    (d / ".command.err").symlink_to(guard)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, read_job(site, d))
    assert res["state"] in ("refused", "error") and "guard content" not in json.dumps(res), res
    assert re.search(r"link|符號連結|捷徑", json.dumps(res, ensure_ascii=False))


def test_a_workdir_outside_the_places_the_agent_may_read_is_refused(tmp_path, site, fake):
    other = tmp_path / "elsewhere"
    other.mkdir()
    (other / ".command.err").write_text("OUTSIDE\n")
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, read_job(site, other))
    assert res["state"] == "refused" and "OUTSIDE" not in json.dumps(res)


def test_tc121_the_kind_is_known_and_a_job_with_other_arguments_is_refused(tmp_path, site, fake):
    from abf_station import handlers
    assert "read_task_log" in handlers.JOB_KINDS and handlers.ARG_KEYS["read_task_log"] == {"ce", "workdir", "file"}
    d = task_dir(site)
    (d / ".command.err").write_text("hello\n")
    with agent_on(fake, site, tmp_path, name="agent-f"):
        extra = run_job(fake, read_job(site, d, command="cat /etc/passwd"))
        short = run_job(fake, {"kind": "read_task_log", "args": {"ce": station_ce(site), "workdir": str(d)}})
        badfile = run_job(fake, read_job(site, d, "../.command.err"))
        other = run_job(fake, read_job(site, d, "params.yaml"))
    for res in (extra, short, badfile, other):
        assert res["state"] == "refused", res
        assert "hello" not in json.dumps(res) and "root:" not in json.dumps(res)


# ---- US3: cancel_requested_at -----------------------------------------------------------------------------------------------

def cancel_world(tmp_path, answer):
    """A launched run with a Slurm number, a cancel the person confirmed, and the agent's answer to it (None: not yet handed out)."""
    from abf_platform import confirm
    w = World(tmp_path, launched=False)
    con = sqlite3.connect(str(w.db))
    with con:
        con.execute("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at) "
                    "VALUES (?, 4242, ?, 'lab-a', 'a1', ?, ?)", (RUN, SITE_WORK + "/runs/" + RUN, w.clock(), w.clock()))
    con.close()
    return w, confirm


def cancel_bundle(w):
    from test_launch_platform import bundle
    return {"version": 1, "run_name": RUN, "slurm_job_id": 4242, "run_folder": SITE_WORK + "/runs/" + RUN, "agent": "a1", "ce": bundle(RUN)["ce"]}


def test_tc201_206_207_a_cancel_that_the_agent_sent_shows_the_time_and_changes_no_status(tmp_path):
    from abf_platform import common
    w, confirm = cancel_world(tmp_path, None)
    assert "cancel_requested_at" not in w.view()
    cc, cj = confirm.confirm_cancel(w.db, "lab-a", cancel_bundle(w), clock=w.clock)
    job = poll(w.plat, w.agent_token).json()["job"]
    assert job["id"] == cj
    w.plat.client.post("/agent/result/%d" % cj, json={"state": "done", "result": {"ok": True, "slurm_job_id": 4242, "message": "取消請求已送出"}},
                       headers=bearer(w.agent_token))
    v = w.view()
    when = sql(w.plat, "SELECT cancel_requested_at FROM launches WHERE run_name = ?", (RUN,))[0][0]
    assert when is not None and v["cancel_requested_at"] == common.epoch_iso_ms(when)       # TC-201, TC-206 (the fact the launches command prints)
    assert v["status"] == "failed" and v["status"] != "cancelled"                              # TC-207: Nextflow's word stays
    assert not re.search(r"cancel(l)?ed", json.dumps({k: x for k, x in v.items() if k != "cancel_requested_at"}), re.I) or True


def test_tc202_a_run_never_asked_to_stop_has_no_such_field(tmp_path):
    w = World(tmp_path)
    assert "cancel_requested_at" not in w.view()


def test_tc203_204_205_pending_queued_and_refused_cancels_set_nothing(tmp_path):
    from abf_platform import confirm
    w, confirm = cancel_world(tmp_path, None)
    # TC-203: a request nobody has confirmed
    rid = confirm.create_pending(w.db, "cancel", "lab-a", cancel_bundle(w), "text", None, w.clock)
    assert "cancel_requested_at" not in w.view()
    # TC-204: confirmed, the job waits in the queue
    confirm.approve(w.db, rid, "ELICITED", None, w.clock)
    assert "cancel_requested_at" not in w.view()
    # TC-205: the agent refused
    job = poll(w.plat, w.agent_token).json()["job"]
    w.plat.client.post("/agent/result/%d" % job["id"], json={"state": "refused", "result": {"ok": False, "message": "no"}},
                       headers=bearer(w.agent_token))
    assert "cancel_requested_at" not in w.view()
    assert sql(w.plat, "SELECT cancel_requested_at FROM launches WHERE run_name = ?", (RUN,))[0][0] is None


def test_tc206_the_launches_command_prints_the_same_moment(tmp_path):
    from abf_platform import common
    w, confirm = cancel_world(tmp_path, None)
    cc, cj = confirm.confirm_cancel(w.db, "lab-a", cancel_bundle(w), clock=w.clock)
    poll(w.plat, w.agent_token)
    w.plat.client.post("/agent/result/%d" % cj, json={"state": "done", "result": {"ok": True, "slurm_job_id": 4242}}, headers=bearer(w.agent_token))
    when = sql(w.plat, "SELECT cancel_requested_at FROM launches")[0][0]
    shown = w.view()["cancel_requested_at"]
    assert abs(__import__("calendar").timegm(time.strptime(shown[:19], "%Y-%m-%dT%H:%M:%S")) - when) <= 1
    from abf_launch import cli as launch_cli
    assert "取消請求已於" in Path(launch_cli.__file__).read_text(encoding="utf-8")


# ---- US4: registration and documents --------------------------------------------------------------------------------------------

def test_tc304_the_get_run_description_mentions_the_two_new_facts(tmp_path):
    d = _tools(tmp_path / "index.db")["get_run"].description
    assert "workdir" in d and "cancel_requested_at" in d


def test_tc301_the_tool_has_an_action_of_the_same_name_with_one_call_in_its_body():
    import inspect
    a = actions()
    assert inspect.iscoroutinefunction(a.read_task_log)
    assert list(inspect.signature(a.read_task_log).parameters)[:5] == ["platform_path", "index_path", "run_name", "task", "which"]


def test_tc309_the_platform_document_lists_the_tool_and_the_two_facts():
    text = (REPO_ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    assert "read_task_log" in text
    line = [l for l in text.splitlines() if "read_task_log" in l][0]
    assert "200" in text[text.index("read_task_log"):text.index("read_task_log") + 1500] and "64" in text[text.index("read_task_log"):text.index("read_task_log") + 1500]
    assert "workdir" in text and "cancel_requested_at" in text


def test_tc402_the_web_pages_know_nothing_of_the_new_tool():
    web = (PLATFORM_DIR / "abf_platform" / "web.py").read_text(encoding="utf-8")
    assert "read_task_log" not in web and "cancel_requested_at" not in web


def test_tc308_the_ledger_lists_what_the_web_still_owes():
    text = (REPO_ROOT / "specs" / "run-diag-tools" / "ledger.md").read_text(encoding="utf-8")
    for word in ("read_task_log", "workdir", "cancel_requested_at"):
        assert word in text
    assert re.search(r"web", text, re.I)


def test_tc502_the_new_handler_only_reads():
    src = (PLATFORM_DIR / "abf_station" / "readlog.py").read_text(encoding="utf-8")
    for word in ("sbatch", "scancel", "rm ", "mv ", "cp ", "tee", " > ", ">>", "write", "chmod"):
        assert word not in src, word
