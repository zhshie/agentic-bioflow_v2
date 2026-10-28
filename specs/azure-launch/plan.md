---
id: azure-launch
title: 在 Azure Batch 上送出與取消分析（確認流程同 Slurm；平台主機上的站台代理在本機跑 Nextflow 主控程序，executor 用 azurebatch）
tier: B
kinds: backend
lane: L2-platform-ce
base: v3（本檔行號取自 origin/v3 796f971，即 azure-ce-type PR #257 合併後；`CLOUD_JOB_KINDS` 逐型別放行表、AWS 的 upload／clean 都已在 v3）
source: memory/dev-plans/aws-launch.md（同型的 AWS 版，已合併）；memory/dev-plans/azure-ce-type.md（本任務的前置，裁決 1 把自動建 pool 留給本任務）
---

# azure-launch

> 本檔由 developer-agent 的 subagent 寫（2026-10-28）。**只處理 Azure 的 C-2**：`azbatch-platform` 環境可以被選去送出一次分析、可以取消。費用預估與上限（C-3）、本機檔案上傳到 Blob（`azure-upload`）、刪 Blob work（`azure-clean`）、續跑／原樣重跑、`fetch_run_records`／`read_task_log`／`list_site_files` 都**不在本任務**（見「不做」）。B 級（使用者看得到的新能力）→ verifier 通過＋CI 綠由 developer-agent 自合。
> **派工前提**：azure-ce-type（#257）已合併，v3 在 796f971 或更新。**車道**：同時改 `compute_envs.py`／`jobs.py` 一帶（L2）與 `platform/abf_station/*`（L1），不可與 L1 站台任務、C-3、其他動 `jobs.py`／`compute_envs.py` 的任務平行。
> **與 aws-launch 的關鍵差別**（先讀這段）：
> 1. 逐型別放行表 `CLOUD_JOB_KINDS` 已存在（`compute_envs.py` 約 :40），本任務不必再「拆共用閘門」，只是把 Azure 從 `CHECK_ONLY_TYPES` 搬進 `PLATFORM_HOST_TYPES`，並在表裡給它**四種**（`preflight`、`launch_nextflow`、`cancel_run`、`pipeline_files`）；AWS 的表有六種，Azure 少 `clean_work`、`put_upload`。
> 2. **憑證交給 Nextflow 的方式不同**：AWS 只要給一個「憑證檔路徑」環境變數；Azure 的 Nextflow 沒有這種機制，官方只認設定鍵或環境變數裡的**金鑰本身**（`AZURE_BATCH_ACCOUNT_KEY`、`AZURE_STORAGE_ACCOUNT_KEY` 或 `AZURE_STORAGE_SAS_TOKEN`）。這是本任務最需要裁決的地方（待裁決 1）。
> 3. Azure 的 pool 前置條件比 AWS 的 job queue 多（`dockerCompatible`、task slots 要等於核心數），預檢目前只確認 pool「存在」（待裁決 3）。

## 目標
讓使用者像在 Slurm、Google Batch、AWS Batch 上一樣：在送出畫面看到全部會被送出的內容，本人答 y 之後，平台主機上的站台代理在**本機**用 Nextflow 的 `azurebatch` executor 啟動一次分析（主控程序在平台主機，計算工作由 Azure Batch 的既有 pool 跑），進度經 `-with-tower` 回到平台；需要時本人確認後可以取消。雲端使用者不裝站台代理。

為什麼這樣切（與 aws-launch 同）：
1. 確認流程不另做一套：沿用 `prepare_launch` → 確認 → `launch_nextflow` job → 站台代理（`verify_confirmation`），所以「沒有本人答 y 就不啟動」自動成立。
2. 平台程式（`abf_platform/`）不啟動任何程式；啟動程式的碼只在 `abf_station/`，只有 `site.py` 呼叫 `subprocess`，只有 `launch.py` 有 `nextflow run` 字樣。
3. 憑證只放平台主機的檔案（azure-ce-type 的 `ABF_STATION_AZURE_CREDENTIALS`）。代理在啟動主控程序那一刻讀檔，只放進主控程序的環境變數，**不進** argv、資料庫、內容包、`head.sh`、`azure.config`、日誌。
4. 費用：Azure 會向實驗室的 Azure 帳號收費。本任務不估價、不設上限（C-3），但送出畫面第一段必須白話寫明，使用者答 y 前一定看得到。

## 維護者原話（verifier 出題用）
**查無 Azure 送出專屬的維護者原話**。以下逐字複製 `aws-launch.md` 所引的雲端方向原話（出處 `memory/PLAN-abf-v3-replan-2026-10.md`），Azure 適用同一組；最後一條是本任務交辦原話。
- 「4. 四種計算環境都建：nano4 → Google Batch（開發上限 NT$1,000/月）→ AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（第 40 行）→ 送出的是「一個 Run」，用已建好的環境＋憑證名字；送出時不重新輸入憑證。
- 「**C-5** Azure Batch／K8s：同模式」（第 169 行）→ Azure 照 Google／AWS 的做法，不另創一套。
- 「Google Batch 雲端：等你開好 GCP 帳號（預算 NT$1,000）；費用顯示美元、每人每月上限、超過自動停。接著 AWS Batch、Azure／K8s。」（第 16 行）→ 費用與自動停是 C-3；本任務只在畫面上白話說明 Azure 會計費，且不得出現任何台幣換算。
- 「雲端費用**照 10-18 裁示**：顯示雲端自己的幣別（美元）、不換算……」（第 46 行）→ 送出畫面不加任何金額或換算。
- 「13. （10-21 拷問二）……**雲端用戶不裝代理**——平台主機自己跑 Nextflow、雲端憑證放平台主機檔案（不進資料庫）」（第 52 行）→ 憑證只在平台主機檔案；使用者端什麼都不用裝。
- 「14. （10-21 拷問三）**B 級部分自合**：網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」（第 54 行）→ 本任務不動網頁畫面。
- 「10-21，他定：雲端優先於畫布；雲端用戶不裝站台代理。」
- 本任務交辦原話（developer-agent，2026-10-28）：azure-launch 是 azure-ce-type 之後的一步，讓平台送出、追蹤、取消 Azure Batch 的 run，**照 aws-launch 的做法**；上傳、清理、續跑對 Azure 仍要清楚拒絕，留給 `azure-upload`、`azure-clean`。→ 每條路徑都要有明確決定（作法 1 的表）；Nextflow 設定鍵一律照官方文件（環境事實）。

## 範圍：檔案（只准改這些）
平台側（不啟動任何程式）：
- `platform/abf_platform/compute_envs.py`（`PLATFORM_HOST_TYPES` 加 `AZURE`、`CHECK_ONLY_TYPES` 拿掉 `AZURE` 變 `()`，註解「新雲端類型先放這裡，只開預檢」保留；`CLOUD_JOB_KINDS` 加 `AZURE` 一列四種；模組頂端說明文字「launching: azure-launch」改成已可送出；Azure 的 `snapshot` 內容不變）
- `platform/abf_platform/jobs.py`（`_target` 約 :110–117：CHECK_ONLY 那條拒絕訊息本來專屬 Azure，改為依型別名產生；`put_upload` 的拒絕訊息把型別名說清楚；Azure 對 `clean_work`／`put_upload` 等的拒絕訊息要含「尚未支援」與 `azure-upload`／`azure-clean`）
- `platform/abf_platform/cloud_store.py`（約 :63–70：Azure 仍不認，不改行為；只在需要時調整錯誤句，使它不誤導成「只有 Google Batch 或 AWS Batch」以外的意思——見測試 AZL-GATE-04。若該句本來就正確則不動）
- `platform/abf_launch/build.py`（加 `is_azure`；`azure_launch_screen`；`launch_screen`、`cancel_screen`、`prepare_cancel` 依型別分派；`prepare_resume`／`prepare_relaunch` 對 Azure 拒絕，用 `AZURE_NO_RESUME`）
- `platform/abf_launch/cli.py`（只在顯示「Slurm 工作編號」處依型別換用詞，約 :200、:237、:267；Slurm、gcb、aws 輸出一字不變）
- `platform/abf_platform/cli.py`、`actions/*`、`cloud_cost.py`：**不改**（`primary_environment` 只選 Slurm，Azure 永不自動被選）

站台代理側：
- `platform/abf_station/launch.py`（加 `AZURE`、`AZURE_RUNS="_azure_runs"`、`AZURE_FILE_NAMES`、`AZURE_FORBIDDEN_ENV`、`NO_AZURE_PATH`、`AZURE_NO_RESUME`、`_check_azure_ce`、`_azure_config`、`_azure_head_script`、`_check_azure_samplesheet`、`render_azure_bundle`；`snapshot_ce` 加 Azure 分支；`render_bundle`（約 :505）、`run_launch`（約 :1322）、`run_resume`（約 :1496）的分派／拒絕加 Azure）
- `platform/abf_station/azure_launch.py`（新；代理端送出與取消，鏡像 `aws_launch.py`，重用 `gcb_launch` 的小工具與 `_cancel_head`）
- `platform/abf_station/cancel.py`（旁加 Azure 分派）
- `platform/abf_station/handlers.py`（只確認 Azure 的預檢分支仍在）
- `platform/abf_station/fetch.py`（`_NOT_RECORDS` 加 `azure.config`）
- `platform/abf_station/clean.py`、`put_upload.py`、`site.py`、`agent.py`、`azure_preflight.py`：**不改**

測試與文件：
- `platform/tests/test_azure_launch.py`（新）
- 「必須更新的既有斷言」列的幾處（`test_azure_ce.py`、`test_aws_ce.py`、`test_aws_launch.py`、`test_gcb_ce.py`）
- `docs/PLATFORM.md`（型別表 Azure 那列與「Azure Batch」小節；新增「Launching on Azure Batch」小節）、`docs/SEQERA_PARITY.md`（Azure Batch 那列與第 84 行的預檢說明句）、`docs/TESTING.md`（新增「azure-launch」小節含手動驗收）、`docs/INSTALL.md` 或 `docs/OPERATIONS.md` 雲端小節（平台主機要 Java 17+、Nextflow、az CLI）
- `specs/azure-launch/ledger.md`（新，executor 進度帳本）

## 作法
1. **逐型別放行（沿用現成的 `CLOUD_JOB_KINDS`）**。Azure 各條路徑的決定：

   | 路徑 | AWS 現況 | Azure 本任務的決定 |
   |---|---|---|
   | 送出 `launch_nextflow` | 開 | **開**（本任務主體） |
   | 取消 `cancel_run` | 開 | **開** |
   | 預檢 `preflight` | 開 | **開**（azure-ce-type 已做；搬動後 `ce preflight` 仍要等得到答案，`cli.py:475` 的條件是 `PLATFORM_HOST_TYPES + CHECK_ONLY_TYPES`，搬動後仍涵蓋 Azure） |
   | `pipeline_files`（只讀公開 GitHub 檔） | 開 | **開** |
   | 清理 `clean_work` | 開 | **關**，拒絕訊息含「尚未支援」與 `azure-clean` |
   | 上傳 `put_upload` | 開 | **關**，拒絕訊息含「尚未支援」與 `azure-upload`；`cloud_store` 對 `az://` 仍丟 `CloudPathError` |
   | 資料集 `--destination` | 開 | **關**（隨 `cloud_store` 不認 Azure） |
   | 費用預估（`_cloud_check`、`cloud_cost.py`） | 無 | **不做**（C-3）；送出畫面明寫「沒有費用預估與上限」 |
   | 續跑／原樣重跑 | 拒 | **拒**（`AZURE_NO_RESUME`，同款訊息，換型別名） |
   | `list_site_files`／`fetch_run_records`／`read_task_log` | 拒（尚未支援） | **拒**（同款訊息，換型別名） |

   `jobs._target` 的拒絕訊息一律依「型別名」產生，不再有寫死的 AWS／Google／Azure 句子；Azure 的訊息不得含 `AWS` 或 `Google Batch`，AWS／gcb 的訊息與搬動前位元級相同。
2. **`PLATFORM_HOST_TYPES = (GOOGLE_BATCH, AWS, AZURE)`、`CHECK_ONLY_TYPES = ()`**。程式裡不得有任何以位置取用（`PLATFORM_HOST_TYPES[0]`）的寫法。
3. **內容包 `render_azure_bundle`**（鏡像 `render_aws_bundle`）：
   - 專屬資料夾 `<storage_root>/_azure_runs/<run>`；檔案：`samplesheet.csv`、`params.yaml`、`nextflow.config`、`azure.config`、`head.sh`，另有 `tower.token`（O_EXCL、600）與 `head.pid`、`head.out`。
   - `reach` 必須是 `local`；內容包不含 `account`；資料夾權限 700、不覆蓋既有資料夾。
   - `azure.config` 只寫這些鍵（全部取自環境檔裡的非機密欄位）：
     - `process.executor = 'azurebatch'`
     - `process.queue = '<pool>'`
     - `workDir = 'az://<container>/<subfolder>/runs/<run>/work'`
     - `azure.batch.accountName = '<batchAccountName>'`
     - `azure.batch.location = '<location>'`
     - `azure.storage.accountName = '<storageAccountName>'`
     - `azure.batch.allowPoolCreation = false`
     - `azure.batch.autoPoolMode = false`
     - 若 `maxvCpus` 有設：`process.resourceLimits = [cpus: N]`（逐任務上限，不是總量；是否被 azurebatch 接受由手動步驟判決，待裁決 5）
     - `spot` 只寫成註解（Nextflow 的真正開關是 pool 層級的 `lowPriority`，由使用者事先建 pool 時決定）
   - 明確關掉自動建 pool 的理由：官方設定參考 `azure.batch.autoPoolMode` 預設 `true`、`allowPoolCreation` 預設 `false`；官方 Azure 頁範例卻把 `autoPoolMode` 設 `true`，兩處矛盾，且自動建 pool 會替實驗室開出沒人預期的機器與帳單，所以本任務一律寫死 `false`、只用事先建好的 pool（azure-ce-type 裁決 1）。
   - 檔案裡**不得出現**帳號金鑰、SAS、憑證檔路徑；`azure.config` 開頭註解說明「金鑰由環境變數提供」（鏡像 `AWS_CREDENTIALS_COMMENT`）。
4. **憑證如何交給主控程序（待裁決 1 的預設做法）**。代理在啟動 `start_detached` 的那一刻，從憑證檔（`azure_preflight` 的 `credentials_path`＋`_read_shape` 同一份解析）讀出金鑰，只放進**主控程序的環境變數**：
   - `AZURE_BATCH_ACCOUNT_KEY`＝`batch_account_key`
   - `AZURE_STORAGE_ACCOUNT_KEY`＝`storage_account_key`，**或** `AZURE_STORAGE_SAS_TOKEN`＝`storage_sas_token`（去掉開頭的 `?`）；兩者擇一，與憑證檔裡有哪個一致
   - 環境的其餘部分先清掉所有 `ABF_*`、`AZURE_*`（鏡像 `AZURE_FORBIDDEN_ENV`），再加上述三個以內；不放 `AZURE_BATCH_ACCESS_KEY`、`AZURE_STORAGE_KEY`（那是 `az` CLI 預檢用的名字，Nextflow 不讀）。
   - 這些值不進 argv、`head.sh`、`azure.config`、內容包、資料庫、日誌、`head.out`；測試用字串拼接產生假金鑰（`tests/credentials_stay_in_settings_test.sh`）。
   - 已知代價：同一個使用者能經 `/proc/<pid>/environ` 看到。這與預檢用 `az` 時的做法相同，平台主機是單一實驗室帳號，風險等級同 AWS 裁決 1 的討論；若維護者要更強隔離，改走「代理寫一個 600 的私有 Nextflow 設定檔、用第三個 `-c` 傳入」，那會讓金鑰落地，需要另外裁決（待裁決 1）。
5. **`head.sh`**：鏡像 `_aws_head_script`，最後一行是 `exec nextflow run <pipeline> -r <rev> -name <run> -params-file params.yaml -c nextflow.config -c azure.config -with-tower <endpoint>`，沿用 `_gcb_quote`、`_gcb_params_yaml`、`GCB_LOOPBACK_OPTS`、`OVERWRITE_BLOCK`、`_tower`。
6. **samplesheet 檢查 `_check_azure_samplesheet`**：所有路徑欄必須是 `az://` 且容器與 `workDir` 的容器相同（Nextflow 官方：儲存體要和 Batch 同區域；跨容器本任務不支援）；本機路徑或別的方案 → 拒絕，訊息告訴使用者「先自己用 `az storage blob` 或 azcopy 把檔案放進同一個容器」。這句話的程式碼要拆成兩段字串（鏡像 `NO_AWS_PATH`），讓原始碼裡沒有完整的上傳指令字樣。
7. **`azure_launch.py`**（鏡像 `aws_launch.py`）：`run_launch(job, ctx, bundle)`，順序：確認內容包是給這個代理的 → run token → 用自己的設定重建內容包並比對 → `upload_paths` 檢查 → deadline → `/proc` → 憑證路徑 → 工具（java、nextflow）→ `az` CLI → 預檢（重用 `azure_preflight.run_preflight`，失敗就不啟動）→ 建資料夾 → 寫五檔＋`tower.token` → `start_detached` → 寫 `head.pid` → 等 settle → 回傳 `{"ok": True, "slurm_job_id": pid, ..., "message": "已啟動：主控程序編號（pid）%d，run 名稱 %s，專屬資料夾 %s；Azure Batch 的工作與費用從現在開始計"}`。`slurm_job_id` 欄位名稱沿用（不改名、不 migration）。
8. **取消**：`azure_launch.run_cancel` 呼叫 `gcb_launch._cancel_head(ctx, bundle, launch.AZURE_RUNS, CANCEL_REMINDER)`；`cancel.py` 依 `ce.platform` 分派。`CANCEL_REMINDER` 白話寫明：「已對主控程序送出一次終止信號；請到 Azure Portal 的 Batch 帳號頁確認 job 與 pool 已停，沒停乾淨要自己處理，費用從啟動到停掉都算」。本任務**不**加 `az batch job terminate`（第二條寫入路徑，需另開任務）。
9. **畫面（`abf_launch/build.py`）**：`azure_launch_screen` 第一段必須有帳單句（常數 `AZURE_COST`）：「由 Azure 向實驗室的 Azure 帳號收費；本系統目前沒有費用預估與上限」——不含金額、不含 `NT$`／`USD`。另有取消提示（`AZURE_CANCEL_NOTE`）、`spot` 備註（`AZURE_SPOT_NOTE`，說明 `spot` 只是記錄，要用低優先權請在建 pool 時設定）。`cancel_screen` 與 `prepare_cancel` 把 `(GCB, AWS)` 擴成含 Azure；沒有 pid 時照舊拒絕。
10. **預檢要補一件事（待裁決 3）**：官方說既有 pool 必須 `dockerCompatible`、task slots 要等於核心數。預設**不改** `azure_preflight`（它不在本任務範圍），而是在 `docs/PLATFORM.md` 的 Azure 小節與 TESTING.md 手動步驟 2 明寫這兩個前置條件；失敗現象與處理寫進文件。若維護者要預檢也查，另開任務。
11. **不需要 migration**：沒有資料表或欄位變動；`slurm_job_id` 沿用；環境設定鍵不變。
12. **新檔頭規則**：`azure_launch.py`、`test_azure_launch.py` 前 40 行要有 `# Nothing existing: …`（TC-070），理由寫「搜過 Nextflow 的 `azurebatch` executor、Seqera `tw launch`、nf-core `tower launch`，都是把工作交給 Seqera 服務，沒有現成可由本機代理在確認後以 `azurebatch` 啟動並可取消的東西」。不得 `import azure.*`（TC-085），Azure 操作一律經 `site.run_fixed` 呼叫 `az` CLI。

## 失敗先行測試（`platform/tests/test_azure_launch.py`，現在都會紅；全部用假的 `start_detached`／`run_fixed`、`tmp_path` 當 `storage_root`，不碰網路、不花錢；測試輸入一律是 fake：`labbatch`、`labstore`、`westeurope`、`lab-pool`、`az://labcontainer/work`）
編號用 `AZL-` 前綴，避免和既有 TC-001～189、TC-602/603/701 撞號。

閘門（最重要的一組）：
- AZL-GATE-01 `test_azure_environment_accepts_exactly_preflight_launch_cancel_and_pipeline_files`：對可用的 Azure 環境，`launch_nextflow`／`cancel_run`／`preflight`／`pipeline_files` 通過；`clean_work`、`put_upload`、`list_site_files`、`fetch_run_records`、`read_task_log` → `JobRefused`，訊息含「尚未支援」，`clean_work` 含 `azure-clean`、`put_upload` 含 `azure-upload`，不含 `AWS`、不含 `Google Batch`。
- AZL-GATE-02 `test_aws_and_google_batch_gates_and_messages_are_unchanged`：AWS 六種仍放行、其餘仍拒；gcb 同；兩者拒絕訊息與搬動前位元級相同（以既有測試的期望字串為準）。
- AZL-GATE-03 `test_type_constants_after_azure_launch`：`PLATFORM_HOST_TYPES == (GOOGLE_BATCH, AWS, AZURE)`、`CHECK_ONLY_TYPES == ()`、`CLOUD_JOB_KINDS[AZURE]` 恰為四種；`abf_platform/`、`abf_station/` 原始碼沒有 `PLATFORM_HOST_TYPES[`。
- AZL-GATE-04 `test_cloud_store_stays_without_azure`：`cloud_store.workdir_bucket`、`upload_prefix`、`object_url`、`big_file_command` 對 Azure 環境（`workDir` 為 `az://…`）一律 `CloudPathError`；`actions.datasets` 的 destination 填 Azure 環境名 → 白話拒絕。
- AZL-GATE-05 `test_put_upload_and_clean_work_jobs_cannot_be_queued_for_azure`：直接排 `put_upload`／`clean_work` → 被拒、jobs 表列數不變；代理端 `clean.run_clean`／`put_upload.run_put` 收到 Azure 的內容包 → 拒絕、不啟動任何程式。
- AZL-GATE-06 `test_azure_ce_preflight_still_routes_after_leaving_check_only`：`ce preflight` 對 Azure 環境仍排出預檢 job，`handlers` 仍走 `azure_preflight`。
- AZL-GATE-07 `test_primary_environment_never_auto_picks_azure_and_naming_it_works`。

內容包與設定：
- AZL-BUNDLE-01 `test_azure_config_has_exactly_the_documented_keys`：`azure.config` 的鍵集合恰為作法 3 的清單（含 `allowPoolCreation = false`、`autoPoolMode = false`），`workDir` 為 `az://labcontainer/work/runs/<run>/work`；`maxvCpus` 有設時才有 `process.resourceLimits`；`spot` 只出現在註解。
- AZL-BUNDLE-02 `test_azure_bundle_contains_no_credential_content`：內容包、`head.sh`、`azure.config`、`snapshot_ce` 結果、資料庫、`ce show` 裡搜不到假金鑰與憑證檔路徑（金鑰以字串拼接組出）。
- AZL-BUNDLE-03 `test_head_script_ends_with_one_exec_nextflow_run_with_both_configs_and_tower`：最後一行恰一個 `exec nextflow run`，含 `-c nextflow.config -c azure.config -with-tower`；source 全文只有 `launch.py` 有 `nextflow run`。
- AZL-BUNDLE-04 `test_samplesheet_must_be_az_paths_in_the_workdir_container`：本機路徑、`s3://`、`gs://`、別的容器的 `az://` → 拒絕，訊息告訴使用者先把檔案放進同一容器，且程式原始碼沒有完整上傳指令字樣。
- AZL-BUNDLE-05 `test_azure_run_folder_is_private_and_never_overwritten`：專屬資料夾 700；已存在 → 拒絕不覆蓋；`tower.token` 600。
- AZL-BUNDLE-06 `test_azure_resume_and_relaunch_are_refused_with_the_azure_name`：`prepare_resume`／`prepare_relaunch`／`run_resume` 對 Azure → 拒絕，訊息含 Azure、不含 AWS。

憑證與環境：
- AZL-CRED-01 `test_head_env_has_only_the_nextflow_credential_names`：假 `start_detached` 收到的 env 有且僅有 `AZURE_BATCH_ACCOUNT_KEY` 與（`AZURE_STORAGE_ACCOUNT_KEY` 或 `AZURE_STORAGE_SAS_TOKEN`）兩類，值對得上憑證檔；沒有 `AZURE_BATCH_ACCESS_KEY`、`AZURE_STORAGE_KEY`、任何 `ABF_*`；SAS 值的開頭 `?` 已去除。
- AZL-CRED-02 `test_credentials_never_appear_in_argv_logs_or_files`：argv、`head.sh`、`head.out`、`ledger`、所有寫出的檔、日誌輸出都搜不到假金鑰。
- AZL-CRED-03 `test_missing_or_badly_shaped_credential_file_stops_before_any_program`：憑證檔不存在／權限不是 600／缺 `batch_account_key`／兩種儲存憑證都缺 → 拒絕，`start_detached` 0 次，訊息說明怎麼修。
- AZL-CRED-04 `test_az_cli_missing_stops_before_launch`：`which az` 找不到 → 拒絕，訊息白話。

確認與憲法：
- AZL-CONF-01 `test_unconfirmed_azure_launch_is_refused_and_nothing_is_written_or_started`（無憑證／雜湊不符／已用過／種類是 `cancel` 各一次 → refused，`tmp_path` 無新檔，`start_detached` 0 次）。
- AZL-CONF-02 `test_a_person_must_say_yes_an_azure_launch_is_never_auto_queued`。
- AZL-CONF-03 `test_the_platform_package_starts_no_program`（沿用 aws 同名測試的掃描範圍，再加 `azure_launch.py` 不含 `nextflow run`、`sbatch`、`subprocess`）；`test_the_launch_allow_list_still_has_one_entry`。
- AZL-CONF-04 `test_no_cloud_library_is_imported_and_no_new_dependency`：`pyproject.toml` 無 `azure-*`；原始碼無 `import azure`（TC-085）。
- AZL-CONF-05 `test_mcp_tool_list_is_still_twelve`。

送出與取消：
- AZL-RUN-01 `test_launch_writes_five_files_starts_one_detached_head_and_returns_pid`：成功路徑，回傳訊息含 pid、run 名稱、資料夾與 Azure 帳單句；`head.pid` 內容等於 pid。
- AZL-RUN-02 `test_preflight_failure_blocks_the_launch`：假 `run_fixed` 讓預檢某項 fail → 不建資料夾、不啟動。
- AZL-RUN-03 `test_head_that_dies_during_settle_is_reported_with_its_log_tail`。
- AZL-CANCEL-01 `test_cancel_sends_one_sigterm_after_cwd_and_ps_checks_for_azure`：用 `gcb_launch._cancel_head` 與 `AZURE_RUNS`；pid 對不上 run 資料夾 → 不送信號。
- AZL-CANCEL-02 `test_cancel_without_pid_is_refused_in_plain_words`；`test_cancel_message_reminds_to_check_the_azure_portal`。
- AZL-CANCEL-03 `test_gcb_and_aws_cancel_messages_are_unchanged_by_the_refactor`（只在 `_cancel_head` 已存在於 v3 的前提下斷言兩者訊息不變）。

畫面：
- AZL-SCREEN-01 `test_azure_launch_screen_first_paragraph_states_billing_without_amounts`：第一段含 `AZURE_COST`；全文沒有 `NT$`、`USD`、`$`＋數字。
- AZL-SCREEN-02 `test_slurm_gcb_and_aws_screens_are_byte_identical`（與搬動前輸出比對）。
- AZL-SCREEN-03 `test_cli_wording_switches_only_for_azure`：`abf_launch/cli.py` 三處用詞，Slurm／gcb／aws 不變，Azure 不出現「Slurm 工作編號」。

文件：
- AZL-DOC-01 `test_platform_md_documents_azure_launch`：型別表 Azure 那列為「checked and launched on the platform host (upload, clean, resume: not yet)」；有「Launching on Azure Batch」小節，含 pool 前置條件（`dockerCompatible`、task slots 等於核心數）、儲存體與 Batch 同區域、`az` CLI 需求。
- AZL-DOC-02 `test_seqera_parity_azure_row`：`SEQERA_PARITY.md` 的 Azure Batch 列為「Have (create + check + launch + cancel)」，且結尾仍是 `[ ] |`。
- AZL-DOC-03 `test_testing_md_has_azure_launch_section_with_manual_steps`：含手動步驟、「會花錢、需維護者同意」字樣。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
動手前先跑 `git grep -nE "CHECK_ONLY_TYPES|尚未支援送出|azure-launch|launch in azure-launch" -- platform docs`，以實際結果為準；以下是 origin/v3 796f971 的清單：
- `platform/tests/test_azure_ce.py:720`：`CHECK_ONLY_TYPES == (AZ,)` → `== ()`，並加 `AZ in PLATFORM_HOST_TYPES`。理由：本任務把 Azure 搬進可送出類型。
- `platform/tests/test_azure_ce.py:746`：Azure 送出被拒的訊息含「尚未支援送出」與 `azure-launch` → 改成只對 `clean_work`／`put_upload` 等未開的種類斷言，訊息含「尚未支援」與 `azure-upload`／`azure-clean`；`launch_nextflow` 改為放行。理由：launch 已開。
- `platform/tests/test_azure_ce.py:864`：`SEQERA_PARITY` 列字串 `Have (create + check); launch in azure-launch` → 作法與 AZL-DOC-02 一致的新字串。
- `platform/tests/test_azure_ce.py:951`：`"azure-launch" in msgs["launch"]`（Azure 的 launch 被拒訊息）→ 改為 launch 放行的新斷言；若該處斷言的是別的來源（如 CLI 說明），依實況只換掉 Azure 專屬字樣。
- `platform/tests/test_aws_ce.py:907`、`platform/tests/test_gcb_ce.py:853`、`platform/tests/test_aws_launch.py:985`（與 :992 附近 `startswith("CHECK_ONLY_TYPES")` 那段）：`CHECK_ONLY_TYPES == ("azbatch-platform",)` → `== ()`，`PLATFORM_HOST_TYPES` 期望值加上 `AZURE`。理由：同上。
- 若 `git grep` 找到其他逐字釘住「Azure 只能預檢」的斷言（含 `docs/*.md` 內被測試釘住的句子），只准做「加 Azure」的最小改動；任何其他既有斷言要變動 → 回報 BLOCKED，不自行判斷（azure-ce-type 裁決 10 同款）。
- 不准動：Slurm、gcb、aws 的內容包、畫面、`head.sh`、取消訊息的任何斷言。

## 完成標準（done when）
- 自動：上面所有新測試綠；全套綠（含 `tests/platform_test.sh`、`no_second_run_state_test.sh`、`credentials_stay_in_settings_test.sh`）；已知環境紅 `test_tc047_tc051` 依 README 通例視同綠（只剩這一條紅才算）；MCP 工具仍 12；Slurm、gcb、aws 的內容包、畫面、`head.sh`、取消訊息位元級不變；`git diff --name-only` 不含 `.github/`、憲法、版本號檔、`web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`、已安裝的 plugin 副本。
- 手動（維護者；**會花很小一筆錢，屬 C 級，需要維護者同意**；先確認 Azure Cost Management 的預算警示已設；測試已全綠不代表要做這步，做不做由維護者決定）：
  1. 平台主機（WSL）有 Java 17+、Nextflow、az CLI；`storage_root` 已設；憑證檔在 `ABF_STATION_AZURE_CREDENTIALS` 指的位置（600）；azure-ce-type 的預檢 `available`。
  2. 事先建好的 pool 符合官方前置條件：`dockerCompatible`、task slots 等於 VM 核心數、與儲存體同區域；pipeline 每個 process 都有 `container`。失敗現象＝Nextflow 啟動即報 pool 設定錯誤或 task 找不到容器；失敗就停手回報，走待裁決 3，不自行加設定。
  3. 送出一個最小的 samplesheet（兩三個很小的檔，已用 `az storage blob` 或 azcopy 放進 `workDir` 同一個容器）：`abf-launch … --ce azure1`；**送出畫面第一段必須看到「由 Azure 向實驗室的 Azure 帳號收費」**；答 y 才開始。**這步同時判決待裁決 1**：若主控程序報認證失敗（Nextflow 沒讀到環境變數），記入 ledger 並回報，不要自行改成別的憑證做法。
  4. 看到 `已啟動：主控程序編號…`；`<storage_root>/_azure_runs/<run>` 有 `head.pid`、`head.out`；Azure Portal 的 Batch 帳號頁出現 job；平台 run 頁出現進度（`-with-tower` 通）；跑完 `az://…/runs/<run>/results` 有輸出。
  5. 再送一個，中途取消：確認 Portal 上 job 被終止（**判決 SIGTERM 是否讓 Nextflow 取消 Batch job**；沒取消乾淨就記入 ledger 回報，不要自行加 `az batch job terminate`，那是第二條寫入路徑，需另開任務）。官方只說 Nextflow 完成時會把 job 標成終止、不刪 pool，沒有描述取消行為，所以這步的結果才是依據。
  6. 在資料庫、`ce show`、畫面、日誌、`head.sh`、`azure.config` 搜不到憑證任何片段與憑證檔路徑；`/proc/<pid>/environ` 有金鑰是已知代價（作法 4）。
  7. 核對 `process.resourceLimits = [cpus: N]` 在 `azurebatch` 上被接受（不報未知指令）；結果寫進 ledger。
- 文件：作法與範圍列的各份文件更新；`TESTING.md` 的「azure-launch」小節寫明手動驗收 1–7，標明「需維護者同意，會花錢」，並列在「Needs human」之下。

## 環境事實
（取自 `git show origin/v3:<path>`，head 796f971，2026-10-28 讀；官方文件 2026-10-28 讀，`nextflow.io/docs/latest/azure.html` 會 302 轉址到 `docs.seqera.io/nextflow/azure`）

**Nextflow 的 Azure Batch 設定鍵（官方）**
- 〔來源：https://docs.seqera.io/nextflow/azure〕`process.executor = 'azurebatch'`；`workDir` 設成 Blob 路徑如 `az://<blob-container>/work`，且「必須包含子資料夾，不能只有容器名」；`azure.storage.accountName`；`azure.batch.accountName`、`azure.batch.location`。
- 〔同上〕用 process 的 `queue` 指令指定 pool（pool 名含連字號要加引號）；「每個 process 都必須指定 container」。
- 〔同上〕`azure.batch.allowPoolCreation = true` 才讓 Nextflow 建 pool，否則 pool 必須在送出任務時已存在；`azure.batch.autoPoolMode` 依 process 的 cpus／memory 自動建 pool，頁面未說預設，範例設 `true`。
- 〔同上〕既有 pool 必須宣告 `dockerCompatible`，每個節點的 task slots 必須等於 VM 核心數，否則 Nextflow 報錯；沒用 Fusion 時 task 上要有 `azcopy`。
- 〔同上〕儲存體帳號與 blob 容器要與 Batch 帳號同一區域；主控程序可以在「本機或 Azure VM」啟動，不必在 Azure 內；Spot 在 pool 設定 `lowPriority = true`；Nextflow 結束時把 Batch job 標成終止，pool 不會刪除除非開 `azure.batch.deletePoolsOnCompletion`；頁面沒有描述取消行為。
- 〔同上〕Nextflow 自產的 task SAS 預設 48 小時，`azure.storage.tokenDuration` 可改。
- 〔來源：https://docs.seqera.io/nextflow/reference/config/azure〕`azure.batch.accountKey`（環境變數 `AZURE_BATCH_ACCOUNT_KEY`）；`azure.batch.accountName`（`AZURE_BATCH_ACCOUNT_NAME`）；`azure.batch.endpoint`（例 `https://nfbatch1.westeurope.batch.azure.com`，無環境變數）；`azure.batch.location`（設了 endpoint 就不需要）；`azure.batch.allowPoolCreation` 預設 `false`；`azure.batch.autoPoolMode` 預設 `true`；`azure.batch.deleteJobsOnCompletion` 預設 `false`（23.10 起）；`azure.batch.deletePoolsOnCompletion` 預設 `false`；`azure.batch.terminateJobsOnCompletion` 預設 `true`；`azure.storage.accountName`（`AZURE_STORAGE_ACCOUNT_NAME`）；`azure.storage.accountKey`（`AZURE_STORAGE_ACCOUNT_KEY`）；`azure.storage.sasToken`（`AZURE_STORAGE_SAS_TOKEN`，是金鑰的替代品）；`azure.storage.tokenDuration` 預設 `48h`。
- 〔查不到〕Blob 認證細節頁（https://docs.seqera.io/nextflow/azure-blob）這次沒讀；SAS 開頭 `?` 要去掉、Entra（Active Directory／Managed Identity）認證只記在 azure-ce-type 的筆記，本任務不用，沒有重新核對。〔查不到〕Azure Batch 帳單細節、容器命名與 pool id 長度規則（azure-ce-type 同樣查不到）。

**共用閘門與可重用的實作（origin/v3 796f971）**
- `platform/abf_platform/compute_envs.py`：`GOOGLE_BATCH`／`AWS`／`AZURE = "azbatch-platform"`、`PLATFORM_HOST_TYPES = (GOOGLE_BATCH, AWS)`、`CHECK_ONLY_TYPES = (AZURE,)`（:39，附註解）、`CHECKABLE` :44、`CLOUD_JOB_KINDS`（約 :40，GCB 與 AWS 各六種）；`_AZURE_CONFIG` 與 `_check_azure`（約 :465–520）；Azure `snapshot`（約 :843）回 `{name, platform, credentialsId, location, batchAccountName, storageAccountName, workDir, pool}`。
- `platform/abf_platform/jobs.py:_target`（約 :95–135，含 :114–116 的 CHECK_ONLY 拒絕訊息）。`platform/abf_platform/cloud_store.py`（約 :63–70，只認 gs／s3）。`platform/abf_platform/cli.py:475`（`ce preflight` 條件）。
- `platform/abf_station/launch.py`：AWS 的 `AWS_RUNS`、`AWS_FILE_NAMES`、`AWS_CREDENTIALS_COMMENT`、`AWS_FORBIDDEN_ENV`、`NO_AWS_PATH`、`AWS_NO_RESUME`、`snapshot_ce`（AWS 分支約 :172）、`_check_aws_ce`、`_aws_config`、`_aws_head_script`、`_check_aws_samplesheet`、`render_aws_bundle`；分派點 `render_bundle`（約 :505）、`run_launch`（約 :1322）、`run_resume`（約 :1496）；可重用 `_gcb_quote`、`_gcb_params_yaml`、`GCB_WORK_CHARS`、`GCB_LOOPBACK_OPTS`、`OVERWRITE_BLOCK`、`_tower`、`path_cells`、`_csv_text`。
- `platform/abf_station/aws_launch.py`（範本）、`gcb_launch.py`（`_check_tools`、`_has_proc`、`_plain_env`、`_settle_seconds`、`_tail`、`_write_new`、`_cancel_head`）、`cancel.py`（依 `ce.platform` 分派）、`azure_preflight.py`（`TYPE`、`CREDENTIALS_ENV = "ABF_STATION_AZURE_CREDENTIALS"`、預設路徑 `<部署資料夾>/_personal/azure-credentials`、`credentials_path`、`clean_environment`、`_az_env`、`_read_shape`＝INI `[default]` 的 `batch_account_key` 與 `storage_account_key` 或 `storage_sas_token`、六項檢查 `credential_name, credential_file, credential_shape, az, pool, storage`、`run_preflight(env, *, cred_path, now, runner, which, stat)`）、`handlers.py`（已路由 Azure 預檢）。
- `platform/abf_launch/build.py`：`is_gcb`／`is_aws`（約 :270–279）、`AWS_COST`、`AWS_CANCEL_NOTE`、`AWS_SPOT_NOTE`、`aws_launch_screen`、`launch_screen`、`cancel_screen`、`prepare_cancel`（約 :296）、`prepare_resume`／`prepare_relaunch`（約 :422）、`primary_environment`（只選 Slurm）。`platform/abf_launch/cli.py:200,237,267`。
- 憲法與測試規矩：`nextflow run` 只准在 `launch.py`、`subprocess` 只准在 `site.py`；新 `.py` 檔前 40 行要 `# Nothing existing: …`（TC-070）；TC-085 禁雲端 SDK；`tests/credentials_stay_in_settings_test.sh`（測試用金鑰以字串拼接）；`test_scope.py`（`abf_platform/` 不得有 `subprocess`）。

## 不做
- 費用預估與上限（C-3）、`cloud_cost.py`、`_cloud_check`。
- `azure-upload`：本機檔案上傳到 Blob、`cloud_store` 的 `az://` 解析、資料集 destination。
- `azure-clean`：刪 Blob 的 work 資料夾。
- 續跑／原樣重跑、`list_site_files`、`fetch_run_records`、`read_task_log`。
- 自動建 pool（`allowPoolCreation`、`autoPoolMode` 一律 `false`）；Entra／Managed Identity 認證；VNet 與自訂映像；user subscription 模式的 Batch 帳號。
- `az batch job terminate` 或任何由平台主動刪 Azure 資源的指令。
- 預檢新增 `dockerCompatible`／task slots 檢查（待裁決 3）。
- 任何網頁畫面、`.github/`、憲法、版本號、已安裝 plugin 副本。
- 真實 Azure 試跑不是自動測試的一部分，只是手動步驟，需維護者同意（C 級）。

## 裁決與待裁決（2026-10-28，developer-agent 的 subagent 起草；與上文衝突時以本段為準）
待裁決（由 developer-agent 在派工前填寫；未填的項目，executor 一律採「預設」欄的做法，不自行改）：

- 待裁決 1：**Nextflow 的 Azure 憑證怎麼給**。預設＝代理讀憑證檔後只放進主控程序的環境變數（`AZURE_BATCH_ACCOUNT_KEY`＋`AZURE_STORAGE_ACCOUNT_KEY` 或 `AZURE_STORAGE_SAS_TOKEN`），不落地；缺點＝同一使用者可從 `/proc/<pid>/environ` 看到。替代＝代理寫 600 的私有 Nextflow 設定檔，用第三個 `-c` 傳入（金鑰落地，需決定存放位置與清除時機）。官方文件這次只確認這些鍵與環境變數名存在，**沒有**確認 Nextflow 在 `-with-tower` 下是否另有行為；以手動步驟 3 判決。
- 待裁決 2：**儲存體用帳號金鑰還是 SAS**。預設＝跟憑證檔裡有的那個走（兩個都有就用金鑰）；SAS 的有效期與權限範圍由使用者建 SAS 時決定，平台不檢查。
- 待裁決 3：**pool 前置條件要不要進預檢**。預設＝不改預檢，只寫文件。需要的話另開任務，檢查 `dockerCompatible` 與 task slots（`az batch pool show` 的輸出欄位名稱本次沒查證）。
- 待裁決 4：**`autoPoolMode` 與 `allowPoolCreation` 一律寫死 `false`**。預設＝是（見作法 3 的理由：官方兩頁對 `autoPoolMode` 預設的說法不一致，且自動建 pool 會產生未預期費用）。若維護者要 Azure 也能自動建 pool，另開任務。
- 待裁決 5：**SIGTERM 是否讓 Nextflow 取消 Azure Batch 的 job**，以及 **`process.resourceLimits` 在 `azurebatch` 是否被接受**。預設＝兩者都由手動步驟 5、7 判決；判決前文件不承諾「取消即停止計費」，取消提示一律要求使用者到 Portal 核對。
- 待裁決 6：**是否保留 `CHECK_ONLY_TYPES = ()` 這個空元組**。預設＝保留（鏡像 AWS 裁決 5，下一個新雲端類型直接用，註解保留）。
- 待裁決 7：**首次真實試跑要不要有費用預估或上限**。預設＝允許無估價、無上限的第一次最小試跑，但要先設 Azure 預算警示（C 級，維護者同意）；C-3 之後才補上限。
- 待裁決 8：**`az` CLI 是否為平台主機的硬需求**。預設＝是（預檢已需要它；啟動前再檢查一次，缺了就拒絕並說明怎麼裝）。
- 待裁決 9：**拒絕訊息裡的後續任務名**。預設＝`azure-upload`、`azure-clean`（與 dev-queue 的任務 id 一致；若 id 不同，訊息與測試同步改）。
- 待裁決 10：**行號與清單核對**。動手前用 `git show origin/v3:<path>` 重新核對本檔列的行號與「必須更新的既有斷言」；以實際 grep 結果為準，清單外的既有斷言要動，一律 BLOCKED 回報。

### developer-agent 裁決（2026-10-28 22:5x，派工前；以下取代上面各「預設」的待裁決狀態）
1. 憑證：採預設，只放主控程序環境變數、不落地。`/proc/<pid>/environ` 同使用者可見，與 AWS 版同等級，可接受；手動步驟 3 若證明行不通再另開任務。
2. 採預設：憑證檔有什麼用什麼，兩者都有時用帳號金鑰。
3. 採預設：預檢不改，pool 條件只寫文件。
4. 採預設：`allowPoolCreation`、`autoPoolMode` 寫死 `false`。
5. 採預設：文件不承諾取消即停止計費。
6. 採預設：保留 `CHECK_ONLY_TYPES = ()`。
7. 本任務只做程式與假測試；任何真實 Azure 試跑屬 C 級，列進 Needs human，維護者點頭前不跑。
8. 採預設：`az` CLI 是硬需求。
9. 採預設：`azure-upload`、`azure-clean`。
10. 採預設：清單外既有斷言要動 → BLOCKED。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
