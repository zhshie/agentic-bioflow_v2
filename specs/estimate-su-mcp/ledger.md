# 接收器記下每個 task 的用量，get_run 帶出 SU 與台幣 progress ledger

- [x] store.py：task_usage 表（CREATE TABLE IF NOT EXISTS，不需 migration）
- [x] receiver.py：COMPLETED／FAILED 的 task 每個 attempt 寫一列
- [x] su.py：run_tasks 讀 task_usage、site_of_run、RUN_NOT_ENDED
- [x] compute_envs.py：suSite 驗證（snapshot 不動）；configs/sites/nchc-nano4-ce.json 加 suSite
- [x] actions：get_run 帶 su（沒結束、成功數對不上都不給數字）；estimate_su 用 site_of_run
- [x] mcp_server.py get_run 說明加一句；test_actions_layer BASELINE 同步（有意更新）
- [x] 文件：PLATFORM.md、TESTING.md TC-048n、acceptance-nano4.md、estimate-su/ledger.md 第 11、12 行
- [x] platform/tests/test_su_in_get_run.py（新）、test_station_envs.py（加 suSite 測試）
- [x] platform/tests/test_failures.py:193（2026-10-24 裁決核可的一行）。以前：`if k != "failure"`；以後：`if k not in ("failure", "su")`；理由：get_run 多出動作層補的 su 欄，與 failure 同類。
