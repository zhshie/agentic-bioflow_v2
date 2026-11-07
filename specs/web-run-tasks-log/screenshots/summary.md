# TC-036 evidence: web-run-tasks-log

Made with `screenshots/seed_failed_demo.py` (throwaway platform of `scripts/dev/ui_check.py` + a FAILED run `ui-fail-run` with two failed tasks:
FASTQC with a recorded work folder, TRIM without; an online agent; the agent's answer for the log is injected with `jobs.take_result`).
Playwright + axe-core, 1440 and 390 wide, zh and en: 6 pages x 4 = 24 screenshots (`<page>-<width>-<lang>.png`). HTTP 200 on all 24.

| page | what it shows | axe (all 4 width/lang combos) |
|---|---|---|
| board-tasks | Tasks tab, failed rows: FASTQC has the "Errors" log link, TRIM has grey "No work directory on record" | moderate landmark-unique, critical meta-refresh |
| board-logs | Logs tab (no longer "Coming later"): both failed tasks, 3 links each or the grey sentence | same two |
| results-logs | the same Logs tab on the results page | same two |
| log-loading | /run/log first visit: "waiting" with symbol + words | critical meta-refresh only |
| log-ready | /run/log with the log text in a `<pre>` | none |
| log-error | /run/log for TRIM (no work folder): one plain sentence + way back | none |

## serious / critical

- There is no `serious`. The only `critical` is `meta-refresh` (`<meta http-equiv="refresh" content="15">`), on 3 + 1 pages:
  - board-tasks, board-logs, results-logs: the existing 15-second tag of the board (docs/reports/cloud-burn-2026-11/UI2.md F1, DESIGN.md:93;
    `render_board` adds it to every board page). It was already there before this task and is the same 8 hits ui_check gave on the plain board and results pages.
  - log-loading: the new page's waiting state refreshes itself every 15 seconds. This is what TC-011 and plan tl06 require ("頁面含自動刷新") and the same way
    the existing results "Outputs" loading page works; DESIGN.md allows no JS there. log-ready and log-error (the states that stay open) carry no refresh and are axe-clean.
- So "no serious or critical" is not literally met: removing the tag would break TC-011 and DESIGN.md:93. Both are the maintainer's decision
  (TESTING.md:1059 treats a board `meta-refresh` as an old finding to note, not count). Asked under 要問的問題.

## DESIGN.md 7, 8 in plain words

- 7 (state is never colour alone): waiting is "◌ + 等待中", read is "✓ + 已讀取", error is "✕ + one sentence"; the Logs tab links are text.
- 8 (phone width): at 390 wide the log page is one column, the log text wraps inside its box, nothing scrolls sideways; the Tasks row shows the log link in its own cell.
