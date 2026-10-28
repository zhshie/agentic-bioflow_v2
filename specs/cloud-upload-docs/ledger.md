# 雲端上傳與費用的文件更新 progress ledger

- [x] OPERATIONS: cost sentence replaced; new "Datasets in the lab's bucket" subsection (6 points); still 6 `##` headings.
- [x] PLATFORM "Input data": C-6 sentence replaced with current state and pointer to OPERATIONS.
- [x] TESTING cloud-upload section: intro and steps 1-4 use `abf-platform dataset ...`; step 4 reads the OPERATIONS line (no command entry).
- [x] `platform/tests/test_cloud_upload_docs.py` (9 tests): RED commit, then GREEN.
- T10 evidence: `git diff --stat origin/v3...HEAD -- docs/CLOUD.md docs/INSTALL.md platform/abf_station/launch.py` is empty (no change to CLOUD.md, INSTALL.md, NO_BUCKET_PATH).
- PR note: the maintainer's words say `gsutil`; per ruling 2 the docs use `gcloud storage cp`.
