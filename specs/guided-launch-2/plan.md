---
id: guided-launch-2
title: 引導式送出第二刀：用站台代理讀到的管線檔，打開「參數表預檢、最新版本、流程圖、樣本表欄位、參數分組表」
tier: B
kinds: ui
lane: L7-web-redesign
base: v3
after: release-lookup-job
source: DESIGN.md v2 畫面 5；guided-launch-1（#210）的「之後開放」項目；維護者 10-25「好，放寬（建議）」（站台代理讀公開 GitHub 檔）
---

# guided-launch-2

> 2026-10-27 重寫（舊版 10-25 BLOCKED：平台不准連網）。現在資料由 `release-lookup-job`（#236）提供：平台**不連網**，只呼叫動作層 `actions.pipeline_files`／`actions.latest_release`，它們排一個 `pipeline_files` 工作給呼叫者的站台代理，代理讀 GitHub、平台用 `schema.py` 解析。**本任務只做網頁**：不改 `actions/`、`schema.py`、`releases.py`、`jobs.py`、站台代理、`mcp_server.py`。
> 「搜尋全部 nf-core」維持「之後開放」：維護者已同意讀 nf-co.re/pipelines.json，但後端（nfcore-catalogue）還沒做，之後另開一刀。
> 維護者 10-23：「先把功能做起來吧，以後再改美觀」——只用現有 class 與 DESIGN.md token。

## 目標
同事填好管線與版本後，送出頁直接告訴他：這版本的參數表讀到了沒、最新版本是哪一版、流程圖長什麼樣、樣本表要哪些欄、有哪些參數（按管線自己的分組、預設值看得到，可以直接填）。送出的東西仍是同一個 `request_launch`。

## 維護者原話（verifier 出題用）
1. 「在送出的介面就要有之前abf-v2那些引導的事情，包括選擇pipline (之前設定的 or 新開的)、pipline的流程圖、pipline的參數等等。介面上不要有AI太口語化的回覆，要有制式化的通知呈現」（DESIGN.md 原話 7）
2. 「Seqera功能太多學習成本高」（原話 6）
3. 「先把功能做起來吧，以後再改美觀」（原話 15）
4. DESIGN.md 畫面 5（英文原文照抄進測試案例）：「3 Workflow diagram … 4 Samplesheet … 5 Parameters: three routes ① reuse a previous run ② defaults ③ adjust by group …」

## 範圍：檔案
- `platform/abf_platform/web_launch.py`（新檔：第 1、2、3、4、5 步新增區塊的渲染函式；`web_board.render_launch` 只加呼叫點與參數）
- `platform/abf_platform/web_board.py`（只限 `render_launch` 的呼叫點、`GUIDED` 字串鍵、樣式表加必要的 class）
- `platform/abf_platform/web.py`（`/launch` GET 取資料並傳入；`/launch` POST 只加「`p.<name>` 欄位併入參數」；新路由 `GET /launch/diagram`；檔頭路由清單 docstring）
- `platform/tests/test_web_guided_launch_2.py`（新檔）
- 既有斷言只准跟著改：`platform/tests/test_web_guided_launch.py` 裡斷言第 1 步「讀取管線參數表」、第 3 步、第 5 步分組表為「之後開放」的那幾條（改成新行為；第 2 步「搜尋全部 nf-core」與第 4 步「預覽」那兩條**不改**）；`platform/tests/test_owner_binding.py` `test_tc068` 的路由集合加 `"/launch/diagram"`。ledger 逐條「舊→新＋理由」。
- `docs/PLATFORM.md`（「The guided launch page」一節補：資料從哪來、讀取中會每 15 秒重問、`/launch/diagram`）、`docs/TESTING.md`（「引導式送出」節補第二刀手動步驟）

## 介面事實（v3，以實際程式為準）
- `actions.pipeline_files(platform_path, pipeline, revision, *, parts=None, compute_env=None, caller=None, enqueue=True)` → `{state: loading|ready|error, pipeline, revision, parts, checked_at, error, reason, schema, schema_input, diagram, image}`。預設 `parts` = schema、schema_input、diagram（不含 image）。
  - `schema`：`{status:"ok", groups:[{…, params:[{name, types, description, help_text, has_default, default, required, hidden, enum, format, pattern}]}], required_without_default:[…]}`；或 `{status:<非 ok>, message:<雙語一句>}`。
  - `schema_input`：`{status:"ok", columns:[{name, types, required, format, pattern, exists, meta, description}]}`；或同上的失敗形。
  - `diagram`：`{status:"ok", name, type: image/png|image/svg+xml, size}`、`{status:"none"}`（沒有圖）、或失敗形。
  - `image`（只在 `parts=["image"]` 時）：`{status:"ok", name, type, size, data_b64}`。
  - `state=="error"` 時 `reason` 是雙語一句、各部分為 None。它從不等待；沒有工作就排一個。
- `actions.latest_release(platform_path, pipeline, *, compute_env=None, caller=None, enqueue=True)` → `{state, pipeline, revision, source: fetched|cache|stale-cache|none, checked_at, why, error}`。
- 兩者已在 `test_web_parity.py` 登記為 WEB_ONLY，沒有 MCP 工具。測試假資料的作法見 `platform/tests/test_pipeline_files_action.py`（讓工作完成、塞代理結果），fixtures 在 `platform/tests/fixtures/schema/`、`tests/fixtures/schema_input/`。

## 作法
1. **何時呼叫**：`/launch` GET 有 `pipeline` 且有 `revision` 時，呼叫一次 `pipeline_files(..., caller=<登入者>, compute_env=<目前選的 ce_name，沒有就 None>)`（`run_in_threadpool`）。有 `pipeline`、沒有 `revision` 時，呼叫一次 `latest_release(...)`。兩者都只讀，不經確認頁。結果傳給 `render_launch`（新參數，例如 `files=`、`latest=`）。
2. **讀取中**：任一結果 `state=="loading"` 時，頁面 `<head>` 加 `<meta http-equiv="refresh" content="15">`（零 JS；15 秒與 PLATFORM.md 一致），並在對應區塊顯示制式通知「讀取中，頁面每 15 秒自動更新。」。都不是 loading 就不加 refresh。
3. **第 1 步預檢**：原本的「○ 讀取管線參數表 之後開放」換成真的檢查列：ready 且 schema ok → `✓ 讀取管線參數表 讀到 <N> 組、<M> 個參數`；loading → `… 讀取中`；error 或 schema 非 ok → `✗` ＋ `reason`／`message` 原句（雙語原句不改寫）。這一列失敗**不擋送出**，第 7 步摘要的「問題」照既有規則列出 ✗ 項。
4. **第 2 步「新管線」分頁**：手填兩欄保留；有 `pipeline` 沒 `revision` 時，在欄位下方顯示 `latest_release` 結果：ready → 「最新版本：<revision>」＋連結「使用這一版」（`_qs` 帶 pipeline 與 revision）；`source=="stale-cache"` 另加一句「目前連不到 GitHub，這是 <checked_at 台北時間> 查到的。」；loading → 讀取中；error → `✗ why`。「搜尋全部 nf-core 之後開放」原樣保留。
5. **第 3 步流程圖**：diagram ok → `<figure><a href="/launch/diagram?…"><img src="/launch/diagram?pipeline=…&revision=…" alt="<pipeline> <revision> 流程圖"></a></figure>`（點圖開原圖；`img` 以樣式表限寬 100%，不用 `style=`）；`status=="none"` → 制式通知「這條管線沒有提供流程圖。」，狀態視同完成；loading／失敗 → 讀取中／`✗ message`。還沒有 pipeline＋revision → 原本的「之後開放」改成灰字「選好管線與版本後顯示」。
6. **`GET /launch/diagram`**：要登入（臨時密碼 session 照 #234 的規則導 `/welcome`；沒登入照其他 GET 頁導 `/login`）。參數 `pipeline`、`revision`。呼叫 `pipeline_files(..., parts=["image"], caller=<登入者>, enqueue=False)`；image ok → base64 解碼、`Content-Type` 用 `image.type`、`Cache-Control: private, max-age=3600`、`X-Content-Type-Options: nosniff`；svg 另加 `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'`。不是 ok（含 loading）→ 404，本文一句純文字。⚠️ 預設 parts 的工作**不含 image**：GET `/launch` 在 diagram ok 時要另外以 `parts=["image"]`、`enqueue=True` 呼叫一次，讓圖的工作先排上；圖的工作還在讀時也算 loading（維持 15 秒 refresh），讀好後 `<img>` 才出現。
7. **第 4 步樣本表**：在 select 下方，schema_input ok 時列一張表：欄名、必填（✓／—）、說明（`description`；空的就留空，不露出正規表示式原文）。原「預覽 之後開放」保留（檔案內容在站台，不做）。loading／失敗同上。不推斷「哪欄是樣本名／R1／R2」（見「不做」）。
8. **第 5 步路線 ③ 參數分組表**：schema ok 時，在 textarea **上方**加分組表：每組一個 `<details>`（第一個不是全 hidden 的組預設展開），組內每個參數一列：名稱、說明、型別、預設值、輸入欄 `name="p.<參數名>"`（`placeholder`＝預設值；`enum` → `<select>` 含空白選項＋各值；boolean → `<select>` 空白／true／false；其他 → `<input>`）。全部 `hidden` 參數集中到最後一個 `<details>`「進階（管線預設隱藏的參數）」。`required_without_default` 的參數名旁標「必填」。這個表在第 5 步那個 GET 表單內，`p.*` 一起送回；GET 處理時把非空的 `p.*` 轉成參數文字併入 `params`：同名時 textarea 的值優先。文字格式照 `web_board.params_text` 既有格式（executor 先讀它）；轉換寫成一個純函式，有單元測試。
9. **POST `/launch`**：同樣把非空 `p.*` 併入 `params`（textarea 優先），其餘驗證與 `request_launch` 呼叫完全不變。
10. **限制**：零 JavaScript、無 `style=`、單一樣式表（新 class 只用 DESIGN.md token）、CSP 不改（圖片同源）、每人只看自己的（`caller` 一律傳登入者）、390 px 無橫向捲動（分組表在窄螢幕上下排）、英文版每個字都有、制式通知、狀態一律「符號＋文字＋顏色」。

## 失敗先行測試（新檔 `platform/tests/test_web_guided_launch_2.py`；假代理結果照 `test_pipeline_files_action.py` 的作法，用 fixtures 真檔）
- G01 第 1 步：ready → ✓ 與正確組數／參數數；loading → 「讀取中」且頁面有 `http-equiv="refresh" content="15"`；error（`network`、`not_found` 各一）→ ✗＋原句；全部 ready 時頁面**沒有** refresh。
- G02 第 2 步：有 pipeline 無 revision → 呼叫 latest_release；ready 顯示版本與「使用這一版」連結（含 pipeline 與 revision）；stale-cache 多一句；error 顯示 why；「搜尋全部 nf-core」仍是「之後開放」。
- G03 第 3 步：diagram ok＋image ready → `<img src="/launch/diagram?…">`；none → 「這條管線沒有提供流程圖。」；未選版本 → 「選好管線與版本後顯示」。
- G04 `/launch/diagram`：image ok（png fixture 位元組）→ 200、正確 Content-Type、本文等於解碼後位元組、有 nosniff；svg → 另有那條 CSP；image loading／缺 → 404；沒登入 → 導 `/login`；臨時密碼 session → 導 `/welcome`；以 bob 登入時傳給 `pipeline_files` 的 caller 是 bob。
- G05 第 4 步：ampliseq 2.18.0 schema_input → 表格欄名順序照檔案、必填標記正確；頁面不含 `pattern` 的正規表示式原文。
- G06 第 5 步：分組順序照 `allOf`；enum → select、boolean → select、hidden 集中在「進階」；`required_without_default` 標「必填」；`p.*` 欄位名正確。
- G07 `p.*` 合併：純函式單元測試（空值忽略、textarea 同名優先）；GET 帶 `p.FW_primer=AAA` → 第 7 步摘要的參數含它；POST 帶 `p.*` → `request_launch` 收到的參數含它，textarea 同名者取 textarea 的值。
- G08 英文版：`lang=en` 每個新區塊都是英文、沒有中文（使用者自己的名稱與 GitHub 原文說明除外）。
- G09 限制：新頁面無 `<script`、無 `style=`、CSP 標頭不變、只有一個樣式表；整個測試中平台沒有對外連線（monkeypatch socket 連線即失敗）。
- G10 呼叫次數：一次 GET `/launch` 最多呼叫 `pipeline_files` 兩次（預設 parts 一次、diagram ok 時 image 一次）、`latest_release` 最多一次；沒有 pipeline 時一次都不呼叫。

## 完成標準
上列測試綠；全套綠；改寫的既有斷言在 ledger 逐條列。`docs/TESTING.md` 手動步驟：站台代理在跑 → 開 `/launch?pipeline=nf-core/ampliseq&src=new` 看到最新版本 → 用那一版 → 等 15–60 秒看到 ✓ 參數表、流程圖、樣本表欄位、參數分組表 → 填一個 `p.*` → 第 7 步摘要看得到 → 送出走到確認頁（不按送出）。截圖由 developer-agent 補（1440／390 × zh／en）。

## 不做
- 「搜尋全部 nf-core」（等後端 nfcore-catalogue）。
- 推斷樣本表欄位角色（樣本名／R1／R2）、讀樣本表檔案內容做預覽、參數值驗證（型別以外）。
- 改 `actions/`、`schema.py`、`releases.py`、`jobs.py`、站台代理、`mcp_server.py`、確認頁、`request_launch`、CSP；加 JS、加資料表。

## 裁決
1. 已知只在本機環境紅、可接受：`tests/init_workspace_test.sh` 的「site side with no run area known fails clearly」；`test_port_race.py`、`jev_test.sh`、`confirm_launch_test.sh` 在本機 WSL 時好時壞（以 CI 為準）。
2. 15 秒自動更新會清掉使用者正在 textarea 打、還沒送出的字：可接受（只在讀取中、通常 1 分鐘內結束）；讀取中時第 5 步 textarea 上方加一句「讀取中頁面會自動更新，請等讀完再填參數。」
3. 流程圖若是 `.svg`：照作法 6 的標頭從同源路由送出，以免 svg 內的 script 執行。

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
