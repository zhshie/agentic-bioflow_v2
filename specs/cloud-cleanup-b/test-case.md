# 測試案例：平台認得「清理 work」這種申請與工作（cloud-cleanup-b）

**規格**：`specs/cloud-cleanup-b/plan.md`（本功能沒有 spec.md，以 plan.md 的目標、作法與「維護者原話」為準）　**總覽**：`test-case-overview.md`

白話名詞：「申請（pending）」＝平台先記下「想刪某個 run 的 work 目錄」這張待確認的單子，本身不會刪任何東西。「確認」＝申請者本人在確認頁按送出（`PAGE` 通道，經 `confirm.approve`）。「工作（job）」＝確認後排進佇列、等代理去做的事。「work 目錄」＝Nextflow 放中間檔的 `work/`，不是結果。「代理」＝跑在使用者那邊、替平台碰叢集或雲端的小程式。「hand-off 紀錄」＝平台 `launches` 表，記每個 run 送出去的資料夾與 Slurm／主控程序編號。「內容包」＝申請裡存的那包資料（bundle），`clean_work` 的內容包鍵恰為 `version`、`run_name`、`slurm_job_id`、`run_folder`、`agent`、`ce`、`work`。

本片沒有任何程式會建立 `clean_work` 申請，也沒有網頁畫面；以下所有申請都是測試手工建立，只在 `abf_platform` 層做，不走網頁。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

維護者原話對照（逐字）：
- 「跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪」→ TC-006、TC-007、TC-066（沒有本人按送出就沒有工作；沒有任何自動路徑）。
- 「C-7 `cloud-cleanup`（B／backend）：succeeded 後建『刪除 work 目錄』的待確認請求（走 `_ask`，新 kind `clean_work`；對 nano4 也適用）」→ TC-001、TC-036、TC-039（種類名恰為 `clean_work`；Slurm 與 Google Batch 兩種環境都排得進）。
- 「直接 `scancel`，以及刪改叢集端 `rawdata`／`results`／`analysis`，一律擋住」→ TC-045、TC-046、TC-048、TC-049（內容包必須與 hand-off 紀錄一致，否則不排工作）。
- 「網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」→ TC-074、TC-072（本片無網頁畫面、沒有碰禁碰的檔）。
- 「平台不啟動程式」（TC-071、TC-061）→ TC-068、TC-076、TC-077。
- 「每個寫入要本人答應」→ TC-006、TC-034、TC-075。

## User Story 1 — 申請本身不是確認，只有本人按送出才排進佇列（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法：種類名恰為 `clean_work`；原話 C-7 | 功能 | 平台已載入 | 查看確認種類對照表 `confirm.JOB_KIND` | 含 `clean_work` 對應到工作種類 `clean_work`；原有的 `launch`→`launch_nextflow`、`cancel`→`cancel_run` 一字不變 | 自動：`platform/tests/test_cleanup_confirm.py` |
| TC-002 | 作法 1：申請 7 天有效 | 功能 | 一位使用者、一份合格的 `clean_work` 內容包 | 用 `create_pending` 建立一張 `clean_work` 申請 | 該申請的到期時間減建立時間恰為 604800 秒（7 天） | 自動 |
| TC-003 | 作法 1：其餘照舊 | 功能 | 同上，但種類為 `launch` 與 `cancel` | 各建立一張申請 | 到期時間減建立時間恰為 600 秒（10 分鐘），與以前相同 | 自動 |
| TC-004 | 作法 1：同人同內容回既有那張 | 功能 | 某人已有一張尚有效（剩餘時間超過 60 秒）的 `clean_work` 申請 | 同一個人對完全相同的內容再申請一次 | 回的是同一張申請編號，沒有多一張 | 自動 |
| TC-005 | 作法 1：另一個人不共用 | 功能 | 甲已有一張申請 | 乙對完全相同的內容申請 | 乙得到另一張不同編號的申請，甲的那張不變 | 自動 |
| TC-006 | 原話 16：沒有本人按送出就沒有工作；「每個寫入要本人答應」 | 例外 | 已建立一張 pending 的 `clean_work` 申請，尚未按送出 | 查看工作表列數與該申請狀態 | 工作表列數與建立前相同（沒有任何 `clean_work` 工作）；申請仍是 pending | 自動 |
| TC-007 | 作法 2、原話 16 | 功能 | 一個有 hand-off 紀錄（含 Slurm 編號、擁有者是甲）的 run；甲有一張內容與紀錄一致的 pending 申請 | 甲透過 `PAGE` 通道呼叫 `confirm.approve` | 恰好排進一個 `clean_work` 工作，工作帶著這張申請的確認編號；申請變成 confirmed、通道記為 `PAGE` | 自動 |
| TC-008 | 作法：一張確認只能用一次 | 例外 | 同 TC-007，已按過送出 | 甲再按一次送出 | 回「已送出」(`already`)，並指出既有那個工作；工作表仍只有一個 `clean_work` 工作 | 自動 |
| TC-009 | 專長守則：跨使用者寫入被拒 | 例外 | 甲的 pending 申請 | 乙（另一位使用者）對甲的申請呼叫 `approve` | 被拒（`not_yours`，「不是你的申請」）；沒有排任何工作；申請仍是 pending | 自動 |
| TC-010 | 專長守則：跨使用者讀取被拒 | 例外 | 甲有一張 pending 申請 | 用乙的身分呼叫 `open_clean_requests`；並讀 `describe` | 乙得到的結果不含甲的 run；`describe` 回傳的 `caller_user_id` 是甲（網頁靠它擋乙） | 自動 |
| TC-011 | 作法：逾時不能按 | 例外 | 一張 pending 申請 | 時鐘撥過 7 天後甲呼叫 `approve` | 回「已逾時」(`expired`)，沒有排任何工作，申請變 void | 自動 |
| TC-012 | 作法：作廢的不能按 | 例外 | 一張已被作廢（void）的申請 | 甲呼叫 `approve` | 回「作廢」(`void`)，沒有排任何工作 | 自動 |
| TC-013 | 計畫測試：被刪除（forgotten）的不能按 | 例外 | 一張 pending 的 `clean_work` 申請，其 run 已被擁有者執行 `forget_content` | 甲呼叫 `approve` | 被拒（申請已作廢），沒有排任何工作 | 自動 |
| TC-014 | 作法：憑證種類要對 | 例外 | 一張已確認的 `clean_work` 憑證（種類 `clean_work`） | 拿它去排 `launch_nextflow` 工作與 `cancel_run` 工作（兩個各試一次） | 兩次都被拒，訊息說「憑證種類不符」；沒有排任何工作 | 自動 |
| TC-015 | 作法：反方向也不行 | 例外 | 一張已確認的 `launch` 憑證與一張已確認的 `cancel` 憑證 | 各拿去排 `clean_work` 工作 | 兩次都被拒，「憑證種類不符」；沒有排任何工作 | 自動 |
| TC-016 | 作法 `facts()` | 功能 | 一張未被刪除的 pending `clean_work` 申請 | 呼叫 `confirm.facts` | 回傳恰好 `what`＝`clean_work`、`run_name`、`work` 三項（`work` 取自內容包），不含其他欄位 | 自動 |
| TC-017 | 作法 `facts()` | 例外 | 一張內容已被 forget 的 `clean_work` 申請 | 呼叫 `confirm.facts` | 回 None | 自動 |
| TC-018 | 作法：`open_clean_requests` | 功能 | 甲有兩個不同 run 的 pending、未逾時、內容還在的 `clean_work` 申請 | 呼叫 `open_clean_requests`（甲） | 回 `{run_name: 申請編號}`，恰好這兩筆 | 自動 |
| TC-019 | 同上：他人的不出現 | 例外 | 乙也有自己的 pending 申請 | 甲呼叫 `open_clean_requests` | 結果不含乙的 run | 自動 |
| TC-020 | 同上：逾時的不出現 | 例外 | 甲有一張已過 7 天的 pending 申請 | 甲呼叫 `open_clean_requests` | 結果不含它 | 自動 |
| TC-021 | 同上：非 pending 或沒內容的不出現 | 例外 | 甲各有一張 void、confirmed、被 forget 的 `clean_work` 申請 | 甲呼叫 `open_clean_requests` | 三張都不出現 | 自動 |
| TC-022 | 作法 6：forget 對稱 | 功能 | 一個 run 有 pending 的 `clean_work` 申請，也有一個已完成的 `clean_work` 工作；另一個 run 也有同樣的東西 | 擁有者對第一個 run 執行 `forget_content` | 該 run 的 `clean_work` 申請變 void 且內容清空，工作的內容只剩 run 名稱；不報錯（含 launch／cancel 的 forget 仍正常）；另一個 run 的資料完全不動 | 自動 |
| TC-023 | 作法 6：有工作排隊時拒絕 forget | 例外 | 該 run 有一個 queued（或 claimed）的 `clean_work` 工作 | 擁有者執行 `forget_content` | 被拒（「還有工作在排隊或進行中」），沒有任何內容被清掉 | 自動 |

## User Story 2 — 申請的名額（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | 作法 1：`clean_work` 不佔那 10 張 | 功能 | 甲已有 10 張不同的 pending `launch`／`cancel` 申請 | 甲再建立一張 `clean_work` 申請 | 成功收下，不受那 10 張的上限擋 | 自動 |
| TC-025 | 作法 1：反過來也不被擋 | 功能 | 甲已有 12 張不同 run 的 pending `clean_work` 申請 | 甲建立 10 張 `launch` 申請 | 10 張都成功；第 11 張 `launch` 仍被既有上限擋（既有 10 張的規矩沒變） | 自動 |
| TC-026 | 作法 1：上限 50，白話提示 | 例外 | 甲已有 50 張未逾時、不同 run 的 pending `clean_work` 申請 | 甲再建立第 51 張 | 被拒（`JobRefused`），訊息為白話中文，說明已有 50 個等待中的清理提醒，請先處理或等它們逾時；不含堆疊、SQL 或內部路徑 | 自動 |
| TC-027 | 作法 1：上限邊界 | 功能 | 甲已有 49 張 pending `clean_work` 申請 | 甲建立第 50 張 | 成功收下 | 自動 |
| TC-028 | 作法 1：上限只算未逾時的 | 功能 | 甲的 50 張 `clean_work` 申請都已過 7 天 | 甲建立新的 `clean_work` 申請 | 成功收下（逾時的不佔名額） | 自動 |
| TC-029 | 作法 1：上限是每個人各自的 | 功能 | 甲已有 50 張 pending `clean_work` 申請 | 乙建立一張 `clean_work` 申請 | 成功收下 | 自動 |

## User Story 3 — 佇列只放行有確認、且與紀錄一致的 `clean_work`（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 作法：期限 600 秒 | 功能 | 沒有設定環境變數 | 查 `jobs.DEADLINE_SECONDS["clean_work"]` 與 `jobs.deadline_seconds("clean_work")` | 兩者都是 600 | 自動 |
| TC-031 | 作法：環境變數可覆蓋 | 功能 | 設 `ABF_PLATFORM_DEADLINE_CLEAN` 為有效數字（例如 900） | 查 `jobs.deadline_seconds("clean_work")` | 回 900 | 自動 |
| TC-032 | 作法：壞值退回預設 | 例外 | 把 `ABF_PLATFORM_DEADLINE_CLEAN` 分別設成非數字、`0`、負數 | 查 `jobs.deadline_seconds("clean_work")` | 三種都回 600，不報錯 | 自動 |
| TC-033 | 作法：種類七種 | 功能 | 平台已載入 | 查 `jobs.KINDS` 與 `jobs.CONFIRMED` | `KINDS` 共七種，`clean_work` 排最後，前六種順序不變；`CONFIRMED` 含 `clean_work`→`clean_work`，原兩筆不變 | 自動 |
| TC-034 | 原話：每個寫入要本人答應 | 例外 | 一份內容包 | 呼叫 `enqueue_confirmed` 排 `clean_work`，確認編號給 None、給空字串、給不存在的編號（三種） | 都被拒（「沒有確認憑證／查無此確認憑證」）；沒有排任何工作 | 自動 |
| TC-035 | 作法：資料庫那道鎖 | 例外 | 直接對資料庫寫一列 `kind='clean_work'` 且沒有確認編號的工作 | 執行 INSERT | 資料庫拒絕（約束失敗），沒有寫進去 | 自動 |
| TC-036 | 作法 3、原話 C-7（nano4）：Slurm 環境 | 功能 | 一個 Slurm 環境，狀態分別為 available 與 invalid（環境之後壞了），代理在線，其他都合格 | 各排一次 `clean_work` | 兩種狀態都排進去（`clean_work` 不要求環境 available） | 自動 |
| TC-037 | 作法 3：Slurm 既有擋法不變 | 例外 | Slurm 環境狀態為 disabled、unsupported（各一次） | 各排一次 `clean_work` | 都被拒，訊息說明該環境已停用／不支援；沒有排工作 | 自動 |
| TC-038 | 作法 3：代理離線 | 例外 | 環境的代理已離線 | 排 `clean_work` | 被拒，訊息為白話，說代理離線、沒有排進任何工作 | 自動 |
| TC-039 | 作法 3、原話 C-7：Google Batch 環境 | 功能 | 一個 Google Batch 環境，狀態為 available、invalid、creating（各一次），代理在線 | 各排一次 `clean_work` | 三種都排進去 | 自動 |
| TC-040 | 作法 3：Google Batch 仍擋停用／不支援 | 例外 | Google Batch 環境狀態為 unsupported、disabled | 排 `clean_work` | 都被拒；沒有排工作 | 自動 |
| TC-041 | 作法 3：Google Batch 放行清單只加一種 | 例外 | 一個 Google Batch 環境 | 排 `list_site_files`、`fetch_run_records`、`read_task_log`（三種各一次） | 三種都像以前一樣被拒（「尚未支援」） | 自動 |
| TC-042 | 作法 2：要有 hand-off 紀錄 | 例外 | 有一張已確認的 `clean_work` 憑證，但該 run 在 hand-off 紀錄裡沒有任何一列 | 排工作 | 被拒，白話說 run 沒有 Slurm 編號的紀錄（不是平台送出的）；沒有排工作 | 自動 |
| TC-043 | 作法 2：要有編號 | 例外 | hand-off 紀錄有這個 run 但 `slurm_job_id` 為空 | 排工作 | 被拒，同上；沒有排工作 | 自動 |
| TC-044 | 作法 2：擁有者規則 | 例外 | run 是甲送出的，確認憑證是乙的 | 乙排工作 | 被拒，說法與「找不到這個 run」相同（不透露它存在）；沒有排工作 | 自動 |
| TC-045 | 作法 2 ①、原話「一律擋住」 | 例外 | 內容包的 `run_folder` 與 hand-off 紀錄的 `run_folder` 差一個字 | 排工作 | 被拒（白話）；沒有排工作 | 自動 |
| TC-046 | 作法 2 ② | 例外 | 內容包的 `slurm_job_id` 與紀錄不同 | 排工作 | 被拒（白話）；沒有排工作 | 自動 |
| TC-047 | 作法 2 ③ | 例外 | 紀錄的 `work_cleaned_at` 已有時間 | 排工作 | 被拒，白話說「已經清過了」；沒有排工作 | 自動 |
| TC-048 | 作法 2 ④：多一個鍵 | 例外 | 內容包比規定多一個鍵（例如多一個 `paths`） | 排工作 | 被拒；沒有排工作 | 自動 |
| TC-049 | 作法 2 ④：少一個鍵 | 例外 | 內容包缺一個必要鍵（例如沒有 `work`） | 排工作 | 被拒；沒有排工作 | 自動 |
| TC-050 | 作法 2：既有的代理核對 | 例外 | 內容包的 `agent` 不是該環境的代理 | 排工作 | 被拒，訊息說明內容包是給哪個代理、環境的代理是誰；沒有排工作 | 自動 |

## User Story 4 — 代理的答覆怎麼清洗、怎麼記帳（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-051 | 作法 4：只留該留的鍵 | 功能 | 一個 `clean_work` 工作，代理答覆夾帶 `slurm_job_id`、`path`、`left_on_site`、`entries` 等多餘的鍵 | 呼叫 `jobs.clean_result("clean_work", …)` | 結果含 `ok`、`message`、`run_name`、`cleaned`；夾帶的那些多餘鍵一個都不在 | 自動 |
| TC-052 | 作法 4：`cleaned` | 功能 | 答覆 `cleaned` 為真正的布林 `True` | 清洗 | 結果的 `cleaned` 是 `True` | 自動 |
| TC-053 | 作法 4：只有真正的 True 才算 | 例外 | 答覆的 `cleaned` 分別為 `1`、`"true"`、`"yes"`、`False`、完全沒有這個鍵 | 各清洗一次 | 五種結果的 `cleaned` 都是 `False` | 自動 |
| TC-054 | 作法 4：文字有上限 | 功能 | 答覆的 `message` 長 5000 字、`run_name` 長 200 字 | 清洗 | `message` 不超過 2000 字、`run_name` 不超過 64 字 | 自動 |
| TC-055 | 作法 5：只寫對的那一列 | 功能 | 同一個 run 名在 hand-off 紀錄有兩列（不同 Slurm 編號），另有別的 run | 代理答覆 `done`、`ok`＝True、`cleaned`＝True | 只有「run 名與 Slurm 編號都與該工作內容包相同」的那一列的 `work_cleaned_at` 有時間；同名另一列與別的 run 都不動 | 自動 |
| TC-056 | 作法 5、裁決 4 | 例外 | 同上 | 代理答覆 `refused` | `work_cleaned_at` 沒有寫 | 自動 |
| TC-057 | 作法 5、裁決 4 | 例外 | 同上 | 代理答覆 `error` | `work_cleaned_at` 沒有寫 | 自動 |
| TC-058 | 作法 5 | 例外 | 同上 | 代理答覆 `done` 但 `ok` 為假（即使 `cleaned` 是 True） | `work_cleaned_at` 沒有寫 | 自動 |
| TC-059 | 作法 5 | 例外 | 同上 | 代理答覆 `done`、`ok` 為真但 `cleaned` 是 False（或缺） | `work_cleaned_at` 沒有寫 | 自動 |
| TC-060 | 作法 5、裁決 4：不自動重試 | 例外 | 一個答覆為 `refused`、`error` 或 `cleaned` 為 False 的 `clean_work` 工作 | 答覆之後查工作表 | 沒有出現任何新的 `clean_work` 工作 | 自動 |
| TC-061 | 作法 5：遲到的答覆照樣記 | 功能 | 一個 `clean_work` 工作已過期（expired），代理才送來 `done`、`ok`、`cleaned`＝True | 收下答覆 | 工作仍標為 expired、答覆放進遲到欄；`work_cleaned_at` 照樣寫上 | 自動 |
| TC-062 | 作法 5：被 forget 的工作 | 例外 | 一個 `clean_work` 工作的內容已被擁有者刪除（args 只剩 run 名），代理送來 `done`、`ok`、`cleaned`＝True | 收下答覆 | 不報錯、答覆被收下；hand-off 紀錄沒有任何一列被寫 | 自動 |
| TC-063 | 作法 5：端到端 | 功能 | 一張已按送出的 `clean_work` 申請，工作 queued | 代理 claim 該工作、再用 `take_result` 答覆 `done`、`ok`、`cleaned`＝True | claim 時帶著確認憑證並把憑證標為已用；答覆被收下、工作 `result` 保留 `cleaned: true`；hand-off 紀錄該列有 `work_cleaned_at` | 自動 |
| TC-064 | 作法 5：run_name 與編號取自工作自己的內容包 | 例外 | 代理的答覆內寫了別的 `run_name` 與別的 `slurm_job_id` | 收下答覆 | 被寫的仍是該工作自己內容包裡的那個 run 與編號；答覆裡指的另一個 run 完全不動 | 自動 |

## User Story 5 — 不在範圍（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-065 | 不做：不建立任何 `clean_work` 申請（建立在 f 片） | 不在範圍 | 一個 launch 工作跑到 `done` 並記了 Slurm 編號的完整流程 | 跑完整個流程後查確認表與工作表 | 沒有任何 `clean_work` 申請，也沒有任何 `clean_work` 工作 | 自動 |
| TC-066 | 原話 16：沒有任何自動路徑 | 不在範圍 | 一張 pending 的 `clean_work` 申請、一個合格的 hand-off 紀錄 | 把時鐘撥到 30 天後，並做平台所有會被呼叫的維護動作（建立其他申請、claim、清理過期列） | 申請沒有自己變成 confirmed，沒有出現任何 `clean_work` 工作 | 自動 |
| TC-067 | 不做：不新增 MCP 工具、`actions` 函式、網頁路由、`enqueue_clean` | 不在範圍 | 平台已載入 | 數 MCP 工具、列 `actions` 公開名稱、列網頁路由、查 `jobs` 有無 `enqueue_clean` | MCP 工具仍是 12 個；`actions` 的公開名稱集合與本片之前相同；網頁路由集合不變；`jobs` 沒有 `enqueue_clean` | 自動 |
| TC-068 | 不做：不新增 worker／執行緒／常駐迴圈／排程 | 不在範圍 | 平台套件原始碼 | 掃 `abf_platform/` 與 `abf_launch/` | 沒有 `threading`、`Thread(`、`sched`、`cron`、`while True`、`asyncio.create_task` 等新增；既有 `test_scope.py` TC-071 的掃描仍通過 | 自動 |
| TC-069 | 不做：不改 launch、cancel 的任何行為、期限或文字 | 不在範圍 | 平台已載入 | 查 launch／cancel 的期限與申請有效期；跑 launch 與 cancel 的既有測試 | launch 期限仍 300、cancel 仍 90、兩者申請仍 10 分鐘；launch 與 cancel 的既有測試一個都沒有被改過、全部通過 | 自動：`platform/tests/test_cleanup_confirm.py` 與既有 launch／cancel 測試 |
| TC-070 | 不做：不做批次清、部分清 | 不在範圍 | 內容包夾帶多個目錄（例如 `works` 清單，或 `work` 之外的 `paths` 鍵） | 排工作 | 被拒，不會只清其中一部分；沒有排工作 | 自動 |
| TC-071 | 不做：不做失敗／中止／失聯 run 的清理；平台不讀 run 狀態 | 不在範圍 | `confirm.py`、`jobs.py` 原始碼 | 查有沒有讀 `final_status` | 兩個檔裡沒有以 `final_status` 決定 `clean_work` 的程式（排工作只看 hand-off 紀錄） | 自動 |
| TC-072 | 禁碰清單：只准改計畫列的 7 個檔 | 不在範圍 | 實作完成的分支 | 驗收者以 `git diff --name-only <base>...HEAD` 核對 | 變更檔只有 `confirm.py`、`jobs.py`、`test_cleanup_confirm.py`、三處既有測試（`test_resume_scope.py`、`test_keep_submissions.py`、`test_launch_platform.py`）與 `ledger.md`；`store.py`、`cli.py`（platform 與 abf_launch）、`receiver.py`、`records.py`、`cloud_cost.py`、`compute_envs.py`、`mcp_server.py`、`guidance.py`、`actions/`、`build.py`、`web*.py`、`abf_station/*` 都沒有出現 | 手動：驗收閱卷以 `git diff` 核對（本片無使用者操作，不新增 `docs/TESTING.md` 步驟） |
| TC-073 | 作法 8：不需要 migration | 不在範圍 | 實作完成的分支 | 驗收者核對 `git diff` 與 `store.py` | `store.py` 沒有任何變動；沒有新增 migration 或資料結構變更 | 手動：同上 |
| TC-074 | 不做：不改確認頁與看板；網頁沒有畫面變化 | 不在範圍 | 實作完成的分支 | 驗收者核對 `git diff` 的 `web*.py` 與 `docs/` | `web*.py` 與 `docs/` 沒有任何變動 | 手動：同上 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-075 | 原則 I.2／安全網：每個寫入要本人答應，寫入工具要有自己的拒絕測試 | 例外 | 一份合格的內容包與 hand-off 紀錄，但憑證分別是：仍 pending 的、void 的、已用過的、內容雜湊對不上的（四種） | 各排一次 `clean_work` | 四種都被拒；沒有排任何工作 | 自動 |
| TC-076 | 原則 2：平台不啟動程式、不刪檔 | 例外 | `abf_platform/` 與 `abf_launch/` 全部原始碼 | 掃描 | 不含 `rm -`、`storage rm`、`rmtree`、`subprocess`，也不含 TC-061 禁用字；掃描本身不拆字、也不禁 `gcloud` 這個字（`cloud_store.py` 有 `gcloud storage cp` 的提示文字） | 自動 |
| TC-077 | 原則 2：既有範圍掃描 | 功能 | `test_scope.py` 未被修改 | 執行 TC-071 與 TC-061 的掃描 | 通過 | 自動：`platform/tests/test_scope.py` |
| TC-078 | 憲法 5.0.0：三條通道、確認管道不變 | 功能 | 更新後的既有測試 | 執行 `test_resume_scope.py` 的三通道測試與 `test_keep_submissions.py` 的 TC-083 測試 | 通道仍恰為 `TERMINAL`／`ELICITED`／`PAGE`；`confirm.approve` 的原始碼仍不含 `forget`；兩個測試除加入 `clean_work`（與函式名 "two kinds" 改 "three kinds"）外，其餘斷言一字不變 | 自動：`platform/tests/test_resume_scope.py`、`platform/tests/test_keep_submissions.py` |
| TC-079 | 計畫「必須更新的既有斷言」：只改這三處 | 功能 | 實作完成的分支 | 驗收者逐檔比對三個既有測試與 base | 只有 `test_resume_scope.py:68-70`、`test_keep_submissions.py:773`、`test_launch_platform.py:606` 的集合斷言加入 `clean_work`（及函式名）；沒有任何斷言被刪除、放寬或跳過；其他既有測試沒被動 | 手動：驗收閱卷以 `git diff` 核對 |
| TC-080 | TC-070（新檔理由） | 功能 | 新檔 `test_cleanup_confirm.py` | 查檔案前 40 行 | 有 `# Nothing existing:` 開頭、理由至少 15 字；既有檢查通過 | 自動：既有 TC-070 檢查 |
| TC-081 | 專長守則：錯誤訊息與日誌 | 例外 | 觸發 TC-026、TC-034、TC-042、TC-045、TC-047 各種拒絕 | 讀被拒的訊息文字 | 訊息說明發生什麼事與該怎麼做；不含堆疊（Traceback）、SQL、內部檔案路徑、密鑰或 token | 自動 |
