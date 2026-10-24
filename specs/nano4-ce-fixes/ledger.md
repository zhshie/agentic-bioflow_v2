# nano4 計算環境範本收進 16S 實跑的四個修正 progress ledger

- [x] 2026-10-24 executor: 不需要 migration（只改 JSON 範本與文件，沒有資料表或欄位變動）；沒有新增 CE 鍵、沒改程式。
  - 事實 1（nf-tower 插件）：`configs/sites/nchc-nano4-ce.json` 的 `NXF_PLUGINS_DIR`；建法在 `docs/SETTINGS.md`。
  - 事實 2（iGenomes）：範本 `siteConfigVars` 只留 `NFCORE_SITE_CONFIG`；理由在 `docs/SETTINGS.md`。
  - 事實 3（ref_taxonomy_storage）：只在 `docs/SETTINGS.md`（每次 run 的參數）。
  - 事實 4（壞映像）：範本 `NXF_SINGULARITY_LIBRARYDIR`；建庫與 `file` 檢查在 `docs/SETTINGS.md`；`SITE_ADAPTER.md`、`PITFALLS.md` 54 指向它。
  - 測試：`platform/tests/test_estimate_su.py` 新增兩條，改動 N4-17～20、N4-21 兩處。
