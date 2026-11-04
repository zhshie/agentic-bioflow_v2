# cb-T1 ledger

Base: origin/v3 62c91293. Pure test additions, so mutation proof replaces RED (RULES 5.3).

## New tests on unchanged code
```
....                                                                     [100%]
76 passed in 0.10s
```

## Mutation proof (each mutant applied to platform/abf_platform/common.py, test run, file restored; never committed)

### token_from_header compares scheme 'Bearer' case-sensitively
```
FAILED tests/test_common_untested.py::test_token_from_header_table[bearer abc-abc]
FAILED tests/test_common_untested.py::test_token_from_header_table[BEARER abc-abc]
FAILED tests/test_common_untested.py::test_token_from_header_table[BeArEr abc-abc]
3 failed, 73 passed in 0.16s
```

### token_from_header Basic accepts any user, not only @token
```
FAILED tests/test_common_untested.py::test_token_from_header_table[Basic c29tZW9uZTp4eXo=-None]
FAILED tests/test_common_untested.py::test_token_from_header_table[Basic Onh5eg==-None]
2 failed, 74 passed in 0.14s
```

### _seconds_from_env returns non-positive values (drops the > 0 fallback)
```
E         comparison failed
E         comparison failed
E         comparison failed
E         comparison failed
E         comparison failed
FAILED tests/test_common_untested.py::test_offline_after_seconds_reads_the_env_value_or_falls_back[-5-60.0]
FAILED tests/test_common_untested.py::test_offline_after_seconds_reads_the_env_value_or_falls_back[-0.1-60.0]
FAILED tests/test_common_untested.py::test_offline_after_seconds_reads_the_env_value_or_falls_back[0-60.0]
FAILED tests/test_common_untested.py::test_offline_after_seconds_reads_the_env_value_or_falls_back[0.0-60.0]
FAILED tests/test_common_untested.py::test_offline_after_seconds_reads_the_env_value_or_falls_back[nan-60.0]
FAILED tests/test_common_untested.py::test_offline_after_seconds_is_always_positive
6 failed, 70 passed in 0.14s
```

### offline_after_seconds uses 2 beats instead of 3
```
E         comparison failed
E         comparison failed
E         comparison failed
15 failed, 61 passed in 0.19s
```

### run_failure_reason drops the control-character scrub
```
FAILED tests/test_common_untested.py::test_run_failure_reason_table[line1\nline2-other-line1 line2]
FAILED tests/test_common_untested.py::test_run_failure_reason_table[line1\r\n\r\nline2-None-line1 line2]
FAILED tests/test_common_untested.py::test_run_failure_reason_table[a\x1b\x00\x7fb-None-a b]
9 failed, 67 passed in 0.17s
```

### run_failure_reason drops the REASON_MAX_CHARS cut
```
FAILED tests/test_common_untested.py::test_run_failure_reason_cuts_at_the_limit
FAILED tests/test_common_untested.py::test_run_failure_reason_cuts_after_cleaning_not_before
2 failed, 74 passed in 0.12s
```

### run_failure_reason prefers the report over the message
```
FAILED tests/test_common_untested.py::test_run_failure_reason_table[boom-other-boom]
FAILED tests/test_common_untested.py::test_run_failure_reason_table[  boom  -other-boom]
FAILED tests/test_common_untested.py::test_run_failure_reason_table[line1\nline2-other-line1 line2]
3 failed, 73 passed in 0.14s
```

After restoring, git diff on common.py is empty; new file: 76 passed.
