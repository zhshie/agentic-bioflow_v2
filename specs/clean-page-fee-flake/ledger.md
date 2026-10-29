# test_clean_page 隨機十六進位 id 碰巧含 fee 時誤判；比對前先遮罩 id progress ledger

- [x] RED (88e129af): `test_a_request_id_that_contains_fee_does_not_fail_the_wording_check` failed at `assert word not in words` (test_clean_page.py:464) with `_words_of` unmasked; other 37 passed.
- [x] GREEN: `_words_of` masks `[0-9a-f]{32,}` -> X; test_clean_page.py 38 passed. Word list, BASE_STYLE assertion unchanged; no skip/xfail/retry; only platform/tests/test_clean_page.py changed (plus this ledger).
- Scan line: no other test found with all-a-f short-word `not in` on text containing random hex (per plan's grep; not a full audit).
- origin/v3 vs branch: before the change 28 passed on the bee02b6d base; now 38 passed (10 new cases).
