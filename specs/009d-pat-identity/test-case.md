# 測試案例：009d 個人存取權杖（PAT）——讓平台認得「誰在呼叫」，HTTP MCP 現在必須帶權杖

**規格**：無 `spec.md`（依維護者指示一律以 `specs/009d-pat-identity/plan.md` 為準；plan 的「給維護者」三句是他看得懂的承諾）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、有人想繞過時，系統怎麼反應（拒絕、停下）。
- **不在範圍**：計畫「Not in this PR」明講這次不做的事；測試確認它真的沒做。

維護者的話（計畫「給維護者」，逐字）：

1. 「權杖只在終端機建立與撤銷，只顯示一次。」
2. 「`mcp --http` 現在必須帶 `Authorization: Bearer <PAT>`，否則 401；stdio（本機）不變、不用權杖。」
3. 「送出與取消仍然只能在終端機按 y；身分只是被記錄下來，不是新的確認方式。角色（010）、OAuth、公開網址都不在這一步。」

下面 TC-A02、TC-A07、TC-B01、TC-B10、TC-D05、TC-D06、TC-D08、TC-F01 至 TC-F03 直接用這三句當輸入與預期結果。

名詞：**PAT**＝個人存取權杖（personal access token），一串只發給某位使用者的密碼，值以 `abf_pat_` 開頭；**tokens.db**＝只存權杖雜湊（hash，單向轉換後的指紋，看不出原值）的資料庫；**canary 掃描**＝先造一個已知的假值，再把整個資料庫檔案逐位元組找這個值，找到就算洩漏；**401**＝HTTP「未授權」；**stdio**＝本機標準輸入輸出，MCP 的本機連線方式；**caller（呼叫者）**＝`Caller(user_id, name, lab)`，代表「是哪位使用者在呼叫」，`None` 代表本機終端機／stdio；**TERMINAL**＝只代表「人在終端機按了 y」的專用記號；**AST 掃描**＝用程式讀原始碼的結構（不是只搜文字）來檢查誰引用了誰；**夾具（fixture）**＝測試開始前造好的假資料，PAT 一律在測試執行時才造，不寫成檔案裡的字面值。

「前後一樣」的基準＝計畫起點 `v3`（009b 合併之後）的行為。

## User Story 1 — 建立使用者、發個人權杖，只在終端機、只顯示一次（優先度 P1）

維護者原話：「權杖只在終端機建立與撤銷，只顯示一次。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-A01 | 計畫·設計 3（`user add`）；給維護者 第 1 句 | 功能 | 乾淨的 tokens.db，還沒有任何使用者 | 在終端機執行 `abf-platform user add <姓名> --lab <實驗室>` | 指令成功結束；之後可以用這個姓名替他發 PAT（`pat new --user <姓名>` 成功）；`abf-platform --help` 列得出 `user`、`pat` 指令 | 自動：`platform/tests/test_pat.py` |
| TC-A02 | 計畫·設計 1、3；給維護者 第 1 句：「只顯示一次」 | 功能 | 已有一位使用者 | 執行 `abf-platform pat new --user <姓名>` | 標準輸出裡出現一串以 `abf_pat_` 開頭的權杖，且與 `token new` 同樣用「只顯示一次、之後無法再顯示、只留雜湊」的說法；權杖後面接 `secrets.token_urlsafe(32)` 長度的隨機字串；連續發兩次得到兩個不同的值 | 自動：`test_pat.py` |
| TC-A03 | 計畫·設計 3（`--label`） | 功能 | 已有一位使用者 | `pat new --user <姓名> --label 筆電`，再執行 `pat list` | `pat list` 的那一列看得到標籤「筆電」 | 自動：`test_pat.py` |
| TC-A04 | 計畫·設計 3（`pat list`） | 功能 | 一位使用者有兩把 PAT，其中一把已撤銷 | 執行 `pat list` | 每把一列，列出 id、使用者、標籤、建立時間、是否已撤銷；已撤銷的那把標示為已撤銷；整份輸出裡找不到任何 PAT 的值，也找不到它的 SHA-256 雜湊 | 自動：`test_pat.py` |
| TC-A05 | 計畫·設計 1；Changes 第 2 步（canary 掃描） | 功能 | 執行時才造出的 PAT（fixture） | 發 PAT 後，逐位元組掃描整份 tokens.db 與 index.db | 兩個檔案都找不到 PAT 的值；tokens.db 裡只有它的雜湊（`_hash`，SHA-256）；使用者的姓名與實驗室存在 tokens.db 的 `users` 表，不在 index.db | 自動：`test_pat.py`（與 `test_secrets.py` tc040 同一寫法） |
| TC-A06 | 計畫·設計 3（`pat revoke`）；給維護者 第 1 句：「撤銷」 | 功能 | 一位使用者有一把有效 PAT | 執行 `pat revoke <id>` | 指令成功；`pat list` 該列標示已撤銷；同一把 PAT 之後被拒絕（對應 TC-B05）；同一位使用者的另一把 PAT 仍然有效 | 自動：`test_pat.py` |
| TC-A07 | 計畫·設計 3：「nothing else prints or logs it」；給維護者 第 1 句 | 功能 | 一位使用者與一把剛發的 PAT | 收集這些輸出並逐一搜尋 PAT 的值：`user add`、`pat list`、`pat revoke`、各種錯誤輸出、`mcp --http` 伺服器本身的標準輸出／錯誤輸出（含用這把 PAT 成功呼叫、被拒絕呼叫之後） | 只有 `pat new` 的標準輸出含有 PAT；其餘全部找不到 | 自動：`test_pat.py` |
| TC-A08 | 計畫·設計 1；Changes 第 2 步（an old tokens.db migrates） | 功能 | 一份舊格式 tokens.db（只有 008 的欄位、沒有 `user_id`、沒有 `users` 表），內含一把舊 run 權杖 | 用新程式開啟，然後建立使用者、發 PAT | 開啟不出錯；舊 run 權杖仍然查得到、種類仍是 `run`；新增了 `user_id` 欄位與 `users` 表；新發的 PAT 可用 | 自動：`test_pat.py` |
| TC-A09 | 給維護者 第 1 句：「先建立使用者，再替他發 PAT」 | 例外 | 沒有名為 `nobody` 的使用者 | 執行 `pat new --user nobody` | 被拒絕（非零結束碼，有說明）；沒有發出任何權杖，tokens.db 裡沒有新增列 | 自動：`test_pat.py` |
| TC-A10 | 計畫·設計 1（`name UNIQUE`） | 例外 | 已有使用者「王小明」 | 再執行一次 `user add 王小明 --lab <另一個實驗室>` | 被拒絕；`users` 表仍然只有一列，原本的實驗室沒有被改掉 | 自動：`test_pat.py` |
| TC-A11 | 計畫·設計 3：「No MCP tool, no web route, no action for these」 | 功能 | 伺服器與接收端（receiver）建好 | 列出 MCP 工具；列出接收端與 `abf_platform.actions` 的所有路由／函式 | MCP 工具仍然正好六個，名稱與輸入欄位裡沒有 `user`、`pat`、`token`；接收端沒有任何建立或撤銷使用者／PAT 的路由；`actions` 裡沒有建立或撤銷使用者／PAT 的函式。建立與撤銷只存在於終端機指令 | 自動：`test_pat.py` |
| TC-A12 | 計畫·設計 1（`create_token` 只接受已知種類） | 例外 | 無 | 呼叫 `create_token(path, kind="admin")`（種類不是 run／agent／pat） | 丟 `ValueError`；沒有寫入任何權杖 | 自動：`test_pat.py` |

## User Story 2 — `mcp --http` 必須帶權杖，否則 401；本機 stdio 不變（優先度 P1）

維護者原話：「`mcp --http` 現在必須帶 `Authorization: Bearer <PAT>`，否則 401；stdio（本機）不變、不用權杖。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-B01 | 給維護者 第 2 句；設計 4 | 例外 | 啟動 `mcp --http`（本機迴圈位址），資料庫裡有一位使用者 | 不帶任何 `Authorization` 標頭，送出 MCP 請求 | 回應 401，並帶標頭 `WWW-Authenticate: Bearer`；沒有任何工具被執行 | 自動：`test_pat.py`；`test_mcp.py` tc025 的「沒帶標頭」情形 |
| TC-B02 | 設計 4（wrong scheme） | 例外 | 同上，另有一把有效 PAT | 標頭寫成 `Authorization: Basic <有效 PAT>`，以及 `Authorization: Token <有效 PAT>` | 兩種都回應 401 與 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-B03 | 設計 4（malformed） | 例外 | 同上 | 標頭寫成 `Authorization: Bearer`（後面沒有值），以及 `Authorization: Bearer `（只有空白） | 都回應 401 與 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-B04 | 設計 4（unknown / garbage） | 例外 | 同上 | 標頭寫成 `Bearer garbage`，以及一串長得像 PAT 但從沒發過的 `Bearer abf_pat_<隨機>` | 都回應 401 與 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-B05 | 計畫 Changes 第 2 步：revoked → 401 | 例外 | 一把 PAT，先用它成功呼叫一次 | 執行 `pat revoke`，不重啟伺服器，再用同一把 PAT 呼叫 | 第一次成功；撤銷之後同一把 PAT 回應 401 | 自動：`test_pat.py` |
| TC-B06 | 設計 2、`lookup_pat`：disabled user = None | 例外 | 一位使用者有一把有效 PAT；測試夾具直接把該使用者的 `disabled_at` 設成現在 | 用該 PAT 呼叫 | 回應 401（權杖本身沒被撤銷，但使用者已停用） | 自動：`test_pat.py` |
| TC-B07 | 設計 4：「body never echoes the token」 | 例外 | 送出一把已撤銷的 PAT、一把亂寫的 Bearer 值 | 收集 401 回應的內容與全部標頭，搜尋送出的權杖值 | 回應本文與標頭裡都找不到送出的權杖值 | 自動：`test_pat.py` |
| TC-B08 | 設計 4；給維護者 第 2 句；Changes 第 2 步（valid PAT → six tools） | 功能 | 一把有效 PAT | 帶 `Authorization: Bearer <PAT>` 連 `mcp --http`，列出工具 | 正好六個工具：`get_compute_env`、`get_run`、`list_agents`、`list_compute_envs`、`list_runs`、`list_site_files` | 自動：`test_pat.py`；`test_mcp.py` tc025 |
| TC-B09 | Changes 第 2 步：「same answers as stdio」 | 功能 | 資料庫裡有三個 run（既有 fixture）、一把有效 PAT | 分別經 stdio 與經 HTTP＋PAT 呼叫 `list_runs`、`get_run`（真實 id）、`list_compute_envs`、`list_agents` | 兩條路的回傳內容逐欄相同 | 自動：`test_pat.py` |
| TC-B10 | 給維護者 第 2 句：「stdio（本機）不變、不用權杖」 | 功能 | tokens.db 裡完全沒有使用者與 PAT | 啟動 `mcp`（stdio）並列出工具、呼叫 `list_runs` | 不需要任何權杖就成功；回傳與 `v3` 相同 | 自動：`test_pat.py`；既有 `test_mcp.py` 其餘測試不改動全綠 |
| TC-B11 | 設計 7：no users yet | 功能 | tokens.db 裡沒有任何使用者 | 啟動 `mcp --http` | 伺服器正常啟動不退出；終端機印出一行說明「還沒有使用者，所以每個請求都會是 401」；實際送出任何請求都回 401 | 自動：`test_pat.py` |
| TC-B12 | 設計 6：non-loopback host | 功能 | 無 | 以非迴圈位址（例如 `--host 0.0.0.0`）啟動 `mcp --http` | 仍印出原本的風險提示（`_risk_line`），並多一句說明需要權杖；以迴圈位址啟動不印風險提示 | 自動：`test_pat.py`（或 `test_cli.py` 既有寫法旁） |
| TC-B13 | 設計 6：「no flag or env var turns auth off」 | 例外 | 無 | 執行 `mcp --http --no-auth`、`--insecure`、`--no-token`；另用 AST 掃 `http_auth.py`、`mcp_server.py`、`cli.py` 的 `cmd_mcp` | 三個旗標都被命令列解析器拒絕（unrecognized arguments）；`http_auth.py` 與 `mcp_server.py` 沒有讀任何環境變數；`mcp` 的 `--help` 沒有任何關閉驗證的選項 | 自動：`test_pat.py` |
| TC-B14 | 設計 4：「sets a contextvars caller for the request」 | 功能 | 兩位使用者各有一把 PAT | 依序送：A 的有效請求、不帶標頭的請求、B 的有效請求 | A 的請求看到的呼叫者是 A；不帶標頭的請求是 401，沒有沿用 A；B 的請求看到的呼叫者是 B（呼叫者不會殘留到下一個請求） | 自動：`test_pat.py` |
| TC-B15 | Changes 第 5 步：tc025 只改輸入 | 功能 | 對 `v3` 比較 `platform/tests/test_mcp.py` 的 diff | 驗收審查者讀 diff | tc025 的改動只有「建使用者、發 PAT、送標頭」；它的斷言（回應與工具清單）一字未動、沒有放寬；其他測試未動；`ledger.md` 列出這是唯一輸入被改的釘住測試 | 手動：驗收審查者讀 diff 與 `ledger.md` |

## User Story 3 — 一種權杖只開一扇門（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | 設計 2：PAT 在接收端被拒絕 | 例外 | 一把有效 PAT；接收端（Nextflow 回報訊息的入口）建好 | 用這把 PAT 當 Nextflow 的存取權杖送訊息到接收端 | 被拒絕，方式與未知權杖相同；沒有建立任何 run、沒有寫入索引 | 自動：`test_pat.py` |
| TC-C02 | 設計 2：PAT 在 agent 入口被拒絕 | 例外 | 一把有效 PAT；agent 入口（心跳、領工作）建好 | 用這把 PAT 當 agent 權杖呼叫 agent 的每個入口 | 全部被拒絕，方式與未知權杖相同；沒有 agent 被登記、沒有工作被領走 | 自動：`test_pat.py` |
| TC-C03 | 設計 2：run 權杖在 MCP 被拒絕 | 例外 | 一把有效 run 權杖（`token new` 發的） | 用它當 Bearer 連 `mcp --http` | 回應 401 與 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-C04 | 設計 2：agent 權杖在 MCP 被拒絕 | 例外 | 一把有效 agent 權杖（`agent-token new` 發的） | 用它當 Bearer 連 `mcp --http` | 回應 401 與 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-C05 | 設計 2：`lookup_pat` 回傳值 | 功能 | 一位使用者與一把有效 PAT | 呼叫 `lookup_pat(tokens_path, PAT)` | 回傳含 `user_id`、`name`、`lab`、`token_id` 四個欄位，值與該使用者與該權杖一致 | 自動：`test_pat.py` |
| TC-C06 | 設計 2：`lookup_pat` 的 None 情形 | 例外 | 已撤銷的 PAT、使用者已停用的 PAT、從沒發過的值、空字串、`None`、run 權杖、agent 權杖 | 逐一呼叫 `lookup_pat` | 全部回傳 `None`，不丟例外 | 自動：`test_pat.py` |
| TC-C07 | 計畫「Pinned guards」：`test_cli.py`、`test_station_envs.py` 的 tokens.db 檢查 | 功能 | 既有測試 | 執行 `test_cli.py`、`test_station_envs.py`、`test_receiver.py` | 全綠；`token new`、`agent-token new`、`agent-token revoke` 的行為與輸出與 `v3` 相同 | 自動：既有測試不改動 |

## User Story 4 — 身分只是被記錄，不是新的確認方式（優先度 P1）

維護者原話：「送出與取消仍然只能在終端機按 y；身分只是被記錄下來，不是新的確認方式。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-D01 | 設計 5：讀取動作多一個 `caller=None` | 功能 | 六個讀取動作 | 檢查簽名；分別不帶、帶 `caller=None`、帶一個 `Caller` 呼叫同一動作 | `caller` 是只能用關鍵字傳的參數、預設 `None`；三種呼叫的回傳內容完全相同（讀取動作忽略 caller） | 自動：`test_pat.py` 或 `test_actions_layer.py` |
| TC-D02 | Changes 第 2 步：「a spy on a read action sees the user」 | 功能 | 把某個讀取動作換成記錄參數的替身；一位使用者與其 PAT | 帶該 PAT 經 HTTP 呼叫對應的 MCP 工具 | 替身收到的 `caller` 是該使用者的 `Caller(user_id, name, lab)`，三個欄位都對 | 自動：`test_pat.py` |
| TC-D03 | 設計 5：`None` 代表本機 stdio | 功能 | 同上替身 | 經 stdio 呼叫同一工具 | 替身收到的 `caller` 是 `None` | 自動：`test_pat.py` |
| TC-D04 | 設計 5：`Caller` 是 frozen | 功能 | 一個 `Caller` | 嘗試改它的 `name` | 丟錯（不可修改）；它有且只有 `user_id`、`name`、`lab` 三個欄位 | 自動：`test_pat.py` |
| TC-D05 | 給維護者 第 3 句；Changes 第 2 步：`confirmed_by="yes", caller=u` 仍被拒 | 例外 | 一位使用者 `u`；一個空的平台資料庫 | 呼叫 `launch(..., confirmed_by="yes", caller=u)` | 丟 `JobRefused`（沒有人類確認管道）；沒有確認紀錄列、沒有工作被排入 | 自動：`test_pat.py` |
| TC-D06 | 給維護者 第 3 句 | 例外 | 同上 | 呼叫 `cancel(..., confirmed_by="yes", caller=u)` | 同 TC-D05：被拒、什麼都沒寫入 | 自動：`test_pat.py` |
| TC-D07 | 設計 5：「`confirmed_by` check stays first」 | 例外 | 一個「還不存在」的狀態資料庫路徑；一位使用者 `u` | 呼叫 `launch(path, ..., confirmed_by=None, caller=u)`（以及 `True`、長得像 TERMINAL 的字串） | 在開任何資料庫之前就被拒絕，路徑沒有被建立；只帶 `caller` 不算確認 | 自動：`test_pat.py` |
| TC-D08 | 設計 5；Changes 第 2 步：`launch(TERMINAL, caller=u)` | 功能 | 一位使用者 `u`、一個可排工作的環境與一份合法 bundle | 呼叫 `launch(..., confirmed_by=TERMINAL, caller=u)` | 排入剛好一個工作；確認紀錄列上有使用者 `u` 的姓名與 id | 自動：`test_pat.py` |
| TC-D09 | 設計 5（cancel 對稱） | 功能 | 同上，要取消一個執行中的 run | 呼叫 `cancel(..., confirmed_by=TERMINAL, caller=u)` | 排入剛好一個取消工作；確認紀錄列上有 `u` 的姓名與 id | 自動：`test_pat.py` |
| TC-D10 | 設計 5：`abf_launch/cli.py` 傳 `caller=None` | 功能 | 終端機的送出／取消流程 | 從終端機走一次送出與一次取消（既有測試的寫法）；並讀 `abf_launch/cli.py` | 行為與輸出與 `v3` 相同；確認紀錄列的使用者欄為空（NULL）；`abf_launch/cli.py` 呼叫 `actions.launch`／`actions.cancel` 時明確傳 `caller=None` | 自動：既有 `test_launch_cli.py`、`test_launch_platform.py` 不改動全綠＋`test_pat.py` |
| TC-D11 | 設計 5：確認紀錄的新欄位「migrated in place」 | 功能 | 一份舊格式 platform.db（confirmations 沒有使用者欄）且有一筆舊確認 | 用新程式開啟後再送一次確認 | 開啟不出錯；舊紀錄還在、使用者欄為 NULL；新紀錄有使用者 | 自動：`test_pat.py` |
| TC-D12 | 設計 4：import 規則；Changes 第 2、5 步 AST | 功能 | 原始碼 | 用 AST 掃 `mcp_server.py` 與 `http_auth.py` | `mcp_server.py` 引用 abf_platform 內部模組只有 `actions` 與 `http_auth`，且仍然沒有出現 `launch`、`cancel`、`TERMINAL`、`confirm`；`http_auth.py` 引用 abf_platform 內部模組只有 `store` 與 `actions.Caller`；009b 的 import 規則測試只多放行 `http_auth` 這一個名字；只有 `abf_launch/cli.py` 引用 `actions.launch\|cancel\|TERMINAL` | 自動：`test_pat.py`、`test_actions_layer.py` |

## User Story 5 — 文件、標頭、整體綠燈與紀錄（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-E01 | 計畫「Pinned guards」：tc070 標頭規則 | 功能 | 新增 `http_auth.py` 及其他新 `.py` | 執行 `test_scope.py` | 每個新 `.py` 第一行是 `# Not X: <理由>` 或 `# Nothing existing: ...`；測試全綠 | 自動：`platform/tests/test_scope.py` tc070 |
| TC-E02 | Changes 第 6 步 | 功能 | 讀 `docs/PLATFORM.md` | 驗收審查者照文件操作 | 文件寫了：身分是什麼（使用者、實驗室）、如何 `user add` 與 `pat new`、PAT 只顯示一次、`mcp --http` 要帶 `Authorization: Bearer <PAT>`、怎麼把 PAT 放進用戶端；步驟具體到能照做 | 手動：驗收審查者讀 `docs/PLATFORM.md` |
| TC-E03 | Changes 第 6 步 | 功能 | 讀 `CHANGELOG.md` | 驗收審查者找 3.0.0-dev 區段 | 有一行寫明 breaking：`mcp --http` 需要 PAT | 手動：驗收審查者讀 `CHANGELOG.md` |
| TC-E04 | Changes 第 7 步 | 功能 | 實作完成 | `cd platform && python -m pytest -q`；WSL 內 `bash tests/run_all.sh` | 兩者全綠（CI 同） | 自動：CI；`platform/tests/`；`tests/run_all.sh` |
| TC-E05 | Changes 第 1、2、7 步 | 功能 | 讀 `specs/009d-pat-identity/ledger.md` | 驗收審查者核對 | 有「SDK 確實提供 streamable HTTP 的 ASGI app、如何包它」的事實紀錄；有寫測試後、寫程式前的 FAIL 證據，以及之後的 PASS 證據 | 手動：驗收審查者讀 `ledger.md` |
| TC-E06 | 計畫「Pinned guards」：釘住的測試不動 | 功能 | 對 `v3` 比較全部被改的測試檔 | 驗收審查者讀 diff | `test_mcp.py` tc024、`test_launch_platform.py` TC-010／TC-061、`test_secrets.py` tc040、`test_cli.py`、`test_station_envs.py` 沒有被刪除、放寬或跳過任何斷言；唯二被改的既有測試是 tc025（只改輸入）與 009b 的 import 規則測試（只多一個名字 `http_auth`） | 手動：驗收審查者讀 diff |

## 不在範圍（計畫「Not in this PR」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-F01 | 不在範圍：OAuth 2.1、discovery metadata；給維護者 第 3 句 | 不在範圍 | 啟動 `mcp --http`，有一把有效 PAT | 帶 PAT 要 `/.well-known/oauth-protected-resource` 與 `/.well-known/oauth-authorization-server`；看 401 回應的 `WWW-Authenticate` | 這兩個路徑回 404（沒有 metadata）；401 的標頭就是 `Bearer`，沒有 `resource_metadata` 等 OAuth 欄位；伺服器沒有設 SDK 的 `AuthSettings` | 自動：`test_pat.py` |
| TC-F02 | 不在範圍：公開網址、TLS；給維護者 第 3 句 | 不在範圍 | 讀 `cli.py` 的 `mcp` 子指令與 `run_http` | 看可用選項與啟動參數 | 沒有 `--ssl`／`--cert`／`--public-url` 之類選項；`run_http` 仍是明文 HTTP（只有 host、port） | 自動：`test_pat.py` |
| TC-F03 | 不在範圍：角色／PI／實驗室權限（010）；給維護者 第 3 句 | 不在範圍 | 兩位不同實驗室的使用者，各有 PAT | 各自呼叫六個工具 | `users` 表只有 id、name、lab、created_at、disabled_at 五欄，沒有角色欄；兩人看到的答案完全相同（實驗室只是被記錄，不影響可見範圍） | 自動：`test_pat.py` |
| TC-F04 | 不在範圍：每位使用者的算力環境限制 | 不在範圍 | 兩位使用者、兩個算力環境 | 兩人各自呼叫 `list_compute_envs`、`get_compute_env`、`list_site_files` | 兩人看到同樣的兩個環境；沒有任何按使用者過濾或限額的欄位或邏輯 | 自動：`test_pat.py` |
| TC-F05 | 不在範圍：權杖到期或輪替 | 不在範圍 | 一把剛發的 PAT | 用 `ABF_PLATFORM_CLOCK_OFFSET` 把時鐘撥快一年，再用該 PAT 呼叫；列出 `pat` 的子指令 | PAT 仍然有效（tokens 表中該 PAT 的 `expires_at` 為空）；`pat` 只有 `new`、`list`、`revoke`，沒有輪替（rotate）或續期指令 | 自動：`test_pat.py` |
| TC-F06 | 不在範圍：網頁登入（011+） | 不在範圍 | 接收端與 MCP 伺服器建好 | 列出所有路由；對各路由觀察回應 | 沒有登入／登出／session 路由；沒有任何回應設 cookie | 自動：`test_pat.py` |
| TC-F07 | 不在範圍：新的確認方式、MCP 裡的 PAT／使用者工具；給維護者 第 3 句 | 不在範圍 | 原始碼 | 列出 MCP 工具；找確認管道 | 工具仍是六個唯讀工具（`test_mcp.py` tc024 不改動、全綠）；確認管道仍然只有 `TERMINAL`；沒有新增任何可代替終端機按 y 的東西（TC-D05 至 TC-D07 已驗被拒） | 自動：`test_mcp.py` tc024；`test_pat.py` |
| TC-F08 | 不在範圍：不改 TC-010、tc024、TC-061、`LAUNCH_ALLOW`、hooks、憲法、`.github/` | 不在範圍 | 對 `v3` 的 diff | 驗收審查者列出被改動的檔案 | 沒有任何檔案在 `hooks/`、`.github/`、`.specify/memory/constitution.md` 之下；`LAUNCH_ALLOW` 沒變；沒有改 `spec.md`／`test-case*.md` | 手動：驗收審查者讀 `git diff v3...HEAD --stat` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-G01 | 原則 2：只有一條排工作的路，且不另存 run 狀態 | 功能 | 實作完成 | 執行 `tests/no_second_run_state_test.sh` | 全綠；`LAUNCH_ALLOW` 沒變；`caller` 只被「記錄」，沒有新增任何排工作或存 run 狀態的路徑 | 自動：`tests/no_second_run_state_test.sh` |
| TC-G02 | 安全網：送出命令要完整顯示並等明確確認 | 功能 | 實作完成 | 執行 `test_launch_platform.py`（TC-010、TC-061）與 `test_launch_cli.py` | 全綠且未被改動；TC-D05 至 TC-D07 證明帶了身分也不能繞過確認 | 自動：`platform/tests/test_launch_platform.py` |
| TC-G03 | 安全網：憑證不進 git、不被印出、只放在部署自己的設定區 | 功能 | 實作完成 | 執行 `tests/credentials_stay_in_settings_test.sh`；掃所有被追蹤檔案找 `abf_pat_` 後面接 20 個以上字元的字面值 | 腳本全綠；沒有任何被追蹤檔案含 PAT 形狀的字面值（測試的 PAT 都在執行時才造）；沒有腳本印出權杖變數 | 自動：`tests/credentials_stay_in_settings_test.sh`；`test_pat.py` |
| TC-G04 | 計畫 Constitution Check：「Loosens nothing; adds one refusal」 | 功能 | 對 `v3` 與本分支各跑一次相同的閘門測試 | 驗收審查者在兩個分支跑 `test_mcp.py` tc024、`test_launch_platform.py`、`test_receiver.py`、`test_station_envs.py`、`test_secrets.py`，並用同一組「`v3` 會拒絕」的請求（無權杖打接收端、未知權杖打 agent 入口、非 TERMINAL 的 `confirmed_by`）各打一次 | `v3` 拒絕的，本分支全部仍然拒絕；唯一新增的拒絕是 `mcp --http` 沒帶有效 PAT；沒有任何 `v3` 拒絕的請求在本分支被放行 | 手動：驗收審查者在兩個分支跑並比較 |
