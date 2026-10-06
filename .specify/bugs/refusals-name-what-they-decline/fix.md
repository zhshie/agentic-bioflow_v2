# Fix: refusals-name-what-they-decline

- **Branch**: `fix/user-folder-audit2`
- **Changed**: `scripts/settings.sh` (`refuse_unwritable_mode`, three `use_root` refusals, `cloud_sync_caution`), `scripts/detect_conditions.sh` (no-jq and msys-no-WSL messages), `tests/settings_test.sh`, `tests/conditions_matrix_test.sh`
- **Approach**: each refusal now carries one `What is refused is ...` sentence naming a folder, a shell or a capability. The synced-folder caution no longer calls the folder the token's "intended home"; it says a synced folder is accepted for the root but is a poor place for a token, the same reading as the permission refusal.
- **Red -> green**: 9 new assertions failed first (7 in settings_test, 2 in conditions_matrix_test), all pass after (WSL).
