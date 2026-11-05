# Nothing existing: tests of what the platform writes for a resume (the files Nextflow's cache hashes are built from) and of the small hash-diff script; the invariants are this task's own, no library says "a resume changes only what it must".
"""resume-cache-miss: a resume with edits must differ from the first launch only where the edit is (hypotheses H1-H5 of
specs/resume-cache-miss/plan.md), and scripts/nf_hash_diff.py names the first field that differs between two hash logs.
Test cases are named in the comments (TC-001 ...), see specs/resume-cache-miss/test-case.md."""
import copy
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from resume_harness import SESSION, FakePerson, Rig
from test_launch_bundle import inputs, site_ce
from test_resume_edit_params_station import last_line

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "nf_hash_diff.py"
# every kind of scalar the params file writes, the awkward ones included
PARAMS = {"primer": "AGRG", "pacbio": True, "depth": 3, "min_cov": 1e-05, "ratio": 0.25, "off": False,
          "label": 'say "hi" \\ there', "name_zh": "樣本 é", "cutoff": 2.5e10}


def origin_bundle(**over):
    from abf_station import launch
    kw = inputs(ce=site_ce(), params=copy.deepcopy(PARAMS))
    kw.update(over)
    return launch.render_bundle(**kw)


def resume_files(origin, overrides=None, attempt=2):
    from abf_station import launch
    return launch.render_resume(origin=origin, run_name="run-one-a%d" % attempt, attempt=attempt, session_id=SESSION, overrides=overrides)


def head_of(files, attempt=2):
    return files["head-%d.sh" % attempt]


# ---- US1: what a resume writes ---------------------------------------------------------------------------------------------------------

def test_resume_without_edit_reuses_origin_files():
    # TC-001, TC-002
    o = origin_bundle()
    files = resume_files(o)
    assert list(files) == ["head-2.sh"]                       # no params-2.yaml, no extra-2.config; params.yaml and nextflow.config stay
    old, new = o["files"]["head.sh"].splitlines(), files["head-2.sh"].splitlines()
    assert len(old) == len(new)
    diff = [(a, b) for a, b in zip(old, new) if a != b]
    assert len(diff) == 2                                      # the job name line and the nextflow line, nothing else
    assert diff[0] == ("#SBATCH -J nf-run-one", "#SBATCH -J nf-run-one-a2")
    assert last_line(o["files"]["head.sh"]).replace(" -name run-one", " -resume %s -name run-one-a2" % SESSION) == last_line(files["head-2.sh"])


def test_resume_with_param_edit_keeps_unchanged_params_byte_identical():
    # TC-003, TC-004, TC-005 (H1, H2)
    o = origin_bundle()
    files = resume_files(o, {"params": {"depth": 4}})
    old, new = o["files"]["params.yaml"].splitlines(), files["params-2.yaml"].splitlines()
    assert len(old) == len(new)
    diff = [(a, b) for a, b in zip(old, new) if a != b]
    assert diff == [("depth: 3", "depth: 4")]
    for key in ("min_cov", "cutoff", "off", "pacbio", "label", "name_zh", "ratio", "primer", "input", "outdir"):
        a = [x for x in old if x.startswith(key + ":")]
        b = [x for x in new if x.startswith(key + ":")]
        assert a and a == b, key
    assert "min_cov: 1e-05" in new
    # H2: the same two strings, not a normalised form of them
    assert 'input: "%s/samplesheet.csv"' % o["run_folder"] in new and 'outdir: "%s/results"' % o["run_folder"] in new


def test_resume_params_yaml_matches_origin_render():
    # TC-006
    from abf_station import launch
    o = origin_bundle()
    assert launch._params_yaml(o["params"], o["run_folder"]) == o["files"]["params.yaml"]


def test_resume_head_differs_only_in_allowed_flags():
    # TC-007 (H3)
    o = origin_bundle()
    files = resume_files(o, {"params": {"depth": 4}, "extra_config": "process.memory = '16 GB'"})
    new = last_line(head_of(files)).split(" ")
    for flag in ("-name", "-resume", "-params-file"):
        i = new.index(flag)
        del new[i:i + 2]
    i = new.index("extra-2.config")
    assert new[i - 1] == "-c"
    del new[i - 1:i + 1]
    old = last_line(o["files"]["head.sh"]).split(" ")
    for flag in ("-name", "-params-file"):
        i = old.index(flag)
        del old[i:i + 2]
    assert new == old
    # the site config and tower stay, and the extra file comes after nextflow.config
    line = last_line(head_of(files))
    assert '-c "$NFCORE_SITE_CONFIG"' in line and line.index("-c nextflow.config") < line.index("-c extra-2.config") and "-with-tower" in line
    # every line above the last is what the first launch had, but the job name
    assert [x for x in head_of(files).splitlines()[:-1] if "-J" not in x] == [x for x in o["files"]["head.sh"].splitlines()[:-1] if "-J" not in x]


@pytest.mark.parametrize("overrides", [None, {"params": {"depth": 4}}, {"extra_config": "process.memory = '16 GB'"},
                                       {"params": {"depth": 4}, "extra_config": "process.memory = '16 GB'"}])
def test_resume_env_and_modules_match_origin(overrides):
    # TC-009 (H4)
    o = origin_bundle()
    pick = lambda text: sorted(x for x in text.splitlines() if x.startswith(("module load", "export ")))
    assert any(x.startswith("module load") for x in pick(o["files"]["head.sh"])) and any(x.startswith("export ") for x in pick(o["files"]["head.sh"]))
    assert pick(head_of(resume_files(o, overrides))) == pick(o["files"]["head.sh"])


def test_resume_extra_config_has_no_hash_affecting_keys():
    # TC-010, TC-011, TC-012 (H5)
    o = origin_bundle()
    assert "extra-2.config" not in resume_files(o) and "extra-2.config" not in resume_files(o, {"params": {"depth": 4}})
    user = "process.memory = '16 GB'"
    text = resume_files(o, {"extra_config": user})["extra-2.config"]
    lines = text.splitlines()
    assert lines[0].startswith("// added by the platform") and "\n".join(lines[1:]) == user
    assert not re.search(r"container|\benv\b|ext\.args|beforeScript|containerOptions", "\n".join(l for l in lines if l.startswith("//")))
    assert not re.search(r"container|\benv\b|ext\.args", text)


def test_resume_unconfirmed_changes_nothing(tmp_path, monkeypatch):
    # TC-013: no yes (declined, or no way to ask) -> no new job, no launch row, no confirmed confirmation
    rig = Rig(tmp_path, monkeypatch)
    rig.first("x")
    before = rig.counts()
    declined = rig.ask("resume", "x", person=FakePerson(False))
    assert declined["sent"] is False
    pending = rig.ask("resume", "x", person=FakePerson(None))
    assert pending["sent"] is False
    assert len(rig.jobs()) == before[0] and len(rig.launches()) == before[2]
    assert all(c["state"] != "confirmed" for c in rig.confirmations()[before[1]:])


# ---- US3: scripts/nf_hash_diff.py ------------------------------------------------------------------------------------------------------

FQ_LINE = "  c0ff3a1b2c3d4e5f60718293a4b5c6d7  [nextflow.util.ArrayBag] [FileHolder(sourceObj:%s, storePath:%s, stageName:reads.fq)]"


def hash_log(container="quay.io/biocontainers/fastqc:0.12.1--hdfd78af_0", script="fastqc -q reads.fq\nmv a b", fq="/data/s1.fq", tasks=("s1", "s2"), drop_input=False):
    """A made-up log in the shape of Nextflow's 'cache hash' block (see the header of scripts/nf_hash_diff.py for the source of the shape)."""
    out = ["Nov-04 10:00:00.001 [main] DEBUG nextflow.Session - Session UUID: 0b1c2d3e"]
    for t in tasks:
        out += ["Nov-04 10:00:01.123 [Actor Thread 5] INFO  nextflow.processor.TaskProcessor - [FASTQC (%s)] cache hash: 5f8e9a; mode: STANDARD; entries:" % t,
                "  d3f6a1b2c3d4e5f60718293a4b5c6d7e  [java.util.UUID] 0b1c2d3e-4f50-4a6b-8c7d-9e0f1a2b3c4d",
                "  7c4d1a2b3c4d5e6f708192a3b4c5d6e7  [java.lang.String] NFCORE_AMPLISEQ:AMPLISEQ:FASTQC",
                "  9a10b2c3d4e5f60718293a4b5c6d7e8f  [java.lang.String] " + script,
                "  b27e0a1b2c3d4e5f60718293a4b5c6d7e  [java.lang.String] " + container]
        if not drop_input:
            out.append(FQ_LINE % (fq, fq))
        out.append("Nov-04 10:00:02.000 [Actor Thread 5] INFO  nextflow.Session - something else")
    return "\n".join(out) + "\n"


def run_script(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT)] + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
    assert "Traceback" not in r.stdout + r.stderr
    return r


def run_diff(tmp_path, a, b):
    pa, pb = tmp_path / "a.log", tmp_path / "b.log"
    pa.write_text(a, encoding="utf-8")
    pb.write_text(b, encoding="utf-8")
    return run_script([pa, pb])


def test_nf_hash_diff_reports_first_difference(tmp_path):
    # TC-031: only the container differs
    r = run_diff(tmp_path, hash_log(), hash_log(container="quay.io/biocontainers/fastqc:0.12.2--zzz"))
    assert r.returncode == 1 and "container" in r.stdout.split("\n")[0]
    # TC-032: the same
    r = run_diff(tmp_path, hash_log(), hash_log())
    assert r.returncode == 0 and "無差異" in r.stdout and "container" not in r.stdout
    # TC-033: two differ; the earlier one in the log is named (container comes before the input)
    r = run_diff(tmp_path, hash_log(), hash_log(container="quay.io/x/y:2", fq="/data/other.fq"))
    assert "container" in r.stdout.split("\n")[0] and "input" not in r.stdout.split("\n")[0]
    # the script comes before the container
    r = run_diff(tmp_path, hash_log(), hash_log(container="quay.io/x/y:2", script="fastqc -q other.fq"))
    assert "script" in r.stdout.split("\n")[0]


def test_nf_hash_diff_missing_field_and_unknown_format_say_what_and_what_next(tmp_path):
    # TC-034, TC-036: an entry missing in the second file
    r = run_diff(tmp_path, hash_log(), hash_log(drop_input=True))
    assert r.returncode != 0 and "少了" in r.stdout and "截斷" in r.stdout
    # TC-035, TC-036: text that is not a hash log
    r = run_diff(tmp_path, "just some text\nno hashes here\n", hash_log())
    assert r.returncode == 2 and "格式不認得" in r.stderr and "a.log" in r.stderr and ".nextflow.log" in r.stderr
    # a file that is not there
    r = run_script([tmp_path / "nope.log", tmp_path / "nope2.log"])
    assert r.returncode == 2 and "cp" in r.stderr
    r = run_script([])
    assert r.returncode == 2
