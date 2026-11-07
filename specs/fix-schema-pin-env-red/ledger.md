# 修 test_no_schema_change 環境誤報（三點比對） progress ledger

## executor 進度（2026-11-07）
- 已做：test_mcp_launch_pipeline.py 加 `schema_diff` helper（`origin/v3...HEAD`）、`test_schema_pin_ignores_base_advance`、`test_schema_pin_still_catches_branch_change`（schema.sql／store.py／migrations 三種參數）；`test_no_schema_change` 改用 helper。四條新測試在 abf-fast-suite 鏡像綠；反證測試證明分支真改三處時 helper 非空（紅）。
- 失敗：`test_no_schema_change` 在 abf-fast-suite 鏡像仍紅。鏡像是 clone，其 `origin/v3` = worktree 本機 `v3` 分支(075b6177)，比分支底(87107ae9，worktree 的 origin/v3)舊，所以三點比對把 #377/#378 的 store.py 變動算成分支的。worktree 內直跑則空（綠）。
- 建議：(a) 測試在比對前 `git fetch origin refs/remotes/origin/v3:refs/remotes/origin/v3`；或 (b) abf-fast-suite 鏡像把 worktree 的 refs/remotes/origin/v3 帶過去；或 (c) 以 first-parent 上第一個 "Merge pull request" 為底。需 lead 裁決，違反「照 origin/v3...HEAD」裁決所以我沒擅自做。
