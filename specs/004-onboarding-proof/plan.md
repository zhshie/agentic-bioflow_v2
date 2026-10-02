# Implementation Plan: onboarding proof per machine

**Branch**: `004-onboarding-proof` | **Spec**: `spec.md` | **Test cases**: `test-case.md` (built ahead of approval on the maintainer's instruction; see overview)

## Summary

Record "this machine proved the environment on public test data" as a machine-scoped setting, written only from a run Platform confirms. `setup_verify.sh` answers "already set up" only with that record, and returns a new exit 3 without it. `commands/setup.md` routes every entry (exit 3, repair after `--use`, first run) through step 8, and gates step 9 on the record.

## Technical context

- Bash + jq, the same as `scripts/runs_board.sh`. No Python is needed.
- The settings layer is `scripts/settings.sh`:
  - `MACHINE_KEYS` routes a key to `config/machines/<machine_id>.yaml`.
  - `setting` and `set_setting` already route on it.
  - `machine_id` already tells Git Bash and WSL on one box apart.
- Platform query: `tw -o json runs list --workspace <ws>` gives `.workflows[].workflow.{id,projectName,status,userName}`. This shape was measured live on 2026-09-18 (runs_board.sh header). It is the same call and token loading as `runs_board.sh`. `tw runs view` was not chosen because its output has no project name (tower-cli `ViewCmd.java`).

## Design

1. `scripts/settings.sh`: add `proof_run` to `MACHINE_KEYS`, with a comment saying why it is per machine.
2. New `scripts/setup_proof.sh`:
   - `--check`: if `setting proof_run` is non-empty, print `proven on this machine: <value>` and exit 0. Otherwise print that it is not proven and point to setup step 8, exit 1.
   - `--record <run-id>`:
     - Read `workspace_id --required`, `seqera_user` and `tw_bin`, and load the token the same way runs_board does.
     - Run `tw -o json runs list --workspace`. Exit 1 if tw fails or jq cannot parse the result (FR-004).
     - Select the entry by id. Exit 1 if it is missing, if status is not `SUCCEEDED`, or if projectName is not `nf-core/demo`. Also accept a projectName that ends with `/nf-core/demo`, because a URL-form name may appear.
     - Exit 1 if the userName differs from `seqera_user` when that is set.
     - Each refusal names its reason.
     - On success, `set_setting proof_run "<id> <YYYY-MM-DD> nf-core/demo"`, print it, and exit 0.
   - Usage errors exit 2.
3. `scripts/setup_verify.sh`: when preflight passes, call `setup_proof.sh --check`.
   - Proven: the current message, plus the proof line, exit 0.
   - Not proven: a new message ("settings are complete, but this machine has not yet proven the environment on public test data - commands/setup.md step 8"), exit 3.
   - Everything else stays unchanged.
4. `commands/setup.md`:
   - T27 paragraph: handle exit 3 by going straight to step 8, then steps 9 and 10.
   - Repair: before finishing, run `scripts/setup_proof.sh --check`. If it is not proven, do step 8 and then step 9.
   - Step 8: after nf-core/demo succeeds, run `scripts/setup_proof.sh --record <run-id>`.
   - Step 9: only after `--record` succeeded.
5. `docs/SETTINGS.md`: document the `proof_run` row and add it to the machine-file list in the table near line 406 (FR-006).

## Constitution check

- Principle 3: no paths. Everything is derived from settings. `tests/no_hardcoded_paths.sh`.
- Principle 4: the command layer names no scheduler or relay. `tests/command_layer_is_site_neutral.sh` covers setup.md.
- Principle 7: this feature is the fix.
- Principle IV, Evidence Before Claims: the record is written only from Platform's answer.
- Safety net: nothing here submits or deletes. `setup_proof.sh` only reads Platform and writes one setting.

## Tests

- `tests/setup_proof_test.sh` (new) uses a fake tw that prints `$RUNS_LIST_FILE` or exits non-zero. It covers TC-004–TC-009 and TC-011, and checks the machines-file vs env.yaml placement.
- `tests/setup_verify_only_test.sh`:
  - The existing "already set up" case now needs a proof record: TC-001.
  - New cases: TC-002 and TC-003.
  - The existing no-settings and preflight-fail cases are TC-010.
- `tests/setup_doc_test.sh` (new): TC-012–TC-014 as greps on `commands/setup.md` for the specific instructions.
- TC-015 covers docs/SETTINGS.md, and TC-016 is the full suite.
- `tests/run_all.sh` must pick up the new test files. Check how it discovers tests.

## Complexity and risk

- Small: one new script of about 80 lines, a 10-line change to setup_verify, and documentation.
- Risk: existing machines get exit 3 on their next setup. This is intended and stated in the spec Assumptions.
- Risk: projectName format on real Platform runs launched from a URL. Mitigated by accepting a `/nf-core/demo` suffix. Verify on the real site (manual checklist).
