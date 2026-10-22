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
    assert len(cancels) == 1 and "-R 127.0.0.1:0:127.0.0.1:8787" in cancels[0]   # the spec the forward was opened with (TC-U2-34)
    assert site.listening() == []
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


# ---- follow-up 2 (2026-10-13): unforward must really end the forward, and say so when it could not ------------------
# The fake ssh behaves like OpenSSH 8.9p1 here: a cancel matches only the -R spec the forward was opened with, and a
# refused cancel is two lines on stderr with exit code 0. The truth is site.listening(), not ssh.log.

SPEC = "127.0.0.1:0:127.0.0.1:%s"
OK_LINE = "reverse forward cancelled and its records removed"
GONE = {"forward_port": None, "forward_state": None}


def forwarded(site, port="8787"):
    r = on_site(site, "--forward", port)
    assert r.returncode == 0, r.stderr
    return r


def records(site):
    return {n: (personal(site) / n).read_bytes() if (personal(site) / n).exists() else None for n in ("forward_port", "forward_state")}


def fake_ssh_run(site, *args):
    return subprocess.run([str(site.ssh_bin)] + list(args), capture_output=True, text=True, timeout=30)


def test_tc_u2_06_the_fake_ssh_refuses_a_cancel_with_the_allocated_port_like_openssh(site):
    forwarded(site)
    assert site.listening() == ["41234"]
    a = fake_ssh_run(site, "-O", "cancel", "-R", "127.0.0.1:41234:127.0.0.1:8787", "h")
    assert a.returncode == 0
    assert "mux_client_forward: forwarding request failed: port not forwarded" in a.stderr
    assert "muxclient: master cancel forward request failed" in a.stderr
    assert site.listening() == ["41234"]
    b = fake_ssh_run(site, "-O", "cancel", "-R", SPEC % 8787, "h")
    assert b.returncode == 0 and b.stderr == "" and b.stdout == ""
    assert site.listening() == []


def test_tc_u2_01_unforward_really_ends_the_forward_with_the_spec_it_was_opened_with(site):
    forwarded(site)
    assert site.listening() == ["41234"]
    r = on_site(site, "--unforward")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == OK_LINE and r.stderr == ""
    cancels = [c for c in site.ssh_calls() if "-O cancel" in c]
    assert len(cancels) == 1 and "-R 127.0.0.1:0:127.0.0.1:8787" in cancels[0]
    assert site.listening() == []
    assert not (personal(site) / "forward_port").exists() and not (personal(site) / "forward_state").exists()
    assert on_site(site, "--check-forward").returncode == 1


def test_tc_u2_02_the_forward_records_what_a_cancel_needs_and_nothing_secret(site):
    forwarded(site)
    text = (personal(site) / "forward_state").read_text()
    assert re.search(r"^master_pid=\d+$", text, re.M) and "local_port=8787" in text.splitlines()
    assert SPEC % 8787 in text
    for n in ("forward_state", "forward_port"):
        assert stat.S_IMODE((personal(site) / n).stat().st_mode) == 0o600
    assert not re.search(r"(?i)token|CANARY|secret|BEGIN|password", text + (personal(site) / "forward_port").read_text())
    assert on_site(site, "--check-forward").stdout.strip() == "41234"


def test_tc_u2_03_another_local_port_is_cancelled_the_same_way(site):
    forwarded(site, "9100")
    r = on_site(site, "--unforward")
    assert r.returncode == 0, r.stderr
    cancels = [c for c in site.ssh_calls() if "-O cancel" in c]
    assert len(cancels) == 1 and "-R 127.0.0.1:0:127.0.0.1:9100" in cancels[0]
    assert site.listening() == [] and records(site) == GONE


def test_tc_u2_05_a_record_written_by_the_old_code_can_still_be_cancelled(site):
    forwarded(site)
    pid = [ln for ln in (personal(site) / "forward_state").read_text().splitlines() if ln.startswith("master_pid=")][0]
    (personal(site) / "forward_state").write_text(pid + "\nlocal_port=8787\n")
    assert on_site(site, "--check-forward").stdout.strip() == "41234"           # TC-U2-32: the old format reads the same
    r = on_site(site, "--unforward")
    assert r.returncode == 0, r.stderr
    assert "-R 127.0.0.1:0:127.0.0.1:8787" in [c for c in site.ssh_calls() if "-O cancel" in c][0]
    assert site.listening() == [] and records(site) == GONE


def test_tc_u2_10_a_cancel_the_connection_refuses_is_said_aloud_and_nothing_is_forgotten(site):
    forwarded(site)
    state = personal(site) / "forward_state"
    state.write_text("\n".join(l for l in state.read_text().splitlines() if "127.0.0.1:" not in l).replace("local_port=8787", "local_port=9999") + "\n")
    before = records(site)
    r = on_site(site, "--unforward")
    assert r.returncode != 0
    assert "41234" in r.stderr and re.search(r"(?i)still open", r.stderr)
    assert "cancelled" not in r.stdout and "records removed" not in r.stdout
    assert records(site) == before
    assert site.listening() == ["41234"]
    assert on_site(site, "--check-forward").stdout.strip() == "41234"


def test_tc_u2_11_after_a_refusal_the_second_try_works(site):
    forwarded(site)
    site.set("cancel_refuse_once", "1")
    before = records(site)
    first = on_site(site, "--unforward")
    assert first.returncode != 0 and records(site) == before and site.listening() == ["41234"]
    second = on_site(site, "--unforward")
    assert second.returncode == 0 and second.stdout.strip() == OK_LINE
    assert site.listening() == [] and records(site) == GONE


def run_abf_unforward(site):
    env = dict(site.agent_env(), PYTHONPATH=str(PLATFORM_DIR))
    return subprocess.run([sys.executable, "-m", "abf_station", "unforward", "--deployment", str(site.root)], env=env,
                          capture_output=True, text=True, timeout=60)


def test_tc_u2_12_abf_station_unforward_shows_the_failure_exits_non_zero_and_keeps_both_copies(tmp_path, site, fake):
    (res,), _ = launch(site, fake, tmp_path, ["run-a"])
    assert res["state"] == "done"
    relay = site.storage / "_relay"
    site.set("cancel_refuse_once", "1")
    n_before = len(site.destructive())
    r = run_abf_unforward(site)
    out = r.stdout + r.stderr
    assert r.returncode != 0
    assert "41234" in out and re.search(r"(?i)still open", out) and "cancelled and its records removed" not in out
    assert (personal(site) / "forward_port").exists()
    assert (relay / "forward_port").exists() and (relay / "forward_instance").exists()
    assert len(site.destructive()) == n_before and site.listening() == ["41234"]    # nothing on the site was removed
    r2 = run_abf_unforward(site)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert OK_LINE in r2.stdout and "the copy on the site" in r2.stdout
    assert site.listening() == []
    assert not (personal(site) / "forward_port").exists()
    assert not (relay / "forward_port").exists() and not (relay / "forward_instance").exists()


def test_tc_u2_13_cmd_unforward_prints_both_outputs_and_follows_the_script_exit_code(site, monkeypatch, capsys):
    import argparse
    sys.path.insert(0, str(PLATFORM_DIR))
    from abf_station import cli, site as site_mod

    class Fake:
        def __init__(self, *a, **k):
            pass

        def call(self, args, **k):
            return site_mod.SiteResult(1 if args == ["--unforward"] else 0, b"OUT-TEXT\n", "ERR-TEXT\n")

    monkeypatch.setattr(site_mod, "Site", Fake)
    rc = cli.cmd_unforward(argparse.Namespace(plugin_root=str(REPO_ROOT), deployment=str(site.root)))
    cap = capsys.readouterr()
    assert rc != 0 and "OUT-TEXT" in cap.out + cap.err and "ERR-TEXT" in cap.out + cap.err
    assert "removed" not in (cap.out + cap.err).replace("OUT-TEXT", "")             # no site-copy removal after a failure


def test_tc_u2_14_without_a_shared_connection_the_records_just_go(site):
    forwarded(site)
    site.set("ssh_mode", "nomaster")
    r = on_site(site, "--unforward")
    assert r.returncode == 0 and r.stdout.strip() == OK_LINE and r.stderr == ""
    assert not [c for c in site.ssh_calls() if "-O cancel" in c]
    assert records(site) == GONE


def test_tc_u2_15_a_forward_of_an_earlier_connection_does_not_leave_a_record_that_cannot_be_cleared(site):
    forwarded(site)
    site.set("master_pid", "9999")                                                   # the connection was opened again
    r = on_site(site, "--unforward")
    assert r.returncode == 0, r.stderr
    assert re.search(r"(?i)earlier connection", r.stdout + r.stderr)
    assert not re.search(r"(?i)still open", r.stdout + r.stderr)
    assert records(site) == GONE


def test_tc_u2_16_a_cancel_that_errors_out_keeps_the_records_and_names_the_port(site):
    forwarded(site)
    site.set("cancel_error", "1")
    before = records(site)
    r = on_site(site, "--unforward")
    assert r.returncode != 0 and "41234" in r.stderr and re.search(r"(?i)still be open|still open", r.stderr)
    assert "cancelled" not in r.stdout and records(site) == before


@pytest.mark.parametrize("text", ["mux_client_forward: forwarding request failed: port not forwarded\n",
                                  "muxclient: master cancel forward request failed\n"])
def test_tc_u2_17_one_of_the_two_refusal_lines_is_enough_to_call_it_a_failure(site, text):
    forwarded(site)
    site.set("cancel_refuse_text", text)
    before = records(site)
    r = on_site(site, "--unforward")
    assert r.returncode != 0 and "41234" in r.stderr and records(site) == before


def test_tc_u2_18_an_unrelated_warning_on_stderr_is_not_a_failure(site):
    forwarded(site)
    site.set("cancel_warning", "Warning: Permanently added 'lgn304' (ED25519) to the list of known hosts.\n")
    r = on_site(site, "--unforward")
    assert r.returncode == 0 and r.stdout.strip() == OK_LINE
    assert site.listening() == [] and records(site) == GONE


def test_tc_u2_19_with_no_record_there_is_nothing_to_cancel_and_nothing_is_created(site):
    r = on_site(site, "--unforward")
    assert r.returncode == 0 and r.stdout.strip() == OK_LINE
    assert not [c for c in site.ssh_calls() if "-O cancel" in c]
    assert not personal(site).exists() or list(personal(site).iterdir()) == []


@pytest.mark.parametrize("state", [None, "master_pid=4242\n"])
def test_tc_u2_20_a_record_that_is_incomplete_does_not_claim_the_forward_is_gone(site, state):
    forwarded(site)
    if state is None:
        (personal(site) / "forward_state").unlink()
    else:
        (personal(site) / "forward_state").write_text(state)
    r = on_site(site, "--unforward")
    assert r.returncode != 0 and "41234" in r.stderr and re.search(r"(?i)incomplete", r.stderr)
    assert "cancelled" not in r.stdout
    assert (personal(site) / "forward_port").exists() and site.listening() == ["41234"]


def test_tc_u2_30_the_success_path_says_exactly_what_it_said_before(site):
    forwarded(site)
    r = on_site(site, "--unforward")
    assert (r.returncode, r.stdout, r.stderr) == (0, OK_LINE + "\n", "")


def test_tc_u2_33_a_poll_opens_no_extra_connection_and_unforward_opens_none(site):
    forwarded(site)
    on_site(site, "--check-forward")
    on_site(site, "--unforward")
    calls = site.ssh_calls()
    assert [c for c in calls if "-O " not in c] == []                                # every call is a mux operation
    assert len([c for c in calls if "-O forward" in c]) == 1


def test_tc_u2_51_a_failed_unforward_removes_nothing_and_a_good_one_removes_only_its_two_files(tmp_path, site, fake):
    (res,), _ = launch(site, fake, tmp_path, ["run-a"])
    site.set("cancel_refuse_once", "1")
    before = site.destructive()
    run_abf_unforward(site)
    assert site.destructive() == before
    r = run_abf_unforward(site)
    assert r.returncode == 0
    new = site.destructive()[len(before):]
    assert len(new) == 1 and new[0].startswith("rm -f") and new[0].count("_relay/") == 2
    assert site.guards_intact() and (site.storage / "rawdata" / "s1.fq").exists() and (site.storage / "cache").is_dir()


# ---- way_back: direct (M1-03) : the progress goes to a public address, no reverse forward ---------------------------------

PUBLIC = "https://abf.example.ts.net"


def set_settings(site, *lines):
    site.settings.write_text(site.settings.read_text() + "\n".join(lines) + "\n")


def direct_facts(url=PUBLIC, **over):
    f = {"reach": "ssh", "platform_local": False, "forward_file": None, "way_back": "direct", "platform_public_url": url}
    f.update(over)
    return f


def direct_bundle(site, fake, url=PUBLIC, run="run-a", **over):
    env = [{"name": "NXF_SINGULARITY_CACHEDIR", "value": str(site.storage / "cache"), "head": True, "compute": False}]
    return bundle_for(site, fake, run=run, ce={"environment": env}, facts=direct_facts(url, **over))


def hello_facts(fake):
    return [r[1]["facts"] for r in fake.requests if r[0] == "hello"][-1]


def test_tc001_tc004_tc005_tc006_direct_names_the_public_endpoint_and_needs_no_platform_local(site, fake):
    b = direct_bundle(site, fake)
    assert b["tower"] == {"mode": "direct", "endpoint": PUBLIC}
    for url in ("http://127.0.0.1:8787", "http://localhost:8787"):
        assert direct_bundle(site, fake, url)["tower"] == {"mode": "direct", "endpoint": url}


def test_tc002_tc003_tc007_tc028_tc033_direct_launch_opens_no_forward_and_still_goes_over_ssh(tmp_path, site, fake):
    set_settings(site, "way_back: direct", "platform_public_url: " + PUBLIC)
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        wait_for(lambda: fake.count("hello"))
        res = run_job(fake, job_of(direct_bundle(site, fake)))
        text = a.output()
    assert res["state"] == "done", res
    assert site.ssh_calls() and all(c for c in site.ssh_calls())
    assert not [c for c in site.ssh_calls() if "-O forward" in c or "-O check" in c or "--forward" in c or "-R " in c]
    assert not (site.storage / "_relay" / "forward_port").exists()
    assert [c for c in site.calls() if c.startswith("sbatch")]
    assert hello_facts(fake)["reach"] == "ssh"
    assert TOKEN not in text and not any(TOKEN in c for c in site.ssh_calls())
    assert TOKEN not in str(hello_facts(fake))


@pytest.mark.parametrize("url", ["http://abf.example.ts.net", "http://192.168.1.5:8787", "http://localhost.example.com:8787", "ftp://abf.example.ts.net", None])
def test_tc008_tc009_tc010_tc011_tc012_direct_over_plain_http_is_refused_before_the_site_is_touched(tmp_path, site, fake, url):
    from abf_station.launch import BundleError
    with pytest.raises(BundleError) as e:
        direct_bundle(site, fake, url)
    msg = str(e.value)
    assert "https" in msg and "loopback" in msg and "Traceback" not in msg and str(site.settings) not in msg
    assert site.calls() == [] and site.ssh_calls() == []


def test_tc013_tc014_tc015_tc018_forward_stays_the_default_and_the_public_address_is_ignored(site, fake):
    forward = str(site.storage / "_relay" / "forward_port")
    base = {"reach": "ssh", "platform_local": True, "forward_file": forward}
    for extra in ({}, {"way_back": "forward"}, {"platform_public_url": PUBLIC}, {"way_back": None, "platform_public_url": PUBLIC}):
        b = bundle_for(site, fake, facts=dict(base, **extra))
        assert b["tower"] == {"mode": "forward", "forward_file": forward}


def test_tc031_a_direct_launch_without_confirmation_is_refused(tmp_path, site, fake):
    b = direct_bundle(site, fake)
    good = job_of(b)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        wait_for(lambda: fake.count("hello"))
        res = run_job(fake, dict(good, args={"bundle": b, "bundle_sha256": good["args"]["bundle_sha256"]}))
    assert res["state"] == "refused", res
    assert not (site.work / "runs").exists() and not [c for c in site.calls() if c.startswith("sbatch")]


def test_tc032_the_public_address_is_part_of_what_was_confirmed(tmp_path, site, fake):
    from abf_platform import common
    a = direct_bundle(site, fake, "https://a.example.ts.net")
    b = direct_bundle(site, fake, "https://b.example.ts.net")
    assert common.bundle_sha256(a) != common.bundle_sha256(b)
    swapped = dict(job_of(a), args={"bundle": b, "confirmation_id": "c" * 32, "bundle_sha256": common.bundle_sha256(a)})
    swapped["confirmation"] = {"id": "c" * 32, "sha256": common.bundle_sha256(a), "kind": "launch"}
    with agent_on(fake, site, tmp_path, name="agent-f"):
        wait_for(lambda: fake.count("hello"))
        res = run_job(fake, swapped)
    assert res["state"] == "refused", res


def test_tc020_tc021_tc028_the_agent_reports_both_settings_and_keeps_reach(tmp_path, site, fake):
    with agent_on(fake, site, tmp_path, name="agent-f"):
        wait_for(lambda: fake.count("hello"))
    f = hello_facts(fake)
    assert f["way_back"] == "forward" and f["platform_public_url"] is None and f["reach"] == "ssh"


def test_tc020_a_configured_direct_is_reported(tmp_path, site, fake):
    set_settings(site, "way_back: direct", "platform_public_url: " + PUBLIC)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        wait_for(lambda: fake.count("hello"))
    f = hello_facts(fake)
    assert f["way_back"] == "direct" and f["platform_public_url"] == PUBLIC and f["reach"] == "ssh"


def test_tc022_tc023_clean_facts_keeps_only_the_literals_and_https_addresses():
    from abf_platform import common
    for ok in ("forward", "direct"):
        assert common.clean_facts({"way_back": ok})["way_back"] == ok
    for bad in ("sideways", ["direct"], 5, None):
        assert common.clean_facts({"way_back": bad})["way_back"] is None
    assert common.clean_facts({"platform_public_url": PUBLIC})["platform_public_url"] == PUBLIC
    for bad in (5, ["https://x"], "javascript:alert(1)", "ftp://abf.example.ts.net", "http://abf.example.ts.net", "http://localhost.example.com"):
        assert common.clean_facts({"platform_public_url": bad})["platform_public_url"] is None
    assert common.clean_facts({"evil": "x"}).get("evil") is None
