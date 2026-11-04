# 送出可選 Config profiles（test 免樣本表） progress ledger

- [x] 站台 station：`brings_input`、`_check_profiles`、`render_bundle(profiles=)`、resume／relaunch 重建、雲端拒絕 profiles、預檢 `site_profiles`（abf_station/launch.py、handlers.py）
- [x] 平台：jobs.py 清理並保存 `site_profiles`；`request_launch` 驗證名單、查無紀錄時拒絕並請先跑預檢；`mcp_server.py` 的 `profiles` 參數
- [x] build.py／confirm.py：確認畫面 `Config profiles: …`、`Samplesheet: from the pipeline's test profile`；樣本表為 None 時不出錯
- [x] 測試：`test_launch_profiles.py` 85 通過；TC-060 加在 `test_http_site_samplesheet.py`
- [x] `docs/TESTING.md` 新增「nano4 test profile 驗收」節（TC-011／TC-012，手動）
- [ ] 手動驗收 (a)(b)：待操作員在 nano4 重跑預檢並對八個 pipeline 各跑一次 test run，結果記在這裡
- [x] 修正輪：補 TC-068／069／072／073／074／076／077／078 的測試於 `test_launch_profiles.py`（93 通過）；TC-006 的 or 斷言收緊
