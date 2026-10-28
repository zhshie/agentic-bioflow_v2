---
id: aws-upload
title: 把使用者的輸入檔上傳到 AWS Batch 環境的 S3 workDir bucket（對應 Google 版 cloud-upload 的 put_upload）
tier: B
kinds: backend
lane: L2-platform-ce
after: aws-launch merged into v3
branch: feat/aws-upload
base: v3（aws-launch 合併後）。本檔行號取自 origin/v3 9f6c8d2；aws-ce-type／aws-launch 才會新增或搬動的名字標「合併後才有」，executor 開工前用 `git show origin/v3:<檔>` 重查行號，不對就以實際內容為準
source: memory/dev-plans/cloud-upload.md（Google 版，已合併）；memory/dev-plans/aws-launch.md（裁決 A3：AWS 的 upload 與 clean 先關閉，分成 aws-upload／aws-clean 兩件）
---

# aws-upload

> 本檔由 developer-agent 的 subagent 寫（2026-10-28），只有計畫、沒有程式。B 級 → verifier 通過＋CI 綠由 developer-agent 自合。
> **與 aws-clean 動到同一批檔案，兩件必須接力、不可平行**（見「範圍：檔案」最後一段）。建議先 aws-upload、再 aws-clean。

## 目標
使用者在網頁選一個 AWS Batch 環境、挑一個本機檔案按「上傳」，檔案會經平台主機上的站台代理串流進 `s3://<workDir 的 bucket>/uploads/<owner>/` 底下，成為可登記成資料集的雲端位置，之後 launch 可以用它當輸入。行為與 Google 版逐項對應，Google 版的行為與輸出一個字都不變。

為什麼這樣切：
1. 沿用 Google 版三層，不另做一套：①平台側位置語言與資料集登記（`cloud_store.py`、`datasets.py` 的 `destination`）②`put_upload` job 與站台代理的串流寫入（`put_upload.py`、`jobs.enqueue_put_upload`）③超過上限時給使用者的自己上傳指令（`big_file_command`）。
2. 平台不碰 AWS：平台程式沒有雲端函式庫、不呼叫 aws；真正執行 `aws` 的只有 `abf_station/`，而且走固定指令執行器（`site.run_fixed`／`site.start_fed`，`shell=False`，無 boto3）。
3. 憑證只經 `AWS_SHARED_CREDENTIALS_FILE` 加 `AWS_PROFILE=default`（aws-ce-type 補充 8–13、aws-launch A1），不用金鑰環境變數。

## 維護者原話（verifier 出題用）
- 「4. 四種計算環境都建：nano4 → Google Batch → AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（`memory/PLAN-abf-v3-replan-2026-10.md` 第 40 行）→ 上傳是「資料集」這一層，掛在已建好的環境與憑證名字上，不另要使用者輸入金鑰。
- aws-launch 裁決 A3（維護者採納）：AWS 的 clean 與 upload 在各自的任務完成前維持關閉。→ 本任務完成後 `put_upload` 對 AWS 才打開，`clean_work` 仍關（直到 aws-clean）。
- ADR 0010：聊天工具與個人存取權杖沒有上傳工具。→ AWS 也不新增任何 MCP 工具；上傳只經網頁的「上傳」按鈕。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/cloud_store.py`：位置語言加 `s3://`。新增 `parse_s3`（同 `parse_gs` 的形狀）；`workdir_bucket`（現行第 50-61 行，只認 `PLATFORM_HOST_TYPES` 與 `gs://`）改成也認 AWS 環境與 `s3://`，並新增 `workdir_scheme(state, ce_name)`；`upload_prefix`（70）、`object_url`（78）、`inside_prefix`（83）加關鍵字參數 `scheme="gs"`（預設值保證 Google 呼叫不變）；`big_file_command`（95-98）依 scheme 給 `aws s3 cp` 版。
- `platform/abf_platform/datasets.py`：`draft_samplesheet`／`check_web_upload`／`register_dataset` 已有的 `destination=None` 關鍵字，內部的 `_cloud_target` 認得 `s3://`。**不准新增公開函式、不准加新參數名**（TC-063 釘死公開函式清單）。注意 TC-059/061/078/085/081 的禁字（`open(`、`hashlib`、`\bsha\d*`、`subprocess`、`confirm`、`queue`、`submit`、`jobs` 等），註解與變數名也不能含。
- `platform/abf_platform/jobs.py`：`put_upload` 的放行改走逐型別表（見作法 1）；`enqueue_put_upload`（現行 232 起，aws-ce-type 後約 235）與 `_uploaded_file`（218-229）的 Google 專屬文字改成依環境類型選；`put_upload` 結果處理（約 940）若寫死 `gs://` 要一併改。
- `platform/abf_platform/compute_envs.py`：`CLOUD_JOB_KINDS` 的 AWS 元組加 `"put_upload"`（只加這一個字串）。
- `platform/abf_station/put_upload.py`：`_transfer`（168 起）依環境類型分流，新增 `_transfer_aws`；`_cloud_size`（119）新增 AWS 版。
- `platform/abf_station/handlers.py`：只有在 `put_upload` 的 `ARGS` 驗證需要放寬 `dest` 開頭時才改；能不改就不改。
- 新檔：`platform/tests/test_aws_upload.py`（檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，TC-070）。
- 文件：`docs/PLATFORM.md`、`docs/SEQERA_PARITY.md`、`docs/TESTING.md` 各加或改 AWS 上傳的段落（與 aws-launch 同樣的三份）。
- **不准碰**：`web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`、`clean.py`、`build.py`（那是 aws-clean 的）。
- **與 aws-clean 重疊**：兩件都會改 `jobs.py`、`compute_envs.py` 的 `CLOUD_JOB_KINDS` 同一行 AWS 元組、`docs/PLATFORM.md`／`SEQERA_PARITY.md`／`TESTING.md`，以及 `test_aws_launch.py` 裡「AWS 的 put_upload／clean_work 被拒」的斷言。所以必須接力：後一件開工前先 rebase 到前一件合併後的 v3，不可同時各自改同一行。

## 作法
1. **逐型別放行，不新增共用元組。** aws-launch 已把「是否放行」做成 `CLOUD_JOB_KINDS` 逐型別表（AWS 目前是 `("preflight","launch_nextflow","cancel_run","pipeline_files")`）。本任務只在 AWS 那一格加 `"put_upload"`，並把 `jobs.py` 現行「`put_upload` 只給 Google」的寫死判斷改成查這張表。`clean_work` 不加。`put_upload` 仍要求環境 `available`（與 Google 版一致，現行 126 行）。
2. **位置語言。** 上傳位置是 `s3://<bucket>/uploads/<owner>/<name>`，bucket 取自環境的 `workDir`（與 `runs/` 同一個 bucket、不同前綴，沿用 cloud-upload 裁決）。`inside_prefix` 必須擋 `..`、空段、前綴撞名（`uploads/alice2/` 不屬於 `uploads/alice/`）。
3. **站台代理重新判斷全部**（不信平台）：`dest` 必須等於重算出的 `object_url`；`size` 在 1..2 GB；暫存檔在 `<ABF_STATION_UPLOADS>/<owner>/`，用 `O_NOFOLLOW` 開、是一般檔案、大小一致。這幾項直接沿用 Google 版的函式，不複製。
4. **串流。** `site.start_fed(["aws","s3","cp","-",dest,"--region",region])`，用既有 `cloud_store.stream_into` 餵資料。2 GB 以下不需要 `--expected-size`（那只在超過 50 GB 才需要；官方文件 `https://docs.aws.amazon.com/cli/latest/reference/s3/cp.html`，執行者開工前要讀一遍確認；本計畫沒有驗證 stdin 串流在 2 GB 的記憶體行為）。環境變數用 aws-launch 合併後的共用函式（`aws_preflight` 的 `_aws_env` 或 aws-launch 抽出的 `_plain_env`，名字以合併後為準）：只帶 `AWS_SHARED_CREDENTIALS_FILE`、`AWS_PROFILE=default`、`AWS_CONFIG_FILE=os.devnull`、`AWS_DEFAULT_REGION`，其餘 `AWS_*`、`ABF_*` 一律剝掉。憑證路徑用 `aws_preflight.credentials_path(settings_file)`。
5. **驗大小。** 傳完後 `aws s3api head-object --bucket B --key K --query ContentLength --output text` 比對大小，相符才刪暫存檔（`_remove` 照舊檢查 dev/ino）。`head-object` 的官方文件本計畫沒讀過，**查不到**，執行者必須先讀 `https://docs.aws.amazon.com/cli/latest/reference/s3api/head-object.html` 再寫。
6. **資料集登記。** 不做 migration：是不是雲端路徑看 `path` 開頭是 `gs://` 或 `s3://`。一個資料集的所有檔案必須同一 scheme；`s3://` 與 `gs://`、本機路徑混在一起，拒絕並說明。
7. **超過上限的指令。** `big_file_command` 的 s3 版是 `aws s3 cp <你電腦上的資料夾> s3://<bucket>/uploads/<owner>/rawdata/ --recursive`，文字要寫明「這要在你自己的電腦上、用你自己的 AWS 登入執行，平台不會代你上傳」。
8. 平台程式碼不得出現「station」字樣（TC-061），寫「平台主機上的代理」；不得出現 `subprocess`、`threading`、雲端函式庫字樣（TC-071、TC-083/114/085）。

## 失敗先行測試（`platform/tests/test_aws_upload.py`，現在全紅；全部用假的 `site.run_fixed`／`site.start_fed`、`tmp_path` 當 `storage_root` 與暫存目錄，不碰網路、不呼叫真 aws、不花錢；測試輸入一律假的：`lab-bucket`、`eu-west-1`、`aws-lab`、`alice`、`bob`。憑證相關鍵名用字串相加組出來，避免被 `credentials_stay_in_settings_test.sh` 掃到）
1. `test_aws_env_may_queue_put_upload_when_available`：`available` 的 AWS 環境可以 `enqueue_put_upload`；非 `available` 被拒，訊息說環境還不能用。
2. `test_put_upload_gate_is_a_per_type_table_not_a_shared_tuple`：`CLOUD_JOB_KINDS` 裡 AWS 含 `put_upload`、不含 `clean_work`；Google 那格六個值與修改前完全相同。
3. `test_clean_work_still_refused_for_aws`：AWS 環境排 `clean_work` 仍被拒（這是 aws-clean 之前的保證）。
4. `test_workdir_bucket_for_aws_is_the_s3_bucket`：AWS 環境 `workdir_bucket` 回 `lab-bucket`；`workdir_scheme` 回 `s3`。
5. `test_workdir_bucket_for_google_is_unchanged`：Google 環境兩個函式的回傳與修改前相同（逐字）。
6. `test_s3_object_url_is_inside_the_owners_prefix`：`object_url` 在 `s3://lab-bucket/uploads/alice/` 底下；`inside_prefix` 對 `uploads/alice2/x`、`uploads/alice/../bob/x`、`uploads//x` 都回假。
7. `test_agent_streams_into_aws_s3_cp_with_fixed_argv`：假 `start_fed` 收到的 argv 恰為 `["aws","s3","cp","-",dest,"--region","eu-west-1"]`；沒有 shell、沒有 `--expected-size`。
8. `test_agent_env_has_only_the_credentials_file_and_profile`：傳給 `start_fed` 的 env 含 `AWS_SHARED_CREDENTIALS_FILE`（指到假憑證檔）、`AWS_PROFILE=default`、`AWS_CONFIG_FILE`＝`os.devnull`；測試先在父行程塞金鑰類 `AWS_*` 與 `ABF_X` 假值，env 裡不得出現。
9. `test_agent_rejudges_dest_and_refuses_a_foreign_prefix`：`dest` 指到 `s3://lab-bucket/runs/x`、別的 bucket、別人的 `uploads/bob/` 都拒，假 `start_fed` 一次都沒被呼叫。
10. `test_size_is_checked_with_head_object_before_the_staged_file_goes`：假 `run_fixed` 對 `head-object` 回不同大小 → 結果是失敗、暫存檔仍在；回相同大小 → 成功、暫存檔被刪。
11. `test_missing_credentials_file_fails_without_leaking_its_content`：憑證檔不存在 → 失敗訊息可含路徑（補充 8–13 的唯一例外），但不含任何金鑰值。
12. `test_symlinked_or_resized_staged_file_is_refused`：暫存檔是符號連結、或大小與 `size` 不符 → 拒，`start_fed` 未被呼叫。
13. `test_dataset_destination_s3_registers_s3_paths`：`register_dataset(destination=<AWS 環境>)` 寫入的 `path` 以 `s3://lab-bucket/uploads/alice/` 開頭。
14. `test_mixed_schemes_in_one_dataset_are_refused`：同一資料集混 `s3://` 與 `gs://`、或混本機路徑 → 拒並說明。
15. `test_over_limit_file_gets_the_aws_command_and_a_plain_warning`：大於 2 GB 的暫存檔 → 訊息含 `aws s3 cp` 指令與「在你自己的電腦上、用你自己的 AWS 登入」。
16. `test_no_cloud_library_and_no_station_word_in_platform_sources`：掃 `abf_platform/` 新舊檔，無 `boto3`／`botocore`／`google`／`azure` 匯入、無 "station" 字樣、無 `subprocess`。
17. `test_no_mcp_upload_tool_exists`：MCP 工具清單沒有任何 upload 字樣的工具（ADR 0010）。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
- `test_aws_launch.py` 的 `test_put_upload_and_clean_work_jobs_cannot_be_queued_for_aws`：拆成「`clean_work` 仍被拒」，`put_upload` 那半移除（上面第 3 條取代）。
- `test_aws_launch.py` 的 `test_cloud_store_stays_google_only`：改為「Google 行為不變、AWS 認得 s3」（第 4、5 條取代）。
- `test_aws_launch.py` 的 `test_a_dataset_destination_cannot_be_an_aws_environment`：改為 AWS 可當 destination（第 13 條取代）。
- `test_cloud_upload.py:453` 的 `test_workdir_bucket_needs_a_google_batch_environment`：名字與斷言改成「需要 Google 或 AWS 的雲端環境，Slurm 與其他仍被拒」。
- 其餘 `test_cloud_upload.py`、`test_byte_channel_a.py:400` 的 Google 指令斷言一個字都不准動。
- 以上名稱與行號取自對 aws-launch 計畫的閱讀與 grep，executor 開工前要確認它們在合併後的 v3 真的存在、叫這個名字。

## 完成標準（done when）
- 上面 17 條測試全綠，且執行前確認過它們是紅的（先在沒改程式的分支跑一次，紅的記進 ledger）。
- 整個 `platform/tests` 套件全綠，Google 相關測試（`test_cloud_upload*.py`、`test_byte_channel_*`、`test_station_*`）不改任何斷言。已知環境紅燈 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 視同綠。
- 手動差異檢查（範圍、既有測試未被改弱）記在 ledger，不列為 TC。
- 真實 AWS 上傳不屬完成標準（會花錢，C 級；維護者另外點頭、先設好 AWS Budgets 警示）。

## 環境事實
- AWS 憑證：`AWS_SHARED_CREDENTIALS_FILE`，檔內只用 `[default]`；站台代理的檔案位置來自 `ABF_STATION_AWS_CREDENTIALS`，預設 `<部署資料夾>/_personal/aws-credentials`（aws-ce-type 新增，`aws_preflight.py:34-40`）。
- 站台代理對外的唯一出口是 `site.run_fixed`／`site.start_fed`；不得新增另一條 `subprocess` 路徑。
- Google 路徑有真實驗證；AWS 的 `aws s3 cp -`、`s3api head-object` 官方文件本計畫沒有讀（aws-launch 同樣標「查不到」），一律以執行者開工前讀到的為準。
- 環境設定鍵：`region`、`workDir`（`s3://`）、`jobQueue`、`spot`、`maxvCpus`；舊的 `headQueue`／`computeQueue` 會被拒。

## 不做
- 不做 S3 刪除（aws-clean）、不做費用估算（C-3）、不做續跑。
- 不新增 MCP 上傳工具、不改網頁檔案。
- 不用 boto3，不用 `s3 sync`、`--acl`、presigned URL、瀏覽器直傳。
- 不做跨環境搬資料（把 Google 上傳的檔案搬到 S3）。
- 不開放 AWS 環境的 `list_site_files`。

## 不確定的地方（需要維護者或執行者查證）
1. `aws s3 cp -` 串流 2 GB 的記憶體與逾時行為：官方文件未讀，執行者要先讀；若有問題，上限要不要降到比 Google 低？
2. bucket 版本控管（versioning）開著時，上傳覆寫同名檔會留下舊版本、持續收費；要不要建議在 `uploads/` 前綴設生命週期規則？（本任務只在文件寫建議，不自動設。）
3. `big_file_command` 的目的地：Google 版指到 `rawdata/`，AWS 版是否同樣用 `uploads/<owner>/rawdata/`？使用者端怎麼登入 AWS 也要寫進說明。
4. bucket 命名規則是否直接重用 aws-ce-type 的 `_AWS_BUCKET`，還是 `cloud_store` 自己再定一份？傾向重用，避免兩處不一致。
5. 暫存目錄 `ABF_STATION_UPLOADS` 與 Google 共用、不分 scheme 是否可行？
6. 與 aws-clean 的接力順序：若維護者希望先做 clean，「必須更新的既有斷言」前兩條要換手。

## 裁決

（developer-agent 2026-10-28 裁決，executor 與 verifier 照此辦）
1. AWS CLI 語意：executor 開工前必讀 AWS CLI 官方參考（s3 cp／ls／rm、s3api head-object／list-objects-v2），把頁面網址與用到的旗標寫進進度帳本；計畫的指令形狀與官方不符時以官方為準，帳本記一行。測試一律用假的 run_fixed／start_fed，不連真的 AWS。
2. 接力順序：aws-upload 先、aws-clean 後；各自在前一件合進 v3 後才開工，開工時用 `git show origin/v3:` 重查 aws-launch 合併後的實際名字與行號。
3. 串流上傳上限沿用 Google 版數值；官方文件寫明更低限制才調低，帳本註明出處。
4. （作廢：原第 4、5、7 條誤貼自 aws-clean，對本任務不適用，verifier 不必出題。）
5. bucket 版本控管：本任務只在 docs/PLATFORM.md 的 AWS 上傳段補一句「bucket 若開了版本控管，覆寫同名檔會留下舊版本、仍收費」。
6. **big_file_command 的 AWS 版在範圍內**，以本文作法 7 與測試 15 為準（取代原裁決 6）。目的地用 `s3://<bucket>/uploads/<owner>/rawdata/`；文字只寫「在你自己的電腦上、用你自己的 AWS 登入執行」，不教怎麼登入 AWS（登入說明另案）。verifier 的 TC-082～085 有效。
7. 交付範圍：本任務交付的是動作層＋站台代理＋文件，**沒有可按的網頁按鈕**——目前 Google 版也沒有網頁或 MCP 呼叫 `enqueue_put_upload`，網頁入口屬前端 session 的車道，另案。PR 說明與 PLATFORM.md 照實寫「網頁入口尚未接上」。目標段「使用者在網頁按上傳」改讀為「網頁接上後」。
8. B 級：verifier 通過＋CI 綠由 developer-agent 自合。

（developer-agent 2026-10-28 14:55 補裁決 A1–A6，回應 verifier 合約階段的阻擋）
- **A1 路徑更正**：範圍清單的 `platform/abf_platform/datasets.py` 是筆誤，實際是 `platform/abf_platform/actions/datasets.py`（`_cloud_target`）。規則照舊：不准新增公開函式與參數名。
- **A2 `workdir_scheme` 的形狀**：簽名是 `workdir_scheme(ce)`，吃已取得的環境 dict，與 `workdir_bucket(ce)` 對稱，不開資料庫、不連線。回 `"gs"` 或 `"s3"`；其他平台丟 `CloudPathError`。測試 4 照此寫。`workdir_bucket(ce)` 對 AWS 認 `s3://` 開頭的 `workDir`；Google 的回傳與錯誤訊息逐字不變。錯誤訊息裡「只有 Google Batch 環境可以」要改成同時提到 AWS Batch，這是對既有斷言的有意更新，也列進下面的 A3。
- **A3 必須更新的既有斷言再加這幾條**（PR 說明逐條寫以前／以後／理由，其餘照舊不准動）：
  - (a) `test_aws_launch.py` 的 `test_aws_environment_accepts_exactly_preflight_launch_cancel_and_pipeline_files`：以前，AWS 可排的種類是 preflight／launch／cancel／pipeline_files，put_upload 被拒。以後多一個 put_upload；clean_work 仍被拒，訊息仍含 `aws-clean`。理由是本任務本來就要打開 put_upload。
  - (b) `test_aws_ce.py` 的 `test_jobs_other_than_the_preflight_are_refused_in_plain_words`：從迴圈中移除 `put_upload`，其餘種類照舊。
  - (c) `test_aws_ce.py` 的 `test_no_new_write_path_for_aws`：put_upload 改為允許，但其他寫入路徑照舊禁止。允許的唯一出口是 `site.start_fed`／`site.run_fixed`，由新測試 7、16 把關。
  - (d) SEQERA_PARITY.md 的 AWS 列改成 `Have (create + check + launch + cancel + upload); clean in aws-clean`。`test_aws_ce.py:927` 與 `test_aws_launch.py:1228` 的逐字比對跟著換成這句。
  - (e) `test_workdir_bucket_needs_a_google_batch_environment` 的錯誤訊息比對（若有逐字比對）跟著 A2 的新訊息換。
  - 行號以開工時 `git show origin/v3:` 為準；名字找不到就在帳本記一行，不自己猜著改別的測試。
- **A4 head-object 失敗**：跟 Google 版的 `_cloud_size` 失敗處理一致。executor 先讀 `put_upload.py` 的 Google 分支，照它的語意做（若 Google 是「成功但沒核對、暫存檔保留」，AWS 也一樣），並在帳本寫一行「Google 版的行為是 X，AWS 照做」。不變的底線：大小沒核對相符，就不刪暫存檔（TC-061）。
- **A5 平台主機沒裝 aws、或 aws 無法啟動**：結果是失敗，訊息用白話寫「平台主機上找不到 aws 指令，請管理者安裝 AWS CLI」，暫存檔保留，不露出堆疊。要加一條測試：假的 `start_fed` 丟 `FileNotFoundError`，就得到這個結果。
- **A6 環境變數**：沿用 `aws_preflight._aws_env`（含 `AWS_PAGER`、`AWS_EC2_METADATA_DISABLED`、保留 `AWS_CA_BUNDLE`）。不另做一份，也不要求剛好四個變數；TC-043 的「金鑰類 AWS_*、ABF_* 不出現」照舊。
- **A7 jobs.py 的 AWS 拒絕訊息**：clean_work 的訊息改成只提 `aws-clean`（例「clean comes later in aws-clean」），仍要含「尚未支援」。
- verifier 補寫的禁字 TC（TC-114、TC-090），照收。

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
