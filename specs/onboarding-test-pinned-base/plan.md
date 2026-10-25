---
id: onboarding-test-pinned-base
tier: A
kinds: backend
lane: L-onboard-fix
---
# 移除 test_onboarding_doc.py 釘死 6061925 的兩個一次性檢查

## 目標
`platform/tests/test_onboarding_doc.py` 有兩個測試拿固定提交 `BASE = "6061925"`（:14）比對：
- `test_tc047_tc051_other_docs_untouched`（:329-332）：要求四份文件與 6061925 沒差異。#209／#210／#213 合併後 v3 本身就不符；CI 只因淺層 clone 解析不到 6061925 而跳過，完整 clone 上 v3 是紅的（前端 session 882cfe 回報，developer-agent 已用 `git diff --stat 6061925 origin/v3 -- docs/…` 證實：2 檔有差異）。
- `test_tc045_tc046_readme_pointer`（:316-326）的後半：拿 6061925 的 README 逐行比對。README 之後一改就紅。
這兩個是 #211 那次 PR 才需要的「沒動到別的檔」檢查，合併後就不該留在全套裡（同 nano4-site-config 裁決二 10 刪掉 TC-097 的先例）。

## 作法
1. 刪掉 `test_tc047_tc051_other_docs_untouched` 整個函式。
2. `test_tc045_tc046_readme_pointer` 只保留前半（README 有且只有一行指向 docs/ONBOARDING.md、在 docs/PITFALLS.md 那行之前、前後各一空行）；刪掉 `base = _git(...)` 起的三行。
3. 若 `BASE` 與 `_git` 不再有人用就一起刪（`subprocess` import 同理）。
4. ledger 記：完整 clone 上修正前 `test_tc047…` 紅、修正後全檔綠的輸出。

## 失敗先行測試
- 在完整 clone（有 6061925）上跑 `pytest platform/tests/test_onboarding_doc.py`：修正前 test_tc047 紅（證明問題存在）；修正後全綠。這就是 RED→GREEN 證據，不需新增測試檔。

## 範圍（只准改）
- `platform/tests/test_onboarding_doc.py`
- `specs/onboarding-test-pinned-base/ledger.md`

## 不做
- 不改 docs/ 任何檔、不改 ONBOARDING.md、不改其他測試。

## 完成標準
- 完整 clone 上 `test_onboarding_doc.py` 全綠；全套 `tests/run_all.sh` 綠。
- 檔內不再出現 `6061925`。

## 維護者原話
（無；A 級，由前端 session 回報。）

## 環境事實
- 行號以 origin/v3 為準：BASE :14、_git :312、test_tc045_tc046 :316-326、test_tc047_tc051 :329-332。

## 裁決（2026-10-25 07:10，developer-agent）
1. 刪除一次性檢查，不改成「比對本 PR 自己的 diff」（測試在合併後跑在任何分支上，沒有可靠的「本 PR」可比）。

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
