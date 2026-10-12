# Nothing existing: tests of the way back from the cluster to the platform (the reverse forward in scripts/on_site.sh and the agent's check of every hop of it), with a fake ssh and a fake site; the repository's tests do not open forwards.
"""The reverse forward and the hop-by-hop preflight of a launch (feature 007b, FR-005, FR-006)."""
import os
import re
import stat
import subprocess
import sys

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT, pkg_env
from station_harness import FakePlatform, FakeSite
from test_station_fakeplatform import agent_on, wait_for
from test_station_launch import ACCT, TOKEN, bundle_for, job_of, run_job

ON_SITE = REPO_ROOT / "scripts" / "on_site.sh"
INSTANCE = "inst-0123456789abcdef"
PROXY = "http://login.example:18080"


@pytest.fixture
def site(tmp_path):
    s = FakeSite(tmp_path / "s", reach="ssh", account=ACCT, site_user="tester", destructive_log=True)
    (s.storage / "cache").mkdir()
    (s.storage / "rawdata" / "s1.fq").write_text("x")
    s.set("instance_id", INSTANCE)
    return s


@pytest.fixture
def fake():
    f = FakePlatform()
    f.hello_reply = dict(f.hello_reply, instance=INSTANCE)
    yield f
    f.stop()


def on_site(site, *args, input=None):
    env = dict(os.environ, LAB_SETTINGS_FILE=str(site.settings), ON_SITE_SSH_BIN=str(site.ssh_bin), PATH=site.agent_env()["PATH"],
               HOME=str(site.home))
    env.pop("ON_SITE_DRY_RUN", None)
    return subprocess.run(["bash", str(ON_SITE)] + list(args), env=env, capture_output=True, text=True, input=input, timeout=60)


def personal(site):
    return site.root / "_personal"


# ---- on_site.sh: --forward, --unforward, --check-forward ----------------------------------------------------------

def test_tc038_forward_asks_sshd_for_a_loopback_port_and_records_it_privately(site):
    r = on_site(site, "--forward", "8787")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "41234"
    forwards = [c for c in site.ssh_calls() if "-O forward" in c]
    assert len(forwards) == 1 and "-R 127.0.0.1:0:127.0.0.1:8787" in forwards[0]
    assert "0.0.0.0" not in forwards[0] and " -R *" not in forwards[0]
    pf = personal(site) / "forward_port"
    assert pf.read_text().strip() == "41234" and stat.S_IMODE(pf.stat().st_mode) == 0o600
    assert (personal(site) / "forward_state").exists()


def test_tc038_check_forward_says_yes_only_for_the_connection_the_forward_was_made_on(site):
    assert on_site(site, "--check-forward").returncode == 1                        # nothing recorded
    assert on_site(site, "--forward", "8787").returncode == 0
    r = on_site(site, "--check-forward")
    assert r.returncode == 0 and r.stdout.strip() == "41234"
    site.set("master_pid", "9999")                                                   # the master was replaced
    r = on_site(site, "--check-forward")
    assert r.returncode == 1 and "another connection" in r.stderr
    site.set("ssh_mode", "nomaster")
    r = on_site(site, "--check-forward")
    assert r.returncode == 2 and "needs-human reason=no-master" in r.stderr


def test_tc038_unforward_cancels_the_forward_and_removes_the_records(site):
    on_site(site, "--forward", "8787")
    r = on_site(site, "--unforward")
    assert r.returncode == 0, r.stderr
    cancels = [c for c in site.ssh_calls() if "-O cancel" in c]
    assert len(cancels) == 1 and "-R 127.0.0.1:41234:127.0.0.1:8787" in cancels[0]
    assert not (personal(site) / "forward_port").exists() and not (personal(site) / "forward_state").exists()
    assert on_site(site, "--check-forward").returncode == 1


def test_tc038_a_forward_that_sshd_refuses_is_reported_and_leaves_no_record(site):
    site.set("fwd_fail", "1")
    r = on_site(site, "--forward", "8787")
    assert r.returncode != 0 and re.search(r"forward", r.stderr)
    assert not (personal(site) / "forward_port").exists()
    assert on_site(site, "--forward", "notaport").returncode != 0
    assert on_site(site, "--forward", "0").returncode != 0
    assert on_site(site, "--forward", "70000").returncode != 0


def test_tc038_over_local_reach_there_is_no_forward_to_open(tmp_path):
    s = FakeSite(tmp_path / "l", reach="local")
    env = dict(os.environ, LAB_SETTINGS_FILE=str(s.settings), PATH=s.agent_env()["PATH"])
    r = subprocess.run(["bash", str(ON_SITE), "--forward", "8787"], env=env, capture_output=True, text=True)
    assert r.returncode == 3 and "local" in r.stderr
    assert not (s.root / "_personal").exists()


def test_tc038_on_site_gained_no_background_process_and_no_loop():
    # the section of on_site.sh that feature 007b added (between its two markers) starts nothing in the background and loops over nothing
    text = ON_SITE.read_text()
    section = text[text.index("# --- the reverse forward (feature 007b)"):text.index('if [ "$MODE" = check ]; then')]
    code = [ln for ln in section.splitlines() if not ln.lstrip().startswith("#")]
    bad = [ln for ln in code if re.search(r"nohup|setsid|disown|crontab|\bwhile\b|\buntil\b|\bsleep\b|[^&]&\s*$|[^&>]&\s+[^&>]", ln)]
    assert code and bad == [], bad
    head = text[:text.index("# --- the reverse forward (feature 007b)")]
    assert head.count("--forward") >= 2 and "while" not in section


# ---- the agent: one forward for every launch, and every hop checked --------------------------------------------------

def ssh_site_job(site, fake, run, **over):
    env = [{"name": "NXF_SINGULARITY_CACHEDIR", "value": str(site.storage / "cache"), "head": True, "compute": False},
           {"name": "http_proxy", "value": PROXY, "head": True, "compute": True},
           {"name": "NXF_OPTS", "value": "-Dhttp.proxyHost=login.example -Dhttp.proxyPort=18080", "head": True, "compute": False}]
    forward = str(site.storage / "_relay" / "forward_port")
    return job_of(bundle_for(site, fake, run=run, ce={"environment": env},
                             facts={"reach": "ssh", "platform_local": True, "forward_file": forward}, **over))


def launch(site, fake, tmp_path, runs, **kw):
    out = []
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        wait_for(lambda: fake.count("hello"))
        for run in runs:
            out.append(run_job(fake, ssh_site_job(site, fake, run, **kw)))
        text = a.output()
    return out, text


def test_tc038_tc012_two_launches_share_one_forward_and_both_files_hold_its_port(tmp_path, site, fake):
    (a, b), out = launch(site, fake, tmp_path, ["run-a", "run-b"])
    assert a["state"] == "done" and b["state"] == "done", (a, b)
    forwards = [c for c in site.ssh_calls() if "-O forward" in c]
    assert len(forwards) == 1 and "-R 127.0.0.1:0:127.0.0.1:%d" % fake.port in forwards[0]
    assert [c for c in site.ssh_calls() if "-O check" in c], "the forward was looked for before it was made"
    assert (personal(site) / "forward_port").read_text().strip() == "41234"
    relay_file = site.storage / "_relay" / "forward_port"
    assert relay_file.read_text().strip() == "41234" and stat.S_IMODE(relay_file.stat().st_mode) == 0o600
    inst_file = site.storage / "_relay" / "forward_instance"
    assert inst_file.read_text().strip() == INSTANCE and stat.S_IMODE(inst_file.stat().st_mode) == 0o600
    scripts = site.scripts()
    assert len(scripts) == 2 and all(str(relay_file) in s for s in scripts)
    assert all("-Dhttp.nonProxyHosts=" in s for s in scripts)
    assert [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")] == []
    assert not [c for c in site.ssh_calls() if "-O cancel" in c], "nothing cancels the forward by itself"


def test_tc037_every_hop_is_probed_without_a_token_and_the_answer_must_carry_this_platforms_id(tmp_path, site, fake):
    (res,), _ = launch(site, fake, tmp_path, ["run-a"])
    assert res["state"] == "done"
    curls = [c for c in site.calls() if c.startswith("curl")]
    assert len(curls) == 2
    assert "-x" not in curls[0].split() and "-x %s" % PROXY in curls[1]
    for c in curls:
        assert "http://127.0.0.1:41234/user-info" in c
        assert TOKEN not in c and not re.search(r"(?i)authorization|bearer|token", c)


@pytest.mark.parametrize("mode,keyword", [
    ("nomaster", r"WSL|共用連線|ControlPath"),
    ("direct-refused", r"反向通道沒開"),
    ("relay-refused", r"relay.*(沒在跑|start)|egress_ctl\.sh start"),
    ("relay-403", r"請重啟 relay.*egress_ctl\.sh restart"),
    ("direct-silent", r"平台沒有回應"),
    ("relay-502", r"平台沒有回應"),
    ("relay-wrongid", r"別的程式|佔用"),
    ("direct-other", r"別的程式|佔用"),
])
def test_tc037_each_broken_hop_is_named_with_its_own_fix_and_nothing_is_made(tmp_path, site, fake, mode, keyword):
    if mode == "nomaster":
        site.set("ssh_mode", "nomaster")
    else:
        hop, how = mode.split("-")
        site.set("curl_" + ("direct" if hop == "direct" else "proxy"),
                 {"refused": "refused", "silent": "silent", "403": "e403", "502": "e502", "wrongid": "wrongid", "other": "other"}[how])
    (res,), _ = launch(site, fake, tmp_path, ["run-a"])
    assert res["state"] == "refused", res
    assert re.search(keyword, res["result"]["message"]), res["result"]["message"]
    assert not (site.work / "runs").exists()
    assert not [c for c in site.calls() if c.startswith("sbatch")]
    assert not [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")]


def test_tc037_the_two_messages_for_a_closed_tunnel_and_a_silent_platform_differ(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        wait_for(lambda: fake.count("hello"))
        site.set("curl_direct", "refused")
        a = run_job(fake, ssh_site_job(site, fake, "run-a"))
        site.set("curl_direct", "silent")
        b = run_job(fake, ssh_site_job(site, fake, "run-b"))
    assert a["result"]["message"] != b["result"]["message"]


def test_tc037_a_forward_that_cannot_be_made_is_a_refusal_with_the_reason(tmp_path, site, fake):
    site.set("fwd_fail", "1")
    (res,), _ = launch(site, fake, tmp_path, ["run-a"])
    assert res["state"] == "refused" and re.search(r"forward|反向通道", res["result"]["message"]), res
    assert not (site.work / "runs").exists()


def test_tc038_abf_station_unforward_cancels_and_removes_both_files(tmp_path, site, fake):
    (res,), _ = launch(site, fake, tmp_path, ["run-a"])
    assert res["state"] == "done"
    env = dict(site.agent_env(), PYTHONPATH=str(PLATFORM_DIR))
    r = subprocess.run([sys.executable, "-m", "abf_station", "unforward", "--deployment", str(site.root)], env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert [c for c in site.ssh_calls() if "-O cancel" in c]
    assert not (personal(site) / "forward_port").exists()
    assert not (site.storage / "_relay" / "forward_port").exists()
    assert not (site.storage / "_relay" / "forward_instance").exists()


def test_tc064_after_the_shared_connection_ends_nothing_rebuilds_the_forward(tmp_path, site, fake):
    (res,), _ = launch(site, fake, tmp_path, ["run-a"])
    n = len([c for c in site.ssh_calls() if "-O forward" in c])
    site.set("ssh_down", "1")
    import time
    time.sleep(2)
    assert len([c for c in site.ssh_calls() if "-O forward" in c]) == n
    text = ON_SITE.read_text()
    assert "while true" not in text and "nohup" not in text


@pytest.mark.parametrize("n", [1, 3, 5, 8, 11, 14, 17, 20, 24])
def test_tc017_a_connection_that_drops_at_any_call_ends_in_an_honest_answer_and_at_most_one_sbatch(tmp_path, site, fake, n):
    site.set("ssh_drop_after", str(n))
    (res,), _ = launch(site, fake, tmp_path, ["run-a"])
    assert res["state"] in ("refused", "error", "done"), res
    assert len([c for c in site.calls() if c.startswith("sbatch")]) <= 1
    assert not [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")]
    assert res["result"].get("message"), res
    if res["state"] != "done":
        assert not res["result"]["ok"]
        folder = site.work / "runs" / "run-a"
        if folder.exists():
            assert str(folder) in res["result"]["message"] + res["result"].get("left_on_site", ""), "what is left is told"
    assert site.guards_intact()
