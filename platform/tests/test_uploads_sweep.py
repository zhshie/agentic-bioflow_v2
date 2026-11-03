# Nothing existing: uploads_web.sweep had no test; these are plain file-system tests under tmp_path (no network, no program started).
"""uploads-sweep-tests. Test case ids (TC-001 ...) refer to specs/uploads-sweep-tests/test-case.md. `now` is a fixed integer and every os.utime time is an integer
number of seconds, so the strict `>` in sweep is decided exactly; nothing waits."""
import os

import pytest

from abf_platform import uploads_web

NOW = 1_800_000_000
BATCH = "a" * 32
STALE = 86400


def age(path, seconds):
    os.utime(path, (NOW - seconds, NOW - seconds))


def staging(area, name=".incoming-" + BATCH, files=("1.part", "2.part")):
    """Make a staging folder with files in it; set its age last (adding or removing an entry would reset the folder's time)."""
    d = area / name
    d.mkdir()
    for f in files:
        (d / f).write_bytes(b"data-" + f.encode())
    return d


@pytest.fixture
def area(tmp_path):
    a = tmp_path / "uploads"
    a.mkdir()
    return a


def test_tc001_old_folder_is_removed(area):  # TC-001
    d = staging(area)
    age(d, STALE + 1)
    uploads_web.sweep(area, now=NOW)
    assert not d.exists()


def test_tc002_exactly_24h_is_kept(area):  # TC-002: "older" is strictly greater than
    d = staging(area)
    age(d, STALE)
    uploads_web.sweep(area, now=NOW)
    assert d.is_dir()
    assert (d / "1.part").exists() and (d / "2.part").exists()


def test_tc003_new_folder_is_kept(area):  # TC-003
    d = staging(area)
    age(d, 10)
    uploads_web.sweep(area, now=NOW)
    assert d.is_dir()
    assert (d / "1.part").exists() and (d / "2.part").exists()


def test_tc004_to_tc007_other_things_are_never_touched(area):  # TC-004, TC-005, TC-006, TC-007
    final = area / "final.fastq.gz"
    final.write_bytes(b"finished upload")
    batches = area / ".batches"
    batches.mkdir()
    (batches / "record.json").write_text("{}")
    nodot = area / "incoming-nodot"
    nodot.mkdir()
    (nodot / "x.part").write_bytes(b"x")
    nodash = area / ".incomingX"
    nodash.write_bytes(b"not a staging folder")
    for p in (final, batches, nodot, nodash):  # files are all in place before the times are set
        age(p, 10**7)
    uploads_web.sweep(area, now=NOW)
    assert final.read_bytes() == b"finished upload"
    assert (batches / "record.json").read_text() == "{}"
    assert (nodot / "x.part").read_bytes() == b"x"
    assert nodash.read_bytes() == b"not a staging folder"


def test_tc008_tc009_missing_area_is_quiet(tmp_path):  # TC-008, TC-009
    assert uploads_web.sweep(tmp_path / "nope") is None


def test_tc010_tc011_subfolder_characterization(area):  # TC-010, TC-011
    # CHARACTERIZATION of today's behaviour, NOT the wanted behaviour: discard() deletes files only, so a staging folder that holds a subfolder
    # cannot be removed and stays (its files are gone). A staging folder never holds subfolders in normal use; this test only reminds whoever changes discard().
    d = staging(area)
    (d / "sub").mkdir()
    age(d, STALE + 1)
    uploads_web.sweep(area, now=NOW)  # must not raise
    assert d.is_dir()
    assert not (d / "1.part").exists() and not (d / "2.part").exists()
    assert (d / "sub").is_dir()


def test_tc012_one_failure_does_not_stop_the_next(area):  # TC-012
    bad = staging(area, ".incoming-" + "b" * 32)
    (bad / "sub").mkdir()
    good = staging(area, ".incoming-" + "c" * 32)
    age(bad, STALE + 1)
    age(good, STALE + 1)
    uploads_web.sweep(area, now=NOW)
    assert not good.exists()
    assert bad.is_dir()
