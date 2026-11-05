# 測試案例：網頁四個畫面缺陷（#338 #341 #342 #343）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
Reader: the maintainer, who is not an engineer.
Language: 繁體中文; identifiers and file paths stay as they are.
-->

**規格**：`specs/web-bugs-b/plan.md`（本任務沒有 spec.md；以計畫內逐字引用的四個 issue 原話與 DESIGN.md 原文為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應（顯示「—」、退回固定句、不丟例外）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

自動測試檔：新檔 `platform/tests/test_web_bugs_b.py`（只用 `render_usage`、`render_board`、`web_board.STYLE`、`read_run`，不開瀏覽器）。手動步驟：`docs/TESTING.md` 新增的「390 px 手動檢查」，用 `scripts/dev/ui_check.py --start`。

## User Story 1 — 費用頁（/usage）中文註記與月份標題（#338）（優先度 P1）

維護者原話：「中文『國網 SU（本月）』卡片的註記顯示 `task NFCORE_AMPLISEQ:AMPLISEQ:RENAME_RAW_DATA_FILES`，英文版同一張卡顯示 `no SU factor for partition ngs8g`。`/usage?month=2026-10` 時，卡片標題仍是『國網 SU（本月）』與『雲端已用（本月）』（英文 `this month`）。預期：中文顯示對應 `no SU factor for partition ngs8g` 的中文原因，不是任務名稱；標題與所顯示的月份一致。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | #338 原話；計畫 1.1 | 功能 | 有一筆算不出 SU 的原因：`task NFCORE_AMPLISEQ:AMPLISEQ:RENAME_RAW_DATA_FILES: 分區 ngs8g 沒有 SU 係數 (no SU factor for partition ngs8g)` | 以中文開 `/usage`（`render_usage`，lang=zh） | 國網 SU 卡片註記含「分區 ngs8g 沒有 SU 係數」；整頁不含 `NFCORE_AMPLISEQ`，也不含 `task `（任務名稱不出現） | 自動：`test_web_bugs_b.py::test_338_zh_reason_has_no_task_name` |
| TC-002 | #338 原話「英文版…顯示 `no SU factor for partition ngs8g`」；計畫 1.1 | 功能 | 同 TC-001 的資料 | 以英文開 `/usage` | 卡片註記就是 `no SU factor for partition ngs8g`（與改前一致）；英文頁沒有任何中日韓文字 | 自動：`test_338_en_reason_unchanged` |
| TC-003 | 計畫 1.1「中英文顯示同一件事」 | 功能 | 同 TC-001 的資料 | 以中文開 `/usage` | 中文註記不帶結尾英文括號 `(no SU factor …)`；原因的意思與英文版同一件事（分區 ngs8g 沒有 SU 係數） | 自動：`test_338_zh_reason_has_no_task_name`（含此斷言） |
| TC-004 | 計畫 1.1、`test_338_reason_fallbacks` | 例外 | reasons 是空的 | 中英文各開 `/usage` | 註記顯示既有的 `no_reason` 固定句，不是空白、不是錯誤 | 自動：`test_338_reason_fallbacks` |
| TC-005 | 計畫 1.1 | 例外 | reasons 只有 `task X: `，冒號後沒有原因 | 中英文各開 `/usage` | 註記顯示 `no_reason` 固定句 | 自動：`test_338_reason_fallbacks` |
| TC-006 | 計畫 1.1「多段只取第一段」 | 例外 | reasons 的第一筆含多段，以 `"; "` 相接（例：兩個原因） | 中英文各開 `/usage` | 註記只含第一段原因，第二段文字不出現 | 自動：`test_338_reason_fallbacks` |
| TC-007 | 計畫 1.1「英文須無 CJK，否則 `no_reason`」 | 例外 | 原因結尾括號內含中文字 | 以英文開 `/usage` | 英文頁註記顯示 `no_reason`，整頁無中日韓文字 | 自動：`test_338_reason_fallbacks` |
| TC-008 | #338 原話 `/usage?month=2026-10`；計畫 1.2 | 功能 | 目前月份是 2026-11；看 `month=2026-10` | 以中文開 `/usage?month=2026-10` | 卡片標題為「國網 SU（2026-10）」「雲端已用（2026-10）」；頁面不含「（本月）」 | 自動：`test_338_past_month_titles_show_month` |
| TC-009 | #338 原話「（英文 `this month`）」 | 功能 | 同 TC-008 | 以英文開 `/usage?month=2026-10&lang=en` | 標題含 `(2026-10)`，不含 `this month`，整頁無中日韓文字 | 自動：`test_338_past_month_titles_show_month` |
| TC-010 | 計畫 1.2「本月照舊、字串一字不改」 | 功能 | 看的月份就是目前月份 | 中英文各開 `/usage` | 中文標題仍是「國網 SU（本月）」「雲端已用（本月）」；英文仍含 `this month` | 自動：`test_338_current_month_titles_unchanged` |
| TC-011 | 計畫 1.2「其他月份（含未來月）」 | 功能 | 看未來月 `month=2099-01` | 中英文各開 | 標題顯示 `2099-01`，標題裡沒有「本月」／`this month` | 自動：`test_web_cost.py`（:226 改後的斷言） |
| TC-012 | 計畫 1.3 | 功能 | 非本月、該月沒有任何分析（`2099-01`） | 中英文各開 | 中文空表句為「— 2099-01 尚無分析」；英文含 `No analyses in 2099-01`，英文頁無中日韓文字 | 自動：`test_338_empty_month_sentence` |
| TC-013 | 計畫 1.3「本月句不動」 | 功能 | 本月沒有任何分析 | 中英文各開 `/usage` | 中文仍是「— 本月尚無分析」；英文仍是 `No analyses this month` | 自動：`test_338_empty_month_sentence`；`test_web_cost.py:349-351` 不改仍綠 |
| TC-014 | 計畫 1.3「action 是本月待辦，非本月不顯示」 | 功能 | 本月雲端額度已用盡的資料，但看的是過去月份 | 開 `/usage?month=<過去月>` | 頁面不出現「待處理：本月雲端額度已用盡」；看本月時照舊出現（`test_su_usd.py:370` 不改仍綠） | 自動：`test_web_bugs_b.py`（executor 補一條）與 `test_su_usd.py:370` |
| TC-015 | 計畫「必須維持不變」清單 | 功能 | 既有測試 | 執行既有費用頁測試 | `test_web_cost.py:148`（本月四張卡標題）、`:190/215/525`、`test_web_wording_sweep.py:489`（「另有 N 個分析無法計算」）、`:261-263`、`:478`、`:480`、`test_su_usd.py:370/412/417` 一字未改且全綠 | 自動：上述既有測試檔 |
| TC-016 | 計畫 1.5；六項檢核 3、4 | 功能 | 新增字串 `card_su_month`、`card_used_month`、`empty_month` | 跑 zh／en 對等檢查與禁用詞掃描 | 每個新字串中英各一；英文版無中日韓文字；通過既有禁用詞掃描（不口語） | 自動：`test_web_wording_sweep.py` 與 `test_web_cost.py` 既有對等檢查 |
| TC-017 | 計畫「允許改動的斷言」 | 功能 | `test_web_cost.py:226` 原斷言 `/usage?month=2099-01` 含「本月尚無分析」 | 看 diff | 該斷言只改為「含該月空表句」並加「標題無『本月』」；沒有刪掉案例，也沒有其他 cost 斷言被改 | 手動：驗收者以 `git diff` 比對 base 的 `test_web_cost.py` |

## User Story 2 — run 頁標題列資訊行與執行資訊分頁（#341）（優先度 P1）

維護者原話：「標題列只有名稱＋狀態徽章（＋『更多』）…『執行資訊』分頁只有 id、名稱、狀態、開始、結束，沒有管線版本與站台。預期：標題列含 `pipeline revision · site · started · last update`。」頁面：`/?run=876a9a8b617c67f1`、`/?run=876a9a8b617c67f1&stage=running&tab=info`。DESIGN.md：「title row (name, state pill, `pipeline revision · site · started · last update`)」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | #341 原話；計畫 2.2 | 功能 | 一個保留的 run，有管線、版本、站台、開始時間、最後訊息時間 | 以中文開 run 頁（`render_board`） | `.head` 內有一個 `class="meta"` 的段落，內含管線、版本、站台、開始時間、最後更新五個值（只查值在，不釘整行字面） | 自動：`test_341_head_has_meta_line` |
| TC-019 | 計畫 六項檢核 3；`test_341_head_has_meta_line` | 功能 | 同 TC-018 | 以英文開 run 頁 | `.head` 內同樣有 `class="meta"` 與五個值；英文頁無中日韓文字 | 自動：`test_341_head_has_meta_line` |
| TC-020 | 計畫 2.2、結構釘 | 功能 | 同 TC-018 | 看 run 頁標題列 | 資訊行在徽章與「更多」之後、仍在 `.head` 內；`test_web_fixes_1.py:24`、`test_web_status_squares_3.py:42`、`test_web_board.py:684/756/1270` 不改仍綠 | 自動：上述既有測試 |
| TC-021 | 計畫 2.2「最後更新」取值順序 | 功能 | 三種 run：有 `last_message_at`；沒有但有 `ended_at`；兩者都沒有只有 `started_at` | 各開一次 run 頁 | 最後更新依序顯示 `last_message_at`、`ended_at`、`started_at` 的時間（`_time` 格式 `MM-DD HH:mm`） | 自動：`test_web_bugs_b.py`（executor 補一條，可併入 `test_341_head_has_meta_line`） |
| TC-022 | 計畫 2.2；`test_341_meta_line_missing_values_dash` | 例外 | 手作的 run dict 缺 pipeline／revision／last_message_at（`render_board` 常被測試這樣呼叫） | 開 run 頁 | 不丟例外；缺的值顯示「—」，其他欄位照常 | 自動：`test_341_meta_line_missing_values_dash` |
| TC-023 | #341 原話「執行資訊分頁…沒有管線版本與站台」；計畫 2.4 | 功能 | 保留的 run，中文 | 開 `?stage=running&tab=info` | 原有列（id、名稱、狀態、開始、結束）仍在；另有管線、版本、站台、最後更新四列（`<dl class="fields">`） | 自動：`test_341_info_tab_has_new_rows` |
| TC-024 | 計畫 2.4、六項檢核 3 | 功能 | 同 TC-023，英文 | 開英文資訊分頁 | 四列都在；整頁無中日韓文字；既有 `test_web_running.py:284-328`（含 :291）、`test_web_board.py:545/1284/1296`、`test_web_results_outputs.py:92/106`、`test_results_files.py:590` 不改仍綠 | 自動：`test_341_info_tab_has_new_rows` 與上述既有測試 |
| TC-025 | 計畫 2.1 | 功能 | `launch_prefill` 回 `kept: True` 並帶 `pipeline`、`revision`、`ce_name` | 呼叫 `read_run` | 回傳的 view 有 `pipeline`、`revision` | 自動：`test_341_read_run_adds_pipeline_revision` |
| TC-026 | 計畫 2.1「外來 run → 顯示『—』」 | 例外 | `launch_prefill` 回 `{"found": False, "kept": False}`（外來 run） | 呼叫 `read_run`，再開 run 頁 | view 沒有 `pipeline`／`revision`；不丟例外；資訊行對應欄位顯示「—」 | 自動：`test_341_read_run_adds_pipeline_revision` |
| TC-027 | 計畫 2.1「已忘記 → 顯示『—』」 | 例外 | `launch_prefill` 回 `{"found": True, "kept": False, …}` | 同 TC-026 | 同 TC-026：欄位不放、不丟例外、顯示「—」 | 自動：`test_341_read_run_adds_pipeline_revision` |
| TC-028 | 計畫 2.1「站台用 `compute_env`，沒有時用 `ce_name`」 | 功能 | 兩種 run：view 有 `compute_env`；沒有 `compute_env` 但 prefill 有 `ce_name` | 開 run 頁 | 站台依序顯示 `compute_env`、`ce_name`；兩者皆無則「—」 | 自動：`test_web_bugs_b.py`（executor 補一條，可併入 `test_341_read_run_adds_pipeline_revision`） |
| TC-029 | 計畫 2.4、六項檢核 3、4 | 功能 | #341 新增的 zh／en 字串（管線、版本、站台、最後更新） | 跑 zh／en 對等與禁用詞掃描 | 每個字串中英各一；英文無中日韓文字；通過禁用詞掃描；站台字樣沿用 `web_finished.py` 既有同義詞，不自造 | 自動：`test_web_wording_sweep.py`、`test_web_nano4_path.py:546-557` 的既有掃描 |
| TC-030 | #341 原話兩個頁面 | 功能 | 以 `ui_check.py --start` 起暫時平台（種了一個成功的 run） | 在 1440 px 開 `/?run=<id>` 與 `/?run=<id>&stage=running&tab=info`，中英文各一次 | 標題列多一行「管線 版本 · 站台 · 開始 · 最後更新」且獨占一行；資訊分頁看得到管線、版本、站台、最後更新 | 手動：`docs/TESTING.md`（新增步驟） |

## User Story 3 — 右欄寬度 360／300（#342）（優先度 P1）

維護者原話：「1440 px：左 272、右 320（規格 360）。1100 px（≤1200）：左 232、右 288（規格 300）。預期：DESIGN.md Skeleton『Right column 360px』；『≤1200px: 232 / fluid / 300.』；『Where this file and the drafts differ, this file wins』。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | #342 原話「Right column 360px」；計畫 3 | 功能 | `web_board.STYLE` | 讀樣式表 | 含 `272px minmax(0,1fr) 360px` | 自動：`test_342_right_column_360_300` |
| TC-032 | #342 原話「≤1200px: 232 / fluid / 300」 | 功能 | 同上 | 讀 `@media (max-width:1200px)` 區塊 | 含 `232px minmax(0,1fr) 300px` | 自動：`test_342_right_column_360_300` |
| TC-033 | 計畫 3 | 功能 | 同上 | 搜尋欄寬規則 | 樣式表裡不再有 `320px`／`288px` 的欄寬規則 | 自動：`test_342_right_column_360_300` |
| TC-034 | 計畫 3「左欄 272／232 不動，≤900 px 單欄規則不動」 | 不在範圍 | 同上 | 讀樣式表 | 左欄仍為 272／232；≤900 px 仍是單欄，順序中欄→右欄→左欄（`test_web_board.py:211-212` 同區其他檢查不動仍綠） | 自動：`test_web_board.py::test_tcs11_s12_s13_layout_css` |
| TC-035 | #342 原話兩個寬度 | 功能 | `ui_check.py --start` | 在 1440 px 量右欄寬；視窗改 1100 px 再量 | 1440 px 右欄 360 px、左欄 272 px；1100 px 右欄 300 px、左欄 232 px（量到的數字寫進 PR／ledger） | 手動：`docs/TESTING.md`（新增步驟） |
| TC-036 | 計畫「不做」、裁決 1 | 不在範圍 | 看 diff | 查 `DESIGN.md` | `DESIGN.md` 沒有任何改動（維護者若要 320／288，另開任務） | 手動：驗收者以 `git diff --stat` 查 |
| TC-037 | 計畫「允許改動的斷言」 | 功能 | `test_web_board.py:211-212` 原釘 `320px`／`288px` | 看 diff | 只把這兩處預期改成 `360px`／`300px`，同區其他斷言與案例不動 | 手動：驗收者以 `git diff` 比對 base |

## User Story 4 — 手機寬度（390 px）可點區與檔名不斷字（#343）（優先度 P1）

維護者原話：「連結高 16–20 px：中 29×20、EN 35×20、輸出表的資料夾連結與『下載』、『報告』『MultiQC 報告』、『重新讀取』、『← 上一階段』『下一階段 →』、『開啟確認頁』。36 個可點元素中 15 個在某個方向小於 24 px。檔名在字中斷行（`cutadap`／`t`、`phylose`／`q`、`pipelin`／`e_info`、`overall`／`_summar`／`y.tsv`），且沒有水平捲動。預期：可點目標 ≥24×24 CSS px；檔名不要斷成單字元碎片（水平捲動或縮窄其他欄）。頁面：`/?run=876a9a8b617c67f1&stage=results&tab=outputs`；其他 run 頁與 `/usage` 的『← 上一月』也偏小。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | #343 原話；計畫 4.1 | 功能 | `web_board.STYLE` | 解析 `@media (max-width:900px)` 區塊 | 區塊內有 `min-height:24px`、`min-width:24px`，且規則涵蓋 `.switch a`、`.pager a`、`.views a`、`.rtabs a`、`.tbl a`、`.otbl a`、`.ostat a`、`.rail a`（`.ostat` 涵蓋「重新讀取」與麵包屑，`.views` 涵蓋 `/usage` 的「← 上一月」） | 自動：`test_343_mobile_min_target_rules` |
| TC-039 | 計畫 4.1「`display:inline-flex;align-items:center`」 | 功能 | 同上 | 同 TC-038 | 該規則含 `display:inline-flex` 與 `align-items:center` | 自動：`test_343_mobile_min_target_rules` |
| TC-040 | 計畫 4.1「只在 ≤900 px 內加」；不做第 3 條 | 不在範圍 | 同上 | 檢查 `@media (max-width:900px)` 區塊之外 | 寬螢幕（>900 px）沒有新增上述連結的 24 px 最小尺寸規則，桌面外觀不變 | 自動：`test_web_bugs_b.py`（executor 補一條，斷言區塊外無此規則） |
| TC-041 | 計畫 4.1「`.pager` 兩個鍵保持左右兩端」 | 功能 | `ui_check.py --start`，390 px | 開結果輸出頁看底部「← 上一階段」「下一階段 →」 | 兩個鍵仍分在左右兩端，沒有擠在一起 | 手動：`docs/TESTING.md`（新增步驟） |
| TC-042 | #343 原話檔名斷字；計畫 4.2 | 功能 | `web_board.STYLE` | 讀 `.otbl code` 規則 | 不再含 `overflow-wrap:anywhere`；改為 `overflow-wrap:normal;word-break:keep-all` | 自動：`test_343_otbl_filename_not_anywhere` |
| TC-043 | 計畫 4.2「水平捲動而不是斷成單字元」 | 功能 | 同上 | 讀 ≤900 px 區塊 | 輸出表（或其外框）有 `overflow-x:auto` | 自動：`test_343_otbl_filename_not_anywhere` |
| TC-044 | 計畫 4.2「`.tbl{table-layout:fixed}` 在 ≤900 px 的 `.otbl` 改回 `auto`」 | 功能 | 同上 | 讀 ≤900 px 區塊 | `.otbl` 的 `table-layout` 為 `auto` | 自動：`test_web_bugs_b.py`（executor 補一條，可併入 `test_343_otbl_filename_not_anywhere`） |
| TC-045 | 計畫 4.2「其他表不動」 | 不在範圍 | 同上 | 讀 `.tbl th,.tbl td` 規則 | 仍含 `overflow-wrap:anywhere`；其他表的斷行行為沒變 | 自動：`test_web_bugs_b.py`（executor 補一條）；既有表格測試不改仍綠 |
| TC-046 | #343 原話「36 個可點元素中 15 個小於 24 px」 | 功能 | `ui_check.py --start`，視窗 390 px（裝置模擬），中文與英文各一 | 開 `/?run=<id>&stage=results&tab=outputs`，逐一量所有可點元素：中、EN、輸出表資料夾連結與「下載」、「報告」「MultiQC 報告」、「重新讀取」、「← 上一階段」「下一階段 →」、「開啟確認頁」 | 每一個可點元素寬與高都 ≥24 CSS px（量到的數字寫進 PR／ledger） | 手動：`docs/TESTING.md`（新增步驟） |
| TC-047 | #343 原話檔名例子 | 功能 | 同 TC-046，輸出表有 `cutadapt`、`phyloseq`、`pipeline_info`、`overall_summary.tsv` | 看輸出表的檔名 | 這幾個檔名完整顯示成一段（`cutadapt`、`phyloseq`、`pipeline_info`、`overall_summary.tsv`），不再被切成 `cutadap`／`t`、`phylose`／`q`、`pipelin`／`e_info`、`overall`／`_summar`／`y.tsv`；太長時靠水平捲動 | 手動：`docs/TESTING.md`（新增步驟） |
| TC-048 | #343 原話「其他 run 頁與 `/usage` 的『← 上一月』也偏小」；計畫 4.4 | 功能 | 同 TC-046 | 在 390 px 開其他 run 頁（Now 頁、執行中、失敗的 run）與 `/usage`、`/usage?month=<過去月>` | 頁首「中／EN」、分頁連結、「← 上一月」「下一月 →」等可點元素 ≥24×24 | 手動：`docs/TESTING.md`（新增步驟） |
| TC-049 | 計畫 六項檢核 5「390 px 無水平溢出（輸出表除外）」 | 功能 | 同 TC-046 | 在瀏覽器主控台比較 `document.documentElement.scrollWidth` 與 `clientWidth` | 兩者相等（頁面沒有水平溢出）；輸出表自己可以水平捲動 | 手動：`docs/TESTING.md`（新增步驟） |

## User Story 5 — 共通限制、既有斷言與範圍（優先度 P1）

這一節對應 DESIGN.md Constraints（single stylesheet, no inline style, every screen exists in English）、專長守則（ui）與計畫的範圍、完成標準。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 計畫 六項檢核 2；`test_style_no_inline_no_script` | 功能 | 渲染 `/usage?month=<過去月>`、帶資訊行的 run 頁、結果輸出頁，中英文各一 | 檢查輸出的 HTML | 無 `style=`、無 `<script`；新規則都在同一個 `STYLE` 字串；沒有請求外部網址 | 自動：`test_style_no_inline_no_script` |
| TC-051 | 計畫 5、完成標準最後一條 | 功能 | 已 `git merge origin/v3`（含 `web-bugs-a`）之後 | 重算並更新 STYLE 長度與雜湊，跑這些測試 | `test_web_nano4_path.py:545`、`test_clean_page.py:158-163` 與 `BASE_STYLE`、`test_results_files.py:695`、`test_settings_pick_installed.py:692`、`test_web_resume_edit.py:612` 的值等於實際算出的值並全綠；CSP 的 `style-src sha256` 與 `style_source()` 相符；ledger 逐條列舊值→新值與重算指令 | 自動：上述既有測試檔 |
| TC-052 | 計畫「類別必須在 STYLE 內」 | 功能 | 新增 `class="meta"` | 檢查中欄用到的 class | `.head .meta` 規則在 `STYLE` 內（含 `flex-basis:100%`），`test_web_nano4_path.py:546-557`、`test_web_resume_edit.py:524` 不改仍綠 | 自動：上述既有測試 |
| TC-053 | 計畫 六項檢核 1「沒新顏色、沒新字型」 | 功能 | base 與改後的 `STYLE` | 比對兩者的色碼與字型宣告 | 改後沒有 base 之外的色碼或字型；`.head .meta` 只用既有 token 與色 | 自動：`test_web_bugs_b.py`（計畫未列此測試，executor 補一條）；否則驗收者看 diff |
| TC-054 | 專長守則「狀態＝符號＋文字＋顏色」 | 功能 | run 頁加了資訊行之後 | 渲染每種狀態的 run 頁標題列 | 狀態徽章仍同時含符號與文字；資訊行未把徽章擠掉（`test_web_status_squares_3.py:42` 不改仍綠） | 自動：`test_web_status_squares_3.py` 與 `test_web_board.py` 既有測試 |
| TC-055 | 專長守則；計畫完成標準「axe 無 serious／critical」 | 功能 | `ui_check.py --start` | 跑 1440／390 × zh／en，pages 含 `results`、`usage` | axe 沒有 serious 或 critical；摘要貼進 ledger | 手動：`docs/TESTING.md`（`ui_check.py`） |
| TC-056 | 計畫 完成標準「risk M 須附截圖」 | 功能 | 同上 | 截 `/usage?month=<過去月>`（中英）與 `?stage=results&tab=outputs`（390 px，中英），以及 1440 px 的 run 頁 | 截圖存於 repo 之外；畫面與 TC-008、TC-018、TC-046、TC-047 描述一致；PR 附上 | 手動：`docs/TESTING.md`（`ui_check.py`） |
| TC-057 | 計畫「範圍：檔案」、完成標準 | 功能 | `docs/TESTING.md` | 查文件 | 有「390 px 手動檢查」步驟，使用 `scripts/dev/ui_check.py`，涵蓋 TC-035、TC-041、TC-046、TC-047、TC-048、TC-049 的做法 | 手動：驗收者讀 `docs/TESTING.md` |
| TC-058 | 計畫「必須維持不變」 | 功能 | 清單內的既有斷言 | 比對 base 與改後的測試檔 | 清單內各斷言（TC-015、TC-020、TC-024、TC-052 所列）一字未改且全綠 | 自動：各既有測試檔 |
| TC-059 | 計畫「允許改動的斷言」「不得為了讓測試過而改別的斷言」 | 功能 | 看 diff | 比對所有被動到的既有測試檔 | 只有「必須改」清單內的斷言被改（`test_web_board.py:211-212`、`test_web_cost.py:226`、各 STYLE 長度／雜湊）；沒有刪案例、沒有放寬別的斷言 | 手動：驗收者以 `git diff` 比對 base |
| TC-060 | 專長守則「DESIGN.md 每個畫面、每個狀態」 | 功能 | 全部改動完成 | 跑完整測試套件（閘門） | 既有畫面測試（含空、載入、錯誤、失敗狀態）全綠；僅 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 屬已知環境紅 | 自動：完成記號 `GREEN <HEAD sha>` |
| TC-061 | 計畫「範圍：檔案」「完成標準」 | 不在範圍 | 看 diff | `git diff --stat` | 只含 `web_cost.py`、`web_board.py`、`web.py`、`docs/TESTING.md`、`test_web_bugs_b.py`，以及計畫列名的既有測試檔；沒有其他檔 | 手動：驗收者以 `git diff --stat` 查 |
| TC-062 | 計畫「不做」第 1 條 | 不在範圍 | 看 diff | 查 `su.py`、`actions/__init__.py`、`status.py`、`web_finished.py`、`dev-queue.json` | 全部未改；`su.py` 的原因格式（`task %s: …`、`"; "` 相接）不變，`launch_prefill` 回傳形狀不變 | 自動：`test_su_usd.py` 既有測試綠；diff 為空 |
| TC-063 | 計畫「範圍：檔案」`web.py` 只動 `read_run` | 不在範圍 | 看 diff | 查 `web.py` | 改動只在 `read_run`（約 :515–527）；其他函式沒動 | 手動：驗收者以 `git diff` 查 |
| TC-064 | 計畫「不做」第 3、4 條 | 不在範圍 | 看 diff | 查 `scripts/dev/ui_check.py` 與 pytest 依賴 | `ui_check.py` 未改；pytest 沒有加入 Playwright；24 px 規則沒有套到 >900 px 版面（見 TC-040）；除 `/usage` 外未重做其他頁 | 手動：驗收者以 `git diff` 查 |

## 憲法與安全網

本變更沒有碰 `.specify/memory/constitution.md` 的 1–13 條不變式與安全網（只改網頁的顯示、樣式與一個讀取函式；不改 hooks、不改 action 層、不改確認頁的放行流程）。DESIGN.md Constraints 與專長守則的限制已在 TC-050 至 TC-054 逐條對應。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|

<!--
IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
