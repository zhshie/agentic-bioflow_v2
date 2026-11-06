# 管線登記紀錄表與狀態機（動作層） progress ledger

## 進度
- [x] registrations.py（表、狀態推導、四個動作）與 actions/__init__.py 薄包裝
- [x] test_pipeline_registrations.py；三個名單測試只加行；docs/TESTING.md 加 (a)(b) 兩步

## 新測試改前的紅輸出
RED commit（只有測試與名單，沒有實作）：`40 failed, 7 passed`，失敗原因皆為 `AttributeError: module 'abf_platform.actions' has no attribute 'propose_pipeline_registration'`（或 `list_pipeline_registrations` 等），名單測試因多了名稱而紅。

## 不需要 migration 的理由
新表 `pipeline_registrations` 在第一次寫入時以 `CREATE TABLE IF NOT EXISTS` 建立（讀取從不建表，缺表時視為空）；不改任何既有表、不進 `store.STATE_SCHEMA`；舊的 `sitePipelines` 以讀時合併呈現（`legacy=True`、`awaiting_test`），不搬資料。

## 未確認前後表列數比對
`test_unconfirmed_propose_and_remove_change_nothing`：`confirmed_by=None` 或假字串時丟 `JobRefused`，`pipeline_registrations` 列數前後相同；`test_legacy_site_pipelines_show_as_awaiting_test` 與 `test_table_is_created_on_first_use...` 確認讀取不寫表。

## 修正回合（驗證者回報後）
- TC-069 測試改用甲、乙真實 token 值（與其雜湊）比對所有回應，並檢查無 SQL 字句、檔案路徑、Traceback。
- TC-065 測試改為逐列比對三張組合管線表的建表語句、欄位與資料在登記動作前後完全相同。
- `docs/TESTING.md` 步驟 (a) 的檔案清單補上 `platform/tests/test_k8s_launch.py`（裁決 R 第 2 點認可的一行）。受保護的 TC-029 合約文字未改，這個例外交維護者決定是否補進合約。

## 其他
- 舊登記列的擁有者欄 `owner` 存環境擁有者的 user id（字串；終端機建的環境為空字串），因此終端機（caller=None）看得到全部。
