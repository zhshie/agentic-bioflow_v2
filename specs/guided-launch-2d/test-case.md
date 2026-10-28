# 測試案例：引導式送出第二輪重排（2d：分析名稱第一、只列設定好的運算環境、管線與版本一處決定、流程圖直接顯示、拿掉前置檢查）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：memory/dev-plans/guided-launch-2d.md（計畫即規格；「裁決」優先）。
維護者原話六條（計畫「維護者原話」）：
 原話1 分析名稱第一／前置檢查在設定做好沒做好就不跑／版本不要有第二個可調處 → TC-001～008、011～020、032
 原話2 流程圖在選定管線時直接顯示於正下方 → TC-037～046
 原話3 順序 分析名稱→運算環境→管線→樣本表→確認 → TC-001、002、009、073
 原話4 參數在樣本表之後、確認之前 → TC-009
 原話5 版本只出現一次、選完管線後旁邊下拉、預設最新、「版本已指定」整步拿掉 → TC-003、022～034
 原話6 只放寬自家圖片的 img-src → TC-047～050、068
-->

**規格**：`memory/dev-plans/guided-launch-2d.md`　**測試檔**：`platform/tests/test_web_guided_launch_2d.py`（新檔；每條測試註解寫 TC 編號）

類型：**功能**（要做到的事）、**例外**（缺東西或出錯時怎麼反應）、**不在範圍**（這次不做，測試確認沒做）。

## 本檔用的說法

- **ann**：登入的使用者。**假代理**：用 `test_web_guided_launch_2.py` 的 `Fake`（`pipeline_files`、`latest_release` 的替身，記錄呼叫；`socket.connect` 被擋）。平台自己不連網。
- **P／R**：`nf-core/ampliseq`、`2.18.0`。fixtures 同 2b（ampliseq schema、schema_input、`ampliseq_workflow.png`）。
- **環境（env）假資料**：用 `actions.list_compute_envs` 的形狀：`{name, status, message, config:{sitePipelines}}`。「可用」＝`status == "available"`。
- **步驟區**：`<details class="gstep" data-step="n">`，n 為 1～6。
- **shown_pipeline／shown_revision／shown_params_from**：表單隱藏欄。管線、版本或沿用分析與 shown_* 不同時，送出只是「載入」（303 回 GET `/launch`，不送出）。
- **禁用詞（22 個）**：用過、選好、寫死、自己填、自己調整、你還沒、還沒有、還不能、這個、這份、這條、這一版、一下、弄、搞、東西、喔、啦、吧、囉、蠻、超。
- **計畫新句子（逐字）**：
  - S1「尚無可用的運算環境，請先至設定頁完成設定。」
  - S2「此管線版本尚未在所選運算環境登記，請洽管理者登記；已登記的管線列於設定頁。」（developer-agent 10-28 裁決 4 改句：設定頁目前只能檢視、不能登記）
  - S3「尚無已上傳的樣本表，請先上傳。」
  - S4「正在讀取版本清單…」
  - S5「正在讀取流程圖…」
  - S6「此管線未提供流程圖。」
- 「自動」＝新檔 `test_web_guided_launch_2d.py`，除非另寫；「手動」＝ `docs/TESTING.md`、ledger、`git diff` 或截圖。

## US1 — 六步順序與分析名稱第一（P1）

原話1「分析名稱要放在第1個順位」、原話3「分析名稱->運算環境->選pipline->樣本表->確認」、原話4。

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-001 | 原話1、3；K01；作法1 | 功能 | P／R 全部讀好 | 開 `/launch`（中文） | 恰有六個步驟區，標題依序逐字為「分析名稱」「運算環境」「管線」「樣本表」「參數」「確認」 | 自動 |
| TC-002 | K01；作法7 | 功能 | 同上，`lang=en` | 開頁面 | 六個步驟區，標題為六個互不相同、非空、不含中文字的英文；不含 "Pre-check" | 自動 |
| TC-003 | 原話1、5；K01；作法2 | 功能 | 中英文各一次，且分別在：讀好、讀取中、讀失敗、沒有樣本表、沒有環境、POST 被擋回 | 檢查 HTML | 沒有「前置檢查」「Pre-check」字樣，沒有 `class="checks"` 清單，沒有「版本已指定」一列 | 自動 |
| TC-004 | 作法1 | 功能 | 讀好；再看 POST 被擋回 | 檢查六個步驟區 | `data-step` 為 1～6 連號；每區標頭同時有狀態符號與文字（✓已完成／●目前／○之後，英文對應） | 自動 |
| TC-005 | 原話1；K02 | 功能 | 剛開 `/launch`，什麼都沒填 | 看步驟狀態 | ① 為「目前」且展開；② 以後為「之後」 | 自動 |
| TC-006 | 原話1；K02 | 功能 | 讀好 | 看輸入 | 頁面只有一個 `name="run_name"`，在 ① 內，帶紅星；① 內它是唯一的輸入欄 | 自動 |
| TC-007 | K02；作法1 | 功能 | 有可用環境、有樣本表 | 看表單 | 表單內恰一個 `<button type="submit">`（頁首登出鍵不算），文字「送出（前往確認頁）」，位於 ⑥ 內 | 自動 |
| TC-008 | 原話1、5；作法3 | 功能 | 讀好 | 看 ⑥ | ⑥ 只有文字摘要（分析名稱、管線＋版本、樣本表、參數、運算環境）加送出鍵；⑥ 內沒有 `name="run_name"`、`name="pipeline"`、`name="revision"` 的可編輯控制項 | 自動 |
| TC-009 | 原話4；裁決1 | 功能 | 讀好 | 看步驟順序與內容 | 「樣本表」（含 `name="samplesheet"`）在「參數」之前；「參數」（含 `p.` 格子與 `name="params"` 進階框）在「確認」之前 | 自動 |
| TC-010 | 2b TC-020 延續 | 功能 | 網址帶 `run_name=my-run` | 開頁面 | ① 的分析名稱欄值為 `my-run` | 自動 |

## US2 — 運算環境只列設定好的（P1）

原話1「前置檢查一律在設定那邊做好，沒做好就不跑」、原話3「國網or雲端，設定做好才顯示出來」；裁決2。

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-011 | K03；原話3；作法2 | 功能 | 兩個環境：A（available）、B（status 為 creating／invalid／unsupported／disabled 各測一次）。另測「Slurm available＋Google Cloud Batch 非 available」與反過來 | 看 ② | `name="ce_name"` 下拉只含 available 的那一個；非 available 的名稱不在頁面的選項裡。國網與雲端一視同仁，只看狀態 | 自動 |
| TC-012 | 作法2 | 功能 | 同上，網址 `ce_name=B`（B 非 available） | 開頁面 | 網址這個值被忽略；選中的是第一個 available 環境 | 自動 |
| TC-013 | K04；S1；作法2 | 例外 | (a) 完全沒有環境；(b) 有環境但全部非 available | 開頁面 | ② 顯示 S1（逐字）、含連到 `/settings` 的連結（英文頁帶 `lang=en`）；整頁沒有 `<button type="submit">`；沒有 `name="ce_name"` 下拉 | 自動 |
| TC-014 | K04；作法2 | 例外 | 同 TC-013 的 (a)、(b)，另測「環境存在但非 available，POST 的 `ce_name` 填它」 | 直接 POST（其餘欄位合規） | 400，列出 e_ce 句子；`request_launch` 沒被呼叫 | 自動 |
| TC-015 | K05；S2；作法2 | 例外 | 所選環境 `config.sitePipelines` 是非空清單，不含 P＋R | 開 P／R 頁面；再 POST（shown_* 與管線一致） | ③ 顯示 S2（逐字）與連到 `/settings` 的連結；POST 回 400 並列出登記問題；`request_launch` 沒被呼叫 | 自動 |
| TC-016 | 作法2 | 功能 | sitePipelines 清單含 P＋R | 同上 | ③ 沒有 S2；POST 通過到確認頁 | 自動 |
| TC-017 | 作法2（同現狀） | 功能 | 所選環境沒有 `sitePipelines`，或為空清單，或不是 list | 同上 | 不檢查登記：沒有 S2，POST 通過 | 自動 |
| TC-018 | 作法2 | 例外 | 環境 A 的清單含 P＋R，環境 B 的清單不含；頁面畫的是 A | POST 時 `ce_name=B`（shown_* 一致） | 以 POST 選到的環境 B 判斷：400；用 A 則通過 | 自動 |
| TC-019 | K06；S3；作法2 | 例外 | ann 沒有任何樣本表 | 開頁面；按送出 | ④ 顯示 S3（逐字）與一個連結；送出鍵仍在（2b TC-009 保留）；POST 回 400 列出樣本表問題；`request_launch` 沒被呼叫 | 自動 |
| TC-020 | 作法2；裁決3 | 功能 | 同 TC-019，中英文各一次 | 看 S3 的連結 | 頁面目前沒有真的上傳網址（側欄「上傳資料」只是灰字），所以連結 `href` 為看板 `/`（英文 `/?lang=en`）；ledger 記下這個退路 | 自動；ledger 手動 |
| TC-021 | 作法2 | 功能 | 參數表假代理回 (a) loading (b) error (c) ready | 看 ⑤ 開頭 | 讀取狀態在 ⑤ 開頭：loading 為「…」＋文字，error 為「✗」＋原因，ready 為「✓」＋組數／參數數；都同時有符號與文字 | 自動 |

## US3 — 管線與版本一處決定（P1）

原話1「怎麼會確定了pipline版本後面又一個可調版本的地方」；原話5「版本只出現一次，選完管線後旁邊出現該管線的版本下拉選單，預設最新版」。

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-022 | K07；作法3 | 功能 | 「其他 nf-core 管線」分頁；網址帶 `pipeline=nf-core/ampliseq&src=new`；假代理回版本清單 `["2.18.0","2.17.0","2.16.1"]`（新到舊） | 開頁面 | 整頁只有一個 `name="revision"` 的可編輯控制項，是 `<select>`；選項依序等於該清單；`2.18.0` 為選中；沒有 `type="text"` 的 revision 輸入框 | 自動 |
| TC-023 | 作法3；2b TC-008 | 功能 | 「曾使用的管線」分頁，選一列（網址帶 pipeline、revision） | 看表單 | 版本只用隱藏欄 `name="revision"` 帶，沒有版本下拉也沒有文字框；各列自帶版本 | 自動 |
| TC-024 | 作法3；原話5 | 功能 | 其他 nf-core 分頁；POST 的 pipeline 與 shown_pipeline 不同，`revision` 空白（其餘欄位合規） | 按送出 | 303 到 `/launch?pipeline=…`（帶 `src=new`，英文帶 `lang=en`）；不是 400；頁面不出現 e_revision 句子；`request_launch` 沒被呼叫 | 自動 |
| TC-025 | 作法3；原話5 | 功能 | 接 TC-024 的 GET，版本清單讀好 | 看頁面與呼叫紀錄 | 下拉選中最新版；隱藏欄 `shown_revision` 等於該最新版；假代理的 `pipeline_files` 以該最新版被呼叫（參數表與流程圖用這一版讀） | 自動 |
| TC-026 | 作法3 | 功能 | 管線等於 shown_pipeline；POST 的 revision（下拉值）與 `shown_revision` 不同 | 按送出 | 303 重載，帶新版本；`request_launch` 沒被呼叫 | 自動 |
| TC-027 | 作法3 | 功能 | 管線、版本都與 shown_* 相同；其餘合規 | 按送出 | `request_launch` 呼叫一次，管線、版本正確；303 到 `/c/<id>` | 自動 |
| TC-028 | K08；S4；作法3 | 例外 | 其他 nf-core 分頁；`latest_release` 回 `loading` | 開頁面 | 顯示 S4（逐字），有「…」符號；沒有版本下拉；`<meta http-equiv="refresh" content="15">` 存在 | 自動 |
| TC-029 | K08；作法3 | 例外 | `latest_release` 回 `error` 且無快取（無 `revision`） | 開頁面；再 POST（管線等於 shown_pipeline，revision 空白） | 顯示「✗」＋原因；沒有版本下拉；POST 回 400 並列出 e_revision；不是 303 | 自動 |
| TC-030 | 作法3 | 功能 | `latest_release` 回 ready、`source=stale-cache`、`releases=["2.17.0","2.16.1"]`，帶 `why` | 開頁面 | 下拉只含這兩個快取版本、預設 `2.17.0`；顯示無法連線 GitHub 的說明（沿用 `g2_stale` 句型） | 自動 |
| TC-031 | 作法3（避免悄悄換版） | 例外 | 其他 nf-core 分頁，網址帶 `revision=2.10.0`，不在假代理清單裡 | 開頁面 | 下拉仍含 `2.10.0` 並選中它，不被換成最新版 | 自動 |
| TC-032 | 原話1、5；作法3 | 功能 | 其他 nf-core 分頁，下拉已出現 | 看整頁連結與控制項 | 頁面沒有任何第二個可改版本的入口：沒有「套用此版本」連結；`pipeline`／`revision` 以外沒有其他版本欄位；⑥ 只顯示 | 自動 |

## US4 — 版本清單來源（P1）

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-033 | K09；作法4 | 功能 | tags job 的 ls-remote 文字含 `v3.0.0`、`2.18.0`、`2.17.0`、`dev`、`master`、`2.19.0-rc1`，以及非數字的 tag | 呼叫 `actions.latest_release` | 回傳含 `releases`：只含可用 tag（`releases.usable`）、新到舊的 list[str]；`revision` 等於 `releases[0]`；其餘既有欄位不變 | 自動 |
| TC-034 | K09；作法4 | 功能 | 快取檔舊格式（entry 只有 `revision`、`checked_at`） | 呼叫 | `releases == [revision]`；新寫入的快取 entry 帶 `releases`，重讀得到同一份清單 | 自動 |
| TC-035 | 作法4 | 功能 | (a) stale-cache 路徑 (b) loading (c) error | 呼叫 | (a) `releases` 取自快取；(b)(c) `releases` 為空 list；`state`、`source`、`why`、`error` 規則不變 | 自動 |
| TC-036 | 作法4 | 例外 | 假代理的 `latest_release` 回傳沒有 `releases` 鍵（舊形狀） | 開頁面 | 頁面不報錯，下拉只含 `[revision]` | 自動 |

## US5 — 流程圖直接顯示（P1）

原話2「流程圖要在使用者決定pipline時直接顯示於正下方不需要額外點選打開」。

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-037 | K10；作法5；原話2 | 功能 | P／R 已定，圖讀好 | 開頁面 | ③ 內有 `<img src="/launch/diagram?pipeline=nf-core/ampliseq&revision=2.18.0">`（網址編碼同 `urllib.parse.urlencode(safe="/")`），`alt` 為「nf-core/ampliseq 2.18.0 流程圖」；英文頁有英文 alt | 自動 |
| TC-038 | K10；原話2 | 功能 | 同上 | 看位置 | `<img>` 在 ③ 的管線欄位（或所選管線列）之後，在 ④ 標題之前 | 自動 |
| TC-039 | K10；作法5 | 功能 | 同上 | 看頁面 | 沒有「開啟流程圖」「Open diagram」字樣，沒有 `class="dlink"`，沒有檔名與大小那一行 | 自動 |
| TC-040 | 原話2「不需要額外點選」 | 功能 | 圖讀好，且已填 run_name 使目前步驟移到後面的步驟（③ 狀態為「已完成」） | 看 ③ 的 `<details>` | ③ 帶 `open`（不論目前是哪一步），圖不需點開 | 自動 |
| TC-041 | K11；S5；作法5 | 例外 | 圖檔還在讀（`diagram` 已有、`image` 為 loading），以及 `files` 為 loading 兩種 | 開頁面 | 顯示 S5（逐字，含「…」符號）；沒有 `<img`；有 15 秒自動重整 | 自動 |
| TC-042 | K11；S6；作法5 | 例外 | 管線沒有流程圖（`diagram.status == "none"`） | 開頁面 | 顯示 S6（逐字）；沒有 `<img`；③ 狀態不卡成「讀取中」 | 自動 |
| TC-043 | 作法5 | 例外 | (a) `files` 整體 error (b) `diagram.status` 不是 ok／none (c) `image` error | 開頁面 | 顯示「✗」＋原因文字；沒有 `<img`；頁面其他區塊照常 | 自動 |
| TC-044 | 作法5 | 功能 | 還沒定管線版本（剛開頁） | 開頁面 | 沒有 `<img`、沒有指向 `/launch/diagram` 的連結 | 自動 |
| TC-045 | 作法5；既有 g04 | 功能 | 登入／未登入；png、svg、未就緒 | GET `/launch/diagram?…` | 行為與 base 相同：圖檔照傳、svg 帶無 script 的專屬 CSP、未就緒 404 一行、未登入走登入；既有 g04 測試全綠 | 自動 |
| TC-046 | 作法5；專長守則 | 功能 | 圖讀好 | 看 HTML 與樣式表 | `<img>` 用 class（沒有 `style=`）；樣式表有該 class 的 `max-width:100%` 與 `height:auto` | 自動 |

## US6 — 只放寬 /launch 的圖片安全設定（P1）

原話6「同意，只放寬自家圖片」；作法6。

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-047 | K12；作法6 | 功能 | 登入 | GET `/launch`（含帶管線版本、含 `lang=en`） | `Content-Security-Policy` 含 `img-src 'self'`；去掉這一項後，其餘與 base 的 CSP 逐字相同（`default-src 'none'; style-src …; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`） | 自動 |
| TC-048 | K12；作法6 | 功能 | POST 被擋（回 400）的頁面 | 看標頭 | 同 TC-047 | 自動 |
| TC-049 | K12；作法6 | 功能 | 登入 | GET `/`、`/settings`、`/usage`（或現有的看板／設定／用量頁）、`/c/<id>`、`/login`、`/launch/diagram`（png 與 svg） | 這些回應的 CSP 都不含 `img-src`，且與 base 逐字相同 | 自動 |
| TC-050 | 作法6 | 功能 | /launch 各狀態 | 檢查 CSP 與 HTML | CSP 不含任何外部網址、`*`、`data:`、`https:`；頁面所有 `src=` 都是站內路徑 | 自動 |

## US7 — 用字、狀態、前端限制

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-051 | K13；作法7 | 功能 | 狀態：讀好、讀取中、失敗、沒有樣本表、沒有環境（S1）、未登記（S2）、版本讀取中（S4）、版本讀不到、流程圖讀取中（S5）、沒有流程圖（S6）、POST 被擋回、曾使用分頁 | 取 `<main data-pane="middle">` 中文（去掉 `.ptbl`、`.scols` 說明欄） | 不含 22 個禁用詞；既有 2b 用字守門測試仍在、仍全綠 | 自動 |
| TC-052 | 作法2、3、5 | 功能 | 對應狀態 | 檢查文字 | S1～S6 六句逐字出現在對應狀態（包括頁尾標點與「…」） | 自動 |
| TC-053 | 作法7 | 功能 | 同上，`lang=en` | 檢查文字 | 每個新狀態有對應英文句，且不含中文字；不含禁用詞對應的口語 | 自動 |
| TC-054 | 專長守則 | 功能 | TC-013、015、019、028、029、041、042、043 的各狀態 | 檢查 HTML | 每個狀態同時有符號（✓／✗／…／○／—）與文字，不只靠 class 顏色 | 自動 |
| TC-055 | 專長守則；前端限制 | 功能 | 任何 /launch 狀態（含 img 顯示時） | 檢查 HTML | 沒有 `<script`、沒有 `style=` 屬性，只有一個樣式表 | 自動 |
| TC-056 | K14；專長守則 | 功能 | 樣式表 | 讀 CSS 字串 | 新增或修改的規則不含會超過 390px 的固定寬度，`img` 規則為 `max-width:100%` 且 `height:auto`；沒有 `overflow-x` 需求 | 自動 |
| TC-057 | 專長守則（手機、鍵盤、截圖） | 功能 | 全部區塊都有內容 | developer-agent 截 1440／390 × 中文／英文四張；只用鍵盤走過連結、下拉、`<details>`、送出鍵 | 390 寬無橫向捲動；圖依寬度縮小；焦點外框可見；截圖附 PR 給維護者判斷 | 手動 |
| TC-058 | 專長守則（Impeccable） | 功能 | 讀好的中英文頁各渲染成 HTML 檔 | 閱卷者跑 `impeccable detect <file.html>`（唯讀） | 無違反 DESIGN.md token／畫面／狀態；其他發現列「需要人看的事」 | 手動 |
| TC-074 | 專長守則（只用既有 token） | 功能 | 看樣式 diff | 閱卷者讀 `git diff` | 新增的樣式只用 DESIGN.md 已定義的色彩、字型、字級、間距、圓角，沒有自創顏色或數值 | 手動 |

## US8 — 送出與錯誤標示（沿用既有規則）

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-059 | 原話1 | 功能 | POST 缺分析名稱（其餘合規、shown_* 一致） | 按送出 | 400，列出 e_run_name；① 為「目前」；`request_launch` 沒被呼叫 | 自動 |
| TC-060 | 作法1 | 功能 | 分別造成：缺環境、缺管線或版本、缺樣本表、參數格式錯、`request_launch` 拒絕 | 各按送出 | 400，目前步驟依序標在 ②、③、④、⑤、⑥ | 自動 |
| TC-061 | 現行規則 | 功能 | 管線與 shown_pipeline 不同，且分析名稱空白 | 按送出 | 仍是 303 載入，不先報分析名稱的錯（與 base 同序） | 自動 |
| TC-062 | 憲法第2條（確認頁是唯一排佇列處） | 功能 | 所有 303 載入、400、一般送出 | 記錄 `request_launch` 與任何排佇列呼叫 | 303 與 400 沒有呼叫；一般送出只走到 `/c/<id>`；csrf 錯誤仍 403 不重載 | 自動 |
| TC-063 | 2b TC-003 延續 | 功能 | 其他 nf-core 分頁，讀好 | 看表單 | 管線、版本下拉、分析名稱、運算環境、樣本表、沿用分析、參數格子、進階框，全在同一個 `<form method="post" action="/launch">` 內；沒有 `method="get"` 表單 | 自動 |
| TC-073 | 原話3 逐字場景 | 功能 | 假代理：一個 available 環境、一個樣本表、版本清單、圖讀好 | ann 依序：看到分析名稱欄 → 填名稱 → 選運算環境 → 輸入 `ampliseq` 按送出（載入）→ 版本下拉預設最新、圖在下方 → 看樣本表 → 看參數 → 按送出 | 順序與他說的一致，最後到 `/c/<id>`，確認頁收到的名稱、環境、管線、版本、樣本表都對 | 自動 |

## 不在範圍

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-064 | 不做1；範圍 | 不在範圍 | 比對 base diff | 看 `web_settings.py` 與設定頁 | 設定頁沒被改（只有連過去） | 手動：`git diff` |
| TC-065 | 不做2 | 不在範圍 | 比對 base diff | 看 STRINGS 與側欄、看板、run 頁、設定頁字串 | 沒被改；只有 GUIDED 與 /launch 用的 `l_*`／`e_*`／`g_*`／`g2_*` 有改 | 手動：`git diff` |
| TC-066 | 不做3、4 | 不在範圍 | 比對 base diff 與測試 | 看 `<script`、MCP 工具清單、連線 | 沒有 script；MCP 工具清單與 base 相同；`socket.connect` 被擋時整套新測試仍通過 | 自動 |
| TC-067 | 2b 不做延續 | 不在範圍 | 其他 nf-core 分頁 | 看「搜尋全部 nf-core」 | 仍標示尚未開放，沒有搜尋輸入框或鍵 | 自動 |
| TC-068 | 原話6「只放寬自家圖片」 | 不在範圍 | 比對 diff | 看 CSP 與 `launch_diagram` | 沒有開放外部圖；平台沒有存圖或留副本，圖只經 `/launch/diagram` 由代理讀的結果提供 | 自動＋手動 |
| TC-069 | 範圍：檔案 | 不在範圍 | 比對 base diff | 看改動範圍 | `actions/__init__.py` 只動 `# ---- release-lookup-job` 區塊內的 `latest_release`；其餘只在計畫「範圍：檔案」列的檔 | 手動：`git diff` |

## 完成與文件

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-070 | 「允許改的斷言」 | 功能 | 比對 base 的測試檔 | 看每個改動的斷言 | 只改計畫列的種類（七步順序、前置檢查五列、流程圖連結與檔名大小、版本文字框、/launch 的 CSP 無 img-src、2b TC-010／023／006／007 等被牽動者、頁面雜湊、路由清單、`test_releases.py` 鍵集合）；每條在 ledger「2d」節有舊→新與理由；其他斷言沒有刪或放寬；`test-case*.md` 與計畫沒有在實作中被改 | 手動：閱卷者讀 diff 與 ledger |
| TC-071 | 範圍：文件 | 功能 | 看文件 | 閱讀 | `DESIGN.md` 的 /launch 線框與步驟順序改成六步，沒有「前置檢查」一步，也沒有「說明檔名的流程圖附註」；`docs/PLATFORM.md` 補六步、版本下拉、圖直接顯示、/launch 的 `img-src 'self'`；`docs/TESTING.md`「Guided launch」節手動步驟改為新流程 | 手動 |
| TC-072 | 完成標準；GATE | 功能 | 看完成記號 | 比對 | 完成記號為 `GREEN <HEAD sha>` 且工作樹乾淨；全套綠（WSL，清掉 `__pycache__`）；K01～K14 都在 | 手動：閱卷者查 gate 與 CI |
