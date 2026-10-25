---
id: pipefail-grep-q-sweep
title: 其他測試腳本裡同一種時好時壞（pipefail＋grep -q）一次掃掉
tier: A
kinds: backend
lane: L-flake
base: v3，在 constitution-scope-flake（#231）合併之後
source: #231 verifier 找到的根因；developer-agent 2026-10-25 掃 origin/v3 tests/：至少 20 支有 `set -o pipefail` 又有 `| grep -q`
---

# pipefail-grep-q-sweep

## 目標
`set -o pipefail` 底下寫 `printf … | grep -q 字串`：grep 一找到就先結束，前面的 printf／cat 還在寫就收到 Broken pipe，pipefail 把整條管線算失敗，於是「字明明在卻判找不到」。這在 #231 被證實是 constitution_scope_test 時好時壞的根因（壓測 24000 次，舊寫法 10 次誤判、新寫法 0 次）。同一寫法還在其他至少 19 支測試裡（含 jev_test.sh，今天也有一次不明的 1 項紅）。一次改掉，並加一支守門測試防止再寫回來。對使用者：PR 不再莫名其妙卡住。

## 維護者原話（verifier 出題用）
- 「全綠才准停」；run_all：「Fix the test, or add one line per file to tests/quarantine.txt」——本任務一律「Fix the test」，不加 quarantine。

## 範圍：檔案
- `tests/*.sh` 中同時有 `pipefail` 與「管線接 `grep` 且帶 `-q`（含 `-qF`、`-iq`、`-Eq`、`-F -q` 這類寫法）」的檔：只改那些行。
- 新增 `tests/no_pipefail_grep_q_test.sh`（守門；檔首照慣例寫為什麼）。
- `specs/pipefail-grep-q-sweep/ledger.md`
- **不准動**：`tests/run_all.sh`、`tests/quarantine.txt`、`hooks/*`、`.github/*`、憲法、任何非 tests/ 的檔。

## 作法（決定）
1. 每一處 `X | grep -q… PATTERN` 改成 `X | grep …（去掉 q）PATTERN >/dev/null`，其他旗標、樣式、比對字串一字不改。`if`／`&&`／`||` 的邏輯不變。
2. 只改「管線右邊是 grep -q」的行；`grep -q PATTERN FILE`（直接讀檔、沒有管線）不用改。
3. 守門測試：掃 `tests/*.sh`（排除它自己），凡是檔內有 `pipefail` 的，就不得出現「`|` 之後接 `grep` 且旗標含 `q`」；樣式要涵蓋 `grep -q`、`grep -qF`、`grep -iq`、`grep -F -q`、`grep -E -q`。另加兩條自我測試：放一個含違規寫法的暫存檔它要紅、乾淨的要綠。
4. 每支改過的腳本在 WSL 各跑一次要綠；ledger 列出改了哪些檔、各幾處。

## 失敗先行測試
- 守門測試在現在的 v3 上要紅（列出違規檔）；改完全綠。
- 壓測一支代表性的檔（例：platform_direction_docs_test.sh，15 處）：8 份同時、各跑 200 次，改前若能重現誤判就貼數字，改後 0 次。

## 完成標準（done when）
- 守門測試綠；所有改過的腳本單跑綠；全套綠。
- 既有斷言的比對字串與預期值一個都沒動（閱卷看 diff）。

## 環境事實
- 根因與壓測方法見 #231 的 PR 說明與 `specs/constitution-scope-flake/ledger.md`。

## 不做
- 不改 run_all 的 FLAKY 判定、不加 quarantine、不加重試。

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
