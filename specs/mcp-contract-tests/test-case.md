# 測試案例：abf MCP 伺服器的記憶體內合約測試

**規格**：`specs/mcp-contract-tests/plan.md`（本任務為 tier C 測試任務，沒有獨立 spec.md；以計畫與「維護者原話」為準）　**總覽**：`test-case-overview.md`

說明用語：「工具」＝ Claude Desktop 等客戶端看得到、可呼叫的功能（例如 `launch`）；「記憶體內客戶端」＝ 測試程式自己扮演客戶端、不開網路埠直接連伺服器；「快照」＝ 把「現有工具名稱與各自接受的參數」存成一份進版控的 JSON 檔，之後有人改動就會被測試擋下；「凍結豁免清單」＝ 目前已知不合格、先登記起來、之後只准變少不准變多的名單；「寫入工具」＝ 會啟動、取消、刪除、續跑、重跑的 `launch`、`cancel`、`forget`、`resume`、`relaunch`。

所有 TC 的測試都是 `platform/tests/mcp/` 下的 pytest，函式內以註解寫明對應的 TC 編號。每條測試另須在 ledger 附一則「刻意破壞後變紅、還原後變綠」的證明（計畫「失敗先行測試」）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、不該做的事發生時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

## User Story 1 — 工具清單快照：改工具名或參數會被擋下（優先度 P1）

維護者原話 3：「list_tools names+input schemas snapshot as JSON (committed, normalize CRLF)」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 §3 名稱清單；原話 3；原話 2（用記憶體內客戶端） | 功能 | 以官方 SDK 的 `mcp.Client` 直接連 `build_server(...)`（不開行程、不開埠）；測試內有一份寫死的 24 個工具名稱清單，內容取自 base v3 實際 `list_tools` 輸出 | 呼叫 `list_tools()`，把名稱集合與寫死清單比對 | 兩邊完全相等；多一個或少一個工具測試都失敗，訊息指出多出或缺少的名稱。清單恰為 24 個（若實際不是 24 個，executor 回報而不是改數字） | 自動：`platform/tests/mcp/test_mcp_contract_tools.py::test_tool_names_match_explicit_list` |
| TC-002 | 作法 §3 快照；原話 3 | 功能 | `platform/tests/mcp/snapshots/tools.json` 已進版控，UTF-8、LF 行尾、內容只含每個工具的 `name` 與 `inputSchema`，依名稱排序，`sort_keys=True, indent=2, ensure_ascii=False` | 取得 `list_tools()` 的名稱與輸入結構，產生同格式文字，與快照檔比對 | 完全相同則通過；給任一工具加一個參數（刻意破壞）時變紅，訊息列出差異與「重新產生快照的指令」 | 自動：`test_mcp_contract_tools.py::test_tools_schema_matches_snapshot` |
| TC-003 | 作法 §3 快照缺檔／不符、預設不覆寫 | 例外 | 情況 A：快照檔不存在（用暫存目錄模擬）。情況 B：快照內容與實際不同。環境變數 `ABF_UPDATE_MCP_SNAPSHOT` 未設定 | 跑快照比對 | 兩種情況都失敗，訊息含重新產生快照的指令（提到 `ABF_UPDATE_MCP_SNAPSHOT=1`）；快照檔不被改寫、不被建立。只有設為 `1` 時才寫檔 | 自動：`test_mcp_contract_tools.py::test_snapshot_missing_or_different_fails_without_overwrite` |
| TC-004 | 作法 §3 CRLF；原話 3「normalize CRLF」 | 功能 | 把快照檔的暫存複本全部換成 CRLF 行尾（Windows 的 git autocrlf 會造成的狀況） | 用與 TC-002 相同的比對程式比對 | 仍然通過（讀檔後兩邊都先把 `\r\n` 換成 `\n`）；真正的內容差異仍然會失敗 | 自動：`test_mcp_contract_tools.py::test_snapshot_is_crlf_insensitive` |

## User Story 2 — 描述檢查：每個工具的說明文字合格（優先度 P1）

維護者原話 4：「description lint (what/when/when-not/params/return/next-step, <= ~600 chars, every param described)」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-005 | 作法 §4 長度；原話 4「<= ~600 chars」 | 功能 | 測試內有 `OVER_LIMIT = {工具名: 目前長度上限}` 凍結清單（已知含 `launch` 約 1,300、`resume`、`forget`、`get_run`、`read_run_file` 等，以實測值填入），旁有「這是技術債、改短後請刪除該項」的註解 | 對 24 個工具各量 `len(description)` | 不在清單內的工具全部 ≤ 600 字元；清單內的工具長度 ≤ 清單記的上限（變長就紅）；把某描述加長（刻意破壞）會變紅；清單每一項在 ledger 逐項列出供維護者決定；產品描述文字不被改 | 自動：`test_mcp_contract_tools.py::test_descriptions_within_limit`、`::test_over_limit_list_only_shrinks` |
| TC-006 | 作法 §4 六面向；原話 4「what/when/when-not/params/return/next-step」；專長守則（何時用／何時不要用） | 功能 | 測試內有六個面向的關鍵詞判斷（what＝第一句非空；when-not＝含 `does NOT`／`Only for`／`never`／`cannot`／`not` 之一；next-step、return 依計畫列的詞）；另有「凍結豁免清單（工具名＋面向）」，旁註明「這是描述的缺口，不是測試放水」 | 對每個工具逐面向檢查 | 每個工具、每個面向要嘛通過，要嘛在豁免清單內；不在清單內的缺口使測試失敗；刪掉某描述的 when-not 句（刻意破壞）會變紅；清單只准縮小，且每一項在 ledger 逐項列出 | 自動：`test_mcp_contract_tools.py::test_descriptions_cover_the_six_aspects` |
| TC-007 | 作法 §4 每個參數都有說明；原話 4「every param described」；專長守則（沒有說明的參數視為未完成） | 功能 | 取得每個工具 `inputSchema.properties` 的所有參數名；另有參數說明的凍結豁免清單 | 對每個參數，檢查 schema 的 `description` 欄或工具描述文字有沒有提到該參數名 | 兩者皆無且不在豁免清單內 → 失敗；全部通過或在清單內才綠；清單只准縮小，每一項在 ledger 列出 | 自動：`test_mcp_contract_tools.py::test_every_param_is_described` |
| TC-008 | 作法 §4 附帶；專長守則（密鑰不得出現在工具輸出） | 例外 | 24 個工具的描述文字 | 檢查描述有無 `\n\n` 以外的控制字元，有無密鑰樣式（`token`、`Bearer ` 加長字串） | 都沒有才通過；塞入一個假的 `Bearer abcdef...` 長字串到被檢查文字（測試內小例）時偵測得到而失敗 | 自動：`test_mcp_contract_tools.py::test_descriptions_have_no_control_chars_or_secrets` |

## User Story 3 — 寫入工具的零副作用名單（優先度 P1）

維護者原話 5：「every write tool called once = zero side effect (backend mock not called)」。實際「呼叫一次不改資料」的 TC 放在下面「憲法與安全網」一節（TC-010、TC-011）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-009 | 作法 §5 名單推導 | 功能 | 測試內有明確寫入工具名單 `launch`、`cancel`、`forget`、`resume`、`relaunch` | 從 `list_tools` 的 annotations 取出 `readOnlyHint` 為 false 的工具 | 推導出的集合與明確名單完全相等；若有人新增寫入工具而沒補測試，這條失敗並指出新工具名 | 自動：`platform/tests/mcp/test_mcp_contract_writes.py::test_write_tools_derived_from_annotations_equal_explicit_list` |

## 憲法與安全網

涉及：Safety Net 與 Constitution 5.0.0 對「啟動／取消／刪除只有本人說好才算」的規定（`.specify/memory/constitution.md` 約第 186 行起，`platform/abf_platform/actions` 只從終端、表單或確認頁接受本人的「好」），以及 Constitution 4.0.0「只有一條送出路徑」。下面兩條證明合約測試真的抓得到「單次呼叫就偷偷動手」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | Safety Net：寫入需本人說好；作法 §5；原話 5 | 功能 | 用 repo 的 `plat` 夾具／`human_harness.World` 建出有一位使用者與一個環境的真實資料庫；記憶體內客戶端不宣告 elicitation（詢問表單）能力，等於沒人回答「好」；動作層的真正寫入點（`confirm.approve`、建立 job 的函式，名稱由 executor 在 `confirm.py`、`actions/__init__.py` 確認）以會 `pytest.fail` 的函式取代 | 對 `launch`、`cancel`、`forget`、`resume`、`relaunch` 各呼叫一次（5 個參數化案例，每個測試只開一個 Client） | 每一個都：`jobs` 表列數不變、`launch_nextflow`／`cancel`／`forget` 對應工作列數為 0、`confirmations` 至多一筆且 `state='pending'`（不是 approved）、站台沒收到任何指令、`forget` 沒有刪任何 run 資料夾，且被換成 `pytest.fail` 的寫入點完全沒被碰到。把某個 `request_*` 暫時改成直接建 job（刻意破壞）會變紅。若找不到寫入點名稱，只用資料庫比對，並在 ledger 說明 | 自動：`test_mcp_contract_writes.py::test_write_tool_called_once_has_no_side_effect[launch\|cancel\|forget\|resume\|relaunch]` |
| TC-011 | Safety Net：不得宣稱已啟動；作法 §5 回傳值 | 功能 | 同 TC-010 | 對上述 5 個工具各呼叫一次，讀回傳內容 | 回傳 `sent` 為 false，且含確認頁位址或表單提示；內容沒有任何「已啟動／已取消／已刪除」的宣稱 | 自動：`test_mcp_contract_writes.py::test_write_tool_reply_says_not_sent` |

## User Story 4 — 每個工具一條可操作的錯誤路徑（優先度 P1）

維護者原話 6：「one error path per tool (actionable message, no secret/stack)」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 作法 §6 可操作；原話 6「actionable message」；專長守則（說發生什麼、為什麼、下一步） | 例外 | 參數化涵蓋 `list_tools` 的全部 24 個工具（讀取與寫入）；每個工具給一組必然失敗的輸入（不存在的 `run_id`／`run_name`／`compute_env`／`pipeline` 等）；executor 先印出實際回應再寫斷言 | 逐一呼叫 | 每個工具的結果是錯誤（`isError` 為真，或回傳 dict 帶 `error`／`state`，以實際行為為準）；訊息含失敗的物件名稱，且含下一步的動詞（請／用／先）；不得為了讓測試綠而改產品 | 自動：`test_mcp_contract_writes.py::test_error_path_is_actionable_and_clean[<每個工具>]`（可操作部分） |
| TC-013 | 作法 §6 乾淨；原話 6「no secret/stack」；專長守則（不露堆疊、路徑、SQL、密鑰） | 例外 | 同 TC-012；夾具有建立 PAT（個人存取權杖）值 | 檢查每個工具錯誤回應的全文 | 不含 `Traceback`、`File "`、`.py"`、`sqlite3`、`SELECT `、絕對路徑（`/home`、`C:\`、暫存路徑）、`Bearer `，也不含夾具 PAT 的值；暫時讓某錯誤訊息帶出路徑（刻意破壞）會變紅 | 自動：`test_mcp_contract_writes.py::test_error_path_is_actionable_and_clean[<每個工具>]`（乾淨部分） |
| TC-014 | 作法 §6 缺必填參數 | 例外 | 對每個有必填參數的工具，呼叫時省略必填參數 | 逐一呼叫 | 被拒絕（由 SDK 驗證），且回應不是堆疊 | 自動：`test_mcp_contract_writes.py::test_missing_required_param_is_rejected_without_stack` |
| TC-015 | 作法 §6 產品缺口處理；裁決 3 | 例外 | 若某工具現行錯誤訊息不合 TC-012／TC-013（例如露出路徑） | 該案例標示處理 | 該案例標 `pytest.mark.xfail(strict=True, reason=...)`（一旦產品修好就轉紅，逼人拿掉標記），並在 ledger 與回報逐項列出；`platform/abf_platform/` 沒有任何改動；若沒有任何缺口則 ledger 明寫「無 xfail」 | 自動：xfail 標記存在於上述測試檔；`git diff --stat origin/v3` 由閱卷核對 |

## User Story 5 — 站台遠端工具走真的 HTTP（優先度 P1）

維護者原話 7：「one HTTP-transport case for remote-site tools (past bug)」；原話 8 的「port already in use」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 作法 §7；原話 7、8（埠被占用）；專長守則（HTTP 另加測試） | 功能 | 以子行程啟動 HTTP 伺服器（沿用 `helpers.free_port()`、`start_cli`、`wait_port`、`mcp_http_call` 與 `test_mcp.py` 的啟動方式，Host 用 127.0.0.1，帶 PAT 的 `Authorization: Bearer`）；站台沒有線上代理；不寫死埠號；不在測試行程內用 `uvicorn.run` | 呼叫 `list_site_files` | 回應是 `state` 為 loading／離線的說明，不是 500、不是連線中斷（`RemoteDisconnected`）；`finally` 一定 `stop_proc`；`wait_port` 逾時時，子行程記錄檔尾端印進失敗訊息；連跑 3 次不因埠殘留而失敗。環境起不來（原生 Windows）→ 標 UNVERIFIED 並寫明要在 WSL／Linux 跑 | 自動：`platform/tests/mcp/test_mcp_contract_http.py::test_site_tools_over_http` |
| TC-017 | 作法 §7 名稱兩邊相等 | 功能 | 同 TC-016 的 HTTP 伺服器，另有同一份索引的記憶體內客戶端 | 兩邊各呼叫 `list_tools` | 工具名稱集合完全相等（各用各自的埠，不與其他測試共用） | 自動：`test_mcp_contract_http.py::test_http_and_inproc_list_the_same_tools` |
| TC-018 | 作法 §7 反例 | 例外 | 同 TC-016 的 HTTP 伺服器 | 不帶 token 對 `/mcp` 發請求 | 回 401，回應內文不含堆疊（無 `Traceback`、`File "`） | 自動：`test_mcp_contract_http.py::test_http_without_token_is_401` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 「不做」：不改產品程式、不改 abf_station、不新增相依；原話 8、9「Files allowed: new tests/mcp/** only, no product code changes. Do not touch platform/abf_station/」 | 不在範圍 | 實作完成後的 worktree | 看 `git diff --stat origin/v3`；看新測試資料夾與測試檔 | 變動只出現在 `platform/tests/mcp/**`；`platform/abf_platform/`、`platform/abf_station/`、`platform/pyproject.toml`、`platform/constraints.txt`、既有測試零改動；`platform/tests/mcp/` 內沒有 `__init__.py`；新測試不 import pytest-asyncio、不用 `asyncio_mode=auto`，一律同步函式內 `asyncio.run(...)`，每個測試只開一個 `Client`；不使用 `FastMCP` 或 `create_connected_server_and_client_session`。描述超過 600 字元只列豁免清單，沒有被縮短 | 自動：測試內斷言無 `__init__.py`、無 pytest-asyncio 依賴；其餘由閱卷以 `git diff --stat` 核對 |
| TC-020 | 「不做」：快照不含描述、不測 stdio／OAuth／跨使用者 | 不在範圍 | 新增的快照檔與測試檔 | 讀快照 JSON 的欄位；讀新測試檔涵蓋的內容 | 快照每個工具只有 `name` 與 `inputSchema`，沒有 `description`；新測試沒有 stdio 傳輸案例、沒有 OAuth 流程案例、沒有「以兩位使用者 PAT 重跑讀取工具」的跨使用者案例（這些屬既有測試或後續切片）；記憶體內測試只涵蓋本機呼叫者 | 自動：`test_mcp_contract_tools.py::test_snapshot_has_only_name_and_input_schema`；其餘由閱卷讀檔核對 |
