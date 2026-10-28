# 測試案例：引導式送出第二刀（`/launch` 預檢、最新版本、流程圖連結、樣本表欄位、參數分組表）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
來源：`specs/guided-launch-2/plan.md`（本任務沒有獨立的 spec.md，計畫即規格；計畫「裁決」一節與上文衝突時以裁決為準）。
維護者指示：測試案例只能來自計畫裡的例子，不自創計畫沒說的行為。計畫沒說的事不寫成 TC，記在總覽「我不確定的地方」。
維護者原話共四條（計畫「維護者原話」）：見 TC-001、TC-063、TC-096、TC-097、TC-098。
-->

**規格**：`specs/guided-launch-2/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## 本檔用的說法

- **ann、bob**：兩位不同的登入使用者；除非另外寫，操作者都是 ann。
- **P／R**：管線 `nf-core/ampliseq`、版本 `2.18.0`。「帶 P 與 R」＝網址 `/launch?pipeline=nf-core/ampliseq&revision=2.18.0`。
- **站台代理**：替使用者去 GitHub 讀管線檔案的小程式；平台自己不連網。測試用「假代理結果」代替（讓工作完成、塞入 fixtures 真檔的內容，作法照 `platform/tests/test_pipeline_files_action.py`）。
- **fixtures**：`platform/tests/fixtures/schema/`（參數表）與 `tests/fixtures/schema_input/`（樣本表欄位）裡的真檔。
- **pipeline_files／latest_release**：平台內部兩個「讀管線檔案」「查最新版本」的動作，回傳狀態 `loading`（讀取中）／`ready`（讀好）／`error`（失敗）。
- **步驟區塊**：頁面上編號 1 到 7 的 `<details>`。**狀態**有三種：done（✓、收合）、current（展開、有外框）、later（收合、灰）。
- **制式通知**：固定句子，不是對話口吻。
- **狀態列**：以符號開頭的一行：`✓`（成功）、`✗`（失敗）、`…`（讀取中）、`○`（尚未檢查）。每一列必須「符號＋文字」並用，顏色另加。
- **雙語原句**：代理或動作層回來的 `reason`／`message`／`why` 長得像 `中文 (English)`；中文頁只顯示中文那半，英文頁只顯示英文那半（計畫裁決 5，經 `web_board.plain_reason`）。
- 驗證方式「自動」＝ `platform/tests/test_web_guided_launch_2.py`（新檔），除非另外寫明；每條測試要在註解寫上它的 TC 編號。「手動」＝ `docs/TESTING.md`「引導式送出」節新增的第二刀步驟，或閱卷者看 git diff。

## User Story 1 — 第 1 步：參數表預檢與「讀取中」自動更新（優先度 P1）

維護者原話 1（DESIGN.md 原話 7）：「在送出的介面就要有之前abf-v2那些引導的事情，包括選擇pipline (之前設定的 or 新開的)、pipline的流程圖、pipline的參數等等。介面上不要有AI太口語化的回覆，要有制式化的通知呈現」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 1（pipline 的參數）；作法 3；G01 | 功能 | 假代理結果：P／R 的參數表讀好（ready，schema ok，用 ampliseq 2.18.0 的 fixture） | ann 開啟帶 P 與 R 的 `/launch` | 第 1 步有一列 `✓ 讀取管線參數表 讀到 N 組、M 個參數`，N、M 等於該 fixture 實際的組數與參數數（測試自己從 fixture 算，不寫死） | 自動 |
| TC-002 | 作法 3；G01 | 功能 | 同上但工作還在讀（loading） | ann 開啟同一頁 | 第 1 步那一列是 `… 讀取中`（符號加文字） | 自動 |
| TC-003 | 作法 3；裁決 5；G01 | 例外 | 假代理結果：state 為 error，錯誤類別 `network`，reason 是 `中文 (English)` 兩半的一句 | ann 在中文頁開啟 | 第 1 步那一列是 `✗ 讀取管線參數表` 加 reason 的**中文那半**；不出現英文那半 | 自動 |
| TC-004 | 作法 3；G01 | 例外 | 假代理結果：state 為 error，錯誤類別 `not_found` | ann 開啟 | 同 TC-003：`✗` 加該 reason 的中文半句 | 自動 |
| TC-005 | 作法 3；G01 | 例外 | 假代理結果：state 為 ready，但 schema 的 status 不是 ok，帶一句 message | ann 開啟 | 第 1 步那一列是 `✗` 加該 message 的中文半句（不是 ✓） | 自動 |
| TC-006 | 作法 2；G01 | 功能 | 假代理結果：全部 ready | ann 開啟 | 頁面 `<head>` 沒有 `http-equiv="refresh"` | 自動 |
| TC-007 | 裁決 9（未寫明的狀態） | 功能 | 網址有 `pipeline` 但沒有 `revision` | ann 開啟 | 第 1 步那一列是 `○ 讀取管線參數表　選好版本後檢查`；不是 ✗；第 7 步摘要的「問題」不含這一項；`pipeline_files` 沒被呼叫 | 自動 |
| TC-008 | 作法 3；裁決 9 | 例外 | 第 1 步那一列是 ✗（如 TC-003） | 看第 7 步摘要 | 「問題」依既有規則列出該 ✗ 項 | 自動 |
| TC-009 | 作法 3「這一列失敗不擋送出」 | 例外 | 第 1 步那一列是 ✗；其餘必填欄位都填好 | ann 按送出（POST `/launch`） | 仍然走到確認頁（沒有被這個 ✗ 擋住） | 自動 |
| TC-010 | 作法 2；原話 1（制式通知）；G01 | 功能 | 任一結果是 loading | ann 開啟 | `<head>` 有 `<meta http-equiv="refresh" content="15">`，且對應區塊出現制式通知「讀取中，頁面每 15 秒自動更新。」（逐字） | 自動 |
| TC-011 | 裁決 2 | 功能 | 任一結果是 loading | ann 看第 5 步 | textarea 上方有一句「讀取中頁面會自動更新，請等讀完再填參數。」（逐字），textarea 仍可用 | 自動 |
| TC-012 | 裁決 2 | 功能 | 全部 ready | ann 看第 5 步 | 沒有上面那句「讀取中頁面會自動更新……」 | 自動 |
| TC-013 | 作法 1；G10（空狀態） | 功能 | 網址沒有 `pipeline` | ann 開啟 `/launch` | `pipeline_files` 與 `latest_release` 一次都沒被呼叫；頁面沒有 refresh | 自動 |

## User Story 2 — 第 2 步「新管線」：最新版本（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 作法 1、4；G02、G10 | 功能 | 網址 `src=new`，有 `pipeline=nf-core/ampliseq`，沒有 `revision`；ann 登入 | 開啟頁面 | `latest_release` 被呼叫一次且 caller 是 ann；`pipeline_files` 沒被呼叫 | 自動 |
| TC-015 | 作法 4；G02 | 功能 | 假代理結果：latest_release ready，revision 為 `2.18.0` | 開啟頁面 | 兩個手填欄位下方出現「最新版本：2.18.0」 | 自動 |
| TC-016 | 作法 4；G02 | 功能 | 同 TC-015 | 看「使用這一版」連結 | 連結存在，網址含 `pipeline=nf-core/ampliseq` 與 `revision=2.18.0`；跟著連結走，新頁面的版本已帶入 | 自動 |
| TC-017 | 作法 4 | 功能 | 假代理結果：source 是 fetched 或 cache（不是 stale-cache） | 開啟頁面 | 沒有「目前連不到 GitHub」那句 | 自動 |
| TC-018 | 作法 4；G02 | 功能 | 假代理結果：source 為 `stale-cache`，checked_at 是一個已知時間 | 開啟頁面 | 除最新版本外多一句「目前連不到 GitHub，這是 <時間> 查到的。」，<時間> 是 checked_at 換成**台北時間**（UTC+8）的結果 | 自動 |
| TC-019 | 作法 2、4；G02 | 功能 | 假代理結果：latest_release 是 loading | 開啟頁面 | 該區塊顯示讀取中（符號加文字），頁面有 refresh 15 | 自動 |
| TC-020 | 作法 4；裁決 5；G02 | 例外 | 假代理結果：latest_release 是 error，why 是雙語一句 | 開啟頁面（中文） | 顯示 `✗` 加 why 的中文半句 | 自動 |
| TC-021 | 作法 4「手填兩欄保留」 | 功能 | 「新管線」分頁 | 看頁面 | 管線與版本兩個手填欄位仍在、可輸入 | 自動 |
| TC-022 | 作法 4；「不做」第 1 條；G02 | 不在範圍 | 「新管線」分頁 | 看頁面 | 「搜尋全部 nf-core」仍標示「之後開放」，沒有搜尋功能；`test_web_guided_launch.py` 裡這條斷言沒被改 | 自動 |
| TC-023 | 裁決 11 | 功能 | 網址 `src=used`，有 `pipeline` 沒 `revision` | 開啟頁面 | `latest_release` 沒被呼叫 | 自動 |
| TC-024 | 作法 1 | 功能 | 網址同時有 `pipeline` 與 `revision` | 開啟頁面 | `latest_release` 沒被呼叫（改呼叫 `pipeline_files`） | 自動 |

## User Story 3 — 第 3 步：流程圖（連結形式）與 `/launch/diagram`（優先度 P1）

維護者原話 1 的「pipline的流程圖」與 DESIGN.md 畫面 5 原文（英文照抄）：「3 Workflow diagram … 4 Samplesheet … 5 Parameters: three routes ① reuse a previous run ② defaults ③ adjust by group …」。依計畫裁決 4，圖**不內嵌**（現行 CSP 會擋 `<img>`，CSP 不改），改顯示檔名＋大小＋連結。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 裁決 4、9；DESIGN 畫面 5「3 Workflow diagram」 | 功能 | 假代理結果：diagram ok（有 `name`、`size`），圖檔工作（parts=image）也 ready | 帶 P 與 R 開啟 | 第 3 步顯示圖檔名（`diagram.name`）、大小，與連結「開啟流程圖」，連結指向 `/launch/diagram?pipeline=nf-core/ampliseq&revision=2.18.0`（含 pipeline 與 revision） | 自動 |
| TC-026 | 裁決 9 | 功能 | 同 TC-025 | 看第 3 步標記 | 狀態是 done（✓、收合） | 自動 |
| TC-027 | 裁決 4 | 不在範圍 | 同 TC-025 | 檢查整頁 HTML | 沒有 `<img` 與 `<figure>`（圖不內嵌） | 自動 |
| TC-028 | 作法 5；裁決 9；G03 | 功能 | 假代理結果：diagram 的 status 是 `none` | 開啟頁面 | 第 3 步顯示制式通知「這條管線沒有提供流程圖。」，狀態視同完成（done） | 自動 |
| TC-029 | 作法 5；裁決 9 | 功能 | 假代理結果：diagram 部分仍在讀（loading） | 開啟頁面 | 第 3 步顯示讀取中（符號加文字），標記是 later，頁面有 refresh 15 | 自動 |
| TC-030 | 作法 5；裁決 5、9 | 例外 | 假代理結果：diagram 部分失敗，帶雙語 message | 開啟頁面（中文） | 第 3 步標記 later，顯示 `✗` 加 message 的中文半句 | 自動 |
| TC-031 | 作法 6；裁決 9 | 功能 | diagram ok，但 `parts=["image"]` 的工作仍在讀 | 開啟頁面 | 「開啟流程圖」連結不出現，改顯示「圖檔讀取中」；頁面有 refresh 15 | 自動 |
| TC-032 | 裁決 9 | 例外 | diagram ok，但 `parts=["image"]` 回 error（或 image 非 ok），帶 message | 開啟頁面 | 「開啟流程圖」連結不出現，改顯示 `✗` 加該 message | 自動 |
| TC-033 | 作法 5；G03 | 功能 | 網址沒有 pipeline 或沒有 revision | 開啟頁面 | 第 3 步是灰字「選好管線與版本後顯示」，不再有「之後開放」 | 自動 |
| TC-034 | 作法 6；G10 | 功能 | diagram ok | 開啟頁面並記錄呼叫 | `pipeline_files` 共兩次：一次預設 parts、一次 `parts=["image"]` 且 `enqueue=True`；diagram 是 none 時沒有第二次 | 自動 |
| TC-035 | 作法 6；G04 | 功能 | image ready，內容是 png fixture 的位元組；ann 登入 | ann GET `/launch/diagram?pipeline=…&revision=…` | 200；Content-Type 是 `image/png`；本文逐位元組等於解碼後的 png | 自動 |
| TC-036 | 作法 6；G04 | 功能 | 同 TC-035 | 看回應標頭 | 有 `X-Content-Type-Options: nosniff` 與 `Cache-Control: private, max-age=3600` | 自動 |
| TC-037 | 作法 6；裁決 3；G04 | 功能 | image ready，type 是 `image/svg+xml` | ann GET 同路由 | Content-Type 是 `image/svg+xml`，且標頭有 `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'`（逐字） | 自動 |
| TC-038 | 作法 6；G04 | 例外 | image 仍是 loading | ann GET 同路由 | 404，本文是一句純文字（不是網頁） | 自動 |
| TC-039 | 作法 6；G04 | 例外 | image 工作缺（沒有結果）或 error | ann GET 同路由 | 404，本文一句純文字 | 自動 |
| TC-040 | 作法 6；G04 | 例外 | 沒登入 | GET `/launch/diagram` | 導到 `/login` | 自動 |
| TC-041 | 作法 6（#234 規則）；G04 | 例外 | 以臨時密碼登入的 session | GET `/launch/diagram` | 導到 `/welcome` | 自動 |
| TC-042 | 作法 6；「每人只看自己的」；G04 | 功能 | bob 登入 | bob GET `/launch/diagram` | 傳給 `pipeline_files` 的 caller 是 bob，參數 `parts=["image"]`、`enqueue=False` | 自動 |
| TC-043 | 裁決 10；DESIGN 畫面 5 其餘項目 | 不在範圍 | 任何有圖或沒圖的狀態 | 看第 3、5 步 | 沒有 README 階段清單、沒有劃線的跳過階段、沒有「將執行的階段」、組別表沒有「本次值」欄；圖說只有檔名 | 自動 |

## User Story 4 — 第 4 步：樣本表欄位（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-044 | 作法 7；G05；DESIGN「4 Samplesheet」 | 功能 | 假代理結果：schema_input ok，用 ampliseq 2.18.0 的 fixture | ann 開啟帶 P 與 R 的頁面 | 第 4 步 select 下方有一張表，欄名順序與 fixture 檔案裡的順序一致 | 自動 |
| TC-045 | 作法 7；G05 | 功能 | 同上 | 看「必填」欄 | 該欄必填者顯示 ✓，非必填顯示 —，與 fixture 的 required 一致 | 自動 |
| TC-046 | 作法 7 | 功能 | 同上，fixture 裡有 description 的欄與沒有 description 的欄 | 看「說明」欄 | 有 description 者顯示該說明；沒有者留空 | 自動 |
| TC-047 | 作法 7；G05 | 功能 | 同上，fixture 欄位有 `pattern` | 檢查整頁 HTML | 頁面不含任何 `pattern` 的正規表示式原文 | 自動 |
| TC-048 | 作法 7 | 功能 | 同上 | 看表頭 | 表頭恰好是「欄名、必填、說明」三欄 | 自動 |
| TC-049 | 作法 7 | 功能 | 同上 | 看位置 | 表在第 4 步的樣本表 select 之後（下方） | 自動 |
| TC-050 | 作法 7；裁決 9 | 功能 | schema_input 部分仍在讀 | 開啟頁面 | 第 4 步顯示讀取中（符號加文字），頁面有 refresh 15 | 自動 |
| TC-051 | 作法 7；裁決 5 | 例外 | schema_input 部分失敗，帶雙語 message | 開啟頁面（中文） | 第 4 步顯示 `✗` 加 message 的中文半句，沒有表 | 自動 |
| TC-052 | 作法 7；「不做」第 2 條 | 不在範圍 | 第 4 步 | 看頁面 | 「預覽」仍標示「之後開放」，沒有讀樣本表檔案內容；`test_web_guided_launch.py` 裡這條斷言沒被改 | 自動 |
| TC-053 | 「不做」第 2 條 | 不在範圍 | 同 TC-044 | 看表 | 沒有「樣本名／R1／R2」之類的欄位角色標示（只列 schema_input 的欄名、必填、說明） | 自動 |

## User Story 5 — 第 5 步：參數分組表與 `p.*` 併入參數（優先度 P1）

DESIGN.md 畫面 5 原文：「5 Parameters: three routes ① reuse a previous run ② defaults ③ adjust by group …」；本刀做的是路線 ③「按管線自己的分組調整」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-054 | 作法 8；G06 | 功能 | schema ok（ampliseq 2.18.0 fixture） | 開啟頁面 | 第 5 步 textarea 上方有分組表：每組一個 `<details>`，順序與 schema 的 `allOf` 一致 | 自動 |
| TC-055 | 作法 8 | 功能 | 同上 | 看展開狀態 | 第一個「不是全部 hidden」的組預設展開，其他組收合 | 自動 |
| TC-056 | 作法 8；G06 | 功能 | 同上 | 看一個參數列 | 該列有名稱、說明、型別、預設值，與輸入欄 `name="p.<參數名>"`；輸入欄的 `placeholder` 等於預設值 | 自動 |
| TC-057 | 作法 8 | 功能 | 參數有 `enum` | 看該列輸入欄 | 是 `<select>`，含空白選項與每個 enum 值 | 自動 |
| TC-058 | 作法 8 | 功能 | 參數型別是 boolean | 看該列輸入欄 | 是 `<select>`，選項為空白、true、false | 自動 |
| TC-059 | 作法 8 | 功能 | 參數是其他型別（字串、整數、數字） | 看該列輸入欄 | 是 `<input>` | 自動 |
| TC-060 | 作法 8；G06 | 功能 | schema 中有 `hidden` 的參數 | 看分組表 | 所有 hidden 參數出現在最後一個 `<details>`，標題「進階（管線預設隱藏的參數）」 | 自動 |
| TC-061 | 作法 8；G06 | 功能 | schema 的 `required_without_default` 列有參數名 | 看分組表 | 這些參數名旁標「必填」；不在清單內的參數沒有此標記 | 自動 |
| TC-062 | 作法 8 | 功能 | schema ok | 檢查 HTML 結構 | 分組表在第 5 步那個 GET 表單裡面、在 textarea 之前 | 自動 |
| TC-063 | 原話 4（DESIGN 畫面 5 三條路線）；作法 8 | 功能 | schema ok | 看第 5 步 | 三條路線（① 沿用前次、② 預設值、③ 按組調整）的選項仍在，分組表屬於路線 ③ 的內容 | 自動 |
| TC-064 | 裁決 9 | 功能 | schema 部分仍在讀 | 看第 5 步 | 分組表位置顯示「讀取中」（符號加文字），textarea 可用 | 自動 |
| TC-065 | 裁決 5、9 | 例外 | schema 失敗（或 state error），帶雙語 message | 看第 5 步（中文） | 分組表位置顯示 `✗` 加 message 的中文半句；textarea 照常可用 | 自動 |
| TC-066 | 裁決 9 | 功能 | 沒有 revision（schema 尚未讀） | 看第 5 步 | 分組表位置一行灰字「參數分組表：讀到參數表後顯示」，不再有「之後開放」；textarea 可用 | 自動 |
| TC-067 | 作法 8；G07 | 功能 | 純函式（把 `p.*` 轉成參數文字併入 params）單元測試：輸入含空字串的 `p.*` | 呼叫函式 | 空值被忽略，不產生任何參數 | 自動 |
| TC-068 | 作法 8；G07 | 功能 | 同一個參數名同時出現在 textarea 與 `p.*`，值不同 | 呼叫函式 | 結果取 textarea 的值 | 自動 |
| TC-069 | 裁決 6 | 功能 | 參數型別含 `integer`，`p.*` 值為 `"5"` | 呼叫函式 | 輸出的參數文字是不加引號的整數 5 | 自動 |
| TC-070 | 裁決 6 | 功能 | 參數型別含 `number`，`p.*` 值為 `"0.5"` | 呼叫函式 | 輸出是不加引號的數字 0.5 | 自動 |
| TC-071 | 裁決 6 | 功能 | 參數型別含 `boolean`，`p.*` 值為 `"true"`（再測 `"false"`） | 呼叫函式 | 輸出是布林 true（false 同理），不加引號 | 自動 |
| TC-072 | 裁決 6 | 功能 | 參數型別是字串，`p.*` 值為 `AAA`，另一個字串參數值長得像數字（如 `123`） | 呼叫函式 | `AAA` 依 `params_text` 既有格式輸出；像數字的字串依既有規則加引號，維持字串 | 自動 |
| TC-073 | 裁決 6 | 例外 | 參數型別含 `integer`，`p.*` 值為 `abc`（轉不了） | 呼叫函式 | 保留成字串，不報錯、不丟掉 | 自動 |
| TC-074 | 作法 8；G07 | 功能 | 網址帶 `p.FW_primer=AAA` | ann 開啟 `/launch`（GET） | 第 7 步摘要的參數含 `FW_primer: AAA` | 自動 |
| TC-075 | 作法 9；G07 | 功能 | POST `/launch` 帶 `p.FW_primer=AAA`，其餘必填都有 | ann 送出 | `request_launch` 收到的參數含 `FW_primer`＝`AAA` | 自動 |
| TC-076 | 作法 9；G07 | 功能 | POST 帶 `p.FW_primer=AAA`，textarea 也寫 `FW_primer: BBB` | ann 送出 | `request_launch` 收到的 `FW_primer` 是 `BBB`（textarea 優先） | 自動 |
| TC-077 | 裁決 7；G07 | 功能 | radio 勾路線 ②（預設值），同時 `p.FW_primer=AAA` | ann 送出（GET 或 POST） | 路線視為 ③（custom），`FW_primer` 的值保留，沒有被清空 | 自動 |
| TC-078 | 裁決 7 | 功能 | radio 勾路線 ②，沒有任何非空 `p.*` | ann 送出 | params 被清空（既有行為不變） | 自動 |
| TC-079 | 作法 8、9 | 功能 | 所有 `p.*` 欄都是空的（只有 placeholder 的預設值） | ann 送出 | 沒有任何參數因此被加進 params（預設值不會被當成使用者填的） | 自動 |
| TC-080 | 作法 9「其餘驗證與 request_launch 呼叫完全不變」 | 功能 | POST 不帶任何 `p.*` | ann 送出 | 驗證結果與傳給 `request_launch` 的內容和第二刀之前一致（既有送出測試仍綠） | 自動 |
| TC-081 | 「不做」第 2 條（型別以外不驗證） | 不在範圍 | `p.*` 填了不在 enum 內、或不符 `pattern` 的值 | ann 送出 | 沒有被這一刀拒絕，值照樣併入 params（只做型別轉換） | 自動 |

## User Story 6 — 全頁規則：英文版、前端限制、呼叫次數、原話、文件與範圍（優先度 P2）

維護者原話 2：「Seqera功能太多學習成本高」；原話 3：「先把功能做起來吧，以後再改美觀」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-082 | 作法 10；G08 | 功能 | `lang=en`，第 1 步三種狀態（ready／loading／error） | 開啟頁面 | 第 1 步新增的各列與通知全是英文，不含中文字 | 自動 |
| TC-083 | G08 | 功能 | `lang=en`，第 2 步最新版本（ready／stale-cache／loading／error） | 開啟頁面 | 該區塊每個字都是英文，不含中文字 | 自動 |
| TC-084 | G08 | 功能 | `lang=en`，第 3 步（連結／none／讀取中／失敗） | 開啟頁面 | 該區塊每個字都是英文，不含中文字 | 自動 |
| TC-085 | G08 | 功能 | `lang=en`，第 4 步樣本表 | 開啟頁面 | 表頭與通知是英文，不含中文字 | 自動 |
| TC-086 | G08 | 功能 | `lang=en`，第 5 步分組表與提示句 | 開啟頁面 | 表頭、「必填」標記、「進階」標題、提示句皆為英文（使用者自己的名稱與 GitHub 原文說明除外） | 自動 |
| TC-087 | 裁決 5；G08 | 例外 | `lang=en`，reason／message／why 是 `中文 (English)` | 開啟頁面 | 顯示 reason 的英文半句，不出現中文半句 | 自動 |
| TC-088 | 作法 10；G09 | 功能 | 任何含新區塊的 `/launch` 頁 | 檢查 HTML | 沒有 `<script` | 自動 |
| TC-089 | 作法 10；G09 | 功能 | 同上 | 檢查 HTML | 沒有 `style=` 屬性 | 自動 |
| TC-090 | 作法 10；G09 | 功能 | 同上 | 檢查 HTML | 只有一個樣式表（沒有新增第二個 `<style>` 或 `<link rel=stylesheet>`） | 自動 |
| TC-091 | 作法 10；「不做」第 3 條；G09 | 功能 | 同上 | 比對 `/launch` 回應的 `Content-Security-Policy` | 與第二刀之前逐字相同（沒有加 `img-src` 等） | 自動 |
| TC-092 | G09 | 功能 | 測試把 socket 連線設成一連就失敗 | 跑整個第二刀測試檔 | 全部通過，即平台沒有對外連線 | 自動 |
| TC-093 | G10 | 功能 | 有 pipeline 與 revision，diagram ok | 一次 GET `/launch` | `pipeline_files` 最多呼叫兩次、`latest_release` 最多一次 | 自動 |
| TC-094 | 專長守則（狀態不只靠顏色） | 功能 | 渲染 ✓、✗、…、○ 各狀態的 HTML | 檢查每條狀態列 | 每條都同時含符號與文字，不是只靠 class 顏色 | 自動 |
| TC-095 | 作法 10（每人只看自己的） | 功能 | ann、bob 各自登入開 `/launch` | 各開一次並記錄呼叫 | 傳給 `pipeline_files`／`latest_release` 的 caller 分別是 ann、bob | 自動 |
| TC-096 | 原話 3；作法 10 | 功能 | 檢視新增的樣式表規則 | 掃描新 class 的宣告 | 顏色、字型、間距等只用 DESIGN.md 的 token 或既有 class，沒有自創色碼 | 自動 |
| TC-097 | 原話 1（制式化的通知、不要太口語） | 功能 | 各狀態：讀取中、沒有流程圖、讀取失敗 | 看新增區塊的文字 | 都是計畫指定的固定句（如「讀取中，頁面每 15 秒自動更新。」「這條管線沒有提供流程圖。」）加狀態列，沒有對話口吻的句子 | 自動 |
| TC-098 | 原話 2（學習成本低） | 功能 | 只填好管線與版本 | ann 開啟一次頁面 | 同一頁一次看到預檢、流程圖、樣本表欄位、參數分組表，不需要另外點進別的頁或學新概念 | 自動 |
| TC-099 | 作法 10（390 px） | 功能 | 手機寬度 390 px，中文與英文各一次 | 開啟含全部新區塊的頁面 | 沒有橫向捲動；分組表在窄螢幕上下排 | 手動：`docs/TESTING.md` 第二刀 |
| TC-100 | 專長守則（鍵盤） | 功能 | 只用鍵盤 | Tab 走過新增的連結、輸入欄、`<details>` | 每個焦點都看得到外框，點擊目標夠大 | 手動：`docs/TESTING.md` 第二刀 |
| TC-101 | 完成標準（截圖） | 功能 | 全部新區塊都有內容 | developer-agent 截 1440／390 × 中文／英文四張 | 四張截圖附在 PR，供維護者判斷好不好看 | 手動：`docs/TESTING.md` 第二刀 |
| TC-102 | 完成標準（手動步驟） | 功能 | 站台代理在跑 | 依 TESTING.md：開 `/launch?pipeline=nf-core/ampliseq&src=new` → 看最新版本 → 用那一版 → 等 15–60 秒 → 看到 ✓ 參數表、流程圖連結、樣本表欄位、參數分組表 → 填一個 `p.*` → 第 7 步摘要看得到 → 走到確認頁（不按送出） | 每一步都如預期；`docs/TESTING.md`「引導式送出」節確實有這些步驟 | 手動：`docs/TESTING.md` 第二刀 |
| TC-103 | 範圍：`docs/PLATFORM.md` | 功能 | 看 `docs/PLATFORM.md`「The guided launch page」一節 | 閱讀 | 補了：資料從哪來、讀取中每 15 秒重問、`/launch/diagram` | 手動：閱卷者讀該文件 |
| TC-104 | 範圍：`test_owner_binding.py` | 功能 | 跑 `test_tc068` | 看路由集合 | 集合含 `"/launch/diagram"`，測試綠 | 自動：`platform/tests/test_owner_binding.py` |
| TC-105 | 範圍：既有斷言只准跟著改；裁決 12 | 功能 | 比對 `test_web_guided_launch.py` 與 base | 看 diff 與 `ledger.md` | 只改了第 1 步「讀取管線參數表」、第 3 步、第 5 步分組表三類「之後開放」斷言（含 `len(chk) == 4` 一類）；第 2 步「搜尋全部 nf-core」與第 4 步「預覽」兩條沒動；每條在 ledger 有「舊→新＋理由」 | 手動：閱卷者看 git diff |
| TC-106 | 「不做」第 3 條；計畫檔頭 | 不在範圍 | 比對 base 的 git diff | 看改動的檔案 | 沒有動 `actions/`、`schema.py`、`releases.py`、`jobs.py`、站台代理、`mcp_server.py`、確認頁、`request_launch`；沒有加 JS、沒有加資料表 | 手動：閱卷者看 git diff |
| TC-107 | 計畫「介面事實」（WEB_ONLY） | 不在範圍 | 跑 `test_web_parity.py` | 看結果 | 沒有新增 MCP 工具；`pipeline_files`、`latest_release` 仍登記為 WEB_ONLY，測試綠 | 自動：`platform/tests/test_web_parity.py` |

## 憲法與安全網

本刀碰到：憲法第 2 條（唯一的送出路徑，必須經使用者在確認頁確認）、第 6 條（樣本表欄位與參數必須來自管線自己的檔，不得有每條管線一份設定）、第 3 條（不露出叢集路徑）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-108 | 第 2 條（確認頁才算同意） | 功能 | POST `/launch` 帶 `p.*` 值 | ann 送出 | 只走到確認頁，沒有直接送出任何分析；既有 `test_tch09_*`、`test_tch09_b_c_*`（未確認的送出被拒）仍綠 | 自動：`platform/tests/test_human_channel.py`、`test_confirm_page.py`、本檔 |
| TC-109 | 第 6 條（欄位與參數來自管線自己的檔） | 功能 | 用 `fixtures/schema/` 裡另一條管線的 schema 與 schema_input 作為假代理結果 | 開啟該管線頁面 | 分組表與樣本表顯示的是那條管線自己的組與欄，不是 ampliseq 的；`tests/no_per_pipeline_config.sh` 仍綠 | 自動 |
| TC-110 | 第 3 條（無叢集路徑） | 例外 | 假代理結果的 reason 內含一段檔案路徑（如 `/home/x/y`） | 開啟頁面 | 頁面顯示的句子裡路徑被 `plain_reason` 縮成「…」，不露出原路徑 | 自動 |

<!--
Rules for the writer:
- Every acceptance scenario and every FR in spec.md maps to at least one TC. Every
  "out of scope" item in spec.md maps to at least one 不在範圍 TC.
- A TC tests one thing. Two expectations = two rows.
- 驗證方式 is 自動 (a test file under tests/, named once it exists, "自動" until then)
  or 手動 (a step in docs/TESTING.md's manual half). Nothing else.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
