# Feature Specification: 平台收得到 Nextflow 的進度，AI 看得到（run receiver＋唯讀 MCP）

**Feature Branch**: `008-run-receiver`

**Created**: 2026-10-11

**Status**: Draft

**Input**: 2026-10-11 維護者：「先不要管現在的 Plugin 了，趕快開始 MCP 以及平台的建立」。依 `docs/ROADMAP.md` Stage 2，先做不需要國網就能開發測試的部分：008 Tower 相容接收端＋009 MCP server 的唯讀起點。站台代理（007）等國網 M6 答案。

> 名詞見 `CONTEXT.md`。研究來源見本資料夾 `research.md`。

## 為什麼是這一塊先做

Nextflow 內建的 `nf-tower` 外掛，只要設定 `tower.endpoint`，就會把一個 run 的開始、進度、心跳、結束送到那個網址〔`TowerClient.groovy`、`TowerObserver.groovy`〕。我們的平台只要接得住這 5 種送件，就能知道每個 run 的狀態，不改 Nextflow、不寫監看程式。接得住之後，用 MCP 開兩個唯讀工具，AI（Claude Desktop／Claude Code）就能回答「我的 run 跑到哪了？哪個 task 掛了？」。

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Nextflow 跑起來，平台就知道（Priority: P1）

**Acceptance Scenarios**:

1. **Given** 平台在本機執行、使用者有一組平台給的 token，**When** 用 `nextflow run <本機小管線> -with-tower http://127.0.0.1:<port>`（帶 token）跑完（自動測試用 `platform/tests/fixtures/` 的小管線；`nextflow-io/hello` 另做手動測試），**Then** 平台記下這個 run：名字、session ID、開始與結束時間、狀態「成功」、task 總數與成功數。（正常）
2. **Given** 同上，run 跑到一半，**When** 查平台，**Then** 狀態是「執行中」，task 數字跟 Nextflow 最近一次送來的進度一致。（正常）
3. **Given** run 中有 task 失敗、整個 run 失敗，**When** 跑完，**Then** 狀態「失敗」，並記下失敗的 task 名稱、exit code 與錯誤訊息（Nextflow 送來的那段）。（正常）
4. **Given** 同一個 session 用 `-resume` 再跑一次，**When** 跑完，**Then** 平台記成第二個 run，兩個都看得到。（正常）
5. **Given** run 在 Nextflow 送出「結束」之前被強制中止（kill），**When** 超過心跳期限沒有新消息，**Then** 平台顯示「失聯」，不假裝它還在跑，也不假裝它成功。（例外）

### User Story 2 — 沒有 token 或 token 錯，平台不收（Priority: P1）

**Acceptance Scenarios**:

1. **Given** 沒帶 token 或 token 錯，**When** Nextflow 送第一筆（create），**Then** 平台拒收（401），Nextflow 在開跑前就停下並顯示驗證失敗；平台不留任何紀錄。（例外）
2. **Given** token 正確，**When** 有人用另一組正確 token 對別人的 run 送進度，**Then** 拒收；一個 token 只能更新自己建立的 run。（例外）

### User Story 3 — AI 用 MCP 查得到（Priority: P1）

**Acceptance Scenarios**:

1. **Given** 平台有 3 個 run，**When** MCP 客戶端呼叫 `list_runs`，**Then** 回傳 3 筆，最新的在前，每筆含名字、狀態、開始時間、task 進度。（正常）
2. **Given** 一個失敗的 run，**When** 呼叫 `get_run`，**Then** 回傳狀態、時間、各 process 的 task 數，以及失敗 task 的名稱、exit code、錯誤訊息。（正常）
3. **Given** 不存在的 run ID，**When** 呼叫 `get_run`，**Then** 回傳清楚的「找不到這個 run」，不是空白也不是程式錯誤。（例外）
4. **Given** Claude Code 或 Claude Desktop 照 `docs/` 的說明接上這個 MCP server，**When** 使用者問「我最近的 run 狀態」，**Then** AI 用 `list_runs` 回答。（正常，手動）
5. **Given** 任何 MCP 工具，**When** 列出工具清單，**Then** 這次的工具全部標為唯讀（`readOnlyHint`），沒有任何會啟動、取消或刪除東西的工具。（正常）

### User Story 4 — 平台的紀錄可以從 Nextflow 自己的紀錄重建（Priority: P1）

這是憲法「等待檢查的原則」第一條要的檢查（`docs/ROADMAP.md`）。

**Acceptance Scenarios**:

1. **Given** 平台已收過幾個 run，**When** 刪掉平台的資料庫，從那些 run 的啟動資料夾（`.nextflow.log`、`.nextflow/history`、trace 檔）重建，**Then** 重建出的每個 run 的名字、session ID、狀態、開始結束時間、task 總數／成功數／失敗數，跟刪之前一樣。（正常）
2. **Given** 平台的紀錄跟 Nextflow 自己的紀錄不一致（例如平台漏收了「結束」），**When** 重建，**Then** 以 Nextflow 的紀錄為準。（例外）

### User Story 5 — 只存 metadata，不存秘密（Priority: P1）

**Acceptance Scenarios**:

1. **Given** Nextflow 送來的 begin 內容含 `configText`、`commandLine`、環境變數、params，**When** 平台存下，**Then** 不存 `configText`、`commandLine`（可能含 `--api_key xxx`）與環境變數；params 只存名字和不像秘密的值（名字含 token／password／secret／key 的一律不存值）。（例外）
2. **Given** 有人用 MCP 或 API 查一個 run，**When** 回傳，**Then** 不含任何 token。（例外）

## Requirements *(mandatory)*

- **FR-001**: 平台 MUST 實作 `nf-tower` 外掛使用的這幾個端點：`POST /trace/create`、`PUT /trace/{id}/begin`、`PUT /trace/{id}/progress`、`PUT /trace/{id}/heartbeat`、`PUT /trace/{id}/complete`，並接受網址上的 `?workspaceId=`（忽略其值）。外掛在其他路徑會呼叫的 `GET /user-info` MUST 回一個合法的最小回應。payload 欄位以 Nextflow 原始碼為準（`research.md` 列出版本與連結）。
- **FR-002**: create 的回應 MUST 含 `workflowId`；缺了 Nextflow 會中止。
- **FR-003**: token MUST 接受 `Authorization: Bearer <token>` 與 Basic（使用者名 `@token`）兩種；token 由平台產生、只存雜湊；一個 token 只能寫自己建立的 run。
- **FR-004**: 預設只聽 `127.0.0.1`。要對外開放 MUST 明確設定，且說明文件寫出風險。
- **FR-005**: 平台的 run 索引是索引，不是真相；token 存在另一個檔案，重建絕不碰它。run ID 由 Nextflow 自己的紀錄決定（sessionId＋runName 的雜湊），重建後不變。存放位置由設定決定（不寫死路徑），刪掉後 MUST 能用 `rebuild` 指令從 run 的啟動資料夾重建（US4）。索引裡只放能從 Nextflow 紀錄推回來的欄位，再加上失敗 task 的錯誤訊息（重建時從 `.nextflow.log` 取）。
- **FR-006**: 超過 Nextflow 心跳間隔的 3 倍（預設心跳約 1 分鐘，以原始碼為準）沒有任何消息、又沒收到 complete 的 run，MUST 顯示為「失聯」。不需要背景程式：查詢時當場判斷。
- **FR-007**: MCP server MUST 用官方 Python `mcp` SDK，提供 stdio 與 Streamable HTTP 兩種接法；這次只有 `list_runs`、`get_run` 兩個工具，都標 `readOnlyHint: true`。
- **FR-008**: 不存 `configText`、`commandLine`、環境變數、名字像秘密的 params 值（含巢狀層，只依名字判斷）；API 與 MCP 回應不含 token。
- **FR-009**: `docs/PLATFORM.md`（新）MUST 說明：怎麼啟動平台、怎麼發 token、怎麼讓 Nextflow 指向它、怎麼讓 Claude Code／Claude Desktop 接 MCP、怎麼重建索引。
- **FR-010**: 整套測試 MUST 能在 WSL 與 GitHub CI 上跑，不需要網路以外的帳號；**全程不經 Seqera 的服務、MCP 或 `tw`**（ADR 0004）。

## 不在範圍

1. 任何寫入動作（launch、取消、刪除、清 `work/`）與確認頁面——下一個 feature，連同「寫入工具沒有確認就拒絕」的檢查一起做。
2. 站台代理、國網連線（007）。
3. 多人與角色（010）、網頁（011+）、OAuth、上雲端。
4. 憲法修正：本 feature 做出重建檢查後，「索引不是第二份真相」入憲是另一個修正 PR（C 級，維護者 merge）。
5. 現有 plugin 的 hooks、scripts、skills 不動。

## Success Criteria

- **SC-001**: 在 WSL 本機跑 fixture 小管線（成功一次、故意失敗一次；手動再跑一次 `nextflow-io/hello`），`list_runs`／`get_run` 回答的狀態與 task 數跟 Nextflow 自己印的一致。
- **SC-002**: 刪資料庫→重建→每個 run 的欄位跟刪之前相同。
- **SC-003**: 整套測試（含既有的）在 WSL 與 CI 全綠。

## Assumptions

- WSL 有 Java 17（已確認 17.0.18）；Nextflow 由測試自行下載到快取資料夾，版本釘死。
- CI 能用 pip 安裝套件。
