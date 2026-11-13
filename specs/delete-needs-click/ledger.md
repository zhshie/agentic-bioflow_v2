# delete-needs-click：實作紀錄（executor）

## 做了什麼（程式）

| 檔案:位置 | 改了什麼 | 為什麼 |
|---|---|---|
| `platform/abf_platform/actions/__init__.py` `DELETE_ONLY_ON_THE_PAGE`、`_is_delete`、`_page_url`、`_own_waiting_request`（`_already_done` 之後、`_ask` 之前，新增） | 新拒絕的中英文句子；判斷「這是刪除申請」；確認頁網址（原本在 `_ask` 內聯，抽成函式，同一算式）；只讀的「這筆申請是呼叫者自己的、同種類、同內容（雜湊相同）、仍 pending、未逾時嗎」 | 新拒絕只給「自己的、仍在等待、內容相同」的刪除申請（Q1），其餘維持舊拒絕、不帶網址 |
| `actions/__init__.py` `_ask`，`user_confirmed is True` 分支 | 刪除且沒帶 `request_id` → 指向確認頁的拒絕（Q4）；刪除且申請在等待 → 回新拒絕（含網址，`confirmation_url`），不呼叫 `confirm.approve`；其餘情況照舊進 `confirm.approve`，但刪除傳 `writer=None` | 拒絕發生在 `confirm.approve` 之前，申請列從頭到尾沒被寫過 |
| `actions/figures.py` `_request_change` 尾段 | 刪除的第一次答覆（pending）改為只指向確認頁（計畫 3）；拒絕答覆若帶 `confirmation_url` 就放進 `url` | 計畫 3、TC-002 |
| `platform/abf_platform/mcp_server.py` `delete_figure` 的描述與兩個參數說明（新增 `_DELETE_REQUEST_ID_DOC`、`_DELETE_USER_CONFIRMED_DOC`） | 說明改為：刪除不可復原，須本人在確認頁或表單確認，`user_confirmed`／`request_id` 對刪除無效 | 計畫 4、Q5；`pack_figures` 與其他工具的字串一字未動 |

## 為什麼不需動 `confirm.py`、`store.py`

- 新拒絕發生在 `_ask` 呼叫 `confirm.approve` 之前：`_own_waiting_request` 只用 `store.open_readonly` 讀一列，沒有任何寫入，所以申請維持 pending、不作廢、不消耗（TC-004、006 驗證列數、狀態、通道與 jobs 不變）。
- 不在等待的刪除（別人的、別種的、捏造、內容改過、逾時、作廢、已確認）仍走原本的 `confirm.approve(…CHAT…)`，得到原本的拒絕與原本的副作用（逾時仍被標為作廢，這是舊行為，TC-015 驗證訊息不變、不帶網址）。
- 防呆：刪除若在檢查之後、approve 之內才變成可核准（競態），`writer=None` 使 `confirm.approve` 無寫入函式可呼叫，圖庫不會被改；`confirm.approve` 的 CHAT 路徑本身一行未動，打包與其他種類因此逐字不變。
- 因此 L 級證明是：改動只在 `_ask` 之前加一道只讀的攔截，`confirm.py`、`store.py` 的每一行與原本相同（`git diff origin/v3...HEAD --stat` 可驗）。

## 為什麼參數留在 schema

`request_id`、`user_confirmed` 仍在 `delete_figure` 的 schema（`required` 仍是 `["run_id","name"]`），只是說明改成「對刪除無效」。理由：既有釘住測試（`test_the_tool_descriptions_say_the_three_things` 的參數名單、快照的屬性清單）不必改屬性，只改 R5、R6 點名的字串；而且已被舊版說明教過的 LLM 若仍帶這兩個參數，會得到清楚的拒絕與確認頁網址，而不是「未知參數」的錯誤。

## R1–R6（既有測試的反轉；只有這六處）

| 代號 | 舊值 | 新值 | 原因 |
|---|---|---|---|
| R1 `test_gallery_change_confirm.py::test_delete_on_each_channel[CHAT]` | 轉達後 `ok`，a 被刪 | 轉達後 `refused`，圖庫指紋不變，申請仍 pending、通道空；ELICITED、PAGE 分支不動 | 計畫：刪除不接受對話轉達 |
| R2 `…::test_a_replayed_yes_does_not_run_twice` 刪除半段 | 以轉達確認刪除 | 以確認頁（PAGE）確認刪除並斷言 a 不在 index；之後「新同名 a 不被誤刪」的斷言原樣保留 | 同上 |
| R3 `…::test_a_figure_deleted_in_between_is_a_plain_refusal` | 轉達得「圖庫已變動」 | 轉達得新拒絕（不含「圖庫已變動」）、申請仍 pending；「圖庫已變動」改由確認頁路徑（`refused_by_yes`）驗；圖庫不變的斷言保留 | Q3 |
| R4 `…::test_a2_a_reused_request_id_does_not_restate_the_result` 刪除一輪 | 第一次確認用轉達 | 刪除一輪第一次確認用確認頁；轉達重複使用的斷言（先前已經確認並執行過、不重述結果、不含圖名）不變，打包一輪不動 | Q2 |
| R5 `test_gallery_change.py::test_the_tool_descriptions_say_the_three_things` | 兩個工具都須含 `user_confirmed` 與 `only after` | 打包維持原斷言；刪除須含 `user_confirmed` 與 `no effect`、不含 `only after`；增加兩個參數說明含 `no effect` 的斷言；其餘（參數順序、required、`one figure`、`cannot be undone` 不在、長度 < 1200）不動 | 計畫 4 |
| R6 `platform/tests/mcp/snapshots/tools.json` 的 delete_figure | `request_id`：「…only together with user_confirmed=true, after the person answered yes in the chat.」；`user_confirmed`：「True only after the person themselves answered yes in the chat…」 | 兩段改為「Has no effect on delete_figure: …」；其他工具、其他欄位不動 | Q5 |

此外新增的測試皆為新增（`test_dnc_*`，每個註解 TC 編號），沒有刪除、放寬、skip 任何既有斷言。

## TC 覆蓋

TC-001～004、010：`test_dnc_a_relayed_delete_is_refused_with_the_page_and_nothing_is_consumed`；TC-005：`test_dnc_the_person_can_still_press_after_the_relay_was_refused`；TC-006：`test_dnc_thirty_relays_delete_nothing`；TC-007：`test_dnc_after_the_time_limit_the_old_refusals_stand`（網頁在轉達逾時後已被作廢，回 409「逾時」而非 410，兩者皆不給按鈕）；TC-008：`test_dnc_the_page_says_the_gallery_changed`、R3；TC-009：`test_dnc_user_confirmed_alone_points_to_the_page_and_makes_no_row`；TC-011/012：`test_dnc_the_refusals_of_other_people_and_other_kinds_give_no_page`（鮑看不到安的 run，所以得到「找不到 run」，同現狀，不帶網址）；TC-013/014：`test_dnc_invented_ids_and_a_changed_name_give_the_old_refusals`；TC-015：`test_dnc_an_expired_and_a_voided_request_keep_their_own_refusals`；TC-016：`test_dnc_a_request_the_person_already_confirmed_is_not_a_new_refusal`；TC-017/019：`test_dnc_the_form_still_deletes_and_a_no_still_voids`；TC-018：`test_delete_on_each_channel[PAGE]`；TC-020/026：`test_dnc_the_first_answer_names_only_the_page`；TC-021：`test_dnc_nobody_to_ask_is_as_it_was`；TC-022/023：R5、R6、`test_tools_schema_matches_snapshot`；TC-025/035：`test_dnc_a_relayed_pack_still_works_and_the_database_holds_no_chat_delete`；TC-024、027、028、030～032、036：既有測試未改且通過。

## 與 origin/v3 本來就紅的測試（不是本案造成，未動）

在 `origin/v3`（0b35b79c）上單獨跑也失敗：
- `platform/tests/mcp/test_mcp_contract_tools.py::test_descriptions_within_limit`（`pack_figures` 描述 614 字，超過 600，且不在 `OVER_LIMIT`）。
- `platform/tests/mcp/test_mcp_contract_writes.py::test_write_tool_reply_says_not_sent[delete_figure]` 與 `[pack_figures]`（該測試的圖庫不存在，答覆為「圖庫裡沒有…」而不含 `abf-platform` 或 `http`）。

本案的 `delete_figure` 描述為 571 字，沒有再增加超限的工具。

## `git diff origin/v3...HEAD --stat`

（見本檔最後一次提交時的輸出，附於下）

STAT_PLACEHOLDER
