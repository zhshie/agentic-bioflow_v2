# Nothing existing: no test covers a command line that runs on a user's own computer with a personal token kept in a file there; test_pat.py covers the token and the HTTP door from the server's side.
"""cli-fetch-publish-figure, slice 1: the connection side (studio_remote and the studio-connect command) and the errors the fetch-results command shows.
Test case numbers are in the comments (specs/cli-fetch-publish-figure/test-case.md). Nothing here uses a real token: every token is made by the test."""
import ast
import hashlib
import json
import logging
import os
import re
import sqlite3
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT, free_port, mcp_http_call, own_runs, pkg_env, start_cli, stop_proc, wait_port
from studio_harness import FakeSite, Stub, patch_session
from test_station_platform import state_db
from test_web_wording_sweep import banned_in, CJK_RE

PKG = PLATFORM_DIR / "abf_platform"
SECRET = "abf_" + "pat_SECRETMARK0123456789abcdefghijklmnopqrstu"      # a made-up token with a mark that can be searched for
POSIX = os.name == "posix"


# ---- helpers ----------------------------------------------------------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _world(tmp_path, monkeypatch):
    for k in list(os.environ):
        if k.startswith("ABF_"):
            monkeypatch.delenv(k)
    monkeypatch.setenv("LC_ALL", "zh_TW.UTF-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))      # not the HOME variable: a subprocess would lose the user site-packages
    monkeypatch.setenv("ABF_STUDIO_CONFIG", str(tmp_path / "cfg" / "studio.json"))
    (tmp_path / "home").mkdir()
    from abf_platform import studio_remote
    monkeypatch.setattr(studio_remote, "RETRY_DELAY", 0.0)
    monkeypatch.setattr(studio_remote, "CALL_TIMEOUT", 5.0)
    return tmp_path


def cfg_path(tmp_path):
    return tmp_path / "cfg" / "studio.json"


def main(argv, capsys, stdin=None, monkeypatch=None):
    """Run the real command line in process; returns (exit code, stdout, stderr)."""
    from abf_platform import cli
    if stdin is not None:
        import io
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    try:
        rc = cli.main(argv)
    except SystemExit as e:
        rc = e.code
    out = capsys.readouterr()
    return rc, out.out, out.err


def connect(server, capsys, monkeypatch, token=SECRET, extra=()):
    return main(["studio-connect", "--server", server, "--token-stdin"] + list(extra), capsys, stdin=token + "\n", monkeypatch=monkeypatch)


def write_config(tmp_path, server, token=SECRET, mode=0o600):
    from abf_platform import studio_remote
    studio_remote.save_config(server, token)
    if POSIX:
        os.chmod(cfg_path(tmp_path), mode)
    return cfg_path(tmp_path)


def no_connection(monkeypatch):
    """Any attempt to open the MCP transport fails the test: the check of the settings file comes before every connection."""
    import mcp.client.streamable_http as transport

    def boom(*a, **k):
        raise AssertionError("a connection was made")
    monkeypatch.setattr(transport, "streamable_http_client", boom)


def words_ok(text):
    """The wording rule for a message: written Chinese, no stack, no inner path or SQL, a next step."""
    assert "Traceback" not in text and 'File "' not in text and not re.search(r"\bSELECT\b|\bINSERT\b|sqlite", text), text
    assert banned_in(text) == [], (banned_in(text), text)
    assert "請" in text and "。" in text, text


# ---- a real server for the tests that need one ------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """`abf-platform mcp --http` with two users (each with a personal token), one revoked token, and a run that belongs to the first."""
    from test_mcp import _three_runs
    from abf_platform import status, store
    tmp = tmp_path_factory.mktemp("srv")
    plat, _ = _three_runs(tmp)
    tokens = plat.tokens
    alice = store.create_user(tokens, "alice", "lab-x")
    bob = store.create_user(tokens, "bob", "lab-y")
    t_alice = store.create_token(tokens, kind="pat", user_id=alice)
    t_bob = store.create_token(tokens, kind="pat", user_id=bob)
    t_revoked = store.create_token(tokens, kind="pat", user_id=alice)
    con = sqlite3.connect(str(tokens))
    pid = con.execute("SELECT id FROM tokens WHERE token_hash = ?", (hashlib.sha256(t_revoked.encode()).hexdigest(),)).fetchone()[0]
    con.close()
    assert store.revoke_pat(tokens, pid) == 1
    runs = status.list_runs(plat.index, time.time())
    own_runs(state_db(plat), alice, [r["name"] for r in runs])
    port = free_port()
    proc = start_cli(["mcp", "--http", "--port", str(port)], pkg_env(ABF_PLATFORM_DB=plat.index), tmp / "mcp.log")
    try:
        wait_port(port, proc=proc)
        yield {"url": "http://127.0.0.1:%d" % port, "alice": t_alice, "bob": t_bob, "revoked": t_revoked, "run": runs[0]["id"], "tokens": tokens,
               "plat": plat, "alice_id": alice}      # slice 2: the platform folder and the first user, for the tests that look at the tables
    finally:
        stop_proc(proc)


# ---- US1: studio-connect ----------------------------------------------------------------------------------------------------------------

def test_tc001_studio_connect_saves_server_and_token_and_prints_neither_token_nor_more(tmp_path, capsys, monkeypatch):
    # TC-001
    import getpass
    from abf_platform import studio_remote
    opened = patch_session(monkeypatch, FakeSite())
    rc, out, err = connect("https://platform.example", capsys, monkeypatch)
    assert rc == 0, (out, err)
    assert json.loads(cfg_path(tmp_path).read_text(encoding="utf-8")) == {"server": "https://platform.example", "token": SECRET}
    assert "https://platform.example" in out and "權杖已存入 %s" % cfg_path(tmp_path) in out
    assert SECRET not in out + err
    assert opened and opened[0]["token"] == SECRET        # the check connected with the token it was given
    # hidden input: getpass is what asks when --token-stdin is not given
    asked = []
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": asked.append(prompt) or "abf_pat_" + "q" * 43)
    rc, out, err = main(["studio-connect", "--server", "https://platform.example"], capsys)
    assert rc == 0 and asked and json.loads(cfg_path(tmp_path).read_text())["token"] == "abf_pat_" + "q" * 43
    # the default place when ABF_STUDIO_CONFIG is not set
    monkeypatch.delenv("ABF_STUDIO_CONFIG")
    assert studio_remote.config_path() == tmp_path / "home" / ".abf" / "studio.json"
    rc, out, err = connect("https://platform.example", capsys, monkeypatch)
    assert rc == 0 and (tmp_path / "home" / ".abf" / "studio.json").is_file()


def test_tc002_there_is_no_token_flag_and_a_refused_one_is_not_echoed(tmp_path, capsys):
    # TC-002
    from abf_platform import cli
    assert "--token" not in cli._option_names(cli.build_parser())
    for argv in (["studio-connect", "--server", "https://p.example", "--token", "abf_pat_FAKE123"],
                 ["studio-connect", "--server", "https://p.example", "--token=abf_pat_FAKE123"],
                 ["--json", "studio-connect", "--server", "https://p.example", "--token", "abf_pat_FAKE123"]):
        rc, out, err = main(argv, capsys)
        assert rc not in (0, None), argv
        assert "abf_pat_FAKE123" not in out + err, (argv, out, err)
        assert not cfg_path(tmp_path).exists()


@pytest.mark.parametrize("bad", ["http://example.com", "https://platform.example/mcp", "ftp://platform.example", "https://", "https://user@platform.example",
                                 "http://127.0.0.1.example.com", "https://platform.example:99999"])
def test_tc003_a_server_address_must_be_https_host_without_path(bad, tmp_path, capsys, monkeypatch):
    # TC-003
    opened = patch_session(monkeypatch, FakeSite())
    rc, out, err = connect(bad, capsys, monkeypatch)
    assert rc not in (0, None) and "https://" in err and "路徑" in err
    assert opened == [] and not cfg_path(tmp_path).exists()
    assert SECRET not in out + err


@pytest.mark.parametrize("ok", ["http://127.0.0.1:8080", "http://localhost:8080"])
def test_tc004_loopback_http_is_the_one_exception(ok, tmp_path, capsys, monkeypatch):
    # TC-004
    rc, out, err = connect(ok, capsys, monkeypatch, extra=["--no-check"])
    assert rc == 0, err
    assert json.loads(cfg_path(tmp_path).read_text())["server"] == ok


def test_tc005_a_check_that_fails_saves_nothing_and_keeps_the_old_file(server, tmp_path, capsys, monkeypatch):
    # TC-005
    from abf_platform import studio_remote
    old = write_config(tmp_path, "https://old.example", token="abf_pat_OLD" + "o" * 40)
    before = old.read_bytes()
    rc, out, err = connect(server["url"], capsys, monkeypatch, token="abf_pat_" + "w" * 43)
    assert rc == 3 and studio_remote.tr("token_bad") in err and old.read_bytes() == before
    rc, out, err = connect("http://127.0.0.1:%d" % free_port(), capsys, monkeypatch)
    assert rc == 3 and "本機網路" in err and old.read_bytes() == before
    assert SECRET not in out + err


def test_tc006_no_check_saves_without_any_connection(tmp_path, capsys, monkeypatch):
    # TC-006
    from abf_platform import studio_remote

    def boom(*a, **k):
        raise AssertionError("a connection was made")
    monkeypatch.setattr(studio_remote, "open_session", boom)
    rc, out, err = connect("https://platform.example", capsys, monkeypatch, extra=["--no-check"])
    assert rc == 0 and "權杖已存入" in out and cfg_path(tmp_path).is_file()


@pytest.mark.skipif(not POSIX, reason="TC-007: file modes are checked on POSIX only (Windows reports bits that mean nothing)")
def test_tc007_config_is_0600_in_a_0700_folder_and_a_failed_write_leaves_nothing_half(tmp_path, capsys, monkeypatch):
    # TC-007
    rc, out, err = connect("https://platform.example", capsys, monkeypatch, extra=["--no-check"])
    assert rc == 0
    assert stat.S_IMODE(cfg_path(tmp_path).stat().st_mode) == 0o600 and stat.S_IMODE(cfg_path(tmp_path).parent.stat().st_mode) == 0o700
    before = cfg_path(tmp_path).read_bytes()

    def failing_replace(a, b):
        raise OSError("disk full")
    monkeypatch.setattr(os, "replace", failing_replace)
    rc, out, err = connect("https://other.example", capsys, monkeypatch, token="abf_pat_" + "n" * 43, extra=["--no-check"])
    assert rc not in (0, None) and "abf_pat_" + "n" * 43 not in out + err and "Traceback" not in err
    assert sorted(p.name for p in cfg_path(tmp_path).parent.iterdir()) == ["studio.json"] and cfg_path(tmp_path).read_bytes() == before


def test_tc008_running_it_again_overwrites_and_says_so(tmp_path, capsys, monkeypatch):
    # TC-008
    rc, out, err = connect("https://platform.example", capsys, monkeypatch, extra=["--no-check"])
    assert rc == 0 and "已覆蓋" not in out
    rc, out, err = connect("https://platform.example", capsys, monkeypatch, token="abf_pat_" + "z" * 43, extra=["--no-check"])
    assert rc == 0 and "已覆蓋" in out and json.loads(cfg_path(tmp_path).read_text())["token"] == "abf_pat_" + "z" * 43


def test_tc009_the_environment_token_wins_over_the_file(tmp_path, capsys, monkeypatch):
    # TC-009
    stub = Stub(status=401)
    try:
        write_config(tmp_path, stub.url, token="abf_pat_AAAA" + "a" * 39)
        monkeypatch.setenv("ABF_PAT", "abf_pat_BBBB" + "b" * 39)
        rc, out, err = main(["fetch-results", "r1"], capsys)
    finally:
        stub.stop()
    seen = {r[1] for r in stub.requests}
    assert seen == {"Bearer abf_pat_BBBB" + "b" * 39}, seen
    assert "abf_pat_AAAA" not in out + err and "abf_pat_BBBB" not in out + err


def test_tc010_not_configured_says_what_to_do_exit_2_and_does_not_connect(tmp_path, capsys, monkeypatch):
    # TC-010
    no_connection(monkeypatch)
    rc, out, err = main(["fetch-results", "r1"], capsys)
    assert rc == 2 and "abf-platform studio-connect --server" in err
    assert not (tmp_path / "home" / "abf-results").exists() and not cfg_path(tmp_path).exists()
    words_ok(err)


@pytest.mark.skipif(not POSIX, reason="TC-011: file modes are checked on POSIX only")
def test_tc011_a_config_others_can_read_is_refused(tmp_path, capsys, monkeypatch):
    # TC-011
    path = write_config(tmp_path, "https://platform.example", mode=0o644)
    no_connection(monkeypatch)
    rc, out, err = main(["fetch-results", "r1"], capsys)
    assert rc == 2 and "chmod 600 %s" % path in err
    assert SECRET not in out + err
    words_ok(err)


def test_tc012_where_permission_bits_mean_nothing_it_reminds_once_and_does_not_refuse(tmp_path, capsys, monkeypatch):
    # TC-012
    from abf_platform import studio_remote
    monkeypatch.setattr(studio_remote, "permission_bits_trusted", lambda: False)
    opened = patch_session(monkeypatch, FakeSite(files={"a.tsv": "x"}))
    rc, out, err = connect("https://platform.example", capsys, monkeypatch)
    assert rc == 0 and "雲端同步" in out and out.count("雲端同步") == 1
    if POSIX:
        os.chmod(cfg_path(tmp_path), 0o666)
    opened.clear()
    rc, out, err = main(["fetch-results", "r1", "--dir", str(tmp_path / "got")], capsys)
    assert "chmod" not in out + err and rc != 2 and opened


def test_tc013_no_browser_no_keyring_no_new_dependency_and_the_help_says_where_the_token_comes_from(capsys):
    # TC-013
    for name in ("studio_cli.py", "studio_remote.py"):
        text = (PKG / name).read_text(encoding="utf-8")
        assert not re.search(r"webbrowser|keyring|create_token|oauth", text, re.I), name
    rc, out, err = main(["studio-connect", "--help"], capsys)
    assert rc == 0 and "pat new" in out
    pyproject = (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dependencies = ["mcp>=2.3,<3", "python-multipart"]' in pyproject


# ---- US2 / US4: what fetch-results shows when the connection or the site is not right -----------------------------------------------------

def _site_with_one_file(read_answer, envs=None, env_error=False):
    return FakeSite(files={"a.tsv": "x\ty\n"}, errors={"a.tsv": read_answer}, envs=envs, env_error=env_error)


SITE_DOWN = {"found": True, "state": "error", "code": "refused",
             "reason": "No open connection to the site. Log in once in a WSL terminal first and leave it open."}


def test_tc022_a_closed_site_link_and_a_refused_path_are_different_messages(tmp_path, capsys, monkeypatch):
    # TC-022
    from abf_platform import studio_remote
    write_config(tmp_path, "https://platform.example")
    patch_session(monkeypatch, _site_with_one_file(SITE_DOWN))
    rc1, out1, err1 = main(["fetch-results", "r1", "--dir", str(tmp_path / "d1")], capsys)
    refused = {"found": True, "state": "error", "code": "bad_path", "reason": "站台拒絕讀取這個路徑（不在允許讀取的資料夾內）"}
    patch_session(monkeypatch, _site_with_one_file(refused))
    rc2, out2, err2 = main(["fetch-results", "r1", "--dir", str(tmp_path / "d2")], capsys)
    assert rc1 == 1 and rc2 == 1
    assert studio_remote.tr("site_closed") in out1 + err1 and refused["reason"] not in out1 + err1
    assert "路徑不正確" not in out1 + err1
    assert refused["reason"] in out2 + err2 and studio_remote.tr("site_closed") not in out2 + err2
    for answer_code in ("site_unreachable", "agent_offline"):       # the codes count as well, whatever the words say
        patch_session(monkeypatch, _site_with_one_file({"found": True, "state": "error", "code": answer_code, "reason": "x"}))
        rc, out, err = main(["fetch-results", "r1", "--dir", str(tmp_path / ("d" + answer_code))], capsys)
        assert studio_remote.tr("site_closed") in out + err, answer_code


def test_tc023_the_site_connection_field_is_printed_when_present_and_silent_when_absent(tmp_path, capsys, monkeypatch):
    # TC-023
    write_config(tmp_path, "https://platform.example")
    env = {"name": "lab-a", "agent": "agent-7", "site_connection": {"state": "closed", "as_of": "2026-11-12T08:00:00Z", "agent": "agent-7"}}
    patch_session(monkeypatch, _site_with_one_file(SITE_DOWN, envs=[env]))
    rc, out, err = main(["fetch-results", "r1", "--dir", str(tmp_path / "a")], capsys)
    text = out + err
    assert rc == 1 and "closed" in text and "2026-11-12T08:00:00Z" in text and "agent-7" in text
    for envs, env_error in (([{"name": "lab-a", "agent": "agent-7"}], False), ([], False), (None, True)):
        patch_session(monkeypatch, _site_with_one_file(SITE_DOWN, envs=envs, env_error=env_error))
        rc, out, err = main(["fetch-results", "r1", "--dir", str(tmp_path / "b")], capsys)
        assert rc == 1 and "as_of" not in out + err and "Traceback" not in out + err


def test_tc029_somebody_elses_run_and_a_missing_run_get_the_same_one_sentence(server, tmp_path, capsys):
    # TC-029
    write_config(tmp_path, server["url"], token=server["bob"])
    rc1, out1, err1 = main(["fetch-results", server["run"]], capsys)
    rc2, out2, err2 = main(["fetch-results", "no-such-run-0000"], capsys)
    assert rc1 == rc2 == 1 and (out1, err1) == (out2, err2) and "Run not found" in out1 + err1, (rc1, out1, err1, rc2, out2, err2)
    assert not (tmp_path / "home" / "abf-results").exists()
    assert server["bob"] not in out1 + err1


# ---- US4: the connection errors, with a real server and stubs -----------------------------------------------------------------------------

def test_tc040_a_wrong_or_revoked_token_gives_the_token_message_exit_3(server, tmp_path, capsys):
    # TC-040
    from abf_platform import studio_remote
    for token in ("abf_pat_" + "x" * 43, server["revoked"]):
        write_config(tmp_path, server["url"], token=token)
        rc, out, err = main(["fetch-results", server["run"]], capsys)
        assert rc == 3 and studio_remote.tr("token_bad") in err and token not in out + err
        words_ok(err)


def test_tc041_a_closed_port_says_check_the_local_network(tmp_path, capsys):
    # TC-041
    write_config(tmp_path, "http://127.0.0.1:%d" % free_port())
    rc, out, err = main(["fetch-results", "r1"], capsys)
    assert rc == 3 and "本機網路" in err and "--server" in err and "Traceback" not in err
    words_ok(err)


@pytest.mark.parametrize("status", [502, 503, 504])
def test_tc042_a_gateway_error_says_the_public_address_does_not_answer(status, tmp_path, capsys):
    # TC-042
    from abf_platform import studio_remote
    stub = Stub(status=status)
    try:
        write_config(tmp_path, stub.url)
        rc, out, err = main(["fetch-results", "r1"], capsys)
    finally:
        stub.stop()
    assert rc == 3 and studio_remote.tr("unreachable", url=stub.url) in err and "Tailscale Funnel" in err and stub.url in err
    words_ok(err)


def test_tc042_a_timeout_and_a_failed_tls_handshake_say_the_same(tmp_path, capsys, monkeypatch):
    # TC-042
    from abf_platform import studio_remote
    monkeypatch.setattr(studio_remote, "CALL_TIMEOUT", 0.4)
    slow = Stub(status=200, delay=3)
    try:
        write_config(tmp_path, slow.url)
        rc, out, err = main(["fetch-results", "r1"], capsys)
    finally:
        slow.stop()
    assert rc == 3 and studio_remote.tr("unreachable", url=slow.url) in err
    plain = Stub(status=200)       # a server that does not speak TLS, reached over https
    try:
        https = "https://127.0.0.1:%d" % plain.port
        write_config(tmp_path, https)
        rc, out, err = main(["fetch-results", "r1"], capsys)
    finally:
        plain.stop()
    assert rc == 3 and studio_remote.tr("unreachable", url=https) in err


def test_tc043_retries_at_most_twice_two_seconds_apart_and_always_ends(tmp_path, capsys, monkeypatch):
    # TC-043
    import asyncio
    from abf_platform import studio_remote
    source = (PKG / "studio_remote.py").read_text(encoding="utf-8")
    assert re.search(r"^CALL_TIMEOUT = 30(\.0)?\b", source, re.M) and re.search(r"^RETRIES = 2\b", source, re.M) and re.search(r"^RETRY_DELAY = 2(\.0)?\b", source, re.M)
    slept = []

    async def fake_sleep(s):
        slept.append(s)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(studio_remote, "RETRY_DELAY", 2.0)
    stub = Stub(status=503)
    try:
        write_config(tmp_path, stub.url)
        t0 = time.time()
        rc, out, err = main(["fetch-results", "r1"], capsys)
    finally:
        stub.stop()
    assert rc == 3 and time.time() - t0 < 60
    assert len(stub.initialize_posts()) == 3 and slept == [2.0, 2.0], (len(stub.initialize_posts()), slept)
    hang = Stub(status=200, delay=3)      # never answers in time: each try is ended by the call timeout, and the whole ends
    monkeypatch.setattr(studio_remote, "CALL_TIMEOUT", 0.3)
    try:
        write_config(tmp_path, hang.url)
        t0 = time.time()
        rc, out, err = main(["fetch-results", "r1"], capsys)
    finally:
        hang.stop()
    assert rc == 3 and time.time() - t0 < 30


@pytest.mark.parametrize("status", [403, 404])
def test_tc044_a_refused_session_says_run_it_again_then_ask_the_administrator(status, tmp_path, capsys):
    # TC-044
    stub = Stub(status=status)
    try:
        write_config(tmp_path, stub.url)
        rc, out, err = main(["fetch-results", "r1"], capsys)
    finally:
        stub.stop()
    assert rc == 3 and "重新執行一次" in err and "管理者" in err
    words_ok(err)


def test_tc045_every_message_says_what_happened_and_what_to_do(server, tmp_path, capsys, monkeypatch):
    # TC-045
    from abf_platform import studio_remote
    messages = []
    rc, out, err = main(["fetch-results", "r1"], capsys)                                         # TC-010
    messages.append(err)
    if POSIX:                                                                                    # TC-011
        write_config(tmp_path, "https://platform.example", mode=0o644)
        messages.append(main(["fetch-results", "r1"], capsys)[2])
    write_config(tmp_path, server["url"], token="abf_pat_" + "x" * 43)                           # TC-040
    messages.append(main(["fetch-results", "r1"], capsys)[2])
    write_config(tmp_path, "http://127.0.0.1:%d" % free_port())                                  # TC-041
    messages.append(main(["fetch-results", "r1"], capsys)[2])
    for status in (503, 403):                                                                    # TC-042, TC-044
        stub = Stub(status=status)
        try:
            write_config(tmp_path, stub.url)
            messages.append(main(["fetch-results", "r1"], capsys)[2])
        finally:
            stub.stop()
    write_config(tmp_path, "https://platform.example")                                           # TC-021 and TC-022
    patch_session(monkeypatch, _site_with_one_file(SITE_DOWN))
    rc, out, err = main(["fetch-results", "r1", "--dir", str(tmp_path / "x")], capsys)
    messages.append(err)
    patch_session(monkeypatch, _site_with_one_file({"found": True, "state": "error", "code": "refused", "reason": "站台拒絕讀取該路徑，不在允許的資料夾內。"}))
    rc, out, err = main(["fetch-results", "r1", "--dir", str(tmp_path / "y")], capsys)
    messages.append(err)
    assert len(messages) >= 7
    for m in messages:
        words_ok(m)


# ---- the constitution and the safety net ------------------------------------------------------------------------------------------------

def test_tc079_the_token_is_never_printed_or_logged_on_the_good_paths(tmp_path, capsys, monkeypatch, caplog):
    # TC-079
    caplog.set_level(logging.DEBUG)
    patch_session(monkeypatch, FakeSite(files={"ASV_table.tsv": "a\tb\n1\t2\n"}))
    seen = [connect("https://platform.example", capsys, monkeypatch, extra=["--no-check"]),
            main(["fetch-results", "r1", "--dir", str(tmp_path / "ok")], capsys)]
    for rc, out, err in seen:
        assert rc == 0 and SECRET not in out + err
    assert SECRET not in caplog.text
    assert (tmp_path / "ok" / "ASV_table.tsv").is_file() and all(SECRET not in p.read_text() for p in (tmp_path / "ok").rglob("*") if p.is_file())


def test_tc080_the_token_is_not_in_any_failure_either_with_debug(server, tmp_path, capsys, monkeypatch, caplog):
    # TC-080
    from abf_platform import studio_remote
    caplog.set_level(logging.DEBUG)
    collected = []
    monkeypatch.setattr(studio_remote, "CALL_TIMEOUT", 0.4)
    write_config(tmp_path, server["url"], token=SECRET)
    collected.append(main(["--debug", "fetch-results", "r1", "--dir", str(tmp_path / "e1")], capsys))      # 401
    for kind, stub in (("unreachable", Stub(status=503)), ("timeout", Stub(status=200, delay=3))):
        try:
            write_config(tmp_path, stub.url)
            collected.append(main(["--debug", "fetch-results", "r1", "--dir", str(tmp_path / "e2")], capsys))
        finally:
            stub.stop()
    write_config(tmp_path, "https://platform.example")
    patch_session(monkeypatch, _site_with_one_file(SITE_DOWN))
    collected.append(main(["--debug", "fetch-results", "r1", "--dir", str(tmp_path / "e3")], capsys))
    assert [c[0] for c in collected] == [3, 3, 3, 1], [c[0] for c in collected]
    for rc, out, err in collected:
        assert SECRET not in out + err
    assert SECRET not in caplog.text
    debug_lines = [l for rc, out, err in collected for l in err.splitlines() if l.startswith("debug:")]
    assert any("options" in l for l in debug_lines) and not any("e1" in l or "--dir " + str(tmp_path) in l for l in debug_lines)


def test_tc081_json_does_not_crash_is_valid_and_has_no_token(server, tmp_path, capsys, monkeypatch):
    # TC-081
    with monkeypatch.context() as faked:          # a targeted restore: a bare monkeypatch.undo() also drops the _world fixture's home patch
        patch_session(faked, FakeSite(files={"ASV_table.tsv": "a\tb\n"}))
        rc, out, err = main(["--json", "studio-connect", "--server", "https://platform.example", "--token-stdin", "--no-check"], capsys,
                            stdin=SECRET + "\n", monkeypatch=faked)
        assert rc == 0 and json.loads(out)["ok"] is True and SECRET not in out + err
        rc, out, err = main(["--json", "fetch-results", "r1", "--dir", str(tmp_path / "j")], capsys)
        assert rc == 0 and json.loads(out)["ok"] is True and SECRET not in out + err
    write_config(tmp_path, server["url"], token="abf_pat_" + "x" * 43)
    rc, out, err = main(["--json", "fetch-results", "r1"], capsys)
    assert rc == 3 and json.loads(err)["ok"] is False and "abf_pat_" + "x" * 43 not in out + err
    rc, out, err = main(["--json", "studio-connect", "--server", "http://example.com", "--token-stdin"], capsys, stdin=SECRET + "\n", monkeypatch=monkeypatch)
    assert rc != 0 and SECRET not in out + err and json.loads(err)["ok"] is False


def test_tc082_the_commands_open_no_database(tmp_path, capsys, monkeypatch):
    # TC-082
    empty = tmp_path / "emptydb"
    empty.mkdir()
    env = pkg_env(ABF_PLATFORM_DB=empty / "index.db", ABF_STUDIO_CONFIG=cfg_path(tmp_path))
    r = subprocess.run([sys.executable, "-m", "abf_platform", "studio-connect", "--server", "https://platform.example", "--token-stdin", "--no-check"],
                       env=env, input=SECRET + "\n", capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    r = subprocess.run([sys.executable, "-m", "abf_platform", "fetch-results", "r1", "--dir", str(tmp_path / "got")],
                       env=dict(env, ABF_STUDIO_CONFIG=str(tmp_path / "nowhere" / "studio.json")), capture_output=True, text=True, timeout=120)
    assert r.returncode == 2
    patch_session(monkeypatch, FakeSite(files={"ASV_table.tsv": "a\tb\n"}))
    monkeypatch.setenv("ABF_PLATFORM_DB", str(empty / "index.db"))
    write_config(tmp_path, "https://platform.example")
    rc, out, err = main(["fetch-results", "r1", "--dir", str(tmp_path / "got2")], capsys)
    assert rc == 0 and list(empty.iterdir()) == []


FORBIDDEN_IMPORTS = {"subprocess", "socket", "urllib", "requests", "httpx", "store", "actions", "figures", "webbrowser", "keyring"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            found += [(a.name.split(".")[0], a.name, None) for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            mod = ("." * n.level) + (n.module or "")
            found.append((mod.lstrip(".").split(".")[0], mod, [a.name for a in n.names]))
    return found


def test_tc083_the_new_modules_import_nothing_forbidden():
    # TC-083
    for name in ("studio_cli.py", "studio_remote.py"):
        for root, mod, names in _imports(PKG / name):
            assert root not in FORBIDDEN_IMPORTS or mod.lstrip(".") == "actions.figures", (name, mod)
            if "figures" in mod.split("."):       # slice 2 (TC-083): the limits of the gallery, constants only, and only in studio_cli
                assert name == "studio_cli.py" and mod.lstrip(".") == "actions.figures" and names and all(n.startswith("MAX_") for n in names), (name, mod, names)
                continue
            assert "store" not in mod.split(".") and "actions" not in mod.split("."), (name, mod)
            if "jobs" in mod.split("."):      # the one exception: a constant, and only in studio_cli
                assert name == "studio_cli.py" and names == ["RUN_FILE_MAX_BYTES"], (name, mod, names)
    stdlib_and_mcp = {"__future__", "asyncio", "contextlib", "getpass", "json", "os", "sys", "time", "pathlib", "ssl", "re", "errno",
                      "exceptiongroup", "typing", "anyio", "httpx2", "mcp"}
    for root, mod, names in _imports(PKG / "studio_remote.py"):
        assert root in stdlib_and_mcp, mod
    for name in ("studio_cli.py", "studio_remote.py"):
        text = (PKG / name).read_text(encoding="utf-8")
        assert not re.search(r"\bimport httpx\b|from httpx import|requests\.|urllib", text.replace("httpx2", "")), name


def test_tc085_the_tools_the_commands_call_exist_on_the_server_and_are_the_slice_one_set(server):
    # TC-085
    called = set()
    for name in ("studio_cli.py", "studio_remote.py"):
        for n in ast.walk(ast.parse((PKG / name).read_text(encoding="utf-8"))):
            if not isinstance(n, ast.Call):
                continue
            fn = getattr(n.func, "attr", getattr(n.func, "id", ""))
            index = {"call_tool": 0, "_ask": 1}.get(fn)      # call_tool(name, args) and the polling helper _ask(session, name, args)
            if index is not None and len(n.args) > index and isinstance(n.args[index], ast.Constant):
                called.add(n.args[index].value)
    assert called == {"run_outputs", "read_run_file", "list_compute_envs", "publish_figure"}, called      # slice 2 adds publish_figure
    tools, _ = mcp_http_call(server["url"] + "/mcp", [], token=server["alice"])
    assert called <= {t.name for t in tools}
    text = (PKG / "studio_cli.py").read_text(encoding="utf-8")
    assert not re.search(r"readRoots|read_roots|owner_id|user_id", text)      # no owner filter and no root check of its own


def test_the_wording_of_the_connection_messages_zh_en_same_keys_and_written_chinese():
    # TC-078
    from abf_platform import studio_remote
    zh, en = studio_remote.STRINGS["zh"], studio_remote.STRINGS["en"]
    assert set(zh) == set(en)
    for k, v in en.items():
        assert not CJK_RE.search(v), k
    for k, v in zh.items():
        assert banned_in(v) == [], (k, banned_in(v))
