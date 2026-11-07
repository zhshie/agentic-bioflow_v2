---
id: web-run-tasks-log
title: 網頁分析頁的任務日誌：失敗任務逐筆「看日誌」、日誌分頁（非阻塞）
tier: B
kinds: ui, backend
risk: M
lane: web-run
base: v3
blocked_on: none
source: 同事測試員回報缺口；維護者 2026-11-06 核准順序答「好」（優先序 2＝網頁的執行紀錄／任務清單檢視）
---

## 目標

分析頁的「日誌」分頁現在是灰色「之後開放」。本任務讓使用者在網頁上看到：每個失敗任務的 `.command.err`／`.command.out`／`.command.log` 末段（沿用 `read_task_log` 的上限：200 行、64 KB），不必回 Claude 對話叫 MCP 讀。對使用者的意義：run 失敗時，在網頁就能知道哪個任務為何失敗。

已有什麼（不重做）：
- 「任務」分頁（`web_board.tab_body(..., "tasks")`）已列失敗任務：名稱、結束碼、訊息、工作資料夾（只在有記錄時）。
- MCP 工具 `read_task_log`（`actions.read_task_log`，async、阻塞、只讀失敗任務、200 行／64 KB、限呼叫者自己的 run）已存在；agent 端 `read_task_log` job 與 `jobs.enqueue_task_log` 已存在，**不需要新 job 種類，不動 store.py CHECK**。
- 網頁讀檔的非阻塞範式已存在：`actions.run_file`（排 job → `loading` → 15 秒刷新讀 job 列）與 `web.run_file_get`／`web_board.render_file_page`。

缺的：網頁沒有非阻塞的 task-log 讀法；日誌分頁無內容；任務列沒有連到日誌。

## 維護者原話（verifier 出題用）

- 同事測試員回報的缺口，維護者 2026-11-06 核准順序：「好」（優先序 2＝網頁的執行紀錄／任務清單檢視：每個 run 的 Nextflow 任務與日誌）。
- DESIGN.md 第 7 項（執行中分頁）與第 8 項（結果頁分頁）已列「日誌」「Tasks」「Logs」；DESIGN.md 第 93 行：JS 只在標明處使用，**本任務不用 JS**。
- 既有規範（逐字沿用，不得違反）：網頁無 JS、無 `style=`、單一樣式表由 CSP sha256 釘住；`web_*.py` 只呼叫 `actions`，不得 import jobs／status／compute_envs／confirm／agents（tc060）；每位使用者只看自己的 run。

每句至少一條測試：見「失敗先行測試」tl01–tl12。

## 範圍：檔案

只准改：
- `platform/abf_platform/actions/__init__.py`（新增非阻塞 `task_log_view`；不改 `read_task_log` 簽章與行為）
- `platform/abf_platform/jobs.py`（新增 `latest_task_log(state_path, ce_name, workdir, filename)`，仿 `latest_run_file`；`enqueue_task_log` 不改）
- `platform/abf_platform/web.py`（新路由 `GET /run/log`；`board_page` 與 `read_run` 只在需要處傳遞）
- `platform/abf_platform/web_board.py`（日誌分頁、任務列連結、`render_log_page`、STRINGS 加字；STYLE 只用現有 token）
- 測試：`platform/tests/test_web_run_log.py`（新）、`test_web_parity.py`（WEB_ONLY 加 `task_log_view`、WEB_ROUTES 加 `/run/log`）、`test_web_results_outputs.py`、`test_web_running.py`、`test_web_wording_sweep.py`（只在新字需要時）
- `docs/TESTING.md`（本功能的手動截圖步驟）

不准動：`mcp_server.py`、`platform/tests/mcp/snapshots/tools.json`、`test_actions_layer.py` 的 BASELINE（本任務不新增 MCP 工具；`task_log_view` 是網頁專用，列在 WEB_ONLY）、`store.py`、`platform/abf_station/`。

## 作法

1. `actions.task_log_view(index_path, platform_path, run_id, task_key, which, *, caller=None, retry=False)`：
   - run 不是呼叫者的 → `{found: False, message}`，不排 job。
   - `task_key` 必須在該 run 的 `failed_tasks` 內（用 `status.get_run` 的 `failed_tasks`，以 task_key 或 name 比對；不接受使用者自帶的 workdir 路徑）。workdir 取記錄值；沒有記錄 → `error` code `no_workdir`。
   - `which` ∈ `LOG_FILES` 的鍵（err／out／log）；其他 → `bad_which`。
   - 仿 `run_file`：查 `jobs.latest_task_log`；進行中 → `loading`；10 分鐘內已有結果且未 `retry` → 直接回；否則 `jobs.enqueue_task_log(...)`（`caller_user_id` 帶呼叫者）。`JobRefused` 轉成 `error` code（`agent_offline`、`not_on_site`、`refused`）與一句理由，不外洩他人 run 的存在。
   - 回傳 `{found, state: loading|ready|error, code, reason, task, which, text, truncated, lines}`；`text` 只在 ready 有。
2. `web.py`：`GET /run/log?run=&task=&which=&retry=` → `render_log_page`；未登入走 `unauth`；ready 時**整頁 HTML**（文字用 `esc()` 放進 `<pre>`），**不是**下載；沿用 `_HEADERS`（不放寬 CSP）。loading 時頁面自己 15 秒刷新（同 `render_file_page` 的做法）。
3. `web_board.py`：
   - 「任務」分頁每個失敗任務列加一格「日誌」，連到 `/run/log?...&which=err`（有 workdir 才有連結，否則灰字「沒有記錄工作資料夾」）。
   - `logs` 分頁（running 的 `TABS` 與 results 的 `RESULT_TABS` 兩處）不再是 `<section class="soon">`：列出失敗任務，每筆三個連結（錯誤／輸出／全部＝err／out／log）；無失敗任務 → 一句「目前沒有失敗任務」；`failed_partial`／`failed_unlisted` 的提示沿用任務分頁的字。
   - `config`、`metrics` 分頁**仍是** `soon`（不在本任務）。
   - 用字：新字一律 zh/en 成對，英文不含中日韓字元，避開 `test_web_wording_sweep.py` 的禁用字。
4. 設計關卡：這是畫面改動（kind: ui）。版面照 Seqera 的 run 頁 Tasks／Logs 結構（R26／R27：先模仿 Seqera／nf-core，只換色票與用字），不自創；executor 附 `scripts/dev/ui_check.py` 四張截圖（1440／390 px × zh／en）與 axe 結果，並對照 DESIGN.md 第 7、8 項寫一段白話說明；PR 說明引用本節。

## 失敗先行測試

新檔 `platform/tests/test_web_run_log.py`（先寫、現在會紅）：
- tl01 `GET /run/log` 未登入 → 同 `/run/file` 的未授權回應。
- tl02 他人的 run → 404 頁，且資料庫沒有新 `read_task_log` job。
- tl03 task 不在 `failed_tasks` → `error`，沒有 job 被排。
- tl04 沒有 workdir 記錄 → `error`／`no_workdir`，沒有 job。
- tl05 `which` 不在 err／out／log → `bad_which`。
- tl06 第一次請求 → `loading`＋排了一個 `read_task_log` job（args 的 file 為 `.command.err`，workdir 為記錄值，不是 query 內容）；頁面含自動刷新。
- tl07 同一請求再來（job 仍 queued）→ 不重複排。
- tl08 job done、結果文字 → 整頁含該文字、內容被跳脫（`<script>` 變 `&lt;script&gt;`）、`Content-Type: text/html`、無 `content-disposition`，CSP 與 `_HEADERS` 相同。
- tl09 結果超過 200 行／64 KB → 顯示「已截斷」註記。
- tl10 agent 離線 → 錯誤頁含一句白話，狀態碼不是 500。
- tl11 running 與 results 兩種頁的 `tab=logs` 都不再含 `<section class="soon">`，含失敗任務的三個連結；無失敗任務 → 「目前沒有失敗任務」。
- tl12 任務分頁每個失敗任務列有 `/run/log?...which=err` 連結；網頁模組仍符合 tc060（不 import jobs 等）。

### 允許改動的既有斷言（只准這幾條，其餘不得改）

以 `git grep` origin/v3 查出，會因日誌分頁不再是 `soon` 而變：
- `platform/tests/test_web_results_outputs.py:109`：`'<section class="soon">' in mid(c.get(url(rid, tab="logs")).text)` → 改成日誌分頁的新內容斷言。
- `platform/tests/test_web_running.py:289`：分頁標籤順序（`Tasks, Logs, Run info, Configuration, Metrics`）**不變**；`:315` 的 `soon` 面板斷言要改為只剩 `config`／`metrics`（若該段迴圈含 `logs`，把 `logs` 移出）。
- `platform/tests/test_web_results_outputs.py:347`：results 分頁標籤 `Outputs, Run info, Tasks, Logs` **不變**。
- `test_web_wording_sweep.py:98,303,577`：`TABS` 含 `logs`，頁面渲染掃描會涵蓋新字；新字必須過掃描，不是改掃描。
- `test_web_parity.py`：WEB_ONLY／WEB_ROUTES 加新名稱（加法，不是改既有項）。
不變的釘住（不得放寬）：CSP 全文（`test_results_files.py:707`、`test_web_board.py:883`、`test_web_downstream.py:144`、`test_web_upload.py:1184` 等）、MCP `tools.json` 與 `test_actions_layer.py` BASELINE。

## 完成標準（done when）

- tl01–tl12 全綠；改過的既有斷言僅上列幾條；`platform/tests` 全套綠（已知環境紅見 README 通例）。
- `git diff --stat` 不含 store.py、mcp_server.py、tools.json、platform/abf_station/；新增路由已列入 parity 測試。
- 四張截圖（1440／390 × zh／en）與 axe 無新違規；白話說明附在 PR。
- docs/TESTING.md 有手動步驟：造一個失敗 run → 網頁看到日誌。

## 環境事實

- 日誌在站台上，由 agent 讀（`read_task_log` job，期限 60 秒）；agent 離線或站台不可達時網頁只能說明原因，不能補讀。
- `failed_tasks`（store.py）每個任務名只留一列，欄位 run_id, task_key, name, exit_code, error_message, workdir；`workdir` 不是每列都有（receiver 只在 Tower 事件帶出時記錄）。`task_usage` 沒有 workdir，所以**成功任務的日誌讀不到**（見不做）。
- 工作資料夾放在登入節點 `/tmp` 時沒有 `.command.log`／`.exitcode`；sbatch 拒絕作業名含 `|` 時沒有 `.command.err`（PITFALLS，見下）——此時畫面要顯示「檔案不存在」的白話，不是空白。
- PITFALLS 已查，相符項：
  - Launching 節（約 667 行）：`Symptom: jobs fail before the task script runs, leaving no .command.log and no .exitcode, only a bare exit 1 in sacct`——檢查：日誌頁對「檔案不存在」給白話，測試 tl10 一併涵蓋。
  - Launching 節（約 688 行）：`Symptom: every submission of nf-core/funcscan fARGene tasks dies at once with sbatch: error: ERROR: Job name contains an invalid character '|' and there is no .command.err`——同上。
  - 圖片與 PDF 經 Tower Agent 會壞、HTML／TSV／日誌可靠：本任務只讀文字日誌，不受影響。

## 不做

後續切片（另開任務，不在這裡做）：
- 成功／執行中任務的清單與日誌：需要 receiver 為所有任務記 workdir（改 store 結構＝要 migration，tc063），且 `get_run` 形狀變動會動 MCP 快照。
- 「設定檔」「指標」分頁（仍 `soon`）。
- Nextflow 主日誌（`.nextflow.log`）與 slurm-*.out：位於 run 資料夾而不在 `results/`，現有 `read_run_file` 讀不到，要新增 agent 端讀法（動 `platform/abf_station/`，風險 L）。
- 即時串流／自動捲動（需要 JS，DESIGN.md 未標此處可用 JS）。
- 新增 MCP 工具、改 `read_task_log`、改 CSP、改 `store.py`。

## 裁決
- lead 2026-11-07（回應 web-run-tasks-log-fail-1「UNVERIFIED needs human」）：TC-035、TC-036 屬「PR 階段交付」，不是推送的前置條件。處理：(1) 測試已綠（0d05064d）就推分支、開 PR；(2) 由閱卷者（verifier）依本計畫「專長守則（ui）」跑 `scripts/ui_check.py`（無則用 Playwright＋with_server.py）拍 4 張截圖、跑 axe，結果附 PR；(3) axe 若跑不出來，標 axe：UNVERIFIED 並寫缺什麼，不當作 FAIL；(4) TC-035 閱卷者對 docs/TESTING.md 手動步驟逐字讀一遍，標 PASS／FAIL。(5) 網頁畫面 B 級：verifier 通過＋CI 綠即掛自動合併，截圖進每日清單讓維護者事後看（10-24、10-29 他定）。
- 此件不需要維護者事前點頭。

## 專長守則（ui）

### executor

- 先讀專案根目錄的 `PRODUCT.md`（給誰用、要解決什麼）與 `DESIGN.md`（版面線框、tokens、每個畫面與狀態、維護者的原話例子）。讀不到就 BLOCKED，不自己發明設計。
- 只准用 `DESIGN.md` 定義的 tokens（色彩、字型、字級、間距、圓角）與版面。不新增任何視覺決策：不自創顏色、字型、間距數值，不順手「美化」。
- `DESIGN.md` 沒決定的事，一律寫進報告的「卡住的原因／要問的問題」，不猜。
- `DESIGN.md` 列出的每個畫面、每個狀態都必須做出來，包含空狀態、載入中、錯誤、失敗。少一個就不算完成。
- 遵守計畫寫明的前端限制（例如 CSP、禁用 inline style、不載外部資源、只在允許處使用 JS）。限制與設計衝突時停下來問，不自行取捨。
- 狀態絕不只靠顏色：一律「符號＋文字＋顏色」三者並用。
- 手機寬度可用（不橫向捲動、點擊目標夠大），鍵盤操作時焦點外框可見。
- 介面文字用使用者視角的白話，不露出內部術語、錯誤代碼或程式名詞；錯誤訊息說發生什麼事與下一步。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- `DESIGN.md` 的每個畫面、每個狀態都至少對應 1 個 TC（含空、載入、錯誤、失敗）。
- 維護者的原話例子逐字對應到 TC。
- 計畫列的前端限制各對應 TC（例如頁面不得含 inline style、不得請求外部網址、CSP 標頭存在）。
- 狀態表達 TC：每個狀態輸出的 HTML 同時含符號、文字，不得只靠 class 顏色。

**ACCEPTANCE（閱卷）必須檢查：**
- 把每個有改動的頁面渲染成 HTML 檔（用專案的 test client，或計畫指名的 fixture）。做不到就標 UNVERIFIED，並寫明需要什麼才能驗。
- 對渲染出的 HTML 跑 Impeccable 偵測器（唯讀）：`sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>`。
- **FAIL**：違反 `DESIGN.md` 的 tokens／畫面／狀態；違反計畫寫明的前端限制；狀態只靠顏色；缺少 DESIGN.md 列出的畫面或狀態。
- **「需要人看的事」**：偵測器的其他發現（對比、常見字型、AI 範本味等）與品味問題。這些不判 FAIL。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
- 注意：「看起來好不好」的最終判斷屬於維護者，靠 developer-agent 附在 PR 的截圖（B 級）決定，verifier 不替他下結論。
- **實際跑起來看（ACCEPTANCE，2026-11-03 加）**：用 `webapp-testing` 的 `with_server.py` 把真正的應用程式起起來，再用 Playwright 驗。腳本路徑 `G:/我的雲端硬碟/謝馬爾/.claude/skills/webapp-testing/scripts/with_server.py`，**先跑 `--help`** 看用法（把它當黑盒子用，不要先讀原始碼）；啟動指令與通訊埠寫在計畫裡。
  - repo 已有 `scripts/ui_check.py` 就直接跑它：1440／390 寬 × zh／en 共 4 張截圖，加 axe-core 無障礙掃描；**axe 出現 serious 或 critical 一律 FAIL**。
  - repo 還沒有 `ui_check.py`：verifier 自己用 Playwright（經 `with_server.py`）拍同樣 4 張截圖；axe 沒跑就標 **axe：UNVERIFIED**，並寫明缺什麼。
  - 截圖只能存到 repo 之外或 `.gitignore` 排除的資料夾，**絕不存進 Drive 工作區**；報告只貼路徑與張數。
  - 起不了應用程式（缺依賴、埠被占）標 UNVERIFIED 並寫明需要什麼，不改以靜態 HTML 當作通過。

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
