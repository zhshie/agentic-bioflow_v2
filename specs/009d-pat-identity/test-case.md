# 測試案例：009d 個人存取權杖（PAT）與使用者身分，`mcp --http` 必須帶權杖

**規格**：無 `spec.md`（依維護者指示，一律以 `specs/009d-pat-identity/plan.md` 為準；plan 的「給維護者」三句是他看得懂的承諾）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、有人想繞過時，系統怎麼反應（拒絕、停下）。
- **不在範圍**：計畫「Not in this PR」明講這次不做的事；測試確認它真的沒做。

維護者的話（plan「給維護者」，逐字）：

1. 「這一步讓平台認得『誰在呼叫』：先建立使用者（姓名、實驗室），再替他發個人存取權杖（PAT）；權杖只在終端機建立與撤銷，只顯示一次。」
2. 「你用起來的差別：`mcp --http` 現在必須帶 `Authorization: Bearer <PAT>`，否則 401；stdio（本機）不變、不用權杖。」
3. 「送出與取消仍然只能在終端機按 y；身分只是被記錄下來，不是新的確認方式。角色（010）、OAuth、公開網址都不在這一步。」

名詞：**PAT**＝個人存取權杖，一串像密碼的字，帶著它才能連 MCP；**使用者**＝平台記得的一個人（姓名＋實驗室）；**tokens.db**＝只存權杖「雜湊」（單向轉換後的指紋，看不出原字串）的檔案，`rebuild`（重建索引）不會動它；**401**＝網路回應「你沒出示有效身分」；**caller**＝這次呼叫是誰（空的＝本機終端機或 stdio，本來就不需驗證）；**TERMINAL**＝只代表「人在終端機按了 y」的專用記號；**AST 掃描**＝用程式讀原始碼結構（不是只搜字）來檢查誰引用了誰；**canary 掃描**＝把一個測試時才產生的假權杖，找遍資料庫檔，確認原字串沒有出現。

「前後一樣」的基準＝計畫起點 `v3`（009b 合併後）。所有權杖在測試裡於執行時產生，不寫死在檔案裡。

## User Story 1 — 在終端機建立使用者與發權杖，只顯示一次（優先度 P1）

維護者原話：「先建立使用者（姓名、實驗室），再替他發個人存取權杖（PAT）；權杖只在終端機建立與撤銷，只顯示一次。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-P01 | 給維護者 第 1 句「先建立使用者（姓名、實驗室）」；Design 1、3 | 功能 | 全新的 tokens.db（還沒有任何使用者） | 執行 `abf-platform user add alice --lab genomics` | 結束碼 0；tokens.db 的 `users` 表有且只有一列，姓名 `alice`、實驗室 `genomics`、`created_at` 有值、`disabled_at` 為空 | 自動：`platform/tests/test_pat.py`（經 CLI） |
| TC-P02 | Design 1（`name UNIQUE`） | 例外 | 已有使用者 `alice` | 再執行一次 `abf-platform user add alice --lab other` | 平台中仍然只有一位名為 `alice` 的使用者（不會出現兩個同名使用者）；不丟出未處理的錯誤堆疊 | 自動：`test_pat.py` |
| TC-P03 | 給維護者 第 1 句「再替他發個人存取權杖」「只顯示一次」；Design 1、3 | 功能 | 已有使用者 `alice` | 執行 `abf-platform pat new --user alice` | 結束碼 0；標準輸出出現一行與 `token new` 同樣口吻的說明（含 `shown once and cannot be shown again; only its hash is kept`），接著一行權杖，權杖以 `abf_pat_` 開頭，其後是 `secrets.token_urlsafe(32)` 長度的隨機字串 | 自動：`test_pat.py` |
| TC-P04 | Design 3（`pat new --label`） | 功能 | 已有使用者 `alice` | 執行 `pat new --user alice --label laptop`，再執行 `pat list` | `pat list` 的那一列顯示標籤 `laptop` | 自動：`test_pat.py` |
| TC-P05 | Design 3（`pat list`） | 功能 | `alice` 有兩把 PAT，其中一把已撤銷 | 執行 `abf-platform pat list` | 每把一列，顯示：編號、使用者、標籤、建立時間、是否已撤銷；輸出裡沒有任何雜湊值、沒有任何權杖原字串 | 自動：`test_pat.py` |
| TC-P06 | 給維護者 第 1 句「權杖只在終端機……撤銷」；Design 3 | 功能 | `alice` 有一把可用的 PAT（編號 N） | 執行 `abf-platform pat revoke N` | 結束碼 0；`pat list` 該列標示已撤銷；之後用該 PAT 連 `mcp --http` 得到 401（見 TC-P16） | 自動：`test_pat.py` |
| TC-P07 | 給維護者 第 1 句「只顯示一次」；Design 3「nothing else prints or logs it」 | 例外 | 在測試中記下 `pat new` 產生的 PAT 原字串 | 依序收集 `user add`、`pat list`、`pat revoke`、錯誤情況（例如拿不存在的編號去 revoke）、以及 `mcp --http` 伺服器的標準輸出／錯誤輸出與記錄檔 | 這些輸出裡都找不到該 PAT 原字串；原字串只出現在 `pat new` 的標準輸出 | 自動：`test_pat.py` |
| TC-P08 | Design 1（只存雜湊）；Pinned guard tc040 | 功能 | 測試執行時產生一把 PAT | 對 tokens.db 與 index.db 做 canary 掃描（整檔位元組搜尋原字串），並查 `tokens` 表 | 兩個檔案裡都找不到原字串；tokens 表有一列，其 `token_hash` 等於該 PAT 的 sha256 | 自動：`test_pat.py`（沿用 `test_secrets.py` tc040 的做法） |
| TC-P09 | Design 3「No MCP tool, no web route, no action for these」；Not in this PR「no PAT or user tool in MCP」 | 不在範圍 | 伺服器建好 | 列出 MCP 工具；列出 `abf_platform.actions` 的公開函式 | 工具仍然正好是 `get_compute_env`、`get_run`、`list_agents`、`list_compute_envs`、`list_runs`、`list_site_files` 六個；工具名與動作層函式名裡都沒有與 user／pat／token 管理有關的 | 自動：`test_pat.py` ＋既有 `test_mcp.py::test_tc024_exactly_six_read_only_tools` |
| TC-P10 | Design 3（no web route） | 不在範圍 | 起 MCP HTTP 伺服器、收單與代理端點應用程式 | 列出各應用程式註冊的路由 | 沒有任何路由可以建立／列出／撤銷使用者或 PAT；用有效 PAT 呼叫猜測的管理路徑（如 `/users`、`/pat`）得到 404 或 401，不是 200，也不改變資料 | 自動：`test_pat.py` |
| TC-P11 | Design 3（`pat revoke <id>` 以編號） | 功能 | `alice` 先後發了兩把 PAT，A 與 B，兩者值不同 | 撤銷 A | A 得到 401；B 仍可連線得到 200 | 自動：`test_pat.py` |

## User Story 2 — `mcp --http` 必須帶權杖，stdio 不變（優先度 P1）

維護者原話：「`mcp --http` 現在必須帶 `Authorization: Bearer <PAT>`，否則 401；stdio（本機）不變、不用權杖。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-P12 | 給維護者 第 2 句「否則 401」；Design 4 | 例外 | 有使用者與有效 PAT，`mcp --http` 在本機埠啟動 | 不帶 `Authorization` 標頭，對 `/mcp` 發出請求 | 回應 401，且有標頭 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-P13 | Design 4（wrong scheme） | 例外 | 同上 | 帶 `Authorization: Basic <任意>`，以及 `Authorization: Token <有效 PAT 的值>` | 兩者都是 401 並有 `WWW-Authenticate: Bearer`（用對的權杖但方案錯也不放行） | 自動：`test_pat.py` |
| TC-P14 | Design 4（malformed） | 例外 | 同上 | 帶 `Authorization: Bearer`（沒有值）、`Bearer !!! ???`、一長串亂碼 | 都是 401 並有 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-P15 | Design 4（unknown） | 例外 | 同上 | 帶一把格式看起來對（`abf_pat_` 開頭、長度相同）但從未發出過的權杖 | 401 並有 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-P16 | Design 2（revoked token = None）；TC-P06 | 例外 | 一把 PAT 已用 `pat revoke` 撤銷 | 用它連 `/mcp` | 401 並有 `WWW-Authenticate: Bearer`；撤銷後不需重啟伺服器即生效 | 自動：`test_pat.py` |
| TC-P17 | Design 2（disabled user = None） | 例外 | `alice` 有有效 PAT；測試直接把 tokens.db 中 `alice` 的 `disabled_at` 設成現在時間（plan 沒有停用指令，故由測試設定） | 用該 PAT 連 `/mcp` | 401 並有 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-P18 | Design 4「body never echoes the token」 | 例外 | 同上；用一把有獨特字串的假權杖 | 帶該假權杖連 `/mcp`，檢視 401 的回應本文與所有回應標頭 | 本文與標頭裡都找不到那把權杖字串 | 自動：`test_pat.py` |
| TC-P19 | 給維護者 第 2 句；Design 4；Pinned guard tc025（輸入改為帶 PAT） | 功能 | 有使用者 `alice` 與有效 PAT；資料庫裡有三個 run | 帶 `Authorization: Bearer <PAT>` 連 `/mcp`，列出工具，呼叫 `list_runs`、`get_run`（真實 id）、`get_run("deadbeefdeadbeef")`；同樣呼叫再用 stdio 跑一次 | 工具正好六個（`get_compute_env`、`get_run`、`list_agents`、`list_compute_envs`、`list_runs`、`list_site_files`）；三個呼叫的回答與 stdio 逐欄相同；`get_run` 回的 `id` 是該真實 id | 自動：`platform/tests/test_mcp.py::test_tc025_…`（只改輸入：建使用者、發 PAT、送標頭）＋`test_pat.py` |
| TC-P20 | Pinned guard tc025（`assert_loopback_only`） | 功能 | 同 TC-P19，用預設主機啟動 `mcp --http` | 檢查監聽位址 | 仍然只監聽 loopback（本機），沒有因為加了驗證而改變監聽範圍 | 自動：`test_mcp.py::test_tc025_…`（斷言不變） |
| TC-P21 | 給維護者 第 2 句「stdio（本機）不變、不用權杖」；Design 5、Facts | 功能 | 資料庫裡有 run；tokens.db 裡沒有任何使用者或 PAT | 以 stdio 起 `abf-platform mcp`（不帶任何權杖或標頭），列出工具並呼叫 `list_runs` | 六個工具都可用，回答與改動前相同；沒有要求權杖 | 自動：`test_pat.py` ＋既有 `test_mcp.py` stdio 相關測試 |
| TC-P22 | Design 7（沒有使用者時） | 例外 | tokens.db 沒有任何使用者 | 起 `abf-platform mcp --http`，再對 `/mcp` 發請求（有帶隨意的 Bearer 與不帶各一次） | 伺服器照常啟動（不因沒使用者而退出）；每個請求都是 401；啟動時輸出一行說明「還沒有使用者／所有請求都會被拒絕」之類的提示（只一行） | 自動：`test_pat.py` |
| TC-P23 | Design 6 | 功能 | 起 `mcp --http --host <非 loopback 位址>`（測試可用替身避免真的對外監聽） | 看 `cmd_mcp` 的輸出 | 原有的風險提示（`_risk_line`）仍在，並多一句說明需要權杖（含 `a token is required`） | 自動：`test_pat.py`（與 `test_cli.py` 風險提示測試並存） |
| TC-P24 | Design 6「no flag or env var turns auth off」 | 例外 | 沒有使用者；`mcp --http` 的選項說明 | 嘗試 `mcp --http --no-auth`、`--insecure`、`--disable-auth`；再於環境變數裡設常見的關閉名稱（如 `ABF_NO_AUTH=1`、`ABF_AUTH=off`）啟動 | 這些旗標被命令列解析拒絕（非 0 結束碼，不啟動）；環境變數不影響結果，不帶權杖仍是 401；`--help` 裡沒有關閉驗證的選項 | 自動：`test_pat.py` |
| TC-P25 | Design 4「contextvars caller for the request」 | 功能 | `alice` 與 `bob` 各有一把有效 PAT | 先用 alice 的 PAT 呼叫，緊接著用 bob 的 PAT 呼叫，再不帶標頭呼叫 | 兩次有效呼叫各自看到自己的 caller（見 TC-P32）；第三次是 401，不會沿用前一次的身分 | 自動：`test_pat.py` |

## User Story 3 — 權杖不開別的門，別種權杖也不開 MCP（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-P26 | Design 2「A PAT never opens another door」 | 例外 | 一把有效 PAT；收單（receiver）應用程式 | 用該 PAT 當 Bearer 對收單端點（建立 run 等）發請求 | 401，不寫入任何 run 或事件 | 自動：`test_pat.py` |
| TC-P27 | Design 2 | 例外 | 同上；代理（agent）端點應用程式 | 用該 PAT 對代理端點（輪詢工作、回報等）發請求 | 401，不領走任何工作、不寫入任何狀態 | 自動：`test_pat.py` |
| TC-P28 | Design 2「a run/agent token is refused on MCP」 | 例外 | 一把 run 權杖（`token new`）；`mcp --http` 啟動 | 用 run 權杖當 Bearer 連 `/mcp` | 401 並有 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-P29 | Design 2 | 例外 | 一把 agent 權杖（`agent-token new`） | 用 agent 權杖當 Bearer 連 `/mcp` | 401 並有 `WWW-Authenticate: Bearer` | 自動：`test_pat.py` |
| TC-P30 | Design 2（`lookup_pat` 回傳形狀） | 功能 | 有效 PAT、已撤銷 PAT、被停用使用者的 PAT、一把 run 權杖、一把 agent 權杖、一把從未發出的字串 | 對每一把呼叫 `store.lookup_pat(tokens_path, 值)` | 有效 PAT 回傳含 `user_id`、`name`、`lab`、`token_id` 四個鍵的字典且內容正確；其餘五種都回 `None` | 自動：`test_pat.py` |
| TC-P31 | Design 1（`create_token` 的種類） | 功能 | tokens.db | 呼叫 `create_token(kind="pat", user_id=…)`；再呼叫 `create_token(kind="admin")` 之類未知種類 | `pat` 種類成功並回傳 `abf_pat_` 開頭的值；未知種類丟 `ValueError`；`run`、`agent` 原有行為不變（run 權杖仍可自 `token new` 取得並用於收單） | 自動：`test_pat.py` ＋既有 `test_cli.py` |

## User Story 4 — 身分只被記錄，不是新的確認方式（優先度 P1）

維護者原話：「送出與取消仍然只能在終端機按 y；身分只是被記錄下來，不是新的確認方式。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-P32 | Design 5（read actions gain `caller`）；測試計畫「a spy on a read action sees the user」 | 功能 | `alice`（實驗室 `genomics`）有有效 PAT；以替身（spy）包住一個讀取動作 | 用 alice 的 PAT 經 HTTP 呼叫該讀取工具 | 替身收到的 `caller` 是 `Caller(user_id, name="alice", lab="genomics")`（凍結的資料物件）；工具回答與不帶 caller 時相同（讀取動作忽略 caller） | 自動：`test_pat.py` |
| TC-P33 | Design 5「`None` means local stdio/terminal」 | 功能 | 以 stdio 起伺服器；以替身包住讀取動作 | 經 stdio 呼叫該工具 | 替身收到的 `caller` 是 `None` | 自動：`test_pat.py` |
| TC-P34 | 給維護者 第 3 句「不是新的確認方式」；測試計畫「`launch(..., confirmed_by="yes", caller=u)` still refused」 | 例外 | 一位有效使用者的 `Caller`；一個可排工作的平台狀態與環境 | 呼叫 `actions.launch(state, env, bundle, confirmed_by="yes", caller=u)` | 丟出 `JobRefused`（訊息 `no human confirmation channel`）；確認紀錄表與工作表沒有新增任何一列 | 自動：`test_pat.py` ＋既有 `test_actions_layer.py` 規則 |
| TC-P35 | 給維護者 第 3 句 | 例外 | 同上 | 呼叫 `actions.launch(state, env, bundle, confirmed_by=u, caller=u)`（把 Caller 本身當成確認者） | 同樣被拒、什麼都沒寫入 | 自動：`test_pat.py` |
| TC-P36 | 給維護者 第 3 句「送出與取消」；Design 5（cancel） | 例外 | 同上 | 呼叫 `actions.cancel(state, env, bundle, confirmed_by="yes", caller=u)` 與 `confirmed_by=u` | 兩者都丟 `JobRefused`，確認表與工作表沒有新增任何一列 | 自動：`test_pat.py` |
| TC-P37 | Design 5「the `confirmed_by` check stays first (order unchanged)」 | 例外 | 同上 | 呼叫 `launch(..., confirmed_by="yes", caller=<形狀不對的任意物件>)` | 仍是 `no human confirmation channel` 的 `JobRefused`，而不是因 caller 不合法而丟別種錯誤（確認者檢查在最前面） | 自動：`test_pat.py` |
| TC-P38 | Design 5；測試計畫「`launch(TERMINAL, caller=u)` queues one job and the confirmation row names the user」 | 功能 | 同上 | 呼叫 `actions.launch(state, env, bundle, confirmed_by=TERMINAL, caller=u)` | 回傳（確認編號, 工作編號）；工作表恰多一列 launch 工作；確認紀錄恰多一列，且這一列能辨認出是這位使用者（姓名或 id，兩者其一） | 自動：`test_pat.py` |
| TC-P39 | Design 5（cancel 也記錄） | 功能 | 同上，有一個可取消的 run | 呼叫 `actions.cancel(state, env, bundle, confirmed_by=TERMINAL, caller=u)` | 工作表恰多一列 cancel 工作；確認紀錄恰多一列，能辨認出是這位使用者 | 自動：`test_pat.py` |
| TC-P40 | Design 5「`abf_launch/cli.py` passes `caller=None`」 | 功能 | 終端機送出流程（`abf-launch` 在測試中以回答 y 的替身完成） | 走一次完整的送出 | 工作照常排入；確認紀錄的使用者欄位為空（NULL）；行為與改動前相同 | 自動：既有 `test_launch_cli.py`／`test_launch_platform.py` 不改動全綠＋`test_pat.py` 查該欄位 |
| TC-P41 | Design 5「nullable column, migrated in place」 | 功能 | 一份改動前版本建立、沒有該欄的 platform.db，內有舊的確認紀錄與工作 | 開啟並執行 `launch(TERMINAL)` | 檔案原地升級（舊列保留且該欄為空）；新送出可正常運作；不需要手動搬資料 | 自動：`test_pat.py` |
| TC-P42 | Design 4「import rule extended by exactly one allowed name」；Design 5 | 功能 | 讀 `mcp_server.py` 與 `http_auth.py` 的原始碼（AST） | 檢查兩者從 `abf_platform` 匯入了什麼，以及 `mcp_server.py` 是否提到 launch、cancel、TERMINAL、confirm | `mcp_server.py` 匯入的平台子模組正好是 `{actions, http_auth}`；`http_auth.py` 只匯入 `store` 與 `actions`（且從 `actions` 只取 `Caller`）；`mcp_server.py` 完全不提 `launch`、`cancel`、`TERMINAL`、`confirm\b`；六個工具本體仍是各一個陳述式、呼叫同名 `actions` 函式；工具輸入欄位裡沒有 `caller` | 自動：`test_actions_layer.py`（只加一個允許名稱 `http_auth`）＋`test_pat.py` |
| TC-P43 | Pinned guard 009b；Design 5 | 功能 | 掃描整個 `abf_platform/` | AST 掃描誰引用 `actions.launch`、`actions.cancel`、`TERMINAL` | 只有 `abf_launch/cli.py` 引用；`http_auth.py`、`cli.py`（platform 的 CLI）、`mcp_server.py` 都不引用 | 自動：`test_actions_layer.py` 不改動斷言 |

## User Story 5 — 舊檔相容、既有測試不變、文件（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-P44 | Design 1（`_migrate_tokens` 原地升級，old files keep working） | 功能 | 一份只有 008 欄位（或更舊、無 `kind`）的 tokens.db，內有一把 run 權杖、一把 agent 權杖 | 用新版開啟並執行 `user add`、`pat new`、經收單與代理端點使用舊權杖 | 檔案原地升級、新增 `users` 表與 `user_id` 欄；舊的 run／agent 權杖仍然有效且種類不變；新建的 PAT 可用 | 自動：`test_pat.py` ＋既有 `test_cli.py`、`test_station_envs.py` 的 tokens.db 檢查 |
| TC-P45 | Design 1「`rebuild` never opens it」 | 功能 | 已有使用者與一把 PAT；index.db 有資料 | 執行 `abf-platform rebuild`（重建索引） | 使用者與 PAT 都還在，PAT 仍可連 `/mcp`；tokens.db 內容不變 | 自動：`test_pat.py` |
| TC-P46 | Changes 5「Edit `test_mcp.py` tc025 only to create a user, issue a PAT and send the header (assertions unchanged)」 | 功能 | 取 `git diff v3...HEAD -- platform/tests/test_mcp.py` | 逐行檢查 | tc025 只差在建立使用者、發 PAT、送標頭；所有斷言（六個工具名、`assert_loopback_only`、stdio 與 HTTP 回答相同、`id` 等於真實 id）與 `v3` 逐字相同；`test_mcp.py` 其他測試沒有被改動 | 手動：驗收者以 `git diff v3...HEAD` 比對 |
| TC-P47 | Pinned guards；Changes 5（009b import-rule 只加一個名稱） | 功能 | 實作完成 | 跑 `test_mcp.py::test_tc024…`、`test_launch_platform.py` 的 TC-010 與 TC-061、`test_actions_layer.py`、`test_scope.py` tc070、`test_secrets.py` tc040 | 全綠；這些測試檔相對 `v3` 只有 plan 點名的改動（`test_actions_layer.py` 的 tcc01 允許集合由 `{actions}` 變成 `{actions, http_auth}`，其餘斷言逐字不變） | 自動：既有測試不改動（各檔） |
| TC-P48 | Pinned guards（test_cli／test_station_envs） | 功能 | 實作完成 | 跑 `test_cli.py`、`test_station_envs.py` | 全綠；tokens.db 相關檢查沒有被放寬 | 自動：既有測試 |
| TC-P49 | Changes 6（`docs/PLATFORM.md`） | 功能 | 實作完成 | 讀 `docs/PLATFORM.md` | 有說明：身分（使用者＝姓名＋實驗室）、PAT 是什麼、怎麼用 `user add`／`pat new`／`pat list`／`pat revoke` 建立與撤銷、怎麼在 MCP 客戶端設定 `Authorization: Bearer <PAT>`、stdio 不用權杖；說明 PAT 只顯示一次 | 自動：`test_pat.py`（讀文件，查上述字詞皆在）＋人看一遍（見總覽「需要人看」） |
| TC-P50 | Changes 6（`CHANGELOG.md`） | 功能 | 實作完成 | 讀 `CHANGELOG.md` 的 3.0.0-dev 段落 | 有一行標示破壞性變更：`mcp --http` 需要 PAT（含 `breaking` 與 `mcp --http`、`PAT`） | 自動：`test_pat.py`（或文件測試） |

## User Story 6 — 這一步不做的事（優先度 P1，確認沒偷做）

維護者原話：「角色（010）、OAuth、公開網址都不在這一步。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-P51 | Not in this PR「No OAuth 2.1, no discovery metadata」；Design 4 | 不在範圍 | `mcp --http` 已啟動；有效 PAT | 對 `/.well-known/oauth-authorization-server` 與 `/.well-known/oauth-protected-resource` 發請求（帶 PAT）；掃描原始碼 | 不是 200 的探索文件（404 或同等）；原始碼沒有使用 SDK 的 `AuthSettings`／OAuth 提供者；也沒有 `/authorize`、`/token` 之類 OAuth 端點 | 自動：`test_pat.py` |
| TC-P52 | Not in this PR「no public URL or TLS」 | 不在範圍 | `mcp --http` 的選項說明與原始碼 | 查看選項；以預設設定啟動 | 沒有 `--ssl`、`--cert`、`--key`、`--public-url` 之類選項；預設仍是純 HTTP、只監聽 loopback | 自動：`test_pat.py` |
| TC-P53 | Not in this PR「no roles/PI/lab permissions (010)」；給維護者 第 3 句 | 不在範圍 | 兩位不同實驗室的使用者 `alice`（genomics）、`bob`（proteomics），各有 PAT | 檢查 `users` 表欄位；兩人各自呼叫六個工具 | `users` 表欄位正好是 `id, name, lab, created_at, disabled_at`，沒有角色欄；tokens 表沒有角色欄；兩人的所有讀取回答相同，不因實驗室而不同 | 自動：`test_pat.py` |
| TC-P54 | Not in this PR「no per-user compute-environment limits」 | 不在範圍 | 資料庫有兩個算力環境；`alice`、`bob` 各有 PAT | 兩人各自呼叫 `list_compute_envs` 與 `get_compute_env` | 兩人看到完全相同的環境清單與內容，沒有依使用者過濾 | 自動：`test_pat.py` |
| TC-P55 | Not in this PR「no token expiry or rotation」 | 不在範圍 | 一把新發的 PAT | 查 tokens 表該列的 `expires_at`；把時鐘用 `ABF_PLATFORM_CLOCK_OFFSET` 往前撥很多年；嘗試 `pat rotate`／`pat renew` | `expires_at` 為空；時鐘撥前後 PAT 仍有效（200）；`pat` 底下沒有 rotate／renew／expire 指令，被命令列解析拒絕 | 自動：`test_pat.py` |
| TC-P56 | Not in this PR「no web login (011+)」 | 不在範圍 | MCP HTTP 應用程式與其他應用程式 | 對 `/login`、`/signin`、`/session` 等路徑發請求（帶／不帶 PAT） | 沒有登入頁或登入端點：回 404（或在無權杖時統一 401），不是 200；不設任何 session cookie | 自動：`test_pat.py` |
| TC-P57 | Not in this PR「No new way to confirm (still TERMINAL)」；給維護者 第 3 句 | 不在範圍 | 有效 PAT；記下工作表與確認表的列數 | 用該 PAT 經 HTTP 依序呼叫六個工具各一次（含嘗試用一個不存在的 `launch`／`cancel` 工具名） | 列數前後相同，沒有任何寫入；呼叫不存在的工具得到「找不到工具」類錯誤，不會排入任何工作 | 自動：`test_pat.py` |
| TC-P58 | Not in this PR「No edit to TC-010, tc024, TC-061, `LAUNCH_ALLOW`, hooks, constitution, `.github/`」 | 不在範圍 | 實作完成 | `git diff v3...HEAD --name-only` 並檢視相關檔案內容 | 沒有檔案屬於 `hooks/`、`.specify/memory/constitution.md`、`.github/`；TC-010、tc024、TC-061 的測試本體與 `LAUNCH_ALLOW` 相對 `v3` 無差異 | 手動：驗收者以 `git diff v3...HEAD` 比對 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | 原則 I.2：唯一的送出路徑；不得有第二份 run 狀態 | 功能 | 實作完成 | 跑 `tests/no_second_run_state_test.sh`（在 WSL）；檢查 `LAUNCH_ALLOW` | 全綠；`LAUNCH_ALLOW` 與 `v3` 相同（仍然至多一項）；新增的 `users` 表與 `caller` 欄不是 run 狀態，沒有被該檢查判為第二份真相；沒有新增任何送出工作的程式 | 自動：`tests/no_second_run_state_test.sh` |
| TC-C02 | 安全網「憑證」：不印、不進 git | 功能 | 實作完成 | 跑 `tests/credentials_stay_in_settings_test.sh`；canary 掃描（TC-P08） | 全綠；沒有任何腳本印出權杖變數；沒有任何被追蹤的檔案含像權杖的值（測試夾具於執行時才產生 PAT） | 自動：`tests/credentials_stay_in_settings_test.sh` ＋`test_pat.py`、`test_secrets.py` tc040 |
| TC-C03 | 安全網「憑證」：never printed／never logged | 例外 | `mcp --http` 以記錄檔收集輸出 | 送出數個請求：有效 PAT、無效 PAT、帶獨特字串的假權杖；結束後讀記錄檔與伺服器輸出 | 記錄檔與輸出裡找不到任何一把被送出的權杖字串（有效或無效），也沒有它的雜湊 | 自動：`test_pat.py` |
| TC-C04 | 安全網「送出前完整顯示並等待明確確認」；原則 I.2「使用者看過並確認」 | 功能 | 實作完成 | 跑 `test_launch_platform.py` TC-010／TC-061、`test_actions_layer.py`、以及 `hooks/confirm_launch.sh` 的 `tests/confirm_launch_test.sh` | 全綠且未被改動；沒有讓 PAT 或使用者身分成為確認的替代（見 TC-P34 到 P37） | 自動：上述測試檔 |
| TC-C05 | 原則 I.1：每個新檔要自述為何不用現成方案；`test_scope.py` tc070 | 功能 | 新增 `platform/abf_platform/http_auth.py` 與 `platform/tests/test_pat.py` | 跑 `test_scope.py` tc070；讀兩個新檔的最前幾行 | 兩個檔案開頭都有 `# Not <工具>: <原因>` 或 `# Nothing existing: <原因>`；`http_auth.py` 的說明有講明為何不用 SDK 的 OAuth（OAuth 是之後的切片）；`pyproject.toml` 的 packages 列表若有新套件則已列入 | 自動：`platform/tests/test_scope.py` |
| TC-C06 | Development Workflow：每個階段全綠 | 功能 | 實作完成 | `cd platform && python -m pytest -q`；WSL 內 `bash tests/run_all.sh`（或 CI 結果） | 兩者全綠，沒有跳過的案例、沒有被放寬的斷言 | 自動：CI／`tests/run_all.sh` |

<!--
IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
