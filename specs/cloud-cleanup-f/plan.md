---
id: cloud-cleanup-f
title: run 成功的當下，平台為它自己的主人提出一張「清掉中間檔」的待確認申請（Slurm 與 Google Batch），連同文件與真實驗收
tier: B
kinds: backend
lane: L-cleanup
after: cloud-cleanup-c, cloud-cleanup-d, cloud-cleanup-e
base: v3
---

# cloud-cleanup-f

> 本檔由 developer-agent 起草（2026-10-24），`cloud-cleanup.md` 切成六片之最後一片（a 資料庫 → b 平台記帳 → c 代理刪 Slurm 的 work → d 代理刪 Google Batch 的 work → e 確認頁與看板通知 → **f 成功後提出申請＋文件**）。**本片是把整件事接上線的那一片**：run 成功（收件端收到 `complete`）時，平台為該 run 的擁有者建一張 `clean_work` 待確認申請；之後的每一步（確認頁、佇列、代理核對與刪除、記帳）前五片都已完成。本片不動任何網頁畫面（e 片已做），B 級（後端行為改變）→ verifier 通過＋CI 綠即可合併；**但文件裡的手動驗收要由維護者在自己的測試 run 上做完**才算完成（見完成標準）。
> **名詞**：「work 目錄」＝Nextflow 放每個 task 中間檔的 `work/`，不是結果；「申請」＝待確認的 `clean_work`（`confirmations.state='pending'`），本人在確認頁按「確認刪除」之前不是確認、也不產生工作。平台程式碼（`abf_platform/`、`abf_launch/`）裡一律寫「代理／agent」，不得出現 TC-061 禁用的那個英文字（`test_scope.py:189`）。
> **派工前提**：c、d、e 都已合併（有代理能刪、有頁面能按）。**不可更早合併**：否則會建出一張「按了會失敗」或「寫著取消的刪除」的申請。

## 目標
一個 run 成功跑完後，平台自己提出「這次 run 的 work 目錄可以刪了」，等本人在確認頁按「確認刪除」，代理才去刪；沒按就什麼都不刪。對使用者的意義：Nextflow 的中間檔常比結果大很多倍（雲端是 bucket 儲存費、nano4 是 /work 配額），但現在沒有安全的收拾辦法。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md` 與 `CLAUDE.md`；每句至少對應一條測試案例：
- 「**跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪**」（裁示 16，第 58 行）→ ①只有成功的 run 才提出②刪 work 一定經本人確認，沒有任何自動路徑（無排程、無「N 天後自動」、無 POLICY 通道）③「結果」不在這次刪除範圍。
- 「**C-7 `cloud-cleanup`**（B／backend）：succeeded 後建「刪除 work 目錄」的待確認請求（走 `_ask`，新 kind `clean_work`；對 nano4 也適用）；結果到期（30 天）前 7 天建 Decision-needed 通知，不自動刪；費用頁顯示儲存月費。files：`confirm.py`、`jobs.py`、`actions/__init__.py`、`web_board.py` 通知、`test_cleanup.py`」（第 171 行）→ 只有 `succeeded` 才建；種類 `clean_work`；Slurm（nano4）與 Google Batch 兩種都適用。**後半（30 天到期前提醒、費用頁儲存月費）不在本任務**（見「不做」）。
- 「直接 `scancel`，以及刪改叢集端 `rawdata`／`results`／`analysis`，一律擋住」（`CLAUDE.md` §3.4）→ 提出的內容包裡的路徑一律是 `…/work`；任何含 `rawdata`、`results`、`analysis` 的路徑平台根本不會提出。
- 「網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併，事後列進每日清單；網頁畫面仍等他回好／不好」（裁示 14，第 54 行）→ 本片無網頁畫面（確認畫面的**文字**是 `clean_screen` 產生的，會顯示在 e 片的頁面上：這幾句話合併前附截圖列進每日清單，維護者回好／不好）。
- 憲法原則 2＋任務交辦：「平台不啟動程式」（TC-071、TC-061）→ 平台程式碼只組資料、記帳；不含 `subprocess`、`rm -`、`storage rm`、`rmtree`，也不含 TC-061 禁用字。
- 「每個寫入要本人答應」（憲法 6／ADR 0006，引自 `017d-launch-composed.md` 第 26 行）→ 沒有 `clean_work` 的確認就沒有任何檔案被動。

## 範圍：檔案（只准改這些，共 7 個含 ledger）
- `platform/abf_launch/build.py`：新增 `prepare_clean(state, run, owner=None)`（仿 `prepare_cancel` :275）與 `clean_screen(bundle, row)`（仿 `cancel_screen` :640，用 `terminal.PREFIX`／`pair`／`esc`）、`clean_work_path(view_snapshot, row)`；`target_problem`（:125）不改（它吃 kind 字串）。
- `platform/abf_platform/actions/__init__.py`：新增 `offer_cleanup(platform_path, index_path, run_name, *, clock=time.time)`（寫「建立待確認申請」，**不是 MCP 工具、不是 `request_*`**）。
- `platform/abf_platform/receiver.py`：`complete`（:230）在 run 成功時呼叫 `offer_cleanup`（見作法 4）。
- `docs/PLATFORM.md`：新增「Cleaning a finished run's work folder」小節（放在 `### Forget (keep-submissions)` :415 之後、`### Resume and relaunch` :427 之前），並更正兩句既有敘述（見作法 7）。
- `docs/TESTING.md`：新增「cloud-cleanup」小節（含手動驗收）；更正第 158 行那句 `(rm is not a job kind, and no job kind writes.)`。
- `platform/tests/test_cleanup_offer.py`（新；檔首 `# Nothing existing: …`，TC-070；端到端段落以 `platform/tests/test_launch_e2e.py` 的 `FakeSite(destructive_log=True)` 夾具與 `test_gcb_launch.py` 的 `Box` 夾具為樣板）。
- `specs/cloud-cleanup-f/ledger.md`。

**禁碰**：`store.py`、`confirm.py`、`jobs.py`（a、b 已完成）、`web.py`、`web_board.py`（e 已完成）、`abf_station/*`（c、d 已完成）、`cli.py`（兩個都不碰）、`records.py`、`cloud_cost.py`、`compute_envs.py`、`mcp_server.py`、`guidance.py`、`actions/chat_tools.py`、`tests/no_second_run_state_test.sh`、`test_actions_layer.py` 等既有測試（除非下列「必須更新」）。

**必須更新的既有斷言**：預計沒有（本片只加函式與文件）。docs 會被幾個既有測試讀：`test_gcb_launch.py:1146-1175`、`test_gcb_ce.py:854-880`（要求 PLATFORM.md 仍含 "Slurm-like confirmed launch and cancel on the platform host (resume: not yet)"、"Slurm and Google Cloud Batch can run; the other types can be modelled only" 等字串）、`test_actions_layer.py:600-606`（Action layer 小節 <30 行）、`test_failures.py:285`、`test_catalogue.py:413`。**文件改動不得動到這些被釘住的字**；若有紅，改文件不改測試。另外 `docs/PLATFORM.md:8`、`:136` 與 `docs/TESTING.md:158` 三句被更正的話，起草時用 `never deletes`、`delete, move`、`no job kind` 搜過 `platform/tests/`、`tests/`、`docs/`，沒有測試釘住它們（只有文件本身出現）；executor 動手前再搜一次，若有命中就列進 PR 說明。

## 作法
1. **申請的內容（`build.prepare_clean`，純資料）**。內容包鍵恰為 `version, run_name, slurm_job_id, run_folder, agent, ce, work`（與 c 片 `KEYS` 一致；`version` 為 1）。`ce = bundle_mod.snapshot_ce(compute_envs.get(state, row["ce"]))`。`work` 的公式**有兩條**，不是一條（舊計畫寫成一條，但續跑會讓它錯）：
   - Slurm：`row["run_folder"] + "/work"`（`run_folder` 取自 hand-off 紀錄；續跑那一次沿用原資料夾，所以不能用 `<workDir>/runs/<run_name>/work`）。
   - Google Batch：`"%s/runs/%s/work" % (ce["workDir"], row["run_name"])`（`gs://…`；與 `render_gcb_bundle` 的 `base + "/work"` 同一個位置；d 片的代理用同一條公式重算）。
   `prepare_clean` 拒絕（`build.Refusal`，白話）的情形：不是這位擁有者從平台送出的 run（比照 `prepare_cancel` :281-286）、hand-off 紀錄沒有編號、`work_cleaned_at` 已有值（「已經清過了」）、環境找不到、環境現在的代理不是當初送出的代理、`target_problem(…, "clean_work", owner)` 有問題、**環境的 `workDir` 在送出之後改過了**（用 `jobs.launch_content(con, row, job)`〔`jobs.py:385`〕取得當初送出的內容包，比對 `bundle["ce"]["workDir"]` 與現在的 `ce["workDir"]`，不同就拒絕；Slurm 另外要求 `os.path.dirname(row["run_folder"]) == ce["workDir"] + "/runs"`）、找不到當初送出的內容（無法確認環境沒變，不提出）、這個 run 已被擁有者 `forget`（`jobs.run_forgotten`）。理由：Google Batch 的紀錄沒有存 bucket 路徑，若環境之後被改成別的 `workDir`，用現在的環境算出來的路徑就不是這個 run 的 work。
2. **誰來建申請、何時建**（`actions.offer_cleanup`）：`complete` 當下，為**一個** run：
   1. 讀 hand-off 紀錄 `jobs.latest_launch(con, run_name)`（`jobs.py:296`；用 `store.open_readonly`，檔案不存在就返回，**不建立任何檔案**）：沒有紀錄、`user_id` 為空（沒有擁有者的 run，例如純終端機送出——確認頁要登入的使用者才按得下去，**不支援，畫面與文件寫明**）、`slurm_job_id` 為空、`work_cleaned_at` 已有值 → 靜靜跳過。
   2. `status.find_run(index_path, run_name)` 的狀態恰為 `succeeded`（`status.py`；`failed`、`aborted`（Nextflow 視為失敗）、`lost`、`running` 一律不提——失敗的 run 要靠 work 續跑）。
   3. `build.prepare_clean(platform_path, run_name, owner=row["user_id"])` 通過。
   4. `confirm.create_pending(platform_path, "clean_work", ce_name, bundle, build.as_text(build.clean_screen(bundle, row)), row["user_id"], clock)`（b 片：7 天有效、不佔 10 張名額）。已有未逾時的同內容申請就回既有的（`create_pending` 依 sha 重用），所以多次呼叫不會多建。
   任何一項不過、任何例外（`JobRefused`、`build.Refusal`、`sqlite3.Error`、其他）都**靜靜跳過並回 `{"offered": False, "reason": …}`**，絕不丟出去。
3. **只有 `succeeded` 才提**，且**一個 run 成功只提一次**：觸發點是收件端的 `complete`，沒有排程、沒有常駐迴圈、沒有網頁 GET 的副作用。申請 7 天內沒按就逾時，之後**不會自動重提**（見裁決 4）。過去已經成功的 run（本功能上線之前成功的）也**不會被提**，因為沒有觸發點（見給維護者的問題）。
4. **接收端接線（`receiver.complete`）**：在 `with con:` 區塊與 `finally: con.close()` 之後、`store.end_token` 之前或之後皆可（以不影響回應為準），`if succeeded and trow["run_name"] is not None:` 呼叫 `actions.offer_cleanup(platform_path, index_path, trow["run_name"], clock=clock)`，整個包在 `try/except Exception: pass`。`import` 放在函式內（`receiver.py` 現在只 import `agents, common, store`，避免循環匯入）。回應 `{"status": "OK"}` 與 token 的結束行為一個位元都不變；offer 失敗不影響 run 的紀錄。`token new` 做的 token（`run_name` 為空）不是替某個 run 發的，不提。平台資料庫不存在時不建立它。
5. **確認畫面（`clean_screen`）必須逐字含的白話**（Slurm 與 Google Batch 共用的前三句，及 Google Batch 另加的第四句）：
   ① 「這會永久刪除這次 run 的中間檔資料夾：」＋完整路徑（`work`）；
   ② 「結果（results）、原始資料與分析資料夾不會被動。」；
   ③ 「刪掉之後這個 run 不能再續跑（-resume）；要再算一次，請當成新分析重新送出。」——**這句改寫過**：舊計畫寫「要重算只能原樣重跑或重新送出」，但 `build._predecessor` 對 `succeeded` 的 run 一律拒絕續跑與重跑（`build.py:353`「已成功，不需要…」），所以成功的 run 本來就不能續跑或原樣重跑，唯一的辦法是 `launch` 當新分析；
   ④（只有 Google Batch）「刪除的是 bucket 裡這個前綴下的物件。」＋executor 依 d 片 ledger 裡官方文件對**軟刪除／版本控制**的結論補一句如實的說明；**不得寫「無法還原」，除非 d 片 ledger 證實預設就無法還原**（舊計畫寫了「無法還原」，起草時未查證）。
   ⑤ 不得出現任何金額（本任務不顯示費用）；畫面上也沒有 Slurm 工作編號以外的內部詞（`Traceback`、`SELECT`、`args_json` 等）。
6. **migration**：不需要（a 片已完成；本片不改資料結構）。
7. **文件**：`docs/PLATFORM.md` 新小節寫明：何時提（收到 `complete` 且成功）、對誰（run 的擁有者；沒有擁有者不提）、刪哪個目錄（Slurm＝`<run 資料夾>/work`；Google Batch＝bucket 裡 `…/runs/<run>/work/` 前綴）、不刪什麼（`results`、`rawdata`、`analysis`）、為什麼是代理刪（平台不啟動程式）、申請 7 天有效且過期不重提、刪了之後這個 run 不能續跑、`publishDir` 用連結模式時代理會拒絕（結束碼 17）、Google Batch 刪的是 bucket 前綴且軟刪除的說明、過去成功的 run 不會被提。更正兩句既有敘述：第 8 行 `It never deletes a run, a run folder or a result on the site` 改為 `It never deletes a run folder or a result on the site; the only thing it can have deleted is the work folder of a finished run, and only after its owner's yes (see "Cleaning a finished run's work folder")`；第 136 行（代理最初的唯讀敘述，`### Start it` 之前那段）若仍在描述「現在的代理」，改成指向新小節，executor 先讀上下文判斷（這句在 launch 出現後本來就已過時）。範例路徑只用 `/work/u1/abf`、`gs://lab-bucket/work`、`ampliseq-d5`。`docs/TESTING.md` 新小節「cloud-cleanup」寫明手動驗收 1–4；第 158 行改為 `(Only a finished run's work folder can be deleted, and only after its owner's yes; see cloud-cleanup.)`。

## 失敗先行測試（現在都會紅；新檔 `test_cleanup_offer.py`，預估 40 條 TC）
內容包與畫面（`build`）：
- `test_slurm_bundle_has_the_seven_keys_and_work_is_the_run_folder_plus_work`；`test_a_resume_attempt_gets_the_origin_folders_work_not_a_folder_named_after_the_attempt`。
- `test_gcb_bundle_work_is_workdir_runs_run_work_and_matches_what_the_agent_recomputes`（與 d 片 `expected` 公式同值）。
- `test_prepare_clean_refuses_each_unfit_case_in_plain_words`（別人的 run、無編號、已清過、環境找不到、代理換了、環境停用、`workDir` 改過〔Slurm 與 Google Batch 各一〕、找不到當初的內容、被 forget；九條，訊息不含 SQL／路徑堆疊）。
- `test_the_bundle_is_identical_when_built_twice`（雜湊穩定）。
- `test_the_screen_says_what_is_deleted_what_is_not_and_that_resume_is_gone`（①②③ 的逐字關鍵語）；`test_only_the_gcb_screen_has_the_bucket_sentence_and_it_never_says_cannot_be_undone_unless_the_ledger_proved_it`；`test_the_screen_has_no_money_and_no_internal_words`。
提出（`offer_cleanup`）：
- `test_a_succeeded_run_gets_one_pending_clean_work_request_and_nothing_else`（`jobs` 表列數不變）；`test_offering_again_makes_no_second_request`。
- `test_failed_aborted_lost_running_and_unknown_runs_get_no_request`（五條）。
- `test_a_run_without_an_owner_gets_no_request`；`test_another_users_run_is_not_offered_to_the_caller`（只提給 `user_id` 本人）。
- `test_a_run_whose_work_was_cleaned_gets_no_request`；`test_a_forgotten_run_gets_no_request`。
- `test_the_request_lives_seven_days_and_does_not_use_up_the_ten_slots`。
- `test_offer_cleanup_never_raises`（把 `create_pending`、`prepare_clean`、`find_run` 各換成會丟例外的假貨）；`test_a_full_clean_quota_is_skipped_silently`。
- `test_offer_makes_no_file_when_there_is_no_platform_database`。
接收端（`receiver`）：
- `test_complete_of_a_succeeded_run_makes_one_offer_and_the_response_and_token_end_are_unchanged`。
- `test_complete_of_a_failed_run_makes_none`；`test_complete_when_the_offer_fails_still_answers_ok_and_records_the_run`；`test_a_token_not_made_for_one_run_makes_no_offer`；`test_a_second_complete_of_an_aborted_run_makes_no_second_offer`。
端到端（假站台／假主機，用 c、d 的真代理程式碼）：
- `test_slurm_end_to_end_complete_offer_page_press_agent_deletes_then_the_record_says_cleaned_and_nothing_more_is_offered`：只有 `work` 消失、`results/`、`rawdata/`、`analysis/` 位元級不變；`work_cleaned_at` 有值；再收到 `complete` 不再提。
- `test_slurm_end_to_end_resumed_attempt_cleans_the_origin_folder`。
- `test_gcb_end_to_end_with_a_fake_bucket_deletes_only_the_run_prefix_and_keeps_work2_and_work_keep`。
- `test_nothing_is_deleted_until_the_person_presses`（到按之前，`destructive()` 與假 bucket 都不變）。
- `test_an_agent_refusal_or_error_leaves_work_cleaned_at_empty_and_makes_no_new_offer`。
範圍與憲法：
- `test_the_only_place_that_creates_a_clean_work_request_is_offer_cleanup`（掃 `abf_platform/`、`abf_launch/`：`create_pending(` 帶 `"clean_work"` 的呼叫只在 `actions/__init__.py` 一處）。
- `test_no_new_mcp_tool_no_new_route_no_new_cli_command`（工具仍 12；路由清單不變；`abf-platform --help` 的子指令清單不變）。
- `test_platform_and_launch_sources_have_no_program_start_no_rm_and_not_the_forbidden_word`（掃 `abf_platform/` 與 `abf_launch/`，不靠拆字）。
- `test_docs_say_what_is_deleted_what_is_not_and_keep_the_pinned_sentences`（PLATFORM.md 新小節的關鍵語；上列被其他測試釘住的字串仍在）。

## 完成標準（done when）
- 自動：新測試綠；全套綠（含 `tests/platform_test.sh`、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`）；MCP 工具數仍 12；`git diff --name-only` 只有「範圍：檔案」所列；Slurm 的內容包、畫面、`head.sh` 與 golden 位元級不變（`git diff --stat` 貼進 ledger，依 dev-plans 通例由 verifier 核對並重跑）。
- 手動（維護者，兩項都在**自己的測試 run** 上做，**由產品本身（確認頁）去刪，不要用任何 AI session 直接對叢集或 bucket 下刪除指令**）：
  1. nano4：用一個很小的 run（成功）→ 看板右欄出現「可以清掉中間檔」通知 → 點進 `/c/<rid>` → 畫面有作法 5 的 ①②③ 三句 → 先**不按**，隔一會兒用 `list_site_files` 看 `…/runs/<run>/work` 還在 → 再按「確認刪除」→ 只有 `work` 消失，`results/` 完整。
  2. nano4：核對這次 run 的 Nextflow 工作目錄真的是 `<run folder>/work`（看 Nextflow 日誌開頭的 `work-dir`，或 `.nextflow.log`）。**不是的話停手回報**：表示站台設定或 `nextflowConfig` 改了 `workDir`，公式要改。
  3. Google Batch（他自己的帳號）：同樣的 run，按「確認刪除」後 bucket 裡 `…/runs/<run>/work/` 消失；另外先手動放兩個同層物件 `…/runs/<run>/work2/x`、`…/runs/<run>/work-keep` 確認**沒被刪**（驗證前綴不會撞名；`gcloud storage rm --recursive` 對尾端斜線的行為在 d 片只憑文件，這是第一次實測）；並記下 bucket 有沒有軟刪除／版本控制，以及刪掉的物件之後是否仍能列出，結果回填 d 片 ledger 與本片畫面第 ④ 句。
  4. nano4 續跑：讓一個 run 失敗、續跑（`-a2`）成功 → 通知出現在 `-a2` 那個 run → 按「確認刪除」→ 原資料夾的 `work` 消失。
  5. 逾時不重提：在自己的測試庫把一張申請的 `expires_at` 改到過去，確認頁顯示「已逾時（7 天）」、看板沒有通知、之後也沒有新的一張出現。
- 文件：作法 7 的各份文件更新；`docs/TESTING.md` 的「cloud-cleanup」小節寫明手動驗收 1–5。
- 通知畫面截圖（確認頁含 `clean_screen` 的文字、看板卡片；zh、en 各一）列進每日清單，維護者回好／不好。

## 環境事實
（行號為 `origin/v3` @ `279363b`；以函式名為準，動手前 `git fetch -q origin` 再核對。）
- 收件端：`receiver.py` `create_app` :40（有 `index_path`、`tokens_path`、`clock`、`platform_path`）；`complete` :230（成功判斷 `succeeded = wf.get("success") is True` :252；寫 `final_status` :256-259；`store.end_token` :276；回應 :277）；目前只 import `agents, common, store`（:15）。`final_status` 在 run 索引，不在 `platform.db`；`status.find_run` 讀它。
- 鏡像對象：`build.py` `prepare_cancel` :275、`cancel_screen` :640、`_same_environment` :384、`as_text` :720、`target_problem` :125、`_predecessor` :327（成功的 run 不能續跑／重跑 :353）；`launch.py` `snapshot_ce` :139；`terminal.py` `PREFIX` :13、`esc` :17、`block` :39、`pair` :49；`actions/__init__.py` 的 forget 區 :734-812（`forget_check` 的讀法可借）、`_ask` :453（本片不用，因為不是 AI 發起）。
- hand-off 紀錄：`jobs.latest_launch` :296、`owned_run_names` :280、`launch_content` :385、`launch_job` :451、`run_forgotten` :368。
- 擁有者：確認頁要登入的使用者才按得下去（`confirm.approve` 對 `caller_user_id is None` 只允許 `ELICITED`，`confirm.py:117`）。
- 觀察：`final_status` 的 `succeeded` 只代表 Nextflow 工作流程自報成功；主控工作可能還沒收尾。所以代理在刪除當下自己再確認主控程序／工作已不在（c 片的 `squeue -u … -o %Z`、d 片的 `ps`），本片不依賴它。
- 憲法掃描：`test_scope.py` TC-071（:99）與 TC-061（:186）掃 `abf_platform/`（`_sources()` :19-20）；`abf_launch/` 不在其中，本片的測試自己補掃。平台原始碼本來就有 `gcloud storage cp` 這串字（`cloud_store.py:95`），所以不禁 `gcloud`，只禁 `storage rm`、`rm -`、`rmtree` 與啟動程式。新 `.py` 檔前 40 行要有 `# Nothing existing: …`（TC-070）：`test_cleanup_offer.py`。
- 平台現實：試用跑在常開桌機＋Tailscale Funnel；確認頁要用登入的使用者按，所以沒有擁有者的 run 無法被確認。

## 不做
- 不做總表 C-7 的後半：結果 30 天到期前 7 天的 Decision-needed 通知、費用頁顯示儲存月費（它們要 `cloud_cost.py`、費用頁，屬 `cloud-cost` 與網頁費用頁任務）。
- 不刪、不移動、不改 `results/`、`rawdata/`、`analysis/`、run 資料夾本身、`.nextflow*`、`head.sh` 等任何 `work` 以外的東西；不做「刪整個 run」「刪結果」的選項，也不做旗標。
- 不自動刪：沒有排程、沒有「N 天後自動」、沒有 POLICY 通道；只有本人在確認頁按確認刪除。
- 不新增 MCP 工具、不新增網頁路由、不新增終端機指令（`abf-platform clean-work` 之類另開 `cloud-cleanup-cli` 小任務）；不碰 `mcp_server.py`、`guidance.py`、`chat_tools.py`。
- 不做批次清（一次清多個 run）、部分清（只清某幾個 task 目錄）、`nextflow clean`。
- 不補提過去已成功的 run；不做逾時後的重新提出（見給維護者的問題）。
- 不做失敗／中止／失聯 run 的清理（失敗的 run 要靠 work 續跑）；不寫 `gcloud batch jobs delete` 或任何取消 Batch 工作的第二條寫入路徑。
- 不動 AWS／Azure／K8s 類型；不改 Slurm 與 Google Batch 的送出、取消、續跑行為。
- 不在平台裡新增 worker、執行緒、常駐迴圈。

## 裁決（2026-10-24，developer-agent；已併入上文，與其他段落不衝突）
1. **觸發點是 `receiver` 的 `complete`（run 成功當下），不靠網頁 GET 的副作用。** 理由：GET 不應有寫入副作用，且「有人看的時候補建」不是「成功當下建」。代價：動 `receiver.py`（cloud-cost 已合併，不再衝突），收件路徑上多一次寫入——用 `try/except` 包住，失敗不影響 run 的紀錄。
2. **沒有擁有者的 run 不支援，畫面與文件寫明。** 理由：確認頁要登入的使用者才按得下去；要補就得加終端機路徑，連帶動 `TERMINAL` 通道的掃描，預設不做。
3. **work 路徑有兩條公式（Slurm：`run_folder/work`；Google Batch：`<workDir>/runs/<run>/work`）。** 舊計畫的單一公式在續跑時會指向不存在的位置。
4. **逾時後不自動重提。** 舊計畫寫「下次 `offer_cleanups` 再提」，但觸發點既已改成成功當下，沒有第二次機會；是否補「重新提出」的入口列為給維護者的問題。
5. **Slurm 的 work 目錄位置是假設**（國網站台設定檔有沒有改 `workDir` 沒查到），列為手動驗收項 2；executor 以內容包記下的 `workDir` 為準、不自己推，不通過就停手回報。
6. **不用 `nextflow clean`，用刪掉字面目錄的做法**（c、d 片）；`gcloud storage rm --recursive` 的語意由 executor 對照 `--help` 與官方文件並寫進 ledger。
7. **確認畫面與通知的新文字由 verifier 依本計畫出題，合併前附截圖列進每日清單，維護者回好／不好。**
8. **「環境的 workDir 在送出之後改過」不提出**（本次新增）：避免用現在的環境算出一個不是這個 run 的路徑。
9. **畫面第 ③ 句與舊計畫不同**：成功的 run 本來就不能續跑／重跑，改寫成如實的說法（見作法 5）。
10. **切片理由**：舊計畫約 30 檔、需求超過 60 條測試；依 `dev-architecture-review-2026-10-24.md` §3 與 `dev-plans/README.md` 通例切成六片。本片 7 檔（含 ledger）。

## 裁決（2026-10-27，developer-agent，executor 第一輪 BLOCKED 後）
11. **准改兩條過時的既有測試，各只改一處，舊到新與理由寫進 ledger：**
    - `platform/tests/test_cleanup_confirm.py`（b 片 TC-065/066，約第 589 行）「整個 abf_platform 原始碼沒有 `create_pending(...clean_work`」：那是 b 片「還沒有東西會建申請」的守衛，f 片本來就要建。改成**只排除 `actions/__init__.py` 裡 `offer_cleanup` 這一個函式的本體**（用 ast 取出該函式範圍後再掃，或等效寫法），其他檔與其他函式仍不得出現；`request_clean` 那半句不變。
    - `platform/tests/test_web_parity.py`（TC-H16a/b）：把 `"offer_cleanup"` 加進 `INTERNAL` 表（e 片加 clean_requests 時同樣是改表）。
12. **TC-108 的「兩邊清單都不出現」指使用者看得到的清單**（MCP 工具、網頁路由、CLI 子指令、WEB_ONLY）。`INTERNAL` 是記錄「系統內部呼叫、不對使用者開放」的帳本，放進去正符合 TC-108 的本意，不算違反。
13. **TC-113 的檔案清單加上這兩個測試檔**（共 9 個）；`docs/PLATFORM.md` 「What it does not do」段的兩處更正也准，因為不改會跟新小節互相矛盾。
14. 合約其餘不變（沿用已確認的 test-case.md），不重出題。

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
