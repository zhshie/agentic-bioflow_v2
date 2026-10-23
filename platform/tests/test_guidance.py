# Nothing existing: tests of the guidance served over the MCP URL (spec 009g) - routing instructions, one prompt per flow skill, skills as resources, the packaged copy; the rules are ours.
"""Guidance over the URL (009g): instructions, prompts and resources made from the one folder skills/.

Test cases are named in the comments (TC-101 ...), see specs/009g-guidance-over-mcp/test-case.md.
"""
import ast
import asyncio
import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT, free_port, mcp_stdio_params, pkg_env, start_cli, stop_proc, wait_port
from test_launch_platform import setup
from test_scope import _repo_names, judge

PKG = PLATFORM_DIR / "abf_platform"
SKILLS = REPO_ROOT / "skills"
FLOWS = ["setup", "launch", "runs", "downstream", "finish"]
ALL_SKILLS = FLOWS + ["operational"]
READ_TOOLS = ["get_compute_env", "get_run", "list_agents", "list_compute_envs", "list_runs", "list_site_files", "read_task_log"]


def guidance():
    from abf_platform import guidance as g
    return g


def _server(tmp_path):
    from abf_platform.mcp_server import build_server
    return build_server(str(tmp_path / "index.db"))


def _split(raw):
    """Independent reading of a SKILL.md: (frontmatter text, body after the closing --- line)."""
    assert raw.startswith("---\n")
    end = raw.index("\n---\n", 3)
    return raw[4:end], raw[end + len("\n---\n"):]


def _skill_raw(name):
    return (SKILLS / name / "SKILL.md").read_bytes().decode("utf-8")


def _table_rows(raw):
    sec = raw.split("## The five commands", 1)[1].split("\n## ", 1)[0]
    rows = [ln for ln in sec.splitlines() if ln.startswith("| `")]
    return [[c.strip() for c in ln.strip("|").split("|")] for ln in rows]


def _copy_skills(tmp_path):
    dst = tmp_path / "skills"
    shutil.copytree(SKILLS, dst)
    return dst


# ---- US1: instructions ---------------------------------------------------------------------------------------------------

def test_tc101_every_row_of_the_routing_table_is_in_the_instructions():
    text = guidance().routing_instructions()
    rows = _table_rows(_skill_raw("operational"))
    assert [r[0] for r in rows] == ["`%s`" % f for f in FLOWS]
    for cmd, when, _ in rows:
        assert cmd in text and when in text


def test_tc102_run_rnaseq_is_routed_to_launch():
    text = guidance().routing_instructions()
    para = text[text.index("does not have to name a command"):].split("\n\n", 1)[0]
    assert "I want to run RNA-seq" in para and "`launch`" in para


def test_tc103_tc104_tc105_the_fixed_sentence():
    text = guidance().routing_instructions()
    assert "read-only" in text
    assert "launch" in text and "cancel" in text and "terminal" in text
    assert "prompt" in text


def test_tc106_instructions_are_at_most_2kb():
    assert len(guidance().routing_instructions().encode("utf-8")) <= 2048


def test_tc107_instructions_follow_the_file(tmp_path):
    d = _copy_skills(tmp_path)
    p = d / "operational" / "SKILL.md"
    raw = p.read_bytes().decode("utf-8")
    old = "Checking on, debugging, or delivering a run"
    assert old in raw
    raw = raw.replace(old, "Looking at a run again tomorrow")
    raw = raw.replace("\n\n**The user does not have to name a command.**",
                      "\n| `extra` | A sixth thing nobody planned | nowhere |\n\n**The user does not have to name a command.**")
    p.write_bytes(raw.encode("utf-8"))
    text = guidance().routing_instructions(d)
    assert "Looking at a run again tomorrow" in text and "`extra`" in text and old not in text


def test_tc108_a_missing_heading_raises(tmp_path):
    d = _copy_skills(tmp_path)
    p = d / "operational" / "SKILL.md"
    p.write_bytes(p.read_bytes().decode("utf-8").replace("## The five commands", "## Something else").encode("utf-8"))
    with pytest.raises(guidance().GuidanceError):
        guidance().routing_instructions(d)


def test_tc109_a_missing_table_raises(tmp_path):
    d = _copy_skills(tmp_path)
    p = d / "operational" / "SKILL.md"
    lines = [ln for ln in p.read_bytes().decode("utf-8").split("\n") if not ln.startswith("|")]
    p.write_bytes("\n".join(lines).encode("utf-8"))
    with pytest.raises(guidance().GuidanceError):
        guidance().routing_instructions(d)


def test_tc110_the_server_instructions_are_the_generated_text(tmp_path):
    assert _server(tmp_path).instructions == guidance().routing_instructions()


# ---- direct server helpers ------------------------------------------------------------------------------------------------

def _prompts(server):
    return {p.name: p for p in asyncio.run(server.list_prompts())}


def _prompt_text(server, name):
    res = asyncio.run(server.get_prompt(name))
    assert len(res.messages) == 1 and res.messages[0].role == "user"
    return res.messages[0].content.text


def _resources(server):
    return {str(r.uri): r for r in asyncio.run(server.list_resources())}


def _read(server, uri):
    out = list(asyncio.run(server.read_resource(uri)))
    assert len(out) == 1
    c = out[0].content
    return c if isinstance(c, str) else c.decode("utf-8")


# ---- US2: prompts ---------------------------------------------------------------------------------------------------------

def test_tc201_tc202_exactly_the_five_flow_prompts(tmp_path):
    names = sorted(_prompts(_server(tmp_path)))
    assert names == sorted(FLOWS)
    assert not {"operational", "agentic-bioflow-operational"} & set(names)


def test_tc203_prompts_take_no_arguments(tmp_path):
    for p in _prompts(_server(tmp_path)).values():
        assert not p.arguments


def test_tc204_tc205_a_prompt_is_the_skill_body_byte_for_byte(tmp_path):
    server = _server(tmp_path)
    for name in FLOWS:
        _, body = _split(_skill_raw(name))
        text = _prompt_text(server, name)
        assert text.encode("utf-8") == body.encode("utf-8")
        assert not text.startswith("---") and "\nname: " + name + "\n" not in text[:200]


def test_tc209_other_prompts_are_refused(tmp_path):
    server = _server(tmp_path)
    for name in ("operational", "nope"):
        with pytest.raises(Exception):
            asyncio.run(server.get_prompt(name))


# ---- US3: resources -------------------------------------------------------------------------------------------------------

def test_tc301_tc302_tc303_six_fixed_resources(tmp_path):
    server = _server(tmp_path)
    res = _resources(server)
    assert sorted(res) == sorted("skill://%s/SKILL.md" % n for n in ALL_SKILLS)
    for n in ALL_SKILLS:
        uri = "skill://%s/SKILL.md" % n
        assert res[uri].mime_type == "text/markdown"
        assert _read(server, uri).encode("utf-8") == _skill_raw(n).encode("utf-8")


def test_tc304_tc706_no_templates(tmp_path):
    assert asyncio.run(_server(tmp_path).list_resource_templates()) == []


@pytest.mark.parametrize("uri", [
    "skill://nope/SKILL.md", "skill://abf/SKILL.md",
    "skill://launch/../operational/SKILL.md", "skill://../pyproject.toml", "skill://launch/../../pyproject.toml",
    "skill://launch/OTHER.md", "skill://launch/", "skill://launch"])
def test_tc307_tc308_tc309_other_uris_are_refused(tmp_path, uri):
    server = _server(tmp_path)
    with pytest.raises(Exception):
        asyncio.run(server.read_resource(uri))


# ---- stdio and streamable HTTP clients ------------------------------------------------------------------------------------

async def _client_view(client):
    prompts = {p.name: p for p in (await client.list_prompts()).prompts}
    texts = {}
    for n in prompts:
        r = await client.get_prompt(n)
        assert len(r.messages) == 1
        texts[n] = r.messages[0].content.text
    res = {str(r.uri): r for r in (await client.list_resources()).resources}
    contents = {}
    for u in res:
        r = await client.read_resource(u)
        contents[u] = r.contents[0].text
    return {"instructions": client.instructions, "prompts": texts, "resources": contents,
            "prompt_args": {n: p.arguments for n, p in prompts.items()}}


def _stdio_view(tmp_path):
    from mcp import Client

    async def go():
        async with Client(mcp_stdio_params(pkg_env(ABF_PLATFORM_DB=tmp_path / "index.db"))) as client:
            return await _client_view(client)
    return asyncio.run(go())


def _http_view(tmp_path):
    # 009d made every HTTP call need a personal access token, so the HTTP client of TC-112 carries one;
    # it asks for no extra credential for the guidance: the view must still equal the stdio one.
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    from test_pat import _env, _pat
    env = _env(tmp_path)
    (tmp_path / "data").mkdir(exist_ok=True)
    token, _uid = _pat(tmp_path)
    port = free_port()
    proc = start_cli(["mcp", "--http", "--port", str(port)], env, tmp_path / "mcp.log")
    try:
        wait_port(port, proc=proc)

        async def go():
            http_client = httpx2.AsyncClient(headers={"Authorization": "Bearer " + token})
            async with Client(streamable_http_client("http://127.0.0.1:%d/mcp" % port, http_client=http_client)) as client:
                return await _client_view(client)
        return asyncio.run(go())
    finally:
        stop_proc(proc)


def _expected_view():
    return {"instructions": guidance().routing_instructions(),
            "prompts": {n: _split(_skill_raw(n))[1] for n in FLOWS},
            "resources": {"skill://%s/SKILL.md" % n: _skill_raw(n) for n in ALL_SKILLS}}


def test_tc111_tc206_tc305_stdio_client_sees_the_guidance(tmp_path):
    view = _stdio_view(tmp_path)
    exp = _expected_view()
    assert view["instructions"] == exp["instructions"]
    assert all(f in view["instructions"] for f in FLOWS)
    assert view["prompts"] == exp["prompts"] and view["resources"] == exp["resources"]
    assert not any(view["prompt_args"].values())


def test_tc112_tc207_tc306_http_client_with_a_pat_sees_the_same(tmp_path):
    http = _http_view(tmp_path)
    exp = _expected_view()
    assert http["instructions"] == exp["instructions"]
    assert http["prompts"] == exp["prompts"] and http["resources"] == exp["resources"]


# ---- US4: one copy -------------------------------------------------------------------------------------------------------

def test_tc401_load_skills_finds_the_six_directories():
    skills = guidance().load_skills()
    assert sorted(skills) == sorted(ALL_SKILLS)
    for n, doc in skills.items():
        fm, body = _split(_skill_raw(n))
        assert re.search(r"^name:\s*%s\s*$" % re.escape(doc.name), fm, re.M)
        assert doc.description and doc.description[:30] in fm
        assert doc.body_text == body
    assert skills["launch"].name == "launch" and skills["operational"].name == "agentic-bioflow-operational"


def test_tc402_skills_dir_falls_back_to_the_repo(tmp_path):
    pkg = tmp_path / "abf_platform"
    pkg.mkdir()
    assert guidance().skills_dir(pkg) == SKILLS


def test_tc403_skills_dir_prefers_the_packaged_copy(tmp_path):
    pkg = tmp_path / "abf_platform"
    (pkg / "skills" / "launch").mkdir(parents=True)
    assert guidance().skills_dir(pkg) == pkg / "skills"


def _copy_for_build(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(SKILLS, root / "skills")
    shutil.copytree(PLATFORM_DIR, root / "platform",
                    ignore=shutil.ignore_patterns("tests", "__pycache__", "build", "*.egg-info", "skills"))
    return root


def test_tc404_the_wheel_copy_equals_the_repo_skills(tmp_path):
    # TC-404; skipped (with the reason printed) only when no build backend can be had offline.
    try:
        import setuptools
        modern = int(setuptools.__version__.split(".")[0]) >= 61
    except ImportError:
        modern = False
    root = _copy_for_build(tmp_path)
    out = tmp_path / "wheels"
    cmd = [sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(out), str(root / "platform")]
    if modern:
        cmd.insert(5, "--no-build-isolation")
    done = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if done.returncode != 0:
        tail = (done.stdout + done.stderr)[-1500:]
        if not modern and re.search(r"No matching distribution|Could not find a version|Connection|Temporary failure|"
                                    r"build backend|setuptools|Name or service", tail, re.I):
            reason = "no build backend available offline (setuptools>=61 missing): " + tail.strip().splitlines()[-1]
            print("TC-404 SKIPPED: " + reason)
            pytest.skip(reason)
        pytest.fail("pip wheel failed:\n" + tail)
    wheel = next(out.glob("*.whl"))
    with zipfile.ZipFile(wheel) as z:
        got = {n[len("abf_platform/skills/"):]: z.read(n) for n in z.namelist()
               if n.startswith("abf_platform/skills/") and not n.endswith("/")}
    want = {str(p.relative_to(SKILLS)).replace("\\", "/"): p.read_bytes() for p in SKILLS.rglob("*") if p.is_file()}
    assert sorted(got) == sorted(want) and len(want) == 6
    assert got == want


def _pyproject():
    return (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")


def test_tc406_package_data_covers_the_skills():
    assert 'package-data = {"abf_platform" = ["skills/*/SKILL.md", "data/*.json"]}' in _pyproject().splitlines()


def test_tc407_packages_is_not_extended():
    text = _pyproject()
    listed = re.findall(r'"([^"]+)"', re.search(r"^packages\s*=\s*\[(.*?)\]", text, re.S | re.M).group(1))
    assert sorted(listed) == sorted(["abf_platform", "abf_platform.actions", "abf_station", "abf_launch"])
    for init in PKG.rglob("__init__.py"):
        assert ".".join(["abf_platform"] + list(init.parent.relative_to(PKG).parts)) in listed


def _git(*args):
    return subprocess.run(["git", "-C", str(REPO_ROOT)] + list(args), capture_output=True, text=True).stdout


def test_tc408_the_copy_is_ignored_and_not_tracked():
    assert "platform/abf_platform/skills/" in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert _git("ls-files", "platform/abf_platform/skills").strip() == ""


NEW_PY = [PKG / "guidance.py", PLATFORM_DIR / "setup.py", Path(__file__)]


def test_tc409_no_second_copy_of_the_text():
    tracked = _git("ls-files", "platform").splitlines()
    assert not [t for t in tracked if t.endswith("SKILL.md")]
    for p in NEW_PY[:2] + [PKG / "mcp_server.py"]:
        src = p.read_text(encoding="utf-8")
        assert "pipelines → datasets → launch" not in src and "outside Seqera" not in src, p.name


def test_tc410_tc801_the_new_files_carry_a_header():
    names = _repo_names()
    assert [judge(p, names) for p in NEW_PY] == ["", "", ""]


def test_tc411_guidance_imports_only_the_standard_library():
    tree = ast.parse((PKG / "guidance.py").read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            mods = [] if n.level else [n.module]
        else:
            continue
        for m in mods:
            assert m.split(".")[0] in sys.stdlib_module_names, m


# ---- US5: the tools stay, nothing is written ------------------------------------------------------------------------------

def test_tc501_six_read_only_tools_remain(tmp_path):
    # 009c: the six are unchanged and read-only; `launch` and `cancel` are added (they write nothing without a person's yes);
    # 009e: and `resume` and `relaunch`, which are asked in the same way
    tools = asyncio.run(_server(tmp_path).list_tools())
    assert sorted(t.name for t in tools) == sorted(READ_TOOLS + ["launch", "cancel", "forget", "resume", "relaunch"])  # keep-submissions (TC-040)
    reads = [t for t in tools if t.name in READ_TOOLS]
    assert all(t.annotations.read_only_hint is True and t.annotations.destructive_hint is not True for t in reads)


def _snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).rglob("*")) if p.is_file()}


def test_tc503_reading_the_guidance_writes_nothing(tmp_path):
    from abf_platform.mcp_server import build_server
    plat, _, _ = setup(tmp_path)
    before = _snapshot(tmp_path)
    server = build_server(str(plat.index))
    _ = server.instructions
    for n in FLOWS:
        _prompt_text(server, n)
    for r in _resources(server):
        _read(server, r)
    assert _snapshot(tmp_path) == before


# ---- not in this PR -------------------------------------------------------------------------------------------------------

def test_tc701_tc703_the_new_files_do_not_launch_read_env_or_confirm():
    for p in NEW_PY[:2]:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute):
                assert n.attr not in ("environ", "getenv", "launch", "cancel"), (p.name, n.attr)
            if isinstance(n, ast.Name):
                assert n.id not in ("TERMINAL", "environ", "getenv"), (p.name, n.id)
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in n.names] + [getattr(n, "module", None) or ""]
                assert not any(re.search(r"confirm|jobs|terminal|abf_launch|actions", x) for x in names), (p.name, names)


def test_tc701_the_http_routes_are_those_of_v3(tmp_path):
    # TC-701 (routes half): the receiver keeps exactly the v3 routes (no launch/cancel/confirm path), and the MCP app is the one /mcp door.
    from abf_platform import receiver
    from test_actions_layer import ROUTES_V3
    app = receiver.create_app(tmp_path / "index.db", tmp_path / "tokens.db")
    got = sorted((getattr(r, "path", "?"), tuple(sorted(getattr(r, "methods", None) or []))) for r in app.routes)
    assert got == ROUTES_V3
    assert not any(re.search(r"launch|cancel|confirm", path) for path, _ in got)
    mcp_paths = sorted(getattr(r, "path", "?") for r in _server(tmp_path).streamable_http_app().routes)
    assert mcp_paths == ["/mcp"]


def test_tc705_dev_variables_change_nothing(tmp_path, monkeypatch):
    before = guidance().routing_instructions()
    for k in ("ABF_DEV", "ABF_PLATFORM_DEV", "ABF_PLATFORM_YES", "ABF_YES"):
        monkeypatch.setenv(k, "1")
    server = _server(tmp_path)
    assert server.instructions == before
    assert sorted(_prompts(server)) == sorted(FLOWS) and len(_resources(server)) == 6


def test_tc707_the_mcp_pin_is_unchanged():
    assert 'dependencies = ["mcp>=2.3,<3"]' in _pyproject()
    assert re.search(r"^mcp==2\.3\.0\s*$", (PLATFORM_DIR / "constraints.txt").read_text(encoding="utf-8"), re.M)
