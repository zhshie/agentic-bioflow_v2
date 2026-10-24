# 一間實驗室一台主機的部署包（systemd＋Caddy＋備份） progress ledger

- [x] tests/hosted_deploy_test.sh written first (RED, TC-001..079 static and backup-run checks).
- [x] deploy/systemd/abf-{serve,mcp,web}.service, deploy/env.example (US1).
- [x] deploy/Caddyfile.template: routes per the code (serve 8787: /trace, /user-info, /agent/*; mcp 8788: /mcp, protected-resource; web 8789: OAuth server, /consent, the rest) (US2).
- [x] deploy/backup.sh: SQLite .backup (python3 fallback), env overrides, signing key optional (US3). Note: a missing uploads/ or records/ folder is skipped with a line, not an error, because a fresh host has neither yet; tokens.db and platform.db missing still fail (decision 16 names only those two).
- [x] docs/OPERATIONS.md sections 2, 3, 4, 6 and "Hosting one lab"; docs/INSTALL.md two pointer sentences; docs/TESTING.md hosted-deploy section (US4).
- [x] Not touched: platform/ code, gate files, existing tests (US5).
