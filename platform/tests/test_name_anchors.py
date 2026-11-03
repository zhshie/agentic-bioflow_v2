# Nothing existing: the owner/name identifier rule of the launch params is ours (116b ruling 3); this file checks its anchor against a trailing newline.
"""regex-dollar-newline TC-030..032: `build.OWNER_NAME` must end with \Z, so "nf-core/rnaseq\n" is not taken for an identifier."""
import os

import pytest

from human_harness import World
from owner_harness import Duo


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def _confine(d, params):
    from abf_launch import build
    area = os.path.realpath(d.area(d.a))
    bundle = {"samplesheet": [["sample"]], "path_columns": [], "params": params}
    return build._confine(d.state, bundle, area, [])


def test_tc030_trailing_newline_identifier_is_refused(d):
    # regex-dollar-newline TC-030
    from abf_launch import build
    with pytest.raises(build.Refusal):
        _confine(d, {"ref": "nf-core/rnaseq\n"})


def test_tc031_plain_identifier_still_passes(d):
    # regex-dollar-newline TC-031
    from abf_launch import build
    area = os.path.realpath(d.area(d.a))
    assert build._param_path("nf-core/rnaseq", area, []) is None
    _confine(d, {"ref": "nf-core/rnaseq"})


def test_tc032_second_legal_identifier_is_not_a_path(d):
    # regex-dollar-newline TC-032
    from abf_launch import build
    area = os.path.realpath(d.area(d.a))
    assert build._param_path("my_org.x/pipe-1.0", area, []) is None
