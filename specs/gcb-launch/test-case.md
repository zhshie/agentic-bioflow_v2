# 測試案例：在 Google Batch 上送出與取消分析（gcb-launch，C-2）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：本任務沒有 spec.md，以 `specs/gcb-launch/plan.md`（含「維護者原話」逐字引文）為規格。
IDs: TC-001..TC-144。每條只測一件事；驗證方式「自動」＝ `platform/tests/` 下的測試，並在測試內以註解 `# TC-nnn` 標明。
-->

**規格**：`specs/gcb-launch/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「尚未支援」而不是悄悄亂做。

名詞：**主控程序**＝在平台主機上跑 Nextflow 的那個程式（Google Batch 的虛擬機只負責算）；**站台代理**＝裝在平台主機上、確認後才動手的程式；**pid**＝作業系統給程式的編號。

## User Story 1 — 本人答 y 之後，才在 Google Batch 上送出一次分析（優先度 P1）

維護者原話（plan「維護者原話」，第 167 行）：「`cancel` 以 `head.pid` 送 SIGTERM……`-with-tower` 指 loopback 的 receiver」；計畫目標：「沒有本人答 y 就不啟動」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 8；目標 | 功能 | 一個 `available` 的 gcb 環境、代理在線、有效確認憑證、金鑰檔與 Java/Nextflow 檢查都用假的通過 | 代理收到 gcb 的 `launch_nextflow` 工作 | 結果為 `done`、`ok` 為真；訊息為「已啟動：主控程序編號（pid）<pid>，run 名稱 <run>，專屬資料夾 <路徑>；Google Batch 的工作與費用從現在開始計」 | 自動：`test_gcb_launch.py::test_launch_writes_head_pid_and_reports_it_as_the_job_number` |
| TC-002 | 作法 8.5、8.7 | 功能 | 同 TC-001，假的 `start_detached` 回傳 pid | 送出成功 | 結果裡 `slurm_job_id` 等於該 pid（欄位名不改）；`head.pid` 檔內容也是同一個 pid | 自動：同上 |
| TC-003 | 作法 8.4、8.5 | 功能 | 同 TC-001，`tmp_path` 當 `storage_root` | 送出成功後看專屬資料夾 `<storage_root>/_gcb_runs/<run>` | 資料夾權限 700；裡面有 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`gcb.config`、`head.sh`、`tower.token`、`head.pid`；`tower.token` 與 `head.pid` 權限 600 | 自動：同上 |
| TC-004 | 作法 8.5 | 功能 | 同 TC-001，假的 `start_detached` 記下呼叫參數 | 送出成功 | 恰呼叫 1 次；argv 為 `["bash", "<run_folder>/head.sh"]`；cwd 是專屬資料夾；輸出檔是 `<run_folder>/head.out`；沒有用 shell | 自動：`test_gcb_launch.py::test_launch_writes_head_pid_and_reports_it_as_the_job_number`（並看假 `start_detached` 的記錄） |
| TC-005 | 作法 8.7；環境事實（`_apply_handover`） | 功能 | 平台端走完 `take_result` | 代理回報成功結果 | `launches.slurm_job_id` 等於該 pid；平台程式沒有為此改動 | 自動：`test_gcb_launch.py::test_the_platform_records_the_pid_in_the_launches_row` |
| TC-006 | 作法 2 | 功能 | gcb 環境可用 | 從 `prepare_launch` 開始送出 | 依序經過 `prepare_launch` → `check_run_name` → 確認頁 → `enqueue_launch` → 代理 `claim`；沒有另一條送出路徑 | 自動：`test_gcb_launch.py::test_a_person_must_say_yes_a_gcb_launch_is_never_auto_queued` |
| TC-007 | 目標 1；作法 8.1 | 例外 | 代理收到 gcb 的 `launch_nextflow`，但**沒有**確認憑證 | 代理處理該工作 | 結果 `refused`；`storage_root` 底下沒有任何新檔；`start_detached` 呼叫 0 次 | 自動：`test_gcb_launch.py::test_unconfirmed_gcb_launch_is_refused_and_nothing_is_written_or_started` |
| TC-008 | 同上 | 例外 | 有確認憑證但雜湊與內容包不符 | 代理處理該工作 | `refused`；沒有新檔；`start_detached` 0 次 | 自動：同上 |
| TC-009 | 同上 | 例外 | 確認憑證已經用過一次 | 再送一次同一個工作 | `refused`；沒有新檔；`start_detached` 0 次 | 自動：同上 |
| TC-010 | 同上 | 例外 | 憑證的種類是 `cancel`（不是 `launch`） | 拿它去送出 | `refused`；沒有新檔；`start_detached` 0 次 | 自動：同上 |
| TC-011 | 目標 1；作法 2 | 例外 | 對 gcb 環境發出送出要求（網頁或 `abf-launch`） | 在人答 y 之前查 jobs 表 | 還沒有任何 `launch_nextflow` 工作被建立（不會自動排進佇列） | 自動：`test_gcb_launch.py::test_a_person_must_say_yes_a_gcb_launch_is_never_auto_queued` |
| TC-012 | 目標 1 | 例外 | 同 TC-011 | 人答 n、或逾時、或取消 | jobs 表列數與送出前相同 | 自動：同上 |
| TC-013 | 作法 3、8.2 | 例外 | 有效確認，但內容包的 `gcb.config` 被改了一個字元 | 代理處理 | 代理重建內容包後發現不相等，拒絕；沒有新檔；`start_detached` 0 次 | 自動：`test_gcb_launch.py::test_a_changed_bundle_is_refused_by_the_agent` |
| TC-014 | 同上 | 例外 | 內容包的 `project` 被改成別的專案 | 代理處理 | 拒絕；沒有新檔；沒有啟動 | 自動：同上 |
| TC-015 | 同上 | 例外 | 內容包的 samplesheet 被改了一格 | 代理處理 | 拒絕；沒有新檔；沒有啟動 | 自動：同上 |
| TC-016 | 作法 8.4 | 例外 | 專屬資料夾 `<storage_root>/_gcb_runs/<run>` 已經存在 | 送出 | 拒絕、不覆蓋；原資料夾內容不變；`start_detached` 0 次 | 自動：`test_gcb_launch.py::test_an_existing_run_folder_is_never_overwritten` |
| TC-017 | 作法 8.4 | 例外 | 專屬資料夾內預先放了一個連結（符號連結）指向別處 | 送出 | 寫入不跟隨連結（`O_NOFOLLOW`），拒絕或失敗；連結指向的檔案沒被改 | 自動：`test_gcb_launch.py::test_a_link_in_the_run_folder_is_never_followed` |
| TC-018 | 作法 8.4 | 例外 | 寫檔中途失敗（例如磁碟寫不進去） | 送出 | 結果 `error`；訊息列出殘留的資料夾（`left_on_site`）；`start_detached` 0 次 | 自動：`test_gcb_launch.py`（寫入失敗案例；executor 命名並在註解標 TC-018） |
| TC-019 | 作法 8.6 | 例外 | 假的主控程序啟動後立刻結束（例如 Java 壞掉），金鑰型字串出現在 `head.out` | 送出 | 結果 `error`；訊息含結束碼與 `head.out` 末 300 字內的段落；金鑰型字串顯示為 `[hidden]`；資料夾保留 | 自動：`test_gcb_launch.py::test_a_head_that_dies_at_once_is_reported_with_its_scrubbed_tail` |
| TC-020 | 作法 8.3 | 例外 | 平台主機找不到 `java` | 送出 | 白話拒絕，說明缺 Java 與該怎麼辦；沒有啟動 | 自動：`test_gcb_launch.py::test_missing_java_or_nextflow_stops_the_launch_in_plain_words` |
| TC-021 | 作法 8.3 | 例外 | 平台主機找不到 `nextflow` | 送出 | 白話拒絕，說明缺 Nextflow 與該怎麼辦；沒有啟動 | 自動：同上 |
| TC-022 | 作法 8.3 | 例外 | Java 版本低於 17 | 送出 | 白話拒絕，說明需要 Java 17 以上；沒有啟動 | 自動：`test_gcb_launch.py::test_old_java_is_refused` |
| TC-023 | 作法 8.3 | 例外 | 工作期限剩餘低於 `MIN_REMAINING` | 送出 | 拒絕（與 Slurm 同一個門檻）；沒有啟動 | 自動：`test_gcb_launch.py`（期限案例；註解標 TC-023） |
| TC-024 | 作法 8.3 | 例外 | 送出前再跑 C-1 預檢，其中一項不通過（假的 `gcloud` 回報失敗） | 送出 | 拒絕並顯示預檢的白話訊息；沒有啟動 | 自動：`test_gcb_launch.py`（預檢失敗案例；註解標 TC-024） |
| TC-025 | 作法 3 | 例外 | 代理沒有回報 `storage_root` | 準備送出（建內容包） | `BundleError`，白話說「請在部署設定檔設 storage_root」 | 自動：`test_gcb_launch.py::test_run_folder_is_under_storage_root_and_a_missing_storage_root_is_refused_in_plain_words` |
| TC-026 | 環境事實（平台主機現實） | 例外 | 代理主機沒有 `/proc`（不是 Linux 或 WSL） | 送出 | 送出前白話拒絕，說明只支援 Linux 或 WSL；沒有啟動 | 自動：`test_gcb_launch.py`（無 /proc 案例；註解標 TC-026） |
| TC-027 | 裁決 9 | 例外 | 代理設定的 `reach` 不是本機（`local`） | 送出 | 白話拒絕；沒有啟動 | 自動：`test_gcb_launch.py`（reach 案例；註解標 TC-027） |
| TC-028 | 作法 3（`NO_SCRIPTS`） | 例外 | 環境的 `preRunScript` 或 `postRunScript` 非空 | 準備送出 | 拒絕（沿用 Slurm 的「不准帶前後置腳本」規則） | 自動：`test_gcb_launch.py`（註解標 TC-028） |
| TC-029 | 作法 7 | 例外 | 環境的 `workDir` 是裸 bucket（`gs://lab-bucket`，沒有子目錄） | 送出 | 在送出時拒絕，訊息說明 Nextflow 的規定（須至少含一層子目錄）；C-1 建立環境時的驗證不變 | 自動：`test_gcb_launch.py::test_a_bare_bucket_work_dir_is_refused_at_launch_with_nextflows_rule` |
| TC-030 | 作法 8（「失敗就停、不重試」） | 例外 | 前置檢查或啟動任一步失敗 | 送出 | `start_detached` 最多 1 次；失敗後沒有任何自動重試 | 自動：`test_gcb_launch.py`（註解標 TC-030） |
| TC-031 | 裁決 7 | 例外 | Java、Nextflow、金鑰檔、預檢其中之一失敗 | 送出，之後看 `storage_root` | 沒有寫任何檔案、沒有專屬資料夾（在寫檔之前就拒絕） | 自動：`test_gcb_launch.py::test_a_missing_or_open_or_wrong_project_key_file_stops_the_launch_before_anything_is_written`、`test_missing_java_or_nextflow_stops_the_launch_in_plain_words` |

## User Story 2 — 送出的內容包與設定檔（優先度 P1）

維護者原話（第 167 行）：「config 追加 `process.executor='google-batch'; google{project; location; batch.spot}`，`workDir` gs://」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 作法 3 | 功能 | 合法 gcb 環境與輸入 | 建 gcb 內容包 | 鍵為 `version, agent, ce, run_name, run_folder, pipeline, revision, samplesheet, params, path_columns, tower, files, pipeline_source`，**沒有** `account`；`files` 恰好五個：`samplesheet.csv`、`params.yaml`、`nextflow.config`、`gcb.config`、`head.sh` | 自動：`test_gcb_launch.py::test_gcb_bundle_has_the_five_files_and_the_expected_keys` |
| TC-033 | 作法 3 | 功能 | 平台與代理用同樣輸入各建一次 | 比對 | 兩份內容包完全相等 | 自動：`test_gcb_launch.py::test_gcb_bundle_is_identical_when_built_twice_from_the_same_inputs` |
| TC-034 | 作法 4；維護者原話 | 功能 | 全欄位合法環境（project `lab-project-1`、workDir `gs://lab-bucket/work`） | 建 `gcb.config` | 含 `process.executor = 'google-batch'`、`google.project`、`google.location`、`workDir = 'gs://lab-bucket/work/runs/<run>/work'`、`google.batch.spot = true`、`google.batch.bootDiskSize = 50.GB`、`serviceAccountEmail`、`network`、`subnetwork`、`usePrivateAddress`；沒有表以外的鍵 | 自動：`test_gcb_launch.py::test_gcb_config_has_exactly_the_documented_keys` |
| TC-035 | 作法 4 | 功能 | 環境未設 `spot` | 建 `gcb.config` | **沒有** `google.batch.spot` 那一行 | 自動：同上 |
| TC-036 | 作法 4 | 功能 | `bootDiskSize` 存成 `50 GB` | 建 `gcb.config` | 寫成 `50.GB` | 自動：`test_gcb_launch.py::test_boot_disk_size_is_written_in_nextflow_units` |
| TC-037 | 作法 4 | 功能 | `bootDiskSize` 存成 `50GB` | 建 `gcb.config` | 寫成 `50.GB` | 自動：同上 |
| TC-038 | 作法 4、裁決 6 | 功能 | 環境設了 `maxvCpus` 為 N | 建 `gcb.config` | 寫成 `process.resourceLimits = [cpus: N]`（單一 task 的 cpus 上限） | 自動：`test_gcb_launch.py::test_max_vcpus_is_written_as_a_per_task_limit_and_the_screen_does_not_call_it_a_total` |
| TC-039 | 作法 4 | 功能 | 環境有 `labels` | 建 `gcb.config` | `process.resourceLabels` 含使用者的 labels 與固定一組 `abf-run=<run 名稱>` | 自動：`test_gcb_launch.py::test_labels_and_the_run_label_are_written_and_a_long_run_name_is_cut_to_63` |
| TC-040 | 作法 4 | 功能 | run 名稱超過 63 字 | 建 `gcb.config` | `abf-run` 的值只取前 63 字 | 自動：同上 |
| TC-041 | 作法 4（逐值跳脫） | 例外 | `labels` 值、`bootDiskImage`、`network` 含引號、換行或 `}` | 建內容包 | 建包時拒絕或被安全跳脫；產出的 `gcb.config` 行數只有預期的行數，沒有被注入的設定 | 自動：`test_gcb_launch.py::test_a_hostile_value_cannot_break_out_of_the_config_text` |
| TC-042 | 作法 3 | 功能 | `storage_root` 為某目錄 | 建內容包 | `run_folder` 為 `<storage_root>/_gcb_runs/<run_name>` | 自動：`test_gcb_launch.py::test_run_folder_is_under_storage_root_and_a_missing_storage_root_is_refused_in_plain_words` |
| TC-043 | 作法 3 | 功能 | 同 TC-034 | 看 `params.yaml` | `outdir` 為 `gs://lab-bucket/work/runs/<run>/results`；`input` 為 `<run_folder>/samplesheet.csv`；work 目錄是 `…/runs/<run>/work`（每個 run 一個前綴） | 自動：`test_gcb_launch.py::test_outdir_and_work_are_per_run_gs_prefixes` |
| TC-044 | 作法 6；目標「顯示全部會被送出的內容」 | 功能 | 送出成功 | 比對畫面上的 `head.sh` 文字、寫進資料夾的 `head.sh`、交給 `start_detached` 的檔案 | 三者內容完全相同 | 自動：`test_gcb_launch.py::test_head_script_is_the_one_that_is_shown_and_run` |
| TC-045 | 作法 6 | 功能 | 同上 | 看 `head.sh` 最後一行 | 為 `exec nextflow run <pipeline> -r <revision> -name <run> -params-file params.yaml -c nextflow.config -c gcb.config -with-tower <endpoint>`；開頭有 `umask 077` 與 `cd <run_folder>` | 自動：同上 |
| TC-046 | 作法 6 | 功能 | 同上 | 搜 `head.sh` | 不含 `sbatch`、`#SBATCH` | 自動：同上 |
| TC-047 | 作法 6 | 功能 | 同上 | 看 `head.sh` | 含註解 `# credentials: the agent sets GOOGLE_APPLICATION_CREDENTIALS from its own key file; the path is not part of this script`，且不含金鑰檔路徑 | 自動：`test_gcb_launch.py::test_the_key_path_is_only_in_the_process_environment` |
| TC-048 | 作法 5、6 | 功能 | 環境 `environment` 有一項 `head: true`、一項非 head | 送出 | `head: true` 的變數在 `head.sh` 裡被 export、主控程序拿得到；非 head 的不會 | 自動：`test_gcb_launch.py`（註解標 TC-048） |
| TC-049 | 作法 4 | 功能 | 使用者的 `nextflowConfig` 有自由文字 | 看檔案 | 原文留在 `nextflow.config`，檔尾沿用 `OVERWRITE_BLOCK`（不在 `gcb.config`）；`head.sh` 以 `-c nextflow.config -c gcb.config` 順序疊加（後者勝） | 自動：`test_gcb_launch.py`（註解標 TC-049） |
| TC-050 | 作法 4 | 功能 | 合法環境 | 搜 `gcb.config` | 沒有 `maxSpotAttempts`、沒有 `queueSize` | 自動：`test_gcb_launch.py::test_gcb_config_has_exactly_the_documented_keys` |
| TC-051 | 作法 4 | 功能 | `network`／`subnetwork` 為短名稱 `default` | 建 `gcb.config` | 短名稱原樣寫入（不自行補成完整路徑） | 自動：`test_gcb_launch.py`（註解標 TC-051） |
| TC-052 | 作法 7 | 功能 | samplesheet 路徑欄位為 `gs://lab-bucket/x.fastq.gz`，workDir bucket 是 `lab-bucket` | 建內容包 | 通過 | 自動：`test_gcb_launch.py::test_samplesheet_paths_must_be_gs_urls_of_the_work_bucket` |
| TC-053 | 作法 7 | 例外 | 路徑欄位為本機路徑 `/home/x.fastq.gz` | 建內容包 | 拒絕；訊息提到把檔案放進 bucket 是之後的功能（C-6），現在請自己用 `gcloud storage cp` 放進去 | 自動：同上 |
| TC-054 | 作法 7 | 例外 | 路徑欄位為 `s3://…` | 建內容包 | 拒絕，訊息提到 `gcloud storage cp` | 自動：同上 |
| TC-055 | 作法 7 | 例外 | 路徑欄位為 `https://…` | 建內容包 | 拒絕，訊息提到 `gcloud storage cp` | 自動：同上 |
| TC-056 | 作法 7 | 例外 | 路徑欄位為 `gs://other/x`（不同 bucket） | 建內容包 | 拒絕，訊息提到 `gcloud storage cp` | 自動：同上 |
| TC-057 | 作法 7 | 例外 | 路徑欄位為 `gs://lab-bucket/../x` | 建內容包 | 拒絕，訊息提到 `gcloud storage cp` | 自動：同上 |
| TC-058 | 作法 7 | 例外 | 路徑欄位含控制字元或雙向文字（BIDI）字元 | 建內容包 | 拒絕 | 自動：`test_gcb_launch.py`（註解標 TC-058） |
| TC-059 | 作法 7 | 功能 | 非路徑欄位（如 strandedness）的值不是 `gs://` | 建內容包 | 不受影響，照常通過 | 自動：`test_gcb_launch.py::test_samplesheet_paths_must_be_gs_urls_of_the_work_bucket` |
| TC-060 | 作法 7 | 功能 | `params` 的某個值是本機路徑樣子的字串 | 建內容包 | 不檢查路徑（與 Slurm 一致） | 自動：`test_gcb_launch.py`（註解標 TC-060） |
| TC-061 | 作法 6 | 例外 | `revision` 不是固定版本（例如分支名） | 建內容包 | 拒絕（`-r` 只收固定版本，與 Slurm 同） | 自動：`test_gcb_launch.py`（註解標 TC-061） |

## User Story 3 — 送出畫面白話說明「Google 會計費」（優先度 P1）

維護者原話：「費用顯示美元……本任務只負責『畫面上白話說明 Google 會計費』，且不得出現任何台幣換算」；「雲端費用照 10-18 裁示：顯示雲端自己的幣別（美元）、不換算……」→ 送出畫面不加任何金額或換算。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-062 | 作法 10 | 功能 | gcb 內容包 | 產生送出畫面 | 畫面含連續的一句「由 Google 向實驗室的 Google Cloud 帳號收費」；整段為「費用：按下 y 之後，這個 run 會在 Google Cloud 專案 <project> 裡建立 Batch 工作與虛擬機，由 Google 向實驗室的 Google Cloud 帳號收費。平台目前還沒有費用預估與上限；實際金額請看 Google 的帳單。主控程序跑在平台主機上，取消請用平台的取消指令。」 | 自動：`test_gcb_launch.py::test_the_screen_says_google_bills_the_lab_in_its_first_paragraph` |
| TC-063 | 作法 10 | 功能 | 同上 | 看畫面順序 | 標題「送出確認」之後的**第一段**就是費用段（在管線、環境等欄位之前） | 自動：同上 |
| TC-064 | 作法 10 | 功能 | 專案名為 `lab-project-1` | 看費用段 | 段內有專案名 `lab-project-1` | 自動：同上 |
| TC-065 | 維護者原話；作法 10 | 不在範圍 | 同上 | 搜整個 gcb 送出畫面 | 不含 `NT$`、`USD`、`US$`、`TWD`，也不含貨幣符號加數字的金額（名稱或 pid 裡的數字不算）；沒有估價、沒有上限數字 | 自動：同上 |
| TC-066 | 作法 10 | 功能 | 環境有 `spot` 與 `maxvCpus` | 看畫面欄位 | 有：管線、版本、環境、代理、run 名稱、專屬資料夾（本機）、Google 專案、區域、工作目錄（gs://…/work）、結果位置（gs://…/results）、Spot 與否、單一 task 的 cpus 上限（有設才顯示）、samplesheet、`params.yaml`、`nextflow.config`、`gcb.config`、`head.sh` | 自動：`test_gcb_launch.py`（註解標 TC-066） |
| TC-067 | 作法 4、裁決 6 | 功能 | 環境設了 `maxvCpus` | 看畫面 | 寫的是「單一 task 的 cpus 上限」，沒有說成「全部 vCPU 的總上限」 | 自動：`test_gcb_launch.py::test_max_vcpus_is_written_as_a_per_task_limit_and_the_screen_does_not_call_it_a_total` |
| TC-068 | 作法 10 | 功能 | gcb 的 run、有 pid | 產生取消畫面 | 標題與欄位用「主控程序編號（pid）」，並附同樣的提醒（殘留的 Batch 工作要自己確認） | 自動：`test_gcb_launch.py`（註解標 TC-068） |
| TC-069 | 範圍（`cli.py` 三處） | 功能 | `abf-launch` 終端機流程 | 對 gcb 環境與 Slurm 環境各取消／顯示一次 | gcb 用「主控程序編號（pid）」的用詞；Slurm 的輸出一字不變 | 自動：`test_gcb_launch.py`（註解標 TC-069）；Slurm 側由既有 `test_launch_cli.py` 原樣綠 |

## User Story 4 — 經本人確認後取消正在跑的 run（優先度 P1）

維護者原話（第 167 行）：「`cancel` 以 `head.pid` 送 SIGTERM（Nextflow 自己取消 Batch jobs）」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 作法 9.4 | 功能 | 有效取消確認；假的 `ps` 與 `/proc` 全符合（擁有者、`-name <run>`、cwd） | 代理執行取消 | `os.kill` 恰呼叫 1 次、訊號 SIGTERM、pid 正確 | 自動：`test_gcb_launch.py::test_cancel_sends_one_sigterm_to_exactly_the_verified_process` |
| TC-071 | 作法 9.5 | 功能 | 同上 | 看結果 | `ok` 為真、`slurm_job_id` 是 pid；訊息含「請到 Google Cloud Console」並提醒沒取消乾淨的虛擬機仍會計費 | 自動：同上 |
| TC-072 | 作法 9.3 ① | 例外 | `ps` 查不到該 pid（已結束） | 取消 | 拒絕「已結束，不取消」；`os.kill` 0 次 | 自動：`test_gcb_launch.py::test_cancel_refuses_and_sends_nothing_when_the_process_is_gone_the_owner_differs_the_name_differs_or_the_cwd_differs` |
| TC-073 | 作法 9.3 ② | 例外 | 該 pid 的擁有者不是代理自己的使用者 | 取消 | 拒絕；`os.kill` 0 次 | 自動：同上 |
| TC-074 | 作法 9.3 ③ | 例外 | 該 pid 的 `args` 不含 `-name <run>` | 取消 | 拒絕；`os.kill` 0 次 | 自動：同上 |
| TC-075 | 作法 9.3 ④ | 例外 | 該 pid 的 cwd 不是專屬資料夾 | 取消 | 拒絕；`os.kill` 0 次 | 自動：同上 |
| TC-076 | 作法 9.2 | 例外 | `head.pid` 內容與確認內容包的編號不同 | 取消 | 拒絕；`os.kill` 0 次 | 自動：`test_gcb_launch.py::test_cancel_refuses_when_head_pid_does_not_match_the_bundle` |
| TC-077 | 作法 9.1 | 例外 | 沒有取消確認憑證 | 取消 | 拒絕；`os.kill` 0 次 | 自動：`test_gcb_launch.py::test_cancel_refuses_an_unconfirmed_or_reused_confirmation` |
| TC-078 | 作法 9.1 | 例外 | 取消確認憑證已用過 | 再取消一次 | 拒絕；`os.kill` 0 次 | 自動：同上 |
| TC-079 | 作法 9.2 | 例外 | 內容包的資料夾不等於用代理自己的 `storage_root` 重算出的 `<storage_root>/_gcb_runs/<run>` | 取消 | 拒絕（不信內容包）；`os.kill` 0 次 | 自動：`test_gcb_launch.py`（註解標 TC-079） |
| TC-080 | 作法 9.4；裁決 8 | 不在範圍 | 取消成功或失敗的各種情形 | 看程式行為 | 只送一次 SIGTERM；不重試、不迴圈、不 `kill -9`、不呼叫 `gcloud` 去刪或取消 Batch 工作 | 自動：`test_gcb_launch.py::test_cancel_sends_one_sigterm_to_exactly_the_verified_process` |
| TC-081 | 作法 9（平台側不改） | 功能 | gcb 的 run 取消成功 | 看平台 | `cancel_requested_at` 被寫入 | 自動：`test_gcb_launch.py::test_cancel_request_time_is_recorded_for_a_gcb_run` |
| TC-082 | 作法 1 | 功能 | gcb 環境狀態不是 `available`（之後壞了），但有正在跑的 run | 取消 | 不因環境狀態被擋（跟 Slurm 一樣） | 自動：`test_gcb_launch.py::test_cancel_needs_no_available_status` |

## User Story 5 — 憑證只在平台主機，不外洩（優先度 P1）

維護者原話：「雲端憑證放平台主機檔案（不進資料庫）」；「憑證：只在平台主機檔案（600），資料庫只存 `credentialName`；`credential_findings` 仍擋鍵值」；「送出的是『一個 Run』，用的是已建好的環境＋憑證名字；不在送出時重新輸入憑證」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-083 | 作法 5 | 功能 | 假 `start_detached` 記下 argv、env、cwd | 送出 | 金鑰檔路徑只出現在 `env["GOOGLE_APPLICATION_CREDENTIALS"]`；不在 argv、不在 `head.sh`、不在內容包、不在 `head.out` 以外的任何回傳 | 自動：`test_gcb_launch.py::test_the_key_path_is_only_in_the_process_environment` |
| TC-084 | 作法 5 | 功能 | 代理程序環境裡有 `ABF_*`、`TOWER_ACCESS_TOKEN` 與別的 `GOOGLE_APPLICATION_CREDENTIALS` | 送出，看交給主控程序的 env | 不含任何 `ABF_*`、不含 `TOWER_ACCESS_TOKEN`；`GOOGLE_APPLICATION_CREDENTIALS` 是代理自己設定的那個路徑；`CLOUDSDK_CORE_DISABLE_PROMPTS=1` | 自動：同上 |
| TC-085 | 作法 5；憲法安全網 | 例外 | 金鑰檔裡放唯一標記字串（標頭字串在測試裡以拼接組出，不寫字面） | 跑完整流程（含失敗路徑） | 回給平台的結果、訊息、`left_on_site`、`launches`／`jobs` 資料庫位元組都搜不到該標記 | 自動：`test_gcb_launch.py::test_no_marker_of_the_key_file_reaches_a_result_a_message_or_the_database` |
| TC-086 | 作法 5 | 例外 | 金鑰檔不存在 | 送出 | 拒絕並沿用 C-1 的白話訊息；專屬資料夾不存在；`start_detached` 0 次 | 自動：`test_gcb_launch.py::test_a_missing_or_open_or_wrong_project_key_file_stops_the_launch_before_anything_is_written` |
| TC-087 | 作法 5 | 例外 | 金鑰檔權限是 644（Windows 跳過） | 送出 | 拒絕；專屬資料夾不存在；`start_detached` 0 次 | 自動：同上 |
| TC-088 | 作法 5 | 例外 | 金鑰檔內的 `project_id` 與環境的專案不符 | 送出 | 拒絕；專屬資料夾不存在；`start_detached` 0 次 | 自動：同上 |
| TC-089 | 作法 5 | 功能 | 送出成功 | 看 `head.out` 權限 | 為 600 | 自動：`test_gcb_launch.py`（註解標 TC-089） |
| TC-090 | 維護者原話 | 功能 | 建立並送出 gcb 環境 | 查資料庫 | 只存憑證**名字**（`credentialName`）；沒有金鑰內容或金鑰路徑 | 自動：`test_gcb_launch.py::test_no_marker_of_the_key_file_reaches_a_result_a_message_or_the_database` |
| TC-091 | 維護者原話 | 例外 | 建立 gcb 環境時把金鑰鍵值塞進設定 | 建立 | 仍被 `credential_findings` 擋下（C-1 行為不退步） | 自動：既有 `test_gcb_ce.py` 的對應測試原樣綠 |
| TC-092 | 維護者原話（第 40 行） | 功能 | 已建好的 gcb 環境 | `prepare_launch(ce="gcb1")` 或網頁選該環境 | 送出只需要環境名字；送出流程沒有要求輸入憑證的參數或提示 | 自動：`test_gcb_launch.py::test_primary_environment_never_auto_picks_google_batch_and_naming_it_works` |

## User Story 6 — 平台只放行該放行的工作，且各人的環境互相看不到（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-093 | 作法 1 | 功能 | `available` 的 gcb 環境、代理在線 | `check_target` 檢查 `launch_nextflow` 與 `cancel_run` | 兩者都不丟例外（C-1 時是被拒的） | 自動：`test_gcb_launch.py::test_check_target_lets_launch_and_cancel_through_for_an_available_gcb_environment` |
| TC-094 | 作法 1 | 例外 | 同上 | 送 `list_site_files`（含 `enqueue_listing`） | 被拒，訊息含「尚未支援」，不含 `C-2`、「set an agent」、「has no agent」 | 自動：`test_gcb_launch.py::test_check_target_still_refuses_listing_fetch_and_task_log_in_plain_words` |
| TC-095 | 作法 1 | 例外 | 同上 | 送 `fetch_run_records` | 被拒，訊息含「尚未支援」，不含 `C-2` | 自動：同上 |
| TC-096 | 作法 1 | 例外 | 同上 | 送 `read_task_log` | 被拒，訊息含「尚未支援」，不含 `C-2` | 自動：同上 |
| TC-097 | 作法 1 | 例外 | gcb 環境狀態為 `invalid`／`creating`／`disabled` | 送出 | 被拒 | 自動：`test_gcb_launch.py::test_launch_on_a_gcb_environment_that_is_not_available_is_refused` |
| TC-098 | 作法 2、裁決 5 | 功能 | 只有一個 `available` 的 gcb 環境 | 查 `primary_environment` | 回傳 None（不會自動選到會花錢的環境） | 自動：`test_gcb_launch.py::test_primary_environment_never_auto_picks_google_batch_and_naming_it_works` |
| TC-099 | 作法 2 | 功能 | 同上 | `prepare_launch(ce="gcb1")` | 成功 | 自動：同上 |
| TC-100 | 憲法專長守則（跨使用者，寫） | 例外 | 使用者 A 有環境 `gcb1`；使用者 B 的 token | B 用 `gcb1` 的名字送出 | 被拒，說法與「找不到」相同 | 自動：`test_gcb_launch.py::test_another_users_gcb_environment_and_run_are_not_found_for_launch_and_cancel` |
| TC-101 | 憲法專長守則（跨使用者，寫） | 例外 | A 有一個 gcb 的 run | B 取消 A 的 run | 被拒 | 自動：同上 |
| TC-102 | 作法 11 | 例外 | 一個 gcb 環境的 run | 平台 `prepare_resume` | 被拒，訊息「Google Batch 的 run 還不能續跑或原樣重跑（尚未支援）」 | 自動：`test_gcb_launch.py::test_resume_and_relaunch_of_a_gcb_run_are_refused_in_plain_words` |
| TC-103 | 作法 11 | 例外 | 同上 | 平台 `prepare_relaunch` | 被拒，同樣的白話訊息 | 自動：同上 |
| TC-104 | 作法 11 | 例外 | 代理收到 gcb 的續跑工作（繞過平台） | 代理 `run_resume` | 代理端再擋一次，拒絕；沒有啟動 | 自動：同上 |
| TC-105 | 範圍（`fetch.py`） | 功能 | 專屬資料夾內有 `gcb.config` | `fetch_run_records` 的紀錄清單 | `gcb.config` 不被當作 Nextflow 紀錄列出（在 `_NOT_RECORDS`） | 自動：`test_gcb_launch.py::test_fetch_run_records_does_not_list_gcb_config_as_a_record` |

## User Story 7 — 不在範圍的事沒有被做，也沒有退步（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-106 | 不做：費用 | 不在範圍 | 看 repo | 找檔案 | 沒有 `cloud_cost.py`、沒有 `rates.json`；沒有估價、上限、自動停的程式 | 自動：`test_gcb_ce.py::test_nothing_of_the_later_slices_exists`（保留的那部分） |
| TC-107 | 不做：上傳 | 不在範圍 | 看原始碼 | 搜 `storage cp` | 原始碼沒有 `storage cp`（上傳是 C-6）；本機路徑會被拒並說明（見 TC-053） | 自動：同上 |
| TC-108 | 不做：刪除／第二條寫入路徑 | 不在範圍 | 看原始碼 | 搜 `gcloud batch jobs delete`／`cancel`、`buckets create`、`services enable`、`service-accounts create`、`storage rm` | 都沒有 | 自動：同上 |
| TC-109 | 不做：平台 worker | 不在範圍 | 看 repo | 找檔名與字樣 | 沒有 `abf_platform/local_runner.py`；平台裡沒有新增 worker、執行緒、常駐迴圈 | 自動：`test_gcb_launch.py::test_the_platform_package_starts_no_program_and_holds_no_submission_word`；`test_scope.py` TC-071 原樣綠 |
| TC-110 | 不做：新工具／路由 | 不在範圍 | 看 MCP 與網頁 | 數工具與路由 | MCP 工具仍 12 個；沒有新增網頁路由 | 自動：`test_gcb_launch.py::test_tool_list_unchanged_and_no_new_web_route` |
| TC-111 | 不做：其他雲 | 不在範圍 | AWS Batch／Azure／K8s 類型的環境 | 送出 | 仍白話說「尚未支援」，行為與 C-1 相同 | 自動：既有 `test_launch_cli.py:306-312`、`test_launch_bundle.py` 原樣綠 |
| TC-112 | 不做：Wave／Fusion／GPU／多 bucket／Workload Identity | 不在範圍 | 任何合法環境 | 看 `gcb.config` 與原始碼 | 沒有 Wave、Fusion、GPU、instance template、Workload Identity 相關鍵；samplesheet 只收同 bucket（見 TC-056） | 自動：`test_gcb_launch.py::test_gcb_config_has_exactly_the_documented_keys` |
| TC-113 | 作法 14 | 不在範圍 | 看資料庫結構 | 列 `launches`、`compute_envs`、`jobs` 欄位 | 與 C-1 時相同，沒有新增欄位、沒有 migration | 自動：`test_gcb_launch.py::test_no_migration_is_needed_and_the_columns_are_unchanged` |
| TC-114 | 不做：雲端函式庫 | 不在範圍 | 看 `pyproject.toml` 與原始碼 | 搜 | 沒有 `google-cloud` 依賴、沒有 `import google`／`boto3` | 自動：`test_gcb_launch.py::test_no_cloud_library_is_imported_and_no_new_dependency` |
| TC-115 | 不改 Slurm 任何位元組 | 功能 | 同一組固定 Slurm 輸入 | 在 base 與本分支各產生一次內容包、送出畫面、`head.sh` | 逐位元相同 | 自動：`test_gcb_launch.py::test_the_slurm_screen_and_bundle_are_byte_identical_to_before` |
| TC-116 | 不改 C-1 預檢與驗證 | 功能 | C-1 的預檢清單 | 看 `CHECK_NAMES` 與其測試 | 清單未變（Java／Nextflow 檢查只在送出前，不加進預檢）；C-1 的驗證規則未變 | 自動：既有 `test_gcb_ce.py` 預檢相關測試原樣綠 |
| TC-117 | 必須更新的既有斷言 | 功能 | 看 `test_gcb_ce.py` 的四處 | 比對 base 與本分支 | 只有計畫列的更新：①jobs 種類測試改為只拒 `list_site_files`／`fetch_run_records`／`read_task_log`，`launch_nextflow`／`cancel_run` 不被拒；②該函式改名為 `test_launch_is_allowed_but_the_environment_is_never_auto_picked`，第一行改為 `is None`，其餘不動；③`test_nothing_of_the_later_slices_exists` 只拿掉 `local_runner.py` 與 `_local_head\|head\.pid\|local_runner` 兩條，其餘保留；④文件斷言換成新字樣、勾選仍為 `[ ]` | 手動：驗收者逐處比對 `git diff` |
| TC-118 | 範圍：檔案（只准改這些） | 功能 | 看 `git diff --name-only <base>...HEAD` | 比對計畫「範圍」清單 | 沒有清單以外的檔案；`records.py`、`web*.py`、`agent.py`、`hello`／`clean_facts` 沒被改；Slurm 相關既有測試（`test_station_launch.py`、`test_station_cancel.py`、`test_station_resume.py`、`test_launch_bundle.py`、`test_station_envs.py`、`test_scope.py`）一行都沒動；不得有 spec 或 `test-case*.md` 被改 | 手動：`docs/TESTING.md` gcb-launch 小節「驗收者看 `git diff --name-only`」 |
| TC-119 | 完成標準 | 功能 | 既有測試 | 跑全套 | `test_station_launch.py`（含 `test_unconfirmed_launch_is_refused`）、`test_station_cancel.py`、`test_station_resume.py`、`test_launch_bundle.py`、`test_launch_cli.py`、`test_station_envs.py`、`test_station_e2e.py::test_tc031`、`test_scope.py` 全部原樣綠，其中 `test_station_docs.py` 若紅只准改被跳過那一列的判斷 | 自動：全套 |

## User Story 8 — 文件讓人看得懂、做得到（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-120 | 作法 13 | 功能 | `docs/PLATFORM.md` 第 8 節 | 看型別表 | `googlebatch-platform` 的 Supported 欄為 `Slurm-like confirmed launch and cancel on the platform host (resume: not yet)`；「Only Slurm…」那句為 `Slurm and Google Cloud Batch can run; the other types can be modelled only` | 自動：`test_gcb_launch.py::test_docs_describe_the_launch_the_billing_sentence_and_the_requirements` |
| TC-121 | 作法 13 | 功能 | `docs/PLATFORM.md` 新小節「Launching on Google Batch」 | 看內容 | 含：誰跑什麼（主控程序在平台主機、計算在 Batch）、Java 17+／Nextflow／gcloud 與金鑰檔、`storage_root`、samplesheet 要 `gs://` 且同 bucket、`gcb.config` 每個鍵的對照、Google 向實驗室帳號收費的段落、取消與殘留工作提醒、不能續跑 | 自動：同上 |
| TC-122 | 作法 13 | 功能 | `docs/SEQERA_PARITY.md` F 節 | 看 Google Cloud Batch 那列 | 為 `Have (create + check + launch + cancel; resume not yet)`，勾選仍是 `[ ]`（他在自己的帳號跑通前不勾） | 自動：`test_gcb_ce.py::test_docs_list_every_gcb_key_and_check`（更新後） |
| TC-123 | 完成標準（文件） | 功能 | `docs/TESTING.md` | 看「gcb-launch」小節 | 寫明手動驗收第 1–6 步，以及「驗收者看 `git diff --name-only`、C-1 測試只動計畫列的四處」 | 手動：閱讀 `docs/TESTING.md` |
| TC-124 | 作法 13；C-1 裁決 4 | 功能 | `docs/INSTALL.md` 或 `docs/OPERATIONS.md` 的雲端小節（至少其一） | 看內容 | 寫明平台主機要有 Java 17+、Nextflow、gcloud | 自動：`test_gcb_launch.py::test_docs_describe_the_launch_the_billing_sentence_and_the_requirements` |
| TC-125 | 作法 13 | 功能 | 所有新文件與範例 | 搜範例名稱 | 只用 `lab-project-1`、`runner@lab-project-1.iam.gserviceaccount.com`、`gs://lab-bucket/work`；沒有真實信箱 | 自動：同上 |

## User Story 9 — 維護者在自己的帳號上真的跑通一次（優先度 P1，手動，會花很小一筆錢）

維護者原話（第 50 行）：「雲端第一個真實使用者＝他自己的自費帳號；……年底若只能交兩塊＝**雲端跑通＋花費控制**與**網頁全流程（國網）**」→「跑通」要在他自己的帳號上真的跑一次最小的分析。前提：C-0 帳號與 C-1 的 `available` 都完成，GCP 帳單預算與警示已設。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-126 | 完成標準 手動 1 | 功能 | 平台主機（WSL） | 檢查 Java、Nextflow、gcloud、`storage_root`、金鑰檔 | Java 17+、Nextflow、gcloud 都在；`storage_root` 已設；金鑰檔在 `ABF_STATION_GCP_CREDENTIALS` 指的位置且權限 600 | 手動：`docs/TESTING.md` gcb-launch 第 1 步 |
| TC-127 | 完成標準 手動 2 | 功能 | 兩三個很小的檔已用 `gcloud storage cp` 放進 `workDir` 同一個 bucket | `abf-launch … --ce gcb1` | 送出畫面第一段看到「由 Google 向實驗室的 Google Cloud 帳號收費」；答 y 才開始 | 手動：同上 第 2 步 |
| TC-128 | 完成標準 手動 3 | 功能 | 已答 y | 看輸出、資料夾、Console、平台 run 頁 | 看到「已啟動：主控程序編號…」；`ls <storage_root>/_gcb_runs/<run>` 有 `head.pid`、`head.out`；Google Cloud Console 的 Batch 頁出現 job；平台 run 頁出現進度（`-with-tower` 通）；跑完 `gs://…/runs/<run>/results` 有輸出 | 手動：同上 第 3 步 |
| TC-129 | 完成標準 手動 4 | 功能 | 再送一個，中途用取消指令取消 | 看 Batch 頁 | job 被取消或刪除（驗證 SIGTERM 會讓 Nextflow 取消 Batch 工作）；若沒取消乾淨，記入 ledger 並回報 developer-agent，**不得**自行加 `gcloud batch jobs delete` | 手動：同上 第 4 步 |
| TC-130 | 完成標準 手動 5 | 功能 | 前面各步完成 | 在平台資料庫、`ce show`、送出畫面、日誌、`head.sh` 搜金鑰片段與金鑰檔路徑 | 都搜不到 | 手動：同上 第 5 步 |
| TC-131 | 完成標準 手動 6 | 功能 | 實跑過 | 核對 `process.resourceLabels` 是否出現在 Batch job 的標籤；若有設短名稱 `network`／`subnetwork`，看是否被接受 | 兩項結果寫進 `specs/gcb-launch/ledger.md`；不支援的標籤段落依計畫處理並記錄 | 手動：同上 第 6 步 |

## 憲法與安全網

本任務動到：原則 1（先搜過現成做法）、原則 2（唯一送出路徑與人的確認）、原則 3（不寫死路徑）、原則 4（指令層不指名排程器）、安全網（送出完整顯示並等確認；寫入工具未確認一律拒絕；憑證不外洩、平台不存憑證）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-132 | 原則 2（唯一送出檔） | 功能 | `tests/no_second_run_state_test.sh` | 執行 | 綠；`LAUNCH_ALLOW` 仍只有 `platform/abf_station/launch.py` 一筆，對應測試仍是 `test_unconfirmed_launch_is_refused` | 自動：`test_gcb_launch.py::test_the_launch_allow_list_still_has_one_entry`；`bash tests/no_second_run_state_test.sh` |
| TC-133 | 原則 2（平台不啟動程式） | 功能 | 掃 `abf_platform/` 與 `abf_station/` | 搜字樣 | `subprocess`、`Popen`、`os.system` 只在 `site.py`；`nohup`、`setsid` 不出現在這兩個資料夾；`nextflow run` 與 `sbatch` 不在新檔 `gcb_launch.py`，也不在本任務於 `site.py`、`launch.py` 之外新增的任何一行（`handlers.py` 既有的 `sbatch` 探測字樣屬 base，不算） | 自動：`test_gcb_launch.py::test_the_platform_package_starts_no_program_and_holds_no_submission_word` |
| TC-134 | 原則 2、裁決 3 | 功能 | 直接測 `site.start_detached` | monkeypatch `subprocess.Popen` 後呼叫 | `shell` 非真、`start_new_session=True`、`stdin` 為 DEVNULL、輸出導向指定檔；`site.py` 仍是唯一呼叫 `subprocess` 的檔案 | 自動：`test_gcb_launch.py::test_start_detached_uses_a_fixed_argv_no_shell_and_a_new_session` |
| TC-135 | 原則 2（人的確認管道） | 例外 | gcb 環境、沒有人答 y | 經 MCP 工具與網頁路由各試圖送出 | 兩條都被拒；pending request、token、模型自己的答覆都不算人的 yes | 自動：`test_human_channel.py::test_tch09_*`、`test_confirm_page.py::test_tch09_b_c_*` 原樣綠，加上 TC-011／TC-012 |
| TC-136 | 安全網（寫入工具未確認即拒絕，含取消） | 例外 | gcb 的取消 | 未經人答覆就取消（MCP 與網頁） | 被拒；`os.kill` 0 次 | 自動：`test_gcb_launch.py::test_cancel_refuses_an_unconfirmed_or_reused_confirmation`；`test_actions_layer.py::test_tcb04_*`～`test_tcb08_*` 原樣綠 |
| TC-137 | 安全網（送出指令完整顯示再等確認） | 功能 | gcb 送出 | 在 y 之前看畫面 | 畫面含 samplesheet、`params.yaml`、`nextflow.config`、`gcb.config`、`head.sh` 的完整內容，與之後實際寫入的相同 | 自動：`test_gcb_launch.py::test_head_script_is_the_one_that_is_shown_and_run` |
| TC-138 | 安全網（憑證只在設定區） | 功能 | `tests/credentials_stay_in_settings_test.sh` | 執行 | 綠；新測試檔不含金鑰標頭字面（以拼接組出） | 自動：`bash tests/credentials_stay_in_settings_test.sh` |
| TC-139 | 安全網（平台不存憑證） | 功能 | 既有密鑰測試 | 執行 | `test_secrets.py`（`test_tc040_*`、`test_tc042_*`、`test_tc_i03_*`）、`test_nextflow_e2e.py::test_tc041_*`、`test_human_channel.py::test_tcf10_f11_*` 原樣綠 | 自動：`tests/platform_test.sh` |
| TC-140 | 原則 1（先搜過現成做法） | 功能 | 新檔 `gcb_launch.py`、`test_gcb_launch.py` | 看前 40 行 | 各有 `# Nothing existing: …`（至少 15 字，寫明搜過 Nextflow `google-batch` executor、Seqera `tw launch`、nf-core `tower launch`） | 自動：`test_scope.py` TC-070 |
| TC-141 | 原則 2、作法 8 | 功能 | `gcb_launch.py` 原始碼 | 搜字樣 | 不出現 `nextflow run`、`sbatch` 字樣 | 自動：`test_gcb_launch.py::test_the_platform_package_starts_no_program_and_holds_no_submission_word` |
| TC-142 | 原則 3（不寫死路徑） | 功能 | `tests/no_hardcoded_paths.sh` | 執行 | 綠；專屬資料夾路徑由 `storage_root` 推出 | 自動：`bash tests/no_hardcoded_paths.sh` |
| TC-143 | 原則 4（指令層站台中立） | 功能 | `tests/command_layer_is_site_neutral.sh` | 執行 | 綠 | 自動：`bash tests/command_layer_is_site_neutral.sh` |
| TC-144 | 完成標準 | 功能 | WSL／Linux | 跑 `tests/platform_test.sh` 與全套 `tests/run_all.sh` | 全綠；`HEAD` 的完成記號與工作樹乾淨 | 自動：全套 |

<!--
Rules for the writer:
- 編號不重編；刪除的案例保留該列並劃掉。
- 「註解標 TC-nnn」＝計畫沒有替該情境指定測試名稱，executor 自行命名，並在測試內以 `# TC-nnn` 註解標明，供閱卷者對應。
-->
