# Nothing existing: static checks of what feature 007b added against the constitution and the feature's red lines; the repository's own checks do not scan platform/.
"""Static scans for feature 007b: one submission path, no daemon, no hard-coded site, headers, no skipped tests."""
import ast
import re
import subprocess
from pathlib import Path

from helpers import PLATFORM_DIR, REPO_ROOT
from test_scope import _repo_names, judge

TESTS = PLATFORM_DIR / "tests"
CODE_DIRS = ("abf_platform", "abf_station", "abf_launch")


def code_files():
    return sorted(p for d in CODE_DIRS for p in (PLATFORM_DIR / d).rglob("*.py"))


def real_lines(path):
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.lstrip().startswith("#"):
            yield n, line


def test_tc052_the_words_that_submit_a_job_stand_in_one_file_and_the_screen_uses_its_function():
    # TC-052: the same expressions as scan 1 of tests/no_second_run_state_test.sh
    submit = re.compile(r"""(^\s*|["'(;&|`]\s*)(sbatch|qsub|bsub|srun|nextflow\s+run)(\s|["']|$)""")
    hits = {p.relative_to(PLATFORM_DIR).as_posix() for p in code_files() for n, line in real_lines(p) if submit.search(line)}
    assert hits == {"abf_station/launch.py"}, hits
    for p in code_files():
        text = p.read_text(encoding="utf-8")
        assert not re.search(r"""["'](nex|sb|next)["']\s*\+|\+\s*["'](tflow run|atch|flow run)["']""", text), p.name
    assert "from abf_station import launch" in (PLATFORM_DIR / "abf_launch" / "cli.py").read_text(encoding="utf-8")
    assert "render_bundle(" in (PLATFORM_DIR / "abf_launch" / "cli.py").read_text(encoding="utf-8")
    assert "render_bundle(" in (PLATFORM_DIR / "abf_station" / "launch.py").read_text(encoding="utf-8")


def test_tc052_the_launch_allow_entry_is_one_and_names_a_test_that_exists():
    text = (REPO_ROOT / "tests" / "no_second_run_state_test.sh").read_text(encoding="utf-8")
    block = text[text.index('LAUNCH_ALLOW="\n') + len('LAUNCH_ALLOW="\n'):]
    entries = [ln for ln in block[:block.index('"\n')].splitlines() if ln.strip()]
    assert len(entries) == 1
    path, test, why = entries[0].split("|", 2)
    assert path == "platform/abf_station/launch.py" and test == "platform/tests/test_station_launch.py::test_unconfirmed_launch_is_refused"
    tree = ast.parse((REPO_ROOT / test.split("::")[0]).read_text(encoding="utf-8"))
    assert any(isinstance(n, ast.FunctionDef) and n.name == test.split("::")[1] for n in tree.body)


def test_tc068_nothing_that_launches_cancels_or_fetches_loops_or_runs_in_a_thread():
    for name in ("launch.py", "cancel.py", "fetch.py"):
        text = (PLATFORM_DIR / "abf_station" / name).read_text(encoding="utf-8")
        assert not re.search(r"^\s*(while|until)\b|\bthreading\b|\bThread\(|\bsched\b|nohup|setsid|daemon", text, re.M), name
    for p in code_files():
        if p.name in ("agent.py",):
            continue
        assert not re.search(r"^\s*while\s+(True|1)\b", p.read_text(encoding="utf-8"), re.M), p.name
    cancel = (PLATFORM_DIR / "abf_station" / "cancel.py").read_text(encoding="utf-8")
    assert cancel.count("squeue") >= 1 and len(re.findall(r"site\.call\(\[\"squeue", cancel)) == 1
    assert len(re.findall(r"site\.call\(\[\"scancel", cancel)) == 1
    for p in code_files():
        if p.name != "cancel.py":
            assert "scancel" not in "".join(l for _, l in real_lines(p)) or p.name == "handlers.py" and False, p.name


def test_tc069_tc070_the_account_the_login_node_and_the_relay_port_are_in_no_program():
    account = re.compile(r"\b[A-Z]{3}[0-9]{6}\b")
    site_words = re.compile(r"\b(ngs[0-9]*[gGmM]?|lgn[0-9]*|nchc|taiwania|18080)\b", re.I)
    for p in code_files():
        text = "".join(l + "\n" for _, l in real_lines(p))
        assert not account.search(text), p.name
        assert not site_words.search(text), (p.name, site_words.search(text).group(0))
    for f in (REPO_ROOT / "tests" / "platform_test.sh",):
        assert not account.search(f.read_text(encoding="utf-8")), f.name


def test_tc066_every_new_file_says_what_it_is_not():
    names = _repo_names()
    new = [PLATFORM_DIR / "abf_launch" / n for n in ("__init__.py", "cli.py", "terminal.py")]
    new += [PLATFORM_DIR / "abf_station" / n for n in ("launch.py", "cancel.py", "fetch.py")]
    new += [PLATFORM_DIR / "abf_platform" / n for n in ("confirm.py", "records.py")]
    new += [TESTS / n for n in ("test_launch_bundle.py", "test_launch_cli.py", "test_launch_platform.py", "test_launch_e2e.py",
                                "test_launch_nextflow.py", "test_launch_static.py", "test_launch_docs.py", "test_station_launch.py",
                                "test_station_cancel.py", "test_station_channel.py", "test_relay_loopback.py", "test_receiver_nf2510.py",
                                "test_wrapper_nf2.py", "launch_harness.py")]
    new += [TESTS / "fixtures" / "record_payloads.py"]
    problems = [judge(p, names) for p in new]
    assert [x for x in problems if x] == []


def test_tc056_the_new_tests_do_not_skip_a_case_and_never_reach_a_real_cluster_or_seqera():
    words = ["sk" + "ip", "xf" + "ail", "importor" + "skip"]
    pat = re.compile(r"pytest\.(%s)|@pytest\.mark\.(%s)|\.%s\(" % ("|".join(words), "|".join(words), "|".join(words)))
    new = ["test_launch_bundle.py", "test_launch_cli.py", "test_launch_platform.py", "test_launch_e2e.py", "test_launch_nextflow.py",
           "test_launch_static.py", "test_launch_docs.py", "test_station_launch.py", "test_station_cancel.py", "test_station_channel.py",
           "test_relay_loopback.py", "test_receiver_nf2510.py", "test_wrapper_nf2.py", "launch_harness.py"]
    for name in new:
        text = (TESTS / name).read_text(encoding="utf-8")
        assert not pat.search(text), name
        assert not re.search(r"(^|[\s;&|`(])tw\s+(runs|launch|info|pipelines|compute-envs)\b", text), name
        assert "cloud." + "seqera" not in text, name


def test_tc074_no_token_or_account_is_committed():
    tracked = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True).stdout.split()
    assert tracked, "git must know the files"
    bad = []
    for f in tracked:
        if not f.endswith((".py", ".sh", ".md", ".env", ".json", ".config", ".in")) or f.startswith(("specs/", "platform/tests/fixtures/payloads/")):
            continue
        p = REPO_ROOT / f
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if re.search(r"abf_[A-Za-z0-9_-]{30,}", text) and not f.startswith("platform/tests/"):
            bad.append(f)
    assert bad == []


def test_the_one_waiting_loop_of_the_terminal_commands_is_pinned_in_place_and_in_time():
    # the only loop and the only sleep in abf_launch: the foreground wait of `abf-platform launch` for a late answer of the agent,
    # in _report_launch, bounded by the grace time (default 120 s), with a person at the terminal. Nowhere else.
    loops, sleeps = [], []
    for path in sorted((PLATFORM_DIR / "abf_launch").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            for n in ast.walk(fn):
                if isinstance(n, ast.While):
                    loops.append((path.name, fn.name, ast.unparse(n.test)))
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "sleep":
                    sleeps.append((path.name, fn.name))
    assert [(f, name) for f, name, _ in loops] == [("cli.py", "_report_launch")], loops
    assert "time.time() < end" in loops[0][2], "the loop has a time limit in its own condition"
    assert sleeps == [("cli.py", "_report_launch")], sleeps
    text = (PLATFORM_DIR / "abf_launch" / "cli.py").read_text(encoding="utf-8")
    assert re.search(r"^GRACE_DEFAULT = 120\.0$", text, re.M)
    assert re.search(r"end = time\.time\(\) \+ _grace\(\)", text) and "time.sleep(0.25)" in text


def test_nothing_else_in_the_new_code_sleeps_or_waits_in_a_loop():
    for p in code_files():
        if p.parent.name == "abf_launch" or p.name in ("agent.py", "agents.py", "jobs.py", "site.py"):  # the 007 poll loops
            continue
        text = "".join(l + "\n" for _, l in real_lines(p))
        assert not re.search(r"\btime\.sleep\(|\basyncio\.sleep\(", text), p.name
