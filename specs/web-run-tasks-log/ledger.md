# 網頁任務日誌（失敗任務） progress ledger

- [x] RED 測試 test_web_run_log.py（TC-001..049）
- [x] actions.task_log_view、jobs.latest_task_log、GET /run/log、web_board 日誌分頁／任務列連結／render_log_page
- [x] 既有斷言：running 表頭／第一列（加日誌欄）、logs 分頁不再 soon、路由清單加 /run/log、parity WEB_ONLY 加 task_log_view
- [x] docs/TESTING.md 手動步驟
- [ ] 四張截圖與 axe（ui_check.py）未跑，留給 PR 階段

## Fix round 2 (2026-11-07)
- TC-036: screenshots redone with a seeded failed run (24 pages: board tasks/logs, results logs, /run/log loading/ready/error; 1440/390 x zh/en). ready and error pages axe-clean. Only critical left is meta-refresh (existing board tag; loading page tag is required by TC-011); left for the maintainer, see screenshots/summary.md.
- GATE: full suite rerun at the new HEAD, marker written after.
