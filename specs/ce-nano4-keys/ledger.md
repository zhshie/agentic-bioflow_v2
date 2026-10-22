# 計算環境新增 modules／siteConfigVars／sitePipelines 三鍵 progress ledger

- [x] ce-nano4-keys: `modules` / `siteConfigVars` / `sitePipelines` added to `_SLURM_CONFIG` and validated in `_check_slurm` via `_check_site_keys` (`platform/abf_platform/compute_envs.py`); all errors listed at once, each naming its key (a bad value shown as one character at most). Tests: `platform/tests/test_station_envs.py` (TC-NK-01..28 incl. `test_tc024b_*`, `test_tc029b_*`).
- Migration check (R8): 不需要 migration. `compute_envs` stores the whole config in the single `config_json` column (`platform/abf_platform/store.py` table definition; `view()` returns `json.loads(row["config_json"])`), not field by field. Test `test_nano4_keys_live_in_config_json_only` confirms no new column.
- Decisions on the open questions of the overview: all three keys optional and absent when not given (no empty lists added); each sitePipelines item needs exactly pipeline/revision/module/home; empty lists are allowed; `..` path segments in a module are refused.

- [x] 2026-10-22 developer-agent：test-case.md TC-NK-23／24 的假金鑰字面值改寫成「AKIA 接 CANARYZZ99887766」的描述（測試語意不變；原字面值會被護欄 tests/credentials_stay_in_settings_test.sh 掃到，該護欄本來就不該放行任何檔案裡的金鑰形狀）。executor 的測試檔已用既有 KEY_ID 常數組字串。
