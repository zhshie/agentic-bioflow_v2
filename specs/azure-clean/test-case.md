# 測試案例：Azure 跑完清理 Blob work 前綴（azure-clean，clean_work）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：本任務沒有 spec.md，以 `specs/azure-clean/plan.md`（含「維護者原話」、文末「裁決」1–8；與上文衝突時以裁決為準）為規格。
IDs: TC-001..TC-126。每條只測一件事；驗證方式「自動」＝ `platform/tests/test_azure_clean.py`（平台端，ID 前綴 AZC-PLT-）、`platform/tests/test_station_clean_azure.py`（站台代理端，ID 前綴 AZC-STN-），或計畫指定要更新的既有測試檔，並在測試內以註解 `# TC-nnn` 標明。
所有測試輸入都用假值：容器 `labcontainer`、子目錄 `work`、`westeurope`、儲存體帳戶 `azlab`、run 名稱 `r1`、擁有者 `alice`、`bob`；全部用假的 `site.run_fixed`（記錄每次呼叫的指令清單與環境變數），`tmp_path` 當 `storage_root`；不碰網路、不呼叫真的 `az`、不花錢。
假容器的內容含鄰居 blob：`work/runs/r1/work/…`（要清的）、`work/runs/r1/work2/…`、`work/runs/r1/work-keep`、`work/runs/r1/results/…`、`work/runs/other/work/…`、`work/uploads/alice/…`。假的 `delete-batch` 照 fnmatch 比對 pattern（`*` 會跨 `/`，與官方文件相同）。
憑證相關的鍵名與假金鑰在測試裡用字串相加組出，避免被 `tests/credentials_stay_in_settings_test.sh` 掃到。
呼叫數的寫法：站台代理在「檢查 run 資料夾、環境、work 路徑」這幾步就停的案例，`run_fixed` 的呼叫總數是 0；到了「查 head 程序」之後才停的案例，則是「沒有任何列舉、沒有任何刪除呼叫」，head 程序還活著時連 `az` 都沒有被呼叫。
-->

**規格**：`specs/azure-clean/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「尚未支援」而不是悄悄亂做。

名詞：**站台代理**＝裝在平台主機上、唯一會真的執行 `az` 指令的程式（平台本身不碰 Azure，也不刪任何東西）；**work 前綴**＝這個 run 在 Blob 容器上的暫存位置 `az://<container>/<sub>/runs/<run>/work/`（blob 名稱前綴是 `<sub>/runs/<run>/work/`）；**results**＝這個 run 的結果，在同一層的 `results/`，絕不能動；**放行表**＝`compute_envs.CLOUD_JOB_KINDS`，每一種雲端環境各自列出它肯接的工作種類；**內容包**＝平台寫給站台代理的清理申請（run 名稱、資料夾、環境快照、work 路徑等欄位）；**預檢**＝站台代理在動手前再做一次的唯讀檢查（憑證檔、`az`、儲存體等）；**前綴撞名**＝`work2/`、`work-keep` 這種名字開頭和 `work` 一樣、但不是 work 底下的東西；**fnmatch 萬用字元**＝`* ? [ ]`，`delete-batch` 的 `--pattern` 用它比對，`*` 會連 `/` 一起比對。

## User Story 1 — 平台端：放行、準備、提出、記錄（優先度 P1）

計畫目標：「一個在 Azure Batch 環境成功跑完的 run，平台提出『清理 work 目錄』的申請，本人在確認頁答 y 之後……刪完平台記下 `work_cleaned_at`，同一個 run 不會再被提出第二次。」本任務完成前，`clean_work` 對 Azure 一直是被拒的（azure-launch 的做法，維護者採納的 aws-launch 裁決 A3 之 Azure 對應）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；AZC-PLT-01 | 功能 | 目前的 `compute_envs.CLOUD_JOB_KINDS` | 讀 Azure 那一格 | 恰含 `preflight`、`launch_nextflow`、`cancel_run`、`pipeline_files`、`put_upload`、`clean_work` 六種（原有五種不少，只多 `clean_work`） | 自動：`test_azure_clean.py::test_clean_work_is_allowed_for_azure_and_still_for_google_and_aws` |
| TC-002 | AZC-PLT-01 | 功能 | 同上 | 讀 Google 那一格與 AWS 那一格 | 兩格都與修改前逐字相同（各六種，順序不變） | 自動：同上 |
| TC-003 | 作法 1 | 功能 | Azure 環境（代理在線）；有一筆已被本人確認的 `clean_work` 申請，run 為 alice 送出的 Azure run | alice 排入 `clean_work` 工作 | 工作排入，種類是 `clean_work`，指派給該環境的代理 | 自動：`test_azure_clean.py`（註解標 TC-003） |
| TC-004 | 作法 1（不要順手要求環境 available） | 功能 | 同 TC-003，但環境狀態不是 `available`（例如 `invalid`） | 排入 `clean_work`；同一環境再試 `put_upload` | `clean_work` 排入成功（與 Google、AWS 一致）；`put_upload` 仍因狀態不是 available 被拒 | 自動：`test_azure_clean.py`（註解標 TC-004） |
| TC-005 | 作法 2.1；憲法 I.2 | 例外 | Azure 環境；沒有任何確認（或確認尚未被本人按下） | 嘗試排入 `clean_work` | 被拒，說明需要本人的確認；沒有工作被排入 | 自動：`test_azure_clean.py`（註解標 TC-005） |
| TC-006 | 範圍（jobs.py 拿掉 `azure-clean` 字樣）；作法 1 | 例外 | Azure 環境；`list_site_files`（仍不在 Azure 放行表） | 嘗試排入 | 被拒，訊息含「尚未支援」；訊息**不含**「azure-clean」 | 自動：`test_azure_clean.py`（註解標 TC-006） |
| TC-007 | 範圍（jobs.py 只動 Azure 的拒絕訊息） | 功能 | Google 環境與 AWS 環境各一個不在其放行表的工作種類 | 嘗試排入 | 兩句被拒的訊息都與修改前逐字相同 | 自動：`test_azure_clean.py`（註解標 TC-007）＋既有 `test_aws_ce.py`／`test_gcb_ce.py` 斷言（不改） |
| TC-008 | 目標（與 Google、AWS 同一套核對，「逐項相同」） | 例外 | Azure 環境；`clean_work` 內容包的 `run_folder` 或 `slurm_job_id` 和平台的送出紀錄不同，或欄位多一個／少一個 | 嘗試排入 | 被拒，說內容與紀錄不一致、請重新申請；沒有工作被排入 | 自動：`test_azure_clean.py`（註解標 TC-008） |
| TC-009 | AZC-PLT-02 | 功能 | 平台記錄有一筆成功的 Azure run `r1`：環境 `workDir=az://labcontainer/work`，run 資料夾 `<storage_root>/_azure_runs/r1`，有工作編號，沒清過 | 呼叫 `prepare_clean` | 回傳的內容包 `work == "az://labcontainer/work/runs/r1/work"`（手算，無結尾斜線）；`run_folder` 是送出紀錄裡的那個；不會被「必須在 workDir/runs 底下」那條擋掉 | 自動：`test_azure_clean.py::test_prepare_clean_accepts_a_succeeded_azure_run` |
| TC-010 | 範圍（build.py `clean_work_path`） | 功能 | 三種環境快照：Google（`gs://lab-bucket/work`）、Slurm、Azure（`az://labcontainer/work`） | 呼叫 `clean_work_path` | Google 與 Slurm 的結果與修改前逐字相同；Azure 回 `az://labcontainer/work/runs/r1/work` | 自動：`test_azure_clean.py`（註解標 TC-010） |
| TC-011 | AZC-PLT-03 | 例外 | 同 TC-009，但環境的 `workDir` 在 run 送出之後被改過 | 呼叫 `prepare_clean` | 被拒並說明（環境在 run 送出之後改過、無法確認路徑）；沒有內容包 | 自動：`test_azure_clean.py::test_prepare_clean_refuses_when_the_environment_changed_after_the_run` |
| TC-012 | AZC-PLT-04 | 例外 | 同 TC-009，但這個 run 的 `work_cleaned_at` 已有值 | 呼叫 `prepare_clean` | 被拒，說 work 目錄已經清過了 | 自動：`test_azure_clean.py::test_prepare_clean_refuses_an_already_cleaned_run` |
| TC-013 | 範圍（build.py 只放寬 Google、AWS、Azure 三種） | 例外 | 一個 Slurm run，其 `run_folder` 的上一層不是 `<workDir>/runs` | 呼叫 `prepare_clean` | 仍被拒（Slurm 的規則沒有被放寬） | 自動：`test_azure_clean.py`（註解標 TC-013） |
| TC-014 | 專長守則（跨使用者，讀） | 例外 | alice 送出的 Azure run `r1`；bob 是另一位使用者 | 以 bob 的身分呼叫 `prepare_clean(…, owner=bob)` | 被拒，說法與「run 不存在」相同，不洩漏 alice 的 run | 自動：`test_azure_clean.py`（註解標 TC-014） |
| TC-015 | 專長守則（跨使用者，寫） | 例外 | 同 TC-014；bob 自己有一筆已確認的 `clean_work` 申請，內容指向 alice 的 `r1` | bob 嘗試排入 `clean_work` | 被拒；沒有工作被排入 | 自動：`test_azure_clean.py`（註解標 TC-015） |
| TC-016 | AZC-PLT-05；作法 7 | 功能 | 一個成功的 Azure run（索引裡狀態 `succeeded`），有擁有者 alice，沒清過 | 呼叫 `offer_cleanup` | 為 alice 建立一筆待確認的 `clean_work` 申請，內容是 TC-009 的內容包 | 自動：`test_azure_clean.py::test_offer_cleanup_offers_for_a_succeeded_azure_run` |
| TC-017 | AZC-PLT-05；裁決 7（run 成功才提出） | 例外 | 失敗的 Azure run；取消的 Azure run | 各呼叫一次 `offer_cleanup` | 都不提出，理由寫明只有成功的 run 才提出清理；沒有建立任何申請 | 自動：同上 |
| TC-018 | 作法 7（`offer_cleanups` 指令不改） | 功能 | 兩個 Azure run：一個成功、一個失敗 | 呼叫 `offer_cleanups` | `offered` 為 1、`skipped` 為 1；成功的那個被提出 | 自動：`test_azure_clean.py`（註解標 TC-018） |
| TC-019 | 目標（提出只是申請）；作法 2.1 | 例外 | 同 TC-016 | 呼叫 `offer_cleanup` 之後看資料庫與假的 `az` | 確認列狀態是「待確認」；工作表沒有新增任何一列；沒有任何 `az` 呼叫 | 自動：`test_azure_clean.py`（註解標 TC-019） |
| TC-020 | AZC-PLT-07；作法 5 | 功能 | 一個 Azure `clean_work` 工作；代理回報 `("done", {ok: True, cleaned: True, run_name, message})` | 平台收下結果 | 該 run 的 `work_cleaned_at` 被寫入 | 自動：`test_azure_clean.py::test_work_cleaned_at_is_written_only_when_cleaned_is_true` |
| TC-021 | AZC-PLT-07；作法 5 | 例外 | 同 TC-020，但回報 `cleaned: False`、或沒有 `cleaned`、或 `ok: False`、或狀態是 error／refused | 平台收下結果 | `work_cleaned_at` 不寫入 | 自動：同上 |
| TC-022 | 目標（同一個 run 不會再被提出第二次） | 功能 | TC-020 之後 | 再呼叫 `offer_cleanup` 與 `prepare_clean` | 都不提出／被拒，說已經清過了 | 自動：`test_azure_clean.py`（註解標 TC-022） |
| TC-023 | AZC-PLT-08 | 功能 | Azure 環境；既有的 `launch_nextflow`、`cancel_run`、`put_upload` 申請 | 排入工作 | 結果（排入或被拒、訊息）與修改前（azure-upload 合併後）完全相同 | 自動：`test_azure_clean.py::test_clean_work_for_azure_leaves_launch_cancel_and_upload_unchanged` |

## User Story 2 — 本人看到的確認畫面（優先度 P1）

計畫失敗先行測試 AZC-PLT-06：畫面寫明刪的是哪個前綴、什麼不會動、刪了無法復原、軟刪除／版本控制的提醒；沒有金額；Google、AWS 畫面一字不變。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | AZC-PLT-06；範圍（clean_screen） | 功能 | TC-009 的 Azure 內容包（`work = az://labcontainer/work/runs/r1/work`） | 呼叫 `clean_screen` | 畫面印出 `az://labcontainer/work/runs/r1/work/`（帶結尾斜線）和 run 名稱 `r1` | 自動：`test_azure_clean.py::test_the_clean_screen_says_what_is_deleted_and_what_is_kept_in_plain_words` |
| TC-025 | AZC-PLT-06 | 功能 | 同上 | 看畫面 | 寫明 `results` 不會動 | 自動：同上 |
| TC-026 | AZC-PLT-06 | 功能 | 同上 | 看畫面 | 寫明這是「永久刪除」 | 自動：同上 |
| TC-027 | AZC-PLT-06；範圍（新常數 `CLEAN_AZ`）；裁決 4 | 功能 | 同上 | 看畫面 | 有一句 Azure 專屬說明：刪的是 Blob 容器裡這個前綴下的物件、只有這一個前綴、容器裡其他資料夾與檔案不會被動；另有一句：儲存體帳戶若開了軟刪除或版本控制，舊版本與已刪項目在保留期內仍佔空間 | 自動：同上 |
| TC-028 | AZC-PLT-06；不做（費用估算） | 例外 | 同上 | 搜尋畫面全文 | 沒有金額、貨幣符號、「台幣」「NT$」「USD」之類的換算 | 自動：同上 |
| TC-029 | 範圍（Azure 畫面不沿用只對 Google 成立的說法） | 例外 | 同上 | 搜尋畫面全文 | 沒有「gcloud」、Google 的「7 天」軟刪除說法 | 自動：同上 |
| TC-030 | AZC-PLT-06（Google 畫面一字不變） | 功能 | Google 的內容包 | 呼叫 `clean_screen` | 每一行與修改前逐字相同 | 自動：`test_cleanup_confirm.py` 既有斷言（不改）＋`test_azure_clean.py` 同名檢查 |
| TC-031 | AZC-PLT-06（AWS、Slurm 畫面一字不變） | 功能 | AWS 的內容包；Slurm 的內容包 | 呼叫 `clean_screen` | 每一行與修改前逐字相同 | 自動：`test_aws_clean.py` 既有斷言（不改）＋`test_azure_clean.py` 同名檢查 |

## User Story 3 — 站台代理的護欄、列舉、只刪一次（優先度 P1）

計畫作法 2、3、4、5、6 與失敗先行測試 AZC-STN-01..18；維護者的派工指示：「刪雲端資料只限該 run 的 work 前綴，確認與護欄要和 gcs 清理相同，絕不刪前綴之外。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | AZC-STN-01；作法 3 | 功能 | 合法的 Azure 清理（有效確認、內容包欄位齊全、`workDir=az://labcontainer/work`、`westeurope`、儲存體帳戶 `azlab`、run 資料夾 `<storage_root>/_azure_runs/r1`、`head.pid` 的程序已不在、預檢全通過）；假容器內有 `work/runs/r1/work/…` 與鄰居 | 站台代理處理 | `run_fixed` 的呼叫恰為兩次：先一次唯讀列舉、再一次 `delete-batch`（順序固定） | 自動：`test_station_clean_azure.py::test_clean_azure_lists_then_deletes_exactly_one_prefix` |
| TC-033 | AZC-STN-01；作法 3 | 功能 | 同 TC-032（帳號金鑰憑證） | 看 `delete-batch` 那次的指令 | 是清單（不是 shell 文字），恰為 `["az","storage","blob","delete-batch","--source","labcontainer","--pattern","work/runs/r1/work/*","--auth-mode","key"]`（旗標順序以實作為準，集合恰為這五個）：pattern 是「整段前綴＋`/*`」；沒有 `--dryrun`、`--delete-snapshots`、`--if-*`、`--account-key`、`--sas-token` | 自動：同上 |
| TC-034 | 作法 3 | 功能 | 同 TC-032 | 看列舉那次的指令 | 是 `az storage blob list`，`--container-name labcontainer`、`--prefix work/runs/r1/work/`（前綴**以 `/` 結尾**）、`--query "[].name"`、`--output tsv`、`--auth-mode key`、`--num-results "*"`；不含任何刪除或寫入字眼；在 `delete-batch` 之前 | 自動：`test_station_clean_azure.py`（註解標 TC-034） |
| TC-035 | 作法 5 | 功能 | 同 TC-032 | 看代理的回報 | 狀態 `done`；鍵恰為 `ok`、`cleaned`、`run_name`、`message`；`ok` 與 `cleaned` 都是真；`run_name` 是 `r1`；訊息白話說已刪除容器裡該前綴（`az://labcontainer/work/runs/r1/work` 或其 blob 前綴）底下的物件、`results` 沒有動 | 自動：`test_station_clean_azure.py`（註解標 TC-035） |
| TC-036 | 裁決 6 | 功能 | 同 TC-032，但憑證只有 SAS 權杖（沒有帳號金鑰） | 看列舉與 `delete-batch` 的指令與環境 | 兩個指令都**不帶** `--auth-mode`（其餘旗標與 TC-033、TC-034 相同）；SAS 權杖只經環境變數 `AZURE_STORAGE_SAS_TOKEN`；argv 裡沒有權杖 | 自動：`test_station_clean_azure.py`（註解標 TC-036） |
| TC-037 | AZC-STN-09 | 功能 | 同 TC-032，`workDir=az://labcontainer/work`；假容器的鍵是 `work/runs/r1/work/…` | 看 pattern 與前綴核對 | pattern 與列舉的 `--prefix` 都含 `work/runs/r1/work`，不是 `runs/r1/work`（Azure 的 workDir 一定有子目錄，沒有裸容器案例） | 自動：`test_station_clean_azure.py::test_workdir_subfolder_is_kept_in_the_prefix` |
| TC-038 | AZC-STN-02；作法 2.1 | 例外 | 沒有有效確認（沒有本人答 y） | 站台代理處理 | 拒絕；`run_fixed` 呼叫數 0（`az` 一次都沒呼叫） | 自動：`test_station_clean_azure.py::test_unconfirmed_clean_is_refused_and_az_is_never_called` |
| TC-039 | AZC-STN-03 | 例外 | 確認的類型是 `launch`（不是 `clean_work`） | 站台代理處理 | 拒絕；呼叫數 0 | 自動：`test_station_clean_azure.py::test_expired_or_wrong_type_confirmation_is_refused` |
| TC-040 | AZC-STN-03 | 例外 | 確認已超過期限 | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-041 | 作法 2.1（確認與 Google、AWS 逐項相同） | 例外 | 確認有效，但內容包在確認之後被改過 | 站台代理處理 | 拒絕；呼叫數 0 | 自動：`test_station_clean_azure.py`（註解標 TC-041） |
| TC-042 | 作法 2.2（KEYS 檢查） | 例外 | 內容包多一個欄位，或少一個欄位 | 站台代理處理 | 拒絕，說欄位不對；呼叫數 0 | 自動：`test_station_clean_azure.py`（註解標 TC-042） |
| TC-043 | 作法 2.2（agent 檢查） | 例外 | 內容包的 `agent` 不是這個代理的名字 | 站台代理處理 | 拒絕，說這個清理是給另一個代理的；呼叫數 0 | 自動：`test_station_clean_azure.py`（註解標 TC-043） |
| TC-044 | 作法 2.2（run 名稱正規式） | 例外 | run 名稱不符平台給的格式（例如大寫、含 `/`、空字串、超過長度上限） | 站台代理處理 | 拒絕，說 run 名稱不對；呼叫數 0 | 自動：`test_station_clean_azure.py`（註解標 TC-044） |
| TC-045 | 作法 2.2（`slurm_job_id`／`pid` 範圍） | 例外 | `slurm_job_id` 是 `true`、文字 `"5"`、0、負數，或超過 2^31-1 | 站台代理處理 | 拒絕，說編號必須是一個十進位數字；呼叫數 0 | 自動：`test_station_clean_azure.py`（註解標 TC-045） |
| TC-046 | AZC-STN-12；作法 2.3 | 例外 | 內容包的 `run_folder` 不是 `<storage_root>/_azure_runs/r1`（例如 `_gcb_runs/r1`、`_aws_runs/r1`、別的 run 的資料夾、`storage_root` 之外） | 站台代理處理 | 拒絕，說專屬資料夾不是這台主機上這個 run 的那一個；呼叫數 0 | 自動：`test_station_clean_azure.py::test_run_folder_must_be_the_azure_runs_folder` |
| TC-047 | 作法 2.3 | 例外 | 部署設定沒有 `storage_root` | 站台代理處理 | 拒絕，說沒有 storage_root；呼叫數 0 | 自動：`test_station_clean_azure.py`（註解標 TC-047） |
| TC-048 | AZC-STN-14；作法 2.4 | 例外 | 內容包裡環境的 `workDir` 不是 `az://` 開頭 | 站台代理處理 | 拒絕並說環境設定不合規則；呼叫數 0 | 自動：`test_station_clean_azure.py::test_environment_is_judged_again_and_a_bad_container_is_refused` |
| TC-049 | AZC-STN-14；作法 2.4 | 例外 | 容器名稱不合規則：含大寫、含 `--`、過短（各一例） | 站台代理處理 | 每一例都拒絕；呼叫數 0 | 自動：同上 |
| TC-050 | AZC-STN-14；作法 2.4 | 例外 | `workDir` 子目錄含 `..` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-051 | AZC-STN-08；作法 2.5 | 例外 | 內容包的 `work` 被改成 `az://labcontainer/work/runs/r1`（少了 work） | 站台代理處理 | 拒絕，說路徑不是這個平台給這個 run 的；呼叫數 0 | 自動：`test_station_clean_azure.py::test_work_path_is_recomputed_and_must_match_the_bundle` |
| TC-052 | AZC-STN-08 | 例外 | `work` 被改成 `az://labcontainer/work/runs/r1/results/` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-053 | AZC-STN-08 | 例外 | `work` 被改成 `az://labcontainer/work/runs/r1/work/../results/` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-054 | AZC-STN-08；作法 2.6（容器與 workDir 的容器相同） | 例外 | `work` 被改成另一個容器：`az://other-container/work/runs/r1/work` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-055 | AZC-STN-10；作法 2.6 | 例外 | 環境 `workDir=az://labcontainer/rawdata`，內容包的 `work` 與代理算出的一致（所以只有「路徑段」這道護欄能擋） | 站台代理處理 | 拒絕，說路徑含 rawdata、results、analysis 或 ..；呼叫數 0 | 自動：`test_station_clean_azure.py::test_barred_segments_and_empty_segments_are_refused` |
| TC-056 | AZC-STN-10 | 例外 | 同 TC-055，`workDir=az://labcontainer/results` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-057 | AZC-STN-10 | 例外 | 同 TC-055，`workDir=az://labcontainer/analysis` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-058 | AZC-STN-10 | 例外 | 同 TC-055，路徑段為 `..` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-059 | AZC-STN-10 | 例外 | 同 TC-055，路徑段為 `.` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-060 | AZC-STN-10 | 例外 | 同 TC-055，路徑含空段（`az://labcontainer//x`） | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-061 | AZC-STN-11；作法 2.6（fnmatch） | 例外 | `workDir` 子目錄含 `*`（例如 `az://labcontainer/a*b`）；內容包與代理算出的一致 | 站台代理處理 | 拒絕，說含萬用字元；呼叫數 0 | 自動：`test_station_clean_azure.py::test_glob_characters_in_the_subfolder_are_refused` |
| TC-062 | AZC-STN-11 | 例外 | 子目錄含 `?` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-063 | AZC-STN-11 | 例外 | 子目錄含 `[` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-064 | AZC-STN-11 | 例外 | 子目錄含 `]` | 站台代理處理 | 拒絕；呼叫數 0 | 自動：同上 |
| TC-065 | 作法 2.6（run 名稱不得含萬用字元） | 例外 | 直接餵內容包，run 名稱含 `*` 或 `?`（路徑與 `work` 同步改成一致） | 站台代理處理 | 拒絕；呼叫數 0 | 自動：`test_station_clean_azure.py`（註解標 TC-065） |
| TC-066 | AZC-STN-04；作法 2.7 | 例外 | `head.pid` 記的編號等於內容包的，且 `ps` 顯示那個程序還活著、指令列帶 `-name r1` | 站台代理處理 | 拒絕，白話說主控程序還在跑、先等它結束或取消；沒有任何列舉或刪除呼叫，也沒有任何 `az` 呼叫 | 自動：`test_station_clean_azure.py::test_a_running_head_is_refused_and_az_is_not_called` |
| TC-067 | 作法 2.7（重用 `_head_gone`） | 例外 | `head.pid` 不存在、或內容不是純數字 | 站台代理處理 | 拒絕，說無法確認主控程序已結束、保守起見不刪；沒有任何 `az` 呼叫 | 自動：`test_station_clean_azure.py`（註解標 TC-067） |
| TC-068 | 作法 2.7 | 例外 | `head.pid` 記的編號和內容包的 `slurm_job_id` 不同 | 站台代理處理 | 拒絕；沒有任何 `az` 呼叫 | 自動：`test_station_clean_azure.py`（註解標 TC-068） |
| TC-069 | 作法 2.7（沒有名為這個 run 的 nextflow 還在跑才放行） | 功能 | `head.pid` 的編號現在被另一個程式佔用（`ps` 回一行，指令列不帶 `-name r1`），其餘條件合法 | 站台代理處理 | 視為主控程序已結束，照 TC-032 的兩次呼叫完成 | 自動：`test_station_clean_azure.py`（註解標 TC-069） |
| TC-070 | 作法 2.7（重用 `_head_gone`） | 例外 | 查程序的 `ps` 逾時 | 站台代理處理 | 結果是 error，說查詢逾時、沒有刪任何東西、也不重試；沒有任何 `az` 呼叫 | 自動：`test_station_clean_azure.py`（註解標 TC-070） |
| TC-071 | AZC-STN-17；作法 2.8 | 例外 | 憑證檔（`ABF_STATION_AZURE_CREDENTIALS` 指的檔案）不存在，其餘合法 | 站台代理處理 | 失敗，白話說預檢未通過、找不到憑證檔；呼叫數 0；訊息不含金鑰值 | 自動：`test_station_clean_azure.py::test_a_missing_credentials_file_or_missing_az_fails_safely` |
| TC-072 | AZC-STN-17；作法 2.8 | 例外 | `az` 不在 PATH 上 | 站台代理處理 | 失敗，白話說找不到 `az`；呼叫數 0；訊息不含金鑰值 | 自動：同上 |
| TC-073 | 作法 2.8 | 例外 | 憑證檔在，但唯讀預檢有一項（非憑證名稱那項）不是 pass | 站台代理處理 | 拒絕，說預檢未通過並列出哪一項；沒有列舉、沒有刪除呼叫 | 自動：`test_station_clean_azure.py`（註解標 TC-073） |
| TC-074 | AZC-STN-15；作法 3（憑證只走環境變數） | 功能 | 同 TC-032，憑證檔路徑指到 `tmp_path` 下的假檔 | 看列舉與 `delete-batch` 兩次呼叫的環境變數 | 兩次的環境都由 `_az_env` 放入：`AZURE_STORAGE_ACCOUNT`＝`azlab`、`AZURE_STORAGE_KEY`（或 SAS）、`AZURE_CONFIG_DIR`、`AZURE_CORE_*`；沒有別的 `AZURE_*` | 自動：`test_station_clean_azure.py::test_az_env_has_only_the_allowed_azure_keys` |
| TC-075 | AZC-STN-15 | 例外 | 同 TC-074；測試先在父行程塞假的 `ABF_X=假值` 與另一個 `AZURE_*` | 看兩次呼叫的環境變數 | 這些父行程的變數都不在其中 | 自動：同上 |
| TC-076 | AZC-STN-15；作法 3 | 例外 | 憑證檔內的假金鑰（鍵名與值以字串相加組出） | 搜尋所有被記錄呼叫的 argv，以及代理所有回報與例外訊息 | 假金鑰的值不出現在任何 argv，也不出現在任何結果訊息 | 自動：同上 |
| TC-077 | 作法 3（沒有 shell） | 功能 | 同 TC-032 | 看所有被記錄的呼叫 | 每一次的指令都是清單（不是字串）；呼叫是經由固定指令執行器 `site.run_fixed`（沒有 shell） | 自動：`test_station_clean_azure.py`（註解標 TC-077） |
| TC-078 | AZC-STN-05；作法 3 | 例外 | 其餘合法，但列舉結果混入 `work/runs/r1/work2/x` | 站台代理處理 | 整個拒絕，白話說列出的物件不全在 work 底下（前綴撞名）；`delete-batch` 沒被呼叫；`cleaned` 不是真 | 自動：`test_station_clean_azure.py::test_listing_with_a_neighbour_prefix_aborts_before_delete` |
| TC-079 | AZC-STN-05 | 例外 | 列舉結果混入 `work/runs/other/work/x` | 站台代理處理 | 整個拒絕；`delete-batch` 沒被呼叫 | 自動：同上 |
| TC-080 | 作法 3（前綴撞名 `work-keep`） | 例外 | 列舉結果混入 `work/runs/r1/work-keep` | 站台代理處理 | 整個拒絕；`delete-batch` 沒被呼叫 | 自動：同上 |
| TC-081 | 作法 4（results 絕不刪） | 例外 | 列舉結果混入 `work/runs/r1/results/x` | 站台代理處理 | 整個拒絕；`delete-batch` 沒被呼叫 | 自動：同上 |
| TC-082 | 裁決 5（階層式命名空間，寧可誤拒） | 例外 | 列舉結果包含名稱恰為 `work/runs/r1/work`（無結尾斜線的目錄物件）的一列 | 站台代理處理 | 整個拒絕，訊息白話說明；`delete-batch` 沒被呼叫 | 自動：`test_station_clean_azure.py`（註解標 TC-082） |
| TC-083 | AZC-STN-06；裁決 2 | 例外 | 列舉輸出超過 1000 行（例如 1500 行），前面都合法，鄰居鍵出現在第 1001 行以後 | 站台代理處理 | 整個拒絕；`delete-batch` 沒被呼叫（不能只看第一頁就放行；不假設分頁頁數） | 自動：`test_station_clean_azure.py::test_a_neighbour_that_appears_late_in_a_long_listing_aborts` |
| TC-084 | AZC-STN-09 | 例外 | `workDir=az://labcontainer/work`；列舉混入 `work/runs/r1/work2/x`；另一案混入 `runs/r1/work/x`（少了 workDir 的子目錄） | 站台代理處理 | 兩案都整個拒絕；`delete-batch` 沒被呼叫（前綴核對含子目錄） | 自動：`test_station_clean_azure.py::test_workdir_subfolder_is_kept_in_the_prefix` |
| TC-085 | AZC-STN-07；作法 3 | 功能 | 列舉輸出為空（rc 0、沒有任何名稱） | 站台代理處理 | `cleaned: True`、`ok: True`；訊息白話說「那裡本來就沒有東西」；沒有 `delete-batch` 呼叫 | 自動：`test_station_clean_azure.py::test_empty_listing_is_a_plain_success_without_delete` |
| TC-086 | 作法 3（通過後才刪）；結構對照 `_clean_aws` | 例外 | 列舉本身失敗（結束碼非 0） | 站台代理處理 | 狀態 error，`cleaned` 不是真，訊息說列出失敗、沒有刪任何東西、可以再申請；沒有 `delete-batch` | 自動：`test_station_clean_azure.py`（註解標 TC-086） |
| TC-087 | 作法 3 | 例外 | 列舉逾時 | 站台代理處理 | `cleaned` 不是真，訊息說逾時、沒有刪任何東西、稍後可再申請；沒有 `delete-batch` | 自動：`test_station_clean_azure.py`（註解標 TC-087） |
| TC-088 | AZC-STN-16；作法 3（不重試） | 例外 | 其餘合法，假 `delete-batch` 回非零 | 站台代理處理 | `delete-batch` 只被呼叫一次（不重試）；`cleaned` 非真；訊息白話說刪除沒有成功、可能只刪了一部分、可以再申請，不含完整輸出與金鑰 | 自動：`test_station_clean_azure.py::test_a_failed_delete_is_not_retried_and_cleaned_is_false` |
| TC-089 | 作法 3（不重試） | 例外 | 假 `delete-batch` 逾時 | 站台代理處理 | 只呼叫一次；`cleaned` 非真；訊息說逾時、可能只刪了一部分、可以再申請 | 自動：`test_station_clean_azure.py`（註解標 TC-089） |
| TC-090 | 作法 6；專長守則（回應不含密鑰、不露出內部路徑） | 例外 | 假 `az`（列舉失敗與刪除失敗）輸出很長，內含像金鑰的假字串、憑證檔路徑、本機路徑，以及 `ABF_`／`AZURE_` 環境變數的值 | 站台代理處理 | 訊息裡不含那串金鑰、憑證檔路徑、本機路徑、那些環境變數的值，也不是完整輸出 | 自動：`test_station_clean_azure.py`（註解標 TC-090） |
| TC-091 | 作法 6（截 300 字） | 例外 | 同 TC-090 | 看訊息中引用 `az` 輸出的部分 | 引用的輸出不超過 300 字 | 自動：`test_station_clean_azure.py`（註解標 TC-091） |
| TC-092 | 作法 4；不做 | 功能 | 假容器有 `work/runs/r1/work/` 底下的物件，也有 `work2/`、`work-keep`、`results/`、`other/work/`、`uploads/`、`runs/other/` 的物件；假 `delete-batch` 照 fnmatch 比對 pattern（`*` 跨 `/`）；成功清理 | 清理完，看假容器剩什麼 | 只有 `work/runs/r1/work/` 底下的物件不見了；所有鄰居物件、`results/`、`uploads/`、其他 run 都還在 | 自動：`test_station_clean_azure.py`（註解標 TC-092） |
| TC-093 | 作法 2；不留空殼 | 功能 | 一個 Azure 的 `clean_work` 工作（有效確認），從代理處理 `clean_work` 的進入點（`handlers` 派工）送入 | 代理處理 | 走到 Azure 的清理並呼叫了列舉與 `delete-batch`（Azure 分支從 `run_clean` 真的接得到，不是只有直接呼叫 `_clean_azure` 才通） | 自動：`test_station_clean_azure.py`（註解標 TC-093） |
| TC-094 | AZC-STN-18 | 功能 | 同一組假世界下 Google 的清理工作與 Slurm 的清理工作 | 代理處理 | `_clean_gcb` 的指令與結果、Slurm 的路徑與修改前相同（只驗不變，不改它們的測試） | 自動：`test_station_clean_azure.py::test_google_and_aws_clean_paths_are_unchanged` |
| TC-095 | AZC-STN-18 | 功能 | 同一組假世界下 AWS 的清理工作 | 代理處理 | `_clean_aws` 的指令（`aws s3 ls`／`rm`）與結果與修改前相同 | 自動：同上 |
| TC-096 | 作法 2、3 | 例外 | Azure 清理的成功與各種拒絕情境；以及 Google、AWS 的清理 | 看所有被記錄的呼叫 | Azure 的清理沒有任何 `gcloud` 或 `aws` 呼叫；Google、AWS 的清理沒有任何 `az` 呼叫 | 自動：`test_station_clean_azure.py`（註解標 TC-096） |
| TC-097 | AZC-STN-13；作法 4；不做 | 不在範圍 | 讀 `clean.py` 的 Azure 段（`# ---- Azure Batch (azure-clean) ---` 標記起到 AWS 標記前） | 搜尋禁字 | 不含 `--delete-snapshots`、`--dryrun`、`container delete`、`storage remove`、`azcopy`、`az batch`、`--if-`、`--sas-token`、`--account-key`、`sync`、`s3api`、`boto3` | 自動：`test_station_clean_azure.py::test_forbidden_words_never_appear_in_clean_py` |
| TC-098 | AZC-STN-13 | 不在範圍 | 同上 | 數 `delete-batch` 與看迴圈 | `delete-batch` 在 Azure 段恰出現一次；沒有 `run_fixed` 在 For／While 裡（一個 run 最多一次刪除呼叫） | 自動：同上 |
| TC-099 | 範圍（站台程式碼禁小寫 `azure`、禁 `import azure`） | 不在範圍 | `abf_station/` 全部 `.py` | 掃描 | 沒有小寫單字 `azure`（含註解；`Azure`、`az://`、`az storage blob` 可以）；沒有 `import azure`；沒有 Azure SDK | 自動：既有 `test_station_static.py:46` 與既有靜態掃描＋`test_station_clean_azure.py`（註解標 TC-099） |
| TC-100 | 範圍（位置硬規定） | 不在範圍 | `clean.py` | 找兩個標記的位置 | `# ---- Azure Batch (azure-clean) ---` 在 `# ---- AWS Batch (aws-clean) ---` 之前；AWS 標記之後到檔尾沒有 Azure 的程式；既有的 `test_station_clean_aws.py` TC-084 掃描（不改）仍綠 | 自動：`test_station_clean_azure.py`（註解標 TC-100）＋既有 `test_station_clean_aws.py` |
| TC-101 | 範圍（`test_station_clean.py:588` 既有 TC-073 的更新） | 功能 | 既有的 `test_station_clean.py` TC-073（誰可以呼叫 `ctx.site.call(`） | 看該斷言與跑該檔 | 集合改為 `{"_clean_gcb","_clean_aws","_clean_azure","_head_gone"}`，只加 `_clean_azure` 這一個名字；`ctx.site.call(` 仍恰一次；`rm -rf` 只在 `clean.py` 的掃描仍綠 | 自動：`test_station_clean.py` |

## User Story 4 — 文件、既有斷言、邊界（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-102 | AZC-PLT-10；範圍（SEQERA_PARITY） | 功能 | `docs/SEQERA_PARITY.md` | 讀 Azure 那一列 | 該列的狀態欄恰為 `Have (create + check + launch + cancel + upload + clean)`，列尾仍是 `[ ] |`；不再含 `clean in azure-clean` | 自動：`test_azure_clean.py::test_docs_say_azure_can_clean_now` |
| TC-103 | 範圍（SEQERA_PARITY 第 84 行與 AWS 句不動） | 不在範圍 | `docs/SEQERA_PARITY.md` | 讀 Pre-flight 句與 `test_aws_clean.py:359-366` 釘的「for AWS Batch the same agent runs them…」句 | 兩處與修改前逐字相同 | 自動：既有 `test_aws_clean.py`（不改） |
| TC-104 | AZC-PLT-10；範圍（PLATFORM 型別表） | 功能 | `docs/PLATFORM.md` | 讀 `azbatch-platform` 那一列 | 說明 Azure 現在也能清理（例如 "checked, launched and cleaned on the platform host (resume: not yet)" 之類），不再把 clean 列在「not yet」；仍寫 resume 尚未支援 | 自動：`test_azure_clean.py::test_docs_say_azure_can_clean_now` |
| TC-105 | 範圍（PLATFORM「Cleaning a finished run's work folder」節） | 功能 | `docs/PLATFORM.md` | 讀該節 | 補了 Azure 一句：work 位於 `az://<container>/<sub>/runs/<run>/work`；容器若開了軟刪除或版本控制，舊版本與已刪項目在保留期內仍佔空間；Google、AWS 既有句一字不動 | 自動：`test_azure_clean.py::test_docs_say_azure_can_clean_now` |
| TC-106 | AZC-PLT-10（文件說 Azure 現在能清） | 例外 | `docs/PLATFORM.md` 的 Azure 小節（現行第 427 行「a clean … refused」、第 504 行「Not yet」） | 讀這兩處 | 不再說 Azure 的 clean 被拒或「not yet」；說的 resume、relaunch、費用估算、列檔等「尚未支援」仍在 | 自動：`test_azure_clean.py::test_docs_say_azure_can_clean_now` |
| TC-107 | 完成標準；範圍（TESTING.md） | 功能 | `docs/TESTING.md` | 讀新節 "Cleaning an Azure Batch work folder (azure-clean): the maintainer checks by hand" | 節存在；寫明只對**測試用**容器與前綴做一次真實清理、先 `az storage blob list --prefix …` 確認、答 y 後再 list 確認只有該前綴消失；要記下 `delete-batch` 真實輸出格式與失敗結束碼、`list --num-results "*"` 對大量 blob 的行為；另有在開了軟刪除／版本控制的帳戶上觀察刪除後舊版本的步驟；真實憑證、容器、費用由維護者決定 | 手動：`docs/TESTING.md`（該新節） |
| TC-108 | 必須更新的既有斷言(a)：`test_azure_ce.py` | 功能 | `test_azure_ce.py`（「各 job 種類對 Azure 被拒」迴圈、`test_no_new_write_path_for_azure`、`"azure-launch" in msgs["launch"]`／`"azure-clean" in msgs["launch"]`、PLATFORM／SEQERA 逐字斷言） | 讀 diff 與跑該檔 | `clean_work` 已移出「被拒」清單；沒有要求訊息含 `azure-clean`；文件逐字斷言改成新字串；該檔全綠；改動只限計畫清單（找不到原句者在帳本記一行） | 自動：`test_azure_ce.py`；驗收者以 `git diff` 對照計畫清單 |
| TC-109 | 必須更新的既有斷言(a)：`test_azure_launch.py` | 功能 | `test_azure_launch.py` 的 AZL-GATE-01、AZL-GATE-03、AZL-GATE-05、AZL-DOC-01、AZL-DOC-02 及其他提到 `azure-clean` 的斷言 | 讀 diff 與跑該檔 | GATE-01 改成 `clean_work` 對 Azure 可排隊；GATE-03 改成含 `clean_work` 的六個值；GATE-05 兩邊都已不成立，移除或由 AZC-PLT-01、AZC-STN-01 取代；DOC-01、DOC-02 改成新句；其餘斷言不動；該檔全綠 | 自動：`test_azure_launch.py`；驗收者以 `git diff` 對照計畫清單 |
| TC-110 | 必須更新的既有斷言(a)：`test_azure_upload.py` | 功能 | `test_azure_upload.py`（`test_clean_work_and_resume_still_refused_for_azure`、SEQERA 句） | 讀 diff 與跑該檔 | `clean_work` 不再被當作「對 Azure 被拒」，改成可排隊；SEQERA 句改成新句；其餘斷言不動；該檔全綠 | 自動：`test_azure_upload.py`；驗收者以 `git diff` 對照計畫清單 |
| TC-111 | 必須更新的既有斷言(b)：不准動 | 不在範圍 | `test_station_clean_gcb.py`、`test_station_clean_aws.py`（含 TC-084）、`test_cleanup_confirm.py`、`test_cleanup_store.py`（TC-030）、`test_byte_channel_b.py:763`、`test_station_static.py`、`test_aws_ce.py` 的 "can run" 句 | 以 `git diff <base>...HEAD` 比對這些檔 | 一個字都沒動，且跑起來全綠 | 自動：這些既有檔；驗收者以 `git diff` 確認 |
| TC-112 | 範圍（compute_envs 寫成兩段字面）；既有 TC-030 | 不在範圍 | `compute_envs.py` 的 Azure 元組 | 跑 `test_cleanup_store.py::test_nothing_writes_clean_work_or_work_cleaned_at`（TC-030） | 仍綠：`"clean_" "work"` 兩段字面，其他平台檔沒有連續的 `clean_work` | 自動：既有 `test_cleanup_store.py` |
| TC-113 | 範圍（新檔）；既有 TC-070 | 功能 | 兩個新測試檔 `test_station_clean_azure.py`、`test_azure_clean.py` | 讀檔頭前 40 行 | 各有一行 `# Nothing existing: …`，至少 15 個字（既有掃描通過） | 自動：既有 TC-070 掃描 |
| TC-114 | 完成標準 | 功能 | 整個 `platform/tests` | 跑整個套件（由完成記號 GREEN 證明） | 全綠（已知環境紅燈 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 視同綠）；計畫清單以外若有既有斷言變紅，執行者回報 BLOCKED 而不是自行改 | 自動：完成記號＋CI |
| TC-115 | 完成標準（先紅後綠）；原則 IV | 功能 | `specs/azure-clean/ledger.md` | 讀進度帳本 | 記有：新測試在沒改程式的分支上先跑過、確實是紅的；用到的 Microsoft Learn `az storage blob` 頁面網址與用到的旗標；手動差異檢查（範圍、既有測試未被改弱、`clean.py` 以外沒有 `delete-batch`／`rm`、Azure 段在 AWS 標記之前） | 手動：讀 ledger |
| TC-116 | 專長守則（migration）；不做（不重做 cloud-cleanup 的 migration） | 不在範圍 | 資料結構（資料表與欄位） | 新建資料庫，比對資料表與欄位 | 與修改前完全相同（沒有新增或改動欄位；`work_cleaned_at` 是 cloud-cleanup 已有的）；計畫與 PR 說明「不需要 migration」 | 自動：`test_azure_clean.py`（註解標 TC-116）＋既有 migration 測試 |
| TC-117 | 不做（不改確認機制、不改網頁、不新增 MCP 工具）；「不准碰」清單 | 不在範圍 | `web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`、`cloud_store.py`、`datasets.py`、`put_upload.py`、`azure_launch.py` 的既有行為、MCP 工具清單、確認機制測試 | 以 `git diff <base>...HEAD --name-only` 比對，並跑 `test_web_*`、確認相關測試 | 這些檔沒有被改；相關測試全綠且斷言一字未動；沒有新增網頁入口或 MCP 工具 | 自動：既有測試；驗收者以 `git diff` 對照計畫「範圍：檔案」 |
| TC-118 | 不做（排程式自動清理、生命週期規則、費用估算） | 不在範圍 | `compute_envs.py`、`jobs.py` | 比對修改前後 | Azure 放行表與 base 相比只多 `clean_work` 一種；`DEADLINE_SECONDS`、`work_cleaned_at` 寫入邏輯沒變；沒有新增排程、生命週期設定或金額換算 | 自動：`test_azure_clean.py`（註解標 TC-118）；驗收者以 `git diff` 確認 |
| TC-119 | 不做（不處理 Azure 的 resume） | 不在範圍 | Azure 環境；`resume` 與 `relaunch` | 嘗試排入或提出 | 仍被拒，說明尚未支援；行為與修改前相同 | 自動：`test_azure_clean.py`（註解標 TC-119）＋既有 Azure 測試 |
| TC-120 | 範圍（azure_preflight.py 不改既有函式行為） | 不在範圍 | `azure_preflight.py` 的 `clean_environment`、`credentials_path`、`_az_env`、`run_preflight` | 跑既有 `test_azure_ce.py`、`test_azure_launch.py` 的預檢測試；以 `git diff` 看該檔 | 既有函式沒有被改行為（至多多一個唯讀小函式）；預檢測試全綠 | 自動：既有測試；驗收者以 `git diff` 確認 |
| TC-121 | 完成標準（真實刪除不屬完成標準）；不確定點 1–5 | 不在範圍 | 本任務的自動測試 | 檢查是否有測試或程式碼真的呼叫了真 `az`、用了真憑證 | 沒有；全部用假的 `site.run_fixed`；真實清理、真實輸出格式、軟刪除計費的觀察留給維護者（TC-107），驗收記 UNVERIFIED（needs human） | 手動：`docs/TESTING.md`（TC-107 的新節） |

## 憲法與安全網

涉及：憲法 I.2（唯一的送出路徑只在本人的 yes 之後；刪除只在站台代理的 `clean.py`）、IV（先讀來源再下結論）、VI（失敗不能悄悄）、專長守則（確認管道、錯誤訊息、密鑰、跨使用者、對等性）。這件會刪雲端資料，風險較高：任何一道護欄少了就是 FAIL。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-122 | I.2；專長守則（確認管道，未經確認不得改變資料） | 例外 | Azure 環境；`clean_work` 的待確認申請（狀態 pending，沒人按），或已被拒絕、已過期的申請 | 嘗試用它排入 `clean_work`，並直接把內容包交給代理 | 全部被拒；沒有工作被排入；`run_fixed` 呼叫數 0；`work_cleaned_at` 沒有被寫入 | 自動：`test_azure_clean.py`（註解標 TC-122）＋`test_station_clean_azure.py`（TC-038..041） |
| TC-123 | I.2；作法 8 | 例外 | `platform/abf_platform/` 與 `platform/abf_launch/` 全部 `.py`，以及 `abf_station/` 除 `clean.py` 以外的檔案 | 掃描 | 沒有 `delete-batch`、沒有 `rm` 刪除字樣、沒有 `subprocess`、沒有雲端函式庫字樣、平台程式沒有「station」字樣；`web.py`、`web_board.py`、`cloud_store.py`、`put_upload.py` 不含 `azure-clean`、`_clean_azure` | 自動：`test_azure_clean.py::test_the_platform_stays_free_of_deleting_words_and_cloud_libraries`＋既有掃描 |
| TC-124 | 專長守則（錯誤訊息說明原因與處理方式；不露出堆疊、內部路徑） | 例外 | TC-038..TC-091 中每一種拒絕與失敗的回報 | 檢查每一則訊息 | 每一則都有白話中文說明發生什麼事與下一步（重新申請、等 run 結束、檢查預檢…）；沒有堆疊、SQL、內部路徑 | 自動：`test_station_clean_azure.py`（註解標 TC-124） |
| TC-125 | 專長守則（密鑰不得出現在日誌或任何回應） | 例外 | 憑證檔內容與父行程環境都放獨一無二的假金鑰字串；成功與失敗情境 | 搜尋代理的每一個回報、例外訊息與被記錄的 argv | 找不到任何假金鑰；環境只在 `run_fixed` 的 env 參數裡 | 自動：`test_station_clean_azure.py`（註解標 TC-125）＋既有 `tests/credentials_stay_in_settings_test.sh` |
| TC-126 | 專長守則（對等性：使用者可見動作與動作層函式一一對應） | 功能 | 既有的對等性測試 | 跑該測試 | 全綠且清單沒有被改：本任務沒有新增任何使用者可見動作或動作層函式（`offer_cleanups` 不改） | 自動：既有 `test_web_parity.py` 等對等性測試（不改） |
