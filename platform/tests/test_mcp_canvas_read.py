# Nothing existing: the canvas backend (catalogue, compose, validate) had no MCP door; these are the tests of its five read-only tools.
"""canvas-mcp-read: find_module, describe_module, list_pipelines, get_pipeline, get_validation as MCP tools.
Test cases TC-001 ... TC-052 are named in the comments (specs/canvas-mcp-read, test cases file)."""
import json
import re
from pathlib import Path

import pytest

from human_harness import World, tool_json
from owner_harness import Duo, sql_rows
from helpers import tool_text

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "abf_platform"
FIXTURES = HERE / "fixtures" / "compose"
NEW = ["find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"]
NO = "沒有這個模組xyz"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def qc_graph():
    return json.loads((FIXTURES / "fastqc_multiqc" / "graph.json").read_text(encoding="utf-8"))


def pl():
    from abf_platform.actions import pipelines
    return pipelines


def make(d, caller, name="demo-qc"):
    return pl().create_pipeline(d.state, name=name, graph=qc_graph(), caller=caller)["pipeline"]["id"]


def call(w, name, args, caller=None):
    return w.call(name, args, caller=caller)


def fastqc_in_file():
    from abf_platform import catalogue
    return next(m for m in catalogue.load()["modules"] if m["name"] == "fastqc")


def assert_clean(text):
    assert "Traceback" not in text and "SELECT " not in text and not re.search(r"[A-Za-z]:\\|/home/|/mnt/", text)


# ---- US1 ----
def test_find_module_fastqc_shape(w):
    # TC-001 TC-002 TC-003 TC-004 TC-005
    from abf_platform import catalogue
    r = tool_json(call(w, "find_module", {"q": "fastqc"}))
    assert r["sha"] and r["sha"] == catalogue.load()["sha"]
    assert r["count"] == len(r["modules"]) >= 1
    m = next(x for x in r["modules"] if x["name"] == "fastqc")
    assert m["path"] and m["description"]
    want = fastqc_in_file()
    assert m["inputs"] == want["inputs"] and m["outputs"] == want["outputs"]
    assert all("sha" not in x for x in r["modules"])
    assert "hint" not in r


def test_find_module_nothing(w):
    # TC-006 TC-007 TC-014
    res = call(w, "find_module", {"q": NO})
    assert not res.is_error
    r = tool_json(res)
    assert r["count"] == 0 and r["modules"] == [] and r["sha"]
    assert r["hint"].strip() and "fastqc" in r["hint"]
    assert_clean(tool_text(res))


def test_describe_module(w):
    # TC-008 TC-009 TC-010 TC-014
    r = tool_json(call(w, "describe_module", {"name": "fastqc"}))
    assert r["found"] is True and r["name"] == "fastqc" and "inputs" in r and "outputs" in r
    res = call(w, "describe_module", {"name": NO})
    assert not res.is_error
    r = tool_json(res)
    assert r["found"] is False and r["name"] == NO
    assert NO in r["message"] and "find_module" in r["message"]
    assert_clean(tool_text(res))


def test_catalogue_is_public(w, d):
    # TC-011
    a = tool_json(call(w, "find_module", {"q": "fastqc"}, caller=d.a))
    b = tool_json(call(w, "find_module", {"q": "fastqc"}, caller=d.b))
    assert a == b


SMALL = {"sha": "abc123", "count": 1, "modules": [
    {"name": "toy", "path": "modules/nf-core/toy", "description": "a toy", "keywords": [],
     "inputs": [{"name": "reads"}], "outputs": [{"name": "out"}]}]}


def test_wrappers_with_data():
    # TC-012 TC-013
    from abf_platform.actions import catalogue as c
    r = c.find_module("toy", data=SMALL)
    assert r["sha"] == "abc123" and r["count"] == 1 and "hint" not in r
    m = r["modules"][0]
    assert m["name"] == "toy" and m["inputs"] == [{"name": "reads"}] and m["outputs"] == [{"name": "out"}] and "sha" not in m
    assert c.find_module("fastqc", data=SMALL)["count"] == 0
    assert c.describe_module("toy", data=SMALL)["found"] is True
    n = c.describe_module(NO, data=SMALL)
    assert n["found"] is False and NO in n["message"] and "find_module" in n["message"]


# ---- US2 ----
def test_owner_reads(w, d):
    # TC-015 TC-016 TC-017 TC-018 TC-019
    pid = make(d, d.a)
    lst = tool_json(call(w, "list_pipelines", {}, caller=d.a))
    assert [p["id"] for p in lst["pipelines"]] == [pid]
    assert {"name", "version", "n_nodes"} <= set(lst["pipelines"][0])
    g2 = {"nodes": [{"id": "x0", "module": "fastqc"}]}
    assert pl().update_pipeline(d.state, pid, graph=g2, caller=d.a)["ok"]
    assert tool_json(call(w, "get_pipeline", {"pipeline_id": pid}, caller=d.a))["version"] == 2
    v1 = tool_json(call(w, "get_pipeline", {"pipeline_id": pid, "version": 1}, caller=d.a))
    assert v1["version"] == 1
    assert tool_json(call(w, "get_validation", {"pipeline_id": pid}, caller=d.a))["validation"] is None
    assert pl().validate_pipeline(d.state, pid, caller=d.a)["ok"]
    got = tool_json(call(w, "get_validation", {"pipeline_id": pid}, caller=d.a))
    assert got["validation"] and got["version"] == 2


def snapshot(d):
    return [sql_rows(d.state, "SELECT * FROM %s" % t) for t in ("pipelines", "pipeline_versions", "pipeline_validations")]


def test_five_tools_write_nothing(w, d):
    # TC-020
    pid = make(d, d.a)
    pl().validate_pipeline(d.state, pid, caller=d.a)
    before = snapshot(d)
    for n, a in [("find_module", {"q": "fastqc"}), ("describe_module", {"name": "fastqc"}), ("list_pipelines", {}),
                 ("get_pipeline", {"pipeline_id": pid}), ("get_validation", {"pipeline_id": pid})]:
        call(w, n, a, caller=d.a)
    assert snapshot(d) == before


def test_other_user_sees_nothing(w, d):
    # TC-021 TC-022 TC-023 TC-024 TC-052
    pid = make(d, d.a, name="secret-qc")
    pl().validate_pipeline(d.state, pid, caller=d.a)
    assert tool_json(call(w, "list_pipelines", {}, caller=d.b))["pipelines"] == []
    texts = []
    for n in ("get_pipeline", "get_validation"):
        res = call(w, n, {"pipeline_id": pid}, caller=d.b)
        r = tool_json(res)
        assert r["found"] is False and "not found" in r["message"]
        texts.append(tool_text(res))
    for t in texts + [tool_text(call(w, "list_pipelines", {}, caller=d.b))]:
        assert "secret-qc" not in t and "fastqc" not in t
    ghost = 987654
    mine = tool_text(call(w, "get_pipeline", {"pipeline_id": pid}, caller=d.b)).replace(str(pid), "<id>")
    none = tool_text(call(w, "get_pipeline", {"pipeline_id": ghost}, caller=d.b)).replace(str(ghost), "<id>")
    assert mine == none
    for t in texts:
        assert "token" not in t.lower() and "password" not in t.lower()


def test_tools_equal_the_action_layer(w, d):
    # TC-025
    pid = make(d, d.a)
    pl().validate_pipeline(d.state, pid, caller=d.a)
    make(d, d.b, name="bobs-qc")
    for caller in (d.a, d.b):
        assert tool_json(call(w, "list_pipelines", {}, caller=caller)) == json.loads(json.dumps(pl().list_pipelines(d.state, caller=caller)))
    for n, fn in (("get_pipeline", pl().get_pipeline), ("get_validation", pl().get_validation)):
        assert tool_json(call(w, n, {"pipeline_id": pid}, caller=d.a)) == json.loads(json.dumps(fn(d.state, pid, caller=d.a)))


# ---- US3, US4 ----
def test_registration(w):
    # TC-026 TC-027 TC-041 TC-044 TC-045
    tools, _ = w.mcp([])
    names = {t.name for t in tools}
    assert set(NEW) <= names and "get_pipeline_version" not in names
    for t in tools:
        if t.name in NEW:
            assert t.annotations.read_only_hint is True
    assert {t.name for t in tools if t.annotations.read_only_hint is not True} == {"launch", "cancel", "forget", "resume", "relaunch"}
    assert not names & {"create_pipeline", "update_pipeline", "export_pipeline", "validate_pipeline", "launch_pipeline"}
    from abf_platform.actions import catalogue as c
    from abf_platform.actions import pipelines as p
    layer = {"find_module": c.find_module, "describe_module": c.describe_module, "list_pipelines": p.list_pipelines,
             "get_pipeline": p.get_pipeline, "get_validation": p.get_validation}
    assert set(layer) == set(NEW)
    src = (PKG / "mcp_server.py").read_text(encoding="utf-8")
    for n in NEW:
        assert re.search(r"(catalogue|pipeline)_actions\.%s\(" % n, src)


def test_chat_spec_starts(w):
    # TC-032
    from abf_platform.actions import chat_tools
    tools, _ = w.mcp([])
    chat_tools.classify_check(tools)


def test_import_style_and_not_exported():
    # TC-039 TC-040
    import abf_platform.actions as actions
    assert not hasattr(actions, "find_module") and not hasattr(actions, "describe_module")
    src = (PKG / "mcp_server.py").read_text(encoding="utf-8")
    assert "import abf_platform.actions.catalogue as catalogue_actions" in src
    assert "import abf_platform.actions.pipelines as pipeline_actions" in src
    assert not re.search(r"from \S*actions\S* import .*\b(catalogue|pipelines)\b", src)
