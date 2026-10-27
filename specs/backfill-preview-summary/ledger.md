# runs offer-cleanup 預覽的總結行不再寫「已提出 0 張」 progress ledger

- [x] cli.py `cmd_runs_offer_cleanup`: preview (`--list` or no `--apply`, same `preview` flag) prints the preview summary line, N counted from `would_offer` rows; `--apply` line unchanged.
- [x] test_cleanup_backfill.py: 3 new tests (TC-001..007, 012); no existing assertion changed.
- [x] docs/TESTING.md step 2: last line starts with `預覽：`.
- 不需要 migration，只改終端機文字。
