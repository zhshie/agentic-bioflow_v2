# Nothing existing: end-to-end tests of the real platform process, the real agent process and a fake site; the pieces are ours.
"""End to end: real platform, real agent, fake site (feature 007)."""
import asyncio
import datetime
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

from helpers import PLATFORM_DIR, REPO_ROOT, db_bytes, pkg_env, tool_json
from station_harness import (AgentProc, CANARY_TOKEN, FakePlatform, FakeSite, RealPlatform, mcp_inproc_json,
                             snapshot, start_agent)

H = 2          # heartbeat seconds the platform and the agent are started with (documented setting)
POLL = 2       # long-poll seconds
FAST = {"ABF_AGENT_HEARTBEAT_SECONDS": H, "ABF_AGENT_POLL_SECONDS": POLL,
        "ABF_PLATFORM_DEADLINE_PREFLIGHT": 40, "ABF_PLATFORM_DEADLINE_LIST_SITE_FILES": 20}
CHECKS = {"connect", "work_dir", "sbatch", "squeue", "sinfo", "java", "nextflow", "head_queue"}


# ---------------------------------------------------------------------------------------
# helpers that talk to the running platform through its files, the way the command line and MCP do
# ---------------------------------------------------------------------------------------

def run_job(state_db, kind, ce, path=None, clock=time.time, deadline=None, offline_after=None):
    """Queue a job the way the command line and MCP do, and wait for its answer. deadline and offline_after
    (seconds) are handed over explicitly by the scenarios that must not depend on process-wide settings."""
    from abf_platform import jobs
    if kind == "preflight":
        jid = jobs.enqueue_preflight(state_db, ce, clock, deadline_seconds=deadline, offline_after=offline_after)
    else:
        jid = jobs.enqueue_listing(state_db, ce, str(path), clock, deadline_seconds=deadline, offline_after=offline_after)
    return asyncio.run(jobs.wait_for_result(state_db, jid, clock))


def ce_of(state_db, name):
    from abf_platform import compute_envs
    return compute_envs.get(state_db, name)


def verdicts(out):
    return {c["name"]: c["status"] for c in out["result"]["checks"]}


def failed(out):
    return {n for n, s in verdicts(out).items() if s == "fail"}


def listing(plat, ce, path):
    return mcp_inproc_json(plat.index, "list_site_files", {"compute_env": ce, "path": str(path)})


def iso_epoch(text):
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


class World:
    """One platform process, one fake site, one agent, and one available Slurm environment named lab-a."""

    def __init__(self, tmp, env=None, agent_name="agent-a", site=None, agent_env=None, set_env=True):
        self.tmp = Path(tmp)
        self.mp = pytest.MonkeyPatch()
        self.env = dict(FAST)
        self.env.update(env or {})
        for k, v in (self.env.items() if set_env else []):  # only the shared world sets them, for its in-process calls
            self.mp.setenv(k, str(v))
        self.site = site or FakeSite(self.tmp / "site")
        self.plat = RealPlatform(self.tmp, self.env)
        self.state_db = self.plat.state_db
        self.agent = start_agent(self.plat, self.site, agent_name, self.tmp,
                                 env=self.site.agent_env(**(agent_env or {})))
        self.agent_name = agent_name
        self.tokens = {agent_name: self.agent.token}
        r = self.plat.create_ce(self.site, "lab-a", agent=agent_name)
        assert r.returncode == 0, r.stdout + r.stderr
        self.plat.wait_ce("lab-a", "available")

    def close(self):
        self.agent.stop()
        self.plat.stop()
        self.mp.undo()


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    w = World(tmp_path_factory.mktemp("w0"), agent_env={"CANARY_IN_ENV": "CANARYENV_5a7d41"})
    yield w
    w.close()


# ---------------------------------------------------------------------------------------
# User Story 3: pre-flight
# ---------------------------------------------------------------------------------------

def test_tc041_preflight_lists_every_check_and_only_all_passing_makes_it_available(world):
    # TC-041
    before = len([c for c in world.site.calls() if c.startswith("sinfo")])
    out = run_job(world.state_db, "preflight", "lab-a")
    assert out["state"] == "done" and out["ok"] is True
    assert set(verdicts(out)) == CHECKS and set(verdicts(out).values()) == {"pass"}
    nf = [c for c in out["result"]["checks"] if c["name"] == "nextflow"][0]
    assert "24.10.5" in nf["detail"]
    assert ce_of(world.state_db, "lab-a")["status"] == "available"
    assert len([c for c in world.site.calls() if c.startswith("sinfo")]) == before + 1, "the job ran more than once"


def test_tc042_one_fault_at_a_time_fails_exactly_that_check(world):
    # TC-042
    site = world.site
    moved = site.tmp / "work-moved"

    def fault_missing(tool):
        return (lambda: site.remove(tool), lambda: site.restore(tool))

    def fault_workdir():
        return (lambda: shutil.move(str(site.work), str(moved)), lambda: shutil.move(str(moved), str(site.work)))

    cases = [
        ("sinfo", fault_missing("sinfo"), {"sinfo"}),
        ("sbatch", fault_missing("sbatch"), {"sbatch"}),
        ("work_dir", fault_workdir(), {"work_dir"}),
        ("java", (lambda: site.set("java_text", 'openjdk version "11.0.21" 2023-10-17'), lambda: site.clear("java_text")),
         {"java"}),
        ("nextflow", fault_missing("nextflow"), {"nextflow"}),
        ("head_queue", (lambda: site.set("queues", "dev\nother*\n"), lambda: site.clear("queues")), {"head_queue"}),
    ]
    for name, (break_it, fix_it), want in cases:
        break_it()
        try:
            out = run_job(world.state_db, "preflight", "lab-a")
        finally:
            fix_it()
        assert failed(out) == want, (name, verdicts(out))
        # strict: the faulted item fails, every other item passes; only without sinfo is head_queue unchecked
        expected = {n: ("fail" if n in want else "pass") for n in CHECKS}
        if name == "sinfo":
            expected["head_queue"] = "unchecked"
        assert verdicts(out) == expected, (name, verdicts(out))
        ce = ce_of(world.state_db, "lab-a")
        assert ce["status"] == "invalid" and name in ce["message"], (name, ce["message"])
    assert run_job(world.state_db, "preflight", "lab-a")["ok"] is True


def test_tc043_four_faults_are_all_reported_by_one_preflight(world):
    # TC-043
    site = world.site
    moved = site.tmp / "work-moved43"
    site.remove("java")
    site.remove("nextflow")
    site.set("queues", "dev\n")
    shutil.move(str(site.work), str(moved))
    try:
        out = run_job(world.state_db, "preflight", "lab-a")
    finally:
        shutil.move(str(moved), str(site.work))
        site.restore("java")
        site.restore("nextflow")
        site.clear("queues")
    assert failed(out) == {"java", "nextflow", "head_queue", "work_dir"}, verdicts(out)
    ce = ce_of(world.state_db, "lab-a")
    assert ce["status"] == "invalid"
    for name in ("java", "nextflow", "head_queue", "work_dir"):
        assert name in ce["message"]
    assert run_job(world.state_db, "preflight", "lab-a")["ok"] is True


@pytest.mark.parametrize("text,passes", [
    ('openjdk version "17.0.9" 2023-10-17', True),
    ('openjdk version "21.0.1" 2023-10-17', True),
    ('openjdk version "17"', True),
    ('openjdk version "11.0.21" 2023-10-17', False),
    ('java version "1.8.0_392"', False),
    ("not java at all", False),
])
def test_tc044_java_versions_are_read_and_an_unreadable_one_never_passes(world, text, passes):
    # TC-044
    world.site.set("java_text", text)
    try:
        out = run_job(world.state_db, "preflight", "lab-a")
    finally:
        world.site.clear("java_text")
    java = [c for c in out["result"]["checks"] if c["name"] == "java"][0]
    assert (java["status"] == "pass") is passes, java
    if text == "not java at all":
        assert re.search(r"cannot read the version|讀不出版本", java["detail"]), java
    assert world.agent.alive()


def test_tc048_preflight_does_not_touch_the_site(world):
    # TC-048
    site = world.site
    (site.work / "sub").mkdir(exist_ok=True)
    (site.work / "a.txt").write_text("a")
    (site.work / "sub" / "b.txt").write_text("b")
    time.sleep(0.05)
    before = snapshot(site.work)
    out = run_job(world.state_db, "preflight", "lab-a")
    assert out["ok"] is True
    assert snapshot(site.work) == before
    assert site.dangerous() == []


def test_tc049_the_status_follows_the_site_in_both_directions(world):
    # TC-049
    site = world.site
    assert run_job(world.state_db, "preflight", "lab-a")["ok"]
    good = ce_of(world.state_db, "lab-a")
    assert good["status"] == "available"
    time.sleep(0.05)
    site.remove("sinfo")
    try:
        run_job(world.state_db, "preflight", "lab-a")
    finally:
        site.restore("sinfo")
    bad = ce_of(world.state_db, "lab-a")
    assert bad["status"] == "invalid" and bad["message"] != good["message"] and bad["lastUpdated"] > good["lastUpdated"]
    time.sleep(0.05)
    assert run_job(world.state_db, "preflight", "lab-a")["ok"]
    again = ce_of(world.state_db, "lab-a")
    assert again["status"] == "available" and again["lastUpdated"] > bad["lastUpdated"]


def test_tc066_failure_reasons_are_the_agents_own_short_words_never_the_site_output(world):
    # TC-066
    site = world.site
    site.set("java_dump_env", "1")
    site.set("sinfo_noise", "1")
    try:
        out = run_job(world.state_db, "preflight", "lab-a")
    finally:
        site.clear("java_dump_env")
        site.clear("sinfo_noise")
    blob = repr(out)
    assert "CANARYENV_5a7d41" not in blob and "java failed" not in blob
    assert failed(out) == {"java"}
    for c in out["result"]["checks"]:
        assert len(c["detail"]) <= 300, c
    assert "CANARYENV_5a7d41" not in ce_of(world.state_db, "lab-a")["message"]
    assert run_job(world.state_db, "preflight", "lab-a")["ok"]


# ---------------------------------------------------------------------------------------
# User Story 2 with a live agent
# ---------------------------------------------------------------------------------------

def test_tc025_a_new_environment_checks_itself_when_an_agent_is_online(world):
    # TC-025
    r = world.plat.create_ce(world.site, "lab-auto", agent="agent-a")
    assert r.returncode == 0, r.stdout + r.stderr
    first = world.plat.db_rows("SELECT status FROM compute_envs WHERE name = 'lab-auto'")[0][0]
    assert first == "creating"
    status, message = world.plat.wait_ce("lab-auto", "available", timeout=30)
    assert message


def test_tc026_without_an_agent_the_environment_waits_and_says_why(world):
    # TC-026
    r = world.plat.create_ce(world.site, "lab-orphan", agent="agent-late")
    assert r.returncode == 0, r.stdout + r.stderr
    status, message = world.plat.db_rows("SELECT status, message FROM compute_envs WHERE name = 'lab-orphan'")[0]
    assert status == "creating" and re.search(r"no agent online|沒有代理在線", message) and "agent-late" in message
    late = start_agent(world.plat, world.site, "agent-late", world.tmp, env=world.site.agent_env())
    try:
        out = run_job(world.state_db, "preflight", "lab-orphan")
        assert out["ok"] is True
        assert ce_of(world.state_db, "lab-orphan")["status"] == "available"
    finally:
        late.stop()


def test_tc031_unsupported_types_are_refused_at_once_and_nothing_is_run(world):
    # TC-031
    from abf_platform import compute_envs, jobs
    from test_station_envs import UNSUPPORTED
    log = len(world.site.calls())
    n_jobs = len(world.plat.db_rows("SELECT id FROM jobs"))
    for pid, fields in UNSUPPORTED.items():
        compute_envs.create(world.state_db, {"name": "u-" + pid, "platform": pid, "agent": "agent-a", "config": fields},
                            time.time)
    for pid in UNSUPPORTED:
        with pytest.raises(jobs.JobRefused) as e:
            jobs.enqueue_preflight(world.state_db, "u-" + pid, time.time)
        assert re.search(r"not supported|尚未支援", str(e.value))
        res = listing(world.plat, "u-" + pid, world.site.work)
        assert res["ok"] is False and re.search(r"not supported|尚未支援", res["message"])
        assert ce_of(world.state_db, "u-" + pid)["status"] == "unsupported"
    assert len(world.site.calls()) == log
    assert len(world.plat.db_rows("SELECT id FROM jobs")) == n_jobs


# ---------------------------------------------------------------------------------------
# User Story 4: listing
# ---------------------------------------------------------------------------------------

def stat_of(path):
    st = os.stat(path)
    return {"size": st.st_size, "mtime": st.st_mtime}


def test_tc051_a_listing_matches_what_the_filesystem_says(world):
    # TC-051
    raw = world.site.storage / "rawdata"
    rnd = random.Random(int.from_bytes(os.urandom(4), "big"))
    for i in range(5):
        p = raw / ("sample_%d.fastq.gz" % i)
        p.write_bytes(b"" if i == 0 else os.urandom(rnd.randint(1, 4000)))
        t = time.time() - rnd.randint(100, 100000)
        os.utime(p, (t, t))
    (raw / "batch2").mkdir(exist_ok=True)
    res = listing(world.plat, "lab-a", raw)
    assert res["ok"] is True, res
    want = {p.name: p for p in raw.iterdir()}
    got = {e["name"]: e for e in res["entries"]}
    assert set(got) == set(want) and res["count"] == len(want) == len(res["entries"])
    for name, p in want.items():
        st = stat_of(p)
        if p.is_file():
            assert got[name]["size"] == st["size"], name
            assert got[name]["type"] == "file"
        else:
            assert got[name]["type"] == "dir"
        assert abs(iso_epoch(got[name]["modified"]) - st["mtime"]) <= 1, name
    assert any(e["size"] == 0 for e in res["entries"] if e["type"] == "file")


def test_tc052_tc053_the_read_roots_are_the_work_dir_the_launch_dir_and_the_storage_root(world):
    # TC-052, TC-053
    site = world.site
    inside = [site.work, str(site.work) + "/", site.launch, site.storage, str(site.storage) + "/",
              site.storage / "rawdata"]
    for p in inside:
        res = listing(world.plat, "lab-a", p)
        assert res["ok"] is True, (p, res)
    seen = world.agent.output().count("site:")
    outside = ["/etc", "/", site.site, site.evil, "relative/dir"]
    for p in outside:
        res = listing(world.plat, "lab-a", p)
        assert res["ok"] is False and re.search(r"outside|範圍之外|不在允許", res["message"]), (p, res)
    assert world.agent.output().count("site:") == seen, "a refused path ran something on the site"


def test_tc056_an_empty_folder_is_a_success_and_three_failures_are_told_apart(world):
    # TC-056
    site = world.site
    (site.work / "empty").mkdir(exist_ok=True)
    (site.work / "a-file").write_text("x")
    locked = site.work / "locked"
    locked.mkdir(exist_ok=True)
    (locked / "inner").write_text("x")
    locked.chmod(0)
    try:
        ok = listing(world.plat, "lab-a", site.work / "empty")
        missing = listing(world.plat, "lab-a", site.work / "no-such-folder")
        notdir = listing(world.plat, "lab-a", site.work / "a-file")
        denied = listing(world.plat, "lab-a", locked)
    finally:
        locked.chmod(0o755)
    assert ok["ok"] is True and ok["count"] == 0 and ok["entries"] == []
    errors = {}
    for label, res in (("missing", missing), ("notdir", notdir), ("denied", denied)):
        assert res["ok"] is False and res["message"] and "Traceback" not in res["message"], (label, res)
        errors[label] = res["error"]
    assert len(set(errors.values())) == 3, errors
    assert errors == {"missing": "not_found", "notdir": "not_a_directory", "denied": "permission_denied"}


def test_tc057_a_long_listing_says_it_was_cut_and_by_how_much(world):
    # TC-057
    from abf_platform import jobs
    assert jobs.LIST_LIMIT == 500
    big = world.site.work / "big"
    big.mkdir(exist_ok=True)
    for i in range(jobs.LIST_LIMIT + 50):
        (big / ("f%04d" % i)).write_text("")
    res = listing(world.plat, "lab-a", big)
    assert res["ok"] is True and res["truncated"] is True
    assert res["total"] == 550 and res["count"] == 500 == len(res["entries"]) and res["limit"] == 500
    assert re.search(r"truncated|截斷", res.get("note", ""))


def test_tc058_awkward_file_names_come_back_exactly(world):
    # TC-058
    d = world.site.work / "names"
    d.mkdir(exist_ok=True)
    names = ["with space.txt", "中文檔案.txt", "-leading-dash.txt", "it's.txt", "semi;colon.txt", "$(not-run).txt"]
    for n in names:
        (d / n).write_bytes(os.urandom(3))
    res = listing(world.plat, "lab-a", d)
    assert res["ok"] is True
    got = {e["name"]: e for e in res["entries"]}
    assert set(got) == set(names)
    for n in names:
        assert got[n]["size"] == 3 and abs(iso_epoch(got[n]["modified"]) - os.stat(d / n).st_mtime) <= 1


# ---------------------------------------------------------------------------------------
# User Story 1 on a live platform
# ---------------------------------------------------------------------------------------

def agents_rows(world):
    return world.plat.db_rows("SELECT name, last_seen_at FROM agents ORDER BY name")


def test_tc014_idle_polls_end_quietly_and_keep_the_last_contact_moving(world):
    # TC-014
    seen = set()
    end = time.time() + 4.5
    while time.time() < end:
        seen.update(r[1] for r in agents_rows(world) if r[0] == "agent-a")
        time.sleep(0.25)
    assert len(seen) >= 3, "the last contact did not move with each poll: %r" % sorted(seen)
    out = world.agent.output()
    assert "Traceback" not in out and not re.search(r"cannot reach|stopped:|will not start", out), out


def sockets_of(pid):
    inodes = set()
    for fd in Path("/proc/%d/fd" % pid).iterdir():
        try:
            link = os.readlink(str(fd))
        except OSError:
            continue
        m = re.match(r"socket:\[(\d+)\]", link)
        if m:
            inodes.add(m.group(1))
    found = []
    for fn in ("/proc/net/tcp", "/proc/net/tcp6"):
        if not Path(fn).exists():  # a machine without IPv6 has no tcp6 table; tcp must be there
            assert fn.endswith("tcp6"), fn
            continue
        for ln in Path(fn).read_text().splitlines()[1:]:
            parts = ln.split()
            if parts[9] in inodes:
                found.append({"local": int(parts[1].split(":")[1], 16), "remote": int(parts[2].split(":")[1], 16),
                              "state": parts[3]})
    return found


def test_tc012_the_agent_listens_on_nothing_while_it_works(world):
    # TC-012
    world.site.set("find_sleep", "3")
    result = {}
    th = threading.Thread(target=lambda: result.update(listing(world.plat, "lab-a", world.site.work)))
    th.start()
    socks = []
    try:
        end = time.time() + 4
        while time.time() < end:
            socks += sockets_of(world.agent.proc.pid)
            time.sleep(0.1)
    finally:
        th.join(30)
        world.site.clear("find_sleep")
    assert result.get("ok") is True
    assert [s for s in socks if s["state"] == "01"], "the agent showed no connection to the platform at all"
    assert not [s for s in socks if s["state"] == "0A"], "a listening socket: %r" % (socks,)
    assert all(s["remote"] == world.plat.port for s in socks), socks


def test_tc013_the_platform_only_accepts_connections_and_never_dials_out(world):
    # TC-013
    from abf_platform import compute_envs
    tok = world.plat.agent_token("never-polls")
    r = httpx.post(world.plat.url + "/agent/hello", json={"name": "never-polls", "version": "0.1.0"},
                   headers={"Authorization": "Bearer " + tok})
    assert r.status_code == 200
    compute_envs.create(world.state_db, {"name": "waiting", "platform": "slurm-platform", "agent": "never-polls",
                                         "config": {"workDir": "/data/work", "headQueue": "normal"}}, time.time)
    from abf_platform import jobs
    jobs.enqueue_preflight(world.state_db, "waiting", time.time)
    time.sleep(3.5)
    socks = sockets_of(world.plat.proc.pid)
    assert socks
    assert all(s["local"] == world.plat.port for s in socks), "the platform dialled out: %r" % (socks,)


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGINT])
def test_tc022_a_signal_ends_the_agent_without_waiting_for_the_poll(world, sig):
    # TC-022
    name = "agent-sig-%d" % int(sig)
    a = start_agent(world.plat, world.site, name, world.tmp, env=world.site.agent_env())
    time.sleep(1.2)  # now inside a poll
    t0 = time.time()
    rc = a.stop(sig, timeout=6)
    assert time.time() - t0 <= 5
    assert rc in (0, 143, 130), rc
    assert a.proc.poll() is not None


def test_tc006_a_revoked_token_stops_the_agent_with_the_reason(world):
    # TC-006
    from abf_platform import agents
    a = start_agent(world.plat, world.site, "agent-rev", world.tmp, env=world.site.agent_env())
    try:
        r = world.plat.cli(["agent-token", "revoke", "agent-rev"])
        assert r.returncode == 0, r.stdout + r.stderr
        rc = a.wait(POLL + 5)
        out = a.output()
        assert rc != 0 and re.search(r"revoked|rejected|撤銷|拒絕", out), out
        assert out.count("\n") <= 4
        for path in ("/agent/hello", "/agent/poll", "/agent/result/1"):
            assert httpx.post(world.plat.url + path, json={"name": "agent-rev"},
                              headers={"Authorization": "Bearer " + a.token}).status_code == 401
        views = {v["name"]: v for v in agents.list_agents(world.state_db, time.time() + 3 * H + 5)}
        assert views["agent-rev"]["status"] == "offline"
    finally:
        a.stop()


def test_tc083_the_agent_does_not_depend_on_where_it_was_started(world):
    # TC-083 (every agent here starts in an unrelated folder; a preflight working proves on_site.sh was found)
    assert Path(os.readlink("/proc/%d/cwd" % world.agent.proc.pid)).resolve() == world.site.cwd.resolve()
    assert run_job(world.state_db, "preflight", "lab-a")["ok"] is True


def test_tc083_a_deployment_without_settings_is_refused_before_any_poll(tmp_path):
    # TC-083
    f = FakePlatform()
    try:
        site = FakeSite(tmp_path / "s")
        for label, root in (("missing", tmp_path / "nowhere"), ("no settings file", tmp_path / "empty-root")):
            if label != "missing":
                (tmp_path / "empty-root").mkdir()
            tf = tmp_path / "tok"
            tf.write_text(CANARY_TOKEN + "\n")
            tf.chmod(0o600)
            cmd = [sys.executable, "-m", "abf_station", "run", "--platform", f.url, "--token-file", str(tf),
                   "--deployment", str(root)]
            p = subprocess.run(cmd, env=site.agent_env(), cwd=str(site.cwd), capture_output=True, text=True, timeout=20)
            assert p.returncode != 0
            assert str(root) in p.stdout + p.stderr and re.search(r"env\.yaml|settings", p.stdout + p.stderr), p.stdout + p.stderr
            assert f.count() == 0
    finally:
        f.stop()


def test_tc082_a_windows_shell_is_refused_by_naming_the_missing_capability(tmp_path):
    # TC-082
    site = FakeSite(tmp_path / "s")
    tf = tmp_path / "tok"
    tf.write_text(CANARY_TOKEN + "\n")
    tf.chmod(0o600)
    args = ["--platform", "http://127.0.0.1:9", "--token-file", str(tf), "--deployment", str(site.root)]
    code = ("import sys; sys.platform = 'win32'; from abf_station import cli; sys.exit(cli.main(['run'] + %r))" % (args,))
    p1 = subprocess.run([sys.executable, "-c", code], env=site.agent_env(), cwd=str(site.cwd), capture_output=True,
                        text=True, timeout=30)
    fake_bin = tmp_path / "fake-uname"
    fake_bin.mkdir()
    (fake_bin / "uname").write_text("#!/bin/bash\necho MINGW64_NT-10.0-19045\n")
    (fake_bin / "uname").chmod(0o755)
    env = site.agent_env()
    env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
    p2 = subprocess.run([sys.executable, "-m", "abf_station", "run"] + args, env=env, cwd=str(site.cwd),
                        capture_output=True, text=True, timeout=30)
    for p in (p1, p2):
        text = p.stdout + p.stderr
        assert p.returncode != 0, text
        assert re.search(r"WSL", text) and re.search(r"bash", text), text
        assert not re.search(r"Git Bash|folder|directory", text, re.I), text


# ---------------------------------------------------------------------------------------
# scenarios that need a platform of their own: TC-001, TC-003, TC-004, TC-015, TC-016, TC-019, TC-020, TC-023
#
# They run in threads from the first test of the module on, while the tests of the shared world run one
# after the other; each test below waits for its scenario and shows its failure. A scenario uses no
# process-wide setting: the numbers go to its own platform process, or are handed to the calls explicitly.
# ---------------------------------------------------------------------------------------

def scenario_life(tmp_path):
    """TC-001, TC-003, TC-004: online, killed, back under the same name."""
    site = FakeSite(tmp_path / "s")
    plat = RealPlatform(tmp_path, dict(FAST))
    try:
        tf, token = plat.token_file("agent-life", tmp_path)
        t0 = time.time()
        a = AgentProc(plat.url, tf, site, "agent-life", tmp_path)
        plat.wait_agent_online("agent-life")
        time.sleep(0.5)
        views = plat.mcp_json("list_agents")["agents"]
        t1 = time.time()
        version = subprocess.run([sys.executable, "-m", "abf_station", "--version"], env=pkg_env(), capture_output=True,
                                 text=True).stdout.strip()
        assert len(views) == 1 and views[0]["name"] == "agent-life" and views[0]["status"] == "online"
        assert views[0]["version"] == version and version
        assert t0 - 1 <= iso_epoch(views[0]["last_contact_at"]) <= t1 + 1
        assert iso_epoch(views[0]["last_contact_at"]) > t0 - 0.001
        a.proc.send_signal(signal.SIGKILL)
        a.proc.wait()
        a.log.close()
        time.sleep(POLL + 1)  # a poll the platform still holds for the dead agent is not a contact
        now_view = plat.mcp_json("list_agents")["agents"][0]
        late_view = plat.mcp_json("list_agents", ABF_PLATFORM_CLOCK_OFFSET=3 * H + 5)["agents"][0]
        assert now_view["status"] == "online", "offline is decided by the clock, not by a broken connection"
        assert late_view["status"] == "offline" and late_view["last_contact_at"] == now_view["last_contact_at"]
        first_contact = iso_epoch(late_view["last_contact_at"])
        b = AgentProc(plat.url, tf, site, "agent-life", tmp_path)
        try:
            end = time.time() + 15
            while time.time() < end and not (plat.db_rows("SELECT last_seen_at FROM agents")[0][0] > first_contact + 0.5):
                time.sleep(0.2)
            again = plat.mcp_json("list_agents")["agents"]
            assert len(again) == 1 and again[0]["status"] == "online"
            assert iso_epoch(again[0]["last_contact_at"]) > first_contact
        finally:
            b.stop()
    finally:
        plat.stop()


def scenario_early(tmp_path):
    """TC-020: an agent started before the platform says so, slowly, and connects when the platform comes."""
    site = FakeSite(tmp_path / "s")
    plat = RealPlatform(tmp_path, dict(FAST), start=False)
    tok = plat.agent_token("agent-early")
    tf = tmp_path / "tok"
    tf.write_text(tok + "\n")
    tf.chmod(0o600)
    a = AgentProc(plat.url, tf, site, "agent-early", tmp_path)
    try:
        end = time.time() + 10
        while time.time() < end and plat.url not in a.output():
            time.sleep(0.2)
        assert plat.url in a.output(), a.output()
        assert re.search(r"cannot reach|unreachable|連不上", a.output(), re.I)
        time.sleep(3.5)
        lines = [ln for ln in a.output().splitlines() if plat.url in ln]
        assert len(lines) <= 3, "the agent repeats itself too fast:\n" + a.output()
        assert tok not in a.output()
        plat.start()
        plat.wait_agent_online("agent-early", timeout=40)
        assert a.alive()
    finally:
        a.stop()
        plat.stop()


def scenario_held(tmp_path):
    """TC-015, TC-016: a held poll neither delays a job nor blocks other requests."""
    from helpers import basic_header, load_scenario
    w = World(tmp_path, env={"ABF_AGENT_POLL_SECONDS": 20, "ABF_AGENT_HEARTBEAT_SECONDS": 20}, set_env=False)
    try:
        held_since = time.time()  # the agent now holds a 20 s poll
        time.sleep(1.0)
        plat = w.plat
        r = plat.cli(["token", "new"])
        run_tok = re.search(r"abf_[A-Za-z0-9_-]{20,}", r.stdout).group(0)
        body = load_scenario("ok_run")["requests"][0]["body"]
        t = time.time()
        c = httpx.post(plat.url + "/trace/create", json=body, headers={"Authorization": basic_header(run_tok)})
        assert c.status_code < 300 and time.time() - t < 2
        wid = c.json()["workflowId"]
        t = time.time()
        p = httpx.put(plat.url + "/trace/%s/progress" % wid, json={"progress": {"succeeded": 1}},
                      headers={"Authorization": basic_header(run_tok)})
        assert p.status_code < 300 and time.time() - t < 2
        t = time.time()
        assert httpx.get(plat.url + "/user-info", headers={"Authorization": basic_header(run_tok)}).status_code == 200
        assert time.time() - t < 2
        t = time.time()
        runs = mcp_inproc_json(plat.index, "list_runs")
        assert time.time() - t < 2 and len(runs["runs"]) == 1
        # the poll has been held for more than 5 s by the time this job arrives
        time.sleep(max(0, 6.0 - (time.time() - held_since)))
        t = time.time()
        res = run_job(w.state_db, "list_site_files", "lab-a", w.site.work, offline_after=60)
        elapsed = time.time() - t
        assert res["ok"] is True, res
        assert elapsed < 5, "the job waited for the end of the poll (%.1f s)" % elapsed
    finally:
        w.close()


def last_job(plat):
    return plat.db_rows("SELECT id, state, late_result_json FROM jobs ORDER BY id DESC LIMIT 1")[0]


def wait_for_late_result(plat, job_id, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        row = plat.db_rows("SELECT late_result_json FROM jobs WHERE id = ?", (job_id,))[0]
        if row[0]:
            return row[0]
        time.sleep(0.3)
    raise AssertionError("the busy agent's late answer never arrived")


def scenario_busy(tmp_path):
    """TC-023, TC-019: a busy agent stays online; a silent one is called silent, and its late answer changes nothing."""
    from abf_platform import agents
    w = World(tmp_path, env={"ABF_AGENT_HEARTBEAT_SECONDS": 1, "ABF_AGENT_POLL_SECONDS": 1}, agent_name="agent-w3",
              set_env=False)
    try:
        site = w.site
        # TC-023: a 4 s preflight against a 3 s offline limit (three beats of 1 s)
        site.set("sinfo_sleep", "4")
        done = {}
        th = threading.Thread(target=lambda: done.update(
            run_job(w.state_db, "preflight", "lab-a", deadline=30, offline_after=3)))
        th.start()
        states = []
        t0 = time.time()
        while th.is_alive() and time.time() - t0 < 30:
            states.append(agents.list_agents(w.state_db, time.time(), offline_after=3)[0]["status"])
            time.sleep(0.4)
        th.join()
        site.clear("sinfo_sleep")
        assert done.get("ok") is True and time.time() - t0 >= 3.5, "the preflight did not take the 4 s it should"
        assert len(states) >= 6 and set(states) == {"online"}, states
        assert w.plat.mcp_json("list_agents", **w.env)["agents"][0]["status"] == "online"
        # TC-019: the agent is online but the site command sleeps past the caller's 2 s
        site.set("find_sleep", "4")
        t = time.time()
        res = run_job(w.state_db, "list_site_files", "lab-a", site.work, deadline=2, offline_after=3)
        waited = time.time() - t
        assert res["ok"] is False and res["state"] == "expired" and re.search(r"did not answer|沒有回應", res["message"]), res
        assert "agent-w3" in res["message"] and "list_site_files" in res["message"]
        assert waited <= 2 + 5
        job_id, state, _ = last_job(w.plat)
        assert state == "expired"
        # the busy agent finishes later: its late answer is kept, marked late, and the job stays expired
        wait_for_late_result(w.plat, job_id)
        site.clear("find_sleep")
        assert last_job(w.plat)[1] == "expired"
        # a late pre-flight verdict (here: "invalid") must not touch the environment either
        site.set("queues", "other\n")
        site.set("sinfo_sleep", "4")
        before = ce_of(w.state_db, "lab-a")
        out = run_job(w.state_db, "preflight", "lab-a", deadline=2, offline_after=3)
        assert out["ok"] is False and out["state"] == "expired" and re.search(r"did not answer|沒有回應", out["message"])
        wait_for_late_result(w.plat, last_job(w.plat)[0])
        after = ce_of(w.state_db, "lab-a")
        site.clear("queues")
        site.clear("sinfo_sleep")
        assert after["status"] == before["status"] == "available" and after["message"] == before["message"]
        assert after["lastUpdated"] == before["lastUpdated"]
    finally:
        w.close()


class Side:
    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=4)
        self.futures = {}

    def start(self, name, fn, tmp):
        self.futures[name] = self.pool.submit(fn, tmp)

    def result(self, name):
        return self.futures[name].result(timeout=240)


@pytest.fixture(scope="module", autouse=True)
def side(tmp_path_factory):
    s = Side()
    for name, fn in (("life", scenario_life), ("early", scenario_early), ("held", scenario_held),
                     ("busy", scenario_busy)):
        s.start(name, fn, tmp_path_factory.mktemp(name))
    yield s
    s.pool.shutdown(wait=True)


def test_tc001_tc003_tc004_online_then_killed_then_back_with_the_same_name(side):
    # TC-001, TC-003, TC-004
    side.result("life")


def test_tc020_an_agent_started_before_the_platform_says_so_slowly_and_then_connects(side):
    # TC-020
    side.result("early")


def test_tc015_tc016_a_held_poll_neither_delays_a_job_nor_blocks_other_requests(side):
    # TC-015, TC-016
    side.result("held")


def test_tc023_tc019_a_busy_agent_stays_online_and_a_silent_one_is_called_silent(side):
    # TC-023, TC-019
    side.result("busy")


# ---------------------------------------------------------------------------------------
# reach: ssh through a fake ssh: TC-045, TC-046, TC-087
# ---------------------------------------------------------------------------------------

def test_tc045_tc046_tc087_ssh_site_failures_are_told_in_the_site_scripts_own_words(world, tmp_path):
    # TC-045, TC-046, TC-087
    s = FakeSite(tmp_path / "ssh-site", reach="ssh")
    agent = start_agent(world.plat, s, "agent-ssh", tmp_path, env=s.agent_env(ON_SITE_TIMEOUT=3))
    try:
        r = world.plat.create_ce(s, "lab-ssh", agent="agent-ssh")
        assert r.returncode == 0, r.stdout + r.stderr
        world.plat.wait_ce("lab-ssh", "available", timeout=40)
        # TC-045: the master connection is not open
        s.set("ssh_mode", "nomaster")
        env = dict(os.environ, LAB_SETTINGS_FILE=str(s.settings), ON_SITE_SSH_BIN=str(s.ssh_bin),
                   PATH=s.agent_env()["PATH"], HOME=str(s.home), ON_SITE_TIMEOUT="3")
        direct = subprocess.run(["bash", str(REPO_ROOT / "scripts" / "on_site.sh"), "--check-reach"], env=env,
                                capture_output=True, text=True, timeout=30)
        open_line = [ln.strip() for ln in direct.stderr.splitlines() if re.match(r"^\s+ssh -o ControlMaster", ln)]
        assert open_line, direct.stderr
        t = time.time()
        out = run_job(world.state_db, "preflight", "lab-ssh")
        assert time.time() - t < 15
        v = verdicts(out)
        assert v["connect"] == "fail" and set(v.values()) <= {"fail", "unchecked"} and list(v.values()).count("fail") == 1
        detail = [c for c in out["result"]["checks"] if c["name"] == "connect"][0]["detail"]
        assert open_line[0] in detail and re.search(r"WSL", detail), detail
        assert ce_of(world.state_db, "lab-ssh")["status"] == "invalid"
        # TC-046: the master answers a ping but a session hangs (all sessions in use)
        s.set("ssh_mode", "hang")
        out = run_job(world.state_db, "preflight", "lab-ssh")
        detail = [c for c in out["result"]["checks"] if c["name"] == "connect"][0]["detail"]
        assert re.search(r"session|工作階段", detail) and not re.search(r"queue|佇列", detail), detail
        # TC-087: the connection is lost in the middle of a listing
        s.set("ssh_mode", "ok")
        assert run_job(world.state_db, "preflight", "lab-ssh")["ok"] is True
        s.set("ssh_drop_after", "1")
        res = listing(world.plat, "lab-ssh", s.work)
        assert res["ok"] is False
        assert re.search(r"ControlMaster", res["message"]) and re.search(r"WSL", res["message"]), res
        assert agent.alive()
        s.clear("ssh_drop_after")
        s.clear("ssh_down")
        assert listing(world.plat, "lab-ssh", s.work)["ok"] is True
        assert "passphrase" not in agent.output().lower() and "password" not in agent.output().lower()
    finally:
        agent.stop()


# ---------------------------------------------------------------------------------------
# the end of the module: what no flow above may have done (TC-064, TC-065, TC-070)
# ---------------------------------------------------------------------------------------

def test_tc064_the_site_saw_no_dangerous_call_and_the_guard_files_are_unchanged(world):
    # TC-064
    calls = world.site.calls()
    assert calls, "the fake site was never called, so nothing was shown"
    assert world.site.dangerous() == [], world.site.dangerous()
    assert not [c for c in calls if re.match(r"(scancel|srun|qsub|bsub)\b", c)]
    assert world.site.guards_intact()


def test_tc065_no_secret_of_the_site_or_the_agent_is_anywhere_on_the_platform(world, tmp_path):
    # TC-065
    plat = world.plat
    canaries = [b"CANARY_agent_connection_91ab", b"CANARY_tw_token_77cd", b"CANARYENV_5a7d41", b"CANARYKEY_5c1e8b"]
    tokens = [t.encode() for t in world.tokens.values()]
    rej = plat.cli(["ce", "create", "--name", "bad", "--platform", "slurm-platform", "--work-dir", "/data/work",
                    "--head-queue", "normal", "--env", "AWS_SECRET_ACCESS_KEY=CANARYCE_00aa"])
    assert rej.returncode != 0
    shown = [rej.stdout, rej.stderr]
    for args in (["ce", "list"], ["ce", "show", "lab-a"]):
        r = plat.cli(args)
        shown += [r.stdout, r.stderr]
    shown.append(repr(mcp_inproc_json(plat.index, "list_compute_envs")))
    shown.append(repr(mcp_inproc_json(plat.index, "list_agents")))
    shown.append(repr(mcp_inproc_json(plat.index, "get_compute_env", {"name": "lab-a"})))
    for path in ("/", "/user-info", "/agent/hello", "/agent/poll", "/trace/create", "/nothing"):
        r = httpx.get(plat.url + path)
        shown.append(r.text)
    blob = db_bytes(plat.index, plat.tokens, plat.state_db) + plat.log.read_bytes() + "\n".join(shown).encode()
    for c in canaries + tokens + [b"CANARYCE_00aa"]:
        assert c not in blob, c
    assert b"site-login" in db_bytes(plat.state_db), "the credential NAME is kept"


def test_tc070_the_agent_leaves_no_file_behind_and_does_not_read_the_private_key(world):
    # TC-070 (everything above has run with HOME, the working folder and TMPDIR empty at the start)
    site = world.site
    assert sorted(p.name for p in site.cwd.iterdir()) == []
    assert sorted(p.name for p in site.tmpdir.iterdir()) == []
    assert sorted(str(p.relative_to(site.home)) for p in site.home.rglob("*")) == [".ssh", ".ssh/id_test"]
    assert os.stat(site.key).st_atime_ns == site.key_atime, "the private key was read"
