# Nothing existing: tests that a model key pasted into a compute environment field is refused by name; the shapes of keys are the providers' and the refusal is ours.
"""014a: model-key shapes in abf_platform.compute_envs. Test cases are named in the comments (TC-010 ...), see specs/014a-chat-backend/test-case.md."""
import json
import re

import pytest

from station_harness import Inproc

CRED = re.compile(r"credential|憑證")
AGENT_SIDE = re.compile(r"agent|代理")
TAIL = "AbC123_-xYz789" * 3        # 42 characters of the alphabet a key uses; made here, not a real key
KEYS = {
    "anthropic": "sk-ant-api03-" + TAIL[:40],
    "openai-project": "sk-proj-" + TAIL[:40],
    "openai": "sk-" + TAIL[:40],
}


@pytest.fixture
def ip(tmp_path, monkeypatch):
    return Inproc(tmp_path, monkeypatch)


@pytest.mark.parametrize("label", sorted(KEYS))
def test_tc010_model_key_shapes_are_credentials(label):
    # TC-010
    from abf_platform import compute_envs
    assert compute_envs.looks_like_credential(KEYS[label])


@pytest.mark.parametrize("text", ["disk-usage", "task-runner-42", "ask-me", "sk-" + "a" * 19])
def test_tc011_ordinary_text_is_not_a_credential(text):
    # TC-011
    from abf_platform import compute_envs
    assert not compute_envs.looks_like_credential(text)


@pytest.mark.parametrize("label", sorted(KEYS))
def test_tc013_the_finding_names_the_field_and_never_holds_the_value(label):
    # TC-013
    from abf_platform import compute_envs
    cfg = {"workDir": "/data/work", "nextflowConfig": "process.ext.x = '%s'" % KEYS[label],
           "environment": [{"name": "SOMEVAR", "value": KEYS[label]}]}
    found = compute_envs.credential_findings(cfg, "config")
    assert "config.nextflowConfig" in found and "config.environment[0]" in found, found
    assert KEYS[label] not in json.dumps(found)


@pytest.mark.parametrize("label", sorted(KEYS))
@pytest.mark.parametrize("field,flags", [
    ("nextflowConfig", lambda k: {"nextflow_config": "process.ext.x = '%s'" % k}),
    ("environment", lambda k: {"env": ["SOMEVAR=" + k]}),
])
def test_tc012_tc017_tc042_a_model_key_in_a_field_is_refused_by_name_and_never_stored(ip, label, field, flags):
    # TC-012 (nextflowConfig), TC-017 (environment), TC-042 (nothing stored, nothing echoed)
    key = KEYS[label]
    before = ip.rows()
    rc, out = ip.create_slurm("lab-x", **flags(key))
    assert rc != 0, out
    assert field in out, out
    assert CRED.search(out) and AGENT_SIDE.search(out), out
    assert key not in out and TAIL[:30] not in out
    assert key.encode() not in ip.all_bytes() and TAIL[:30].encode() not in ip.all_bytes()
    assert ip.rows() == before


def test_tc015_the_six_existing_patterns_are_unchanged_and_the_new_ones_come_after():
    # TC-015
    from abf_platform import compute_envs
    old = [
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----",
        r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
        r"aws_secret_access_key\s*[=:]",
        r"abf_[A-Za-z0-9_-]{20,}",
        r"\bexport\s+[A-Za-z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|KEY)[A-Za-z0-9_]*\s*=",
        r"\b(?:password|passwd|secret|api[_-]?key|access[_-]?key|secret[_-]?key|token)\w*\s*[=:]\s*\S",
    ]
    got = [p.pattern for p in compute_envs._VALUE_PATTERNS]
    assert got[:6] == old
    assert got[6:] == [r"\bsk-ant-[A-Za-z0-9_-]{20,}", r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"]
