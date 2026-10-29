# Station clean_queue rejects names containing .. like the platform does progress ledger

- [x] RED (rules.py unchanged): `tests/test_station_queue_name.py` -> 8 failed, 14 passed (TC-001/002/003/004/005/013 red: clean_queue returned the string; TC-006..011, 014, 015 green).
- [x] GREEN: rules.py `clean_queue` condition gained `or ".." in value`. New file 22 passed; `test_launch_bundle.py` 233 passed (also passes on base, unchanged).
- diff --stat: rules.py 1 line, new test file only; no existing test touched. No migration needed.
- 後續: none seen (did not audit other rules.py functions, per ruling 1).
