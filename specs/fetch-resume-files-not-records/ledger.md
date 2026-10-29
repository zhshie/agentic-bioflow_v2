# 站台 fetch 不准把續跑檔當紀錄讀回 progress ledger

- [x] RED: 6 new parametrized cases of test_tc036_... failed on base (params/extra/head -2 and -10 were read back); old-name and ordinary-name cases passed on base (64 passed, 6 failed).
- [x] GREEN: fetch.py gets `_RESUME_FILE` constant and one `or` in the refusal condition; test_station_cancel.py 70 passed. `_NOT_RECORDS` untouched.
- Two-branch comparison: the ordinary/old-name cases (trace.txt, trace-3.txt, old fixed names) are in the new test file and passed on the unchanged base code at the RED commit, and pass again after the change.
