# upgrade-hint-followup progress ledger

- [x] RED (commit "RED:"): new test TC-H1/H2/H4 on base script output: `TC-H1/H2/H4 hint section  FAIL: sec=''`
- [x] GREEN: hint now says docs/TESTING.md 的「Owner binding follow-up」一節第 2 步; new test ok; TC-U2/U9/U16/U28 still ok
- [x] TC-U27 block deleted (4 lines: the if/else + ok). ok count: before 1 TC-U27 ok line, after 0 (new test adds its own 1 ok): net difference exactly 1
- Scope: git diff --stat = deploy/platform-upgrade.sh (1 line: hint text) + tests/platform_upgrade_test.sh. Only TC-U27 lines were deleted.
- Note: TC-U26 in platform_upgrade_test.sh already FAILs on the base (108bfdff): it expects tests/hosted_deploy_test.sh to differ from merge-base, but #281 is already merged so the diff is empty. Not touched (out of scope, would be weakening).
