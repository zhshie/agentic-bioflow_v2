# cb-T6: hook helper copies stay identical

Source: cloud-burn tasks.json T6 (shard A, order 14, risk M).

## Goal
The safety-net hooks each carry their own copy of `abf_emit`, `abf_cap`,
`abf_jq_works`, `deny` and `ask` (deliberately not shared: a gate must not
vanish with a missing helper). Nothing checks the copies stay in step. Add a
test that does.

## Files
- `tests/hook_helpers_consistent_test.sh` (new). `hooks/` is read-only.
- `specs/cb-T6/plan.md`, `specs/cb-T6/ledger.md`.

## Approach
- Extract each helper body from every `hooks/*.sh` that defines it (awk), drop
  whole-line comments, the header's trailing comment, blank lines and trailing
  blanks; compare same-named copies byte for byte.
- Pin the set of defining files per helper so a new copy must be added to the
  table (and is then compared).
- Existing differences are explicit exceptions inside the test, each pinned to
  its exact text and with its reason:
  - `deny` in confirm_walkthrough.sh: one-line layout of the same two
    statements (also checked to flatten to the same statements).
  - `ask`: confirm_cleanup.sh (one message as reason and context) vs
    confirm_launch.sh (context `$1`, reason `$2`); both pinned, and required to
    still differ.

## RED tests
Pure test addition (code already consistent), so mutation proof instead of RED:
seven temporary mutants of hooks/ each make the test fail; a comment-only edit
passes. Outputs in ledger.md. Mutants never committed (`git checkout -- hooks`).

## Done criteria
- Test passes on unchanged hooks, fails on each mutant.
- `check_scope.sh` clean; `tests/run_all.sh` last line says all passed.

## Environment facts
Linux VM, bash, GNU awk/sed, jq not needed by this test. venv at /tmp/cb/venv.

## Not doing
No change to hooks/, no shared helper file, no comparison of `warn`/`allow`
(not in the brief). Known limit: blank lines inside a quoted multi-line string
(abf_cap's truncation marker) are stripped with the others, as the brief asks.
