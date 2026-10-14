# 007b follow-up 3: progress ledger (executor)

Plan: `followup3-plan.md`. Cases: `followup3-test-case.md` (contract confirmed 2026-10-14).

## Run log

### G3 red (TC-F3-08, TC-F3-10, TC-F3-41) on unfixed `launch.py`
Fake sbatch made realistic first (`platform/tests/station_harness.py`: records its umask; with state file `sbatch_out` it
creates `slurm-<id>.out` in the `-D` folder with `666 & ~umask`). Agent umask 022. Output of
`pytest tests/test_station_launch.py -k tcf3` before the fix:

```
FAILED test_tcf3_08_09_...: AssertionError: 0o644   (slurm-4242.out)
FAILED test_tcf3_10_...:   AssertionError: ['0022']  (umask sbatch saw; wanted 0o077)
2 failed, 2 passed
```
(the `sbatch_out` file is opt-in because the older TC-012 test lists exactly five files of the folder and may not be edited.)

### G1 red (TC-F3-01..04, 12, 20, 21, 22, 23, 32, 63) on unfixed receiver
`pytest tests/test_followup3.py`: 10 failed, 16 passed before the fix (the 16 are the "stays absent / does not crash"
cases that hold on main too: TC-F3-04 for succeeded runs, 22, 23, 32, 63).

### G2 red (TC-F3-05/06/07/24/25/26/27/28/43/82) on unfixed receiver
`pytest tests/test_followup3.py`: 9 failed, 30 passed (the failures are the late heartbeat/progress/complete answered 401, the
grace end and the revoke cases; the rest hold on main already). The only changed old assertion is the heartbeat line of
`test_tc020_complete_revokes_the_token_and_the_run_data_stays` (401 -> 200, rest of the test untouched).
