---
id: azure-clean
title: 分析成功後清掉 Azure Batch 環境的 Blob work 前綴（對應 Google 版 cloud-cleanup、AWS 版 aws-clean 的 clean_work）
tier: B
kinds: backend
lane: L2-platform-ce
after: azure-launch and azure-upload merged into v3
branch: feat/azure-clean
base: v3（azure-launch、azure-upload 合併後）。本檔行號取自 origin/v3 796f971；azure-launch／azure-upload 才會新增或搬動的名字標「合併後才有」，executor 開工前用 `git show origin/v3:<檔>` 重查行號，不對就以實際內容為準
source: memory/dev-plans/aws-clean.md（本檔的孿生，含其 E 段裁決）；memory/dev-plans/cloud-cleanup.md 與 cloud-cleanup-d.md（Google 版，已合併；`clean.py` 的 `_clean_gcb`）；memory/dev-plans/azure-launch.md（Azure 設計與其「developer-agent 裁決」）
---

# azure-clean

> 本檔由 developer-agent 的 subagent 寫（2026-10-28），只有計畫、沒有程式。B 級 → verifier 通過＋CI 綠由 developer-agent 自合。
> **這件會刪雲端資料，風險較高**：刪除範圍只限這個 run 自己的 work 前綴，確認與護欄與 Google 版、AWS 版逐項相同，任何一道護欄少了就是 FAIL。
> **與 azure-upload 動到同一批檔案，必須接力、不可平行**：azure-launch 先、azure-upload 次、本件最後（見「範圍：檔案」最後一段）。本件開工時 azure-launch 與 azure-upload 都已合進 v3。
> 本檔是 aws-clean 的 Azure 孿生：結構與護欄一一對照，差別集中在三處——(1) Azure 的 `workDir` 一定帶子目錄；(2) 刪除用 `az storage blob delete-batch --pattern`，其 pattern 是 fnmatch、`*` 會跨 `/`；(3) 憑證走 `ABF_STATION_AZURE_CREDENTIALS`。

## 目標
一個在 Azure Batch 環境成功跑完的 run，平台提出「清理 work 目錄」的申請，本人在確認頁答 y 之後，平台主機上的站台代理只刪 `az://<container>/<sub>/runs/<run>/work/` 這個前綴底下的 blob（Nextflow 的暫存）；`results` 一個字不動；刪完平台記下 `work_cleaned_at`，同一個 run 不會再被提出第二次。

為什麼這樣切：
1. 提出、確認、排隊的骨架 cloud-cleanup 已經做完（`build.prepare_clean`／`clean_screen`、`actions.offer_cleanups`、確認類型 `clean_work`、`launches.work_cleaned_at`、`jobs.DEADLINE_SECONDS["clean_work"]`）。本任務只新增「Azure 的那一支」，不重做骨架。
2. 平台程式不刪任何東西；會出現 `rm`／`delete` 字樣的檔案只有 `abf_station/clean.py`（沿用 cloud-cleanup 的檔案層級限制）。
3. 憑證只經 `ABF_STATION_AZURE_CREDENTIALS` 指的檔案，由 `azure_preflight._az_env` 放進子行程的環境變數（不進 argv、不進日誌）；用 `az` CLI 經固定指令執行器（`site.run_fixed`，`shell=False`），無 Azure SDK。

## 維護者原話（verifier 出題用）
- aws-launch 裁決 A3（維護者採納）：AWS 的 clean 先關閉，另開 `aws-clean`。→ 本任務完成前 `clean_work` 對 AWS 一直是被拒的。（Azure 對應：azure-launch 對 Azure 一樣先拒 `clean_work`，訊息指向 `azure-clean`；本任務完成前它一直是被拒的。）
- cloud-cleanup 的核心約束（Google 版，同樣適用）：只刪該 run 自己的 work、results 不動、要本人答 y、站台代理重新判斷全部。見 `cloud-cleanup.md` 與 `clean.py` 檔頭。
- 本次派工指示：「刪雲端資料只限該 run 的 work 前綴，確認與護欄要和 gcs 清理相同，絕不刪前綴之外。」

## 範圍：檔案（只准改這些）
- `platform/abf_station/clean.py`：`run_clean`（現行 102 起，依 `ce.platform` 分流：GCB → `_clean_gcb`、AWS → `_clean_aws`）加 Azure 分支；新增 `_clean_azure`，結構逐步對照 `_clean_aws`（275 起）。`KEYS`（26）、`BARRED`、`_head_gone`（170）直接重用。新增 `_azure_work`（對應 `_aws_work`，262）與 Azure 版的訊息清洗（對應 `_said_aws`）。
  - **位置硬規定**：Azure 的程式段放在 `# ---- AWS Batch (aws-clean) ---` 標記（現行 246 行）**之前**，另立 `# ---- Azure Batch (azure-clean) ---` 標記。原因：`test_station_clean_aws.py:540-556`（TC-084）取「AWS 標記之後到檔尾」整段掃禁字，Azure 段若放在後面，就要同時滿足 AWS 的禁字表與 `'s3','rm'` 計數；那條測試不准改。Azure 段本身也避開 `sync`、`s3api`、`boto3` 等字樣（含註解）。
  - 站台程式碼不得出現小寫單字 `azure`（`test_station_static.py:46`，逐行含註解，區分大小寫；寫 `Azure` 或 `az://` 或 `az storage blob` 都可以）；不得 `import azure`（TC-085）。
- `platform/abf_launch/build.py`（E1 同款：不是 `abf_platform/`）：`clean_work_path`（現行 317，GCB／AWS → `<workDir>/runs/<run>/work`）加 Azure；`prepare_clean`（338 起）那行「非 Google 非 AWS 的環境，`posixpath.dirname(run_folder)` 必須等於 `workDir + "/runs"`」要改成「Google、AWS、Azure 都跳過」（Azure 的 run 資料夾在 `<storage_root>/_azure_runs/<run>`，`AZURE_RUNS` 來自 azure-launch）；`clean_screen`（781）：Azure 與 AWS 一樣在前綴後補結尾斜線，另加一句 Azure 專屬說明（新增常數，例如 `CLEAN_AZ`，與 `CLEAN_S3` 同形；寫「刪除的是 Blob 容器裡這個前綴下的物件，只有這一個前綴；容器裡其他的資料夾與檔案不會被動」，並提一句若儲存體帳戶開了軟刪除或版本控制，舊版本與已刪項目在保留期內仍佔空間）。`is_azure` 由 azure-launch 提供（合併後才有）。這是准改的唯一 `abf_launch/` 檔。
- `platform/abf_platform/jobs.py`：`_target`（約 95-135）的 Azure 拒絕訊息裡若有 `azure-clean` 字樣就拿掉（見裁決 E4 同款）；`work_cleaned_at` 寫入（約 1019，條件是結果 `cleaned is True`）、`DEADLINE_SECONDS` 不用改。
- `platform/abf_platform/compute_envs.py`：`CLOUD_JOB_KINDS` 的 Azure 元組加 `"clean_" "work"`（寫成兩段字面，與 Google／AWS 格同款；`test_cleanup_store.py:491-506` TC-030 禁止其他平台檔出現連續的 `clean_work`）。
- `platform/abf_station/handlers.py`：`clean_work` 已有派工，不需要改。
- `platform/abf_station/azure_preflight.py`：只在需要時加一個唯讀小函式；`clean_environment`（回傳 name／platform／credentialsId／location／batchAccountName／storageAccountName／workDir／pool，並以 `compute_envs._check_azure` 重驗）、`credentials_path`、`_az_env`、`run_preflight` 直接重用，**不改既有函式的行為**。
- 新檔：`platform/tests/test_station_clean_azure.py`（檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，TC-070）；平台側測試放 `platform/tests/test_azure_clean.py`（同樣需要 Nothing existing 註解）。
- 文件：`docs/PLATFORM.md`、`docs/SEQERA_PARITY.md`、`docs/TESTING.md`。
- **不准碰**：`web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`、`cloud_store.py`、`datasets.py`、`put_upload.py`（azure-upload 的）、`azure_launch.py` 的既有行為。
- **與 azure-launch／azure-upload 重疊**：三件都會改 `compute_envs.py` 的 `CLOUD_JOB_KINDS` 同一個 Azure 元組、`jobs.py` 的拒絕訊息、三份 `docs/*.md`，以及 `test_azure_ce.py`／`test_azure_launch.py`／`test_azure_upload.py` 裡「Azure 的 put_upload／clean_work 被拒」的斷言。所以必須接力：本件開工前先 rebase 到 azure-upload 合併後的 v3。

## 作法
1. **逐型別放行。** 只在 Azure 那一格加 `"clean_" "work"`。`clean_work` 不要求環境 `available`（`_target` 只對 `list_site_files`／`launch_nextflow`／`put_upload` 要求），與 Google、AWS 一致，不要「順手」改成要求。
2. **站台代理的護欄，順序與 `_clean_aws` 相同，一道都不少**：
   1. `launch.verify_confirmation(job, ctx, "clean_work")`，沒有本人答 y 的確認就在這裡停，`az` 一次都不呼叫。
   2. `KEYS` 檢查、`agent` 檢查、run 名稱正規式、`slurm_job_id`／`pid` 範圍。
   3. `storage_root` 存在，run 資料夾必須恰為 `<storage_root>/_azure_runs/<run>`。
   4. 環境以 `azure_preflight.clean_environment` 重新判斷：容器名稱（`^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$`、無 `--`）、`workDir` 是 `az://<container>/<sub>`（Azure 的 `workDir` 一定帶子目錄，`compute_envs._check_azure` 約 496-515 已驗：子目錄不含 `..`、控制字元）。
   5. 站台代理自己把 work 路徑重算成 `az://<container>/<sub>/runs/<run>/work/`（`_azure_work`），必須和內容包裡的 `work` 逐字相等（內容包的 `work` 無結尾斜線，比較前補齊，與 `_aws_work` 同法）。
   6. 路徑每一段都不是 `BARRED`（`rawdata`、`results`、`analysis`、`..`、`.`），沒有空段，最後一段恰為 `work`；容器與 `workDir` 的容器相同。**另加 Azure 專屬一道：`<sub>` 與 run 名稱不得含 fnmatch 萬用字元 `* ? [ ]`**（因為刪除用的 `--pattern` 是 fnmatch，官方文件寫明 `*` 會連 `/` 一起比對；含萬用字元的子目錄有可能讓 pattern 超出本 run 的前綴）。
   7. `_head_gone`：`head.pid` 的程序已不在、也沒有名為這個 run 的 nextflow 還在跑；還在跑就拒，且此時沒有任何 `az` 呼叫。
   8. 憑證檔存在（`azure_preflight.credentials_path`）、`az` 在 PATH 上、唯讀預檢（azure-launch 的環境檢查函式，名稱以合併後為準，現行對應 `aws_launch._check_environment`）全過；預檢中非 pass 的項目（除憑證名稱一項）都拒。
3. **先唯讀列舉，再刪一次。** 列舉用一次 `az storage blob list --container-name <C> --prefix "<sub>/runs/<run>/work/" --query "[].name" --output tsv --auth-mode key --num-results "*"`（旗標形狀見「環境事實」；`--num-results` 預設 5000，`*` 代表全部，輸出與分頁行為**未驗證**，列為不確定點 1）。列出的每一個 blob 名稱都必須以 `<sub>/runs/<run>/work/` 開頭，否則整個拒絕（擋前綴撞名，例如 `work2/`、`work-keep`、`other/work/`）。列出為空就當成功（`cleaned: True`，訊息白話說「那裡本來就沒有東西」），不呼叫刪除。通過後只執行**一次** `az storage blob delete-batch --source <C> --pattern "<sub>/runs/<run>/work/*" --auth-mode key`：pattern 恰為「整段前綴＋`/*`」；不加 `--dryrun`（那是另一次呼叫）、不加 `--delete-snapshots`、不加任何 `--if-*`、不重試、沒有 shell。憑證只走環境變數（`AZURE_STORAGE_ACCOUNT` 加 `AZURE_STORAGE_KEY` 或 `AZURE_STORAGE_SAS_TOKEN`，由 `_az_env` 放入），argv 裡沒有金鑰。
4. **絕不刪的東西**：`results/`、容器本身、儲存體帳戶、`uploads/`、其他 run 的 `runs/<other>/`、blob 的舊版本與快照（不用 `--delete-snapshots`、不呼叫 `az storage container delete`、`az storage remove`、`az batch ...`、`azcopy`）。測試以禁字掃描把關（見 AZC-STN-13）。
5. **結果形狀**同 Google／AWS 版：`("done", {ok, cleaned: True, run_name, message})`；平台只在 `cleaned is True` 才寫 `work_cleaned_at`。失敗時 `cleaned` 為假、不寫。成功訊息：「已刪除容器裡 %s 底下的物件；results 沒有動」。
6. **錯誤訊息**說發生什麼、該怎麼辦；不露出內部路徑與 `az` 的完整輸出，輸出經清洗（去掉憑證路徑、`ABF_`／`AZURE_` 開頭環境變數的值，對應 `_said_aws`）並截 300 字。
7. **提出清理** `actions.offer_cleanups`（`offer_cleanup` 在 `actions/__init__.py` 約 830-870）與 `cli.py` 的 `offer_cleanups` 指令本身不用改，只驗證 Azure 的成功 run 現在能被提出。
8. 平台程式碼不得出現「station」字樣（TC-061）、`subprocess`、雲端函式庫字樣（TC-071、TC-083/114/085）。`rm`／`delete-batch` 字樣只能出現在 `clean.py`。

## 失敗先行測試（現在全紅；用假的 `site.run_fixed` 記錄每次呼叫的 argv 與 env，`tmp_path` 當 `storage_root`，假容器內容含鄰居 blob `work/…`、`work2/…`、`work-keep`、`results/…`、`other/work/…`；不碰網路、不呼叫真 az、不花錢；輸入一律假的：`labcontainer`、`work`（子目錄）、`westeurope`、`azlab`；假金鑰以字串拼接產生，沿用 `credentials_stay_in_settings_test.sh` 與 azure-launch 的慣例）
站台側（`platform/tests/test_station_clean_azure.py`，ID 前綴 `AZC-STN-`）：
1. `AZC-STN-01 test_clean_azure_lists_then_deletes_exactly_one_prefix`：成功案例的 `run_fixed` 呼叫恰為「一次唯讀列舉、一次 `delete-batch`」，`delete-batch` 的 argv 恰為 `["az","storage","blob","delete-batch","--source","labcontainer","--pattern","work/runs/<run>/work/*","--auth-mode","key"]`（旗標順序以實作為準，集合恰為這五個）。
2. `AZC-STN-02 test_unconfirmed_clean_is_refused_and_az_is_never_called`：沒有有效確認 → 拒，`run_fixed` 呼叫數為 0。
3. `AZC-STN-03 test_expired_or_wrong_type_confirmation_is_refused`：確認類型是 `launch` 而非 `clean_work`、或超過期限 → 拒，呼叫數為 0。
4. `AZC-STN-04 test_a_running_head_is_refused_and_az_is_not_called`：`head.pid` 指到還活著的程序 → 拒，沒有任何列舉或刪除呼叫。
5. `AZC-STN-05 test_listing_with_a_neighbour_prefix_aborts_before_delete`：列舉結果混入 `work/runs/<run>/work2/x` 或 `work/runs/other/work/x` → 整個拒絕，`delete-batch` 沒被呼叫。
6. `AZC-STN-06 test_a_neighbour_that_appears_late_in_a_long_listing_aborts`：列舉輸出超過 1000 行（例如 1500 行），鄰居鍵出現在第 1001 行以後 → 整個拒絕、不呼叫刪除（對應 aws-clean E6，不假設分頁頁數）。
7. `AZC-STN-07 test_empty_listing_is_a_plain_success_without_delete`：列舉為空 → `cleaned: True`，白話訊息，沒有 `delete-batch`。
8. `AZC-STN-08 test_work_path_is_recomputed_and_must_match_the_bundle`：內容包的 `work` 被改成 `az://labcontainer/work/runs/<run>`、`…/results/`、`…/work/../results/`、另一個容器 → 全部拒，呼叫數為 0。
9. `AZC-STN-09 test_workdir_subfolder_is_kept_in_the_prefix`：`workDir=az://labcontainer/work` → pattern 與前綴核對都含 `work/runs/r1/work`，不是 `runs/r1/work`（aws-clean E10 的 Azure 版；Azure 的 workDir 一定有子目錄，沒有裸容器案例）。
10. `AZC-STN-10 test_barred_segments_and_empty_segments_are_refused`：`rawdata`、`results`、`analysis`、`..`、`.`、空段各一例 → 拒。
11. `AZC-STN-11 test_glob_characters_in_the_subfolder_are_refused`：`workDir` 子目錄含 `*`、`?`、`[`、`]` 各一例（此例需讓 `clean_environment` 重驗仍通過或直接餵內容包）→ 拒，呼叫數為 0。
12. `AZC-STN-12 test_run_folder_must_be_the_azure_runs_folder`：run 資料夾不是 `<storage_root>/_azure_runs/<run>`（例如 `_gcb_runs`、`_aws_runs`）→ 拒。
13. `AZC-STN-13 test_forbidden_words_never_appear_in_clean_py`：`clean.py` 的 Azure 段不含 `--delete-snapshots`、`--dryrun`、`container delete`、`storage remove`、`azcopy`、`az batch`、`--if-`、`--sas-token`、`--account-key`（金鑰不得進 argv）、`sync`、`s3api`、`boto3`；`delete-batch` 在 Azure 段恰出現一次；沒有 `run_fixed` 在 For／While 裡。
14. `AZC-STN-14 test_environment_is_judged_again_and_a_bad_container_is_refused`：環境的 `workDir` 非 `az://`、容器名稱不合規則（大寫、`--`、過短）、子目錄含 `..` → 拒，呼叫數為 0。
15. `AZC-STN-15 test_az_env_has_only_the_allowed_azure_keys`：每次 `run_fixed` 的 env 只帶 `_az_env` 設的那些 `AZURE_*`（儲存體帳戶、金鑰或 SAS、`AZURE_CONFIG_DIR`、`AZURE_CORE_*`）；父行程塞的 `ABF_X`、其他 `AZURE_*` 不在其中；假金鑰的值不出現在任何 argv、結果訊息。
16. `AZC-STN-16 test_a_failed_delete_is_not_retried_and_cleaned_is_false`：假 `delete-batch` 回非零 → 只呼叫一次、`cleaned` 非真、訊息不含完整輸出與金鑰。
17. `AZC-STN-17 test_a_missing_credentials_file_or_missing_az_fails_safely`：憑證檔不存在、或 `az` 不在 PATH → 失敗，呼叫數為 0，訊息不含金鑰值。
18. `AZC-STN-18 test_google_and_aws_clean_paths_are_unchanged`：同一組假世界下 `_clean_gcb`、`_clean_aws` 的 argv 與結果與合併前相同（只驗不變，不改它們的測試）。
平台側（`platform/tests/test_azure_clean.py`，ID 前綴 `AZC-PLT-`）：
19. `AZC-PLT-01 test_clean_work_is_allowed_for_azure_and_still_for_google_and_aws`：`CLOUD_JOB_KINDS` 的 Azure 含 `clean_work`，且恰為 preflight、launch_nextflow、cancel_run、pipeline_files、put_upload、clean_work 六個（azure-upload 已合併）；Google、AWS 那格不變。
20. `AZC-PLT-02 test_prepare_clean_accepts_a_succeeded_azure_run`：手算案例：Azure 環境 `workDir=az://labcontainer/work`、run `r1` → `bundle["work"]=="az://labcontainer/work/runs/r1/work"`；run 資料夾 `_azure_runs/r1` 不會被「必須在 workDir/runs 底下」那條擋掉。
21. `AZC-PLT-03 test_prepare_clean_refuses_when_the_environment_changed_after_the_run`：環境 `workDir` 改過 → 拒並說明。
22. `AZC-PLT-04 test_prepare_clean_refuses_an_already_cleaned_run`：`work_cleaned_at` 已有值 → 拒。
23. `AZC-PLT-05 test_offer_cleanup_offers_for_a_succeeded_azure_run`：成功的 Azure run → 建立 `clean_work` 的待確認申請；失敗或取消的 run 不提出。
24. `AZC-PLT-06 test_the_clean_screen_says_what_is_deleted_and_what_is_kept_in_plain_words`：畫面含 `az://labcontainer/work/runs/r1/work/`（帶結尾斜線）、寫明 results 不會動、「永久刪除」，含 Azure 軟刪除／版本說明那一句，不含金額或台幣換算；Google、AWS 畫面一字不變。
25. `AZC-PLT-07 test_work_cleaned_at_is_written_only_when_cleaned_is_true`：`cleaned` 真 → 寫入；假 → 不寫。
26. `AZC-PLT-08 test_clean_work_for_azure_leaves_launch_cancel_and_upload_unchanged`：Azure 的 `launch_nextflow`、`cancel_run`、`put_upload` 行為與合併前完全相同。
27. `AZC-PLT-09 test_the_platform_stays_free_of_deleting_words_and_cloud_libraries`：`web.py`、`web_board.py`、`cloud_store.py`、`put_upload.py` 不含 `azure-clean`、`_clean_azure`（仿 `test_aws_clean.py:388`）；平台檔無 `delete-batch`、`subprocess`、`station`。
28. `AZC-PLT-10 test_docs_say_azure_can_clean_now`：`docs/PLATFORM.md` 與 `docs/SEQERA_PARITY.md` 的新字串逐字成立（見裁決 E3、E6）。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
行號取自 origin/v3 796f971，**azure-launch／azure-upload 已搬動或新增的標「合併後」，executor 開工前用 `git grep -nE "clean_work|azure-clean|_clean_aws|CLOUD_JOB_KINDS|can run" -- platform docs` 重查**；內容相同行號漂移照改，冒出清單外會紅的斷言 → 回報 BLOCKED，不自行改（過去漏列導致 BLOCKED(contract)，這份清單盡量窮盡）。

(a) 會因本任務而改的：
- `platform/tests/test_station_clean.py:588`（TC-073）：`assert holders == {"_clean_gcb", "_clean_aws", "_head_gone"}` → 加上 `"_clean_azure"`，只加這一個名字（`ctx.site.call(` 恰一次、TC-085 `rm -rf` 只在 clean.py 不受影響）。
- `platform/tests/test_azure_ce.py`（合併後行號會因 azure-launch 而動）：
  - 約 738 的「各 job 種類對 Azure 被拒」迴圈（含 `clean_work`，預期訊息為 「尚未支援送出」＋`azure-launch`）：azure-launch 改過、azure-upload 改過後，本任務把 `clean_work` 從「被拒」清單拿掉。
  - 約 936 `test_no_new_write_path_for_azure`（迴圈：`launch_nextflow, cancel_run, clean_work, put_upload, pipeline_files, list_site_files` 全拒）：**不在 azure-launch 的更新清單內**，azure-launch、azure-upload 合併後的狀態未知；本任務必須重讀，把 `clean_work` 移出（若整條已被前兩件改成別的形狀，照實際內容改，並在帳本記一行）。
  - 約 951 `"azure-launch" in msgs["launch"]` 與任何要求訊息含 `azure-clean`／`azure-upload` 字樣的斷言（合併後才有）：改成新訊息該有的字（「尚未支援」）並不得含 `azure-clean`。
  - 約 857-864（PLATFORM.md Azure 列與 SEQERA 列的逐字斷言；azure-launch 與 azure-upload 各改一次）：改成本任務的新字串（見 E3、E6）。
- `platform/tests/test_azure_launch.py`（合併後才有）：AZL-GATE-01（Azure 拒 `clean_work`，訊息含 `azure-clean`）→ 改成 `clean_work` 對 Azure 可排隊；AZL-GATE-03（`CLOUD_JOB_KINDS[AZURE]` 恰為四個值；azure-upload 後為五個）→ 改成含 `clean_work` 的六個；AZL-GATE-05（`test_put_upload_and_clean_work_jobs_cannot_be_queued_for_azure`，含 `clean.run_clean` 拒 Azure 內容包）→ 兩邊都已不成立，移除或由 AZC-PLT-01、AZC-STN-01 取代；AZL-DOC-01（PLATFORM.md Azure 列 "checked and launched on the platform host (upload, clean, resume: not yet)" 之類）、AZL-DOC-02（SEQERA 列舊句）→ 新句。
- `platform/tests/test_azure_upload.py`（合併後才有）：azure-upload 計畫內仍把 `clean_work` 當「對 Azure 被拒」的斷言與 SEQERA 句（形狀同 `test_aws_upload.py:128-131`、`149-157`、`551`、`754-756`）→ 改成可排隊／新句。
- `platform/tests/test_aws_ce.py`：907-908（SEQERA 的 AWS 列斷言，不變）、924（"can run" 句）：azure-launch 已把句子改成 `Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; the other ten types can be modelled only`，本任務**不動這句**（Azure 的「可運行」在 azure-launch 就成立）；只有當 PLATFORM.md 表格 Azure 列有逐字釘住，才連動。
- `platform/tests/test_gcb_ce.py:853-854, 867`、`test_gcb_launch.py:1151`、`test_aws_launch.py:985, 992`：這些釘 "can run" 句與 SEQERA 的 Google／AWS 列；azure-launch 已改過，本任務若沒動那些句子則不改，若 PLATFORM.md 的表格列因本任務而改變 Azure 那一行，連動的只有 Azure 那一行的斷言。
- `docs/PLATFORM.md`（v3 現行行號）：型別表 465-477（`azbatch-platform` 列，現行 476，azure-launch／azure-upload 後會變）→ 改成「checked, launched and cleaned on the platform host (resume: not yet)」之類的新字串（以裁決 E6 為準）；「Cleaning a finished run's work folder」節（約 531-537，Which folder／Who deletes／After it 三段）要補 Azure 一句：work 位於 `az://<container>/<sub>/runs/<run>/work`、容器若開了軟刪除或版本控制，舊版本與已刪項目在保留期內仍佔空間（對照 `test_aws_clean.py` TC-092 對 AWS 版本控管句的釘法；Google／AWS 既有句不動）。
- `docs/SEQERA_PARITY.md`：第 97 行附近 Azure 列（azure-launch 後為 `Have (create + check + launch + cancel)`、azure-upload 後多 `+ upload`）→ `Have (create + check + launch + cancel + upload + clean)`（E3）。第 84 行的 Pre-flight 句與 `test_aws_clean.py:359-366` 釘的「for AWS Batch the same agent runs them…」句**不動**。
- `docs/TESTING.md`：新增 "Cleaning an Azure Batch work folder (azure-clean): the maintainer checks by hand" 節，仿 828-834 的 AWS 節（C 級手動，見「完成標準」）；Azure 型別節（約 787-793）若有「clean 未做」字樣連動改。

(b) 不准動、但容易誤傷的（執行時務必確認它們仍綠）：
- `platform/tests/test_station_clean_aws.py:540-556`（TC-084，AWS 段禁字掃描，見「範圍」的位置硬規定）、576（`def _clean_aws(` 在）、566-573。
- `platform/tests/test_station_clean_gcb.py:485-528`：`storage rm` 只在 clean.py（TC-054）、`rm -rf` 只在 clean.py（TC-057）、TC-058 禁 `batch jobs delete`、`buckets delete`、`gsutil`、`rclone`、`--continue-on-error`、`--all-versions`、run_fixed 不在迴圈裡；TC-069 要求 `clean.py` 第 1 行含 `gcloud storage rm` 與 `prefix`（不改第 1 行與檔頭）；`test_station_clean.py` TC-083（前 40 行含 `nextflow clean`、`rclone purge`、`Seqera`）。
- `platform/tests/test_station_static.py:46`（`\bazure\b` 小寫禁字）、`test_aws_launch.py:1161`、`test_aws_upload.py:693-713`、`test_gcb_ce.py:825-828`、`test_gcb_launch.py:1093`、`test_station_envs.py:478-482`、`test_byte_channel_b.py:903`、`test_cloud_upload.py:649`（雲端函式庫字樣掃描）。
- `platform/tests/test_cleanup_store.py:491-506`（TC-030，連續字串 `clean_work` 只准在 store／confirm／jobs，web／actions 唯讀）、`test_cleanup_confirm.py`、`test_byte_channel_b.py:763`：一個字都不准動。

## 完成標準（done when）
- 上面 28 條測試全綠（條數以合約 TC 為準，28 只是下限），且執行前確認過它們是紅的（先在沒改程式的分支跑一次，紅的記進 ledger）。
- 整個 `platform/tests` 套件全綠，Google、AWS 清理與確認相關測試不改任何斷言（除上列有意更新）。已知環境紅燈 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 視同綠。
- 手動差異檢查（範圍、既有測試未被改弱、`clean.py` 以外沒有 `delete-batch`／`rm` 字樣、Azure 段在 AWS 標記之前）記在 ledger，不列為 TC。
- **真實刪除 Azure 資料不屬完成標準**（C 級：動雲端資料）；列在下面「Needs human」，驗收記 UNVERIFIED(needs human)。

### Needs human（C 級，由維護者本人做，不是 executor 的事）
- 對**測試用**容器與測試用前綴做一次真實清理：先用 `az storage blob list --prefix …` 確認前綴內容，再從確認頁答 y，事後再 list 確認只有該前綴消失、鄰居前綴與 `results/` 完好；記下 `delete-batch` 的真實輸出格式、失敗時的結束碼、`list --num-results "*"` 對大量 blob 的實際行為，回報給 developer-agent 補進 `docs/TESTING.md`。
- 在開了軟刪除／版本控制的儲存體帳戶上觀察：刪除後舊版本是否仍在、是否仍計費。
- 真實 Azure 憑證、容器、費用一律由維護者提供與決定；測試與 CI 只用假的。

## 環境事實
- Azure run 的資料夾是 `<storage_root>/_azure_runs/<run>`，裡面的 `head.pid` 存 pid（azure-launch 設計，合併後才有）。
- work 在 `az://<container>/<sub>/runs/<run>/work`，results 在 `az://<container>/<sub>/runs/<run>/results`（azure-launch 設計）；blob 名稱前綴為 `<sub>/runs/<run>/work/`。Azure 的 `workDir` 一定帶子目錄（`compute_envs._check_azure`），所以沒有「裸容器」案例。
- 憑證：`ABF_STATION_AZURE_CREDENTIALS`，預設 `<部署資料夾>/_personal/azure-credentials`（`azure_preflight.py`）；INI `[default]` 內 `batch_account_key` 與 `storage_account_key` 或 `storage_sas_token`；`_az_env` 放入 `AZURE_STORAGE_ACCOUNT`、`AZURE_STORAGE_KEY`／`AZURE_STORAGE_SAS_TOKEN`、`AZURE_CONFIG_DIR`、`AZURE_CORE_*`，並清掉所有 `ABF_*`／`AZURE_*`。既有儲存體預檢用 `az storage container exists --name C --query exists --output tsv --auth-mode key`，列舉與刪除沿用同樣的 `--auth-mode key`。
- Google 版刪除只有一次 `gcloud storage rm --recursive` 前面加一次唯讀 `ls --recursive`，且檢查每一行都以 work 網址開頭；AWS 版 `_clean_aws` 同結構；Azure 版照做。
- **已讀的官方文件**（Microsoft Learn，`az storage blob` 參考：https://learn.microsoft.com/en-us/cli/azure/storage/blob?view=azure-cli-latest ，本計畫只讀了該頁前約 10 萬字元／共約 18 萬字元）：
  - `az storage blob delete-batch`：「Delete blobs from a blob container recursively.」旗標 `--source/-s`（容器名稱或 URL）、`--pattern`（fnmatch：`*`、`?`、`[seq]`、`[!seq]`；「用 `*` 時會比對任何字元，包括目錄分隔符 `/`」；範例 `--pattern "dir/*"` 刪「目錄」內所有 blob）、`--dryrun`（只顯示摘要不刪）、`--auth-mode {key,login}`、`--account-name`（環境變數 `AZURE_STORAGE_ACCOUNT`）、`--account-key`、`--sas-token`、`--delete-snapshots {include,only}`（「blob 有快照時必須指定」）、`--timeout`、`--if-*`、`--lease-id`。
  - `az storage blob list`：`--container-name/-c`、`--prefix`（範例「foo」會比對 `foo`、`foobar`、`foo/bar`，所以前綴**必須以 `/` 結尾**）、`--num-results`（預設 5000，`*` 為全部）、`--marker`、`--show-next-marker`、`--delimiter`、`--include`、`--auth-mode`、`--query`；跨分區邊界時回傳續傳標記。該頁沒有 `--query` 的範例，也沒有分頁流程說明。
- **未驗證**（本計畫沒有讀到、不得當成事實）：`delete-batch` 的輸出格式與部分失敗時的結束碼；`delete-batch` 內部是否先以 pattern 的固定前綴縮小列舉範圍（影響大容器的效能，不影響正確性）；SAS 權杖是否需要 delete 權限；階層式命名空間（ADLS Gen2）帳戶上目錄物件的行為；blob 軟刪除與版本控制對刪除後計費的影響；`delete-batch` 對超過 5000 個 blob 是否自行分頁；`list --query "[].name" -o tsv` 在 `--num-results "*"` 下的實際輸出。

## 不做
- 不刪 results、不刪容器、不刪儲存體帳戶、不刪 `uploads/`、不刪其他 run、不處理 blob 舊版本、快照與軟刪除項目。
- 不做排程式自動清理、不做生命週期管理規則、不做費用估算（C-3）。
- 不改確認機制本身、不改網頁檔案、不新增 MCP 工具。
- 不用 Azure SDK，不用 `azcopy`，不用 `--dryrun`／`--delete-snapshots`／`--if-*`，不用金鑰旗標（`--account-key`、`--sas-token`）。
- 不重做 cloud-cleanup 已有的 migration、`offer_cleanups` 指令。
- 不處理「azure-launch 的 resume」；續跑仍是 not yet。

## 不確定的地方（需要維護者或執行者查證）
1. 列舉的輸出與分頁：`az storage blob list --num-results "*"` 在大量 blob 下是否回傳全部、`--query "[].name" -o tsv` 是否一行一個名稱；只看第一頁就判斷「全部以前綴開頭」是不夠的。測試以長輸出（鄰居鍵在第 1001 行以後）涵蓋；真實行為留給 C 級手動檢查。
2. `delete-batch --pattern "<prefix>/*"` 的 fnmatch 語意：`*` 會跨 `/`（官方已寫）；前綴結尾 `/` 使 `work2/`、`work-keep` 不被吃到，但 `[` `]` `?` `*` 若出現在 `<sub>` 會改變比對範圍，所以護欄 2.6 直接拒絕這些字元。是否還要再加「delete-batch 之前以列舉結果逐筆比對」（已有，作法 3）即足夠，維護者可否決。
3. 軟刪除與版本控制：新建儲存體帳戶的 blob 軟刪除預設通常開著（保留期內可還原、仍佔空間），本計畫**未查證預設值**；清理畫面只提一句、文件寫明，不處理舊版本。
4. 階層式命名空間帳戶：目錄本身是物件，`delete-batch` 是否會留下空目錄、`list --prefix` 是否會回傳目錄物件（名稱以 `…/work` 無斜線結尾）會使「每個名稱以 `…/work/` 開頭」的檢查誤拒。本計畫**未驗證**；遇到時寧可誤拒、不放行。
5. 金鑰權限：`--auth-mode key` 用儲存體帳戶金鑰，權限遠大於本 run 的前綴；若維護者改用 SAS，需要 list＋delete 權限，且 `_read_shape` 目前接受 `storage_sas_token`，行為差異未驗證。
6. `head.pid` 在 Azure 的意義是否與 Google／AWS 完全相同（azure-launch 的 `gcb_launch._cancel_head` 重用）；合併後以實際為準。
7. 清理的時機：沿用 Google 版（run 成功才提出）。
8. 與 azure-upload 的接力順序與 SEQERA／PLATFORM 字串：若 azure-upload 尚未合併，本件不開工。

## 裁決

（developer-agent 10-29 02:5x 填寫；原本這裡的預設值段被截斷，以本節為準。）

1. 行號一律視為「約略」：azure-upload 已於 #261 合進 v3（新增 `platform/tests/test_azure_upload.py`、改了 compute_envs／jobs／cloud_store／docs）。executor 開工先在 origin/v3 用 grep 引號內的內容重新定位每一個被點名的斷言；找不到原句就在帳本記一行並回報，不得猜。
2. 列舉分頁（不確定 1）：照計畫用 `--num-results "*"`＋逐行檢查全部名稱；任何一行不以 `<prefix>/` 開頭就整個拒絕、不呼叫刪除。真實分頁行為留給手動步驟。
3. fnmatch（不確定 2）：`<sub>` 含 `[ ] ? *` 一律拒絕（護欄 2.6），不再另加別的檢查。
4. 軟刪除（不確定 3）：不處理舊版本；清理確認句與 PLATFORM.md 各加一句「若儲存體帳戶開了軟刪除，刪掉的檔案在保留期內仍佔空間」。
5. 階層式命名空間（不確定 4）：寧可誤拒——列舉出現名稱恰為 `<prefix>`（無結尾斜線）的目錄物件也算鄰居、整個拒絕，訊息白話說明。
6. 權限（不確定 5）：有帳號金鑰帶 `--auth-mode key`；只有 SAS 時不帶 `--auth-mode`、靠環境變數，與 azure-upload 同款。不新增設定欄位。
7. `head.pid`（不確定 6）、清理時機（不確定 7）：照 Google／AWS 版，run 成功才提出清理。
8. 接力（不確定 8）：azure-upload 已合併，可開工。SEQERA 的 Azure 列以 #261 合併後的實際文字為起點加 `+ clean`。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
