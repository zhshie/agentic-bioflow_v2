# Azure Batch 計算環境類型：建立、驗證、免費預檢 progress ledger

- [x] 2026-10-28 RED：platform/tests/test_azure_ce.py（59 個測試，涵蓋自動 TC）先紅 48 個，原因是 azure_preflight 與 Azure 規則尚未存在。
- [x] GREEN：compute_envs.py（AZURE、CHECK_ONLY_TYPES=(AZURE,)、_check_azure、三條 Azure 祕密樣式、snapshot）、abf_station/azure_preflight.py（新）、handlers.py、jobs.py（Azure 專用「尚未支援送出；下一步 azure-launch」）、cli.py（--batch-account、--storage-account、--pool）；PLATFORM.md／SEQERA_PARITY.md／TESTING.md。
- 裁決 10 既有斷言（只增 Azure、移出 unsupported、eleven→ten、azbatch 換成 azcloud）：test_station_envs、test_gcb_ce、test_aws_ce、test_aws_launch、test_gcb_launch、test_launch_bundle、test_launch_cli、test_station_docs。盤點用 `git grep -n 'azbatch-platform\|CHECK_ONLY_TYPES\|eleven\|== 11\|not built for it yet' -- tests docs`；test_aws_clean 的 AWS／Google 拒絕句不動。
- 裁決 8 官方依據：Azure CLI `az batch pool show`、`az storage container exists`（learn.microsoft.com/cli/azure）；Nextflow Azure Batch 文件（nextflow.io/docs/latest/azure.html）。
- 手動項（TC-089、TC-090、TC-131、TC-132）：步驟已寫進 docs/TESTING.md，等維護者用真帳號驗收。
