# Nothing existing: compute_envs._VALUE_PATTERNS has no rule for a secret carried by a URL (userinfo, pre-signed query).
"""A URL that carries a secret counts as a credential (cloud-burn D9; audit-2026-11 03_web_cell_credential_gate.py).

The four inputs of the audit script are the first four cases. Login-shaped strings are built from pieces.
"""
import pytest

from abf_platform import compute_envs

HEX = "0123456789abcdef" * 3
PW = "hun" + "ter2"
AKIA = "AK" + "IA" + "IOSFODNN7EXAMPLE"

CARRIES_A_SECRET = [
    "https://h.org/a.fq.gz?token=abc123",                                                  # control: refused before this change too
    "https://user:" + PW + "@h.org/a.fq.gz",                                               # userinfo
    "https://b.s3.amazonaws.com/a.fq.gz?X-Amz-Credential=" + AKIA + "%2F20261101%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=" + HEX,
    "https://storage.googleapis.com/b/a.fq.gz?X-Goog-Signature=" + HEX,
    # shapes next to them
    "https://storage.googleapis.com/b/a.fq.gz?X-Goog-Algorithm=GOOG4-RSA-SHA256&x-goog-signature=" + HEX.upper(),
    "https://h.org/a.fq.gz?X-Amz-Signature=" + HEX,
    "http://u:" + PW + "@h.org:8080/a.fq.gz",
    "ftp://:" + PW + "@h.org/a.fq.gz",
    "https://user:p%40ss@h.org/a.fq.gz",
    "https://user:p@ss@h.org/a.fq.gz",
    "a sample sheet cell: https://user:" + PW + "@h.org/a.fq.gz, in the middle of text",
]

HARMLESS = [
    "https://h.org/a.fq.gz",
    "https://h.org:8080/a.fq.gz",
    "https://user@h.org/a.fq.gz",                                    # a name with no password
    "https://h.org/a@b.fq.gz",                                       # '@' in the path
    "https://h.org/dir:x@y/a.fq.gz",                                 # ':' and '@' in the path, not in userinfo
    "https://h.org/a.fq.gz?owner=me@lab.org",                        # '@' in the query
    "https://h.org/a.fq.gz?note=a:b@c",
    "https://h.org/a.fq.gz#frag:x@y",
    "https://h.org/a.fq.gz?X-Goog-Signature=",                       # the parameter name alone, no value
    "https://h.org/a.fq.gz?X-Goog-Signature=abc",                    # too short to be a signature
    "https://h.org/a.fq.gz?X-Goog-Algorithm=GOOG4-RSA-SHA256",
    "s3://bucket/key/a.fq.gz",
    "me@lab.org",
    "host:22",
    "/data/lab/a@b.fq.gz",
]


@pytest.mark.parametrize("cell", CARRIES_A_SECRET)
def test_url_with_a_secret_is_a_credential(cell):
    assert compute_envs.looks_like_credential(cell)


@pytest.mark.parametrize("cell", HARMLESS)
def test_plain_url_is_not_a_credential(cell):
    assert not compute_envs.looks_like_credential(cell)


@pytest.mark.parametrize("cell", CARRIES_A_SECRET[:4])
def test_audit_script_inputs_are_refused_by_the_samplesheet_check(cell):
    from abf_station import launch
    with pytest.raises(launch.BundleError):
        launch._check_samplesheet([["sample", "fastq_1"], ["s1", cell]], [], ["/work"])


@pytest.mark.parametrize("cell", HARMLESS[:8])
def test_plain_url_passes_the_samplesheet_check(cell):
    from abf_station import launch
    launch._check_samplesheet([["sample", "fastq_1"], ["s1", cell]], [], ["/work"])


def test_the_secret_is_not_in_the_refusal():
    from abf_platform import compute_envs as ce
    msg = ce.credential_findings({"description": "https://user:" + PW + "@h.org/a"}, "x")
    assert msg and PW not in repr(msg)
