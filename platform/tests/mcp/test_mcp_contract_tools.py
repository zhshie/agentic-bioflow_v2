# New for mcp-contract-tests: in-memory contract tests of the tool list (names, input schemas, descriptions) of abf_platform/mcp_server.py.
# The server is the official python-sdk (v2): `from mcp import Client` talks to the server object directly, no process and no port.
# No pytest-asyncio here: every test is a plain function that runs one `asyncio.run(...)` with one Client (repo convention).
"""Contract tests of the MCP tool list: names, input schemas (snapshot), description lint (TC-001..008, TC-019, TC-020)."""
import asyncio
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / "snapshots" / "tools.json"
REGEN_CMD = "ABF_UPDATE_MCP_SNAPSHOT=1 python -m pytest tests/mcp/test_mcp_contract_tools.py::test_tools_schema_matches_snapshot"

# The tools of v3, written out by hand. Add or remove a tool and this list must change in the same commit.
EXPECTED_TOOLS = sorted([
    "list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "list_used_pipelines",
    "my_usage", "run_outputs", "read_run_file", "list_figures", "read_task_log", "find_module", "describe_module", "list_pipelines",
    "get_pipeline", "get_validation",
    "launch", "launch_pipeline", "cancel", "forget", "resume", "relaunch", "delete_figure", "pack_figures", "publish_figure",
])


def fetch_tools(index):
    """The tools the server lists, as plain dicts: name, description, input schema, read-only flag."""
    from mcp import Client
    from abf_platform import mcp_server

    async def go():
        async with Client(mcp_server.build_server(index)) as client:
            return (await client.list_tools()).tools

    out = []
    for t in asyncio.run(go()):
        ann = t.annotations
        out.append({"name": t.name, "description": t.description or "", "inputSchema": t.input_schema,
                    "readOnly": bool(ann and ann.read_only_hint)})
    return sorted(out, key=lambda t: t["name"])


def render_snapshot(tools):
    """Names and input schemas only (no descriptions: the lint owns those), one stable text."""
    body = [{"name": t["name"], "inputSchema": t["inputSchema"]} for t in sorted(tools, key=lambda t: t["name"])]
    return json.dumps(body, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def compare_snapshot(actual, path):
    """None when the file holds `actual` (line endings ignored); else the failure message. Writes only with ABF_UPDATE_MCP_SNAPSHOT=1."""
    actual = actual.replace("\r\n", "\n")
    if os.environ.get("ABF_UPDATE_MCP_SNAPSHOT") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8", newline="\n")
        return None
    if not path.exists():
        return "snapshot file %s does not exist; to create it run: %s" % (path, REGEN_CMD)
    want = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if want == actual:
        return None
    import difflib
    diff = "".join(list(difflib.unified_diff(want.splitlines(True), actual.splitlines(True), "snapshot", "actual", n=2))[:60])
    return "the tool list differs from %s (a changed name or parameter is a breaking change; if it is intended, regenerate with: %s)\n%s" % (path.name, REGEN_CMD, diff)


# ---- TC-001 ----------------------------------------------------------------------------------------------------------------------------
def test_tool_names_match_explicit_list(plat):
    # TC-001 (the plan said 24 tools; v3 lists 21, so the list below is the real one)
    names = sorted(t["name"] for t in fetch_tools(plat.index))
    extra, missing = sorted(set(names) - set(EXPECTED_TOOLS)), sorted(set(EXPECTED_TOOLS) - set(names))
    assert not extra and not missing, "tools added: %s; tools gone: %s (a rename or removal is a breaking change)" % (extra, missing)
    assert len(names) == len(set(names)) == len(EXPECTED_TOOLS)


# ---- TC-002..004 -----------------------------------------------------------------------------------------------------------------------
def test_tools_schema_matches_snapshot(plat):
    # TC-002
    msg = compare_snapshot(render_snapshot(fetch_tools(plat.index)), SNAPSHOT)
    assert msg is None, msg


def test_snapshot_missing_or_different_fails_without_overwrite(plat, tmp_path, monkeypatch):
    # TC-003: a missing file and a different file both fail, name the regenerate command, and are left as they were
    monkeypatch.delenv("ABF_UPDATE_MCP_SNAPSHOT", raising=False)
    text = render_snapshot(fetch_tools(plat.index))
    gone = tmp_path / "none" / "tools.json"
    msg = compare_snapshot(text, gone)
    assert msg and "ABF_UPDATE_MCP_SNAPSHOT=1" in msg
    assert not gone.exists() and not gone.parent.exists()
    other = tmp_path / "other.json"
    other.write_text(text.replace('"name"', '"nam"', 1), encoding="utf-8", newline="\n")
    before = other.read_bytes()
    msg = compare_snapshot(text, other)
    assert msg and "ABF_UPDATE_MCP_SNAPSHOT=1" in msg
    assert other.read_bytes() == before
    monkeypatch.setenv("ABF_UPDATE_MCP_SNAPSHOT", "0")          # only the value 1 writes
    assert compare_snapshot(text, other) is not None and other.read_bytes() == before
    monkeypatch.setenv("ABF_UPDATE_MCP_SNAPSHOT", "1")
    assert compare_snapshot(text, other) is None
    assert other.read_bytes() == text.encode("utf-8")


def test_snapshot_is_crlf_insensitive(plat, tmp_path, monkeypatch):
    # TC-004: a Windows checkout may turn the snapshot into CRLF; the comparison must not mind, but a real difference still fails
    monkeypatch.delenv("ABF_UPDATE_MCP_SNAPSHOT", raising=False)
    text = render_snapshot(fetch_tools(plat.index))
    crlf = tmp_path / "tools.json"
    crlf.write_bytes(SNAPSHOT.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert b"\r\n" in crlf.read_bytes()
    assert compare_snapshot(text, crlf) is None
    assert compare_snapshot(text.replace('"name"', '"nam"', 1), crlf) is not None


def test_snapshot_has_only_name_and_input_schema():
    # TC-020: no description in the snapshot
    data = json.loads(SNAPSHOT.read_bytes().decode("utf-8"))
    assert [t["name"] for t in data] == EXPECTED_TOOLS
    assert all(sorted(t) == ["inputSchema", "name"] for t in data)


# ---- TC-005..008: description lint -----------------------------------------------------------------------------------------------------
LIMIT = 600

# Technical debt, listed for the maintainer: these descriptions are longer than LIMIT today. A tool listed here may not grow past the
# number written next to it; shorten the description and delete the line. (Measured on v3.)
OVER_LIMIT = {
    "get_run": 804,      # ruling R2: +121 for the sentence that a lost run triggers one read-only site query
    "run_outputs": 700,
}

ASPECTS = {
    "what": lambda d, props: len(d.strip().split()) >= 3,
    "when": lambda d, props: any(w in d.lower() for w in ("when", "if ", "use ", "ask to", "once", "call ", "for ")),
    "when_not": lambda d, props: any(w in d for w in ("does NOT", "Only for", "never", "cannot", "not")),
    "params": lambda d, props: not props or any(p in d for p in props) or "param" in d.lower() or "argument" in d.lower(),
    "return": lambda d, props: any(w in d for w in ("answer", "returns", "comes back", "with its", "each with")),
    "next_step": lambda d, props: bool(re.search(r"call .* again|ask again|\bthen\b|\bafter\b", d)),
}

# The gaps of the aspect check, as (tool, aspect). They are gaps in the descriptions, listed for the maintainer, not leniency in the test:
# the keyword check is crude, but a new tool, or a changed description, must pass it or earn a line here on purpose. The set may only shrink.
ASPECT_GAPS = {
    ('describe_module', 'next_step'),
    ('describe_module', 'when_not'),
    ('find_module', 'next_step'),
    ('forget', 'next_step'),
    ('forget', 'params'),
    ('get_compute_env', 'next_step'),
    ('get_compute_env', 'when'),
    ('get_compute_env', 'when_not'),
    ('get_pipeline', 'next_step'),
    ('get_run', 'next_step'),
    ('get_run', 'params'),
    ('get_run', 'return'),
    ('get_validation', 'next_step'),
    ('get_validation', 'return'),
    ('list_agents', 'next_step'),
    ('list_agents', 'return'),
    ('list_compute_envs', 'next_step'),
    ('list_compute_envs', 'return'),
    ('list_compute_envs', 'when'),
    ('list_pipelines', 'next_step'),
    ('list_pipelines', 'return'),
    ('list_pipelines', 'when'),
    ('list_runs', 'next_step'),
    ('list_runs', 'when'),
    ('list_runs', 'when_not'),
    ('list_site_files', 'next_step'),
    ('list_site_files', 'params'),
    ('list_site_files', 'return'),
    ('list_site_files', 'when'),
    ('list_site_files', 'when_not'),
    ('list_used_pipelines', 'next_step'),
    ('list_used_pipelines', 'return'),
    ('list_used_pipelines', 'when_not'),
    ('my_usage', 'next_step'),
    ('my_usage', 'return'),
    ('read_task_log', 'next_step'),
    ('read_task_log', 'return'),
    ('read_task_log', 'when_not'),
}

# Parameters whose name the description never mentions and that carry no schema description. Same rule: may only shrink.
UNDESCRIBED_PARAMS = {
    ('find_module', 'q'),
    ('forget', 'run_name'),
    ('get_pipeline', 'pipeline_id'),
    ('get_run', 'run_id'),
    ('get_validation', 'pipeline_id'),
    ('launch', 'ce_name'),
    ('launch', 'path_columns'),
    ('launch', 'revision'),
    ('launch', 'run_name'),
    ('list_site_files', 'compute_env'),
    ('list_site_files', 'path'),
    ('read_task_log', 'run_name'),
    ('run_outputs', 'run_id'),
}


def test_descriptions_within_limit(plat):
    # TC-005
    for t in fetch_tools(plat.index):
        n = len(t["description"])
        assert n > 0, "%s has no description" % t["name"]
        if t["name"] in OVER_LIMIT:
            assert n <= OVER_LIMIT[t["name"]], "%s grew to %d chars (frozen at %d); shorten it" % (t["name"], n, OVER_LIMIT[t["name"]])
        else:
            assert n <= LIMIT, "%s description is %d chars, over %d" % (t["name"], n, LIMIT)


def test_over_limit_list_only_shrinks(plat):
    # TC-005: a listed tool that is short enough now must be deleted from OVER_LIMIT; a listed name must exist
    by_name = {t["name"]: len(t["description"]) for t in fetch_tools(plat.index)}
    for name, frozen in OVER_LIMIT.items():
        assert name in by_name, "OVER_LIMIT names a tool that is gone: %s" % name
        assert by_name[name] > LIMIT, "%s is now %d chars: delete it from OVER_LIMIT" % (name, by_name[name])
        assert by_name[name] <= frozen, "%s is %d chars, above its frozen %d" % (name, by_name[name], frozen)


def test_descriptions_cover_the_six_aspects(plat):
    # TC-006
    bad, stale, seen = [], [], set()
    for t in fetch_tools(plat.index):
        props = list(t["inputSchema"].get("properties", {}))
        for aspect, ok in ASPECTS.items():
            passed = ok(t["description"], props)
            seen.add((t["name"], aspect))
            if not passed and (t["name"], aspect) not in ASPECT_GAPS:
                bad.append((t["name"], aspect))
            if passed and (t["name"], aspect) in ASPECT_GAPS:
                stale.append((t["name"], aspect))
    assert not bad, "descriptions miss an aspect (what/when/when_not/params/return/next_step): %s" % sorted(bad)
    assert not stale, "these gaps are closed now; delete them from ASPECT_GAPS: %s" % sorted(stale)
    assert ASPECT_GAPS <= seen, "ASPECT_GAPS names something that does not exist: %s" % sorted(ASPECT_GAPS - seen)


def test_every_param_is_described(plat):
    # TC-007
    bad, stale, seen = [], [], set()
    for t in fetch_tools(plat.index):
        for p, spec in t["inputSchema"].get("properties", {}).items():
            seen.add((t["name"], p))
            has = bool(spec.get("description")) or re.search(r"\b%s\b" % re.escape(p), t["description"]) is not None
            if not has and (t["name"], p) not in UNDESCRIBED_PARAMS:
                bad.append((t["name"], p))
            if has and (t["name"], p) in UNDESCRIBED_PARAMS:
                stale.append((t["name"], p))
    assert not bad, "parameters with no description (schema or tool text): %s" % sorted(bad)
    assert not stale, "these parameters are described now; delete them from UNDESCRIBED_PARAMS: %s" % sorted(stale)
    assert UNDESCRIBED_PARAMS <= seen


SECRET_RE = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}|(?i:token|secret|password|api[_-]?key)\s*[:=]\s*\S{8,}|\b[A-Za-z0-9_-]{40,}\b")


def odd_content(text):
    """What must not be in a description: control characters other than newline, or something shaped like a secret."""
    found = []
    if any(ord(c) < 32 and c != "\n" for c in text) or "\x7f" in text:
        found.append("control character")
    if SECRET_RE.search(text):
        found.append("secret-looking text")
    return found


def test_descriptions_have_no_control_chars_or_secrets(plat):
    # TC-008
    assert odd_content("fine text\n\nsecond paragraph") == []
    assert "secret-looking text" in odd_content("call with Bearer abcdefghijklmnopqrstuvwxyz0123456789")      # the check can see one
    assert "control character" in odd_content("bad\x07bell")
    for t in fetch_tools(plat.index):
        assert odd_content(t["description"]) == [], "%s: %s" % (t["name"], odd_content(t["description"]))


# ---- TC-019: what this folder may and may not be ---------------------------------------------------------------------------------------------
def test_this_folder_has_no_package_file_and_no_async_plugin():
    # TC-019: an __init__.py here would shadow the real `mcp` package; no pytest-asyncio plugin, no fast-server library, one Client per test
    assert not (HERE / "__init__.py").exists()
    words = ["import " + "pytest_asyncio", "asyncio" + "_mode", "pytest.mark." + "asyncio", "create_connected_server" + "_and_client_session",
             "Fast" + "MCP"]
    for f in HERE.glob("test_mcp_contract_*.py"):
        text = f.read_text(encoding="utf-8")
        for w in words:
            assert w not in text, "%s uses %s" % (f.name, w)
