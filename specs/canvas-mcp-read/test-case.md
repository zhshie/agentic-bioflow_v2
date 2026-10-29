# 測試案例：畫布後端的五個唯讀動作開給 MCP（canvas-mcp-read）

<!--
Written by the verifier (CONTRACT mode). Source: specs/canvas-mcp-read/plan.md (B 級，無 spec.md；計畫與補充裁決 13-1…13-6 即規格)。
-->

**規格**：`specs/canvas-mcp-read/plan.md`（本片沒有 spec.md，以計畫的「維護者原話」「作法」「失敗先行測試」「不做」「補充裁決 13-1…13-6」為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「MCP 工具」是使用者的 AI 能呼叫的功能；「動作層」是專案唯一共用的那一層函式（網頁、MCP、聊天都呼叫它）；「甲、乙」是兩位不同的使用者，各有自己的 token（登入憑證）。

## User Story 1 — 使用者的 AI 能找模組、看模組（優先度 P1）

維護者原話：「done：MCP `find_module("fastqc")` 回 name/sha/輸入輸出型別。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 017a；13-2 | 功能 | 平台已啟動，目錄資料檔（`data/nf-core-modules.json`）在 | 經 MCP 呼叫 `find_module("fastqc")` | 回傳最外層有 `sha`（非空，等於目錄快照的 sha），且 `count` 等於 `modules` 的筆數、至少 1 | 自動：`platform/tests/test_mcp_canvas_read.py` |
| TC-002 | 原話 017a；13-2 | 功能 | 同上 | 經 MCP 呼叫 `find_module("fastqc")` | `modules` 裡有一筆 `name` 為 `fastqc`，並帶 `path`、`description` | 自動 |
| TC-003 | 原話 017a「輸入輸出型別」；13-2 | 功能 | 同上 | 經 MCP 呼叫 `find_module("fastqc")` | 該筆帶 `inputs`、`outputs`，內容與資料檔裡 fastqc 的同名欄位一致（欄位沒被改名） | 自動 |
| TC-004 | 13-2「sha 不逐筆重複」 | 功能 | 同上 | 經 MCP 呼叫 `find_module("fastqc")` | `modules` 的每一筆都沒有 `sha` 鍵 | 自動 |
| TC-005 | 13-2「有結果時沒有 hint 鍵」 | 功能 | 同上 | 經 MCP 呼叫 `find_module("fastqc")` | 回傳沒有 `hint` 鍵 | 自動 |
| TC-006 | 計畫「失敗先行測試」第 2 條 | 例外 | 同上 | 經 MCP 呼叫 `find_module("沒有這個模組xyz")` | 不丟例外；回 `count` 為 0、`modules` 為空清單，最外層仍有 `sha` | 自動 |
| TC-007 | 計畫「失敗先行測試」第 2 條；13-2 | 例外 | 同上 | 經 MCP 呼叫 `find_module("沒有這個模組xyz")` | 回傳有 `hint`，是一句非空的話，叫人換關鍵字或用工具名，並舉 `fastqc` 為例 | 自動 |
| TC-008 | 原話 017a「describe_module(name)」 | 功能 | 同上 | 經 MCP 呼叫 `describe_module("fastqc")` | 回 `found: true`，`name` 為 `fastqc`，並帶 `inputs`、`outputs` | 自動 |
| TC-009 | 計畫「失敗先行測試」第 3 條；13-6 | 例外 | 同上 | 經 MCP 呼叫 `describe_module("沒有這個模組xyz")` | 回 `found: false`，`name` 等於輸入的 `沒有這個模組xyz`，不丟例外 | 自動 |
| TC-010 | 13-6 | 例外 | 同上 | 同 TC-009 | `message` 裡有輸入的名稱，也有 `find_module`（叫人去用它找相近的名字），不是舊的 `search` | 自動 |
| TC-011 | 計畫「新增工具與歸屬」：目錄是公開資料 | 功能 | 甲、乙各有 token | 甲、乙各自經 MCP 呼叫 `find_module("fastqc")` | 兩人拿到的結果相同，沒有因為身分不同而被篩選 | 自動 |
| TC-012 | 計畫範圍：`find_module(q, *, data=None)` 薄包裝 | 功能 | 在測試裡自備一份小目錄資料（只有一個假模組） | 直接呼叫 `actions.catalogue.find_module(q, data=該資料)` | 結果只來自該資料，形狀與 TC-001～005 一致（含 `sha`、`count`、`modules`） | 自動 |
| TC-013 | 計畫範圍：`describe_module(name, *, data=None)` 薄包裝 | 功能 | 同 TC-012 | 直接呼叫 `actions.catalogue.describe_module(name, data=該資料)`，各試一次存在與不存在的名稱 | 存在時 `found: true`；不存在時 `found: false` 且訊息同 TC-010 | 自動 |
| TC-014 | 專長守則：錯誤訊息不露內部 | 例外 | 同上 | 檢查 TC-006、TC-009 的回應文字 | 沒有堆疊追蹤、檔案路徑或 SQL 字樣 | 自動 |

## User Story 2 — 使用者的 AI 只看得到自己的 pipeline（優先度 P1）

維護者原話：使用者的 AI 要能問「我有哪些 pipeline」；裁示 1：「使用者用自己的 AI 走 MCP」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 計畫「新增工具與歸屬」list_pipelines | 功能 | 甲用自己的 token 建了一個 pipeline | 甲經 MCP 呼叫 `list_pipelines()` | 清單裡有甲的這個 pipeline（含 id、名稱、最新版本、節點數） | 自動 |
| TC-016 | 同上 get_pipeline | 功能 | 甲的 pipeline 有 2 個版本 | 甲經 MCP 呼叫 `get_pipeline(id)`（不給版本） | 回最新版本的圖 | 自動 |
| TC-017 | 同上 get_pipeline(pipeline_id, version) | 功能 | 同 TC-016 | 甲經 MCP 呼叫 `get_pipeline(id, version=1)` | 回第 1 版的圖，不是最新版 | 自動 |
| TC-018 | 同上 get_validation | 功能 | 甲的某一版已有一次驗證結果 | 甲經 MCP 呼叫 `get_validation(id)` | 回該版已保存的驗證結果 | 自動 |
| TC-019 | 同上 get_validation（動作層文件：從未驗證回 `validation: None`） | 功能 | 甲的 pipeline 從未驗證過 | 甲經 MCP 呼叫 `get_validation(id)` | 回 `validation` 為空（None），不丟例外 | 自動 |
| TC-020 | 計畫目標「只開唯讀」；動作層「nothing is checked again here」 | 功能 | 記下平台資料庫的內容 | 依序經 MCP 呼叫五個新工具（含 `get_validation`） | 呼叫前後資料庫內容完全相同（沒新增列、沒重新驗證、沒留紀錄） | 自動 |
| TC-021 | 計畫「失敗先行測試」第 4 條（list） | 例外 | 甲建了 pipeline；乙有自己的 token | 乙經 MCP 呼叫 `list_pipelines()` | 乙的清單裡沒有甲的 pipeline（id、名稱都不出現） | 自動 |
| TC-022 | 同上（get_pipeline） | 例外 | 同上 | 乙經 MCP 呼叫 `get_pipeline(甲的 id)` | 回「找不到這個組合 (pipeline not found)」，回應裡沒有甲的名稱或圖 | 自動 |
| TC-023 | 同上（get_validation） | 例外 | 同上，甲的 pipeline 有驗證結果 | 乙經 MCP 呼叫 `get_validation(甲的 id)` | 回「找不到」，回應裡沒有甲的驗證內容 | 自動 |
| TC-024 | 動作層規則：「他人的就像不存在」 | 例外 | 同上 | 乙分別呼叫 `get_pipeline(甲的 id)` 與 `get_pipeline(一個根本不存在的 id)` | 兩個回應除了 id 本身外形狀與文字相同，乙無法分辨是「別人的」還是「不存在」 | 自動 |
| TC-025 | 專長守則：路由／工具不得有第二份邏輯；計畫「擁有者規則在動作層，不在工具層」 | 功能 | 甲、乙各有 pipeline | 以同一個身分，分別經 MCP 與直接呼叫動作層（`actions.pipelines`）執行 list／get／get_validation | 三個工具的回傳與動作層回傳完全一致 | 自動 |

## User Story 3 — 工具登記、名單、聊天提示與既有測試（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 計畫「新增工具」；裁決 2 | 功能 | 平台 MCP 伺服器建好 | 列出已登記的工具名 | 有 `find_module`、`describe_module`、`list_pipelines`、`get_pipeline`、`get_validation`；沒有 `get_pipeline_version` | 自動 |
| TC-027 | 計畫「失敗先行測試」第 5 條 | 功能 | 同上 | 檢查五個新工具的註記 | 五個都標 `_READ_ONLY` | 自動 |
| TC-028 | 計畫「失敗先行測試」第 6 條；`test_mcp_server_doc.py` | 功能 | 同上 | 檢查工具名單與計數 | 名單＝舊的 15 個加這 5 個（共 20 個）；唯讀 15 個；其餘 5 個非唯讀（launch、cancel、forget、resume、relaunch） | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-029 | 計畫範圍：檔頭 docstring；13-4 | 功能 | 同上 | 讀 `mcp_server.py` 檔頭 docstring | 點名全部 20 個工具，且唯讀工具數寫「fifteen read」，與實際一致 | 自動：`test_mcp_server_doc.py` |
| TC-030 | 13-4「第 1 行註解的工具數字一併更新」 | 功能 | 同上 | 讀 `mcp_server.py` 第 1 行註解 | 不再寫舊數字 | 自動：`test_mcp_server_doc.py` |
| TC-031 | 13-4「其餘斷言不准放寬」 | 功能 | 對照 base | 比較 `test_mcp_server_doc.py` 與 base | 只有名單、計數、數字詞表（加 thirteen／fourteen／fifteen）改動，其餘斷言沒被刪或放寬 | 手動：驗收者以 `git diff` 對照 base |
| TC-032 | 計畫「失敗先行測試」第 5 條 | 功能 | 平台伺服器與 `/chat/spec` | 啟動 `/chat/spec`（聊天的工具分類檢查 `classify_check`） | 不丟 ValueError，仍能啟動 | 自動 |
| TC-033 | 裁決 1；13-1 | 功能 | 對照 base 的 `CHAT_SYSTEM_PROMPT` | 讀聊天系統提示 | 比 base 多一行，且這行有「模組」與「pipeline」字樣（只講查模組、查自己的 pipeline） | 自動：`test_chat_tools.py` |
| TC-034 | 裁決 1；`chat_tools.BANNED_WORDS` | 功能 | 同上 | 檢查整份系統提示 | 不含 `approve`、`confirm`、`confirmed_by`、`void`、`yes` | 自動：`test_chat_tools.py` |
| TC-035 | 13-1「其餘斷言不准改」 | 功能 | 對照 base | 比較 `test_chat_tools.py` 與 base | 除名單與計數外，只多了 TC-033／TC-034 的斷言，沒有其他改動 | 手動：驗收者以 `git diff` 對照 base |
| TC-036 | 計畫「失敗先行測試」第 6 條；「完成標準」 | 功能 | 所有釘住工具名單的測試檔（`git grep -l '"my_usage"' platform/tests` 列出者）已更新 | 跑全套測試 | 全綠（已知環境紅除外）；`GREEN <HEAD sha>` 完成記號與 HEAD 相符 | 自動：`tests/run_all.sh`（驗收者看完成記號） |
| TC-037 | 13-3 | 功能 | `test_web_parity.py` 一字不改 | 跑 `test_web_parity.py` | 全綠（四張 parity 表一字未動） | 自動：`platform/tests/test_web_parity.py` |
| TC-038 | 13-3；計畫「OWED 只准縮、不准長」 | 功能 | 同上 | 讀 `OWED` | 仍恰好是 `get_compute_env`、`list_agents`、`list_site_files`、`read_task_log`、`forget` 五個，沒有新增 | 自動：`test_web_parity.py`（`test_tcs07_owed_is_written_out`） |
| TC-039 | 13-3；`test_pipelines_store.py:308` | 功能 | 匯入 `abf_platform.actions` | 看 `actions` 套件的公開名稱 | 沒有 `find_module`、`describe_module`；`actions/__init__.py` 沒被改；`test_pipelines_store.py` 仍綠 | 自動 |
| TC-040 | 13-3 | 功能 | 讀 `mcp_server.py` 原始碼 | 檢查匯入寫法 | 用 `import abf_platform.actions.catalogue as catalogue_actions` 與 `import abf_platform.actions.pipelines as pipeline_actions`，不是 `from ... import` | 自動 |
| TC-041 | 專長守則：對等性 TC | 功能 | 同上 | 測試同時列舉「五個新 MCP 工具名」與「它們對應的動作層函式」（`find_module`、`describe_module`、`list_pipelines`、`get_pipeline`、`get_validation`） | 兩邊一一對應；刻意少一邊時測試會失敗 | 自動 |
| TC-042 | 計畫「完成標準」 | 功能 | 讀 `specs/canvas-mcp-read/ledger.md` | 檢查 ledger | 有：改程式前的紅色輸出、`git diff --stat`（只含範圍內的檔）、`find_module("fastqc")` 的實際 MCP 回傳、OWED 沒變大的紀錄 | 手動：驗收者讀 ledger |
| TC-043 | 計畫「完成標準」；驗收規則「不准削弱既有測試」 | 功能 | 對照 base | 比較所有被動到的既有測試檔 | 除工具名單與計數（與 TC-031、TC-035 所述）外，沒有任何斷言被刪、放寬或略過 | 手動：驗收者以 `git diff` 對照 base |

## User Story 4 — 這次不做的事（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-044 | 計畫「不做」第 1 條 | 不在範圍 | 平台 MCP 伺服器建好 | 列出已登記工具名 | 沒有 `create_pipeline`、`update_pipeline`、`export_pipeline`、`validate_pipeline`、`launch_pipeline` | 自動 |
| TC-045 | 同上；專長守則：確認管道 | 不在範圍 | 同上 | 數非唯讀的工具 | 仍恰好是 launch、cancel、forget、resume、relaunch 五個，新增的五個工具沒有任何寫入工具 | 自動 |
| TC-046 | 計畫「不做」：不加網頁路由 | 不在範圍 | 讀網頁路由表（`WEB_ROUTES`） | 跑 `test_web_parity.py` | 路由表沒有新增與本片五個工具相關的路由，測試全綠 | 自動：`test_web_parity.py` |
| TC-047 | 計畫「不做」：不改 PLATFORM.md | 不在範圍 | 對照 base | 看 `docs/PLATFORM.md`、`web.py`、`web_board.py`、`static/` 的差異 | 全無差異（「nine read-only tools」字樣仍在） | 手動：驗收者以 `git diff --stat` 對照 base |
| TC-048 | 計畫「範圍：不准碰」 | 不在範圍 | 對照 base | 看 `git diff --stat` | 只含範圍內的檔：`mcp_server.py`、`actions/catalogue.py`（新）、`actions/chat_tools.py`（只一行）、新測試檔、釘住名單的既有測試；沒有 `actions/pipelines.py`、`catalogue.py`（頂層）、`compute_envs` 相關、`deploy/`、`dev-queue.json`、`actions/__init__.py` | 手動：驗收者以 `git diff --stat` 對照 base |
| TC-049 | 計畫「環境事實」：不准改 | 不在範圍 | 對照 base | 看差異 | `spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` 都沒被改 | 手動：驗收者以 `git diff --stat` 對照 base |
| TC-050 | 13-5；專長守則：migration | 不在範圍 | 對照 base | 看差異 | 沒有新增 migration，也沒有資料表或資料內容的變動 | 手動：驗收者以 `git diff` 對照 base |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-051 | 安全網：寫入工具（launch、cancel、resume、relaunch、forget）須經人確認，後加的寫入工具要帶自己的拒絕測試 | 功能 | 全套測試 | 跑既有五個寫入工具的拒絕／確認測試 | 全綠，且沒有新增未經確認即可寫入的路徑 | 自動：`tests/run_all.sh`（既有測試） |
| TC-052 | 安全網：密鑰、token 不得出現在回應；專長守則：日誌與回應不含密鑰 | 例外 | 甲、乙用各自的 token 呼叫五個工具（含找不到的情況） | 檢查每個回應文字 | 沒有任何 token、密碼字串 | 自動 |

<!--
Rules for the writer:
- IDs are never renumbered after approval.
-->
