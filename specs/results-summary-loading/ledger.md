# 結果頁摘要卡讀取中顯示「讀取中」 progress ledger

## 執行紀錄
- [x] `web_board.py`：`_report_cell` 加 `reading` 參數，輸出分頁、第一層、state=loading 時寫 `⟳ 讀取中`；`_results_body` 傳 `tab == "outputs"`。
- [x] 新測試 `test_results_summary_loading.py`（TC-001~022、029）。
- [x] 既有測試預期改兩處：`test_ro01_results_stage_has_cards_and_tabs`、`test_ro10_english`（報告／MultiQC 報告改讀取中，指標／全部下載不變；沒刪案例）。
- 異動檔：web_board.py、test_results_summary_loading.py、test_web_results_outputs.py、ledger.md；沒有 web.py／actions。
- [x] 整套第一次紅兩支：test_scope tc070（新測試檔缺標頭，已補）、test_clean_page 的 succeeded 板雜湊（計畫沒列；成功板預設開輸出分頁、讀取中文字改變，重新釘兩個 succeeded 雜湊，failed／running 不動）。
