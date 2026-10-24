# Nothing existing: tests of the changes a resume may carry (spec resume-edit-params-a); no library knows our closed grammar of extra Nextflow settings or what our fake site must see written, and the rules are ours.
"""resume-edit-params-a: render_resume / render_resume_bundle with `overrides`, and the agent's resume with them.
Test cases are named in the comments (TC-001 ...), see specs/resume-edit-params-a/test-case.md."""
import copy
import json
import os
import re
import secrets
import stat
import subprocess
from pathlib import Path

import pytest

from resume_harness import OLD_TOKEN, SESSION, make_folder
from station_harness import FakePlatform, FakeSite, snapshot
from test_launch_bundle import render, site_ce, parse_yaml
from test_station_launch import ACCT, TOKEN, bundle_for, job_of, run_job
from test_station_fakeplatform import agent_on

SID = "0b1c2d3e-4f50-4a6b-8c7d-9e0f1a2b3c4d"
HERE = Path(__file__).resolve().parent

# The head script of a resume without changes, as v3 wrote it before overrides existed (made by the code before this task; not regenerated).
GOLDEN_HEAD_2 = (
    "#!/bin/bash\n#SBATCH -D /data/w1/runs/run-one\n#SBATCH -J nf-run-one-a2\n#SBATCH --no-requeue\n#SBATCH -p normal\n"
    "#SBATCH -A ACCT-TEST-7\n#SBATCH -c 4\n#SBATCH --mem=26G\n#SBATCH -t 4-00:00:00\numask 077\ncd /data/w1/runs/run-one || exit 1\n"
    "export SLURM_ACCOUNT=ACCT-TEST-7\nexport http_proxy=http://login.example:18080\n"
    "export NXF_OPTS='-Dhttp.proxyHost=login.example -Dhttp.proxyPort=18080'\nexport NXF_SINGULARITY_CACHEDIR=/data/storage/cache\n"
    "export TOWER_ACCESS_TOKEN=\"$(cat tower.token)\"\n"
    "exec nextflow run nf-core/ampliseq -r 2.18.0 -resume 0b1c2d3e-4f50-4a6b-8c7d-9e0f1a2b3c4d -name run-one-a2 -params-file params.yaml "
    "-c nextflow.config -with-tower http://127.0.0.1:8787\n")
GOLDEN_SHA = "761a89107a7dad8492c5b9a97bb6d3874bfb7ec4ffc99349d7c055cda5b96a37"
OV = {"params": {"min_reads": 100}, "extra_config": "process.memory = '16 GB'"}


def launch_mod():
    from abf_station import launch
    return launch


def files_of(overrides=None, attempt=2, origin=None, **over):
    return launch_mod().render_resume(origin=origin or render(), run_name="run-one-a%d" % attempt, attempt=attempt, session_id=SID,
                                      overrides=overrides, **over)


def bundle_of(overrides=None, attempt=2, origin=None):
    return launch_mod().render_resume_bundle(origin=origin or render(), run_name="run-one-a%d" % attempt, attempt=attempt, session_id=SID,
                                             of_run="run-one", of_slurm_job_id=4242, overrides=overrides)


def refusal(overrides, match=None, **kw):
    with pytest.raises(launch_mod().BundleError) as e:
        files_of(overrides, **kw)
    if match:
        assert re.search(match, str(e.value)), str(e.value)
    return str(e.value)


def extra(text, **kw):
    return files_of({"extra_config": text}, **kw)


def last_line(text):
    return text.rstrip("\n").split("\n")[-1]


# ---- US1 -----------------------------------------------------------------------------------------------------------------------------

def test_overrides_change_the_head_script_and_add_files_only():
    # TC-001, TC-002, TC-003, TC-004, TC-008
    origin = render()
    before = copy.deepcopy(origin)
    files = files_of(OV, origin=origin)
    assert list(files) == ["head-2.sh", "params-2.yaml", "extra-2.config"]
    last = last_line(files["head-2.sh"])
    assert " -params-file params-2.yaml " in last and "-params-file params.yaml" not in last
    assert last.endswith("-c nextflow.config -c extra-2.config -with-tower http://127.0.0.1:8787")
    assert origin == before and not set(files) & set(origin["files"])      # TC-008
    for name in ("samplesheet.csv", "params.yaml", "nextflow.config", "head.sh"):
        assert origin["files"][name] == before["files"][name]
    # TC-003: params only
    only_params = files_of({"params": {"min_reads": 100}})
    assert list(only_params) == ["head-2.sh", "params-2.yaml"]
    assert "extra-2.config" not in only_params["head-2.sh"] and "-params-file params-2.yaml" in only_params["head-2.sh"]
    # TC-004: extra only, attempt 3: params-3.yaml still written and equal to the origin's parameters
    only_extra = extra("process.cpus = 4", attempt=3)
    assert list(only_extra) == ["head-3.sh", "params-3.yaml", "extra-3.config"]
    assert parse_yaml(only_extra["params-3.yaml"]) == parse_yaml(origin["files"]["params.yaml"])
    assert only_extra["params-3.yaml"] == origin["files"]["params.yaml"]


def test_site_config_files_still_come_before_nextflow_config():
    # TC-002: with a site's config files, their -c stay before -c nextflow.config
    origin = render(ce=site_ce())
    last = last_line(files_of(OV, origin=origin)["head-2.sh"])
    assert '-c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c nextflow.config -c extra-2.config -with-tower' in last


def test_params_yaml_keeps_input_and_outdir_of_the_origin_folder():
    # TC-005
    origin = render()
    y = parse_yaml(files_of({"params": {"min_reads": 100}}, origin=origin)["params-2.yaml"])
    old = parse_yaml(origin["files"]["params.yaml"])
    assert y["input"] == old["input"] == origin["run_folder"] + "/samplesheet.csv"
    assert y["outdir"] == old["outdir"] == origin["run_folder"] + "/results"


def test_the_extra_file_has_the_header_comment_and_comes_after_nextflow_config():
    # TC-006, TC-007, TC-002
    for text in ("process.cpus = 4", "process.cpus = 4\n", "process.cpus = 4\n\n\n"):
        got = extra(text, attempt=3)["extra-3.config"]
        assert got == "// added by the platform: extra settings of resume 3\nprocess.cpus = 4\n", repr(got)
    indented = "process {\n\twithName: 'FASTQC' {\n  cpus = 4   \n\t}\n}"
    got = extra(indented)["extra-2.config"]
    assert got == "// added by the platform: extra settings of resume 2\n" + indented + "\n"      # TC-007: written as it was given
    head = files_of({"extra_config": "process.cpus = 4"})["head-2.sh"]
    assert head.index("-c nextflow.config") < head.index("-c extra-2.config")


def test_params_overlay_replaces_keeps_and_adds_and_never_deletes():
    # TC-009, TC-010
    origin = render()
    y = parse_yaml(files_of({"params": {"primer": "NEW", "added": 7}}, origin=origin)["params-2.yaml"])
    assert y["primer"] == "NEW" and y["added"] == 7
    assert y["pacbio"] is True and y["depth"] == 3
    assert y["input"] == origin["run_folder"] + "/samplesheet.csv"
    refusal({"params": {"depth": None}}, "depth")
    kept = parse_yaml(files_of({"params": {"added": 7}}, origin=origin)["params-2.yaml"])
    assert kept["depth"] == 3 and kept["primer"] == "AGRG"


@pytest.mark.parametrize("name", ["input", "outdir"])
def test_params_overrides_are_refused_like_a_launch(name):
    # TC-011
    refusal({"params": {name: "/elsewhere"}}, name)


@pytest.mark.parametrize("name,value", [("n", {"a": 1}), ("n", [1, 2]), ("n", None), ("n", float("nan")), ("n", float("inf")),
                                        ("1bad", 1), ("has space", 1), ("", 1)])
def test_params_overrides_are_refused_like_a_launch_shapes(name, value):
    # TC-012: the same value given to the launch's own parameter check is refused, naming the same key
    launch = launch_mod()
    with pytest.raises(launch.BundleError) as direct:
        launch._check_params({name: value})
    msg = refusal({"params": {name: value}})
    assert (name or "''") in msg or repr(name) in msg
    assert str(direct.value).split(":")[0] == msg.split(":")[0]


@pytest.mark.parametrize("value", ["a\x00b", "a\rb", "a\x1bb", "a‮b", "x" * 100001])
def test_params_overrides_refuse_control_characters_and_overlong_text(value):
    # TC-013
    refusal({"params": {"note": value}}, "note")


@pytest.mark.parametrize("ov,match", [({"queue": "x"}, "queue"), ({"params": [1]}, "params"), ({"params": "x"}, "params"),
                                      ({"extra_config": 5}, "extra_config"), ({"extra_config": ["a"]}, "extra_config"),
                                      ("process.cpus = 1", "overrides"), ([("params", {})], "overrides")])
def test_overrides_of_the_wrong_shape_are_refused(ov, match):
    # TC-014: bilingual and names the field
    msg = refusal(ov, match)
    assert re.search(r"[一-鿿]", msg) and re.search(r"[A-Za-z]{4}", msg)


@pytest.mark.parametrize("key", ["samplesheet", "input", "outdir", "pipeline", "revision", "ce", "session_id", "run_name"])
def test_overrides_cannot_change_what_the_origin_decides(key):
    # TC-015
    refusal({key: "x"}, key)
    refusal({"params": {"a": 1}, key: "x"}, key)


# ---- US3: extra_config -------------------------------------------------------------------------------------------------------------

ACCEPTED = [
    "process.memory = '8 GB'", "process.cpus = 4", "process.time = '1h 30m'", "process.time = '4h'", "process.time = '500ms'",
    "process.errorStrategy = 'retry'", "process.errorStrategy = 'terminate'", "process.errorStrategy = 'ignore'",
    "process.errorStrategy = 'finish'", "process.maxRetries = 3", "process.disk = '100.5 GB'", "process.memory = '512MB'",
    "process.memory = '1 TB'", "process.disk = '2KB'", "process.memory = '3 B'", "process.time = '2d 3h 4m 5s'",
    "// only a comment", "\n\n", "process.cpus = 4\n// c\n\nprocess.memory = '1 GB'",
    "process {\n  cpus = 4\n}",
    "process {\nwithName: 'FASTQC' {\ncpus = 4\n}\n}",
    "process {\nwithLabel: 'process_high' {\nmemory = '64 GB'\ntime = '1d'\n}\n}",
    "process {\n// note\n\nwithName: 'A:B_c.d*|e-f' {\n// inner\nerrorStrategy = 'retry'\nmaxRetries = 2\n}\ncpus = 2\n}",
    "process {\nwithName: '%s' {\ncpus = 1\n}\n}" % ("a" * 200),
]


@pytest.mark.parametrize("text", ACCEPTED)
def test_extra_config_accepts_the_resource_lines(text):
    # TC-016, TC-017, TC-025 (200-character name)
    if text.strip("\n") == "":
        assert list(extra(text)) == ["head-2.sh"]       # nothing but blank lines is no extra file
        return
    got = extra(text)["extra-2.config"]
    assert got.endswith(text.rstrip("\n") + "\n")


def _forms(name):
    return ["process.%s = 'x'" % name, "process.%s = 1" % name, "process {\n%s = 'x'\n}" % name, "process {\n%s {\n}\n}" % name,
            "%s = 'x'" % name, "%s { x = 1 }" % name, "process.%s { x = 1 }" % name]


REFUSED_NAMES = ["includeConfig", "env", "workDir", "executor", "tower", "params", "report", "timeline", "trace", "dag", "docker",
                 "singularity", "apptainer", "container", "beforeScript", "afterScript", "ext", "publishDir", "queue", "clusterOptions",
                 "maxErrors"]


@pytest.mark.parametrize("name", REFUSED_NAMES)
def test_extra_config_refuses_everything_else(name):
    # TC-020: every name in the plan's list, in every form, one by one
    for text in _forms(name):
        msg = refusal({"extra_config": text})
        assert re.search(r"第 \d+ 行", msg), (text, msg)


@pytest.mark.parametrize("text", [
    'process.memory = "${x}"', "process.memory = '${x}'", "process.memory = `ls`", "process.cpus = 4.execute()",
    "process.cpus = new Object()", "process.memory = { 4.GB * task.attempt }", "process.cpus = { task -> 2 }",
    "process {\ncpus = { 2 * task.attempt }\n}", "process.cpus = $x", "process.memory = '8 GB'.execute()",
    "process.cpus = 12345", "process.cpus = 1.5", "process.cpus = -1", "process.memory = 8", "process.memory = '8 XB'",
    "process.memory = '8 gb'", "process.memory = 'lots'", "process.time = '1x'", "process.time = 5", "process.time = '1h30'",
    "process.time = ''", "process.errorStrategy = 'foo'", "process.errorStrategy = retry", "process.maxRetries = 'a'",
    "process.cpus = 4 // more", "// note // more", "process.cpus=4;", "process.cpus = 4; process.cpus = 5",
    "cpus = 4", "process {\nprocess.cpus = 4\n}", "process.report.overwrite = false", "report.overwrite = false",
    "timeline.overwrite = false", "withName: 'A' {\ncpus = 1\n}", "process {\nwithName: 'A B' {\ncpus = 1\n}\n}",
    "process {\nwithName: 'A;B' {\ncpus = 1\n}\n}", "process {\nwithName: 'A$B' {\ncpus = 1\n}\n}",
    "process {\nwithName: '%s' {\ncpus = 1\n}\n}" % ("a" * 201), "process {\nwithName: '' {\ncpus = 1\n}\n}",
    "process {\nwithName: \"A\" {\ncpus = 1\n}\n}", "process {\nwithName: A {\ncpus = 1\n}\n}",
    "process {\nwithName: 'A' {\ncpus = 1\n}", "process {\ncpus = 4", "}", "process.cpus = 4\n}", "process {\n}\n}",
    "process {\nwithName: 'A' {\nwithLabel: 'B' {\ncpus = 1\n}\n}\n}", "process {\nprocess {\n}\n}",
    "process {\nwithName: 'A' {\nwithName: 'B' {\n}\n}\n}", "process.cpus = 4 /* c */", "/* c */", "process.cpus = 4 }",
    "import java.io.File", "System.exit(1)", "process.cpus = 4 + 1", "process.$x = 4", "p\\u0072ocess.cpus = 4",
])
def test_extra_config_refuses_anything_outside_the_closed_syntax(text):
    # TC-019, TC-021, TC-022, TC-023, TC-024, TC-025
    msg = refusal({"extra_config": text})
    assert re.search(r"第 \d+ 行|line \d+", msg), msg
    assert "Traceback" not in msg


def test_a_block_written_on_one_line_is_refused_with_a_hint():
    # TC-018
    msg = refusal({"extra_config": "process { withName: 'X' { cpus = 4 } }"}, r"第 1 行")
    assert "請分行寫，每行一個 `{`、一個設定或一個 `}`" in msg


def test_one_bad_line_refuses_the_whole_file_and_is_named():
    # TC-029
    text = "// one\nprocess.cpus = 4\nprocess.queue = 'x'\n\nprocess.memory = '1 GB'"
    msg = refusal({"extra_config": text}, r"第 3 行")
    assert "queue" in msg and re.search(r"cpus|memory", msg)      # says what is allowed
    assert "第 4 行" not in msg and "Traceback" not in msg


@pytest.mark.parametrize("text", ["// 中文", "// café", "// del\x7f", "// ctl\x01", "// cr\rx", "process.cpus = 4\r\n",
                                  "// back\\slash", "process.memory = '8 GB' \\", "// ‮", "// nul\x00", "// esc\x1b", "// ff\x0c",
                                  "// nbsp "])
def test_extra_config_is_ascii_only_without_backslash_or_cr(text):
    # TC-026
    refusal({"extra_config": text})
    assert extra("process {\n\tcpus = 4\n}".replace("process {\n\tcpus = 4\n}", "// tab\there\nprocess.cpus = 4"))      # tab and newline are fine


def test_extra_config_too_long_is_refused():
    # TC-027
    line = "// " + "x" * 76 + "\n"      # 80 characters with the newline
    ok = line * 249 + "// " + "x" * 77            # 249*80 + 80 = 20000
    assert len(ok) == 20000
    assert "extra-2.config" in extra(ok)
    msg = refusal({"extra_config": ok + "x"}, "extra_config")
    assert "20000" in msg


@pytest.mark.parametrize("text", ["report.overwrite = false", "timeline.overwrite = false", "process.report.overwrite = false"])
def test_extra_config_cannot_undo_the_platforms_overwrite_block(text):
    # TC-028
    origin = render()
    assert "report.overwrite = true" in origin["files"]["nextflow.config"] and "timeline.overwrite = true" in origin["files"]["nextflow.config"]
    refusal({"extra_config": text})


# ---- US4 / US5: the bundle ---------------------------------------------------------------------------------------------------------

def test_without_overrides_the_resume_is_byte_for_byte_today():
    # TC-030, TC-031, TC-033
    files = files_of()
    assert files == {"head-2.sh": GOLDEN_HEAD_2}
    b = bundle_of()
    assert list(b["files"]) == ["head-2.sh"] and b["files"]["head-2.sh"] == GOLDEN_HEAD_2
    assert set(b["resume"]) == {"of_run", "of_slurm_job_id", "session_id", "attempt", "origin"}
    from abf_platform import common
    assert common.bundle_sha256(b) == GOLDEN_SHA


@pytest.mark.parametrize("ov", [None, {}, {"params": {}}, {"extra_config": ""}, {"params": {}, "extra_config": ""}])
def test_empty_overrides_are_no_overrides(ov):
    # TC-032
    from abf_platform import common
    plain, same = bundle_of(), bundle_of(ov)
    assert same == plain and "overrides" not in same["resume"]
    assert files_of(ov) == files_of()
    assert common.bundle_sha256(same) == common.bundle_sha256(plain) == GOLDEN_SHA


def test_overrides_are_in_the_bundle_and_in_its_hash():
    # TC-036, TC-037
    from abf_platform import common
    origin = render()
    both = bundle_of(OV, origin=origin)
    assert both["resume"]["overrides"] == {"params": {"min_reads": 100}, "extra_config": "process.memory = '16 GB'\n"}
    assert both["resume"]["origin"] == origin
    assert list(both["files"]) == ["head-2.sh", "params-2.yaml", "extra-2.config"]
    assert both["files"]["extra-2.config"].split("\n", 1)[1] == both["resume"]["overrides"]["extra_config"]
    assert bundle_of({"params": {"a": 1}, "extra_config": ""})["resume"]["overrides"] == {"params": {"a": 1}}
    assert bundle_of({"params": {}, "extra_config": "process.cpus = 2"})["resume"]["overrides"] == {"extra_config": "process.cpus = 2\n"}
    base = common.bundle_sha256(both)
    seen = {base}
    for edit in (lambda b: b["resume"]["overrides"]["params"].update(min_reads=101),
                 lambda b: b["resume"]["overrides"].update(extra_config="process.cpus = 9\n"),
                 lambda b: b["files"].update({"params-2.yaml": b["files"]["params-2.yaml"] + "x: 1\n"}),
                 lambda b: b["files"].update({"extra-2.config": b["files"]["extra-2.config"] + "// x\n"}),
                 lambda b: b["files"].update({"head-2.sh": b["files"]["head-2.sh"] + "# x\n"})):
        t = copy.deepcopy(both)
        edit(t)
        seen.add(common.bundle_sha256(t))
    assert len(seen) == 6


def test_a_site_module_origin_takes_overrides():
    # TC-038
    origin = render(ce=site_ce())
    assert origin["pipeline_source"]["kind"] == "site-module"
    last = last_line(files_of(OV, origin=origin)["head-2.sh"])
    assert last.startswith('exec nextflow run "$NFCORE_AMPLISEQ_HOME" -resume ')
    assert " -params-file params-2.yaml " in last and "-c nextflow.config -c extra-2.config -with-tower" in last


def test_composed_and_google_batch_origins_are_still_refused_with_overrides():
    # TC-039, TC-040 (render side)
    launch = launch_mod()
    origin = render()
    composed = dict(origin, pipeline_source={"kind": "composed"})
    with pytest.raises(launch.BundleError) as e:
        files_of(OV, origin=composed)
    assert str(e.value) == launch.COMPOSED_NO_RESUME
    with pytest.raises(launch.BundleError) as e:
        files_of(OV, origin=dict(origin, project={}))
    assert str(e.value) == launch.COMPOSED_NO_RESUME


def test_the_new_helpers_do_not_have_resume_or_relaunch_in_their_names():
    # TC-034: tests/test_keep_submissions.py TC-084 scans function names; the constants may
    import ast
    src = (HERE.parent / "abf_station" / "launch.py").read_text(encoding="utf-8")
    names = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)}
    assert {"_check_extra_config", "_normalize_overrides"} <= names
    assert not [n for n in names if re.search(r"resume|relaunch", n) and n not in {"render_resume", "render_resume_bundle", "run_resume"}]


# ---- the site -----------------------------------------------------------------------------------------------------------------------

@pytest.fixture
def site(tmp_path):
    s = FakeSite(tmp_path / "s", account=ACCT, site_user="tester", destructive_log=True)
    (s.storage / "cache").mkdir()
    (s.storage / "rawdata" / "s1.fq").write_text("x")
    return s


@pytest.fixture
def fake():
    f = FakePlatform()
    yield f
    f.stop()


def ov_bundle(site, fake, overrides=OV, attempt=2, run="run-a", new="run-a-a2", **over):
    origin = bundle_for(site, fake, run=run, **over)
    return origin, launch_mod().render_resume_bundle(origin=origin, run_name=new, attempt=attempt, session_id=SESSION, of_run=run,
                                                     of_slurm_job_id=4242, overrides=overrides)


def unchanged(site, f, before):
    assert snapshot(f) == before
    assert not [c for c in site.calls() if c.split()[0] not in ("sinfo", "java", "nextflow", "squeue")], site.calls()
    assert site.destructive() == [] and site.dangerous() == [] and site.guards_intact()


def test_station_writes_the_new_files_once_and_leaves_the_originals_alone(tmp_path, site, fake):
    # TC-041, TC-042, TC-052, TC-055
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, job_of(b))
        out = a.output()
    assert res["state"] == "done", res
    calls = site.calls()
    sb = [c for c in calls if c.startswith("sbatch")]
    assert len(sb) == 1 and sb[0].split()[1] == str(f / "head-2.sh")
    tars = [c for c in site.destructive() if c.startswith("tar")]
    assert len(tars) == 1 and not [c for c in site.destructive() if c.split()[0] in ("rm", "rmdir", "mv")]
    assert site.scripts() == [b["files"]["head-2.sh"]]
    after = snapshot(f)
    assert set(after) - set(before) == {"head-2.sh", "params-2.yaml", "extra-2.config"}
    assert not set(before) - set(after)
    assert {k for k in before if after[k] != before[k]} <= {".", "tower.token"}
    for name in ("samplesheet.csv", "params.yaml", "nextflow.config", "head.sh"):
        assert (f / name).read_bytes() == origin["files"][name].encode("utf-8")
    assert (f / "params-2.yaml").read_text() == b["files"]["params-2.yaml"] and "min_reads: 100" in (f / "params-2.yaml").read_text()
    assert (f / "extra-2.config").read_text() == b["files"]["extra-2.config"]
    assert (f / "tower.token").read_text() == TOKEN != OLD_TOKEN
    assert (f / "work" / "ab" / "task.txt").exists() and "crazy_darwin" in (f / ".nextflow" / "history").read_text()
    # TC-055: the token is only in tower.token
    for p in f.rglob("*"):
        if p.is_file() and p.name != "tower.token" and p.name != "history":
            assert TOKEN not in p.read_text(errors="replace"), p
    assert TOKEN not in json.dumps(b) and TOKEN not in out and not [c for c in calls + site.ssh_calls() if TOKEN in c]
    assert site.guards_intact()


def test_station_writes_only_params_file_when_there_is_no_extra_config(tmp_path, site, fake):
    # TC-042
    origin, b = ov_bundle(site, fake, overrides={"params": {"min_reads": 5}})
    f = make_folder(origin)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res
    assert set(snapshot(f)) - set(before) == {"head-2.sh", "params-2.yaml"}
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1


def test_the_head_script_the_site_got_runs_nextflow_with_the_new_files(tmp_path, site, fake):
    # TC-001 / TC-002 on the site: nextflow is called with params-2.yaml and both configs in the order given
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        assert run_job(fake, job_of(b))["state"] == "done"
    bindir = tmp_path / "nfbin"
    bindir.mkdir()
    nf = bindir / "nextflow"
    nf.write_text("#!/usr/bin/env python3\nimport json, os, sys\njson.dump({'argv': sys.argv[1:]}, open(os.environ['ABF_TEST_OUT'], 'w'))\n")
    nf.chmod(0o755)
    env = {"PATH": str(bindir) + os.pathsep + os.environ["PATH"], "ABF_TEST_OUT": str(tmp_path / "seen.json")}
    assert subprocess.run(["bash", str(f / "head-2.sh")], env=env).returncode == 0
    argv = json.load(open(tmp_path / "seen.json"))["argv"]
    assert argv == ["run", "nf-core/ampliseq", "-r", "2.18.0", "-resume", SESSION, "-name", "run-a-a2", "-params-file", "params-2.yaml",
                    "-c", "nextflow.config", "-c", "extra-2.config", "-with-tower", fake.url]


def test_station_without_overrides_writes_exactly_head_and_token(tmp_path, site, fake):
    # TC-035
    origin, b = ov_bundle(site, fake, overrides=None)
    assert "overrides" not in b["resume"]
    f = make_folder(origin)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res
    assert set(snapshot(f)) - set(before) == {"head-2.sh"}
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1


def tampered(b, how):
    t = copy.deepcopy(b)
    if how == "overrides-params":
        t["resume"]["overrides"]["params"]["min_reads"] = 1
    elif how == "overrides-extra":
        t["resume"]["overrides"]["extra_config"] = "process.cpus = 99\n"
    elif how == "params-file":
        t["files"]["params-2.yaml"] += "evil: 1\n"
    elif how == "extra-file":
        t["files"]["extra-2.config"] += "process.executor = 'local'\n"
    elif how == "head-file":
        t["files"]["head-2.sh"] += "touch /tmp/evil\n"
    elif how == "no-overrides":
        del t["resume"]["overrides"]
    elif how == "empty-overrides":
        t["resume"]["overrides"] = {}
    elif how == "none-overrides":
        t["resume"]["overrides"] = None
    elif how == "unknown-key":
        t["resume"]["surprise"] = 1
    elif how == "unknown-override-key":
        t["resume"]["overrides"]["queue"] = "x"
    elif how == "extra-new-file":
        t["files"]["evil.sh"] = "touch /tmp/evil\n"
    return t


HOWS = ["overrides-params", "overrides-extra", "params-file", "extra-file", "head-file", "no-overrides", "empty-overrides", "none-overrides",
        "unknown-key", "unknown-override-key", "extra-new-file"]


@pytest.mark.parametrize("how", HOWS)
def test_station_refuses_a_bundle_changed_after_the_yes(tmp_path, site, fake, how):
    # TC-043, TC-044: the confirmation and the hash are those of the bundle as it was
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    good = job_of(b)
    job = dict(good, args={"bundle": tampered(b, how), "confirmation_id": good["args"]["confirmation_id"],
                           "bundle_sha256": good["args"]["bundle_sha256"]})
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, job)
        assert a.alive()
    assert res["state"] == "refused" and re.search(r"不符|mismatch", res["result"]["message"]), res
    unchanged(site, f, before)


@pytest.mark.parametrize("how", HOWS)
def test_station_refuses_a_changed_bundle_even_when_the_hash_was_changed_with_it(tmp_path, site, fake, how):
    # TC-043, TC-044, TC-045: confirmed as it is, hash and all: only the agent's own rebuild can refuse it
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, job_of(tampered(b, how)))
        assert a.alive()
    assert res["state"] == "refused", (how, res)
    assert re.search(r"重新產生|欄位|內容不合規則", res["result"]["message"]), res
    unchanged(site, f, before)


def test_an_empty_overrides_key_on_a_bundle_without_changes_is_refused(tmp_path, site, fake):
    # TC-044
    origin, b = ov_bundle(site, fake, overrides=None)
    f = make_folder(origin)
    t = copy.deepcopy(b)
    t["resume"]["overrides"] = {}
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(t))
    assert res["state"] == "refused", res
    unchanged(site, f, before)


def test_station_origin_changed_consistently_is_refused(tmp_path, site, fake):
    # TC-046: the origin is another, internally consistent first launch; the folder holds the real one
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    other_origin, other = ov_bundle(site, fake, params={"primer": "SOMETHING-ELSE", "pacbio": True})
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(other))
    assert res["state"] == "refused" and str(f) in res["result"]["message"], res
    unchanged(site, f, before)


def test_station_origin_changed_on_the_bundle_only_is_refused(tmp_path, site, fake):
    # TC-046: an origin changed on the bundle only (the agent rebuilds the first launch from its own facts)
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    t = copy.deepcopy(b)
    t["resume"]["origin"]["params"]["primer"] = "OTHER"
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(t))
    assert res["state"] == "refused", res
    unchanged(site, f, before)


@pytest.mark.parametrize("which", ["params-2.yaml", "extra-2.config"])
@pytest.mark.parametrize("kind", ["file", "link"])
def test_station_refuses_when_params_n_or_extra_n_exists_or_is_a_link(tmp_path, site, fake, which, kind):
    # TC-047, TC-048
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    if kind == "file":
        (f / which).write_text("somebody's own\n")
    else:
        target = tmp_path / "linked-target"
        target.write_text("untouched\n")
        os.symlink(target, f / which)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused" and which in res["result"]["message"], res
    assert re.search(r"不覆蓋|exists", res["result"]["message"])
    unchanged(site, f, before)
    assert not (f / "head-2.sh").exists() and (f / "tower.token").read_text() == OLD_TOKEN
    if kind == "link":
        assert (tmp_path / "linked-target").read_text() == "untouched\n"


@pytest.mark.parametrize("how", ["edited", "gone"])
def test_original_files_sha_check_still_applies_with_overrides(tmp_path, site, fake, how):
    # TC-049
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    if how == "edited":
        (f / "params.yaml").write_text((f / "params.yaml").read_text() + "x: 1\n")
    else:
        (f / "params.yaml").unlink()
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused" and "params.yaml" in res["result"]["message"], res
    unchanged(site, f, before)


def test_a_resume_confirmation_with_overrides_is_spent_once(tmp_path, site, fake):
    # TC-050
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    job = job_of(b)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        assert run_job(fake, job)["state"] == "done"
        before = snapshot(f)
        second = run_job(fake, job)
    assert second["state"] == "refused" and re.search(r"已經用過|used already", second["result"]["message"]), second
    assert snapshot(f) == before
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1


@pytest.mark.parametrize("how", ["no-confirmation", "other-content", "used", "other-agent"])
def test_nothing_is_written_without_a_matching_yes(tmp_path, site, fake, how):
    # TC-051
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    good = job_of(b)
    if how == "no-confirmation":
        job = dict(good, confirmation=None)
    elif how == "other-content":
        _, other = ov_bundle(site, fake, overrides={"params": {"min_reads": 2}})
        job = dict(good, confirmation=dict(good["confirmation"], sha256=job_of(other)["args"]["bundle_sha256"]))
    elif how == "used":
        job = dict(good, confirmation=dict(good["confirmation"], used_at=12345.0))
    else:
        t = copy.deepcopy(b)
        t["agent"] = t["resume"]["origin"]["agent"] = "agent-other"
        job = job_of(t)
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job)
    assert res["state"] == "refused", res
    unchanged(site, f, before)


@pytest.mark.parametrize("how", ["composed", "composed-kind", "gcb-outer", "gcb-origin"])
def test_composed_and_google_batch_origins_are_still_refused_by_the_station_with_overrides(tmp_path, site, fake, how):
    # TC-039, TC-040: the original words
    launch = launch_mod()
    origin, b = ov_bundle(site, fake)
    f = make_folder(origin)
    t = copy.deepcopy(b)
    if how == "composed":
        t["resume"]["origin"]["project"] = {"main.nf": "x"}
    elif how == "composed-kind":
        t["resume"]["origin"]["pipeline_source"] = {"kind": "composed"}
    elif how == "gcb-outer":
        t["ce"]["platform"] = launch.GCB
    else:
        t["resume"]["origin"]["ce"]["platform"] = launch.GCB
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(t))
    assert res["state"] == "refused", res
    assert res["result"]["message"] == (launch.GCB_NO_RESUME if how.startswith("gcb") else launch.COMPOSED_NO_RESUME), res
    unchanged(site, f, before)


def test_no_second_copy_of_run_state():
    # TC-056
    root = HERE.parent.parent
    r = subprocess.run(["bash", "tests/no_second_run_state_test.sh"], cwd=str(root), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
