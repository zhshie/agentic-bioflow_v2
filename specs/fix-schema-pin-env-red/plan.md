---
id: fix-schema-pin-env-red
title: 修 test_no_schema_change 的環境誤報（改比分支自己的改動，不比本機 origin/v3 的快照）
tier: C
kinds: backend
lane: schema-pin
base: v3
risk: M
---

# fix-schema-pin-env-red

## 目標
`platform/tests/test_mcp_launch_pipeline.py::test_no_schema_change`（TC-032）現在用 `git diff --stat origin/v3 -- migrations store.py schema.sql`。worktree 裡的 `origin/v3` 是本機快照；只要 v3 在分支切出後又改過 `store.py`（例如費用頁 #377／#378），這條就會在「沒碰 schema 的分支」上誤紅。結果：昨晚三個已經寫完、測試全綠的任務（web-nano4-fastq-upload、web-journey-test、lawyer-questions-doc）因這一條擋在最後一步，車道全閒。對使用者的意義：開發循環不再被一條環境誤報卡死。

## 維護者原話（verifier 出題用）
- 「以後開發務必將工作排到最滿」（10-24）；「在還沒到規定 token 上限，都將開發進程拉到最趕」。這一條誤報讓 6 條車道閒置，違反此原話。
- TC-032 的原意（launch_pipeline 規格）：這個功能不准動資料庫 schema。保護力道不得變弱。

## 裁決
- lead 2026-11-07：允許修改這條被釘住的測試，理由是只改「比對的基準」，不放寬「store.py／migrations／schema.sql 不准被這個分支改動」這個斷言。verifier 必須確認：分支若真的改了這三處，測試仍然紅。
- 作法定案：基準改成 `git diff --stat origin/v3...HEAD`（三個點＝與 merge-base 比，只看分支自己的改動），不再受 origin/v3 快照新舊影響。
- lead 2026-11-07（兩次被當孤兒的原因）：不是本任務的問題。supervise 的 Setup 小幫手（Haiku）漏跑用量讀取指令、回報 usage -1，閘門 fail closed 判 `SKIPPED(usage)`，worker 便 `release --outcome pause`，任務變成沒有 owner 的孤兒。已修在 supervise.js（`ensureUsage` 重讀）與 dev-worker.md（SKIPPED(usage) 遇 unknown/stale 且 `ready` 的 pacing 正常時先重跑一次）。本任務計畫不必改，直接重派即可。

## 範圍：檔案
- `platform/tests/test_mcp_launch_pipeline.py`（只改 `test_no_schema_change`）
- `specs/fix-schema-pin-env-red/ledger.md`（新，executor 帳本）

## 作法
1. 該測試的 `git diff` 改成三點比對 `origin/v3...HEAD`；cwd 與路徑參數不變。
2. 補一條反證測試（同檔）：在暫時 git repo 裡製造「分支改了 schema.sql」，斷言 helper 回非空；製造「只有 base 前進、分支沒動」，斷言回空。可把比對抽成小 helper 函式讓兩條共用。
3. 不動其他 `test_no_schema_change` 同名測試（test_k8s_ce、test_web_actions 等是不同檢查）。

## 失敗先行測試
- `test_schema_pin_ignores_base_advance`：base 前進、分支沒動 → 回空（舊寫法會紅）。
- `test_schema_pin_still_catches_branch_change`：分支改 schema.sql → 回非空（防止放寬）。

## 完成標準（done when）
- 兩條新測試綠，原 TC-032 在落後 v3 的 worktree 也綠。
- 全套 `bash tests/run_all.sh` 綠。
- ledger 附：分支真改 schema.sql 時測試會紅的實跑輸出。

## 環境事實
- 三個被擋任務的失敗訊息：`test_no_schema_change fails because mirror local v3 lags origin/v3`（佇列 decisions `web-nano4-fastq-upload-fail-1`、`web-journey-test-fail-2`、`lawyer-questions-doc-fail-1`）。
- 測試位於 origin/v3 的 `platform/tests/test_mcp_launch_pipeline.py` 第 283 行附近，註解寫明該釘點曾因 store.py 變動「搬過一次」，是同一類脆弱性。

## 不做
- 不改 `store.py`、`migrations/`、`schema.sql`。
- 不刪這條測試，不改成永遠綠。
- 不動 CI 設定。

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
