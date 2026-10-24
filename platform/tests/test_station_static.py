# Nothing existing: static checks of the agent package against the constitution and the feature's red lines; the repo's own checks do not scan platform/.
"""Static scans of abf_station/ and the packaging (feature 007)."""
import re
import subprocess
import sys

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT, pkg_env

PKG = PLATFORM_DIR / "abf_station"
PLAT = PLATFORM_DIR / "abf_platform"


def station_sources():
    files = sorted(PKG.rglob("*.py"))
    assert files, "abf_station/ has no source files"
    return files


def hits(files, patterns):
    out = []
    for f in files:
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for pat in patterns:
                if re.search(pat, line):
                    out.append("%s:%d %s" % (f.name, n, line.strip()))
    return out


def test_tc012_the_agent_source_has_nothing_that_listens():
    # TC-012 (static half)
    assert hits(station_sources(), [r"listen", r"\bbind\b", r"socketserver", r"http\.server", r"start_server",
                                    r"uvicorn", r"Starlette", r"Flask"]) == []


def test_tc070_the_agent_source_has_no_prompt_no_key_handling_and_no_terminal_login():
    # TC-070 (static half)
    assert hits(station_sources(), [r"getpass", r"input\(", r"paramiko", r"pexpect", r"id_rsa", r"\.pem\b",
                                    r"\botp\b", r"passphrase"]) == []


def test_agent_stricter_scan_no_other_network_or_cloud_library():
    # plan Revision 2 item 8: the stricter scan of abf_station that replaces the words dropped from the platform scan
    assert hits(station_sources(), [r"import requests", r"import httpx", r"import socket\b", r"\bsocket\.",
                                    r"smtplib", r"boto3", r"botocore", r"kubernetes", r"google\.cloud", r"\bazure\b",
                                    r"\btw\s", r"cloud\." + "seqera", r"tower" + r"\.nf"]) == []


def test_tc090_the_agent_has_no_hidden_loop_no_fork_and_only_the_poll_and_the_beat():
    # TC-090 (source half)
    files = station_sources()
    assert hits(files, [r"\bfork\b", r"daemon", r"nohup", r"setsid", r"sched\b", r"apscheduler", r"crontab"]) == []
    threads = {f.name for f in files if re.search(r"\bThread\(", f.read_text(encoding="utf-8"))}
    loops = {f.name for f in files if re.search(r"^\s*while\b", f.read_text(encoding="utf-8"), re.M)}
    assert threads <= {"agent.py"}, threads
    assert loops <= {"agent.py"}, loops


def test_tc091_only_one_module_starts_programs_and_it_does_so_without_a_shell():
    # TC-091
    files = station_sources()
    importing = [f.name for f in files if re.search(r"^\s*(import subprocess|from subprocess import)", f.read_text(encoding="utf-8"), re.M)]
    assert len(importing) == 1, importing
    assert hits(files, [r"shell\s*=\s*True", r"os\.system", r"os\.popen", r"""["'](ssh|scp|rsync)["']"""]) == []
    text = (PKG / importing[0]).read_text(encoding="utf-8")
    assert "shlex.quote" in text, "every argument handed to the site script must be quoted"
    assert "on_site.sh" in text


def test_tc084_nothing_in_either_package_submits_a_job_or_starts_a_run():
    # TC-084 (static half)
    pats = [r"nextflow\s+run", r"--wrap", r"""nextflow["']\s*,\s*["']run""", r"\b(srun|qsub|bsub)\b"]
    # feature 007b (TC-060): the one file that holds the launch (platform/abf_station/launch.py, the LAUNCH_ALLOW entry) may
    # hold these words; every other file of both packages may not
    others = [f for f in station_sources() if f.name != "launch.py"]
    assert hits(others + sorted(PLAT.rglob("*.py")), pats) == []
    for f in others:
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            assert not re.search(r"\bsbatch\s+(?!--version|-V)[\w./-]", line), (f.name, n, line)


def test_tc087_nothing_keeps_a_process_alive_or_reopens_a_connection():
    # TC-087 (static half)
    ls = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert ls.returncode == 0 and ls.stdout.split(), "git ls-files gave nothing (rc=%s): %s" % (ls.returncode, ls.stderr)
    found = [p for p in ls.stdout.split() if re.search(r"\.(service|timer)$|(^|/)crontab$", p)]
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True).stdout.splitlines()[:20]
    assert not found, "tracked files that keep a process alive: %s\ngit status --porcelain (first 20 lines):\n%s" % (found, "\n".join(status))
    assert hits(station_sources(), [r"ControlMaster", r"ControlPersist", r"ssh\s+-", r"ssh_control"]) == []


def test_tc092_the_path_scan_really_covers_the_agent_package():
    # TC-092
    from test_scope import _all_platform_files
    names = {p.relative_to(PLATFORM_DIR).as_posix() for p in _all_platform_files()}
    assert "abf_station/agent.py" in names and "abf_station/handlers.py" in names
    pat = re.compile(r"(/home|/work|/scratch|/staging|/lustre)/[A-Za-z][A-Za-z0-9_.-]*/")
    bad = []
    for f in station_sources():
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line):
                bad.append("%s:%d" % (f.name, n))
    assert bad == []


def test_tc074_the_package_and_the_command_are_declared_and_the_help_is_complete():
    # TC-074
    toml = (PLATFORM_DIR / "pyproject.toml").read_text()
    pk = re.search(r"packages\s*=\s*\[([^\]]*)\]", toml).group(1)
    assert "abf_station" in pk and "abf_platform" in pk
    assert re.search(r'abf-station\s*=\s*"abf_station\.cli:main"', toml)
    env = pkg_env()
    v = subprocess.run([sys.executable, "-m", "abf_station", "--version"], env=env, capture_output=True, text=True)
    assert v.returncode == 0 and re.match(r"^\d+\.\d+\.\d+\S*$", v.stdout.strip()), v.stdout + v.stderr
    h = subprocess.run([sys.executable, "-m", "abf_station", "--help"], env=env, capture_output=True, text=True)
    assert h.returncode == 0 and re.search(r"\brun\b", h.stdout)
    r = subprocess.run([sys.executable, "-m", "abf_station", "run", "--help"], env=env, capture_output=True, text=True)
    for flag in ("--platform", "--token-file", "--deployment"):
        assert flag in r.stdout, flag


NEW_TESTS = ["test_station_platform.py", "test_station_envs.py", "test_station_fakeplatform.py", "test_station_e2e.py",
             "test_station_static.py", "test_station_docs.py", "station_harness.py"]


def test_tc078_the_new_tests_never_pass_over_a_case_and_never_reach_a_real_cluster_or_seqera():
    # TC-078
    words = ["sk" + "ip", "xf" + "ail", "importor" + "skip"]
    pat = re.compile(r"pytest\.(%s)|@pytest\.mark\.(%s)|\.%s\(" % ("|".join(words), "|".join(words), "|".join(words)))
    bad = []
    for name in NEW_TESTS:
        text = (PLATFORM_DIR / "tests" / name).read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            if pat.search(line) or re.search(r"\b%s\b" % words[0], line) and "pytest" in line:
                bad.append("%s:%d %s" % (name, n, line.strip()))
    assert bad == []
    for f in station_sources():
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(paramiko|pexpect)", text, re.M)
    # the fake site's PATH is a closed box: no real ssh, tw or aws can be found in it
    from station_harness import FakeSite
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        site = FakeSite(Path(d))
        path = site.agent_env()["PATH"].split(":")
        import shutil
        assert shutil.which("tw", path=":".join(path)) is None
        assert shutil.which("aws", path=":".join(path)) is None
        assert (site.bin / "ssh").read_text().count("exit 1") == 1, "the ssh on PATH must be the logging stand-in"
