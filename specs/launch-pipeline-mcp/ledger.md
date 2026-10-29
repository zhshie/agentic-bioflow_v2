# 開一個只會「提出」的 MCP 工具 launch_pipeline，送出自訂 pipeline 仍由本人按確認 progress ledger

- [x] RED 6b063502：新檔 `platform/tests/test_mcp_launch_pipeline.py`，改程式前 17 failed / 4 passed（工具不存在、REQUEST_TOOLS 缺、提示缺）。
- [x] GREEN：`mcp_server.py` 加 `launch_pipeline`（`_WRITES`，只傳 `caller=_caller(ctx)` 給 `actions.request_pipeline_launch`；docstring 改 six）；`chat_tools.py` 的 `REQUEST_TOOLS` 與提示各加一處（無禁字）。新測試 21 passed。
- [x] 釘住名單的既有測試只改名單與計數（test_mcp_server_doc、test_chat_tools、test_actions_layer、test_owner_guard、test_mcp、test_oauth_mcp、test_guidance、test_human_channel、test_keep_submissions、test_pat、test_su_in_get_run、test_aws/azure/gcb_launch、test_dataset_launch、test_launch_e2e、test_launch_platform、test_resume_*）。
- [x] test_owner_guard：`TOOL_ACTION` 加 launch_pipeline→request_pipeline_launch，移除 NO_TOOL 的 `request_pipeline_launch`（現在 MCP 也有出口）。test_actions_layer 的 tca02 對應表加同一個對應。
- 注意（偏離計畫清單）：`test_pipeline_launch.py::test_no_new_public_name_in_the_tool_or_web_layers`（TC-161，註解「外層名稱留給 017e」）禁止 mcp_server.py 出現 `launch_pipeline`／`pipeline_launch`，與本片必然衝突。只改了 mcp_server.py 那一格：檢查前先去掉 `request_pipeline_launch` 與 `launch_pipeline` 兩個字串，web.py、web_board.py 與 handlers.py 的檢查原樣。請驗收者確認。
- 資料庫前後比對：`test_asks_only_and_matches_launch_shape` 呼叫前後 `launches` 列數不變、`launch_nextflow` job 為 0、只多一張 pending confirmation。
- `git diff --stat e428661b HEAD`：只含 mcp_server.py、chat_tools.py、新測試檔與上列既有測試檔；無 web.py、web_board.py、static、confirm.py、actions/__init__.py、migration。
