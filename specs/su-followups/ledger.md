# SU 費率檔打包進平台自己的 data/；補強 estimate-su-mcp 的四條鬆測試（取代作廢的 fix/su-followups） progress ledger

- [x] 費率檔進 wheel：`platform/setup.py` 建置時把 `configs/sites/su_rates.json` 複製到 `abf_platform/data/su_rates.json`（缺檔建置失敗）；`.gitignore` 忽略該複本；`su.py` 的 `RATES_PATH` 載入時先指 `data/` 那份，沒有才指 repo 路徑。`su.py` 沒有出現 station 字樣。測試：`platform/tests/test_su_packaged.py`（先紅：wheel 內沒有 `data/su_rates.json`；後綠）。
- [x] 四條鬆測試補強（`platform/tests/test_su_in_get_run.py`）。每條都先把被測那段弄壞、看到它變紅、還原後轉綠：
  - TC-014（對應 su-followups TC-020、021）：改成真的 `call_tool("get_run")`。弄壞：`mcp_server.get_run` 把 `su` 鍵拿掉 -> `test_mcp_get_run_is_the_same_action` 紅（`KeyError: 'su'`）。
  - TC-083（TC-022 至 027）：五種 unknown 原因都過 `_no_leaks`。弄壞：費率檔讀不到那句帶出 `RATES_PATH` -> `test_unreadable_rates_file_gives_null_site` 紅（斷言列出路徑 `/tmp/.../missing.json`）；`NOT_STORED` 前面加 `SELECT * FROM task_usage` -> `test_get_run_su_is_null_with_reason_for_an_old_run` 紅（該條原有的 startswith 斷言先攔到，`_no_leaks` 同樣會抓）。另有 `test_the_leak_check_can_go_red` 證明檢查函式本身會抓路徑、SQL、Traceback、token。
  - TC-073（TC-028、029）：改成走 `rebuild.rebuild` 重建再問 `get_run`，整句 NOT_STORED 逐字寫在測試裡。弄壞：`run_su` 在沒有 task 時回「有 N 個成功的 task 沒有用量紀錄」那句 -> `test_a_run_without_usage_rows_stays_unknown` 紅（清單內容不等）。
  - TC-048（TC-030、031）：改成經 `actions.estimate_su`（platform.db 不存在／是亂碼）。弄壞：`estimate_su` 不呼叫 `site_of_run`、直接寫死 `nano4` -> `test_estimate_su_without_a_readable_platform_db_judges_the_default_site` 紅（`su` 是 None，期望 8）。
