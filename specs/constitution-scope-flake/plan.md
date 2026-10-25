---
id: constitution-scope-flake
title: constitution_scope_test.sh 在 CI 時好時壞：找出原因並修好
tier: A
kinds: backend
lane: L-flake
base: v3（origin/v3，2026-10-25）
source: developer-agent；CI 紀錄 #219（10-25 上午）與 #228 run 40170104859 attempt 1（06:46 UTC）
---

# constitution-scope-flake

## 目標
`tests/constitution_scope_test.sh` 在 GitHub CI 上今天兩次「第一次紅、重跑綠」，run_all 把它判成 FLAKY 並讓整個 job 失敗，PR 因此卡住、要人手動重跑。找出不確定的來源並修掉，讓它每次結果一樣。對使用者：PR 不再莫名其妙卡住。

## 維護者原話（verifier 出題用）
- 「全綠才准停」（工作區開發規則；CI `run_all` 綠才能合是 ruleset）。
- run_all 的訊息本身：「Fix the test, or add one line per file to tests/quarantine.txt」——本任務選「Fix the test」，**不准**加進 quarantine。

## 範圍：檔案
- `tests/constitution_scope_test.sh`
- `specs/constitution-scope-flake/ledger.md`
- 若根因在 run_all 的輸出截斷或共用暫存，才可另加 `tests/run_all.sh`，並在 ledger 寫明理由（不改 `--retry-failed-once` 與 FLAKY 判定的語意）。

## 作法（決定）
1. **先重現、再改**：在 WSL 把這支測試連跑 50 次（`for i in $(seq 50); do bash tests/constitution_scope_test.sh >/tmp/cs.$i 2>&1 || echo FAIL $i; done`），另在模擬 CI 的條件下跑：`git clone --depth 1` 的淺層副本、沒有 `main` ref、`TMPDIR` 換成另一個資料夾、同時跑兩份。記下哪一種條件會紅、紅在哪一條（貼 ledger）。
2. 已知可疑點（只是線索，以實測為準）：檔內 `mkclone`（約 :152-176）在 `mktemp -d` 底下做淺層 clone、刪 `main` ref；`clone.err` 只印前 400 字；CI 的 run_all 只印失敗檔的最後幾行，所以第一次失敗的那一條沒被印出來。
3. 修法要對準根因（例如固定 clone 來源、等待／檢查 clone 完成、不依賴共用暫存、不依賴時間）。**禁止**：加重試迴圈掩蓋、放寬斷言、跳過案例、加 quarantine。
4. 讓失敗時印出是哪一條（例如失敗的 `bad` 行也寫到 stderr 開頭），下次再紅能直接看到。

## 失敗先行測試
- 能在本機穩定重現紅的條件 → 先把那個條件寫成檔內一個案例或 ledger 裡的重現指令；修好後 50 次連跑 0 紅。
- 若 50 次＋各種模擬條件都重現不了：在 ledger 寫明試過的條件與結果，改做第 4 條（讓下次失敗印出原因），並回報 BLOCKED 讓 developer-agent 決定。

## 完成標準（done when）
- 50 次連跑 0 紅（貼 ledger），模擬 CI 條件下也 0 紅。
- 檔內既有案例一條不少、斷言不放寬。
- 全套綠。

## 環境事實
- CI 用 `actions/checkout` 的淺層 clone；本機 worktree 是完整 clone。
- run_all `--retry-failed-once`：第一次紅、重跑綠＝FLAKY，未列入 quarantine 就讓 job 失敗。

## 不做
- 不加 quarantine、不改 run_all 的 FLAKY 判定。
- 不改憲法本文、不改 PINNED_SN_SHA256。

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
