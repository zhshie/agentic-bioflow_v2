# 下游階段：Studios 開新分頁版（網址只在查詢字串，不儲存） progress ledger

- [x] web_downstream.py、web_board.py／web.py 接線、test_web_downstream.py 47 個測試通過；不儲存、不新增路由／動作／資料表；STYLE／CSP 未動。
- 截圖（TC-017/018）由驗收者以 Playwright 產生，executor 未做。WSL 內 constitution_scope_test.sh 若紅屬環境問題，以 CI 為準。
- 範圍外小改：test_web_wording_sweep.py（表加入、數量 8 改 9，只增不減）。
