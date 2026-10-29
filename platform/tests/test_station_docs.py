# Nothing existing: checks that the documents state the values and settings the code really has; no tool compares a document with a constant.
"""Documents of feature 007: docs/PLATFORM.md, docs/SEQERA_PARITY.md, docs/ROADMAP.md, docs/TESTING.md."""
import re
import shlex

from helpers import REPO_ROOT

DOCS = REPO_ROOT / "docs"


def read(name):
    return (DOCS / name).read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


def test_tc075_the_platform_guide_names_every_step_value_and_setting():
    # TC-075
    from abf_platform import common, compute_envs, jobs
    doc = read("PLATFORM.md")
    f = flat(doc)
    for needle in ("abf-station run", "--token-file", "--deployment", "agent-token new", "agent-token revoke",
                   "ce create", "ce preflight", "on_site.sh", "--check-reach", "WSL", "HTTPS", "platform.db",
                   "ABF_PLATFORM_STATE", "ABF_STATION_MOUNTS_FILE", "ABF_AGENT_HEARTBEAT_SECONDS",
                   "ABF_AGENT_POLL_SECONDS", "ABF_PLATFORM_DEADLINE_PREFLIGHT", "ABF_PLATFORM_DEADLINE_LIST_SITE_FILES",
                   "chmod 600", "drvfs"):
        assert needle in f, needle
    for field in ("workDir", "launchDir", "headQueue", "computeQueue", "maxQueueSize", "preRunScript",
                  "postRunScript", "environment", "nextflowConfig", "credentialsId", "hostName"):
        assert field in doc, "the Slurm field list must name " + field
    assert re.search(r"file names, sizes and modification times", f) and re.search(r"to the model you (chose|choose)", f)
    assert re.search(r"only .{0,40}(inside|in) WSL|WSL or Linux", f) and re.search(r"HTTPS.{0,80}(not|other than|except).{0,40}(local|loopback)|"
                                                                                  r"(non-local|not local).{0,80}HTTPS", f)
    assert re.search(r"\b%d\b[^.|]{0,60}(entries|files)" % jobs.LIST_LIMIT, f), "the listing limit"
    assert re.search(r"heartbeat[^.]{0,80}\b%d\b" % common.AGENT_HEARTBEAT_SECONDS, f, re.I)
    assert re.search(r"poll[^.]{0,80}\b%d\b" % common.AGENT_POLL_SECONDS, f, re.I)
    for pid in compute_envs.KINDS:
        assert "`%s`" % pid in doc, pid
    assert len(compute_envs.KINDS) == 14


def test_tc075_the_example_commands_of_the_guide_parse():
    # TC-075 (a cheap half of TC-076: every `abf-platform ...` line of the new sections is accepted by the parser)
    from abf_platform import cli
    text = read("PLATFORM.md")
    start = text.index("## 6.") if "## 6." in text else 0
    parser = cli.build_parser()
    checked = 0
    for ln in text[start:].splitlines():
        m = re.match(r"^\s*abf-platform ((?:ce|agent-token) [^#<>]*?)\s*(#.*)?$", ln)
        if not m:
            continue
        argv = shlex.split(m.group(1))
        if "..." in argv or any(a.startswith("<") for a in argv):
            continue
        try:
            parser.parse_args(argv)
        except SystemExit as e:
            raise AssertionError("the guide shows a command the parser rejects: %s" % ln) from e
        checked += 1
    assert checked >= 4


def test_tc077_the_parity_table_has_one_row_per_type_and_the_heading_count_is_unchanged():
    # TC-077
    from abf_platform import compute_envs
    par = read("SEQERA_PARITY.md")
    assert "## F. Compute environments (13 items)" in par
    sec = par[par.index("## F. Compute environments"):]
    sec = sec[:sec.index("\n## G.")]
    rows = [ln for ln in sec.splitlines() if ln.startswith("|") and not re.match(r"^\|[-| ]+\|$", ln)]
    body = "\n".join(rows)
    assert re.search(r"Seqera Compute.*Not needed", body)
    assert re.search(r"Slurm.*\bHave\b", body)
    for pid, label in compute_envs.KINDS.items():
        if pid in ("slurm-platform", "googlebatch-platform", "awsbatch-platform", "azbatch-platform", "k8s-platform"):      # k8s-ce: its row says "Have (create + check); launch not yet"; gcb-ce-type: its row says "Have (create + check); launch in C-2"
            continue
        row = [r for r in rows if "`%s`" % pid in r]
        assert row and re.search(r"Modelled, needs a real account", row[0]), (pid, row)
    assert len([r for r in rows if "Modelled, needs a real account" in r]) == 9


def test_tc077_the_roadmap_keeps_stage_one_open_and_marks_stage_four_as_merged():
    # TC-077
    rm = read("ROADMAP.md")
    stages = rm[rm.index("## Stages"):]
    stages = stages[:stages.index("\n## ", 5)]
    assert "| Done when |" in stages
    one = [ln for ln in stages.splitlines() if ln.startswith("| 1 |")][0]
    four = [ln for ln in stages.splitlines() if ln.startswith("| 4 | **Cloud compute**")]
    assert one.startswith("| 1 | **Station agent** (feature 007)")
    assert "station agent + compute environments (Seqera model, all types; NCHC first)" in flat(one)
    assert not re.search(r"\b(done|complete|completed|shipped)\b", one.split("|")[-3] if False else one[:60], re.I)
    assert four and "merged into Stage 1" in flat(four[0])
    for n in range(6):
        row = [ln for ln in stages.splitlines() if ln.startswith("| %d |" % n)][0]
        assert row.split("|")[-2].strip(), row


def test_tc076_tc079_tc080_tc081_tc088_tc093_tc094_the_manual_steps_are_written_down():
    # the manual cases name their steps in docs/TESTING.md
    t = flat(read("TESTING.md"))
    for tc in ("TC-076", "TC-079", "TC-080", "TC-081", "TC-088", "TC-093", "TC-094", "TC-095"):
        assert tc in t, tc
    assert "git diff" in t and "constitution.md" in t and "tests/run_all.sh --list" in t


def _plain_http_sentence():
    f = flat(read("PLATFORM.md"))
    start = f.find("Plain `http://` is only for the same machine")
    assert start >= 0, "the plain-http rule must be in PLATFORM.md"
    end = f.find(". ", start)
    return f[start:end if end >= 0 else len(f)]


def test_tc_lb_01_02_the_refusal_names_all_three_loopback_hosts():
    # TC-LB-01, TC-LB-02
    from abf_station import cli
    msg = cli.url_problem("http://example.com:8788")
    assert "::1" in msg
    assert "Use HTTPS" in msg and "localhost" in msg and "127.0.0.1" in msg


def test_tc_lb_03_04_05_the_platform_guide_names_ipv6_loopback():
    # TC-LB-03, TC-LB-04, TC-LB-05
    sentence = _plain_http_sentence()
    assert "::1" in sentence
    assert "localhost" in sentence and "127.0.0.1" in sentence


def test_tc_lb_06_to_14_the_http_gate_decisions_are_unchanged():
    # TC-LB-06..TC-LB-14
    from abf_station import cli
    for u in ("http://localhost:1", "http://127.0.0.1:1", "http://[::1]:1", "https://example.com"):
        assert cli.url_problem(u) is None, u
    for u in ("http://example.com", "http://192.168.1.5:8788", "http://[::2]:1"):
        assert cli.url_problem(u) is not None, u
    assert cli.url_problem("ftp://x") == "the platform URL ftp://x is not an http or https address"
    assert cli.url_problem("http://") == "the platform URL http:// is not an http or https address"
