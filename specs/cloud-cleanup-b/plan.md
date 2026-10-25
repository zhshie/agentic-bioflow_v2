---
id: cloud-cleanup-b
title: 平台認得「清理 work」這種申請與工作（確認、佇列、期限、答覆記帳）——還沒有任何東西會建立它
tier: B
kinds: backend
lane: L-cleanup
after: cloud-cleanup-a
base: v3
---

# cloud-cleanup-b

> 本檔由 developer-agent 起草（2026-10-24），`cloud-cleanup.md` 切成六片之第二片（a 資料庫 → **b 平台記帳** → c 代理刪 Slurm 的 work → d 代理刪 Google Batch 的 work → e 確認頁 → f 成功後提出申請＋文件）。**本片只讓平台「會處理」`clean_work`**：確認管道、佇列、期限、答覆怎麼記；但**沒有任何程式會建立一張 `clean_work` 申請**（建立在 f 片），所以使用者看不到任何變化。B 級（後端、無網頁畫面）→ verifier 通過＋CI 綠即可合併。
> **名詞**：「work 目錄」＝Nextflow 放每個 task 中間檔的 `work/`，不是結果。「代理」＝跑在使用者那邊、替平台碰叢集或雲端的小程式（程式碼在 `platform/abf_station/`）。平台程式碼（`abf_platform/`、`abf_launch/`）裡一律寫「代理／agent」，不得出現 TC-061 禁用的那個英文字（`test_scope.py:189`）。
> **派工前提**：`cloud-cleanup-a` 已合併（資料庫放得下 `clean_work` 與 `work_cleaned_at`）。

## 目標
平台對 `clean_work` 這個新種類的處理跟 `cancel` 完全對稱、而且同樣嚴格：申請（pending）本身永遠不是確認、不會變成工作；只有申請者本人在確認頁按送出（`PAGE` 通道，經 `confirm.approve`）才排進佇列；佇列裡只有一種寫入型工作能憑這張確認憑證出去；代理答覆「已刪」才在 `launches.work_cleaned_at` 記時間。對使用者的意義：之後的刪除不會有任何繞過「本人答應」的路徑，而且這件事在能刪東西的程式（c、d）出現之前就已經被測試鎖住。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md` 與 `CLAUDE.md`；每句至少對應一條測試案例：
- 「**跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪**」（裁示 16，第 58 行）→ ①沒有本人按送出就沒有任何 `clean_work` 工作（pending 不產生工作）②沒有任何自動路徑（無排程、無「N 天後自動」、無 POLICY 通道）。
- 「**C-7 `cloud-cleanup`**（B／backend）：succeeded 後建「刪除 work 目錄」的待確認請求（走 `_ask`，新 kind `clean_work`；對 nano4 也適用）」（第 171 行）→ 種類名恰為 `clean_work`；Slurm（nano4）與 Google Batch 兩種環境都能排進這個工作。
- 「直接 `scancel`，以及刪改叢集端 `rawdata`／`results`／`analysis`，一律擋住」（`CLAUDE.md` §3.4）→ 平台層面：內容包裡的資料夾必須與 hand-off 紀錄一致，否則不排工作（代理端的路徑硬規則在 c、d 片）。
- 「網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」（裁示 14，第 54 行）→ 本片無網頁畫面。
- 憲法原則 2＋任務交辦：「平台不啟動程式」（`test_scope.py` TC-071、TC-061）→ 平台程式碼不含 `subprocess`、`rm -`、`storage rm`、`rmtree`，也不含 TC-061 禁用字。
- 「每個寫入要本人答應」（憲法 6／ADR 0006，引自 `017d-launch-composed.md` 第 26 行）→ 沒有 `clean_work` 的確認就沒有任何檔案被動。

## 範圍：檔案（只准改這些，共 7 個含 ledger）
- `platform/abf_platform/confirm.py`：
  - `JOB_KIND`（:27）加 `"clean_work": "clean_work"`。
  - 新常數 `CLEAN_PENDING_SECONDS = 7 * 86400`、`MAX_OPEN_CLEAN = 50`。
  - `create_pending`（:70）：有效期依 `kind` 決定（`clean_work` 用 `CLEAN_PENDING_SECONDS`，其餘照舊 `PENDING_SECONDS`；**不加參數**，免得呼叫者忘了傳）；`MAX_OPEN_PENDING`（:24）的計數（:85-86）改成只算 `kind <> 'clean_work'` 的；`clean_work` 另受 `MAX_OPEN_CLEAN` 上限（該人未逾時的 `clean_work` 申請數）。
  - `facts()`（:281）對 `kind == 'clean_work'` 回 `{"what": "clean_work", "run_name": …, "work": …}`（`work` 取內容包的 `work` 欄；仿 :296 的 cancel 分支）。
  - `FORGOTTEN_JOB_KINDS`（:311）加 `"clean_work"`。
  - 新增唯讀函式 `open_clean_requests(state_path, caller_user_id, clock=time.time)`：回 `{run_name: 申請編號}`，只含「該人自己的、`state='pending'`、未逾時、內容還在（`bundle_json` 非空、`forgotten_at` 空）」的 `clean_work` 申請。
- `platform/abf_platform/jobs.py`：
  - `DEADLINE_SECONDS`（:26）加 `"clean_work": 600`；`_DEADLINE_ENV`（:28）加 `"clean_work": "ABF_PLATFORM_DEADLINE_CLEAN"`（`KINDS` :39 自動變七種，`clean_work` 排最後）。
  - `CONFIRMED`（:41）加 `"clean_work": "clean_work"`。
  - `_target`（:71）Google Batch 分支的放行清單（:86）加 `"clean_work"`；`clean_work` **不要求環境狀態為 available**（:100 只對 `list_site_files`、`launch_nextflow` 要求），所以環境之後壞了（`invalid`）仍能清。
  - `enqueue_confirmed`（:553）的非 launch 路徑：`clean_work` 另核對（見作法 2）。**不新增 `enqueue_clean`**：`confirm.approve` 直接呼叫 `enqueue_confirmed`，沒有終端機路徑。
  - `clean_result`（:665）：`clean_work` 專屬分支（見作法 4）。
  - `_apply_handover`（:720）：`clean_work` 的記帳（見作法 5）。
- `platform/tests/test_cleanup_confirm.py`（新；檔首 `# Nothing existing: …`，TC-070）。
- 必須更新的既有斷言（有意；其他一律不准動，PR 說明逐條寫「以前／以後／理由」）：
  - `platform/tests/test_resume_scope.py:68-70`（`test_tc154_tc161_there_are_still_three_channels_two_kinds_of_confirmation_and_two_kinds_of_job`）：以前＝`confirm.JOB_KIND == {launch, cancel}`、`jobs.CONFIRMED == {…兩筆}`、`jobs.KINDS == (六種)`；以後＝各加 `clean_work`（`KINDS` 第七個）；函式名的 "two kinds" 改 "three kinds"。三條 channel（TERMINAL／ELICITED／PAGE）的斷言不動。:73 的 schema 字串已在 a 片改過。
  - `platform/tests/test_keep_submissions.py:773`（`test_tc083_no_new_confirmation_kind_and_approve_knows_nothing_of_forget`）：`set(confirm.JOB_KIND) == {"launch","cancel"}` 加 `clean_work`；`"forget" not in inspect.getsource(confirm.approve)` **不動**。
  - `platform/tests/test_launch_platform.py:606`：`set(jobs.KINDS) == {…六種}` 加 `clean_work`。（:122-134 的「各種類插入／寫入鎖」迴圈不是必改項；要不要順手加 `clean_work` 由 executor 判斷，加了寫進 PR 說明。）
- `specs/cloud-cleanup-b/ledger.md`。

**禁碰**：`store.py`（a 片已改完）、`cli.py`（platform 與 abf_launch 兩個都不碰）、`receiver.py`、`records.py`、`cloud_cost.py`、`compute_envs.py`、`mcp_server.py`、`guidance.py`、`actions/`（含 `chat_tools.py`）、`build.py`、`web*.py`、`abf_station/*`、`tests/no_second_run_state_test.sh`、`test_actions_layer.py`、`test_chat_tools.py`、`test_pat.py`／`test_oauth_mcp.py` 的 `len(tools) == 12`。

## 作法
1. **申請的有效期與名額**（`create_pending`）：`clean_work` 申請 7 天有效（`expires_at = now + 604800`），其餘不變。理由：這是「提醒」不是「現在就要答」，10 分鐘太短；`KEEP_UNSENT_SECONDS`（:26）的清空規則照舊（逾時再 7 天後清掉內容）。同一個人對同樣內容再申請，剩餘時間超過 `REUSE_MIN_SECONDS`（:25）就回既有那張（`create_pending` 本來依 sha 重用，不改）。名額：`clean_work` 不佔那 10 張，反過來也不被它們擋住；自己有 `MAX_OPEN_CLEAN`（50）的上限，超過回 `JobRefused`，用白話說「已有 N 個等待中的清理提醒，請先處理或等它們逾時」。
2. **排進佇列時的核對**（`enqueue_confirmed` 非 launch 路徑，:584-590）：除了既有的「有 hand-off 紀錄且有 Slurm／主控程序編號、擁有者相符」之外，`clean_work` 再核對四件事，任何一項不符 → `JobRefused`（白話）且不排工作：①`bundle["run_folder"]` 與 hand-off 紀錄的 `run_folder` 逐字相同；②`bundle["slurm_job_id"]` 與紀錄相同；③紀錄的 `work_cleaned_at` 為空（否則「已經清過了」）；④內容包鍵集合恰為 `{version, run_name, slurm_job_id, run_folder, agent, ce, work}`。讀 `work_cleaned_at` 用 `jobs._col(row, "work_cleaned_at")`（:326，容忍沒有這欄的列）。`agent` 與環境的代理必須相符是既有檢查（:566）。
3. **環境（`_target`）**：Slurm 環境照既有規則（狀態 `unsupported`／`disabled` 擋、代理離線擋、非擁有者的環境等同「找不到」）；Google Batch 環境只放行 `preflight`、`launch_nextflow`、`cancel_run`、`clean_work` 四種。
4. **答覆的清洗**（`clean_result`）：`clean_work` 取 `ok`（布林）、`message`（≤2000，既有）、`run_name`（≤64）、`cleaned`——**只有真正的 `True` 才是 `True`**（`1`、`"true"`、`"yes"` 都不算；沒有或不是 `True` 就是 `False`）；其他任何鍵一律丟掉。
5. **記帳**（`_apply_handover`，仿 :736 的 cancel 分支）：`job["kind"] == "clean_work"` 且 `state == "done"` 且 `cleaned["ok"]` 且 `cleaned["cleaned"] is True` → `UPDATE launches SET work_cleaned_at = ? WHERE run_name = ? AND slurm_job_id = ?`（`run_name`、`slurm_job_id` 取自工作自己的內容包，不取自答覆）。`refused`、`error`、`ok` 為假、`cleaned` 不是 `True` → **什麼都不寫**，也不自動重試。遲到的答覆（工作已 `expired`，:778-782 的路徑）照樣記（比照 cancel）。內容被擁有者刪除過的工作（`forgotten`，args 只剩 `run_name`）沒有 `slurm_job_id`，`WHERE slurm_job_id = NULL` 比對不到任何列：不寫、不報錯。
6. **forget 對稱**：`FORGOTTEN_JOB_KINDS` 加了 `clean_work` 後，`forget_content` 會清掉該 run 的 `clean_work` 申請（含 pending，變 void）與其工作的內容，並且在有 `clean_work` 工作 queued／claimed 時拒絕（沿用既有規則，不改邏輯）。
7. **`confirm.facts` 與確認頁的相依**：本片讓 `facts()` 回 `{"what": "clean_work", …}`，但 `web.py` 的 `plain_block`（:288-300）用 `_PLAIN[lang][facts["what"]]` 查標籤，e 片才加 `clean_work` 的標籤。**在 e 片合併之前，系統裡不會有任何 `clean_work` 申請**（建立它的 f 片 `after` e），所以不會出現 KeyError；測試用手工建立的申請只在 `abf_platform` 層做，不走網頁。
8. **migration**：不需要（a 片已完成）。本片不改資料結構、不改資料內容的格式。

## 失敗先行測試（現在都會紅；新檔 `test_cleanup_confirm.py`，預估 38 條新增 TC；用既有的 fake platform 夾具與 `tmp_path`，不需要 `FakeSite`）
確認管道（confirm）：
- `test_job_kind_map_has_clean_work_and_the_other_two_unchanged`、`test_a_clean_work_request_lives_seven_days_and_the_others_still_ten_minutes`（量 `expires_at - created_at`）。
- `test_same_person_same_content_gets_the_same_request_and_another_person_does_not`。
- `test_clean_work_requests_do_not_use_up_the_ten_open_slots_and_ten_open_ones_do_not_block_clean_work`；`test_more_than_fifty_open_clean_requests_are_refused_in_plain_words`。
- `test_a_pending_clean_request_is_never_a_confirmation_and_no_job_exists_until_the_person_approves`（approve 前 `jobs` 表列數不變）。
- `test_approve_through_page_queues_exactly_one_clean_work_job_with_this_confirmation`；`test_approving_twice_gives_already_and_one_job`。
- `test_another_users_request_cannot_be_approved_and_cannot_be_read`（讀 `describe`／`facts` 與寫 `approve` 各一條）。
- `test_an_expired_clean_request_cannot_be_approved_and_queues_nothing`（時鐘撥過 7 天）；`test_a_void_or_forgotten_request_cannot_be_approved`。
- `test_a_clean_work_confirmation_cannot_queue_a_launch_or_a_cancel_and_the_other_way_round`（四種組合，`_check_confirmation` :257 的種類不符）。
- `test_facts_of_a_clean_work_request_are_kind_run_and_work_only`；`test_facts_of_a_forgotten_clean_request_is_none`。
- `test_open_clean_requests_returns_only_my_own_unexpired_pending_ones_with_content`（他人的、逾時的、void、confirmed、被 forget 的各一條，都不出現）。
- `test_forget_clears_clean_work_requests_and_jobs_of_the_run_and_waits_for_a_queued_one`。
佇列（jobs）：
- `test_deadline_of_clean_work_is_600_and_the_env_variable_overrides_it_and_a_bad_value_falls_back`（有效值／非數字／0／負數）；`test_kinds_are_seven_and_clean_work_is_last_and_confirmed_map_has_it`。
- `test_a_clean_work_job_is_refused_without_a_confirmation_at_the_queue_and_at_the_database`（兩道鎖各一條）。
- `test_slurm_environment_takes_clean_work_while_available_or_invalid_but_not_disabled_or_unsupported`；`test_offline_agent_refuses_clean_work_in_plain_words`。
- `test_gcb_environment_lets_clean_work_through_whatever_its_status_but_unsupported_and_disabled`；`test_other_gcb_job_kinds_are_still_refused`（`list_site_files`、`fetch_run_records`、`read_task_log` 三條）。
- `test_enqueue_refuses_a_run_with_no_hand_off_row_or_no_job_number_in_plain_words`；`test_another_users_run_is_not_there_for_the_caller`。
- `test_enqueue_refuses_a_folder_or_a_job_number_that_differs_from_the_hand_off_record`（兩條）；`test_enqueue_refuses_when_work_cleaned_at_is_already_set`；`test_enqueue_refuses_a_bundle_with_other_keys`；`test_enqueue_refuses_an_agent_that_is_not_the_environments_agent`。
- `test_clean_result_keeps_only_the_expected_keys_and_cleaned_only_when_it_is_the_real_true`（`True`／`1`／`"true"`／缺少）；`test_clean_result_bounds_the_texts`。
記帳：
- `test_done_ok_cleaned_true_writes_work_cleaned_at_on_that_row_only`（同名兩列、只有帶該 Slurm 編號的那列被寫；別的 run 不動）。
- `test_refused_error_not_ok_or_cleaned_false_answers_write_nothing`（四條）。
- `test_a_late_answer_after_the_deadline_is_still_recorded`；`test_a_late_answer_for_a_forgotten_job_writes_nothing_and_does_not_fail`。
- `test_take_result_end_to_end_for_clean_work_keeps_the_cleaned_answer`。
範圍與憲法：
- `test_no_new_mcp_tool_no_new_action_no_new_route`（工具仍 12 個；`actions` 的公開名稱集合與本片之前相同）。
- `test_platform_and_launch_packages_have_no_deletion_code_and_no_program_start`（掃 `abf_platform/`、`abf_launch/`：不含 `rm -`、`storage rm`、`rmtree`、`subprocess`，且不含 TC-061 禁用字；不靠拆字）。
- `test_launch_and_cancel_keep_their_ten_minute_requests_and_their_deadlines`（回歸）。

## 完成標準（done when）
- 自動：新測試綠；三處既有斷言更新後全套綠（含 `tests/platform_test.sh`、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`）；MCP 工具數仍 12；`git diff --name-only` 只有「範圍：檔案」所列（`git diff --stat` 貼進 ledger，由 verifier 依 ledger 核對並重跑）；launch 與 cancel 的既有測試一個都沒改。
- 手動：無（本片沒有使用者可見行為）。
- 文件：無（`docs/` 在 f 片一次更新）。

## 環境事實
（行號為 `origin/v3` @ `279363b`；以函式名為準，動手前 `git fetch -q origin` 再核對。）
- 鏡像對象是 cancel：`confirm.py` `JOB_KIND` :27、`create_pending` :70（有效期用 `PENDING_SECONDS` :23 寫死在 INSERT :91-93；名額計數 :85-89）、`approve` :117（`JOB_KIND[row["kind"]]` :149 → `jobs.enqueue_confirmed` :152）、`find_cancel` :244、`describe` :260、`facts` :281、`FORGOTTEN_JOB_KINDS` :311、`forget_content` :340。
- `jobs.py`：`DEADLINE_SECONDS` :26、`_DEADLINE_ENV` :28、`KINDS` :39、`CONFIRMED` :41、`_target` :71（Google Batch 放行清單 :86）、`_check_confirmation` :257、`owned_run_names` :280、`latest_launch` :296、`_col` :326、`enqueue_confirmed` :553（非 launch 路徑 :584-590）、`enqueue_cancel` :601、`clean_result` :665（launch／cancel 分支 :682）、`_apply_handover` :720、`take_result` :743（遲到答覆 :778-782）。
- 成功後的 run 沒有任何「狀態」存在平台：`final_status` 在 run 索引（`receiver.py:250-257` 的 `complete` 寫入），不在 `platform.db`。本片不讀它。
- Google Batch 的 hand-off 紀錄：`slurm_job_id` 欄放的是主控程序的 pid（`abf_station/gcb_launch.py:215` `"slurm_job_id": pid`），所以 `enqueue_confirmed` 的「要有編號」檢查對兩種環境一樣有效。
- 憲法掃描：`test_scope.py` TC-071（:99；禁 `subprocess`、`Popen`、`os.system`、`nextflow run`、`sbatch`、`nohup`、`setsid`、`threading` 等）與 TC-061（:186；禁 `ssh`、`sbatch`、`scancel`、`tw `、`station`、`site agent`、`socket` 等）掃的是 `abf_platform/` 全部原始碼（`_sources()` :19-20）。`abf_launch/` 不在這兩個掃描裡，本片的測試自己補掃。**平台原始碼裡有 `gcloud storage cp` 這串字**（`cloud_store.py:95`，給使用者看的指令文字，`test_cloud_upload.py:761` 釘住它），所以本片的掃描**不禁 `gcloud` 這個字**，只禁 `storage rm`、`rm -`、`rmtree` 與啟動程式。
- 新 `.py` 檔前 40 行要有 `# Nothing existing: <≥15 字理由>`（TC-070）：`test_cleanup_confirm.py`。

## 不做
- 不建立任何 `clean_work` 申請（建立者是 f 片的成功後提出）；不寫代理端的刪除（c、d 片）；不改確認頁與看板（e 片）。
- 不新增 MCP 工具、不新增 `actions` 函式、不新增網頁路由、不新增終端機指令；不碰 `mcp_server.py`、`guidance.py`、`chat_tools.py`。
- 不新增 `enqueue_clean`、不新增 worker／執行緒／常駐迴圈、不新增排程。
- 不改 `launch`、`cancel` 的任何行為、期限或文字。
- 不做批次清、部分清、失敗／中止／失聯 run 的清理。

## 裁決（2026-10-24，developer-agent；已併入上文，與其他段落不衝突）
1. **新種類 `clean_work`，不借用 `cancel`。** 理由同 a 片：確認憑證的種類必須對得上工作種類，這道鎖不能拆。
2. **不加 MCP 工具、不加終端機指令；只有網頁確認頁（`PAGE` 通道）一條路。** 理由：任務是「平台提出、本人按」，不是「AI 提出」；少一個入口就少一個被誤用的面。沒有擁有者的 run（純終端機單人模式）因此不支援，f 片的畫面與文件要寫明。
3. **`work_cleaned_at` 只在代理明說 `cleaned: true` 時才寫；「本來就沒有 work」也算 `cleaned: true`。** 理由：避免永遠重提一個其實已經不存在的目錄。
4. **逾時／錯誤／拒絕都不記為已清、不自動重試。** 理由：與 `cancel`、`launch` 一致（一次、不重試）；使用者看得到失敗並可再按。
5. **申請有效期 7 天、不佔 10 張名額，上限自成一格（50）。** 理由：它是提醒不是即時操作；系統自己建的提醒不應擠掉使用者主動的申請，但也不能無界。（舊計畫只寫「不佔名額」，沒有上限；本次補上。）
6. **舊計畫寫「`enqueue_clean`（仿 `enqueue_cancel`）」，本片取消。** 理由：`approve` 直接用 `enqueue_confirmed`，沒有終端機路徑，多一個沒人呼叫的函式只增加要維護的面。
7. **舊計畫的 `_apply_handover` 條件「`cleaned is True`」保留，並補上「內容被 forget 的工作不寫、不報錯」。**
8. **切片理由**：舊計畫整份約 30 檔、需求超過 60 條測試；依 `dev-architecture-review-2026-10-24.md` §3 與 `dev-plans/README.md` 通例切成六片。本片 7 檔（含 ledger）。

## 裁決二（2026-10-25 07:20，executor BLOCKED 後）
7. 授權更新 `platform/tests/test_cleanup_store.py` 的 `test_nothing_writes_clean_work_or_work_cleaned_at`（a 片 TC-030，:491-496）：掃描排除 `confirm.py`、`jobs.py`（本片正當地寫入 clean_work）；`work_cleaned_at` 仍只准 store.py。這是 a 片「後續片才接線」的預留檢查，隨片放寬是預期的。
8. `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 在完整 clone 上本來就紅（釘 6061925），由 onboarding-test-pinned-base 修；本片把它當已知環境紅，ledger 記一行即可，不擋 GREEN。
9. `forget_content` 佔位符改成依長度產生：接受（「不改邏輯」的說法作廢，邏輯等價）。
10. `clean_work` 答覆保留共用的 `error`／`note`（≤300）：接受。MAX_OPEN_CLEAN 邊界照 MAX_OPEN_PENDING（第 51 張拒）。MCP 工具數現為 13，TC-067 改寫：接受。

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
