# 測試案例：在 AWS Batch 上送出與取消分析（aws-launch，C-2）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：本任務沒有 spec.md，以 `specs/aws-launch/plan.md`（含「維護者原話」逐字引文，以及文末「裁決」與 A1–A9，與上文衝突時以文末為準）為規格。
IDs: TC-001..TC-189。每條只測一件事；驗證方式「自動」＝ `platform/tests/` 下的測試，並在測試內以註解 `# TC-nnn` 標明（計畫文內提到的 TC-070、TC-085 是專案既有測試的編號，與本檔編號無關）。
所有測試輸入都用假值：`lab-bucket`、`eu-west-1`、`lab-queue`、`aws-lab`；不碰網路、不啟動真程式。
-->

**規格**：`specs/aws-launch/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「尚未支援」而不是悄悄亂做。

名詞：**主控程序**＝在平台主機上跑 Nextflow 的那個程式（AWS Batch 只負責算）；**站台代理**＝裝在平台主機上、本人答 y 之後才動手的程式；**pid**＝作業系統給程式的編號；**內容包**＝平台與代理各自用同一個函式建一次、必須完全相等的那組要送出的檔案；**放行**＝平台願意為某種環境排入某種工作；**SIGTERM**＝請程式自己結束的標準訊號；**head.sh**＝代理實際執行的啟動腳本，也是畫面上顯示給人看的那份。

## User Story 1 — 本人答 y 之後，才在 AWS Batch 上送出一次分析（優先度 P1）

計畫目標：「沒有本人答 y 就不啟動」；交辦原話：「平台主機自己跑 Nextflow（awsbatch executor），雲端使用者不裝站台代理……以 `head.pid` 取消」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 8；目標 | 功能 | 一個 `available` 的 aws 環境、代理在線、有效確認憑證、金鑰檔／Java／Nextflow／aws CLI／預檢都用假的通過 | 代理收到 aws 的 `launch_nextflow` 工作 | 結果 `ok` 為真；訊息為「已啟動：主控程序編號（pid）<pid>，run 名稱 <run>，專屬資料夾 <路徑>；AWS Batch 的工作與費用從現在開始計」 | 自動：`test_aws_launch.py::test_launch_writes_head_pid_and_reports_it_as_the_job_number` |
| TC-002 | 作法 8；裁決 1 | 功能 | 同 TC-001，假的 `start_detached` 回傳 pid | 送出成功 | 結果裡 `slurm_job_id` 等於該 pid（欄位名不改）；`head.pid` 檔內容也是同一個 pid | 自動：同上 |
| TC-003 | 作法 8 | 功能 | 同 TC-001，假的 `start_detached` 記下呼叫參數 | 送出成功 | 恰呼叫 1 次；argv 為 `["bash", "<run_folder>/head.sh"]`；cwd 是專屬資料夾；輸出檔是 `<run_folder>/head.out`；沒有用 shell | 自動：同上（看假 `start_detached` 的記錄） |
| TC-004 | 作法 3、8 | 功能 | 同 TC-001，`tmp_path` 當 `storage_root` | 送出成功後看專屬資料夾 | 資料夾位置為 `<storage_root>/_aws_runs/<run 名稱>`，權限 700；結果訊息列的路徑就是它 | 自動：`test_aws_launch.py::test_run_folder_is_under_storage_root_in_aws_runs_and_a_missing_storage_root_is_refused` |
| TC-005 | 作法 8 | 功能 | 同 TC-001 | 送出成功後看資料夾內容 | 有 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`aws.config`、`head.sh`、`tower.token`、`head.pid`、`head.out`；前七個檔權限 600；資料夾裡沒有結果檔 | 自動：`test_aws_launch.py`（註解標 TC-005） |
| TC-006 | 作法 8；裁決 1 | 功能 | 平台端走完 `take_result` | 代理回報成功結果 | `launches.slurm_job_id` 等於該 pid；平台程式沒有為此新增欄位 | 自動：`test_aws_launch.py`（註解標 TC-006） |
| TC-007 | 作法 2 | 功能 | aws 環境可用，使用者在送出指令上明講環境名字 | 從 `prepare_launch` 開始送出 | 依序經過 `prepare_launch` → `check_run_name` → 確認頁 → `enqueue_launch` → 代理 `claim`；沒有另一條送出路徑 | 自動：`test_aws_launch.py::test_a_person_must_say_yes_an_aws_launch_is_never_auto_queued` |
| TC-008 | 作法 8 | 功能 | 同 TC-001，環境變數 `ABF_STATION_GCB_SETTLE_SECONDS` 設為某數字（假的睡眠函式） | 送出成功 | 代理啟動後等待的秒數取自這個既有環境變數（不另開新變數） | 自動：`test_aws_launch.py`（註解標 TC-008） |
| TC-009 | 作法 8 步驟 1；目標 | 例外 | 代理收到 aws 的 `launch_nextflow` 工作，但**沒有**確認憑證 | 代理處理該工作 | 結果 `refused`；`tmp_path` 下沒有任何新檔；`start_detached` 呼叫 0 次 | 自動：`test_aws_launch.py::test_unconfirmed_aws_launch_is_refused_and_nothing_is_written_or_started` |
| TC-010 | 同上 | 例外 | 有確認憑證但雜湊與內容包不符 | 代理處理 | `refused`；沒有新檔；`start_detached` 0 次 | 自動：同上 |
| TC-011 | 同上 | 例外 | 確認憑證已經用過一次 | 再送一次同一個工作 | `refused`；沒有新檔；`start_detached` 0 次 | 自動：同上 |
| TC-012 | 同上 | 例外 | 憑證的種類是 `cancel`（不是 `launch`） | 拿它去送出 | `refused`；沒有新檔；`start_detached` 0 次 | 自動：同上 |
| TC-013 | 目標；作法 2 | 例外 | 對 aws 環境發出送出要求 | 在人答 y 之前查 jobs 表 | 還沒有任何 `launch_nextflow` 工作被建立（不會自動排進佇列） | 自動：`test_aws_launch.py::test_a_person_must_say_yes_an_aws_launch_is_never_auto_queued` |
| TC-014 | 目標 | 例外 | 同 TC-013 | 人答 n、或逾時、或取消 | jobs 表列數與送出前相同 | 自動：同上 |
| TC-015 | 作法 3、8 | 例外 | 有效確認，但內容包的 `aws.config` 被改了一個字元 | 代理處理 | 代理重建內容包後發現不相等，拒絕；沒有新檔；`start_detached` 0 次 | 自動：`test_aws_launch.py`（註解標 TC-015） |
| TC-016 | 作法 3、8 | 例外 | 內容包的 `jobQueue` 被改成別的 queue | 代理處理 | 拒絕；沒有新檔；沒有啟動 | 自動：`test_aws_launch.py`（註解標 TC-016） |
| TC-017 | 作法 3、8 | 例外 | 內容包的 samplesheet 被改了一格 | 代理處理 | 拒絕；沒有新檔；沒有啟動 | 自動：`test_aws_launch.py`（註解標 TC-017） |
| TC-018 | 作法 8 | 例外 | 專屬資料夾 `<storage_root>/_aws_runs/<run>` 已經存在 | 送出 | 拒絕、不覆蓋；原資料夾內容不變；`start_detached` 0 次 | 自動：`test_aws_launch.py::test_an_existing_run_folder_is_never_overwritten` |
| TC-019 | 作法 8 | 例外 | 專屬資料夾內預先放了一個連結（符號連結）指向別處 | 送出 | 寫入不跟隨連結，拒絕或失敗；連結指向的檔案沒被改 | 自動：`test_aws_launch.py::test_a_link_in_the_run_folder_is_never_followed` |
| TC-020 | 裁決 1（失敗時資料夾保留） | 例外 | 資料夾已建好，但寫檔中途失敗 | 送出 | 結果 `error`；已建的資料夾不被刪除，並在結果的 `left_on_site` 列出；`start_detached` 0 次 | 自動：`test_aws_launch.py`（註解標 TC-020） |
| TC-021 | 作法 8 | 例外 | 假的主控程序啟動後立刻結束，金鑰型字串出現在 `head.out` | 送出 | 結果 `error`；訊息含 `head.out` 結尾的片段；金鑰型字串被遮蔽；資料夾保留 | 自動：`test_aws_launch.py::test_a_head_that_dies_at_once_is_reported_with_its_scrubbed_tail` |
| TC-022 | 作法 8 | 例外 | 平台主機找不到 `java` | 送出 | 白話拒絕，說明缺 Java 與要裝什麼；沒有啟動 | 自動：`test_aws_launch.py::test_missing_java_nextflow_or_aws_cli_stops_the_launch_in_plain_words` |
| TC-023 | 作法 8 | 例外 | Java 版本低於 17 | 送出 | 白話拒絕，說明需要 Java 17 以上；沒有啟動 | 自動：同上 |
| TC-024 | 作法 8 | 例外 | 平台主機找不到 `nextflow` | 送出 | 白話拒絕，說明缺 Nextflow 與要裝什麼；沒有啟動 | 自動：同上 |
| TC-025 | 作法 8 | 例外 | 平台主機找不到 `aws` 指令列工具（`aws --version` 失敗） | 送出 | 白話拒絕，說明缺 aws CLI 與要裝什麼；沒有啟動 | 自動：同上 |
| TC-026 | 作法 8 | 例外 | 工作期限剩餘低於門檻（與 Slurm 同一個門檻） | 送出 | 拒絕；沒有啟動 | 自動：`test_aws_launch.py`（註解標 TC-026） |
| TC-027 | 作法 5、8 | 例外 | 送出前重跑唯讀預檢（`aws_preflight.run_preflight`：identity、job_queue、bucket），其中一項不通過（假的 aws 回報失敗） | 送出 | 拒絕並顯示預檢的白話訊息；沒有啟動 | 自動：`test_aws_launch.py`（註解標 TC-027） |
| TC-028 | 環境事實（平台主機現實） | 例外 | 代理主機沒有 `/proc`（不是 Linux 或 WSL） | 送出 | 送出前白話拒絕，說明只支援 Linux 或 WSL；沒有啟動 | 自動：`test_aws_launch.py`（註解標 TC-028） |
| TC-029 | 作法 3 | 例外 | 代理沒有回報 `storage_root` | 準備送出（建內容包） | `BundleError`，白話說「請在部署設定檔設 `storage_root`」 | 自動：`test_aws_launch.py::test_run_folder_is_under_storage_root_in_aws_runs_and_a_missing_storage_root_is_refused` |
| TC-030 | 作法 3（`NO_SCRIPTS`） | 例外 | 環境的 `preRunScript` 或 `postRunScript` 非空 | 準備送出 | 拒絕（沿用 Slurm 的「不准帶前後置腳本」規則） | 自動：`test_aws_launch.py`（註解標 TC-030） |
| TC-031 | 作法 6 | 例外 | 環境的 `workDir` 是裸 bucket（`s3://lab-bucket`，沒有子目錄） | 送出 | 在送出時拒絕，訊息說明 Nextflow 的規定（須至少含一層子目錄） | 自動：`test_aws_launch.py::test_a_bare_bucket_work_dir_is_refused_at_launch_with_nextflows_rule` |
| TC-032 | 作法 8（每步失敗就停、不重試） | 例外 | 前置檢查或啟動任一步失敗 | 送出 | `start_detached` 最多 1 次；失敗後沒有任何自動重試 | 自動：`test_aws_launch.py`（註解標 TC-032） |
| TC-033 | 作法 5、8 | 例外 | 金鑰檔、Java、Nextflow、aws CLI、預檢其中之一失敗 | 送出，之後看 `storage_root` | 沒有寫任何檔案、沒有專屬資料夾（在寫檔之前就拒絕） | 自動：`test_aws_launch.py::test_a_missing_open_or_malformed_credentials_file_stops_the_launch_before_anything_is_written`、`test_missing_java_nextflow_or_aws_cli_stops_the_launch_in_plain_words` |
| TC-034 | 環境事實（jobs.py :119–126） | 例外 | aws 環境狀態不是 `available`（例如 `creating`） | 對它排 `launch_nextflow` | 被拒，白話說明只有可用的環境才能送出；jobs 表列數不變 | 自動：`test_aws_launch.py`（註解標 TC-034） |

## User Story 2 — 內容包與設定檔（優先度 P1）

計畫作法 3、4、7：五個檔、`aws.config` 只寫文件查得到的鍵、`head.sh` 就是畫面顯示的那份。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 作法 3 | 功能 | 合法 aws 環境與 gcb 環境各建一份內容包 | 比較兩者的頂層鍵 | aws 的鍵集合＝gcb 的鍵集合去掉 `account` | 自動：`test_aws_launch.py::test_aws_bundle_has_the_five_files_and_the_expected_keys` |
| TC-036 | 作法 3 | 功能 | 合法 aws 內容包 | 看 `files` | 恰為 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`aws.config`、`head.sh` 五個 | 自動：同上 |
| TC-037 | 作法 3 | 功能 | 合法 aws 內容包 | 看 `ce` 區塊 | 鍵為 `name, platform, region, workDir, jobQueue, spot, maxvCpus, environment, nextflowConfig` | 自動：同上 |
| TC-038 | 作法 3 | 功能 | 同上 | 在 `ce` 區塊與整個內容包搜尋 | 沒有金鑰內容、沒有金鑰檔路徑 | 自動：同上 |
| TC-039 | 作法 4 | 功能 | 合法環境 `region=eu-west-1, jobQueue=lab-queue, workDir=s3://lab-bucket/work, maxvCpus=16, spot=true`，run 名稱 `r1` | 建內容包，看 `aws.config` | 內容恰為五行：`process.executor = 'awsbatch'`、`process.queue = 'lab-queue'`、`aws.region = 'eu-west-1'`、`workDir = 's3://lab-bucket/work/runs/r1/work'`、`process.resourceLimits = [cpus: 16]` | 自動：`test_aws_launch.py::test_aws_config_has_exactly_the_documented_keys` |
| TC-040 | 作法 4 | 功能 | 同上但沒設 `maxvCpus` | 看 `aws.config` | 沒有 `resourceLimits` 那一行，其餘四行不變 | 自動：同上 |
| TC-041 | 作法 4 | 功能 | 同 TC-039 | 看 `aws.config` | 不含 `aws.batch.`、`aws.accessKey`、`aws.secretKey`、`aws.profile` | 自動：同上 |
| TC-042 | 作法 4；裁決 6 | 功能 | 兩個環境只差 `spot=true` 與 `spot=false` | 各建一份 `aws.config` | 兩份內容完全相同，且都不含 `spot` 字樣（Spot 只是備註） | 自動：`test_aws_launch.py::test_spot_is_a_note_only_and_the_screen_says_aws_decides` |
| TC-043 | 作法 4 | 功能 | 環境的 `nextflowConfig` 有一段自訂內容 | 建內容包 | 自訂內容原文留在 `nextflow.config`，檔尾有 `OVERWRITE_BLOCK`；`aws.config` 是獨立的第二個檔 | 自動：`test_aws_launch.py`（註解標 TC-043） |
| TC-044 | 作法 3 | 功能 | `workDir=s3://lab-bucket/work`，run 名稱 `r1` | 看 Nextflow 工作目錄與輸出位置 | 工作目錄為 `s3://lab-bucket/work/runs/r1/work`，輸出為 `s3://lab-bucket/work/runs/r1/results` | 自動：`test_aws_launch.py::test_outdir_and_work_are_per_run_s3_prefixes` |
| TC-045 | 作法 3 | 功能 | 同一環境、兩個不同 run 名稱 | 各建一份內容包 | 兩個 run 的工作目錄與輸出前綴互不相同（每個 run 一個前綴） | 自動：同上 |
| TC-046 | 作法 3 | 功能 | 合法內容包 | 看 `params.yaml` | `input` 為 `<run_folder>/samplesheet.csv` | 自動：`test_aws_launch.py`（註解標 TC-046） |
| TC-047 | 作法 6 | 功能 | samplesheet 路徑欄位為 `s3://lab-bucket/x.fastq.gz`，`workDir` 在 `lab-bucket` | 建內容包 | 通過 | 自動：`test_aws_launch.py::test_samplesheet_paths_must_be_s3_urls_of_the_work_bucket` |
| TC-048 | 作法 6 | 例外 | 路徑欄位是本機路徑 `/home/x.fastq.gz` | 建內容包 | 拒絕 | 自動：同上 |
| TC-049 | 作法 6 | 例外 | 路徑欄位是 `gs://lab-bucket/x` | 建內容包 | 拒絕 | 自動：同上 |
| TC-050 | 作法 6 | 例外 | 路徑欄位是 `https://…` | 建內容包 | 拒絕 | 自動：同上 |
| TC-051 | 作法 6 | 例外 | 路徑欄位是 `s3://other/x`（不同 bucket） | 建內容包 | 拒絕 | 自動：同上 |
| TC-052 | 作法 6 | 例外 | 路徑欄位是 `s3://lab-bucket/../x` | 建內容包 | 拒絕 | 自動：同上 |
| TC-053 | 作法 6 | 例外 | 路徑欄位含控制字元 | 建內容包 | 拒絕 | 自動：同上 |
| TC-054 | 作法 6 | 例外 | 路徑欄位含 BIDI（文字方向控制）字元 | 建內容包 | 拒絕 | 自動：同上 |
| TC-055 | 作法 6 | 例外 | 以上任一種被拒的路徑 | 看拒絕訊息 | 訊息提到 `aws s3`，並說明「把檔案放進 bucket 是之後的功能，現在請自己放進去」 | 自動：同上 |
| TC-056 | 作法 6 | 功能 | samplesheet 有非路徑欄位（例如樣本名） | 建內容包 | 非路徑欄位不受上述規則影響 | 自動：同上 |
| TC-057 | 作法 4 | 例外 | `jobQueue`、`region`、環境變數值含引號、換行、`}` | 建內容包 | 被拒絕，或被安全處理成不能跳出設定檔文字的樣子；`aws.config` 不會出現額外的設定行 | 自動：`test_aws_launch.py::test_a_hostile_value_cannot_break_out_of_the_config_text` |
| TC-058 | 作法 3 | 功能 | 平台與代理用同一函式、同樣輸入各建一次 | 比較 | 兩份完全相等 | 自動：`test_aws_launch.py`（註解標 TC-058） |
| TC-059 | 作法 3、5 | 例外 | 設定金鑰檔路徑與一個唯一標記字串 | 建內容包後搜尋全部內容 | 內容包裡沒有金鑰檔路徑、沒有任何祕密 | 自動：`test_aws_launch.py::test_no_marker_of_the_credentials_file_reaches_a_result_a_message_or_the_database` |
| TC-060 | 作法 7 | 功能 | 合法內容包 | 看 `head.sh` 開頭 | 依序有 `#!/bin/bash`、註解行 `# credentials: the agent sets AWS_SHARED_CREDENTIALS_FILE from its own credentials file; the path is not part of this script`、`umask 077`、`cd <run_folder> \|\| exit 1` | 自動：`test_aws_launch.py::test_head_script_is_the_one_that_is_shown_and_run` |
| TC-061 | 作法 7 | 功能 | 環境變數清單有 `head: true` 的項目；另一組情境是 loopback 接收端 | 看 `head.sh` | `head: true` 的項目被 `export`；loopback 時 `NXF_OPTS` 附 `-Dhttp.nonProxyHosts=` | 自動：`test_aws_launch.py`（註解標 TC-061） |
| TC-062 | 作法 7 | 功能 | 合法內容包 | 看 `head.sh` | 有 `export TOWER_ACCESS_TOKEN="$(cat tower.token)"`，token 本身不在腳本裡 | 自動：同 TC-060 |
| TC-063 | 作法 7 | 功能 | 合法內容包 | 看 `head.sh` 最後一行 | 為 `exec nextflow run <pipeline> -r <rev> -name <run> -params-file params.yaml -c nextflow.config -c aws.config -with-tower <endpoint>`（`aws.config` 在後，後者勝） | 自動：同 TC-060 |
| TC-064 | 作法 7 | 例外 | 合法內容包 | 搜尋 `head.sh` 全文 | 不含金鑰檔路徑、不含 `AWS_SHARED_CREDENTIALS_FILE=`（名稱只准出現在註解行且沒有值）、不含 `sbatch` | 自動：同 TC-060 |
| TC-065 | 作法 7；憲法（畫面即所跑） | 功能 | 送出成功 | 比較「內容包裡的 `head.sh`」「畫面顯示的」「寫入資料夾並被執行的」 | 三者逐字相同；腳本模板只在一個函式裡 | 自動：同 TC-060 |
| TC-066 | 作法（fetch.py） | 功能 | 一個 aws run 資料夾裡有 `aws.config` | 列出可取回的紀錄檔 | `aws.config` 不被當成紀錄檔 | 自動：`test_aws_launch.py::test_fetch_run_records_does_not_list_aws_config_as_a_record` |

## User Story 3 — 送出畫面白話說明 AWS 會向實驗室收費（優先度 P1）

維護者原話（plan，第 16、46 行）：「費用顯示美元、每人每月上限、超過自動停」屬 C-3；「雲端費用照 10-18 裁示：顯示雲端自己的幣別（美元）、不換算」→ 本任務只在畫面寫「AWS 會計費」，不加任何金額或換算。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-067 | 作法 10 | 功能 | aws 環境，區域 `eu-west-1`、queue `lab-queue` | 產生送出畫面 | 第一段逐字含：「費用：按下 y 之後，這個 run 會在 AWS 區域 eu-west-1 的 job queue lab-queue 上建立 Batch 工作與運算資源，由 AWS 向實驗室的 AWS 帳號收費。平台目前還沒有費用預估與上限；實際金額請看 AWS 的帳單。主控程序跑在平台主機上，取消請用平台的取消指令。」 | 自動：`test_aws_launch.py::test_the_screen_says_aws_bills_the_lab_in_its_first_paragraph` |
| TC-068 | 作法 10 | 功能 | 同上 | 看畫面順序 | 這段費用說明在「送出確認」標題之後的第一段，在欄位清單之前 | 自動：同上 |
| TC-069 | 作法 10；維護者原話第 46 行 | 例外 | 同上 | 搜尋整個畫面 | 不含 `NT$`、`USD`、`US$`、`TWD`，也沒有「貨幣符號加數字」的金額（名稱與 pid 裡的數字不算） | 自動：同上 |
| TC-070 | 作法 10 | 功能 | 同上，`maxvCpus=16` | 看欄位 | 有：管線、版本、環境、代理、run 名稱、專屬資料夾（本機）、AWS 區域、job queue、工作目錄、結果位置、Spot 備註、samplesheet、`params.yaml`、`nextflow.config`、`aws.config`、`head.sh` | 自動：`test_aws_launch.py`（註解標 TC-070） |
| TC-071 | 作法 4；裁決 6 | 功能 | `spot=true` | 看 Spot 那一欄 | 寫明「是否 Spot 由 AWS 的 job queue 決定，這個欄位只是備註」，不暗示這個欄位會切換 Spot | 自動：`test_aws_launch.py::test_spot_is_a_note_only_and_the_screen_says_aws_decides` |
| TC-072 | 作法 10 | 功能 | 一份有 `maxvCpus=16`、一份沒有 | 各看畫面 | 有值時顯示「單一 task cpus 上限」為 16；沒值時沒有這一行 | 自動：`test_aws_launch.py`（註解標 TC-072） |
| TC-073 | 作法 10 | 功能 | run 名稱 `r1` | 看工作目錄與結果位置 | 顯示 `s3://lab-bucket/work/runs/r1/work` 與 `s3://lab-bucket/work/runs/r1/results` | 自動：`test_aws_launch.py`（註解標 TC-073） |
| TC-074 | 作法 7、10 | 功能 | 同上 | 比較畫面上的 `aws.config`、`nextflow.config`、`params.yaml`、samplesheet 與內容包的檔 | 逐字相同 | 自動：`test_aws_launch.py`（註解標 TC-074） |
| TC-075 | 作法 10 | 功能 | 一個 aws run | 產生取消畫面 | 用詞是「主控程序編號（pid）」，不是 Slurm 工作編號 | 自動：`test_aws_launch.py`（註解標 TC-075） |
| TC-076 | 作法 10 | 功能 | 同上 | 看取消畫面 | 附殘留工作提醒（沒取消乾淨的 Batch 工作仍會計費） | 自動：`test_aws_launch.py`（註解標 TC-076） |
| TC-077 | 範圍（abf_launch/cli.py） | 功能 | aws 環境的 run | 用指令列顯示工作編號處 | 用詞為「主控程序編號」，不是「Slurm 工作編號」 | 自動：`test_aws_launch.py`（註解標 TC-077） |
| TC-078 | 作法 10；不做（費用） | 不在範圍 | 同 TC-067 | 看畫面與送出流程 | 沒有任何費用估算呼叫、沒有上限數字；只有 TC-067 那句「還沒有費用預估與上限」 | 自動：`test_aws_launch.py`（註解標 TC-078） |

## User Story 4 — 本人確認後取消（優先度 P1）

計畫作法 9：取消核對順序為資料夾 → `head.pid` 相符 → `ps` 恰一行 → 擁有者 → `-name <run>` → `/proc/<pid>/cwd`，通過才送一次 SIGTERM。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-079 | 作法 9 | 功能 | 一個 aws run，所有核對都通過（假的 `ps`、`/proc`、`os.kill`），有取消的確認憑證 | 代理處理 `cancel_run` | 對該 pid 恰好送出 1 次 SIGTERM，沒有別的訊號、沒有別的 pid | 自動：`test_aws_launch.py::test_cancel_sends_one_sigterm_to_exactly_the_verified_process` |
| TC-080 | 作法 9 | 功能 | 同上 | 看結果訊息 | 為「取消請求已送出（主控程序 pid <pid>）；請到 AWS Console 的 Batch 頁確認 job 都已結束，沒取消乾淨的工作仍會計費」 | 自動：同上 |
| TC-081 | 作法 9 | 例外 | 該 pid 的程序已不存在 | 取消 | 拒絕，白話說明；`os.kill` 0 次 | 自動：`test_aws_launch.py::test_cancel_refuses_and_sends_nothing_when_the_process_is_gone_the_owner_differs_the_name_differs_or_the_cwd_differs` |
| TC-082 | 作法 9 | 例外 | `ps` 查到的不是恰好一行 | 取消 | 拒絕；`os.kill` 0 次 | 自動：同上 |
| TC-083 | 作法 9 | 例外 | 程序擁有者不是代理的使用者 | 取消 | 拒絕；`os.kill` 0 次 | 自動：同上 |
| TC-084 | 作法 9 | 例外 | 程序的 `-name` 不是這個 run 名稱 | 取消 | 拒絕；`os.kill` 0 次 | 自動：同上 |
| TC-085 | 作法 9 | 例外 | `/proc/<pid>/cwd` 不是這個 run 的專屬資料夾 | 取消 | 拒絕；`os.kill` 0 次 | 自動：同上 |
| TC-086 | 作法 9 | 例外 | `head.pid` 檔的內容與內容包／要取消的 pid 不符 | 取消 | 拒絕；`os.kill` 0 次 | 自動：`test_aws_launch.py::test_cancel_refuses_when_head_pid_does_not_match_the_bundle` |
| TC-087 | 作法 9 | 例外 | aws 的內容包，但 run 資料夾在 `_gcb_runs` 底下 | 取消 | 拒絕（資料夾與內容包不符）；`os.kill` 0 次 | 自動：`test_aws_launch.py::test_cancel_of_an_aws_run_in_a_gcb_runs_folder_is_refused` |
| TC-088 | 作法 9 | 例外 | `<storage_root>/_aws_runs/<run>` 不存在 | 取消 | 拒絕，白話說明；`os.kill` 0 次 | 自動：`test_aws_launch.py`（註解標 TC-088） |
| TC-089 | 目標；作法 9 | 例外 | 沒有取消的確認憑證（或種類是 `launch`、已用過、雜湊不符） | 代理處理 `cancel_run` | `refused`；`os.kill` 0 次 | 自動：`test_aws_launch.py`（註解標 TC-089） |
| TC-090 | 作法 2 | 功能 | aws 環境目前不是 `available`（例如停用前建立的 run 還在跑） | 對它排 `cancel_run` | 被放行（取消不要求 `available`，與 Slurm、gcb 相同） | 自動：`test_aws_launch.py`（註解標 TC-090） |

## User Story 5 — 憑證只在平台主機，只經程序環境（優先度 P1）

維護者原話（plan，第 52 行）：「雲端用戶不裝代理——平台主機自己跑 Nextflow、雲端憑證放平台主機檔案（不進資料庫）」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-091 | 作法 5 | 功能 | 假的 `start_detached` 記下 `argv, env, cwd`，金鑰檔位置由 `ABF_STATION_AWS_CREDENTIALS` 指定 | 送出成功 | `env["AWS_SHARED_CREDENTIALS_FILE"]` 等於該路徑 | 自動：`test_aws_launch.py::test_the_credentials_path_is_only_in_the_process_environment` |
| TC-092 | 作法 5 | 例外 | 同上 | 搜尋 argv、cwd、`head.sh` | 金鑰檔路徑只在 `env`，不在 argv、不在腳本 | 自動：同上 |
| TC-093 | 作法 5 | 功能 | 同上 | 看 `env` | `AWS_PROFILE == "default"` | 自動：同上 |
| TC-094 | 作法 5 | 功能 | 同上 | 看 `env` | `AWS_CONFIG_FILE` 為 `os.devnull`（與預檢環境一致） | 自動：同上 |
| TC-095 | 作法 5 | 功能 | 環境區域 `eu-west-1` | 看 `env` | `AWS_DEFAULT_REGION == "eu-west-1"` | 自動：同上 |
| TC-096 | 作法 5 | 例外 | 測試先把 `ABF_*`、`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_SESSION_TOKEN`、`TOWER_ACCESS_TOKEN` 放進 `os.environ` | 送出成功後看 `env` | 這些變數一個都不在 `env` | 自動：同上 |
| TC-097 | 作法 5 | 例外 | 測試先把 `AWS_DEFAULT_PROFILE`、另一個值的 `AWS_SHARED_CREDENTIALS_FILE` 放進 `os.environ` | 送出成功後看 `env` | `AWS_DEFAULT_PROFILE` 不在；`AWS_SHARED_CREDENTIALS_FILE` 是代理自己的路徑，不是被放進去的那個值 | 自動：同上 |
| TC-098 | 作法 5 | 功能 | 環境變數清單有 `head: true` 與不是 `head` 的各一項 | 送出成功後看 `env` | 只有 `head: true` 的項目被加進主控程序環境 | 自動：`test_aws_launch.py`（註解標 TC-098） |
| TC-099 | 作法 5 | 例外 | 憑證檔裡放一個唯一標記字串（憑證鍵名以字串拼接組出） | 跑完整流程（含失敗情境） | 在結果、訊息、`left_on_site`、資料庫的位元組裡都搜不到該標記與金鑰檔路徑 | 自動：`test_aws_launch.py::test_no_marker_of_the_credentials_file_reaches_a_result_a_message_or_the_database` |
| TC-100 | 作法 5 | 例外 | 金鑰檔不存在 | 送出 | 拒絕；專屬資料夾不存在；`start_detached` 0 次；訊息說明金鑰檔該放哪裡 | 自動：`test_aws_launch.py::test_a_missing_open_or_malformed_credentials_file_stops_the_launch_before_anything_is_written` |
| TC-101 | 作法 5 | 例外 | 金鑰檔權限 644，其他人可讀（Windows 上略過） | 送出 | 拒絕；專屬資料夾不存在；`start_detached` 0 次 | 自動：同上 |
| TC-102 | 作法 5 | 例外 | 金鑰檔缺少 `aws_secret_access_key` 那一行 | 送出 | 拒絕；專屬資料夾不存在；`start_detached` 0 次；訊息不印出檔案內容 | 自動：同上 |
| TC-103 | 作法 5 | 功能 | 假的預檢與憑證檢查函式記下呼叫 | 送出 | 啟動前代理重做 `credential_file`、`credential_shape` 兩項並重跑 `aws_preflight.run_preflight`，且都在寫第一個檔之前 | 自動：`test_aws_launch.py`（註解標 TC-103） |

## User Story 6 — 共用閘門逐型別放行（優先度 P1，本任務最容易出錯處）

計畫作法 1：awsbatch 搬進 `PLATFORM_HOST_TYPES` 時，不可連帶打開清理、上傳、資料集 destination；Google Batch 的行為位元級不變。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104 | 作法 1 表 | 功能 | 一個可用的 aws 環境 | `check_target` 輸入 `launch_nextflow`、`cancel_run`、`preflight`、`pipeline_files` | 四種都不丟例外 | 自動：`test_aws_launch.py::test_aws_environment_accepts_exactly_preflight_launch_cancel_and_pipeline_files` |
| TC-105 | 作法 1 表 | 例外 | 同上 | 輸入 `clean_work`、`put_upload`、`list_site_files`、`fetch_run_records`、`read_task_log` | 五種都被拒（`JobRefused`），訊息含「尚未支援」與型別名「AWS Batch」 | 自動：同上 |
| TC-106 | 作法 1 表 | 例外 | 同上 | 看上述五種的拒絕訊息 | 不含「Google Batch」字樣 | 自動：同上 |
| TC-107 | 作法 1 表 | 例外 | 同上 | 看上述五種的拒絕訊息 | 不含「set an agent」（不把原因說成沒設代理） | 自動：同上 |
| TC-108 | 作法 1；A9(c) | 例外 | 同上 | 看 `clean_work` 與 `put_upload` 的拒絕訊息 | 訊息裡的後續任務名分別是 `aws-clean`、`aws-upload` | 自動：`test_aws_launch.py`（註解標 TC-108）；`test_aws_ce.py::test_jobs_other_than_the_preflight_are_refused_in_plain_words` |
| TC-109 | 作法 1 | 功能 | 一個可用的 gcb 環境 | `check_target` 輸入 gcb 原有的六種 | 仍全部放行 | 自動：`test_aws_launch.py::test_google_batch_still_accepts_its_six_kinds_and_nothing_else` |
| TC-110 | 作法 1 | 例外 | 同上 | 輸入六種以外的種類 | 仍被拒，訊息文字與搬動前位元級相同（以 gcb 既有測試的期望字串為準） | 自動：同上 |
| TC-111 | 作法 1 | 例外 | `cloud_store.workdir_bucket({"platform": AWS, "config": {"workDir": "s3://lab-bucket/work"}})` | 呼叫 | 丟 `CloudPathError`，訊息仍是 gcb 的那句 | 自動：`test_aws_launch.py::test_cloud_store_stays_google_only` |
| TC-112 | 作法 1 | 例外 | 同上 | 對 aws 呼叫 `upload_prefix`、`object_url`、`big_file_command` | 三者同樣丟錯 | 自動：同上 |
| TC-113 | 作法 1 表 | 例外 | 資料集 `--destination` 填 aws 環境名 | 送出資料集指令 | 白話拒絕 | 自動：`test_aws_launch.py::test_a_dataset_destination_cannot_be_an_aws_environment` |
| TC-114 | 作法 1 表 | 例外 | 對 aws 環境直接呼叫 `jobs.enqueue_*` 排 `put_upload`、`clean_work` | 排入 | 被拒；jobs 表列數不變 | 自動：`test_aws_launch.py::test_put_upload_and_clean_work_jobs_cannot_be_queued_for_aws` |
| TC-115 | 作法 1 表 | 例外 | 代理端 `clean.run_clean` 收到 platform 為 aws 的內容包 | 處理 | 回 `Refusal`，不會落到 `rules.clean_environment`（Slurm 路徑） | 自動：同上 |
| TC-116 | 作法 1；A5；A9(a)(b) | 功能 | 載入 `compute_envs` | 看常數 | `PLATFORM_HOST_TYPES == (GCB, AWS)`；`CHECK_ONLY_TYPES == ()`；`CHECKABLE == (SUPPORTED, GCB, AWS)` | 自動：`test_aws_launch.py::test_platform_host_types_has_two_entries_and_nothing_indexes_it_by_position`；`test_gcb_ce.py` 型別常數斷言與 `test_aws_ce.py::test_the_type_constants` 的更新值 |
| TC-117 | 作法 1；A9 | 功能 | 載入 `launch` | 看常數 | `launch.GCB == "googlebatch-platform"`；`launch.AWS == "awsbatch-platform"` | 自動：同 TC-116 |
| TC-118 | 作法 1 | 例外 | 掃描 `abf_platform/`、`abf_station/` 原始碼 | 搜尋 `PLATFORM_HOST_TYPES[` | 找不到（沒有任何地方靠位置取元組） | 自動：同 TC-116 |
| TC-119 | 作法 1 | 功能 | aws 設定 `region=eu-west-1, workDir=s3://lab-bucket/work, jobQueue=lab-queue` | `validate` | 通過 | 自動：`test_aws_launch.py::test_check_dispatch_sends_each_type_to_its_own_check` |
| TC-120 | 作法 1 | 例外 | 同樣設定，但 `platform` 改為 gcb | `validate` | 因缺 `project` 被拒 | 自動：同上 |
| TC-121 | 作法 1 | 例外 | gcb 的設定，但 `platform` 改為 aws | `validate` | 由 aws 自己的檢查判（例如缺 `region`），不是被 `_check_gcb` 判 | 自動：同上 |
| TC-122 | 作法 1 | 功能 | 合法 aws 環境 | 呼叫 `snapshot` | 鍵集合恰為 `name, platform, credentialsId, region, workDir, jobQueue, spot, maxvCpus` | 自動：`test_aws_launch.py::test_snapshot_of_an_aws_environment_has_no_credential_content` |
| TC-123 | 作法 1 | 例外 | 同上，環境裡有金鑰字串（標頭以字串拼接組出） | 呼叫 `snapshot` | 所有值中搜不到金鑰字串 | 自動：同上 |
| TC-124 | 作法 1 | 功能 | 合法 gcb 環境 | 呼叫 `snapshot` | 結果與搬動前完全相同 | 自動：`test_aws_launch.py`（註解標 TC-124；與 base 比對） |
| TC-125 | 作法 1 表（preflight） | 功能 | 建立 aws 環境並執行 `ce preflight` | 等待代理回覆 | 預檢工作被放行、`ce preflight` 仍等得到並印出各項結果；建立環境時仍會排第一個預檢 | 自動：`test_aws_ce.py` 既有案例（`test_create_queues_the_first_preflight_for_the_agent`、`test_ce_preflight_waits_for_the_agent_and_prints_each_check`）保持綠 |
| TC-126 | 作法 2；裁決 5 | 功能 | 使用者只有一個可用環境且是 aws，送出時沒指名環境 | `primary_environment` | 不會自動選 aws（要明講環境名字） | 自動：`test_aws_launch.py::test_primary_environment_never_auto_picks_aws_and_naming_it_works` |
| TC-127 | 作法 2 | 功能 | 同上，但明講 aws 環境名字 | 送出 | 可以進入確認流程 | 自動：同上 |
| TC-128 | 專長守則（跨使用者） | 例外 | 第二位使用者用自己的 token 對第一位的 aws 環境送出（讀） | `launch` | 回「找不到」，與不存在的環境相同，不洩漏存在 | 自動：`test_aws_launch.py::test_another_users_aws_environment_and_run_are_not_found_for_launch_and_cancel` |
| TC-129 | 專長守則（跨使用者） | 例外 | 第二位使用者對第一位的 aws run 取消（寫） | `cancel` | 回「找不到」；沒有排入取消工作 | 自動：同上 |
| TC-130 | A5；待裁決 4 | 功能 | 看 `compute_envs.py` 原始碼 | 找 `CHECK_ONLY_TYPES` 那一行 | 空元組仍保留，旁邊有註解說明「新雲端類型先放這裡，只開預檢」 | 自動：`test_aws_launch.py`（註解標 TC-130） |

## User Story 7 — 不退步與不在範圍（優先度 P1）

計畫「不做」與「必須更新的既有斷言」：Slurm、gcb 位元級不變；續跑／重跑／清理／上傳／費用等一律白話拒絕。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-131 | 作法 1 表；不做 | 例外 | 一個 aws run | 平台端 `prepare_resume` | 白話拒絕（同 gcb 款訊息，把型別名換成 AWS Batch） | 自動：`test_aws_launch.py::test_resume_and_relaunch_of_an_aws_run_are_refused_in_plain_words` |
| TC-132 | 作法 1 表；不做 | 例外 | 同上 | 平台端 `prepare_relaunch` | 白話拒絕 | 自動：同上 |
| TC-133 | 作法 1 表；不做 | 例外 | 代理收到 aws 的續跑 | 代理 `run_resume` | 白話拒絕（`AWS_NO_RESUME`）；沒有啟動 | 自動：同上 |
| TC-134 | 完成標準 | 功能 | 同一組 Slurm 輸入，在 base 與本分支各產一次送出畫面 | 比較 | 位元級相同 | 自動：`test_aws_launch.py::test_the_slurm_and_gcb_screens_and_bundles_are_byte_identical_to_before` |
| TC-135 | 完成標準 | 功能 | 同一組 Slurm 輸入，各產一次內容包（含 `head.sh`） | 比較 | 位元級相同 | 自動：同上 |
| TC-136 | 完成標準 | 功能 | 同一組 gcb 輸入，各產一次送出畫面與取消畫面 | 比較 | 位元級相同 | 自動：同上 |
| TC-137 | 完成標準 | 功能 | 同一組 gcb 輸入，各產一次內容包 | 比較 | 位元級相同 | 自動：同上 |
| TC-138 | 範圍（abf_launch/cli.py） | 功能 | Slurm 與 gcb 的指令列輸出 | 與 base 比較 | 一字不變（尤其「Slurm 工作編號」用詞） | 自動：同上 |
| TC-139 | 作法 9；A4 | 功能 | 把 `run_cancel` 抽成 `_cancel_head` 之後，重跑 gcb 既有取消案例 | 執行 | gcb 的訊息與檢查順序不變；`test_gcb_launch.py`、`test_station_cancel.py` 既有斷言一條都沒改且全綠 | 自動：`test_aws_launch.py::test_gcb_cancel_after_the_refactor_is_byte_identical` |
| TC-140 | 必須更新的既有斷言 | 例外 | 一份 Slurm 內容包，把 `ce.platform` 竄改成 `awsbatch-platform` | 代理處理 | 仍被拒（代理重建內容包發現不符），不會被當成 aws 送出 | 自動：`test_station_launch.py` 既有的 platform type 竄改案例，保持綠且不改 |
| TC-141 | 必須更新的既有斷言 | 功能 | Azure／K8s 類型環境（取代原本用 awsbatch 的範例） | 送出 | 仍被拒，訊息含「尚未支援」；`test_launch_bundle.py` 與 `test_launch_cli.py` 只換被拒的型別，其餘斷言不變 | 自動：`test_launch_bundle.py`、`test_launch_cli.py` 更新後的案例 |
| TC-142 | 不做（不改 aws-ce-type） | 功能 | 建立 `workDir=s3://lab-bucket`（裸 bucket）的 aws 環境 | `ce create` | 建立時仍照 aws-ce-type 的規則（不因本任務改變）；只在送出時才拒絕（TC-031） | 自動：`test_aws_ce.py` 既有案例保持綠 |
| TC-143 | 不做（費用） | 不在範圍 | aws 環境 | 呼叫費用預估 | 沒有預估、沒有上限；`cloud_cost.py` 與價目表沒有 aws 內容；`test_cloud_cost.py` 既有案例保持綠 | 自動：`test_aws_launch.py`（註解標 TC-143） |
| TC-144 | 不做（上傳） | 不在範圍 | 掃描原始碼 | 搜尋 aws 上傳指令 | `abf_station/`、`abf_platform/` 沒有 `aws s3 cp -` 或完整的 `aws s3 cp` 指令字串；`put_upload` 對 aws 被拒（TC-114） | 自動：`test_aws_launch.py`（註解標 TC-144） |
| TC-145 | 不做（清理） | 不在範圍 | 掃描原始碼 | 搜尋 aws 刪除指令 | 沒有 `aws s3 rm`；清理對 aws 被拒（TC-114、TC-115） | 自動：`test_aws_launch.py`（註解標 TC-145） |
| TC-146 | 不做（第二條寫入路徑） | 不在範圍 | 掃描原始碼 | 搜尋 | 沒有 `terminate-job` 或其他會改動 AWS 的指令；`aws_launch.py` 只呼叫 `aws --version` 與既有唯讀預檢 | 自動：`test_aws_launch.py::test_no_new_write_path_for_aws`（或執行者命名，註解標 TC-146） |
| TC-147 | 不做（讀取類） | 不在範圍 | 假的 `run_fixed` 記下所有呼叫 | 對 aws 環境要求 `list_site_files`、`fetch_run_records`、`read_task_log` | 只得到白話拒絕；沒有任何 aws／S3 指令被執行 | 自動：`test_aws_launch.py`（註解標 TC-147） |
| TC-148 | 不做（設定鍵） | 不在範圍 | 合法 aws 內容包 | 搜尋 `aws.config` 與 `nextflow.config` | 沒有 `aws.batch.cliPath`、`aws.batch.platformType`、`jobRole`、`executionRole`、`aws.batch.volumes`、`aws.batch.maxSpotAttempts`，沒有 Fusion／Wave 相關設定 | 自動：`test_aws_launch.py::test_aws_config_has_exactly_the_documented_keys` |
| TC-149 | 不做；憲法 TC-085 | 不在範圍 | 看 `pyproject.toml` 與原始碼 | 搜尋 | 沒有 `boto3`、`botocore`，沒有 `import boto3` | 自動：`test_aws_launch.py::test_no_cloud_library_is_imported_and_no_new_dependency` |
| TC-150 | 不做；專長守則（對等性） | 不在範圍 | 列舉 MCP 工具與網頁路由 | 與 base 比 | MCP 工具仍 12 個；沒有新增路由或網頁畫面 | 自動：`test_aws_launch.py::test_tool_list_unchanged_and_no_new_web_route` |
| TC-151 | 作法 12；專長守則（migration） | 不在範圍 | 比對資料庫表結構 | 與 base 比 | 結構無變化（`launches.slurm_job_id` 可空整數、`jobs.kind`／`confirmations.kind` 不新增、`compute_envs` 無新欄位）；因此不需 migration | 自動：`test_aws_launch.py::test_no_migration_is_needed_for_aws_launch` |
| TC-152 | 裁決 A2；待裁決 2 | 不在範圍 | aws 預檢 | 列出預檢項目 | 仍是 aws-ce-type 的七項，沒有第 8 項 aws CLI／AMI 檢查；環境沒有 `cliPath` 欄位 | 自動：`test_aws_ce.py` 既有案例保持綠 |
| TC-153 | 不做 | 不在範圍 | 對 aws 環境的操作 | 與 base 比 `hello` 與 `clean_facts` | 輸出不變 | 自動：`test_aws_launch.py`（註解標 TC-153） |
| TC-154 | 必須更新的既有斷言；`docs/TESTING.md` | 例外 | 本任務的 `git diff --name-only` 與 diff 內容 | 驗收者逐檔看既有測試的改動 | 既有測試只動計畫列的幾處（A9(a)–(d)、`test_launch_bundle.py`、`test_launch_cli.py`、必要時 `test_gcb_ce.py` 的例外清單）；`test_gcb_launch.py`、`test_station_clean_gcb.py`、`test_cleanup_confirm.py`、`test_pipeline_files_queue.py`、`test_station_launch.py`、`test_station_cancel.py`、`test_scope.py` 與兩支 `.sh` 沒有被改；其餘既有測試檔只准「加」斷言 | 手動：`docs/TESTING.md`「aws-launch」小節 |

## User Story 8 — 文件（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-155 | 作法 11；A9(d) | 功能 | `docs/PLATFORM.md` 型別表 | 看 awsbatch 的 Supported 欄 | 逐字為 `checked and launched on the platform host (upload, clean, resume: not yet)` | 自動：`test_aws_ce.py::test_docs_list_every_aws_key_and_check` |
| TC-156 | 作法 11 | 功能 | `docs/PLATFORM.md` | 找「Launching on AWS Batch」小節 | 存在，且說明誰跑什麼（主控程序在平台主機、計算在 AWS Batch） | 自動：`test_aws_launch.py::test_docs_describe_the_launch_the_billing_sentence_and_the_requirements` |
| TC-157 | 作法 11 | 功能 | 同上 | 看需求 | 寫明平台主機要 Java 17+、Nextflow、aws CLI、憑證檔，以及 `storage_root` | 自動：同上 |
| TC-158 | 作法 11；作法 4 | 功能 | 同上 | 看 `aws.config` 鍵表 | `process.executor`、`process.queue`、`aws.region`、`workDir`、`process.resourceLimits` 每個鍵都有，且說明 `resourceLimits` 是單一 task 上限、不是總 vCPU 上限 | 自動：同上 |
| TC-159 | 作法 11 | 功能 | 同上 | 看費用段 | 白話寫明由 AWS 向實驗室的 AWS 帳號收費、平台還沒有費用預估與上限 | 自動：同上 |
| TC-160 | 作法 11 | 功能 | 同上 | 看取消段 | 說明取消只送一次 SIGTERM，且要到 AWS Console 確認殘留工作 | 自動：同上 |
| TC-161 | 作法 7；A2 | 功能 | 同上 | 看 AMI 說明 | 寫明 Batch compute AMI（或容器）要有 aws CLI | 自動：同上 |
| TC-162 | 作法 6、11 | 功能 | 同上 | 看 samplesheet 說明 | 寫明路徑必須是 `s3://` 且與工作目錄同一個 bucket、現在要自己放檔 | 自動：同上 |
| TC-163 | 作法 11；A3 | 功能 | 同上 | 看限制 | 寫明續跑、清理、上傳尚不支援 | 自動：同上 |
| TC-164 | A9(d) | 功能 | `docs/PLATFORM.md` 約 399 行 | 看那句 | 為 `Slurm, Google Cloud Batch and AWS Batch can run; the other eleven types can be modelled only.`，前一句粗體同步為 `Slurm, Google Cloud Batch and AWS Batch can run` | 自動：`test_aws_ce.py::test_docs_list_every_aws_key_and_check` |
| TC-165 | A9(d) | 功能 | `docs/SEQERA_PARITY.md` AWS Batch 那列 | 看狀態文字 | 逐字為 `Have (create + check + launch + cancel); upload and clean in aws-upload / aws-clean` | 自動：同上 |
| TC-166 | 作法 11 | 功能 | 同一列 | 看勾選框 | 仍是 `[ ]`（他在自己帳號跑通之前不勾） | 自動：同上 |
| TC-167 | A9(d) | 功能 | `docs/SEQERA_PARITY.md` 約第 84 行 | 看括號 | 為 `(create + check + launch + cancel; resume not yet)` | 自動：同上 |
| TC-168 | 完成標準（文件） | 功能 | `docs/TESTING.md` | 找「aws-launch」小節 | 存在，寫明手動驗收 1–7，以及「驗收者看 `git diff --name-only`，既有測試只動計畫列的幾處」 | 手動：`docs/TESTING.md`「aws-launch」小節（閱卷時讀文件） |
| TC-169 | 作法 11 | 功能 | `docs/INSTALL.md` 或 `docs/OPERATIONS.md` 的雲端小節 | 看內容 | 寫明平台主機要 Java 17+、Nextflow、aws CLI | 手動：閱卷時讀文件（二選一皆可） |
| TC-170 | 作法 11 | 例外 | 本任務新增或改動的文件與測試輸入 | 搜尋 | 範例只用 `lab-bucket`、`eu-west-1`、`lab-queue`、`aws-lab`；沒有真實 12 位數帳號 ID、金鑰、信箱 | 自動：`test_aws_launch.py::test_docs_describe_the_launch_the_billing_sentence_and_the_requirements` |

## User Story 9 — 維護者在自己的 AWS 帳號實跑一次（手動；優先度 P3）

計畫完成標準（手動）與裁決 A6：**會花一小筆錢，要等維護者點頭，且先設好 AWS Budgets 警示；不屬於 executor／verifier 的完成標準**。閱卷只確認這些步驟在 `docs/TESTING.md` 寫得夠具體、可照做，不要求實跑。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-171 | 手動 1；A6 | 功能 | 已設好 AWS Budgets 警示 | 檢查平台主機（WSL） | 有 Java 17+、Nextflow、aws CLI；`storage_root` 已設；金鑰檔在 `ABF_STATION_AWS_CREDENTIALS` 指的位置且權限 600 | 手動：`docs/TESTING.md`「aws-launch」步驟 1 |
| TC-172 | 手動 2 | 功能 | job queue 的 compute AMI | 確認 AMI 有 aws CLI | 有；若 task 在搬檔階段報找不到 `aws`，停手回報，不自行加設定 | 手動：同上步驟 2 |
| TC-173 | 手動 3；目標 | 功能 | 兩三個很小的檔已用 `aws s3 cp` 放進 `workDir` 同 bucket | `abf-launch … --ce aws1` | 送出畫面第一段看得到「由 AWS 向實驗室的 AWS 帳號收費」；答 y 才開始 | 手動：同上步驟 3 |
| TC-174 | 手動 3（判決待裁決 1） | 功能 | 同上 | 看主控程序是否通過 AWS 認證 | 通過；若報認證失敗（Nextflow 沒讀 `AWS_SHARED_CREDENTIALS_FILE`），記入 ledger 並回報，不自行改憑證做法 | 手動：同上步驟 3 |
| TC-175 | 手動 4 | 功能 | 送出成功 | 看畫面與主機、AWS Console | 看到「已啟動：主控程序編號…」；`<storage_root>/_aws_runs/<run>` 有 `head.pid`、`head.out`；Batch 頁出現 job；平台 run 頁出現進度；跑完 `s3://…/runs/<run>/results` 有輸出 | 手動：同上步驟 4 |
| TC-176 | 手動 5（判決 SIGTERM 是否取消 Batch job） | 功能 | 再送一個 run，中途取消 | 看 Batch 頁 | job 被終止；若沒取消乾淨，記入 ledger 回報，不自行加 `terminate-job` | 手動：同上步驟 5 |
| TC-177 | 手動 6 | 功能 | 跑過上述流程 | 在資料庫、`ce show`、畫面、日誌、`head.sh` 搜尋 | 搜不到憑證任何片段與憑證檔路徑 | 手動：同上步驟 6 |
| TC-178 | 手動 7 | 功能 | 同上 | 核對 `process.resourceLimits = [cpus: N]` | 在 awsbatch 上被接受（不報未知指令）；結果寫進 ledger | 手動：同上步驟 7 |

## 憲法與安全網

專案原則 I（只做 Seqera 做不到的事，新檔要有 `# Nothing existing:` 標頭）、「平台不啟動任何程式、`nextflow run` 只在 `launch.py`、`subprocess` 只在 `site.py`」「人答 y 才啟動」「憑證不進設定檔以外的地方」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-179 | 一條送出路徑（`nextflow run` 只在 `launch.py`） | 功能 | 本分支 | 跑 `tests/no_second_run_state_test.sh` | 通過；`aws_launch.py` 沒有 `nextflow run` 字樣 | 自動：`tests/no_second_run_state_test.sh` |
| TC-180 | 送出允許清單只有一項 | 功能 | 本分支 | 檢查 `LAUNCH_ALLOW` | 仍恰一項（不為 aws 新增第二個允許位置） | 自動：`test_aws_launch.py::test_the_launch_allow_list_still_has_one_entry` |
| TC-181 | 平台不啟動任何程式 | 例外 | 掃描 `abf_platform/`、`abf_station/` 原始碼（排除註解行） | 搜尋 `nohup`、`setsid`、`subprocess`、`Popen`、`os.system`、`nextflow run`、`sbatch` | 平台包不含；`aws_launch.py` 不含 `nextflow run`、`sbatch`、`subprocess`（`subprocess` 只在 `site.py`） | 自動：`test_aws_launch.py::test_the_platform_package_starts_no_program_and_holds_no_submission_word` |
| TC-182 | 新檔要有 `# Nothing existing:` 標頭（原則 I） | 功能 | 新增的 `aws_launch.py`、`test_aws_launch.py` | 看前 40 行 | 各有 `# Nothing existing: …`，理由為「搜過 Nextflow 的 `awsbatch` executor、Seqera `tw launch`、nf-core `tower launch`，它們都是把工作交給 Seqera 服務，沒有現成可由本機代理在確認後啟動並取消的做法」；`test_scope.py` 通過 | 自動：`platform/tests/test_scope.py` |
| TC-183 | 憑證只在設定檔／平台主機檔案 | 功能 | 新增與改動的測試檔 | 跑 `tests/credentials_stay_in_settings_test.sh` | 通過（測試中的憑證鍵名以字串拼接，不寫字面） | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-184 | 平台不讀憑證檔 | 例外 | aws 環境的建立與預檢流程 | 在平台端監看檔案讀取 | 平台程式不讀憑證檔（只有代理讀） | 自動：`test_aws_ce.py::test_the_platform_does_not_read_the_credential_file` 保持綠 |
| TC-185 | 專長守則：對等性 | 功能 | 列舉使用者可見動作與動作層函式 | 與 base 比 | 兩邊一一對應，本任務沒有新增動作也沒有新增動作層函式；路由處理函式裡沒有第二份送出邏輯 | 自動：既有對等性測試保持綠，並由 TC-150 鎖住工具與路由不變 |
| TC-186 | 專長守則：錯誤訊息與日誌 | 例外 | aws 的每一種拒絕（閘門、續跑、金鑰、缺工具、取消核對失敗） | 看訊息 | 每則都說明發生了什麼與該怎麼辦；不露出堆疊、內部路徑、SQL；不含金鑰 | 自動：`test_aws_ce.py::test_every_refusal_says_what_to_do_and_hides_internals` 的更新版本，及 TC-099 |

## User Story 10 — 維護者原話逐條對照（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-187 | 原話第 40 行：「送出的是一個 Run，用已建好的環境＋憑證名字；送出時不重新輸入憑證」 | 功能 | 已建好的 aws 環境（憑證只是名字） | 看 `abf-launch` 的參數與送出畫面 | 只需指名環境；沒有任何可輸入金鑰或金鑰檔路徑的旗標或提示；畫面沒有要求輸入憑證 | 自動：`test_aws_launch.py`（註解標 TC-187） |
| TC-188 | 原話第 52 行：「雲端用戶不裝代理」；交辦原話 | 功能 | 使用者端（呼叫 `abf-launch` 的那台）PATH 裡沒有 java、nextflow、aws | 準備送出到 aws 環境 | 使用者端仍能走到確認畫面；java／nextflow／aws 的檢查只發生在平台主機的代理 | 自動：`test_aws_launch.py`（註解標 TC-188） |
| TC-189 | 原話第 16、46 行（不換算） | 例外 | 本任務新增的 `PLATFORM.md` AWS 小節與送出畫面 | 搜尋 | 沒有金額、`NT$`、台幣換算 | 自動：`test_aws_launch.py::test_docs_describe_the_launch_the_billing_sentence_and_the_requirements` |
