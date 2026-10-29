# Nothing existing: the rule list lives in compute_envs._VALUE_PATTERNS; this file only tests one more pattern on it.
"""A kubeconfig secret line pasted into a text field is refused and never repeated (k8s-kubeconfig-paste-rule).

The TC ids refer to specs/k8s-kubeconfig-paste-rule/test-case.md. Login-shaped strings are built from pieces.
"""
import logging

import pytest

from station_harness import Inproc

CTX = "lab-context"
MARK = "MARKER" + "KUBEDATA" + "Q" * 40
KEYS = ["client-certificate-data", "client-key-data", "certificate-authority-data"]


@pytest.fixture
def ip(tmp_path, monkeypatch):
    monkeypatch.delenv("ABF_STATION_KUBECONFIG", raising=False)
    box = Inproc(tmp_path, monkeypatch)
    box.tmp = tmp_path
    box.settings = tmp_path / "deploy" / "config" / "env.yaml"
    box.settings.parent.mkdir(parents=True)
    box.settings.write_text("reach: local\n")
    return box


def good_config(**extra):
    c = {"context": CTX, "namespace": "lab-ns", "storageClaimName": "lab-pvc", "workDir": "/workspace/work"}
    c.update(extra)
    return c


def fields(name="k1", config=None, **top):
    f = {"name": name, "platform": "k8s-platform", "agent": "a1", "config": good_config() if config is None else config}
    f.update(top)
    return f


def create(ip, name="k1", config=None, **top):
    from abf_platform import compute_envs
    return compute_envs.create(ip.state_db, fields(name, config, **top))


def refused(ip, config=None, **top):
    from abf_platform import compute_envs
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.create(ip.state_db, fields("bad", config, **top))
    return str(e.value)


def block(key):
    return "clusters:\n- cluster:\n    " + key + ": " + MARK + "\n"


@pytest.mark.parametrize("key", KEYS)
def test_description_refused(ip, key):
    # TC-001, TC-002, TC-003
    msg = refused(ip, description=block(key))
    assert "description" in msg and MARK not in msg


@pytest.mark.parametrize("key", KEYS)
def test_nextflow_config_refused(ip, key):
    # TC-004
    msg = refused(ip, good_config(nextflowConfig=block(key)))
    assert "nextflowConfig" in msg and MARK not in msg


@pytest.mark.parametrize("key", KEYS)
def test_environment_value_refused(ip, key):
    # TC-005
    msg = refused(ip, good_config(environment=[{"name": "SOMEVAR", "value": block(key)}]))
    assert "environment[0].value" in msg and MARK not in msg


@pytest.mark.parametrize("text", [
    "    Client-Key-Data: " + MARK,                                  # TC-006
    "client-key-data : " + MARK,                                     # TC-007
    "my cluster settings, client-key-data: " + MARK,                 # TC-008
    "client-key-data:\n  " + MARK,                                   # TC-009
])
def test_variants_refused(ip, text):
    # TC-006, TC-007, TC-008, TC-009
    msg = refused(ip, description=text)
    assert "description" in msg and MARK not in msg


def test_message_is_the_existing_advice(ip):
    # TC-010
    from abf_platform import compute_envs
    msg = refused(ip, description=block("client-key-data"))
    assert msg == "description " + compute_envs.CREDENTIAL_ADVICE


def test_nothing_stored(ip):
    # TC-011, TC-012
    before = ip.rows()
    for key in KEYS:
        refused(ip, description=block(key))
    assert ip.rows() == before
    if ip.state_db.exists():
        assert MARK.encode() not in ip.state_db.read_bytes()


def test_no_log_or_output_leak(ip, caplog, capsys):
    # TC-013
    with caplog.at_level(logging.DEBUG):
        msg = refused(ip, description=block("client-key-data"))
    out = capsys.readouterr()
    assert MARK not in msg and MARK not in caplog.text and MARK not in out.out and MARK not in out.err


@pytest.mark.parametrize("key", KEYS)
def test_looks_like_credential(key):
    # TC-014
    from abf_platform import compute_envs
    assert compute_envs.looks_like_credential(key + ":")


def test_update_refused_and_old_record_kept(ip):
    # TC-015
    from abf_platform import compute_envs
    create(ip, "k1", description="first")
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.update(ip.state_db, "k1", {"description": "x\nclient-key-data: " + MARK})
    assert "description" in str(e.value) and MARK not in str(e.value)
    assert ip.show("k1")["description"] == "first"
    assert MARK.encode() not in ip.state_db.read_bytes()


@pytest.mark.parametrize("text", [
    "a context for the lab, token-free",                                      # TC-016
    "the certificate is kept on the agent",                                   # TC-017
    "certificate-authority-data lives in the kubeconfig on the agent",        # TC-018
    "client-key-data",                                                        # TC-019
    "my client certificate, signed by the lab CA",                            # TC-020
    "data: certificate",                                                      # TC-021
    "QUJD" * 50,                                                              # TC-027
])
def test_ordinary_text_still_creates(ip, text):
    # TC-016 .. TC-021, TC-027
    assert create(ip, description=text)["status"] == "creating"


def test_token_line_still_refused(ip):
    # TC-022
    msg = refused(ip, description="to" + "ken: " + MARK)
    assert MARK not in msg
