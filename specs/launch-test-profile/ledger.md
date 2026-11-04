# 送出可選 Config profiles（test 免樣本表） progress ledger

- [x] 站台 station：`brings_input`、`_check_profiles`、`render_bundle(profiles=)`、resume／relaunch 重建、雲端拒絕 profiles、預檢 `site_profiles`（abf_station/launch.py、handlers.py）
- [x] 平台：jobs.py 清理並保存 `site_profiles`；`request_launch` 驗證名單、查無紀錄時拒絕並請先跑預檢；`mcp_server.py` 的 `profiles` 參數
- [x] build.py／confirm.py：確認畫面 `Config profiles: …`、`Samplesheet: from the pipeline's test profile`；樣本表為 None 時不出錯
- [x] 測試：`test_launch_profiles.py` 85 通過；TC-060 加在 `test_http_site_samplesheet.py`
- [x] `docs/TESTING.md` 新增「nano4 test profile 驗收」節（TC-011／TC-012，手動）
- [ ] 手動驗收 (a)(b)：待操作員在 nano4 重跑預檢並對八個 pipeline 各跑一次 test run，結果記在這裡
- [x] 修正輪：補 TC-068／069／072／073／074／076／077／078 的測試於 `test_launch_profiles.py`（93 通過）；TC-006 的 or 斷言收緊
- [x] 修正輪 2：核可頁摘要對無樣本表的 test 送出不再顯示「樣本數 0」，confirm.py facts 的 samples 為 None 即不列，profiles 進 facts（web.py 不動：TC-069）；新增 TC-024 摘要測試（94 通過）。修正輪 4：撤回 3537c119 對 plan.md／test-case.md 的修改與 web.py 的 3 行，回到原合約
- [x] 修正輪 3：補 TC-051 至 TC-054 經 MCP launch 的測試（test_non_site_module_and_other_platforms_refuse_profiles，四種雲端），檢查「未送出：」、profiles 不支援句、無寫入；拿掉拒絕程式碼時此測試變紅（98 通過）
- [x] 修正輪 5（11-04 裁決）：合併 origin/v3（22 個工具）、jobs.py 保留最新 done 預檢、web.py 確認頁 2 行 Config profiles 標籤、test_tc059/tc070/tc024 更新。test_mcp_launch_pipeline.py::test_no_schema_change 對固定舊 commit e428661b 比 store.py，v3 本身已不同，環境既有紅
- 全套 @HEAD：142/144；platform_shard_7 紅於 test_mcp_launch_pipeline.py::test_no_schema_change（對固定舊 commit e428661b 比 store.py，origin/v3 本身即不同，與本片無關）與一次性的 test_azure_ce（單跑 61 通過）；platform_shard_2 逾時未重試。需 developer-agent 裁示或修 v3 該測試。
- 裁決 C 第 2 項：已合併 origin/v3 (94830d2b)，test_mcp_launch_pipeline.py::test_no_schema_change 仍紅。store.py 與 origin/v3 無差異；v3 自 e428661b 起把 job 種類加了 read_run_file（九種變十種，store.py 的 CHECK、_jobs_kinds_current 與註解），測試仍對舊 commit 比。依裁決寫 BLOCKED。其餘 test_launch_profiles.py 與 test_mcp_launch_pipeline.py 共 121 通過。
- [x] 修正輪 6（11-05）：還原 web.py 兩行 profiles 標籤（維護者未核可例外，合約 TC-069 要求 web.py 不動）；test_tc024 摘要測試不再斷言 plain 區塊有 Config profiles 列（完整內容仍有）；test_tc069 加 git diff 檢查 web.py／web_board.py／static 與基準無差異。待維護者決定：若要摘要列出 profile 名，須先改合約再加 2 行。手動驗收 TC-011／TC-012 仍未做。
