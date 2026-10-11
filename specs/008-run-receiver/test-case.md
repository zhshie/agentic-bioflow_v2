# 測試案例：平台收得到 Nextflow 的進度，AI 看得到（run receiver＋唯讀 MCP）

**規格**：`specs/008-run-receiver/spec.md`　**總覽**：`test-case-overview.md`

類型只有三種：
- **功能**：規格說要做到的事，在正常情況下有做到。
- **例外**：出錯、缺東西，或使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事。測試確認它真的沒做，或會明白說「這個不支援」，而不是悄悄亂做。

名詞：
- **fixture 管線**：放在 `platform/tests/fixtures/` 的小型本機 Nextflow 管線，不需要容器。
  - **成功管線**一定會成功。
  - **失敗管線**有一個 task 會 exit 1。
- **H**：釘死版本的 Nextflow 的心跳間隔，數值由 executor 從原始碼查出，寫進 `research.md`。
- **canary**：測試故意塞進去的假秘密字串，事後確認它沒被存下。
- **重放**：把先前從真 Nextflow 錄下的送件，原樣再送一次。
- **資料庫位元組**：index 與 tokens 兩個資料庫檔，連同旁邊的 `-wal`、`-shm`、`-journal` 檔的全部內容。

所有「自動」案例都由 `tests/platform_test.sh` 一併執行，它會呼叫 `platform/tests/` 的 pytest。「e2e」表示用真的 Nextflow 跑，檔名是 `platform/tests/test_nextflow_e2e.py`。

## User Story 1 — Nextflow 跑起來，平台就知道（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | FR-001、FR-002；US1 情境 1；SC-001 | 功能 | 平台在本機執行，已發一組 token，資料庫是空的 | e2e：以 `-with-tower` 與 token 跑成功管線，並開 `-with-trace` | `get_run` 回的 run 名稱等於 Nextflow 自己印出的 run name。session ID 等於 `.nextflow/history` 或 `.nextflow.log` 裡的 session ID。狀態是「成功」。task 總數＝成功數＝trace 檔的資料列數 N，且 N≥3。開始與結束時間落在 Nextflow 執行前後的時間窗內。N 不能是測試裡寫死的數字 | 自動：e2e |
| TC-002 | US1 情境 2 | 功能 | 慢速 fixture 管線（有一個 task 睡約 20 秒）；平台有錄下收到的最後一筆 progress | e2e：管線執行到一半（已有 task 完成、仍有 task 在跑）時呼叫 `get_run` | 狀態是「執行中」。task 數字等於平台最近一次收到的 progress 裡的數字，而且不等於最終數字（證明不是事後補上的） | 自動：e2e |
| TC-003 | US1 情境 3 | 功能 | 失敗管線 | e2e：跑到整個 run 失敗 | 狀態是「失敗」。失敗 task 名稱等於 trace 檔中 status 為 FAILED 那一列的 name，exit code 是 1。錯誤訊息含 fixture 失敗 task 自己 echo 的獨特字串（例如 `FIXTURE_BOOM_7`）。成功數等於 trace 中 COMPLETED 的列數 | 自動：e2e |
| TC-004 | US1 情境 4 | 功能 | 成功管線已跑過一次 | e2e：在同一個啟動資料夾用 `-resume` 再跑一次 | 平台上有 2 個 run，run name 不同、session ID 相同，兩個都能被 `list_runs` 與 `get_run` 取到。第二次的 task 數（含 cached）與 Nextflow 第二次自己的 trace 一致 | 自動：e2e |
| TC-005 | FR-006；US1 情境 5 | 例外 | 重放 create、begin 和一筆 progress，不送 complete；假時鐘的最後消息時間為 T | 用假時鐘分別在 T＋3H−1 秒、T＋3H＋1 秒查詢 | 前者是「執行中」，後者是「失聯」，任何時間都不會是「成功」。查詢前後資料庫檔都沒有被寫入（證明是查詢時當場判斷，沒有背景程式） | 自動 |
| TC-006 | FR-006 | 例外 | 同 TC-005，狀態已判為「失聯」 | 之後重放 complete（成功或失敗） | 狀態變成對應的「成功」或「失敗」，不會繼續停在「失聯」 | 自動 |
| TC-007 | FR-001 | 功能 | 從釘死版本的 Nextflow 真跑錄下的五種 payload（版本記在檔頭） | 依序重放 create、begin、progress、heartbeat、complete，網址帶 `?workspaceId=12345`。再在每筆 payload 加一個不認得的欄位，重送一次 | 全部回 2xx。run 資料與不帶 workspaceId 時相同（忽略它的值）。多出來的欄位不會造成失敗，也不會被存進資料庫 | 自動 |
| TC-008 | FR-001 | 功能 | 平台在執行 | 帶合法 token 呼叫 `GET /user-info` | 回 200 和合法 JSON（外掛能解析），回應裡沒有任何 token | 自動 |
| TC-009 | FR-002 | 功能 | 重放真 payload 的 create | 看回應 | 回應 JSON 有非空的 `workflowId`，值等於 sha256(sessionId＋"/"＋runName) 的前 16 個十六進位字元。後續的 begin、progress 用它能找到同一個 run。TC-001 的真 Nextflow 沒有因為缺 `workflowId` 而中止 | 自動 |
| TC-010 | FR-001 | 例外 | 平台在執行，已有 1 個正常的 run | 分別送壞掉的 JSON、給不存在 run ID 的 progress、空內容 | 每次都回 4xx 並附說明，不是 500。沒有新增任何 run 列。之後正常的送件仍然收得下 | 自動 |

## User Story 2 — 沒有 token 或 token 錯，平台不收（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | FR-003；US2 情境 1 | 例外 | 資料庫是空的，先記下各表列數 | 不帶 Authorization 送 create | 回 401。runs、processes、failed_tasks 的列數都沒變（零紀錄） | 自動 |
| TC-012 | FR-003；US2 情境 1 | 例外 | 同上 | 用錯的 token，分別對五個端點（create、begin、progress、heartbeat、complete）和 user-info 送件 | 全部回 401，列數都沒變 | 自動 |
| TC-013 | US2 情境 1 | 例外 | 成功管線，故意給錯的 token | e2e：啟動真 Nextflow | Nextflow 以非零退出碼停下，輸出含驗證失敗的相關訊息。trace 檔沒有任何 task 列（開跑前就停下）。平台上零紀錄 | 自動：e2e |
| TC-014 | FR-003 | 功能 | 一組平台發的 token | 分別用 `Authorization: Bearer <token>` 和 Basic（使用者名 `@token`、密碼空白，也就是 Nextflow 實際送出的樣子）送 create | 兩種都回 2xx 並建立 run。TC-001 裡真 Nextflow 用平台發的 token 跑成功（證明 token 格式與 Nextflow 的送法相容） | 自動 |
| TC-015 | FR-003；US2 情境 2 | 例外 | token A 建立了 run A，token B 是另一組有效 token | 用 B 對 run A 送 progress、heartbeat、complete | 全部被拒（401 或 403），run A 的資料列內容與送件前完全相同。B 自己的 create 仍然成功 | 自動 |
| TC-016 | FR-003 | 功能 | 用 `token new` 發一組 token | 檢查資料庫位元組；重啟平台後，再用同一組 token 送件 | 資料庫位元組裡找不到 token 明文，只有雜湊。重啟後 token 仍然有效 | 自動 |
| TC-017 | FR-003 | 功能 | 無 | 連續執行兩次 `abf-platform token new` | token 只在發出當下顯示一次。兩組不同，每組至少 32 個字元。之後無法再查到明文 | 自動 |
| TC-018 | FR-004 | 功能 | 用預設設定啟動 `abf-platform serve` | 從 127.0.0.1 連線，再用本機非 loopback 網卡的位址連線 | 127.0.0.1 連得上，非 loopback 位址的連線被拒。如果機器沒有第二個網卡位址，測試印出原因，改為檢查 socket 綁定位址是 127.0.0.1（不能靜默通過） | 自動 |
| TC-019 | FR-004 | 功能 | 啟動時明確給 `--host 0.0.0.0` | 連線 | 連得上，啟動輸出有一行風險提示 | 自動 |

## User Story 3 — AI 用 MCP 查得到（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | FR-007；US3 情境 1 | 功能 | 透過接收端（不是直接寫資料庫）建立 3 個開始時間各不相同的 run | 用官方 `mcp` SDK 的 client 以 stdio 連線，呼叫 `list_runs` | 回 3 筆，按開始時間由新到舊排。每筆含名字、狀態、開始時間、task 進度 | 自動 |
| TC-021 | FR-007；US3 情境 2 | 功能 | 失敗管線的 run（TC-003） | 呼叫 `get_run` | 回傳狀態、開始與結束時間、各 process 的 task 數（等於 trace 檔按 process 分組的統計），以及失敗 task 的名稱、exit code、錯誤訊息 | 自動：e2e |
| TC-022 | US3 情境 3 | 例外 | 一個不存在的 run ID | 呼叫 `get_run` | 回「找不到這個 run」並附上該 ID，不是空白、堆疊追蹤或協定層錯誤。之後再呼叫 `list_runs` 仍然正常 | 自動 |
| TC-023 | US3 情境 4 | 功能 | 照 `docs/PLATFORM.md` 把 MCP 接到 Claude Code（以及 Claude Desktop） | 問「我最近的 run 狀態」 | AI 呼叫 `list_runs` 並據此回答，答案與平台上的資料一致 | 手動：`docs/TESTING.md` |
| TC-024 | FR-007；US3 情境 5 | 功能 | MCP server 已啟動 | 列出工具 | 恰好兩個工具：`list_runs`、`get_run`。兩個的 `readOnlyHint` 都是 true，`destructiveHint` 都不是 true。沒有名稱含 launch、cancel、delete、clean、write 的工具 | 自動 |
| TC-025 | FR-007 | 功能 | 以 `abf-platform mcp --http` 啟動 | 用 SDK client 以 Streamable HTTP 連線，呼叫 `list_runs` 與 `get_run` | 結果與 stdio 相同。只聽 127.0.0.1，除非明確給了 `--host` | 自動 |
| TC-026 | FR-006 | 功能 | 一個沒收到 complete 的 run，接收端已停止 | 用假時鐘推到 T＋3H＋1 秒，再經 MCP 查詢 | `list_runs` 和 `get_run` 都顯示「失聯」（MCP 與接收端用同一套判斷） | 自動 |

## User Story 4 — 平台的紀錄可以從 Nextflow 自己的紀錄重建（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | FR-005；US4 情境 1；SC-002 | 功能 | e2e 已產生成功、失敗、resume 三種 run，並先存下每個 run 的 `get_run` 結果 | 停掉平台，把 index 資料庫檔連同 `-wal`、`-shm` 全部刪除（先確認檔案確實不存在），再對那些啟動資料夾執行 `abf-platform rebuild` | run 數量相同且大於 0。每個 run 逐欄與刪除前完全相同：run ID、名稱、session ID、狀態、開始與結束時間、task 總數、成功數、cached 數、失敗數，以及失敗 task 的名稱、exit code、錯誤訊息 | 自動：e2e |
| TC-031 | US4 情境 2 | 例外 | 同上，再人為弄壞索引：把某個已完成 run 的 complete 與狀態抹掉，並把 task 數改錯 | 執行 `rebuild` | 重建後該 run 的狀態與 task 數，等於 Nextflow 自己的紀錄（trace、log）裡的值，而不是被弄壞的值 | 自動：e2e |
| TC-032 | FR-003、FR-005 | 功能 | 重建前發過 token X，並用 X 跑過 run | 刪掉 index 資料庫、執行 `rebuild`，再用 X 送一個新 run 的 create | X 仍然有效（重建不會讓大家的 token 全部失效）。重建不需要任何舊的 index 資料庫 | 自動 |
| TC-033 | FR-005；憲法 VI | 例外 | 重建的參數裡有一個不存在的資料夾、一個沒有讀取權限的資料夾、一個正常的資料夾 | 執行 `rebuild` | 輸出明說哪個資料夾、為什麼被略過。總結列出已重建與已略過各幾個。有略過時退出碼非零。正常資料夾的 run 仍然被重建 | 自動 |
| TC-034 | FR-005、FR-006 | 例外 | 一個啟動資料夾，裡面的 Nextflow 在送出 complete 之前被 `kill -9` | 執行 `rebuild` | 該 run 既不是「成功」也不是「執行中」，而是「失聯」，與重建前即時判斷的規則一致。最後消息時間取 `.nextflow.log` 最後一行的時間 | 自動：e2e |
| TC-035 | FR-005；憲法原則 3 | 功能 | 兩種啟動方式：一種設定 `ABF_PLATFORM_DB=<暫存路徑>`；另一種不設定它，但設 `XDG_DATA_HOME=<暫存路徑>` | 發 token、收一筆 create | 第一種的資料庫只出現在指定路徑。第二種出現在 `<XDG_DATA_HOME>/abf-platform/` 底下。兩種情況下，使用者家目錄與目前工作目錄都沒有新檔 | 自動 |

## User Story 5 — 只存 metadata，不存秘密（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | FR-008；US5 情境 1 | 例外 | 重放一筆 begin，內容含：`configText`（含 canary `CFG_CANARY_9f3`）、`commandLine`（含 `--api_key CMD_CANARY_5d1`）、環境變數（含 canary `ENV_CANARY_2b7`）、params `api_token`、`my_password`、`aws_secret_key`（值都是 canary），以及 `outdir`＝`results`、`genome`＝`GRCh38` | 收下後掃描資料庫位元組 | 找不到任何 canary。params 中 `api_token`、`my_password`、`aws_secret_key` 只有名字、沒有值。`outdir`＝`results`、`genome`＝`GRCh38` 有被存下 | 自動 |
| TC-041 | FR-008；US5 情境 1 | 例外 | e2e：config 檔含 canary；執行 Nextflow 前 export 一個含 canary 的環境變數；params 帶 `--access_token CANARY` | 跑完後掃描資料庫位元組 | 找不到任何 canary | 自動：e2e |
| TC-042 | FR-008 | 例外 | 重放一筆 begin，params 名稱有 `TOKEN`、`secretName`、`ssh_key_path`、`Password`、巢狀的 `{"db": {"password": "x"}}`，以及一個無關的 `outdir` | 查詢資料庫 | 名字含 token、password、secret、key 的（不分大小寫，巢狀層也算）一律不存值。`outdir` 的值有存 | 自動 |
| TC-043 | FR-008；US5 情境 2 | 例外 | 用 token T 建立並跑完一個 run | 收集 create 的回應、`/user-info`、MCP 的 `list_runs` 與 `get_run`，以及接收端所有可以 GET 的路徑的回應 | 所有回應裡都找不到 T 的明文、T 的雜湊值，也沒有 Authorization 字樣 | 自動 |
| TC-044 | FR-008 | 例外 | 擷取接收端與 MCP server 的標準輸出和標準錯誤 | 做一次成功的送件和一次 401 送件 | 輸出裡找不到 token 明文，也找不到 Authorization 標頭的內容 | 自動 |

## FR-009／FR-010／成功條件／測試本身

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | FR-009 | 功能 | 乾淨的環境，只有 `docs/PLATFORM.md` | 請一個沒做過的人照文件從頭做 | 不需要外部知識就能完成五件事：啟動平台、發 token、讓 Nextflow 指向平台、讓 Claude Code 與 Claude Desktop 接上 MCP、重建索引。文件寫出對外開放的風險，以及預設位置可以覆蓋 | 手動：`docs/TESTING.md` |
| TC-051 | FR-010 | 功能 | 掃描整個 `platform/`、fixture 與 `docs/PLATFORM.md`；e2e 的執行環境 | 執行 e2e | 原始碼、fixture、設定裡沒有 Seqera 服務位址（`cloud.seqera.io`、`api.cloud.seqera.io`、`tower.nf`），也沒有呼叫 `tw`。e2e 傳給 Nextflow 的 `tower.endpoint` 一定是本機位址。測試環境的 PATH 裡沒有 `tw` 時，仍然通過 | 自動 |
| TC-052 | SC-003 | 功能 | WSL，以及 GitHub CI | 在 WSL 跑 `bash tests/run_all.sh`；CI 跑 workflow | 兩邊都全綠，輸出看得到 `platform_test.sh` 有被執行並通過，e2e 沒有被 skip（見 TC-054） | 手動：`docs/TESTING.md`（WSL）；CI 結果 |
| TC-053 | SC-001 | 功能 | WSL 本機，平台在執行 | 手動跑 `nextflow run nextflow-io/hello -with-tower http://127.0.0.1:<port>`，成功一次，再故意讓它失敗一次 | `list_runs`／`get_run` 回的狀態和 task 數，跟 Nextflow 自己印出來的一致 | 手動：`docs/TESTING.md` |
| TC-054 | 憲法 VI；plan「Tests」 | 例外 | 三種情況：PATH 裡沒有 Java、Nextflow 下載失敗（把下載位址指向不可達處）、外掛下載失敗；每種都在 `CI=true` 與未設定 `CI` 下各跑一次 | 執行 `tests/platform_test.sh` | `CI=true` 時三種情況都是失敗（退出碼非零）。沒設 `CI` 時，輸出有明顯的一行 `E2E SKIPPED: <原因>`，總結裡列出被 skip 的測試數。任何情況都不能出現沒有提示的綠燈 | 自動 |
| TC-055 | plan「Wrapper」 | 例外 | 在暫存的 `platform/` 副本中加入一個會失敗的 pytest | 執行 `tests/platform_test.sh` | 退出碼非零，輸出指出是哪個測試失敗 | 自動 |
| TC-056 | plan「Risks」 | 功能 | e2e 使用的 Nextflow 版本與 nf-tower 外掛版本都是固定值 | 把預期的 sha256 改錯再跑 | 下載驗證失敗並停下，不會拿未驗證的檔案繼續。下載的檔案放在快取資料夾，不在儲存庫內 | 自動 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 不在範圍 1 | 不在範圍 | 接收端與 MCP server 都在執行 | 對接收端送 `POST /launch`、`DELETE /runs/<id>`、`POST /runs/<id>/cancel`，以及任何寫入 `work/` 的路徑；列出所有 MCP 工具 | 這些路徑回 404 或 405。MCP 只有 TC-024 那兩個唯讀工具，沒有確認頁面 | 自動 |
| TC-061 | 不在範圍 2 | 不在範圍 | 掃描 `platform/` 的非測試原始碼 | 搜尋 ssh、sbatch、scancel、`tw `，以及站台代理相關程式 | 一個都沒有。平台執行時只有監聽，沒有對外連線 | 自動 |
| TC-062 | 不在範圍 3 | 不在範圍 | 接收端在執行 | 請求 `GET /`、`/login`、`/oauth/*`，並檢查資料庫結構 | 沒有網頁（回 404），沒有登入或 OAuth 路徑。資料庫沒有角色、使用者或組織相關的欄位 | 自動 |
| TC-063 | 不在範圍 4 | 不在範圍 | 本 feature 的完整 diff | 檢查 `.specify/memory/constitution.md` 與 `docs/ROADMAP.md` | 憲法檔沒有任何修改，版本仍是 3.0.0。`docs/ROADMAP.md`「Principles waiting for a check」那一列仍在原表，只加註「檢查已存在（`platform/tests/...`）」與「下一步是修憲 PR」，沒有被移進憲法 | 手動：驗收者用 git diff，步驟寫入 `docs/TESTING.md` |
| TC-064 | 不在範圍 5；Tier A | 不在範圍 | 本 feature 的完整 diff | 看 diff | `hooks/`、`scripts/`、`skills/`、`commands/`、`.claude-plugin/` 底下沒有任何檔案被修改 | 手動：驗收者用 git diff，步驟寫入 `docs/TESTING.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 原則 1（先說出現成替代品） | 功能 | `platform/` 底下每個 `.py` 原始檔（含 `cli.py`） | 用與 `tests/scripts_name_their_alternative.sh` 相同的規則檢查：前 40 行要有 `# Not <tool>: <理由>` 或 `# Nothing existing: <理由>`，`<tool>` 不能是本儲存庫的檔案，理由至少 15 字元。另造一個缺標頭的檔案，證明這個檢查會紅 | 全部通過，缺標頭的暫存檔會被抓出來 | 自動 |
| TC-071 | 原則 2（沒有第二份真相、沒有自己的投遞程式、沒有常駐監看） | 功能 | 掃描 `platform/` 的非測試原始碼與儲存庫檔案樹 | 搜尋 `nextflow run`、sbatch 等投遞指令；`while True`、背景執行緒、排程器、`nohup`；儲存庫內的 `*.db`、`*.sqlite`、`-wal` 檔 | 非測試程式碼裡沒有投遞，也沒有常駐迴圈或背景執行緒（TC-005 另外從行為上證明狀態是查詢時才判斷）。儲存庫內沒有已提交的資料庫檔，資料庫檔只在執行時出現在設定的位置 | 自動 |
| TC-072 | 原則 3（不寫死路徑） | 功能 | 掃描 `platform/`（含測試與 fixture）、`docs/PLATFORM.md`、`tests/platform_test.sh` | 用與 `tests/no_hardcoded_paths.sh` 相同的正規表示式 `(/home\|/work\|/scratch\|/staging\|/lustre)/[A-Za-z][A-Za-z0-9_.-]*/` 掃描 | 沒有任何命中。venv 與 Nextflow 的快取位置都由 `${XDG_CACHE_HOME:-$HOME/.cache}` 推導 | 自動 |
| TC-073 | 原則 1、2、3 的既有檢查 | 功能 | 本 feature 的完整 diff | 看 `tests/no_hardcoded_paths.sh`、`tests/scripts_name_their_alternative.sh`、`tests/no_second_run_state_test.sh`、`tests/run_all.sh` 有沒有被改動；執行 `bash tests/run_all.sh --list` | 這四個檔案沒有任何改動，清單裡有 `platform_test.sh`，三個既有檢查原樣全綠 | 手動：驗收者用 git diff，步驟寫入 `docs/TESTING.md` |
