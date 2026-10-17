# Nothing existing: tests of spec 116b, the gaps the review of 116 found (paths in params, a run name that tells too much, links, runs without an owner); the rule is ours.
"""116b: the owner binding of 116 holds for the paths in params, for run names, for links, and old runs can be given an owner.
Test cases are named in the comments (TC-001 ...), see specs/116b-owner-gaps/test-case.md."""
import asyncio
import hashlib
import json
import os
import sqlite3
import time

import pytest

from human_harness import World, csrf_of, form_answer, pending_id_of
from owner_harness import Duo, SHARED, sql_exec, sql_rows

GENERIC = "this run name is taken; choose another"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def counts(d):
    return (len(d.w.jobs()), len(d.w.confirmations()), len(sql_rows(d.state, "SELECT * FROM launches")))


def bob_launch(d, params, run="run-b", answer=None):
    return d.launch(d.b, run=run, ce_name="b1", answer=answer, raw_args={"params": params})


def with_bob(d):
    d.bobs_environment()
    area_a = d.area(d.a)
    area_a.mkdir(parents=True, exist_ok=True)
    (area_a / "a.fq").write_text("x")
    d.area(d.b).mkdir(parents=True, exist_ok=True)
    (d.area(d.b) / "ref.txt").write_text("r")


# ---- US1: paths in params -------------------------------------------------------------------------------------------------

def test_tc001_tc011_a_params_path_into_the_folder_of_another_is_refused(d):
    # TC-001, TC-011
    with_bob(d)
    before = counts(d)
    out = bob_launch(d, {"ref": str(d.area(d.a) / "a.fq")}, answer=form_answer())
    assert out["ok"] is False and out["sent"] is False and "pending" != out.get("state")
    assert counts(d) == before


def test_tc002_a_params_path_in_my_own_folder_passes(d):
    # TC-002
    with_bob(d)
    out = bob_launch(d, {"ref": str(d.area(d.b) / "ref.txt")})
    assert out["ok"] is True and out["state"] == "pending"


def test_tc003_dotdot_is_resolved_before_the_check(d):
    # TC-003
    with_bob(d)
    out = bob_launch(d, {"ref": "%s/../alice/a.fq" % d.area(d.b)})
    assert out["ok"] is False and out["sent"] is False


def test_tc004_a_link_in_my_folder_to_a_file_of_another_is_refused(d):
    # TC-004
    with_bob(d)
    os.symlink(str(d.area(d.a) / "a.fq"), str(d.area(d.b) / "lnk"))
    out = bob_launch(d, {"ref": str(d.area(d.b) / "lnk")})
    assert out["ok"] is False and out["sent"] is False


def test_tc005_a_tilde_value_is_a_path(d):
    # TC-005
    with_bob(d)
    out = bob_launch(d, {"ref": "~/secret.txt"})
    assert out["ok"] is False and out["sent"] is False


def test_tc006_a_shared_reference_file_under_the_read_roots_passes(d):
    # TC-006
    with_bob(d)
    out = bob_launch(d, {"genome_fasta": "%s/genomes/g.fa" % SHARED})
    assert out["ok"] is True and out["state"] == "pending"


def test_tc007_a_path_outside_every_read_root_is_refused(d):
    # TC-007
    with_bob(d)
    out = bob_launch(d, {"ref": "/elsewhere/x.fa"})
    assert out["ok"] is False and out["sent"] is False and "範圍" in out["message"]


def test_tc008_plain_values_are_not_paths(d):
    # TC-008
    with_bob(d)
    out = bob_launch(d, {"genome": "GRCh38", "flag": True, "n": 4, "skip": "skip_qc"})
    assert out["ok"] is True and out["state"] == "pending"
    bundle = json.loads(d.w.sql("SELECT bundle_json FROM confirmations")[0]["bundle_json"])
    assert bundle["params"] == {"genome": "GRCh38", "flag": True, "n": 4, "skip": "skip_qc"}


def test_tc009_the_refusal_names_only_my_own_folder(d):
    # TC-009
    with_bob(d)
    out = bob_launch(d, {"ref": str(d.area(d.a) / "a.fq")})
    msg = out["message"]
    assert os.path.realpath(d.area(d.b)) in msg
    assert "alice" not in msg and "a.fq" not in msg


def test_tc010_the_terminal_and_stdio_keep_the_old_rule(d):
    # TC-010
    from abf_launch import build
    with_bob(d)
    for n, value in enumerate((str(d.area(d.a) / "a.fq"), "/elsewhere/x.fa")):
        ce, bundle = build.prepare_launch(d.state, ce="lab-a", pipeline="nf-core/ampliseq", revision="2.18.0", run_name="run-t%d" % n,
                                          samplesheet=str(d.sheet(d.a)), params={"ref": value})
        assert bundle["params"] == {"ref": value} and "upload_paths" not in bundle
        out = d.launch(None, run="run-s%d" % n, answer=form_answer(), sheet=d.sheet(d.a), raw_args={"params": {"ref": value}})
        assert out["sent"] is True, out


def test_tc049_the_same_lab_shares_nothing_here_either(d):
    # TC-049
    with_bob(d)
    assert {u["lab"] for u in sql_rows(d.w.ip.tokens, "SELECT lab FROM users")} == {"lab-x"}
    out = bob_launch(d, {"ref": str(d.area(d.a) / "a.fq")})
    assert out["ok"] is False and out["sent"] is False
    d.w.hand_over("r-lab", by=d.a)
    out = d.launch(d.b, run="r-lab", ce_name="b1", answer=form_answer())
    assert out["ok"] is False and GENERIC in out["message"]


# ---- US2: a run name that is taken ---------------------------------------------------------------------------------------

def test_tc012_tc015_a_name_of_another_user_gets_the_generic_words(d):
    # TC-012, TC-015
    with_bob(d)
    d.w.hand_over("r1", slurm=4242, by=d.a)
    before = counts(d)
    out = d.launch(d.b, run="r1", ce_name="b1", answer=form_answer())
    assert out["ok"] is False and out["sent"] is False
    assert out["message"].endswith(GENERIC)
    for leak in ("4242", "alice", "已送出", "等", "不明", "used already", "用過"):
        assert leak not in out["message"], leak
    assert counts(d) == before


def test_tc013_tc014_a_name_of_nobody_gets_the_same_words(d):
    # TC-013, TC-014
    with_bob(d)
    d.w.hand_over("r1", slurm=4242, by=d.a)
    d.add_launch_row("r0", None)
    sql_exec(d.state, "UPDATE launches SET slurm_job_id = 777 WHERE run_name = 'r0'")
    other = d.launch(d.b, run="r1", ce_name="b1", answer=form_answer())["message"]
    nobody = d.launch(d.b, run="r0", ce_name="b1", answer=form_answer())["message"]
    assert nobody == other and nobody.endswith(GENERIC)
    assert "777" not in nobody


def test_tc016_my_own_launch_keeps_the_detailed_words(d):
    # TC-016
    d.w.hand_over("r1", slurm=4242, by=d.a)
    out = d.launch(d.a, run="r1", answer=form_answer())
    assert out["ok"] is False and "run 名稱已用過" in out["message"] and "4242" in out["message"] and GENERIC not in out["message"]


def test_tc017_my_own_waiting_launch_keeps_its_words(d):
    # TC-017
    d.sent(d.a, run="r2")
    out = d.launch(d.a, run="r2", answer=form_answer(), raw_args={"params": {"other": 1}})
    assert out["ok"] is False and "還在等代理處理" in out["message"]


def test_tc018_my_own_unknown_launch_keeps_its_words(d):
    # TC-018
    d.add_launch_row("r3", d.a.user_id)
    out = d.launch(d.a, run="r3", answer=form_answer())
    assert out["ok"] is False and "結果不明" in out["message"]


def test_tc019_a_name_whose_launch_was_refused_is_still_free(d):
    # TC-019
    with_bob(d)
    d.sent(d.a, run="r4")
    sql_exec(d.state, "UPDATE jobs SET state = 'refused' WHERE kind = 'launch_nextflow'")
    out = d.launch(d.b, run="r4", ce_name="b1")
    assert out["ok"] is True and out["state"] == "pending"


def test_tc020_the_yes_after_the_name_was_taken_gets_the_generic_words(d):
    # TC-020
    from abf_platform import confirm
    with_bob(d)
    out = d.launch(d.b, run="r5", ce_name="b1")
    rid = pending_id_of(out["confirmation_url"])
    d.w.hand_over("r5", slurm=4242, by=d.a)
    jobs_before = len(sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'launch_nextflow'"))
    with pytest.raises(confirm.NotApproved) as e:
        confirm.approve(d.state, rid, "PAGE", d.b.user_id)
    assert GENERIC in str(e.value) and "4242" not in str(e.value)
    assert len(sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'launch_nextflow'")) == jobs_before


def test_tc021_the_terminal_keeps_the_detailed_words(d):
    # TC-021
    from abf_launch import build
    d.w.hand_over("r1", slurm=4242, by=d.a)
    with pytest.raises(build.Refusal) as e:
        build.prepare_launch(d.state, ce="lab-a", pipeline="nf-core/ampliseq", revision="2.18.0", run_name="r1",
                             samplesheet=str(d.sheet(d.a)))
    assert "4242" in str(e.value) and GENERIC not in str(e.value)


# ---- US3: links ----------------------------------------------------------------------------------------------------------

def listing(d, caller, ce, path):
    from abf_platform import actions
    n = len(sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'list_site_files'"))
    sql_exec(d.state, "UPDATE agents SET last_seen_at = ?", (time.time() + 3600,))
    os.environ["ABF_PLATFORM_DEADLINE_LIST_SITE_FILES"] = "0.3"
    try:
        out = asyncio.run(actions.list_site_files(d.state, ce, str(path), caller=caller))
    finally:
        del os.environ["ABF_PLATFORM_DEADLINE_LIST_SITE_FILES"]
    return out, len(sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'list_site_files'")) - n


def test_tc022_a_link_to_the_folder_of_another_cannot_be_listed(d):
    # TC-022
    with_bob(d)
    os.symlink(str(d.area(d.b)), str(d.area(d.a) / "to_bob"))
    out, queued = listing(d, d.a, "lab-a", d.area(d.a) / "to_bob")
    assert out["ok"] is False and queued == 0 and "自己的上傳資料夾" in out["message"]


def test_tc023_a_link_outside_the_uploads_folder_into_another_cannot_be_listed(d, tmp_path):
    # TC-023
    with_bob(d)
    outside = tmp_path / "shared-root"
    outside.mkdir()
    os.symlink(str(d.area(d.b)), str(outside / "lnk"))
    out, queued = listing(d, d.a, "lab-a", outside / "lnk")
    assert out["ok"] is False and queued == 0


def test_tc024_a_link_inside_my_own_folder_can_be_listed(d):
    # TC-024
    with_bob(d)
    (d.area(d.a) / "real").mkdir()
    os.symlink(str(d.area(d.a) / "real"), str(d.area(d.a) / "mine"))
    for p in (d.area(d.a) / "mine", d.area(d.a)):
        out, queued = listing(d, d.a, "lab-a", p)
        assert queued == 1, (p, out)


def test_tc025_a_folder_without_links_lists_as_before(d):
    # TC-025
    with_bob(d)
    out, queued = listing(d, d.b, "b1", d.area(d.b))
    assert queued == 1


def test_tc027_tc028_the_bundle_records_the_real_paths(d):
    # TC-027, TC-028
    from abf_launch import build
    from abf_platform import actions
    area = d.area(d.a)
    (area / "real").mkdir(parents=True)
    (area / "real" / "x.fq").write_text("x")
    os.symlink(str(area / "real" / "x.fq"), str(area / "lnk"))
    sheet = d.sheet(d.a, [str(area / "lnk")])
    real = os.path.realpath(area / "real" / "x.fq")
    ce, bundle = build.prepare_launch(d.state, ce="lab-a", pipeline="nf-core/ampliseq", revision="2.18.0", run_name="run-q",
                                      samplesheet=str(sheet), params={"ref": str(area / "lnk")}, owner=d.a.user_id,
                                      area=actions.caller_area(d.state, d.a))
    rec = bundle["upload_paths"]
    assert rec["area"] == os.path.realpath(area)
    pairs = {(e["given"], e["real"]) for e in rec["paths"]}
    assert (str(area / "lnk"), real) in pairs
    wheres = {e["where"] for e in rec["paths"]}
    assert any(x.startswith("samplesheet") for x in wheres) and "params ref" in wheres


def _bundle_with_link(d, target):
    from abf_launch import build
    from abf_platform import actions
    area = d.area(d.a)
    (area / "real").mkdir(parents=True, exist_ok=True)
    for n in ("x.fq", "y.fq"):
        (area / "real" / n).write_text(n)
    if os.path.lexists(area / "lnk"):
        os.remove(area / "lnk")
    os.symlink(str(area / "real" / target), str(area / "lnk"))
    sheet = d.sheet(d.a, [str(area / "lnk")], name="s.csv")
    return build.prepare_launch(d.state, ce="lab-a", pipeline="nf-core/ampliseq", revision="2.18.0", run_name="run-q",
                                samplesheet=str(sheet), owner=d.a.user_id, area=actions.caller_area(d.state, d.a))[1]


def test_tc029_a_swapped_link_makes_another_hash_and_the_old_yes_does_not_fit(d):
    # TC-029
    from abf_platform import common, jobs
    first = _bundle_with_link(d, "x.fq")
    second = _bundle_with_link(d, "y.fq")
    assert common.bundle_sha256(first) != common.bundle_sha256(second)
    sql_exec(d.state, "INSERT INTO confirmations (id, sha256, kind, created_at, caller_user_id, state, channel, confirmed_at) "
                      "VALUES ('c1', ?, 'launch', ?, ?, 'confirmed', 'PAGE', ?)",
             (common.bundle_sha256(first), time.time(), d.a.user_id, time.time()))
    with pytest.raises(jobs.JobRefused, match="不符"):
        jobs.enqueue_launch(d.state, "lab-a", second, "c1")
    assert jobs.enqueue_launch(d.state, "lab-a", first, "c1")


def test_tc050_nothing_new_is_made_on_the_site(d):
    # TC-050
    d.sent(d.a)
    bundle = json.loads(d.w.sql("SELECT args_json FROM jobs WHERE kind = 'launch_nextflow'")[0]["args_json"])["bundle"]
    assert bundle["run_folder"] == "/data/w1/runs/run-one" and "alice" not in json.dumps(bundle["ce"])
    assert "alice" not in bundle["files"]["head.sh"] + bundle["files"]["nextflow.config"] + bundle["run_folder"]
    assert set(bundle) - {"version", "agent", "ce", "run_name", "run_folder", "pipeline", "revision", "samplesheet", "params",
                          "path_columns", "account", "tower", "files"} == {"upload_paths"}


# ---- US4: runs assign ----------------------------------------------------------------------------------------------------

def owner_of(d, run):
    return [r["user_id"] for r in sql_rows(d.state, "SELECT user_id FROM launches WHERE run_name = ? ORDER BY id", (run,))]


def test_tc038_tc039_an_old_run_is_given_to_a_user(d):
    # TC-038, TC-039
    d.add_run("r-old", None)
    rc, out = d.w.ip.run("runs", "assign", "r-old", "--user", "alice")
    assert rc == 0, out
    assert "alice" in out and owner_of(d, "r-old") == [d.a.user_id]
    assert d.run_names(d.a) == ["r-old"] and d.run_names(d.b) == []


def test_tc040_only_the_newest_row_changes(d):
    # TC-040
    d.add_launch_row("r-x", None)
    d.add_launch_row("r-x", None)
    rc, out = d.w.ip.run("runs", "assign", "r-x", "--user", "alice")
    assert rc == 0, out
    assert owner_of(d, "r-x") == [None, d.a.user_id]


def test_tc041_nothing_else_changes(d):
    # TC-041
    d.add_launch_row("r-old", None)
    d.add_launch_row("r-other", None)
    cols = "id, run_name, run_folder, ce, agent, slurm_job_id, confirmed_at, job_id"
    before = [tuple(r) for r in sql_rows(d.state, "SELECT %s FROM launches ORDER BY id" % cols)]
    other = [tuple(r) for r in sql_rows(d.state, "SELECT * FROM launches WHERE run_name = 'r-other'")]
    rc, out = d.w.ip.run("runs", "assign", "r-old", "--user", "alice")
    assert rc == 0, out
    assert [tuple(r) for r in sql_rows(d.state, "SELECT %s FROM launches ORDER BY id" % cols)] == before
    assert [tuple(r) for r in sql_rows(d.state, "SELECT * FROM launches WHERE run_name = 'r-other'")] == other


def test_tc042_tc043_an_owned_run_needs_force(d):
    # TC-042, TC-043
    d.add_launch_row("r-owned", d.b.user_id)
    rc, out = d.w.ip.run("runs", "assign", "r-owned", "--user", "alice")
    assert rc != 0 and "--force" in out and owner_of(d, "r-owned") == [d.b.user_id]
    rc, out = d.w.ip.run("runs", "assign", "r-owned", "--user", "alice", "--force")
    assert rc == 0, out
    assert "bob" in out and "alice" in out and owner_of(d, "r-owned") == [d.a.user_id]


def test_tc044_an_unknown_user_is_refused(d):
    # TC-044
    d.add_launch_row("r-old", None)
    rc, out = d.w.ip.run("runs", "assign", "r-old", "--user", "nobody-here")
    assert rc != 0 and "nobody-here" in out and owner_of(d, "r-old") == [None]


def test_tc045_an_unknown_run_is_refused(d):
    # TC-045
    n = len(sql_rows(d.state, "SELECT * FROM launches"))
    rc, out = d.w.ip.run("runs", "assign", "no-such-run", "--user", "alice")
    assert rc != 0 and "no-such-run" in out
    assert len(sql_rows(d.state, "SELECT * FROM launches")) == n


def test_tc046_the_user_is_required(d):
    # TC-046
    d.add_launch_row("r-old", None)
    rc, out = d.w.ip.run("runs", "assign", "r-old")
    assert rc != 0 and "--user" in out and owner_of(d, "r-old") == [None]


def test_tc047_no_mcp_tool_or_web_route_assigns_a_run(d, w):
    # TC-047
    from abf_platform import mcp_server, web
    client = w.web()
    paths = " ".join(getattr(r, "path", "") for r in client.app.routes)
    assert "assign" not in paths and "owner" not in paths
    for mod in (mcp_server, web):
        src = open(mod.__file__, encoding="utf-8").read()
        assert "SET user_id" not in src and "assign" not in src.lower().replace("assign_orphans", "")


def test_tc048_there_are_no_roles_or_sharing(d):
    # TC-048
    d.add_launch_row("r-old", None)
    for flag in ("--role", "--lab", "--share"):
        rc, out = d.w.ip.run("runs", "assign", "r-old", "--user", "alice", flag, "x")
        assert rc != 0
    assert owner_of(d, "r-old") == [None]


# ---- 116b fix round: what is a path in params (ruling after the #125 review, item 3) ------------------------------------------

@pytest.mark.parametrize("value", ["..", ".", "./x", "../x", "a/../b"])
def test_ruling3_these_values_are_paths_and_are_confined(d, value):
    # ruling item 3: `..`, `.`, `./x`, `../x`, `a/../b`
    with_bob(d)
    (d.area(d.b) / "sub").mkdir()
    out = bob_launch(d, {"ref": value})
    assert out["ok"] is False and out["sent"] is False, (value, out)


@pytest.mark.parametrize("value", ["nf-core/rnaseq", "https://x/y", "s3://b/k"])
def test_ruling3_identifiers_and_addresses_are_not_paths(d, value):
    # ruling item 3: an owner/name identifier and a scheme URL pass
    with_bob(d)
    out = bob_launch(d, {"ref": value})
    assert out["ok"] is True and out["state"] == "pending", (value, out)


def test_ruling3_a_directory_name_is_a_path_and_is_recorded_and_a_link_one_to_another_is_refused(d):
    # ruling item 3: a name that is an existing folder of my own is judged as a path (recorded in upload_paths); as a link to another's folder it is refused
    with_bob(d)
    (d.area(d.b) / "sub").mkdir()
    out = bob_launch(d, {"ref": "sub"})
    assert out["ok"] is True and out["state"] == "pending", out
    bundle = json.loads(d.w.sql("SELECT bundle_json FROM confirmations")[0]["bundle_json"])
    assert any(e["where"] == "params ref" for e in bundle["upload_paths"]["paths"])
    os.symlink(str(d.area(d.a)), str(d.area(d.b) / "evil"))
    out = bob_launch(d, {"ref": "evil"}, run="run-b2")
    assert out["ok"] is False and out["sent"] is False, out


def test_ruling3_data_x_fq_is_confined_when_it_names_a_file_of_the_folder(d):
    # ruling item 3, `data/x.fq`: it matches the owner/name shape, so it is a path only when it names an existing file under my folder (the plan's rule);
    # then it is recorded and confined, and as a link to another's file it is refused. Not existing, it is left alone like nf-core/rnaseq.
    with_bob(d)
    (d.area(d.b) / "data").mkdir()
    (d.area(d.b) / "data" / "x.fq").write_text("x")
    out = bob_launch(d, {"ref": "data/x.fq"})
    assert out["ok"] is True and out["state"] == "pending", out
    bundle = json.loads(d.w.sql("SELECT bundle_json FROM confirmations")[0]["bundle_json"])
    assert any(e["where"] == "params ref" for e in bundle["upload_paths"]["paths"])
    os.remove(d.area(d.b) / "data" / "x.fq")
    os.symlink(str(d.area(d.a) / "a.fq"), str(d.area(d.b) / "data" / "x.fq"))
    out = bob_launch(d, {"ref": "data/x.fq"}, run="run-b2")
    assert out["ok"] is False and out["sent"] is False, out
