# upgrade-agents-reconnect-check progress ledger

- [x] RED 234f2f2: tests/platform_upgrade_test.sh failed on every TC (deploy/platform-upgrade.sh did not exist; 24 FAILED).
- [x] GREEN: deploy/platform-upgrade.sh (pull, install, snapshot of online agents + T0, restart, poll list_agents until last_contact_at > T0 or timeout; names the missing, exit 1). tests/platform_upgrade_test.sh all green.
- [x] docs/OPERATIONS.md: one sentence added after the Upgrade code block; the three original lines untouched.
- [x] tests/hosted_deploy_test.sh: only the want_list on line 283 gained `$D/platform-upgrade.sh`.
- [x] Scope: platform/, deploy/backup.sh, deploy/systemd untouched (TC-U28 checks it). No existing test weakened.
