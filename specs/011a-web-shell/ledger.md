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
