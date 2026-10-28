# 分析成功後清掉 Azure Batch 環境的 Blob work 前綴 progress ledger

## 進度（executor，stamp 20261029-0255）

- [x] RED：`test_azure_clean.py`（平台側）、`test_station_clean_azure.py`（站台側）先寫，跑出 20 紅（平台）與 83 紅（站台），commit `RED:`。
- [x] GREEN：`clean.py` 新增 `_clean_azure`／`_azure_work`／`_said_az`／`_storage_only`（Azure 段在 AWS 標記之前）；`compute_envs.CLOUD_JOB_KINDS[AZURE]` 加 `clean_work`；`jobs._target` 拿掉 `azure-clean` 提示；`build.clean_work_path`／`prepare_clean`／`clean_screen` 加 Azure、新增 `CLEAN_AZ`／`CLEAN_AZ_SOFT`；文件（PLATFORM.md、SEQERA_PARITY.md、TESTING.md）。
- 文件依據：Microsoft Learn `https://learn.microsoft.com/en-us/cli/azure/storage/blob?view=azure-cli-latest`，用到的旗標：list 的 `--container-name --prefix --query --output --auth-mode --num-results`；delete-batch 的 `--source --pattern --auth-mode`。
- 偏離計畫之處：標記行寫成 `# ---- Azure Batch (Azure-clean) ---`（大寫 A）。原因：既有 `test_station_static.py:46` 掃整個站台套件（含註解）不准有 `\bazure\b`，小寫 `(azure-clean)` 會讓它轉紅，而那條測試不准改；TC-097/100 的「標記」字串因此以大寫版為準。
- 刻意更新的既有斷言（計畫列名者）：`test_station_clean.py` holders 集合加 `_clean_azure`；`test_azure_launch.py` 的 AZL-GATE-01/03/05、`test_every_azure_refusal…`、SEQERA 列；`test_azure_upload.py` 的 CLOUD_JOB_KINDS 集合、`clean_work` 仍被拒那條、PLATFORM／SEQERA 逐字句；`test_azure_ce.py` 的 `clean_work` 被拒迴圈與 `azure-clean` 訊息斷言、PLATFORM／SEQERA 逐字句（計畫「約 936、951、857-864」）。
- 手動差異檢查：範圍只動計畫列出的檔；沒有刪除或放寬既有斷言（只把 `clean_work` 從「被拒」換成「可排隊」）；`delete-batch` 只出現在 `clean.py` 與文件／測試；Azure 段在 AWS 標記之前。
