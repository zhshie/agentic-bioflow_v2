---
id: backfill-preview-summary
title: runs offer-cleanup 預覽時的總結行不再寫「已提出 0 張」
tier: B
kinds: backend
lane: L-backfill-fix
base: v3
source: cloud-cleanup-backfill（#242）verifier 的 needsHuman：「預覽時最後一行會寫『已提出 0 張、略過 N 個』，即使沒有真的提出」；developer-agent 10-27 裁決改字。
---

# backfill-preview-summary

> 終端機指令 `abf-platform runs offer-cleanup` 不加 `--apply` 時只預覽，但最後一行總結仍印「已提出 0 張、略過 N 個」，讀起來像真的送了東西。改成預覽專用的一句。B 級（使用者看得到的終端機文字），非網頁畫面，verifier 通過＋CI 綠自合。

## 目標
預覽（沒有 `--apply`，或同時給 `--list`）時最後一行是 `預覽：會提出 N 張、略過 M 個；要真的提出請加 --apply (preview: would offer N, skip M; add --apply to offer)`，N＝這次會提出的 run 數。加 `--apply` 時最後一行不變：`已提出 N 張、略過 M 個 (offered N, skipped M)`。

## 維護者原話（verifier 出題用）
- 「中文顯示不能口語」（2026-10-27，web-wording-sweep 的原話；本句沿用正式用字）。
- 他 10-21 定：使用者看得到的行為改變要能說「以前…以後…」。以前：預覽最後一行寫「已提出 0 張」；以後：寫「預覽：會提出 N 張…要真的提出請加 --apply」。

## 範圍：檔案
- `platform/abf_platform/cli.py`：`cmd_runs_offer_cleanup` 的最後一行（約 494 行）依是否預覽印兩種句子。預覽時的 N 用回傳中「會提出」的筆數（`actions.offer_cleanups` 的回傳若沒有該欄，就在 cli 端數 `would offer` 的列，不改 actions）。
- `platform/tests/test_cleanup_backfill.py`：第 137 行附近預覽情境的總結行斷言改成新句子（准改，本任務本來就是改這句）；另加一條：預覽時輸出不得含「已提出」。
- `docs/TESTING.md`：cloud-cleanup-backfill 那節第 2 步補一句「最後一行以『預覽：』開頭」。
- `specs/backfill-preview-summary/ledger.md`
- 不准動：`actions/__init__.py`、`receiver.py`、其他測試檔。

## 作法（決定，不是程式碼）
1. 預覽與否的判斷跟現在決定「會提出／已提出」那兩行用的是同一個條件，不另寫一份。
2. 兩種總結句都中英並列，跟檔內其他句子同格式。

## 失敗先行測試
- T1：`--all`（無 `--apply`），有 2 個可提、1 個略過 → 最後一行＝`預覽：會提出 2 張、略過 1 個；要真的提出請加 --apply (preview: would offer 2, skip 1; add --apply to offer)`；輸出沒有「已提出」。
- T2：`--all --apply` → 最後一行仍是 `已提出 2 張、略過 1 個 (offered 2, skipped 1)`（既有斷言第 89 行不動）。
- T3：`--list --apply` → 視為預覽（既有行為），最後一行是預覽句。

## 完成標準（done when）
- T1–T3 綠；WSL 全套綠（本機分片逾時若在 origin/v3 也逾時，記 ledger、回 DONE，不改 tests/platform_test.sh）。
- `git diff --name-only` 只含上列 4 個檔＋specs 目錄。

## 環境事實
- 指令在 `platform/abf_platform/cli.py` `cmd_runs_offer_cleanup`（#242 新增）；測試在 `platform/tests/test_cleanup_backfill.py`。
- 禁字守門：`test_confirm_page.py` TC-G02 禁 `--yes` 等字；新句子只提 `--apply`，不得出現 `--yes`／`--force`。

## 不做
- 不改每列（`會提出申請`／`已提出申請`／`略過`）的句子。
- 不改 `actions.offer_cleanups` 的回傳形狀。

## 裁決
1. 只改總結行一句；既有斷言只准改預覽情境那一條（約 137 行）。

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
