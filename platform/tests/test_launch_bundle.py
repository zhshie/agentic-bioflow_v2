# Nothing existing: tests of the launch bundle, the one function that turns a user's choices into the files that are shown and then written; no existing tool renders a Nextflow head job script for Slurm from a compute environment.
"""render_bundle: what is shown, what is written, and what is refused (feature 007b)."""
import copy
import csv
import io
import json
import os
import re
import stat
import subprocess
import sys

import pytest

from helpers import PLATFORM_DIR

ACCOUNT = "ACCT-TEST-7"
SHEET = [["sample", "fastq_1"], ["s1", "/data/storage/rawdata/s1.fq.gz"], ["s2", "/data/storage/rawdata/s2.fq.gz"]]


def ce_snapshot(**over):
    ce = {"name": "lab-a", "platform": "slurm-platform", "workDir": "/data/w1", "launchDir": "/data/launch",
          "headQueue": "normal", "computeQueue": "dev", "readRoots": [],
          "headJobOptions": "-A %s -c 4 --mem=26G -t 4-00:00:00" % ACCOUNT,
          "environment": [{"name": "http_proxy", "value": "http://login.example:18080", "head": True, "compute": True},
                          {"name": "NXF_OPTS", "value": "-Dhttp.proxyHost=login.example -Dhttp.proxyPort=18080", "head": True,
                           "compute": False},
                          {"name": "NXF_SINGULARITY_CACHEDIR", "value": "/data/storage/cache", "head": True, "compute": False},
                          {"name": "COMPUTE_ONLY", "value": "x", "head": False, "compute": True}],
          "nextflowConfig": "process.executor = 'slurm'\n", "preRunScript": "", "postRunScript": ""}
    ce.update(over)
    return ce


def facts(**over):
    f = {"slurm_account": ACCOUNT, "reach": "local", "platform_local": True, "endpoint": "http://127.0.0.1:8787",
         "forward_file": None, "storage_root": "/data/storage"}
    f.update(over)
    return f


def inputs(**over):
    d = dict(ce=ce_snapshot(), agent="agent-t", facts=facts(), roots=["/data/w1", "/data/launch", "/data/storage"],
             run_name="run-one", pipeline="nf-core/ampliseq", revision="2.18.0", samplesheet=copy.deepcopy(SHEET),
             params={"primer": "AGRG", "pacbio": True, "depth": 3})
    d.update(over)
    return d


def render(**over):
    from abf_station import launch
    return launch.render_bundle(**inputs(**over))


def refused(match=None, **over):
    from abf_station import launch
    with pytest.raises(launch.BundleError) as e:
        launch.render_bundle(**inputs(**over))
    if match:
        assert re.search(match, str(e.value)), str(e.value)
    return str(e.value)


def parse_yaml(text):
    """The dialect params.yaml is written in: `name: scalar` lines, strings in double quotes with JSON escapes."""
    out = {}
    for ln in text.splitlines():
        m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*): (.*)", ln)
        assert m, "not a plain `name: value` line: %r" % ln
        v = m.group(2)
        if v in ("true", "false"):
            out[m.group(1)] = v == "true"
        elif re.fullmatch(r"-?\d+", v):
            out[m.group(1)] = int(v)
        elif re.fullmatch(r"-?\d+\.\d+([eE][+-]?\d+)?", v):
            out[m.group(1)] = float(v)
        else:
            assert v.startswith('"') and v.endswith('"'), v
            out[m.group(1)] = json.loads(v)
    return out


def sbatch_lines(script):
    return [ln for ln in script.splitlines() if ln.startswith("#SBATCH")]


ALLOWED_SBATCH = [r"#SBATCH -D \S+", r"#SBATCH -J nf-[a-z0-9_-]+", r"#SBATCH --no-requeue", r"#SBATCH -p [A-Za-z0-9_.-]+",
                  r"#SBATCH -c \d+", r"#SBATCH --cpus-per-task=\d+", r"#SBATCH --mem=\d+[MG]", r"#SBATCH -t (\d+-)?\d{1,2}:\d{2}:\d{2}",
                  r"#SBATCH --time=(\d+-)?\d{1,2}:\d{2}:\d{2}", r"#SBATCH -A [A-Za-z0-9_.-]+", r"#SBATCH --qos=[A-Za-z0-9_.-]+"]


def only_template_sbatch(script):
    for ln in sbatch_lines(script):
        assert any(re.fullmatch(p, ln) for p in ALLOWED_SBATCH), ln


# ---- the shape of a bundle ---------------------------------------------------------------------------

def test_the_bundle_is_plain_json_and_holds_what_will_be_written():
    # TC-001, TC-012 (the content), TC-015 (the four files)
    b = render()
    assert json.loads(json.dumps(b)) == b
    assert set(b["files"]) == {"samplesheet.csv", "params.yaml", "nextflow.config", "head.sh"}
    assert b["run_folder"] == "/data/w1/runs/run-one"
    assert b["run_name"] == "run-one" and b["agent"] == "agent-t"
    rows = list(csv.reader(io.StringIO(b["files"]["samplesheet.csv"])))
    assert rows == SHEET
    p = parse_yaml(b["files"]["params.yaml"])
    assert p == {"primer": "AGRG", "pacbio": True, "depth": 3, "input": "/data/w1/runs/run-one/samplesheet.csv",
                 "outdir": "/data/w1/runs/run-one/results"}
    # abort-report-overwrite (TC-015): the user's text first, verbatim; then the platform's commented block, nothing else
    cfg = b["files"]["nextflow.config"]
    assert cfg.startswith("process.executor = 'slurm'\n")
    assert [ln for ln in cfg[len("process.executor = 'slurm'\n"):].splitlines() if ln.strip() and not ln.startswith("//")] \
        == ["report.overwrite = true", "timeline.overwrite = true"]
    from abf_platform import common
    assert common.bundle_sha256(b) == common.bundle_sha256(json.loads(json.dumps(b)))


def test_the_bundle_is_the_same_every_time_for_the_same_input():
    # TC-001: the hash of what is shown is the hash of what is queued
    from abf_platform import common
    assert common.bundle_sha256(render()) == common.bundle_sha256(render())
    assert common.bundle_sha256(render()) != common.bundle_sha256(render(run_name="run-two"))


def test_a_ce_without_a_nextflow_config_still_gives_a_config_file_that_says_so():
    # TC-013
    b = render(ce=ce_snapshot(nextflowConfig=""))
    assert b["files"]["nextflow.config"].startswith("//") and b["files"]["nextflow.config"].endswith("\n")


# ---- the head job script ------------------------------------------------------------------------------

def run_head(tmp_path, bundle, extra_env=None, token="TOKEN_CANARY_f33d"):
    """Run head.sh with a stand-in nextflow in a sandbox folder; returns what the stand-in saw."""
    folder = tmp_path / "run"
    folder.mkdir()
    (folder / "tower.token").write_text(token)
    text = bundle["files"]["head.sh"].replace(bundle["run_folder"], str(folder))
    script = tmp_path / "head.sh"
    script.write_text(text)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "nextflow"
    fake.write_text("#!/usr/bin/env python3\nimport json, os, sys\n"
                    "json.dump({'argv': sys.argv[1:], 'env': dict(os.environ), 'cwd': os.getcwd()}, "
                    "open(os.environ['ABF_TEST_OUT'], 'w'))\n")
    fake.chmod(0o755)
    env = {"PATH": str(bindir) + os.pathsep + os.environ["PATH"], "ABF_TEST_OUT": str(tmp_path / "seen.json"), "HOME": str(tmp_path)}
    env.update(extra_env or {})
    r = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.load(open(tmp_path / "seen.json")), folder, text


def test_tc013_the_head_script_runs_nextflow_the_way_seqera_does(tmp_path):
    # TC-013 (fake nextflow half): the arguments word for word, the environment, and no token in the script text
    b = render()
    seen, folder, text = run_head(tmp_path, b)
    assert seen["argv"] == ["run", "nf-core/ampliseq", "-r", "2.18.0", "-name", "run-one", "-params-file", "params.yaml",
                            "-c", "nextflow.config", "-with-tower", "http://127.0.0.1:8787"]
    assert os.path.realpath(seen["cwd"]) == os.path.realpath(str(folder))
    env = seen["env"]
    assert env["SLURM_ACCOUNT"] == ACCOUNT
    assert env["TOWER_ACCESS_TOKEN"] == "TOKEN_CANARY_f33d"
    assert env["http_proxy"] == "http://login.example:18080" and env["NXF_SINGULARITY_CACHEDIR"] == "/data/storage/cache"
    assert "COMPUTE_ONLY" not in env, "a variable meant for the compute nodes is not exported by the head job"
    assert "NXF_LOG_FILE" not in env
    assert "TOKEN_CANARY_f33d" not in text and "tower.token" in text
    assert not re.search(r"\s-log", text) and "NXF_LOG_FILE" not in text
    assert subprocess.run(["bash", "-n", "-c", b["files"]["head.sh"]], capture_output=True).returncode == 0


def test_tc013_over_a_reverse_forward_the_endpoint_is_read_from_the_forward_file_and_the_proxy_loopback_is_opened(tmp_path):
    # TC-013, TC-026: the head job asks its Java to send even loopback traffic through the relay
    fwd = tmp_path / "fwd"
    fwd.write_text("41234\n")
    b = render(facts=facts(reach="ssh", forward_file=str(fwd)))
    seen, _, text = run_head(tmp_path, b)
    assert seen["argv"][-2:] == ["-with-tower", "http://127.0.0.1:41234"]
    opts = seen["env"]["NXF_OPTS"]
    assert "-Dhttp.proxyHost=login.example" in opts and re.search(r"-Dhttp\.nonProxyHosts=(\s|$)", opts), opts
    assert str(fwd) in text


def test_tc013_a_head_script_cannot_start_without_a_forward_port(tmp_path):
    # TC-013: no port file, no run: it stops at once and says why
    b = render(facts=facts(reach="ssh", forward_file=str(tmp_path / "nothing-here")))
    folder = tmp_path / "run"
    folder.mkdir()
    (folder / "tower.token").write_text("t")
    script = tmp_path / "h.sh"
    script.write_text(b["files"]["head.sh"].replace(b["run_folder"], str(folder)))
    r = subprocess.run(["bash", str(script)], capture_output=True, text=True, env={"PATH": os.environ["PATH"]})
    assert r.returncode != 0 and "forward" in (r.stdout + r.stderr).lower()


def test_tc014_the_sbatch_lines_are_only_the_ones_the_template_allows():
    # TC-014
    b = render(ce=ce_snapshot(headJobOptions="-c 4 --mem=26G -t 4-00:00:00"))
    only_template_sbatch(b["files"]["head.sh"])
    lines = sbatch_lines(b["files"]["head.sh"])
    assert "#SBATCH -D /data/w1/runs/run-one" in lines and "#SBATCH -J nf-run-one" in lines
    assert "#SBATCH --no-requeue" in lines and "#SBATCH -p normal" in lines
    assert "#SBATCH -A %s" % ACCOUNT in lines, "the account is added when the options carry none"
    for good in ("-A acct-1 -c 4 --mem=26G -t 4-00:00:00", "--cpus-per-task=8 --mem=100M --time=12:00:00 --qos=normal",
                 "-c 2", ""):
        only_template_sbatch(render(ce=ce_snapshot(headJobOptions=good), facts=facts(slurm_account="acct-1" if "acct-1" in good else ACCOUNT))["files"]["head.sh"])


@pytest.mark.parametrize("bad", [
    "-c 4\n--wrap=touch c", "--wrap=touch c", "-c 4; touch c", "--chdir=/", "-D /", "--uid=0", "--gid=0", "-o /x", "-e /x",
    "-c 4\x00", "--mem=1T", "--mem=-1G", "-t forever", "-c four", "--export=ALL", "-A", "-p other", "--output=/x", "-c 4 -c 5"])
def test_tc014_other_head_job_options_are_refused_and_named(bad):
    # TC-014
    msg = refused(ce=ce_snapshot(headJobOptions=bad))
    assert "headJobOptions" in msg


def test_tc014_hostile_values_become_literal_text_or_are_refused(tmp_path):
    # TC-014: the render half. Nothing here is run by a shell except as quoted text; head.sh must parse.
    canary = tmp_path / "canary"
    hostile_params = {
        "a": "x'; touch %s; '" % canary, "b": "$(touch %s)" % canary, "c": "`touch %s`" % canary, "d": "${System.exit(1)}",
        "e": "line one\nsecond: key", "f": '!!python/object/apply:os.system ["touch %s"]' % canary, "g": "quote\" and \\ back",
        "h": "tab\there bell\x07 del\x7f", "i": "-" * 50, "j": "ünï ← 中文",
    }
    b = render(params=hostile_params)
    assert parse_yaml(b["files"]["params.yaml"]) == dict(
        hostile_params, input="/data/w1/runs/run-one/samplesheet.csv", outdir="/data/w1/runs/run-one/results")
    assert not canary.exists()
    cells = [["sample", "fastq_1"], ["a,b", "/data/storage/rawdata/ok.fq"], ['say "hi"', "/data/storage/rawdata/ok2.fq"],
             ["multi\nline", "/data/storage/rawdata/ok3.fq"], ["$(touch %s)" % canary, "/data/storage/rawdata/ok4.fq"]]
    b = render(samplesheet=cells)
    assert list(csv.reader(io.StringIO(b["files"]["samplesheet.csv"]))) == cells
    b = render(ce=ce_snapshot(environment=[
        {"name": "A", "value": "v $(touch %s) 'q' \"d\" `x`" % canary, "head": True, "compute": False}]))
    text = b["files"]["head.sh"]
    assert subprocess.run(["bash", "-n", "-c", text], capture_output=True).returncode == 0
    for ln in sbatch_lines(text):
        assert "touch" not in ln and "$(" not in ln
    only_template_sbatch(text)


@pytest.mark.parametrize("name", ["X;touch", "A B", "1A", "A-B", "A=B", ""])
def test_tc014_environment_names_must_be_shell_variable_names(name):
    # TC-014 (plan item 5 wrote capitals only; the proxy variables that ce_apply.sh puts into every environment are
    # http_proxy and https_proxy, so a lower-case name that is a plain shell variable name is exported, as literal text)
    refused(ce=ce_snapshot(environment=[{"name": name, "value": "v", "head": True, "compute": False}]))


def test_tc014_a_lower_case_variable_name_is_written_as_a_plain_export():
    b = render(ce=ce_snapshot(environment=[{"name": "https_proxy", "value": "http://p:1", "head": True, "compute": True}]))
    assert "export https_proxy=http://p:1\n" in b["files"]["head.sh"]


@pytest.mark.parametrize("value", ["a\nb", "a\x00b"])
def test_tc014_environment_values_with_a_newline_or_nul_are_refused(value):
    # TC-014
    msg = refused(ce=ce_snapshot(environment=[{"name": "A", "value": value, "head": True, "compute": False}]))
    assert "environment" in msg


def test_tc014_the_head_queue_is_judged_again():
    # TC-014
    refused(ce=ce_snapshot(headQueue="normal; touch c"))
    refused(ce=ce_snapshot(headQueue=""))


def test_tc013_names_the_variables_it_sets_itself_cannot_come_from_the_environment():
    # TC-013, TC-019: the token and the log file are not for a compute environment to set
    refused(ce=ce_snapshot(environment=[{"name": "TOWER_ACCESS_TOKEN", "value": "x", "head": True, "compute": False}]))
    refused(ce=ce_snapshot(environment=[{"name": "NXF_LOG_FILE", "value": "x", "head": True, "compute": False}]))


# ---- the account -------------------------------------------------------------------------------------

def test_tc021_the_account_must_be_set_and_must_agree_with_the_options():
    # TC-021, steps 1 to 4
    msg = refused(facts=facts(slurm_account=None))
    assert "帳號未設定" in msg and "slurm_account" in msg
    msg = refused(ce=ce_snapshot(headJobOptions="-A OTHER-ACCT -c 4"))
    assert "帳號與環境選項不一致" in msg and "OTHER-ACCT" in msg and ACCOUNT in msg
    b = render(ce=ce_snapshot(headJobOptions="-A %s -c 4" % ACCOUNT))
    assert sbatch_lines(b["files"]["head.sh"]).count("#SBATCH -A %s" % ACCOUNT) == 1
    b = render(ce=ce_snapshot(headJobOptions="-c 4"))
    assert "#SBATCH -A %s" % ACCOUNT in sbatch_lines(b["files"]["head.sh"])
    assert "export SLURM_ACCOUNT=%s" % ACCOUNT in b["files"]["head.sh"]


def test_tc021_a_compute_environment_that_carries_slurm_account_must_agree_too():
    # TC-021: ce_apply.sh puts SLURM_ACCOUNT into the environment list
    ok = ce_snapshot(environment=[{"name": "SLURM_ACCOUNT", "value": ACCOUNT, "head": True, "compute": True}])
    b = render(ce=ok)
    assert b["files"]["head.sh"].count("SLURM_ACCOUNT=") == 1
    bad = ce_snapshot(environment=[{"name": "SLURM_ACCOUNT", "value": "ELSEWHERE-1", "head": True, "compute": True}])
    assert "帳號與環境選項不一致" in refused(ce=bad)


@pytest.mark.parametrize("bad", ["a b", "a;b", "$(x)", "a" * 70, "名字"])
def test_tc021_a_strange_account_is_refused(bad):
    refused(facts=facts(slurm_account=bad))


# ---- names, versions, paths -----------------------------------------------------------------------------

@pytest.mark.parametrize("run", ["Bad", "1abc", "a/b", "..", "x;touch c", "-x", "a.b", "a" * 65, "", "a b", "a\nb", "A"])
def test_tc011_bad_run_names_are_refused_with_the_field_named(run):
    msg = refused(run_name=run)
    assert "run" in msg.lower()


@pytest.mark.parametrize("run", ["a", "a-b_c", "x" * 64, "run-one"])
def test_tc011_good_run_names_pass(run):
    assert render(run_name=run)["run_name"] == run


@pytest.mark.parametrize("rev", ["main", "master", "dev", "HEAD", "2", "1.2.3.4.5", "abc1234", "", "v", "2.18.0-rc1",
                                 "2.18.0 --foo", "A" * 40, "g" * 40])
def test_tc011_a_branch_or_an_unpinned_version_is_refused(rev):
    assert re.search(r"revision|版本", refused(revision=rev), re.I)


@pytest.mark.parametrize("rev", ["2.18.0", "v2.18.0", "1.2", "1.2.3.4", "0123456789abcdef0123456789abcdef01234567"])
def test_tc011_a_tag_or_a_full_commit_passes(rev):
    assert render(revision=rev)["revision"] == rev


@pytest.mark.parametrize("pipe", ["-hub/x", "../x", "./x", ".hidden/x", "nf-core/ampliseq --foo", "nf-core/ampliseq;ls",
                                  "nf core/x", "ampliseq", "a/b/c", "", "nf-core/..", "nf-core/.", "/x", "x/"])
def test_tc011_a_pipeline_is_owner_slash_name_and_nothing_else(pipe):
    assert re.search(r"pipeline|管線", refused(pipeline=pipe), re.I)


@pytest.mark.parametrize("pipe", ["nf-core/ampliseq", "nf-core/rnaseq", "a.b/c_d-e", "A1/B2"])
def test_tc011_good_pipelines_pass(pipe):
    render(pipeline=pipe)


@pytest.mark.parametrize("path", ["/etc/passwd", "/x/../y", "relative/path.fq", "/data/storage/rawdata/a b.fq",
                                  "/data/storage/rawdata/$(id).fq", "/data/elsewhere/a.fq", "/data/storage/../etc/x",
                                  "/data/storage/rawdata/a;b.fq", "/data/storage/rawdata/'q'.fq", "./here.fq"])
def test_tc011_a_sample_file_outside_the_read_roots_or_oddly_spelled_is_refused(path):
    msg = refused(samplesheet=[["sample", "fastq_1"], ["s1", path]])
    assert re.search(r"samplesheet|fastq_1", msg)


def test_tc011_an_empty_path_cell_in_a_path_column_is_allowed_for_single_end_data():
    # a samplesheet may leave fastq_2 empty
    b = render(samplesheet=[["sample", "fastq_1", "fastq_2"], ["s1", "/data/storage/rawdata/a.fq", ""]])
    assert "s1,/data/storage/rawdata/a.fq," in b["files"]["samplesheet.csv"]


def test_tc011_a_ragged_or_empty_samplesheet_is_refused():
    refused(samplesheet=[])
    refused(samplesheet=[["sample", "fastq_1"]])
    refused(samplesheet=[["sample", "fastq_1"], ["only-one"]])
    refused(samplesheet=[["sample", "fastq_1"], ["a", "/data/storage/x", "extra"]])


def test_tc011_the_path_columns_can_be_named():
    sheet = [["id", "reads"], ["s1", "relative.fq"]]
    refused(samplesheet=sheet, path_columns=["reads"])
    refused(samplesheet=[["id", "reads"], ["s1", "/etc/x"]])  # `reads` is a path column by name
    render(samplesheet=[["id", "note"], ["s1", "free text"]])


# ---- a column whose name ENDS in _file / _path is a path column (samplesheet-suffix-path-column) ------------


def test_suffix_path_column_is_judged():
    # TC-001
    msg = refused(samplesheet=[["id", "bam_path"], ["s1", "relative.fq"]])
    assert "samplesheet" in msg


def test_suffix_file_column_is_judged():
    # TC-002
    msg = refused(samplesheet=[["id", "reads_file"], ["s1", "relative.fq"]])
    assert "samplesheet" in msg


def test_suffix_match_is_case_insensitive():
    # TC-003
    refused(samplesheet=[["id", "BAM_PATH"], ["s1", "relative.fq"]])


def test_suffix_path_column_outside_roots_is_refused():
    # TC-004
    refused(samplesheet=[["id", "bam_path"], ["s1", "/etc/passwd"]])


def test_suffix_path_column_is_refused_like_reads():
    # TC-005: same value, only the column differs -> same reason
    a = refused(samplesheet=[["id", "reads"], ["s1", "relative.fq"]])
    b = refused(samplesheet=[["id", "bam_path"], ["s1", "relative.fq"]])
    assert re.sub(r"reads|bam_path", "COL", a) == re.sub(r"reads|bam_path", "COL", b), (a, b)


def test_suffix_path_column_inside_roots_passes():
    # TC-006
    b = render(samplesheet=[["id", "bam_path"], ["s1", "/data/storage/rawdata/s1.bam"]])
    assert "s1,/data/storage/rawdata/s1.bam" in b["files"]["samplesheet.csv"]
    assert "s1,/data/storage/rawdata/s1.bam" in files["samplesheet.csv"]


@pytest.mark.parametrize("col", ["profile", "filepath_note", "genome"])
def test_non_path_columns_are_not_judged(col):
    # TC-007, TC-008, TC-018 (genome is not in the usual names: the list was not widened)
    render(samplesheet=[["id", col], ["s1", "some/relative text"]])


def test_sample_column_is_not_judged():
    # TC-009
    render(samplesheet=[["sample", "note"], ["s1", "free/relative text"]])


# ---- characters that cannot be shown honestly ---------------------------------------------------------------

BAD_CHARS = ["\x00", "\r", "\x1b[2J", "\x1b[8m", "‮", "⁦", "⁧", "⁨", "⁩", "‪", "‏"]


@pytest.mark.parametrize("ch", BAD_CHARS)
def test_tc006_nul_cr_esc_and_bidi_controls_are_refused_in_a_sample_name_and_a_param_and_a_param_name(ch):
    # TC-006, part 1: refused when the bundle is built, and the field is named
    msg = refused(samplesheet=[["sample", "fastq_1"], ["a%sb" % ch, "/data/storage/rawdata/a.fq"]])
    assert "samplesheet" in msg
    msg = refused(params={"depth": "3%s" % ch})
    assert "depth" in msg
    refused(params={"na%sme" % ch: "v"})
    refused(run_name="a%s" % ch)


@pytest.mark.parametrize("ch", ["\x07", "\t", "\x7f", "\n"])
def test_tc006_other_control_characters_are_allowed_in_values(ch):
    # TC-006, part 2: they are shown escaped (see test_launch_cli.py); here they only have to survive the bundle
    b = render(params={"v": "a%sb" % ch})
    assert parse_yaml(b["files"]["params.yaml"])["v"] == "a%sb" % ch


def test_tc006_a_very_long_value_is_kept_whole_up_to_the_limit_and_refused_beyond_it():
    b = render(params={"v": "x" * 5000})
    assert parse_yaml(b["files"]["params.yaml"])["v"] == "x" * 5000
    refused(params={"v": "x" * 100001})


@pytest.mark.parametrize("name", ["a b", "a;b", "--x", "1a", "a-b", "", "a.b", "a" * 101])
def test_tc014_parameter_names_must_be_plain(name):
    refused(params={name: "v"})


@pytest.mark.parametrize("value", [None, [1], {"a": 1}, float("nan"), float("inf")])
def test_tc014_parameter_values_are_text_numbers_or_booleans(value):
    refused(params={"v": value})


# ---- what is not supported, said out loud ----------------------------------------------------------------------

def test_tc025_pre_and_post_run_scripts_are_refused_never_skipped():
    msg = refused(ce=ce_snapshot(preRunScript="echo hi"))
    assert "不支援：這一片不執行事前／事後腳本" in msg
    msg = refused(ce=ce_snapshot(postRunScript="echo bye"))
    assert "不支援：這一片不執行事前／事後腳本" in msg
    render(ce=ce_snapshot(preRunScript="  \n", postRunScript=""))


@pytest.mark.parametrize("key", ["outdir", "input"])
def test_tc025_outdir_and_input_are_fixed(key):
    msg = refused(params={key: "/somewhere"})
    assert key in msg
    if key == "outdir":
        assert "results" in msg


def test_tc025_without_them_outdir_is_results_under_the_run_folder():
    b = render()
    assert parse_yaml(b["files"]["params.yaml"])["outdir"] == b["run_folder"] + "/results"


def test_tc024_a_reverse_forward_needs_the_platform_on_the_same_machine():
    msg = refused(facts=facts(reach="ssh", platform_local=False, forward_file="/data/storage/_relay/forward_port"))
    assert re.search(r"同一台機器|same machine", msg)


def test_tc024_the_forward_file_must_be_a_plain_path():
    refused(facts=facts(reach="ssh", forward_file=None))
    refused(facts=facts(reach="ssh", forward_file="relative"))
    refused(facts=facts(reach="ssh", forward_file="/data/x y"))
    b = render(facts=facts(reach="ssh", forward_file="/data/storage/_relay/forward_port"))
    assert "/data/storage/_relay/forward_port" in b["files"]["head.sh"]


def test_tc062_there_is_no_resume_and_no_retry_in_the_script():
    text = render()["files"]["head.sh"]
    assert "-resume" not in text and "retry" not in text.lower()


def test_tc063_a_compute_environment_of_another_type_is_refused():
    refused(ce=ce_snapshot(platform="azcloud-platform"))      # aws-launch: AWS Batch can be launched now, so another type is the example


def test_tc013_the_script_is_a_single_template_in_one_module():
    # TC-052 (render half): the function the screen shows is the function the agent runs
    from abf_station import launch
    assert launch.render_bundle.__module__ == "abf_station.launch"


# ---- security F4: a name that ends in a newline is not a name -------------------------------------------------------

def test_security_f4_a_trailing_newline_is_refused_by_every_validator():
    nl = "\n"
    refused(run_name="run-one" + nl)
    refused(revision="2.18.0" + nl)
    refused(revision="0123456789abcdef0123456789abcdef01234567" + nl)
    refused(pipeline="nf-core/ampliseq" + nl)
    refused(pipeline="nf-core" + nl + "/ampliseq")
    refused(params={"depth" + nl: 1})
    refused(facts=facts(slurm_account=ACCOUNT + nl))
    refused(ce=ce_snapshot(headQueue="normal" + nl))
    refused(ce=ce_snapshot(workDir="/data/w1" + nl))
    refused(ce=ce_snapshot(environment=[{"name": "A" + nl, "value": "v", "head": True, "compute": False}]))
    refused(ce=ce_snapshot(headJobOptions="-t 1-00:00:00" + nl))
    refused(samplesheet=[["sample", "fastq_1"], ["s1", "/data/storage/rawdata/a.fq" + nl]])


def test_security_f4_the_other_validators_too():
    from abf_station import fetch, launch, rules
    from abf_platform import jobs, records
    assert not launch.TIME.fullmatch("1-00:00:00\n") and not launch.TIME.match("1-00:00:00\n")
    assert not launch.URL.match("http://127.0.0.1:8787\n")
    assert not records.name_ok(".nextflow.log\n") and not records.name_ok("trace-1.txt\n")
    assert not fetch._LOG.match(".nextflow.log\n") and not fetch._TRACE.match("trace-1.txt\n")
    assert not jobs._RUN_NAME.match("run-one\n") and not records._RUN_NAME.match("run-one\n")
    assert rules.path_problem("/data/w1\n") is not None
    try:
        rules.clean_queue("normal\n", "headQueue")
    except rules.Refusal:
        pass
    else:
        raise AssertionError("a queue name with a newline was accepted")
    from abf_platform import compute_envs, agents
    for rx in (compute_envs._NAME, compute_envs._QUEUE, compute_envs._PATH_CHARS, compute_envs._HOST, compute_envs._USER,
               compute_envs._CRED_NAME, compute_envs._ENV_NAME, agents._NAME):
        assert not rx.match("abc\n"), rx.pattern
    assert compute_envs.path_problem("/data/w1\n") is not None


# ---- launch-site-pipeline (M1-02): module load first, a site pipeline started from its home --------------------------------

SITE_CE = {"modules": ["biology/Nextflow/26.10.0"],
           "siteConfigVars": ["NFCORE_SITE_CONFIG", "NFCORE_SITE_REFERENCES"],
           "sitePipelines": [{"pipeline": "nf-core/ampliseq", "revision": "2.18.0",
                              "module": "biology/nf-core-ampliseq/2.18.0", "home": "NFCORE_AMPLISEQ_HOME"}]}
GOLDEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "golden_head_scripts.json")


def site_ce(**over):
    d = copy.deepcopy(SITE_CE)
    d.update(over)
    return ce_snapshot(**d)


def site_head(ce=None, **over):
    return render(ce=ce or site_ce(), **over)["files"]["head.sh"]


def last_line(script):
    return script.splitlines()[-1]


def test_tc_ls_01_03_a_site_pipeline_runs_from_its_home_without_r_and_after_module_load():
    # TC-LS-01, TC-LS-03 (test_tc013b_a_site_pipeline_runs_from_its_home_without_r_and_after_module_load)
    h = site_head()
    assert "module load biology/Nextflow/26.10.0" in h and "module load biology/nf-core-ampliseq/2.18.0" in h
    assert 'exec nextflow run "$NFCORE_AMPLISEQ_HOME"' in h and " -r " not in h
    lines = h.splitlines()
    mods = [i for i, ln in enumerate(lines) if ln.startswith("module ")]
    assert [lines[i] for i in mods] == ["module load biology/Nextflow/26.10.0 || exit 1",
                                        "module load biology/nf-core-ampliseq/2.18.0 || exit 1"]
    assert lines.index("umask 077") < mods[0] < mods[1] < len(lines) - 1
    assert h.count("nextflow run") == 1


def test_tc_ls_02_15_golden_for_a_hit_and_a_miss():
    # TC-LS-02, TC-LS-15, TC-LS-17
    golden = json.load(open(GOLDEN_FILE, encoding="utf-8"))
    assert site_head() == golden["nano4"]
    assert site_head(ce=site_ce(), revision="2.17.0") == golden["nano4-miss"]
    assert render()["files"]["head.sh"] == golden["local"]


def test_tc_ls_04_05_the_last_line_in_full_local_and_forward():
    # TC-LS-04, TC-LS-05
    assert last_line(site_head()) == ('exec nextflow run "$NFCORE_AMPLISEQ_HOME" -name run-one -params-file params.yaml '
                                      '-c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c nextflow.config '
                                      '-with-tower http://127.0.0.1:8787')
    fwd = site_head(facts=facts(reach="ssh", forward_file="/data/storage/_relay/forward_port"))
    assert last_line(fwd) == ('exec nextflow run "$NFCORE_AMPLISEQ_HOME" -name run-one -params-file params.yaml '
                              '-c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c nextflow.config '
                              '-with-tower "http://127.0.0.1:${ABF_FORWARD_PORT}"')
    assert "ABF_FORWARD_PORT=$(cat" in fwd


def run_site_head(tmp_path, bundle, fail_on=None, env_over=None):
    """head.sh with a stand-in `module` (logs its arguments, may fail) and a stand-in `nextflow`."""
    folder = tmp_path / "run"
    folder.mkdir()
    (folder / "tower.token").write_text("TOKEN_CANARY_f33d")
    text = bundle["files"]["head.sh"].replace(bundle["run_folder"], str(folder))
    (tmp_path / "head.sh").write_text(text)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "nextflow").write_text("#!/usr/bin/env python3\nimport json, os, sys\n"
                                     "json.dump(sys.argv[1:], open(os.environ['ABF_NF_OUT'], 'w'))\n")
    (bindir / "module").write_text('#!/bin/bash\necho "$@" >> "$ABF_MOD_LOG"\n'
                                   '[ -n "$ABF_MOD_FAIL" ] && [ "$2" = "$ABF_MOD_FAIL" ] && exit 3\nexit 0\n')
    for f in bindir.iterdir():
        f.chmod(0o755)
    env = {"PATH": str(bindir) + os.pathsep + os.environ["PATH"], "HOME": str(tmp_path), "ABF_NF_OUT": str(tmp_path / "nf.json"),
           "ABF_MOD_LOG": str(tmp_path / "mod.log"), "ABF_MOD_FAIL": fail_on or "",
           "NFCORE_AMPLISEQ_HOME": "/opt/x y/ampliseq", "NFCORE_SITE_CONFIG": "/s/site.config",
           "NFCORE_SITE_REFERENCES": "/s/refs.config"}
    env.update(env_over or {})
    r = subprocess.run(["bash", str(tmp_path / "head.sh")], env=env, capture_output=True, text=True, timeout=60)
    mods = (tmp_path / "mod.log").read_text().splitlines() if (tmp_path / "mod.log").exists() else []
    nf = json.load(open(tmp_path / "nf.json")) if (tmp_path / "nf.json").exists() else None
    return r, mods, nf


def test_tc_ls_06_the_script_runs_modules_then_nextflow_with_the_homes_path(tmp_path):
    # TC-LS-06
    b = render(ce=site_ce())
    r, mods, nf = run_site_head(tmp_path, b)
    assert r.returncode == 0, r.stdout + r.stderr
    assert nf == ["run", "/opt/x y/ampliseq", "-name", "run-one", "-params-file", "params.yaml", "-c", "/s/site.config", "-c",
                  "/s/refs.config", "-c", "nextflow.config", "-with-tower", "http://127.0.0.1:8787"]
    assert mods == ["load biology/Nextflow/26.10.0", "load biology/nf-core-ampliseq/2.18.0"]
    assert subprocess.run(["bash", "-n", "-c", b["files"]["head.sh"]], capture_output=True).returncode == 0


def test_tc_ls_21_22_61_a_module_that_will_not_load_stops_the_job_and_nextflow_never_runs(tmp_path):
    # TC-LS-21, TC-LS-61
    b = render(ce=site_ce())
    r, mods, nf = run_site_head(tmp_path, b, fail_on="biology/nf-core-ampliseq/2.18.0")
    assert r.returncode != 0 and nf is None and len(mods) == 2
    # TC-LS-22
    (tmp_path / "second").mkdir()
    r, mods, nf = run_site_head(tmp_path / "second", b, fail_on="biology/Nextflow/26.10.0")
    assert r.returncode != 0 and nf is None and mods == ["load biology/Nextflow/26.10.0"]


def test_tc_ls_07_pipeline_source_of_a_hit_and_a_miss():
    # TC-LS-07, TC-LS-14, TC-LS-18, TC-LS-19
    assert render(ce=site_ce())["pipeline_source"] == {"kind": "site-module", "module": "biology/nf-core-ampliseq/2.18.0",
                                                       "home": "NFCORE_AMPLISEQ_HOME"}
    b = render(ce=site_ce(), revision="2.17.0")
    assert b["pipeline_source"] == {"kind": "remote"}
    assert last_line(b["files"]["head.sh"]) == ('exec nextflow run nf-core/ampliseq -r 2.17.0 -name run-one -params-file params.yaml '
                                                '-c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c nextflow.config '
                                                '-with-tower http://127.0.0.1:8787')
    assert "module load biology/Nextflow/26.10.0" in b["files"]["head.sh"]
    assert "nf-core-ampliseq" not in b["files"]["head.sh"] and "NFCORE_AMPLISEQ_HOME" not in b["files"]["head.sh"]
    other = render(ce=site_ce(), pipeline="nf-core/rnaseq")
    assert other["pipeline_source"] == {"kind": "remote"} and "nf-core/rnaseq -r 2.18.0" in last_line(other["files"]["head.sh"])
    for ce in (site_ce(sitePipelines=[]), {k: v for k, v in site_ce().items() if k != "sitePipelines"}):
        h = render(ce=ce)["files"]["head.sh"]
        assert "nf-core/ampliseq -r 2.18.0" in last_line(h) and "NFCORE_AMPLISEQ_HOME" not in h


def test_tc_ls_08_09_config_flags_come_only_from_site_config_vars():
    # TC-LS-08
    ln = last_line(site_head(ce=site_ce(siteConfigVars=["B_CFG", "A_CFG", "C_CFG"])))
    assert '-c "$B_CFG" -c "$A_CFG" -c "$C_CFG" -c nextflow.config' in ln and "NFCORE_SITE" not in ln
    # TC-LS-09
    h = site_head(ce=site_ce(siteConfigVars=[]))
    assert last_line(h) == ('exec nextflow run "$NFCORE_AMPLISEQ_HOME" -name run-one -params-file params.yaml -c nextflow.config '
                            '-with-tower http://127.0.0.1:8787') and "NFCORE_SITE" not in h


def test_tc_ls_10_13_first_duplicate_wins_and_homes_come_from_the_ce():
    # TC-LS-10
    sp = [dict(SITE_CE["sitePipelines"][0], module="m/first", home="FIRST_HOME"),
          dict(SITE_CE["sitePipelines"][0], module="m/second", home="SECOND_HOME")]
    b = render(ce=site_ce(sitePipelines=sp))
    assert b["pipeline_source"]["module"] == "m/first" and "module load m/first" in b["files"]["head.sh"]
    assert "SECOND_HOME" not in b["files"]["head.sh"] and "m/second" not in b["files"]["head.sh"]
    # TC-LS-13
    rna = dict(pipeline="nf-core/rnaseq", revision="3.14.0", module="biology/nf-core-rnaseq/3.14.0", home="NFCORE_RNASEQ_HOME")
    h = site_head(ce=site_ce(sitePipelines=SITE_CE["sitePipelines"] + [rna]), pipeline="nf-core/rnaseq", revision="3.14.0")
    assert "module load biology/nf-core-rnaseq/3.14.0" in h and 'exec nextflow run "$NFCORE_RNASEQ_HOME"' in h
    assert "NFCORE_AMPLISEQ_HOME" not in h and "nf-core-ampliseq" not in h


def test_tc_ls_11_58_56_57_only_the_head_script_changes_and_no_queue_profile_or_nfcore_submit():
    # TC-LS-11, TC-LS-58
    plain, site_b = render(), render(ce=site_ce())
    for name in ("samplesheet.csv", "params.yaml", "nextflow.config"):
        assert plain["files"][name] == site_b["files"][name]
    assert sbatch_lines(plain["files"]["head.sh"]) == sbatch_lines(site_b["files"]["head.sh"])
    assert site_b["pipeline"] == "nf-core/ampliseq" and site_b["revision"] == "2.18.0"
    # TC-LS-56, TC-LS-57
    for b in (site_b, render(ce=site_ce(), revision="2.17.0")):
        assert "-profile" not in b["files"]["head.sh"]
        assert "nfcore-submit" not in json.dumps(b)


def test_tc_ls_16_20_without_site_keys_the_script_is_the_old_one_with_modules_one_line_more():
    # TC-LS-16
    b = render()
    assert b["pipeline_source"] == {"kind": "remote"} and "module" not in b["files"]["head.sh"]
    # TC-LS-20
    only = render(ce=ce_snapshot(modules=["biology/Nextflow/26.10.0"]))["files"]["head.sh"].splitlines()
    base = b["files"]["head.sh"].splitlines()
    i = base.index("umask 077")
    assert only == base[:i + 1] + ["module load biology/Nextflow/26.10.0 || exit 1"] + base[i + 1:]


def test_tc_ls_24_25_snapshot_ce_carries_the_three_keys():
    from abf_station import launch
    view = {"name": "n", "platform": "slurm-platform", "config": {"workDir": "/data/w1", "headQueue": "normal"}}
    s = launch.snapshot_ce(view)
    assert s["modules"] == [] and s["siteConfigVars"] == [] and s["sitePipelines"] == []
    view["config"].update(copy.deepcopy(SITE_CE))
    s = launch.snapshot_ce(view)
    for k, v in SITE_CE.items():
        assert s[k] == v
    assert s["workDir"] == "/data/w1" and s["headQueue"] == "normal" and s["environment"] == []


@pytest.mark.parametrize("key,bad", [("modules", ["a;b"]), ("modules", ["a b"]), ("modules", ["$(id)"]), ("modules", [""]),
                                     ("modules", ["x/../y"]), ("modules", [5]), ("modules", "biology/Nextflow/26.10.0"),
                                     ("modules", ["a\n"]), ("siteConfigVars", ["lower_case"]), ("siteConfigVars", ["A;B"]),
                                     ("siteConfigVars", ["1ABC"]), ("siteConfigVars", [""]), ("siteConfigVars", "NFCORE_SITE_CONFIG"),
                                     ("siteConfigVars", ["A\n"])])
def test_tc_ls_28_29_30_32_35_bad_modules_and_variables_are_refused_naming_the_key(key, bad):
    msg = refused(key, ce=site_ce(**{key: bad}))
    assert "Traceback" not in msg and ".py" not in msg and "/home" not in msg


@pytest.mark.parametrize("sp", [
    [dict(SITE_CE["sitePipelines"][0], home="x;y")], [dict(SITE_CE["sitePipelines"][0], home="lower")],
    [dict(SITE_CE["sitePipelines"][0], home='X"; touch /tmp/pwn; "')], [dict(SITE_CE["sitePipelines"][0], module="a;b")],
    [dict(SITE_CE["sitePipelines"][0], module="a\n")], [dict(SITE_CE["sitePipelines"][0], home="A\n")],
    [{"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "module": "m"}],
    [dict(SITE_CE["sitePipelines"][0], extra="x")], ["not an object"], "not a list"])
def test_tc_ls_31_32_bad_site_pipelines_are_refused_naming_the_key(sp):
    refused("sitePipelines", ce=site_ce(sitePipelines=sp))


def test_tc_ls_34_scripts_are_still_refused_when_modules_exist():
    refused("事前|腳本|script", ce=site_ce(preRunScript="module load evil"))


def test_tc_ls_46_the_hash_covers_pipeline_source():
    from abf_platform import common
    hit, miss = render(ce=site_ce()), render(ce=site_ce(), revision="2.17.0")
    assert common.bundle_sha256(hit) != common.bundle_sha256(miss)
    alt = copy.deepcopy(hit)
    alt["pipeline_source"] = {"kind": "remote"}
    assert common.bundle_sha256(alt) != common.bundle_sha256(hit)


def test_tc_ls_36_37_38_a_resume_of_a_site_run_starts_from_the_same_place():
    from abf_station import launch
    sid = "0b1c2d3e-4f50-4a6b-8c7d-9e0f1a2b3c4d"
    origin = render(ce=site_ce())
    h2 = launch.render_resume(origin=origin, run_name="run-one-a2", attempt=2, session_id=sid)["head-2.sh"]
    assert "module load biology/Nextflow/26.10.0" in h2 and "module load biology/nf-core-ampliseq/2.18.0" in h2
    assert '"$NFCORE_AMPLISEQ_HOME"' in h2 and " -r " not in h2
    ln = last_line(h2)
    assert "-resume %s" % sid in ln and "-name run-one-a2" in ln
    assert ln.endswith('-c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c nextflow.config -with-tower http://127.0.0.1:8787')
    a, b = origin["files"]["head.sh"].splitlines(), h2.splitlines()
    assert [i for i, (x, y) in enumerate(zip(a, b)) if x != y] == [2, len(a) - 1] and len(a) == len(b)
    # TC-LS-38
    miss = render(ce=site_ce(), revision="2.17.0")
    m2 = launch.render_resume(origin=miss, run_name="run-one-a2", attempt=2, session_id=sid)["head-2.sh"]
    assert "module load biology/Nextflow/26.10.0" in m2 and "nf-core-ampliseq" not in m2
    assert last_line(m2).startswith("exec nextflow run nf-core/ampliseq -r 2.17.0 -resume %s -name " % sid)


def test_tc_ls_40_an_origin_from_before_the_site_keys_resumes_from_the_remote():
    from abf_station import launch
    sid = "0b1c2d3e-4f50-4a6b-8c7d-9e0f1a2b3c4d"
    origin = render()
    for k in ("modules", "siteConfigVars", "sitePipelines"):
        origin["ce"].pop(k)
    origin.pop("pipeline_source")
    h2 = launch.render_resume(origin=origin, run_name="run-one-a2", attempt=2, session_id=sid)["head-2.sh"]
    assert "module" not in h2 and last_line(h2).startswith("exec nextflow run nf-core/ampliseq -r 2.18.0 -resume ")


def test_tc_ls_53_55_no_secret_and_no_site_names_in_the_code(tmp_path):
    # TC-LS-53
    r, mods, nf = run_site_head(tmp_path, render(ce=site_ce()))
    assert "TOKEN_CANARY_f33d" not in render(ce=site_ce())["files"]["head.sh"]
    # TC-LS-55
    src = open(os.path.join(PLATFORM_DIR, "abf_station", "launch.py"), encoding="utf-8").read()
    src += open(os.path.join(PLATFORM_DIR, "abf_station", "rules.py"), encoding="utf-8").read()
    for word in ("nano4", "NCHC", "NFCORE_", "biology/", "nfcore-submit"):
        assert word not in src, word


# ---- 017d: a composed pipeline is started from the project the bundle carries (spec 017d, TC-085 ... TC-107) -----------------------

COMPOSED_PROJECT = {"main.nf": "workflow {\n}\n", "nextflow.config": "manifest {\n}\n", "modules.json": "{}\n",
                    "modules/nf-core/fastqc/main.nf": "process FASTQC {\n}\n"}


def composed_over(project=None, **over):
    d = dict(ce=site_ce(), pipeline="abf-composed/demo-qc", revision="0.1.0",
             composed={"pipeline_id": 7, "version": 1, "project": copy.deepcopy(COMPOSED_PROJECT if project is None else project)})
    d.update(over)
    return d


def render_composed(project=None, **over):
    return render(**composed_over(project, **over))


def test_tc085_without_composed_the_bundle_is_the_one_of_before():
    # TC-085 (the existing goldens and hashes stay as they are; this one says it in a sentence)
    assert render(composed=None) == render()
    assert "project" not in render() and "project" not in render(ce=site_ce())


def test_tc086_087_088_the_pipeline_and_revision_shapes_of_a_composed_launch():
    # TC-086, TC-087, TC-088
    for pipeline in ("nf-core/ampliseq", "abf-composed", "other/demo-qc"):
        refused("pipeline", **composed_over(pipeline=pipeline))
    for pipeline in ("abf-composed/", "abf-composed/-x", "abf-composed/a b", "abf-composed/a/b"):
        refused(None, **composed_over(pipeline=pipeline))
    for revision in ("1.0.0", "0.2.0", "0.1", "0.1.0 ", "v0.1.0", "main"):
        refused(None, **composed_over(revision=revision))
    ok = render_composed()
    assert ok["pipeline"] == "abf-composed/demo-qc" and ok["revision"] == "0.1.0"
    three = render_composed(revision="0.3.0", composed={"pipeline_id": 7, "version": 3, "project": copy.deepcopy(COMPOSED_PROJECT)})
    assert three["revision"] == "0.3.0"


def test_tc089_171_the_bundle_of_a_composed_launch_has_the_project_and_a_four_key_source():
    # TC-089 (the keys), TC-171 (a mapping of text, no archive)
    from abf_platform import common
    import hashlib
    b, plain = render_composed(), render()
    assert set(b) - set(plain) == {"project"} and set(plain) - set(b) == set()
    assert b["project"] == COMPOSED_PROJECT
    assert b["pipeline_source"] == {"kind": "composed", "pipeline_id": 7, "version": 1,
                                    "project_sha256": hashlib.sha256(common.canonical_json(COMPOSED_PROJECT)).hexdigest()}
    assert not [k for k in b if "tar" in k] and all(isinstance(v, str) for v in b["project"].values())


def test_tc091_107_the_records_and_the_bundle_version_are_those_of_before():
    # TC-091, TC-107
    from abf_station import launch
    assert launch.RECORDS == ("upload_paths", "relaunch")
    assert launch.LAUNCH_KEYS == {"bundle", "confirmation_id", "bundle_sha256"}
    assert launch.BUNDLE_VERSION == 1 and render_composed()["version"] == 1


COMPOSED_LAST = ('exec nextflow run /data/w1/runs/run-one/pipeline/main.nf -name run-one -params-file params.yaml '
                 '-c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c /data/w1/runs/run-one/pipeline/nextflow.config '
                 '-c nextflow.config -with-tower http://127.0.0.1:8787')


def test_tc092_to_095_the_head_script_of_a_composed_launch():
    # TC-092 (the last line in full), TC-093 (module load), TC-094 (no -r), TC-095 (the order of -c)
    h = render_composed()["files"]["head.sh"]
    assert last_line(h) == COMPOSED_LAST
    lines = h.splitlines()
    assert [ln for ln in lines if ln.startswith("module ")] == ["module load biology/Nextflow/26.10.0 || exit 1"]
    assert " -r " not in h and h.count("nextflow run") == 1
    tail = last_line(h)
    i = [tail.index(x) for x in ('-c "$NFCORE_SITE_CONFIG"', '-c "$NFCORE_SITE_REFERENCES"', "-c /data/w1/runs/run-one/pipeline/nextflow.config",
                                  "-c nextflow.config", "-with-tower http://127.0.0.1:8787")]
    assert i == sorted(i)
    only_template_sbatch(h)


def test_tc096_the_golden_file_has_the_composed_script_and_the_others_are_as_before():
    # TC-096
    golden = json.load(open(GOLDEN_FILE, encoding="utf-8"))
    assert sorted(golden) == ["composed", "forward", "local", "nano4", "nano4-miss"]
    assert render_composed()["files"]["head.sh"] == golden["composed"]
    assert site_head() == golden["nano4"] and render()["files"]["head.sh"] == golden["local"]


def test_tc097_a_site_pipeline_of_the_same_name_does_not_take_a_composed_launch():
    # TC-097
    hit = dict(SITE_CE["sitePipelines"][0], pipeline="abf-composed/ampliseq", revision="0.1.0", module="m/hijack", home="HIJACK_HOME")
    b = render_composed(ce=site_ce(sitePipelines=SITE_CE["sitePipelines"] + [hit]), pipeline="abf-composed/ampliseq")
    assert b["pipeline_source"]["kind"] == "composed"
    h = b["files"]["head.sh"]
    assert "m/hijack" not in h and "HIJACK_HOME" not in h and "/pipeline/main.nf" in last_line(h)


BAD_KEYS = ["../x", "/abs/main.nf", "a\\b", "modules/nf-core/x/bin/run.sh", "other/main.nf", "modules/nf-core/a/../../b/main.nf",
            "pipeline/../x", "modules/nf-core/a/meta.yml", "modules/nf-core/A/main.nf", "main.nf/", "modules.json.bak", ""]


@pytest.mark.parametrize("key", BAD_KEYS)
def test_tc098_a_project_key_of_a_bad_shape_is_refused_by_name(key):
    # TC-098
    project = dict(COMPOSED_PROJECT)
    project[key] = "x\n"
    msg = refused(None, **composed_over(project))
    assert (key or "''") in msg or repr(key) in msg


@pytest.mark.parametrize("bad", ["a\x00b", "a\x1bb", "a\rb", "a‮b"])
def test_tc099_control_characters_in_a_project_file_are_refused_by_name(bad):
    # TC-099
    project = dict(COMPOSED_PROJECT, **{"modules/nf-core/fastqc/main.nf": bad})
    assert "modules/nf-core/fastqc/main.nf" in refused(None, **composed_over(project))


def test_tc100_one_file_is_at_most_200000_characters():
    # TC-100
    ok = dict(COMPOSED_PROJECT, **{"modules/nf-core/fastqc/main.nf": "y" * 200000})
    assert render_composed(ok)["project"]["modules/nf-core/fastqc/main.nf"] == "y" * 200000
    over = dict(COMPOSED_PROJECT, **{"modules/nf-core/fastqc/main.nf": "y" * 200001})
    assert "modules/nf-core/fastqc/main.nf" in refused(None, **composed_over(over))


def _sized(total):
    base = {"main.nf": "m", "nextflow.config": "c", "modules.json": "j"}
    left = total - 3
    i = 0
    while left > 0:
        n = min(200000, left)
        base["modules/nf-core/m%d/main.nf" % i] = "z" * n
        left -= n
        i += 1
    return base


def test_tc101_the_whole_project_is_at_most_2_mib():
    # TC-101
    limit = 2 * 1024 * 1024
    ok = _sized(limit)
    assert sum(len(v.encode("utf-8")) for v in ok.values()) == limit
    assert render_composed(ok)["project"] == ok
    over = _sized(limit + 1)
    assert sum(len(v.encode("utf-8")) for v in over.values()) == limit + 1
    refused(None, **composed_over(over))


def test_tc102_a_project_has_at_most_2000_files():
    # TC-102
    def many(n):
        p = {"main.nf": "m", "nextflow.config": "c", "modules.json": "j"}
        p.update({"modules/nf-core/m%d/main.nf" % i: "x" for i in range(n - 3)})
        return p
    assert len(render_composed(many(2000))["project"]) == 2000
    refused(None, **composed_over(many(2001)))


@pytest.mark.parametrize("gone", ["main.nf", "nextflow.config"])
def test_tc103_main_and_config_must_be_there(gone):
    # TC-103
    project = {k: v for k, v in COMPOSED_PROJECT.items() if k != gone}
    assert gone in refused(None, **composed_over(project))


@pytest.mark.parametrize("bad", [12, b"bytes", None, ["x"]])
def test_tc104_a_project_value_must_be_text(bad):
    # TC-104
    project = dict(COMPOSED_PROJECT, **{"modules.json": bad})
    assert "modules.json" in refused(None, **composed_over(project))
    refused(None, **composed_over("not a mapping"))


def test_tc106_a_composed_origin_is_not_resumed():
    # TC-106
    from abf_station import launch
    origin = render_composed()
    with pytest.raises(launch.BundleError) as e:
        launch.render_resume(origin=origin, run_name="run-one-a2", attempt=2, session_id="12345678-1234-1234-1234-123456789abc")
    assert "run" in str(e.value) and re.search(r"[一-鿿]", str(e.value))
    with pytest.raises(launch.BundleError):
        launch.render_resume_bundle(origin=origin, run_name="run-one-a2", attempt=2, session_id="12345678-1234-1234-1234-123456789abc",
                                    of_run="run-one", of_slurm_job_id=5)
