# 測試案例：web-bugs-a（網頁畫面五個缺陷 #335 #336 #337 #339 #340）

**規格**：`specs/web-bugs-a/plan.md`（本任務沒有獨立 spec.md；維護者原話是計畫「維護者原話」一節逐字引用的五個 issue）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞：「確認頁」＝`/c/<token>` 那種讓人按「確認」才會執行的頁面。「左欄」＝網頁左邊的分析清單。「更多選單」＝run 頁標題列的「更多」。`?lang=en` 代表英文版。「無中文」＝除了 run 名稱、路徑等資料值與 `<pre>` 技術摘要外，頁面文字不含中日韓字元（計畫裁決 R7）。

所有「自動」案例由 `platform/tests/test_web_bugs_a.py`（新檔）或計畫「允許改動的既有斷言」表內的既有測試檔承擔；測試內以註解寫明對應的 TC 編號。

## User Story 1 — 確認頁與其 404 的英文版（#335）（優先度 P1）

維護者原話：「英文版不得出現中文（run 名稱除外）。」標題「清理確認」與說明句「以下為將被刪除的全部內容。確認無誤後，請按「確認刪除」；按下後才會排入佇列。」在 `?lang=en` 下仍是中文；`/c/doesnotexist?lang=en` 的「找不到 (not found)／無此網址。」在英文版同樣是中文。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | #335 標題；作法 2 | 功能 | 一個已完成 run 的「清理中間檔」申請（待確認狀態），本人已登入 | 開 `/c/<rid>?lang=en` | 頁面標題是 `Confirm clean-up`；頁面不含「清理確認」 | 自動：`test_confirm_en_title_intro_button` |
| TC-002 | #335 說明句；作法 2 | 功能 | 同 TC-001 | 開 `/c/<rid>?lang=en` | 說明句是 `Everything that will be deleted is shown below. If it is correct, press "Confirm delete"; nothing is queued until you press it.`；頁面不含「以下為將被刪除」 | 自動：`test_confirm_en_title_intro_button` |
| TC-003 | #335；既有 `test_clean_page.py:94` | 功能 | 同 TC-001 | 開 `/c/<rid>?lang=en` | 有按鈕 `Confirm delete`；沒有「取消確認」 | 自動：`test_confirm_en_title_intro_button` 與 `test_clean_page.py` |
| TC-004 | #335「英文版不得出現中文」 | 功能 | 同 TC-001 | 開 `/c/<rid>?lang=en`，把 run 名稱與 `<pre>` 技術摘要拿掉 | 剩餘頁面文字無中文 | 自動：`test_confirm_en_title_intro_button` |
| TC-005 | 作法 2（launch 確認頁） | 功能 | 一個「送出新分析」的待確認申請 | 開 `/c/<rid>?lang=en` | 標題 `Confirm launch`；說明句以 `Everything that will be sent is shown below. If it is correct, press "Send"` 起首；按鈕 `Send` | 自動：`test_confirm_en_launch_and_cancel_pages` |
| TC-006 | 作法 2（cancel 確認頁） | 功能 | 一個「取消執行中分析」的待確認申請 | 開 `/c/<rid>?lang=en` | 標題 `Confirm cancel`；說明句同 TC-005 起首；按鈕 `Send` | 自動：`test_confirm_en_launch_and_cancel_pages` |
| TC-007 | #335「英文版不得出現中文」 | 功能 | 同 TC-005、TC-006 | 開兩種英文版確認頁，扣掉 run 名稱與 `<pre>` | 兩頁都無中文 | 自動：`test_confirm_en_launch_and_cancel_pages` |
| TC-008 | 作法 2（已送出狀態） | 功能 | 一個已被確認、已排入佇列的申請 | 開 `/c/<rid>?lang=en` | 內含 `Sent. Job number` 加編號；頁面無中文 | 自動：`test_confirm_en_confirmed_expired_void` |
| TC-009 | 作法 2（逾時 7 天） | 功能 | 一個「清理」申請已逾 7 天 | 開 `/c/<rid>?lang=en` | 內含 `This request has expired (7 days) and will not be raised again.`；頁面無中文 | 自動：`test_confirm_en_confirmed_expired_void`、`test_clean_page.py`（`test_the_expired_and_void_…` en 迴圈） |
| TC-010 | 作法 2（逾時 10 分鐘） | 功能 | 一個「送出／取消」申請已逾 10 分鐘 | 開 `/c/<rid>?lang=en` | 內含 `This request has expired (10 minutes). Please send it again.`；頁面無中文 | 自動：`test_confirm_en_confirmed_expired_void` |
| TC-011 | 作法 2（作廢，clean） | 功能 | 一個「清理」申請已作廢，附一個原因 | 開 `/c/<rid>?lang=en` | 內含 `This request was voided:` 加該原因；不含 `Please send it again.` | 自動：`test_confirm_en_confirmed_expired_void` |
| TC-012 | 作法 2（作廢，非 clean） | 功能 | 一個「送出／取消」申請已作廢 | 開 `/c/<rid>?lang=en` | 內含 `This request was voided:` 加原因，後面接 ` Please send it again.` | 自動：`test_confirm_en_confirmed_expired_void` |
| TC-013 | #335「英文版不得出現中文」 | 功能 | 已送出、逾時、作廢三種狀態的申請 | 各開英文版 | 三頁都無中文（作廢原因屬資料值，若本身含中文則豁免，見總覽疑問 2） | 自動：`test_confirm_en_confirmed_expired_void` |
| TC-014 | 作法 2「zh 值一字不改」 | 功能 | 同 TC-001，不帶 `lang` | 開 `/c/<rid>` | 仍含 `<h1>清理確認</h1>` 與原說明句「以下為將被刪除的全部內容。確認無誤後，請按「確認刪除」；按下後才會排入佇列。」 | 自動：`test_confirm_zh_unchanged` |
| TC-015 | 計畫允許改動表（`BASE_CONFIRM`／`BASE_EXPIRED`） | 功能 | 既有 `test_clean_page.py:158,159` 的逐位元組雜湊 | 比對修改前後 | 兩者的 `-zh` 鍵與 base 完全相同（證明中文頁一個位元組都沒變） | 自動：`test_clean_page.py`；驗收者讀 diff 比對 |
| TC-016 | 計畫允許改動表（`BASE_CONFIRM`／`BASE_EXPIRED`） | 功能 | 同 TC-015 | 比對修改前後 | 只有 `-en` 鍵被重新釘定；ledger 逐條列新舊雜湊 | 自動：`test_clean_page.py`；驗收者讀 diff 與 ledger |
| TC-017 | #335 404 原話 | 功能 | 本人已登入 | 開 `/c/doesnotexist?lang=en` | 狀態碼 404；標題 `Not found`；內文 `No such address.`；頁面無中文 | 自動：`test_confirm_404_en` |
| TC-018 | 作法 3「zh 404 維持」 | 例外 | 本人已登入 | 開 `/c/doesnotexist`（不帶 lang） | 狀態碼 404；仍是 `找不到 (not found)` 與 `無此網址。` | 自動：`test_confirm_404_en` |
| TC-019 | 作法 3（403） | 例外 | 別人建立的申請 rid；另一人已登入 | 開 `/c/<他人 rid>?lang=en` | 狀態碼 403；標題 `Not yours`；內文 `That request was not sent by you, so it cannot be viewed or acted on here.`；頁面無中文 | 自動：`test_confirm_404_en` |
| TC-020 | 作法 3（view_of 404） | 例外 | 本人已登入；rid 格式合法但不存在 | 開 `/c/<不存在的合法 rid>?lang=en` | 狀態碼 404；標題 `Not found`；內文 `No such request.`；頁面無中文 | 自動：`test_confirm_404_en` |
| TC-021 | 作法 3「zh 404 維持」；既有 `test_pending_confirm_restart.py:211` | 例外 | 同 TC-020，不帶 lang | 開 `/c/<不存在的合法 rid>` 與他人的 rid | 404 仍是 `無此申請`；403 文字與 base 相同 | 自動：`test_pending_confirm_restart.py` 與 `test_web_bugs_a.py` |
| TC-022 | 作法 3（act 路由 404） | 例外 | 本人已登入；一個不存在的 run | 用 `?lang=en` 對 act 路由（`web.py` 約 :644 處）要求該 run | 回 404，頁面為英文、無中文；不帶 lang 時維持原中文 404 | 自動：`test_web_bugs_a.py` |
| TC-023 | 作法 3（confirm_post 開頭的 404） | 例外 | 本人已登入 | 對 `/c/doesnotexist?lang=en` 送 POST | 回 404，頁面為英文、無中文；不帶 lang 時維持原中文 | 自動：`test_web_bugs_a.py` |
| TC-024 | 計畫允許改動表（`test_clean_page.py:119,125`） | 功能 | 既有 `test_the_expired_and_void_…` | 執行該測試 | zh 斷言照舊；en 改斷言英文標題與英文逾時句，並斷言 en 頁無中文；其餘既有斷言一字不改 | 自動：`test_clean_page.py` |
| TC-025 | 「不做」第 1 條（裁決 R2） | 不在範圍 | 在確認頁按下按鈕後的結果頁（已送出／未送出／表單已失效） | 以 `?lang=en` 進入並完成 POST | 結果頁維持中文，與 base 相同；沒有被悄悄翻成英文 | 自動：`test_web_bugs_a.py` |
| TC-026 | 「不做」第 2 條（裁決 R1）；#335「頁面上沒有語言切換連結」 | 不在範圍 | 任一 `/c/*` 頁 | 開 zh 與 en 各一頁 | 兩頁都沒有新增的語言切換連結 | 自動：`test_web_bugs_a.py` |
| TC-027 | 「不做」第 3 條（裁決 R7）；作法 4 | 不在範圍 | 同 TC-001，zh 與 en 各一頁 | 比對兩頁 `<pre>` 技術摘要（含動作層寫出的摘要） | `<pre>` 內容與 zh 相同、未被翻譯；run 名稱與路徑原樣 | 自動：`test_web_bugs_a.py` |

## User Story 2 — 失敗計數與「任務」分頁一致（#336）（優先度 P1）

維護者原話：「web-test-2：`71 / 75`，計數卡「失敗 4」，但分頁「任務」內容為「無失敗任務」。」「英文版 `&lang=en` 相同：`Failed 4`＋`No failed tasks`。」「失敗計數大於 0 時，「任務」分頁要列出對應任務（或明確標示這些失敗已被忽略／已重試成功）。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | #336 中文原話；作法 5 | 功能 | 已完成（succeeded）的 run，任務計數 `71 / 75`、失敗 4，沒有任何失敗任務明細 | 開 run 頁的「任務」分頁（中文） | 分頁含 `失敗計數 4，但沒有可列出的失敗任務明細；這些失敗可能已被忽略或重試成功。`；**不含**「無失敗任務」 | 自動：`test_tasks_tab_unlisted_failures_zh_en` |
| TC-031 | #336 英文原話；作法 5 | 功能 | 同 TC-030 | 開「任務」分頁（`lang=en`） | 分頁含 `The failed count is 4, but no failed task has a recorded detail; these may have been ignored or retried successfully.`；**不含** `No failed tasks` | 自動：`test_tasks_tab_unlisted_failures_zh_en` |
| TC-032 | 作法 5「計數卡不動」；#336 原話 `71 / 75`、「失敗 4」 | 功能 | 同 TC-030 | 開同一 run 頁（中文與英文） | 計數卡仍顯示 `71 / 75` 與「失敗 4」（英文 `Failed 4`），與修改前相同 | 自動：`test_tasks_tab_unlisted_failures_zh_en` |
| TC-033 | 作法 5（部分列出） | 功能 | 失敗計數 4，但只有 2 筆失敗任務明細 | 開「任務」分頁 | 表格仍在並列出那 2 筆；表格下方有一句說明，句中同時出現「列出 2」與「計數 4」兩個數字；不含「無失敗任務」 | 自動：`test_tasks_tab_partial_rows_note` |
| TC-034 | 作法 5（條件為 n > 列數） | 功能 | 失敗計數 2，失敗任務明細 2 筆 | 開「任務」分頁 | 表格列出 2 筆；沒有說明句；不含「無失敗任務」 | 自動：`test_tasks_tab_partial_rows_note` |
| TC-035 | 作法 5；空狀態（檢核 6） | 功能 | 失敗計數 0，無明細 | 開「任務」分頁（中文） | 顯示 `無失敗任務`，與修改前相同；既有 `test_web_running.py:308–309` 仍綠 | 自動：`test_tasks_tab_zero_failed_unchanged` |
| TC-036 | 作法 5；空狀態（檢核 6） | 功能 | 同 TC-035 | 開「任務」分頁（`lang=en`） | 顯示 `No failed tasks`，與修改前相同；既有 `test_web_results_outputs.py:108` 仍綠（若該測試的 world 另有失敗數大於 0，改斷言新說明句，並列入 ledger） | 自動：`test_tasks_tab_zero_failed_unchanged` |
| TC-037 | 檢核 2（讀不到就視為 0／空） | 例外 | run 資料沒有任務計數欄位，也沒有 `failed_tasks` | 開「任務」分頁 | 不是 500；視為 0，顯示 `無失敗任務` | 自動：`test_tasks_tab_zero_failed_unchanged` |
| TC-038 | 作法 5「說明句放 `<p class="muted">`，不新增 class、不用 `style=`」 | 功能 | 同 TC-030、TC-033 | 檢查「任務」分頁輸出 | 說明句在 `<p class="muted">` 內；沒有新 class；沒有 `style=` | 自動：`test_tasks_tab_unlisted_failures_zh_en` |
| TC-039 | 「不做」／裁決 R3（不嘗試判斷忽略或重試成功） | 不在範圍 | 同 TC-030 | 讀說明句 | 句子只用「可能」／`may` 的推測語氣，沒有斷言「已忽略」或「已重試成功」是事實；頁面沒有新增忽略／重試計數 | 自動：`test_tasks_tab_unlisted_failures_zh_en` |

## User Story 3 — 已完成分析的「更多」選單不再給續跑／重跑／取消（#337）（優先度 P1）

維護者原話：「已完成（「完成」）的分析，run 頁（執行中階段）標題列的「更多」選單仍提供可按的「續跑」「重跑」「取消」三個按鈕與「沿用設定重新分析」連結。」「至少「對已完成分析按取消」不應是可點的選項。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | #337；作法 6 | 功能 | 狀態為 succeeded 的 run，進入 `stage=running` | 開 run 頁，看 `<details class="menu">` 內 | 選單內沒有任何指向 `/act/` 的表單 | 自動：`test_menu_succeeded_has_no_action_forms` |
| TC-041 | #337 三個按鈕原話 | 功能 | 同 TC-040（中文） | 讀選單文字 | 不含「續跑」「重跑」「取消」 | 自動：`test_menu_succeeded_has_no_action_forms` |
| TC-042 | #337「對已完成分析按取消不應是可點的選項」 | 功能 | 同 TC-040 | 檢查整個 run 頁 | 整頁沒有任何「取消」的送出表單 | 自動：`test_menu_succeeded_has_no_action_forms` |
| TC-043 | 作法 6（quick 連結保留） | 功能 | 同 TC-040（中文） | 讀選單 | 仍有「沿用設定重新分析」連結（指向 `/launch?from=`）；選單元素仍是 `<details class="menu">`，選單只剩這一個連結 | 自動：`test_menu_succeeded_has_no_action_forms` |
| TC-044 | #337；作法 6（英文） | 功能 | 同 TC-040，`lang=en` | 讀選單 | 不含 `Resume`、`Re-run`、`Cancel`；無 `/act/` 表單 | 自動：`test_menu_succeeded_has_no_action_forms` |
| TC-045 | 作法 6（英文 quick 連結） | 功能 | 同 TC-044 | 讀選單 | 仍有指向 `/launch?from=` 的「沿用設定重新分析」英文連結 | 自動：`test_menu_succeeded_has_no_action_forms` |
| TC-046 | 作法 6；既有 `test_web_running.py:217` | 功能 | 狀態 failed 的 run | 開 run 頁選單 | 與修改前相同：續跑／重跑／取消三個表單；`test_web_running.py:217` 不改仍綠 | 自動：`test_menu_failed_lost_running_unchanged` |
| TC-047 | 作法 6 | 功能 | 狀態 lost 的 run | 開 run 頁選單 | 與修改前相同：三個表單 | 自動：`test_menu_failed_lost_running_unchanged` |
| TC-048 | 作法 6 | 功能 | 狀態 running 的 run | 開 run 頁選單 | 與修改前相同：三個表單 | 自動：`test_menu_failed_lost_running_unchanged` |
| TC-049 | 「不做」第 5 條（結果階段與其他階段的選單；`failure.actions` 驅動的全面改寫，方案 B） | 不在範圍 | succeeded 的 run 在結果階段與其他階段；以及 failed／running 的 run | 開各階段頁，與 base 比對 | 結果階段與其他階段的選單與 base 相同；沒有依 `failure.actions` 重寫其他狀態的選單；`test_web_board.py`、`test_web_resume_edit.py`、`test_web_fixes_1.py` 既有斷言不改仍綠 | 自動：既有測試全綠；驗收者讀 diff |

## User Story 4 — 未開放的階段顯示「之後開放」（#339）（優先度 P2）

維護者原話：「內容區只顯示標題加一行「— 012b」／「— 016」。這兩個是內部計畫（ticket）編號，使用者看不懂，也沒有標示「之後開放」。」「規格寫了、但尚未實作的畫面須灰掉並標「之後開放」（Coming later），不得顯示內部編號。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | #339「不得顯示內部編號」；作法 7 | 功能 | 一個 run，進入 `stage=launch`（送出階段） | 讀中間欄 | 不含 `012b`、不含 `016` | 自動：`test_stage_placeholder_launch_downstream` |
| TC-051 | #339；作法 7 | 功能 | 同一個 run，進入 `stage=downstream`（下游階段） | 讀中間欄 | 不含 `012b`、不含 `016` | 自動：`test_stage_placeholder_launch_downstream` |
| TC-052 | #339「須灰掉並標之後開放」 | 功能 | `stage=launch`（中文） | 讀中間欄 | 含 `之後開放`，且該字在 `class="later"` 的元素內 | 自動：`test_stage_placeholder_launch_downstream` |
| TC-053 | 同上 | 功能 | `stage=downstream`（中文） | 讀中間欄 | 含 `之後開放`，且在 `class="later"` 內 | 自動：`test_stage_placeholder_launch_downstream` |
| TC-054 | #339（Coming later） | 功能 | `stage=launch`，`lang=en` | 讀中間欄 | 含 `Coming later`，且在 `class="later"` 內；無中文 | 自動：`test_stage_placeholder_launch_downstream` |
| TC-055 | 同上 | 功能 | `stage=downstream`，`lang=en` | 讀中間欄 | 含 `Coming later`，且在 `class="later"` 內；無中文 | 自動：`test_stage_placeholder_launch_downstream` |
| TC-056 | #339「完成階段已正確使用灰字之後開放」；既有 `test_web_finished.py:287` | 功能 | 「完成」階段頁 | 讀頁面 | 與修改前相同；`"finished" not in PLACEHOLDER` 仍成立 | 自動：`test_web_finished.py` |
| TC-057 | 計畫「共通」禁字表；`test_tch21_stage_bodies`（`test_web_board.py:547` 一帶）改預期 | 功能 | 送出、下游階段頁的中英文 | 掃禁字表（這個、一下、還沒有、這份、弄、搞、東西、單獨的 `run` 等） | 沒有禁字；`test_tch21_stage_bodies` 改為含 `之後開放`、不含 `012b`／`016`，finished 那條不動 | 自動：`test_web_board.py`、`test_web_wording_sweep.py` |
| TC-058 | 裁決 R5（送出摘要是後續功能） | 不在範圍 | `stage=launch` | 讀中間欄 | 只有標題與灰字「之後開放」；沒有送出摘要、沒有任何會寫入的表單或按鈕 | 自動：`test_stage_placeholder_launch_downstream` |

## User Story 5 — 左欄不再以腳本檔名當專案群組標題（#340）（優先度 P2）

維護者原話：「左欄分析清單的專案群組小標題顯示為「main.nf」…web-test-1、web-test-2 都跑 `nf-core/ampliseq 2.18.0`，卻歸在「main.nf」之下。」「不應顯示腳本檔名。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | #340；作法 8 | 功能 | 一個 run 的 project 是 `main.nf` | 看左欄所有 `<h3>` 小標題 | 沒有任何小標題是 `main.nf`，整頁左欄也不出現 `main.nf` 當標題 | 自動：`test_left_group_script_name_is_no_project` |
| TC-061 | 作法 8；檢核 6 | 功能 | 同 TC-060（中文） | 看那個 run 在左欄的位置 | 在「未分專案」群組下 | 自動：`test_left_group_script_name_is_no_project` |
| TC-062 | 作法 8（英文） | 功能 | 同 TC-060，`lang=en` | 看那個 run 在左欄的位置 | 在 `No project` 群組下 | 自動：`test_left_group_script_name_is_no_project` |
| TC-063 | #340 的 web-test-1／web-test-2 例子 | 功能 | 兩個 run（web-test-1、web-test-2），project 都是 `main.nf`，都跑 `nf-core/ampliseq 2.18.0` | 看左欄 | 兩個 run 都在同一個「未分專案」群組下，沒有「main.nf」標題 | 自動：`test_left_group_script_name_is_no_project` |
| TC-064 | 作法 8（有 `/` 的名稱維持原狀）；`test_web_v2_skeleton.py:193,204,211` | 功能 | 一個 run 的 project 是 `nf-core/ampliseq`，另一個是 `nf-core/rnaseq` | 看左欄 | 各自成群，群組順序規則與修改前相同 | 自動：`test_left_group_script_name_is_no_project`、`test_web_v2_skeleton.py` |
| TC-065 | 作法 8；`test_web_board.py:383` | 功能 | run 的 project 為空（`None` 或空字串） | 看左欄 | 單一群組「未分專案」（`["未分專案"]`），預期不變且仍綠 | 自動：`test_web_board.py` |
| TC-066 | 檢核 6 | 功能 | 只有 project 為 `main.nf` 的 run | 看左欄 | 只有「未分專案」一個群組 | 自動：`test_left_group_script_name_is_no_project` |
| TC-067 | 作法 8 規則（只有「無 `/` 且結尾 `.nf`」才視為腳本檔名） | 功能 | 一個 run 的 project 含 `/` 且以 `.nf` 結尾（例如 `some/main.nf`） | 看左欄 | 該名稱維持原狀，當成自己的群組標題 | 自動：`test_left_group_script_name_is_no_project` |
| TC-068 | 檢核 6（空狀態） | 功能 | 沒有任何 run | 開首頁左欄 | 顯示「尚無分析紀錄。」，與修改前相同 | 自動：`test_web_board.py`（既有） |
| TC-069 | 「不做」第 4 條（裁決 R6：不加資料來源、不依管線名稱分組） | 不在範圍 | 同 TC-063 | 看左欄；看 diff | 這些 run **沒有**被改以 `nf-core/ampliseq` 分組（仍在「未分專案」）；`receiver.py`、`status.py`、`store.py` 沒有改動 | 自動：`test_left_group_script_name_is_no_project`；驗收者讀 diff |

## User Story 6 — 共通限制與完成標準（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 共通；頁面硬限制 | 功能 | 本片改動的各頁（確認頁各狀態、任務分頁、succeeded 選單、送出／下游階段、左欄），zh 與 en | 掃輸出 HTML | 沒有 `<script` | 自動：`test_page_constraints_after_changes` |
| TC-081 | 共通；頁面硬限制 | 功能 | 同 TC-080 | 掃輸出 HTML | 沒有 `style=` | 自動：`test_page_constraints_after_changes` |
| TC-082 | 共通；「不新增 CSS」 | 功能 | 同 TC-080 | 掃輸出 HTML | 恰好一個 `<style>`；沒有新增 class 或 CSS | 自動：`test_page_constraints_after_changes` |
| TC-083 | 共通；CSP 不變 | 功能 | 同 TC-080 | 比對回應標頭 | CSP 標頭與 base 逐字相同 | 自動：`test_page_constraints_after_changes` |
| TC-084 | 共通；「en 頁無中文」；`test_web_wording_sweep.py` | 功能 | 各階段頁與確認頁的英文版 | 跑 `test_english_pages_have_no_cjk_everywhere` 及新測試的無中文檢查 | 全綠；英文頁無中文（run 名稱除外） | 自動：`test_web_wording_sweep.py`、`test_page_constraints_after_changes` |
| TC-085 | 檢核「新字串過禁字表」 | 功能 | 本片新增的全部字串（中文） | 用 `banned_in` 掃 | 結果為空；`test_web_wording_sweep.py:250` 的 `STRINGS["zh"]["no_failed_tasks"] == "無失敗任務"` 不變仍綠 | 自動：`test_page_constraints_after_changes`、`test_web_wording_sweep.py` |
| TC-086 | 共通「新字串兩邊同鍵」 | 功能 | `web_board.STRINGS` | 比對 zh 與 en 的鍵 | 兩邊鍵集合相同（含新增的 `failed_unlisted`、`failed_partial`） | 自動：`test_page_constraints_after_changes` |
| TC-087 | 計畫允許改動表最後一列（zh 預設頁位元組不得變） | 功能 | 既有 `test_confirm_page.py:87`、`test_web_confirm_plain.py:143`、`test_pending_confirm_restart.py:211`、`test_launch_profiles.py:708`、`test_oauth_mcp.py:290` | 不改這些測試，執行 | 全部原樣仍綠 | 自動：上列既有測試檔 |
| TC-088 | 「範圍：檔案」（不動 /settings、/launch、其他路由、`_HEADERS`／CSP） | 不在範圍 | `/settings`、`/launch` 頁 | 修改前後各取一次輸出比對 | 位元組相同 | 自動：`test_web_bugs_a.py`（或既有 settings／launch 測試仍綠）；驗收者讀 `web.py` diff |
| TC-089 | 專長守則：狀態不只靠顏色 | 功能 | 「任務」分頁新說明句；送出／下游階段的灰字標示 | 讀輸出 HTML | 每處都有可讀文字（`失敗計數…`／`The failed count…`、`之後開放`／`Coming later`），不是只靠 class 或顏色 | 自動：`test_page_constraints_after_changes` |
| TC-090 | 完成標準：`git diff --stat` | 功能 | 實作完成後 | 在 worktree 跑 `git diff --stat <base>...HEAD` | 只含「範圍：檔案」所列的檔；`web.py` 的 diff 不含 `/settings`、`/launch` 相關變動 | 手動：`docs/TESTING.md`（驗收者以 diff 檢查，並與 ledger 的 diff stat 比對） |
| TC-091 | 「範圍：不碰」清單 | 不在範圍 | 實作完成後 | 看 diff | `web_launch.py`、`web_settings.py`、`status.py`、`receiver.py`、`store.py`、`mcp_server.py`、`static/*`、`DESIGN.md`、`memory/dev-queue.json`、`spec`／`test-case*.md` 都沒有被改 | 手動：`docs/TESTING.md`（讀 diff） |
| TC-092 | 計畫「允許改動的既有斷言」表 | 功能 | 實作完成後，比對被改動的既有測試檔 | 讀 diff | 被改的斷言只限該表所列；每條在 ledger 列「舊→新與理由」；沒有被放寬、跳過或刪除的其他斷言 | 手動：`docs/TESTING.md`（驗收者逐檔比對 base） |
| TC-093 | 完成標準：五處畫面 zh／en 截圖；檢核 5（手機寬度） | 功能 | 起得來的 web 應用，有 succeeded／failed 的 run | 取五處畫面（確認頁 en、任務分頁、succeeded 選單、送出／下游階段、左欄）在 1440 與 390 寬、zh 與 en 的截圖 | 版面無橫向捲動（390 寬）；中文截圖全中文、英文截圖全英文（run 名稱除外）；取不到就在 ledger 註明 | 手動：`docs/TESTING.md`（011a／011b 網頁截圖各節） |
| TC-094 | 完成標準：整套測試 | 功能 | 實作完成 | 閘門檢查 | 完成記號為 `GREEN <HEAD sha>` 且工作樹乾淨；整套 `tests/run_all.sh` 綠 | 自動：完成記號（GATE） |

## 憲法與安全網

本片只改顯示文字與選單，但碰到「確認頁是唯一確認處」（憲法 5.0.0 對原則 I.2 的修訂：送出要由本人在確認頁按下）；下列案例證明沒有放寬。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-100 | 原則 I.2／5.0.0（按鈕送出的內容不變） | 功能 | 同一個待確認申請 | 比對 zh 與 en 確認頁的 `<form>` | 表單送往的網址、隱藏欄位完全相同（只有可見文字不同）；按下仍走原本的確認流程 | 自動：`test_web_bugs_a.py` |
| TC-101 | 原則 I.2／5.0.0（別人不能代按） | 例外 | 他人的待確認申請；另一個已登入的人 | 對 `/c/<他人 rid>?lang=en` 送 POST 確認 | 被拒（403，英文頁），申請狀態沒有變成已確認，沒有排入佇列 | 自動：`test_web_bugs_a.py` |
| TC-102 | 原則 I.2／5.0.0；檢核 1（#337 只少給按鈕，不新增寫入入口） | 功能 | 修改前後的網頁路由與各頁表單 | 比對 | 沒有新增任何會寫入的路由或表單；succeeded 的 run 頁寫入表單只減不增 | 自動：`test_menu_succeeded_has_no_action_forms`；驗收者讀 diff |
| TC-103 | 原則 I.2 的檢查（未經確認的送出，網頁路由也拒絕） | 功能 | 既有網頁確認與 act 測試 | 不改動，執行 `test_confirm_page.py`、`test_web_actions.py` 等 | 全部原樣仍綠 | 自動：既有測試檔 |
