# constitution-scope-flake progress ledger

## 2026-10-25 executor notes (stamp 20261025-1545-L-flake)

### What the CI log says (run 40147548108, attempt 1, 2026-10-25 00:43 UTC, PR fix/migrate-reports-queue)
Only one line failed: `TC-002: unchanged, no main: the fingerprint line runs and is ok  FAIL: rc=1`. That is the FIRST inner run
(the script run again inside the scratch no-main clone). Every later inner run in the same job (TC-007, TC-003, TC-008, TC-004, TC-006)
passed, and the retry (own empty TMPDIR) passed. The inner run's own output was thrown away, so the failing inner case is unknown.
(#228 run 40170104859 attempt 1 was still running / its log not yet readable when checked; the other recent run with attempt 1 red,
40155700350, failed on platform_* tests, not this file.)

### Reproduction attempts (TC-001, TC-002) - base version of the test, all green
| Condition | How | Result |
|---|---|---|
| 10 plain runs in the worktree (WSL, /mnt/c) | `for i in 1..10: bash tests/constitution_scope_test.sh` | 10/10 green, 0 red |
| shallow clone `--depth 1 --no-local` of HEAD, no `main`, TMPDIR=/tmp/simtmp (other folder), two copies of the test run at the same time in the SAME clone (shared TMPDIR) | `.scratch/sim.sh 8` (8 runs x 2) | 16/16 green, 0 red |
| the four tests that run just before it in CI (commands_resolve_their_own_paths, conditions_matrix_test, confirm_cleanup_candidates_timing_test, confirm_walkthrough_test) run first in a fresh shallow clone | `.scratch/leak.sh` | all rc=0; `git status --ignored` empty; TMPDIR empty; no leftover processes. They leave no state that could break this file |
Not reproduced locally. The three things code reading ruled out: SIGPIPE under `pipefail` (all `printf | grep -q` inputs are far below the 64 KB pipe buffer; constitution is 49 KB flattened and is only piped to a grep that reads all of it), run_all parallelism (it is sequential), shared TMPDIR (every scratch dir comes from `mktemp -d`).

### Root cause
NOT FOUND. I could not make the test go red, so I cannot honestly claim a fix (plan: "if 50 runs + simulated conditions cannot reproduce, do step 4 and report BLOCKED").

### What changed (plan step 4: say which case failed, next time)
Only `tests/constitution_scope_test.sh`; no case removed, no assertion loosened, no quarantine, run_all untouched, constitution and PINNED_SN_SHA256 untouched.
- `bad()` now also writes `constitution_scope_test FAIL: <name>: <reason>` to stderr (stdout line unchanged, so `grep FAIL` on the inner output still works).
- The TC-002 (no main) failure reason now carries the inner run's own FAIL lines (this is exactly the line that went red in CI and showed only `rc=1`).
- TC-E6 (constitution_6_test / constitution_checks_exist_test) no longer hide their output: on failure their FAIL lines are in the reason. Names of the two cases unchanged.
- New cases flake TC-011/012/013 (stderr names the failure; stdout line unchanged; green run prints nothing on stderr).
Not touched, in case it matters for the next red: if the next failure shows a `cp` or `git clone` problem, `mkclone` ignores `cp` failures (no `set -e`); not changed here because that would be a guess.

No migration needed: only a test script and this ledger changed; no data or schema.
