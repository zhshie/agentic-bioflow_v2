# Plan 009g: the guidance travels through the URL (instructions, prompts, skills as resources, packaged copy)

- **Slug**: 009g-guidance-over-mcp
- **Branch**: `feat/009g-guidance-over-mcp`, base **`v3`** (never `main`)
- **Created**: 2026-10-16 by the developer-agent
- **Umbrella**: GitHub issue #93, spec 009. Decision record: `docs/adr/0006-four-entries-one-action-layer.md` (~66-82, "the guidance must also arrive through the URL").
- **Tier**: B (the MCP `instructions` text changes on purpose and clients show the new prompts as commands; no write tools, no auth, the six tools unchanged). Runs in parallel with 009d (separate lane); both touch `mcp_server.py` in different functions, the second to merge brings the first in with `git merge`.

## 給維護者

1. 使用者只要貼上伺服器網址，就會拿到「怎麼用」：連線時自動讀到路由表（想跑 RNA-seq 該走哪個流程），每個流程另有一個 MCP prompt 放完整 SKILL.md。
2. 這一步沒有新的寫入工具、沒有登入；六個唯讀工具一個字都沒變。
3. 技能文字只有一份（repo 的 `skills/`）；打包時複製進 `abf-platform`，測試保證複製品與 repo 相同。

## Facts (origin/v3 after 009b, 2026-10-16)

- `mcp_server.py` builds `MCPServer("abf-platform", instructions="Read-only view of ...")` inline; tools are one-line calls into `actions`; it imports only `from . import actions`.
- `platform/pyproject.toml`: `dependencies = ["mcp>=2.3,<3"]`; `packages = ["abf_platform", "abf_platform.actions", "abf_station", "abf_launch"]`; no package-data. `constraints.txt` pins `mcp==2.3.0`.
- SDK check (planner downloaded `mcp-2.3.0`): it has `mcp/server/mcpserver/prompts/` and `resources/`, no Skills-over-MCP (SEP-2640) API.
- `skills/{setup,launch,runs,downstream,finish,operational}/SKILL.md` exist. `operational` has `## The five commands` with a table at SKILL.md:21; frontmatter `name: agentic-bioflow-operational`.
- Pinned assertions that touch this slice:
  - `test_actions_layer.py` `BASELINE` (exact old `instructions`) and TC-A10 (`server.instructions == base["instructions"]` plus tool names/descriptions/annotations/schemas).
  - `test_actions_layer.py` TC-E07 `test_tce07_no_prompts_on_the_server` (`list_prompts() == []`).
  - `test_actions_layer.py` TC-D01 (every `__init__.py` dotted path under `abf_platform` is in `packages`).
  - `test_mcp.py` tc024 (exactly six read-only tools).
  - `test_scope.py` tc070 (every `.py` has a `# Not …:` / `# Nothing existing:` header in the first 40 lines).
  - `tests/platform_direction_docs_test.sh` (~466): docs say "instructions and one prompt per skill mirroring `skills/`" — must stay true.
  - TC-010, TC-061, and 009b's text scans (`mcp_server.py` never mentions `launch`, `cancel`, `TERMINAL`, `confirm\b`).

## Design decisions (developer-agent)

1. **New module `abf_platform/guidance.py`** (header: `# Not a second copy of the skills: it reads the one folder skills/, copied into the package at build time.`). API: `skills_dir()`, `load_skills() -> {dirname: SkillDoc(name, description, body_text)}`, `routing_instructions()`. `skills_dir()` returns the packaged `abf_platform/skills/` if present, else `<repo>/skills` (editable installs and tests). Stdlib-only frontmatter parsing.
2. **`instructions` = generated routing table** from `skills/operational/SKILL.md`: the `## The five commands` table plus the "user does not have to name a command" paragraph, plus one fixed sentence (the six tools are read-only; launching and cancelling happen only in the terminal; the full flows are the MCP prompts). Capped at about 2 KB; raises `GuidanceError` if the heading or table is missing. `mcp_server.py` calls `instructions=guidance.routing_instructions()`; `mcp_server.py` may import `guidance` in addition to `actions` (009b's import rule extended by exactly this one name).
3. **Skills as MCP resources** (SEP-2640 not in the pinned SDK): one fixed resource per file, `skill://<dir>/SKILL.md`, mime `text/markdown`; no path template, so no path can be passed in. Docs say "skills as resources", never claim SEP-2640 conformance; a later slice swaps the registration when the pin moves to an SDK with a skills API.
4. **One prompt per flow skill** (`setup`, `launch`, `runs`, `downstream`, `finish`; not `operational`): named by directory, no arguments, returns the SKILL.md body (frontmatter stripped, byte-equal) as one user message. Prompts add no tool; tc024 holds.
5. **Packaging**: `package-data = {"abf_platform" = ["skills/*/SKILL.md"]}` and a small `build_py` hook beside `pyproject.toml` copying `<repo>/skills` into the build's `abf_platform/skills`. The copy is never committed (`platform/abf_platform/skills/` in `.gitignore`); `packages` is not extended (data, not a package); both new `.py` files carry a tc070 header.
6. **The packaged copy equals the repo**: a test builds a wheel (`pip wheel --no-deps` into `tmp_path`; skipped with a printed reason only if no build backend is available offline) and compares every `abf_platform/skills/**` file by bytes and file set against `<repo>/skills`. A pure-Python half always runs: `load_skills()` reads the repo folder and finds exactly the six directories.

## Pinned assertions that legitimately change (only these)

- **TC-A10**: tools half unchanged. Only the `instructions` comparison changes: it equals `guidance.routing_instructions()` and independently contains each of the five flow names and the words "read-only" and "terminal".
- **TC-E07**: becomes "exactly the five flow prompts, names equal the flow skill dirs, each text equals its SKILL.md body" (009b's prompt-less server is superseded by this slice).
- **009b's import rule for `mcp_server.py`**: allowed set `{actions}` → `{actions, guidance}`; nothing else.
- Nothing else is edited. tc024, TC-D01, tc070, TC-010, TC-061 and the text scans stand as they are.

## Changes, in order (red first)

1. Write `platform/tests/test_guidance.py`, edit TC-A10, TC-E07 and the import rule as above; run → FAIL; record in ledger. Tests: (a) instructions follow a mutated temp copy of the table; (b) missing table raises `GuidanceError`; (c) exactly five prompts, each equal to its SKILL.md body; (d) exactly six `skill://` resources, each read equals the file, unknown URIs and `..` refused; (e) tools unchanged, six read-only; (f) over stdio and streamable HTTP an SDK client sees the same instructions, prompts and resources; (g) wheel copy equals repo `skills/`; (h) `pyproject` has the package-data and no unlisted `__init__.py`; (i) the generated instructions say launch/cancel happen in the terminal.
2. `guidance.py`; wire `instructions`, prompts and resources in `build_server`.
3. Packaging hook, package-data, `.gitignore`.
4. Docs: `docs/PLATFORM.md` "Guidance over the URL" (resource fallback and why); `docs/TESTING.md` a manual check of how Claude Desktop and Claude Code show the prompts; `CHANGELOG.md` one line in the 3.0.0-dev section.
5. `cd platform && python -m pytest -q` green; WSL `bash tests/run_all.sh` green (incl. `platform_direction_docs_test.sh`); ledger with red/green evidence and the edited-assertion list.

## Not in this PR

- No write tool, no launch/cancel route, no confirmation page (009c), no auth/identity (009d), no resume (009e), no dev mode (009f).
- No real SEP-2640 endpoint, no `mcp` pin change, no harness kit.
- No change to the six tools' names, descriptions, annotations or schemas; no hooks, constitution or `.github/`.

## Constitution Check

- I.1: one source of guidance (`skills/`), no hand-copied second text; `guidance.py` only reads and serves it.
- I.2: untouched; nothing here can submit or cancel.
- Safety Net: no gate loosened; two assertions change, each replaced by an equally specific one.
