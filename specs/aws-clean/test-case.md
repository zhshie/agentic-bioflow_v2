# 測試案例：AWS 跑完清理 S3 work 前綴（aws-clean，clean_work）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：本任務沒有 spec.md，以 `specs/aws-clean/plan.md`（含「維護者原話」、文末「裁決」與 E1–E12；與上文衝突時以 E 段為準）為規格。
IDs: TC-001..TC-108。每條只測一件事；驗證方式「自動」＝ `platform/tests/test_aws_clean.py`（平台端）、`platform/tests/test_station_clean_aws.py`（站台代理端），或計畫 E2 指定要更新的既有測試檔，並在測試內以註解 `# TC-nnn` 標明。
所有測試輸入都用假值：`lab-bucket`、`eu-west-1`、`aws-lab`、run 名稱 `r1`、擁有者 `alice`、`bob`；全部用假的 `site.run_fixed`（記錄每次呼叫的指令清單與環境變數），`tmp_path` 當 `storage_root`；不碰網路、不呼叫真的 aws、不花錢。
假 bucket 的內容含鄰居物件：`runs/r1/work/…`（要清的）、`runs/r1/work2/…`、`runs/r1/work-keep`、`runs/r1/results/…`、`runs/other/work/…`、`uploads/alice/…`。假的列舉與刪除只處理「以該網址的鍵為開頭」的物件，輸出格式照官方文件（網址記在 ledger）。
憑證相關的鍵名在測試裡用字串相加組出來，避免被 `tests/credentials_stay_in_settings_test.sh` 掃到。
呼叫數的寫法（E5）：站台代理在「檢查 run 資料夾、環境、work 路徑」這幾步就停的案例，`run_fixed` 的呼叫總數是 0；到了「查 head 程序」之後才停的案例，則是「沒有任何列舉、沒有任何刪除呼叫」，head 程序還活著時連 aws 都沒有被呼叫。
-->

**規格**：`specs/aws-clean/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「尚未支援」而不是悄悄亂做。

名詞：**站台代理**＝裝在平台主機上、唯一會真的執行 `aws` 指令的程式（平台本身不碰 AWS，也不刪任何東西）；**work 前綴**＝這個 run 在 S3 上的暫存位置 `s3://<bucket>/…/runs/<run>/work/`；**results**＝這個 run 的結果，在同一層的 `results/`，絕不能動；**放行表**＝`compute_envs.CLOUD_JOB_KINDS`，每一種雲端環境各自列出它肯接的工作種類；**內容包**＝平台寫給站台代理的清理申請（run 名稱、資料夾、環境快照、work 路徑等七個欄位）；**預檢**＝站台代理在動手前再做一次的唯讀檢查（憑證檔、身分、job queue、bucket）；**前綴撞名**＝`work2/`、`work-keep` 這種名字開頭和 `work` 一樣、但不是 work 底下的東西。

## User Story 1 — 平台端：放行、準備、提出、記錄（優先度 P1）

計畫目標：「一個在 AWS Batch 環境成功跑完的 run，平台提出『清理 work 目錄』的申請，本人在確認頁答 y 之後……刪完平台記下 `work_cleaned_at`，同一個 run 不會再被提出第二次。」維護者採納的 aws-launch 裁決 A3：「AWS 的 clean 先關閉，另開 `aws-clean`。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；失敗先行測試 15；A3 | 功能 | 目前的 `compute_envs.CLOUD_JOB_KINDS` | 讀 AWS 那一格 | 恰含 `preflight`、`launch_nextflow`、`cancel_run`、`clean_work`、`put_upload`、`pipeline_files` 六種（原有五種不少，只多 `clean_work`） | 自動：`test_aws_clean.py::test_clean_work_is_allowed_for_aws_and_still_for_google` |
| TC-002 | 失敗先行測試 15 | 功能 | 同上 | 讀 Google 那一格 | 與修改前逐字相同（六種，順序不變） | 自動：同上 |
| TC-003 | 作法 1；A3 | 功能 | AWS 環境（代理在線）；有一筆已被本人確認的 `clean_work` 申請，run 為 alice 送出的 AWS run | alice 排入 `clean_work` 工作 | 工作排入，種類是 `clean_work`，指派給該環境的代理 | 自動：`test_aws_clean.py`（註解標 TC-003） |
| TC-004 | 作法 1（不要順手要求環境 available） | 功能 | 同 TC-003，但環境狀態不是 `available`（例如 `invalid`），也不是 `disabled`／`unsupported` | 排入 `clean_work`；同一環境再試 `put_upload` | `clean_work` 排入成功（與 Google 一致）；`put_upload` 仍因狀態不是 available 被拒 | 自動：`test_aws_clean.py`（註解標 TC-004） |
| TC-005 | 作法 2.1；憲法 I.2 | 例外 | AWS 環境；沒有任何確認（或確認尚未被本人按下） | 嘗試排入 `clean_work` | 被拒，說明需要本人的確認；沒有工作被排入 | 自動：`test_aws_clean.py`（註解標 TC-005） |
| TC-006 | E4；作法 1 | 例外 | AWS 環境；`list_site_files`（不在 AWS 放行表） | 嘗試排入 | 被拒，訊息含「尚未支援」；訊息**不含**「aws-clean」也**不含**「aws-upload」字樣 | 自動：`test_aws_clean.py`（註解標 TC-006） |
| TC-007 | E4 | 功能 | Google 環境；一個不在 Google 放行表的種類 | 嘗試排入 | 被拒的句子與修改前逐字相同（「Google Batch environment: this job kind is not built for it yet (尚未支援)」） | 自動：`test_aws_ce.py`／`test_aws_launch.py` 既有斷言（不改）＋ `test_aws_clean.py`（註解標 TC-007） |
| TC-008 | 目標（與 Google 同一套核對） | 例外 | AWS 環境；`clean_work` 內容包的 `run_folder` 或 `slurm_job_id` 和平台的送出紀錄不同，或欄位多一個／少一個 | 嘗試排入 | 被拒，說內容與紀錄不一致、請重新申請；沒有工作被排入 | 自動：`test_aws_clean.py`（註解標 TC-008） |
| TC-009 | 失敗先行測試 16；E1 | 功能 | 平台記錄有一筆成功的 AWS run `r1`：環境 `workDir=s3://lab-bucket`，run 資料夾 `<storage_root>/_aws_runs/r1`，有工作編號，沒清過 | 呼叫 `prepare_clean` | 回傳的內容包恰有七個欄位，`work == "s3://lab-bucket/runs/r1/work"`（手算），`run_folder` 是送出紀錄裡的那個；不會被「必須在 workDir/runs 底下」那條擋掉 | 自動：`test_aws_clean.py::test_prepare_clean_accepts_a_succeeded_aws_run` |
| TC-010 | E10 | 功能 | 同 TC-009，但環境 `workDir=s3://lab-bucket/work` | 呼叫 `prepare_clean` | `work == "s3://lab-bucket/work/runs/r1/work"`（子目錄照字面接上） | 自動：`test_aws_clean.py`（註解標 TC-010） |
| TC-011 | 範圍（build.py `clean_work_path`）；目標（Google／Slurm 不變） | 功能 | 三種環境快照：Google（`gs://lab-bucket/work`）、Slurm、AWS | 呼叫 `clean_work_path` | Google 回 `gs://lab-bucket/work/runs/r1/work`、Slurm 回 `<run 資料夾>/work`（兩者與修改前逐字相同）；AWS 回 `<workDir>/runs/r1/work` | 自動：`test_aws_clean.py`（註解標 TC-011） |
| TC-012 | 失敗先行測試 17 | 例外 | 同 TC-009，但環境的 `workDir` 在 run 送出之後被改過 | 呼叫 `prepare_clean` | 被拒，說環境在 run 送出之後改過、無法確認路徑，所以不提出清理；沒有內容包 | 自動：`test_aws_clean.py::test_prepare_clean_refuses_when_the_environment_changed_after_the_run` |
| TC-013 | 失敗先行測試 18 | 例外 | 同 TC-009，但這個 run 的 `work_cleaned_at` 已有值 | 呼叫 `prepare_clean` | 被拒，說 work 目錄已經清過了 | 自動：`test_aws_clean.py::test_prepare_clean_refuses_an_already_cleaned_run` |
| TC-014 | 範圍（build.py 只改 Google 與 AWS 的那一行） | 例外 | 一個 Slurm run，其 `run_folder` 的上一層不是 `<workDir>/runs` | 呼叫 `prepare_clean` | 仍被拒（說環境改過、無法確認路徑）；Slurm 的規則沒有被放寬 | 自動：`test_aws_clean.py`（註解標 TC-014） |
| TC-015 | 專長守則（跨使用者，讀） | 例外 | alice 送出的 AWS run `r1`；bob 是另一位使用者 | 以 bob 的身分呼叫 `prepare_clean(…, owner=bob)` | 被拒，說 `r1` 不是平台自己送出的（與 run 不存在的說法相同）；沒有洩漏 alice 的環境或路徑 | 自動：`test_aws_clean.py`（註解標 TC-015） |
| TC-016 | 專長守則（跨使用者，寫） | 例外 | 同 TC-015；bob 自己有一筆已確認的 `clean_work` 申請，內容指向 alice 的 `r1` | bob 嘗試排入 `clean_work` | 被拒（對 bob 而言這個 run 不存在）；沒有工作被排入 | 自動：`test_aws_clean.py`（註解標 TC-016） |
| TC-017 | 失敗先行測試 19；作法 7 | 功能 | 一個成功的 AWS run（索引裡狀態 `succeeded`），有擁有者 alice，沒清過 | 呼叫 `offer_cleanup` | 為 alice 建立一筆待確認的 `clean_work` 申請，內容是 TC-009 的內容包，附上確認畫面文字 | 自動：`test_aws_clean.py::test_offer_cleanup_offers_for_a_succeeded_aws_run` |
| TC-018 | 失敗先行測試 19；裁決 7 | 例外 | 失敗的 AWS run；取消的 AWS run | 各呼叫一次 `offer_cleanup` | 都不提出，回的理由寫明只有成功的 run 才提出清理；沒有建立任何申請 | 自動：同上 |
| TC-019 | 作法 7（`offer_cleanups` 指令不改） | 功能 | 兩個 AWS run：一個成功、一個失敗 | 呼叫 `offer_cleanups` | `offered` 為 1、`skipped` 為 1；成功的那個被提出 | 自動：`test_aws_clean.py`（註解標 TC-019） |
| TC-020 | 作法 7；目標（提出只是申請） | 例外 | 同 TC-017 | 呼叫 `offer_cleanup` 之後看資料庫 | `clean_work` 的確認列狀態是「待確認」；工作表沒有新增任何一列；沒有任何 aws 呼叫（平台不刪東西） | 自動：`test_aws_clean.py`（註解標 TC-020） |
| TC-021 | 失敗先行測試 21；作法 5 | 功能 | 一個 AWS `clean_work` 工作；站台代理回報 `("done", {ok: True, cleaned: True, run_name, message})` | 平台收下結果（take_result） | 該 run（依工作內容裡的 run 名稱與工作編號）的 `work_cleaned_at` 被寫入 | 自動：`test_aws_clean.py::test_work_cleaned_at_is_written_only_when_cleaned_is_true` |
| TC-022 | 失敗先行測試 21；作法 5 | 例外 | 同 TC-021，但回報 `cleaned: False`、或沒有 `cleaned`、或 `ok: False`、或狀態是 error／refused | 平台收下結果 | `work_cleaned_at` 不寫入 | 自動：同上 |
| TC-023 | 目標（同一個 run 不會再被提出第二次） | 功能 | TC-021 之後 | 再呼叫 `offer_cleanup` 與 `prepare_clean` | 都不提出／被拒，說已經清過了 | 自動：`test_aws_clean.py`（註解標 TC-023） |
| TC-024 | 失敗先行測試 22 | 功能 | AWS 環境；既有的 `launch_nextflow`、`cancel_run` 申請 | 排入工作 | 結果（排入或被拒、訊息）與 aws-launch 合併後的行為完全相同 | 自動：`test_aws_clean.py::test_clean_work_result_for_aws_leaves_launch_and_cancel_unchanged` |

## User Story 2 — 本人看到的確認畫面（優先度 P1）

計畫失敗先行測試 20 與 E9：畫面寫明刪的是哪個前綴、什麼不會動、刪了無法復原；沒有金額；Google 畫面一字不變。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 失敗先行測試 20；E9 | 功能 | TC-009 的 AWS 內容包（`work = s3://lab-bucket/runs/r1/work`） | 呼叫 `clean_screen` | 畫面印出 `s3://lab-bucket/runs/r1/work/`（帶結尾斜線）和 run 名稱 `r1` | 自動：`test_aws_clean.py::test_the_clean_screen_says_what_is_deleted_and_what_is_kept_in_plain_words` |
| TC-026 | 失敗先行測試 20 | 功能 | 同上 | 看畫面 | 寫明 results、原始資料與分析資料夾不會被動 | 自動：同上 |
| TC-027 | 失敗先行測試 20；E9 | 功能 | 同上 | 看畫面 | 寫明這是「永久刪除」（即無法復原；不必逐字「刪除無法復原」） | 自動：同上 |
| TC-028 | 失敗先行測試 20；不做（費用估算） | 例外 | 同上 | 搜尋畫面全文 | 沒有金額、貨幣符號、「台幣」「NT$」「USD」之類的換算 | 自動：同上 |
| TC-029 | 範圍（build.py：畫面若寫死 Google／bucket／gcloud 要改成白話的 S3 說明） | 例外 | 同上 | 搜尋畫面全文 | 沒有「Google」「gcloud」「軟刪除」「7 天」等只對 Google 成立的說法；不會對 AWS 使用者說 Google 的規則 | 自動：`test_aws_clean.py`（註解標 TC-029） |
| TC-030 | E9（Google 畫面一字不變） | 功能 | Google 的內容包 | 呼叫 `clean_screen` | 每一行與修改前逐字相同（含 bucket 與 7 天軟刪除的兩句） | 自動：`test_cleanup_confirm.py` 既有斷言（不改） |
| TC-031 | E9 | 功能 | Slurm 的內容包 | 呼叫 `clean_screen` | 每一行與修改前逐字相同（不含 bucket 的句子） | 自動：同上 |

## User Story 3 — 站台代理的護欄、列舉、只刪一次（優先度 P1）

計畫作法 2、3、4、5、6 與失敗先行測試 1–14；維護者的派工指示：「刪雲端資料只限該 run 的 work 前綴，確認與護欄要和 gcs 清理相同，絕不刪前綴之外。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 失敗先行測試 1；E6 | 功能 | 合法的 AWS 清理（有效確認、內容包欄位齊全、`workDir=s3://lab-bucket`、`eu-west-1`、run 資料夾 `<storage_root>/_aws_runs/r1`、`head.pid` 的程序已不在、預檢全通過）；假 bucket 的 work 前綴下有幾個物件 | 站台代理處理 | `run_fixed` 的呼叫裡，列舉恰好一次、`rm` 恰好一次，且 `rm` 是最後一個 aws 呼叫；其餘呼叫只能是唯讀檢查（查程序的 `ps`、預檢的 sts／batch describe／head-bucket） | 自動：`test_station_clean_aws.py::test_clean_aws_lists_then_removes_exactly_one_prefix` |
| TC-033 | 失敗先行測試 1；E8 | 功能 | 同 TC-032 | 看那次 `rm` 的指令 | 恰為 `["aws","s3","rm","s3://lab-bucket/runs/r1/work/","--recursive","--region","eu-west-1"]`：是清單、不是 shell 文字；前綴結尾有斜線；沒有 `--include`／`--exclude`／`--dryrun` 等任何其他旗標 | 自動：同上 |
| TC-034 | 作法 5 | 功能 | 同 TC-032 | 看站台代理的回報 | 狀態 `done`；鍵恰為 `ok`、`cleaned`、`run_name`、`message`；`ok` 與 `cleaned` 都是真；`run_name` 是 `r1`；訊息用白話說已刪除該前綴底下的物件、results 沒有動，不含 gcloud／Google 字樣 | 自動：`test_station_clean_aws.py`（註解標 TC-034） |
| TC-035 | 作法 3；E6 | 功能 | 同 TC-032 | 看那次列舉的指令 | 是 `aws s3 ls`（含遞迴）或 `aws s3api list-objects-v2`，目標是 work 前綴、帶 `--region eu-west-1`，不帶 `--max-items`；不含任何刪除或寫入字眼；在 `rm` 之前執行 | 自動：`test_station_clean_aws.py`（註解標 TC-035） |
| TC-036 | E10；E8 | 功能 | 同 TC-032，但環境 `workDir=s3://lab-bucket/work`；假 bucket 的鍵是 `work/runs/r1/work/…` | 站台代理處理 | `rm` 的指令恰為 `["aws","s3","rm","s3://lab-bucket/work/runs/r1/work/","--recursive","--region","eu-west-1"]`；成功 | 自動：`test_station_clean_aws.py`（註解標 TC-036） |
| TC-037 | 失敗先行測試 2；作法 2.1 | 例外 | 沒有有效確認（沒有本人答 y） | 站台代理處理 | 拒絕；`run_fixed` 呼叫數 0（aws 一次都沒呼叫） | 自動：`test_station_clean_aws.py::test_unconfirmed_clean_is_refused_and_aws_is_never_called` |
| TC-038 | 失敗先行測試 3 | 例外 | 確認的類型是 `launch`（不是 `clean_work`） | 站台代理處理 | 拒絕；呼叫數 0 | 自動：`test_station_clean_aws.py::test_expired_or_wrong_type_confirmation_is_refused` |
| TC-039 | 失敗先行測試 3 | 例外 | 確認已超過期限 | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-040 | 作法 2.1（確認與 Google 逐項相同） | 例外 | 確認有效，但內容包在確認之後被改過（雜湊對不上） | 站台代理處理 | 拒絕；呼叫數 0 | 自動：`test_station_clean_aws.py`（註解標 TC-040） |
| TC-041 | 作法 2.2 | 例外 | 內容包多一個欄位，或少一個欄位 | 站台代理處理 | 拒絕，說欄位不對；呼叫數 0 | 自動：`test_station_clean_aws.py`（註解標 TC-041） |
| TC-042 | 作法 2.2 | 例外 | 內容包的 `agent` 不是這個代理的名字 | 站台代理處理 | 拒絕，說這個清理是給另一個代理的；呼叫數 0 | 自動：`test_station_clean_aws.py`（註解標 TC-042） |
| TC-043 | 作法 2.2 | 例外 | run 名稱不符平台給的格式（例如大寫、含 `/`、空字串、超過 64 字） | 站台代理處理 | 拒絕，說 run 名稱不對；呼叫數 0 | 自動：`test_station_clean_aws.py`（註解標 TC-043） |
| TC-044 | 作法 2.2 | 例外 | `slurm_job_id` 是 `true`、文字 `"5"`、0、負數，或超過 2^31-1 | 站台代理處理 | 拒絕，說編號必須是一個十進位數字；呼叫數 0 | 自動：`test_station_clean_aws.py`（註解標 TC-044） |
| TC-045 | 失敗先行測試 9；作法 2.3 | 例外 | 內容包的 `run_folder` 不是 `<storage_root>/_aws_runs/r1`（例如 `<storage_root>/_gcb_runs/r1`、別的 run 的資料夾、或 storage_root 之外） | 站台代理處理 | 拒絕，說專屬資料夾不是這台主機上這個 run 的那一個；呼叫數 0 | 自動：`test_station_clean_aws.py::test_run_folder_must_be_the_aws_runs_folder` |
| TC-046 | 作法 2.3 | 例外 | 部署設定沒有 `storage_root` | 站台代理處理 | 拒絕，說沒有 storage_root；呼叫數 0 | 自動：`test_station_clean_aws.py`（註解標 TC-046） |
| TC-047 | 失敗先行測試 10；作法 2.4 | 例外 | 內容包裡環境的 `workDir` 不是 `s3://` 開頭 | 站台代理處理 | 拒絕並說 workDir 不合規則；呼叫數 0 | 自動：`test_station_clean_aws.py::test_environment_is_judged_again_and_a_bad_bucket_or_region_is_refused` |
| TC-048 | 失敗先行測試 10；作法 2.4 | 例外 | 環境的 bucket 名稱含 `..` | 站台代理處理 | 拒絕；呼叫數 0 | 同上 |
| TC-049 | 失敗先行測試 10；作法 2.4 | 例外 | 環境的 `region` 不符 AWS 區域寫法 | 站台代理處理 | 拒絕；呼叫數 0 | 同上 |
| TC-050 | 失敗先行測試 7；作法 2.5 | 例外 | 內容包的 `work` 被改成 `s3://lab-bucket/runs/r1/`（少了 work） | 站台代理處理 | 拒絕，說路徑不是這個平台給這個 run 的；呼叫數 0 | 自動：`test_station_clean_aws.py::test_work_path_is_recomputed_and_must_match_the_bundle` |
| TC-051 | 失敗先行測試 7；作法 2.5 | 例外 | `work` 被改成 `s3://lab-bucket/runs/r1/results/` | 站台代理處理 | 拒絕；呼叫數 0 | 同上 |
| TC-052 | 失敗先行測試 7；作法 2.5 | 例外 | `work` 被改成 `s3://lab-bucket/runs/r1/work/../results/` | 站台代理處理 | 拒絕；呼叫數 0 | 同上 |
| TC-053 | 失敗先行測試 7；作法 2.6 | 例外 | `work` 被改成另一個 bucket：`s3://other-bucket/runs/r1/work` | 站台代理處理 | 拒絕；呼叫數 0 | 同上 |
| TC-054 | 作法 2.5（逐字相等） | 例外 | `work` 只比站台代理算出的多一個結尾斜線（`s3://lab-bucket/runs/r1/work/`） | 站台代理處理 | 拒絕（不是逐字相等）；呼叫數 0 | 同上 |
| TC-055 | 失敗先行測試 8；作法 2.6 | 例外 | 環境 `workDir=s3://lab-bucket/rawdata`，內容包的 `work` 與站台代理算出的一致（所以只有「路徑段」這道護欄能擋） | 站台代理處理 | 拒絕，說路徑含 rawdata、results、analysis 或 `..`，一律不刪；呼叫數 0 | 自動：`test_station_clean_aws.py::test_barred_segments_and_empty_segments_are_refused` |
| TC-056 | 失敗先行測試 8 | 例外 | 同 TC-055，`workDir=s3://lab-bucket/results` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-057 | 失敗先行測試 8 | 例外 | 同 TC-055，`workDir=s3://lab-bucket/analysis` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-058 | 失敗先行測試 8 | 例外 | 同 TC-055，`workDir=s3://lab-bucket/../x` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-059 | 失敗先行測試 8 | 例外 | 同 TC-055，`workDir=s3://lab-bucket/./x` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-060 | 失敗先行測試 8 | 例外 | 同 TC-055，`workDir=s3://lab-bucket//x`（有空段） | 站台代理處理 | 拒絕，說含空段；呼叫數 0 | 自動：同上 |
| TC-061 | 失敗先行測試 4；作法 2.7 | 例外 | `head.pid` 記的編號等於內容包的，且 `ps` 顯示那個程序還活著、指令列帶 `-name r1` | 站台代理處理 | 拒絕，白話說這個 run 的主控程序還在跑、先等它結束或取消、沒有刪任何東西；沒有任何 aws 呼叫 | 自動：`test_station_clean_aws.py::test_a_running_head_is_refused_and_aws_is_not_called` |
| TC-062 | 作法 2.7 | 例外 | `head.pid` 不存在、或內容不是純數字 | 站台代理處理 | 拒絕，說無法確認主控程序已結束、保守起見不刪；沒有任何 aws 呼叫 | 自動：`test_station_clean_aws.py`（註解標 TC-062） |
| TC-063 | 作法 2.7 | 例外 | `head.pid` 記的編號和內容包的 `slurm_job_id` 不同 | 站台代理處理 | 拒絕；沒有任何 aws 呼叫 | 自動：`test_station_clean_aws.py`（註解標 TC-063） |
| TC-064 | 作法 2.7（沒有名為這個 run 的 nextflow 還在跑才放行） | 功能 | `head.pid` 的編號現在被另一個程式佔用（`ps` 回一行，指令列不帶 `-name r1`），其餘條件合法 | 站台代理處理 | 視為主控程序已不在，繼續做完（走到列舉與 `rm`），成功 | 自動：`test_station_clean_aws.py`（註解標 TC-064） |
| TC-065 | 作法 2.7（重用 `_head_gone`） | 例外 | 查程序的 `ps` 逾時 | 站台代理處理 | 結果是 error，說查詢逾時、沒有刪任何東西、也不重試；沒有任何 aws 呼叫 | 自動：`test_station_clean_aws.py`（註解標 TC-065） |
| TC-066 | 失敗先行測試 14；作法 2.8 | 例外 | 憑證檔不存在（其餘合法，head 已不在） | 站台代理處理 | 失敗，白話說預檢未通過、找不到憑證檔；訊息可含該檔案路徑（這是補充規則 8–13 的唯一例外）但不含任何金鑰值；沒有列舉、沒有刪除呼叫 | 自動：`test_station_clean_aws.py::test_a_missing_credentials_file_fails_with_the_one_allowed_path_detail` |
| TC-067 | 作法 2.8 | 例外 | 憑證檔在，但預檢有一項失敗（例如假的 `head-bucket` 回非零，或憑證檔缺 `[default]`） | 站台代理處理 | 拒絕，說預檢未通過並列出哪一項；沒有列舉、沒有刪除呼叫 | 自動：`test_station_clean_aws.py`（註解標 TC-067） |
| TC-068 | 失敗先行測試 11；憑證約束 | 功能 | 同 TC-032，憑證檔路徑指到 `tmp_path` 下的假檔 | 看列舉與 `rm` 那兩次呼叫的環境變數 | 兩次都有 `AWS_SHARED_CREDENTIALS_FILE`＝那個假檔、`AWS_PROFILE=default`、`AWS_CONFIG_FILE=os.devnull`、`AWS_DEFAULT_REGION=eu-west-1` | 自動：`test_station_clean_aws.py::test_aws_env_has_only_the_credentials_file_and_profile` |
| TC-069 | 失敗先行測試 11；E7 | 例外 | 同 TC-068；測試先在父行程塞假的金鑰類 `AWS_*`（存取金鑰、秘密金鑰、連線階段權杖，鍵名用字串相加組出）、另一個 `AWS_PROFILE`，以及 `ABF_X=假值` | 看列舉與 `rm` 的環境變數 | 金鑰類 `AWS_*` 與所有 `ABF_*` 都不出現；`AWS_PROFILE` 仍是 `default`；除了 TC-068 的四個，只允許 `AWS_PAGER`、`AWS_EC2_METADATA_DISABLED`、`AWS_CA_BUNDLE` | 自動：同 TC-068 |
| TC-070 | 作法 3（沒有 shell） | 功能 | 同 TC-032 | 看所有被記錄的呼叫 | 每一次的指令都是清單（不是字串）；呼叫是經由固定指令執行器 `site.run_fixed`（沒有 shell） | 自動：`test_station_clean_aws.py`（註解標 TC-070） |
| TC-071 | 失敗先行測試 5；作法 3 | 例外 | 其餘合法，但列舉結果混入 `runs/r1/work2/x` | 站台代理處理 | 整個拒絕，白話說列出的物件不全在 work 底下（前綴撞名）、沒有刪；`rm` 沒被呼叫；`cleaned` 不是真 | 自動：`test_station_clean_aws.py::test_listing_with_a_neighbour_prefix_aborts_before_rm` |
| TC-072 | 失敗先行測試 5 | 例外 | 列舉結果混入 `runs/other/work/x` | 站台代理處理 | 整個拒絕；`rm` 沒被呼叫 | 自動：同上 |
| TC-073 | 作法 3（前綴撞名 `work-keep`） | 例外 | 列舉結果混入 `runs/r1/work-keep` | 站台代理處理 | 整個拒絕；`rm` 沒被呼叫 | 自動：同上 |
| TC-074 | 作法 4 | 例外 | 列舉結果混入 `runs/r1/results/x` | 站台代理處理 | 整個拒絕；`rm` 沒被呼叫 | 自動：同上 |
| TC-075 | 裁決 4 改寫成 E6 | 例外 | 列舉輸出很長（超過 1000 行），前面都合法，鄰居鍵 `runs/r1/work2/x` 出現在第 1001 行以後 | 站台代理處理 | 整個拒絕；`rm` 沒被呼叫（不能只看第一頁就放行） | 自動：`test_station_clean_aws.py`（註解標 TC-075；E6 指定的新測試） |
| TC-076 | E6 | 功能 | 列舉輸出超過 1000 行，每一行都在 work 前綴底下 | 站台代理處理 | 成功；`rm` 恰一次（長度不造成誤拒） | 自動：`test_station_clean_aws.py`（註解標 TC-076） |
| TC-077 | 失敗先行測試 6；作法 3 | 功能 | 列舉的結果是官方文件規定的「前綴下沒有任何物件」的樣子 | 站台代理處理 | `cleaned: True`、`ok: True`；訊息白話說「那裡本來就沒有東西」、沒有刪任何東西、results 沒動；沒有 `rm` 呼叫 | 自動：`test_station_clean_aws.py::test_empty_listing_is_a_plain_success_without_rm` |
| TC-078 | 作法 3（通過後才刪） | 例外 | 列舉本身失敗（結束碼非 0，而且不是「沒有物件」的那種輸出） | 站台代理處理 | 狀態 error，`cleaned` 不是真，訊息說列出失敗、沒有刪任何東西、可以再申請；`rm` 沒被呼叫 | 自動：`test_station_clean_aws.py`（註解標 TC-078） |
| TC-079 | 作法 3 | 例外 | 列舉逾時 | 站台代理處理 | `cleaned` 不是真，訊息說逾時、沒有刪任何東西、稍後可再申請；`rm` 沒被呼叫 | 自動：`test_station_clean_aws.py`（註解標 TC-079） |
| TC-080 | E10 | 例外 | 環境 `workDir=s3://lab-bucket/work`；列舉混入 `work/runs/r1/work2/x`；另一案混入 `runs/r1/work/x`（少了 workDir 的子目錄） | 站台代理處理 | 兩案都整個拒絕；`rm` 沒被呼叫（前綴核對以 bucket 加整段前綴為準） | 自動：`test_station_clean_aws.py`（註解標 TC-080） |
| TC-081 | 失敗先行測試 12；作法 3（不重試） | 例外 | 其餘合法，假 `rm` 回非零 | 站台代理處理 | `rm` 只被呼叫一次（不重試）；`cleaned` 不是真；訊息白話說刪除沒有成功、可能只刪了一部分、`work_cleaned_at` 沒記、可以再申請；不含完整輸出 | 自動：`test_station_clean_aws.py::test_a_failed_rm_is_not_retried_and_cleaned_is_false` |
| TC-082 | 作法 3 | 例外 | 假 `rm` 逾時 | 站台代理處理 | `rm` 只被呼叫一次；`cleaned` 不是真；訊息說逾時、可能只刪了一部分、可以再申請 | 自動：`test_station_clean_aws.py`（註解標 TC-082） |
| TC-083 | 作法 6；專長守則（回應不含密鑰、不露出內部路徑） | 例外 | 假 `rm`（及列舉失敗）的輸出很長，內含像金鑰的假字串與憑證檔路徑與本機路徑 | 站台代理處理 | 訊息裡不含那串金鑰、不含憑證檔路徑與本機路徑；引用的輸出經過清洗並不超過 300 字 | 自動：`test_station_clean_aws.py`（註解標 TC-083） |
| TC-084 | 失敗先行測試 13；作法 4；不做 | 不在範圍 | 讀 `clean.py` 的 AWS 分支與所有被記錄的指令 | 搜尋禁字 | 沒有 `delete-objects`、`delete-bucket`、`--versions`、`--include`、`--exclude`、`sync`、`boto3`；`rm` 之外沒有任何刪除指令；`rm` 的旗標只有 `--recursive` 與 `--region <區域>` | 自動：`test_station_clean_aws.py::test_forbidden_words_never_appear_in_clean_py` |
| TC-085 | 失敗先行測試 13 | 功能 | 本檔所有成功與失敗的情境 | 看每一次 `rm` 的目標 | 每一個都以 `s3://lab-bucket/` 開頭、以 `/work/` 結尾，且是這個 run 的 work 前綴（`…/runs/<run>/work/`）；沒有任何一次指到 bucket 本身、`runs/`、`results/`、`uploads/` 或別的 run | 自動：同 TC-084 |
| TC-086 | 作法 4；不做 | 不在範圍 | 假 bucket 有 work 前綴下的物件，也有 `work2/`、`work-keep`、`results/`、`runs/other/work/`、`uploads/alice/` 的物件；成功清理 | 清理完，看假 bucket 剩什麼 | 只有 `runs/r1/work/` 底下的物件被刪；其他鄰居物件一個都沒少；bucket 本身還在 | 自動：`test_station_clean_aws.py`（註解標 TC-086） |
| TC-087 | 作法 2、「只新增 AWS 的那一支」；不留空殼 | 功能 | 一個 AWS 的 `clean_work` 工作（有效確認），從代理處理 `clean_work` 的進入點（`handlers` 派工）送入 | 代理處理 | 走到 AWS 的清理並呼叫了列舉；結果不再是「AWS Batch 的清理尚未支援」 | 自動：`test_station_clean_aws.py`（註解標 TC-087） |
| TC-088 | 目標（Google、Slurm 不變） | 功能 | Google 的清理工作；Slurm 的清理工作 | 代理處理 | Google 仍只呼叫 `gcloud storage ls／rm`（指令與修改前相同）、沒有任何 `aws`；Slurm 仍走原來的那一條 | 自動：`test_station_clean_gcb.py` 與既有 Slurm 清理測試（不改斷言） |
| TC-089 | 作法 2、3 | 功能 | AWS 的清理工作，成功與各種拒絕情境 | 看所有被記錄的呼叫 | 沒有任何 `gcloud` 被呼叫 | 自動：`test_station_clean_aws.py`（註解標 TC-089） |
| TC-090 | 專長守則（回應不含密鑰） | 例外 | 憑證檔內容與父行程環境都放獨一無二的假金鑰字串；成功與失敗情境（TC-066 除外，它可含路徑） | 搜尋站台代理的每一個回報與例外訊息 | 找不到任何金鑰字串；成功回報的鍵只有 `ok`、`cleaned`、`run_name`、`message` | 自動：`test_station_clean_aws.py`（註解標 TC-090） |

## User Story 4 — 文件、既有斷言、邊界（優先度 P2）

E2 更新清單、E3 確切字串、裁決 5、完成標準。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-091 | E3 | 功能 | `docs/SEQERA_PARITY.md` | 讀 AWS 那一列 | 恰為 `\| AWS Batch (`awsbatch-platform`) \| Have (create + check + launch + cancel + upload + clean) \| [ ] \|`；第 84 行附近的 Pre-flight 說明沒有被改 | 自動：`test_aws_clean.py`（註解標 TC-091） |
| TC-092 | 裁決 5；不做（舊版本與刪除標記） | 不在範圍 | `docs/PLATFORM.md` | 讀清理那一節 | 有一句白話寫明「bucket 若開了版本控管，清理後舊版本仍佔空間、仍收費」；程式沒有處理舊版本（見 TC-084） | 自動：`test_aws_clean.py`（註解標 TC-092；只檢查該句存在） |
| TC-093 | 完成標準（真實刪除不屬完成標準）；E12 | 不在範圍 | `docs/TESTING.md` | 讀 AWS 清理的手動步驟 | 有寫明：真的刪 S3 資料與真實輸出格式的確認要維護者另外點頭、只對測試用的 bucket 與前綴；步驟具體到可照著做 | 手動：`docs/TESTING.md`（新增的 AWS 清理一節） |
| TC-094 | E2(a) | 功能 | `test_aws_upload.py` 的 130 行、`test_clean_work_still_refused_for_aws`（149–157）、`test_clean_work_of_an_aws_run_is_refused_by_the_agent_and_starts_nothing`（550）、754–756 | 讀這些測試 | 已改成：AWS 元組含 `clean_work`；AWS 的 `clean_work` 可排隊（或該測試被移除並由 TC-003 取代）；代理對 AWS 清理不再因類型被拒；`aws-clean` 字樣與 SEQERA 舊句換成 TC-091 的新句；清單以外的斷言一個字沒動 | 自動：`test_aws_upload.py` |
| TC-095 | E2(b) | 功能 | `test_aws_launch.py` 的 915–921（拒絕清單與 TC-108 那行）、932 附近、963–978、1225 | 讀這些測試 | `clean_work` 已從「必須被拒」的清單拿掉；`clean_work` 改成可排隊、`run_clean` 對 AWS 不再拒；SEQERA 句換成新句；清單以外的斷言一個字沒動 | 自動：`test_aws_launch.py` |
| TC-096 | E2(c)；E4 | 功能 | `test_aws_ce.py` 的 655–663、829–844、927 | 讀這些測試 | 拒絕清單只剩 `list_site_files`，訊息斷言是「尚未支援」且不得含 aws-upload／aws-clean 字樣；`clean_work` 不再因類型被拒；SEQERA 句換成新句；清單以外的斷言一個字沒動 | 自動：`test_aws_ce.py` |
| TC-097 | E2（Google 一個字都不准動） | 功能 | `test_station_clean_gcb.py`（含 159–160 行對 `ls`／`rm` 指令的斷言與 501 行禁字清單）、`test_cleanup_confirm.py`、`test_byte_channel_b.py:763` | 跑這三個檔；閱卷時以 `git diff <base>...HEAD` 比對 | 全綠，且三個檔與 base 完全相同（沒有被弱化、跳過、改期望值） | 自動：這三個檔 |
| TC-098 | 完成標準 | 功能 | 整個 `platform/tests` | 跑整個套件 | 全綠（已知環境紅燈 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 視同綠）；計畫 E2 清單以外若有既有斷言變紅，執行者回報 BLOCKED，不得自行改 | 自動：整個 `platform/tests` |
| TC-099 | 範圍（compute_envs.py）；既有掃描 | 例外 | `compute_envs.py` 的 AWS 元組 | 跑 `test_cleanup_store.py::test_nothing_writes_clean_work_or_work_cleaned_at`（TC-030） | 仍綠：`compute_envs.py` 沒有出現 `clean_work` 這個完整字樣（AWS 這格和 Google 一樣用 `"clean_" "work"` 兩段相鄰字面寫） | 自動：`test_cleanup_store.py`（既有，不改） |
| TC-100 | 範圍（新檔） | 功能 | 兩個新測試檔 `test_station_clean_aws.py`、`test_aws_clean.py` | 讀檔頭前 40 行 | 各有一行 `# Nothing existing: …`，至少 15 個字（既有的 TC-070 掃描通過） | 自動：既有的 TC-070 掃描 |
| TC-101 | 專長守則（migration）；不做（不重做 migration） | 不在範圍 | 資料結構（資料表與欄位） | 新建資料庫，比對資料表與欄位 | 與修改前完全相同（沒有新增或改動欄位；`work_cleaned_at` 是 cloud-cleanup 已有的欄位）；不需要 migration | 自動：`test_cleanup_store.py` 既有的資料表與欄位斷言（不改） |
| TC-102 | 不做（不改確認機制、網頁、MCP 工具） | 不在範圍 | 既有網頁、MCP 工具與確認機制測試 | 跑 `test_web_*`、MCP 工具清單與確認相關測試 | 全綠且斷言一個字沒動；沒有新增網頁入口、MCP 工具或確認類型（`web.py`、`web_board.py`、`static/*`、`cloud_store.py`、`datasets.py`、`put_upload.py` 不在這次的改動裡） | 自動：既有 `test_web_*`、MCP 工具測試、`test_cleanup_confirm.py` |
| TC-103 | 不做（排程式自動清理、生命週期規則）；作法 1 | 不在範圍 | `compute_envs.py` 與 `jobs.py` | 比對修改前後 | AWS 放行表與 base 相比只多 `clean_work` 一種；工作種類、期限表（`DEADLINE_SECONDS`）沒有新增或改動；沒有任何排程、自動確認或自動排入清理的程式 | 自動：`test_aws_clean.py`（註解標 TC-103） |

## 憲法與安全網

涉及：原則 I.2（本人的 yes，經由人能操作的管道）、原則 2（平台程式不提交、不刪東西；刪除只在站台代理的 `clean.py`）、原則 8（先讀來源再下結論）、專長守則（錯誤訊息、對等性）。Safety Net 的 hooks 不在這次改動範圍。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104 | I.2；專長守則（確認管道，未經確認不得改變資料） | 例外 | AWS 環境；`clean_work` 的待確認申請（狀態 pending，沒人按），或已被拒絕、已過期的申請 | 嘗試用它排入 `clean_work` | 全部被拒；工作表沒有新列；`work_cleaned_at` 沒變 | 自動：`test_aws_clean.py`（註解標 TC-104） |
| TC-105 | 原則 2；作法 8 | 例外 | `platform/abf_platform/` 與 `platform/abf_launch/` 全部 `.py`，以及 `abf_station/` 除 `clean.py` 以外的檔案 | 掃描 | 沒有 `rm` 刪除字樣（AWS 的 `rm` 只出現在 `clean.py`）、沒有 `subprocess`、沒有 "station" 字樣、沒有 `boto3`／`botocore`／`google`／`azure` 匯入（既有的 TC-061、TC-071、TC-083、TC-085、TC-114 掃描仍綠） | 自動：`test_scope.py`、`test_station_static.py`、`test_cleanup_store.py` 既有掃描（不改） |
| TC-106 | 原則 8（先讀來源）；裁決 1 | 功能 | `specs/aws-clean/ledger.md` | 讀進度帳本 | 記有 `aws s3 ls`／`s3 rm`／`s3api list-objects-v2` 官方頁面的網址與用到的旗標；計畫的指令形狀與官方不符處有一行紀錄；假 bucket 的輸出格式附官方網址 | 手動：閱卷時讀 ledger（不是 TESTING.md 的步驟） |
| TC-107 | 專長守則（錯誤訊息說明發生什麼事與該怎麼辦，不露出堆疊、內部路徑） | 例外 | TC-037～TC-083 中每一種拒絕與失敗的回報 | 檢查每一則訊息 | 每一則都有白話中文說明發生什麼事與下一步（例如「沒有刪任何東西」「可以再申請」「請先等它結束」）；不含 Traceback、SQL，也不含 `storage_root` 等內部路徑（TC-066 的憑證檔路徑除外） | 自動：`test_station_clean_aws.py`（註解標 TC-107） |
| TC-108 | 專長守則（對等性：使用者可見動作與動作層函式一一對應） | 功能 | 既有的對等性測試（同時列舉使用者可見的動作與動作層函式） | 跑該測試 | 全綠且清單沒有被改：本任務沒有新增任何使用者動作或動作層函式，`offer_cleanup`／`offer_cleanups` 既有 | 自動：既有對等性測試（不改） |
