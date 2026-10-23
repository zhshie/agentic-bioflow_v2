# 站台啟動先 module load，命中 sitePipelines 用本地路徑啟動 progress ledger

- [x] 站台啟動先 `module load`，命中 `sitePipelines` 用本地路徑啟動（exec 行不帶 `-r`、不帶 `-profile`）。
  - `launch.py`：`snapshot_ce` 帶三鍵；`_check_ce` 直接呼叫 `compute_envs._check_site_keys` 重驗；`_pipeline_source`；`_head_script` 在 `umask 077` 後逐行 `module load X || exit 1`；`siteConfigVars` 逐項 `-c "$VAR"`，我們的 `-c nextflow.config` 在最後。
  - `rules.clean_environment` 放行三鍵；`compute_envs.snapshot` 帶三鍵（缺則 `[]`）。
  - 續跑（`render_resume`）由 CE 重算來源，同樣先 module load；舊 bundle（無三鍵、無 `pipeline_source`）在代理端以 `_as_current` 視為遠端，續跑不被拒。
  - **migration：不需要。** `pipeline_source` 只在 `bundle_json` 內（JSON），`launches` 表不加欄，所以沒有資料結構變動。
  - golden：`local`、`forward` 內容不變（僅 JSON 檔尾逗號格式），新增 `nano4`、`nano4-miss`。
  - 既有測試：沒有更新任何既有斷言（只新增案例）。
  - 範圍外：測試放在 `test_station_envs.py`／`test_station_launch.py`／`test_launch_bundle.py`；未動 `test_owner_binding.py`、`test_actions_layer.py`（TC-LS-50~52 由既有案例涵蓋，launch 參數未變）。
