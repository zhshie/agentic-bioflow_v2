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
    "launch", "cancel", "forget", "resume", "relaunch",
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


def test_registered_tools_are_the_known_twenty():
    # TC-012
    tools = _tools()
    assert {n for n, _ in tools} == EXPECTED
    assert len(tools) == 20
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


def _first_line_problems(first: str, n: int) -> list[str]:
    """Problems with the count words on the first line; empty means it matches n."""
    if n not in NUMBERS.values():
        return [f"read-only tool count {n} is outside NUMBERS: please extend NUMBERS"]
    words = "|".join(NUMBERS)
    problems = []
    stated = re.findall(rf"\b({words})\b read-only", first)
    if not stated:
        problems.append("first line does not state the read-only tool count (a number word right before 'read-only')")
    for w in stated:
        if NUMBERS[w] != n:
            problems.append(f"first line says {w} read-only tools but there are {n}")
    for w in re.findall(rf"\b({words})\b", first):
        if NUMBERS[w] != n:
            problems.append(f"first line contains the number word {w}, which is not {n}")
    return problems


def _read_only_count() -> int:
    return sum(1 for _, a in _tools() if a == "_READ_ONLY")


def test_first_comment_line_does_not_name_an_old_count():
    # TC-009, TC-010
    n = _read_only_count()
    problems = _first_line_problems(TEXT.splitlines()[0], n)
    assert not problems, f"first line vs actual {n}: {problems}"


def test_first_line_guard_rejects_stale_count_ten():
    # TC-001
    assert _first_line_problems("# ... offers ten read-only tools ...", 15)


def test_first_line_guard_rejects_old_six_seven():
    # TC-002
    assert _first_line_problems("# ... offers six read-only tools ...", 10)
    assert _first_line_problems("# ... offers seven read-only tools ...", 10)


def test_first_line_guard_rejects_missing_count():
    # TC-003
    problems = _first_line_problems("# offers read-only tools", 15)
    assert problems and any("read-only" in p for p in problems)


def test_first_line_guard_accepts_matching_count():
    # TC-004
    assert _first_line_problems("# ... offers fifteen read-only tools", 15) == []


def test_first_line_guard_rejects_count_not_next_to_read_only():
    # TC-005
    assert _first_line_problems("# offers fifteen tools", 15)


def test_first_line_guard_rejects_extra_wrong_number_word():
    # TC-006
    assert _first_line_problems("# offers fifteen read-only tools ... ten ...", 15)


def test_first_line_guard_accepts_six_when_n_is_six():
    # TC-007
    assert _first_line_problems("# ... offers six read-only tools", 6) == []


def test_first_line_guard_demands_wider_numbers_when_n_out_of_range():
    # TC-008
    problems = _first_line_problems("# offers fifteen read-only tools", 16)
    assert problems and any("NUMBERS" in p for p in problems)
