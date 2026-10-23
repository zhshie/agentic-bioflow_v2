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

## Rulings E1-E3 (2026-10-18)

- [x] E1 merged origin/v3 (plain merge, no conflicts; keep-submissions' `forget` tool is now in TC-029's expected tool list)
- [x] E2 month_total: month is Asia/Taipei (UTC+8) by run start; any unknown run makes the month unknown; no runs is 0 (TC-034..TC-040)
- [x] E3 rates stay 0.08 / 0.24 with source; factors stay null (owed above)

## nano4 factors (nano4-site-config, 2026-10-22)

- Site `nano4` has two partition keys, `ngs*` (factor 1) and `big-mem*` (factor 7); a trailing `*` means a prefix match. Money rates per SU: nstc 0.1, academic 0.2, industry 0.37, from the Chuangjin-1 price list https://iservice.nchc.org.tw/nchc_service/nchc_service_qa.php?target=54 (NSTC 0.1, academic/government 0.2, enterprise 0.37).
- The factor 7 of `big-mem*` is the GP1 big-memory price over the general price, 0.56 / 0.08 = 7 (lions.nchc.org.tw/ngs.jsp).

## Ruling E4 (2026-10-19)

- [x] E4 rates switched to the Taiwania 3 general (NRQ) rate (sources in su_rates.json): new site `taiwania3` with queues ctest, ct56, ct224, ct560, ct2k, ct8k factor 1; ct2k-amd stays null (price not found, owed). Site `nchc` (ngs queues of nchc.config) stays null. default_site is now taiwania3.
- Test changes: TC-023 old: academic 0.24 and source lions.nchc.org.tw/ngs.jsp; new: academic 0.08, industry 0.16, source iservice.nchc.org.tw; reason: ruling E4. TC-024 still holds (ct56 etc. are named in this ledger). Added: ct56 4 cpus x 2 h = 8 SU and 0.64 TWD (nstc); ct2k-amd unknown.
- Assumption (from NCHC lists, not stated by NCHC): 1 SU = 1 core-hour; verify with get_su_balance before/after a run.
- Real runs stay unknown: the receiver still stores no per-task cpus/realtime (unchanged).
