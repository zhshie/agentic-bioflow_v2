# Plan 009b: the action layer, read actions and the terminal launch/cancel behind it (behaviour unchanged)

- **Slug**: 009b-action-layer
- **Branch**: `feat/009b-action-layer`, base **`v3`** (never `main`)
- **Created**: 2026-10-16 by the developer-agent
- **Umbrella**: GitHub issue #93 step 4 (spec 009), first slice. Decision record: `docs/adr/0006-four-entries-one-action-layer.md` ("the action layer, `platform/abf_platform/actions/`: one function per action; the MCP tools, the web routes and the chat call these functions and nothing else").
- **Tier**: A (refactor + new tests; no user-visible behaviour change; no gate loosened).

## 給維護者

1. 這一步只是把平台內部「動作」集中成一層：查分析、查運算環境、查 agent、列檔案、送出、取消，各變成一個函式，放進 `platform/abf_platform/actions/`。
2. 你用起來完全一樣：MCP 仍然只有六個唯讀工具；送出與取消仍然只能在終端機按 y。
3. 這層是之後確認頁（009c）、登入（009d）、網頁（011–013）共用的底座：關卡放在這裡，四個入口都會經過。

## Facts (origin/v3, 2026-10-16)

- `platform/abf_platform/` has no `actions/`. `mcp_server.py:15` imports `agents, compute_envs, jobs, status, store` and implements six read-only tools inline (`list_runs` 34, `get_run` 41, `list_compute_envs` 51, `get_compute_env` 56, `list_agents` 66, `list_site_files` 74).
- `confirm.py` (`confirm_launch` 28, `confirm_cancel` 33) is documented (lines 3-7) as callable only from terminal commands; `test_launch_platform.py` scans for other callers.
- `abf_launch/cli.py:21` imports `agents, compute_envs, confirm, jobs, store` from `abf_platform`; launch path `cmd_launch` 165-205 (`jobs.check_run_name` 191, `confirm.confirm_launch` 201, `jobs.wait_for_result` 256); `cmd_cancel` 292.
- Pinned guards that MUST stay green and unedited: `test_launch_platform.py:254` (TC-010, no launch/cancel/confirm route), `:275` and `test_mcp.py` tc024 (exactly six read-only tools, banned input fields), `:696` (TC-061, no resume/retry/yes on the CLI), `tests/no_second_run_state_test.sh:63` (`LAUNCH_ALLOW` = `platform/abf_station/launch.py` only).

## Design decisions (developer-agent)

1. New package `platform/abf_platform/actions/` with `__init__.py` exporting one function per action:
   - read: `list_runs`, `get_run`, `list_compute_envs`, `get_compute_env`, `list_agents`, `list_site_files` (async). Bodies move from `mcp_server.py` unchanged; signatures take the state/index paths explicitly.
   - write: `launch(state_path, ce_name, bundle, *, confirmed_by)` and `cancel(state_path, ce_name, bundle, *, confirmed_by)`. Each validates (`jobs.check_target` / `jobs.check_run_name` as today), then calls `confirm.confirm_launch` / `confirm_cancel`. `confirmed_by` is a required keyword; in 009b the only accepted value is the constant `actions.TERMINAL` (a sentinel object, not a string), and anything else raises `jobs.JobRefused("no human confirmation channel")`. This is the seam 009c fills with elicitation / confirmation page; it adds no new way to confirm.
2. `mcp_server.py` tool bodies become one-line calls into `actions`; tool names, docstrings, annotations, `instructions` text unchanged byte-for-byte.
3. `abf_launch/cli.py` calls `actions.launch` / `actions.cancel` with `confirmed_by=actions.TERMINAL` only after `terminal.ask` returned yes; it no longer imports `confirm` directly. The TTY check and y/n prompt stay in `abf_launch/terminal.py`.
4. `confirm.py` docstring updated: callable only from `actions` (and `actions` only with the terminal sentinel until 009c). The scan in `test_launch_platform.py` that lists allowed callers of `confirm_*` is updated from the CLI to `abf_platform/actions/` — this keeps the same strength (exactly one caller module), not looser.
5. New test `platform/tests/test_actions_layer.py`:
   - (a) parity: every MCP tool name in `build_server(...)` has a same-named function in `actions` (read-only six).
   - (b) import restriction: `mcp_server.py` imports nothing from `abf_platform` except `actions` (AST scan); `confirm` is imported only by `actions` (AST scan over `platform/`).
   - (c) `actions.launch(..., confirmed_by="yes")`, `confirmed_by=True`, `None`, and a missing keyword are all refused and enqueue nothing (assert jobs table unchanged).
   - (d) `actions.launch` with `actions.TERMINAL` and a valid bundle enqueues exactly one job (same as today's confirm path).
   Red first: (a)(b)(c)(d) fail before the package exists.
6. Existing tests keep their assertions; only import paths change where a test called `confirm` directly as a fixture (list each in the ledger).
7. `docs/PLATFORM.md`: one short section "Action layer" (where actions live, that every entry calls them, that the only confirmation channel today is the terminal). `CHANGELOG.md` (v3) one line under Unreleased.

## Changes, in order (red first)

1. Write `platform/tests/test_actions_layer.py`; run → FAIL; record in ledger.
2. Create `actions/`; move read bodies; add `launch`/`cancel` with the sentinel.
3. Rewire `mcp_server.py` and `abf_launch/cli.py`; update `confirm.py` docstring and the caller scan.
4. Docs + CHANGELOG.
5. `cd platform && python -m pytest -q` green; WSL `bash tests/run_all.sh` green; ledger with red/green evidence.

## Not in this PR

- No new MCP tool, no write tool, no HTTP route, no elicitation, no confirmation page (009c). No identity (009d). No resume (009e). No dev mode (009f). No `instructions`/prompts changes (009g).
- No edit to TC-010, tc024, TC-061 or `LAUNCH_ALLOW`; no hooks, no constitution, no `.github/`.

## Constitution Check

- I.2 single submission path: unchanged (station `launch.py` is still the only submitter; the platform still only queues after a terminal yes).
- Safety Net: unchanged; this PR adds a refusal (non-terminal `confirmed_by`), it loosens nothing.

## Contract round 1 (verifier, 2026-10-16): decisions that override anything above

1. **Default paths and clock live in `actions`**: `actions` exports `platform_path_for(index_path, platform_path=None)` (wraps `store.default_platform_path`) and every read action that needs the time calls `status.now()` inside `actions`. `build_server` in `mcp_server.py` calls only `actions.*`, so 5(b) holds as written.
2. **Fact corrected**: today there is NO allow-list scan of `confirm_*` callers; design 4's "update the caller scan" is void. 5(b)'s "`confirm` is imported only by `actions`" is a NEW check. Scope: non-test Python under `platform/abf_platform/`, `platform/abf_station/`, `platform/abf_launch/` (AST). `platform/tests/` is out of scope.
3. **Signatures**: `actions.launch` / `actions.cancel` also take keyword-only `clock=time.time, deadline_seconds=None, offline_after=None`, passed through to `confirm.*` unchanged. Existing tests that call `confirm.confirm_launch/confirm_cancel` directly with a fake clock stay exactly as they are (tests are outside the 5(b) scope). Design 6 therefore means: no existing test file changes except where an import breaks.
4. **`platform/pyproject.toml`**: add `"abf_platform.actions"` to `[tool.setuptools] packages` (TC-049).
5. **Accepted**: TC-046 (`mcp_server.py` must not mention `launch`, `cancel` or `TERMINAL` from actions); TC-050 (`actions/__init__.py` carries the `# Not …:` / `# Nothing existing:` header required by tc070); TC-073 (`mcp_server.py` still never matches `confirm\b`).
6. **Order**: the `confirmed_by` check runs first, before any validation or database access; a refused call opens no connection and enqueues nothing.
