# CLOUD.md 月上限說明改成符合「價目表為空」的現況，加釘住測試 progress ledger

- [x] 2 新測試加入；改文件前：doc 測試紅（第 43 行舊句缺「要等價目表填入後才會生效」），特徵化測試直接綠。
- [x] 改 docs/CLOUD.md 第 19、43、66 行與 docs/TESTING.md 第 621 行；test_cloud_cost.py 73 passed。
- [x] 突變：還原 CLOUD.md 後 doc 測試紅，還原回來綠。diff 只含 CLOUD.md、TESTING.md、test_cloud_cost.py（另加本 ledger）。
