# Nothing existing: tests for the words the station prints when the platform answers 403 (owner-binding added a second reason); the rules are ours.
"""station-403-owner-message: the station tells a name mismatch from an owner mismatch by what the platform said.
Test cases are named in the comments (TC-001 ...)."""
import pytest
from starlette.testclient import TestClient

from human_harness import World
from abf_station import agent

OWNER_MSG = "This agent belongs to another user"
BASE_401 = ("the platform rejected the token (401): it is wrong or it was revoked. "
            "Ask for a new one with `abf-platform agent-token new <name>`.")


@pytest.fixture
def w(tmp_path, monkeypatch):
    monkeypatch.setenv("ABF_AGENT_POLL_SECONDS", "0")
    return World(tmp_path, monkeypatch)


def _real_403s(w):
    """(owner mismatch body, name mismatch body), asked of the real platform."""
    from abf_platform import receiver, store
    a, b = w.user("alice"), w.user("bob")
    client = TestClient(receiver.create_app(w.ip.index, w.ip.tokens))

    def hello(token, name):
        return client.post("/agent/hello", json={"name": name, "version": "0.1.0"},
                           headers={"Authorization": "Bearer " + token})
    ta = store.create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=a.user_id)
    tb = store.create_token(w.ip.tokens, kind="agent", agent_name="ag", user_id=b.user_id)
    assert hello(ta, "ag").status_code == 200
    owner = hello(tb, "ag")                     # bob's token, the name alice owns
    name = hello(ta, "other-name")              # alice's token, a different name
    assert owner.status_code == 403 and name.status_code == 403
    return owner.json(), name.json()


@pytest.fixture
def real(w):
    return _real_403s(w)


def owner_text():
    return agent._rejected(403, {"message": OWNER_MSG})


def name_text():
    return agent._rejected(403, {"message": "This token was made for another agent name"})


def unsure_text():
    return agent._rejected(403, {})


# ---- US1 ----
def test_owner_mismatch_real_platform(real):
    body = real[0]
    t = agent._rejected(403, body)
    assert "另一位使用者" in t                                   # TC-001
    assert "another agent name" not in t and "另一個代理名稱" not in t   # TC-002
    assert "403" in t and "--user" in t                           # TC-003
    assert "belongs to another user" in body["message"].lower()   # TC-004
    assert body["message"] not in t                               # TC-026


# ---- US2 ----
def test_name_mismatch_real_platform(real):
    body = real[1]
    t = agent._rejected(403, body)
    assert "--name" in t and "另一個代理名稱" in t                # TC-005
    assert "已經屬於另一位使用者" not in t                        # TC-006
    assert "403" in t                                             # TC-007
    assert "another agent name" in body["message"].lower()        # TC-008
    assert body["message"] not in t                               # TC-026


# ---- US3 ----
@pytest.mark.parametrize("body", [{}, {"message": "something new"}, {"message": 7}, None])
def test_unknown_403_covers_both_causes(body):
    # TC-009, TC-010, TC-011, TC-012
    t = agent._rejected(403, body)
    assert "--name" in t and "另一位使用者" in t
    assert "403" in t                                             # TC-013


def test_three_texts_differ():
    # TC-014
    assert len({owner_text(), name_text(), unsure_text()}) == 3


def test_case_insensitive():
    # TC-015
    assert agent._rejected(403, {"message": "THIS AGENT BELONGS TO ANOTHER USER"}) == owner_text()
    assert agent._rejected(403, {"message": "THIS TOKEN WAS MADE FOR ANOTHER AGENT NAME"}) == name_text()


def test_owner_checked_first():
    # TC-016
    t = agent._rejected(403, {"message": "belongs to another user ... another agent name"})
    assert t == owner_text() and "另一個代理名稱" not in t


# ---- US4 ----
def FakeClientPost(replies):
    replies = list(replies)

    def post(client, path, body, timeout):
        return replies.pop(0) if len(replies) > 1 else replies[0]
    return post


def _agent(monkeypatch, replies, token="tok"):
    monkeypatch.setattr(agent.Client, "post", FakeClientPost(replies))
    monkeypatch.setattr(agent.launch, "own_facts", lambda ctx: {})
    monkeypatch.setattr(agent.common, "heartbeat_seconds", lambda: 1)
    monkeypatch.setattr(agent.common, "poll_seconds", lambda: 0)
    return agent.Agent("http://127.0.0.1:1", token, "ag", agent.Context(None, "s.json"))


OWNER_REPLY = (403, {"message": OWNER_MSG})


def test_hello_passes_body(monkeypatch):
    # TC-017
    a = _agent(monkeypatch, [OWNER_REPLY])
    with pytest.raises(agent.Rejected) as e:
        a.hello()
    assert str(e.value) == owner_text()


def test_answer_passes_body(monkeypatch):
    # TC-018
    a = _agent(monkeypatch, [OWNER_REPLY])
    with pytest.raises(agent.Rejected) as e:
        a.answer(1, "done", {})
    assert str(e.value) == owner_text()


def test_loop_passes_body(monkeypatch):
    # TC-019
    a = _agent(monkeypatch, [(200, {"agent": "ag"}), OWNER_REPLY])
    with pytest.raises(agent.Rejected) as e:
        a.loop()
    assert str(e.value) == owner_text()


def test_run_prints_and_exits(monkeypatch, capsys, tmp_path):
    # TC-020, TC-038
    monkeypatch.setattr(agent.Client, "post", FakeClientPost([(403, {"message": OWNER_MSG + " abf_SECRET"})]))
    monkeypatch.setattr(agent.launch, "own_facts", lambda ctx: {})
    monkeypatch.setattr(agent, "Site", lambda *a, **k: None)
    rc = agent.run("http://127.0.0.1:1", "abf_MYTOKEN", "ag", tmp_path, tmp_path / "s.json")
    out = capsys.readouterr()
    assert rc == agent.EXIT_REJECTED
    assert out.out.strip() == "abf-station stopped: " + owner_text()
    for stream in (out.out, out.err):
        assert "abf_SECRET" not in stream and "abf_MYTOKEN" not in stream


def test_no_retry_on_403(monkeypatch):
    # TC-021
    a = _agent(monkeypatch, [OWNER_REPLY])
    called = []
    monkeypatch.setattr(a, "wait_or_retry", lambda why: called.append(why))
    with pytest.raises(agent.Rejected):
        a.hello()
    assert not called and a.failures == 0


# ---- US5 ----
def test_401_unchanged():
    # TC-022, TC-023
    assert agent._rejected(401) == BASE_401
    assert agent._rejected(401, {"message": "x"}) == BASE_401


@pytest.mark.parametrize("message,expected", [("alice abf_SECRET", unsure_text),
                                              (OWNER_MSG + ": alice abf_SECRET", owner_text)])
def test_no_leak(message, expected):
    # TC-024, TC-025, TC-026
    t = agent._rejected(403, {"message": message})
    assert "abf_SECRET" not in t and "alice" not in t and message not in t
    assert t == expected()


# ---- constitution ----
def test_every_text_has_status_reason_next_step_and_no_internals():
    # TC-036, TC-037
    for t, step in ((owner_text(), "--user"), (name_text(), "--name"), (unsure_text(), "--name")):
        assert "403" in t and step in t
        for bad in ("Traceback", ".py", "SELECT", "/home", "C:\\"):
            assert bad not in t
