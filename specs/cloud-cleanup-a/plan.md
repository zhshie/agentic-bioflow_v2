---
id: cloud-cleanup-a
title: 資料庫先學會「clean_work」這個種類與「work_cleaned_at」欄位（只動 store.py 與 migration，沒有任何功能上線）
tier: B
kinds: backend
lane: L-cleanup
after:
base: v3
---

# cloud-cleanup-a

> 本檔由 developer-agent 起草（2026-10-24），把 `cloud-cleanup.md`（C-7，約 30 檔）切成六片之第一片：**a 資料庫 → b 平台記帳 → c 代理刪 Slurm 的 work → d 代理刪 Google Batch 的 work → e 確認頁（ui）→ f 成功後提出申請＋文件**。**本片只讓資料庫「放得下」新種類與新欄位**：沒有任何程式會寫入 `clean_work`，使用者看不到任何變化。B 級（後端行為改變、但此片無使用者可見變化）→ verifier 通過＋CI 綠即可合併。
> **名詞**：「work 目錄」＝Nextflow 放每個 task 中間檔的 `work/`，不是結果。「確認種類」＝`confirmations.kind`，「工作種類」＝`jobs.kind`。平台程式碼（`abf_platform/`、`abf_launch/`）裡一律寫「代理／agent」，不得出現 TC-061 禁用的那個英文字（`test_scope.py:189`）。

## 目標
`platform.db` 的 `confirmations.kind` 與 `jobs.kind` 兩個 CHECK 都接受 `clean_work`，`launches` 多一欄 `work_cleaned_at`（可空）；新資料庫與舊資料庫升級後的結構完全相同，升級不丟任何一列、重複開啟內容位元相同。對使用者的意義：後面五片（平台記帳、代理刪除、確認頁、成功後提出）都靠這個結構，先單獨合併可以把「最容易出事的資料庫升級」從功能裡切開來驗。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md` 與 `CLAUDE.md`；每句至少對應一條測試案例：
- 「**跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪**」（裁示 16，第 58 行）→ 新的確認種類 `clean_work` 存在，且跟 `launch`／`cancel` 是分開的（不借用 `cancel`）；本片沒有任何自動寫入。
- 「**C-7 `cloud-cleanup`**（B／backend）：succeeded 後建「刪除 work 目錄」的待確認請求（走 `_ask`，新 kind `clean_work`；對 nano4 也適用）」（第 171 行）→ 種類名恰為 `clean_work`（確認種類與工作種類同名）。
- 「網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」（裁示 14，第 54 行）→ 本片無網頁畫面，屬自合範圍。
- 「直接 `scancel`，以及刪改叢集端 `rawdata`／`results`／`analysis`，一律擋住」（`CLAUDE.md` §3.4）→ 資料庫層保持「寫入型工作沒有確認憑證就 `IntegrityError`」這道鎖，`clean_work` 也在其中。

## 範圍：檔案（只准改這些，共 9 個含 ledger）
- `platform/abf_platform/store.py`：
  - `STATE_SCHEMA` 的 `confirmations.kind` CHECK（現 :206）改為 `('launch', 'cancel', 'clean_work')`。
  - `_JOBS_TABLE`（:232）的 `kind` CHECK（:236）在 `'read_task_log'` 後加 `'clean_work'`；寫入鎖 CHECK（:248）改為 `kind NOT IN ('launch_nextflow', 'cancel_run', 'clean_work') OR confirmation_id IS NOT NULL`。
  - `_LAUNCHES_TABLE`（:253）最後加 `work_cleaned_at REAL`（可空，放在 `attempt_kind` 之後）。
  - 新增 `_migrate_confirmation_kinds(con)`、改 `_migrate_jobs_kinds`（:402）的判斷字樣、新增 `_add_cleanup_column(con)`，並調整 `connect_state`（:583）的呼叫順序（見作法）。
- `platform/tests/test_cleanup_store.py`（新；檔首 `# Nothing existing: …` 一句至少 15 字，TC-070）。
- 必須更新的既有斷言（有意；其他一律不准動，PR 說明逐條寫「以前／以後／理由」）：
  - `platform/tests/test_http_site_samplesheet.py:543` 的 `SCHEMA_SHA256`（整份 state 結構雜湊；`test_tc057_no_table_or_column_changed`）：以前＝`56f767…662f9d`；以後＝新結構的雜湊（executor 用該測試自己的算法重算並貼值）。理由：CHECK 與欄位變了。
  - `platform/tests/test_cloud_cost.py:746-748`（`test_nothing_stops_a_running_job_and_no_policy_channel_exists`）：jobs 的種類清單加 `clean_work`（放最後）；`"kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel'))"` 改為含 `'clean_work'`。
  - `platform/tests/test_station_platform.py:322-328`：插入各種類的元組加 `("clean_work", "c3")`（先插一張 `kind='clean_work'` 的 `c3`），`declared` 期望集合加 `clean_work`。
  - `platform/tests/test_keep_submissions.py:774`：只改 `"CHECK (kind IN ('launch', 'cancel'))" in store.STATE_SCHEMA` 那一行（加 `'clean_work'`）；:773 的 `set(confirm.JOB_KIND)` 屬 b 片，本片不動。（:872 的 `drops` 表可加 `"launches": (…, "work_cleaned_at")` 讓 TC-109 也驗新欄位；加不加由 executor 判斷，加了要在 PR 說明。）
  - `platform/tests/test_resume_scope.py:73`：只改 `store.STATE_SCHEMA.count("kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel'))") == 1` 那一行；:68-70 屬 b 片，本片不動。
  - `platform/tests/test_gcb_launch.py:1081`（`test_no_migration_is_needed_and_the_columns_are_unchanged`）：`cols["launches"]` 末尾加 `"work_cleaned_at"`；函式名裡的 "unchanged" 改成合乎事實的說法。
- `specs/cloud-cleanup-a/ledger.md`（executor 進度帳本）。

**禁碰**：`confirm.py`、`jobs.py`、`actions/`、`build.py`、`web*.py`、`receiver.py`、`abf_station/*`、`test_resume_scope.py` 與 `test_keep_submissions.py` 的其他斷言、`test_human_channel.py:198`（那是「舊格式資料庫」的升級來源夾具）。

## 作法
1. **新結構**（決定）：確認種類三種 `launch`／`cancel`／`clean_work`；工作種類七種（`preflight, list_site_files, launch_nextflow, cancel_run, fetch_run_records, read_task_log, clean_work`，`clean_work` 放最後，因為 `test_run_diag_tools.py:290-293` 的舊庫夾具靠 `.replace(", 'read_task_log'", "")` 還原舊 CHECK）；寫入鎖涵蓋三個寫入型工作種類。欄位 `launches.work_cleaned_at REAL`，語意＝「代理回報這個 run 的 work 已刪（或本來就沒有）的時間」，只有 b 片之後的程式會寫，本片永遠是 NULL。
2. **舊庫升級的順序**（`connect_state` :583-604）：
   1. 既有的 `_migrate_jobs`、`_migrate_launches`、`_migrate_jobs_kinds` 照舊先跑；`_migrate_jobs_kinds` 的跳過條件由「sql 含 `read_task_log`」（:407、:413）改為「sql 含 `clean_work`」，因此一次開啟就把任何更舊的 jobs 表直接升到最新（不會多出一次重建）。
   2. `con.executescript(STATE_SCHEMA)` 與既有的 `_add_*` 照舊。
   3. **最後**才跑 `_migrate_confirmation_kinds`：必須排在 `_add_confirmation_state`（:568，它把舊列標成 `confirmed`／`TERMINAL`）與 `_add_forgotten_columns` 之後，否則重建時舊列會被填成預設的 `pending`。
   4. `_add_cleanup_column(con)`（仿 `_add_attempt_columns` :528：欄位不在才 `ALTER TABLE launches ADD COLUMN work_cleaned_at REAL`；另一個行程先加了就不報錯）。
3. **重建 `confirmations`（本片最難的一步）**。`confirmations` 是 `jobs.confirmation_id REFERENCES confirmations(id)`（:247）的**父表**，而 `connect_state` 開了 `PRAGMA foreign_keys = ON`（:588）；在外鍵開著時 `DROP TABLE` 父表會先隱含刪列而失敗。所以照 SQLite 官方「Making Other Kinds Of Table Schema Changes」的步驟做（`sqlite.org/lang_altertable.html`，executor 動手前讀一次並把網址寫進 ledger）：
   - 判斷：`SELECT sql FROM sqlite_master WHERE name='confirmations'` 已含 `'clean_work'` 就直接返回，**一個位元都不動**。
   - `PRAGMA foreign_keys = OFF`（必須在交易之外執行）→ `BEGIN IMMEDIATE` → 在交易內**再判斷一次**（另一個行程可能剛做完）→ 用 `STATE_SCHEMA` 裡的 confirmations 定義建 `confirmations_new` → 依兩表共有的欄位名稱複製（欄位順序與全新資料庫相同，才會與 `test_human_channel.py:203` 的欄位順序斷言一致）→ 呼叫 `_migration_step("copied")`（測試用的故障注入點，:360）→ `DROP TABLE confirmations` → `ALTER TABLE confirmations_new RENAME TO confirmations` → `PRAGMA foreign_key_check` 必須為空，否則 `ROLLBACK` 並丟錯 → `COMMIT`。
   - 無論成功或失敗，`finally` 一律 `PRAGMA foreign_keys = ON` 並把 `isolation_level` 還原（比照 :432-435）；失敗要 `ROLLBACK`，舊表與所有列完全如舊。
   - 重建後 `jobs` 表上的 `confirmation_id UNIQUE REFERENCES confirmations(id)` 仍指向名為 `confirmations` 的表（外鍵關閉時改名不會改寫別表的參照）；測試要斷言 `PRAGMA foreign_key_list(jobs)` 的目標是 `confirmations`、`PRAGMA foreign_key_check` 為空。
4. **migration 需要**（理由）：兩個 CHECK 不能原地修改（SQLite 沒有 `ALTER … CHECK`），沒有它們 `clean_work` 寫不進舊庫；新欄位是新增欄位。已列入「失敗先行測試」。
5. 本片**不**加任何讀寫 `work_cleaned_at` 的程式；讀的人（f 片）必須容忍沒有這欄的舊唯讀庫（`owned_run_names` :280 已有 `sqlite3.OperationalError` 的先例）。

## 失敗先行測試（現在都會紅；新檔 `test_cleanup_store.py`，預估 24 條新增 TC，另有上列 6 處既有斷言的有意更新）
新結構：
- `test_fresh_confirmations_take_clean_work_and_still_refuse_resume_relaunch_retry_and_empty`。
- `test_fresh_jobs_take_clean_work_only_with_a_confirmation`（有憑證可插；`confirmation_id` 為 NULL → `IntegrityError`；對 `launch_nextflow`、`cancel_run` 同樣仍擋）。
- `test_fresh_jobs_still_refuse_rm_delete_clean_and_other_words`（`rm`、`delete`、`clean`、`clean_work `（尾端空白）、`CLEAN_WORK`、空字串）。
- `test_launches_has_work_cleaned_at_as_its_last_column_and_it_is_null_by_default`。
- `test_a_new_and_an_upgraded_database_have_the_same_schema_text_for_confirmations_jobs_and_launches`。
升級：
- `test_old_confirmations_table_is_rebuilt_and_every_row_is_identical`：舊庫（confirmations CHECK 只有兩種、含 pending／confirmed／void 各一列、有 `forgotten_at`）升級後 `SELECT *` 逐列相等。
- `test_a_database_before_009c_gets_its_old_rows_marked_confirmed_terminal_not_pending`（排序正確性：重建發生在 `_add_confirmation_state` 之後）。
- `test_jobs_referencing_the_rebuilt_confirmations_keep_their_ids_and_links`；`test_foreign_key_check_is_empty_and_foreign_keys_are_on_afterwards`；`test_jobs_sequence_counter_survives`。
- `test_a_jobs_table_without_read_task_log_is_upgraded_straight_to_the_newest_kinds_in_one_open`。
- `test_a_launches_table_without_the_attempt_columns_and_without_work_cleaned_at_gets_all_four`。
- `test_old_launches_rows_keep_every_old_value_and_get_null_work_cleaned_at`。
冪等與安全：
- `test_opening_twice_changes_nothing`（`helpers.all_files_digest` 前後相同，新庫與升級後的庫各一次）。
- `test_a_failure_in_the_copy_step_leaves_the_old_table_and_rows_as_they_were_and_foreign_keys_on`（把 `_migration_step` 換成丟錯）；`test_the_next_open_after_that_failure_succeeds`。
- `test_a_second_connection_opening_at_the_same_time_finds_it_done_and_does_not_fail`。
- `test_an_already_new_confirmations_table_is_not_touched`（判斷在 `BEGIN` 前就返回；用 `sqlite_master` 的 rootpage 或檔案雜湊證明沒重建）。
- `test_pending_and_void_requests_made_before_the_upgrade_are_still_found_by_confirm_describe`（唯讀函式 `confirm.describe` 在升級後的庫照常回結果）。
- `test_read_only_open_of_an_old_database_does_not_upgrade_it`（`open_readonly` :622 不升級）。
- `test_store_source_has_no_subprocess_and_no_forbidden_word`（TC-071／TC-061 的既有掃描涵蓋 `store.py`，這裡只確認新增程式沒有拆字拼接）。

## 完成標準（done when）
- 自動：新測試綠；上列 6 處更新後全套綠（含 `tests/platform_test.sh`、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`）；MCP 工具數仍 12；`git diff --name-only` 只有「範圍：檔案」所列（`git diff --stat` 貼進 ledger，依 dev-plans 通例由 verifier 核對）。
- 對一份**真實**舊庫（維護者桌機 `platform.db` 的複本，不是夾具）開啟一次：`SELECT *` 各表前後相同、`PRAGMA integrity_check` 為 ok、`PRAGMA foreign_key_check` 為空（executor 若拿不到真實複本，在 ledger 寫明，由 developer-agent 在桌機補跑；不得省略）。
- 無手動驗收、無文件（本片沒有使用者可見行為；文件在 f 片）。

## 環境事實
（行號為 `origin/v3` @ `279363b`；以函式名為準，動手前 `git fetch -q origin` 再核對。）
- `store.py`：`STATE_SCHEMA` :176；confirmations 表 :203-221，其 `kind` CHECK :206，`state` CHECK :210；`launches_run_name` 索引 :223；`_JOBS_TABLE` :232-250（`kind` CHECK :236、`confirmation_id TEXT UNIQUE REFERENCES confirmations(id)` :247、寫入鎖 :248）；`_LAUNCHES_TABLE` :253-268；`_migration_step` :360；`_migrate_jobs` :364（它在連 confirmations 都沒有的 007 庫上自建一個只有兩種種類的 confirmations，:381-382）；`_migrate_jobs_kinds` :402；`_add_attempt_columns` :528；`_add_forgotten_columns` :548；`_add_confirmation_state` :568；`connect_state` :583（`PRAGMA foreign_keys = ON` :588）；`open_readonly` :622。
- 目前 `confirmations` **沒有**任何放寬 CHECK 的升級函式（`_add_confirmation_state` 只加欄位），所以本片是第一次重建 `confirmations`；`jobs` 的重建先例是 `_migrate_jobs_kinds`。
- 釘住結構的既有測試（本片要更新的，見範圍）：`test_http_site_samplesheet.py:543`（`SCHEMA_SHA256`）、`test_cloud_cost.py:746-748`、`test_station_platform.py:322-328`、`test_keep_submissions.py:774`、`test_resume_scope.py:73`、`test_gcb_launch.py:1081`。**舊計畫沒有列 `SCHEMA_SHA256`、`test_cloud_cost.py`、`test_gcb_launch.py:1081` 這三處**（它們是計畫寫成之後才出現的），是本次重新核對才發現的。
- 其他會讀這些表的測試不受影響：`test_human_channel.py:198-210`（舊庫夾具與欄位順序，結果不變）、`test_run_diag_tools.py:285-300`（`.replace(", 'read_task_log'", "")` 在 `clean_work` 排最後時仍成立）、`test_launch_platform.py:158-160`。
- SQLite 外鍵與 `DROP TABLE` 父表的行為、`PRAGMA foreign_keys` 不能在交易內改：官方文件 `sqlite.org/lang_altertable.html`、`sqlite.org/foreignkeys.html`。**CI 與維護者機器上 Python 內建的 SQLite 版本我沒有查到**（起草機器的 `python` 是 2.7，不能代表）；executor 在 ledger 記下 `sqlite3.sqlite_version`，`PRAGMA foreign_key_check` 需要 SQLite 3.7.16 以上，若 CI 比這舊就停手回報。
- 憲法：平台不啟動程式（`test_scope.py:99` TC-071）；平台原始碼不得出現 TC-061 的禁用字（`test_scope.py:189`；掃描範圍是 `abf_platform/`）；不得拆字拼接。新 `.py` 檔前 40 行要有 `# Nothing existing: …`（TC-070）。

## 不做
- 不改 `confirm.py`、`jobs.py`（`JOB_KIND`、`CONFIRMED`、`KINDS`、`DEADLINE_SECONDS` 都留給 b 片）；不寫任何會產生 `clean_work` 列的程式。
- 不動 `launches` 其他欄位、不改 `jobs` 欄位順序、不加索引、不加新表。
- 不做資料搬移以外的清理（不刪舊列、不重算任何東西）。
- 不碰 AWS／Azure／K8s 類型、不改 Slurm 與 Google Batch 的送出／取消／續跑。

## 裁決（2026-10-24，developer-agent；已併入上文，與其他段落不衝突）
1. **新種類 `clean_work`，確認種類與工作種類同名，不借用 `cancel`。** 理由：`jobs._check_confirmation`（:257）靠「確認種類必須對得上工作種類」擋住拿取消憑證去做別的事；借用 `cancel` 等於拆掉這道鎖。代價就是本片的兩個 CHECK 與 migration。
2. **`store.py` 在本任務範圍內，且在 017d 與 cloud-cost 都已合併之後才開工。** 現況：cloud-cost（#188）、cloud-cost-wire（#199）已在 `v3`，它們改的是 `task_usage` 與 `tokens.db` 的 `cloud_caps`，與本片動的 state 資料庫不同表；開工時以最新 `v3` 重新核對行號。
3. **資料庫保持「寫入型工作沒有確認憑證就寫不進去」**：`clean_work` 與 `launch_nextflow`、`cancel_run` 同列在寫入鎖裡。
4. **`work_cleaned_at` 的語意（供後面各片遵守）**：只有代理明說 `cleaned: true` 時才會被寫（「本來就沒有 work」也算）；逾時或錯誤不記為已清、不自動重試。本片只建欄位。
5. **切片理由（舊計畫整份太大）**：舊計畫約 30 檔、需求超過 60 條測試；依 `dev-architecture-review-2026-10-24.md` §3 與 `dev-plans/README.md` 通例切成六片，每片 ≤10 檔、≤60 TC。本片 9 檔（含 ledger）。

## 裁決二（2026-10-24，回應 verifier 出題退回）
7. 採 (a)：`_migrate_jobs_kinds` 的跳過條件＝jobs 表 sql **同時含** `read_task_log` 與 `clean_work` 才跳過；其餘一律重建。`test_run_diag_tools.py` 不改。
8. 新增 TC 以逐條列出的 21 條為準（「約 24」作廢）。
9. 「結構相同」＝欄位名稱／順序／型別／NOT NULL／預設值／主鍵＋各 CHECK 接受與拒絕的集合相同，不比 `sqlite_master.sql` 逐字；測試名改成 `…have_the_same_structure…`。
10. 真實舊庫複本檢查：executor 在 ledger 寫「拿不到維護者桌機的 platform.db，由 developer-agent 在桌機補跑」即可，不算 UNVERIFIED；developer-agent 合併前補跑並把輸出貼進 PR。

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
