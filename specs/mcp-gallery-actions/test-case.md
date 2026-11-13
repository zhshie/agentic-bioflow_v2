# 測試案例：MCP 工具 pack_figures 與 delete_figure（圖庫第 3 片：AI 經確認通道代使用者打包與刪除）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
本案沒有獨立 spec.md，計畫（specs/mcp-gallery-actions/plan.md）即規格；維護者原話與六個例子都引自計畫。
-->

**規格**：`specs/mcp-gallery-actions/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：功能、例外、不在範圍。驗證方式只有「自動」與「手動」。

## 先講好的共用說法

- **安（Ann）**：圖庫的擁有者。**鮑（Bob）**：另一位使用者。安的分析 R，圖庫有 a、b、c 三張圖（實際檔名 `a.png`、`b.png`、`c.png`），原本只有 c 在交付包內；a 有程式碼檔與參數檔。
- **圖庫指紋**：安的圖庫資料夾裡所有檔案（`index.json`、圖、`*.code.txt`、`*.params.txt`）的檔名清單加內容雜湊。「什麼都沒變」＝前後指紋逐項相同。
- **三個通道**：表單（ELICITED，MCP 客戶端跳出的視窗）、確認頁（PAGE，`/c/<申請編號>`）、聊天（CHAT，使用者在聊天裡親口說「確認」，AI 帶 `request_id` 與 `user_confirmed=true` 再呼叫一次）。
- 驗證方式欄的測試檔名為建議名稱：A＝`platform/tests/test_gallery_change.py`、B＝`platform/tests/test_gallery_change_confirm.py`、C＝`platform/tests/test_gallery_change_page.py`、D＝`platform/tests/test_cleanup_store.py`（延伸）。執行者每個自動測試在註解標明 TC 編號。
- 「Pn」指總覽「我不確定的地方」的問題編號；TC 依我的建議答案撰寫。

## User Story 1 — 本人回答之前，什麼都不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 【機器可驗】 | 計畫目標；憲法安全網；例 1 | 例外 | 安的圖庫有 a、b、c（c 在包內）；尚無人回答；記下圖庫指紋 | LLM 呼叫 `pack_figures(R, ["a.png","b.png"])`，不帶 `request_id`、不帶 `user_confirmed` | 回 `state: "pending"`，有 `request_id`、確認網址與摘要；圖庫指紋與呼叫前完全相同；`confirmations` 只多一列 pending、種類 `gallery_change`；`jobs` 沒有新列 | 自動：B |
| TC-002 【機器可驗】 | 計畫目標；例 2 | 例外 | 同上；a 在包內 | LLM 呼叫 `delete_figure(R, "a.png")`，不帶 `request_id`、`user_confirmed` | 回 `pending`；圖庫指紋不變（a 的圖、程式碼、參數檔都還在）；只多一列 pending；`jobs` 無新列 | 自動：B |
| TC-003 【機器可驗】 | 計畫「作法 1」確認頁通道 | 例外 | 已有一筆 pending 的打包申請 | 安登入、只「打開」確認頁（GET `/c/<編號>`），不按按鈕 | 頁面顯示內容；圖庫指紋不變；申請仍是 pending（開頁面不等於同意） | 自動：C |
| TC-004 【機器可驗】 | 計畫「作法 1」表單通道 | 例外 | 客戶端支援表單；安的連線 | LLM 提出刪除 a；表單跳出，安按「否／取消」 | 回「未送出」並說明原因；圖庫指紋不變；該申請變成作廢（void） | 自動：B |
| TC-005 【機器可驗】 | 計畫「作法 1」 | 例外 | 本機 stdio 客戶端，沒有登入使用者、沒有表單 | LLM 呼叫 `pack_figures` | 回「這裡沒有人可以確認」一類的說明，沒有任何圖被改；不留下之後可被 CHAT 確認的申請 | 自動：B |
| TC-006 【機器可驗】 | 例 2（維護者原句：「LLM 提出刪除 a → 畫面寫明會刪 a 與它的程式碼、參數，且 a 目前在交付包內 → 使用者沒回答、過了時限 → 什麼都沒變」） | 例外 | a 在包內、有程式碼與參數；LLM 提出刪除 a，使用者沒有回答；時鐘撥過 600 秒（既有時限） | 之後有人在確認頁按送出，或 LLM 帶 `request_id`＋`user_confirmed=true` | 都被拒絕（逾時）；a 的圖、程式碼檔、參數檔仍在；a 仍在交付包內；圖庫指紋與提出前相同 | 自動：B |
| TC-007 【機器可驗】 | 計畫「作法 1」 | 例外 | 安的圖庫 a、b、c | 分別提出：含不在圖庫的名稱、名稱含 `..`／`/`／`\`／NUL、超過 30 個名稱、`names` 不是清單、`delete_figure` 的 `name` 傳成清單 | 每一種都「整個拒絕」，說出是哪個名稱或什麼原因；`confirmations` 沒有新列；圖庫指紋不變 | 自動：A |
| TC-008 【機器可驗】 | 維護者原話 2（11-12）：「以後若使用者要回去拿當時未勾選的項目還是要可以」；計畫「打包只改旗標，永不刪圖」 | 功能 | 圖庫 a、b、c；依序確認打包 `[a]`、`[b,c]`、`[]`、`[a,b,c]` | 每次確認後檢查圖庫 | 每次之後，三張圖的圖檔、程式碼檔、參數檔內容與檔案數都與一開始逐位元組相同，只有 `packed`／`packed_at` 隨之改變；永遠沒有任何圖消失 | 自動：A |

## User Story 2 — 畫面寫明會發生什麼（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-009 【機器可驗】 | 例 1（維護者原句：「畫面寫明『加入 a、b；移出 c（仍留在圖庫）』」）；計畫「作法 2」 | 功能 | 圖庫 a、b、c，c 在包內 | LLM 提出打包 a、b；取表單通道給本人看的文字，以及 pending 回覆的 `summary` | 兩處都寫明：加入 a、b；移出 c；c「仍留在圖庫，之後可以再打包」；打包後的交付包恰為 a、b（共 2 張） | 自動：A |
| TC-010 【機器可驗】 | 例 1；計畫「作法 2」確認頁 | 功能 | 同 TC-009 | 安用中文開確認頁 | 頁面寫明同樣的加入 a、b；移出 c 並寫明仍留在圖庫、之後可再打包；有「送出」按鈕 | 自動：C |
| TC-011 【機器可驗】 | 計畫「作法 2」（中、英） | 功能 | 同 TC-009 | 安用英文開確認頁（`?lang=en`） | 英文頁寫明 added a, b；removed from the package c；c stays in the gallery and can be packed again later；全頁沒有中日韓字元 | 自動：C |
| TC-012 【機器可驗】 | 計畫「作法 2」：哪些圖不變 | 功能 | 圖庫 a、b、c、d；a 已在包內、d 不在包內；提出打包 `[a, b]` | 看畫面 | 「不變」處列出 a（已在包內、仍在）；不在 names 的 d 也列為不變（未打包、不受影響）；a 不會被寫成「加入」 | 自動：A |
| TC-013 【機器可驗】 | 計畫「可為空＝清空交付包」；P2 | 功能 | 包內有 c；提出 `pack_figures(R, [])` | 看畫面（三個通道的文字） | 多一行醒目的話：交付包將被清空、目前包內的 c 都會移出但仍留在圖庫；不需要第二道確認；若交付包本來就是空的，依 P6 不建申請 | 自動：A |
| TC-014 【機器可驗】 | 例 2；計畫「作法 2」delete | 功能 | a 在包內，有程式碼檔與參數檔 | LLM 提出刪除 a；看畫面 | 寫明：要刪的是 a；會一併刪掉它的圖檔、程式碼檔、參數檔；a 目前在交付包內、刪除後會一併移出交付包；刪除後圖庫沒有 a | 自動：A、C |
| TC-015 【機器可驗】 | 計畫「作法 2」delete；P3 | 功能 | b 不在包內 | LLM 提出刪除 b | 畫面寫明 b 目前不在交付包內；不會寫「移出交付包」 | 自動：A |
| TC-016 【機器可驗】 | 計畫「作法 2」（寫明會刪什麼） | 功能 | 某張圖沒有程式碼檔、沒有參數檔 | 提出刪除它 | 畫面只列實際存在的檔（圖檔），沒有宣稱會刪不存在的程式碼檔或參數檔 | 自動：A |
| TC-017 【機器可驗】 | 計畫「作法 2」（中、英） | 功能 | 同 TC-014 | 安用英文開確認頁 | 英文頁寫明 will delete a, its code file and its parameter file；a is currently in the delivery package；全頁沒有中日韓字元；按鈕為 "Confirm delete" | 自動：C |
| TC-018 【機器可驗】 | 計畫「作法 2」：三個通道一致 | 功能 | 同一筆打包申請、同一筆刪除申請 | 取表單文字、CHAT 回覆的摘要、確認頁文字，各自抽出加入／移出／不變／刪除的圖名 | 三個通道列出的名單完全相同 | 自動：A |
| TC-019 【機器可驗】 | 維護者 10-27 用字裁示：「一樣要注意中文的顯示不能口語」 | 功能 | 新增的確認畫面字串 | 跑 `test_web_wording_sweep.py` 與新增的字串檢查 | 中文為正式書面語、不含禁用字；英文無中日韓字元；既有 sweep 測試仍綠且未被放寬 | 自動：`platform/tests/test_web_wording_sweep.py` |
| TC-020 【機器可驗】 | 計畫「作法 2」確認頁；P8 | 功能 | 一筆打包、一筆刪除的 pending 申請 | 分別開頁 | 標題分得出是打包還是刪除（中文含「打包」／「刪除」，英文含 package／delete）；打包頁按鈕「送出」、刪除頁按鈕「確認刪除」；表單帶 CSRF 欄位；頁面沒有「工作編號」「送出新分析」等啟動分析的字句 | 自動：C |
| TC-021 【機器可驗】 | 計畫「作法 2」成功頁 | 功能 | 安按下送出且寫入成功 | 看成功頁（打包、刪除各一，中英各一） | 打包：說明交付包現為哪幾張；刪除：說明已刪除哪張；都沒有工作編號；有連到該分析頁的連結 | 自動：C |
| TC-022 【機器可驗】 | 計畫「作法 2」 | 例外 | 一筆逾時的、一筆作廢的、一筆被圖庫變動拒絕的 `gallery_change` 申請 | 安開各頁 | 逾時頁（410）、作廢頁（409）各用自己的白話句（說明原因與「請請 AI 重新提出」）；不會落到啟動分析的文字，也沒有「工作編號 None」 | 自動：C |
| TC-023 【機器可驗】 | 計畫「作法 2」：bundle 很小 | 功能 | 一筆打包申請（30 個名稱）與一筆刪除申請 | 讀 `confirmations.bundle_json` | 只有 `action`、`run_id`、`run_name`、名稱清單與「會發生什麼」；沒有圖的位元組（base64）、程式碼文字、參數文字；大小遠小於 5 MiB 上限 | 自動：A |

## User Story 3 — 本人確認後才生效；冒用、竄改、重放、逾時一律不生效（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 【機器可驗】 | 計畫「作法 1」表單；例 1 | 功能 | 圖庫 a、b、c（c 在包內）；表單通道 | LLM 提出打包 a、b；安在表單按「是」 | 交付包恰為 a、b；回「完成」；申請為 confirmed、通道記 ELICITED | 自動：B |
| TC-025 【機器可驗】 | 計畫「作法 1」確認頁；例 1 | 功能 | 同上；pending 申請 | 安登入，在確認頁按「送出」 | 交付包恰為 a、b；成功頁；通道記 PAGE | 自動：C |
| TC-026 【機器可驗】 | 維護者原話 1（11-12）：「AI要能夠代使用者完成所有事，包括按按鈕(使用者說"確認"就行)」；計畫「作法 1」CHAT | 功能 | pending 申請；安在聊天中回答「確認」 | LLM 用同樣參數加上 `request_id` 與 `user_confirmed=true` 再呼叫 `pack_figures` | 交付包恰為 a、b；回完成；通道記 CHAT | 自動：B |
| TC-027 【機器可驗】 | 計畫「作法 1」表單；例 2 | 功能 | a 在包內；表單通道 | LLM 提出刪除 a；安在表單按「是」 | a 的圖檔、程式碼檔、參數檔都不見；a 不在 `index.json`、不在交付包；其餘圖不變；通道 ELICITED | 自動：B |
| TC-028 【機器可驗】 | 計畫「作法 1」確認頁 | 功能 | 刪除 a 的 pending 申請 | 安在確認頁按「確認刪除」 | 同 TC-027；通道 PAGE | 自動：C |
| TC-029 【機器可驗】 | 維護者原話 1；計畫「作法 1」CHAT | 功能 | 刪除 a 的 pending 申請；安回答「確認」 | LLM 帶 `request_id`＋`user_confirmed=true` 再呼叫 `delete_figure` | 同 TC-027；通道 CHAT | 自動：B |
| TC-030 【機器可驗】 | 例 1（維護者原句：「使用者說『確認』→ 交付包恰為 a、b，c 仍在圖庫、仍可下載」） | 功能 | 圖庫 a、b、c（c 原在包內），經任一通道確認打包 `[a,b]` | 看交付包、`index.json`，再經 `read_figure`／`/run/figure` 取 c | `list_figures(packed_only=True)` 恰為 a、b；c 還在圖庫、`packed=false`；c 的位元組與當初存入的逐位元組相同、可下載 | 自動：A |
| TC-031 【機器可驗】 | 例 1「之後可再打包回來」；維護者原話 2（11-12） | 功能 | TC-030 的結果；LLM 另提出打包 `[c]` 並經確認 | 看交付包 | 交付包恰為 c（a、b 改為未打包但仍在圖庫）；c 的程式碼、參數仍在 | 自動：A |
| TC-032 【機器可驗】 | 計畫「作法 2」：不建 job | 功能 | 任一已確認的 `gallery_change` | 查 `confirmations` 與 `jobs` | `confirmations` 該列 confirmed、`channel` 為 ELICITED／PAGE／CHAT 之一（不是 TERMINAL）；沒有對應的 `jobs` 列；回覆與成功頁都沒有工作編號 | 自動：B |
| TC-033 【機器可驗】 | 例 3（維護者原句：「LLM 自己帶 `user_confirmed=true` 而沒有先提出…拒絕，什麼都沒變」） | 例外 | 圖庫 a、b、c | LLM 只帶 `user_confirmed=true`，不帶 `request_id`（打包與刪除各一次） | 都被拒絕，說明要帶第一次呼叫回的申請編號；圖庫指紋不變；沒有新增 `confirmations` 列 | 自動：B |
| TC-034 【機器可驗】 | 例 3（「或帶別人的 `request_id`」） | 例外 | 鮑有一筆自己的 pending 申請；安的連線 | 安的 LLM 帶鮑的 `request_id`＋`user_confirmed=true` | 被拒絕；安與鮑的圖庫都不變；鮑的申請仍是 pending | 自動：B |
| TC-035 【機器可驗】 | 計畫「作法 3」；P1 | 例外 | 安有一筆 pending 的打包申請；另有一筆 pending 的 `publish_figure` 申請 | (a) 用打包申請的編號呼叫 `delete_figure` 並帶 `user_confirmed=true`；(b) 用 `publish_figure` 的編號呼叫 `pack_figures` 並帶 `user_confirmed=true` | 兩種都被拒絕（內容與種類與當初不同）；圖庫不變；原申請仍可由本人用正確的方式確認 | 自動：B |
| TC-036 【機器可驗】 | 例 3（「或內容與提出時不同」） | 例外 | pending 申請是打包 `[a, b]` | LLM 帶同一個 `request_id`＋`user_confirmed=true`，但改成 `[a]`、或換成另一個 run、或刪除另一張圖 | 全部被拒絕，說明「內容與當初給本人看的不同」；圖庫不變 | 自動：B |
| TC-037 【機器可驗】 | 計畫「作法 3」 | 例外 | 無 | 帶不存在或亂編的 `request_id`＋`user_confirmed=true` | 被拒絕，說明查無這個申請；圖庫不變 | 自動：B |
| TC-038 【機器可驗】 | 計畫「重放」 | 例外 | 打包 `[a,b]` 已確認成功；之後安在網頁上改打包成 `[c]` | LLM 再次用同樣的 `request_id`＋`user_confirmed=true` 呼叫 | 不會再執行一次（交付包仍是網頁上改後的 `[c]`）；回覆是「先前已完成」或拒絕，圖庫不變 | 自動：B |
| TC-039 【機器可驗】 | 計畫「重放」；刪除不可誤傷新圖 | 例外 | 刪除 a 已確認成功；之後 LLM 又用 `publish_figure` 存了一張新的同名 a 並經確認 | LLM 再次用刪除 a 的 `request_id`＋`user_confirmed=true` 呼叫 | 新的 a 還在、未被刪；圖庫不變 | 自動：B |
| TC-040 【機器可驗】 | 計畫「作法 3」 | 例外 | 一筆被拒絕或被本人說「否」而作廢的申請 | 之後 LLM 帶它的 `request_id`＋`user_confirmed=true` | 被拒絕（申請已作廢）；圖庫不變 | 自動：B |
| TC-041 【機器可驗】 | 計畫「逾時」；例 2 | 例外 | pending 的打包申請；時鐘撥過 600 秒 | LLM 帶 `request_id`＋`user_confirmed=true` | 被拒絕（逾時）；圖庫不變；申請變成作廢 | 自動：B |
| TC-042 【機器可驗】 | 計畫「共用額度」（沿用既有） | 例外 | 安同時已有 10 筆 pending 申請（任何非清理種類） | 再提出第 11 筆 `gallery_change`；另外一筆清理提醒（clean_work）不應受影響 | 第 11 筆被拒（既有的「等待中的申請已達上限」訊息）；`gallery_change` 與其他種類共用這 10 筆額度；清理提醒不佔此額度 | 自動：B |
| TC-043 【機器可驗】 | 計畫「共用 `_ask`」；既有去重 | 功能 | 同一人、同一內容，剩餘時間超過 60 秒 | 連續呼叫兩次同樣的 `pack_figures` | 兩次回同一個 `request_id`，只有一列 pending | 自動：B |
| TC-044 【機器可驗】 | 專長守則重疊（確認頁防護） | 例外 | 一筆安的 pending 申請 | 安沒有登入、不帶或帶錯 CSRF、`Origin` 不同源，各按一次送出 | 各自被拒絕（未登入導向登入、CSRF 錯 403、跨站被擋）；圖庫指紋不變 | 自動：C |
| TC-045 【機器可驗】 | 計畫「重放」（確認頁） | 例外 | 一筆已按送出成功的申請 | 安再按一次（重複送出） | 回「已完成」，不再執行，不報錯誤；圖庫指紋與第一次完成後相同 | 自動：C |
| TC-046 【機器可驗】 | 計畫「作法 3」；既有 `write_failed` 處理 | 例外 | 核准時寫入 `index.json` 失敗（例如替換檔案時丟錯誤） | 安確認 | 申請作廢並記原因；回覆與「輸入被拒」不同（說明是寫入失敗、圖庫沒有變更）；`index.json` 與所有圖維持原狀；資料夾內沒有留下暫存檔 | 自動：B |
| TC-047 【機器可驗】 | 憲法 2（CHAT 不得經 stdio） | 例外 | stdio 客戶端（沒有登入的使用者） | 帶任意 `request_id`＋`user_confirmed=true` 呼叫 `pack_figures` | 被拒絕；圖庫不變 | 自動：B |

## User Story 4 — 核准時重新檢查圖庫，變了就拒絕；網頁與 MCP 交錯不會遺失更新（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-048 【機器可驗】 | 例 4（維護者原句：「提出之後、確認之前，使用者在網頁上先刪了 b → 確認時拒絕並說明圖庫已變動，請重新提出」） | 例外 | 圖庫 a、b、c；LLM 提出打包 `[a,b]`（pending）；安在網頁上刪除 b | 安在確認頁按「送出」 | 被拒絕；頁面說明圖庫在提出之後已變動、請 AI 重新提出；沒有任何打包被執行：圖庫只有網頁刪 b 的結果（a、c，打包旗標與刪 b 之前相同） | 自動：C |
| TC-049 【機器可驗】 | 例 4 的 CHAT 版；P4 | 例外 | 同上，但安在聊天回答「確認」 | LLM 帶 `request_id`＋`user_confirmed=true` 再呼叫 `pack_figures`（名單照原樣 `[a,b]`） | 被拒絕，訊息明說「圖庫已變動、請重新提出」（不是籠統的「內容不同」）；圖庫與 TC-048 的結果相同 | 自動：B |
| TC-050 【機器可驗】 | 例 4 的表單版 | 例外 | 同上，表單通道：問了之後、使用者回答「是」之前，網頁刪了 b | 回答「是」 | 同 TC-048：拒絕、說明圖庫已變動、什麼都沒打包 | 自動：B |
| TC-051 【機器可驗】 | 計畫「作法 3」delete | 例外 | LLM 提出刪除 a（pending）；網頁上先刪了 a | 安確認 | 被拒絕，說明圖庫已變動；沒有報錯（不是 500、不是堆疊）；圖庫沒有多餘變動 | 自動：B |
| TC-052 【機器可驗】 | 計畫「作法 3」：「被取代」；R5 | 例外 | 提出打包 `[a,b]`（pending）；期間 LLM 用 `publish_figure` 以同名 b 存入新內容並經確認 | 安確認打包 | 被拒絕（圖庫已變動）；打包旗標不變；新的 b 沒有被打包 | 自動：A |
| TC-053 【機器可驗】 | 計畫「作法 3」：「被別的打包改過」 | 例外 | 提出打包 `[a,b]`（pending）與另一筆刪除 c 的 pending；期間網頁上把打包改成 `[c]` | 安確認其中任一筆 | 兩筆都被拒絕（圖庫已變動）；交付包維持網頁改成的 `[c]` | 自動：A |
| TC-054 【機器可驗】 | 計畫「作法 3」；P5 | 例外 | 提出打包 `[a,b]`（pending）；期間 LLM 另存了新的 d 並經確認 | 安確認打包 | 被拒絕（圖庫已變動，請重新提出）；d 與其餘不變 | 自動：A |
| TC-055 【機器可驗】 | 計畫「作法 3」：通過才呼叫 | 功能 | 提出之後到確認之前，圖庫完全沒有被動過 | 安確認 | 通過、成功寫入（重新檢查不會誤拒） | 自動：A |
| TC-056 【機器可驗】 | 第 2 片 G2（`index.json` 損毀）；專長守則：錯誤訊息 | 例外 | pending 申請；之後 `index.json` 被弄壞 | 安確認 | 被拒絕，回明確的話（圖庫暫時無法讀取）；不是 500；訊息不含檔案路徑；壞檔不被覆寫 | 自動：A |
| TC-057 【機器可驗】 | 計畫「作法 3」 | 例外 | pending 申請；之後該 run 的圖庫資料夾不見了（或該 run 已不屬於安） | 安確認 | 被拒絕，回「找不到」一類的話；沒有建立新資料夾、沒有寫任何檔案 | 自動：A |
| TC-058 【機器可驗】 | 既有 `approve` 的稽核規則 | 例外 | 任一被圖庫變動拒絕的申請 | 查 `confirmations` | 該列為作廢、`void_reason` 寫明原因；本人當時按了同意這件事照舊記錄在該列；沒有 `jobs` 列 | 自動：B |
| TC-059 【機器可驗】 | 第 2 片 G1；R4：重新檢查與寫入同一次持鎖 | 功能 | 圖庫 a、b、c；pending 打包申請；在「核准的重新檢查之後、寫入之前」插入一個網頁刪除 b（測試掛鉤） | 安確認 | 網頁刪除要嘛在核准完成之後才進行，要嘛核准被拒絕；兩種結果之一，且 b 不會復活、旗標不會被舊資料蓋回 | 自動：A |
| TC-060 【機器可驗】 | 例 6（維護者原句：「網頁按鈕與 MCP 工具對同一個圖庫交錯操作，結果與依序操作相同（沒有遺失更新）」） | 功能 | 圖庫 a、b、c；多執行緒同時進行：網頁打包、網頁刪除、MCP 核准打包、MCP 核准刪除；重複至少 50 輪 | 讀最終圖庫 | 每輪最終 `index.json` 都是合法 JSON；等於「某一種依序順序」的結果；沒有已刪的圖復活、沒有圖庫與 `index.json` 不一致 | 自動：A |
| TC-061 【機器可驗】 | 例 6 | 功能 | 四個操作（網頁打包 `[a]`、網頁刪 c、MCP 核准打包 `[b]`、MCP 核准刪 a）的全部 24 種順序 | 每種順序各依序執行一次 | 每種順序的最終圖庫，都等於「用同樣順序一個一個做」的預期結果（過時的核准被拒，算在預期裡）；沒有任何一種順序出現遺失更新 | 自動：A |
| TC-062 【機器可驗】 | 第 1 片 G1；例 6 | 功能 | 一筆 `publish_figure` 申請與一筆 `gallery_change` 申請同時核准 | 同時按 | 新存入的圖不會被打包／刪除的寫入蓋掉而消失；`index.json` 合法 | 自動：A |

## User Story 5 — 擁有權與跨使用者（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-063 【機器可驗】 | 例 5（維護者原句：「另一位使用者對這個 run 提出 → 與 run 不存在同一句答覆」） | 例外 | 鮑登入；安的 R 有 a、b、c；另有一個不存在的 run id | 鮑呼叫 `pack_figures(R, ["a.png"])` 與 `pack_figures(不存在的id, ["a.png"])` | 兩者回答除了 run id 字串本身外完全相同（「找不到這個 run」）；沒有任何申請列；安的圖庫不變 | 自動：A |
| TC-064 【機器可驗】 | 例 5 | 例外 | 同上 | 鮑呼叫 `delete_figure(R, "a.png")` 與 `delete_figure(不存在的id, "a.png")` | 同 TC-063；a 沒被刪、沒有申請列；答覆看不出 a 存在與否 | 自動：A |
| TC-065 【機器可驗】 | 專長守則：跨使用者寫 | 例外 | 安有 pending 的 `gallery_change` 申請 | 鮑分別用確認頁按送出、用 CHAT 的 `request_id`＋`user_confirmed=true`、用自己的表單回答去核准 | 都被拒絕；安的圖庫不變；安的申請仍是 pending，之後安自己可以確認 | 自動：B、C |
| TC-066 【機器可驗】 | 專長守則：跨使用者讀 | 例外 | 同上 | 鮑開安的申請的確認頁（GET） | 回 403 頁，頁面沒有安的圖名、打包內容 | 自動：C |
| TC-067 【機器可驗】 | 計畫「擁有者檢查照 `publish_figure`」；P9 | 功能 | 安自己的、狀態不是 succeeded 的 run（例如 running）有圖庫 | 安的 LLM 對它提出打包 | 與 `publish_figure` 一樣可提出、可確認（網頁隱藏按鈕是畫面限制，不是動作層限制） | 自動：A |

## User Story 6 — 與網頁按鈕對等：同一個動作層函式、同一個結果（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-068 【機器可驗】 | 計畫目標：「兩條路做同一件事、走同一個動作層函式」 | 功能 | 對第 2 片的核心函式與網頁路由所呼叫的函式做偵測（spy） | 經 MCP 核准一次打包、一次刪除；經網頁按鈕各做一次 | 兩條路都呼叫同一個 `pack_figures`／`delete_figure` 核心函式；核准的 writer 沒有自己再寫一份 `index.json` 讀改寫 | 自動：A |
| TC-069 【機器可驗】 | 計畫「語意與網頁相同」 | 功能 | 兩份相同的圖庫（含相同時鐘）；一份用網頁勾選 `[a,b]` 按「打包所選的圖」，一份經 MCP 確認打包 `[a,b]` | 比較兩份結果 | `index.json` 與所有檔案逐項相同 | 自動：A |
| TC-070 【機器可驗】 | 同上（刪除） | 功能 | 兩份相同的圖庫；一份網頁刪除 a，一份經 MCP 確認刪除 a | 比較 | 剩下的檔案與 `index.json` 相同；a 的三個檔都被移除，沒有殘檔 | 自動：A |
| TC-071 【機器可驗】 | 專長守則：路由與工具裡不得有第二份邏輯 | 功能 | 讀 `mcp_server.py` 的新工具處理函式與 `web.py` 的新增程式碼（AST） | 找 `index.json`、`os.unlink`、`os.replace`、`open(` | 新工具處理函式只呼叫動作層的 `request_pack_figures`／`request_delete_figure`，沒有任何圖庫邏輯；既有的 `test_routes_only_call_the_action_layer` 不變且綠 | 自動：A；`platform/tests/test_web_figures.py` |
| TC-072 【機器可驗】 | 專長守則：對等性 | 功能 | 測試同時列舉兩邊 | 比對「使用者可見的動作」與動作層函式 | `request_pack_figures`、`request_delete_figure` 同時出現在動作層與 MCP 工具；`test_web_parity.py` 的 `WEB_ONLY` 只增這兩項（附理由）；`OWED` 不變；`test_actions_layer.py` 的 `WRITE_NAMES` 加入 `pack_figures`、`delete_figure` 並通過「無確認通道一律拒絕」那組測試 | 自動：`platform/tests/test_web_parity.py`、`platform/tests/test_actions_layer.py` |

## User Story 7 — 資料庫遷移與既有種類不受影響（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-073 【機器可驗】 | 計畫「作法 4」：最舊資料庫形狀 | 功能 | 只認 launch、cancel 的最舊 `platform.db`，含舊列與連到它們的 `jobs` | 用新程式開啟 | `confirmations` 的種類限制變成含 `gallery_change`（和 `clean_work`、`publish_figure`）；舊列逐欄相同；`jobs.confirmation_id` 外鍵檢查為空 | 自動：D |
| TC-074 【機器可驗】 | 同上：只有 clean_work 的舊庫 | 功能 | 認 launch、cancel、clean_work 的舊庫 | 開啟 | 同 TC-073；舊列不變 | 自動：D |
| TC-075 【機器可驗】 | 同上：第 1 片遺留的庫 | 功能 | 已認 `publish_figure` 但還不認 `gallery_change` 的庫，含一列已確認的 `publish_figure`（帶 `bundle_json`） | 開啟 | 被遷移成認 `gallery_change`；`publish_figure` 那一列完全不變、其 `bundle_json` 還在；`_confirmations_current` 不再把這種庫當成「已是最新」 | 自動：D |
| TC-076 【機器可驗】 | 計畫「作法 4」 | 功能 | 全新的資料庫 | 插入 `gallery_change`、`resume`、空字串三列 | `gallery_change` 收；`resume` 與空字串仍被拒 | 自動：D |
| TC-077 【機器可驗】 | 計畫：「連跑兩次結果相同」 | 功能 | 任一舊庫 | 連續開啟兩次 | 第二次不改任何東西：`sqlite_master`、各表列數與內容都和第一次之後完全相同 | 自動：D |
| TC-078 【機器可驗】 | 計畫：「失敗回滾」 | 例外 | 舊庫；在複製步驟丟錯誤 | 開啟 | 例外往外傳；舊表與舊列、外鍵設定原樣，不留 `confirmations_new`；`foreign_keys` 回到開啟 | 自動：D |
| TC-079 【機器可驗】 | 既有安全檢查 | 例外 | 舊庫中有一筆 `jobs` 指向不存在的申請 | 開啟 | 遷移停下並回滾，舊表舊列不變 | 自動：D |
| TC-080 【機器可驗】 | 既有並行開啟測試 | 功能 | 兩個連線同時開啟同一個舊庫 | 同時開 | 都不失敗；結果和單獨開一次相同 | 自動：D |
| TC-081 【機器可驗】 | 既有唯讀測試 | 功能 | 舊庫 | 以唯讀開啟 | 不升級、檔案不變 | 自動：D |
| TC-082 【機器可驗】 | 計畫「jobs 的 CHECK 不變」 | 功能 | 遷移前後 | 比對 `jobs` 表的建表文字、`confirm.JOB_KIND`、`jobs.CONFIRMED`、`PENDING_SECONDS` | 全部與遷移前相同（`JOB_KIND` 不含 `gallery_change`；`JOB_KIND` 的完全相等斷言、`PENDING_SECONDS == 600` 的釘住測試未改且綠） | 自動：D；`platform/tests/test_cleanup_confirm.py`、`test_pending_confirm_restart.py` |
| TC-083 【機器可驗】 | L 級爆炸半徑 | 功能 | 遷移前後各抓 `sqlite_master` | 比對 | 除了 `confirmations` 的種類限制文字多出 `gallery_change` 之外，沒有任何差異 | 自動：D |
| TC-084 【機器可驗】 | 計畫「不改既有種類」 | 功能 | launch、cancel、clean_work、publish_figure 各一筆 pending | 各自 approve | 回傳值、佇列行為、`jobs` 列與改動前相同；既有測試（`test_cleanup_confirm.py`、`test_publish_figure_confirm.py` 等）未改且全綠 | 自動：既有測試加 B |
| TC-085 【機器可驗】 | R3：writer 依種類挑選 | 功能 | `publish_figure` 申請，經三個通道各確認一次 | 確認 | 都仍寫入圖庫、結果與改動前相同（writer 沒有被 `gallery_change` 搶走）；`gallery_change` 經三個通道各自走到自己的 writer（TC-024～029 為證） | 自動：B |
| TC-086 【機器可驗】 | 計畫「作法 2」：`NO_JOB_KINDS` | 功能 | 讀 `confirm.NO_JOB_KINDS`、對 `gallery_change` approve | 比對 | `NO_JOB_KINDS` 為 `("publish_figure", "gallery_change")`；`approve` 對 `gallery_change` 不排任何 job，回 `(rid, None)` | 自動：B |
| TC-087 【機器可驗】 | L 級：每個讀寫 `confirmations.kind` 的位置 | 功能 | 搜尋 `platform/abf_platform` 所有讀寫 `confirmations.kind` 或用 `kind` 分支的程式碼 | 逐一對照 ledger 清單 | ledger 的清單與搜尋結果一致；每一處說明新種類是否影響；沒有任何一處把 `gallery_change` 當成 launch 處理（例如 `facts`、`describe`、`find_approved`、確認頁的預設分支） | 自動：讀 ledger 與 diff |
| TC-088 【機器可驗】 | 第 1 片 `forget_content`；計畫「bundle 很小」 | 功能 | 已確認與 pending 的 `gallery_change` 申請，其 `run_name` 為 R | 擁有者 forget 分析 R | 這些列的 `bundle_json`／畫面文字被清空並記 forgotten；pending 的變作廢；圖庫檔案不被刪（沿用第 2 片裁決） | 自動：B |

## User Story 8 — 工具清單與釘住測試（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-089 【機器可驗】 | 計畫「作法 5」：工具數 23→25、唯讀不變 | 功能 | 啟動 MCP 伺服器 | 列出工具 | 共 25 個；唯讀工具仍是原本 15 個；新增的恰為 `pack_figures`、`delete_figure`；`read_figure` 仍不是工具 | 自動：`platform/tests/mcp/test_mcp_contract_tools.py` |
| TC-090 【機器可驗】 | 計畫「作法 1」；P7 | 功能 | 同上 | 讀新工具的標註 | 兩者 `readOnlyHint` 皆 false；`pack_figures` 的 `destructiveHint` 為 false；`delete_figure` 為 true；兩者 `openWorldHint` false；寫入工具清單由標註推導後等於明列的清單（`WRITE_TOOLS` 只增這兩項） | 自動：`platform/tests/mcp/test_mcp_contract_writes.py` |
| TC-091 【機器可驗】 | 計畫「作法 1」「作法 7」工具描述 | 功能 | 讀新工具的簽章與描述 | 檢查 | 簽章：`pack_figures(run_id, names, request_id?, user_confirmed?)`、`delete_figure(run_id, name, request_id?, user_confirmed?)`；描述寫明：只有本人回答後才可帶 `user_confirmed`、打包是「設為這個集合」且沒列到的會移出但不會被刪、刪除一次一張；描述長度未超既有上限 | 自動：A |
| TC-092 【機器可驗】 | 憲法安全網：新寫入工具自己的拒絕測試 | 例外 | 兩個新工具各被呼叫一次，沒人回答 | 跑「未確認一次呼叫零副作用」的參數化測試（已加入兩個工具的呼叫參數） | 沒有碰任何寫入點、沒改 `jobs`、`launches`、舊的確認列，最多新增一列 pending | 自動：`platform/tests/mcp/test_mcp_contract_writes.py` |
| TC-093 【機器可驗】 | 計畫「作法 5」：`tools.json` | 功能 | 重新產生快照 | 與 `main`／第 2 片的快照 diff | 只多出兩個工具條目；其餘既有條目逐位元相同 | 自動：讀 diff；`test_mcp_contract_tools.py` |
| TC-094 【機器可驗】 | 計畫「作法 5」：釘住測試同步、只增不減 | 功能 | 把 `platform/tests` 內寫死工具數與完整工具名清單的地方全部掃出來，目前已知：`test_actions_layer.py:757`、`test_pat.py:384`、`test_oauth_mcp.py:44`、`test_mcp_run_file.py:320`、`test_mcp_server_doc.py:40`、`test_su_in_get_run.py:413`、`test_aws_launch.py:1160`、`test_azure_launch.py:1120`、`test_gcb_launch.py:1068`、`mcp/test_mcp_contract_tools.py` 的 `EXPECTED_TOOLS`、`mcp/snapshots/tools.json`、`mcp/test_mcp_contract_writes.py` 的 `WRITE_TOOLS` 與呼叫參數、`test_actions_layer.py:29` 的 `WRITE_NAMES`、`test_cleanup_store.py:155-157` 的種類清單、`test_chat_tools.py` | 讀 diff 並跑整套 | 沒有任何一處還是舊的 23；每個改動只是加入新名稱或把數字改為 25，沒有刪掉或放寬任何斷言；整個 `platform/tests` 綠 | 自動：整套；讀 diff |
| TC-095 【機器可驗】 | R2：第 2 片測試與本片相反 | 功能 | `test_actions_layer.py` 的 `test_gallery_page_actions_exist_in_the_action_layer_and_are_not_tools`、第 2 片 TC-057／TC-078 對應的斷言 | 讀 diff | 計畫點名這幾處並說明原因（維護者 11-12 裁示）；只放寬「`pack_figures`、`delete_figure` 不是工具」，改成「它們是會經確認通道的寫入工具」；`read_figure` 仍不是工具、`not hasattr(actions, "pack_figures")`（`test_web_figures.py`）仍成立且未改 | 自動：讀 diff 與計畫 |
| TC-096 【機器可驗】 | 計畫「作法 7」文件 | 功能 | 實作完成後 | 讀 `docs/PLATFORM.md`、`docs/TESTING.md`、`CHANGELOG.md` | PLATFORM.md 的工具數與寫入工具敘述（439 行「Twenty-three… The other seven」、443 行「the tools stay twenty-three」）已改為 25／九個，且沒有留下過時句；寫明兩個工具、`gallery_change` 種類、「設為這個集合」語意、移出不刪、重新檢查與拒絕；TESTING.md 有手動步驟；CHANGELOG 有條目 | 自動：讀文件 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-097 【機器可驗】 | 計畫「作法 6」：瀏覽器聊天不提供這兩個工具；R1 | 不在範圍 | 瀏覽器聊天的工具集；`chat_tools.py` | 列出聊天可用工具、跑分類檢查 | 沒有 `pack_figures`、`delete_figure`；兩者在 `CHAT_EXCLUDED`；分類檢查不丟 `ValueError`；`test_chat_tools.py` 只增這項排除斷言 | 自動：`platform/tests/test_chat_tools.py` |
| TC-098 【機器可驗】 | 計畫「不做」：不做一次刪多張 | 不在範圍 | `delete_figure` | 傳入清單、逗號分隔多個名稱 | 被拒絕，說明一次只能刪一張；沒有刪任何圖 | 自動：A |
| TC-099 【機器可驗】 | 計畫「不做」：不做復原刪除 | 不在範圍 | 工具清單、動作層、路由表 | 找名為 undelete、restore、復原 的工具、動作或路由 | 都沒有；刪除確認畫面沒有承諾可復原 | 自動：A |
| TC-100 【機器可驗】 | 計畫「不做」：不改網頁按鈕與第 2 片路由 | 不在範圍 | 第 2 片的 `test_web_figures.py` | 與第 2 片比對路由表與測試 | 路由表與第 2 片完全相同（沒新增路由）；網頁打包與刪除仍不建 `confirmations` 列、仍不收 Bearer token；第 2 片的網頁測試未改且綠 | 自動：`platform/tests/test_web_figures.py`、`test_publish_figure_confirm.py` |
| TC-101 【機器可驗】 | 計畫「不做」：不改確認逾時、額度 | 不在範圍 | 常數 | 讀 `PENDING_SECONDS`、`MAX_OPEN_PENDING`、`KEEP_UNSENT_SECONDS`、`REUSE_MIN_SECONDS`、`CLEAN_PENDING_SECONDS` | 與 `main` 相同；對應的釘住測試未改 | 自動：既有釘住測試 |
| TC-102 【機器可驗】 | 計畫「不做」：不改既有種類路徑 | 不在範圍 | launch、cancel、resume、relaunch、clean_work、forget、publish_figure 既有測試 | 跑這些測試並讀 `confirm.py` diff | 測試未改且全綠；`confirm.py` 的 diff 只新增（常數項、`facts` 的新分支），既有行沒被改動（ledger 附被改動的既有行清單） | 自動：既有測試；讀 diff |
| TC-103 【機器可驗】 | 計畫「不碰」清單 | 不在範圍 | `git diff --stat` | 看改動的檔 | 只有計畫「範圍」所列的檔（加上 R1 補的 `chat_tools.py` 與 `test_chat_tools.py`）；沒有 `.github/`、`hooks/`、`.specify/memory/constitution.md`、`plugin.json`、`platform/abf_station/`、`jobs.py`、`STYLE`／CSS；`CSS_SHA256`（`719ce2ab…`）、`_HEADERS`、`LAUNCH_HEADERS`、`FINISHED_HEADERS`、`FIGURE_HEADERS` 未變；沒有新依賴 | 自動：讀 diff；既有 `test_style_untouched` |
| TC-104 【機器可驗】 | 計畫「作法 1」：只是「提出申請」；第 2 片原話 7 | 不在範圍 | 兩個新工具的簽章 | 找能建立或修改圖內容的參數、或繞過確認的寫入路徑 | 沒有任何內容參數；經 MCP 唯一能新增圖的仍是 `publish_figure`（走確認通道）；打包與刪除沒有其他寫入途徑 | 自動：A |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-105 | 安全網「每個寫入工具未經人回答一律拒絕；新寫入工具附自己的拒絕測試」 | 例外 | 兩個新工具 | 看有沒有專屬的拒絕測試檔、並跑它 | `test_gallery_change_confirm.py` 存在，涵蓋 TC-001～007、TC-033～041、TC-047；三個通道各有「未回答不寫入」案例；全綠 | 自動：B |
| TC-106 | 憲法 2：「權杖、待確認申請、模型自己的答案都不是人的回答」 | 例外 | 只有有效的 Bearer／MCP 權杖，沒有人回答 | 帶權杖呼叫兩個工具，分別帶與不帶 `user_confirmed=true`、帶與不帶別人的 `request_id` | 一律不寫；權杖本身不算同意 | 自動：B |
| TC-107 | 憲法 7.0.0 安全網（第 191-195 行）；不修憲法 | 功能 | 讀 diff；跑 `tests/constitution_6_test.sh` | 比對 | `.specify/memory/constitution.md` 與基準相同；該測試對安全網那條的逐字比對仍綠 | 自動：`tests/constitution_6_test.sh`；讀 diff |
| TC-108 | 憲法 2（不留第二份 run 狀態；唯一送出路徑） | 功能 | 讀新程式碼；跑 `tests/no_second_run_state_test.sh` | 掃描 | 新程式碼不排 job、不碰站台、不呼叫 `on_site`、不保存 run 狀態；掃描仍綠 | 自動：`tests/no_second_run_state_test.sh` |
| TC-109 | 安全網「絕不刪使用者的原始資料」 | 例外 | 安的圖庫資料夾之外放了名稱相似的檔案；一張圖在 `index.json` 內的名稱被手動改成含 `../` | 經 MCP 確認刪除 | 只刪得到圖庫資料夾內「該名稱的三個檔」；資料夾之外的任何檔不受影響；含路徑字元的名稱在提出時就被拒 | 自動：A |
| TC-110 | 憲法：密鑰不外露；專長守則：錯誤訊息與日誌 | 例外 | 觸發所有拒絕（TC-033～041、048～058） | 檢查回覆與日誌 | 每個錯誤都含原因與下一步；不含權杖、檔案系統路徑、SQL、堆疊 | 自動：B |
| TC-111 | 憲法開發流程：L 級證明 | 功能 | 實作完成 | 讀 `specs/mcp-gallery-actions/ledger.md` | 有：(a) `git diff --stat`；(b) `confirm.py`／`store.py` 改了哪幾行與原因、被改動的既有行清單；(c) 遷移前後實際輸出（列數、外鍵檢查、`sqlite_master`）；(d) 所有讀寫 `confirmations.kind` 的位置清單；(e) 既有種類不受影響的證據 | 自動：讀 ledger |
| TC-112 | 憲法開發流程：測試不得被放寬 | 功能 | 本分支所有被改動的既有測試 | 與 `main` 逐一比對 | 沒有被刪掉或放寬的斷言、被跳過的案例或為配合新輸出而改掉的期望值（TC-095 點名的除外）；`spec`／`test-case` 在實作期間未被編輯；`bash tests/run_all.sh` 以 PR 上的 CI 為準全綠 | 自動：讀 diff；CI |

## 實機走通

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-113 【實機驗】 | 例 1；維護者原話 1：「AI要能夠代使用者完成所有事，包括按按鈕(使用者說"確認"就行)」；原話 2 | 功能 | 本機起平台；MCP 客戶端已連上；一個有 a、b、c 三張圖的分析，c 在交付包內 | 1. 請 LLM「把 a、b 放進交付包」。2. 看畫面寫的加入／移出。3. 在聊天說「確認」。4. 到完成頁看交付包、再請 LLM 把 c 打包回來 | 畫面寫明加入 a、b、移出 c（仍留在圖庫）；說「確認」前圖庫沒變；之後交付包恰為 a、b；c 仍在、可下載、也能再打包回來；操作者把每步輸出貼進 ledger；維護者答「是我要的」或指出哪裡不是 | 手動：`docs/TESTING.md`（本案新增） |
| TC-114 【實機驗】 | 例 2 | 功能 | 同上 | 請 LLM 刪除 a；看畫面；不回答，等超過 10 分鐘；再重新整理完成頁 | 畫面寫明會刪 a 與程式碼、參數且 a 在包內；10 分鐘後確認頁顯示逾時；a 與其程式碼、參數都還在、仍在交付包內 | 手動：`docs/TESTING.md` |
| TC-115 【實機驗】 | 計畫「確認畫面（表單、確認頁、聊天摘要；中、英）」；維護者判斷 | 功能 | 同上 | 看打包與刪除的待確認頁與成功頁（中、英；寬螢幕與手機寬度） | 維護者看過後答：文字夠清楚、「仍留在圖庫」讀得出來、刪除畫面讓人知道會失去什麼；截圖存放在 repo 之外 | 手動：`docs/TESTING.md` |
