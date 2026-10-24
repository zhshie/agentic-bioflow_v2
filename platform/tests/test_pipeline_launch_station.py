# Nothing existing: tests that hand the real station agent a composed pipeline's launch job and watch a fake site (spec 017d); the bundle and the site are ours.
"""017d: what the agent does with a confirmed launch of a composed pipeline: it builds the bundle again from its own settings, writes the
project into the run's own `pipeline/` folder in the same unpack as the other files, and submits once. Test cases are named in the
comments (TC-109 ...), see specs/017d-launch-composed/test-case.md."""
import copy
import json
import os
import re
import stat

import pytest

from station_harness import snapshot
from test_station_fakeplatform import agent_on
from test_station_launch import bundle_for, fake, folder, job_of, nothing_happened, run_job, site      # noqa: F401  (fixtures)

PROJECT = {"main.nf": "workflow {\n    FASTQC(ch)\n}\n", "nextflow.config": "manifest {\n    name = 'demo'\n}\n", "modules.json": "{}\n",
           "modules/nf-core/fastqc/main.nf": "process FASTQC {\n}\n", "modules/nf-core/fastqc/templates/t.sh": "echo t\n"}


def composed_bundle(site, fake, run="run-a", project=None, version=1, **over):
    return bundle_for(site, fake, run=run, pipeline="abf-composed/demo", revision="0.%d.0" % version,
                      composed={"pipeline_id": 3, "version": version, "project": copy.deepcopy(PROJECT if project is None else project)}, **over)


def sbatches(site):
    return [c for c in site.calls() if c.startswith("sbatch")]


def written_nothing(site):
    assert not folder(site).exists() and not sbatches(site)


def test_tc109_to_113_a_composed_launch_is_rebuilt_and_the_project_lands_in_the_run_folder(tmp_path, site, fake):
    # TC-109 (rebuilt byte for byte, the project files), TC-110 (head.sh), TC-111 (0600), TC-112 (one sbatch), TC-113 (one unpack)
    b = composed_bundle(site, fake)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
        assert res["state"] == "done", res
    f = folder(site)
    for rel, text in PROJECT.items():
        assert (f / "pipeline" / rel).read_bytes() == text.encode("utf-8"), rel
    assert (f / "head.sh").read_text() == b["files"]["head.sh"]
    assert b["files"]["head.sh"].splitlines()[-1].startswith("exec nextflow run %s/pipeline/main.nf " % f)
    for p in f.rglob("*"):
        if p.is_file():
            assert stat.S_IMODE(p.stat().st_mode) == 0o600, p
        else:
            assert stat.S_IMODE(p.stat().st_mode) == 0o700, p
    assert len(sbatches(site)) == 1
    assert len([c for c in site.destructive() if c.startswith("tar")]) == 1
    names = sorted(str(p.relative_to(f)).replace(os.sep, "/") for p in f.rglob("*") if p.is_file())
    assert names == sorted(["samplesheet.csv", "params.yaml", "nextflow.config", "tower.token", "head.sh"] + ["pipeline/" + k for k in PROJECT])
    assert site.guards_intact()


def test_tc170_the_project_lives_only_in_the_run_folder(tmp_path, site, fake):
    # TC-170: no shared folder of projects, nothing is skipped because an equal copy is there
    b = composed_bundle(site, fake)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        assert run_job(fake, job_of(b))["state"] == "done"
        assert run_job(fake, job_of(composed_bundle(site, fake, run="run-b")))["state"] == "done"
    assert not (site.work / "pipelines").exists() and not list(site.work.glob("**/pipelines"))
    assert sorted(p.name for p in (site.work / "runs").iterdir()) == ["run-a", "run-b"]
    assert (folder(site, "run-b") / "pipeline" / "main.nf").read_text() == PROJECT["main.nf"]
    text = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "abf_station", "launch.py"), encoding="utf-8").read()
    assert "workDir + \"/pipelines" not in text and "/pipelines/" not in text


def _change_main(b):
    b["project"]["main.nf"] = b["project"]["main.nf"].replace("FASTQC", "FASTQD")


def _change_module(b):
    b["project"]["modules/nf-core/fastqc/main.nf"] += "# changed\n"


def _change_sha(b):
    b["pipeline_source"]["project_sha256"] = "0" * 64


@pytest.mark.parametrize("change", [_change_main, _change_module, _change_sha])
def test_tc114_115_116_a_project_changed_after_the_yes_is_refused_and_nothing_is_written(tmp_path, site, fake, change):
    # TC-114, TC-115, TC-116: the confirmation is made for the changed bundle (job_of hashes what it is given), so only the agent can refuse
    b = composed_bundle(site, fake)
    change(b)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    assert "不一致" in json.dumps(res, ensure_ascii=False)
    written_nothing(site)
    assert not [c for c in site.destructive() if c.startswith("tar")]


@pytest.mark.parametrize("key", ["pipeline/../x", "modules/nf-core/a/../../b", "../x", "/abs", "modules/nf-core/x/bin/run"])
def test_tc117_a_project_with_an_unlisted_path_is_refused(tmp_path, site, fake, key):
    # TC-117
    b = composed_bundle(site, fake)
    b["project"][key] = "x\n"
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    written_nothing(site)


def test_tc118_a_composed_source_without_a_project_is_refused(tmp_path, site, fake):
    # TC-118
    b = composed_bundle(site, fake)
    del b["project"]
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    written_nothing(site)


def test_tc119_a_project_without_a_composed_source_is_refused(tmp_path, site, fake):
    # TC-119
    b = composed_bundle(site, fake)
    b["pipeline_source"] = {"kind": "remote"}
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    written_nothing(site)
    plain = bundle_for(site, fake, run="run-p")
    plain["project"] = copy.deepcopy(PROJECT)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        assert run_job(fake, job_of(plain))["state"] == "refused"
    assert not (site.work / "runs" / "run-p").exists()


def test_tc120_a_run_folder_that_exists_is_not_overwritten(tmp_path, site, fake):
    # TC-120
    b = composed_bundle(site, fake)
    f = folder(site)
    f.mkdir(parents=True)
    (f / "keep.txt").write_text("mine")
    before = snapshot(f)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    assert snapshot(f) == before and not (f / "pipeline").exists() and not sbatches(site)


def test_tc121_a_resume_of_a_composed_origin_is_refused(tmp_path, site, fake):
    # TC-121
    origin = composed_bundle(site, fake)
    f = folder(site)
    f.mkdir(parents=True)
    (f / "head.sh").write_text("x")
    before = snapshot(f)
    resume = {"version": 1, "agent": origin["agent"], "ce": copy.deepcopy(origin["ce"]), "run_name": "run-a-a2", "run_folder": origin["run_folder"],
              "files": {"head-2.sh": "#!/bin/bash\n"},
              "resume": {"of_run": "run-a", "of_slurm_job_id": 5, "session_id": "12345678-1234-1234-1234-123456789abc", "attempt": 2,
                         "origin": origin}}
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(resume))
    assert res["state"] == "refused", res
    assert snapshot(f) == before and not sbatches(site)


def test_tc122_138_an_nf_core_launch_through_the_agent_is_unchanged(tmp_path, site, fake):
    # TC-122, TC-138: no pipeline folder, the five files, the same head script as the bundle says
    b = bundle_for(site, fake)
    assert "project" not in b
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
        assert res["state"] == "done", res
    f = folder(site)
    assert sorted(p.name for p in f.iterdir()) == sorted(["samplesheet.csv", "params.yaml", "nextflow.config", "tower.token", "head.sh"])
    assert (f / "head.sh").read_text() == b["files"]["head.sh"] and " -r 2.18.0 " in b["files"]["head.sh"]
    assert len([c for c in site.destructive() if c.startswith("tar")]) == 1


def test_tc123_an_unconfirmed_composed_launch_writes_nothing(tmp_path, site, fake):
    # TC-123
    b = composed_bundle(site, fake)
    good = job_of(b)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        for label, job in (("no confirmation", {k: v for k, v in good.items() if k != "confirmation"}),
                           ("spent", dict(good, confirmation=dict(good["confirmation"], used_at=12345.0))),
                           ("sha mismatch", dict(good, confirmation=dict(good["confirmation"], sha256="0" * 64)))):
            assert run_job(fake, job)["state"] == "refused", label
    written_nothing(site)


def test_tc124_a_read_only_cache_still_stops_a_composed_launch(tmp_path, site, fake):
    # TC-124
    os.chmod(site.storage / "cache", 0o500)
    try:
        with agent_on(fake, site, tmp_path, name="agent-f"):
            res = run_job(fake, job_of(composed_bundle(site, fake)))
    finally:
        os.chmod(site.storage / "cache", 0o700)
    assert res["state"] == "refused" and re.search(r"NXF_SINGULARITY_CACHEDIR|快取", res["result"]["message"]), res
    assert not (site.work / "runs").exists() and not sbatches(site)
