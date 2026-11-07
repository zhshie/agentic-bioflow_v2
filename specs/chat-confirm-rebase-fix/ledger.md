# PR #376 rebase 並修好 test_tcm_47 基準 progress ledger

## 進度 (executor)
- TC-001: origin/feat/mcp-chat-confirm-v5 (7671b877) 已含 origin/v3 最新 (87107ae9)；merge 無衝突，非 force。
- TC-005 失敗訊息：test_tcm_47 紅，只在結構雜湊 (34670e36... vs b401f98b...)。路由清單與表清單已一致 (BASE_ROUTES 已含 /settings/personal)。
- 實際差異只有一項：jobs.kind 的 CHECK 多了 lint_pipeline（v3 的 017c2a-validate-lint, commit b1dadfe9）。把它移除後雜湊正好等於舊基準 b401f98b...。
- step_mode/dev_mode 不在此測試的 sqlite_master 雜湊裡，計畫說的三項與事實不符。依 TC-005 規則停下回報，未更新基準。
- 狀態：BLOCKED，等 developer-agent 裁決是否把基準改成含 lint_pipeline 的新雜湊 34670e36fdb2ae46813b6f97cc7570f01cf5ddc347a139a84c7f2c762335652a。
