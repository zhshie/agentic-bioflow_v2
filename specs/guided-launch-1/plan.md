---
id: guided-launch-1
title: 引導式送出第一刀：/launch 改成七步編號引導（前置檢查、選管線「用過的」、樣本表、參數三路線、運算環境、確認）；流程圖與「全部 nf-core」搜尋標之後開放
tier: B
kinds: ui, backend
lane: L7-web-redesign
base: v3
source: DESIGN.md v2 畫面 5；總表 012b-2；維護者 10-24 回「好」（同意引導式送出排在結果頁之後）
---

# guided-launch-1

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/guided-launch-1/plan.md`。**只處理本任務**。前置：results-outputs（#191）已合併。
> 012b-2 的第一部分。第二部分（guided-launch-2）做：流程圖（pipeline 的 `docs/images/`）、「全部 nf-core」搜尋、平台側讀 `nextflow_schema.json`／`schema_input.json`（新 `schema.py`，要連 GitHub）、參數分組表、樣本表預覽與欄位角色。本任務**不連網**。
> 維護者 10-23：「先把功能做起來吧，以後再改美觀」——只用現有 class 與 DESIGN.md token。

## 目標
同事打開「新分析」，不再面對一張空白表單，而是照 1→7 的編號一步一步走：先挑以前用過的管線（或填新的），系統告訴他站台連線與管線登記有沒有問題，再選樣本表、參數、運算環境，最後看一次摘要按送出，進到既有確認頁。送出的東西跟今天的表單完全一樣（同一個 `request_launch`）。

## 維護者原話（verifier 出題用）
1. 「在送出的介面就要有之前abf-v2那些引導的事情，包括選擇pipline (之前設定的 or 新開的)、pipline的流程圖、pipline的參數等等。介面上不要有AI太口語化的回覆，要有制式化的通知呈現」（DESIGN.md 原話 7）
2. 「開啟一個專案、上傳rawdata之後，馬上就看到選pipline的階段，系統直接一個個引導使用者。」（原話 1）
3. 「Seqera功能太多學習成本高」（原話 6）
4. 「先把功能做起來吧，以後再改美觀」（原話 15）
5. DESIGN.md 畫面 5（英文原文照抄進測試案例）：「guided walk of v2's launch skill, numbered disclosures (done ✓ / current outlined / later): 1 Pre-checks … 2 Pipeline: tabs "Used before" (pipeline, revision, last used by, when; Select; ⚡ Quick launch = all previous settings → confirmation) and "New pipeline (all nf-core)" … 3 Workflow diagram … 4 Samplesheet … 5 Parameters: three routes ① reuse a previous run ② defaults ③ adjust by group … 6 Compute environment · 7 Confirm.」

## 範圍：檔案
- `platform/abf_platform/web_board.py`（`render_launch` 改寫）
- `platform/abf_platform/web.py`（只改 `/launch` 的 GET／POST 處理；不加新路由）
- `platform/abf_platform/actions/__init__.py`（新增一個 read：`list_used_pipelines`）
- `platform/abf_platform/mcp_server.py`（同名 read tool，parity 要求）
- `platform/abf_platform/static/*.css`（只限裁決 5）
- `platform/tests/test_web_guided_launch.py`（新檔）
- `platform/tests/test_web_actions.py`（只限裁決 4 點名的斷言）
- `platform/tests/test_web_parity.py`、`platform/tests/test_actions_layer.py` 及其他「工具清單／工具數」釘死斷言（只加 `list_used_pipelines` 一項，ledger 逐條列）
- `docs/PLATFORM.md`（一段：引導式送出的七步各自讀什麼）

## 作法
**頁面＝`GET /launch`，七個編號區塊**（`<details>`／`<summary>`，無 JS）。狀態三種，各有符號＋文字＋樣式：已完成 `✓`（收合）／目前（展開、外框）／之後（收合、灰）。步驟狀態完全由網址參數決定（`pipeline`、`revision`、`from`、`samplesheet`、`ce`），不新增 session 狀態或資料表。

1. **前置檢查**：選好管線之前顯示「選好管線後檢查」。選好後列出（每項 ✓／✗／— ＋一句制式說明）：
   - 版本已指定（revision 非空）；
   - 站台連線（所選或預設運算環境的 `status`／`checked_ok`／`message`，經既有 read `get_compute_env`／`list_compute_envs`）；
   - 管線已登記（該環境 `sitePipelines` 是否含這個 pipeline＋revision；環境沒有 `sitePipelines` 清單 → 「—（這個環境不需登記）」）；
   - 有可用樣本表（`list_samplesheets` 非空）；
   - 「讀取管線參數表」→ 灰字「之後開放」。
   ✗ 的項目不擋送出（最後仍由確認頁與站台把關），但在第 7 步摘要重列。
2. **選管線**：兩個分頁（網址 `&src=used|new`，預設 `used`；沒有用過的 → 預設 `new`）。
   - 「用過的」：表格欄＝管線、版本、上次分析名稱、上次送出時間、運算環境；每列兩個連結：「選擇」（GET `/launch?pipeline=…&revision=…`）與「⚡ 快速送出」（GET `/launch?from=<run 名>`，沿用既有 prefill，所有步驟 ✓、停在第 7 步）。
   - 「新管線」：沿用今天的 `pipeline`、`revision` 兩個欄位（GET 表單，送出後回到本頁並帶參數）＋灰字「搜尋全部 nf-core 之後開放」。
3. **流程圖**：灰字「之後開放」（第二刀）。顯示為「之後」狀態但不擋後續步驟。
4. **樣本表**：沿用今天的 select（`list_samplesheets`）。沒有樣本表 → 制式通知「沒有可用的樣本表。」＋說明上傳位置（沿用既有文字）。預覽與欄位角色「之後開放」。
5. **參數**：三條路線（單選）：① 沿用上次分析（列出這條管線＋版本用過的分析，選了＝以 `launch_prefill` 帶入參數）② 預設值（不帶參數）③ 自己調整（今天的 `name: value` textarea；參數分組表「之後開放」）。
6. **運算環境**：沿用 select，每個選項旁顯示狀態符號＋文字（來自既有 read）。
7. **確認**：摘要（管線＋版本、分析名稱、樣本表、改過的參數、運算環境、第 1 步的 ✗ 項目）＋「送出」按鈕＝今天的 `POST /launch`（同欄位、同 CSRF、同驗證、同 `request_launch` → 303 到 `/c/<id>` 確認頁）。分析名稱欄位放在這一步。

**新 read `list_used_pipelines(platform_path, *, caller)`**（動作層唯一入口，網頁與 MCP 共用）：
- 來源：`launches` 表 join `confirmations.bundle_json`（pipeline、revision、params 在 bundle 裡；`launches` 沒有 pipeline 欄），經 `jobs.launch_content`；略過已遺忘（`run_forgotten`）的。
- 擁有者規則：只回 caller 自己的。
- 回傳 `{"pipelines": [{"pipeline", "revision", "run_name", "launched_at", "ce_name"}]}`：同一 (pipeline, revision) 只留最新一筆，最新在前，最多 20 筆。
- 不新增資料表、不需 migration。

**POST 不變**：驗證規則、錯誤時 400 重繪（重繪時停在出錯那一步、其餘值保留）、`request_launch` 參數完全一樣。

**不能放掉的限制**：零 JavaScript、無 `style=`、單一樣式表（CSP 雜湊）、每人只看自己的、390 px 無橫向捲動、英文版每個字都有、制式通知（不口語、不用「我」「你可以試試」這類句子）。既有 `test_web_actions.py` 的 tc046–048、tc051、tc060、tc063、tc040 全部要繼續綠。

## 失敗先行測試
`platform/tests/test_web_guided_launch.py`（用 `test_web_actions.py`／`test_web_board.py` 的 World 與 seed）：
- `test_gl01_seven_numbered_steps`：`GET /launch` 有 1–7 七個編號區塊、標題中英各一套；沒選管線時第 2 步是目前、第 1 步顯示「選好管線後檢查」、第 3 步「之後開放」。
- `test_gl02_used_before_lists_own_launches_newest_first`：ann 送過兩條不同管線＋一次重複 → 表格兩列、最新在前；bob 的不出現；遺忘的不出現。
- `test_gl03_select_marks_step2_done_and_runs_prechecks`：`?pipeline=nf-core/ampliseq&revision=2.18.0` → 第 2 步 ✓、第 1 步列出四項檢查＋一項之後開放。
- `test_gl04_registered_check`：環境 `sitePipelines` 有／沒有該版本／沒有清單 三種 → ✓／✗／—。
- `test_gl05_site_connection_check`：環境 status 正常／錯誤 → ✓／✗＋環境的 message。
- `test_gl06_quick_launch_prefills_everything_and_stops_at_confirm`：`?from=<run>` → 所有步驟 ✓、第 7 步展開，摘要列出帶入的參數。
- `test_gl07_param_routes`：① 帶入上次參數 ② 空 ③ textarea 原樣。
- `test_gl08_post_unchanged`：照引導送出 → 一筆 pending 確認、303 到 `/c/<id>`，bundle 與今天的表單送出相同欄位結果相同。
- `test_gl09_post_error_rerenders_at_the_failing_step`：缺 run_name → 400、第 7 步展開、其他值保留、沒有新確認。
- `test_gl10_no_samplesheet_notice`、`test_gl11_english`、`test_gl12_constraints_hold`（無 `<script`、無 `style=`、CSP 雜湊、無口語句）。
- `test_gl13_list_used_pipelines_action_and_mcp_match`：動作層與 MCP 回同樣內容；bob 看不到 ann 的。

## 完成標準（done when）
上列測試綠；全套綠（環境紅見裁決 1）；改寫的既有斷言在 ledger 逐條「舊→新＋理由」。截圖由 developer-agent 補（1440／390 × zh／en），交維護者看（B 級畫面，不自動合併）。

## 環境事實
- 今天的送出：`web.py:604` 路由；`launch_choices` 437、`launch_page` 442、`launch_get` 451（`?from=` 快速送出）、`launch_post` 475；表單在 `web_board.py:803-835`（`render_launch`），參數工具 `parse_params`／`params_text` 733-770。
- `request_launch`：`actions/__init__.py:563`；`launch_prefill` 191；`list_samplesheets` 172；`list_compute_envs`／`get_compute_env`。
- `launches` 表（`store.py:253`）沒有 pipeline 欄；pipeline／revision／params 在 `confirmations.bundle_json`（`store.py:203`），取用走 `jobs.launch_content`（jobs.py:385）與 `jobs.run_forgotten`。jobs 表 `args_json` 7 天後清掉，不要用它。
- `sitePipelines`：運算環境 `config_json` 內 `[{pipeline, revision, module, home}]`（例 `configs/sites/nchc-nano4-ce.json`：nf-core/ampliseq 2.18.0）。
- 既有守門測試（`test_web_actions.py`）：tc060（535）AST 檢查 web 只能呼叫哪些 actions——executor 先讀清楚它允許的集合，新 read 若不在允許集合內，照它的規則登記（不得放寬到允許寫入動作）；tc051（492）路由路徑不得含 `upload|cost|chat|forget|samplesheet|delete`；tc063（599）不得新增表或欄；tc046-048 無 script、單一樣式表、雙語；tc040 禁字掃描。
- 平台程式目前完全不連網（`test_chat_tools.py:178` 等檢查）；本任務維持不連網。

## 不做
- 不連 GitHub：不讀 `nextflow_schema.json`／`schema_input.json`、不抓流程圖、不列 nf-core 全部管線、不查最新版本（第二刀）。
- 不改確認頁、不改 `request_launch` 與 `build.prepare_launch`、不改站台、不動右欄、不加 JS、不加資料表。
- 不做上傳頁、設定頁（012a）。

## 裁決
1. 已知環境紅 `tests/init_workspace_test.sh`「site side with no run area known fails clearly」（桌機 WSL `/work` 權限，CI 綠、base 也紅）不算本任務的紅。
2. 新 read 名稱固定 `list_used_pipelines`；回傳形狀如「作法」。
3. 步驟狀態只由網址參數決定；不新增資料表、欄位、cookie 或伺服器端 session 狀態。
4. 可改寫的既有斷言：只限 `test_web_actions.py` 中斷言「/launch 表單的版面／欄位順序／欄位所在位置」的那幾條（tc020 一類）；欄位名稱、驗證、CSRF、確認流程的斷言不得改。executor 先列 file:line 寫進 ledger 再改。另允許「工具清單／工具數」斷言加一項 `list_used_pipelines`。其他既有斷言變紅 → BLOCKED。
5. 可新增的 CSS 只限：步驟三種狀態（完成／目前外框／之後灰）與步驟編號；沿用既有顏色與間距 token，不得新增數值。
6. 第 1 步的 ✗ 不擋送出。

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
