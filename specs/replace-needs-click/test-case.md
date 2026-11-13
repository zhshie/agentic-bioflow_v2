# 測試案例：存圖若會蓋掉圖庫中既有的圖，必須由本人在表單或確認頁按下確認（replace-needs-click）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
本案沒有 spec.md，計畫（specs/replace-needs-click/plan.md）即規格；維護者原話與六個例子都引自計畫。
本案是 specs/delete-needs-click/ 的直接兄弟，共用說法與裁決（Q1～Q4）照該案。
-->

**規格**：`specs/replace-needs-click/plan.md`　**總覽**：`test-case-overview.md`
**前置**：`specs/delete-needs-click/`（已在 v3）、`specs/mcp-publish-figure/`。

類型只有三種：功能、例外、不在範圍。驗證方式只有「自動」與「手動」。

## 先講好的共用說法

- **安（Ann）**：圖庫的擁有者。**鮑（Bob）**：另一位使用者。安的分析 R，圖庫有 a、b、c 三張圖（`a.png`、`b.png`、`c.png`）；a 有程式碼檔與參數檔、a 在交付包內。`new.png` 是圖庫裡沒有的名稱。
- **圖庫指紋**：安的圖庫資料夾裡所有檔案（`index.json`、圖、`*.code.txt`、`*.params.txt`）的檔名清單加內容雜湊，外加每張圖的 `packed` 狀態。「什麼都沒變」＝前後指紋逐項相同。
- **三個通道**：表單（ELICITED）、確認頁（PAGE，`/c/<申請編號>`，本人登入後按鈕）、對話轉達（CHAT，AI 帶 `request_id` 與 `user_confirmed=true` 再呼叫同一工具）。本案之後，CHAT 對「會取代既有圖」的存圖無效，對新名稱的存圖照舊。
- **取代申請**：`publish_figure` 的申請，提出當下圖庫已有其中任一名稱（bundle 的 `replaces` 非空）。只要清單中有一個名稱會取代，整份申請就是取代申請。
- **新拒絕**：計畫「做什麼」第 2 點的答覆：`state: "refused"`，正式書面語說明「本次存入會取代圖庫中既有的圖，原圖無法復原，須由本人在確認頁按下確認」，中英並列，附該筆申請的確認頁網址（`url` 欄，與第一次提出時給的相同）。
- **測試檔代號**：N＝新增的 `platform/tests/test_replace_needs_click.py`（執行者也可把新測試加進 P；每個測試註解標 TC 編號）；P＝`platform/tests/test_publish_figure_confirm.py`；G＝`platform/tests/test_gallery_change_confirm.py`；S＝`platform/tests/test_studio_publish.py`；M＝`platform/tests/mcp/test_mcp_contract_tools.py`（含快照 `tools.json`）。
- 「Qn」指總覽「我不確定的地方」的問題編號；TC 依我的建議答案撰寫。

## User Story 1 — 對話轉達取代一律拒絕，本人仍可在確認頁核准（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 例 1 前半；計畫做什麼 1、2 | 例外 | 安的客戶端不能跳表單；圖庫有 a、b、c；記下圖庫指紋 | LLM 以 `publish_figure(R, [a.png 新內容＋新程式碼＋新參數])` 提出，得 `request_id`；接著 LLM 自己帶該 `request_id`＋`user_confirmed=true` 再呼叫 | 回 `state: "refused"`；圖庫指紋與呼叫前完全相同（a.png 內容、`a.png.code.txt`、`a.png.params.txt`、`index.json` 逐位元組不變）；沒有 job | 自動：N |
| TC-002 | 例 1「答覆含確認頁網址」；Q2、Q5 | 例外 | 同 TC-001 | 讀拒絕答覆的 `url` 與 `message` | `url` 是該筆申請的確認頁網址，與第一次提出時回的 `url` 逐字相同；`message` 也含該網址 | 自動：N |
| TC-003 | 計畫做什麼 2「正式書面語、中、英」 | 例外 | 同 TC-001 | 讀拒絕答覆的全部字串 | 含「本次存入會取代圖庫中既有的圖」「原圖無法復原」「須由本人在確認頁按下確認」（中文）；同一則訊息內含對應英文；中文不含口語、禁用字（過 `test_web_wording_sweep.py` 的同一組規則）；不含檔案路徑、SQL、token、堆疊；不告訴 LLM 可以或應該以 `user_confirmed=true` 轉達 | 自動：N |
| TC-004 | 計畫做什麼 2「申請維持待確認、不作廢、不消耗」 | 例外 | 同 TC-001 | TC-001 之後查 `confirmations` 與 `jobs` | 該列仍是 pending（不是 void、不是 confirmed）、`channel` 仍為空；`confirmations` 列數與轉達前相同；暫存的圖內容（`bundle_json`）仍在；沒有新增任何 job | 自動：N |
| TC-005 | 例 1 後半 | 功能 | TC-001 拒絕之後，申請仍 pending | 安登入確認頁，按「送出」 | a.png 被新內容取代、程式碼檔與參數檔為新內容；b、c 不變；該列 confirmed、通道 PAGE；沒有 job | 自動：N |
| TC-006 | 例 4 | 例外 | 一筆 pending 的取代 a.png 申請；記下指紋 | LLM 以同一 `request_id`＋`user_confirmed=true` 連續轉達 30 次 | 30 次全是 refused；圖庫指紋不變；該列仍 pending、`confirmations` 沒有多列；之後安在確認頁按送出仍可取代 a.png | 自動：N |
| TC-007 | 例 4「或逾時」 | 例外 | 同 TC-006，轉達 30 次後時鐘撥過 `PENDING_SECONDS` | 再轉達一次；安再開確認頁 | 轉達得「已逾時」的現有拒絕（不帶新拒絕的網址）；確認頁回現有逾時說明、不寫入；圖庫指紋不變 | 自動：N |
| TC-008 | Q5（申請在等待但圖庫變了） | 例外 | 一筆 pending 的取代 a.png 申請；之後 a.png 已被網頁刪除按鈕刪掉 | LLM 轉達；之後安在確認頁按送出 | 轉達仍得新拒絕、申請仍 pending；確認頁按下後回現有「圖庫已變動」的說明（409），沒有 500、沒有堆疊；a.png 沒有被建回；圖庫沒有多餘變動 | 自動：N |
| TC-009 | Q5（沒帶 request_id） | 例外 | 圖庫有 a.png；沒有任何申請 | LLM 呼叫 `publish_figure(R, [a.png], user_confirmed=true)`，不帶 `request_id` | 回 refused、不建任何 `confirmations` 列、圖庫指紋不變；訊息指向確認頁／重新提出，不教 AI「等本人在聊天裡回覆後再帶 user_confirmed=true」 | 自動：N |
| TC-010 | 計畫做什麼 3 | 功能 | 客戶端不能跳表單；圖庫有 a.png | LLM 第一次呼叫 `publish_figure(R, [a.png])` | `state: "pending"`，有 `request_id`、`url`、`summary`（含「覆蓋既有同名圖」）；`message` 只叫本人打開網址、登入、按確認，並說明原圖無法復原；`message` 不含 `user_confirmed`，也不叫 LLM 帶 `request_id` 再呼叫；圖庫不變 | 自動：N |
| TC-011 | 計畫做什麼 1「bundle 的 replaces 非空」；Q6 | 例外 | 圖庫有 a.png、沒有 new.png | LLM 以 `[new.png, a.png]` 兩張一起提出，再自己轉達 | 整份申請視為取代申請：轉達得新拒絕（附網址）；new.png 沒有被存入、a.png 不變；申請仍 pending；之後安在確認頁按送出則兩張都存入 | 自動：N |

## User Story 2 — 其他無效的轉達，拒絕與現在相同（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 例 6；Q5 | 例外 | 安有一筆 pending 取代申請 | 鮑（或沒有登入使用者的連線）以安的 `request_id`＋`user_confirmed=true` 呼叫；另以 `"f"*32`、`"x"`、`"../../etc/passwd"`、100 個 `"a"` 呼叫 | 都與現在相同地 refused（「不是目前這位使用者提出的」「查無這個申請編號」等）；答覆不含安的確認頁網址、不含任何圖名、沒有堆疊；不建申請列；安的申請列與圖庫不變 | 自動：N |
| TC-013 | 例 6；Q5 | 例外 | 安有一筆 pending 取代 a.png 申請、一筆 pending 打包申請與一筆 pending 刪除申請 | `publish_figure` 帶打包的 `request_id`、帶刪除的 `request_id`；帶取代申請的 `request_id` 但把內容改成另一張圖或另一個 `run_id` | 都與現在相同地 refused（別種申請／「內容與當初給本人看的不同」）；不是新拒絕、不帶網址；三筆申請仍 pending；圖庫不變 | 自動：N |
| TC-014 | 例 6；Q5 | 例外 | 一筆取代申請已逾時（撥過 `PENDING_SECONDS`）；另一筆被表單按「否」而作廢 | 各自以 `request_id`＋`user_confirmed=true` 轉達 | 逾時那筆得現有「逾時」拒絕、作廢那筆得現有「作廢」拒絕；兩者都不是新拒絕、不帶網址；圖庫不變 | 自動：N |
| TC-015 | Q5（已確認過的申請） | 例外 | 取代 a.png 的申請已由本人在確認頁按送出並成功；之後 a.png 又被另一筆申請（PAGE）換成別的內容 | LLM 以舊申請的 `request_id`＋`user_confirmed=true` 轉達（相同內容） | 回現有的「已存入圖庫」（與 `test_f4` 重放相同的說法），不重做、不是新拒絕、不帶網址；a.png 仍是後一筆的內容；圖庫指紋不變 | 自動：N |

## User Story 3 — 本人自己按才生效：表單與確認頁照舊（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 例 3 | 功能 | 客戶端支援表單；安的連線；圖庫有 a.png | LLM 提出取代 a.png；表單跳出，安按「是」 | a.png 被新內容取代、程式碼檔與參數檔為新內容；其餘不變；通道 ELICITED；沒有 job；`index.json` 的 a.png 為新的 `request_id` 與 `packed: false` | 自動：N |
| TC-017 | 計畫做什麼 1；既有行為 | 例外 | 客戶端支援表單；圖庫有 a.png | LLM 提出取代 a.png；安在表單按「否」 | 回「未送出」並說明原因；圖庫指紋不變；該申請 void | 自動：N |
| TC-018 | 既有行為；計畫「不做」 | 例外 | 本機 stdio 客戶端，沒有登入使用者、沒有表單；圖庫有 a.png | LLM 呼叫取代 a.png 的 `publish_figure` | 與現在相同：回「這裡沒有人可以確認」的說明、圖庫不變、不留任何申請列 | 自動：N |

## User Story 4 — 存新圖維持現狀：對話轉達可用（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 例 2；計畫做什麼 5 | 功能 | 客戶端不能跳表單；圖庫有 a、b、c、沒有 new.png | LLM 以 new.png 提出；本人在聊天回答後，LLM 帶 `request_id`＋`user_confirmed=true` 轉達 | 照常存入：new.png 與其程式碼檔、參數檔都在 `index.json`；該列 confirmed、通道 CHAT；a、b、c 指紋不變；沒有 job。既有的 CHAT 新名稱測試（P 的 `…[CHAT]`、`test_f4_…`、G 的 `test_publish_figure_keeps_its_own_writer`）不改一字且通過 | 自動：N、P、G |
| TC-020 | 計畫做什麼 5；Q5 | 功能 | 同 TC-019，只提出不轉達 | 讀 new.png 第一次答覆的 `message` | 仍含「用同樣的參數加上 request_id=… 與 user_confirmed=true 再呼叫」的說法，與改動前逐字相同；沒有提到取代 | 自動：N |

## User Story 5 — 提出時不存在、核准時已有同名圖（計畫第 4 點，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 例 5；Q1（CHAT） | 例外 | 客戶端不能跳表單；LLM 以 new.png（內容 X）提出，`replaces` 為空；之後另一筆申請（內容 Y）由本人在確認頁存入 new.png | LLM 對第一筆帶 `request_id`＋`user_confirmed=true` 轉達 | 回 `state: "refused"`，訊息為現有的「圖庫在申請送出後有變動…沒有寫入任何圖」；不帶網址、無堆疊；new.png 仍是內容 Y，`index.json` 與兩個附屬檔逐位元組不變；第一筆申請為 void（既有行為，不是 pending）；沒有 job | 自動：N |
| TC-022 | 例 5；Q1（PAGE、ELICITED） | 例外 | 同 TC-021 的前置，通道換成 PAGE；再一個換成 ELICITED（表單回答前，圖庫被另一筆寫入 new.png） | PAGE：安按第一筆的送出。ELICITED：表單回答「是」 | PAGE 回 409 與現有「圖庫已變動」說明；ELICITED 回「未送出」與同一原因；兩者 new.png 都仍是內容 Y、申請 void、沒有 500。既有的 `test_f6_a_request_that_did_not_say_replaces_does_not_replace` 不改一字且通過 | 自動：N、P |
| TC-023 | 例 5；既有 F6 | 例外 | 客戶端不能跳表單；兩筆 pending 申請都以 new.png 提出（內容 X、Y，圖庫皆無 new.png） | 依序以 CHAT 轉達第一筆、第二筆 | 第一筆存入；第二筆 refused（圖庫已變動）、為 void；new.png 為內容 X，沒有被 Y 取代；沒有任何轉達造成取代 | 自動：N |

## User Story 6 — 工具說明照實（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | 計畫做什麼 6；Q3 | 功能 | 列出工具清單 | 讀 `publish_figure` 的 `description` | 照實說明：新名稱可在本人於聊天回答後轉達；會取代既有的圖時 `user_confirmed` 無效，須由本人在表單或確認頁按下確認、原圖無法復原；長度 ≤ 600；`test_descriptions_within_limit`、各 aspect 檢查通過；`OVER_LIMIT`、`ASPECT_GAPS`、`UNDESCRIBED_PARAMS` 沒有新增項目 | 自動：M |
| TC-025 | 計畫做什麼 6；Q4 | 功能 | 列出輸入 schema 與快照 | 讀 `publish_figure` 的 `request_id`、`user_confirmed` 參數說明 | 專用說明寫明「新名稱可轉達；會取代既有的圖時無效」，不再是共用的「True only after the person themselves answered yes…」單句；`required` 仍為 `["run_id","figures"]`，參數名單不變；`tools.json` 只有 publish_figure 這兩段說明變動，ledger 載明（R1） | 自動：M |
| TC-026 | 計畫做什麼 8；Q7 | 功能 | 同上 | 比對其他八個寫入工具與 pack_figures、delete_figure 的描述、參數說明、快照段落與標註；publish_figure 的 `destructive_hint`、`idempotent_hint`、`read_only_hint` | 其他工具逐字相同（快照無 diff）；publish_figure 標註與改動前相同（不在本案改，ledger 寫為已知限制） | 自動：M |

## User Story 7 — RStudio 指令不受影響（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-027 | 計畫做什麼 7 | 功能 | 假平台（FakeSite）對既有名稱回 pending 與確認頁網址 | 跑 `abf-platform publish-figure` 對一個圖庫已有的名稱 | 工具呼叫的參數只有 `run_id`、`figures`，沒有 `user_confirmed`、`request_id`；輸出為檔名、大小、「尚未存入、請打開連結按下按鈕」與連結，立刻以 0 結束，從不說已存入；`studio_cli.py`、`studio_remote.py`、`scripts/intro` 相對 `origin/v3` 無改動；`test_studio_publish.py` 不改一字且通過 | 自動：S、`git diff` |

## User Story 8 — 其他種類與其他工具一字不動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-028 | 計畫做什麼 8 | 功能 | 無 | 跑 `test_chat_confirm.py`、`test_cleanup_store.py`、forget 相關測試、G 中刪除與打包的 `test_dnc_*` 與既有案例；打包經 CHAT 轉達、刪除經 CHAT 轉達 | 全綠；上列檔案相對 `origin/v3` 沒有任何改動；打包 CHAT 仍生效、刪除 CHAT 仍被拒（delete-needs-click 的行為不變）；launch、cancel、resume、relaunch、forget 行為不變 | 自動：`git diff` 與上列測試 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 計畫「不做」：不保留被取代的舊版本 | 不在範圍 | 圖庫有 a.png；PAGE 取代成功 | 列出圖庫資料夾 | 只有新的 a.png、`a.png.code.txt`、`a.png.params.txt`（若新內容有）、b、c 與 `index.json`；沒有舊版備份、版本資料夾或 `.bak`、`.old`；沒有新增「還原」工具或路由 | 自動：N |
| TC-030 | 計畫「不做」：不碰哪些檔 | 不在範圍 | 本案完成 | `git diff origin/v3...HEAD --stat` | 只有 `actions/__init__.py`、`actions/figures.py`、`mcp_server.py`、`docs/`、`CHANGELOG.md`、`platform/tests/`（含快照）、`specs/replace-needs-click/`；`confirm.py`、`store.py`、`.github/`、`hooks/`、憲法、`plugin.json`、`platform/abf_station/`、`jobs.py`、CSS 都無改動 | 自動：`git diff` 檢查（寫進 ledger） |
| TC-031 | 計畫「不做」：不改其他種類、逾時、待確認上限；不新增路由、相依；聊天不提供 | 不在範圍 | 同上 | 跑 `test_confirm_constants_and_the_job_kinds_are_unchanged`、`test_pending_limit_and_expiry_are_the_existing_ones`、`test_chat_tools.py`（`CHAT_EXCLUDED` 恰為 publish_figure、pack_figures、delete_figure）；比對 `web.py` 路由表與相依檔 | 常數、上限、job 種類、路由表、相依檔與改動前相同；瀏覽器內建聊天仍不提供這三個工具；這些測試未被改且通過 | 自動 |

## 既有測試的改動紀律

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 計畫「測試怎麼做」：被反轉的既有測試由合約逐條點名 | 功能 | 本案完成 | 對照 `git diff origin/v3...HEAD -- platform/tests` 與 ledger | 合約查證過：**沒有任何既有測試期待「經對話轉達取代既有圖」成功**（對話轉達的 publish 案例都在空圖庫、新名稱），所以**沒有既有測試的斷言可以被反轉**。既有檔案被改的只有 R1：`tools.json` 中 publish_figure 的 `request_id` 與 `user_confirmed` 兩段說明。其他測試的變動只能是新增（`test_rnc_*` 之類，註解標 TC 編號）。若執行者發現還有需要反轉的測試，須停手回報，不得自行改 | 自動：`git diff`（寫進 ledger，驗收者讀） |
| TC-033 | 驗收規則「弱化測試」 | 例外 | 同上 | 對 TC-032 以外的所有測試檔比對 `origin/v3`；比對 `spec`／`test-case*.md` | 沒有其他斷言被刪、放寬、skip 或改期待值；`test_publish_figure_confirm.py` 與 `test_gallery_change_confirm.py` 的既有函式（尤其 F4、F5、F6、N4、`test_model_cannot_confirm_itself`、`test_documents_describe_the_tool`）逐字不動；`plan.md` 以外的 `specs/replace-needs-click/` 的 `test-case*.md` 在實作期間無編輯 | 自動：`git diff` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | 安全網：「模型自己的回答從來不算本人的答覆」；原則一第 2 點通道規則 | 例外 | 跑完 TC-001～023 的情境 | 查整個測試資料庫的 `confirmations`，逐列解析 `bundle_json` 的 `replaces` | 沒有任何一列 kind 為 publish_figure、`replaces` 非空、而 `channel` 是 CHAT 的 confirmed 列；取代只可能由 ELICITED／PAGE 的 confirmed 列造成；TC-021、TC-023 的 CHAT 轉達沒有寫過任何檔 | 自動：N |
| TC-035 | 安全網只收緊、不放寬 | 功能 | 本案完成 | 跑憲法所指的檢查：`test_chat_confirm.py`（`test_tcm_*`）、`test_human_channel.py`（`test_tch09_*`）、`test_confirm_page.py` | 全綠且未被改；新名稱存圖與打包的 CHAT 仍被接受，即只有「取代」被收緊 | 自動 |
| TC-036 | 風險 L 的證明（計畫「測試怎麼做」） | 功能 | 本案完成 | 讀 `specs/replace-needs-click/ledger.md` | 寫明改了哪幾個函式、哪幾行；為什麼不需動 `confirm.py`（拒絕發生在 `_ask` 呼叫 `confirm.approve` 之前，只讀、不消耗申請）；計畫第 4 點的實況（CHAT 為 refused 並作廢、PAGE 為 409）；publish_figure 描述與參數說明的字數與選擇；R1 的舊值、新值、原因；`destructive_hint` 未改為已知限制；`tests/mcp/` 在本機實際跑的結果（該目錄在 `fable/mcp-tests-in-ci` 合併前不在 CI） | 手動：讀 `specs/replace-needs-click/ledger.md` |

## 實機走通與文件（手動）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | 例 1、例 2、例 3；計畫做什麼 9 | 功能 | 一個運行中的平台、一個真實 MCP 客戶端、安的圖庫有 a、b、c | 對 AI 說「用 a.png 存這張新圖」；對 AI 回答「確認」；看圖庫。再重來，這次打開 AI 給的網址登入並按「送出」。最後對 AI 說「存一張 new.png」並回答「確認」 | 說「確認」之後 a.png 仍是舊圖，AI 回報須到確認頁按確認並給網址；按下確認頁的鈕後 a.png 換成新圖；new.png 在聊天說「確認」即存入 | 手動：`docs/TESTING.md`（新增的一條） |
| TC-038 | 維護者用字裁示（中文顯示不能口語） | 功能 | 同 TC-037 | 看拒絕答覆的中文與英文、第一次答覆、確認頁 | 維護者能讀懂：為什麼不能在聊天裡確認、原圖無法復原、下一步要去哪裡；用詞正式書面；沒有工作編號、沒有程式碼用語 | 手動：`docs/TESTING.md` |
| TC-039 | 計畫做什麼 9 | 功能 | 本案完成 | 讀 `docs/PLATFORM.md` publish_figure 段與確認通道段、`docs/TESTING.md` 新增的一條、`CHANGELOG.md` | PLATFORM.md 說取代只能表單或確認頁、新名稱仍可轉達，並更正「（or answers yes in the chat）」一類舊說法使其不誤導；TESTING.md 新條具體可照做；CHANGELOG 有一行；`test_documents_describe_the_tool` 的既有斷言仍成立；三處都沒有留下「取代既有圖可帶 `user_confirmed=true`」的舊說法 | 手動：`docs/TESTING.md`（文件逐項讀） |
