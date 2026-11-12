# Ledger: mcp-publish-figure-gallery (slice 2)

Executor record. Written for the reviewer; nothing here changes the plan or the test cases.

## Choices the plan asked to be recorded

- **P1** (a figure packed earlier is not pre-ticked): every tick box is unticked on every page load (`name="fig"`, no `checked`). Each figure shows its own state with a symbol and words (`✓ 已打包` / `— 未打包`, English `✓ Packed` / `— Not packed`), and beside the pack button one line says the package will hold exactly the figures ticked now and that unticked ones leave it (`g_pack_note`). Packing is a set: figures ticked at the last press are `packed: true`, all others `packed: false`; none ticked empties the package.
- **P8** (DESIGN.md screen 9 wording): the plan's wording is used, not the DESIGN.md original. The button reads 打包所選的圖 / "Pack the selected figures", not "Package the n selected figures, go to Finished"; there is no count in the button and no "newest highlighted" (no new CSS; the gallery is sorted newest first by `created`, ties by name). The gallery lives on the finished page itself, so the button returns there (303) instead of moving to another stage.
- P2 to P7, P9 followed the lead's rulings (same page after a press; no tick box or pack button on an empty gallery; a name not in the gallery refuses the whole press; duplicates count once; code/parameters shown only when present; gallery only on the finished stage of a succeeded run; newest first). P9: pack and delete are cookie + CSRF + same-origin button presses, no `confirmations` row, no job, no MCP tool. Reported for the maintainer's one-line answer, not decided here.

## What was built

- `actions/figures.py`: `read_figure`, `pack_figures`, `delete_figure`, `gallery_view` (reads the index and the code/params text, plus the caller's own pending `publish_figure` request), `pending_request`. Not exported from `actions/__init__.py` (not in scope, and no MCP tool may use them); `web.py` imports them from `.actions.figures` by name.
- `web.py`: `GET /run/figure`, `POST /run/figures/pack`, `POST /run/figure/delete`; `FIGURE_HEADERS` (own headers, `web_preview.image_headers` is not used: it labels everything that is not png as svg); `FINISHED_HEADERS`; the finished page asks `gallery_view`.
- `web_finished.py`: the gallery section, the `Figures` row of the package (three states), the refusal page; strings `g_*`, `f_*`, `gr_*` in both languages. `web_board.py`: one extra parameter (`gallery`) passed down, and the page reload is switched off while the gallery holds a figure.
- No migration, no new table, no new dependency, no CSS, no JavaScript, no inline style.

## Constants

CSRF purposes: `figpack:<run id>` and `figdel:<run id>`. Names per press: 30 (= `MAX_PER_RUN`), name length 80 (`NAME_LIMIT`), form body 16384 bytes (`MAX_BODY`), at most 100 form fields parsed (more is refused as "too many"). Image width 240 (`<img width>`), `loading="lazy"`. Response codes: pack/delete refused for a name = 400, index not writable = 500, bad CSRF = 403, other origin = 403, not yours or not there = 404, no login = 303 to /login.

## Decisions that differ from the plan text, and why

1. **`img-src 'self'` only on a finished page that holds a figure.** The plan says "the finished stage". The existing `test_web_result_viewer.py::test_tc070_071_074_075_other_pages_keep_the_base_headers` requires the finished page (a run without a gallery) to keep the base policy exactly, and that test may not be loosened. A page with no `<img>` needs no `img-src`, so it keeps the base policy; a page with figures gets `FINISHED_HEADERS`.
2. **The finished page reloads itself (existing `meta refresh 15`, pinned by `test_fs11_constraints_hold`) only while the gallery is empty.** With figures there is no `<meta refresh>` (TC-011): a reload every 15 seconds would clear the ticks a person has made. The empty-gallery page keeps the old behaviour because the pinned test needs it.
3. **`PAGE_WRITE_NAMES` in `test_actions_layer.py` was not extended.** That list is also run through the "refuse without a human channel" test, which these actions do not take. A new test `test_gallery_page_actions_exist_in_the_action_layer_and_are_not_tools` holds the "exist, and are not tools" half; the list itself is untouched.
4. **`web.py` imports the gallery functions with `from .actions.figures import ...`.** `test_web_parity.py` (pinned) counts every name taken from `actions` and wants it in its tables; the three new names are not in `actions`' public surface (no MCP tool), so the import goes to the submodule. TC-059's one-to-one list is in `test_web_figures.py::test_routes_only_call_the_action_layer` and `test_actions_layer.py`.

## Existing tests that had to change (see the report; some are outside the plan's file list)

- `test_web_finished.py`: the `圖` row expectation `之後開放` became `— 無`, and one English assertion was added (`Figures` is `— None`). The `下載交付包 之後開放` and `Coming later` assertions are untouched.
- `test_actions_layer.py`: one test appended.
- Outside the plan's list, forced by the plan's own new routes: see the report (route-table pins in `test_web_board.py::test_tch11_read_only` and `test_publish_figure_confirm.py::test_page_headers_and_css_are_unchanged`).

## Verification record

Filled in below at the end of the run (suite counts, UI checks, what is unverified).

### UI checks (TC-072, TC-073, TC-074)

Driver: a throwaway script outside the repository (it reuses `scripts/dev/ui_check.py`'s `start_platform`; `ui_check.py` itself has no finished-stage page). Playwright, Chromium and axe-playwright-python were available in WSL. 12 screenshots (empty, three unpacked incl. one SVG and a 74-character file name, packed; 1440 and 390; zh and en) are in WSL `/tmp/ui-shots-gallery/` with `summary.md`.

- Images: all load (0 broken). TC-073: no horizontal overflow at 390 in any state (0 px).
- axe, pages with figures (unpacked, packed): 0 serious, 0 critical; 1 moderate `landmark-unique` on `.side` (the board's own left column, not this slice).
- axe, **empty gallery page: 1 critical `meta-refresh`**. That is the finished page's existing 15-second `<meta refresh>`, pinned by `test_fs11_constraints_hold`, which this slice keeps while the gallery is empty (see decision 2). So TC-072's "no critical" is **not met for the empty state**; it is met for the states with figures. Removing the refresh on every finished page needs that pinned test changed: for the maintainer.
- TC-074 (impeccable detector): see the report; run on the saved HTML files if the tool ran, else UNVERIFIED.
- TC-075, TC-076, TC-094, TC-095 are for the maintainer (manual); not done by the executor.

## Fix round after the adversarial review (lead's rulings G1-G5, 2026-11-13)

Slice 1's fix round (rulings F1-F8, branch `fable/mcp-publish-figure`) was merged first (plain merge). Conflicts, all resolved keeping both sides: `CHANGELOG.md` (slice 1's entry from the other side, slice 2's entry placed right after it, keep-submissions still first), `docs/PLATFORM.md` (slice 1's updated paragraph, then slice 2's two paragraphs), `docs/TESTING.md` (slice 1's steps 1-7, then the slice 2 section), `web.py` imports (`site_link` plus `web_finished` and the figures actions), `test_publish_figure.py` (both blocks), `test_publish_figure_confirm.py` (slice 1's route-table test, with the three slice 2 routes re-added to its expected list). One more forced edit: `test_web_figures.py::test_style_untouched` pinned the style hash `719ce2ab`; the base (v3) repinned `web_board.STYLE` to `15f0b560` (the `.linkbar` rule), so the pin follows it, exactly as the base did in its other tests.

- **G1** `gallery_lock(folder)` in `actions/figures.py`: a thread lock plus `flock` on the gallery folder itself, held from `read_index` to the replace in `pack_figures`, `delete_figure` and `write_confirmed` (the part after the checks is now `_commit`; slice 1's F5 restore-on-failure and F6 case and replaced-set re-check run inside the lock). The lock is on the folder, not a lock file, because slice 1's pinned `test_storage_format` lists the folder and allows only the figures and `index.json`. Test: `test_index_updates_do_not_lose_each_other` (real threads; a delete and a confirmed write start between the pack's read and write; failed first: index listed `a.png` with no file).
- **G2** the finished page shows `g_broken` for a damaged index; `pack_figures` and `delete_figure` check damage before names and answer reason `unreadable` (400, same sentence, no path), also for an empty name list. Tests: `test_finished_gallery_empty_line` (TC-009 **changed by ruling G2**: damaged index now reads "圖庫暫時無法讀取" / "cannot be read right now", 200, no path, not the empty-gallery line), `test_damaged_index_refuses_pack_and_delete_with_one_sentence`.
- **G3** `FIGURE_HEADERS` policy gets `form-action 'none'; base-uri 'none'; frame-ancestors 'none'`; an SVG requested with `Sec-Fetch-Dest: document` is an attachment. Test: `test_figure_csp_and_svg_opened_as_a_document`.
- **G4** `_stage` removes its temporary file when the write fails (covers `.tmp-idx-*` and the rest). Test: `test_failed_index_write_leaves_no_temporary_file`.
- **G5** the page inlines the first 200 lines or 20 KB of each code and params text, with one sentence and a link to `GET /run/figure?run=&name=&part=code|params` (plain-text attachment `<name>.code.txt`; same owner check, same 404, same headers; no new route). TC-004 **changed by ruling G5**: "complete, not truncated" became "the first part complete, the rest downloadable". Tests: `test_finished_page_inlines_only_the_start_of_code_and_params`, `test_part_download_is_owner_only_and_answers_404_for_everything_else`.
- The 15-second refresh of an empty gallery (`test_fs11`) is kept.
- SYNC outside the plan's file list, forced by the plan's own route: `test_keep_submissions.py::test_tc082_the_web_has_no_forget_route` refused any route path containing `delete`; it now names `/run/figure/delete` as the one allowed (the gallery's own delete of a figure). It still refuses every forget route and every other delete route.
