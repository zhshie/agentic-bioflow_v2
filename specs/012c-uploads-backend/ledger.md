# 012c backend: pair FASTQ, register a Dataset, refuse web uploads over 2 GB progress ledger

- [x] tests first: `platform/tests/test_datasets.py` (TC-001 to TC-085, RED commit before the module existed)
- [x] `platform/abf_platform/actions/datasets.py`: `pair_fastq`, `draft_samplesheet`, `check_web_upload`, `register_dataset`, `list_datasets`, `get_dataset`; table `datasets` made by the module (store.py untouched)
- [x] focused run: `pytest tests/test_datasets.py` green; full suite: see the last commit
- [x] 2026-10-19 revision (re-land of PR #143): TC-064 keeps only the content check (no `origin/v3` diff); TC-066 removed from the automatic tests and moved to the verifier's review checklist; unused `git()` helper and `subprocess` import removed. Test-only change.
