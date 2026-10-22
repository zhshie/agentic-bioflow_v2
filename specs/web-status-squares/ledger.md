# ledger web-status-squares

Implementation: `platform/abf_platform/web_board.py` (SYMBOLS removed; STATES; `_sqw` square+word; strings; stage bar; tally; CSS `.state-unknown`), `DESIGN.md` (3 lines), `docs/TESTING.md` (011a step 3). `web.py`, `store.py`: untouched.
Chip strings (`chip_*`, the launch-page source line) also follow the new words (succeeded 完成, lost 待處理 / Pending) and gain `chip_unknown`.

## Existing assertions changed (old -> new, one for one)

test_web_board.py
- `tally()` helper: regex `[▶!✓⟳?…]\s*\d+` -> `[^\s\d]+\s*\d+` (the tally now reads "word n").
- test_tcs19_s20_left_column: `("▶","執行中")`,`("✗","失敗")`,`("⏸","失聯/暫停")`,`("✓","成功")` -> square markup + `執行中/失敗/待處理/完成`.
- test_tcs26_counts_row: `["▶ 3","! 3","✓ 4"]` -> `["執行中 3","待處理 2","失敗 1","完成 4"]` (the old "!" was failed+lost; Q1 splits it).
- test_tcs01_ten_runs_at_once: `["▶ 4","! 3","✓ 3"]` -> `["執行中 4","待處理 1","失敗 2","完成 3"]`.
- test_tcl21_item_is_one_link: symbol+label -> square markup + label (`成功`->`完成`, `失聯/暫停`->`待處理`).
- test_tcl22_l23_numbers_and_done: `"▶ 執行中 8/10"` -> `"執行中 8/10"` plus the square in the item.
- test_tcs27_s28_item_lines: `a-run ▶ ▶ 執行中 8/10` etc. -> `a-run 執行中 8/10`, `b-fail 失敗 1/10`, `c-lost 待處理 4/10`, `d-ok 完成 10/10`, each also asserts the square.
- test_tch21_stage_bodies: `n.replace("✓ ","")` -> names compared directly (no glyph any more).
- test_tcs29_stage_strip_style: `"✓" in done cells, "✓" not in results` -> done square in launch and running, and (Q4 revised) the succeeded run's own square on results.
- test_tcl14_l15_l16_middle: head `✗` -> the failed badge holds the square; count cell `成功`->`完成`.
- test_tch08_states_and_symbols: symbols ▶✓✗⏸ -> square markup (row, badge); labels `成功`->`完成`, `失聯/暫停`->`待處理`.
- test_tcs32_s33_s34_now_page: `"▶" in line` -> square in line.
- test_tch03_only_own_runs: red-number `!\s*(\d+)` -> sum of the 待處理 and 失敗 tally groups.
- test_tcl32_l33_english: count cell `succeeded` -> `done`.
- test_tcs50/tcs51 (tally users): follow the tally() helper.
- test_r10_reason_marker_left_tag_and_wrapping: `成功`->`完成`, `失聯/暫停`->`待處理`, `Succeeded`->`Done`, `Lost/paused`->`Pending`; the `stg` span regex now includes the square.
- ok-line check (`"✓" in ok[0] and "成功"`): -> square + `完成`.

test_web_running.py
- test_r40_r44_title_and_cards: `"✗ 失敗" in plain(mid)` -> `<span class="sq"></span> 失敗` in mid.
- test_r55_r58_tasks_bar_and_legend: labels `成功`->`完成`, `Succeeded`->`Done`.
- test_r79_r92_tab_contents: `"✗ 失敗" in info` -> square + 失敗 in the raw info HTML.

test_web_actions.py: none changed (its GLYPHS check only forbids glyphs).
