---
id: azure-upload
title: 把使用者的輸入檔上傳到 Azure Batch 環境的 Blob workDir 容器（對應 AWS 版 aws-upload、Google 版 cloud-upload 的 put_upload）
tier: B
kinds: backend
lane: L2-platform-ce
after: azure-launch merged into v3
branch: feat/azure-upload
base: v3（azure-launch 合併後）。本檔行號取自 origin/v3 796f971（azure-ce-type 已合、azure-launch 未合）；azure-launch 才會新增或搬動的名字標「合併後才有」，executor 開工前用 `git grep -n <名字> origin/v3` 重查行號，不對就以實際內容為準（azure-launch 裁決 10 同法）
source: memory/dev-plans/aws-upload.md（AWS 版，已合併）；memory/dev-plans/cloud-upload.md（Google 版，已合併）；memory/dev-plans/azure-launch.md（azure-launch 的「不做」把 Blob 上傳、`cloud_store` 的 `az://` 解析、資料集 destination 留給本件）
---

# azure-upload

> 本檔由 developer-agent 的 subagent 寫（2026-10-28），只有計畫、沒有程式。B 級 → verifier 通過＋CI 綠由 developer-agent 自合。
> **與 azure-clean 動到同一批檔案，兩件必須接力、不可平行**（見「範圍：檔案」最後一段）。順序：azure-launch → azure-upload → azure-clean。
> **前提：azure-launch 尚未合進 v3。** 本檔假設它的設計照 `memory/dev-plans/azure-launch.md`（含「developer-agent 裁決」）實現。開工時若實際合併結果與此不同，以合併後的 v3 為準，帳本記一行。

## 目標
使用者（網頁接上後）選一個 Azure Batch 環境、挑一個本機檔案按「上傳」，檔案會經平台主機上的站台代理，用 `az storage blob upload` 寫進 `az://<workDir 的容器>/uploads/<owner>/` 底下，成為可登記成資料集的雲端位置，之後 launch 可以用它當輸入。行為與 AWS 版逐項對應，Google 版與 AWS 版的行為與輸出一個字都不變。

為什麼這樣切：
1. 沿用既有三層，不另做一套：①平台側位置語言與資料集登記（`cloud_store.py`、`actions/datasets.py` 的 `destination`）②`put_upload` job 與站台代理的寫入（`put_upload.py`、`jobs.enqueue_put_upload`）③超過上限時給使用者的自己上傳指令（`big_file_command`）。
2. 平台不碰 Azure：平台程式沒有雲端函式庫、不呼叫 `az`；真正執行 `az` 的只有 `abf_station/`，而且走固定指令執行器（`site.run_fixed`／`site.start_fed`，`shell=False`，無 Azure SDK）。
3. 憑證只經環境變數交給 `az`（`AZURE_STORAGE_KEY` 或 `AZURE_STORAGE_SAS_TOKEN`），來源是站台代理的憑證檔，**金鑰不進 argv、不寫進任何檔案**（azure-launch 裁決 2 同樣的規則）。

### Azure 與 AWS 的差異（先講結論，後面各節照此）
| 項目 | AWS（已合） | Azure（本件） |
|---|---|---|
| 位置語言 | `s3://<bucket>/uploads/<owner>/<name>` | `az://<container>/uploads/<owner>/<name>` |
| 寫入指令 | `aws s3 cp - <dest>`（stdin 串流） | `az storage blob upload`（官方是以檔案路徑為主；stdin 只有 Preview 的 `--data @-`，見待裁決 1） |
| 驗大小 | `aws s3api head-object … ContentLength` | `az storage blob show … --query properties.contentLength`（輸出形狀官方頁面沒寫，見待裁決 3） |
| 憑證交付 | `AWS_SHARED_CREDENTIALS_FILE`＋`AWS_PROFILE`（檔案路徑） | 環境變數 `AZURE_STORAGE_KEY`／`AZURE_STORAGE_SAS_TOKEN`＋`AZURE_STORAGE_ACCOUNT`（值本身在 env 裡，但只在子行程記憶體，不落地） |
| 設定目錄 | `AWS_CONFIG_FILE=os.devnull` | `AZURE_CONFIG_DIR` 指到每次呼叫新建的暫存資料夾（`azure_preflight._call` 同做法），用完刪 |
| 同名覆寫 | `s3 cp` 預設覆寫 | `--overwrite` 預設 false，要明寫 `--overwrite true` 才與 S3 對等（見待裁決 2） |
| 容器／bucket 規則 | `_AWS_BUCKET` | `compute_envs._AZURE_CONTAINER`（`^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]\Z`，且不准 `--`） |

## 維護者原話（verifier 出題用）
- 「4. 四種計算環境都建：nano4 → Google Batch → AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（`memory/PLAN-abf-v3-replan-2026-10.md` 第 40 行）→ 上傳是「資料集」這一層，掛在已建好的環境與憑證名字上，不另要使用者輸入金鑰。
- aws-launch 裁決 A3（維護者採納）：AWS 的 clean 與 upload 在各自的任務完成前維持關閉。→ Azure 同樣處理（azure-launch 把 upload 與 clean 都留關閉）；本任務完成後 `put_upload` 對 Azure 才打開，`clean_work` 仍關（直到 azure-clean）。
- ADR 0010：聊天工具與個人存取權杖沒有上傳工具。→ Azure 也不新增任何 MCP 工具；上傳只經網頁的「上傳」按鈕。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/cloud_store.py`：位置語言加 `az://`。新增 `parse_az`（同 `parse_s3` 的形狀，容器規則重用 `compute_envs._AZURE_CONTAINER` 並加不准 `--`，不另寫第二份）；`workdir_scheme(ce)` 加 `"az"` 分支；`workdir_bucket(ce)` 對 Azure 環境認 `az://` 開頭的 `workDir`，回容器名；`_parse` 的 pattern 依 scheme 選；`upload_prefix`／`object_url`／`inside_prefix` 的 `scheme` 關鍵字參數接受 `"az"`（Google、AWS 呼叫不變）；`big_file_command` 依 scheme 給 `az` 版。**禁字**：`test_cloud_upload.py:649`（TC-088）與 `test_aws_upload.py` 約 705 行（TC-090/115）會把 `cloud_store.py`／`actions/datasets.py` 全文轉小寫後掃 "azure"，所以這兩個檔裡 "Azure"／"azure" 一個字都不能出現：錯誤訊息用中性字（例「Blob 儲存體」「Batch 環境」）或把字拆成 `"az" "ure"`，變數與註解同理。同一組測試還禁 `open(`、`hashlib`、`subprocess`、`os.system`、`socket`、`urllib`、`httpx`、`requests`、`import google`、`boto3`、「station」。
- `platform/abf_platform/actions/datasets.py`：`_cloud_target`（約 115）、`_scheme`、`_wrong_scheme`、`_cloud_place`（目前兩路 `parse_s3`／`parse_gs`）、`check_web_upload`（約 215-236 的超限訊息）、`register_dataset`（約 278-338）加 `az` 分支。**不准新增公開函式、不准加新參數名**（TC-063 釘死公開函式清單）；TC-059/061/078/085/081 的禁字（`open(`、`hashlib`、`subprocess`、`confirm`、`queue`、`submit`、`jobs` 等）與上面的 "azure" 禁字，註解與變數名也不能含。
- `platform/abf_platform/jobs.py`：`_target`（約 95-135）的三處寫死文字——第 108-113 行「kind 不在 `CLOUD_JOB_KINDS[platform]` 就拒」的 AWS／Google 句、第 114-116 行 Azure 的「尚未支援送出；下一步 azure-launch」（azure-launch 會先改掉，合併後重查）、第 117-118 行「只有 Google Batch 或 AWS Batch 環境能放雲端資料」（要加上 Azure Batch）；`_uploaded_file`（約 218-238）的超限訊息加 az 版；`enqueue_put_upload`（約 241-262）呼叫 `cloud_store.workdir_scheme`／`object_url` 已是 scheme 化，確認 az 走得通；`put_upload` 結果處理（約 949，`path` 上限 1100）若寫死 `gs://`／`s3://` 要一併改。
- `platform/abf_platform/compute_envs.py`：`CLOUD_JOB_KINDS` 的 Azure 元組加 `"put_upload"`（只加這一個字串；azure-launch 合併後是四個，加完五個）。`clean_work` 不加。
- `platform/abf_station/put_upload.py`：`run_put` 依 `given.platform` 分流加 Azure（scheme `"az"`）；新增 `_transfer_az` 與 Azure 版 `_cloud_size`（`_aws_cloud_size` 的鏡像）。
- `platform/abf_station/azure_preflight.py`：**只准加一個** 上傳用的環境建構小函式（或在 `put_upload.py` 內重用 `_az_env`／`_read_shape`），能不動就不動；若 azure-launch 已抽出共用的 `_plain_env`，用它。
- `platform/abf_station/handlers.py`：只有 `put_upload` 的 `ARGS` 驗證需要放寬 `dest` 開頭時才改；能不改就不改。
- 新檔：`platform/tests/test_azure_upload.py`（檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，TC-070）。
- 文件：`docs/PLATFORM.md`、`docs/SEQERA_PARITY.md`、`docs/TESTING.md` 各加或改 Azure 上傳的段落（與 azure-launch 同樣的三份）。
- **不准碰**：`web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`、`clean.py`、`build.py`（那是 azure-clean 的）。
- **與 azure-clean 重疊**：兩件都會改 `jobs.py`、`compute_envs.py` 的 `CLOUD_JOB_KINDS` 同一行 Azure 元組、`docs/PLATFORM.md`／`SEQERA_PARITY.md`／`TESTING.md`，以及 `test_azure_launch.py` 裡「Azure 的 put_upload／clean_work 被拒」的斷言。所以必須接力：後一件開工前先 rebase 到前一件合併後的 v3，不可同時各自改同一行。

## 作法
1. **逐型別放行，不新增共用元組。** 只在 `CLOUD_JOB_KINDS` 的 Azure 那一格加 `"put_upload"`，`jobs.py` 沿用 aws-upload 已做好的「查表」判斷。`put_upload` 仍要求環境 `available`。`clean_work`、`resume` 對 Azure 仍拒（azure-clean 另案；launch 的續跑也仍拒）。
2. **位置語言。** 上傳位置是 `az://<container>/uploads/<owner>/<name>`，容器取自環境 `workDir` 的容器（與 `runs/` 同一個容器、不同前綴）。注意 `workDir` 必有子資料夾（`az://<container>/<subfolder>`，`compute_envs` 必檢），**上傳前綴不含這個子資料夾**——所以 `uploads/` 與 `<subfolder>/` 是同容器下的兄弟路徑，互不重疊。`inside_prefix` 必須擋 `..`、空段、前綴撞名（`uploads/alice2/` 不屬於 `uploads/alice/`），跨容器一律拒。
3. **站台代理重新判斷全部**（不信平台）：`dest` 必須等於重算出的 `object_url`；`size` 在 1..2 GB（沿用 `cloud_store.UPLOAD_LIMIT = 2_000_000_000`）；暫存檔在 `<ABF_STATION_UPLOADS>/<owner>/`，用 `O_NOFOLLOW` 開、是一般檔案、大小一致。這幾項直接沿用既有函式（`_area`、`_open`、`_remove`、`_cleaned`、`_fail`），不複製。環境重新判斷用 `azure_preflight.clean_environment(ce)`。
4. **寫入（預設方案，待裁決 1 可翻轉）。** `az storage blob upload` 官方描述是「Upload a file to a storage blob … with automatic chunking and progress notifications」，核心參數是 `--file/-f`（本機檔案路徑）。stdin 串流只有 `--data @-`（官方標 Preview，需配 `--length`），官方頁面沒寫 2 GB 的記憶體行為。預設方案：
   - 用 `site.run_fixed(argv, env, timeout=3600)`，argv 固定為 `["az","storage","blob","upload","--account-name",A,"--container-name",C,"--name",K,"--file",<暫存檔絕對路徑>,"--overwrite","true","--no-progress","--output","none"]`。`K` 是 `uploads/<owner>/<name>`；帳號 `A` 取自 `ce["storageAccountName"]`；**不傳 `--account-key`／`--sas-token`**（那會進 argv），一律走環境變數。
   - `--file` 會讓 `az` 自己重開路徑，與 AWS 版「站台代理自己開 fd 再串流」不同，多出一個檢查到使用之間的空窗（TOCTOU）。補法：呼叫前 `lstat` 一次（非符號連結、一般檔案、大小＝`size`、記下 dev/ino），呼叫後再 `lstat` 一次，dev/ino 或大小變了就當失敗、暫存檔保留。這個取捨寫進 PR 說明，由 verifier 判斷夠不夠。
   - 這條路徑不經 `_Sink`／`cloud_store.stream_into`，所以不做 AWS 版的「已送出位元組數」核對，改靠第 5 條的雲端大小核對。
5. **驗大小。** 傳完後 `site.run_fixed(["az","storage","blob","show","--account-name",A,"--container-name",C,"--name",K,"--query","properties.contentLength","--output","tsv"], env, timeout=60)`（`DESCRIBE_SECONDS`），比對 `int(stdout.strip())`。相符才刪暫存檔（`_remove` 照舊檢查 dev/ino）。`blob show` 的輸出形狀與 JMESPath 路徑官方頁面沒寫（`https://learn.microsoft.com/en-us/cli/azure/storage/blob?view=azure-cli-latest` 只列出參數），**查不到**，執行者必須先讀該頁 `az storage blob show` 一節；讀不到輸出範例就列入待裁決 3，不猜。核對失敗的語意照 aws-upload A4：`(TimeoutError, OSError)` 或解析不出數字 → 回 done 但訊息寫「已上傳…，但沒能核對雲端大小；暫存檔保留」；大小不符 → `_fail("雲端物件大小與本機不符，暫存檔保留，請重新上傳")`。不變的底線：大小沒核對相符，就不刪暫存檔。
6. **環境變數。** 重用 `azure_preflight._az_env`（它已剝掉所有 `ABF_*`、`AZURE_*`，再設 `AZURE_STORAGE_ACCOUNT`、`AZURE_STORAGE_KEY` 或 `AZURE_STORAGE_SAS_TOKEN`、`AZURE_CONFIG_DIR`、`AZURE_CORE_COLLECT_TELEMETRY=false`、`AZURE_CORE_NO_COLOR`、`AZURE_CORE_ONLY_SHOW_ERRORS`）。憑證檔：`ABF_STATION_AZURE_CREDENTIALS`，預設 `<部署資料夾>/_personal/azure-credentials`，`[default]` 段（`_read_shape`）。帳號金鑰與 SAS 都在時以帳號金鑰為準（azure-launch 裁決 2）。每次呼叫自建 `tempfile.mkdtemp` 當 `AZURE_CONFIG_DIR`，用完在 `finally` 刪（`azure_preflight._call` 同做法）。上傳不需要 `AZURE_BATCH_*`，是否剝掉見待裁決 5。**一定要明給金鑰或 SAS**：官方說兩者都沒有時 CLI 會試著用登入身分去查帳號金鑰，那在平台主機上會卡住或洩漏意外行為。
7. **平台主機沒裝 `az`、或無法啟動**（鏡像 aws-upload A5）：`FileNotFoundError` → 失敗，白話訊息「平台主機上找不到 az 指令，請管理者安裝 Azure CLI」，暫存檔保留，不露出堆疊。注意 `abf_station` 原始碼不准出現小寫 `\bazure\b`（`test_station_static.py:46` 逐行比對、大小寫敏感）：訊息中的 "Azure" 大寫可以過，但保險起見照 `azure_preflight` 的做法用 `"Az" "ure"` 拼接。
8. **資料集登記。** 不做 migration：是不是雲端路徑看 `path` 開頭是 `gs://`、`s3://` 或 `az://`。一個資料集的所有檔案必須同一 scheme；`az://` 與其他 scheme、本機路徑混在一起，拒絕並說明。`az://` 路徑的容器必須等於目的環境 `workDir` 的容器，否則拒。
9. **超過上限的指令。** `big_file_command` 的 az 版是 `az storage blob upload-batch --destination <container> --destination-path uploads/<owner>/rawdata/ --source <你電腦上的資料夾>`，文字要寫明「這要在你自己的電腦上、用你自己的 Azure 登入執行，平台不會代你上傳」。官方頁面確認 `upload-batch` 存在、`--destination/-d`、`--source/-s` 是容器與本機資料夾，**`--destination-path` 是否存在本計畫沒有核到**（待裁決 6），執行者必須先讀該頁再寫；指令字面在原始碼裡要拆開寫（像 s3 版 `"aws s3 " "cp …"`），原因見第 11 條。
10. 平台程式碼不得出現「station」字樣（TC-061），寫「平台主機上的代理」；不得出現 `subprocess`、`threading`、雲端函式庫字樣；`put_upload.py` 不得出現 `cloud_cost`（`test_aws_upload.py` 約 713-715）、`delete-object|s3 rm|s3 sync|--acl|presign`，也不得出現 `storage blob delete`（azure-clean 的事）。
11. **舊的禁令要先拆，否則自己的程式碼會被自己的測試擋下。** `test_azure_ce.py:884-891` 的 `test_no_launch_cost_or_upload_code_for_azure` 用一條正則掃 `abf_platform` 與 `abf_station` 全部原始碼，禁 `storage blob upload` 與 `azcopy` 等。本任務需要寫 `az storage blob upload`，所以必須有意地**縮窄**這條正則：拿掉 `storage blob upload`（與 `upload-batch`，若用到），保留 `storage blob delete`、`azcopy`、`batch pool create/delete/resize`、`storage container create`、`az batch job/task` 的禁令。**這是 azure-launch 計畫沒列到的既有釘子，上次漏列造成過 BLOCKED(contract)。** 另一條路是在原始碼裡把字拆開躲過正則，但那是掩耳盜鈴，不採用；採用縮窄正則，並在 PR 說明寫「以前／以後／理由」。

## 失敗先行測試（`platform/tests/test_azure_upload.py`，現在全紅；全部用假的 `site.run_fixed`，必要時假 `site.start_fed`，`tmp_path` 當 `storage_root` 與暫存目錄，不碰網路、不呼叫真 az、不花錢；測試輸入一律假的：`labcontainer`、`labstore`、`westeurope`、`azure-lab`、`alice`、`bob`。憑證相關鍵名與假金鑰一律用字串相加組出來，避免被 `credentials_stay_in_settings_test.sh` 掃到）
編號前綴 `AZU-`。
1. `AZU-GATE-01 test_azure_env_may_queue_put_upload_when_available`：`available` 的 Azure 環境可以 `enqueue_put_upload`；非 `available` 被拒，訊息說環境還不能用。
2. `AZU-GATE-02 test_put_upload_gate_is_a_per_type_table_not_a_shared_tuple`：`CLOUD_JOB_KINDS` 裡 Azure 恰為五個（preflight、launch_nextflow、cancel_run、pipeline_files、put_upload），不含 `clean_work`；Google 與 AWS 那兩格各六個值與修改前完全相同。
3. `AZU-GATE-03 test_clean_work_and_resume_still_refused_for_azure`：Azure 環境排 `clean_work` 仍被拒，訊息含 `azure-clean`，不含 `azure-launch`、`azure-upload`；續跑仍被拒。
4. `AZU-LOC-01 test_workdir_bucket_for_azure_is_the_container`：Azure 環境 `workdir_bucket` 回 `labcontainer`；`workdir_scheme` 回 `az`；`workDir` 沒有子資料夾、容器名不合規（大寫、含 `--`、太短）都丟 `CloudPathError`。
5. `AZU-LOC-02 test_google_and_aws_location_behaviour_is_unchanged`：Google 與 AWS 環境的 `workdir_bucket`、`workdir_scheme`、`upload_prefix`、`object_url`、`big_file_command` 回傳與修改前逐字相同。
6. `AZU-LOC-03 test_az_object_url_is_inside_the_owners_prefix`：`object_url` 在 `az://labcontainer/uploads/alice/` 底下；`inside_prefix` 對 `uploads/alice2/x`、`uploads/alice/../bob/x`、`uploads//x`、別的容器都回假。
7. `AZU-LOC-04 test_uploads_prefix_does_not_overlap_the_workdir_subfolder`：`workDir=az://labcontainer/runs-a` 時上傳位置是 `az://labcontainer/uploads/alice/x`，不在 `runs-a/` 之下。
8. `AZU-AGT-01 test_agent_uploads_with_fixed_argv_and_no_secret_in_argv`：假 `run_fixed` 收到的 argv 恰為第 4 條作法的形狀；含 `--account-name labstore`、`--container-name labcontainer`、`--name uploads/alice/<name>`、`--file <暫存檔>`、`--overwrite true`；**不含** `--account-key`、`--sas-token`、`--connection-string`，也不含任何假金鑰字串；沒有 shell。
9. `AZU-AGT-02 test_agent_env_has_the_storage_credentials_and_nothing_else_from_the_parent`：傳給 `run_fixed` 的 env 含 `AZURE_STORAGE_ACCOUNT=labstore`、`AZURE_STORAGE_KEY`（值＝測試組出的假金鑰）、`AZURE_CONFIG_DIR`（存在的暫存資料夾）、`AZURE_CORE_COLLECT_TELEMETRY=false`；測試先在父行程塞 `AZURE_*`、`ABF_X` 假值，env 裡不得出現。只有 SAS 時改設 `AZURE_STORAGE_SAS_TOKEN` 且不設 `AZURE_STORAGE_KEY`；兩者都有時用帳號金鑰。呼叫結束後 `AZURE_CONFIG_DIR` 指的資料夾已被刪。
10. `AZU-AGT-03 test_agent_rejudges_dest_and_refuses_a_foreign_prefix`：`dest` 指到 `az://labcontainer/runs/x`、別的容器、別人的 `uploads/bob/` 都拒，假 `run_fixed` 一次都沒被呼叫。
11. `AZU-AGT-04 test_size_is_checked_with_blob_show_before_the_staged_file_goes`：假 `run_fixed` 對 `blob show` 回不同大小 → 結果是失敗、暫存檔仍在；回相同大小 → 成功、暫存檔被刪。
12. `AZU-AGT-05 test_unreadable_size_keeps_the_staged_file`：`blob show` 逾時、`OSError`、或輸出不是數字 → 結果 done 但訊息說沒能核對，暫存檔保留（鏡像 aws-upload A4）。
13. `AZU-AGT-06 test_missing_credentials_file_fails_without_leaking_its_content`：憑證檔不存在或缺金鑰與 SAS → 失敗訊息可含路徑，但不含任何金鑰值；`run_fixed` 未被呼叫。
14. `AZU-AGT-07 test_symlinked_or_resized_staged_file_is_refused`：暫存檔是符號連結、或大小與 `size` 不符 → 拒，`run_fixed` 未被呼叫。
15. `AZU-AGT-08 test_staged_file_swapped_during_the_upload_is_not_deleted`：假 `run_fixed` 在上傳呼叫期間把暫存檔換成別的檔案（dev/ino 變了）→ 結果是失敗、暫存檔保留。（對應 `--file` 的空窗，見作法 4）
16. `AZU-AGT-09 test_missing_az_program_gives_a_plain_message`：假 `run_fixed` 丟 `FileNotFoundError` → 結果失敗，訊息含「找不到 az 指令」與 Azure CLI，暫存檔保留，無 Traceback。
17. `AZU-AGT-10 test_failed_az_exit_keeps_the_staged_file_and_hides_the_stderr_secrets`：`az` 回非 0，stderr 內含假金鑰 → 結果失敗、暫存檔保留，訊息不含該假金鑰。
18. `AZU-AGT-11 test_run_put_still_refuses_slurm_and_unknown_platforms`：Slurm 與其他類型的環境，`run_put` 仍回「這種計算環境不能放雲端資料」那句（逐字，azure-launch 裁決 13 規定這句不變）。
19. `AZU-DSET-01 test_dataset_destination_az_registers_az_paths`：`register_dataset(destination=<Azure 環境>)` 寫入的 `path` 以 `az://labcontainer/uploads/alice/` 開頭。
20. `AZU-DSET-02 test_mixed_schemes_in_one_dataset_are_refused`：同一資料集混 `az://` 與 `gs://`、`s3://`、或本機路徑 → 拒並說明；`az://` 路徑的容器不是 `workDir` 的容器 → 拒。
21. `AZU-DSET-03 test_over_limit_file_gets_the_az_command_and_a_plain_warning`：大於 2 GB 的暫存檔 → 訊息含 `az storage blob upload-batch` 指令與「在你自己的電腦上、用你自己的 Azure 登入」。
22. `AZU-STATIC-01 test_no_cloud_library_and_no_station_word_in_platform_sources`：掃 `abf_platform/` 新舊檔，無 `boto3`／`botocore`／`google`／`azure` 匯入、無 "station" 字樣、無 `subprocess`；`cloud_store.py` 與 `actions/datasets.py` 全文小寫後無 "azure"。
23. `AZU-STATIC-02 test_put_upload_source_has_no_delete_no_cost_no_shell_words`：`put_upload.py` 無 `storage blob delete`、`azcopy`、`delete-object`、`s3 rm`、`--acl`、`presign`、`cloud_cost`、`shell=True`、`os.system`。
24. `AZU-STATIC-03 test_no_mcp_upload_tool_exists`：MCP 工具清單沒有任何 upload 字樣的工具（ADR 0010）。
25. `AZU-DOC-01`～`AZU-DOC-03`：`docs/PLATFORM.md` Azure 型別表那一列寫「checked and launched on the platform host (clean, resume: not yet)」；`docs/SEQERA_PARITY.md` Azure 列為 `Have (create + check + launch + cancel + upload); clean in azure-clean`；`docs/TESTING.md` 有「Uploading to Azure Batch (azure-upload): the maintainer checks by hand」一節，含 `az storage blob show` 驗大小的步驟與「會花一點錢、先設好成本警示」的警語；PLATFORM.md 的 Azure 上傳段寫明「網頁入口尚未接上」與「版本控制或軟刪除開著時，覆寫同名檔會留下舊版本、仍收費」。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
**這一節是 BLOCKED(contract) 的主要來源，逐條列出。** 行號取自 origin/v3 796f971（azure-launch 未合），azure-launch 合併後行號與函式名會變，executor 開工第一步：`git grep -n -E "put_upload|upload" origin/v3 -- platform/tests/test_azure_ce.py platform/tests/test_azure_launch.py platform/tests/test_aws_launch.py platform/tests/test_gcb_ce.py`，逐條比對，名字找不到就在帳本記一行，不自己猜著改別的測試。

A. 本任務自己必須改的（不改就紅）：
1. `test_azure_ce.py:884-891` `test_no_launch_cost_or_upload_code_for_azure`：正則禁 `storage blob upload`、`azcopy` 於 `abf_platform` 與 `abf_station` 全部原始碼。以前：任何位置出現 `storage blob upload` 都紅。以後：拿掉 `storage blob upload`（與用到的 `upload-batch`），其餘禁令保留；測試名稱與說明改成「Azure 沒有刪除、沒有 azcopy、沒有建池」。理由：本任務就是要寫這個指令（作法 11）。**azure-launch 計畫沒有列這一條。**
2. `test_azure_ce.py:936` `test_no_new_write_path_for_azure`：迴圈 `("launch_nextflow","cancel_run","clean_work","put_upload","pipeline_files","list_site_files")` 全被拒。azure-launch 會先把 `launch_nextflow`、`cancel_run`、`pipeline_files` 拿掉；本任務從迴圈再拿掉 `put_upload`，`clean_work`、`list_site_files` 仍被拒。理由：put_upload 改為允許，允許的唯一出口是 `site.run_fixed`，由 `AZU-AGT-01`、`AZU-STATIC-02` 把關。
3. `test_azure_ce.py:732-750` `test_jobs_other_than_the_preflight_are_refused_in_plain_words`（迴圈在 738 行附近）：azure-launch 重寫後，從「被拒」迴圈中再移除 `put_upload`；`clean_work` 仍在迴圈裡。（鏡像 aws-upload A3(b)）
4. `test_azure_ce.py:850-870` `test_docs_list_every_azure_key_and_check`：857 行的 PLATFORM.md 型別表正則、859 行、864 行的 SEQERA_PARITY 列。azure-launch 先改成 launch 的字串；本任務再改：PLATFORM.md Azure 列變「checked and launched on the platform host (clean, resume: not yet)」，SEQERA_PARITY 列變 `Have (create + check + launch + cancel + upload); clean in azure-clean`。理由：文件要與動作層一致。
5. `test_azure_launch.py`（azure-launch 新增，合併後才有）：
   - `AZL-GATE-01`（put_upload 被拒、訊息含 `azure-upload`）：改為 put_upload 對 `available` 的 Azure 環境可排；只剩 `clean_work` 被拒且訊息含 `azure-clean`。
   - `AZL-GATE-03`（`CLOUD_JOB_KINDS[AZURE]` 恰為四個）：改為恰為五個，多 `put_upload`。
   - `AZL-GATE-04`（`cloud_store` 對 Azure `az://` 的 workDir 丟 `CloudPathError`；`actions.datasets` 的 destination 為 Azure 被拒）：改為 `cloud_store` 認得 `az://`、`workdir_scheme` 回 `az`、destination 為 Azure 可用（`AZU-LOC-01`、`AZU-DSET-01` 取代）。
   - `AZL-GATE-05`（put_upload／clean_work 不能為 Azure 排隊；站台代理 `put_upload.run_put` 拒 Azure 環境）：`put_upload` 那半移除，`clean_work` 那半保留；`run_put` 拒 Azure 那半移除（`AZU-AGT-*` 取代），但「Slurm 仍被拒」保留。
   - `AZL-DOC-01`（PLATFORM.md Azure 列「…(upload, clean, resume: not yet)」）、`AZL-DOC-02`（SEQERA_PARITY「Have (create + check + launch + cancel)」）、`AZL-DOC-03`（TESTING.md）：字串逐字換成本任務的新句子；`AZL-DOC-03` 若釘死 TESTING.md 的小節清單，加進新的 Azure 上傳小節。
6. `test_cloud_upload.py:453` `test_workdir_bucket_needs_a_google_batch_environment`（aws-upload 後的名字與訊息以合併後為準，重查）：它與 `test_aws_upload.py` 約 226-241 行（`workdir_scheme` 的 `CloudPathError` 與 `str(e.value) == "這個計算環境沒有 gs:// 的 workDir，不能放雲端資料 (this environment has no gs:// workDir)"` 逐字比對、以及 `workdir_scheme(aws_ce())=="s3"`）一起檢查：Google 與 AWS 的逐字訊息**不准動**；只有「其他平台丟 `CloudPathError`」那類斷言，若測試用 Azure 環境當「不能放」的反例，要換成別的類型（例 Slurm 或 K8s），並列進 PR 說明。`cloud_store.workdir_scheme` 的「只有 Google Batch 或 AWS Batch 環境可以」句要加上 Azure Batch——**但 azure-launch 裁決 13 規定它在 azure-launch 中不變，改動只在本任務**，所以所有逐字比對這句的測試（`test_cloud_upload.py:304` 的「不能放雲端資料」子字串不受影響；其餘用 `grep -n "只有 Google Batch"` 重查）一併換句。
7. `test_aws_launch.py` 與 `test_aws_ce.py`、`test_gcb_ce.py`、`test_gcb_launch.py` 中把 **Azure 當成「不能放雲端資料／不能排 put_upload」的反例**的斷言（azure-launch 裁決 11 已列：`test_azure_ce.py:720/746/756/857/859/864/951`、`test_aws_ce.py:907/924`、`test_gcb_ce.py:853/867`、`test_gcb_launch.py:1151`、`test_aws_launch.py:985/992`）：azure-launch 會把它們改成「Azure 可 launch」，本任務要逐條 grep 其中是否還有「Azure 的 put_upload 被拒」或「SEQERA_PARITY／PLATFORM.md 的 Azure 字串」，有就換成本任務的字串。`test_aws_ce.py:907/924` 與 `test_gcb_ce.py:853/867`、`test_gcb_launch.py:1151` 釘的是 PLATFORM.md 型別表整段句子（"Slurm, Google Cloud Batch and AWS Batch can run; …"），azure-launch 裁決 12 已把它改成 "Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; the other ten types can be modelled only"，**本任務不再改這句**，只改 Azure 那一列。

B. 本任務不准動、但要確認不會被新程式碼誤傷（跑全套前先單獨跑）：
- `test_cloud_upload.py:649`（TC-088）、`test_aws_upload.py` 約 693-715（禁雲端函式庫匯入、禁 `delete-object|s3 rm|s3 sync|--acl|presign`、禁 `cloud_cost`、禁 "azure"）：新程式碼要符合，不改測試。
- `test_station_static.py:46`（`\bazure\b` 逐行禁字，小寫）：`abf_station` 新程式碼要符合，不改測試。
- `test_byte_channel_b.py:903`（`put_upload.py` 禁 `google|boto|azure|requests|httpx|socket` 匯入）：符合，不改。
- `test_azure_ce.py:564-575` `test_the_commands_are_read_only`：只掃預檢 argv 的字，禁 `upload` 這個字；上傳 argv 在 `put_upload.py` 不在預檢，預期不受影響——但若測試是掃 `azure_preflight.py` 全文，把上傳用的環境小函式放在 `put_upload.py` 而不是 `azure_preflight.py`。
- `test_station_docs.py:78`、`test_station_envs.py:21,161,478,482`：Azure 相關清單與掃描，預期不受影響，先單獨跑一次確認。
- 其餘 `test_cloud_upload*.py`、`test_aws_upload.py`、`test_byte_channel_*`、`test_station_*` 的 Google 與 AWS 指令斷言一個字都不准動。

## 完成標準（done when）
- 上面所有 `AZU-` 測試全綠，且執行前確認過它們是紅的（先在沒改程式的分支跑一次，紅的記進 ledger）。
- 整個 `platform/tests` 套件全綠，Google 與 AWS 相關測試不改任何斷言（上面 A 節列的有意更新除外）。已知環境紅燈 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 視同綠。
- 手動差異檢查（範圍、既有測試未被改弱、`test_azure_ce.py:884` 正則只拿掉上傳那一項）記在 ledger，不列為 TC。
- **真實 Azure 上傳不屬完成標準，列為「需要人」的 C 級步驟**：會寫真實的 Blob 容器、花一點錢；維護者另外點頭、先設好 Azure 成本警示（Cost Management budget alert）；步驟寫進 `docs/TESTING.md`。所有自動測試用假的 `az`，不連網、不花錢。

## 環境事實
- Azure 憑證檔：站台代理的位置來自 `ABF_STATION_AZURE_CREDENTIALS`，預設 `<部署資料夾>/_personal/azure-credentials`，`[default]` 段內 `batch_account_key`，以及 `storage_account_key` 或 `storage_sas_token`（`azure_preflight._read_shape`）。
- 環境設定鍵：`location`、`batchAccountName`、`storageAccountName`、`workDir`（`az://<container>/<subfolder>`，子資料夾必填）、`pool`、`spot`、`maxvCpus`。`snapshot()` 回的是扁平 dict；`compute_envs.view(row)` 才有 `config` 子 dict，`cloud_store.workdir_bucket(ce)` 讀 `ce["config"]["workDir"]`，`put_upload.run_put` 自己組 `{"platform":…, "config":{"workDir":…}}`。
- 站台代理對外的唯一出口是 `site.run_fixed`／`site.start_fed`；不得新增另一條 `subprocess` 路徑。
- 已驗證的 az CLI 事實（`https://learn.microsoft.com/en-us/cli/azure/storage/blob?view=azure-cli-latest`，2026-10-28 讀）：`az storage blob upload` 有 `--file/-f`、`--overwrite {false,true}`（預設 false，false 時遇已存在的 blob 失敗）、`--max-connections`（blob 超過 64 MB 時的平行連線數，預設 2）、`--no-progress`、`--validate-content`（每個區塊 MD5 由服務端驗）、`--tier`、`--timeout`、`--auth-mode {key, login}`、`--account-name`、`--container-name/-c`、`--name/-n`、`--sas-token`；`--data`（Preview，範例 `echo $data | az storage blob upload --data @- …`）與 `--length`（Preview）；環境變數 `AZURE_STORAGE_KEY`、`AZURE_STORAGE_SAS_TOKEN`、`AZURE_STORAGE_CONNECTION_STRING`、`AZURE_STORAGE_ACCOUNT`、`AZURE_STORAGE_AUTH_MODE`。`az storage blob upload-batch` 存在（`-d` 容器、`-s` 來源資料夾、`--pattern`、`--overwrite`、`--max-connections`）。
- **未驗證**（官方該頁沒寫，列入待裁決）：`blob show` 的輸出欄位名與 JMESPath；`upload-batch` 有沒有 `--destination-path`；blob 名稱長度上限；單一 blob 2 GB 的行為與 `--file` 記憶體用量；只有 SAS 時要不要 `--auth-mode key`（預檢對兩種都用 `--auth-mode key`）；SAS 的權限範圍（需要 write／create）。
- Google、AWS 路徑已有真實驗證；Azure 路徑沒有。

## 不做
- 不做 Blob 刪除（azure-clean）、不做費用估算、不做續跑、不開放 Azure 的 `clean_work`。
- 不新增 MCP 上傳工具、不改網頁檔案（網頁入口另案）。
- 不用 Azure SDK，不用 `azcopy`、`--account-key`／`--sas-token` 旗標（金鑰進 argv）、`--connection-string`、SAS URL 產生、瀏覽器直傳。
- 不做跨環境搬資料（把 Google 或 AWS 上傳的檔案搬到 Blob）。
- 不開放 Azure 環境的 `list_site_files`。
- 不教使用者怎麼登入 Azure（登入說明另案）。
- 不自動設容器的生命週期規則、版本控制或軟刪除；只在文件寫建議。

## 不確定的地方（需要維護者或執行者查證）
見下一節「裁決與待裁決」的待裁決 1～11。

## 裁決與待裁決

### 已定（本檔作者依據 aws-upload／azure-launch 的既有裁決推定，developer-agent 可翻案）
1. 接力順序：azure-launch → azure-upload → azure-clean；各自在前一件合進 v3 後才開工，開工時用 `git grep origin/v3` 重查實際名字與行號。
2. 上傳上限沿用 `UPLOAD_LIMIT = 2_000_000_000` 與逾時 3600 秒；官方文件寫明更低限制才調低，帳本註明出處。
3. 位置：同容器、前綴 `uploads/<owner>/`，不含 `workDir` 子資料夾。
4. 憑證：金鑰只經環境變數，不進 argv、不寫檔；帳號金鑰優先於 SAS。
5. `clean_work`、續跑對 Azure 仍拒；訊息只提 `azure-clean`，仍含「尚未支援」。
6. 交付範圍：動作層＋站台代理＋文件，**沒有可按的網頁按鈕**，PR 說明與 PLATFORM.md 照實寫「網頁入口尚未接上」。
7. 版本控制：本任務只在 PLATFORM.md 補一句「版本控制或軟刪除開著時，覆寫同名檔會留下舊版本、仍收費」。
8. B 級：verifier 通過＋CI 綠由 developer-agent 自合。
9. 路徑更正：資料集動作在 `platform/abf_platform/actions/datasets.py`，不是 `datasets.py`。規則照舊：不准新增公開函式與參數名。
10. `workdir_scheme(ce)` 簽名吃環境 dict，回 `"gs"`、`"s3"` 或 `"az"`，其他平台丟 `CloudPathError`；Google 與 AWS 的回傳與逐字訊息不變。
11. 失敗語意鏡像 aws-upload A4／A5：雲端大小沒核對相符就不刪暫存檔；找不到 `az` → 白話失敗、暫存檔保留。

### 待裁決（給 developer-agent；執行者開工前要有答案，否則走預設）
1. **主要傳輸方式。** 預設：`--file` 路徑方式（穩定、官方主要用法，用 `run_fixed`），代價是 `az` 自己重開路徑的檢查到使用空窗，用前後 `lstat` 補。替代：`--data @- --length N` 從 stdin 串流（用 `start_fed`＋`stream_into`，與 AWS 版同形，無空窗），但官方標 Preview，且 2 GB 時 `az` 是否整個讀進記憶體沒有文件。請決定；若選替代，作法 4、測試 8、15 要重寫。
2. **`--overwrite true` 還是預設 false。** 預設：明寫 true，與 S3 靜默覆寫對等，使用者重傳同名檔不會失敗。代價：容器開了版本控制或軟刪除時會留舊版本繼續收費。若選 false，重傳同名檔會得到「已存在」失敗，需要白話訊息。
3. **驗大小的指令與 JMESPath。** 預設：`az storage blob show … --query properties.contentLength --output tsv`。官方頁面沒給輸出形狀，執行者必須先讀 `blob show` 一節；讀不到就改用 `az storage blob list --prefix <key> --query "[0].properties.contentLength"` 或回報待人查，不准猜。
4. **`--auth-mode`。** 預檢對金鑰與 SAS 都帶 `--auth-mode key`。只有 SAS 時帶它是否正確、SAS 權限是否足夠（需 write／create），官方頁面沒說；預設：與預檢一致，帶 `--auth-mode key`，SAS 權限不足時把 `az` 的錯誤轉成白話失敗。
5. **上傳環境要不要剝掉 `AZURE_BATCH_*`。** `_az_env` 預設會設它們；上傳用不到。預設：剝掉（最小權限），需要的話在上傳用的小函式裡 `pop`。
6. **`big_file_command` 的 az 形狀。** `upload-batch` 的 `--destination-path` 是否存在未核；若不存在，改成 `--destination <container>/uploads/<owner>/rawdata`（容器後接路徑）或要求使用者 `cd` 後用 `--pattern`。執行者先讀文件再定，結果記帳本。
7. **blob 名稱規則。** `uploads/<owner>/<name>` 的長度、字元限制官方該頁未寫；`cloud_store.object_url` 已擋 `/`、`\`、`..`、NUL、空字串、長度 255。預設：沿用，不另加；若官方有更嚴的限制，補測試。
8. **禁字處理方式。** `cloud_store.py`／`actions/datasets.py` 全文不准有 "azure"（小寫比對）、`abf_station` 不准有小寫 `\bazure\b`。預設：錯誤與說明用中性字，必要時拆字；`azure_preflight` 內既有的拆字做法照用。請確認不要改禁字測試本身（改測試比拆字更重）。
9. **`test_azure_ce.py:884` 正則的縮窄範圍。** 預設：只拿掉 `storage blob upload`（與 `upload-batch`）。請確認這樣的縮窄可以接受，不是把整條測試刪掉。
10. **暫存目錄共用。** `ABF_STATION_UPLOADS` 與 Google、AWS 共用、不分 scheme（同 aws-upload 待裁決 5）。預設：共用。
11. **azure-launch 合併後的真實名字。** `_plain_env`（若有）、`CLOUD_JOB_KINDS[AZURE]` 的四個值、`_target` 的 Azure 拒絕句、`test_azure_launch.py` 的測試名與編號，都是本檔的推定；合併後重查，不符以實際為準。

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

### developer-agent 裁決（10-28 23:5x，對應上方待裁決 1–11）
1. 主傳輸用 `--file` 路徑模式，前後 lstat 比對（不用 Preview 的 `--data @-`）。
2. `--overwrite true`：跟 S3 的靜默覆蓋一致；版本保留／軟刪除的費用寫進 PLATFORM.md 一句提醒即可。
3. 大小檢查照計畫；executor 先跑 `az storage blob show --help` 與官方頁確認輸出，形狀不符就用 `blob list` 退路，兩者都不可靠 → BLOCKED。
4. 兩種憑證都有時用帳號金鑰（同 azure-launch 裁決 2）；只有 SAS 時用 SAS，權限不足的錯誤原樣轉成白話拒絕，不重試。
5. 上傳環境剝掉 `AZURE_BATCH_*`。
6. `--destination-path` 由 executor 用 `--help` 與官方頁查證；查不到 → 改逐檔 `upload`，不准猜旗標。
7. 沿用既有 255 字元檢查。
8. 禁字用中性措辭繞開，不准拆字串湊字、不准改禁字測試本身。
9. 准許只把 `test_azure_ce.py:884` 的正則拿掉 `storage blob upload` 與 `upload-batch`，其餘照留。
10. `ABF_STATION_UPLOADS` 跨 scheme 共用。
11. azure-launch 合併後由 developer-agent 重 grep 行號與名稱再派；清單以外的既有斷言要改 → BLOCKED。
12. （10-29 01:1x，azure-launch #258 合併後重 grep）行號已位移：`test_no_launch_cost_or_upload_code_for_azure` 現在在 886 行（正則在 890 行）、`test_no_new_write_path_for_azure` 在 934 行（迴圈 938）、`test_jobs_other_than_the_preflight_are_refused_in_plain_words` 在 733 行（迴圈 740）、`test_docs_list_every_azure_key_and_check` 在 851 行、`test_the_commands_are_read_only` 在 560 行。本計畫所有 `test_*.py:<行號>` 一律以**函式名稱**為準，行號只當提示。

## 裁決（10-29 01:4x，回應 verifier 合約審查的 6 點）
13. **禁字 "azure"（`test_aws_upload.py` 約 705 行的字表）**：這個字表的用意是「不准在這兩個檔用 Azure SDK」，而同一個測試 693 行已用 `_imports()` 禁 `azure` 匯入。准許把 705 行字表裡的 `"azure"` 換成 `"import azure"` 與 `"from azure"`（跟既有的 `"import google"` 同一種寫法），693、713 行的匯入禁令一字不動。這樣 cloud_store.py、datasets.py 可以直接寫 Azure 字句與用 `compute_envs.AZURE`／`_AZURE_CONTAINER`，**不准拆字**（裁決 8 仍有效）。PR 說明寫「以前／以後／理由」。這是清單外第 6 處准改的既有斷言，其他仍照裁決 11。
14. **`--auth-mode`**：有 `storage_account_key` 時，upload 與 blob show 的 argv 都帶 `--auth-mode key`（與預檢、azure-clean 一致）；只有 `storage_sas_token` 時改帶 `--sas-token`（值從環境變數傳，不進 argv 明文——若 az 不吃環境變數就用 `AZURE_STORAGE_SAS_TOKEN`），不帶 `--auth-mode`。作法 4／5 與 AZU-AGT-01 的「恰為」形狀依此補上。
15. **超限指令**：訊息用 `az storage blob upload-batch`；若查不到 `--destination-path`，退路是 `--destination <container>/uploads/<owner>/rawdata`，**不改成逐檔 upload**（逐檔只適用於代理端真正上傳的路徑，裁決 6）。
16. **拆字範圍**：裁決 8 只管 platform 的 cloud_store.py、datasets.py；abf_station 沿用 azure_preflight 既有的 `"Az" "ure"` 寫法。
17. **憑證檔必填鍵**：上傳沿用 `_read_shape` 原樣，沒有 `batch_account_key` 就拒絕（一個環境一份憑證檔，跟送出 run 同一份）。不另開放寬。
18. **人工確認**：沿用 AWS／Google 上傳的既有做法（檔案主人在網頁按上傳即排入），不加二次確認；不是規格變更，不必問維護者。
19. （10-29 02:0x，取代裁決 14 的 SAS 那半句）**只有 SAS 時**：argv 不帶 `--sas-token`、也不帶 `--auth-mode`；SAS 只經環境變數 `AZURE_STORAGE_SAS_TOKEN` 交給 az。有帳號金鑰時帶 `--auth-mode key`，金鑰經 `AZURE_STORAGE_KEY` 環境變數。旗標順序不釘，只釘動詞開頭、旗標配對齊全、沒有多餘旗標（照合約）。
20. **大小寫**：`test_cloud_upload.py:649`（TC-088）不改；所以 cloud_store.py 原文不得出現小寫 `azure`，只能用 `AZURE`／`Azure`。datasets.py 同樣照做。
21. **失敗訊息**：照專長守則，不露出內部路徑（含憑證檔路徑）；AZU-AGT-06 的「可含路徑」作廢。只說錯在哪、該怎麼辦，不含金鑰值、不含堆疊。
