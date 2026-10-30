# Nothing existing: unit tests of the first ssh step (realpath) of list/read file/read log when the shared connection is gone.
"""A dead site connection at the realpath step is site_unreachable with the log-in line, not a path refusal (realpath-site-down).
TC numbers are in the comments, see specs/realpath-site-down/test-case.md."""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from abf_station import handlers, readfile, readlog, rules
from abf_station.site import SiteResult

WORK = "/data/work"
OPEN_CMD = "ssh -fN -M -S /tmp/cm-nano4 nano4"
NO_MASTER = "on_site: needs-human reason=no-master\nrun this: %s\n" % OPEN_CMD
RELOGIN = "Log in once in a WSL terminal first"
SECRET = "hunter2-TOKEN-xyz"
CE = {"platform": "slurm-platform", "workDir": WORK, "headQueue": "q"}
TASK = WORK + "/work/ab/cdef"

REFUSAL = {
    "listing": "the site could not say where the path leads, so it is not listed (站台無法確認路徑的真實位置)",
    "readfile": "the site could not say where the path leads, so it is not read (站台無法確認路徑的真實位置)",
    "readlog": "the site could not say where the task folder leads, so it is not read (站台無法確認路徑的真實位置)",
}


class FakeSite:
    def __init__(self, realpath, reach_ok=False, reach_err=NO_MASTER, after=None):
        self.realpath, self.reach_ok, self.reach_err, self.after = realpath, reach_ok, reach_err, after
        self.calls = []

    def call(self, args, input=None, timeout=None):
        self.calls.append(args)
        first = args[0]
        if first == "--check-reach":
            return SiteResult(0, b"", "") if self.reach_ok else SiteResult(1, b"", self.reach_err)
        if first.startswith("realpath"):
            return self.realpath(args)
        if self.after:
            return self.after(args)
        return SiteResult(0, b"", "")


def down(rc=255, err="Permission denied (keyboard-interactive)", timed_out=False):
    return lambda args: SiteResult(rc, b"", err, timed_out)


def echo(args):
    """A realpath that resolves each wanted path to itself."""
    wanted = args[0].split(" -- ", 1)[1]
    paths = [a or b for a, b in re.findall(r"'([^']*)'|(\S+)", wanted)]
    return SiteResult(0, b"".join(p.encode() + b"\0" for p in paths), "")


def ctx(site, tmp_path):
    return SimpleNamespace(site=site, settings_file=str(tmp_path / "none.yml"))


def run_listing(site, tmp_path):
    return handlers.listing(rules.clean_environment(CE), WORK + "/x", ctx(site, tmp_path))


def run_readfile(site, tmp_path):
    return readfile.run_read({"args": {"ce": CE, "run": "myrun", "path": "out.txt"}}, ctx(site, tmp_path))


def run_readlog(site, tmp_path):
    return readlog.run_read({"args": {"ce": CE, "workdir": TASK, "file": ".command.err"}}, ctx(site, tmp_path))


ENTRIES = {"listing": run_listing, "readfile": run_readfile, "readlog": run_readlog}
ALL = pytest.mark.parametrize("entry", list(ENTRIES))


def expect_down(entry, site, tmp_path):
    kind, body = ENTRIES[entry](site, tmp_path)
    assert kind == "error" and body["error"] == "site_unreachable", (kind, body)
    return body["message"]


@ALL
def test_tc001_to_003_rc255_is_site_unreachable_with_the_login_line(entry, tmp_path):
    # TC-001, TC-002, TC-003
    msg = expect_down(entry, FakeSite(down()), tmp_path)
    assert RELOGIN in msg and OPEN_CMD in msg


@ALL
@pytest.mark.parametrize("res", [SiteResult(124, b"", "", True), SiteResult(1, b"", "on_site: needs-human reason=no-master\n")])
def test_tc004_005_timeout_and_needs_human(entry, res, tmp_path):
    # TC-004, TC-005
    expect_down(entry, FakeSite(lambda a: res), tmp_path)


@ALL
def test_tc006_the_message_is_not_a_path_refusal(entry, tmp_path):
    # TC-006
    msg = expect_down(entry, FakeSite(down()), tmp_path)
    assert OPEN_CMD in msg
    for bad in ("路徑不正確", "could not say where the path leads", "站台無法確認路徑的真實位置"):
        assert bad not in msg


@ALL
def test_tc007_same_sentence_as_a_later_step_going_down(entry, tmp_path):
    # TC-007
    first = expect_down(entry, FakeSite(down()), tmp_path)
    later = expect_down(entry, FakeSite(echo, after=lambda a: SiteResult(255, b"", "x")), tmp_path)
    assert first == later


@ALL
def test_tc008_reach_ok_gives_the_plain_site_sentence(entry, tmp_path):
    # TC-008
    msg = expect_down(entry, FakeSite(down(), reach_ok=True), tmp_path)
    assert msg == "The site could not do this (exit code 255)."


@ALL
def test_tc009_and_018_only_realpath_and_check_reach_are_called(entry, tmp_path):
    # TC-009, TC-018
    site = FakeSite(down())
    expect_down(entry, site, tmp_path)
    assert [c[0].split()[0] for c in site.calls] == ["realpath", "--check-reach"], site.calls
    assert not any("ControlMaster" in " ".join(c) or "-O" in c for c in site.calls)


@ALL
@pytest.mark.parametrize("how", ["rc1", "nonul", "count"])
def test_tc010_011_012_other_failures_stay_the_v3_refusal(entry, how, tmp_path):
    # TC-010, TC-011, TC-012
    res = {"rc1": SiteResult(1, b"", "No such file"), "nonul": SiteResult(0, b"/a", ""),
           "count": SiteResult(0, b"/a\0/b\0/c\0/d\0", "")}[how]
    with pytest.raises(rules.Refusal) as e:
        ENTRIES[entry](FakeSite(lambda a: res), tmp_path)
    assert str(e.value) == REFUSAL[entry]


def test_tc013_real_path_keeps_its_shape():
    # TC-013
    ok = FakeSite(lambda a: SiteResult(0, b"/r/p\0/r\0", ""))
    assert handlers._real_path(ok, "/r/p", ["/r"]) == ("/r/p", ["/r"])
    assert handlers._real_path(FakeSite(lambda a: SiteResult(1, b"", "No such file")), "/r/p", ["/r"]) is None
    assert handlers._real_path(FakeSite(down()), "/r/p", ["/r"]) is None


@ALL
def test_tc016_017_plain_words_and_no_secret(entry, tmp_path):
    # TC-016, TC-017
    site = FakeSite(down(err="Permission denied password=%s" % SECRET), reach_err=NO_MASTER)
    msg = expect_down(entry, site, tmp_path)
    assert "Traceback" not in msg and "SELECT" not in msg.upper() and SECRET not in msg


def test_tc019_error_codes_are_the_v3_set():
    # TC-019
    root = Path(handlers.__file__).parent
    codes = set()
    for f in root.glob("*.py"):
        codes |= set(re.findall(r'_failure\(\s*"([a-z_]+)"', f.read_text(encoding="utf-8")))
    v3 = {"changed", "not_a_directory", "not_a_file", "not_found", "not_on_site", "permission_denied", "site_unreachable", "too_large"}
    assert codes == v3, codes ^ v3
