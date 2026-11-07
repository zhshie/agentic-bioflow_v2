# 網頁任務日誌（失敗任務） progress ledger

- [x] RED 測試 test_web_run_log.py（TC-001..049）
- [x] actions.task_log_view、jobs.latest_task_log、GET /run/log、web_board 日誌分頁／任務列連結／render_log_page
- [x] 既有斷言：running 表頭／第一列（加日誌欄）、logs 分頁不再 soon、路由清單加 /run/log、parity WEB_ONLY 加 task_log_view
- [x] docs/TESTING.md 手動步驟
- [ ] 四張截圖與 axe（ui_check.py）未跑，留給 PR 階段

## Fix round 2 (2026-11-07)
- TC-036: screenshots redone with a seeded failed run (24 pages: board tasks/logs, results logs, /run/log loading/ready/error; 1440/390 x zh/en). ready and error pages axe-clean. Only critical left is meta-refresh (existing board tag; loading page tag is required by TC-011); left for the maintainer, see screenshots/summary.md.
- GATE: full suite rerun at the new HEAD, marker written after.

- Fix round 3 (2026-11-07): TC-010 gets its own test (test_tc010_failed_task_reason_is_readable_in_the_web_page): err link -> loading -> job done -> same link shows FASTQC and <pre>Error: out of memory</pre>. TC-036 meta-refresh vs TC-011 conflict NOT touched (needs maintainer: spec/TC choice). GATE: full suite rerun at the new HEAD.

## Fix round 4 (2026-11-07): ruling on TC-036 vs TC-011 (plan 裁決 second block)
- Waiting log page: `<meta http-equiv=refresh>` removed; it now shows a Refresh link (zh 重新整理 / en Refresh, same address, no retry) and the data time (資料時間 / Data as of, Taipei time of the page). web_board.py render_log_page, strings l_loading, l_reload, l_asof.
- TC-011 assertion changed (allowed by the ruling), old -> new:
  - old: waiting page contains `http-equiv="refresh"` and `content="15`; new: waiting page has the Refresh link and the data time and no `http-equiv` (helper `is_waiting` in test_web_run_log.py).
  - same swap in the other waiting-page checks: TC-010 scenario first page, TC-013/014, TC-022/023, TC-024 (they asserted the bare word "refresh"). The finished page still asserts no refresh tag. No other assertion touched.
- docs/TESTING.md step 3 of the manual case updated.
- Screenshots: all 24 retaken with seed_failed_demo.py; log pages axe-clean. Remaining axe critical `meta-refresh` is the board's old tag on board-tasks, board-logs, results-logs (pages that already had it; outside this task by the ruling). Every board page built by `render_board` has it; also `document(..., refresh=True)` pages of other features (results outputs loading, /run/file loading, launch loading, waiting-for-run page).
- GATE: full suite at the new HEAD, marker written after.
