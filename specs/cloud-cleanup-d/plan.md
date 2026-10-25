---
id: cloud-cleanup-d
title: 平台主機上的代理替 Google Batch 的 run 刪掉 bucket 裡那個 run 自己的 work 前綴（先列出再刪，一次，不重試）
tier: B
kinds: backend
lane: L-cleanup
after: cloud-cleanup-c
base: v3
---

# cloud-cleanup-d

> 本檔由 developer-agent 起草（2026-10-24），`cloud-cleanup.md` 切成六片之第四片（a 資料庫 → b 平台記帳 → c 代理刪 Slurm 的 work → **d 代理刪 Google Batch 的 work** → e 確認頁 → f 成功後提出申請＋文件）。**本片只寫代理端的 Google Batch 分支**：同一個 `abf_station/clean.py`，加上用 `gcloud storage` 刪 bucket 裡一個前綴。此刻平台還不會送出這種工作（f 片才會建立申請），所以使用者看不到任何變化。B 級（後端、無網頁畫面）→ verifier 通過＋CI 綠即可合併。
> **名詞**：「work 前綴」＝`gs://<bucket>/<workDir 的子資料夾>/runs/<run>/work/` 底下的所有物件；「平台主機」＝跑 Google Batch 主控程序的那台機器（Google Batch 的 Nextflow 主控程序跑在這裡，代理也在這裡，`reach: local`）。
> **派工前提**：`cloud-cleanup-c` 已合併（`clean.py` 與 `run_clean` 已存在）。

## 目標
Google Batch 環境的 run 成功後，使用者按了「確認刪除」，平台主機上的代理：驗確認憑證、重算並逐字比對 work 的 `gs://` 路徑、確認這個 run 的主控程序已結束、確認金鑰在位且預檢通過，然後**先唯讀列出**該前綴底下的物件（每一行都必須在 `…/work/` 底下，否則拒絕），**再用一次**固定參數的 `gcloud storage rm --recursive <那一個網址>` 刪掉，不用 shell、不重試。對使用者的意義：Nextflow 在 bucket 留下的中間檔（常比結果大很多倍、每月計儲存費）能安全收掉，而且同層的 `work2/`、`work-keep`、`results/` 不會被波及。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md` 與 `CLAUDE.md`；每句至少對應一條測試案例：
- 「**跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪**」（裁示 16，第 58 行）→ ①未經確認憑證一律拒絕且 `gcloud` 一個字都不呼叫②刪的是中間檔，結果（`results/`）不在範圍③代理不會自己決定刪。
- 「**C-7 `cloud-cleanup`**（B／backend）：succeeded 後建「刪除 work 目錄」的待確認請求（走 `_ask`，新 kind `clean_work`；對 nano4 也適用）」（第 171 行）→ 與 c 片的 Slurm 對稱：同一個種類 `clean_work`，Google Batch 也適用。
- 「直接 `scancel`，以及刪改叢集端 `rawdata`／`results`／`analysis`，一律擋住」（`CLAUDE.md` §3.4）→ 硬規則同 c 片：路徑含 `rawdata`、`results`、`analysis` 或最後一段不是 `work` 一律拒絕；雲端 bucket 比照辦理。
- 「網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」（裁示 14，第 54 行）→ 本片無網頁畫面。
- 憲法原則 2＋任務交辦：「平台不啟動程式」（`test_scope.py` TC-071）→ `gcloud` 只由代理經 `site.run_fixed` 啟動；平台程式碼不動。
- 「每個寫入要本人答應」（憲法 6／ADR 0006，引自 `017d-launch-composed.md` 第 26 行）→ 第一步永遠是 `launch.verify_confirmation`。

## 範圍：檔案（只准改這些，共 6 個含 ledger）
- `platform/abf_station/clean.py`：加 `_clean_gcb(job, ctx, bundle)`、`run_clean` 的 Google Batch 分派（取代 c 片的「尚未支援」拒絕）、`_gcloud_env(key_path)`、`_head_gone(folder, run, number)`。**全套件唯一**出現 `storage rm` 字樣的檔案（連同 c 片的 `rm -rf`）。
- `platform/tests/test_station_clean_gcb.py`（新；檔首 `# Nothing existing: …`，TC-070；以 `platform/tests/test_gcb_launch.py` 的 `Box` 夾具（:48）與 `job_of`（:155）為樣板，假 `gcloud`／`ps` 走 `monkeypatch`）。
- 必須更新的既有斷言（有意；其他一律不准動，PR 說明逐條寫「以前／以後／理由」）：
  - `platform/tests/test_station_clean.py`（c 片的檔）：`test_a_google_batch_bundle_is_refused_in_plain_words_and_nothing_is_sent` 改成「Google Batch 內容包交給 `_clean_gcb`」（被拒的原因改為通過 d 片規則之外的那些，如金鑰缺失）；理由：c 片當時刻意拒絕，d 片是它的接手。
  - `platform/tests/test_gcb_ce.py:805-808`（`test_nothing_of_the_later_slices_exists`）：以前＝`abf_platform/` 與 `abf_station/` 所有檔都不得出現 `buckets create|services enable|service-accounts create|storage rm`；以後＝`storage rm` 只准出現在 `abf_station/clean.py`，其餘三個字樣、其餘所有檔的規則**不動**（正則那一行 `re.search(r"buckets create|…|storage rm", text)` 保持字面不變，因為 `test_cloud_upload.py:728-732` 靠 `GCB_CE_SRC` 原文剖析它；做法是 `clean.py` 另走一條只檢查前三個字樣的分支）。
  - `platform/tests/test_cloud_upload.py:726-735`（`test_the_scope_nail_no_longer_lists_the_command_but_keeps_the_rest`）：`options == [四個字樣]` 不動；最後的 `for f in _source_files(): assert not re.search("|".join(options), …)` 對 `abf_station/clean.py` 只檢查前三個字樣（其餘所有檔仍檢查四個）。
- `specs/cloud-cleanup-d/ledger.md`。

**禁碰**：`abf_station/launch.py`／`cancel.py`／`gcb_launch.py`／`gcb_preflight.py`／`site.py`／`rules.py`／`handlers.py`（只讀它們的函式；`handlers.py` 在 c 片已完成）、`platform/abf_platform/*`、`platform/abf_launch/*`、`tests/no_second_run_state_test.sh`、`test_gcb_launch.py`（只 import 它的夾具，不改它）。

## 作法
1. **分派**：`run_clean` 在 `verify_confirmation`、`set(bundle) == KEYS`（鍵集合與 c 片相同）之後，`bundle["ce"]["platform"] == launch.GCB`（`launch.py:522`）就交給 `_clean_gcb`；Slurm 走 c 片的 `_clean_slurm`，兩條之間不共用路徑公式（見裁決 1）。
2. **`_clean_gcb` 的順序固定，每步失敗就停、不重試**：
   1. `bundle["agent"] == ctx.agent_name`；`run` 符合 `launch.RUN_NAME`；`slurm_job_id`（＝主控程序的 pid，`gcb_launch.py:215`）是 1 到 2^31-1 的整數（非布林）。
   2. `storage = launch.own_facts(ctx).get("storage_root")` 必須有（沒有 → 拒絕「部署設定沒有 storage_root」，同 `gcb_launch.run_cancel` :234-236）；`bundle["run_folder"] == "%s/%s/%s" % (storage, launch.GCB_RUNS, run)`（逐字，`launch.py:523`、:724）。
   3. **work 路徑重算**：`ce_out, bucket, _ = launch._check_gcb_ce(bundle["ce"])`（:541；`BundleError` → `Refusal`；這一步已用 `GCB_WORK_CHARS`（:528）擋掉 `* ? [ ] { }` 與空白，因為 `gcloud` 會展開萬用字元）；`expected = "%s/runs/%s/work" % (ce_out["workDir"], run)`；`bundle["work"] == expected`（**逐字**，不正規化、不容許結尾斜線）；把 `expected[len("gs://"):]` 以 `/` 切段：不得有空段、`.`、`..`，不得有 `rawdata`、`results`、`analysis` 任何一段；最後一段必須是 `work`；`expected` 的 bucket 必須等於 `bucket`。Google Batch 的 run 不會續跑或重跑（`launch.py:68` `GCB_NO_RESUME`），所以資料夾名恆等於 `run`，不需要 c 片的 `-aN` 規則。
   4. **主控程序已結束**（`_head_gone`）：`recorded = gcb_launch._read_small(os.path.join(folder, "head.pid"))`（:64；缺少或不是純數字 → 拒絕「找不到 head.pid，無法確認主控程序已結束」，保守起見不刪）；`int(recorded) == bundle["slurm_job_id"]` 否則拒絕；用 `host.run_fixed(["ps","-o","user=","-o","args=","-p",str(number)], gcb_launch._plain_env(), 20)`（仿 `gcb_launch.run_cancel` :243）：`rc != 0` 或沒有輸出＝已不在；有輸出且命令列含 `-name <run>`（同 :254 的正則）＝**還在跑 → 拒絕**「主控程序還在跑」；有輸出但 `-name` 不符＝pid 被別的程序重用，視為已不在。`TimeoutError` → `error`「查詢逾時，沒有刪任何東西，也不重試」。
   5. 金鑰與預檢：`key_path = gcb_preflight.credentials_path(ctx.settings_file)`（`gcb_preflight.py:35`）；`gcb_launch._check_environment(bundle["ce"], key_path)`（:122，唯讀預檢：金鑰檔在、權限私密、是服務帳戶金鑰、專案相符，與兩個 `gcloud` 問題），失敗 → 拒絕且沒有刪任何東西。環境：`env = gcb_launch._plain_env()`（:74）再加 `GOOGLE_APPLICATION_CREDENTIALS=<金鑰路徑>` 與 `CLOUDSDK_CORE_DISABLE_PROMPTS=1`（寫成 `_gcloud_env`，**不用** `_head_env`——那個會帶入環境設定的使用者變數）。金鑰路徑**只放在環境變數**，不進 argv、結果、訊息、日誌。
   6. **先唯讀列出**：`rc, out = host.run_fixed(["gcloud","storage","ls","--recursive","--project",ce_out["project"], expected + "/"], env, 120)`。解析 `out`：忽略空行；結尾是 `:` 的行是子資料夾標題，去掉冒號後比對；**每一行都必須以 `expected + "/"` 開頭**，否則拒絕「列出的物件不全在 work 底下（前綴撞名），不刪」。沒有任何物件行 → 成功且 `cleaned: true`，**不呼叫 `rm`**（「已經沒有東西」）。`rc != 0`：若輸出表示「沒有符合的物件」（executor 對照 `gcloud storage ls --help` 與官方文件確認這種情況的結束碼與訊息，寫進 ledger；與下面第 7 步同樣屬「未實測」）→ 同「已經沒有東西」；其他非零 → `error`，訊息經 `gcb_preflight._scrub`（:66）並把金鑰路徑換成 `[key file]`（`KEY_SHOWN`，`gcb_launch.py:32`）。
   7. **再一次**：`rc, out = host.run_fixed(["gcloud","storage","rm","--recursive","--project",ce_out["project"], expected + "/"], env, 300)`。argv 恰一個 URL、不用 shell、不加 `--continue-on-error`、不重試。**旗標拼法與「尾端斜線是否只刪該前綴、不波及 `work2/`、`work-keep`」executor 先對 `gcloud storage rm --help` 與官方文件核對，核對不過就停手回報，不要猜。**非零結束碼 → `error`，訊息過 `_scrub`，含「可能只刪了一部分；work_cleaned_at 沒記，可以再申請」；`TimeoutError` → 同樣的 `error`。
   8. 成功回 `("done", {"ok": True, "cleaned": True, "run_name": run, "message": "已刪除 bucket 裡 <expected> 底下的物件；results 沒有動"})`。
3. **migration**：不需要（本片不碰資料結構）。

### 手算範例（路徑 → 刪除／拒絕；verifier 直接拿去出題）
`workDir=gs://lab-bucket/work`，run `r1`，`expected=gs://lab-bucket/work/runs/r1/work`

| # | 內容包的 `work`（或雲端實況） | 結果 | 為什麼 |
|---|---|---|---|
| 1 | `gs://lab-bucket/work/runs/r1/work` | **刪除**（先 `ls`，每行都以 `…/work/` 開頭） | 逐字相等 |
| 2 | `gs://lab-bucket/work/runs/r1/results` | 拒絕 | 含 `results`、最後一段不是 `work` |
| 3 | `gs://lab-bucket/work/runs/r1/work/*`、`…/work*`、`…/work?`、`…/work[ab]`、`…/work{a,b}` | 拒絕 | 萬用字元不在白名單 |
| 4 | `gs://other-bucket/work/runs/r1/work` | 拒絕 | bucket 與 `workDir` 不同 |
| 5 | `gs://lab-bucket/work/runs/r1/` | 拒絕 | 最後一段不是 `work` |
| 6 | `ls` 回了 `gs://lab-bucket/work/runs/r1/work2/x` | 拒絕，不呼叫 `rm` | 不是以 `…/work/` 開頭（前綴撞名） |
| 7 | `ls` 沒有任何物件行 | **成功，`cleaned: true`**，不呼叫 `rm` | 已經沒有東西 |
| 8 | `gs://lab-bucket/work/runs/r1/work/../results` | 拒絕 | 含 `..` |
| 9 | `gs://lab-bucket/work/rawdata/work`、`gs://lab-bucket/analysis/runs/r1/work` | 拒絕 | 含 `rawdata`／`analysis` 段 |
| 10 | `gs://lab-bucket/work/runs/r2/work`（run 是 `r1`） | 拒絕 | 與這個 run 的重算值不同 |
| 11 | `gs://lab-bucket/work//runs/r1/work` | 拒絕 | 空段 |
| 12 | `ce.workDir=gs://lab-bucket`（沒有子資料夾） | 拒絕 | `_check_gcb_ce` 的既有規則（Nextflow 要求至少一層） |
| 13 | `head.pid` 的 pid 還活著且命令列有 `-name r1` | 拒絕 | 主控程序還在跑 |
| 14 | `head.pid` 的 pid 活著但命令列不含 `-name r1` | 繼續（視為 pid 被重用） | 不是這個 run 的 |
| 15 | 沒有 `head.pid` | 拒絕 | 無法確認已結束 |

## 失敗先行測試（現在都會紅；新檔 `test_station_clean_gcb.py`，預估 28 條 TC：手算範例 15 列參數化＋下列 13 條；假 `gcloud` 以一個小的「假 bucket」（物件名稱字典）實作 `ls`／`rm` 的前綴語意，這個假語意本身就是對文件的假設，手動驗收要用真的 bucket 驗證）
- `test_unconfirmed_gcb_clean_is_refused_and_no_gcloud_is_called`：沒有憑證／雜湊不符／憑證已用過／憑證種類是 `launch`／`cancel`（五種）。
- `test_every_row_of_the_hand_check_table`：上表 1–15 逐列，斷言結果、假 `gcloud` 的呼叫次數與內容、假 bucket 裡各物件是否還在（同層 `work2/x`、`work-keep`、`results/a.tsv` 全程不變）。
- `test_a_bundle_with_other_keys_a_wrong_agent_or_a_wrong_folder_is_refused`；`test_a_missing_storage_root_is_refused_in_plain_words`。
- `test_a_hostile_run_name_or_workdir_is_refused_before_any_command`（空白、`;`、`$()`、換行、BIDI）。
- `test_gcloud_is_called_with_one_fixed_argv_and_one_url_and_no_shell`：成功案例中含 `rm` 動詞的呼叫恰一次；其 argv 恰為 `["gcloud","storage","rm","--recursive","--project",<專案>, "<expected>/"]`；沒有 `--continue-on-error`；走 `run_fixed`（不是 `subprocess` 直接呼叫）。
- `test_the_key_path_is_only_in_the_environment_and_never_in_argv_a_result_or_a_message`（成功與兩種失敗各掃一次）。
- `test_a_missing_open_or_wrong_project_key_is_refused_before_ls_and_rm`（沿用 `_check_environment` 的三種失敗）。
- `test_a_listing_with_a_foreign_prefix_stops_before_rm`（範例 6 的獨立斷言）。
- `test_rm_failure_is_an_error_with_a_scrubbed_message_is_not_retried_and_claims_nothing`；`test_rm_timeout_is_reported_as_possibly_partial_and_is_not_retried`。
- `test_ps_timeout_is_an_error_and_nothing_is_listed_or_deleted`。
- `test_storage_rm_appears_only_in_clean_py_among_the_station_files`（掃 `abf_station/*.py`）；`test_rm_rf_still_appears_only_in_clean_py`（c 片的斷言仍綠）。
- `test_the_slurm_path_of_c_is_unchanged_and_its_tests_stay_green`（回歸：重跑 `test_station_clean.py` 的 Slurm 部分）。

## 完成標準（done when）
- 自動：新測試綠；三處既有斷言更新後全套綠（含 `tests/platform_test.sh`、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`）；MCP 工具數仍 12；`git diff --name-only` 只有「範圍：檔案」所列；`abf_station/launch.py`、`gcb_launch.py` 位元級不變（`git diff --stat` 貼進 ledger，依 dev-plans 通例由 verifier 核對並重跑）。
- 手動（維護者在**自己的測試 run** 上做，**由產品本身（確認頁）去刪，不要用任何 AI session 直接對 bucket 下刪除指令**；因為入口在 f 片，這項放到 f 片的驗收一起做）：本片合併前 executor 只需在 ledger 寫明 `gcloud storage rm --help` 與官方文件對「尾端斜線」「`--recursive`」「沒有符合物件時的結束碼」的核對結果與網址。
- 文件：無（在 f 片）。

## 環境事實
（行號為 `origin/v3` @ `279363b`；以函式名為準，動手前 `git fetch -q origin` 再核對。）
- Google Batch 的路徑：`launch.py` `render_gcb_bundle` :703；`run_folder = "<storage_root>/_gcb_runs/<run>"`（:724；`GCB_RUNS` :523）；`base = "<workDir>/runs/<run>"`（:725），`gcb.config` 的 work 是 `base + "/work"`（:732）、`outdir` 是 `base + "/results"`（:729）——**一個 run 一個前綴，正是為了讓這個任務能只刪這個 run**。`ce_out["workDir"]` 已被 `_check_gcb_ce` 正規化成 `gs://<bucket>/<prefix>` 且 prefix 只含白名單字元（`GCB_WORK_CHARS` :528；:560-565）。
- 主控程序：`gcb_launch.py` `_has_proc` :35、`_proc_cwd` :47、`_read_small` :64、`_plain_env` :74、`_head_env` :80、`_check_environment` :122、`run_launch` :147（`head.pid` 寫在 :204；`"slurm_job_id": pid` :215）、`_same_user` :220、`run_cancel` :225（資料夾核對 :232-236、`head.pid` 核對 :238-241、`ps` :243、`-name` 正則 :254）。
- 代理能用的兩種「碰外面」的方法，不要新增第三種：`site.run_fixed`（`site.py:91`，固定 argv、無 shell、逾時丟 `TimeoutError`）與 `Site.call`。`gcb_preflight.credentials_path` :35、`clean_environment` :44、`_scrub` :66、`run_preflight` :108。
- 預檢用過的 `gcloud` 形式：`gcloud storage ls gs://lab-bucket/ --project lab-project-1`（`test_gcb_ce.py:585`），所以 `--project` 對 `storage` 子指令可用；`rm` 是否同樣可以靠 `--help` 確認。
- **不屬於起草時能查證的事（executor 動手前各讀一次官方說明並把網址寫進 ledger，與下列假設不符就停手回報）**：①`gcloud storage rm --recursive gs://b/p/work/` 的尾端斜線只刪該前綴、不波及 `work2/`、`work-keep`；②`gcloud storage ls --recursive` 對不存在的前綴的結束碼與訊息；③bucket 若開了**物件版本控制或軟刪除（soft delete）**，`rm` 之後物件可能仍保留一段時間並繼續計費、也可能還原得回來——這會影響 f 片畫面上那句「無法還原」能不能這樣寫，executor 把官方說明的結論寫進 ledger 給 f 片用；④`ps` 在 WSL 與 Linux 的輸出形式（沿用 `run_cancel` 已在用的形式，無新假設）。
- 憲法掃描：`test_scope.py` TC-071／TC-061 掃的是 `abf_platform/`（:19-20），本片不動它；`abf_station/` 受 TC-070 檔頭規則。`test_gcb_ce.py:805-808` 與 `test_cloud_upload.py:726-735` 是「`storage rm` 不在別處」的兩個釘子（見範圍）。`tests/no_second_run_state_test.sh` 的送出字樣不含 `rm`。
- 新 `.py` 檔前 40 行要有 `# Nothing existing: <≥15 字理由>`（TC-070）：`test_station_clean_gcb.py`。`clean.py` 的檔頭（c 片寫的）把 `gcloud storage rm` 也納入理由：Google 自己的刪除工具不核對路徑與前綴，這裡要的是「刪之前先列出、逐行驗證、再刪一次」。

## 不做
- 不做平台端的任何事、不做確認頁、不做建立申請（a、b、e、f）；不改 Slurm 的清理（c）。
- 不寫 `gcloud batch jobs delete` 或任何取消 Batch 工作的第二條寫入路徑；不刪 bucket 本身或任何 `work` 以外的前綴；不動 `results/`、`rawdata/`、`analysis/`。
- 不用 `gsutil`、`rclone`、任何雲端函式庫（`test_gcb_ce.py` 的 `test_no_cloud_library_is_imported` 仍綠）；不加 `--continue-on-error`、不加重試、不加迴圈。
- 不處理版本控制／軟刪除的清除（那是 bucket 管理者的事，只在畫面上誠實說明，見 f 片）。
- 不動 AWS／Azure／K8s 類型；不改 Google Batch 的送出、取消。

## 裁決（2026-10-24，developer-agent；已併入上文，與其他段落不衝突）
1. **Google Batch 的 work 在 `<workDir>/runs/<run>/work`，Slurm 的在 `run_folder/work`；兩邊各自重算，不共用公式。** 舊計畫寫「共用一條 `work_target`」，但 Slurm 的續跑沿用原資料夾（c 片）而 Google Batch 不會續跑（`GCB_NO_RESUME`），兩邊的 `run_name` 與資料夾名的關係不同。
2. **先列出再刪。** 理由：把「前綴撞名」變成刪除之前就看得到、可以拒絕的事；代價是多一次唯讀呼叫。
3. **argv 恰一個 URL、不用 shell、一次、不重試、不加 `--continue-on-error`。** 一次失敗就回報，使用者看得到並可再申請。
4. **只在代理明說 `cleaned: true`（含「已經沒有東西」）時平台才記帳**（b 片）；逾時或錯誤不記。
5. **`gcloud` 的語意（尾端斜線、結束碼、軟刪除）以官方文件與 `--help` 為準，由 executor 核對並寫進 ledger；核對不過就停手回報，不在程式裡猜。**
6. **憑證**：金鑰路徑只在環境變數，沿用 `gcb_launch` 的檢查與環境組法；不使用 `_head_env`。
7. **切片理由**：舊計畫約 30 檔、需求超過 60 條測試；依 `dev-architecture-review-2026-10-24.md` §3 與 `dev-plans/README.md` 通例切成六片。本片 6 檔（含 ledger）。

## 裁決二（2026-10-25，回應 verifier 出題退回）
1. **c 片 TC-073 那條斷言改寫**（`platform/tests/test_station_clean.py:575` 附近，本片准改這一條）：改成——`clean.py` 不得含 `import subprocess`、`os.system`、`os.popen`、`start_detached`；`run_fixed` 只准出現在 `_clean_gcb` 與 `_head_gone` 兩個函式內（用 `ast` 找函式範圍，不用行號）；`ctx.site.call(` 仍恰出現一次。除此條與「Google Batch 被拒」那條外，`test_station_clean.py` 其他一律不准動。
2. 「Google Batch 被拒」那條的實際名稱是 `test_tc013_a_google_batch_bundle_is_refused_in_plain_words`（:190），以它為準。
3. `gcloud storage ls` 逾時（`TimeoutError`）→ `("refused", {"ok": False, "cleaned": False, "message": "列出雲端暫存檔逾時，沒有刪任何東西；稍後可以再申請"})`，不呼叫 `rm`。
4. `ps` 回超過一行 → 拒絕「無法確認主控程序已結束（ps 回了不只一行），保守起見不刪」，比照 `gcb_launch.run_cancel` :255。
5. 行號以函式名為準（`GCB_RUNS` 現 :542、`run_folder` :743、`GCB` :541、`test_gcb_ce.py` 掃描 :803-805）。

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
