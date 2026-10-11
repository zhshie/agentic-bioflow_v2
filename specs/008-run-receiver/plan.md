# Plan: 008-run-receiver

## Revision 3 (2026-10-11, after implementation; accepted by the developer-agent)

- **Contract clarification for TC-030 and TC-031.** The start and end times of a rebuilt run may differ from the live values by at most 1 second, in whole seconds. Every other compared field must still be exactly equal.
  - The reason is that Nextflow takes separate clock readings for its live events and for its own files, and `.nextflow/history` has only second precision. `research.md` records the measured samples.
  - This loosens the literal "完全相同" of the contract on those two timestamps only. `test-case.md` itself is unchanged.
- **Known limit, not in the contract.** A rebuilt run has no token owner, so its later messages are refused. `docs/PLATFORM.md` §5 tells users not to rebuild while a run is still going.
- **Follow-up, not in this feature.**
  - When `ABF_PLATFORM_CLOCK_OFFSET` is set, say so visibly.
  - Under no CI, the whole platform suite skips when the venv cannot be built; it prints `PLATFORM TESTS SKIPPED`.

## Revision 2 (2026-10-11, after verifier CONTRACT review): supersedes the sections below where they conflict

- **M1, tokens survive a rebuild.** Tokens live in their own SQLite file, `tokens.db`, next to the index, with its own override `ABF_PLATFORM_TOKENS`. `rebuild` only ever drops and recreates the index file and never opens `tokens.db` (TC-032).
- **M2, run IDs are deterministic.** `workflowId` is the first 16 hex characters of sha256(sessionId + "/" + runName). `create` returns it, and `rebuild` derives the same value from `.nextflow/history` / `.nextflow.log`. IDs are therefore equal before and after a rebuild (TC-030).
- **M3, no silent skip.**
  - `tests/platform_test.sh` checks Java ≥17 and Python ≥3.10 itself. It also checks that the pinned Nextflow and nf-tower downloads succeeded with matching sha256.
  - Under `CI=true`, any of those failing is a test failure (exit ≠ 0).
  - Without `CI`, it prints `E2E SKIPPED: <reason>` and a skipped count in the summary.
  - pytest runs with `-rs` so skips are listed (TC-054, TC-055).
- **M4, Nextflow and its nf-tower plugin are pinned with sha256.**
  - Both are downloaded once into `${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform/` and the run uses `NXF_HOME` pointing there.
  - Decision (developer-agent): ADR 0004's red line covers Seqera Platform's services, its MCP server and `tw`. Nextflow's own distribution and its open-source (Apache-2.0) plugins are ordinary Nextflow use, the same as every user of Nextflow. Downloading them is allowed.
  - The test asserts that `tower.endpoint` is always local (TC-051).
- **M5, source facts come first.** Task 1 for the executor is to read the pinned Nextflow version's nf-tower source and write three things into `research.md`, with file:line:
  - the heartbeat interval;
  - the `TraceRecord` and `progress` fields;
  - the literal Authorization header.
  - Then it records real payloads from a real run into `platform/tests/fixtures/payloads/`, with the version in a header. Replay tests use only those recordings (TC-005, TC-007).
- **M6, Streamable HTTP is tested.** `abf-platform mcp --http` binds 127.0.0.1 unless `--host` is given, and is tested with the SDK client (TC-025).
- **M7, the spec is aligned.** US1-1 and SC-001 now use the local fixture pipelines; `nextflow-io/hello` is the manual TC-053.
- **`commandLine` is not stored.** It can carry `--api_key xxx` (FR-008 updated). Params are judged by name only, including nested levels.
- **Counting rule, also written into `research.md`.** It applies the same way to live events and to a rebuild:
  - total = trace rows;
  - succeeded = COMPLETED;
  - cached = CACHED, shown separately and not counted in succeeded;
  - failed = FAILED;
  - a retried task counts once per attempt row, exactly as the trace has it.
- **A killed run during rebuild.**
  - The last-message time is the timestamp of the last line of `.nextflow.log`.
  - With no completion record, the status is "lost". It is never "succeeded" and never "running" (TC-034).
- **Layout.**
  - The package lives at `platform/abf_platform/`, and `platform/` itself has no `__init__.py`, so the stdlib `platform` is never shadowed.
  - pytest runs from inside `platform/`.
  - Dependencies are locked in `platform/constraints.txt`.
  - Task 0 is to install it on WSL Python 3.10.6; if that fails, the executor stops BLOCKED.
- **The existing constitution checks do not scan `platform/`.** Equivalent checks run inside `platform/tests/` (TC-070–072). The four existing check files stay untouched (TC-073).
- **Repo hygiene.** `.gitignore` gains `*.db`, `*.db-wal`, `*.db-shm`, `*.db-journal` and the venv. `docs/PLATFORM.md` says that the default locations are overridable and that both HTTP servers listen only locally by default.
- **Logs.** Log output never contains a token or an Authorization header (TC-044).
- **CI file is not changed.** Changing CI config needs the maintainer's yes. ubuntu-latest already ships Java 17 and Python 3, and the wrapper's own version check fails loudly under `CI=true` if either is missing. If the 300 s per-test timeout bites on a cold cache, stop and report; do not raise the timeout.

Tier A: this feature only adds a spec. It touches none of the plugin's hooks, scripts, skills or commands.
Spec: `spec.md`. Research: `research.md`.

## Shape

New top-level folder `platform/`. It is a Python package `abf_platform` (Python ≥3.10), with dependencies pinned in `platform/pyproject.toml`: `mcp>=2.3,<3`, plus what `mcp` already brings (Starlette, uvicorn). Test extras are `pytest` and `httpx`.

| Module | Job |
|---|---|
| `store.py` | SQLite index. Its location comes from `ABF_PLATFORM_DB`, or the platform config dir (`${XDG_DATA_HOME:-~/.local/share}/abf-platform/index.db`); nothing is hard-coded. Tables: tokens (hash only), runs, processes, failed_tasks. `configText`, env and secret-looking params are never written (FR-008). |
| `receiver.py` | Starlette app for the endpoints in FR-001, with auth per FR-003 and token ownership per US2. Binds 127.0.0.1 unless `--host` is given (FR-004). |
| `status.py` | Derives the status shown at query time: running, succeeded, failed, or lost when there has been no message for more than 3× the heartbeat and no complete (FR-006). Takes an injectable clock for tests. |
| `rebuild.py` | Drops the index and rebuilds it from launch dirs, using `.nextflow/history`, `.nextflow.log` and the trace file (`-with-trace`). Nextflow's records win (US4). |
| `mcp_server.py` | Official `mcp` SDK. Tools `list_runs` and `get_run`, both `readOnlyHint: true`. Transports: stdio, and Streamable HTTP (FR-007). |
| `cli.py` | `abf-platform serve`, `abf-platform token new`, `abf-platform mcp [--http]`, `abf-platform rebuild <launch dirs…>`. |

Each module header names its alternative per principle 1, for example `# Not nf-shard: no auth, TypeScript+Postgres, stale since 2024-09`.

## Tests (red first)

- **Unit tests (`platform/tests/`, pytest):**
  - Replay recorded payloads against the receiver.
  - Auth and ownership checks.
  - Status derivation with a fake clock.
  - Secret filtering.
  - MCP tools called in process through the SDK's client against stdio.
- **Real Nextflow (`platform/tests/test_nextflow_e2e.py`):**
  - Download a pinned Nextflow release to the cache dir.
  - Run two local fixture pipelines under `platform/tests/fixtures/`: one succeeds and one has a task that exits 1. Neither needs a container or the network beyond the Nextflow download.
  - Point them at the receiver with `-with-tower` and a token, then compare with Nextflow's own output.
  - Then run the rebuild comparison from US4.
  - If Java 17+ is missing, the test is marked SKIPPED with the reason printed. It is never silently passed (constitution VI).
- **Wrapper `tests/platform_test.sh`:**
  - Creates a venv under `${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform-venv` and installs `platform[test]`.
  - Runs pytest and exits non-zero on any failure.
  - It is picked up by `tests/run_all.sh` like every other `*_test.sh`. Check that CI has Java; GitHub's Ubuntu runners ship Temurin 17.

## Docs

- New `docs/PLATFORM.md` (FR-009).
- One line in `docs/ROADMAP.md`'s waiting table: the rebuild check now exists (`platform/tests/…`), and the amendment is next.

## Risks and how they are handled

- **Payload fields drift between Nextflow versions.** Pin one version in the e2e test and record it in `research.md`. The receiver ignores unknown fields and never fails on them.
- **Existing constitution checks may scan new folders** (`no_hardcoded_paths`, `scripts_name_their_alternative`, `no_second_run_state`). The new code must pass them unchanged. If a check cannot pass without editing the check, the executor stops BLOCKED. Loosening a check is not the executor's call.
- **The suite runs in WSL with Python 3.10.6.** `mcp` 2.x needs ≥3.10; confirm it installs there.

## Done when

US1–US5 cases pass (US3-4 is manual), the whole suite is green in WSL and CI, the verifier ACCEPTs, and the docs exist.
