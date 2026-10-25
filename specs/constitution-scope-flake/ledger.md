# constitution-scope-flake progress ledger

## 2026-10-25 executor notes, fix round (stamp 20261025-1545-L-flake)

Status: ROOT CAUSE FOUND AND FIXED. (Round 1 wrote "NOT FOUND" after 10 plain runs and 16 simulated runs; the verifier asked for the
full counts from the contract, one row per condition. Doing them produced the red.)

### What the CI log says (run 40147548108, attempt 1, 2026-10-25 00:43 UTC, PR fix/migrate-reports-queue)
Only one line failed: `TC-002: unchanged, no main: the fingerprint line runs and is ok  FAIL: rc=1`. That is the FIRST inner run
(the script run again inside the scratch no-main clone). Every later inner run passed, and the retry passed.

### Reproduction on the BASE version of the test (commit 2e31aab, tests/constitution_scope_test.sh blob e8a39b6f), in WSL
Each condition is its own row. All commands ran in /tmp/rp clones of the worktree (so the worktree stayed clean).
| TC | Condition | How | Runs | Red |
|---|---|---|---|---|
| TC-001 | plain, full clone | `for i in $(seq 50); do bash tests/constitution_scope_test.sh >log.$i 2>&1 \|\| echo FAIL $i; done` | 50 | 0 |
| TC-002 | shallow clone | `git clone --depth 1 --no-local` of base, run in it | 20 | 0 |
| TC-002 | no `main` ref | full clone, `checkout --detach`, no `refs/heads/main` | 20 | 0 |
| TC-002 | shallow AND no `main` (what CI has) | `--depth 1` clone, detached, no `main` | 20 | **1 (run 12)** |
| TC-002 | TMPDIR in another folder | `TMPDIR=/tmp/simtmp bash tests/constitution_scope_test.sh` in the full clone | 20 | 0 |
| TC-002 | two copies at the same time, SAME clone (same TMPDIR) | two background runs in the same shallow clone, `wait` both | 20 x 2 | 0 |
| TC-002 | two copies at the same time, two separate clones | one run in each of two shallow clones at once | 20 x 2 | 0 |
| (load) | 3 shallow no-main clones, 60 runs each, all three loops at the same time; run on the round-1 version (it prints the inner FAIL lines) | 3 background loops | 180 | **4** (loop 1: #8, #19; loop 3: #23, #38) |

The red in the shallow+no-main row was exactly the CI line: `TC-002: unchanged, no main: the fingerprint line runs and is ok  FAIL: rc=1`
(first inner run). So the red needs the CI shape (shallow, no main) and some CPU load; it is about 1 in 20 to 1 in 45 runs. The 7 non-load
rows above were run one after another with nothing else running, which is why round 1 saw only green.

### Where it is red (TC-003): the inner run's own FAIL line
The round-1 diagnostics showed the inner reason. All four reds were one check inside the inner run failing although the text IS in the file:
- `...names the 2026-10-02 subagent case   FAIL: no '2026-10-02' in the Amendments section` (twice: once the inner TC-002 run, once the TC-013 inner run)
- `TC-042: ...via hooks/confirm_launch.sh   FAIL: no '`hooks/confirm_launch.sh`' in the Safety Net section`
- `TC-041: ...via hooks/confirm_cleanup.sh   FAIL: no '`hooks/confirm_cleanup.sh`' in the Safety Net section`
Which check goes red changes from run to run, and it is always a `sn_has` / `am_has` check (text piped from `$SN` / `$AM`).

### Root cause
`printf '%s\n' "$SN" | grep -qF -- "$2"` under `set -o pipefail`. `grep -q` quits at the first match. The text is not necessarily delivered in one
write (the Safety Net section is 4,506 bytes, the Amendments section 29,756 bytes). If grep finds its match in the first part and exits before printf
has written the rest, printf gets "Broken pipe" and exits non-zero; `pipefail` then makes the whole pipeline fail although grep matched. The check then
says "not found" and prints `FAIL`. Whether it happens depends on who runs first, so it shows up under load and the rerun is green. That is the CI pattern.
(Round 1 ruled SIGPIPE out because the inputs are far below the 64 KB pipe size; that missed that the writer can still be cut off between writes.)

Proof, with the pipelines taken out of the test (`sigpipe.sh`: the same two pipelines on the real `$AM` and `$SN`, 4,000 loops each, 8 copies at the same time):
- old form (`grep -qF`): false "not found" 22 times in total (Amendments text 21, Safety Net text 1; every one of the 8 copies hit at least once on the Amendments text);
- new form (`grep -F ... >/dev/null`): 0 in all 8 x 8,000 loops.
- With a single copy and no load (3,000 loops): 0 for both forms.

### Fix (TC-010: aimed at the root cause)
Only `tests/constitution_scope_test.sh`.
- Every check that pipes text into `grep -q` now uses `grep -F ... >/dev/null`, so grep reads all the input and only grep's own result is used. Same patterns,
  same strings, same pass/fail meaning. Sites: `sn_has`, the "cannot be relaxed" check, `am_has`, `am3_has`, `pa_has`, the flake TC-011 and TC-012 greps, TC-E1, TC-E7, TC-E8.
  (`has()` and the TC-009 file greps read a file, not a pipe, and stay as they were.)
- A comment above `has()` says why.
- New guard case `flake TC-014`: fails if any non-comment line of the file pipes into a `grep -q...`. Red on the base (RED commit 2b6c8ea), green after the fix (GREEN commit 7928f96).
- No retry loop, no skipped case, no loosened assertion, no quarantine, `run_all.sh` untouched, constitution and PINNED_SN_SHA256 untouched.
- Round 1's diagnostics stay (stderr names the failing case; inner FAIL lines are kept in the TC-002 reason).

### Results after the fix (commit 7928f96), same conditions
| TC | Condition | Runs | Red |
|---|---|---|---|
| TC-005 | plain, full clone | 50 | 0 |
| TC-006 | shallow clone | 20 | 0 |
| TC-006 | shallow AND no `main` | 20 | 0 |
| TC-006 | TMPDIR in another folder | 20 | 0 |
| TC-006 | two copies at once, same clone | 20 x 2 | 0 |
| TC-006 | two copies at once, two separate clones | 20 x 2 | 0 |
| TC-006 | the load that gave 4 reds in 180 on round 1: 3 shallow no-main clones x 60 at the same time | 180 | 0 |
| TC-007 | last line `all passed`, exit 0 | every run above | 0 |

### TC-008: case names
Base (2e31aab) prints 98 `ok` cases; HEAD prints 102. Missing at HEAD: none. New at HEAD: flake TC-011, TC-012, TC-013 (round 1), TC-014 (this round).

### Other notes
- TC-009: the only assertion text touched is the grep flag form. No expected string changed.
- TC-014 (quarantine): `tests/quarantine.txt` untouched. TC-015: `tests/run_all.sh` untouched. TC-016: constitution and fingerprint untouched.
- TC-023: no migration needed: only a test script and this ledger changed; no data or schema.
- Not changed, on purpose: `mkclone` has no `set -e` around `cp`; `NEWFP=$(... | grep -oE ... | head -1 ...)` and `... | grep -nF | head -1` (the early exit is `head`, the value is already complete, and they sit in command substitutions whose status is not tested). No evidence they cause a red.
