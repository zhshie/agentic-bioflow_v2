# Nothing existing: tests that the platform tests are run in two run_all.sh entries with nothing left out and nothing run twice; it only reads the wrapper's lists.
"""Follow-up 1 of feature 007b, F3: the split of tests/platform_test.sh (TC-F3-02, TC-F3-03, TC-F3-04, TC-F3-05, TC-F3-06)."""
import os
import re
import subprocess

from helpers import PLATFORM_DIR, REPO_ROOT
from test_wrapper import _bin_without_java, _clean_env, warm  # noqa: F401  (warm is a fixture)

MAIN = REPO_ROOT / "tests" / "platform_test.sh"
CLOCK = REPO_ROOT / "tests" / "platform_clock_test.sh"
CLOCK_FILES = ["tests/test_station_e2e.py", "tests/test_nextflow_e2e.py"]


def listed(script, **extra):
    env = _clean_env(ABF_PLATFORM_LIST="1", **extra)
    r = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    files = []
    for line in r.stdout.splitlines():
        kind, _, rest = line.partition(":")
        assert kind in ("shard", "alone"), line
        files.append((kind, rest.split()))
    return files


def test_tcf3_02_every_test_file_is_in_exactly_one_entry():
    # TC-F3-02: the union of the two entries is every platform/tests/test_*.py, each once
    everything = sorted("tests/" + p.name for p in (PLATFORM_DIR / "tests").glob("test_*.py"))
    main = [f for _, fs in listed(MAIN) for f in fs]
    clock = [f for _, fs in listed(CLOCK) for f in fs]
    assert sorted(main + clock) == everything
    assert len(set(main + clock)) == len(main + clock)


def test_tcf3_05_the_two_clock_sensitive_files_run_alone_one_after_the_other():
    # TC-F3-05: not in any shard of the main entry; in the other entry each on its own, in this order
    main = listed(MAIN)
    assert all(kind == "shard" for kind, _ in main)
    assert not [f for _, fs in main for f in fs if f in CLOCK_FILES]
    assert listed(CLOCK) == [("alone", [CLOCK_FILES[0]]), ("alone", [CLOCK_FILES[1]])]


def test_tcf3_06_run_all_lists_both_entries_and_the_new_one_ends_in_test_sh():
    # TC-F3-06
    assert CLOCK.name.endswith("_test.sh")
    r = subprocess.run(["bash", str(REPO_ROOT / "tests" / "run_all.sh"), "--list", "--allow-msys"], capture_output=True, text=True,
                       timeout=60, env=_clean_env())
    names = r.stdout.split()
    assert "platform_test.sh" in names and "platform_clock_test.sh" in names and "run_all.sh" not in names


def test_tcf3_04_the_limit_of_a_test_was_not_raised_and_its_comment_is_there():
    # TC-F3-04
    text = (REPO_ROOT / "tests" / "run_all.sh").read_text()
    m = re.search(r"^PER_TEST_TIMEOUT=(\d+)\s+#\s*(.*)$", text, re.M)
    assert m and int(m.group(1)) <= 300 and "only catches a hang" in m.group(2)


def test_tcf3_03_nothing_may_be_skipped_on_ci_in_the_second_entry_too(tmp_path, warm):  # noqa: F811
    # TC-F3-03: no Java on CI is a failure of the clock entry, as it is of the main one
    path = str(_bin_without_java(tmp_path))
    for script in (MAIN, CLOCK):
        ci = subprocess.run(["bash", str(script)], env=_clean_env(PATH=path, CI="true"), capture_output=True, text=True, timeout=300)
        assert ci.returncode != 0 and "FAIL (CI=true)" in ci.stdout, (script.name, ci.stdout[-400:])
