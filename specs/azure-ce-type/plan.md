---
id: azure-ce-type
title: Azure Batch 計算環境類型：能建立、驗證、存放（憑證只放平台主機檔案，預檢不花錢）
branch: feat/azure-ce-type
tier: B
kinds: backend
lane: L2-platform-ce
after: aws-launch merged into v3
base: v3（aws-ce-type PR #246 已合；本任務必須等 aws-launch 合進 v3 後，才從那時的 v3 開分支。以下行號取自 origin/v3@fdfcc00，aws-launch 合併後一律重新核對）
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 3 的 C-5（Azure Batch／K8s「同模式」，本片只做 Azure Batch 的計算環境類型）；做法完全仿 memory/dev-plans/aws-ce-type.md（含其「裁決」與「裁決補充」）
---

# azure-ce-type

> 本檔由 developer-agent 的子 agent 起草（2026-10-28），**待 developer-agent 裁決「不確定的地方」第 1、2、3、6 點後才派工**。**只處理 C-5 的 Azure Batch 計算環境類型**：`azbatch-platform` 可以建立、驗證、儲存、預檢。**真的在 Azure Batch 上跑 Nextflow 是之後的 `azure-launch`，不在本任務。** B 級（使用者看得到的新能力）→ verifier 通過＋CI 綠由 developer-agent 自合。
> 車道 L2（`compute_envs.py`、`jobs.py`、`cli.py`），**不可與 aws-launch、aws-upload、aws-clean 平行**（見「不確定的地方」第 7 點的重疊表）。

## 目標
讓管理者能用 `abf-platform ce create --platform azbatch-platform --agent <平台主機上的代理> --batch-account … --storage-account … --location … --work-dir az://… --pool …` 登記一個 Azure Batch 環境，由**平台主機上的站台代理**檢查：設定合不合規、憑證檔讀不讀得到且形狀對、（裝了 `az` 命令列時）Batch 帳號金鑰能不能讀到指定的 pool 且 pool 是 active、儲存體容器存不存在。結果記成 `available` 或 `invalid`。

為什麼這樣切（同 aws，不重新發明）：①雲端用戶不裝站台代理（10-21 拷問二）——代理裝在平台主機上；②Azure 憑證只放代理那一側的檔案，資料庫只存憑證**名字**（`credentialsId`）；③預檢全部唯讀、不建 pool、不調整 pool 大小、不寫容器，所以**不計費**；④launch 留給 `azure-launch`，所以 `available` 的 Azure 環境在那之前仍**不能被選去送出**，也不會被自動挑為主要環境。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`（行號為該檔現況）：
- 「**C-5** Azure Batch／K8s：同模式」（第 169 行）→ 照 C-4（AWS）／C-1／C-2 的模式：類型常數、設定鍵規則、憑證檔在代理側、預檢唯讀、launch 另做。
- 「10-21，他定：雲端優先於畫布；雲端用戶不裝站台代理。」→ Azure 環境沒有「使用者自己的代理」；預檢由平台主機上的那個代理做；使用者什麼都不用裝。
- 「四種計算環境都建：nano4 → Google Batch … → AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（第 40 行）→ 憑證與環境分開，環境只記憑證名字。
- 「費用顯示美元、每人每月上限」（第 16 行）→ 本片不碰費用、不加任何幣別欄位。
- 「撞牆時先砍 …… AWS／Azure」（第 20 行）→ 本片刻意小：只做建立＋預檢，不做 launch、費用、上傳、清理。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/compute_envs.py`（新常數 `AZURE`；`CHECK_ONLY_TYPES` 加入 Azure；新增 `_AZURE_*` 規則與 `_check_azure`；`clean` 的分派加一支；`snapshot` 加 Azure 分支；`_VALUE_PATTERNS` 加三條 Azure 憑證字樣，見作法 3）
- `platform/abf_station/azure_preflight.py`（新；仿 `platform/abf_station/aws_preflight.py`；函式皆可注入）
- `platform/abf_station/handlers.py`（import 與 preflight 分支旁加 Azure 分支）
- `platform/abf_platform/jobs.py`（`_target` 的 CHECK_ONLY 拒絕訊息改成依類型分句；只動這一處，aws-launch 合併後的「每類型允許表」若已存在則在表中加 Azure 一列）
- `platform/abf_platform/cli.py`（`_config_from_args` 的旗標對照加 `--batch-account`、`--storage-account`、`--pool`；`add_argument` 區加這三個旗標；`--location` 與 `--spot` 的說明文字更新；`cmd_ce_preflight` 的舊記錄補齊檢查若已是 `PLATFORM_HOST_TYPES + CHECK_ONLY_TYPES` 則不必改）
- `platform/tests/test_azure_ce.py`（新）
- `platform/tests/test_station_envs.py`（只改「必須更新的既有斷言」列的幾處）
- `platform/tests/test_gcb_ce.py`（只改 UNSUPPORTED 數量斷言與 CHECKABLE／CHECK_ONLY_TYPES 斷言）
- `platform/tests/test_aws_ce.py`（只在「其餘 UNSUPPORTED 類型仍 unsupported」類的計數斷言需要時改，見「必須更新的既有斷言」）
- `platform/tests/test_station_docs.py`（TC-077 的跳過清單與計數）
- `platform/tests/test_launch_cli.py`（把「雲端 launch 被拒」例子換成仍為 unsupported 的類型）
- `docs/PLATFORM.md`（型別表、「Fourteen types」那段、新增「Azure Batch」小節）
- `docs/SEQERA_PARITY.md`（Azure Batch 列、F 節開頭那句）
- `docs/TESTING.md`（新增「Azure Batch environment (azure-ce-type)」小節，仿 aws 小節）
- `specs/azure-ce-type/ledger.md`（新，executor 進度帳本）

**不准碰**：網頁相關檔（`web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`）、`abf_launch/`、`gcb_preflight.py`、`aws_preflight.py`（只 import，不改）、`launch.py`、`cloud_store.py`、`clean.py`。

## 作法
1. **型別常數**：`PLATFORM_HOST_TYPES` **原樣保留**（它代表「檢查＋送出＋取消＋清理＋上傳都做好」，被 `jobs._target`、`cloud_store.workdir_bucket`、`abf_station/launch.py`、`snapshot` 依賴；把 Azure 放進去會讓 Azure 環境悄悄獲准排 `launch_nextflow`／`clean_work`／`put_upload`）。新增 `AZURE = "azbatch-platform"`，把它加進 `CHECK_ONLY_TYPES`：aws-launch 若把 `CHECK_ONLY_TYPES` 留成空 tuple（它的第 4 個未決問題預設如此），就改成 `(AZURE,)`；若 aws-launch 另有做法，以合併後的 v3 為準，原則不變——Azure 只開預檢（fail-closed）。`CHECKABLE` 的組法（`(SUPPORTED,) + PLATFORM_HOST_TYPES + CHECK_ONLY_TYPES`）自動納入，`create`／`update` 不必改。
2. **Azure 設定鍵（`_AZURE_CONFIG = _COMMON_CONFIG + (...)`，仿 `_AWS_CONFIG`）**。鍵名刻意避開 `key`／`secret`／`token`（`common.is_secret_name` 會擋）：
   | 鍵 | 型別／規則 | 對應 Nextflow |
   |---|---|---|
   | `location` | 必填；Azure 區域短名，如 `westeurope`、`japaneast`、`eastus2`；正規式 `^[a-z][a-z0-9]{2,39}\Z`（本計畫自訂的保守規則，見環境事實「查不到」） | `azure.batch.location` |
   | `batchAccountName` | 必填；3–24 字、只有小寫英文與數字 | `azure.batch.accountName` |
   | `storageAccountName` | 必填；3–24 字、只有小寫英文與數字（規則同 Batch 帳號，來源見「查不到」） | `azure.storage.accountName` |
   | `workDir` | 必填；`az://<container>/<子目錄>`；**子目錄必填**（Nextflow 文件明說不可只放容器名）；container 名 3–63 字、小寫英數與 `-`、頭尾為英數；子目錄不含 `..`、控制字元；總長 ≤`MAX_PATH`；去掉結尾斜線 | `workDir` |
   | `pool` | 必填；**已存在的** Batch pool ID：`^[A-Za-z0-9_-]{1,64}\Z`（字元集取自 Nextflow 文件；64 字上限是本計畫保守值） | `process.queue` |
   | `spot` | 選填；布林；**只存**（Nextflow 對應的是每個 pool 的 `lowPriority`，怎麼落地留給 `azure-launch`） | 平台自訂 |
   | `maxvCpus` | 選填；整數 1–10000；**只存**（同 aws，布林與字串拒收） | 平台自訂 |
   | `nextflowConfig`、`environment`、`preRunScript`、`postRunScript` | 沿用共用檢查 | 共用 |
   - 未知鍵 → `unknown setting for an Azure Batch environment: X (known: …)`（句型同 AWS）。舊的 `UNSUPPORTED` 範例記錄（鍵為 `region`、`vmType`）裡的這兩個鍵都是未知鍵，訊息要含該鍵名與「請刪除後重建這個計算環境」（沿 aws 裁決 5，不做別名）。
   - 全部錯誤一次列出、每個點名鍵、被拒的值最多顯示 60 字（沿用 `_shown`）。
   - **`agent` 必填**：`agent is required: an Azure Batch environment is checked by the agent that runs on the platform host, so name it with --agent (需要指定一個站台代理，就是平台主機上的那個)`。
3. **憑證只放名字**：用既有頂層欄位 `credentialsId`（`_CRED_NAME`；CLI `--credentials`），只是標籤，必填（沿 aws 裁決 8c）。`credential_findings` 原樣套用，並在 `_VALUE_PATTERNS` 補三條 Azure 字樣（Azure 帳號金鑰是 88 字 base64，沒有固定前綴，AWS 的 `AKIA` 那類規則抓不到）：`AccountKey\s*=`（連線字串）、`SharedAccessSignature\s*=`、`[?&]sig=[A-Za-z0-9%+/=]{16,}`（SAS 簽章）。新規則必須有測試證明不誤傷 `location`、`pool`、`workDir`、`batchAccountName` 等正常值。
4. **憑證檔位置（在代理那一側，平台不讀）**：`azure_preflight.credentials_path(settings_file, environ=None)` ＝ 環境變數 `ABF_STATION_AZURE_CREDENTIALS`，否則 `<deployment>/_personal/azure-credentials`（寫法照 `aws_preflight.credentials_path`）。檔案格式是 **INI，只讀 `[default]` 區段**（沿 aws 裁決 3、8），鍵名（**這是本計畫自訂的格式，Azure 沒有標準的共用憑證檔**，見不確定的地方第 2 點）：
   - `batch_account_key`（必填）
   - `storage_account_key` 或 `storage_sas_token`（二擇一，至少一個）
   - 檔案內容永遠不進 DB、日誌、任何回傳；程式只在記憶體裡用 `configparser`（`interpolation=None`、檔大小 ≤1 MB）解析，**只檢查鍵是否存在，不印值**；缺 `[default]` 時 detail 含檔案路徑、不列其他區段名（沿 aws 裁決 8b、12）。
5. **預檢（`azure_preflight.py`）**——唯讀、不計費、不建／刪／調整 pool、不建任何 job 或 task、不寫容器。簽名 `run_preflight(env, *, cred_path, now=time.time, runner=None, which=None, stat=os.stat) -> {"ok": bool, "checks": [{"name","status","detail"}]}`；`runner(argv, env, timeout)` 回 `(returncode, output_tail)`，預設走 `site.run_fixed`（固定 argv、無 shell），逾時 30 秒、輸出截 300 字。`_scrub`、`_check`、`_run` 直接 import 自 `gcb_preflight`（沿 aws 裁決 6，不動 gcb 檔）。**不 import 任何 `azure-*` Python 套件**（`azure.batch`、`azure.storage.blob` 等；同 boto3 的理由，且 TC-085 的精神是不引入雲端 SDK）。
   `clean_environment(ce)`：代理在組命令列前**再驗一次**，只留 `name, platform, credentialsId, location, batchAccountName, storageAccountName, workDir, pool`，重用 `compute_envs` 的 `_AZURE_*` 正規式，不合規 → `rules.Refusal`。
   | 檢查名 | 做什麼 | 通過／失敗 |
   |---|---|---|
   | `credential_name` | `credentialsId` 有設 | 沒設 → fail |
   | `credential_file` | 檔案存在、是一般檔案；POSIX 上 `mode & 0o077 == 0`；Windows 略過權限位並明說 | 缺檔 → fail，detail 寫出**應放的路徑**與 `chmod 600` |
   | `credential_shape` | 在記憶體解析；要有 `[default]` 區段、`batch_account_key`、以及 `storage_account_key` 或 `storage_sas_token` 其一；**不看值**；失敗訊息只講缺哪個鍵 | fail 時不印任何值 |
   | `az` | `which("az")`；沒有 → **unchecked**（不是 fail） | |
   | `pool` | `az batch pool show --pool-id P --query state --output tsv`（金鑰經環境變數，見下）；輸出 `active` → pass；pool 不存在 → fail「pool 不存在於這個 Batch 帳號」；`deleting` → fail。這一項同時證明 Batch 帳號名、區域（endpoint）、金鑰三者正確，所以不另設 `batch_account` 檢查 | rc≠0 → fail＋`_scrub` 後前 300 字 |
   | `storage` | `az storage container exists --name C --output tsv --query exists`（帳號名與金鑰／SAS 經環境變數，`--auth-mode key`）；輸出為真值 → pass；為假 → fail「容器不存在」 | rc≠0 → fail＋`_scrub` 後前 300 字 |
   - 憑證檔不可用或沒有 `az` 時，`pool`、`storage` 為 `unchecked` 且 `runner` 一次都不呼叫。逾時只讓該項 fail。任何一項不是 pass 就不是 `available`。機器上沒有 `az` 時環境停在 `invalid`，訊息明說缺 `az`。
   - **每次呼叫的環境變數**（`_az_env`）：從 `os.environ` 複製，**刪掉**所有 `ABF_*` 與 `AZURE_*`（含 `AZURE_CONFIG_DIR`、`AZURE_CLIENT_*`、`AZURE_BATCH_*`、`AZURE_STORAGE_*`）；再設：`AZURE_BATCH_ACCOUNT=<batchAccountName>`、`AZURE_BATCH_ENDPOINT=https://<batchAccountName>.<location>.batch.azure.com`、`AZURE_BATCH_ACCESS_KEY=<batch_account_key>`、`AZURE_STORAGE_ACCOUNT=<storageAccountName>`、`AZURE_STORAGE_KEY=<storage_account_key>`（或改設 `AZURE_STORAGE_SAS_TOKEN`）、`AZURE_CONFIG_DIR=<每次新建的空暫存目錄>`（不准悄悄改用主機上 `az login` 留下的登入狀態；呼叫完刪除）、`AZURE_CORE_COLLECT_TELEMETRY=false`、`AZURE_CORE_NO_COLOR=true`、`AZURE_CORE_ONLY_SHOW_ERRORS=true`。金鑰與路徑**只在 env，不在 argv**；argv 只有 pool ID 與容器名（兩者不是祕密）。
   - 結果走既有紀錄路徑：`jobs` 的 preflight 工作 → `compute_envs.apply_preflight`，`verdict_message` 不改。
6. **代理接線（handlers.py）**：`kind == "preflight"` 且 `ce["platform"] == azure_preflight.TYPE` → `azure_preflight.run_preflight(azure_preflight.clean_environment(ce), cred_path=azure_preflight.credentials_path(ctx.settings_file))`，回 `("done", _verdict(res["checks"]))`，與 aws 分支同形。Azure 環境**不得**落到 Slurm 的 `rules.clean_environment` 路徑。
7. **`snapshot`**：`v["platform"] == AZURE` 時回 `{name, platform, credentialsId, location, batchAccountName, storageAccountName, workDir, pool}`。其他類型的回傳一個字都不變。
8. **`jobs._target`**：Azure 環境收到 `preflight` 以外的工作種類 → `JobRefused`，訊息依類型分句：`%s is an Azure Batch environment: it is checked on the platform host, and launching on it is not built yet (尚未支援送出；下一步 azure-launch)`。aws-launch 合併後 AWS 已可送出，所以原本寫死 "AWS Batch" 的句子必須先確認已改成依類型取名；本任務只加 Azure 的句子，不改 AWS 的。`put_upload` 等對非 `PLATFORM_HOST_TYPES` 的拒絕不動。
9. **送出與自動選擇不放行（不改程式，要有測試）**：`abf_launch/build.py` 的 `primary_environment` 只選 `SUPPORTED` 與 aws-launch 後新增的可送出類型；Azure 永遠不被自動挑；`target_problem` 走 `jobs.check_target` → 作法 8 的拒絕。
10. **CLI**：`ce create`／`ce update` 的第一次預檢沿用 `_queue_first_preflight`；`_default_agent` 只對 `SUPPORTED` 生效（雲端環境必須明寫 `--agent`）。新旗標：`--batch-account`（`batchAccountName`）、`--storage-account`（`storageAccountName`）、`--pool`（`pool`）；`--location` 已存在（gcb 用），Azure 共用同一旗標，只更新說明文字為「Google Batch／Azure Batch: the region」；`--spot`／`--no-spot` 說明加上 Azure Batch；`maxvCpus` 用 `--config-json`。`cmd_ce_preflight` 的舊記錄補齊檢查須涵蓋 Azure（若 aws-ce-type 已寫成 `PLATFORM_HOST_TYPES + CHECK_ONLY_TYPES` 就自動涵蓋）。
11. **既有 `azbatch-platform` 舊列**（以前一律 `unsupported`，鍵為 `region`／`vmType` 之類）：`ce list`／`ce show` 照舊顯示、狀態維持 `unsupported`；`ce update` 與 `ce preflight` 一律先過新規則，`region`／`vmType` 被當未知鍵拒絕，訊息含該鍵名與「請刪除後重建這個計算環境」。
12. **文件**：`docs/PLATFORM.md` 的型別表 Azure 列 Supported 欄改為 `checked on the platform host (launch: not yet)`；「Fourteen types」那段的「the other eleven」改成 ten（並加 Azure 到「can be created and checked」）；新增「Azure Batch」小節（鍵表、檢查表、憑證檔位置與 `ABF_STATION_AZURE_CREDENTIALS`、`[default]` 區段與三個鍵名、「預檢不計費：只讀，不建 pool、不建 job」、平台主機要裝 `az` 命令列、pool 必須事先由營運者建好）。`docs/SEQERA_PARITY.md`：Azure Batch 列改成 `Have (create + check); launch in azure-launch`，勾選維持 `[ ]`。`docs/TESTING.md` 新增手動小節。範例一律用 `lab-container`、`labbatch`、`labstore`、`westeurope`、`lab-pool`，不得出現真實帳號名、訂閱 ID 或金鑰。
13. **不需要 migration**：同一張 `compute_envs` 表的新 `config_json` 鍵，`status` 沿用既有五種值；舊紀錄不受影響。

## 失敗先行測試（`platform/tests/test_azure_ce.py`，現在都會紅；全部用假 `runner`、假 `which`，不碰網路；仿 `platform/tests/test_aws_ce.py` 的夾具）
工具常數：`LOC="westeurope"`、`BATCH="labbatch"`、`STORE="labstore"`、`WORKDIR="az://lab-container/work/"`、`POOL="lab-pool"`、`CRED="azure-lab"`；`good_config()` ＝ `{"location":LOC,"batchAccountName":BATCH,"storageAccountName":STORE,"workDir":WORKDIR,"pool":POOL}`；`fields()` 帶 `agent="a1"`。**金鑰一律用字串拼接組出**（`tests/credentials_stay_in_settings_test.sh` 會掃全 repo）：`BKEY = "MARKER" + "BATCHKEY" + "A" * 60`、`SKEY = "MARKER" + "STOREKEY" + "B" * 60`、`SAS = "sv=2024-01-01&" + "s" + "ig=" + "MARKERSAS" + "C" * 30`；`CRED_FILE = "[default]\nbatch_account_key = " + BKEY + "\nstorage_account_key = " + SKEY + "\n"`。

建立與驗證：
- `test_a_valid_azure_batch_environment_is_created_as_creating`：`good_config()` ＋ `spot:true, maxvCpus:256` → `create` 成功、`status=="creating"`、`config["workDir"]=="az://lab-container/work"`（結尾斜線去掉）、`message` 含「waiting for the first preflight」。
- `test_required_settings_and_agent`：`location`、`batchAccountName`、`storageAccountName`、`workDir`、`pool` 各缺一個 → 錯誤點名該鍵；缺 `agent` → 訊息含「需要指定一個站台代理」；`ce create` 不給 `--agent` 即使線上只有一個代理也被拒。
- `test_location_rules`：`westeurope`、`japaneast`、`eastus2` 通過；`West Europe`、`eu-west-1`、`""`、`a; b` 被拒，訊息含 `westeurope` 範例。
- `test_account_name_rules`：`labbatch`、`ab1` 通過；`LabBatch`、`ab`（太短）、25 字、`lab-batch`、`lab_batch` 被拒（Batch 與 storage 各測一次）。
- `test_workdir_must_be_an_azure_blob_url_with_a_subfolder`：`/data/work`、`s3://b/x`、`gs://b/x`、`az://`、`az://lab-container`（沒有子目錄）、`az://lab-container/`、`az://UPPER/x`、`az://ab/x`（容器名太短）、`az://lab-container/../x` 各被拒；`az://lab-container/work/` → 存成 `az://lab-container/work`。
- `test_pool_is_an_id_not_a_path`：`lab-pool`、`Pool_1` 通過；`a b`、`a/b`、65 字名字、`""` 被拒。
- `test_spot_and_maxvcpus_rules`：`spot:"yes"` 被拒；`maxvCpus:0`、`10001`、`true`、`"8"` 被拒；`maxvCpus:10000` 通過。
- `test_unknown_keys_are_refused_and_old_keys_say_what_to_do`：`region`、`vmType`、`jobQueue`、`headQueue`、`project`、`foo` 各被拒，訊息含 `unknown setting for an Azure Batch environment` 與已知鍵清單；`region`、`vmType` 的訊息另含「請刪除後重建這個計算環境」。
- `test_all_errors_are_listed_at_once_and_values_are_cut`：同時錯三個鍵 → 一則訊息含三個鍵名；一個 200 字的壞值在訊息裡 ≤ 60 字。
- `test_shared_checks_apply`：`nextflowConfig` 超過 20000 字、`environment` 項目鍵名不合規 → 與 Slurm 相同的拒絕。

憑證不進資料庫：
- `test_the_credential_is_only_a_name_at_the_top_level`：`credentialsId="azure-lab"` 存下；`ce show` 的 `credentialsId` 為 `azure-lab`；config 裡沒有任何憑證鍵。
- `test_credentials_id_is_a_name_only`：含空白、`=`、`BKEY` 的 `credentialsId` 被拒。
- `test_an_account_key_or_sas_pasted_anywhere_is_refused_and_not_repeated`：把 `AccountKey=` 開頭的連線字串、`SharedAccessSignature=…`、含 `sig=` 的 `SAS` 放進 `description`、`nextflowConfig`、`environment` 的值、`workDir` 的子目錄 → 全被拒；錯誤訊息只含欄位路徑，不含該字串；DB 檔位元組比對沒有 `BKEY`／`SKEY`／`SAS` 片段。
- `test_a_key_named_field_is_refused`：config 有 `batchAccountKey`、`accountKey`、`sasToken`、`servicePrincipalSecret` → 被 `credential_findings` 擋。
- `test_normal_values_are_not_mistaken_for_secrets`：`good_config()` 完整建立成功（新增的 `_VALUE_PATTERNS` 不誤傷 `location`、`pool`、`workDir`、帳號名）；另測含 `design=1`、`signature` 字樣的普通 `description` 不被誤擋。
- `test_the_platform_does_not_read_the_credential_file`：把 `CRED_FILE` 寫在代理部署的 `_personal/` 下，建立、列出、`ce show` 之後，`platform.db` 位元組與所有 CLI 輸出都找不到 `BKEY`、`SKEY`。

預檢（假 runner，`monkeypatch.setattr(azure_preflight, "_run", runner)`，假裝有／沒有 `az`）：
- `test_every_check_is_reported_with_name_status_and_detail`：六項名稱依序為 `credential_name, credential_file, credential_shape, az, pool, storage`。
- `test_a_missing_credential_name_is_a_failure`：不設 `credentialsId` → `credential_name` fail、`credential_shape` unchecked。
- `test_a_missing_credential_file_says_where_to_put_it`：沒有檔 → `credential_file` fail，detail 含 `<deployment>/_personal/azure-credentials` 的實際路徑與 `chmod 600`；`pool`、`storage` unchecked；環境 `invalid`；`runner` 呼叫 0 次。
- `test_the_credential_file_location_follows_the_agents_setting`：設 `ABF_STATION_AZURE_CREDENTIALS=<tmp>/x` → 用該路徑；沒設 → `<settings 檔 parent.parent>/_personal/azure-credentials`。
- `test_a_credential_file_other_people_can_read_is_refused`（POSIX 專用）：mode 0644 → fail、detail 含 `chmod 600`；0600 → pass。
- `test_permission_bits_are_not_checked_on_windows`：假裝 `sys.platform=="win32"` → pass 且 detail 含「Windows 不檢查權限位」。
- `test_a_credential_file_that_is_a_folder_is_refused`：路徑是資料夾 → fail「not a regular file」。
- `test_the_shape_of_the_file_is_judged_without_printing_it`：(a) 缺 `batch_account_key` → fail，detail 含該鍵名；(b) 沒有 `[default]`（只有 `[other]`）→ fail，detail 含「沒有 [default] 區段」與檔案路徑、**不含** `other`；(c) 有 `batch_account_key` 但 `storage_account_key` 與 `storage_sas_token` 都沒有 → fail，detail 含這兩個鍵名；(d) 只有 `storage_sas_token` 也算通過；(e) 不是 INI（隨機位元組）→ fail 且 detail 為固定句。整份 `checks` JSON 與環境 `message` 都不含 `BKEY`、`SKEY`、`SAS`。
- `test_without_the_az_cli_the_api_checks_are_unchecked_and_nothing_is_run`：`which` 回 None → `az` unchecked、`pool`／`storage` unchecked、環境 `invalid`、`message` 含「az」與「沒裝」；`runner` 呼叫 0 次。
- `test_all_checks_passing_makes_the_environment_available`：假 runner 對 `batch pool show` 回 `(0,"active")`、對 `storage container exists` 回 `(0,"true")` → 六項皆 pass、`status=="available"`。
- `test_a_pool_that_is_missing_or_not_active_fails`：batch 回 `(3, "PoolNotFound …")` → `pool` fail 且 detail 含 `lab-pool`；回 `(0,"deleting")` → fail；`storage` 仍被執行。
- `test_a_missing_container_fails`：storage 回 `(0,"false")` → `storage` fail 且 detail 含容器名 `lab-container`。
- `test_an_api_failure_is_reported_trimmed_and_scrubbed`：storage 回 `(1, 2000 字，其中夾 AccountKey= 連線字串與一段 88 字 base64)` → fail、detail ≤300 字、不含該連線字串也不含該 base64。
- `test_a_timeout_fails_that_check_only`：pool 的假 runner 丟 `TimeoutError` → `pool` fail 且 detail 含「逾時」；`storage` 仍被執行。
- `test_the_commands_are_read_only`：記錄所有 argv；每條前綴必為 `az batch pool show` 或 `az storage container exists`；沒有任何一條含 `create`、`delete`、`resize`、`update`、`upload`、`set`、`start`、`stop`、`login`、`autoscale`、`job`、`task`、`copy`、`remove` 這些字（**不花錢保證**）。
- `test_the_credential_goes_in_the_environment_not_in_argv`：每次呼叫的 env 有 `AZURE_BATCH_ACCOUNT=="labbatch"`、`AZURE_BATCH_ENDPOINT=="https://labbatch.westeurope.batch.azure.com"`、`AZURE_BATCH_ACCESS_KEY==BKEY`（`storage` 那次是 `AZURE_STORAGE_ACCOUNT`、`AZURE_STORAGE_KEY==SKEY`；檔裡只有 SAS 時改為 `AZURE_STORAGE_SAS_TOKEN`）、`AZURE_CONFIG_DIR` 指向一個空的暫存目錄、`AZURE_CORE_COLLECT_TELEMETRY=="false"`；argv 不含 `BKEY`、`SKEY`、`SAS`、憑證檔路徑；env 不含任何 `ABF_` 開頭變數；測試先在自己的環境設 `AZURE_CLIENT_SECRET=X`、`AZURE_STORAGE_KEY=Y`、`ABF_PLATFORM_TOKEN=T` 後，env 裡沒有繼承到這三個；呼叫結束後暫存的 `AZURE_CONFIG_DIR` 已刪除。
- `test_the_default_runner_is_a_fixed_argv_without_a_shell`：呼叫 `azure_preflight._run(["az","storage","container","exists"], {"A":"1"}, 30)` 時（`subprocess.run` 以假物件替換）收到 `shell=False`、list 型 argv、`timeout=30`。
- `test_the_agent_judges_the_environment_again_before_it_builds_a_command`：把 `location:"x; touch c"`、`batchAccountName:"A B"`、`workDir:"az://lab-container"`、`pool:"q q"`、`credentialsId:"a b"` 各送進 `azure_preflight.clean_environment` → `rules.Refusal`；`platform` 為 `slurm-platform` 或 `awsbatch-platform` → 同樣被拒。

接線與 CLI：
- `test_create_queues_the_first_preflight_for_the_agent`：`ce create --platform azbatch-platform --agent a1 --credentials azure-lab --location westeurope --batch-account labbatch --storage-account labstore --work-dir az://lab-container/work --pool lab-pool`（代理 `a1` 在線）→ rc 0、輸出含「preflight queued」、`jobs` 表多一列 `preflight`、其 args 的 `ce` 即 `snapshot`：鍵集合恰為 `{name, platform, credentialsId, location, batchAccountName, storageAccountName, workDir, pool}`。
- `test_create_with_the_agent_offline_says_so_and_does_not_pretend`：代理離線 → 訊息含「沒有代理在線」，狀態仍 `creating`，`jobs` 表沒有新列。
- `test_ce_preflight_waits_for_the_agent_and_prints_each_check`：`auto_serve` 夾具下 `ce preflight az1` → 每項印 `name: status - detail`。
- `test_cli_flags`：`--batch-account`、`--storage-account`、`--pool`、`--location`、`--spot` 分別進到對應 config 鍵；`--no-spot` → `spot:false`。
- `test_slurm_google_batch_and_aws_batch_are_unchanged`：Slurm、gcb、aws 建立後仍各走自己的預檢；三者的 `snapshot` 與改動前逐鍵相同。
- `test_jobs_other_than_the_preflight_are_refused_in_plain_words`：對 `available` 的 Azure 環境 `enqueue_*` 為 `launch_nextflow`、`cancel_run`、`clean_work`、`put_upload`、`list_site_files`、`pipeline_files` → 全 `JobRefused`，訊息含「尚未支援送出」與 `azure-launch`、不含 "AWS"，`jobs` 表列數不變。
- `test_launch_is_refused_and_the_environment_is_never_auto_picked`：`build.target_problem(state,"az1","launch_nextflow")` 回非 None 的白話句；只有一個 `available` 的 Azure 環境時 `build.primary_environment` 回 None；有 `available` 的 Slurm 環境時選 Slurm。
- `test_another_users_azure_environment_is_not_found`：B 以 `owner=` 取 A 的 Azure 環境 → None；B 對它 `enqueue_preflight` → 與不存在相同的 `JobRefused` 文字。
- `test_updating_a_disabled_environment_queues_no_preflight`：`ce disable` 後 `ce update --pool other` → 設定改了、`jobs` 表列數不變。

舊記錄與其他類型：
- `test_an_old_azure_record_is_still_listed_and_shown`：直接 SQL 插一列 `azbatch-platform`、`status='unsupported'`、`config_json='{"workDir":"az://lab-container/work","region":"westeurope","vmType":"Standard_D4s_v3"}'` → `ce list`、`ce show` 照常；狀態仍 `unsupported`。
- `test_an_old_record_is_refused_with_the_next_step`：對該列 `ce preflight` 與 `ce update --agent a1 --pool lab-pool` → rc≠0，訊息含 `region` 或 `vmType` 與「請刪除後重建這個計算環境」。
- `test_the_other_types_stay_unsupported`：其餘 10 個 `UNSUPPORTED` 類型仍 `create` 成功且 `unsupported`。
- `test_no_cloud_library_is_imported`：`azure_preflight.py` 無 `import azure`／`boto3`／`botocore`／`google`／`requests`；`pyproject.toml` 不含 `azure-`、`boto3`、`botocore`。
- `test_the_platform_package_starts_no_program`：`abf_platform/` 底下沒有 `subprocess`。
- `test_no_launch_cost_or_upload_code_for_azure`：`abf_platform/`、`abf_station/` 的原始碼沒有 `az batch pool create`、`az batch pool delete`、`az batch pool resize`、`az batch job`、`az batch task`、`az storage blob upload`、`az storage blob delete`、`az storage container create`、`azcopy`；`azure_preflight.py` 沒有 `-with-tower`。
- `test_tool_list_unchanged_and_no_new_web_route`：MCP 工具名集合仍是現有 12 個；`web.py` 路由表不變（同 `test_gcb_ce.py` 那條的檢查）。
- `test_docs_list_every_azure_key_and_check`：`docs/PLATFORM.md` 含 `` `location` ``、`` `batchAccountName` ``、`` `storageAccountName` ``、`` `workDir` ``、`` `pool` ``、`` `spot` ``、`` `maxvCpus` ``、六個檢查名各一個、`ABF_STATION_AZURE_CREDENTIALS`、`_personal/azure-credentials`、`batch_account_key`、`預檢不計費`、`creates no pool`；`SEQERA_PARITY.md` 的 `azbatch-platform` 列含 `Have (create + check); launch in azure-launch` 且以 `[ ] |` 結尾；`TESTING.md` 含 `azure-ce-type`、`預檢不計費`、`git diff`；三份文件都找不到 `AccountKey=`、`sig=` 字樣、也找不到 GUID 形狀的訂閱／租戶 ID。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」；以下行號取自 v3@fdfcc00，aws-launch 合併後先重新核對，**用語意定位**）
- `platform/tests/test_station_envs.py` 的 `UNSUPPORTED`（頂部約 :19-32）：**移除 `azbatch-platform` 那一筆**（約 :20），剩 10 種。它被 TC-030、TC-096、TC-085、`test_station_e2e.py` 的 TC-031、`test_gcb_ce.py`、（aws-ce-type 之後）`test_aws_ce.py` 使用。
- 同檔的函式名與註解：`test_tc030_the_eleven_modelled_types_are_stored_as_not_supported` 與頂部註解「the 11 types」改「ten／10」；斷言本身不動。
- 同檔 TC-032（約 :162-163）：`sorted(set(UNSUPPORTED) | {"slurm-platform","googlebatch-platform","awsbatch-platform"}) == sorted(KINDS)` 的集合加入 `"azbatch-platform"`（aws-launch 若已改過這個集合，以合併後的樣子為準，再加一個）；`len(KINDS)==14` 不動。
- 同檔 TC-096（約 :283-292）：`"azbatch-platform"` 與 `UNSUPPORTED["azbatch-platform"]` 改用 `"azcloud-platform"` 與 `UNSUPPORTED["azcloud-platform"]`（它在測「尚未支援的環境不能當主要」，換另一個 unsupported 類型意思不變）。
- 同檔 TC-085（約 :464-484）：迴圈自動縮成 10 種，斷言不動。它禁止原始碼 import 雲端套件——本任務依賴 `az` 命令列而非套件，不會撞；若 executor 想加 `azure-*` Python 套件，視為違規，回報 BLOCKED。
- `platform/tests/test_gcb_ce.py` 約 :816 `assert len(UNSUPPORTED) == 11` → `== 10`；約 :849-851 TC-089：`CHECK_ONLY_TYPES == ("awsbatch-platform",)` 與 `CHECKABLE == (SUPPORTED, GCB, "awsbatch-platform")` 要改成合併後 v3 的樣子再加 `AZURE`（aws-launch 若已把 AWS 搬進 `PLATFORM_HOST_TYPES`，則改成 `CHECK_ONLY_TYPES == ("azbatch-platform",)`、`CHECKABLE` 相應調整）。**以合併後 v3 的實際值為準，只加 Azure，不動其他類型的斷言。**
- `platform/tests/test_station_docs.py` TC-077（約 :66-90）：跳過清單加 `"azbatch-platform"`；`== 11` 改 `== 10`（Azure 的列改為 `Have (create + check); launch in azure-launch`，不再是 "Modelled, needs a real account"）；`## F. Compute environments` 標題與 `KINDS` 必須出現在 PLATFORM.md 的斷言不動。
- `platform/tests/test_launch_cli.py` 約 :306-308：這個測試是「雲端類型的 launch 被拒、且沒呼叫任何雲端工具」。`azbatch-platform` 現在需要 `--agent`，用舊的 `{"workDir":"az://bucket/work","region":"westeurope"}` 會在 `ce create` 就被拒。改成 `"azcloud-platform"`、config 為 `{"workDir":"az://bucket/work","instanceType":"Standard_D4s_v3"}`（仍是 unsupported）；其餘斷言（rc、`refuse(...)` 的 `尚未支援|not supported`、`log` 為空）不動。aws-launch 若已把這個例子換成 Azure 或 K8s 類型，以合併後的樣子為準，凡指到 `azbatch-platform` 的都換成仍為 unsupported 的類型。
- `test_launch_bundle.py`（約 :450）、`test_station_launch.py`、`test_cloud_cost.py`、`test_estimate_su.py`、`test_web_parity.py`：若 aws-launch 把任何一處改成指向 `azbatch-platform` 的「仍 unsupported」例子，本任務要一併換成別的 unsupported 類型；沒有指到就**不准動**。
- `test_scope.py::test_tc070`：新檔需有檔首標頭（見「環境事實」）。
- **executor 在實作前先跑一次全套找出任何還沒列到的紅，列在 ledger；超出上列範圍就回報 BLOCKED，不要自己改。** 已知環境紅：`test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched`，若它是唯一的紅視為綠。

## 完成標準（done when）
- 自動：上面所有新測試綠；全套綠（在 WSL 跑 `tests/run_all.sh`）；MCP 工具數仍 12；`git diff --name-only` 只含「範圍：檔案」列出的檔，且不含任何網頁檔。
- 手動（維護者，Azure 帳號開好後做一次，**不計費**）：事先建好 Batch 帳號、儲存體帳號、blob 容器與一個 pool（營運者手動做，本任務不建）；在平台主機裝 Azure CLI，把憑證檔放到 `<agent deployment>/_personal/azure-credentials`（600，`[default]` 區段）；`abf-platform ce create --name az1 --platform azbatch-platform --agent <代理> --credentials azure-lab --location <區域> --batch-account <名> --storage-account <名> --work-dir az://<容器>/work --pool <pool>`，看到每項檢查；全 pass 時 `ce show az1` 顯示 `available`；`ce show` 輸出與 `platform.db` 裡搜不到金鑰任何片段。**這一次手動也要驗證「用金鑰環境變數執行 `az batch pool show` 不需要先 `az batch account login`」（目前查不到，見環境事實）；若需要，回報 developer-agent 改檢查方式。**
- 文件：`docs/PLATFORM.md`、`docs/SEQERA_PARITY.md`、`docs/TESTING.md` 依作法 12 更新。

## 環境事實
**平台內部（origin/v3@fdfcc00 現況，aws-launch 合併後須重新核對）**
- `compute_envs.py`：`KINDS` 14 個識別字，`azbatch-platform` 為 `Azure Batch`；`SUPPORTED`＝`"slurm-platform"`；`PLATFORM_HOST_TYPES = ("googlebatch-platform",)`；`AWS = "awsbatch-platform"`、`CHECK_ONLY_TYPES = (AWS,)`；`CHECKABLE = (SUPPORTED,) + PLATFORM_HOST_TYPES + CHECK_ONLY_TYPES`。`_AWS_CONFIG`／`_check_aws` 是本任務的直接範本。現在 `azbatch-platform` 走 `_check_other`（只有共用檢查），狀態 `unsupported`。
- `abf_station/aws_preflight.py`（範本）：`credentials_path`、`clean_environment`、`_aws_env`（先刪 `ABF_*` 與 `AWS_*` 再設）、`_read_shape`（`configparser`、`[default]`、只看鍵名、拒絕 `credential_process`）、`run_preflight`。`_scrub`／`_check`／`_run` 來自 `gcb_preflight`。
- 平台本身不啟動任何程式（`test_scope.py` TC-071）：`abf_platform/` 不得出現 `subprocess`；啟動 `az` 只在 `abf_station/`，經 `site.run_fixed`。
- 新 `.py`（含測試）前 40 行要有 `# Nothing existing: <理由，≥15 字>`（`test_scope.py` TC-070）。理由要具體：搜過 Nextflow `azurebatch` executor 與 Seqera 的 Azure Batch 表單，沒有離線又不計費的預檢；Azure 官方 Python 套件被「不引入雲端 SDK」規則擋掉，所以用 `az` 命令列。
- 憑證防線：`common.is_secret_name`（正規式 `token|password|secret|key`，不分大小寫）＋`compute_envs._VALUE_PATTERNS`；`tests/credentials_stay_in_settings_test.sh` 掃全 repo（它的 `SHAPES` 抓 JWT、`ghp_`、`AKIA`、`-----BEGIN … PRIVATE KEY-----` 等，測試與計畫不得有完整金鑰字面，故測試金鑰用字串拼接）。
- 已定案的 aws 規則在本任務沿用：憑證檔讀 `[default]`、`credentialsId` 只是必填標籤、舊鍵視為未知鍵並教使用者刪除重建、直接 import `gcb_preflight` 的私有輔助函式、缺憑證檔時 detail 含實際路徑（刻意例外）。出處：`memory/dev-plans/aws-ce-type.md` 的「裁決」與「裁決補充」。

**Nextflow 的 Azure 設定（來源 URL；本片不產生任何 Nextflow 設定，核對屬 `azure-launch`，但鍵名對應表依據如下）**
- 官方文件 `https://www.nextflow.io/docs/latest/azure.html`（會 302 轉到 `https://docs.seqera.io/nextflow/azure`，以下以轉址後內容為準）：`process.executor = 'azurebatch'`；`workDir = 'az://<blob-container>/work'`，**必須含至少一層子目錄，不可只寫容器名**；每個 process 都要有 `container`；必要設定 `azure.storage.accountName`、`azure.batch.accountName`、`azure.batch.location`；pool ID 由 `queue` 指令指定；`azure.batch.allowPoolCreation` 預設 false；`autoPoolMode` 文件範例設 true；既有 pool 必須 `dockerCompatible`，且每節點 task slots 要等於 VM 核心數；具名 pool 設在 `azure.batch.pools.<name>`；Spot（low priority）是每個 pool 的 `lowPriority = true`；pool 名限英數、`-`、`_`；儲存體帳號與容器必須與 Batch 帳號同區域；`az account list-locations -o table` 可列區域；自訂映像與虛擬網路需 Entra（service principal 或 managed identity）；Azure file share 需要儲存體帳號金鑰；Nextflow 自動產生的 SAS 有效 48 小時（`azure.storage.tokenDuration`）。
- 設定鍵清單 `https://docs.seqera.io/nextflow/reference/config/azure`：`azure.batch.accountName`、`accountKey`（環境變數 `AZURE_BATCH_ACCOUNT_KEY`）、`location`、`allowPoolCreation`、`autoPoolMode`、`endpoint`；`azure.storage.accountName`、`accountKey`（`AZURE_STORAGE_ACCOUNT_KEY`）、`sasToken`（`AZURE_STORAGE_SAS_TOKEN`）、`tokenDuration`；`azure.activeDirectory.servicePrincipalId／servicePrincipalSecret／tenantId`（`AZURE_CLIENT_ID`／`AZURE_CLIENT_SECRET`／`AZURE_TENANT_ID`）；`azure.managedIdentity.*`；`azure.batch.pools.<name>.{vmType, vmCount, autoScale, maxVmCount, lowPriority, virtualNetwork, …}`。
- 儲存體驗證 `https://docs.seqera.io/nextflow/azure-blob`：帳號金鑰、SAS（要去掉開頭的 `?`）、service principal、managed identity 四種方式，與上列環境變數備援。
- 本計畫的鍵名對應：`location`→`azure.batch.location`、`batchAccountName`→`azure.batch.accountName`、`storageAccountName`→`azure.storage.accountName`、`pool`→`process.queue`、`workDir`→`workDir`；`spot`→每個 pool 的 `lowPriority`（只存，不落地）。**這個對應只是命名表，不是已驗證的設定；`azure-launch` 的計畫必須重新讀上列官方文件。**

**Azure 命令列與服務（來源 URL）**
- `az batch pool show`：`https://learn.microsoft.com/en-us/cli/azure/batch/pool?view=azure-cli-latest`——有 `--pool-id`、`--query`；Batch 帳號參數 `--account-name`（環境變數 `AZURE_BATCH_ACCOUNT`）、`--account-key`（`AZURE_BATCH_ACCESS_KEY`）、`--account-endpoint`（`AZURE_BATCH_ENDPOINT`）。該頁同時有 `az batch pool delete`、`resize` 等會改變狀態的指令，**預檢絕不呼叫**（測試以禁用字掃描）。
- `az storage container exists`：`https://learn.microsoft.com/en-us/cli/azure/storage/container?view=azure-cli-latest`——參數 `--name`、`--account-name`、`--account-key`、`--sas-token`、`--auth-mode {key,login}`；環境變數 `AZURE_STORAGE_ACCOUNT`、`AZURE_STORAGE_KEY`、`AZURE_STORAGE_SAS_TOKEN`、`AZURE_STORAGE_AUTH_MODE`、`AZURE_STORAGE_CONNECTION_STRING`；只給帳號名而沒有金鑰或 SAS 時，CLI 會嘗試用已登入的帳號去查金鑰（所以預檢要清掉主機的登入狀態，見作法 5 的 `AZURE_CONFIG_DIR`）。
- Batch 帳號：`https://learn.microsoft.com/en-us/azure/batch/batch-account-create-portal`——帳號名 3–24 字、只有小寫英文與數字、在區域內唯一；endpoint 形式 `https://<account>.<region>.batch.azure.com`；支援 Entra ID 與 Shared Key 兩種驗證；「User subscription mode Batch accounts must be accessed by using Microsoft Entra ID」（所以 user subscription 模式的帳號不能用本片的金鑰預檢）；帳號可被設成只准 Entra。
- Entra 驗證：`https://learn.microsoft.com/en-us/azure/batch/batch-aad-auth`——Batch 資源 endpoint 為 `https://batch.core.windows.net/`。本片不支援，留給之後。
- Spot VM：`https://learn.microsoft.com/en-us/azure/batch/batch-spot-vms`——Batch 現在稱 "Spot"，pool 設定仍叫 `targetLowPriorityNodes`；Spot 沒有最高出價，只因容量被收回。

**查不到（官方資料沒讀到或沒有明說，計畫裡只能當保守規則或待驗證項）**
- Azure blob 容器名稱規則：這次沒讀到官方頁面，計畫用的 3–63 字、小寫英數與 `-`、頭尾英數是保守子集，維護者實測時若遇到合法名稱被拒要回報。
- 儲存體帳號名稱規則：同上，沿用 Batch 帳號的 3–24 字小寫英數規則。
- Batch pool ID 的長度上限（計畫用 64）；Nextflow 文件只說字元集。
- Azure 區域短名的完整格式規則（計畫用 `^[a-z][a-z0-9]{2,39}\Z`）。
- `az batch pool show` 只靠環境變數裡的帳號金鑰（不先 `az batch account login`）是否能成功：CLI 文件列出了這些環境變數，但沒有明說這樣可單獨運作。**需要維護者手動驗證一次（完成標準已列）。**
- Nextflow 是否接受 `spot` 這個鍵：不接受，它用 `lowPriority`；因此 `spot` 純屬平台自訂鍵。
- Batch 帳號、pool、儲存體帳號本身的計費細節：沒讀到明文。已知費用來自 pool 節點與儲存量，預檢只讀不建，計費風險靠「命令列只有 show／exists」＋測試掃描來保證；價格頁 `https://azure.microsoft.com/pricing/details/batch/` 未讀。
- 讀取 pool 與容器所需的最小 Azure 角色名稱：沒讀到（本片用金鑰，不涉及 RBAC）。
- 低優先（low priority）VM 的退場日期：沒找到明文，所以不把它寫進計畫。

## 不做
- **不在 Azure Batch 上送出、取消、續跑任何東西**（`azure-launch`：Azure 版 bundle、`-with-tower`、本機 Nextflow 主控程序全屬它）。
- 不做費用（USD、cap、費率）、不做容器上傳、不做 work 清理、不建 pool（不做 `allowPoolCreation`／`autoPoolMode`，只收**已存在**的 pool ID）、不建 Batch 帳號或儲存體帳號或容器（營運者手動做）。
- 不支援 Entra 驗證（service principal、managed identity）、Fusion、自訂映像、虛擬網路、Azure file share；之後加不破壞資料結構。
- 不用任何 `azure-*` Python 套件；不用 `azcopy`。
- 不新增 MCP 工具、網頁路由或畫面；不改 `hello` 回傳；不改 `abf_launch/`。
- 不碰 `azcloud-platform`、K8s、EKS、GKE、AWS Cloud、Google Cloud 等其他類型，它們維持 `unsupported`。
- 不動 `gcb_preflight.py`、`aws_preflight.py`、`launch.py`、`cloud_store.py`、`clean.py`。

## 不確定的地方
1. **一定要事先有 pool，還是支援 Nextflow 的 auto-pool**：預檢是免費唯讀，只能核對「已存在的 pool」；Nextflow 的 `autoPoolMode` 會在跑時自動建 pool（官方文件範例設 true，而設定參考頁說預設 true，兩處說法不一，這次沒查清）。我的預設：`pool` 必填、只收已存在的 pool；auto-pool 留給 `azure-launch` 再議。
2. **憑證檔格式與驗證方式**：Azure 沒有標準的共用憑證檔，`azure-credentials`（INI、`[default]`、`batch_account_key`／`storage_account_key`／`storage_sas_token`）是我仿 aws 自訂的。替代：改用 service principal（`AZURE_CLIENT_ID`／`SECRET`／`TENANT_ID`），金鑰輪替較方便但設定複雜，且 user subscription 模式的 Batch 帳號只能用 Entra。我的預設：先做帳號金鑰，Entra 之後加。請裁決檔名與鍵名。
3. **`az batch pool show` 單靠環境變數能不能用**：查不到官方明文。若維護者手動驗證發現不行，替代方案是改檢查 `az batch account show`（需要訂閱層權限，不是金鑰）或每次先在暫存的 `AZURE_CONFIG_DIR` 內跑 `az batch account login --shared-key-auth`（多一次呼叫）。預設：照作法 5，手動驗證不過再改。
4. **`spot` 的鍵名**：Nextflow 用 `lowPriority`（每個 pool），我沿用 aws/gcb 的 `spot` 只存不驗。替代：改叫 `lowPriority`，貼近 Nextflow 但跟其他雲不一致。預設：`spot`。
5. **`--location` 與 `--region`**：gcb 已用 `--location`，aws 用 `--region`；Azure 的 Nextflow 鍵就叫 `location`，所以共用 `--location`。替代：另開 `--azure-location`。預設：共用。
6. **`CHECK_ONLY_TYPES` 的最終形狀取決於 aws-launch**：aws-launch 的第 4 個未決問題預設是留一個空 tuple 給 Azure/K8s。若 developer-agent 在 aws-launch 另有裁決（例如刪掉 `CHECK_ONLY_TYPES`），本任務要跟著改作法 1 與兩個測試的斷言。請在派工前確認。
7. **與進行中／排隊中任務的檔案重疊**（所以本任務 `after: aws-launch merged into v3`，且 aws-upload、aws-clean 若同車道排在前面也要先合）：
   | 檔案 | aws-launch | aws-upload | aws-clean | 本任務 |
   |---|---|---|---|---|
   | `compute_envs.py` | 改 `CHECK_ONLY_TYPES`、`snapshot` 分支 | 可能動 `snapshot` | 動 `snapshot`、`clean` | 加 `AZURE`、`_check_azure`、`snapshot`、`_VALUE_PATTERNS` |
   | `jobs.py` | 每類型允許表（取代共用閘門） | 同上 | 同上 | 在表中加 Azure 一列、拒絕訊息分句 |
   | `launch.py`／`aws_launch.py` | 新增／修改 | | | 不碰 |
   | `cloud_store.py`、`clean.py` | | 改 | 改 | 不碰 |
   | `test_aws_ce.py`、`test_gcb_ce.py`、`test_station_envs.py`、`test_station_docs.py`、`test_launch_cli.py` | 改 CHECK_ONLY 與 unsupported 例子 | | | 再改一次（見「必須更新的既有斷言」） |
   | `docs/PLATFORM.md`、`SEQERA_PARITY.md`、`TESTING.md` | 改 | | | 改 |
   不可平行；每一輪先對 `git show origin/v3:<檔>` 重新量行號。
8. **frontmatter 的 `kinds`**：交辦與既有 69 份計畫一致寫 `kinds: backend`（不加方括號）。

## 裁決


1. `pool` 必填、只收已存在的 pool；auto-pool 留給 azure-launch。
2. 只做帳號金鑰。檔名 `_personal/azure-credentials`、`[default]`、鍵名 `batch_account_key`／`storage_account_key`／`storage_sas_token` 照計畫；Entra（服務主體）之後另開。PLATFORM.md 明寫「user subscription 模式的 Batch 帳號本片不支援」。
3. 照作法 5；`az batch pool show` 單靠環境變數是否可行列為手動驗收項（需他的 Azure 帳號，屬 C 級，不在自動完成標準內）。
4. 鍵名用 `spot`，只存不驗；文件寫明對應 Nextflow 的 `lowPriority`。
5. 共用 `--location`。
6. 以 aws-launch 合併後的實際 v3 為準：aws-launch 裁決 A9 讓 `CHECK_ONLY_TYPES == ()`，本任務把 `AZURE` 放進 `CHECK_ONLY_TYPES`、`PLATFORM_HOST_TYPES` 不動。開工時用 `git show origin/v3:` 重查常數與拒絕訊息。
7. 本任務排在 L2 車道 aws-launch、aws-upload、aws-clean 之後，前一件合進 v3 才開工；行號一律用語意重新定位。
8. 開工前必讀計畫引用的 Azure CLI／Nextflow 官方頁原文（不是摘要），網址記進帳本；測試只用假 runner、假 which，絕不呼叫真的 `az`。
9. B 級，verifier 通過＋CI 綠由 developer-agent 自行合併。

10. （10-28 20:1x，aws-launch／upload／clean 都已合進 v3 @ #254 後補）上面「必須更新的既有斷言」的行號與部分內容是 aws 三件合併前寫的。開工先用 `git grep -n 'awsbatch-platform\|CHECK_ONLY_TYPES\|not built for it yet\|UNSUPPORTED' origin/v3 -- platform/tests docs` 列出所有把「哪些類型支援／只檢查／被拒」逐字釘住的既有斷言（含集合、計數、拒絕句、SEQERA_PARITY 那一列），寫進帳本。准改的只限：在這類集合／計數／文件列**加入 Azure**或把 Azure 從 unsupported 名單移出；每一條在 PR 說明寫「以前／以後／理由」。凡要刪斷言、放寬判斷、或改到 AWS／Google／Slurm 的語意，一律 BLOCKED 回報，不要自己改。（病例：aws-clean 因漏列 test_station_clean.py TC-073 被退一次。）

11. （10-28 20:2x，回應 verifier 合約審查的阻擋）範圍列擴充：除上面「範圍：檔案」外，**准改**以下既有測試，且每檔只准「加入 Azure／把 Azure 移出 unsupported／對應的計數與 'eleven'→'ten' 字樣」，不得刪改其他類型的斷言：`platform/tests/test_aws_launch.py`（約 :985 `CHECK_ONLY_TYPES == ()`、`CHECKABLE`；約 :992 那行註解「新雲端類型先放這裡，只開預檢」維持存在）、`platform/tests/test_gcb_launch.py`（約 :1151 PLATFORM.md 句子 'the other eleven types…'）、`platform/tests/test_launch_bundle.py`（約 :450 把 `azbatch-platform` 換成仍 unsupported 的類型，例如 `azcloud-platform`）、`platform/tests/test_aws_ce.py`（約 :788、:906、:923）、`platform/tests/test_gcb_ce.py`（約 :852、:866；第 163 行寫的舊值 `('awsbatch-platform',)` 作廢，以 v3 實際值 `()` 為準再加 Azure）。行號一律語意重定位。完成標準改為：`git diff --name-only` ⊆ 範圍列 ＋ 本條所列檔 ＋ ledger 依裁決 10 列出、且符合同一限制的既有測試檔；不含網頁檔。
12. `ce create --platform azbatch-platform` 不給 `--credentials`：**允許建立**，由第一次預檢報 `credential_name` fail（與 v3 現行 AWS 行為一致：`compute_envs.py` 建立時 `credentialsId` 可為空）。作法 3 的「必填」指預檢必過項，不是建立時拒絕。合約補一條測這一格。

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
