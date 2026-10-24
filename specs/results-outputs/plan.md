---
id: results-outputs
title: 結果階段第一刀：摘要卡＋「輸出」分頁（列出 <run 資料夾>/results）＋其餘分頁沿用或標「之後開放」
tier: B
kinds: ui, backend
lane: L7-web-redesign
base: v3
source: DESIGN.md v2 畫面 8；011c-results-page 被 verifier 退回（10-22，P1–P11）後依其建議「第一刀只做摘要卡＋Outputs＋空狀態」重寫；維護者 10-24「繼續」
---

# results-outputs

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/results-outputs/plan.md`。**只處理本任務**。前置：web-v2-skeleton（#177）與 web-v2-fixes-1（#183）已合併；若 #183 尚未合併，從含 #183 的 origin/v3 開工。
> 取代 `011c-results-page.md` 的第一部分。Report（可編輯報告）、MultiQC 內嵌、Download all 留給後續任務（見「不做」）。
> 維護者 10-23：「先把功能做起來吧，以後再改美觀」——只用現有 class 與 DESIGN.md token。

## 目標
一個成功跑完的分析，點進「結果」階段就能看到它產出了哪些檔案（`<run 資料夾>/results` 的清單），不必登入叢集。這是同事不問人就能跑完一次 16S 的倒數第二步。

## 維護者原話（verifier 出題用）
1. DESIGN.md 畫面 8：「**Results stage**: summary cards; tabs Report (generated, editable, saved → goes into the package) / Outputs / Reports (MultiQC embedded, JS) / Run info / Tasks / Logs / Metrics; Download all.」（本任務做 summary cards、Outputs、Run info、Tasks、Logs；其餘以「之後開放」佔位）
2. 「進來之後馬上可以看到各個run的狀態與進度」（DESIGN.md 原話 R01）
3. 「下載、看結果甚麼的點進去看就好了。」（10-23，R16）
4. 「先把功能做起來吧，以後再改美觀」（10-23，R15）

## 範圍：檔案
- `platform/abf_platform/web_board.py`
- `platform/abf_platform/web.py`（只在 run 頁的 GET 處理裡呼叫新的 read，不加新路由）
- `platform/abf_platform/actions/__init__.py`（新增一個 read：`run_outputs`）
- `platform/abf_platform/jobs.py`（只限新增「查某路徑最新一筆 list_site_files 工作」的唯讀函式）
- `platform/abf_platform/mcp_server.py`（只在 parity 測試要求時登記同名 read tool）
- `platform/tests/test_web_results_outputs.py`（新檔）
- `platform/tests/test_web_parity.py`、`platform/tests/test_actions_layer.py`（只為新 read 更新清單／BASELINE；PR 與 ledger 寫明是有意的）
- `platform/tests/test_web_board.py`、`platform/tests/test_web_running.py`、`platform/tests/test_web_v2_skeleton.py`（只限「裁決 4」點名的斷言）
- `docs/PLATFORM.md`（一段：結果階段的輸出清單從哪來）

## 作法
**結果階段頁**（`?run=<id>&stage=results`，成功的 run 預設就是這頁）取代現在 `_stage_card` 在 results 階段顯示的 `_task_card`：
- 四張摘要卡（沿用執行階段卡片元件）：完成步驟 `n / n`、耗時、運算環境、費用。
- 分頁列（同執行階段的分頁元件），網址值與順序：`outputs`（預設）｜`info`｜`tasks`｜`logs`；中文「輸出／執行資訊／任務／日誌」，英文「Outputs／Run info／Tasks／Logs」。`info`／`tasks`／`logs` 直接重用 `tab_body`。
- 「報告」「MultiQC 報告」「指標」「全部下載」以灰字「之後開放」顯示（不是連結），英文「Report／MultiQC report／Metrics／Download all」＋「coming later」。
- 未成功的 run 進 `stage=results`：維持現在的「這個 run 還沒到這個階段。」。

**輸出分頁的資料：新 read `run_outputs(index_path, platform_path, run_id, *, caller)`**（動作層唯一入口，網頁與 MCP 共用）：
- 擁有者規則在動作層：別人的 run 回「找不到」，不洩漏是否存在。
- 路徑＝該 run 最新一次 launch 的 `run_folder` ＋ `/results`（站台 `abf_station/launch.py:359` 固定 `outdir = run_folder + "/results"`）。run 不是平台送出的（沒有 launch 紀錄）→ 狀態 `unavailable`，原因「不是從平台送出的分析，沒有輸出資料夾紀錄」。
- **不阻塞頁面**：網頁每 15 秒自動更新，所以 read 不得等待站台。作法＝先找 jobs 表中「同一運算環境、kind=list_site_files、args 路徑等於該 results 路徑」最新一筆：
  - 有、已完成且 ok → `ready`，回檔案清單（名稱、類型、大小、修改時間，沿用 list_site_files 結果欄位）＋讀取時間；
  - 有、還在 queued／claimed → `loading`；
  - 有、失敗或逾時 → `error`，附站台回的訊息（白話、不露路徑以外的內部細節）；
  - 沒有（或已被清掉）→ 送出一筆新的 listing 工作並回 `loading`。
  - 頁面上「重新讀取」連結（GET `&tab=outputs&relist=1`）會強制送新的一筆；自動更新的網址不得帶 `relist`。
- 站台離線或運算環境不可用 → 不送工作，`error`，原因沿用 `jobs` 既有的拒絕句。
- 列表只讀，不需要確認頁（同 list_site_files）。

**輸出分頁四種狀態**（符號＋文字＋顏色）：
- `loading`：「⟳ 讀取中」＋「每 15 秒自動更新」；
- `ready`：檔案表（名稱用等寬字、資料夾在前、名稱排序）＋「讀取於 HH:MM」＋「重新讀取」；空資料夾 → 「— 這個資料夾是空的」；
- `error`：「✗ 讀不到」＋原因欄位＋「重新讀取」；
- `unavailable`：「— 沒有輸出資料夾紀錄」＋原因。

**不能放掉的限制**：零 JavaScript、無 `style=`、單一樣式表（CSP 雜湊）、15 秒 refresh、每人只看自己的 run、版面不溢出（390 px 無橫向捲動；檔名過長在欄內換行）。

## 失敗先行測試
`platform/tests/test_web_results_outputs.py`（用 `test_web_v2_skeleton` 的 World／`std` 種子，必要時加一筆有 launch 紀錄的 succeeded run）：
- `test_ro01_results_stage_has_cards_and_tabs`：succeeded run 的 `stage=results` 有四張卡、四個可點分頁（outputs 預設選中）、四個「之後開放」灰字；不再出現執行階段的任務卡。
- `test_ro02_first_view_queues_one_listing_and_shows_loading`：第一次 GET 送出恰一筆 list_site_files，路徑＝`<run_folder>/results`；頁面「讀取中」；第二次 GET（工作仍在排隊）不再多送。
- `test_ro03_finished_listing_is_shown`：模擬站台回結果後，GET 顯示檔名、資料夾在前、「讀取於」。
- `test_ro04_empty_folder` 、`test_ro05_error_shows_reason_and_relist`、`test_ro06_not_launched_from_platform_is_unavailable`。
- `test_ro07_relist_queues_a_new_job_and_refresh_url_has_no_relist`。
- `test_ro08_owner_rule`：bob 用 ann 的 run id → 動作層回找不到，頁面不送 listing。
- `test_ro09_page_never_waits_for_the_site`：站台不回應時 GET 仍立即回 200（不呼叫 `wait_for_result`）。
- `test_ro10_english`、`test_ro11_constraints_hold`（無 `<script`、無 `style=`、CSP 雜湊相符、有 15 秒 refresh）。
- parity／BASELINE 更新。

## 完成標準（done when）
上列測試綠；全套綠（環境紅見裁決 1）；改寫的既有斷言在 ledger 逐條「舊→新＋理由」。截圖由 developer-agent 補（1440／390 × zh／en）。

## 環境事實
- `outdir` 固定 `<run_folder>/results`：`platform/abf_station/launch.py:285,359`。`run_folder` 在 platform.db `launches` 表；最新一次 launch 用 `jobs.latest_launch(con, run_name)`。
- `actions.list_site_files` 會 `await jobs.wait_for_result`（最長 60 秒，`DEADLINE_SECONDS["list_site_files"]`）——**網頁不能走它**，要自己查 jobs 表。
- jobs 表欄位：`agent, compute_env, kind, args_json, state, created_at, deadline_at, finished_at, result…`；完成的工作過 `PRUNE_AFTER_SECONDS` 會被刪（被刪就等於沒有，重送）。
- `_uploads_problem` 只管上傳資料夾；run 資料夾的列表是否被站台的 read roots 允許，executor 要先查 `abf_station` 的 listing 規則。**若站台拒絕列 run 資料夾，回 BLOCKED，不改站台程式**。
- 目前結果階段顯示 `_task_card`（`web_board.py::_stage_card`）。
- 截圖工具（developer-agent 用）：`memory/scripts/abf-shots/`。

## 不做
- 不做可編輯報告、MultiQC 內嵌、全部下載／交付包、指標（後續任務）。
- 不改站台（`abf_station/*`）、不改確認頁、不加 JS、不改 token、不動右欄。
- 不做下載單一檔案（之後與 Download all 一起設計）。

## 裁決
1. 已知環境紅 `tests/init_workspace_test.sh`「site side with no run area known fails clearly」（桌機 WSL `/work` 權限，CI 綠、base 也紅）不算本任務的紅。
2. 新 read 名稱固定 `run_outputs`；回傳 `{"state": "loading|ready|error|unavailable", "path", "files": [...], "listed_at", "reason"}`。
3. 查 jobs 表用新的唯讀函式（建議 `jobs.latest_listing(state_path, ce_name, path)`）；**不新增資料表、不需要 migration**（理由：jobs 表已存結果）。
4. 可改寫的既有斷言：只限斷言「succeeded run 的結果階段顯示任務卡／`_task_card` 內容」的那幾條；executor 先列出 file:line 寫進 ledger 再改。其他既有斷言變紅 → BLOCKED。
5. 分頁元件、卡片元件沿用現有 class；可新增的 CSS 只限：輸出表格的檔名換行（`overflow-wrap:anywhere`）與狀態列。不得新增顏色或間距數值。
6. succeeded run 的右欄維持現狀。

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
