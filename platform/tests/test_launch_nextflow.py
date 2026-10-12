# Nothing existing: end-to-end tests that run the pinned real Nextflow 25.10.4 through the real head script, the real relay and the real receiver; Nextflow's own test setups know nothing of our relay and platform.
"""Live progress over the whole chain (feature 007b): head.sh -> Nextflow 25.10.4 -> relay -> receiver -> get_run."""
import os
import shlex
import signal
import subprocess
import threading
import time
from pathlib import Path

import pytest

from abf_platform import common, rebuild, status, store
from e2e_harness import Env, trace_by_process, trace_counts, trace_files, trace_rows, wait_until
from helpers import PLATFORM_DIR
from test_launch_bundle import ce_snapshot
from test_relay_loopback import Relay

FLOWS = Path(__file__).resolve().parent / "fixtures" / "flows"
ACCOUNT = "ACCT-TEST-7"

SHIM = """#!/bin/bash
# stands in for `nextflow run <pipeline> -r <rev> ...`: runs the local fixture flow with the other options unchanged
args=("$@"); out=(run "$ABF_TEST_FLOW"); i=2
while [ $i -lt ${#args[@]} ]; do
  case "${args[$i]}" in -r) i=$((i + 2)); continue ;; esac
  out+=("${args[$i]}"); i=$((i + 1))
done
exec bash "$ABF_NXF2_LAUNCHER" "${out[@]}"
"""


class Chain:
    """One receiver, and for each run a relay, a run folder written the way the agent writes it, and the real head.sh."""

    def __init__(self, cfg, tmp):
        self.cfg = cfg
        self.tmp = Path(tmp)
        self.env = Env(cfg, self.tmp / "plat")
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "nextflow").write_text(SHIM)
        (self.bin / "nextflow").chmod(0o755)
        self.relays = {}
        self.runs = {}

    def start(self, run, flow, n=8, kill_group=False):
        (self.tmp / ("relay-" + run)).mkdir()
        relay = Relay(self.tmp / ("relay-" + run), forward=self.env.port,
                      instance=store.instance_id(store.default_platform_path(self.env.index)))
        self.relays[run] = relay
        from abf_station import launch
        ce = ce_snapshot(workDir=str(self.tmp / ("work-" + run)), launchDir=None, headQueue="normal", computeQueue=None, environment=[
            {"name": "NXF_OPTS", "value": "-Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=%d" % relay.port, "head": True, "compute": False}],
            headJobOptions="-c 1", nextflowConfig="process.executor = 'local'\ntrace.enabled = true\n")
        facts = {"slurm_account": ACCOUNT, "reach": "ssh", "platform_local": True, "endpoint": self.env.url,
                 "forward_file": str(relay.forward_file), "storage_root": str(self.tmp)}
        b = launch.render_bundle(ce=ce, agent="a1", facts=facts, roots=[str(self.tmp)], run_name=run, pipeline="nf-core/ampliseq",
                                 revision="2.18.0", samplesheet=[["sample", "fastq_1"], ["s", str(self.tmp / "s.fq")]], params={"n": n})
        folder = Path(b["run_folder"])
        folder.mkdir(parents=True, mode=0o700)
        for name, text in b["files"].items():
            (folder / name).write_text(text)
        token = store.create_token(self.env.tokens, run_name=run)
        (folder / "tower.token").write_text(token)
        env = {k: v for k, v in os.environ.items() if not k.startswith(("NXF_", "TOWER_", "ABF_"))}
        env.update({"PATH": str(self.bin) + os.pathsep + env["PATH"], "NXF_HOME": self.cfg["home"], "NXF_VER": self.cfg["ver"],
                    "NXF_OFFLINE": "true", "NXF_ANSI_LOG": "false", "NXF_DISABLE_CHECK_LATEST": "true",
                    "ABF_TEST_FLOW": str(FLOWS / flow / "main.nf"), "ABF_NXF2_LAUNCHER": self.cfg["launcher"]})
        proc = subprocess.Popen(["bash", str(folder / "head.sh")], cwd=str(folder), env=env, stdout=open(folder / "nf-out.txt", "w"),
                                stderr=subprocess.STDOUT, start_new_session=True)
        self.runs[run] = {"proc": proc, "folder": folder, "bundle": b, "token": token}
        return proc

    def view(self, run):
        for r in status.list_runs(self.env.index, status.now()):
            if r["name"] == run:
                return status.get_run(self.env.index, r["id"], status.now())
        return None

    def stop(self):
        for r in self.runs.values():
            if r["proc"].poll() is None:
                os.killpg(r["proc"].pid, signal.SIGKILL)
        for relay in self.relays.values():
            relay.stop()
        self.env.stop()


@pytest.fixture(scope="module")
def chain(e2e_cfg2, tmp_path_factory):
    c = Chain(e2e_cfg2, tmp_path_factory.mktemp("chain"))
    samples = {"multi": []}

    def sampler():
        while not stop.is_set():
            v = c.view("run-multi")
            if v:
                samples["multi"].append((time.time(), {p["name"]: (p["succeeded"], p["running"], p["failed"]) for p in v["processes"]},
                                         v["status"], v["tasks"]["total"]))
            stop.wait(0.5)

    stop = threading.Event()
    c.samples = samples
    c.start("run-multi", "multi")
    c.start("run-retry", "retry")
    c.start("run-cut", "multi")
    c.start("run-term", "multi", n=20)
    t = threading.Thread(target=sampler, daemon=True)
    t.start()
    # the relay of run-cut is stopped while the run is under way (it never sends its complete, so it is lost); run-term gets a SIGTERM
    wait_until(lambda: (c.view("run-cut") or {}).get("tasks", {}).get("succeeded", 0) >= 1, timeout=90, what="run-cut under way")
    c.relays["run-cut"].stop()
    wait_until(lambda: (c.view("run-term") or {}).get("tasks", {}).get("succeeded", 0) >= 1, timeout=90, what="run-term under way")
    os.killpg(c.runs["run-term"]["proc"].pid, signal.SIGTERM)
    for r in c.runs.values():
        try:
            r["proc"].wait(timeout=240)
        except subprocess.TimeoutExpired:
            pass
    time.sleep(2)
    stop.set()
    t.join(5)
    yield c
    c.stop()


def trace_of(c, run):
    return trace_rows(trace_files(c.runs[run]["folder"])[0])


def test_tc026_the_progress_of_a_run_is_seen_changing_and_ends_equal_to_the_trace(chain):
    # TC-026: head.sh as generated, NXF_OPTS as generated, the relay as it is
    assert chain.runs["run-multi"]["proc"].returncode == 0, open(chain.runs["run-multi"]["folder"] / "nf-out.txt").read()
    rows = trace_of(chain, "run-multi")
    assert len(rows) >= 12
    frames = []
    for _, procs, st, total in chain.samples["multi"]:
        if not frames or frames[-1] != (procs, total):
            frames.append((procs, total))
    assert len(frames) >= 3, frames
    assert any(r > 0 for _, procs, _, _ in chain.samples["multi"] for (_, r, _) in procs.values()), "a moment with tasks running"
    v = chain.view("run-multi")
    assert v["status"] == "succeeded"
    want = trace_by_process(rows)
    got = {p["name"]: {k: p[k] for k in ("total", "succeeded", "cached", "failed", "aborted")} for p in v["processes"]}
    assert got == want
    assert v["tasks"]["total"] == len(rows) == trace_counts(rows)["total"]
    log = chain.relays["run-multi"].lines()
    opened = [ln for ln in log if "OPEN" in ln]
    assert opened and all("OPEN-HTTP 127.0.0.1 %d" % chain.env.port in ln for ln in opened), opened
    assert not [ln for ln in log if "DENY" in ln], log


def test_tc027_a_failed_task_with_its_message_and_a_retried_task_that_is_not_a_failure(chain):
    assert chain.runs["run-retry"]["proc"].returncode != 0
    rows = trace_of(chain, "run-retry")
    v = chain.view("run-retry")
    assert v["status"] == "failed"
    assert [f["name"] for f in v["failed_tasks"]] == ["BAD"]
    log = rebuild._parse_log(chain.runs["run-retry"]["folder"] / ".nextflow.log")
    assert v["failed_tasks"][0]["error_message"] == log["errors"]["BAD"] and "FIXTURE_BOOM_7" in log["errors"]["BAD"]
    got = {p["name"]: {k: p[k] for k in ("total", "succeeded", "cached", "failed", "aborted")} for p in v["processes"]}
    assert got == trace_by_process(rows)
    assert got["FLAKY"]["succeeded"] == 1 and got["FLAKY"]["failed"] == 1


def test_tc033_with_the_relay_gone_the_run_finishes_is_shown_lost_and_is_made_right_from_its_records(chain):
    assert chain.runs["run-cut"]["proc"].returncode == 0, open(chain.runs["run-cut"]["folder"] / "nf-out.txt").read()
    rows = trace_of(chain, "run-cut")
    assert len(rows) >= 12
    v = chain.view("run-cut")
    assert v["status"] != "succeeded", "its last messages were lost with the relay"
    later = status.get_run(chain.env.index, v["id"], time.time() + 181)
    assert later["status"] == "lost"


def test_tc045_a_stopped_run_is_shown_as_nextflow_reports_it_and_a_run_that_just_vanishes_is_lost(chain):
    v = chain.view("run-term")
    assert v is not None and v["status"] == "failed", v
    assert v["ended_at"] is not None
    assert v["tasks"]["total"] >= 1
    k = chain.view("run-cut")      # its messages stopped with the relay and no complete ever came: it just vanishes
    assert k["status"] == "running"
    assert status.get_run(chain.env.index, k["id"], time.time() + 181)["status"] == "lost"
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        assert "已取消" not in f.read_text(encoding="utf-8"), f.name


def test_tc039_the_token_of_a_run_is_refused_for_any_other_run_through_the_whole_chain(chain):
    import urllib.request
    tok = chain.runs["run-cut"]["token"]  # its complete never arrived, so the token is still alive
    relay = chain.relays["run-retry"]
    body = b'{"sessionId": "s-x", "runName": "some-other-run"}'
    req = urllib.request.Request("http://127.0.0.1:%d/trace/create" % chain.env.port, data=body, method="POST", headers={
        "Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=10)
    assert e.value.code in (401, 403)
    assert chain.view("some-other-run") is None


def test_tc033_the_records_of_the_run_folder_make_the_lost_run_right_and_say_where_the_answer_came_from(chain):
    # last in the file: rebuild drops the whole index and builds it again from the folder it is given
    rows = trace_of(chain, "run-cut")
    result = rebuild.rebuild([str(chain.runs["run-cut"]["folder"])], chain.env.index, out=lambda *_: None)
    assert result.runs == 1
    fixed = chain.view("run-cut")
    assert fixed["status"] == "succeeded" and fixed["tasks"]["total"] == len(rows)
    import sqlite3
    con = sqlite3.connect(str(chain.env.index))
    assert con.execute("SELECT source FROM runs WHERE run_name = 'run-cut'").fetchone()[0] == "rebuild"
    con.close()
