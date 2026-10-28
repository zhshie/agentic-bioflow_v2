# 時鐘測試項目拆成兩個，每項 ≤180 秒；更正 suite-speed 帳本一句 progress ledger

## 2026-10-28 executor (stamp 20261028-2100-clocksplit1), base v3 74e11ed

- [x] Tests first (RED 0b0cee1): `platform/tests/test_platform_parts.py` (clock2, ten entries, SC-01/05/14/17/18/29), `tests/run_all_shard_test.sh` (10 wrappers), `tests/run_all_retry_test.sh` (SC-06, SC-19, SC-20).
- [x] `tests/platform_test.sh`: `clock` and `clock2` parts (`LAST_1`, `LAST_2`; `LAST` = both); `tests/platform_clock_2_test.sh` new; `tests/run_all.sh` three patterns; `tests/quarantine.txt` line 12; docs TESTING/PLATFORM; `platform_clock_test.sh` header.
- [x] `specs/suite-speed/ledger.md` line 26 only (1 insertion, 1 deletion).
- `.github/` untouched (ruling 2).

### Before (work method 0), WSL, nproc 16, HEAD 86784e1 (= base plus plan and test cases)
- Collect-only, `ABF_PLATFORM_PART=all`, lines with `::` sorted: 5102 lines, sha256 540062cc3dffa653b028d39c0745056241525404adeab5a5aba9a74cb2f8dead.
- `bash tests/platform_clock_test.sh` alone: 228 s (3m48.7s; 85 passed in 94.0 s for test_station_e2e.py, 23 passed in 132.4 s for test_nextflow_e2e.py), load before 3.45, after 4.78. Both single files are under 180 s, so no BLOCKED (SC-27).
- `run_all.sh --list --allow-msys`: 133 lines.
- Eight numbered lists from `ABF_PLATFORM_LIST=1` compared before and after: identical for PART=1..8 (only `clock`, `clock2` and `all` differ, as planned).

### After
- Collect-only, same command: 5106 lines, sha256 e61b23c7764f9624dca84b60b89aefd8d3b5e0aa2137ea5862e3876643013902. The diff against before is exactly: 3 test names changed (nine -> ten in `test_ps03`, `test_ps34_ps35`, `test_tcf3_06`) and 4 new tests (test_sc01, test_sc17, test_sc18, test_sc29). Every other id is identical, nothing lost, nothing doubled.
- `bash tests/platform_clock_test.sh` alone: 80.7 s (85 passed); `bash tests/platform_clock_2_test.sh` alone: 124.0 s (23 passed). Load 4.74 and 2.00 before the two runs. Sum 204.7 s against 228 s before. Each is under 180 s.
- `run_all.sh --list --allow-msys`: 134 lines (one more).

### Existing assertions touched (only because the count or the name list changed)
- `test_platform_parts.py`: PARTS/ENTRIES gain clock2/CLOCK2; `test_tcf3_05` clock is one file, clock2 the other, "not in any shard" part kept; `test_ps08` message substring and `clock3`/`clock_2` added; `test_ps11` pattern gains the new name; `test_ps27...` docs must also name `platform_clock_2_test.sh`.
- `run_all_shard_test.sh`: pattern, name list, 9 -> 10 (SS-11, SS-36, SS-37); TC-002 and the counter-examples kept.
- `run_all_retry_test.sh`: only additions (SS-71 loop gains the new name; SC-06, SC-19, SC-20). TC-089, PS-22, PS-24 untouched and green.
