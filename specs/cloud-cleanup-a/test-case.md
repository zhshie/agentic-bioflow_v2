# 測試案例：資料庫先學會「clean_work」這個種類與「work_cleaned_at」欄位（cloud-cleanup-a）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) from the plan only: there is no spec.md for this task.
The maintainer's words are quoted in plan.md under 「維護者原話」; every row below comes from a line of plan.md
(目標, 範圍：檔案, 作法 1-5, 失敗先行測試, 完成標準, 環境事實, 不做, 裁決, 裁決二, 專長守則（backend）).
Where 作法 2.1 ("skip when the jobs sql contains clean_work") and 裁決二 item 7 ("skip only when it contains both read_task_log and clean_work")
differ, 裁決二 was written later in answer to the verifier and governs; the rows follow it.
Nothing was added that the plan does not state.
-->

**規格**：`specs/cloud-cleanup-a/plan.md`（本件沒有 spec.md，計畫即依據）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、被改動、不合規則、同時開啟時，系統怎麼反應（拒絕、停下，且舊資料完全如舊）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：

- 「確認種類」＝`confirmations.kind`（一張「待人說 yes」的請求是哪一類）；「工作種類」＝`jobs.kind`（代理要做的工作是哪一類）。「`clean_work`」＝刪除 Nextflow 的 `work/` 中間檔這件事的種類名，兩處同名。
- 「寫入鎖」＝資料庫自己的規則：`launch_nextflow`、`cancel_run`、`clean_work` 這三種會改東西的工作，沒有確認憑證（`confirmation_id` 為空）就寫不進去，會丟 `IntegrityError`。
- 「重建」＝SQLite 不能原地改 CHECK 規則，只能建新表、複製每一列、刪舊表、改名。「舊庫」＝照舊結構做出來的 `platform.db`（測試自己造）。
- 「外鍵」＝`jobs.confirmation_id` 指向 `confirmations(id)`；`confirmations` 是父表。
- 「位元相同」＝用 `helpers.all_files_digest` 對資料庫檔算出的雜湊前後一樣。
- 「新測試檔」＝`platform/tests/test_cleanup_store.py`；每個測試在註解裡寫出它對應的 TC 編號。計畫列了 21 個具名測試；下列 TC 若不在那 21 個之內，可以併入同主題的測試（例如參數化），但每條都要有自己的斷言。
- 「手動（閱卷）」＝閱卷者讀 diff、`git diff --stat` 與 `specs/cloud-cleanup-a/ledger.md` 逐句對照預期結果（本片不改 `docs/`）。「自動＋閱卷」＝既有或新測試要綠，且閱卷者另外讀 diff 確認。
- 起始資料（測試自訂）：確認請求 `c1`（launch）、`c2`（cancel）、`c3`（clean_work，只在新結構裡能插）。

## User Story 1 — 全新資料庫認得 clean_work，且寫入鎖不鬆（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話「新 kind `clean_work`」「種類名恰為 `clean_work`（確認種類與工作種類同名）」；原話「新的確認種類 `clean_work` 存在，且跟 `launch`／`cancel` 是分開的」；`test_fresh_confirmations_take_clean_work_and_still_refuse_…` | 功能 | 全新資料庫（`connect_state` 開在空路徑） | 在 `confirmations` 各插一列 kind 為 `launch`、`cancel`、`clean_work` | 三列都插得進去；`confirmations.kind` 的 CHECK 宣告的集合恰為 `{launch, cancel, clean_work}`（三個互相分開的種類，沒有借用 `cancel`） | 自動：新測試檔 |
| TC-002 | 同上（`…still_refuse_resume_relaunch_retry_and_empty`） | 例外 | 全新資料庫 | 在 `confirmations` 插 kind 為 `resume`、`relaunch`、`retry`、空字串（逐一，各自一次） | 四次都丟 `sqlite3.IntegrityError`，`confirmations` 沒有多出任何列 | 自動：新測試檔 |
| TC-003 | 原話「種類名恰為 `clean_work`」；作法 1（工作種類七種，`clean_work` 放最後）；`test_fresh_jobs_take_clean_work_only_with_a_confirmation` | 功能 | 全新資料庫；已有 `c3`（kind `clean_work`） | 插一列 `jobs`，kind `clean_work`、`confirmation_id` 為 `c3` | 插得進去；`jobs.kind` 的 CHECK 宣告的清單依序恰為 `preflight, list_site_files, launch_nextflow, cancel_run, fetch_run_records, read_task_log, clean_work` | 自動：新測試檔 |
| TC-004 | 原話（`CLAUDE.md` §3.4）「直接 `scancel`，以及刪改叢集端 `rawdata`／`results`／`analysis`，一律擋住」→ 資料庫層「寫入型工作沒有確認憑證就 `IntegrityError`」，`clean_work` 也在其中；裁決 3 | 例外 | 全新資料庫 | 插一列 `jobs`，kind `clean_work`、`confirmation_id` 為 NULL | 丟 `sqlite3.IntegrityError`；`jobs` 列數沒有增加 | 自動：新測試檔 |
| TC-005 | 作法 1（寫入鎖涵蓋三個寫入型工作種類）；`…only_with_a_confirmation`（對 `launch_nextflow`、`cancel_run` 同樣仍擋） | 例外 | 全新資料庫 | 各插一列 `jobs`，kind `launch_nextflow`、kind `cancel_run`，`confirmation_id` 都是 NULL | 兩次都丟 `sqlite3.IntegrityError`；`jobs` 沒有新增列 | 自動：新測試檔 |
| TC-006 | 作法 1（寫入鎖只涵蓋三個寫入型種類）；目標（不改其他行為） | 功能 | 全新資料庫 | 各插一列 `jobs`，kind 為 `preflight`、`list_site_files`、`fetch_run_records`、`read_task_log`，`confirmation_id` 為 NULL | 四列都插得進去（唯讀工作仍不需要憑證） | 自動：新測試檔（可併入 TC-003 的測試） |
| TC-007 | `test_fresh_jobs_still_refuse_rm_delete_clean_and_other_words` | 例外 | 全新資料庫 | 插 `jobs`，kind 依序為 `rm`、`delete`、`clean`、`clean_work `（尾端一個空白）、`CLEAN_WORK`、空字串 | 六次都丟 `sqlite3.IntegrityError`（逐案各自斷言，不抽樣）；`jobs` 沒有新增列 | 自動：新測試檔 |
| TC-008 | 目標；作法 1（欄位 `launches.work_cleaned_at REAL`，可空，放在 `attempt_kind` 之後）；`test_launches_has_work_cleaned_at_as_its_last_column_and_it_is_null_by_default` | 功能 | 全新資料庫 | 讀 `PRAGMA table_info(launches)`；插一列 `launches` 但不給 `work_cleaned_at` | 欄位依序為 `id, run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, cancel_requested_at, job_id, user_id, parent_run, attempt, attempt_kind, work_cleaned_at`（新欄在最後，前 14 欄與以前完全一樣）；型別 REAL、可為空（notnull＝0、沒有預設值）；剛插的那列 `work_cleaned_at` 為 NULL | 自動：新測試檔 |

## User Story 2 — 舊資料庫升級：每一列原封不動，結構與新庫相同（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-009 | 目標（升級不丟任何一列）；作法 3；`test_old_confirmations_table_is_rebuilt_and_every_row_is_identical` | 功能 | 舊庫：`confirmations` 的 CHECK 只有 `launch`／`cancel`；含 pending、confirmed、void 各一列，且各欄都有值（`caller_user_id`、`forgotten_at`、`forgotten_by`、`bundle_json`、`screen_text`、`void_reason` 等） | 用 `connect_state` 開一次；之後 `SELECT *` | 每一列每一欄的值與升級前逐一相等（列數相同）；欄位順序與全新資料庫的 `confirmations` 相同；再插一列 kind `clean_work` 插得進去 | 自動：新測試檔 |
| TC-010 | 作法 2.3（重建必須排在 `_add_confirmation_state` 之後）；`test_a_database_before_009c_gets_its_old_rows_marked_confirmed_terminal_not_pending` | 功能 | 更舊的舊庫（009c 之前）：`confirmations` 只有 `id, sha256, kind, created_at, used_at, caller_user_id` 六欄，有兩列 | 用 `connect_state` 開一次 | 兩列都是 `state='confirmed'`、`channel='TERMINAL'`、`confirmed_at` 等於各自的 `created_at`（不是預設的 `pending`）；該表接受 kind `clean_work` | 自動：新測試檔 |
| TC-011 | 作法 3（外鍵父表重建）；`test_jobs_referencing_the_rebuilt_confirmations_keep_their_ids_and_links` | 功能 | 舊庫：`jobs` 有三列，其中兩列的 `confirmation_id` 指向 `c1`、`c2`（舊結構的 launch／cancel 請求） | 用 `connect_state` 開一次 | 三列 `jobs` 的 `id` 與 `confirmation_id` 都沒變；用 `confirmation_id` 去 JOIN `confirmations` 仍各找到原本那一列（內容與升級前相同） | 自動：新測試檔 |
| TC-012 | 作法 3 最後一點；`test_foreign_key_check_is_empty_and_foreign_keys_are_on_afterwards` | 功能 | 任何舊庫（內容同 TC-011） | 用 `connect_state` 開一次，在回傳的連線上查 `PRAGMA foreign_key_check`、`PRAGMA foreign_keys`、`PRAGMA foreign_key_list(jobs)` | `foreign_key_check` 沒有任何結果；`foreign_keys` 為 1（外鍵保持開著）；`jobs` 的外鍵目標表名是 `confirmations`（不是 `confirmations_new` 或別的名字） | 自動：新測試檔 |
| TC-013 | 作法 3 / `_migrate_jobs_kinds` 的先例；`test_jobs_sequence_counter_survives` | 功能 | 舊庫：`jobs` 曾用過到某個編號再刪掉最大的一列，使 `sqlite_sequence` 中 `jobs` 的 seq 大於現存最大 id | 用 `connect_state` 開一次；再插一列新 `jobs` | 升級後 `sqlite_sequence` 中 `jobs` 的 seq 與升級前相同；新插的那列 id＝seq＋1（編號不倒退、不重複） | 自動：新測試檔 |
| TC-014 | 作法 2.1；`test_a_jobs_table_without_read_task_log_is_upgraded_straight_to_the_newest_kinds_in_one_open` | 功能 | 舊庫：`jobs` 的 CHECK 沒有 `read_task_log`（也沒有 `clean_work`），有幾列各種已有的工作 | 用 `connect_state` 只開一次 | 開一次之後，`jobs` 就接受 kind `read_task_log` 與 `clean_work`（`clean_work` 需憑證）；原有各列逐欄相等、id 不變；欄位順序與全新資料庫的 `jobs` 相同 | 自動：新測試檔 |
| TC-015 | 裁決二 第 7 點（「其餘一律重建」）；目標（今天維護者的舊庫就是這個形狀） | 功能 | 舊庫：`jobs` 的 CHECK 有 `read_task_log` 但沒有 `clean_work`，有幾列 | 用 `connect_state` 開一次 | `jobs` 被重建：接受 `clean_work`（有憑證）、寫入鎖涵蓋 `clean_work`（沒憑證丟 `IntegrityError`）；原有各列逐欄相等、id 與 seq 不變 | 自動：新測試檔（可併入 TC-014 的測試，參數化兩種舊 CHECK） |
| TC-016 | 裁決二 第 7 點（同時含兩者才跳過） | 功能 | 全新結構的資料庫（`jobs` 的 sql 同時含 `read_task_log` 與 `clean_work`） | 記下 `sqlite_master` 中 `jobs` 的 rootpage；用 `connect_state` 再開一次 | `jobs` 的 rootpage 沒變（沒有被重建）；內容位元相同 | 自動：新測試檔 |
| TC-017 | 目標（舊庫升級後結構與新庫相同）；`test_a_launches_table_without_the_attempt_columns_and_without_work_cleaned_at_gets_all_four` | 功能 | 舊庫：`launches` 沒有 `parent_run`、`attempt`、`attempt_kind`，也沒有 `work_cleaned_at` | 用 `connect_state` 開一次 | 四個欄位都被加上，欄位順序與全新資料庫的 `launches` 相同（`work_cleaned_at` 在最後） | 自動：新測試檔 |
| TC-018 | `test_old_launches_rows_keep_every_old_value_and_get_null_work_cleaned_at` | 功能 | 舊庫：`launches` 有幾列，各舊欄都有值 | 用 `connect_state` 開一次 | 每一列的每個舊欄值不變；每一列的 `work_cleaned_at` 都是 NULL | 自動：新測試檔 |
| TC-019 | 目標（「新資料庫與舊資料庫升級後的結構完全相同」）；裁決二 第 9 點（相同＝欄位名稱／順序／型別／NOT NULL／預設值／主鍵＋各 CHECK 接受與拒絕的集合；不比 `sqlite_master.sql` 逐字）；`test_a_new_and_an_upgraded_database_have_the_same_structure_for_confirmations_jobs_and_launches` | 功能 | 一個全新資料庫；一個由舊庫升級而來的資料庫（舊庫：`confirmations` 兩種 kind、`jobs` 有 `read_task_log` 無 `clean_work`、`launches` 無 `work_cleaned_at`） | 對兩者比較 `confirmations`、`jobs`、`launches` 三張表 | 欄位名稱、順序、型別、NOT NULL、預設值、主鍵相同；`confirmations.kind`／`state`、`jobs.kind`／`state`、寫入鎖、`launches.attempt_kind` 各 CHECK 對一組同樣的合法與非法值，兩邊接受與拒絕的結果完全相同 | 自動：新測試檔 |
| TC-020 | 目標（任何舊庫升級後結構相同）；環境事實（`_migrate_jobs` 在連 `confirmations` 都沒有的 007 庫上自建只有兩種種類的 `confirmations`，:381-382） | 功能 | 最舊的 007 庫：沒有 `confirmations` 表，`jobs` 沒有 `agent` 欄等，有幾列 `jobs` | 用 `connect_state` 開一次，並比較 `confirmations`、`jobs`、`launches` 與全新資料庫（比法同 TC-019） | 開得成功；三張表結構與全新資料庫相同；`confirmations` 接受 `clean_work`；原有 `jobs` 各列內容保留 | 自動：新測試檔 |
| TC-021 | `test_pending_and_void_requests_made_before_the_upgrade_are_still_found_by_confirm_describe` | 功能 | 舊庫：有一列 pending、一列 void 的確認請求 | 升級後對這兩個請求編號各呼叫一次 `confirm.describe` | 兩次都回傳結果（不是「找不到」），其 kind、state、畫面文字與升級前直接讀那一列的值一致 | 自動：新測試檔 |

## User Story 3 — 重複開啟、中途失敗、同時開啟、唯讀開啟都安全（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 目標（重複開啟內容位元相同）；`test_opening_twice_changes_nothing`（新庫） | 功能 | 全新資料庫，已開過一次 | 記下 `helpers.all_files_digest`；再用 `connect_state` 開一次並關閉；再算一次 | 前後雜湊相同 | 自動：新測試檔 |
| TC-023 | 同上（升級後的庫） | 功能 | 舊庫，已用 `connect_state` 升級過一次 | 記下雜湊；再開兩次；再算雜湊 | 雜湊與第一次升級完成後相同（第二、三次開啟什麼都沒改） | 自動：新測試檔 |
| TC-024 | 作法 3 第一點（已含 `'clean_work'` 就直接返回，一個位元都不動）；`test_an_already_new_confirmations_table_is_not_touched` | 功能 | 已是新結構的資料庫 | 記下 `sqlite_master` 中 `confirmations` 的 rootpage 與檔案雜湊；再用 `connect_state` 開一次 | rootpage 沒變、檔案雜湊相同，沒有出現 `confirmations_new`（判斷在 `BEGIN` 之前就返回，沒有重建） | 自動：新測試檔 |
| TC-025 | 作法 3 第二、三點（失敗要 ROLLBACK，舊表與所有列完全如舊；`finally` 還原外鍵與 `isolation_level`）；`test_a_failure_in_the_copy_step_leaves_the_old_table_and_rows_as_they_were_and_foreign_keys_on` | 例外 | 舊庫（同 TC-009 的內容）；把 `_migration_step` 換成一遇到 `"copied"` 就丟錯 | 用 `connect_state` 開；另外在自己開的連線上直接呼叫 `_migrate_confirmation_kinds` 並丟錯 | `connect_state` 把錯誤丟出來；之後以普通方式讀：`confirmations` 仍是兩種 kind 的舊結構、每一列每一欄與失敗前相同，`jobs` 各列不變，沒有留下 `confirmations_new`；直接呼叫的那條連線 `PRAGMA foreign_keys` 為 1、`isolation_level` 為原值 | 自動：新測試檔 |
| TC-026 | `test_the_next_open_after_that_failure_succeeds` | 例外 | TC-025 失敗之後的同一個資料庫；故障注入拿掉 | 再用 `connect_state` 開一次 | 開得成功；結果與 TC-009、TC-011、TC-012 的預期相同（每列相等、連結不變、`foreign_key_check` 為空） | 自動：新測試檔 |
| TC-027 | 作法 3（交易內再判斷一次，「另一個行程可能剛做完」）；`test_a_second_connection_opening_at_the_same_time_finds_it_done_and_does_not_fail` | 例外 | 舊庫；兩條連線（例如兩個執行緒，或第一條在複製步驟停住時第二條開始） | 兩條連線同時對同一個舊庫呼叫 `connect_state` | 兩條都成功返回，沒有丟任何錯（例如表已存在、資料庫鎖住逾時）；最後 `confirmations` 列數與升級前相同、沒有重複列；結構同 TC-019 | 自動：新測試檔 |
| TC-028 | 作法 3（`PRAGMA foreign_key_check` 必須為空，否則 `ROLLBACK` 並丟錯） | 例外 | 舊庫（兩種 kind 的 `confirmations`）；其中一列 `jobs` 的 `confirmation_id` 指向不存在的請求（建檔時外鍵關著） | 用 `connect_state` 開 | 丟錯；`confirmations` 仍是兩種 kind 的舊結構，每一列與失敗前相同，沒有留下 `confirmations_new`；直接呼叫遷移函式的連線外鍵回到 ON | 自動：新測試檔（可併入 TC-025 的測試） |
| TC-029 | 作法/範圍（`open_readonly` :622 不升級）；`test_read_only_open_of_an_old_database_does_not_upgrade_it` | 例外 | 舊庫（未升級過） | 記下檔案雜湊；用 `open_readonly` 開、讀幾列、關閉；再算雜湊 | 檔案雜湊沒變；`confirmations` 的 CHECK 仍只有兩種 kind、`launches` 仍沒有 `work_cleaned_at`；讀取本身成功 | 自動：新測試檔 |

## User Story 4 — 本片只讓資料庫「放得下」：沒有任何功能上線（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 原話「跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪」→ 本片沒有任何自動寫入；作法 5；不做（不寫任何會產生 `clean_work` 列的程式） | 不在範圍 | 本片完成後的 `platform/abf_platform/` 全部原始碼；一個新資料庫，並走過既有的建立請求、送出流程 | 搜尋 `abf_platform/` 中 `store.py` 以外的檔案有沒有 `work_cleaned_at` 或 `clean_work`；`store.py` 裡出現處是否只在表定義與升級函式；查資料庫 | 其他檔案沒有這兩個字；`store.py` 只在 DDL 與遷移函式出現，沒有對它們的 INSERT／UPDATE／SELECT；資料庫裡 kind 為 `clean_work` 的 `confirmations`、`jobs` 列數為 0，`launches` 所有列的 `work_cleaned_at` 都是 NULL | 自動：新測試檔 |
| TC-031 | 範圍：檔案（9 個）與「禁碰」清單；原話「網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」→ 本片無網頁畫面 | 不在範圍 | 本片全部改動 | 閱卷者讀 `git diff --name-only <base>...HEAD` | 變動的路徑只在計畫「範圍：檔案」所列 9 個之內（`store.py`、新測試檔、六個既有測試檔、`ledger.md`）；`confirm.py`、`jobs.py`、`actions/`、`build.py`、`web*.py`、`receiver.py`、`abf_station/*` 沒有任何變動；`test_resume_scope.py` 與 `test_keep_submissions.py` 只動了計畫點名的那一行；`test_human_channel.py` 沒變 | 手動（閱卷） |
| TC-032 | 不做（不動 `launches` 其他欄位、不改 `jobs` 欄位順序、不加索引、不加新表） | 不在範圍 | 全新資料庫，與 base 的全新資料庫比較 | 比對 `sqlite_master` 的表名與索引名集合、`jobs` 欄位順序、`launches` 前 14 欄 | 表名與索引名集合與 base 完全相同（沒有新表、沒有新索引）；`jobs` 的 15 欄順序與 base 相同；`launches` 前 14 欄與 base 相同，只多最後一欄 | 自動＋閱卷：新測試檔（欄位順序）與 diff |
| TC-033 | 不做（不做資料搬移以外的清理：不刪舊列、不重算任何東西） | 不在範圍 | 舊庫：含 expired／refused 的 `jobs`、void 與已 forgotten 的 `confirmations`、被取消的 `launches` | 升級前後各數各表列數，並比對那幾列內容 | 每張表列數升級前後相同；沒有任何列被刪、被重算或被改值（包含 `forgotten_at`、`void_reason`） | 自動：新測試檔 |
| TC-034 | 完成標準「MCP 工具數仍 12」；不做（沒有任何功能上線） | 不在範圍 | 本片完成後 | 跑既有的 MCP 工具清單測試 | 工具數仍為 12，沒有新增的工具、路由或動作 | 自動：既有 MCP／動作層測試 |
| TC-035 | 不做（不改 `confirm.py`、`jobs.py`；`JOB_KIND`、`CONFIRMED`、`KINDS`、`DEADLINE_SECONDS` 留給 b 片） | 不在範圍 | 本片完成後 | 跑 `test_keep_submissions.py` 的 `set(confirm.JOB_KIND) == {"launch", "cancel"}`（:773）與 `test_resume_scope.py` 的 `confirm.JOB_KIND`、`jobs.CONFIRMED`、`jobs.KINDS` 三行（:68-70）——這幾行都沒被改 | 這幾行原封不動且測試為綠：動作層仍然不認識 `clean_work`（沒有任何入口可以建立這種請求） | 自動：既有測試（閱卷確認那幾行未被改） |

## User Story 5 — 既有測試只准改這六處，其他一律不動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-036 | 範圍：`test_http_site_samplesheet.py:543` 的 `SCHEMA_SHA256`；`test_tc057_no_table_or_column_changed` | 功能 | 本片完成後 | 跑該測試；閱卷者讀該檔的 diff | 測試為綠；`SCHEMA_SHA256` 由 `56f767…662f9d` 換成新值，且新值是該測試自己的算法對全新資料庫算出來的（不是手填）；算法本身與測試其他行沒有被改 | 自動＋閱卷 |
| TC-037 | 範圍：`test_cloud_cost.py:746-748` | 功能 | 本片完成後 | 跑 `test_nothing_stops_a_running_job_and_no_policy_channel_exists`；讀 diff | 測試為綠；jobs 種類清單在 `read_task_log` 後加 `clean_work`（放最後）；確認種類那一行字串改為含 `'clean_work'`（`kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel', 'clean_work'))`）；沒有別的斷言被動 | 自動＋閱卷 |
| TC-038 | 範圍：`test_station_platform.py:322-328` | 功能 | 本片完成後 | 跑該測試；讀 diff | 測試為綠；先插一張 kind `clean_work` 的 `c3`，插入元組多了 `("clean_work", "c3")`，`declared` 期望集合加 `clean_work`；前面對 `rm`、`launch`、`scancel`、`write_file`、空字串仍要被拒絕的迴圈沒被改動 | 自動＋閱卷 |
| TC-039 | 範圍：`test_keep_submissions.py:774` | 功能 | 本片完成後 | 跑 `test_tc083_no_new_confirmation_kind_and_approve_knows_nothing_of_forget`；讀 diff | 測試為綠；只有 :774 那一行加了 `'clean_work'`；:773 的 `set(confirm.JOB_KIND)` 沒動；若加了 :872 的 `drops` 項，PR 說明有寫 | 自動＋閱卷 |
| TC-040 | 範圍：`test_resume_scope.py:73` | 功能 | 本片完成後 | 跑該測試；讀 diff | 測試為綠；只有 :73 那一行改了（計數字串含 `'clean_work'`）；:68-70 沒動；`test_tc161…`（拒絕 `resume`、`relaunch`、`retry`、空字串）沒動 | 自動＋閱卷 |
| TC-041 | 範圍：`test_gcb_launch.py:1081` | 功能 | 本片完成後 | 跑 `test_no_migration_is_needed_and_the_columns_are_unchanged`（改名後）；讀 diff | 測試為綠；`cols["launches"]` 末尾多 `"work_cleaned_at"`；函式名不再說 "unchanged"；`jobs`、`compute_envs` 的欄位斷言沒被改 | 自動＋閱卷 |
| TC-042 | 範圍：「其他一律不准動」；環境事實（其他會讀這些表的測試不受影響）；弱化測試檢查 | 功能 | 本片完成後 | 讀 `git diff <base>...HEAD -- platform/tests`；跑 `test_human_channel.py`、`test_run_diag_tools.py`（含 `test_tc110_…`）、`test_launch_platform.py` | 除了上列六處與新測試檔，沒有其他既有測試檔被改；六處改動都是「加入 `clean_work`／`work_cleaned_at`」，沒有斷言被刪、放寬、跳過或把期望值改成配合輸出；那三個檔原封不動且為綠 | 自動＋閱卷 |
| TC-043 | 完成標準第一條（新測試綠；全套綠含三支 shell 測試） | 功能 | 本片完成後；在 WSL／Linux 的乾淨工作區 | 跑 `tests/run_all.sh`，含 `tests/platform_test.sh`、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh` | 全部綠；新測試檔全綠 | 自動 |

## User Story 6 — 交付紀錄：ledger 與 PR 說明交代清楚（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-044 | 作法 3（動手前讀 `sqlite.org/lang_altertable.html`，網址寫進 ledger）；環境事實（記下 `sqlite3.sqlite_version`，需 3.7.16 以上，否則停手回報） | 功能 | `specs/cloud-cleanup-a/ledger.md` | 閱卷者讀 ledger | ledger 有 `sqlite.org/lang_altertable.html` 網址，與實際的 `sqlite3.sqlite_version` 數字，且該數字不小於 3.7.16（若小於，ledger 寫的是停手回報而不是繼續） | 手動（閱卷） |
| TC-045 | 完成標準第一條（`git diff --stat` 貼進 ledger） | 功能 | ledger；`git diff --stat <base>...HEAD` | 閱卷者把 ledger 貼的 stat 與實際 stat 對照 | ledger 有 `git diff --stat`，且與實際一致、檔案只有 9 個（含 ledger） | 手動（閱卷） |
| TC-046 | 完成標準第二條；裁決二 第 10 點（拿不到維護者桌機 `platform.db` 時，寫明由 developer-agent 在桌機補跑，不算缺漏） | 功能 | ledger | 閱卷者讀 ledger 的「真實舊庫複本」一節 | 二擇一：(a) 貼出對真實複本開一次的結果——各表前後 `SELECT *` 相同、`PRAGMA integrity_check` 為 ok、`PRAGMA foreign_key_check` 為空；(b) 明寫「拿不到維護者桌機的 platform.db，由 developer-agent 在桌機補跑」。兩者都沒有就是缺漏 | 手動（閱卷） |
| TC-047 | 範圍（六處既有斷言更新，「PR 說明逐條寫以前／以後／理由」） | 功能 | PR 說明（若尚未開 PR，則 ledger 中預備的 PR 說明段） | 閱卷者讀 | 六處更新各有一條「以前／以後／理由」；若加了 `test_keep_submissions.py:872` 的 `drops` 項，另有說明 | 手動（閱卷） |
| TC-048 | 完成標準第三條（無手動驗收、無文件）；不做 | 不在範圍 | 本片完成後 | 閱卷者讀 `git diff <base>...HEAD -- docs`、`README*` | `docs/` 與使用者文件沒有任何變動；`docs/TESTING.md` 沒有新增步驟 | 手動（閱卷） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-049 | 原則 I（TC-070：每個新 `.py` 檔前 40 行要有 `# Nothing existing: …`） | 功能 | 新測試檔 | 跑 `test_scope.py` 的 TC-070 檢查 | 新測試檔前 40 行有 `# Nothing existing: …`，那句至少 15 字；檢查為綠 | 自動：既有 `test_scope.py` |
| TC-050 | 原則 II（TC-071：平台不啟動程式、沒有常駐迴圈與背景工作） | 功能 | 本片完成後的 `store.py` | 跑 `test_scope.py` 的 TC-071 檢查；新測試 `test_store_source_has_no_subprocess_and_no_forbidden_word` | 兩者為綠；新增的遷移程式只做 SQL，沒有 `subprocess`、`os.system`、執行緒、`while True` | 自動：既有 `test_scope.py`＋新測試檔 |
| TC-051 | 平台原始碼禁用字（TC-061，掃描 `abf_platform/`）；不得拆字拼接 | 功能 | 本片完成後的 `abf_platform/` | 跑 `test_scope.py` 的 TC-061 檢查；新測試檢查新增程式有沒有把禁用字拆開再拼接 | 兩者為綠；`store.py` 新增的註解與字串只寫「代理／agent」，沒有 TC-061 禁用的那個英文字，也沒有拆字拼接 | 自動：既有 `test_scope.py`＋新測試檔 |
| TC-052 | 原則 II（沒有第二份 run 狀態；檢查 `tests/no_second_run_state_test.sh`）與修訂 4.0.0／5.0.0（寫入要經本人確認） | 功能 | 本片完成後 | 跑 `bash tests/no_second_run_state_test.sh` | 為綠；新增欄位沒有引入任何新的狀態來源或寫入路徑（寫入鎖證明見 TC-004、TC-005） | 自動：既有 shell 測試 |
