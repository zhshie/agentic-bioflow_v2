# Azure：把本機檔案上傳到 Azure Blob 供分析使用 progress ledger

## 完成項目
- [x] 測試先行（RED 3636c83）：`platform/tests/test_azure_upload.py`，27 條先紅（理由都對：az 位置不認得、Azure 環境被拒、`run_put` 拒 Azure）。
- [x] `compute_envs.CLOUD_JOB_KINDS[AZURE]` 加 `put_upload`（五個，不含 clean）。
- [x] `cloud_store.py`：`parse_az`、`workdir_scheme`=`az`、容器檢查、`az storage blob upload-batch --destination-path` 指令；原文無小寫 azure。
- [x] `jobs.py`：拿掉「上傳要等 azure-upload」提示；Azure 超過 2 GB 的訊息；不能放雲端資料的句子加 Azure Batch。
- [x] `actions/datasets.py`：只加 az 分支，沒新增公開函式或參數；`_TABLE` 不動，沒有 migration。
- [x] `abf_station/put_upload.py`：`_transfer_az`（`--file` 模式、上傳前後 lstat 比對 dev/ino/大小、`blob show` 核對大小才刪暫存檔、每次呼叫自己的 `AZURE_CONFIG_DIR` 並在 finally 刪、環境變數拿掉 `AZURE_BATCH_*`、失敗訊息不含路徑與金鑰）。
- [x] 文件：PLATFORM.md、SEQERA_PARITY.md、TESTING.md。

## 查證（裁決 15 / 3）
- 本機沒裝 `az`，無法跑 `az --help`。改以 Microsoft 官方文件確認 `az storage blob upload-batch` 有 `--destination-path`；azure-cli 自己的測試 `test_storage_blob_scenarios.py` 用 `JMESPathCheck('properties.contentLength', ...)` 檢查 `blob show`，確認該查詢路徑存在。
- 只有 SAS 時 az 吃 `AZURE_STORAGE_SAS_TOKEN` 環境變數：依裁決 19 實作，沒有真機驗證（真機步驟在 TESTING.md，TC-119 手動）。

## 既有斷言的有意修改（以前 / 以後 / 理由）
1. `test_azure_ce.py::test_no_launch_cost_or_upload_code_for_azure`：正則禁 `storage blob upload` -> 拿掉該項並改名 `test_no_delete_no_azcopy_no_pool_creation_for_azure`；理由：本任務就是要寫這個指令（A.1）。
2. `test_azure_ce.py::test_no_new_write_path_for_azure`：迴圈含 `put_upload` -> 移除；`clean_work`、`list_site_files` 仍被拒（A.2）。
3. `test_azure_ce.py::test_jobs_other_than_the_preflight_are_refused_in_plain_words`：被拒迴圈移除 `put_upload`（A.3）。
4. `test_azure_ce.py::test_docs_list_every_azure_key_and_check`：PLATFORM.md 列 -> `(clean, resume: not yet)`；SEQERA_PARITY 列 -> `Have (create + check + launch + cancel + upload); clean in azure-clean`（A.4）。
5. `test_azure_launch.py`：GATE-01（put_upload 改為被接受）、GATE-03（五個）、GATE-04（改為 cloud_store 認得 az、資料集可用 Azure 目的地，函式改名）、GATE-05（只留 clean_work 與 Slurm 被拒；函式改名）、DOC-02（SEQERA_PARITY 列新句）（A.5）。
6. `test_azure_launch.py::test_every_azure_refusal_says_what_to_do_and_leaks_nothing`：被拒迴圈移除 `put_upload`（計畫 A 沒逐字列，與 A.3 同理，否則必紅）。
7. `test_azure_launch.py::test_no_azure_command_that_changes_anything`：正則 `blob (upload|delete)|az storage` -> `blob delete|az storage (?!blob (upload|show)\b)`；理由：本任務合法寫入 `az storage blob upload`／`show`，刪除與其他 az storage 子指令仍禁（計畫 A 沒逐字列，同 A.1 的理由）。
8. `test_aws_upload.py` 705 行字表：`"azure"` -> `"import azure", "from azure"`（裁決 13；693、713 行未動）。
- 搜過 `test_cloud_upload.py`、`test_aws_*`、`test_gcb_*`：沒有把 Azure 當反例、或逐字比對舊句子「只有 Google Batch 或 AWS Batch」的斷言，無需改。

## 手動差異檢查
- 沒動 spec、合約檔、憲法、ROADMAP、.github、plugin.json、web.py、web_board.py、static、DESIGN.md、clean.py、build.py、store.py。
- 既有測試只做上列八種修改，其餘一個字沒動。
