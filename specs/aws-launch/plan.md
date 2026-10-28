---
id: aws-launch
title: 在 AWS Batch 上送出與取消分析（確認流程同 Slurm；平台主機上的站台代理在本機跑 Nextflow 主控程序，executor 用 awsbatch）
tier: B
kinds: backend
lane: L2-platform-ce
base: v3（aws-ce-type 分支 `feat/aws-ce-type` 先合併；本任務從合併後的 v3 開分支。本檔行號取自 origin/v3 2233693，aws-ce-type 才會新增的名字都標「aws-ce-type 新增」）
source: memory/dev-plans/gcb-launch.md（同型的 Google 版，已合併）；memory/dev-plans/aws-ce-type.md（本任務的前置，裁決 7 要求本任務先查 Nextflow awsbatch 官方文件）
---

# aws-launch

> 本檔由 developer-agent 的 subagent 寫（2026-10-28）。**只處理 AWS 的 C-2**：`awsbatch` 環境可以被選去送出一次分析、可以取消。費用預估與上限（C-3）、本機檔案上傳到 S3、刪 S3 work、續跑／原樣重跑、`fetch_run_records`／`read_task_log`／`list_site_files` 都**不在本任務**（見「不做」與裁決 3）。B 級（使用者看得到的新能力）→ verifier 通過＋CI 綠由 developer-agent 自合。
> **派工前提**：aws-ce-type 已合併。**車道**：同時改 `compute_envs.py` 一帶（L2）與 `platform/abf_station/*`（L1），不可與 L1 站台任務、C-3、其他動 `jobs.py`／`compute_envs.py` 的任務平行。
> **與 gcb-launch 的關鍵差別**（先讀這段）：gcb 的「放行」是靠 `PLATFORM_HOST_TYPES` 這個**共用元組**，一加進去就同時打開 launch、cancel、clean_work、put_upload、pipeline_files（`jobs.py:110`）與 `cloud_store.workdir_bucket`（:52）。aws-ce-type 刻意把 awsbatch 留在 `CHECK_ONLY_TYPES`；本任務把它搬進 `PLATFORM_HOST_TYPES` 時，**那些共用閘門會連帶對 AWS 打開，而 AWS 的清理與上傳都還沒做**。所以本任務一半的工作是「把共用閘門改成逐型別放行」，見作法 1。

## 目標
讓使用者像在 Slurm、Google Batch 上一樣：在送出畫面看到全部會被送出的內容，本人答 y 之後，平台主機上的站台代理在**本機**用 Nextflow 的 `awsbatch` executor 啟動一次分析（主控程序在平台主機，計算工作由 AWS Batch 的 job queue 跑），進度經 `-with-tower` 回到平台；需要時本人確認後可以取消。雲端使用者不裝站台代理。

為什麼這樣切（與 gcb-launch 同）：
1. 確認流程不另做一套：沿用 `prepare_launch` → 確認 → `launch_nextflow` job → 站台代理（`verify_confirmation` launch.py:974），所以「沒有本人答 y 就不啟動」自動成立。
2. 平台程式（`abf_platform/`）不啟動任何程式；啟動程式的碼只在 `abf_station/`，只有 `site.py` 呼叫 `subprocess`，只有 `launch.py` 有 `nextflow run` 字樣。
3. 憑證只經環境變數 `AWS_SHARED_CREDENTIALS_FILE` 給主控程序，路徑是代理自己的設定（aws-ce-type 新增的 `ABF_STATION_AWS_CREDENTIALS`），不進 argv、資料庫、內容包、`head.sh`、日誌。
4. 費用：AWS 會向實驗室的 AWS 帳號收費。本任務不估價、不設上限（C-3），但送出畫面必須白話寫明，使用者答 y 前一定看得到。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`（行號同 gcb-launch.md 所引）：
- 「4. 四種計算環境都建：nano4 → Google Batch（開發上限 NT$1,000/月）→ AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（第 40 行）→ 送出的是「一個 Run」，用已建好的環境＋憑證名字；送出時不重新輸入憑證。
- 「Google Batch 雲端：等你開好 GCP 帳號（預算 NT$1,000）；費用顯示美元、每人每月上限、超過自動停。接著 AWS Batch、Azure／K8s。」（第 16 行）→ 費用與自動停是 C-3；本任務只在畫面上白話說明 AWS 會計費，且不得出現任何台幣換算。
- 「雲端費用**照 10-18 裁示**：顯示雲端自己的幣別（美元）、不換算……」（第 46 行）→ 送出畫面不加任何金額或換算。
- 「13. （10-21 拷問二）……**雲端用戶不裝代理**——平台主機自己跑 Nextflow、雲端憑證放平台主機檔案（不進資料庫）」（第 52 行）→ 憑證只在平台主機檔案；使用者端什麼都不用裝。
- 「14. （10-21 拷問三）**B 級部分自合**：網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」（第 54 行）→ 本任務不動網頁畫面。
- 本任務交辦原話（developer-agent，2026-10-28）：「平台主機自己跑 Nextflow（awsbatch executor），雲端使用者不裝站台代理……本機 head script 匯出 `AWS_SHARED_CREDENTIALS_FILE`、awsbatch 的 Nextflow config、workDir `s3://`、以 `head.pid` 取消，以及 gcb 開過的 clean／upload／cloud_store 路徑各自決定現在做或不做。」→ 每條路徑都要有明確決定（作法 1 的表）；Nextflow 設定鍵一律照官方文件（環境事實）。

## 範圍：檔案（只准改這些）
平台側（不啟動任何程式）：
- `platform/abf_platform/compute_envs.py`（`PLATFORM_HOST_TYPES` 加 awsbatch、`CHECK_ONLY_TYPES` 拿掉；加逐型別放行表；:450 的檢查分派、:691 的 `snapshot` 改成逐型別；aws 的送出欄位）
- `platform/abf_platform/jobs.py`（:110–113 改用逐型別放行表；`put_upload` 仍只限 Google Batch）
- `platform/abf_platform/cloud_store.py`（:52 `workdir_bucket` 只認 Google Batch，其餘不動——見作法 1）
- `platform/abf_launch/build.py`（加 `is_aws`；`launch_screen`:685／`cancel_screen`:713 依型別分派；aws 的 `aws_launch_screen`；`prepare_resume`:525／`prepare_relaunch`:569 對 aws 拒絕）
- `platform/abf_launch/cli.py`（只在顯示「Slurm 工作編號」處依型別換用詞；Slurm、gcb 輸出一字不變）
- `platform/abf_platform/cli.py:419`、`actions/*`、`cloud_cost.py`：**不改**（看 gate 行為，見作法 1）

站台代理側：
- `platform/abf_station/launch.py`（加 `AWS`、`AWS_RUNS`、`AWS_FILE_NAMES`、`_check_aws_ce`、`_aws_config`、`_aws_head_script`、`_check_aws_samplesheet`、`render_aws_bundle`；:1136 `run_launch` 與 :1308 `run_resume` 的分派／拒絕加 aws；`snapshot_ce`:158 加 aws 分支；:541 `GCB = PLATFORM_HOST_TYPES[0]` 改成不靠位置）
- `platform/abf_station/aws_launch.py`（新；代理端送出與取消，鏡像 `gcb_launch.py`，重用其小工具）
- `platform/abf_station/gcb_launch.py`（**只**把 `run_cancel`:225 抽成 `_cancel_head(ctx, bundle, runs_dir, reminder)`，gcb 的行為與訊息位元級不變；見裁決 2）
- `platform/abf_station/cancel.py`（:28 旁加 aws 分派）
- `platform/abf_station/handlers.py`（只確認 aws 的預檢分支在；`clean.py`、`put_upload.py` 不改）
- `platform/abf_station/fetch.py`（:18 `_NOT_RECORDS` 加 `aws.config`）
- `platform/abf_station/site.py`、`agent.py`：**不改**（`start_detached`:121、`run_fixed`:96 夠用）

測試與文件：
- `platform/tests/test_aws_launch.py`（新）
- `platform/tests/test_aws_ce.py`（aws-ce-type 新增；只改「必須更新的既有斷言」列的幾處）
- `platform/tests/test_cloud_upload.py`、`test_station_clean_gcb.py`、`test_gcb_launch.py`、`test_gcb_ce.py`：**只准加**「gcb 行為不變」的斷言，不准改既有斷言
- `docs/PLATFORM.md`（型別表與新增「Launching on AWS Batch」小節）、`docs/SEQERA_PARITY.md`（AWS Batch 那列）、`docs/TESTING.md`（新增「aws-launch」小節含手動驗收）、`docs/INSTALL.md` 或 `docs/OPERATIONS.md` 雲端小節（平台主機要 Java 17+、Nextflow、aws CLI）
- `specs/aws-launch/ledger.md`（新，executor 進度帳本）

## 作法
1. **共用閘門逐型別放行（本任務最容易出錯處）**。把 awsbatch 搬進 `PLATFORM_HOST_TYPES` 之前，先查 gcb 打開過的每一條路，決定 aws 現在給不給：

   | 路徑（origin/v3 位置） | gcb 現況 | aws 本任務的決定 |
   |---|---|---|
   | 送出 `launch_nextflow`（`jobs.py:110` 清單） | 開 | **開**（本任務主體） |
   | 取消 `cancel_run`（同上） | 開 | **開** |
   | 預檢 `preflight`（同上；`handlers.py:67–71`、`cli.py:419 cmd_ce_preflight`） | 開 | **開**（aws-ce-type 已做 `aws_preflight`；本任務只確認 `PLATFORM_HOST_TYPES` 搬動後 `ce preflight` 仍等得到答案） |
   | `pipeline_files`（同上；`handlers.py:64` 只讀公開 GitHub 檔，不碰環境、不碰憑證） | 開 | **開**（唯讀、與雲端無關；擋它沒有好處） |
   | 清理 `clean_work`（`jobs.py:110`；`clean.py:108` 分派 `_clean_gcb`:189，用 `gcloud storage ls/rm --recursive`，:217、:235） | 開 | **關**。理由：`clean.py` 的 aws 版要用 `aws s3 rm --recursive`，那條指令的官方文件這次**沒查**；刪遠端檔是不可逆動作，不在查證前上線。需要時另開 `aws-clean` 任務（見裁決 3） |
   | 上傳 `put_upload`（`jobs.py:112`；`put_upload.py:176–180` 用 `gcloud storage cp -` 串流；`cloud_store.py:52,60`） | 開 | **關**。見裁決 3：技術上可行（`aws s3 cp - s3://…`，環境事實），但要新做 `cloud_store` 的 s3 解析、前綴、`put_upload` 的 aws 傳輸與大小核對，是獨立功能 |
   | 資料集 `--destination`（`actions/datasets.py:116`，經 `cloud_store.workdir_bucket`） | 開 | **關**（隨 `cloud_store` 保持 gcb 專用） |
   | 費用預估（`actions/__init__.py:1100`、`cloud_cost.py:19 CLOUD`） | 只 gcb | **不做**（C-3）；aws 送出畫面明寫「沒有費用預估與上限」 |
   | 續跑／原樣重跑（`build.py:417`、`launch.py:1308`、`GCB_NO_RESUME` :87） | gcb 拒 | **拒**（同款訊息，`AWS_NO_RESUME`） |
   | 其餘 `list_site_files`／`fetch_run_records`／`read_task_log` | gcb 拒（尚未支援） | **拒**（同款訊息，把「Google Batch」換成型別名） |

   作法：`compute_envs.py` 新增 `GOOGLE_BATCH = "googlebatch-platform"` 常數與逐型別放行表 `CLOUD_JOB_KINDS = {GOOGLE_BATCH: (…六種不變…), AWS: ("preflight","launch_nextflow","cancel_run","pipeline_files")}`（`AWS` 為 aws-ce-type 在該檔定義的 awsbatch 常數，執行者以合併後實名為準）；`jobs.py:110` 改查此表，拒絕訊息用 `compute_envs.KINDS[platform]` 的型別名；`jobs.py:112` 的 `put_upload` 只收 `GOOGLE_BATCH`；`cloud_store.py:52` 改為 `ce.get("platform") != compute_envs.GOOGLE_BATCH`（gcb 的訊息與行為不變）；`compute_envs.py:450` 的 `elif platform in PLATFORM_HOST_TYPES: _check_gcb(…)` 改為 gcb 走 `_check_gcb`、aws 走 aws-ce-type 的 aws 檢查（不可讓 aws 設定被 `_check_gcb` 判）；`compute_envs.py:691 snapshot` 的 `in PLATFORM_HOST_TYPES` 分支改為 gcb 保持原樣、aws 回 `{name, platform, credentialsId, region, workDir, jobQueue, spot, maxvCpus}`（鍵名以 aws-ce-type 為準，不含任何憑證內容）；`launch.py:541 GCB = PLATFORM_HOST_TYPES[0]` 改為 `GCB = compute_envs.GOOGLE_BATCH`（元組變兩項後 `[0]` 不再可靠），新增 `AWS = compute_envs.AWS`。`CHECKABLE`（:36）自動含 aws，`ce create`／`ce preflight` 的行為由 aws-ce-type 已測的路徑決定，本任務只加不退化的斷言。
2. **送出的入口完全沿用**：`build.prepare_launch`:136 → `jobs.check_run_name` → 確認頁 → `jobs.enqueue_launch` → 代理 `claim`。`primary_environment`:114（只選 slurm）**不改**：使用者要送去 AWS 必須明講環境名字，避免「只有一個可用環境就自動花錢」（裁決 5）。`cancel_run` 不要求 `available`（與 Slurm、gcb 相同）。
3. **aws 的內容包（`launch.render_aws_bundle`，純函式，與 `render_gcb_bundle`:722 並列，不改 Slurm、gcb 兩條）**。鍵與 gcb 相同、**沒有** `account`；`files` 五個檔：`samplesheet.csv`、`params.yaml`、`nextflow.config`、`aws.config`、`head.sh`。
   - `ce`＝`snapshot_ce` 對 aws 的版本：`name, platform, region, workDir, jobQueue, spot, maxvCpus, environment, nextflowConfig`（`preRunScript`／`postRunScript` 非空 → 沿用 `NO_SCRIPTS` launch.py:78 拒絕）。**沒有** `credentialsId` 的內容、金鑰路徑（credentialsId 只是名字，進內容包無妨，但不是必要就不放；以 gcb 版為準）。
   - `run_folder`＝本機 `<storage_root>/_aws_runs/<run_name>`（`AWS_RUNS = "_aws_runs"`，與 `GCB_RUNS = "_gcb_runs"` :542 並列；`storage_root` 來自 `own_facts`:954，沒有 → `BundleError` 白話請設 `storage_root`）。資料夾放 `head.sh`、`aws.config`、`params.yaml`、`samplesheet.csv`、`tower.token`、`head.pid`、`head.out`、`.nextflow*`；不放結果。
   - Nextflow 工作目錄與輸出在 S3：`work_uri＝<ce.workDir>/runs/<run>/work`、`outdir＝<ce.workDir>/runs/<run>/results`；`params.yaml` 的 `input` 為 `run_folder/samplesheet.csv`（同 `_gcb_params_yaml`:680）。每個 run 一個前綴。
   - 平台與代理用同一函式、同樣輸入各建一次，**不相等就拒絕**（沿用 gcb 的重建比對）；內容包不得含代理主機專屬路徑或祕密。
4. **`aws.config`（`_aws_config`）**——只寫下列鍵，每一個都對照官方文件（出處見「環境事實」）；使用者的 `nextflowConfig` 原文留在 `nextflow.config`，以 `-c nextflow.config -c aws.config` 疊加，**後者勝**：
   | 內容 | 來源欄位 | Nextflow 鍵 |
   |---|---|---|
   | `process.executor = 'awsbatch'` | 固定 | `process.executor` |
   | `process.queue = 'lab-queue'` | `jobQueue` | `process.queue`（AWS 頁：job queue 以 `process.queue` 或 `queue` directive 指定） |
   | `aws.region = 'eu-west-1'` | `region` | `aws.region`（文件：須與 Batch 環境同區） |
   | `workDir = 's3://lab-bucket/work/runs/<run>/work'` | `workDir`＋run | 頂層 `workDir`（文件：必須在 S3 bucket 內且**至少含一層子目錄**，所以裸 bucket `workDir` 在送出時拒絕，見 6） |
   | `process.resourceLimits = [cpus: N]` | `maxvCpus` 有值才寫 | 單一 task 的 cpus 上限，**不是**總 vCPU 上限（同 gcb 裁決 6）。注意：此指令在官方 process 參考頁只有一句話說明（見環境事實），executor 手動驗收時核對；不接受就拿掉並記入 ledger |
   - `spot`：**不寫任何 Nextflow 鍵**。官方文件：Spot 由 AWS 端綁在 job queue 的 compute environment 決定，「No additional Nextflow configuration is required」。`spot` 欄位只存放、顯示於畫面（「是否 Spot 由 AWS 的 job queue 決定，這個欄位只是備註」）。
   - **不寫** `aws.accessKey`／`aws.secretKey`／`aws.profile`（憑證只走程序環境，見 5）、不寫 `aws.batch.cliPath`（見 7 與裁決 4）、不寫 `aws.batch.maxSpotAttempts`（維持預設 0）、不用 Fusion／Wave（授權與設定超出範圍，見不做）。
   - 所有值寫入前逐一用單引號字串嚴格驗證（`region`、`jobQueue`、`workDir` 重用 aws-ce-type 的格式檢查，在建包時再驗一次）；檔尾沿用 `OVERWRITE_BLOCK`:71 到 `nextflow.config`。
5. **憑證與主控程序環境**：金鑰檔路徑＝aws-ce-type 新增的 `credentials_path(settings_file)`（環境變數 `ABF_STATION_AWS_CREDENTIALS`，預設 `<部署資料夾>/_personal/aws-credentials`，讀 `[default]` 設定檔）。啟動前代理**重做 aws-ce-type 的 `credential_file` 與 `credential_shape` 兩項**，並重跑 `aws_preflight.run_preflight`（唯讀；`identity`、`job_queue`、`bucket`），不過就拒絕。主控程序環境由代理明確組出：`os.environ` 去掉所有 `ABF_*`、`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_SESSION_TOKEN`、`AWS_PROFILE`、`AWS_DEFAULT_PROFILE`、`AWS_SHARED_CREDENTIALS_FILE`、`TOWER_ACCESS_TOKEN`，再加 `AWS_SHARED_CREDENTIALS_FILE=<路徑>`、`AWS_PROFILE=default`、`AWS_CONFIG_FILE=os.devnull`（與 aws-ce-type 預檢環境一致）、`AWS_DEFAULT_REGION=<region>`，以及 CE `environment` 中 `head: true` 的項目。路徑**不寫進 `head.sh`、不進 argv、內容包、結果訊息**；回給平台的任何文字先過 aws-ce-type 的 `_scrub`。**重要未決：Nextflow 官方文件從未提到 `AWS_SHARED_CREDENTIALS_FILE`**（只有 AWS SDK 文件提到），見待裁決 1；此任務的實作先照交辦寫，手動驗收第 3 步是這點的判決。
6. **輸入資料**：samplesheet 的路徑欄位（`path_cells`:233 的判定沿用）每格必須是 `s3://<workDir 的 bucket>/<物件路徑>`；本機路徑、`http(s)://`、`gs://`、含 `..`、控制字元、BIDI 字元一律在建包時拒絕，訊息指出「把檔案放進 bucket 是之後的功能；現在請自己用 `aws s3 cp` 放進去」（字串分兩段寫，原始碼不放完整上傳指令，仿 `NO_BUCKET_PATH`:550）。`workDir` 若為裸 bucket（`s3://bucket`）→ 送出時拒絕並說明 Nextflow 的規定，不改 aws-ce-type 的建立時驗證。
7. **`head.sh`（`_aws_head_script`，是代理執行的那份，也是畫面顯示的那份）**：`#!/bin/bash`、註解行 `# credentials: the agent sets AWS_SHARED_CREDENTIALS_FILE from its own credentials file; the path is not part of this script`、`umask 077`、`cd <run_folder> || exit 1`、`export` CE 的 head 環境變數（loopback 時 `NXF_OPTS` 附 `-Dhttp.nonProxyHosts=`，同 `GCB_LOOPBACK_OPTS`:549）、`export TOWER_ACCESS_TOKEN="$(cat tower.token)"`，最後一行 `exec nextflow run <pipeline> -r <rev> -name <run> -params-file params.yaml -c nextflow.config -c aws.config -with-tower <endpoint>`。**AWS CLI 的需求**：awsbatch 用 AWS CLI 在 S3 與 task 容器之間搬檔（AWS 頁），所以 Batch 的 compute AMI（或容器）要有 aws CLI；本任務**不**寫 `aws.batch.cliPath`（文件查不到預設值），由手動驗收第 2 步確認，失敗才走裁決 4。
8. **代理端送出（`aws_launch.run_launch(job, ctx, bundle)`）**，順序與 gcb 相同、每步失敗就停、不重試：確認已過（launch.py:1130 `run_launch` 開頭）→ 重建比對 → 期限、`/proc`、Java 17+／Nextflow（重用 `gcb_launch._check_tools`:98）、aws CLI 存在（`run_fixed(["aws","--version"])`）、`aws_preflight` → 建 700 資料夾（已存在拒絕）→ 五檔＋`tower.token` 以 `O_EXCL|O_NOFOLLOW` 600 寫入（重用 `gcb_launch._write_new`:55）→ `site.start_detached(["bash", <run_folder>/head.sh], env, cwd, <run_folder>/head.out)` → 寫 `head.pid` → 等 `_settle_seconds`（重用 `gcb_launch._settle_seconds`:91，同一個環境變數 `ABF_STATION_GCB_SETTLE_SECONDS`，見裁決 2）→ 成功回 `{"ok": True, "slurm_job_id": <pid>, "run_name", "run_folder", "message": "已啟動：主控程序編號（pid）%d，run 名稱 %s，專屬資料夾 %s；AWS Batch 的工作與費用從現在開始計"}`。`slurm_job_id` 欄位名不改、不做 migration（同 gcb 裁決 2）。
9. **取消**：`cancel.py:28` 旁加 aws 分派。`gcb_launch.run_cancel`（:225）抽成 `_cancel_head(ctx, bundle, runs_dir, reminder)`，gcb 與 aws 各傳自己的 `runs_dir`（`GCB_RUNS`／`AWS_RUNS`）與提醒句；檢查順序不變（資料夾＝`<storage_root>/<runs_dir>/<run>`、`head.pid` 相符、`ps` 恰一行、擁有者、`-name <run>`、`/proc/<pid>/cwd`），通過才 `os.kill(pid, SIGTERM)` 一次。aws 的提醒句：「取消請求已送出（主控程序 pid %d）；請到 AWS Console 的 Batch 頁確認 job 都已結束，沒取消乾淨的工作仍會計費」。**Nextflow 收到 SIGTERM 是否取消 Batch job，官方頁面查不到**（沿用 gcb 的處理：手動驗收第 5 步判決）。
10. **畫面**：`aws_launch_screen` 欄位：管線、版本、環境、代理、run 名稱、專屬資料夾（本機）、AWS 區域、job queue、工作目錄（s3://…/work）、結果位置（s3://…/results）、Spot 備註、單一 task cpus 上限（若有）、samplesheet、`params.yaml`、`nextflow.config`、`aws.config`、`head.sh`。**第一段（「送出確認」標題後）必須逐字含**：「費用：按下 y 之後，這個 run 會在 AWS 區域 <region> 的 job queue <queue> 上建立 Batch 工作與運算資源，**由 AWS 向實驗室的 AWS 帳號收費**。平台目前還沒有費用預估與上限；實際金額請看 AWS 的帳單。主控程序跑在平台主機上，取消請用平台的取消指令。」不得出現金額、`NT$`、`USD`、`US$`、`TWD`。`cancel_screen` 對 aws 同 gcb 方式改用「主控程序編號（pid）」並附殘留工作提醒。Slurm、gcb 畫面位元級不變。
11. **文件**：`PLATFORM.md` 型別表 awsbatch 的 Supported 欄改為 `Slurm-like confirmed launch and cancel on the platform host (resume, clean, upload: not yet)`；新增「Launching on AWS Batch」小節（誰跑什麼、平台主機要 Java 17+／Nextflow／aws CLI 與憑證檔、`storage_root`、samplesheet 要 `s3://` 且同 bucket、`aws.config` 鍵表（作法 4）、費用白話段、取消與殘留提醒、AMI 要有 aws CLI、不能續跑／清理／上傳）。`SEQERA_PARITY.md` 那列改為 `Have (create + check + launch + cancel; resume, clean, upload not yet)`，勾選**維持 `[ ]`** 直到他在自己的帳號上跑通。範例只用 `lab-bucket`、`eu-west-1`、`lab-queue`、`aws-lab`，不放真實帳號 ID、金鑰、信箱。
12. **migration：不需要**。理由同 gcb：`launches.slurm_job_id` 是可空 `INTEGER` 無型別 CHECK、`jobs.kind` 與 `confirmations.kind` 不新增、`compute_envs` 沒有新欄位（aws 的鍵都在 `config` JSON 內，由 aws-ce-type 已定）。以 `test_no_migration_is_needed_for_aws_launch` 鎖住表結構。

## 失敗先行測試（`platform/tests/test_aws_launch.py`，現在都會紅；全部用假的 `start_detached`／`run_fixed`、`tmp_path` 當 `storage_root`，不碰網路、不啟動真程式；測試輸入一律是 fake：`lab-bucket`、`eu-west-1`、`lab-queue`、`aws-lab`）
閘門（本任務最重要的一組）：
- `test_aws_environment_accepts_exactly_preflight_launch_cancel_and_pipeline_files`：對可用的 aws 環境 `check_target` 輸入 `launch_nextflow`／`cancel_run`／`preflight`／`pipeline_files` → 不丟例外；輸入 `clean_work`、`put_upload`、`list_site_files`、`fetch_run_records`、`read_task_log` → `JobRefused`，訊息含「尚未支援」與型別名 `AWS`，不含 `Google Batch`、不含「set an agent」。
- `test_google_batch_still_accepts_its_six_kinds_and_nothing_else`：gcb 環境對 `clean_work`、`put_upload` 等六種仍放行、其餘仍拒，訊息文字與搬動前位元級相同（以 gcb 既有測試的期望字串為準）。
- `test_cloud_store_stays_google_only`：`cloud_store.workdir_bucket({"platform": AWS, "config": {"workDir": "s3://lab-bucket/work"}})` → `CloudPathError`，訊息仍是 gcb 的那句；`upload_prefix`／`object_url`／`big_file_command` 對 aws 同樣丟錯。
- `test_a_dataset_destination_cannot_be_an_aws_environment`：`actions.datasets` 的 destination 填 aws 環境名 → 白話拒絕。
- `test_put_upload_and_clean_work_jobs_cannot_be_queued_for_aws`：`jobs.enqueue_*` 直接對 aws 環境排 `put_upload`／`clean_work` → 被拒、jobs 表列數不變；代理端 `clean.run_clean` 收到 platform 為 aws 的內容包 → `Refusal`（不落到 `rules.clean_environment`）。
- `test_platform_host_types_has_two_entries_and_nothing_indexes_it_by_position`：`PLATFORM_HOST_TYPES` 含 gcb 與 aws；`launch.GCB == "googlebatch-platform"`、`launch.AWS == "awsbatch"`；原始碼 `abf_platform/`、`abf_station/` 沒有 `PLATFORM_HOST_TYPES[`。
- `test_check_dispatch_sends_each_type_to_its_own_check`：`validate` 一個 aws 設定（`region=eu-west-1, workDir=s3://lab-bucket/work, jobQueue=lab-queue`）通過；同樣設定改 `platform` 為 gcb → 因缺 `project` 被拒；反向亦然（aws 設定不會被 `_check_gcb` 判）。
- `test_snapshot_of_an_aws_environment_has_no_credential_content`：`snapshot` 結果的鍵集合固定，值中搜不到金鑰字串（金鑰標頭以字串拼接組出，不寫字面）。
確認與憲法：
- `test_unconfirmed_aws_launch_is_refused_and_nothing_is_written_or_started`（無憑證／雜湊不符／已用過／種類是 `cancel` 各一次 → `refused`，`tmp_path` 無新檔，`start_detached` 0 次）。
- `test_a_person_must_say_yes_an_aws_launch_is_never_auto_queued`；`test_primary_environment_never_auto_picks_aws_and_naming_it_works`。
- `test_the_platform_package_starts_no_program_and_holds_no_submission_word`（沿用 gcb 同名測試的掃描範圍，再加 `aws_launch.py` 不含 `nextflow run`、`sbatch`、`subprocess`）；`test_the_launch_allow_list_still_has_one_entry`。
- `test_no_cloud_library_is_imported_and_no_new_dependency`：`pyproject.toml` 無 `boto3`／`botocore`；原始碼無 `import boto3`（TC-085）。
- `test_another_users_aws_environment_and_run_are_not_found_for_launch_and_cancel`（讀與寫各一條）。
內容包與畫面：
- `test_aws_bundle_has_the_five_files_and_the_expected_keys`：鍵集合＝gcb 版（無 `account`）；`files` 為 `samplesheet.csv, params.yaml, nextflow.config, aws.config, head.sh`。
- `test_aws_config_has_exactly_the_documented_keys`：合法 CE（`region=eu-west-1, jobQueue=lab-queue, workDir=s3://lab-bucket/work, maxvCpus=16, spot=true`）、run 名稱 `r1` → `aws.config` 恰為：`process.executor = 'awsbatch'`、`process.queue = 'lab-queue'`、`aws.region = 'eu-west-1'`、`workDir = 's3://lab-bucket/work/runs/r1/work'`、`process.resourceLimits = [cpus: 16]`，**不含** `aws.batch.`、`aws.accessKey`、`aws.secretKey`、`aws.profile`、`spot`；未設 `maxvCpus` 時沒有 `resourceLimits` 行。
- `test_spot_is_a_note_only_and_the_screen_says_aws_decides`。
- `test_a_hostile_value_cannot_break_out_of_the_config_text`（`jobQueue`／`region`／`environment` 值含引號、換行、`}`）；`test_a_bare_bucket_work_dir_is_refused_at_launch_with_nextflows_rule`（`s3://lab-bucket` → 拒絕）。
- `test_samplesheet_paths_must_be_s3_urls_of_the_work_bucket`：`s3://lab-bucket/x.fastq.gz` 過；`/home/x.fastq.gz`、`gs://lab-bucket/x`、`https://…`、`s3://other/x`、`s3://lab-bucket/../x` 各被拒，訊息提到 `aws s3`；非路徑欄位不受影響。
- `test_outdir_and_work_are_per_run_s3_prefixes`；`test_run_folder_is_under_storage_root_in_aws_runs_and_a_missing_storage_root_is_refused`。
- `test_head_script_is_the_one_that_is_shown_and_run`：最後一行含 `-c nextflow.config -c aws.config`、`-with-tower`、`-name <run>`；全文不含金鑰路徑、不含 `AWS_SHARED_CREDENTIALS_FILE=`（只允許出現在註解行的名稱，不含值）、不含 `sbatch`。
- `test_the_screen_says_aws_bills_the_lab_in_its_first_paragraph`（含「由 AWS 向實驗室的 AWS 帳號收費」、區域、queue；不含金額字樣）。
- `test_the_slurm_and_gcb_screens_and_bundles_are_byte_identical_to_before`。
憑證：
- `test_the_credentials_path_is_only_in_the_process_environment`：假 `start_detached` 記下 `argv, env, cwd`；路徑只在 `env["AWS_SHARED_CREDENTIALS_FILE"]`；`env["AWS_PROFILE"] == "default"`；`env` 不含 `ABF_*`、`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_SESSION_TOKEN`、`TOWER_ACCESS_TOKEN`（測試先把這些放進 `os.environ` 再斷言被剝除）。
- `test_no_marker_of_the_credentials_file_reaches_a_result_a_message_or_the_database`（唯一標記字串放進憑證檔，跑完整流程後在結果、`left_on_site`、DB 位元組都搜不到；憑證鍵名以字串拼接組出，`tests/credentials_stay_in_settings_test.sh` 會掃字面）。
- `test_a_missing_open_or_malformed_credentials_file_stops_the_launch_before_anything_is_written`（缺檔／權限 644（`skipif win32`）／缺 `aws_secret_access_key` 行 → 拒絕、資料夾不存在、`start_detached` 0 次）。
啟動與取消：
- `test_launch_writes_head_pid_and_reports_it_as_the_job_number`；`test_an_existing_run_folder_is_never_overwritten`；`test_a_link_in_the_run_folder_is_never_followed`；`test_a_head_that_dies_at_once_is_reported_with_its_scrubbed_tail`。
- `test_missing_java_nextflow_or_aws_cli_stops_the_launch_in_plain_words`（三項各一；訊息說明要裝什麼）。
- `test_cancel_sends_one_sigterm_to_exactly_the_verified_process`（結果含「AWS Console」）；`test_cancel_refuses_and_sends_nothing_when_the_process_is_gone_the_owner_differs_the_name_differs_or_the_cwd_differs`（`os.kill` 0 次）；`test_cancel_refuses_when_head_pid_does_not_match_the_bundle`；`test_cancel_of_an_aws_run_in_a_gcb_runs_folder_is_refused`（`_gcb_runs` 資料夾對 aws 內容包不符）。
- `test_gcb_cancel_after_the_refactor_is_byte_identical`（把 `_cancel_head` 抽出後，gcb 的訊息與檢查順序不變，直接重跑 gcb 既有取消案例）。
- `test_resume_and_relaunch_of_an_aws_run_are_refused_in_plain_words`（平台 `prepare_*` 與代理 `run_resume` 各一）；`test_fetch_run_records_does_not_list_aws_config_as_a_record`。
其他：`test_tool_list_unchanged_and_no_new_web_route`（MCP 工具仍 12 個）、`test_no_migration_is_needed_for_aws_launch`、`test_docs_describe_the_launch_the_billing_sentence_and_the_requirements`（PLATFORM.md 含 `aws.config` 每個鍵、費用段、Java／Nextflow／aws CLI、`storage_root`、`s3://`；範例無真實帳號 ID）。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
- aws-ce-type 新增的測試中，釘住「awsbatch 在 `CHECK_ONLY_TYPES`、不能送出」的斷言（例：`CHECK_ONLY_TYPES == (AWS,)`、送出被拒且訊息含「尚未支援」）：以前＝awsbatch 只能檢查；以後＝`CHECK_ONLY_TYPES` 變空元組、`launch_nextflow`／`cancel_run` 放行，其餘種類仍拒。執行者在合併後的 `test_aws_ce.py` 逐條找，**找不到的不要硬改**，PR 說明列出實際動到的函式名。
- `platform/tests/test_launch_bundle.py`（第 450 行用 awsbatch 測「尚未支援」）與 `test_launch_cli.py:306-312`（awsbatch「尚未支援」）：這兩處在 gcb-launch 計畫裡被標為「awsbatch 仍不支援」而不准動。**本任務正好讓它們變成錯的**——以前＝awsbatch 送出被拒「尚未支援」；以後＝改用 Azure／K8s 類型（仍不支援）當被拒範例，斷言其餘不變。理由：測試的本意是「不支援的型別被拒」，awsbatch 已支援所以換例子。（行號取自 gcb-launch.md 當時的 v3，執行者先 `git show origin/v3:` 核對再改。）
- `test_cloud_upload.py::test_workdir_bucket_needs_a_google_batch_environment`（:453 附近）：預期**不用改**（`cloud_store` 保持 gcb 專用）；若因元組變兩項而紅，只改被誤判的那一個比較式，不放寬訊息。
- `test_gcb_ce.py::test_nothing_of_the_later_slices_exists` 等掃描全原始碼的斷言：若因新增 `aws_launch.py`、`_aws_config` 而紅，只准在例外清單加 aws 的檔名，不准刪掃描。
- 確認**不會**變紅、不准改：`test_gcb_launch.py`、`test_station_clean_gcb.py`、`test_cleanup_confirm.py`、`test_pipeline_files_queue.py`、`test_station_launch.py`、`test_station_cancel.py`、`test_scope.py`（新檔需 `# Nothing existing:` 標頭）、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`。

## 完成標準（done when）
- 自動：上面所有新測試綠；全套綠（含 `tests/platform_test.sh`、`no_second_run_state_test.sh`、`credentials_stay_in_settings_test.sh`）；已知環境紅 `test_tc047_tc051` 依 README 通例視同綠；MCP 工具仍 12；Slurm 與 gcb 的內容包、畫面、`head.sh`、取消訊息位元級不變。
- 手動（維護者，aws-ce-type 的 `available` 完成後做一次；**會花很小一筆錢**——先確認 AWS Budgets 警示已設）：
  1. 平台主機（WSL）有 Java 17+、Nextflow、aws CLI；`storage_root` 已設；憑證檔在 `ABF_STATION_AWS_CREDENTIALS` 指的位置（600）。
  2. 確認 job queue 的 compute AMI 有 aws CLI（AWS 頁：Nextflow 靠它搬檔）。**失敗現象**＝task 在 stage 階段報找不到 `aws`；失敗就停手回報，走裁決 4，不自行加設定。
  3. 送出一個最小的 samplesheet（兩三個很小的檔，已用 `aws s3 cp` 放進 `workDir` 同 bucket）：`abf-launch … --ce aws1`；**送出畫面第一段必須看到「由 AWS 向實驗室的 AWS 帳號收費」**；答 y 才開始。**這步同時判決待裁決 1**：若主控程序報認證失敗（Nextflow 沒讀 `AWS_SHARED_CREDENTIALS_FILE`），記入 ledger 並回報，不要自行改成別的憑證做法。
  4. 看到 `已啟動：主控程序編號…`；`<storage_root>/_aws_runs/<run>` 有 `head.pid`、`head.out`；AWS Console 的 Batch 頁出現 job；平台 run 頁出現進度（`-with-tower` 通）；跑完 `s3://…/runs/<run>/results` 有輸出。
  5. 再送一個，中途取消：確認 Batch 頁的 job 被終止（**判決 SIGTERM 是否讓 Nextflow 取消 Batch job**；沒取消乾淨就記入 ledger 回報，不要自行加 `aws batch terminate-job`，那是第二條寫入路徑，需另開任務）。
  6. 在資料庫、`ce show`、畫面、日誌、`head.sh` 搜不到憑證任何片段與憑證檔路徑。
  7. 核對 `process.resourceLimits = [cpus: N]` 在 awsbatch 上被接受（不報未知指令）；結果寫進 ledger。
- 文件：作法 11 的各份文件更新；`TESTING.md` 的「aws-launch」小節寫明手動驗收 1–7 與「驗收者看 `git diff --name-only`，既有測試只動計畫列的幾處」。

## 環境事實
（取自 `git show origin/v3:<path>`，head 2233693，2026-10-28 讀；官方文件 2026-10-28 讀，`nextflow.io/docs/latest/*.html` 會轉址到 `docs.seqera.io/nextflow/*`）

**共用閘門與可重用的 gcb 實作（origin/v3）**
- `platform/abf_platform/compute_envs.py`：`PLATFORM_HOST_TYPES = ("googlebatch-platform",)` :35、`CHECKABLE` :36、驗證分派 :450（`elif platform in PLATFORM_HOST_TYPES: _check_gcb`）、`snapshot` :691（`in PLATFORM_HOST_TYPES` 回 gcb 欄位）、`_GCB_CONFIG` 未知鍵訊息 :327。
- `platform/abf_platform/jobs.py:110`（gcb 六種放行清單，其餘拒「尚未支援」）、:112–113（`put_upload` 非 `PLATFORM_HOST_TYPES` 拒）、:119–126（無代理、離線、`launch_nextflow`／`list_site_files`／`put_upload` 須 `available`）。
- `platform/abf_platform/cloud_store.py`：`parse_gs`（只收 `gs://`）、`workdir_bucket`:52（`in PLATFORM_HOST_TYPES` 且 `gs://`）、`upload_prefix`、`object_url`、`inside_prefix`、`big_file_command`、`stream_into`。`platform/abf_platform/cli.py:419`（`ce preflight` 條件）。`actions/__init__.py:1100`、`actions/datasets.py:116`、`cloud_cost.py:19`（皆 gcb 專用）。
- `platform/abf_station/launch.py`：`GCB_NO_RESUME`:87、`snapshot_ce`:158（gcb 分支 :163）、`render_bundle`:490（gcb 分派 :494）、`GCB = PLATFORM_HOST_TYPES[0]`:541、`GCB_RUNS`:542、`GCB_FILE_NAMES`:543、`GCB_CREDENTIALS_COMMENT`:544、`GCB_FORBIDDEN_ENV`:546、`GCB_LOOPBACK_OPTS`:549、`NO_BUCKET_PATH`:550、`_check_gcb_ce`:560、`_gcb_config`:639、`_gcb_head_script`:662、`_gcb_params_yaml`:680、`_check_gcb_samplesheet`:687、`render_gcb_bundle`:722、`own_facts`:954、`verify_confirmation`:974、`run_launch`:1130（gcb 分派 :1136）、`run_resume`:1302（gcb 拒絕 :1308）。
- `platform/abf_station/gcb_launch.py`：`_proc_cwd`:47、`_write_new`:55、`_head_env`:80、`_settle_seconds`:91、`_check_tools`:98、`_check_environment`:122、`run_launch`:147、`run_cancel`:225。`cancel.py`：`KEYS`:14、`run_cancel`:24（分派 :28）。`clean.py`：分派 :108、`_clean_gcb`:189、`gcloud storage ls/rm` :217/:235。`put_upload.py`：`run_put`:144、`_transfer`:168、`gcloud` 檢查 :176、`start_fed(["gcloud","storage","cp","-",…])` :180。`site.py`：`run_fixed`:96、`wait_for_exit`:109、`start_detached`:121、`start_fed`:187。`fetch.py`：`_NOT_RECORDS`:18。`handlers.py`：`JOB_KINDS`:16、gcb 預檢分支 :67–71、`pipeline_files` :64。
- `platform/abf_launch/build.py`：`primary_environment`:114、`target_problem`:126、`prepare_launch`:136、`is_gcb`:270、`prepare_cancel`:276、`prepare_resume`:525、`prepare_relaunch`:569、`gcb_launch_screen`:629、`launch_screen`:685、`cancel_screen`:713；gcb 判斷散在 :314、:374、:417、:687、:714、:749。`platform/abf_launch/cli.py:200,237,267`（依型別換用詞處）。
- **aws-ce-type 新增（合併後才存在，名字以合併實況為準）**：`CHECK_ONLY_TYPES`、`aws_preflight`（私有工具取自 `gcb_preflight`）、`ABF_STATION_AWS_CREDENTIALS`、`<部署資料夾>/_personal/aws-credentials`、`[default]` 設定檔、設定鍵 `region`／`workDir`（`s3://`）／`jobQueue`／`spot`／`maxvCpus`、預檢七項 `credential_name, credential_file, credential_shape, aws, identity, job_queue, bucket`、預檢環境 `AWS_SHARED_CREDENTIALS_FILE／AWS_PROFILE／AWS_CONFIG_FILE=os.devnull／AWS_DEFAULT_REGION`。
- 憲法：`nextflow run` 只准在 `launch.py`、`subprocess` 只准在 `site.py`；新 `.py` 檔前 40 行要 `# Nothing existing: …`（TC-070）；TC-085 禁 `boto3`／`botocore`，所以 AWS 操作一律經 `site.run_fixed` 或 `site.start_fed` 呼叫 `aws` CLI。`aws_launch.py`、`test_aws_launch.py` 檔頭理由：「搜過 Nextflow 的 `awsbatch` executor、Seqera `tw launch`、nf-core `tower launch`，它們都是把工作交給 Seqera 服務，沒有現成可由本機代理在確認後啟動並取消的做法」。

**Nextflow awsbatch 設定鍵（逐鍵對官方文件）**
- `process.executor = 'awsbatch'`；`process.queue`（或 `queue` directive）指定 job queue；`aws.region` 須與 Batch 環境同區；`workDir` 必須在 S3 bucket、至少含一層子目錄（`s3://<bucket>/work` 可、`s3://<bucket>` 不可）；可從本機或 EC2 啟動；Spot 在 AWS 端綁 compute environment，「No additional Nextflow configuration is required」；啟動端所需 IAM 動作清單（Batch：CancelJob、DescribeComputeEnvironments、DescribeJobDefinitions、DescribeJobQueues、DescribeJobs、ListJobs、RegisterJobDefinition、SubmitJob、TagResource、TerminateJob，及 EC2/ECS/ECR 唯讀）：https://docs.seqera.io/nextflow/aws
- `aws.region`、`aws.profile`（「AWS profile from `~/.aws/credentials`」）、`aws.accessKey`、`aws.secretKey`；`aws.batch.cliPath`（「The path where the AWS command line tool is installed in the host AMI」，**頁面未寫預設值，查不到**）；`aws.batch.maxSpotAttempts`（預設 0，24.10 起由 5 改 0）；`aws.batch.retryMode`（預設 `standard`）、`maxTransferAttempts`（預設 1）、`delayBetweenAttempts`（預設 10 sec）、`maxParallelTransfers`（預設 4）、`logsGroup`（預設 `/aws/batch/job`）：https://docs.seqera.io/nextflow/reference/config/aws 。**本計畫只寫入前四行表中的鍵（`process.executor`、`process.queue`、`aws.region`、`workDir`）加可選的 `process.resourceLimits`；其餘一律不寫。**
- `aws.batch.cliPath` 的敘述（Nextflow 用 `aws` CLI 在 S3 與 task 容器間搬檔；CLI 可裝在容器映像或自訂 AMI；host 上 `aws` 的「祖父目錄」會以同路徑掛進容器）與「用 Fusion 則不需要 CLI」：https://docs.seqera.io/nextflow/aws 。Fusion／Wave：`fusion.enabled` 預設 false、需授權：https://docs.seqera.io/nextflow/reference/config/fusion 、https://docs.seqera.io/nextflow/fusion 。**頁面未說明 Wave 是否一定要開，查不到；本任務不採用。**
- `process.resourceLimits`：官方 process 參考頁只有一句話說明，沒有 AWS Batch 的細節：https://docs.seqera.io/nextflow/reference/process （所以手動驗收第 7 步實測）。
- **查不到**：Nextflow 是否讀 `AWS_SHARED_CREDENTIALS_FILE`。Nextflow 的驗證順序（https://docs.seqera.io/nextflow/amazons3 ，Authentication）：①config 的 `aws.accessKey`／`aws.secretKey` ②`aws.profile`／`AWS_PROFILE`／`AWS_DEFAULT_PROFILE` 指的自訂 profile（`$HOME/.aws/credentials` 或 config）③環境變數 `AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY`（可加 `AWS_SESSION_TOKEN`）④web identity token ⑤`~/.aws/credentials` 的 `default` profile ⑥SSO ⑦container credentials ⑧EC2 instance profile；全找不到＝匿名（只能讀公開 bucket）。整頁**沒有**出現 `AWS_SHARED_CREDENTIALS_FILE`。只有 AWS SDK 文件說明該變數改變憑證檔位置（對 SDK 與 CLI）：https://docs.aws.amazon.com/sdkref/latest/guide/file-location.html ；其中 JVM 系統屬性 `aws.sharedCredentialsFile` 僅列於 Java SDK v2。→ 對 `aws` CLI 有效有據；對 Nextflow 的 JVM 只是推論。
- **查不到**：SIGTERM 時 Nextflow 是否取消 Batch job（上列頁面都沒寫）；`aws s3 rm --recursive` 與 `aws s3api head-object` 的官方文件（這次沒查，所以清理與上傳後的大小核對都不在本任務）。

**用 AWS CLI 上傳到 S3（不用 boto3；本任務不做，只記可行性）**
- `aws s3 cp - s3://bucket/key` 可把標準輸入串流上傳；`--expected-size`（位元組）只在串流超過 50GB 時需要，現有上限 `UPLOAD_LIMIT = 2_000_000_000`（`cloud_store.py`）遠低於它，不需要；串流與 `--recursive` 不相容（下載方向）：https://docs.aws.amazon.com/cli/latest/reference/s3/cp.html 。對應 `put_upload.py:180` 的 `gcloud storage cp -` 做法（`site.start_fed`）。要做時需新增 s3 版的位置解析、前綴與大小核對，是獨立任務（裁決 3）。

**平台主機現實**：取消靠 `/proc/<pid>/cwd`，所以代理主機須是 Linux 或 WSL（沒有 `/proc` → 送出前白話拒絕，同 gcb）。

## 不做
- 不做費用：不估價、不設上限、不加 AWS 價目表、不動 `cloud_cost.py`（C-3）；畫面只有「AWS 會計費」的白話，沒有數字。
- 不做本機檔案上傳到 S3、不做資料集 `--destination` 對 aws、不做 `aws s3 rm` 清理（見裁決 3）；samplesheet 只收 `s3://` 且同 bucket。
- 不做續跑、原樣重跑、`list_site_files`、`fetch_run_records`、`read_task_log` 對 aws（白話拒絕）。
- 不寫 `aws batch terminate-job` 之類第二條寫入路徑；不在平台裡加 worker、執行緒、常駐迴圈。
- 不用 Fusion／Wave、不設 `aws.batch.cliPath`、不設 `aws.batch.platformType`／`jobRole`／`executionRole`（Fargate）、不做 `aws.batch.volumes`、不用 `aws.accessKey`／`aws.secretKey`／`aws.profile` 寫進任何檔。
- 不改 Slurm、gcb 的任何一個位元組行為（`gcb_launch.run_cancel` 的抽出須位元級等價）；不改 aws-ce-type 的預檢清單與驗證規則；不碰 Azure／K8s。
- 不新增 MCP 工具、網頁路由或畫面（只改 `launch_screen`／`cancel_screen` 文字）；不改 `hello` 與 `clean_facts`。

## 裁決與待裁決（2026-10-28，developer-agent 的 subagent 起草；與上文衝突時以本段為準）
**預設已採（可推翻）**
1. **沿用 gcb 的整套設計**（代理端 `aws_launch.py`、內容包樣板留在 `launch.py`、`slurm_job_id` 存 pid 不做 migration、`start_detached` 不用 `nohup`／`setsid`、只送一次 SIGTERM、`primary_environment` 不自動選 aws、失敗時資料夾保留、`maxvCpus` 落為單一 task 上限）。理由同 gcb-launch 裁決 1–10。
2. **`gcb_launch.run_cancel` 抽成共用 `_cancel_head`，不複製一份**；`_check_tools`、`_write_new`、`_settle_seconds`（同一個 `ABF_STATION_GCB_SETTLE_SECONDS`）等小工具直接從 `gcb_launch` 匯入。理由：取消的核對順序是安全關鍵，複製兩份會各自演化。代價：gcb 取消路徑被動到，以 `test_gcb_cancel_after_the_refactor_is_byte_identical` 把關。**另一選項**：複製一份（零風險、多 70 行）。預設：抽共用。
3. **清理與上傳對 aws 都關，不隨 `PLATFORM_HOST_TYPES` 自動打開。** 理由：①`clean.py` 與 `put_upload.py`、`cloud_store.py` 全部寫死 `gs://` 與 `gcloud`；②刪遠端檔不可逆，而 `aws s3 rm` 的官方文件這次沒查；③上傳雖可行（環境事實），仍是獨立功能。**後續任務建議**：`aws-clean`（對應 C-7）、`aws-upload`（對應 C-6）。**另一選項**：本任務一併做上傳（可行，約多半個任務量）。預設：不做。
4. **`aws.batch.cliPath` 不做成環境欄位**（YAGNI；文件查不到預設值）。手動驗收第 2 步若證明 AMI 找不到 `aws`，才回報並另開小任務加選填鍵 `cliPath`（需改 aws-ce-type 的未知鍵清單與測試）。
5. **aws 不被自動選為預設環境**（`primary_environment` 不改）。
6. **`spot` 只是備註**：Nextflow 無對應鍵，Spot 由 AWS 端 compute environment 決定（官方文件）。畫面明講，避免使用者以為這個欄位會切換 Spot。
7. **新檔標頭**：`aws_launch.py`、`test_aws_launch.py` 前 40 行要有 `# Nothing existing: …`。
8. **派工順序**：aws-ce-type 合併 → 本任務；與 `compute_envs.py`、`jobs.py` 同車道任務、`abf_station/*` 的 L1 任務、C-3 不可平行。

**待裁決（需要維護者或 developer-agent 回答；執行者遇到就停手回報，不自行決定）**
- **待裁決 1（最重要）：憑證怎麼交給 Nextflow。** 交辦原話是匯出 `AWS_SHARED_CREDENTIALS_FILE`，但 Nextflow 官方文件從不提這個變數（只有 AWS SDK 文件提到，且對 Nextflow 的 JVM 只是推論）。預設照交辦寫，由手動驗收第 3 步判決。若失敗，備選：(a) 代理讀憑證檔後只在程序環境設 `AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY`（文件第③順位，明確有寫；憑證仍不進 argv／檔案，但值會在程序環境裡）；(b) 把 `HOME` 指到一個只放該憑證檔的私有目錄，吃第⑤順位 `default` profile。(a) 較穩、(b) 較貼近檔案不進環境的原則；兩者都偏離「匯出 `AWS_SHARED_CREDENTIALS_FILE`」，要他點頭。
- **待裁決 2：`aws` CLI 要不要成為 Batch compute AMI 的明文前提。** 官方只說 Nextflow 靠 CLI 搬檔、可裝在 AMI 或容器；預設值查不到。本計畫把它寫進文件與手動驗收，不寫進程式。要不要改成預檢多一項（需動 aws-ce-type 的七項清單）？預設：不加。
- **待裁決 3：清理與上傳是否在本任務一併做**（裁決 3 的另一選項）。預設不做；他若要「雲端跑通」的最小閉環含刪 work，應另開 `aws-clean`。
- **待裁決 4：`CHECK_ONLY_TYPES` 變空元組是否保留。** 搬完後它是空的；刪掉會動 aws-ce-type 的 import 與測試，保留空元組零風險但留下死碼。預設：保留空元組並加一行註解，下一個類型（Azure／K8s）上線時再用。
- **待裁決 5：費用。** AWS 沒有 gcb 那樣的 C-3 估價；是否允許在沒有任何上限的情況下由他自己的帳號跑第一次？預設：允許，理由同 gcb（第一個真實使用者是他自己），但 AWS Budgets 警示必須先設（手動驗收前提）。


### 裁決（2026-10-28 10:30 developer-agent；與上文及上面待裁決衝突時，以本段為準）
A1. 憑證：照主案，設 `AWS_SHARED_CREDENTIALS_FILE`＋`AWS_PROFILE=default`（承 aws-ce-type 裁決 8）。不採備案 (a)：把金鑰放進程序環境變數，會在 /proc 看得到。手動驗收第 3 步若證明 JVM 不讀這個變數，就另開任務改走備案 (b)（把 HOME 指到私有目錄）。本任務不預先實作備案。
A2. 不寫 `aws.batch.cliPath`，預檢也不加第 8 項；把「Batch compute AMI 要有 aws CLI」寫進 PLATFORM.md，並放進手動驗收。
A3. AWS 的清理與上傳這次維持關閉，另開 aws-upload、aws-clean 兩件任務。
A4. 把 gcb 的 run_cancel 抽成共用的 `_cancel_head`。gcb 的既有測試一條都不准改，而且要全綠；有任何一條需要改，就退回改成複製一份。
A5. 保留空的 `CHECK_ONLY_TYPES`，並加註解說明「新雲端類型先放這裡，只開預檢」。
A6. 手動驗收（真的在 AWS 跑、會花錢）不屬於 executor／verifier 的完成標準：完成標準只認自動測試。真實試跑要等維護者點頭（C 級：花錢），並且先設好 AWS Budgets 警示。
A7. 接受：SIGTERM 能不能取消 Batch job、resourceLimits，都留在手動驗收判定。
A8. 計畫引用的測試行號（test_launch_bundle.py:450、test_launch_cli.py:306-312），executor 開工前要用 `git show origin/v3:` 重查；行號不對就以實際內容為準。aws-ce-type 新增的東西，要等它合進 v3 後才能派本件。


**A9（10-28 developer-agent，回應 verifier 合約階段 BLOCKED）以下既有斷言准許更新，是本任務的有意改變，閱卷不得判放水；PR 說明逐條寫以前／以後／理由。test_gcb_ce.py「只准加」規則對 (a) 例外：**
- (a) `platform/tests/test_gcb_ce.py` 釘型別常數的那幾行（v3 約 849–851）：以前 `PLATFORM_HOST_TYPES == (GCB,)`、`CHECK_ONLY_TYPES == ("awsbatch-platform",)`；以後 `PLATFORM_HOST_TYPES == (GCB, AWS)`、`CHECK_ONLY_TYPES == ()`，CHECKABLE 跟著改成兩者之和。理由：AWS 可以送出了。
- (b) `platform/tests/test_aws_ce.py::test_the_type_constants`：同 (a) 的以後值。
- (c) `test_aws_ce.py::test_jobs_other_than_the_preflight_are_refused_in_plain_words` 與 `::test_every_refusal_says_what_to_do_and_hides_internals`：launch_nextflow／cancel_run 改成「被放行」；仍被拒的工作（上傳、清理、resume）保留原斷言，訊息裡的任務名改成 `aws-upload`／`aws-clean`。理由：本任務只放行送出與取消。
- (d) `test_aws_ce.py::test_docs_list_every_aws_key_and_check`：以後的逐字值＝PLATFORM.md 表格 `checked and launched on the platform host (upload, clean, resume: not yet)`；399 行那句改成 `Slurm, Google Cloud Batch and AWS Batch can run; the other eleven types can be modelled only.`（前一句粗體同步改成 `Slurm, Google Cloud Batch and AWS Batch can run`）；SEQERA_PARITY 表格 `Have (create + check + launch + cancel); upload and clean in aws-upload / aws-clean`，第 84 行括號改 `(create + check + launch + cancel; resume not yet)`。
- 測試名 `test_platform_host_types_has_two_entries` 裡的字串以 `compute_envs.AWS` 的實值（`"awsbatch-platform"`）為準，計畫上文寫的 `"awsbatch"` 作廢。
- 行號一律用語意重新定位（函式名＋斷言內容），不靠行號。

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
