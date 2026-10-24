# cloud-upload ledger

- [x] RED: tests in platform/tests/test_cloud_upload.py (84 red before the code)
- [x] GREEN: platform/abf_platform/cloud_store.py (locations, prefix rule, one-line command, streaming core) and the keyword `destination=None` on the three functions in actions/datasets.py
- [x] docs/TESTING.md: "Datasets in a cloud bucket (cloud-upload)" section; says the end-to-end check waits for the byte-channel task
- Manual TCs (082, 083, 084, 085, 086, 093, 094) are for the verifier; no migration needed (datasets table untouched, cloud places live in the existing files_json path).
