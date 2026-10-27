# 測試案例：run 成功的當下提出「清掉中間檔」的待確認申請（cloud-cleanup-f，含文件與手動驗收）

**規格**：`specs/cloud-cleanup-f/plan.md`（本片沒有另寫 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「work 目錄」＝Nextflow 放每個 task 中間檔的 `work/`，不是結果；「申請」＝種類為 `clean_work`、狀態為 `pending` 的待確認紀錄（本人在確認頁按「確認刪除」之前，它不是確認，也不產生任何工作）；「代理」＝站台上真的去刪檔的那一端（c 片 Slurm、d 片 Google Batch 已做好）；「本人」＝申請上記的那位登入者（run 的擁有者）；「看板」＝登入後的 run 清單與單一 run 頁；「假站台／假 bucket」＝測試用的假資料夾與假儲存桶，會記下被刪了什麼。

範例路徑只用計畫指定的：Slurm 環境 `workDir` 為 `/work/u1/abf`、run 資料夾 `/work/u1/abf/runs/ampliseq-d5`、work 為 `/work/u1/abf/runs/ampliseq-d5/work`；Google Batch 環境 `workDir` 為 `gs://lab-bucket/work`、work 為 `gs://lab-bucket/work/runs/ampliseq-d5/work`；續跑的 run 為 `ampliseq-d5-a2`，沿用 `ampliseq-d5` 的資料夾。

**維護者原話與 TC 對照**（計畫「維護者原話」逐字引文，每句至少一條）：

| 維護者原話 | 對應 TC |
|---|---|
| 「跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪」：①只有成功的 run 才提出 | TC-031、TC-032、TC-038～TC-041、TC-059 |
| 同上：②刪 work 一定經本人確認，沒有任何自動路徑（無排程、無「N 天後自動」、無 POLICY 通道） | TC-034、TC-069、TC-070、TC-079、TC-103、TC-112 |
| 同上：③「結果」不在這次刪除範圍 | TC-008、TC-022、TC-071 |
| 「C-7 `cloud-cleanup`：succeeded 後建『刪除 work 目錄』的待確認請求（新 kind `clean_work`；對 nano4 也適用）」 | TC-031、TC-032、TC-056 |
| 同上後半「結果到期前 7 天建 Decision-needed 通知、費用頁顯示儲存月費」→ 計畫明講不在本任務 | TC-118 |
| 「直接 scancel，以及刪改叢集端 rawdata／results／analysis，一律擋住」（CLAUDE.md §3.4）：提出的路徑一律是 `…/work` | TC-002、TC-004、TC-008、TC-071 |
| 「網頁畫面以外的 B 級，verifier 通過＋CI 綠就由我合併；網頁畫面仍等他回好／不好」：確認畫面文字附截圖列進每日清單 | TC-101 |
| 「平台不啟動程式」（憲法原則 2、TC-071、TC-061） | TC-109、TC-110 |
| 「每個寫入要本人答應」（憲法 6／ADR 0006） | TC-034、TC-069、TC-080、TC-103 |

## User Story 1 — 申請的內容與確認畫面的白話（優先度 P1）

前置通用：資料庫裡有一筆 hand-off 紀錄（平台送出 run 的紀錄）；測試用 `build.prepare_clean`／`build.clean_screen` 直接建，不經網頁。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1（內容包的鍵） | 功能 | Slurm 環境 `workDir=/work/u1/abf`；本人 A 的 run `ampliseq-d5` 已成功、紀錄完整 | 對 A 的 `ampliseq-d5` 呼叫 `prepare_clean` | 內容包的鍵恰為 `version, run_name, slurm_job_id, run_folder, agent, ce, work` 七個，不多不少；`version` 為 1 | 自動：`test_cleanup_offer.py::test_slurm_bundle_has_the_seven_keys_and_work_is_the_run_folder_plus_work` |
| TC-002 | 作法 1（Slurm 公式） | 功能 | 同上；`run_folder=/work/u1/abf/runs/ampliseq-d5` | 同上 | `work` 恰為 `/work/u1/abf/runs/ampliseq-d5/work`（run 資料夾＋`/work`） | 自動：同上 |
| TC-003 | 作法 1（續跑沿用原資料夾） | 功能 | run `ampliseq-d5-a2` 是 `ampliseq-d5` 的續跑，hand-off 紀錄的 `run_folder` 是原資料夾 `/work/u1/abf/runs/ampliseq-d5` | 對 `ampliseq-d5-a2` 呼叫 `prepare_clean` | `work` 是 `/work/u1/abf/runs/ampliseq-d5/work`，不是任何以 `-a2` 命名的資料夾下的 work | 自動：`test_a_resume_attempt_gets_the_origin_folders_work_not_a_folder_named_after_the_attempt` |
| TC-004 | 作法 1（Google Batch 公式） | 功能 | Google Batch 環境 `workDir=gs://lab-bucket/work`；A 的 run `ampliseq-d5` 已成功 | 呼叫 `prepare_clean` | `work` 恰為 `gs://lab-bucket/work/runs/ampliseq-d5/work` | 自動：`test_gcb_bundle_work_is_workdir_runs_run_work_and_matches_what_the_agent_recomputes` |
| TC-005 | 作法 1（與 d 片代理同一公式） | 功能 | 同上 | 把內容包交給 d 片代理重算它要刪的前綴 | 代理重算的值與內容包 `work` 完全相同（同一個位置，不是相近） | 自動：同上 |
| TC-006 | 作法 1（`ce` 欄） | 功能 | 同上（Slurm 與 Google Batch 各一） | 呼叫 `prepare_clean` | 內容包的 `ce` 等於當下環境的快照（`snapshot_ce` 的結果），與送出時同一種形狀 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-006） |
| TC-007 | 作法 1（雜湊穩定） | 功能 | 同 TC-001 | 對同一 run 連續建兩次內容包，各算雜湊 | 兩次內容包完全相同、雜湊相同（這樣重複提出才會被認成同一張） | 自動：`test_the_bundle_is_identical_when_built_twice` |
| TC-008 | 維護者原話③；CLAUDE.md §3.4 | 功能 | Slurm 與 Google Batch 的各種成功 run，包括 run 名稱剛好叫 `results` 的一個 | 對每個呼叫 `prepare_clean` | 每個內容包的 `work` 都以 `/work` 結尾，被刪的對象是 work 目錄，不是名為 `rawdata`、`results`、`analysis` 的資料夾，也不是 run 資料夾本身 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-008） |
| TC-009 | 作法 1（拒絕：別人的 run） | 例外 | B 登入；run `ampliseq-d5` 是 A 送出的 | 以 `owner=B` 呼叫 `prepare_clean` | 被拒絕（`build.Refusal`），說「不是平台自己送出的」這類白話，與 run 不存在時說法一樣，不洩漏它屬於 A | 自動：`test_prepare_clean_refuses_each_unfit_case_in_plain_words` |
| TC-010 | 作法 1（拒絕：無編號） | 例外 | hand-off 紀錄的 `slurm_job_id` 為空 | 呼叫 `prepare_clean` | 被拒絕，白話說這個 run 沒有工作編號 | 自動：同上 |
| TC-011 | 作法 1（拒絕：已清過） | 例外 | 紀錄的 `work_cleaned_at` 已有值 | 呼叫 `prepare_clean` | 被拒絕，白話說「已經清過了」 | 自動：同上 |
| TC-012 | 作法 1（拒絕：環境找不到） | 例外 | 紀錄裡的環境已被刪掉 | 呼叫 `prepare_clean` | 被拒絕，白話說環境找不到 | 自動：同上 |
| TC-013 | 作法 1（拒絕：代理換了） | 例外 | 環境現在的代理與當初送出該 run 的代理不同 | 呼叫 `prepare_clean` | 被拒絕，白話說是別的代理送出的 | 自動：同上 |
| TC-014 | 作法 1（拒絕：環境現在不收清理） | 例外 | 環境已停用，使 `target_problem(…, "clean_work", owner)` 回報有問題 | 呼叫 `prepare_clean` | 被拒絕，說的是 `target_problem` 的白話原因 | 自動：同上 |
| TC-015 | 作法 1（拒絕：Slurm 的 workDir 送出後改過） | 例外 | Slurm 環境的 `workDir` 在送出之後被改成別的值（與當初送出的內容包不同） | 呼叫 `prepare_clean` | 被拒絕，白話說環境在送出之後改過、無法確認路徑，不提出 | 自動：同上 |
| TC-016 | 作法 1（拒絕：Google Batch 的 workDir 送出後改過） | 例外 | Google Batch 環境的 `workDir` 從 `gs://lab-bucket/work` 改成別的 bucket | 呼叫 `prepare_clean` | 被拒絕，同上；不會用現在的環境算出一個不是這個 run 的路徑 | 自動：同上 |
| TC-017 | 作法 1（Slurm 的資料夾位置核對） | 例外 | Slurm 的 `run_folder` 上一層不是 `<workDir>/runs` | 呼叫 `prepare_clean` | 被拒絕，不提出 | 自動：同上 |
| TC-018 | 作法 1（拒絕：找不到當初送出的內容） | 例外 | 當初送出的內容已不在（無法確認環境沒變） | 呼叫 `prepare_clean` | 被拒絕，白話說找不到當初的內容，所以不提出 | 自動：同上 |
| TC-019 | 作法 1（拒絕：被 forget） | 例外 | 擁有者已對這個 run 做過 `forget`（刪除送出內容） | 呼叫 `prepare_clean` | 被拒絕，白話說這個 run 的內容已被刪除 | 自動：同上 |
| TC-020 | 專長守則（錯誤訊息）；作法 1 | 例外 | TC-009～TC-019 各種拒絕 | 逐一讀拒絕訊息 | 每一則都說明發生什麼事，不含 SQL、`Traceback`、檔案堆疊 | 自動：同上 |
| TC-021 | 作法 5 ① | 功能 | Slurm 的清理申請，要刪 `/work/u1/abf/runs/ampliseq-d5/work` | 讀 `clean_screen` 的文字 | 逐字含「這會永久刪除這次 run 的中間檔資料夾：」，其後是完整路徑 `/work/u1/abf/runs/ampliseq-d5/work` | 自動：`test_the_screen_says_what_is_deleted_what_is_not_and_that_resume_is_gone` |
| TC-022 | 作法 5 ② | 功能 | 同上 | 同上 | 逐字含「結果（results）、原始資料與分析資料夾不會被動。」 | 自動：同上 |
| TC-023 | 作法 5 ③ | 功能 | 同上 | 同上 | 逐字含「刪掉之後這個 run 不能再續跑（-resume）；要再算一次，請當成新分析重新送出。」；不含舊寫法「要重算只能原樣重跑或重新送出」 | 自動：同上 |
| TC-024 | 作法 5（Google Batch 共用前三句） | 功能 | Google Batch 的清理申請，要刪 `gs://lab-bucket/work/runs/ampliseq-d5/work` | 讀 `clean_screen` | 同樣逐字含 ①②③ 三句，①後的完整路徑是 `gs://lab-bucket/work/runs/ampliseq-d5/work` | 自動：同上 |
| TC-025 | 作法 5 ④（bucket 句） | 功能 | 同上 | 同上 | 逐字含「刪除的是 bucket 裡這個前綴下的物件。」 | 自動：`test_only_the_gcb_screen_has_the_bucket_sentence_and_it_never_says_cannot_be_undone_unless_the_ledger_proved_it` |
| TC-026 | 作法 5 ④（如實說明軟刪除，不得寫無法還原） | 功能 | 同上；d 片 ledger 的結論是：新建的桶預設有 7 天軟刪除、保留期內仍可還原、仍計費；沒有證實預設無法還原 | 讀 Google Batch 畫面 | 有一句如實的軟刪除／版本控制說明，與 d 片 ledger 一致；畫面任何地方都沒有「無法還原」「不能還原」「無法復原」「cannot be undone」 | 自動：同上 |
| TC-027 | 作法 5 ④（只有 Google Batch 才有） | 功能 | Slurm 的清理申請 | 讀 Slurm 的 `clean_screen` | 沒有 bucket 句，也沒有軟刪除句 | 自動：同上 |
| TC-028 | 作法 5 ⑤（無金額） | 功能 | Slurm 與 Google Batch 的畫面 | 讀畫面全文 | 沒有任何金額（沒有 `$`、`NT`、`元`、`USD`、費用數字） | 自動：`test_the_screen_has_no_money_and_no_internal_words` |
| TC-029 | 作法 5 ⑤（無內部詞） | 功能 | 同上 | 同上 | 沒有 `Traceback`、`SELECT`、`args_json` 這類內部詞；除 Slurm 工作編號外沒有內部欄位名 | 自動：同上 |
| TC-030 | 範圍（`clean_screen` 用 `terminal.esc`，仿 `cancel_screen`） | 功能 | run 資料夾或 run 名稱含控制字元（例如終端機換色碼） | 讀 `clean_screen` | 控制字元被轉義，與 `cancel_screen` 處理方式相同，不會原樣出現在畫面 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-030） |

## User Story 2 — run 成功的當下，只為擁有者提出一張申請（優先度 P1）

前置通用：平台資料庫存在；hand-off 紀錄完整；使用者 A 是擁有者。以 `actions.offer_cleanup(platform_path, index_path, run_name, clock=…)` 直接呼叫。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | 作法 2；C-7（nano4） | 功能 | A 的 Slurm run `ampliseq-d5`，run 索引狀態 `succeeded` | 呼叫 `offer_cleanup` | `confirmations` 表新增恰好一張：種類 `clean_work`、狀態 `pending`、擁有者 A、環境為該 run 的環境；回傳 `offered` 為真 | 自動：`test_a_succeeded_run_gets_one_pending_clean_work_request_and_nothing_else` |
| TC-032 | 作法 2；C-7（Google Batch） | 功能 | A 的 Google Batch run 已 `succeeded` | 同上 | 同上，申請內容的 `work` 是 `gs://lab-bucket/work/runs/ampliseq-d5/work` | 自動：同上 |
| TC-033 | 作法 2 步驟 4 | 功能 | 同 TC-031 | 取出申請存的內容包與畫面文字 | 內容包等於 `prepare_clean` 的結果；畫面文字等於 `as_text(clean_screen(...))` | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-033） |
| TC-034 | 憲法 6／ADR 0006；作法 2 | 功能 | 同 TC-031；呼叫前先記下 `jobs` 表列數 | 呼叫 `offer_cleanup` | `jobs` 表列數不變，沒有任何 `clean_work` 工作被排進佇列（提出申請不是確認） | 自動：同 TC-031 |
| TC-035 | 作法 2（不重複） | 功能 | 同 TC-031；已提出過一次 | 再呼叫 `offer_cleanup` 一次 | 申請仍只有一張，回的是既有那張，沒有第二張 | 自動：`test_offering_again_makes_no_second_request` |
| TC-036 | 作法 2 步驟 4（7 天有效） | 功能 | 同 TC-031 | 讀申請的到期時間；再把時鐘撥過 7 天 | 到期時間是建立後 7 天；過了 7 天該申請是逾時 | 自動：`test_the_request_lives_seven_days_and_does_not_use_up_the_ten_slots` |
| TC-037 | 作法 2 步驟 4（不佔 10 張名額） | 功能 | A 已有 10 張其他種類的待確認申請（名額用滿） | 對成功的 run 呼叫 `offer_cleanup` | 清理申請仍被建立；不影響 A 那 10 張，A 的其他種類名額計數不變 | 自動：同上 |
| TC-038 | 不做：失敗 run 不清；裁示 16① | 不在範圍 | run 狀態 `failed` | 呼叫 `offer_cleanup` | 沒有建申請；回 `offered` 為假並附 `reason` | 自動：`test_failed_aborted_lost_running_and_unknown_runs_get_no_request`（failed 一條） |
| TC-039 | 同上 | 不在範圍 | run 狀態 `aborted`（Nextflow 視為失敗） | 同上 | 沒有建申請 | 自動：同上（aborted 一條） |
| TC-040 | 同上 | 不在範圍 | run 狀態 `lost`（失聯） | 同上 | 沒有建申請 | 自動：同上（lost 一條） |
| TC-041 | 同上 | 不在範圍 | run 狀態 `running`（還沒結束） | 同上 | 沒有建申請 | 自動：同上（running 一條） |
| TC-042 | 作法 2 步驟 2 | 例外 | 要提的 run 名稱在 run 索引裡不存在 | 同上 | 沒有建申請，靜靜回 `offered` 為假 | 自動：同上（unknown 一條） |
| TC-043 | 作法 2 步驟 1；裁決 2 | 例外 | 成功的 run 的 hand-off 紀錄 `user_id` 為空（純終端機送出，沒有擁有者） | 呼叫 `offer_cleanup` | 沒有建申請，靜靜回 `offered` 為假 | 自動：`test_a_run_without_an_owner_gets_no_request` |
| TC-044 | 專長守則（擁有者規則）；作法 2 | 例外 | A 的 run 成功；B 也是登入使用者 | 呼叫 `offer_cleanup` | 申請的擁有者只會是 A；B 名下沒有任何清理申請；不存在把 A 的 run 提給別人的路徑 | 自動：`test_another_users_run_is_not_offered_to_the_caller` |
| TC-045 | 作法 2 步驟 1 | 例外 | 紀錄的 `work_cleaned_at` 已有值，run 狀態 `succeeded` | 呼叫 `offer_cleanup` | 沒有建申請 | 自動：`test_a_run_whose_work_was_cleaned_gets_no_request` |
| TC-046 | 作法 1、2 | 例外 | 擁有者已對該 run `forget` | 呼叫 `offer_cleanup` | 沒有建申請 | 自動：`test_a_forgotten_run_gets_no_request` |
| TC-047 | 作法 2 步驟 1 | 例外 | 紀錄的 `slurm_job_id` 為空 | 呼叫 `offer_cleanup` | 沒有建申請 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-047） |
| TC-048 | 作法 2 步驟 1 | 例外 | 這個 run 名稱在 hand-off 紀錄裡沒有紀錄 | 呼叫 `offer_cleanup` | 沒有建申請，靜靜回 `offered` 為假 | 自動：同上（註解標 TC-048） |
| TC-049 | 作法 2「任何例外都靜靜跳過」 | 例外 | 把 `confirm.create_pending` 換成會丟例外的假貨 | 呼叫 `offer_cleanup` | 不丟出例外；回 `{"offered": False, "reason": …}` | 自動：`test_offer_cleanup_never_raises` |
| TC-050 | 同上 | 例外 | 把 `build.prepare_clean` 換成會丟例外的假貨 | 同上 | 同上 | 自動：同上 |
| TC-051 | 同上 | 例外 | 把 `status.find_run` 換成會丟例外的假貨 | 同上 | 同上 | 自動：同上 |
| TC-052 | 同上（`sqlite3.Error`、`JobRefused`） | 例外 | 資料庫操作丟 `sqlite3.Error`，另一次丟 `JobRefused` | 同上 | 兩次都不丟出，回 `offered` 為假 | 自動：同上 |
| TC-053 | 作法 2「名額滿靜靜跳過」 | 例外 | A 的清理申請已達上限（confirm 的 `MAX_OPEN_CLEAN`） | 對另一個成功的 run 呼叫 `offer_cleanup` | 沒有建申請、不丟例外、回 `offered` 為假 | 自動：`test_a_full_clean_quota_is_skipped_silently` |
| TC-054 | 作法 2 步驟 1；作法 4 | 例外 | `platform_path` 指向不存在的資料庫，目錄是空的 | 呼叫 `offer_cleanup` | 不丟例外；目錄裡沒有出現任何新檔案（不建立資料庫） | 自動：`test_offer_makes_no_file_when_there_is_no_platform_database` |
| TC-055 | 專長守則（錯誤訊息與日誌） | 例外 | TC-038～TC-054 各種跳過 | 讀回傳的 `reason` | 每個 `reason` 是一句白話原因，不含堆疊、SQL、內部檔案路徑 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-055） |
| TC-056 | 不做：不動 AWS／Azure／K8s 類型 | 不在範圍 | run 的環境是只能「建模」不能跑的類型（非 Slurm、非 Google Batch） | 呼叫 `offer_cleanup` | 沒有建申請（環境不收 `clean_work`），不丟例外 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-056） |

## User Story 3 — 接收端收到 `complete` 才觸發，且不影響原本的回應（優先度 P1）

前置通用：假的 run 索引與 token，用 receiver 的測試夾具送 `complete`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-057 | 作法 4；裁決 1 | 功能 | A 的 run 有 token；hand-off 紀錄完整 | 送 `complete`，`workflow.success` 為真 | 回應 OK；恰好產生一張 `clean_work` 申請 | 自動：`test_complete_of_a_succeeded_run_makes_one_offer_and_the_response_and_token_end_are_unchanged` |
| TC-058 | 作法 4（回應與 token 一個位元都不變） | 功能 | 同上；另備一個把 offer 關掉的對照 | 兩邊各送同樣的 `complete` | 回應內容完全相同（`{"status": "OK"}`）、token 都已結束、run 的 `final_status` 等欄位寫入相同 | 自動：同上 |
| TC-059 | 裁示 16①；作法 3 | 不在範圍 | `workflow.success` 為假 | 送 `complete` | 回應 OK，沒有產生任何申請 | 自動：`test_complete_of_a_failed_run_makes_none` |
| TC-060 | 作法 4（offer 失敗不影響 run 紀錄） | 例外 | 把 `offer_cleanup` 換成會丟例外的假貨 | 送成功的 `complete` | 仍回 OK；run 的最終狀態與結束時間照常寫入；token 照常結束 | 自動：`test_complete_when_the_offer_fails_still_answers_ok_and_records_the_run` |
| TC-061 | 作法 4（`token new` 的 token） | 例外 | token 是用 `token new` 做的（沒有綁 run 名稱） | 送成功的 `complete` | 沒有產生申請 | 自動：`test_a_token_not_made_for_one_run_makes_no_offer` |
| TC-062 | 作法 4（`after_complete` 路徑） | 例外 | 已中止（aborted）的 run 再收到第二次 `complete` | 送第二次 | 回 OK；沒有第二次 offer，也沒有寫入任何東西 | 自動：`test_a_second_complete_of_an_aborted_run_makes_no_second_offer` |
| TC-063 | 作法 4（平台資料庫不存在） | 例外 | 平台資料庫檔案不存在；成功的 `complete` | 送 `complete` | 回應 OK；沒有建立 `platform.db` | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-063） |
| TC-064 | 作法 4（import 放函式內，避免循環匯入） | 功能 | 只載入 `receiver` 模組 | 檢查模組頂層與載入結果 | `receiver.py` 頂層仍只 import `agents, common, store`；`offer_cleanup` 的 import 在 `complete` 函式內；單獨載入 receiver 不會連帶載入 actions | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-064） |
| TC-065 | 裁決 1（觸發點不是網頁 GET） | 不在範圍 | A 的成功 run 沒有清理申請（沒有經過 `complete`） | A 開啟看板、單一 run 頁、確認頁各一次 | 沒有建立任何申請（GET 沒有寫入副作用） | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-065） |
| TC-066 | 不做：不補提過去已成功的 run | 不在範圍 | 一個在本功能上線之前就成功的 run，沒有再收到 `complete` | 等同「什麼都不觸發」：開看板、跑其他 run 的 `complete` | 這個舊 run 沒有被補提申請 | 自動：同上（註解標 TC-066） |
| TC-067 | 不做：逾時後不重提；裁決 4 | 不在範圍 | 一張清理申請已逾時（建立後撥過 7 天），該 run 的 `work_cleaned_at` 仍空 | 開看板、開確認頁、再對別的 run 送 `complete` | 沒有為這個 run 出現新的一張；舊的維持逾時 | 自動：同上（註解標 TC-067） |

## User Story 4 — 端到端：本人按了才刪，只刪 work（優先度 P1）

前置通用：假站台（`FakeSite(destructive_log=True)`，會記下每個破壞性指令）或假 bucket；用 c、d 片真正的代理程式碼；使用者 A 登入；run 資料夾裡另有 `results/`、`rawdata/`、`analysis/`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-068 | 目標；作法 5（畫面出現在 e 片的頁面上） | 功能 | Slurm run 成功並送過 `complete` | A 打開該申請的確認頁 `/c/<編號>` | 頁面顯示 ①②③ 三句白話與完整 work 路徑，有「確認刪除」按鈕 | 自動：`test_slurm_end_to_end_complete_offer_page_press_agent_deletes_then_the_record_says_cleaned_and_nothing_more_is_offered` |
| TC-069 | 憲法 6；維護者原話② | 功能 | 同上；A 還沒按 | 檢查假站台的破壞性指令記錄與 work 資料夾 | 破壞性指令記錄為空；`work/` 完整還在（沒按就什麼都不刪） | 自動：`test_nothing_is_deleted_until_the_person_presses` |
| TC-070 | 目標；維護者原話② | 功能 | 同上 | A 按「確認刪除」，代理執行 | `work/` 目錄消失 | 自動：Slurm 端到端測試（TC-068 同檔） |
| TC-071 | 維護者原話③；CLAUDE.md §3.4 | 功能 | 同上 | 按完之後逐檔比對 `results/`、`rawdata/`、`analysis/` 與 run 資料夾其他檔 | 這些位元級完全不變；唯一消失的是 `work/` | 自動：同上 |
| TC-072 | 作法 2、c 片記帳 | 功能 | 同上 | 讀 hand-off 紀錄 | `work_cleaned_at` 有值 | 自動：同上 |
| TC-073 | 作法 3（一次成功只提一次） | 功能 | 同上；已清完 | 對同一 run 再送 `complete` | 不會再出現新申請 | 自動：同上 |
| TC-074 | 作法 1（續跑） | 功能 | run `ampliseq-d5` 失敗後以 `-a2` 續跑成功 | `-a2` 送 `complete`，A 在確認頁按「確認刪除」 | 申請出現在 `ampliseq-d5-a2` 名下；按後 `/work/u1/abf/runs/ampliseq-d5/work`（原資料夾的 work）消失，原資料夾其他東西還在 | 自動：`test_slurm_end_to_end_resumed_attempt_cleans_the_origin_folder` |
| TC-075 | 憲法 6；維護者原話② | 功能 | Google Batch run 成功；假 bucket 內有 `runs/ampliseq-d5/work/…` 若干物件 | A 還沒按 | 假 bucket 的內容完全不變 | 自動：`test_nothing_is_deleted_until_the_person_presses` |
| TC-076 | 目標；d 片 | 功能 | 同上 | A 按「確認刪除」，代理執行 | `runs/ampliseq-d5/work/` 前綴下的物件全部消失 | 自動：`test_gcb_end_to_end_with_a_fake_bucket_deletes_only_the_run_prefix_and_keeps_work2_and_work_keep` |
| TC-077 | 作法 5 ④；手動項 3 的自動版 | 功能 | 假 bucket 裡另有同層的 `runs/ampliseq-d5/work2/x` 與 `runs/ampliseq-d5/work-keep` | 同上 | 這兩個物件還在（前綴不會撞名）；`results`、其他 run 的物件也不變 | 自動：同上 |
| TC-078 | 作法（代理拒絕或出錯） | 例外 | 代理回覆拒絕（例如結束碼 17）或出錯 | A 按「確認刪除」 | `work_cleaned_at` 仍是空；之後不會自動出現新的申請；沒有被刪的東西多於代理明說的 | 自動：`test_an_agent_refusal_or_error_leaves_work_cleaned_at_empty_and_makes_no_new_offer` |
| TC-079 | 維護者原話②；裁決 4 | 例外 | 清理申請已逾時（7 天） | A 試著按「確認刪除」 | 按不下去（頁面顯示已逾時），沒有任何東西被刪，沒有自動重提 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-079） |
| TC-080 | 專長守則（跨使用者，寫） | 例外 | A 的清理申請待按；B 登入 | B 用自己的身分對 A 的申請按「確認刪除」 | 被拒絕；沒有任何工作排進佇列；申請仍是 A 的待按 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-080） |
| TC-081 | 專長守則（跨使用者，讀） | 例外 | 同上 | B 打開 A 的申請頁 `/c/<編號>`，並看 B 自己的看板 | B 讀不到 A 的內容（與找不到申請一樣的回應）；B 的看板沒有 A 的 run 的通知 | 自動：同上（註解標 TC-081） |

## User Story 5 — 文件與手動驗收（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-082 | 範圍；作法 7（位置） | 功能 | `docs/PLATFORM.md` | 讀章節標題順序 | 有「Cleaning a finished run's work folder」小節，放在 `### Forget (keep-submissions)` 之後、`### Resume and relaunch` 之前 | 自動：`test_docs_say_what_is_deleted_what_is_not_and_keep_the_pinned_sentences` |
| TC-083 | 作法 7（何時、對誰） | 功能 | 同上 | 讀新小節 | 寫明：收到 `complete` 且成功才提；對 run 的擁有者提 | 自動：同上 |
| TC-084 | 作法 7（刪哪個、不刪什麼） | 功能 | 同上 | 讀新小節 | 寫明 Slurm＝`<run 資料夾>/work`；Google Batch＝bucket 裡 `…/runs/<run>/work/` 前綴；不刪 `results`、`rawdata`、`analysis` | 自動：同上 |
| TC-085 | 作法 7（為什麼代理刪、期限、不能續跑） | 功能 | 同上 | 讀新小節 | 寫明：平台不啟動程式所以由代理刪；申請 7 天有效、過期不重提；刪了之後這個 run 不能續跑 | 自動：同上 |
| TC-086 | 作法 7（連結模式、軟刪除） | 功能 | 同上 | 讀新小節 | 寫明：`publishDir` 用連結模式時代理會拒絕（結束碼 17）；Google Batch 刪的是 bucket 前綴且軟刪除的說明，與 d 片 ledger 一致，沒有「無法還原」 | 自動：同上 |
| TC-087 | 裁決 2；作法 7 | 功能 | 同上 | 讀新小節 | 寫明沒有擁有者的 run（例如純終端機送出）不支援，因為確認頁要登入的使用者才按得下去 | 自動：同上 |
| TC-088 | 作法 3、作法 7 | 功能 | 同上 | 讀新小節 | 寫明過去（本功能上線前）成功的 run 不會被提出申請 | 自動：同上 |
| TC-089 | 作法 7（更正第 8 行） | 功能 | `docs/PLATFORM.md` 開頭段落 | 讀第 8 行附近 | 原句 `It never deletes a run, a run folder or a result on the site` 已改為 `It never deletes a run folder or a result on the site; the only thing it can have deleted is the work folder of a finished run, and only after its owner's yes (see "Cleaning a finished run's work folder")`；後面「prunes finished job rows」等其他文字不變 | 自動：同上 |
| TC-090 | 作法 7（更正代理最初唯讀敘述，`### Start it` 之前） | 功能 | 同上 | 讀 `### Start it` 之前、說代理「不 launch、cancel、delete、move 或 write」的那段 | 該段不再把「現在的代理」描述成沒有任何刪除能力，並指向新小節（若判斷它只在講最初唯讀版本，也要寫明是最初版本） | 自動：同上 |
| TC-091 | 作法 7、「必須更新的既有斷言」 | 功能 | 文件改完 | 跑 `test_gcb_launch.py`、`test_gcb_ce.py`、`test_actions_layer.py`、`test_failures.py`、`test_catalogue.py` 中讀文件的測試 | 全綠；被釘住的字串（如 "Slurm-like confirmed launch and cancel on the platform host (resume: not yet)"、"Slurm and Google Batch can run; the other types can be modelled only"）仍在；「Action layer」小節仍 &lt; 30 行；沒有改任何既有測試 | 自動：既有測試 |
| TC-092 | 作法 7（範例路徑） | 功能 | 新小節與 TESTING.md 新小節 | 掃範例路徑 | 範例路徑只用 `/work/u1/abf`、`gs://lab-bucket/work`、`ampliseq-d5`，沒有真實站台路徑、帳號 | 自動：`test_docs_say_what_is_deleted_what_is_not_and_keep_the_pinned_sentences` |
| TC-093 | 完成標準（文件） | 功能 | `docs/TESTING.md` | 讀 | 有「cloud-cleanup」小節，寫明手動驗收 1、2、3、4、5 共五項（以「完成標準」為準，不是 1–4） | 自動：同上 |
| TC-094 | 作法 7（更正第 158 行） | 功能 | `docs/TESTING.md` | 讀第 158 行附近 | `(rm is not a job kind, and no job kind writes.)` 已改為 `(Only a finished run's work folder can be deleted, and only after its owner's yes; see cloud-cleanup.)` | 自動：同上 |
| TC-095 | 範圍（動手前再搜一次三句被更正的話）；完成標準 | 功能 | `specs/cloud-cleanup-f/ledger.md` | 驗收時讀 ledger | 有 `git diff --stat`；有用 `never deletes`、`delete, move`、`no job kind` 搜過 `platform/tests/`、`tests/`、`docs/` 的結果，有命中的列進說明 | 手動：verifier 驗收時核對 ledger |
| TC-096 | 完成標準·手動 1 | 功能 | 維護者自己的 nano4 測試 run（很小、成功）；用產品確認頁去刪，不用 AI session 對叢集下刪除指令 | 看板右欄出現「可以清掉中間檔」通知 → 點進 `/c/<rid>` → 確認畫面有 ①②③ 三句 → 先不按，用 `list_site_files` 看 `…/runs/<run>/work` 還在 → 再按「確認刪除」 | 按之前 work 還在；按之後只有 `work` 消失，`results/` 完整 | 手動：`docs/TESTING.md`「cloud-cleanup」手動 1 |
| TC-097 | 完成標準·手動 2；裁決 5 | 功能 | 同上 | 看 Nextflow 日誌開頭的 `work-dir`（或 `.nextflow.log`） | 它真的是 `<run folder>/work`；不是的話停手回報（表示站台設定改了 workDir，公式要改） | 手動：同上，手動 2 |
| TC-098 | 完成標準·手動 3 | 功能 | 維護者自己帳號的 Google Batch run；先手動放 `…/runs/<run>/work2/x` 與 `…/runs/<run>/work-keep` | 按「確認刪除」 | bucket 裡 `…/runs/<run>/work/` 消失；`work2/x` 與 `work-keep` 沒被刪（驗證前綴不撞名；這是 `gcloud storage rm --recursive` 對尾端斜線行為的第一次實測） | 手動：同上，手動 3 |
| TC-099 | 完成標準·手動 3（回填） | 功能 | 同上 | 記下 bucket 有沒有軟刪除／版本控制、刪掉的物件之後是否仍能列出 | 結果回填 d 片 ledger，並用來確認本片畫面第 ④ 句寫得如實 | 手動：同上，手動 3 |
| TC-100 | 完成標準·手動 4 | 功能 | nano4 讓一個 run 失敗、續跑（`-a2`）成功 | 看通知 → 按「確認刪除」 | 通知出現在 `-a2` 那個 run；按後原資料夾的 `work` 消失 | 手動：同上，手動 4 |
| TC-101 | 完成標準·手動 5 | 功能 | 自己的測試庫；一張清理申請把 `expires_at` 改到過去 | 開確認頁、看看板，再等一陣子 | 確認頁顯示「已逾時（7 天）」；看板沒有通知；之後也沒有新的一張出現 | 手動：同上，手動 5 |
| TC-102 | 裁示 14；裁決 7；完成標準（截圖） | 功能 | 合併前 | 附確認頁（含 `clean_screen` 文字）與看板卡片的截圖，zh、en 各一，列進每日清單 | 截圖已附；維護者回「好」或「不好」 | 手動：`docs/TESTING.md`「cloud-cleanup」 |

## 憲法與安全網

涉及：憲法原則 2（平台不啟動程式，TC-071／TC-061）、憲法 6／ADR 0006（每個寫入要本人答應）、TC-070（新檔 `# Nothing existing:` 檔首）、專長守則（backend）的對等性、擁有者、錯誤訊息、migration。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-103 | 憲法 6／ADR 0006；專長守則（確認管道） | 例外 | 一張清理申請處於待按、逾時、作廢三種狀態之一；沒有本人的確認 | 嘗試為它（或不帶確認）排入一個 `clean_work` 工作 | 平台拒絕；沒有工作被排入；沒有任何檔案被動 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-103） |
| TC-104 | 作法 2；範圍與憲法 | 功能 | 掃 `abf_platform/`、`abf_launch/` 全部原始碼 | 找 `create_pending(` 且帶 `"clean_work"` 的呼叫 | 只在 `actions/__init__.py` 一處（`offer_cleanup`） | 自動：`test_the_only_place_that_creates_a_clean_work_request_is_offer_cleanup` |
| TC-105 | 不做：不新增 MCP 工具 | 不在範圍 | 取 MCP 工具清單 | 數 | 仍是 12 個，名稱不變；`offer_cleanup` 不是工具、也不是 `request_*` | 自動：`test_no_new_mcp_tool_no_new_route_no_new_cli_command` |
| TC-106 | 不做：不新增網頁路由 | 不在範圍 | 取路由清單 | 比對 | 與改動前完全相同 | 自動：同上 |
| TC-107 | 不做：不新增終端機指令 | 不在範圍 | 跑 `abf-platform --help` | 比對子指令清單 | 與改動前完全相同（沒有 `clean-work` 之類） | 自動：同上 |
| TC-108 | 專長守則（對等性） | 功能 | 列舉使用者可見動作（MCP 工具、網頁路由、CLI 子指令）與動作層函式兩邊 | 兩邊一一對應 | 既有對等性測試（`test_actions_layer.py`）原樣綠；新增的 `offer_cleanup` 是系統在 `complete` 時呼叫的，兩邊清單都不出現，且沒有任何使用者動作繞過動作層自己建 `clean_work` 申請 | 自動：既有 `test_actions_layer.py`＋`test_cleanup_offer.py`（註解標 TC-108） |
| TC-109 | 憲法原則 2；TC-071；TC-061 | 功能 | 掃 `abf_platform/` 與 `abf_launch/` 原始碼（不靠拆字） | 找啟動程式的用法、`rm -`、`storage rm`、`rmtree`，以及 TC-061 的禁用字 | 全部沒有 | 自動：`test_platform_and_launch_sources_have_no_program_start_no_rm_and_not_the_forbidden_word` |
| TC-110 | 憲法原則 2 | 功能 | `test_scope.py` TC-071、TC-061 | 跑 | 原樣綠；沒有修改這兩條測試 | 自動：既有 `test_scope.py` |
| TC-111 | TC-070 | 功能 | 新檔 `platform/tests/test_cleanup_offer.py` | 讀檔首 40 行 | 含 `# Nothing existing: …` | 自動：既有 TC-070 掃描 |
| TC-112 | 維護者原話②；不做：不自動刪 | 不在範圍 | 掃原始碼與設定 | 找排程、常駐迴圈、執行緒、計時器、「N 天後自動」、POLICY 通道上的 `clean_work` | 都沒有；本片沒有新增 worker；刪除只有本人按確認這一條路 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-112） |
| TC-113 | 完成標準；範圍 | 功能 | 實作完成 | `git diff --name-only` 對 base | 只有「範圍：檔案」所列 7 個（`build.py`、`actions/__init__.py`、`receiver.py`、`PLATFORM.md`、`TESTING.md`、`test_cleanup_offer.py`、`ledger.md`）；禁碰清單（`store.py`、`confirm.py`、`jobs.py`、`web.py`、`web_board.py`、`abf_station/*`、`cli.py`…）一個都沒動；`spec`／`test-case*.md` 沒被改 | 手動：verifier 驗收時以 git diff 核對 |
| TC-114 | 專長守則（migration）；作法 6 | 功能 | 一個 a 片之後建好的 platform.db（已有 `work_cleaned_at` 欄）；`store.py` 未改 | 對它呼叫 `offer_cleanup` 前後比對資料表結構 | 不需要 migration：結構（`PRAGMA table_info`、CHECK）前後完全相同，只多一筆 `confirmations` 資料 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-114） |
| TC-115 | 完成標準（Slurm 位元級不變） | 功能 | 既有 Slurm 送出內容包、畫面、`head.sh` 與 golden 檔 | 跑既有 golden 與送出／取消／續跑測試 | 全綠且 golden 檔沒有被改（位元級不變） | 自動：既有測試；`git diff` 確認 golden 未動 |
| TC-116 | 專長守則（路由處理函式不得有第二份邏輯） | 功能 | 讀 `receiver.complete` | 檢查新增內容 | 只有「成功且有 run 名稱才呼叫 `actions.offer_cleanup`」並包 `try/except`；擁有者判斷、狀態判斷、建申請全在動作層，不在 receiver 裡再寫一份 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-116） |
| TC-117 | 專長守則（錯誤訊息與日誌不洩密） | 例外 | 提出申請的過程與各種跳過情形；內容包的 `ce` 快照 | 讀內容包、畫面文字、`reason`、日誌輸出 | 不含 token、密碼、金鑰、憑證檔內容 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-117） |
| TC-118 | 不做：總表 C-7 後半 | 不在範圍 | 一個 run 的結果已超過 30 天（或快到期） | 開看板、費用頁 | 沒有任何「結果到期前 7 天」的 Decision-needed 通知；費用頁沒有新增儲存月費；`cloud_cost.py`、`web_board.py` 沒被改 | 自動：`test_cleanup_offer.py`（executor 命名，註解標 TC-118）；檔案未動由 TC-113 核對 |
| TC-119 | 不做：不刪 work 以外、不做「刪整個 run」「刪結果」選項或旗標 | 不在範圍 | 讀內容包鍵、畫面與確認頁 | 找任何可選擇範圍的欄位、旗標、按鈕 | 沒有；內容包只有那七個鍵；`.nextflow*`、`head.sh`、run 資料夾本身都不在刪除範圍 | 自動：同上（註解標 TC-119） |
| TC-120 | 不做：批次清、部分清、`nextflow clean` | 不在範圍 | 一次有多個成功的 run | 提出申請 | 一張申請只對應一個 run、一個 work 路徑；沒有「一次清多個」「只清某幾個 task 目錄」；原始碼沒有 `nextflow clean` | 自動：同上（註解標 TC-120） |
| TC-121 | 不做：不寫第二條寫入路徑 | 不在範圍 | 掃原始碼 | 找 `gcloud batch jobs delete` 或任何取消 Batch 工作的新寫入 | 沒有 | 自動：同上（註解標 TC-121） |
| TC-122 | 不做：不改送出、取消、續跑行為 | 不在範圍 | Slurm 與 Google Batch 既有測試 | 跑 | 全綠，沒有為了讓它們過而改動既有斷言 | 自動：既有測試 |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
