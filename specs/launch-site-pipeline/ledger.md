# 站台啟動先 module load，命中 sitePipelines 用本地路徑啟動 progress ledger

- [x] 站台啟動先 `module load`，命中 `sitePipelines` 用本地路徑啟動（exec 行不帶 `-r`、不帶 `-profile`）。
  - `launch.py`：`snapshot_ce` 帶三鍵；`_check_ce` 直接呼叫 `compute_envs._check_site_keys` 重驗；`_pipeline_source`；`_head_script` 在 `umask 077` 後逐行 `module load X || exit 1`；`siteConfigVars` 逐項 `-c "$VAR"`，我們的 `-c nextflow.config` 在最後。
  - `rules.clean_environment` 放行三鍵；`compute_envs.snapshot` 帶三鍵（缺則 `[]`）。
  - 續跑（`render_resume`）由 CE 重算來源，同樣先 module load；舊 bundle（無三鍵、無 `pipeline_source`）在代理端以 `_as_current` 視為遠端，續跑不被拒。
  - **migration：不需要。** `pipeline_source` 只存在 `bundle_json`（JSON 文字，`confirmations.bundle_json` 與 `jobs.args_json` 內），`launches` 表不加欄。理由：它是 bundle 的一個鍵，不是新的資料表欄位，所以沒有資料結構變動；`launches` 欄位與 base 相同（TC-LS-47 用 `PRAGMA table_info(launches)` 比對）。
  - golden：`local`、`forward` 內容不變（僅 JSON 檔尾逗號格式），新增 `nano4`、`nano4-miss`。
  - **既有測試被更新的斷言（TC-LS-48 要求列出）：只有一處。** `platform/tests/test_owner_gaps.py` 的 `test_tc050_nothing_new_is_made_on_the_site`（約 328 行）：允許的 bundle 鍵集合加入 `"pipeline_source"`（commit bd1e72a，計畫裁決 6）。原因：bundle 本來就多了這一個鍵，這條斷言是「bundle 除了這些鍵之外只能多 `upload_paths`」，所以要把新鍵列進去；其餘斷言（沒有 alice、資料夾在 `runs` 之下）一字未動。`test_launch_bundle.py`、`test_station_launch.py` 沒有既有斷言被更新（只新增案例）；`golden_head_scripts.json` 的 `local`、`forward` 內容與 base 逐字相同。
  - 修正輪（驗收退回）補的測試：`test_station_launch.py` 加 TC-LS-12（終端機 launch，參數與 base 相同）、27（`rules.clean_environment`）、41（`run_resume` 命中續跑）、42（舊格式 origin 續跑）、47（讀 `confirmations.bundle_json` 與 `PRAGMA table_info(launches)`，取代原本的原始碼 regex）、52（MCP 工具清單與 `launch` 參數）、53（token 不在 bundle／head.sh／拒絕訊息／代理日誌）；`test_owner_binding.py` 只新增 TC-LS-50、51（跨使用者讀、寫）。TC-LS-42、27 用「拿掉 `_as_current`／拿掉 `clean_environment` 新鍵就變紅」確認測得到。
  - 範圍外：新增案例放在 `test_owner_binding.py`（合約允許只新增案例）；未動 `test_actions_layer.py`。
