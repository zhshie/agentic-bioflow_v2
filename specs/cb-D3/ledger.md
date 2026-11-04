# cb-D3 ledger

## RED (base 62c91293, tests only)
```
test_regex_anchor_fixes.py::test_plain_rejects_trailing_newline[txt\n]
test_regex_anchor_fixes.py::test_plain_rejects_trailing_newline[a.b\n]
test_regex_anchor_fixes.py::test_plain_rejects_trailing_newline[A_b-c\n]
test_regex_anchor_fixes.py::test_extensions_reject_trailing_newline[*.txt\n]
test_regex_anchor_fixes.py::test_extensions_reject_trailing_newline[*.{gz,txt\n}]
test_regex_anchor_fixes.py::test_extensions_reject_trailing_newline[*.fa\n]
test_regex_anchor_fixes.py::test_bucket_rejects_trailing_newline[abc\n]
test_regex_anchor_fixes.py::test_bucket_rejects_trailing_newline[a-b\n]
test_regex_anchor_fixes.py::test_bucket_rejects_trailing_newline[my-bucket\n]
test_regex_anchor_fixes.py::test_bucket_rejects_trailing_newline[aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n]
test_regex_anchor_fixes.py::test_bucket_rejects_trailing_newline[aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n]
test_regex_anchor_fixes.py::test_source_literal_ends_with_end_of_string_anchor[validate.py-_PLAIN]
test_regex_anchor_fixes.py::test_source_literal_ends_with_end_of_string_anchor[cloud_store.py-_BUCKET]
13 failed, 20 passed in 0.14s
```

13 new tests fail on unchanged code (trailing-newline acceptance + source literal); the 20 regression-shape tests pass on base, as intended.
