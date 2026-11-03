# Nothing existing: tests of `agent-token list` and `agent-token revoke --id N` (revoke one agent token by id); the rules are ours.
"""Revoke one agent token by id, and list the ids. Test cases are named in the comments (TC-001 ...)."""
import ast
import hashlib
import re
import sqlite3
import subprocess
import sys

import pytest

from helpers import PLATFORM_DIR, Clock, Platform, pkg_env, run_cli

PKG = PLATFORM_DIR / "abf_platform"
REPO = PLATFORM_DIR.parent
REVOKE_NAME_LINE = "revoked 3 token(s) of agent ag; the agent is refused from its next request"
REJECT_ID = "rejected: no live agent token with id %s"
EITHER = "rejected: give either an agent name or --id N, not both and not neither"


def _store():
    from abf_platform import store
    return store


class Env:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.tokens = tmp_path / "data" / "tokens.db"
        self.env = pkg_env(ABF_PLATFORM_DB=tmp_path / "data" / "index.db")
        self.secrets = []

    def agent(self, name="ag", user=None):
        st = _store()
        uid = None
        if user:
            uid = st.user_id_of(self.tokens, user) or st.create_user(self.tokens, user, "lab-x")
        t = st.create_token(self.tokens, kind="agent", agent_name=name, user_id=uid)
        self.secrets.append(t)
        return t

    def run_token(self):
        t = _store().create_token(self.tokens, kind="run")
        self.secrets.append(t)
        return t

    def pat(self, user="alice"):
        st = _store()
        uid = st.user_id_of(self.tokens, user) or st.create_user(self.tokens, user, "lab-x")
        t = st.create_token(self.tokens, kind="pat", user_id=uid)
        self.secrets.append(t)
        return t

    def cli(self, *args):
        return run_cli(list(args), env=self.env)

    def table(self):
        con = sqlite3.connect(str(self.tokens))
        try:
            return con.execute("SELECT * FROM tokens ORDER BY id").fetchall()
        finally:
            con.close()

    def revoked_at(self, i):
        con = sqlite3.connect(str(self.tokens))
        try:
            return con.execute("SELECT revoked_at FROM tokens WHERE id = ?", (i,)).fetchone()[0]
        finally:
            con.close()

    def id_of(self, token):
        con = sqlite3.connect(str(self.tokens))
        try:
            return con.execute("SELECT id FROM tokens WHERE token_hash = ?",
                               (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()[0]
        finally:
            con.close()

    def no_secrets(self, *outs):
        text = "\n".join(outs)
        for s in self.secrets:
            assert s not in text
            assert hashlib.sha256(s.encode()).hexdigest() not in text


@pytest.fixture
def e(tmp_path):
    (tmp_path / "data").mkdir()
    return Env(tmp_path)


@pytest.fixture
def two(e):
    """`ag` twice: id 1 the old one (no user), id 2 the new one (user alice)."""
    old = e.agent("ag")
    new = e.agent("ag", user="alice")
    return e, old, new


def _lines(r):
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


# ---- US1 -----------------------------------------------------------------------------------------------------------

def test_revoke_by_id_revokes_only_that_one_and_the_other_keeps_working(two):
    # TC-001 TC-002 TC-003 TC-004
    e, old, new = two
    r = e.cli("agent-token", "revoke", "--id", "1")
    assert r.returncode == 0
    assert e.revoked_at(1) is not None
    assert e.revoked_at(2) is None
    st = _store()
    assert st.lookup_token(e.tokens, old) is None
    assert st.lookup_token(e.tokens, new)["agent_name"] == "ag"


def test_receiver_refuses_the_revoked_one_and_accepts_the_other(two):
    # TC-005 TC-006
    e, old, new = two
    assert e.cli("agent-token", "revoke", "--id", "1").returncode == 0
    p = Platform(e.tmp / "data", clock=Clock())
    body = {"name": "ag", "version": "0.1.0"}
    assert p.client.post("/agent/hello", json=body, headers={"Authorization": "Bearer " + old}).status_code == 401
    assert p.client.post("/agent/hello", json=body, headers={"Authorization": "Bearer " + new}).status_code == 200


def test_revoke_by_id_touches_only_the_middle_of_three(e):
    # TC-007
    toks = [e.agent("ag") for _ in range(3)]
    assert e.cli("agent-token", "revoke", "--id", "2").returncode == 0
    st = _store()
    assert st.lookup_token(e.tokens, toks[0]) and st.lookup_token(e.tokens, toks[2])
    assert st.lookup_token(e.tokens, toks[1]) is None
    assert e.revoked_at(1) is None and e.revoked_at(3) is None


def test_revoke_by_id_prints_what_happened_and_never_the_secret(two):
    # TC-008
    e, _, _ = two
    r = e.cli("agent-token", "revoke", "--id", "1")
    assert "revoked agent token 1" in r.stdout
    assert "agent ag" in r.stdout
    assert "other tokens of this agent are untouched" in r.stdout
    e.no_secrets(r.stdout, r.stderr)


def test_find_the_old_token_in_the_list_then_revoke_it(two):
    # TC-009
    e, old, new = two
    lines = [ln for ln in e.cli("agent-token", "list").stdout.splitlines() if "user -" in ln]
    assert len(lines) == 1
    n = re.search(r"id (\d+)", lines[0]).group(1)
    assert n == "1"
    assert e.cli("agent-token", "revoke", "--id", n).returncode == 0
    st = _store()
    assert st.lookup_token(e.tokens, old) is None
    assert st.lookup_token(e.tokens, new) is not None


def test_store_revoke_agent_token_returns_the_name(two):
    # TC-010
    e, old, _ = two
    st = _store()
    assert st.revoke_agent_token(e.tokens, 1) == {"agent_name": "ag"}
    assert st.lookup_token(e.tokens, old) is None


# ---- US2 -----------------------------------------------------------------------------------------------------------

def test_list_shows_id_agent_user_state_and_created(two):
    # TC-011 TC-012 TC-013 TC-015 TC-022
    e, _, _ = two
    assert e.cli("agent-token", "revoke", "--id", "1").returncode == 0
    r = e.cli("agent-token", "list")
    assert r.returncode == 0
    ls = _lines(r)
    assert len(ls) == 2
    assert "id 1" in ls[0] and "agent ag" in ls[0] and "user -" in ls[0] and ls[0].endswith("  revoked")
    assert "id 2" in ls[1] and "agent ag" in ls[1] and "user alice" in ls[1] and ls[1].endswith("not revoked")
    for ln in ls:
        assert re.search(r"created \d{4}-\d{2}-\d{2} \d{2}:\d{2}", ln)
    e.no_secrets(r.stdout, r.stderr)


def test_list_is_ordered_by_id(e):
    # TC-014
    for _ in range(4):
        e.agent("ag")
    ids = [int(re.search(r"id (\d+)", ln).group(1)) for ln in _lines(e.cli("agent-token", "list"))]
    assert ids == [1, 2, 3, 4]


def test_list_filters_by_name_and_never_shows_run_or_pat(e):
    # TC-016 TC-017 TC-018
    e.agent("ag")
    e.agent("ag")
    e.agent("other")
    run = e.id_of(e.run_token())
    pat = e.id_of(e.pat())
    r = e.cli("agent-token", "list", "ag")
    assert [ln for ln in _lines(r) if "agent other" in ln] == []
    assert len(_lines(r)) == 2
    r2 = e.cli("agent-token", "list")
    assert any("agent other" in ln for ln in _lines(r2)) and len(_lines(r2)) == 3
    for out in (r.stdout, r2.stdout):
        for i in (run, pat):
            assert "id %d " % i not in out


def test_list_with_nothing_says_so(e):
    # TC-019 TC-020 TC-021
    _store().create_user(e.tokens, "alice", "lab-x")     # a tokens.db that exists but holds no agent token
    r = e.cli("agent-token", "list")
    assert r.returncode == 0 and "no agent tokens" in r.stdout
    e.tokens.unlink()
    r = e.cli("agent-token", "list")
    assert r.returncode == 0 and "no agent tokens" in r.stdout
    assert r.stderr.strip() == ""
    e.agent("ag")
    r = e.cli("agent-token", "list", "nobody")
    assert r.returncode == 0 and "no agent tokens for nobody" in r.stdout


def test_store_list_agent_tokens(e):
    # TC-023
    e.agent("ag")
    e.agent("ag", user="alice")
    e.run_token()
    e.pat()
    rows = _store().list_agent_tokens(e.tokens)
    assert len(rows) == 2
    for r in rows:
        assert sorted(r) == ["agent_name", "created_at", "id", "revoked_at", "user"]
    assert rows[0]["user"] is None and rows[1]["user"] == "alice"
    assert _store().list_agent_tokens(e.tmp / "nope" / "tokens.db") == []


# ---- US3 -----------------------------------------------------------------------------------------------------------

def test_revoke_by_name_is_unchanged(e):
    # TC-030 TC-031 TC-032
    ags = [e.agent("ag") for _ in range(3)]
    other = e.agent("other")
    r = e.cli("agent-token", "revoke", "ag")
    assert r.returncode == 0 and r.stdout.strip() == REVOKE_NAME_LINE
    st = _store()
    assert all(st.lookup_token(e.tokens, t) is None for t in ags)
    assert st.lookup_token(e.tokens, other) is not None
    r = e.cli("agent-token", "revoke", "nobody")
    assert r.returncode == 1
    assert r.stdout.strip() == "revoked 0 token(s) of agent nobody; the agent is refused from its next request"


# ---- US4 -----------------------------------------------------------------------------------------------------------

def test_unknown_id_is_rejected_with_next_step_and_changes_nothing(two):
    # TC-040 TC-041 TC-042
    e, _, _ = two
    before = e.table()
    r = e.cli("agent-token", "revoke", "--id", "999")
    assert r.returncode == 1
    assert REJECT_ID % 999 in r.stderr and "沒有這個有效的代理 token" in r.stderr and "agent-token list" in r.stderr
    for out in (r.stdout, r.stderr):
        assert "Traceback" not in out and "SELECT" not in out and "UPDATE" not in out and ".db" not in out
    assert e.table() == before


def test_run_token_and_pat_ids_are_rejected_and_stay_live(e):
    # TC-043 TC-044 TC-045 TC-046
    run = e.run_token()
    pat = e.pat()
    before = e.table()
    r = e.cli("agent-token", "revoke", "--id", str(e.id_of(run)))
    assert r.returncode == 1 and (REJECT_ID % e.id_of(run)) in r.stderr
    r = e.cli("agent-token", "revoke", "--id", str(e.id_of(pat)))
    assert r.returncode == 1 and (REJECT_ID % e.id_of(pat)) in r.stderr
    assert "personal access" not in r.stderr
    st = _store()
    assert st.lookup_token(e.tokens, run) is not None
    assert st.lookup_pat(e.tokens, pat) is not None
    assert e.table() == before


def test_an_already_revoked_id_is_rejected_and_not_rewritten(two):
    # TC-047 TC-048
    e, _, _ = two
    assert e.cli("agent-token", "revoke", "--id", "1").returncode == 0
    first = e.revoked_at(1)
    r = e.cli("agent-token", "revoke", "--id", "1")
    assert r.returncode == 1 and (REJECT_ID % 1) in r.stderr
    assert e.revoked_at(1) == first


def test_exactly_one_of_name_or_id(two):
    # TC-049 TC-050 TC-051 TC-052 TC-053
    e, _, _ = two
    before = e.table()
    for args in (["agent-token", "revoke"], ["agent-token", "revoke", "ag", "--id", "1"]):
        r = e.cli(*args)
        assert r.returncode == 1
        assert EITHER in r.stderr and "請給代理名字或 --id，二選一" in r.stderr
        assert e.table() == before
    r = e.cli("agent-token", "revoke", "--id", "abc")
    assert r.returncode == 2
    assert e.table() == before


def test_store_revoke_agent_token_returns_none_for_everything_else(e):
    # TC-054
    st = _store()
    e.agent("ag")
    e.run_token()
    e.pat()
    assert st.revoke_agent_token(e.tokens, 1) == {"agent_name": "ag"}
    before = e.table()
    for i in (1, 2, 3, 999):
        assert st.revoke_agent_token(e.tokens, i) is None
    assert st.revoke_agent_token(e.tmp / "nope" / "tokens.db", 1) is None
    assert e.table() == before


# ---- US5 -----------------------------------------------------------------------------------------------------------

def test_revoke_by_id_does_not_ask_for_confirmation(two):
    # TC-060
    e, _, _ = two
    r = subprocess.run([sys.executable, "-m", "abf_platform", "agent-token", "revoke", "--id", "1"],
                       env=e.env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
    assert r.returncode == 0 and e.revoked_at(1) is not None


def test_no_actions_name_mentions_a_token():
    # TC-061
    from abf_platform import actions
    assert not [n for n in dir(actions) if re.search(r"user|pat\b|pat_|token", n, re.I)]


def test_no_oldest_mode_and_no_json_or_all_flags(two):
    # TC-062 TC-064
    e, _, _ = two
    before = e.table()
    assert e.cli("agent-token", "revoke", "ag", "--oldest").returncode == 2
    assert e.cli("agent-token", "list", "--json").returncode == 2
    assert e.cli("agent-token", "list", "--all").returncode == 2
    assert e.table() == before


def test_pat_list_lists_only_pats(e):
    # TC-063
    e.agent("ag")
    e.agent("ag")
    e.pat()
    r = e.cli("pat", "list")
    assert r.returncode == 0 and len(_lines(r)) == 1 and "agent" not in r.stdout


def test_the_tokens_table_columns_are_unchanged(e):
    # TC-065
    e.agent("ag")
    con = sqlite3.connect(str(e.tokens))
    cols = [r[1] for r in con.execute("PRAGMA table_info(tokens)")]
    con.close()
    assert cols == ["id", "token_hash", "created_at", "kind", "agent_name", "revoked_at", "run_name", "expires_at",
                    "ended_at", "user_id", "label", "grant_id"]


def test_list_changes_nothing_and_revoke_id_changes_only_its_row(two):
    # TC-066
    e, _, _ = two
    e.run_token()
    before = e.table()
    e.cli("agent-token", "list")
    assert e.table() == before
    assert e.cli("agent-token", "revoke", "--id", "1").returncode == 0
    after = e.table()
    assert before[0][5] is None and after[0][5] is not None
    assert [r[:5] + r[6:] for r in after] == [r[:5] + r[6:] for r in before]
    assert after[1:] == before[1:]


# ---- constitution and safety net -------------------------------------------------------------------------------------

def test_no_secret_is_printed_on_any_error_path(e):
    # TC-070
    e.agent("ag")
    e.agent("ag")
    run = e.id_of(e.run_token())
    pat = e.id_of(e.pat())
    for args in (["--id", "999"], ["--id", str(run)], ["--id", str(pat)], [], ["ag", "--id", "1"], ["--id", "abc"]):
        r = e.cli("agent-token", "revoke", *args)
        e.no_secrets(r.stdout, r.stderr)


def _func(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


def test_cli_is_a_thin_caller_of_the_store():
    # TC-071
    src = (PKG / "cli.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for fn, call in (("cmd_agent_token_list", "list_agent_tokens"), ("cmd_agent_token_revoke", "revoke_agent_token")):
        f = _func(tree, fn)
        text = ast.get_source_segment(src, f)
        for bad in ("sqlite3", "execute(", "SELECT", "UPDATE"):
            assert bad not in text
        assert any(isinstance(n, ast.Attribute) and n.attr == call and getattr(n.value, "id", "") == "store"
                   for n in ast.walk(f))


def test_cli_and_store_actions_correspond():
    # TC-072
    cli = (PKG / "cli.py").read_text(encoding="utf-8")
    st = _store()
    pairs = {'asub.add_parser("list"': "list_agent_tokens", 'ar.add_argument("--id"': "revoke_agent_token"}
    for cli_side, store_side in pairs.items():
        assert cli_side in cli, cli_side
        assert callable(getattr(st, store_side, None)), store_side


def test_the_docs_name_the_new_commands():
    # plan test 12
    ops = (REPO / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    plat = (REPO / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    assert "agent-token list" in ops and "agent-token revoke --id" in ops
    assert "agent-token revoke --id" in plat
