# 測試案例：網頁任務日誌（失敗任務）

**規格**：`specs/web-run-tasks-log/plan.md`（本任務沒有獨立 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞：「日誌」指失敗任務工作資料夾裡的三個檔案：`.command.err`（錯誤）、`.command.out`（輸出）、`.command.log`（全部）。「站台」是跑分析的那台機器；「agent」是站台上幫網頁讀檔的程式。自動測試主檔為 `platform/tests/test_web_run_log.py`，每條測試在註解裡寫上它對應的 TC 編號。

維護者的話（計畫引用）：「好」（2026-11-06 核准順序，優先序 2＝網頁的執行紀錄／任務清單檢視：每個 run 的 Nextflow 任務與日誌）。這句沒有可當輸入的句子，對應的成果是 TC-010：run 失敗時，在網頁就能知道哪個任務為何失敗，不必回對話叫 MCP 讀。

## User Story 1 — 從任務列與日誌分頁進入日誌（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 3「任務分頁加一格日誌」；tl12 | 功能 | 一個失敗的分析，有一個失敗任務，已記錄工作資料夾 | 登入後打開該分析的「任務」分頁 | 該失敗任務那一列有一格「日誌」，內含連到 `/run/log?...which=err` 的連結（帶該分析與該任務） | 自動：`platform/tests/test_web_run_log.py` |
| TC-002 | 作法 3「沒有 workdir 顯示灰字」 | 功能 | 一個失敗任務沒有記錄工作資料夾 | 打開「任務」分頁 | 該列的日誌格沒有連結，顯示灰字「沒有記錄工作資料夾」（英文版為成對的英文句） | 自動 |
| TC-003 | 作法 3「logs 分頁（執行中）」；tl11 | 功能 | 執行中的分析，有兩個失敗任務 | 打開 `tab=logs` | 頁面不含 `<section class="soon">`；兩個失敗任務各列出一筆，每筆有三個連結，標籤為「錯誤」「輸出」「全部」，分別連到 `which=err`、`which=out`、`which=log` | 自動 |
| TC-004 | 作法 3「logs 分頁（結果）」；tl11 | 功能 | 已結束（結果頁）的分析，有兩個失敗任務 | 打開 `tab=logs` | 同 TC-003：不含 `<section class="soon">`，兩個失敗任務各三個連結（錯誤／輸出／全部） | 自動 |
| TC-005 | 作法 3「無失敗任務」；tl11 | 功能 | 執行中的分析，沒有失敗任務 | 打開 `tab=logs` | 顯示一句「目前沒有失敗任務」，沒有日誌連結，也不是「之後開放」面板 | 自動 |
| TC-006 | 作法 3「無失敗任務」；tl11 | 功能 | 結果頁的分析，沒有失敗任務 | 打開 `tab=logs` | 顯示一句「目前沒有失敗任務」，沒有日誌連結，也不是「之後開放」面板 | 自動 |
| TC-007 | 作法 3「failed_partial 提示沿用」 | 功能 | 一個分析處於「失敗任務只列出一部分」（failed_partial）的狀況 | 打開 `tab=logs` | 顯示的提示文字與「任務」分頁在同一狀況下的提示逐字相同 | 自動 |
| TC-008 | 作法 3「failed_unlisted 提示沿用」 | 功能 | 一個分析處於「有失敗但任務清單抓不到」（failed_unlisted）的狀況 | 打開 `tab=logs` | 顯示的提示文字與「任務」分頁在同一狀況下的提示逐字相同 | 自動 |
| TC-009 | 允許改動清單；tl11 後段 | 功能 | 執行中頁與結果頁各一 | 讀分頁標籤 | 執行中頁的標籤順序仍為 Tasks, Logs, Run info, Configuration, Metrics；結果頁仍為 Outputs, Run info, Tasks, Logs | 自動：`test_web_running.py`、`test_web_results_outputs.py` |

## User Story 2 — 讀取並顯示日誌頁（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 目標：run 失敗時在網頁就能知道哪個任務為何失敗 | 功能 | 一個失敗的分析，任務「FASTQC」有記錄工作資料夾，站台上其 `.command.err` 內容為「Error: out of memory」 | 在「任務」分頁點該任務的「日誌」連結；第一次看到載入中；agent 讀完後（job 完成）重新整理 | 最後看到的頁面是整頁 HTML，內含任務名稱 FASTQC 與文字「Error: out of memory」；全程沒有回到對話叫 MCP 讀 | 自動 |
| TC-011 | tl06 後半；作法 2「loading 時頁面自己 15 秒刷新」 | 功能 | 該任務尚無任何讀日誌的 job | 第一次請求 `GET /run/log?run=&task=&which=err` | 回應是載入中頁面，內含自動刷新（15 秒），沒有顯示日誌文字 | 自動 |
| TC-012 | tl06 前半；作法 1 | 功能 | 同 TC-011 | 第一次請求，並在網址多帶一個假的 `workdir=/evil` | 資料庫新增剛好一個 `read_task_log` job；其參數的檔案為 `.command.err`，工作資料夾為該任務記錄的值，不是網址裡的內容；job 帶呼叫者身分 | 自動 |
| TC-013 | tl07 | 功能 | 已有一個 queued（排隊中）的 `read_task_log` job | 同一請求再送一次 | 仍是載入中頁面，資料庫的 job 數沒有增加 | 自動 |
| TC-014 | 作法 1「進行中 → loading」 | 功能 | 已有一個 running（執行中）的 `read_task_log` job | 同一請求再送一次 | 仍是載入中頁面，沒有新增 job | 自動 |
| TC-015 | tl08 | 功能 | job 已完成，結果文字為多行普通文字 | 請求該頁 | 頁面把文字放在 `<pre>` 區塊內，文字完整可見 | 自動 |
| TC-016 | tl08 | 功能 | job 已完成，結果文字含 `<script>alert(1)</script>` | 請求該頁 | 頁面中是 `&lt;script&gt;`，原始 `<script>alert(1)</script>` 不出現 | 自動 |
| TC-017 | tl08；作法 2「不是下載」 | 功能 | 同 TC-015 | 請求該頁並看回應標頭 | `Content-Type` 為 text/html；沒有 `content-disposition` 標頭 | 自動 |
| TC-018 | tl08；作法 2「沿用 _HEADERS」 | 功能 | 同 TC-015 | 請求該頁並看回應標頭 | CSP 標頭與網頁其他頁使用的 `_HEADERS` 完全相同，沒有放寬 | 自動 |
| TC-019 | 作法 3「錯誤／輸出／全部」；作法 1 | 功能 | 失敗任務有工作資料夾 | 請求 `which=out` | 排的 job 讀的檔案是 `.command.out` | 自動 |
| TC-020 | 同上 | 功能 | 失敗任務有工作資料夾 | 請求 `which=log` | 排的 job 讀的檔案是 `.command.log` | 自動 |
| TC-021 | tl09 | 功能 | job 完成，結果標示被截斷（超過 200 行或 64 KB） | 請求該頁 | 頁面顯示「已截斷」註記，並仍顯示取得的末段文字 | 自動 |
| TC-022 | 作法 1「10 分鐘內已有結果且未 retry → 直接回」 | 功能 | 10 分鐘內已有完成的同一任務同一檔案的結果 | 不帶 `retry` 再請求一次 | 直接顯示該結果，沒有新增 job | 自動 |
| TC-023 | 作法 1「retry」；作法 2 路由 `retry=` | 功能 | 同 TC-022 | 帶 `retry=1` 請求 | 新增一個 `read_task_log` job，頁面為載入中 | 自動 |
| TC-024 | 作法 1「以 task_key 或 name 比對」 | 功能 | 失敗任務清單中有一個任務，其 task_key 與 name 不同 | 分別用 task_key、用 name 當 `task=` 請求 | 兩種都被接受（都不是「找不到任務」錯誤），並使用同一個記錄的工作資料夾 | 自動 |
| TC-025 | 環境事實「檔案不存在要有白話，不是空白」（PITFALLS：無 `.command.log`／`.command.err`） | 例外 | 站台上該工作資料夾沒有被要求的檔案（例如工作資料夾放在登入節點 /tmp 沒有 `.command.log`，或 sbatch 拒絕作業名而沒有 `.command.err`） | 請求該檔案的日誌頁 | 頁面用一句白話說明檔案不存在（不是空白頁、不是 500） | 自動 |
| TC-026 | tl10 | 例外 | agent 離線 | 請求日誌頁 | 錯誤頁含一句白話（說明站台 agent 目前離線／讀不到），HTTP 狀態碼不是 500 | 自動 |
| TC-027 | 作法 1「JobRefused 轉成 not_on_site／refused 與一句理由」 | 例外 | 該分析的運算環境不在站台，或系統拒絕排這個 job | 請求日誌頁 | 錯誤頁含一句白話理由，說明為何目前讀不到；內容不洩漏他人分析是否存在 | 自動 |
| TC-028 | 專長守則「狀態表達」 | 功能 | 載入中狀態的日誌頁 | 看頁面 HTML | 同時含一個符號與一句文字（例如「讀取中」之類），不是只靠 class 顏色 | 自動 |
| TC-029 | 專長守則「狀態表達」 | 功能 | 完成（ready）狀態的日誌頁 | 看頁面 HTML | 同時含符號與文字標示該狀態，不是只靠 class 顏色 | 自動 |
| TC-030 | 專長守則「狀態表達」 | 功能 | 錯誤狀態的日誌頁（例如 agent 離線） | 看頁面 HTML | 同時含符號與文字，不是只靠 class 顏色 | 自動 |
| TC-031 | 作法 3「新字 zh／en 成對，英文不含中日韓字元」；DESIGN.md 約束「每個畫面都有英文」 | 功能 | 日誌頁、日誌分頁、任務列新增的字 | 以 `?lang=en` 看載入中、完成、錯誤三種日誌頁，與日誌分頁、任務分頁 | 介面字串全為英文且不含中日韓字元（日誌檔案本身的內容不算）；每個新中文字串都有對應英文 | 自動 |
| TC-032 | 作法 3「避開禁用字」；DESIGN.md「用字」 | 功能 | 新增的中文字串 | 跑 `test_web_wording_sweep.py` | 通過；掃描規則與禁用字清單沒有被修改，是新字去適應 | 自動：`test_web_wording_sweep.py` |
| TC-033 | 維護者原話／既有規範：無 `style=`、不載外部資源 | 功能 | 日誌頁的載入中、完成、錯誤三種狀態 | 看頁面 HTML | 不含 `style=` 屬性；不含指向外部網址的資源（連結到站內 `/run/...` 除外） | 自動 |
| TC-034 | 同上 | 功能 | 「日誌」分頁與「任務」分頁（含新連結），執行中頁與結果頁各一 | 看頁面 HTML | 不含 `style=` 屬性；不含外部資源；仍只有一份樣式表，CSP 的 sha256 釘住仍成立 | 自動 |
| TC-035 | 完成標準「docs/TESTING.md 有手動步驟」 | 功能 | `docs/TESTING.md` | 閱讀手動部分 | 有一段步驟：造一個失敗的分析，然後在網頁看到日誌；步驟具體到不懂程式的人可照做 | 手動：`docs/TESTING.md` |
| TC-036 | 作法 4；專長守則（ui） | 功能 | 執行者交付的截圖與 axe 結果 | 閱卷者跑 `scripts/dev/ui_check.py`，並把日誌頁、日誌分頁渲染成 HTML | 1440／390 寬 × 中／英共 4 張截圖；axe 無 serious 或 critical；PR 附對照 DESIGN.md 第 7、8 項的白話說明 | 手動：`docs/TESTING.md` |

## User Story 3 — 只看得到自己的分析、只讀得到失敗任務（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | tl01 | 例外 | 未登入 | `GET /run/log?run=...&task=...&which=err` | 回應與未登入請求 `/run/file` 的未授權回應相同 | 自動 |
| TC-038 | tl02 | 例外 | 使用者 B 登入，分析屬於使用者 A | B 請求 A 的分析的日誌頁 | 回 404 頁；資料庫沒有新增 `read_task_log` job | 自動 |
| TC-039 | 作法 1「不外洩他人 run 的存在」 | 例外 | 使用者 B 登入 | 分別請求 A 的分析、與一個根本不存在的分析編號 | 兩個回應（狀態碼與頁面內容）相同，看不出前者存在 | 自動 |
| TC-040 | 作法 1「run 不是呼叫者的 → found False，不排 job」（動作層） | 例外 | 使用者 B 的身分，A 的分析 | 直接呼叫 `actions.task_log_view(..., caller=B)` | 回傳 `found` 為 False 與一句訊息；沒有排 job | 自動 |
| TC-041 | tl03 | 例外 | 自己的分析，`task` 不在該分析的失敗任務清單內 | 請求日誌頁 | 顯示錯誤（動作層為 `error`）；沒有排 job | 自動 |
| TC-042 | 作法 1「不接受使用者自帶的 workdir 路徑」 | 例外 | 自己的分析；請求網址帶 `workdir=/etc` 或把 `task=` 填成路徑 | 請求日誌頁 | 沒有讀 /etc 或該路徑的 job；若 `task` 不在失敗清單則同 TC-041 | 自動 |
| TC-043 | tl04 | 例外 | 失敗任務沒有記錄工作資料夾 | 請求日誌頁 | 顯示錯誤（動作層 code 為 `no_workdir`）並有一句白話；沒有排 job | 自動 |
| TC-044 | tl05 | 例外 | 自己的分析與合法任務 | 請求 `which=foo`（不在 err／out／log） | 顯示錯誤（動作層 code 為 `bad_which`）並有一句白話；沒有排 job | 自動 |
| TC-045 | 專長守則（backend）「錯誤訊息不露出堆疊、內部路徑或 SQL」 | 例外 | 各種錯誤狀況（TC-025 至 TC-027、TC-041、TC-043、TC-044） | 看每個錯誤頁的文字 | 每個都說明發生什麼事與下一步；不含堆疊追蹤、SQL、平台主機的內部檔案路徑 | 自動 |

## User Story 4 — 這次不做的事（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-046 | 不做「成功／執行中任務的日誌」；環境事實「成功任務日誌讀不到」 | 不在範圍 | 一個分析有成功任務與執行中任務 | 看「任務」分頁與「日誌」分頁；再用成功任務的名稱請求日誌頁 | 成功與執行中的任務沒有日誌連結；用其名稱請求時回錯誤（同 TC-041），沒有排 job | 自動 |
| TC-047 | 不做「設定檔、指標分頁」；作法 3「config、metrics 仍是 soon」 | 不在範圍 | 執行中頁與結果頁 | 打開 `tab=config`、`tab=metrics` | 仍是 `<section class="soon">`「之後開放」面板，沒有被順手做出來 | 自動 |
| TC-048 | 不做「Nextflow 主日誌與 slurm-*.out」 | 不在範圍 | 自己的分析與合法任務 | 請求 `which=nextflow`、`which=slurm` | 回 `bad_which` 錯誤，沒有排 job；頁面上也沒有這兩種檔案的連結 | 自動 |
| TC-049 | 不做「即時串流／自動捲動（需要 JS）」；DESIGN.md「本任務不用 JS」 | 不在範圍 | 日誌頁的載入中、完成、錯誤三種狀態 | 看頁面 HTML | 不含 `<script`、事件處理屬性；載入中只靠整頁 15 秒刷新，不是串流 | 自動 |
| TC-050 | 不做「新增 MCP 工具」 | 不在範圍 | 本任務完成後 | 跑 MCP 快照測試與 `test_actions_layer.py` | `platform/tests/mcp/snapshots/tools.json` 與 BASELINE 沒有改動且測試通過；`task_log_view` 只列在 `test_web_parity.py` 的 WEB_ONLY | 自動：`test_actions_layer.py`、MCP 快照測試、`test_web_parity.py` |
| TC-051 | 不做「改 read_task_log」 | 不在範圍 | MCP 的 `read_task_log` 既有測試 | 跑既有測試 | 簽章與行為不變（失敗任務限定、200 行／64 KB、只限自己的 run），既有測試未被修改即通過 | 自動：既有 `read_task_log` 測試 |
| TC-052 | 不做「改 CSP」 | 不在範圍 | 既有釘住 CSP 全文的測試 | 跑 `test_results_files.py`、`test_web_board.py`、`test_web_downstream.py`、`test_web_upload.py` | 全部通過，且這些檔案中釘住 CSP 的斷言沒有被放寬 | 自動 |
| TC-053 | 不做「改 store.py、abf_station」；範圍：不准動的檔案 | 不在範圍 | 本任務的整個變更 | 閱卷者看 `git diff --stat` | 不含 `store.py`、`mcp_server.py`、`tools.json`、`platform/abf_station/`、`test_actions_layer.py` 的 BASELINE；沒有新 job 種類；因此不需要 migration | 手動：閱卷者核對 git diff（不在 docs/TESTING.md） |

## 憲法與安全網

本任務碰到的規則：網頁模組只呼叫動作層（tc060）；每位使用者只看自己的 run（擁有者規則）；CSP 單一樣式表釘住；Safety Net 的「寫入工具須經人確認」清單（launch／cancel／resume 等）沒有新增，本功能只排一個唯讀的讀檔 job，不在該清單內。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-054 | tc060：`web_*.py` 只呼叫 `actions`，不得 import jobs／status／compute_envs／confirm／agents；tl12 後半 | 功能 | 改動後的 `web.py`、`web_board.py` | 跑 tc060 的檢查 | 通過；兩個網頁模組沒有 import 上述模組（`latest_task_log` 只被 `actions` 使用） | 自動 |
| TC-055 | 網頁與動作層一一對應（對等性） | 功能 | `test_web_parity.py` | 跑該測試 | 通過；WEB_ONLY 新增 `task_log_view`、WEB_ROUTES 新增 `/run/log`，兩者都是加法，沒有改既有項目 | 自動：`test_web_parity.py` |
| TC-056 | 不弱化既有測試（Development Workflow） | 功能 | 本任務對既有測試檔的改動 | 閱卷者比對 base 與 HEAD | 被改的既有斷言僅限計畫列的幾條（`test_web_results_outputs.py` 的 logs 分頁斷言、`test_web_running.py` 的 soon 面板斷言、`test_web_parity.py` 的加法）；`test_web_wording_sweep.py` 的規則與禁用字沒改；沒有任何斷言被放寬或跳過 | 手動：閱卷者核對 git diff（不在 docs/TESTING.md） |
| TC-057 | 動作層唯一（專長守則 backend）；擁有者規則在動作層 | 功能 | `/run/log` 路由處理函式 | 閱卷者讀 `web.py` 路由 | 路由只呼叫 `actions.task_log_view` 並交給 `render_log_page`；比對失敗任務、挑 workdir、排 job、擁有者過濾都在動作層，路由裡沒有第二份邏輯 | 自動：TC-038、TC-040 對動作層與路由各驗一次，加閱卷核對 |
