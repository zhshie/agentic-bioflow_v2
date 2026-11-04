# cb-T4 plan: rename the two different `to_gb` helpers

- Source: cloud-burn tasks.json T4.
- Goal: `scripts/tune_resources.sh:75` and `scripts/why_pending.sh:86` both define `to_gb` with
  different signatures and semantics (string in, decimal GB out / "number unit" in, ceil integer GB
  out, bare number = MB). Rename to `mem_to_gb` (tune_resources.sh) and `mem_to_gb_ceil`
  (why_pending.sh) so one cannot be pasted over the other. Behaviour byte-identical.
- Files: `scripts/tune_resources.sh`, `scripts/why_pending.sh`, `tests/mem_to_gb_test.sh` (new),
  `specs/cb-T4/plan.md`, `specs/cb-T4/ledger.md`.
- Call sites at origin/v3 62c91293: tune_resources.sh 75 (def), 154 (comment), 157 (2 calls),
  276, 277; why_pending.sh 86 (def), 108. Nothing else in scripts/, tests/, skills/ references
  the name (only prose in docs/reports/sweep-2026-11.md, not touched).
- Approach: capture outputs of both functions on the base for a table of inputs (before any
  change); write tests/mem_to_gb_test.sh asserting exactly those outputs, extracting each function
  from its script by name (the scripts run main when sourced); watch it fail on base (names do not
  exist); rename; watch it pass.
- RED tests: one table test per function, plus absence of the old name in both scripts.
- Done: new test green, existing tune_resources/why_pending tests unchanged and green, check_scope
  OK, run_all last line says all passed.
- Environment: venv at /tmp/cb/venv, `pip install -e platform pytest`; build/egg-info removed.
- Not doing: moving the helpers into scripts/utils/portable.sh, unifying semantics, docs.
