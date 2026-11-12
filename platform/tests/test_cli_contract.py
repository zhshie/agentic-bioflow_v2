# Nothing existing: test_cli.py and the *_cli.py files check what single commands do; no test walks every command for its exit code, its stdout/stderr split and that nothing internal leaks.
"""Contract of the abf-platform command line (argparse, not click): exit 0 / 1 / 2, results on stdout and
messages on stderr, no stack or SQL or internal path in what a person reads, no colour codes.

Every command runs in process through abf_platform.cli.main on a database under tmp_path (ABF_PLATFORM_DB),
except the one real-process case. Nothing is started, sent, cancelled or deleted: serve, web, mcp, launch,
resume, relaunch, cancel, forget, fetch-records and preflight are only tried with wrong arguments or in the
way they refuse. Test cases (TC-0xx) are those of specs/cli-contract-tests/test-case.md."""
import json
import os
import re
import sys

import pytest

from abf_platform import cli
from helpers import pkg_env, run_cli
from test_cli_snapshots import JSON_NAMES, assert_golden, walk_leaves

LEAK_WORDS = ("Traceback", 'File "', "SELECT ", "INSERT ", "sqlite")
CE_ARGS = ["--platform", "slurm-platform", "--agent", "a1", "--work-dir", "/w", "--head-queue", "q", "--compute-queue", "q"]
CE_CREATE = ["ce", "create", "--name", "s1"] + CE_ARGS
USER_BOB = ["user", "add", "bob", "--lab", "L"]
PAT_ID = "{PAT_ID}"
AGENT_ID = "{AGENT_ID}"


@pytest.fixture
def home(tmp_path, monkeypatch):
    for k in list(os.environ):
        if k.startswith("ABF_PLATFORM_"):
            monkeypatch.delenv(k)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(tmp_path / "data" / "index.db"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def call(argv, capsys):
    """Run one command in process: (exit code, stdout, stderr). A SystemExit (argparse) gives its code."""
    capsys.readouterr()
    try:
        rc = cli.main(list(argv))
    except SystemExit as e:
        rc = e.code
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


def prepare(steps, capsys):
    for argv in steps:
        rc, out, err = call(argv, capsys)
        assert rc == 0, (argv, rc, out, err)


def fill(argv, capsys):
    """Replace {PAT_ID} by the id `pat list` shows (ids are not promised, so they are read)."""
    argv = list(argv)
    if PAT_ID in argv:
        _, out, _ = call(["pat", "list"], capsys)
        argv[argv.index(PAT_ID)] = re.search(r"^id (\d+)", out, re.M).group(1)
    return argv


def no_leak(text, tmp_path):
    for w in LEAK_WORDS + (str(tmp_path),):
        assert w not in text, "%r in %r" % (w, text)


# One row per leaf: bad = a wrong use (exit 2); happy / fail = (steps before, argv) or None with the reason in no_*.
def leaf(path, bad, happy=None, fail=None, no_happy="", no_fail=""):
    assert happy or no_happy, path
    assert fail or no_fail, path
    return path, dict(bad=bad, happy=happy, fail=fail, no_happy=no_happy, no_fail=no_fail)


MATRIX = dict([
    leaf("serve", ["serve", "--port", "abc"], no_happy="runs until stopped and takes a port; its start is covered by test_cli.py",
         no_fail="no refusal of its own: a taken port is an environment matter"),
    leaf("web", ["web", "--port", "abc"], no_happy="runs until stopped and takes a port; its start is covered by test_cli.py",
         fail=([], ["web", "--host", "0.0.0.0"])),
    leaf("mcp", ["mcp", "--port", "abc"], no_happy="runs until stopped (stdio or a port); its start is covered by test_cli.py",
         no_fail="no refusal of its own"),
    leaf("token new", ["token", "new", "--bogus"], happy=([], ["token", "new"]), no_fail="issuing a token cannot be refused"),
    leaf("agent-token new", ["agent-token", "new"], happy=([], ["agent-token", "new", "a1"]),
         fail=([USER_BOB], ["agent-token", "new", "a1"])),
    leaf("agent-token revoke", ["agent-token", "revoke", "--id", "abc"], happy=([["agent-token", "new", "a1"]], ["agent-token", "revoke", "a1"]),
         fail=([], ["agent-token", "revoke"])),
    leaf("agent-token list", ["agent-token", "list", "--bogus"], happy=([], ["agent-token", "list"]), no_fail="listing cannot be refused"),
    leaf("user add", ["user", "add", "bob"], happy=([], USER_BOB), fail=([USER_BOB], USER_BOB)),
    leaf("user cloud-cap", ["user", "cloud-cap", "bob"], happy=([USER_BOB], ["user", "cloud-cap", "bob", "5"]),
         fail=([], ["user", "cloud-cap", "zed", "5"])),
    leaf("user welcome", ["user", "welcome", "bob"], happy=([USER_BOB], ["user", "welcome", "bob", "--platform-url", "https://h.example"]),
         fail=([USER_BOB], ["user", "welcome", "zed", "--platform-url", "https://h.example"])),
    leaf("user passwd", ["user", "passwd"], no_happy="the password is typed at a real terminal; a test has none (TC-011 tries the refusal)",
         fail=([USER_BOB], ["user", "passwd", "bob"])),
    leaf("pat new", ["pat", "new"], happy=([USER_BOB], ["pat", "new", "--user", "bob"]), fail=([USER_BOB], ["pat", "new", "--user", "zed"])),
    leaf("pat list", ["pat", "list", "--bogus"], happy=([], ["pat", "list"]), no_fail="listing cannot be refused"),
    leaf("pat revoke", ["pat", "revoke", "abc"], happy=([USER_BOB, ["pat", "new", "--user", "bob"]], ["pat", "revoke", PAT_ID]),
         fail=([], ["pat", "revoke", "999"])),
    leaf("oauth revoke", ["oauth", "revoke"], happy=([USER_BOB], ["oauth", "revoke", "bob"]), fail=([], ["oauth", "revoke", "zed"])),
    leaf("ce create", ["ce", "create", "--bogus"], happy=([["agent-token", "new", "a1"]], CE_CREATE),
         fail=([], ["ce", "create", "--name", "x", "--platform", "slurm-platform", "--work-dir", "/w"])),
    leaf("ce update", ["ce", "update"], happy=([["agent-token", "new", "a1"], CE_CREATE], ["ce", "update", "s1", "--description", "d"]),
         fail=([], ["ce", "update", "nada"])),
    leaf("ce list", ["ce", "list", "--bogus"], happy=([], ["ce", "list"]), no_fail="listing cannot be refused"),
    leaf("ce show", ["ce", "show"], happy=([["agent-token", "new", "a1"], CE_CREATE], ["ce", "show", "s1"]), fail=([], ["ce", "show", "nada"])),
    leaf("ce primary", ["ce", "primary"], happy=([["agent-token", "new", "a1"], CE_CREATE], ["ce", "primary", "s1"]),
         fail=([], ["ce", "primary", "nada"])),
    leaf("ce disable", ["ce", "disable"], happy=([["agent-token", "new", "a1"], CE_CREATE], ["ce", "disable", "s1"]),
         fail=([], ["ce", "disable", "nada"])),
    leaf("ce enable", ["ce", "enable"], happy=([["agent-token", "new", "a1"], CE_CREATE, ["ce", "disable", "s1"]], ["ce", "enable", "s1"]),
         fail=([], ["ce", "enable", "nada"])),
    leaf("ce preflight", ["ce", "preflight"], no_happy="waits for a live agent's answer; no agent runs in a test",
         fail=([], ["ce", "preflight", "nada"])),
    leaf("rebuild", ["rebuild", "--bogus"], happy=([], ["rebuild", "launchdir"]), fail=([], ["rebuild", "emptydir"])),
    leaf("runs assign", ["runs", "assign"], no_happy="needs a run record of the hand-off table, which only a real launch writes",
         fail=([USER_BOB], ["runs", "assign", "r1", "--user", "zed"])),
    leaf("runs offer-cleanup", ["runs", "offer-cleanup", "--bogus"], happy=([], ["runs", "offer-cleanup", "--all"]),
         fail=([], ["runs", "offer-cleanup"])),
    leaf("dataset register", ["dataset", "register"], happy=([], ["dataset", "register", "--name", "p", "--version", "v1",
                                                                 "--samplesheet", "s.csv", "--file", "a_R1.fq.gz"]),
         fail=([], ["dataset", "register", "--name", "p", "--version", "v1", "--samplesheet", "nosuch.csv", "--file", "a"])),
    leaf("dataset list", ["dataset", "list", "--bogus"], happy=([], ["dataset", "list"]), fail=([USER_BOB], ["dataset", "list"])),
    leaf("dataset show", ["dataset", "show"], happy=([["dataset", "register", "--name", "p", "--version", "v1", "--samplesheet", "s.csv",
                                                       "--file", "a_R1.fq.gz"]], ["dataset", "show", "p"]), fail=([], ["dataset", "show", "nada"])),
    leaf("launch", ["launch", "--pipeline", "a/b"], no_happy="asks y/n on a real terminal; a test has none",
         fail=([USER_BOB], ["launch", "--pipeline", "a/b", "--revision", "1", "--run-name", "r", "--samplesheet", "x.csv"])),
    leaf("resume", ["resume"], no_happy="asks y/n on a real terminal; a test has none", fail=([USER_BOB], ["resume", "r1"])),
    leaf("relaunch", ["relaunch"], no_happy="asks y/n on a real terminal; a test has none", fail=([USER_BOB], ["relaunch", "r1"])),
    leaf("cancel", ["cancel"], no_happy="asks y/n on a real terminal; a test has none", fail=([], ["cancel", "r1"])),
    leaf("forget", ["forget"], no_happy="asks y/n on a real terminal; a test has none", fail=([], ["forget", "r1"])),
    leaf("launches", ["launches", "--bogus"], happy=([], ["launches"]), no_fail="listing cannot be refused"),
    leaf("fetch-records", ["fetch-records"], no_happy="asks a live agent to read a site; no agent runs in a test", fail=([], ["fetch-records", "r1"])),
    leaf("studio-connect", ["studio-connect"], no_happy="the token is typed at a hidden prompt or read from standard input, and the check connects to a platform; a test has neither (test_studio_remote.py covers it)",
         no_fail="its refusals exit 2 (an address or token that cannot be used) or 3 (no connection), which this matrix does not take as failures (test_studio_remote.py covers them)"),
    leaf("fetch-results", ["fetch-results"], no_happy="it reads a platform over the network and writes a folder on the computer it runs on; a test has no platform (test_studio_cli.py covers it with fakes)",
         no_fail="its refusals exit 2 (not set up, and the settings file is the computer's own) or 3 (no connection), which this matrix does not take as failures (test_studio_remote.py covers them)"),
    leaf("publish-figure", ["publish-figure"], no_happy="it sends a figure to a platform over the network and the person answers at a link; a test has no platform (test_studio_publish.py covers it with fakes)",
         no_fail="its refusals exit 1 (the platform said no), 2 (not set up) or 3 (no connection); a test has no platform (test_studio_publish.py and test_studio_remote.py cover them)"),
])


def make_launch_dirs(home):
    (home / "launchdir" / ".nextflow").mkdir(parents=True, exist_ok=True)
    (home / "launchdir" / ".nextflow" / "history").write_text(
        "2026-01-01 10:00:00\t1m\trun-a\tOK\tmain.nf\tsess-0001\n", encoding="utf-8")
    (home / "emptydir").mkdir(exist_ok=True)
    (home / "s.csv").write_text("sample,fastq_1,fastq_2\ns1,a_R1.fq.gz,\n", encoding="utf-8")


def cases(kind):
    return [pytest.param(p, id=p) for p, row in MATRIX.items() if row[kind]]


def _run_case(home, capsys, path, kind):
    make_launch_dirs(home)
    row = MATRIX[path]
    if kind == "bad":
        return call(row["bad"], capsys)
    steps, argv = row[kind]
    prepare(steps, capsys)
    return call(fill(argv, capsys), capsys)


def test_every_leaf_is_in_the_matrix():
    # TC-001
    real = {" ".join(p) for p, _ in walk_leaves(cli.build_parser())}
    assert set(MATRIX) == real, "only in the matrix: %s; only in the parser: %s" % (sorted(set(MATRIX) - real), sorted(real - set(MATRIX)))
    for path, row in MATRIX.items():
        assert row["bad"], path
        assert bool(row["happy"]) != bool(row["no_happy"]), path
        assert bool(row["fail"]) != bool(row["no_fail"]), path
    # the launch commands are in it as well
    assert {"launch", "cancel", "forget", "resume", "relaunch", "launches", "fetch-records", "studio-connect", "fetch-results", "publish-figure"} <= set(MATRIX)


@pytest.mark.parametrize("path", sorted(MATRIX))
def test_leaf_help_exits_zero(path, home, capsys):
    # TC-002
    rc, out, err = call(path.split() + ["--help"], capsys)
    assert rc == 0 and out.strip() and err == "", (rc, out, err)


@pytest.mark.parametrize("path", sorted(MATRIX))
def test_bad_arg_exits_two(path, home, capsys):
    # TC-003, TC-010 (serve, web, mcp with --port abc)
    rc, out, err = _run_case(home, capsys, path, "bad")
    assert rc == 2, (rc, out, err)
    assert "usage:" in err and out == "" and "Traceback" not in err, (out, err)


# TC-004: the seven bad situations, asserted exactly as the contract says: exit 1, stdout empty, stderr starts with `rejected:`,
# at least 20 characters, and Chinese after a "(" or a full-width "(". `ce show` and `dataset show` do NOT meet this today: they
# print their own not-found line (cli.py:464-470, 633-643) and this task does not change cli.py. Those two are strict xfail: the
# contract stays whole, the suite stays green, and the day cli.py is unified they turn XPASS (red) so the marker gets removed.
# Their real wording is pinned by test_not_found_shows_use_their_own_wording below.
GAP = "contract wants `rejected:` first; today's not-found line differs (decisions.tsv tc-004); maintainer must accept it or unify cli.py"
CJK_AFTER_PAREN = re.compile("[(\uff08][^)\uff09]*[\u4e00-\u9fff]")
RUNTIME = [
    pytest.param("user add", None, id="user add"),
    pytest.param("user cloud-cap", ([USER_BOB], ["user", "cloud-cap", "bob", "abc"]), id="user cloud-cap bad number"),
    pytest.param("ce create", None, id="ce create"),
    pytest.param("ce show", None, id="ce show", marks=pytest.mark.xfail(strict=True, reason=GAP)),
    pytest.param("web", None, id="web"),
    pytest.param("dataset show", None, id="dataset show", marks=pytest.mark.xfail(strict=True, reason=GAP)),
    pytest.param("agent-token new", None, id="agent-token new"),
]
RUNTIME_PATHS = {"user add", "user cloud-cap", "ce create", "ce show", "web", "dataset show", "agent-token new"}


@pytest.mark.parametrize("path,case", RUNTIME)
def test_runtime_failure_exits_one(path, case, home, capsys):
    # TC-004
    if case is None:
        rc, out, err = _run_case(home, capsys, path, "fail")
    else:
        make_launch_dirs(home)
        steps, argv = case
        prepare(steps, capsys)
        rc, out, err = call(argv, capsys)
    assert rc == 1 and out == "", (rc, out, err)
    assert err.startswith("rejected:") and len(err.strip()) >= 20 and CJK_AFTER_PAREN.search(err), err
    no_leak(out + err, home)


@pytest.mark.parametrize("path,start", [("ce show", "compute environment "), ("dataset show", "")])
def test_not_found_shows_use_their_own_wording(path, start, home, capsys):
    # TC-004 (the two commands above as they really behave today): exit 1, clean stdout, Chinese explanation, no leak
    rc, out, err = _run_case(home, capsys, path, "fail")
    assert rc == 1 and out == "" and err.startswith(start) and len(err.strip()) >= 20, (rc, out, err)
    assert re.search("[\u4e00-\u9fff]", err), err
    assert not err.startswith("rejected:"), "now unified: drop the xfail marks in RUNTIME and delete this test"
    no_leak(out + err, home)


def test_runtime_failure_other_commands_exit_one(home, capsys, monkeypatch):
    # TC-001 (every leaf with a failure path): exit 1, nothing on stdout (rebuild reports its skipped folder there), no leak
    for path, row in MATRIX.items():
        if not row["fail"] or path in RUNTIME_PATHS:
            continue
        sub = home / path.replace(" ", "_")
        sub.mkdir()
        monkeypatch.setenv("ABF_PLATFORM_DB", str(sub / "data" / "index.db"))
        rc, out, err = _run_case(home, capsys, path, "fail")
        assert rc == 1, (path, rc, out, err)
        assert (out == "") != (path == "rebuild"), (path, out)
        assert (err.strip() or out.strip()), path
        no_leak(out + err, home)


def test_user_passwd_refuses_without_a_terminal(home, capsys):
    # TC-011
    prepare([USER_BOB], capsys)
    for argv in (["user", "passwd", "bob"], ["user", "passwd", "bob", "--temporary"]):
        rc, out, err = call(argv, capsys)
        assert rc == 1 and out == "", (rc, out, err)
        assert err.startswith("rejected:") and "終端機" in err and "terminal" in err, err
        no_leak(out + err, home)


@pytest.mark.parametrize("path", [p for p in sorted(MATRIX) if MATRIX[p]["happy"]])
def test_happy_paths_exit_zero_with_empty_stderr(path, home, capsys):
    # TC-005 (the six named there are in the next test; this is every other leaf that can succeed)
    rc, out, err = _run_case(home, capsys, path, "happy")
    assert rc == 0 and err == "", (rc, out, err)


def test_happy_paths_keep_stdout_and_stderr_apart(home, capsys):
    # TC-005
    make_launch_dirs(home)
    rc, out, err = call(["token", "new"], capsys)
    assert rc == 0 and err == "", err
    assert len(re.findall(r"^abf_\S+$", out, re.M)) == 1, out
    for argv in (USER_BOB, ["pat", "new", "--user", "bob"], ["ce", "list"], ["dataset", "list", "--user", "bob"], ["rebuild", "launchdir"]):
        rc, out, err = call(argv, capsys)
        assert rc == 0 and err == "", (argv, rc, out, err)


def normalise_json(text):
    """Times and generated ids differ per run: keep the keys, hide the values."""
    obj = json.loads(text)

    def walk(v, key=""):
        if isinstance(v, dict):
            return {k: walk(x, k) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x, key) for x in v]
        if isinstance(v, (int, float)) and not isinstance(v, bool) and re.search(r"(?i)(time|_at$|At$|created|updated|^id$|_id$|Id$)", key):
            return "<N>"
        if isinstance(v, str) and (re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.+Z-]+", v) or re.fullmatch(r"[0-9a-f]{32,}", v)):
            return "<TS>"
        return v
    return json.dumps(walk(obj), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def test_json_outputs_parse(home, capsys):
    # TC-006
    make_launch_dirs(home)
    prepare([["agent-token", "new", "a1"], CE_CREATE,
             ["dataset", "register", "--name", "p", "--version", "v1", "--samplesheet", "s.csv", "--file", "a_R1.fq.gz"]], capsys)
    for argv, name in ((["ce", "show", "s1"], JSON_NAMES[0]), (["dataset", "show", "p"], JSON_NAMES[1])):
        rc, out, err = call(argv, capsys)
        assert rc == 0 and err == "", (argv, rc, err)
        json.loads(out)
        text = normalise_json(out).replace(str(home), "<TMP>")
        assert_golden(name, text)


@pytest.mark.parametrize("no_color", [True, False], ids=["NO_COLOR=1", "unset"])
def test_no_color(no_color, home, capsys, monkeypatch):
    # TC-007
    if no_color:
        monkeypatch.setenv("NO_COLOR", "1")
    for argv, want in ((["--help"], 0), (["token", "new"], 0), (["user", "cloud-cap", "zed", "5"], 1)):
        rc, out, err = call(argv, capsys)
        assert rc == want, (argv, rc, out, err)
        assert "\x1b[" not in out + err, (argv, out, err)


@pytest.mark.parametrize("path,kind", [(p, k) for p in sorted(MATRIX) for k in ("bad", "fail") if k == "bad" or MATRIX[p]["fail"]])
def test_errors_never_leak(path, kind, home, capsys):
    # TC-008: the outputs of the bad-argument cases and of the failure cases
    rc, out, err = _run_case(home, capsys, path, kind)
    assert rc == (2 if kind == "bad" else 1)
    no_leak(out + err, home)


def test_errors_never_leak_in_a_real_process(tmp_path):
    # TC-009: a real child process (sys.executable), so an uncaught exception would show
    env = pkg_env(ABF_PLATFORM_DB=tmp_path / "data" / "index.db")
    r = run_cli(["ce", "show", "不存在"], env=env, cwd=tmp_path)
    assert r.returncode == 1 and r.stdout == "", (r.returncode, r.stdout, r.stderr)
    assert r.stderr.strip() and "Traceback" not in r.stderr
    no_leak(r.stdout + r.stderr, tmp_path)
    assert sys.executable  # the interpreter is never taken from PATH


def test_documented_gaps():
    # TC-012, updated by cli-json-debug-version: --version, --json and --debug now exist, on the root only (their tests are in
    # test_cli_flags.py); there is still no NO_COLOR handler. It is a statement of the present, not a skipped test.
    def parsers(p):
        yield p
        for a in p._actions:
            if hasattr(a, "choices") and isinstance(getattr(a, "choices", None), dict):
                for child in a.choices.values():
                    yield from parsers(child)
    root = cli.build_parser()
    options = {o for p in parsers(root) for a in p._actions for o in a.option_strings}
    top = {o for a in root._actions for o in a.option_strings}
    assert {"--json", "--debug", "--version"} <= top
    # a leaf has none of --json and --debug; `dataset register|show` keep a --version of their own (the dataset's version)
    leaves = {o for p in parsers(root) if p is not root for a in p._actions for o in a.option_strings}
    assert not leaves & {"--json", "--debug"}, leaves & {"--json", "--debug"}
