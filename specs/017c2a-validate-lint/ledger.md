# 組合管線驗證：可選 nf-core lint（站台工作） progress ledger

- [x] jobs.py / store.py: kind `lint_pipeline` (eleventh), deadline 300, `ABF_PLATFORM_DEADLINE_LINT_PIPELINE`, `enqueue_lint_pipeline`, `clean_result` branch, jobs CHECK + migration.
- [x] pipeline_lint.py (new), actions/pipelines.py (`_project_files`, `validate_pipeline(lint=, compute_env=)`, `get_validation` collects).
- [x] abf_station/lint.py (new) and handlers.py registration.
- [x] Tests: test_pipeline_lint.py (TC-001..018, 043, 050..069, 080, 081, 083, 101..103, 106..108), test_station_lint.py (TC-020..042, 044, 104, 105), TC-082/085 in test_pipelines_validation.py, TC-109 in test_validate.py, TC-100 in test_pipeline_launch.py. TC-084 by the unchanged test_pipeline_export tests. TC-120/122 by no_second_run_state_test.sh and test_scope.py.
- [x] docs/PLATFORM.md and docs/TESTING.md (manual section).
- Manual, not verified here: TC-045, TC-046, TC-047 (real nf-core on a real host) — 未驗證.
- Pinned tests whose assertions were extended for the new kind (count/list of kinds, slices, scans): test_byte_channel_a, test_byte_channel_b, test_nfcore_catalogue, test_station_clean, test_station_pipeline_files, test_pipelines_validation (scan allows "lint"), test_handlers_header, test_k8s_launch (gate tables and kinds digest skip lint_pipeline like read_run_file; schema digest strips the new CHECK entry so the base hash holds).
- Deviation: lint.py calls `site.run_fixed` through module-level `RUN`; it raises TimeoutError (not subprocess.TimeoutExpired) because `subprocess` may not appear outside site.py; any other exception is also reported as an error.
- Full-suite fix round: kind list/slice pins also in test_cleanup_confirm, test_cleanup_store, test_pipeline_files_queue, test_resume_scope (append lint_pipeline; no assertion weakened).

- Full-suite fix round 2: kind-list/CHECK pins in test_launch_platform, test_station_platform (two), test_cloud_cost (append lint_pipeline); test_web_nano4_path TC-043 digest strips the new CHECK entry like test_k8s_launch. No assertion weakened.
