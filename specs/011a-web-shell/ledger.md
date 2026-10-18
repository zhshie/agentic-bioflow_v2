# 011a: web shell, three panes, read-only progress ledger

## Tasks

- [x] RED `a3dee77`: `platform/tests/test_web_board.py` (TC-H01 to H15, H17, H07a, K1, N01 to N06) and `platform/tests/test_web_parity.py` (TC-H16a to H16h); TC-G04 rewritten.
- [x] GREEN: `platform/abf_platform/web_board.py` (pure rendering, `STYLE`, `stage_of`), `GET /` in `web.py` (login redirect, caller always passed, 404 without echo), CSP `style-src` is the stylesheet's sha256.
- [x] Docs: `docs/PLATFORM.md`, `CHANGELOG.md`, `web.py` header, `docs/TESTING.md` (visual check and ledger review).
- [ ] Manual (verifier): TC-V01 to V05 screenshots; TC-D01 to D09, N07, K5 by reading this ledger and the diff.

## Rewritten pins (TC-D01 to TC-D05)

| Pin | Old | New | Reason |
|---|---|---|---|
| TC-G04 `test_confirm_page.py::test_tcg04_g05_g06_...` (TC-D01) | Test name `..._has_five_routes_...`; routes list is five (`/c/{rid}` GET and POST, `/login` GET and POST, `/logout` POST); the 404/405 loop starts with `/` | Name `..._has_six_routes_...`; routes list adds `("/", ("GET", "HEAD"))`; `/` removed from the 404/405 loop. Every other path in the loop is unchanged | Decision 2 adds exactly one route, `GET /`. `POST /` giving 405 and the six-route list are asserted again in `test_web_board.py::test_tch11_read_only` |
| Login dead-end page (TC-D02) | No test pinned the text "已登入 … 請回到 AI …". Login tests accept `status in (200, 303)` | Nothing in an old test changed. The login with no `next` now answers 303 to `/`; asserted new in `test_tch02_login_lands_on_root` | The dead-end page is replaced by the board (decision 2) |
| CSP string (TC-D03) | No test pinned the old string (`style-src 'unsafe-inline'`). `test_tcd13` only checks `script-src` or `default-src 'none'` is present, still true | Not changed. New: `test_tch13_csp_and_markup` pins the hash and the rest | Decision 7: stricter CSP. There was no old pin to rewrite |
| `docs/PLATFORM.md` wording (TC-D04) | No test pinned "its only web pages are the login and the confirmation page", "five routes" or "no web page but the login and the confirmation page" (searched `tests/*.sh`, `platform/tests/*.py`) | Text now says the board is a third page and the routes are six, with the CSP shown | Decision 10; nothing to rewrite in a test |

Found only by the full run (older tests that pinned the old page; each change is the smallest that keeps the test's purpose):

| Pin | Old | New | Reason |
|---|---|---|---|
| `test_owner_binding.py` tc008, tc011, tc037, tc039, tc067 (login status) | `w.login(...).status_code == 200` (the dead-end "已登入" page) | `== 303` | Decision 2: a login with no `next` redirects to `/` |
| `test_owner_binding.py` tc011 | `/` was in the loop of paths that must be 404 | `/` taken out of the loop; added: `GET /` is 200 and does not contain the other user's request id | `/` is now the board; the test's point (the web shows no list of requests, never somebody else's) is kept |
| `test_owner_binding.py` tc068 | routes set `{/login, /logout, /c/{rid}}` | adds `/` | Decision 2: the sixth route |
| `test_review_fixes_2.py` r3 | `w.login(c, "ann").status_code == 200` after 10 failures | `== 303` | Same as the first row; the test still shows a right password works after wrong ones |
| `test_launch_static.py` tc069/tc070 | (exemption added in round 1 for the label `NCHC SU`) | restored exactly as before 011a | Plan ruling option B: the label is the site-neutral `SU —`, so no exemption is needed |

No other existing test was edited, deleted, skipped or loosened (TC-D05). One fix inside my own new tests during GREEN: `test_tch09_cost` counted the digit in `<h2>`; it now strips tags before looking for digits.

## Notes

- `docs/ROADMAP.md` still says the parity test "arrives with 011a"; that file is not mine to edit.
- No change to `actions/`, `jobs.py`, `mcp_server.py`, `store.py`, `hooks/`, `.claude/` (TC-N07, TC-K5).
- Round 2 (plan ruling option B): cost label `SU —` / `雲端 —` (TC-H09b, now also asserts no "NCHC" in page or `web_board.py`); `test_tch21_stage_strip_and_bodies` now asserts both times and each count paired with its state (TC-H21c); the tc069/tc070 exemption is removed.
- Round 2 fix: docs/TESTING.md step 1 (TC-V01) now says "SU —" to match the page.

## Merge of v3 (#126 009i OAuth, #128 same-origin referrer and header middleware)

Resolved as the union; nothing loosened from either side.

- `web.py`: routes = `/` + 009c's five + `/consent/{rid}` (GET, POST) + the SDK's OAuth routes; the middlewares `RegisterBodyCap`, `RegisterRateCap` and `add_headers` of v3 are kept, so `/` (and its framework 404/405) carry the same headers as every page (same-origin referrer, the CSP with the stylesheet hash). The consent page renders through `_page`, which renders through `web_board.document` (one stylesheet, one hashed `style-src`); v3's second inline stylesheet is gone. `_page` keeps 009i's `form_action` parameter (the consent page adds the connector's origin to `form-action`). Login: no `next` goes to `/`; `next` allows `/c/<hex>` and `/consent/<hex>`.
- Tests: `test_confirm_page.py` TC-G04 and `test_owner_binding.py` tc068 route sets are the union (011a's `/` added to 009i's sets; `/` leaves the "must be 404" loop as before). `test_web_parity.py`: `ConnectorCaller` and `form_is_trusted` (new public names from 009i) are INTERNAL (MCP side only, the web never calls them); the OAuth web routes are not actions, so WEB_ONLY gets no entry.
- Docs: CHANGELOG, `docs/PLATFORM.md` (route sentence is the union, the CSP sentence kept and told that the consent page adds one `form-action` origin), `docs/TESTING.md` (both sections kept).
- `test_web_board.py` TC-H11 (`test_tch11_read_only`): its pinned route list now also holds the 009i OAuth/consent routes (same union as TC-G04); the read-only assertions (one form, one button, POST / is 405) are unchanged.

## Layout B redo (plan "Layout redo", L1 to L9, rulings B1 to B6, C1 to C6)

- [x] RED `3429979`: `test_web_board.py` rewritten for the new markup, plus TC-L01 to L44 (L-numbers below), TC-H12d, TC-N08 to N11.
- [x] GREEN: `web_board.py` redone (top bar, 232/1fr/272 grid, stage cells `is-done`/`is-current`/`is-later`, whole-block history items, one string table `STRINGS` zh/en, `render_not_found`); `web.py` board route reads `lang`, reads `failure_reason` through `get_run(caller=...)` for the failed items shown (at most 100), and answers the 404 through `render_not_found`.
- [x] Docs: CHANGELOG, `docs/PLATFORM.md` (right column and the switch), `docs/TESTING.md` (visual check TC-V06 to TC-V10), `web.py` header.
- [ ] Manual (verifier): TC-V06 to V10 screenshots (wide, <900 px, zh and en); TC-D10, TC-D11 by this ledger and the diff.

### Test assertions changed for the new markup (TC-D10); none deleted without a replacement

| Old test and assertion | New | Reason |
|---|---|---|
| `test_tch01b_h20_h21a_three_panes`: page contains "本月費用", "專案與分析（011b）尚未開放", "設定（尚未開放）", the user name | `test_tcl02_h21a_three_panes`: no "本月費用", "011b" or "尚未開放" anywhere; cost line "本月 SU — · 雲端 —"; each run a link to `/?run=<id>`; "之後開放" outside every link; settings grey; one form | B1, B4 replace the wording; TC-L02, L05, L06. The user name moved to the top bar (asserted in `test_tcl01_top_bar`) |
| `test_tch20a_newest_first`: `text.split("本月費用")[0]` was the left column | `pane(text, "left")` | the cost heading is gone; columns are found by `data-pane` |
| `test_tch21_stage_strip_and_bodies`: stage order by `stage=` index, `→` between cells, counts as `label : n` in English words | split into `test_tch21_stage_bodies` (times verbatim, count label paired with number, reason, placeholders), `test_tcl07_to_l13_stage_strip` (five cells, `is-*` classes, `aria-current`), `test_tcl14_l15_l16_middle` (badge, seven cells in C6 order, prev/next links) | L3, B2, C6: no arrows between cells, count labels are the C6 Chinese words |
| `test_tch22_groups_and_counts`: five groups in stage order, "3" not in the running head | `test_tch22_l19_l20_groups_and_counts`: groups running, results, later; heads exactly "執行中（4）" and "結果（3）"; no 送出/下游/完成 group; failed and lost items under running | B5, C1 |
| `test_tch08_states_readable_without_colour`: `state-*` class on a `<span>` followed by the label | `test_tch08_l21_states_readable_without_colour`: each of the four right-column items is one link with the `state-*` class, "symbol label" text and `href=/?run=`; four distinct classes | L4, L5, TC-L21 |
| `test_tch09_cost`: two lines, "雲端 —" before the first group | one line exactly "本月 SU — · 雲端 —" before any group, no link, no number, no "NCHC", no "本月費用" | B1, option B, TC-L17, L18 |
| `test_tch19_long_lists`: `split("本月費用")` into left/right | `pane(t, ...)`; same counts (100 shown, "還有 150 筆" in both columns) | same reason as `test_tch20a` |
| `group_head` helper | reads the right column by `data-pane` | same |

Unchanged and still passing: H01a, H02, H03, H04, H05, H06, H07, H08 (progress), H10, H11, H12, H13, H14, H15, H17, H18, K1, N02, N04, N05 (their markup needles still exist: `rel="prev"`, `data-current`, "還沒有", `<progress>`).
`test_launch_static.py` tc069/tc070 are untouched.

Fix round (verifier, TC-L44): `test_tcl44_no_external_url_script_or_style_attribute` now creates a second user "bob" with no runs and checks the empty-state page (`/`, `/?lang=en`, `/?run=nope`) with the same three checks (no http(s) URL, no `<script`, no `style=` or `on*=`), replacing the stub `empty = login(...)` / `assert empty`. Test-only change; product code untouched.

## Web design v1 redo (plan "REDO per web design v1": G0 to G10, rulings R1 to R7)

- [x] G0 `24cd5fb`: plain merge of `origin/v3` (no rebase, no force). One conflict, `docs/PLATFORM.md` ("What it does not do"): kept v3's text (resume/relaunch asked for by name, `head-<N>.sh`) and our "read-only board" wording. The test files auto-merged; keep-submissions, resume/relaunch and 013a tests are all still in.
- [x] RED `d35670b`: `platform/tests/test_web_board.py` rewritten to the DESIGN.md structure (TC-S01 to S49, TC-L, TC-H, TC-N rows), `test_web_parity.py` tables recomputed for v3.
- [x] GREEN: `web_board.py` redone (DESIGN.md tokens only, mast with the two cost lines, 272/fluid/320 grid, Now page, settings page, `render_settings`, Taipei time, `<details open>` groups), `web.py` adds `GET /settings`.

### OWED written out (TC-S06, TC-S07; rule R2; the list may only shrink)

OWED (an action with an MCP tool of the same name and no web route): `list_compute_envs`, `get_compute_env`, `list_agents`, `list_site_files`, `launch`, `cancel`, `forget`.
Since the v3 merge the MCP side also has the tools `resume` and `relaunch`; they call `request_resume` and `request_relaunch`, which with `request_forget` are in INTERNAL, as are `forget_check`, `keep_screen`, the `FORGET_*` words, `FORGETTABLE` and `RUN_NOT_FOUND`.

### JS spots of DESIGN.md that 011a does not build (TC-S09, G8)

DESIGN.md "Constraints" marks JS for: live updates (the Now page and the right column), client-side pipeline search, chat send/streaming, drag-and-drop upload, the MultiQC embed and the Studio iframe. In 011a only the first is on a screen of this slice: both the Now page and the right column refresh with `<meta http-equiv="refresh" content="15">` on `/` (no script, no `<script>` anywhere; TC-H13e pins it). The others belong to 012b, 014, 012c, 013 and 016.

### Test assertions changed for the design v1 markup (TC-D10); none deleted without a replacement

| Old assertion (layout B) | New | Reason |
|---|---|---|
| right column held the cost line `本月 SU — · 雲端 —` | `test_tcs03_s04_cost_readout`: two elements `SU —` and `雲端 NT$ —` (`Cloud NT$ —`) in the mast, no link, no `<progress>`, none in the panes | R1 |
| left heading `我的 run` over a list, `設定` grey, grid `232px 1fr 272px` | `現在` first, then `我的 run`, grey tools, `設定` a link to `/settings`; grid `272px minmax(0,1fr) 320px`, 1200 px and 900 px queries | G1, G2, R4, TC-S11 to S13 |
| groups were `<section><h3>` | `<details open><summary>`; counts row `▶ n`, `! n`, `✓ n` | R6, TC-L19, TC-S26 |
| item line 2 was `symbol label · key fact` (end time for succeeded, `—` for lost) | `symbol label done/total`, a `<progress>`, and for failed a reason line | R6 (the B3 rule is superseded), TC-S27 |
| middle with no run said `選一個 run` | the Now page with the cards 正在跑 and 需要注意 | G4, R3 |
| times verbatim ISO `2023-11-14T22:13:20Z` | `MM-DD HH:mm` Asia/Taipei | G7, TC-H21c, TC-S46 |
| stage cells had no mark | done cells start with `✓ ` | TC-S29 |
| `test_tn04` listed `/settings` as a 404 path | `/settings` taken out (it is a route now), `/cost` and `/setup` added | R4, TC-N04 |
| `test_tn05` expected the eight tools | the eleven tools of v3 (adds forget, resume, relaunch) | the merge; no tool is added by 011a |
| `test_tch16d` OWED is exactly six | TC-S06 (rule) and TC-S07 (the literal list above) | R2 |
| login redirect and `tn08` | unchanged | |

Unchanged and still passing: the confirmation page and consent tests (`test_confirm_page.py`, `test_oauth_consent.py` and the rest) pass as they were; `test_launch_static.py` tc069/tc070 are untouched.

### Older pins changed for `GET /settings` (TC-D01, TC-D10)

| Pin | Old | New | Reason |
|---|---|---|---|
| `test_confirm_page.py` TC-G04 | routes were the union of 009c, 009i and `GET /`; `/settings` in the must-be-404 loop | routes add `("/settings", ("GET", "HEAD"))`; `/settings` taken out of the 404 loop and `/cost` put in | R4: `GET /settings` is the seventh page route; the loop's point (nothing else exists) is kept |
| `test_owner_binding.py` tc068 | route paths were the union plus `/` | adds `/settings` | same |

### Decided: no Jev item on the settings page (R8; TC-D13, TC-K6)

`tests/jev_test.sh` TC-085 says nothing under `platform/` may mention jev (ADR 0007: Jev is optional and lives on the plugin side). So the settings page of 011a has no Jev item: the platform names no Jev anywhere, "密碼與金鑰" lists only 「AI 模型金鑰」. DESIGN.md's 「Jev 金鑰（選填）」 on screen 12 is dropped from 011a and left for the ADR 0009/0010 amendment. `tests/jev_test.sh` is not changed (no diff against v3); `grep -rli jev platform/` finds nothing; the test for TC-N14 builds the word by concatenation.

### Red number and succeeded items (R9; TC-S50, TC-S51)

The red number beside 「現在」 in the left pane is the count of failed plus lost runs, the same list the 「需要注意」 card is built from, computed on every request from `list_runs`; it is not shown when 0. TC-S51 already held after R6 (succeeded, lost and running items carry no time and no lone dash).

### Manual rows left to the verifier / developer-agent

TC-V02 to TC-V04, TC-V11 to TC-V18 (screenshots with Playwright, the detector, the Tab walk) and the ledger-review rows TC-D01 to TC-D13, TC-S07 to TC-S09, TC-N07, TC-K5 follow `docs/TESTING.md`. No schema, `actions/`, `jobs.py`, `mcp_server.py`, `store.py`, `hooks/` or `.claude/` file was changed (no migration needed: nothing stored).

### Fix round: TC-S31 had no test

`test_tcs31_no_other_platform_names` in `platform/tests/test_web_board.py` reads `/`, `/?lang=en`, `/?run=<id>`, `/settings` and `/settings?lang=en` (the style sheet is inline, so it is inside each page) and fails if any names the platforms ADR 0004 replaces (case-insensitive; the words are built by concatenation so they stay out of the sources). The implementation already passed; the test was checked to fail when a forbidden word is injected into the page. No code under `platform/abf_platform/` changed.

### Fix round 2: TC-D12 and TC-D13 manual steps

`docs/TESTING.md` ("The web shell (011a)", Ledger review) now matches the confirmed rows. TC-D12: the empty-diff check covers `DESIGN.md` and `PRODUCT.md` only (plan.md is legitimately edited by the developer-agent after 637dc7c), plus the `git log` check that no subject starts with `RED:` or `GREEN:`. TC-D13: a new step reads this ledger's Jev decision, runs `git diff origin/v3...HEAD -- tests/jev_test.sh` and `grep -rli jev platform/`, and tells the reader to clear `platform/tests/__pycache__` first. Documentation only; no code changed.

### Fix round 3: the OAuth consent page was not in TC-S45 and TC-H13d

`test_tch13_csp_and_markup` and `test_tcs45_confirm_pages_share_the_style` in `platform/tests/test_web_board.py` now also read a real `/consent/<id>` page (made the way `test_oauth_consent.py` does, through `oauth_harness.Rig`). They check its CSP `style-src` sha256 against its one inline stylesheet, that it is the same stylesheet as `/`, and that it has no `style=`, `<script`, `on*=` or external address. The implementation already passed; both tests were seen to fail when the consent page's stylesheet was temporarily changed (the change was reverted, not committed). No code under `platform/abf_platform/` changed.
