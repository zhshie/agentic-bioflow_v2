# 測試案例：keep-submissions（送出的內容除非使用者刪除，不然不刪）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
There is no spec.md for this task; `specs/keep-submissions/plan.md` carries the maintainer's words, the rulings (1-6, R1-R16, F1-F12), and the five examples.
Revised 2026-10-18 after "Follow-up after PR #133 review" (F1-F6, the developer-agent reopened the contract; F6 lets the verifier amend):
  amended: TC-016, TC-040, TC-062, TC-064, TC-070, TC-074, TC-084, TC-093, TC-095;
  added: TC-075, TC-100 to TC-113 (catch up with v3 / 009e), TC-120 to TC-131 (resume and relaunch refuse a forgotten run, F2),
         TC-140 to TC-146 (forget while the launch is still starting, F4), TC-150 to TC-161 (any channel keeps its content, F5), TC-096, TC-097.
Revised again 2026-10-18 after "Rulings after follow-up acceptance" (F7-F12; the developer-agent reopened the contract, F6 lets the verifier amend):
  amended: TC-062, TC-074, TC-084, TC-093, TC-131;
  added: TC-114, TC-115 (F8 ask list, F9 named old-test edits), TC-132, TC-133 (F10 pending resume/relaunch voided at once), TC-147 (F7 launch job row pruned),
         TC-162 to TC-165 (F11 terminal-confirmed cancel keeps its content).
No id was renumbered. Every other row is word for word what was confirmed before.
-->

**規格**：`specs/keep-submissions/plan.md`（本任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

他的原話（2026-10-18）：「送出內容除非使用者刪除不然不刪」。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「內容」＝一筆送出紀錄裡的 `bundle_json`（當時要跑什麼）和 `screen_text`（使用者當時看到並同意的畫面文字）。「稽核欄位」＝紀錄本身（誰、何時、哪一種、狀態）。「未送出」＝狀態是 `void`（作廢）或 `pending`（等待中）且已逾時的申請。「工作」＝`jobs` 表的一列，平台交給叢集代理去做的一件事（啟動、取消…），它自己也留一份排隊時的內容副本。「009e」＝已經在 `v3` 的「續跑（resume，同一個資料夾接著做）與原樣重跑（relaunch，全新資料夾）」功能。「舊格式的列」＝本變更之前做的、已確認但確認紀錄沒有內容的終端機啟動（內容只在工作副本裡）。「run 索引」＝平台從 Nextflow 自己的紀錄讀出來的 run 清單（`get_run` 查的就是它）。新增的測試全部寫在 `platform/tests/test_keep_submissions.py`，每個測試用註解寫出它對應的 TC 編號（計畫 R13）。本表所有「自動」都指這個檔案，除非另外寫明。

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
| TC-016 | R9；F5（改寫：終端機確認的啟動現在確認紀錄也有內容） | 功能 | R1 是從終端機確認的啟動（F5 之後：它的確認紀錄有 bundle 與畫面文字，工作也留有一份） | `forget R1` 並答 `y` | 確認紀錄的內容與工作那份內容都被清掉（工作變成 TC-014 的樣子），兩處都有 `forgotten_at`，稽核欄位保留，沒有錯誤 | 自動 |
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
| TC-040 | R1；F3（改寫：固定工具清單改成兩邊的聯集） | 功能 | `test_human_channel.py`、`test_guidance.py`、`test_actions_layer.py` 裡的 MCP 工具清單 | 讀這些清單，並列出平台實際註冊的工具 | 每份清單恰好是 `origin/v3` 上的那份再多一個 `forget`（所以同時含 `resume`、`relaunch` 與 `forget`），其餘一個字不變；實際註冊的工具也包含這三個 | 自動 |
| TC-041 | R9 | 功能 | R1 的取消申請有兩筆：一筆是 A 的，一筆是另一個人 B 的（兩筆都指名 R1，都有內容） | A 透過 MCP 對 R1 執行 `forget` 並同意 | A 的那筆被清掉；B 的那筆內容不動 | 自動 |

## User Story 4 — 現在不能刪的時候，與不用等的時候（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 例子 5；規則 3；R7 | 例外 | 擁有者的 R1 正在跑（狀態 running），內容在 | 擁有者透過 MCP 要求 `forget R1` | 被拒絕，回答同時有中文和英文說明「還在跑，不能刪」；資料庫一個字都沒變 | 自動 |
| TC-051 | R7 | 例外 | R1 的狀態是 lost（失聯，叢集上可能還在跑） | 擁有者要求 `forget R1` | 被拒絕，內容與工作紀錄都沒變 | 自動 |
| TC-052 | R7；R15 | 例外 | R1 的啟動工作狀態是排隊中（queued），run 索引裡還沒有 R1（`get_run` 回 found:false） | 擁有者要求 `forget R1` | 被拒絕，回答「這個 run 還在準備中，不能刪除 (the run is still starting)」；沒有任何變動 | 自動 |
| TC-053 | R7 | 例外 | R1 狀態已是 succeeded，但它有一筆 `jobs` 還在排隊（queued，例如一個取消工作） | 擁有者要求 `forget R1` | 被拒絕，沒有任何變動 | 自動 |
| TC-054 | R7 | 例外 | R1 狀態已是 succeeded，但它有一筆 `jobs` 已被代理領走（claimed） | 擁有者要求 `forget R1` | 被拒絕，沒有任何變動 | 自動 |
| TC-055 | R7；R5 | 例外 | R1 正在跑 | 在終端機執行 `abf-platform forget R1` | 同樣被拒絕（終端機沒有擁有者檢查，但狀態檢查照樣有），資料庫一個字都沒變 | 自動 |
| TC-056 | R15 | 例外 | R1 的啟動工作狀態是已被代理領走（claimed），run 索引裡還沒有 R1 | 擁有者要求 `forget R1` | 被拒絕，回答同 TC-052 的「還在準備中」那句；沒有任何變動 | 自動 |
| TC-057 | R15 | 功能 | R1 的啟動工作被代理拒絕了（`refused`），R1 從來沒進過 run 索引；確認紀錄與工作紀錄都有內容 | 擁有者要求 `forget R1`，同意 | 允許（不是「還在準備中」，也不是「查無」）；確認紀錄與工作那份內容被清掉，稽核欄位保留，有 `forgotten_at` | 自動 |
| TC-058 | R15 | 功能 | R1 的啟動工作失敗了（`error`），R1 從來沒進過 run 索引；有內容 | 擁有者要求 `forget R1`，同意 | 同 TC-057：允許、內容被清掉、稽核保留 | 自動 |
| TC-059 | R15 | 功能 | R1 的啟動工作已逾時（`expired`），R1 從來沒進過 run 索引；有內容 | 擁有者要求 `forget R1`，同意 | 同 TC-057：允許、內容被清掉、稽核保留 | 自動 |

## User Story 5 — 刪除之後，別的地方不能壞；已知的限制（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | R10；規則 4 | 功能 | R1 的啟動工作已逾時（expired）；擁有者之後執行了 `forget R1`；之後代理才遲到地回報這個工作的結果 | 代理送出遲到的結果 | 系統照常收下，沒有當掉；仍能從被留下的 run 名處理（`_apply_handover` 讀得到 `R1`） | 自動 |
| TC-061 | R10 | 功能 | 同 TC-060，但是 R1 的取消工作（cancel_run） | 代理送出遲到的結果 | 系統沒有當掉（讀不到取消用的 Slurm 編號時，不去改任何別的 run） | 自動 |
| TC-062 | 規則 4；F1–F5、F7–F12（改寫：009e 已經進來，不再是「記下接入點」；F7 至 F12 也要記下） | 功能 | `specs/keep-submissions/ledger.md` | 讀它 | 不再寫「009e 還不在 v3、沒有帶進它的程式碼」；改為記下：已合併 `origin/v3`（F1）、續跑與重跑拒絕已刪除的 run 的位置（F2：命令列、MCP、排隊檢查三處）、F3 的清單對帳、F4、F5 各自完成；並記下 F7（啟動工作列已被清掉時允許刪）、F8（`forget` 加進 settings.json 的 ask 清單）、F9（被點名的兩個 009e 測試只改前置資料）、F10（刪除時把指向該 run 的等待中續跑／重跑申請作廢）、F11（終端機確認的取消也保留內容）、F12（網頁對等仍欠）；沒有已完成的項目是空白打勾 | 自動（驗收者讀檔） |
| TC-063 | R12 | 功能 | `specs/keep-submissions/ledger.md` | 讀它 | 記下 `forget` 是欠下的網頁對等功能（`docs/ROADMAP.md:98`），因為目前沒有網頁路由 | 自動（驗收者讀檔） |
| TC-064 | R16；F5（改寫：限制（一）縮小了） | 功能 | `specs/keep-submissions/ledger.md` | 讀它 | 記下三項已知限制：（一）工作自己那份副本仍在工作結束 7 天後隨該列被刪，但現在不論哪個管道確認的送出，確認紀錄都保有內容；只有 F5 之前做的終端機啟動（舊格式的列）內容只在工作副本；（二）`result_json`／`late_result_json` 是結果不是送出內容，`forget` 不清；（三）沒有網頁刪除。三項都明說「維護者可再議」或等同意思；且不再寫「終端機確認的啟動只有工作副本有內容」這句對新列已不成立的話 | 自動（驗收者讀檔） |
| TC-065 | R16（二） | 功能 | R1 的工作有 `result_json` 與 `late_result_json` 內容；R1 已結束 | `forget R1` 並同意 | 這兩欄一個字都沒變（`forget` 只清送出內容，不清結果） | 自動 |
| TC-066 | R16（一） | 功能 | 一筆已確認的啟動（表單確認），它的工作 8 天前就結束；確認紀錄有內容 | 之後再排入一個新工作（會順手清掉結束超過 7 天的工作列） | 該舊工作列被清掉（現行行為原樣保留），但那筆已確認紀錄的 bundle 與畫面文字還在 | 自動 |

## User Story 6 — 文件與測試紀錄（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 規則 6；F5（補：不論管道） | 功能 | `docs/PLATFORM.md` | 讀保留期限那一段 | 寫明：已確認送出的內容保留到擁有者刪除，不論由終端機、表單或網頁確認；未送出的（作廢、逾時等待中）7 天後清掉；不再有「已確認的 7 天後清」的說法 | 自動 |
| TC-071 | 規則 6 | 功能 | `docs/PLATFORM.md` | 讀新動作的說明 | 有 `forget`：終端機 `abf-platform forget RUN` 與 MCP 工具 `forget`；只有擁有者；跑到一半不能刪；刪了無法復原；紀錄保留 | 自動 |
| TC-072 | R4 | 功能 | `docs/PLATFORM.md` | 找「the job keeps its own copy of what was queued」那一句 | 那一句已改成也說明 `forget` 會把這份工作自己留的副本一起清掉 | 自動 |
| TC-073 | 規則 6 | 功能 | `CHANGELOG` | 讀最上面的新條目 | 有一條說明：已確認內容不再被時間清掉、新增 `forget` | 自動 |
| TC-074 | R13（改寫：排除名單更新） | 功能 | `platform/tests/test_keep_submissions.py` | 讀檔案 | 本合約每一條標「自動」、驗證方式是這個檔案的 TC 編號，都在某個測試的註解裡出現（不含由驗收者讀檔／讀差異判斷或用既有腳本或既有測試檔的 TC-010、062、063、064、075、084、090、091、093、094、095、100、101、102、103、105、106、110、111、112、114、115）；沒有寫了編號卻空的或只檢查檔案存在的測試 | 自動（驗收者讀檔） |
| TC-075 | F2；F4；F5 | 功能 | `docs/PLATFORM.md` | 讀「續跑與重跑」那一節與 `forget` 那一節 | 寫明：已刪除內容的 run 不能續跑或重跑（答「內容已被擁有者刪除」）；`forget` 在「啟動成功但 run 尚未進索引」時拒絕，直到索引看到它或工作結束後 24 小時；續跑與重跑先讀確認紀錄的內容、只有舊格式的列才退回讀工作副本、「太久了」只用在退回的情況 | 自動（驗收者讀檔） |

## User Story 7 — 追上 v3（009e）：合併、兩邊並存、清單與數量對帳（優先度 P1）

這一段對應 F1、F3 與 F8。重點：兩邊的功能都在，任何數量都不能為了讓測試過而調低。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-100 | F1 | 功能 | 本分支的 git 紀錄 | 看紀錄 | `origin/v3` 當時的最新一筆是本分支的祖先；有一筆單獨的合併提交（兩個父提交）只放合併與衝突解決；本分支原有的提交（含 6199677、d75e7f7）都仍是祖先（沒有 rebase，也沒有被改寫掉） | 自動（驗收者讀 git 紀錄） |
| TC-101 | F1 | 功能 | `docs/PLATFORM.md` | 讀全文的章節標題與內容 | 「Forget」那一節與 009e 的「Resume and relaunch」那一節都在，兩邊原有的段落沒有被丟掉；沒有衝突標記（`<<<<<<<`、`=======`、`>>>>>>>`）殘留在任何檔案 | 自動（驗收者讀檔與 `git grep`） |
| TC-102 | F1 | 功能 | `platform/abf_launch/build.py`、`platform/abf_launch/cli.py`、`platform/abf_platform/mcp_server.py` | 讀這三個檔 | `build.py` 同時有 `forget_screen` 與 009e 的 `prepare_resume`、`prepare_relaunch`、`resume_screen`、`relaunch_screen`；`cli.py` 同時有 `forget`、`resume`、`relaunch` 三個子指令；`mcp_server.py` 同時註冊 `forget`、`resume`、`relaunch` | 自動（驗收者讀檔） |
| TC-103 | F1 | 功能 | `platform/tests/test_resume_*.py`、`test_station_resume.py`、`test_station_launch.py` 及其他 009e 帶來的測試 | 對照 `origin/v3` 的同名檔 | 009e 的測試全部還在、全部通過；對它們的改動只有兩種：F3 的「加上 `forget` 與數量加 1」，以及 TC-093 允許的 F9 前置資料調整；沒有 009e 的斷言被刪除、放寬、跳過 | 自動（驗收者對照 `origin/v3` 的差異） |
| TC-104 | F3 | 功能 | 平台實際註冊的 MCP 工具 | 列出工具 | 恰好 11 個：`list_runs`、`get_run`、`list_compute_envs`、`get_compute_env`、`list_agents`、`list_site_files`、`launch`、`cancel`、`resume`、`relaunch`、`forget`；其中會寫東西的五個（launch、cancel、resume、relaunch、forget）都沒有任何能代替人說「是」的欄位；六個唯讀的仍是唯讀 | 自動 |
| TC-105 | F3 | 功能 | 所有寫著工具數量的測試（`test_pat.py`、`test_oauth_mcp.py`、`test_mcp.py`、`test_launch_e2e.py`、`test_launch_platform.py`、`test_human_channel.py`、`test_guidance.py`、`test_actions_layer.py`、`test_station_envs.py`） | 逐處對照 `origin/v3` | 每個數量都是 v3 的數量加 1（10 變 11），沒有任何一處是 8 或 9（那會是漏了 009e 的兩個），沒有任何數量比 v3 小；每份名單都同時含 `resume`、`relaunch`、`forget` | 自動（驗收者對照差異；測試本身隨 `bash tests/platform_test.sh`） |
| TC-106 | F3 | 功能 | `docs/PLATFORM.md` 描述工具的那一段（原寫「Nine tools」） | 讀 | 數量與名單是 11 個並逐個點名，與 TC-104 一致；找不到「Nine tools」「Ten tools」這類舊數量 | 自動（驗收者讀檔） |
| TC-107 | F3 | 功能 | MCP 的 `instructions` 文字（`platform/abf_platform/guidance.py` 的固定句與產生的段落） | 讀它，並跑 `test_guidance.py` | 同時說到 `launch`、`cancel`、`resume`、`relaunch`、`forget` 都只是「詢問」（沒有人說是之前什麼都不會送出）；009e 那句「失敗的 run 只用名字就能續跑或重跑」仍在；文字大小仍在該檔設的上限內；`test_guidance.py` 通過 | 自動：`platform/tests/test_guidance.py` |
| TC-108 | F3 | 功能 | `test_actions_layer.py` 的寫入動作名單、`test_station_envs.py` 的指令集合與 `--help` 字串 | 讀並執行 | 動作名單含 `request_resume`、`request_relaunch` 與 `forget` 的動作；指令集合含 `resume`、`relaunch`、`forget` 以及 v3 上已有的 `oauth` 等，`--help` 字串依註冊順序含這三個；009e 改寫過的「沒有會自己動手的 retry／resume」那條仍然成立 | 自動 |
| TC-109 | F1；R8 | 功能 | 一個合併前（v3 之前）的舊版 `platform.db`，有若干 `launches`、`confirmations`、`jobs` 列 | 用合併後的程式打開它 | `launches` 多了 009e 的 `parent_run`、`attempt`、`attempt_kind`；`confirmations` 與 `jobs` 多了 `forgotten_at`、`forgotten_by`；所有原有的列數與內容都沒少沒變；`launches` 欄位順序是 009e 釘的順序 | 自動 |
| TC-110 | F3；R12 | 功能 | `specs/keep-submissions/ledger.md` 與 `docs/ROADMAP.md` 第 98 行附近 | 讀 | 欠下的網頁對等清單同時列出 `forget`（本任務）以及 009e 留下的 `resume`、`relaunch`（如 009e 的 ledger 所記）；沒有把任何一項拿掉來讓清單變短 | 自動（驗收者讀檔） |
| TC-111 | F1 | 功能 | `CHANGELOG.md` | 讀最上面的幾個條目 | 009e 的條目與本任務的條目都在，兩邊的文字沒有被併掉或遺漏 | 自動（驗收者讀檔） |
| TC-112 | F1；F3 | 功能 | 合併完成、F2–F5 實作完成的分支 | 跑整個平台測試（`bash tests/platform_test.sh`，Windows 走 WSL，或看 CI 結果） | 全部通過；`tests/platform_test.sh` 的分片裡，每個測試檔剛好在一個分片（含 `test_keep_submissions.py` 與 009e 新增的測試檔）；單一分片的時間限制沒有被調高 | 自動（驗收者讀 CI 結果與 `tests/platform_test.sh`） |
| TC-113 | R14；F1 | 功能 | `test_station_envs.py` 的禁字掃描允許名單與 `test_station_platform.py` 的欄位檢查允許名單 | 讀 | 禁字掃描允許名單仍剛好多 `forgotten_at`、`forgotten_by` 兩個名字（TC-094 不變）；009e 加的 `("launches","parent_run")` 允許項仍在；兩邊都沒有被另一邊覆蓋掉 | 自動 |
| TC-114 | F8 | 功能 | `extensions/claude-code-kit/settings.json`，與釘住這份清單的測試（`platform/tests/test_resume_entrypoints.py` 約第 151 行） | 讀 `permissions.ask`，並讀那個測試 | `ask` 剛好五個名字：`mcp__abf-platform__launch`、`cancel`、`resume`、`relaunch`、`forget`（前四個原本就有，沒有被拿掉，沒有多出別的）；釘住的測試要求這五個，原本對前四個的斷言都還在 | 自動：`platform/tests/test_resume_entrypoints.py`（驗收者讀檔與差異） |
| TC-115 | F9 | 功能 | `specs/keep-submissions/ledger.md` 與 009e 兩個答「太久了」的測試（一個續跑、一個重跑；對照 `origin/v3`） | 讀 ledger，並逐行對照這兩個測試與 `origin/v3` 的同名測試 | ledger 逐一點名這兩個測試；兩個測試與 `origin/v3` 的差別只在前置資料（把那一列造成沒有內容的舊格式），所有斷言一字不變 | 自動（驗收者讀檔與差異） |

## User Story 8 — 續跑與重跑不能用在已刪除的 run（優先度 P1）

這一段對應 F2 與 F10。拒絕的字句是「內容已被擁有者刪除」（計畫 R10 的完整句是「內容已被擁有者刪除 (content deleted by its owner)」，測試只要求前半句出現）。所有拒絕都不排任何工作。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-120 | F2 | 例外 | R1 是擁有者的、已失敗（本來可以續跑）；擁有者已對 R1 `forget`（內容被刪） | 擁有者在終端機執行 `abf-platform resume R1` | 被拒絕，回答含「內容已被擁有者刪除」；不是「太久了」，也不是「找不到」，也不是程式錯誤；`jobs` 沒有新增任何一列 | 自動 |
| TC-121 | F2 | 例外 | 同 TC-120 | 擁有者在終端機執行 `abf-platform relaunch R1` | 同 TC-120 | 自動 |
| TC-122 | F2 | 例外 | 同 TC-120；擁有者用 MCP | 呼叫 `resume`，run_name 是 R1 | 同 TC-120 的拒絕；沒有排任何工作 | 自動 |
| TC-123 | F2 | 例外 | 同 TC-120；擁有者用 MCP | 呼叫 `relaunch`，run_name 是 R1 | 同 TC-120 的拒絕；沒有排任何工作 | 自動 |
| TC-124 | F2（「或它的第一次啟動」） | 例外 | 分析 x 的第一次啟動 `x` 已失敗，續跑出 `x-a2` 也已失敗；擁有者之後對 `x` 執行 `forget` | 擁有者要求續跑 `x-a2`，再要求重跑 `x-a2` | 兩個都被拒絕，回答含「內容已被擁有者刪除」（因為它們的來源，第一次啟動的內容，已被刪）；沒有排任何工作 | 自動 |
| TC-125 | F2（「它所根據的 run」） | 例外 | 同 TC-124，但被 `forget` 的是 `x-a2` 本身，`x` 沒有被刪 | 擁有者要求續跑 `x-a2`，再要求重跑 `x-a2` | 兩個都被拒絕，回答含「內容已被擁有者刪除」；沒有排任何工作 | 自動 |
| TC-126 | F2（排隊檢查） | 例外 | 擁有者在 `forget R1` 之前，已經為失敗的 R1 準備好一份續跑的內容（bundle）；之後 R1 被 `forget` | 之後才用終端機的確認路徑把那份舊的續跑內容送去排隊 | 被拒絕，回答含「內容已被擁有者刪除」；`jobs` 與 `confirmations` 都沒有新增任何一列（要嘛兩個都寫，要嘛都不寫） | 自動 |
| TC-127 | F2（排隊檢查） | 例外 | 同 TC-126，但是重跑的內容 | 同 TC-126 | 同 TC-126 | 自動 |
| TC-128 | F2；#116 規則 | 例外 | R1 是使用者 A 的、已失敗，A 已 `forget` 它；使用者 B 是另一個人 | B 透過 MCP 對 R1 要求 `resume`，再要求 `relaunch` | 兩次的回答都和「根本沒有這個 run」一模一樣（「找不到」），不透露 R1 存在或已被刪 | 自動 |
| TC-129 | F2；F5 | 例外 | R1 已被 `forget`，而且 R1 的啟動工作副本早已超過 7 天被清掉（舊版這種情況會答「太久了」） | 擁有者要求續跑與重跑 R1 | 回答是「內容已被擁有者刪除」，不是「太久了，這次送出的內容已經清掉…」 | 自動 |
| TC-130 | F2（不誤傷） | 功能 | R1、R2 是擁有者的兩個不同的、已失敗的 run；R1 已被 `forget` | 擁有者要求續跑 R2，並按「是」 | R2 照常排入續跑工作（不受 R1 被刪影響） | 自動 |
| TC-131 | F2（已存在的等待中申請）；F10（改寫：現在要求當場作廢） | 例外 | 擁有者在 `forget R1` 之前用 MCP 為 R1 要求過續跑，申請還在等待中、尚未按送出；之後 R1 被 `forget` | `forget` 完成後，再按下送出 | 那筆申請在 `forget` 完成時就已經是作廢（`void`），不是等到按送出才被擋；按送出不排任何工作，`jobs` 沒有新增任何一列 | 自動 |
| TC-132 | F10 | 功能 | 擁有者的 R1 已失敗；擁有者用 MCP 為 R1 各要求過一次續跑與一次重跑，兩筆申請都在等待中、尚未逾時、尚未按送出，內容都在 | 擁有者對 R1 `forget` 並同意 | `forget` 完成的當下，這兩筆申請的狀態都已是作廢（`void`），不必等按送出、也不必等逾時；兩筆的 bundle 與畫面文字被清掉，並有 `forgotten_at` | 自動 |
| TC-133 | F10（不誤傷） | 功能 | 同 TC-132，另有擁有者為另一個失敗的 run R2 要求過的等待中續跑申請 | 擁有者對 R1 `forget` 並同意 | R2 那筆申請仍是等待中，內容完整、沒有 `forgotten_at`，之後按「是」仍能照常排入續跑 | 自動 |

## User Story 9 — `forget` 與「啟動剛成功但 run 還沒進索引」（優先度 P1）

這一段對應 F4 與 F7。「工作成功結束」＝代理回報 sbatch 已經送出去了。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-140 | F4 | 例外 | R1 的啟動工作 1 小時前成功結束，run 索引裡還沒有 R1 | 擁有者透過 MCP 要求 `forget R1` | 被拒絕，回答「這個 run 還在準備中，不能刪除」；資料庫一個字都沒變 | 自動 |
| TC-141 | F4 | 例外 | 同 TC-140，但工作是 23 小時前成功結束 | 同上 | 仍被拒絕，同一句；沒有任何變動 | 自動 |
| TC-142 | F4 | 功能 | 同 TC-140，但工作是 25 小時前成功結束，run 索引仍沒有 R1 | 擁有者要求 `forget R1`，同意 | 允許（當成從沒進過索引，同 R15）；內容被清掉，稽核保留，有 `forgotten_at` | 自動 |
| TC-143 | F4 | 功能 | R1 的啟動工作 1 小時前成功結束，這時 run 索引已經看到 R1 且狀態是 succeeded | 擁有者要求 `forget R1`，同意 | 允許（不必等 24 小時）；內容被清掉 | 自動 |
| TC-144 | F4；R7 | 例外 | 同 TC-143，但索引裡 R1 的狀態是 running | 擁有者要求 `forget R1` | 被拒絕（還在跑），沒有任何變動 | 自動 |
| TC-145 | F4（R15 不變） | 功能 | R1 的啟動工作 1 分鐘前剛被代理拒絕（另兩次：剛失敗 `error`、剛逾時 `expired`），R1 從沒進過索引 | 擁有者對各次要求 `forget R1`，同意 | 三種都立刻允許，不必等 24 小時，也不答「還在準備中」 | 自動 |
| TC-146 | F4；R5 | 例外 | 同 TC-140 | 在終端機執行 `abf-platform forget R1` | 同樣被拒絕，同一句「還在準備中」；資料庫一個字都沒變 | 自動 |
| TC-147 | F7 | 功能 | R1 的啟動確實送出過（確認紀錄在），但它的啟動工作列早已被清掉（刪掉那一列來造出這種舊資料），run 索引裡沒有 R1（`get_run` 回 found:false） | 擁有者要求 `forget R1`，同意 | 允許：不是「這個 run 還在準備中」，也不是「查無」，也不是程式錯誤；R1 在確認紀錄裡能被找到的內容被清掉並有 `forgotten_at`，稽核欄位保留 | 自動 |

## User Story 10 — 不論哪個管道確認的送出，內容都保留到使用者刪除（優先度 P1）

這一段對應 F5 與 F11。他的原話：「送出內容除非使用者刪除不然不刪」。以前終端機確認的啟動，唯一一份內容在 7 天就被清的工作副本裡。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-150 | F5 | 功能 | 一個使用者在終端機看完畫面，輸入 `y` 確認一個啟動 | 確認完成後讀 `confirmations` 那一列 | 該列 `bundle_json` 是剛才確認的內容（與送出的 bundle 一字不差），`screen_text` 是當時畫面上讓他同意的文字，`state` 是 `confirmed`、`channel` 是 TERMINAL | 自動 |
| TC-151 | F5 | 功能 | 同 TC-150 | 讀那一列 | 存起來的 bundle 算出的 sha256 等於該列的 `sha256`（內容與使用者同意的雜湊一致） | 自動 |
| TC-152 | F5（不變的部分） | 功能 | 一個啟動由 MCP 表單確認，另一個由確認網頁確認 | 兩者確認之後讀各自的 `confirmations` 列 | 兩列都有 bundle 與畫面文字（維持現狀） | 自動 |
| TC-153 | F5；例子 1 | 功能 | 一筆終端機確認的啟動，400 天前確認 | 之後任何人呼叫一次 `create_pending` | 這列的 bundle 與畫面文字都還在 | 自動 |
| TC-154 | F5；R16（一） | 功能 | 一筆終端機確認的啟動，它的工作 8 天前就結束 | 之後再排入一個新工作（會清掉結束超過 7 天的工作列） | 舊工作列被清掉（現行行為保留），但終端機確認那一列的 bundle 與畫面文字還在 | 自動 |
| TC-155 | F5；規則 3 | 功能 | 一個終端機確認的 run R1，已結束；確認紀錄與工作都有內容 | `forget R1` 並答 `y` | 確認紀錄的內容與工作副本都被清掉，稽核欄位保留，兩處都有 `forgotten_at` | 自動 |
| TC-156 | F5；009e | 功能 | R1 是終端機確認的啟動，已失敗；它的啟動工作 10 天前結束、已被清掉 | 擁有者要求續跑 R1 並按「是」 | 成功進入確認並排入續跑工作；內容取自確認紀錄；不是「太久了」 | 自動 |
| TC-157 | F5；009e | 功能 | 同 TC-156 | 擁有者要求重跑 R1 並按「是」 | 成功排入重跑工作；樣本表與參數與 R1 當時的一字不差；不是「太久了」 | 自動 |
| TC-158 | F5（舊格式的列，工作還在） | 功能 | R1 是舊格式的列（確認紀錄沒有內容、也沒被 `forget` 過），它的啟動工作還在（未滿 7 天），R1 已失敗 | 擁有者要求續跑 R1 | 照 009e 原樣從工作副本取內容，成功進入確認 | 自動 |
| TC-159 | F5（舊格式的列，工作已被清掉） | 例外 | 同 TC-158，但啟動工作已超過 7 天被清掉 | 擁有者要求續跑 R1 | 回答「太久了，這次送出的內容已經清掉，請當成新分析重新送出」；沒有排任何工作 | 自動 |
| TC-160 | F5（同上，重跑） | 例外 | 同 TC-159 | 擁有者要求重跑 R1 | 同 TC-159 的「太久了…」；沒有排任何工作 | 自動 |
| TC-161 | F5（不改壞原本的啟動） | 功能 | 使用者在終端機確認一個啟動 | 確認完成後看 `confirmations` 與 `jobs` | 恰好新增一筆確認紀錄與一筆啟動工作，工作的 `confirmation_id` 指向這筆確認；與沒有這項改動時的行為相同 | 自動 |
| TC-162 | F11 | 功能 | 一個使用者在終端機看完畫面，輸入 `y` 確認一個取消（cancel） | 確認完成後讀 `confirmations` 那一列 | 該列 `bundle_json` 是剛才確認的取消內容（指名那個 run，與送出的 bundle 一字不差），`screen_text` 是當時畫面上讓他同意的文字，`state` 是 `confirmed`、`channel` 是 TERMINAL，sha256 與存起來的 bundle 一致 | 自動 |
| TC-163 | F11；規則 1 | 功能 | 一筆終端機確認的取消，400 天前確認 | 之後任何人呼叫一次 `create_pending` | 這列的 bundle 與畫面文字都還在 | 自動 |
| TC-164 | F11；R16（一） | 功能 | 一筆終端機確認的取消，它的取消工作 8 天前就結束 | 之後再排入一個新工作（會清掉結束超過 7 天的工作列） | 舊工作列被清掉（現行行為保留），但終端機確認那一列的 bundle 與畫面文字還在 | 自動 |
| TC-165 | F11；規則 3；R9 | 功能 | R1 已結束，另有一筆終端機確認的取消（指名 R1），確認紀錄有內容 | 擁有者 `forget R1` 並答 `y` | 這筆取消確認紀錄的 bundle 與畫面文字被清掉，稽核欄位保留，有 `forgotten_at` | 自動 |

## 不在範圍（計畫「Out of scope」與相關禁止事項）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 不在範圍：刪除叢集上的結果 | 不在範圍 | R1 已結束，叢集端有 `rawdata`／`results`／`analysis` | `forget R1` 並同意 | 沒有任何工作被排進 `jobs`（任何種類都沒有新增），叢集端沒有任何刪除動作；`forget` 只動這個資料庫裡的內容 | 自動 |
| TC-081 | 不在範圍：從 run 清單刪 run | 不在範圍 | R1 已結束，在 run 清單裡 | `forget R1` 並同意 | R1 仍在 run 清單裡，`get_run` 仍找得到它，狀態與原來相同 | 自動 |
| TC-082 | 不在範圍：任何網頁介面；規則 5 | 不在範圍 | 網頁服務（唯讀） | 檢查網頁的路由，並對網頁送出一個 forget 的請求 | 網頁沒有任何刪除按鈕或 forget 路由；請求得到「找不到」或被拒，R1 沒變 | 自動 |
| TC-083 | R2；R8（不動既有的確認機制） | 不在範圍 | 程式碼 | 讀 `confirm.JOB_KIND` 與 `confirmations.kind` 的 CHECK 限制 | `JOB_KIND` 仍只有 launch、cancel 兩項，`kind` 的 CHECK 仍只允許 `'launch'`、`'cancel'`，`confirm.approve` 沒有為 forget 加分支（009e 的續跑與重跑本來就用 `launch`，也沒有新增種類） | 自動 |
| TC-084 | 規則 4；F1；F10（改寫：009e 現在進來了，守住「不去改它」） | 不在範圍 | 本分支相對 `origin/v3` 的差異 | 看 `git diff origin/v3...HEAD` 裡 009e 的檔案（`abf_station/launch.py`、`build.py` 的續跑與重跑部分、`jobs.py` 的世系部分、`status.py` 等） | 對 009e 程式的改動只有四類：F2 的「已刪除就拒絕」、F5 的「先讀確認紀錄、舊格式才退回讀工作副本」、F3 加上 `forget` 到清單與數量、F10 的「`forget` 完成時把指向該 run 的等待中續跑／重跑申請作廢」；沒有改變續跑或重跑的確認流程、三個確認管道、`LAUNCH_ALLOW` 的唯一提交檔、資料夾規則（續跑只寫 `head-N.sh` 與 `tower.token`）；沒有為 `forget` 新增第二個提交路徑 | 自動（驗收者讀 diff） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-090 | 第 2 條（不得留第二份 run 狀態） | 功能 | 這個分支 | 執行 `bash tests/no_second_run_state_test.sh` | 通過；新增的 `forgotten_at`、`forgotten_by` 只記「內容被刪」這件稽核事實，不記 run 的狀態，檢查沒有被放寬；F4 的「還在準備中」沒有新增任何儲存的狀態（見 TC-097） | 自動：`tests/no_second_run_state_test.sh` |
| TC-091 | 安全網：啟動前必須有人確認 | 例外 | 沒有人確認的啟動請求 | 透過 MCP 與網頁各送一次未確認的啟動 | 仍然都被拒絕（`test_human_channel.py` 的 `test_tch09_*`、`test_confirm_page.py` 的 `test_tch09_b_c_*` 通過且未被修改）；`forget` 沒有開出新的送出路徑 | 自動：`tests/platform_test.sh` |
| TC-092 | 安全網：不刪使用者原始資料（`rawdata/`、`results/`、`analysis/`） | 功能 | R1 在叢集與本機有這三類資料夾 | `forget R1` 並同意 | 這些資料夾與裡面的檔案一個都沒少（見 TC-080 沒有排任何工作） | 自動 |
| TC-093 | 開發流程：不得放寬舊測試（改寫：基準改為合併後的 `origin/v3`；F8、F9 點名） | 功能 | diff 裡所有被修改的測試檔 | 逐檔對照 `origin/v3`（本任務自己的改動）與 main | 除了這些有名字的改動，沒有任何斷言被刪除、放寬、跳過或把預期值改成配合新輸出：R1（TC-010、TC-040）、R14 與 F3（TC-094、TC-095、TC-104、TC-105、TC-108、TC-113）、F8（TC-114：釘住 ask 清單的測試改成五個名字，原本四個名字的斷言仍在）；每一處都只是「加上 `forget`」、「加上 `forgotten_at`／`forgotten_by` 欄位名」或「數量加 1」。唯一另外允許的是 F9 點名的：009e 的兩個「太久了」測試（續跑、重跑）只能改前置資料成「舊格式的列」，斷言一字不動，並在 ledger 逐一列出（TC-115）。合併衝突解決後的測試檔，兩個父提交的斷言都在（沒有任一邊被丟掉）。`spec.md`、`test-case*.md` 沒有在實作期間被編輯 | 自動（驗收者對照差異） |
| TC-094 | R14（`test_station_envs.py` 的禁字掃描） | 例外 | `platform/tests/test_station_envs.py` 的 `banned_schema_words` 掃描（欄位名含禁字如 `org` 就失敗） | 讀這個掃描與它的允許名單，並用一個虛構欄位名 `forgotten_org` 餵給它 | 允許名單只多了剛好 `forgotten_at` 與 `forgotten_by` 兩個確切名字；`forgotten_org`（或任何其他含禁字的名字）仍然失敗，且有一條斷言證明這點；掃描的其他部分沒變 | 自動（`platform/tests/test_station_envs.py`；驗收者對照差異） |
| TC-095 | R14；F3（改寫：基準是 v3，數量 10 變 11） | 功能 | `test_station_envs.py`、`test_pat.py`、`test_oauth_mcp.py`、`test_mcp.py`、`test_launch_e2e.py`、`test_launch_platform.py` 裡的工具清單、數量、指令集合與說明文字 | 逐處對照 `origin/v3` | 每一處只有兩種變動：清單或指令集與說明文字多了 `forget`、工具數量從 v3 的數字加 1（10 變 11）；其餘一個字不變（包括 009e 加的 `resume`、`relaunch`）；這些測試在合併後的程式上通過 | 自動（驗收者對照差異；測試本身隨 `bash tests/platform_test.sh`） |
| TC-096 | 安全網：每一次提交都要人按「是」；F2/F4/F5 沒開新路 | 例外 | 這個分支 | 跑 009e 的 `test_unconfirmed_resume_is_refused`、三個確認管道的單例測試與 `tests/no_second_run_state_test.sh` 的唯一提交檔檢查 | 全部通過且未被修改；F2 的拒絕路徑、F4 的拒絕、F5 多寫的確認紀錄內容，都沒有讓任何沒有人確認的內容被送出 | 自動：`tests/platform_test.sh` |
| TC-097 | 第 2 條（Nextflow 的紀錄才是真相）；F4 | 功能 | `platform/abf_platform/store.py` 的欄位清單，與 `forget` 判斷「還在準備中」的程式 | 讀 | 除了 `forgotten_at`、`forgotten_by` 之外沒有新增任何欄位；「還在準備中」與 24 小時是從既有的資料（工作列的狀態與結束時間，加上 run 索引）當場算的，沒有存任何「準備中」旗標 | 自動 |
