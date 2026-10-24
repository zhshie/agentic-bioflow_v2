---
id: guided-launch-2
title: 引導式送出第二刀：平台讀管線的 nextflow_schema／schema_input（新 schema.py，有快取）、流程圖、「全部 nf-core」搜尋、參數分組表、樣本表欄位與角色
tier: B
kinds: ui, backend
lane: L7-web-redesign
base: v3
source: DESIGN.md v2 畫面 5；總表 012b-2；guided-launch-1（#210）的「之後開放」項目
---

# guided-launch-2

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/guided-launch-2/plan.md`。**只處理本任務**。前置：guided-launch-1（#210）已合併——它把第 1 步「讀取管線參數表」、第 2 步「搜尋全部 nf-core」、第 3 步流程圖、第 4 步預覽與欄位角色、第 5 步參數分組表標成「之後開放」。本任務把這五個打開。
> 維護者 10-23：「先把功能做起來吧，以後再改美觀」——只用現有 class 與 DESIGN.md token。

## 目標
同事選好管線後，頁面直接告訴他：這條管線的流程圖長什麼樣、樣本表要哪些欄、哪一欄是樣本名、哪兩欄是 R1／R2、有哪些參數（按管線自己的分組列出、預設值看得到）。沒用過的管線可以從 nf-core 全部清單裡搜。送出的東西仍是同一個 `request_launch`。

## 維護者原話（verifier 出題用）
1. 「在送出的介面就要有之前abf-v2那些引導的事情，包括選擇pipline (之前設定的 or 新開的)、pipline的流程圖、pipline的參數等等。介面上不要有AI太口語化的回覆，要有制式化的通知呈現」（DESIGN.md 原話 7）
2. 「Seqera功能太多學習成本高」（原話 6）
3. 「先把功能做起來吧，以後再改美觀」（原話 15）
4. DESIGN.md 畫面 5（英文原文照抄進測試案例）：「2 Pipeline: tabs "Used before" … and "New pipeline (all nf-core)" … 3 Workflow diagram … 4 Samplesheet … 5 Parameters: three routes ① reuse a previous run ② defaults ③ adjust by group …」

## 範圍：檔案
- `platform/abf_platform/schema.py`（新檔：抓取＋快取＋解析）
- `platform/abf_platform/web_launch.py`（新檔：第 1–5 步新增區塊的渲染；`web_board.render_launch` 只加呼叫點）
- `platform/abf_platform/web_board.py`（只限 `render_launch` 的呼叫點與字串鍵）
- `platform/abf_platform/web.py`（`/launch` GET 傳入 schema 結果；POST 只加「`p.<name>` 欄位併入參數」；新增一條路由 `GET /launch/diagram` 回快取的圖檔）
- `platform/abf_platform/actions/__init__.py`（新 read：`get_pipeline_schema`、`search_pipelines`）
- `platform/abf_platform/mcp_server.py`（同名兩個 read tool，parity 要求）
- `platform/tests/test_schema.py`、`platform/tests/test_web_guided_launch_2.py`（新檔）
- 「工具清單／工具數」釘死斷言（只加這兩項，ledger 逐條列）
- `docs/PLATFORM.md`（一段：schema 從哪裡抓、快取在哪、離線時怎樣）、`docs/TESTING.md`（「引導式送出」節補第二刀手動步驟）

## 作法
**`schema.py`（唯一連網的地方）**
- `fetch(url, *, timeout=10) -> bytes`：`urllib.request`，User-Agent 固定字串；只允許 `https://raw.githubusercontent.com/`、`https://api.github.com/repos/`、`https://nf-co.re/` 三個前綴，其他一律拒絕。
- 快取：`<platform_path>/cache/schema/<owner>__<repo>/<revision>/<檔名>`；指定版本（tag 或 sha）的檔案永久有效；`nf-co.re/pipelines.json` 24 小時。讀不到網路時用快取；都沒有 → 回結構化的 `unavailable` 與原因，不丟例外。
- 取得：`nextflow_schema.json`、`assets/schema_input.json`（raw.githubusercontent.com/<pipeline>/<revision>/…）；流程圖：GitHub contents API 列 `docs/images`，取第一個檔名含 `metro` 或 `workflow` 的 `.png`／`.svg`（都沒有 → 無圖）。
- 解析：nextflow_schema 的 `$defs`（舊版 `definitions`）依 `allOf` 順序成分組 `{title, description, params:[{name, type, default, description, required, hidden, enum}]}`；`hidden: true` 的參數預設收進「進階」。schema_input 欄位清單＋角色：**重用 `scripts/utils/schema_roles.py` 的規則**（`infer_roles`），不重寫第二套——用 import 或把它搬進平台套件再讓 scripts 端 import 平台版，二選一，ledger 說明。
- 可注入的 fetcher（測試用，`schema.FETCH` 或參數），**測試一律不連真網路**；用 `tests/fixtures/schema_input/` 的真檔，nextflow_schema 另存一份 ampliseq 2.18.0 真檔進 fixtures（下載原檔、不改）。

**新 read（動作層唯一入口，網頁與 MCP 共用）**
- `get_pipeline_schema(platform_path, pipeline, revision, *, caller)` → `{"status": "ok"|"unavailable", "reason", "groups", "input_columns", "roles": {sample, read1, read2} | {"needs_decision": {role, candidates}}, "diagram": bool}`。
- `search_pipelines(platform_path, q, *, caller)` → `{"pipelines": [{name, description, latest_release}]}`，來源 `nf-co.re/pipelines.json`，名稱或描述含 q（不分大小寫），最多 30 筆；q 空 → 全部按名稱排序。

**頁面改動**
1. 第 1 步「讀取管線參數表」：✓（讀到）／✗＋原因（讀不到；不擋送出，第 7 步摘要重列）。
2. 第 2 步「新管線」分頁：GET 搜尋框 `q`＋結果表（名稱、描述、最新版本、「選擇」連結帶 `pipeline` 與 `revision=最新版本`）；仍保留手填兩欄。
3. 第 3 步流程圖：有圖 → `<img src="/launch/diagram?pipeline=…&revision=…" alt="…流程圖">`，大圖可點開原圖；無圖 → 制式通知「這條管線沒有提供流程圖。」狀態視同完成、不擋後續。
4. 第 4 步樣本表：在 select 下列出這條管線要的欄位（必填標記）與推斷出的角色（樣本名／R1／R2）；推斷不出 → 制式通知列出候選欄位。不讀樣本表檔案內容（內容在站台，見「不做」）。
5. 第 5 步路線 ③：參數分組表（每組一個 `<details>`，非 hidden 組展開第一組），每個參數一列：名稱、說明、型別、預設值、輸入欄 `name="p.<參數名>"`（placeholder＝預設值；enum → `<select>`；boolean → `<select>` true／false／未設定）。原本的 textarea 保留在表下方當「其他參數」。
   POST：非空的 `p.*` 欄位併入參數（同名時 textarea 的值優先），其餘驗證、`request_launch` 呼叫完全不變。

**不能放掉的限制**：零 JavaScript、無 `style=`、單一樣式表（CSP 雜湊）、每人只看自己的、390 px 無橫向捲動（分組表在窄螢幕變成上下排）、英文版每個字都有、制式通知。既有 `test_web_actions.py` 的 tc046–048、tc051、tc060、tc063、tc040 全部繼續綠；`test_chat_tools.py` tc035（chat_tools 模組不連網）不受影響——連網只在 `schema.py`。

## 失敗先行測試
`platform/tests/test_schema.py`：
- `test_sc01_only_three_url_prefixes`：其他網址 → 拒絕、沒有發出請求。
- `test_sc02_cache_hit_needs_no_network`：抓過一次後換成會丟例外的 fetcher，仍回同樣結果；pipelines.json 超過 24 小時才重抓。
- `test_sc03_offline_without_cache_is_unavailable_not_exception`。
- `test_sc04_groups_from_real_ampliseq_schema`：分組順序照 `allOf`、hidden 參數標記、default 正確。
- `test_sc05_roles_match_schema_roles_rules`：五份 fixtures 各自的角色與 `scripts/utils/schema_roles.py` 的結果一致（同一套規則）。
- `test_sc06_diagram_pick`：contents 清單含 metro png → 選它；沒有 → 無圖。
`platform/tests/test_web_guided_launch_2.py`（用既有 World 與 seed，fetcher 注入 fixtures）：
- `test_gl2_01_precheck_schema_ok_and_unavailable`
- `test_gl2_02_search_nfcore_filters_and_links_latest_release`
- `test_gl2_03_diagram_img_and_route_serves_cached_bytes`（content-type 正確；未登入 → 轉登入頁）
- `test_gl2_04_no_diagram_notice`
- `test_gl2_05_samplesheet_columns_and_roles`／`test_gl2_06_roles_need_decision_notice`
- `test_gl2_07_param_group_table_inputs`（enum、boolean、hidden 進階）
- `test_gl2_08_post_merges_p_fields_textarea_wins`：`p.FW_primer=AAA` → bundle 參數含之；textarea 同名 → textarea 值。
- `test_gl2_09_english`、`test_gl2_10_constraints_hold`（無 script、無 style=、CSP、無口語句）
- `test_gl2_11_actions_and_mcp_match`：兩個新 read 動作層與 MCP 回同樣內容。

## 完成標準（done when）
上列測試綠；全套綠（環境紅見裁決 1）；改寫的既有斷言在 ledger 逐條「舊→新＋理由」。截圖由 developer-agent 補（1440／390 × zh／en）。

## 環境事實
- guided-launch-1 合併後的頁面：`web_board.render_launch`、`web.py` 的 `/launch` GET／POST；`list_used_pipelines` 在 `actions/__init__.py`。executor 先讀合併後的實際程式，以它為準。
- 既有規則碼：`scripts/utils/schema_roles.py`（`schema_properties`、`infer_roles`、`NeedsDecision`）；fixtures `tests/fixtures/schema_input/*.json`（真檔、不改）。
- CSP 在 `web.py`（找 `Content-Security-Policy`）；圖片走同源路由 `/launch/diagram`，**不改 CSP**。
- 守門測試：tc060 web 能呼叫的 actions 白名單（新 read 照它的規則登記，不得放寬到寫入動作）；tc051 路由不得含 `upload|cost|chat|forget|samplesheet|delete`（`/launch/diagram` 合規）；tc063 不得新增表或欄（快取是檔案，不是表）。

## 不做
- 不讀樣本表檔案內容做預覽（檔案在站台；要站台代理新動作，屬後端車道，之後另開）。
- 不查「是否有更新版本」提醒、不做參數值驗證（型別以外）、不改確認頁、不改 `request_launch`、不改 CSP、不加 JS、不加資料表。

## 裁決
1. 已知只在本機環境紅、可接受：`tests/init_workspace_test.sh` 的「site side with no run area known fails clearly」。
2. 工具清單／工具數斷言若與其他車道（settings-page 的 `list_my_tokens`、cost-page 的 `my_usage`）同時加工具：照本計畫只加兩項；合併衝突由 developer-agent 解。
3. 流程圖若 GitHub 上是 `.svg`：照原樣以 `image/svg+xml` 從同源路由送出，回應加 `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'` 與 `X-Content-Type-Options: nosniff`，以免 svg 內的 script 執行。

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
