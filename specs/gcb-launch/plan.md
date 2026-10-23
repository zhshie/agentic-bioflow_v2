---
id: gcb-launch
title: 在 Google Batch 上送出與取消分析（確認流程同 Slurm；平台主機上的站台代理在本機跑 Nextflow 主控程序）
tier: B
kinds: backend
lane: L2-platform-ce
base: v3（C-1 PR #175 `feat/gcb-ce-type-2` 先合併；本任務從合併後的 v3 開分支）
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 3 的 C-2（拷問 10-21 第二輪第 13 點）；站台代理的取代做法見 memory/dev-plans/gcb-ce-type.md 裁決二 F–K
---

# gcb-launch

> 本檔由 developer-agent 寫（2026-10-24）。**只處理 C-2**：`googlebatch-platform` 環境可以被選去送出一次分析、可以取消。費用預估與上限是 C-3、本機檔案上傳到 bucket 是 C-6、續跑／原樣重跑／抓回 Nextflow 記錄是後續，**都不在本任務**。B 級（使用者看得到的新能力）→ verifier 通過＋CI 綠由 developer-agent 自合。
> **派工前提**：PR #175（C-1）已合併。**車道注意**：本任務同時改 `compute_envs.py` 一帶（L2）與 `platform/abf_station/*`（L1），不可與 L1 站台任務（M1-02～04、017c 站台側）或 C-3 平行（同檔會衝突）。
> **這份計畫與 replan 原文有三處不同**（原文是 C-1 拷問二之前寫的），都來自 C-1 裁決二 F–K：①不新增 `platform/abf_platform/local_runner.py`、不在平台裡放 worker（平台本身不啟動任何程式，憲法原則 2、`test_scope.py` TC-071）——執行者仍是站台代理，只是它裝在平台主機上；②不把 `_head_script` 拆成 `_slurm_head`／`_local_head` 並抽 `abf_launch/bundle_check.py`（見裁決 1）；③不用 `nohup setsid … &`（見裁決 3）。

## 目標
讓使用者像在 Slurm 上一樣：在送出畫面看到「全部會被送出的內容」，本人答 y 之後，平台主機上的站台代理在**本機**用 Nextflow 的 `google-batch` executor 啟動一次分析（主控程序在平台主機，計算工作由 Google Batch 的虛擬機跑），進度經 `-with-tower` 回到平台；需要時本人確認後可以取消。

為什麼這樣切：
1. 確認流程不另做一套：沿用 `prepare_launch` → 確認 → `launch_nextflow` job → 站台代理（`verify_confirmation` 的「確認憑證、雜湊、只用一次」全部沿用），所以「沒有本人答 y 就不啟動」自動成立（維護者要求）。
2. 平台程式（`abf_platform/`）一行都不啟動程式；所有啟動程式的碼在 `abf_station/`，且只有 `site.py` 真的呼叫 `subprocess`。
3. 憑證只經環境變數 `GOOGLE_APPLICATION_CREDENTIALS` 給主控程序，路徑是代理自己的設定（C-1 的 `ABF_STATION_GCP_CREDENTIALS`），不進 argv、不進資料庫、不進內容包、不進日誌。
4. 費用：Google 會向實驗室的 Google 帳號收費。本任務不估價、不設上限（C-3），但送出畫面必須白話寫明這件事，使用者答 y 前一定看得到。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`：
- 「4. 四種計算環境都建：nano4 → Google Batch（開發上限 NT$1,000/月）→ AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（第 40 行）→ 送出的是「一個 Run」，用的是已建好的環境＋憑證名字；不在送出時重新輸入憑證。
- 「Google Batch 雲端：等你開好 GCP 帳號（預算 NT$1,000）；費用顯示美元、每人每月上限、超過自動停。接著 AWS Batch、Azure／K8s。」（第 16 行）→ 費用與自動停是 C-3；本任務只負責「畫面上白話說明 Google 會計費」，且不得出現任何台幣換算。
- 「雲端費用**照 10-18 裁示**：顯示雲端自己的幣別（美元）、不換算、每人每月上限由管理者開帳號時設，NT$1,000 只是 GCP 帳單預算」（第 46 行）→ 送出畫面不加任何金額或換算。
- 「12. （10-21 拷問）雲端第一個真實使用者＝他自己的自費帳號；……年底若只能交兩塊＝**雲端跑通＋花費控制**與**網頁全流程（國網）**」（第 50 行）→ 「跑通」要在他自己的帳號上真的跑一次最小的分析（手動驗收）。
- 「13. （10-21 拷問二）託管＝**一間實驗室一台平台**（每實驗室一個 VPS／容器，程式不改，不做跨實驗室隔離；ADR 0005 不動）。站台代理：**國網用戶裝在個人電腦**（持 2FA）；**雲端用戶不裝代理**——平台主機自己跑 Nextflow、雲端憑證放平台主機檔案（不進資料庫）→ C-1／C-2 改為平台內建的 `local` 執行器，不經站台。」（第 52 行；其中「平台內建的 `local` 執行器」已被 C-1 裁決二 F、G 改為「平台主機上的站台代理」）→ 憑證只在平台主機檔案；使用者端什麼都不用裝。
- 「**C-2 `gcb-launch-platform`**（B／backend；10-21 他定：雲端用戶不裝站台代理）：平台主機自己當執行者……config 追加 `process.executor='google-batch'; google{project; location; batch.spot}`，`workDir` gs://）；`cancel` 以 `head.pid` 送 SIGTERM（Nextflow 自己取消 Batch jobs）；`-with-tower` 指 loopback 的 receiver。憑證：只在平台主機檔案（600），資料庫只存 `credentialName`；`credential_findings` 仍擋鍵值。golden 加 `gcb`；新測試 `test_local_runner.py`。」（第 167 行，節錄）→ 設定鍵、`head.pid`、SIGTERM 取消、`-with-tower`、憑證規則照辦；新測試檔名改為 `test_gcb_launch.py`（裁決 1）；「golden 加 `gcb`」見作法 12。
- 「14. （10-21 拷問三）**B 級部分自合**：網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」（第 54 行）→ 本任務不動網頁畫面。

## 範圍：檔案（只准改這些）
平台側（不啟動任何程式）：
- `platform/abf_platform/jobs.py`（`_target` 的 gcb 分支：放行 `launch_nextflow`、`cancel_run`；其餘種類仍白話拒絕；`clean_result` 不改）
- `platform/abf_platform/compute_envs.py`（只加 `snapshot` 對 gcb 的送出欄位；`maxvCpus` 落地不需改驗證）
- `platform/abf_launch/build.py`（`snapshot_ce` 呼叫處、`launch_screen`、`cancel_screen`、`prepare_resume`／`prepare_relaunch` 對 gcb 拒絕、編號用詞小函式；`primary_environment` 不改）
- `platform/abf_launch/cli.py`（只在顯示「Slurm 工作編號」的三處依環境類型換用詞，Slurm 的輸出一字不變）
- `platform/abf_platform/records.py`／`web*.py`：**不改**（進度仍由 Nextflow 的 tower 事件進來，與 Slurm 相同）

站台代理側（所有啟動程式的碼都在這裡）：
- `platform/abf_station/launch.py`（**唯一**保留 `nextflow run` 字樣與內容包樣板的檔案，憲法 LAUNCH_ALLOW 只有這一筆：加 `render_gcb_bundle`、`_gcb_head_script`、`_gcb_config`、`_check_gcb_samplesheet`；`run_launch` 開頭 `verify_confirmation` 之後依 `bundle["ce"]["platform"]` 分派）
- `platform/abf_station/gcb_launch.py`（新；代理端的送出與取消：重建內容包比對、寫本機專屬資料夾、啟動、記 pid、核對後送 SIGTERM；**不出現** `nextflow run`、`sbatch` 等字樣）
- `platform/abf_station/site.py`（只加 `start_detached(argv, env, cwd, out_path)`，與 C-1 的 `run_fixed` 並列；仍是唯一呼叫 `subprocess` 的檔案）
- `platform/abf_station/cancel.py`（`run_cancel` 開頭依 `ce.platform` 分派到 `gcb_launch.run_cancel`）
- `platform/abf_station/handlers.py`（只在 `JOB_KINDS` 的分派處接上；不新增種類）
- `platform/abf_station/fetch.py`（只把 `gcb.config` 加進 `_NOT_RECORDS`）
- `platform/abf_station/agent.py`：**不改**（`Context` 夠用）

測試與文件：
- `platform/tests/test_gcb_launch.py`（新）
- `platform/tests/test_gcb_ce.py`（只改「必須更新的既有斷言」列的幾處）
- `platform/tests/test_station_docs.py`（只在 parity 列斷言跟著 `SEQERA_PARITY.md` 新字樣時調整）
- `platform/tests/golden/`（若 `launch_screen`／內容包有 golden：新增 `gcb` 一份；Slurm 的 golden 一個位元都不准動）
- `docs/PLATFORM.md`（第 8 節型別表與「Google Cloud Batch」小節；新增「在 Google Batch 上送出」小節）
- `docs/SEQERA_PARITY.md`（F 節 Google Cloud Batch 那列）
- `docs/TESTING.md`（新增「gcb-launch」小節，含手動驗收）
- `docs/INSTALL.md` 或 `docs/OPERATIONS.md` 的雲端小節（平台主機要有 Java 17+、Nextflow、gcloud；C-1 裁決 4 已預告在 C-2 補）
- `specs/gcb-launch/ledger.md`（新，executor 進度帳本）

## 作法
1. **放行的種類（jobs.py `_target`，PR 上的 :86）**：gcb 環境收到 `preflight`、`launch_nextflow`、`cancel_run` → 往下走既有檢查（有 agent、agent 在線、`launch_nextflow` 須 `available`）；收到 `list_site_files`／`fetch_run_records`／`read_task_log` → 仍 `JobRefused`，白話：`%s is a Google Batch environment: this job kind is not built for it yet (尚未支援)`（拿掉「下一步 C-2」，因為 C-2 做完了）。`cancel_run` 不要求 `available`（跟 Slurm 一樣：環境之後壞了，也要能取消已經在跑的）。
2. **送出的入口完全沿用**：`build.prepare_launch` → `jobs.check_run_name` → `_ask`（確認頁，網頁與終端機同一條）→ `jobs.enqueue_launch` → 代理 `claim`。`primary_environment`（build.py:109）**不改**，仍只自動選 Slurm：使用者要送去 Google Batch 必須**明講環境名字**（`--ce gcb1`／網頁選那一個），避免「只有一個可用環境就自動花錢」（裁決 5）。
3. **gcb 的內容包（`launch.render_gcb_bundle`，純函式，與 `render_bundle` 並列，不改 Slurm 那條）**。形狀與 Slurm 相同的鍵：`version, agent, ce, run_name, run_folder, pipeline, revision, samplesheet, params, path_columns, tower, files, pipeline_source`，**沒有** `account`；`files` 有五個檔：`samplesheet.csv`、`params.yaml`、`nextflow.config`、`gcb.config`、`head.sh`。
   - `ce`＝`snapshot_ce` 對 gcb 的版本：`name, platform, project, location, workDir, spot, bootDiskSize, bootDiskImage, serviceAccountEmail, network, subnetwork, usePrivateAddress, labels, maxvCpus, environment, nextflowConfig`（`preRunScript`／`postRunScript` 非空 → 沿用 `NO_SCRIPTS` 拒絕）。
   - `run_folder`＝**代理主機上的本機路徑** `<storage_root>/_gcb_runs/<run_name>`（`storage_root` 是代理 `hello` 已回報的 fact，launch.py:518 `own_facts`；沒有 → `BundleError`，白話說「請在部署設定檔設 storage_root」）。這個資料夾放 `head.sh`、`gcb.config`、`params.yaml`、`samplesheet.csv`、`tower.token`、`head.pid`、`head.out`、`.nextflow*`；**不放結果**。
   - Nextflow 的工作目錄與輸出都在 bucket：`work_uri＝<ce.workDir>/runs/<run_name>/work`、`outdir＝<ce.workDir>/runs/<run_name>/results`（`_params_yaml` 的 gcb 版把 `input` 寫成 `run_folder/samplesheet.csv`、`outdir` 寫成 gs:// 那一個）。每個 run 一個前綴，之後 C-7 才能只刪這個 run 的 work。
   - 平台與代理各自用同一個函式、同樣的輸入（平台用 hello 回報的 facts、代理用自己的設定）建一次，**不相等就拒絕**（沿用 launch.py `run_launch` 的重建比對），所以內容包裡**不得出現代理主機專屬的路徑或祕密**（金鑰檔路徑只在代理端，內容包看不到，見 5）。
4. **`gcb.config`（`_gcb_config`）**——由 CE 的欄位產生，使用者的 `nextflowConfig` 原文留在 `nextflow.config`，兩者以 `-c nextflow.config -c gcb.config` 疊加，**後者勝**（平台管的鍵不能被自由文字蓋掉）。鍵名都對照 Nextflow 文件（見「環境事實」的來源）：
   | 內容 | 來源欄位 | Nextflow 鍵 |
   |---|---|---|
   | `process.executor = 'google-batch'` | 固定 | `process.executor` |
   | `workDir = 'gs://…/runs/<run>/work'` | `workDir`＋run 名稱 | 頂層 `workDir`（文件：須是 Cloud Storage 路徑且「至少含一層子目錄」，所以裸 bucket 的 `workDir` 在這裡拒絕，見 7） |
   | `google.project`、`google.location` | `project`、`location` | `google.project`、`google.location` |
   | `google.batch.spot = true` | `spot` 為真才寫 | `google.batch.spot` |
   | `google.batch.bootDiskSize = 50.GB` | `bootDiskSize`（C-1 存 `50 GB`／`50GB`）→ 轉成 `<整數>.GB` | `google.batch.bootDiskSize`（文件寫法 `50.GB`） |
   | `google.batch.bootDiskImage = '…'` | `bootDiskImage` | `google.batch.bootDiskImage` |
   | `google.batch.serviceAccountEmail = '…'` | `serviceAccountEmail` | `google.batch.serviceAccountEmail` |
   | `google.batch.network`、`google.batch.subnetwork` | `network`、`subnetwork` | 文件接受完整 URL、`projects/{p}/global/networks/{n}`、`global/networks/{n}`（子網路對應 `…/regions/{r}/subnetworks/{s}`）。C-1 允許短名稱 `default`：短名稱原樣交給 Nextflow，**executor 在手動驗收時核對** Batch 是否接受，不接受就在 `_gcb_config` 補成 `global/networks/<名>`／`regions/<location>/subnetworks/<名>` |
   | `google.batch.usePrivateAddress = true` | `usePrivateAddress` 為真才寫 | `google.batch.usePrivateAddress` |
   | `process.resourceLabels = [ … ]` | `labels` ＋固定一組 `abf-run=<run 名稱前 63 字>` | `process.resourceLabels`（文件只說它是「附在 task 上的 name-value」，**沒寫 Google Batch 是否支援**，executor 以實跑核對；不支援就把整段拿掉並在 ledger 記下，C-1 的 `labels` 欄位不動） |
   | `process.resourceLimits = [cpus: N]` | `maxvCpus` | **只限制單一 task 的 cpus 不超過 N，不是全部 vCPU 的總上限**（Nextflow 沒有同名的總量鍵；總量上限屬 C-3）。畫面與文件都這樣寫，不假裝成總上限（裁決 6） |
   - 不寫 `google.batch.maxSpotAttempts`（維持 Nextflow 預設；文件寫預設 0，以前是 5）、不寫 `executor.queueSize`（預設 Google Batch 為 1000）。
   - 所有值寫入前逐一用單引號字串跳脫（含 `\`、`'`、換行都拒絕或跳脫，沿用 launch.py 對 `_yaml_scalar` 的嚴格態度）；`labels` 的鍵值 C-1 已限 `[a-z0-9_-]`，這裡仍再驗一次。
   - 檔尾沿用 `OVERWRITE_BLOCK` 到 `nextflow.config`（不是 `gcb.config`），行為與 Slurm 相同。
5. **憑證**：金鑰檔路徑＝`gcb_preflight.credentials_path(settings_file)`（C-1，已是代理自己的設定）。啟動前代理**重做 C-1 的 `credential_file` 與 `credential_shape` 兩項**（存在、一般檔案、權限 600、型別是 service account、鍵齊全、`project_id` 與環境相符）；不過就拒絕並沿用 C-1 的白話訊息。主控程序的環境變數是**明確組出來的**：`os.environ` 去掉所有 `ABF_*` 與 `GOOGLE_APPLICATION_CREDENTIALS`、去掉 `TOWER_ACCESS_TOKEN`，再加上 `GOOGLE_APPLICATION_CREDENTIALS=<路徑>`、`CLOUDSDK_CORE_DISABLE_PROMPTS=1`，以及 CE 的 `environment` 中 `head: true` 的項目（規則同 Slurm 的 `_check_ce`）。路徑**不寫進 `head.sh`、不進 argv、不進內容包、不進結果訊息**。主控程序的 stdout／stderr 導向 `head.out`（600），回給平台的任何訊息先過 `gcb_preflight._scrub`。
6. **`head.sh`（`_gcb_head_script`，在 launch.py，是代理要執行的那一份、也是畫面上顯示的那一份）**：
   - `umask 077`、`cd <run_folder> || exit 1`、`export` CE 的 head 環境變數（含 NXF_OPTS 的 loopback 規則：endpoint 是 loopback 時附加 `-Dhttp.nonProxyHosts=`，同 launch.py:360 起的做法）、`export TOWER_ACCESS_TOKEN="$(cat tower.token)"`。
   - 最後一行：`exec nextflow run <pipeline> -r <revision> -name <run> -params-file params.yaml -c nextflow.config -c gcb.config -with-tower <endpoint>`（pipeline、revision 用同一組 `_check_pipeline`／`_check_revision`；`-r` 只收固定版本，同 Slurm）。
   - 檔內有一行註解：`# credentials: the agent sets GOOGLE_APPLICATION_CREDENTIALS from its own key file; the path is not part of this script`，讓使用者知道有憑證、但看不到路徑。
7. **輸入資料（裁決 4：要 `gs://`）**：samplesheet 的「路徑欄位」（`path_cells` 的判定規則沿用）每一格必須是 `gs://<bucket>/<物件路徑>`，且 `<bucket>` 必須等於該環境 `workDir` 的 bucket；`/…` 本機路徑、`http(s)://`、`s3://`、含 `..`、控制字元、BIDI 字元的格子一律在建內容包時拒絕，訊息白話並指出「把檔案放進 bucket 是之後的功能（C-6 上傳），現在請自己用 `gcloud storage cp` 放進去」。非路徑欄位（如 strandedness）不受影響。`params` 值不檢查路徑（跟 Slurm 一致，Slurm 也只檢 samplesheet 與 `_confine` 的上傳區）。`workDir` 若沒有子目錄（`gs://bucket` 裸 bucket）→ 在送出時拒絕並說明 Nextflow 的規定，**不改 C-1 的建立時驗證**。
8. **代理端送出（`gcb_launch.run_launch(job, ctx, bundle)`）順序**，每一步失敗就停、不重試：
   1. `verify_confirmation(job, ctx, "launch")` 已在 `launch.run_launch` 開頭通過（沒有確認憑證／雜湊不符／用過 → 在這之前就拒絕，沒有任何檔案、程式）。
   2. 重建比對（作法 3）。
   3. 前置檢查：工作期限剩餘（`_left`、`MIN_REMAINING` 同 Slurm）；金鑰檔（作法 5）；`run_fixed(["nextflow","-version"], …)` 與 `run_fixed(["java","-version"], …)`（Java ≥ 17，沿用 `handlers._parse_java`／`_parse_nextflow`）；再跑一次 C-1 的 `run_preflight`（`gcloud` 的唯讀 `batch jobs list`、`storage ls`），不通過就拒絕。**Java／Nextflow 檢查只放在送出前，不加進 C-1 的預檢清單**（C-1 的 `CHECK_NAMES` 與其測試不動，裁決 7）。
   4. 本機建專屬資料夾：`os.mkdir`（已存在 → 拒絕，不覆蓋）、權限 700；五個檔加 `tower.token` 以 `O_CREAT|O_EXCL|O_NOFOLLOW`、權限 600 寫入。寫入失敗 → `error`，訊息列出殘留的資料夾（`left_on_site`），尚未啟動。
   5. 啟動：`site.start_detached(["bash", "<run_folder>/head.sh"], env, cwd=<run_folder>, out_path=<run_folder>/head.out)`＝`subprocess.Popen(argv 列表, shell=False, start_new_session=True, stdin=DEVNULL, stdout/stderr→head.out)`。**不用 shell、不用 `nohup`／`setsid` 這些字**（裁決 3）；啟動後主控程序獨立於代理（代理重啟不會殺它）。把 pid 寫入 `head.pid`（600）。
   6. 啟動後等最多 5 秒（可由 `ABF_STATION_GCB_SETTLE_SECONDS` 調，測試用 0）：若程序已結束（例如 Java 壞掉）→ `error`，訊息 = 結束碼＋`head.out` 末 300 字（先 `_scrub`），資料夾保留。
   7. 成功 → `("done", {"ok": True, "slurm_job_id": <pid>, "run_name": run, "run_folder": folder, "message": "已啟動：主控程序編號（pid）%d，run 名稱 %s，專屬資料夾 %s；Google Batch 的工作與費用從現在開始計"})`。**結果裡的 `slurm_job_id` 欄位名不改**（平台 `clean_result`／`_apply_handover` 與 `launches` 表都靠它，見裁決 2 與 migration 一節），意思是「這次送出的工作編號」，gcb 上是 pid。
9. **取消（`gcb_launch.run_cancel`，由 `cancel.run_cancel` 分派）**——鏡像 Slurm 的「先確認是那一個工作才動手」：
   1. `verify_confirmation(job, ctx, "cancel")`；`set(bundle) == KEYS`（不變）。
   2. 資料夾必須等於 `<storage_root>/_gcb_runs/<run>`（用代理自己的 `storage_root` 重算，不信 bundle）；`head.pid` 內容必須等於 bundle 的編號。
   3. **一次查詢**：`run_fixed(["ps","-o","user=","-o","args=","-p",<pid>], …)`＋讀 `/proc/<pid>/cwd`：①查不到 → 拒絕「已結束，不取消」；②擁有者必須是代理自己的使用者；③`args` 必須含 `-name <run>`；④`cwd` 必須是專屬資料夾。任何一項不符 → `Refusal`，**不送任何訊號**（防 pid 被回收給別的程式）。
   4. 通過才 `os.kill(pid, signal.SIGTERM)` **一次**，不重試、不迴圈、不 `kill -9`、不殺行程群組之外的東西。Nextflow 收到 SIGTERM 會自己終止並取消它送出去的 Batch 工作（replan 原文如此寫；Nextflow 文件沒有逐字寫這點，所以列為手動驗收項，見完成標準）。
   5. 回 `("done", {"ok": True, "slurm_job_id": pid, "run_name": run, "message": "取消請求已送出（主控程序 pid %d）；請到 Google Cloud Console 的 Batch 頁確認沒有殘留的工作，沒取消乾淨的虛擬機仍會計費"})`。
   - 平台側 `_apply_handover` 對 `cancel_run` 用 `slurm_job_id` 欄位寫 `cancel_requested_at`：因為我們沿用同欄位，**平台程式不用改**。
10. **送出畫面與取消畫面（`build.launch_screen`／`cancel_screen` 對 gcb 的版本）**：Slurm 畫面一字不動；gcb 的 `launch_screen` 欄位為：管線、版本、環境、代理、run 名稱、專屬資料夾（本機）、**Google 專案、區域、工作目錄（gs://…/work）、結果位置（gs://…/results）、Spot 與否、單一 task 的 cpus 上限（若有）**、samplesheet、`params.yaml`、`nextflow.config`、`gcb.config`、`head.sh`。**必須有的一段白話（verifier 逐字比對關鍵語）**：
    > 「費用：按下 y 之後，這個 run 會在 Google Cloud 專案 <project> 裡建立 Batch 工作與虛擬機，**由 Google 向實驗室的 Google Cloud 帳號收費**。平台目前還沒有費用預估與上限；實際金額請看 Google 的帳單。主控程序跑在平台主機上，取消請用平台的取消指令。」
    - 這段在畫面的最上方（「送出確認」標題之後第一段），不只在文件裡；不得出現任何金額、台幣或美元數字。
    - `cancel_screen` 的標題與欄位對 gcb 改為「主控程序編號（pid）」並附同樣的提醒句（殘留的 Batch 工作要自己確認）。
11. **續跑、原樣重跑**：`prepare_resume`／`prepare_relaunch`（build.py:380、412）對 gcb 環境的 run 白話拒絕：`Google Batch 的 run 還不能續跑或原樣重跑（尚未支援）`；代理端 `run_resume` 的入口也再擋一次（防繞過）。
12. **golden 與既有行為**：Slurm 的內容包、畫面、`head.sh` 位元級不變（既有 golden／`test_launch_bundle.py`／`test_station_launch.py` 全部原樣綠，是驗收標準）；為 gcb 另加一組 golden（`gcb_bundle.json` 與畫面文字）。若 repo 目前沒有 launch 的 golden 目錄，改成在 `test_gcb_launch.py` 內寫期望字串，不新建 golden 機制。
13. **文件**：`docs/PLATFORM.md` 第 8 節型別表 `googlebatch-platform` 的 Supported 欄改成 `Slurm-like confirmed launch and cancel on the platform host (resume: not yet)`；「Only Slurm can run…」那句改成 `Slurm and Google Cloud Batch can run; the other types can be modelled only`；新增「Launching on Google Batch」小節：誰在跑什麼（主控程序在平台主機、計算在 Batch）、平台主機要有 Java 17+／Nextflow／gcloud 與金鑰檔、`storage_root` 要設、samplesheet 要 `gs://` 且同 bucket、`gcb.config` 欄位對照表（作法 4）、費用由 Google 向實驗室帳號收的白話段、取消與殘留工作的提醒、不能續跑、參考基因組建議用 `--igenomes_base gs://gcp-public-data--igenomes`（nf-core 文件的做法；若 executor 查不到出處就不寫這句）。`docs/SEQERA_PARITY.md` 的列改成 `Have (create + check + launch + cancel; resume not yet)`，勾選**維持 `[ ]`** 直到他在自己的帳號上跑通（該節「a type turns supported only after a run on a real account」不變）。範例只用 `lab-project-1`、`runner@lab-project-1.iam.gserviceaccount.com`、`gs://lab-bucket/work`。
14. **migration：不需要**。理由：①`launches.slurm_job_id` 是 `INTEGER` 可空欄位，沒有型別專屬的 CHECK，gcb 的 pid 放得進去；②`jobs.kind` 的 CHECK 只列六個既有種類，沒有新增；③`confirmations.kind` 仍是 `launch`／`cancel`；④`compute_envs` 沒有新欄位。代價（欄位名說 slurm、裝的是 pid）已記在裁決 2，並以測試 `test_no_migration_is_needed_and_the_columns_are_unchanged` 鎖住「表結構不變」。

## 失敗先行測試（`platform/tests/test_gcb_launch.py`，現在都會紅；全部用假的 `start_detached`、假的 `run_fixed`、`tmp_path` 當 `storage_root`，不碰網路、不啟動真程式）
確認與憲法：
- `test_unconfirmed_gcb_launch_is_refused_and_nothing_is_written_or_started`：給代理一個 gcb 的 `launch_nextflow` job，沒有確認憑證／雜湊不符／憑證已用過／種類是 `cancel` 各一次 → `refused`；`tmp_path` 底下沒有任何新檔，假 `start_detached` 呼叫 0 次。
- `test_the_platform_package_starts_no_program_and_holds_no_submission_word`：掃 `abf_platform/` 與 `abf_station/` 除 `site.py`、`launch.py` 外的原始碼——沒有 `subprocess`、`Popen`、`os.system`、`nohup`、`setsid`、`nextflow run`、`sbatch`（呼應 TC-071 與 `tests/no_second_run_state_test.sh`）；`subprocess` 只在 `site.py`。
- `test_the_launch_allow_list_still_has_one_entry`：讀 `tests/no_second_run_state_test.sh`，`LAUNCH_ALLOW` 仍只有 `platform/abf_station/launch.py` 一筆、對應測試名仍是 `test_unconfirmed_launch_is_refused`（該檔既有測試，不改）。
- `test_a_person_must_say_yes_a_gcb_launch_is_never_auto_queued`：`request_launch`／`abf-launch` 對 gcb 在 `_ask` 之前不會有 `launch_nextflow` job；答 n、逾時、取消 → jobs 表列數不變。
平台側：
- `test_check_target_lets_launch_and_cancel_through_for_an_available_gcb_environment`、`test_check_target_still_refuses_listing_fetch_and_task_log_in_plain_words`（含「尚未支援」、不含「set an agent」）。
- `test_launch_on_a_gcb_environment_that_is_not_available_is_refused`（`invalid`／`creating`／`disabled`）、`test_cancel_needs_no_available_status`。
- `test_primary_environment_never_auto_picks_google_batch_and_naming_it_works`：只有一個 `available` gcb → `primary_environment` 為 None；`prepare_launch(ce="gcb1")` 成功。
- `test_another_users_gcb_environment_and_run_are_not_found_for_launch_and_cancel`（讀與寫各一條：B 用 A 的環境名送出被拒；B 取消 A 的 run 被拒）。
- `test_resume_and_relaunch_of_a_gcb_run_are_refused_in_plain_words`（平台 `prepare_*` 與代理 `run_resume` 各一條）。
內容包與畫面：
- `test_gcb_bundle_has_the_five_files_and_the_expected_keys`、`test_gcb_bundle_is_identical_when_built_twice_from_the_same_inputs`（平台與代理各建一次相等）、`test_a_changed_bundle_is_refused_by_the_agent`（改 `gcb.config` 一個字元／改 project／改 samplesheet）。
- `test_gcb_config_has_exactly_the_documented_keys`：用合法 CE（全欄）斷言 `gcb.config` 含 `process.executor = 'google-batch'`、`google.project`、`google.location`、`workDir = 'gs://lab-bucket/work/runs/<run>/work'`、`google.batch.spot = true`、`google.batch.bootDiskSize = 50.GB`、`serviceAccountEmail`、`network`、`subnetwork`、`usePrivateAddress`；未設 `spot` 時**沒有** `google.batch.spot` 行。
- `test_boot_disk_size_is_written_in_nextflow_units`：`50 GB`、`50GB` 都變 `50.GB`。
- `test_max_vcpus_is_written_as_a_per_task_limit_and_the_screen_does_not_call_it_a_total`。
- `test_labels_and_the_run_label_are_written_and_a_long_run_name_is_cut_to_63`。
- `test_a_hostile_value_cannot_break_out_of_the_config_text`：`labels` 值、`bootDiskImage`、`network` 含引號／換行／`}` → 建包時拒絕或被安全跳脫，產出的 `gcb.config` 只有預期的行數。
- `test_a_bare_bucket_work_dir_is_refused_at_launch_with_nextflows_rule`。
- `test_run_folder_is_under_storage_root_and_a_missing_storage_root_is_refused_in_plain_words`。
- `test_outdir_and_work_are_per_run_gs_prefixes`（`params.yaml` 的 `outdir`、`input`）。
- `test_head_script_is_the_one_that_is_shown_and_run`：畫面上的 `head.sh` 文字＝寫進資料夾並交給 `start_detached` 的檔案內容；最後一行含 `-with-tower`、`-c nextflow.config -c gcb.config`、`-name <run>`；不含 `sbatch`、`#SBATCH`。
- `test_the_screen_says_google_bills_the_lab_in_its_first_paragraph`：畫面第一段含「由 Google 向實驗室的 Google Cloud 帳號收費」關鍵語、專案名；不含 `NT$`、`USD`、`US$`、`TWD`、任何數字金額。
- `test_the_slurm_screen_and_bundle_are_byte_identical_to_before`（以既有 golden／固定輸入比對）。
- `test_samplesheet_paths_must_be_gs_urls_of_the_work_bucket`：`gs://lab-bucket/x.fastq.gz` 過；`/home/x.fastq.gz`、`s3://…`、`https://…`、`gs://other/x`、`gs://lab-bucket/../x` 各被拒，訊息提到 `gcloud storage cp`；非路徑欄位不受影響。
憑證：
- `test_the_key_path_is_only_in_the_process_environment`：假 `start_detached` 記下 `argv`、`env`、`cwd`；金鑰路徑只在 `env["GOOGLE_APPLICATION_CREDENTIALS"]`；不在 `argv`、不在 `head.sh`、不在內容包、不在 `head.out` 之外的任何回傳；`env` 不含 `ABF_*`、不含 `TOWER_ACCESS_TOKEN`。
- `test_no_marker_of_the_key_file_reaches_a_result_a_message_or_the_database`：金鑰檔放唯一標記字串；整個流程跑完，回給平台的結果、`left_on_site`、`launches`／`jobs` 的 DB 位元組都搜不到；金鑰標頭字串用字串拼接在測試裡組出（不寫字面，`tests/credentials_stay_in_settings_test.sh` 會掃）。
- `test_a_missing_or_open_or_wrong_project_key_file_stops_the_launch_before_anything_is_written`（缺檔／權限 644（`skipif win32`）／`project_id` 不符 → 拒絕、資料夾不存在、`start_detached` 0 次）。
啟動與取消：
- `test_start_detached_uses_a_fixed_argv_no_shell_and_a_new_session`：直接測 `site.start_detached`（monkeypatch `subprocess.Popen`）：`shell` 非真、`start_new_session=True`、`stdin` 為 DEVNULL、輸出到指定檔。
- `test_launch_writes_head_pid_and_reports_it_as_the_job_number`：結果 `slurm_job_id` ＝ 假 pid；`head.pid` 內容相同；`tower.token`、`head.pid` 權限 600、資料夾 700。
- `test_an_existing_run_folder_is_never_overwritten`、`test_a_link_in_the_run_folder_is_never_followed`（`O_NOFOLLOW`）。
- `test_a_head_that_dies_at_once_is_reported_with_its_scrubbed_tail`：假程序立刻結束 → `error`，訊息有結束碼與 `head.out` 末段，且金鑰型字串被 `[hidden]`。
- `test_missing_java_or_nextflow_stops_the_launch_in_plain_words`、`test_old_java_is_refused`。
- `test_the_platform_records_the_pid_in_the_launches_row`：走 `take_result` → `launches.slurm_job_id`＝pid。
- `test_cancel_sends_one_sigterm_to_exactly_the_verified_process`：假 `ps`／`/proc` 全符 → `os.kill` 呼叫恰 1 次、訊號 SIGTERM、pid 正確；結果含「請到 Google Cloud Console」。
- `test_cancel_refuses_and_sends_nothing_when_the_process_is_gone_the_owner_differs_the_name_differs_or_the_cwd_differs`（四條各一，`os.kill` 0 次）。
- `test_cancel_refuses_when_head_pid_does_not_match_the_bundle`、`test_cancel_refuses_an_unconfirmed_or_reused_confirmation`。
- `test_cancel_request_time_is_recorded_for_a_gcb_run`（`cancel_requested_at` 寫入）。
- `test_fetch_run_records_does_not_list_gcb_config_as_a_record`（`_NOT_RECORDS` 含 `gcb.config`）。
其他：
- `test_no_cloud_library_is_imported_and_no_new_dependency`（`pyproject.toml` 沒有 `google-cloud`；原始碼沒有 `import google`／`boto3`，呼應 TC-085）。
- `test_tool_list_unchanged_and_no_new_web_route`（MCP 工具仍 12 個）。
- `test_no_migration_is_needed_and_the_columns_are_unchanged`（`launches`、`compute_envs`、`jobs` 的欄位清單與 C-1 的 `test_no_migration_is_needed` 同）。
- `test_docs_describe_the_launch_the_billing_sentence_and_the_requirements`（PLATFORM.md 含 `gcb.config` 每個鍵、費用段、Java／Nextflow／gcloud、`storage_root`、`gs://`；範例沒有真實信箱）。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
釘住「gcb 不能送出」或「C-2 還沒做」的 C-1 測試：
- `platform/tests/test_gcb_ce.py::test_agent_jobs_other_than_the_preflight_are_refused_in_plain_words`：以前＝`list_site_files`／`launch_nextflow`／`cancel_run`／`fetch_run_records`／`read_task_log` 全拒絕且訊息含「尚未支援送出」與 `C-2`；以後＝只有 `list_site_files`、`fetch_run_records`、`read_task_log`（含 `enqueue_listing`）拒絕，訊息含「尚未支援」、不含 `C-2`、不含「set an agent」「has no agent」；`launch_nextflow` 與 `cancel_run` 改斷言**不被拒絕**（`check_target` 不丟例外）。理由：C-2 就是放行這兩種。
- `test_gcb_ce.py::test_launch_is_refused_and_the_environment_is_never_auto_picked`：以前＝第一行 `assert build.target_problem(ip.state_db, "gcb1", "launch_nextflow")`；以後＝該行改為 `is None`（`available` 且代理在線），函式改名 `test_launch_is_allowed_but_the_environment_is_never_auto_picked`；其餘（`primary_environment` 為 None、`ce primary` 可設、有 Slurm 時選 Slurm）**原樣不動**。
- `test_gcb_ce.py::test_nothing_of_the_later_slices_exists`：以前＝禁止 `local_runner.py` 檔名、禁止原始碼出現 `_local_head|head\.pid|local_runner`；以後＝這兩條拿掉（本任務正是要出現 `head.pid`），**保留**：沒有 `cloud_cost.py`／`rates.json`、沒有 `buckets create|services enable|service-accounts create|storage cp|storage rm`、`-with-tower` 不在 `abf_station/gcb_preflight.py`（C-1 的預檢檔仍不碰 Nextflow）。
- `test_gcb_ce.py::test_docs_list_every_gcb_key_and_check`：以前＝`PLATFORM.md` 要有「checked on the platform host (launch: not yet)」與「Only Slurm can run; Google Cloud Batch can be created and checked」；`SEQERA_PARITY.md` 那列要是「Have (create + check); launch in C-2」且以 `[ ] |` 結尾；以後＝換成作法 13 的新字樣（勾選仍必須是 `[ ]`）；`takes effect from C-2`、`ABF_STATION_GCP_CREDENTIALS`、`預檢不計費` 等其餘斷言不動（`maxvCpus` 那句文件改寫為「takes effect from C-2 as a per-task cpus limit; a total cap belongs to C-3」，保留原關鍵語）。
- `platform/tests/test_station_docs.py:77-82`（TC-077 的 parity 列迴圈）：若新字樣仍不是 `Modelled, needs a real account`，現有「跳過 `googlebatch-platform`」的邏輯已涵蓋，**預期不用改**；executor 先跑，紅了才改，且只改被跳過那一列的判斷。
- 確認**不會**變紅、不准改：`test_station_launch.py`（含 `test_unconfirmed_launch_is_refused`，LAUNCH_ALLOW 指向它）、`test_station_cancel.py`、`test_station_resume.py`、`test_launch_bundle.py`（第 450 行用 awsbatch，仍不支援）、`test_launch_cli.py:306-312`（awsbatch 仍「尚未支援」）、`test_station_envs.py`、`test_station_e2e.py::test_tc031`、`test_scope.py`（新檔需有檔首 `# Nothing existing:`／`# Not …:` 標頭，見下）、`tests/no_second_run_state_test.sh`（不改，只要它仍綠）、`tests/credentials_stay_in_settings_test.sh`。

## 完成標準（done when）
- 自動：上面所有新測試綠；全套綠（含 `tests/platform_test.sh` 與 `tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`）；MCP 工具數仍 12；Slurm 的內容包、畫面、`head.sh` 與 golden 位元級不變。
- 手動（維護者，C-0 帳號與 C-1 的 `available` 都完成後做一次，**會花很小一筆錢**——先確認 GCP 帳單預算與警示已設）：
  1. 平台主機（WSL）有 Java 17+、Nextflow、gcloud；`storage_root` 已設；金鑰檔在 `ABF_STATION_GCP_CREDENTIALS` 指的位置（600）。
  2. 把一個最小的 samplesheet（兩三個很小的檔，已用 `gcloud storage cp` 放進 `workDir` 同一個 bucket）送出：`abf-launch … --ce gcb1`；**送出畫面第一段必須看到「由 Google 向實驗室的 Google Cloud 帳號收費」**；答 y 才開始。
  3. 看到 `已啟動：主控程序編號…`；`ls <storage_root>/_gcb_runs/<run>` 有 `head.pid`、`head.out`；Google Cloud Console 的 Batch 頁出現 job；平台的 run 頁出現進度（`-with-tower` 這條路通）；跑完 `gs://…/runs/<run>/results` 有輸出。
  4. 再送一個，中途用取消指令取消：確認 Batch 頁的 job 被取消／刪除（**驗證 SIGTERM 會讓 Nextflow 取消 Batch 工作**；若沒有取消乾淨，記入 ledger 並回報 developer-agent，不要自行加 `gcloud batch jobs delete`，那是第二條寫入路徑，需要另開任務）。
  5. 在平台資料庫、`ce show`、送出畫面、日誌、`head.sh` 搜不到金鑰任何片段與金鑰檔路徑。
  6. 核對兩個「executor 實跑核對」項：`process.resourceLabels` 在 Batch 上有出現在 job 的標籤；短名稱的 `network`／`subnetwork`（若他有設）被接受。結果寫進 ledger。
- 文件：作法 13 的各份文件更新；`docs/TESTING.md` 的「gcb-launch」小節寫明手動驗收（第 1–6 步）與「驗收者看 `git diff --name-only`、C-1 測試只動計畫列的四處」。

## 環境事實
（行號為 PR #175 分支 `origin/feat/gcb-ce-type-2` 的內容；`git fetch origin` 後以 `git show <ref>:<path>` 讀）
- 送出入口：`platform/abf_launch/build.py` `primary_environment`:109（只選 `compute_envs.SUPPORTED`＝slurm）、`target_problem`:121、`prepare_launch`:131（取 `agents.get_facts`、`inputs_from_environment`、`render_bundle`）、`prepare_cancel`:258（需 `slurm_job_id` 非空）、`prepare_resume`:380／`prepare_relaunch`:412、`launch_screen`:439、`cancel_screen`:458。網頁／MCP 路徑：`platform/abf_platform/actions/__init__.py` `request_launch`:~495（呼叫 `build.prepare_launch`，再 `launch_screen`、`_ask`）、`request_cancel`:~530。
- 平台工作層：`platform/abf_platform/jobs.py` `_target`:71（C-1 在 :86 加了 gcb 分支，目前除 `preflight` 全拒）、:101（`launch_nextflow` 須 `available`）、`CONFIRMED`:41、`enqueue_launch`:570／`enqueue_cancel`:578、`clean_result`:642（`launch_nextflow`／`cancel_run` 取整數 `slurm_job_id`≥1、`run_name`≤64、`run_folder`≤1100、`left_on_site`≤600）、`_apply_handover`:697（`launches.slurm_job_id`、`cancel_requested_at`）。
- 資料表：`platform/abf_platform/store.py` `launches`:~245（`slurm_job_id INTEGER` 可空、無型別 CHECK）、`jobs.kind` CHECK 只列六種、`confirmations.kind` 只 `launch`／`cancel`。
- 代理：`platform/abf_station/handlers.py` `JOB_KINDS`:16、`handle`:34（:48-55 分派 `launch_nextflow`／`cancel_run`；:57 C-1 的 gcb 預檢）；`launch.py` `snapshot_ce`:91、`_check_ce`:125（只收 Slurm；`NO_SCRIPTS`）、`path_cells`:233、`_check_samplesheet`:242、`_params_yaml`:347、`_tower`:294（`reach == "local"` → 直接用代理回報的 `endpoint`）、`_head_script`:360、`render_bundle`:409、`own_facts`:518、`verify_confirmation`:538、`_prechecks`:734、`run_launch`:694、`_submit`:761（`SUBMITTED` 正則抓 Slurm 號碼）、`run_resume`:850；`cancel.py` `run_cancel`:24（`KEYS`:14；Slurm 以 `squeue` 核對名稱／擁有者／工作目錄再 `scancel` 一次，gcb 版照這個順序）；`site.py` `Site.call`:61、`run_fixed`:91（C-1 加；固定 argv、無 shell、逾時丟 `TimeoutError`）；`gcb_preflight.py` `credentials_path`:35、`clean_environment`:44、`_scrub`:66、`_gcloud_env`:83、`_read_key`:90、`run_preflight`:108；`agent.py` `Context`:195（`used_confirmations`）；`rules.py` `clean_environment`:90（只收 `slurm-platform`）；`fetch.py` `_NOT_RECORDS`:~20。
- 憲法掃描：`platform/tests/test_scope.py` TC-071（`abf_platform/` 內不得有 `nextflow run`、`sbatch`、`nohup`、`setsid`、`subprocess` 等）；`tests/no_second_run_state_test.sh` 第一項掃 `platform/` 的送出字樣，`LAUNCH_ALLOW` 至多一筆（現為 `abf_station/launch.py`）；第二項（daemon 字樣）只掃 `scripts/`。→ 所以 `nextflow run` 字樣只能在 `launch.py`、`subprocess` 只能在 `site.py`。
- 新 `.py` 檔前 40 行需有 `# Nothing existing: <≥15 字理由>`（`test_scope.py` TC-070）：`gcb_launch.py`、`test_gcb_launch.py` 都要；理由要寫「搜過 Nextflow `google-batch` executor、Seqera `tw launch`、nf-core `tower launch`，它們都是把工作交給 Seqera 服務，沒有現成可由本機代理在確認後啟動並取消的做法」。
- C-1 已定、本任務沿用：憑證檔位置是代理自己的設定（`ABF_STATION_GCP_CREDENTIALS`，否則 `<部署資料夾>/_personal/gcp-sa.json`）；平台只存憑證**名字**；gcb 環境必須有 agent，該 agent 就是跑在平台主機上的站台代理（C-1 裁決二 F、G、H）；預檢 `CHECK_NAMES` 八項。
- 平台主機現實：首位使用者的平台主機是他自己的桌機，代理跑在 WSL（金鑰檔在 WSL home；`/proc` 可用）。本任務的取消核對依賴 `/proc/<pid>/cwd`，因此**代理主機須是 Linux 或 WSL**；macOS 與原生 Windows 不在本任務範圍（送出前檢查發現沒有 `/proc` → 白話拒絕）。
- Nextflow 設定鍵來源（2026-10-24 讀）：
  - `google.project`（專案 ID）、`google.location`（預設 `us-central1`）、`google.batch.spot`（預設 false）、`google.batch.bootDiskSize`（附單位，如 `50.GB`）、`google.batch.bootDiskImage`、`google.batch.serviceAccountEmail`（預設 Compute Engine 預設帳號；是**任務**執行用，不是 Nextflow 本身）、`google.batch.network`（完整 URL、`projects/{p}/global/networks/{n}` 或 `global/networks/{n}`）、`google.batch.subnetwork`（完整 URL、`projects/{p}/regions/{r}/subnetworks/{s}` 或 `regions/{r}/subnetworks/{s}`）、`google.batch.usePrivateAddress`（預設 false；僅內部 IP，之後 Docker 映像只能來自 Google Container Registry）、`google.batch.maxSpotAttempts`（預設 0）：https://docs.seqera.io/nextflow/reference/config/google（Nextflow 官網 `https://www.nextflow.io/docs/latest/google.html` 會轉址到 `docs.seqera.io/nextflow/google`）。
  - `process.executor = 'google-batch'`、`workDir` 必須是 Cloud Storage 路徑且至少含一層子目錄、啟動身分需 Batch Job Editor＋Service Account User、任務服務帳號需 Batch Agent Reporter＋Logs Writer：https://docs.seqera.io/nextflow/google 。
  - 憑證：Nextflow 讀 Application Default Credentials，`GOOGLE_APPLICATION_CREDENTIALS` 指向服務帳號金鑰檔，用金鑰檔時 `google.project` 預設取檔內專案、若自己也設則須相符：https://docs.seqera.io/nextflow/google-storage （Authentication 一節）。
  - `executor.queueSize`：Google Batch 預設 1000；`executor.pollInterval` 預設 10s：https://docs.seqera.io/nextflow/reference/config/executor 。
  - `process.resourceLabels`：文件寫「附在 task 執行上的 name-value」，**未逐字說 Google Batch 支援**（https://docs.seqera.io/nextflow/reference/process/directives ）。`google.batch.labels` 在 config 參考頁**查不到**，所以不用。
  - **查不到**：SIGTERM／Ctrl-C 時 Nextflow 是否取消 Batch 工作——上述頁面都沒寫。依據只有 replan 原文；所以列為手動驗收第 4 步，且取消回覆一律提醒使用者到 Console 確認。

## 不做
- 不做費用：不估價、不設上限、不加 `cloud_cost.py`／`configs/cloud/rates.json`、不加自動停（C-3）；畫面只有「Google 會計費」的白話，沒有數字。
- 不做本機檔案上傳到 bucket（C-6）；samplesheet 只收 `gs://` 且同 bucket。
- 不做續跑、原樣重跑、`fetch_run_records`、`read_task_log`、`list_site_files` 對 gcb 的支援（仍白話拒絕；之後另開任務，因為它們讀的是專屬資料夾與工作目錄）。
- 不做刪 work（C-7）、不寫 `gcloud batch jobs delete`／`cancel` 之類的第二條寫入路徑。
- 不在平台裡新增 worker、執行緒、常駐迴圈或 `local_runner.py`（憲法原則 2）。
- 不改 Slurm 任何一個位元組的行為；不改 C-1 的預檢清單與驗證規則；不碰 AWS／Azure／K8s 類型。
- 不新增 MCP 工具、網頁路由或畫面（畫面只改 `launch_screen`／`cancel_screen` 的文字）；不改 `hello` 回傳與 `clean_facts`。
- 不做多個 bucket 的讀取白名單、不做 Workload Identity、不做 Wave／Fusion／GPU／instance template。

## 裁決（2026-10-24，developer-agent 起草；與上文衝突時以本段為準）
1. **代理端新增 `gcb_launch.py`，內容包樣板留在 `launch.py`；不抽 `abf_launch/bundle_check.py`，不拆 `_slurm_head`／`_local_head`。** 理由：憲法的 `LAUNCH_ALLOW` 只允許一個送出檔案（`launch.py`），把 `nextflow run` 字樣留在那裡就不用改憲法掃描；gcb 的內容包形狀不同（沒有帳號、佇列），硬共用一個函式會讓 Slurm 路徑多出條件分支而冒險動到 golden。代價：少量重複（run 名稱、pipeline、revision 檢查直接重用 `launch.py` 既有函式，不重寫）。**預設採此做法。**
2. **沿用 `launches.slurm_job_id` 欄位存 pid，結果鍵名不改，不做 migration。** 理由：改欄位名或加欄位要動 `launches` 表、`clean_result`、`_apply_handover`、`prepare_cancel`、`prepare_resume`、cli 三處與全部相關測試，風險遠大於收益；pid 的回收風險由取消時的「名稱＋擁有者＋工作目錄」三重核對擋住。**另一選項**：加 `launches.head_ref TEXT`，需要 migration（仿 `_add_forgotten_columns`）與改 `build.py` 五處判斷。**預設：沿用；若維護者覺得欄位名騙人，另開 `launches-job-ref` 小任務做改名。**
3. **用 `subprocess.Popen(argv 列表, start_new_session=True)` 啟動，不用 `nohup setsid … &`。** 理由：①不經 shell、不靠字串引號；②`tests/no_second_run_state_test.sh` 的常駐程式掃描對 `nohup`／`setsid` 字樣很敏感（雖然只掃 `scripts/`，不想讓 `platform/` 長出那些字）；③pid 直接拿得到，不用 `echo $!`。主控程序是「那次分析本身」不是監看常駐程式，這點寫進 `site.py` 檔首說明。**預設採此做法。**
4. **輸入資料要 `gs://` 且必須在該環境 `workDir` 的 bucket**（維護者交辦「建議」）。理由：金鑰與預檢只驗證過那一個 bucket；跨 bucket 讀取的權限無從在建包時檢查；本機上傳是 C-6。**另一選項**：C-1 的環境加選填鍵 `readBuckets`（清單），多開幾個可讀 bucket，需改 `compute_envs.py` 與 C-1 的鍵清單測試。**預設：只允許同 bucket；真有需要（例如公開資料集）再加 `readBuckets`。**
5. **gcb 不被自動選為預設環境**（`primary_environment` 不改）。理由：按 y 才花錢是一回事，「只有一個可用環境就悄悄選它」是另一回事；明講環境名字等於多一道意圖確認。**預設採此做法；列出供他知悉。**
6. **`maxvCpus` 落成 `process.resourceLimits = [cpus: N]`（單一 task 上限），並白話說明它不是總量上限。** 理由：Nextflow 沒有同名的總量鍵；`executor.queueSize` 限的是同時 task 數、不是 vCPU 數，拿來冒充總量上限會給人錯誤的安全感。總量上限屬 C-3（cap／watchdog）。**預設採此做法；C-1 文件的「takes effect from C-2」那句照此改寫，不說謊。**
7. **Java／Nextflow 的檢查放在送出前，不加進 C-1 的預檢清單。** 理由：不動 C-1 的 `CHECK_NAMES` 與其十幾個測試；代價：環境顯示 `available` 但平台主機沒裝 Nextflow 時，要到按 y 之後才發現（代理在寫任何檔案**之前**就拒絕，沒有殘留）。**另一選項**：把 `java`、`nextflow` 兩項加進預檢（改 C-1 測試的清單長度與順序）。**預設：送出前檢查。**
8. **取消只送一次 SIGTERM。** 理由：與 Slurm 的「一次 scancel、不重試」一致；強制 `kill -9` 會讓 Nextflow 來不及取消 Batch 工作（反而留下計費中的虛擬機）。若手動驗收發現 SIGTERM 取消不乾淨，**停手回報**，不自行加 `gcloud` 刪除。**預設採此做法。**
9. **進度回報用代理回報的 `endpoint`（`reach` 為 `local` 時就是它連的平台網址，通常是 loopback），不要求公開 https 網址。** 理由：只有主控程序（跑在平台主機）送 tower 事件，Batch 的虛擬機不需要連回平台，所以用 loopback 就夠，也就不用把平台對外公開；任務原文寫「指向平台公開網址」的情況（`way_back: direct` 且 `reach` 非本機）不適用於 gcb，若代理設定了不同的 `reach` 值 → 白話拒絕。**預設採此做法。**
10. **失敗時資料夾保留不刪**（`left_on_site` 說明位置），與 Slurm 一致。
11. **新檔標頭**：`gcb_launch.py`、`test_gcb_launch.py` 前 40 行要有 `# Nothing existing: …`（見「環境事實」）。
12. **派工順序**：C-1（PR #175）合併 → 本任務；同車道 `compute_envs.py`、`test_gcb_ce.py` 不可平行；`abf_station/*` 與 L1 任務不可平行。

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
