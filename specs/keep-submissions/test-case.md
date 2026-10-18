# 測試案例：keep-submissions（送出的內容除非使用者刪除，不然不刪）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
There is no spec.md for this task; `specs/keep-submissions/plan.md` carries the maintainer's words, the rulings (1-6, R1-R13), and the five examples.
-->

**規格**：`specs/keep-submissions/plan.md`（本任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

他的原話（2026-10-18）：「送出內容除非使用者刪除不然不刪」。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「內容」＝一筆送出紀錄裡的 `bundle_json`（當時要跑什麼）和 `screen_text`（使用者當時看到並同意的畫面文字）。「稽核欄位」＝紀錄本身（誰、何時、哪一種、狀態）。「未送出」＝狀態是 `void`（作廢）或 `pending`（等待中）且已逾時的申請。新增的測試全部寫在 `platform/tests/test_keep_submissions.py`，每個測試用註解寫出它對應的 TC 編號（計畫 R13）。本表所有「自動」都指這個檔案，除非另外寫明。

## User Story 1 — 已確認送出的內容不會被時間清掉（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 例子 1；規則 1 | 功能 | 有一筆已確認（`confirmed`）的啟動申請，400 天前確認，內容（bundle 與畫面文字）都還在 | 之後任何人呼叫一次 `create_pending`（它會順手做清理） | 這筆 400 天前確認的紀錄，bundle 與畫面文字都還在，內容與原來一字不差 | 自動：`platform/tests/test_keep_submissions.py` |
| TC-002 | 規則 1 | 功能 | 同 TC-001 | 同 TC-001 | 這筆紀錄的稽核欄位（id、sha256、種類、時間、caller_user_id、channel、state 仍是 `confirmed`）全部不變 | 自動 |
| TC-003 | 規則 1（舊規則是 7 天） | 功能 | 一筆已確認的紀錄，8 天前確認（剛好超過舊的 7 天上限），內容在 | 呼叫一次 `create_pending` | 內容仍在（舊版這時會被清掉，新版不會） | 自動 |
| TC-004 | 例子 2；規則 2 | 功能 | 一筆等待中（`pending`）的申請，8 天前就已逾時，內容在 | 呼叫一次 `create_pending` | 這筆的 bundle 與畫面文字被清掉 | 自動 |
| TC-005 | 例子 2；規則 2 | 功能 | 一筆等待中的申請，6 天前逾時，內容在 | 呼叫一次 `create_pending` | 這筆的 bundle 與畫面文字還在 | 自動 |
| TC-006 | 規則 2 | 功能 | 一筆作廢（`void`）的申請，8 天前建立，內容在 | 呼叫一次 `create_pending` | 內容被清掉 | 自動 |
| TC-007 | 規則 2 | 功能 | 一筆作廢的申請，6 天前建立，內容在 | 呼叫一次 `create_pending` | 內容還在 | 自動 |
| TC-008 | 規則 2（稽核欄位保留） | 功能 | 同 TC-004 與 TC-006 的兩筆被清掉內容的紀錄 | 清理之後讀這兩筆 | 兩筆都還在，id、sha256、種類、時間、caller_user_id、state 不變，只有 bundle 與畫面文字變空 | 自動 |
| TC-009 | 規則 2（改名） | 功能 | 程式碼 | 讀 `platform/abf_platform/confirm.py` 的常數 | 有 `KEEP_UNSENT_SECONDS`，值等於 7 天（604800 秒）；舊名 `KEEP_CONTENT_SECONDS` 已不存在 | 自動 |
| TC-010 | R1（被推翻的舊測試） | 功能 | `platform/tests/test_review_fixes.py`（約第 119 行、第二個 review item 8）與 `platform/tests/test_review_fixes_2.py` 的 `test_r8_confirmed_rows_lose_their_content_after_seven_days_too` | 讀這兩個測試 | 兩個測試都改成「已確認的紀錄不論多久都保有內容」；作廢與逾時等待中那一半的斷言原封不動，仍是「7 天後被清掉」；除了這兩處，這些測試檔沒有其他斷言被放寬 | 自動（驗收者對照 main 的差異） |

## User Story 2 — 擁有者主動刪除一個 run 的送出內容（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 例子 3；規則 3 | 功能 | 擁有者在終端機以外的人按的管道（表單或網頁）確認送出了 run R1；R1 已結束（succeeded）；它的確認紀錄有 bundle 與畫面文字 | 擁有者執行 `abf-platform forget R1`，在提示出現時回答 `y` | R1 那筆確認紀錄的 bundle 與畫面文字都變空 | 自動 |
| TC-012 | 例子 3；規則 3（稽核保留） | 功能 | 同 TC-011 | 同 TC-011 | 那筆確認紀錄仍在，id、sha256、種類、時間、caller_user_id、channel、state（`confirmed`）都不變 | 自動 |
| TC-013 | R8 | 功能 | 同 TC-011 | 同 TC-011 | 被清掉內容的每一筆（確認紀錄與工作紀錄）都寫入 `forgotten_at`（刪除時間）；從終端機刪的，`forgotten_by` 是空值（NULL） | 自動 |
| TC-014 | R4；R10 | 功能 | 同 TC-011；R1 的啟動工作（jobs 的一列）自己留了一份排隊內容 | 同 TC-011 | 該工作的 `args_json` 變成剛好 `{"forgotten": true, "bundle": {"run_name": "R1"}}`；該列的稽核欄位（id、agent、kind、state、時間、confirmation_id 等）不變，並有 `forgotten_at` | 自動 |
| TC-015 | R9 | 功能 | R1 還有一筆已確認的取消（cancel）申請及它的取消工作，兩者都留有內容 | 擁有者 `forget R1` 並答 `y` | 取消確認紀錄與取消工作的內容也被清掉（同 TC-013、TC-014 的方式），稽核欄位保留 | 自動 |
| TC-016 | R9 | 功能 | R1 是從終端機確認的啟動（這種啟動在 `confirmations` 裡本來就沒有內容），只有工作紀錄留有內容 | `forget R1` 並答 `y` | 只有工作那份內容被清掉（變成 TC-014 的樣子），沒有錯誤 | 自動 |
| TC-017 | R6；R9 | 功能 | R1 另有：一筆等待中的取消申請（尚未逾時）、一筆作廢的啟動申請，都留有內容且都指名 R1 | `forget R1` 並答 `y` | 這兩筆的內容都被清掉；原本還開著的那筆等待中申請變成作廢（`void`），不能再被按送出 | 自動 |
| TC-018 | R9 | 功能 | 另有 run R2，同樣已結束、有內容，也有它自己的工作與申請 | `forget R1` 並答 `y` | R2 的確認紀錄、工作、申請的內容一個字都沒動，也沒有 `forgotten_at` | 自動 |
| TC-019 | 規則 3（畫面文字、y、無 --yes） | 功能 | R1 已結束 | 執行 `abf-platform forget R1` | 提示畫面逐字包含「刪除後無法復原；這個 run 之後不能再續跑或原樣重跑。紀錄（誰、何時送出）會保留。」，並等待回答 `y`，像 `cancel` 一樣 | 自動 |
| TC-020 | 規則 3（像 cancel 一樣要人確認） | 例外 | R1 已結束，內容在 | 執行 `abf-platform forget R1`，回答 `n`（或直接按 Enter、或任何不是 `y` 的字） | 什麼都沒被清掉，沒有任何 `forgotten_at` | 自動 |
| TC-021 | 規則 3（不可有 --yes） | 例外 | R1 已結束，內容在 | 執行 `abf-platform forget R1 --yes` | 指令不接受 `--yes`（跟 `cancel` 一樣報不認得的選項），什麼都沒被清掉 | 自動 |
| TC-022 | R5 | 功能 | R1 是使用者 A 送出的；從終端機操作 | 在終端機（沒有登入身分）執行 `forget R1` 並答 `y` | 照樣刪除，不做擁有者檢查，跟 `abf-platform cancel` 一樣 | 自動 |
| TC-023 | R7；例子 3 | 功能 | R1 的狀態（`status.py` 算出的）是 succeeded | `forget R1` 並答 `y` | 允許，內容被清掉 | 自動 |
| TC-024 | R7 | 功能 | R1 的狀態是 failed | 同上 | 允許，內容被清掉 | 自動 |
| TC-025 | R7 | 功能 | R1 的狀態是 aborted | 同上 | 允許，內容被清掉 | 自動 |
| TC-026 | R6 | 例外 | R1 已經刪除過一次（沒有任何已確認的內容留著） | 再執行一次 `forget R1` | 回答「已經刪除過了 (already deleted)」；不報錯；資料庫一個字都沒變（`forgotten_at` 不會被改寫） | 自動 |
| TC-027 | R8 | 功能 | 一個舊版 `platform.db`，`confirmations` 與 `jobs` 沒有 `forgotten_at`、`forgotten_by`，裡面有若干列 | 用新版程式打開它 | 兩張表都多了這兩欄；所有原有的列數與內容都沒少沒變 | 自動 |

## User Story 3 — 透過 MCP（AI 的工具）與其他人（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 例子 4；規則 3；R5 | 例外 | R1 是使用者 A 的 run，內容在；使用者 B 是另一個人 | B 透過 MCP 或 HTTP 要求 `forget R1` | 回答「查無／not found」；R1 的任何資料都沒變；B 沒有被問任何確認 | 自動 |
| TC-031 | 規則 3（#116 規則：不是你的和不存在，答案一樣） | 例外 | 同 TC-030，另有一個根本不存在的 run 名 R999 | B 要求 `forget R1`，再要求 `forget R999` | 兩個回答完全相同，看不出 R1 存在 | 自動 |
| TC-032 | 規則 3；R8 | 功能 | R1 是使用者 A 的、已結束；A 的 MCP 客戶端可以跳出表單 | A 呼叫 MCP 工具 `forget`，在表單上按同意 | R1 的內容被清掉；被清掉的每一列 `forgotten_by` 是 A 的使用者編號，並有 `forgotten_at` | 自動 |
| TC-033 | 規則 3（畫面文字） | 功能 | 同 TC-032 | A 呼叫 `forget` | 表單上的文字逐字包含「刪除後無法復原；這個 run 之後不能再續跑或原樣重跑。紀錄（誰、何時送出）會保留。」 | 自動 |
| TC-034 | 規則 3（要人同意才刪） | 例外 | 同 TC-032 | A 呼叫 `forget`，在表單上按拒絕（或關掉） | 什麼都沒被清掉；`confirmations` 沒有新增任何一列 | 自動 |
| TC-035 | R8（沒有確認紀錄） | 功能 | 同 TC-032 | A 呼叫 `forget` 並同意 | `confirmations` 的列數前後相同（`forget` 不寫確認紀錄，也沒有新的 `kind`） | 自動 |
| TC-036 | R2（不排工作） | 功能 | 同 TC-032 | A 呼叫 `forget` 並同意 | `jobs` 沒有新增任何一列（`forget` 不排任何工作） | 自動 |
| TC-037 | R2；009i 連接器規則 | 例外 | A 用 HTTP 連線，客戶端的表單不被信任（連接器權杖 `form_ok` 為 false，也就是只能走網頁確認的那種） | 呼叫 `forget` | 不寫任何東西、不給確認網頁連結，回答「這個客戶端無法跳出確認視窗；請在終端機執行 abf-platform forget <run> (this client cannot show a confirmation form; use the terminal command)」 | 自動 |
| TC-038 | R2；R11 | 例外 | 本機 stdio 連線，客戶端沒有可用的表單 | 呼叫 `forget` | 不寫任何東西，回答同 TC-037 的那句話 | 自動 |
| TC-039 | R11 | 功能 | 本機 stdio 連線，客戶端有可用的表單；R1 已結束 | 呼叫 `forget`，表單按同意 | 照樣刪除（跟 `cancel` 一樣）；`forgotten_by` 為空值（stdio 沒有使用者） | 自動 |
| TC-040 | R1（固定的工具清單） | 功能 | `test_human_channel.py`（約 158 行）、`test_guidance.py`（約 397 行）、`test_actions_layer.py`（約 28 行）裡的 MCP 工具清單 | 讀這些清單，並列出平台實際註冊的工具 | 每份清單恰好比 main 多一個 `forget`，其餘一個字不變；實際註冊的工具也包含 `forget` | 自動 |
| TC-041 | R9 | 功能 | R1 的取消申請有兩筆：一筆是 A 的，一筆是另一個人 B 的（兩筆都指名 R1，都有內容） | A 透過 MCP 對 R1 執行 `forget` 並同意 | A 的那筆被清掉；B 的那筆內容不動 | 自動 |

## User Story 4 — 現在不能刪的時候（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 例子 5；規則 3；R7 | 例外 | 擁有者的 R1 正在跑（狀態 running），內容在 | 擁有者透過 MCP 要求 `forget R1` | 被拒絕，回答同時有中文和英文說明「還在跑，不能刪」；資料庫一個字都沒變 | 自動 |
| TC-051 | R7 | 例外 | R1 的狀態是 lost（失聯，叢集上可能還在跑） | 擁有者要求 `forget R1` | 被拒絕，內容與工作紀錄都沒變 | 自動 |
| TC-052 | R7 | 例外 | R1 已送出啟動工作，但 run 索引裡還沒有 R1（`get_run` 回 found:false，而啟動工作存在） | 擁有者要求 `forget R1` | 被拒絕，回答「這個 run 還在準備中，不能刪除 (the run is still starting)」；沒有任何變動 | 自動 |
| TC-053 | R7 | 例外 | R1 狀態已是 succeeded，但它有一筆 `jobs` 還在排隊（queued，例如一個取消工作） | 擁有者要求 `forget R1` | 被拒絕，沒有任何變動 | 自動 |
| TC-054 | R7 | 例外 | R1 狀態已是 succeeded，但它有一筆 `jobs` 已被代理領走（claimed） | 擁有者要求 `forget R1` | 被拒絕，沒有任何變動 | 自動 |
| TC-055 | R7；R5 | 例外 | R1 正在跑 | 在終端機執行 `abf-platform forget R1` | 同樣被拒絕（終端機沒有擁有者檢查，但狀態檢查照樣有），資料庫一個字都沒變 | 自動 |

## User Story 5 — 刪除之後，別的地方不能壞（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | R10；規則 4 | 功能 | R1 的啟動工作已逾時（expired）；擁有者之後執行了 `forget R1`；之後代理才遲到地回報這個工作的結果 | 代理送出遲到的結果 | 系統照常收下，沒有當掉；仍能從被留下的 run 名處理（`_apply_handover` 讀得到 `R1`） | 自動 |
| TC-061 | R10 | 功能 | 同 TC-060，但是 R1 的取消工作（cancel_run） | 代理送出遲到的結果 | 系統沒有當掉（讀不到取消用的 Slurm 編號時，不去改任何別的 run） | 自動 |
| TC-062 | 規則 4 | 功能 | `specs/keep-submissions/ledger.md` | 讀它 | 若 009e（續跑／原樣重跑）還不在 v3：ledger 寫下「讀已確認 bundle 的人要在哪裡把『內容已被擁有者刪除 (content deleted by its owner)』當成拒絕訊息」的接入點；同時 diff 裡沒有 009e 的程式碼 | 自動 |
| TC-063 | R12 | 功能 | `specs/keep-submissions/ledger.md` | 讀它 | 記下 `forget` 是欠下的網頁對等功能（`docs/ROADMAP.md:98`），因為目前沒有網頁路由 | 自動 |

## User Story 6 — 文件與測試紀錄（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 規則 6 | 功能 | `docs/PLATFORM.md` | 讀保留期限那一段 | 寫明：已確認送出的內容保留到擁有者刪除；未送出的（作廢、逾時等待中）7 天後清掉；不再有「已確認的 7 天後清」的說法 | 自動 |
| TC-071 | 規則 6 | 功能 | `docs/PLATFORM.md` | 讀新動作的說明 | 有 `forget`：終端機 `abf-platform forget RUN` 與 MCP 工具 `forget`；只有擁有者；跑到一半不能刪；刪了無法復原；紀錄保留 | 自動 |
| TC-072 | R4 | 功能 | `docs/PLATFORM.md` | 找「the job keeps its own copy of what was queued」那一句 | 那一句已改成也說明 `forget` 會把這份工作自己留的副本一起清掉 | 自動 |
| TC-073 | 規則 6 | 功能 | `CHANGELOG` | 讀最上面的新條目 | 有一條說明：已確認內容不再被時間清掉、新增 `forget` | 自動 |
| TC-074 | R13 | 功能 | `platform/tests/test_keep_submissions.py` | 讀檔案 | 本合約每一條標「自動」的 TC 編號，都在這個檔案某個測試的註解裡出現；沒有寫了編號卻空的或只檢查檔案存在的測試 | 自動（驗收者讀檔） |

## 不在範圍（計畫「Out of scope」與相關禁止事項）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 不在範圍：刪除叢集上的結果 | 不在範圍 | R1 已結束，叢集端有 `rawdata`／`results`／`analysis` | `forget R1` 並同意 | 沒有任何工作被排進 `jobs`（任何種類都沒有新增），叢集端沒有任何刪除動作；`forget` 只動這個資料庫裡的內容 | 自動 |
| TC-081 | 不在範圍：從 run 清單刪 run | 不在範圍 | R1 已結束，在 run 清單裡 | `forget R1` 並同意 | R1 仍在 run 清單裡，`get_run` 仍找得到它，狀態與原來相同 | 自動 |
| TC-082 | 不在範圍：任何網頁介面；規則 5 | 不在範圍 | 網頁服務（唯讀） | 檢查網頁的路由，並對網頁送出一個 forget 的請求 | 網頁沒有任何刪除按鈕或 forget 路由；請求得到「找不到」或被拒，R1 沒變 | 自動 |
| TC-083 | R2；R8（不動既有的確認機制） | 不在範圍 | 程式碼 | 讀 `confirm.JOB_KIND` 與 `confirmations.kind` 的 CHECK 限制 | `JOB_KIND` 仍只有 launch、cancel 兩項，`kind` 的 CHECK 仍只允許 `'launch'`、`'cancel'`，`confirm.approve` 沒有為 forget 加分支 | 自動 |
| TC-084 | 規則 4（不要把 009e 帶進來） | 不在範圍 | diff | 看這個分支相對 main 的變更 | 沒有續跑或原樣重跑（resume／relaunch）的程式碼 | 自動（驗收者讀 diff） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-090 | 第 2 條（不得留第二份 run 狀態） | 功能 | 這個分支 | 執行 `bash tests/no_second_run_state_test.sh` | 通過；新增的 `forgotten_at`、`forgotten_by` 只記「內容被刪」這件稽核事實，不記 run 的狀態，檢查沒有被放寬 | 自動：`tests/no_second_run_state_test.sh` |
| TC-091 | 安全網：啟動前必須有人確認 | 例外 | 沒有人確認的啟動請求 | 透過 MCP 與網頁各送一次未確認的啟動 | 仍然都被拒絕（`test_human_channel.py` 的 `test_tch09_*`、`test_confirm_page.py` 的 `test_tch09_b_c_*` 通過且未被修改）；`forget` 沒有開出新的送出路徑 | 自動：`tests/platform_test.sh` |
| TC-092 | 安全網：不刪使用者原始資料（`rawdata/`、`results/`、`analysis/`） | 功能 | R1 在叢集與本機有這三類資料夾 | `forget R1` 並同意 | 這些資料夾與裡面的檔案一個都沒少（見 TC-080 沒有排任何工作） | 自動 |
| TC-093 | 開發流程：不得放寬舊測試 | 功能 | diff 裡所有被修改的測試檔 | 逐檔對照 main | 除了 TC-010 與 TC-040 指名的那幾處，沒有任何斷言被刪除、放寬、跳過或把預期值改成配合新輸出；`spec.md`、`test-case*.md` 沒有在實作期間被編輯 | 自動（驗收者對照 main 的差異） |
