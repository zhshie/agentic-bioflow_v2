# Nothing existing: the only existing check (test_launch_bundle.py:531) tries names ending in a newline; no test asks whether the config files the launch itself writes into the folder are refused.
"""records.name_ok refuses the cloud config files the launch writes (feature 007b, FR-011)."""
import base64

import pytest

from abf_platform import records
from abf_station import fetch

CLOUD = ["gcb.config", "aws.config", "az" "ure.config"]
OLD_FIVE = ["tower.token", "params.yaml", "head.sh", "nextflow.config", "samplesheet.csv"]


@pytest.mark.parametrize("name", CLOUD)
def test_the_platform_refuses_every_file_the_launch_writes_that_is_not_a_record(name):
    # TC-001, TC-002, TC-003
    assert records.name_ok(name) is False


@pytest.mark.parametrize("name", CLOUD)
def test_store_files_does_not_write_them(tmp_path, name):
    # TC-004, TC-005, TC-006, TC-007
    data = base64.b64encode(b"SECRET_CONFIG").decode()
    out = records.store_files(tmp_path, "run-one", [{"name": name, "data": data}])
    assert out["files"] == []
    assert any(name in why and "not a record of Nextflow" in why for why in out["refused"])
    assert not (tmp_path / "run-one" / name).exists()
    assert "SECRET_CONFIG" not in repr(out)


@pytest.mark.parametrize("name", [".nextflow.log", ".nextflow.log.3", ".nextflow/history", "trace-1.txt",
                                  "trace-2026-10-29_1.txt", "params.txt", "head.log", "aws.config.txt",
                                  "trace.txt", "trace-3.txt", ".nextflow.log.12"])
def test_real_records_still_pass(name):
    # TC-008 to TC-012, TC-014
    assert records.name_ok(name) is True


@pytest.mark.parametrize("name", OLD_FIVE)
def test_the_old_five_are_still_refused(name):
    # TC-013
    assert records.name_ok(name) is False


def test_platform_list_is_a_subset_of_the_station_list():
    # TC-016
    assert records._NOT_RECORDS <= fetch._NOT_RECORDS


def test_the_list_is_exactly_the_eight_names():
    # TC-017
    assert records._NOT_RECORDS == set(OLD_FIVE + CLOUD)


# records-resume-files: TC-001..TC-010, TC-011..TC-017, TC-021
_RESUME_NAMES = ["head-1.sh", "params-2.yaml", "extra-10.config", "head-123.sh"]
_OTHER_NAMES = ["head.log", "params.txt", "trace-1.txt", ".nextflow.log.2", "head-1.sh.txt", "params-x.yaml", "extra-1.json"]


@pytest.mark.parametrize("name", _RESUME_NAMES)
def test_resume_files_are_refused_by_name(name):
    assert records.name_ok(name) is False


@pytest.mark.parametrize("name", _RESUME_NAMES)
def test_store_files_does_not_write_resume_files(tmp_path, name):
    data = base64.b64encode(b"SECRET_RESUME").decode()
    out = records.store_files(tmp_path, "run-one", [{"name": name, "data": data}])
    assert out["files"] == []
    assert len(out["refused"]) == 1
    assert name in out["refused"][0] and "not a record of Nextflow" in out["refused"][0]
    assert not (tmp_path / "run-one" / name).exists()
    assert "SECRET_RESUME" not in repr(out)


@pytest.mark.parametrize("name", _OTHER_NAMES)
def test_lookalikes_and_real_records_are_still_accepted(name):
    assert records.name_ok(name) is True


def test_both_locks_agree_on_resume_files():
    for name in _RESUME_NAMES + _OTHER_NAMES:
        assert bool(records._RESUME_FILE.match(name)) == bool(fetch._RESUME_FILE.match(name)), name
