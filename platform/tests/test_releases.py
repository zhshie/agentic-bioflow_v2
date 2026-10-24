# Nothing existing: nf-core's CLI and the plugin's prepare_launch.sh each look up tags on their own; the platform has no function to reuse, so the pick logic is tested here.
"""release-tag-pick: choose the newest launchable release from a list of tag names.
Test cases TC-001 ... TC-071 are in specs/release-tag-pick/test-case.md; T1 ... T22 are the plan's numbers.
Everything is a fake fetch function and files in tmp_path: no network, no program is started."""
import json
import os
import re
from pathlib import Path

import pytest

from abf_platform import releases
from abf_platform.releases import lookup, parse_ls_remote, pick_latest, repo_of, usable

NOW = 1760000000.0
KEYS = {"pipeline", "revision", "source", "checked_at", "why"}


class Fetch:
    def __init__(self, result=None, exc=None):
        self.result, self.exc, self.calls = result, exc, []

    def __call__(self, repo):
        self.calls.append(repo)
        if self.exc is not None:
            raise self.exc
        return self.result


class Clock:
    def __init__(self, t=NOW):
        self.t = t

    def __call__(self):
        return self.t


def _seed(path, repo="nf-core/ampliseq", revision="3.0.0", at=NOW):
    path.write_text(json.dumps({repo: {"revision": revision, "checked_at": at}}))


def test_t1_repo_of_accepts():
    # T1 / TC-001 TC-002 TC-003
    assert repo_of("ampliseq") == "nf-core/ampliseq"
    assert repo_of("nf-core/ampliseq") == "nf-core/ampliseq"
    assert repo_of("lab/own-flow") == "lab/own-flow"


@pytest.mark.parametrize("bad", ["", "../x", "a/b/c", "nf core/x", None])
def test_t2_repo_of_rejects(bad):
    # T2 / TC-004 ... TC-008
    with pytest.raises(ValueError) as e:
        repo_of(bad)
    msg = str(e.value)
    assert re.search(r"[一-鿿]", msg) and re.search(r"[A-Za-z]{3}", msg)


@pytest.mark.parametrize("tag", ["3.0.0", "v2.1", "1.2.3.4", "1.0"])
def test_t3_usable_true(tag):
    # T3 / TC-009
    assert usable(tag) is True


@pytest.mark.parametrize("tag", ["3.0.0dev", "3.0.0-rc1", "dev", "master",
                                 "0123456789abcdef0123456789abcdef01234567", "3.0.0\n", ""])
def test_t4_usable_false(tag):
    # T4 / TC-010 ... TC-014
    assert usable(tag) is False


def test_t5_numeric_not_string_order():
    # T5 / TC-015
    assert pick_latest(["3.9.0", "3.10.0", "3.2.1"]) == "3.10.0"


def test_t6_prerelease_and_branch_excluded():
    # T6 / TC-016
    assert pick_latest(["2.18.0", "3.0.0", "3.0.0dev", "dev"]) == "3.0.0"


def test_t7_v_prefix_and_short_versions():
    # T7 / TC-017 TC-018 TC-019 TC-020
    assert pick_latest(["v3.0.0", "3.0.0"]) == "3.0.0"
    assert pick_latest(["3.0.0", "v3.0.0"]) == "3.0.0"
    assert pick_latest(["3.0", "3.0.1"]) == "3.0.1"
    assert pick_latest(["v2.1", "1.0"]) == "v2.1"


def test_t8_nothing_usable():
    # T8 / TC-021 TC-022 TC-023
    assert pick_latest([]) is None
    assert pick_latest(["dev", "master"]) is None
    assert pick_latest([None, 3, "2.0.0"]) == "2.0.0"


def test_t9_parse_ls_remote():
    # T9 / TC-024
    sha = "0123456789abcdef0123456789abcdef01234567"
    text = "%s\trefs/tags/2.18.0\nnotabline\n   \n%s\trefs/tags/3.0.0\n" % (sha, sha)
    assert parse_ls_remote(text) == ["2.18.0", "3.0.0"]


def test_t10_first_lookup_fetches_and_caches(tmp_path):
    # T10 / TC-025 TC-026 TC-027 TC-028
    cp = tmp_path / "c.json"
    f = Fetch(["2.18.0", "3.0.0"])
    r = lookup("nf-core/ampliseq", f, cache_path=cp, clock=Clock())
    assert (r["revision"], r["source"], r["pipeline"]) == ("3.0.0", "fetched", "nf-core/ampliseq")
    assert r["checked_at"] == NOW
    assert len(f.calls) == 1
    assert json.loads(cp.read_text())["nf-core/ampliseq"] == {"revision": "3.0.0", "checked_at": NOW}


def test_t11_fresh_cache_skips_fetch(tmp_path):
    # T11 / TC-029 TC-030 TC-031 TC-032
    cp = tmp_path / "c.json"
    f = Fetch(["3.0.0"])
    lookup("nf-core/ampliseq", f, cache_path=cp, clock=Clock())
    for dt in (3600, 86399, 0):
        r = lookup("nf-core/ampliseq", f, cache_path=cp, clock=Clock(NOW + dt))
        assert (r["source"], r["revision"]) == ("cache", "3.0.0")
    assert len(f.calls) == 1


def test_t12_exactly_ttl_is_expired(tmp_path):
    # T12 / TC-033
    cp = tmp_path / "c.json"
    f = Fetch(["3.0.0"])
    lookup("nf-core/ampliseq", f, cache_path=cp, clock=Clock())
    r = lookup("nf-core/ampliseq", f, cache_path=cp, clock=Clock(NOW + 86400))
    assert r["source"] == "fetched" and len(f.calls) == 2


def test_t13_future_checked_at_is_expired(tmp_path):
    # T13 / TC-034
    cp = tmp_path / "c.json"
    _seed(cp, at=NOW + 100)
    f = Fetch(["3.0.0"])
    r = lookup("nf-core/ampliseq", f, cache_path=cp, clock=Clock())
    assert r["source"] == "fetched" and len(f.calls) == 1


def test_t14_newer_release_replaces_cache_only(tmp_path):
    # T14 / TC-035 TC-036 TC-037
    cp = tmp_path / "c.json"
    _seed(cp, revision="2.18.0", at=NOW - 90000)
    r = lookup("nf-core/ampliseq", Fetch(["2.18.0", "3.0.0"]), cache_path=cp, clock=Clock())
    assert (r["revision"], r["source"]) == ("3.0.0", "fetched")
    assert set(r) == KEYS
    assert json.loads(cp.read_text())["nf-core/ampliseq"]["revision"] == "3.0.0"


def test_t15_fetch_fails_with_old_cache(tmp_path):
    # T15 / TC-038 TC-039 TC-040 TC-055
    cp = tmp_path / "c.json"
    _seed(cp, revision="2.18.0", at=NOW - 90000)
    before = cp.read_text()
    r = lookup("nf-core/ampliseq", Fetch(exc=OSError("network down")), cache_path=cp, clock=Clock())
    assert (r["source"], r["revision"]) == ("stale-cache", "2.18.0")
    assert r["why"] and "network down" in r["why"] and "Traceback" not in r["why"]
    assert cp.read_text() == before


def test_t16_fetch_fails_without_cache_then_retries(tmp_path):
    # T16 / TC-041 TC-042
    cp = tmp_path / "c.json"
    r = lookup("nf-core/ampliseq", Fetch(exc=RuntimeError("boom")), cache_path=cp, clock=Clock())
    assert r["revision"] is None and r["source"] == "none"
    f = Fetch(["3.0.0"])
    r = lookup("nf-core/ampliseq", f, cache_path=cp, clock=Clock(NOW + 5))
    assert (r["revision"], r["source"]) == ("3.0.0", "fetched") and len(f.calls) == 1


def test_t17_no_usable_tag(tmp_path):
    # T17 / TC-043
    r = lookup("nf-core/ampliseq", Fetch(["dev"]), cache_path=tmp_path / "c.json", clock=Clock())
    assert r["revision"] is None
    assert "沒有可用的 release tag" in r["why"]


@pytest.mark.parametrize("content", ["not json", "[]", '{"nf-core/x": 5}'])
def test_t18_broken_cache_is_ignored(tmp_path, content):
    # T18 / TC-044 TC-045 TC-046
    cp = tmp_path / "c.json"
    cp.write_text(content)
    f = Fetch(["3.0.0"])
    r = lookup("nf-core/x", f, cache_path=cp, clock=Clock())
    assert r["revision"] == "3.0.0" and len(f.calls) == 1
    assert json.loads(cp.read_text())["nf-core/x"]["revision"] == "3.0.0"


def test_t19_two_pipelines_one_file(tmp_path):
    # T19 / TC-047 TC-048
    cp = tmp_path / "c.json"
    fa, fb = Fetch(["3.0.0"]), Fetch(["1.4.0"])
    lookup("nf-core/ampliseq", fa, cache_path=cp, clock=Clock())
    r = lookup("lab/own-flow", fb, cache_path=cp, clock=Clock(NOW + 10))
    assert r["revision"] == "1.4.0"
    data = json.loads(cp.read_text())
    assert data["nf-core/ampliseq"] == {"revision": "3.0.0", "checked_at": NOW}
    assert data["lab/own-flow"] == {"revision": "1.4.0", "checked_at": NOW + 10}
    r = lookup("nf-core/ampliseq", fa, cache_path=cp, clock=Clock(NOW + 20))
    assert (r["source"], r["revision"]) == ("cache", "3.0.0")


def test_t20_no_cache_path_touches_no_file(tmp_path):
    # T20 / TC-049
    r = lookup("nf-core/ampliseq", Fetch(["3.0.0"]), cache_path=None, clock=Clock())
    assert r["revision"] == "3.0.0"
    assert list(tmp_path.iterdir()) == []


def test_t21_failed_write_keeps_old_file(tmp_path, monkeypatch):
    # T21 / TC-050 TC-051 TC-052
    cp = tmp_path / "c.json"
    _seed(cp, revision="2.18.0", at=NOW - 90000)
    before = cp.read_text()

    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(os, "replace", boom)
    r = lookup("nf-core/ampliseq", Fetch(["3.0.0"]), cache_path=cp, clock=Clock())
    assert isinstance(r, dict) and set(r) == KEYS
    assert cp.read_text() == before
    assert [p.name for p in tmp_path.iterdir()] == ["c.json"]


def test_tc053_fetch_gets_full_name():
    # TC-053
    f = Fetch(["3.0.0"])
    r = lookup("ampliseq", f, clock=Clock())
    assert f.calls == ["nf-core/ampliseq"] and r["pipeline"] == "nf-core/ampliseq"


def test_tc054_bad_name_returns_dict():
    # TC-054
    f = Fetch(["3.0.0"])
    r = lookup("../x", f, clock=Clock())
    assert set(r) == KEYS and r["revision"] is None and f.calls == []


def test_t22_source_has_no_network_or_process_words():
    # T22 / TC-056
    src = Path(releases.__file__).read_text(encoding="utf-8")
    for word in ("urllib", "socket", "subprocess", "threading", "requests",
                 "stat" + "ion", "ss" + "h", "nextflow run"):
        assert word not in src, word
