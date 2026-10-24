# Nothing existing: checks that docs/PLATFORM.md and docs/TESTING.md say what a resume with edits really does; no tool compares a document with a constant.
"""resume-edit-params-d: the words about a resume that carries changed parameters and extra resource settings (TC-001 to TC-033, TC-046)."""
import re
import shlex

from helpers import REPO_ROOT

DOCS = REPO_ROOT / "docs"
SECTION = "### Resume and relaunch (spec 009e)"


def read(name):
    return (DOCS / name).read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


def resume_section():
    text = read("PLATFORM.md")
    assert SECTION in text
    body = text[text.index(SECTION):]
    return body[:body.index("\n### What was handed over")] if "\n### What was handed over" in body else body[:body.index("\n### ", 10)]


def test_platform_md_says_a_resume_may_carry_params_and_extra_config_and_a_relaunch_the_name_alone():
    # TC-001, TC-002, TC-003, TC-005, TC-020
    sec = flat(resume_section())
    full = flat(read("PLATFORM.md"))
    assert re.search(r"`resume` (may|can) (also )?carr(y|ies)[^.]*`params`[^.]*`extra_config`", sec)
    assert re.search(r"`relaunch`[^.]*(name|run_name)[^.]*alone|`relaunch` takes (only )?(the )?(run )?name", sec)
    assert re.search(r"changing the samples, the pipeline, the revision or the environment is a new analysis", sec, re.I)
    assert re.search(r"(resume|it) that changes (some|a few) parameters or adds resource settings is still the same analysis", sec)
    assert "can be gone on with by its name alone" not in full
    assert "Changing the samples, the parameters, the revision, the pipeline or the environment is a new analysis" not in full
    assert "each with the one argument `run_name`" not in full
    assert not re.search(r"`?resume`?[^.]{0,40}(only|just) (the|one)[^.]{0,20}(argument|name)", full)
    assert "the gap is `resume-edit-params`" not in full
    assert re.search(r"a (required|mandatory)[^.]*`run_name`[^.]*(two|2) optional[^.]*`params`[^.]*`extra_config`|one required[^.]*two optional", sec)
    assert re.search(r"web form[^.]*(compute|environment)[^.]*not (built|done)|not (built|done)[^.]*web form", full)


def test_platform_md_says_what_an_edited_resume_writes_and_shows():
    # TC-008, TC-009, TC-010, TC-046
    from abf_launch import build
    sec = flat(resume_section())
    assert "params-<N>.yaml" in sec and "extra-<N>.config" in sec and "resume.overrides" in sec
    assert build.EDITED_SENTENCE in sec
    assert re.search(r"(old|first)[^.]*(→|->|to)[^.]*new", sec)
    assert re.search(r"(task|tasks)[^.]*(uses?|using)[^.]*(changed|edited)[^.]*(run again|rerun|re-run|run anew)[^.]*(rest|others?)[^.]*(reused|cached|kept|carried)", sec)
    for name in ("samplesheet.csv", "params.yaml", "nextflow.config", "head.sh"):
        assert name in sec, name
    assert re.search(r"(four files|those four)[^.]*(not changed|untouched|never changed|is not touched|are not touched)|(not changed|untouched)[^.]*four", sec) \
        and re.search(r"sha", sec)


def test_platform_md_names_the_six_keys_the_ascii_rule_and_the_20000_limit():
    # TC-013, TC-015, TC-016
    from abf_station import launch
    sec = flat(resume_section())
    assert "What may be changed" in sec
    for key in launch.EXTRA_KEYS:
        assert "`%s`" % key in sec, key
    assert len(launch.EXTRA_KEYS) == 6
    assert str(launch.MAX_EXTRA_CONFIG) in sec.replace(",", "") and "20000" in sec.replace(",", "")
    assert re.search(r"ASCII", sec) and re.search(r"backslash", sec)
    assert "-c extra-<N>.config" in sec and "nextflow.config" in sec


def test_platform_md_says_a_repeated_same_call_gets_the_same_job_and_a_different_one_is_refused_naming_the_attempt():
    # TC-022, TC-023, TC-024
    sec = flat(resume_section())
    assert "Asking again" in sec
    i = sec.index("Asking again")
    part = sec[i:i + 1500]
    assert re.search(r"same (edits|content|changes)[^.]*(same|that) (job|attempt)|same job number", part)
    assert re.search(r"(no|not) (a )?second job|does not (open|start|queue) a second", part)
    assert re.search(r"(other|different)[^.]*refused[^.]*(newest|latest)[^.]*(names|naming|name)", part)
    assert "get_run" not in part.split("**", 3)[0] and not re.search(r"same[^.]*(is|are|will be) refused", part)


def test_platform_md_still_says_not_yet_accepted_on_nchc_and_that_composed_and_google_batch_cannot_resume():
    # TC-025, TC-026, TC-044
    full = flat(read("PLATFORM.md"))
    sec = flat(resume_section())
    i = sec.index("Not yet accepted on NCHC")
    part = sec[i:i + 1200]
    assert "-resume <session id>" in part
    assert re.search(r"(also|same)[^.]*(resume|resumes)[^.]*(changed|edited) param", part)
    assert re.search(r"fake site only", part) and not re.search(r"(was|has been) (checked|verified|accepted) on (NCHC|Taiwania)", part)
    assert re.search(r"Resume and relaunch of a Google Batch run[^.]*refused with 尚未支援", full)
    assert re.search(r"A resume or a relaunch of a composed run is refused", full)


def test_the_resume_command_examples_in_section_9_parse_with_the_real_parser():
    # TC-004
    from abf_platform import cli
    sec = resume_section()
    parser = cli.build_parser()
    seen = []
    for ln in sec.splitlines():
        m = re.match(r"^\s*abf-platform ((?:resume|relaunch)\b[^#<>]*?)\s*(#.*)?$", ln)
        if not m:
            continue
        argv = shlex.split(m.group(1))
        parser.parse_args(argv)
        seen.append(argv)
    assert ["resume", "ampliseq-d5", "--param", "min_reads=100", "--config-file", "bigmem.config"] in seen
    assert ["resume", "ampliseq-d5"] in seen and ["relaunch", "ampliseq-d5"] in seen
    assert len(seen) >= 3


def test_testing_md_has_the_changed_params_cache_check_marked_not_yet_done():
    # TC-029, TC-030, TC-031, TC-032, TC-033
    text = read("TESTING.md")
    sec = flat(text[text.index("## Resume and relaunch (009e)"):])
    sec = sec[:sec.index(" ## ", 5)] if " ## " in sec[5:] else sec
    m = re.search(r"\d\. \*\*[^*]*(changed|edited) param[^*]*\(not yet done\)\.?\*\*(.*?)(?= \d\. \*\*|$)", sec)
    assert m, "no numbered point about a resume with changed parameters marked (not yet done)"
    pt = m.group(2)
    assert "abf-platform resume RUN --param" in pt and "--config-file" in pt and "process.memory" in pt and re.search(r"answer y", pt)
    assert "-resume <session id>" in pt and "-params-file params-2.yaml" in pt and "-c extra-2.config" in pt
    assert "get_run" in pt and "cached" in pt
    for name in ("params.yaml", "nextflow.config", "head.sh", "samplesheet.csv"):
        assert name in pt, name
    assert "a resume may carry changed parameters and extra resource settings; the samples, pipeline, revision and environment cannot change" in sec
