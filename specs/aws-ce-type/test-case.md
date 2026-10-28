# 測試案例：AWS Batch 計算環境類型（能建立、驗證、存放；預檢不花錢）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Every row can be judged without reading code.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/aws-ce-type/plan.md`（本任務沒有 spec.md，計畫即規格；「裁決補充」2026-10-28 10:10 與計畫本文衝突時以補充為準）　**總覽**：`test-case-overview.md`

名詞先講白：
- **站台代理**：裝在某台機器上、替平台去做事的小程式。AWS 的環境由「平台主機上的那一個代理」做檢查，使用者自己什麼都不用裝。
- **預檢**：建好環境後，代理去檢查「設定合不合規、憑證檔對不對、AWS 認不認這把鑰匙、queue 在不在、bucket 連不連得上」，全過才是 `available`（可用）。
- **憑證檔**：放 AWS 金鑰的檔，只放在代理那台機器上；資料庫只記一個憑證**名字**。
- **假 runner／假 which**：測試用的替身，假裝執行了 `aws` 命令、假裝有沒有裝 `aws`，不碰網路、不花錢。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」。

測試名稱欄位括號內的 `test_…` 是計畫已列的測試函式名，供 executor 對照；每個自動測試要在註解寫出它的 TC 編號。常數沿用計畫：`REGION=eu-west-1`、`BUCKET_URL=s3://lab-bucket/work/`、`QUEUE=lab-queue`、`CRED=aws-lab`。金鑰字串一律用拼接組出，不得在檔案裡寫出完整字面。

## User Story 1 — 管理者能建立一個 AWS Batch 環境，設定不合規會被當場擋下（優先度 P1）

維護者原話（plan.md 引 PLAN 第 169 行）：「**C-4** AWS Batch：複製 C-1／C-2（region、workDir s3://、job queue、spot；憑證走 `AWS_SHARED_CREDENTIALS_FILE`）。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 C-4；作法 1、2 | 功能 | 一個在線的代理 `a1`；設定為 region=eu-west-1、workDir=s3://lab-bucket/work/、jobQueue=lab-queue，另加 spot=true、maxvCpus=256 | 管理者建立 `awsbatch-platform` 環境 | 建立成功；狀態 `creating`；存下的 workDir 是 `s3://lab-bucket/work`（結尾斜線去掉）；訊息含「waiting for the first preflight」；region、jobQueue 這類欄位名與值沒有被憑證偵測誤傷 | 自動：`platform/tests/test_aws_ce.py`（`test_a_valid_aws_batch_environment_is_created_as_creating`） |
| TC-002 | 作法 2 必填 | 例外 | 同 TC-001 但缺 region | 建立 | 被拒；錯誤訊息點名 `region` | 自動：同檔（`test_region_workdir_jobqueue_and_agent_are_required`） |
| TC-003 | 作法 2 必填 | 例外 | 同 TC-001 但缺 workDir | 建立 | 被拒；訊息點名 `workDir` | 自動：同檔（同上） |
| TC-004 | 作法 2 必填 | 例外 | 同 TC-001 但缺 jobQueue | 建立 | 被拒；訊息點名 `jobQueue` | 自動：同檔（同上） |
| TC-005 | 作法 2「agent 必填」 | 例外 | 設定齊全但沒有 agent | 建立 | 被拒；訊息含「需要指定一個站台代理」 | 自動：同檔（同上） |
| TC-006 | 作法 2；作法 10；原話「雲端用戶不裝站台代理」 | 例外 | 線上剛好只有一個代理 | 用命令列 `ce create --platform awsbatch-platform` 不寫 `--agent` | 仍被拒（雲端環境必須明寫 `--agent`，不會自動挑那唯一的代理） | 自動：同檔（同上） |
| TC-007 | 作法 2 region | 功能 | 其他設定正確 | 分別用 region：`eu-west-1`、`ap-northeast-1`、`us-gov-west-1` 建立 | 三個都通過 | 自動：同檔（`test_region_rules`） |
| TC-008 | 作法 2 region | 例外 | 其他設定正確 | 分別用 region：`europe-west2`、`EU-WEST-1`、`eu-west`、空字串 | 四個都被拒；訊息含範例 `eu-west-1` | 自動：同檔（`test_region_rules`） |
| TC-009 | 作法 2 workDir | 功能 | 其他設定正確 | 分別用 workDir：`s3://lab-bucket/work/`、`s3://lab-bucket` | 分別存成 `s3://lab-bucket/work` 與 `s3://lab-bucket` | 自動：同檔（`test_workdir_must_be_an_s3_url`） |
| TC-010 | 作法 2 workDir | 例外 | 其他設定正確 | 分別用 workDir：`/data/work`、`gs://b/x`、`s3://`、`s3://UPPER/x`、`s3://ab/x`（bucket 名太短）、`s3://lab-bucket/../x` | 六個都被拒 | 自動：同檔（同上） |
| TC-011 | 作法 2 jobQueue | 功能 | 其他設定正確 | 分別用 jobQueue：`lab-queue`、`Q_1` | 兩個都通過 | 自動：同檔（`test_job_queue_is_a_name_not_an_arn`） |
| TC-012 | 作法 2 jobQueue（只收名字不收 ARN） | 例外 | 其他設定正確 | 分別用 jobQueue：一串 `arn:aws:batch:eu-west-1:` 開頭的 ARN、`a b`（含空白）、129 個字的名字 | 三個都被拒 | 自動：同檔（同上） |
| TC-013 | 作法 2 spot | 例外 | 其他設定正確 | 設 `spot` 為字串 `"yes"` | 被拒（spot 只收布林） | 自動：同檔（`test_spot_and_maxvcpus_rules`；裁決 9） |
| TC-014 | 作法 2 maxvCpus | 例外 | 其他設定正確 | 分別設 `maxvCpus` 為 0、10001 | 兩個都被拒（範圍只收 1～10000） | 自動：同檔（同上） |
| TC-015 | 作法 2 maxvCpus | 例外 | 其他設定正確 | 分別設 `maxvCpus` 為 `true`、`"8"` | 兩個都被拒（只收整數，不收布林與字串） | 自動：同檔（同上） |
| TC-016 | 作法 2 spot、maxvCpus | 功能 | 其他設定正確 | 設 `maxvCpus` 為 10000；另外設 `spot` 為 true、false 各一次 | 都通過，且原樣存下 | 自動：同檔（同上） |
| TC-017 | 作法 2 未知鍵 | 例外 | 其他設定正確 | 分別多帶 `headQueue`、`computeQueue`、`hostName`、`project`、`location`、`bootDiskSize`、`foo` | 七個都被拒；訊息含「unknown setting for an AWS Batch environment」並列出已知鍵清單 | 自動：同檔（`test_unknown_slurm_and_gcb_keys_are_refused`） |
| TC-018 | 作法 2 錯誤一次列出 | 例外 | region、workDir、jobQueue 同時填錯 | 建立 | 只出一則訊息，同時點名這三個鍵 | 自動：同檔（`test_all_errors_are_listed_at_once_and_values_are_cut`） |
| TC-019 | 作法 2 被拒的值最多顯示 60 字 | 例外 | 某欄位填一個 200 字的壞值 | 建立 | 錯誤訊息裡顯示的那個壞值不超過 60 字 | 自動：同檔（同上） |
| TC-020 | 作法 2 共用檢查 | 例外 | 其他設定正確 | 分別：`nextflowConfig` 超過 20000 字；`environment` 的某項鍵名不合規 | 兩個都被拒，拒絕方式與 Slurm 環境相同 | 自動：同檔（`test_shared_checks_apply`） |
| TC-021 | 裁決 3、9（spot／maxvCpus 只存不對 AWS 核對） | 功能 | 環境 spot=true、maxvCpus=256；預檢用假 runner 並記下每條命令 | 跑完整預檢 | 所有被執行的命令都只屬三種唯讀命令（見 TC-024）；沒有任何一條是 `describe-compute-environments` 之類拿 spot 去對 AWS 的命令；spot 與 maxvCpus 的值照存 | 自動：同檔（`test_every_check_is_reported_…` 與命令記錄） |

## User Story 2 — 憑證只是一個名字，金鑰絕不進資料庫（優先度 P1）

維護者原話：「四種計算環境都建：…… 架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（憑證與環境分開，環境只記憑證名字。）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 作法 3；原話（憑證 → 環境分開） | 功能 | 建立時帶 `credentialsId=aws-lab` | 建立後 `ce show` | 頂層 `credentialsId` 顯示 `aws-lab`；設定（config）裡沒有任何憑證相關的鍵 | 自動：同檔（`test_the_credential_is_only_a_name_at_the_top_level`） |
| TC-023 | 作法 3 | 例外 | 其他設定正確 | 分別用 credentialsId：含空白、含 `=`、貼進一整串 AWS 金鑰 ID | 三個都被拒（它只能是名字） | 自動：同檔（`test_credentials_id_is_a_name_only`） |
| TC-024 | 作法 3；Safety Net 憑證條 | 例外 | 其他設定正確 | 把一把 AWS 金鑰 ID（用拼接組出）分別放進 `description`、`nextflowConfig`、`environment` 的某個值、`workDir` 的前綴 | 四處都被拒 | 自動：同檔（`test_an_access_key_pasted_anywhere_is_refused_and_not_repeated`） |
| TC-025 | 作法 3；專長守則（密鑰不得出現在回應） | 例外 | 同 TC-024 的四種貼法 | 看錯誤訊息，並逐位元組檢查資料庫檔 | 錯誤訊息只講欄位位置、不重複那把金鑰；資料庫檔裡找不到它 | 自動：同檔（同上） |
| TC-026 | 作法 3 | 例外 | 其他設定正確 | 在 `preRunScript` 放一行 `aws_secret_access_key = x` | 被拒 | 自動：同檔（`test_a_secret_key_line_pasted_anywhere_is_refused`） |
| TC-027 | 作法 3 | 例外 | 其他設定正確 | 設定裡加 `awsSecretAccessKey`、`accessKey`、`sessionToken`（各一次） | 三個都被憑證偵測擋下 | 自動：同檔（`test_a_key_named_field_is_refused`） |
| TC-028 | 作法 4（平台不讀憑證檔） | 功能 | 憑證檔（含金鑰 ID 與 `MARKERSECRET…` 字串）寫在代理部署的 `_personal/` 下 | 建立、列出、`ce show` | `platform.db` 位元組與所有命令列輸出都找不到 `MARKERSECRET`，也找不到那把金鑰 ID | 自動：同檔（`test_the_platform_does_not_read_the_credential_file`） |

## User Story 3 — 預檢：代理唯讀地檢查，全過才可用，而且不花錢（優先度 P1）

維護者原話：「10-21，他定：雲端優先於畫布；雲端用戶不裝站台代理。」（預檢由平台主機上的那個代理做；使用者什麼都不用裝。）以下憑證區段一律依裁決補充 8：固定讀 `[default]`，`AWS_PROFILE=default`，`credentialsId` 只是必填的名字標籤。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 作法 5 檢查表 | 功能 | 假 runner、假 which | 跑一次預檢 | 回報七項，依序為 `credential_name, credential_file, credential_shape, aws, identity, job_queue, bucket`；每項都有 name、status、detail | 自動：同檔（`test_every_check_is_reported_with_name_status_and_detail`） |
| TC-030 | 作法 5 credential_name；裁決 8(c) | 例外 | 環境沒設 `credentialsId` | 跑預檢 | `credential_name` 為 fail；`credential_shape` 為 unchecked；訊息不再說「它也是 profile 名」 | 自動：同檔（`test_a_missing_credential_name_is_a_failure`） |
| TC-031 | 作法 5 credential_file；裁決 12 | 例外 | 憑證檔不存在 | 跑預檢 | `credential_file` 為 fail；detail 寫出實際應放的路徑（`<deployment>/_personal/aws-credentials`）與 `chmod 600` | 自動：同檔（`test_a_missing_credential_file_says_where_to_put_it`） |
| TC-032 | 作法 5「憑證不可用時…runner 一次都不呼叫」 | 例外 | 憑證檔不存在 | 跑預檢 | `credential_shape`、`identity`、`job_queue`、`bucket` 都是 unchecked；環境狀態 `invalid`；假 runner 被呼叫 0 次 | 自動：同檔（同上） |
| TC-033 | 作法 4 | 功能 | 設 `ABF_STATION_AWS_CREDENTIALS=<tmp>/x`；另一次不設 | 取憑證檔路徑 | 有設時回該路徑；沒設時回 `<settings 檔 parent.parent>/_personal/aws-credentials` | 自動：同檔（`test_the_credential_file_location_follows_the_agents_setting`） |
| TC-034 | 作法 5 credential_file（POSIX） | 例外 | POSIX 系統；憑證檔權限 0644（別人讀得到） | 跑預檢 | `credential_file` 為 fail；detail 含 `chmod 600` | 自動：同檔（`test_a_credential_file_other_people_can_read_is_refused`，Windows 跳過） |
| TC-035 | 作法 5 credential_file（POSIX） | 功能 | POSIX 系統；憑證檔權限 0600 | 跑預檢 | `credential_file` 為 pass | 自動：同檔（同上） |
| TC-036 | 作法 5 credential_file（Windows） | 功能 | 把平台判斷設成 win32 | 跑預檢 | `credential_file` 為 pass；detail 含「Windows 不檢查權限位」 | 自動：同檔（`test_permission_bits_are_not_checked_on_windows`） |
| TC-037 | 作法 5 | 例外 | 憑證檔路徑其實是一個資料夾 | 跑預檢 | `credential_file` 為 fail，訊息說不是一般檔案（not a regular file） | 自動：同檔（`test_a_credential_file_that_is_a_folder_is_refused`） |
| TC-038 | 裁決 8(b) | 例外 | 憑證檔只有別的區段（例如 `[other]`），沒有 `[default]` | 跑預檢 | `credential_shape` 為 fail；detail 為「憑證檔沒有 [default] 區段」加檔案路徑；detail **不含**檔內其他區段名 | 自動：同檔（`test_the_shape_of_the_file_is_judged_without_printing_it` (b)） |
| TC-039 | 作法 5 credential_shape | 例外 | `[default]` 區段缺 `aws_secret_access_key`（只有 ID） | 跑預檢 | `credential_shape` 為 fail；detail 說缺 `aws_secret_access_key` | 自動：同檔（同上 (a)） |
| TC-040 | 作法 5 credential_shape | 例外 | 憑證檔是隨機位元組，不是 INI | 跑預檢 | `credential_shape` 為 fail；detail 是固定的一句話，不夾檔案內容 | 自動：同檔（同上 (c)） |
| TC-041 | 作法 5「credential_process 不支援」 | 例外 | `[default]` 區段含 `credential_process = /bin/x` | 跑預檢 | `credential_shape` 為 fail；detail 點名 `credential_process` | 自動：同檔（同上 (d)） |
| TC-042 | 作法 5「檔大小 ≤1 MB」 | 例外 | 憑證檔大於 1 MB | 跑預檢 | `credential_shape` 為 fail，不解析該檔 | 自動：同檔（新增一條） |
| TC-043 | 作法 4、5；專長守則（密鑰不得出現在回應） | 例外 | TC-038～TC-041 四種壞檔 | 看整份 `checks` 的內容與環境的 `message` | 兩者都找不到金鑰 ID、`MARKERSECRET`，也不列出檔內其他區段名 | 自動：同檔（同上） |
| TC-044 | 作法 5 aws；裁決 4（gcb）沿用 | 例外 | 假 which 回「沒有 aws」；憑證檔正常 | 跑預檢 | `aws` 為 unchecked（不是 fail）；`identity`、`job_queue`、`bucket` 為 unchecked；環境 `invalid`；訊息明說「aws」「沒裝」；假 runner 呼叫 0 次 | 自動：同檔（`test_without_the_aws_cli_the_api_checks_are_unchecked_and_nothing_is_run`） |
| TC-045 | 作法 5 狀態規則 | 功能 | 憑證檔正常；假 runner：身分查詢回 `(0,"123456789012")`、queue 回 `(0,"ENABLED")`、bucket 回 `(0,"")` | 跑預檢並記錄結果 | 七項全 pass；環境狀態 `available`；`checked_ok` 為 1 | 自動：同檔（`test_all_checks_passing_makes_the_environment_available`） |
| TC-046 | 作法 5 identity | 功能 | 同 TC-045 | 看 `identity` 的 detail | 不含 `123456789012`（帳號 ID 不印），detail 是固定句「the key answered」 | 自動：同檔（同上） |
| TC-047 | 作法 5 identity | 例外 | 假 runner 對身分查詢回非 0 | 跑預檢 | `identity` 為 fail；detail 是清除過敏感字的輸出前 300 字；環境不是 `available` | 自動：同檔（新增一條，仿 TC-050） |
| TC-048 | 作法 5 job_queue | 例外 | 假 runner 對 queue 查詢回 `(0,"")`（空輸出） | 跑預檢 | `job_queue` 為 fail；detail 含 `lab-queue`（說 queue 不存在於這個區域） | 自動：同檔（`test_a_job_queue_that_does_not_exist_or_is_disabled_fails`） |
| TC-049 | 作法 5 job_queue | 例外 | 假 runner 對 queue 查詢回 `(0,"DISABLED")` | 跑預檢 | `job_queue` 為 fail | 自動：同檔（同上） |
| TC-050 | 作法 5 bucket；專長守則 | 例外 | 假 runner 對 bucket 檢查回 `(255, 2000 字輸出，夾一把金鑰 ID 與一段 40 字隨機 token)` | 跑預檢 | `bucket` 為 fail；detail 不超過 300 字；不含那把金鑰 ID，也不含那段 token | 自動：同檔（`test_an_api_failure_is_reported_trimmed_and_scrubbed`） |
| TC-051 | 作法 5「逾時 30 秒」 | 例外 | 假 runner 讓身分查詢丟出逾時 | 跑預檢 | 只有 `identity` 為 fail，detail 含「逾時」；`job_queue`、`bucket` 仍各自被執行 | 自動：同檔（`test_a_timeout_fails_that_check_only`） |
| TC-052 | 作法 5「唯讀、不計費」 | 功能 | 記錄預檢送出的所有命令 | 跑完整預檢 | 每條命令的前三個字都是 `aws sts get-caller-identity`、`aws batch describe-job-queues`、`aws s3api head-bucket` 三者之一 | 自動：同檔（`test_the_commands_are_read_only`） |
| TC-053 | 作法 5「不花錢保證」 | 功能 | 同 TC-052 | 檢查所有命令的每個參數 | 沒有任何參數（以整個字詞比對，含以此為開頭的子命令）是 create、submit、delete、put、cp、rm、mb、terminate、register、update、cancel；`--output` 這種參數不算誤報 | 自動：同檔（同上） |
| TC-054 | 原話 C-4（憑證走 `AWS_SHARED_CREDENTIALS_FILE`）；作法 5 環境變數；裁決 8(a) | 功能 | 記錄每次呼叫收到的環境變數 | 跑完整預檢 | 每次都有：`AWS_SHARED_CREDENTIALS_FILE`＝憑證檔路徑、`AWS_PROFILE`＝`default`、`AWS_DEFAULT_REGION`＝`eu-west-1`、`AWS_CONFIG_FILE`＝系統的空裝置、`AWS_EC2_METADATA_DISABLED`＝`true` | 自動：同檔（`test_the_credential_goes_in_the_environment_not_in_argv`） |
| TC-055 | 作法 5「路徑只在環境、不在 argv」 | 功能 | 同 TC-054 | 檢查每條命令的參數 | 任何參數都不含憑證檔路徑 | 自動：同檔（同上） |
| TC-056 | 作法 5「不准悄悄改用主機的角色或個人 ~/.aws」 | 功能 | 測試先在自己的環境設 `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_SESSION_TOKEN`、`ABF_PLATFORM_TOKEN` | 跑完整預檢 | 傳給 `aws` 的環境裡沒有這四個，也沒有任何 `ABF_` 開頭的變數 | 自動：同檔（同上） |
| TC-057 | 作法 5 預設 runner | 功能 | 把 `subprocess.run` 換成替身 | 呼叫預設 runner：`["aws","s3api","head-bucket"]`、逾時 30 | 替身收到 `shell=False`、list 型參數、`timeout=30` | 自動：同檔（`test_the_default_runner_is_a_fixed_argv_without_a_shell`） |
| TC-058 | 作法 5 clean_environment（代理再驗一次） | 例外 | 直接把壞值送進代理端的 `clean_environment` | 分別送：region=`x; touch c`、workDir=`s3://b/x`（太短）、jobQueue=`q q`、credentialsId=`a b` | 四個都被拒（Refusal） | 自動：同檔（`test_the_agent_judges_the_environment_again_before_it_builds_a_command`） |
| TC-059 | 作法 5 clean_environment | 例外 | 送進 `platform` 為 `slurm-platform` 的環境 | 呼叫 `clean_environment` | 被拒（AWS 預檢不接別的類型） | 自動：同檔（同上） |
| TC-060 | 作法 5 clean_environment、作法 7 | 功能 | 一個合規、還帶有 spot、maxvCpus、nextflowConfig 的 AWS 環境 | 呼叫 `clean_environment` | 只留 `name, platform, credentialsId, region, workDir, jobQueue` 六個鍵 | 自動：同檔（新增一條） |
| TC-061 | 計畫「完成標準：手動」 | 功能 | 維護者的 AWS 帳號已開；平台主機已裝 AWS CLI v2；憑證檔放 `<agent deployment>/_personal/aws-credentials`（權限 600，區段 `[default]`） | `abf-platform ce create --name aws1 --platform awsbatch-platform --agent <代理> --credentials aws-lab --region <區域> --job-queue <queue> --work-dir s3://<bucket>/work` | 看到每一項檢查結果；全 pass 時 `ce show aws1` 顯示 `available`；`ce show` 輸出與 `platform.db` 裡搜不到金鑰任何片段；AWS 帳單沒有新項目 | 手動：`docs/TESTING.md`「AWS Batch environment (aws-ce-type)」 |

## User Story 4 — 接上代理與命令列；`available` 之後仍不能送出、不會被自動挑走（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-062 | 作法 6、10 | 功能 | 代理 `a1` 在線 | `ce create --platform awsbatch-platform --agent a1 --credentials aws-lab --region eu-west-1 --work-dir s3://lab-bucket/work --job-queue lab-queue` | 回傳碼 0；輸出含「preflight queued」；工作表多一列 `preflight` | 自動：同檔（`test_create_queues_the_first_preflight_for_the_agent`） |
| TC-063 | 作法 7 snapshot | 功能 | 同 TC-062 | 看那一列工作的 `ce` 參數 | 鍵集合恰為 `{name, platform, credentialsId, region, workDir, jobQueue}`，沒有別的 | 自動：同檔（同上） |
| TC-064 | 作法 10（代理離線不假裝） | 例外 | 代理 `last_seen` 超過離線門檻 | 建立 AWS 環境 | 訊息含「沒有代理在線」；狀態仍 `creating`；工作表沒有新增列 | 自動：同檔（`test_create_with_the_agent_offline_says_so_and_does_not_pretend`） |
| TC-065 | 作法 6；環境事實（AWS 不得落到 Slurm 路徑） | 功能 | 自動服務的代理夾具；一個 AWS 環境 `aws1` | `ce preflight aws1` | 逐項印出 `name: status - detail`，名稱是上述七個 AWS 檢查名（不是 Slurm 的檢查名） | 自動：同檔（`test_ce_preflight_waits_for_the_agent_and_prints_each_check`） |
| TC-066 | 作法 10 旗標 | 功能 | 無 | 建立時帶 `--region eu-west-1 --job-queue lab-queue --spot` | `ce show` 的設定有 region、jobQueue、`spot:true` | 自動：同檔（`test_cli_flags`） |
| TC-067 | 作法 10 旗標 | 功能 | 無 | 建立時帶 `--no-spot` | `ce show` 的 `spot` 為 false | 自動：同檔（同上） |
| TC-068 | 作法 10（說明文字） | 功能 | 無 | 看 `ce create` 的說明 | `--spot` 的說明寫「Google Batch／AWS Batch」 | 自動：同檔（新增一條） |
| TC-069 | 作法 1（其他類型不變） | 功能 | 建立一個 Slurm 環境 | 建立並看工作表與 snapshot | 仍排入 preflight；snapshot 與改動前逐鍵相同 | 自動：同檔（`test_slurm_and_google_batch_are_unchanged`） |
| TC-070 | 作法 1（其他類型不變） | 功能 | 建立一個 Google Batch 環境 | 建立並看預檢走向與 snapshot | 仍走 `gcb_preflight`；snapshot 與改動前逐鍵相同 | 自動：同檔（同上） |
| TC-071 | 作法 1、裁決 2（fail-closed） | 功能 | 無 | 讀常數 | `SUPPORTED` 仍是 `slurm-platform`；`PLATFORM_HOST_TYPES == ("googlebatch-platform",)`；`CHECK_ONLY_TYPES == ("awsbatch-platform",)`；`CHECKABLE == (SUPPORTED, GCB, "awsbatch-platform")` | 自動：`platform/tests/test_gcb_ce.py`（TC-089 更新後） |
| TC-072 | 作法 8；原話「撞牆時先砍…… AWS」（本片只做建立＋預檢） | 例外 | 一個 `available` 的 AWS 環境、代理在線 | 對它分別排：`launch_nextflow`、`cancel_run`、`clean_work`、`put_upload`、`list_site_files`、`pipeline_files` | 六個都被拒；訊息含「尚未支援送出」與 `aws-launch`；不含「set one with」 | 自動：同檔（`test_jobs_other_than_the_preflight_are_refused_in_plain_words`） |
| TC-073 | 作法 8 | 例外 | 同 TC-072 | 看工作表列數 | 被拒之後列數不變（什麼都沒排進去） | 自動：同檔（同上） |
| TC-074 | 作法 9 | 例外 | 同 TC-072 | `build.target_problem(state,"aws1","launch_nextflow")` | 回非空的白話句（送出被拒） | 自動：同檔（`test_launch_is_refused_and_the_environment_is_never_auto_picked`） |
| TC-075 | 作法 9 | 例外 | 只有一個 `available` 的 AWS 環境 | 自動挑主要環境 | `primary_environment` 回「沒有」（不會挑 AWS） | 自動：同檔（同上） |
| TC-076 | 作法 9；裁決 11 | 功能 | `available` 的 AWS 環境 `aws1` | `ce primary aws1` | 成功（可設為主要），但 `primary_environment` 仍不回傳 AWS | 自動：同檔（同上） |
| TC-077 | 裁決 11 | 功能 | 同時有 `available` 的 Slurm 與 AWS 環境 | 自動挑主要環境 | 選到 Slurm 環境 | 自動：同檔（同上） |
| TC-078 | 專長守則（跨使用者，讀） | 例外 | 使用者 A 有一個 AWS 環境；使用者 B 登入 | B 以自己的身分查看、取得 A 的 AWS 環境 | 找不到（與環境不存在時相同） | 自動：同檔（`test_another_users_aws_environment_is_not_found`） |
| TC-079 | 專長守則（跨使用者，寫） | 例外 | 同 TC-078 | B 對 A 的 AWS 環境排 `preflight` | 被拒，文字與環境不存在時一模一樣；工作表沒有新增列 | 自動：同檔（同上） |
| TC-080 | 專長守則（跨使用者，寫） | 例外 | 同 TC-078 | B 嘗試修改、停用 A 的 AWS 環境（`ce update`、`ce disable`） | 兩者都被拒，與不存在相同；A 的環境設定與狀態完全沒變 | 自動：同檔（新增一條；計畫原清單缺此條） |
| TC-081 | 作法 10 | 例外 | 一個已停用（`ce disable`）的 AWS 環境 | `ce update --job-queue other` | 設定改了，但工作表列數不變（停用中不排預檢） | 自動：同檔（`test_updating_a_disabled_environment_queues_no_preflight`） |

## User Story 5 — 以前就存在的 `awsbatch-platform` 舊記錄（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-082 | 作法 11 | 功能 | 資料庫直接插一列舊記錄：`awsbatch-platform`、`unsupported`、設定含 workDir、region、`headQueue`、`computeQueue` | `ce list`、`ce show` | 照常顯示；狀態仍 `unsupported` | 自動：同檔（`test_an_old_aws_record_is_still_listed_and_shown`） |
| TC-083 | 作法 11；裁決 5、10 | 例外 | 同 TC-082 | `ce preflight` 該環境 | 回傳碼不為 0；訊息點名 `headQueue` 並含「請刪除後重建這個計算環境」 | 自動：同檔（`test_an_old_record_must_be_completed_before_an_update_or_a_preflight`，依裁決 10 改寫） |
| TC-084 | 裁決 5、10 | 例外 | 同 TC-082 | 對該環境預檢／更新時，訊息針對 `computeQueue` | 訊息點名 `computeQueue` 並含「請刪除後重建這個計算環境」 | 自動：同檔（同上） |
| TC-085 | 作法 11 | 例外 | 同 TC-082 | `ce update --agent a1 --job-queue lab-queue` | 仍因舊鍵被拒（update 不能刪鍵）；訊息點名舊鍵並教下一步（刪除後重建）；環境內容沒被改 | 自動：同檔（同上） |
| TC-086 | 作法 11 | 功能 | 舊記錄只含 workDir、region（沒有 headQueue／computeQueue） | `ce update --agent a1 --credentials aws-lab --job-queue lab-queue` | 成功；狀態轉為 `creating`；排入一個 preflight | 自動：同檔（`test_an_old_record_that_is_completed_becomes_creating`） |

## User Story 6 — 文件寫清楚（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-087 | 作法 12 | 功能 | 無 | 讀 `docs/PLATFORM.md` | 含 `` `region` ``、`` `workDir` ``、`` `jobQueue` ``、`` `spot` ``、`` `maxvCpus` ``、七個檢查名各一個、`ABF_STATION_AWS_CREDENTIALS`、`_personal/aws-credentials`、`預檢不計費`、`creates no Batch job` | 自動：同檔（`test_docs_list_every_aws_key_and_check`） |
| TC-088 | 作法 12 | 功能 | 無 | 讀 `docs/PLATFORM.md` 第 8 節 | 型別表 AWS Batch 的 Supported 欄是 `checked on the platform host (launch: not yet)`；那句改成「Slurm and Google Cloud Batch can run; AWS Batch can be created and checked; the other eleven types can be modelled only」 | 自動：同檔（新增斷言） |
| TC-089 | 裁決 8(d) | 功能 | 無 | 讀 `docs/PLATFORM.md` 的 AWS Batch 小節與憑證檔範例 | 範例區段名是 `[default]`；沒有說 `credentialsId` 是 profile 名 | 自動：同檔（新增斷言） |
| TC-090 | 裁決 5 | 功能 | 無 | 讀 `docs/PLATFORM.md` | 說明舊的 `headQueue`／`computeQueue` 記錄要刪除後重建 | 自動：同檔（新增斷言） |
| TC-091 | 作法 12 | 功能 | 無 | 讀 `docs/SEQERA_PARITY.md` | `awsbatch-platform` 那一列含 `Have (create + check); launch in aws-launch`，且以 `[ ] |` 結尾（勾選維持未勾）；F 節開頭那句加上 AWS | 自動：同檔（同上） |
| TC-092 | 作法 12 | 功能 | 無 | 讀 `docs/TESTING.md` | 含 `aws-ce-type`、`預檢不計費`、`git diff`（維護者放憑證檔、建環境、看到 available；驗收者看 `git diff --name-only`） | 自動：同檔（同上） |
| TC-093 | 作法 12；既有文件守門 | 功能 | 無 | 跑 `platform/tests/test_station_docs.py`（跳過清單加 `awsbatch-platform`、`== 11`） | 通過；標題 `## F. Compute environments (13 items)` 與 `KINDS` 必須出現在 PLATFORM.md 的斷言仍在且過 | 自動：`platform/tests/test_station_docs.py` |
| TC-094 | 作法 12（範例不得露真實帳號） | 例外 | 無 | 掃三份文件 | 找不到 12 位數字的帳號 ID（`PLATFORM.md` 白名單內的範例除外）；找不到 `AKIA`／`ASIA` 開頭的金鑰字串；範例只用 `lab-bucket`、`eu-west-1`、`lab-queue`、`aws-lab` | 自動：同檔（`test_docs_list_every_aws_key_and_check`） |

## User Story 7 — 計畫明講這次不做的事（優先度 P2）

維護者原話：「撞牆時先砍 …… AWS／Azure」→ 本片刻意小：只做建立＋預檢，不做 launch、費用、上傳、清理。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-095 | 不做第 1 條（不送出、不取消、不續跑） | 不在範圍 | 無 | 掃 `abf_platform/`、`abf_station/` 原始碼 | 沒有 `batch submit-job`；`aws_preflight.py` 沒有 `-with-tower`；AWS 環境的送出被明白拒絕（見 TC-072） | 自動：同檔（`test_no_launch_cost_or_upload_code_for_aws`） |
| TC-096 | 不做第 2 條；原話「費用顯示美元、每人每月上限」（本片不碰） | 不在範圍 | 無 | 建立時多帶 `currency`、`costCap` 之類鍵 | 被當作未知鍵拒絕；沒有任何幣別／費用欄位或費率程式被加入 | 自動：同檔（新增一條，併入 `test_unknown_slurm_and_gcb_keys_are_refused`） |
| TC-097 | 不做第 2 條（不做上傳、清理） | 不在範圍 | 無 | 掃原始碼 | 沒有 `s3 cp`、`s3 sync`、`s3 rm`；AWS 環境的 `put_upload`／`clean_work` 被拒（見 TC-072） | 自動：同檔（`test_no_launch_cost_or_upload_code_for_aws`） |
| TC-098 | 不做第 2、5 條（不建資源；不做 Fargate／ECS／Forge；只收已存在的 queue 名） | 不在範圍 | 無 | 掃原始碼；建立時多帶 `fargate`、`forge` 鍵 | 沒有 `s3api create-bucket`、`batch create-`、`iam create-`；兩個鍵被當未知鍵拒絕 | 自動：同檔（同上） |
| TC-099 | 不做第 3 條（不新增 MCP 工具、網頁路由；不改 hello） | 不在範圍 | 無 | 列出 MCP 工具名與網頁路由表、讀 `hello` 回傳 | 工具名仍是現有 12 個；路由表不變；`hello` 不變 | 自動：同檔（`test_tool_list_unchanged_and_no_new_web_route`） |
| TC-100 | 不做第 4 條（其他類型維持不支援） | 不在範圍 | 無 | 對其餘 11 種 `UNSUPPORTED` 類型（含 `awscloud-platform`、`eks-platform`、`azbatch-platform`）各建立一次 | 都建立成功且狀態是 `unsupported`；訊息仍說尚未支援 | 自動：同檔（`test_the_other_types_stay_unsupported`） |
| TC-101 | 不做第 5 條（不用 boto3／botocore） | 不在範圍 | 無 | 掃 `aws_preflight.py` 與 `pyproject.toml` | 沒有 `import boto3`、`botocore`、`azure`、`google`、`requests`；`pyproject.toml` 沒有 `boto3`／`botocore` | 自動：同檔（`test_no_cloud_library_is_imported`） |
| TC-102 | 不做第 6 條（不支援 SSO／credential_process／角色鏈） | 不在範圍 | 無 | 檢查預檢送出的所有命令與環境 | 沒有 `aws sso`、`sts assume-role`、`--profile`；`credential_process` 被明白拒絕（見 TC-041） | 自動：同檔（新增一條，併入命令記錄） |
| TC-103 | 不做第 7 條（不改 `abf_launch/`；範圍：檔案「只准改這些」） | 不在範圍 | 無 | 驗收者看 `git diff --name-only` | 只出現計畫「範圍：檔案」列的檔；`abf_launch/` 與 `gcb_preflight.py` 沒被改 | 手動：`docs/TESTING.md`「AWS Batch environment (aws-ce-type)」 |
| TC-104 | 「必須更新的既有斷言」（其他一律不准動） | 不在範圍 | 無 | 驗收者逐檔比對既有測試與 base | 被改的既有斷言僅限計畫列出的幾處（UNSUPPORTED 剩 11 種、TC-032 集合、TC-096 換 azbatch、TC-089 常數、test_station_docs 的 11、test_launch_cli 換 azbatch）；沒有刪除或放寬其他斷言 | 手動：`docs/TESTING.md`「AWS Batch environment (aws-ce-type)」（git diff 步驟） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-105 | 原則 2／平台不啟動任何程式（`test_scope.py` TC-071）；環境事實 | 功能 | 無 | 掃 `abf_platform/` | 底下沒有 `subprocess`；啟動 `aws` 只發生在 `abf_station/`，經固定參數、無 shell 的 `site.run_fixed` | 自動：`platform/tests/test_scope.py`（TC-071）與 `platform/tests/test_aws_ce.py`（`test_the_platform_package_starts_no_program`） |
| TC-106 | Safety Net 憑證條 | 功能 | 無 | 跑 `tests/credentials_stay_in_settings_test.sh` | 通過：新增的測試與文件沒有完整金鑰字面 | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-107 | Safety Net 憑證條的平台半（`test_secrets.py`） | 功能 | 無 | 跑 `platform/tests/test_secrets.py` | 通過：新類型沒有開出讓憑證存進平台的路徑 | 自動：`platform/tests/test_secrets.py` |
| TC-108 | `test_scope.py` TC-070（新檔標頭） | 功能 | 無 | 看新增的 `aws_preflight.py` 與 `test_aws_ce.py` 前 40 行 | 各有 `# Nothing existing: <具體理由，≥15 字>` | 自動：`platform/tests/test_scope.py`（TC-070） |
| TC-109 | 專長守則（對等性） | 功能 | 無 | 同時列舉使用者看得到的動作（命令列 `ce` 子命令、MCP 工具、網頁路由）與動作層函式，兩邊比對 | 兩邊一一對應；AWS 沒有新增只在其中一邊存在的動作；`cli.py` 沒有自己的第二份驗證邏輯（驗證在 `compute_envs`） | 自動：`platform/tests/test_actions_layer.py`、`platform/tests/test_web_parity.py` |
| TC-110 | 專長守則（確認管道）；裁決 13 | 功能 | 無 | 檢查 AWS 帶來的寫入路徑 | 沒有新的寫入入口：`ce create／update／disable` 沿用既有管理者命令列；所有會真的動 AWS 的工作種類都被拒（TC-072）；MCP 工具與網頁路由數量不變（TC-099） | 自動：`platform/tests/test_aws_ce.py` |
| TC-111 | 專長守則（錯誤訊息要有原因與處理方式） | 例外 | 無 | 逐一引發：缺 agent、缺憑證檔、沒裝 `aws`、非預檢工作被拒、舊鍵被拒 | 每則訊息都講發生什麼事，也講下一步該做什麼（指定 `--agent`／放檔到路徑並 `chmod 600`／裝 aws／等 aws-launch／刪除後重建） | 自動：`platform/tests/test_aws_ce.py` |
| TC-112 | 專長守則（不露堆疊、內部路徑、SQL）；裁決 12 | 例外 | 無 | 看上列所有錯誤與預檢回報 | 沒有堆疊、SQL；沒有內部路徑——唯一例外是「缺憑證檔」那一則可寫出應放檔案的路徑 | 自動：`platform/tests/test_aws_ce.py` |
| TC-113 | 專長守則（日誌與回應不含密鑰） | 例外 | 憑證檔含金鑰 ID 與 `MARKERSECRET…`；跑完建立、預檢成功、預檢失敗各一次 | 逐位元組搜尋資料庫、工作表（含 args、結果）、所有命令列輸出與日誌 | 找不到金鑰 ID、`MARKERSECRET…`，也找不到帳號 ID | 自動：`platform/tests/test_aws_ce.py` |
| TC-114 | 專長守則（資料結構）；作法 13 | 功能 | 一份 base 版本建出的資料庫（含舊 AWS 記錄與其他類型記錄） | 用新版本開啟並列出 | 不需要 migration：沒有新增 migration 檔、資料表結構不變、舊記錄都照常讀得出來；`status` 仍只有既有五種值 | 自動：`platform/tests/test_aws_ce.py` |
