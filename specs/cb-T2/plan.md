# cb-T2: table tests for scripts/utils/schema_roles.py

- source: cloud-burn tasks.json T2 (branch `test/cb-t2-schema-roles`, base `origin/v3` @ 62c91293)
- tier: S (pure test addition; no production code touched)

## Goal
Every public name in `scripts/utils/schema_roles.py` gets table-driven cases, so a change to the one place that
decides "which column is the sample / R1 / R2" cannot slip through the two existing callers
(`tests/generate_samplesheet_test.sh`, `tests/prepare_launch_test.sh`), which only reach it through the CLI.

## Files
- `tests/schema_roles_unit_test.sh` (new)
- `specs/cb-T2/plan.md`, `specs/cb-T2/ledger.md`

## Approach
One bash file, standard repo shape (ok/FAIL per case, verdict in the exit code, no network, no settings file),
whose cases are a Python table run by `python3 -I` that imports the module by path:
`schema_properties`, `is_fastq_column`, `is_mixed_reads_column`, `infer_roles` (+ `Roles`, `NeedsDecision`,
`machine_line`), `other_file_columns`, `parse_roles`, `explain`, `load_schema`, `main` (in-process and as a CLI
subprocess: exit codes 0 / 2 / 3, stdout vs stderr). Three real fixtures under `tests/fixtures/schema_input/`
are used as sanity rows; every other schema is synthetic and inline.

## RED tests / proof
Code is already right, so RED = mutation proof (RULES 5.3): for each of ~30 temporary mutants of
`schema_roles.py` the new file must fail; each mutant, the failing-case count and the restore are in `ledger.md`.
Mutants are never committed (`git diff origin/v3 -- scripts/` must be empty).

## Done criteria
- new file passes on unchanged code; every mutant makes it fail; scope guard passes; `run_all.sh` green.

## Environment facts
Python 3 stdlib only; venv at /tmp/cb/venv for the full suite.

## Not doing
No change to `schema_roles.py` (a case that fails on unchanged code would be moved out and recorded as a FINDING);
no edit to any other test; no spec/test-case documents.
