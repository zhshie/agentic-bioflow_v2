# MCP 契約測試（工具清單快照、描述檢查、寫入零副作用） progress ledger

- [x] TC-001..008, 019, 020 tool list snapshot and description lint (test_mcp_contract_tools.py, snapshots/tools.json)
- [x] TC-009..011 write tools: zero side effect, reply says not sent (test_mcp_contract_writes.py)
- [x] TC-012..015 error path per tool: 15 product gaps marked xfail(strict) in GAPS (cancel, get_compute_env, get_pipeline, get_validation, get_run, launch, list_site_files, read_task_log, relaunch, resume: no next step; find_module, forget, my_usage, read_run_file, run_outputs: no name; 2026-11-14 mcp-list-figures adds a 16th, list_figures: its refusal is the shared "run not found" sentence, no name and no next step). abf_platform/ untouched.
- [x] TC-016..018 HTTP: test_mcp_contract_http.py. list_site_files over HTTP with the site's agent offline answers ok false "offline" at once (not 60 s wait).

## 給維護者的清單（測試找到的產品缺口；abf_platform/ 一行都沒改）

- 工具數：plan 寫 24，實際 server 只有 21（EXPECTED_TOOLS 用真實的 21 個）。
- 描述超過 600 字（OVER_LIMIT，凍結、只能縮）：get_run 683、launch 968、read_run_file 1016、resume 807、run_outputs 700。
- 描述缺面向（ASPECT_GAPS，凍結、只能縮，共 41 項 tool/aspect）：見 test_mcp_contract_tools.py 的 ASPECT_GAPS。關鍵字檢查很粗，缺項是「這段描述沒有這類字眼」。
- 參數沒說明（UNDESCRIBED_PARAMS，14 項）：find_module.q、forget.run_name、get_pipeline.pipeline_id、get_run.run_id、get_validation.pipeline_id、launch.{revision,run_name,ce_name,path_columns}、list_site_files.{compute_env,path}、read_run_file.run_id、read_task_log.run_name、run_outputs.run_id。
- 錯誤訊息缺口（GAPS，xfail strict，共 15 個工具，產品修好後標記要拿掉）：
  - 沒說下一步：cancel、get_pipeline、get_validation、get_compute_env、get_run、launch、list_site_files、read_task_log、relaunch、resume。
  - 沒點名失敗的東西：find_module（hint 不重複關鍵字）、forget、my_usage、read_run_file、run_outputs（後三者也沒說下一步）。
- 沒有必填參數的 5 個工具（list_runs、list_compute_envs、list_agents、list_used_pipelines、list_pipelines）找不到會失敗的輸入，只檢查回答乾淨；TC-014 對它們 skip（6 個 skip，含 1 個無必填的其他工具）。
- list_site_files 描述寫「never waits」，但站台代理在線時會等到 job 期限（約 60 秒）；HTTP 測試因此讓代理離線（last_seen_at=0）才秒回。

## 環境備註

- WSL 裡 tests/constitution_scope_test.sh 是紅的：環境問題（與本任務無關），不是這個分支造成的。

## 破壞性驗證（改產品碼 → 測試要紅 → 還原；還原後 git diff 只剩 platform/tests/mcp 與 specs）

| 破壞 | 抓到的測試 |
|---|---|
| list_agents 改名 list_agentz | test_tool_names_match_explicit_list、test_tools_schema_matches_snapshot、test_snapshot_is_crlf_insensitive、test_descriptions_cover_the_six_aspects |
| get_pipeline 多一個參數 extra | test_tools_schema_matches_snapshot、test_every_param_is_described |
| describe_module 描述加 1100 字 | test_descriptions_within_limit（以及 control-char 檢查） |
| launch 刪掉「does NOT start anything」與「cannot say it for them」 | test_descriptions_cover_the_six_aspects（只刪一句抓不到：when_not 的關鍵字檢查是任一字眼就過，這是已知的粗糙） |
| request_cancel 直接 enqueue_cancel | test_write_tool_called_once_has_no_side_effect[cancel] |
| run_outputs 的錯誤訊息帶 /home/... 路徑 | test_error_path_is_clean_for_every_tool[read_run_file]、[run_outputs] |
