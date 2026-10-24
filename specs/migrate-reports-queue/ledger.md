# 搬舊設定時一併搬 reports/ 佇列（#23） progress ledger

- [x] migrate-reports-queue: migrate_legacy copies oldsettingsdir/reports/*.report to <root>/config/reports (no overwrite, 700/600, reports count + deletable list); docs/SETTINGS.md one sentence; tests/settings_migrate_reports_test.sh (TC-001..021).
