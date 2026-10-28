# cloud-cleanup-backfill progress ledger

- [x] `runs offer-cleanup` (cli.py), `actions.offer_cleanups`, `offer_cleanup(dry_run=)` (actions/__init__.py): preview by default, `--apply` writes pending requests only. `--all` walks every run of the index; `offer_cleanup` skips non-succeeded with its own reason (test cases TC-001/TC-010 want those rows).
- [x] Tests `platform/tests/test_cleanup_backfill.py` (17 tests). Existing assertions updated (ruling 5, 7): `test_cleanup_offer.py` signature pin gets `"dry_run"`; `test_web_parity.py` INTERNAL gets `offer_cleanups`.
- [x] Docs: OPERATIONS.md row in section 5; TESTING.md section.
- [x] Fix round (TC-026, TC-061): `test_all_apply_offers_for_each_succeeded_run` now builds `FakeSite(destructive_log=True)` and asserts destructive.log, ssh log and slurm jobs are empty after `--all --apply`.
- [x] Full-suite rerun (stamp 20261027-1950-L-backfill): run 1 = 126/127, only egress_ctl_restart_test.sh failed (load flake, passed on retry; shard_3 ok in 283s). Run 2 = 126/127, only platform_shard_3_test.sh hit the 300 s local timeout. Shard 3 run directly: 1166 passed in 344 s (exit 0). Same file set without the new test took 351 s earlier on this machine (developer-agent ruling), so the timeout is the known capacity issue, not code. tests/platform_test.sh and SHARDS untouched.
