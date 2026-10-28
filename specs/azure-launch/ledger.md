# 在 Azure Batch 上送出、追蹤與取消分析 progress ledger

- [x] RED 9923747: platform/tests/test_azure_launch.py (70 tests) and the planned assertion updates (test_azure_ce, test_aws_ce, test_gcb_ce, test_gcb_launch, test_aws_launch).
- [x] Code: compute_envs (Azure in PLATFORM_HOST_TYPES, CHECK_ONLY_TYPES empty, CLOUD_JOB_KINDS), jobs (refusal wording for Azure), abf_station/launch.py (Azure bundle), abf_station/azure_launch.py (new: launch, cancel), cancel.py, fetch.py, abf_launch build/cli (screen, messages).
- [x] Docs: PLATFORM.md (Launching on Azure Batch), SEQERA_PARITY.md, TESTING.md (manual steps, costs money), OPERATIONS.md.
- Not on the plan's list, changed anyway (minimal): `test_azure_ce.py::test_no_new_write_path_for_azure` (TC-148 of the old slice) pinned that launch_nextflow, cancel_run and pipeline_files are refused for Azure; they are allowed now, so the loop keeps only clean_work, put_upload, list_site_files. The verifier should judge this.
- Out of scope, seen: `azure_preflight._read_shape` uses an undefined `cred_path` in its no-`[default]` branch (NameError); `_check_environment` catches it and refuses with a plain message. The file is untouchable here.
