# Nothing existing: a guard over our own source (every read and queue call of the action layer names its caller, tools and actions pair up); no library knows this project's owner rule.
"""owner-binding: a new action that forgets to pass the caller fails here, the day it is written (#116, issue scope 2).
The scanner reads source with `ast` and only looks at whether an owner argument is given, not at its value: None (the terminal)
is a legal value. Test cases are named in the comments (TC-049 ...)."""
import ast
import asyncio
import inspect
import re
from pathlib import Path

from helpers import PLATFORM_DIR

PKG = Path(PLATFORM_DIR) / "abf_platform"
LAUNCH = Path(PLATFORM_DIR) / "abf_launch"

# module.function -> (keyword names that count, position of the owner argument)
CALLS = {
    ("compute_envs", "get"): ({"owner"}, 2),
    ("compute_envs", "list_all"): ({"owner"}, 1),
    ("agents", "list_agents"): ({"owner"}, 3),
    ("jobs", "latest_pipeline_files"): ({"caller_user_id", "owner", "caller"}, 4),
    ("jobs", "enqueue_listing"): ({"caller_user_id", "owner", "caller"}, 6),
    ("jobs", "enqueue_task_log"): ({"caller_user_id", "owner", "caller"}, 7),
    ("jobs", "enqueue_pipeline_files"): ({"caller_user_id", "owner", "caller"}, None),
    ("jobs", "check_target"): ({"caller_user_id", "owner", "caller"}, 5),
}

# Functions of abf_launch/build.py that read an environment AFTER the owner check of the run they work on (each one's reason):
ALLOWED = {
    "is_gcb": "asks only the type of an environment whose name came from a run or environment already checked",
    "_same_environment": "compares the environment of a run that the caller's own check already let through",
    "prepare_cancel": "its first lines compare the run's user_id with the owner and call target_problem(..., owner)",
    "prepare_clean": "its first lines compare the run's user_id with the owner and call target_problem(..., owner)",
}
ALLOWED_PREFIX = "is_"      # the type checks of build.py (aws-launch adds is_aws)


def scanned_files():
    files = sorted((PKG / "actions").glob("*.py"))
    files += [PKG / "mcp_server.py", PKG / "pipeline_launch.py", LAUNCH / "build.py"]
    files += sorted(PKG.glob("web*.py"))
    return files


def unowned_calls(source):
    """[(enclosing function, 'module.function', line)] of the watched calls that name no owner."""
    found = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack = []

        def visit_FunctionDef(self, node):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node):
            f = node.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and (f.value.id, f.attr) in CALLS:
                names, pos = CALLS[(f.value.id, f.attr)]
                given = any(k.arg in names for k in node.keywords) or any(k.arg is None for k in node.keywords)
                if pos is not None and len(node.args) > pos:
                    given = True
                if not given:
                    where = self.stack[-1] if self.stack else "<module>"
                    if where not in ALLOWED and not where.startswith(ALLOWED_PREFIX):
                        found.append((where, "%s.%s" % (f.value.id, f.attr), node.lineno))
            self.generic_visit(node)

    V().visit(ast.parse(source))
    return found


def test_every_read_and_queue_call_in_the_action_layer_names_its_caller():
    # TC-049, TC-050
    bad = []
    for path in scanned_files():
        for where, call, line in unowned_calls(path.read_text(encoding="utf-8")):
            bad.append("%s:%d %s in %s" % (path.name, line, call, where))
    assert not bad, bad
    names = {p.name for p in scanned_files()}
    assert {"mcp_server.py", "pipeline_launch.py", "build.py", "__init__.py"} <= names
    assert any(n.startswith("web") for n in names)


def test_the_scanner_catches_a_call_without_an_owner():
    # TC-051, TC-052
    assert unowned_calls("def f(p, name):\n    return compute_envs.get(p, name)\n") == [("f", "compute_envs.get", 2)]
    for code in ("compute_envs.get(p, n)", "compute_envs.list_all(p)", "agents.list_agents(p, now)",
                 "jobs.latest_pipeline_files(p, r, v, a)", "jobs.enqueue_listing(p, c, x, clock)", "jobs.enqueue_task_log(p, r, w, f, clock)",
                 "jobs.enqueue_pipeline_files(p, r, v, parts)", "jobs.check_target(p, c, k)"):
        assert len(unowned_calls("def f():\n    %s\n" % code)) == 1, code


def test_the_scanner_lets_the_named_exceptions_through():
    # TC-053, TC-054, TC-055, TC-056
    assert unowned_calls("def f(p, name):\n    return compute_envs.get(p, name, owner=1)\n") == []
    assert unowned_calls("def f(state, ce_name, owner):\n    return compute_envs.get(state, ce_name, owner)\n") == []
    assert unowned_calls("def f():\n    jobs.latest_pipeline_files(platform_path, repo, revision, asked, caller_id)\n") == []
    for fn in ("is_gcb", "_same_environment", "prepare_cancel", "prepare_clean", "is_aws"):
        assert unowned_calls("def %s(state, x):\n    return compute_envs.get(state, x)\n" % fn) == [], fn
    assert unowned_calls("def prepare_something_else(state, x):\n    return compute_envs.get(state, x)\n")


def test_the_allow_list_has_no_dead_names():
    # TC-057
    defined = {n.name for n in ast.walk(ast.parse((LAUNCH / "build.py").read_text(encoding="utf-8")))
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert set(ALLOWED) <= defined, set(ALLOWED) - defined


def test_the_scan_list_leaves_the_terminal_and_the_cost_code_out():
    # TC-061
    scanned = {str(p.relative_to(PLATFORM_DIR)).replace("\\", "/") for p in scanned_files()}
    for left_out in ("abf_platform/cli.py", "abf_launch/cli.py", "abf_platform/cloud_cost.py", "abf_platform/su.py"):
        assert left_out not in scanned
    assert not [s for s in scanned if s.startswith("abf_station/")]


# ---- the MCP tools and the actions pair up ----------------------------------------------------------------------------------

# tool name -> the action that serves it (same name unless listed): the write tools only ask, through request_*
TOOL_ACTION = {"launch": "request_launch", "cancel": "request_cancel", "forget": "request_forget",
               "resume": "request_resume", "relaunch": "request_relaunch"}

# actions with a `caller` that no tool is named after, each with the reason
NO_TOOL = {
    "approve": "the person's yes on the web confirmation page",
    "caller_area": "helper: the caller's upload folder",
    "clean_requests": "web page: clean-work requests",
    "confined_samplesheet": "helper: confine a samplesheet to the caller's folder",
    "estimate_su": "web page and launch screen",
    "find_approved": "web confirmation page",
    "forget_check": "web page: what forgetting would delete",
    "form_is_trusted": "helper of the MCP form",
    "latest_release": "web page",
    "launch": "the confirmed path (confirmed_by), not a tool",
    "cancel": "the confirmed path (confirmed_by), not a tool",
    "forget": "the confirmed path (confirmed_by), not a tool",
    "launch_prefill": "web launch page",
    "list_samplesheets": "web launch page",
    "nfcore_catalogue": "web launch page",
    "pipeline_files": "web launch page",
    "read_confined_samplesheet": "helper of the launch page",
    "request_pipeline_launch": "web launch page",
    "start_upload_batch": "web upload page: the press of Upload is the yes (web-upload-page)",
    "upload_batch_status": "web upload page: the progress of one batch (web-upload-page)",
    "register_site_pipeline": "the confirmed path (confirmed_by), not a tool: the settings page's second step",
    "remove_site_pipeline": "the confirmed path (confirmed_by), not a tool: the settings page's second step",
    "check_site_pipeline_change": "web settings page: step one of the two steps, reads only",
}


def caller_actions():
    from abf_platform import actions
    return {n for n, f in vars(actions).items()
            if inspect.isfunction(f) and not n.startswith("_") and f.__module__.startswith("abf_platform.actions")
            and "caller" in inspect.signature(f).parameters}


def tool_names(tmp_path):
    from abf_platform import mcp_server
    server = mcp_server.build_server(tmp_path / "index.db", tmp_path / "platform.db")
    return {t.name for t in asyncio.run(server.list_tools())}


def parity_problems(tools, actions, extra_tools=(), extra_actions=()):
    tools = set(tools) | set(extra_tools)
    actions = set(actions) | set(extra_actions)
    problems = []
    served = set()
    for t in sorted(tools):
        a = TOOL_ACTION.get(t, t)
        served.add(a)
        if a not in actions:
            problems.append("tool %s has no action %s with a caller" % (t, a))
    for a in sorted(actions - served - set(NO_TOOL)):
        problems.append("action %s has a caller but no tool and is not listed in NO_TOOL" % a)
    for a in sorted(set(NO_TOOL) - actions):
        problems.append("NO_TOOL names %s, which is not an action with a caller" % a)
    return problems


def test_every_mcp_tool_has_an_action_and_every_caller_action_has_a_tool(tmp_path):
    # TC-058, TC-076
    tools = tool_names(tmp_path)
    assert tools == {"cancel", "forget", "get_compute_env", "get_run", "launch", "list_agents", "list_compute_envs", "list_runs",
                     "list_site_files", "list_used_pipelines", "my_usage", "read_task_log", "relaunch", "resume", "run_outputs"}
    assert parity_problems(tools, caller_actions()) == []
    assert all(NO_TOOL[a] for a in NO_TOOL)


def test_a_missing_side_of_the_pairing_fails(tmp_path):
    # TC-059
    tools, actions = tool_names(tmp_path), caller_actions()
    assert parity_problems(tools, actions, extra_tools=["brand_new_tool"])
    assert parity_problems(tools, actions, extra_actions=["brand_new_action"])


def test_the_web_files_are_only_read():
    # TC-062
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    attrs = {c.func.attr for c in calls if isinstance(c.func, ast.Attribute)}
    assert "read_text" in attrs and not attrs & {"write_text", "write_bytes", "write", "unlink", "rename"}
    opens = [c for c in calls if isinstance(c.func, ast.Name) and c.func.id == "open"]
    assert not opens
