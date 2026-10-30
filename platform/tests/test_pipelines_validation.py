# Nothing existing: Seqera and nf-core keep no per-version record of a static check of a canvas graph; the owner rule (what is not yours answers like what does not exist) is this platform's own.
"""017c: the latest static check of each saved pipeline version is kept in the platform's own database (`actions.pipelines`
validate_pipeline / get_validation). Test cases are named in the comments (TC-053 ...), see specs/017c-validate/test-case.md."""
import json
import logging
import re
import sqlite3
from pathlib import Path

import pytest

from human_harness import World
from owner_harness import Duo, sql_exec, sql_rows

HERE = Path(__file__).resolve().parent
PLATFORM = HERE.parent
FIXTURES = HERE / "fixtures" / "compose"
MODULE = PLATFORM / "abf_platform" / "actions" / "pipelines.py"
SHA = "5ed90b42e78410e7411e9c6bdfeff33226d6c58e"
BAD = {"nodes": [{"id": "qc", "module": "fastqc"}, {"id": "s", "module": "samtools_sort"}],
       "edges": [{"from": {"node": "qc", "output": "html"}, "to": {"node": "s", "input": 2}}]}


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def pl():
    from abf_platform.actions import pipelines
    return pipelines


def qc_graph():
    return json.loads((FIXTURES / "fastqc_multiqc" / "graph.json").read_text(encoding="utf-8"))


def make(d, caller, name="demo-qc", graph=None):
    return pl().create_pipeline(d.state, name=name, graph=graph if graph is not None else qc_graph(), caller=caller)


def pid_of(r):
    return r["pipeline"]["id"]


def rows(d):
    return sql_rows(d.state, "SELECT * FROM pipeline_validations ORDER BY pipeline_id, version")


def count(d, table):
    try:
        return sql_rows(d.state, "SELECT COUNT(*) AS n FROM %s" % table)[0]["n"]
    except sqlite3.OperationalError:
        return 0


def words(text, name):
    return re.sub(re.escape(str(name)), "<name>", str(text))


def test_validate_pipeline_stores_and_get_validation_returns_it(d):
    # TC-053, TC-055, TC-056, TC-062, TC-063, TC-064, TC-089
    pid = pid_of(make(d, d.a))
    r = pl().validate_pipeline(d.state, pid, caller=d.a, clock=lambda: 1234.5)
    assert r["ok"] is True and (r["id"], r["name"], r["version"]) == (pid, "demo-qc", 1)
    v = r["validation"]
    assert v["ok"] is True and v["stale"] is False and v["validated_at"] == 1234.5
    assert sorted(v) == ["catalogue_sha", "checks", "findings", "ok", "open_inputs", "stale", "validated_at"]
    expected = json.loads((HERE / "fixtures" / "validate" / "good_fastqc_multiqc.expected.json").read_text(encoding="utf-8"))
    assert v["findings"] == expected["findings"]
    got = pl().get_validation(d.state, pid, caller=d.a)
    assert got["ok"] is True and got["validation"] == v and got["validation"]["stale"] is False
    cols = sorted(c["name"] for c in sql_rows(d.state, "PRAGMA table_info(pipeline_validations)"))
    assert cols == ["catalogue_sha", "graph_sha256", "pipeline_id", "result_json", "validated_at", "version"]
    row = rows(d)[0]
    assert row["catalogue_sha"] == SHA == json.loads(row["result_json"])["catalogue_sha"] and row["graph_sha256"]


def test_a_graph_with_an_error_is_ok_outside_and_not_ok_inside(d):
    # TC-054, TC-096
    pid = pid_of(make(d, d.a, graph=BAD))
    r = pl().validate_pipeline(d.state, pid, caller=d.a)
    assert r["ok"] is True and r["validation"]["ok"] is False
    f = [x for x in r["validation"]["findings"] if x["code"] == "META_MISMATCH"][0]
    assert "qc.html" in f["message"] and "s.2" in f["message"]


def test_get_validation_before_any_validation_is_none_not_an_error(d):
    # TC-057, TC-109
    pid = pid_of(make(d, d.a))
    pl().update_pipeline(d.state, pid, graph=BAD, caller=d.a)
    r = pl().get_validation(d.state, pid, caller=d.a)
    assert r["ok"] is True and r["validation"] is None
    assert count(d, "pipeline_validations") == 0


def test_revalidating_replaces_the_row_and_keeps_one_row_per_version(d):
    # TC-058, TC-059, TC-060
    pid = pid_of(make(d, d.a))
    pl().validate_pipeline(d.state, pid, caller=d.a, clock=lambda: 1.0)
    pl().validate_pipeline(d.state, pid, caller=d.a, clock=lambda: 2.0)
    assert len(rows(d)) == 1 and rows(d)[0]["validated_at"] == 2.0
    first = pl().get_validation(d.state, pid, 1, caller=d.a)["validation"]
    pl().update_pipeline(d.state, pid, graph=BAD, caller=d.a)
    assert pl().get_validation(d.state, pid, caller=d.a)["validation"] is None            # newest = version 2, not yet checked
    pl().validate_pipeline(d.state, pid, caller=d.a, clock=lambda: 3.0)
    assert [(r["version"]) for r in rows(d)] == [1, 2]
    assert pl().get_validation(d.state, pid, 1, caller=d.a)["validation"] == first
    assert pl().get_validation(d.state, pid, caller=d.a)["validation"]["ok"] is False


def test_stored_result_is_stale_when_the_catalogue_sha_changes(d):
    # TC-061, TC-110
    from abf_platform import catalogue
    pid = pid_of(make(d, d.a))
    pl().validate_pipeline(d.state, pid, caller=d.a, clock=lambda: 5.0)
    before = [dict(r) for r in rows(d)]
    other = dict(catalogue.load(), sha="somethingelse")
    got = pl().get_validation(d.state, pid, caller=d.a, data=other)["validation"]
    assert got["stale"] is True and got["ok"] is True and got["catalogue_sha"] == SHA and got["validated_at"] == 5.0
    assert [dict(r) for r in rows(d)] == before


def test_not_found_and_other_users(d):
    # TC-070 .. TC-075, TC-081
    pid = pid_of(make(d, d.a))
    pl().validate_pipeline(d.state, pid, caller=d.a)
    n = count(d, "pipeline_validations")
    for fn in (pl().validate_pipeline, pl().get_validation):
        gone = fn(d.state, 999999, caller=d.b)
        mine = fn(d.state, 999999, caller=d.a)
        theirs = fn(d.state, pid, caller=d.b)
        assert theirs["ok"] is False and "找不到這個組合" in theirs["message"] and "validation" not in theirs
        assert words(theirs["message"], pid) == words(gone["message"], 999999) == words(mine["message"], 999999)
        assert re.search(r"\([ -~]+\)", theirs["message"])
    assert count(d, "pipeline_validations") == n
    other = pid_of(make(d, d.b, name="bobs"))
    assert pl().validate_pipeline(d.state, other, caller=d.a)["ok"] is False
    assert count(d, "pipeline_validations") == n


def test_terminal_caller_none_sees_everything(d):
    # TC-076
    a, b = pid_of(make(d, d.a)), pid_of(make(d, d.b, name="bobs"))
    for p in (a, b):
        assert pl().validate_pipeline(d.state, p, caller=None)["ok"] is True
        assert pl().get_validation(d.state, p, caller=None)["validation"]["ok"] is True


def test_validate_makes_no_confirmation_or_job(d, tmp_path):
    # TC-077, TC-078
    pid = pid_of(make(d, d.a))
    tables = ["jobs", "confirmations", "launches"]
    counts = lambda: [count(d, t) for t in tables]
    before = counts()
    files = sorted(p.relative_to(d.state.parent).as_posix() for p in d.state.parent.rglob("*") if p.is_file() and not p.name.startswith("platform.db"))
    pl().validate_pipeline(d.state, pid, caller=d.a)
    pl().get_validation(d.state, pid, caller=d.a)
    assert counts() == before
    after = sorted(p.relative_to(d.state.parent).as_posix() for p in d.state.parent.rglob("*") if p.is_file() and not p.name.startswith("platform.db"))
    assert after == files


def test_validation_table_is_lazy_and_old_db_works(d):
    # TC-065, TC-066
    from abf_platform import store
    assert "pipeline_validations" not in store.STATE_SCHEMA
    pid = pid_of(make(d, d.a))
    sql_exec(d.state, "DROP TABLE pipeline_validations")
    r = pl().get_validation(d.state, pid, caller=d.a)
    assert r["ok"] is True and r["validation"] is None
    sql_exec(d.state, "DROP TABLE pipeline_validations")
    assert pl().validate_pipeline(d.state, pid, caller=d.a)["ok"] is True


def test_pipeline_versions_stay_append_only(d):
    # TC-067
    pid = pid_of(make(d, d.a))
    before = sql_rows(d.state, "SELECT graph_json FROM pipeline_versions")[0]["graph_json"]
    pl().validate_pipeline(d.state, pid, caller=d.a)
    for stmt in ("UPDATE pipeline_versions SET version = 9", "DELETE FROM pipeline_versions"):
        with pytest.raises(sqlite3.DatabaseError):
            sql_exec(d.state, stmt)
    assert sql_rows(d.state, "SELECT graph_json FROM pipeline_versions")[0]["graph_json"] == before


def test_error_messages_hide_internals(d, caplog):
    # TC-079, TC-080
    caplog.set_level(logging.DEBUG)
    pid = pid_of(make(d, d.a))
    seen = [pl().validate_pipeline(d.state, pid, caller=d.b), pl().get_validation(d.state, pid, caller=d.b),
            pl().validate_pipeline(d.state, 4242, caller=d.a), pl().validate_pipeline(d.state, pid, 7, caller=d.a),
            pl().validate_pipeline(d.state, pid, caller=d.a), pl().get_validation(d.state, pid, caller=d.a)]
    text = json.dumps(seen, ensure_ascii=False) + caplog.text
    for word in ("SELECT", "INSERT", "sqlite", "Traceback", "platform.db", str(d.state)):
        assert word not in text, word
    assert not re.search(r"abf_[a-z]+_[A-Za-z0-9]{8,}|scrypt|password", text, re.I)


def test_no_program_is_started_by_validation():
    # TC-083
    src = MODULE.read_text(encoding="utf-8")
    start = src.index("CREATE TABLE IF NOT EXISTS pipeline_validations")
    mine = src[start:src.index(");", start)] + src[src.index("def validate_pipeline"):]
    for word in ("subprocess", "os.system", "sbatch", "nextflow", "lint", "stub"):
        assert word not in mine.lower(), word


def test_the_actions_package_does_not_export_the_new_functions():
    # TC-068, TC-104
    import abf_platform.actions as actions
    for n in ("validate_pipeline", "get_validation"):
        assert not hasattr(actions, n)


# ---- regex-dollar-newline: the pipeline name ends with \Z ---------------------------------------------------------------

def test_regex_dollar_newline_tc010_011_012_name_with_newline_is_refused_and_nothing_is_saved(d):
    # regex-dollar-newline TC-010, TC-011, TC-012
    before = (count(d, "pipelines"), count(d, "pipeline_versions"))
    r = make(d, d.a, name="abc\n")
    assert r["ok"] is False
    assert (count(d, "pipelines"), count(d, "pipeline_versions")) == before
    upper = make(d, d.a, name="ABC")
    assert upper["ok"] is False
    assert r["message"] == upper["message"]


def test_regex_dollar_newline_tc013_legal_names_are_created(d):
    # regex-dollar-newline TC-013
    assert make(d, d.a, name="abc")["ok"] is True
    assert make(d, d.a, name="a" + "b" * 39)["ok"] is True


def test_regex_dollar_newline_tc050_old_refused_names_stay_refused(d):
    # regex-dollar-newline TC-050
    assert make(d, d.a, name="a" * 41)["ok"] is False
