# Nothing existing: flake8/ruff have no rule for "$ matches before a trailing newline in a validator"; tests/regex_end_anchor_test.sh only scans the source, these pin the behaviour.
"""cb-D3: a name that ends in a newline is not a plain extension (validate._PLAIN) and not a bucket name (cloud_store._BUCKET).
Python's `$` also matches just before a trailing "\\n"; both patterns end with \\Z instead."""
import re
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "abf_platform"


def validate_mod():
    from abf_platform import validate
    return validate


def cs():
    from abf_platform import cloud_store
    return cloud_store


@pytest.mark.parametrize("text", ["txt\n", "a.b\n", "A_b-c\n"])
def test_plain_rejects_trailing_newline(text):
    assert not validate_mod()._PLAIN.match(text)


@pytest.mark.parametrize("pattern", ["*.txt\n", "*.{gz,txt\n}", "*.fa\n"])
def test_extensions_reject_trailing_newline(pattern):
    assert validate_mod()._extensions(pattern) is None


@pytest.mark.parametrize("text", ["txt", "a.b", "A_b-c", "x", "tar.gz"])
def test_plain_still_accepts_plain_names(text):
    assert validate_mod()._PLAIN.match(text)


def test_extensions_still_read_plain_patterns():
    v = validate_mod()
    assert v._extensions("*.txt") == {"txt"}
    assert v._extensions("*.fa{sta,sa}") == {"fasta", "fasa"}


@pytest.mark.parametrize("name", ["abc\n", "a-b\n", "my-bucket\n", "a" * 62 + "\n", "a" * 63 + "\n"])
def test_bucket_rejects_trailing_newline(name):
    assert not cs()._BUCKET.match(name)
    assert not cs()._container_ok("gs", name)


@pytest.mark.parametrize("name", ["abc", "a.b-c_d", "a" * 63, "my-bucket"])
def test_bucket_still_accepts_valid_names(name):
    assert cs()._BUCKET.match(name)
    assert cs()._container_ok("gs", name)


@pytest.mark.parametrize("name", ["ab", "a" * 64, "-abc", "abc-", "ABC", "ab c", "a/b", "abc\n\n", "a\nbc"])
def test_bucket_still_rejects_what_base_rejected(name):
    assert not cs()._BUCKET.match(name)


def test_parse_gs_still_rejects_newline_locations():
    for url in ("gs://abc\n/x", "gs://abc/x\n"):
        with pytest.raises(cs().CloudPathError):
            cs().parse_gs(url)
    assert cs().parse_gs("gs://abc/x") == ("abc", "x")


@pytest.mark.parametrize("fname,var", [("validate.py", "_PLAIN"), ("cloud_store.py", "_BUCKET")])
def test_source_literal_ends_with_end_of_string_anchor(fname, var):
    src = (PKG / fname).read_text(encoding="utf-8")
    m = re.search(r"^%s = re\.compile\(r\"(.*)\"\)$" % var, src, re.M)
    assert m, var
    assert m.group(1).endswith("\\Z")
    assert not m.group(1).endswith("$")
