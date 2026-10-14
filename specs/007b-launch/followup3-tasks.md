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
