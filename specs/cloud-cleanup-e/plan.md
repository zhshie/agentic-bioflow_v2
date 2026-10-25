---
id: cloud-cleanup-e
title: 確認頁認得「清理確認」（不再把它顯示成「取消確認」）與看板右側的「可以清掉中間檔」待處理通知
tier: B
kinds: ui, backend
lane: L-cleanup
after: cloud-cleanup-b
base: v3
---

# cloud-cleanup-e

> 本檔由 developer-agent 起草（2026-10-24），`cloud-cleanup.md` 切成六片之第五片（a 資料庫 → b 平台記帳 → c 代理刪 Slurm 的 work → d 代理刪 Google Batch 的 work → **e 確認頁與看板通知** → f 成功後提出申請＋文件）。**本片只動網頁畫面**：確認頁對 `clean_work` 顯示正確的標題、動詞、按鈕與逾時文字，看板的 run 頁右側在該 run 有一張未逾時的清理申請時多一則通知。此刻沒有任何程式會建立 `clean_work` 申請（f 片才建），所以使用者在正式環境看不到變化；f 片 `after` 本片，確保「有申請」之前「畫面」已經就位（否則 `web.py` 會把清理申請顯示成「取消確認」，一個按下去其實是刪除的按鈕上寫著取消，這是本計畫最需要避免的錯誤）。
> **派工前提**：`cloud-cleanup-b` 已合併（`confirm.facts` 已回 `clean_work`、`confirm.open_clean_requests` 已存在）。**派工前 developer-agent 先通知前端 session**（`web.py`、`web_board.py` 的擁有者），告知本片只動這兩個檔的指定位置（見範圍），並請它在本片合併前不要同時大改這些函式；本片含網頁畫面的新文字，**等維護者回「好／不好」才合併**，不屬 B 級自合範圍。
> **名詞**：「確認頁」＝`/c/<申請編號>`，本人看過摘要後按送出的那頁；「看板」＝登入後的 run 清單與單一 run 頁。平台程式碼（`abf_platform/`、`abf_launch/`）裡一律寫「代理／agent」，不得出現 TC-061 禁用的那個英文字（`test_scope.py:189`）。

## 目標
①確認頁：`clean_work` 的申請顯示「清理確認」、說明會被刪除的是什麼、按鈕寫「確認刪除」、逾時寫「7 天」，並在最上方的白話區塊顯示「種類：清理中間檔／run 名稱／要刪除的資料夾」。②看板：一個 `succeeded` 的 run，若登入者自己有一張未逾時的清理申請，右側「待處理」多一張卡片：「這個 run 已成功；可以清掉中間檔」，附連到確認頁的連結（連結本身只是 GET，不改任何東西）。launch／cancel 的頁面與沒有申請時的看板**位元級不變**。對使用者的意義：他在按下會刪東西的按鈕之前，看到的字是對的。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md` 與 `CLAUDE.md`；每句至少對應一條測試案例：
- 「**跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪**」（裁示 16，第 58 行）→ ①確認頁上必須是本人按（同一個登入者、CSRF 記號、同一個申請）才排進佇列②頁面與通知都寫明刪的是中間檔、結果不動③看板通知只是連結，不會自己刪。
- 「**C-7 `cloud-cleanup`**（B／backend）：succeeded 後建「刪除 work 目錄」的待確認請求（走 `_ask`，新 kind `clean_work`；對 nano4 也適用）…… files：`confirm.py`、`jobs.py`、`actions/__init__.py`、`web_board.py` 通知、`test_cleanup.py`」（第 171 行）→ 看板通知放在 `web_board.py`；通知只對 `succeeded` 的 run 出現。
- 「網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併，事後列進每日清單；網頁畫面仍等他回好／不好」（裁示 14，第 54 行）→ **本片是網頁畫面：verifier 通過＋CI 綠之後，附確認頁與看板通知的截圖（zh、en 各一）請維護者回好／不好，才合併**。
- 「每個寫入要本人答應」（憲法 6／ADR 0006，引自 `017d-launch-composed.md` 第 26 行）→ 確認頁的 POST 沿用既有檢查（同源、登入、同一個使用者、CSRF），不加任何新的寫入路徑。
- 憲法：平台不啟動程式（TC-071）；平台原始碼不含 TC-061 禁用字、不拆字拼接。

## 範圍：檔案（只准改這些，共 5 個含 ledger）
- `platform/abf_platform/web.py`：
  - `_PLAIN`（:71-76）zh／en 各加 `clean_work`（種類名）與 `work`（欄位標籤）兩個鍵；`plain_block`（:288-300）的欄位清單加 `("work", "work")`。
  - `state_page`（:302-316）與 `confirm_post`（:328-351）的成功／失敗頁：標題、動詞、按鈕、逾時與送出後文字依 `req["kind"]` 三分（見作法 1）；`launch`、`cancel` 的字一個都不動。
  - `board_page`（:~370-382）取資料處：呼叫新的 `actions.clean_requests` 並把結果放進被選 run（見作法 3）。
- `platform/abf_platform/web_board.py`：新增 `_clean_notice(t, run)`；`_right`（:664-671）在被選 run 為 `succeeded` 且有 `clean_request` 時多放這張卡；`t` 字典 zh（:52 附近）與 en（:96 附近）各加三個字串；CSS 沿用既有 `.notice`、`.state-succeeded`（:172、:202），**不新增樣式**。
- `platform/abf_platform/actions/__init__.py`：新增唯讀函式 `clean_requests(platform_path, *, caller, clock=time.time)` → `{run_name: 申請編號}`（只呼叫 `confirm.open_clean_requests`，caller 的 `user_id` 傳進去；`caller` 為 `None` 回 `{}`）。**不是 MCP 工具、不是 `request_*`、不加路由**。
- `platform/tests/test_clean_page.py`（新；檔首 `# Nothing existing: …`，TC-070；以 `platform/tests/test_confirm_page.py` 的夾具為樣板，申請用 `confirm.create_pending` 直接建（f 片之前沒有別的建法））。
- `specs/cloud-cleanup-e/ledger.md`。

**禁碰**：`confirm.py`、`jobs.py`、`store.py`（a、b 已完成）、`build.py`、`receiver.py`、`cli.py`（兩個都不碰）、`mcp_server.py`、`guidance.py`、`actions/chat_tools.py`、`abf_station/*`、既有 web 測試檔（`test_confirm_page.py`、`test_web_board.py`、`test_web_v2_skeleton.py`、`test_web_running.py`、`test_web_actions.py` 一個斷言都不准改——若有紅，代表 launch／cancel 的頁面被動到了，先停手回報）、`test_actions_layer.py`、`test_pat.py`／`test_oauth_mcp.py` 的 `len(tools) == 12`。

## 作法
1. **確認頁文字（`state_page`；以下是提議，等維護者回好／不好）**：

   | 項目 | `launch`（不變） | `cancel`（不變） | `clean_work`（新） |
   |---|---|---|---|
   | 標題 | 送出確認 | 取消確認 | 清理確認 |
   | 待按時的引言 | 下面就是會被送出的全部內容。確定了再按「送出」；按了才會排進佇列。 | （同左，動詞「取消」） | 下面就是會被刪除的全部內容。確定了再按「確認刪除」；按了才會排進佇列。 |
   | 按鈕 | 送出 | 送出 | 確認刪除 |
   | 逾時 | 這個申請已逾時（10 分鐘）。請回到 AI 重新送出。 | （同左） | 這個申請已逾時（7 天），不會自動重新提出。 |
   | 作廢 | …請回到 AI 重新送出。 | （同左） | 這個申請已作廢：<原因>。 |
   | 白話區塊「種類」 | 送出新分析 | 取消 | 清理中間檔 |
   | 新欄位 | — | — | 要刪除的資料夾：<work 路徑> |

   en 版同義（種類 `Clean up intermediate files`、欄位 `Folder to delete`、按鈕 `Confirm delete`）。**現有程式用 `req["kind"] == "launch"` 二分（:303、:311），不改就會把 `clean_work` 顯示成「取消確認」**；改成對照表（kind → 一組字），`launch`、`cancel` 的輸出逐字不變。
   **按下送出之後的頁面（`confirm_post`）也寫死了「回到 AI」**：成功頁（:351）說「你可以回到 AI，用同樣的參數再呼叫一次，它會告訴你工作編號」、失敗頁（:349）說「請回到 AI 重新送出」。清理申請不是 AI 發起的，這兩句對它是錯的，所以 `clean_work` 用自己的字：成功「已送出。工作編號 N。代理會開始清理這個 run 的中間檔；結果不會被動。」失敗「未送出：<原因>。」（不叫人回到 AI）。`confirm_post` 已有 `answer, req = view_of(rid, user)`（:340 之前），`req["kind"]` 現成可用。「已送出。工作編號 N。」的 `already` 頁（:348）兩種通用，不改。（:565 的 `consent_gone` 是連接器授權頁，與本計畫無關，不動。）
2. **確認頁的安全規則不動**：`view_of`（:279）的「不是你的申請 → 403」、`confirm_post`（:328）的同源檢查、登入、`csrf(sid, rid)`、`actions.approve(..., confirmed_by=actions.PAGE, ...)` 全部不改；`clean_work` 的 `GET` 不改任何東西。
3. **看板通知**：`board_page`（:~370）在 `selected` 取得之後，若 `selected["status"] == "succeeded"`，呼叫 `actions.clean_requests(platform_path, caller=caller)`（放在 `run_in_threadpool`，與 `read_run` 同樣的寫法），把 `.get(selected["name"])` 放進 `selected["clean_request"]`（沒有就不放這個鍵）。`web_board._clean_notice` 只在該鍵存在時回一張卡片，內容：等級標籤沿用 `t["level_action"]`（「待處理」）、時間欄略、兩行欄位——「內容：這個 run 已成功；它的中間檔（work）可以清掉，結果不會被動。」「下一步：打開確認頁，看清楚要刪的資料夾再決定。」——一個連到 `/c/<申請編號>` 的連結（`lang=en` 時帶 `?lang=en`），**不是表單、不是按鈕**。失敗的 run、別人的 run、逾時的申請、已被按過的申請都不會有這個鍵，所以沒有卡片。
4. **migration**：不需要（不碰資料結構）。
5. **本片不處理**：再次提出（逾時 7 天後不會自動重提；見裁決 4）、沒有擁有者的 run（不會有申請）。

## 失敗先行測試（現在都會紅；新檔 `test_clean_page.py`，預估 19 條 TC）
確認頁：
- `test_a_pending_clean_request_page_says_clean_not_cancel_and_has_the_confirm_delete_button`（標題、引言、按鈕、zh 與 en 各一）。
- `test_the_plain_block_shows_kind_run_name_and_the_folder_to_delete_and_nothing_else`（無 pipeline／version／env／samples 列，不出現破折號）。
- `test_the_expired_and_void_pages_for_clean_work_say_seven_days_and_do_not_say_send_it_again_from_the_ai`。
- `test_launch_and_cancel_pages_are_byte_for_byte_what_they_were`（三種狀態 × 兩種種類 × 兩種語言與之前的輸出相同；用本片之前的輸出存成測試內的字串常數）。
- `test_get_changes_nothing_for_a_clean_request`（頁面狀態前後 `confirmations`、`jobs` 全表相同）。
- `test_only_the_person_who_has_the_request_can_see_and_press_it`（他人 GET → 403、他人 POST → 403、未登入 → 登入頁；讀與寫各一條）。
- `test_pressing_with_a_wrong_or_missing_csrf_queues_nothing`；`test_pressing_once_queues_exactly_one_clean_work_job_and_twice_says_already`。
- `test_the_pages_after_pressing_never_tell_a_clean_request_to_go_back_to_the_ai`（成功頁、`not_found`／`not_yours`／`expired`／其他失敗頁各掃一次：不含「回到 AI」）；`test_the_pages_after_pressing_a_launch_or_a_cancel_are_unchanged`（逐字回歸）。
- `test_pressing_after_seven_days_queues_nothing`（時鐘撥過 7 天，頁面 410）。
看板：
- `test_a_succeeded_run_with_my_open_clean_request_shows_one_notice_with_a_link_to_the_confirmation_page`（連結恰為 `/c/<rid>`，內容含「結果不會被動」，zh 與 en 各一）。
- `test_the_notice_is_a_link_not_a_form_and_has_no_button`。
- `test_no_notice_for_a_failed_a_running_or_a_lost_run_even_with_an_open_request`（三條）。
- `test_no_notice_for_another_users_request_or_run`（他人的 run、他人的申請）。
- `test_no_notice_after_the_request_is_pressed_expired_void_or_forgotten`（四條）。
- `test_a_board_without_any_clean_request_is_byte_for_byte_what_it_was`（succeeded、failed、running 三種 run 頁與右欄與之前的輸出相同）。
範圍：
- `test_clean_requests_is_a_read_that_filters_by_caller_and_is_not_a_tool_or_a_route`（`actions.clean_requests` 存在；MCP 工具仍 12 個；`web.py` 路由清單與本片之前相同）。
- `test_the_web_sources_have_no_program_start_and_not_the_forbidden_word`（TC-071／TC-061 既有掃描涵蓋 `web.py`、`web_board.py`、`actions/__init__.py`，這裡確認新字串沒有拆字拼接）。

## 完成標準（done when）
- 自動：新測試綠；全套綠（含 `tests/platform_test.sh`、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`）；MCP 工具數仍 12；`git diff --name-only` 只有「範圍：檔案」所列；既有 web 測試一個沒改（`git diff --stat` 貼進 ledger，依 dev-plans 通例由 verifier 核對並重跑）。
- 手動（維護者，在本機看板上）：用 `confirm.create_pending` 手工建一張 `clean_work` 申請（executor 把建法寫進 ledger，**只用於看畫面，不要按送出**）→ 確認頁標題、字句、按鈕、白話區塊都對；一個成功 run 的右欄出現卡片、點連結進得了確認頁；失敗 run 沒有。executor 附 zh、en 的確認頁與看板截圖列進每日清單，**維護者回「好／不好」才合併**。
- 文件：無（`docs/` 在 f 片一次更新）。

## 環境事實
（行號為 `origin/v3` @ `279363b`；以函式名為準，動手前 `git fetch -q origin` 再核對。）
- `web.py`：`_PLAIN` :71-76；`view_of` :279；`plain_block` :288（`t[facts["what"]]` :295 查標籤——標籤不存在會 `KeyError`，所以 `_PLAIN` 一定要先有 `clean_work`）；`state_page` :302（標題二分 :303、動詞二分 :311、逾時文字寫死「10 分鐘」:315）；`confirm_get` :318；`confirm_post` :328；`read_runs` :352、`read_run` :358、`board_page` :~370（`render_board` 呼叫 :386）。
- `web_board.py`：`_failure_notice` :494（失敗通知的樣式，`class="notice state-failed"` :508）；`_right` :664；`render_board` :706；`t` 字典 `level_action` zh :52／en :96；CSS `.state-succeeded` :172、`.notice` :202。
- `confirm.facts`（b 片）回 `{"what": "clean_work", "run_name": …, "work": …}`；`confirm.open_clean_requests`（b 片）回 `{run_name: 申請編號}`。
- `test_actions_layer.py:156` 的對等檢查是單向的（每個工具要有同名動作），不要求每個動作都是工具；但 executor 動手前讀一遍該檔的 `SCAN_DIRS`（:25）與其 AST 掃描，確認新增的 `actions.clean_requests` 不會觸發任何掃描（它的名字不含 `launch`／`cancel`，也不 import 它們）。
- 憲法掃描：`test_scope.py` TC-071（:99）、TC-061（:186）掃 `abf_platform/` 全部原始碼；新 `.py` 檔前 40 行要有 `# Nothing existing: …`（TC-070）：`test_clean_page.py`。
- **前端 session 協調**：`web.py`／`web_board.py` 屬 ui 車道，由前端 session 負責；本片的 kinds 帶 `ui` 即為此。

## 不做
- 不新增網頁路由、不新增表單、不新增按鈕（通知只有連結；真正的按鈕只有確認頁那一個）。
- 不改 launch／cancel 的頁面；不改看板的其他卡片、不改樣式表。
- 不建立任何申請（f 片）；不新增 MCP 工具；不新增終端機指令。
- 不做再次提出的入口、不做「全部清理」、不做費用／儲存月費顯示（舊計畫的後半，另案：費用頁屬 `cloud-cost` 與網頁費用頁任務）、不做 30 天到期前 7 天的提醒（另案）。

## 裁決（2026-10-24，developer-agent；已併入上文，與其他段落不衝突）
1. **只走網頁確認頁（`PAGE` 通道），沒有 MCP 工具、沒有終端機路徑、沒有新路由。** 理由：任務是「平台提出、本人按」，不是「AI 提出」；少一個入口就少一個被誤用的面。沒有擁有者的 run（純終端機單人模式）因此不支援，f 片的畫面與文件要寫明。
2. **看板通知只是連結。** 理由：真正會刪東西的按鈕只留一個，在確認頁，並且帶 CSRF 與同使用者檢查。
3. **畫面先於申請上線。** 理由：f 片 `after` 本片；在 e 合併之前系統裡不會有任何 `clean_work` 申請，所以不會出現「標著取消的刪除按鈕」。
4. **逾時（7 天）後不會自動重提。** 舊計畫寫「下次 `offer_cleanups` 再提一張新的」，但觸發點已改成「run 成功當下」（f 片），沒有第二次機會。是否要補「重新提出」的入口，列為給維護者的問題，不在本片。
5. **新文字（確認頁、通知）等維護者回好／不好**，verifier 依本檔出題，合併前附 zh、en 截圖列進每日清單。
6. **切片理由**：舊計畫約 30 檔、需求超過 60 條測試；依 `dev-architecture-review-2026-10-24.md` §3 與 `dev-plans/README.md` 通例切成六片。本片 5 檔（含 ledger）。

## 裁決二（2026-10-25，回應 executor 卡住；與上文衝突時以本段為準）
1. **准改四條既有測試，但守住原意**（原意＝除了 store／confirm／jobs，沒有任何程式能「寫」或「排入」clean_work）：
   - `test_cleanup_confirm.py::test_tc067_no_new_entry_point_for_clean_work` 與 `test_cleanup_store.py::test_nothing_writes_clean_work_or_work_cleaned_at`：允許清單加 `web.py`、`web_board.py`、`actions/__init__.py`，**同時**對這三個檔加一條更嚴的檢查——檔內不得出現 `enqueue`、`create_confirmation`、`INSERT`、`UPDATE`、`work_cleaned_at =` 與 `clean_work` 同一行或同一函式（用 `ast` 找函式範圍）；也就是只准「讀」與「顯示」。
   - `test_web_parity.py` 兩條：把 `clean_requests` 登記為 `WEB_ONLY`（唯讀、只給網頁用）。
   - 其餘既有測試一律不准動；範圍加這三個測試檔，只限上述改動。
2. MCP 工具數以現況為準（不寫死 12）；TC-062 改成「沒有名稱含 clean 的工具」：接受。
3. 英文確認頁只翻種類名、欄位名、按鈕，其他沿用中文：接受，截圖時一併給維護者看。
4. `jev_test.sh` 那 1 項失敗：executor 先在 base（origin/v3）跑同一支，若 base 也紅，ledger 附輸出、視同已知環境紅；若 base 綠，要查清是不是本片造成。
5. 手動截圖（TC-078～081）：照 ui 守則用 Playwright 截 1440／390 px × zh／en 四張，放進 PR。

## 裁決三（2026-10-25 20:40，回應全套因負載紅）
6. 鏡像的舊 `__pycache__` 已由 developer-agent 修掉（abf-fast-suite 改成 `git clean -qfdx`），jev_test 的 TC-085 不會再被舊 pyc 誤觸。
7. **計時類偶發紅的判定**：全套只剩計時／逾時類（`confirm_launch_test.sh` 的 slow 門檻、`platform_clock_test.sh`、`test_station_e2e.py`、`test_relay_loopback.py`）紅，且每支單跑都綠 → ledger 貼「全套輸出＋每支單跑輸出」，視同綠寫 GREEN；任何非計時類的紅照常算紅。
8. 截圖（TC-078～081）這輪一定要做：Playwright 截 1440／390 px × zh／en 四張，存進 `specs/cloud-cleanup-e/shots/`。

## 專長守則（ui）

### executor

- 先讀專案根目錄的 `PRODUCT.md`（給誰用、要解決什麼）與 `DESIGN.md`（版面線框、tokens、每個畫面與狀態、維護者的原話例子）。讀不到就 BLOCKED，不自己發明設計。
- 只准用 `DESIGN.md` 定義的 tokens（色彩、字型、字級、間距、圓角）與版面。不新增任何視覺決策：不自創顏色、字型、間距數值，不順手「美化」。
- `DESIGN.md` 沒決定的事，一律寫進報告的「卡住的原因／要問的問題」，不猜。
- `DESIGN.md` 列出的每個畫面、每個狀態都必須做出來，包含空狀態、載入中、錯誤、失敗。少一個就不算完成。
- 遵守計畫寫明的前端限制（例如 CSP、禁用 inline style、不載外部資源、只在允許處使用 JS）。限制與設計衝突時停下來問，不自行取捨。
- 狀態絕不只靠顏色：一律「符號＋文字＋顏色」三者並用。
- 手機寬度可用（不橫向捲動、點擊目標夠大），鍵盤操作時焦點外框可見。
- 介面文字用使用者視角的白話，不露出內部術語、錯誤代碼或程式名詞；錯誤訊息說發生什麼事與下一步。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- `DESIGN.md` 的每個畫面、每個狀態都至少對應 1 個 TC（含空、載入、錯誤、失敗）。
- 維護者的原話例子逐字對應到 TC。
- 計畫列的前端限制各對應 TC（例如頁面不得含 inline style、不得請求外部網址、CSP 標頭存在）。
- 狀態表達 TC：每個狀態輸出的 HTML 同時含符號、文字，不得只靠 class 顏色。

**ACCEPTANCE（閱卷）必須檢查：**
- 把每個有改動的頁面渲染成 HTML 檔（用專案的 test client，或計畫指名的 fixture）。做不到就標 UNVERIFIED，並寫明需要什麼才能驗。
- 對渲染出的 HTML 跑 Impeccable 偵測器（唯讀）：`sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>`。
- **FAIL**：違反 `DESIGN.md` 的 tokens／畫面／狀態；違反計畫寫明的前端限制；狀態只靠顏色；缺少 DESIGN.md 列出的畫面或狀態。
- **「需要人看的事」**：偵測器的其他發現（對比、常見字型、AI 範本味等）與品味問題。這些不判 FAIL。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
- 注意：「看起來好不好」的最終判斷屬於維護者，靠 developer-agent 附在 PR 的截圖（B 級）決定，verifier 不替他下結論。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
