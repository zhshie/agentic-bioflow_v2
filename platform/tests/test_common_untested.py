# Nothing existing: table tests for three small functions of abf_platform.common that no other test calls directly.
"""Table tests: token_from_header, offline_after_seconds, run_failure_reason (cloud-burn T1)."""
import base64

import pytest

from abf_platform import common


def _basic(text):
    return "Basic " + base64.b64encode(text.encode("utf-8")).decode("ascii")


@pytest.mark.parametrize("header, expected", [
    # nothing usable
    (None, None),
    ("", None),
    ("   ", None),
    # Bearer: the scheme is case-insensitive, the token is kept as sent
    ("Bearer abc", "abc"),
    ("bearer abc", "abc"),
    ("BEARER abc", "abc"),
    ("BeArEr abc", "abc"),
    # Bearer without a credential
    ("Bearer", None),
    ("Bearer ", None),
    ("Bearer    ", None),
    # extra spaces: around the whole value, between scheme and token, around the token
    ("  Bearer abc  ", "abc"),
    ("Bearer   abc", "abc"),
    ("Bearer abc   ", "abc"),
    # only the first space separates scheme from credential; the rest belongs to the credential
    ("Bearer a b", "a b"),
    # other schemes and bare words
    ("Token abc", None),
    ("Digest abc", None),
    ("abc", None),
    ("Bearerabc", None),
    ("Bearer-abc def", None),
    # Basic base64("@token:<token>"), as Nextflow sends it
    (_basic("@token:xyz"), "xyz"),
    (_basic("@token:xyz").replace("Basic", "basic"), "xyz"),
    (_basic("@token:xyz").replace("Basic", "BASIC"), "xyz"),
    (_basic("@token:a:b"), "a:b"),
    ("  " + _basic("@token:xyz") + "  ", "xyz"),
    (_basic("@token:xyz").replace("Basic ", "Basic   "), "xyz"),
    # Basic that is not the Nextflow form
    (_basic("someone:xyz"), None),
    (_basic(":xyz"), None),
    (_basic("@token:"), None),
    (_basic("@token"), None),
    (_basic(""), None),
    ("Basic", None),
    ("Basic ", None),
    ("Basic !!!not-base64!!!", None),
    ("Basic " + base64.b64encode(b"\xff\xfe:\xff").decode("ascii"), None),
])
def test_token_from_header_table(header, expected):
    assert common.token_from_header(header) == expected


ENV = "ABF_AGENT_HEARTBEAT_SECONDS"


@pytest.mark.parametrize("value, expected", [
    # unset is covered separately; these are values of the variable
    ("", 60.0),            # empty string means the default
    ("abc", 60.0),         # non-numeric
    ("12abc", 60.0),
    ("1,5", 60.0),
    ("-5", 60.0),          # negative
    ("-0.1", 60.0),
    ("0", 60.0),           # zero is not a heartbeat
    ("0.0", 60.0),
    ("nan", 60.0),         # nan is not > 0
    ("10", 30.0),          # three beats of 10 seconds
    ("1", 3.0),
    ("1.5", 4.5),
    (" 10 ", 30.0),        # float() accepts padding
    ("20", 60.0),
])
def test_offline_after_seconds_reads_the_env_value_or_falls_back(monkeypatch, value, expected):
    monkeypatch.setenv(ENV, value)
    assert common.offline_after_seconds() == pytest.approx(expected)


def test_offline_after_seconds_unset_is_three_default_beats(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    assert common.offline_after_seconds() == 3 * common.AGENT_HEARTBEAT_SECONDS == 60


def test_offline_after_seconds_is_always_positive(monkeypatch):
    for value in ("", "x", "-1", "0", "nan", "3"):
        monkeypatch.setenv(ENV, value)
        assert common.offline_after_seconds() > 0


@pytest.mark.parametrize("message, report, expected", [
    # nothing
    (None, None, None),
    ("", "", None),
    ("   ", "\n \n\t\n", None),
    # the message wins over the report
    ("boom", "other", "boom"),
    ("  boom  ", "other", "boom"),
    # a blank or missing message falls back to the report's first non-empty line
    ("", "other", "other"),
    (None, "other", "other"),
    ("   ", "other", "other"),
    (None, "\n\n  second \nthird", "second"),
    (None, "first\nsecond", "first"),
    # the message is one text, not split into lines: newlines become a space
    ("line1\nline2", "other", "line1 line2"),
    ("line1\r\n\r\nline2", None, "line1 line2"),
    # control characters: each run becomes one space, then the ends are stripped
    ("a\x1b\x00\x7fb", None, "a b"),
    ("a\tb", None, "a b"),
    ("\x1bred\x00", None, "red"),
    ("a\x85b", None, "a b"),          # C1 control
    ("\x00\x01\x02", "fallback", "fallback"),  # a message of only control characters is empty
    (None, "\x1b\n\x00\nreal", "real"),
    # non-str input is ignored, never coerced
    (123, "other", "other"),
    (b"bytes", None, None),
    (["list"], None, None),
    ("boom", 123, "boom"),
    (None, 123, None),
    # printable non-ASCII is kept
    ("失敗 é", None, "失敗 é"),
])
def test_run_failure_reason_table(message, report, expected):
    assert common.run_failure_reason(message, report) == expected


def test_run_failure_reason_cuts_at_the_limit():
    assert common.REASON_MAX_CHARS == 1000
    assert common.run_failure_reason("x" * 1500, None) == "x" * 1000
    assert common.run_failure_reason(None, "y" * 1500) == "y" * 1000
    exact = "z" * 1000
    assert common.run_failure_reason(exact, None) == exact
    assert len(common.run_failure_reason("w" * 1001, None)) == 1000


def test_run_failure_reason_cuts_after_cleaning_not_before():
    # leading control characters and spaces do not use up the budget
    assert common.run_failure_reason("\x1b\x1b  " + "x" * 1500, None) == "x" * 1000
