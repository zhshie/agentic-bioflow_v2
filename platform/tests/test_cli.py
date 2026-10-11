# Nothing existing: tests of this folder's command line (serve, token new, mcp, rebuild); the commands are ours.
"""Command-line tests: tokens, binding, default locations, log hygiene (feature 008)."""
import os
import re
import sqlite3
import sys
from pathlib import Path

import httpx
import pytest

from helpers import (assert_loopback_only, basic_header, db_bytes, free_port, load_scenario, pkg_env,
                     run_cli, start_cli, stop_proc, wait_port)


def _env(tmp_path, **extra):
    return pkg_env(ABF_PLATFORM_DB=tmp_path / "data" / "index.db", **extra)


def test_tc017_token_new_prints_once_and_is_never_recoverable(tmp_path):
    # TC-017
    env = _env(tmp_path)
    a = run_cli(["token", "new"], env=env)
    b = run_cli(["token", "new"], env=env)
    assert a.returncode == 0 and b.returncode == 0
    ta = re.findall(r"abf_[A-Za-z0-9_-]{20,}", a.stdout)
    tb = re.findall(r"abf_[A-Za-z0-9_-]{20,}", b.stdout)
    assert len(ta) == 1 and len(tb) == 1
    assert ta[0] != tb[0]
    assert len(ta[0]) >= 32 and len(tb[0]) >= 32
    blob = db_bytes(tmp_path / "data" / "tokens.db", tmp_path / "data" / "index.db")
    assert ta[0].encode() not in blob and tb[0].encode() not in blob
    # nothing else in the output tells the token again, and there is no command that lists it
    assert a.stdout.count(ta[0]) == 1 and ta[0] not in a.stderr
    listing = run_cli(["token", "list"], env=env)
    assert listing.returncode != 0
    assert ta[0] not in listing.stdout + listing.stderr


def test_tc018_default_serve_listens_on_loopback_only(tmp_path):
    # TC-018
    env = _env(tmp_path)
    port = free_port()
    proc = start_cli(["serve", "--port", str(port)], env, tmp_path / "serve.log")
    try:
        wait_port(port, proc=proc)
        assert_loopback_only(port)
    finally:
        stop_proc(proc)


def test_tc019_explicit_host_listens_and_prints_a_risk_line(tmp_path):
    # TC-019
    env = _env(tmp_path)
    port = free_port()
    log = tmp_path / "serve.log"
    proc = start_cli(["serve", "--host", "0.0.0.0", "--port", str(port)], env, log)
    try:
        wait_port(port, proc=proc)
        r = httpx.get("http://127.0.0.1:%d/user-info" % port)
        assert r.status_code == 401
        text = log.read_text()
        assert re.search(r"warning.*(network|other machines|0\.0\.0\.0)", text, re.I), text
    finally:
        stop_proc(proc)


def test_tc035_default_locations_follow_the_overrides(tmp_path):
    # TC-035: ABF_PLATFORM_DB wins; otherwise XDG_DATA_HOME/abf-platform. Nothing lands in HOME or the cwd.
    body = load_scenario("ok_run")["requests"][0]["body"]
    for mode in ("db", "xdg"):
        home = tmp_path / mode / "home"
        cwd = tmp_path / mode / "cwd"
        home.mkdir(parents=True)
        cwd.mkdir()
        if mode == "db":
            target = tmp_path / mode / "chosen"
            env = pkg_env(HOME=home, ABF_PLATFORM_DB=target / "index.db", XDG_DATA_HOME=tmp_path / mode / "unused")
            expect_dir = target
        else:
            target = tmp_path / mode / "xdg"
            env = pkg_env(HOME=home, XDG_DATA_HOME=target)
            expect_dir = target / "abf-platform"
        t = run_cli(["token", "new"], env=env, cwd=cwd)
        token = re.search(r"abf_[A-Za-z0-9_-]+", t.stdout).group(0)
        port = free_port()
        proc = start_cli(["serve", "--port", str(port)], env, tmp_path / mode / "serve.log", cwd=cwd)
        try:
            wait_port(port, proc=proc)
            r = httpx.post("http://127.0.0.1:%d/trace/create" % port, json=body,
                           headers={"Authorization": basic_header(token)})
            assert r.status_code < 300
        finally:
            stop_proc(proc)
        found = sorted(p.name for p in expect_dir.iterdir())
        assert "index.db" in found and "tokens.db" in found, found
        assert list(home.iterdir()) == [], list(home.iterdir())
        assert list(cwd.iterdir()) == [], list(cwd.iterdir())
        if mode == "db":
            assert not (tmp_path / mode / "unused").exists()


def test_tc044_server_output_never_holds_a_token_or_authorization_header(tmp_path):
    # TC-044: a good request and a 401, then read what the receiver printed.
    env = _env(tmp_path)
    token = re.search(r"abf_[A-Za-z0-9_-]+", run_cli(["token", "new"], env=env).stdout).group(0)
    port = free_port()
    log = tmp_path / "serve.log"
    proc = start_cli(["serve", "--port", str(port)], env, log)
    wrong = "abf_" + "w" * 43
    body = load_scenario("ok_run")["requests"][0]["body"]
    try:
        wait_port(port, proc=proc)
        ok = httpx.post("http://127.0.0.1:%d/trace/create" % port, json=body,
                        headers={"Authorization": basic_header(token)})
        bad = httpx.post("http://127.0.0.1:%d/trace/create" % port, json=body,
                         headers={"Authorization": basic_header(wrong)})
        assert ok.status_code < 300 and bad.status_code == 401
    finally:
        stop_proc(proc)
    text = log.read_text()
    assert text.strip(), "the receiver printed nothing at all, so this check proves nothing"
    low = text.lower()
    assert token not in text and wrong not in text
    assert "authorization" not in low and basic_header(token).split()[1] not in text


def test_serve_creates_the_database_folder_and_refuses_a_busy_port(tmp_path):
    # Missing folders are created; a port that is taken fails with a message, not a trace.
    env = _env(tmp_path)
    port = free_port()
    proc = start_cli(["serve", "--port", str(port)], env, tmp_path / "a.log")
    try:
        wait_port(port, proc=proc)
        second = run_cli(["serve", "--port", str(port)], env=env, timeout=60)
        assert second.returncode != 0
        assert "Traceback" not in second.stderr
    finally:
        stop_proc(proc)
