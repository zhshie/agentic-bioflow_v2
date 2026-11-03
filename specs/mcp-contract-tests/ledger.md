# MCP 契約測試（工具清單快照、描述檢查、寫入零副作用） progress ledger

- [x] TC-001..008, 019, 020 tool list snapshot and description lint (test_mcp_contract_tools.py, snapshots/tools.json)
- [x] TC-009..011 write tools: zero side effect, reply says not sent (test_mcp_contract_writes.py)
- [x] TC-012..015 error path per tool: 15 product gaps marked xfail(strict) in GAPS (cancel, get_compute_env, get_pipeline, get_validation, get_run, launch, list_site_files, read_task_log, relaunch, resume: no next step; find_module, forget, my_usage, read_run_file, run_outputs: no name). abf_platform/ untouched.
- [x] TC-016..018 HTTP: test_mcp_contract_http.py. list_site_files over HTTP with the site's agent offline answers ok false "offline" at once (not 60 s wait).
