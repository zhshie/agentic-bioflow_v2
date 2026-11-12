# Nothing existing: test_launch_docs.py and test_cloud_upload_docs.py pin the sentences of other features; nothing pins the guide of the two commands that run on a user's own computer.
"""cli-fetch-publish-figure, slice 1, documents (TC-074, TC-075, TC-076): the guide says what the commands do, where the settings file is and what the exit codes
mean, the operations guide says how a person gets a token and the address and how to install the package, and the manual steps are written so that they can be followed."""
import re
import shlex

from helpers import REPO_ROOT

DOCS = REPO_ROOT / "docs"


def read(name):
    return (DOCS / name).read_text(encoding="utf-8")


def section(text, heading):
    assert heading in text, heading
    body = text[text.index(heading):]
    nxt = re.search(r"\n#{1,2} ", body[len(heading):])
    return body if not nxt else body[:len(heading) + nxt.start()]


def flat(text):
    return re.sub(r"\s+", " ", text)


PLATFORM_HEADING = "## Commands on your own computer (cli-fetch-publish-figure)"
FAKE = re.compile(r"abf_pat_[A-Za-z0-9_-]{20,}")


def test_tc074_the_platform_guide_describes_the_two_commands_the_settings_file_and_the_exit_codes():
    # TC-074
    s = flat(section(read("PLATFORM.md"), PLATFORM_HEADING))
    for needle in ("abf-platform studio-connect", "abf-platform fetch-results", "~/.abf/studio.json", "ABF_STUDIO_CONFIG", "ABF_PAT", "chmod 600",
                   "--token-stdin", "--no-check", "--dir", "~/abf-results/<run>", "fetch-records", "pat new", "run_outputs", "read_run_file"):
        assert needle in s, needle
    assert '"server"' in s and '"token"' in s
    for code in ("0", "1", "2", "3"):
        assert re.search(r"(?<![0-9])%s (means|is|:|=)" % code, s) or re.search(r"\bexit %s\b|\| %s \|" % (code, code), s), code
    assert re.search(r"not (a )?(sent|fetched)[^.]*(html|binary)|(html|binary)[^.]*not (sent|fetched)", s, re.I) and "25 MB" in s and "100 MB" in s
    assert re.search(r"cloud[- ]sync", s, re.I) and re.search(r"never (printed|logged)|is not printed", s)
    assert "publish-figure" not in s      # slice 2
    assert not FAKE.search(s)


def test_tc074_the_example_lines_parse_and_are_not_taken_for_launch_examples():
    # TC-074
    from abf_platform import cli
    body = section(read("PLATFORM.md"), PLATFORM_HEADING)
    parser = cli.build_parser()
    checked = 0
    for ln in body.splitlines():
        m = re.match(r"^\s*(?:\$ )?abf-platform ((?:studio-connect|fetch-results)\b[^#<>|]*?)\s*(#.*)?$", ln)
        if not m:
            continue
        try:
            parser.parse_args(shlex.split(m.group(1)))
        except SystemExit as e:
            raise AssertionError("the guide shows a command the parser rejects: %s" % ln) from e
        checked += 1
    assert checked >= 3
    # the scan of test_launch_docs only takes launch, cancel, launches, fetch-records and rebuild lines: none of those may stand in this section
    assert not re.search(r"(?m)^\s*abf-platform (launch|cancel|launches|fetch-records|rebuild)\b", body)


def test_tc074_the_changelog_has_an_entry():
    # TC-074
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    head = text.split("\n## ", 2)[1] if "\n## " in text else text
    assert "studio-connect" in head and "fetch-results" in head and "cli-fetch-publish-figure" in head
    assert "publish-figure" not in head.split("cli-fetch-publish-figure", 1)[1].split("\n- ", 1)[0] or "slice 2" in head


def test_tc075_the_operations_guide_says_how_to_get_a_token_the_address_and_the_package():
    # TC-075
    text = read("OPERATIONS.md")
    funnel = text.index("tailscale funnel --bg 8080")
    after = flat(text[funnel:])
    assert "### Giving a person the commands for their own computer" in text[funnel:]
    s = flat(section(text[funnel:], "### Giving a person the commands for their own computer"))
    for needle in ("abf-platform user add", "abf-platform pat new --user", "pat revoke", "ABF_PUBLIC_URL", "tailscale funnel status", "pip install", "platform/",
                   "studio-connect --server https://"):
        assert needle in s, needle
    assert re.search(r"private", s, re.I) and re.search(r"access", s, re.I) and re.search(r"cloud[- ]sync", s, re.I)
    assert re.search(r"Windows", s) and not FAKE.search(s)
    assert after.index("Giving a person the commands") > 0


def test_tc076_the_manual_steps_are_written_and_the_ledger_fields_are_listed():
    # TC-076
    s = flat(section(read("TESTING.md"), "## cli-fetch-publish-figure, slice 1 (studio-connect, fetch-results): the maintainer checks on his own computer"))
    for needle in ("studio-connect --server https://", "fetch-results", "RStudio", "Console", "wrong token", "network", "Funnel",
                   "stage=downstream", "1440", "390", "axe", "UNVERIFIED",
                   "git diff --stat", "MAX_TOTAL_BYTES", "mcp", "ls -l"):
        assert needle in s, needle
    for tc in ("TC-039", "TC-046", "TC-047", "TC-055"):
        assert tc in s, tc
    assert re.search(r"not (on )?the (desktop|platform machine)|another computer|second computer", s, re.I)
    assert not FAKE.search(s)
