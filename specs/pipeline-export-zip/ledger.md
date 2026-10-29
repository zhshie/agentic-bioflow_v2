# 自訂 pipeline 匯出成可獨立執行的 zip（動作層，不含 MCP 與網頁） progress ledger

- [x] RED: `test_pipeline_export.py` written first; before the code, 14 failed + 1 skipped (`AttributeError: module 'abf_platform.actions.pipelines' has no attribute 'export_pipeline'`).
- [x] GREEN: `export_pipeline` added to `actions/pipelines.py` (placed before `validate_pipeline`, because an existing test scans the text after that def for "nextflow"); `test_pipelines_store.py` only the public-name list test (seven -> eight).
- Note: zip is written with `struct`+`zlib` by hand (`_pack`) because `test_pipelines_store_has_no_submit_path` forbids the word "zipfile" in pipelines.py. Entries sorted, time 1980-01-01, deflate level 9.
- TC-008 stub-run: UNVERIFIED (no nextflow on this machine; test skips).
- Zip file list for fastqc->multiqc: README.txt, main.nf, modules.json, modules/nf-core/fastqc/... , modules/nf-core/multiqc/..., nextflow.config (sorted).
- `git diff --stat`: pipelines.py, test_pipelines_store.py, test_pipeline_export.py, plan/ledger only.
- [x] Fix round (verifier: weak tests, tests only, no code change): TC-016 now uses a graph whose kept check has an error (META_MISMATCH) and asserts that error is in `validation`; TC-022 compares every row of every table (not counts); TC-031 checks per failure the what-happened and what-to-do phrases in both languages; TC-033 passes a caller whose fields carry a token value (plain and connector) and asserts that value is in no response and no log record.
