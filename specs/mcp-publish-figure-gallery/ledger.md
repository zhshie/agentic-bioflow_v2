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
