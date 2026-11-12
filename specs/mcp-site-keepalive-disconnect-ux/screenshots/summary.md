# Screenshots and axe: the red "site connection is down" bar (TC-030, TC-032)

Re-shot 2026-11-12 (replaces the first set, which was taken with an agent that was offline, so no bar was shown).
Setup: a throwaway platform in a temp folder on a free port (`scripts/dev/ui_check.py` `start_platform`), user `alice`, agent `agent-t`
registered as owned by alice, online (re-registered every 3 s during the shoot), reporting `site_link=closed`.
Before shooting, `site_link.closed_agents` listed `['agent-t']`. Playwright Chromium in WSL, axe-playwright-python, full-page shots.
The real platform (8787/8788/8789) and its database were not touched.

## What every one of the 12 images shows
Measured in the browser on each page (not assumed): exactly one `.linkbar`, directly under the dark top bar (top = 40 px), full width,
background `rgb(250, 230, 227)`, text `rgb(176, 38, 29)`, a leading ✗, no horizontal scroll (scrollWidth = clientWidth: 1440 or 390).
Bar wording, zh: 站台連線已掉：請在執行 agent「agent-t」那台機器的 WSL 終端機重新登入（貼上開連線指令並輸入 OTP）。已在跑的分析不受影響；新的分析在恢復前無法送出。
Bar wording, en: The site connection is down. On the machine running agent "agent-t", log in again in its WSL terminal (paste the connect line, type the one-time code). Runs already going are not affected; new runs cannot be sent until it is back.

| file | page | width | lang |
|---|---|---|---|
| board-1440-zh.png, board-1440-en.png, board-390-zh.png, board-390-en.png | board `/` | 1440, 390 | zh, en |
| launch-1440-zh.png, launch-1440-en.png, launch-390-zh.png, launch-390-en.png | `/launch` | 1440, 390 | zh, en |
| settings-1440-zh.png, settings-1440-en.png, settings-390-zh.png, settings-390-en.png | `/settings` | 1440, 390 | zh, en |

The images show only the bar and the page around it. They do not show a refused launch, and they do not show the bar going away
(that is covered by `platform/tests/test_site_disconnect_ux.py::test_bar_goes_when_open_again`, not by an image).

## axe (axe-core via axe-playwright-python), 12 combinations
- critical `meta-refresh` (node `meta[http-equiv="refresh"]`): on the board page only, in all 4 width/language combinations. Not new:
  the same tag is on origin/v3 at `platform/abf_platform/web_board.py:958` (the board's auto-refresh) and this feature does not touch it;
  the same finding is recorded for the base in `docs/reports/cloud-burn-2026-11/UI2.md`, and `docs/TESTING.md` says to note it, not count it.
- moderate `landmark-unique` (nodes `.side`, `.views`): on all 12 pages. Also not about the bar.
- Nothing, of any impact, points at `.linkbar`. No serious finding anywhere. The tool's overall verdict is therefore "fail" because of the one
  pre-existing critical `meta-refresh`; whether TC-030 counts as passed with it is the reviewer's call.
