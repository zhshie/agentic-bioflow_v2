# 測試案例：Google Batch 計算環境（gcb-ce-type，依裁決二重做）

**規格**：`specs/gcb-ce-type/plan.md`（本功能沒有 spec.md，計畫即規格；以裁決二 F–K 為最高）　**總覽**：`test-case-overview.md`

白話說明（給非工程師）：
- 「計算環境」＝使用者登記的一個「可以在哪裡跑分析」的設定。這次新增一種：Google Cloud Batch（簡稱 gcb）。
- 「預檢」＝在不花錢、不真的跑分析的前提下，檢查這個環境設定得對不對、連不連得上。
- 「站台代理」＝裝在某台電腦上、替平台去做事的小程式。依裁決二，gcb 的預檢由「跑在平台主機上的那個代理」執行，平台本身不啟動任何程式。
- 「金鑰檔」＝Google 服務帳號的 JSON 憑證檔。它只放在代理那台電腦的檔案裡；資料庫只記「憑證的名字」。
- 本檔所有「金鑰文字」的測試資料，一律在測試裡用字串拼接組出，不在任何檔案寫出私鑰標頭的字面（裁決 J）。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

「自動」的測試寫在 `platform/tests/test_gcb_ce.py`（新檔），除非另註明；所有 gcloud 呼叫一律用假的 runner、假的 which，不碰網路。

## User Story 1 — 建立 Google Batch 環境並驗證設定（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1、2；完成標準 | 功能 | 有一個已登記的站台代理；合法設定含 project、location、workDir 與所有選填鍵（spot、bootDiskSize、bootDiskImage、serviceAccountEmail、network、subnetwork、usePrivateAddress、labels、maxvCpus） | 建立 `googlebatch-platform` 環境 | 建立成功；狀態是 `creating`，訊息是「等待第一次預檢」；不是 `unsupported` | 自動：`test_a_valid_google_batch_environment_is_created_as_creating` |
| TC-002 | 作法 2（workDir） | 功能 | 同 TC-001，workDir 寫 `gs://lab-bucket/work/` | 建立後讀回設定 | 設定原樣回來，只有 workDir 的結尾斜線被去掉（`gs://lab-bucket/work`） | 自動 |
| TC-003 | 作法 2（project 必填） | 例外 | 設定缺 `project` | 建立 | 被拒，錯誤訊息點名 `project` | 自動：`test_project_location_and_workdir_are_required` |
| TC-004 | 作法 2（location 必填） | 例外 | 設定缺 `location` | 建立 | 被拒，訊息點名 `location` | 自動 |
| TC-005 | 作法 2（workDir 必填） | 例外 | 設定缺 `workDir` | 建立 | 被拒，訊息點名 `workDir` | 自動 |
| TC-006 | 作法 2（workDir 形狀） | 例外 | 其他設定合法 | 分別把 workDir 設成 `/data/work`、`s3://b/x`、`gs://`、`gs://UPPER/x`、`gs://b/../x` | 這五個每一個都被拒 | 自動：`test_workdir_must_be_a_gs_url` |
| TC-007 | 作法 2（workDir 形狀） | 功能 | 其他設定合法 | workDir 設成 `gs://lab-bucket/work/` | 被接受 | 自動 |
| TC-008 | 作法 2（project 規則） | 例外 | 其他設定合法 | project 設成大寫開頭的 `Lab-Project`、只有 5 個字的 `abcde`、結尾是連字號的 `lab-project-` | 每一個都被拒，訊息點名 `project` | 自動 |
| TC-009 | 作法 2（location 規則） | 例外 | 其他設定合法 | location 設成 `Europe_West2`；對照 `europe-west2` 被接受 | `Europe_West2` 被拒、訊息點名 `location`；`europe-west2` 通過 | 自動 |
| TC-010 | 作法 2（spot 布林） | 例外 | 其他設定合法 | spot 設成字串 `"yes"` | 被拒，訊息點名 `spot`；設成 true 則被接受 | 自動 |
| TC-011 | 作法 2（bootDiskSize） | 功能 | 其他設定合法 | bootDiskSize 分別設 `50 GB` 與 `50GB` | 兩種寫法都被接受 | 自動 |
| TC-012 | 作法 2（bootDiskSize） | 例外 | 其他設定合法 | bootDiskSize 分別設 `0 GB`、`2001 GB`、`50` | 三個都被拒，訊息點名 `bootDiskSize` | 自動 |
| TC-013 | 作法 2、3（serviceAccountEmail） | 功能 | 其他設定合法 | serviceAccountEmail 設 `runner@lab-project-1.iam.gserviceaccount.com` | 被接受；它是信箱，不被當成祕密而擋下 | 自動：`test_service_account_email_is_a_plain_email_not_a_secret` |
| TC-014 | 作法 2（serviceAccountEmail） | 例外 | 其他設定合法 | serviceAccountEmail 設 `not-an-email` | 被拒，訊息點名 `serviceAccountEmail` | 自動 |
| TC-015 | 作法 2（labels） | 例外 | 其他設定合法 | labels 分別給：大寫字母開頭的鍵、超過 63 字的值、65 組標籤、非物件 | 每一個都被拒，訊息點名 `labels` | 自動 |
| TC-016 | 作法 2（maxvCpus） | 例外 | 其他設定合法 | maxvCpus 分別設 0、10001、`"many"` | 都被拒，訊息點名 `maxvCpus`；設 10000 則被接受 | 自動 |
| TC-017 | 作法 2；裁決 6 | 功能 | 其他設定合法 | maxvCpus 設 100，建立後讀回 | 值原樣存起來並讀回（本片只存、不驗證它與 Nextflow 的對應） | 自動 |
| TC-018 | 作法 2（network／subnetwork） | 例外 | 其他設定合法 | network 設 `Bad Name`、subnetwork 設含空白的字串 | 都被拒，訊息點名該鍵；`default` 與 `projects/p1/global/networks/n1` 的形式則被接受 | 自動 |
| TC-019 | 作法 2（未知鍵） | 例外 | 其他設定合法 | 分別加入鍵 `headQueue`、`hostName`、`foo` | 每一個都被拒，訊息寫 `unknown setting for a Google Batch environment: <鍵>` 並列出已知鍵（known: …） | 自動：`test_unknown_and_slurm_keys_are_refused` |
| TC-020 | 作法 2（全部錯誤一次列出） | 例外 | 同時把 `project`、`spot`、`bootDiskSize` 都設錯 | 建立 | 只有一則拒絕訊息，同時含這三個鍵名 | 自動：`test_all_errors_are_listed_at_once` |
| TC-021 | 作法 2（不回顯被拒的值） | 例外 | project 設成一個 200 字的錯誤字串 | 建立 | 被拒；訊息裡沒有那 200 字全文（值最多顯示 60 字） | 自動 |
| TC-022 | 裁決 G；作法 6 | 例外 | 設定合法，但建立時沒有指定 agent | 建立 gcb 環境 | 被白話拒絕，說明 gcb 環境需要指定一個站台代理（平台主機上的那個）；不會自動補代理（自動補代理只對 Slurm 生效） | 自動 |
| TC-023 | 作法 2（共用檢查） | 例外 | 其他設定合法 | `environment` 放入 Slurm 環境同樣會拒的壞項目 | 同樣被拒（沿用共用檢查）；合法的 `nextflowConfig`、`preRunScript`、`postRunScript` 被接受 | 自動 |

## User Story 2 — 舊的 googlebatch 紀錄不壞、能升級（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | 裁決 C | 功能 | 資料庫裡有一筆以前建立的 `googlebatch-platform` 舊列（狀態 `unsupported`、沒有 project） | `ce list`、`ce show` | 照舊顯示，狀態仍是 `unsupported`，不報錯 | 自動 |
| TC-025 | 裁決 C | 例外 | 同 TC-024 | `ce update` 該舊列但沒補 project、location、workDir | 被拒，訊息說明要補哪些欄位；舊列內容沒變 | 自動 |
| TC-026 | 裁決 C、K | 功能 | 同 TC-024；有一個代理 | `ce update` 補齊必填欄位與 agent | 通過新規則；狀態從 `unsupported` 變成 `creating`，再由預檢決定 `available` 或 `invalid` | 自動 |
| TC-027 | 裁決 C | 例外 | 同 TC-024 | 直接 `ce preflight` 該舊列 | 先過新規則，不通過就被拒並說明要補欄位；沒有排任何工作 | 自動 |
| TC-028 | 裁決 E | 例外 | 一個已被停用（disabled）的 gcb 環境 | `ce update` 它 | 設定照新規則更新，但不排預檢工作（jobs 表列數不變） | 自動 |

## User Story 3 — 憑證只放名字，金鑰不進資料庫（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 維護者原話第 40 行「架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）」；作法 3 | 功能 | 設定合法 | 建立時帶 `--credentials gcp-lab`（頂層欄位 `credentialsId`），再 `ce show` | 憑證與環境分開：環境只記名字 `gcp-lab`，沒有新增 `credentialName` 設定鍵 | 自動 |
| TC-030 | 作法 3 | 例外 | 設定合法 | `credentialsId` 分別給含空白的字串、含 `=` 的字串、很長的金鑰形字串 | 每一個都被拒（沿用現有的名字規則） | 自動：`test_credentials_id_is_a_name_only` |
| TC-031 | 作法 3 | 例外 | 設定合法 | 把一段 PEM 私鑰開頭標頭開頭的文字（測試內拼接組出）分別貼進 `description`、`nextflowConfig`、`environment` 的某個值、`labels` 的某個值 | 這四處每一處都被拒 | 自動：`test_a_private_key_pasted_anywhere_is_refused_and_not_repeated` |
| TC-032 | 作法 3 | 例外 | 同 TC-031 | 看被拒時的錯誤訊息 | 訊息只講欄位路徑（例如哪個欄位），不含那段金鑰文字 | 自動 |
| TC-033 | 憲法安全網（平台不存收到的憑證）；作法 3 | 例外 | 同 TC-031，且已有被拒的嘗試 | 把資料庫檔整份以位元組讀出比對 | 找不到那段金鑰文字，也沒有金鑰檔路徑以外的金鑰內容 | 自動 |
| TC-034 | 作法 3 | 例外 | 設定合法 | 設定裡放鍵名 `privateKey`、`serviceAccountKey` | 兩個都被「鍵名像祕密」的檢查擋下 | 自動：`test_a_key_named_field_is_refused` |
| TC-035 | 維護者原話第 52 行「雲端憑證放平台主機檔案（不進資料庫）」；裁決 H | 功能 | 在代理預設的金鑰檔位置放一個含唯一標記字串的假金鑰檔；平台與代理在同一個測試裡跑 | 建立環境、跑完預檢、讀平台程式原始碼與資料庫 | 平台程式（`abf_platform/`）沒有讀金鑰檔的程式，也沒有 `gcp_credentials_file` 這個函式；唯一標記字串不在資料庫、不在任何預檢回傳 | 自動 |
| TC-036 | 完成標準（手動）；維護者原話第 52 行 | 功能 | 維護者已把服務帳號 JSON 放到代理那台電腦的指定位置（權限 600） | 照 `docs/TESTING.md`「gcb-ce-type」小節建立環境並預檢通過後，在 `ce show` 輸出與 `platform.db` 裡搜金鑰檔的任何片段 | 搜不到金鑰的任何片段 | 手動：`docs/TESTING.md` |

## User Story 4 — 預檢經由站台代理執行，不計費（優先度 P1）

預檢的八個檢查名固定為：`credential_name`、`credential_file`、`credential_shape`、`credential_project`、`service_account`、`gcloud`、`batch_api`、`bucket`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | 裁決 F、G；作法 6 | 功能 | 一個在線的站台代理（假的）；合法 gcb 設定且 agent 指向它 | `ce create --platform googlebatch-platform …` | 平台排入一個預檢工作給該代理（jobs 表多一列），輸出說預檢已排入；環境停在 `creating`，等代理回報 | 自動：`test_cli_create_runs_the_first_preflight_for_google_batch`（依裁決二改寫） |
| TC-038 | 裁決 G；作法 6（沿用 slurm 的路徑） | 例外 | agent 指向的代理離線 | `ce create` | 建立成功，訊息說「沒有代理在線，尚未預檢」；環境仍是 `creating`，沒有假裝通過 | 自動 |
| TC-039 | 作法 6 | 功能 | 一個在線的代理；既有 gcb 環境 | `ce preflight <名>` | 排工作給代理、等回報，逐項印出 `名稱: 狀態 - 說明`，最後印出環境狀態 | 自動 |
| TC-040 | 作法 5 | 功能 | 代理端 `run_preflight` 注入假 runner、假 which | 對一個合法環境跑預檢 | 回傳 `ok` 與 `checks`，八個檢查名都出現，每項有 name、status、detail | 自動 |
| TC-041 | 作法 5（credential_name） | 例外 | 環境沒有設憑證名字 | 預檢 | `credential_name` 為 fail，說明要「給這個環境一個憑證名字」 | 自動 |
| TC-042 | 作法 5；裁決 D | 例外 | 代理端沒有金鑰檔 | 預檢 | `credential_file` 為 fail；說明裡寫出應放的路徑與一句怎麼放（這是終端機管理者指令，路徑不是祕密，為許可的例外） | 自動：`test_preflight_reports_a_missing_credential_file_with_where_to_put_it` |
| TC-043 | 作法 5；裁決 K | 功能 | 同 TC-042 | 預檢並套用結果 | 環境變成 `invalid`；不需要檔案的檢查（例如 `credential_name`）仍有結果 | 自動 |
| TC-044 | 裁決 K | 例外 | 同 TC-042 | 看 `credential_shape` 與 `credential_project` | 兩項都是 `unchecked`（沒檔就沒辦法檢查），不是 fail 也不是 pass | 自動 |
| TC-045 | 作法 5（POSIX 權限） | 例外 | 非 Windows；金鑰檔權限 0644 | 預檢 | `credential_file` 為 fail，說明提到權限（別人可讀寫） | 自動（Windows 上略過）：`test_preflight_refuses_a_world_readable_credential_file` |
| TC-046 | 作法 5（POSIX 權限） | 功能 | 非 Windows；金鑰檔權限 0600 | 預檢 | `credential_file` 為 pass | 自動（Windows 上略過） |
| TC-047 | 作法 5（Windows） | 功能 | 在 Windows 上；金鑰檔存在 | 預檢 | 不檢查權限位，`credential_file` 的說明寫「Windows 不檢查權限位」 | 自動（僅 Windows 上執行） |
| TC-048 | 作法 5（credential_shape） | 例外 | 金鑰檔缺 `client_email` 鍵 | 預檢 | `credential_shape` 為 fail，說明只講缺哪個鍵（`client_email`），不印任何值 | 自動：`test_preflight_checks_the_shape_of_the_key_file_without_printing_it` |
| TC-049 | 作法 5（credential_shape） | 例外 | 金鑰檔的 `type` 不是 `service_account` | 預檢 | `credential_shape` 為 fail，說明只講鍵名與期待的型態，不印金鑰值 | 自動 |
| TC-050 | 作法 5；專長守則（日誌與回應不含密鑰） | 例外 | 金鑰檔每個欄位都含唯一標記字串 | 跑預檢（含失敗情況）並讀 `checks` 的整份 JSON、環境的 `message`、工作結果 | 任何地方都找不到那些唯一標記字串 | 自動 |
| TC-051 | 作法 5（credential_project） | 例外 | 金鑰檔內的 `project_id` 與環境的 `project` 不同 | 預檢 | `credential_project` 為 fail；說明同時顯示兩個專案 ID（專案 ID 不是祕密） | 自動：`test_preflight_project_in_file_must_match_the_environment` |
| TC-052 | 作法 5（service_account） | 功能 | 環境沒設 `serviceAccountEmail` | 預檢 | `service_account` 為 pass，說明「用 Compute Engine 預設帳號」 | 自動 |
| TC-053 | 作法 5；裁決 8 | 功能 | 環境設了 `serviceAccountEmail`，與金鑰檔的 `client_email` 不同，但形狀正確 | 預檢 | `service_account` 為 pass（不要求兩者相同） | 自動 |
| TC-054 | 作法 5（gcloud） | 例外 | 假 which 回 None（機器上沒有 gcloud） | 預檢 | `gcloud` 為 `unchecked`（不是 fail）；`batch_api`、`bucket` 也是 `unchecked` | 自動：`test_preflight_without_gcloud_leaves_api_checks_unchecked` |
| TC-055 | 作法 5；裁決 4 | 例外 | 同 TC-054，其他檢查全 pass | 預檢並套用結果 | 環境停在 `invalid`（不是 `available`）；訊息明說缺 gcloud | 自動 |
| TC-056 | 作法 5；維護者原話第 50 行 | 例外 | 同 TC-054 | 預檢 | 假 runner 被呼叫 0 次（沒有 gcloud 就不碰任何外部命令） | 自動 |
| TC-057 | 作法 5；完成標準 | 功能 | 假 runner 一律回 0；金鑰檔正確；有 gcloud | 預檢並套用結果 | 八項全部 pass；環境 `status == "available"`、`checked_ok == 1`；結果走和 Slurm 相同的記錄路徑 | 自動：`test_preflight_all_pass_makes_the_environment_available` |
| TC-058 | 作法 5（batch_api） | 例外 | 假 runner 對 batch_api 回 rc 1 與 2000 字輸出（其中夾一段像金鑰的字串） | 預檢 | `batch_api` 為 fail；說明不超過 300 字；不含那段像金鑰的片段；環境 `invalid` | 自動：`test_preflight_batch_api_failure_is_reported_and_trimmed` |
| TC-059 | 作法 5（bucket） | 例外 | 假 runner 對 bucket 回 rc 1 與 2000 字含金鑰形片段的輸出 | 預檢 | `bucket` 為 fail；說明不超過 300 字；不含金鑰形片段 | 自動 |
| TC-060 | 裁決 E | 例外 | 假 runner 對 batch_api 模擬逾時 | 預檢 | `batch_api` 為 fail，說明裡寫「逾時」；其他項照常有結果 | 自動 |
| TC-061 | 裁決 E | 功能 | 記錄每次 runner 收到的逾時值 | 預檢 | 每一次 gcloud 呼叫的逾時都是 30 秒 | 自動 |
| TC-062 | 作法 5（batch_api） | 功能 | 記錄 runner 收到的 argv | 預檢（專案 P、區域 L） | 其中一條是 `gcloud batch jobs list --project P --location L --limit 1 --format value(name)`，內容與計畫逐字相同 | 自動 |
| TC-063 | 作法 5（bucket） | 功能 | 記錄 runner 收到的 argv | 預檢（workDir 為 `gs://lab-bucket/work`） | 其中一條是 `gcloud storage ls gs://lab-bucket/ --project P`（只列頂層、不寫入） | 自動 |
| TC-064 | 維護者原話第 16、50 行；作法 5（不計費） | 例外 | 記錄預檢期間所有 runner 的 argv | 預檢 | 每一條都以 `gcloud batch jobs list` 或 `gcloud storage ls` 開頭；任何一條都不含 `create`、`submit`、`delete`、`cp`、`rm`、`mb`、`enable` 這些字（保證不建 job、不寫 bucket、不花錢） | 自動：`test_preflight_only_runs_read_only_commands` |
| TC-065 | 裁決 B；作法 5 | 例外 | 記錄所有 runner 的 argv 與 env | 預檢 | 每一次 gcloud 呼叫的 env 都帶 `CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE`＝同一個金鑰檔路徑，且 `CLOUDSDK_CORE_DISABLE_PROMPTS=1`；金鑰檔路徑不在任何 argv 裡 | 自動：`test_preflight_passes_the_credential_through_the_environment_not_argv` |
| TC-066 | 裁決 B | 例外 | 代理的程序環境裡刻意放 `ABF_PLATFORM_TOKEN` 之類的 `ABF_` 開頭變數 | 預檢 | 傳給 runner 的 env 沒有任何 `ABF_` 開頭的變數（對 `GOOGLE_APPLICATION_CREDENTIALS` 不下斷言） | 自動 |
| TC-067 | 作法 5（預設 runner） | 功能 | 把 `subprocess.run` 換成會記錄參數的假物件 | 用預設 runner 跑一次 | 以固定 argv 呼叫、不經 shell（`shell=False`）、帶逾時；回傳的輸出尾巴不超過 300 字 | 自動 |
| TC-068 | 裁決 H；作法 4（改由代理端決定） | 功能 | 代理端有一個文件記載的金鑰檔位置設定（名稱由 executor 選定並寫進 `docs/PLATFORM.md`）；指向一個不存在的路徑 | 預檢 | `credential_file` 的失敗說明寫出的就是該設定指定的路徑；沒設定時是文件寫的預設位置 | 自動 |
| TC-069 | 維護者原話第 50 行「雲端第一個真實使用者＝他自己的自費帳號」；完成標準（手動） | 功能 | 維護者自己的 GCP 帳號；金鑰檔已放好；代理跑在同一台主機 | 照 `docs/TESTING.md`「gcb-ce-type」小節建立環境、等預檢完成；再到 Google Cloud 主控台看 Batch 的工作清單 | 每項檢查都顯示；全部 pass 時 `ce show` 顯示 `available`；主控台沒有任何新增的 Batch 工作，也沒有產生費用 | 手動：`docs/TESTING.md` |

## User Story 5 — 送出一律不放行、擁有者規則不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 作法 7；裁決 G | 例外 | 一個 gcb 環境（狀態 `available`，有 agent） | 分別對它排 `list_site_files`、`launch_nextflow`、`cancel_run`、`fetch_run_records`、`read_task_log` | 五種都被白話拒絕，訊息含「尚未支援送出」與 `C-2`；沒有排入任何工作 | 自動：`test_agent_jobs_on_a_google_batch_environment_are_refused_in_plain_words`（依裁決二，不含預檢） |
| TC-071 | 作法 7 | 例外 | 同 TC-070 | 看上述五個拒絕訊息 | 都不含「set an agent」「has no agent」這類誤導（拒絕放在「沒有代理」檢查之前） | 自動 |
| TC-072 | 作法 9 | 例外 | 一個 `available` 的 gcb 環境 | 用 launch 的目標檢查（`build.target_problem`）看它 | 回傳一句白話拒絕（不是 None），說明尚未支援送出 | 自動：`test_launch_on_a_google_batch_environment_is_refused_not_misrouted` |
| TC-073 | 作法 9 | 功能 | 一個 `available` 的 gcb 環境 | `ce primary <名>` | 可以被設成 primary | 自動 |
| TC-074 | 作法 9 | 例外 | 資料庫裡只有一個 `available` 的 gcb 環境（沒有 Slurm） | 呼叫 `primary_environment` 的自動選擇 | 回傳 None（自動選仍只選 Slurm，不會自動把人送進還沒做的路徑） | 自動：`test_primary_environment_never_auto_picks_google_batch` |
| TC-075 | 作法 8；專長守則（跨使用者，讀） | 例外 | 使用者 A 建了一個 gcb 環境 | 使用者 B 以自己的身分取 A 的環境 | 回傳找不到（None／not found），與 Slurm 環境相同 | 自動：`test_another_users_google_batch_environment_is_not_found` |
| TC-076 | 作法 8；專長守則（跨使用者，寫） | 例外 | 同 TC-075 | 使用者 B 以自己的身分修改、停用或對 A 的 gcb 環境排工作 | 被當成找不到而拒絕；A 的環境內容與 jobs 表沒變 | 自動 |
| TC-077 | 作法 8；專長守則（對等性） | 功能 | 本功能完成後 | 列舉 MCP 工具名與網頁路由 | 工具數仍是 12、沒有新增網頁路由（預檢是終端機管理者指令）；對等性清單與動作層函式清單仍一一對應 | 自動：`test_tool_list_unchanged_and_no_new_web_route`（讀 `test_estimate_su.py::test_tc029` 同一組） |
| TC-078 | 專長守則（錯誤訊息） | 例外 | TC-003 至 TC-022、TC-070 的各種拒絕 | 逐一看訊息 | 每則都說明發生什麼事與怎麼處理；不含堆疊追蹤、SQL；除 `credential_file` 失敗說明的應放路徑（裁決 D）外，不含平台內部路徑 | 自動 |

## User Story 6 — 不在範圍（本片明確不做）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-079 | 不做第 1 條（不送出／取消；C-2） | 不在範圍 | 本功能完成後 | 搜尋 `platform/` 原始碼與檔案清單；再對 gcb 環境嘗試 launch | 沒有 `local_runner.py`、`_local_head`、`head.pid`、`-with-tower` loopback 的程式；launch 被明白拒絕並指向 C-2，沒有在 Google Batch 上送出或取消任何東西 | 自動 |
| TC-080 | 不做第 2 條；維護者原話第 16、46 行「顯示雲端自己的幣別（美元）、不換算」 | 不在範圍 | 設定合法 | 設定裡加入 `usd`、`cap`、`budgetTWD`（台幣）等費用鍵；並檢查檔案清單 | 這些鍵都被當未知鍵拒絕（沒有任何台幣或美元欄位）；沒有 `cloud_cost.py`、`configs/cloud/rates.json`；沒有 bucket 上傳或刪除 work 的程式 | 自動 |
| TC-081 | 不做第 3 條 | 不在範圍 | 本功能完成後 | 比對 base 與 HEAD 的 MCP 工具、網頁路由、畫面檔與 `hello` 回傳 | 沒有新增工具、路由、畫面；`hello` 的回傳內容與 base 相同 | 自動 |
| TC-082 | 不做第 4 條 | 不在範圍 | 本功能完成後 | 建立另外 12 種型別（如 `awsbatch-platform`、azure、k8s）各一個 | 每一個仍是 `unsupported`，並明白說不支援；不是 `creating` | 自動 |
| TC-083 | 不做第 5 條前半；裁決 F | 不在範圍 | 本功能完成後 | 讀 `platform/pyproject.toml` 與 `abf_platform/`、`abf_station/` 全部原始碼 | 沒有 `google-cloud*`、`google-auth`、`boto3`、`azure` 的依賴或 import；`abf_station/gcb_preflight.py` 沒有 `import google`、`boto3`、`azure`、`requests` | 自動：`test_no_cloud_library_is_imported`（檔案位置依裁決二） |
| TC-084 | 不做第 5 條後半 | 不在範圍 | 本功能完成後 | 搜尋原始碼 | 沒有建立 bucket、啟用 API、建立服務帳號的程式或 gcloud 指令 | 自動 |
| TC-085 | 不做第 6 條；裁決 7 | 不在範圍 | 金鑰檔的 `type` 是 `external_account`（Workload Identity Federation 形） | 預檢 | `credential_shape` 為 fail，環境 `invalid`；明白表示只支援服務帳號金鑰檔 | 自動 |
| TC-086 | 不做第 7 條 | 不在範圍 | 設定合法 | 分別加入鍵 `wave`、`fusion`、`instanceTemplate`、`gpu` | 每一個都被當未知鍵拒絕並列出已知鍵 | 自動 |
| TC-087 | 作法 11 | 不在範圍 | 一個用 base 建立的舊資料庫（含一筆 slurm 環境） | 用新程式開啟並讀取；比對 `compute_envs` 資料表的欄位 | 資料表欄位與 base 相同、沒有新增 migration 檔；舊紀錄仍可讀；`status` 仍只有既有的五種值 | 自動 |

## User Story 7 — 既有行為不變與文件（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-088 | 作法 6；回歸 | 功能 | 一個 Slurm 環境與在線代理 | `ce create` Slurm | 仍排入 `preflight` 工作給它的代理，行為與 base 相同 | 自動：`test_slurm_still_queues_a_job_for_its_agent` |
| TC-089 | 作法 1；裁決 1；維護者原話第 166 行 | 功能 | 本功能完成後 | 讀 `compute_envs` 的常數 | `SUPPORTED` 仍是字串 `"slurm-platform"`；`PLATFORM_HOST_TYPES == ("googlebatch-platform",)`；`CHECKABLE == (SUPPORTED, "googlebatch-platform")`；既有用 `==` 比較 `SUPPORTED` 的地方行為不變 | 自動 |
| TC-090 | 作法 6（_default_agent） | 功能 | 一個 Slurm 環境不指定 agent | `ce create` | 仍自動補上預設代理（行為不變）；gcb 不套用這個預設（見 TC-022） | 自動 |
| TC-091 | 必須更新的既有斷言 | 功能 | 更新後的 `test_station_envs.py` | 跑 TC-030 | 函式名與註解改為 twelve；其餘 12 種型別（不含 googlebatch）逐一建立，狀態都是 `unsupported`；`UNSUPPORTED` 字典剩 12 筆 | 自動：`platform/tests/test_station_envs.py` TC-030 |
| TC-092 | 必須更新的既有斷言 | 功能 | 更新後的 `test_station_envs.py` | 跑 TC-032 | `len(KINDS) == 14` 不變；`set(UNSUPPORTED) ∪ {"slurm-platform", "googlebatch-platform"}` 等於 `KINDS` | 自動：同上 TC-032 |
| TC-093 | 必須更新的既有斷言 | 功能 | 更新後的 `test_station_docs.py` | 跑 TC-077 | 除 googlebatch 外每個非 Slurm 型別的 parity 列都寫 `Modelled, needs a real account`；googlebatch 那列寫 `Have (create + check); launch in C-2`；計數為 12；F 節標題仍是 `(13 items)` | 自動：`platform/tests/test_station_docs.py` TC-077 |
| TC-094 | 必須更新的既有斷言 | 功能 | 更新後的文件 | 跑 `test_station_docs.py` 的識別字檢查 | `docs/PLATFORM.md` 仍列出全部 14 個型別識別字；`len(KINDS) == 14` | 自動 |
| TC-095 | 必須更新的既有斷言；裁決 A(b) | 功能 | 實作完成 | 閱卷者執行 `git diff --name-only` 並逐個看既有測試檔的變更 | 既有測試只動計畫列的那幾處（`UNSUPPORTED` 與 TC-030、TC-032、TC-077 的斷言）；沒有其他被放寬、刪除或跳過的斷言；`test_station_e2e.py`、`test_tc096`、`test_estimate_su.py`、`test_pat.py`、`test_oauth_mcp.py`、`test_web_parity.py` 未被改動 | 手動：`docs/TESTING.md` |
| TC-096 | 作法 10 | 功能 | 實作完成 | 閱卷者讀 `docs/PLATFORM.md` 第 8 節型別表 | `googlebatch-platform` 的 Supported 欄是 `checked on the platform host (launch: not yet)`，並有一句「Only Slurm can run; Google Cloud Batch can be created and checked」 | 手動：`docs/TESTING.md` |
| TC-097 | 作法 10 | 功能 | 實作完成 | 跑文件檢查 | `docs/PLATFORM.md` 含作法 2 的每個鍵名、作法 5 的八個檢查名，以及代理端金鑰檔位置設定的名稱（TC-068 選定的那個） | 自動：`test_docs_list_every_gcb_key_and_check` |
| TC-098 | 作法 10；裁決 6；裁決 A(c) | 功能 | 實作完成 | 閱卷者讀 `docs/PLATFORM.md` 的 Google Cloud Batch 小節 | 小節有「預檢不計費」的說明（讀檔、列 API、列 bucket，不建任何 Batch job）；`maxvCpus` 旁註明「C-2 起生效」；說明憑證檔放在代理那台電腦、資料庫只存名字 | 手動：`docs/TESTING.md` |
| TC-099 | 作法 10 | 功能 | 實作完成 | 跑 TC-077 並讀 `docs/SEQERA_PARITY.md` F 節 | Google Cloud Batch 那列寫 `Have (create + check); launch in C-2`，勾選仍是 `[ ]`；F 節開頭「a type turns supported only after a run on a real account」那句沒變 | 自動：TC-077；勾選處為閱卷者讀檔 |
| TC-100 | 作法 10 | 功能 | 實作完成 | 閱卷者搜尋本次變更新增的文件與測試的範例 | 範例只出現 `lab-project-1`、`runner@lab-project-1.iam.gserviceaccount.com` 這類假值，沒有真實專案 ID 或信箱 | 手動：`docs/TESTING.md` |
| TC-101 | 裁決 A | 功能 | 實作完成 | 閱卷者讀 `docs/TESTING.md` | 有「gcb-ce-type」小節，含三件事：(a) 維護者放金鑰檔、跑 `ce create`、看到 `available`、全站搜不到金鑰片段的步驟；(b) 驗收者看 `git diff --name-only`、既有測試只動計畫列的幾處；(c) 指向 PLATFORM.md「預檢不計費」那句 | 手動：`docs/TESTING.md` |
| TC-102 | 裁決補充（新檔檔首標頭）；憲法原則 1 | 功能 | 實作完成 | 跑 `test_scope.py` 的 TC-070 | `abf_station/gcb_preflight.py` 與 `test_gcb_ce.py` 前 40 行內都有 `# Nothing existing: <理由，至少 15 字>`，理由具體說明搜過 Nextflow `google-batch` 與 Seqera 做法、官方 Python 套件被 TC-085 擋掉所以用 gcloud 命令列 | 自動：`platform/tests/test_scope.py` TC-070 |
| TC-103 | 完成標準（自動） | 功能 | 實作完成 | 在 WSL 跑全套 `tests/run_all.sh`，並確認 `tests/platform_test.sh` 的 REST 分片收入新測試檔 | 全套綠；新測試檔自動被收入；MCP 工具數仍 12 | 自動：`tests/run_all.sh`、`tests/platform_test.sh` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104 | 原則 2／裁決 F：平台本身不啟動任何程式 | 例外 | 實作完成 | 跑 `test_scope.py` 的 TC-071，並搜 `abf_platform/` | `abf_platform/` 底下沒有 `subprocess`、`os.system`、`Popen`；gcloud 只由 `abf_station/gcb_preflight.py` 呼叫；TC-071 沒有被放寬（與 base 相同的禁止清單） | 自動：`platform/tests/test_scope.py` TC-071 |
| TC-105 | 原則 2：不新增第二條送出路徑 | 例外 | 實作完成 | 跑 `tests/no_second_run_state_test.sh` | 通過；預檢只做列表（唯讀），沒有任何送出 | 自動：`tests/no_second_run_state_test.sh` |
| TC-106 | 安全網：憑證只放部署自己的設定區、不印出、不進 git；裁決 J | 例外 | 實作完成 | 跑 `tests/credentials_stay_in_settings_test.sh`，並搜本次變更的測試、文件與合約 | 通過；沒有任何檔案寫出 PEM 私鑰標頭的字面字串（測試內以字串拼接組出並註解原因） | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-107 | 安全網：平台不存收到的憑證 | 例外 | 實作完成 | 跑 `platform/tests/test_secrets.py` 的既有測試 | 通過且未被放寬；並配合 TC-033、TC-035 證明資料庫沒有金鑰內容 | 自動：`platform/tests/test_secrets.py` |
| TC-108 | 原則 3：不寫死個人路徑 | 例外 | 實作完成 | 跑 `tests/no_hardcoded_paths.sh` | 通過；範例路徑沒有 `/work/<真實帳號>/` | 自動：`tests/no_hardcoded_paths.sh` |
| TC-109 | 安全網：寫入工具須人工確認 | 例外 | 實作完成 | 跑 `test_actions_layer.py`、`test_human_channel.py`、`test_keep_submissions.py` 的既有確認管道測試；再對 gcb 環境嘗試 launch | 既有測試全綠且未被改動；本功能沒有新增任何寫入工具；對 gcb 環境的 launch 即使有人確認也被拒 | 自動：上述既有測試＋TC-072 |
