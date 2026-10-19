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
# 012b: launch and cancel are the tools whose web routes are POST /launch and POST /act/cancel; the routes call request_launch and request_cancel (INTERNAL below), never launch or cancel.
WEB_ROUTES = {"list_runs": "GET /", "get_run": "GET /", "list_compute_envs": "GET /launch",
              "launch": "POST /launch, through request_launch", "cancel": "POST /act/cancel, through request_cancel"}
# 012b: the tools resume and relaunch have no action of that name (they are request_resume / request_relaunch); their web routes are POST /act/resume and POST /act/relaunch.
WEB_VIA_REQUEST = {"launch": "request_launch", "cancel": "request_cancel", "resume": "request_resume", "relaunch": "request_relaunch"}
# The PAGE confirmation channel is web-only by design: the MCP side uses the form channel and request_launch/request_cancel.
WEB_ONLY = {
    "describe_request": "the confirmation page shows one pending request to the person it was made for",
    "approve": "the button of the confirmation page: the PAGE channel's yes",
    "platform_path_for": "the page finds platform.db from the index path, the way every entry does",
    "list_samplesheets": "the launch form's choice of samplesheet: the files in the caller's own upload folder",
    "launch_prefill": "the quick launch of the launch form: what the person's own earlier run was sent with, when it is still kept",
}
# Actions with an MCP tool of the same name and no web route yet. The list only shrinks: adding a name means changing this test, the ledger and the plan (R2).
OWED = {"get_compute_env": "012a", "list_agents": "012a", "list_site_files": "012d",
        "forget": "terminal only (v3 keep-submissions), with a request form on /c/"}
OWED_BEFORE_012B = {"list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "launch", "cancel", "forget"}
# Helpers, classes and constants that no web route or tool exposes by name. 009i: ConnectorCaller, form_is_trusted (MCP side only).
# v3 (keep-submissions, resume/relaunch): request_forget, request_resume, request_relaunch are what the tools forget, resume, relaunch call; forget_check and keep_screen are helpers; the FORGET_* and RUN_NOT_FOUND words are constants.
INTERNAL = {"request_launch", "request_cancel", "request_forget", "request_resume", "request_relaunch", "find_approved", "void_request",
            "person_at", "caller_area", "confined_samplesheet", "read_confined_samplesheet", "forget_check", "keep_screen",
            "Caller", "ConnectorCaller", "form_is_trusted", "NotApproved", "PAGE", "ELICITED", "TERMINAL", "DEFAULT_WEB_BASE",
            "FORGETTABLE", "FORGET_ALREADY", "FORGET_NO_FORM", "FORGET_STARTING", "FORGET_WAIT_SECONDS", "RUN_NOT_FOUND"}
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


def mcp_called_actions():
    """The names the MCP server's tool handlers take from `actions` (AST of mcp_server.py)."""
    return called_actions((PLATFORM_DIR / "abf_platform" / "mcp_server.py").read_text(encoding="utf-8"))


def test_tcs06_owed_follows_the_rule():
    # TC-S06 (replaces TC-H16d): R2, every public action a tool calls and no web route calls is in OWED or INTERNAL
    assert {"get_compute_env", "list_agents", "list_site_files"} <= set(OWED)
    for name in mcp_called_actions():          # platform_path_for is the helper every entry uses to find platform.db
        assert name in set(WEB_ROUTES) | set(WEB_ONLY) | set(OWED) | INTERNAL, name
    assert not (set(OWED) & called_actions((WEB).read_text(encoding="utf-8")))
    assert {"forget_check", "keep_screen"} <= INTERNAL


def test_tcs07_owed_is_written_out():
    # TC-S07: the literal list, also in the ledger; it may only shrink
    assert set(OWED) == {"get_compute_env", "list_agents", "list_site_files", "forget"}
    assert set(OWED) < OWED_BEFORE_012B          # 012b: it only shrank (TC-038)
    ledger = (PLATFORM_DIR.parent / "specs" / "011a-web-shell" / "ledger.md").read_text(encoding="utf-8")
    for name in OWED:
        assert name in ledger


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
    assert owed_called("from . import actions\nactions.forget(1)\n") == {"forget"}      # 012b: launch left OWED, forget did not
    assert owed_called("from .actions import list_agents\n") == {"list_agents"}


def test_tc037_web_routes_call_the_request_actions():
    # TC-037 (012b): the four write routes are in the web table, each through its request_* action, and none of them is owed any more
    src = WEB.read_text(encoding="utf-8")
    assert {"launch", "cancel", "list_compute_envs"} <= set(WEB_ROUTES) and not ({"launch", "cancel", "list_compute_envs"} & set(OWED))
    assert set(WEB_VIA_REQUEST.values()) <= called_actions(src)
    assert not ({"launch", "cancel"} & called_actions(src))          # TC-060: the web never confirms by itself


def test_tc039_the_guards_are_not_loosened():
    # TC-039: a new public name and an owed name called by the web are still caught
    assert union_problems(public_names() | {"get_board"}, tables()) != []
    assert owed_called("from . import actions\nactions.forget(1)\n") == {"forget"}
    assert owed_called("from . import actions\nactions.launch(1)\n") == set()      # launch left OWED in 012b; test_web_actions bans the call
