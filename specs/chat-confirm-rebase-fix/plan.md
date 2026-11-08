---
id: chat-confirm-rebase-fix
title: PR #376（憲法 7.0.0，CHAT 通道）rebase 到最新 v3 並修好被舊結構雜湊卡住的測試
tier: A
kinds: backend
lane: L-chat-confirm-fix
base: v3
risk: L
serves: M1-CHATCONFIRM
---

# chat-confirm-rebase-fix

## 目標
PR #376（分支見 `gh pr view 376 -R zhshie/agentic-bioflow_v2`）把憲法升到 7.0.0（新增第四種人的同意通道 CHAT）。維護者 11-07 已當面「同意 7.0.0」。它現在卡在 CI：`shard 4/4` 的 `test_chat_confirm.py::test_tcm_47_no_new_column_no_new_table` 寫死的基準結構雜湊與路由，被 v3 後來加入的 `/settings/personal` 路由與 `step_mode`、`dev_mode` 欄位弄舊。本件 rebase 到最新 v3、重算該測試的基準，讓 #376 的 CI 變綠、可合併。**不改 CHAT 通道的行為與憲法條文。**
意義：憲法 8.0.0（預算內免逐次確認，`dev-mode-launch`）疊在 7.0.0 上，#376 不合併，維護者最基本要求（AI 免逐次確認跑完全程）就不能開工。

## 維護者原話（verifier 出題用）
> 「憲法 7.0.0（PR #376）…最終條文你同意嗎？」→「同意 7.0.0」（2026-11-07）

## 裁決
- 本件是 A 級（碰憲法）但維護者已同意條文；只動測試的基準值與 rebase 衝突，不改條文、不改 CHAT 行為。
- gitleaks 與 pip-audit 在 v3 本身也紅（計畫撰寫者查證，非 #376 造成），不是本件範圍；若它們是必要檢查而擋合併，回報 lead，不要放寬檢查。
- 憲法版本與指紋釘測試（`test_tcm_*` 內的憲法版本檢查）要維持：版本仍是 7.0.0。

## 範圍：檔案
只准改：PR #376 分支上與 rebase 衝突的檔；`platform/tests/test_chat_confirm.py`（`test_tcm_47` 的基準結構雜湊與路由清單，只准把新增的 `/settings/personal` 路由與 `step_mode`、`dev_mode` 欄位納入基準）。其餘一律不動。

## 作法
1. `git fetch origin v3`，在 #376 的分支上 rebase（衝突逐檔解，保留 v3 的新內容與 #376 的 CHAT 新增）。
2. 跑 `test_tcm_47`：讀失敗訊息，確認差異只來自 v3 新增的 `/settings/personal`、`step_mode`、`dev_mode`；把基準更新為包含它們，並在 ledger 逐項列出新增了什麼。
3. 全套 `bash tests/run_all.sh`（WSL）全綠。
4. 不用 `--force`：rebase 後以 `git merge origin/v3` 方式整合（先問才可 force），推到 PR 分支。

## 失敗先行測試
- `test_tcm_47` 目前紅（已知）。完成後綠，且「真的新增表或欄位」時仍會紅（ledger 附證明：暫時加一個假欄位，測試轉紅，再移除）。

## 完成標準（done when）
- #376 的必要檢查（tests shard 1–4）全綠；ledger 列出基準更新的差異清單。
- 憲法版本仍為 7.0.0，CHAT 通道行為測試無一條被改弱。
- gitleaks／pip-audit 若仍紅，ledger 說明是 v3 既有問題。

## 環境事實
- v3 憲法目前 6.2.0；#376 尚未合併。WSL 跑測試；從中文路徑 cwd 呼叫 wsl 會失敗（見 repo CLAUDE.md）。
- 計畫撰寫者查證：#376 為正式 PR（非 draft），MERGEABLE。

## 不做
- 不改憲法條文、不改 CHAT 行為、不放寬任何安全測試、不處理 8.0.0（另件 `dev-mode-launch`）。

## 裁決（lead，2026-11-08，回應 executor 的 BLOCKED／續作）
1. **核可更新基準**：BASE_SCHEMA_SHA256 改成 34670e36fdb2ae46813b6f97cc7570f01cf5ddc347a139a84c7f2c762335652a（唯一差異＝jobs.kind CHECK 多了 lint_pipeline，來自已合併的 017c2a），BASE_ROUTES 加入 /run/log（來自已合併的 web-run-tasks-log）。這是跟著 v3 已合併的事實更新基準，不是放寬測試；TC-008 的「加假欄位會轉紅」證明測試仍然咬得住。除這兩項外不得改任何基準或斷言。
2. **shard_6 逼近 300 秒**：不是本件程式問題。機器閒時單跑 280 秒，視為通過；若 CI 上逾時，gh run rerun --failed 一次即可，不要為此改逾時上限。
3. 本件不碰 .github/、gitleaks、pip-audit。

## 裁決（lead，2026-11-08 10:30，回應第 3 次退回：修正已綠但未推）
4. **先合入再推**：PR #376 分支（feat/chat-confirm-rebase-fix 的遠端）已前進到 aed240d9。在 worktree 先 `git fetch` 後 `git merge origin/feat/chat-confirm-rebase-fix`（不 rebase、不 force、不重寫歷史），衝突只解「基準常數」那幾行，其餘一律保留遠端版本；合入後重跑全套，全綠才推。
5. **「計畫差異說法」**：以本計畫裁決 1 為準（只改兩個基準＋/run/log），PR 描述照寫，不另發明說法。
6. **v3 上的 gitleaks／pip-audit 紅燈不屬本件**：另件處理，本件不碰也不因它退回；tests 工作流綠即可。
7. 不得放寬任何斷言、不得改憲法條文。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
