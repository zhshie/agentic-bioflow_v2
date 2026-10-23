# station-packaged-scripts progress ledger

- [x] 建置 hook 複製 scripts/、configs/ 到 abf_station/plugin/；缺來源時 SystemExit。
- [x] site.default_plugin_root()；cli run／unforward 改用它；找不到時訊息補「安裝版裡沒有、也沒給 --plugin-root」。
- [x] .gitignore 加 platform/abf_station/plugin/；test_guidance.py 的 _copy_for_build 也帶 scripts/、configs/。
- TC-406 以前／以後：沒改（package-data 未動，plugin 檔由 build_lib 複製進 wheel）。
- 欠：platform/abf_platform/su.py 讀 configs/sites/su_rates.json 有同類潛在問題（pip 安裝版找不到 repo 的 configs），本件未處理。
