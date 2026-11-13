# replace-needs-click：實作紀錄（executor）

## 做了什麼（程式）

| 檔案:位置 | 改了什麼 | 為什麼 |
|---|---|---|
| `platform/abf_platform/actions/__init__.py` `_REPLACE_ONLY_ON_THE_PAGE`、`_is_replace`（`_is_delete` 之後，新增） | 新拒絕的中英文句子；判斷「這是取代申請」：kind 為 `publish_figure` 且 bundle 的 `replaces` 非空 | 計畫 1、2、Q6：看申請當時存的 `replaces`，不看現況圖庫 |
| `actions/__init__.py` `_ask`，`user_confirmed is True` 分支 | 取代且沒帶 `request_id` → 指向確認頁的拒絕、不建列（TC-009）；取代且 `_own_waiting_request` 為真 → 回新拒絕（含 `confirmation_url`），不呼叫 `confirm.approve`；其餘照舊進 `confirm.approve`，取代傳 `writer=None`（防競態，與刪除相同） | 拒絕在 `confirm.approve` 之前、只讀，申請維持 pending（TC-004、006） |
| `actions/figures.py` `request_publish_figure` 尾段 | 取代申請第一次的答覆只指向確認頁（計畫 3）；拒絕答覆若帶 `confirmation_url` 就放進 `url`（Q2） | TC-002、010 |
| `platform/abf_platform/mcp_server.py` `publish_figure` 的描述與兩個參數說明（新增 `_PUBLISH_REQUEST_ID_DOC`、`_PUBLISH_USER_CONFIRMED_DOC`） | 描述改寫為 598 字（原 565、上限 600）：新名稱可轉達；同名取代時 `user_confirmed` 無效；參數說明兩段專用，共用字串 `_REQUEST_ID_DOC`／`_USER_CONFIRMED_DOC` 不動 | 計畫 6、Q3、Q4 |

複用的既有機制：`_own_waiting_request`、`_page_url`、`_ask` 的 `user_confirmed` 分支（delete-needs-click 加的）。沒有第二套機制。

## 為什麼不需動 `confirm.py`、`store.py`

- 新拒絕發生在 `_ask` 呼叫 `confirm.approve` 之前，只用 `store.open_readonly` 讀一列（`_own_waiting_request`），沒有寫入，所以申請維持 pending、不作廢、不消耗（TC-004、006 驗證列數、狀態、通道與 jobs 不變）。
- 不在等待的申請（別人的、別種的、捏造、內容改過、逾時、作廢、已確認）仍走原本的 `confirm.approve(…CHAT…)`，得到原本的拒絕；已確認的重放仍回「已存入圖庫」。
- 新名稱（`replaces` 為空）一行都沒變，CHAT 照舊（TC-019、020）。`pack_figures`、`delete_figure` 與其他種類的程式沒動。
- `git diff origin/v3...HEAD --stat` 可驗：`confirm.py`、`store.py`、`.github/`、`hooks/`、`platform/abf_station/`、`jobs.py`、CSS、`studio_cli.py`、`studio_remote.py` 無改動。

## 計畫第 4 點的實況（Q1，只加測試、不改程式）

提出時名稱不存在（`replaces` 為空）、核准時已有同名圖：重放取申請當時存的 `replaces`（空），雜湊相同，第一道門不攔；`figures._commit` 比對名單不符而拒絕。
- CHAT：`state: refused`、申請被作廢、什麼都不寫（TC-021、023）。**訊息**是平台一般的「未送出：平台沒有接受這次確認。請從頭再呼叫一次 publish_figure…」。合約 TC-021 寫的是「圖庫在申請送出後有變動…」，與程式實況不符（該句只出現在確認頁與表單的路徑）；依 Q1「不改程式」，測試釘住實況句，未改程式。請 verifier 在驗收時核對。
- PAGE：409、「圖庫在申請送出後有變動」（TC-022、008）。計畫文字寫「圖庫已變動」，實際頁面句是前者。
- ELICITED：「未送出」，new.png 仍是別人存的內容（TC-022 表單那一支，表單開著時另一筆寫入同名圖）。

## 合約內的兩處對不上（執行者的選擇，請驗收者看）

1. TC-003 要求答覆含「這次存入會取代圖庫中既有的圖」，同時要求過 `test_web_wording_sweep.py` 的禁用字；後者的 `NEW_WORDS` 含「這次」。兩者無法同時照字面成立。我照合約與計畫逐字寫了該句；測試中把這一句挖掉後才套禁用字檢查（`test_rnc_a_relayed_replace_is_refused…`，註解已寫）。這句出現在給 AI 的工具答覆，不是確認頁。若維護者要避開「這次」，改為「本次」並改合約。
2. TC-025 預期說明含「新名稱可轉達；會取代既有的圖時無效」，已照此寫成英文。

## 描述與參數說明的字數與選擇（TC-024、025、026）

- `publish_figure` 描述 598 字（上限 600），過六個 aspect 檢查；`OVER_LIMIT`、`ASPECT_GAPS`、`UNDESCRIBED_PARAMS` 沒有新增項目。為騰出字數刪去「private」、「(plain text)」，並把 caption 限制改為「max 200 characters」；其餘資訊都在。
- 參數說明專用兩段（Q4）；共用字串不動，其他八個工具的快照段落無 diff。
- 標註：`publish_figure` 仍是 `destructive_hint=False`、`idempotent_hint=True`（Q7）。**已知限制：**同名取代不可復原，與此標註不相稱；本案依計畫不改，請維護者決定是否改為 `destructive_hint=True`、`idempotent_hint=False`。TC-026 以 `test_rnc_the_tool_description_and_parameters_say_a_replace_needs_the_click` 釘住標註不變。

## R1（既有測試的改動；唯一一處）

| 代號 | 舊值 | 新值 | 原因 |
|---|---|---|---|
| R1 `platform/tests/mcp/snapshots/tools.json` publish_figure 的 `request_id` | 「The id of the pending request that the first call returned; only together with user_confirmed=true, after the person answered yes in the chat.」 | 同句加上「, and only for a new name: it has no effect when a figure already in the gallery would be replaced.」 | Q4、TC-025 |
| R1 同檔 `user_confirmed` | 「True only after the person themselves answered yes in the chat to this request; never fill it in for them.」 | 「…to this request, for a new name; never fill it in for them. It has no effect when a figure already in the gallery would be replaced: that is confirmed only on the confirmation page or in their own form.」 | 同上 |

沒有任何既有測試的斷言被反轉、刪除、放寬或 skip；其他測試皆為新增（`platform/tests/test_replace_needs_click.py`，每個註解 TC 編號）。`git diff origin/v3...HEAD --stat -- platform/tests` 只有該新檔與 `tools.json`。

## TC 覆蓋

TC-001～004：`test_rnc_a_relayed_replace_is_refused_with_the_page_and_nothing_is_consumed`；TC-005：`…the_person_can_still_press…`；TC-006、007：`…thirty_relays…`；TC-008：`…gallery_changed_meanwhile…`；TC-009：`…user_confirmed_alone…`；TC-010：`…first_answer_names_only_the_page`；TC-011：`…one_name_that_replaces…`；TC-012：`…other_people_and_invented_ids…`；TC-013：`…other_kinds_and_changed_content…`；TC-014：`…expired_and_a_voided…`；TC-015：`…already_confirmed…`；TC-016、017：`…the_form_replaces_and_a_no_voids`；TC-018：`…nobody_to_ask…`；TC-019、020：`…a_new_name_is_confirmed_by_a_relayed_yes…`；TC-021：`…chat_cannot_replace_a_name…`；TC-022：`…page_cannot_replace…`、`…form_cannot_replace…`；TC-023：`…two_relays…`；TC-024～026：`…tool_description_and_parameters…`、`tests/mcp`（快照、字數、aspect）；TC-027：`test_studio_publish.py` 未改且通過；TC-028、035：`test_chat_confirm.py`、`test_human_channel.py`、`test_confirm_page.py`、`test_gallery_change_confirm.py` 未改且通過；TC-029、034：`…no_old_version_is_kept…`；TC-030～033：`git diff`；TC-031：`test_chat_tools.py`（`CHAT_EXCLUDED`）通過。TC-036～039：本檔、`docs/TESTING.md`（新增「replace-needs-click」一節）、`docs/PLATFORM.md`、`CHANGELOG.md`。

## `platform/tests/mcp/` 在本機的實際結果（該目錄在 `fable/mcp-tests-in-ci` 合併前不在 CI）

WSL，`~/abf-venv/bin/python -m pytest tests/mcp -q`，在 GREEN 之後：

```
FAILED tests/mcp/test_mcp_contract_tools.py::test_descriptions_within_limit
FAILED tests/mcp/test_mcp_contract_writes.py::test_write_tool_reply_says_not_sent[delete_figure]
FAILED tests/mcp/test_mcp_contract_writes.py::test_write_tool_reply_says_not_sent[pack_figures]
3 failed, 84 passed, 6 skipped, 17 xfailed in 41.22s
```

恰為 origin/v3 本來就紅的那三個（`pack_figures` 描述 614 字；兩個寫入工具在空圖庫上的答覆不含 `abf-platform`／`http`），與本案無關，未動。`publish_figure` 的 `test_descriptions_within_limit` 與其兩個 `test_write_tool_reply_says_not_sent` 案例通過。
