# Tasks: 004 onboarding proof

## S1 — proof record + setup_verify (TC-001–TC-011, TC-015)

- [x] T001 RED: `tests/setup_proof_test.sh` (TC-004–009, TC-011) and new/changed cases in `tests/setup_verify_only_test.sh` (TC-001–003, TC-010); see them fail
- [x] T002 `scripts/settings.sh` MACHINE_KEYS += proof_run; new `scripts/setup_proof.sh`; `scripts/setup_verify.sh` exit 3; GREEN
- [x] T003 `docs/SETTINGS.md` row + machine-file list (TC-015)

## S2 — setup.md routing (TC-012–TC-014)

- [x] T004 RED: `tests/setup_doc_test.sh`
- [x] T005 `commands/setup.md` T27 / Repair / step 8 / step 9 wording; GREEN; `command_layer_is_site_neutral.sh` stays green

## Close

- [ ] T006 full suite in WSL (TC-016)
- [ ] T007 independent acceptance
