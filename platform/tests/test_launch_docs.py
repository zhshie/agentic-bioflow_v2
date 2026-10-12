# Nothing existing: checks that the documents of feature 007b say what the code really does and name the limits it really has; no tool compares a document with a constant.
"""docs/PLATFORM.md section 9, SEQERA_PARITY.md, PITFALLS.md, ROADMAP.md, TESTING.md (feature 007b, TC-058)."""
import re

from helpers import REPO_ROOT

DOCS = REPO_ROOT / "docs"


def read(name):
    return (DOCS / name).read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


def section9():
    text = read("PLATFORM.md")
    assert "## 9. Launch and cancel" in text
    body = text[text.index("## 9. Launch and cancel"):]
    return flat(body[:body.index("\n## Where the files are")])


def test_tc058_the_platform_guide_section_9_covers_every_part_of_launch_and_cancel():
    s = section9()
    for needle in ("abf-platform launch", "abf-platform cancel", "abf-platform launches", "abf-platform fetch-records",
                   "abf-station unforward", "X-ABF-Platform", "tower.token", "forward_port", "ABF_PLATFORM_DEADLINE_LAUNCH",
                   "ABF_PLATFORM_LAUNCH_GRACE", "ABF_STATION_MIN_REMAINING", "slurm_account", "storage_root", "nf_relay.py"):
        assert needle in s, needle
    assert re.search(r"y or Y", s) and re.search(r"nothing (else )?answers|no flag|no environment variable", s, re.I)
    assert re.search(r"8 hours|eight hours|8-hour", s)
    assert re.search(r"same machine", s) and re.search(r"loopback", s)
    assert "fetch-records" in s and "paths and parameters" in s and re.search(r"(logs|records)[^.]*(sent|leave|go|travel|stored)[^.]*platform", s)
    assert re.search(r"revoked[^.]*complete", s) and re.search(r"14 days", s)
    assert re.search(r"cancel does not revoke", s)
    assert re.search(r"(can|could) (fake|forge)[^.]*(y|answer)", s) and re.search(r"platform\.db", s) and re.search(r"pty|pseudo-terminal", s)
    assert re.search(r"approval|ask rule|permission", s) and "abf-platform launch|cancel" in s.replace("\\|", "|")


def test_tc058_the_guide_says_what_the_station_now_does_and_still_does_not():
    text = flat(read("PLATFORM.md"))
    assert "Launching, with a confirmation step, is a later feature (007b)" not in text
    assert re.search(r"never (deletes|removes)|deletes nothing", text, re.I)


def test_tc058_the_example_commands_of_section_9_parse():
    import shlex
    from abf_platform import cli
    text = read("PLATFORM.md")
    body = text[text.index("## 9. Launch and cancel"):text.index("\n## Where the files are")]
    parser = cli.build_parser()
    checked = 0
    for ln in body.splitlines():
        m = re.match(r"^\s*abf-platform ((?:launch|cancel|launches|fetch-records|rebuild)\b[^#<>]*?)\s*(#.*)?$", ln)
        if not m:
            continue
        argv = shlex.split(m.group(1))
        try:
            parser.parse_args(argv)
        except SystemExit as e:
            raise AssertionError("section 9 shows a command the parser rejects: %s" % ln) from e
        checked += 1
    assert checked >= 4


def test_tc058_the_parity_table_has_launch_progress_and_cancel_rows_and_lists_what_is_not_built():
    par = flat(read("SEQERA_PARITY.md"))
    i = par.index("## L. ")
    sec = par[i:]
    for row in ("Launch", "Live progress", "Cancel"):
        assert re.search(r"\| %s[^|]*\|[^|]*\b(Have|Partly have)\b" % row, sec), row
    for missing in ("list of every task", "CPU and memory", "logs and reports", "queued state"):
        assert missing in sec, missing
    assert "A. Launchpad and pipelines (16 items)" in par and "F. Compute environments (13 items)" in par


def test_tc058_pitfalls_gets_the_two_new_entries():
    p = flat(read("PITFALLS.md"))
    assert re.search(r"GatewayPorts off on NCHC: reverse forward is loopback-only \(measured 2026-10-11\)", p)
    assert re.search(r"Seqera launcher scripts hold the token in a 755 file", p)


def test_tc058_the_roadmap_notes_007b_and_does_not_move_the_waiting_principle_into_the_constitution():
    rm = flat(read("ROADMAP.md"))
    assert "007b is built" in rm and "TC-047" in rm
    assert "Every platform write tool (launch, delete, clear `work/`) refuses without the user's confirmation step" in rm
    assert re.search(r"007b builds it for launch and cancel", rm)


def test_tc058_testing_md_has_the_manual_steps_of_the_real_cluster_cases():
    t = flat(read("TESTING.md"))
    for tc in ("TC-047", "TC-048", "TC-049", "TC-050", "TC-053", "TC-060", "TC-076", "TC-077"):
        assert tc in t, tc
    assert "abf-station unforward" in t and "ss -ltn" in t and "squeue" in t and "git diff" in t
