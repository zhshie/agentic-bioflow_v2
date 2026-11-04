# 測試案例：引導送出第 4 步「樣本表預覽與欄位角色」（012b-2-guided-launch）

**規格**：`specs/012b-2-guided-launch/plan.md`（本任務沒有獨立 spec.md，以計畫及其「裁決」「補充裁決」為規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

## 共用假設（每條 TC 的前置條件都以此為底）

- 已登入網頁平台，開啟 `/launch`（引導送出頁）；使用假站台，不連真實站台、不真的送出任何分析。
- 「樣本表」指使用者自己上傳夾裡的 CSV 檔。「預覽表」指第 4 步顯示的檔案前幾列表格。
- 三種假管線規格（樣本表欄位規格，來自管線自己的 `schema_input`）：
  - **管線甲**：必填 `sample`、`fastq_1`、`fastq_2`；選填 `strandedness`。
  - **管線乙**：必填 `sample`、`forwardReads`、`reverseReads`（取自維護者的例句）。
  - **管線丙**：必填 `sample`、`fastq_1`；沒有 `fastq_2` 欄。
- 「自動」的測試檔為新檔 `platform/tests/test_web_guided_launch_preview.py`（以下簡稱預覽測試檔），除非 TC 另外寫明檔案。
- 實作前須先 `git merge origin/v3`（計畫「裁決」第 1 條），否則看不到 `platform/` 的網頁檔。

維護者原話（逐字，對應的 TC 在下方使用）：

> 「介面上不要有AI太口語化的回覆，要有制式化的通知呈現 ("樣本表少了 reverseReads 欄，AI 改不了。"這種不行)」→ TC-104、TC-105、TC-521
>
> 「另外一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」→ TC-521、TC-520
>
> 「分析名稱要放在第1個順位，前置檢查一律在設定那邊做好，沒做好就不跑……」→ TC-612、TC-613
>
> 「先把功能做起來吧，以後再改美觀」（只用現有 class 與 DESIGN.md token）→ TC-605、TC-606
>
> DESIGN.md 第 4 步：「4 Samplesheet (column roles, preview, n/n paired; with none uploaded: "No samplesheet has been uploaded. Please upload one first." and a link)」→ TC-301、TC-511、TC-101～TC-103、TC-201

## User Story 1 — 選了樣本表，第 4 步直接顯示預覽表（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；作法 2 | 功能 | 上傳夾有一份樣本表，已在第 4 步選它 | 開 `/launch` | 第 4 步出現標題「樣本表預覽」與一張預覽表；不再出現「預覽與欄位角色（尚未開放）」 | 自動：`test_preview_replaces_not_yet_open` |
| TC-002 | 作法 2 | 功能 | 樣本表有 8 列資料，已選 | 開 `/launch` | 預覽表的資料列恰好 5 列 | 自動：`test_preview_first_five_rows_and_total` |
| TC-003 | 作法 2 | 功能 | 樣本表欄位順序為 `sample, fastq_2, fastq_1, extra`，已選 | 開 `/launch` | 預覽表欄位順序與檔內相同（`sample, fastq_2, fastq_1, extra`），不依管線規格重排 | 自動 |
| TC-004 | 作法 2 | 功能 | 樣本表有 8 列資料，已選 | 開 `/launch` | 表下出現「共 8 列」與「僅顯示前 5 列」 | 自動：`test_preview_first_five_rows_and_total` |
| TC-005 | 補充裁決（恰 5 列） | 功能 | 樣本表恰好 5 列資料，已選 | 開 `/launch` | 預覽表 5 列、出現「共 5 列」；不出現「僅顯示前 5 列」 | 自動 |
| TC-006 | 空狀態（只有標頭） | 功能 | 樣本表只有標頭列、沒有資料列，已選 | 開 `/launch` | 預覽表顯示標頭、沒有資料列，出現「共 0 列」；頁面正常（200） | 自動 |
| TC-007 | 作法 2；裁決 10 | 功能 | 某儲存格內容為 70 個英文字元，且最後 10 字為獨有的 `ZZZZZZZZZZ` | 開 `/launch` | 該格只顯示前 60 字元再加「…」；`ZZZZZZZZZZ` 不出現在整頁 HTML | 自動 |
| TC-008 | 裁決 10 | 功能 | 某儲存格恰好 60 個英文字元 | 開 `/launch` | 該格完整顯示，沒有「…」 | 自動 |
| TC-009 | 裁決 10（以字元計） | 功能 | 某儲存格為 60 個中文字（180 位元組） | 開 `/launch` | 該格完整顯示，沒有「…」 | 自動 |
| TC-010 | 裁決 10 | 功能 | 某儲存格為 61 個中文字 | 開 `/launch` | 該格只顯示前 60 字再加「…」（共 61 字元），第 61 個字不在 HTML | 自動 |
| TC-011 | 作法 5；`test_cell_content_is_escaped` | 功能 | 某儲存格內容為 `<script>alert(1)</script>` | 開 `/launch` | 輸出為 `&lt;script&gt;`，原樣的 `<script>` 不在預覽表內 | 自動：`test_cell_content_is_escaped` |
| TC-012 | 專長守則（不得有 script） | 功能 | 同 TC-011 | 開 `/launch` | 整頁 HTML 不含 `<script` | 自動：`test_cell_content_is_escaped` |
| TC-013 | 裁決 8 | 功能 | 樣本表標頭含欄名 `<b>x</b>` 與 `a"b` | 開 `/launch` | 預覽表標頭輸出為 `&lt;b&gt;` 與 `&quot;`；整頁無 `<script` | 自動 |
| TC-014 | 裁決 8 | 功能 | 同 TC-013，且已選管線 | 開 `/launch` | 「欄位角色」區中的欄名同樣以 `&lt;b&gt;`、`&quot;` 輸出，沒有原始 `<b>` | 自動 |
| TC-015 | 六項檢核 1；作法 1 | 功能 | 已選樣本表 | 只開 `/launch`（GET），不按送出 | 沒有建立任何待確認的送出請求，沒有啟動任何東西 | 自動 |
| TC-016 | 範圍：actions；裁決 5 | 功能 | 8 列樣本表 | 直接呼叫 `preview_samplesheet(..., limit=5)` | 回傳含 `columns`、`rows`、`total`、`truncated`、`paired` 五個鍵；`rows` 至多 5 列；`total` 為 8；`truncated` 為真 | 自動 |

## User Story 2 — 欄位角色與缺少的必填欄（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-101 | 作法 3；DESIGN 第 4 步「column roles」 | 功能 | 選管線甲；樣本表含 `sample` 欄 | 開 `/launch` | `sample` 該列顯示「✓ 必填」（符號與文字同時出現） | 自動：`test_column_roles_symbol_and_text` |
| TC-102 | 作法 3 | 功能 | 選管線甲；樣本表含 `strandedness` 欄 | 開 `/launch` | `strandedness` 該列顯示「✓ 選填」 | 自動：`test_column_roles_symbol_and_text` |
| TC-103 | 作法 3 | 功能 | 選管線甲；樣本表含管線沒有的欄 `extra` | 開 `/launch` | `extra` 該列顯示「— 管線無此欄」 | 自動：`test_column_roles_symbol_and_text` |
| TC-104 | 維護者原話第 7 點（reverseReads 例句）；作法 3 | 功能 | 選管線乙；樣本表有 `sample`、`forwardReads`，**沒有** `reverseReads` | 開 `/launch` | 角色區另列一行「✗ 缺少必填欄」並附欄名 `reverseReads` | 自動：`test_column_roles_symbol_and_text` |
| TC-105 | 維護者原話第 7 點 | 功能 | 同 TC-104 | 開 `/launch` | 第 4 步不出現「AI 改不了」，也不出現「AI」字樣或「樣本表少了 … 欄，」這類整句口語；缺欄只用制式的「✗ 缺少必填欄」＋欄名 | 自動 |
| TC-106 | 作法 3 | 功能 | 選管線甲；樣本表有 5 個欄位 | 開 `/launch` | 角色區中，樣本表的每個欄位各恰好一列角色，沒有遺漏、沒有重複 | 自動 |
| TC-107 | 作法 3 | 功能 | 選管線甲；樣本表含全部必填欄 | 開 `/launch` | 頁面不出現「缺少必填欄」 | 自動 |
| TC-108 | 裁決 C（不阻擋送出） | 功能 | 選管線乙；樣本表缺 `reverseReads`（出現「✗ 缺少必填欄」） | 在頁上按「送出（前往確認頁）」 | 送出鍵仍在、可按；送出後仍進入既有確認頁，沒有被預覽擋下 | 自動 |
| TC-109 | 裁決 2（沒選管線） | 例外 | 尚未選管線；已選樣本表 | 開 `/launch` | 第 4 步顯示預覽表，但不列欄位角色、不列配對；頁面 200 | 自動 |
| TC-110 | 裁決 4；作法 3 | 例外 | 選管線甲，但管線的樣本表規格仍在讀取中 | 開 `/launch` | 預覽表照常顯示，其下顯示既有的「讀取中」字樣 | 自動：`test_schema_loading_and_missing_cases` |
| TC-111 | 裁決 4 | 例外 | 同 TC-110 | 開 `/launch` | 不列任何欄位角色，也不出現「已配對」 | 自動：`test_schema_loading_and_missing_cases` |
| TC-112 | 補充裁決（`_failure`）；作法 3 | 例外 | 選管線甲，但讀取管線樣本表規格失敗 | 開 `/launch` | 預覽表照常顯示；顯示既有的讀取失敗訊息；不列角色與配對；頁面 200 | 自動 |
| TC-113 | 作法 3；六項檢核 6 | 例外 | 選的管線沒有樣本表規格（沒有 `schema_input`） | 開 `/launch` | 只顯示預覽表；不列角色、不列配對；沒有 `✗` 錯誤句；頁面 200 | 自動：`test_schema_loading_and_missing_cases` |
| TC-114 | 專長守則（狀態不只靠顏色）；作法 6 | 功能 | 選管線甲；樣本表同時有必填欄、選填欄、管線沒有的欄，且缺一個必填欄 | 開 `/launch` | 四種角色標示（`✓ 必填`、`✓ 選填`、`— 管線無此欄`、`✗ 缺少必填欄`）在 HTML 裡都同時含符號與文字，不是只靠 class 顏色 | 自動 |

## User Story 3 — 已配對 n／N（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-201 | 作法 4；DESIGN「n/n paired」 | 功能 | 選管線甲；樣本表有 `fastq_1`、`fastq_2`，共 4 列，其中 3 列兩欄都有內容 | 開 `/launch` | 出現「已配對 3／4」 | 自動：`test_paired_count_when_both_fastq_columns` |
| TC-202 | 作法 4（N 用總列數） | 功能 | 選管線甲；樣本表共 8 列，其中 6 列兩欄都有內容 | 開 `/launch` | 出現「已配對 6／8」（分母是總列數 8，不是預覽的 5 列） | 自動 |
| TC-203 | 補充裁決（純空白視為空） | 功能 | 選管線甲；某列 `fastq_2` 只有空白字元 | 開 `/launch` | 該列不計入已配對數 | 自動 |
| TC-204 | 作法 4（不猜） | 例外 | 選管線丙（沒有 `fastq_2`）；樣本表有 `fastq_1`、`fastq_2` | 開 `/launch` | 頁面不出現「已配對」 | 自動：`test_paired_count_when_both_fastq_columns` |
| TC-205 | 作法 4 | 例外 | 選管線甲；樣本表有 `fastq_1` 但沒有 `fastq_2` | 開 `/launch` | 頁面不出現「已配對」 | 自動：`test_paired_count_when_both_fastq_columns` |
| TC-206 | 作法 4 | 例外 | 選管線甲；樣本表有 `fastq_2` 但沒有 `fastq_1` | 開 `/launch` | 頁面不出現「已配對」 | 自動 |
| TC-207 | 裁決 5 | 功能 | 樣本表欄位不含 `fastq_1` 與 `fastq_2` | 直接呼叫 `preview_samplesheet` | 回傳中 `paired` 鍵存在，值為 `None`（不是 0、不是缺鍵） | 自動 |

## User Story 4 — 空狀態與讀取失敗（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-301 | DESIGN 第 4 步（無樣本表）；裁決 3 | 例外 | 使用者沒有任何已上傳的樣本表 | 開 `/launch` | 第 4 步顯示「尚無已上傳的樣本表，請先上傳。」與指向 `/upload` 的連結；沒有預覽表 | 自動：`test_no_sheet_selected_no_preview` |
| TC-302 | 裁決 3 | 例外 | 同 TC-301 | 開 `/launch` | 不出現「選定樣本表後顯示預覽。」 | 自動 |
| TC-303 | 裁決 3 | 例外 | 有已上傳的樣本表，但沒有選任何一份 | 開 `/launch` | 第 4 步顯示「選定樣本表後顯示預覽。」，沒有預覽表，頁面 200 | 自動：`test_no_sheet_selected_no_preview` |
| TC-304 | 裁決 3 | 例外 | 同 TC-303 | 開 `/launch` | 不出現「尚無已上傳的樣本表」（有清單時不得說沒上傳） | 自動 |
| TC-305 | 補充裁決（名稱不在清單） | 例外 | 有已上傳的樣本表；網址帶入選的檔名為 `../x` | 開 `/launch` | 視同未選：顯示「選定樣本表後顯示預覽。」，沒有預覽表，頁面 200 | 自動：`test_only_own_uploads` |
| TC-306 | 補充裁決；作法 7 | 例外 | 另一位使用者的上傳夾有檔 `other.csv`（內含獨有字串）；網址帶入該檔名 | 開 `/launch` | 視同未選（同 TC-305 的句子）；獨有字串不出現在頁面 | 自動：`test_only_own_uploads` |
| TC-307 | 裁決 2（沒選管線） | 例外 | 尚未選管線；有已上傳的樣本表 | 開 `/launch` | 第 4 步仍顯示樣本表選單；頁面含「分析名稱」與「送出（前往確認頁）」；不含「預覽與欄位角色（尚未開放）」 | 自動 |
| TC-308 | 裁決 7；`test_unreadable_sheet_says_so_and_send_still_works` | 例外 | 已選的樣本表檔大於 1 MiB | 開 `/launch` | 第 4 步顯示「樣本表超過 1 MiB，無法預覽。」，前面有 `✗`；頁面 200 | 自動：`test_unreadable_sheet_says_so_and_send_still_works` |
| TC-309 | 裁決 7 | 例外 | 已選的樣本表檔內含 NUL 位元組 | 開 `/launch` | 顯示「樣本表不是 UTF-8 文字檔，無法預覽。」，前面有 `✗` | 自動：`test_unreadable_sheet_says_so_and_send_still_works` |
| TC-310 | 裁決 7 | 例外 | 已選的樣本表檔不是 UTF-8 編碼 | 開 `/launch` | 顯示「樣本表不是 UTF-8 文字檔，無法預覽。」，前面有 `✗` | 自動：`test_unreadable_sheet_says_so_and_send_still_works` |
| TC-311 | 裁決 9 | 例外 | 已選的樣本表檔是 0 位元組 | 開 `/launch` | 顯示「樣本表是空的，沒有標頭列。」，前面有 `✗`；不顯示預覽表，不列角色與配對 | 自動 |
| TC-312 | 裁決 7 | 例外 | 已選的樣本表在清單內，但讀取時已不屬於呼叫者或已被移除 | 開 `/launch` | 顯示「無法讀取所選樣本表，請重新上傳。」，前面有 `✗`；頁面 200，不是 500 | 自動 |
| TC-313 | 裁決 7 | 例外 | 觸發 TC-308～TC-312 任一種失敗 | 開 `/launch` | 失敗句中不含檔案內容、檔案路徑、「Traceback」字樣 | 自動 |
| TC-314 | 六項檢核 2 | 例外 | 觸發讀取失敗 | 開 `/launch` | 「送出（前往確認頁）」鍵仍在，第 1、2、3、5、6 步內容照常顯示 | 自動：`test_unreadable_sheet_says_so_and_send_still_works` |
| TC-315 | 作法 1（預覽不阻擋送出） | 例外 | 觸發讀取失敗，其餘欄位填妥 | 按「送出（前往確認頁）」 | 行為與沒有預覽時相同：進入既有確認頁，不被預覽擋下 | 自動 |
| TC-316 | 專長守則（狀態不只靠顏色） | 例外 | 觸發讀取失敗 | 開 `/launch` | 失敗句的 HTML 同時有 `✗` 符號（`csym` 樣式）、文字，且用既有 `bad` class | 自動 |

## User Story 5 — 只准看自己的上傳夾（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-401 | 作法 7；範圍：actions | 例外 | 另一位使用者上傳夾有檔 `other.csv` | 以本人身分呼叫 `preview_samplesheet` 指向 `other.csv` | 被拒絕（`Refusal`，一句白話）；拒絕訊息不含該檔內容 | 自動：`test_only_own_uploads` |
| TC-402 | 作法 7 | 例外 | 一般登入 | 以 `../` 開頭的路徑呼叫 `preview_samplesheet` | 被拒絕，不洩漏任何檔案內容 | 自動：`test_only_own_uploads` |
| TC-403 | 範圍：actions（不跟隨連結） | 例外 | 本人上傳夾裡有一個指向夾外檔案的連結檔 | 呼叫 `preview_samplesheet` 指向該連結檔 | 被拒絕，不讀取夾外檔案 | 自動 |
| TC-404 | 作法 7（不接受任意路徑） | 例外 | 一般登入 | 以絕對路徑呼叫 `preview_samplesheet` | 被拒絕 | 自動 |
| TC-405 | 範圍：actions；裁決 9 | 例外 | 本人上傳夾有 0 位元組的樣本表 | 呼叫 `preview_samplesheet` | 拋出 `Refusal`，一句白話 | 自動 |
| TC-406 | 範圍：actions | 例外 | 本人樣本表含 NUL 位元組 | 呼叫 `preview_samplesheet` | 拋出 `Refusal`，一句白話 | 自動 |
| TC-407 | 範圍：actions | 例外 | 本人樣本表不是 UTF-8 | 呼叫 `preview_samplesheet` | 拋出 `Refusal`，一句白話 | 自動 |
| TC-408 | 範圍：actions | 例外 | 本人樣本表超過 1 MiB | 呼叫 `preview_samplesheet` | 拋出 `Refusal`，一句白話 | 自動 |
| TC-409 | 範圍：`test_owner_guard.py` | 功能 | 新增動作 `preview_samplesheet` | 跑 `platform/tests/test_owner_guard.py` | 全綠；若掃描要求列名只補了一行，沒有放寬或刪除任何既有斷言 | 自動：`test_owner_guard.py` |
| TC-410 | 範圍：`test_web_parity.py`；裁決 B | 功能 | 新增動作 `preview_samplesheet` | 跑 `platform/tests/test_web_parity.py` | 全綠；`preview_samplesheet` 登在 `WEB_ONLY`（理由「網頁專用，樣本表預覽，無 MCP 工具」）；`OWED` 沒有變動 | 自動：`test_web_parity.py` |
| TC-411 | 範圍：不新增 MCP 工具 | 不在範圍 | 完成後 | 列出 MCP 伺服器的工具清單 | 與修改前相同，沒有新增樣本表預覽工具 | 自動 |

## User Story 6 — 用字、英文與制式通知（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-501 | 作法 2、5 | 功能 | 已選樣本表 | 開 `/launch?lang=en` | 第 4 步出現「Samplesheet preview」 | 自動：`test_english` |
| TC-502 | 裁決 7 | 功能 | 選管線甲；樣本表含 `sample` | 開 `/launch?lang=en` | `sample` 該列顯示「✓ Required」 | 自動：`test_english` |
| TC-503 | 裁決 7 | 功能 | 選管線甲；樣本表含 `strandedness` | 開 `/launch?lang=en` | 該列顯示「✓ Optional」 | 自動：`test_english` |
| TC-504 | 裁決 7 | 功能 | 選管線甲；樣本表含 `extra` | 開 `/launch?lang=en` | 該列顯示「— Not in this pipeline」 | 自動：`test_english` |
| TC-505 | 裁決 7 | 功能 | 選管線乙；樣本表缺 `reverseReads` | 開 `/launch?lang=en` | 顯示「✗ Missing required column」與 `reverseReads` | 自動：`test_english` |
| TC-506 | 裁決 7 | 功能 | 同 TC-201 | 開 `/launch?lang=en` | 顯示「Paired 3/4」 | 自動：`test_english` |
| TC-507 | 裁決 7 | 功能 | 8 列樣本表 | 開 `/launch?lang=en` | 顯示「8 rows in total」 | 自動：`test_english` |
| TC-508 | 裁決 7 | 功能 | 8 列樣本表 | 開 `/launch?lang=en` | 顯示「Showing the first 5 rows」 | 自動：`test_english` |
| TC-509 | 裁決 7（單數） | 功能 | 只有 1 列資料的樣本表 | 開 `/launch?lang=en` | 顯示「1 row in total」（不是「1 rows」） | 自動 |
| TC-510 | 裁決 3 | 功能 | 有清單、未選樣本表 | 開 `/launch?lang=en` | 顯示「The preview appears once a samplesheet is selected.」 | 自動 |
| TC-511 | DESIGN 第 4 步英文原文；補充裁決 | 功能 | 沒有任何已上傳的樣本表 | 開 `/launch?lang=en` | 顯示「No samplesheet has been uploaded. Please upload one first.」與指向 `/upload` 的連結 | 自動 |
| TC-512 | 裁決 7 | 例外 | 樣本表超過 1 MiB | 開 `/launch?lang=en` | 顯示「The samplesheet is larger than 1 MiB and cannot be previewed.」 | 自動 |
| TC-513 | 裁決 7 | 例外 | 樣本表含 NUL 或不是 UTF-8 | 開 `/launch?lang=en` | 顯示「The samplesheet is not a UTF-8 text file and cannot be previewed.」 | 自動 |
| TC-514 | 裁決 7 | 例外 | 所選樣本表讀不到 | 開 `/launch?lang=en` | 顯示「The selected samplesheet cannot be read. Please upload it again.」 | 自動 |
| TC-515 | 裁決 9 | 例外 | 樣本表為 0 位元組 | 開 `/launch?lang=en` | 顯示「The samplesheet is empty and has no header row.」 | 自動 |
| TC-516 | 作法 5 | 功能 | 有預覽、角色、配對的狀態 | 開 `/launch?lang=en`，取第 4 步 | 內容不含任何中文字 | 自動：`test_english` |
| TC-517 | 作法 5 | 例外 | 觸發 TC-512～TC-515 各狀態 | 開 `/launch?lang=en`，取第 4 步 | 內容不含任何中文字 | 自動 |
| TC-518 | 作法 5 | 功能 | 「無樣本表」與「有清單未選」兩種狀態 | 開 `/launch?lang=en` | 第 4 步內容不含任何中文字 | 自動 |
| TC-519 | 作法 5 | 功能 | 所有新增的 `g_pv_*` 字串 | 檢查 `STRINGS` | 每個新鍵在 `zh`、`en` 兩邊都有，且非空 | 自動 |
| TC-520 | 維護者 2b 原話（不口語）；範圍 | 功能 | 新增的中文字串 | 跑 `test_web_wording_sweep.py` | 全綠，且新字串沒有出現在其禁字表（「這個」「一下」「還沒有」「用過」等） | 自動：`test_web_wording_sweep.py` |
| TC-521 | 維護者原話第 7 點、2b 原話 | 功能 | 任何第 4 步狀態（有預覽、缺欄、失敗、未選） | 開 `/launch` | 第 4 步不出現「選用這個樣本」「用過的」及「AI」字樣；所有通知句都是制式短句 | 自動 |
| TC-522 | 範圍：取代 `g_preview` | 功能 | 已選樣本表 | 開 `/launch?lang=en` | 不再出現「Preview and column roles (not yet available)」 | 自動 |

## User Story 7 — 前端限制與不動別處（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-601 | 範圍（全頁無 script） | 功能 | 預覽、角色、配對都顯示的狀態 | 開 `/launch` | 整頁 HTML 不含 `<script` | 自動：`test_no_script_no_inline_style_csp_unchanged` |
| TC-602 | 範圍（無 inline style） | 功能 | 同 TC-601 | 開 `/launch` | 整頁 HTML 不含 `style=` | 自動：`test_no_script_no_inline_style_csp_unchanged` |
| TC-603 | 範圍（單一 style） | 功能 | 同 TC-601 | 開 `/launch` | 整頁恰好一個 `<style>` | 自動：`test_no_script_no_inline_style_csp_unchanged` |
| TC-604 | 範圍（CSP 不變） | 功能 | 同 TC-601 | 開 `/launch` | 回應的 CSP 標頭與修改前（2d 版）逐字相同，`img-src` 維持 2d 的樣子 | 自動：`test_no_script_no_inline_style_csp_unchanged` |
| TC-605 | 維護者 2 原話「先把功能做起來吧」；範圍（不新增 CSS） | 功能 | 同 TC-601 | 開 `/launch` | 那個 `<style>` 的內容與修改前完全相同（沒有新增 CSS） | 自動 |
| TC-606 | 範圍；作法 6 | 功能 | 同 TC-601 | 開 `/launch` | 預覽、角色、失敗句用到的 class 只限 `tbl`、`muted`、`off`、`bad`、`csym` | 自動 |
| TC-607 | 範圍：不做第 3 步搜尋 | 不在範圍 | 完成後 | 開 `/launch`；跑三條既有斷言 | 第 3 步仍是「搜尋全部 nf-core（尚未開放）」；`test_web_guided_launch.py:168`、`test_web_guided_launch_2.py:210`、`test_web_guided_launch_2b.py:658` 皆綠 | 自動 |
| TC-608 | 不做：逐步模式 | 不在範圍 | 完成後 | 開 `/launch` | 頁面仍只有單一「送出（前往確認頁）」鍵，沒有「下一步」按鈕；程式沒有讀取 `step_mode` 旗標 | 自動 |
| TC-609 | 不做：版本政策 | 不在範圍 | 完成後 | 開 `/launch`；跑 2d 版本相關既有測試 | 版本仍只選一次，頁面沒有新增「記住版本」或「新版提示」；2d 既有測試皆綠 | 自動 |
| TC-610 | 不做：不改樣本表內容 | 不在範圍 | 已選樣本表，記下檔案雜湊 | 開 `/launch` 數次 | 上傳夾內該檔案位元組不變 | 自動 |
| TC-611 | 不做：不建立／不編輯樣本表 | 不在範圍 | 已選樣本表 | 開 `/launch` | 預覽區沒有任何輸入欄、按鈕或「建立樣本表」控制項 | 自動 |
| TC-612 | 維護者 2d 原話（前置檢查不放回 /launch） | 不在範圍 | 完成後 | 開 `/launch` | 頁面不出現「前置檢查」 | 自動 |
| TC-613 | 維護者 2d 原話（分析名稱第 1） | 不在範圍 | 完成後 | 開 `/launch` | 六步順序仍是 分析名稱→運算環境→管線→樣本表→參數→確認；只列可用的運算環境 | 自動 |
| TC-614 | 不新增路由 | 不在範圍 | 完成後 | 比對 Route 表 | 與修改前相同，沒有新增路由 | 自動 |
| TC-615 | 不動第 5 步 | 不在範圍 | 完成後 | 開 `/launch` | 第 5 步仍沒有「之後開放」（`test_web_guided_launch_2.py:455` 綠） | 自動 |
| TC-616 | 不動第 1、2、3、5、6 步 | 不在範圍 | 同樣輸入，修改前後各開一次 `/launch` | 比對 | 除第 4 步外，其餘各步文字與修改前相同 | 自動 |
| TC-617 | 範圍：被釘住的舊測試（`test_web_guided_launch_2.py:398`） | 功能 | 修改後 | 跑 `test_web_guided_launch_2.py` | 原本斷言「預覽與欄位角色（尚未開放）」的地方改為斷言新的預覽內容；其餘斷言未被放寬；全綠 | 自動：`test_web_guided_launch_2.py` |
| TC-618 | 範圍；裁決 2 | 功能 | 修改後 | 跑 `test_web_guided_launch_2b.py` | 第 616 行「no pipeline」清單恰為 `["尚未選擇", "分析名稱", "送出（前往確認頁）"]`，只刪掉「預覽與欄位角色（尚未開放）」；全綠 | 自動：`test_web_guided_launch_2b.py` |
| TC-619 | 範圍；`test_web_guided_launch.py:363` | 功能 | 修改後 | 跑 `test_web_guided_launch.py` | 全綠；第 363 行只有在它依賴 `g_preview` 時才改預期，否則原樣保留 | 自動：`test_web_guided_launch.py` |
| TC-620 | 範圍（只改預期，不刪案例） | 功能 | 修改前後 | 比對上述三個既有測試檔的測試函式 | 測試函式數量與名稱不減少；沒有新增跳過、沒有放寬的斷言 | 自動 |
| TC-621 | 範圍：檔案清單；完成標準 | 不在範圍 | 完成後 | 驗收者讀 `git diff --stat <base>...HEAD` | 只含計畫「範圍：檔案」所列的檔（含 `docs/TESTING.md`），沒有 `web_settings.py`、`store.py`、`jobs.py`、`schema.py`、`mcp_server.py`、`static/*`、其他計畫檔 | 手動：`docs/TESTING.md` |
| TC-622 | 範圍：`web.py` 只動 `/launch` GET | 不在範圍 | 完成後 | 驗收者讀 `web.py` 的 diff | diff 不含 `/settings` 一帶（約 1103～1330 行）；沒有新增路由行 | 手動：`docs/TESTING.md` |
| TC-623 | 範圍：`web_board.py` 只動兩處 | 不在範圍 | 完成後 | 驗收者讀 `web_board.py` 的 diff | diff 不含 `_report_cell`、`SETTINGS`、`_frame`；只動 `g_preview`／`g_pv_*` 字串與第 4 步那一行 | 手動：`docs/TESTING.md` |

## User Story 8 — 畫面與手機寬度（手動，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-701 | 六項檢核 5；完成標準（有預覽） | 功能 | 起動應用程式；選管線與樣本表，欄位齊全 | 跑 `scripts/dev/ui_check.py`（1440／390 × 中文／英文，共 4 張） | 4 張截圖都顯示預覽表、角色、已配對；內容可讀、不重疊 | 手動：`docs/TESTING.md` |
| TC-702 | 完成標準（缺必填欄） | 功能 | 同上，但樣本表缺一個必填欄 | 同上 4 張 | 4 張都顯示「✗ 缺少必填欄」（符號＋文字）與欄名 | 手動：`docs/TESTING.md` |
| TC-703 | 完成標準（讀取失敗） | 功能 | 同上，但樣本表是非 UTF-8 檔 | 同上 4 張 | 4 張都顯示 `✗` 加一句白話；送出鍵仍在 | 手動：`docs/TESTING.md` |
| TC-704 | 六項檢核 5（手機寬度） | 功能 | 390 寬 | 看 TC-701 的手機截圖 | 預覽表沒有橫向捲動，維持既有卡片式排版 | 手動：`docs/TESTING.md` |
| TC-705 | 專長守則（axe） | 功能 | 同 TC-701 | 跑 `ui_check.py` 的 axe 無障礙掃描 | 沒有 serious 或 critical 項目 | 手動：`docs/TESTING.md` |
| TC-706 | 裁決 6 | 功能 | 修改後 | 讀 `docs/TESTING.md` 的 diff | 只新增第 4 步三種狀態（有預覽、缺必填欄、讀取失敗）的手動檢查條目，沒有改動既有條目 | 手動：`docs/TESTING.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-801 | 第 2 條（唯一提交路徑的掃描涵蓋 `platform/`） | 功能 | 新增唯讀動作 `preview_samplesheet` | 跑 `tests/no_second_run_state_test.sh` | 全綠；新動作不提交、不寫檔 | 自動：`tests/no_second_run_state_test.sh` |
| TC-802 | 第 2 條（未確認不得啟動） | 功能 | 修改後 | 跑 `test_human_channel.py` 的 `test_tch09_*` 與 `test_confirm_page.py` 的 `test_tch09_b_c_*` | 全綠；送出仍只經 `POST /launch` → 確認頁 | 自動 |
| TC-803 | 第 6 條（欄位來自管線自己的 `schema_input`） | 功能 | 一個本倉庫沒見過的假管線規格（欄位名為任意新名稱） | 開 `/launch`，樣本表含該些欄 | 角色依該規格正確顯示；倉庫沒有新增任何逐管線的設定檔；`tests/no_per_pipeline_config.sh` 全綠 | 自動 |
| TC-804 | 第 2 條（不得另存一份狀態） | 功能 | 已選樣本表 | 開 `/launch` 數次 | 平台資料夾中沒有出現新檔，樣本表內容沒有被另存成快取或索引 | 自動 |
