# Tasks: 006 machine identity

## S1 — identity in settings.sh (TC-001–TC-012)

- [ ] T001 RED: `tests/machine_identity_test.sh` (TC-001–TC-012), fake `uname` on PATH; see it fail
- [ ] T002 `scripts/settings.sh`: `MACHINE_ID_FILE`, `legacy_machine_id`, `stored_machine_id`, `machine_id`, `legacy_machine_file`, `resolve_machine_file`, `ensure_machine_id`; `set_setting` and `migrate_legacy` use them; GREEN
- [ ] T003 existing tests that touch machine files stay green (`settings_test`, `setup_proof_test`, `setup_verify_only_test`, `where_test`, `on_site_test`, `install_deps_test`), plus `portable_userland`, `no_hardcoded_paths`, `scripts_name_their_alternative`

## S2 — docs (TC-013)

- [ ] T004 `docs/SETTINGS.md`: identity rule, legacy fallback, one-time rename; `where.sh` label check

## Close

- [ ] T005 full suite in WSL (TC-014)
- [ ] T006 independent acceptance
