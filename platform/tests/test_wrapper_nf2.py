# Nothing existing: tests of the second pinned Nextflow in tests/platform_test.sh, the wrapper that runs this folder; it exists only in this repo.
"""The second pinned pair (Nextflow 25.10.4, nf-tower 1.17.5) is pinned and checked like the first (feature 007b, TC-054)."""
import re
import shutil

import pytest

from helpers import REPO_ROOT
from test_wrapper import REAL_CACHE, _clean_env, _skipped_line, _wrapper

PINS = REPO_ROOT / "platform" / "tests" / "pins.env"
KEYS = ("NF_LAUNCHER_SHA256", "NF_DIST_SHA256", "NFTOWER_SHA256",
        "NF2_LAUNCHER_SHA256", "NF2_DIST_SHA256", "NFTOWER2_SHA256")


def _pins():
    out = {}
    for ln in PINS.read_text().splitlines():
        m = re.match(r"^([A-Z0-9_]+)=(.*)$", ln)
        if m:
            out[m.group(1)] = m.group(2)
    return out


@pytest.fixture(scope="module")
def warm2():
    """One real preflight of both pairs, so the cache holds everything before the failure cases below."""
    text = (REPO_ROOT / "tests" / "platform_test.sh").read_text()
    # a wrapper that does not know the value 2 would run the whole suite, this file included
    assert 'PREFLIGHT_ONLY:-}" = "2"' in text, "tests/platform_test.sh does not set up the second Nextflow pair"
    r = _wrapper(_clean_env(ABF_PLATFORM_PREFLIGHT_ONLY="2"))
    if "E2E SKIPPED" in r.stdout:
        raise AssertionError("the second pair cannot be skipped here: " + r.stdout[-400:])
    assert r.returncode == 0 and "both pairs" in r.stdout, r.stdout + r.stderr
    return r


def test_tc054_both_pairs_are_pinned_with_a_sha256_each():
    # TC-054
    pins = _pins()
    assert pins["NF_VERSION"] == "26.04.7" and pins["NFTOWER_VERSION"] == "1.28.3"
    assert pins["NF2_VERSION"] == "25.10.4" and pins["NFTOWER2_VERSION"] == "1.17.5"
    for k in KEYS:
        assert re.fullmatch(r"[0-9a-f]{64}", pins[k]), k
    assert len({pins[k] for k in KEYS}) == 6, "six different files"
    for k in ("NF2_LAUNCHER_URL", "NF2_DIST_URL", "NFTOWER2_URL"):
        assert pins["NF2_VERSION"] in pins[k] or pins["NFTOWER2_VERSION"] in pins[k], k
    wrapper = (REPO_ROOT / "tests" / "platform_test.sh").read_text()
    for name in ("NF2_LAUNCHER_SHA256", "NF2_DIST_SHA256", "NFTOWER2_SHA256", "ABF_NXF2_LAUNCHER", "ABF_NXF2_HOME"):
        assert name in wrapper, name


def test_tc054_the_second_pair_is_downloaded_unpacked_and_exported(warm2):
    # TC-054
    assert (REAL_CACHE / "downloads" / "nextflow-25.10.4").is_file()
    assert (REAL_CACHE / "downloads" / "nextflow-25.10.4-dist").is_file()
    assert (REAL_CACHE / "downloads" / "nf-tower-1.17.5.zip").is_file()
    assert (REAL_CACHE / "nxf-home-25.10.4" / "plugins" / "nf-tower-1.17.5" / "classes").is_dir()


@pytest.mark.parametrize("key,ci", [("ABF_NF2_LAUNCHER_SHA256", None), ("ABF_NF2_DIST_SHA256", None),
                                    ("ABF_NFTOWER2_SHA256", None), ("ABF_NF2_DIST_SHA256", "true")])
def test_tc054_a_wrong_sha256_of_the_second_pair_stops_the_run_in_both_modes(warm2, key, ci):
    # TC-054: a mismatch is a failure, never a skip
    extra = {key: "0" * 64, "ABF_PLATFORM_PREFLIGHT_ONLY": "2"}
    if ci:
        extra["CI"] = ci
    r = _wrapper(_clean_env(**extra))
    assert r.returncode != 0, (key, ci)
    assert "sha256 mismatch" in r.stdout, r.stdout
    assert "E2E SKIPPED" not in r.stdout


def test_tc054_without_the_second_pair_ci_fails_and_a_local_run_skips_loudly(tmp_path, warm2):
    # TC-054: Nextflow 25.10.4 cannot be downloaded (the first pair is in the fresh cache already)
    cache = tmp_path / "cache"
    (cache / "downloads").mkdir(parents=True)
    for f in list((REAL_CACHE / "downloads").glob("nextflow-26*")) + [REAL_CACHE / "downloads" / "nf-tower-1.28.3.zip"]:
        shutil.copy(f, cache / "downloads" / f.name)
    kw = dict(ABF_PLATFORM_CACHE=str(cache), ABF_NF2_LAUNCHER_URL="http://127.0.0.1:9/nextflow",
              ABF_PLATFORM_PREFLIGHT_ONLY="2")
    ci = _wrapper(_clean_env(CI="true", **kw))
    assert ci.returncode != 0 and "download failed" in ci.stdout, ci.stdout
    local = _wrapper(_clean_env(**kw))
    assert local.returncode == 0, local.stdout + local.stderr
    line = _skipped_line(local.stdout)
    assert line and "download failed" in line[0], local.stdout
    assert "would be skipped" in local.stdout
