# Nothing existing: tests of tests/platform_test.sh, the wrapper that runs this folder; it exists only in this repo.
"""Wrapper tests: no silent skip, failures are visible, downloads are verified (feature 008)."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT

WRAPPER = REPO_ROOT / "tests" / "platform_test.sh"
CACHE_BASE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
REAL_CACHE = CACHE_BASE / "abf-platform"
NEEDED = ["bash", "env", "dirname", "cat", "cut", "sed", "sha256sum", "curl", "mkdir", "rm", "mv", "cp",
          "mktemp", "tee", "tail", "head", "sort", "grep", "cmp", "ls", "tr", "uname", "python3",
          "python3.10", "python3.11", "python3.12", "python3.13", "virtualenv"]


def _clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("ABF_") and k not in ("CI", "PYTEST_CURRENT_TEST")}
    env.update(extra)
    return env


def _wrapper(env, timeout=600):
    return subprocess.run(["bash", str(WRAPPER)], env=env, capture_output=True, text=True, timeout=timeout)


def _preflight_env(**extra):
    return _clean_env(ABF_PLATFORM_PREFLIGHT_ONLY="1", **extra)


@pytest.fixture(scope="module")
def warm():
    """One real preflight, so the cache and the venv exist before the failure cases below."""
    r = _wrapper(_preflight_env())
    if "E2E SKIPPED" in r.stdout:
        pytest.skip("E2E SKIPPED: " + r.stdout.strip().splitlines()[-1])
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def _bin_without_java(tmp_path):
    d = tmp_path / "bin-no-java"
    d.mkdir()
    for name in NEEDED:
        p = shutil.which(name)
        if p:
            os.symlink(p, d / name)
    assert not (d / "java").exists()
    return d


def _skipped_line(out):
    return [ln for ln in out.splitlines() if ln.startswith("E2E SKIPPED:")]


def test_tc054_missing_java_fails_on_ci_and_skips_loudly_otherwise(tmp_path, warm):
    # TC-054, case 1: no Java on PATH
    path = str(_bin_without_java(tmp_path))
    ci = _wrapper(_preflight_env(PATH=path, CI="true"))
    assert ci.returncode != 0
    assert "Java" in ci.stdout + ci.stderr
    local = _wrapper(_preflight_env(PATH=path))
    assert local.returncode == 0, local.stdout + local.stderr
    assert _skipped_line(local.stdout), local.stdout
    assert "Java" in _skipped_line(local.stdout)[0]


def test_tc054_nextflow_download_failure(tmp_path, warm):
    # TC-054, case 2: the Nextflow download address cannot be reached (fresh cache folder)
    cache = tmp_path / "cache"
    kw = dict(ABF_PLATFORM_CACHE=str(cache), ABF_NF_LAUNCHER_URL="http://127.0.0.1:9/nextflow")
    ci = _wrapper(_preflight_env(CI="true", **kw))
    assert ci.returncode != 0 and "download failed" in ci.stdout
    local = _wrapper(_preflight_env(**kw))
    assert local.returncode == 0
    assert _skipped_line(local.stdout) and "download failed" in _skipped_line(local.stdout)[0]


def test_tc054_plugin_download_failure(tmp_path, warm):
    # TC-054, case 3: only the plugin download fails
    cache = tmp_path / "cache"
    (cache / "downloads").mkdir(parents=True)
    for f in (REAL_CACHE / "downloads").glob("nextflow-*"):
        shutil.copy(f, cache / "downloads" / f.name)
    kw = dict(ABF_PLATFORM_CACHE=str(cache), ABF_NFTOWER_URL="http://127.0.0.1:9/nf-tower.zip")
    ci = _wrapper(_preflight_env(CI="true", **kw))
    assert ci.returncode != 0 and "download failed" in ci.stdout
    local = _wrapper(_preflight_env(**kw))
    assert local.returncode == 0
    assert _skipped_line(local.stdout) and "nf-tower" in _skipped_line(local.stdout)[0]


def test_tc054_skipped_tests_are_counted_in_the_summary(tmp_path, warm):
    # TC-054: not CI, Java hidden, the end-to-end module only: its tests are skipped, and the summary says how many.
    path = str(_bin_without_java(tmp_path))
    r = _wrapper(_clean_env(PATH=path, ABF_PYTEST_TARGETS="tests/test_nextflow_e2e.py"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert _skipped_line(r.stdout)
    m = re.search(r"platform tests: pytest exit 0, (\d+) skipped", r.stdout)
    assert m and int(m.group(1)) >= 5, r.stdout[-600:]
    # and on CI the same situation is a failure
    ci = _wrapper(_clean_env(PATH=path, CI="true", ABF_PYTEST_TARGETS="tests/test_nextflow_e2e.py"))
    assert ci.returncode != 0


def test_tc055_a_failing_test_makes_the_wrapper_fail_and_names_it(tmp_path, warm):
    # TC-055
    copy = tmp_path / "platform"
    shutil.copytree(PLATFORM_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
    (copy / "tests" / "test_deliberate_failure.py").write_text(
        "def test_deliberately_failing_marker():\n    assert 1 == 2\n")
    r = _wrapper(_clean_env(ABF_PLATFORM_DIR=str(copy),
                            ABF_PYTEST_TARGETS="tests/test_deliberate_failure.py"))
    assert r.returncode != 0
    assert "test_deliberately_failing_marker" in r.stdout
    assert "pytest exit 1" in r.stdout


def test_tc056_a_wrong_sha256_stops_the_run_in_both_modes(tmp_path, warm):
    # TC-056: the pinned value is wrong -> stop, even without CI
    wrong = "0" * 64
    for key in ("ABF_NF_DIST_SHA256", "ABF_NF_LAUNCHER_SHA256", "ABF_NFTOWER_SHA256"):
        for ci in (None, "true"):
            extra = {key: wrong}
            if ci:
                extra["CI"] = ci
            r = _wrapper(_preflight_env(**extra))
            assert r.returncode != 0, (key, ci)
            assert "sha256 mismatch" in r.stdout, r.stdout


def test_tc056_a_download_with_the_wrong_content_is_discarded(tmp_path, warm):
    # TC-056: a fresh download whose content does not match is removed, not used; downloads live in the cache folder.
    cache = tmp_path / "cache"
    some_file = REAL_CACHE / "downloads" / "nextflow-26.04.7"
    r = _wrapper(_preflight_env(ABF_PLATFORM_CACHE=str(cache), ABF_NF_LAUNCHER_URL="file://" + str(some_file),
                                ABF_NF_LAUNCHER_SHA256="1" * 64))
    assert r.returncode != 0 and "sha256 mismatch" in r.stdout
    assert not (cache / "downloads" / "nextflow-26.04.7").exists()
    assert not list((cache / "downloads").glob("*.part*"))
    # the real downloads are in the cache folder, never inside the repository
    assert str(REPO_ROOT) not in str(REAL_CACHE)
