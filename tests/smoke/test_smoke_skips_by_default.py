"""Self-proof tests: skip logic, URL rules, marker, scripts/smoke.sh.

These are NOT marked smoke and never skip on a missing SMOKE_BASE_URL.
Child pytest runs always use -m smoke, so they never select these again.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from smoke_support import MARKERS_OPT, FakeSite

ROOT = Path(__file__).resolve().parents[2]
SKIP_REASON = "SMOKE_BASE_URL is not set"


def _env(**set_vars):
    env = dict(os.environ)
    env.pop("SMOKE_BASE_URL", None)
    env.update(set_vars)
    return env


def _pytest(env, args, cwd=ROOT):
    cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"] + args
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
    return proc, proc.stdout + proc.stderr


# TC-001
@pytest.mark.parametrize("value", [None, "  "])
def test_tc001_skip_when_env_unset_or_blank(value):
    env = _env() if value is None else _env(SMOKE_BASE_URL=value)
    proc, out = _pytest(env, ["-o", MARKERS_OPT, "-m", "smoke", "tests/smoke", "-rs"])
    assert proc.returncode == 0, out
    assert "skipped" in out
    assert SKIP_REASON in out
    m = re.search(r"(\d+) skipped", out)
    assert m and int(m.group(1)) >= 5
    for word in ("passed", "failed"):
        assert word not in out
    assert not re.search(r"\berrors?\b", out)


# TC-001 (direct run of the probe file: probes skipped, fake-site tests pass)
def test_tc001_direct_run_skips_probes_and_passes_selftests():
    proc, out = _pytest(_env(), ["tests/smoke/test_smoke.py", "-rs"])
    assert proc.returncode == 0, out[-800:]
    assert "skipped" in out and "passed" in out
    assert SKIP_REASON in out


# TC-002
def test_tc002_no_default_url_in_sources():
    files = sorted((ROOT / "tests" / "smoke").glob("*.py")) + [ROOT / "scripts" / "smoke.sh"]
    assert len(files) >= 4
    pat = re.compile(r"https?://(?:[^\s/@'\"]*@)?([^\s/'\":?#]+)")
    allowed = {"127.0.0.1", "localhost", "example.invalid"}
    bad = []
    for f in files:
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for host in pat.findall(line):
                if host not in allowed:
                    bad.append("%s:%d" % (f.name, n))
    assert bad == []


# TC-003
@pytest.mark.parametrize("url,secret", [("http://u:p@127.0.0.1:1", "u:p"),
                                        ("ftp://127.0.0.1:1", "ftp://")])
def test_tc003_rejects_bad_urls(url, secret):
    proc, out = _pytest(_env(SMOKE_BASE_URL=url),
                        ["-o", MARKERS_OPT, "-m", "smoke", "tests/smoke", "-rs"])
    assert proc.returncode != 0
    assert "failed" in out
    assert "passed" not in out and "skipped" not in out
    assert secret not in out
    assert "127.0.0.1:1" not in out


# TC-014
def test_tc014_marker_registered_via_option_no_config_files():
    for name in ("pytest.ini", "conftest.py", "pyproject.toml"):
        assert not (ROOT / name).exists()
    assert not (ROOT / "tests" / "smoke" / "conftest.py").exists()
    proc, out = _pytest(_env(), ["--strict-markers", "-o", MARKERS_OPT, "-m", "smoke",
                                 "tests/smoke", "--collect-only", "-q"])
    assert proc.returncode == 0, out
    assert "Unknown pytest.mark" not in out and "PytestUnknownMarkWarning" not in out
    probes = [l for l in out.splitlines() if "test_smoke.py::" in l]
    assert len(probes) >= 5


def _smoke_sh(env, cwd=ROOT):
    env = dict(env)
    env["SMOKE_PYTHON"] = sys.executable
    proc = subprocess.run(["bash", str(ROOT / "scripts" / "smoke.sh")], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, proc.stdout + proc.stderr


# TC-015
def test_tc015_smoke_sh_unset_exits_2():
    proc, out = _smoke_sh(_env())
    assert proc.returncode == 2
    assert "SMOKE_BASE_URL is not set: nothing was checked." in out
    assert "Usage" in out or "usage" in out


# TC-016
def test_tc016_smoke_sh_green(tmp_path):
    with FakeSite() as site:
        proc, out = _smoke_sh(_env(SMOKE_BASE_URL=site.base), cwd=tmp_path)
    assert proc.returncode == 0, out[-800:]
    assert "passed" in out and "Smoke checks passed." in out
    assert "Unknown pytest.mark" not in out and "PytestUnknownMarkWarning" not in out


# TC-017
def test_tc017_smoke_sh_failure_prints_rollback_hint():
    with FakeSite(drop="csp") as site:
        proc, out = _smoke_sh(_env(SMOKE_BASE_URL=site.base))
    assert proc.returncode != 0
    assert "Smoke checks passed." not in out
    hint = out[out.index("Smoke checks failed."):].strip().splitlines()
    assert len(hint) <= 3
    text = " ".join(hint)
    for needle in ("deploy/backup.sh", "pip install ./platform", "docs/OPERATIONS.md"):
        assert needle in text
