---
id: gcb-ce-type
title: Google Batch 計算環境類型：能建立、驗證、存放（憑證只放平台主機檔案，預檢不花錢）
tier: B
kinds: backend
lane: L2-platform-ce
base: v3
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 3 的 C-1（拷問 10-21 第二輪第 13 點、第 10 點）
---

# gcb-ce-type

> 本檔由 developer-agent 寫（2026-10-24）。**只處理 C-1 第一片**：`googlebatch-platform` 這個類型可以建立、驗證、儲存、預檢。**真的在 Google Batch 上跑 Nextflow 是下一個任務 C-2（`gcb-launch-platform`），不在本任務。** B 級（使用者看得到的新能力）→ verifier 通過＋CI 綠由 developer-agent 自合。
> 與 M1-05 的 `compute_envs.py` 車道相同（L2），須等 `estimate-su-mcp` 合併後再派（兩件都改 `compute_envs.py`）。

## 目標
讓管理者能用 `abf-platform ce create --platform googlebatch-platform …` 登記一個 Google Cloud Batch 環境，平台檢查設定合不合規、檢查平台主機上的服務帳號憑證檔讀不讀得到、（可以時）檢查 Batch API 與 bucket 連得上，並把結果記成 `available` 或 `invalid`。

為什麼這樣切：①雲端用戶不裝站台代理（拷問二），所以這個類型的預檢不能走「排工作給代理」那條路，要由平台主機自己做；②憑證 JSON 只放平台主機檔案，資料庫只存名字（`credential_findings` 已擋鍵值）；③預檢全部不計費（讀檔、列 API、列 bucket 都不建任何 Batch job），GCP 帳號預算 NT$1,000 在這一片碰不到；④launch 留給 C-2，所以 `available` 的 gcb 環境在 C-2 之前仍**不能被選去送出**（見作法 9）。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`：
- 「4. 四種計算環境都建：nano4 → Google Batch（開發上限 NT$1,000/月）→ AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（第 40 行）→ 欄位與流程照 Seqera 的 Google Batch CE，憑證與環境分開、環境只記憑證名字。
- 「站台代理：**國網用戶裝在個人電腦**（持 2FA）；**雲端用戶不裝代理**——平台主機自己跑 Nextflow、雲端憑證放平台主機檔案（不進資料庫）→ C-1／C-2 改為平台內建的 `local` 執行器，不經站台。」（10-21 拷問二，第 52 行）→ gcb 環境沒有 agent；預檢由平台主機做；資料庫裡找不到金鑰內容。
- 「Google Batch 雲端：等你開好 GCP 帳號（預算 NT$1,000）；費用顯示美元、每人每月上限、超過自動停。」（第 16 行）→ 本片不碰費用，但設定結構不可寫死幣別換算（費用屬 C-3）。
- 「雲端費用**照 10-18 裁示**：顯示雲端自己的幣別（美元）、不換算、每人每月上限由管理者開帳號時設，NT$1,000 只是 GCP 帳單預算」（第 46 行）→ 本片不加任何台幣欄位。
- 「**雲端第一個真實使用者＝他自己的自費帳號**」（10-21 拷問，第 50 行）→ 預檢必須能在他自己的帳號上不花錢跑完。
- 「C-1 `gcb-ce-type`：`compute_envs.py` `SUPPORTED` 改集合 …… 憑證 JSON 只放站台主機 `<deployment>/_personal/gcp-sa.json`（600）…… 平台只存 `credentialName`。`test_tc030` unsupported 數 13→12。」（第 166 行）→ 見裁決 1、2、3 對原文的三處調整。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/compute_envs.py`（新類型集合、`_check_gcb`、`create` 的初始狀態、`snapshot` 不動）
- `platform/abf_platform/gcb_preflight.py`（新；平台主機端預檢，函式皆可注入）
- `platform/abf_platform/store.py`（只加 `gcp_credentials_file()`，仿 `uploads_root`，約 store.py:293）
- `platform/abf_platform/cli.py`（`_queue_first_preflight`:282、`cmd_ce_create`:307、`cmd_ce_update`:323、`cmd_ce_preflight`:366、`_config_from_args`:219 加旗標）
- `platform/abf_platform/jobs.py`（只在 `_target`:71 加一個分支：gcb 環境收到需要代理的工作 → 白話拒絕；不新增工作種類）
- `platform/abf_launch/build.py`（只確認 `primary_environment`:109 仍只選 slurm；若需要，用明確的 `compute_envs.AGENT_TYPES` 取代 `== SUPPORTED`）
- `platform/tests/test_gcb_ce.py`（新）
- `platform/tests/test_station_envs.py`（只改 `UNSUPPORTED` 與兩個測試的斷言，見「必須更新的既有斷言」）
- `platform/tests/test_station_docs.py`（:77-82 的 parity 列斷言，見同節）
- `docs/PLATFORM.md`（第 8 節型別表、CE 鍵表加 gcb 小節、預檢小節加 gcb 檢查）
- `docs/SEQERA_PARITY.md`（F 節 Google Cloud Batch 那列、F 節開頭一段）
- `specs/gcb-ce-type/ledger.md`（新，executor 進度帳本）

## 作法
1. **型別集合（compute_envs.py:33）**：`SUPPORTED = "slurm-platform"` **保留**（它的意思是「走站台代理的類型」，cli.py:284/311/331、build.py:112 都靠這個字串）。新增：
   - `PLATFORM_HOST_TYPES = ("googlebatch-platform",)`：由平台主機自己檢查、自己（C-2 起）執行的類型。
   - `CHECKABLE = (SUPPORTED,) + PLATFORM_HOST_TYPES`。
   - `create` 的初始狀態：`platform in CHECKABLE` → `creating`＋「等待第一次預檢」；其餘照舊 `unsupported`。`set_primary`、`apply_preflight`、`jobs._target` 對 `unsupported` 的既有行為不變。
2. **gcb 設定鍵（`_GCB_CONFIG`＝`_COMMON_CONFIG` ＋下列）**，欄位取自 Nextflow `google.*` 與 Seqera 的 Google Cloud Batch 表單（只取欄位、不抄文字）：
   | 鍵 | 型別／規則 | 對應 |
   |---|---|---|
   | `project` | 必填；GCP 專案 **ID**，小寫字母開頭，6–30 字，`[a-z][a-z0-9-]*[a-z0-9]` | `google.project` |
   | `location` | 必填；區域，如 `europe-west2`，`[a-z]+-[a-z]+[0-9]+` | `google.location` |
   | `workDir` | 必填；`gs://<bucket>[/<prefix>]`；bucket 名 3–63 字小寫英數與 `-_.`；前綴不含 `..`、控制字元；去掉結尾斜線 | `workDir` |
   | `spot` | 選填；布林，預設 false | `google.batch.spot` |
   | `bootDiskSize` | 選填；`<整數>GB`（如 `50 GB` 或 `50GB`，1–2000） | `google.batch.bootDiskSize` |
   | `bootDiskImage` | 選填；映像名稱字元集 `[A-Za-z0-9_./:-]`，≤200 | `google.batch.bootDiskImage` |
   | `serviceAccountEmail` | 選填；`name@project.iam.gserviceaccount.com` 形狀（只是**信箱**，不是金鑰） | `google.batch.serviceAccountEmail` |
   | `network`、`subnetwork` | 選填；VPC／子網路名，`[a-z]([-a-z0-9]*[a-z0-9])?` 或 `projects/…/global/networks/…` 形式 | `google.batch.network`／`subnetwork` |
   | `usePrivateAddress` | 選填；布林 | `google.batch.usePrivateAddress` |
   | `labels` | 選填；物件，鍵值各 ≤63 字，鍵 `[a-z][a-z0-9_-]*`，值 `[a-z0-9_-]*`，最多 64 組 | 資源標籤（GCP label 規則） |
   | `maxvCpus` | 選填；整數 1–10000；平台側上限，C-2 決定怎麼落到 Nextflow（見裁決 6） | 平台自訂 |
   | `nextflowConfig`、`environment`、`preRunScript`、`postRunScript` | 沿用共用檢查（`_text`、`_check_environment`） | 共用 |
   - 未知鍵 → 與 Slurm 同寫法：`unknown setting for a Google Batch environment: X (known: …)`。
   - 全部錯誤一次列出（仿 `_check_site_keys`:248 的寫法），不回顯被拒的值全文（值最多顯示 60 字）。
   - `agent` 給了 → 拒絕：`a Google Batch environment needs no agent: the platform host runs it (雲端環境不需要代理，由平台主機執行)`。`hostName`／`userName`／`port`／`launchDir`／`readRoots` 等 Slurm 鍵不在 `_GCB_CONFIG`，自然被未知鍵規則擋下。
3. **憑證只放名字**：用既有頂層欄位 `credentialsId`（`_CRED_NAME` 規則，compute_envs.py:55,330）當憑證**名字**，不新增 `credentialName` 設定鍵（裁決 2）。`credential_findings`（:118）原樣套用；`serviceAccountEmail` 是信箱，不得被 `_VALUE_PATTERNS` 誤傷，且 `<PEM 私鑰開頭標頭>` 貼進任何欄位仍被擋、訊息只講欄位路徑。
4. **憑證檔位置**：`store.gcp_credentials_file(platform_path=None, env=None)`＝環境變數 `ABF_PLATFORM_GCP_CREDENTIALS`，否則 `<platform.db 同資料夾>/_personal/gcp-sa.json`（寫法照 `uploads_root`，store.py:293）。**檔案內容永遠不進 DB、不進日誌、不進任何回傳**；程式只在記憶體裡解析 JSON 取 `type`、`client_email`、`project_id` 三欄來比對，用完即丟。
5. **預檢（`gcb_preflight.py`）**——全部不計費、不建任何 Batch job、不寫 bucket。函式簽名（可注入）：
   `run_preflight(ce, *, cred_path, now=time.time, runner=_run, which=shutil.which, stat=os.stat) -> {"ok": bool, "checks": [{"name","status","detail"}]}`；
   `runner(argv, env, timeout)` 回 `(returncode, stdout_tail)`，**測試一律傳假的**；預設實作用 `subprocess.run`（`shell=False`、固定 argv、`timeout=20`、輸出截斷 300 字）。不 import 任何 `google.*` / `boto3` 套件（`test_tc085` 掃描原始碼，見「必須更新的既有斷言」）。
   | 檢查名 | 做什麼 | 通過／失敗 |
   |---|---|---|
   | `credential_name` | `credentialsId` 有設 | 沒設 → fail，詳述「給這個環境一個憑證名字」 |
   | `credential_file` | 檔案存在、可讀、是一般檔案；POSIX 上 mode 不得讓 group／other 可讀寫（`mode & 0o077 == 0`）；Windows 略過 mode 並在 detail 說「Windows 不檢查權限位」 | 缺檔 → fail，detail 寫出**應放的路徑**（路徑本身不是祕密）與一句怎麼放 |
   | `credential_shape` | 解析 JSON，`type == "service_account"`，有 `client_email`、`private_key` 鍵（**只檢查鍵存在，不看值**） | 失敗訊息只講缺哪個鍵，不印任何值 |
   | `credential_project` | 檔內 `project_id` 與環境 `project` 相同 | 不同 → fail，兩個專案 ID 都顯示（專案 ID 不是祕密） |
   | `service_account` | 若環境設了 `serviceAccountEmail`：與檔內 `client_email` 無須相同（可以是另一個執行帳號），只檢查形狀；沒設 → pass，detail「用 Compute Engine 預設帳號」 | |
   | `gcloud` | `which("gcloud")`；沒有 → **unchecked**（不是 fail） | |
   | `batch_api` | 有 gcloud 才做：`runner(["gcloud","batch","jobs","list","--project",P,"--location",L,"--limit","1","--format","value(name)"], env={…CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE=<cred_path>, CLOUDSDK_CORE_DISABLE_PROMPTS=1})`；列表是唯讀、不計費 | rc 0 → pass；rc≠0 → fail，detail 只放 gcloud 輸出的前 300 字並先經 `credential_findings` 風格的掃描去掉像金鑰的片段 |
   | `bucket` | 有 gcloud 才做：`runner(["gcloud","storage","ls","gs://<bucket>/","--project",P])`（只列頂層、不寫入） | 同上 |
   - 狀態規則沿用平台：任何一項不是 pass 就不是 `available`（`jobs.clean_result` 的「全 pass 才 ok」, jobs.py:654）；`unchecked` 不算 pass。→ **機器上沒有 gcloud 時環境停在 `invalid`，訊息明說缺 gcloud**（裁決 4：是否放行，developer-agent 已定（2026-10-24）：採預設）。
   - 結果以 `compute_envs.apply_preflight(con, name, ok, checks, now)`（compute_envs.py:604）寫入，與代理走同一條記錄路徑，`verdict_message` 不改。
6. **CLI 接線**：
   - `ce create`／`ce update`：gcb 類型建好後**同步**跑一次平台主機預檢（取代 `_queue_first_preflight` 的「排工作給代理」），輸出每項 `name: status - detail`。`cmd_ce_create` 的 `_default_agent`（cli.py:311）只對 `SUPPORTED` 生效，不變。
   - `ce preflight <name>`：gcb 類型不排工作，直接同步跑 `run_preflight`；slurm 路徑原樣不動。
   - 新旗標（`_config_from_args`，cli.py:219）只加 `--project`、`--location`、`--spot`／`--no-spot`、`--service-account-email`、`--boot-disk-size`；其餘鍵用既有 `--config-json`。
7. **`jobs._target`（jobs.py:71）**：gcb 環境收到 `list_site_files`／`launch_nextflow`／`cancel_run`／`fetch_run_records`／`read_task_log` → `JobRefused`：`%s is a Google Batch environment: it is checked on the platform host and launching on it is not built yet (尚未支援送出；下一步 C-2)`。放在 `no agent` 檢查**之前**，所以訊息不會誤導成「請設定 agent」。
8. **擁有者**：gcb 環境照現行 `owner_user_id` 規則，別人的環境對呼叫者是 not found；預檢指令是終端機管理者指令，不新增網頁路由或 MCP 工具（工具數仍 12；parity OWED 不動）。
9. **選擇與送出不放行**：`build.primary_environment`（build.py:109-118）與 `ce primary` 的行為：gcb 環境可以被設成 primary（它是 `available` 時），但 `launch` 對 gcb 環境在 `target_problem`（build.py:121）處白話拒絕（同作法 7 的句子）。`primary_environment` 的「自動選」仍只選 slurm，避免自動把人送進還沒做的路徑。
10. **文件**：`docs/PLATFORM.md` 第 8 節型別表把 `googlebatch-platform` 的 Supported 欄改成 `checked on the platform host (launch: not yet)`，並說「Only Slurm can run; Google Cloud Batch can be created and checked」；新增「Google Cloud Batch」小節：鍵表（作法 2）、憑證檔位置（作法 4）、預檢表（作法 5）、「不計費」說明、`ABF_PLATFORM_GCP_CREDENTIALS`。`docs/SEQERA_PARITY.md` F 節 Google Cloud Batch 列改成 `Have (create + check); launch in C-2`，勾選維持 `[ ]` 直到 C-2 跑通（該節開頭「a type turns supported only after a run on a real account」不變）。範例不得出現真實專案 ID／信箱（用 `lab-project-1`、`runner@lab-project-1.iam.gserviceaccount.com`）。
11. **不需要 migration**：只是同一張 `compute_envs` 表的新 `platform` 值與新的 `config_json` 鍵；`status` 沿用既有五種值；舊紀錄不受影響。

## 失敗先行測試（`platform/tests/test_gcb_ce.py`，現在都會紅；全部用假 `runner`、假 `which`，不碰網路）
- `test_a_valid_google_batch_environment_is_created_as_creating`：合法 config（作法 2 全欄）→ `create` 成功、`status == "creating"`、`config` 原樣回來（`workDir` 去掉結尾斜線）。
- `test_project_location_and_workdir_are_required`：各缺一個 → 錯誤訊息點名該鍵。
- `test_workdir_must_be_a_gs_url`：`/data/work`、`s3://b/x`、`gs://`、`gs://UPPER/x`、`gs://b/../x` 各被拒；`gs://lab-bucket/work/` 通過。
- `test_unknown_and_slurm_keys_are_refused`：`headQueue`、`hostName`、`foo` → 拒絕並列出已知鍵。
- `test_all_errors_are_listed_at_once`：同時錯 `project`、`spot`、`bootDiskSize` → 一則訊息含三個鍵名。
- `test_agent_is_refused_for_a_cloud_environment`：給 `agent` → 拒絕，訊息含「不需要代理」。
- `test_a_private_key_pasted_anywhere_is_refused_and_not_repeated`：把 `<PEM 私鑰開頭標頭>…` 放進 `description`、`nextflowConfig`、`environment` 值、`labels` 值 → 都被拒；訊息只含欄位路徑，不含金鑰文字；DB 檔位元組比對沒有該文字。
- `test_a_key_named_field_is_refused`：config 裡有 `privateKey`、`serviceAccountKey` → 被 `credential_findings` 擋。
- `test_service_account_email_is_a_plain_email_not_a_secret`：`runner@lab-project-1.iam.gserviceaccount.com` 被接受；`not-an-email` 被拒。
- `test_credentials_id_is_a_name_only`：`credentialsId` 含空白或 `=`/長字串金鑰形 → 被拒（沿用 :330 規則）。
- `test_credential_file_location_follows_the_setting`：`ABF_PLATFORM_GCP_CREDENTIALS` 設了就用它；沒設是 platform.db 旁的 `_personal/gcp-sa.json`。
- `test_preflight_reports_a_missing_credential_file_with_where_to_put_it`：沒有檔 → `credential_file` fail，detail 含預期路徑；環境變成 `invalid`；其他不需檔的檢查（`credential_name`）仍有結果。
- `test_preflight_refuses_a_world_readable_credential_file`（`@pytest.mark.skipif(win32)`）：檔 mode 0644 → fail，detail 提到權限；0600 → pass。
- `test_preflight_checks_the_shape_of_the_key_file_without_printing_it`：缺 `client_email` → fail 且 detail 只含鍵名；整份 `checks` JSON 與環境 `message` 不含檔裡任何值（用唯一標記字串斷言）。
- `test_preflight_project_in_file_must_match_the_environment`：檔內 `project_id` 不同 → fail，兩個 ID 都在 detail。
- `test_preflight_without_gcloud_leaves_api_checks_unchecked`：`which` 回 None → `batch_api`、`bucket` 為 `unchecked`、環境 `invalid`、message 說缺 gcloud；`runner` 被呼叫 0 次。
- `test_preflight_all_pass_makes_the_environment_available`：假 runner 回 0 → 所有檢查 pass → `status == "available"`、`checked_ok == 1`。
- `test_preflight_batch_api_failure_is_reported_and_trimmed`：假 runner 回 rc 1 與 2000 字輸出（內含一段像金鑰的字串）→ `batch_api` fail、detail ≤300 字、不含該金鑰片段。
- `test_preflight_only_runs_read_only_commands`：記錄所有 `runner` argv，斷言每一條開頭是 `gcloud batch jobs list` 或 `gcloud storage ls`，且沒有 `create`、`submit`、`delete`、`cp`、`rm`、`mb`、`enable` 這些字（**不花錢保證**）。
- `test_preflight_passes_the_credential_through_the_environment_not_argv`：金鑰檔路徑只在 `env`（`CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE`），不在 argv；env 不含 `GOOGLE_APPLICATION_CREDENTIALS` 以外的平台祕密（不繼承 `ABF_*` token）。
- `test_preflight_is_synchronous_and_queues_no_job`：`ce preflight` gcb 後 `jobs` 表列數不變。
- `test_cli_create_runs_the_first_preflight_for_google_batch`：`ce create --platform googlebatch-platform …`（注入假 runner）→ 輸出每項檢查、環境狀態已不是 `creating`。
- `test_slurm_still_queues_a_job_for_its_agent`：slurm 建立後仍排 `preflight` 工作（回歸，行為不變）。
- `test_agent_jobs_on_a_google_batch_environment_are_refused_in_plain_words`：對 gcb 環境 `enqueue_preflight`／`launch_nextflow` 等 → `JobRefused`，訊息含「尚未支援送出」與 `C-2`，不含「set an agent」。
- `test_launch_on_a_google_batch_environment_is_refused_not_misrouted`：`build.target_problem` 對 `available` 的 gcb 環境回非 None 的白話句。
- `test_primary_environment_never_auto_picks_google_batch`：只有一個 `available` 的 gcb 環境 → `primary_environment` 回 None。
- `test_another_users_google_batch_environment_is_not_found`：B 用 `owner=` 取 A 的 gcb 環境 → None（與 slurm 相同）。
- `test_tool_list_unchanged_and_no_new_web_route`：MCP 工具名集合仍 12 個；沒有新增路由（讀 `test_estimate_su.py::test_tc029` 同一組）。
- `test_no_cloud_library_is_imported`：`gcb_preflight.py` 原始碼沒有 `import google`、`boto3`、`azure`、`requests`（呼應 TC-085）。
- `test_docs_list_every_gcb_key_and_check`：`docs/PLATFORM.md` 含作法 2 每個鍵名與作法 5 每個檢查名，並含 `ABF_PLATFORM_GCP_CREDENTIALS`。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫明「以前／以後／理由」）
釘住「CE 類型清單」或 schema 的既有測試與斷言：
- `platform/tests/test_station_envs.py:19-33` `UNSUPPORTED` 字典：**移除 `googlebatch-platform` 那一筆（:21）**，剩 12 種。它同時被 :146（TC-030）、:289（TC-096，只用 `awsbatch-platform`，不受影響）、:473（TC-085）與 `test_station_e2e.py:284`（TC-031，`from test_station_envs import UNSUPPORTED`）使用；移除後這三處自動只迴圈 12 種，**`test_station_e2e.py` 不必改**。
- `test_station_envs.py:145-146` `test_tc030_the_thirteen_modelled_types_are_stored_as_not_supported`：函式名與註解的「thirteen」改「twelve」；斷言本身（逐型別 `status == "unsupported"`）不動。
- `test_station_envs.py:163-164` TC-032：`len(compute_envs.KINDS) == 14` 不變；`sorted(set(UNSUPPORTED) | {"slurm-platform"}) == sorted(KINDS)` 改成 `set(UNSUPPORTED) | {"slurm-platform", "googlebatch-platform"}`。
- `test_station_envs.py:465-485` TC-085：迴圈自動縮成 12 種，斷言不動。**注意它同時禁止 `pyproject.toml` 含 `google-cloud` 與原始碼 import `google.cloud`**——本任務依賴 `gcloud` 命令列而非套件，所以不會撞；若 executor 想加 Python 套件，視為違規，回報 BLOCKED。
- `platform/tests/test_station_docs.py:77-82` TC-077：「每個非 slurm 型別的 parity 列都寫 `Modelled, needs a real account`」改成跳過 `googlebatch-platform`（它的列改為 `Have (create + check); launch in C-2`），並把 :82 的 `== 13` 改成 `== 12`；`## F. Compute environments (13 items)` 標題（:71）不動。
- `test_station_docs.py:39-41`：`for pid in compute_envs.KINDS: assert "\`%s\`" % pid in doc` 與 `len(KINDS) == 14` 不變（PLATFORM.md 仍列出全部 14 個識別字）。
- 確認**不會**變紅、不准改：`test_station_e2e.py::test_tc031`（讀 `UNSUPPORTED`，自動縮小）、`test_tc096`（用 awsbatch）、`test_estimate_su.py`（工具數）、`test_pat.py:383/751`、`test_oauth_mcp.py:44`、`test_web_parity.py`、`platform/tests/test_scope.py::test_tc070`（新檔需有檔首標頭，見裁決補充）。

## 完成標準（done when）
- 自動：上面所有新測試綠；全套綠（含 `tests/platform_test.sh` 的 REST 分片，新測試檔會自動被收入）；MCP 工具數仍 12。
- 手動（維護者，C-0 帳號開好後做一次，**不計費**）：把服務帳號 JSON 放到 `<platform.db 資料夾>/_personal/gcp-sa.json`（600），`abf-platform ce create --name gcb1 --platform googlebatch-platform --project <他的專案ID> --location <區域> --config-json '{"workDir":"gs://<bucket>/work"}' --credentials gcp-lab`，看到每項檢查，全 pass 時 `ce show gcb1` 顯示 `available`；`ce show` 的輸出與 `platform.db` 裡搜不到金鑰任何片段。
- 文件：`docs/PLATFORM.md`、`docs/SEQERA_PARITY.md` 依作法 10 更新。

## 環境事實
- `compute_envs.SUPPORTED` 目前是**字串** `"slurm-platform"`（compute_envs.py:33），被 `==` 比較於 `cli.py:284/311/331`、`build.py:112`、`compute_envs.py:350,465`；改成集合會讓 `x == SUPPORTED` 悄悄變成永遠 False（這是不照原計畫改成集合的原因，裁決 1）。
- `KINDS` 有 14 個識別字，`googlebatch-platform` 在 compute_envs.py:27。
- 現行非 Slurm 類型只走 `_check_other`（compute_envs.py:300）、狀態 `unsupported`；`jobs._target` 對 `unsupported` 立刻拒絕（jobs.py:86-88）；`create` 在 compute_envs.py:465-467 決定初始狀態。
- 預檢結果的記錄路徑：`jobs.clean_result`（jobs.py:647-655，全 pass 才 ok、檢查最多 20 項、detail ≤300 字）→ `compute_envs.apply_preflight`（compute_envs.py:604-610，略過 `disabled`／`unsupported`）。平台主機預檢要複用 `apply_preflight`，用 `jobs.transaction`（jobs.py:114）包。
- 平台的資料夾設定模式：`store.default_platform_path`（store.py:285）、`uploads_root`（store.py:293，環境變數優先、否則 platform.db 旁）。目前**沒有**通用的「部署 settings 檔」；`agents.hello` 的 facts（common.py:184 `FACT_TEXT`）是代理自報，不適用於無代理的雲端環境。
- 憑證防線：`common.is_secret_name`（common.py:24，正則 `token|password|secret|key`）＋`compute_envs._VALUE_PATTERNS`（:102，含 `<PEM 私鑰標頭樣式>`）。
- 測試套件規則：新 `.py`（含測試）前 40 行需有 `# Nothing existing: <理由，≥15 字>`（`platform/tests/test_scope.py:75-80`）；`tests/platform_test.sh:55-60` 的分片清單不含新檔時自動歸入 REST，不需改；範例路徑不得出現 `/work/<真實帳號>/`（`tests/no_hardcoded_paths.sh`）。
- 研究依據：`specs/007-station-agent/research.md:38,71,113`（Google Batch 的欄位與 `google-batch` executor）。Nextflow `google.*`：`project`、`location`、`batch.spot`、`batch.bootDiskSize`、`batch.bootDiskImage`、`batch.serviceAccountEmail`、`batch.maxSpotAttempts`、`batch.cpuPlatform`（Nextflow 文件，docs.seqera.io/nextflow/google，2026-10-24 讀）；`network`／`subnetwork`／`usePrivateAddress`／`labels` 該頁沒寫，欄位名取自 Seqera 表單（Use Private Address、VPC、Subnet、Resource labels，docs.seqera.io 的 Google Cloud Batch 頁），實際 Nextflow 鍵名由 executor 在 `google` 設定範圍參考頁核對後再寫入 C-2。
- Google 端需要的 API 與角色（Nextflow 文件）：Cloud Batch API 啟用；啟動身分要 Batch Job Editor＋Service Account User；作業服務帳號要 Batch Agent Reporter＋Logs Writer；兩者都要 bucket 存取。→ C-0 的角色清單比這個多給 Storage Object Admin，沒衝突；預檢不檢查角色（無帳號無法離線檢查），由 `batch_api`／`bucket` 兩項的實際結果反映。

## 不做
- **不在 Google Batch 上送出或取消任何東西**（C-2 `gcb-launch-platform`：`local_runner.py`、`_local_head`、`head.pid`、`-with-tower` loopback 全屬 C-2）。
- 不做費用：不加 USD、cap、`cloud_cost.py`、`configs/cloud/rates.json`（C-3）；不做 bucket 上傳（C-6）、不做刪 work（C-7）。
- 不新增 MCP 工具、網頁路由或畫面（設定頁 012a 之後再接）；不改 `hello` 回傳。
- 不碰 AWS／Azure／K8s 類型（C-4、C-5），它們維持 `unsupported`。
- 不用 Python Google 套件（`google-cloud-*`、`google-auth`）；不寫建立 bucket、啟用 API、建服務帳號的程式（那是 C-0，他手動做）。
- 不做 Workload Identity Federation（只做服務帳號金鑰檔；見裁決 7）。
- 不做 Wave／Fusion／instance template／GPU 欄位（Seqera 表單有，本片不收；之後有需要再加，未知鍵目前會被拒）。

## 裁決（2026-10-24，developer-agent 起草；與上文衝突時以本段為準）
1. **不把 `SUPPORTED` 改成集合**（原計畫第 166 行這樣寫）。理由：它是字串，既有 5 處用 `==` 比較，改成集合會讓那些比較悄悄失效；改成新增 `PLATFORM_HOST_TYPES`／`CHECKABLE`，語意清楚（「走代理」vs「平台主機自己做」）。**預設採此做法；不改變方向，不需維護者確認。**
2. **憑證名字用既有頂層 `credentialsId`，不新增 config 鍵 `credentialName`**（原計畫第 166 行列了 `credentialName`）。理由：Seqera 的模型就是「環境 → 憑證」一個欄位，現有驗證（`_CRED_NAME`）與 `view` 都已有；多一個鍵會出現兩處說同一件事。**預設採此做法。**
3. **`serviceAccount` 改名 `serviceAccountEmail`**，與 Nextflow `google.batch.serviceAccountEmail` 及 Seqera「Service Account email」一致，也讓人一看就知道這是信箱不是金鑰。**預設採此做法。**
4. **機器上沒有 `gcloud` 時：環境停在 `invalid`（不是 `available`）**。理由：「預檢通過」的意思是連得上 Batch API 與 bucket；沒檢查到就不該說通過（憲法 IV.9「不要猜」）。代價：平台主機必須裝 gcloud（`docs/INSTALL.md`／`OPERATIONS.md` 的雲端小節在 C-2 補）。另一選項：沒 gcloud 時只做檔案檢查並標 `available`。**預設：invalid。developer-agent 已定（2026-10-24）：採預設**（因為這會影響他的桌機要不要裝 gcloud）。
5. **憑證檔位置用環境變數 `ABF_PLATFORM_GCP_CREDENTIALS`，否則 `<platform.db 資料夾>/_personal/gcp-sa.json`**；**不新增 settings 檔或資料庫 settings 表**（原計畫第 166 行說「站台 settings `gcp_credentials_file`」，但現在平台沒有通用 settings 機制，為單一鍵蓋一個機制不值得；與 `uploads_root` 同模式）。`hello` 回「有／無」那一句取消（雲端環境沒有代理，不會 hello）；「有／無」改由 `credential_file` 預檢項顯示。**預設採此做法。**
6. **`maxvCpus` 先只存、不驗證它與 Nextflow 的對應**；C-2 決定落到 `executor.queueSize` 還是 `process.resourceLimits`。Seqera 與 Nextflow 的 google 設定範圍都沒有同名鍵。**預設：存，附註文件寫「C-2 起生效」。**
7. **只支援服務帳號金鑰檔，不做 Workload Identity Federation**。理由：雲端第一個用戶是他自己的自費帳號、平台主機是自己的桌機，WIF 沒有好處；Seqera 兩者都支援，之後加不破壞資料結構（只是多一種 credential 型別）。**預設採此做法。**
8. **預檢 `service_account` 不要求信箱與金鑰檔的 `client_email` 相同**（可以是「用金鑰檔身分，建立 job 時以另一個服務帳號執行」，這是 Batch 的正常用法，Nextflow 文件的 Service Account User 角色就是為此）。**預設採此做法。**
9. **gcb 環境在 C-2 之前即使 `available` 也不能送出**（作法 7、9）。若維護者希望 C-1 合併後「看起來就能用」，需連同 C-2 一起合併上線；兩件之間不應有使用者可見的半成品入口。**不改方向；列出供他知悉。**

## 裁決補充（2026-10-24）：新檔的檔首標頭與派工順序
- 新的 `.py` 檔（`gcb_preflight.py`、`test_gcb_ce.py`）前 40 行內要有 `# Nothing existing: <理由，≥15 字>`（`platform/tests/test_scope.py:75-80` TC-070），否則全套會紅。理由要具體說「搜過 Nextflow `google-batch` 與 Seqera 的做法，沒有現成可呼叫的離線預檢；官方 Python 套件被 TC-085 擋掉，所以用 gcloud 命令列」。
- 派工順序：`estimate-su-mcp` → 本任務 → C-2；同車道 `compute_envs.py`、`test_station_envs.py` 不可平行。

## 裁決（2026-10-24 03:05，developer-agent，回應 verifier 出題退回）
A. 範圍加 `docs/TESTING.md`：新增「gcb-ce-type」小節，寫 (a) 維護者放金鑰檔、跑 `ce create`、看到 `available`、全站搜不到金鑰片段的步驟；(b) 驗收者看 `git diff --name-only`、既有測試只動計畫列的那幾處；(c) 指向 PLATFORM.md「預檢不計費」那句。
B. 每一次 gcloud 呼叫（batch_api、bucket、其他）都用 env 的 `CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE` 帶同一個金鑰檔路徑，路徑不進 argv；env 不含任何 `ABF_` 開頭變數。對 `GOOGLE_APPLICATION_CREDENTIALS` 不下斷言。
C. 既有 `googlebatch-platform` 舊列：list／show 照舊、狀態維持 `unsupported`；`ce update` 舊列時照新規則驗證（缺 `project` 就拒，訊息說要補哪些欄位）；`ce preflight` 舊列同樣先過新規則。
D. `credential_file` 失敗訊息寫出應放的路徑（終端機管理者指令、路徑不是祕密），例外於「不露內部路徑」守則。
E. runner 逾時：每次呼叫 30 秒逾時，逾時記成該項 `fail` 並說「逾時」；停用中的 gcb 環境 update 不跑預檢。

## 裁決二（2026-10-24 03:40，developer-agent，回應 executor BLOCKED；與上文衝突一律以本段為準）
F. **平台本身不啟動任何程式（憲法原則 2，`test_scope.py` TC-071）不放寬。** gcloud 預檢改由**站台代理**執行：新增 `platform/abf_station/gcb_preflight.py`（把 executor 已寫的 `abf_platform/gcb_preflight.py` 搬過去，邏輯與注入式 runner 不變），`abf_platform/` 底下不得出現 `subprocess`。
G. **雲端用戶仍然什麼都不用裝**：平台主機的營運者在同一台主機跑一個站台代理（`abf-station run`，就是今天桌機上那一個），gcb 環境的 `agent` 指向它。所以作法裡「gcb 拒絕 agent」改成：gcb 環境**必須**有 agent，且預檢經既有的 `enqueue_preflight`／`apply_preflight` 走代理（`jobs._target` 對 gcb 環境放行 preflight 種類；其他種類——launch、resume 等——仍白話拒絕並指向 C-2）。
H. 金鑰檔的位置改由站台代理那一側決定（代理部署的 settings／環境變數），平台資料庫仍只存憑證**名稱**；平台不讀金鑰檔。`store.gcp_credentials_file` 拿掉。
I. 範圍檔清單：加 `platform/abf_station/gcb_preflight.py`、`platform/abf_station/agent.py`、`platform/abf_station/handlers.py`（只限接上 gcb 預檢）；`abf_platform/gcb_preflight.py` 刪除。
J. **測試、計畫、合約一律不寫出 PEM 私鑰標頭的字面字串**（`tests/credentials_stay_in_settings_test.sh` 會掃）；需要時在測試裡用字串拼接組出，並註解原因。
K. 裁決 C 補：舊 `googlebatch-platform` 列在 `ce update` 通過新規則後狀態設為 `creating`，再由預檢決定 available／invalid。缺金鑰檔時 `credential_shape`、`credential_project` 為 `unchecked`。

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
