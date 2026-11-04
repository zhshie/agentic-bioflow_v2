# CI 新增 gitleaks 與 pip-audit 掃描（獨立 workflow） progress ledger

- [x] .gitleaks.toml、platform/pip-audit-ignore.txt（cbf1cdaa）；security.yml（0ce2ca05，由 developer-agent 寫，因 .github/ 受寫入防護）；tests/ci_security_workflow_test.sh 12 項檢查全綠；docs/TESTING.md 新增「CI security checks」一節。
- tests.yml 未動。兩個 job 目前不是必過檢查（ruleset 未動）。方向題給維護者：觀察約兩週後是否設為必過？
- uses 釘版與查證（TC-010）：2026-11-04 以 `gh api repos/<owner>/<repo>/git/ref/tags/<tag>` 查證，兩者皆為 lightweight tag（object.type=commit），sha 與 security.yml 一致：
  - `gh api repos/actions/checkout/git/ref/tags/v4.2.2` -> object.sha `11bd71901bbe5b1630ceea73d27597364c9af683`（security.yml:24、:42）
  - `gh api repos/actions/setup-python/git/ref/tags/v5.6.0` -> object.sha `a26af69be951a213d495a4c3e4e4022e16d87065`（security.yml:43）
- 兩個 job 的首跑結果：未做（executor 不得 push）；由 lander／developer-agent 貼回此處。

## 爆炸半徑證明（TC-057、TC-058；風險 L，碰 .github/）
1. 觸發與權限：`security.yml` 觸發為 pull_request、push 到 v3／main、每週一 03:17 UTC 排程、workflow_dispatch（security.yml:6-12）；權限只有 `contents: read`（:14-15），不用 pull_request_target，沒有 secrets、沒有寫入權限。
2. 與 tests.yml 的共用物：無。workflow 名 `security`，job 名 `gitleaks`、`pip-audit`；tests.yml 的 job 為 `shard`、`run_all`（tests.yml:56、:100），無同名。對 security.yml grep `concurrency|cache` 為 0 筆（不用 actions/cache、無 concurrency 群組、無 cache key）。tests.yml 未被修改（tests/ci_security_workflow_test.sh 的 test_existing_tests_yml_untouched 為 ok）。
3. 非必過檢查，最壞情況：ruleset／分支保護沒動，這兩個 job 不是必過檢查。最壞情況是新 job 紅燈，PR 仍可合併，`run_all` 的狀態與 job 組成不受影響，不會擋住合併佇列。
4. 移除方式：刪除 `.github/workflows/security.yml` 一個檔即完全移除兩個 job；`.gitleaks.toml`、`platform/pip-audit-ignore.txt` 留著無害（只被該 workflow、測試與 docs/TESTING.md 引用）。

## 測試先紅的輸出（TC-042）
RED 提交 7fc32540（測試檔已寫、security.yml 與 .gitleaks.toml 還不存在）。2026-11-04 以 `git archive 7fc32540` 解到暫存目錄後執行 `bash tests/ci_security_workflow_test.sh`，輸出（結束碼 1）：
```
FAIL test_security_workflow_exists_and_is_separate
FAIL test_job_names_do_not_collide_with_required_check
FAIL test_triggers
FAIL test_permissions_are_read_only_and_no_pull_request_target
FAIL test_every_uses_is_pinned_to_full_sha
FAIL test_no_way_to_turn_checks_off
FAIL test_allowlist_entries_have_reason_and_are_not_blanket
FAIL test_gitleaks_download_is_verified
FAIL test_gitleaks_scans
FAIL test_gitleaks_uses_redact
skipped test_existing_tests_yml_untouched (no origin/v3 history)
ok   test_existing_tests_yml_untouched
FAIL test_pip_audit_targets_both_files
11 check(s) failed
```
之後實作完成，在 HEAD 再跑為全綠（12 項檢查）。
