# 測試案例：完成頁下載結果檔入口（finish-package-download）

**規格**：`specs/finish-package-download/plan.md`（本任務無獨立 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞：「完成頁」＝網頁上一次分析跑完後的「完成」階段頁面；「交付包區塊」＝完成頁上列出六列（結果表格、MultiQC 報告等）的那一塊；「輸出分頁」＝「結果 → 輸出」分頁，原本就能下載單一檔案；「頂層檔案」＝結果資料夾最外層的檔案（不含資料夾）。所有 TC 的測試檔為 `platform/tests/test_web_finished.py`，除非另有註明。

維護者原話（逐字，作為 TC 的輸入與預期）：
- 原話 1（11-05）：「跑完到pipline都有在網站上顯示及時狀態嗎? 能在上面下載結果黨嗎?」
- 原話 2（DESIGN.md 畫面 10）：「**Finished stage**: delivery package (edited report, tables, MultiQC, figures, methods with versions, samplesheet), provenance, Download.」
- 原話 3（ROADMAP 第 3 階段）：「A person with no AI tool completes setup → launch → running → results → downstream (in a Studio) → finished from the web alone」
- 原話 4（10-27 裁示）：「一樣要注意中文的顯示不能口語」

## User Story 1 — 完成頁直接列出可下載的結果檔（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「作法」第 2 點；失敗先行測試 1（fs12）；原話 1「能在上面下載結果黨嗎?」 | 功能 | 一次已成功的分析，擁有者已在「輸出」讀過結果，頂層有數個檔案與至少一個資料夾（沿用 `ENTRIES`）。 | 擁有者開啟該次分析的完成頁。 | 交付包區塊內出現標題「下載結果檔」恰一次；每個「非資料夾、非過大」的頂層檔案各有一條連結，連結形如 `href="/run/file?run=<rid>&amp;path=<檔名>"`；資料夾沒有連結。 | 自動：`test_fs12_finished_lists_download_links_for_top_level_files` |
| TC-002 | 計畫「作法」第 2 點（項目格式：名稱＋大小） | 功能 | 同 TC-001。 | 擁有者開啟完成頁，看任一檔案連結。 | 每條連結後面緊接該檔大小的文字（KB 或 MB，一位小數）；中英文頁面格式相同。 | 自動：`test_fs12`（大小斷言） |
| TC-003 | 失敗先行測試 2（fs13）；原話 2「MultiQC」；計畫「作法」第 2 點 | 功能 | 頂層有名為 `multiqc` 的資料夾。 | 擁有者開啟完成頁。 | 出現一條連到 `multiqc/multiqc_report.html` 的連結，字樣為既有的「MultiQC 報告」。 | 自動：`test_fs13_multiqc_links_to_the_report_file` |
| TC-004 | 失敗先行測試 2（fs13 負例；對映 `test_fs06` 負例） | 例外 | 頂層沒有 `multiqc`，或有一個名為 `multiqc` 的「檔案」（不是資料夾）。 | 擁有者開啟完成頁。 | 頁面上沒有任何連到 `multiqc/multiqc_report.html` 的連結。 | 自動：`test_fs13` |
| TC-005 | 失敗先行測試 3（fs14）；原話 1（25 MB 上限） | 例外 | 頂層有一個標為「過大」（超過 25 MB）的檔案。 | 擁有者開啟完成頁。 | 該檔顯示純文字「<檔名> 大於 25 MB」（文字說明，不只靠顏色）；該檔名沒有任何 `href`。 | 自動：`test_fs14_too_large_file_is_text_not_a_link` |
| TC-006 | 失敗先行測試 6（fs17）；計畫「作法」第 2 點（最多 20 項） | 功能 | 頂層有 25 個一般檔案，沒有 `multiqc` 資料夾。 | 擁有者開啟完成頁。 | 恰有 20 條下載連結；末尾一行「其餘檔案請至「查看輸出」。」，且「查看輸出」連到輸出分頁。 | 自動：`test_fs17_more_than_twenty_files_are_capped` |
| TC-007 | 失敗先行測試 7（fs18）；計畫「作法」第 5 點 | 功能 | 同 TC-001，另有一個過大檔；網址帶 `&lang=en`，檔名皆為 ASCII。 | 擁有者開啟英文完成頁。 | 標題為「Download result files」、過大檔旁為「Over 25 MB」；頁面不含任何中日韓字；下載連結帶 `lang=en`。 | 自動：`test_fs18_english_download_block` |
| TC-008 | 失敗先行測試 4（fs15）；計畫「作法」第 2 點（不加空標題） | 例外 | 分析已成功，但輸出尚未被讀取。 | 擁有者開啟完成頁。 | 頁面不含「下載結果檔」；頁面沒有排任何站台列表工作（`listings(w) == []`）。 | 自動：`test_fs15_no_block_before_outputs_are_read` |
| TC-009 | 失敗先行測試 4（fs15） | 例外 | 輸出讀取失敗，或讀到的列表是空的。 | 擁有者開啟完成頁。 | 兩種情況下頁面都不含「下載結果檔」，且 `listings(w) == []`。 | 自動：`test_fs15` |
| TC-010 | 原話 4「一樣要注意中文的顯示不能口語」 | 功能 | 新增的中文字串（標題、「大於 25 MB」、「其餘檔案請至「查看輸出」。」）。 | 執行中文用字檢查。 | 新字串為正式書面語，通過 `test_web_wording_sweep.py`，不含禁用詞；兩種語言的字串鍵相同（`dl_head`、`dl_big`、`dl_more`）。 | 自動：`platform/tests/test_web_wording_sweep.py` |

## User Story 2 — 既有行為不退步（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 失敗先行測試 8（fs19）；原話 2（六列交付包）；既有 `test_fs06`、`test_fs01` | 功能 | 完成頁有新區塊（同 TC-001，且有 `multiqc` 資料夾）。 | 擁有者開啟完成頁，取出交付包六列。 | 六列的值與原本逐字相同（`結果表格` 與 `MultiQC 報告` 皆為「✓ 在輸出資料夾」）；`class="steps"` 仍恰一個；新區塊的 `<li>` 以 `<li><a` 開頭，不被六列解析誤抓。 | 自動：`test_fs19_download_block_changes_nothing_else`、`test_fs06`、`test_fs01` |
| TC-012 | 失敗先行測試 8（fs19）；計畫「作法」第 4 點 | 功能 | 完成頁有新區塊。 | 擁有者以 GET 開啟完成頁。 | 頁面不含 `<form`、`<button`、內嵌 `style=`、`href="/download`；`jobs` 表的工作種類清單在開啟前後相同（頁面不新增任何工作）。 | 自動：`test_fs19`、`test_fs01`、`test_fs11` |
| TC-013 | 原話 1「已存在的「結果 → 輸出」分頁下載行為不得退步」 | 功能 | 既有結果頁的報告格與檔案下載測試。 | 執行 `test_results_files.py`、`test_results_summary_loading.py`。 | 全數仍綠，且 `web_board.py` 沒有被修改。 | 自動：`platform/tests/test_results_files.py`、`platform/tests/test_results_summary_loading.py` |
| TC-014 | 原話 3「from the web alone」；計畫「完成標準」截圖與 `docs/TESTING.md` 手動步驟 | 功能 | 已成功的分析；只有瀏覽器，沒有 AI 工具、沒有終端機。 | 開啟完成頁，點一個結果檔連結與 MultiQC 報告連結。 | 連結進入既有的 `/run/file` 下載流程（有檔就能取得）；完成頁有連結、過大檔、英文各一張截圖；手機寬度不橫向捲動。`docs/TESTING.md` 完成頁手動步驟已加入「點結果檔連結」一步且寫得能照做。 | 手動：`docs/TESTING.md`（完成頁段，第 785～790 行附近新增步驟） |

## User Story 3 — 只有擁有者能拿到自己的結果檔（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 失敗先行測試 5（fs16，跨使用者讀）；專長守則：擁有者規則 | 例外 | ann 有一次已成功且已讀輸出的分析；bob 是另一位使用者。 | bob 開啟 ann 那次分析的完成頁。 | 與既有行為一致的 404；回應中沒有任何 `/run/file` 連結，也沒有 ann 的檔名。 | 自動：`test_fs16_other_users_run_gives_no_links` |
| TC-016 | 失敗先行測試 5（fs16，跨使用者寫對應）；專長守則：跨使用者 TC | 例外 | 同 TC-015；記下 `jobs` 表中 `read_run_file` 的筆數。 | bob 用自己的 cookie 直接 GET ann 那次分析的 `/run/file?...`。 | 得到同一個 404／拒絕頁；`jobs` 表的 `read_run_file` 筆數不增加（不得替別人排站台讀檔工作）。 | 自動：`test_fs16` |

## User Story 4 — 範圍界線：整包交付包下載之後才開放（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 計畫「作法」第 3 點；「不做」第 1 條（`build_package` 留作下一刀）；原話 2「Download」 | 不在範圍 | 完成頁有新下載區塊。 | 擁有者開啟中文與英文完成頁。 | 「下載交付包」那一行原樣保留：中文為 `<p class="off">下載交付包 <span class="later">之後開放</span></p>`，英文為「Download delivery package」「Coming later」；`href="/download` 不存在；沒有整包下載連結。 | 自動：`test_fs08_download_is_coming_later`、`test_fs10_english` |
| TC-018 | 計畫「不做」第 1、2 條；「完成標準」動作數、路由數釘住 | 不在範圍 | 本刀完成後的整套程式。 | 執行動作數與路由數釘住的測試。 | 動作層仍為 54 個且 digest 不變、網頁路由仍為 30 個且 digest 不變；沒有 `build_package` 動作、沒有新網頁路由、沒有新站台工作種類；網頁／動作對等性與擁有者守衛測試未被修改且仍綠；`platform/abf_station/`、`jobs.py`、`store.py`、`web.py`、`web_board.py` 沒有出現在變更中。 | 自動：`test_k8s_launch.py::test_the_user_visible_actions_are_those_of_the_base`、`test_web_parity.py`、`test_actions_layer.py`、`test_owner_guard.py`、`test_mcp_contract_tools.py`（驗收時另以 `git diff` 核對路徑） |
| TC-019 | 計畫「不做」第 3 條（不改 25 MB 上限、不做多檔打包、不做整個資料夾下載） | 不在範圍 | 頂層有資料夾與過大檔。 | 擁有者開啟完成頁。 | 資料夾沒有下載連結；過大檔沒有連結；`jobs.RUN_FILE_MAX_BYTES` 仍為 26214400；頁面沒有「全部下載」或壓縮包連結。 | 自動：`test_fs12`、`test_fs14`、`platform/tests/test_results_files.py` |

## 憲法與安全網

<!-- 憲法與安全網：本刀不碰安全網（hooks、gate）；觸及的是後端專長守則（頁面不得有第二份邏輯、不得自行連網、不得替人排工作）。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 專長守則：動作層唯一、頁面不含第二份邏輯；既有 `test_fs07`（計畫第 9 點） | 功能 | `web_finished.py` 新增 `_downloads` 之後的原始碼。 | 執行 `test_fs07`。 | 原始碼不 import socket、urllib、subprocess 等網路或程序模組（連結一律用 `board._url`，不自行編碼網址）；頁面不排任何列表；`outputs` 仍只來自既有的 `run_outputs(enqueue=False)` 答案。 | 自動：`test_fs07` |

<!--
Rules for the writer:
- Every acceptance scenario and every FR in spec.md maps to at least one TC. Every
  "out of scope" item in spec.md maps to at least one 不在範圍 TC.
- A TC tests one thing. Two expectations = two rows.
- 驗證方式 is 自動 (a test file under tests/, named once it exists, "自動" until then)
  or 手動 (a step in docs/TESTING.md's manual half). Nothing else.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
