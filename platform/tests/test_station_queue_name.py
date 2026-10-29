# Nothing existing: 既有測試 test_launch_bundle.py 只直接測換行結尾的佇列名；沒有任何測試覆蓋 `..`，兩道鎖是否拒收同一批名字也沒人比對。
"""The station's second lock refuses queue names with '..', like the platform's first lock."""
import pytest

from abf_platform import compute_envs
from abf_station import rules

BAD = ["a..b", "..", "x.."]
GOOD = ["ct224", "gp4", "a.b", "a_b-c.1"]
OTHER_BAD = ["", None, 123]


def platform_accepts(name):
    config = {"workDir": "/data/w1", "headQueue": name}
    try:
        compute_envs._check_slurm(config)
    except compute_envs.CEError:
        return False
    return True


def station_accepts(name):
    try:
        return rules.clean_queue(name, "headQueue") == name
    except rules.Refusal:
        return False


@pytest.mark.parametrize("name", BAD)
def test_dotdot_refused(name):
    # TC-001, TC-002, TC-003
    with pytest.raises(rules.Refusal):
        rules.clean_queue(name, "headQueue")


def _message(name):
    with pytest.raises(rules.Refusal) as e:
        rules.clean_queue(name, "headQueue")
    return str(e.value)


def test_same_message_as_before():
    # TC-004
    expected = "headQueue is not a valid queue name (letters, digits, _ . - only)"
    assert _message("a..b") == expected
    assert _message("normal\n") == expected


def test_message_is_plain():
    # TC-005
    msg = _message("a..b")
    assert "headQueue" in msg and "letters, digits, _ . - only" in msg
    assert "Traceback" not in msg and "/" not in msg
    assert "token" not in msg.lower() and "secret" not in msg.lower()


@pytest.mark.parametrize("name", GOOD)
def test_good_names_unchanged(name):
    # TC-006, TC-007, TC-008, TC-009
    assert rules.clean_queue(name, "headQueue") == name


def test_empty_refused():
    # TC-010
    with pytest.raises(rules.Refusal):
        rules.clean_queue("", "headQueue")


@pytest.mark.parametrize("name", [None, 123])
def test_non_string_refused(name):
    # TC-011
    with pytest.raises(rules.Refusal):
        rules.clean_queue(name, "headQueue")


@pytest.mark.parametrize("name", BAD)
def test_both_locks_refuse_dotdot(name):
    # TC-013
    assert not platform_accepts(name)
    assert not station_accepts(name)


@pytest.mark.parametrize("name", GOOD)
def test_both_locks_accept_good(name):
    # TC-014
    assert platform_accepts(name)
    assert station_accepts(name)


@pytest.mark.parametrize("name", OTHER_BAD)
def test_both_locks_refuse_empty_and_non_string(name):
    # TC-015
    assert not platform_accepts(name)
    assert not station_accepts(name)
