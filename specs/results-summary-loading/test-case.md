# 測試案例：結果頁摘要卡「讀取中」（results-summary-loading）

**規格**：`specs/results-summary-loading/plan.md`（本任務沒有 spec.md，計畫即規格；維護者無直接原話，依 results-files TC-026 字面行為）　**總覽**：`test-case-overview.md`

名詞：「摘要卡」＝結果頁上方的卡片；「兩格」＝摘要卡下方那一行裡的「報告」「MultiQC 報告」；「輸出分頁」＝結果頁的輸出檔案分頁；「列表」＝系統向站台讀取的輸出資料夾清單。所有「自動」案例的測試都寫在 `platform/tests/test_results_summary_loading.py`（既有測試的改動另註明），並在註解標出 TC 編號。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 輸出列表還在讀取時，摘要卡兩格寫「讀取中」（優先度 P1）

依據 results-files TC-026 逐字：「輸出列表還在讀取，或讀取失敗｜開結果階段｜兩格沒有下載連結，也不寫『此管線沒有產生』（因為尚不知道有沒有）」。TC-026 沒規定要寫什麼字；本計畫補上：讀取中寫「讀取中」（英文 `Reading`）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；作法 1、2 | 功能 | 一個已成功的 run，輸出列表剛排進工作、尚未讀完（假站台） | 同事直接開該 run 結果頁的輸出分頁（中文） | 「報告」「MultiQC 報告」兩格各自都寫「讀取中」 | 自動：`test_loading_cells_say_reading` |
| TC-002 | 目標；作法 2 | 功能 | 同 TC-001 | 同 TC-001 | 兩格都不再出現「之後開放」 | 自動：`test_loading_cells_say_reading` |
| TC-003 | results-files TC-026（逐字）；作法 2 | 功能 | 同 TC-001 | 同 TC-001 | 兩格都不寫「此管線沒有產生」（因為還不知道有沒有） | 自動：`test_loading_cells_say_reading` |
| TC-004 | results-files TC-026（逐字）；作法 2「不放連結」 | 功能 | 同 TC-001 | 同 TC-001 | 兩格都沒有指向 `/run/file` 的下載連結 | 自動：`test_loading_cells_say_reading` |
| TC-005 | 作法（「指標」「全部下載」不變）；範圍 | 功能 | 同 TC-001 | 同 TC-001 | 「指標」「全部下載」兩格仍是灰色的「之後開放」（`<span class="off">… <span class="later">之後開放</span></span>`），沒有被改成讀取中 | 自動：`test_loading_cells_say_reading` |
| TC-006 | 作法 5 | 功能 | 同 TC-001 | 同 TC-001，網址加 `&lang=en`（英文頁） | 「報告」「MultiQC 報告」對應的兩格都寫 `Reading`，且不含 `Coming later` | 自動：`test_loading_cells_english` |
| TC-007 | 作法 5 | 功能 | 同 TC-006 | 同 TC-006 | 英文頁的「Metrics」「Download all」兩格仍寫 `Coming later` | 自動：`test_loading_cells_english` |
| TC-008 | 作法 5「英文頁不得出現中文字」 | 功能 | 同 TC-006 | 同 TC-006 | 英文頁主要內容（`mid()` 取出的部分）不含任何中文字 | 自動：`test_loading_cells_english` |
| TC-009 | 專長守則「符號＋文字」；作法 2 | 功能 | 同 TC-001 | 同 TC-001，取出兩格的 HTML | 每一格的 HTML 同時含符號 `⟳` 與文字「讀取中」，不是只靠顏色或 class | 自動：`test_loading_cells_say_reading`（狀態表達斷言） |
| TC-010 | 作法 2「沿用既有符號與 class，不新增 class」 | 功能 | 同 TC-001 | 同 TC-001，取出兩格的 HTML | 每一格的結構是「標籤字（報告／MultiQC 報告）＋ `<span class="ostat state-running">⟳ 讀取中</span>`」，包在 `<span class="off">` 內；用的是既有 class `state-running`，沒有新 class | 自動：`test_loading_cells_say_reading`（狀態表達斷言） |
| TC-011 | 專長守則／作法 2「不用 inline style」 | 功能 | 同 TC-001 | 同 TC-001，取整頁 HTML | 整頁 HTML 不含 `style=` | 自動：`test_loading_cells_say_reading`（狀態表達斷言） |
| TC-012 | 六項必填 3 | 功能 | 同 TC-001 | 看讀取中狀態的結果頁截圖 | 兩格仍在摘要卡下方原本那一行，沒有多出新的段落、版面沒有變 | 手動：PR 附結果頁讀取中狀態截圖（計畫完成標準），閱卷者對照 |
| TC-013 | 六項必填 5 | 功能 | 同 TC-001 | 用手機寬度看同一頁截圖 | 兩格是行內短字，與原本同寬度級，沒有出現橫向捲動 | 手動：PR 附結果頁讀取中狀態截圖（手機寬度） |

## User Story 2 — 其他狀態維持原樣，不退步（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 作法 3；六項必填 2 | 例外 | 輸出分頁已開過，列表讀取失敗（站台回 not_found） | 再開一次輸出分頁 | 「報告」「MultiQC 報告」兩格仍是灰色「之後開放」 | 自動：`test_failed_listing_keeps_later_words` |
| TC-015 | 作法 3 | 例外 | 同 TC-014 | 同 TC-014 | 兩格不含「讀取中」（讀取失敗不能說還在讀） | 自動：`test_failed_listing_keeps_later_words` |
| TC-016 | results-files TC-026（逐字）；作法 3 | 例外 | 同 TC-014 | 同 TC-014 | 兩格不寫「此管線沒有產生」，也沒有下載連結 | 自動：`test_failed_listing_keeps_later_words` |
| TC-017 | 作法 4 | 例外 | 已成功的 run，從沒排過列表（沒開過輸出分頁） | 直接開 `?run=<id>&stage=results&tab=tasks`（任務分頁） | 兩格是「之後開放」，不是「讀取中」（該分頁不會自動更新，寫讀取中會永遠不變） | 自動：`test_other_tabs_do_not_claim_reading` |
| TC-018 | 作法 4 | 例外 | 同 TC-017 | 同 TC-017 | 開任務分頁沒有因此排出任何讀列表的工作（排程清單仍為空） | 自動：`test_other_tabs_do_not_claim_reading` |
| TC-019 | 作法 4 | 例外 | 已成功的 run，第一層列表尚未讀到 | 開輸出分頁的子資料夾頁（例如 `multiqc` 資料夾） | 兩格不含「讀取中」，維持「之後開放」 | 自動：`test_subfolder_page_does_not_claim_reading` |
| TC-020 | 作法 1 末段、作法 3（c）「沒有送出紀錄／不是自己的 run」 | 例外 | 沒有送出紀錄的 run，或不是自己的 run | 開該 run 的結果頁輸出分頁 | 兩格維持「之後開放」，不寫「讀取中」 | 自動（計畫的測試清單未列，執行者須補一條新測試並標 TC-020） |
| TC-021 | 作法 6；results-files TC-025 不退步 | 功能 | 列表已讀完，第一層有 `multiqc/` 與 `summary_report/` | 開輸出分頁 | 「報告」「MultiQC 報告」兩格是下載連結，不是讀取中 | 自動：`test_ready_listing_still_gives_links_or_none` |
| TC-022 | 作法 6；results-files TC-025 不退步 | 功能 | 列表已讀完，但第一層沒有那兩個資料夾 | 開輸出分頁 | 兩格寫「此管線沒有產生」，不是讀取中、也沒有連結 | 自動：`test_ready_listing_still_gives_links_or_none` |
| TC-023 | 範圍：既有測試同步（`test_ro01…`） | 功能 | 既有測試 `test_web_results_outputs.py::test_ro01_results_stage_has_cards_and_tabs`，預期已改 | 開輸出分頁、第一次載入（中文） | 「報告」「MultiQC 報告」兩格是讀取中，「指標」「全部下載」仍是「之後開放」；該測試只改預期、沒有刪案例 | 自動：`test_web_results_outputs.py::test_ro01_results_stage_has_cards_and_tabs` |
| TC-024 | 範圍：既有測試同步（`test_ro10_english`） | 功能 | 既有測試 `test_web_results_outputs.py::test_ro10_english`，預期已改 | 開輸出分頁、第一次載入（英文） | 「Report」「MultiQC report」兩格是 `Reading`，「Metrics」「Download all」仍是 `Coming later`；只改預期、沒有刪案例 | 自動：`test_web_results_outputs.py::test_ro10_english` |
| TC-025 | 範圍：已核對不受影響的既有測試 | 功能 | `test_results_files.py` 的 `test_tc025_*`、`test_tc026_unknown_means_no_link_and_no_claim`、`test_tc037_the_cards_keep_two_greyed_words_and_the_tabs_stay` 沒有被修改 | 執行這幾個測試 | 全部維持通過（無連結、無「此管線沒有產生」仍成立；列表讀完時兩格與「指標」「全部下載」不變） | 自動：`test_results_files.py` |

## User Story 3 — 範圍界線：只修這一個狀態（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 不做：不改 `web.py`、其他分頁、完成階段 `web_finished.py`；範圍：檔案 | 不在範圍 | 實作完成後的分支 | 看 `git diff --stat <base>...HEAD` | 異動檔案只有：`platform/abf_platform/web_board.py`（且只動 `_report_cell`／`_results_body`）、新測試檔、`test_web_results_outputs.py`；沒有 `web.py`、`web_finished.py` | 手動：閱卷者看 diff stat（ledger 亦須貼出，計畫完成標準） |
| TC-027 | 不做：不給 `run_outputs` 新增「已排工作」旗標；不改 `actions/__init__.py` | 不在範圍 | 同 TC-026 | 看 diff | `platform/abf_platform/actions/__init__.py` 沒有任何異動 | 手動：閱卷者看 diff stat |
| TC-028 | 不做：不改左欄的字 | 不在範圍 | 既有測試 `test_web_board.py`（約 :317）與 `test_web_upload.py`（約 :1017）釘著左欄的「之後開放」 | 執行這兩個測試 | 維持通過、沒有被改動預期 | 自動：`test_web_board.py`、`test_web_upload.py` |
| TC-029 | 不做第 2 條：其他分頁在列表其實正在讀時仍寫「之後開放」（計畫接受的行為） | 不在範圍 | 先開輸出分頁讓列表排進工作且未讀完 | 再切到任務分頁 | 兩格仍是「之後開放」，不是「讀取中」（沒有偷偷做「所有分頁都準確」） | 自動（計畫的測試清單未列，執行者須補一條新測試並標 TC-029） |
| TC-030 | 不做：不新增字串、不改讀取失敗的字、不動 STYLE／CSP | 不在範圍 | 同 TC-026 | 看 `web_board.py` 的 diff | 中文用既有 `o_loading`（「讀取中」）、英文用既有 `Reading`；字串表、STYLE 區塊、CSP 設定沒有新增或修改 | 手動：閱卷者看 diff |
