# ledger web-confirm-plain


- [x] Tests first: `platform/tests/test_web_confirm_plain.py` (TC-001..026, 029, 008, 017-020), RED commit then GREEN.
- [x] C1 `confirm.facts` + `actions.request_facts` (WEB_ONLY in `test_web_parity.py`); C2/C4/C5 `web.py` `state_page` (plain `<dl class="fields plain">`, `<details>`, `?lang=en`); C3 `overflow-wrap:anywhere` on `pre` in `web_board.py`.
- [x] TC-007, TC-016, TC-033 are manual (`docs/TESTING.md`); not done by the executor.

## Changed existing assertions (string swaps only)
- `platform/tests/test_web_board.py::test_tcs45_confirm_pages_share_the_style`:
  old `assert c.get("/c/%s?lang=en" % rid).text == r.text`
  new `assert style_of(c.get("/c/%s?lang=en" % rid).text) == style_of(r.text)`
  why: the plan (C5) gives the confirmation page English labels under `?lang=en`, so the whole page can no longer equal the Chinese one; the point of the test (one shared stylesheet) is kept.

## Fix round (verifier, 2026-10-19)
- TC-007, TC-016, TC-033: the manual steps now exist in `docs/TESTING.md`, section "The confirmation page, plain words first (web-confirm-plain)" (steps 1-4 = TC-007, step 5 = TC-016, step 6 = TC-033). A person still has to do them; the executor did not.
- Correction to "string swaps only" above: the one changed assertion in `test_web_board.py::test_tcs45_confirm_pages_share_the_style` is NOT a pure string swap. It narrows a whole-page equality to the stylesheet alone, so TC-031 ("test_web_board.py unchanged") does not hold literally. The English page content is covered by `test_web_confirm_plain.py` (TC-021). The maintainer or verifier must accept it (TESTING.md step 6).
