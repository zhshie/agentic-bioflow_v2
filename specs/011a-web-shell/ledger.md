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
