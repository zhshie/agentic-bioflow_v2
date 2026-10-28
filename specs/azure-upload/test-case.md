# 測試案例：把本機檔案上傳到 Azure Batch 環境的 Blob（azure-upload，put_upload）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：本任務沒有 spec.md，以 `specs/azure-upload/plan.md` 為規格，含「維護者原話」、「失敗先行測試」AZU-*、文末 developer-agent 裁決 1–12 與「裁決（10-29 01:4x）」13–21。裁決與上文衝突時以裁決為準（見總覽「不確定的地方」）。
IDs: TC-001..TC-124。每條只測一件事；驗證方式「自動」＝ `platform/tests/test_azure_upload.py`（或計畫指定要更新、或保持不動的既有測試檔），並在測試內以註解 `# TC-nnn` 標明。計畫的 AZU-* 名稱寫在「對應需求」欄。
所有測試輸入都用假值：`labcontainer`、`labstore`、`westeurope`、`azure-lab`、`alice`、`bob`；全部用假的 `site.run_fixed`（必要時假 `site.start_fed`），`tmp_path` 當儲存根目錄與暫存目錄；不碰網路、不呼叫真的 az、不花錢。
憑證相關的鍵名與假金鑰在測試裡用字串相加組出來，避免被 `tests/credentials_stay_in_settings_test.sh` 掃到。
-->

**規格**：`specs/azure-upload/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「尚未支援」而不是悄悄亂做。

名詞：**站台代理**＝裝在平台主機上、唯一會真的執行 `az` 指令的程式（平台本身不碰 Azure）；**暫存檔**＝使用者傳到平台主機上傳資料夾（`<ABF_STATION_UPLOADS>/<擁有者>/`）的那份檔案，傳到 Blob 並核對大小相符之後才會被刪；**放行表**＝`compute_envs.CLOUD_JOB_KINDS`，每一種雲端環境各自列出它肯接的工作種類；**位置**＝`az://容器/名稱`、`s3://…`、`gs://…` 這種寫法；**前綴**＝某個人專屬的那一段，例如 `az://labcontainer/uploads/alice/`；**假的 run_fixed**＝測試裡取代真正啟動 `az` 的替身，會記下收到的指令（argv）與環境變數（env）；**argv**＝指令拆成一個個字的清單；本檔的 2 GB 是十進位 2,000,000,000 位元組。

## User Story 1 — 只有 Azure 的「上傳」被打開，其他仍關著（優先度 P1）

計畫目標與作法 1；維護者採納的 aws-launch 裁決 A3：「clean 與 upload 在各自的任務完成前維持關閉。→ Azure 同樣處理；本任務完成後 `put_upload` 對 Azure 才打開，`clean_work` 仍關（直到 azure-clean）」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；作法 1；AZU-GATE-01 | 功能 | Azure 環境 `azure-lab`（location `westeurope`、storageAccountName `labstore`、workDir `az://labcontainer/work`）狀態 `available`，代理在線；alice 的上傳資料夾裡有 5 位元組的 `reads.fastq.gz` | alice 對 `azure-lab` 呼叫 `enqueue_put_upload` | 排入恰好 1 筆 `put_upload` 工作；工作的 `dest`＝`az://labcontainer/uploads/alice/reads.fastq.gz`、`owner`＝alice、`name`＝`reads.fastq.gz`、`size`＝5 | 自動：`test_azure_upload.py::test_azure_env_may_queue_put_upload_when_available` |
| TC-002 | 作法 1；AZU-GATE-01 | 例外 | `azure-lab` 狀態是 `creating`（不是 `available`），其餘同 TC-001 | alice 呼叫 `enqueue_put_upload` | 被拒；訊息白話說明只有可用（available）的環境才能存檔、並提示先做預檢；工作表列數不變 | 自動：同上 |
| TC-003 | 作法 1；AZU-GATE-02 | 功能 | 載入 `compute_envs` | 看 Azure 那一格的放行種類 | 恰為 `preflight`、`launch_nextflow`、`cancel_run`、`pipeline_files`、`put_upload` 五個；不含 `clean_work` | 自動：`test_azure_upload.py::test_put_upload_gate_is_a_per_type_table_not_a_shared_tuple` |
| TC-004 | AZU-GATE-02；目標（Google 一個字都不變） | 功能 | 同上 | 看 Google 那一格的放行種類 | 恰為 `preflight`、`launch_nextflow`、`cancel_run`、`clean_work`、`put_upload`、`pipeline_files` 六個，與修改前完全相同 | 自動：同上 |
| TC-005 | AZU-GATE-02；目標（AWS 一個字都不變） | 功能 | 同上 | 看 AWS 那一格的放行種類 | 恰為 `preflight`、`launch_nextflow`、`cancel_run`、`clean_work`、`put_upload`、`pipeline_files` 六個，與修改前完全相同 | 自動：同上 |
| TC-006 | 作法 1（逐型別放行，不新增共用元組、沿用「查表」判斷） | 功能 | 一個 `available` 的 Azure 環境和一個 `available` 的 Google 環境；測試內暫時把 Azure 那一格的 `put_upload` 拿掉，再放回 | 各排一次 `put_upload` | 拿掉時 Azure 被拒、放回時 Azure 通過；Google 兩次都通過。證明放行是查那張表，不是寫死「只給某幾家」 | 自動：同上 |
| TC-007 | 作法 1；AZU-GATE-03；裁決 5；維護者採納的 A3 | 例外 | `available` 的 Azure 環境 | 對它排 `clean_work` | 被拒；訊息含「尚未支援」與 `azure-clean`，不含 `azure-launch`、`azure-upload`；工作表列數不變 | 自動：`test_azure_upload.py::test_clean_work_and_resume_still_refused_for_azure` |
| TC-008 | 作法 1；AZU-GATE-03 | 例外 | `available` 的 Azure 環境，有一個已結束的 run | 對它要求續跑（resume） | 仍被拒（Azure 的續跑本任務不開放）；沒有排入任何工作 | 自動：同上 |
| TC-009 | 範圍 `jobs.py` 第三處寫死文字 | 例外 | 一個 `available` 的 Slurm 環境 | 對它排 `put_upload` | 被拒，用白話說這種環境不能放雲端資料，且說明可以放的環境包含 Azure Batch（與 Google Batch、AWS Batch 並列）；工作表列數不變 | 自動：`test_azure_upload.py`（註解標 TC-009） |
| TC-010 | 專長守則（跨使用者，寫） | 例外 | `azure-lab` 屬於 alice；bob 另有帳號與權杖，且 bob 自己的上傳資料夾裡也有同名檔 | bob 用自己的身分對 `azure-lab` 呼叫 `enqueue_put_upload` | 回答與「環境不存在」一樣（找不到這個計算環境）；工作表列數不變 | 自動：`test_azure_upload.py`（註解標 TC-010） |
| TC-011 | 目標（Google 版行為與輸出不變） | 功能 | `available` 的 Google Batch 環境（workDir `gs://labcontainer/work`），alice 有上傳檔 | alice 對它呼叫 `enqueue_put_upload` | 排入 1 筆工作，`dest`＝`gs://labcontainer/uploads/alice/<檔名>`，與修改前相同 | 自動：`test_cloud_upload.py`（既有，斷言一個字不改） |
| TC-012 | 專長守則（確認管道）；作法 1；裁決 18 | 例外 | 一個 `available` 的 Azure 環境；有人想用一般的排工作入口（泛用排工作，不是 `enqueue_put_upload`）直接排 `put_upload` | 試排 | 被拒，說明上傳只能走專用入口；工作表列數不變 | 自動：`test_azure_upload.py`（註解標 TC-012） |
| TC-013 | 不做（不開放 Azure 的 `list_site_files`） | 不在範圍 | `available` 的 Azure 環境 | 對它排 `list_site_files` | 被拒，用白話說這種工作尚未支援；工作表列數不變 | 自動：`test_azure_ce.py::test_no_new_write_path_for_azure`（保留 `clean_work`、`list_site_files`，只拿掉 `put_upload`） |

## User Story 2 — `az://` 位置的表示法與歸屬判斷（優先度 P1）

計畫作法 2、環境事實、裁決 3、7、10。上傳前綴 `uploads/<owner>/` 與 `workDir` 的子資料夾是同一個容器下的兄弟路徑。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | AZU-LOC-01 | 功能 | Azure 環境 workDir `az://labcontainer/work` | 呼叫 `workdir_bucket` | 回 `labcontainer` | 自動：`test_azure_upload.py::test_workdir_bucket_for_azure_is_the_container` |
| TC-015 | AZU-LOC-01；裁決 10 | 功能 | 同上 | 呼叫 `workdir_scheme` | 回 `az` | 自動：同上 |
| TC-016 | AZU-LOC-01 | 例外 | Azure 環境 workDir 是 `az://labcontainer`（沒有子資料夾） | 呼叫 `workdir_bucket` | 丟 `CloudPathError` | 自動：同上 |
| TC-017 | AZU-LOC-01 | 例外 | Azure 環境 workDir 是 `az://LabContainer/work`（容器名含大寫） | 呼叫 `workdir_bucket` | 丟 `CloudPathError` | 自動：同上 |
| TC-018 | AZU-LOC-01 | 例外 | Azure 環境 workDir 是 `az://lab--container/work`（容器名含 `--`） | 呼叫 `workdir_bucket` | 丟 `CloudPathError` | 自動：同上 |
| TC-019 | AZU-LOC-01 | 例外 | Azure 環境 workDir 是 `az://ab/work`（容器名太短） | 呼叫 `workdir_bucket` | 丟 `CloudPathError` | 自動：同上 |
| TC-020 | 作法 2（Azure 環境認 `az://` 開頭的 workDir） | 例外 | Azure 環境的 workDir 是 `s3://labcontainer/work` | 呼叫 `workdir_bucket` | 丟 `CloudPathError`，訊息白話、不露出堆疊 | 自動：`test_azure_upload.py`（註解標 TC-020） |
| TC-021 | 裁決 10；範圍 A.6 | 例外 | Slurm 環境 | 呼叫 `workdir_scheme` | 丟 `CloudPathError`；訊息含「不能放雲端資料」，並把 Azure Batch 列進可以放的類型 | 自動：`test_azure_upload.py`（註解標 TC-021） |
| TC-022 | AZU-LOC-02 | 功能 | Google 環境（workDir `gs://…`） | 呼叫 `workdir_bucket`、`workdir_scheme`、`upload_prefix`、`object_url`、`big_file_command` | 五個回傳都與修改前逐字相同（`workdir_scheme`＝`gs`；超限指令仍是 `gcloud storage cp …`） | 自動：`test_azure_upload.py::test_google_and_aws_location_behaviour_is_unchanged` |
| TC-023 | AZU-LOC-02 | 功能 | AWS 環境（workDir `s3://…`） | 呼叫同樣五個函式 | 五個回傳都與修改前逐字相同（`workdir_scheme`＝`s3`；超限指令仍是 `aws s3 cp … --recursive`） | 自動：同上 |
| TC-024 | 範圍 A.6（Google 與 AWS 逐字訊息不准動） | 例外 | 沒有 `gs://` workDir 的 Google 環境；沒有 `s3://` workDir 的 AWS 環境 | 各呼叫 `workdir_bucket` | 訊息分別與修改前逐字相同（例如「這個計算環境沒有 gs:// 的 workDir，不能放雲端資料 (this environment has no gs:// workDir)」） | 自動：`test_aws_upload.py`、`test_cloud_upload.py`（既有，斷言一個字不改） |
| TC-025 | AZU-LOC-03 | 功能 | Azure 環境 workDir `az://labcontainer/work` | 呼叫 `object_url(alice, "reads.fastq.gz")` | 回 `az://labcontainer/uploads/alice/reads.fastq.gz` | 自動：`test_azure_upload.py::test_az_object_url_is_inside_the_owners_prefix` |
| TC-026 | AZU-LOC-03 | 功能 | 同上 | 對 `az://labcontainer/uploads/alice/x` 呼叫 `inside_prefix`（alice 的前綴） | 回真 | 自動：同上 |
| TC-027 | 作法 2；AZU-LOC-03 | 例外 | 同上 | `inside_prefix` 收到 `uploads/alice2/x`（前綴撞名） | 回假 | 自動：同上 |
| TC-028 | 作法 2；AZU-LOC-03 | 例外 | 同上 | `inside_prefix` 收到 `az://labcontainer/uploads/alice/../bob/x` | 回假 | 自動：同上 |
| TC-029 | 作法 2；AZU-LOC-03 | 例外 | 同上 | `inside_prefix` 收到 `az://labcontainer/uploads//x`（空段） | 回假 | 自動：同上 |
| TC-030 | 作法 2；AZU-LOC-03 | 例外 | 同上 | `inside_prefix` 收到 `az://other-container/uploads/alice/x`（別的容器） | 回假 | 自動：同上 |
| TC-031 | 作法 2；AZU-LOC-04 | 功能 | Azure 環境 workDir `az://labcontainer/runs-a` | 看 alice 的上傳位置 | 是 `az://labcontainer/uploads/alice/x`，不在 `runs-a/` 之下 | 自動：`test_azure_upload.py::test_uploads_prefix_does_not_overlap_the_workdir_subfolder` |
| TC-032 | 作法 2（`parse_az` 同 `parse_s3` 的形狀） | 例外 | 無 | `parse_az("az://labcontainer/uploads/../bob/x")` | 丟 `CloudPathError`，說位置不能含 `..` | 自動：`test_azure_upload.py`（註解標 TC-032） |
| TC-033 | 作法 2（容器規則重用 `_AZURE_CONTAINER` 並加不准 `--`） | 例外 | 無 | `parse_az` 收到容器名含大寫、含 `--`、只有 2 個字的位置 | 每個都丟 `CloudPathError` | 自動：`test_azure_upload.py`（註解標 TC-033） |
| TC-034 | 裁決 7（沿用既有檔名檢查，含 255 字元） | 例外 | 同 TC-025 | `object_url` 收到的檔名含 `/`、含 `\`、含 `..`、含 NUL、空字串、256 個字元 | 每個都丟 `CloudPathError` | 自動：`test_azure_upload.py`（註解標 TC-034） |

## User Story 3 — 站台代理重新判斷一切、用固定指令寫入、核對大小才刪暫存檔（優先度 P1）

計畫作法 3–7、AZU-AGT-01～11、裁決 1、2、4、5、14、17、19、21。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 作法 4；AZU-AGT-01；裁決 19 | 功能 | 代理收到一筆合法的 `put_upload`（alice、`reads.fastq.gz`、5 位元組）；憑證檔有帳號金鑰；假 `run_fixed` | 代理處理 | 假 `run_fixed` 的上傳呼叫，argv 以 `az storage blob upload` 開頭，並含成對的 `--account-name labstore`、`--container-name labcontainer`、`--name uploads/alice/reads.fastq.gz`、`--file <暫存檔的絕對路徑>` | 自動：`test_azure_upload.py::test_agent_uploads_with_fixed_argv_and_no_secret_in_argv` |
| TC-036 | 作法 4；AZU-AGT-01 | 功能 | 同 TC-035 | 看同一個 argv | 含成對的 `--overwrite true`、`--output none` 與單獨的 `--no-progress` | 自動：同上 |
| TC-037 | 作法 4；AZU-AGT-01；不做（不用 `--account-key`、`--sas-token`、`--connection-string`） | 例外 | 同 TC-035，憑證檔金鑰是測試組出的假金鑰 | 看 argv 的每一個字 | 不含 `--account-key`、`--sas-token`、`--connection-string`，也不含那串假金鑰；argv 是清單、沒有 shell | 自動：同上 |
| TC-038 | 裁決 14、19 | 功能 | 同 TC-035（憑證檔有帳號金鑰） | 看上傳 argv | 含成對的 `--auth-mode key`；除 TC-035、TC-036 列的旗標外沒有多餘旗標 | 自動：同上 |
| TC-039 | 裁決 19 | 功能 | 憑證檔只有 SAS、沒有帳號金鑰 | 代理處理，看上傳 argv | 不含 `--auth-mode`，也不含 `--sas-token`；其餘旗標配對與 TC-035、TC-036 相同 | 自動：同上 |
| TC-040 | 作法 4（用 `run_fixed`、逾時 3600 秒）；裁決 2 | 功能 | 同 TC-035 | 看上傳那一次呼叫 | 走 `site.run_fixed`，逾時是 3600 秒；沒有呼叫 `site.start_fed` | 自動：`test_azure_upload.py`（註解標 TC-040） |
| TC-041 | 作法 6；AZU-AGT-02 | 功能 | 同 TC-035 | 看傳給 `run_fixed` 的 env | 含 `AZURE_STORAGE_ACCOUNT=labstore`、`AZURE_STORAGE_KEY`（值＝測試組出的假金鑰）、`AZURE_CONFIG_DIR`（呼叫當下存在的資料夾）、`AZURE_CORE_COLLECT_TELEMETRY=false` | 自動：`test_azure_upload.py::test_agent_env_has_the_storage_credentials_and_nothing_else_from_the_parent` |
| TC-042 | 作法 6；AZU-AGT-02 | 例外 | 測試先在父行程塞假的 `AZURE_*` 值與 `ABF_X=假值` | 看傳給 `run_fixed` 的 env | 父行程塞的 `AZURE_*`（憑證檔給的除外）與所有 `ABF_*` 都不出現 | 自動：同上 |
| TC-043 | 作法 6；AZU-AGT-02 | 功能 | 憑證檔只有 SAS | 看 env | 有 `AZURE_STORAGE_SAS_TOKEN`，沒有 `AZURE_STORAGE_KEY` | 自動：同上 |
| TC-044 | 作法 6；裁決 4；azure-launch 裁決 2 | 功能 | 憑證檔同時有帳號金鑰與 SAS | 看 env 與 argv | 用帳號金鑰（env 有 `AZURE_STORAGE_KEY`、argv 有 `--auth-mode key`） | 自動：同上 |
| TC-045 | 作法 6；裁決 5 | 例外 | 父行程與測試塞了假的 `AZURE_BATCH_*` 值 | 看傳給上傳與驗大小兩次呼叫的 env | 沒有任何 `AZURE_BATCH_*` | 自動：同上 |
| TC-046 | 作法 6；AZU-AGT-02 | 功能 | 同 TC-035，上傳成功 | 呼叫結束後看當時的 `AZURE_CONFIG_DIR` 路徑 | 那個資料夾已被刪 | 自動：同上 |
| TC-047 | 作法 6（用完在 `finally` 刪） | 例外 | 假 `run_fixed` 回非 0 | 呼叫結束後看 `AZURE_CONFIG_DIR` 路徑 | 那個資料夾已被刪 | 自動：`test_azure_upload.py`（註解標 TC-047） |
| TC-048 | 作法 5；裁決 3、14 | 功能 | 同 TC-035，上傳成功 | 看驗大小那一次 `run_fixed` | argv 以 `az storage blob show` 開頭，含成對的 `--account-name labstore`、`--container-name labcontainer`、`--name uploads/alice/reads.fastq.gz`、`--query properties.contentLength`、`--output tsv`、`--auth-mode key`；逾時 60 秒；env 規則同 TC-041、TC-042、TC-045 | 自動：`test_azure_upload.py::test_size_is_checked_with_blob_show_before_the_staged_file_goes` |
| TC-049 | 作法 3；AZU-AGT-03 | 例外 | 工作擁有者 alice，`dest` 是 `az://labcontainer/runs/x` | 代理處理 | 拒絕；`run_fixed` 0 次 | 自動：`test_azure_upload.py::test_agent_rejudges_dest_and_refuses_a_foreign_prefix` |
| TC-050 | 作法 3；AZU-AGT-03 | 例外 | `dest` 是 `az://other-container/uploads/alice/reads.fastq.gz` | 代理處理 | 拒絕；`run_fixed` 0 次 | 自動：同上 |
| TC-051 | 作法 3；AZU-AGT-03 | 例外 | `dest` 是 `az://labcontainer/uploads/bob/reads.fastq.gz` | 代理處理 | 拒絕；`run_fixed` 0 次 | 自動：同上 |
| TC-052 | 作法 3（`dest` 必須等於重算出的 `object_url`） | 例外 | `dest` 是 `az://labcontainer/uploads/alice/../bob/x` | 代理處理 | 拒絕；`run_fixed` 0 次 | 自動：`test_azure_upload.py`（註解標 TC-052） |
| TC-053 | 作法 3（暫存檔在 `<ABF_STATION_UPLOADS>/<owner>/`） | 例外 | 工作的擁有者名字是 `../bob` | 代理處理 | 拒絕；`run_fixed` 0 次 | 自動：`test_azure_upload.py`（註解標 TC-053） |
| TC-054 | 作法 3（`size` 在 1..2 GB） | 例外 | `size` 是 0 | 代理處理 | 拒絕，訊息說大小要在 1 位元組到 2 GB 之間；`run_fixed` 0 次 | 自動：`test_azure_upload.py`（註解標 TC-054） |
| TC-055 | 作法 3；裁決 2 | 例外 | `size` 是 2,000,000,001 | 代理處理 | 拒絕；`run_fixed` 0 次 | 自動：同上 |
| TC-056 | 作法 3；AZU-AGT-07 | 例外 | 暫存檔是符號連結（指向別的檔） | 代理處理 | 拒絕；`run_fixed` 0 次 | 自動：`test_azure_upload.py::test_symlinked_or_resized_staged_file_is_refused` |
| TC-057 | 作法 3；AZU-AGT-07 | 例外 | 暫存檔實際大小與工作的 `size` 不符 | 代理處理 | 拒絕；`run_fixed` 0 次；暫存檔仍在 | 自動：同上 |
| TC-058 | 作法 3（是一般檔案） | 例外 | 暫存檔的位置是一個資料夾 | 代理處理 | 拒絕；`run_fixed` 0 次 | 自動：`test_azure_upload.py`（註解標 TC-058） |
| TC-059 | 作法 5；AZU-AGT-04；裁決 11 | 例外 | 假 `run_fixed` 對 `blob show` 回與本機不同的大小 | 代理處理 | 結果失敗，訊息含「雲端物件大小與本機不符，暫存檔保留，請重新上傳」；暫存檔仍在 | 自動：`test_azure_upload.py::test_size_is_checked_with_blob_show_before_the_staged_file_goes` |
| TC-060 | 作法 5；AZU-AGT-04 | 功能 | 假 `run_fixed` 對 `blob show` 回與本機相同的大小 | 代理處理 | 結果成功；暫存檔被刪 | 自動：同上 |
| TC-061 | 範圍 `jobs.py`（`put_upload` 結果處理，`path` 上限 1100） | 功能 | 同 TC-060 的成功結果 | 平台收下代理回報的結果 | 工作標為完成，記錄的 `path` 是 `az://labcontainer/uploads/alice/reads.fastq.gz`（沒有被當成 `gs://`／`s3://` 以外的東西拒掉或截壞） | 自動：`test_azure_upload.py`（註解標 TC-061） |
| TC-062 | 作法 5；AZU-AGT-05；A4 | 例外 | 假 `run_fixed` 對 `blob show` 丟逾時（`TimeoutError`） | 代理處理 | 結果是 done，訊息說「已上傳…，但沒能核對雲端大小；暫存檔保留」；暫存檔仍在 | 自動：`test_azure_upload.py::test_unreadable_size_keeps_the_staged_file` |
| TC-063 | 作法 5；AZU-AGT-05 | 例外 | 假 `run_fixed` 對 `blob show` 丟 `OSError` | 代理處理 | 同 TC-062 | 自動：同上 |
| TC-064 | 作法 5；AZU-AGT-05 | 例外 | 假 `blob show` 輸出不是數字 | 代理處理 | 同 TC-062 | 自動：同上 |
| TC-065 | 作法 6；AZU-AGT-06；裁決 21 | 例外 | 憑證檔不存在 | 代理處理 | 失敗；`run_fixed` 0 次；訊息用白話說明憑證沒備好該找管理者，不含憑證檔路徑，不含任何金鑰值 | 自動：`test_azure_upload.py::test_missing_credentials_file_fails_without_leaking_its_content` |
| TC-066 | 作法 6；AZU-AGT-06 | 例外 | 憑證檔存在，但帳號金鑰與 SAS 都沒有 | 代理處理 | 同 TC-065 | 自動：同上 |
| TC-067 | 裁決 17 | 例外 | 憑證檔有帳號金鑰，但沒有 `batch_account_key` | 代理處理 | 拒絕（與送出 run 同一份憑證檔的規則）；`run_fixed` 0 次；訊息不含金鑰值與路徑 | 自動：`test_azure_upload.py`（註解標 TC-067） |
| TC-068 | 作法 4（前後 lstat）；AZU-AGT-08 | 例外 | 假 `run_fixed` 在上傳期間把暫存檔換成別的檔案（dev/ino 變了） | 代理處理 | 結果失敗；暫存檔保留、沒有被刪 | 自動：`test_azure_upload.py::test_staged_file_swapped_during_the_upload_is_not_deleted` |
| TC-069 | 作法 4（前後 lstat） | 例外 | 假 `run_fixed` 在上傳期間讓暫存檔大小改變 | 代理處理 | 結果失敗；暫存檔保留 | 自動：同上 |
| TC-070 | 作法 7；AZU-AGT-09 | 例外 | 假 `run_fixed` 丟 `FileNotFoundError`（平台主機沒裝 az） | 代理處理 | 結果失敗；訊息含「找不到 az 指令」與 Azure CLI；暫存檔保留；沒有 Traceback | 自動：`test_azure_upload.py::test_missing_az_program_gives_a_plain_message` |
| TC-071 | AZU-AGT-10 | 例外 | 假 `az` 回非 0，stderr 內含假金鑰 | 代理處理 | 結果失敗；暫存檔保留；訊息不含該假金鑰 | 自動：`test_azure_upload.py::test_failed_az_exit_keeps_the_staged_file_and_hides_the_stderr_secrets` |
| TC-072 | 專長守則（錯誤訊息）；裁決 21 | 例外 | 跑 TC-054、TC-062、TC-065、TC-067、TC-070、TC-071 的失敗情境 | 看每則回應 | 每則都用白話說明發生什麼事與下一步；沒有 `Traceback`、沒有 `File "..."`、沒有 SQL、沒有暫存檔或憑證檔的本機路徑 | 自動：`test_azure_upload.py`（註解標 TC-072） |
| TC-073 | 專長守則（回應不含密鑰）；裁決 21 | 功能 | 同 TC-060 的成功情境，憑證檔路徑與一個唯一標記字串 | 看代理回的整個結果 | 搜不到金鑰值、憑證檔路徑、標記字串 | 自動：`test_azure_upload.py`（註解標 TC-073） |
| TC-074 | AZU-AGT-11；azure-launch 裁決 13 | 功能 | 代理收到 Slurm 環境與其他類型環境的 `put_upload` | 代理處理（`run_put`） | 回「這種計算環境不能放雲端資料 (this kind of environment cannot hold cloud data)」，逐字不變；沒有啟動任何程式 | 自動：`test_azure_upload.py::test_run_put_still_refuses_slurm_and_unknown_platforms` |
| TC-075 | 目標（Google 與 AWS 的行為與輸出一個字都不變） | 功能 | 既有的 Google、AWS 代理上傳情境 | 跑既有的 `test_cloud_upload*.py`、`test_aws_upload.py`、`test_byte_channel_*`、`test_station_*` | 全綠，其中 Google／AWS 指令斷言一個字未動 | 自動：既有測試檔 |
| TC-076 | 作法 3（環境重新判斷用 `azure_preflight.clean_environment`） | 例外 | 工作裡的 Azure 環境缺 `storageAccountName`（或 workDir 不是 `az://` 加子資料夾） | 代理處理 | 拒絕，訊息白話；`run_fixed` 0 次 | 自動：`test_azure_upload.py`（註解標 TC-076） |

## User Story 4 — 超過 2 GB 給使用者自己上傳的指令（優先度 P2）

計畫作法 9、AZU-DSET-03、裁決 15、不做（不教登入 Azure）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-077 | 範圍 `actions/datasets.py`（`check_web_upload` 超限訊息）；AZU-DSET-03 | 功能 | 目的地是 Azure 環境；一個大於 2 GB 的暫存檔（用假 `stat` 讓大小大於上限，不真的建大檔） | 走網頁上傳的檢查 | 被拒；訊息含 Azure 版的自己上傳指令 | 自動：`test_azure_upload.py::test_over_limit_file_gets_the_az_command_and_a_plain_warning` |
| TC-078 | 範圍 `jobs.py`（`_uploaded_file` 超限訊息） | 功能 | alice 對 `azure-lab` 呼叫 `enqueue_put_upload`，暫存檔大於 2 GB（假 `stat`） | 呼叫 | 被拒；訊息含 Azure 版的自己上傳指令；工作表列數不變 | 自動：同上 |
| TC-079 | 作法 9；AZU-DSET-03 | 功能 | 同 TC-077 | 看訊息 | 含 `az storage blob upload-batch` | 自動：同上 |
| TC-080 | 作法 9；AZU-DSET-03 | 功能 | 同 TC-077 | 看訊息 | 含「在你自己的電腦上、用你自己的 Azure 登入」，並說明平台不會代你上傳 | 自動：同上 |
| TC-081 | 作法 9；裁決 15 | 功能 | 同 TC-077，alice | 看訊息裡的目的地 | 指向容器 `labcontainer` 與 `uploads/alice/rawdata`（寫成 `--destination-path uploads/alice/rawdata/` 或 `--destination labcontainer/uploads/alice/rawdata` 兩種形狀之一均可，由執行者查證後記帳本）；沒有指到別人的前綴或 `workDir` 子資料夾 | 自動：同上 |
| TC-082 | 作法 9；A4 同類（平台不代傳） | 例外 | 同 TC-078 | 看資料庫與代理 | 沒有排入任何 `put_upload` 工作；沒有啟動任何程式 | 自動：同上 |
| TC-083 | 不做（不教使用者怎麼登入 Azure） | 不在範圍 | 同 TC-077 與 TC-078 的訊息 | 搜尋訊息全文 | 不含 `az login`、`az account`、登入步驟之類的教學，也不含任何金鑰字樣 | 自動：`test_azure_upload.py`（註解標 TC-083） |
| TC-084 | 目標（Google、AWS 不變） | 功能 | Google 與 AWS 環境，各有大於 2 GB 的檔 | 走同樣的檢查 | 訊息與修改前逐字相同（`gcloud storage cp …`、`aws s3 cp …`） | 自動：`test_cloud_upload.py`、`test_aws_upload.py`（既有，斷言一個字不改） |
| TC-085 | 專長守則（回應不含密鑰） | 例外 | 憑證檔與父行程有假金鑰、假 SAS | 看超限訊息 | 訊息不含任何金鑰或 SAS 值 | 自動：`test_azure_upload.py`（註解標 TC-085） |

## User Story 5 — 登記成資料集（優先度 P1）

計畫作法 8：不做 migration，看 `path` 開頭是 `gs://`、`s3://` 或 `az://`；一個資料集必須同一 scheme；`az://` 路徑的容器必須等於目的環境 `workDir` 的容器。裁決 9（路徑是 `actions/datasets.py`，不准新增公開函式與參數名）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-086 | 作法 8；AZU-DSET-01 | 功能 | alice 的 Azure 環境 `azure-lab`；樣本表裡的檔案都是 `az://labcontainer/uploads/alice/…` | `register_dataset(destination=azure-lab)` | 登記成功；資料表寫入的 `path` 以 `az://labcontainer/uploads/alice/` 開頭 | 自動：`test_azure_upload.py::test_dataset_destination_az_registers_az_paths` |
| TC-087 | 作法 8；AZU-DSET-02 | 例外 | 同一份資料集同時有 `az://…` 與 `gs://…` 的檔案 | 登記 | 被拒並說明一份資料集的檔案要全是同一種；資料表沒有新增 | 自動：`test_azure_upload.py::test_mixed_schemes_in_one_dataset_are_refused` |
| TC-088 | 作法 8；AZU-DSET-02 | 例外 | 同一份資料集同時有 `az://…` 與 `s3://…` 的檔案 | 登記 | 同 TC-087 | 自動：同上 |
| TC-089 | 作法 8；AZU-DSET-02 | 例外 | 同一份資料集同時有 `az://…` 與本機路徑的檔案 | 登記 | 同 TC-087 | 自動：同上 |
| TC-090 | 作法 8；AZU-DSET-02 | 例外 | 檔案是 `az://other-container/uploads/alice/a_R1.fastq.gz`，目的環境 workDir 的容器是 `labcontainer` | 登記 | 被拒；說明容器必須是環境 workDir 的容器；資料表沒有新增 | 自動：同上 |
| TC-091 | 不做（不做跨環境搬資料） | 不在範圍 | 目的地 `azure-lab`；檔案是 Google 上傳留下的 `gs://labcontainer/uploads/alice/a_R1.fastq.gz`（或 AWS 的 `s3://…`） | 登記 | 被拒（要的是 `az://`）；沒有任何程式被啟動、沒有任何檔案被搬動；資料表沒有新增 | 自動：`test_azure_upload.py`（註解標 TC-091） |
| TC-092 | 專長守則（跨使用者，寫）；作法 2 | 例外 | 目的地 `azure-lab`（alice 的）；有一個檔案是 `az://labcontainer/uploads/bob/a_R1.fastq.gz` | alice 登記 | 被拒；訊息只提 alice 自己的前綴 `az://labcontainer/uploads/alice/`，不提 bob；資料表沒有新增 | 自動：`test_azure_upload.py`（註解標 TC-092） |
| TC-093 | 作法 2、8 | 例外 | 有一個檔案是 `az://labcontainer/uploads/alice/../bob/a_R1.fastq.gz` | 登記 | 被拒；資料表沒有新增 | 自動：`test_azure_upload.py`（註解標 TC-093） |
| TC-094 | 專長守則（跨使用者，寫） | 例外 | `azure-lab` 是 alice 的環境；bob 登入 | bob 登記時把目的地填 `azure-lab` | 被拒，訊息「找不到計算環境」（與環境不存在相同）；資料表沒有新增 | 自動：`test_azure_upload.py`（註解標 TC-094） |
| TC-095 | 專長守則（跨使用者，讀） | 例外 | alice 已登記含 `az://` 路徑的資料集 `reads` | bob 用自己的身分 `list_datasets`、`get_dataset("reads")` | 列表看不到它；`get_dataset` 回「找不到」，不透露 alice 的路徑 | 自動：`test_azure_upload.py`（註解標 TC-095） |
| TC-096 | 目標（Google、AWS 登記不變） | 功能 | Google 與 AWS 環境各登記含 `gs://`、`s3://` 路徑的資料集 | 登記 | 與修改前相同的結果與訊息（既有斷言不改） | 自動：`test_cloud_upload.py`、`test_aws_upload.py`（既有） |
| TC-097 | 作法 8（不做 migration）；專長守則（結構變動） | 功能 | 比較修改前後的資料集資料表定義與 migration 清單 | 看差異 | 資料表欄位與定義與修改前完全相同；沒有新增 migration；計畫已寫明不需要 migration 的理由 | 自動：`test_azure_upload.py`（註解標 TC-097） |
| TC-098 | 裁決 9；範圍 `datasets.py`（TC-063 釘死公開函式清單） | 功能 | 列出 `actions/datasets.py` 的公開函式與各函式的參數名 | 與修改前比對 | 完全相同：沒有新增公開函式、沒有新增參數名 | 自動：既有 `test_cloud_upload.py`（TC-063 那條，斷言不改）；`test_azure_upload.py`（註解標 TC-098） |
| TC-099 | 專長守則（不得含密鑰）；既有規則不退步 | 例外 | 目的地 `azure-lab`；檔案路徑含像憑證的值（假的長金鑰字串） | 登記 | 被拒，說路徑含像憑證的值；資料表沒有新增 | 自動：`test_azure_upload.py`（註解標 TC-099） |

## User Story 6 — 禁字與靜態檢查、不在範圍、文件（優先度 P2）

計畫作法 7、10、11、AZU-STATIC-01～03、AZU-DOC-01～03、裁決 8、9、13、16、20、「不做」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-100 | AZU-STATIC-01；作法 10 | 功能 | 掃 `abf_platform/` 全部原始碼 | 看匯入與字樣 | 沒有 `boto3`／`botocore`／`google`／`azure` 的匯入；沒有 `subprocess`、`threading` | 自動：`test_azure_upload.py::test_no_cloud_library_and_no_station_word_in_platform_sources`；`test_aws_upload.py`（既有，705 行字表依裁決 13 換成 `"import azure"`、`"from azure"`，693、713 行匯入禁令一字不動） |
| TC-101 | AZU-STATIC-01；作法 10（TC-061 / TC-089 既有禁字） | 功能 | 同上 | 看字樣 | 平台原始碼（含 `cloud_store.py`、`actions/datasets.py`）沒有 "station" 字樣 | 自動：同上 |
| TC-102 | 範圍 `cloud_store.py`／`datasets.py` 禁字；裁決 13、20 | 功能 | 掃 `cloud_store.py` 與 `actions/datasets.py` 原文 | 看字樣 | 沒有 `open(`、`hashlib`、`subprocess`、`os.system`、`socket`、`urllib`、`httpx`、`requests`、`import google`、`boto3`；`cloud_store.py` 原文沒有小寫 `azure`（可用 `Azure`、`AZURE`、`compute_envs.AZURE`，不准拆字湊字） | 自動：`test_cloud_upload.py`（TC-088 既有，不改）；`test_azure_upload.py`（註解標 TC-102） |
| TC-103 | AZU-STATIC-02；作法 10 | 功能 | 掃 `abf_station/put_upload.py` | 看匯入與字樣 | 沒有 `google`／`boto`／`azure`／`requests`／`httpx`／`socket`／`subprocess` 的匯入；沒有 `shell=True`、`Popen`、`os.system`；只經 `site.run_fixed`／`site.start_fed` 啟動程式 | 自動：`test_azure_upload.py::test_put_upload_source_has_no_delete_no_cost_no_shell_words`；`test_byte_channel_b.py`（TC-903 行那條，既有不改） |
| TC-104 | 不做（Blob 刪除、azcopy）；AZU-STATIC-02 | 不在範圍 | 掃 `put_upload.py` | 看字樣 | 沒有 `storage blob delete`、`azcopy`、`delete-object`、`s3 rm`、`s3 sync`、`--acl`、`presign` | 自動：同上 |
| TC-105 | 不做（費用估算）；AZU-STATIC-02 | 不在範圍 | 掃 `put_upload.py`、`cloud_store.py`，並看 `enqueue_put_upload` 的原始碼 | 看字樣 | 都沒有 `cloud_cost` | 自動：同上 |
| TC-106 | 不做（不用 `--account-key`／`--sas-token`／`--connection-string`、SAS URL、瀏覽器直傳、Azure SDK） | 不在範圍 | 掃 `put_upload.py` | 看字樣 | 沒有這三個旗標字樣，沒有 SAS URL 產生，沒有 SDK 匯入 | 自動：同上 |
| TC-107 | 作法 7；裁決 16 | 功能 | 掃 `abf_station/` 全部原始碼 | 逐行比對小寫 `\bazure\b` | 沒有符合（訊息中的 Azure 字樣依 `azure_preflight` 的 `"Az" "ure"` 寫法） | 自動：`test_station_static.py`（既有，不改）；`test_azure_upload.py`（註解標 TC-107） |
| TC-108 | 作法 11；裁決 9 | 功能 | 掃 `abf_platform` 與 `abf_station` 全部原始碼 | 用縮窄後的 `test_no_launch_cost_or_upload_code_for_azure`（改名為「Azure 沒有刪除、沒有 azcopy、沒有建池」之類）的規則 | 沒有 `storage blob delete`、`azcopy`、`batch pool create/delete/resize`、`storage container create`、`az batch job/task`；規則只拿掉 `storage blob upload` 與 `upload-batch`，其餘保留（verifier 閱卷時對 base 比對正則） | 自動：`test_azure_ce.py` 該測試 |
| TC-109 | 維護者原話（ADR 0010）；不做（不新增 MCP 上傳工具） | 不在範圍 | 載入 MCP 工具清單 | 看工具名單 | 沒有任何名稱含 `upload` 的工具 | 自動：`test_azure_upload.py::test_no_mcp_upload_tool_exists` |
| TC-110 | 專長守則（對等性）；不做（不改網頁） | 功能 | 同時列出「使用者可見的動作」（MCP 工具名單、網頁路由、指令列子命令）與「動作層函式」 | 與修改前的清單比對 | 兩邊都與修改前完全相同（本任務沒有新增任何使用者可見動作；`web.py`、`web_board.py`、`static/*` 沒被改） | 自動：`test_azure_upload.py`（註解標 TC-110） |
| TC-111 | 不做（不用 Azure SDK） | 不在範圍 | 看 `pyproject.toml`、`constraints.txt` | 比對修改前 | 沒有新增任何 Azure 或雲端函式庫相依 | 自動：`test_azure_upload.py`（註解標 TC-111） |
| TC-112 | 作法（新檔 `test_azure_upload.py`，TC-070 的 `# Nothing existing:`） | 功能 | 開 `platform/tests/test_azure_upload.py` | 看前 40 行 | 有 `# Nothing existing: …` 一行，說明至少 15 個字；測試函式以計畫的 AZU-* 名稱或註解 `# TC-nnn` 標示對應 | 自動：`tests/scripts_name_their_alternative.sh`／`test_azure_upload.py` 自檢 |
| TC-113 | AZU-DOC-01；必須更新的既有斷言 A.4 | 功能 | 讀 `docs/PLATFORM.md` 的型別表 | 找 Azure 那一列 | 寫「checked and launched on the platform host (clean, resume: not yet)」 | 自動：`test_azure_ce.py::test_docs_list_every_azure_key_and_check`、`test_azure_launch.py` 的 `AZL-DOC-01`（依計畫換成新句） |
| TC-114 | AZU-DOC-02 | 功能 | 讀 `docs/SEQERA_PARITY.md` | 找 Azure 那一列 | 寫「Have (create + check + launch + cancel + upload); clean in azure-clean」 | 自動：同上，`AZL-DOC-02` |
| TC-115 | AZU-DOC-03；完成標準 | 功能 | 讀 `docs/TESTING.md` | 找 Azure 上傳的小節 | 有「Uploading to Azure Batch (azure-upload): the maintainer checks by hand」一節，含 `az storage blob show` 驗大小的步驟與「會花一點錢、先設好成本警示」的警語 | 自動：同上，`AZL-DOC-03` |
| TC-116 | 裁決 6；AZU-DOC | 功能 | 讀 `docs/PLATFORM.md` 的 Azure 上傳段 | 找文字 | 寫明「網頁入口尚未接上」 | 自動：`test_azure_upload.py`（註解標 TC-116） |
| TC-117 | 裁決 2、7；AZU-DOC | 功能 | 同上 | 找文字 | 寫明「版本控制或軟刪除開著時，覆寫同名檔會留下舊版本、仍收費」 | 自動：`test_azure_upload.py`（註解標 TC-117） |
| TC-118 | 範圍 A.7（azure-launch 裁決 12 的整句不再改） | 功能 | 讀 `docs/PLATFORM.md` 型別表那一句 | 找文字 | 仍是 "Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; the other ten types can be modelled only" | 自動：`test_aws_ce.py`、`test_gcb_ce.py`、`test_gcb_launch.py`（既有，斷言不改） |
| TC-119 | 完成標準（真實 Azure 上傳是 C 級「需要人」步驟） | 功能 | 讀 `docs/TESTING.md` 的 Azure 上傳小節 | 照著做的人能否看懂 | 步驟具體到維護者能照做：用哪個環境、傳多大的檔、預期在 `blob show` 看到什麼大小；明寫真的上傳會寫真實 Blob 容器、花錢、需維護者另外點頭並先設好 Azure 成本警示（Cost Management budget alert），且不屬完成標準 | 手動：`docs/TESTING.md` |

## 憲法與安全網

本任務動到憲法第 2 條（不新增送出路徑；只有一個程式能啟動外部程式）、第 3 條（不寫死位置）、安全網的「憑證只留在設定檔」與「平台不存放收到的憑證」，以及維護者原話（憑證 → 計算環境 → 資料集，掛在已建好的環境名字上，不另要使用者輸入金鑰）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-120 | 憲法第 2 條 | 功能 | 本任務完成後的整個程式庫 | 跑 `tests/no_second_run_state_test.sh` | 通過；上傳沒有新增任何「送出 run」的路徑，也沒有第二份 run 狀態 | 自動：`tests/no_second_run_state_test.sh` |
| TC-121 | 憲法第 2 條（站台代理對外的唯一出口是 `site.run_fixed`／`site.start_fed`，不得新增另一條 subprocess 路徑） | 功能 | 掃 `abf_station/` | 跑 `test_station_static.py` 的「只有一個模組啟動程式且不用 shell」檢查 | 通過；`put_upload.py` 沒有自己的 subprocess | 自動：`test_station_static.py`（既有，不改） |
| TC-122 | 憲法第 3 條 | 功能 | 本任務完成後的整個程式庫 | 跑 `tests/no_hardcoded_paths.sh`，並掃新程式碼 | 通過；新程式碼沒有寫死的容器名、帳號名、`/home`、`/scratch` 等位置，位置都來自環境設定 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-123 | 安全網（憑證只留在設定檔）；計畫「前提」測試輸入規則 | 功能 | 含 `test_azure_upload.py` 的整個程式庫 | 跑 `tests/credentials_stay_in_settings_test.sh` | 通過；測試裡的假金鑰與憑證鍵名都是字串相加組出來，沒有被掃到 | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-124 | 安全網（平台不存放收到的憑證）；維護者原話（PLAN 第 40 行） | 例外 | 憑證檔與父行程有假的金鑰、假的 SAS；排入一筆 Azure `put_upload` 工作 | 檢查工作內容、資料庫中的那一列、代理回報的結果 | 工作只帶環境資訊與 `owner`、`name`、`size`、`dest`；沒有憑證檔路徑、沒有任何金鑰或 SAS 值；使用者不需要輸入金鑰 | 自動：`test_azure_upload.py`（註解標 TC-124）；`test_secrets.py`（既有，不改） |
