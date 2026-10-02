# Bug Fix: Low-severity gaps left in the paper package after #32

- **Slug**: package-gaps-low
- **Fixed**: 2026-10-02
- **Assessment**: ./assessment.md
- **Issue**: #38
- **Status**: applied, all five items fixed

## Per item

| # | Item | Fix | Where |
|---|------|-----|-------|
| 1 | `${...}` in an HTML attribute vanishes with the tag or lands in a link target | One regex pass over tags and placeholders. Inside a tag the placeholder becomes `#`; its `[GAP: unresolved placeholder ${x}]` is written as text just before the tag, so it survives tag stripping and is never a link target | `scripts/methods_text.py` `mark_unresolved_placeholders()` |
| 2 | Plan row with no id skipped silently | Table rows with any content but an empty id are kept; Results prints `[GAP: a plan row has no id (question: '...') - no figure can be matched to it; add an id to analysis.md]`. All-blank rows still ignored | `scripts/build_package.sh` `parse_table()` and the Results loop |
| 3 | Methods paragraph and software list do not name their source | `Source:` line after the methods paragraph (MultiQC report, or template path relative to the assets dir) and one under "### Software" (versions file; CITATIONS.md or "no CITATIONS.md") | `scripts/methods_text.py` `render()` |
| 4 | Second format of a figure not mentioned | `Also in figures/, not embedded: fig1.pdf` under the figure | `scripts/build_package.sh` |
| 5 | Non-image file embedded as an image | Only png/jpg/jpeg/svg/pdf/tif/tiff/gif/webp can be embedded. An id whose only matches are other files prints `[GAP: id 'fig1' has no image file in figures/ - only: fig1.csv]` and those files are not also reported as orphans | `scripts/build_package.sh` `fig_matches()` |

## Tests (extend `tests/package_gaps_test.sh`, 13 new assertions)

RED on 3eb87fa (code of main 1a049f1): `9 failed`. GREEN after the fix: `OK: invisible-package-gaps stays fixed`.

| Assertion | Red on main | Why it is not vacuous |
|-----------|-------------|-----------------------|
| `${cls}` in `<div class="...">` shows as a gap | FAIL | the whole tag and marker were stripped |
| `${site}` gap is not only a link target | FAIL | main output: `[the project site]([GAP: ...])` |
| `${site}` in `<a href>` shows as a gap | ok on main | passes on main because the marker exists inside the link target; kept as a guard, the assertion above is the one that fails |
| methods paragraph names its template | FAIL | no `Source` line existed |
| software list names versions file and CITATIONS.md | FAIL | |
| MultiQC-rendered paragraph names the report | FAIL | |
| id-less plan row is a visible gap | FAIL | |
| `fig1.pdf` named beside `fig1.png` | FAIL | pdf appeared nowhere in the manuscript |
| `fig1.csv` not embedded | FAIL | main emitted `![..](figures/fig1.csv)` |
| missing image is a visible gap naming `fig1.csv` | FAIL | |
| `fig1.csv` not also an orphan | ok on main | guard for the new "claimed" handling, not a red test |

Other runs (WSL): `package_gaps_test.sh`, `build_package_test.sh`, `methods_text_test.sh`,
`principle_9_test.sh`, `package_crate_test.sh`, `no_hardcoded_paths.sh`,
`scripts_name_their_alternative.sh` all OK. The full suite was not run (affected files only).

## Needs maintainer decision

1. **Item 4 wording and place.** The "Also in figures/, not embedded" line is plain text, not a `[GAP:]`, because nothing is missing. It will appear in the rendered manuscript and the author must delete it if unwanted. Alternatives: move it to README.md, or make it a `[GAP:]` so it cannot be missed.
2. **Item 5 image list.** pdf stays embeddable (as before, lowest preference). If PDFs should not be embedded either (quarto converts them, a known failure source per the script header), drop `.pdf` from `IMAGE_EXTS`.
3. **Item 1 placeholder in href** becomes `#` (a link to the top of the page) with the gap shown before the link text. A different neutral target is a one-character change.
4. **`Source:` paths.** The template/CITATIONS.md path is shown relative to the assets dir (`nf-core/demo/CITATIONS.md`), not absolute, to keep output free of home directories (constitution 3).

## Not fixed

- The kv-block (`id: ...`) form of `analysis.md` has the same "no id" hole for item 2, but a block without `id:` cannot be told apart from an ordinary heading, so flagging it would add false gaps. Only the table form is covered.
- `commands/finish.md` step 3 does not yet list the two new gap kinds (id-less row, no image file) or the "Also in figures/" line; editing `commands/` brings in the manual half of `docs/TESTING.md`, so left for the maintainer.

## After independent acceptance (2026-10-02)

Fixed test-first (5 assertions red on 0e31903, green after):

- **Regression vs main**: `fig1_a.png`, `fig1_b.png`, `fig1_c.csv` with id `fig1` printed "matches 2 files" and dropped the csv from the manuscript and the orphan list. Now `[GAP: id 'fig1' matches 2 image files in figures/: ...; also: fig1_c.csv]`; every file in figures/ is named somewhere.
- A gap marker before `<a href>` fused with the link text into a pandoc reference link (`[GAP: ...][site](#)`); a space now separates them.
- `commands/finish.md` step 3 names the new gap kinds (plan row with no id, id with no image file) and says the "Also in figures/, not embedded" line is not a gap. `command_layer_is_site_neutral.sh` green.

Needs maintainer decision (added): an id whose only matches are other non-image files such as `.eps` or `.html` stays a visible `[GAP: ... no image file ...]`, as now; say if `.eps` should count as embeddable.
