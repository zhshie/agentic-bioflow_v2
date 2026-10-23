---
id: catalogue-optional
title: 模組目錄快照記下輸入是否可省略（optional），讓 017c 的未接輸入能分輕重
tier: A
kinds: backend
lane: L11-catalogue
base: v3
---

# catalogue-optional

> 本檔由 developer-agent 寫（2026-10-24），`/supervise` 複製進 worktree。**只處理本任務**。

## 目標
nf-core 模組的 `meta.yml` 在輸入記錄上可以標 `optional: true`。017a 的快照（`platform/abf_platform/data/nf-core-modules.json`，由 `catalogue.flatten` 攤平）目前丟掉了這個欄位，所以 017c 只能把所有「沒接的輸入」都當 warning。本任務讓攤平後的每筆輸入記錄帶 `optional`（布林，meta.yml 沒寫就是 `false`），並以同一個上游 sha（5ed90b42…）重產快照。

## 維護者原話（verifier 出題用）
- 無原話；來源是 017c 計畫的待決事項「必填輸入目前只能是 warning；要變成錯誤，須另開 A 級任務讓快照帶 optional」。

## 範圍：檔案
- `platform/abf_platform/catalogue.py`（`flatten`／`_entry` 保留 `optional`）
- `platform/abf_platform/data/nf-core-modules.json`（用 `python -m abf_platform.catalogue snapshot --modules <checkout> --sha 5ed90b42e78410e7411e9c6bdfeff33226d6c58e --out ...` 重產；developer-agent 會在派工後提供重產好的檔案，若 executor 環境無法 clone 上游，回報 BLOCKED 等 developer-agent 產生）
- `platform/tests/test_catalogue.py`
- `docs/PLATFORM.md`（模組目錄一節補一句 optional 的意義）
- `specs/catalogue-optional/ledger.md`

## 失敗先行測試
- `test_flatten_keeps_optional_true`：meta.yml 輸入記錄有 `optional: true` → 攤平後該記錄 `optional is True`。
- `test_flatten_defaults_optional_false`：沒寫 → `False`。
- `test_snapshot_has_optional_on_every_input_record`：真快照每筆輸入記錄都有布林 `optional`。
- `test_snapshot_marks_known_optional_input`：挑一個上游 meta.yml 已知標 optional 的模組輸入（executor 從 5ed90b42 的 meta.yml 找一個，寫進測試並在 ledger 記出處路徑），斷言為 True。
- 既有 017a 測試（dumps 逐位元、sha、count）照舊通過；`test_dumps_matches_file` 類測試在重產後仍成立。

## 完成標準
全套綠。

## 不做
- 不改 017c 的 OPEN_INPUT 判定（另一件）。不改輸出記錄。不換上游 sha。

## 裁決（2026-10-24，developer-agent）
1. 不需要 migration（快照是檔案，不進資料庫）。
2. 017c 若先合併：本件合併後另開 A 級小件把 OPEN_INPUT 在 `optional: false` 時升為 error。

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
