# 遠端同事的一次性臨時密碼（後端） progress ledger

- [x] RED: `platform/tests/test_temp_password.py` (TC-001..TC-078, TC-094/095, TC-099..TC-103, TC-110/111) and the doc cases in `test_onboarding_doc.py` (TC-079..TC-096); `check_flags` now takes `cli=` and knows `temporary` (the intended update of T26).
- [x] GREEN store: `users.temp_until REAL` in `TOKEN_SCHEMA` plus the same-shaped migration in `_migrate_tokens`; `TEMP_PASSWORD_SECONDS = 72 * 3600`; `issue_temporary_password`, `change_web_password`; `set_web_password` clears `temp_until`; `check_web_password(..., now=None)` returns `must_change`; `web_session_user(..., allow_must_change=False)` is fail-closed for a temporary session.
- [x] GREEN cli: `abf-platform user passwd <name> --temporary` (real terminal only, four output lines, no prompt); the path without the flag is unchanged.
- [x] GREEN docs: ONBOARDING section 2 and the welcome letter, OPERATIONS command table, PLATFORM login paragraph.

## Evidence
- Opening the tokens.db of the platform: the test uses `store.connect_tokens` (TC-056).
- OUT OF PLAN (the plan said no existing assertion would go red; two did): the full suite showed that `test_pat.py::test_tcf03_f04_*` and `test_web_actions.py::test_tc063_no_schema_change` pin the column list of `tokens.users`. Each got the one new name `temp_until` appended to its expected list, nothing else changed. The developer-agent should confirm this is wanted.
- Python used by the quick runs: 3.10.6, sqlite 3.37.2 (WSL Ubuntu). The Windows `python` here is 2.7, not used for tests.
- `git diff --stat -- platform/abf_platform/web.py` is empty (web.py untouched); `actions/`, `guidance.py`, `mcp_server.py`, the constitution, ADR 0006, INSTALL.md and TESTING.md untouched.
- The path of `cmd_user_passwd` without `--temporary`: the terminal check, the user check, the two `getpass` calls, the differ/exception messages and the success message are the original lines (only the docstring and the added `--temporary` branches differ).
- Constitution checks run green: `tests/credentials_stay_in_settings_test.sh`, `tests/no_hardcoded_paths.sh`, `tests/no_per_pipeline_config.sh`, `tests/command_layer_is_site_neutral.sh`, `tests/platform_storage_doc_test.sh`.
- Known, not ours: `test_station_envs.py::test_tc040_*` and `::test_nano4_*` fail in a quick run with `No module named 'starlette'` (a child process uses the system python); they fail the same way on the RED commit.
- Merge note for the PR: the PR waits for the constitution amendment (`constitution-temp-password`); change-password lives in the store layer on purpose (ruling 2).
