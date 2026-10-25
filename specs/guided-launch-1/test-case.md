# 測試案例：引導式送出第一刀（`/launch` 七步編號引導，不連網）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：`specs/guided-launch-1/plan.md`（本任務沒有獨立的 spec.md，計畫即規格）；維護者原話見計畫「維護者原話」五條。
維護者指示：測試案例只能來自計畫裡的例子，不自創計畫沒說的行為。計畫沒說的事不寫成 TC，記在總覽「我不確定的地方」。
-->

**規格**：`specs/guided-launch-1/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## 本檔用的說法

- **ann、bob**：兩位不同的登入使用者；除非另外寫，操作者都是 ann。
- **S**：ann 上傳資料夾裡的一份樣本表（`list_samplesheets` 看得到）。
- **E1**：ann 的運算環境，狀態正常，`sitePipelines` 清單含 `nf-core/ampliseq` 版本 `2.18.0`。**E2**：ann 的另一個運算環境，狀態為錯誤，有一句 message。
- **R1、R2**：ann 送出過的兩個 run，管線不同（R1＝`nf-core/ampliseq` `2.18.0`，R2＝另一條管線），內容仍保留。**R1b**：ann 之後又送了一次和 R1 同管線同版本的 run。
- **步驟區塊**：頁面上編號 1 到 7 的 `<details>`／`<summary>`。**狀態**有三種：已完成（符號 ✓、收合）、目前（展開、有外框）、之後（收合、灰）。每種狀態都要「符號＋文字＋樣式」並用。
- 網址參數：`pipeline`、`revision`、`from`（快速送出）、`params_from`（沿用某次分析的參數）、`samplesheet`、`ce`、`src`（`used` 或 `new`）、`lang`。
- 「既有的 xx 文字」＝ `web_board.py` 現有字串，不另寫新句。
- 驗證方式「自動」＝都在 `platform/tests/test_web_guided_launch.py`（新檔），除非另外寫明；每條測試要在註解寫上它的 TC 編號。「手動」＝ `docs/TESTING.md` 新增的「引導式送出」一節。

## User Story 1 — 七個編號步驟的骨架，與維護者的原話（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法「七個編號區塊」；gl01 | 功能 | ann 登入，中文，有 S 與 E1 | 開 `GET /launch` | 頁面有恰好 7 個編號區塊，編號 1 到 7 依序出現，每個都有標題；7 個標題彼此不同；每個區塊是 `<details>` 加 `<summary>` | 自動（`test_gl01_*`） |
| TC-002 | gl01 | 功能 | 同 TC-001，網址不帶任何參數 | 開 `/launch` | 第 2 步是「目前」（展開、有外框）；第 1 步顯示「選好管線後檢查」且不是「目前」；第 3 步顯示「之後開放」且是「之後」狀態 | 自動（`test_gl01_*`） |
| TC-003 | 作法「之後（收合、灰）」 | 功能 | 同 TC-002 | 開 `/launch` | 第 4、5、6、7 步都是收合的「之後」狀態，沒有一個是展開的 | 自動 |
| TC-004 | 作法「狀態三種」；裁決 10 | 功能 | 網址分別為：不帶參數、`?pipeline=nf-core/ampliseq&revision=2.18.0`、`?from=<R1>` | 各開一次 | 每一頁恰好一個步驟是「目前」且只有它展開；已完成的步驟都收合；其餘為「之後」收合 | 自動 |
| TC-005 | 作法「各有符號＋文字＋樣式」；專長守則（狀態不只靠顏色） | 功能 | 取同時含「已完成」「目前」「之後」三種狀態的頁面 HTML（例如 `?pipeline=…&revision=…`） | 逐一檢查三種狀態的區塊 | 已完成的區塊同時有符號 `✓`、狀態文字、狀態樣式；目前的區塊同時有符號、狀態文字、外框樣式；之後的區塊同時有符號或標記、狀態文字、灰色樣式；沒有任何一種只靠 class 顏色表達 | 自動 |
| TC-006 | 裁決 10；作法 3「第 3 步固定之後但不擋後續」；gl03 | 功能 | ann 登入，網址 `?pipeline=nf-core/ampliseq&revision=2.18.0`，沒有 `samplesheet` | 開頁 | 第 2 步是 ✓ 且收合；第 3 步仍是「之後」；目前步驟是第 4 步（第 3 步不算，不擋後面的步驟） | 自動（`test_gl03_*`） |
| TC-007 | 作法「步驟狀態完全由網址參數決定」；裁決 3 | 功能 | 同一個網址、同一位使用者 | 連開兩次；再用另一個全新登入的連線開同一個網址 | 三次的步驟狀態完全相同；回應沒有為了步驟狀態新設任何 cookie；資料表沒有因此新增列 | 自動 |
| TC-008 | 維護者原話 1：「在送出的介面就要有之前abf-v2那些引導的事情，包括選擇pipline (之前設定的 or 新開的)、pipline的流程圖、pipline的參數等等。介面上不要有AI太口語化的回覆，要有制式化的通知呈現」 | 功能 | ann 登入，有 R1、S、E1 | 開 `/launch`，再開 `/launch?pipeline=nf-core/ampliseq&revision=2.18.0` | 第 2 步可選「用過的」（含 R1）或「新管線」兩種來源；有「流程圖」步驟區塊，內容是灰字「之後開放」（計畫已把流程圖延到第二刀）；有「參數」步驟區塊；通知與說明是制式短句，不是對話口吻 | 自動 |
| TC-009 | 維護者原話 2：「開啟一個專案、上傳rawdata之後，馬上就看到選pipline的階段，系統直接一個個引導使用者。」 | 功能 | ann 已有 S（上傳過資料），開 `/launch`，不點任何東西 | 看第一個畫面 | 不是一張空白大表單；第 2 步「選管線」已展開、一眼可見用過的管線或新管線欄位；其餘步驟以編號收合，使用者照 1 到 7 一步步走 | 自動 |
| TC-010 | 維護者原話 3：「Seqera功能太多學習成本高」 | 功能 | 取 `/launch` 與送出失敗重繪頁的 HTML | 列出頁面所有 `input`／`select`／`textarea` 的欄位名稱 | 欄位只有今天表單已有的（`csrf`、`lang`、`pipeline`、`revision`、`run_name`、`samplesheet`、`ce_name`、`params`），再加上計畫列的「參數路線選擇」與頁面狀態參數（`src`、`from`、`params_from`、`ce`）；沒有計畫之外的新欄位 | 自動 |
| TC-011 | 維護者原話 4：「先把功能做起來吧，以後再改美觀」；裁決 5 | 功能 | 本任務完成後的樣式表與 base 的樣式表 | 比對兩份 | 新增的規則只有步驟三種狀態（完成／目前外框／之後灰）與步驟編號；沒有新增任何色碼、間距、字級數值，全部沿用既有 token | 自動 |
| TC-012 | 維護者原話 5（DESIGN.md 畫面 5）：「guided walk of v2's launch skill, numbered disclosures (done ✓ / current outlined / later): 1 Pre-checks … 2 Pipeline: tabs "Used before" (pipeline, revision, last used by, when; Select; ⚡ Quick launch = all previous settings → confirmation) and "New pipeline (all nf-core)" … 3 Workflow diagram … 4 Samplesheet … 5 Parameters: three routes ① reuse a previous run ② defaults ③ adjust by group … 6 Compute environment · 7 Confirm.」 | 功能 | ann 登入，`lang=en`，有 R1、S、E1 | 開 `/launch?lang=en` | 七個區塊的英文標題依序為 Pre-checks、Pipeline、Workflow diagram、Samplesheet、Parameters、Compute environment、Confirm；第 2 步的兩個分頁標題為「Used before」與以「New pipeline」開頭的標題；每個「用過的」列有 `⚡` 加 Quick launch 的連結；第 5 步有三條路線，編號 ①②③ | 自動（`test_gl11_*`） |
| TC-013 | 限制「英文版每個字都有」；gl11 | 功能 | `lang=en`，網址分別為不帶參數、`?pipeline=…&revision=…`、`?from=<R1>` | 取整頁文字 | 沒有任何中日韓文字（使用者的 run 名稱、檔名、站台回的 message 除外） | 自動（`test_gl11_*`） |

## User Story 2 — 第 2 步：選管線（用過的／新管線）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 作法 2「用過的」；gl02 | 功能 | ann 送過 R1（ampliseq 2.18.0）、R2（另一條管線）、R1b（與 R1 同管線同版本，較新） | 開 `/launch?src=used` | 表格恰好 2 列（不是 3 列），最新的一列在最上面 | 自動（`test_gl02_*`） |
| TC-021 | gl02「重複」 | 功能 | 同 TC-020 | 看 ampliseq 2.18.0 那一列 | 「上次分析名稱」是 R1b 的名稱，不是 R1 的 | 自動 |
| TC-022 | 作法 2 欄位 | 功能 | 同 TC-020 | 看表頭與一列內容 | 欄位依序為：管線、版本、上次分析名稱、上次送出時間、運算環境；每列各格都有值 | 自動 |
| TC-023 | gl02「bob 的不出現」；限制「每人只看自己的」 | 例外 | bob 也送過一條管線，名稱不同於 ann 的 | ann 開 `/launch?src=used`；bob 開同一頁 | ann 的表格沒有 bob 的管線或 run 名稱；bob 的表格沒有 ann 的 | 自動 |
| TC-024 | gl02「遺忘的不出現」；作法「略過已遺忘」 | 功能 | ann 對 R2 做過「遺忘」 | ann 開 `/launch?src=used` | R2 那一列不在表格裡 | 自動 |
| TC-025 | 作法 2「預設 used；沒有用過的 → 預設 new」 | 功能 | 情況甲：ann 有用過的管線；情況乙：ann 沒有任何用過的管線 | 各自開 `/launch`（不帶 `src`） | 甲預設顯示「用過的」分頁；乙預設顯示「新管線」分頁 | 自動 |
| TC-026 | 作法 2「網址 `&src=used｜new`」 | 功能 | ann 有用過的管線 | 分別開 `/launch?src=new` 與 `/launch?src=used` | 前者顯示「新管線」分頁內容，後者顯示「用過的」表格；兩個分頁標題都有可點的連結 | 自動 |
| TC-027 | 作法 2「選擇」連結 | 功能 | 同 TC-020 | 取 R1b 那一列的「選擇」連結 | 它是一個 GET 連結，網址為 `/launch?pipeline=nf-core/ampliseq&revision=2.18.0`（含必要的語言或分頁參數亦可）；不是表單送出 | 自動 |
| TC-028 | 作法 2「⚡ 快速送出」連結 | 功能 | 同 TC-020 | 取每一列的「⚡ 快速送出」連結 | 網址為 `/launch?from=<該列的上次分析名稱>`，是 GET 連結，標題含 `⚡` | 自動 |
| TC-029 | 作法 2「新管線」 | 功能 | ann 開 `/launch?src=new` | 看分頁內容 | 有 `pipeline`、`revision` 兩個欄位的 GET 表單（送出後回到 `/launch` 並帶這兩個參數），另有灰字「搜尋全部 nf-core 之後開放」；沒有搜尋輸入框 | 自動 |
| TC-030 | gl03；作法 2 | 功能 | ann 開 `/launch?pipeline=nf-core/ampliseq&revision=2.18.0` | 看第 2 步 | 第 2 步顯示 ✓ 並收合；頁面仍保有所選的管線與版本（摘要或隱藏欄位可見） | 自動（`test_gl03_*`） |
| TC-031 | 限制「零 JavaScript」；安全 | 例外 | 網址帶惡意值：`?pipeline="><script>x</script>&revision=<b>1</b>`，以及 run 名稱含 `<b>` 的用過的列 | 開頁 | 這些值在頁面中被轉義成純文字，頁面沒有 `<script`，沒有生出新標籤 | 自動 |
| TC-032 | 專長守則「路由裡不得有第二份邏輯」；範圍 `web.py` | 功能 | 把 `actions.list_used_pipelines` 換成回固定兩筆資料的替身 | 開 `/launch?src=used` | 表格內容完全取自替身的回傳；網頁自己沒有去查資料庫或 jobs | 自動 |

## User Story 3 — 第 1 步：前置檢查（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 作法 1；gl03 | 功能 | ann 有 S、E1 | 開 `?pipeline=nf-core/ampliseq&revision=2.18.0` | 第 1 步列出四項檢查：版本已指定、站台連線、管線已登記、有可用樣本表；另有第五項「讀取管線參數表」為灰字「之後開放」 | 自動（`test_gl03_*`） |
| TC-041 | 作法 1「選好管線之前顯示『選好管線後檢查』」 | 功能 | 網址不帶 `pipeline` | 開頁 | 第 1 步只有「選好管線後檢查」一句，沒有任何 ✓／✗／— 的檢查列 | 自動 |
| TC-042 | gl04「有 → ✓」 | 功能 | E1 的 `sitePipelines` 含 ampliseq 2.18.0 | 開 `?pipeline=nf-core/ampliseq&revision=2.18.0&ce=E1` | 「管線已登記」列為 ✓ 加一句制式說明 | 自動（`test_gl04_*`） |
| TC-043 | gl04「沒有該版本 → ✗」 | 例外 | E1 的 `sitePipelines` 有清單，但不含 ampliseq 的 `9.9.9` | 開 `?pipeline=nf-core/ampliseq&revision=9.9.9&ce=E1` | 「管線已登記」列為 ✗ 加一句制式說明 | 自動 |
| TC-044 | gl04「沒有清單 → —」 | 功能 | 環境的設定裡沒有 `sitePipelines` 清單 | 開頁並選到這個環境 | 「管線已登記」列為「—（這個環境不需登記）」 | 自動 |
| TC-045 | gl05「正常 → ✓」 | 功能 | E1 狀態正常 | 開 `?pipeline=…&revision=…&ce=E1` | 「站台連線」列為 ✓ 加一句制式說明 | 自動（`test_gl05_*`） |
| TC-046 | gl05「錯誤 → ✗＋message」 | 例外 | E2 狀態為錯誤，message 是一句固定文字 | 開 `?pipeline=…&revision=…&ce=E2` | 「站台連線」列為 ✗，並顯示環境的那句 message（內容相同，語言版本可只留本頁語言那半） | 自動 |
| TC-047 | 作法 1「版本已指定（revision 非空）」 | 功能 | 兩個網址：帶 `revision=2.18.0`；只帶 `pipeline` 不帶 `revision` | 各開一次 | 前者「版本已指定」為 ✓；後者為 ✗ | 自動 |
| TC-048 | 作法 1「有可用樣本表」 | 功能 | 情況甲：ann 有 S；情況乙：ann 沒有任何樣本表 | 各開 `?pipeline=…&revision=…` | 甲「有可用樣本表」為 ✓；乙為 ✗ | 自動 |
| TC-049 | 作法 1「所選或預設運算環境」 | 功能 | ann 有 E1（預設，排第一）與 E2 | 開不帶 `ce` 的網址；再開 `&ce=E2` | 前者的站台連線與登記檢查取自預設環境 E1；後者取自 E2 | 自動 |
| TC-050 | 作法 1、裁決 6「✗ 不擋送出」 | 功能 | 前置檢查有 ✗（例如選 E2 或版本未登記）；其他欄位都合法 | 照引導走到最後，`POST /launch` | 仍然 303 轉到 `/c/<id>`，產生一筆待確認；✗ 沒有擋住送出 | 自動 |
| TC-051 | 作法 1「第 7 步摘要重列 ✗ 項目」 | 功能 | 前置檢查有一個 ✗ | 看第 7 步摘要 | 摘要裡重列該 ✗ 項目及其說明 | 自動 |
| TC-052 | 作法 1「✓／✗／— ＋一句制式說明」；專長守則 | 功能 | 一頁同時有 ✓、✗、— 三種檢查列 | 取 HTML | 每一列同時有符號與文字說明；沒有只靠顏色的列 | 自動 |
| TC-053 | 限制「每人只看自己的」 | 例外 | bob 有環境 B1；ann 登入 | ann 開 `?pipeline=…&revision=…&ce=B1` | 頁面沒有 B1 的名稱、狀態、message 或 `sitePipelines` 內容；不會把 B1 當成 ann 的環境 | 自動 |

## User Story 4 — 快速送出與第 5 步：參數三條路線（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | gl06；裁決 7 | 功能 | R1 內容仍保留，未選樣本表 | 開 `/launch?from=<R1>` | 第 1、2、5、6 步為 ✓；第 3 步為「之後」；目前步驟是第 4 步 | 自動（`test_gl06_*`） |
| TC-061 | gl06「再帶 samplesheet」；裁決 7 | 功能 | 同 TC-060，R1 帶有參數 | 開 `/launch?from=<R1>&samplesheet=<S>` | 目前步驟是第 7 步；第 7 步摘要列出帶入的參數 | 自動 |
| TC-062 | 作法 2「沿用既有 prefill」；裁決 7 | 功能 | 同 TC-060 | 看表單欄位 | 管線、版本、運算環境、參數取自 R1；分析名稱欄位是空的、樣本表沒有被帶入；出現既有的提示（既有 `l_from` 文字） | 自動 |
| TC-063 | 作法「沿用既有 prefill」，內容已不保留 | 例外 | 一個 run 的內容已被清掉（`kept` 為否） | 開 `/launch?from=<該 run>` | 回應 200；顯示既有的「這個 run 的內容沒有保留，請自己填。」；沒有任何預填值；沒有送出任何東西 | 自動 |
| TC-064 | 作法「沿用既有 prefill」，別人的或不存在的 run | 例外 | bob 的 run；一個不存在的名稱 | ann 開 `/launch?from=<bob 的 run>` 與 `/launch?from=nope` | 兩者都是既有的「找不到」404 頁，內容相同，沒有洩漏 bob 的任何資料 | 自動 |
| TC-065 | 作法 5「三條路線（單選）」 | 功能 | 開有選好管線的 `/launch` | 看第 5 步 | 有 ① 沿用上次分析、② 預設值、③ 自己調整三個選項，且是單選（同一時間只能選一個） | 自動 |
| TC-066 | 作法 5 ①「列出這條管線＋版本用過的分析」 | 功能 | ann 有兩次 ampliseq 2.18.0 的 run 與一次別的管線的 run；bob 也有 ampliseq 2.18.0 的 run | 開 `?pipeline=nf-core/ampliseq&revision=2.18.0` 看路線 ① | 只列 ann 自己的、且管線＋版本相同的 run；沒有別條管線的，沒有 bob 的 | 自動 |
| TC-067 | gl07 ①；裁決 9 | 功能 | R1 帶參數 `a: 1`；網址 `?pipeline=nf-core/ampliseq&revision=2.18.0&ce=E1&samplesheet=<S>&params_from=<R1>` | 開頁 | 參數框內容等於 R1 的參數（與今天預填的寫法相同）；管線、版本、運算環境、樣本表維持網址上選的值 | 自動（`test_gl07_*`） |
| TC-068 | gl07 ② | 功能 | 選路線 ②（預設值） | 照引導走到送出 | 參數框是空的；送出時不帶參數（`params` 為空） | 自動 |
| TC-069 | gl07 ③ | 功能 | 路線 ③，參數框輸入多行 `name: value` | 重繪或進摘要 | 參數框內容原樣保留，一個字都沒改；參數分組表為灰字「之後開放」 | 自動 |
| TC-070 | 裁決 9「必須是 caller 自己的」 | 例外 | bob 的 run `RB` | ann 開 `?pipeline=…&revision=…&params_from=<RB>` | 顯示制式通知「這個分析的參數不能沿用。」；參數框為空（當作沒選）；頁面沒有 RB 的任何參數或名稱以外的資料 | 自動 |
| TC-071 | 裁決 9「管線＋版本相同」 | 例外 | ann 的 R2（另一條管線）；ann 的 R1 但網址的版本是另一個 | 開 `?pipeline=nf-core/ampliseq&revision=2.18.0&params_from=<R2>`；再開 `?pipeline=nf-core/ampliseq&revision=9.9.9&params_from=<R1>` | 兩次都顯示「這個分析的參數不能沿用。」，參數框為空 | 自動 |
| TC-072 | 裁決 9「否則制式通知並當作沒選」 | 例外 | 不存在的 run 名稱 | 開 `?pipeline=…&revision=…&params_from=nope` | 同樣顯示「這個分析的參數不能沿用。」，參數框為空，頁面仍是 200 | 自動 |
| TC-073 | 限制「英文版每個字都有」；裁決 9 | 例外 | `lang=en`，同 TC-070 的情況 | 開頁 | 通知是英文一句，沒有中日韓文字 | 自動 |
| TC-074 | 裁決 9「`from` 只代表快速送出」 | 功能 | 網址只帶 `pipeline`、`revision`、`params_from=<R1>`，不帶 `from` | 開頁 | 沒有快速送出的提示（既有 `l_from` 文字）；管線、版本、運算環境維持網址上的值，只有參數被帶入 | 自動 |

## User Story 5 — 樣本表、運算環境、確認與送出（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 作法 4；gl10 | 例外 | ann 沒有任何樣本表 | 開 `?pipeline=…&revision=…` | 第 4 步顯示制式通知「沒有可用的樣本表。」，並附既有的上傳說明文字；沒有可選的樣本表 | 自動（`test_gl10_*`） |
| TC-081 | 作法 4「沿用 select；預覽之後開放」 | 功能 | ann 有 S；bob 有 SB | ann 開頁看第 4 步 | 下拉選單只有 ann 自己的樣本表（有 S、沒有 SB）；「預覽與欄位角色」為灰字「之後開放」 | 自動 |
| TC-082 | 作法 6 | 功能 | ann 有 E1（正常）、E2（錯誤）；bob 有 B1 | ann 開頁看第 6 步 | 下拉選單只有 E1、E2；每個選項旁有狀態符號加狀態文字（E1 正常、E2 錯誤，內容取自環境現況）；沒有 B1 | 自動 |
| TC-083 | 作法 7「摘要」 | 功能 | 已選管線、版本、樣本表、環境，分析名稱已填，參數改過一行，前置檢查有一個 ✗ | 看第 7 步 | 摘要列出：管線＋版本、分析名稱、樣本表、改過的參數、運算環境、第 1 步的 ✗ 項目 | 自動 |
| TC-084 | 作法 7「分析名稱欄位放在這一步；送出＝POST /launch」 | 功能 | 開頁 | 看第 7 步的表單 | 分析名稱輸入框在第 7 步；有「送出」按鈕，表單是 `POST /launch`，含 CSRF 欄位；第 7 步以外沒有分析名稱欄位 | 自動 |
| TC-085 | gl08；目標「送出的東西跟今天的表單完全一樣」 | 功能 | ann 照引導填好全部欄位 | `POST /launch`；另用 base 的表單欄位值做同樣的送出 | 303 轉到 `/c/<id>`，恰好新增一筆待確認；兩次的 bundle（管線、版本、分析名稱、樣本表、環境、參數）欄位與結果相同 | 自動（`test_gl08_*`） |
| TC-086 | 作法「POST 不變：驗證規則」：管線與版本 | 例外 | 管線含不合法字元；版本空白；版本含空白字元 | 各自 POST | 都回 400，沒有新確認；錯誤句與今天相同（既有 `e_pipeline`、`e_revision`） | 自動 |
| TC-087 | 同上：樣本表與運算環境 | 例外 | `samplesheet` 不在 ann 的清單；`ce_name` 不在 ann 的環境 | 各自 POST | 都回 400，沒有新確認；錯誤句與今天相同 | 自動 |
| TC-088 | 同上：參數 | 例外 | 參數框有不合法行（沒有冒號、重複名稱、值是清單） | POST | 回 400，沒有新確認；錯誤句與今天相同，點出哪個參數 | 自動 |
| TC-089 | 作法「同 CSRF」 | 例外 | CSRF 錯誤的 POST；`Origin` 是別的網站的 POST | 各自送出 | 都被拒絕（403 或既有的外來來源拒絕），沒有新確認 | 自動 |
| TC-090 | gl09 | 例外 | 其他欄位都合法，缺分析名稱 | `POST /launch` | 400；第 7 步展開成「目前」；其他已填的值都保留；沒有新確認 | 自動（`test_gl09_*`） |
| TC-091 | 裁決 10「出錯欄位所在步驟中編號最小的」 | 例外 | 同時有三個錯誤：樣本表不合法（第 4 步）、參數不合法（第 5 步）、缺分析名稱（第 7 步） | POST | 400；目前步驟是第 4 步，不是第 5 或第 7 步 | 自動 |
| TC-092 | 作法「錯誤時 400 重繪，其餘值保留」 | 功能 | 任一種 400 的情況 | 看重繪頁 | 管線、版本、樣本表、運算環境、參數框、分析名稱（若有填）都保留原值 | 自動 |
| TC-093 | 專長守則「跨使用者寫」 | 例外 | bob 登入 | bob `POST /launch`，樣本表填 ann 的 S，另一次運算環境填 ann 的 E1 | 都回 400，沒有新確認；ann 的資料沒被使用 | 自動 |
| TC-094 | 專長守則「錯誤訊息說明原因與處理、不露內部細節」 | 例外 | TC-086 至 TC-091 的各種 400 頁 | 取文字 | 錯誤句說明發生什麼事；頁面沒有 `Traceback`、SQL、`args_json`、內部檔案路徑 | 自動 |

## User Story 6 — 新 read `list_used_pipelines`（動作層與 MCP）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-100 | 作法「回傳形狀」；裁決 2 | 功能 | ann 有 R1、R2 | 呼叫 `actions.list_used_pipelines(platform_path, caller=ann)` | 回 `{"pipelines": [...]}`，每筆恰有 `pipeline`、`revision`、`run_name`、`launched_at`、`ce_name` | 自動（`test_gl13_*`） |
| TC-101 | 作法「擁有者規則」；gl13 | 例外 | ann 有送出紀錄；bob 沒有 | 以 bob 呼叫；再以 ann 呼叫 | bob 得到 `{"pipelines": []}`，沒有 ann 的任何資料；ann 只得到自己的 | 自動 |
| TC-102 | 作法「同一 (pipeline, revision) 只留最新一筆，最新在前」 | 功能 | R1、R2、R1b 如前 | 呼叫 | 兩筆；ampliseq 2.18.0 那筆的 `run_name` 是 R1b；依送出時間由新到舊 | 自動 |
| TC-103 | 作法「最多 20 筆」 | 功能 | ann 送過 25 個不同 (pipeline, revision) 的 run | 呼叫 | 恰好 20 筆，且是最新的 20 筆 | 自動 |
| TC-104 | 作法「略過已遺忘」 | 功能 | ann 的 R2 被遺忘 | 呼叫 | 結果沒有 R2 | 自動 |
| TC-105 | 作法「來源是 confirmations.bundle_json，不用 jobs 的 args_json」 | 功能 | 把 R1 對應工作的 `args_json` 清空（模擬 7 天後被清掉） | 呼叫 | 仍然列出 R1 的 pipeline 與 revision | 自動 |
| TC-106 | 作法「MCP 同名 read tool」；gl13 | 功能 | ann 有 R1、R2 | 經 MCP 以 ann 的身分呼叫 `list_used_pipelines` | 內容與動作層回傳完全相同 | 自動（`test_gl13_*`） |
| TC-107 | 專長守則「跨使用者讀」；gl13 | 例外 | 同 TC-101 | 經 MCP 以 bob 的身分呼叫 | 回空清單，看不到 ann 的任何資料 | 自動 |
| TC-108 | 專長守則「對等性」；範圍「parity 測試只加一項」 | 功能 | `test_web_parity.py`、`test_actions_layer.py` 更新後 | 跑這兩個檔 | 通過；`list_used_pipelines` 同時出現在動作層、網頁用到的動作清單、MCP 工具清單，缺任一邊測試就失敗；這兩個檔相對 base 的差異只多了 `list_used_pipelines` 一項（OWED 等其他清單沒放寬），ledger 逐條列 | 自動：`platform/tests/test_web_parity.py`、`platform/tests/test_actions_layer.py` |
| TC-109 | 作法「是 read」 | 功能 | 呼叫前後各取確認紀錄、工作與送出紀錄的筆數 | 呼叫 `list_used_pipelines` 與開 `/launch` | 筆數都沒變；沒有新的確認、工作或送出 | 自動 |
| TC-110 | 作法「不新增資料表、不需 migration」；裁決 3 | 功能 | base 與本任務各建一個新資料庫 | 比對資料表與欄位 | 完全相同；沒有新的 migration（既有 `test_tc063_no_schema_change` 不用改就通過） | 自動 |

## User Story 7 — 不能放掉的限制與文件（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-120 | 限制「零 JavaScript」；gl12 | 功能 | 這些頁面：不帶參數、選好管線、快速送出、`params_from`、沒有樣本表、400 重繪，中文與英文各一 | 取 HTML | 都不含 `<script`，也沒有 `onclick` 這類事件屬性 | 自動（`test_gl12_*`） |
| TC-121 | 限制「無 `style=`」；gl12 | 功能 | 同 TC-120 | 取 HTML | 都不含 `style=` | 自動 |
| TC-122 | 限制「單一樣式表（CSP 雜湊）」；gl12 | 功能 | 同 TC-120 | 取 HTML 與回應標頭 | 每頁只有一份 `<style>`，沒有 `<link>`；標頭 CSP 含該樣式表的雜湊，沒有 `script-src`、沒有 `'unsafe-inline'` | 自動 |
| TC-123 | 限制「既有 tc046–048、tc051、tc060、tc063、tc040 全部要繼續綠」 | 功能 | 本任務完成後 | 跑 `platform/tests/test_web_actions.py` | 這幾條都通過；它們的斷言內容相對 base 沒有被改動 | 自動：`platform/tests/test_web_actions.py` |
| TC-124 | 限制「制式通知（不口語、不用「我」「你可以試試」）」；gl12 | 功能 | 本任務新增的所有介面字串（中英文，含第 1 步說明、通知、灰字、摘要） | 掃描 | 沒有第一人稱「我」或 I、沒有「你可以試試」或 you could try 這類建議口吻、沒有閒聊語氣；全是制式短句 | 自動（`test_gl12_*`） |
| TC-125 | 限制「英文版每個字都有」；gl11 | 功能 | `lang=en`，頁面包含：沒有樣本表的通知、「參數不能沿用」通知、400 重繪的錯誤句、第 1 步各檢查列 | 取文字 | 沒有中日韓文字（站台回的 message、使用者輸入除外） | 自動 |
| TC-126 | 限制/環境事實「平台不連網」 | 功能 | 本任務變更的程式檔 | 跑既有「平台不連網」檢查（如 `test_chat_tools.py:178` 一類）並開各頁 | 通過；各頁面渲染過程沒有對外發出任何網路請求，沒有新增網路用戶端的引用 | 自動 |
| TC-127 | 限制「390 px 無橫向捲動」；專長守則（手機寬度） | 功能 | 引導式送出的頁面：不帶參數、選好管線後、第 7 步，含長管線名稱 | 在 1440 與 390 寬（裝置模擬）、中文與英文各開，量 `document.documentElement.scrollWidth` 與 `clientWidth` | 390 寬時兩個數字相等；沒有橫向捲軸，沒有內容被切掉 | 手動：`docs/TESTING.md`「引導式送出」 |
| TC-128 | 專長守則「焦點外框可見、點擊目標夠大」 | 功能 | 同 TC-127 | 用鍵盤 Tab 依序走過步驟標題、連結、欄位、送出鈕；390 寬看點擊範圍 | 每個都能被聚焦且焦點外框看得到；點擊範圍不比既有按鈕和連結小 | 手動：`docs/TESTING.md`「引導式送出」 |
| TC-129 | 目標「照 1→7 的編號一步一步走」 | 功能 | 一個有上傳資料、有 R1 的使用者，瀏覽器關閉 JS | 從 `/launch` 開始，依頁面指示走完第 1 到第 7 步，按「送出」 | 每一步都看得出下一步要做什麼；不靠 JS 就能走到第 7 步並送出；最後落在既有確認頁 `/c/<id>` | 手動：`docs/TESTING.md`「引導式送出」 |
| TC-130 | 範圍 `docs/PLATFORM.md`（一段：七步各自讀什麼） | 功能 | 本任務完成後的 `docs/PLATFORM.md` | 讀它 | 有一段說明七個步驟各自讀什麼資料（例如第 2 步讀 `list_used_pipelines`，第 1 步讀運算環境與樣本表清單） | 手動：驗收者讀檔 |
| TC-131 | 裁決 8、範圍 `docs/TESTING.md` | 功能 | 本任務完成後的 `docs/TESTING.md` | 讀它 | 新增一節「引導式送出」，含：390 px 無橫捲、Tab 鍵焦點外框、走一次 1→7；每步寫得具體到能照著做 | 手動：驗收者讀檔 |
| TC-132 | 完成標準「截圖」；裁決 8 | 功能 | developer-agent 補在 PR 的截圖 | 看 PR | 有 1440 與 390 寬、中文與英文各一組截圖；這是 B 級畫面，由維護者決定好不好看，不自動合併 | 手動：維護者看 PR 截圖 |
| TC-133 | 裁決 4、完成標準「ledger 逐條舊→新＋理由」 | 功能 | 本任務的 ledger 與 `git diff <base>...HEAD` 對測試檔 | 比對 | 被改的既有斷言只有 `test_web_actions.py` 中「/launch 表單版面或欄位順序或位置」那幾條（如 tc020 一類）與「工具清單或工具數」加 `list_used_pipelines`；欄位名稱、驗證、CSRF、確認流程的斷言一字未動；每條在 ledger 有 file:line 與「舊→新＋理由」 | 手動：驗收者 `git diff` 比對 |

## User Story 8 — 這次不做的事（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-140 | 不做「不連 GitHub：不讀 `nextflow_schema.json`／`schema_input.json`、不抓流程圖」 | 不在範圍 | 選好管線的 `/launch` | 取 HTML 並檢查程式 | 第 3 步只有灰字「之後開放」，沒有 `<img>`、`<svg>`、圖片網址；程式裡沒有讀取這兩個檔案或請求 GitHub 的新程式碼 | 自動 |
| TC-141 | 不做「不列 nf-core 全部管線」 | 不在範圍 | `/launch?src=new` | 取 HTML | 「搜尋全部 nf-core」只是灰字「之後開放」；沒有搜尋框、沒有管線卡片清單 | 自動 |
| TC-142 | 不做「不查最新版本」 | 不在範圍 | 選好管線，版本欄填任意值 | 開頁 | 頁面沒有「最新版本」提示或自動填版本；版本檢查只看是否非空 | 自動 |
| TC-143 | 不做「樣本表預覽與欄位角色、參數分組表」 | 不在範圍 | 選好管線與樣本表 | 取 HTML | 第 4 步的預覽與欄位角色、第 5 步的參數分組表都只是灰字「之後開放」；沒有預覽表或分組表 | 自動 |
| TC-144 | 不做「不改確認頁、不改 `request_launch` 與 `build.prepare_launch`、不改站台、不動右欄、不加 JS、不加資料表」 | 不在範圍 | 本任務分支與 base | 比對 `platform/abf_station/`、確認頁相關程式、`request_launch` 與 `build.prepare_launch` 的函式內容、右欄 | 這幾處相對 base 沒有差異；`/launch` 的右欄內容與 base 相同 | 手動：驗收者 `git diff <base>...HEAD`（`docs/TESTING.md` 對應步驟） |
| TC-145 | 範圍「不加新路由」；裁決 3「不新增 cookie 或伺服器端 session」 | 不在範圍 | base 與本任務的網頁路由清單 | 比對 | 路由清單完全相同（既有 tc051 的禁用字樣仍成立）；沒有新的狀態儲存 | 自動 |
| TC-146 | 不做「上傳頁、設定頁（012a）」 | 不在範圍 | ann 登入 | 開 `/upload`，並開 `/settings` 與 base 比對 | `/upload` 仍是 404；`/settings` 內容與 base 相同 | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-160 | 安全網「launch 要等人確認」；原則 I.2 | 功能 | ann 登入 | 用各種網址組合 GET `/launch`（含 `from`、`params_from`、`pipeline`、`revision`、`ce`、`samplesheet`） | 沒有產生任何確認紀錄或站台工作；只有 `POST /launch` 能產生待確認，且需要 CSRF | 自動 |
| TC-161 | 安全網「每個寫入工具要人先答應」 | 功能 | 本任務完成後 | 跑 `test_actions_layer.py`（`test_tcb04_*` 到 `test_tcb08_*`）與 `test_human_channel.py`（`test_tch09_*`） | 通過；`list_used_pipelines` 不在寫入工具清單；`request_launch` 行為不變 | 自動：`platform/tests/test_actions_layer.py`、`platform/tests/test_human_channel.py` |
| TC-162 | 專長守則「路由只呼叫允許的動作」；`test_web_actions.py` tc060 | 功能 | 本任務完成後 | 跑 tc060 | 通過；網頁沒有呼叫 `launch`、`cancel`、`forget` 等寫入動作，沒有 import `jobs`、`compute_envs`、`confirm`；`list_used_pipelines` 是以登記方式放行的 read，沒有放寬到寫入動作 | 自動：`platform/tests/test_web_actions.py` |
| TC-163 | 原則 I.2：平台索引不是第二份真相 | 功能 | 本任務完成後 | 跑 `tests/no_second_run_state_test.sh` | 通過；用過的管線清單每次從既有紀錄現算，沒有新表、新檔 | 自動：`tests/no_second_run_state_test.sh` |
| TC-164 | 原則 II.3：不寫死路徑 | 功能 | 本任務完成後 | 跑 `tests/no_hardcoded_paths.sh` | 通過 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-165 | 安全網「憑證不外露」 | 例外 | 運算環境的設定裡放一個假憑證字串 | 開各引導頁（含第 1 步、第 6 步）、呼叫 `list_used_pipelines` 的動作層與 MCP、看日誌 | 假憑證字串不出現在任何頁面、MCP 回覆或日誌 | 自動 |
| TC-166 | 完成標準：全套綠 | 功能 | 本任務完成後 | 在 WSL 跑 `tests/run_all.sh` | 全綠；唯一可忽略的是計畫裁決 1 點名的已知環境紅（`tests/init_workspace_test.sh`「site side with no run area known fails clearly」，base 也紅） | 自動：`tests/run_all.sh` |

<!--
IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
