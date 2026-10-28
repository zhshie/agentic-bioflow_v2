---
id: aws-ce-type
title: AWS Batch 計算環境類型：能建立、驗證、存放（憑證只放平台主機檔案，預檢不花錢）
tier: B
kinds: backend
lane: L2-platform-ce
base: v3（@223369324548；gcb-ce-type PR #175 與 gcb-launch PR #180 都已合併。本任務從現在的 v3 開分支）
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 3 的 C-4（前半：計算環境類型）；做法完全仿 memory/dev-plans/gcb-ce-type.md 的「裁決二 F–K」（預檢由平台主機上的站台代理做）
---

# aws-ce-type

> 本檔由 developer-agent 的子 agent 起草（2026-10-28），**待 developer-agent 裁決第 1、2、3、5 點後才派工**（見文末「待裁決」）。**只處理 C-4 的第一半**：`awsbatch-platform` 這個類型可以建立、驗證、儲存、預檢。**真的在 AWS Batch 上跑 Nextflow 是下一個任務 `aws-launch`（C-2 的 AWS 版），不在本任務。** B 級（使用者看得到的新能力）→ verifier 通過＋CI 綠由 developer-agent 自合。
> 車道 L2（`compute_envs.py`、`test_station_envs.py`、`jobs.py`、`cli.py`），不可與同車道任務平行。

## 目標
讓管理者能用 `abf-platform ce create --platform awsbatch-platform --agent <平台主機上的代理> --region … --work-dir s3://… …` 登記一個 AWS Batch 環境，由**平台主機上的站台代理**檢查：設定合不合規、憑證檔讀不讀得到且形狀對、（裝了 `aws` 命令列時）憑證能不能通過身分查詢、job queue 存不存在且啟用、S3 bucket 連不連得上；結果記成 `available` 或 `invalid`。

為什麼這樣切（同 gcb，不重新發明）：①雲端用戶不裝站台代理（10-21 拷問二）——代理裝在平台主機上，由營運者跑 `abf-station run`；②AWS 憑證檔只放代理那一側的檔案，資料庫只存憑證**名字**（`credentialsId`）；③預檢全部唯讀、不建任何 Batch job、不寫 bucket，所以**不計費**；④launch 留給 `aws-launch`，所以 `available` 的 AWS 環境在那之前仍**不能被選去送出**，也不會被自動挑為主要環境。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`（行號為該檔現況）：
- 「**C-4** AWS Batch：複製 C-1／C-2（region、workDir s3://、job queue、spot；憑證走 `AWS_SHARED_CREDENTIALS_FILE`）。」（第 169 行）→ 設定鍵有 region、workDir（s3://）、job queue、spot；憑證檔由代理以環境變數 `AWS_SHARED_CREDENTIALS_FILE` 交給 `aws`，**不是**放進資料庫。
- 「10-21，他定：雲端優先於畫布；雲端用戶不裝站台代理。」→ AWS 環境沒有「使用者自己的代理」；預檢由平台主機上的那個代理做；使用者什麼都不用裝。（對照第 52 行拷問二與 `gcb-ce-type` 裁決二 F、G。）
- 「四種計算環境都建：nano4 → Google Batch … → AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（第 40 行）→ 憑證與環境分開，環境只記憑證名字。
- 「費用顯示美元、每人每月上限」（第 16 行）→ 本片不碰費用、不加任何幣別欄位（費用屬後續 AWS 版 cloud-cost）。
- 「撞牆時先砍 …… AWS／Azure」（第 20 行）→ 本片刻意小：只做建立＋預檢，不做 launch、費用、上傳、清理。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/compute_envs.py`（新常數 `AWS`、`CHECK_ONLY_TYPES`；`CHECKABLE`:36；`_AWS_*` 規則與 `_check_aws`；`clean`:448-453 的分派；`snapshot`:687 加 AWS 分支）
- `platform/abf_station/aws_preflight.py`（新；仿 `platform/abf_station/gcb_preflight.py`；函式皆可注入）
- `platform/abf_station/handlers.py`（:16 的 import、:66-71 的 gcb 預檢分支旁加 AWS 分支）
- `platform/abf_platform/jobs.py`（`_target`:95-125，只在 :110-113 旁加一個分支）
- `platform/abf_platform/cli.py`（`_config_from_args`:278-282 加 `--region`、`--job-queue` 兩旗標；`add_argument` 區 :633-638 加旗標並把 `--spot` 的說明改成「Google Batch／AWS Batch」；`cmd_ce_preflight`:419 的舊記錄補齊檢查擴及新類型）
- `platform/tests/test_aws_ce.py`（新）
- `platform/tests/test_station_envs.py`（只改「必須更新的既有斷言」列的幾處）
- `platform/tests/test_gcb_ce.py`（只改 :816 與 :849-850）
- `platform/tests/test_station_docs.py`（:78、:82）
- `platform/tests/test_launch_cli.py`（:306-308 換成仍為 unsupported 的類型）
- `docs/PLATFORM.md`（第 8 節型別表 :373 與 :364 那句、新增「AWS Batch」小節）
- `docs/SEQERA_PARITY.md`（F 節開頭 :84 那句、AWS Batch 列 :95）
- `docs/TESTING.md`（新增「AWS Batch environment (aws-ce-type)」小節，仿 :569 的 gcb 小節）
- `specs/aws-ce-type/ledger.md`（新，executor 進度帳本）

## 作法
1. **型別常數（compute_envs.py:34-36）**：`SUPPORTED`（字串 `"slurm-platform"`）與 `PLATFORM_HOST_TYPES = ("googlebatch-platform",)` **原樣保留**。理由：`PLATFORM_HOST_TYPES` 現在代表「檢查＋送出＋取消＋清理＋上傳都做好」的類型，被 `jobs.py:110`、`cloud_store.py:52`（`workdir_bucket`）、`abf_station/launch.py:541`（`GCB = PLATFORM_HOST_TYPES[0]`）、`compute_envs.snapshot`:691 依賴；把 AWS 放進去會讓 AWS 環境悄悄獲准排 `launch_nextflow`／`clean_work`／`put_upload`。新增：
   - `AWS = "awsbatch-platform"`
   - `CHECK_ONLY_TYPES = (AWS,)`：由平台主機上的代理**只做預檢**的類型（`aws-launch` 完成時，這個類型再搬進 `PLATFORM_HOST_TYPES`）。
   - `CHECKABLE = (SUPPORTED,) + PLATFORM_HOST_TYPES + CHECK_ONLY_TYPES`（:36 改這行）。
   - `create`:565 與 `update`:614 已用 `in CHECKABLE`，所以新類型自動：建立時 `creating`＋「等待第一次預檢」、舊的 `unsupported` 舊列補齊後轉 `creating`。這兩處不必改。
2. **AWS 設定鍵（`_AWS_CONFIG = _COMMON_CONFIG + (...)`，仿 :303 的 `_GCB_CONFIG`）**，欄位取自 Nextflow `aws.region`、`process.queue` 與 Seqera 的 AWS Batch 表單（只取欄位名）：
   | 鍵 | 型別／規則 | 對應 |
   |---|---|---|
   | `region` | 必填；AWS 區域，如 `eu-west-1`、`ap-northeast-1`、`us-gov-west-1`；正規式 `^[a-z]{2}(-[a-z]+)+-[0-9]\Z` | `aws.region` |
   | `workDir` | 必填；`s3://<bucket>[/<prefix>]`；bucket 名 3–63 字、小寫英數與 `-` `.`、頭尾為英數；前綴不含 `..`、控制字元；總長 ≤`MAX_PATH`；去掉結尾斜線 | `workDir` |
   | `jobQueue` | 必填；Batch job queue **名字**（不收 ARN）：`^[A-Za-z0-9_-]{1,128}\Z` | `process.queue` |
   | `spot` | 選填；布林 | 平台自訂（見待裁決 3） |
   | `maxvCpus` | 選填；整數 1–10000；**只存**，`aws-launch` 起才決定怎麼落到 Nextflow（同 gcb 裁決 6） | 平台自訂 |
   | `nextflowConfig`、`environment`、`preRunScript`、`postRunScript` | 沿用共用檢查（`_text`:151、`_check_environment`:161） | 共用 |
   - 未知鍵 → `unknown setting for an AWS Batch environment: X (known: …)`（句型同 :327）。舊記錄裡的 `headQueue`、`computeQueue` 也屬未知鍵。
   - 全部錯誤一次列出、每個點名鍵、被拒的值最多顯示 60 字（沿用 `_shown`:317）。
   - **`agent` 必填**（同 :329-331）：`agent is required: an AWS Batch environment is checked by the agent that runs on the platform host, so name it with --agent (需要指定一個站台代理，就是平台主機上的那個)`。
3. **憑證只放名字**：用既有頂層欄位 `credentialsId`（`_CRED_NAME`:58；CLI `--credentials`）。**不新增 `credentialName` 鍵**（沿 gcb-ce-type 裁決 2）。`credential_findings`:121 原樣套用：`AKIA…`／`ASIA…` 開頭的金鑰 ID、`aws_secret_access_key =` 字樣已在 `_VALUE_PATTERNS`:107-108 擋住，鍵名含 `key`／`secret`／`token` 的欄位由 `common.is_secret_name` 擋住。`region`、`jobQueue`、`workDir` 等欄位名與值不得被誤傷。
4. **憑證檔位置（在代理那一側，平台不讀）**：`aws_preflight.credentials_path(settings_file, environ=None)` ＝ 環境變數 `ABF_STATION_AWS_CREDENTIALS`，否則 `<deployment>/_personal/aws-credentials`（deployment＝`Path(settings_file).parent.parent`，寫法照 `gcb_preflight.credentials_path`:35-41）。檔案是 AWS 標準的 shared credentials 檔（INI），**每個區段是一個 profile，區段名 ＝ 環境的 `credentialsId`**（見待裁決 2）。檔案內容永遠不進 DB、日誌、任何回傳；程式只在記憶體裡解析，檢查鍵是否存在，用完即丟。
5. **預檢（`aws_preflight.py`）**——唯讀、不計費、不建任何 Batch job、不寫 bucket、不呼叫任何 `create`／`submit`／`delete`／`put`。簽名仿 `gcb_preflight.run_preflight`:108：`run_preflight(env, *, cred_path, now=time.time, runner=None, which=None, stat=os.stat) -> {"ok": bool, "checks": [{"name","status","detail"}]}`；`runner(argv, env, timeout)` 回 `(returncode, output_tail)`，預設走 `site.run_fixed`（`platform/abf_station/site.py:96`，固定 argv、無 shell），逾時 30 秒、輸出截 300 字。`_scrub`、`_check`、`_run` 直接 import 自 `gcb_preflight`（`clean.py:152`、`put_upload.py:52` 已有先例；見待裁決 5）。**不 import `boto3`／`botocore`**（`test_station_envs.py:480-484` 與 `test_gcb_ce.py:822-828` 掃描）。
   `clean_environment(ce)`：代理在組命令列前**再驗一次**（同 `gcb_preflight.clean_environment`:44），只留 `name, platform, credentialsId, region, workDir, jobQueue`，重用 `compute_envs` 的 `_AWS_REGION`／`_AWS_BUCKET`／`_AWS_QUEUE`／`_CRED_NAME`，不合規 → `rules.Refusal`。
   | 檢查名 | 做什麼 | 通過／失敗 |
   |---|---|---|
   | `credential_name` | `credentialsId` 有設 | 沒設 → fail：「給這個環境一個憑證名字（它也是憑證檔裡的 profile 名）」 |
   | `credential_file` | 檔案存在、是一般檔案；POSIX 上 `mode & 0o077 == 0`；Windows 略過權限位並明說 | 缺檔 → fail，detail 寫出**應放的路徑**與一句怎麼放（路徑不是祕密） |
   | `credential_shape` | 用 `configparser`（`interpolation=None`、檔大小 ≤1 MB）在記憶體解析；要有名為 `credentialsId` 的區段，含 `aws_access_key_id` 與 `aws_secret_access_key` 兩個**鍵**；**不看值**；區段裡有 `credential_process` → fail（`aws` 會執行該命令，不支援） | 失敗訊息只講缺哪個鍵／缺哪個區段，不印任何值、不列出檔內其他 profile 名 |
   | `aws` | `which("aws")`；沒有 → **unchecked**（不是 fail） | |
   | `identity` | `aws sts get-caller-identity --region R --query Account --output text`；rc 0 → pass，detail 是固定句「the key answered」**不印帳號 ID** | rc≠0 → fail，detail ＝ `_scrub(輸出)` 前 300 字 |
   | `job_queue` | `aws batch describe-job-queues --job-queues Q --region R --query "jobQueues[].state" --output text`；輸出為 `ENABLED` → pass；空輸出 → fail「queue 不存在於這個區域」；`DISABLED` → fail | |
   | `bucket` | `aws s3api head-bucket --bucket B --region R` | rc 0 → pass；否則 fail＋`_scrub` 後前 300 字 |
   - 憑證檔不可用（缺檔／權限太寬／形狀不對）或沒有 `aws` 時，`identity`、`job_queue`、`bucket` 為 `unchecked` 且 `runner` 一次都不呼叫。
   - 狀態規則沿用平台：任何一項不是 pass 就不是 `available`（`jobs.clean_result` 全 pass 才 ok）。**機器上沒有 `aws` 時環境停在 `invalid`，訊息明說缺 `aws`**（沿 gcb 裁決 4）。
   - **每次呼叫的環境變數**（`_aws_env(cred_path, ce)`）：從 `os.environ` 複製，**刪掉**所有 `ABF_*`、`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_SESSION_TOKEN`、`AWS_PROFILE`；再設 `AWS_SHARED_CREDENTIALS_FILE=<cred_path>`、`AWS_PROFILE=<credentialsId>`、`AWS_CONFIG_FILE=<os.devnull>`、`AWS_DEFAULT_REGION=<region>`、`AWS_PAGER=""`、`AWS_EC2_METADATA_DISABLED=true`（不准悄悄改用主機的角色或個人 `~/.aws`）。金鑰檔路徑**只在 env，不在 argv**。
   - 結果走既有紀錄路徑：`jobs` 的 preflight 工作 → `compute_envs.apply_preflight`:712，`verdict_message` 不改。
6. **代理接線（handlers.py:66-71）**：`kind == "preflight"` 且 `ce["platform"] == aws_preflight.TYPE` → `aws_preflight.run_preflight(aws_preflight.clean_environment(ce), cred_path=aws_preflight.credentials_path(ctx.settings_file))`，回 `("done", _verdict(res["checks"]))`，與 gcb 分支同形。
7. **`snapshot`（compute_envs.py:687-694）**：`v["platform"] == AWS` 時回 `{name, platform, credentialsId, region, workDir, jobQueue}`（代理的預檢需要的就這些）。其他類型的回傳一個字都不變。
8. **`jobs._target`（jobs.py:110）**：AWS 環境收到 `preflight` 以外的工作種類 → `JobRefused("%s is an AWS Batch environment: it is checked on the platform host, and launching on it is not built yet (尚未支援送出；下一步 aws-launch)")`，放在 `unsupported` 與 `no agent` 檢查**之前**（同 :110 的位置），gcb 那句不動。`put_upload` 對非 `PLATFORM_HOST_TYPES` 的拒絕（:112）不動，所以 AWS 仍被拒。
9. **送出與自動選擇不放行（不改程式，要有測試）**：`abf_launch/build.py:114-123` 的 `primary_environment` 只選 `SUPPORTED`（:117）→ AWS 永遠不被自動挑；`target_problem`:126 走 `jobs.check_target` → 作法 8 的拒絕。AWS 環境 `available` 時可以用 `ce primary` 設為主要（同 gcb），但 `launch` 一律被白話拒絕。
10. **CLI**：`ce create`／`ce update` 的第一次預檢沿用 `_queue_first_preflight`:332（`ce["platform"] in CHECKABLE` 即排工作給代理；代理離線時照舊印「沒有代理在線，尚未預檢」，不假裝）。`cmd_ce_create`:361 的 `_default_agent` 只對 `SUPPORTED` 生效（不變，與 gcb 一致：雲端環境必須明寫 `--agent`）。`cmd_ce_preflight`:419 的「舊記錄補齊檢查」條件改成 `ce["platform"] in compute_envs.PLATFORM_HOST_TYPES + compute_envs.CHECK_ONLY_TYPES`。新旗標：`--region`、`--job-queue`（對應 `region`、`jobQueue`）；`--work-dir` 與 `--spot`／`--no-spot` 既有，只改 `--spot` 的說明文字；`maxvCpus` 用 `--config-json`（同 gcb）。
11. **既有 `awsbatch-platform` 舊列**（以前一律 `unsupported`、鍵為 `region`／`headQueue`／`computeQueue` 之類）：`ce list`／`ce show` 照舊顯示、狀態維持 `unsupported`；`ce update` 與 `ce preflight` 一律先過新規則（缺鍵就說缺哪些、`headQueue`／`computeQueue` 被當未知鍵拒絕，訊息列出已知鍵）；補齊後狀態轉 `creating`（沿 gcb 裁決 C、K）。
12. **文件**：`docs/PLATFORM.md` 第 8 節表 :373 的 Supported 欄改為 `checked on the platform host (launch: not yet)`，:364 那句改成「Slurm and Google Cloud Batch can run; AWS Batch can be created and checked; the other eleven types can be modelled only」；新增「AWS Batch」小節（鍵表、檢查表、憑證檔位置與 `ABF_STATION_AWS_CREDENTIALS`、「預檢不計費：只讀，不建 Batch job」、平台主機要裝 `aws` 命令列）。`docs/SEQERA_PARITY.md`：AWS Batch 列改成 `Have (create + check); launch in aws-launch`，勾選維持 `[ ]`；F 節開頭那句加上 AWS。`docs/TESTING.md` 新增小節（維護者放憑證檔、跑 `ce create`、看到 `available`、全站搜不到金鑰片段；驗收者看 `git diff --name-only`；指向 PLATFORM.md 的「預檢不計費」那句）。範例一律用 `lab-bucket`、`eu-west-1`、`lab-queue`、`aws-lab`，不得出現真實帳號 ID。
13. **不需要 migration**：同一張 `compute_envs` 表的新 `config_json` 鍵，`status` 沿用既有五種值；舊紀錄不受影響。

## 失敗先行測試（`platform/tests/test_aws_ce.py`，現在都會紅；全部用假 `runner`、假 `which`，不碰網路；仿 `platform/tests/test_gcb_ce.py` 的 `Inproc` 夾具與 `Fake` runner）
工具常數：`REGION="eu-west-1"`、`BUCKET_URL="s3://lab-bucket/work/"`、`QUEUE="lab-queue"`、`CRED="aws-lab"`；`good_config()` ＝ `{"region":REGION,"workDir":BUCKET_URL,"jobQueue":QUEUE}`；`fields()` 帶 `agent="a1"`。金鑰字串一律用拼接組出（裁決 J，`tests/credentials_stay_in_settings_test.sh` 會掃）：`AKID = "AK" + "IA" + "ABCDEFGHIJKLMNOP"`，`CRED_FILE = "[aws-lab]\naws_access_key_id = " + AKID + "\naws_secret_access_key = MARKERSECRET0123456789abcdefghij\n"`。

建立與驗證：
- `test_a_valid_aws_batch_environment_is_created_as_creating`：`good_config()` ＋ `spot:true, maxvCpus:256` → `create` 成功、`status=="creating"`、`config["workDir"]=="s3://lab-bucket/work"`（結尾斜線去掉）、`message` 含「waiting for the first preflight」。
- `test_region_workdir_jobqueue_and_agent_are_required`：各缺一個 → 錯誤點名該鍵；缺 `agent` → 訊息含「需要指定一個站台代理」；`ce create` 不給 `--agent` 即使線上只有一個代理也被拒（與 gcb 同）。
- `test_region_rules`：`eu-west-1`、`ap-northeast-1`、`us-gov-west-1` 通過；`europe-west2`、`EU-WEST-1`、`eu-west`、`""` 被拒，訊息含 `eu-west-1` 範例。
- `test_workdir_must_be_an_s3_url`：`/data/work`、`gs://b/x`、`s3://`、`s3://UPPER/x`、`s3://ab/x`（太短）、`s3://lab-bucket/../x` 各被拒；`s3://lab-bucket/work/` → 存成 `s3://lab-bucket/work`；`s3://lab-bucket` → 存成 `s3://lab-bucket`。
- `test_job_queue_is_a_name_not_an_arn`：`lab-queue`、`Q_1` 通過；`arn:aws:batch:eu-west-1:123456789012:job-queue/q`、`a b`、129 字名字被拒。
- `test_spot_and_maxvcpus_rules`：`spot:"yes"` 被拒；`maxvCpus:0`、`10001`、`true`、`"8"` 被拒；`maxvCpus:10000` 通過。
- `test_unknown_slurm_and_gcb_keys_are_refused`：`headQueue`、`computeQueue`、`hostName`、`project`、`location`、`bootDiskSize`、`foo` 各被拒，訊息含 `unknown setting for an AWS Batch environment` 與已知鍵清單。
- `test_all_errors_are_listed_at_once_and_values_are_cut`：同時錯 `region`、`workDir`、`jobQueue` → 一則訊息含三個鍵名；一個 200 字的壞值在訊息裡 ≤ 60 字。
- `test_shared_checks_apply`：`nextflowConfig` 超過 20000 字、`environment` 項目鍵名不合規 → 與 Slurm 相同的拒絕。

憑證不進資料庫：
- `test_the_credential_is_only_a_name_at_the_top_level`：`credentialsId="aws-lab"` 存下；`ce show` 的 `credentialsId` 為 `aws-lab`；config 裡沒有任何憑證鍵。
- `test_credentials_id_is_a_name_only`：`credentialsId` 含空白、`=`、或 `AKID` 字串 → 被拒。
- `test_an_access_key_pasted_anywhere_is_refused_and_not_repeated`：把 `AKID` 放進 `description`、`nextflowConfig`、`environment` 的值、`workDir` 的前綴 → 全被拒；錯誤訊息只含欄位路徑，不含 `AKID`；DB 檔位元組比對沒有 `AKID`。
- `test_a_secret_key_line_pasted_anywhere_is_refused`：把 `"aws_secret_access_key = x"` 放進 `preRunScript` → 被拒（`_VALUE_PATTERNS`:108）。
- `test_a_key_named_field_is_refused`：config 有 `awsSecretAccessKey`、`accessKey`、`sessionToken` → 被 `credential_findings` 擋。
- `test_the_platform_does_not_read_the_credential_file`：把 `CRED_FILE` 寫在代理部署的 `_personal/` 下，建立、列出、`ce show` 之後，`platform.db` 位元組與所有 CLI 輸出都找不到 `MARKERSECRET`、`AKID`。

預檢（假 runner，`monkeypatch.setattr(aws_preflight, "_run", runner)`，`aws_preflight.shutil.which` 假裝有／沒有 `aws`）：
- `test_every_check_is_reported_with_name_status_and_detail`：七項名稱依序為 `credential_name, credential_file, credential_shape, aws, identity, job_queue, bucket`，各有 name／status／detail。
- `test_a_missing_credential_name_is_a_failure`：不設 `credentialsId` → `credential_name` 為 fail，`credential_shape` 為 unchecked。
- `test_a_missing_credential_file_says_where_to_put_it`：沒有檔 → `credential_file` fail，detail 含 `<deployment>/_personal/aws-credentials` 的實際路徑與 `chmod 600`；`credential_shape`、`identity`、`job_queue`、`bucket` 為 unchecked；環境變 `invalid`；`runner` 呼叫 0 次。
- `test_the_credential_file_location_follows_the_agents_setting`：設 `ABF_STATION_AWS_CREDENTIALS=<tmp>/x` → `credentials_path` 回該路徑；沒設 → `<settings 檔 parent.parent>/_personal/aws-credentials`。
- `test_a_credential_file_other_people_can_read_is_refused`（POSIX 專用，`skipif win32`）：mode 0644 → `credential_file` fail、detail 含 `chmod 600`；0600 → pass。
- `test_permission_bits_are_not_checked_on_windows`：`monkeypatch` 把 `aws_preflight.sys.platform` 設成 `"win32"` → pass 且 detail 含「Windows 不檢查權限位」。
- `test_a_credential_file_that_is_a_folder_is_refused`：路徑是資料夾 → fail「not a regular file」。
- `test_the_shape_of_the_file_is_judged_without_printing_it`：(a) 缺 `aws_secret_access_key` → fail，detail 含 `aws_secret_access_key`；(b) 沒有 `[aws-lab]` 區段（只有 `[default]`）→ fail，detail 含 `aws-lab`、**不含** `default`；(c) 不是 INI（隨機位元組）→ fail 且 detail 為固定句；(d) 區段含 `credential_process = /bin/x` → fail，detail 含 `credential_process`。四種情況的整份 `checks` JSON 與環境 `message` 都不含 `AKID`、`MARKERSECRET`。
- `test_without_the_aws_cli_the_api_checks_are_unchecked_and_nothing_is_run`：`which` 回 None → `aws` 為 unchecked、`identity`／`job_queue`／`bucket` 為 unchecked、環境 `invalid`、`message` 含「aws」與「沒裝」；`runner` 呼叫 0 次。
- `test_all_checks_passing_makes_the_environment_available`：假 runner 對 sts 回 `(0,"123456789012")`、對 batch 回 `(0,"ENABLED")`、對 s3api 回 `(0,"")` → 七項皆 pass、`status=="available"`、`checked_ok==1`；`identity` 的 detail **不含** `123456789012`。
- `test_a_job_queue_that_does_not_exist_or_is_disabled_fails`：batch 回 `(0,"")` → `job_queue` fail 且 detail 含 `lab-queue`；回 `(0,"DISABLED")` → fail。
- `test_an_api_failure_is_reported_trimmed_and_scrubbed`：s3api 回 `(255, 2000 字，其中夾 AKID 與一段 40 字隨機 token)` → `bucket` fail、detail ≤300 字、不含 `AKID` 也不含該 token。
- `test_a_timeout_fails_that_check_only`：sts 的假 runner 丟 `TimeoutError` → `identity` fail 且 detail 含「逾時」；`job_queue`、`bucket` 仍各自被執行。
- `test_the_commands_are_read_only`：記錄所有 argv；每條前三個字必為 `aws sts get-caller-identity`、`aws batch describe-job-queues`、`aws s3api head-bucket` 之一；沒有任何一條含 `create`、`submit`、`delete`、`put`、`cp`、`rm`、`mb`、`terminate`、`register`、`update`、`cancel` 這些字（**不花錢保證**）。
- `test_the_credential_goes_in_the_environment_not_in_argv`：每次呼叫 env 的 `AWS_SHARED_CREDENTIALS_FILE` ＝ 憑證檔路徑、`AWS_PROFILE=="aws-lab"`、`AWS_DEFAULT_REGION=="eu-west-1"`、`AWS_CONFIG_FILE` ＝ `os.devnull`、`AWS_EC2_METADATA_DISABLED=="true"`；argv 不含該路徑；env 不含任何 `ABF_` 開頭變數，且（測試先在自己的環境設 `AWS_ACCESS_KEY_ID=X`、`AWS_SECRET_ACCESS_KEY=Y`、`AWS_SESSION_TOKEN=Z`、`ABF_PLATFORM_TOKEN=T` 後）env 裡沒有那四個鍵。
- `test_the_default_runner_is_a_fixed_argv_without_a_shell`：呼叫 `aws_preflight._run(["aws","s3api","head-bucket"], {"A":"1"}, 30)` 時（`subprocess.run` 以假物件替換）收到 `shell=False`、list 型 argv、`timeout=30`。
- `test_the_agent_judges_the_environment_again_before_it_builds_a_command`：直接把 `region:"x; touch c"`、`workDir:"s3://b/x"`（太短）、`jobQueue:"q q"`、`credentialsId:"a b"` 各送進 `aws_preflight.clean_environment` → `rules.Refusal`；`platform` 為 `slurm-platform` → 同樣被拒。

接線與 CLI：
- `test_create_queues_the_first_preflight_for_the_agent`：`ce create --platform awsbatch-platform --agent a1 --credentials aws-lab --region eu-west-1 --work-dir s3://lab-bucket/work --job-queue lab-queue`（代理 `a1` 在線）→ rc 0、輸出含「preflight queued」、`jobs` 表多一列 `preflight`、其 args 的 `ce` 即 `snapshot`：鍵集合恰為 `{name, platform, credentialsId, region, workDir, jobQueue}`。
- `test_create_with_the_agent_offline_says_so_and_does_not_pretend`：代理 `last_seen` 超過離線門檻 → 訊息含「沒有代理在線」，狀態仍 `creating`，`jobs` 表沒有新列。
- `test_ce_preflight_waits_for_the_agent_and_prints_each_check`：在 `auto_serve` 夾具下 `ce preflight aws1` → 每項印 `name: status - detail`。
- `test_cli_flags`：`--region eu-west-1 --job-queue lab-queue --spot` → `ce show` 的 config 有 `region`、`jobQueue`、`spot:true`；`--no-spot` → `spot:false`。
- `test_slurm_and_google_batch_are_unchanged`：Slurm 建立後仍排 preflight；gcb 建立後仍走 `gcb_preflight`；兩者的 `snapshot` 與改動前逐鍵相同。
- `test_jobs_other_than_the_preflight_are_refused_in_plain_words`：對 `available` 的 AWS 環境 `enqueue_*` 為 `launch_nextflow`、`cancel_run`、`clean_work`、`put_upload`、`list_site_files`、`pipeline_files` → 全 `JobRefused`，訊息含「尚未支援送出」與 `aws-launch`，不含「set one with」；`jobs` 表列數不變。
- `test_launch_is_refused_and_the_environment_is_never_auto_picked`：`build.target_problem(state,"aws1","launch_nextflow")` 回非 None 的白話句；只有一個 `available` 的 AWS 環境時 `build.primary_environment` 回 None；`ce primary aws1` 成功（它是 `available`）但 `primary_environment` 仍回 None 之外的行為不變：有 `available` 的 Slurm 環境時選 Slurm。
- `test_another_users_aws_environment_is_not_found`：B 以 `owner=` 取 A 的 AWS 環境 → None；B 對它 `enqueue_preflight` → 與不存在相同的 `JobRefused` 文字。
- `test_updating_a_disabled_environment_queues_no_preflight`：`ce disable` 後 `ce update --job-queue other` → 設定改了、`jobs` 表列數不變。

舊記錄與其他類型：
- `test_an_old_aws_record_is_still_listed_and_shown`：直接 SQL 插一列 `awsbatch-platform`、`status='unsupported'`、`config_json='{"workDir":"s3://lab-bucket/work","region":"eu-west-1","headQueue":"head-q","computeQueue":"comp-q"}'` → `ce list`、`ce show` 照常；狀態仍 `unsupported`。
- `test_an_old_record_must_be_completed_before_an_update_or_a_preflight`：對該列 `ce preflight` → rc≠0，訊息含 `headQueue` 與「ce update」；`ce update --agent a1 --job-queue lab-queue` 仍因 `headQueue` 被拒；先 `--config-json '{"headQueue":null,...}'` 無法刪鍵——所以測試改為：整列重建前先確認拒絕訊息列出已知鍵，維護者需刪除重建（此行為寫入 PLATFORM.md）。
- `test_an_old_record_that_is_completed_becomes_creating`：舊列只含 `workDir`、`region`（無 headQueue/computeQueue）→ `ce update --agent a1 --credentials aws-lab --job-queue lab-queue` 成功、狀態 `creating`，並排入一個 preflight。
- `test_the_other_types_stay_unsupported`：其餘 11 個 `UNSUPPORTED` 類型仍 `create` 成功且 `unsupported`。
- `test_no_cloud_library_is_imported`：`aws_preflight.py` 無 `import boto3|botocore|azure|google|requests`；`pyproject.toml` 不含 `boto3`／`botocore`。
- `test_the_platform_package_starts_no_program`：`abf_platform/` 底下沒有 `subprocess`（`test_scope.py` TC-071 已有，本測試只確認新增的 `compute_envs.py` 改動沒破壞）。
- `test_no_launch_cost_or_upload_code_for_aws`：`abf_platform/`、`abf_station/` 的原始碼沒有 `s3 cp`、`s3 sync`、`s3 rm`、`s3api create-bucket`、`batch submit-job`、`batch create-`、`iam create-`；沒有 `-with-tower` 出現在 `aws_preflight.py`。
- `test_tool_list_unchanged_and_no_new_web_route`：MCP 工具名集合仍是現有 12 個；`web.py` 路由表不變（讀 `test_gcb_ce.py::test_tool_list_unchanged_and_no_new_web_route` 同一組）。
- `test_docs_list_every_aws_key_and_check`：`docs/PLATFORM.md` 含 `` `region` ``、`` `workDir` ``、`` `jobQueue` ``、`` `spot` ``、`` `maxvCpus` ``、七個檢查名各一個、`ABF_STATION_AWS_CREDENTIALS`、`_personal/aws-credentials`、`預檢不計費`、`creates no Batch job`；`SEQERA_PARITY.md` 的 `awsbatch-platform` 列含 `Have (create + check); launch in aws-launch` 且以 `[ ] |` 結尾；`TESTING.md` 含 `aws-ce-type`、`預檢不計費`、`git diff`；三份文件都找不到 12 位數字的 AWS 帳號 ID（`\b\d{12}\b`，`PLATFORM.md` 的範例除外：用 `123456789012` 者須在白名單）、也找不到 `AKIA`／`ASIA` 開頭字串。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
- `platform/tests/test_station_envs.py:19-32` `UNSUPPORTED`：**移除 `awsbatch-platform` 那一筆（:20）**，剩 11 種。它被 :144-153（TC-030）、:283-292（TC-096）、:464-484（TC-085）、`test_station_e2e.py:282-295`（TC-031）、`test_gcb_ce.py:812-819` 使用。
- `test_station_envs.py:145` `test_tc030_the_twelve_modelled_types_are_stored_as_not_supported` 函式名與頂部註解 :18 的「twelve／12」改「eleven／11」；斷言本身不動。
- `test_station_envs.py:163` TC-032：`{"slurm-platform", "googlebatch-platform"}` 改為 `{"slurm-platform", "googlebatch-platform", "awsbatch-platform"}`；:162 `len(KINDS)==14` 不動；:167 要求訊息列出 `awsbatch-platform`，仍成立（訊息列的是 `KINDS`），不動。
- `test_station_envs.py:287-288` TC-096：`"awsbatch-platform"` 與 `UNSUPPORTED["awsbatch-platform"]` 改用 `"azbatch-platform"` 與 `UNSUPPORTED["azbatch-platform"]`（它在測「尚未支援的環境不能當主要」，換另一個 unsupported 類型意思不變）。
- `test_station_envs.py:464-484` TC-085：迴圈自動縮成 11 種，斷言不動。注意它禁止 `pyproject.toml` 含 `boto3`／`botocore` 與原始碼 import 它們——本任務依賴 `aws` 命令列而非套件，不會撞；若 executor 想加 Python 套件，視為違規，回報 BLOCKED。
- `test_gcb_ce.py:816` `assert len(UNSUPPORTED) == 12` → `== 11`；`:849-850` TC-089：`PLATFORM_HOST_TYPES == (GCB,)` 不動，`CHECKABLE == (SUPPORTED, GCB)` 改為 `CHECKABLE == (SUPPORTED, GCB, "awsbatch-platform")`，並加一行 `assert compute_envs.CHECK_ONLY_TYPES == ("awsbatch-platform",)`。
- `platform/tests/test_station_docs.py:78`：跳過清單加 `"awsbatch-platform"`（它的列改為 `Have (create + check); launch in aws-launch`）；:82 的 `== 12` 改 `== 11`；:70 的 `## F. Compute environments (13 items)` 標題與 :39-41 的 `KINDS` 必須出現在 PLATFORM.md 的斷言不動。
- `platform/tests/test_launch_cli.py:306-307`：這個測試是「雲端類型的 launch 被拒、且沒呼叫任何雲端工具」。`awsbatch-platform` 現在需要 `--agent`，用舊的 `{"workDir":"s3://bucket/work","region":"eu-west-1"}` 會在 `ce create` 就被拒。改成 `"azbatch-platform"`、config 為 `{"workDir":"az://bucket/work","region":"westeurope"}`（Azure Batch 仍是 unsupported）；其餘斷言（rc、`refuse(...)` 的 `尚未支援|not supported`、`log` 為空）不動。
- 確認**不會**變紅、不准改：`test_station_e2e.py::test_tc031`（讀 `UNSUPPORTED`，自動縮小）、`test_launch_bundle.py:449-450`（只改 `ce_snapshot` 的 platform 字串，bundle 本來就拒非 Slurm／非 gcb 類型）、`test_station_launch.py:220`（同理）、`test_cloud_cost.py:458`（以 SQL 直接插列，不經 `clean`）、`test_estimate_su.py`、`test_web_parity.py`、`test_scope.py::test_tc070`（新檔需有檔首標頭，見「環境事實」）。**executor 在實作前先跑一次全套找出任何還沒列到的紅，列在 ledger；超出上列範圍就回報 BLOCKED，不要自己改。**

## 完成標準（done when）
- 自動：上面所有新測試綠；全套綠（在 WSL 跑 `tests/run_all.sh`）；MCP 工具數仍 12；`git diff --name-only` 只含「範圍：檔案」列出的檔。
- 手動（維護者，AWS 帳號開好後做一次，**不計費**）：在平台主機（跑 `abf-station run` 的那台）裝 AWS CLI v2，把 shared credentials 檔放到 `<agent deployment>/_personal/aws-credentials`（600），區段名 `[aws-lab]`；`abf-platform ce create --name aws1 --platform awsbatch-platform --agent <代理> --credentials aws-lab --region <區域> --job-queue <queue> --work-dir s3://<bucket>/work`，看到每項檢查，全 pass 時 `ce show aws1` 顯示 `available`；`ce show` 輸出與 `platform.db` 裡搜不到金鑰任何片段。
- 文件：`docs/PLATFORM.md`、`docs/SEQERA_PARITY.md`、`docs/TESTING.md` 依作法 12 更新。

## 環境事實
- `compute_envs.py`（origin/v3 現況）：`KINDS` 14 個識別字，`awsbatch-platform` 在 :24；`SUPPORTED`:34、`PLATFORM_HOST_TYPES`:35、`CHECKABLE`:36；`_COMMON_CONFIG`:145；`_GCB_CONFIG`:303 與 `_check_gcb`:321 是本任務的範本；`clean`:411 分派在 :448-453；`create`:563、`update`:588、`snapshot`:687、`verdict_message`:705、`apply_preflight`:712。現在 `awsbatch-platform` 走 `_check_other`:398（只有共用檢查），狀態 `unsupported`。
- `abf_station/gcb_preflight.py`（本任務的範本）：`credentials_path`:35、`clean_environment`:44、`_scrub`:66、`_run`:73、`_check`:79、`run_preflight`:108。它 import `abf_platform.compute_envs` 重用同一組正規式——AWS 版照做。
- `abf_station/handlers.py`:66-71 是 gcb 預檢分支；:72-75 是 Slurm 的路徑（`rules.clean_environment`），AWS 環境**不得**落到那裡（它會當成 Slurm 去驗）。
- `jobs.py`:110-113 是 gcb 的「只准這幾種工作」檢查；`_target` 還有 `UNSUPPORTED`:114、`DISABLED`:117、`no agent`:119、離線:122 的檢查，順序不變。
- 平台本身不啟動任何程式（憲法原則 2，`test_scope.py` TC-071）：`abf_platform/` 底下不得出現 `subprocess`。啟動 `aws` 只在 `abf_station/`，經 `site.run_fixed`（`site.py:96`）。
- 新 `.py`（含測試）前 40 行要有 `# Nothing existing: <理由，≥15 字>`（`platform/tests/test_scope.py` TC-070）。理由要具體：搜過 Nextflow `awsbatch` executor 與 Seqera 的 AWS Batch 表單，沒有離線又不計費的預檢；官方 Python 套件 `boto3` 被 TC-085 擋掉，所以用 `aws` 命令列。
- 憑證防線：`common.is_secret_name`（`common.py:24`）＋`compute_envs._VALUE_PATTERNS`:105（已含 `AKIA|ASIA` 與 `aws_secret_access_key`）；`tests/credentials_stay_in_settings_test.sh` 掃全 repo（測試與計畫不得有完整金鑰字面）。
- 相關 Nextflow 設定名（`aws.region`、`aws.batch.*`、`process.executor = 'awsbatch'`、`process.queue`）依據 `specs/007-station-agent/research.md` 與 Nextflow 文件；**本片不產生任何 Nextflow 設定**，核對屬 `aws-launch`。
- AWS 端需要的權限（預檢實際用到的三個動作）：`sts:GetCallerIdentity`、`batch:DescribeJobQueues`、`s3:ListBucket`（`head-bucket` 所需）。預檢不檢查 IAM 角色本身（無帳號無法離線檢查），由三項實際結果反映。
- 預算：預檢只做讀取，AWS 端不收費（STS／Batch Describe／S3 HEAD 不產生計費項目的算力）；S3 HEAD 請求有極小的請求費，視為零。

## 不做
- **不在 AWS Batch 上送出、取消、續跑任何東西**（`aws-launch`：AWS 版的 gcb bundle、`-with-tower`、`head.pid`、本機 Nextflow 主控程序全屬它）。
- 不做費用（USD、cap、費率檔）、不做 bucket 上傳、不做 work 清理、不做 Fargate／ECS 版本、不做 Forge 自動建 queue（只收**已存在**的 queue 名）。
- 不新增 MCP 工具、網頁路由或畫面（設定頁之後再接）；不改 `hello` 回傳。
- 不碰 Azure／K8s／AWS Cloud（`awscloud-platform`）／EKS 等其他類型，它們維持 `unsupported`。
- 不用 Python AWS 套件（`boto3`、`botocore`）；不寫建 bucket、建 queue、建 IAM 角色的程式（那是營運者手動做）。
- 不支援 IAM Identity Center／SSO／`credential_process`／角色鏈（`role_arn`、`source_profile`），只支援 shared credentials 檔裡的長期（或臨時）access key 對；之後加不破壞資料結構。
- 不改 `abf_launch/`（`primary_environment` 本來就只選 Slurm）。

## 待裁決（developer-agent；寫完上面的設計後仍無法自行確認的）
1. **常數命名與位置**：我新增 `CHECK_ONLY_TYPES = (AWS,)`，不把 AWS 放進 `PLATFORM_HOST_TYPES`（理由見作法 1：後者現在被 launch／清理／上傳程式當作「已完整支援」）。替代：把 `PLATFORM_HOST_TYPES` 拆成兩個既有名字的子集合；或 `aws-launch` 前就讓 AWS 進 `PLATFORM_HOST_TYPES` 並靠 `jobs._target` 的白名單擋。**預設：新增 `CHECK_ONLY_TYPES`。**
2. **憑證檔格式與 `credentialsId` 的意義**：我讓 `credentialsId` 同時是「資料庫裡的憑證名」與「shared credentials 檔裡的 profile 區段名」，檔案放 `<deployment>/_personal/aws-credentials`、環境變數 `ABF_STATION_AWS_CREDENTIALS`。主計畫只寫「憑證走 `AWS_SHARED_CREDENTIALS_FILE`」，沒定檔名、沒定 profile 規則。替代：不看 profile，固定用 `[default]`（一個環境一個檔）。**預設：profile ＝ `credentialsId`。** 也請確認檔名 `aws-credentials`（對照 gcb 的 `gcp-sa.json`）。
3. **`spot` 的語意**：AWS 的 spot 是 Batch **計算環境**的屬性，不是 Nextflow 的一個設定；`jobQueue` 已經決定了它。本片只存 `spot` 布林。替代：預檢多加 `spot_matches`，用 `aws batch describe-compute-environments` 核對 queue 背後是否 SPOT 類型（多一次唯讀呼叫，多一個檢查名）。**預設：只存、文件寫「`aws-launch` 起生效」；不加 `spot_matches`。**
4. **只收單一 `jobQueue`，不收 Seqera 表單的 head queue／compute queue 兩個**：因為 head 程序在平台主機上跑（與 gcb 相同），只有 compute queue 需要。既有 `UNSUPPORTED` 的 awsbatch 範例用 `headQueue`／`computeQueue`，這兩個鍵之後被當未知鍵拒絕（舊列需補齊；因 `update` 不能刪鍵，舊列要刪掉重建，見測試 `test_an_old_record_must_be_completed…`）。**預設：單一 `jobQueue`；舊列重建。** 若要容許舊鍵當別名請說。
5. **共用程式**：`aws_preflight.py` 直接 import `gcb_preflight._scrub`／`_run`／`_check`（底線開頭的私有函式，但 `clean.py:152`、`put_upload.py:52` 已這樣用）。替代：先抽一個 `abf_station/preflight_common.py`（會動 gcb 檔，擴大範圍與風險）。**預設：直接 import，不動 gcb 檔。**
6. **frontmatter 的 `kinds`**：交辦寫 `kinds: [backend]`，但 `memory/scripts/build-dev-plans.py:36-39` 用逗號切字串、既有 69 份都寫 `kinds: backend`，加方括號會被讀成 `[backend]` 一個怪 kind。我寫成 `kinds: backend`。
7. **`test_an_old_record_must_be_completed…` 那條**的寫法偏繞（`update` 無法刪除 config 鍵）。若 developer-agent 想讓 `ce update` 支援 `null` 刪鍵，那是 compute_envs 的另一個行為變更，不在本片；我的預設是不改，舊列刪掉重建。

## 裁決（2026-10-28 developer-agent，取代上面「待裁決」各條）
1. frontmatter 維持 `kinds: backend`（不加方括號，與既有計畫一致）。
2. 採 `CHECK_ONLY_TYPES` 新 tuple（fail-closed：只開預檢，不打開 launch／clean／upload 路徑）；搬進 `PLATFORM_HOST_TYPES` 留給 aws-launch。
3. 憑證檔一律讀 `[default]` profile；`credentialsId` 只是名稱標籤，不當 profile 名。環境變數 `ABF_STATION_AWS_CREDENTIALS`、預設檔 `<deployment>/_personal/aws-credentials`，與 gcb 的 `ABF_STATION_GCP_CREDENTIALS`／`gcp-sa.json` 命名對稱，照用。
4. `spot`、`maxvCpus` 只存不驗，照計畫。
5. 只留單一 `jobQueue`；舊的 `headQueue`／`computeQueue` 視為未知鍵拒絕，錯誤訊息要點名該鍵並寫「請刪除後重建這個計算環境」。不做別名。那個措辭彆扭的舊測試，改成測「舊鍵被拒且訊息教下一步」。
6. 直接 import `gcb_preflight` 的私有輔助函式，不抽共用模組（不碰 gcb 檔）。
7. Nextflow awsbatch 設定鍵名不在本任務驗證，留給 aws-launch，且 aws-launch 計畫必須先查 Nextflow 官方文件。


### 裁決補充（2026-10-28 10:10，回應 verifier 合約審查的阻擋；本文、測試清單、完成標準與裁決衝突處一律以本段為準）
8. 憑證 profile：(a) 一律讀 `[default]`，執行 Nextflow／aws 指令時明設 `AWS_PROFILE=default`（不留空，避免主機環境殘留別的 profile）；(b) 沒有 `[default]` 區段時 detail＝「憑證檔沒有 [default] 區段」＋檔案路徑，不列出檔內其他 profile 名；(c) `credentialsId` 仍是必填標籤（沒設就 fail，`credential_name` 檢查保留），只是不當 profile 名；(d) 測試常數 `CRED_FILE`、完成標準、PLATFORM.md 範例的區段名一律改成 `[default]`，測試裡的 `AWS_PROFILE=="aws-lab"` 改成 `=="default"`。
9. `spot`／`maxvCpus`：「只存不驗」＝不對 AWS 做核對（不呼叫任何 AWS API 比對）；本地型別與範圍檢查照作法 2 表格與 `test_spot_and_maxvcpus_rules` 保留（`spot` 只收布林；`maxvCpus` 只收 1～10000 的整數，布林與字串拒收）。
10. 舊 `headQueue`／`computeQueue` 記錄：錯誤訊息只需含該鍵名與「請刪除後重建這個計算環境」；刪掉作法 11 與舊測試裡的「ce update」與「整列重建前先確認…」字樣要求。
11. `primary_environment`：verifier 的解讀正確——AWS 設為主要後 `primary_environment` 仍不回傳 AWS（它是 CHECK_ONLY）；同時有 available 的 Slurm 時選 Slurm。
12. 缺憑證檔時 detail 含實際路徑：接受，是刻意例外（路徑不是祕密，使用者需要知道檔案放哪）。其他錯誤訊息仍不露內部路徑。
13. `ce create`／`update`／`disable` 沒有另外的人工確認要求，沿用既有管理者 CLI 行為即可。

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
