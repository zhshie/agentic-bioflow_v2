# 測試案例：mcp_server.py 檔頭工具清單與數量對齊程式

<!--
Written by the verifier (CONTRACT mode). 來源：計畫 specs/mcp-server-doc-tool-list/plan.md（A 級，無 spec.md；維護者原話只有本次派工指示）。
本檔只用計畫寫明的事實與檢查，沒有新增計畫沒說的行為。
-->

**規格**：`specs/mcp-server-doc-tool-list/plan.md`（本件無 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應（這裡是「之後有人加工具卻忘了改說明，測試要變紅」）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「說明」＝ `platform/abf_platform/mcp_server.py` 最前面的兩處文字——第 1 行的 `#` 註解，和緊接著的 `"""…"""` 模組說明字串。「唯讀工具」＝以 `annotations=_READ_ONLY` 註冊的工具（現在十個）；「問人工具」＝寫入類、只會發出請求等人按同意的工具（現在五個：launch、cancel、forget、resume、relaunch）。

驗證方式「手動」的意思：閱卷者照該列寫的指令自己重跑並看輸出。計畫禁止改 `docs/`，所以這些步驟不寫進 `docs/TESTING.md`，指令就寫在該列。

新測試檔指 `platform/tests/test_mcp_server_doc.py`；單檔跑法（在 `platform/` 底下）：`ABF_PYTEST_TARGETS=tests/test_mcp_server_doc.py bash tests/platform_test.sh`。

## User Story 1 — 說明和程式實際註冊的工具一致，且之後會自動提醒（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；測試一 `test_module_doc_names_every_registered_tool` | 功能 | 改字完成；新測試檔存在 | 測試用 `ast` 讀 mcp_server.py，取所有 `@server.tool(name="…")` 的名字（含 `_add_write_tools` 裡的），共 15 個；對每一個檢查模組說明字串是否含該名字 | 15 個名字全部出現在模組說明字串裡，沒有缺的 | 自動：`tests/test_mcp_server_doc.py::test_module_doc_names_every_registered_tool` |
| TC-002 | 目標（`forget` 沒列）；測試一 | 功能 | 同 TC-001 | 檢查模組說明字串 | 含 `forget`，且它被列在「問人」的工具裡，不是列在唯讀工具裡 | 自動：同 TC-001（含 `forget` 部分）；分組見 TC-008 |
| TC-003 | 目標（漏列三個）；測試一 | 功能 | 同 TC-001 | 檢查模組說明字串 | 同時含 `list_used_pipelines`、`my_usage`、`run_outputs` 三個名字 | 自動：同 TC-001 |
| TC-004 | 目標（第 2 行「七個」）；測試二 `test_module_doc_counts_the_read_only_tools` | 功能 | 改字完成 | 測試從同一棵 AST 數出 `annotations=_READ_ONLY` 的工具數 N（應為 10）；用正則 `\b(six|seven|eight|nine|ten|eleven|twelve)\b read` 在模組說明字串裡找數字詞 | 至少找到一處；找到的**每一處**轉成整數都等於 N（10）；找不到或有任何一處不等於 10 就失敗 | 自動：`tests/test_mcp_server_doc.py::test_module_doc_counts_the_read_only_tools` |
| TC-005 | 過期說明三（第 5 行「The seven read tools」） | 功能 | 改字完成 | 讀模組說明字串中 `carry readOnlyHint` 那句 | 那句的數字寫成十（ten），不再是 seven；與 TC-004 的「每一處都等於 N」一致 | 自動：同 TC-004（閱卷者另確認測試迭代全部命中而不是只看第一個） |
| TC-006 | 過期說明一（第 1 行「six」）；測試三 `test_first_comment_line_does_not_name_an_old_count` | 功能 | 改字完成 | 測試讀 mcp_server.py 第 1 行 | 第 1 行不含 `six`，也不含 `seven` | 自動：`tests/test_mcp_server_doc.py::test_first_comment_line_does_not_name_an_old_count` |
| TC-007 | 決定（第 1 行前綴與語意不變） | 功能 | 改字完成 | `git diff -U0 origin/v3 -- platform/abf_platform/mcp_server.py`，看第 1 行 | 第 1 行仍以 `# Not the Seqera MCP server:` 開頭，語意仍是「這個伺服器讀本機索引與 compute environment，不是 Seqera 託管的那個」；若第 1 行提到唯讀工具個數，只能是十或不寫數字 | 手動：上列 git diff 指令 |
| TC-008 | 決定（第 2–3 行逐一列名） | 功能 | 改字完成 | 讀 diff 中第 2–3 行起的模組說明 | 十個唯讀工具（list_runs、get_run、list_compute_envs、get_compute_env、list_agents、list_site_files、list_used_pipelines、my_usage、run_outputs、read_task_log）與五個問人工具（launch、cancel、forget、resume、relaunch）逐一列名，且兩組分開寫；沒有把問人工具寫成唯讀，也沒有把唯讀寫成問人 | 手動：`git diff -U0 origin/v3 -- platform/abf_platform/mcp_server.py` |
| TC-009 | 對照（第 7–10 行不動） | 功能 | 改字完成 | 讀 diff | 原第 7–10 行（對 `list_site_files`、`read_task_log` 的描述）逐字沒變；第 12–18 行對 launch／cancel／resume／relaunch 的敘述沒有被刪或改弱 | 手動：同 TC-008 的 diff 指令 |
| TC-010 | 失敗先行 | 功能 | 新測試檔已寫、mcp_server.py 尚未改字 | 先跑一次新測試檔 | 測試一、二、三都是紅的：測試一缺 `list_used_pipelines`、`my_usage`、`run_outputs`、`forget`；測試二寫的是 seven；測試三第 1 行含 six；紅的輸出貼在 ledger；改字後三則轉綠 | 手動：閱卷者讀 `specs/mcp-server-doc-tool-list/ledger.md` 的紅色輸出，並在改字後的 HEAD 重跑新測試檔得綠 |
| TC-011 | 目標（之後加工具忘了改說明就會紅） | 例外 | 新測試檔存在 | 閱卷者讀測試一與測試二的寫法 | 名字清單與唯讀數量都是從 AST 即時取得、不是寫死在測試裡；因此多註冊一個沒列進說明的工具，測試一會紅；多註冊一個唯讀工具而數字沒改，測試二會紅 | 自動：同 TC-001、TC-004（閱卷者讀測試碼確認其來源是 AST） |
| TC-012 | 對照組（必須一直綠） | 功能 | 新測試檔存在 | 測試把已註冊工具名字集合與寫死在測試裡的 15 個名字比對，並確認唯讀數 N 為 10 | 兩者相等（15 個名字：list_runs、get_run、list_compute_envs、get_compute_env、list_agents、list_site_files、list_used_pipelines、my_usage、run_outputs、read_task_log、launch、cancel、forget、resume、relaunch），改字前後都是綠 | 自動：`tests/test_mcp_server_doc.py` 內的對照組測試 |
| TC-013 | 作法（測試只讀文字、不需裝 mcp） | 功能 | 新測試檔存在 | 閱卷者讀新測試檔的 import 與內容 | 只用 `ast`、`re`、`pathlib` 這類標準庫讀 mcp_server.py 的原始碼文字；沒有 import `mcp`／`abf_platform`、沒有網路、沒有開資料庫 | 手動：`grep -nE "^\s*(import|from) " platform/tests/test_mcp_server_doc.py` 並讀檔 |

## User Story 2 — 只改說明，不改任何執行行為（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 決定（只改 `#` 註解行與 `"""` 內）；完成標準 | 功能 | 實作完成 | `git diff -U0 origin/v3 -- platform/abf_platform/mcp_server.py`，逐行看每個增刪行 | 每一個變更行不是以 `#` 開頭，就是位於檔頭模組 `"""…"""` 之內；沒有任何其他變更行 | 手動：上列指令 |
| TC-021 | 作法最後一項；完成標準 | 功能 | 實作完成 | 對 base 與 HEAD 的 mcp_server.py 各 `ast.parse`，各自去掉模組說明字串後比對 | 兩棵 AST 相等（註解不在 AST 內；說明字串已去掉）；輸出貼在 ledger，閱卷者自己重跑一次 | 手動：以 `git show origin/v3:platform/abf_platform/mcp_server.py` 與工作樹檔案各跑 `ast.dump` 比對 |
| TC-022 | 範圍：檔案；完成標準 | 功能 | 實作完成 | `git diff --stat origin/v3...HEAD` | 除了 `specs/mcp-server-doc-tool-list/` 底下的計畫與 ledger 文件外，只有兩個檔：`platform/abf_platform/mcp_server.py`、`platform/tests/test_mcp_server_doc.py`（新檔） | 手動：上列指令 |
| TC-023 | 範圍：新檔頭要求 | 功能 | 新測試檔存在 | 讀新測試檔前 40 行；跑 `platform/tests/test_scope.py` | 前 40 行內有 `# Nothing existing:` 開頭的一行，說明至少 15 個字；`test_scope.py` 的 TC-070（每個原始檔都要說明為何不用現成的）為綠；mcp_server.py 自己的 `# Not the Seqera MCP server:` 那行也仍被接受 | 自動：`tests/test_scope.py::test_tc070_every_python_source_names_its_alternative` |
| TC-024 | 範圍：不准碰任何既有測試的既有斷言 | 功能 | 實作完成 | `git diff --stat origin/v3...HEAD -- platform/tests tests` | 唯一的變更是新增 `test_mcp_server_doc.py`；`test_mcp.py`、`test_pat.py`、`test_oauth_mcp.py` 等既有測試檔零變更（沒有刪、放寬、跳過或改期望值） | 手動：上列指令 |
| TC-025 | 決定（新增文字不得撞禁字）；環境事實 | 功能 | 實作完成 | 跑會掃描 mcp_server.py 整檔文字的既有檢查：`test_scope.py`（TC-051、TC-061 禁字，含 `station`）、`test_launch_platform.py`（tc067：不得出現 `launches`、`confirm`）、`test_catalogue.py`（不得出現 `catalogue`）、`test_human_channel.py`（不得出現大寫 `PAGE`／`ELICITED`／`TERMINAL`）、`test_cleanup_confirm.py`（tc067：不得出現 `clean_work`）、`test_gcb_ce.py`（不得出現 `gcp`／`google`）、`test_guidance.py`（tc409）、`test_dataset_launch.py`、`test_datasets.py`、`test_cloud_upload_docs.py`，以及 `bash tests/constitution_6_test.sh` | 全部維持綠，沒有因為新增的說明文字而變紅 | 自動：上列既有測試檔（閱卷者逐一跑這幾個檔，不必重跑全套） |
| TC-026 | 完成標準（整個套件全綠）；對照組 | 功能 | 實作完成 | 讀 `executor-status` 完成記號；閱卷者另跑與工具數量有關的既有測試 | 完成記號為 `GREEN <HEAD sha>` 且工作樹乾淨；既有測試仍是綠且斷言未改：`test_pat.py:383` 的 `len(tools) == 15`、`test_oauth_mcp.py:44` 的 `len(tools) == 15`、`test_mcp.py` 的 15 個名字清單與只有五個問人工具的 `read_only_hint` 檢查（已知環境紅依 dev-plans README 只算一條例外） | 自動：`tests/test_pat.py`、`tests/test_oauth_mcp.py`、`tests/test_mcp.py` |

## User Story 3 — 不在範圍（計畫「不做」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 不做：不改 `guidance.py:16` 的 `FIXED_SENTENCE`（裁決 2） | 不在範圍 | 實作完成 | `git diff origin/v3...HEAD -- platform/abf_platform/guidance.py`；並跑 `tests/test_guidance.py` | `guidance.py` 零變更；`FIXED_SENTENCE` 仍是「Seven tools of this server are read-only. …」（落後的數字刻意留給另一件）；`test_guidance.py` 為綠 | 手動：上列 git diff（應為空）；並跑 `tests/test_guidance.py` |
| TC-031 | 不做：不改工具名稱、`description=`、`annotations` | 不在範圍 | 實作完成 | 比對 base 與 HEAD 的 mcp_server.py 中每個 `@server.tool(...)` 的 `name`、`description`、`annotations` | 15 個工具的名稱、描述字串（使用者與模型看得到的文字）、唯讀／寫入／停止標記，逐字與 base 相同 | 手動：在 TC-021 的 AST 比對之外，閱卷者再對 `description=` 做逐字 diff |
| TC-032 | 範圍：不准碰 `actions/`、`web*.py`、`jobs.py`、`store.py`、`docs/` | 不在範圍 | 實作完成 | `git diff --name-only origin/v3...HEAD` | 清單裡沒有 `platform/abf_platform/actions/`、任何 `web*.py`、`jobs.py`、`store.py`、`docs/` 底下的檔 | 手動：上列指令 |
| TC-033 | 不做：不需要 migration | 不在範圍 | 實作完成 | 同 TC-032 的清單，並看有沒有資料表結構或 migration 相關檔 | 沒有任何 migration 或資料結構變動（`store.py`、`jobs.py` 皆未動），計畫已寫明「不需要 migration」 | 手動：同 TC-032 的 git diff 指令 |
| TC-034 | 環境事實：不准改的檔 | 不在範圍 | 實作完成 | `git diff --name-only origin/v3...HEAD` 對照禁改清單 | `spec.md`、任何 `test-case*.md`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` 都沒有在實作期間被改（`specs/mcp-server-doc-tool-list/` 下 `test-case*.md` 是出題者在實作前寫入的版本，之後不得再變） | 手動：上列指令 |

## 憲法與安全網

本件只動註解與說明，執行行為不變；以下逐條證明被碰到的規則與專長守則（backend）仍成立。

| 編號 | 憲法條目／專長守則 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | Safety Net：每個寫入工具（今日 launch、cancel、resume、relaunch、forget）未經人同意不得動作（constitution.md:188） | 功能 | 實作完成 | 跑 `bash tests/constitution_6_test.sh` 與 `tests/test_mcp.py` | constitution_6 的 TC-045（憲法列出的寫入工具＝ mcp_server.py 註冊的寫入工具）為綠；五個問人工具的 `read_only_hint` 仍是 False，其餘十個仍是 True；說明文字沒有製造出多餘的 `server.tool(name="…", annotations=_WRITES` 樣式字串 | 自動：`tests/constitution_6_test.sh`、`platform/tests/test_mcp.py` |
| TC-041 | 原則 I.1：每個原始檔在檔頭寫明「為何不用現成的」（constitution.md:22） | 功能 | 實作完成 | 跑 `test_scope.py` 的 TC-070 | mcp_server.py 的 `# Not the Seqera MCP server: …` 與新測試檔的 `# Nothing existing: …` 都通過 | 自動：`tests/test_scope.py::test_tc070_every_python_source_names_its_alternative` |
| TC-042 | 專長守則・對等性：使用者可見的動作清單與動作層函式一一對應 | 功能 | 實作完成 | 跑 `tests/test_actions_layer.py`（含「每個工具本體只呼叫一次動作層」） | 為綠；工具清單與動作層函式兩邊都沒有變動（已由 TC-012、TC-021 釘住） | 自動：`tests/test_actions_layer.py` |
| TC-043 | 專長守則・跨使用者：他人的紀錄讀與寫都被拒 | 功能 | 實作完成 | 跑 `tests/test_owner_guard.py`、`tests/test_owner_binding.py` | 為綠；因為沒有任何執行行改動（TC-020、TC-021），這項規則的行為與 base 相同 | 自動：上列既有測試 |
| TC-044 | 專長守則・確認管道：寫入動作未經確認不得改變資料 | 功能 | 實作完成 | 跑 `tests/test_human_channel.py`、`tests/test_keep_submissions.py`、`tests/test_resume_entrypoints.py` | 為綠；行為與 base 相同 | 自動：上列既有測試 |
| TC-045 | 專長守則・錯誤訊息與日誌：不露出密鑰 | 功能 | 實作完成 | 跑 `tests/test_secrets.py`；讀 diff 中新增的文字 | `test_secrets.py` 為綠；新增文字只含工具名稱與數字詞，不含 token、密碼、路徑或 SQL | 自動：`tests/test_secrets.py`；新增文字部分為手動讀 diff |
