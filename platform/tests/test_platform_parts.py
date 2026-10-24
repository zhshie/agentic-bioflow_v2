# Nothing existing: tests that the platform tests are run in four run_all.sh entries with nothing left out and nothing run twice; it only reads the wrapper's lists.
"""The split of tests/platform_test.sh into four run_all.sh entries (parts 1, 2, 3 and the clock): TC-F3-02 to TC-F3-06 and PS-01 to PS-61."""
import os
import re
import shutil
import subprocess

from helpers import PLATFORM_DIR, REPO_ROOT
from test_wrapper import _bin_without_java, _clean_env, warm  # noqa: F401  (warm is a fixture)

MAIN = REPO_ROOT / "tests" / "platform_test.sh"
CLOCK = REPO_ROOT / "tests" / "platform_clock_test.sh"
SHARD2 = REPO_ROOT / "tests" / "platform_shard_2_test.sh"
SHARD3 = REPO_ROOT / "tests" / "platform_shard_3_test.sh"
ENTRIES = [MAIN, SHARD2, SHARD3, CLOCK]
CLOCK_FILES = ["tests/test_station_e2e.py", "tests/test_nextflow_e2e.py"]
PARTS = ["1", "2", "3", "clock"]


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


def _all_files():
    return sorted("tests/" + p.name for p in (PLATFORM_DIR / "tests").glob("test_*.py"))


def _files(entries):
    return [f for _, fs in entries for f in fs]


def test_tcf3_02_every_test_file_is_in_exactly_one_entry():
    # TC-F3-02, PS-01, PS-02: the union of the four entries is every platform/tests/test_*.py, each once
    got = [f for part in PARTS for f in _files(listed(MAIN, ABF_PLATFORM_PART=part))]
    assert sorted(got) == _all_files()
    assert len(set(got)) == len(got)


def test_ps03_all_is_the_union_of_the_four_parts():
    # PS-03
    allf = _files(listed(MAIN, ABF_PLATFORM_PART="all"))
    assert sorted(allf) == _all_files()
    assert sorted(allf) == sorted(f for p in PARTS for f in _files(listed(MAIN, ABF_PLATFORM_PART=p)))


def test_tcf3_05_the_two_clock_sensitive_files_run_alone_one_after_the_other():
    # TC-F3-05, PS-04, PS-10: not in any shard of parts 1 to 3; in the clock entry each on its own, in this order
    main = listed(MAIN)
    assert all(kind == "shard" for kind, _ in main)
    assert not [f for _, fs in main for f in fs if f in CLOCK_FILES]
    assert listed(CLOCK) == [("alone", [CLOCK_FILES[0]]), ("alone", [CLOCK_FILES[1]])]
    assert listed(MAIN, ABF_PLATFORM_PART="clock") == [("alone", [CLOCK_FILES[0]]), ("alone", [CLOCK_FILES[1]])]
    for part in "123":
        assert not [f for f in _files(listed(MAIN, ABF_PLATFORM_PART=part)) if f in CLOCK_FILES]


def test_ps05_the_three_parts_are_non_empty_shards():
    # PS-05
    for part in "123":
        got = listed(MAIN, ABF_PLATFORM_PART=part)
        assert got and all(kind == "shard" and fs for kind, fs in got), part


def test_ps06_every_listed_file_exists():
    # PS-06
    for part in PARTS:
        for f in _files(listed(MAIN, ABF_PLATFORM_PART=part)):
            assert (PLATFORM_DIR / f).is_file(), f


def test_ps07_the_default_part_is_1():
    # PS-07
    assert listed(MAIN) == listed(MAIN, ABF_PLATFORM_PART="1")


def test_ps08_the_old_value_main_and_a_fourth_part_are_refused():
    # PS-08
    for bad in ("main", "4"):
        r = subprocess.run(["bash", str(MAIN)], env=_clean_env(ABF_PLATFORM_PART=bad), capture_output=True, text=True, timeout=60)
        assert r.returncode == 1 and "must be 1, 2, 3, clock or all" in r.stdout, (bad, r.stdout)


def _named(script_text):
    """The test files the wrapper names itself: the lines of the fixed lists, and the clock files."""
    named = set(CLOCK_FILES)
    for line in script_text.splitlines():
        if re.fullmatch(r"(tests/test_\w+\.py ?)+", line):
            named.update(line.split())
    return named


def _copy_platform(tmp_path, n_new, drop_rest=False):
    dst = tmp_path / "platform"
    shutil.copytree(PLATFORM_DIR, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
    if drop_rest:
        named = _named(MAIN.read_text())
        for f in (dst / "tests").glob("test_*.py"):
            if "tests/" + f.name not in named:
                f.unlink()
    for i in range(n_new):
        (dst / "tests" / f"test_zz_new_{i}.py").write_text("")
    return dst


def test_ps09_ps32_new_files_are_spread_over_the_three_parts(tmp_path):
    # PS-09, PS-32
    dst = _copy_platform(tmp_path, 7)
    seen = {}
    for part in "123":
        for f in _files(listed(MAIN, ABF_PLATFORM_PART=part, ABF_PLATFORM_DIR=str(dst))):
            seen.setdefault(f, []).append(part)
    for i in range(7):
        assert len(seen[f"tests/test_zz_new_{i}.py"]) == 1
    named = _named(MAIN.read_text())
    rest = sorted((f for f in seen if f not in named), key=lambda s: s.encode())
    counts = {p: 0 for p in "123"}
    for i, f in enumerate(rest):
        assert seen[f] == [str((i % 3) + 1)], (i, f, seen[f])
        counts[seen[f][0]] += 1
    assert max(counts.values()) - min(counts.values()) <= 1, counts


def test_ps32_on_the_real_tree_the_rest_goes_round_robin():
    # PS-32
    named = _named(MAIN.read_text())
    seen = {}
    for part in "123":
        for f in _files(listed(MAIN, ABF_PLATFORM_PART=part)):
            seen.setdefault(f, []).append(part)
    rest = sorted((f for f in _all_files() if f not in named), key=lambda s: s.encode())
    assert rest
    for i, f in enumerate(rest):
        assert seen[f] == [str((i % 3) + 1)], (i, f, seen.get(f))


def test_ps33_empty_rest_shards_are_not_printed(tmp_path):
    # PS-33
    dst = _copy_platform(tmp_path, 1, drop_rest=True)
    (dst / "tests" / "test_zz_new_0.py").rename(dst / "tests" / "test_zz_only.py")
    found = 0
    for part in "123":
        r = subprocess.run(["bash", str(MAIN)], env=_clean_env(ABF_PLATFORM_LIST="1", ABF_PLATFORM_PART=part, ABF_PLATFORM_DIR=str(dst)),
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        for line in r.stdout.splitlines():
            assert line.partition(":")[2].strip(), line
            found += line.count("test_zz_only.py")
    assert found == 1


def test_ps34_ps35_the_four_entries_list_in_the_same_format():
    # PS-34, PS-35
    for e in ENTRIES:
        got = listed(e)
        assert got
        for kind, fs in got:
            assert fs and all(f.startswith("tests/") for f in fs)
    for e, part in ((SHARD2, "2"), (SHARD3, "3")):
        code = [ln for ln in e.read_text().splitlines() if ln.strip() and not ln.strip().startswith("#")]
        assert len(code) == 3, code
        assert code[0].startswith("HERE=")
        assert code[1] == f"export ABF_PLATFORM_PART={part}"
        assert code[2] == 'exec bash "$HERE/platform_test.sh" "$@"'
        assert listed(e) == listed(MAIN, ABF_PLATFORM_PART=part)


def test_ps36_nobody_names_the_old_part_main():
    # PS-36
    for d in ("tests", "docs"):
        for p in (REPO_ROOT / d).rglob("*"):
            if p.is_file() and p.suffix in (".sh", ".md", ".txt", ".py") and p.name != "run_all_retry_test.sh":
                assert "ABF_PLATFORM_PART=main" not in p.read_text(errors="ignore"), p


def test_ps11_every_script_that_selects_a_part_is_covered_by_the_quarantine_rule():
    # PS-11
    pat = re.compile(r"^\s*(export\s+)?ABF_PLATFORM_PART=", re.M)
    for p in (REPO_ROOT / "tests").glob("*.sh"):
        if p.name in ("run_all_retry_test.sh", "platform_test.sh"):
            continue
        if pat.search(p.read_text()):
            assert p.name == "platform_clock_test.sh" or re.fullmatch(r"platform_shard_\d+_test\.sh", p.name), p.name
    assert "platform_shard_*_test.sh" in (REPO_ROOT / "tests" / "run_all.sh").read_text()


def test_tcf3_06_run_all_lists_the_four_entries_and_each_ends_in_test_sh():
    # TC-F3-06, PS-12
    r = subprocess.run(["bash", str(REPO_ROOT / "tests" / "run_all.sh"), "--list", "--allow-msys"], capture_output=True, text=True,
                       timeout=60, env=_clean_env())
    names = r.stdout.split()
    assert "run_all.sh" not in names
    for e in ENTRIES:
        assert e.name in names and e.name.endswith("_test.sh"), e.name


def test_ps46_the_files_the_constitution_names_are_run_exactly_once():
    # PS-46
    allf = _files(listed(MAIN, ABF_PLATFORM_PART="all"))
    for n in ("test_actions_layer", "test_human_channel", "test_resume_entrypoints", "test_keep_submissions", "test_nextflow_e2e",
              "test_secrets", "test_confirm_page"):
        assert allf.count(f"tests/{n}.py") == 1, n


def test_ps61_there_are_exactly_two_shard_scripts():
    # PS-61
    assert sorted(p.name for p in (REPO_ROOT / "tests").glob("platform_shard_*_test.sh")) == ["platform_shard_2_test.sh", "platform_shard_3_test.sh"]


def test_tcf3_04_the_limit_of_a_test_was_not_raised_and_its_comment_is_there():
    # TC-F3-04, PS-26, PS-40
    text = (REPO_ROOT / "tests" / "run_all.sh").read_text()
    m = re.search(r"^PER_TEST_TIMEOUT=(\d+)\s+#\s*(.*)$", text, re.M)
    assert m and int(m.group(1)) == 300 and "only catches a hang" in m.group(2)
    assert "~30s" not in m.group(2)
    assert not re.search(r"\d\s*(s|sec|seconds)\b", m.group(2))


def test_ps27_to_ps30_ps41_ps43_docs_name_the_four_entries():
    # PS-27, PS-28, PS-29, PS-30, PS-41, PS-43
    names = [e.name for e in ENTRIES]
    testing = (REPO_ROOT / "docs" / "TESTING.md").read_text()
    assert "About 100 seconds" not in testing and "default 300" in testing
    assert all(n in testing for n in names)
    assert "The machine part is `tests/platform_test.sh`" not in testing
    assert "Several minutes, mostly the four platform entries (" in testing
    platform = (REPO_ROOT / "docs" / "PLATFORM.md").read_text()
    assert all(n in platform for n in names) and "every test file but two" not in platform
    assert "ABF_PLATFORM_PART=all" in platform


def test_ps31_the_comments_no_longer_say_two_entries():
    # PS-31
    for e in ENTRIES:
        text = e.read_text()
        assert "Two run_all.sh entries" not in text and "about half" not in text, e.name


def _collected(script):
    r = subprocess.run(["bash", str(script)], env=_clean_env(ABF_PYTEST_ARGS="--collect-only -q"), capture_output=True, text=True, timeout=600)
    assert r.returncode == 0 and "platform tests: pytest exit 0" in r.stdout, r.stdout[-600:]
    return sorted({"tests/" + m.group(1) for m in re.finditer(r"^tests/(test_\w+\.py)::", r.stdout, re.M)})


def test_ps13_ps14_each_entry_collects_its_own_files_and_together_all(warm):  # noqa: F811
    # PS-13, PS-14
    union = []
    for e in ENTRIES:
        got = _collected(e)
        assert got == sorted(set(_files(listed(e)))), e.name
        union += got
    assert len(set(union)) == len(union)
    assert sorted(union) == _all_files()


def test_ps15_ps16_the_second_entry_pays_no_bootstrap(tmp_path, warm):  # noqa: F811
    # PS-15, PS-16
    first = subprocess.run(["bash", str(MAIN)], env=_clean_env(ABF_PLATFORM_PREFLIGHT_ONLY="2"), capture_output=True, text=True, timeout=600)
    assert first.returncode == 0, first.stdout[-400:]
    bindir = tmp_path / "fake"
    bindir.mkdir()
    log = tmp_path / "curl.log"
    (bindir / "curl").write_text(f'#!/bin/sh\necho "$@" >> "{log}"\nexit 1\n')
    (bindir / "curl").chmod(0o755)
    second = subprocess.run(["bash", str(SHARD2)], env=_clean_env(ABF_PLATFORM_PREFLIGHT_ONLY="2", PATH=f"{bindir}:{os.environ['PATH']}"),
                            capture_output=True, text=True, timeout=600)
    assert second.returncode == 0, second.stdout[-400:]
    assert "installing platform test dependencies" not in second.stdout
    assert not log.exists() or log.read_text() == ""


def test_tcf3_03_nothing_may_be_skipped_on_ci_in_any_entry(tmp_path, warm):  # noqa: F811
    # TC-F3-03, PS-17: no Java on CI is a failure of every entry, as it is of the first one
    path = str(_bin_without_java(tmp_path))
    for script in ENTRIES:
        ci = subprocess.run(["bash", str(script)], env=_clean_env(PATH=path, CI="true"), capture_output=True, text=True, timeout=300)
        assert ci.returncode != 0 and "FAIL (CI=true)" in ci.stdout, (script.name, ci.stdout[-400:])
