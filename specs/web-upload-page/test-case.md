# 測試案例：網頁上傳資料頁（雲端運算環境）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Language: 繁體中文; identifiers (TC-, 路徑, 函式名) stay as they are.
-->

**規格**：`specs/web-upload-page/plan.md`（本任務沒有獨立 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」。

## 共用設定（每條 TC 的「前置條件」若沒另寫，就是這個）

- 使用者 **alice**：已用一般密碼登入（不是臨時密碼）；有雲端運算環境 `gcb1`（Google Batch，status 為 available）。
- 使用者 **bob**：也已登入；有自己的環境 `gcb2`（Google Batch，available）。
- 「上傳夾」＝平台上傳資料夾裡屬於該使用者的子資料夾，即 `<uploads>/<user>/`。
- 測試用的雲端環境一律是 fixture，不連真雲端；「工作」＝送給站台代理的 `put_upload` 工作，測試直接改它的結果來模擬站台回報。
- 測試用的檔案很小；「大小上限」在測試裡可調成小數字（計畫：測試用可調上限或假大小串流），實際預設值是 2,000,000,000 位元組。
- 「成對檔」＝`sampleA_R1.fastq.gz` 與 `sampleA_R2.fastq.gz`。
- 驗證方式寫「自動」的，測試放在 `platform/tests/test_web_upload.py`（或該列註明的既有測試檔），每個測試在註解寫它的 TC 編號。

## 維護者原話與 DESIGN.md 原文（逐字對應的 TC）

1. 「加速進行，這禮拜做完"還沒做，要讓同事不問人就能自己用完的部分"」（10-28）→ TC-020、TC-024、TC-079、TC-083、TC-132
2. DESIGN.md 第 55 行「Upload data」原文：`Upload data: drop zone (≤ ~2 GB per file; large FASTQ via the AI and push.sh; files go through the site agent to the person's own site or cloud storage, platform keeps no copy); Create samplesheet (auto-pair R1/R2, columns from the chosen pipeline's schema_input.json, makes a new version); Uploaded data table with version, used by, checksum, updated.` → TC-009、TC-010、TC-034、TC-101、TC-124、TC-125、TC-126
3. ADR 0010 10-25 更正（第 109-114 行）：「The press of "upload" is the confirmation」「A staged copy on the platform host is allowed … the size of the cloud object equals the size of the local file, that one staged copy is deleted」→ TC-024、TC-021、TC-095、TC-101
4. 「先把功能做起來吧，以後再改美觀」（10-23）→ TC-016、TC-119、TC-124

## User Story 1 — 上傳頁 `GET /upload`：選環境、填資料集、選檔（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；原話 1 | 功能 | alice 有 `gcb1`（available） | alice 開 `GET /upload` | 200；頁面有一個以 POST 送到 `/upload`、`multipart/form-data` 的表單，含：運算環境下拉、資料集名稱、版本、FASTQ 檔欄位（`<input type=file multiple>`）、樣本表檔欄位（選填）、一個隱藏的 CSRF 欄位、一個送出鈕 | 自動 |
| TC-002 | 作法 1 | 功能 | alice 有 `gcb1`（Google Batch、available）與 `aws1`（AWS、available） | `GET /upload` | 運算環境下拉恰好列出 `gcb1` 與 `aws1`，不多不少 | 自動 |
| TC-003 | 作法 1 | 例外 | alice 另有 `gcb-off`（雲端環境，但 status 不是 available） | `GET /upload` | 下拉不含 `gcb-off`；仍含 `gcb1` | 自動 |
| TC-004 | 作法 1；不做（國網） | 例外 | alice 另有 `nchc1`（國網／Slurm 類，available） | `GET /upload` | 下拉不含 `nchc1`；仍含 `gcb1` | 自動 |
| TC-005 | 作法 1（屬於自己的環境）；跨使用者讀 | 例外 | bob 有 `gcb2` | alice 開 `GET /upload` | 下拉不含 `gcb2`，整個頁面任何地方都沒有 `gcb2` 這個字 | 自動 |
| TC-006 | 作法 1（空狀態）；DESIGN 空狀態 | 例外 | alice 沒有任何 available 的雲端環境（可有也可沒有國網環境） | `GET /upload` | 200；頁面用一句話說明沒有可用的雲端運算環境，並有連到 `/settings` 的連結；頁面沒有 `<form>`、沒有檔案欄位、沒有送出鈕 | 自動 |
| TC-007 | 裁決 20；作法 1 | 功能 | alice 有 `gcb1` 與 `nchc1` | `GET /upload`（中文） | 頁面含「國網環境的資料目前請用指令上傳」；加 `?lang=en` 時含意思相同的英文句，且該句不含中文字 | 自動 |
| TC-008 | 裁決 20 | 功能 | alice 只有雲端環境，沒有國網類環境 | `GET /upload` | 頁面不含「國網環境的資料目前請用指令上傳」 | 自動 |
| TC-009 | 作法 1；原話 2（DESIGN.md「≤ ~2 GB per file」） | 功能 | alice 有 `gcb1` | `GET /upload`（中文與 `?lang=en`） | 頁面寫明每檔上限 2 GB（中文含「2 GB」，英文含 "2 GB"），並說明更大的檔請改用指令；上限數字與程式實際上限（2,000,000,000 位元組）一致 | 自動 |
| TC-010 | 裁決 21；原話 2（大檔走另一條路） | 功能 | alice 有 `gcb1`（Google Batch）與 `aws1`（AWS） | `GET /upload` | 表單下方對每個列出的環境各一行大檔指令：`gcb1` 那行以 `gcloud storage cp` 開頭、含 `gcb1` 的 `uploads/alice/` 上傳前綴；`aws1` 那行以 `aws s3 cp` 開頭、含 `s3://` 前綴；內容與 `cloud_store.big_file_command` 對同環境同使用者給的一致，檔案位置以 `<檔名>` 佔位；不含別的使用者或別的環境的前綴 | 自動 |
| TC-011 | 專長守則 ui（必填標記）；DESIGN.md 用字(4) | 功能 | alice 有 `gcb1` | `GET /upload` | 必填欄位（運算環境、資料集名稱、版本、FASTQ 檔）各有 `<span class="req" title="必填">*</span>`（英文版 title 為 "Required"）；表單上方有圖例「* 必填」；樣本表欄位（選填）沒有此標記；「必填」二字不重複當作欄位標籤 | 自動 |
| TC-012 | DESIGN.md 約束「every screen exists in English」 | 功能 | alice 有 `gcb1` | `GET /upload?lang=en` | 頁面本文（扣掉引用自 `cloud_store` 的指令原文）不含中文字；欄位標籤與說明都是英文 | 自動 |
| TC-013 | DESIGN.md「Buttons are fixed verbs only (上傳 …)」 | 功能 | alice 有 `gcb1` | `GET /upload`（中文與英文） | 送出鈕文字恰為「上傳」（英文 "Upload"）；頁面上任何按鈕的文字都不含數字、檔案大小或檔名 | 自動 |
| TC-014 | 作法 2 前段；裁決 19（GET 對應） | 例外 | 沒登入 | 不帶登入 cookie 開 `GET /upload` | 與不帶 cookie 開 `GET /launch` 同樣被轉到登入頁（同狀態碼、同轉址格式），不顯示表單 | 自動 |
| TC-015 | 失敗先行測試（臨時密碼）；作法 2 | 例外 | alice 用臨時密碼登入（尚未改密碼） | 對 `/upload` 做 `GET`，再做 `POST` | 兩者都 303 到 `/welcome`；沒有寫任何檔、沒有排任何工作 | 自動 |
| TC-016 | 作法 6；原話 4；專長守則 ui 前端限制 | 功能 | alice 有 `gcb1` | 取 `GET /upload` 與 `GET /upload/<batch>`（各種狀態）的 HTML 與標頭 | 沒有 `style=` 屬性、沒有 `<script>`、沒有外部網址資源（`src`／`href` 只指向本站）；`Content-Security-Policy` 標頭與 `GET /launch` 的完全相同；只連結既有的單一樣式表；沒有拖放區 | 自動 |
| TC-017 | DESIGN.md 用字（禁用字）；裁決 16 | 功能 | 上傳頁、各種拒收頁（400／403／404／413）、進度頁各狀態 | 取中文版 HTML 的主欄，只看本任務自己寫的句子 | 不含這些字串：用過、選好、寫死、自己填、自己調整、你還沒、還沒有、還不能、這個、這份、這條、這一版、一下、弄、搞、東西、喔、啦、吧、囉、蠻、超（引用 `jobs.py`／站台／`check_web_upload` 回傳的原文不檢查） | 自動 |
| TC-018 | 專長守則 ui／backend（白話、不露內部資訊） | 功能 | 上傳頁、各種拒收頁、進度頁各狀態 | 取 HTML | 不含 `put_upload`、`enqueue`、`.incoming-`、`.batches`、`Traceback`、上傳資料夾的伺服器絕對路徑、SQL 字樣 | 自動 |
| TC-019 | 作法 1（型別判斷「沿用 jobs.py，不重寫」） | 功能 | 原始碼 | 檢查 `web_upload.py`、`uploads_web.py`、`actions/uploads.py` | 這三個新檔沒有自己寫一份雲端型別清單（不含 `GOOGLE_BATCH`、`AWS` 型別字串常數）；哪些環境可上傳由 `jobs.py` 提供的判斷決定 | 自動 |

## User Story 2 — 送出上傳 `POST /upload`：收檔、暫存、排工作（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 作法 2；失敗先行測試；原話 1 | 功能 | alice 有 `gcb1`；名稱 `ds1`、版本 `v1` 尚未登記 | 在表單選 `gcb1`、填 `ds1`／`v1`、選成對檔、不給樣本表，按「上傳」 | 一次送出就完成：回 303 到 `/upload/<batch>`；使用者不需要再按任何確認或執行任何指令 | 自動 |
| TC-021 | 作法 2；ADR 0010 更正（暫存） | 功能 | 同 TC-020 | 送出後檢查上傳夾 | `<uploads>/alice/sampleA_R1.fastq.gz` 與 `…_R2.fastq.gz` 存在，內容與送出的位元組完全相同；`<uploads>/alice/.incoming-<batch>/` 已不存在；平台沒有刪掉這兩個暫存檔（刪除由站台在核對尺寸後做） | 自動 |
| TC-022 | 作法 2（邊收邊寫到 `.incoming-<batch>`） | 功能 | 同 TC-020，用分段送出的串流 | 在收到一半時檢查上傳夾 | 已收的位元組在 `<uploads>/alice/.incoming-<batch>/` 之下，尚未出現在 `<uploads>/alice/<檔名>`；收完才移到最後位置 | 自動 |
| TC-023 | 作法 2；環境事實（`enqueue_put_upload`） | 功能 | 同 TC-020 | 送出後讀工作表 | 恰好兩個 `put_upload` 工作；擁有者為 alice、環境為 `gcb1`；檔名分別是兩個檔；目的地各為 `gs://<gcb1 的 bucket>/uploads/alice/<檔名>`（與 `enqueue_put_upload` 自己算出的相同） | 自動 |
| TC-024 | 裁決 1；原話 3（ADR「按上傳就是確認」） | 功能 | 同 TC-020 | 送出後檢查回應與確認紀錄 | 第一個回應就是 303 到進度頁，沒有經過確認頁（沒有轉到 `/c/<id>`）；待確認請求的紀錄沒有新增任何一筆 | 自動 |
| TC-025 | 作法 3；裁決 3；裁決 18 | 功能 | 同 TC-020 | 讀 `<uploads>/alice/.batches/<batch>.json` | 是 JSON，含 `batch`、`owner`（alice）、`ce`（`gcb1`）、`name`（`ds1`）、`version`（`v1`）、`files`（每檔有 `name`、`job_id`、`dest`）、`samplesheet`，以及 `registered` 旗標（此時為假）；不含密碼、token、cookie、雲端金鑰 | 自動 |
| TC-026 | 作法 3；裁決 13（不需 migration） | 功能 | 同 TC-020 | 檢查批次紀錄檔與資料庫 | 批次紀錄檔權限為 0600；`.batches/` 內沒有殘留的暫存檔（寫入是暫存檔加 rename）；平台資料庫沒有新增資料表或欄位，`_migrate` 清單未變 | 自動 |
| TC-027 | 作法 2（沒給樣本表就自動配對） | 功能 | 同 TC-020，沒給樣本表 | 送出後讀批次紀錄的 `samplesheet` | 是由 `draft_samplesheet`／`pair_fastq` 產生的樣本表：表頭含 `sample`、`fastq_1`、`fastq_2`，有一列 `sampleA`，兩個檔名依序是 R1、R2 | 自動 |
| TC-028 | 作法 2 | 功能 | 同 TC-020，另給一份合格樣本表（欄位 `sample,fastq_1,fastq_2`，儲存格是本批的檔名） | 送出 | 批次紀錄的 `samplesheet` 就是使用者給的內容，沒有被自動草稿取代 | 自動 |
| TC-029 | 裁決 4（必要欄位只有 `sample`、`fastq_1`） | 功能 | alice 只選一個檔 `solo.fastq.gz`，並給樣本表 `sample,fastq_1` 一列指向 `solo.fastq.gz` | 送出 | 303 到進度頁；排了一個工作；沒有因為「配不成對」被拒（單端資料集能用） | 自動 |
| TC-030 | 作法 2；環境事實（AWS） | 功能 | alice 另有 `aws1`（AWS、available） | 選 `aws1`、用成對檔送出 | 303；兩個工作的目的地各為 `s3://<aws1 的 bucket>/uploads/alice/<檔名>` | 自動 |
| TC-031 | 作法 2、範圍（上傳路由用自己的上限） | 功能 | 送出的整個請求大於 16384 位元組（例如一個 1 MiB 的 FASTQ） | 送出 | 不被截斷、不回 413 或 400；303 到進度頁；暫存檔大小等於送出的大小 | 自動 |
| TC-032 | 範圍（`MAX_BODY` 不准改） | 功能 | 原始碼與既有路由 | 讀 `web.MAX_BODY`；對既有的表單路由（例如登入）送超過 16384 位元組的內文 | `MAX_BODY` 仍是 16384；既有路由仍在 16384 位元組截斷，行為與修改前相同 | 自動 |
| TC-033 | 作法 2（「超過」才拒；大小 1 位元組～上限） | 功能 | 上限調成 N 位元組；alice 送恰好 N 位元組的檔 | 送出 | 接受（303），不是 413 | 自動 |
| TC-034 | 作法 2；原話 2（約 2 GB 上限）；失敗先行測試 | 例外 | 上限調成 N；alice 送 N+1 位元組的檔，另一個檔正常 | 送出 | 回 413 頁；頁面指出是哪個檔太大；上傳夾裡沒有留下任何新檔、`.incoming-*` 已刪；沒有排任何工作；沒有建立批次紀錄 | 自動 |
| TC-035 | 作法 2（「立刻中止」） | 例外 | 上限調成 N；用假串流送一個宣告很大、實際有 N×100 位元組的檔，記錄伺服器讀了多少 | 送出 | 回 413；伺服器沒有把整串內容讀完（讀取量遠小於 N×100，約在 N 加上一兩個讀取區塊之內）；暫存已清空 | 自動 |
| TC-036 | 裁決 8（超大小也清掉整批暫存） | 例外 | 一批兩個檔，第一個正常、第二個超過上限 | 送出 | 413；第一個檔的暫存也被清掉；上傳夾恢復成送出前的樣子；沒有工作 | 自動 |
| TC-037 | 作法 2（413 頁帶指令）；原話 2 | 例外 | 同 TC-034，選 `gcb1` | 看 413 頁 | 頁面有「每檔上限 2 GB」的說明與一行該環境的大檔指令（取自 `check_web_upload` 的回答），指令不含別人的前綴 | 自動 |
| TC-038 | 裁決 5（前置檢查：1 位元組～2 GB） | 例外 | alice 送一個 0 位元組的 FASTQ | 送出 | 被拒（400）；頁面指出是哪個檔、為什麼；暫存清空；沒有工作 | 自動 |
| TC-039 | 作法 2；失敗先行測試 | 例外 | 檔名為 `../evil_R1.fastq.gz` | 送出 | 400；整個上傳區（含上層資料夾）沒有出現 `evil_R1.fastq.gz`，也沒有被截斷成 `evil_R1.fastq.gz` 收下；沒有工作；暫存清空 | 自動 |
| TC-040 | 作法 2；裁決 6 | 例外 | 檔名為 `a/b_R1.fastq.gz` | 送出 | 400，不做 basename 截斷（沒有收下 `b_R1.fastq.gz`）；沒有工作；暫存清空 | 自動 |
| TC-041 | 作法 2；裁決 6 | 例外 | 檔名為 `a\b_R1.fastq.gz` | 送出 | 400，沒有收下 `b_R1.fastq.gz`；沒有工作；暫存清空 | 自動 |
| TC-042 | 作法 2（檔名含 `..`） | 例外 | 檔名為 `a..b_R1.fastq.gz` | 送出 | 400；沒有工作；暫存清空 | 自動 |
| TC-043 | 作法 2（控制字元） | 例外 | 檔名含控制字元（例如 `bad\x01name_R1.fastq.gz`） | 送出 | 400；沒有工作；暫存清空 | 自動 |
| TC-044 | 裁決 6（同批重名） | 例外 | 同一批裡有兩個同名檔 | 送出 | 400，指出重名的檔；沒有工作；暫存清空 | 自動 |
| TC-045 | 裁決 6；裁決 18 | 例外 | 上傳夾已有 `sampleA_R1.fastq.gz`（不屬於任何批次），alice 再送同名檔 | 送出 | 400，訊息為「此檔名正在上傳或已使用，請改檔名。」（英文 "This file name is in use by another upload; rename the file."）；原檔內容沒被動；沒有工作；暫存清空 | 自動 |
| TC-046 | 裁決 18（重新上傳） | 功能 | 上傳夾有 `sampleA_R1.fastq.gz`，屬於 alice 一個已失敗的批次 | alice 再送同名檔（新資料集版本） | 接受（303）；舊暫存檔被新的取代；舊批次紀錄帶 `superseded` 標記（值為真）；新批次排了工作 | 自動 |
| TC-047 | 裁決 18 | 例外 | 同名檔屬於 alice 一個進行中（排隊中或傳送中）的批次 | 送出同名檔 | 400，用 TC-045 的同一句；舊檔與舊批次沒被動 | 自動 |
| TC-048 | 裁決 18 | 例外 | 同名檔屬於 alice 一個已登記的批次（檔案仍在上傳夾） | 送出同名檔 | 400，用 TC-045 的同一句；舊檔沒被動 | 自動 |
| TC-049 | 作法 2（檔案寫在各人自己的資料夾） | 功能 | alice 的上傳夾已有 `sampleA_R1.fastq.gz` | bob 送出同名檔到他自己的環境 `gcb2` | 接受（303）；檔寫在 `<uploads>/bob/`，alice 的檔不變 | 自動 |
| TC-050 | 裁決 3 | 例外 | alice 已有資料集 `ds1`／`v1` | alice 再用 `ds1`／`v1` 送出 | 400，訊息為「此名稱與版本已登記，請換一個版本。」；沒寫任何檔；沒有工作；沒有批次紀錄 | 自動 |
| TC-051 | 裁決 3 | 例外 | 同 TC-050，`?lang=en` | 送出 | 400，訊息為 "This name and version are already registered. Use another version."；其餘同 TC-050 | 自動 |
| TC-052 | 裁決 3（以擁有者區分） | 功能 | bob 已有資料集 `ds1`／`v1`，alice 沒有 | alice 用 `ds1`／`v1` 送出 | 接受（303） | 自動 |
| TC-053 | 裁決 15 | 例外 | 沒選任何 FASTQ | 送出 | 400，訊息為「請選擇至少一個 FASTQ 檔。」（英文 "Choose at least one FASTQ file."）；沒寫檔、沒排工作 | 自動 |
| TC-054 | 裁決 15 | 例外 | 資料集名稱留白 | 送出 | 400；名稱欄旁標「此欄為必填。」（英文 "This field is required."）；沒寫檔、沒排工作 | 自動 |
| TC-055 | 裁決 15 | 例外 | 版本留白 | 送出 | 400；版本欄旁標「此欄為必填。」（英文 "This field is required."）；沒寫檔、沒排工作 | 自動 |
| TC-056 | 作法 1（名稱與版本規則 `^[A-Za-z0-9._-]{1,64}$`） | 例外 | 名稱 `bad name!`，另一次版本是 65 個字元 | 各送出一次 | 兩次都 400，指出是哪一欄、規則是什麼；沒寫檔、沒排工作 | 自動 |
| TC-057 | 作法 2（`SAMPLESHEET_LIMIT`）；裁決 8 | 例外 | 樣本表大於 1 MiB | 送出 | 400，說明樣本表太大、上限 1 MiB；暫存清空；沒有工作 | 自動 |
| TC-058 | 作法 2；失敗先行測試（配不成對） | 例外 | 只選 `sampleA_R1.fastq.gz`、`sampleB_R1.fastq.gz`，沒給樣本表 | 送出 | 400，頁面列出配不到的檔名（兩個都要列）；暫存清空；沒有工作 | 自動 |
| TC-059 | 裁決 4（欄位檢查） | 例外 | 樣本表缺 `fastq_1` 欄 | 送出 | 400，說明缺哪一欄；暫存清空；沒有工作 | 自動 |
| TC-060 | 裁決 4（路徑儲存格要對得上本批檔名） | 例外 | 樣本表的 `fastq_1` 儲存格填 `other.fastq.gz`，本批沒有這個檔 | 送出 | 400，指出是哪個儲存格不在本批；暫存清空；沒有工作 | 自動 |
| TC-061 | 裁決 4（不含網址） | 例外 | 樣本表儲存格是 `https://example.org/x.fastq.gz` | 送出 | 400，說明樣本表含網址；暫存清空；沒有工作 | 自動 |
| TC-062 | 裁決 4（不含像憑證的值） | 例外 | 樣本表某儲存格是像憑證的值（例如 `AKIAIOSFODNN7EXAMPLE` 或 `ghp_` 開頭長字串） | 送出 | 400，說明樣本表含像憑證的值；頁面與紀錄不回顯該值；暫存清空；沒有工作 | 自動 |
| TC-063 | 裁決 5（排到一半被拒） | 例外 | 兩個檔；排第二個工作時 `enqueue_put_upload` 拒絕（測試用替身模擬） | 送出，跟著轉址看進度頁 | 第一個工作照排、仍傳送；批次標為失敗；第二個檔的暫存被刪；進度頁指出被拒的是哪個檔與原因；沒有登記資料集 | 自動 |
| TC-064 | 作法 2；跨使用者寫；裁決 5（先驗環境） | 例外 | POST 的環境名稱是 `gcb2`（bob 的）、一個不存在的名字、或已離線的 `gcb-off` | 各送一次 | 都被拒（4xx，不是 5xx）；沒寫任何檔、沒排工作；`gcb2` 與不存在的名字得到的回應內容相同（不洩漏別人的環境存不存在） | 自動 |
| TC-065 | 作法 2（CSRF）；失敗先行測試 | 例外 | 表單沒帶 CSRF 欄位，或值是錯的 | 送出 | 403；沒寫檔；沒排工作；沒建批次紀錄 | 自動 |
| TC-066 | 作法 2（CSRF purpose `upload`） | 例外 | 用別的用途（例如 `welcome`、`logout`）發出的 CSRF 值送出 | 送出 | 403；沒寫檔、沒排工作 | 自動 |
| TC-067 | 作法 2（`same_origin`）；失敗先行測試 | 例外 | 請求帶別的網站的 `Origin`／`Referer` | 送出（CSRF 值正確） | 403；沒寫檔、沒排工作 | 自動 |
| TC-068 | 裁決 19 | 例外 | 沒登入 | 不帶 cookie `POST /upload` | 反應與不帶 cookie 的 `POST /launch` 相同（同狀態碼、同轉址）；沒寫檔、沒排工作 | 自動 |
| TC-069 | ADR 0010（個人存取權杖沒有上傳） | 例外 | 只有 `Authorization: Bearer <個人存取權杖>`，沒有網頁登入 cookie | `POST /upload` | 被當成沒登入處理（同 TC-068），沒寫檔、沒排工作 | 自動 |
| TC-070 | 專長守則 backend（錯誤訊息不露堆疊） | 例外 | 寫入暫存檔時磁碟丟出錯誤（測試用替身） | 送出 | 回出錯頁，說明發生什麼事與下一步；內容不含堆疊、內部路徑或 SQL；沒有排任何工作；上傳夾的最後位置（`<uploads>/alice/<檔名>`）沒有留下半個檔 | 自動 |

## User Story 3 — 進度頁 `GET /upload/{batch}` 與自動登記（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-071 | 作法 4 | 功能 | alice 剛送出成對檔（批次 B，兩個工作都排隊中） | `GET /upload/B` | 每檔一列：檔名、大小、狀態；兩列 | 自動 |
| TC-072 | 裁決 7；裁決 14；專長守則（符號＋文字） | 功能 | 工作狀態 queued | 看該檔那一列 | HTML 含「○ 排隊中」（符號與文字都在，不只靠 class 顏色） | 自動 |
| TC-073 | 裁決 7；裁決 14 | 功能 | 工作狀態 claimed | 看該列 | HTML 含「◐ 傳送中」 | 自動 |
| TC-074 | 裁決 7；裁決 14 | 功能 | 工作 done 且 `ok` 為真 | 看該列 | HTML 含「✓ 完成」 | 自動 |
| TC-075 | 裁決 7；裁決 14；失敗狀態 | 例外 | 工作 done 且 `ok` 為假，message 為「cloud size differs」 | 看該列 | HTML 含「✕ 失敗」，且附工作回的 message 原文 | 自動 |
| TC-076 | 裁決 7 | 例外 | 工作狀態 expired | 看該列 | HTML 含「✕ 失敗」，並附原因（逾時／過期的說明） | 自動 |
| TC-077 | 裁決 14（英文） | 功能 | 四種狀態各一個檔，`?lang=en` | 看各列 | 依序含 "○ Queued"、"◐ Sending"、"✓ Done"、"✕ Failed" | 自動 |
| TC-078 | 作法 4（15 秒重新整理） | 功能 | 批次還有檔在排隊中或傳送中 | 取 HTML | 含 `<meta http-equiv="refresh" content="15">`（與既有頁同一寫法）；頁面沒有 `<script>` | 自動 |
| TC-079 | 作法 4；失敗先行測試；原話 1 | 功能 | 兩個工作都 done 且 ok（測試直接改工作結果）；名稱 `ds1`、版本 `v1` | alice `GET /upload/B` | 資料集 `ds1`／`v1` 被登記；`list_datasets` 看得到它；不需要使用者再做任何別的操作 | 自動 |
| TC-080 | 作法 4（檔案路徑與樣本表換成雲端位置） | 功能 | 同 TC-079；工作結果的 `path` 為 `gs://<bucket>/uploads/alice/<檔名>` | 讀已登記資料集 | 資料集的檔案清單就是這兩個 `gs://` 位置；樣本表的 `fastq_1`、`fastq_2` 儲存格換成同一組位置，不再有純檔名；批次紀錄的 `registered` 為真 | 自動 |
| TC-081 | 作法 4（AWS） | 功能 | 批次用 `aws1`，工作結果的 `path` 為 `s3://…` | 同 TC-079 | 資料集的檔案與樣本表儲存格都是 `s3://` 位置 | 自動 |
| TC-082 | 作法 4（已登記，前往送出） | 功能 | 登記成功之後 | 看進度頁（中文與 `?lang=en`） | 中文顯示「已登記，前往送出」，並有連到 `/launch` 的連結；英文版有含 "Registered" 的英文句與同一個連結 | 自動 |
| TC-083 | 作法 4、作法 5；原話 1（不問人就能用完） | 功能 | 同 TC-079，alice 已登記 | alice 開 `/launch` 第 4 步（樣本表） | 第 4 步列出 `ds1`／`v1` 可選；全程使用者沒有執行過任何指令 | 自動 |
| TC-084 | 作法 4（重整不重複登記）；失敗先行測試；裁決 10 | 功能 | 同 TC-079 | 連續 `GET /upload/B` 三次 | 資料庫裡 `ds1`／`v1` 只有一筆；第二、三次都直接顯示已登記，沒有出現錯誤頁或「已存在」訊息 | 自動 |
| TC-085 | 作法 4（全部完成才登記） | 例外 | 兩個工作，一個 done ok、另一個還在傳送中 | `GET /upload/B` | 沒有登記資料集；頁面還是進度狀態 | 自動 |
| TC-086 | 作法 4；失敗先行測試（有一個失敗不登記） | 例外 | 兩個工作，一個 done ok、一個 done 非 ok | `GET /upload/B` | 沒有登記資料集（`list_datasets` 沒有 `ds1`）；顯示失敗原因；有「重新上傳」連結，連到 `/upload` | 自動 |
| TC-087 | 裁決 18；作法 4 | 功能 | 接續 TC-086：alice 按「重新上傳」，用同檔名、新版本 `v2` 送出 | 送出 | 成功（303）；舊批次標 `superseded`；新批次走完後登記 `ds1`／`v2` | 自動 |
| TC-088 | 裁決 4（登記仍失敗） | 例外 | 兩個工作都 ok，但在登記前有人用 CLI 先登記了同名同版本 `ds1`／`v1`，使 `register_dataset` 回 `ok:false` | alice `GET /upload/B` | 頁面顯示 `register_dataset` 回的原因；列出已在雲端的兩個 `gs://…` 位置；有句子「檔案仍在你的雲端資料夾，可換一個版本重新上傳」（英文版有相同意思的英文句）；不顯示「已登記」 | 自動 |
| TC-089 | 裁決 3（只依本批旗標判斷已登記） | 例外 | 同 TC-088 | 看進度頁 | 不因為「同名同版本的資料集存在」就顯示「已登記，前往送出」；批次紀錄的 `registered` 仍為假 | 自動 |
| TC-090 | 裁決 4（不自動刪雲端檔） | 例外 | 同 TC-088 | 看工作表 | 沒有任何刪除或清理雲端檔案的工作被排入；批次紀錄的 `dest` 位置仍保留 | 自動 |
| TC-091 | 作法 3（他人 batch＝404）；跨使用者讀 | 例外 | alice 有批次 B | bob `GET /upload/B` | 404；頁面不含 alice 的檔名、名稱、版本 | 自動 |
| TC-092 | 作法 3；專長守則 backend（不露內部路徑） | 例外 | 不存在的批次 `nope`；以及類似路徑的批次 `..%2F..%2Fetc` | alice 各開一次 | 兩者都 404，回應內容與 TC-091 相同；沒有讀到 `.batches` 以外的檔；不露出伺服器路徑 | 自動 |
| TC-093 | 作法 3、裁決 10；跨使用者寫 | 例外 | alice 的批次 B 兩個工作都已 ok、尚未被 alice 開過 | bob `GET /upload/B`，之後檢查資料集 | bob 得到 404；沒有登記任何資料集（登記只會發生在 alice 自己開頁時） | 自動 |
| TC-094 | 裁決 19（GET 對應）；作法 4 | 例外 | 沒登入 | 不帶 cookie `GET /upload/B` | 與不帶 cookie `GET /launch` 同樣被轉到登入頁；臨時密碼登入者則 303 到 `/welcome` | 自動 |
| TC-095 | ADR 0010 更正（尺寸核對後刪暫存是站台的事） | 功能 | 兩個工作都 ok | 開進度頁數次 | 平台沒有刪除或改動上傳夾裡的暫存檔 | 自動 |
| TC-096 | 裁決 5（進度頁標出被拒的檔） | 例外 | 同 TC-063 的批次 | 開進度頁 | 被拒的那個檔那一列標「✕ 失敗」並附被拒原因；已排的那個檔照常顯示狀態；沒有登記 | 自動 |

## User Story 4 — 入口串接：總看板按鈕與送出頁第 4 步（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-097 | 作法 5；裁決 13 | 功能 | alice 已登入 | 開總看板 `GET /` | 「↑ 上傳資料」是連到 `/upload` 的連結（`<a href="/upload">`），不是灰色停用元件 | 自動：`platform/tests/test_web_board.py`（`test_tcs21_s22_left_grey_and_settings` 改後版）與新檔 |
| TC-098 | 作法 5；裁決 13（中英皆然） | 功能 | 同上，`?lang=en` | 開總看板 | 英文版的上傳項也是連到 `/upload` 的連結 | 自動 |
| TC-099 | 裁決 13（其餘斷言不動） | 功能 | 同上 | 開總看板 | 設定連結仍在；資料瀏覽與其他「之後開放」項目仍是灰色；左欄其他內容與修改前相同 | 自動 |
| TC-100 | 作法 5；DESIGN.md 第 5 畫面第 4 步 | 功能 | alice 沒有任何已上傳的樣本表／資料集 | 開 `/launch` 第 4 步 | 仍顯示 "No samplesheet has been uploaded. Please upload one first."（中文版同義句不變）；其中的連結指向 `/upload` | 自動 |

## User Story 5 — 文件、分層、被釘死的既有測試、範圍（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-101 | 裁決 9；原話 2、3 | 功能 | 修改後的 `DESIGN.md` | 讀「Upload data」那一段，並比對修改前 | 該段末多一行「10-28 第一刀：表單上傳＋進度頁；拖放、依 schema 建表、已上傳資料表格留待後續」；「platform keeps no copy」不再出現，改為說明暫存於平台主機、雲端尺寸核對後刪除；整份 `DESIGN.md` 其他地方一字未動 | 自動 |
| TC-102 | 裁決 13；範圍（OPERATIONS） | 功能 | `docs/OPERATIONS.md` | 讀第 6 點 | 含 "The web page /upload sends files up to 2 GB into the bucket"，不再含 "Not built yet"；`test_cloud_upload_docs.py:42` 改為斷言這兩件事且綠 | 自動：`platform/tests/test_cloud_upload_docs.py` |
| TC-103 | 裁決 13；範圍（PLATFORM） | 功能 | `docs/PLATFORM.md` | 讀 :382 附近 | 含「網頁上傳頁（/upload）會把檔案暫存於平台主機後排入此工作」，不再含「網頁入口尚未接上」；`test_aws_upload.py:751` 改為斷言這兩件事且綠 | 自動：`platform/tests/test_aws_upload.py` |
| TC-104 | 裁決 12；範圍（TESTING） | 功能 | `docs/TESTING.md` | 找本任務的新手動一節 | 該節有可照做的步驟：①≥100 MB 真檔經 Tailscale Funnel 上傳一次直到登記；②390 px 寬無橫向捲動；③鍵盤 Tab 焦點外框可見；④中文與英文各看一次；⑤閱卷步驟：`pyproject.toml`、釘死測試只加項、ledger、`STYLE` 未改、`jobs.py`／`abf_station` 範圍（對應 TC-105、TC-117、TC-118、TC-119、TC-122、TC-123） | 手動：`docs/TESTING.md` 新節 |
| TC-105 | 範圍（pyproject） | 功能 | `platform/pyproject.toml` 與 `platform/constraints.txt` | 比對與修改前的差異 | 只多一個直接依賴 `python-multipart`；沒有其他套件；`constraints.txt` 沒動（仍釘 0.0.32） | 手動：`docs/TESTING.md` 新節 |
| TC-106 | 裁決 13（分層字樣） | 功能 | 原始碼 | 檢查 `web.py`、`web_board.py`、`web_upload.py`、`uploads_web.py`、`actions/__init__.py` | 這五個檔沒有新增 `register_dataset`、`draft_samplesheet`、`check_web_upload`、`pair_fastq`、`actions.datasets`、`get_dataset` 字樣；`test_datasets.py:470` 附近的 `test_tc064` 一字未改且綠 | 自動：`platform/tests/test_datasets.py`（`test_tc064`）＋ `test_web_upload.py` |
| TC-107 | 裁決 13；專長守則 backend（路由不得有第二份邏輯） | 功能 | 原始碼 | 檢查 `/upload` 三條路由的處理函式 | 網頁只呼叫 `actions/__init__.py` 的 `start_upload_batch`、`upload_batch_status`（及需要時的 `register_upload_batch`）；這幾個函式只轉呼叫 `actions/uploads.py`；只有 `actions/uploads.py` 呼叫 datasets 與 `jobs.enqueue_put_upload` | 自動 |
| TC-108 | 專長守則 backend（對等性） | 功能 | 原始碼 | 跑 `test_web_parity.py` | 同一個測試同時列舉「使用者可見的上傳動作」與「動作層函式」，兩邊一一對應；上傳動作已加進清單（只加不刪）；任一邊缺項就失敗 | 自動：`platform/tests/test_web_parity.py` |
| TC-109 | 裁決 13（`test_aws_upload.py:727`） | 功能 | 修改後測試 | 跑該測試 | 期望清單恰為 `["actions/uploads.py", "jobs.py"]`（只有這兩個檔呼叫 `enqueue_put_upload`），其餘斷言不動且綠 | 自動：`platform/tests/test_aws_upload.py` |
| TC-110 | 裁決 13（datasets.py 函式清單） | 功能 | 修改後測試 | 跑 `test_aws_upload.py:665` 與 `test_datasets.py:441` | 清單加上 `check_samplesheet`，共七個函式，其餘不動且綠 | 自動 |
| TC-111 | 裁決 13（不需 migration） | 功能 | `test_aws_upload.py:660` | 跑該測試 | 該測試一字未改且綠（資料表雜湊與 `_migrate` 清單不變） | 自動 |
| TC-112 | 裁決 13（`test_web_board.py:316`） | 功能 | 修改後測試 | 跑 `test_tcs21_s22_left_grey_and_settings` | 「↑ 上傳資料」改為斷言連到 `/upload`（中英皆然），其餘斷言不動且綠 | 自動 |
| TC-113 | 裁決 17 | 功能 | 修改後測試 | 跑 `test_confirm_page.py:315`、`test_web_board.py:1184`（`test_tn04_other_paths_stay_missing`）、`test_web_actions.py:505-506`（`test_tc051_tc056_nothing_out_of_scope_exists`） | 前兩者把 `/upload` 從「必須 404」拿掉，改斷言它存在（未登入時與 `/launch` 同樣轉到登入）；第三者的正規表達式移除 `upload|`，並另加一行斷言含 upload 的路由恰為 `/upload` 與 `/upload/{batch}`（共兩條，不多）；各測試其餘清單與字詞不動且綠 | 自動 |
| TC-114 | 範圍（被逐字釘住、只加不刪） | 功能 | 修改後測試 | 比對 `test_dataset_cli.py:183`、`test_cleanup_offer.py:815`、`test_confirm_page.py:313`、`test_web_board.py:820`、`test_owner_binding.py:824`、`test_temp_password.py:290`、`test_web_parity.py:16` 與修改前 | 每一處只多了項目，沒有刪除或改弱任何斷言；各測試綠 | 自動 |
| TC-115 | 完成標準（釘死測試只加項）；放水檢查 | 功能 | 本任務全部對既有測試檔的修改 | 比對與 base 的差異 | 除計畫與 ledger 點名的測試外，沒有任何既有測試被刪、被跳過、被放寬或改期望值；計畫、`test-case*.md` 在實作期間沒被改 | 自動：`tests/run_all.sh`；閱卷時以 diff 核對 |
| TC-116 | 完成標準（ledger）；作法 3 | 功能 | `specs/web-upload-page/ledger.md` | 讀 ledger | 寫明批次紀錄存哪（`<uploads>/<user>/.batches/<batch>.json`，不進資料庫）；逐條列出改了哪些釘死斷言（檔、行、舊值、新值、原因），涵蓋 TC-102、103、109、110、112、113、114 | 手動：`docs/TESTING.md` 新節 |
| TC-117 | 範圍（ledger 逐條）；放水檢查 | 功能 | ledger 與 `git diff <base>...HEAD -- platform/tests` | 逐條對照 | diff 裡每個既有測試的改動都在 ledger 有一條；ledger 沒列的改動為零 | 手動：`docs/TESTING.md` 新節 |
| TC-118 | 範圍（`web_board.py` 只限三件事） | 功能 | `git diff <base>...HEAD -- platform/abf_platform/web_board.py` | 讀差異 | 只有：灰色上傳鈕變連結、第 4 步連結改指 `/upload`、新增 STRINGS；沒有修改既有的其他行（合併 L8 時的聯集除外） | 手動：`docs/TESTING.md` 新節 |
| TC-119 | 原話 4；專長守則 ui（不新增視覺決策） | 功能 | `web_board.STYLE`（單一樣式表） | 比對與修改前 | `STYLE` 一字未改；上傳頁與進度頁只用既有 class，沒有新顏色、字型、間距 | 手動：`docs/TESTING.md` 新節 |
| TC-120 | 範圍（`check_samplesheet` 不寫入） | 功能 | `actions/datasets.py` | 呼叫 `check_samplesheet`（合格與不合格的樣本表各一次），同時讓資料庫連線函式一用就丟錯 | 兩次都正常回答（合格／不合格與原因）；資料集資料表筆數不變；沒有碰資料庫 | 自動 |
| TC-121 | 範圍；不做（不改 `register_dataset` 行為） | 功能 | 既有 `register_dataset` 測試（`test_datasets.py`、`test_dataset_cli.py`、`test_dataset_launch.py`） | 跑 | 除函式清單那一處外一字未改且全綠；`register_dataset` 對舊輸入回的 `ok`、訊息與修改前相同 | 自動 |
| TC-122 | 範圍（`jobs.py` 只加讀取）；不做 | 功能 | `git diff <base>...HEAD -- platform/abf_platform/jobs.py platform/abf_station` | 讀差異 | `jobs.py` 只新增讀取「某批上傳工作狀態」的小函式，`enqueue_put_upload` 與其他既有函式一字未動；`abf_station/` 下沒有任何差異 | 手動：`docs/TESTING.md` 新節 |
| TC-123 | 範圍（`web.py` 只新增） | 功能 | `git diff <base>...HEAD -- platform/abf_platform/web.py` | 讀差異 | 只有新增三條路由與註冊行；既有行不變（合併 L8 時的聯集除外）；`MAX_BODY` 仍是 16384；上傳路由不走 `body_of` | 手動：`docs/TESTING.md` 新節 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-124 | 裁決 9；不做（拖放）；原話 4 | 不在範圍 | alice 有 `gcb1` | 看 `GET /upload` 的 HTML | 沒有拖放區、沒有 JavaScript；只有一般檔案選擇欄 | 自動 |
| TC-125 | 裁決 9；原話 2（Create samplesheet from `schema_input.json`） | 不在範圍 | 同上 | 看上傳頁 | 沒有「依管線 schema 建樣本表」的介面；樣本表只有「選一個檔」與「不給則自動配對 R1/R2」兩種 | 自動 |
| TC-126 | 裁決 9；原話 2（Uploaded data table） | 不在範圍 | alice 已登記一個資料集 | 看上傳頁與進度頁 | 沒有「已上傳資料」表格（版本、使用於、checksum、更新時間） | 自動 |
| TC-127 | 不做（國網／Slurm 網頁上傳） | 不在範圍 | alice 有 `nchc1`（Slurm 類） | `POST /upload` 指定 `nchc1` | 被拒（4xx）；沒寫檔、沒排工作；頁面（TC-007）已說明國網環境請用指令上傳 | 自動 |
| TC-128 | 不做（斷點續傳、2 GB 以上） | 不在範圍 | 路由清單 | 列出路由中含 upload 的 | 恰為 `/upload`（GET、POST）與 `/upload/{batch}`（GET），沒有分段、續傳、取消或刪除上傳的路由；2 GB 以上的檔走 TC-034／TC-037 的 413 加指令 | 自動 |
| TC-129 | 不做（AI／MCP 上傳工具）；ADR 0010（聊天工具與個人存取權杖沒有上傳工具） | 不在範圍 | MCP 工具清單與聊天工具清單 | 列出全部工具名稱 | 沒有名稱或功能是上傳檔案的工具；既有工具數與清單（`test_mcp.py`、`test_chat_tools.py`）一字未改且綠 | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-130 | 原則 I 第 2 條（不得有第二份執行狀態、除了確認過的提交路徑外沒有東西提交） | 功能 | 本任務新增的檔 | 跑 `tests/no_second_run_state_test.sh` | 綠；新增的 `actions/uploads.py` 等沒有被掃出「提交」或「第二份 run 狀態」；批次紀錄只記上傳，不是執行狀態 | 自動：`tests/no_second_run_state_test.sh` |
| TC-131 | 原則 II 第 3 條（不寫死路徑） | 功能 | 本任務新增的檔 | 跑 `tests/no_hardcoded_paths.sh` | 綠；上傳夾位置取自平台設定，不寫死個人或叢集路徑 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-132 | 原則 III 第 7 條（不需要找維護者）；原話 1 | 功能 | 一台經 Tailscale Funnel 對外的平台，一位同事帳號與一個 fixture 或真的雲端環境 | 同事只用網頁：選環境、填名稱版本、選 ≥100 MB 的真檔上傳，等進度頁到「已登記」，再到 `/launch` 第 4 步選它 | 全程沒有開終端機、沒有問任何人；進度頁每個檔最後是「✓ 完成」；第 4 步看得到這個資料集 | 手動：`docs/TESTING.md` 新節 |
| TC-133 | 安全網（憑證不外洩）；專長守則 backend（日誌與回應不含密鑰） | 例外 | 一次完整流程（成功一批、失敗一批），測試帶一個可辨認的 session cookie 值與 CSRF 值 | 收集所有回應本文、批次紀錄檔與平台日誌輸出 | 不含 session cookie 值、密碼；CSRF 值只出現在表單的隱藏欄位，不出現在網址、日誌或批次紀錄；不含雲端金鑰或 token | 自動 |
| TC-134 | 平台不開對外連線（`docs/PLATFORM.md` :323、:382；`actions/datasets.py` 模組說明；裁決 11）；作法 6 | 功能 | 一次完整上傳加登記流程 | 在流程中監看對外連線 | 平台沒有開任何非本機的連線；位元組只寫本機暫存夾；送雲端的事只由排入的工作完成 | 自動 |
| TC-135 | 作法 6；裁決 11 | 功能 | 本任務新增的 Python 檔 | 檢查 import | `web_upload.py`、`uploads_web.py`、`actions/uploads.py` 不 import 任何網路或雲端用戶端（`socket`、`urllib`、`http.client`、`requests`、`boto3`、`google.cloud` 之類）；`web.py` 的 CSP 常數沒改 | 自動 |
