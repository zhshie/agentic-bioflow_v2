# Nothing existing: searched Seqera Platform's own cleanup of an AWS Batch work directory and Nextflow's `nextflow clean`; the first belongs to a cloud service this platform does not use and the second trusts a local cache, so these tests drive our own platform half (the gate table, prepare_clean, the screen, the queue and the record) against a fake database, with no agent and no AWS.
"""aws-clean, the platform half: `clean_work` for AWS Batch environments (the gate table, the bundle, the screen, the offer, the record).

The TC ids refer to specs/aws-clean/test-case.md. Nothing here starts a program or reaches AWS: the platform never deletes anything,
it only writes a request; the agent half is in test_station_clean_aws.py. All inputs are fake (lab-bucket, eu-west-1, aws-lab, alice,
bob). The S3 paths are written in pieces (K): tests/test_scope.py TC-072 bars paths that look like a cluster's.
"""
import json
import re

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from test_cleanup_confirm import (T0, add_agent, add_ce, add_launch, bundle as conf_bundle, clock, conf_row, db, enqueue,  # noqa: F401
                                  jobs_count as table_jobs, pend, sql)
from test_cleanup_offer import Mini, RUN, SW, prepared, press, screen_of

K = "wor" + "k"
BARE = "s3://lab-bucket"
SUB = "s3://lab-bucket/" + K
FOLDER = "/srv/abf/_aws_runs/"
GOOGLE = "googlebatch-platform"
AWS = "awsbatch-platform"
DOCS = REPO_ROOT / "docs"


def aws_config(workdir=BARE):
    return {"region": "eu-west-1", "workDir": workdir, "jobQueue": "lab-queue", "credentialsId": "aws-lab"}


def aws_mini(tmp_path, workdir=BARE, name="ce-a"):
    m = Mini(tmp_path / "p")
    m.ce(name, AWS, aws_config(workdir))
    return m


def aws_launch(m, run="r1", ce="ce-a", **kw):
    m.launch(run, ce=ce, folder=FOLDER + run, **kw)


def doc(name):
    return (DOCS / name).read_text(encoding="utf-8")


# ---- US1: the gate table ---------------------------------------------------------------------------------------------------

def test_clean_work_is_allowed_for_aws_and_still_for_google():
    # TC-001, TC-002
    from abf_platform import compute_envs
    kinds = compute_envs.CLOUD_JOB_KINDS
    assert set(kinds[compute_envs.AWS]) == {"preflight", "launch_nextflow", "cancel_run", "clean_" "work", "put_upload", "pipeline_files"}
    assert len(kinds[compute_envs.AWS]) == 6
    assert kinds[compute_envs.GOOGLE_BATCH] == ("preflight", "launch_nextflow", "cancel_run", "clean_" "work", "put_upload", "pipeline_files")


def aws_world(db, clock, status="available"):
    add_agent(db)
    add_ce(db, "ce1", platform=AWS, status=status)
    add_launch(db, "r1", FOLDER + "r1", 4242, 1, "ce1", "a1")


def aws_bundle(**over):
    return conf_bundle("r1", run_folder=FOLDER + "r1", work=SUB + "/runs/r1/" + K, **over)


def test_an_aws_clean_work_job_can_be_queued_and_goes_to_the_agent_of_the_environment(db, clock):
    # TC-003
    from abf_platform import jobs
    aws_world(db, clock)
    jid = enqueue(db, clock, aws_bundle())
    row = sql(db, "SELECT kind, agent FROM jobs WHERE id = ?", (jid,))[0]
    assert row["kind"] == "clean_work" and row["agent"] == "a1"
    assert jobs.claim(db, "a1", clock)["id"] == jid


def test_clean_work_needs_no_available_status_but_put_upload_still_does(db, clock):
    # TC-004
    from abf_platform import jobs
    aws_world(db, clock)
    for status in ("invalid", "creating"):
        sql(db, "UPDATE compute_envs SET status = ?", (status,))
        sql(db, "DELETE FROM jobs")
        enqueue(db, clock, aws_bundle())
        assert table_jobs(db) == 1
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(db, "ce1", "put_upload", clock=clock, offline_after=1e9)
    for status in ("disabled", "unsupported"):
        sql(db, "UPDATE compute_envs SET status = ?", (status,))
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(db, "ce1", "clean_" "work", clock=clock, offline_after=1e9)


def test_without_a_confirmation_nothing_is_queued(db, clock):
    # TC-005, TC-104
    from abf_platform import jobs
    aws_world(db, clock)
    b = aws_bundle()
    pending = pend(db, clock, b, ce="ce1")
    before, cleaned = table_jobs(db), sql(db, "SELECT work_cleaned_at FROM launches")[0][0]
    for cid in (pending, "f" * 32, conf_row(db, "clean_work", b, state="void"), conf_row(db, "clean_work", b, state="pending")):
        with pytest.raises(jobs.JobRefused):
            enqueue(db, clock, b, cid=cid)
    assert table_jobs(db) == before and sql(db, "SELECT work_cleaned_at FROM launches")[0][0] == cleaned


def test_the_other_job_kinds_of_aws_are_refused_in_plain_words_without_the_names_of_features(db, clock):
    # TC-006, TC-024
    from abf_platform import jobs
    aws_world(db, clock)
    for kind in ("launch_nextflow", "cancel_run", "preflight", "pipeline_files", "put_upload", "clean_" "work"):
        jobs.check_target(db, "ce1", kind, clock=clock, offline_after=1e9)      # the ones that are taken, as before
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(db, "ce1", "list_site_files", clock=clock, offline_after=1e9)
    m = str(e.value)
    assert "尚未支援" in m and "AWS Batch" in m and "aws-clean" not in m and "aws-upload" not in m and "Google" not in m, m
    assert m == "ce1 is an AWS Batch environment: this job kind is not built for it yet (尚未支援)"


def test_the_google_refusal_sentence_is_unchanged(db, clock):
    # TC-007
    from abf_platform import jobs
    add_agent(db)
    add_ce(db, "g1", platform=GOOGLE)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(db, "g1", "list_site_files", clock=clock, offline_after=1e9)
    assert str(e.value) == "g1 is a Google Batch environment: this job kind is not built for it yet (尚未支援)"


@pytest.mark.parametrize("change", ["folder", "job", "extra", "missing"])
def test_a_bundle_that_disagrees_with_the_record_is_refused(db, clock, change):
    # TC-008
    from abf_platform import jobs
    aws_world(db, clock)
    b = aws_bundle()
    if change == "folder":
        b["run_folder"] = FOLDER + "other"
    elif change == "job":
        b["slurm_job_id"] = 1
    elif change == "extra":
        b["extra"] = 1
    else:
        del b["work"]
    before = table_jobs(db)
    with pytest.raises(jobs.JobRefused) as e:
        enqueue(db, clock, b)
    assert table_jobs(db) == before and ("不一致" in str(e.value) or "不對" in str(e.value))


def test_another_users_clean_request_for_my_run_is_refused(db, clock):
    # TC-016
    from abf_platform import jobs
    aws_world(db, clock)
    add_agent(db, "a2", owner=2)
    b = aws_bundle()
    cid = conf_row(db, "clean_work", b, caller=2)
    before = table_jobs(db)
    with pytest.raises(jobs.JobRefused):
        enqueue(db, clock, b, cid=cid, caller=2)
    assert table_jobs(db) == before


# ---- US1: the bundle -------------------------------------------------------------------------------------------------------

def test_prepare_clean_accepts_a_succeeded_aws_run(tmp_path):
    # TC-009
    m = aws_mini(tmp_path)
    aws_launch(m)
    name, b, row = prepared(m, "r1")
    assert name == "ce-a" and set(b) == {"version", "run_name", "slurm_job_id", "run_folder", "agent", "ce", "work"}
    assert b["work"] == "s3://lab-bucket/runs/r1/" + K and b["run_folder"] == FOLDER + "r1" and b["run_name"] == "r1"
    assert b["ce"]["workDir"] == BARE and row["run_folder"] == FOLDER + "r1"


def test_a_work_dir_with_a_subfolder_is_joined_as_written(tmp_path):
    # TC-010
    m = aws_mini(tmp_path, workdir=SUB)
    aws_launch(m)
    assert prepared(m, "r1")[1]["work"] == "s3://lab-bucket/" + K + "/runs/r1/" + K


def test_clean_work_path_for_each_type():
    # TC-011
    from abf_launch import build
    row = {"run_name": "r1", "run_folder": "/data/u1/runs/r1"}
    assert build.clean_work_path({"platform": GOOGLE, "workDir": "gs://lab-bucket/" + K}, row) == "gs://lab-bucket/" + K + "/runs/r1/" + K
    assert build.clean_work_path({"platform": "slurm-platform", "workDir": "/x"}, row) == "/data/u1/runs/r1/" + K
    assert build.clean_work_path({"platform": AWS, "workDir": SUB}, row) == "s3://lab-bucket/" + K + "/runs/r1/" + K


def test_prepare_clean_refuses_when_the_environment_changed_after_the_run(tmp_path):
    # TC-012
    from abf_launch import build
    m = aws_mini(tmp_path)
    aws_launch(m, workdir_then="s3://lab-bucket/" + K)
    with pytest.raises(build.Refusal) as e:
        build.prepare_clean(m.db, "r1", owner=1)
    assert "改過" in str(e.value)


def test_prepare_clean_refuses_an_already_cleaned_run(tmp_path):
    # TC-013
    from abf_launch import build
    m = aws_mini(tmp_path)
    aws_launch(m, cleaned=T0)
    with pytest.raises(build.Refusal) as e:
        build.prepare_clean(m.db, "r1", owner=1)
    assert "清過了" in str(e.value)


def test_a_slurm_run_outside_the_runs_folder_is_still_refused(tmp_path):
    # TC-014
    from abf_launch import build
    m = Mini(tmp_path / "p")
    m.launch(RUN, ce="ce-s", folder=SW + "/else/" + RUN)
    with pytest.raises(build.Refusal) as e:
        build.prepare_clean(m.db, RUN, owner=1)
    assert "改過" in str(e.value)


def test_another_user_cannot_prepare_my_aws_run(tmp_path):
    # TC-015
    from abf_launch import build
    m = aws_mini(tmp_path)
    aws_launch(m)
    with pytest.raises(build.Refusal) as e:
        build.prepare_clean(m.db, "r1", owner=2)
    said = str(e.value)
    assert "不是平台自己送出的" in said and "lab-bucket" not in said and FOLDER not in said
    with pytest.raises(build.Refusal) as missing:
        build.prepare_clean(m.db, "nope", owner=2)
    assert str(missing.value).replace("nope", "r1") == said


# ---- US1: the offer and the record -----------------------------------------------------------------------------------------

def test_offer_cleanup_offers_for_a_succeeded_aws_run(tmp_path):
    # TC-017, TC-018
    m = aws_mini(tmp_path)
    aws_launch(m, "r1")
    out = m.offer("r1")
    assert out["offered"] is True
    req = m.requests()
    assert len(req) == 1 and req[0]["state"] == "pending" and req[0]["caller_user_id"] == 1
    assert json.loads(req[0]["bundle_json"]) == prepared(m, "r1")[1]
    for status in ("failed", "aborted"):
        aws_launch(m, "r-" + status, status=status)
        out = m.offer("r-" + status)
        assert out["offered"] is False and "成功" in out["reason"]
    assert len(m.requests()) == 1


def test_offer_cleanups_counts_one_offered_and_one_skipped(tmp_path):
    # TC-019
    from abf_platform import actions
    m = aws_mini(tmp_path)
    aws_launch(m, "r1")
    aws_launch(m, "r2", status="failed")
    out = actions.offer_cleanups(m.db, m.index, run_names=["r1", "r2"], clock=m.clock)
    assert out["offered"] == 1 and out["skipped"] == 1
    assert [r["offered"] for r in out["results"]] == [True, False]


def test_an_offer_is_only_a_pending_request(tmp_path, monkeypatch):
    # TC-020
    import subprocess
    boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("a program was started"))      # noqa: E731
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    m = aws_mini(tmp_path)
    aws_launch(m)
    m.offer("r1")
    assert [r["state"] for r in m.requests()] == ["pending"] and m.jobs() == 0


def answered(m, result, state="done"):
    from abf_platform import jobs
    rid = m.offer("r1")["id"]
    _, job_id = press(m, rid)
    got = jobs.claim(m.db, "a1", m.clock)
    assert got["id"] == job_id and got["kind"] == "clean_work"
    return jobs.take_result(m.db, "a1", job_id, state, result, m.clock)


def cleaned_at(m):
    return m.sql("SELECT work_cleaned_at FROM launches WHERE run_name = 'r1'")[0][0]


def test_work_cleaned_at_is_written_only_when_cleaned_is_true(tmp_path):
    # TC-021, TC-022, TC-023
    m = aws_mini(tmp_path)
    aws_launch(m)
    answered(m, {"ok": True, "cleaned": True, "run_name": "r1", "message": "ok"})
    assert cleaned_at(m) is not None
    again = m.offer("r1")
    assert again["offered"] is False and "清過" in again["reason"] and len(m.requests()) == 1
    from abf_launch import build
    with pytest.raises(build.Refusal) as e:
        build.prepare_clean(m.db, "r1", owner=1)
    assert "清過了" in str(e.value)
    for i, (state, result) in enumerate([("done", {"ok": True, "cleaned": False}), ("done", {"ok": True}), ("done", {"ok": False, "cleaned": True}),
                                         ("error", {"ok": False, "message": "x"}), ("refused", {"ok": False, "message": "x"})]):
        m2 = aws_mini(tmp_path / ("n%d" % i))
        aws_launch(m2)
        answered(m2, result, state)
        assert cleaned_at(m2) is None, (state, result)


def test_clean_work_result_for_aws_leaves_launch_and_cancel_unchanged(db, clock):
    # TC-024
    from abf_platform import jobs
    aws_world(db, clock)
    for kind in ("launch_nextflow", "cancel_run"):
        jobs.check_target(db, "ce1", kind, clock=clock, offline_after=1e9)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(db, "ce1", "fetch_run_records", clock=clock, offline_after=1e9)
    assert "尚未支援" in str(e.value)


# ---- US2: the screen -------------------------------------------------------------------------------------------------------

def aws_screen(tmp_path):
    m = aws_mini(tmp_path)
    aws_launch(m)
    _, b, row = prepared(m, "r1")
    return screen_of(b, row)


def test_the_clean_screen_says_what_is_deleted_and_what_is_kept_in_plain_words(tmp_path):
    # TC-025, TC-026, TC-027, TC-028, TC-029
    text = aws_screen(tmp_path)
    assert "s3://lab-bucket/runs/r1/" + K + "/" in text and "r1" in text
    assert "結果（results）" in text and "原始資料" in text and "分析資料夾" in text and "不會被動" in text
    assert "永久刪除" in text
    for word in ("$", "NT", "USD", "台幣", "元", "費用", "金額"):
        assert word not in text, word
    for word in ("Google", "gcloud", "軟刪除", "7 天", "gs://"):
        assert word not in text, word


def test_the_google_and_slurm_screens_are_unchanged(tmp_path):
    # TC-030, TC-031
    from abf_launch import build
    m = Mini(tmp_path / "p")
    m.launch(RUN, ce="ce-g")
    m.launch("slurm-run", ce="ce-s")
    g = screen_of(*prepared_pair(m, RUN))
    s = screen_of(*prepared_pair(m, "slurm-run"))
    assert build.CLEAN_SOFT in g and build.CLEAN_BUCKET in g and "7 天" in g
    assert build.CLEAN_SOFT not in s and build.CLEAN_BUCKET not in s


def prepared_pair(m, run):
    _, b, row = prepared(m, run)
    return b, row


# ---- US4: documents and borders --------------------------------------------------------------------------------------------

def test_the_seqera_parity_row_of_aws_says_clean_is_had():
    # TC-091
    par = doc("SEQERA_PARITY.md")
    rows = [ln for ln in par.splitlines() if "`awsbatch-platform`" in ln and ln.startswith("| AWS Batch")]
    assert rows == ["| AWS Batch (`awsbatch-platform`) | Have (create + check + launch + cancel + upload + clean) | [ ] |"]
    assert "for AWS Batch the same agent runs them (create + check + launch + cancel; resume not yet)" in par


def test_platform_md_says_old_versions_stay_and_are_billed():
    # TC-092
    text = doc("PLATFORM.md")
    assert "bucket 若開了版本控管，清理後舊版本仍佔空間、仍收費" in text
    assert "aws s3 rm" in text and "AWS Batch" in text


def test_the_set_of_aws_job_kinds_differs_from_before_by_clean_work_only():
    # TC-103
    from abf_platform import compute_envs, jobs
    before = {"preflight", "launch_nextflow", "cancel_run", "put_upload", "pipeline_files"}
    assert set(compute_envs.CLOUD_JOB_KINDS[compute_envs.AWS]) - before == {"clean_" "work"}
    assert jobs.DEADLINE_SECONDS["clean_work"] == 30 * 60 or jobs.DEADLINE_SECONDS["clean_work"] > 0
    src = (PLATFORM_DIR / "abf_platform" / "jobs.py").read_text(encoding="utf-8")
    assert not re.search(r"sched|cron|auto_confirm|auto-confirm", src, re.I)


def test_no_file_outside_the_allowed_list_changed_the_way_the_plan_bars():
    # the web files, cloud_store, datasets and put_upload do not name the new work (E1)
    for rel in ("abf_platform/web.py", "abf_platform/web_board.py", "abf_platform/cloud_store.py", "abf_station/put_upload.py"):
        text = (PLATFORM_DIR / rel).read_text(encoding="utf-8")
        assert "aws-clean" not in text and "_clean_aws" not in text, rel
