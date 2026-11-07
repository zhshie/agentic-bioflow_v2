# 修 test_no_schema_change 環境誤報（三點比對） progress ledger

## executor 進度（2026-11-07）
- 已做：test_mcp_launch_pipeline.py 加 `schema_diff` helper（`origin/v3...HEAD`）、`test_schema_pin_ignores_base_advance`、`test_schema_pin_still_catches_branch_change`（schema.sql／store.py／migrations 三種參數）；`test_no_schema_change` 改用 helper。四條新測試在 abf-fast-suite 鏡像綠；反證測試證明分支真改三處時 helper 非空（紅）。
- 失敗：`test_no_schema_change` 在 abf-fast-suite 鏡像仍紅。鏡像是 clone，其 `origin/v3` = worktree 本機 `v3` 分支(075b6177)，比分支底(87107ae9，worktree 的 origin/v3)舊，所以三點比對把 #377/#378 的 store.py 變動算成分支的。worktree 內直跑則空（綠）。
- 建議：(a) 測試在比對前 `git fetch origin refs/remotes/origin/v3:refs/remotes/origin/v3`；或 (b) abf-fast-suite 鏡像把 worktree 的 refs/remotes/origin/v3 帶過去；或 (c) 以 first-parent 上第一個 "Merge pull request" 為底。需 lead 裁決，違反「照 origin/v3...HEAD」裁決所以我沒擅自做。

## executor 第二輪（裁決 a）
- test_no_schema_change 比對前先 fetch origin：先試 +refs/remotes/origin/v3（鏡像 clone 的 origin 是 worktree，其 v3 過舊），失敗再 fetch v3；兩者皆失敗則 skip 並印原因。斷言不變。
- 反證：test_schema_pin_still_catches_branch_change（三種路徑）證明分支真改 store.py/schema.sql/migrations 時 helper 非空。
- 鏡像單檔 25 passed。

## 修正輪：TC-008 實跑輸出（HEAD 349641d0，abf-fast-suite 鏡像）
反證測試 `test_schema_pin_still_catches_branch_change`（參數 schema.sql／store.py／migrations；每個參數在暫時 repo 的分支上改該檔，斷言 `schema_diff` 非空，故分支真改 schema 時 `test_no_schema_change` 會紅）：
```
$ abf-fast-suite <wt> --pytest tests/test_mcp_launch_pipeline.py::test_schema_pin_still_catches_branch_change
...                                                                      [100%]
3 passed, 5 warnings in 0.39s
$ abf-fast-suite <wt> --pytest tests/test_mcp_launch_pipeline.py::test_no_schema_change
.                                                                        [100%]
1 passed in 0.20s
```
