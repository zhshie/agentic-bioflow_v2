# Nothing existing: the other doc tests are shell scripts that check one fixed file; this one checks docs/ONBOARDING.md against the real parsers and can be pointed at a mutated copy.
"""docs/ONBOARDING.md cannot drift from the code. Test cases TC-001 ... TC-059 of the account-onboarding test case file are named in
the comments (T1 ... T13 are the plan's numbers). Reads files only; no network, no program is started."""
import re
from pathlib import Path

from helpers import REPO_ROOT

DOC = REPO_ROOT / "docs" / "ONBOARDING.md"
CLI = (REPO_ROOT / "platform" / "abf_platform" / "cli.py").read_text(encoding="utf-8")
STATION_CLI = (REPO_ROOT / "platform" / "abf_station" / "cli.py").read_text(encoding="utf-8")
MCP = (REPO_ROOT / "platform" / "abf_platform" / "mcp_server.py").read_text(encoding="utf-8")
CJK = re.compile(r"[一-鿿]")
GROUPS = {"user": "usub", "pat": "psub", "agent-token": "asub", "ce": "csub"}


def text(path=DOC):
    return Path(path).read_text(encoding="utf-8")


def section(doc, n):
    return re.split(r"(?m)^## ", doc)[n]


def fences(doc):
    return re.findall(r"```[a-z]*\n(.*?)```", doc, re.S)


def check_subcommands(doc):
    """T2: abf-platform commands of the doc that cli.py does not define."""
    top = set(re.findall(r'sub\.add_parser\("([^"]+)"', CLI))
    bad = []
    for w1, w2 in re.findall(r"abf-platform ([a-z][a-z-]*)(?: ([a-z][a-z-]*))?", doc):
        if w1 not in top:
            bad.append(w1)
        elif w1 in GROUPS and w2:
            if not re.search(r'%s\.add_parser\("%s"' % (GROUPS[w1], re.escape(w2)), CLI):
                bad.append("%s %s" % (w1, w2))
    return bad


def check_flags(doc):
    """T3: the flags of the doc that are not an add_argument of cli.py (whole words only)."""
    known = set(re.findall(r'add_argument\("(--[a-z-]+)"', CLI))
    used = set(re.findall(r"--(?:lab|user|owner|agent|cloud-cap[a-z-]*)(?![A-Za-z0-9-])", doc))
    return sorted(f for f in used if f not in known)


def test_tc001_five_headings():
    # TC-001 (T1)
    heads = re.findall(r"(?m)^## (.*)$", text())
    keys = ["Who does what", "The operator opens the account", "The welcome message", "The colleague connects",
            "A colleague on NCHC runs a station agent"]
    assert len(heads) == 5
    for i, (h, k) in enumerate(zip(heads, keys), 1):
        assert h.startswith("%d." % i) and k in h


def test_tc002_each_section_opens_with_chinese():
    # TC-002
    for i in range(1, 6):
        first = section(text(), i).split("\n\n")[1].strip()
        assert CJK.search(first), "section %d first paragraph has no Chinese" % i


def test_tc003_roles_and_table():
    # TC-003
    s = section(text(), 1)
    assert "operator" in s and "colleague" in s
    assert len(re.findall(r"(?m)^\|.*\|$", s)) >= 3


def test_tc004_cloud_users_install_nothing():
    # TC-004 (T8)
    d = text()
    assert "Google Batch" in d and ("no station agent" in d or "install nothing" in d)


def test_tc005_nchc_row_on_own_computer():
    # TC-005
    rows = [r for r in section(text(), 1).splitlines() if r.startswith("|")]
    nchc = [r for r in rows if "NCHC" in r and "station agent" in r]
    assert nchc and ("WSL" in nchc[0] or "Linux" in nchc[0])
    assert "platform host" not in nchc[0]


def test_tc006_order_of_operator_steps():
    # TC-006
    s = section(text(), 2)
    pos = [s.find(k) for k in ("user add", "user passwd", "pat new", "agent-token new", "ce create", "pat list")]
    assert all(p >= 0 for p in pos) and pos == sorted(pos)


def test_tc007_user_add_line():
    # TC-007
    s = section(text(), 2)
    assert re.search(r"(?m)^abf-platform user add <name> --lab <lab> --cloud-cap-usd <N>\s*$", s)


def test_tc008_no_cap_cannot_send_to_cloud():
    # TC-008
    s = section(text(), 2)
    assert "abf-platform user cloud-cap <name> <N>" in s and "cannot send to the cloud" in s


def test_tc009_usd_range_and_nchc():
    # TC-009
    s = section(text(), 2)
    assert "1,000,000" in s and re.search(r"NCHC[^\n]*(no|not)[^\n]*(cap|limit)", s)


def test_tc010_passwd_by_the_person_twice():
    # TC-010
    s = section(text(), 2)
    assert re.search(r"(?m)^abf-platform user passwd <name>\s*$", s)
    assert "twice" in s and "real terminal" in s and re.search(r"no (flag|option)", s)
    assert not re.search(r"user passwd[^\n]*--(password|file)", s)


def test_tc011_two_ways_to_log_in():
    # TC-011
    s = section(text(), 2)
    assert "Claude Desktop" in s and "OAuth" in s and "abf-platform pat new --user <name>" in s


def test_tc012_pat_shown_once():
    # TC-012
    assert "once" in section(text(), 2)


def test_tc013_pat_not_in_chat():
    # TC-013
    s = section(text(), 2)
    assert "chat" in s and "terminal" in s


def test_tc014_nchc_commands_one_per_line():
    # TC-014
    s = section(text(), 2)
    assert re.search(r"(?m)^abf-platform agent-token new <agent-name> --user <name>\s*$", s)
    assert re.search(r"(?m)^abf-platform ce create --owner <name> --agent <agent-name>", s)


def test_tc015_ce_fields_not_copied():
    # TC-015
    s = section(text(), 2)
    assert "docs/PLATFORM.md" in s and "| Key | Rule |" not in s


def test_tc016_verify():
    # TC-016
    s = section(text(), 2)
    assert "docs/INSTALL.md" in s and "abf-platform pat list" in s and "never" in s


def test_tc018_one_command_per_line_and_no_shortcuts():
    # TC-018
    d = text()
    assert "略" not in d and "同上" not in d
    for block in fences(d):
        for line in block.splitlines():
            assert len(re.findall(r"abf-(?:platform|station) ", line)) <= 1, line
            assert not ("abf-" in line and ("&&" in line or ";" in line)), line


def test_tc019_welcome_block():
    # TC-019 (T6)
    f = fences(section(text(), 3))
    assert len(f) == 1
    for p in ("<platform-URL>", "<name>", "<lab>", "<operator>"):
        assert p in f[0]


def test_tc020_welcome_points_to_sections():
    # TC-020 (T6)
    b = fences(section(text(), 3))[0]
    for n in (2, 4, 5):
        assert re.search(r"(§|section )%d" % n, b)
    assert "docs/INSTALL.md" in b


def test_tc021_welcome_content():
    # TC-021
    b = fences(section(text(), 3))[0]
    assert "PAT" in b and "password" in b and "NCHC" in b


def test_tc022_welcome_cap_in_dollars():
    # TC-022
    b = fences(section(text(), 3))[0]
    assert re.search(r"US\$|US dollars", b) and "cap" in b.lower()


def test_tc024_project_number_placeholder():
    # TC-024
    assert "<your NSTC project>" in fences(section(text(), 3))[0]


def test_tc025_install_pointer_no_copy():
    # TC-025
    s = section(text(), 4)
    assert "docs/INSTALL.md" in s and all(a in s for a in ("Claude Code", "Claude Desktop", "Codex"))
    assert "claude mcp add" not in text()


def test_tc026_list_runs():
    # TC-026
    assert "list_runs" in section(text(), 4) and 'name="list_runs"' in MCP
    assert "list_runs" in (REPO_ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")


def test_tc027_tc028_prerequisites():
    # TC-027, TC-028
    s = section(text(), 5)
    head = s[:s.find("```")]
    assert "account" in head and "project" in head and "WSL" in head
    assert "Git Bash" in head and re.search(r"refus|reject", head)


def test_tc029_tc030_order_of_steps():
    # TC-029, TC-030 (T7)
    s = section(text(), 5)
    pos = [s.find(m) for m in ("WSL's own home", "chmod 600", "--check-reach", "abf-station run")]
    assert all(p >= 0 for p in pos) and pos == sorted(pos)
    assert "/mnt/c" in s or "Windows drive" in s


def test_tc031_station_run_flags():
    # TC-031 (T4)
    m = re.search(r"(?m)^abf-station run (.*)$", section(text(), 5))
    assert m
    run_flags = re.findall(r'r\.add_argument\("(--[a-z-]+)"', STATION_CLI)
    for f in ("--platform", "--token-file", "--deployment"):
        assert f in m.group(1) and f in run_flags


def test_tc032_https_rule():
    # TC-032 (T7)
    s = section(text(), 5)
    assert "https" in s and "localhost" in s and "127.0.0.1" in s


def test_tc033_list_agents():
    # TC-033 (T7)
    assert "list_agents" in section(text(), 5) and 'name="list_agents"' in MCP


def test_tc034_error_table_not_copied():
    # TC-034
    s = section(text(), 5)
    assert "What it tells you" in s and "docs/PLATFORM.md" in s
    assert not re.search(r"(?m)^\|.*Meaning", s)


def test_tc035_subcommands_exist():
    # TC-035 (T2)
    assert check_subcommands(text()) == []


def test_tc036_flags_exist():
    # TC-036 (T3)
    d = text()
    for f in ("--lab", "--cloud-cap-usd", "--user", "--owner", "--agent"):
        assert re.search(re.escape(f) + r"(?![A-Za-z0-9-])", d), f
    assert check_flags(d) == []


def test_tc037_station_subcommands_exist():
    # TC-037 (T4)
    top = set(re.findall(r'sub\.add_parser\("([^"]+)"', STATION_CLI))
    used = re.findall(r"abf-station ([a-z][a-z-]*)", text())
    assert used and all(u in top for u in used)


def test_tc038_paths_exist():
    # TC-038 (T5)
    paths = re.findall(r"`((?:docs|scripts|platform|deploy)/[^`\s]+\.[A-Za-z0-9]+)`", text())
    assert paths
    assert [p for p in paths if not (REPO_ROOT / p).exists()] == []


def test_tc039_tc040_dollars_only():
    # TC-039, TC-040 (T9)
    d = text()
    assert not any(w in d for w in ("NT$", "台幣", "匯率"))
    assert "US$" in d or "US dollars" in d


def test_tc041_tc023_no_secrets():
    # TC-041, TC-023 (T10)
    d = text()
    assert not re.search(r"abf_pat_[A-Za-z0-9]{8,}", d)
    assert not re.search(r"mst1\d{5}", d)
    assert not re.search(r"u9\d{7}", d)


def test_tc042_mutation_subcommand_caught():
    # TC-042 (T12)
    d = text()
    assert "user cloud-cap" in d
    assert check_subcommands(d.replace("user cloud-cap", "user cloudcap")) == ["user cloudcap"]


def test_tc043_mutation_flag_caught():
    # TC-043 (T12)
    d = text()
    assert check_flags(d.replace("--cloud-cap-usd", "--cloud-cap")) == ["--cloud-cap"]


def test_tc045_tc046_readme_pointer():
    # TC-045, TC-046 (T11)
    lines = text(REPO_ROOT / "README.md").splitlines()
    i = [n for n, l in enumerate(lines) if "docs/ONBOARDING.md" in l]
    assert len(i) == 1
    j = [n for n, l in enumerate(lines) if "docs/PITFALLS.md" in l][0]
    assert i[0] < j and lines[i[0] - 1] == "" and lines[i[0] + 1] == ""


def test_tc053_readme_addition_has_no_secrets():
    # TC-053
    line = [l for l in text(REPO_ROOT / "README.md").splitlines() if "docs/ONBOARDING.md" in l][0]
    assert not re.search(r"abf_pat_|mst1\d{5}|u9\d{7}", line)
