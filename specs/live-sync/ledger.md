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
| test_web_fixes_1.py::test_f08_constraints_hold | `"<script" not in t and "style=" not in t and 'rel="stylesheet"' not in t and t.count("<style>") == 1` | `one_live_script(t) and "style=" not in t and 'rel="stylesheet"' not in t and t.count("<style>") == 1` (final state; a first version lost the last clause to a comment, restored after acceptance) | (i) | run pages |
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
| test_web_status_squares_3.py::test_ss05_constraints | `"<script" not in text and " style=" not in text and not re.search(r"\son[a-z]+=", text) and text.count("<style>") == 1` | `live_rules(text) and " style=" not in text and not re.search(r"\son[a-z]+=", text) and text.count("<style>") == 1` (final state; the on-attribute and style-count clauses had been lost to a comment, restored) | (i) | run pages; the downstream stage and `/settings` run the old rule through `live_rules` (no meta refresh = no script, no `<noscript`, no `script-src`) |
| test_web_upload.py::test_tc016_* | `"<script" not in r.text`; csp == launch csp | `live_rules(r.text, csp)`; csp without `ADD` == launch csp | (i) | `/upload/<batch>` on the way; `/upload` form unchanged |
| test_web_upload.py::test_tc078_it_reloads_itself_while_files_are_on_the_way | meta refresh present, no `<script` | `<noscript>` + meta, `one_live_script` | (i) | `/upload/<batch>` on the way |
| test_web_upload.py::test_tc124_to_tc126_* | `"<script" not in text.lower()` | `live_rules(text)` | (i) | `/upload/<batch>` on the way (red); `/upload`, `/upload?lang=en` keep the old rule |
| test_web_v2_skeleton.py::test_v15_constraints_hold | `"<script" not in t` | `one_live_script(t)` | (i) | `/`, run page |
| test_results_files.py::test_tc037_*, test_tc027_044_* | `"<script" not in t` | `one_live_script(t)` / `live_rules(t)` | (i) | results pages |
| test_results_files.py::test_tc039_style_and_csp_are_those_of_the_base | csp of every listed page == the first | each == base (+ `ADD` where the page reloads itself) | (i) | `/`, outputs, waiting download; settings and usage unchanged |
| test_su_usd.py::test_tc072_run_page_limits | `"<script" not in t` | `one_live_script(t)` | (i) | run pages |
| test_clean_page.py::test_a_board_without_any_clean_request_is_byte_for_byte_what_it_was | golden hash of the whole board (`snap`) | the same golden hashes, of the board with the three additions of live-sync taken off (`snap_board`, used at this one place only; `snap` for the `/c/` confirmation pages is exactly as before and their hashes pass unchanged) | accepted by the lead | `/` |
| test_clean_page.py::test_no_inline_style_*_same_headers_as_a_launch_page | each header == the confirmation page's | CSP of the board == the confirmation page's + `ADD` | (ii)/(i) | board (in scope); `/c/` pages unchanged |
| test_temp_password.py::test_tc027_every_login_route_sends_a_temporary_session_to_the_password_page | the walk over every route of the app expects 303 `/welcome` for each, exempting `/login`, `/logout`, `/welcome`, `/authorize`, the `.well-known` paths and the three OAuth POST routes | the exempt list also has `/static/live.js` (public: the same bytes for everybody, TC-036); `/live/version` and `/live/content` are walked and answer a temporary login with 303 `/welcome` like every page | R-B (route pin) | every route |
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
| S3 | pass: another figure arrived between the version and the content; the page ended equal to a fresh load (`fig6, fig5, s3a, s3b, fig3, fig1, fig2`), no duplicate, 2 content asks |
| DIRTY | pass: a box still holding the person's text stayed; a box changed back was replaced |

After the acceptance round the whole script (18 cases) was run again from a clean platform: 18 of 18 pass. (A first run of the new cases failed TC-014 because the script itself published the S3 figures in several earlier cases; fixed in the script.)

(TC-040 was re-run alone after the script changed it to a launch page nobody had answered; the other fifteen are from the full run.) Playwright's string-waiting calls evaluate strings and the pages forbid `unsafe-eval`, so the script polls with `page.evaluate` (`until`); a plain `time.sleep` held back the page events and read zero, so waits go through `page.wait_for_timeout` (`nap`).

## Known limits and things not proven

- `live.js` not loadable while scripts are on: no fallback (Q3), written in PLATFORM.md.
- The Outputs listing not asked for yet: one full page load when a run turns succeeded (R-F).
- A `<details>` the person opened is closed again when its region is replaced (open state is not a form control).
- TC-063 is checked by removing the additions (noscript, script tag, body attributes) and looking at the head and body, not against a rendering of `origin/v3` (CI has none).
- TC-062 checks the dependency lines and the new files by text.
- TC-067 checks that no tool name contains `live` or `sync`; it does not compare the whole tool list with `origin/v3` (`platform/tests/mcp/` holds that snapshot and passes).

## Proofs done once with git (not tests: CI has no base to compare with, TC-055, TC-065)

- Merged `origin/v3` three times (c3588e92 with #403 and #404, then a4133ab6 with #405); conflicts in `web.py`, `web_finished.py`, `CHANGELOG.md`, `docs/PLATFORM.md`, `docs/TESTING.md` were resolved by hand. The downstream stage of #404 (Studio frame) is out of scope: `test_studio_embed.py::test_tc015_*` gained an assertion that it has no `<script`, no `data-live`, no `script-src`/`connect-src` and keeps `frame-src`.
- `git diff origin/v3...HEAD --name-only | grep -E "^(\.github/|hooks/|\.specify/memory/constitution|\.claude-plugin/plugin.json|platform/abf_station/)|confirm\.py|(^|/)store\.py"` prints only `platform/tests/test_chat_confirm.py` and `platform/tests/test_publish_figure_confirm.py` (their names end in `confirm.py`; they are tests, the route-table pins of R-B). `confirm.py` and `store.py` themselves, `.github/`, `hooks/`, the constitution, `plugin.json`, `platform/abf_station/`: not touched.
- `web_board.py` is not in `git diff origin/v3...HEAD --name-only` (a test of another feature requires it).
- `spec`-like files `plan.md`, `test-case.md`, `test-case-overview.md`: unchanged since the contract commit.
- No test I added or rewrote compares with a base (`merge-base`, `git diff`, `git show`, `pytest.skip`): checked by grep.

## After the acceptance review (lead's list A1-A11, S1-S3, N6, N7, dirty)

| item | test (platform/tests/test_web_live_sync.py unless named) | implementation |
|---|---|---|
| A1 | test_web_fixes_1.py::test_f08_constraints_hold, the `t.count("<style>") == 1` clause is back in force | tests only |
| A2 | test_web_status_squares_3.py::test_ss05_constraints, both clauses back in force; the whole loop (including downstream and `/settings`) runs `live_rules` | tests only |
| A3 | test_clean_page.py: `snap` is as it was; `snap_board` is used at the board line only; the `/c/` hashes are unchanged and pass | tests only |
| A4 | `test_tc016_the_launch_edit_and_upload_pages_have_regions_too` (`check_regions`: every control and every form is in exactly one region or is a container form; no overlap; fixed names) for the launch page (loading), the resume edit page (loading) and the upload progress page | `web_live._container` |
| A5 | `test_tc046_the_login_and_confirmation_pages_have_no_script_and_todays_policy`: the login page and the confirmation page of a real launch request (`/c/<id>`, both languages): no `<script`, no `<noscript`, CSP == the literal string | tests only |
| A6 | `test_tc044_tc046_*`, `test_tc044_welcome_consent_figure_diagram_and_ready_preview_pages_have_none`, `test_tc044_ready_preview_pages_have_no_script`: `/welcome`, `/consent/<id>`, `/c/<id>`, `/run/figure`, `/launch/diagram`, a ready picture page and a ready report page: no script, no `script-src`, no `connect-src` | tests only |
| A7 | `test_tc045_the_report_policy_is_unchanged` and `test_tc045_the_page_policies_are_unchanged` (two assertions that each hold alone; the report keeps its own `connect-src 'none'`) | tests only |
| A8 | `test_tc063_the_pages_are_the_pages_of_before_but_for_the_three_additions`: nine pages (board, running stage, results stage, Outputs tab, finished stage, English board, empty board, launch loading, launch plain) hashed after `strip_live` against digests made by origin/v3 a4133ab6 | `platform/tests/live_golden.py` |
| A9 | `test_tc061_a_look_at_a_page_that_did_not_change_is_answered_at_once_and_whole` (answer under 3 s, `content-length`, no streaming) | tests only |
| A10 | the header docstring of the test file says three real routes | tests only |
| A11 | this table and the rewritten-tests table above | |
| S1 | `test_s1_every_id_of_the_gallery_page_is_unique_and_is_made_of_the_figure_name` (five names, every `id` unique, `pick-<name>`, `del-<name>`, `form=` and `for=` match); `live.js` selects nothing by id | `web_finished._key` is the figure's own name |
| S2 (a) | `test_s2_a_page_asked_about_twice_is_read_once` | `web_live.layout` memory (16 pages, by sha1 of the text; `decorate` stores the final text with shifted offsets); `web._html` is async and parses in the thread pool; the looks parse in the thread pool |
| S2 (b) | `test_s2_the_floor_of_one_second_and_the_script_is_not_told_to_reload` (429 + `Retry-After: 1`, `{"s":"slow"}`, nothing run, another page or another route is another question, passes again after 1.5 s; `live.js` treats 429 as "ask again at the usual time") | `web.py` `too_soon`, `web_live.LOOK_FLOOR_SECONDS`; key = (login, route, page) |
| S2 (c) | `test_s2_the_memories_of_the_server_are_bounded`, `test_s2_the_reload_limit_still_holds_*` | `web_live.Recent` (cap 4096, oldest out) for both the 15-second memory and the floor |
| S3 | browser case `S3` of `scripts/dev/check_live_sync.py`: another figure arrives between the version and the content; the page ends equal to a fresh load, no duplicate, 2 content asks | `/live/content` returns `v` (the version of each region); `live.js` throws an answer away whose versions are not the planned ones and asks again at the next turn; after two such answers in a row it loads the page whole (a deviation from "limited to 15 s": the 15-second limit is the server's for its own reload answers; this reload is the script's own and needs two bad answers at least 2 s apart) |
| N6 | `test_n6_a_page_nested_too_deeply_goes_out_as_it_was` (3000 levels: the page is returned byte for byte, refresh as it was, no script) | `web_live.decorate` catches `RecursionError`; the looks answer "reload" (rate limited) |
| N7 (a) | `test_n7a_the_other_tabs_of_a_succeeded_run_are_not_reloaded_for_a_listing_nobody_asks_for` | `web.py read_outputs`: `would_queue` counts only on the Outputs tab |
| N7 (b) | `test_n7b_a_batch_whose_registration_fails_is_registered_once_per_page_load_not_per_look`: looks never register; the one real load tries once; the page that shows the failure has no script and no refresh, so nothing reloads it again. Today the registration is tried once per page load too, so the frequency is not higher. | no code change |
| dirty | browser case `DIRTY` (a box changed back is released and its region replaced; a box still holding the person's text stays) | `live.js`: the `dirty` set is gone; a control is touched only while it differs from the server's value (`defaultValue`, `defaultChecked`, a drop-down against the option it showed when it came) |

TC-063 golden: made with `git archive origin/v3 | tar -x -C /tmp/base3` (a4133ab6, before any live-sync code), `cp platform/tests/live_golden.py` and a three-line pytest that prints `board_digests(World(...))` and `launch_digests(...)` into `/tmp/base3/platform/tests/`, then `python -m pytest -s` there (twice, 70 s apart: the same digests). The scenario has fixed names, fixed times and a fixed clock; the launch time shown on the finished stage is set by the scenario (a first golden made at another minute differed: fixed).

A real defect found on the way: a figure's ids were made of a hash of its name; they are now the name itself. A helper edit during this round briefly corrupted `web_finished.py` (a search for `def _figure` hit `def _figures_row`); the file was restored from origin/v3 and the three changes reapplied; `git diff origin/v3 -- platform/abf_platform/web_finished.py` is 12 insertions, 4 deletions.

## Round 3: two tabs starving each other (blocking defect), and three low items

**The defect.** The 1-second floor answered 429 to a login that asked the same page again inside a second. The script asks every 2 seconds without any jitter, so two tabs of one login on one page kept a fixed phase: tab A (t = 0, 2, 4 ...) always got 200, tab B (t = 0.5, 2.5 ...) always got 429 and never updated.

**The fix.** Inside the floor the same (login, route, question) is given **its own last answer as it was** (status, body, headers; the page's handler is not run, nothing is parsed). `web_live.Recent` now keeps `(when, answer)` for this memory (`ANSWER_CAP` 256 entries, answers over `ANSWER_MAX_BYTES` 200 000 are not kept; oldest out first). The key contains the login's session id, so an answer is given only to the login that got it; only a 200 is kept, so a 401, a 303 or a 404 is never anyone's saved answer; a request without a live login goes straight to the old path (401, or 303 `/welcome` for a temporary login) and enters no memory. `live.js` still reads a 429 as "ask again later" (the server no longer sends it) and schedules every turn with 2 s plus or minus up to 250 ms of random (never under 0.5 s).

| item | RED/GREEN test | implementation |
|---|---|---|
| floor gives the last answer as it was | `test_s2_inside_the_floor_the_same_login_is_given_its_last_answer_as_it_was` (same status, body, headers; `render_board` not called; no job; another page is another question; a full second later it is made afresh) | `web.py looked`, `web_live.Recent` |
| two tabs | `test_s2_two_tabs_of_one_login_both_get_every_answer_and_both_see_a_change` (moved clock, A at 0, 1, 2 ..., B at 0.5, 1.5 ... six asks each, all 200 and ok; a change at 2.2 s is seen by both no later than the first ask after the floor) | same |
| other login | `test_s2_another_login_inside_the_floor_gets_its_own_answer_never_the_kept_one_of_another` (bob inside the floor of ann's question gets bob's mast, not ann's; a second login of ann gets its own CSRF tokens, disjoint from the first login's, and equal to its own page's; two asks without a login are a plain 401 each) | key contains the session id |
| S3 still holds with kept answers | `test_s3_an_old_answer_given_inside_the_floor_*` (the kept content carries the old `v`; it differs from the version the script plans for next, so the script throws it away; asked after the floor it matches) | `/live/content` `v`, `live.js` |
| browser: two tabs | `TWO-TABS`: both tabs of one login update after 1.3 s | `live.js` jitter |
| low 1: flooded memory | `test_s2_when_the_memory_is_flooded_the_oldest_page_loses_its_15_second_limit_and_that_is_accepted` (cap 20, thirty other would-ask pages inside the window: the oldest page is told to reload once more, then limited again) and `test_s2_the_reload_limit_holds_with_the_normal_memory_when_other_pages_ask` | `web_live.MEMORY_CAP` |
| low 2: the script's own reload | browser `S3B`: every content answer is already old when it arrives (a figure is published during each); 7 content asks, 2 page loads, the gap between the two loads 17.0 s (never under 15 s) | `live.js`: `lastGo` (a memory variable set when the page came) and `Date.now() - lastGo >= 15000` before the second bad answer in a row loads the page; otherwise it keeps throwing away and asking again |
| low 3 | this section and the `test_temp_password.py` row of the rewritten-tests table | |

**Choice for low 1 and why.** The memory of reloads is bounded (4096 entries) and the oldest entry goes first. I kept that and say so: a page pushed out of the memory inside its 15 seconds can be told to load whole once more, which is exactly one real page load (what a person pressing reload makes, and what the page did every 15 seconds before this feature); to push it out one login would have to make more than 4096 distinct would-ask pages inside 15 seconds, and any one of those asks costs at most one real page load too. The alternative (never evicting) would let a flood grow the memory without end. An entry older than 15 seconds is expired anyway, so evicting it loses nothing.

**Low 2: how it is done without sessionStorage.** The 15-second spacing counts from `lastGo = Date.now()` at the moment the page's script starts; a page loaded by a reload starts its own count, so two reloads of its own are always at least 15 seconds apart. No new field in `data-live` was needed.

**Browser checks after this round.** `scripts/dev/check_live_sync.py` has 20 cases (the 16 of the contract, `S3`, `S3B`, `DIRTY`, `TWO-TABS`).

## Round 4: the CI rules that scan the platform sources

Four existing tests (not edited) failed on CI because `web_live.py` used `threading` (`test_scope.py::test_tc071_*`, `test_cleanup_confirm.py::test_tc068_tc076_*`; the same word is banned by `test_aws_upload.py` and `test_azure_upload.py::test_no_cloud_library_and_no_station_word_in_platform_sources`). The layout memory had a `threading.Lock()` because `layout` ran in the thread pool and wrote the memory. Now the thread pool only does pure work: `web_live.layout` and `decorate_with_layout` keep nothing and return their result; the memory (`recall`, `remember`, `recall_page`, `remember_page`) is read and written only on the event loop, by `web._html` and `page_layout` after the thread has returned. No lock, no other synchronisation. The page memory is keyed by the text, the policy and `force`, and holds scripted pages only. (A first version wrote a literal NUL character into a cache key; the scan tests refused the source; it is a `|` now.)

## Results of the platform tests (WSL, `~/abf-venv`, no `-x`)

- Whole `platform/tests` on the branch before the last two merges: 8641 passed, 4 failed, 25 errors, 52 minutes. The 25 errors are the tests that need the pinned Nextflow (`test_nextflow_e2e`, `test_launch_nextflow`, `test_launch_e2e`, `test_pipeline_export`): not available here, not caused by this change. The 4 failures: `test_studio_embed.py::test_tc015_*` (the route pin, fixed afterwards) and `test_aws_upload.py::test_clean_work_is_taken_for_aws_since_aws_clean`, `test_azure_upload.py::test_clean_work_and_resume_still_refused_for_azure`, `test_byte_channel_a.py::test_tc076_tc077_*`: these three say "agent ... is offline" in a long run and pass on their own, on `origin/v3` and on this branch (138 passed each way, also after `test_web_live_sync.py`); I could not find the cause: unverified, the CI is the judge.
- After the last merge: `test_studio_embed`, `test_web_live_sync`, `test_web_downstream`, `test_web_figures`, `test_web_board`, `test_confirm_page`, `test_owner_binding` and the three above: all pass except the same three "agent offline" ones, which pass when run alone.
- Runs made before the lead's instruction about `ABF_STUDIO_CONFIG` did not set it (three whole-suite runs and several partial ones): `test_studio_remote.py::test_tc081` may have overwritten `~/.abf/studio.json` on this machine; I did not check.
