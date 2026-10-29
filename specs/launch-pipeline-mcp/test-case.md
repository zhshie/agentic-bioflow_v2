# 測試案例：launch-pipeline-mcp（只會「提出」的 MCP 工具 launch_pipeline）

**規格**：`specs/launch-pipeline-mcp/plan.md`（此功能只有計畫、沒有 spec.md；需求以 plan 的「目標／範圍／作法／失敗先行測試／不做／裁決」為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「提出」＝只寫下一張待確認的請求，不啟動任何東西；「本人按好」＝使用者在自己 AI 客戶端的表單，或在平台確認頁按下確認。「job／run」＝真正送去跑的工作與分析紀錄。

維護者原話對照（計畫引用的，沒有「我打這句」型的輸入範例，所以 TC 以原話的意思為預期結果）：

- 017e「MCP 鏡像：… `launch_pipeline`（`_add_write_tools`、`chat_tools.REQUEST_TOOLS`、`confirm.JOB_KIND`）；… parity 表全列」→ TC-001、TC-015、TC-021、TC-023、TC-028
- 裁示 1「使用者用自己的 AI 走 MCP」→ TC-001、TC-002
- 裁示 5（v1 畫布「送去跑」）→ TC-002、TC-008
- 10-18 裁示「AI 可發起任何送出、頁面跳『確認送出嗎？』本人按」→ TC-003、TC-005、TC-007、TC-015、TC-018

## User Story 1 — 使用者的 AI 能「提出」自訂 pipeline 的送出，但不能代按（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；作法「工具介面」；017e | 功能 | 啟動平台的 MCP 伺服器（`build_server`） | 列出伺服器的工具 | 清單裡有 `launch_pipeline`，且它的註記是寫入類（`_WRITES`：不是唯讀、不是破壞性）。改程式前這條是紅的（工具不存在） | 自動：`platform/tests/test_mcp_launch_pipeline.py` |
| TC-002 | 失敗先行測試第 1 條；作法「回傳」 | 功能 | 甲有一個已存、驗證通過的 pipeline；MCP 客戶端不會跳表單（沒宣告表單能力） | 甲呼叫 `launch_pipeline`，給 `pipeline_id`、`run_name` 和樣本表 | 回傳是「已提出、等本人」：`sent` 為 false、`state` 為 pending，用一句話說明要本人按好，並附上該去哪裡按（確認頁網址），與同情境下 `launch` 的回傳形狀相同 | 自動 |
| TC-003 | 失敗先行測試第 1 條；10-18 裁示 | 功能 | 同 TC-002；先記下資料庫裡 job 與 run 的列數 | 甲呼叫 `launch_pipeline`（本人沒按好） | 呼叫之後 job 與 run 的列數和呼叫前相同（沒有新增任何 job／run）。貼進 ledger 的前後比對與此一致 | 自動 |
| TC-004 | 作法「工具介面」（欄位名照 `request_pipeline_launch` 的簽名） | 功能 | 取得 `launch_pipeline` 的參數表（input schema） | 讀它的參數名、必填與可省 | 參數名等於 `request_pipeline_launch` 簽名裡給使用者的那些：`pipeline_id`、`version`、`run_name`、`samplesheet`、`samplesheet_text`、`ce_name`、`params`，不多不少（`platform_path`、`caller`、`person`、`clock`、`remote`、`data` 不出現）。`pipeline_id`、`run_name` 必填；`version`、`ce_name`、`params` 與樣本表欄位可省 | 自動 |
| TC-005 | 作法「工具介面」：沒有任何參數能表示「已同意」；失敗先行測試第 2 條 | 功能 | 取得 `launch_pipeline` 的參數表 | 檢查每個參數名 | 沒有任何參數名（不分大小寫）含 `confirm`、`approve`、`yes`、`void` | 自動 |
| TC-006 | 作法「擁有者規則」「工具介面」；專長守則（動作層唯一） | 功能 | 把 `actions.request_pipeline_launch` 換成記錄呼叫的替身 | 呼叫 `launch_pipeline` 工具 | 替身被呼叫一次，帶著 `caller`（來自這次呼叫的身分，不是記住的舊身分）、`person`、`remote` 與使用者給的欄位；工具函式本身沒有第二份啟動邏輯 | 自動 |
| TC-007 | 「行為與既有 launch 工具一模一樣」；10-18 裁示 | 例外 | 客戶端會跳表單；甲有可送出的自訂 pipeline | 呼叫 `launch_pipeline`，客戶端的表單被拒絕或關掉 | 沒有 job 被排入；回傳說明沒有送出（`sent` 為 false），與 `launch` 在同情況下的行為相同 | 自動 |
| TC-008 | 「行為與既有 launch 工具一模一樣」；裁示 5（送去跑） | 功能 | 客戶端會跳表單；甲有可送出的自訂 pipeline | 呼叫 `launch_pipeline`，本人在客戶端表單按好 | 同一次呼叫排入一個 job，回傳含 job 編號；這是本人的「好」，不是工具自己決定的 | 自動 |
| TC-009 | 「行為與既有 launch 工具一模一樣」 | 功能 | 客戶端不跳表單；甲已呼叫過一次，並在確認頁按好 | 甲用完全相同的參數再呼叫一次 `launch_pipeline` | 回傳該 job 的編號，不會再多開一張請求或第二個 job | 自動 |

## User Story 2 — 找不到、驗證不過、跨使用者時，回清楚的錯誤（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 失敗先行測試第 3 條；專長守則（跨使用者，讀） | 例外 | 甲有 pipeline；乙是另一位使用者，有自己的 token | 乙用甲的 `pipeline_id` 呼叫 `launch_pipeline` | 回「找不到」，文字與乙用一個根本不存在的 `pipeline_id` 時相同；回應裡沒有甲的 pipeline 名稱、內容或任何能證明它存在的資訊 | 自動 |
| TC-011 | 失敗先行測試第 3 條；專長守則（跨使用者，寫） | 例外 | 同 TC-010；先記下待確認請求與 job、run 的列數 | 乙用甲的 `pipeline_id` 呼叫 `launch_pipeline` | 沒有為乙新增任何待確認請求、job、run | 自動 |
| TC-012 | 失敗先行測試第 4 條 | 例外 | 甲有 pipeline，只有第 1 版 | 甲呼叫 `launch_pipeline`，`version` 給一個不存在的版本 | 回傳是一則錯誤（以「未送出：」開頭），含原因與該怎麼辦；沒有丟出例外、沒有堆疊追蹤；沒有新增 job／run | 自動 |
| TC-013 | 失敗先行測試第 4 條 | 例外 | 甲有一個今天的檢查仍有錯誤、沒驗證通過的 pipeline | 甲呼叫 `launch_pipeline` | 回傳是一則錯誤，說明檢查沒過的原因與該怎麼處理；沒有丟出例外、沒有堆疊；沒有新增 job／run | 自動 |
| TC-014 | 專長守則（錯誤訊息與日誌：不含密鑰） | 例外 | 用一個已知字串當甲的 token，跑 TC-002、TC-010、TC-012、TC-013 的呼叫，並收集日誌 | 檢查所有回應與日誌文字 | 回應與日誌都不含該 token 或任何密鑰；錯誤訊息不含內部路徑、SQL | 自動 |

## User Story 3 — 平台聊天助理也能提出 launch_pipeline（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 作法「證據」；裁決 3；017e（`chat_tools.REQUEST_TOOLS`） | 功能 | 載入 `chat_tools` | 讀 `REQUEST_TOOLS` | 包含 `launch_pipeline`，且原有五個（`launch`、`cancel`、`resume`、`relaunch`、`forget`）仍在 | 自動 |
| TC-016 | 失敗先行測試第 5 條 | 功能 | 啟動伺服器，取得真實工具清單 | 對真實清單跑 `classify_check` | 不丟 ValueError（`launch_pipeline` 因已列入 `REQUEST_TOOLS` 而被歸類） | 自動 |
| TC-017 | 失敗先行測試第 5 條（`/chat/spec` 能啟動） | 功能 | 取得聊天用的工具清單（`tool_specs`） | 查 `launch_pipeline` | 清單裡有它，說明與參數表與伺服器上的同一份（不是複製的），共用既有「清單由伺服器推導」的檢查 | 自動 |
| TC-018 | 失敗先行測試第 5 條；作法「BANNED_WORDS」 | 功能 | 取得聊天系統提示字串（`CHAT_SYSTEM_PROMPT`） | 檢查提示 | 提示裡新增一行提到 `launch_pipeline`（屬於「提出請求」那一組，說明確認仍由本人在頁面按）；整段提示不含 `approve`、`confirm`、`confirmed_by`、`void`、`yes`（不分大小寫） | 自動 |
| TC-019 | 失敗先行測試第 5 條 | 功能 | 取得聊天用的工具清單 | 檢查每個工具名與每個參數名 | 沒有任何一個含 `approve`、`confirm`、`confirmed_by`、`void`、`yes`（含新加的 `launch_pipeline` 及其參數） | 自動 |
| TC-020 | 作法「證據」（兩處必須同批加） | 例外 | 在真實清單外多加一個既非唯讀、也不在 `REQUEST_TOOLS` 的假工具 `wipe_everything` | 跑 `classify_check` 與 `tool_specs` | 仍丟錯並點名 `wipe_everything`（新增 `launch_pipeline` 沒有讓分類檢查變鬆） | 自動 |

## User Story 4 — 釘住工具名單的既有測試同步更新（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 範圍「mcp_server.py 檔頭」；失敗先行測試第 6 條 | 功能 | 讀 mcp_server.py 的註冊工具與檔頭 docstring | 跑 `test_mcp_server_doc.py` | 註冊工具為 21 個（原 20 加 `launch_pipeline`）、唯讀仍 15 個；docstring 點名 `launch_pipeline`，並把「提出」類由 five 改成 six（不再留「five tools that ask a person」）；「fifteen read-only」不變 | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-022 | 範圍「釘住工具名單的既有測試」；失敗先行測試第 6 條 | 功能 | `test_actions_layer.py`（`WRITE_NAMES`）、`test_chat_tools.py`、`test_owner_guard.py`、`test_mcp.py` 及 `git grep -l '"my_usage"' platform/tests` 列出的其餘檔，都已加入 `launch_pipeline` | 逐檔執行這些測試 | 全部通過；每個釘住工具名單或計數的檔都已含 `launch_pipeline`（沒有漏改而偶然沒被測到的名單） | 自動 |
| TC-023 | 作法「證據」（`test_owner_guard.py:150`）；017e「parity 表全列」；專長守則（對等性） | 功能 | 測試同時列舉「MCP 工具」與「動作層有 caller 的函式」 | 跑 `test_owner_guard.py` 的對等性檢查 | `launch_pipeline` 對應到 `request_pipeline_launch`；`request_pipeline_launch` 不再只登記為「網頁送出頁」（NO_TOOL 那條已移除或改寫為「MCP 也有出口」）；兩邊一一對應、沒有任一邊缺 | 自動 |
| TC-024 | 範圍「不准碰 web.py」；專長守則（對等性） | 功能 | `test_web_parity.py` 的四張表 | 跑 `test_web_parity.py` | 全綠；`request_pipeline_launch` 仍屬 INTERNAL，沒有因為新增工具而要求新增網頁路由 | 自動 |
| TC-025 | 完成標準「既有斷言除工具名單與計數外沒被刪或放寬」 | 功能 | 驗收者取得 base 與 HEAD 的 diff | 比對上述所有被改動的既有測試檔 | 改動只有工具名單與計數；沒有刪掉、放寬、跳過任何既有斷言（`test_chat_tools.py` 的 TC-002、TC-007、TC-008 等保持原樣） | 手動：驗收者比對 `git diff`，結果記入 ledger |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 不做第 1 條；裁決 2 | 不在範圍 | 取得伺服器工具清單 | 檢查清單 | 沒有 `create_pipeline`、`update_pipeline`、`export_pipeline`、`validate_pipeline`；工具總數就是 21 | 自動 |
| TC-027 | 不做第 2 條 | 不在範圍 | 取得網頁應用的路由表 | 找 `/act/launch_pipeline` | 沒有這條路由（對它發出請求得到「不存在」，而不是被處理）；`web.py`、`web_board.py`、`static/` 沒有變動 | 自動 |
| TC-028 | 不做第 3 條 | 不在範圍 | 載入 `confirm`、`request_pipeline_launch` 的既有測試 | 檢查 `confirm.JOB_KIND` 與確認頁邏輯 | `confirm.JOB_KIND` 與 base 相同、`confirm.py` 沒有變動；`request_pipeline_launch` 仍不在 `confirm` 的 `REQUEST_TOOLS` 內（既有 `test_pipeline_launch.py` 的簽名與共用後半段檢查維持通過、未被改） | 自動：`platform/tests/test_pipeline_launch.py` |
| TC-029 | 範圍「只准改這些」；「不准碰」清單 | 不在範圍 | 驗收者取得 `git diff --stat <base>...HEAD` | 檢查變動的檔案 | 只含：`mcp_server.py`、`actions/chat_tools.py`、新檔 `test_mcp_launch_pipeline.py`、以及釘住工具名單的既有測試；沒有碰 `web.py`、`web_board.py`、`static/`、`confirm.py`、`actions/__init__.py`、`docs/PLATFORM.md`、`pipeline_launch.py`、dev-queue.json、spec／test-case／constitution／ROADMAP／`.github/`／plugin.json | 手動：驗收者比對 `git diff --stat`，結果記入 ledger |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 原則 I.2 與安全網的送出規則：未經本人確認的送出，經 MCP 工具也要被擋，不是只有動作函式擋 | 例外 | 用 HTTP 傳輸、遠端呼叫（`remote` 為真）、客戶端不跳表單；甲有可送出的 pipeline | 甲的 token 呼叫 `launch_pipeline`，沒有任何人按好 | 沒有 job；回傳指出要到確認頁按好；token 本身不能當作「好」 | 自動 |
| TC-031 | 原則 I.2：確認頁的「按的人必須是發出請求的人」 | 例外 | 甲經 `launch_pipeline` 留下一張待確認請求；乙是另一位登入使用者 | 乙到確認頁對甲的這張請求按好 | 被拒絕，沒有 job；甲的請求仍是待確認 | 自動 |
| TC-032 | 專長守則（資料結構變動須附 migration 或寫明不需要） | 功能 | 對比 base 與 HEAD 的資料庫結構與 migration 檔 | 檢查結構與 diff | 沒有新增或修改任何資料表、欄位、migration 檔；`launch_pipeline` 只寫入既有的待確認請求（與 `launch` 同一個表）；因此不需要 migration | 自動 |
