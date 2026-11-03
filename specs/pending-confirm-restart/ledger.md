# 平台重啟後待確認連結仍可確認 progress ledger

- [x] 新測試 `platform/tests/test_pending_confirm_restart.py`（TC-001～TC-020，13 個測試函式）。
- 結論：**v3 沒有重啟失效的 bug**。13 個測試在未改任何 `platform/abf_platform/` 檔案下全綠，只保留為回歸測試；`git diff --stat` 只有測試、ledger、decisions.tsv。
- 推論：11-01 的連結失效，最可能是（1）重啟花了超過 10 分鐘，依設計逾時；或（2）升版腳本讓新行程指向不同的資料資料夾／`--state`／`--tokens`（TC-017 描述此現象：新金鑰、新資料庫、顯示「無此申請」）。請 developer-agent 到正式機核對升版腳本實際使用的資料資料夾（不讀金鑰內容）。
- 註：測試中移動假時鐘時需讓代理的 last_seen 跟上（否則佇列以「代理離線」拒絕，與重啟無關）。
- WSL 內 `constitution_scope_test.sh` 若紅，屬 worktree 用 Windows git 建立的環境問題，以 CI 為準；落地前 `git merge origin/v3`。
