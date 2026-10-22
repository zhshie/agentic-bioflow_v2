# Screenshots for the maintainer's look, 2026-10-22

Playwright (Chromium 1248), device emulation, full page, against a seeded data folder: four runs owned by one user — running (12/37), succeeded (44/44), failed (18/23, DADA2 error), lost (7/39, no heartbeat).

| File | Page | Width | Language | scrollWidth / clientWidth |
|---|---|---|---|---|
| now-1440-zh.png / now-1440-en.png | Now page `/` | 1440 | 中 / EN | 1440 / 1440 |
| now-390-zh.png / now-390-en.png | Now page `/` | 390 (mobile) | 中 / EN | 390 / 390 |
| run-failed-1440-zh.png / run-failed-1440-en.png | failed run `/?run=…` | 1440 | 中 / EN | 1440 / 1440 |
| run-failed-390-zh.png / run-failed-390-en.png | failed run `/?run=…` | 390 (mobile) | 中 / EN | 390 / 390 |

TC-065 (no sideways scroll at 390 px): scrollWidth equals clientWidth on all four 390 px pages.
