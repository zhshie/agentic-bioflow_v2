# 測試案例：用 id 撤銷「一把」代理 token（`agent-token revoke --id N`）並能列出 token id（`agent-token list`）

**規格**：`specs/agent-token-revoke-by-id/plan.md`（這個任務沒有獨立的 spec.md，計畫即規格；對應欄位引用計畫的段落名或維護者原話編號）　**總覽**：`test-case-overview.md`

名詞（一句話解釋）：「代理 token」＝發給實驗室代理程式（station agent）的通行憑證，平台只存它的雜湊（hash，不可還原的指紋），憑證本身只在發出時顯示一次。「接收端」＝平台上收代理程式請求的那一側；憑證被撤銷後它回 401（未授權）。「run token」＝跑某次分析專用的憑證；「PAT」＝個人存取憑證（personal access token）。這兩種都不是代理 token，`--id` 不可以誤撤它們。「回傳碼」＝指令結束時的數字，0 代表成功，1 代表被拒絕，2 代表指令格式本身錯誤。

維護者原話（唯一來源，2026-10-29）：「revoke one agent token by id instead of every token of a name; from 2026-10-29: an old desktop token (id 1) was left live because revoking by name would also kill the new token.」其導出的四件事：①可以只撤一把（用 id）②同名的另一把照常能用 ③撤掉的那把之後被拒 ④舊的按名字撤銷不變。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

共同的測試布置（下列各案例沿用）：所有測試都用暫存資料夾裡的 `ABF_PLATFORM_DB`，不碰真實部署。「`ag` 兩把」＝同名代理 `ag` 發了兩把 token：id 1 是舊的（沒有綁使用者，模擬維護者遇到的舊桌機 token），id 2 是新的。

## User Story 1 — 用 id 只撤掉其中一把，同名的另一把照常能用（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話①；計畫「決定（介面）」revoke --id | 功能 | `ag` 兩把（id 1 舊、id 2 新），都有效 | 執行 `agent-token revoke --id 1` | 指令回傳碼 0 | 自動：`platform/tests/test_agent_token_revoke_id.py` |
| TC-002 | 原話①③ | 功能 | 同 TC-001，撤銷後查資料庫 `tokens.db` | 讀 id 1 那一列的 `revoked_at`（撤銷時間欄） | id 1 的 `revoked_at` 有值 | 自動 |
| TC-003 | 原話② | 功能 | 同 TC-001，撤銷後 | 讀 id 2 那一列；用新 token 的值呼叫 `store.lookup_token` | id 2 的 `revoked_at` 仍為空；`lookup_token` 對新值仍回傳 `agent_name` 為 `ag` 的紀錄 | 自動 |
| TC-004 | 原話③ | 功能 | 同 TC-001，撤銷後 | 用舊 token 的值呼叫 `store.lookup_token` | 回傳 `None`（查無有效 token） | 自動 |
| TC-005 | 原話③；計畫「拒絕舊 token 的現成機制」 | 功能 | 同 TC-001，撤銷後；用 `receiver.create_app(index, tokens)` 的測試客戶端 | 用舊 token 對接收端送 `POST /agent/hello` | 回 401 | 自動 |
| TC-006 | 原話② | 功能 | 同 TC-005 | 用新 token 對接收端送 `POST /agent/hello` | 回 200（照常能用） | 自動 |
| TC-007 | 計畫「完成標準」：只撤那一把 | 功能 | `ag` 三把（id 1、2、3）都有效 | 執行 `agent-token revoke --id 2` | 只有 id 2 被撤；id 1、id 3 的 `revoked_at` 仍為空，`lookup_token` 對它們的值仍有效 | 自動 |
| TC-008 | 計畫「決定（介面）」成功訊息 | 功能 | 同 TC-001 | 執行 `agent-token revoke --id 1`，看標準輸出 | 輸出含 `revoked agent token 1`、`agent ag`、`other tokens of this agent are untouched` | 自動 |
| TC-009 | 維護者原話情境：先找 id 再撤舊桌機 token | 功能 | `ag` 兩把：id 1 舊（沒有 user）、id 2 新（user alice）；維護者事先不知道哪個 id 是舊的 | 先執行 `agent-token list`，從清單找到 `user -` 的那一行與它的 id，再用該 id 執行 `agent-token revoke --id <那個 id>` | 清單上那一行的 id 是 1；撤銷後舊桌機 token 被拒（`lookup_token` 回 `None`），新 token 仍有效 | 自動 |
| TC-010 | 計畫「決定（store）」 | 功能 | `ag` 兩把，都有效 | 直接呼叫 `store.revoke_agent_token(tokens_path, 1)` | 回傳 `{"agent_name": "ag"}`，且 id 1 已被撤 | 自動 |

## User Story 2 — 用 `agent-token list` 看到每把 token 的 id（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 計畫「決定（介面）」list | 功能 | `ag` 兩把（id 1 無 user、id 2 user alice） | 執行 `agent-token list` | 每把 token 恰好一行；兩行分別含 `id 1`、`id 2`，且都含 `agent ag` | 自動 |
| TC-012 | 計畫「list」user 欄；裁決 8 | 功能 | 同 TC-011 | 執行 `agent-token list` | id 2 那行含 `user alice`；沒有 user 的舊 id 1 那行含 `user -` | 自動 |
| TC-013 | 計畫「list」撤銷狀態 | 功能 | 同 TC-011，先撤 id 1 | 執行 `agent-token list` | id 1 那行結尾是 `revoked`；id 2 那行結尾是 `not revoked`（注意 `not revoked` 也含 `revoked`，必須分得出來） | 自動 |
| TC-014 | 計畫「list」依 id 排序 | 功能 | 三把以上 agent token，建立順序與 id 順序一致 | 執行 `agent-token list` | 各行依 id 由小到大排列 | 自動 |
| TC-015 | 計畫「list」格式 `created YYYY-MM-DD HH:MM` | 功能 | 同 TC-011 | 執行 `agent-token list` | 每行含 `created ` 後接 `年-月-日 時:分` 格式的時間 | 自動 |
| TC-016 | 計畫「list [NAME]」給名字只列該名字 | 功能 | `ag` 兩把，另有 `other` 一把 agent token | 執行 `agent-token list ag` | 只出現 `ag` 的行；不出現 `other` 的行 | 自動 |
| TC-017 | 計畫「list」不給名字列全部 | 功能 | 同 TC-016 | 執行 `agent-token list`（不給名字） | `ag` 的行與 `other` 的行都出現 | 自動 |
| TC-018 | 計畫「只列 kind = 'agent'」；裁決 6 | 功能 | 同 TC-016，另有一把 run token、一把 PAT（它們的 id 與上面各 agent token 不同） | 執行 `agent-token list` 與 `agent-token list ag` | 兩次輸出都不出現 run token 與 PAT 的 id（也就是清單裡不會把它們當代理 token 列出） | 自動 |
| TC-019 | 計畫「沒有任何一把時印 `no agent tokens`，回傳 0」 | 功能 | `tokens.db` 存在但是空的 | 執行 `agent-token list` | 印 `no agent tokens`，回傳碼 0 | 自動 |
| TC-020 | 同上，檔案不存在的情況 | 功能 | `tokens.db` 這個檔案根本不存在 | 執行 `agent-token list` | 印 `no agent tokens`，回傳碼 0，沒有錯誤訊息或堆疊 | 自動 |
| TC-021 | 計畫「有給 NAME 則 `no agent tokens for NAME`」 | 功能 | 有 `ag` 的 token，沒有 `nobody` 的 | 執行 `agent-token list nobody` | 印 `no agent tokens for nobody`，回傳碼 0 | 自動 |
| TC-022 | 計畫「不印 token 值、不印雜湊」 | 功能 | `ag` 兩把，已知兩把 token 的原值，並算出它們的 sha256 雜湊 | 執行 `agent-token list`，檢查標準輸出與標準錯誤 | 兩處都不含任何一把 token 的原值，也不含其 sha256 雜湊 | 自動 |
| TC-023 | 計畫「決定（store）」list_agent_tokens | 功能 | `ag` 兩把（一有 user、一無），另有 run token 與 PAT | 呼叫 `store.list_agent_tokens(tokens_path)`；再呼叫 `store.list_agent_tokens(不存在的路徑)` | 第一次回傳只含兩把 agent token 的清單，每筆只有 `id`、`agent_name`、`user`、`created_at`、`revoked_at` 這幾個欄位，沒有 token 值或雜湊，無 user 的那筆 `user` 為空；第二次回傳 `[]` | 自動 |

## User Story 3 — 按名字撤銷的舊用法完全不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 原話④；計畫「revoke NAME 完全不變」 | 功能 | `ag` 三把有效，`other` 一把有效 | 執行 `agent-token revoke ag` | 回傳碼 0；標準輸出恰為 `revoked 3 token(s) of agent ag; the agent is refused from its next request`（逐字） | 自動 |
| TC-031 | 原話④ | 功能 | 同 TC-030，撤銷後 | 用各 token 的值呼叫 `lookup_token` | `ag` 的三把都查無（`None`）；`other` 那把仍有效 | 自動 |
| TC-032 | 計畫「回傳碼不變」 | 例外 | 沒有名為 `nobody` 的代理 token | 執行 `agent-token revoke nobody` | 回傳碼 1；標準輸出為 `revoked 0 token(s) of agent nobody; the agent is refused from its next request` | 自動 |
| TC-033 | 計畫「兩分支比對」；現有測試依賴 | 功能 | 本分支的程式 | 執行既有的 `test_pat.py`、`test_onboarding_doc.py`、`test_station_e2e.py::test_tc006_a_revoked_token_stops_the_agent_with_the_reason` | 全部通過，且這些檔案的既有斷言沒有被改動或放寬 | 自動：既有測試 |

## User Story 4 — 打錯或不該撤的情況一律被拒、不改資料（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 計畫「找不到 → 回 1」 | 例外 | 沒有 id 為 999 的 token | 執行 `agent-token revoke --id 999` | 回傳碼 1；標準錯誤含 `rejected: no live agent token with id 999`、`沒有這個有效的代理 token`，以及下一步指引 `agent-token list` | 自動 |
| TC-041 | 計畫「不露堆疊、路徑、SQL」 | 例外 | 同 TC-040 | 同 TC-040，檢查標準輸出與標準錯誤 | 不含 `Traceback`、SQL 語句或檔案路徑 | 自動 |
| TC-042 | 計畫「不改任何資料」 | 例外 | 同 TC-040，先記下 `tokens.db` 整張表 | 執行 `agent-token revoke --id 999` 後再讀整張表 | 前後完全一致 | 自動 |
| TC-043 | 裁決 6：run token 的 id 被拒 | 例外 | 有一把 run token（取其 id） | 執行 `agent-token revoke --id <run token 的 id>` | 回傳碼 1；訊息與 TC-040 同一句（`no live agent token with id N`），不透露它其實是別種 token | 自動 |
| TC-044 | 裁決 6：不誤關進行中的 run | 例外 | 同 TC-043，之後 | 用 run token 的值呼叫 `lookup_token` | 仍有效（沒被撤） | 自動 |
| TC-045 | 裁決 6：PAT 的 id 被拒 | 例外 | 有一把 PAT（取其 id） | 執行 `agent-token revoke --id <PAT 的 id>` | 回傳碼 1；訊息同 TC-040 那句，不透露它是 PAT | 自動 |
| TC-046 | 裁決 6 | 例外 | 同 TC-045，之後 | 用 PAT 的值呼叫 `lookup_pat` | 仍有效（沒被撤） | 自動 |
| TC-047 | 裁決 7：已撤銷的再撤一次被拒 | 例外 | `ag` 的 id 1 已經撤銷 | 再執行 `agent-token revoke --id 1` | 回傳碼 1（不是「重複撤銷也算成功」）；訊息同 TC-040 那句 | 自動 |
| TC-048 | 計畫「不改任何資料」 | 例外 | 同 TC-047，先記下 id 1 的 `revoked_at` | 再撤一次之後讀 id 1 的 `revoked_at` | 與第一次撤銷時的值完全相同（沒被改寫） | 自動 |
| TC-049 | 計畫「二選一」：都沒給 | 例外 | `ag` 有有效 token | 執行 `agent-token revoke`（不給名字也不給 `--id`） | 回傳碼 1；標準錯誤含 `rejected: give either an agent name or --id N, not both and not neither` 與 `請給代理名字或 --id，二選一` | 自動 |
| TC-050 | 計畫「二選一」：兩個都給 | 例外 | `ag` 兩把有效 | 執行 `agent-token revoke ag --id 1` | 回傳碼 1；標準錯誤同 TC-049 那句 | 自動 |
| TC-051 | 計畫「不改資料」 | 例外 | 同 TC-049、TC-050 的兩種情形，先記下整張表 | 分別執行後各讀整張表 | `ag` 的所有 token 仍有效，表前後一致（按名字沒有被偷偷全撤） | 自動 |
| TC-052 | 計畫「`--id` 是整數」 | 例外 | `ag` 有有效 token | 執行 `agent-token revoke --id abc` | 被指令列解析器拒絕，回傳碼 2 | 自動 |
| TC-053 | 同上 | 例外 | 同 TC-052，先記下整張表 | 執行後讀整張表 | 前後一致 | 自動 |
| TC-054 | 計畫「決定（store）」None 的情況 | 例外 | 一把 run token、一把 PAT、一把已撤銷的 agent token、一個不存在的 id | 各呼叫 `store.revoke_agent_token(tokens_path, 該 id)`；再對不存在的檔案路徑呼叫一次 | 每次都回傳 `None`，資料不變 | 自動 |

## User Story 5 — 這次明講不做的事（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 計畫「不做」第 2 條、裁決 3：不加撤銷前確認 | 不在範圍 | `ag` 兩把有效；指令在沒有任何輸入（沒有終端機可回答）的情況下執行 | 執行 `agent-token revoke --id 1` | 直接完成（回傳碼 0、id 1 已撤），沒有「確定嗎？」之類的提問、也不卡住等輸入 | 自動 |
| TC-061 | 計畫「不做」第 3 條、裁決 1：不加 MCP 工具、網頁路由、`actions/` 函式 | 不在範圍 | 本分支程式 | 列出 `actions` 模組的名字、MCP 工具清單、網頁路由 | `actions` 沒有任何含 `user`／`pat`／`token` 的名字；MCP 工具與網頁路由都沒有 token 管理（沿用既有 `test_pat.py::test_tca11_*` 並由新檔再斷言一次 `actions` 這一側） | 自動 |
| TC-062 | 計畫「不做」第 4 條：不做「自動挑最舊一把」之類的聰明模式 | 不在範圍 | `ag` 兩把有效 | 執行 `agent-token revoke ag --oldest` | 被指令列解析器拒絕（回傳碼 2，不認得這個選項），兩把都仍有效 | 自動 |
| TC-063 | 計畫「不做」第 5 條：不給 `pat list` 加 agent token | 不在範圍 | `ag` 兩把 agent token，另有一把 PAT | 執行 `pat list` | 只列出 PAT；沒有任何 agent token 的行 | 自動 |
| TC-064 | 計畫「不做」第 5 條：不加 `--all`／`--json` | 不在範圍 | 任一狀態 | 執行 `agent-token list --json`、`agent-token list --all` | 兩者都被指令列解析器拒絕（回傳碼 2） | 自動 |
| TC-065 | 計畫「不做」第 6 條、「遷移說明」：不新增欄位、不改結構 | 不在範圍 | 用本分支建立一份 `tokens.db` | 讀 `tokens` 資料表的欄位清單 | 欄位恰為 `id`、`token_hash`、`created_at`、`kind`、`agent_name`、`revoked_at`、`run_name`、`expires_at`、`ended_at`、`user_id`、`label`、`grant_id`（與改動前相同），且本任務沒有新增 migration 檔 | 自動 |
| TC-066 | 計畫「遷移說明」：既有資料不改、舊資料庫直接可用 | 不在範圍 | `ag` 兩把與其他種類 token，先記下整張表 | 執行 `agent-token list`，再執行一次 `agent-token revoke --id 1` | `list` 完全不改表；`revoke --id 1` 之後只有 id 1 的 `revoked_at` 變了，其餘每一列、每個欄位都沒變 | 自動 |

## 憲法與安全網

涉及的規則：憲法原則 V「憑證不被印出」（`.specify/memory/constitution.md` 約第 196–204 行：憑證只留在自己的設定區，絕不印出）；以及專案專長守則（動作層唯一、對等性）。這個任務是終端機操作者專用的指令，不經 MCP／網頁，故憲法 I.2 的「人按送出」確認管道不適用（見總覽）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 原則 V：憑證不被印出（出錯路徑也一樣） | 例外 | `ag` 兩把、一把 run token、一把 PAT，已知它們的原值與 sha256 | 依序執行：`revoke --id 999`、`revoke --id <run token id>`、`revoke --id <PAT id>`、`revoke`（不給參數）、`revoke ag --id 1`、`revoke --id abc` | 每一次的標準輸出與標準錯誤都不含任何 token 原值或其 sha256 | 自動 |
| TC-071 | 專長守則：動作只在動作層，CLI 只是薄呼叫端 | 功能 | `platform/abf_platform/cli.py` | 用程式語法樹檢查 `cmd_agent_token_list` 與 `cmd_agent_token_revoke` 的內容 | 兩個函式內都沒有 `sqlite3`、`execute(`、`SELECT`、`UPDATE`；且分別呼叫 `store.list_agent_tokens`、`store.revoke_agent_token` | 自動 |
| TC-072 | 專長守則：對等性（使用者可見動作與動作層函式一一對應） | 功能 | 本分支程式 | 同一個測試同時列舉兩邊：CLI 的 `agent-token list` 與 `agent-token revoke --id`，以及 `store` 的 `list_agent_tokens` 與 `revoke_agent_token` | 兩邊一一對應；任何一邊缺了，測試就失敗 | 自動 |
