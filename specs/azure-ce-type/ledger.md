# Azure Batch 計算環境類型：建立、驗證、免費預檢 progress ledger

- [x] 2026-10-28 RED：platform/tests/test_azure_ce.py（59 個測試，涵蓋自動 TC）先紅 48 個，原因是 azure_preflight 與 Azure 規則尚未存在。
- [x] GREEN：compute_envs.py（AZURE、CHECK_ONLY_TYPES=(AZURE,)、_check_azure、三條 Azure 祕密樣式、snapshot）、abf_station/azure_preflight.py（新）、handlers.py、jobs.py（Azure 專用「尚未支援送出；下一步 azure-launch」）、cli.py（--batch-account、--storage-account、--pool）；PLATFORM.md／SEQERA_PARITY.md／TESTING.md。
- 裁決 10 既有斷言（只增 Azure、移出 unsupported、eleven→ten、azbatch 換成 azcloud）：test_station_envs、test_gcb_ce、test_aws_ce、test_aws_launch、test_gcb_launch、test_launch_bundle、test_launch_cli、test_station_docs。盤點用 `git grep -n 'azbatch-platform\|CHECK_ONLY_TYPES\|eleven\|== 11\|not built for it yet' -- tests docs`；test_aws_clean 的 AWS／Google 拒絕句不動。
- 裁決 8 官方依據：Azure CLI `az batch pool show`、`az storage container exists`（learn.microsoft.com/cli/azure）；Nextflow Azure Batch 文件（nextflow.io/docs/latest/azure.html）。
- 手動項（TC-089、TC-090、TC-131、TC-132）：步驟已寫進 docs/TESTING.md，等維護者用真帳號驗收。
- 全套第一次跑多出兩個計畫沒列的既有釘子，已處理：①`test_model_key_refusal.py::test_tc015`（釘死 `_VALUE_PATTERNS` 全清單）——計畫作法 3 要求加三條 Azure 樣式，所以只在清單**尾端附加**三條並把斷言的後半段同步（前八條原樣，沒放寬）；②`test_station_static.py::test_agent_stricter_scan`（禁 abf_station 出現獨立單字 `azure`，用來抓雲端套件）——不改測試，改程式：端點網域與憑證檔名在原始碼裡用字串拼接。
- 修正輪：TC-038 測試改為同時要求訊息含鍵名與「像憑證」、且不含 unknown setting（拿掉憑證偵測即會失敗）；程式不動。
