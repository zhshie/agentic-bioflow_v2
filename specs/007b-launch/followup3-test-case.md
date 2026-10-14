# 測試案例：007b 後續修正 3（第一次真國網驗收 TC-047／TC-048 的小事：失敗原因、complete 之後的 401、檔案權限）

**規格**：`specs/007b-launch/spec.md`（FR-004、FR-009）、`specs/008-run-receiver/spec.md`（FR-005、FR-006、TC-030）、`docs/PLATFORM.md:341`　**計畫**：`specs/007b-launch/followup3-plan.md`　**總覽**：`followup3-test-case-overview.md`

類型：**功能**（該做到的事）、**例外**（出錯或不該發生的事怎麼反應）、**防止退步**（和 main 比對）、**不在範圍**（確認沒做）。
名詞沿用 `test-case.md` 與 `followup2-test-case.md`（假站台、假平台、假 ssh、錄製的 Nextflow 事件）。新增：

- **維護者的真實觀察**（`acceptance-nchc.md`，2026-10-13，Taiwania 3 登入節點 lgn304）：
  - TC-047：ampliseq run 跑完成功；run 資料夾權限 700，但 `slurm-*.out` 是 644、`head.sh` 是 711（「資料夾裡沒東西漏出去，但檔案不該靠資料夾才安全」）。
  - TC-048：`tc048-cancel-2` 在 DADA2_MERGE 剛送出時被取消。`get_run` 顯示 `failed`、49/50 個 task、1 個 pending，**完全沒有原因**。
  - TC-048：run 結束後 Nextflow 的 log 出現**一條 401 警告**（平台在 `complete` 裡撤銷 token，而 Nextflow 在那之後還送了一則訊息）。
- **失敗原因欄位**：`get_run` 新增的一個欄位，放 Nextflow 自己的話。欄位名稱由執行者定（下稱「原因欄位」）。成功的 run 沒有這個欄位或值為空；執行者在報告裡寫明是哪一種。
- **complete 之後的訊息**：同一個 token、同一個 run 的 `progress`、`heartbeat`、重複的 `complete`。**哪一種是真實 Nextflow 會送的，由執行者從 Nextflow 26.04.7／nf-tower 1.28.3 原始碼找出並引行號**；本檔三種都測。
- **仿真假 sbatch**：測試用的假 `sbatch` 要像真的 Slurm：依 `-D <資料夾>` 與工作編號，在該資料夾建立 `slurm-<編號>.out`，**檔案權限取 `666 & 呼叫 sbatch 時的 umask`**（Slurm 的輸出檔由 slurmstepd 依送出者的 umask 開）。測試把站台代理行程的 umask 設成 022，才能在 main 上重現 644。其餘行為（`sbatch_fail`、`sbatch_garbage`、`sbatch_exit`、工作編號 4242）不變。
- **舊格式索引**：main 寫出的 `index.db`，`runs` 表沒有原因欄位。
- 「全部檔案」指一次送出完成後，專屬資料夾（`<work>/runs/<run>/`）裡的每一個檔案：`samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`、`tower.token`，以及仿真 sbatch 建的 `slurm-*.out`。

**絕不使用 `~/abf-station-test/`、不使用 port 8787 的真平台、不連國網。** 全部自動測試只用暫存資料夾與假站台。

## 功能

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-F3-01 | 維護者的例子（TC-048）：取消的 run 要說原因 | 功能 | 一個 run 已送 `create`／`begin`，`progress` 為 succeeded 49、pending 1（共 50），沒有 FAILED 的 task；`complete` 帶 `success=false`、`exitStatus=1`、`errorMessage="Execution cancelled by user"`（合成文字，真實文字見 TC-F3-13）、`errorReport` 為空 | `status.get_run` | `status` 是 `failed`；task 數 49 成功、1 pending、共 50（與 main 逐字相同）；原因欄位**逐字等於** `Execution cancelled by user`；`failed_tasks` 為空 | 自動：`test_receiver.py` 新增 |
| TC-F3-02 | 原因取 `errorMessage`；沒有才取 `errorReport` 第一行 | 功能 | (a) `fail_run.json` 的 complete（`errorMessage`＝`FIXTURE_BOOM_7`）；(b) 同一份但 `errorMessage` 改為 null；(c) 同一份但 `errorMessage` 改為空字串 | 分別 replay 後 `get_run` | (a) 原因＝`FIXTURE_BOOM_7`（不是 errorReport）。(b)(c) 原因＝`errorReport` 的第一個非空行（`Error executing process > 'BAD'`）；不是整段報告 | 自動 |
| TC-F3-03 | 已錄製的失敗 run（兩個 Nextflow 版本） | 功能 | 錄製檔 `fail_run.json`（26.04.7）、`nf2510_fail.json`、`nf2510_retry.json`（25.10.4） | replay 後 `get_run` | 三者的原因欄位都是 `FIXTURE_BOOM_7`；`failed_tasks`（名稱、結束碼、`error_message`）與 main 逐位元組相同 | 自動 |
| TC-F3-04 | 成功的 run 沒有原因 | 功能 | `ok_run.json`、`ok_resume.json`、`heartbeat_run.json`、`nf2510_ok.json`、`slow_run.json`、`nf2510_resume.json` | replay 後 `get_run` | 沒有原因欄位或值為空（與執行者報告所寫一致）；其餘欄位與 main 相同；`list_runs` 的輸出與 main 逐位元組相同（原因只出現在 `get_run`） | 自動 |
| TC-F3-05 | 維護者的例子（TC-048）：complete 之後的訊息不再 401 | 功能 | 平台用一個為 `run-one` 發的 run token；完整 replay `nf2510_ok` 到 complete，回應都 < 300 | 用同一個 token 對同一個 run 送：(a) `heartbeat`；(b) `progress`（內容與 complete 的不同）；(c) 第二次 `complete` | 三者都回 **2xx，不是 401**；回應內容與一般 OK 相同（`{"status": "OK"}`） | 自動：`test_launch_platform.py`（改寫 `test_tc020_complete_revokes…` 的 heartbeat 那一行） |
| TC-F3-06 | complete 之後的訊息什麼都不改 | 功能 | 同 TC-F3-05，先取 complete 之後 `index.db` 的完整內容（`runs`、`processes`、`failed_tasks` 所有欄位） | 送 TC-F3-05 的三種訊息，再取一次 | 兩次內容**完全相同**（只有 `last_message_at` 可以不同；若執行者選擇不更新它，也要相同）：`final_status`、`ended_at`、`exit_status`、六個 `n_*`、`processes`、`failed_tasks`、原因欄位都不變；`get_run` 前後相等 | 自動 |
| TC-F3-07 | token 在 complete 當下仍被標為已撤銷 | 功能 | TC-F3-05 的起點 | 讀 `tokens.db` | complete 後該 token 的 `revoked_at` **不是 NULL**（`test_tc020_complete_revokes…` 的 `tokens_rows(plat)[0][2] is not None` 保留，不改弱）；規格 FR-004 的「收到 complete 時撤銷」字面仍成立；允許的只是「同一 run、不改任何東西」這一道窄門 | 自動 |
| TC-F3-08 | 維護者的例子（TC-047）：`slurm-*.out` 不再是 644 | 功能 | 假站台＋仿真假 sbatch；代理行程 umask 為 022；一次完整的 launch | 看專屬資料夾裡仿真 sbatch 建的 `slurm-4242.out` | 權限是 **0600**（不是 0644）；在 main 上同一測試得 0644（見 TC-F3-41） | 自動：`test_station_launch.py` 新增 |
| TC-F3-09 | 專屬資料夾裡的檔案都不比資料夾寬 | 功能 | 同 TC-F3-08 | 列出專屬資料夾與其中全部檔案的權限 | 資料夾 0700；`samplesheet.csv`、`params.yaml`、`nextflow.config`、`tower.token`、`slurm-*.out` 都是 0600；`head.sh` 是 0600 或 0700（**群組與其他人的權限位元都是 0**）；沒有任何檔案的 `mode & 0o077` 不為 0 | 自動 |
| TC-F3-10 | sbatch 的呼叫形狀 | 功能 | 同 TC-F3-08，看送到站台的指令與假 sbatch 的呼叫紀錄 | 一次 launch | `sbatch` 恰好呼叫一次，參數與 main 相同（`<資料夾>/head.sh`）；它是在 `umask 077` 之下執行（以假 sbatch 記下的自身 umask 為準，不是只看指令字串）；成功訊息與 main 逐字相同 | 自動 |
| TC-F3-11 | rebuild 與即時路徑的原因一致 | 功能 | 一個失敗 run 的真 Nextflow（假 pipeline，一個 task `exit 1`，訊息 `FIXTURE_BOOM_7`）：即時送進平台的索引 A；同一資料夾 `rebuild` 出索引 B | 比較兩邊 `get_run` | 若 `.nextflow.log` 記有該文字：A 與 B 原因欄位**相同**（`test_nextflow_e2e.py` 的 TC-030 比對保持嚴格，不為此放寬）。若 log 沒有：B 為空，且執行者在報告寫明「rebuild 沒有」，並在 TC-030 比對中**點名**排除此欄位，其他欄位仍逐一相等 | 自動 |
| TC-F3-12 | 既有索引升級，每一列都留著 | 功能 | main 寫的 `index.db`：`runs` 有 3 列（succeeded／failed／running）、有 `processes` 與 `failed_tasks`、沒有原因欄位 | 用本分支啟動接收端（`create_app`）；另用 `rebuild` 以外的路徑 | 欄位新增成功；3 列所有舊欄位值、`processes`、`failed_tasks` **逐值不變**；舊列的原因欄位為 NULL；再啟動一次不報錯（可重複執行）；之後新的 failed run 的 complete 能寫入原因 | 自動 |
| TC-F3-13 | 真國網複驗 TC-047／TC-048 | 功能 | 修好的版本，維護者在 NCHC 上做；**不是執行者做** | 依 `docs/TESTING.md`：(a) 跑一個 nf-core 小 run 到成功，`ls -l <run 資料夾>`；(b) 再跑一個、中途 `cancel`，結束後 `get_run`，看 Nextflow log | (a) `slurm-*.out`、`head.sh` 及其他檔案都沒有群組／其他人的權限；(b) `get_run` 的失敗 run 顯示 Nextflow 自己的原因文字（記下真實文字）；Nextflow log 沒有 complete 之後的 401 警告。結果記進 `docs/TESTING.md` 的驗收紀錄 | 手動：維護者 |
| TC-F3-14 | 報告寫出 711 的原因與 401 的訊息來源 | 功能 | 執行者的報告與 `docs/PITFALLS.md` | 讀 | 報告有：(a) 引用 nf-tower 1.28.3 原始碼行號，說明 complete 之後會送哪一則訊息；(b) `head.sh` 為何是 711 的證據（或寫明「離線重現不出，原因未知，等 TC-F3-13」）；(c) 選了「寬限期」還是「已結束的 run 只允許不改任何東西」及理由；(d) rebuild 是否帶原因；(e)「bounded」的上限數字與「escaped」的意思 | 手動：驗收者讀報告 |

## 例外

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-F3-20 | 原因有上限，但不切短 Nextflow 的原話 | 例外 | (a) complete 的 `errorMessage` 正好 255 個字；(b) 10,000 個字 | `get_run` | (a) 原樣完整輸出（Nextflow 自己截在 255，平台上限**必須 ≥255**）；(b) 輸出長度 ≤ 執行者在報告寫的上限，且不會讓 `get_run` 變大到不能用；兩者都不因長度而 500 | 自動 |
| TC-F3-21 | 原因要跳脫，和其他顯示的文字一樣 | 例外 | `errorMessage` 含 ESC 控制碼（`\x1b[31m`）、`\r`、NUL、很多換行、以及 `<script>` | `get_run`（含經 MCP／CLI 輸出） | 輸出沒有原始的控制字元（ESC、NUL、`\r`）；換行不會讓一行變成多個欄位；`<script>` 當一般文字出現；輸出仍是合法 JSON | 自動 |
| TC-F3-22 | 沒有原因就什麼都不顯示，不編造 | 例外 | failed 的 complete：(a) `errorMessage`、`errorReport` 都是 null；(b) 都是空字串；(c) 欄位根本不存在 | `get_run` | `status` 仍是 `failed`；task 數同 main；原因欄位不存在或為空；**不出現**「cancelled」「unknown error」等平台自己編的字（FR-009 只准事實） | 自動 |
| TC-F3-23 | 型別不對不會讓接收端崩 | 例外 | complete 的 `errorMessage` 是數字、物件、清單，`errorReport` 是數字 | 送出 | 回 200（或與 main 相同的狀態碼）；run 照常記成 failed；原因欄位為空；`failed_tasks` 與 main 相同；沒有 500 | 自動 |
| TC-F3-24 | 結束後的訊息不能把狀態倒回去 | 例外 | 失敗的 run（`nf2510_fail`）已 complete，task 數與 `failed_tasks`、原因已定 | 之後同 token 送：(a) `progress`（running 3、succeeded 0、tasks 全 RUNNING）；(b) `heartbeat`；(c) `complete` 帶 `success=true`、不同 `exitStatus` | `status` 仍 `failed`、`ended_at`／`exit_status` 不變、各 `n_*` 不變、`processes` 與 `failed_tasks` 不變、原因欄位不變；`get_run` 前後相等 | 自動 |
| TC-F3-25 | token 不能建新的 run | 例外 | complete 之後的 token（為 `run-one` 發的） | (a) `create` 帶同名 `run-one` 但**新的 sessionId**；(b) `create` 帶另一個名字；(c) `create` 帶同 session 同名（重複建立） | 都回 401 或 403；`runs` 表的列數不變；(c) 若執行者選擇回 200，也不得改任何已記錄的東西（TC-F3-06 同標準） | 自動 |
| TC-F3-26 | token 不能碰別的 run | 例外 | complete 之後的 token A；另一個 run B（另一 token 建的、仍在跑） | 用 A 對 B 的 id 送 `progress`、`heartbeat`、`complete`；對不存在的 run id 送 `heartbeat` | 回 401、403 或 404，**不是 200**；B 的索引內容不變、B 沒被結束；不存在的 id 不產生新列 | 自動 |
| TC-F3-27 | 寬限最終要結束 | 例外 | complete 之後的 token | 用測試時鐘（`ABF_PLATFORM_CLOCK_OFFSET` 或 `clock`）前進到執行者報告所寫的結束時間之後，再送 `heartbeat`、`progress`、`complete`、`create` | 全部回 401（含 `X-ABF-Platform` 標頭）；結束時間**≤14 天**；若選「已結束 run 只准不改任何東西」那一種，也要有明確結束點（不得只靠 14 天到期）。另：14 天到期仍照舊 401（既有 `test_tc020_fourteen_days…` 不改而通過） | 自動 |
| TC-F3-28 | 其他撤銷原因仍然立刻失效 | 例外 | (a) 代理拒絕或失敗的送出，token 被撤銷（`revoke_run_tokens`）；(b) 一個沒有 complete 的 run 被取消後 token 仍有效（既有行為）；(c) 手動 `revoke_token` | 對 (a)(c) 用該 token 送 `heartbeat`、`progress`、`create` | (a)(c) 全部立刻 401，**不因為本次修正而得到寬限**；(b) 取消不撤銷的既有測試仍過 | 自動：既有 `test_tc020_when_the_agent_refuses…`、`…a_cancel_does_not_revoke…` 不改而通過＋新增 (c) |
| TC-F3-29 | 被拒絕的 complete 不撤銷 token | 例外 | complete 的 body 缺 `workflow`（400） | 送出後看 `tokens.db` | 回 400；`revoked_at` 仍是 NULL；之後的 `heartbeat` 仍 200（既有 `…a_refused_complete…` 不改而通過） | 自動 |
| TC-F3-30 | sbatch 失敗的回報不變 | 例外 | 假站台設 `sbatch_fail`（Invalid account）、`sbatch_garbage`、`sbatch_exit=255` | 各跑一次 launch | 訊息、`left_on_site` 與 main 逐字相同；sbatch 只呼叫一次、不重試（`sbatch_garbage` 兩次共 2 次是兩個 job 的總數，沿用既有斷言）；專屬資料夾與檔案仍留在原處且權限為 0600／0700（沒有因失敗而變寬） | 自動：既有 `test_tc017…` 不改而通過＋權限斷言 |
| TC-F3-31 | 資料夾已存在、解開失敗：行為不變 | 例外 | (a) 專屬資料夾已存在；(b) 假 tar 失敗 | 跑 launch | (a) 拒絕訊息與 main 相同、不覆蓋、不呼叫 sbatch、既有資料夾的內容與權限不動；(b) 訊息同 main、不呼叫 sbatch | 自動：既有測試不改而通過 |
| TC-F3-32 | 舊索引在唯讀情況下讀得出來 | 例外 | main 寫的舊 `index.db`（沒有原因欄位），**沒有**啟動接收端（`status.get_run` 以唯讀開檔，無法升級） | `status.get_run`／`list_runs`／MCP `get_run` | 不崩潰（沒有 KeyError）；舊的失敗 run 不顯示原因；其餘欄位與 main 相同；檔案沒被寫入（修改時間與雜湊不變） | 自動 |

## 防止退步

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-F3-40 | 舊測試是改正、不是刪掉或放寬 | 防止退步 | 本分支對 main 的 diff | 檢查所有被動到的測試檔 | 唯一被改的既有斷言是 `test_launch_platform.py` 中 `test_tc020_complete_revokes_the_token_and_the_run_data_stays` 的 `heartbeat … == 401` 那一行（改成 2xx＋索引不變）；`create … == 401`、`revoked_at is not None`、`get_run` 前後相等**全留**；其他測試的斷言一個都沒被刪、沒被放寬、沒有 skip；改動理由寫在計畫或報告 | 手動：驗收者看 diff |
| TC-F3-41 | 新的檔案權限測試真的抓得到 main | 防止退步 | main 的 `launch.py` 加上本分支新增的測試與仿真假 sbatch | 跑 TC-F3-08、TC-F3-10 | **在 main 上必須失敗**（`slurm-4242.out` 得 0644、sbatch 的 umask 是 022）；執行者把失敗輸出記進執行紀錄。TC-F3-09 的 `head.sh` 部分若在 main 上也過，執行者要在報告明說「這一項在 main 上就成立，不是這次修的」（見 TC-F3-14b），不得宣稱修好 | 自動＋執行紀錄 |
| TC-F3-42 | 所有錄製檔的 get_run 輸出，除了新欄位外與 main 相同 | 防止退步 | 全部 10 個錄製檔（`fail_run`、`ok_run`、`ok_resume`、`slow_run`、`heartbeat_run`、`nf2510_*`） | 在 main 與分支各 replay，比對 `get_run` 與 `list_runs` | 去掉原因欄位後兩邊逐位元組相同；`list_runs` 完全相同 | 自動：與 main 比對 |
| TC-F3-43 | 401 的長相不變 | 防止退步 | 無 token、亂湊的 token、為別的 run 發的 token、agent token | 送 `create`、`progress`、`/user-info` | 仍是 401、訊息 `Unauthorized: missing or unknown access token`、標頭 `X-ABF-Platform` 與 main 相同；agent token 仍不能寫 run | 自動：既有 `test_tc011…`、`test_tc020…` 不改而通過 |
| TC-F3-44 | complete 之前的行為一個字都不變 | 防止退步 | 完整 replay 各錄製檔 | 比對每一個回應的狀態碼與內容（create、begin、progress、heartbeat） | 與 main 相同；`workflowId` 相同；重試的 task 仍只算一列（`nf2510_retry`） | 自動：與 main 比對 |
| TC-F3-45 | `failed_tasks` 與錯誤訊息擷取不變 | 防止退步 | `fail_run`、`nf2510_fail`、`nf2510_retry` 與含 `Command error:` 的 errorReport | replay／`extract_error` | `failed_tasks` 的 `name`、`exit_code`、`error_message` 與 main 逐位元組相同（`common.extract_error` 沒被改） | 自動 |
| TC-F3-46 | rebuild 的其他欄位不變、不碰 token | 防止退步 | 同 008 的 TC-030／031／032 起點 | 跑 `test_nextflow_e2e.py` 對應測試 | 除 TC-F3-11 點名的欄位外，rebuild 與即時路徑逐一相等（時間容差 1 秒不變）；`tokens.db` 在 rebuild 前後逐位元組相同、rebuild 沒有開啟它 | 自動：既有測試不改而通過 |
| TC-F3-47 | 送出的內容與確認雜湊不變 | 防止退步 | 同樣的輸入在 main 與分支各 render 一次 | 比對 `render_bundle` 的結果與 `bundle_sha256` | `head.sh`、`params.yaml`、`nextflow.config`、`samplesheet.csv` 的內容與雜湊逐位元組相同（`umask 077` 只加在 sbatch 的呼叫上，不改使用者看到並確認的內容） | 自動：與 main 比對 |
| TC-F3-48 | 測試數量不減、沒有 skip | 防止退步 | 本分支與 main | 數 `platform/tests/` 的測試與 skip／xfail | 數量只增不減；沒有新的 skip／xfail；`pins.env` 不動 | 手動：驗收者看 diff＋測試輸出 |
| TC-F3-49 | 其他站台行為不變 | 防止退步 | `station_harness.py`／`launch_harness.py` 與假 sbatch 的 diff | 跑 `test_station_launch.py`、`test_station_channel.py`、`test_station_cancel.py`、`test_station_fakeplatform.py`、`test_launch_platform.py`、`test_launch_followup.py` | 全部通過；假 sbatch 的 `--version`、工作編號、`jobs.tsv` 紀錄、`scripts/` 複本、`sbatch_*` 開關不受影響；取消流程（`scancel` 前先 `squeue` 核對）不變 | 自動 |

## 不在範圍

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-F3-60 | 沒有碰 "Report/Timeline file already exists" 警告 | 不在範圍 | 本分支的 diff | 檢查 | 計算環境設定（CE config）沒新增或改 report／timeline 設定；沒有讀站台的 log 或下載站台檔案；報告把這件事留給 developer-agent 在連線恢復後處理 | 手動：驗收者看 diff |
| TC-F3-61 | 沒碰 relay 網域、009、plugin、.github | 不在範圍 | 本分支的 diff | 檢查 | `plugin/`、`.github/`、`scripts/nf_relay.py` 沒改；沒有新增 relay 網域；沒有網頁確認頁、沒有 MCP 寫入工具、沒有免確認取消 | 手動：驗收者用 git diff |
| TC-F3-62 | 沒碰正在跑的驗收環境 | 不在範圍 | 全部新測試與執行紀錄 | 掃描＋看紀錄 | 只用暫存資料夾與假站台；不讀寫 `~/abf-station-test/`；不用真 port 8787；不連 NCHC | 自動：掃描新測試原始碼＋手動：看紀錄 |
| TC-F3-63 | 平台不替取消編原因 | 不在範圍 | 一個 run 的 `launches` 列有 `cancel_requested_at`；其 complete 的 `errorMessage` 與 `errorReport` 都空 | `get_run` | 沒有原因（不會因為 `launches` 有取消時間就寫「cancelled by user」）；原因只來自 Nextflow 的 complete 訊息（原則 2、FR-009） | 自動 |
| TC-F3-64 | `launch.py` 只動 sbatch 的呼叫 | 不在範圍 | `platform/abf_station/launch.py` 的 diff | 檢查 | diff 只涉及 sbatch 那一次呼叫（加 `umask 077`，或另一個執行者證明可行的做法），以及為了權限必要的最小改動；沒有新的站台指令、沒有 `chmod -R`、沒有 `rm`、沒有背景程式或迴圈；`LAUNCH_ALLOW` 不變；`test_station_static.py` 通過 | 手動：驗收者看 diff＋自動：既有 static 測試 |
| TC-F3-65 | 不追改已經存在的 run 資料夾 | 不在範圍 | 站台上已有舊 run 資料夾（644／711 的檔案） | 檢查程式 | 沒有任何程式去改舊資料夾的權限；只有新的 launch 受影響 | 手動：驗收者看 diff |

## 憲法與安全網

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-F3-80 | 原則 2：索引不是真相，沒有第二份狀態 | 功能 | 本分支新增的欄位與 rebuild | 讀 diff＋跑 `tests/no_second_run_state_test.sh` | 原因欄位是 Nextflow 在 complete 送來的原話，沒有平台自己推出來的狀態；沒有新的狀態機、沒有常駐程式或計時器（寬限期若有，是查詢時用時鐘算，不是背景工作）；`rebuild` 丟掉索引後仍能重建，欄位的來源是 Nextflow 的紀錄或明確為空 | 自動＋手動 |
| TC-F3-81 | 安全網：不刪使用者資料 | 例外 | 站台有 `rawdata/s1.fq`、`results`、`analysis`，破壞性紀錄（`rm`／`rmdir`／`mv`／`tar` 包裝）開啟 | 跑一次成功與一次 sbatch 失敗的 launch | 破壞性紀錄中沒有 `rm`；`rawdata`、`results`、`analysis`、快取原封不動；`tar` 只出現在解開新資料夾那一次 | 自動 |
| TC-F3-82 | 安全網：憑證與權限 | 例外 | 一次 launch＋complete 完成，token 明文已知 | 掃描：`get_run`／`list_runs`／MCP 輸出、原因欄位、`index.db`、平台與代理的 log、站台上專屬資料夾 | token 明文與 base64 只出現在 `tower.token`（0600）；不在 `head.sh`、不在 `get_run`／原因欄位、不在 `index.db`；`configText`、`commandLine`、名字像秘密的 params 值仍不存（FR-008）；窄門的存在不讓 token 能讀到任何資料（它只能送、不能讀） | 自動 |
| TC-F3-83 | 安全網：送出前完整顯示並等確認 | 功能 | 一次 launch | 看確認畫面與送到代理的 bundle | 使用者確認的內容與 main 相同（TC-F3-47）；沒有未經確認就多做的事（沒有額外的 sbatch、`umask` 不算新的動作）；`confirm_launch` 流程與假站台上「未確認不送」的既有測試通過 | 自動：既有測試不改而通過 |
| TC-F3-84 | 原則 8：實測寫進文件 | 功能 | 本分支的 diff | 讀 `docs/PITFALLS.md`、`docs/PLATFORM.md` | PITFALLS 有新條目：(a) Slurm 的輸出檔由送出者的 umask 決定，所以 sbatch 要在 `umask 077` 下呼叫；(b) complete 之後 Nextflow 還會送哪一則訊息（引 nf-tower 1.28.3 行號）；(c) 真實的取消 run 其 `errorMessage` 長什麼樣（日期、版本）。`docs/PLATFORM.md:341` 的 token 段落更新成與新行為相符，且仍寫明「綁 run 名稱、不能建別的 run、complete 時撤銷、14 天」；`tests/` 中 PITFALLS 對應程序（TESTING.md P2）仍通過 | 手動：驗收者看 diff |
| TC-F3-85 | 原則 13：不編造「已修好」 | 例外 | 執行者報告與 TC-F3-41 的結果 | 讀 | 凡是離線測試證明不了的（`head.sh` 在真站台上為何 711、真取消訊息的文字、真 Nextflow 的 complete 後訊息）都標為「等維護者在國網複驗」，不寫成已驗證；沒有只在測試裡成立、卻在入口用不到的程式（原因欄位必須經接收端 `complete` 寫入、經 `get_run` 讀出，兩端都被測試走過） | 手動：驗收者看報告 |
| TC-F3-86 | 原則 3：沒有個人路徑或寫死的站台路徑 | 功能 | 本分支新增的程式與測試 | 跑 `tests/no_hardcoded_paths.sh` | 通過；新測試不含 `/home/<人名>`、`/work/`、NCHC 帳號或 lgn 主機名；測試的資料夾來自 `tmp_path` | 自動 |
