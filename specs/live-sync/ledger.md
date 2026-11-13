# live-sync: ledger (executor, 2026-11-13)

Branch `fable/live-sync`. Contract: `plan.md`, `test-case-overview.md`, `test-case.md` (not edited).

## lead rulings 2026-11-13 (2)

- **R-A** Existing tests outside the first lists may be rewritten only in two ways, assertion by assertion: (i) an assertion about an in-scope page (a page that reloads itself today, or the succeeded finished stage with figures) that says "no `<script`" or pins the CSP becomes "exactly one `<script src>` with a same-origin path and no inline content; CSP is today's string plus exactly `script-src 'self'; connect-src 'self'`"; (ii) an assertion that compares an out-of-scope page's CSP or markup with `/` is retargeted to a literal string or `web._HEADERS`. Every assertion about an out-of-scope page itself stays as written. `test_tn06_no_push_routes` keeps its meaning.
- **R-B** The three entry points are real routes (not an ASGI middleware), with the login and owner checks of the pages; the route-table pins gain exactly those three lines. TC-064 stays as written.
- **R-C** Re-running the page handlers with a LOOK flag is accepted if TC-024 to TC-031 hold for every in-scope route, proved by tests that compare the whole platform data folder and count queued jobs.
- **R-D** Marking regions by `<body data-live>` plus ordinal children is accepted; TC-016 is judged on the logical regions; a new figure inserted before ticked ones must not replace a touched region.
- **R-E** The id change in `web_finished.py` and `data/*.js` in package-data are accepted; say whether the wheel contains `live.js`.
- **R-F** The known limit (one full load when a run turns succeeded and the Outputs listing has no answer yet) is accepted and written in `docs/PLATFORM.md` (done, "Live updates").

### What was done for each ruling

- R-B: `/static/live.js`, `/live/version`, `/live/content` are `Route(..., methods=["GET"])` of the web app (`web.py`). The pins that gained exactly those three lines: `test_confirm_page.py::test_tcg04_*`, `test_owner_binding.py::test_tc068_*`, `test_web_board.py` (the exact route list), `test_chat_confirm.py::test_tcm_47_*`, `test_cleanup_offer.py::test_no_new_mcp_tool_no_new_route_no_new_cli_command`, `test_dataset_cli.py` (Route regex), `test_k8s_launch.py::test_the_user_visible_actions_are_those_of_the_base`, `test_publish_figure_confirm.py::test_page_headers_and_css_are_unchanged` (git-diff of the route list), `test_web_downstream.py::test_no_new_route_no_new_action`. Where the pin already filtered "the three gallery routes", the three live routes were added to the same filter (chat_confirm, cleanup_offer, dataset_cli, k8s_launch, confirm_page also pins them apart). `test_temp_password.py::test_tc027_*` walks every route with a temporary-password login: `/static/live.js` joins its exempt list (the script is public, TC-036); the two live looks answer a temporary login with 303 `/welcome` like every page.
- R-C: `test_web_live_sync.py` compares the whole platform folder (every file's bytes, every row of every table of the three databases, the job count, the confirmation count) before and after a version and a content request, for: the board (running, failed, results, outputs, `relist=1`, finished, empty, `/?run_name=`), `/run/file` and `/run/preview` waiting (with `retry=1`, `relist=1`), `/launch` with the real actions (no fake: `pipeline_files` and `latest_release`, `src=used` and `src=new`), `/act/resume/edit` before and after the run is no longer failed (no `request_resume`, no confirmation row), `/upload/<batch>` on the way and complete-but-not-registered (no Dataset registered). `test_tc022_tc023_*` counts queued `pipeline_files` jobs against today (a whole page every 15 s for 100 s, with the site silent and with an answer at 20 s) with a movable clock. The release-cache file is the one write a look could have made (`releases.lookup`): a look passes no cache path (`actions.latest_release` asks `web_live.looking()`).
- R-D: see "regions" below. Browser check TC-014 (new figure inserted before the ticked ones, newest first): result `figures ['fig3.png', 'fig1.png', 'fig2.png'], ticked before ['fig1.png', 'fig2.png'], ticked after ['fig1.png', 'fig2.png']`. The script matches regions by version, not by place; a touched region that is paired with a changed one is skipped, never replaced and never duplicated (this was a real bug first: the ids of a figure's tick box and delete form carried its position, so a new figure changed every other figure's region; they are now made of the figure's name, `web_finished.py::_key`).
- R-E: the wheel **was built and contains `live.js`**: `PYTHONPATH=<setuptools 84> pip wheel --no-deps --no-build-isolation platform/` then `zipfile -l`: `abf_platform/data/live.js 10118 bytes` (the venv's own setuptools 59 cannot read `[project]`; a newer one was used from a temp folder).
- Not changed because a test pins it: `web_board.py` is untouched (`test_publish_figure_confirm.py` requires it). The `<noscript>`, the script tag, the body attributes and the policy are made in `web.py::_html` / `web_live.decorate` after the page is rendered, so the page of every other route is byte for byte what it was.

## How the regions work (R-D, TC-016)

`<body data-live>` carries `{h, c: [{n, p, v}]}`: `h` = a hash of the page's policy, `c` = the containers (name, place from the body as the index of each ancestor among its element children, `v` = the version of each child). Containers: `page` (body), `grid` (`div.wb`), `left`, `mid`, `right` (the three columns), `narrow` (the single-column page), `form`/`steps` (the launch and resume forms and their steps), `gal`/`pack`/`figs` (the gallery). A *region* is a direct child of a container that is not itself a container, named `<container>-<n>`: fixed words and a number. Every form control is inside exactly one region (`test_tc016_*` checks it by offsets), regions do not nest, no start tag of the page is changed. The version of a region is a hash of its text with the per-login form tokens made equal (`value="<64 hex>"`), so two logins give the same versions and a content request returns the region as the full page has it.

## Routes that carry the script (TC-043)

Exactly the pages that reload themselves today, plus one:
1. `/` : every stage of a run except the succeeded run's downstream stage; the empty board; not the board with a refusal line (the answer to a POST).
2. `/?run_name=<name>` while the index has no such run (waiting).
3. `/launch` while the pipeline's files are being read (loading).
4. `/act/resume/edit` while the pipeline's files are being read.
5. `/run/file` waiting for the site's answer.
6. `/run/preview` waiting for the site's answer.
7. `/upload/<batch>` while files are on the way.
8. `/?run=<id>&stage=finished` of a succeeded run whose gallery has figures (no refresh, no `<noscript>`).

Not carrying it: `/login`, `/welcome`, `/c/<id>`, `/consent/<id>`, `/settings`, `/usage`, `/upload` (the form), `/run/log`, ready `/run/preview` pages, `/run/figure`, `/run/image`, `/run/report`, `/launch/diagram`, `/launch` once its files are read, the succeeded run's downstream stage, 404 pages, a refusal line on the board.

## CSP before and after (each header set)

`S` = `style-src 'sha256-FfC1YK8kGEBly+aw5sxs1lF8rL8fd0bvd3C1C3uWpGw='` (unchanged: no new CSS). `ADD` = `; script-src 'self'; connect-src 'self'`.

| header set | before (and after, for every page that does not carry the script) | after, for the pages of the list above |
|---|---|---|
| `_HEADERS` (board, waiting file/preview pages, resume edit) | `default-src 'none'; S; form-action 'self'; frame-ancestors 'none'; base-uri 'none'` | the same string + `ADD` |
| `LAUNCH_HEADERS` (`/launch`, `/upload/<batch>`) | `default-src 'none'; img-src 'self'; S; form-action 'self'; frame-ancestors 'none'; base-uri 'none'` | + `ADD` |
| `FINISHED_HEADERS` (finished stage with figures) | same string as `LAUNCH_HEADERS` | + `ADD` |
| consent page (`form-action` gains the connector origin) | unchanged | unchanged |
| `FIGURE_HEADERS`, `/run/image`, `/run/report`, ready `/run/preview` (`frame-src 'self'` / `img-src 'self'`), `/launch/diagram`, login, welcome, confirmation | unchanged | unchanged |

## Existing tests rewritten (old assertion -> new assertion; rule; page)

`helpers.py` gained `one_live_script(text)` (exactly one `<script`, and it is `<script src="/static/live.js"></script>`), `live_rules(text, csp=None)` (a page with the meta refresh, now inside `<noscript>`: exactly the one script and, if the policy is given, today's policy + `ADD`; any other page: no `<script`, no `<noscript`, no `script-src`, no `connect-src`: the old rule, unchanged) and `strip_live(text)`.

| test | old | new | rule | page |
|---|---|---|---|---|
| test_web_board.py::test_tch13_csp_and_markup | `"script-src" not in csp` and `"<script" not in t` for all 8 pages | `live_rules(...)` | (i) for `/`, `/?lang=en`, `/?run=`; the settings, 404, login, confirmation and consent pages keep the old rule | `/`, run page |
| test_web_board.py::test_tcl44_* | `"<script" not in t.lower()` | `live_rules(t)` | (i) | `/`, run pages; settings and 404 keep the old rule |
| test_web_board.py::test_tn06_no_push_routes | `"<script" not in c.get("/").text` | `one_live_script(c.get("/").text)` and the script has no `WebSocket`, `EventSource`, `sendBeacon`, `.submit(`, `POST`; the route-name check is unchanged (the three new paths contain none of `ws|stream|events|sse`) | (i), meaning kept | `/` |
| test_web_board.py (route list) | exact list | + `/live/content`, `/live/version`, `/static/live.js` | R-B | routes |
| test_web_actions.py::test_tc046_tc048_* | `"<script" not in t`, `"script-src" not in csp` | `live_rules(t, csp)` | (i) | `/`, run page; `/launch` and POST answers keep the old rule |
| test_web_bugs_a.py::test_page_constraints_after_changes | `"<script" not in r.text` | `live_rules(r.text, csp)` | (i) | `/?run=...&stage=running|launch` of a succeeded run (board) |
| test_web_bugs_b.py::test_style_no_inline_no_script | `"<script" not in text` | `live_rules(text)` | (i) | the two run pages; `/usage` keeps the old rule |
| test_web_downstream.py::test_studio_link_opens_new_tab | CSP of the downstream page == CSP of `/` == empty | == `web._HEADERS[...]` | (ii) | the succeeded downstream stage (out of scope) |
| test_web_downstream.py::test_no_new_route_no_new_action | exact routes | + three | R-B | routes |
| test_web_figures.py::test_gallery_text_is_escaped | no `script` tag; no `<script` in the page | the only `script` tag is `src=/static/live.js`; one `<script` | (i) | finished stage with figures |
| test_web_figures.py::test_no_refresh_and_no_poll_on_finished | no meta refresh, no `<script` | no meta refresh, no `<noscript`, `one_live_script` | (i) (named by the lead) | finished stage with figures |
| test_web_figures.py::test_finished_csp_gets_img_src_but_other_pages_do_not | `/`, run pages == base; finished == base+img-src; no `script-src` | `/` and run pages == base + `ADD` (they reload themselves); `/settings`, `/usage`, `/c/` == base; finished == base+img-src + `ADD`; an empty gallery == base + `ADD` | (i) | `/`, run pages, finished |
| test_web_figures.py::test_no_inline_style_or_script_in_gallery | `"<script" not in t` | `one_live_script(t)` | (i) | finished stage (with and without figures) |
| test_web_finished.py::test_fs11_constraints_hold | `"<script" not in t` | `one_live_script(t)` | (i) | finished stage |
| test_web_fixes_1.py::test_f08_constraints_hold | `"<script" not in t` | `one_live_script(t)` | (i) | run pages |
| test_web_guided_launch.py::test_gl12_constraints_hold | `"<script" not in t`, `"script-src" not in csp` | `live_rules(t, csp)` | (i) | `/launch` (loading states carry it, ready ones none) |
| test_web_guided_launch_2.py::test_g09_limits | `"<script" not in t`; csp == launch csp | `live_rules(t, csp)`; csp == launch csp (+ `ADD` when it reloads) | (i) | `/launch` loading state; ready and error states unchanged |
| test_web_guided_launch_2d.py::test_tc049_other_pages_are_as_before | csp of `/` == base | `/` == base + `ADD`; settings, usage, `/c/` == base | (i)/(ii) | `/` |
| test_web_guided_launch_2d.py::test_tc055_* | `"<script" not in page` | `live_rules(page)` | (i) | `/launch` loading state; the other states unchanged |
| test_web_result_viewer.py::test_tc007_listings_gain_only_plain_links | `<script` banned in every page | `live_rules(text)`; `<script` removed from the banned tuple | (i) | results/finished/outputs pages |
| test_web_result_viewer.py::test_tc070_071_074_075_* | csp == base for `/`, finished, outputs, waiting download | == base + `ADD` for pages that reload themselves; settings, usage unchanged | (i) | `/`, finished, outputs, waiting `/run/file` |
| test_web_result_viewer.py::test_tc046_no_other_page_has_frame_src | `"script-src" not in csp` | `live_rules(text, csp)`; `frame-src` and `<iframe` still banned | (i) | the waiting `/run/preview` page of a file not yet answered (red); ready previews unchanged |
| test_web_results_outputs.py::test_ro11_constraints_hold | `"<script" not in r.text` | `live_rules(r.text, csp)` | (i) | results pages |
| test_web_resume_edit.py::test_tc060_to_tc062_* | `<script` in the banned regex | regex without it + `live_rules(t)` | (i) | `/act/resume/edit` loading state; ready state unchanged |
| test_web_run_log.py::test_tc015_to_018_021_* (line 213) | CSP of log page == CSP of `/` | == `web._HEADERS[...]` | (ii) | `/run/log` (out of scope) |
| test_web_run_log.py::test_tc034_tabs_have_no_inline_style_or_external_resource | `"<script" not in t` | `one_live_script(t)` | (i) | the board run page, tabs tasks and logs (red); `/run/log` untouched |
| test_web_running.py::test_r60_r78_order_and_tabs | `"<script" not in t` | `one_live_script(t)` | (i) | run page |
| test_web_running.py::test_r103_r114_limits_and_readonly | `<script` banned; `"script-src" not in csp` | `one_live_script(t)`; csp ends with `ADD` | (i) | run pages |
| test_web_settings_personal.py::test_no_script_no_inline_style | `"<script" not in r.text` for `/settings` and `/`; csp ends with `...base-uri 'none'` | `live_rules(r.text, csp)`; csp (without `ADD`) ends the same | (i) | `/` (red); `/settings` keeps the old rule |
| test_web_status_squares_3.py::test_ss05_constraints | `"<script" not in text` | `live_rules(text)` | (i) | run pages; the downstream stage and `/settings` keep the old rule |
| test_web_upload.py::test_tc016_* | `"<script" not in r.text`; csp == launch csp | `live_rules(r.text, csp)`; csp without `ADD` == launch csp | (i) | `/upload/<batch>` on the way; `/upload` form unchanged |
| test_web_upload.py::test_tc078_it_reloads_itself_while_files_are_on_the_way | meta refresh present, no `<script` | `<noscript>` + meta, `one_live_script` | (i) | `/upload/<batch>` on the way |
| test_web_upload.py::test_tc124_to_tc126_* | `"<script" not in text.lower()` | `live_rules(text)` | (i) | `/upload/<batch>` on the way (red); `/upload`, `/upload?lang=en` keep the old rule |
| test_web_v2_skeleton.py::test_v15_constraints_hold | `"<script" not in t` | `one_live_script(t)` | (i) | `/`, run page |
| test_results_files.py::test_tc037_*, test_tc027_044_* | `"<script" not in t` | `one_live_script(t)` / `live_rules(t)` | (i) | results pages |
| test_results_files.py::test_tc039_style_and_csp_are_those_of_the_base | csp of every listed page == the first | each == base (+ `ADD` where the page reloads itself) | (i) | `/`, outputs, waiting download; settings and usage unchanged |
| test_su_usd.py::test_tc072_run_page_limits | `"<script" not in t` | `one_live_script(t)` | (i) | run pages |
| test_clean_page.py::test_a_board_without_any_clean_request_is_byte_for_byte_what_it_was | golden hash of the whole board | golden hash of the board with the live additions taken off (`strip_live`) | meaning kept, see note 1 | `/` |
| test_clean_page.py::test_no_inline_style_*_same_headers_as_a_launch_page | each header == the confirmation page's | CSP of the board == the confirmation page's + `ADD` | (ii)/(i) | board (in scope); `/c/` pages unchanged |
| test_web_live_sync.py | (new) | | | |
| package-data pins: test_guidance.py::test_tc406_*, test_module_sources.py::test_package_data_gets_exactly_one_more_glob | `"data/*.json", "data/*.json.gz"]` | `..., "data/*.js"]` | R-E | `pyproject.toml` |

Note 1: the golden-hash test is neither (i) nor (ii); it is about the rest of the page, so the helper that hashes the page takes the live additions off first. The lead should confirm.

Tests of list (c) (R2: compare with `/`): `test_web_run_log.py` line 213, `test_web_downstream.py`, `test_clean_page.py` are retargeted as above; `test_results_files.py` 703-707, `test_web_figures.py` 470-474 and `test_web_upload.py` 339 are the tc039, finished_csp and tc016 rows.

Tests whose red assertion was about an out-of-scope page: none. For the four the lead named: `test_no_script_no_inline_style` was red on `/` (the board); `test_tc034_*` on the board run page (`/?run=..&tab=tasks|logs`); `test_tc046_no_other_page_has_frame_src` on the waiting `/run/preview` page; `test_tc124_to_tc126_*` on `/upload/<batch>` with files on the way. `/settings`, `/run/log`, ready previews and the upload form pass unchanged.

## Other code changes the tests forced

- `scripts/dev/check_live_sync.py` imports `free_port` from `ui_check.py` (`test_no_duplicate_defs`).
- `latest_release` has no new parameter (its signature is pinned): it asks `web_live.looking()`.
- The version of a region ignores the per-login form tokens (`test_site_disconnect_ux` compares two logins byte for byte).

## Browser checks (`scripts/dev/check_live_sync.py`, Chromium 1248 through Playwright 1.64, WSL)

Run `python3 scripts/dev/check_live_sync.py --platform-python ~/abf-venv/bin/python`. All 16 passed:

| case | result |
|---|---|
| TC-001 | pass: badge went from 執行中 to the succeeded one in 2.3 s |
| TC-004 | pass: marks kept on the unchanged tools row and foot, not on the changed run list |
| TC-005 | pass: 10 version asks and 0 content asks in 22 s |
| TC-006 | pass: scroll 120 -> 120, `window` mark kept, page loads 1 |
| TC-007 | pass: gaps 2.03 s (nine in a row) |
| TC-008 | pass: 0 asks while hidden, first ask 0.00 s after coming back (visibility is emulated by overriding `document.hidden`: headless Chromium has no tab strip) |
| TC-009 | pass: gaps while failing 4.0, 8.0, 16.0, 30.0 s; after recovery 2.1, 2.0, 2.0 s |
| TC-011 | pass: ended at `/login`, page loads 1 -> 2 -> 2 |
| TC-014 | pass: see R-D |
| TC-017 | pass: the typed box and the focus stayed |
| TC-018 | pass: the untouched parameter step changed while the touched step stayed (a first run failed: a drop-down with no marked option counted as "changed"; fixed in `live.js`) |
| TC-019 | pass: scroll 60 -> 60, focus kept |
| TC-032 | pass: the download `a.txt` started |
| TC-034 | pass: 2 page loads in 35 s with scripts off, 0 live asks |
| TC-035 | pass: 1 page load in 35 s with scripts on |
| TC-040 | pass: 32 requests, 28 to the live routes, all same-origin GET |

(TC-040 was re-run alone after the script changed it to a launch page nobody had answered; the other fifteen are from the full run.) Playwright's string-waiting calls evaluate strings and the pages forbid `unsafe-eval`, so the script polls with `page.evaluate` (`until`); a plain `time.sleep` held back the page events and read zero, so waits go through `page.wait_for_timeout` (`nap`).

## Known limits and things not proven

- `live.js` not loadable while scripts are on: no fallback (Q3), written in PLATFORM.md.
- The Outputs listing not asked for yet: one full page load when a run turns succeeded (R-F).
- A `<details>` the person opened is closed again when its region is replaced (open state is not a form control).
- TC-063 is checked by removing the additions (noscript, script tag, body attributes) and looking at the head and body, not against a rendering of `origin/v3` (CI has none).
- TC-062 checks the dependency lines and the new files by text.
- TC-067 checks that no tool name contains `live` or `sync`; it does not compare the whole tool list with `origin/v3` (`platform/tests/mcp/` holds that snapshot and passes).

## Results of the platform tests

See the end of this file (filled in after the last run).
