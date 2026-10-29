# TC-U26 改成檢查現在的 want_list，不再拿 merge-base 差異當檢查 progress ledger

- [x] TC-U26 now checks the current `want_list=` line of tests/hosted_deploy_test.sh (7 entries), placed before the `if mb=` block; TC-U28 untouched (its skip label now only names TC-U28). Only tests/platform_upgrade_test.sh changed.
  - RED (before, in worktree under WSL, origin/v3 present): `TC-U26 FAIL`, `1 FAILED`; ok count 33. In the mirror without origin/v3 it was only a skip (no protection).
  - GREEN: `TC-U26 ... want_list names platform-upgrade.sh and the six originals  ok`, `all platform_upgrade tests passed`, ok count 34 (= 33 + 1); also ok in the mirror with no origin/v3 (not skipped).
  - Negative proof 1 (removed `$D/platform-upgrade.sh` from line 283): `TC-U26 FAIL: want_list missing: $D/platform-upgrade.sh`. Negative proof 2 (removed `$D/backup.sh`): `TC-U26 FAIL: want_list missing: $D/backup.sh`. (Also hosted_deploy check red, so 2 FAILED, expected.) File restored with git checkout.
