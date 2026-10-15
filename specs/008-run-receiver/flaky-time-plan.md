# Plan: rebuild time comparison flakes on CI (A-tier, test-only)

## Problem
On 2026-10-15 CI (commit cba254d, PR #90 first run) `platform/tests/test_nextflow_e2e.py::_same_runs` failed:
started_at/ended_at from the live index and from `rebuild` differed by 2 s, but the test allows <= 1 s.
The rerun passed. Same code, so this is timing noise, not a product bug.

## Why it happens (to be confirmed by the executor, cite sources)
Live times come from Nextflow's HTTP messages; rebuilt times come from `.nextflow.log` / trace files.
Nextflow samples the clock separately for each, and both are truncated to whole seconds, so on a slow
CI runner the gap can reach 2 s. research.md "Time resolution" documents the 1 s case only.

## Change
1. Find the exact CI failure log (`gh run list` / `gh run view --log-failed` on the #90 branch runs) and record which field and by how much.
2. Confirm from Nextflow source/research.md where each timestamp is taken; record in research.md "Time resolution".
3. Widen tolerance to a named constant (e.g. `_CLOCK_SLACK_SECONDS = 3`) with a comment citing the reason; use it at both lines and at line ~385 only if the same reasoning applies.
4. Keep every other assertion unchanged (fields still compared exactly; ended_at None still exact).
5. Add a PITFALLS.md entry.

## Not in scope
Product code, rebuild logic, other tests, CI config.

## Done when
Full suite green in WSL (except the known gate_process_count env failure) and on CI; verifier PASS.
