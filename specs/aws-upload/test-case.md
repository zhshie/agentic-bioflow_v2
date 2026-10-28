# 測試案例：把輸入檔上傳到 AWS Batch 環境的 S3（aws-upload，put_upload）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：本任務沒有 spec.md，以 `specs/aws-upload/plan.md`（含「維護者原話」、文末「裁決」與 A1–A7；與上文衝突時以文末為準）為規格。
IDs: TC-001..TC-133。每條只測一件事；驗證方式「自動」＝ `platform/tests/test_aws_upload.py`（或計畫指定要更新的既有測試檔），並在測試內以註解 `# TC-nnn` 標明。
所有測試輸入都用假值：`lab-bucket`、`eu-west-1`、`aws-lab`、`alice`、`bob`；全部用假的 `site.run_fixed`／`site.start_fed`，`tmp_path` 當儲存根目錄與暫存目錄；不碰網路、不呼叫真的 aws、不花錢。
憑證相關的鍵名在測試裡用字串相加組出來，避免被 `tests/credentials_stay_in_settings_test.sh` 掃到。
編號說明：計畫文內提到的 TC-043、TC-061、TC-082～085、TC-090、TC-114 在本檔裡指的內容見各列（TC-043＝環境變數剝除、TC-061＝大小沒核對相符不刪暫存檔、TC-082～085＝超過 2 GB 的指令、TC-090＝平台端禁字掃描、TC-114＝代理端禁字）。計畫作法 8 內另一組 TC-061／070／083／085 是專案既有 Google 測試的編號，與本檔無關。
-->

**規格**：`specs/aws-upload/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「尚未支援」而不是悄悄亂做。

名詞：**站台代理**＝裝在平台主機上、唯一會真的執行 `aws` 指令的程式（平台本身不碰 AWS）；**暫存檔**＝使用者傳到平台主機上傳資料夾（`<ABF_STATION_UPLOADS>/<擁有者>/`）的那份檔案，傳到 S3 並核對大小相符之後才會被刪；**放行表**＝`compute_envs.CLOUD_JOB_KINDS`，每一種雲端環境各自列出它肯接的工作種類；**位置**＝`s3://bucket/名稱` 或 `gs://bucket/名稱` 這種寫法；**前綴**＝某個人專屬的那一段，例如 `s3://lab-bucket/uploads/alice/`；**位元組**＝檔案大小單位，本檔的 2 GB 是十進位 2,000,000,000 位元組；**假的 start_fed／run_fixed**＝測試裡取代真正啟動程式的替身，會記下收到的指令與環境變數。

## User Story 1 — 只有 AWS 的「上傳」被打開，其他仍關著（優先度 P1）

計畫目標與作法 1；裁決 A3（維護者採納）：「AWS 的 clean 與 upload 在各自的任務完成前維持關閉。→ 本任務完成後 `put_upload` 對 AWS 才打開，`clean_work` 仍關」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；作法 1；失敗先行測試 1 | 功能 | AWS 環境 `aws-lab`（region `eu-west-1`、workDir `s3://lab-bucket/work`）狀態 `available`，代理在線；alice 的上傳資料夾裡有 5 位元組的 `reads.fastq.gz` | alice 對 `aws-lab` 呼叫 `enqueue_put_upload` | 排入恰好 1 筆 `put_upload` 工作 | 自動：`test_aws_upload.py::test_aws_env_may_queue_put_upload_when_available` |
| TC-002 | 目標；作法 2 | 功能 | 同 TC-001 | 看排入的工作內容 | 欄位恰為 `ce`、`owner`、`name`、`size`、`dest` 五個；`owner`＝alice、`name`＝`reads.fastq.gz`、`size`＝5、`dest`＝`s3://lab-bucket/uploads/alice/reads.fastq.gz` | 自動：`test_aws_upload.py`（註解標 TC-002） |
| TC-003 | 作法 1；失敗先行測試 1 | 例外 | `aws-lab` 狀態是 `creating`（不是 `available`），其餘同 TC-001 | alice 呼叫 `enqueue_put_upload` | 被拒；訊息白話說明只有可用（available）的環境才能存檔，並提示先做預檢；工作表列數不變 | 自動：`test_aws_upload.py::test_aws_env_may_queue_put_upload_when_available` |
| TC-004 | 作法 1；失敗先行測試 2；A3(a) | 功能 | 載入 `compute_envs` | 看 AWS 那一格的放行種類 | 恰為 `preflight`、`launch_nextflow`、`cancel_run`、`pipeline_files`、`put_upload` 五個；不含 `clean_work` | 自動：`test_aws_upload.py::test_put_upload_gate_is_a_per_type_table_not_a_shared_tuple` |
| TC-005 | 失敗先行測試 2；目標（Google 一個字都不變） | 功能 | 同上 | 看 Google 那一格的放行種類 | 恰為 `preflight`、`launch_nextflow`、`cancel_run`、`clean_work`、`put_upload`、`pipeline_files` 六個，與修改前完全相同 | 自動：同上 |
| TC-006 | 作法 1（逐型別放行，不新增共用元組） | 功能 | 一個 `available` 的 AWS 環境和一個 `available` 的 Google 環境；測試內暫時把 AWS 那一格的 `put_upload` 拿掉，再放回 | 各排一次 `put_upload` | 拿掉時 AWS 被拒、放回時 AWS 通過；Google 兩次都通過。證明放行是查那張表，不是寫死「只給 Google」 | 自動：同上 |
| TC-007 | 作法 1；目標 | 例外 | 一個 `available` 的 Slurm 環境 | 對它排 `put_upload` | 被拒，用白話說這種環境不能放雲端資料；工作表列數不變 | 自動：`test_aws_upload.py`（註解標 TC-007） |
| TC-008 | 作法 1；失敗先行測試 3；裁決 A3 | 例外 | `available` 的 AWS 環境 | 對它排 `clean_work` | 被拒；訊息含「尚未支援」與 `aws-clean`；工作表列數不變 | 自動：`test_aws_upload.py::test_clean_work_still_refused_for_aws` |
| TC-009 | A7 | 例外 | 同 TC-008 | 看那則拒絕訊息 | 只提到 `aws-clean`，不再提到 `aws-upload` | 自動：同上 |
| TC-010 | 失敗先行測試 3；裁決 A3 | 例外 | 代理收到 AWS 環境的 `clean_work` 工作（假的執行器記錄所有被啟動的程式） | 代理處理 | 拒絕，訊息含「尚未支援」；沒有啟動任何程式（沒有 aws、沒有 S3 指令） | 自動：`test_aws_upload.py`（註解標 TC-010；承接 `test_aws_launch.py` 被拆開後保留的 clean_work 那一半） |
| TC-011 | 不做（不開放 `list_site_files`） | 不在範圍 | `available` 的 AWS 環境 | 對它排 `list_site_files`、`fetch_run_records`、`read_task_log` | 三種都被拒，訊息含「尚未支援」與「AWS Batch」，不含「Google Batch」；工作表列數不變 | 自動：`test_aws_launch.py::test_aws_environment_accepts_exactly_preflight_launch_cancel_and_pipeline_files`（A3(a) 更新後的版本） |
| TC-012 | 目標（Google 版行為與輸出不變） | 功能 | `available` 的 Google Batch 環境 `gcb-lab`（workDir `gs://lab-bucket/work`），alice 有上傳檔 | alice 對它呼叫 `enqueue_put_upload` | 排入 1 筆工作，欄位同 TC-002，`dest`＝`gs://lab-bucket/uploads/alice/<檔名>` | 自動：`test_cloud_upload.py`（既有，斷言一個字不改） |
| TC-013 | 專長守則（跨使用者，寫） | 例外 | `aws-lab` 屬於 alice；bob 另有帳號與權杖 | bob 用自己的身分對 `aws-lab` 呼叫 `enqueue_put_upload` | 回答與「環境不存在」一樣（找不到這個計算環境）；工作表列數不變 | 自動：`test_aws_upload.py`（註解標 TC-013） |
| TC-014 | 專長守則（跨使用者，寫） | 例外 | bob 的權杖，`aws-lab` 是 bob 自己的環境 | bob 呼叫時把擁有者名字填成 `alice`（想用 alice 的前綴） | 被拒（回答與找不到相同）；工作表列數不變 | 自動：`test_aws_upload.py`（註解標 TC-014） |
| TC-015 | 作法 1；Google 逐項對應 | 例外 | 同 TC-001，但 alice 的上傳資料夾裡沒有那個檔案 | alice 呼叫 `enqueue_put_upload` | 被拒，白話請她先把檔案傳到自己的資料夾；沒有排入 | 自動：`test_aws_upload.py`（註解標 TC-015） |
| TC-016 | 作法 1；Google 逐項對應 | 例外 | 上傳資料夾裡該名字是資料夾，或是符號連結 | alice 呼叫 `enqueue_put_upload` | 被拒，說明這不是一般檔案；沒有排入 | 自動：`test_aws_upload.py`（註解標 TC-016） |
| TC-017 | 作法 1；Google 逐項對應 | 例外 | 上傳資料夾裡有 0 位元組的空檔 | alice 呼叫 `enqueue_put_upload` | 被拒，說明是空檔案沒有東西可存；沒有排入 | 自動：`test_aws_upload.py`（註解標 TC-017） |

## User Story 2 — S3 位置的表示法與歸屬判斷（優先度 P1）

作法 2：位置是 `s3://<bucket>/uploads/<owner>/<name>`，bucket 取自環境的 workDir；`inside_prefix` 必須擋 `..`、空段、前綴撞名；A2：`workdir_scheme(ce)` 吃環境 dict，回 `"gs"` 或 `"s3"`，其他平台丟 `CloudPathError`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 作法 2；失敗先行測試 4 | 功能 | AWS 環境 dict，workDir `s3://lab-bucket/work` | 呼叫 `workdir_bucket` | 回 `lab-bucket` | 自動：`test_aws_upload.py::test_workdir_bucket_for_aws_is_the_s3_bucket` |
| TC-019 | A2；失敗先行測試 4 | 功能 | 一個 AWS 環境 dict 和一個 Google 環境 dict | 各呼叫 `workdir_scheme` | AWS 回 `"s3"`，Google 回 `"gs"` | 自動：同上 |
| TC-020 | A2 | 例外 | Slurm 環境 dict | 呼叫 `workdir_scheme` | 丟 `CloudPathError`（一句白話） | 自動：`test_aws_upload.py`（註解標 TC-020） |
| TC-021 | A2 | 例外 | AWS 環境 dict 但 workDir 不是 `s3://` 開頭（例如缺少或寫成 `gs://x/y`） | 呼叫 `workdir_bucket` | 丟 `CloudPathError`，一句白話，不是堆疊 | 自動：`test_aws_upload.py`（註解標 TC-021） |
| TC-022 | 失敗先行測試 5；目標（Google 不變） | 功能 | Google 環境 dict，workDir `gs://lab-bucket/work`；另一個 Google 環境的 workDir 不是 `gs://` | 各呼叫 `workdir_bucket` | 前者回 `lab-bucket`；後者丟的錯誤訊息逐字等於修改前（「這個計算環境沒有 gs:// 的 workDir，不能放雲端資料 (this environment has no gs:// workDir)」） | 自動：`test_aws_upload.py::test_workdir_bucket_for_google_is_unchanged` |
| TC-023 | A2；A3(e) | 例外 | Slurm 環境 dict | 呼叫 `workdir_bucket` | 丟 `CloudPathError`，訊息同時提到 Google Batch 與 AWB Batch 兩種（寫作「AWS Batch」），不再只說 Google | 自動：`test_cloud_upload.py::test_workdir_bucket_needs_a_google_batch_environment`（A3(e) 更新後：名字與斷言改成「需要 Google 或 AWS 的雲端環境，Slurm 與其他仍被拒」） |
| TC-024 | 作法 2（新增 `parse_s3`，形狀同 `parse_gs`） | 功能 | 無 | `parse_s3("s3://lab-bucket/uploads/alice/a.fq.gz")` | 回 `("lab-bucket", "uploads/alice/a.fq.gz")` | 自動：`test_aws_upload.py`（註解標 TC-024） |
| TC-025 | 作法 2 | 例外 | 無 | `parse_s3` 收到 `gs://lab-bucket/x`、`https://lab-bucket/x`、`lab-bucket/x` | 三個都丟 `CloudPathError`，只收 `s3://` 開頭 | 自動：`test_aws_upload.py`（註解標 TC-025） |
| TC-026 | 作法 2 | 例外 | 無 | `parse_s3("s3://lab-bucket/uploads/../bob/x")` | 丟 `CloudPathError`，說位置不能含 `..` | 自動：`test_aws_upload.py`（註解標 TC-026） |
| TC-027 | 作法 2 | 例外 | 無 | `parse_s3` 收到含控制字元（換行、NUL）的位置 | 丟 `CloudPathError` | 自動：`test_aws_upload.py`（註解標 TC-027） |
| TC-028 | 作法 2 | 例外 | 無 | `parse_s3("s3://lab-bucket")`、`parse_s3("s3://lab-bucket/")`（bucket 後面沒有名稱） | 兩個都丟 `CloudPathError`，說位置後面要有名稱 | 自動：`test_aws_upload.py`（註解標 TC-028） |
| TC-029 | 目標（Google 一個字都不變） | 例外 | 無 | `parse_gs("s3://lab-bucket/x")` | 仍丟 `CloudPathError`「只收 gs:// 開頭的位置」，訊息與修改前相同 | 自動：`test_cloud_upload.py`（既有斷言不改） |
| TC-030 | 作法 2 | 功能 | AWS 環境 dict | `upload_prefix(ce, "alice", scheme="s3")`；`upload_prefix(ce, None, scheme="s3")` | 前者回 `s3://lab-bucket/uploads/alice/`，後者回 `s3://lab-bucket/uploads/` | 自動：`test_aws_upload.py::test_s3_object_url_is_inside_the_owners_prefix` |
| TC-031 | 作法 2；失敗先行測試 6 | 功能 | 同上 | `object_url(ce, "alice", "a.fq.gz", scheme="s3")` | 回 `s3://lab-bucket/uploads/alice/a.fq.gz`，且 `inside_prefix` 對 alice 的前綴為真 | 自動：同上 |
| TC-032 | 作法 2 | 例外 | 同上 | `object_url` 的檔名給 `a/b`、`..`、空字串 | 都丟 `CloudPathError`（檔名必須是單層名稱） | 自動：`test_aws_upload.py`（註解標 TC-032） |
| TC-033 | 作法 2；失敗先行測試 5 | 功能 | Google 環境 dict | 不帶 `scheme` 呼叫 `upload_prefix(ce, "alice")` 與 `object_url(ce, "alice", "a.fq.gz")` | 回 `gs://lab-bucket/uploads/alice/` 與 `gs://lab-bucket/uploads/alice/a.fq.gz`，與修改前逐字相同 | 自動：`test_aws_upload.py::test_workdir_bucket_for_google_is_unchanged` |
| TC-034 | 作法 2 | 功能 | 前綴 `s3://lab-bucket/uploads/alice/` | `inside_prefix("s3://lab-bucket/uploads/alice/a.fq.gz", 前綴, scheme="s3")` | 回真 | 自動：`test_aws_upload.py::test_s3_object_url_is_inside_the_owners_prefix` |
| TC-035 | 作法 2；失敗先行測試 6 | 例外 | 同上 | `inside_prefix` 收到 `s3://lab-bucket/uploads/alice2/x`（前綴撞名） | 回假 | 自動：同上 |
| TC-036 | 作法 2；失敗先行測試 6 | 例外 | 同上 | `inside_prefix` 收到 `s3://lab-bucket/uploads/alice/../bob/x` | 回假 | 自動：同上 |
| TC-037 | 作法 2；失敗先行測試 6 | 例外 | 同上 | `inside_prefix` 收到 `s3://lab-bucket/uploads//x`（空段） | 回假 | 自動：同上 |
| TC-038 | 作法 2 | 例外 | 同上 | `inside_prefix` 收到 `s3://other-bucket/uploads/alice/x`（別的 bucket） | 回假 | 自動：`test_aws_upload.py`（註解標 TC-038） |

## User Story 3 — 站台代理重新判斷一切，串流寫進 S3，核對大小才刪暫存檔（優先度 P1）

作法 3、4、5；A4、A5、A6。代理不信平台：位置、大小、暫存檔都自己再驗一次。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 | 作法 3、4、5 | 功能 | 代理收到合法的 AWS `put_upload` 工作（`dest`＝`s3://lab-bucket/uploads/alice/reads.fastq.gz`、size 5）；暫存檔在 `<上傳資料夾>/alice/reads.fastq.gz`；假憑證檔存在；假 `start_fed` 成功；假 `head-object` 回 5 | 代理處理 | 結果 `ok` 為真，`bytes`＝5，`path`＝`dest`；訊息寫明已上傳與暫存檔已刪 | 自動：`test_aws_upload.py::test_size_is_checked_with_head_object_before_the_staged_file_goes` |
| TC-040 | 作法 4；失敗先行測試 7 | 功能 | 同 TC-039，region `eu-west-1` | 看假 `start_fed` 收到的指令 | 恰為 `["aws","s3","cp","-",dest,"--region","eu-west-1"]`，是清單而不是一串 shell 文字 | 自動：`test_aws_upload.py::test_agent_streams_into_aws_s3_cp_with_fixed_argv` |
| TC-041 | 作法 4；失敗先行測試 7 | 功能 | 同 TC-039 | 看同一個指令與其他所有被記錄的指令 | 沒有 `--expected-size`（2 GB 以下不需要） | 自動：同上 |
| TC-042 | 作法 4；失敗先行測試 8；A6 | 功能 | 同 TC-039；代理的憑證檔路徑設成 `tmp_path` 下的假檔 | 看傳給 `start_fed` 的環境變數 | `AWS_SHARED_CREDENTIALS_FILE` 指到那個假檔、`AWS_PROFILE`＝`default`、`AWS_CONFIG_FILE`＝`os.devnull`、`AWS_DEFAULT_REGION`＝`eu-west-1` | 自動：`test_aws_upload.py::test_agent_env_has_only_the_credentials_file_and_profile` |
| TC-043 | 作法 4；失敗先行測試 8；A6 | 例外 | 同 TC-039；測試先在父行程塞假的金鑰類 `AWS_*` 值（存取金鑰、秘密金鑰、連線階段權杖，鍵名用字串相加組出）、另一個 `AWS_PROFILE`、以及 `ABF_X=假值` | 看傳給 `start_fed` 的環境變數 | 金鑰類 `AWS_*` 與所有 `ABF_*` 都不出現；`AWS_PROFILE` 仍是 `default`。（沿用 `aws_preflight._aws_env`，允許它的 `AWS_PAGER`、`AWS_EC2_METADATA_DISABLED`、`AWS_CA_BUNDLE`） | 自動：同 TC-042 |
| TC-044 | 作法 4、5；A6 | 功能 | 同 TC-043 | 看傳給 `head-object` 那次 `run_fixed` 的環境變數 | 與 TC-042、TC-043 的規則相同：憑證檔與 profile 正確、金鑰類 `AWS_*` 與 `ABF_*` 不出現 | 自動：`test_aws_upload.py`（註解標 TC-044） |
| TC-045 | 作法 4 | 功能 | 同 TC-039，暫存檔內容是已知的 5 位元組；假 `start_fed` 記下收到的資料 | 代理處理 | 餵進去的資料逐位元組等於暫存檔內容；餵完後關閉輸入並等待結束 | 自動：`test_aws_upload.py`（註解標 TC-045） |
| TC-046 | 作法 4；Google 逐項對應 | 例外 | 假的 aws 程式結束碼不是 0 | 代理處理 | 結果 `ok` 為假，白話說 aws 沒有成功並提示 bucket 上可能要檢查；暫存檔仍在 | 自動：`test_aws_upload.py`（註解標 TC-046） |
| TC-047 | 作法 4；Google 逐項對應 | 例外 | 假的 aws 程式等待逾時 | 代理處理 | 結果 `ok` 為假，說逾時；程式被終止；暫存檔仍在 | 自動：`test_aws_upload.py`（註解標 TC-047） |
| TC-048 | 作法 4；專長守則（回應不含密鑰） | 例外 | 假的 aws 輸出含像金鑰的字串（假值）與本機路徑 | 代理處理（結束碼非 0） | 結果訊息不含那串金鑰值，也不含本機路徑；訊息長度被截短 | 自動：`test_aws_upload.py`（註解標 TC-048） |
| TC-049 | 作法 3；失敗先行測試 9 | 例外 | 工作的 `dest` 是 `s3://lab-bucket/runs/x`（同一個 bucket，但不是 uploads） | 代理處理 | 拒絕；假 `start_fed` 一次都沒被呼叫 | 自動：`test_aws_upload.py::test_agent_rejudges_dest_and_refuses_a_foreign_prefix` |
| TC-050 | 作法 3；失敗先行測試 9 | 例外 | `dest` 是 `s3://other-bucket/uploads/alice/reads.fastq.gz`（別的 bucket） | 代理處理 | 拒絕；`start_fed` 0 次 | 自動：同上 |
| TC-051 | 作法 3；失敗先行測試 9 | 例外 | 工作擁有者是 alice，`dest` 是 `s3://lab-bucket/uploads/bob/reads.fastq.gz` | 代理處理 | 拒絕；`start_fed` 0 次 | 自動：同上 |
| TC-052 | 作法 3 | 例外 | `dest` 在 alice 自己的前綴裡，但檔名與工作的 `name` 不同（不等於重算出的 `object_url`） | 代理處理 | 拒絕；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-052） |
| TC-053 | 作法 3、6（同一 scheme） | 例外 | AWS 環境的工作，`dest` 是 `gs://lab-bucket/uploads/alice/reads.fastq.gz` | 代理處理 | 拒絕；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-053） |
| TC-054 | 作法 3 | 例外 | `dest` 是 `s3://lab-bucket/uploads/alice/../bob/x` | 代理處理 | 拒絕；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-054） |
| TC-055 | 作法 3 | 例外 | 工作的 `size` 是 0 | 代理處理 | 拒絕，說大小要在 1 位元組到 2 GB 之間；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-055） |
| TC-056 | 作法 3 | 例外 | 工作的 `size` 是 2,000,000,001 | 代理處理 | 拒絕，說大小要在 1 位元組到 2 GB 之間；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-056） |
| TC-057 | 作法 3 | 例外 | 工作的 `size` 是 `true` 或文字 `"5"` | 代理處理 | 拒絕；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-057） |
| TC-058 | 作法 3 | 例外 | 工作缺 `dest` 欄，或多帶一個不認得的欄位 | 代理處理 | 拒絕，說工作缺少需要的欄位；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-058） |
| TC-059 | 作法 3（不信平台） | 例外 | 工作裡環境快照的 `region` 不是 AWS 區域寫法，或 `workDir` 不是 `s3://` 或 bucket 名稱不合規則 | 代理處理 | 拒絕並說哪一項不合規則；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-059） |
| TC-060 | 作法 3；失敗先行測試 12 | 例外 | 暫存檔是符號連結（指向別處的檔案） | 代理處理 | 拒絕，說這是捷徑不是一般檔案；`start_fed` 0 次；連結指向的檔案沒被動 | 自動：`test_aws_upload.py::test_symlinked_or_resized_staged_file_is_refused` |
| TC-061 | 作法 5；失敗先行測試 10；A4（底線：大小沒核對相符就不刪暫存檔） | 例外 | 同 TC-039，但假 `head-object` 回傳的大小與暫存檔不同（例如 4） | 代理處理 | 結果 `ok` 為假，白話說雲端物件大小與本機不符、請重新上傳；暫存檔仍在 | 自動：`test_aws_upload.py::test_size_is_checked_with_head_object_before_the_staged_file_goes` |
| TC-062 | 作法 5；失敗先行測試 10 | 功能 | 同 TC-039，假 `head-object` 回 5 | 代理處理 | 結果 `ok` 為真；暫存檔已被刪除 | 自動：同上 |
| TC-063 | A4 | 例外 | 同 TC-039，但假 `head-object` 失敗（結束碼非 0、輸出不是純數字、或逾時） | 代理處理 | 與 Google 版相同：結果 `ok` 為真，訊息明說「已上傳，但沒能核對雲端大小；暫存檔保留」；暫存檔仍在 | 自動：`test_aws_upload.py`（註解標 TC-063） |
| TC-064 | 作法 5 | 功能 | 同 TC-039 | 看 `head-object` 那次 `run_fixed` 的指令 | 以 `["aws","s3api","head-object"` 開頭，帶 `--bucket lab-bucket`、`--key uploads/alice/reads.fastq.gz`、`--query ContentLength`、`--output text`；是清單、不是 shell 文字。（若讀官方文件後形狀要調整，執行者須在帳本記一行並回報重開本條） | 自動：`test_aws_upload.py`（註解標 TC-064） |
| TC-065 | 作法 5（`_remove` 照舊檢查 dev/ino） | 例外 | 同 TC-039，但在傳完到刪除之間，暫存檔被換成另一個檔案（不同 inode）或被換成連結 | 代理處理 | 暫存檔沒被刪；訊息白話說暫存檔沒刪掉、請管理者清理；結果仍標示已上傳 | 自動：`test_aws_upload.py`（註解標 TC-065） |
| TC-066 | 作法 5 | 功能 | alice 的上傳資料夾有 `reads.fastq.gz` 與 `other.fastq.gz`，傳前者成功 | 代理處理 | 只有 `reads.fastq.gz` 被刪，`other.fastq.gz` 還在 | 自動：`test_aws_upload.py`（註解標 TC-066） |
| TC-067 | 失敗先行測試 11 | 例外 | 憑證檔不存在 | 代理處理 | 失敗；訊息白話說找不到憑證檔、請管理者檢查（可含檔案路徑，這是補充 8–13 的唯一例外）；`start_fed` 0 次、`head-object` 0 次；暫存檔仍在 | 自動：`test_aws_upload.py::test_missing_credentials_file_fails_without_leaking_its_content` |
| TC-068 | 失敗先行測試 11；專長守則 | 例外 | 父行程與憑證檔裡有假的金鑰值；在 TC-046、TC-047、TC-067 的情境下 | 看所有失敗結果的訊息 | 沒有任何金鑰值（不論來自環境變數或憑證檔內容） | 自動：同上 |
| TC-069 | A5 | 例外 | 假的 `start_fed` 丟 `FileNotFoundError`（平台主機沒裝 aws） | 代理處理 | 結果 `ok` 為假，訊息逐字含「平台主機上找不到 aws 指令，請管理者安裝 AWS CLI」；不露出堆疊；暫存檔仍在 | 自動：`test_aws_upload.py`（註解標 TC-069；計畫 A5 要求的新測試） |
| TC-070 | A5 | 例外 | 假的 `start_fed` 丟 `PermissionError`（aws 在但無法啟動） | 代理處理 | 結果 `ok` 為假，白話說沒能啟動 aws、請管理者檢查；不露出堆疊；暫存檔仍在 | 自動：`test_aws_upload.py`（註解標 TC-070） |
| TC-071 | 作法 3；失敗先行測試 12 | 例外 | 暫存檔實際大小與工作的 `size` 不同（例如工作寫 5、檔案 7 位元組） | 代理處理 | 拒絕，說檔案和排隊時不一樣、請重新上傳；`start_fed` 0 次 | 自動：`test_aws_upload.py::test_symlinked_or_resized_staged_file_is_refused` |
| TC-072 | 作法 3 | 例外 | 該名字在擁有者資料夾裡是資料夾 | 代理處理 | 拒絕，說這不是一般檔案；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-072） |
| TC-073 | 作法 3 | 例外 | 暫存檔不存在 | 代理處理 | 拒絕，說找不到要上傳的檔案、請重新上傳；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-073） |
| TC-074 | 作法 3 | 例外 | 工作的擁有者名字是 `../bob`（想跳出自己的資料夾） | 代理處理 | 拒絕；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-074） |
| TC-075 | 目標（Google 不變） | 功能 | 合法的 Google `put_upload` 工作（假憑證、假 gcloud） | 代理處理 | 假 `start_fed` 收到的指令仍是 `["gcloud","storage","cp","-",dest,"--project",<專案>]`；沒有任何 `aws` 指令被執行 | 自動：`test_station_*.py`／`test_cloud_upload*.py` 既有斷言不改，加 `test_aws_upload.py`（註解標 TC-075） |
| TC-076 | 作法 4 | 例外 | 合法的 AWS 工作 | 代理處理，記錄所有被啟動的程式 | 沒有任何 `gcloud` 被執行 | 自動：`test_aws_upload.py`（註解標 TC-076） |
| TC-077 | 作法（jobs.py 結果處理） | 功能 | 代理對 AWS 的 `put_upload` 回報成功：`bytes`＝5、`path`＝`s3://lab-bucket/uploads/alice/reads.fastq.gz` | 平台收下結果（take_result） | 工作標成完成，結果 `ok` 為真，`bytes`＝5，`path` 原樣保留 | 自動：`test_aws_upload.py`（註解標 TC-077） |
| TC-078 | 作法（jobs.py 結果處理） | 例外 | 代理回報成功但沒帶 `bytes` 或沒帶 `path` | 平台收下結果 | 結果 `ok` 被改成假（成功必須說明多少位元組、在哪裡） | 自動：`test_aws_upload.py`（註解標 TC-078） |
| TC-079 | 專長守則（回應不含密鑰） | 功能 | 同 TC-039，憑證檔路徑與一個唯一標記字串 | 代理處理成功，看結果與訊息 | 結果的鍵只有 `ok`、`bytes`、`path`、`message`；整個結果搜不到憑證檔路徑、也搜不到標記字串 | 自動：`test_aws_upload.py`（註解標 TC-079） |
| TC-080 | 作法 3 | 例外 | 工作裡環境快照的平台是 Slurm（既不是 Google 也不是 AWS） | 代理處理 | 拒絕，白話說環境類型不對；`start_fed` 0 次 | 自動：`test_aws_upload.py`（註解標 TC-080） |
| TC-081 | 範圍（handlers.py 能不改就不改） | 功能 | 載入代理的 `handlers.ARG_KEYS` 與 `put_upload.ARGS` | 看 `put_upload` 的欄位集合 | 恰為 `ce`、`owner`、`name`、`size`、`dest`，與修改前相同 | 自動：`test_aws_upload.py`（註解標 TC-081） |

## User Story 4 — 超過 2 GB 時，給使用者「自己在自己電腦上傳」的指令（優先度 P1）

作法 7；裁決 6：AWS 版在範圍內，目的地用 `s3://<bucket>/uploads/<owner>/rawdata/`；文字只寫「在你自己的電腦上、用你自己的 AWS 登入執行」，不教怎麼登入 AWS。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-082 | 作法 7；裁決 6 | 功能 | AWS 環境 dict，bucket `lab-bucket`，擁有者 alice | 呼叫 `big_file_command(ce, "alice", scheme="s3")` | 逐字回 `aws s3 cp <你電腦上的資料夾> s3://lab-bucket/uploads/alice/rawdata/ --recursive` | 自動：`test_aws_upload.py`（註解標 TC-082） |
| TC-083 | 作法 7；失敗先行測試 15 | 例外 | AWS 環境可用；alice 的暫存檔大於 2,000,000,000 位元組（測試用假的檔案狀態，不真的建 2 GB） | alice 呼叫 `enqueue_put_upload` | 被拒；訊息含 TC-082 那一行 `aws s3 cp` 指令，並寫明「在你自己的電腦上、用你自己的 AWS 登入」執行、平台不會代你上傳；沒有排入 | 自動：`test_aws_upload.py::test_over_limit_file_gets_the_aws_command_and_a_plain_warning` |
| TC-084 | 作法 7（`check_web_upload`） | 例外 | AWS 環境可用；alice 回報兩個檔案：一個 3,000,000,000、一個 100 位元組，`destination="aws-lab"` | 呼叫 `check_web_upload` | `ok` 為假；`over` 只列大的那個、`accepted` 列小的那個；`command` 是 TC-082 的指令；訊息含「在你自己的電腦上、用你自己的 AWS 登入」與你的前綴 `s3://lab-bucket/uploads/alice/` | 自動：`test_aws_upload.py`（註解標 TC-084） |
| TC-085 | 裁決 6（不教怎麼登入 AWS） | 例外 | 同 TC-083 與 TC-084 的訊息 | 搜尋訊息全文 | 不含 `aws configure`、`aws sso`、`access key` 之類教人登入的步驟，也不含任何金鑰字樣 | 自動：`test_aws_upload.py`（註解標 TC-085） |
| TC-086 | 目標（Google 一個字都不變） | 功能 | Google 環境 dict | 呼叫 `big_file_command(ce, "alice")` | 逐字回 `gcloud storage cp <你電腦上的資料夾>/* gs://lab-bucket/uploads/alice/rawdata/` | 自動：`test_cloud_upload.py`、`test_byte_channel_a.py:400`（既有，斷言不改） |
| TC-087 | 目標（Google 不變） | 功能 | Google 環境可用；alice 的暫存檔大於 2 GB | alice 呼叫 `enqueue_put_upload` | 被拒，訊息含 `gcloud storage cp` 指令，不含 `aws` | 自動：`test_cloud_upload.py`（既有，斷言不改） |
| TC-088 | 目標（Google 不變） | 功能 | Google 環境；alice 回報一個 3,000,000,000 位元組的檔案 | 呼叫 `check_web_upload(destination="gcb-lab")` | 結果、`command` 與訊息與修改前逐字相同 | 自動：`test_cloud_upload.py`（既有，斷言不改） |
| TC-089 | 作法 3；Google 上限沿用（裁決 3） | 例外 | AWS 環境可用；alice 的暫存檔恰為 2,000,000,001 位元組（假的檔案狀態） | alice 呼叫 `enqueue_put_upload` | 被拒並給 TC-082 的指令；沒有排入 | 自動：`test_aws_upload.py`（註解標 TC-089） |
| TC-090 | 作法 8；失敗先行測試 16 | 例外 | 掃描 `abf_platform/` 底下所有 `.py`（新舊檔） | 搜尋禁字 | 沒有 `boto3`／`botocore`／`google`／`azure` 的匯入；沒有 "station" 字樣；沒有 `subprocess`、`threading` | 自動：`test_aws_upload.py::test_no_cloud_library_and_no_station_word_in_platform_sources` |

## User Story 5 — 把 S3 上的檔案登記成資料集（優先度 P1）

作法 6：不做 migration，是不是雲端路徑看 `path` 開頭是 `gs://` 或 `s3://`；一個資料集的檔案必須同一 scheme；`s3://` 與 `gs://`、本機路徑混在一起要拒絕並說明。A1：實際檔案是 `abf_platform/actions/datasets.py`，不准新增公開函式與參數名。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-091 | 作法 6；失敗先行測試 13 | 功能 | alice 的 AWS 環境 `aws-lab`；兩個檔案 `s3://lab-bucket/uploads/alice/a_R1.fastq.gz`、`.../a_R2.fastq.gz`；樣本表恰好只列這兩個 | `register_dataset(destination="aws-lab", ...)` | 登記成功；存下的每個 `path` 都以 `s3://lab-bucket/uploads/alice/` 開頭 | 自動：`test_aws_upload.py::test_dataset_destination_s3_registers_s3_paths` |
| TC-092 | 作法 6 | 功能 | 同 TC-091 登記成功之後 | alice 用 `get_dataset` 讀回 | 兩個 `path` 與登記時給的逐字相同，沒有多出別的檔案 | 自動：同上 |
| TC-093 | 作法 6；專長守則（跨使用者，寫） | 例外 | 同 TC-091，但有一個檔案是 `s3://lab-bucket/uploads/bob/a_R1.fastq.gz` | 登記 | 被拒；訊息只提 alice 自己的前綴 `s3://lab-bucket/uploads/alice/`，不提 bob；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-093） |
| TC-094 | 作法 6 | 例外 | 有一個檔案是 `s3://other-bucket/uploads/alice/a_R1.fastq.gz` | 登記 | 被拒；訊息說 bucket 必須是這個環境 workDir 所在的 `lab-bucket`；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-094） |
| TC-095 | 作法 2、6 | 例外 | 有一個檔案是 `s3://lab-bucket/uploads/alice2/a_R1.fastq.gz`（前綴撞名） | 登記 | 被拒；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-095） |
| TC-096 | 作法 2、6 | 例外 | 有一個檔案是 `s3://lab-bucket/uploads/alice/../bob/a_R1.fastq.gz` | 登記 | 被拒；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-096） |
| TC-097 | 作法 6；失敗先行測試 14 | 例外 | 目的地 `aws-lab`；檔案一個是 `s3://lab-bucket/uploads/alice/a_R1.fastq.gz`、一個是 `gs://lab-bucket/uploads/alice/a_R2.fastq.gz` | 登記 | 被拒，白話說明一份資料集的檔案要全是同一種（`s3://`）；資料表沒有新增 | 自動：`test_aws_upload.py::test_mixed_schemes_in_one_dataset_are_refused` |
| TC-098 | 作法 6；失敗先行測試 14 | 例外 | 目的地 `aws-lab`；檔案一個是 s3 位置、一個是本機路徑 | 登記 | 被拒，白話說明不能同時混本機路徑與雲端位置；資料表沒有新增 | 自動：同上 |
| TC-099 | 作法 6 | 例外 | 目的地是 Google 環境 `gcb-lab`；有一個檔案是 `s3://lab-bucket/uploads/alice/a_R1.fastq.gz` | 登記 | 被拒，說只收 `gs://` 開頭的位置；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-099） |
| TC-100 | 作法 6 | 例外 | 同 TC-091，但樣本表裡有一個 `s3://` 位置不在登記的檔案內 | 登記 | 被拒，說樣本表裡有檔案不在登記的檔案內；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-100） |
| TC-101 | 作法 6（既有規則不退步） | 例外 | 同 TC-091，但樣本表某一格是 `https://example.test/x.fastq.gz` | 登記 | 仍被拒（樣本表含網址不收）；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-101） |
| TC-102 | 作法 6（`draft_samplesheet`） | 功能 | 目的地 `aws-lab`；給兩個單層檔名 `a_R1.fastq.gz`、`a_R2.fastq.gz` | 呼叫 `draft_samplesheet` | 配成一組，樣本表草稿裡的路徑是 `s3://lab-bucket/uploads/alice/a_R1.fastq.gz` 與 `.../a_R2.fastq.gz`；沒有寫入任何東西 | 自動：`test_aws_upload.py`（註解標 TC-102） |
| TC-103 | 作法 6 | 例外 | 目的地 `aws-lab`；給 `s3://lab-bucket/uploads/bob/a_R1.fastq.gz` | 呼叫 `draft_samplesheet` | 被拒，訊息只提 alice 自己的前綴 | 自動：`test_aws_upload.py`（註解標 TC-103） |
| TC-104 | 作法 6 | 例外 | 目的地 `aws-lab`；給 `gs://lab-bucket/uploads/alice/a_R1.fastq.gz` | 呼叫 `draft_samplesheet` | 被拒，說明要的是 `s3://` 位置 | 自動：`test_aws_upload.py`（註解標 TC-104） |
| TC-105 | 作法 6 | 功能 | 目的地 `aws-lab`；回報的檔案都不超過 2 GB | 呼叫 `check_web_upload` | `ok` 為真，`accepted` 列出全部檔名，`over` 為空 | 自動：`test_aws_upload.py`（註解標 TC-105） |
| TC-106 | 作法 6；目標（不退步） | 功能 | 不給 `destination`；檔案在 alice 自己的上傳資料夾（本機路徑） | 登記；另試一個 `s3://` 檔案 | 本機路徑照舊登記成功；`s3://` 開頭的檔案照舊被拒（樣本表／路徑含網址不收） | 自動：`test_datasets.py`、`test_scope.py`（既有，斷言不改） |
| TC-107 | 目標（Google 不變） | 功能 | 目的地 `gcb-lab`；兩個 `gs://lab-bucket/uploads/alice/...` 檔案 | 登記 | 與修改前相同，登記成功，路徑原樣 | 自動：`test_cloud_upload.py`（既有，斷言不改） |
| TC-108 | 專長守則（跨使用者，寫） | 例外 | `aws-lab` 是 alice 的環境；bob 登入 | bob 登記時把目的地填 `aws-lab` | 被拒，訊息「找不到計算環境」（與環境不存在相同）；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-108） |
| TC-109 | 專長守則（跨使用者，讀） | 例外 | alice 已登記含 s3 路徑的資料集 `reads` | bob 用自己的身分 `list_datasets`、`get_dataset("reads")` | 列表看不到它；`get_dataset` 回「找不到」，不透露 alice 的路徑 | 自動：`test_aws_upload.py`（註解標 TC-109） |
| TC-110 | 作法 6 | 例外 | 目的地是 Slurm 環境 | 登記 | 被拒，白話說這個環境不能放雲端資料；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-110） |
| TC-111 | 專長守則（不得含密鑰）；既有規則不退步 | 例外 | 目的地 `aws-lab`；檔案路徑含像憑證的值（假的長金鑰字串） | 登記 | 被拒，說路徑含像憑證的值；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-111） |
| TC-112 | 作法 6（不做 migration）；專長守則（結構變動） | 功能 | 比較修改前後的資料集資料表定義與 migration 清單 | 看差異 | 資料表欄位與定義與修改前完全相同；沒有新增 migration；計畫已寫明不需要 migration 的理由（看 `path` 開頭判斷是 `gs://` 還是 `s3://`） | 自動：`test_aws_upload.py`（註解標 TC-112） |
| TC-113 | 範圍（A1）；不准新增公開函式與參數名 | 功能 | 列出 `actions/datasets.py` 的公開函式（不以底線開頭）及 `draft_samplesheet`／`check_web_upload`／`register_dataset` 的參數名 | 與修改前比對 | 公開函式清單與這三個函式的參數名逐字相同 | 自動：`test_aws_upload.py`（註解標 TC-113）；既有的公開函式清單測試（計畫稱 TC-063）仍綠 |

## User Story 6 — 邊界、不在範圍、文件（優先度 P1）

計畫「不做」五條、作法 8、裁決 5、裁決 7、A3(d)，以及文件要求。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-114 | 作法 8；「環境事實」第二點；失敗先行測試 16 | 例外 | 掃描 `abf_station/put_upload.py` 與本任務動過的代理端檔案 | 搜尋禁字與啟動程式的方式 | 沒有 `boto3`／`botocore`／`google`／`azure` 匯入；沒有 `subprocess`、`shell=True`；啟動程式只經 `site.run_fixed` 與 `site.start_fed`，沒有新增另一條路徑 | 自動：`test_aws_upload.py`（註解標 TC-114） |
| TC-115 | 作法 8；範圍（datasets 的禁字） | 例外 | 掃描 `cloud_store.py` 與 `actions/datasets.py` | 搜尋 `open(`、`hashlib`、`subprocess`、`os.system`、`socket`、`urllib`、`httpx`、`requests`、`import google`、`boto3`、`azure`、`station` 等既有禁字 | 一個都沒出現（註解與變數名也不能含）；既有的禁字掃描測試維持綠 | 自動：`test_cloud_upload.py`、`test_scope.py`、`test_datasets.py`（既有，不改） |
| TC-116 | ADR 0010；失敗先行測試 17；不做（不新增 MCP 上傳工具） | 不在範圍 | 載入 MCP 工具清單 | 搜尋工具名稱 | 沒有任何名稱含 `upload` 的工具 | 自動：`test_aws_upload.py::test_no_mcp_upload_tool_exists` |
| TC-117 | 裁決 7；不做（不改網頁檔案） | 不在範圍 | 掃描 `abf_platform/`、`abf_launch/`、CLI 與 MCP 的原始碼 | 搜尋 `enqueue_put_upload` 的呼叫處 | 除了定義它的 `jobs.py`，沒有任何網頁、MCP 工具或指令列呼叫它（網頁入口尚未接上，與 Google 版現況一樣） | 自動：`test_aws_upload.py`（註解標 TC-117） |
| TC-118 | 不做（不做 S3 刪除；不用 `s3 sync`、`--acl`、presigned URL） | 不在範圍 | 本檔所有代理端情境中記錄到的全部指令，以及 `put_upload.py` 原始碼 | 搜尋 | 沒有 `s3 rm`、`delete-object`、`s3 sync`、`--acl`、`presign`；唯一寫入 S3 的是 TC-040 那一個 `aws s3 cp -` | 自動：`test_aws_upload.py`（註解標 TC-118） |
| TC-119 | 不做（不做費用估算，C-3） | 不在範圍 | 一次成功的與一次失敗的 AWS 上傳；`put_upload.py`、`cloud_store.py`、`jobs.py` 的上傳相關程式 | 看匯入與所有訊息 | 沒有匯入或呼叫費用估算模組；訊息裡沒有任何金額或幣別 | 自動：`test_aws_upload.py`（註解標 TC-119） |
| TC-120 | 不做（不做續跑） | 不在範圍 | 一筆 AWS `put_upload` 工作，aws 程式中途失敗 | 代理處理一次 | 假 `start_fed` 只被呼叫 1 次，沒有自動重試或續傳；結果是失敗，暫存檔仍在 | 自動：`test_aws_upload.py`（註解標 TC-120） |
| TC-121 | 不做（不做跨環境搬資料） | 不在範圍 | 目的地 `aws-lab`；檔案是 Google 上傳留下的 `gs://lab-bucket/uploads/alice/a_R1.fastq.gz` | 登記資料集 | 被拒（要的是 `s3://`）；沒有任何程式被啟動、沒有任何檔案被搬動；資料表沒有新增 | 自動：`test_aws_upload.py`（註解標 TC-121） |
| TC-122 | 作法 8（文件）；裁決 7 | 功能 | 讀 `docs/PLATFORM.md` | 找 AWS Batch 上傳那一段 | 有一段寫明：AWS 環境可以由平台主機上的代理把檔案串流寫進 `s3://<workDir 的 bucket>/uploads/<擁有者>/`，成為可登記成資料集的位置；並明說「網頁入口尚未接上」（目前沒有網頁或 MCP 呼叫它） | 自動：`test_aws_upload.py`（註解標 TC-122，掃文件關鍵句） |
| TC-123 | 作法 1；裁決 A3(d)；文件 | 功能 | 讀 `docs/PLATFORM.md` | 找 AWS Batch 相關各處 | 不再有任何句子說 AWS 的上傳「尚未支援」或「上傳留給之後的 aws-upload」；仍寫明清理（aws-clean）與列出檔案、讀回紀錄是尚未支援 | 自動：`test_aws_upload.py`（註解標 TC-123） |
| TC-124 | 裁決 5 | 功能 | 讀 `docs/PLATFORM.md` 的 AWS 上傳段 | 找 bucket 版本控管的說明 | 有一句寫明：bucket 若開了版本控管，覆寫同名檔會留下舊版本、仍然收費 | 自動：`test_aws_upload.py`（註解標 TC-124） |
| TC-125 | 裁決 A3(d) | 功能 | 讀 `docs/SEQERA_PARITY.md` 的 AWS Batch 那一列 | 比對 | 那一列含逐字 `Have (create + check + launch + cancel + upload); clean in aws-clean`，且該列仍以 `[ ] |` 結尾；`test_aws_ce.py:927`、`test_aws_launch.py:1228` 的逐字比對已改成這句 | 自動：`test_aws_ce.py`、`test_aws_launch.py`（A3(d) 更新後的既有測試） |
| TC-126 | 完成標準（真實上傳不屬完成標準）；作法文件要求 | 功能 | 讀 `docs/TESTING.md` | 找 AWS 上傳的段落 | 有一段寫明：真的往 AWS 上傳會花錢，屬於需維護者另外點頭、並先設好 AWS Budgets 警示才做的手動實跑，不屬完成標準；步驟具體到維護者能照做（用哪個環境、傳多大的檔、預期看到什麼） | 手動：`docs/TESTING.md`（閱卷者確認該段存在且夠具體；維護者實跑不屬本任務完成標準） |
| TC-127 | 憲法第 1 條（先查現成工具）；計畫「範圍」 | 功能 | 打開新檔 `platform/tests/test_aws_upload.py` | 看檔頭前 40 行 | 有一行 `# Nothing existing: …`，冒號後至少 15 個字 | 自動：專案既有的檔頭掃描測試（計畫稱 TC-070），以及 `bash tests/scripts_name_their_alternative.sh` |

## 憲法與安全網

本任務動到憲法第 1 條（先查現成工具）、第 2 條（不新增送出路徑與第二份狀態）、ADR 0010（聊天與權杖沒有上傳工具）、以及「憑證只留在設定檔」這條檢查；另依 backend 專長守則補確認管道、對等性、錯誤訊息與無密鑰的 TC。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-128 | 憲法第 2 條（不新增送出路徑） | 功能 | 本任務完成後的整個 repo | 跑 `bash tests/no_second_run_state_test.sh` | 通過；`put_upload` 只寫資料，沒有新增任何會「送出分析」的檔案（沒有 sbatch、沒有 Batch 工作的建立） | 自動：`tests/no_second_run_state_test.sh` |
| TC-129 | 「憑證只留在設定檔」檢查 | 功能 | 本任務完成後的整個 repo（含 `test_aws_upload.py`） | 跑 `bash tests/credentials_stay_in_settings_test.sh` | 通過；憑證相關鍵名在測試裡是用字串相加組出的，沒有整串明寫 | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-130 | 專長守則（確認管道）；目標 | 例外 | 一個 `available` 的 AWS 環境；有人想用一般的排工作入口（`_enqueue`／泛用排工作）直接排 `put_upload` | 試排 | 被拒，說明上傳只能走專用入口 `enqueue_put_upload`；工作表列數不變 | 自動：`test_aws_upload.py`（註解標 TC-130） |
| TC-131 | 專長守則（對等性）；不做（不新增 MCP 工具、不改網頁） | 功能 | 同時列出「使用者可見的動作」（MCP 工具名單、網頁路由、指令列子命令）與「動作層函式」 | 與修改前的清單比對 | 兩邊都與修改前完全相同（本任務沒有新增任何使用者可見動作；動作層的 `datasets` 函式也沒有新增） | 自動：`test_aws_upload.py`（註解標 TC-131） |
| TC-132 | 專長守則（錯誤訊息說明原因與處理方式，不露出堆疊或內部路徑） | 例外 | 跑 TC-003、TC-046、TC-047、TC-067、TC-069、TC-070、TC-083 的失敗情境 | 看每則回應 | 每則都用白話說明發生什麼事與下一步；沒有 `Traceback`、沒有 `File "..."`、沒有 SQL、沒有暫存檔本機路徑（TC-067 的憑證檔路徑是計畫允許的唯一例外） | 自動：`test_aws_upload.py`（註解標 TC-132） |
| TC-133 | 維護者原話（PLAN 第 40 行：憑證 → 計算環境 → 資料集，掛在已建好的環境與憑證名字上，不另要使用者輸入金鑰） | 功能 | 排入一筆 AWS `put_upload` 工作，環境有 `credentialsId` 名字 | 檢查工作內容、資料庫中的那一列、代理的結果 | 工作只帶憑證的「名字」，沒有憑證檔路徑也沒有任何金鑰值；上傳流程中沒有任何一步要使用者輸入金鑰；代理的憑證只來自它自己的設定（`ABF_STATION_AWS_CREDENTIALS` 或預設的 `_personal/aws-credentials`） | 自動：`test_aws_upload.py`（註解標 TC-133） |
