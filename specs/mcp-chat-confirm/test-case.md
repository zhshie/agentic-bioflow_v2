# 測試案例：MCP 對話確認通道（CHAT）＋憲法 7.0.0

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/mcp-chat-confirm/plan.md`（無 spec.md；以 plan、維護者原話與各輪「裁決」為規格，衝突時以較晚的裁決為準）　**總覽**：`test-case-overview.md`

名詞：
- **待確認**＝AI 第一次呼叫工具時平台的回覆（還沒送出，附一個 request id）。
- **確認呼叫**＝AI 用同樣的參數，加上 `request_id=<那個 id>` 與 `user_confirmed=true` 再呼叫一次。
- **列**＝平台資料庫 `confirmations` 表裡的一筆申請（狀態 pending＝等人回答、confirmed＝已核准、void＝作廢）。
- ann、bob＝測試用的兩位不同使用者；`w`＝測試夾具 `World`（`platform/tests/human_harness.py`）。
- 自動測試都在 `platform/tests/test_chat_confirm.py`，函式名以 `test_tcm` 開頭，註解裡寫對應的 TC 編號；先寫、先紅。
- 「無 job」＝工作佇列裡沒有新增任何工作（`w.jobs()` 沒變）。

類型只有三種：功能、例外、不在範圍。驗證方式：自動＝測試檔；手動＝由驗收者讀 git diff／文件並把證據寫進報告（只有 TC-080 寫進 `docs/TESTING.md`）。

## US1 — 在對話裡回覆「送出」就能送出，不必開網頁（launch 主線，優先度 P1）

維護者原話：「ai agent透過MCP使用abf，現在是不能直接送出，一定要跳出網頁確認連結才能送出嗎? 若是，改成只要有得到使用者回復確認送出就好，這樣才能達成全靠MCP也能跑」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 維護者原話；作法 5；TCM-01 | 功能 | 有使用者 ann；沒有任何申請與工作；client 沒有表單 | ann 的 AI 呼叫 launch（正常參數，不帶 request_id、user_confirmed） | 回覆 sent=False、state="pending"、有 id；工作清單為空；confirmations 只有一列且是 pending | 自動 |
| TC-002 | 作法 5 | 功能 | 同 TC-001 | 看 TC-001 回覆的 message | 訊息含 `request_id` 與 `user_confirmed`；說明要請本人在對話裡明確回覆後再呼叫一次；說明「在本人回覆之前不可自己填 true」；仍提到可請他打開網址按送出；不再含「AI 不能代按」 | 自動 |
| TC-003 | 維護者原話（使用者在對話回覆→排隊）；TCM-01 | 功能 | TC-001 之後，ann 在對話裡回覆了「送出」 | AI 用同樣的參數加 `request_id=<TC-001 的 id>`、`user_confirmed=true` 再呼叫 launch | 回覆 sent=True、state="queued"、有 job_id；`w.jobs("launch_nextflow")` 恰一筆 | 自動 |
| TC-004 | 維護者原話（全靠 MCP） | 功能 | 沒有表單的 client；測試期間不碰網頁 `/c/<id>` | 走完 TC-001＋TC-003 | 全程沒有送出任何表單答案、沒有對 `/c/<id>` 發請求，仍然排隊成功；該列 channel 是 `CHAT`，不是 PAGE 也不是 ELICITED | 自動 |
| TC-005 | 作法 7；TCM-03 | 例外 | ann 有一個 pending 列（TC-001）；client 沒有表單 | AI 帶該 id 但 `user_confirmed=false` 呼叫；再試一次完全不帶 `user_confirmed` | 兩次都回待確認（sent=False）；那一列仍是 pending；無 job | 自動 |
| TC-006 | 專長守則：對等性；作法 6 | 功能 | 兩位使用者各發同樣內容的 launch：一位用表單答「是」（ELICITED），一位用 CHAT | 比較兩邊結果 | 兩邊都排出同種類（launch_nextflow）且內容相同的工作；列的 kind、sha256、caller_user_id 規則相同；只有 channel 不同（ELICITED／CHAT） | 自動 |
| TC-007 | 作法 8；TCM-08 | 功能 | ann 已經用 CHAT 核准並排隊（TC-003） | AI 再用同樣參數呼叫 launch，這次不帶 request_id、user_confirmed | 回覆指向同一個 job_id；工作仍只有 1 筆；confirmations 沒有新增列（也就是沒有再問一次） | 自動 |
| TC-008 | 作法 5 | 功能 | 同 TC-001 | 比對待確認回覆的鍵 | 仍有 sent、state、summary、confirmation_url、message，型別與舊版相同；`id` 就是 request id | 自動 |
| TC-009 | 維護者硬條件：稽核記 CHAT；TCM-15 | 功能 | TC-003 完成 | 讀 ann 那一列 | channel=="CHAT"；confirmed_at 非空；caller_user_id==ann 的 user_id；sha256 等於該次內容（bundle）的雜湊 | 自動 |
| TC-010 | 作法 13；TCM-15 | 功能 | 一列 channel 為 CHAT 且已核准；另一列 channel 為其他字串（如 "X"）且已核准 | 呼叫 `find_approved`（含 include_spent） | 找得到 CHAT 那列；找不到其他字串那列（通道清單是白名單，只多了 CHAT） | 自動 |
| TC-011 | 作法 14；TCM-16 | 例外 | ann 有 pending 列；讓 `jobs.enqueue_confirmed` 拒絕 | AI 發確認呼叫 | 回覆為未送出；該列變 void，但 channel 仍是 `CHAT`、confirmed_at 保留（使用者確實說過是）；無 job | 自動 |

## US2 — 擋住不該通過的確認（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 作法 6；第一輪裁決 7；TCM-02(a) | 例外 | 沒有任何待確認；client 沒有表單 | AI 呼叫 launch，帶 `user_confirmed=true` 但沒有 request_id | 回覆 ok False，訊息以「未送出：」開頭並請 AI 先不帶 user_confirmed 發起申請取得 request id；confirmations 沒有任何新列；無 job | 自動 |
| TC-013 | 第一輪裁決 7 | 例外 | client 宣告支援表單（夾具提供表單答案） | AI 呼叫 launch，帶 `user_confirmed=true`、沒有 request_id | 不跳表單（表單答案沒被用到）；被拒、沒有新列、無 job | 自動 |
| TC-014 | 作法 6；TCM-02(b) | 例外 | ann 無任何申請 | 確認呼叫帶一個隨機 32 位 hex 的 request_id | ok False；confirmations 沒有任何列；無 job | 自動 |
| TC-015 | 作法 6；TCM-02(c) | 例外 | 同上 | 確認呼叫帶空字串 request_id | ok False，不寫任何列，無 job，沒有堆疊訊息 | 自動 |
| TC-016 | 作法 6；TCM-02(c) | 例外 | 同上 | 確認呼叫帶過長（例如 5000 字）的 request_id | ok False，不寫任何列，無 job | 自動 |
| TC-017 | 作法 6；TCM-02(c) | 例外 | 同上 | 確認呼叫帶非字串的 request_id（例如數字、清單） | ok False，不寫任何列，無 job | 自動 |
| TC-018 | 維護者硬條件：內容綁雜湊；TCM-04 | 例外 | ann 以預設參數取得 pending id | 確認呼叫改 `params={"depth": 9}`，帶該 id＋true | ok False（狀態 changed）；無 job；該列仍是 pending，不是 void | 自動 |
| TC-019 | 維護者硬條件：內容綁雜湊；TCM-04 | 例外 | 同 TC-018 | 確認呼叫改 revision（另一次改 run_name），帶該 id＋true | 兩次都被拒（changed）；無 job；該列仍 pending | 自動 |
| TC-020 | 作法 11（八步 ⑥） | 例外 | 同 TC-018 | 看被拒後的列 | 該列沒有被核准、沒有被作廢、沒有排任何 job，channel 與 confirmed_at 沒被寫 | 自動 |
| TC-021 | 第三輪裁決 2：別人的 id 一律 not_yours；TCM-06 | 例外 | ann 的列已用 CHAT 核准並排隊，job_id 為 J | bob 拿 ann 的 id 發確認呼叫（任意參數） | ok False；回覆整段轉成文字後**不含 J**；列與 job 都不變 | 自動 |
| TC-022 | 作法 6；TCM-04 第三次呼叫 | 功能 | TC-018 被拒後，ann 的列仍 pending | ann 的 AI 改回原參數，帶同一個 id＋true | 排隊成功（sent True、state "queued"） | 自動 |
| TC-023 | 作法 12 | 例外 | 同 TC-018 | 看 changed 回覆 | 訊息以「未送出：」開頭，說明內容與當初顯示的不同，並告訴 AI「請改回原參數，或重新發起一次」；不帶 job_id | 自動 |
| TC-024 | 維護者硬條件：同一呼叫者；跨使用者寫；TCM-06 | 例外 | ann 有 pending 列 | bob 拿 ann 的 id＋true 發確認呼叫 | ok False（not_yours）；該列仍 pending；無 job；之後 ann 自己的確認呼叫仍能核准成功 | 自動 |
| TC-025 | 第三輪裁決 2；跨使用者讀；TCM-06 | 例外 | ann 的列已 void（例如已過期被標 void） | bob 拿該 id＋true 發確認呼叫 | 被拒；回覆整段文字不含作廢原因（不含 expired、void 等字樣）也不含 ann 的任何資料 | 自動 |
| TC-026 | 維護者硬條件：10 分鐘逾時；TCM-05 | 功能 | ann 有新的 pending 列；時鐘推進 599 秒 | 確認呼叫 | 仍可核准，排隊成功 | 自動 |
| TC-027 | 同上；TCM-05 | 例外 | ann 有 pending 列；時鐘推進 600 秒 | 確認呼叫 | 被拒；該列標為 void，原因含 `expired`；無 job | 自動 |
| TC-028 | 同上；TCM-05 | 例外 | 同上；時鐘推進 601 秒 | 確認呼叫 | 同 TC-027 | 自動 |
| TC-029 | 維護者硬條件：一次性；TCM-07 | 例外 | TC-003 完成（job_id 為 J） | ann 再送一次完全相同的確認呼叫 | 回覆仍是同一個 J；`len(w.jobs())==1`；`len(w.confirmations())==1` | 自動 |
| TC-030 | 作法 9；Q3；TCM-09 | 例外 | 透過 stdio（caller 為 None）；ann 另有一個 pending 列的 id | stdio 帶該 id＋true 發確認呼叫 | 被拒；無 job；該列仍 pending | 自動 |
| TC-031 | 作法 9；TCM-09 | 例外 | 有一列 pending | 直接呼叫 `confirm.approve(..., "CHAT", None, ...)` | 丟出 `NotApproved`，status 為 `not_yours`；該列不變 | 自動 |
| TC-032 | 作法 6；TCM-11 | 例外 | ann 有一列 launch 的 pending；ann 另有可取消的 run | 把 launch 的 id 拿去給 cancel 帶 true | 被拒；無 job；launch 那列仍 pending | 自動 |
| TC-033 | 第二輪裁決 3／第三輪裁決 2：雜湊檢查在 already 之前 | 例外 | ann 的列已 CHAT 核准並排隊（job_id J） | ann 用同一個 id＋true 但改了 params 再呼叫 | ok False（changed）；回覆不含 J；沒有新 job；原列不變 | 自動 |
| TC-034 | 第三輪裁決 2：void 優先 | 例外 | ann 的列是 void；確認呼叫同時改了 params | 發確認呼叫 | 回覆是 void／作廢類的拒絕，不是 changed；無 job | 自動 |
| TC-035 | 第三輪裁決 2：expired 優先 | 例外 | ann 的 pending 列已逾 600 秒；確認呼叫同時改了 params | 發確認呼叫 | 回覆是 expired 類的拒絕，不是 changed；該列標 void；無 job | 自動 |
| TC-036 | 作法 11（八步 ④） | 例外 | ann 的列是 void（非逾時，例如佇列拒絕後作廢） | ann 用同一 id、原參數發確認呼叫 | 被拒；無 job；不重新核准 | 自動 |
| TC-037 | 作法 6：既有檢查照常 | 例外 | ann 有 pending 列 | 確認呼叫的 run_name 不合規（`check_run_name` 會拒絕的那種） | 被拒；無 job；該列沒被核准（仍 pending） | 自動 |
| TC-038 | 作法 6：`_cloud_check` 照常 | 例外 | ann 有 pending 列；夾具讓雲端檢查在確認時失敗 | 發確認呼叫 | 被拒、無 job、該列沒被核准 | 自動 |
| TC-039 | 作法 6：擁有者規則；跨使用者寫 | 例外 | ann 有 cancel 的 pending 列（針對 ann 的 run） | bob 呼叫 cancel（run_name 是 ann 的 run）帶 ann 的 id＋true | 被拒；無 job；ann 的列仍 pending | 自動 |

## US3 — 介面、通道與範圍邊界（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 第二輪裁決 2；第三輪裁決 4 | 不在範圍 | 無 | 讀 `launch_pipeline` 的工具 schema 與沒有人確認時的行為 | schema 與 base 逐項相同，沒有 request_id、user_confirmed；沒有人確認仍拒絕、無 job | 自動 |
| TC-041 | 不做第 1 條；TCM-12 | 不在範圍 | 無 | 讀 `forget` 的 schema；用 CHAT 方式嘗試核准 forget | schema 沒有 request_id、user_confirmed；forget 仍只收表單，沒有刪除任何東西 | 自動 |
| TC-042 | 不做第 1 條 | 不在範圍 | 有一列 clean_work 的待處理申請 | 對它發 CHAT 確認 | 被拒；該申請不被核准；`clean_work` 仍只有表單通道 | 自動 |
| TC-043 | 作法「其他工具不動」；TCM-14 | 不在範圍 | 無 | 比對 launch、cancel、resume、relaunch 以外所有 MCP 工具（含 forget、唯讀工具）的 schema 與舊版（snapshot） | 逐項相同 | 自動 |
| TC-044 | 作法 2；裁決 3；「照3.」；TCM-12 | 例外 | ann 有一列 pending | 呼叫公開的 `actions.approve(..., confirmed_by=actions.CHAT)` | 被拒；該列沒被核准、沒寫入任何東西（CHAT 不是網頁路由可用的通道） | 自動 |
| TC-045 | 「照3.」＝CHAT 與網頁並存；不做第 2 條；TCM-12 | 功能 | ann 有一列 pending | ann 在網頁 `/c/<id>` 按送出 | 該列標成 `PAGE` 並排隊；既有網頁測試（含 `test_tch09_b_c_*`）全綠（`web.py`、`web_*.py` 零 diff 由 TC-077 驗） | 自動 |
| TC-046 | 「照3.」＝CHAT 與表單並存；TCM-12 | 功能 | client 宣告支援表單，ann 答「是」 | 呼叫 launch，帶表單答案 | 該列標成 `ELICITED` 並排隊，不需要 request_id；既有 tc01、tc_c* 保持綠 | 自動 |
| TC-047 | 作法 1；不做第 2 條；專長守則：migration | 不在範圍 | 無 | 比對 base：HTTP 路由清單、MCP 工具名清單、`confirmations` 表的欄位與其他表、migration 檔 | 路由與工具名完全相同；表結構完全相同（沒有新欄位、新表）；沒有新增 migration（理由：`channel` 是自由字串，不需要 migration）；`store.py`、`jobs.py` 零 diff 另由 TC-077 驗 | 自動 |
| TC-048 | 作法 4；TCM-14 | 功能 | 無 | 讀 launch、cancel、resume、relaunch 四個工具的 schema | 各自的 properties＝舊集合 ∪ {request_id, user_confirmed}；恰好這四個工具多了這兩個欄位，其他工具都沒有 | 自動 |
| TC-049 | 作法 4；TCM-14 | 功能 | 無 | 讀上述四個工具兩個新欄位的型別 | `user_confirmed` 是 boolean、預設 False；`request_id` 是 string 或 null、預設空；各工具 `required` 與舊版相同 | 自動 |
| TC-050 | 作法 16 | 功能 | 無 | 讀四個工具的 description | 保留原有「you cannot say it for them」前後句；各加一句 CHAT 流程，含「只在本人於對話中明確回覆之後才填 user_confirmed=true；不確定就再問」的意思 | 自動 |
| TC-051 | 作法 17（規則 B） | 功能 | 無 | 讀 `FIXED_SENTENCE` | 仍含 `does not start anything until the person says yes`、`you cannot say it for them`、`(in the terminal, abf-platform launch, cancel, resume and relaunch ask the same way)`、`The tool forget only asks too: it deletes nothing until the person says yes in their own client's form.`、`deletes nothing until the person says yes`；多一句說明可在對話回覆後帶 request_id 與 user_confirmed=true 再呼叫；總長 ≤ 2048 bytes | 自動 |
| TC-052 | 作法 18；PLATFORM.md 該句 | 功能 | 無 | 讀 `elicit.py` 檔頭、`mcp_server.py` 模組 docstring、`docs/PLATFORM.md` 該句 | 不再宣稱「沒有任何參數能說 yes／confirm=true 一律不行」；改成表單仍是平台自己問人、CHAT 是另一條通道且保證較弱 | 手動：驗收者讀 diff 並 grep 舊句 |
| TC-053 | 作法 15；TCM-13 | 功能 | 無 | 呼叫 `chat_tools.tool_specs()`，看 launch、cancel、resume、relaunch | 這四個的 properties 都不含 request_id、user_confirmed | 自動 |
| TC-054 | 作法 15；TCM-13 | 功能 | 無 | 讀 `CHAT_SYSTEM_PROMPT`；對 `tool_specs()` 全部項目檢查工具名與屬性名（與既有 `test_chat_tools.py::test_tc002` 同範圍） | `CHAT_SYSTEM_PROMPT` 與 base 逐字相同；工具名與屬性名不含 `BANNED_WORDS`。（description 不在此列：現有 description 本來就含 yes，見總覽「不確定的地方」） | 自動 |
| TC-055 | 作法「文字」；完成標準：文件 | 功能 | 無 | 讀 `docs/PLATFORM.md`（「The confirmation page」節）、`CHANGELOG.md`、`skills/launch|runs|operational/SKILL.md` | PLATFORM.md 多一段 CHAT；CHANGELOG 有條目；三個 skill 各只加一句 CHAT；被測試釘住的句子都沒被刪（`tests/skill_runs_uses_actions_test.sh`、`platform_direction_docs_test.sh`、`platform_storage_doc_test.sh` 仍綠） | 手動：驗收者讀 diff；釘字由上述 shell 測試佐證 |

## US4 — cancel、resume、relaunch 走同一流程（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-056 | 作法「四個工具」；TCM-10 | 功能 | `w.hand_over()` 後 ann 有可取消的 run | cancel 先待確認、再確認呼叫 | 排隊成功，工作種類是 `cancel_run`，channel 為 CHAT | 自動 |
| TC-057 | 同上；TCM-10 | 功能 | ann 有一個失敗的 run（用 `test_resume_entrypoints.py` 的既有夾具） | resume 先待確認、再確認呼叫 | 排隊成功，channel 為 CHAT | 自動 |
| TC-058 | 維護者硬條件：內容綁雜湊；TCM-10 | 例外 | resume 已有 pending；確認呼叫改了 `params`（另一次改 `extra_config`） | 發確認呼叫 | 兩次都被拒（changed）；無 job；該列仍 pending | 自動 |
| TC-059 | 同上；TCM-10 | 功能 | ann 有一個失敗的 run | relaunch 先待確認、再確認呼叫 | 排隊成功，channel 為 CHAT | 自動 |
| TC-060 | 作法 8（`find_attempt`） | 功能 | resume 與 relaunch 各已用 CHAT 核准 | 各自再呼叫一次，不帶新參數 | 回覆指向已存在的 job；沒有新 job；confirmations 沒有新列 | 自動 |
| TC-061 | 作法 8（`find_cancel`） | 功能 | cancel 已用 CHAT 核准 | 再呼叫一次 cancel，不帶新參數 | 回覆指向已存在的 job；沒有新 job；沒有新列 | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-062 | Safety Net：寫入工具未經人答覆一律拒絕；規則 C | 例外 | `test_tch09_nothing_reaches_the_queue_through_the_tools_without_a_person` 已改寫（函式名保留 `test_tch09_` 前綴） | 原迴圈照跑（ann 與 None、launch 與 cancel、四種 variants）；新增帶 `user_confirmed=True` 但(a)沒有 pending、(b)別人的 id、(c)過期的 id | 全部 `w.jobs()==[]`；原迴圈的斷言一字沒被放寬 | 自動 |
| TC-063 | I.2 | 功能 | 讀憲法 I.2 | 讀 diff | 「三條」改成四條，加入 CHAT 的定義；誠實寫明平台看不到對話、CHAT 只保證「AI 不能核准沒給人看過、內容被改、過期、已用過、或不是他的申請」，不保證那句 yes 出自人；列出殘留風險與限縮手段；「AI cannot press for them」改成「AI cannot answer for them; it can only relay the person's own reply on the request id」 | 手動 |
| TC-064 | Safety Net（第一輪裁決 4） | 功能 | 讀 Safety Net 規則 | 比對 base | 括號 (today `launch`, `launch_pipeline`, `cancel`, `resume`, `relaunch` and `forget`) 與 base 逐字相同（有反引號、含 launch_pipeline）；`constitution_6_test.sh` TC-045 仍綠 | 手動：比對 base，並跑該 shell 測試 |
| TC-065 | Safety Net | 功能 | 同上 | 讀 diff | 「takes a person's yes only from…」那句加入第四條通道（對話回覆） | 手動 |
| TC-066 | Safety Net | 功能 | 同上 | 讀 diff | 「a token, a pending request or the model's own answer is never that answer」保留「token／pending request／model's own answer 都不算」，並加「a chat reply counts only as the person's own, relayed with the request id and `user_confirmed=true`」 | 手動 |
| TC-067 | Approval 規則（第一輪裁決 3） | 例外 | 讀 7.0.0 條目的 Approval | 讀 diff | 寫成 `**Approval.** PENDING: 維護者尚未對修正案全文表示同意（「照3.」只是選方案）。合併前必須由維護者親口同意後補上其原話。`；沒有「已同意」；沒有杜撰引言；「照3.」只被引為選方案 | 手動 |
| TC-068 | 作法 22；第一輪裁決 5 | 功能 | ledger 第一行記了開工日 `date +%F` | 比對 | 7.0.0 條目標題日期、檔尾 `**Version**: 7.0.0 \| **Ratified**: 2026-09-28 \| **Last Amended**: <日期>`、`charter_v4_workflow_test.sh`、`constitution_scope_test.sh`（兩處）、`platform_direction_docs_test.sh` 的版本字串全是同一個日期、與憲法檔尾逐字相同；這些 shell 測試全綠；舊的 6.2.0 條目檢查未動 | 自動：三個 shell 測試 |
| TC-069 | Task 例外範圍（第一輪裁決 3）；不做「不修舊憲法條目」 | 不在範圍 | 無 | 讀 `git diff` 的憲法部分 | 只動 I.2、Safety Net 規則與其 Check 行、新增 7.0.0 條目、檔尾版本行；其餘一個字都沒動；舊條目（含 5.0.0「A pending request, a token, and anything the model can answer are not a channel」）沒被修改 | 手動 |
| TC-070 | Safety Net Check 行 | 功能 | 無 | 讀 Check 行並跑 `tests/constitution_checks_exist_test.sh`、`tests/constitution_6_test.sh` | 加了 `test_tcm`（`test_chat_confirm.py`），原有前綴一個不少；兩個 shell 測試皆綠 | 自動 |
| TC-071 | 作法 21 | 功能 | 無 | 讀 7.0.0 條目 | `### 7.0.0 (<日期>)` 下六段依序：Rationale（引維護者原話）、What changes、Sync Impact Report（列受影響檔）、Impact on existing deployments（新參數選填、舊 client 不受影響、不需要 migration、schema 多兩個選填欄位）、**Version.** MAJOR（說明為何不是 MINOR）、Approval；引用「照3.」；明寫 5.0.0 那句對 CHAT 不再適用 | 手動 |

## 專長守則（backend）

| 編號 | 憲法條目／守則 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-072 | 對等性 | 功能 | 無 | 測試同時列舉使用者可見的動作（MCP 工具 launch、cancel、resume、relaunch）與動作層函式（request_launch、request_cancel、request_resume、request_relaunch） | 兩邊一一對應；少任何一邊測試就失敗 | 自動 |
| TC-073 | 動作層唯一邏輯 | 功能 | 無 | 檢查 `mcp_server.py` 四個工具的處理函式與 CHAT 路徑 | 處理函式沒有自己核准或排隊，一律呼叫動作層；CHAT 與 ELICITED、PAGE 共用 `confirm.approve`，沒有第二份核准邏輯 | 自動 |
| TC-074 | 錯誤訊息與日誌 | 例外 | 無 | 分別觸發：沒有 pending、not_yours、expired、stdio 被拒、沒有 request_id | 每個回覆都以「未送出：」開頭、一句白話原因、一句下一步（例如「請重新發起申請」）；不含 job_id 欄位、堆疊、檔案路徑、SQL（changed 與無 request_id 的內容另依 TC-023、TC-012）。用詞是否夠白話由維護者看 draft PR | 自動（只驗形狀） |
| TC-075 | 密鑰不外洩 | 例外 | 帶 token 登入的 ann 與 bob 各跑完 TC-001～TC-029 的代表情境 | 檢查所有回覆與日誌輸出 | 不含 token、密碼、完整檔案路徑 | 自動 |

## 完成標準與流程

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-076 | 規則 C；不做「不放寬既有拒絕」 | 功能 | 無 | 跑既有拒絕測試：`test_tca14_*`、`test_tcb04_*`／`test_tcb08_*`、`test_tc142_*`／`test_tc144_*`、`test_tc034_*`／`test_tc037_*`／`test_tc038_*` | 全綠；若有修改，只加「CHAT 也被拒」的斷言，沒有放寬或刪斷言（對 base 比對） | 自動 |
| TC-077 | 範圍：檔案；不做（含八項建議） | 不在範圍 | 無 | 讀 `git diff --name-only` 與 diff | 只含「範圍：檔案」所列；`.github/`、hooks、`plugin.json`、`platform/abf_station/`、`web.py`／`web_*.py`、`jobs.py`、`store.py`、`CONTEXT.md`、`docs/adr/*`、`docs/PRINCIPLES.md`、`docs/ROADMAP.md` 零 diff；沒有做八項「建議但需另點頭」（每日上限、SU 預估、client 能顯示表單時拒絕 CHAT、伺服器端標記網頁聊天、/c/<id> 顯示 CHAT 與作廢鈕、核准通知、留存回覆原文、forget 納入 CHAT） | 手動 |
| TC-078 | 作法 10；完成標準 | 功能 | 無 | `git diff origin/v3 -- platform/abf_platform/confirm.py` | 只有加關鍵字參數 `expected_sha=None`、`expected_kind=None`、CHAT 專屬分支與通道清單加 `'CHAT'`、docstring；ELICITED／PAGE 路徑的程式行沒有改 | 手動：讀 diff；既有 tc01、tc_c* 測試佐證 |
| TC-079 | 爆炸半徑證明（必交） | 功能 | 無 | 驗收者讀報告與程式 | 報告列出：(1) 所有 `confirm.approve` 的呼叫處與各自 channel，證明能「把 CHAT 傳進去核准」的只有 `_ask` 的確認分支（其餘是定義或白名單）；(2) 所有能把模型參數送進四個工具的入口（stdio、HTTP MCP、PAT、OAuth 連接器、網頁聊天 /chat）與誰能填 user_confirmed（任何 MCP client 的模型都能填；網頁聊天靠剝 schema）；(3) 以 TC-014、018、021、024、032 證明別人的 id 或沒給人看過的內容無法被核准；每項附實際執行的指令與輸出 | 手動 |
| TC-080 | 完成標準：手動 | 功能 | 測試平台；只有 stdio＋HTTP MCP 的 client，不開網頁 | 依 `docs/TESTING.md` 新增的步驟做一次 launch：看摘要→在對話回「送出」→AI 帶 id 再呼叫→收到工作編號 | 收到工作編號；`confirmations` 表該列 channel 為 `CHAT`；`docs/TESTING.md` 有這個步驟且具體到可照做 | 手動：`docs/TESTING.md` |
| TC-081 | 第一輪裁決 3（Q1）；PR 流程 | 功能 | PR 已開 | 看 PR 狀態與報告 | PR 為 draft，沒有 `--auto`、未 merge；報告與 ledger 寫明「本任務依明文例外修改憲法」；憲法 Approval 仍是 PENDING，等維護者對全文親口同意 | 手動：驗收者查 PR 狀態與 ledger |
| TC-082 | 規則 A（既有 schema 測試只加例外，不放寬） | 功能 | 無 | 對 base 逐檔比對 plan 規則 A 列的既有測試（`test_resume_edit_params_platform.py`、`test_resume_entrypoints.py`、`test_human_channel.py::test_tca08_*`、`test_dataset_launch.py`、`test_http_site_samplesheet.py`、`test_station_launch.py`、`test_launch_platform.py`、`test_keep_submissions.py`） | 允許集合只多了 `CHAT_ARGS`，且只限 launch、cancel、resume、relaunch 四個；其餘 yes 類名稱（`yes`、`confirm`、`confirmed`、`approve`、`approved`、`送出`、`ok`、`agree`、`force`、`skip`、`accept`、`void`）照舊禁止；`forget` 與唯讀工具照舊零 yes 欄位；regex 本身沒被改（比對前先 `props - CHAT_ARGS`）；`test_keep_submissions.py:478`（forget 屬性）未改 | 手動：驗收者讀 diff |
| TC-083 | 規則 A；plan「必須更新的既有斷言」 | 功能 | 無 | 讀 `platform/tests/mcp/snapshots/tools.json` 的 diff | 是用 `test_mcp_contract_tools.py` 既有的重生方法產生；diff 只多出四個工具各兩個欄位，沒有別的變動 | 手動：驗收者讀 diff |
| TC-084 | 規則 A～D；plan「PR 說明逐條寫以前／以後／理由」 | 功能 | PR 已開 | 讀 PR 說明與 ledger | 每一條有意更新的既有斷言都有「以前／以後／理由」；ledger 列出 `git grep "could say yes\|cannot say it for them\|FIXED_SENTENCE"` 的命中；有引用 PITFALLS 重查結果；沒有「必須更新」清單之外的測試被改 | 手動：驗收者讀 PR 說明與 ledger |
| TC-085 | 範圍：測試（新）；`test_scope.py` TC-070 | 功能 | 無 | 跑 `platform/tests/test_scope.py` 與看 `test_chat_confirm.py` 檔頭 | 新檔檔首 40 行內有 `# Nothing existing: <理由，≥15 字>`；測試函式都以 `test_tcm` 開頭且註解寫 TC 編號；`test_scope.py` 綠 | 自動：`platform/tests/test_scope.py` |

<!--
IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
