# 測試案例：在 Azure Batch 上送出與取消分析（azure-launch，C-2）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：本任務沒有 spec.md，以 `specs/azure-launch/plan.md`（含「維護者原話」逐字引文，以及文末「裁決與待裁決」與 developer-agent 裁決 1–13，與上文衝突時以文末為準）為規格。
IDs: TC-001..TC-157。每條只測一件事；驗證方式「自動」＝ `platform/tests/` 下的測試，並在測試內以註解 `# TC-nnn` 標明（計畫文內提到的 TC-070、TC-085 是專案既有測試的編號，與本檔編號無關；計畫裁決 12 所說的「合約 TC-136」就是本檔的 TC-136）。計畫列出的測試名稱（`AZL-…`）寫在驗證方式欄，沒有列名的由 executor 命名並以註解標明。
所有測試輸入都用假值：`labbatch`、`labstore`、`westeurope`、`lab-pool`、`az://labcontainer/work`、環境名 `azure1`；不碰網路、不啟動真程式、不花錢。
-->

**規格**：`specs/azure-launch/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「尚未支援」而不是悄悄亂做。

名詞：**主控程序**＝在平台主機上跑 Nextflow 的那個程式（Azure Batch 只負責算）；**站台代理**＝裝在平台主機上、本人答 y 之後才動手的程式；**pid**＝作業系統給程式的編號；**內容包**＝平台與代理各自用同一個函式建一次、必須完全相等的那組要送出的檔案；**放行**＝平台願意為某種環境排入某種工作；**SIGTERM**＝請程式自己結束的標準訊號；**head.sh**＝代理實際執行的啟動腳本；**pool**＝Azure Batch 裡事先建好的一群運算機器；**SAS**＝一種有期限的儲存體存取字串。

## User Story 1 — 本人答 y 之後，才在 Azure Batch 上送出一次分析（優先度 P1）

計畫目標：「沒有本人答 y 就不啟動」；交辦原話：「讓平台送出、追蹤、取消 Azure Batch 的 run，照 aws-launch 的做法」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 7；AZL-RUN-01 | 功能 | 一個 `available` 的 Azure 環境 `azure1`（pool `lab-pool`、`az://labcontainer/work`）、代理在線、有效確認憑證；憑證檔、Java、Nextflow、`az`、預檢都用假的通過 | 代理收到 `launch_nextflow` 工作 | 結果 `ok` 為真；訊息逐字格式為「已啟動：主控程序編號（pid）<pid>，run 名稱 <run>，專屬資料夾 <路徑>；Azure Batch 的工作與費用從現在開始計」，且含 Azure 帳單句 | 自動：`AZL-RUN-01 test_launch_writes_five_files_starts_one_detached_head_and_returns_pid` |
| TC-002 | 作法 7；裁決 11 | 功能 | 同 TC-001，假的 `start_detached` 回傳 pid | 送出成功 | 結果裡 `slurm_job_id` 等於該 pid（欄位名不改）；`head.pid` 檔內容也是同一個 pid | 自動：同 TC-001 |
| TC-003 | 作法 7；AZL-RUN-01 | 功能 | 同 TC-001，假的 `start_detached` 記下呼叫參數 | 送出成功 | 恰呼叫 1 次；argv 為 `["bash", "<run_folder>/head.sh"]`；cwd 是專屬資料夾；輸出檔是 `<run_folder>/head.out`；沒有用 shell | 自動：同 TC-001（看假 `start_detached` 的記錄） |
| TC-004 | 作法 3；AZL-BUNDLE-05 | 功能 | 同 TC-001，`tmp_path` 當 `storage_root` | 送出成功後看專屬資料夾 | 位置為 `<storage_root>/_azure_runs/<run 名稱>`，權限 700；結果訊息列的路徑就是它。代理沒回報 `storage_root` 時，建內容包白話拒絕並說明要設 `storage_root` | 自動：`AZL-BUNDLE-05 test_azure_run_folder_is_private_and_never_overwritten`（`storage_root` 缺失案例由 executor 命名並標 TC-004） |
| TC-005 | 作法 3；AZL-RUN-01 | 功能 | 同 TC-001 | 送出成功後看資料夾內容 | 有 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`azure.config`、`head.sh`、`tower.token`、`head.pid`、`head.out`；資料夾裡沒有結果檔 | 自動：同 TC-001 |
| TC-006 | 作法 7、11 | 功能 | 平台端走完 `take_result` | 代理回報成功結果 | `launches.slurm_job_id` 等於該 pid；平台沒有為此新增欄位 | 自動：`test_azure_launch.py`（註解標 TC-006） |
| TC-007 | 目標第 1 點；AZL-CONF-02 | 功能 | Azure 環境可用，使用者在送出指令上明講環境名字 | 從 `prepare_launch` 開始送出 | 依序經過 `prepare_launch` → 確認頁 → 排入 `launch_nextflow` → 代理領取驗證確認；沒有另一條送出路徑 | 自動：`AZL-CONF-02 test_a_person_must_say_yes_an_azure_launch_is_never_auto_queued` |
| TC-008 | 作法 3；AZL-BUNDLE-05 | 功能 | 同 TC-001 | 送出成功後看 `tower.token` | 檔案存在、權限 600，以「不得覆蓋」方式建立（已存在則失敗，不寫入） | 自動：同 TC-004 |
| TC-009 | 目標第 1 點；AZL-CONF-01 | 例外 | 代理收到 Azure 的 `launch_nextflow` 工作，但**沒有**確認憑證 | 代理處理該工作 | 結果 `refused`；`tmp_path` 下沒有任何新檔；`start_detached` 呼叫 0 次 | 自動：`AZL-CONF-01 test_unconfirmed_azure_launch_is_refused_and_nothing_is_written_or_started` |
| TC-010 | 同上 | 例外 | 有確認憑證但雜湊與內容包不符 | 代理處理 | `refused`；沒有新檔；`start_detached` 0 次 | 自動：同上 |
| TC-011 | 同上 | 例外 | 確認憑證已經用過一次 | 再送一次同一個工作 | `refused`；沒有新檔；`start_detached` 0 次 | 自動：同上 |
| TC-012 | 同上 | 例外 | 憑證的種類是 `cancel`（不是 `launch`） | 拿它去送出 | `refused`；沒有新檔；`start_detached` 0 次 | 自動：同上 |
| TC-013 | 目標；AZL-CONF-02 | 例外 | 對 Azure 環境發出送出要求 | 在人答 y 之前查 jobs 表 | 還沒有任何 `launch_nextflow` 工作被建立（不會自動排進佇列） | 自動：`AZL-CONF-02`（同 TC-007） |
| TC-014 | 目標；AZL-CONF-02 | 例外 | 同 TC-013 | 人答 n、或逾時、或取消 | jobs 表列數與送出前相同 | 自動：`AZL-CONF-02`（同 TC-007） |
| TC-015 | 作法 7（用自己的設定重建內容包並比對） | 例外 | 有效確認，但內容包的 `azure.config` 被改了一個字元 | 代理處理 | 代理重建內容包後發現不相等，拒絕；沒有新檔；`start_detached` 0 次 | 自動：`test_azure_launch.py`（註解標 TC-015） |
| TC-016 | 同上 | 例外 | 內容包的 pool 被改成別的 pool 名 | 代理處理 | 拒絕；沒有新檔；沒有啟動 | 自動：`test_azure_launch.py`（註解標 TC-016） |
| TC-017 | 同上 | 例外 | 內容包的 samplesheet 被改了一格 | 代理處理 | 拒絕；沒有新檔；沒有啟動 | 自動：`test_azure_launch.py`（註解標 TC-017） |
| TC-018 | 作法 3；AZL-BUNDLE-05 | 例外 | 專屬資料夾 `<storage_root>/_azure_runs/<run>` 已經存在 | 送出 | 拒絕、不覆蓋；原資料夾內容不變；`start_detached` 0 次 | 自動：`AZL-BUNDLE-05`（同 TC-004） |
| TC-019 | 作法 7；AZL-RUN-03 | 例外 | 假的主控程序啟動後在等待期間就結束，`head.out` 有內容 | 送出 | 結果 `error`；訊息含 `head.out` 結尾的片段；資料夾保留供查看 | 自動：`AZL-RUN-03 test_head_that_dies_during_settle_is_reported_with_its_log_tail` |
| TC-020 | 作法 7（工具檢查） | 例外 | 平台主機找不到 `java` | 送出 | 白話拒絕，說明缺 Java 與要裝什麼；沒有新檔；沒有啟動 | 自動：`test_azure_launch.py`（註解標 TC-020） |
| TC-021 | 作法 7；文件需求（Java 17+） | 例外 | Java 版本低於 17 | 送出 | 白話拒絕，說明需要 Java 17 以上；沒有新檔；沒有啟動 | 自動：`test_azure_launch.py`（註解標 TC-021） |
| TC-022 | 作法 7 | 例外 | 平台主機找不到 `nextflow` | 送出 | 白話拒絕，說明缺 Nextflow 與要裝什麼；沒有新檔；沒有啟動 | 自動：`test_azure_launch.py`（註解標 TC-022） |
| TC-023 | 作法 7；裁決 8；AZL-CRED-04 | 例外 | `which az` 找不到 | 送出 | 白話拒絕，說明缺 `az` 指令列工具與怎麼裝；沒有新檔；沒有啟動 | 自動：`AZL-CRED-04 test_az_cli_missing_stops_before_launch` |
| TC-024 | 作法 7（deadline） | 例外 | 工作期限剩餘低於門檻（與 Slurm、gcb、aws 同一個門檻） | 送出 | 拒絕；沒有新檔；沒有啟動 | 自動：`test_azure_launch.py`（註解標 TC-024） |
| TC-025 | 作法 7；AZL-RUN-02 | 例外 | 送出前重跑唯讀預檢（`azure_preflight.run_preflight`），假的 `run_fixed` 讓其中一項 fail | 送出 | 拒絕並顯示預檢的白話訊息；不建資料夾；`start_detached` 0 次 | 自動：`AZL-RUN-02 test_preflight_failure_blocks_the_launch` |
| TC-026 | 作法 7（`/proc`） | 例外 | 代理主機沒有 `/proc`（不是 Linux 或 WSL） | 送出 | 送出前白話拒絕，說明只支援 Linux 或 WSL；沒有新檔；沒有啟動 | 自動：`test_azure_launch.py`（註解標 TC-026） |
| TC-027 | 裁決 13（前後置腳本） | 例外 | 環境的 `preRunScript` 或 `postRunScript` 非空 | 準備送出 | 拒絕（與 AWS 版相同）；沒有新檔；沒有啟動 | 自動：`test_azure_launch.py`（註解標 TC-027） |
| TC-028 | 作法 3 | 例外 | 內容包的 `reach` 不是 `local`；另一份內容包含 `account` 鍵 | 建內容包／代理處理 | `reach` 非 `local` 的被拒；合法內容包不含 `account` | 自動：`test_azure_launch.py`（註解標 TC-028） |
| TC-029 | 環境事實（jobs.py 既有規則，GATE-01「可用的 Azure 環境」） | 例外 | Azure 環境狀態不是 `available`（例如 `creating`） | 對它排 `launch_nextflow` | 被拒，白話說明只有可用的環境才能送出；jobs 表列數不變 | 自動：`test_azure_launch.py`（註解標 TC-029） |

## User Story 2 — 內容包與設定檔（優先度 P1）

計畫作法 3、5、6：五個檔、`azure.config` 只寫官方文件查得到的鍵、自動建 pool 一律關、`head.sh` 最後一行是唯一的 `exec nextflow run`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 作法 3；AZL-BUNDLE-01 | 功能 | 合法環境：`batchAccountName=labbatch`、`storageAccountName=labstore`、`location=westeurope`、pool `lab-pool`、`workDir=az://labcontainer/work`、未設 `maxvCpus`；run 名稱 `r1` | 建內容包，看 `azure.config` 的鍵與值 | 鍵恰為：`process.executor = 'azurebatch'`、`process.queue = 'lab-pool'`、`workDir`、`azure.batch.accountName = 'labbatch'`、`azure.batch.location = 'westeurope'`、`azure.storage.accountName = 'labstore'`、`azure.batch.allowPoolCreation = false`、`azure.batch.autoPoolMode = false`，沒有別的設定鍵 | 自動：`AZL-BUNDLE-01 test_azure_config_has_exactly_the_documented_keys` |
| TC-031 | 作法 3 | 功能 | 同上 | 看 `workDir` | 為 `az://labcontainer/work/runs/r1/work`；兩個不同 run 名稱的 `workDir` 互不相同 | 自動：同上 |
| TC-032 | 作法 3 | 功能 | 同上但 `maxvCpus=16` | 看 `azure.config` | 多一行 `process.resourceLimits = [cpus: 16]`；未設 `maxvCpus` 時沒有這一行 | 自動：同上 |
| TC-033 | 作法 3 | 功能 | 兩個環境只差 `spot=true` 與 `spot=false` | 各建一份 `azure.config` | `spot` 只可能出現在註解行，不是設定鍵；兩份的設定鍵完全相同 | 自動：同上 |
| TC-034 | 作法 3、裁決 4 | 功能 | 同 TC-030 | 看 `azure.config` | `azure.batch.allowPoolCreation = false` 與 `azure.batch.autoPoolMode = false` 逐字存在，不是 `true`，也沒有被省略 | 自動：同上 |
| TC-035 | 作法 3 | 功能 | 同 TC-030 | 看 `azure.config` 開頭 | 有註解說明「金鑰由環境變數提供」，註解裡沒有任何金鑰值 | 自動：同上 |
| TC-036 | 作法 3、4；AZL-BUNDLE-02 | 例外 | 憑證檔放假金鑰（以字串拼接組出）與唯一路徑 | 建內容包後搜尋內容包全部欄位、`head.sh`、`azure.config`、`nextflow.config`、`params.yaml` | 搜不到假金鑰、SAS、憑證檔路徑 | 自動：`AZL-BUNDLE-02 test_azure_bundle_contains_no_credential_content` |
| TC-037 | 作法 4；AZL-BUNDLE-02 | 例外 | 同上 | 搜尋 `snapshot_ce` 的結果、資料庫的位元組、`ce show` 的輸出 | 搜不到假金鑰與憑證檔路徑 | 自動：同上 |
| TC-038 | 作法 5；AZL-BUNDLE-03 | 功能 | 合法內容包 | 看 `head.sh` 最後一行 | 恰一個 `exec nextflow run <pipeline> -r <rev> -name <run> -params-file params.yaml -c nextflow.config -c azure.config -with-tower <endpoint>`（`azure.config` 在後） | 自動：`AZL-BUNDLE-03 test_head_script_ends_with_one_exec_nextflow_run_with_both_configs_and_tower` |
| TC-039 | 目標第 2 點；AZL-BUNDLE-03 | 例外 | 掃描 `abf_platform/`、`abf_station/` 原始碼 | 搜尋 `nextflow run` | 只有 `launch.py` 有 | 自動：同 TC-038 |
| TC-040 | 作法 6；AZL-BUNDLE-04 | 功能 | samplesheet 路徑欄為 `az://labcontainer/x.fastq.gz`，`workDir` 的容器是 `labcontainer` | 建內容包 | 通過 | 自動：`AZL-BUNDLE-04 test_samplesheet_must_be_az_paths_in_the_workdir_container` |
| TC-041 | 作法 6 | 例外 | 路徑欄位是本機路徑 `/home/x.fastq.gz` | 建內容包 | 拒絕 | 自動：同上 |
| TC-042 | 作法 6 | 例外 | 路徑欄位是 `s3://labcontainer/x` | 建內容包 | 拒絕 | 自動：同上 |
| TC-043 | 作法 6 | 例外 | 路徑欄位是 `gs://labcontainer/x` | 建內容包 | 拒絕 | 自動：同上 |
| TC-044 | 作法 6 | 例外 | 路徑欄位是別的容器 `az://othercontainer/x` | 建內容包 | 拒絕（跨容器本任務不支援） | 自動：同上 |
| TC-045 | 作法 6 | 例外 | 以上任一種被拒的路徑 | 看拒絕訊息 | 訊息告訴使用者先自己用 `az storage blob` 或 azcopy 把檔案放進同一個容器 | 自動：同上 |
| TC-046 | 作法 6 | 例外 | 掃描 `abf_platform/`、`abf_station/` 原始碼 | 搜尋完整的上傳指令字樣 | 找不到（提示句的程式碼拆成兩段字串） | 自動：同上 |
| TC-047 | 範圍（fetch.py） | 功能 | 一個 Azure run 資料夾裡有 `azure.config` | 列出可取回的紀錄檔 | `azure.config` 不被當成紀錄檔 | 自動：`test_azure_launch.py`（註解標 TC-047） |
| TC-048 | 作法 1 表；不做（續跑）；AZL-BUNDLE-06 | 不在範圍 | 一個 Azure run | 平台端 `prepare_resume` | 白話拒絕，訊息含 Azure、不含 `AWS` | 自動：`AZL-BUNDLE-06 test_azure_resume_and_relaunch_are_refused_with_the_azure_name` |
| TC-049 | 同上 | 不在範圍 | 同上 | 平台端 `prepare_relaunch` | 白話拒絕，訊息含 Azure、不含 `AWS` | 自動：同上 |
| TC-050 | 同上 | 不在範圍 | 代理收到 Azure 的續跑工作 | 代理 `run_resume` | 拒絕（`AZURE_NO_RESUME`）；沒有啟動；訊息含 Azure、不含 `AWS` | 自動：同上 |

## User Story 3 — 憑證只在平台主機，只經主控程序的環境變數（優先度 P1）

維護者原話（plan 第 52 行）：「雲端用戶不裝代理——平台主機自己跑 Nextflow、雲端憑證放平台主機檔案（不進資料庫）」；裁決 1：不落地、只放環境變數。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-051 | 作法 4；AZL-CRED-01 | 功能 | 憑證檔（`ABF_STATION_AZURE_CREDENTIALS` 指向、權限 600）有 `batch_account_key` 與 `storage_account_key`；假的 `start_detached` 記下 env | 送出成功 | env 的 `AZURE_BATCH_ACCOUNT_KEY` 等於 `batch_account_key` | 自動：`AZL-CRED-01 test_head_env_has_only_the_nextflow_credential_names` |
| TC-052 | 作法 4 | 功能 | 同上 | 看 env | 有 `AZURE_STORAGE_ACCOUNT_KEY` 等於 `storage_account_key`，沒有 `AZURE_STORAGE_SAS_TOKEN` | 自動：同上 |
| TC-053 | 作法 4 | 功能 | 憑證檔改為 `batch_account_key` 加 `storage_sas_token`（值以 `?` 開頭） | 送出成功後看 env | 有 `AZURE_STORAGE_SAS_TOKEN`，值已去掉開頭的 `?`；沒有 `AZURE_STORAGE_ACCOUNT_KEY` | 自動：同上 |
| TC-054 | 裁決 2 | 功能 | 憑證檔同時有 `storage_account_key` 與 `storage_sas_token` | 送出成功後看 env | 用帳號金鑰（`AZURE_STORAGE_ACCOUNT_KEY`），不放 SAS | 自動：同上 |
| TC-055 | 作法 4 | 例外 | 同 TC-051 | 看 env | 沒有 `AZURE_BATCH_ACCESS_KEY`、沒有 `AZURE_STORAGE_KEY`（那是 `az` 預檢用的名字） | 自動：同上 |
| TC-056 | 作法 4 | 例外 | 測試先把 `ABF_*` 與無關的 `AZURE_*` 變數放進 `os.environ` | 送出成功後看 env | 沒有任何 `ABF_*`；`AZURE_*` 只剩上述金鑰名（兩類以內），被放進去的無關 `AZURE_*` 一個都不在 | 自動：同上 |
| TC-057 | 作法 4；AZL-CRED-02 | 例外 | 憑證檔放假金鑰（字串拼接組出），跑完整流程 | 搜尋 argv、`head.sh`、`head.out`、帳本（ledger）、所有寫出的檔 | 搜不到假金鑰 | 自動：`AZL-CRED-02 test_credentials_never_appear_in_argv_logs_or_files` |
| TC-058 | 作法 4；專長守則（日誌與回應） | 例外 | 同上，含各種失敗情境 | 搜尋回傳結果、訊息、`left_on_site`、日誌輸出、資料庫的位元組 | 搜不到假金鑰與憑證檔路徑 | 自動：同上 |
| TC-059 | 作法 4；AZL-CRED-03 | 例外 | 憑證檔不存在 | 送出 | 拒絕；`start_detached` 0 次；沒有專屬資料夾；訊息說明憑證檔該放哪裡 | 自動：`AZL-CRED-03 test_missing_or_badly_shaped_credential_file_stops_before_any_program` |
| TC-060 | 作法 4 | 例外 | 憑證檔權限不是 600（Windows 上略過） | 送出 | 拒絕；`start_detached` 0 次；訊息說明怎麼修 | 自動：同上 |
| TC-061 | 作法 4 | 例外 | 憑證檔缺 `batch_account_key` | 送出 | 拒絕；`start_detached` 0 次；訊息說明怎麼修 | 自動：同上 |
| TC-062 | 作法 4 | 例外 | 憑證檔 `storage_account_key` 與 `storage_sas_token` 兩者都缺 | 送出 | 拒絕；`start_detached` 0 次；訊息說明怎麼修 | 自動：同上 |
| TC-063 | 作法 4；專長守則 | 例外 | 憑證檔格式錯誤（含假金鑰） | 送出 | 訊息不印出憑證檔內容 | 自動：同上 |

## User Story 4 — 送出畫面與指令列：白話說明 Azure 會向實驗室收費（優先度 P1）

維護者原話（plan 第 16、46 行）：費用顯示與上限屬 C-3；「雲端費用照 10-18 裁示：顯示雲端自己的幣別（美元）、不換算」→ 本任務只在畫面寫明 Azure 會計費，不加任何金額或換算。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-064 | 作法 9；AZL-SCREEN-01 | 功能 | Azure 環境 `azure1` | 產生送出畫面 | 第一段含 `AZURE_COST` 那句：「由 Azure 向實驗室的 Azure 帳號收費；本系統目前沒有費用預估與上限」 | 自動：`AZL-SCREEN-01 test_azure_launch_screen_first_paragraph_states_billing_without_amounts` |
| TC-065 | 作法 9 | 功能 | 同上 | 看畫面順序 | 帳單句在「送出確認」標題之後的第一段，在欄位清單之前 | 自動：同上 |
| TC-066 | 作法 9；原話第 46 行 | 例外 | 同上 | 搜尋整個畫面 | 不含 `NT$`、`USD`、`$` 加數字的金額（環境名、pid 裡的數字不算） | 自動：同上 |
| TC-067 | 作法 9 | 功能 | 同上 | 看畫面 | 有取消提示（`AZURE_CANCEL_NOTE`） | 自動：`test_azure_launch.py`（註解標 TC-067） |
| TC-068 | 作法 9 | 功能 | `spot=true` 的環境 | 看畫面 | 有 `AZURE_SPOT_NOTE`：說明 `spot` 只是記錄，要用低優先權請在建 pool 時設定；不暗示這個欄位會切換 Spot | 自動：`test_azure_launch.py`（註解標 TC-068） |
| TC-069 | 作法 9 | 功能 | 一個 Azure run | 產生取消畫面 | 用詞是「主控程序編號（pid）」，不是 Slurm 工作編號；沒有 pid 時照舊拒絕 | 自動：`test_azure_launch.py`（註解標 TC-069） |
| TC-070 | 範圍（cli.py :200）；AZL-SCREEN-03 | 功能 | Azure 環境的 run | 指令列顯示「已送出／已啟動」那行 | 用「已啟動：主控程序編號（pid）…」，不出現「Slurm 工作編號」 | 自動：`AZL-SCREEN-03 test_cli_wording_switches_only_for_azure` |
| TC-071 | 範圍（cli.py :237） | 功能 | Azure 環境的 run，代理回報結果不明 | 指令列顯示結果不明那行 | 說請查平台主機上的專屬資料夾與主控程序，不是「國網上」「Slurm 工作」 | 自動：同上 |
| TC-072 | 範圍（cli.py :267）；作法 8；裁決 5 | 功能 | Azure 環境的 run，取消成功 | 指令列顯示取消成功那段 | 說已送出取消請求（主控程序 pid）並要求到 Azure Portal 的 Batch 頁核對；不出現 Slurm／squeue；**不承諾**「取消即停止計費」或「Nextflow 會取消 Batch 工作」 | 自動：同上 |
| TC-073 | 範圍（cli.py） | 功能 | Slurm、gcb、aws 的 run | 指令列三處輸出與 base 比 | 一字不變（尤其 Slurm 仍是「Slurm 工作編號」） | 自動：同上 |

## User Story 5 — 本人確認後取消（優先度 P1）

計畫作法 8：取消呼叫 `gcb_launch._cancel_head(ctx, bundle, launch.AZURE_RUNS, CANCEL_REMINDER)`；不加 `az batch job terminate`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-074 | 作法 8；AZL-CANCEL-01 | 功能 | 一個 Azure run，核對全通過（假的 `ps`、`/proc`、`os.kill`），有取消的確認憑證 | 代理處理 `cancel_run` | 對該 pid 恰好送出 1 次 SIGTERM，沒有別的訊號、沒有別的 pid | 自動：`AZL-CANCEL-01 test_cancel_sends_one_sigterm_after_cwd_and_ps_checks_for_azure` |
| TC-075 | 作法 8；AZL-CANCEL-01 | 例外 | `head.pid` 的內容對不上要取消的 pid／run | 取消 | 拒絕；`os.kill` 0 次 | 自動：同上 |
| TC-076 | 作法 8；AZL-CANCEL-01 | 例外 | `/proc/<pid>/cwd` 不是這個 run 的專屬資料夾 | 取消 | 拒絕；`os.kill` 0 次 | 自動：同上 |
| TC-077 | 作法 8 | 例外 | `<storage_root>/_azure_runs/<run>` 不存在 | 取消 | 白話拒絕；`os.kill` 0 次 | 自動：`test_azure_launch.py`（註解標 TC-077） |
| TC-078 | 作法 9；AZL-CANCEL-02 | 例外 | Azure run 沒有 pid | 取消 | 以白話拒絕，說明為何不能取消；`os.kill` 0 次 | 自動：`AZL-CANCEL-02 test_cancel_without_pid_is_refused_in_plain_words` |
| TC-079 | 作法 8；AZL-CANCEL-02 | 功能 | 取消成功 | 看結果訊息 | 含：已對主控程序送出一次終止信號；請到 Azure Portal 的 Batch 帳號頁確認 job 與 pool 已停；沒停乾淨要自己處理；費用從啟動到停掉都算 | 自動：`AZL-CANCEL-02 test_cancel_message_reminds_to_check_the_azure_portal` |
| TC-080 | 裁決 5 | 例外 | 同上 | 搜尋取消訊息與取消畫面全文 | 沒有「已停止計費」「取消後不再收費」之類的承諾 | 自動：同上 |
| TC-081 | 作法 9 | 功能 | 一個 Azure run | `cancel_screen`、`prepare_cancel` | 都支援 Azure（不再落到 Slurm 路徑）；Slurm 的仍走原路 | 自動：`test_azure_launch.py`（註解標 TC-081） |
| TC-082 | 目標；AZL-CONF-01 | 例外 | 沒有取消的確認憑證（或種類是 `launch`、已用過、雜湊不符） | 代理處理 `cancel_run` | `refused`；`os.kill` 0 次 | 自動：`test_azure_launch.py`（註解標 TC-082） |
| TC-083 | 作法 8 | 功能 | 一個 Azure run 與一個 aws run | `cancel.py` 依 `ce.platform` 分派 | Azure 走 `azure_launch.run_cancel`（資料夾根為 `_azure_runs`）；aws 仍走自己的 | 自動：`AZL-CANCEL-01`（同 TC-074） |
| TC-084 | AZL-CANCEL-03 | 功能 | 把取消抽成共用函式後，重跑 gcb、aws 取消案例 | 執行 | gcb、aws 取消訊息與檢查順序不變；既有 `test_gcb_launch.py`、`test_station_cancel.py`、`test_aws_launch.py` 取消斷言一條都沒改且全綠 | 自動：`AZL-CANCEL-03 test_gcb_and_aws_cancel_messages_are_unchanged_by_the_refactor` |

## User Story 6 — 共用閘門逐型別放行（優先度 P1，本任務最容易出錯處）

計畫作法 1、2：Azure 搬進 `PLATFORM_HOST_TYPES` 時只開四種，不可連帶打開清理、上傳、資料集 destination、讀取類；AWS、Google Batch 的行為位元級不變。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-085 | 作法 1 表；AZL-GATE-01 | 功能 | 一個可用的 Azure 環境 | `check_target` 輸入 `launch_nextflow`、`cancel_run`、`preflight`、`pipeline_files` | 四種都不丟例外 | 自動：`AZL-GATE-01 test_azure_environment_accepts_exactly_preflight_launch_cancel_and_pipeline_files` |
| TC-086 | 作法 1 表 | 不在範圍 | 同上 | 輸入 `clean_work`、`put_upload`、`list_site_files`、`fetch_run_records`、`read_task_log` | 五種都被拒（`JobRefused`），訊息含「尚未支援」 | 自動：同上 |
| TC-087 | 作法 1 表；裁決 9 | 不在範圍 | 同上 | 看 `clean_work` 的拒絕訊息 | 含 `azure-clean` | 自動：同上 |
| TC-088 | 作法 1 表；裁決 9 | 不在範圍 | 同上 | 看 `put_upload` 的拒絕訊息 | 含 `azure-upload` | 自動：同上 |
| TC-089 | 作法 1 | 例外 | 同上 | 看上述五種的拒絕訊息 | 不含 `AWS`、不含 `Google Batch` | 自動：同上 |
| TC-090 | 作法 1（依型別名產生） | 例外 | 同上 | 看上述五種的拒絕訊息 | 以型別名 `Azure Batch` 稱呼這個環境 | 自動：同上 |
| TC-091 | 作法 1；AZL-GATE-02 | 功能 | 一個可用的 aws 環境 | `check_target` 輸入 aws 原有的六種（含 `clean_work`、`put_upload`） | 仍全部放行；六種以外仍被拒 | 自動：`AZL-GATE-02 test_aws_and_google_batch_gates_and_messages_are_unchanged` |
| TC-092 | 作法 1；AZL-GATE-02 | 功能 | 一個可用的 gcb 環境 | `check_target` 輸入 gcb 原有的六種 | 仍全部放行；六種以外仍被拒 | 自動：同上 |
| TC-093 | 作法 1（位元級相同）；AZL-GATE-02 | 例外 | aws、gcb 環境 | 對六種以外的種類，看拒絕訊息 | 逐字等於 base（aws：`ce1 is an AWS Batch environment: this job kind is not built for it yet (尚未支援)`；gcb：`g1 is a Google Batch environment: this job kind is not built for it yet (尚未支援)`，以既有 `test_aws_clean.py:116/:126` 為準） | 自動：同上 |
| TC-094 | 作法 2；AZL-GATE-03 | 功能 | 載入 `compute_envs` | 看常數 | `PLATFORM_HOST_TYPES == (GOOGLE_BATCH, AWS, AZURE)` | 自動：`AZL-GATE-03 test_type_constants_after_azure_launch` |
| TC-095 | 作法 2；裁決 6 | 功能 | 同上 | 看 `CHECK_ONLY_TYPES` | 為空元組 `()`；原始碼該行旁保留註解「新雲端類型先放這裡，只開預檢」 | 自動：同上 |
| TC-096 | 作法 1；AZL-GATE-03 | 功能 | 同上 | 看 `CLOUD_JOB_KINDS[AZURE]` | 恰為 `preflight`、`launch_nextflow`、`cancel_run`、`pipeline_files` 四種 | 自動：同上 |
| TC-097 | 作法 2；AZL-GATE-03 | 例外 | 掃描 `abf_platform/`、`abf_station/` 原始碼 | 搜尋 `PLATFORM_HOST_TYPES[` | 找不到（沒有任何地方靠位置取元組） | 自動：同上 |
| TC-098 | 作法 2、AZL-GATE-06 | 功能 | 同上 | 看 `CHECKABLE` | 仍含 Slurm、gcb、aws、Azure 四種（搬動沒讓 Azure 掉出可預檢清單） | 自動：`test_azure_launch.py`（註解標 TC-098） |
| TC-099 | 作法 1 表；AZL-GATE-04 | 不在範圍 | Azure 環境，`workDir` 為 `az://labcontainer/work` | 呼叫 `cloud_store.workdir_bucket`、`upload_prefix`、`object_url`、`big_file_command` | 四者一律丟 `CloudPathError` | 自動：`AZL-GATE-04 test_cloud_store_stays_without_azure` |
| TC-100 | 作法 1 表；AZL-GATE-04 | 不在範圍 | 資料集 `--destination` 填 Azure 環境名 | 送出資料集指令 | 白話拒絕，沒有登記任何資料集 | 自動：同上 |
| TC-101 | 作法 1 表；AZL-GATE-05 | 不在範圍 | 對 Azure 環境直接呼叫 `jobs.enqueue_*` 排 `put_upload`、`clean_work` | 排入 | 被拒；jobs 表列數不變 | 自動：`AZL-GATE-05 test_put_upload_and_clean_work_jobs_cannot_be_queued_for_azure` |
| TC-102 | 作法 1 表；AZL-GATE-05 | 不在範圍 | 代理端 `clean.run_clean` 收到 Azure 的內容包 | 處理 | 拒絕；不啟動任何程式；不落到 Slurm 的清理路徑 | 自動：同上 |
| TC-103 | 作法 1 表；AZL-GATE-05 | 不在範圍 | 代理端 `put_upload.run_put` 收到 Azure 的內容包 | 處理 | 拒絕；不啟動任何程式 | 自動：同上 |
| TC-104 | 作法 1 表（preflight）；AZL-GATE-06 | 功能 | 建立 Azure 環境並執行 `ce preflight` | 等待代理回覆 | 預檢工作被放行、`ce preflight` 仍排出預檢 job 並等得到答案（`cli.py:475` 條件仍涵蓋 Azure） | 自動：`AZL-GATE-06 test_azure_ce_preflight_still_routes_after_leaving_check_only` |
| TC-105 | AZL-GATE-06 | 功能 | 代理收到 Azure 的預檢工作 | 處理 | `handlers` 仍走 `azure_preflight` | 自動：同上 |
| TC-106 | 作法（primary_environment）；AZL-GATE-07 | 功能 | 使用者只有一個可用環境且是 Azure，送出時沒指名環境 | `primary_environment` | 不會自動選 Azure（只選 Slurm） | 自動：`AZL-GATE-07 test_primary_environment_never_auto_picks_azure_and_naming_it_works` |
| TC-107 | AZL-GATE-07 | 功能 | 同上，但明講 Azure 環境名字 | 送出 | 可以進入確認流程 | 自動：同上 |
| TC-108 | 專長守則（跨使用者，讀） | 例外 | 第二位使用者用自己的 token 對第一位的 Azure 環境送出 | `launch` | 回「找不到」，與不存在的環境相同，不洩漏存在 | 自動：`test_azure_launch.py`（註解標 TC-108） |
| TC-109 | 專長守則（跨使用者，寫） | 例外 | 第二位使用者對第一位的 Azure run 取消 | `cancel` | 回「找不到」；沒有排入取消工作 | 自動：`test_azure_launch.py`（註解標 TC-109） |
| TC-110 | 裁決 13 | 例外 | Slurm 環境 | 排 `put_upload` | 仍是白話拒絕，訊息文字與 base 相同 | 自動：`test_azure_launch.py`（註解標 TC-110） |
| TC-111 | 範圍（compute_envs snapshot） | 功能 | 合法 Azure 環境 | 呼叫 `snapshot` | 鍵集合恰為 `name, platform, credentialsId, location, batchAccountName, storageAccountName, workDir, pool`（與搬動前相同） | 自動：`test_azure_launch.py`（註解標 TC-111；與 base 比對） |

## User Story 7 — 不退步與不在範圍（優先度 P1）

計畫「不做」與「必須更新的既有斷言」：Slurm、gcb、aws 位元級不變；費用、上傳、清理、續跑、讀取類、自動建 pool、終止 Batch 資源等一律不做。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112 | 完成標準；AZL-SCREEN-02 | 功能 | 同一組 Slurm 輸入，在 base 與本分支各產一次送出畫面、取消畫面、內容包（含 `head.sh`） | 比較 | 位元級相同 | 自動：`AZL-SCREEN-02 test_slurm_gcb_and_aws_screens_are_byte_identical` |
| TC-113 | 完成標準 | 功能 | 同一組 gcb 輸入，各產一次畫面與內容包 | 比較 | 位元級相同 | 自動：同上 |
| TC-114 | 完成標準 | 功能 | 同一組 aws 輸入，各產一次畫面與內容包 | 比較 | 位元級相同 | 自動：同上 |
| TC-115 | 必須更新的既有斷言（不准動） | 功能 | 既有 Slurm、gcb、aws 的內容包、畫面、`head.sh`、取消訊息斷言 | 比對 base 與本分支的測試檔 | 這些斷言一條都沒被改，且全綠 | 自動：既有測試保持綠 |
| TC-116 | 必須更新的既有斷言；裁決 11 | 例外 | 本任務的 `git diff` | 驗收者逐檔看既有測試的改動 | 既有測試只動計畫列的幾處（`test_azure_ce.py` 約 :720、:746、:756、:857、:859、:864、:951；`test_aws_ce.py` 約 :907、:924；`test_gcb_ce.py` 約 :853、:867；`test_aws_launch.py` 約 :985、:992；`test_gcb_launch.py` 約 :1151），且只做「Azure 從只能預檢改成能跑」的最小改動；其餘既有測試只准加、不准減 | 手動：驗收者讀 `git diff`，對照 `docs/TESTING.md`「azure-launch」小節 |
| TC-117 | 不做（不改 azure-ce-type） | 功能 | Azure 的 `ce create`、`ce show`、`ce preflight` | 跑 `test_azure_ce.py` 其餘既有案例 | 全綠；建環境仍排第一個預檢 | 自動：`test_azure_ce.py` 既有案例保持綠 |
| TC-118 | 不做（費用 C-3）；原話第 16 行 | 不在範圍 | Azure 環境 | 搜尋費用預估呼叫 | 沒有預估、沒有上限；`cloud_cost.py` 與 `_cloud_check` 沒有 Azure 內容；`primary_environment`、`cli.py`（platform）、`actions/*` 未改 | 自動：`test_azure_launch.py`（註解標 TC-118）；`test_cloud_cost.py` 既有案例保持綠 |
| TC-119 | 不做（azure-upload） | 不在範圍 | 掃描 `abf_station/`、`abf_platform/` 原始碼 | 搜尋 `az storage blob upload`、`azcopy copy` 等完整上傳指令 | 找不到；`put_upload` 對 Azure 被拒（TC-101、TC-103） | 自動：`test_azure_launch.py`（註解標 TC-119） |
| TC-120 | 不做（azure-clean） | 不在範圍 | 掃描原始碼 | 搜尋 `az storage blob delete`、`delete-batch`、`azcopy rm` | 找不到；`clean_work` 對 Azure 被拒（TC-101、TC-102） | 自動：`test_azure_launch.py`（註解標 TC-120） |
| TC-121 | 不做（第二條寫入路徑）；作法 8 | 不在範圍 | 假的 `run_fixed` 記下所有 `az` 呼叫；掃描 `azure_launch.py` | 送出與取消各跑一次 | 沒有 `az batch job terminate` 或任何會改動 Azure 的指令；`azure_launch.py` 只呼叫 `az` 的版本查詢與既有唯讀預檢 | 自動：`test_azure_launch.py`（註解標 TC-121） |
| TC-122 | 不做（讀取類） | 不在範圍 | 假的 `run_fixed` 記下所有呼叫 | 對 Azure 環境要求 `list_site_files`、`fetch_run_records`、`read_task_log` | 只得到白話拒絕；沒有任何 `az` 或 Blob 指令被執行 | 自動：`test_azure_launch.py`（註解標 TC-122） |
| TC-123 | 不做（Entra／VNet／自訂映像／自動建 pool） | 不在範圍 | 合法 Azure 內容包 | 搜尋 `azure.config` 與 `nextflow.config` | 沒有 Entra／Managed Identity、VNet、自訂映像、`deletePoolsOnCompletion`、`accountKey`、`sasToken`、`endpoint` 等設定，沒有 `autoPoolMode = true`／`allowPoolCreation = true` | 自動：`AZL-BUNDLE-01`（同 TC-030） |
| TC-124 | 不做（預檢新增檢查）；作法 10；裁決 3 | 不在範圍 | `azure_preflight` | 列出預檢項目 | 仍是六項（`credential_name, credential_file, credential_shape, az, pool, storage`），沒有 `dockerCompatible`／task slots 檢查；`azure_preflight.py` 未改 | 自動：`test_azure_ce.py` 既有案例保持綠；`git diff` 無 `azure_preflight.py` |
| TC-125 | 憲法 TC-085；AZL-CONF-04 | 不在範圍 | `pyproject.toml` 與原始碼 | 搜尋 | 沒有 `azure-*` 依賴，沒有 `import azure` | 自動：`AZL-CONF-04 test_no_cloud_library_is_imported_and_no_new_dependency` |
| TC-126 | 不做（網頁畫面）；AZL-CONF-05；專長守則（對等性） | 不在範圍 | 列舉 MCP 工具與網頁路由 | 與 base 比 | MCP 工具仍 12 個；沒有新增路由或網頁畫面；使用者可見動作與動作層函式清單兩邊一一對應、本任務沒有新增 | 自動：`AZL-CONF-05 test_mcp_tool_list_is_still_twelve`；既有對等性測試保持綠 |
| TC-127 | 作法 11；專長守則（migration） | 不在範圍 | 比對資料庫表結構 | 與 base 比 | 結構無變化（`launches.slurm_job_id` 沿用、無新欄位、環境設定鍵不變），因此不需 migration | 自動：`test_azure_launch.py`（註解標 TC-127） |
| TC-128 | 完成標準；範圍「不改」清單 | 例外 | 本任務的 `git diff --name-only` | 驗收者逐檔看 | 不含 `.github/`、憲法、版本號檔、`web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`、已安裝 plugin 副本；`clean.py`、`put_upload.py`、`site.py`、`agent.py`、`azure_preflight.py`、`cloud_cost.py`、`actions/*`、`abf_platform/cli.py` 未被改；`spec`／`test-case*.md` 沒被改 | 手動：驗收者讀 `git diff --name-only` |
| TC-129 | 不做（真實 Azure 試跑）；裁決 7 | 不在範圍 | 本任務新增的全部測試 | 檢查測試如何跑 | 全部用假的 `start_detached`／`run_fixed`、`tmp_path`；沒有任何測試連網或啟動真程式；真實試跑只在 `docs/TESTING.md` 手動步驟 | 手動：驗收者讀 `test_azure_launch.py` 與 `docs/TESTING.md` |

## User Story 8 — 文件（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-130 | 範圍（PLATFORM.md）；AZL-DOC-01 | 功能 | `docs/PLATFORM.md` 型別表 | 看 azbatch 的 Supported 欄 | 逐字為 `checked and launched on the platform host (upload, clean, resume: not yet)` | 自動：`AZL-DOC-01 test_platform_md_documents_azure_launch` |
| TC-131 | 範圍；AZL-DOC-01 | 功能 | `docs/PLATFORM.md` | 找「Launching on Azure Batch」小節 | 存在，說明誰跑什麼（主控程序在平台主機、計算在 Azure Batch 既有 pool） | 自動：同上 |
| TC-132 | 範圍；作法 7；裁決 8 | 功能 | 同上 | 看需求 | 寫明平台主機要 Java 17+、Nextflow、`az` CLI、憑證檔，以及 `storage_root` | 自動：同上 |
| TC-133 | 作法 10；AZL-DOC-01 | 功能 | 同上 | 看 pool 前置條件 | 寫明 pool 必須 `dockerCompatible`、task slots 等於核心數、儲存體與 Batch 同區域、每個 process 都要有 container；並寫失敗現象與處理 | 自動：同上 |
| TC-134 | 作法 3；裁決 4 | 功能 | 同上（「Azure Batch」小節） | 看 `azure.config` 鍵表 | 列出作法 3 的每個鍵，說明 `resourceLimits` 是單一 task 上限不是總量、`allowPoolCreation`／`autoPoolMode` 寫死 `false` 與原因、`spot` 只是記錄 | 自動：同上 |
| TC-135 | 作法 8、9；裁決 5 | 功能 | 同上 | 看費用段與取消段 | 白話寫明由 Azure 向實驗室的 Azure 帳號收費、平台沒有費用預估與上限；取消只送一次 SIGTERM、要到 Azure Portal 核對；不承諾取消即停止計費 | 自動：同上 |
| TC-136 | 裁決 12；AZL-DOC-01 | 功能 | `docs/PLATFORM.md` 中「Slurm, Google Cloud Batch and AWS Batch can run; Azure Batch can be created and checked; …」那句（原本出現兩次，含粗體處） | 看兩處 | 兩處都改為 `Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; the other ten types can be modelled only`，不再有「can be created and checked」 | 自動：同 TC-130（並配合更新後的 `test_azure_ce.py`／`test_aws_ce.py`／`test_gcb_ce.py`／`test_gcb_launch.py` 既有斷言） |
| TC-137 | 範圍；AZL-DOC-02 | 功能 | `docs/SEQERA_PARITY.md` Azure Batch 那列 | 看狀態文字與結尾 | 以 `Have (create + check + launch + cancel)` 開頭，且結尾仍是 `[ ] |`（勾選框未勾） | 自動：`AZL-DOC-02 test_seqera_parity_azure_row` |
| TC-138 | 範圍；裁決 13 | 功能 | `docs/SEQERA_PARITY.md` 第 84 行預檢說明句 | 看 Azure 那段括號 | 不再寫 `launch in azure-launch`；寫為 `create + check + launch + cancel; resume not yet`（與 aws 句同格式） | 自動：同上 |
| TC-139 | 範圍；AZL-DOC-03 | 功能 | `docs/TESTING.md` | 找「azure-launch」小節 | 存在，寫明手動驗收步驟 1–7，並含「會花錢、需維護者同意」字樣，列在「Needs human」之下 | 自動：`AZL-DOC-03 test_testing_md_has_azure_launch_section_with_manual_steps` |
| TC-140 | 範圍（INSTALL／OPERATIONS） | 功能 | `docs/INSTALL.md` 或 `docs/OPERATIONS.md` 的雲端小節 | 看內容 | 寫明平台主機要 Java 17+、Nextflow、`az` CLI（二選一皆可） | 手動：驗收者讀文件 |
| TC-141 | 原話第 16、46 行 | 例外 | 本任務新增或改動的文件段落 | 搜尋 | 沒有金額、`NT$`、台幣換算 | 自動：`AZL-DOC-01`（同 TC-130） |

## User Story 9 — 維護者在自己的 Azure 帳號實跑一次（手動；優先度 P3）

計畫完成標準（手動）與裁決 7：**會花很小一筆錢，屬 C 級，要等維護者點頭，且先確認 Azure Cost Management 預算警示已設；不屬於 executor／verifier 的完成標準**。閱卷只確認這些步驟在 `docs/TESTING.md` 寫得夠具體、可照做，不要求實跑。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-142 | 手動 1 | 功能 | 預算警示已設 | 檢查平台主機（WSL） | 有 Java 17+、Nextflow、`az` CLI；`storage_root` 已設；憑證檔在 `ABF_STATION_AZURE_CREDENTIALS` 指的位置（600）；azure-ce-type 的預檢 `available` | 手動：`docs/TESTING.md`「azure-launch」步驟 1 |
| TC-143 | 手動 2；裁決 3 | 功能 | 事先建好的 pool | 對照官方前置條件 | pool 為 `dockerCompatible`、task slots 等於 VM 核心數、與儲存體同區域；每個 process 都有 `container`；失敗（Nextflow 啟動即報 pool 設定錯誤或找不到容器）就停手回報，不自行加設定 | 手動：同上步驟 2 |
| TC-144 | 手動 3；目標 | 功能 | 兩三個很小的檔已用 `az storage blob` 或 azcopy 放進 `workDir` 同一個容器 | `abf-launch … --ce azure1` | 送出畫面第一段看得到「由 Azure 向實驗室的 Azure 帳號收費」；答 y 才開始 | 手動：同上步驟 3 |
| TC-145 | 手動 3（判決待裁決 1） | 功能 | 同上 | 看主控程序是否通過 Azure 認證 | 通過；若報認證失敗（Nextflow 沒讀到環境變數），記入 ledger 並回報，不自行改憑證做法 | 手動：同上步驟 3 |
| TC-146 | 手動 4 | 功能 | 送出成功 | 看畫面、主機、Azure Portal | 看到「已啟動：主控程序編號…」；`<storage_root>/_azure_runs/<run>` 有 `head.pid`、`head.out`；Portal 的 Batch 帳號頁出現 job；平台 run 頁出現進度；跑完 `az://…/runs/<run>/results` 有輸出 | 手動：同上步驟 4 |
| TC-147 | 手動 5（判決待裁決 5） | 功能 | 再送一個 run，中途取消 | 看 Portal | job 被終止；沒取消乾淨就記入 ledger 回報，不自行加 `az batch job terminate` | 手動：同上步驟 5 |
| TC-148 | 手動 6 | 功能 | 跑過上述流程 | 在資料庫、`ce show`、畫面、日誌、`head.sh`、`azure.config` 搜尋 | 搜不到憑證任何片段與憑證檔路徑（`/proc/<pid>/environ` 有金鑰是已知代價） | 手動：同上步驟 6 |
| TC-149 | 手動 7（判決待裁決 5） | 功能 | 同上 | 核對 `process.resourceLimits = [cpus: N]` | 在 `azurebatch` 上被接受（不報未知指令）；結果寫進 ledger | 手動：同上步驟 7 |

## 憲法與安全網

專案原則 I（新檔要有 `# Nothing existing:` 標頭）、「平台不啟動任何程式、`nextflow run` 只在 `launch.py`、`subprocess` 只在 `site.py`」「人答 y 才啟動」「憑證不進設定檔以外的地方」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-150 | 一條送出路徑（`nextflow run` 只在 `launch.py`） | 功能 | 本分支 | 跑 `tests/no_second_run_state_test.sh` | 通過；`azure_launch.py` 沒有 `nextflow run` 字樣 | 自動：`tests/no_second_run_state_test.sh` |
| TC-151 | 送出允許清單只有一項 | 功能 | 本分支 | 檢查 `LAUNCH_ALLOW` | 仍恰一項（不為 Azure 新增第二個允許位置） | 自動：`AZL-CONF-03 test_the_launch_allow_list_still_has_one_entry` |
| TC-152 | 平台不啟動任何程式 | 例外 | 掃描 `abf_platform/`、`abf_station/` 原始碼（排除註解行） | 搜尋 `nohup`、`setsid`、`subprocess`、`Popen`、`os.system`、`nextflow run`、`sbatch` | 平台包不含；`azure_launch.py` 不含 `nextflow run`、`sbatch`、`subprocess`（`subprocess` 只在 `site.py`） | 自動：`AZL-CONF-03 test_the_platform_package_starts_no_program` |
| TC-153 | 原則 I（新檔標頭，專案既有 TC-070） | 功能 | 新增的 `azure_launch.py`、`test_azure_launch.py` | 看前 40 行 | 各有 `# Nothing existing: …`，理由為「搜過 Nextflow 的 `azurebatch` executor、Seqera `tw launch`、nf-core `tower launch`，都是把工作交給 Seqera 服務，沒有現成可由本機代理在確認後以 `azurebatch` 啟動並可取消的東西」；`test_scope.py` 通過 | 自動：`platform/tests/test_scope.py` |
| TC-154 | 憑證只在設定檔／平台主機檔案 | 功能 | 新增與改動的測試檔 | 跑 `tests/credentials_stay_in_settings_test.sh` | 通過（測試中的假金鑰以字串拼接，不寫字面） | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-155 | 專長守則：錯誤訊息與日誌 | 例外 | Azure 的每一種拒絕（閘門、續跑、憑證、缺工具、取消核對失敗） | 看訊息 | 每則都說明發生了什麼與該怎麼辦；不露出堆疊、內部路徑、SQL；不含金鑰 | 自動：`test_azure_launch.py`（註解標 TC-155）；並見 TC-058 |

## User Story 10 — 維護者原話逐條對照（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-156 | 原話第 40 行：「送出的是一個 Run，用已建好的環境＋憑證名字；送出時不重新輸入憑證」 | 功能 | 已建好的 Azure 環境（憑證只是名字） | 看 `abf-launch` 的參數與送出畫面 | 只需指名環境；沒有任何可輸入金鑰或憑證檔路徑的旗標或提示；畫面沒有要求輸入憑證 | 自動：`test_azure_launch.py`（註解標 TC-156） |
| TC-157 | 原話第 52 行：「雲端用戶不裝代理」；第 54 行：本任務不動網頁畫面 | 功能 | 使用者端（呼叫 `abf-launch` 的那台）PATH 裡沒有 java、nextflow、az | 準備送出到 Azure 環境 | 使用者端仍能走到確認畫面；java／nextflow／az 的檢查只發生在平台主機的代理 | 自動：`test_azure_launch.py`（註解標 TC-157） |
