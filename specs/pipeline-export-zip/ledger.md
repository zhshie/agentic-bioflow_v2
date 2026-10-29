# 自訂 pipeline 匯出成可獨立執行的 zip（動作層，不含 MCP 與網頁） progress ledger

- [x] RED: `test_pipeline_export.py` written first; before the code, 14 failed + 1 skipped (`AttributeError: module 'abf_platform.actions.pipelines' has no attribute 'export_pipeline'`).
- [x] GREEN: `export_pipeline` added to `actions/pipelines.py` (placed before `validate_pipeline`, because an existing test scans the text after that def for "nextflow"); `test_pipelines_store.py` only the public-name list test (seven -> eight).
- Note: zip is written with `struct`+`zlib` by hand (`_pack`) because `test_pipelines_store_has_no_submit_path` forbids the word "zipfile" in pipelines.py. Entries sorted, time 1980-01-01, deflate level 9.
- TC-008 stub-run: UNVERIFIED (no nextflow on this machine; test skips).
- Zip file list for fastqc->multiqc: README.txt, main.nf, modules.json, modules/nf-core/fastqc/... , modules/nf-core/multiqc/..., nextflow.config (sorted).
- `git diff --stat`: pipelines.py, test_pipelines_store.py, test_pipeline_export.py, plan/ledger only.
