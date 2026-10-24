# Nothing existing: tests of the words about a resume that may carry edits (resume-edit-params-c); the sentences are ours.
"""resume-edit-params-c: the MCP opening sentence, the two skills, ADR 0009, the Seqera parity table and the changelog say what b does.
Test cases are named in the comments (TC-001 ...), see specs/resume-edit-params-c/test-case.md."""
import re

from helpers import REPO_ROOT

NEW = "A failed run is relaunched with its name alone; a resume may also carry changed parameters and extra resource settings."
OLD = "resumed or relaunched with its name alone"
KEYS = ("cpus", "memory", "time", "disk", "maxRetries", "errorStrategy")
FLAGS = ("--param", "--params-file", "--config-file")
AMEND = ("（Amended by the resume-edit-params task, 2026-10: a resume may change some parameters and add resource settings and stays "
         "the same analysis; changing the samples, pipeline, revision or compute environment still starts a new analysis.）")
ROW = "| Resume | Have, with edit | parameters and a restricted resource config can be changed on resume (CLI, MCP); compute-environment switch and web form: not done |"


def _skills():
    from abf_platform import guidance
    return {n: guidance.read_skill(n) for n in ("operational", "runs")}


def _flat(text):
    return re.sub(r"\s+", " ", text)


def test_the_mcp_instructions_say_a_resume_may_carry_edits_and_a_relaunch_takes_the_name_alone():
    # TC-001 TC-002 TC-003 TC-004 TC-050
    from abf_platform import guidance
    text = guidance.routing_instructions()
    assert NEW in text
    assert OLD not in text
    assert len(text.encode("utf-8")) <= guidance.MAX_BYTES
    assert guidance.MAX_BYTES == 2048
    for s in ("Seven tools of this server are read-only.",
              "The tool forget only asks too: it deletes nothing until the person says yes in their own client's form.",
              "The complete steps of each command are the MCP prompt of the same name (setup, launch, runs, downstream, finish).",
              "(in the terminal, abf-platform launch, cancel, resume and relaunch ask the same way)",
              "does not start anything until the person says yes", "you cannot say it for them"):
        assert s in text, s


def test_both_skills_say_what_a_resume_may_change_and_what_it_may_not():
    # TC-010 TC-011 TC-012 TC-013 TC-014 TC-015 TC-016 TC-017 TC-051
    from abf_station.launch import EXTRA_KEYS
    assert tuple(EXTRA_KEYS) == KEYS
    for name, text in _skills().items():
        flat = _flat(text)
        assert "`params`" in text and "`extra_config`" in text, name
        for k in KEYS:
            assert k in text, (name, k)
        for f in FLAGS:
            assert f in text, (name, f)
        assert "new `launch`" in text, name
        assert re.search(r"`relaunch`[^.]*(name|cannot change parameters)", flat), name
        assert any("`resume`" in ln and "`relaunch`" in ln for ln in text.splitlines()), name
    op = _flat(_skills()["operational"])
    assert "only the keys" in op and "cannot delete" in op
    assert "run again" in op and "reused" in op
    assert "same folder" in op
    assert "Each time asks the person and waits for their yes" in op
    for f in ("samplesheet.csv", "params.yaml", "nextflow.config", "head.sh"):
        assert f not in op


def test_the_cli_resume_has_the_three_flags_the_skills_name():
    # TC-012
    src = (REPO_ROOT / "platform" / "abf_launch" / "cli.py").read_text(encoding="utf-8")
    for f in FLAGS:
        assert 'add_argument("%s"' % f in src, f


def test_the_runs_skill_no_longer_says_a_resume_cannot_change_parameters():
    # TC-018 TC-019 TC-020 TC-022
    flat = _flat(_skills()["runs"])
    assert "`relaunch` and `resume` cannot change parameters" not in flat
    assert "The samples and parameters are those of the first launch; changing them is a new `launch`" not in flat
    assert "`relaunch` cannot change parameters; a `resume` may carry the corrected `params`" in flat
    assert "same job number" in flat
    assert "only for the latest one" in flat and "names the one that exists" in flat
    for name, text in _skills().items():
        for m in re.finditer(r"[^.]*(composed|Google Batch)[^.]*\.", _flat(text)):
            assert "may change" not in m.group(0) and "can change param" not in m.group(0), (name, m.group(0))


def test_adr_0009_has_the_amendment_line_verbatim_and_nothing_else_changed():
    # TC-030 TC-031
    lines = (REPO_ROOT / "docs/adr/0009-web-layout-three-panes.md").read_text(encoding="utf-8").splitlines()
    assert lines.count(AMEND) == 1
    i = lines.index(AMEND)
    assert lines[i - 1].endswith("analysis; changing the samples or the parameters starts a new analysis.")
    assert lines[i + 1].startswith("3. **The board moves by itself**")


def test_the_parity_row_for_resume_says_have_with_edit():
    # TC-032 TC-033
    lines = (REPO_ROOT / "docs/SEQERA_PARITY.md").read_text(encoding="utf-8").splitlines()
    assert lines.count(ROW) == 1
    assert "| Resume | Have | |" not in lines
    assert "| Relaunch | Have | |" in lines


def test_the_parity_section_counts_did_not_change():
    # TC-034
    text = (REPO_ROOT / "docs/SEQERA_PARITY.md").read_text(encoding="utf-8")
    assert "the original count was 84" in text and "lists 83 named items" in text
    assert "A 16, B 11, C 1, D 5, E 9, F 13, G 2, H 7, I 3, J 9, K 7" in text
    heads = re.findall(r"^## ([A-K])\..*\((\d+) (?:named )?items?[;)]", text, re.M)
    assert sum(int(n) for _, n in heads) == 83
    stars = [l for l in text.splitlines() if "★" in l and "marked ★" not in l]
    assert len(stars) == 4


def test_the_changelog_has_one_entry_for_resume_edit_params():
    # TC-035 TC-036 TC-037 TC-038
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    entries = [l for l in text.splitlines() if l.startswith("- ") and "extra_config" in l and "resume" in l]
    assert len(entries) == 1
    e = entries[0]
    assert "`params`" in e
    for k in KEYS:
        assert k in e, k
    assert "composed" in e and "Google Batch" in e and "relaunch" in e
    assert "no migration" in e.lower()
    assert "NCHC" in e
