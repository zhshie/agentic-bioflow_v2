# Nothing existing: current tests start the server and connect with the SDK client; none checks that the header text of mcp_server.py lists every registered tool, and this one only reads source text, so it needs no mcp install.
"""Header text of mcp_server.py stays in step with the registered tools (mcp-server-doc-tool-list)."""
import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "abf_platform" / "mcp_server.py"
TEXT = SRC.read_text(encoding="utf-8")
TREE = ast.parse(TEXT)
DOC = ast.get_docstring(TREE) or ""

NUMBERS = {"six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15}

EXPECTED = {
    "list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents",
    "list_site_files", "list_used_pipelines", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation", "run_outputs", "read_task_log",
    "launch", "launch_pipeline", "cancel", "forget", "resume", "relaunch",
}


def _tools():
    """(name, annotations-name) for every @server.tool(...) decorator."""
    found = []
    for node in ast.walk(TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr == "tool"):
                    kw = {k.arg: k.value for k in dec.keywords}
                    name = kw["name"].value
                    ann = kw["annotations"].id if isinstance(kw.get("annotations"), ast.Name) else ""
                    found.append((name, ann))
    return found


def test_registered_tools_are_the_known_twenty_one():
    # TC-012
    tools = _tools()
    assert {n for n, _ in tools} == EXPECTED
    assert len(tools) == 21
    assert sum(1 for _, a in tools if a == "_READ_ONLY") == 15


def test_module_doc_names_every_registered_tool():
    # TC-001, TC-002, TC-003, TC-011
    missing = [n for n, _ in _tools() if n not in DOC]
    assert not missing, f"module docstring does not name: {missing}"


def test_module_doc_counts_the_read_only_tools():
    # TC-004, TC-005, TC-011
    n = sum(1 for _, a in _tools() if a == "_READ_ONLY")
    found = re.findall(r"\b(six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen)\b read", DOC)
    assert found, "module docstring states no read-only tool count"
    assert all(NUMBERS[w] == n for w in found), f"{found} vs actual {n}"


def test_first_comment_line_does_not_name_an_old_count():
    # TC-006
    first = TEXT.splitlines()[0]
    assert "six" not in first and "seven" not in first
