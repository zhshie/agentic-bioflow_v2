# 直接用環境變數放寬轉送對端時，送出前檢查要警告 progress ledger

- [x] PEER-1..12 tests added (RED c77459d), hook block added (GREEN). TC-001..024 automated in tests/confirm_launch_test.sh.
- Evidence (TC-025..032):
  - `git diff --name-only origin/v3...HEAD`: hooks/confirm_launch.sh, tests/confirm_launch_test.sh, specs/relay-env-warning/* only.
  - diff of scripts/ platform/ deploy/ docs/ skills/ commands/ hooks/hooks.json vs origin/v3: empty.
  - hooks + tests diff: 0 deleted lines (additions only). New hook block sits right after the EXTRA_DOMAINS block, appends to RELAY_LIST, no new ask/allow/exit, only `[[ == ]]` then one `[[ =~ ]]`.
- TC-033 two-branch comparison of `bash tests/confirm_launch_test.sh` (origin/v3 4ade619 vs HEAD): base 398 lines, branch 425 lines. Differences: +27 PEER lines, plus one summary line `idg cases: 108 -> 116` (8 new idg asserts). Every existing line ok in both; 0 FAIL on branch.
