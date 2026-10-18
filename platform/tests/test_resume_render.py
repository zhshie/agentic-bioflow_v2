# Nothing existing: tests of the head script of a resume and of the bundle that carries it (spec 009e); no library renders a Nextflow head job script, and the rules of what a resume may change are ours.
"""009e: render_resume and render_resume_bundle (abf_station/launch.py), and the guard that a first launch's head script did not move.
Test cases are named in the comments (TC-012 ...), see specs/009e-resume-relaunch/test-case.md."""
import copy
import json
from pathlib import Path

import pytest

from test_launch_bundle import facts, render

SID = "0b1c2d3e-4f50-4a6b-8c7d-9e0f1a2b3c4d"
GOLDEN = json.loads((Path(__file__).resolve().parent / "fixtures" / "golden_head_scripts.json").read_text(encoding="utf-8"))


def launch_mod():
    from abf_station import launch
    return launch


def test_tc013_a_first_launch_head_script_is_byte_for_byte_what_it_was_before():
    # TC-013 (golden): the two head scripts were written by the code of v3 before 009e and are kept in fixtures/golden_head_scripts.json
    assert render()["files"]["head.sh"] == GOLDEN["local"]
    forward = facts(reach="ssh", forward_file="/data/storage/_relay/forward_port")
    assert render(facts=forward)["files"]["head.sh"] == GOLDEN["forward"]


def test_tc012_the_resume_head_script_has_the_session_id_the_new_name_and_the_attempt_in_its_file_name():
    # TC-012
    origin = render()
    files = launch_mod().render_resume(origin=origin, run_name="run-one-a2", attempt=2, session_id=SID)
    assert list(files) == ["head-2.sh"]
    last = files["head-2.sh"].rstrip("\n").split("\n")[-1]
    assert last.startswith("exec nextflow run nf-core/ampliseq -r 2.18.0 ")
    assert "-resume %s " % SID in last and " -name run-one-a2 " in last
    assert "-params-file params.yaml -c nextflow.config -with-tower http://127.0.0.1:8787" in last
    third = launch_mod().render_resume(origin=origin, run_name="run-one-a3", attempt=3, session_id=SID)
    assert list(third) == ["head-3.sh"]


def test_tc012_the_resume_script_differs_from_the_first_one_only_in_the_job_name_and_the_last_line():
    # TC-012 / D7: "the only difference from the first head script is -resume <session id> and the new -name"
    origin = render()
    first = origin["files"]["head.sh"].split("\n")
    second = launch_mod().render_resume(origin=origin, run_name="run-one-a2", attempt=2, session_id=SID)["head-2.sh"].split("\n")
    assert len(first) == len(second)
    differing = [i for i, (a, b) in enumerate(zip(first, second)) if a != b]
    assert [first[i] for i in differing] == ["#SBATCH -J nf-run-one", first[-2]]
    assert second[differing[0]] == "#SBATCH -J nf-run-one-a2"
    assert differing == [2, len(first) - 2]


def test_tc012_the_forward_variant_keeps_its_port_lines():
    origin = render(facts=facts(reach="ssh", forward_file="/data/storage/_relay/forward_port"))
    text = launch_mod().render_resume(origin=origin, run_name="run-one-a2", attempt=2, session_id=SID)["head-2.sh"]
    assert "ABF_FORWARD_PORT=$(cat /data/storage/_relay/forward_port" in text
    assert text.rstrip("\n").split("\n")[-1].endswith('-with-tower "http://127.0.0.1:${ABF_FORWARD_PORT}"')


def test_tc064_a_relaunch_has_no_resume_in_its_head_script():
    # TC-064: a relaunch is an ordinary render of the same inputs under a new name
    fresh = render(run_name="run-one-a2")
    assert "-resume" not in fresh["files"]["head.sh"]
    assert fresh["files"]["head.sh"].rstrip("\n").split("\n")[-1].count("-name run-one-a2") == 1


@pytest.mark.parametrize("session", ["", "x", "$(touch /tmp/c)", "0b1c2d3e-4f50-4a6b-8c7d-9e0f1a2b3c4d; touch c", "0b1c2d3e 4f50",
                                     "../../etc", 7, None, "0b1c2d3e-4f50-4a6b-8c7d-9e0f1a2b3c4dx"])
def test_a_session_id_that_is_not_a_uuid_is_never_put_in_a_script(session):
    with pytest.raises(launch_mod().BundleError):
        launch_mod().render_resume(origin=render(), run_name="run-one-a2", attempt=2, session_id=session)


@pytest.mark.parametrize("name", ["Bad", "a b", "x;y", "", "-x", "a" * 65])
def test_a_resume_run_name_must_be_a_run_name(name):
    with pytest.raises(launch_mod().BundleError):
        launch_mod().render_resume(origin=render(), run_name=name, attempt=2, session_id=SID)


@pytest.mark.parametrize("attempt", [0, 1, -3, True, 2.0, "2", None])
def test_an_attempt_is_a_whole_number_from_two(attempt):
    with pytest.raises(launch_mod().BundleError):
        launch_mod().render_resume(origin=render(), run_name="run-one-a2", attempt=attempt, session_id=SID)


def test_tc006_tc011_the_resume_bundle_has_one_file_and_no_samples_or_parameters_of_its_own():
    # TC-006, TC-011
    origin = render()
    b = launch_mod().render_resume_bundle(origin=origin, run_name="run-one-a2", attempt=2, session_id=SID, of_run="run-one",
                                          of_slurm_job_id=4242)
    assert set(b) == {"version", "agent", "ce", "run_name", "run_folder", "files", "resume"}
    assert list(b["files"]) == ["head-2.sh"]
    assert not ({"samplesheet", "params", "pipeline", "revision", "path_columns"} & set(b))
    assert b["run_folder"] == origin["run_folder"] and b["run_name"] == "run-one-a2" and b["agent"] == origin["agent"]
    assert b["ce"] == origin["ce"]
    assert b["resume"] == {"of_run": "run-one", "of_slurm_job_id": 4242, "session_id": SID, "attempt": 2, "origin": origin}
    # TC-007 (the origin is the bundle as it was, not a copy that was rebuilt)
    assert b["resume"]["origin"] == origin


def test_the_resume_bundle_is_built_from_the_origin_without_changing_it():
    origin = render()
    before = copy.deepcopy(origin)
    launch_mod().render_resume_bundle(origin=origin, run_name="run-one-a2", attempt=2, session_id=SID, of_run="run-one",
                                      of_slurm_job_id=4242)
    assert origin == before


def test_the_origin_of_a_relaunched_analysis_may_carry_the_records_of_that_launch():
    # an origin that was itself a relaunch carries `relaunch` and (over HTTP) `upload_paths`; the resume bundle takes it verbatim
    origin = render()
    origin["relaunch"] = {"of_run": "x", "attempt": 2, "of_sha256": "0" * 64}
    origin["upload_paths"] = {"area": "/u/a", "paths": []}
    b = launch_mod().render_resume_bundle(origin=origin, run_name="run-one-a3", attempt=3, session_id=SID, of_run="run-one",
                                          of_slurm_job_id=1)
    assert b["resume"]["origin"] == origin
    assert list(b["files"]) == ["head-3.sh"]
