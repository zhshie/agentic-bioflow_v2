# tests/run_all.sh: header comment hard-codes 39 test files; --list shows 94 progress ledger

## Ledger

- [x] Added `tests/run_all_count_test.sh` (TC-001, 002, 004, 005). Before the fix: (b) no-number check (TC-001) and the run-time wording check (TC-002) were RED; (a) `--list` count equals real file count (TC-004) was already GREEN.
- [x] Rewrote the header comment of `tests/run_all.sh` (comment lines only): no literal count, says files are counted at run time, summary line reports the count (banner not claimed to).
