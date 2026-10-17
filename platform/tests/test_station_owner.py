# Nothing existing: tests of the agent's side of 116b (a link swapped after the yes, a listing that must not follow a link out); the protocol and the fake site are ours.
"""The agent re-resolves the upload-area paths of a launch at job time and does not follow links when it lists (116b).
Test cases are named in the comments (TC-026, TC-030 ...), see specs/116b-owner-gaps/test-case.md."""
import os

import pytest

from test_station_fakeplatform import agent_on, list_args
from test_station_launch import bundle_for, folder, job_of, nothing_happened, run_job, site, fake   # noqa: F401  (the two fixtures)


def make_areas(site):
    up = site.storage / "up"
    for who in ("alice", "bob"):
        (up / who / "real").mkdir(parents=True)
    (up / "alice" / "real" / "x.fq").write_text("x")
    (up / "alice" / "real" / "y.fq").write_text("y")
    (up / "bob" / "secret.fq").write_text("secret")
    os.symlink(str(up / "alice" / "real" / "x.fq"), str(up / "alice" / "lnk"))
    return up / "alice", up / "bob"


def with_record(site, fake, cell, real, area, **over):
    """A launch bundle whose samplesheet cell is `cell` and whose record says the cell led to `real` when the person said yes."""
    b = bundle_for(site, fake, samplesheet=[["sample", "fastq_1"], ["s1", str(cell)]], **over)
    b["upload_paths"] = {"area": os.path.realpath(area),
                         "paths": [{"where": "samplesheet 第 2 列第 2 欄", "given": str(cell), "real": os.path.realpath(real)}]}
    return b


def test_tc030_nothing_moved_the_job_goes_on(tmp_path, site, fake):
    # TC-030
    alice, _ = make_areas(site)
    b = with_record(site, fake, alice / "lnk", alice / "real" / "x.fq", alice)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res
    assert len([c for c in site.calls() if c.startswith("sbatch")]) == 1


def test_tc031_a_link_swapped_into_another_folder_after_the_yes_is_refused(tmp_path, site, fake):
    # TC-031
    alice, bob = make_areas(site)
    b = with_record(site, fake, alice / "lnk", alice / "real" / "x.fq", alice)
    job = job_of(b)
    os.remove(alice / "lnk")
    os.symlink(str(bob / "secret.fq"), str(alice / "lnk"))
    with agent_on(fake, site, tmp_path, name="agent-f") as a:
        res = run_job(fake, job)
        assert res["state"] == "refused" and res["result"]["message"], res      # TC-034
        assert "secret" not in res["result"]["message"] and a.alive()
    nothing_happened(site)


def test_tc032_a_link_swapped_inside_the_folder_is_refused_too(tmp_path, site, fake):
    # TC-032
    alice, _ = make_areas(site)
    b = with_record(site, fake, alice / "lnk", alice / "real" / "x.fq", alice)
    job = job_of(b)
    os.remove(alice / "lnk")
    os.symlink(str(alice / "real" / "y.fq"), str(alice / "lnk"))
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job)
    assert res["state"] == "refused", res
    nothing_happened(site)


def test_tc033_a_record_outside_the_owners_folder_is_refused(tmp_path, site, fake):
    # TC-033
    alice, bob = make_areas(site)
    b = with_record(site, fake, bob / "secret.fq", bob / "secret.fq", alice)
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    nothing_happened(site)


def test_tc035_the_check_never_widens_what_the_agent_may_read(tmp_path, site, fake):
    # TC-035: the recorded path equals the resolved one but lies outside every read root of the agent
    area = site.evil / "up" / "alice"
    area.mkdir(parents=True)
    (area / "x.fq").write_text("x")
    b = bundle_for(site, fake)
    b["samplesheet"] = [["sample", "fastq_1"], ["s1", str(area / "x.fq")]]
    b["upload_paths"] = {"area": os.path.realpath(area),
                         "paths": [{"where": "samplesheet 第 2 列第 2 欄", "given": str(area / "x.fq"), "real": os.path.realpath(area / "x.fq")}]}
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "refused", res
    nothing_happened(site)


def test_tc036_a_swapped_params_path_is_refused(tmp_path, site, fake):
    # TC-036
    alice, bob = make_areas(site)
    os.symlink(str(alice / "real" / "x.fq"), str(alice / "ref"))
    b = bundle_for(site, fake, params={"primer": "AGRG", "ref": str(alice / "ref")})
    b["upload_paths"] = {"area": os.path.realpath(alice),
                         "paths": [{"where": "params ref", "given": str(alice / "ref"), "real": os.path.realpath(alice / "real" / "x.fq")}]}
    job = job_of(b)
    os.remove(alice / "ref")
    os.symlink(str(bob / "secret.fq"), str(alice / "ref"))
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job)
    assert res["state"] == "refused", res
    nothing_happened(site)


def test_tc037_a_terminal_launch_has_no_record_and_is_not_refused(tmp_path, site, fake):
    # TC-037
    b = bundle_for(site, fake)
    assert "upload_paths" not in b
    with agent_on(fake, site, tmp_path, name="agent-f"):
        res = run_job(fake, job_of(b))
    assert res["state"] == "done", res


def test_tc026_the_listing_does_not_follow_a_link_out_of_the_folder(tmp_path, site, fake):
    # TC-026
    alice, bob = make_areas(site)
    os.symlink(str(bob), str(alice / "to_bob"))
    with agent_on(fake, site, tmp_path):
        res = fake.wait_result(fake.push("list_site_files", list_args(site, str(alice))))
        assert res["state"] == "done", res
        names = {e["name"]: e["type"] for e in res["result"]["entries"]}
        assert names["to_bob"] == "link" and "secret.fq" not in names
        assert "secret" not in str(res["result"])


def test_tc026b_a_requested_folder_that_is_a_link_out_of_every_read_root_is_refused(tmp_path, site, fake):
    # TC-026: the folder asked for is itself a link, and its other end is where the agent may not read
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "f.txt").write_text("x")
    os.symlink(str(outside), str(site.storage / "up_link"))
    with agent_on(fake, site, tmp_path):
        res = fake.wait_result(fake.push("list_site_files", list_args(site, str(site.storage / "up_link"))))
        assert res["state"] == "refused", res
        assert "f.txt" not in str(res)
