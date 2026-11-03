# Slurm 主任務 NODE_FAIL 等結束狀態要顯示為失敗 progress ledger

- [x] 站台端：fetch_run_records 加 slurm_job_id，無完成行時問 squeue 再 sacct（TC-007..011, 020）
- [x] 平台端：jobs.head_state / ask_head_state / clean_scheduler；failures.with_head_state；get_run 與 list_runs 疊加；build._predecessor 放行（TC-001..006, 012..019, 021..023）
- [x] docs/PLATFORM.md、PITFALLS.md（#59）、TESTING.md 手動步驟
- [ ] TODO（人工）：在 nano4 手動驗收（docs/TESTING.md 新段）；本任務沒有碰真實站台
- 備註：tests/constitution_scope_test.sh 在 WSL 內為紅，屬環境問題，與本任務無關。
- 備註：TC-012 與 v3 的 failures 測試矛盾（見 decisions.tsv），保留 v3 行為。
- 證據：`git diff --stat` 見 commit；sacct 在 origin/v3 尚無使用。
- [x] 裁決 O（對抗審）：限流算任何狀態且與排程同一交易、slurm_job_id 只走 head-state 路徑、_fetches_of 先依 run 過濾再取 20 筆、截斷的 log 不算完成行（TC-026..029）
- [x] 對抗審第二輪（11-04）：續跑後同資料夾的 .nextflow.log 是續跑的，不能遮住第一次嘗試的 NODE_FAIL；完成行要每個「看得出真的跑過」的 log 都有才不問排程器（fetch.py）。平台端 head_state 仍只取最新讀回（TC-014 d 釘住），因站台不再回 None 而不會翻回 lost。
