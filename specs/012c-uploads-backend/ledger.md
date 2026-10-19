# 012c backend: pair FASTQ, register a Dataset, refuse web uploads over 2 GB progress ledger

- [x] tests first: `platform/tests/test_datasets.py` (TC-001 to TC-085, RED commit before the module existed)
- [x] `platform/abf_platform/actions/datasets.py`: `pair_fastq`, `draft_samplesheet`, `check_web_upload`, `register_dataset`, `list_datasets`, `get_dataset`; table `datasets` made by the module (store.py untouched)
- [x] focused run: `pytest tests/test_datasets.py` green; full suite: see the last commit
