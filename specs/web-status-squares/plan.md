# web-status-squares: one way to show a state, everywhere

Tier B (visible change). Maintainer 2026-10-19: "好的按照你的建議" — replace the old glyphs with the coloured square + word used by 012b, and make the English word for a finished run "Done" everywhere.

## What changes
- W1. Every place in `platform/abf_platform/web_board.py` (and `web.py` if any) that shows a run state with a glyph (`SYMBOLS` ▶ ✓ ✗ ⏸, the tally line `▶ n ! n ✓ n`, the stage label prefix `✓ `, the right-panel card icons, the left list) shows instead the same element 012b introduced: a small coloured square (its own element, colour from DESIGN.md tokens) followed by the word. No glyph characters remain in state displays.
- W2. Four states only, as the maintainer set them on 10-19: Running / 待處理 / Failed / Done. Chinese words: 執行中 / 待處理 / 失敗 / 完成. A lost/paused run shows as 待處理 (it needs the person), with its reason text unchanged. English: Running / Pending / Failed / Done. "Succeeded" disappears from the UI strings (the Nextflow status values in data are unchanged).
- W3. The tally line uses the same four words with counts (e.g. 執行中 1 · 待處理 3 · 完成 1), no glyphs, no "!".
- W4. Keep colour + word; colour alone never carries meaning.
- W5. Zero JS, one stylesheet, CSP hash updated, no inline style; English page has no Chinese; phone width 390 has no horizontal scroll.

## Out of scope
The confirmation page (separate task web-confirm-plain), layout changes, new routes.

## Tests first
- No state glyph (▶ ✓ ✗ ⏸ ⚡ and the tally "!") appears in any rendered board/run/now page, zh or en.
- Each of the four states renders the square element + the right word in zh and en; lost renders 待處理/Pending.
- "Succeeded" does not appear in any rendered page; "Done" does on the en page for a succeeded run.
- Existing tests that pin glyphs or "Succeeded" are changed only by swapping the string, each change listed in the ledger.
- No schema change; no migration needed.

## Rulings, 2026-10-19 (developer-agent, after the contract review)

- Q1 (tally). Four groups, one per state, always in this order: 執行中 n · 待處理 n · 失敗 n · 完成 n (en: Running n · Pending n · Failed n · Done n). A failed run counts under 失敗; a lost/paused run counts under 待處理. A group with 0 is still shown (0), so the line never changes shape. Add a test with failed and lost runs present.
- Q2 (task counts). The per-run task-count cell that today says 成功／Succeeded (Nextflow task numbers) becomes 完成／Done. The other task-count words (Cached, Failed, Aborted …) and all seven numbers stay unchanged.
- Q3 (DESIGN.md / TESTING.md). This task updates both to the new rule: DESIGN.md "States" becomes "coloured square + word; colour never carries meaning alone" (one sentence change, nothing else in DESIGN.md), and the 011a visual-check step 3 in docs/TESTING.md passes when the four states are told apart by their words in black and white. Add `DESIGN.md` and `docs/TESTING.md` to this task's files.
- Q4 (stage bar). A finished stage gets the Done square; the current stage gets the Running square; later stages get no square. Stage names and order unchanged.
- Q5 (unknown status). A status that is none of the four shows a neutral grey square and the word 未知／Unknown; no glyph and no "?".

## Rulings, 2026-10-22 (developer-agent, after the second contract review)

- Q4 revised. The stage bar shows the run's own state on the current stage: a finished stage gets the Done square; the current stage gets the square of the run's status (Running, Succeeded, Failed or Lost — the same square as everywhere else); later stages get no square. So a failed run shows the Failed square on the stage it failed in, and a succeeded run shows the Succeeded square on 結果. Stage names, order and the colour-plus-text rule (W1, W4) unchanged: the square keeps its text next to the stage name only where the board already shows text; the stage name itself is the text.
- Q3 revised. DESIGN.md: besides the "States" sentence, the two lines that still list symbol characters for states (the States list "▶ Running · ✓ Succeeded …" and the symbol in "Formal notices") are rewritten to name the squares instead, so DESIGN.md and the page agree that no symbol character stands for a state. No other DESIGN.md line changes.
- Unknown status in the totals row: counted in none of the four groups (the four groups count only running, pending, succeeded, failed); it still shows its own grey square and the word 未知 where a run is listed.
- Existing tests that the squares invalidate (symbol assertions in test_web_board.py and the running-page tests) may be changed only by swapping the asserted symbol for the asserted square markup, one for one, each listed in the ledger with old and new value.
