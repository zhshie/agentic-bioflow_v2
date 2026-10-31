# run_outputs 錯誤答案不再永久沿用（連線恢復後重新列出）；.html 結果檔改給下載連結 progress ledger

- 完成：run_outputs 錯誤工作 ≥30 秒重排（actions._listing_is_error、jobs.LISTING_ERROR_RETRY_SECONDS）；read_run_file 的 .html/.htm 走 binary（_READ_HTML）；mcp 描述、SKILL.md、PLATFORM.md、TESTING.md 只增不改；新測試 platform/tests/test_mcp_run_file_live_fixes.py（RED 先行）。
- 被觸及的既有斷言：無修改（test_ro05*、tc013/tc015、test_tc020_021_028 等皆未改）。web*.py、abf_station/、store.py、run_file() 無改動。
- 環境註記：WSL 內 constitution_scope_test/git ls-files 類失敗為 worktree 環境問題（裁決 4）。
