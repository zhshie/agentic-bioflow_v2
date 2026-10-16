# 009b: action layer (platform/abf_platform/actions/), behaviour unchanged progress ledger

- [x] Step 1 (RED, commits 55c9328, 0c342dc): `platform/tests/test_actions_layer.py` written before `actions/` existed. Run result: 38 failed, 10 passed (the passing ones are guards that already hold at v3) (ImportError "cannot import name 'actions'" for the (a) parity, (c) refusal and (d) launch tests, plus failing import-scan, packaging, confirm-docstring, docs and changelog checks).
- [x] Step 2: `platform/abf_platform/actions/__init__.py`: six read actions (bodies moved from mcp_server.py), `platform_path_for`, `TERMINAL` sentinel, `launch`/`cancel` (keyword-only `confirmed_by`, checked first, then `confirm.*`).
- [x] Step 3: `mcp_server.py` tool bodies are one call into `actions`; `abf_launch/cli.py` calls `actions.launch`/`actions.cancel` with `confirmed_by=actions.TERMINAL` after `terminal.ask`, no longer imports `confirm`; `confirm.py` docstring updated; `pyproject.toml` lists `abf_platform.actions`.
- [x] Step 4: `docs/PLATFORM.md` section "Action layer"; `CHANGELOG.md` one line.
- [x] Step 5: `test_actions_layer.py` 48 passed after the change; full evidence below.

Existing tests changed: none (no import broke; tests that call `confirm.*` directly are outside the scan).
Pinned guards untouched: TC-010, tc024, TC-061, `LAUNCH_ALLOW`.

Evidence: `bash tests/run_all.sh` in WSL Ubuntu at 89fe67f (all code): 103/103 passed, all green. Re-run at the final commit (this ledger edit only) recorded in the executor status.
