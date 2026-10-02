# Tasks: plugin scope (005, #48)

Derived from `plan.md`. Test-first: each stage commits its red tests, then the implementation.
Test cases are in `test-case.md` (approved 2026-10-02).

## S1 - in-use helper, marker, gates (TC-001..013, 016..020)

- [ ] T001 Write `tests/in_use_test.sh` (fake HOME / state dir / settings / pointer). Cases TC-001..006, 007, 008, 009, 010, 011, 012, 013, 017, 018, 019, 020 against every hook. Commit it red.
- [ ] T002 `hooks/in_use.sh`: `abf_in_use <raw-input> <command-text>`; Seqera MCP, session id, marker, command text (plugin root, plugin script names, `tw`, deployment paths), deployment cwd / `storage_root`; builtins only; unsure means in use.
- [ ] T003 `hooks/plugin_intro.sh` writes `$STATE/in-use/<sid>` when the plugin is used (typed command, Skill load, natural-language door), also when the overview was already shown.
- [ ] T004 Gate `confirm_launch.sh`, `confirm_cleanup.sh`, `confirm_walkthrough.sh`, `guard_plugin_files.sh` right after the raw input is read (before jq).
- [ ] T005 Gate `next_step.sh` (Stop) and `session_start.sh` (SessionStart).
- [ ] T006 Existing hook tests stay green unchanged (they carry no session id: FR-005).

## S2 - D3 exceptions (TC-014, TC-015)

- [ ] T007 Red tests in `tests/confirm_launch_test.sh`: WSL command word and `-o BatchMode=yes` do not ask; plain ssh, `BatchMode=no`, `echo wsl; ssh` still ask.
- [ ] T008 `confirm_launch.sh` D3 loop skips those two shapes.

## S3 - constitution 2.0.0 (TC-021, TC-022)

- [ ] T009 `tests/constitution_scope_test.sh`, red.
- [ ] T010 Amend `.specify/memory/constitution.md` to 2.0.0 (Safety Net scope, in-use definition, rationale, impact, Last Amended 2026-10-02).
- [ ] T011 Update every citing doc: `docs/PRINCIPLES.md`, root `CLAUDE.md`, `README.md`, `docs/SITE_ADAPTER.md`, hook headers.

## S4 - speed (TC-023)

- [ ] T012 `tests/in_use_speed_test.sh`: main vs this branch, 20 calls each, not-in-use input, pass when new <= main x 1.1; skip when git or `main` is unavailable.
