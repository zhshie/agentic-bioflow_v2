# preflight 先 module load，檢查站台 pipeline 版本與唯讀快取 progress ledger

- [x] merge v3 into the branch (the worktree base lacked #157 / #162 / #155; verifier's note in test-case-overview.md)
- [x] `rules.clean_environment`: judges `modules`, `sitePipelines[].module`/`home` again (compute_envs rules, imported) and `singularityLibraryDir` (clean_root)
- [x] `compute_envs.snapshot`: new key `singularityLibraryDir` (only `NXF_SINGULARITY_LIBRARYDIR`, no other variable)
- [x] `handlers.preflight`: conditional `modules`, `site_pipeline`, `image_library`; `java`/`nextflow` get the `module load ... &&` prefix; abandon lists the applicable conditional checks as `unchecked`
- [x] FakeSite: fake `module` program (state/modules.allow), site pipeline folders and home variables; tests in `test_station_e2e.py` (`test_pf_*`)
- [x] docs: `docs/PLATFORM.md` (Preflight, three conditional checks), `docs/TESTING.md` (TC-047n: `library` renamed `image_library`)

## Migration

Not needed: a preflight answer is stored in the `compute_envs` JSON record that already exists; no table or column is added or changed.

## Existing assertions updated (the only one)

- `platform/tests/test_station_envs.py::test_tc_ls_23_24_26_snapshot_carries_the_three_keys_and_nothing_more`: the key set of `snapshot` gains `singularityLibraryDir` (plan: "允許更新的既有斷言").

## Not done on purpose

`_verdict`, `CHECK_ORDER`, `apply_preflight`, `abf_station/launch.py` (including `snapshot_ce`) are unchanged. No real site was reached. Known risk P11: on the real nano4 `module` may be a shell function that a non-interactive ssh does not have; the real-site steps (TC-047n / 048n) must check this first.
