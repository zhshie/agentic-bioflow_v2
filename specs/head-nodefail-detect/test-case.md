# 測試案例：Slurm 主任務被排程器終結（NODE_FAIL 等）時，平台顯示 Failed 並說出排程器狀態

**規格**：`specs/head-nodefail-detect/plan.md`（本任務沒有獨立 spec.md，計畫即規格；「對應需求」欄寫的是計畫的段落）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞（一行說明）：「head job」＝送去 Slurm 排程器、負責啟動整條分析的那個主任務；「完成紀錄」＝Nextflow 自己寫下的「這個 run 結束了」的紀錄（平台的真相來源）；「lost」＝送出後超過 3×60 秒沒有任何完成紀錄，平台原本只能顯示「失聯」；「站台」＝在叢集上替平台執行唯讀指令的程式；「抓取」＝平台請站台讀一次 run 資料夾的唯讀工作（`fetch_run_records`）；「事實」＝抓取結果裡的 `scheduler` 欄（排程器對該 head job 的回答）；「終結壞狀態」＝計畫作法 3 表格內的九種：NODE_FAIL、BOOT_FAIL、CANCELLED、TIMEOUT、OUT_OF_MEMORY、FAILED、DEADLINE、PREEMPTED、REVOKED；「覆蓋層」＝查詢時把 lost 的 run 疊顯示成 Failed 的那一層（不寫回索引）。

測試檔：平台端 `platform/tests/test_head_nodefail.py`；站台端 `platform/tests/test_station_head_state.py`。每個自動測試要在註解寫出自己的 TC 編號。

## User Story 1 — 被排程器終結的 head，網頁／MCP 看到 Failed 並說出原因（優先度 P1）

維護者原話 4（handoff 11-01-2104 待辦第 2 點）：「平台偵測不到 head job NODE_FAIL（t1 job 78／Slurm 654018 整個看不到，站台 log 只寫 "job 78: done"）」→ 對應 TC-001。維護者原話 2：run 只有 Running／Done／Failed 三態，lost 顯示為 Failed。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；維護者原話 2、4（重現 t1）；作法 5 | 功能 | 重現 t1：一個 run 已送出（平台 job 78、Slurm 工作編號 654018）；索引裡沒有任何 Nextflow 完成紀錄；已超過 `LOST_AFTER_SECONDS`（索引狀態是 lost）；該 run 最新一筆已完成的抓取結果是 `scheduler = {"job_id":"654018","state":"NODE_FAIL","source":"sacct"}` | 擁有者對這個 run 呼叫 `get_run` | 回傳的 `status` 是 `failed`（網頁顯示 Failed，不是失聯）；`failure.failure_reason` 恰為 `Slurm head job 654018 ended as NODE_FAIL (sacct)`（含狀態字 NODE_FAIL 與工作編號） | 自動：`platform/tests/test_head_nodefail.py` |
| TC-002 | 維護者原話 1；作法 5 | 功能 | 同 TC-001 | 擁有者呼叫 `get_run`，看 `failure` 欄 | `failure` 仍恰是原本那五個鍵（`status_seqera`、`failed_tasks`、`failure_reason`、`log`、`actions`），沒有新增鍵；`status_seqera == "failed"`；`actions` 含「續跑（resume）」與「重送（relaunch）」，內容與一般 failed 的 run 相同 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-003 | 作法 3 單一表格（終結壞狀態） | 功能 | 同 TC-001，但把抓取結果的狀態逐一換成表格內九種：NODE_FAIL、BOOT_FAIL、CANCELLED、TIMEOUT、OUT_OF_MEMORY、FAILED、DEADLINE、PREEMPTED、REVOKED（來源 sacct 或 squeue 各至少涵蓋一次） | 對每一種呼叫 `get_run` | 每一種都得到 `status == "failed"`、`status_seqera == "failed"`，原因句為 `Slurm head job <工作編號> ended as <該狀態> (<來源>)`，句中是它自己的狀態字；`actions` 含續跑與重送 | 自動：`platform/tests/test_head_nodefail.py`（參數化） |
| TC-004 | 作法 5（`get_run`、`list_runs` 共用同一個疊加函式） | 功能 | 同 TC-001 | 擁有者呼叫 `list_runs` | 清單中該 run 的 `status` 為 `failed`，其 `failure.failure_reason` 與 TC-001 同一句；疊加邏輯只在動作層一份（路由處理函式沒有第二份） | 自動：`platform/tests/test_head_nodefail.py` |

## User Story 2 — 「被問到時才問一次」，不是常駐監控（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-005 | 作法 6；作法 1；維護者原話 3（不新增常駐程式） | 功能 | 一個 lost 的 run，其發送紀錄有 Slurm 工作編號，且沒有新鮮（< 60 秒）的已完成或排隊中的抓取 | 擁有者連叫兩次 `get_run`；之後再叫一次 `list_runs` | 工作佇列裡只多出一個 `fetch_run_records` 抓取，且它帶著 `slurm_job_id`；`list_runs` 沒有排任何工作；沒有別種工作被排入 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-006 | 作法 6（抓取完成後下一次 `get_run` 就會看到疊加） | 功能 | 一個 lost 的 run，尚無抓取結果 | 第一次 `get_run`（此時排出抓取）；站台完成該抓取，結果為 NODE_FAIL；再 `get_run` 一次 | 第一次與 v3 相同（`lost`）；第二次出現 `failed` 與含 NODE_FAIL 的原因句 | 自動：`platform/tests/test_head_nodefail.py` |

## User Story 3 — 站台只在「沒有完成紀錄」時才問排程器，且不信任、不猜（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | 作法 2（sacct 狀態與正規化） | 功能 | 假站台：假 sbatch 送出後，狀態檔把該 job 設為終結狀態（squeue 查不到、sacct 有結果），run 資料夾的 log 沒有完成行。逐一用 `NODE_FAIL`、`CANCELLED by 1234`、`TIMEOUT`、`OUT_OF_MEMORY` | 對每一種呼叫 `fetch_run_records`，帶 `slurm_job_id` | 回傳 `scheduler == {"job_id":"<id>","state":"<STATE>","source":"sacct"}`，其中 `CANCELLED by 1234` 的尾巴被去掉、得到 `CANCELLED`；狀態全為大寫 | 自動：`platform/tests/test_station_head_state.py`（參數化） |
| TC-008 | 作法 2（有完成紀錄時完全不呼叫）；維護者原話 3 | 功能 | 假站台：log 有完成行；假 squeue、假 sacct 各有呼叫計數 | 呼叫 `fetch_run_records`，帶 `slurm_job_id` | `scheduler` 為 None；假 squeue 與假 sacct 的呼叫次數都是 0 | 自動：`platform/tests/test_station_head_state.py` |
| TC-009 | 作法 2（squeue 先問、仍在佇列就不問 sacct）；作法 3（活著的狀態） | 功能 | 假站台：log 沒有完成行；假 squeue 對該工作編號回 `RUNNING` | 呼叫 `fetch_run_records`，帶 `slurm_job_id` | `scheduler.state == "RUNNING"`、`source == "squeue"`；假 sacct 沒被呼叫 | 自動：`platform/tests/test_station_head_state.py` |
| TC-010 | 作法 2、「不做」第 5 條（不猜） | 例外 | 假站台：log 沒有完成行；squeue 查不到；sacct 結束碼非 0（或兩者都查不到工作） | 呼叫 `fetch_run_records`，帶 `slurm_job_id` | `scheduler is None`；不丟例外；抓取工作本身仍成功回報其餘內容 | 自動：`platform/tests/test_station_head_state.py` |
| TC-011 | 作法 2、8（只接受純數字）；既有行為（未知參數被拒） | 例外 | 假站台已就緒，並記錄收到的所有指令 | (a) 呼叫 `fetch_run_records`，`slurm_job_id="1; rm -x"`；(b) 呼叫帶一個 `fetch.ARGS` 以外的未知參數 | (a) 被拒絕，假站台沒有收到任何指令；(b) 仍被 `handlers` 拒絕（既有行為不變）；`fetch.ARGS` 原有三個鍵仍在，新增 `slurm_job_id` | 自動：`platform/tests/test_station_head_state.py` |

## User Story 4 — 不誤判：活著的、已完成的、偽造的，都不能被標成失敗（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 作法 3（活著的狀態：不可把還在排隊或執行的 head 標成失敗） | 例外 | 一個 lost 的 run，最新抓取事實的狀態逐一為 RUNNING、PENDING（並涵蓋 COMPLETING、REQUEUED、SUSPENDED、CONFIGURING） | 對每一種呼叫 `get_run` 與 `list_runs` | 全都不疊加：run 維持 v3 的原樣（`lost`、原因 None），`actions` 不含續跑（`relaunch` 沿用 v3 原樣，維護者裁決 11-03：lost 仍可重送） | 自動：`platform/tests/test_head_nodefail.py`（參數化） |
| TC-013 | 作法 3（COMPLETED 但無完成紀錄） | 例外 | 一個 lost 的 run，抓取事實為 `COMPLETED` | `get_run`，再嘗試續跑 | 狀態維持 `lost`；原因句為 `Slurm head job <id> completed but Nextflow left no completion record`；`actions` 不含續跑；續跑被拒 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-014 | 作法 4、8（站台回傳是不可信資料）；作法 3（不認得的狀態不疊加）；裁決 P2 修訂（11-04） | 例外 | 一個 lost 的 run，分別有三種抓取結果：(a) 事實的 `job_id` 與該 run 發送紀錄的 `slurm_job_id` 不符；(b) 狀態不在允許清單；(c) 狀態字串過長／型別不對；另有一個情況 (d) 較舊的抓取是 NODE_FAIL、但較新的一筆已完成的抓取事實是 RUNNING（或 PENDING）（較新一筆是 `scheduler=None` 的情況改由 TC-031 負責） | 對每一種呼叫 `get_run` | 全部不疊加（維持 v3 的 lost、原因 None）；失敗原因句不含該偽造內容；(d) 以較新的活著事實為準，不疊加（與裁決 Q1 一致，詳見 TC-037） | 自動：`platform/tests/test_head_nodefail.py`（參數化） |

## User Story 5 — 續跑／重送閘門放行「確定被終結」的 lost run（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 作法 7 | 功能 | 一個 lost 的 run，其 `head_state` 是終結壞狀態（如 NODE_FAIL） | 對它走續跑的前置檢查（`build._predecessor`） | 放行，視同 failed 通過 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-016 | 作法 7（其他 lost 仍被拒）；既有 `test_a_run_that_is_lost_is_not_one_that_has_ended` 逐字不變 | 例外 | 一個 lost 的 run，沒有抓取事實（或事實是 COMPLETED、RUNNING、被偽造） | 對它走續跑的前置檢查 | 仍被拒絕，用的是既有那句拒絕的話（與 v3 逐字相同）；既有被釘住的測試未被刪改 | 自動：`platform/tests/test_head_nodefail.py` 與既有 `test_resume_platform.py` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 原則 I.2（Nextflow 紀錄為真相；`tests/no_second_run_state_test.sh`）；維護者原話 3 | 功能 | 一個 run 有 Nextflow 完成紀錄（成功），同時有一筆抓取事實 NODE_FAIL | `get_run` 與 `list_runs` | 狀態仍是成功（succeeded），不疊加、無失敗原因；有任何完成紀錄的 run 都不走疊加路徑 | 自動：`platform/tests/test_head_nodefail.py`；並 `tests/no_second_run_state_test.sh` 維持綠 |
| TC-018 | 原則 I.2（索引不是第二份真相；`test_tc030_*`／`test_tc031_*`）；計畫「不寫回索引」 | 功能 | 一個疊加成立的 lost run；記下呼叫前 runs 索引內該 run 的資料列 | 連續 `get_run`、`list_runs` | runs 索引內容與呼叫前完全相同（儲存的狀態仍是 lost）；沒有新表、新檔存放排程器狀態（抓取結果只留在既有的工作結果裡）；`test_nextflow_e2e.py` 的 `test_tc030_*`、`test_tc031_*` 維持綠 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-019 | 專長守則：擁有者規則；Safety Net（寫入工具皆須人工確認） | 例外 | 兩位使用者 A、B；A 有一個 lost 且事實為 NODE_FAIL 的 run | B 用自己的身分對 A 的 run 呼叫 `get_run`，並呼叫 `list_runs` | `get_run` 回「找不到這個 run」（`found: False`），不洩漏疊加後的原因；`list_runs` 看不到 A 的 run；B 的呼叫沒有替 A 的 run 排任何抓取。（本案不新增任何寫入動作，故沒有「寫」的對應案例；見 TC-023 的對等性檢查） | 自動：`platform/tests/test_head_nodefail.py` |
| TC-020 | 專長守則：錯誤訊息與日誌；Safety Net（憑證不外露）；計畫作法 8 | 例外 | 假站台的 sacct 回出惡意或雜亂的內容：多行、很長、含看起來像路徑（如 `/home/x/...`）或 token 的字串、非允許清單的狀態 | 呼叫 `fetch_run_records` 帶 `slurm_job_id`，再由平台 `get_run` | 站台回傳的 `scheduler` 是 None 或只含允許清單內的狀態字，不含那段原文；平台顯示的原因句、站台日誌與回應都不含密鑰（token）與內部路徑；原因句說明發生了什麼事（排程器狀態）與可做的事（續跑／重送） | 自動：`platform/tests/test_station_head_state.py` 與 `platform/tests/test_head_nodefail.py` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 「不做」第 5 條：`squeue`／`sacct` 都查不到的 head（`scheduler=None`）維持 lost | 不在範圍 | 一個 lost 的 run：沒有任何抓取結果，或所有抓取的 `scheduler` 都是 None（沒有任何較早的終結壞狀態事實） | `get_run` 與 `list_runs` | 與 v3 逐字相同：`failure` 的 `status_seqera` 為 `unknown`、`failure_reason` 為 None；續跑依舊被擋；沒有被猜成失敗 | 自動：`platform/tests/test_head_nodefail.py`（並維持 `test_failures.py` 第 64～72 行等被釘住的斷言為綠） |
| TC-022 | 「不做」第 3 條：送出後索引根本沒有該 run，本片不處理 | 不在範圍 | 一次 Slurm 送出已有發送紀錄，但索引裡從未出現該 run（沒有任何 Nextflow 事件） | `get_run` 該 run，並 `list_runs` | 仍是「找不到這個 run」，清單不列它；沒有因此替它建立 run 列、也沒有疊加；程式沒有宣稱支援這種情況 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-023 | 「不做」第 4 條：不新增 job 種類、migration、狀態機、常駐監控；不寫回 runs 表；不改 MCP 工具介面與網頁字串 | 不在範圍 | 本案完成後的程式 | 比對 `jobs.KINDS` 與 `handlers.JOB_KINDS`、`migrations/` 目錄、動作層函式清單與 `list_runs`／`get_run` 的對應清單、MCP 工具清單 | `jobs.KINDS`／`handlers.JOB_KINDS` 與 base 相同（既有整組相等測試維持綠）；沒有新增 migration 檔；動作層與使用者可見動作的一一對應不變（對等性測試維持綠，兩邊同時列舉）；`get_run` 排出的只有唯讀的 `fetch_run_records`，不經確認就不會建立任何寫入類工作；無新增狀態值或常駐程式 | 自動：`platform/tests/test_head_nodefail.py` 與既有 `test_byte_channel_a.py`、`test_byte_channel_b.py`、`test_cleanup_store.py`、`test_launch_platform.py`、`test_resume_scope.py`、`test_station_platform.py`、`test_actions_layer.py` |
| TC-024 | 「不做」第 1、2 條：不排除壞節點（25a-cpn01／02／04／05）；不在國網真機重跑 | 不在範圍 | 本案的 `git diff --stat` | 閱卷者讀 diff 與 ledger | diff 沒有任何計算環境設定、節點排除或 `--exclude` 類改動；ledger 註明「國網真機重跑為手動驗收待辦」，由維護者／操作員日後親手開 ControlMaster（2FA）驗收；executor 沒有連線任何站台 | 手動：`docs/TESTING.md`（本案須在其手動段新增「真站台 NODE_FAIL 重跑驗收」一條，只加不改） |

## 文件與驗收備忘

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 範圍：文件（`docs/PLATFORM.md` 的「Failed runs」段與 lost 狀態說明；`docs/PITFALLS.md` 新增一條） | 功能 | 本案完成後的文件 | 閱卷者讀這兩份文件 | `docs/PLATFORM.md` 說明：排程器終結的 head 會顯示 Failed 並寫出排程器狀態、COMPLETED 無紀錄仍是 lost 要人看、僅在被問到時查一次；`docs/PITFALLS.md` 新增一條「排程器終結的 head 不會留下 Nextflow 紀錄」，寫的是量到的現象（t1／Slurm 654018）而非推測 | 手動：`docs/TESTING.md`（新增的手動步驟，只加不改） |

## 對抗審追加（Opus，11-03；計畫裁決 O）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 裁決 O(1)：限流算任何狀態 | 例外 | 一個 lost 的 run，其 head-state 抓取依序以 refused、error、expired 結束（各測一次） | 5 秒內對該 run 連續呼叫 get_run 5 次 | 該 run 的 fetch_run_records 列總數為 1，不是 5；另測兩個同時的 get_run 只排 1 筆 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-027 | 裁決 O(2)：舊站台代理相容 | 功能 | 一般 `enqueue_fetch`（CLI `abf-launch fetch` 路徑）；以及 head-state 查詢 | 比對兩條路徑送出的 args 鍵 | 一般路徑鍵集合恰為 {ce, run_name, run_folder}；只有 head-state 路徑多 slurm_job_id；head-state 被 refused 時 run 維持 lost | 自動：`platform/tests/test_head_nodefail.py` |
| TC-028 | 裁決 O(3)：LIMIT 順序 | 功能 | run x 有 30 秒前的 NODE_FAIL 事實；同一運算環境上 run y 之後又有 100 筆新抓取 | 對 x 呼叫 get_run 與 list_runs | 兩者都顯示 failed，不是 lost | 自動：`platform/tests/test_head_nodefail.py` |
| TC-029 | 裁決 O(4)：log 超過 20 MB | 例外 | lost 的 run，.nextflow.log 超過 20 MB 被截斷、沒有完成行，排程器回 NODE_FAIL | get_run | 仍會問排程器並顯示 failed | 自動：`platform/tests/test_station_head_state.py` 與 `platform/tests/test_head_nodefail.py` |

## 裁決 P 修正輪（/code-review 對 PR #318，11-04）

每項先寫會失敗的測試，再修。TC-035 是修正輪的第一步與收尾條件。TC-032 因裁決 Q1 修訂了裁決 P3 而改寫（見該列）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 裁決 P1：沒問排程器的普通抓取不得蓋掉較早的 NODE_FAIL 事實 | 功能 | 一個 lost 的 run（發送紀錄工作編號 654018）；較早一筆已完成的抓取結果帶 `scheduler = {"job_id":"654018","state":"NODE_FAIL","source":"sacct"}`；之後同一個 run 又有一筆已完成的普通抓取（例如 `abf-launch fetch` 路徑），其結果沒有 `scheduler` 鍵 | 擁有者呼叫 `get_run` 與 `list_runs` | 兩者都仍是 `status == "failed"`，原因句仍恰為 `Slurm head job 654018 ended as NODE_FAIL (sacct)`；`head_state` 只採「結果帶 scheduler 鍵、且是這個 run 的」抓取中最新的一筆 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-031 | 裁決 P2：站台這次問不到＝沒有新事實，不得以 scheduler=None 覆蓋已有的終結壞狀態 | 例外 | 一個 lost 的 run；較早一筆已完成的抓取事實是 NODE_FAIL（工作編號與發送紀錄相符）；較新一筆已完成的抓取是 `scheduler = None`（squeue 與 sacct 都失敗、查無或連線斷線） | 擁有者連續多次呼叫 `get_run` 與 `list_runs`（其間再加入更多 `scheduler=None` 的新抓取） | 每一次都仍是 `status == "failed"` 且原因句含 NODE_FAIL 與工作編號；從頭到尾沒有在 Failed 與 lost 之間來回 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-032（裁決 Q1 改寫，原為「已有終結事實就不再每分鐘重問」） | 裁決 Q1（修改裁決 P3）：有終結事實的 run，每 10 分鐘最多再問排程器一次 | 功能 | 一個 lost 的 run，有 Slurm 工作編號；最新有效事實是終結壞狀態（如 NODE_FAIL），該抓取是 90 秒前完成的（已超過 60 秒、未滿 10 分鐘） | 擁有者呼叫 `get_run` 兩次、`list_runs` 一次 | 該 run 的 `fetch_run_records` 列總數沒有增加（沒有排新的抓取）；三次都是 `failed`，原因句不變 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-033 | 裁決 P3：caller 為 None 時不得替任何人排站台工作 | 例外 | 一個 lost 的 run，有 Slurm 工作編號，且沒有新鮮的抓取（照 TC-005 本來會被排一個抓取的情況） | 以 caller 為 None 呼叫 `get_run` | 工作佇列沒有多出任何 `fetch_run_records`（也沒有其他種類的工作）；不丟例外 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-034 | 裁決 P4：輪替的日誌缺 `_STARTED` 標記時，不得把第一次嘗試的 NODE_FAIL 靜默丟掉，寧可問排程器 | 例外 | 假站台：run 資料夾的目前 `.nextflow.log` 有完成行（例如續跑的那次）；另有輪替檔 `.nextflow.log.1` 沒有「看得出真的跑過」的啟動標記、也沒有完成行；假 sacct 對該工作編號回 `NODE_FAIL` | 呼叫 `fetch_run_records`，帶 `slurm_job_id` | 站台仍詢問排程器（假 squeue 或假 sacct 呼叫次數至少 1），回傳的 `scheduler` 含 `NODE_FAIL`；沒有因為目前的 log 有完成行就跳過詢問。對照：TC-008（所有 log 都看得出真的跑過且都有完成行）仍是 0 次呼叫 | 自動：`platform/tests/test_station_head_state.py` |
| TC-035 | 裁決 P5、P6：修正輪第一步先 `git merge origin/v3`（不 rebase、不 force push），解完衝突、全套先綠，再做 1–4 | 功能 | 修正輪完成後的分支 | 閱卷者執行 `git merge-base --is-ancestor origin/v3 HEAD`、查看歷史有無合併提交、比對被釘住的既有測試與 base | origin/v3 是 HEAD 的祖先；歷史中有合併提交（不是 rebase 重寫）；被釘住的既有測試（計畫「允許的斷言」）只增不減、未放寬；TC-030～034 每一項都有自己的新測試，且各自在修正前會失敗（RED 提交先於 GREEN 提交） | 閱卷者查 git 紀錄與 diff（不是產品行為，不需寫入 `docs/TESTING.md`）；全套綠由 GATE 完成記號證明 |

TC-036 保留不用（裁決 Q4：新測試編號從 TC-037 起，避免與 TC-035 撞名；程式碼中原標 TC-035／TC-036 的兩處註解改成 TC-037／TC-038）。

## 裁決 Q（/code-review 第二次對 PR #318，11-04）

每項先寫會失敗的測試，再修。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | 裁決 Q1：壞結束事實不是永久的（Slurm 可能把 NODE_FAIL 的任務重新排隊而再度 RUNNING）；最新一筆真實排程器答案為準 | 功能 | 一個 lost 的 run（發送紀錄工作編號 654018）；較早一筆已完成的抓取事實是 NODE_FAIL（`job_id` 相符）；較新一筆已完成的抓取事實是 `RUNNING`（另以 `PENDING` 各測一次，工作編號相符）；兩筆都是真的排程器答案（帶 `scheduler`、非 None） | 擁有者呼叫 `get_run` 與 `list_runs` | 兩者都不再顯示 Failed：`status` 回到 lost 的原樣（失聯）、`failure_reason` 為 None；`actions` 不含續跑（resume），也沒有覆蓋層加上的重送——實際 `actions` 與一個沒有任何事實的普通 lost run 完全相同（v3 釘住的 lost 行為，見總覽「不確定」第 8 點）。對照：把兩筆順序反過來（先 RUNNING、後 NODE_FAIL）則顯示 Failed | 自動：`platform/tests/test_head_nodefail.py`（參數化 RUNNING／PENDING；程式碼註解原 TC-035 改標 TC-037） |
| TC-038 | 裁決 Q2：被覆蓋層顯示成 Failed 的 run 沒有 ended_at，所有「Ended」欄位要用與失敗通知相同的備用時間（`last_message_at` 或事實時間） | 功能 | 一個被覆蓋層顯示成 Failed 的 run（NODE_FAIL 事實成立，run 沒有 `ended_at`）；失敗通知對這個 run 用的備用時間為 T | 在網頁看板（`web_board`）與其他顯示「Ended」的地方讀這個 run | 每一個「Ended」欄位都顯示 T（與失敗通知所用的同一個備用時間），沒有任何一處顯示「—」 | 自動：`platform/tests/test_head_nodefail.py`（或 web_board 相關測試檔，檔名由 executor 定，註解寫 TC-038；程式碼註解原 TC-036 改標 TC-038） |
| TC-039 | 裁決 Q2：耗時不得持續增加 | 功能 | 同 TC-038 | 在時間 t1 讀看板上這個 run 的耗時（`_duration`），把時鐘往後撥 1 小時，再讀一次 | 兩次耗時相同（等於備用時間 T 減去開始時間），沒有隨現在時間增加 | 自動：`platform/tests/test_head_nodefail.py`（或 web_board 相關測試檔；註解寫 TC-039） |
| TC-040 | 裁決 Q1：每 10 分鐘最多再問一次 | 功能 | 一個 lost 的 run，有 Slurm 工作編號；最新有效事實是 NODE_FAIL，該抓取是 11 分鐘前完成的（事實年齡未滿 6 小時） | 擁有者呼叫 `get_run`，緊接著再呼叫一次 `get_run` | 第一次呼叫排出恰好一個 `fetch_run_records` 抓取且帶 `slurm_job_id`；緊接著的第二次沒有再排新的；兩次都仍是 `failed`（新答案尚未回來前，不翻回 lost） | 自動：`platform/tests/test_head_nodefail.py` |
| TC-041 | 裁決 Q1：事實年齡超過 6 小時就不再問 | 例外 | 一個 lost 的 run，有 Slurm 工作編號；最新有效事實是 NODE_FAIL，事實年齡是 6 小時 1 分鐘 | 擁有者呼叫 `get_run`（隔一段時間再呼叫一次） | 該 run 的 `fetch_run_records` 列總數沒有增加（不排任何新的抓取），不丟例外 | 自動：`platform/tests/test_head_nodefail.py` |
| TC-042 | 裁決 Q1：撤掉覆蓋層後，續跑閘門也要撤掉 | 例外 | 同 TC-037（先 NODE_FAIL、後 RUNNING，最新答案為 RUNNING） | 對它走續跑的前置檢查（`build._predecessor`） | 被拒絕，用的是既有那句拒絕的話（與 v3 逐字相同） | 自動：`platform/tests/test_head_nodefail.py` |
| TC-043 | 裁決 Q4：編號整理 | 功能 | 修正輪完成後的程式碼與測試 | 閱卷者在 `platform/` 內搜尋 TC-035、TC-036 | 原先標為 TC-035／TC-036 的兩處程式碼註解（與其測試名稱）已改標 TC-037／TC-038，且與本檔 TC-037／TC-038 的內容相符；沒有任何註解把 TC-035 或 TC-036 用在非「合併 origin/v3」的意思上 | 閱卷者查 diff（不是產品行為，不需寫入 `docs/TESTING.md`） |
