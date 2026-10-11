# Nothing existing: unit tests of this folder's small shared functions (run id, times, secret names, error text); they encode Nextflow's formats.
"""Unit tests of abf_platform.common (feature 008)."""
import hashlib

from abf_platform import common
from helpers import load_scenario

LOG_BLOCK = """Error executing process > 'BAD'

Caused by:
  Process `BAD` terminated with an error exit status (1)


Command executed:

  echo "FIXTURE_BOOM_7" >&2
  exit 1

Command exit status:
  1

Command output:
  (empty)

Command error:
  FIXTURE_BOOM_7
  second line

Work dir:
  /LAUNCH/wk/99/f487fbbae150ee64f32bef71ecb84a

Tip: you can replicate the issue by changing to the process work dir and entering the command `bash .command.run`
"""


def test_run_id_is_the_first_16_hex_of_sha256_of_session_slash_name():
    assert common.run_id("abc", "name") == hashlib.sha256(b"abc/name").hexdigest()[:16]
    assert common.run_id("abc", "name") != common.run_id("abc", "other")


def test_extract_error_reads_the_command_error_section_from_the_log_text():
    assert common.extract_error(LOG_BLOCK) == ("BAD", "FIXTURE_BOOM_7\nsecond line")


def test_extract_error_gives_the_same_answer_for_the_recorded_error_report():
    report = [r for r in load_scenario("fail_run")["requests"] if r["path"].endswith("/complete")][0]
    report = report["body"]["workflow"]["errorReport"]
    assert common.extract_error(report) == ("BAD", "FIXTURE_BOOM_7")
    # a log line puts a time stamp in front of the first line only
    prefixed = "Oct-11 11:04:13.259 [TaskFinalizer-3] ERROR nextflow.processor.TaskProcessor - " + report
    assert common.extract_error(prefixed) == ("BAD", "FIXTURE_BOOM_7")
    assert common.extract_error("nothing to see here") is None


def test_secret_names_are_judged_by_name_only():
    for name in ("TOKEN", "my_password", "aws_secret_key", "ssh_key_path", "Password", "secretName"):
        assert common.is_secret_name(name)
    for name in ("outdir", "genome", "input", "max_cpus"):
        assert not common.is_secret_name(name)
    scrubbed = common.scrub_params({"a": {"password": "x", "b": [1, {"api_key": "y"}]}, "outdir": "o"})
    assert scrubbed == {"a": {"password": None, "b": [1, {"api_key": None}]}, "outdir": "o"}


def test_times_are_whole_seconds_and_nanosecond_strings_parse():
    t = common.parse_iso_epoch("2026-10-11T11:04:02.315527812+08:00")
    assert t == common.parse_iso_epoch("2026-10-11T11:04:02+08:00")
    assert common.epoch_iso(t) == "2026-10-11T03:04:02Z"
    assert common.parse_iso_epoch(None) is None
