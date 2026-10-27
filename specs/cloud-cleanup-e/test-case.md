# 測試案例：確認頁與看板提示的文字（cloud-cleanup-e，刪除不再顯示成「取消」）

**規格**：`specs/cloud-cleanup-e/plan.md`（本片沒有另寫 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「清理申請」＝種類為 `clean_work` 的申請（代理要刪某個 run 的中間檔資料夾 work，結果不動）；「確認頁」＝`/c/<申請編號>`；「看板」＝登入後的 run 清單與單一 run 頁；「本人」＝申請上記的那位登入者。本片之前沒有任何程式會建清理申請，測試一律用 `confirm.create_pending` 直接建。

**維護者原話與 TC 對照**（計畫「維護者原話」逐字引文）：

| 維護者原話 | 對應 TC |
|---|---|
| 「跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪」：①本人按才排進佇列 | TC-019、TC-022、TC-024～TC-028 |
| 同上：②頁面與通知都寫明刪的是中間檔、結果不動 | TC-004、TC-020、TC-038、TC-040 |
| 同上：③看板通知只是連結，不會自己刪 | TC-042、TC-044、TC-045 |
| 「C-7 …… `web_board.py` 通知」：通知放在看板、只對 succeeded 的 run 出現 | TC-038、TC-046～TC-048 |
| 「網頁畫面仍等他回好／不好」 | TC-078、TC-079 |
| 「每個寫入要本人答應」（憲法 6／ADR 0006）：確認頁 POST 沿用同源、登入、同一使用者、CSRF，不加新寫入路徑 | TC-017、TC-018、TC-024～TC-028、TC-063、TC-071 |
| 「平台不啟動程式（TC-071）；不含 TC-061 禁用字、不拆字拼接」 | TC-068、TC-069 |

## User Story 1 — 確認頁認得「清理確認」，不再顯示成「取消確認」（優先度 P1）

前置通用：登入者 A 有一張未逾時、待按的清理申請，run 名稱 R、要刪的資料夾 W。除非另寫，打開的是 `/c/<申請編號>`（中文）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標①；作法1 標題列 | 功能 | A 的清理申請待按 | A 打開確認頁 | 頁面標題是「清理確認」；頁面任何地方都沒有「取消確認」或「送出確認」 | 自動：`test_clean_page.py::test_a_pending_clean_request_page_says_clean_not_cancel_and_has_the_confirm_delete_button` |
| TC-002 | 作法1 待按引言 | 功能 | 同上 | A 打開確認頁 | 引言是「下面就是會被刪除的全部內容。確定了再按「確認刪除」；按了才會排進佇列。」，且不含「會被送出」「會被取消」 | 自動：同上 |
| TC-003 | 作法1 按鈕 | 功能 | 同上 | A 打開確認頁 | 頁面上送出表單的按鈕文字是「確認刪除」，不是「送出」 | 自動：同上 |
| TC-004 | 目標①；作法1 白話區塊 | 功能 | 同上 | A 打開確認頁 | 最上方白話區塊有三列：「種類：清理中間檔」「run 名稱：R」「要刪除的資料夾：W」 | 自動：`test_the_plain_block_shows_kind_run_name_and_the_folder_to_delete_and_nothing_else` |
| TC-005 | 作法1；既有規則「不知道的欄位不顯示破折號」 | 功能 | 同上 | A 打開確認頁 | 白話區塊只有上述三列：沒有「管線」「版本」「環境」「樣本數」「新資料夾」列，也沒有破折號「—」或「-」充當值 | 自動：同上 |
| TC-006 | 作法1 en 版 | 功能 | 同上 | A 用 `?lang=en` 打開確認頁 | 白話區塊是「Request：Clean up intermediate files」「Run name：R」「Folder to delete：W」 | 自動：`test_a_pending_clean_request_page_says_clean_not_cancel_and_has_the_confirm_delete_button`（en 部分） |
| TC-007 | 作法1 en 版按鈕 | 功能 | 同上 | A 用 `?lang=en` 打開確認頁 | 送出表單的按鈕文字是「Confirm delete」 | 自動：同上 |
| TC-008 | 目標；作法1「最需要避免的錯誤」 | 功能 | 同上 | A 用 `?lang=en` 打開確認頁 | 頁面任何地方都沒有「取消確認」 | 自動：同上 |
| TC-009 | 作法1 逾時列 | 功能 | 清理申請建立後時鐘撥過 7 天 | A 打開確認頁 | 顯示「這個申請已逾時（7 天），不會自動重新提出。」；沒有「10 分鐘」，沒有「回到 AI」；標題仍是「清理確認」 | 自動：`test_the_expired_and_void_pages_for_clean_work_say_seven_days_and_do_not_say_send_it_again_from_the_ai` |
| TC-010 | 作法1 作廢列 | 功能 | 清理申請已被作廢（原因 X） | A 打開確認頁 | 顯示「這個申請已作廢：X。」；沒有「回到 AI」「重新送出」；標題是「清理確認」 | 自動：同上 |
| TC-011 | 作法1 標題列（已送出狀態） | 功能 | 清理申請已被 A 按過、已排出工作 N | A 打開確認頁 | 標題是「清理確認」，顯示「已送出。工作編號 N。」，沒有「取消確認」 | 自動：`test_clean_page.py` |
| TC-012 | 作法2「GET 不改任何東西」 | 功能 | 清理申請待按；記下 confirmations 與 jobs 兩個表的全部內容 | A 打開確認頁（中、英各一次） | 打開前後 confirmations 與 jobs 全表內容完全相同（沒有新增工作、申請仍待按） | 自動：`test_get_changes_nothing_for_a_clean_request` |
| TC-013 | 作法1「launch、cancel 逐字不變」 | 功能 | 一張待按的 launch 申請、一張待按的 cancel 申請（中、英各打開） | 打開兩張確認頁 | 四份 HTML（launch／cancel × 中／英）與本片動手前（base v3）記錄下來的字串逐字相同：標題「送出確認」／「取消確認」、按鈕「送出」、引言動詞不變 | 自動：`test_launch_and_cancel_pages_are_byte_for_byte_what_they_were` |
| TC-014 | 同上 | 功能 | launch 與 cancel 申請各一張，已逾時 | 打開確認頁（中、英） | 與 base 記錄逐字相同，仍寫「10 分鐘」「請回到 AI 重新送出」 | 自動：同上 |
| TC-015 | 同上 | 功能 | launch 與 cancel 申請各一張，已作廢 | 打開確認頁（中、英） | 與 base 記錄逐字相同，仍寫「請回到 AI 重新送出」 | 自動：同上 |
| TC-016 | 同上 | 功能 | launch 與 cancel 申請各一張，已送出 | 打開確認頁（中、英） | 與 base 記錄逐字相同 | 自動：同上 |
| TC-017 | 作法2；原話「每個寫入要本人答應」（讀） | 例外 | 清理申請屬於 A；另一位登入者 B | B 打開 A 的確認頁 | 回 403，只說這個申請不是你送出的；頁面沒有 W、R，沒有任何按鈕 | 自動：`test_only_the_person_who_has_the_request_can_see_and_press_it` |
| TC-018 | 作法2（讀） | 例外 | 同一張申請；沒有登入 | 未登入者打開確認頁 | 顯示登入頁（網址導回此確認頁），不顯示申請內容 | 自動：同上 |

## User Story 2 — 按下「確認刪除」之後（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 原話①；作法2 | 功能 | A 的清理申請待按 | A 在確認頁帶正確 CSRF 按送出 | 申請變成已送出，jobs 表恰好多一筆 kind 為 `clean_work` 的工作，且關聯到這張申請 | 自動：`test_pressing_once_queues_exactly_one_clean_work_job_and_twice_says_already` |
| TC-020 | 作法1 成功頁 | 功能 | 同 TC-019 | 看按下後的回應頁 | 寫著「已送出。工作編號 N。代理會開始清理這個 run 的中間檔；結果不會被動。」（N 為 TC-019 那筆工作的編號） | 自動：同上 |
| TC-021 | 作法1「清理申請不是 AI 發起的」 | 功能 | 同 TC-019 | 看按下後的回應頁 | 頁面不含「回到 AI」「再呼叫一次」 | 自動：`test_the_pages_after_pressing_never_tell_a_clean_request_to_go_back_to_the_ai` |
| TC-022 | 作法1 already 頁 | 功能 | A 已按過一次 | A 再按一次（正確 CSRF） | jobs 表中該申請的 `clean_work` 工作仍只有一筆 | 自動：`test_pressing_once_queues_exactly_one_clean_work_job_and_twice_says_already` |
| TC-023 | 作法1 already 頁（兩種通用，不改） | 功能 | 同上 | 看第二次按下的回應頁 | 寫著「已送出。工作編號 N。」，N 與第一次相同 | 自動：同上 |
| TC-024 | 原話「每個寫入要本人答應」；作法2 CSRF | 例外 | A 的清理申請待按 | A 送出表單但 CSRF 記號是錯的 | 回 403「表單已失效」類頁面；jobs 沒有新增工作；申請仍待按 | 自動：`test_pressing_with_a_wrong_or_missing_csrf_queues_nothing` |
| TC-025 | 同上 | 例外 | 同上 | A 送出表單但完全沒帶 CSRF | 同 TC-024：被拒、沒排任何工作、申請仍待按 | 自動：同上 |
| TC-026 | 原話「本人」；作法2（寫） | 例外 | 清理申請屬於 A；另一位登入者 B | B 對 A 的申請送出表單（即使 CSRF 對 B 自己是有效的） | 回 403；jobs 沒有新增工作；申請仍待按 | 自動：`test_only_the_person_who_has_the_request_can_see_and_press_it` |
| TC-027 | 作法2（寫，未登入） | 例外 | 沒有登入 | 未登入者對該申請送出表單 | 顯示登入頁（401）；沒排任何工作；申請仍待按 | 自動：同上 |
| TC-028 | 作法2 同源檢查 | 例外 | A 已登入 | A 的瀏覽器從別的網站（Origin 不同源）對該申請送出表單 | 被拒絕；沒排任何工作；申請仍待按 | 自動：`test_clean_page.py` |
| TC-029 | 作法1 逾時；`test_pressing_after_seven_days_queues_nothing` | 例外 | 清理申請建立後時鐘撥過 7 天 | A 帶正確 CSRF 按送出 | 回 410；jobs 沒有新增工作 | 自動：`test_pressing_after_seven_days_queues_nothing` |
| TC-030 | 作法1 失敗頁 | 例外 | 同 TC-029 | 看按下後的回應頁 | 寫著「未送出：<原因>。」，不含「回到 AI」「重新送出」 | 自動：`test_the_pages_after_pressing_never_tell_a_clean_request_to_go_back_to_the_ai` |
| TC-031 | 作法1 失敗頁（其他失敗） | 例外 | 清理申請已作廢（原因 X），A 仍持有舊頁面 | A 按送出 | 回 409；寫著「未送出：…」並含原因；不含「回到 AI」「重新送出」；沒排工作 | 自動：同上 |
| TC-032 | 作法1 失敗頁（找不到） | 例外 | 一個不存在的申請編號 | 登入者 A 對它送出表單 | 回 404；頁面不含「回到 AI」 | 自動：同上 |
| TC-033 | 作法1 失敗頁（不是你的） | 例外 | 清理申請屬於 A，B 登入 | B 對它送出表單 | 回 403；頁面不含「回到 AI」 | 自動：同上 |
| TC-034 | 作法1「launch、cancel 的字一個都不動」 | 功能 | 一張待按的 launch 申請 | 本人按送出 | 成功頁與 base 逐字相同：「已送出。工作編號 N。你可以回到 AI，用同樣的參數再呼叫一次，它會告訴你工作編號。」 | 自動：`test_the_pages_after_pressing_a_launch_or_a_cancel_are_unchanged` |
| TC-035 | 同上 | 功能 | 一張待按的 cancel 申請 | 本人按送出 | 成功頁與 base 逐字相同 | 自動：同上 |
| TC-036 | 同上 | 功能 | 一張已逾時的 launch 申請 | 本人按送出 | 失敗頁與 base 逐字相同：「未送出：…。請回到 AI 重新送出。」，狀態碼與 base 相同 | 自動：同上 |
| TC-037 | 同上 | 功能 | 一張已逾時的 cancel 申請 | 本人按送出 | 失敗頁與 base 逐字相同，狀態碼與 base 相同 | 自動：同上 |

## User Story 3 — 看板右側的「可以清掉中間檔」待處理通知（優先度 P1）

前置通用：A 有一個狀態為 `succeeded` 的 run R，且 A 自己有一張針對 R 的、未逾時、待按的清理申請（編號 rid）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | 目標②；作法3；原話 C-7 | 功能 | 通用前置 | A 打開 R 的 run 頁（中文） | 右欄恰好出現 1 張這個通知卡片（不是 0、不是 2 張） | 自動：`test_a_succeeded_run_with_my_open_clean_request_shows_one_notice_with_a_link_to_the_confirmation_page` |
| TC-039 | 作法3 等級標籤；專長守則「符號＋文字」 | 功能 | 通用前置 | 同上 | 卡片的等級標籤文字是「待處理」，且與既有失敗通知同款結構（有色塊符號＋文字，不只靠 class 顏色） | 自動：同上 |
| TC-040 | 作法3「內容」；原話②結果不動 | 功能 | 通用前置 | 同上 | 「內容」欄是「這個 run 已成功；它的中間檔（work）可以清掉，結果不會被動。」 | 自動：同上 |
| TC-041 | 作法3「下一步」 | 功能 | 通用前置 | 同上 | 「下一步」欄是「打開確認頁，看清楚要刪的資料夾再決定。」；卡片沒有時間欄 | 自動：同上 |
| TC-042 | 作法3 連結 | 功能 | 通用前置 | 同上 | 卡片裡的連結網址恰好是 `/c/<rid>`（中文時不帶 lang 參數）；連結裡沒有 CSRF 記號 | 自動：同上 |
| TC-043 | 作法3 en 版 | 功能 | 通用前置 | A 用 `?lang=en` 打開 R 的 run 頁 | 右欄恰好 1 張通知卡片，連結恰好是 `/c/<rid>?lang=en` | 自動：同上（en 部分） |
| TC-044 | 作法3「不是表單、不是按鈕」；原話③ | 功能 | 通用前置 | A 打開 R 的 run 頁，取出通知卡片的 HTML | 卡片裡沒有 form、button、input；只有一個連結 | 自動：`test_the_notice_is_a_link_not_a_form_and_has_no_button` |
| TC-045 | 原話③「通知不會自己刪」；作法2 | 功能 | 通用前置；記下 confirmations 與 jobs 全表 | A 打開 R 的 run 頁（中、英各一次） | 前後兩表內容完全相同：申請仍待按、沒有任何新工作 | 自動：`test_clean_page.py` |
| TC-046 | 原話 C-7「只對 succeeded」 | 例外 | A 的 run R 狀態是 `failed`，A 有針對 R 的待按清理申請 | A 打開 R 的 run 頁 | 沒有「可以清掉中間檔」通知卡片（失敗 run 仍只有原本的失敗通知） | 自動：`test_no_notice_for_a_failed_a_running_or_a_lost_run_even_with_an_open_request` |
| TC-047 | 同上 | 例外 | R 狀態是 `running`，同樣有待按清理申請 | A 打開 R 的 run 頁 | 沒有該通知卡片 | 自動：同上 |
| TC-048 | 同上 | 例外 | R 狀態是 `lost`，同樣有待按清理申請 | A 打開 R 的 run 頁 | 沒有該通知卡片 | 自動：同上 |
| TC-049 | 作法3「別人的申請」 | 例外 | A 的 succeeded run R 沒有 A 自己的清理申請；B 有一張針對同名 run 的待按清理申請 | A 打開 R 的 run 頁 | 沒有通知卡片 | 自動：`test_no_notice_for_another_users_request_or_run` |
| TC-050 | 作法3「別人的 run」 | 例外 | B 的 succeeded run R_B 與 B 的待按清理申請；A 登入 | A 嘗試打開 R_B 的 run 頁 | 與既有行為相同（找不到，404），頁面不含通知卡片，也不洩漏 R_B 的名稱或 rid | 自動：同上 |
| TC-051 | 作法3 以 run 名稱對應 | 例外 | A 有 succeeded 的 run R1 與 R2；A 只有一張針對 R2 的待按清理申請 | A 打開 R1 的 run 頁 | R1 頁沒有通知卡片；（對照）打開 R2 才有 | 自動：`test_clean_page.py` |
| TC-052 | 作法3「已被按過的申請」 | 例外 | 通用前置，但 A 已在確認頁按過送出 | A 打開 R 的 run 頁 | 沒有通知卡片 | 自動：`test_no_notice_after_the_request_is_pressed_expired_void_or_forgotten` |
| TC-053 | 作法3「逾時的申請」 | 例外 | 通用前置，時鐘撥過 7 天 | A 打開 R 的 run 頁 | 沒有通知卡片 | 自動：同上 |
| TC-054 | 作法3 | 例外 | 通用前置，但申請已作廢 | A 打開 R 的 run 頁 | 沒有通知卡片 | 自動：同上 |
| TC-055 | 作法3 | 例外 | 通用前置，但申請內容已被本人刪除（forgotten） | A 打開 R 的 run 頁 | 沒有通知卡片 | 自動：同上 |
| TC-056 | 目標「沒有申請時的看板位元級不變」 | 功能 | succeeded 的 run，A 沒有任何清理申請 | A 打開該 run 頁（頁面與右欄） | HTML 與 base 記錄逐字相同（右欄仍顯示原本「沒有通知」那行） | 自動：`test_a_board_without_any_clean_request_is_byte_for_byte_what_it_was` |
| TC-057 | 同上 | 功能 | failed 的 run，沒有清理申請 | A 打開該 run 頁 | HTML 與 base 記錄逐字相同 | 自動：同上 |
| TC-058 | 同上 | 功能 | running 的 run，沒有清理申請 | A 打開該 run 頁 | HTML 與 base 記錄逐字相同 | 自動：同上 |

## User Story 4 — 唯讀函式與計畫「不做」的事（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-059 | 範圍：`actions.clean_requests` | 功能 | A 有兩張待按清理申請（針對 R1、R2） | 以 A 為 caller 呼叫 `actions.clean_requests` | 回 `{R1: 申請編號, R2: 申請編號}`，恰好這兩筆 | 自動：`test_clean_requests_is_a_read_that_filters_by_caller_and_is_not_a_tool_or_a_route` |
| TC-060 | 專長守則 backend「擁有者規則在動作層」 | 例外 | 只有 A 有清理申請 | 以 B 為 caller 呼叫 `actions.clean_requests` | 回 `{}` | 自動：同上 |
| TC-061 | 範圍：`caller` 為 `None` 回 `{}` | 例外 | A 有清理申請 | 以 `caller=None` 呼叫 | 回 `{}` | 自動：同上 |
| TC-062 | 不做「不新增 MCP 工具」 | 不在範圍 | 平台已啟動 | 列出 MCP 工具；檢查 `clean_requests` 不是工具、名稱不以 `request_` 開頭 | 工具仍恰好 12 個，沒有新增 | 自動：同上；並由既有 `test_pat.py`／`test_oauth_mcp.py` 的 `len(tools) == 12` 守住 |
| TC-063 | 不做「不新增網頁路由」 | 不在範圍 | 取得 `web.py` 的路由清單 | 與本片之前（base）的路由清單比對 | 兩份完全相同，沒有新增路徑 | 自動：同上 |
| TC-064 | 不做「不建立任何申請」 | 不在範圍 | 沒有任何清理申請 | 登入、打開看板各個 run 頁、打開不存在申請的確認頁 | confirmations 表中 kind 為 `clean_work` 的筆數仍是 0；jobs 沒有 `clean_work` | 自動：`test_clean_page.py` |
| TC-065 | 不做「再次提出的入口」 | 不在範圍 | 清理申請已逾時 | A 打開確認頁（中、英） | 頁面沒有表單、按鈕或任何「再提出／重新申請」連結 | 自動：`test_the_expired_and_void_pages_for_clean_work_say_seven_days_and_do_not_say_send_it_again_from_the_ai` |
| TC-066 | 不做「費用／儲存月費顯示」「30 天到期提醒」 | 不在範圍 | 通用前置 | 取得清理確認頁（待按）與通知卡片的文字 | 不含任何費用、儲存月費、「30 天」到期提醒的字句 | 自動：`test_clean_page.py` |
| TC-067 | 不做「不改樣式表」 | 不在範圍 | 取得看板的樣式表 | 與 base 比對 | 樣式表內容逐字相同（通知沿用既有 `.notice`、`.state-succeeded`） | 自動：`test_clean_page.py` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-068 | 平台不啟動程式（TC-071） | 功能 | 本片改過的 `web.py`、`web_board.py`、`actions/__init__.py` | 跑既有 TC-071 掃描 | 通過；新字串沒有啟動程式的寫法 | 自動：`test_scope.py` TC-071；並由 `test_the_web_sources_have_no_program_start_and_not_the_forbidden_word` 確認新字串沒拆字拼接 |
| TC-069 | 平台原始碼不含禁用字（TC-061） | 功能 | 同上 | 跑既有 TC-061 掃描 | 通過；平台程式碼一律寫「代理／agent」，沒有禁用的那個英文字，也沒有拆字拼接 | 自動：`test_scope.py` TC-061；`test_the_web_sources_have_no_program_start_and_not_the_forbidden_word` |
| TC-070 | 新測試檔登記（TC-070） | 功能 | 新檔 `platform/tests/test_clean_page.py` | 檢查檔案前 40 行 | 含 `# Nothing existing: …` 這一行 | 自動：`test_scope.py` TC-070 |
| TC-071 | 每個寫入要本人答應（ADR 0006） | 功能 | 資料庫快照（所有表） | 呼叫 `actions.clean_requests` 多次（有申請、無申請、caller 為 None） | 呼叫前後所有表內容完全相同（純讀取） | 自動：`test_clean_requests_is_a_read_that_filters_by_caller_and_is_not_a_tool_or_a_route` |
| TC-072 | 專長守則 ui：不得 inline style、不載外部資源 | 功能 | 清理確認頁（待按／已送出／逾時／作廢）與含通知的看板 | 取得各頁 HTML | 沒有 `style=` 屬性；沒有指向外部網址的 src／href（除了站內 `/c/<rid>` 連結） | 自動：`test_clean_page.py` |
| TC-073 | 專長守則 ui：CSP 等標頭 | 功能 | 同上 | 取得各頁回應標頭 | 與既有 launch 確認頁一樣帶 Content-Security-Policy、X-Frame-Options、Cache-Control: no-store 等標頭，內容相同 | 自動：`test_clean_page.py` |
| TC-074 | 專長守則 backend：對等性 | 功能 | 既有 `test_actions_layer.py`（未修改） | 執行該檔 | 通過；新增的 `actions.clean_requests` 不觸發任何掃描 | 自動：`platform/tests/test_actions_layer.py` |
| TC-075 | 專長守則 backend：錯誤訊息與洩漏 | 例外 | TC-029、TC-031、TC-032、TC-033 的失敗頁 | 檢查回應文字 | 說明發生什麼事（未送出＋原因）；不含堆疊追蹤、SQL、伺服器內部路徑、CSRF 值、session 值 | 自動：`test_clean_page.py` |
| TC-076 | 範圍：只准改指定檔案 | 功能 | 實作完成 | `git diff --name-only <base>...HEAD` | 只有 `web.py`、`web_board.py`、`actions/__init__.py`、`test_clean_page.py`、`specs/cloud-cleanup-e/ledger.md` 這 5 個；沒有碰 `confirm.py`、`jobs.py`、`store.py`、`build.py`、`receiver.py`、`cli.py`、`mcp_server.py`、`guidance.py`、`chat_tools.py`、`abf_station/*` | 手動：閱卷者依計畫「完成標準」核對 diff（本片無 docs，見總覽疑問 3） |
| TC-077 | 範圍：既有測試不准改 | 功能 | 實作完成 | `git diff --stat <base>...HEAD -- platform/tests` | 只有新檔 `test_clean_page.py`；`test_confirm_page.py`、`test_web_board.py`、`test_web_v2_skeleton.py`、`test_web_running.py`、`test_web_actions.py`、`test_actions_layer.py`、`test_pat.py`、`test_oauth_mcp.py` 零差異；ledger 貼有 `git diff --stat` | 手動：閱卷者核對並重跑這些檔 |
| TC-078 | 原話「網頁畫面仍等他回好／不好」 | 功能 | verifier 通過、CI 綠 | 檢查 ledger 與交付物 | 附有確認頁（待按，中、英各一）與看板通知（中、英各一）的截圖，已列進每日清單；維護者回「好」之前不合併 | 手動：計畫「完成標準」手動項（ledger 記載） |
| TC-079 | 完成標準·手動 | 功能 | 本機看板；以 `confirm.create_pending` 手工建一張清理申請（只看畫面，不按送出） | 維護者開確認頁與一個成功 run、一個失敗 run 的看板 | 確認頁標題、字句、按鈕、白話區塊都對；成功 run 右欄出現卡片、點連結進得了確認頁；失敗 run 沒有卡片 | 手動：計畫「完成標準」手動項（ledger 記載） |
| TC-080 | 專長守則 ui：偵測器 | 功能 | 把清理確認頁各狀態與含通知的看板渲染成 HTML 檔 | 閱卷者跑 Impeccable 偵測器（唯讀） | 無違反 DESIGN.md 的 tokens／畫面／狀態；偵測器其他發現交維護者看 | 手動：閱卷者渲染並執行 |
| TC-081 | 完成標準；專長守則「不猜設計」 | 功能 | 實作完成 | 閱讀 ledger | 寫明手工建清理申請的方法（並註明不要按送出）、`git diff --stat`；DESIGN.md 沒決定的事列在「要問的問題」，沒有自創顏色、字型、間距 | 手動：閱卷者閱讀 ledger 與 diff |
