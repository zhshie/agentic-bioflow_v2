# samplesheet 欄名以 _file／_path 結尾也要當路徑欄檢查 progress ledger

- [x] 測試 TC-001..009、018 加進 platform/tests/test_launch_bundle.py（RED 先紅，5 條失敗）
- [x] launch.py `path_cells`：`DEFAULT_PATH_COLUMN.match(h)` 改 `.search(h)`（GREEN）

## DEFAULT_PATH_COLUMN 使用處（git grep）
- platform/abf_station/launch.py:62 定義（regex 未改）
- platform/abf_station/launch.py:325 `path_cells`：match 改 search。其餘呼叫點無（其他 launch 路徑經 path_cells 共用）。
- docs/ 沒有逐字列出預設路徑欄名，未動。
