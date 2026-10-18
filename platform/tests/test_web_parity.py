# Nothing existing: the parity check of docs/ROADMAP.md "owed parity" (every action has an MCP tool and a web route, and the owed list only shrinks); the tables are ours.
"""011a, user story 4: the web pages and the MCP tools match one to one. Test cases are named in the comments (TC-H16a ...)."""
import ast
import inspect

import pytest

from helpers import PLATFORM_DIR
from human_harness import World

WEB = PLATFORM_DIR / "abf_platform" / "web.py"
BOARD = PLATFORM_DIR / "abf_platform" / "web_board.py"

# The read actions a web route calls; each has a same-named MCP tool.
WEB_ROUTES = {"list_runs": "GET /", "get_run": "GET /"}
# The PAGE confirmation channel is web-only by design: the MCP side uses the form channel and request_launch/request_cancel.
WEB_ONLY = {
    "describe_request": "the confirmation page shows one pending request to the person it was made for",
    "approve": "the button of the confirmation page: the PAGE channel's yes",
    "platform_path_for": "the page finds platform.db from the index path, the way every entry does",
}
# Actions with an MCP tool and no web route yet. The list only shrinks: adding a name means changing this test and the plan.
OWED = {"list_compute_envs": "012a", "get_compute_env": "012a", "list_agents": "012a", "list_site_files": "012d",
        "launch": "terminal only, with request forms on /c/", "cancel": "terminal only, with request forms on /c/"}
# 009i added ConnectorCaller (the caller an OAuth token stands for) and form_is_trusted (does the MCP client show a 送出 form): MCP-side only, the web never calls them; the OAuth web routes are not actions, so they are not in WEB_ONLY.
INTERNAL = {"request_launch", "request_cancel", "find_approved", "void_request", "person_at", "caller_area", "confined_samplesheet",
            "read_confined_samplesheet", "Caller", "ConnectorCaller", "form_is_trusted", "NotApproved", "PAGE", "ELICITED", "TERMINAL", "DEFAULT_WEB_BASE"}
FORBIDDEN_IMPORTS = {"confirm", "jobs", "compute_envs", "agents", "status"}


def public_names():
    from abf_platform import actions
    return {n for n, v in vars(actions).items() if not n.startswith("_") and not inspect.ismodule(v)}


def tables():
    return [set(WEB_ROUTES), set(WEB_ONLY), set(OWED), INTERNAL]


def union_problems(public, tabs):
    """What is wrong with the four tables against the public names of actions (empty: nothing)."""
    problems = []
    union = set().union(*tabs)
    if union != public:
        problems.append("not in a table: %s; in a table but not public: %s" % (sorted(public - union), sorted(union - public)))
    for i, a in enumerate(tabs):
        for b in tabs[i + 1:]:
            if a & b:
                problems.append("in two tables: %s" % sorted(a & b))
    return problems


def called_actions(source):
    """The names a module takes from `actions`: actions.NAME anywhere, and names imported from it."""
    found = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "actions":
            found.add(node.attr)
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[-1] == "actions":
            found.update(a.name for a in node.names)
    return found


def owed_called(source):
    return called_actions(source) & set(OWED)


def imported(source):
    out = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            out.update(a.name for a in node.names)
            if node.module:
                out.update(node.module.split("."))
        elif isinstance(node, ast.Import):
            for a in node.names:
                out.update(a.name.split("."))
    return out


def test_tch16a_h16b_union_is_the_public_names():
    # TC-H16a, TC-H16b
    assert union_problems(public_names(), tables()) == []


def test_tch16c_web_routes_have_a_same_named_tool(tmp_path, monkeypatch):
    # TC-H16c
    tools, _ = World(tmp_path, monkeypatch).mcp([])
    assert set(WEB_ROUTES) <= {t.name for t in tools}


def test_tch16d_owed_is_exactly_six():
    # TC-H16d
    assert set(OWED) == {"list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "launch", "cancel"}


def test_tch16e_no_owed_name_is_called_by_the_web():
    # TC-H16e
    for p in (WEB, BOARD):
        assert owed_called(p.read_text(encoding="utf-8")) == set(), p.name


def test_tch16f_web_uses_only_its_tables_and_imports_no_internals():
    # TC-H16f1, TC-H16f2
    allowed = set(WEB_ROUTES) | set(WEB_ONLY) | INTERNAL
    for p in (WEB, BOARD):
        src = p.read_text(encoding="utf-8")
        assert called_actions(src) <= allowed, (p.name, called_actions(src) - allowed)
        assert not (imported(src) & FORBIDDEN_IMPORTS), (p.name, imported(src) & FORBIDDEN_IMPORTS)


def test_tch16g_a_new_public_function_is_caught():
    # TC-H16g
    assert union_problems(public_names() | {"get_board"}, tables()) != []
    assert union_problems(public_names() - {"cancel"}, tables()) != []


def test_tch16h_an_owed_name_called_by_the_web_is_caught():
    # TC-H16h
    assert owed_called("from . import actions\nactions.launch(1)\n") == {"launch"}
    assert owed_called("from .actions import list_agents\n") == {"list_agents"}
