# 測試案例：資料集可以登記在雲端 bucket（cloud-upload，平台這一半）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這個功能沒有 spec.md；`specs/cloud-upload/plan.md` 同時是規格（其中「維護者原話」、「完成標準」、「失敗先行測試」、「不做」、「裁決」是依據）。
-->

**規格**：`specs/cloud-upload/plan.md`（本功能以計畫代替 spec.md）　**總覽**：`test-case-overview.md`

名詞（第一次出現各一句話）：
- **bucket**：Google Cloud 上放檔案的「大桶子」，位置寫成 `gs://桶子名/資料夾/檔名`。
- **workDir**：一個 Google Batch 計算環境（compute environment，平台上登記的一個「在哪裡跑分析」的設定）裡寫的工作位置，例如 `gs://lab-bucket/work`；它前面那一段 `lab-bucket` 就是該環境的 bucket。
- **前綴**：位置的開頭部分。alice 的前綴是 `gs://lab-bucket/uploads/alice/`，她登記的檔案都必須在這個前綴底下。
- **sink／chunk**：串流時，檔案被切成一塊一塊（chunk）送出，接收的那端叫 sink。本任務只測「平台這一側怎麼數、怎麼停」，接收端在測試裡是假的。

測試用的固定情境（來自計畫）：兩位使用者 alice、bob（計畫的 d.a、d.b）；環境 `gcb1` 屬於 alice，workDir 是 `gs://lab-bucket/work`；環境 `gcb2` 屬於 bob，workDir 是 `gs://other-bucket/work`。以下「登記」指 `register_dataset(…, destination="gcb1")`，「草稿」指 `draft_samplesheet`，「檢查上傳」指 `check_web_upload`。「驗證方式 自動」一律指 `platform/tests/test_cloud_upload.py`，除非另註。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

## User Story 1 — 把資料集登記在雲端位置（優先度 P1）

維護者原話：「雲端上傳＝平台代傳到使用者自己的 bucket、不落地」「資料集登記 bucket 路徑」「雲端第一個真實使用者＝他自己的自費帳號」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話「資料集登記 bucket 路徑」「第一個真實使用者＝他自己」；測試 13 | 功能 | alice 有環境 `gcb1`（workDir `gs://lab-bucket/work`）；她要登記兩個檔 `gs://lab-bucket/uploads/alice/a_R1.fastq.gz`、`…/a_R2.fastq.gz`，樣本表兩欄寫的就是這兩個位置 | alice 用 `destination="gcb1"` 登記資料集 | 回覆成功；資料表多一列，屬於 alice | 自動 |
| TC-002 | 測試 13；作法 B（files_json 不加欄位） | 功能 | 同 TC-001 已登記 | alice 取得該資料集 | 檔案清單裡每個項目的欄位只有 `path`（有給大小時再加 `size_bytes`），`path` 都以 `gs://` 開頭；沒有「雲端與否」之類的新欄位 | 自動 |
| TC-003 | 測試 13；作法 B「不需要 migration」 | 功能 | 同 TC-001 已登記 | 讀 `datasets` 資料表的欄位清單，與基準分支（改動前）比對 | 欄位清單一字不差，沒有新增欄位 | 自動 |
| TC-004 | 裁決 5（不要求環境 available） | 功能 | `gcb1` 的狀態是「建立中」（不是 available，例如預檢還沒過） | alice 用 `destination="gcb1"` 登記 | 回覆成功（登記只寫名字與位置，不要求環境能用） | 自動 |
| TC-005 | 作法 A.4、B（終端機 owner 為空） | 功能 | 終端機（沒有使用者身分）呼叫；檔案位置是 `gs://lab-bucket/uploads/…` 底下的檔 | 終端機用 `destination="gcb1"` 登記 | 回覆成功；終端機登記的檔只要在 `gs://lab-bucket/uploads/` 底下就收 | 自動 |
| TC-006 | 測試 21；作法 B（草稿） | 功能 | alice 有 4 個位置：`gs://lab-bucket/uploads/alice/` 底下的 `a_R1`、`a_R2`、`b_R1`、`b_R2`（皆 `.fastq.gz`） | alice 用 `destination="gcb1"` 做樣本表草稿 | 配成兩對（a、b），`unpaired`（沒配上的）是空的；草稿裡寫的是完整的 `gs://` 位置 | 自動 |
| TC-007 | 作法 A.4、B（單層檔名＝object_url） | 功能 | alice 給的名字是單層檔名 `a_R1.fastq.gz`、`a_R2.fastq.gz` | alice 用 `destination="gcb1"` 做草稿 | 配成一對；草稿裡的位置是 `gs://lab-bucket/uploads/alice/a_R1.fastq.gz` 與 `…/a_R2.fastq.gz` | 自動 |
| TC-008 | 測試 21（仿 012c TC-060）；原話「不落地」 | 功能 | 先記下平台資料夾與 uploads 資料夾裡所有檔案的清單 | alice 做雲端草稿（成功與被拒各一次） | 做完後清單與做之前完全相同（草稿不寫入任何東西） | 自動 |
| TC-009 | 原話「不落地」；作法 A 前言（全程不打開檔案） | 功能 | 先記下平台資料夾、uploads 資料夾裡所有檔案（名稱與大小） | alice 雲端登記一份資料集，再做一次雲端「檢查上傳」（含一個超過 2 GB 的檔） | 除了平台資料庫檔本身，沒有多出任何新檔案（沒有暫存、中繼檔或複製） | 自動 |
| TC-010 | 測試 22；作法 B（預設 `None`） | 功能 | 讀三個函式的簽章 | 檢查 `destination` 參數 | 三個函式 `draft_samplesheet`、`check_web_upload`、`register_dataset` 都有關鍵字參數 `destination`，預設值是 `None`；原有位置參數的順序沒變 | 自動 |
| TC-011 | 測試 22；完成標準第 4 條（不傳 destination 行為不變） | 功能 | 不改動 `platform/tests/test_datasets.py` | 原封不動跑 `test_datasets.py` 全部 | 全部通過（沒有被改過的斷言，沒有被略過的案例） | 自動：`platform/tests/test_datasets.py` |
| TC-012 | 作法 B（`size_bytes` 規則不變） | 例外 | alice 登記雲端檔，其中一個 `size_bytes` 給 -1 | alice 用 `destination="gcb1"` 登記 | 回覆失敗，說大小必須是 0 以上的整數；資料表沒有新列 | 自動 |

## User Story 2 — 不屬於你的位置，一律白話拒絕（優先度 P1）

維護者原話：「平台代傳到**使用者自己的** bucket」。位置只能落在呼叫者自己的前綴、且 bucket 必須是該環境 workDir 的 bucket。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 測試 14；原話「使用者自己的 bucket」 | 例外 | alice 要登記的檔位置在 `gs://lab-bucket/uploads/bob/a_R1.fastq.gz`（bob 的前綴） | alice 用 `destination="gcb1"` 登記 | 回覆失敗；訊息點名 alice 自己的前綴 `gs://lab-bucket/uploads/alice/`，完全不出現 bob 的任何東西；沒有新列 | 自動 |
| TC-014 | 測試 15 | 例外 | 位置是 `gs://other-bucket/uploads/alice/a_R1.fastq.gz`（bucket 不是 `gcb1` workDir 的那個） | alice 用 `destination="gcb1"` 登記 | 回覆失敗；訊息說明 bucket 必須就是該計算環境 workDir 所在的 bucket；沒有新列 | 自動 |
| TC-015 | 測試 4（字首相同的別人） | 例外 | 有一位使用者名字是 `alicex`（或位置 `gs://lab-bucket/uploads/alicex/a_R1.fastq.gz`） | alice 登記這個位置 | 回覆失敗（`alicex` 不是 alice 的前綴，只是字首相同） | 自動 |
| TC-016 | 測試 4；作法 A.5（前綴本身不算檔案） | 例外 | 位置是 `gs://lab-bucket/uploads/alice/`（只有前綴，後面沒有檔名） | alice 登記 | 回覆失敗 | 自動 |
| TC-017 | 測試 2；作法 A.2（`..` 不得出現） | 例外 | 位置是 `gs://lab-bucket/uploads/alice/../bob/a_R1.fastq.gz` | alice 登記 | 回覆失敗；沒有新列 | 自動 |
| TC-018 | 測試 17；作法 B（不得混雜） | 例外 | 檔案清單一個是 `gs://lab-bucket/uploads/alice/a_R1.fastq.gz`、一個是本機路徑 | alice 用 `destination="gcb1"` 登記 | 回覆失敗，說一份資料集不能同時混本機路徑與雲端位置；沒有新列 | 自動 |
| TC-019 | 測試 18（同 012c TC-045） | 例外 | 樣本表某格寫 `gs://lab-bucket/uploads/alice/c_R1.fastq.gz`，但登記的檔案清單裡沒有它 | alice 用 `destination="gcb1"` 登記 | 回覆失敗，指出樣本表裡有檔案不在登記的檔案內；沒有新列 | 自動 |
| TC-020 | 測試 18（同 012c TC-052） | 例外 | 樣本表多一欄，某格是 `https://example.org/x_R1.fastq.gz` | alice 用 `destination="gcb1"` 登記 | 回覆失敗，訊息含「網址」；沒有新列 | 自動 |
| TC-021 | 測試 19；原話「憑證不進資料庫」 | 例外 | 位置是 `gs://lab-bucket/uploads/alice/` 加上 `abf_pat_` 再接 30 個英數字（像個人存取權杖的值；測試裡用字串拼接組出） | alice 登記，之後讀平台資料庫檔的位元組（含 `-wal`） | 回覆失敗；資料表仍是空的；位元組裡找不到 `abf_pat_` 這串 | 自動 |
| TC-022 | 作法 A.8；專長守則（回應不含密鑰） | 例外 | 同 TC-021 | 看被拒的回覆文字 | 訊息不原樣複述那個像憑證的值 | 自動 |
| TC-023 | 測試 21 | 例外 | 草稿裡四個位置，其中一個在 `gs://lab-bucket/uploads/bob/` 底下 | alice 用 `destination="gcb1"` 做草稿 | 整份草稿被拒（不是只丟掉那一個）；沒有部分結果 | 自動 |
| TC-024 | 測試 16；專長守則（跨使用者，寫） | 例外 | `gcb1` 屬於 alice；bob 沒有權限 | bob 用 `destination="gcb1"` 登記；另一次用 `destination="no-such-env"` 登記 | 兩次的回覆（把環境名換成 `<name>` 後）一字不差；不透露 `gcb1` 存在或屬於誰；沒有新列 | 自動 |
| TC-025 | 測試 16 | 例外 | 同 TC-024 | bob 分別用 `destination="gcb1"` 與 `"no-such-env"` 做草稿 | 兩次回覆（換掉環境名後）一字不差 | 自動 |
| TC-026 | 測試 16 | 例外 | 同 TC-024 | bob 分別用 `destination="gcb1"` 與 `"no-such-env"` 檢查上傳 | 兩次回覆（換掉環境名後）一字不差 | 自動 |
| TC-027 | 作法 B（同一句「找不到計算環境」） | 例外 | alice 用不存在的環境名 | alice 登記 | 回覆失敗，說找不到計算環境（白話）；沒有新列 | 自動 |
| TC-028 | 測試 5；作法 A.3 | 例外 | alice 擁有一個 Slurm 環境（不是 Google Batch），另有一個沒有 workDir 的環境 | alice 分別拿這兩個環境當 `destination` 登記 | 兩次都失敗，白話說明這個環境不能放雲端資料；沒有新列 | 自動 |
| TC-029 | 專長守則（跨使用者，讀）；作法 B（擁有者規則不變） | 例外 | alice 已登記一份雲端資料集 `proj`／`v1` | bob 列出資料集 | 清單裡沒有 alice 的 `proj` | 自動 |
| TC-030 | 專長守則（跨使用者，讀）；仿 012c TC-068 | 例外 | 同 TC-029 | bob 取得 `proj`／`v1`；另一次取得一個誰都沒登記過的名稱 | 兩次回覆除了名稱外一字不差；不透露存在、屬於誰 | 自動 |
| TC-031 | 專長守則（錯誤訊息白話、不露堆疊／SQL／內部路徑） | 例外 | 分別觸發 TC-013、014、017、018、027、028 的拒絕 | 看每一則回覆的文字 | 每則都說明發生了什麼事、該怎麼處理；沒有「Traceback」、SQL 語句或平台主機的內部路徑 | 自動 |

## User Story 3 — 單檔超過 2 GB，回一行在你電腦上跑的指令（優先度 P1）

維護者原話：「>2 GB 回指令」「上傳 >2 GB 改給指令」。2 GB 是十進位 2,000,000,000 位元組，剛好等於上限仍收、多一個位元組就不收。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 測試 20；原話「剛好 2,000,000,000 仍收」（沿用 012c TC-024） | 功能 | alice 的一個檔恰好 2,000,000,000 位元組 | alice 用 `destination="gcb1"` 檢查上傳 | 回覆成功，該檔在 `accepted`；`over` 是空的 | 自動 |
| TC-033 | 測試 20；沿用 012c TC-026 | 例外 | 一個檔 `big_R1.fastq.gz` 是 2,000,000,001 位元組 | alice 用 `destination="gcb1"` 檢查上傳 | 回覆失敗；`over` 列出 `big_R1.fastq.gz` | 自動 |
| TC-034 | 測試 20；原話「大檔給指令」；裁決 3 | 例外 | 同 TC-033 | 看回覆裡的 `command` | 指令以 `gcloud storage cp ` 開頭，含 alice 的前綴 `gs://lab-bucket/uploads/alice/`，不含 bob 的前綴 | 自動 |
| TC-035 | 作法 B（第二句換成 bucket 版） | 例外 | 同 TC-033 | 看回覆的整段文字 | 第二句說：如果檔案已經在這個 bucket 裡，就放進同一個前綴 `gs://lab-bucket/uploads/alice/`；不再出現原本的 `push.sh` 與「國網」說法 | 自動 |
| TC-036 | 作法 B（`ok:false` 形狀不變） | 例外 | 同 TC-033 | 看回覆的欄位 | `ok` 為 false，且 `message`、`over`、`command`、`accepted` 四個欄位都在 | 自動 |
| TC-037 | 測試 20（同 012c TC-029） | 例外 | 四個檔：三個各 500,000,000 位元組、一個 2,500,000,000 位元組 | alice 雲端檢查上傳 | `over` 只列那個大檔；三個小檔在 `accepted` | 自動 |
| TC-038 | 作法 B（逐檔，不是總和；沿用 012c TC-025） | 功能 | 四個檔各 1,999,999,999 位元組（總和遠超 2 GB） | alice 雲端檢查上傳 | 回覆成功，4 檔都被接受 | 自動 |
| TC-039 | 作法 B（`sizes` 驗證不變） | 例外 | `sizes` 裡有一個檔的大小是 -1（另一次是非整數） | alice 雲端檢查上傳 | 回覆失敗，說明大小必須是檔名對位元組數；與不帶 `destination` 時的規則相同 | 自動 |
| TC-040 | 作法 A.4（終端機沒有使用者名） | 功能 | 終端機（沒有使用者身分）呼叫，檔案超過 2 GB | 終端機用 `destination="gcb1"` 檢查上傳 | 指令與提示裡的目的地是 `gs://lab-bucket/uploads/rawdata/`（沒有使用者名那一層） | 自動 |
| TC-041 | 測試 6；作法 A.6、A.8 | 例外 | 呼叫 `big_file_command` 給 alice 的環境 | 看回傳字串 | 只有一行；以 `gcloud storage cp ` 開頭；含 `gs://lab-bucket/uploads/alice/rawdata/` 與留給人填的 `<你電腦上的資料夾>`；不含專案名、不含 `gcp-sa`、不含 `.json` | 自動 |

## User Story 4 — 位置語言：怎麼讀、怎麼判斷屬於誰（優先度 P1，`cloud_store.py` 純函式）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-042 | 測試 1；作法 A.2 | 功能 | 位置 `gs://lab-bucket/uploads/alice/a_R1.fastq.gz` | `parse_gs` | 得到 `("lab-bucket", "uploads/alice/a_R1.fastq.gz")` | 自動 |
| TC-043 | 測試 2；作法 A.2 | 例外 | 逐一給：`s3://b/x`、`https://b/x`、`gs://B/x`（大寫）、`gs://ab/x`（太短）、`gs://b-ok/../x`、`gs://b-ok/a/../../x`、`gs://b-ok/`（沒有物件名）、`gs://b-ok//x`（物件名以 `/` 開頭）、含 NUL 或換行的位置、物件名 1025 位元組 | 各自 `parse_gs` | 每一個都丟 `CloudPathError` | 自動 |
| TC-044 | 測試 2；專長守則 | 例外 | 同 TC-043 的每一個 | 看錯誤訊息 | 每則是白話句子，不含堆疊或程式內部名稱 | 自動 |
| TC-045 | 測試 2；作法 A.2（只收 gs://） | 例外 | 給 `s3://b/x`、`https://b/x`、`file://b/x` | `parse_gs` | 三個都被拒，訊息說「只收 gs://」 | 自動 |
| TC-046 | 作法 A.2（bucket 規則邊界） | 功能 | bucket 名分別為：3 字元、63 字元、含 `-`／`_`／`.` 在中間、頭尾是數字 | 各自 `parse_gs`（後面接合法物件名） | 全部成功 | 自動 |
| TC-047 | 作法 A.2（bucket 規則邊界） | 例外 | bucket 名分別為：2 字元、64 字元、含大寫、以 `-` 開頭、以 `.` 結尾 | 各自 `parse_gs` | 全部丟 `CloudPathError` | 自動 |
| TC-048 | 作法 A.2（物件名 ≤ 1024 位元組） | 功能 | 物件名恰好 1024 個 UTF-8 位元組 | `parse_gs` | 成功 | 自動 |
| TC-049 | 測試 2 | 例外 | 物件名 1025 個 UTF-8 位元組 | `parse_gs` | 丟 `CloudPathError` | 自動 |
| TC-050 | 作法 A.2（以 UTF-8 位元組計，不是字數） | 例外 | 物件名是 600 個雙位元組的中文字（600 字、1200 位元組） | `parse_gs` | 丟 `CloudPathError` | 自動 |
| TC-051 | 測試 3；作法 A.5（不做 URL 解碼） | 功能 | 位置 `gs://lab-bucket/uploads/alice/%2e%2e/bob/x` | `parse_gs` 與 `inside_prefix`（前綴是 alice 的） | 物件名保留字面 `%2e%2e`；位置仍在 alice 的前綴內，沒有被當成 `..` 離開 | 自動 |
| TC-052 | 測試 4 | 功能 | 前綴 `gs://lab-bucket/uploads/alice/`，位置 `gs://lab-bucket/uploads/alice/x` | `inside_prefix` | 為真 | 自動 |
| TC-053 | 測試 4；作法 A.5 | 例外 | 位置就是前綴本身 | `inside_prefix` | 為假 | 自動 |
| TC-054 | 測試 4 | 例外 | 位置 `gs://other-bucket/uploads/alice/x`（同前綴但不同 bucket） | `inside_prefix` | 為假 | 自動 |
| TC-055 | 測試 4 | 例外 | 位置 `gs://lab-bucket/uploads/alicex/x` | `inside_prefix`（前綴是 alice 的） | 為假 | 自動 |
| TC-056 | 測試 5；作法 A.3 | 功能 | Google Batch 環境 workDir `gs://lab-bucket/work` | `workdir_bucket` | 得到 `lab-bucket` | 自動 |
| TC-057 | 作法 A.3（「workDir 所在的 bucket」）；平台既有規則允許 workDir 只寫 bucket | 功能 | Google Batch 環境 workDir 是 `gs://lab-bucket`（後面沒有資料夾） | `workdir_bucket` | 得到 `lab-bucket`，不丟錯 | 自動 |
| TC-058 | 測試 5 | 例外 | Slurm 環境；另一個沒有 workDir 的環境 | 各自 `workdir_bucket` | 都丟 `CloudPathError` | 自動 |
| TC-059 | 測試 14 前提；作法 A.4 | 功能 | alice 的環境；另一次 owner 為空 | `upload_prefix` | alice：`gs://lab-bucket/uploads/alice/`；owner 為空：`gs://lab-bucket/uploads/` | 自動 |
| TC-060 | 作法 A.4 | 功能 | 檔名 `a_R1.fastq.gz`，owner alice | `object_url` | 得到 `gs://lab-bucket/uploads/alice/a_R1.fastq.gz` | 自動 |
| TC-061 | 作法 A.4 | 例外 | 檔名分別為：`x/y`、`x\y`、`..`、含 NUL、空字串、256 個字元 | 各自 `object_url` | 全部丟 `CloudPathError` | 自動 |
| TC-062 | 作法 A.4（長度 1～255） | 功能 | 檔名恰好 255 個字元 | `object_url` | 成功 | 自動 |

## User Story 5 — 串流核心：一塊一塊轉交、超過就停、出錯就中止（優先度 P2，與傳輸方式無關）

維護者原話：「不落地」。核心用假的接收端與假的資料塊測試，不連網、不啟動程式。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-063 | 測試 7 | 功能 | 5 塊共 1000 位元組；宣告大小 1000 | `stream_into` | 回覆成功，`received` 是 1000；接收端依序收到那 5 塊；`close` 呼叫一次、`abort` 零次 | 自動 |
| TC-064 | 測試 8；作法 A.7② | 例外 | 宣告 1000，實際送出 1001 位元組 | `stream_into` | 回覆失敗（`ok` 為 false），帶 `message` 與 `received` | 自動 |
| TC-065 | 測試 8 | 例外 | 同 TC-064 | 看接收端被呼叫的次數 | `abort` 一次、`close` 零次 | 自動 |
| TC-066 | 測試 8；作法 A.7②（停止讀下一塊） | 例外 | 同 TC-064，用會記錄「被取用幾次」的資料塊來源 | 看來源被取用的次數 | 超過的那一瞬間之後，後面的塊沒有被讀取 | 自動 |
| TC-067 | 測試 9；原話「>2 GB 改給指令」 | 例外 | `limit=2_000_000_000`，宣告大小 `limit+1`（只備兩個小塊） | `stream_into` | 回覆失敗；接收端 `write` 零次（一塊都沒轉交） | 自動 |
| TC-068 | 測試 10；作法 A.7③ | 例外 | 宣告 1000，只送 999 位元組 | `stream_into` | 回覆失敗（短了）；`abort` 被呼叫、`close` 沒有 | 自動 |
| TC-069 | 作法 A.7②（「超過」才停，剛好等於不算超過） | 功能 | `limit=1000`、宣告 1000、剛好送 1000 位元組 | `stream_into` | 回覆成功，`received` 為 1000 | 自動 |
| TC-070 | 測試 11；作法 A.7⑤ | 例外 | 資料塊來源在途中丟出 `RuntimeError`（訊息含 `token=abc123 /home/x/gcp-sa.json`） | `stream_into` | 回覆失敗；`abort` 一次；訊息只說「傳輸中斷」之類的白話 | 自動 |
| TC-071 | 測試 11；作法 A.7⑤ | 例外 | 接收端 `write` 丟同樣的例外 | `stream_into` | 回覆失敗；`abort` 一次 | 自動 |
| TC-072 | 測試 11；專長守則（回應不含密鑰） | 例外 | 同 TC-070、TC-071 | 把回覆轉成文字 | 文字裡沒有 `abc123`、`gcp-sa`、`/home` | 自動 |
| TC-073 | 測試 12；作法 A.7①（不累積） | 功能 | 資料塊來源產出 200 塊、每塊 1 MiB（同一個 bytes 物件），接收端立刻丟棄 | `stream_into`，並以記憶體追蹤或弱參照量測 | 沒有任何清單或 bytearray 累積全部位元組（記憶體只持有目前這一塊） | 自動 |
| TC-074 | 原話「不落地」；作法 A 前言 | 功能 | 先記下測試用資料夾與目前工作資料夾的檔案清單 | 跑 TC-063 與 TC-064 的情境 | 清單完全相同（核心沒有寫出任何檔案） | 自動 |

## User Story 6 — 範圍與文件（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-075 | 不做：位元組通道、新工作種類、上傳路由、MCP 接線；「必須更新的既有斷言」 | 不在範圍 | 改動完成 | 不改動地跑 `test_actions_layer.py`（唯讀工具基準與 `READ_TOOLS`）、`jobs.kind` 清單與 `launches`／`jobs`／`compute_envs` 欄位的既有斷言 | 全部通過；工具個數、`UNSUPPORTED` 長度（12）、`jobs.kind` 六種、各表欄位都沒變（沒有新工具、新路由、新工作種類） | 自動：`platform/tests/test_actions_layer.py`、`platform/tests/test_gcb_launch.py` |
| TC-076 | 不做：MCP／動作層接線；待裁決第 2 項 | 不在範圍 | 改動完成 | 不改動地跑 `test_datasets.py` 的 TC-064（`actions/__init__.py`、`mcp_server.py`、`web.py`、`web_board.py`、`store.py` 找不到資料集函式名） | 通過（`destination` 沒有被接到任何對外入口） | 自動：`platform/tests/test_datasets.py` |
| TC-077 | 測試 27；裁決 7（不新增公開函式） | 不在範圍 | 改動完成 | 取出 `datasets` 的公開函式清單 | 剛好是 `check_web_upload, draft_samplesheet, get_dataset, list_datasets, pair_fastq, register_dataset`，名稱不含 delete／remove／share／update／edit／rename／unregister | 自動 |
| TC-078 | 不做：刪除 work、30 天提醒 | 不在範圍 | 改動完成 | 列出 `cloud_store.py` 的公開函式名並掃兩個來源檔 | 沒有任何刪除、到期、提醒類的函式或字眼（如 delete、remove、expire、remind）；沒有刪檔的程式 | 自動 |
| TC-079 | 不做：校驗和；測試 23／TC-061 | 不在範圍 | 改動完成 | 掃 `cloud_store.py` 與 `datasets.py`；看 `stream_into` 的回覆欄位 | 原始碼沒有 `hashlib`、`md5`、`sha` 開頭的字；回覆只有 `ok`、`received`、`message`，沒有雜湊欄位 | 自動 |
| TC-080 | 不做：AWS S3／Azure | 不在範圍 | alice 要登記的位置是 `s3://lab-bucket/uploads/alice/a_R1.fastq.gz` | alice 用 `destination="gcb1"` 登記 | 回覆失敗，說只收 `gs://`；沒有新列 | 自動 |
| TC-081 | 不做：新增依賴、改 pyproject／constraints；測試 25 | 不在範圍 | 改動完成 | 讀 `platform/pyproject.toml` 與 `platform/constraints.txt` 的內容 | 兩個檔都不含 `google`；內容與基準分支相同 | 自動 |
| TC-082 | 不做：把 gs:// 位置帶進送出流程 | 不在範圍 | 改動完成 | 驗收者比對 `platform/abf_platform/actions/__init__.py`、`pipeline_launch.py`、`platform/abf_launch/build.py` 與基準分支 | 三個檔沒有任何差異（本任務沒有改送出流程） | 手動：驗收者 `git diff <base>...HEAD`（`docs/TESTING.md` 的 cloud-upload 小節列出此步） |
| TC-083 | 範圍：檔案（只准改四個）；完成標準第 2 條 | 不在範圍 | 改動完成 | 驗收者 `git diff --name-only <base>...HEAD` | 只有 `platform/abf_platform/actions/datasets.py`、`platform/abf_platform/cloud_store.py`、`platform/tests/test_cloud_upload.py`、`docs/TESTING.md`（另可有本功能的 `specs/cloud-upload/` 檔）；沒有 `cli.py`、`store.py`、`receiver.py`、`deploy/`、`configs/sites/*`、`docs/OPERATIONS.md`、`docs/INSTALL.md` | 手動：驗收者 `git diff`（同上） |
| TC-084 | 不做：改任何現有測試的斷言 | 不在範圍 | 改動完成 | 驗收者逐一比對被改動的既有測試檔與基準分支 | 沒有任何斷言被刪除、放寬或略過；`test_datasets.py`、`test_gcb_ce.py`、`test_gcb_launch.py`、`test_station_envs.py`、`test_guidance.py` 沒有差異 | 手動：驗收者 `git diff`（同上） |
| TC-085 | 完成標準第 5 條 | 功能 | 改動完成 | 讀 `docs/TESTING.md` | 有「cloud-upload」小節，且明寫：端到端（真的把檔案傳進 bucket）要等位元組通道任務，目前只能驗到登記與拒絕 | 手動：`docs/TESTING.md` |
| TC-086 | 完成標準第 5 條（手動驗收步驟具體可照做） | 功能 | 同 TC-085 | 驗收者照小節走一遍 | 每一步都說清楚要做什麼、看到什麼才算過（至少包含：登記一份雲端資料集看到成功、登記別人的前綴看到被拒、超過 2 GB 看到一行指令），不需要讀程式 | 手動：`docs/TESTING.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-087 | 第 1 條（新檔要說明為什麼不用現成的）；測試 23 前提；TC-070 | 功能 | 兩個新 `.py` 檔 | 跑 `test_scope.py` 的 TC-070 | `cloud_store.py` 與 `test_cloud_upload.py` 前 40 行各有 `# Nothing existing:` 且說明至少 15 字 | 自動：`platform/tests/test_scope.py` |
| TC-088 | 第 2 條（不開網路、不啟動程式）；測試 23；TC-061／TC-071 | 例外 | 改動完成 | 掃 `cloud_store.py` 原始碼 | 沒有 `open(`、`subprocess`、`os.system`、`socket`、`urllib`、`httpx`、`requests`、`import google`、`boto3`、`azure`；`test_scope.py` 的 TC-061、TC-071 對新檔通過 | 自動 |
| TC-089 | 測試 24；TC-061（不拆字） | 例外 | 改動完成 | 掃 `cloud_store.py` 與 `datasets.py`；另把兩個檔的引號、加號、空白全部拿掉後再掃一次 | 兩種掃法都找不到 `station` 這個字（沒有拆字、拼字；註解寫的是「the agent on the platform host」） | 自動 |
| TC-090 | 第 3 條（不寫死位置） | 例外 | 改動完成 | 掃 `cloud_store.py` 與 `datasets.py`（不含測試檔） | 沒有寫死的 bucket 名（如 `lab-bucket`）、`/home`、`/work`、`/scratch`、`/staging`、`/lustre` 之類的路徑；bucket 一律來自計算環境的 workDir | 自動 |
| TC-091 | 測試 26；原話「憑證不進資料庫」 | 例外 | 改動完成 | 掃 `cloud_store.py` 與 `datasets.py` | 不含 `gcp-sa`、`GOOGLE_APPLICATION_CREDENTIALS`、`CLOUDSDK`、`.json` | 自動 |
| TC-092 | 作法 A.8、目標第 3 點（沒有任何金鑰路徑的參數） | 例外 | 改動完成 | 讀 `cloud_store.py` 每個函式的參數名與 `datasets.py` 三個新增參數 | 沒有任何接收金鑰檔路徑或金鑰內容的參數；回覆裡也沒有這類欄位 | 自動 |
| TC-093 | 完成標準第 6 條 | 例外 | 改動完成 | 驗收者在回報內容包、資料庫、日誌、測試輸出、PR 說明搜站台金鑰檔名與 `private_key` | 搜不到任何金鑰片段 | 手動：驗收者 `grep -r`（完成標準） |
| TC-094 | 專長守則（資料結構沒變動要在計畫或 PR 寫「不需要 migration」的理由）；作法 B | 功能 | 改動完成 | 驗收者讀 PR 說明 | 明寫「不需要 migration」與理由（`datasets` 表欄位全不動，雲端位置存在既有 `files_json` 的 `path`），並逐條寫「沒動」的既有斷言 | 手動：驗收者讀 PR 說明 |
| TC-095 | 第 3 條與 012c 的既有規則；「必須更新的既有斷言」 | 功能 | 改動完成 | 不改動地跑 `test_datasets.py` 的 TC-059（無 `open(`／`os.stat`）、TC-061（無雜湊字）、TC-078（無 `subprocess`／`jobs`／`confirm`／`queue`／`submit` 等）、TC-081（無寫死路徑）、TC-085（無刪改檔案的字） | 全部通過：新增的程式碼同樣守住這些掃描 | 自動：`platform/tests/test_datasets.py` |
| TC-096 | 完成標準第 1 條 | 功能 | 改動完成 | 跑 `platform/tests/` 全套與 `tests/platform_test.sh` | 全綠，包含 `test_cloud_upload.py` 全部、`test_scope.py` 全部；沒有被略過的案例 | 自動：`tests/platform_test.sh` |
