---
id: init-workspace-hermetic
title: init_workspace_test 的「no run area known」案例不再受本機部署設定影響
tier: A
kinds: backend
lane: L9-tests
base: v3
---

# init-workspace-hermetic

> 本檔由 developer-agent 寫（2026-10-24），`/supervise` 複製進 worktree。**只處理本任務**。

## 目標
`tests/init_workspace_test.sh` 第 267-268 行「site side with no run area known fails clearly, not silently」在任何機器上都得到預期的 rc 2，不因開發機上真實的部署設定（例如 `~/.config/agentic-bioflow/root` 指到一個 `storage_root: /work/...` 的部署）而變成 rc 1（`mkdir: cannot create directory '/work'`）。

## 維護者原話（verifier 出題用）
- 無原話；2026-10-23～24 桌機 WSL 上每一輪全套都只剩這一條紅，三個任務因此被擋成 BLOCKED。CI（GitHub Actions）上是綠的。

## 範圍：檔案
- `tests/init_workspace_test.sh`（只改這一個案例的環境隔離，必要時加一個共用的隔離 helper）
- `specs/init-workspace-hermetic/ledger.md`

## 作法
1. 先查 `scripts/settings.sh`（`setting()` 約第 586 行、設定檔位置約第 318 行）`storage_root` 從哪裡讀：部署根指標檔（`~/.config/agentic-bioflow/root` 或 XDG 路徑）、環境變數、或內建預設。
2. 讓這個案例在乾淨環境跑：`env -u LAB_RUNS_DIR HOME="$TMP/emptyhome" XDG_CONFIG_HOME="$TMP/emptyhome/.config"`，再加上 settings.sh 用來找部署設定的變數（指向不存在的路徑）。保留 rc 2 與 "no run area known" 的斷言。
3. 若查出 `settings.sh` 對 `storage_root` 有寫死的預設（與 init_workspace.sh「There is no default beyond that, deliberately」矛盾），停下回報 BLOCKED，不改腳本。

## 失敗先行測試
- 先證明現況會紅：在測試裡（或 ledger 記錄）以「HOME 指向一個含部署指標、storage_root 為不可寫路徑」的暫存家目錄跑舊寫法 → rc 1；改後同情境 → rc 2。把這個「有部署設定的家目錄」情境做成新案例 `site side ignores the developer's own deployment when testing`，斷言 rc 2。

## 完成標準
該檔所有案例綠；全套綠（這次不可以再有那一條紅）。

## 不做
- 不改 `scripts/init_workspace.sh`、`scripts/settings.sh`（除非裁決另外允許）。

## 裁決（2026-10-24，developer-agent）
1. 不需要 migration。

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
