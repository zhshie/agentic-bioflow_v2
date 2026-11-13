# 測試案例：刪除圖庫中的圖，必須由本人在表單或確認頁按下確認（delete-needs-click）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
本案沒有 spec.md，計畫（specs/delete-needs-click/plan.md）即規格；維護者原話與五個例子都引自計畫。
-->

**規格**：`specs/delete-needs-click/plan.md`　**總覽**：`test-case-overview.md`
**前置**：第 3 片 `specs/mcp-gallery-actions/`（已在 v3）。

類型只有三種：功能、例外、不在範圍。驗證方式只有「自動」與「手動」。

## 先講好的共用說法

- **安（Ann）**：圖庫的擁有者。**鮑（Bob）**：另一位使用者。安的分析 R，圖庫有 a、b、c 三張圖（`a.png`、`b.png`、`c.png`）；a 有程式碼檔與參數檔、a 在交付包內。
- **圖庫指紋**：安的圖庫資料夾裡所有檔案（`index.json`、圖、`*.code.txt`、`*.params.txt`）的檔名清單加內容雜湊，外加交付包名單。「什麼都沒變」＝前後指紋逐項相同。
- **三個通道**：表單（ELICITED，用戶端跳出的視窗）、確認頁（PAGE，`/c/<申請編號>`，本人登入後按鈕）、對話轉達（CHAT，AI 帶 `request_id` 與 `user_confirmed=true` 再呼叫同一工具）。本案之後，CHAT 對刪除無效，對打包與其他種類照舊。
- **「新拒絕」**：計畫「做什麼」第 2 點的答覆：正式書面語說明「刪除無法復原，須由本人在確認頁按下確認」，中英並列，附該筆申請的確認頁網址（與第一次提出時給的相同）。
- 驗證方式欄的測試檔：A＝`platform/tests/test_gallery_change_confirm.py`、B＝`platform/tests/test_gallery_change.py`、C＝`platform/tests/mcp/test_mcp_contract_tools.py`（快照）、D＝`platform/tests/test_gallery_change_page.py`。執行者每個自動測試在註解標明 TC 編號。
- 「Qn」指總覽「我不確定的地方」的問題編號；TC 依我的建議答案撰寫。

## User Story 1 — 對話轉達刪除一律拒絕，本人仍可在確認頁核准（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 例 1 前半；計畫做什麼 2 | 例外 | 安的客戶端不能跳表單；記下圖庫指紋 | LLM 呼叫 `delete_figure(R, "a.png")` 得 `request_id`；接著 LLM 自己帶該 `request_id`＋`user_confirmed=true` 再呼叫 | 回 `state: "refused"`；圖庫指紋與呼叫前完全相同（a 的圖、程式碼檔、參數檔都還在，a 仍在交付包）；沒有 job | 自動：A |
| TC-002 | 例 1「答覆含確認頁網址」；Q1 | 例外 | 同 TC-001 | 讀 TC-001 拒絕答覆的 `url` 與 `message` | 答覆含該筆申請的確認頁網址，與第一次提出時回的 `url` 逐字相同 | 自動：A |
| TC-003 | 計畫做什麼 2「正式書面語、中、英」 | 例外 | 同 TC-001 | 讀拒絕答覆的 `message` | 含「刪除無法復原」與「須由本人在確認頁按下確認」（中文）；同一則訊息內含對應英文（說刪除無法復原、須由本人在確認頁按下確認）；中文不含口語、禁用字（過 `test_web_wording_sweep.py` 的同一組規則） | 自動：A |
| TC-004 | 計畫做什麼 2「申請維持待確認、不作廢、不消耗」 | 例外 | 同 TC-001 | TC-001 之後查 `confirmations` | 該列仍是 pending（不是 void、不是 confirmed）、`channel` 仍為空；`confirmations` 列數與 TC-001 轉達前相同；沒有新增任何 `jobs` 列 | 自動：A |
| TC-005 | 例 1 後半 | 功能 | TC-001 拒絕之後，申請仍 pending | 安登入確認頁，按「確認刪除」 | a 的圖檔、程式碼檔、參數檔都不見；a 不在 `index.json`、不在交付包；b、c 不變；該列 confirmed、通道 PAGE；沒有 job | 自動：D、A |
| TC-006 | 例 4 | 例外 | 一筆 pending 的刪除 a 申請；記下指紋 | LLM 以同一 `request_id`＋`user_confirmed=true` 連續轉達 30 次 | 30 次全是 refused；圖庫指紋不變（一張圖都沒少）；該列仍 pending、`confirmations` 沒有多列；之後安在確認頁按確認仍可刪除 a | 自動：A |
| TC-007 | 例 4「或等它逾時」 | 例外 | 同 TC-006，轉達 30 次後時鐘往後撥過 `PENDING_SECONDS` | 再轉達一次；安再開確認頁 | 轉達得到「已逾時」的現有拒絕（不帶新拒絕的網址）；確認頁 410 逾時；圖庫指紋不變 | 自動：A、D |
| TC-008 | Q3 | 例外 | 一筆 pending 的刪除 a 申請；之後 a 已被網頁按鈕刪掉（圖庫已變） | LLM 轉達；之後安在確認頁按確認 | 轉達得到新拒絕，申請仍 pending；確認頁按下後回「圖庫已變動」的現有說明，沒有 500、沒有堆疊；圖庫沒有多餘變動 | 自動：A |
| TC-009 | Q4 | 例外 | 沒有任何申請 | LLM 呼叫 `delete_figure(R, "a.png", user_confirmed=true)`，不帶 `request_id` | 回 refused、不建任何 `confirmations` 列、圖庫不變；訊息不再教 AI「等本人在聊天裡回覆後再帶 user_confirmed=true」，改為指向確認頁／重新提出 | 自動：A |
| TC-010 | 計畫做什麼 3；Q4 | 例外 | 同 TC-001 | 檢查所有刪除的拒絕與等待答覆的 `message` | 沒有任何一句告訴 LLM 可以或應該以 `user_confirmed=true` 轉達；不含檔案路徑、SQL、token、堆疊 | 自動：A |

## User Story 2 — 其他無效的轉達，拒絕與現在相同（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 例 5；Q1 | 例外 | 安有一筆 pending 刪除申請 | 鮑（或沒有登入使用者的連線）以安的 `request_id`＋`user_confirmed=true` 呼叫 | 與現在相同的「這個申請不是目前這位使用者提出的」拒絕；答覆不含安的確認頁網址、不含任何圖名；安的申請列不變、圖庫不變 | 自動：A |
| TC-012 | 例 5 | 例外 | 安有一筆 pending 打包申請與一筆 pending 刪除申請 | `delete_figure` 帶打包的 `request_id`；`pack_figures` 帶刪除的 `request_id`（都帶 `user_confirmed=true`） | 兩個都與現在相同地 refused；圖庫不變；兩筆申請仍 pending；答覆不含對方申請的網址 | 自動：A |
| TC-013 | 例 5；第 3 片 TC-037 | 例外 | 無 | `delete_figure` 帶 `request_id` 為 `"f"*32`、`"x"`、`"../../etc/passwd"`、100 個 `"a"`，加 `user_confirmed=true` | 都與現在相同地 refused，沒有堆疊、沒有網址；不建任何申請列 | 自動：A |
| TC-014 | 例 5；第 3 片 TC-036 | 例外 | 一筆 pending 刪除 a 的申請 | 帶該 `request_id`＋`user_confirmed=true`，但 `name` 改成 `b.png` | 與現在相同的「內容與當初給本人看的不同」拒絕；a、b 都還在；不是新拒絕、不帶網址 | 自動：A |
| TC-015 | 例 5；Q1 | 例外 | 一筆刪除申請已逾時（撥過 `PENDING_SECONDS`）；另一筆被表單按「否」而作廢 | 各自以 `request_id`＋`user_confirmed=true` 轉達 | 逾時那筆得現有「逾時」拒絕、作廢那筆得現有「作廢」拒絕；兩者都不是新拒絕、不帶網址；圖庫不變 | 自動：A |
| TC-016 | Q2；第 3 片 TC-038/039 | 例外 | 刪除 a 已由本人在確認頁按確認並成功；之後 a.png 又被 `publish_figure` 存了一張新的（同名） | LLM 以舊的刪除申請的 `request_id`＋`user_confirmed=true` 轉達 | 回現有的「先前已經確認並執行過…請重新查詢」，不重述結果、不含圖名；新的 a 還在；圖庫指紋不變 | 自動：A |

## User Story 3 — 本人自己按才生效：表單與確認頁照舊（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 例 2 | 功能 | 客戶端支援表單；安的連線 | LLM 提出刪除 a；表單跳出，安按「是」 | a 的圖檔、程式碼檔、參數檔都不見；a 不在 `index.json`、不在交付包；其餘不變；通道 ELICITED；沒有 job | 自動：A |
| TC-018 | 計畫做什麼 1（PAGE） | 功能 | 客戶端不能跳表單；刪除 a 的 pending 申請 | 安在確認頁按「確認刪除」 | 同 TC-017；通道 PAGE | 自動：A、D |
| TC-019 | 計畫做什麼 1；第 3 片 TC-004 | 例外 | 客戶端支援表單 | LLM 提出刪除 a；安在表單按「否」 | 回「未送出」並說明原因；圖庫指紋不變；該申請 void | 自動：A |
| TC-020 | 計畫做什麼 3 | 功能 | 客戶端不能跳表單；安的連線 | LLM 第一次呼叫 `delete_figure(R, "a.png")` | `state: "pending"`，有 `request_id`、`url`、摘要；`message` 只叫本人打開網址、登入、按確認；`message` 不含 `user_confirmed`，也不叫 LLM 帶 `request_id` 再呼叫；圖庫不變 | 自動：A |
| TC-021 | 第 3 片 TC-005；計畫「不做」 | 例外 | 本機 stdio 客戶端，沒有登入使用者、沒有表單 | LLM 呼叫 `delete_figure` | 與現在相同：回「這裡沒有人可以確認」的說明、沒有任何圖被改、不留任何申請列 | 自動：A |

## User Story 4 — 工具說明照實（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 計畫做什麼 4 | 功能 | 列出工具清單 | 讀 `delete_figure` 的 `description` | 說明刪除不可復原、必須由本人在表單或確認頁按下確認，`user_confirmed` 對刪除無效；不再有「only after they answered in this chat call again with request_id and user_confirmed=true」之類教 AI 轉達的句子；仍含 one figure，長度小於 1200；`destructive_hint` 仍為 True | 自動：B、A |
| TC-023 | 計畫做什麼 4；Q5 | 功能 | 列出工具清單與輸入 schema | 讀 `delete_figure` 的 `request_id`、`user_confirmed` 參數說明 | 若參數仍在 schema（建議），說明明寫「對刪除無效」，不再寫「True only after the person answered yes in the chat」；`required` 仍為 `["run_id","name"]`；快照 `tools.json` 只有 delete_figure 這兩段說明變動，ledger 載明 | 自動：C、B |
| TC-024 | 計畫做什麼 5 | 功能 | 同上 | 讀 `pack_figures` 的 `description` 與兩個參數說明，以及其他八個寫入工具 | 與改動前逐字相同（快照中它們的段落沒有 diff） | 自動：C、B |

## User Story 5 — 打包與其他種類一字不動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 例 3 | 功能 | 客戶端不能跳表單；LLM 提出 `pack_figures(R, ["a.png","b.png"])`，本人已在聊天回答 | LLM 帶 `request_id`＋`user_confirmed=true` 再呼叫 | 照常生效：交付包恰為 a、b，c 仍在圖庫；該列 confirmed、通道 CHAT；沒有 job | 自動：A |
| TC-026 | 計畫做什麼 5 | 功能 | 同上，只提出不轉達 | 讀打包第一次答覆的 `message` | 仍含「用同樣的參數加上 request_id=… 與 user_confirmed=true 再呼叫 pack_figures」的說法，與改動前相同 | 自動：A |
| TC-027 | 計畫做什麼 5 | 功能 | `publish_figure` 的 pending 申請 | CHAT 轉達 | 照常存圖；通道 CHAT；既有 publish 測試不改一字 | 自動：A |
| TC-028 | 計畫做什麼 5「launch、cancel、resume、relaunch、clean_work、forget」 | 功能 | 無 | 跑 `platform/tests/test_chat_confirm.py`、`test_cleanup_store.py` 與 forget 相關測試 | 全綠；這些檔案相對 `origin/v3` 沒有任何改動（`git diff origin/v3...HEAD -- <這些檔>` 為空） | 自動 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 計畫「不做」：不碰哪些檔 | 不在範圍 | 本案完成 | `git diff origin/v3...HEAD --stat` | 只有 `actions/__init__.py`、`actions/figures.py`、`mcp_server.py`、`docs/`、`CHANGELOG.md`、`platform/tests/`（含快照）、`specs/delete-needs-click/`；`confirm.py`、`store.py`、`.github/`、`hooks/`、憲法、`plugin.json`、`platform/abf_station/`、`jobs.py`、CSS 都無改動 | 自動：`git diff` 檢查（寫進 ledger） |
| TC-030 | 計畫「不做」：不新增路由、相依；網頁按鈕不動 | 不在範圍 | 同上 | 比對 `web.py` 的路由表與相依檔；跑第 3 片網頁按鈕（`POST /run/figure/delete`）既有測試 | 路由表、相依檔無變動；網頁按鈕刪除照舊可用 | 自動：D 與既有網頁測試 |
| TC-031 | 計畫「不做」：不改逾時與待確認上限 | 不在範圍 | 同上 | 跑 `test_confirm_constants_and_the_job_kinds_are_unchanged`；比對 `PENDING_SECONDS` 與上限常數 | 常數與 job 種類與改動前相同；該測試未被改 | 自動：A |
| TC-032 | 計畫「不做」：瀏覽器內建聊天仍不提供這兩個工具 | 不在範圍 | 同上 | 跑 `test_chat_tools.py`（TC-097） | `CHAT_EXCLUDED` 仍恰為 publish_figure、pack_figures、delete_figure；聊天沒有被提供它們；該測試未被改 | 自動 |

## 既有測試的改動紀律

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-033 | 本案刻意反轉第 3 片的行為 | 功能 | 本案完成 | 對照 `git diff origin/v3...HEAD -- platform/tests` 與 ledger | 既有測試被改的只有：R1 `test_delete_on_each_channel` 的 CHAT 分支（改為斷言被拒、圖庫不變；ELICITED、PAGE 分支不動）；R2 `test_a_replayed_yes_does_not_run_twice` 刪除半段（改由 PAGE 確認，「新同名 a 不被誤刪」的斷言保留）；R3 `test_a_figure_deleted_in_between_is_a_plain_refusal`（轉達得新拒絕，「圖庫已變動」改由 PAGE 驗）；R4 `test_a2_a_reused_request_id_does_not_restate_the_result` 刪除那一輪（第一次確認改用 PAGE，斷言保留）；R5 `test_the_tool_descriptions_say_the_three_things` 對 delete 的 `user_confirmed`／`only after` 斷言；R6 `tools.json` 快照的 delete_figure 兩段說明。ledger 對每一條寫舊值、新值、原因；被反轉的測試是改成相反斷言，不是刪除、不是 skip | 自動：`git diff`（寫進 ledger，驗收者讀） |
| TC-034 | 驗收規則「弱化測試」 | 例外 | 同上 | 對 TC-033 以外的所有測試檔比對 `origin/v3`；比對 `spec`／`test-case*.md` | 沒有其他斷言被刪、放寬、skip 或改期待值；`plan.md` 以外的 `specs/delete-needs-click/` 的 `test-case*.md` 在實作期間無編輯；`test_gallery_change_confirm.py` 的逾時（約 92 行）、他種編號（約 206 行）、內容改過（約 223 行）、單帶 `user_confirmed`（約 166 行）案例逐字不動 | 自動：`git diff` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 安全網：「模型自己的回答從來不算本人的答覆」；原則一第 2 點通道規則 | 例外 | 跑完 TC-001～016 的情境 | 查整個測試資料庫的 `confirmations` | 沒有任何一列 gallery_change 且 action 為 delete 的申請，`channel` 是 CHAT 或 state 是 confirmed 而通道為空；刪除只可能由 ELICITED／PAGE 的 confirmed 列造成；寫圖庫的函式沒有被 CHAT 路徑呼叫過 | 自動：A |
| TC-036 | 安全網只收緊、不放寬 | 功能 | 本案完成 | 跑憲法所指的檢查：`platform/tests/test_chat_confirm.py`（`test_tcm_*`）、`test_human_channel.py`（`test_tch09_*`）、`test_confirm_page.py` | 全綠且未被改；打包的 CHAT 仍被接受（TC-025），即只有刪除被收緊 | 自動 |
| TC-037 | 風險 L 的證明（計畫「測試怎麼做」） | 功能 | 本案完成 | 讀 ledger | 寫明改了哪幾個函式、哪幾行、為什麼不需動 `confirm.py`（拒絕發生在 `_ask` 呼叫 `confirm.approve` 之前或等同之處，且不消耗申請）；選擇保留參數（或移除）的理由；R1～R6 的舊值、新值、原因 | 手動：讀 `specs/delete-needs-click/ledger.md` |

## 實機走通與文件（手動）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | 例 1、例 2；計畫做什麼 6 | 功能 | 一個運行中的平台、一個真實 MCP 客戶端、安的圖庫有 a、b、c | 對 AI 說「刪掉 a」；對 AI 回答「確認」；看圖庫。再重來一次，這次打開 AI 給的網址登入並按「確認刪除」 | 在聊天說「確認」之後 a 還在，AI 回報須到確認頁按確認並給網址；按下確認頁的鈕後 a、它的程式碼檔、參數檔不見、交付包不再列 a | 手動：`docs/TESTING.md`（第 3 片第 2 條改寫處） |
| TC-039 | 維護者用字裁示（一樣要注意中文顯示不能口語） | 功能 | 同 TC-038 | 看拒絕答覆的中文與英文，看確認頁 | 維護者能讀懂：為什麼不能在聊天裡確認、下一步要去哪裡；用詞正式書面；沒有工作編號、沒有程式碼用語 | 手動：`docs/TESTING.md` |
| TC-040 | 計畫做什麼 6 | 功能 | 本案完成 | 讀 `docs/PLATFORM.md` 該工具與確認通道段落、`docs/TESTING.md` 第 3 片刪除那一條、`CHANGELOG.md` | PLATFORM.md 說刪除只能表單或確認頁、打包仍可轉達；TESTING.md 該條改為「在確認頁按確認」且具體可照做；CHANGELOG 有一行；三處都沒有留下「刪除可帶 `user_confirmed=true`」的舊說法 | 手動：`docs/TESTING.md`（文件逐項讀） |
