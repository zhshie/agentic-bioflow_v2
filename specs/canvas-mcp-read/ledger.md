# 畫布後端的五個唯讀動作開給 MCP：找模組、看模組、列我的 pipeline、看某版、看驗證結果 progress ledger

## 進度（executor）
- [x] 新測試 `platform/tests/test_mcp_canvas_read.py`（TC-001…027、032、039–041、044–045、052）
- [x] `actions/catalogue.py`（新，薄包裝）、`mcp_server.py` 五個唯讀工具（`_add_canvas_reads`，`import ... as`）、docstring 與第 1 行數字改為 fifteen
- [x] `chat_tools.CHAT_SYSTEM_PROMPT` 加一行（13-1），`test_chat_tools.py` 加 TC-033/034 斷言
- [x] 釘住名單的既有測試只改名單／計數（見下「偏離」一條例外）

### 改程式前的紅色輸出（RED commit e44029d7）
`9 failed, 3 passed`：test_find_module_fastqc_shape (KeyError)、test_find_module_nothing、test_describe_module (KeyError: 'found')、test_wrappers_with_data (ImportError: actions.catalogue)、test_owner_reads (KeyError: 'pipelines')、test_other_user_sees_nothing、test_tools_equal_the_action_layer、test_registration (五個名字不在工具列)、test_import_style_and_not_exported。

### MCP 呼叫 `find_module("fastqc")` 的實際回傳（節錄）
`{"sha": "5ed90b42e78410e7411e9c6bdfeff33226d6c58e", "count": 3, "modules": [{"name": "fastqc", "path": "fastqc", "description": "Run FastQC on sequenced reads", "inputs": [{"channel": 0, "name": "meta", "type": "map", ...}, {"channel": 0, "name": "reads", "type": "file", ...}], "outputs": [{"channel": "html", "name": "*.html", "type": "file", ...}, ...]}, ...]}`

### OWED
四張 parity 表與 `test_web_parity.py` 一字未改；OWED 仍是原本五個，沒有變大。

### 偏離與需要驗收者注意
- `test_pipelines_store.py::test_the_files_owned_by_other_work_do_not_mention_pipelines`：該測試禁 `mcp_server.py` 出現 `actions.pipelines` 字樣，但計畫 13-3／TC-040 規定要 `import abf_platform.actions.pipelines as pipeline_actions`，兩者無法並存。只對 `mcp_server.py` 的 `actions.pipelines` 一個字改成「必須恰好只有那一行 import」，其餘字與其餘檔照舊。`mcp_server.py` 文字避開 `compose`（寫 saved pipelines）。
- `test_owner_guard.py`、`test_su_usd.py`、`test_actions_layer.py`、`test_pat.py`：新五個工具的動作在子模組（不在 `actions` 套件），故這些「工具↔套件動作」的配對斷言把五個名字單獨處理（名單與計數性質），未刪未放寬其他斷言。
- `test_pat.py` TC-D14 只掃 `build_server` 本體（仍是 10 個），因五個工具在 `_add_canvas_reads`，故該數字不動。
- `get_pipeline`／`get_validation` 的 `pipeline_id` 型別為 int（動作層 id 為整數）。
- 不需要 migration（13-5）。
- 全套第一輪還抓到三個釘名單的檔不在計畫清單內（`git grep '"my_usage"'` 沒列到）：`test_cleanup_offer.py`（名單加五個）、`test_su_in_get_run.py`、`test_aws_launch.py`、`test_gcb_launch.py`、`test_azure_launch.py`（計數 15→20，名單加五個）。
- `test_catalogue.py::test_no_tool_route_or_action_mentions_the_catalogue`（TC-070/071，017a 的「尚未開給 MCP」守門）：本片的目的就是開給 MCP，故只對 `mcp_server.py` 與 `actions/catalogue.py` 兩個檔略過；`web.py`、`web_board.py`、`actions/` 其餘檔照舊禁。這是放寬，驗收者請看。
