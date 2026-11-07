# PR #376 rebase 並修好 test_tcm_47 基準 progress ledger

## 進度 (executor)
- TC-001: origin/feat/mcp-chat-confirm-v5 (7671b877) 已含 origin/v3 最新 (87107ae9)；merge 無衝突，非 force。
- TC-005 失敗訊息：test_tcm_47 紅，只在結構雜湊 (34670e36... vs b401f98b...)。路由清單與表清單已一致 (BASE_ROUTES 已含 /settings/personal)。
- 實際差異只有一項：jobs.kind 的 CHECK 多了 lint_pipeline（v3 的 017c2a-validate-lint, commit b1dadfe9）。把它移除後雜湊正好等於舊基準 b401f98b...。
- step_mode/dev_mode 不在此測試的 sqlite_master 雜湊裡，計畫說的三項與事實不符。依 TC-005 規則停下回報，未更新基準。
- 狀態：BLOCKED，等 developer-agent 裁決是否把基準改成含 lint_pipeline 的新雜湊 34670e36fdb2ae46813b6f97cc7570f01cf5ddc347a139a84c7f2c762335652a。

## 續作 (executor, 依 dev-worker 裁決)
- 基準更新差異清單（只有一項）：jobs.kind CHECK 加 'lint_pipeline'（v3 017c2a-validate-lint）。BASE_SCHEMA_SHA256 b401f98b... -> 34670e36fdb2ae46813b6f97cc7570f01cf5ddc347a139a84c7f2c762335652a。路由清單、表清單、step_mode/dev_mode 均無需改。
- TC-001/003: origin/v3 (87107ae9) 已在 HEAD 歷史內，以 merge 整合，沒有 force。
- TC-006: 更新後 test_chat_confirm.py 38 passed。
- TC-008 證明：暫時在 store.py confirmations 加假欄位 fake_col，test_tcm_47 轉紅；git checkout 還原後 38 passed 全綠；未留下假欄位。
- TC-023: 不需要 migration；本件只改測試基準值，沒有改資料結構。
- TC-014: 未碰 gitleaks/pip-audit 或 .github；若仍紅是 v3 既有問題（依計畫查證）。
