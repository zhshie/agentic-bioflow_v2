# 雲端檢查改嚴：s3 名稱拒 ..、AWS_ 前綴環境變數一律擋、測試失敗訊息補檔名 progress ledger

- [x] 項目 1：`cloud_store._container_ok` s3 分支加 `and ".." not in name`。RED 輸出：`test_parse_s3_refuses_a_double_dot_in_the_bucket`、`test_workdir_bucket_refuses_a_double_dot_in_an_s3_workdir` 皆 `DID NOT RAISE CloudPathError`；改後綠。
- [x] 項目 2：`launch.py` `_check_aws_ce` 的 `if` 加 `or name.upper().startswith("AWS_")`；tuple 未動。RED：`test_every_aws_prefixed_environment_name_is_refused` `DID NOT RAISE BundleError`；改後綠。
- [x] 項目 3：`test_azure_launch.py:1109` 把 `, f.name` 移到 `#` 之前（只動一行）。
- 差異檢查：cloud_store.py、launch.py 各一行邏輯改動；沒動 gs/az 分支、compute_envs、aws_preflight；不需要 migration；沒有新訊息文字。
- 項目 3 手動演練（TC-041，2026-10-29 補做）：複製 `test_azure_launch.py` 為不進 commit 的 `test_scratch_tc041.py`，只把 1109 行的正規式換成 `r"import"`（必命中），其餘不動。執行 `abf-fast-suite ... --pytest tests/test_scratch_tc041.py`，輸出：`E   AssertionError: __main__.py` / `E   assert not <re.Match object; span=(0, 6), match='import'>` / `tests/test_scratch_tc041.py:1109: AssertionError` / `FAILED tests/test_scratch_tc041.py::test_no_azure_command_that_changes_anything` / `1 failed, 69 passed`。失敗訊息帶檔名 `__main__.py`。副本演練後已刪除，工作樹乾淨。
