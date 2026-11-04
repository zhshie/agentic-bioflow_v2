---
id: head-nodefail-detect
title: Slurm head job 被排程器終結（NODE_FAIL／CANCELLED／TIMEOUT／OUT_OF_MEMORY）時，平台要讓該 run 變 Failed 並說出排程器狀態
tier: C
kinds: backend
risk: L
lane: L45-head-nodefail-detect
branch: fix/head-nodefail-giveup
base: v3
source: 桌機 session 7j5l5bj 10-31 在 nano4 實測：t1（平台 job 78、Slurm 654018）head job 整個消失，站台 log 只寫 "job 78: done"，平台沒有任何失敗訊號；見 memory/handoff/2026-11-01-2104.md 待辦第 2 點
---

# head-nodefail-detect

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/head-nodefail-detect/plan.md`。**只處理本任務**。risk L：範圍含 `platform/abf_station/`。

## 目標
Slurm 的 head job 被排程器終結（NODE_FAIL、CANCELLED、TIMEOUT、OUT_OF_MEMORY 等），Nextflow 來不及寫完成紀錄時，同事在網頁或 MCP 要看到該 run 是 Failed，失敗原因寫出排程器狀態（例如「Slurm head job 654018 ended as NODE_FAIL (sacct)」），並且 `failure` 欄（PR #166，Seqera 式）給出續跑／重送。現況：平台送出 sbatch 後再也不問 Slurm；run 靜默 3×60 秒後變 `lost`，原因 `None`，續跑被擋。

## 維護者原話（verifier 出題用）
1. 「跟Seqera platform一樣的模式，不要自己定義」（10-23 常設）→ 沿用 `failure` 欄五個鍵（`status_seqera`、`failed_tasks`、`failure_reason`、`log`、`actions`），不新增欄位型別、不新增狀態。
2. DESIGN.md 第 42 行：run 只有 Running／Done／Failed 三態，`lost` 顯示為 Failed。→ 偵測到排程器終結後，這個 run 顯示 Failed，原因具名。
3. 憲法原則 2（真相來自 Nextflow 的紀錄）→ Nextflow 有完成紀錄時一律以它為準，排程器狀態只在「沒有完成紀錄」時才讀；不新增狀態機、不新增監控常駐程式。
4. handoff 11-01-2104 待辦第 2 點：「平台偵測不到 head job NODE_FAIL（t1 job 78／Slurm 654018 整個看不到，站台 log 只寫 "job 78: done"）」→ 對應第一條測試。

## 範圍：檔案
- `platform/abf_station/fetch.py`：`fetch_run_records` 新增選填參數 `slurm_job_id`；沒有完成紀錄時，站台詢問 squeue、再問一次 sacct，結果放進回傳的 `scheduler`。`ARGS` 加入新鍵。
- `platform/abf_station/handlers.py`：只在 `ARG_KEYS["fetch_run_records"]` 跟著 `fetch.ARGS` 時需要動；若自動跟隨則不改。
- `platform/abf_platform/jobs.py`：新增 `head_state(db, run)`（讀該 run 最新一筆 done 的 `fetch_run_records` 結果裡驗證過的 `scheduler`）；`enqueue_fetch` 接受 `slurm_job_id`，同一 run 已有排隊或執行中的抓取就不重複排。
- `platform/abf_platform/actions/__init__.py`：`get_run`／`list_runs` 在 run 為 `lost` 時，疊上排程器事實（仿 `cancel_requested_at` 的疊加做法）：`failure_reason`、`status_seqera = failed`、`actions` 含 resume／relaunch；`get_run` 對 lost 的 run 排一個去重的唯讀抓取。
- `platform/abf_launch/build.py`：`_predecessor` 的「已失敗才可續跑」判斷，接受「lost 且排程器事實顯示 head 已終結」。
- `platform/abf_platform/failures.py`：僅在必須時加一個「排程器終結」原因格式化函式；`summarize` 簽章與五個鍵不變。
- `platform/tests/station_harness.py`：`FakeSite` 加假 `sacct`（與假 sbatch／squeue／scancel 同一套狀態檔機制，見 `_fakes`、`FAKE_TOOLS`）。
- 新測試：`platform/tests/test_head_nodefail.py`（平台端）、`platform/tests/test_station_head_state.py`（站台端）。
- 文件：`docs/PLATFORM.md`（「Failed runs」段、lost 狀態說明第 63、646、674 行附近）、`docs/PITFALLS.md` 加一條「排程器終結的 head 不會留下 Nextflow 紀錄」。
- 被釘住的既有測試（只准增加、不刪不放寬；每條都要用 `git -C <repo> grep -n` 對 origin/v3 再確認一次行號）見下節「允許的斷言」。

## 作法
1. **不新增 job 種類、不新增 migration。** `jobs.kind` 有 CHECK 限制，新種類要 migration；本案重用既有唯讀的 `fetch_run_records`。理由寫進 PR。
2. **站台端（`fetch.py`）**：`fetch_run_records` 收到選填 `slurm_job_id`（只接受純數字，沿用 `cancel.py` 的工作編號驗證）。流程：照舊讀 Nextflow 紀錄；只有在 log 裡找不到完成行（沒有完成紀錄）時，才先 `squeue -h -j <id> -o %T`，若已不在佇列再 `sacct -n -P -X -j <id> -o State`。取第一行，去掉 `CANCELLED by <uid>` 的尾巴，大寫。結果放 `scheduler = {"job_id": "<id>", "state": "<STATE>", "source": "squeue"|"sacct"}`；兩者都查不到或指令失敗則 `scheduler = None`（不猜）。有完成紀錄時完全不呼叫 squeue／sacct。
3. **狀態分類（平台端、純函式、單一表格）**：
   - 終結壞狀態：NODE_FAIL、BOOT_FAIL、CANCELLED、TIMEOUT、OUT_OF_MEMORY、FAILED、DEADLINE、PREEMPTED、REVOKED → run 視為 Failed，原因 `Slurm head job <id> ended as <STATE> (<source>)`。
   - 活著：PENDING、RUNNING、COMPLETING、REQUEUED、SUSPENDED、CONFIGURING → 不疊加，run 維持原樣（不可把還在排隊或執行的 head 標成失敗）。
   - COMPLETED 但 Nextflow 沒有完成紀錄 → 維持 `lost`，原因改為 `Slurm head job <id> completed but Nextflow left no completion record`，不開續跑（資料不全，要人看）。
   - 不認得的狀態或 `scheduler = None` → 不疊加。
4. **平台端讀取**：`jobs.head_state` 只信「最新一筆 done 的 `fetch_run_records`」且該筆 `scheduler.job_id` 等於 `launches.slurm_job_id`；欄位逐一驗證型別與長度（站台回傳視為不可信資料）。
5. **疊加（actions 層）**：`get_run`、`list_runs` 共用同一個疊加函式（動作層唯一一份邏輯，路由處理函式不得複製）。只對 `lost` 的 run 生效；疊加後 `status` 顯示 Failed、`failure` 欄的 `failure_reason` 為上面的句子、`status_seqera = failed`、`actions` 與一般 failed run 相同。**不寫回索引（不改 runs 表）**，與 `cancel_requested_at` 同一種「查詢時疊加」。有任何 Nextflow 完成紀錄的 run 不走此路徑。
6. **觸發**：`get_run` 看到 lost 的 run、且 `launches.slurm_job_id` 有值、且沒有新鮮（< 60 秒）的 done／排隊中的抓取，就 `enqueue_fetch(..., slurm_job_id=...)`；`list_runs` 只讀已有的結果，不排工作。這是「被問到時才問一次」，不是常駐程式。抓取完成後下一次 `get_run` 就會看到疊加。
7. **續跑／重送閘門**：`build._predecessor` 原本要求索引狀態為 `failed`；新增一條：狀態為 `lost` 且 `head_state` 為終結壞狀態，視同 failed 通過。其他 lost（沒有事實、COMPLETED 無紀錄）仍被拒，既有 `test_a_run_that_is_lost_is_not_one_that_has_ended` 逐字不變。
8. **安全**：站台新增的 shell 只用驗證過的純數字工作編號；`sacct` 輸出視為不可信，只取第一行第一欄並以允許清單比對，日誌與回應不含密鑰、不露內部路徑。
9. 不改 MCP 工具介面、不改網頁字串（失敗原因走既有 `failure_reason`）。

## 失敗先行測試
全部用 `platform/tests/` 既有假站台（`FakeSite`、假 sbatch、假 squeue）；先寫、現在會紅。
**`test_station_head_state.py`（站台端）**
- `test_nodefail_head_reports_sacct_state`：假 sbatch 送出後，狀態檔設該 job 為 NODE_FAIL（squeue 查不到、sacct 回 `NODE_FAIL`）、log 沒有完成行；`fetch_run_records` 帶 `slurm_job_id` → `scheduler == {"job_id":..., "state":"NODE_FAIL", "source":"sacct"}`。
- 同上以參數化覆蓋 CANCELLED（含 `CANCELLED by 1234` 尾巴→`CANCELLED`）、TIMEOUT、OUT_OF_MEMORY。
- `test_completion_record_wins`：log 有完成行時，假 squeue／sacct 的呼叫次數為 0，`scheduler` 為 None。
- `test_running_head_is_not_failed`：squeue 回 RUNNING → `scheduler.state == "RUNNING"`，sacct 沒被呼叫。
- `test_scheduler_unreachable_is_none`：sacct rc 非 0 → `scheduler is None`，不丟例外。
- `test_job_id_must_be_digits`：`slurm_job_id="1; rm -x"` → 被拒，假站台沒有收到任何指令。
- `test_unknown_arg_still_refused`：其他未知參數仍被 `handlers` 拒絕（既有行為）。
**`test_head_nodefail.py`（平台端）**
- `test_lost_run_with_nodefail_head_is_failed`：重現 t1：run 已送出、無 Nextflow 完成紀錄、超過 `LOST_AFTER_SECONDS`、抓取結果 `NODE_FAIL` → `get_run` 的 `status` 為 Failed，`failure.failure_reason` 含 `NODE_FAIL` 與工作編號，`failure.status_seqera == "failed"`，`actions` 含續跑與重送。
- 參數化 CANCELLED、TIMEOUT、OUT_OF_MEMORY：同樣結果，原因句含各自狀態字。
- `test_lost_run_without_fact_stays_lost`：沒有抓取結果 → 與 v3 逐字相同（`unknown`、原因 None）。
- `test_get_run_enqueues_one_fetch`：連叫兩次 `get_run` → 只排一個抓取，且帶 `slurm_job_id`。
- `test_running_head_not_overlaid`：事實為 RUNNING／PENDING → 不疊加。
- `test_completed_without_record_is_not_resumable`：事實為 COMPLETED → 維持 lost、有「completed but Nextflow left no completion record」，續跑被拒。
- `test_nextflow_record_wins`：run 有完成紀錄（成功）且事實為 NODE_FAIL → 狀態仍是成功，不疊加。
- `test_resume_accepted_for_nodefail_head`：`_predecessor` 對疊加的 lost run 放行；對無事實的 lost run 仍拒（沿用既有句子）。
- `test_forged_scheduler_fact_ignored`：抓取結果的 `job_id` 與 `launches.slurm_job_id` 不符、或 state 不在允許清單／過長 → 不疊加。
- `test_other_user_cannot_see_overlay`：第二位使用者讀第一位的 run → 被拒（擁有者規則，讀一條）。
- 對等性：動作層函式與 `list_runs`／`get_run` 的對應清單不變（既有對等性測試維持綠）。

## 允許的斷言（既有測試）
下列既有測試釘住本案會碰的常數或句子，**只准新增、不刪不放寬**；開工前用 `git -C <repo> grep -n "<字串>" origin/v3 -- platform/tests` 逐條對一次：
- `test_failures.py`：第 64～72 行（lost／cancelled 的 `summarize` 結果，`unknown`、原因 None）、86、208、288；`failures.summarize` 回五個鍵不變。
- `test_status.py`：19、40、56（lost 判定秒數與狀態）。
- `test_resume_platform.py`：268、424～431（lost 的 run 不可續跑）；`test_launch_followup.py` 407；`test_resume_scope.py`。
- `test_station_clean.py`：295（`fetch.ARGS` 的內容）——新增 `slurm_job_id` 後此條要同步擴充，**用新增斷言，不改原斷言的其他鍵**；若原斷言是整組相等，則改成「原本的三個鍵仍在」並在 PR 說明。
- `jobs.KINDS` 與 `handlers.JOB_KINDS` 的整組相等測試（本案不增種類，必須維持綠）：`test_byte_channel_a.py`（114、232）、`test_byte_channel_b.py`（184）、`test_cleanup_store.py`（137、173、179）、`test_launch_platform.py`（122、606）、`test_resume_scope.py`（70）、`test_station_platform.py`（324、330）。
- `test_station_cancel.py`：143～162（`fetch_run_records` 站台端的既有案例）。
- 其餘引用 lost／fetch 的測試：`test_cleanup_confirm.py`、`test_pipeline_files_queue.py`、`test_station_pipeline_files.py`、`test_cloud_cost.py`、`test_nfcore_catalogue.py`、aws／azure／gcb／k8s 的 launch 與 clean 測試、`test_web_running.py:125`、`test_cleanup_offer.py:364`、`test_mcp.py:111`、`test_web_board.py`。
- `docs/TESTING.md` 若有列 `fetch_run_records` 的手動步驟，只加不改。

## 完成標準（done when）
- 上面每條失敗先行測試綠；`tests/run_all.sh` 全綠（環境紅依 README 通例）。
- diff 只新增分支：沒有完成紀錄之外的路徑行為與 v3 逐字相同；無 migration、`jobs.KINDS` 不變。
- 閱卷（risk L）另附：爆炸半徑證明——新增的站台 shell 只含驗證過的數字工作編號；沒有寫回索引；PASS 後跑一次 Opus 對抗審。
- 附證據：`git diff --stat`、`git -C <repo> grep -n sacct origin/v3`（應為 0 筆，證明是新增）貼進 ledger。

## 環境事實
- 實際現象：t1／平台 job 78／Slurm 654018，站台 log 只有 "job 78: done"（`memory/daily/2026-10-31.desktop-7j5l5bj.md`）；executor 不必去讀國網。
- 現行讀取點：`status.derive_status`（`lost`＝3×60 秒無完成，`common.LOST_AFTER_SECONDS`）、`failures.summarize`（`_FAILED = ("failed","lost")`）、`actions.get_run`（約 103 行）、`list_runs`（約 81 行）、取消疊加（約 93～113 行）。
- 站台：`site.call` 在站台跑 shell；`cancel.py` 已會用工作編號查 squeue；`launch.py::_probe` 以名稱查 squeue；目前站台**沒有任何 sacct 使用**。
- 假站台：`station_harness.py` 的 `FakeSite._fakes` 有假 sbatch／squeue／scancel，由狀態檔與 `jobs.tsv` 驅動；要新增的是假 sacct。
- 唯一非測試的 `enqueue_fetch` 呼叫者：`platform/abf_launch/cli.py:426`；`ARG_KEYS["fetch_run_records"] = fetch.ARGS`，未知鍵被拒。
- 續跑閘門：`platform/abf_launch/build.py::_predecessor`（約 435～500 行）。
- 驗收的真站台重跑是手動步驟（見不做）。

## 不做
- 排除壞節點（25a-cpn01／02／04／05）：A 級、改計算環境設定，另案、要先問維護者。
- 國網（nano4）的真機重跑：由維護者／操作員日後驗收，需他親手開 ControlMaster（2FA）；executor 不碰國網，ledger 註明「手動驗收待辦」。
- 「送出後索引根本沒有該 run」（沒有任何 Nextflow 事件、從未註冊）的情況：本片不處理，列為後續切片（需要以 `launches` 為起點列出 run，改動較大）。
- 不新增 job 種類、migration、狀態機、常駐監控；不寫回 runs 表；不改 MCP 工具介面與網頁字串。
- 不處理 `squeue`／`sacct` 都查不到的 head（`scheduler=None` 維持 lost）。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
2. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值，條數 ≤ 25。
3. 本任務碰 `platform/abf_station/`，risk L，須附爆炸半徑證明；請把 `risk: L` 抄進佇列的任務物件。
4. 先決定的設計取捨（由 executor 實作，不再問）：①疊加只在查詢時，不寫索引；②`get_run` 可排唯讀抓取（去重、60 秒內不重排）；③`status` 顯示 Failed，續跑閘門才放行；④COMPLETED 無紀錄維持 lost。若維護者不同意①～④，改派前先告知 developer-agent。
5. 與其他車道：`platform/abf_platform/actions/__init__.py`、`jobs.py` 是熱檔，落地前 `git merge origin/v3`，衝突以 v3 為準再重套本案分支。
6. worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明。

N. TC-012 裁決（11-03）：lost 的 run 仍提供 `relaunch`（v3 既有測試釘住），只保證不出現 `resume`。get_run 對 NODE_FAIL 回 status=failed 是預期（目的就是顯示為失敗）。非 Slurm 後端查不到 sacct 就維持 lost，接受。Nextflow 完成行 `Execution complete -- Goodbye` 的真站台比對列為 nano4 手動驗收，不擋合併。
O. 對抗審修正（11-03，Opus 審查，三項已重現）：
 (1) 一分鐘限流要算「任何狀態」的 fetch_run_records（含 refused／error／expired）：同一 run 60 秒內已有任何一筆，就不再排新的；檢查與 enqueue 放進同一個寫入交易（避免兩個 get_run 同時各排一筆）。
 (2) `slurm_job_id` 只由 head-state 查詢那條路徑加進 args；一般的 `enqueue_fetch`（含 `abf-launch fetch` CLI）維持原三個鍵，不送新鍵（舊站台代理會整個拒絕）。head-state 查詢被 refused 時視為「沒有事實」、run 維持 lost，且受 (1) 限流，不重排。
 (3) `_fetches_of` 的 LIMIT 100 要在依 run_name 過濾「之後」才套用（或每個 run 各取最新幾筆），否則同一運算環境上別的 run 的抓取會把事實擠掉。
 (4) `.nextflow.log` 超過 20 MB 被截斷時，不可當作「已有完成行」：截斷＝完成行未知，仍要問排程器（排程器回 COMPLETED 之類就維持原顯示）。
 新增測試案例 TC-026～TC-029 對應 (1)～(4)，已寫進 test-case.md；實作不得改弱既有測試。

P. （11-04，濃縮重寫：原文曾被 build-dev-plans.py 洗掉）最新一筆真實排程器答案為準；None 不覆蓋較早的結束事實；已結束的 head 不重問；沒有呼叫者就不做事；輪轉日誌缺開始標記時問排程器；第一步 `git merge origin/v3`；測試 TC-030 起。
Q. /code-review 第二次裁決（11-04）：(1) 壞結束事實不是永久的：每 10 分鐘最多再問一次（事實年齡超過 6 小時不再問），最新一筆真實排程器答案為準，答案是 RUNNING／PENDING 時覆蓋層撤掉（修改 P3），須有測試 NODE_FAIL 後 RUNNING → 不再顯示 Failed、不提供 resume／relaunch。(2) 被覆蓋層顯示成 Failed 的 run 沒有 ended_at：web_board 的 _duration 與所有 Ended 欄位要用與失敗通知相同的備用時間。(3) 其餘列 C 級後續。(4) 註解中 TC-035／036 改標，測試編號從 TC-037 起（已實作為 ADV-4／ADV-5，維護者端接受）。
R. /code-review 第三次對 PR #318 的裁決（11-04，只收兩項，其餘進 backlog 列 C 級）：
 1. 沒有任何可用事實時也要有放棄上限：run 失聯超過 6 小時（以最後訊息時間或建立時間算）且仍沒有事實，就不再每分鐘問排程器；須有測試（失聯 7 小時、事實 None → 不再排新的 fetch_run_records）。
 2. get_run 的 MCP 標註不再是純唯讀（會排一個站台讀取工作、寫 platform.db）：read_only_hint 改為 false（保留 idempotent），工具說明加一句「失聯的 run 會觸發一次唯讀的站台查詢」；既有 MCP 合約測試若釘死該標註，同步改並在 ledger 說明。
 3. 其餘六項（NODE_FAIL 重排風險、kept_fact_sql 效能、symlink 日誌、list_runs 多餘查詢、狀態表重複、區域 import）進 backlog，不擋這支 PR。
 4. 第一步仍是 git merge origin/v3；測試編號從 TC-044 起。

## 裁決 R4（11-04，developer-agent，Opus 對抗審後）

對抗審對：6 小時放棄上限只能在「至少問過一次卻沒答案」之後生效；從未被問過的失聯 run，有人第一次打開時要問一次（隔夜才看的 t1 NODE_FAIL 才顯示原因）。合約 TC-044 的 [no_fetch] 變體已由我改成「恰好排一筆，之後不再排」，[only_none] 不變。改 `jobs.ask_head_state`：放棄條件加上「已有至少一筆抓取列」。先寫 RED 再改。

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
