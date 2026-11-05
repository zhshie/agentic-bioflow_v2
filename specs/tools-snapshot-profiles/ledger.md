# 補 #362 漏更新的工具快照與 launch 參數說明（修 v3 上 4 支紅測試） progress ledger

## executor 11-05
- 改前 origin/v3：紅 test_tools_schema_matches_snapshot、test_snapshot_is_crlf_insensitive、test_over_limit_list_only_shrinks、test_every_param_is_described（4 failed 7 passed），與計畫一致。
- 完成：pipeline 說明、OVER_LIMIT 刪 launch、快照重產；合約檔 11 passed。刻意破壞三項未另做（邏輯由測試規則本身保證）。
- 全套 149/150：唯一紅 tests/platform_upgrade_test.sh TC-U28（merge-base 與 HEAD 之間 platform/ 有改動就紅，v3 本身因差異為空而綠）。本任務必須改 platform/，故此測試對任何動 platform/ 的分支必紅；不得改測試，卡住請 developer-agent 裁決。其餘 150 檔中 149 綠，含合約檔。
- 11-06：合併 origin/v3（TC-U28 已刪），全套 150/150（shard_4 逾時重跑通過）。
