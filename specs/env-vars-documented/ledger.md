# 程式讀的每個 ABF_* 環境變數都要寫進 docs/；補齊缺漏並加測試防再犯 progress ledger

- [x] RED: `test_env_vars_documented.py` before docs: 4 failed, 3 passed (every_abf_variable..., deadline_table_covers_every_job_kind, two_station_timeouts..., station_uploads_is_explained...). Missing list in test 1: ABF_PLATFORM_DEADLINE_CLEAN, ABF_PLATFORM_DEADLINE_PUT_UPLOAD, ABF_PLATFORM_DEADLINE_READ_TASK_LOG, ABF_STATION_UPLOADS, ABF_STATION_PUT_TIMEOUT, ABF_STATION_GCB_SETTLE_SECONDS.
- [x] GREEN: docs/PLATFORM.md (3 table rows + tail of the "only the tests change" paragraph), docs/OPERATIONS.md (sentence appended to the end of point 6). Single file after: 7 passed.
- Evidence for "same folder": platform/tests/test_byte_channel_b.py:76,94-96 `World.set_uploads` sets ABF_STATION_UPLOADS to `aw.uploads`, and :195,377,636 call `jobs.enqueue_put_upload(..., aw.uploads, ...)` with that same folder. So the sentence says the agent's folder is the platform's `uploads_root`.
- Not done on a v3 checkout: the two-branch comparison is covered by the RED run above (same test file, docs unchanged = HEAD of v3 docs).
- Note: `git diff` shows 2 deleted lines only because the appended text sits on the same line as the old sentence (tail append, no old words removed).
