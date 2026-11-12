# Nothing existing: the tests of fetch-results (test_studio_cli.py) use a platform that answers correctly; none of them feeds the command what a wrong or hostile platform answers.
"""cli-fetch-publish-figure, slice 1, correction round (lead's rulings R4 to R12): fetch-results against a platform that lies about sizes, names and pages.
Each fake that could loop gives up with an AssertionError after a number of calls, so a command that does not end fails the test instead of hanging it."""
import asyncio
import os
import re
from pathlib import Path

import pytest

from studio_harness import FakeSite, Stub, patch_session
from test_studio_cli import fetch, got


@pytest.fixture(autouse=True)
def _world(tmp_path, monkeypatch):
    for k in list(os.environ):
        if k.startswith("ABF_"):
            monkeypatch.delenv(k)
    monkeypatch.setenv("LC_ALL", "zh_TW.UTF-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    (tmp_path / "home").mkdir()
    from abf_platform import studio_cli
    monkeypatch.setattr(studio_cli, "POLL_SECONDS", 0.01)


def row(name, download=None, size=1, kind="file", enter=None):
    return {"name": name, "type": kind, "size": size, "modified": "", "enter": enter, "download": download if kind == "file" else None, "too_large": False}


def listing(rows):
    return {"found": True, "state": "ready", "path": "/f/results", "compute_env": "lab-a", "files": rows, "listed_at": 1, "reason": None, "sub": "", "bad_path": False, "max_bytes": 26214400, "top": []}


class Capped(FakeSite):
    """A FakeSite that stops the test when asked too often."""
    LIMIT = 3000

    def handle(self, name, args):
        assert len(self.calls) < self.LIMIT, "the command does not end"
        return super().handle(name, args)


class Sub(Capped):
    """The root listing is given, a folder `sub` lists `sub_rows`, files come from `files`."""

    def __init__(self, root, sub_rows=(), **kw):
        super().__init__(**kw)
        self.root, self.sub_rows = root, list(sub_rows)

    def run_outputs(self, args):
        return listing(self.sub_rows) if args.get("path") else listing(self.root)


def run(site, tmp_path, capsys, monkeypatch, extra=()):
    patch_session(monkeypatch, site)
    return fetch(["r1", "--dir", str(tmp_path / "o")] + list(extra), capsys)


# ---- R4: a command that never ends --------------------------------------------------------------------------------------------------------

def test_r4_an_empty_page_with_a_next_offset_is_refused_not_followed_forever(tmp_path, capsys, monkeypatch):
    class Empty(Capped):
        def read_run_file(self, args):
            return {"found": True, "state": "ready", "kind": "text", "text": "", "offset": args["offset"], "next_offset": (args.get("offset") or 0) + 1}
    site = Empty(files={"a.tsv": "x\n"})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and got(tmp_path / "o") == {}
    assert len(site.names("read_run_file")) <= 3


def test_r4_a_file_has_a_page_limit(tmp_path, capsys, monkeypatch):
    from abf_platform import studio_cli
    assert isinstance(studio_cli.MAX_PAGES, int)
    monkeypatch.setattr(studio_cli, "MAX_PAGES", 5)
    site = Capped(files={"a.tsv": "x" * 100, "b.tsv": "y\n"})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and got(tmp_path / "o") == {"b.tsv": b"y\n"}
    assert len(site.names("read_run_file")) <= 5 + 1 + 1
    assert "a.tsv" in out + err


def test_r4_the_whole_command_has_one_deadline(tmp_path, capsys, monkeypatch):
    from abf_platform import studio_cli
    assert studio_cli.COMMAND_DEADLINE_SECONDS > studio_cli.DEADLINE_SECONDS
    monkeypatch.setattr(studio_cli, "COMMAND_DEADLINE_SECONDS", 0.5)
    monkeypatch.setattr(studio_cli, "POLL_SECONDS", 0.05)

    class Slow(Capped):
        LIMIT = 100000

        def read_run_file(self, args):
            if args["path"].startswith("f"):
                return {"found": True, "state": "loading", "message": "wait"}
            return super().read_run_file(args)
    site = Slow(files={"f%d.tsv" % i: "x\n" for i in range(100)})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1
    assert len(site.names("read_run_file")) < 600
    assert re.search(r"f\d+\.tsv", out + err)


# ---- R5: folders --------------------------------------------------------------------------------------------------------------------------

def test_r5_the_number_of_folders_listed_is_limited_and_said(tmp_path, capsys, monkeypatch):
    from abf_platform import studio_cli
    assert isinstance(studio_cli.MAX_DIRS, int)
    monkeypatch.setattr(studio_cli, "MAX_DIRS", 10)
    site = Capped(files={"d%03d/a.tsv" % i: "x\n" for i in range(60)})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1
    assert len(site.names("run_outputs")) <= 10 + 1
    assert re.search(r"50", out + err) and "10" in out + err


# ---- R6, R7: sizes ------------------------------------------------------------------------------------------------------------------------

def test_r6_the_total_counts_the_bytes_read_and_a_negative_size_counts_as_zero(tmp_path, capsys, monkeypatch):
    from abf_platform import studio_cli
    monkeypatch.setattr(studio_cli, "MAX_TOTAL_BYTES", 20)
    site = FakeSite(files={"a.tsv": "123456789\n", "b.tsv": "123456789\n", "c.tsv": "123456789\n"}, sizes={"a.tsv": -10**12, "b.tsv": -10**12, "c.tsv": -10**12})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and sorted(got(tmp_path / "o")) == ["a.tsv", "b.tsv"]
    assert "c.tsv" in out + err


def test_r7_the_file_limit_counts_utf8_bytes_not_characters(tmp_path, capsys, monkeypatch):
    from abf_platform import studio_cli
    monkeypatch.setattr(studio_cli, "RUN_FILE_MAX_BYTES", 10)
    site = FakeSite(files={"big.tsv": "\U0001F600" * 4, "ok.tsv": "\U0001F600" * 2}, sizes={"big.tsv": 4, "ok.tsv": 2})       # the listing says 4 bytes and 2; 16 and 8 arrive
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and sorted(got(tmp_path / "o")) == ["ok.tsv"]


# ---- R8: the name that is written is the name that was listed ---------------------------------------------------------------------------

def test_r8_a_download_that_is_not_its_folder_plus_its_name_is_refused(tmp_path, capsys, monkeypatch):
    site = Sub([row("a.tsv", download="evil.R"), row("sub", kind="dir", enter="sub"), row("ok.tsv", download="ok.tsv")],
               [row("a.tsv", download="sub/Makefile")], files={"evil.R": "x\n", "sub/Makefile": "y\n", "ok.tsv": "o\n"})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and got(tmp_path / "o") == {"ok.tsv": b"o\n"}
    assert not any(a["path"] in ("evil.R", "sub/Makefile") for a in site.names("read_run_file"))


# ---- R9: odd names and odd shapes do not crash ------------------------------------------------------------------------------------------

def test_r9_a_very_long_name_is_refused_in_a_sentence(tmp_path, capsys, monkeypatch):
    long = "a" * 300 + ".tsv"
    site = Sub([row(long, download=long), row("ok.tsv", download="ok.tsv")], files={long: "x\n", "ok.tsv": "o\n"})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and got(tmp_path / "o") == {"ok.tsv": b"o\n"}
    assert "Traceback" not in out + err


def test_r9_a_lone_surrogate_in_the_text_is_refused_in_a_sentence(tmp_path, capsys, monkeypatch):
    site = FakeSite(files={"bad.tsv": "a\ud800b\n", "ok.tsv": "o\n"})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and got(tmp_path / "o") == {"ok.tsv": b"o\n"}


def test_r9_a_lone_surrogate_in_a_name_is_refused(tmp_path, capsys, monkeypatch):
    bad = "a\ud800.tsv"
    site = Sub([row(bad, download=bad), row("ok.tsv", download="ok.tsv")], files={"ok.tsv": "o\n"})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and got(tmp_path / "o") == {"ok.tsv": b"o\n"}


@pytest.mark.parametrize("files", [["x"], "abc", 5, [None], [["a.tsv"]]])
def test_r9_a_listing_that_is_not_a_list_of_objects_is_a_problem_not_a_crash(files, tmp_path, capsys, monkeypatch):
    site = Sub(None, files={"ok.tsv": "o\n"})
    site.run_outputs = lambda args: listing(files)
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and "Traceback" not in out + err


# ---- R10: what the platform says is shown without control characters ----------------------------------------------------------------------

@pytest.mark.parametrize("ctl", ["\x1b", "\x07", "\x9b", "\x85"])
def test_r10_control_characters_of_a_name_or_a_reason_never_reach_the_terminal(ctl, tmp_path, capsys, monkeypatch):
    name = "x%s[31mred.tsv" % ctl
    site = Sub([row(name, download=name), row("e.tsv", download="e.tsv"), row("p.bam", download="p.bam")], files={"e.tsv": "e\n"},
               errors={"e.tsv": {"found": True, "state": "error", "code": "failed", "reason": "no%sway" % ctl}})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1
    assert ctl not in out + err
    assert got(tmp_path / "o") == {}


def test_r10_a_not_found_message_and_a_listing_reason_are_cleaned_too(tmp_path, capsys, monkeypatch):
    site = FakeSite(files={"a.tsv": "x\n"}, outputs={"found": True, "state": "error", "reason": "bad\x1b[2Jreason"})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and "\x1b" not in out + err and "reason" in out + err
    site = FakeSite(found=False)
    site.NO_RUN = "gone\x9b!"
    rc, out, err = run(site, tmp_path / "x", capsys, monkeypatch)
    assert rc == 1 and "\x9b" not in out + err


# ---- R11: binary tables, duplicates -------------------------------------------------------------------------------------------------------

def test_r11_a_table_the_platform_calls_binary_is_a_problem(tmp_path, capsys, monkeypatch):
    site = FakeSite(files={"a.tsv": "x\n", "b.tsv": "y\n"}, binary={"a.tsv"})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and got(tmp_path / "o") == {"b.tsv": b"y\n"} and "a.tsv" in out + err


def test_r11_a_download_listed_twice_is_fetched_once_and_said(tmp_path, capsys, monkeypatch):
    site = Sub([row("a.tsv", download="a.tsv"), row("a.tsv", download="a.tsv")], files={"a.tsv": "x\n"})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert got(tmp_path / "o") == {"a.tsv": b"x\n"}
    assert len(site.names("read_run_file")) == 1
    assert out.count("read.delim") == 1


def test_r11_two_names_that_differ_only_in_case_are_fetched_once_and_it_is_a_problem(tmp_path, capsys, monkeypatch):
    site = FakeSite(files={"A.tsv": "x\n", "a.tsv": "y\n"})
    rc, out, err = run(site, tmp_path, capsys, monkeypatch)
    assert rc == 1 and len(site.names("read_run_file")) == 1 and len(got(tmp_path / "o")) == 1


# ---- R12: the token does not go to a proxy ----------------------------------------------------------------------------------------------

def test_r12_a_loopback_http_address_does_not_use_the_proxy_of_the_environment(monkeypatch):
    from abf_platform import studio_remote
    proxy, target = Stub(status=200), Stub(status=401)
    token = "abf_pat_" + "z" * 43
    try:
        for k in ("HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
            monkeypatch.setenv(k, proxy.url)
        monkeypatch.delenv("NO_PROXY", raising=False)
        monkeypatch.delenv("no_proxy", raising=False)

        async def go():
            async with studio_remote.open_session({"server": target.url, "token": token}) as session:
                await session.tool_names()
        with pytest.raises(studio_remote.StudioError):
            asyncio.run(go())
        assert proxy.requests == [], "the token was sent to the proxy"
        assert any(r[1] == "Bearer " + token for r in target.requests)
    finally:
        proxy.stop()
        target.stop()
