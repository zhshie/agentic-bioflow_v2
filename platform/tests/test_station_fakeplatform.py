# Nothing existing: tests that hand the real agent hostile or malformed jobs through a fake platform; the protocol is ours.
"""The real agent against a fake platform: refusals, token file rules, URL rules (feature 007)."""
import contextlib
import os
import re
import signal
import stat
import time

import pytest

from station_harness import (AgentProc, CANARY_TOKEN, FakePlatform, FakeSite, Inproc, ce_snapshot, write_exec)

REFUSAL = re.compile(r"not supported|unsupported|不支援")


@pytest.fixture
def site(tmp_path):
    return FakeSite(tmp_path / "s")


@pytest.fixture
def fake():
    f = FakePlatform()
    yield f
    f.stop()


@contextlib.contextmanager
def agent_on(fake, site, tmp_path, token=CANARY_TOKEN, mode=0o600, name="agent-f", url=None, env_extra=None,
             site_env=None, extra_args=()):
    tf = tmp_path / "tokenfile"
    tf.write_text(token + "\n")
    tf.chmod(mode)
    a = AgentProc(url or fake.url, tf, site, name, tmp_path, extra_args=extra_args, env_extra=env_extra,
                  env=site_env)
    try:
        yield a
    finally:
        a.stop()


def wait_for(fn, timeout=15, what="condition"):
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(0.1)
    raise AssertionError("timed out waiting for " + what)


def list_args(site, path):
    return {"ce": ce_snapshot(site), "path": path}


def assert_site_untouched(site):
    assert site.dangerous() == [], site.dangerous()
    assert site.guards_intact()


def test_tc005_a_401_stops_the_agent_with_one_line_and_no_retry_storm(tmp_path, site):
    # TC-005
    f = FakePlatform(always_status=401)
    try:
        with agent_on(f, site, tmp_path) as a:
            rc = a.wait(10)
            out = a.output()
        assert rc != 0
        assert re.search(r"rejected|revoked|refused|拒絕|撤銷", out), out
        assert len([ln for ln in out.splitlines() if ln.strip()]) <= 3, out
        assert f.count() <= 2
        assert CANARY_TOKEN not in out
    finally:
        f.stop()


def test_tc021_only_a_local_address_may_use_plain_http(tmp_path, site, fake):
    # TC-021
    port = fake.port
    # local plain HTTP is allowed: 127.0.0.1 and localhost reach the fake platform
    for host in ("127.0.0.1", "localhost"):
        before = fake.count("hello")
        with agent_on(fake, site, tmp_path, url="http://%s:%d" % (host, port)) as a:
            wait_for(lambda: fake.count("hello") > before, what="a hello over http://" + host)
    # HTTPS to a name is not stopped by the plain-HTTP rule: it tries to connect and keeps trying
    with agent_on(fake, site, tmp_path, url="https://localhost:%d" % port) as a:
        time.sleep(3)
        assert a.alive()
        out = a.output()
        assert not re.search(r"plain|clear text|明文", out), out
        assert re.search(r"cannot reach|unreachable|連不上|connect", out, re.I), out
    # plain HTTP to anything else is refused at once, before any request
    n = fake.count()
    with agent_on(fake, site, tmp_path, url="http://lab-platform.example.org:%d" % port) as a:
        rc = a.wait(5)
        out = a.output()
    assert rc != 0
    assert re.search(r"HTTPS|https", out) and re.search(r"plain|clear|明文", out), out
    assert fake.count() == n, "the refused start sent a request"


@pytest.mark.parametrize("path", ["{w}/../x", "{w}/a/../../etc", "..", "{w}/.."])
def test_tc054_the_agent_refuses_dot_dot_paths_by_itself(tmp_path, site, fake, path):
    # TC-054 (the agent's lock; the platform's lock is in test_tc054_the_platform_refuses_dot_dot_paths_first)
    with agent_on(fake, site, tmp_path) as a:
        jid = fake.push("list_site_files", list_args(site, path.format(w=site.work)))
        res = fake.wait_result(jid)
        assert res["state"] == "refused"
        assert ".." in res["result"]["message"]
        assert "site:" not in a.output(), "a refused path must not reach the site"
        assert a.alive()


def test_tc054_the_platform_refuses_dot_dot_paths_first(tmp_path, monkeypatch, site):
    # TC-054 (the platform's lock): nothing is queued
    ip = Inproc(tmp_path / "ip", monkeypatch)
    from abf_platform import agents
    assert ip.run("ce", "create", "--name", "lab-a", "--platform", "slurm-platform", "--agent", "a1",
                  "--work-dir", str(site.work), "--head-queue", "normal")[0] == 0
    agents.register(ip.state_db, "a1", "0.1.0", time.time)
    from test_station_envs import make_available
    make_available(ip, "lab-a")
    n = len(ip.rows()["jobs"])
    for p in (str(site.work) + "/../x", str(site.work) + "/a/../../etc", "..", str(site.work) + "/.."):
        res = ip.mcp_json("list_site_files", {"compute_env": "lab-a", "path": p})
        assert res["ok"] is False and ".." in res["message"], res
    assert len(ip.rows()["jobs"]) == n


BAD_CHARS = ["{w}/x; touch {c}", "{w}/x && touch {c}", "{w}/$(touch {c})", "{w}/`touch {c}`", "{w}/a|b",
             "{w}/a\nb", "{w}/*", "{w}/?", "~", "{w}/a>b", "{w}/a<b", "{w}/a b", "{w}/a'b", '{w}/a"b', "{w}/a\\b",
             "{w}/a{{b}}", "{w}/a#b", "{w}/a!b", "{w}/a(b)"]


def test_tc055_shell_characters_in_a_path_never_run_through_either_lock(tmp_path, site, fake, monkeypatch):
    # TC-055
    canary = tmp_path / "canary-file-that-must-not-exist"
    paths = [p.format(w=site.work, c=canary) for p in BAD_CHARS]
    with agent_on(fake, site, tmp_path) as a:
        ids = [fake.push("list_site_files", list_args(site, p)) for p in paths]
        for jid in ids:
            res = fake.wait_result(jid)
            assert res["state"] == "refused", res
            assert re.search(r"not allowed|不允許", res["result"]["message"]), res
        assert "site:" not in a.output()
    assert not canary.exists()
    # the platform's lock
    ip = Inproc(tmp_path / "ip", monkeypatch)
    from abf_platform import agents
    from test_station_envs import make_available
    assert ip.run("ce", "create", "--name", "lab-a", "--platform", "slurm-platform", "--agent", "a1",
                  "--work-dir", str(site.work), "--head-queue", "normal")[0] == 0
    agents.register(ip.state_db, "a1", "0.1.0", time.time)
    make_available(ip, "lab-a")
    n = len(ip.rows()["jobs"])
    for p in paths:
        res = ip.mcp_json("list_site_files", {"compute_env": "lab-a", "path": p})
        assert res["ok"] is False and re.search(r"not allowed|不允許", res["message"]), (p, res)
    assert len(ip.rows()["jobs"]) == n
    assert not canary.exists()


KINDS = ["rm", "delete", "mv", "move", "scancel", "shell", "run_command", "exec", "write_file", "sbatch", "launch",
         "cleanup", "", None]


def test_tc060_tc084_every_job_kind_outside_the_list_is_refused_and_the_agent_carries_on(tmp_path, site, fake):
    # TC-060, TC-084 (launch is among the kinds)
    with agent_on(fake, site, tmp_path) as a:
        ids = [fake.push_raw({"kind": k, "args": {"ce": ce_snapshot(site), "path": str(site.storage / "rawdata")}})
               for k in KINDS]
        for k, jid in zip(KINDS, ids):
            res = fake.wait_result(jid)
            assert res["state"] == "refused", (k, res)
            assert REFUSAL.search(res["result"]["message"]), (k, res)
        good = fake.push("list_site_files", list_args(site, str(site.storage / "rawdata")))
        res = fake.wait_result(good)
        assert res["state"] == "done" and res["result"]["ok"] is True
        assert a.alive()
    assert_site_untouched(site)


def test_tc061_odd_spellings_and_odd_arguments_are_refused_and_never_executed(tmp_path, site, fake):
    # TC-061
    rawdata = str(site.storage / "rawdata")
    with agent_on(fake, site, tmp_path) as a:
        odd_kinds = ["List_Site_Files", " list_site_files", "list_site_files\n", "preflight;rm -rf x",
                     "LIST_SITE_FILES", "list_site_files ", "preflight\u0000"]
        for k in odd_kinds:
            res = fake.wait_result(fake.push(k, list_args(site, rawdata)))
            assert res["state"] == "refused", (k, res)
        bad_args = [
            {"ce": ce_snapshot(site), "path": rawdata, "cmd": "rm -rf " + rawdata},
            {"ce": ce_snapshot(site), "path": [rawdata]},
            {"ce": ce_snapshot(site), "path": 123},
            {"ce": ce_snapshot(site), "path": None},
            {"ce": ce_snapshot(site)},
            {"ce": ce_snapshot(site), "path": rawdata + "/" + "a" * 5000},
            {"path": rawdata},
            {"ce": "lab-a", "path": rawdata},
        ]
        for args in bad_args:
            res = fake.wait_result(fake.push("list_site_files", args))
            assert res["state"] in ("refused", "done"), res
            if args.get("cmd"):
                assert_site_untouched(site)
            elif res["state"] == "done":
                raise AssertionError("malformed arguments were accepted: %r" % (args,))
        for odd in ("a string", ["a", "list"], 7, None):
            res = fake.wait_result(fake.push_raw({"kind": "list_site_files", "args": odd}))
            assert res["state"] == "refused", (odd, res)
        assert fake.wait_result(fake.push("list_site_files", list_args(site, rawdata)))["state"] == "done"
        assert a.alive()
    assert_site_untouched(site)


def test_tc062_hostile_values_in_the_environment_are_not_run(tmp_path, site, fake):
    # TC-062
    canary = tmp_path / "canary-62"
    with agent_on(fake, site, tmp_path) as a:
        for over in ({"headQueue": "normal; touch %s" % canary},
                     {"workDir": "/x$(touch %s)" % canary},
                     {"computeQueue": "`touch %s`" % canary},
                     {"headQueue": "normal", "version": "$(touch %s)" % canary, "workDir": str(site.work)}):
            jid = fake.push("preflight", {"ce": ce_snapshot(site, **over)})
            res = fake.wait_result(jid)
            assert res["state"] in ("refused", "done")
            if over.get("version"):
                continue
            bad_names = [c["name"] for c in res["result"].get("checks", []) if c["status"] == "fail"] \
                if res["state"] == "done" else ["refused"]
            assert bad_names, res
        assert a.alive()
    assert not canary.exists()


def test_tc067_the_token_is_nowhere_in_output_arguments_or_what_a_site_command_sees(tmp_path, site, fake):
    # TC-067 (normal start, a 401, an unreachable platform, SIGTERM; and the cmdline and the child environment)
    outputs = []
    with agent_on(fake, site, tmp_path) as a:
        wait_for(lambda: fake.count("hello"), what="hello")
        cmdline = open("/proc/%d/cmdline" % a.proc.pid, "rb").read().decode(errors="replace")
        assert CANARY_TOKEN not in cmdline and str(a.cmd[a.cmd.index("--token-file") + 1]) in cmdline
        jid = fake.push("preflight", {"ce": ce_snapshot(site)})
        fake.wait_result(jid)
        a.stop(signal.SIGTERM)
        outputs.append(a.output())
    env_seen = (site.state / "sinfo_env.txt").read_text()
    assert CANARY_TOKEN not in env_seen
    f401 = FakePlatform(always_status=401)
    try:
        with agent_on(f401, site, tmp_path) as a:
            a.wait(10)
            outputs.append(a.output())
    finally:
        f401.stop()
    dead = FakePlatform()
    url = dead.url
    dead.stop()
    with agent_on(dead, site, tmp_path, url=url) as a:
        time.sleep(3)
        a.stop(signal.SIGTERM)
        outputs.append(a.output())
    for out in outputs:
        assert CANARY_TOKEN not in out


@pytest.mark.parametrize("mode,ok", [(0o600, True), (0o640, False), (0o644, False), (0o660, False), (0o604, False)])
def test_tc068_a_token_file_others_can_read_is_refused_before_any_request(tmp_path, site, fake, mode, ok):
    # TC-068
    with agent_on(fake, site, tmp_path, mode=mode) as a:
        if ok:
            wait_for(lambda: fake.count("hello"), what="hello with a 0600 token file")
            assert a.alive()
        else:
            rc = a.wait(8)
            out = a.output()
            assert rc != 0
            assert str(tmp_path / "tokenfile") in out and "chmod 600" in out, out
            assert fake.count() == 0
            assert CANARY_TOKEN not in out


@pytest.mark.parametrize("content,want", [(None, r"not found|找不到|does not exist"), ("", r"empty|空"), ("  \n\t\n", r"empty|空")])
def test_tc069_a_missing_or_empty_token_file_is_refused(tmp_path, site, fake, content, want):
    # TC-069
    tf = tmp_path / "tokenfile"
    if content is not None:
        tf.write_text(content)
        tf.chmod(0o600)
    a = AgentProc(fake.url, tf, site, "agent-f", tmp_path)
    try:
        rc = a.wait(8)
        out = a.output()
    finally:
        a.stop()
    assert rc != 0 and re.search(want, out, re.I), out
    assert fake.count() == 0


@pytest.mark.parametrize("fstype,ok", [("drvfs", False), ("9p", False), ("ext4", True), ("tmpfs", True)])
def test_tc097_a_token_file_on_a_windows_drive_mount_is_refused(tmp_path, site, fake, fstype, ok):
    # TC-097
    mounts = tmp_path / "mounts"
    mounts.write_text("/dev/sda1 / ext4 rw,relatime 0 0\nproc /proc proc rw 0 0\n"
                      "%s %s %s rw,noatime 0 0\n" % ("C:\\134" if fstype == "drvfs" else "none", os.path.realpath(str(tmp_path)), fstype))
    with agent_on(fake, site, tmp_path, env_extra={"ABF_STATION_MOUNTS_FILE": str(mounts)}) as a:
        if ok:
            wait_for(lambda: fake.count("hello"), what="hello on " + fstype)
        else:
            rc = a.wait(8)
            out = a.output()
            assert rc != 0
            assert str(tmp_path / "tokenfile") in out
            assert re.search(r"Windows|drvfs|9p", out) and re.search(r"home|WSL", out), out
            assert fake.count() == 0 and CANARY_TOKEN not in out


def test_tc097_a_missing_mount_table_fails_the_check_instead_of_passing_over_it(tmp_path, site, fake):
    # TC-097
    with agent_on(fake, site, tmp_path, env_extra={"ABF_STATION_MOUNTS_FILE": str(tmp_path / "no-such-mounts")}) as a:
        rc = a.wait(8)
        out = a.output()
    assert rc != 0 and re.search(r"mount", out, re.I), out
    assert fake.count() == 0


COMMAND_BAD_WORDS = re.compile(r"\b(rm|mv|cp|touch|mkdir|tee|dd|chmod|chown|ln|kill|scancel|srun|qsub|bsub)\b")


def command_lines(out):
    """The `local<TAB>command` / `ssh host<TAB>command` lines on_site.sh printed, as the agent relays them."""
    lines = []
    for ln in out.splitlines():
        if ln.startswith("site-output: "):
            body = ln[len("site-output: "):]
            if "\t" in body:
                lines.append(body)
    return lines


def check_vocabulary(lines):
    assert lines, "the agent showed no command line, so there is nothing to check"
    for ln in lines:
        cmd = ln.split("\t", 1)[1]
        assert not COMMAND_BAD_WORDS.search(cmd), ln
        assert not re.search(r">>?\s*(?!/dev/null)\S", cmd.replace("2>&1", "")), ln
        for m in re.finditer(r"\bsbatch\b(.*)", cmd):
            assert cmd[:m.start()].rstrip().endswith("command -v") or m.group(1).strip() in ("--version", "-V"), ln
        for m in re.finditer(r"\bnextflow\b(.*)", cmd):
            assert m.group(1).strip().startswith("-version") or cmd[:m.start()].rstrip().endswith("command -v"), ln


def test_tc050_the_site_commands_are_a_small_fixed_vocabulary_over_local_reach(tmp_path, site, fake):
    # TC-050 (reach: local, ON_SITE_DRY_RUN prints instead of running)
    with agent_on(fake, site, tmp_path, env_extra={"ON_SITE_DRY_RUN": "1"}) as a:
        fake.wait_result(fake.push("preflight", {"ce": ce_snapshot(site)}))
        fake.wait_result(fake.push("list_site_files", list_args(site, str(site.storage / "rawdata"))))
        out = a.output()
    check_vocabulary(command_lines(out))
    assert all(ln.startswith("local\t") for ln in command_lines(out))
    assert site.calls() == []


def test_tc050_over_ssh_reach_only_the_override_binary_is_used_never_ssh_from_path(tmp_path, fake):
    # TC-050 (reach: ssh)
    s = FakeSite(tmp_path / "ssh-site", reach="ssh")
    with agent_on(fake, s, tmp_path, env_extra={"ON_SITE_DRY_RUN": "1"}) as a:
        fake.wait_result(fake.push("preflight", {"ce": ce_snapshot(s)}))
        fake.wait_result(fake.push("list_site_files", list_args(s, str(s.storage / "rawdata"))))
        out = a.output()
    lines = command_lines(out)
    check_vocabulary(lines)
    assert all(ln.startswith("ssh tester@fake.example\t") for ln in lines), lines
    assert not [c for c in s.calls() if c.startswith("ssh")], "the ssh on PATH was called"


def test_the_agent_refuses_a_sibling_prefix_and_other_places_but_lists_inside_the_roots(tmp_path, site, fake):
    # TC-052, TC-053 at the agent's own lock (the end-to-end version is in test_station_e2e.py)
    inside = [str(site.work), str(site.work) + "/", str(site.launch), str(site.storage), str(site.storage / "rawdata")]
    outside = ["/etc", "/", str(site.site), str(site.evil), "relative/dir", str(site.work)[:-1]]
    with agent_on(fake, site, tmp_path) as a:
        for p in inside:
            res = fake.wait_result(fake.push("list_site_files", list_args(site, p)))
            assert res["state"] == "done" and res["result"]["ok"] is True, (p, res)
        seen = a.output().count("site:")
        for p in outside:
            res = fake.wait_result(fake.push("list_site_files", list_args(site, p)))
            assert res["state"] == "refused", (p, res)
            assert re.search(r"outside|範圍之外|不在允許", res["result"]["message"]), (p, res)
        assert a.output().count("site:") == seen
