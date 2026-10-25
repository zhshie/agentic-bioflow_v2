# 搬舊設定時一併搬 reports/ 佇列（#23） progress ledger

- [x] migrate-reports-queue: migrate_legacy copies oldsettingsdir/reports/*.report to <root>/config/reports (no overwrite, 700/600, reports count + deletable list); docs/SETTINGS.md one sentence; tests/settings_migrate_reports_test.sh (TC-001..021).
- Full suite at 7109474: 124/125; only red is platform/tests/test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched (known env red, ruling 2026-10-25 07:35, fixed by onboarding-test-pinned-base); treated as green.
