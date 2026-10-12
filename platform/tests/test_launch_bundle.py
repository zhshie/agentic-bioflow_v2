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
    assert b["files"]["nextflow.config"] == "process.executor = 'slurm'\n"
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
    refused(ce=ce_snapshot(platform="awsbatch-platform"))


def test_tc013_the_script_is_a_single_template_in_one_module():
    # TC-052 (render half): the function the screen shows is the function the agent runs
    from abf_station import launch
    assert launch.render_bundle.__module__ == "abf_station.launch"
