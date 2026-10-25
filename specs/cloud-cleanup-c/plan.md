---
id: cloud-cleanup-c
title: 代理替 Slurm（nano4）的 run 刪掉那個叫 work 的目錄：路徑硬檢查、拒絕表、假站台測試
tier: B
kinds: backend
lane: L-cleanup
after: cloud-cleanup-b
base: v3
---

# cloud-cleanup-c

> 本檔由 developer-agent 起草（2026-10-24），`cloud-cleanup.md` 切成六片之第三片（a 資料庫 → b 平台記帳 → **c 代理刪 Slurm 的 work** → d 代理刪 Google Batch 的 work → e 確認頁 → f 成功後提出申請＋文件）。**本片只寫代理端**（`platform/abf_station/`）：收到一張已確認的 `clean_work` 工作，核對一長串條件，通過才在叢集上刪那一個 `work` 目錄。此刻平台還不會送出這種工作（f 片才會建立申請），所以使用者看不到任何變化。B 級（後端、無網頁畫面）→ verifier 通過＋CI 綠即可合併。
> **名詞**：「work 目錄」＝Nextflow 放每個 task 中間檔的 `work/`，不是結果；「代理」＝跑在使用者那邊、替平台碰叢集或雲端的小程式；「run 資料夾」＝`<workDir>/runs/<名稱>`，裡面有 `results/`、`work/`、`head.sh` 等。
> **派工前提**：`cloud-cleanup-b` 已合併。車道：`abf_station/` 屬 L1 站台車道，本任務是唯一動它的任務，不可與別的站台任務平行。

## 目標
代理收到 `clean_work` 工作（Slurm 環境）時：先驗確認憑證與內容雜湊（沒有就什麼都不做），再用自己的規則把路徑逐項重算一遍，與內容包**逐字相等**且最後一段恰為 `work`、整條路徑不含 `rawdata`／`results`／`analysis` 才動手；在叢集上只送**一條**固定樣板的指令，樣板先核對「資料夾真實位置、沒有連結、你自己沒有工作還在這個資料夾裡跑、work 是你的、results 沒有指向 work 的連結」，最後才 `rm -rf --one-file-system -- work`。對使用者的意義：他按了「確認刪除」之後，只有中間檔消失，結果與原始資料不會被碰到，而且碰不到的原因可以被一條條測試證明。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md` 與 `CLAUDE.md`；每句至少對應一條測試案例：
- 「**跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪**」（裁示 16，第 58 行）→ ①沒有確認憑證／雜湊不符／憑證已用過／憑證種類不是 `clean_work`，一律拒絕且**一條遠端指令都不送**②刪的是中間檔、結果（results）不在範圍③代理自己不會「自動」做任何清理（只回應一張已確認的工作）。
- 「**C-7 `cloud-cleanup`**（B／backend）：succeeded 後建「刪除 work 目錄」的待確認請求（走 `_ask`，新 kind `clean_work`；對 nano4 也適用）」（第 171 行）→ 本片就是「對 nano4 也適用」的代理端；種類名 `clean_work`。
- 「直接 `scancel`，以及刪改叢集端 `rawdata`／`results`／`analysis`，一律擋住」（`CLAUDE.md` §3.4，HPC 送分析／刪檔）→ 硬規則：任何路徑含 `rawdata`、`results`、`analysis`，或最後一段不是 `work`，一律拒絕，沒有例外、沒有旗標可關。
- 「網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」（裁示 14，第 54 行）→ 本片無網頁畫面。
- 憲法原則 2＋任務交辦：「平台不啟動程式」（`test_scope.py` TC-071）→ 刪除由代理執行；`rm -rf` 這串字在整個 `abf_station/` 只准出現在新檔 `clean.py`。
- 「每個寫入要本人答應」（憲法 6／ADR 0006，引自 `017d-launch-composed.md` 第 26 行）→ 代理端的第一步永遠是 `launch.verify_confirmation`。

## 範圍：檔案（只准改這些，共 5 個含 ledger）
- `platform/abf_station/clean.py`（新；檔首 `# Nothing existing: …`）：`KEYS`、`ATTEMPT`、`expected_work(...)`、`run_clean(job, ctx)`、`_clean_slurm(...)`、遠端指令樣板與結束碼對照。**全套件唯一**出現 `rm -rf` 字樣的檔案。
- `platform/abf_station/handlers.py`：只改頂部 import（:13）、`JOB_KINDS`（:16）加 `"clean_work"`、`ARG_KEYS`（:17-18）加 `"clean_work": launch.LAUNCH_KEYS`、`handle()` 的 `cancel_run` 分派旁（:50-51）加一行 `if kind == "clean_work": return clean.run_clean(job, ctx)`、模組開頭說明文字補一句；不動其他種類。
- `platform/tests/station_harness.py`：只加 `FakeSite` 的假 `squeue` 對 `-u <user> -o %Z`（印出該使用者各工作的工作目錄，一行一個）的支援；既有 `-j`、`-n` 行為與輸出一個位元都不動；刪除記錄沿用已有的 `destructive.log`（`destructive_log=True`，:167-170）。
- `platform/tests/test_station_clean.py`（新；檔首 `# Nothing existing: …`，TC-070；以 `platform/tests/test_station_cancel.py` 為樣板：`FakeSite`、`job_of`、`run_job`、`bundle_for` 取自 `test_station_launch`）。
- `specs/cloud-cleanup-c/ledger.md`。

**禁碰**：`abf_station/launch.py`／`cancel.py`／`gcb_launch.py`／`gcb_preflight.py`／`site.py`／`rules.py`（只讀它們的函式）、`platform/abf_platform/*`、`platform/abf_launch/*`、`tests/no_second_run_state_test.sh`（`LAUNCH_ALLOW` 維持一筆）、既有測試檔（若 `handlers.JOB_KINDS` 多一種讓某個既有斷言變紅，executor 先停手回報，列出是哪一條；本計畫起草時用 `JOB_KINDS`、`this agent does` 在 `platform/tests/` 搜過，只有 `test_run_diag_tools.py:466` 的成員檢查，不受影響）。Google Batch 的清理是 d 片，本片遇到 Google Batch 的內容包只回拒絕。

## 作法
1. **內容包（由平台在 f 片建立，這裡先釘死形狀）**：鍵集合恰為 `KEYS = {"version", "run_name", "slurm_job_id", "run_folder", "agent", "ce", "work"}`（與 `cancel.KEYS` 同形，`cancel.py:14`，多一個 `work`）。`ce` 是 `snapshot_ce` 的結果，`workDir` 取自這個內容包（與 `cancel.py` 一樣：內容雜湊保證它就是使用者按送出時看到的那份，`rules.clean_root` 保證它是合規路徑）。
2. **順序固定，每步失敗就停、不重試**：
   1. `bundle = launch.verify_confirmation(job, ctx, "clean_work")`（:955；沒有憑證／雜湊不符／已用過／種類不是 `clean_work` → `rules.Refusal`，**此時什麼都還沒做**）。
   2. `set(bundle) == KEYS`；`bundle["agent"] == ctx.agent_name`；`ce.platform` 是 Google Batch → 回拒絕「Google Batch 的清理尚未支援（cloud-cleanup-d）」（d 片改成分派）；其他非 Slurm → `rules.clean_environment` 自己會拒。
   3. `env = rules.clean_environment(bundle["ce"])`；`run = bundle["run_name"]` 必須符合 `launch.RUN_NAME`（:33）；`bundle["slurm_job_id"]` 是 1 到 2^31-1 的整數（非布林）。
   4. **路徑重算（逐字比對，不正規化、不容許結尾斜線）**，以下任何一項不符 → `rules.Refusal`，一條遠端指令都不送：
      - `folder = bundle["run_folder"]`：`rules.path_problem(folder)` 為 `None`；`rules.normalize(folder) == folder`；`os.path.dirname(folder) == env["workDir"] + "/runs"`；`leaf = os.path.basename(folder)` 符合 `RUN_NAME`。
      - **run 與資料夾的關係（舊計畫漏掉的一條）**：`run == leaf`（第一次送出的 run），**或** `run == leaf[:64 - len(sfx)] + sfx`，其中 `sfx` 是 `run` 結尾的 `-a<N>`（`ATTEMPT = re.compile(r"-a([0-9]{1,4})\Z")`，N≥2；公式與平台的 `build.attempt_name` :321 相同）。理由：續跑（resume）的那一次叫 `<原名>-a2`，但**用的是原本那個資料夾**（`launch.py:904` `"run_folder": origin["run_folder"]`），work 也在那裡；若照「資料夾 = `runs/<run 名稱>`」去比，續跑成功的 run 永遠清不了（還會誤以為是路徑被竄改）。
      - `bundle["work"] == folder + "/work"`（逐字）；以 `/` 切開 `work` 的各段，**不得**有 `rawdata`、`results`、`analysis`、`..`、`.` 任何一段，最後一段必須是 `work`。（連上層段也算：若 `workDir` 本身含 `results` 段，所有清理都會被拒——這是刻意的保守，文件要寫。）
   5. `user = cancel.site_user(ctx.settings_file)`，必須符合 `^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\Z`（同 `cancel.py` :39-41）；沒有就拒絕「部署設定沒有 site_user」。
   6. 工作期限：`launch._left(ctx, job) < launch._min_remaining()`（:979、:987）→ 拒絕；遠端指令逾時 `timeout = int(min(300, left - 15))`。
   7. **一條遠端指令** `res = ctx.site.call([cmd], timeout=timeout)`，`cmd` 是固定樣板，只有 `folder`、`user`、`folder + "/work"` 三個值經 `quote()` 代入（`site.py:28`），刪除的對象寫死是字面的 `work`（相對於 `cd` 之後的目前目錄，不是變數）。多行複合指令有先例：`launch._probe`（:1222）。樣板依序（每行一個判斷，`F`＝folder、`U`＝user）：
      ```
      cd -- F || exit 11
      test "$(realpath -- .)" = F || exit 12
      q=$(squeue -h -u U -o %Z 2>&1) || exit 18
      printf '%s\n' "$q" | grep -qxF -- F && exit 13
      test -d work || exit 20
      test ! -L work || exit 14
      test "$(realpath -- work)" = F/work || exit 15
      test "$(stat -c %U work)" = U || exit 16
      if [ -d results ] && find results -type l -lname '*/work/*' | grep -q . ; then exit 17; fi
      rm -rf --one-file-system -- work
      ```
      （上面是意思；executor 寫成單一字串，保持**一條**指令、`;`／換行串接、不用變數替換路徑給 `rm`。第 4 行是「你在 Slurm 上還有工作的工作目錄就是這個資料夾」——涵蓋主控程序、以及同一個資料夾的其他次續跑；比舊計畫的 `squeue -h -j <number>` 更穩，因為工作結束一段時間後 `squeue -j` 會回「無效工作編號」而不是空輸出。）
   8. **結果碼對照（每個碼一句白話，指出是哪一項不符）**：11 進不了資料夾；12 資料夾本身或上層是捷徑；13 你在這個資料夾裡還有 Slurm 工作；14 `work` 本身是捷徑；15 `work` 的真實位置不是預期的；16 `work` 的擁有者不是 `site_user`；17 `results` 裡有指向 `work` 的捷徑（`publishDir` 用連結模式），刪了會讓結果壞掉；18 問不到 Slurm 佇列、無法確認工作已結束。以上全部 → `rules.Refusal`，訊息含「沒有改動任何東西」。`20`（沒有 `work` 目錄）→ 成功且 `cleaned: true`，不刪任何東西。`0` → 成功。其他非零 → `error`，訊息含結束碼與「可能只刪了一部分；work_cleaned_at 沒記，可以再申請」，**不重試**。`res.timed_out` → `error`「逾時，可能只刪了一部分」。
   9. 成功回 `("done", {"ok": True, "cleaned": True, "run_name": run, "message": "已刪除 <folder>/work；results 沒有動"})`。代理回給平台的永遠是自己的短句，不轉貼站台原始輸出。
3. `rm -rf` 對 `work` 內部的連結只刪連結本身、不跟進去（Nextflow 的 work 裡有許多指向輸入檔的連結，這是預期行為，手算範例 11）；`--one-file-system` 防止跨掛載點。　4. **migration**：不需要（本片不碰資料結構）。

### 手算範例（路徑／實況 → 結果；verifier 直接拿去出題）
環境 `workDir=/work/u1/abf`，`site_user=tester`；資料夾 `F=/work/u1/abf/runs/ampliseq-d5`，run `ampliseq-d5`，除非另註。

| # | 內容包的 `work`（或叢集上的實況） | 結果 | 為什麼 |
|---|---|---|---|
| 1 | `F/work` | **刪除** | 與重算值逐字相等、最後一段是 `work` |
| 2 | `F/work/` | 拒絕 | 不是逐字相等（結尾斜線） |
| 3 | `F/results` | 拒絕 | 含 `results`、最後一段不是 `work` |
| 4 | `F/work/../results` | 拒絕 | 含 `..` |
| 5 | `/work/u1/abf/rawdata` | 拒絕 | 含 `rawdata`、不等於重算值 |
| 6 | `F`（整個 run 資料夾） | 拒絕 | 最後一段不是 `work` |
| 7 | `/work/u1/abf/runs/other-run/work`（folder 仍是 `F`） | 拒絕 | 與重算值不同 |
| 8 | `/work/u1/abf/analysis/work` | 拒絕 | 含 `analysis` |
| 9 | 叢集上 `F/work` 其實是連到 `F/results` 的連結 | 拒絕（碼 14） | `test ! -L work` |
| 10 | 叢集上 `F` 的上層被換成連結（`realpath .` ≠ F） | 拒絕（碼 12） | 真實位置不符 |
| 11 | `work` 內有連到 `/work/u1/abf/rawdata/x.fastq.gz` 的連結 | **刪除** | 只刪連結，`rawdata/x.fastq.gz` 還在 |
| 12 | `F/results/a.tsv` 是連到 `F/work/ab/cdef/a.tsv` 的連結 | 拒絕（碼 17） | 刪了結果會壞 |
| 13 | `squeue -u tester -o %Z` 列出 `F` | 拒絕（碼 13） | 工作還在這個資料夾裡 |
| 14 | `F/work` 不存在 | **成功，`cleaned: true`**，不刪任何東西（碼 20） | 已經沒有東西 |
| 15 | `F/work` 的擁有者不是 `tester` | 拒絕（碼 16） | 不是你的 |
| 16 | run=`ampliseq-d5-a2`、`run_folder=F`、`work=F/work` | **刪除** | 續跑那一次用原資料夾；`-a2` 符合公式 |
| 17 | run=`other-a2`、`run_folder=F` | 拒絕 | 名稱和資料夾的 leaf 對不上 |
| 18 | 64 字元的 leaf `L`，run=`L[:61]+"-a2"`，`run_folder=…/runs/L` | **刪除** | 平台截斷長名字的公式 |
| 19 | `workDir=/work/u1/results/abf` | 拒絕 | 路徑含 `results` 段（保守） |
| 20 | `squeue` 失敗（`squeue_fail`） | 拒絕（碼 18） | 無法確認已結束 |
| 21 | `run_folder=/work/u1/abf/runs/x/y` | 拒絕 | 不是 `workDir/runs/<名稱>` 的形狀 |

## 失敗先行測試（現在都會紅；新檔 `test_station_clean.py`，預估 38 條 TC：拒絕表 21 列參數化＋下列 17 條）
未確認：
- `test_unconfirmed_clean_is_refused_and_nothing_is_sent`：沒有憑證／雜湊不符／憑證已用過／憑證種類是 `launch`／憑證種類是 `cancel`（五種）→ `refused`；`site.calls()` 沒有任何遠端指令、`destructive()` 為空。
內容包與身分：
- `test_a_bundle_with_other_keys_a_missing_key_a_wrong_agent_is_refused`（三條）。
- `test_a_hostile_run_name_or_workdir_or_folder_is_refused_before_any_command`（空白、`;`、`$()`、反引號、換行、BIDI 字元、過長、`..`）。
- `test_a_google_batch_bundle_is_refused_in_plain_words_and_nothing_is_sent`（d 片會改掉這一條，屬有意）。
- `test_a_missing_site_user_is_refused_in_plain_words`；`test_too_little_deadline_left_is_refused_before_any_command`。
刪除行為：
- `test_every_row_of_the_hand_check_table`：上表 1–21 逐列（參數化），斷言結果狀態與 `site.destructive()`。
- `test_exactly_one_remote_command_and_exactly_one_rm_whose_only_target_is_the_word_work`：成功案例 `site.calls()` 恰一個 `on_site` 呼叫、`destructive()` 恰一行、對象是 `work`、含 `--one-file-system`、沒有 `*`、沒有 `$`。
- `test_nothing_outside_work_changes`：用 `snapshot(root)` 比對，`results/`、`rawdata/`、`analysis/`（含 `guard.txt`）與 `work` 之外的檔案位元級不變。
- `test_links_inside_work_are_removed_but_their_targets_stay`（範例 11）。
- `test_the_remote_command_is_one_fixed_template_and_only_three_values_vary`（把三個值換掉後與樣板比對）。
- `test_each_exit_code_has_its_own_plain_sentence_and_none_echoes_the_sites_raw_output`。
- `test_timeout_is_reported_as_possibly_partial_and_is_not_retried`；`test_an_unknown_nonzero_exit_is_an_error_with_the_code_and_no_retry`。
- `test_a_second_run_of_the_same_confirmed_job_is_refused`（`ctx.used_confirmations`）。
範圍與憲法：
- `test_rm_rf_appears_only_in_clean_py_among_the_station_files`（掃 `abf_station/*.py`）。
- `test_the_launch_allow_list_still_has_one_entry`（讀 `tests/no_second_run_state_test.sh`，`LAUNCH_ALLOW` 仍只有 `platform/abf_station/launch.py` 一筆）。
- `test_the_handler_lists_clean_work_with_launch_keys_and_still_refuses_unknown_kinds_and_extra_arguments`。
- `test_the_fake_squeue_old_behaviour_is_unchanged`（`-j`、`-n` 的輸出與本片之前相同）。

## 完成標準（done when）
- 自動：新測試綠；全套綠（含 `tests/platform_test.sh`、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`）；MCP 工具數仍 12；`git diff --name-only` 只有「範圍：檔案」所列；Slurm 的送出、取消、續跑的內容包、畫面、`head.sh` 與 golden 位元級不變（`git diff --stat` 貼進 ledger，依 dev-plans 通例由 verifier 核對並重跑）。
- 手動：無（平台端 f 片之後才有入口；真實 nano4 驗收放在 f 片）。**但請 executor 在 ledger 記下：在假站台上 `rm -rf --one-file-system` 與 `realpath`、`stat -c %U`、`find -lname` 的行為與真實叢集（GNU coreutils）是否一致的已知差異**；有疑慮的列為 f 片手動驗收的一項。
- 文件：無（`docs/` 在 f 片一次更新）。

## 環境事實
（行號為 `origin/v3` @ `279363b`；以函式名為準，動手前 `git fetch -q origin` 再核對。）
- 鏡像對象：`abf_station/cancel.py`（`KEYS` :14、`site_user` :17、`run_cancel` :24；一次 `squeue` 問清楚才送一次 `scancel`）；`handlers.py` `JOB_KINDS` :16、`ARG_KEYS` :17-18、`handle` :34（`cancel_run` 分派 :50-51、不支援種類的拒絕訊息 :41）；`launch.verify_confirmation` :955（沒有憑證 :962、沒有記錄 :964、種類不符或已用過 :966、雜湊 :970-972、同一份憑證用過 :973-975）。
- 代理能用的兩種「碰外面」的方法，不要新增第三種：`Site.call`（`site.py:61`，經站台指令稿 `on_site.sh` 在叢集上執行一條指令；預設逾時 `ON_SITE_TIMEOUT`，可用 `timeout=` 調；逾時回 `timed_out=True`）與 `run_fixed`（`site.py:91`；本片用不到）。`quote()` 在 `site.py:28`。
- 路徑公式：Slurm 的 `run_folder = "%s/runs/%s" % (workDir, run_name)`（`launch.py:499`，第一次送出）；續跑沿用原資料夾（`launch.py:904`），其 `run_name` 是 `<root>-a<N>`（`build.py:321` `attempt_name`）；主控工作 `#SBATCH -D <run_folder>` 並 `cd` 進去（`launch.py:424`、:432）；結果在 `<run_folder>/results`（`_params_yaml` :403-406 的 `outdir`）。`nextflow.config` 沒有 `workDir`，所以 Nextflow 預設的 work 是 `<run_folder>/work`。**查不到**：國網站台設定檔（`$NFCORE_SITE_CONFIG`）有沒有改 `workDir`——這個假設的真實驗收在 f 片手動項 2，不通過就停手回報，不要在程式裡猜替代路徑。
- 規則：`rules.py` `path_problem` :23、`normalize` :51、`clean_root` :76、`clean_environment` :90。
- **既有 `cancel` 對續跑那一次的行為（旁註，不在本片範圍）**：`cancel.py` 驗 `folder == "%s/runs/%s" % (workDir, run)`，而續跑那一次的 `run_folder` 是原資料夾、`run` 是 `<原名>-a2`，兩者不等，所以取消一個正在跑的續跑看起來會被拒絕。我只讀了程式沒有實測；列在給維護者的問題，不在本片修。
- 假站台：`station_harness.py` `FakeSite`（:55；`destructive_log=True` :58-61，把 `rm`、`rmdir`、`mv`、`tar` 包起來記到 `destructive.log` :167-170；`calls()` :287；`destructive()` :315）；假 `squeue` :146-153 只懂 `-j <id>`、`-n <name>`，輸出一律是 `名稱|使用者|工作目錄`，所以本片要加 `-u` 與 `-o %Z`。`TOOLS`（:20-24）已含 `realpath`、`readlink`、`stat`、`find`、`grep`、`head`、`rm`。
- 憲法掃描：`test_scope.py` TC-071 與 TC-061 掃的是 `abf_platform/`（`_sources()` :19-20）；`abf_station/` 只受 TC-070 檔頭規則（`_header_sources()` :23-25）與 `tests/no_second_run_state_test.sh`（送出字樣只認 `sbatch/qsub/bsub/srun/nextflow run/tw launch`，`rm` 不在內）。
- 新 `.py` 檔前 40 行要有 `# Nothing existing: <≥15 字理由>`（TC-070）：`clean.py`、`test_station_clean.py`。`clean.py` 的理由寫「要刪的只有一個固定位置的目錄，且要在本人確認後由代理逐項核對路徑；`nextflow clean` 要啟動 Nextflow 並信任它的快取、`rclone purge` 不核對路徑、Seqera Platform 的刪除是它雲端服務的功能，都不符合」。**起草時沒有重新連網查證這三者**，只憑已知文件；executor 動手前各讀一次官方說明頁並把網址寫進 ledger，與這句不符就停手回報。

## 不做
- 不做 Google Batch（d 片）；不做平台端的任何事（a、b 已完成；建立申請在 f）；不做確認頁（e）。
- 不刪、不移動、不改 `results/`、`rawdata/`、`analysis/`、run 資料夾本身、`.nextflow*`、`head.sh`、`slurm-*.out` 等任何 `work` 以外的東西；不做「刪整個 run」「刪結果」的選項，也不做旗標。
- 不用 `nextflow clean`（它依賴 run 資料夾裡的快取資料庫，刪的範圍不由我們的路徑檢查決定）。；不做批次清、部分清（只清某幾個 task 目錄）、失敗／中止／失聯 run 的清理（失敗的 run 要靠 work 續跑）。；不重試、不加迴圈、不加執行緒；不新增 `site` 呼叫方式；不改 `launch.py`／`cancel.py`。

## 裁決（2026-10-24，developer-agent；已併入上文，與其他段落不衝突）
1. **只刪「字面叫 `work` 的那一個目錄」，而且由代理重算後逐字比對。** 內容包裡的 `work` 只是「被顯示、被雜湊、被確認」的那一份，不是被信任的輸入。遠端指令對 `work` 用相對名稱（先 `cd` 到已驗證的 run 資料夾），不把可變路徑交給 `rm`。
2. **用刪掉字面目錄的做法，不用 `nextflow clean`。** 理由見「不做」。
3. **Slurm 的 work 目錄位置是假設，列為手動驗收（f 片項 2）。** 代理以內容包記下的 `workDir`（經 `rules.clean_root`）為準，不自己推別的路徑。
4. **逾時／錯誤／拒絕都不記為已清、不重試。** 代理只回答；記帳是平台（b 片）。
5. **舊計畫的「Slurm 與 Google Batch 共用一條 `work_target` 公式」在 Slurm 這邊不成立，改寫為：Slurm 的 work 在 `run_folder/work`（`run_folder` 取自 hand-off 紀錄，續跑沿用原資料夾），Google Batch 的在 `<workDir>/runs/<run>/work`（d 片）。** 理由：續跑那一次的 `run_name`（`-a2`）和資料夾名不同，舊公式 `<workDir>/runs/<run_name>/work` 會指向不存在的位置，並且讓續跑成功的 run 永遠清不了。
6. **舊計畫的 `squeue -h -j <number>` 改為 `squeue -h -u <user> -o %Z` 並比對資料夾。** 理由：涵蓋同一資料夾的其他次續跑，而且不受已結束工作的編號被 Slurm 回收／回報「無效編號」影響。
7. **`rm -rf` 在 Lustre 上的耗時未實測**：遠端指令逾時上限 300 秒、平台端工作期限 600 秒（b 片）；逾時回「可能只刪了一部分」，使用者可再申請。若手動驗收發現常常不夠，再調，不在程式裡加重試迴圈。
8. **切片理由**：舊計畫約 30 檔、需求超過 60 條測試；依 `dev-architecture-review-2026-10-24.md` §3 與 `dev-plans/README.md` 通例切成六片。本片 5 檔（含 ledger）。

## 裁決二（2026-10-25，回應第一趟 BLOCKED）
1. test_onboarding_doc 的紅已由 #218 修掉：developer-agent 已把 origin/v3 合進本分支，重跑即可，不必碰該測試。
2. **樣板第 9 行改成「find 失敗就停」**（刪除動作的安全網不准在檢查出錯時放行）：`if [ -d results ]; then l=$(find results -type l -lname '*/work/*' -print) || exit 17; [ -n "$l" ] && exit 17; fi`。find 自己出錯與找到連結一樣回碼 17（保守，不新增碼）。合約要有一條：假 find 失敗（例如 results 內有不可讀子目錄）→ 碼 17、work 沒有被刪。
3. `*/work/*` 誤判指向 rawdata 的連結（workDir 本身在 /work 底下）偏保守、不會誤刪，本片接受、不改；寫進 ledger 留給之後。
4. MCP 工具數以既有測試為準（14），計畫寫 12 是筆誤，平台端不動。
5. 「路徑重算失敗」與碼 20 的訊息用詞照 verifier 合約現行斷言（非空、白話、未送遠端指令／done 且未刪任何東西）即可。

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
