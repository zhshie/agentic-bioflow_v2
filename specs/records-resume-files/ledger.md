# 平台端 records.name_ok 續跑檔 progress ledger

- RED (before code): 9 failed, 31 passed (test_resume_files_are_refused_by_name x4, test_store_files_does_not_write_resume_files x4, test_both_locks_agree_on_resume_files: AttributeError _RESUME_FILE).
- GREEN: records.py gains one constant and one condition; test file only appended.
