# 測試案例：Azure Batch 計算環境類型（能建立、驗證、存放；預檢不花錢）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Every row can be judged without reading code.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/azure-ce-type/plan.md`（本任務沒有 spec.md，計畫即規格；計畫末尾的「裁決」1～13 與計畫本文衝突時，以裁決為準：裁決 12 說建立時可以不給 `--credentials`，作法 3 的「必填」指預檢必過項；裁決 11 擴充了准改的既有測試）　**總覽**：`test-case-overview.md`

名詞先講白：
- **站台代理**：裝在某台機器上、替平台去做事的小程式。Azure 的環境由「平台主機上的那一個代理」做檢查，使用者自己什麼都不用裝。
- **預檢**：建好環境後，代理去檢查「設定合不合規、憑證檔對不對、Batch 帳號認不認這把金鑰、pool 在不在且是 active、儲存體容器在不在」，全過才是 `available`（可用）。
- **憑證檔**：放 Azure 帳號金鑰的檔，只放在代理那台機器上；資料庫只記一個憑證**名字**。
- **pool**：Azure Batch 裡一組已經存在的運算節點；本任務只收「已存在的 pool 的名字」，不建立。
- **假 runner／假 which**：測試用的替身，假裝執行了 `az` 命令、假裝有沒有裝 `az`，不碰網路、不花錢。
- **az**：Azure 官方命令列工具。本任務用它做唯讀檢查，不使用任何 Azure 的 Python 套件。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」。

「驗證方式」欄括號內的 `test_…` 是計畫已列的測試函式名，供 executor 對照；每個自動測試要在註解寫出它的 TC 編號。「同檔」＝`platform/tests/test_azure_ce.py`。常數沿用計畫：`LOC=westeurope`、`BATCH=labbatch`、`STORE=labstore`、`WORKDIR=az://lab-container/work/`、`POOL=lab-pool`、`CRED=azure-lab`；`BKEY`、`SKEY`、`SAS` 是測試用的假金鑰，一律用字串拼接組出，不得在任何檔案裡寫出完整字面（`tests/credentials_stay_in_settings_test.sh` 會掃全 repo）。

## User Story 1 — 管理者能建立一個 Azure Batch 環境，設定不合規會被當場擋下（優先度 P1）

維護者原話（plan.md 引 PLAN 第 169 行）：「**C-5** Azure Batch／K8s：同模式」→ 照 C-4（AWS）的模式：類型、設定鍵規則、憑證檔在代理側、預檢唯讀、launch 另做。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 C-5；作法 1、2 | 功能 | 一個在線的代理 `a1`；設定為 location=westeurope、batchAccountName=labbatch、storageAccountName=labstore、workDir=`az://lab-container/work/`、pool=lab-pool，另加 spot=true、maxvCpus=256 | 管理者建立 `azbatch-platform` 環境 | 建立成功；狀態 `creating`；存下的 workDir 是 `az://lab-container/work`（結尾斜線去掉）；訊息含「waiting for the first preflight」；這些欄位名與值沒有被憑證偵測誤傷 | 自動：同檔（`test_a_valid_azure_batch_environment_is_created_as_creating`） |
| TC-002 | 作法 2 必填 | 例外 | 同 TC-001 但缺 location | 建立 | 被拒；錯誤訊息點名 `location` | 自動：同檔（`test_required_settings_and_agent`） |
| TC-003 | 作法 2 必填 | 例外 | 同 TC-001 但缺 batchAccountName | 建立 | 被拒；訊息點名 `batchAccountName` | 自動：同檔（同上） |
| TC-004 | 作法 2 必填 | 例外 | 同 TC-001 但缺 storageAccountName | 建立 | 被拒；訊息點名 `storageAccountName` | 自動：同檔（同上） |
| TC-005 | 作法 2 必填 | 例外 | 同 TC-001 但缺 workDir | 建立 | 被拒；訊息點名 `workDir` | 自動：同檔（同上） |
| TC-006 | 作法 2 必填；裁決 1（pool 必填） | 例外 | 同 TC-001 但缺 pool | 建立 | 被拒；訊息點名 `pool` | 自動：同檔（同上） |
| TC-007 | 作法 2「agent 必填」；原話「雲端用戶不裝站台代理」 | 例外 | 設定齊全但沒有 agent | 建立 | 被拒；訊息含「需要指定一個站台代理」 | 自動：同檔（同上） |
| TC-008 | 作法 2、10；原話「雲端用戶不裝站台代理」 | 例外 | 線上剛好只有一個代理 | 用命令列 `ce create --platform azbatch-platform` 不寫 `--agent` | 仍被拒（雲端環境必須明寫 `--agent`，不會自動挑那唯一的代理） | 自動：同檔（同上） |
| TC-009 | 裁決 12 | 功能 | 設定齊全、有 agent，但建立時不給憑證名字（不帶 `--credentials`） | 建立 | 建立成功，狀態 `creating`（不在建立時拒絕；缺憑證名字由第一次預檢報 `credential_name` 失敗，見 TC-043） | 自動：同檔（新增一條，裁決 12 要求補） |
| TC-010 | 作法 2 location | 功能 | 其他設定正確 | 分別用 location：`westeurope`、`japaneast`、`eastus2` 建立 | 三個都通過 | 自動：同檔（`test_location_rules`） |
| TC-011 | 作法 2 location | 例外 | 其他設定正確 | 分別用 location：`West Europe`、`eu-west-1`、空字串、`a; b` | 四個都被拒；訊息含範例 `westeurope` | 自動：同檔（同上） |
| TC-012 | 作法 2 兩個帳號名 | 功能 | 其他設定正確 | 分別把 batchAccountName 與 storageAccountName 設為 `labbatch`、`ab1` | 全部通過 | 自動：同檔（`test_account_name_rules`） |
| TC-013 | 作法 2 batchAccountName | 例外 | 其他設定正確 | batchAccountName 分別用 `LabBatch`、`ab`（太短）、25 個字、`lab-batch`、`lab_batch` | 五個都被拒 | 自動：同檔（同上） |
| TC-014 | 作法 2 storageAccountName | 例外 | 其他設定正確 | storageAccountName 分別用 `LabBatch`、`ab`（太短）、25 個字、`lab-batch`、`lab_batch` | 五個都被拒 | 自動：同檔（同上） |
| TC-015 | 作法 2 workDir | 功能 | 其他設定正確 | workDir 用 `az://lab-container/work/` | 存成 `az://lab-container/work` | 自動：同檔（`test_workdir_must_be_an_azure_blob_url_with_a_subfolder`） |
| TC-016 | 作法 2 workDir | 例外 | 其他設定正確 | workDir 分別用 `/data/work`、`s3://b/x`、`gs://b/x`、`az://` | 四個都被拒 | 自動：同檔（同上） |
| TC-017 | 作法 2 workDir（Nextflow 要求子目錄必填） | 例外 | 其他設定正確 | workDir 分別用 `az://lab-container`、`az://lab-container/`（只有容器名，沒有子目錄） | 兩個都被拒 | 自動：同檔（同上） |
| TC-018 | 作法 2 workDir 容器名規則 | 例外 | 其他設定正確 | workDir 分別用 `az://UPPER/x`（大寫）、`az://ab/x`（容器名太短） | 兩個都被拒 | 自動：同檔（同上） |
| TC-019 | 作法 2 workDir 子目錄規則 | 例外 | 其他設定正確 | workDir 用 `az://lab-container/../x` | 被拒 | 自動：同檔（同上） |
| TC-020 | 作法 2 pool；裁決 1 | 功能 | 其他設定正確 | pool 分別用 `lab-pool`、`Pool_1` | 兩個都通過 | 自動：同檔（`test_pool_is_an_id_not_a_path`） |
| TC-021 | 作法 2 pool（是 ID 不是路徑） | 例外 | 其他設定正確 | pool 分別用 `a b`、`a/b`、65 個字的名字、空字串 | 四個都被拒 | 自動：同檔（同上） |
| TC-022 | 作法 2 spot | 例外 | 其他設定正確 | 設 `spot` 為字串 `"yes"` | 被拒（spot 只收布林） | 自動：同檔（`test_spot_and_maxvcpus_rules`） |
| TC-023 | 作法 2 maxvCpus | 例外 | 其他設定正確 | 分別設 `maxvCpus` 為 0、10001 | 兩個都被拒（範圍只收 1～10000） | 自動：同檔（同上） |
| TC-024 | 作法 2 maxvCpus | 例外 | 其他設定正確 | 分別設 `maxvCpus` 為 `true`、`"8"` | 兩個都被拒（只收整數，不收布林與字串） | 自動：同檔（同上） |
| TC-025 | 作法 2 spot、maxvCpus | 功能 | 其他設定正確 | 設 `maxvCpus` 為 10000；另外設 `spot` 為 true、false 各一次 | 都通過，且原樣存下 | 自動：同檔（同上） |
| TC-026 | 作法 2 未知鍵 | 例外 | 其他設定正確 | 分別多帶 `region`、`vmType`、`jobQueue`、`headQueue`、`project`、`foo` | 六個都被拒；訊息含「unknown setting for an Azure Batch environment」並列出已知鍵清單 | 自動：同檔（`test_unknown_keys_are_refused_and_old_keys_say_what_to_do`） |
| TC-027 | 作法 2 未知鍵；作法 11 | 例外 | 其他設定正確 | 分別多帶 `region`、`vmType` | 兩個的訊息都另外含「請刪除後重建這個計算環境」 | 自動：同檔（同上） |
| TC-028 | 作法 2 錯誤一次列出 | 例外 | location、pool、workDir 同時填錯 | 建立 | 只出一則訊息，同時點名這三個鍵 | 自動：同檔（`test_all_errors_are_listed_at_once_and_values_are_cut`） |
| TC-029 | 作法 2 被拒的值最多顯示 60 字 | 例外 | 某欄位填一個 200 字的壞值 | 建立 | 錯誤訊息裡顯示的那個壞值不超過 60 字 | 自動：同檔（同上） |
| TC-030 | 作法 2 共用檢查 | 例外 | 其他設定正確 | `nextflowConfig` 超過 20000 字 | 被拒，拒絕方式與 Slurm 環境相同 | 自動：同檔（`test_shared_checks_apply`） |
| TC-031 | 作法 2 共用檢查 | 例外 | 其他設定正確 | `environment` 的某一項鍵名不合規 | 被拒，拒絕方式與 Slurm 環境相同 | 自動：同檔（同上） |

## User Story 2 — 憑證只是一個名字，金鑰絕不進資料庫（優先度 P1）

維護者原話：「四種計算環境都建：…… 架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（憑證與環境分開，環境只記憑證名字。）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 作法 3；原話（憑證 → 環境分開） | 功能 | 建立時帶 `credentialsId=azure-lab` | 建立後 `ce show` | 頂層 `credentialsId` 顯示 `azure-lab`；設定（config）裡沒有任何憑證相關的鍵 | 自動：同檔（`test_the_credential_is_only_a_name_at_the_top_level`） |
| TC-033 | 作法 3；裁決 13 | 例外 | 其他設定正確 | 分別用 credentialsId：含空白的、含 `=` 的、`BKEY + "=="`（假金鑰加兩個等號，真實 Azure 金鑰是 base64、常以 `==` 結尾） | 三個都被拒（它只能是名字） | 自動：同檔（`test_credentials_id_is_a_name_only`） |
| TC-034 | 作法 3；Safety Net 憑證條 | 例外 | 其他設定正確 | 把 `AccountKey=` 開頭的連線字串（用拼接組出）分別放進 `description`、`nextflowConfig`、`environment` 的某個值、`workDir` 的子目錄 | 四處都被拒 | 自動：同檔（`test_an_account_key_or_sas_pasted_anywhere_is_refused_and_not_repeated`） |
| TC-035 | 作法 3 | 例外 | 其他設定正確 | 把 `SharedAccessSignature=…` 字串分別放進同樣四處 | 四處都被拒 | 自動：同檔（同上） |
| TC-036 | 作法 3 | 例外 | 其他設定正確 | 把含 `sig=` 的 SAS 字串（`SAS`，用拼接組出）分別放進同樣四處 | 四處都被拒 | 自動：同檔（同上） |
| TC-037 | 作法 3；專長守則（密鑰不得出現在回應） | 例外 | 同 TC-034～036 的貼法 | 看錯誤訊息，並逐位元組檢查資料庫檔 | 錯誤訊息只講欄位位置、不重複那串字；資料庫檔裡找不到 `BKEY`、`SKEY`、`SAS` 的任何片段 | 自動：同檔（同上） |
| TC-038 | 作法 3 | 例外 | 其他設定正確 | 設定裡分別加 `batchAccountKey`、`accountKey`、`sasToken`、`servicePrincipalSecret` | 四個都被憑證偵測擋下（訊息說這像憑證、只留名字） | 自動：同檔（`test_a_key_named_field_is_refused`） |
| TC-039 | 作法 3「新規則不誤傷」 | 功能 | `good_config()`（location、pool、workDir、兩個帳號名都是正常值） | 完整建立 | 建立成功（新增的三條 Azure 憑證字樣沒有誤傷正常值） | 自動：同檔（`test_normal_values_are_not_mistaken_for_secrets`） |
| TC-040 | 作法 3「新規則不誤傷」 | 功能 | 其他設定正確 | `description` 寫普通文字，含 `design=1` 與 `signature` 字樣 | 建立成功，沒有被誤擋 | 自動：同檔（同上） |
| TC-041 | 作法 4（平台不讀憑證檔） | 功能 | 憑證檔（含 `BKEY`、`SKEY`）寫在代理部署的 `_personal/` 下 | 建立、列出、`ce show` | `platform.db` 位元組與所有命令列輸出都找不到 `BKEY`、`SKEY` | 自動：同檔（`test_the_platform_does_not_read_the_credential_file`） |

## User Story 3 — 預檢：代理唯讀地檢查，全過才可用，而且不花錢（優先度 P1）

維護者原話：「10-21，他定：雲端優先於畫布；雲端用戶不裝站台代理。」（預檢由平台主機上的那個代理做；使用者什麼都不用裝。）憑證檔格式（裁決 2）：INI，只讀 `[default]`；鍵名 `batch_account_key`（必填）、`storage_account_key` 或 `storage_sas_token`（二擇一）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-042 | 作法 5 檢查表 | 功能 | 假 runner、假 which | 跑一次預檢 | 回報六項，依序為 `credential_name, credential_file, credential_shape, az, pool, storage`；每項都有 name、status、detail | 自動：同檔（`test_every_check_is_reported_with_name_status_and_detail`） |
| TC-043 | 作法 5 credential_name；裁決 12 | 例外 | 環境沒設 `credentialsId` | 跑預檢 | `credential_name` 為 fail；`credential_shape` 為 unchecked | 自動：同檔（`test_a_missing_credential_name_is_a_failure`） |
| TC-044 | 作法 5 credential_file | 例外 | 憑證檔不存在 | 跑預檢 | `credential_file` 為 fail；detail 寫出實際應放的路徑（`<deployment>/_personal/azure-credentials`）與 `chmod 600` | 自動：同檔（`test_a_missing_credential_file_says_where_to_put_it`） |
| TC-045 | 作法 5「憑證檔不可用…runner 一次都不呼叫」 | 例外 | 憑證檔不存在 | 跑預檢 | `pool`、`storage` 都是 unchecked；環境狀態 `invalid`；假 runner 被呼叫 0 次 | 自動：同檔（同上） |
| TC-046 | 作法 4 | 功能 | 設 `ABF_STATION_AZURE_CREDENTIALS=<tmp>/x` | 取憑證檔路徑 | 回該路徑 | 自動：同檔（`test_the_credential_file_location_follows_the_agents_setting`） |
| TC-047 | 作法 4 | 功能 | 不設該環境變數 | 取憑證檔路徑 | 回 `<settings 檔 parent.parent>/_personal/azure-credentials` | 自動：同檔（同上） |
| TC-048 | 作法 5 credential_file（POSIX） | 例外 | POSIX 系統；憑證檔權限 0644（別人讀得到） | 跑預檢 | `credential_file` 為 fail；detail 含 `chmod 600` | 自動：同檔（`test_a_credential_file_other_people_can_read_is_refused`，Windows 跳過） |
| TC-049 | 作法 5 credential_file（POSIX） | 功能 | POSIX 系統；憑證檔權限 0600 | 跑預檢 | `credential_file` 為 pass | 自動：同檔（同上） |
| TC-050 | 作法 5 credential_file（Windows） | 功能 | 把平台判斷設成 win32 | 跑預檢 | `credential_file` 為 pass；detail 含「Windows 不檢查權限位」 | 自動：同檔（`test_permission_bits_are_not_checked_on_windows`） |
| TC-051 | 作法 5 | 例外 | 憑證檔路徑其實是一個資料夾 | 跑預檢 | `credential_file` 為 fail，訊息說不是一般檔案（not a regular file） | 自動：同檔（`test_a_credential_file_that_is_a_folder_is_refused`） |
| TC-052 | 作法 5 credential_shape (a) | 例外 | `[default]` 區段缺 `batch_account_key` | 跑預檢 | `credential_shape` 為 fail；detail 說缺 `batch_account_key` | 自動：同檔（`test_the_shape_of_the_file_is_judged_without_printing_it` (a)） |
| TC-053 | 作法 4、5 (b) | 例外 | 憑證檔只有別的區段（例如 `[other]`），沒有 `[default]` | 跑預檢 | `credential_shape` 為 fail；detail 含「沒有 [default] 區段」與檔案路徑；detail **不含**檔內其他區段名（`other`） | 自動：同檔（同上 (b)） |
| TC-054 | 作法 5 (c) | 例外 | 有 `batch_account_key`，但 `storage_account_key` 與 `storage_sas_token` 都沒有 | 跑預檢 | `credential_shape` 為 fail；detail 同時點名 `storage_account_key` 與 `storage_sas_token` 這兩個鍵 | 自動：同檔（同上 (c)） |
| TC-055 | 作法 5 (d) | 功能 | 有 `batch_account_key`，只有 `storage_sas_token`（沒有 `storage_account_key`） | 跑預檢 | `credential_shape` 為 pass | 自動：同檔（同上 (d)） |
| TC-056 | 作法 4、5 (e) | 例外 | 憑證檔是隨機位元組，不是 INI | 跑預檢 | `credential_shape` 為 fail；detail 是固定的一句話，不夾檔案內容 | 自動：同檔（同上 (e)） |
| TC-057 | 作法 4（`interpolation=None`） | 功能 | 憑證檔 `storage_sas_token` 的值含 `%3A` 這種百分號編碼（真實 SAS 常見），其餘正常 | 跑預檢 | `credential_shape` 為 pass（百分號不被當成變數替換而出錯） | 自動：同檔（新增一條） |
| TC-058 | 作法 4（檔大小 ≤1 MB） | 例外 | 憑證檔大於 1 MB | 跑預檢 | `credential_shape` 不是 pass（不解析該檔）；回報裡沒有檔案內容 | 自動：同檔（新增一條） |
| TC-059 | 作法 4、5；專長守則（密鑰不得出現在回應） | 例外 | TC-052～TC-056 五種壞檔，檔內有 `BKEY`、`SKEY`、`SAS` | 看整份 `checks` 的內容（轉成 JSON）與環境的 `message` | 兩者都找不到 `BKEY`、`SKEY`、`SAS` 的任何片段，也不列出檔內其他區段名 | 自動：同檔（同上） |
| TC-060 | 作法 5 az | 例外 | 假 which 回「沒有 az」；憑證檔正常 | 跑預檢 | `az` 為 unchecked（不是 fail） | 自動：同檔（`test_without_the_az_cli_the_api_checks_are_unchecked_and_nothing_is_run`） |
| TC-061 | 作法 5「沒有 az 時…環境停在 invalid」 | 例外 | 同 TC-060 | 跑預檢並看環境 | `pool`、`storage` 為 unchecked；環境 `invalid`；`message` 含「az」與「沒裝」；假 runner 呼叫 0 次 | 自動：同檔（同上） |
| TC-062 | 作法 5 狀態規則 | 功能 | 憑證檔正常；假 runner：`batch pool show` 回 `(0,"active")`、`storage container exists` 回 `(0,"true")` | 跑預檢並記錄結果 | 六項全 pass；環境狀態 `available` | 自動：同檔（`test_all_checks_passing_makes_the_environment_available`） |
| TC-063 | 作法 5 pool；裁決 13 | 例外 | 假 runner 對 `batch pool show` 回 `(3, "PoolNotFound …")` | 跑預檢 | `pool` 為 fail；detail 含 `lab-pool`（例如「pool lab-pool 不存在於這個 Batch 帳號」） | 自動：同檔（`test_a_pool_that_is_missing_or_not_active_fails`） |
| TC-064 | 作法 5 pool | 例外 | 假 runner 對 `batch pool show` 回 `(0,"deleting")` | 跑預檢 | `pool` 為 fail | 自動：同檔（同上） |
| TC-065 | 作法 5「逐項各自執行」 | 例外 | 同 TC-063（pool 失敗） | 看 `storage` | `storage` 仍被執行（假 runner 收到 storage 的呼叫） | 自動：同檔（同上） |
| TC-066 | 作法 5「任何一項不是 pass 就不是 available」 | 例外 | 同 TC-063，其餘都正常 | 看環境 | 環境狀態 `invalid`；`message` 點名 `pool` 這一項 | 自動：同檔（同上） |
| TC-067 | 作法 5 storage | 例外 | 假 runner 對 `storage container exists` 回 `(0,"false")` | 跑預檢 | `storage` 為 fail；detail 含容器名 `lab-container` | 自動：同檔（`test_a_missing_container_fails`） |
| TC-068 | 作法 5 storage（輸出為真值／為假） | 功能 | 假 runner 對 `storage container exists` 分別回 `(0,"True")`、`(0,"False")`（az 的表格輸出常把布林寫成首字母大寫） | 各跑一次預檢 | `True` → `storage` pass；`False` → `storage` fail | 自動：同檔（新增一條） |
| TC-069 | 作法 5 storage；專長守則 | 例外 | 假 runner 對 `storage container exists` 回 `(1, 2000 字輸出，夾一串 AccountKey= 連線字串與一段 88 字 base64)` | 跑預檢 | `storage` 為 fail；detail 不超過 300 字 | 自動：同檔（`test_an_api_failure_is_reported_trimmed_and_scrubbed`） |
| TC-070 | 作法 5 `_scrub`；專長守則（密鑰不得出現在回應） | 例外 | 同 TC-069 | 看 detail | 不含那串連線字串，也不含那段 88 字 base64 | 自動：同檔（同上） |
| TC-071 | 作法 5「逾時只讓該項 fail」 | 例外 | 假 runner 讓 `batch pool show` 丟出逾時（`TimeoutError`） | 跑預檢 | `pool` 為 fail，detail 含「逾時」 | 自動：同檔（`test_a_timeout_fails_that_check_only`） |
| TC-072 | 作法 5 | 例外 | 同 TC-071 | 看 `storage` | `storage` 仍被執行 | 自動：同檔（同上） |
| TC-073 | 作法 5「唯讀、不計費」 | 功能 | 記錄預檢送出的所有命令 | 跑完整預檢 | 每條命令的前綴都是 `az batch pool show` 或 `az storage container exists` 二者之一 | 自動：同檔（`test_the_commands_are_read_only`） |
| TC-074 | 作法 5「不花錢保證」 | 功能 | 同 TC-073 | 檢查所有命令的每個字 | 沒有任何字是 create、delete、resize、update、upload、set、start、stop、login、autoscale、job、task、copy、remove（以整個字詞比對；`--output` 這類參數不算誤報） | 自動：同檔（同上） |
| TC-075 | 作法 2 spot、maxvCpus（只存） | 功能 | 環境設定 spot=true、maxvCpus=256 | 跑完整預檢 | 送出的仍只有那兩種唯讀命令，命令與環境變數裡都沒有用到 spot 或 maxvCpus；兩個值照存 | 自動：同檔（新增一條，併入命令記錄） |
| TC-076 | 作法 5 環境變數 | 功能 | 憑證檔含 `BKEY`；記錄每次呼叫收到的環境變數 | 跑完整預檢 | 每次都有：`AZURE_BATCH_ACCOUNT=="labbatch"`、`AZURE_BATCH_ENDPOINT=="https://labbatch.westeurope.batch.azure.com"`、`AZURE_BATCH_ACCESS_KEY==BKEY` | 自動：同檔（`test_the_credential_goes_in_the_environment_not_in_argv`） |
| TC-077 | 作法 5 環境變數 | 功能 | 憑證檔含 `storage_account_key`（`SKEY`） | 看 `storage` 那次呼叫的環境變數 | 有 `AZURE_STORAGE_ACCOUNT=="labstore"` 與 `AZURE_STORAGE_KEY==SKEY` | 自動：同檔（同上） |
| TC-078 | 作法 5 環境變數 | 功能 | 憑證檔只有 `storage_sas_token` | 看 `storage` 那次呼叫的環境變數 | 改設 `AZURE_STORAGE_SAS_TOKEN`（值為該 SAS）；沒有 `AZURE_STORAGE_KEY` | 自動：同檔（同上） |
| TC-079 | 作法 5 `AZURE_CONFIG_DIR`（不准悄悄改用主機上 `az login` 留下的登入狀態） | 功能 | 記錄每次呼叫收到的環境變數 | 跑完整預檢 | 每次呼叫的 `AZURE_CONFIG_DIR` 指向一個存在、且是空的暫存資料夾 | 自動：同檔（同上） |
| TC-080 | 作法 5 環境變數 | 功能 | 同 TC-079 | 看環境變數 | `AZURE_CORE_COLLECT_TELEMETRY=="false"`、`AZURE_CORE_NO_COLOR=="true"`、`AZURE_CORE_ONLY_SHOW_ERRORS=="true"` | 自動：同檔（同上） |
| TC-081 | 作法 5「金鑰與路徑只在 env，不在 argv」 | 功能 | 同 TC-076 | 檢查每條命令的參數 | 任何參數都不含 `BKEY`、`SKEY`、`SAS`，也不含憑證檔路徑 | 自動：同檔（同上） |
| TC-082 | 作法 5 `_az_env`（先刪 `ABF_*` 與 `AZURE_*`） | 功能 | 測試先在自己的環境設 `AZURE_CLIENT_SECRET=X`、`AZURE_STORAGE_KEY=Y`、`ABF_PLATFORM_TOKEN=T` | 跑完整預檢 | 傳給 `az` 的環境裡沒有繼承到這三個（`AZURE_STORAGE_KEY` 若出現，值是檔裡的 `SKEY` 而不是 `Y`），也沒有任何 `ABF_` 開頭的變數 | 自動：同檔（同上） |
| TC-083 | 作法 5「呼叫完刪除」 | 功能 | 同 TC-079 | 預檢結束後檢查那些暫存資料夾 | 都已被刪除 | 自動：同檔（同上） |
| TC-084 | 作法 5 預設 runner | 功能 | 把 `subprocess.run` 換成替身 | 呼叫預設 runner：`["az","storage","container","exists"]`、環境 `{"A":"1"}`、逾時 30 | 替身收到 `shell=False`、list 型參數、`timeout=30` | 自動：同檔（`test_the_default_runner_is_a_fixed_argv_without_a_shell`） |
| TC-085 | 作法 5 clean_environment（代理再驗一次） | 例外 | 直接把壞值送進代理端的 `clean_environment` | 分別送：location=`x; touch c`、batchAccountName=`A B`、workDir=`az://lab-container`（沒有子目錄）、pool=`q q`、credentialsId=`a b` | 五個都被拒（`rules.Refusal`） | 自動：同檔（`test_the_agent_judges_the_environment_again_before_it_builds_a_command`） |
| TC-086 | 作法 5 clean_environment | 例外 | 送進 `platform` 為 `slurm-platform`、`awsbatch-platform` 的環境 | 呼叫 `clean_environment` | 兩個都被拒（Azure 預檢不接別的類型） | 自動：同檔（同上） |
| TC-087 | 作法 5 clean_environment、作法 7 | 功能 | 一個合規、還帶有 spot、maxvCpus、nextflowConfig 的 Azure 環境 | 呼叫 `clean_environment` | 只留 `name, platform, credentialsId, location, batchAccountName, storageAccountName, workDir, pool` 八個鍵 | 自動：同檔（新增一條） |
| TC-088 | 作法 6（Azure 不得落到 Slurm 路徑） | 功能 | 代理收到 Azure 環境的 preflight 工作（假 runner、假 which、憑證檔就位） | 代理處理該工作 | 工作完成並回報 Azure 的六項檢查結果；沒有經過 Slurm 的 `rules.clean_environment` 路徑 | 自動：`platform/tests/test_azure_ce.py`（`test_ce_preflight_waits_for_the_agent_and_prints_each_check` 與代理分支斷言） |
| TC-089 | 計畫「完成標準：手動」；裁決 3 | 功能 | 維護者的 Azure 帳號已開，且事先手動建好 Batch 帳號、儲存體帳號、blob 容器與一個 pool；平台主機已裝 Azure CLI；憑證檔放 `<agent deployment>/_personal/azure-credentials`（權限 600，`[default]` 區段） | `abf-platform ce create --name az1 --platform azbatch-platform --agent <代理> --credentials azure-lab --location <區域> --batch-account <名> --storage-account <名> --work-dir az://<容器>/work --pool <pool>` | 看到每一項檢查結果；全 pass 時 `ce show az1` 顯示 `available`；`ce show` 輸出與 `platform.db` 裡搜不到金鑰任何片段；Azure 帳單沒有新項目 | 手動：`docs/TESTING.md`「Azure Batch environment (azure-ce-type)」 |
| TC-090 | 裁決 3（C 級手動驗收） | 功能 | 同 TC-089 | 確認「只用金鑰環境變數執行 `az batch pool show`，不先 `az batch account login`」真的成功 | 成功則 `pool` 檢查為 pass；若不成功，回報 developer-agent 改檢查方式（不自己改）。步驟寫進 TESTING.md | 手動：`docs/TESTING.md`「Azure Batch environment (azure-ce-type)」 |

## User Story 4 — 接上代理與命令列；`available` 之後仍不能送出、不會被自動挑走（優先度 P1）

維護者原話：「撞牆時先砍 …… AWS／Azure」→ 本片刻意小：只做建立＋預檢，不做 launch、費用、上傳、清理。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-091 | 作法 6、10 | 功能 | 代理 `a1` 在線 | `ce create --platform azbatch-platform --agent a1 --credentials azure-lab --location westeurope --batch-account labbatch --storage-account labstore --work-dir az://lab-container/work --pool lab-pool` | 回傳碼 0；輸出含「preflight queued」；工作表多一列 `preflight` | 自動：同檔（`test_create_queues_the_first_preflight_for_the_agent`） |
| TC-092 | 作法 7 snapshot | 功能 | 同 TC-091 | 看那一列工作的 `ce` 參數 | 鍵集合恰為 `{name, platform, credentialsId, location, batchAccountName, storageAccountName, workDir, pool}`，沒有別的 | 自動：同檔（同上） |
| TC-093 | 作法 10（代理離線不假裝） | 例外 | 代理離線 | 建立 Azure 環境 | 訊息含「沒有代理在線」；狀態仍 `creating`；工作表沒有新增列 | 自動：同檔（`test_create_with_the_agent_offline_says_so_and_does_not_pretend`） |
| TC-094 | 作法 6、10；環境事實（Azure 不得落到 Slurm 路徑） | 功能 | 自動服務的代理夾具；一個 Azure 環境 `az1` | `ce preflight az1` | 逐項印出 `name: status - detail`，名稱是上述六個 Azure 檢查名 | 自動：同檔（`test_ce_preflight_waits_for_the_agent_and_prints_each_check`） |
| TC-095 | 作法 10 旗標 | 功能 | 無 | 建立時帶 `--batch-account labbatch --storage-account labstore --pool lab-pool --location westeurope --spot` | `ce show` 的設定分別有 batchAccountName、storageAccountName、pool、location，以及 `spot:true` | 自動：同檔（`test_cli_flags`） |
| TC-096 | 作法 10 旗標 | 功能 | 無 | 建立時帶 `--no-spot` | `ce show` 的 `spot` 為 false | 自動：同檔（同上） |
| TC-097 | 作法 10；裁決 5（說明文字） | 功能 | 無 | 看 `ce create` 的說明 | `--location` 的說明寫「Google Batch／Azure Batch: the region」 | 自動：同檔（新增一條） |
| TC-098 | 作法 10（說明文字） | 功能 | 無 | 看 `ce create` 的說明 | `--spot`／`--no-spot` 的說明提到 Azure Batch | 自動：同檔（新增一條） |
| TC-099 | 作法 1（其他類型不變） | 功能 | 建立一個 Slurm 環境 | 建立並看工作表與 snapshot | 仍排入 preflight；snapshot 與改動前逐鍵相同 | 自動：同檔（`test_slurm_google_batch_and_aws_batch_are_unchanged`） |
| TC-100 | 作法 1（其他類型不變） | 功能 | 建立一個 Google Batch 環境 | 建立並看預檢走向與 snapshot | 仍走 `gcb_preflight`；snapshot 與改動前逐鍵相同 | 自動：同檔（同上） |
| TC-101 | 作法 1（其他類型不變） | 功能 | 建立一個 AWS Batch 環境 | 建立並看預檢走向與 snapshot | 仍走 `aws_preflight`；snapshot 與改動前逐鍵相同；AWS 的送出相關行為（含拒絕句）不變 | 自動：同檔（同上）與 `platform/tests/test_aws_clean.py` |
| TC-102 | 作法 1、裁決 6（fail-closed） | 功能 | 無 | 讀常數 | `SUPPORTED` 仍是 `slurm-platform`；`PLATFORM_HOST_TYPES == ("googlebatch-platform","awsbatch-platform")`（原樣不動）；`CHECK_ONLY_TYPES == ("azbatch-platform",)`；`CHECKABLE == (SUPPORTED, GCB, AWS, "azbatch-platform")` | 自動：`platform/tests/test_gcb_ce.py`（TC-089 更新後） |
| TC-103 | 作法 8；原話「撞牆時先砍…… Azure」 | 例外 | 一個 `available` 的 Azure 環境、代理在線 | 對它分別排：`launch_nextflow`、`cancel_run`、`clean_work`、`put_upload`、`list_site_files`、`pipeline_files` | 六個都被拒；訊息含「尚未支援送出」與 `azure-launch`；不含 "AWS" | 自動：同檔（`test_jobs_other_than_the_preflight_are_refused_in_plain_words`） |
| TC-104 | 作法 8 | 例外 | 同 TC-103 | 看工作表列數 | 被拒之後列數不變（什麼都沒排進去） | 自動：同檔（同上） |
| TC-105 | 作法 9 | 例外 | 同 TC-103 | `build.target_problem(state,"az1","launch_nextflow")` | 回非空的白話句（送出被拒） | 自動：同檔（`test_launch_is_refused_and_the_environment_is_never_auto_picked`） |
| TC-106 | 作法 9 | 例外 | 只有一個 `available` 的 Azure 環境 | 自動挑主要環境（`build.primary_environment`） | 回「沒有」（不會挑 Azure） | 自動：同檔（同上） |
| TC-107 | 作法 9 | 功能 | 同時有 `available` 的 Slurm 與 Azure 環境 | 自動挑主要環境 | 選到 Slurm 環境 | 自動：同檔（同上） |
| TC-108 | 專長守則（跨使用者，讀） | 例外 | 使用者 A 有一個 Azure 環境；使用者 B 登入 | B 以自己的身分查看、取得 A 的 Azure 環境（以 `owner=` 取） | 找不到（回「沒有」，與環境不存在時相同） | 自動：同檔（`test_another_users_azure_environment_is_not_found`） |
| TC-109 | 專長守則（跨使用者，寫） | 例外 | 同 TC-108 | B 對 A 的 Azure 環境排 `preflight` | 被拒，文字與環境不存在時一模一樣；工作表沒有新增列 | 自動：同檔（同上） |
| TC-110 | 專長守則（跨使用者，寫） | 例外 | 同 TC-108 | B 嘗試修改、停用 A 的 Azure 環境（`ce update`、`ce disable`） | 兩者都被拒，與不存在相同；A 的環境設定與狀態完全沒變 | 自動：同檔（新增一條；計畫清單缺此條，補） |
| TC-111 | 作法 10 | 功能 | 一個已停用（`ce disable`）的 Azure 環境 | `ce update --pool other` | 設定改了，但工作表列數不變（停用中不排預檢） | 自動：同檔（`test_updating_a_disabled_environment_queues_no_preflight`） |

## User Story 5 — 以前就存在的 `azbatch-platform` 舊記錄（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112 | 作法 11 | 功能 | 資料庫直接插一列舊記錄：`azbatch-platform`、`unsupported`、設定 `{"workDir":"az://lab-container/work","region":"westeurope","vmType":"Standard_D4s_v3"}` | `ce list`、`ce show` | 照常顯示；狀態仍 `unsupported` | 自動：同檔（`test_an_old_azure_record_is_still_listed_and_shown`） |
| TC-113 | 作法 11 | 例外 | 同 TC-112 | `ce preflight` 該環境 | 回傳碼不為 0；訊息點名 `region` 或 `vmType`，並含「請刪除後重建這個計算環境」；狀態仍 `unsupported` | 自動：同檔（`test_an_old_record_is_refused_with_the_next_step`） |
| TC-114 | 作法 11 | 例外 | 同 TC-112 | `ce update --agent a1 --pool lab-pool` | 回傳碼不為 0（update 不能刪鍵）；訊息點名 `region` 或 `vmType` 並含「請刪除後重建這個計算環境」；環境內容沒被改 | 自動：同檔（同上） |

## User Story 6 — 文件寫清楚（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-115 | 作法 12 | 功能 | 無 | 讀 `docs/PLATFORM.md` | 含 `` `location` ``、`` `batchAccountName` ``、`` `storageAccountName` ``、`` `workDir` ``、`` `pool` ``、`` `spot` ``、`` `maxvCpus` `` 與六個檢查名（`credential_name`、`credential_file`、`credential_shape`、`az`、`pool`、`storage`）各一個 | 自動：同檔（`test_docs_list_every_azure_key_and_check`） |
| TC-116 | 作法 12；裁決 2 | 功能 | 無 | 讀 `docs/PLATFORM.md` 的 Azure Batch 小節 | 含 `ABF_STATION_AZURE_CREDENTIALS`、`_personal/azure-credentials`、`[default]` 區段、鍵名 `batch_account_key`（以及 `storage_account_key`、`storage_sas_token`）、`預檢不計費`、`creates no pool` | 自動：同檔（同上） |
| TC-117 | 作法 12 | 功能 | 無 | 讀 `docs/PLATFORM.md` 第 8 節 | 型別表 Azure Batch 的 Supported 欄是 `checked on the platform host (launch: not yet)`；「Fourteen types」那段含 `the other ten types can be modelled only`，並把 Azure Batch 列為「can be created and checked」；整份不再有 `the other eleven` | 自動：同檔（同上，新增斷言） |
| TC-118 | 裁決 2 | 功能 | 無 | 讀 `docs/PLATFORM.md` 的 Azure Batch 小節 | 明寫「user subscription 模式的 Batch 帳號本片不支援」（同義的清楚句子即可，須點出 user subscription 模式與不支援） | 自動：同檔（同上，新增斷言） |
| TC-119 | 作法 12；裁決 1、4 | 功能 | 無 | 讀 `docs/PLATFORM.md` 的 Azure Batch 小節 | 寫明：`spot` 只存、對應 Nextflow 的 `lowPriority`；pool 必須事先由營運者建好（本平台不建）；平台主機要裝 `az` 命令列 | 自動：同檔（同上，新增斷言） |
| TC-120 | 作法 12 | 功能 | 無 | 讀 `docs/SEQERA_PARITY.md` | `azbatch-platform` 那一列含 `Have (create + check); launch in azure-launch`，且以 `[ ] |` 結尾（勾選維持未勾）；F 節開頭那句也提到 Azure Batch（與 AWS 同樣處理） | 自動：同檔（同上） |
| TC-121 | 作法 12；裁決 13（手動步驟寫進文件） | 功能 | 無 | 讀 `docs/TESTING.md` | 有「Azure Batch environment (azure-ce-type)」小節，含 `azure-ce-type`、`預檢不計費`、`git diff`，並寫出 TC-089、TC-090、TC-131、TC-132 的步驟（維護者放憑證檔、建環境、看到 available、驗證金鑰環境變數可用；驗收者看 `git diff --name-only`） | 自動：同檔（同上） |
| TC-122 | 作法 12（範例不得露真實資料） | 例外 | 無 | 掃三份文件（PLATFORM、SEQERA_PARITY、TESTING） | 找不到 `AccountKey=`、`sig=` 字樣；找不到 GUID 形狀的訂閱／租戶 ID；文件裡出現的 `az://` 網址只用 `lab-container` 或佔位符；範例只用 `lab-container`、`labbatch`、`labstore`、`westeurope`、`lab-pool` | 自動：同檔（同上） |

## User Story 7 — 計畫明講這次不做的事（優先度 P2）

維護者原話：「費用顯示美元、每人每月上限」→ 本片不碰費用、不加任何幣別欄位。「撞牆時先砍 …… AWS／Azure」→ 本片只做建立＋預檢。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-123 | 不做第 1 條（不送出、不取消、不續跑） | 不在範圍 | 無 | 掃 `abf_platform/`、`abf_station/` 原始碼 | 沒有 `az batch job`、`az batch task`；`azure_preflight.py` 沒有 `-with-tower`；Azure 環境的送出被明白拒絕（見 TC-103） | 自動：同檔（`test_no_launch_cost_or_upload_code_for_azure`） |
| TC-124 | 不做第 2 條；原話「費用顯示美元…」（本片不碰） | 不在範圍 | 無 | 建立時多帶 `currency`、`costCap` 之類鍵 | 被當作未知鍵拒絕；沒有任何幣別／費用欄位或費率程式被加入 | 自動：同檔（新增一條，併入 `test_unknown_keys_are_refused_and_old_keys_say_what_to_do`） |
| TC-125 | 不做第 2 條（不做容器上傳、不做 work 清理） | 不在範圍 | 無 | 掃 `abf_platform/`、`abf_station/` 原始碼 | 沒有 `az storage blob upload`、`az storage blob delete`、`azcopy`；Azure 環境的 `put_upload`／`clean_work` 被拒（見 TC-103） | 自動：同檔（`test_no_launch_cost_or_upload_code_for_azure`） |
| TC-126 | 不做第 2 條（不建 pool、帳號、容器；不做 auto-pool；只收已存在的 pool） | 不在範圍 | 無 | 掃原始碼；建立時多帶 `allowPoolCreation`、`autoPoolMode` | 沒有 `az batch pool create`、`az batch pool delete`、`az batch pool resize`、`az storage container create`；兩個鍵被當未知鍵拒絕 | 自動：同檔（同上與未知鍵測試） |
| TC-127 | 不做第 3 條（不支援 Entra：service principal、managed identity；不做 Fusion、自訂映像、虛擬網路、file share） | 不在範圍 | 無 | 建立時分別多帶 `servicePrincipalId`、`tenantId`、`managedIdentity`、`virtualNetwork`、`customImage`、`fileShare` | 六個都被拒（未知鍵）；預檢送出的命令與環境沒有 `az login`、`--auth-mode login`（見 TC-074） | 自動：同檔（新增一條，併入未知鍵測試） |
| TC-128 | 不做第 4 條（不用 `azure-*` Python 套件、不用 azcopy） | 不在範圍 | 無 | 掃 `azure_preflight.py` 與 `pyproject.toml` | 沒有 `import azure`、`boto3`、`botocore`、`google`、`requests`；`pyproject.toml` 沒有 `azure-`、`boto3`、`botocore` | 自動：同檔（`test_no_cloud_library_is_imported`） |
| TC-129 | 不做第 5 條（不新增 MCP 工具、網頁路由、畫面；不改 hello） | 不在範圍 | 無 | 列出 MCP 工具名與網頁路由表、讀 `hello` 回傳 | 工具名仍是現有 12 個；路由表不變；`hello` 不變 | 自動：同檔（`test_tool_list_unchanged_and_no_new_web_route`） |
| TC-130 | 不做第 6 條（其他類型維持不支援） | 不在範圍 | 無 | 對其餘 10 種 `UNSUPPORTED` 類型（含 `awscloud-platform`、`azcloud-platform`、`k8s-platform`、`eks-platform`、`gke-platform`）各建立一次 | 都建立成功且狀態是 `unsupported`；訊息仍說尚未支援 | 自動：同檔（`test_the_other_types_stay_unsupported`） |
| TC-131 | 不做第 7 條與「範圍：檔案」（不碰網頁檔、`abf_launch/`、`gcb_preflight.py`、`aws_preflight.py`、`launch.py`、`cloud_store.py`、`clean.py`） | 不在範圍 | 無 | 驗收者看 `git diff --name-only` 對 base | 只出現計畫「範圍：檔案」列的檔、裁決 11 所列的既有測試檔、以及依裁決 10 列進帳本的既有測試檔；不含任何網頁檔、`abf_launch/`、上述不准碰的檔 | 手動：`docs/TESTING.md`「Azure Batch environment (azure-ce-type)」 |
| TC-132 | 「必須更新的既有斷言」與裁決 10、11（其他一律不准動） | 不在範圍 | 無 | 驗收者逐檔比對既有測試與 base | 被改的既有斷言只限：在集合／計數／文件列加入 Azure、把 Azure 移出 unsupported 名單、`eleven`→`ten` 字樣、以及把 `azbatch-platform` 換成仍 unsupported 的類型；沒有刪除或放寬任何斷言，也沒有動到 AWS／Google／Slurm 的語意；新斷言數不少於舊的 | 手動：`docs/TESTING.md`「Azure Batch environment (azure-ce-type)」（git diff 步驟） |

## User Story 8 — 既有測試只做計畫列出的有意更新（優先度 P2）

這些是計畫「必須更新的既有斷言」與裁決 10、11 列出的更新；每一條更新後該測試檔必須是綠的，且其他斷言原封不動。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-133 | 必須更新的既有斷言（`test_station_envs.py` UNSUPPORTED） | 功能 | 無 | 讀 `UNSUPPORTED` 名單並跑 `test_station_envs.py` | 名單移除 `azbatch-platform` 剩 10 種；`test_tc030_…` 的名稱與頂部註解由 eleven／11 改 ten／10；斷言本身不動；檔案全綠 | 自動：`platform/tests/test_station_envs.py` |
| TC-134 | 必須更新的既有斷言（TC-032） | 功能 | 無 | 跑 TC-032 | 集合加入 `azbatch-platform` 後仍等於 `KINDS`；`len(KINDS)==14` 不動 | 自動：`platform/tests/test_station_envs.py` |
| TC-135 | 必須更新的既有斷言（TC-096） | 功能 | 無 | 跑 TC-096 | 「尚未支援的環境不能當主要」改用 `azcloud-platform` 與 `UNSUPPORTED["azcloud-platform"]`，意思不變，仍綠 | 自動：`platform/tests/test_station_envs.py` |
| TC-136 | 必須更新的既有斷言（TC-085） | 功能 | 無 | 跑 TC-085（禁止原始碼 import 雲端套件） | 迴圈自動縮成 10 種，斷言不動，仍綠 | 自動：`platform/tests/test_station_envs.py` |
| TC-137 | 必須更新的既有斷言（`test_gcb_ce.py`） | 功能 | 無 | 跑 `test_gcb_ce.py` | `len(UNSUPPORTED)==10`；常數斷言改成 `CHECK_ONLY_TYPES == ("azbatch-platform",)` 與加入 Azure 的 `CHECKABLE`（`PLATFORM_HOST_TYPES` 斷言不動）；文件句子斷言與新句一致；其餘斷言不動；全綠 | 自動：`platform/tests/test_gcb_ce.py` |
| TC-138 | 裁決 11（`test_aws_ce.py`、`test_aws_launch.py`） | 功能 | 無 | 跑兩個檔 | 只加入 Azure（UNSUPPORTED 計數 10、不再把 `azbatch-platform` 當 unsupported 範例、`CHECK_ONLY_TYPES`／`CHECKABLE` 加 Azure、文件句子 eleven→ten）；`compute_envs.py` 中以 `CHECK_ONLY_TYPES` 開頭的那一行仍含「新雲端類型先放這裡，只開預檢」；全綠 | 自動：`platform/tests/test_aws_ce.py`、`platform/tests/test_aws_launch.py` |
| TC-139 | 必須更新的既有斷言（`test_station_docs.py` TC-077） | 功能 | 無 | 跑 TC-077 | 跳過清單加 `azbatch-platform`；`Modelled, needs a real account` 的列數由 11 改 10；`## F. Compute environments (13 items)` 與 `KINDS` 必須出現在 PLATFORM.md 的斷言不動；全綠 | 自動：`platform/tests/test_station_docs.py` |
| TC-140 | 必須更新的既有斷言（`test_launch_cli.py`） | 功能 | 無 | 跑 `test_launch_cli.py` 中雲端類型 launch 被拒的測試 | 改用 `azcloud-platform`（設定 `{"workDir":"az://bucket/work","instanceType":"Standard_D4s_v3"}`）；rc、`尚未支援\|not supported`、雲端工具紀錄為空這些斷言不動；全綠 | 自動：`platform/tests/test_launch_cli.py` |
| TC-141 | 裁決 11（`test_launch_bundle.py`） | 功能 | 無 | 跑 `test_launch_bundle.py` 的「另一種類型被拒」測試 | 把 `azbatch-platform` 換成仍 unsupported 的類型（例如 `azcloud-platform`）；斷言不動；全綠 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-142 | 裁決 11（`test_gcb_launch.py`） | 功能 | 無 | 跑 `test_gcb_launch.py` 中 PLATFORM.md 句子的測試 | 只把 eleven 改 ten（及 Azure 一句，與 TC-117 的新句一致）；其餘不動；全綠 | 自動：`platform/tests/test_gcb_launch.py` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-143 | 平台不啟動任何程式（`test_scope.py` TC-071）；環境事實 | 功能 | 無 | 掃 `abf_platform/` | 底下沒有 `subprocess`；啟動 `az` 只發生在 `abf_station/`，經固定參數、無 shell 的 `site.run_fixed` | 自動：`platform/tests/test_scope.py`（TC-071）與同檔（`test_the_platform_package_starts_no_program`） |
| TC-144 | Safety Net 憑證條 | 功能 | 無 | 跑 `tests/credentials_stay_in_settings_test.sh` | 通過：新增的測試與文件沒有完整金鑰字面（測試金鑰用拼接組出） | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-145 | Safety Net 憑證條的平台半（`test_secrets.py`） | 功能 | 無 | 跑 `platform/tests/test_secrets.py` | 通過：新類型沒有開出讓憑證存進平台的路徑 | 自動：`platform/tests/test_secrets.py` |
| TC-146 | `test_scope.py` TC-070（新檔標頭） | 功能 | 無 | 看新增的 `azure_preflight.py` 與 `test_azure_ce.py` 前 40 行 | 各有 `# Nothing existing: <具體理由，≥15 字>`（理由說明搜過 Nextflow `azurebatch` 與 Seqera 的 Azure Batch 表單沒有離線又不計費的預檢、官方 Python 套件被「不引入雲端 SDK」擋掉所以用 `az`） | 自動：`platform/tests/test_scope.py`（TC-070） |
| TC-147 | 專長守則（對等性） | 功能 | 無 | 同時列舉使用者看得到的動作（命令列 `ce` 子命令、MCP 工具、網頁路由）與動作層函式，兩邊比對 | 兩邊一一對應；Azure 沒有新增只在其中一邊存在的動作；`cli.py` 沒有自己的第二份驗證邏輯（驗證在 `compute_envs`） | 自動：`platform/tests/test_actions_layer.py`、`platform/tests/test_web_parity.py` |
| TC-148 | 專長守則（確認管道） | 功能 | 無 | 檢查 Azure 帶來的寫入路徑 | 沒有新的寫入入口：`ce create／update／disable` 沿用既有管理者命令列；所有會真的動 Azure 的工作種類都被拒（TC-103）；MCP 工具與網頁路由數量不變（TC-129） | 自動：`platform/tests/test_azure_ce.py` |
| TC-149 | 專長守則（錯誤訊息要有原因與處理方式） | 例外 | 無 | 逐一引發：缺 agent、缺憑證檔、沒裝 `az`、非預檢工作被拒、舊鍵被拒 | 每則訊息都講發生什麼事，也講下一步該做什麼（指定 `--agent`／放檔到路徑並 `chmod 600`／裝 `az`／等 azure-launch／刪除後重建） | 自動：`platform/tests/test_azure_ce.py` |
| TC-150 | 專長守則（不露堆疊、內部路徑、SQL） | 例外 | 無 | 看上列所有錯誤與預檢回報 | 沒有堆疊、SQL；沒有內部路徑——唯一例外是「缺憑證檔」那一則可寫出應放檔案的路徑 | 自動：`platform/tests/test_azure_ce.py` |
| TC-151 | 專長守則（日誌與回應不含密鑰） | 例外 | 憑證檔含 `BKEY`、`SKEY`；跑完建立、預檢成功、預檢失敗各一次 | 逐位元組搜尋資料庫、工作表（含 args、結果）、所有命令列輸出與日誌 | 找不到 `BKEY`、`SKEY` 的任何片段 | 自動：`platform/tests/test_azure_ce.py` |
| TC-152 | 專長守則（資料結構）；作法 13 | 功能 | 一份 base 版本建出的資料庫（含舊 Azure 記錄與其他類型記錄） | 用新版本開啟並列出 | 不需要 migration：沒有新增 migration 檔、資料表結構不變、舊記錄都照常讀得出來；`status` 仍只有既有五種值 | 自動：`platform/tests/test_azure_ce.py` |
