# 測試案例：設定頁「運算環境」表格在手機寬度改成卡片

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Every row can be judged without reading code.
Language: 繁體中文; identifiers (TC-, US) and file paths stay as they are.
-->

**規格**：`specs/settings-ce-table-mobile/plan.md`（這個任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

名詞：「卡片」指手機寬度（390 px）下，每個運算環境各佔一塊、六個欄位上下排列、每個欄位前面有自己的標籤。「base」指這個任務開工時的 v3（2552583b，已含 web-wording-sweep）。「現有測試」指 `platform/tests/` 下本任務之前就存在的測試檔。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：沒有資料、缺欄位時，畫面怎麼反應。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

維護者原話（逐字，驗收的依據）：

1. 「發現一個問題：手機寬度下「計算環境」表格太窄，字被切成「Nam/e」「Av/aila/ble」，看得到但難讀。我會開一件 B 級修正（手機改成上下排的卡片）」
2. 「先把功能做起來吧，以後再改美觀」（只修可讀性，不重新設計）

自動測試檔：新檔 `platform/tests/test_web_settings_ce_mobile.py`（簡稱「新測試檔」）。手動步驟寫在 `docs/TESTING.md` 新增的小節（TC-024 檢查它存在）；只能看 diff 的項目由執行者把證據貼進 `ledger.md`，驗收者自己重跑核對。

## User Story 1 — 手機寬度下每個環境一張卡片，欄位帶標籤（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；測試 A ce01 | 功能 | 有兩個運算環境（同現有測試的 `two_envs`） | 開 `/settings` | 「運算環境」區的表格標籤是 `<table class="tbl ce">`（不是只有 `class="tbl"`） | 自動：新測試檔 |
| TC-002 | 作法 1；測試 A ce02 | 功能 | 同上，語言為中文 | 開 `/settings`，看每個資料列 | 每列有 6 個 `<td data-label="…">`，標籤依序是「名稱、平台、狀態、站台代理、已登記管線、上次使用時間」 | 自動：新測試檔 |
| TC-003 | 作法 1；測試 A ce02 | 功能 | 同上，語言為英文 | 開 `/settings?lang=en` | 每列的 6 個標籤依序是「Name、Platform、Status、Site agent、Registered pipelines、Last used」 | 自動：新測試檔 |
| TC-004 | 作法 1；測試 A ce02 | 功能 | 兩個環境，其中一個有登記管線、另一個沒有 | 開 `/settings`，數資料列與格子 | 兩個環境各是一列，每列恰好 6 格、6 格都帶 `data-label`，表頭 `<th>` 沒有被加屬性 | 自動：新測試檔 |
| TC-005 | 作法 2；測試 A ce03 | 功能 | 頁面回應的樣式表 | 讀回應裡的 CSS | 含 `@media (max-width:640px)` 區塊，區塊內出現 `.tbl.ce`、`attr(data-label)`、`thead{display:none}` | 自動：新測試檔 |
| TC-006 | 維護者原話 1；測試 C 斷言 2 | 功能 | 兩個運算環境（其一有已登記管線，同 shots-1029 的 gcb1／gcb3）；用手機裝置模擬 390 px（`is_mobile=True`，不是拉視窗） | 開 `/settings?lang=en`，截圖 | 「Name」「Available」「Registered pipelines」整個詞都在同一行，沒有出現「Nam/e」「Av/aila/ble」這種被切開的字 | 手動：`docs/TESTING.md` 新小節 |
| TC-007 | 維護者原話 1；測試 C | 功能 | 同 TC-006 | 開 `/settings`（中文），390 px 截圖 | 六個欄位標籤（名稱、平台、狀態、站台代理、已登記管線、上次使用時間）每個都完整顯示，沒有被切成一字一行 | 手動：`docs/TESTING.md` 新小節 |
| TC-008 | 維護者原話 1（「上下排的卡片」）；完成標準 | 功能 | 同 TC-006，兩個環境 | 390 px 下看中、英截圖各一張 | 兩個環境是兩張分開的卡片；每張卡片六個欄位上下排列，每個值緊靠自己的標籤，不會散到別的欄位底下（例如狀態的符號與它的訊息文字、環境名稱與「主要」標記，仍在同一欄位內） | 手動：`docs/TESTING.md` 新小節 |
| TC-009 | 測試 C 斷言 1；完成標準 | 功能 | 用同一組資料，四種組合：1440 與 390（裝置模擬）× 中文與 `?lang=en` | 在每種組合下取 `document.documentElement.scrollWidth` 與 `clientWidth` | 四種組合都是 `scrollWidth <= clientWidth`（沒有橫向捲動）；兩組數字寫進 PR 與 ledger | 手動：`docs/TESTING.md` 新小節 |
| TC-010 | 測試 C 斷言 2（盡力）；預檢裁決 D | 功能 | 同 TC-006；資料含長字串（如 `nf-core/rnaseq 3.14.0`） | 390 px 下，對卡片內文字檢查「詞中折行」，或直接人工看四張圖 | 長度 20 字以內的詞不在詞中折行；長字串可在 `/` 折行不算失敗。若自動檢查取不到穩定結果，改人工看圖並在 ledger 註明，這時不以此退回；但「欄位標籤被切」仍判 FAIL | 手動：`docs/TESTING.md` 新小節 |
| TC-011 | 計畫「不改行為、不改資料」；測試 B | 功能 | 現有測試 `test_web_settings.py` 的 `test_st04_ce_table`、`test_st04b_status_mapping_and_unknown` | 跑這兩個測試 | 全綠：表頭六個中文詞不變；可用是「✓ 可用」帶 `state-succeeded`，無法使用是「✗ 無法使用」帶 `state-failed`，未檢查是「— 未檢查」；狀態同時有符號、文字與顏色 class；「主要」只出現在主要環境；最近使用時間與管線內容照舊 | 自動：`platform/tests/test_web_settings.py` |
| TC-012 | 作法 2「配色只用既有變數」 | 功能 | `.tbl.ce` 在 `@media (max-width:640px)` 內的所有規則 | 讀這些規則的顏色值 | 只用既有變數 `--raised`、`--line`、`--muted`（跟著深色模式），沒有新的十六進位色碼或 rgb 色值 | 自動：新測試檔（執行者補斷言，註解寫 TC-012） |
| TC-013 | 例外：沒有運算環境 | 例外 | 一個使用者沒有任何運算環境 | 開 `/settings` | 「運算環境」區顯示「尚無運算環境。」，沒有任何表格，也沒有 `tbl ce` | 自動：`platform/tests/test_web_settings.py` 的 `test_st04c_empty_and_escaping` |
| TC-014 | 例外：欄位沒有值 | 例外 | 一個環境沒有站台代理名稱、沒有登記管線、從未使用 | 開 `/settings` | 該列仍是 6 格且都帶標籤；沒值的格子顯示「—」，不是空白；表格內仍沒有連結、按鈕、輸入框或表單 | 自動：`platform/tests/test_web_settings.py` 的 `test_st04_ce_table` 與新測試檔 ce02 |

## User Story 2 — 桌面寬度的畫面與現在一樣（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 作法 2；測試 A ce04 | 功能 | 回應的樣式表 | 把 CSS 裡所有含 `.tbl.ce` 的規則取出 | 每一條都在 `@media (max-width:640px)` 區塊內，基礎規則（區塊外）一條也沒有，所以 640 px 以上不受影響 | 自動：新測試檔 |
| TC-016 | 測試 C 斷言 3；完成標準 | 功能 | 同一組資料（兩個環境）；base 分支與修改後各截一張 1440 px | 中文與英文各比對 base 與修改後的 1440 px 截圖 | 逐像素比對差異為 0（或明確說明為何為 0 以外），看起來與現在一樣 | 手動：`docs/TESTING.md` 新小節 |
| TC-017 | 作法 2；測試 A ce05 | 功能 | 執行頁與費用頁（它們也用 `.tbl`） | 開這兩頁，看表格 | 表格仍是 `<table class="tbl">`（不帶 `ce`），格子 `<td>` 不帶 `data-label` | 自動：新測試檔 |
| TC-018 | 範圍「不准碰」；`.tbl` 既有規則 | 功能 | 修改前後的 `web_board.py` | 看 diff 裡 `.tbl{…}` 與 `.tbl th,.tbl td{…}` 兩條規則 | 這兩條一字不動；本次在 `STYLE` 只新增一段 `@media (max-width:640px)` | 手動：執行者貼 `git diff` 到 `ledger.md`，驗收者重跑核對 |

## User Story 3 — 只改標記與樣式，不動字串、既有測試與其他東西（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 作法「零新字串」；測試 A ce06 | 功能 | base 的 `web_settings.STRINGS` 與 `web_board.STRINGS` | 比對修改後的兩份 | 鍵集合與每個值都與 base 完全相同（沒有新增、刪除、改寫任何一個字串） | 自動：新測試檔 |
| TC-020 | 測試 B | 功能 | 修改完成 | 跑 `test_web_settings.py`、`test_web_settings_register.py`、`test_web_parity.py`、`test_web_board.py` | 四個檔全綠 | 自動：這四個檔 |
| TC-021 | 範圍；作法 4；預檢裁決 A | 功能 | `git diff <base>...HEAD -- platform/tests` | 看測試目錄的差異 | 除新測試檔外，只有 `test_web_settings.py` 兩行（原 :201 與 :224）把 `"<td>"` 改成 `"<td"`，其他斷言一字不動，沒有被刪除、放寬或跳過的測試 | 手動：執行者貼 diff 到 `ledger.md`，驗收者重跑核對 |
| TC-022 | 完成標準「diff 範圍」 | 功能 | `git diff <base>...HEAD --stat` | 看改了哪些檔 | 只有 `web_settings.py`、`web_board.py`、新測試檔、`test_web_settings.py`、`docs/TESTING.md`，以及可選的 `scripts/dev/check_settings_mobile.py`（與任務目錄下的 ledger、截圖）；`web_settings.py` 只動 `_ce_row` 與 `_compute` 的標記，diff 中 `STRINGS` 相關行數為 0 | 手動：執行者貼 diff stat 到 `ledger.md`，驗收者重跑核對 |
| TC-023 | 完成標準「ledger 附…」；測試 C | 功能 | 修改完成 | 看 `specs/settings-ce-table-mobile/screenshots/` 與 `ledger.md` | 資料夾裡有 4 張截圖（1440／390 × 中文／英文），ledger 附 diff stat、四張截圖路徑、兩組 scrollWidth 數字 | 手動：`docs/TESTING.md` 新小節 |
| TC-024 | 範圍「`docs/TESTING.md` 新增一小節」 | 功能 | 修改完成 | 讀 `docs/TESTING.md` | 有新小節，寫明 Playwright 四張截圖（1440／390 裝置模擬 × 中英）與 scrollWidth 溢出檢查的步驟，具體到可照做 | 手動：`docs/TESTING.md` |
| TC-025 | 完成標準 | 功能 | 修改完成 | 在 WSL 跑 `bash tests/platform_test.sh` | 全綠（已知環境紅依 README 通例處理） | 自動：`tests/platform_test.sh` |

## User Story 4 — 計畫「不做」與前端限制（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 不做 1：不改任何字串、翻譯、標籤用詞 | 不在範圍 | 設定頁中文與英文 | 開 `/settings` 與 `/settings?lang=en`，看表頭與各區文字 | 表頭仍是原本的六個詞（中：名稱、平台、狀態、站台代理、已登記管線、上次使用時間；英：Name、Platform、Status、Site agent、Registered pipelines、Last used），沒有任何用詞被順手改掉；中英對照測試仍綠 | 自動：`platform/tests/test_web_settings.py`、`platform/tests/test_web_parity.py` |
| TC-027 | 不做 2：不碰其他頁面的表格、`.ptbl`、不把全站表格做成響應式 | 不在範圍 | 修改前後的 diff | 看 `.ptbl` 規則（原 :246-247）與其他頁面檔 | `.ptbl` 手機規則一字不動；`web_board.py` 中執行頁與其他頁面的表格標記沒有被改；沒有新增其他表格的手機規則 | 手動：執行者貼 diff 到 `ledger.md`，驗收者重跑核對 |
| TC-028 | 不做 3：不改資料、動作、路由、登記管線表單 | 不在範圍 | 設定頁的登記管線與移除管線表單 | 跑登記管線相關現有測試；看 diff 有無新增路由 | `test_web_settings_register.py` 全綠；`_env_block` 沒被改；沒有新增路由、資料庫或動作變更 | 自動：`platform/tests/test_web_settings_register.py` |
| TC-029 | 不做 4 與維護者原話 2：不重新設計卡片外觀 | 不在範圍 | `STYLE` 新增的那一段 | 看 diff | 新增的 CSS 只有一個 `@media (max-width:640px)` 區塊，沒有新顏色、新圖示（只有 `attr(data-label)` 的標籤文字）、新斷點，也沒有調整桌面外觀 | 手動：執行者貼 diff 到 `ledger.md`，驗收者重跑核對 |
| TC-030 | 不做 5：不新增 JS | 不在範圍 | 設定頁輸出與 diff | 比對修改前後的設定頁 `<script>` 與 diff | 設定頁沒有新增 `<script>`，diff 沒有新增 JS | 手動：執行者貼 diff 到 `ledger.md`，驗收者重跑核對 |
| TC-031 | 範圍「不准碰」清單 | 不在範圍 | `git diff <base>...HEAD --stat` | 找這些檔 | `web_upload.py`、`web_launch.py`、`web_cost.py`、`web_finished.py`、`web.py`、`DESIGN.md`、`PRODUCT.md`、任何資料庫或動作層的檔案都沒有出現在 diff 裡 | 手動：執行者貼 diff stat 到 `ledger.md`，驗收者重跑核對 |
| TC-032 | 前端限制：設計文件規定樣式表單一、不得有 inline style（DESIGN.md 第 90 行） | 功能 | 設定頁 HTML（中文與英文） | 在「運算環境」區找 `style=` 屬性 | 表格與它的格子沒有任何 inline `style` 屬性，卡片外觀全由樣式表提供 | 自動：新測試檔（執行者補斷言，註解寫 TC-032） |
