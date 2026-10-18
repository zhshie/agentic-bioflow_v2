# estimate-su progress ledger

- [x] configs/sites/su_rates.json (money rates from POSITIONING.md line 82; all seven nchc queues, every factor null)
- [x] platform/abf_platform/su.py: su_of_tasks, month_total (computed on read, nothing stored), run_tasks (always unknown for now)
- [x] actions.estimate_su (owner-only like get_run; returns su, twd_nstc, twd_academic, unknown_reasons)
- [x] platform/tests/test_estimate_su.py

## 欠 (owed)

- 各分區 SU 係數 repo 內查不到（nchc.config、SITE_ADAPTER.md、LAB_AGENTS.md、PITFALLS.md 都沒有記錄）。欠：維護者或 lab-agent 向國網取得後填入 configs/sites/su_rates.json；在那之前每個分區的係數都是 null，SU 顯示未知（—）。
- receiver／索引沒有保存每個 task 的 cpus、realtime、分區（store.py 只存計數與失敗 task），所以 estimate_su 對真實 run 回未知；未改 receiver。欠：receiver 開始保存 trace 後，改 su.run_tasks 讀它。
- MCP 工具（estimate_su 的工具）：欠，隨 012d 完成。
- 網頁顯示：欠，隨同位對照（parity）工作完成。
- 雲端費用：不算，Stage 4 前顯示「—」。
