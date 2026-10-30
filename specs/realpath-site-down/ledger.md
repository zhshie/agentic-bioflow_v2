# 站台連線斷掉時，讀檔／列目錄／讀 log 回 site_unreachable＋重新登入句，不是路徑拒絕 progress ledger

## Executor 2026-10-30
- [x] 新測試 platform/tests/test_station_realpath_down.py（TC-001..013,016..019）；RED 先提交。
- [x] handlers._real_path_res／_realpath_down 新增，_real_path 包它；listing/readfile/readlog 斷線回 site_unreachable。
- [x] docs/PITFALLS.md 第 58 條（TC-015）。
- 既有 test_station_owner／test_owner_gaps／test_resume_platform 綠、未改動。
- 注意：WSL 裡 constitution_scope_test.sh 紅＝環境問題，以 CI 為準。
