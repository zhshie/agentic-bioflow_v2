# Nothing existing: tests of the pipeline registration record and its actions (specs/pipe-reg-store); the record is this platform's own.
"""pipe-reg-store: the table `pipeline_registrations` and the four actions over it. TC-nnn in the comments are those of
specs/pipe-reg-store/test-case.md."""
import json
import re
import sqlite3
import time

import pytest

from helpers import PLATFORM_DIR
from human_harness import World
from test_web_settings import make_env, make_agent

PKG = PLATFORM_DIR / "abf_platform"
RN, R1, R2 = "nf-core/rnaseq", "3.26.0", "3.25.0"
NANO4 = [{"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "module": "biology/a/2.18.0", "home": "A_HOME"},
         {"pipeline": "nf-core/rnaseq", "revision": "3.26.0", "module": "biology/r/3.26.0", "home": "R_HOME"},
         {"pipeline": "nf-core/sarek", "revision": "3.9.0", "module": "biology/s/3.9.0", "home": "S_HOME"},
         {"pipeline": "nf-core/scrnaseq", "revision": "4.2.0", "module": "biology/c/4.2.0", "home": "C_HOME"}]
GBATCH = {"project": "lab-project-1", "location": "europe-west2", "workDir": "gs://lab-bucket/work"}
ALL_COLUMNS = {"compute_env", "pipeline", "revision", "source", "state", "reason", "failed_step", "test_run", "tested_at", "updated_at"}


def A():
    from abf_platform import actions
    return actions


@pytest.fixture
def w(tmp_path, monkeypatch):
    from abf_platform import compute_envs
    world = World(tmp_path, monkeypatch)
    world.base_env = compute_envs.get(world.ip.state_db, "lab-a")
    world.ann = world.user("ann")      # the first person owns lab-a
    world.bob = world.user("bob")
    world.db = world.ip.state_db
    return world


def rows(w, where="1"):
    con = sqlite3.connect(str(w.db))
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute("SELECT * FROM pipeline_registrations WHERE " + where)]
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def count(w, table="pipeline_registrations"):
    con = sqlite3.connect(str(w.db))
    try:
        return con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        con.close()


def propose(w, ce="lab-a", pipeline=RN, revision=R1, caller=None, by="PAGE"):
    a = A()
    return a.propose_pipeline_registration(w.db, ce=ce, pipeline=pipeline, revision=revision,
                                           confirmed_by=getattr(a, by) if isinstance(by, str) else by, caller=caller or w.ann)


def remove(w, ce="lab-a", pipeline=RN, revision=R1, caller=None, by="PAGE"):
    a = A()
    return a.remove_pipeline_registration(w.db, ce=ce, pipeline=pipeline, revision=revision,
                                          confirmed_by=getattr(a, by) if isinstance(by, str) else by, caller=caller or w.ann)


def listing(w, ce="lab-a", caller=None):
    return A().list_pipeline_registrations(w.db, ce=ce, caller=caller or w.ann)


def set_legacy(w, ce="lab-a", entries=NANO4):
    from abf_platform import compute_envs
    compute_envs.update(w.db, ce, {"config": {"sitePipelines": entries}})


def cloud_env(w, caller=None):
    from abf_platform import compute_envs
    caller = caller or w.ann
    compute_envs.create(w.db, {"name": "gcb", "platform": "googlebatch-platform", "agent": "ag-gcb", "owner_user_id": caller.user_id, "config": GBATCH})
    return "gcb"


NOT_FOUND = {"ok": False, "field": None, "message": "找不到所選的運算環境 (compute environment not found)"}


# ---- 1 propose and the record -----------------------------------------------------------------------------------------------
def test_propose_creates_checking_row(w):
    # TC-001, TC-002
    assert propose(w)["ok"] is True
    items = listing(w)["items"]
    assert len(items) == 1
    i = items[0]
    assert (i["state"], i["source"], i["compute_env"], i["pipeline"], i["revision"]) == ("checking", "site-module", "lab-a", RN, R1)
    assert ALL_COLUMNS <= set(i)


def test_propose_on_cloud_env_is_remote(w):
    # TC-003, TC-059, TC-060
    gcb = cloud_env(w)
    assert propose(w, ce=gcb)["ok"]
    assert propose(w)["ok"]
    only = listing(w, ce=gcb)["items"]
    assert len(only) == 1 and only[0]["source"] == "remote" and only[0]["state"] == "checking"
    both = listing(w, ce=None)["items"]
    assert {(i["compute_env"], i["source"]) for i in both} == {("gcb", "remote"), ("lab-a", "site-module")}
    assert [i["compute_env"] for i in listing(w, ce="lab-a")["items"]] == ["lab-a"]


def test_duplicate_propose_is_not_doubled(w):
    # TC-004
    propose(w)
    assert propose(w) == {"ok": True, "changed": False, "state": "checking"}
    assert len(rows(w)) == 1


def test_removed_then_proposed_again_returns_to_checking(w):
    # TC-005
    propose(w)
    remove(w)
    assert listing(w)["items"] == []
    assert propose(w)["ok"]
    assert len(rows(w)) == 1 and listing(w)["items"][0]["state"] == "checking"


def test_versions_and_environments_are_separate_keys(w):
    # TC-006, TC-007, TC-049
    propose(w, revision=R1)
    propose(w, revision=R2)
    assert sorted(i["revision"] for i in listing(w)["items"]) == [R2, R1]
    make_agent(w, w.ann, "ag-b")
    make_env(w, w.ann, "lab-b", "ag-b")
    propose(w, ce="lab-b")
    assert sorted(r["compute_env"] for r in rows(w, "revision = '%s'" % R1)) == ["lab-a", "lab-b"]
    assert [i["compute_env"] for i in listing(w, ce="lab-b")["items"]] == ["lab-b"]
    remove(w, ce="lab-a")
    assert [i["revision"] for i in listing(w, ce="lab-a")["items"]] == [R2]
    assert [i["compute_env"] for i in listing(w, ce="lab-b")["items"]] == ["lab-b"]
    assert rows(w, "compute_env = 'lab-b'")[0]["stage"] == "checking"


def test_propose_over_a_legacy_entry_makes_one_row_not_legacy(w):
    # TC-008
    set_legacy(w)
    propose(w)
    same = [i for i in listing(w)["items"] if (i["pipeline"], i["revision"]) == (RN, R1)]
    assert len(same) == 1 and same[0]["state"] == "checking" and not same[0].get("legacy")


def test_table_is_created_on_first_use_and_old_db_still_opens(w):
    # TC-009
    assert rows(w) == [] and count(w) == 0
    con = sqlite3.connect(str(w.db))
    assert con.execute("SELECT 1 FROM sqlite_master WHERE name = 'pipeline_registrations'").fetchone() is None
    con.close()
    assert listing(w) == {"ok": True, "items": []}
    assert propose(w)["ok"]
    assert w.sql("SELECT name FROM compute_envs WHERE name = 'lab-a'")
    w.sql("SELECT * FROM jobs")


# ---- 2 validation ---------------------------------------------------------------------------------------------------------
def bad(w, **kw):
    before = count(w)
    out = propose(w, **kw)
    assert out["ok"] is False and count(w) == before
    return out


@pytest.mark.parametrize("name", ["nf-core/A B", "../x"])
def test_bad_name_names_the_field(w, name):
    # TC-010, TC-011
    out = bad(w, pipeline=name)
    assert out["field"] == "pipeline" and out["message"].startswith("管線名稱格式不合")


@pytest.mark.parametrize("name", ["", 7])
def test_empty_or_non_string_pipeline(w, name):
    # TC-012
    out = bad(w, pipeline=name)
    assert out == {"ok": False, "field": "pipeline", "message": "pipeline 必須填寫 (pipeline is required)"}


def test_empty_revision(w):
    # TC-013
    assert bad(w, revision="") == {"ok": False, "field": "revision", "message": "revision 必須填寫 (revision is required)"}


@pytest.mark.parametrize("rev", ["main", "1", "v1.", "1.2.3 ", "a" * 39])
def test_bad_revision_names_the_field(w, rev):
    # TC-014, TC-015, TC-016
    out = bad(w, revision=rev)
    assert out["field"] == "revision" and "revision" in out["message"]


def test_good_revisions(w):
    # TC-017
    for rev in ("3.26.0", "v2.1", "a" * 40):
        assert propose(w, revision=rev)["ok"]
    assert len(listing(w)["items"]) == 3


@pytest.mark.parametrize("ce", ["", 5])
def test_bad_ce(w, ce):
    # TC-018
    assert bad(w, ce=ce)["field"] == "ce"


def test_validation_order(w):
    # TC-019, TC-020
    assert bad(w, pipeline="nf-core/A B", revision="main")["field"] == "pipeline"
    assert bad(w, ce="nope", pipeline="nf-core/A B") == NOT_FOUND


def test_version_and_name_rules_are_the_existing_ones(w, monkeypatch):
    # TC-021
    from abf_platform import actions, compute_envs
    text = (PKG / "actions" / "registrations.py").read_text(encoding="utf-8")
    assert "compute_envs._REVISION" in text and "_SP_NAME" in text and not re.search(r"re\.compile", text)
    assert propose(w, revision="main")["ok"] is False
    monkeypatch.setattr(compute_envs, "_REVISION", re.compile(r".+"))
    assert propose(w, revision="main")["ok"] is True
    monkeypatch.setattr(actions, "_SP_NAME", re.compile(r".+"))
    assert propose(w, pipeline="whatever", revision="3.1")["ok"] is True


def test_messages_are_bilingual_and_plain(w):
    # TC-022, TC-069
    outs = [propose(w, pipeline="nf-core/A B"), propose(w, pipeline=""), propose(w, revision=""), propose(w, revision="main"),
            propose(w, ce=""), propose(w, ce="nope"), remove(w), propose(w, caller=w.bob)]
    for o in outs:
        assert o["ok"] is False and re.search(r"\(.+\)$", o["message"]) and re.search("[　-鿿]", o["message"])
        assert not re.search(r"Traceback|SELECT|INSERT|[A-Za-z]:\\|/home/|/tmp/", o["message"])


# ---- 3 confirmation channel -----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("by", [None, "alice"])
def test_unconfirmed_propose_and_remove_change_nothing(w, by):
    # TC-023, TC-024, TC-025, TC-026
    from abf_platform import jobs
    before = count(w)
    with pytest.raises(jobs.JobRefused, match="no human confirmation channel"):
        propose(w, by=by)
    assert count(w) == before
    propose(w)
    n = count(w)
    for call in (lambda: propose(w, pipeline="nf-core/A B", by=by), lambda: remove(w, by=by), lambda: remove(w, pipeline="nf-core/none", by=by),
                 lambda: propose(w, ce="nope", by=by)):
        with pytest.raises(jobs.JobRefused, match="no human confirmation channel"):
            call()
    assert count(w) == n and rows(w)[0]["stage"] == "checking" and len(listing(w)["items"]) == 1


# ---- 4 scope --------------------------------------------------------------------------------------------------------------
def test_nothing_is_queued_and_site_list_is_not_touched(w):
    # TC-027, TC-028, TC-031, TC-068
    set_legacy(w)
    cfg = w.sql("SELECT config_json FROM compute_envs WHERE name = 'lab-a'")[0][0]
    jobs_n, conf_n = count(w, "jobs"), count(w, "confirmations")
    propose(w, pipeline="nf-core/fetchngs", revision="1.12.0")
    propose(w, pipeline="nf-core/fetchngs", revision="1.12.0")
    remove(w, pipeline="nf-core/fetchngs", revision="1.12.0")
    propose(w, pipeline="nf-core/fetchngs", revision="1.12.0")
    assert (count(w, "jobs"), count(w, "confirmations")) == (jobs_n, conf_n)
    assert w.sql("SELECT config_json FROM compute_envs WHERE name = 'lab-a'")[0][0] == cfg
    from abf_platform.actions import registrations
    assert registrations._start_check({}, {}) is None
    kinds = w.sql("SELECT sql FROM sqlite_master WHERE name = 'jobs'")[0][0]
    assert len(re.findall(r"'[a-z_]+'", re.search(r"kind TEXT NOT NULL CHECK \(kind IN \(([^)]*)\)", kinds).group(1))) == 10


# ---- 5 owner rules --------------------------------------------------------------------------------------------------------
def test_second_user_cannot_read_or_write(w):
    # TC-032, TC-033, TC-034, TC-035, TC-036
    set_legacy(w)
    propose(w)
    n = count(w)
    mine = A().list_pipeline_registrations(w.db, ce="lab-a", caller=w.bob)
    nope = A().list_pipeline_registrations(w.db, ce="no-such-env", caller=w.bob)
    assert mine == nope == NOT_FOUND
    assert A().list_pipeline_registrations(w.db, ce=None, caller=w.bob) == {"ok": True, "items": []}
    assert A().list_registered_pipelines(w.db, ce="lab-a", caller=w.bob) == NOT_FOUND
    assert propose(w, caller=w.bob, pipeline="nf-core/sarek", revision="3.9.0") == NOT_FOUND
    assert count(w) == n
    assert remove(w, caller=w.bob) == NOT_FOUND
    assert rows(w)[0]["stage"] == "checking"


def test_each_user_sees_only_their_own(w):
    # TC-038
    make_agent(w, w.bob, "ag-bob")
    make_env(w, w.bob, "bob-env", "ag-bob")
    propose(w)
    propose(w, ce="bob-env", caller=w.bob, revision=R2)
    assert [i["revision"] for i in listing(w, ce=None)["items"]] == [R1]
    assert [i["revision"] for i in listing(w, ce=None, caller=w.bob)["items"]] == [R2]


def test_no_token_in_any_answer(w):
    # TC-069
    from abf_platform import store
    assert not store.__dict__.get("TOKEN_MARK")
    text = json.dumps([propose(w, caller=w.bob), remove(w, caller=w.bob), listing(w, caller=w.bob)])
    assert "Traceback" not in text and "token" not in text.lower()


# ---- 7 remove -------------------------------------------------------------------------------------------------------------
def test_remove_marks_removed_and_keeps_the_row(w):
    # TC-044, TC-047
    propose(w)
    assert remove(w) == {"ok": True, "changed": True, "state": "removed"}
    assert listing(w)["items"] == [] and [r["stage"] for r in rows(w)] == ["removed"]
    assert remove(w) == {"ok": True, "changed": False, "state": "removed"}
    assert len(rows(w)) == 1


def test_remove_unknown_registration_is_refused(w):
    # TC-045, TC-048
    out = remove(w)
    assert out == {"ok": False, "field": None, "message": "找不到此登記紀錄 (registration not found)"} and rows(w) == []
    assert remove(w, ce="nope") == NOT_FOUND


def test_remove_legacy_only_is_refused(w):
    # TC-046
    set_legacy(w)
    cfg = w.sql("SELECT config_json FROM compute_envs WHERE name = 'lab-a'")[0][0]
    assert remove(w)["message"] == "找不到此登記紀錄 (registration not found)"
    assert rows(w) == [] and w.sql("SELECT config_json FROM compute_envs WHERE name = 'lab-a'")[0][0] == cfg


def test_removed_row_suppresses_legacy_entry(w):
    # TC-050
    set_legacy(w)
    cfg = w.sql("SELECT config_json FROM compute_envs WHERE name = 'lab-a'")[0][0]
    propose(w)
    remove(w)
    got = {(i["pipeline"], i["revision"]) for i in listing(w)["items"]}
    assert (RN, R1) not in got and len(got) == 3
    assert w.sql("SELECT config_json FROM compute_envs WHERE name = 'lab-a'")[0][0] == cfg


# ---- 8 listing and legacy -------------------------------------------------------------------------------------------------
def test_legacy_site_pipelines_show_as_awaiting_test(w):
    # TC-051, TC-052, TC-037, TC-067
    set_legacy(w)
    first = listing(w)
    assert first["ok"] and len(first["items"]) == 4
    assert all(i["state"] == "awaiting_test" and i["source"] == "site-module" and i["legacy"] is True for i in first["items"])
    assert {(i["pipeline"], i["revision"]) for i in first["items"]} == {(p["pipeline"], p["revision"]) for p in NANO4}
    A().list_registered_pipelines(w.db, ce="lab-a", caller=w.ann)
    assert count(w) == 0
    assert A().list_pipeline_registrations(w.db, ce=None, caller=w.bob)["items"] == []


def test_list_shapes_and_removed_hidden(w):
    # TC-053, TC-054
    assert listing(w) == {"ok": True, "items": []}
    propose(w)
    propose(w, revision=R2)
    remove(w, revision=R2)
    assert [i["revision"] for i in listing(w)["items"]] == [R1]


def test_registered_list_excludes_legacy_and_checking(w):
    # TC-055, TC-056, TC-057
    set_legacy(w)
    propose(w, pipeline="nf-core/fetchngs", revision="1.12.0")
    assert A().list_registered_pipelines(w.db, ce="lab-a", caller=w.ann) == {"ok": True, "items": []}
    assert all(i["state"] != "registered" for i in listing(w)["items"])
    con = sqlite3.connect(str(w.db))
    now = time.time()
    for n, st in enumerate(("awaiting_test", "testing", "failed")):
        con.execute("INSERT INTO pipeline_registrations (owner, compute_env, pipeline, revision, source, stage, created_at, updated_at) "
                    "VALUES (?, 'lab-a', 'nf-core/x', ?, 'site-module', ?, ?, ?)", (str(w.ann.user_id), "1.%d" % n, st, now, now))
    con.commit()
    con.close()
    assert A().list_registered_pipelines(w.db, ce="lab-a", caller=w.ann)["items"] == []


def test_state_is_the_stage(w):
    # TC-058
    from abf_platform.actions import registrations
    stages = ("checking", "preparing", "awaiting_test", "testing", "failed")
    propose(w)
    con = sqlite3.connect(str(w.db))
    now = time.time()
    for n, st in enumerate(stages):
        con.execute("INSERT INTO pipeline_registrations (owner, compute_env, pipeline, revision, source, stage, created_at, updated_at) "
                    "VALUES (?, 'lab-a', 'nf-core/y', ?, 'site-module', ?, ?, ?)", (str(w.ann.user_id), "2.%d" % n, st, now, now))
    con.commit()
    con.close()
    for r in rows(w, "pipeline = 'nf-core/y'"):
        assert registrations._state(r, None) == r["stage"]
    assert {i["state"] for i in listing(w)["items"] if i["pipeline"] == "nf-core/y"} == set(stages)


# ---- 9 table --------------------------------------------------------------------------------------------------------------
def test_table_constraints(w):
    # TC-061 .. TC-065
    propose(w)
    con = sqlite3.connect(str(w.db))
    now = time.time()

    def ins(rev="9.9.9", source="site-module", stage="checking", step=None, pipe="nf-core/z"):
        con.execute("INSERT INTO pipeline_registrations (owner, compute_env, pipeline, revision, source, stage, failed_step, created_at, updated_at) "
                    "VALUES ('o', 'e', ?, ?, ?, ?, ?, ?, ?)", (pipe, rev, source, stage, step, now, now))

    ins()
    with pytest.raises(sqlite3.IntegrityError):
        ins()
    with pytest.raises(sqlite3.IntegrityError):
        ins(rev="1.0", source="bogus")
    for k, s in enumerate(("site-module", "site-fetch", "remote")):
        ins(rev="3.%d" % k, source=s)
    for k, s in enumerate(("registered", "bogus")):
        with pytest.raises(sqlite3.IntegrityError):
            ins(rev="4.%d" % k, stage=s)
    for k, s in enumerate(("checking", "preparing", "awaiting_test", "testing", "failed", "removed")):
        ins(rev="5.%d" % k, stage=s)
    with pytest.raises(sqlite3.IntegrityError):
        ins(rev="6.0", step="bogus")
    for k, s in enumerate((None, "check", "prepare", "test")):
        ins(rev="7.%d" % k, step=s)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    con.close()
    assert "pipeline_registrations" in names
    from abf_platform import store
    assert "pipeline_registrations" not in store.STATE_SCHEMA


def test_composed_pipeline_tables_unaffected(w):
    # TC-065
    from abf_platform.actions import pipelines
    propose(w)
    con = sqlite3.connect(str(w.db))
    pipelines._table(con)
    con.close()
    assert count(w, "pipelines") == 0 and count(w, "pipeline_versions") == 0 and count(w, "pipeline_validations") == 0
