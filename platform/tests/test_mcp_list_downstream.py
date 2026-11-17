# Nothing existing: no test covered the read-only MCP tool list_downstream (spec downstream-method-catalog).
"""downstream-method-catalog: list_downstream over MCP. Test cases TC-M* are named in the comments. No A/B counts are pinned here:
the packaged catalogue ages with the real date (TC-M02 compares with a direct call)."""
import ast
import hashlib
import json
from pathlib import Path

import pytest

from human_harness import World
from helpers import tool_json, tool_text

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "abf_platform"
DATA = PKG / "data" / "downstream-methods.json"
MCP_SRC = PKG / "mcp_server.py"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def tools(w):
    ts, _ = w.mcp([])
    return {t.name: t for t in ts}


def methods():
    return [e["method"] for e in json.loads(DATA.read_text(encoding="utf-8"))["entries"]]


def test_ld01_tool_is_registered_read_only_with_one_string_param(w):
    # TC-M01 TC-M06 TC-N04
    ts = tools(w)
    t = ts["list_downstream"]
    assert t.annotations.read_only_hint is True
    s = t.input_schema
    assert s["required"] == ["pipeline"] and list(s["properties"]) == ["pipeline"] and s["properties"]["pipeline"]["type"] == "string"
    assert len(ts) == 27 and sum(1 for x in ts.values() if x.annotations and x.annotations.read_only_hint) == 17


def test_ld02_call_returns_the_catalogue_rows(w):
    # TC-M02 TC-M05 TC-M17
    from abf_platform import downstream_catalog
    d = tool_json(w.call("list_downstream", {"pipeline": "ampliseq"}))
    want = downstream_catalog.list_downstream("ampliseq")
    assert d["count"] == want["count"] and [m["id"] for m in d["methods"]] == [m["id"] for m in want["methods"]]
    for m in d["methods"]:
        assert {"id", "method", "link", "grade", "declared_grade", "downgraded", "version_pin", "license", "doi", "inputs",
                "non_interactive_plot", "singularity", "reviewed", "notes"} <= set(m)
    r = w.call("list_downstream", {"pipeline": "scrnaseq"})
    assert not r.is_error and tool_json(r)["count"] == 0 and tool_json(r)["note"] == "no certified downstream methods for this pipeline"


def test_ld02_empty_pipeline_is_a_clean_tool_error(w):
    # TC-M03 TC-M04
    r = w.call("list_downstream", {"pipeline": ""})
    text = tool_text(r)
    assert r.is_error and "pipeline" in text and "請" in text
    for bad in ("Traceback", 'File "', ".py", "/home", "/mnt/", "C:\\"):
        assert bad not in text


def test_ld03_nothing_is_pushed_into_instructions():
    # TC-M10
    from abf_platform import guidance, mcp_server
    from abf_platform.actions import chat_tools
    ins = [guidance.routing_instructions(), chat_tools.CHAT_SYSTEM_PROMPT]
    for m in methods() + ["ANCOM-BC", "MaAsLin2", "DESeq2", "clusterProfiler"]:
        for text in ins:
            assert m not in text, m
    server = mcp_server.build_server(Path("."))
    assert all(m not in (server.instructions or "") for m in methods())
    assert "list_downstream" in chat_tools.CHAT_SYSTEM_PROMPT


def test_ld04_body_is_one_call_into_the_actions_layer():
    # TC-M07
    tree = ast.parse(MCP_SRC.read_text(encoding="utf-8"))
    build = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_server")
    inner = {n.name for n in ast.walk(build) if isinstance(n, ast.FunctionDef)}
    assert "list_downstream" not in inner
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "list_downstream"]
    assert len(fn) == 1
    calls = [n for st in fn[0].body for n in ast.walk(st) if isinstance(n, ast.Call)]
    assert len(calls) == 1 and ast.unparse(calls[0].func) == "downstream_actions.list_downstream"


def test_ld05_not_exported_from_actions_package():
    # TC-M08
    import abf_platform.actions as actions
    import abf_platform.actions.downstream as ds
    assert not hasattr(actions, "list_downstream") and callable(ds.list_downstream)


def test_ld06_description_within_limit_and_every_parameter_described(w):
    # TC-M09
    t = tools(w)["list_downstream"]
    assert len(t.description) <= 600
    for word in ("read-only", "certified", "asks", "no analysis", "grade C"):
        assert word.lower() in t.description.lower(), word
    assert t.input_schema["properties"]["pipeline"].get("description")


def test_ld07_no_files_written(w):
    # TC-M18
    before = sorted(p.name for p in DATA.parent.iterdir())
    h = hashlib.sha256(DATA.read_bytes()).hexdigest()
    w.call("list_downstream", {"pipeline": "rnaseq"})
    assert sorted(p.name for p in DATA.parent.iterdir()) == before and hashlib.sha256(DATA.read_bytes()).hexdigest() == h
