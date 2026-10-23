---
id: failure-seqera
title: 失敗 run 照 Seqera 模式帶出失敗 task／exit code／日誌＋Resume／Relaunch（唯讀，不分類）
tier: B
kinds: backend
lane: L7-web-redesign
base: v3
source: 維護者 10-23 20:15（取代 failure-cause 的四類設計）
---

# failure-seqera

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree。**只處理本任務**。取代舊任務 failure-cause（分支 feat/failure-cause 作廢，不要參考它）。

## 目標
失敗（或失聯）的分析，平台照 Seqera Platform 的做法把事實原樣帶出：哪個 task 失敗、exit code、錯誤訊息、日誌，以及 Seqera run 選單上的兩個動作 Resume／Relaunch。**不分類失敗原因、不替使用者挑動作。**純讀取，不送出任何東西。

## 維護者原話（verifier 出題用）
- 「分成四類 改成 跟Seqera platform一樣的模式，不要自己定義」（10-23 20:15）
- 「失敗原因直接參考Seqera platform架構。」（10-23）
- 「介面上不要有AI太口語化的回覆，要有制式化的通知呈現」——只回欄位值，不產生句子。

## Seqera 的模式（官方文件，只取功能）
run 狀態 submitted／running／succeeded／failed／cancelled／unknown〔docs.seqera.io/platform-enterprise/monitoring/overview〕；失敗 run 的細節＝Tasks 表（含 exit 欄＝task exit code）、task 的 exit code／status／attempts、Logs 分頁（Nextflow 主控台輸出）〔…/monitoring/run-details〕；run 選單有 Resume 與 Relaunch；**沒有失敗原因分類**。

## 範圍：檔案
- `platform/abf_platform/failures.py`（新檔）
- `platform/abf_platform/actions/__init__.py`（只在 `get_run`／`list_runs` 回傳加 `failure` 欄位；不動寫入函式）
- `platform/tests/test_failures.py`（新檔）
- `docs/PLATFORM.md`（加一小節「Failed runs」）
- `specs/failure-seqera/ledger.md`（進度帳本）

## 作法
1. `failures.summarize(view: dict) -> dict | None`：輸入 `status.get_run(..., detail=True)` 的 view（含 `status`、`failure_reason`、`failed_tasks`、`tasks` 計數、`cancel_requested_at`）。`status` 不是 `failed`／`lost` → None。不讀檔、不連網、不寫資料庫。
2. 回傳固定五鍵：
   - `status_seqera`：有 `cancel_requested_at` → `"cancelled"`；`lost` → `"unknown"`；否則 `"failed"`。
   - `failed_tasks`：`view["failed_tasks"]` 原值（每筆 `name, exit_code, error_message, workdir`），順序沿用 status 的排序，**不改寫、不截斷**；沒有就 `[]`。
   - `failure_reason`：原值（可為 None）。
   - `log`：view 裡已有的日誌取得方式（若 view 有日誌路徑／鍵就原樣帶；沒有就 None）。不新增讀日誌的功能。
   - `actions`：`["resume", "relaunch"]`；若 `tasks.succeeded + tasks.cached == 0` 則只有 `["relaunch"]`（沒有可沿用的快取）。
3. `actions.get_run` 直接用自己組好的 view；`actions.list_runs` 只對 status 是 `failed`／`lost` 的列另呼叫 `status.get_run(index_path, <id>, now)` 取完整 view、補 `jobs.cancel_requested_at(...)`，再交給 `summarize`，放進該列 `failure`；其他列 `failure` 為 None。列裡除了 `failure` 不多帶欄位。**不改 `status.py`**。
4. 在 `actions/__init__.py` 用 `from .. import failures`（不要 `from ..failures import summarize`，否則 `test_web_parity.py` 的 public_names 多一個名字）。
5. `failures.py` 與 `test_failures.py` 前 40 行內要有 `# Nothing existing: <理由，≥15 字>`（`test_scope.py` TC-070）；`failures.py` 的註解與 docstring 不得出現 `tw `、`station`、`ssh`（TC-061）。
6. PLATFORM.md 小節寫明：欄位意義、`lost` 對 Seqera 的 `unknown`、兩個動作對 Seqera Resume／Relaunch、本平台續跑還不能改資源與參數（缺口 `resume-edit-params`，記進 ledger 的「欠」）。
7. 不需要 migration。

## 失敗先行測試（`platform/tests/test_failures.py`，手造 view，不開伺服器）
- `test_ff01_not_failed_is_none`：running／succeeded → None。
- `test_ff02_failed_tasks_are_carried_verbatim`：一個 task `exit_code: 137, name: "NFCORE_AMPLISEQ:AMPLISEQ:DADA2_DENOISING", error_message: "Killed"` → 原值逐鍵相等。
- `test_ff03_lost_is_unknown`。
- `test_ff04_cancel_requested_is_cancelled`。
- `test_ff05_resume_and_relaunch_when_tasks_completed`：succeeded 3 → `["resume","relaunch"]`。
- `test_ff06_relaunch_only_when_nothing_completed`：succeeded 0、cached 0 → `["relaunch"]`。
- `test_ff07_shape_is_fixed`：恰好五鍵；actions ⊆ {resume, relaunch}；結果裡沒有任何分類或建議文字的鍵（例如 `cause`、`evidence`、`advice`）。
- `test_ff08_get_run_and_list_runs_carry_failure`：用既有 store harness 種一筆 failed run，`get_run` 與 `list_runs` 該筆 `failure.failed_tasks[0].exit_code == 137`；另一位使用者看不到（擁有者規則沿用）。
- `test_ff09_failures_is_read_only`：`ast` 檢查 failures.py 不 import `jobs`、`confirm`、`receiver`。

## 完成標準
九條綠；全套綠（`tests/init_workspace_test.sh` 的「site side with no run area known」在 v3 本來就因 WSL 不能 mkdir /work 而紅，不算本件退步，但不准改它）。

## 不做
- 不分類原因、不判斷資源碼、不比對錯誤訊息樣式、不產生建議句。
- 不自動送出續跑或重跑；不呼叫 AI／Jev；不改網頁（前端 session 另做）；不改 `status.py`、`receiver.py`。

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
