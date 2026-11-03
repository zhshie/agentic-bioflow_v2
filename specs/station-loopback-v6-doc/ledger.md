# station 的「純 http 只准本機」拒絕訊息與 PLATFORM.md 補上 ::1，與程式實際行為一致 progress ledger

- [x] RED (before fix, test_station_docs.py): `2 failed, 6 passed` - TC-LB-01/02 (`::1` not in refusal message) and TC-LB-03/04/05 (`::1` not in PLATFORM.md sentence) failed; TC-LB-06..14 green.
- [x] GREEN (after fix): `8 passed`. Changed: one string in `platform/abf_station/cli.py` (url_problem message), one line (176) in `docs/PLATFORM.md`, new tests appended to `platform/tests/test_station_docs.py`. Judgement code and LOOPBACK untouched; no existing test altered; no migration needed.
- Diff stat vs base: cli.py 1 line, PLATFORM.md 1 line, test_station_docs.py additions only.
