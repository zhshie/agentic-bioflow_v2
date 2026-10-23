# su-followups progress ledger

- [x] su.py finds `su_rates.json` in the wheel (`abf_station/plugin/configs/sites`, located with `importlib.util.find_spec("abf_station")`), else the repo `configs/sites`. `RATES_PATH` stays a module name; `load_rates()` still reads it per call.
- [x] New `platform/tests/test_su_packaged.py` (TC-SF-01..06); the four loose tests of #171 tightened in `test_su_in_get_run.py` (TC-SF-10..18). No existing assertion removed.

## Proof that each new test goes red (TC-SF-19, TC-SF-20)

- `test_rates_found_from_the_packaged_plugin`: committed first (`RED:`) against the old `RATES_PATH` (repo path only). Red at `assert got["nano4"] is not None` (`load_rates()` gave None from an installed wheel). Green after the change.
- `test_packaged_copy_beats_the_repo_path`: red on the old code at `assert done.stdout.strip() != "999"` (it read the decoy at the repo path). Green after the change.
- `test_checkout_still_uses_repo_configs` and `test_no_rates_anywhere_is_unknown_without_a_path` pass on the old code too (they guard the fallback and the no-path message); not a red-first pair.
- TC-014 (`test_mcp_get_run_is_the_same_action`): made the MCP `get_run` tool drop the `su` key; the test went red (assertion `"su" in via`). First try (passing `platform_path=None`) stayed green, so that was not a real break.
- TC-083 (`_clean`): put a path, `/tmp/x.db`, into `NOT_STORED` and `RUN_NOT_ENDED`; went red in the TC-020, 022, 025/026 tests and in the rebuilt-run test.
- TC-073 (rebuilt run): made `run_su` turn "no usage rows" into an empty task list (su 0 instead of null); `test_a_run_without_usage_rows_stays_unknown` went red, via the real `rebuild.rebuild()` run.
- TC-048 (`test_site_of_run_without_a_platform_db_is_the_default`): made `site_of_run` return `nano4` when platform.db is missing or unreadable; it went red, at the `estimate_su` call.
