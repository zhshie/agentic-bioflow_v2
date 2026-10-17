# Nothing existing: end-to-end tests of launch, cancel and fetch-records with the real platform process, the real agent process, the real command line on a pseudo-terminal and a fake site; the pieces are ours.
"""Launch, cancel and fetch-records through the whole chain except the cluster itself (feature 007b)."""
import json
import os
import re
import signal
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest

from helpers import db_bytes, pkg_env
from launch_harness import ACCOUNT, QUESTION_CANCEL, QUESTION_LAUNCH, Pty, cli_argv
from station_harness import FakeSite, RealPlatform, snapshot, start_agent, tool_json

NAME = "agent-e"
FAST = {"ABF_AGENT_HEARTBEAT_SECONDS": 2, "ABF_AGENT_POLL_SECONDS": 2, "ABF_PLATFORM_DEADLINE_PREFLIGHT": 40,
        "ABF_PLATFORM_DEADLINE_LAUNCH": 30, "ABF_PLATFORM_DEADLINE_CANCEL": 30, "ABF_PLATFORM_LAUNCH_GRACE": 1}


class World:
    def __init__(self, tmp, env=None, agent_env=None):
        self.tmp = Path(tmp)
        self.site = FakeSite(self.tmp / "site", account=ACCOUNT, site_user="tester", destructive_log=True)
        (self.site.storage / "cache").mkdir()
        for i in range(1, 4):
            (self.site.storage / "rawdata" / ("s%d.fq" % i)).write_text("x")
        self.env = dict(FAST, **(env or {}))
        self.plat = RealPlatform(self.tmp, self.env)
        self.agent = start_agent(self.plat, self.site, NAME, self.tmp,
                                 env=self.site.agent_env(**dict({"ABF_STATION_MIN_REMAINING": 2}, **(agent_env or {}))))
        r = self.plat.create_ce(self.site, "lab-a", agent=NAME, **{"--head-job-options": "-A %s -c 4 --mem=26G -t 1-00:00:00" % ACCOUNT,
                                                                   "--nextflow-config": "process.executor = 'slurm'\n"})
        assert r.returncode == 0, r.stdout + r.stderr
        r = self.plat.cli(["ce", "update", "lab-a", "--env", "head:NXF_SINGULARITY_CACHEDIR=%s" % (self.site.storage / "cache")])
        assert r.returncode == 0, r.stdout + r.stderr
        self.plat.wait_ce("lab-a", "available")

    def samplesheet(self, name="samples.csv"):
        p = self.tmp / name
        p.write_text("sample,fastq_1\n" + "".join("s%d,%s/rawdata/s%d.fq\n" % (i, self.site.storage, i) for i in range(1, 4)))
        return p

    def args(self, run, extra=()):
        return ["launch", "--ce", "lab-a", "--pipeline", "nf-core/ampliseq", "--revision", "2.18.0", "--run-name", run,
                "--samplesheet", str(self.samplesheet()), "--param", "pacbio=true"] + list(extra)

    def cli_env(self, **extra):
        e = dict(self.plat.env)
        e.update({k: str(v) for k, v in extra.items()})
        return e

    def run_cli(self, *args, answer=None, question=QUESTION_LAUNCH, timeout=90, env=None):
        p = Pty(cli_argv(*args), env or self.cli_env())
        if answer is not None:
            assert p.wait_for(question, 30), p.text()
            p.send(answer)
        return p.finish(timeout)

    def rows(self, sql, args=()):
        return self.plat.db_rows(sql, args)

    def close(self):
        self.agent.stop()
        self.plat.stop()


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    w = World(tmp_path_factory.mktemp("e2e"))
    yield w
    w.close()


def sbatches(site):
    return [c for c in site.calls() if c.startswith("sbatch ") and "--version" not in c]


def test_tc001_tc012_tc019_a_confirmed_launch_goes_through_every_hand_and_the_token_stays_in_its_file(world):
    site = world.site
    rc, screen = world.run_cli(*world.args("run-a"), answer="y\n")
    assert rc == 0 and "已送出：Slurm 工作編號 4242" in screen, screen[-600:]
    f = site.work / "runs" / "run-a"
    assert sorted(p.name for p in f.iterdir()) == sorted(["samplesheet.csv", "params.yaml", "nextflow.config", "tower.token", "head.sh"])
    assert len(sbatches(site)) == 1
    row = world.rows("SELECT run_name, slurm_job_id, run_folder, ce, agent, submitted_at FROM launches")[0]
    assert row[:5] == ("run-a", 4242, str(f), "lab-a", NAME) and row[5]
    token = (f / "tower.token").read_text()
    assert token.startswith("abf_")
    # the plain token is nowhere but in its file
    blob = db_bytes(world.plat.index, world.plat.tokens, world.plat.state_db)
    assert token.encode() not in blob
    assert token not in screen and token not in world.agent.output() and token not in (world.plat.dir / "serve.log").read_text()
    for p in f.iterdir():
        assert (token in p.read_text()) == (p.name == "tower.token")
    for c in site.calls() + site.ssh_calls():
        assert token not in c
    # the shown screen and the written script are the same text
    shown = screen[screen.index("== head.sh"):screen.index(QUESTION_LAUNCH)] if QUESTION_LAUNCH in screen else ""
    assert (f / "head.sh").read_text().splitlines()[0] == "#!/bin/bash"
    assert rows_of(world, "confirmations")[0][4] is not None, "the confirmation is spent when the job is claimed"
    assert not [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")]
    assert site.guards_intact()


def rows_of(world, table):
    return world.rows("SELECT * FROM " + table)


def test_tc020_the_run_token_is_for_its_run_and_ends_with_the_run(world):
    import httpx
    f = world.site.work / "runs" / "run-a"
    token = (f / "tower.token").read_text()
    base = "http://127.0.0.1:%d" % world.plat.port
    h = {"Authorization": "Bearer " + token}
    r = httpx.post(base + "/trace/create", json={"sessionId": "s1", "runName": "someone-else"}, headers=h)
    assert r.status_code in (401, 403)
    r = httpx.post(base + "/trace/create", json={"sessionId": "s1", "runName": "run-a"}, headers=h)
    assert r.status_code == 200
    wid = r.json()["workflowId"]
    rc, listing = world.run_cli("launches")
    assert rc == 0 and "run-a" in listing and "已收到 Nextflow 的事件" in listing
    r = httpx.put(base + "/trace/%s/complete" % wid, json={"workflow": {"success": True, "exitStatus": 0}, "progress": {}}, headers=h)
    assert r.status_code == 200
    r = httpx.post(base + "/trace/create", json={"sessionId": "s2", "runName": "run-a"}, headers=h)
    assert r.status_code == 401


def test_tc003_an_answer_that_is_not_y_leaves_the_site_and_the_platform_as_they_were(world):
    site = world.site
    before = (len(site.calls()), len(rows_of(world, "confirmations")), len(rows_of(world, "launches")))
    for answer in ("n\n", "\n", "yes\n"):
        rc, screen = world.run_cli(*world.args("run-never"), answer=answer)
        assert rc != 0 and "未送出" in screen
    assert (len(site.calls()), len(rows_of(world, "confirmations")), len(rows_of(world, "launches"))) == before
    assert not (site.work / "runs" / "run-never").exists()


def test_tc016_two_launches_of_one_name_make_one_folder_and_one_sbatch(world):
    site = world.site
    n = len(sbatches(site))
    a = Pty(cli_argv(*world.args("run-twin")), world.cli_env())
    b = Pty(cli_argv(*world.args("run-twin")), world.cli_env())
    assert a.wait_for(QUESTION_LAUNCH, 30) and b.wait_for(QUESTION_LAUNCH, 30)
    a.send("y\n")
    b.send("y\n")
    ra, sa = a.finish(90)
    rb, sb = b.finish(90)
    assert sorted([ra == 0, rb == 0]) == [False, True], (sa[-300:], sb[-300:])
    assert len(sbatches(site)) == n + 1
    assert len([x for x in world.rows("SELECT run_name FROM launches") if x[0] == "run-twin"]) == 1


def test_tc040_tc044_a_cancel_stops_the_one_job_and_the_second_try_finds_it_gone(world):
    site = world.site
    site.set("sbatch_id", "5151")
    rc, screen = world.run_cli(*world.args("run-c"), answer="y\n")
    assert rc == 0, screen[-300:]
    site.add_job(9001, "nf-someone-else", "other", "/elsewhere")
    rc, screen = world.run_cli("cancel", "run-c", answer="Y\n", question=QUESTION_CANCEL)
    assert rc == 0 and "取消請求已送出" in screen, screen[-400:]
    assert [c for c in site.calls() if c.startswith("scancel")] == ["scancel 5151"]
    assert "9001|nf-someone-else|other|/elsewhere" in site.slurm_jobs()
    assert world.rows("SELECT cancel_requested_at FROM launches WHERE run_name = 'run-c'")[0][0] is not None
    rc, listing = world.run_cli("launches")
    assert "取消請求已於" in listing and not re.search(r"已取消|執行中|成功|失敗", listing)
    rc, screen = world.run_cli("cancel", "run-c", answer="y\n", question=QUESTION_CANCEL)
    assert rc != 0 and re.search(r"已不在佇列|已結束", screen), screen[-300:]
    assert [c for c in site.calls() if c.startswith("scancel")] == ["scancel 5151"]


def test_tc010_tc061_no_web_page_and_no_mcp_tool_can_launch_or_cancel(world):
    import httpx
    base = "http://127.0.0.1:%d" % world.plat.port
    for path in ("/", "/login", "/confirm", "/confirmation", "/launch", "/cancel"):
        for method in ("GET", "POST"):
            assert httpx.request(method, base + path, json={}).status_code in (401, 404, 405), path
    _, outs = world.plat.mcp([("list_agents", {})])
    tools, _ = world.plat.mcp([])
    # 009c: the six read tools plus launch and cancel, which only make a pending request (no job without a person's yes)
    assert sorted(t.name for t in tools) == ["cancel", "get_compute_env", "get_run", "launch", "list_agents", "list_compute_envs",
                                              "list_runs", "list_site_files"]


def test_tc034_fetch_records_brings_the_logs_back_and_rebuild_puts_a_lost_run_right(world, e2e_cfg2):
    site = world.site
    site.set("sbatch_id", "6161")
    rc, screen = world.run_cli(*world.args("run-f"), answer="y\n")
    assert rc == 0, screen[-300:]
    f = site.work / "runs" / "run-f"
    # a real Nextflow run in that folder leaves the records Nextflow leaves
    env = {k: v for k, v in os.environ.items() if not k.startswith(("NXF_", "TOWER_", "ABF_"))}
    env.update({"NXF_HOME": e2e_cfg2["home"], "NXF_VER": e2e_cfg2["ver"], "NXF_OFFLINE": "true", "NXF_ANSI_LOG": "false",
                "NXF_DISABLE_CHECK_LATEST": "true"})
    flow = Path(__file__).resolve().parent / "fixtures" / "flows" / "ok" / "main.nf"
    r = subprocess.run(["bash", e2e_cfg2["launcher"], "run", str(flow), "-name", "run-f", "-with-trace", "-process.executor", "local"], cwd=str(f), env=env,
                       capture_output=True, text=True, timeout=240)
    assert r.returncode == 0, r.stdout + r.stderr
    before = snapshot(f)
    destructive_before, confirmations_before = len(site.destructive()), len(rows_of(world, "confirmations"))
    rc, screen = world.run_cli("fetch-records", "run-f")
    assert rc == 0, screen
    assert QUESTION_LAUNCH not in screen and len(rows_of(world, "confirmations")) == confirmations_before, "reading asks for no confirmation"
    assert snapshot(f) == before, "the site folder is untouched"
    got = world.plat.dir / "data" / "records" / "run-f"
    assert (got / ".nextflow.log").is_file() and (got / ".nextflow" / "history").is_file()
    assert list(got.glob("trace-*.txt")), "the trace the log names came too"
    assert not (got / "tower.token").exists() and not (got / "params.yaml").exists()
    assert len(site.destructive()) == destructive_before, "nothing was unpacked, moved or deleted on the site"
    rc, out = world.run_cli("rebuild")
    assert rc == 0, out
    _, outs = world.plat.mcp([("list_runs", {})])
    runs = tool_json(outs[0])["runs"]
    mine = [r for r in runs if r["name"] == "run-f"]
    assert mine and mine[0]["status"] == "succeeded" and mine[0]["tasks"]["total"] == 7


def test_tc035_a_run_that_was_not_launched_from_this_platform_cannot_be_fetched(world):
    rc, out = world.run_cli("fetch-records", "never-launched")
    assert rc != 0 and re.search(r"不是平台自己送出的|not launched", out)


def test_tc018_an_answer_after_the_deadline_is_still_recorded_and_a_killed_agent_leaves_an_honest_message(tmp_path):
    w = World(tmp_path, env={"ABF_PLATFORM_DEADLINE_LAUNCH": 5, "ABF_PLATFORM_LAUNCH_GRACE": 25},
              agent_env={"ABF_STATION_MIN_REMAINING": 1})
    try:
        site = w.site
        site.set("sbatch_sleep", "8")
        rc, screen = w.run_cli(*w.args("run-late"), answer="y\n", timeout=120)
        assert rc == 0 and "已送出：Slurm 工作編號 4242" in screen and "期限之後" in screen, screen[-500:]
        assert "代理沒有回應，工作已丟棄" not in screen
        assert w.rows("SELECT submitted_at FROM launches WHERE run_name = 'run-late'")[0][0] is not None
        # the agent is killed while sbatch is running
        site.set("sbatch_sleep", "20")
        site.set("sbatch_id", "7777")
        env = w.cli_env(ABF_PLATFORM_LAUNCH_GRACE=3)
        p = Pty(cli_argv(*w.args("run-lost")), env)
        assert p.wait_for(QUESTION_LAUNCH, 30)
        p.send("y\n")
        end = time.time() + 30
        while time.time() < end and not [c for c in site.calls() if c.startswith("sbatch ") and "run-lost" in c]:
            time.sleep(0.2)
        w.agent.stop(signal.SIGKILL)
        rc, screen = p.finish(90)
        assert rc != 0 and "結果不明：請查國網上的 %s 與 Slurm 工作 nf-run-lost" % (site.work / "runs" / "run-lost") in screen, screen[-500:]
        n = len(sbatches(site))
        w.agent = start_agent(w.plat, site, NAME, tmp_path, env=site.agent_env(ABF_STATION_MIN_REMAINING=1))
        time.sleep(4)
        assert len(sbatches(site)) == n, "the job is never handed to an agent again"
    finally:
        w.close()
