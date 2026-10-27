# cloud-cleanup-backfill progress ledger

- [x] `runs offer-cleanup` (cli.py), `actions.offer_cleanups`, `offer_cleanup(dry_run=)` (actions/__init__.py): preview by default, `--apply` writes pending requests only. `--all` walks every run of the index; `offer_cleanup` skips non-succeeded with its own reason (test cases TC-001/TC-010 want those rows).
- [x] Tests `platform/tests/test_cleanup_backfill.py` (17 tests). Existing assertions updated (ruling 5, 7): `test_cleanup_offer.py` signature pin gets `"dry_run"`; `test_web_parity.py` INTERNAL gets `offer_cleanups`.
- [x] Docs: OPERATIONS.md row in section 5; TESTING.md section.
- [x] Fix round (TC-026, TC-061): `test_all_apply_offers_for_each_succeeded_run` now builds `FakeSite(destructive_log=True)` and asserts destructive.log, ssh log and slurm jobs are empty after `--all --apply`.
