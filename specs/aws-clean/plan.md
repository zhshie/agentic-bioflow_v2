---
id: aws-clean
title: 分析成功後清掉 AWS Batch 環境的 S3 work 前綴（對應 Google 版 cloud-cleanup 的 clean_work）
tier: B
kinds: backend
lane: L2-platform-ce
after: aws-launch merged into v3
branch: feat/aws-clean
base: v3（aws-launch 合併後）。本檔行號取自 origin/v3 9f6c8d2；aws-launch 才會新增或搬動的名字標「合併後才有」，executor 開工前用 `git show origin/v3:<檔>` 重查行號，不對就以實際內容為準
source: memory/dev-plans/cloud-cleanup.md 與 cloud-cleanup-d.md（Google 版，已合併；`clean.py` 的 `_clean_gcb`）；memory/dev-plans/aws-launch.md（裁決 A3：AWS 的 clean 先關閉）
---

# aws-clean

> 本檔由 developer-agent 的 subagent 寫（2026-10-28），只有計畫、沒有程式。B 級 → verifier 通過＋CI 綠由 developer-agent 自合。
> **這件會刪雲端資料，是兩件裡風險較高的一件**：刪除範圍只限這個 run 自己的 work 前綴，確認與護欄與 Google 版逐項相同，任何一道護欄少了就是 FAIL。
> **與 aws-upload 動到同一批檔案，兩件必須接力、不可平行**（見「範圍：檔案」最後一段）。建議 aws-upload 先合併。

## 目標
一個在 AWS Batch 環境成功跑完的 run，平台提出「清理 work 目錄」的申請，本人在確認頁答 y 之後，平台主機上的站台代理只刪 `s3://<bucket>/runs/<run>/work/` 這個前綴底下的物件（Nextflow 的暫存）；`results` 一個字不動；刪完平台記下 `work_cleaned_at`，同一個 run 不會再被提出第二次。

為什麼這樣切：
1. 提出、確認、排隊的骨架 cloud-cleanup 已經做完（`build.prepare_clean`／`clean_screen`、`actions.offer_cleanups`、確認類型 `clean_work`、`launches.work_cleaned_at` 的 migration、`jobs.DEADLINE_SECONDS["clean_work"]`）。本任務只新增「AWS 的那一支」，不重做骨架。
2. 平台程式不刪任何東西；會出現 `rm` 字樣的檔案只有 `abf_station/clean.py`（沿用 cloud-cleanup 的檔案層級限制）。
3. 憑證只經 `AWS_SHARED_CREDENTIALS_FILE` 加 `AWS_PROFILE=default`，用 aws CLI 經固定指令執行器（`site.run_fixed`，`shell=False`），無 boto3。

## 維護者原話（verifier 出題用）
- aws-launch 裁決 A3（維護者採納）：AWS 的 clean 先關閉，另開 `aws-clean`。→ 本任務完成前 `clean_work` 對 AWS 一直是被拒的。
- cloud-cleanup 的核心約束（Google 版，同樣適用）：只刪該 run 自己的 work、results 不動、要本人答 y、站台代理重新判斷全部。見 `cloud-cleanup.md` 與 `clean.py` 檔頭。
- 本次派工指示：「刪雲端資料只限該 run 的 work 前綴，確認與護欄要和 gcs 清理相同，絕不刪前綴之外。」

## 範圍：檔案（只准改這些）
- `platform/abf_station/clean.py`：`run_clean`（現行 101 起，108 行依 `ce.platform == launch.GCB` 分流）加 AWS 分支；新增 `_clean_aws`，結構逐步對照 `_clean_gcb`（189 起）。`KEYS`（26）、`BARRED`（28）、`_head_gone`（167）、`NOTHING_MATCHED`（137）直接重用。新增 `_aws_work`（對應 `_gcb_work`，155）與 AWS 版的環境檢查。
- `platform/abf_platform/build.py`：`prepare_clean`（現行 338 起）有一行「非 Google 的環境，`posixpath.dirname(run_folder)` 必須等於 `workDir + "/runs"`」；AWS 的 run 資料夾在 `<storage_root>/_aws_runs/<run>`（aws-launch 的 `AWS_RUNS`），所以那一行要改成「Google 與 AWS 都跳過」。`clean_work_path(ce, row)` 要能回 AWS 的 `<workDir>/runs/<run>/work`。`clean_screen` 的畫面文字若寫死「Google／bucket／gcloud」要依類型改成白話的 S3 說明。這個檔案也有 `is_gcb`（約 270）；是否需要同形的 AWS 判斷，以合併後實際內容為準。
- `platform/abf_platform/jobs.py`：`clean_work` 對 AWS 放行（走逐型別表）；其餘 `work_cleaned_at` 寫入（約 1012，條件是結果 `cleaned is True`）、`DEADLINE_SECONDS`（30）不用改，除非有寫死 Google 的判斷。
- `platform/abf_platform/compute_envs.py`：`CLOUD_JOB_KINDS` 的 AWS 元組加 `"clean_work"`（只加這一個字串）。
- `platform/abf_station/handlers.py`：`clean_work` 已有派工，不需要改；只有新增的 `KEYS` 需要時才動。
- 新檔：`platform/tests/test_station_clean_aws.py`（檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，TC-070）；平台側的提出與放行測試放 `platform/tests/test_aws_clean.py`（同樣需要 Nothing existing 註解）。
- 文件：`docs/PLATFORM.md`、`docs/SEQERA_PARITY.md`、`docs/TESTING.md`。
- **不准碰**：`web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`、`cloud_store.py`、`datasets.py`、`put_upload.py`（那是 aws-upload 的）。
- **與 aws-upload 重疊**：兩件都會改 `jobs.py`、`compute_envs.py` 的 `CLOUD_JOB_KINDS` 同一行 AWS 元組、三份 `docs/*.md`，以及 `test_aws_launch.py` 裡「AWS 的 put_upload／clean_work 被拒」的斷言。所以必須接力：後一件開工前先 rebase 到前一件合併後的 v3。

## 作法
1. **逐型別放行。** 只在 AWS 那一格加 `"clean_work"`。注意 `clean_work` 不要求環境 `available`（現行 126 行只列 `list_site_files`／`launch_nextflow`／`put_upload`），這點和 Google 一致，不要「順手」改成要求。
2. **站台代理的護欄，順序與 `_clean_gcb` 相同，一道都不少**：
   1. `launch.verify_confirmation(job, ctx, "clean_work")`，沒有本人答 y 的確認就在這裡停，`aws` 一次都不呼叫。
   2. `KEYS` 檢查、`agent` 檢查、run 名稱正規式、`slurm_job_id`／`pid`。
   3. `storage_root` 存在，run 資料夾必須恰為 `<storage_root>/_aws_runs/<run>`。
   4. 環境以 `aws_preflight.clean_environment`（或 aws-launch 合併後的同等函式）重新判斷：區域、bucket 名稱（不得含 `..`）、`workDir` 是 `s3://`。
   5. 站台代理自己把 work 路徑重算成 `s3://<bucket>/runs/<run>/work/`，必須和內容包裡的 `work` 逐字相等。
   6. 路徑每一段都不是 `BARRED`（`rawdata`、`results`、`analysis`、`..`、`.`），沒有空段，最後一段恰為 `work`；bucket 與 `workDir` 的 bucket 相同。
   7. `_head_gone`：`head.pid` 的程序已不在、也沒有名為這個 run 的 nextflow 還在跑；還在跑就拒。
   8. 憑證金鑰檢查與環境檢查（共用 aws-launch 的 `_check_environment`，名稱以合併後為準）。
3. **先唯讀列舉，再刪一次。** 先用唯讀指令列出前綴內的物件（候選：`aws s3 ls --recursive s3://<bucket>/runs/<run>/work/` 或 `aws s3api list-objects-v2 --bucket B --prefix runs/<run>/work/`；兩者輸出格式本計畫**都沒讀過官方文件，查不到**，執行者要先讀 `https://docs.aws.amazon.com/cli/latest/reference/s3/ls.html`、`.../s3/rm.html`、`.../s3api/list-objects-v2.html` 再選一個）。列出的每一個鍵都必須以 `runs/<run>/work/` 開頭，否則整個拒絕（擋前綴撞名，例如 `work2/`、`work-keep`）。列出為空就當成功（`cleaned: True`，訊息白話說「那裡本來就沒有東西」）。通過後只執行**一次** `aws s3 rm s3://<bucket>/runs/<run>/work/ --recursive --region <region>`：前綴結尾必須有斜線；不加 `--include`／`--exclude`、不重試、不用 `--dryrun` 之外的任何旗標；沒有 shell。
4. **絕不刪的東西**：`results/`、bucket 本身、`uploads/`、其他 run 的 `runs/<other>/`、物件的舊版本（不呼叫 `s3api delete-objects`、`delete-bucket`、`--versions`）。測試以禁字掃描把關（見測試 13）。
5. **結果形狀**同 Google 版：`("done", {ok, cleaned: True, run_name, message})`；平台只在 `cleaned is True` 才寫 `work_cleaned_at`。失敗時 `cleaned` 為假、不寫。成功訊息對照 Google 版：「已刪除 bucket 裡 %s 底下的物件；results 沒有動」，AWS 版改成白話的 S3 說法。
6. **錯誤訊息**說發生什麼、該怎麼辦；不露出內部路徑與 `aws` 的完整輸出，輸出經 `aws_preflight._scrub` 並截 300 字。
7. **提出清理** `actions.offer_cleanups` 與 `cli.py` 的 `offer_cleanups` 指令本身不用改（現行 `actions/__init__.py:859`、`cli.py:470-484`），只驗證 AWS 的成功 run 現在能被提出。
8. 平台程式碼不得出現「station」字樣（TC-061）、`subprocess`、雲端函式庫字樣（TC-071、TC-083/114/085）。`rm` 字樣只能出現在 `clean.py`。

## 失敗先行測試（`platform/tests/test_station_clean_aws.py` 與 `platform/tests/test_aws_clean.py`，現在全紅；用假的 `site.run_fixed` 記錄每次呼叫的 argv，`tmp_path` 當 `storage_root`，假 bucket 內容含鄰居物件 `runs/<run>/work/`、`runs/<run>/work2/`、`runs/<run>/work-keep`、`runs/<run>/results/`、`runs/other/work/`；不碰網路、不呼叫真 aws、不花錢；輸入一律假的：`lab-bucket`、`eu-west-1`、`aws-lab`）
站台側（`test_station_clean_aws.py`）：
1. `test_clean_aws_lists_then_removes_exactly_one_prefix`：成功案例的 `run_fixed` 呼叫恰為「一次唯讀列舉、一次 `rm`」，`rm` 的 argv 恰為 `["aws","s3","rm","s3://lab-bucket/runs/<run>/work/","--recursive","--region","eu-west-1"]`。
2. `test_unconfirmed_clean_is_refused_and_aws_is_never_called`：沒有有效確認 → 拒，`run_fixed` 呼叫數為 0。
3. `test_expired_or_wrong_type_confirmation_is_refused`：確認類型是 `launch` 而非 `clean_work`、或超過期限 → 拒，呼叫數為 0。
4. `test_a_running_head_is_refused_and_aws_is_not_called`：`head.pid` 指到還活著的程序 → 拒，呼叫數為 0。
5. `test_listing_with_a_neighbour_prefix_aborts_before_rm`：列舉結果混入 `runs/<run>/work2/x` 或 `runs/other/work/x` → 整個拒絕，`rm` 沒被呼叫。
6. `test_empty_listing_is_a_plain_success_without_rm`：列舉為空 → `cleaned: True`，白話訊息，沒有 `rm`。
7. `test_work_path_is_recomputed_and_must_match_the_bundle`：內容包的 `work` 被改成 `s3://lab-bucket/runs/<run>/`、`.../results/`、`.../work/../results/`、另一個 bucket → 全部拒，呼叫數為 0。
8. `test_barred_segments_and_empty_segments_are_refused`：`rawdata`、`results`、`analysis`、`..`、`.`、空段各一例 → 拒。
9. `test_run_folder_must_be_the_aws_runs_folder`：run 資料夾不是 `<storage_root>/_aws_runs/<run>`（例如 `_gcb_runs`）→ 拒。
10. `test_environment_is_judged_again_and_a_bad_bucket_or_region_is_refused`：環境的 `workDir` 非 `s3://`、bucket 名稱含 `..`、region 不合規則 → 拒，呼叫數為 0。
11. `test_aws_env_has_only_the_credentials_file_and_profile`：每次 `run_fixed` 的 env 只帶 `AWS_SHARED_CREDENTIALS_FILE`、`AWS_PROFILE=default`、`AWS_CONFIG_FILE=os.devnull`、`AWS_DEFAULT_REGION`；父行程塞的金鑰類 `AWS_*` 與 `ABF_X` 不在其中。
12. `test_a_failed_rm_is_not_retried_and_cleaned_is_false`：假 `rm` 回非零 → 只呼叫一次、`cleaned` 非真、訊息不含完整輸出。
13. `test_forbidden_words_never_appear_in_clean_py`：`clean.py` 的 AWS 分支不含 `delete-objects`、`delete-bucket`、`--versions`、`--include`、`--exclude`、`sync`、`boto3`、`--recursive` 以外的刪除旗標；`rm` 的 argv 在任何情況下都以 `runs/` 開頭的 work 前綴結尾。
14. `test_a_missing_credentials_file_fails_with_the_one_allowed_path_detail`：憑證檔不存在 → 失敗，訊息可含該路徑（補充 8–13 的例外），不含任何金鑰值，呼叫數為 0。
平台側（`test_aws_clean.py`）：
15. `test_clean_work_is_allowed_for_aws_and_still_for_google`：`CLOUD_JOB_KINDS` 的 AWS 含 `clean_work`；Google 那格不變；AWS 的 `put_upload` 與 aws-upload 是否已合併一致（若 aws-upload 未合併，斷言它仍被拒）。
16. `test_prepare_clean_accepts_a_succeeded_aws_run`：手算案例：AWS 環境 `workDir=s3://lab-bucket`、run `r1` → `bundle["work"]=="s3://lab-bucket/runs/r1/work"`；run 資料夾 `_aws_runs/r1` 不會被「必須在 workDir/runs 底下」那條擋掉。
17. `test_prepare_clean_refuses_when_the_environment_changed_after_the_run`：環境 `workDir` 改過 → 拒並說明。
18. `test_prepare_clean_refuses_an_already_cleaned_run`：`work_cleaned_at` 已有值 → 拒。
19. `test_offer_cleanup_offers_for_a_succeeded_aws_run`：成功的 AWS run → 建立 `clean_work` 的待確認申請；失敗或取消的 run 不提出。
20. `test_the_clean_screen_says_what_is_deleted_and_what_is_kept_in_plain_words`：畫面含 `s3://lab-bucket/runs/r1/work/`、寫明「results 不會動」「刪除無法復原」，不含金額或台幣換算。
21. `test_work_cleaned_at_is_written_only_when_cleaned_is_true`：`cleaned` 真 → 寫入；`cleaned` 假 → 不寫。
22. `test_clean_work_result_for_aws_leaves_launch_and_cancel_unchanged`：AWS 的 `launch_nextflow`、`cancel_run` 行為與 aws-launch 合併後完全相同。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
- `test_aws_launch.py` 的 `test_put_upload_and_clean_work_jobs_cannot_be_queued_for_aws`：若 aws-upload 先合併，這條已被改成只剩 `clean_work`，本任務把它改成「`clean_work` 對 AWS 可排隊」或整條移除並由上面第 15 條取代；若本任務先合併，則改成只剩 `put_upload` 的半邊。
- `test_aws_launch.py` 裡任何斷言 `CLOUD_JOB_KINDS` 的 AWS 元組恰為四個值的測試：改成含 `clean_work`（與 aws-upload 合併後再加 `put_upload`，兩者的順序以先合併的為準）。
- Google 的 `test_station_clean_gcb.py`（含 159-160 行對 `ls`／`rm` argv 的斷言與 501 行的禁字清單）、`test_cleanup_confirm.py`、`test_byte_channel_b.py:763` 一個字都不准動。
- 以上名稱與行號取自對 aws-launch 計畫的閱讀與 grep，executor 開工前要確認它們在合併後的 v3 真的存在、叫這個名字。

## 完成標準（done when）
- 上面 22 條測試全綠，且執行前確認過它們是紅的（先在沒改程式的分支跑一次，紅的記進 ledger）。
- 整個 `platform/tests` 套件全綠，Google 清理與確認相關測試不改任何斷言。已知環境紅燈 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 視同綠。
- 手動差異檢查（範圍、既有測試未被改弱、`clean.py` 以外沒有 `rm` 字樣）記在 ledger，不列為 TC。
- 真實刪除 S3 資料不屬完成標準（C 級：動雲端資料）；若之後要試，維護者另外點頭，並只對測試用的 bucket 與前綴。

## 環境事實
- AWS run 的資料夾是 `<storage_root>/_aws_runs/<run>`，裡面的 `head.pid` 存 pid；內容包檔案有 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`aws.config`、`head.sh`（aws-launch 設計，合併後才有）。
- work 在 `s3://<workDir>/runs/<run>/work`，results 在 `s3://<workDir>/runs/<run>/results`（aws-launch 設計）。
- 憑證：`AWS_SHARED_CREDENTIALS_FILE`＋`AWS_PROFILE=default`，檔案位置 `ABF_STATION_AWS_CREDENTIALS`，預設 `<部署資料夾>/_personal/aws-credentials`（`aws_preflight.py:34-40`，aws-ce-type 新增）。
- Google 版刪除只有一次 `gcloud storage rm --recursive` 前面加一次唯讀 `ls --recursive`，且檢查每一行都以 `work/` 網址開頭（`clean.py` 217-235）；AWS 版照做。
- `aws s3 rm`／`s3 ls`／`s3api list-objects-v2` 的官方文件本計畫**沒有讀過**，上面的指令形狀是對照 Google 版推出來的設計，不是已驗證的事實。

## 不做
- 不刪 results、不刪 bucket、不刪 `uploads/`、不刪其他 run、不處理物件舊版本與刪除標記。
- 不做排程式自動清理、不做 S3 生命週期規則、不做費用估算（C-3）。
- 不改確認機制本身、不改網頁檔案、不新增 MCP 工具。
- 不用 boto3，不用 `s3api delete-objects`，不用 `--include`／`--exclude` 縮小範圍。
- 不重做 cloud-cleanup 已有的 migration、`offer_cleanups` 指令。

## 不確定的地方（需要維護者或執行者查證）
1. `aws s3 ls --recursive` 與 `s3api list-objects-v2` 哪個輸出好解析、有沒有 1000 筆分頁的問題：work 前綴下物件可能很多，只讀到第一頁就判斷「全部以 work/ 開頭」是不夠的；`aws s3` 高階指令會自動分頁，`s3api` 預設也會，但要讀文件確認。
2. 版本控管開著的 bucket：`aws s3 rm --recursive` 只加刪除標記、舊版本仍在、仍收費。要不要在文件寫明，並在清理畫面提醒？這個行為本計畫未驗證。
3. 前綴結尾斜線的語意：`rm s3://b/runs/r/work/ --recursive` 是否只匹配 `work/` 底下，而不會吃到 `work2/`；列舉那一步的鍵檢查是第二道保險，仍要保留。
4. 清理的時機：Google 版要求 run 成功才提出；AWS 是否同樣只在成功時？（計畫沿用，若維護者想失敗的也清，是另一個任務。）
5. `head.pid` 在 AWS 的意義是否與 Google 完全相同（aws-launch 的 `_cancel_head`）；合併後以實際為準。
6. 刪除的 API 費用與請求次數很小，但仍屬雲端操作；是否要在確認畫面提一句「會產生少量 S3 請求費」？
7. 與 aws-upload 的接力順序：若維護者要先做 clean，上面「必須更新的既有斷言」第一條要換手。

## 裁決

（developer-agent 2026-10-28 裁決，executor 與 verifier 照此辦）
1. AWS CLI 語意：executor 開工前必讀 AWS CLI 官方參考（s3 cp／ls／rm、s3api head-object／list-objects-v2），把頁面網址與用到的旗標寫進進度帳本；計畫的指令形狀與官方不符時以官方為準，帳本記一行。測試一律用假的 run_fixed／start_fed，不連真的 AWS。
2. 接力順序：aws-upload 先、aws-clean 後；各自在前一件合進 v3 後才開工，開工時用 `git show origin/v3:` 重查 aws-launch 合併後的實際名字與行號。
3. 串流上傳上限沿用 Google 版數值；官方文件寫明更低限制才調低，帳本註明出處。
4. 列舉必須讀完所有分頁才判斷「全部以 runs/<run>/work/ 開頭」；要有一條測試「第二頁出現鄰居前綴 → 整個拒絕」。
5. bucket 版本控管：不處理舊版本；只在 docs/PLATFORM.md 補一句「bucket 若開了版本控管，清理後舊版本仍佔空間、仍收費」。清理畫面文字不改。
6. big_file_command 的 AWS 版、使用者端 AWS 登入說明：不在範圍，既有行為不變。
7. clean_work 提出時機沿用 Google 版（只在 run 成功時）。
8. B 級：verifier 通過＋CI 綠由 developer-agent 自合。
- （2026-10-28 14:57 補）上面第 3、6 條是 aws-upload 的事，誤貼進這份，對本任務不適用，verifier 不必為它們出題。aws-upload 的最終裁決見 `aws-upload.md`：大檔指令的 AWS 版已在範圍內，SEQERA_PARITY 的 AWS 列會改成 `Have (create + check + launch + cancel + upload); clean in aws-clean`。本任務開工時以合併後的 v3 為準，把那句改成含 clean。
- **E 段（10-28 18:20 developer-agent，回應 verifier 合約退回；與上文衝突時以 E 段為準）**
  - E1 路徑：上文「`platform/abf_platform/build.py`」一律讀作 **`platform/abf_launch/build.py`**（`prepare_clean`、`clean_work_path`、`clean_screen`、`is_gcb`／`is_aws` 都在那裡）。准改的只有這一個 `abf_launch/` 檔；`abf_launch/` 其他檔不准動。
  - E2 必須更新的既有斷言（完整清單，取代上文那節；以下以外的既有斷言一律不准動，PR 逐條寫以前／以後／理由）：
    (a) `test_aws_upload.py`：130（AWS 元組不含 clean_work → 改為含）、149-157 `test_clean_work_still_refused_for_aws`（改成 AWS 的 clean_work 可排隊，或移除並由新測試取代）、550 `test_clean_work_of_an_aws_run_is_refused_by_the_agent_and_starts_nothing`（同上）、754-756（`aws-clean` 字樣與 SEQERA 舊句 → 新句）。
    (b) `test_aws_launch.py`：915-921（從「必須被拒」清單拿掉 clean_work，連同 TC-108 那行）、932 附近若把 clean_work 當拒絕對象也一併改、963-978（clean_work 改成可排隊、`run_clean` 對 AWS 不再拒）、1225（SEQERA 新句）。
    (c) `test_aws_ce.py`：655-663（清單只剩 list_site_files；訊息斷言改成「尚未支援」且不得含 aws-upload／aws-clean 字樣）、829-844（clean_work 不再因類型被拒；`msgs["launch"]` 的 `aws-clean` 斷言改成新訊息該有的字）、927（SEQERA 新句）。
    開工時用 `git show origin/v3:` 確認行號；行號漂移但內容相同照改，冒出清單外會紅的斷言 → 回報 BLOCKED，不自行改。
  - E3 SEQERA_PARITY 的 AWS 列確切新字串：`| AWS Batch (`awsbatch-platform`) | Have (create + check + launch + cancel + upload + clean) | [ ] |`（第 84 行附近那句 Pre-flight 說明不動）。
  - E4 `jobs.py:111-113` AWS 拒絕訊息拿掉「clean comes later in aws-clean (清理在之後的 aws-clean)」，改成只說「this job kind is not built for it yet (尚未支援)」，與 Google 句同形。
  - E5 呼叫數：接受 verifier 解讀——步驟 1–6 就停的案例總呼叫數 0；步驟 7 以後才停的案例「沒有任何列舉／刪除呼叫」，head 還活著時沒有任何 aws 呼叫。
  - E6 列舉：用會自動分頁的單一列舉呼叫（`aws s3 ls --recursive` 或 `s3api list-objects-v2` 不帶 `--max-items`，由 CLI 自動分頁），一次列舉＋一次 rm。裁決 4 的「第二頁出現鄰居前綴」測試改寫成「列舉輸出很長、鄰居鍵出現在後段（第 1001 行以後）→ 整個拒絕、不呼叫 rm」。
  - E7 環境變數：沿用 aws-upload TC-043 判法（允許 `AWS_PAGER`、`AWS_EC2_METADATA_DISABLED`、`AWS_CA_BUNDLE`；禁止金鑰類 `AWS_*` 與所有 `ABF_*`）。
  - E8 rm 旗標恰為 `--recursive` 與 `--region <區域>`，其他旗標一個都不准。
  - E9 畫面：AWS 畫面印帶結尾斜線的前綴 `s3://…/work/`；「永久刪除」即算說明無法復原，不必逐字「刪除無法復原」；Google 畫面一字不變。
  - E10 workDir：與 Google 同一公式 `<workDir>/runs/<run>/work`；workDir 帶子目錄（如 `s3://lab-bucket/work`）就照字面接上（→ `s3://lab-bucket/work/runs/r1/work`），要一條測試釘住這個情況，前綴核對以 bucket＋整段前綴為準。
  - E11 測試條數以合約 TC 為準，「22 條」只是下限。
  - E12 真實輸出格式：假 bucket 照官方文件的輸出格式寫（帳本附網址）；真實解析屬 C 級實跑，驗收列 UNVERIFIED(needs human)。

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
