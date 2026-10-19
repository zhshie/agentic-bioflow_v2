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
