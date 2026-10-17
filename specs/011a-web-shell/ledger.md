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

No other existing test was edited, deleted, skipped or loosened (TC-D05). One fix inside my own new tests during GREEN: `test_tch09_cost` counted the digit in `<h2>`; it now strips tags before looking for digits.

## Notes

- `docs/ROADMAP.md` still says the parity test "arrives with 011a"; that file is not mine to edit.
- No change to `actions/`, `jobs.py`, `mcp_server.py`, `store.py`, `hooks/`, `.claude/` (TC-N07, TC-K5).
