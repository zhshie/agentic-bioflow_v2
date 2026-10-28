# Nothing existing: searched Seqera Platform's own cleanup of an Azure Batch work directory and Nextflow's `nextflow clean`; the first belongs to a cloud service this platform does not use and the second trusts a local cache, so these tests drive the platform half of our own request.
"""azure-clean, the platform half: `clean_work` for Azure Batch environments (the gate table, the bundle, the screen, the offer, the record).

The TC ids refer to specs/azure-clean/test-case.md. Nothing here starts a program or reaches Azure: the platform never deletes anything,
it only writes a request; the agent half is in test_station_clean_azure.py. All inputs are fake (labcontainer, westeurope, azlab, alice,
bob). The blob paths are written in pieces (K): tests/test_scope.py TC-072 bars paths that look like a cluster's.
"""
import json
import re
import sqlite3

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from test_cleanup_confirm import (T0, add_agent, add_ce, add_launch, bundle as conf_bundle, clock, conf_row, db, enqueue,  # noqa: F401
                                  jobs_count as table_jobs, pend, sql)
from test_cleanup_offer import Mini, RUN, SW, prepared, press, screen_of

K = "wor" + "k"
BARE = "az://labcontainer/" + K
FOLDER = "/srv/abf/_azure_runs/"
GOOGLE = "googlebatch-platform"
AWS = "awsbatch-platform"
AZ = "azbatch-platform"
DOCS = REPO_ROOT / "docs"
EXPECTED = "az://labcontainer/" + K + "/runs/r1/" + K


def azure_config(workdir=BARE):
    return {"location": "westeurope", "batchAccountName": "labbatch", "storageAccountName": "azlab", "workDir": workdir,
            "pool": "lab-pool", "credentialsId": "azure-lab"}


def azure_mini(tmp_path, workdir=BARE, name="ce-z"):
    m = Mini(tmp_path / "p")
    m.ce(name, AZ, azure_config(workdir))
    return m


def azure_launch(m, run="r1", ce="ce-z", **kw):
    m.launch(run, ce=ce, folder=FOLDER + run, **kw)


def doc(name):
    return (DOCS / name).read_text(encoding="utf-8")


def azure_world(db, clock, status="available"):
    add_agent(db)
    add_ce(db, "ce1", platform=AZ, status=status)
    add_launch(db, "r1", FOLDER + "r1", 4242, 1, "ce1", "a1")


def azure_bundle(**over):
    return conf_bundle("r1", run_folder=FOLDER + "r1", work=EXPECTED, **over)


# ---- US1: the gate table ---------------------------------------------------------------------------------------------------

def test_clean_work_is_allowed_for_azure_and_still_for_google_and_aws():
    # TC-001, TC-002 (AZC-PLT-01)
    from abf_platform import compute_envs
    kinds = compute_envs.CLOUD_JOB_KINDS
    assert set(kinds[compute_envs.AZURE]) == {"preflight", "launch_nextflow", "cancel_run", "pipeline_files", "put_upload", "clean_" "work"}
    assert len(kinds[compute_envs.AZURE]) == 6
    six = ("preflight", "launch_nextflow", "cancel_run", "clean_" "work", "put_upload", "pipeline_files")
    assert kinds[compute_envs.GOOGLE_BATCH] == six and kinds[compute_envs.AWS] == six


def test_an_azure_clean_work_job_can_be_queued_and_goes_to_the_agent_of_the_environment(db, clock):
    # TC-003
    from abf_platform import jobs
    azure_world(db, clock)
    jid = enqueue(db, clock, azure_bundle())
    row = sql(db, "SELECT kind, agent FROM jobs WHERE id = ?", (jid,))[0]
    assert row["kind"] == "clean_work" and row["agent"] == "a1"
    assert jobs.claim(db, "a1", clock)["id"] == jid


def test_clean_work_needs_no_available_status_but_put_upload_still_does(db, clock):
    # TC-004
    from abf_platform import jobs
    azure_world(db, clock)
    for status in ("invalid", "creating"):
        sql(db, "UPDATE compute_envs SET status = ?", (status,))
        sql(db, "DELETE FROM jobs")
        enqueue(db, clock, azure_bundle())
        assert table_jobs(db) == 1
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(db, "ce1", "put_upload", clock=clock, offline_after=1e9)


def test_without_a_confirmation_nothing_is_queued(db, clock):
    # TC-005, TC-122
    from abf_platform import jobs
    azure_world(db, clock)
    b = azure_bundle()
    pending = pend(db, clock, b, ce="ce1")
    before, cleaned = table_jobs(db), sql(db, "SELECT work_cleaned_at FROM launches")[0][0]
    for cid in (pending, "f" * 32, conf_row(db, "clean_work", b, state="void"), conf_row(db, "clean_work", b, state="pending")):
        with pytest.raises(jobs.JobRefused):
            enqueue(db, clock, b, cid=cid)
    assert table_jobs(db) == before and sql(db, "SELECT work_cleaned_at FROM launches")[0][0] == cleaned


def test_the_other_job_kinds_of_azure_are_refused_in_plain_words_without_the_names_of_features(db, clock):
    # TC-006
    from abf_platform import jobs
    azure_world(db, clock)
    for kind in ("launch_nextflow", "cancel_run", "preflight", "pipeline_files", "put_upload", "clean_" "work"):
        jobs.check_target(db, "ce1", kind, clock=clock, offline_after=1e9)      # the ones that are taken
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(db, "ce1", "list_site_files", clock=clock, offline_after=1e9)
    m = str(e.value)
    assert "尚未支援" in m and "azure-clean" not in m and "azure-launch" not in m and "azure-upload" not in m, m
    assert m == "ce1 is an Azure Batch environment: this job kind is not built for it yet (尚未支援)"


def test_the_google_and_aws_refusal_sentences_are_unchanged(db, clock):
    # TC-007
    from abf_platform import jobs
    add_agent(db)
    add_ce(db, "g1", platform=GOOGLE)
    add_ce(db, "w1", platform=AWS)
    for name, text in (("g1", "g1 is a Google Batch environment: this job kind is not built for it yet (尚未支援)"),
                       ("w1", "w1 is an AWS Batch environment: this job kind is not built for it yet (尚未支援)")):
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(db, name, "list_site_files", clock=clock, offline_after=1e9)
        assert str(e.value) == text


@pytest.mark.parametrize("change", ["folder", "job", "extra", "missing"])
def test_a_bundle_that_disagrees_with_the_record_is_refused(db, clock, change):
    # TC-008
    from abf_platform import jobs
    azure_world(db, clock)
    b = azure_bundle()
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
    # TC-015
    from abf_platform import jobs
    azure_world(db, clock)
    add_agent(db, "a2", owner=2)
    b = azure_bundle()
    cid = conf_row(db, "clean_work", b, caller=2)
    before = table_jobs(db)
    with pytest.raises(jobs.JobRefused):
        enqueue(db, clock, b, cid=cid, caller=2)
    assert table_jobs(db) == before


# ---- US1: the bundle -------------------------------------------------------------------------------------------------------

def test_prepare_clean_accepts_a_succeeded_azure_run(tmp_path):
    # TC-009 (AZC-PLT-02)
    m = azure_mini(tmp_path, workdir="az://labcontainer/work")
    azure_launch(m)
    name, b, row = prepared(m, "r1")
    assert name == "ce-z" and set(b) == {"version", "run_name", "slurm_job_id", "run_folder", "agent", "ce", "work"}
    assert b["work"] == "az://labcontainer/work/runs/r1/work" and b["run_folder"] == FOLDER + "r1" and b["run_name"] == "r1"
    assert b["ce"]["workDir"] == "az://labcontainer/work" and row["run_folder"] == FOLDER + "r1"


def test_clean_work_path_for_each_type():
    # TC-010
    from abf_launch import build
    row = {"run_name": "r1", "run_folder": "/data/u1/runs/r1"}
    assert build.clean_work_path({"platform": GOOGLE, "workDir": "gs://lab-bucket/" + K}, row) == "gs://lab-bucket/" + K + "/runs/r1/" + K
    assert build.clean_work_path({"platform": "slurm-platform", "workDir": "/x"}, row) == "/data/u1/runs/r1/" + K
    assert build.clean_work_path({"platform": AZ, "workDir": "az://labcontainer/work"}, row) == "az://labcontainer/work/runs/r1/work"


def test_prepare_clean_refuses_when_the_environment_changed_after_the_run(tmp_path):
    # TC-011 (AZC-PLT-03)
    from abf_launch import build
    m = azure_mini(tmp_path)
    azure_launch(m, workdir_then="az://labcontainer/other")
    with pytest.raises(build.Refusal) as e:
        build.prepare_clean(m.db, "r1", owner=1)
    assert "改過" in str(e.value)


def test_prepare_clean_refuses_an_already_cleaned_run(tmp_path):
    # TC-012 (AZC-PLT-04)
    from abf_launch import build
    m = azure_mini(tmp_path)
    azure_launch(m, cleaned=T0)
    with pytest.raises(build.Refusal) as e:
        build.prepare_clean(m.db, "r1", owner=1)
    assert "清過了" in str(e.value)


def test_a_slurm_run_outside_the_runs_folder_is_still_refused(tmp_path):
    # TC-013
    from abf_launch import build
    m = Mini(tmp_path / "p")
    m.launch(RUN, ce="ce-s", folder=SW + "/else/" + RUN)
    with pytest.raises(build.Refusal) as e:
        build.prepare_clean(m.db, RUN, owner=1)
    assert "改過" in str(e.value)


def test_another_user_cannot_prepare_my_azure_run(tmp_path):
    # TC-014
    from abf_launch import build
    m = azure_mini(tmp_path)
    azure_launch(m)
    with pytest.raises(build.Refusal) as e:
        build.prepare_clean(m.db, "r1", owner=2)
    said = str(e.value)
    assert "不是平台自己送出的" in said and "labcontainer" not in said and FOLDER not in said
    with pytest.raises(build.Refusal) as missing:
        build.prepare_clean(m.db, "nope", owner=2)
    assert str(missing.value).replace("nope", "r1") == said


# ---- US1: the offer and the record -----------------------------------------------------------------------------------------

def test_offer_cleanup_offers_for_a_succeeded_azure_run(tmp_path):
    # TC-016, TC-017 (AZC-PLT-05)
    m = azure_mini(tmp_path)
    azure_launch(m, "r1")
    out = m.offer("r1")
    assert out["offered"] is True
    req = m.requests()
    assert len(req) == 1 and req[0]["state"] == "pending" and req[0]["caller_user_id"] == 1
    assert json.loads(req[0]["bundle_json"]) == prepared(m, "r1")[1]
    for status in ("failed", "aborted"):
        azure_launch(m, "r-" + status, status=status)
        out = m.offer("r-" + status)
        assert out["offered"] is False and "成功" in out["reason"]
    assert len(m.requests()) == 1


def test_offer_cleanups_counts_one_offered_and_one_skipped(tmp_path):
    # TC-018
    from abf_platform import actions
    m = azure_mini(tmp_path)
    azure_launch(m, "r1")
    azure_launch(m, "r2", status="failed")
    out = actions.offer_cleanups(m.db, m.index, run_names=["r1", "r2"], clock=m.clock)
    assert out["offered"] == 1 and out["skipped"] == 1
    assert [r["offered"] for r in out["results"]] == [True, False]


def test_an_offer_is_only_a_pending_request(tmp_path, monkeypatch):
    # TC-019
    import subprocess
    boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("a program was started"))      # noqa: E731
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    m = azure_mini(tmp_path)
    azure_launch(m)
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
    # TC-020, TC-021, TC-022 (AZC-PLT-07)
    m = azure_mini(tmp_path)
    azure_launch(m)
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
        m2 = azure_mini(tmp_path / ("n%d" % i))
        azure_launch(m2)
        answered(m2, result, state)
        assert cleaned_at(m2) is None, (state, result)


def test_clean_work_for_azure_leaves_launch_cancel_and_upload_unchanged(db, clock):
    # TC-023 (AZC-PLT-08)
    from abf_platform import jobs
    azure_world(db, clock)
    for kind in ("launch_nextflow", "cancel_run", "put_upload", "preflight", "pipeline_files"):
        jobs.check_target(db, "ce1", kind, clock=clock, offline_after=1e9)
    for kind in ("fetch_run_records", "read_task_log", "list_site_files"):
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(db, "ce1", kind, clock=clock, offline_after=1e9)
        assert "尚未支援" in str(e.value)


def test_list_site_files_for_azure_is_refused_without_the_name_of_a_feature(db, clock):
    # TC-006 (the hint of the old message is gone)
    from abf_platform import jobs
    azure_world(db, clock)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(db, "ce1", "list_site_files", clock=clock, offline_after=1e9)
    assert "azure-" not in str(e.value)


def test_resume_and_relaunch_are_still_refused_for_azure(tmp_path):
    # TC-119
    from abf_launch import build
    m = azure_mini(tmp_path)
    azure_launch(m, status="failed")
    for fn in (build.prepare_resume, build.prepare_relaunch):
        with pytest.raises(build.Refusal):
            fn(m.db, "r1", index_path=str(m.index))


# ---- US2: the screen -------------------------------------------------------------------------------------------------------

def azure_screen(tmp_path):
    m = azure_mini(tmp_path, workdir="az://labcontainer/work")
    azure_launch(m)
    _, b, row = prepared(m, "r1")
    return screen_of(b, row)


def test_the_clean_screen_says_what_is_deleted_and_what_is_kept_in_plain_words(tmp_path):
    # TC-024 .. TC-029 (AZC-PLT-06)
    from abf_launch import build
    text = azure_screen(tmp_path)
    assert "az://labcontainer/work/runs/r1/work/" in text and "r1" in text
    assert "結果（results）" in text and "不會被動" in text
    assert "永久刪除" in text
    assert build.CLEAN_AZ in text and "Blob 容器" in text and "只有這一個前綴" in text
    assert "軟刪除" in text and "版本控制" in text and "保留期" in text
    for word in ("$", "NT", "USD", "台幣", "元", "費用", "金額"):
        assert word not in text, word
    for word in ("Google", "gcloud", "7 天", "gs://", "S3", "s3://"):
        assert word not in text, word


def test_the_google_aws_and_slurm_screens_are_unchanged(tmp_path):
    # TC-030, TC-031
    from abf_launch import build
    m = Mini(tmp_path / "p")
    m.launch(RUN, ce="ce-g")
    m.launch("slurm-run", ce="ce-s")
    g = screen_of(*prepared_pair(m, RUN))
    s = screen_of(*prepared_pair(m, "slurm-run"))
    assert build.CLEAN_SOFT in g and build.CLEAN_BUCKET in g and "7 天" in g
    assert build.CLEAN_SOFT not in s and build.CLEAN_BUCKET not in s and build.CLEAN_AZ not in s and build.CLEAN_AZ not in g
    bundle = {"run_name": "r1", "work": "s3://lab-bucket/runs/r1/" + K, "ce": {"platform": AWS}}
    aws = build.as_text(build.clean_screen(bundle, None))
    assert "s3://lab-bucket/runs/r1/" + K + "/" in aws and build.CLEAN_S3 in aws and build.CLEAN_AZ not in aws


def prepared_pair(m, run):
    _, b, row = prepared(m, run)
    return b, row


# ---- US4: documents and borders --------------------------------------------------------------------------------------------

def test_docs_say_azure_can_clean_now():
    # TC-102, TC-104, TC-105, TC-106 (AZC-PLT-10)
    par = doc("SEQERA_PARITY.md")
    rows = [ln for ln in par.splitlines() if "`azbatch-platform`" in ln and ln.startswith("| Azure Batch")]
    assert rows == ["| Azure Batch (`azbatch-platform`) | Have (create + check + launch + cancel + upload + clean) | [ ] |"]
    assert "clean in azure-clean" not in par
    text = doc("PLATFORM.md")
    row = [ln for ln in text.splitlines() if ln.startswith("| `azbatch-platform`")]
    assert row == ["| `azbatch-platform` | Azure Batch | checked, launched and cleaned on the platform host (resume: not yet) |"]
    assert "az://<container>/<sub>/runs/<run>/work" in text
    assert "儲存體帳戶若開了軟刪除或版本控制，舊版本與已刪項目在保留期內仍佔空間" in text
    assert "az storage blob delete-batch" in text
    azure = text.split("### Azure Batch", 1)[1].split("### Uploading to Azure Batch", 1)[0]
    assert "a clean and an upload are refused" not in azure and "azure-clean" not in text
    tail = text.split("**Not yet.**", 1)[1].split("\n", 1)[0]
    assert "clean," not in tail and "resume or a relaunch" in tail
    # the Google and AWS sentences stay
    assert "bucket 若開了版本控管，清理後舊版本仍佔空間、仍收費" in text


def test_testing_md_has_the_hand_check_for_azure_clean():
    # TC-107
    text = doc("TESTING.md")
    head = "## Cleaning an Azure Batch work folder (azure-clean): the maintainer checks by hand"
    assert head in text
    body = text.split(head, 1)[1].split("\n## ", 1)[0]
    for needle in ("az storage blob list", "--prefix", "delete-batch", "--num-results", "軟刪除", "測試用"):
        assert needle in body, needle


def test_the_set_of_azure_job_kinds_differs_from_before_by_clean_work_only():
    # TC-118
    from abf_platform import compute_envs, jobs
    before = {"preflight", "launch_nextflow", "cancel_run", "put_upload", "pipeline_files"}
    assert set(compute_envs.CLOUD_JOB_KINDS[compute_envs.AZURE]) - before == {"clean_" "work"}
    assert jobs.DEADLINE_SECONDS["clean_work"] > 0
    src = (PLATFORM_DIR / "abf_platform" / "jobs.py").read_text(encoding="utf-8")
    assert not re.search(r"sched|cron|auto_confirm|auto-confirm|lifecycle", src, re.I)


def test_the_platform_stays_free_of_deleting_words_and_cloud_libraries():
    # TC-117, TC-123 (AZC-PLT-09)
    for rel in ("abf_platform/web.py", "abf_platform/web_board.py", "abf_platform/cloud_store.py", "abf_station/put_upload.py"):
        text = (PLATFORM_DIR / rel).read_text(encoding="utf-8")
        assert "azure-clean" not in text and "_clean_azure" not in text, rel
    for sub in ("abf_platform", "abf_launch"):
        for path in (PLATFORM_DIR / sub).glob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "delete-batch" not in text, path
    for path in (PLATFORM_DIR / "abf_station").glob("*.py"):
        if path.name != "clean.py":
            assert "delete-batch" not in path.read_text(encoding="utf-8"), path


def test_no_new_columns_a_migration_is_not_needed():
    # TC-116: work_cleaned_at is the column cloud-cleanup made; the schema has no azure-clean column
    from abf_platform import store
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "platform.db")
        store.connect_state(path).close()
        con = sqlite3.connect(path)
        cols = [r[1] for r in con.execute("PRAGMA table_info(launches)")]
        con.close()
    assert "work_cleaned_at" in cols and not [c for c in cols if "azure" in c.lower()]
