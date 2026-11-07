# TC-036 evidence: web-run-tasks-log

Made with `screenshots/seed_failed_demo.py` (throwaway platform of `scripts/dev/ui_check.py` + a FAILED run `ui-fail-run` with two failed tasks:
FASTQC with a recorded work folder, TRIM without; an online agent; the agent's answer for the log is injected with `jobs.take_result`).
Playwright + axe-core, 1440 and 390 wide, zh and en: 6 pages x 4 = 24 screenshots (`<page>-<width>-<lang>.png`). HTTP 200 on all 24.

| page | what it shows | axe (all 4 width/lang combos) |
|---|---|---|
| board-tasks | Tasks tab, failed rows: FASTQC has the "Errors" log link, TRIM has grey "No work directory on record" | moderate landmark-unique, critical meta-refresh |
| board-logs | Logs tab (no longer "Coming later"): both failed tasks, 3 links each or the grey sentence | same two |
| results-logs | the same Logs tab on the results page | same two |
| log-loading | /run/log first visit: "waiting" with symbol + words, a Refresh link and the data time | none |
| log-ready | /run/log with the log text in a `<pre>` | none |
| log-error | /run/log for TRIM (no work folder): one plain sentence + way back | none |

## serious / critical (redone after the lead's ruling of 2026-11-07)

- The waiting page `/run/log` no longer carries `<meta http-equiv="refresh">`: it has a "Refresh" link (same address, no retry) and the line "Data as of HH:MM". log-loading is axe-clean in all 4 combos (the first try had a `link-in-text-block` serious hit at 1440 when the link shared a paragraph with the time; the link now has its own paragraph).
- The only `critical` left is `meta-refresh` on board-tasks, board-logs and results-logs: the board's existing 15-second tag (`render_board` adds it to every board page; DESIGN.md:93). It was there before this task (the same hit ui_check gives on the plain board and results pages) and is outside this task by the ruling; docs/TESTING.md:1059 treats it as an older finding to note, not count. No `serious` hit on any page. `moderate landmark-unique` on the three board pages is also old.
- log-ready, log-error, log-loading: no violations.

## DESIGN.md 7, 8 in plain words

- 7 (state is never colour alone): waiting is "◌ + 等待中", read is "✓ + 已讀取", error is "✕ + one sentence"; the Logs tab links are text.
- 8 (phone width): at 390 wide the log page is one column, the log text wraps inside its box, nothing scrolls sideways; the Tasks row shows the log link in its own cell.
