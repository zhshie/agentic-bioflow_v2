# Nothing existing: pytest fixtures for this folder's tests; there is no shared fixture library for a receiver, a token store and a fake clock.
"""Fixtures for the platform tests (feature 008)."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import Clock, Platform  # noqa: E402


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def plat(tmp_path, clock):
    return Platform(tmp_path / "plat", clock=clock)


@pytest.fixture
def token(plat):
    return plat.new_token()


@pytest.fixture(scope="session")
def e2e_cfg():
    """Where the wrapper put the pinned Nextflow. Skips loudly, never silently."""
    reason = os.environ.get("ABF_E2E_SKIP_REASON")
    if reason:
        pytest.skip("E2E SKIPPED: " + reason)
    launcher = os.environ.get("ABF_NXF_LAUNCHER")
    if not launcher:
        pytest.fail("the end-to-end tests need the pinned Nextflow: run them through tests/platform_test.sh")
    return {
        "launcher": launcher,
        "home": os.environ["ABF_NXF_HOME"],
        "ver": os.environ["ABF_NXF_VER"],
    }
