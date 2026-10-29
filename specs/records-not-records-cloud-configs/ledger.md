# 平台端紀錄名單補上三個雲端設定檔 progress ledger

- RED (before fix): 7 failed, 17 passed (gcb/aws/azure name_ok + store_files, exact-eight set).
- GREEN: test_records_names.py 24 passed. diff: records.py line 20 only + new test file.
- Two-branch check: old behaviour of trace.txt/trace-3.txt/.nextflow.log.12 asserted True in the new file (passes at RED commit too = same on base).
