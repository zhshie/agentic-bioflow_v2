# 測試案例：run-diag-tools（平台為 runs 技能補上的三項唯讀診斷能力）

<!--
Written by the verifier (CONTRACT mode) from specs/run-diag-tools/plan.md (含 D1–D5 裁決).
此功能沒有 spec.md；計畫是唯一來源。計畫只引用維護者的話「都照你的建議」，沒有逐字的輸入／輸出範例，
所以下面每條都來自計畫的目標、Tests 清單、不在範圍與 D1–D5，沒有加計畫沒說的行為（TC-006 是唯一有疑問的，見總覽）。
-->

**規格**：`specs/run-diag-tools/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

白話先講：這次平台要多做三件「只讀、只給 run 的主人看」的事。

1. `get_run`（看一個 run 的狀態）對每個失敗的任務多附一個「這個任務在站台上的工作資料夾」（`workdir`）。
2. 新工具 `read_task_log`：請該 run 的站台代理人（station agent，住在實驗室叢集那邊的小程式）讀那個資料夾裡的 `.command.err`／`.command.out`／`.command.log` 其中一個，回傳最後面的內容（最多 200 行、64 KB）。
3. `get_run` 在「取消請求已確認並送出」時多附 `cancel_requested_at`，讓技能能分辨「被取消」和「自己失敗」。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

除非另外註明，「自動」都是 `platform/tests/test_run_diag_tools.py`（新檔，先寫測試）；舊測試檔另有註明。「假代理人」＝測試裡用來代替真站台代理人的程式。

## User Story 1 — 失敗任務帶回它的工作資料夾（get_run）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標 1 | 功能 | 重播 `fail_run` 的錄製事件（任務事件裡有 `workdir`） | 對這個 run 呼叫 `get_run` | `failed_tasks` 的每一筆都有 `workdir`，值等於該任務自己事件裡寫的資料夾（例如 `/LAUNCH/wk/0a/2292cff672c3dd2d67d07193de947a`） | 自動 |
| TC-002 | 目標 1；D1(a) | 功能 | 重播 `nf2510_fail` | 呼叫 `get_run` | 每一筆失敗任務都有 `workdir`，等於它自己事件裡的值 | 自動 |
| TC-003 | 目標 1；D1(a) | 功能 | 重播 `nf2510_retry`（任務失敗後重試，後一次嘗試取代前一次） | 呼叫 `get_run` | 留下來的失敗任務帶 `workdir`，且是留下來那一次嘗試自己事件裡的資料夾，不是被取代那次的 | 自動 |
| TC-004 | 目標 1「缺就不出現，絕不猜」 | 例外 | 重播一個失敗 run，但把某個失敗任務事件裡的 `workdir` 拿掉 | 呼叫 `get_run` | 那個任務的資料裡**沒有** `workdir` 這個欄位（不是空字串、不是 null、不是推算出的路徑）；有 `workdir` 的其他任務不受影響 | 自動 |
| TC-005 | 目標 1「缺就不出現，絕不猜」 | 例外 | 一個失敗任務只出現在 run 結束時的錯誤報告（沒有它的任務事件） | 呼叫 `get_run` | 這個任務出現在 `failed_tasks`，但沒有 `workdir` 欄位 | 自動 |
| TC-006 | 目標 1；既有部署不壞（沿用 `store.py:304` 對 `failure_reason` 的升級先例） | 例外 | 一個本次修改之前建立的 `index.db`（`failed_tasks` 沒有 `workdir` 欄，裡面已有失敗任務） | 打開它、呼叫 `get_run`、再讓它收下一個新的失敗任務事件 | 舊資料全部還在，舊的失敗任務顯示時沒有 `workdir`；新事件寫得進去，新任務有 `workdir`；沒有出現資料庫錯誤 | 自動 |
| TC-007 | 目標 1「只給主人看」 | 例外 | 一個 run 是使用者 A 送出的 | 以使用者 B 的身分呼叫 `get_run` 那個 run 的 id | 得到 `found: false` 與「找不到這個 run」，內容和 B 查一個根本不存在的 id 時完全相同；看不到任何 `workdir` 或失敗任務 | 自動 |

## User Story 2 — `read_task_log` 讀失敗任務的記錄尾巴（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-101 | 目標 2；which=err | 功能 | 自己的 run、有一個帶 `workdir` 的失敗任務、代理人在線；假代理人在那個資料夾有 `.command.err` | 呼叫 `read_task_log(run_name, task, "err")`，`task` 用 `get_run` 顯示的失敗任務名 | 回傳成功，內容是假代理人讀到的 `.command.err` 文字；交給代理人的工作指名的是該任務的 `workdir` 與檔案 `.command.err` | 自動 |
| TC-102 | 目標 2；which=out | 功能 | 同 TC-101，資料夾有 `.command.out` | 呼叫 `read_task_log(…, "out")` | 回傳 `.command.out` 的內容；工作指名檔案 `.command.out` | 自動 |
| TC-103 | 目標 2；which=log | 功能 | 同 TC-101，資料夾有 `.command.log` | 呼叫 `read_task_log(…, "log")` | 回傳 `.command.log` 的內容；工作指名檔案 `.command.log` | 自動 |
| TC-104 | 目標 2；D5 | 功能 | 檔案只有 5 行、不到上限 | 呼叫 `read_task_log` | 5 行全部回傳，答案裡沒有說被截斷 | 自動 |
| TC-105 | 目標 2「最後 200 行」；D5 | 功能 | 檔案 500 行，每行很短 | 呼叫 `read_task_log` | 回傳的恰是最後 200 行（第 301–500 行），前面的行不在；答案明說被截斷了 | 自動 |
| TC-106 | 目標 2「64 KB 上限」；D5 | 功能 | 檔案只有 3 行，但每行約 40 KB（總共遠超 64 KB） | 呼叫 `read_task_log` | 回傳內容不超過 64 KB，保留的是檔案**最後面**的部分；答案明說被截斷了 | 自動 |
| TC-107 | D5「平台端再檢查一次」 | 功能 | 假代理人故意不守上限，回傳 1000 行（或超過 64 KB）的內容 | 呼叫 `read_task_log` | 平台給呼叫者的答案仍不超過 200 行／64 KB，保留最後面，並說被截斷了 | 自動 |
| TC-108 | 目標 2；D5「警告 log 會送給使用者選的模型」 | 功能 | 啟動平台的 MCP 伺服器 | 列出工具、讀 `read_task_log` 的說明 | 工具名稱就是 `read_task_log`；標為唯讀（read-only）；說明文字警告「記錄內容會送到你所選的模型」，和 `list_site_files` 說明的同類警告一致 | 自動 |
| TC-109 | 目標 2「沿用 list_site_files 的路徑，不開新通道」；D4 | 功能 | 呼叫一次 `read_task_log` | 看工作佇列與平台提供的網址 | 佇列裡多一筆種類為 `read_task_log` 的工作，由同一個代理人用同一個輪詢管道領走並回答；平台沒有新增任何專供它用的網址或連線 | 自動 |
| TC-110 | D4「舊 platform.db 要能升級」 | 功能 | 一個本次修改之前建立的 `platform.db`（jobs 表的種類限制沒有 `read_task_log`，裡面已有工作與送出紀錄） | 打開它，再送出一個 `read_task_log` 工作 | 舊資料列全部保留、數量不變；新工作能排進佇列、不被資料庫拒絕 | 自動 |
| TC-111 | 目標 2「which 只能是 err、out、log」 | 例外 | 條件同 TC-101 | 呼叫 `read_task_log(…, "../../etc/passwd")`，再試 `"foo"`、空字串 | 三次都被拒絕並說明 which 只能是 err、out、log；佇列裡沒有新增工作 | 自動 |
| TC-112 | D2 | 例外 | 自己的 run；`task` 填一個不是這個 run 失敗任務的名字（例如成功的任務、或亂打的字） | 呼叫 `read_task_log` | 被拒絕，說「no recorded workdir for this task」（這個任務沒有記錄到的工作資料夾）；沒有排任何工作 | 自動 |
| TC-113 | 目標 2「沒有 workdir 就拒絕」 | 例外 | 自己的 run；失敗任務存在，但事件沒帶 `workdir`（同 TC-004 的情況） | 呼叫 `read_task_log` 讀這個任務 | 被拒絕，說「no recorded workdir for this task」；沒有排任何工作 | 自動 |
| TC-114 | D5 | 例外 | 一個 run 不是從這個平台送出的（`launches` 沒有它的紀錄），但 `get_run` 看得到 | 呼叫 `read_task_log` | 被拒絕，說「no station agent is known for this run」；沒有排任何工作 | 自動 |
| TC-115 | 目標 2「代理人離線要說」 | 例外 | 自己的 run、任務有 `workdir`，但該 run 的代理人已離線（超過離線門檻沒聯絡） | 呼叫 `read_task_log` | 被拒絕，明說是代理人離線（和其他拒絕原因的字句不同）；沒有排任何工作 | 自動 |
| TC-116 | D5 | 例外 | 自己的 run、代理人在線、任務有 `workdir`，但該資料夾裡沒有 `.command.err` | 呼叫 `read_task_log(…, "err")` | 答案說「file not found in the task folder」（任務資料夾裡找不到該檔案），不是空內容或一般錯誤 | 自動 |
| TC-117 | 目標「只給主人看」 | 例外 | 一個 run 是使用者 A 送出的 | 以使用者 B 呼叫 `read_task_log` 讀那個 run 的任務 | 得到的「找不到這個 run」答案，和 B 對 A 的 run 呼叫 `get_run` 得到的一樣；沒有排任何工作，代理人沒被打擾 | 自動 |
| TC-118 | 目標「只給主人看」 | 例外 | 一個根本不存在的 run 名 | 呼叫 `read_task_log` | 得到的答案和 TC-117 完全相同（不讓人藉此分辨「別人的」和「不存在的」） | 自動 |
| TC-119 | 目標 2「代理人端只准讀 workdir」；D4 | 例外 | 直接對代理人的處理程式送一個 `read_task_log` 工作，其 `workdir` 帶有 `..`（例如 `/site/wk/ab/../../secret`），旁邊有一個真的檔案 | 讓代理人執行這個工作 | 代理人拒絕，沒有讀取任何檔案，答案裡沒有那個檔案的內容 | 自動 |
| TC-120 | 目標 2「不得有往外的符號連結」；D4 | 例外 | 任務資料夾裡的 `.command.err` 是一個符號連結（捷徑），指向資料夾外的另一個檔案 | 讓代理人讀 which=err | 代理人拒絕（說連結指向範圍之外），資料夾外那個檔案的內容沒有出現在答案裡 | 自動 |
| TC-121 | D4「列入白名單的種類與參數」 | 例外 | 對代理人送一個 `read_task_log` 工作，但參數多帶一個白名單以外的鍵（或少帶必要的鍵） | 讓代理人執行 | 代理人拒絕這個工作，不讀任何東西；同時 `read_task_log` 已在代理人認得的工作種類清單裡 | 自動：`platform/tests/test_run_diag_tools.py`，並確認既有 `test_station_*` 靜態檢查仍綠 |

## User Story 3 — get_run 說出「取消請求已送出」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-201 | 目標 3；D3 | 功能 | 自己的 run；使用者確認取消，取消工作被代理人回報成功完成 | 呼叫 `get_run` | 回傳裡有 `cancel_requested_at`，是一個時間點（不是空值） | 自動 |
| TC-202 | 目標 3「只有確認過的取消才有」 | 例外 | 一個 run 從沒被要求取消 | 呼叫 `get_run` | 回傳裡沒有 `cancel_requested_at` 這個欄位 | 自動 |
| TC-203 | D3 | 例外 | 取消請求已建立但使用者還沒確認（待確認狀態） | 呼叫 `get_run` | 沒有 `cancel_requested_at` | 自動 |
| TC-204 | D3「確認了但還在排隊」 | 例外 | 使用者已確認取消，工作在佇列裡、代理人還沒做完 | 呼叫 `get_run` | 沒有 `cancel_requested_at` | 自動 |
| TC-205 | D3「被拒絕的取消」 | 例外 | 使用者已確認取消，但代理人回報拒絕／失敗（沒有真的送出停止） | 呼叫 `get_run` | 沒有 `cancel_requested_at` | 自動 |
| TC-206 | 目標 3「就是 `abf-platform launches` 印的那個事實」 | 功能 | 同 TC-201 | 同時看 `abf-platform launches` 的「取消請求已於 T 送出」和 `get_run` 的 `cancel_requested_at` | 兩者表示同一個時間點；`launches` 沒有印這句的 run，`get_run` 也沒有這個欄位 | 自動 |
| TC-207 | 目標 3「平台不另寫『已取消』狀態」（憲法 I.2 與 `docs/PLATFORM.md` 現有說法） | 功能 | 同 TC-201，Nextflow 之後回報該 run 失敗 | 呼叫 `get_run` | `status` 仍是 Nextflow 給的狀態（failed），沒有出現 `cancelled` 之類的新狀態；`cancel_requested_at` 只是額外的一個事實 | 自動 |

## User Story 4 — 工具登錄、既有測試與文件跟著更新（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-301 | 「MCP 工具和動作同名；動作層一致性測試」 | 功能 | 本次修改完成 | 跑 `platform/tests/test_actions_layer.py` | `actions` 裡有 `read_task_log`，MCP 伺服器裡有同名工具，其函式本體只有一次對 `actions` 的呼叫（tca13 規則）；該測試檔通過 | 自動：`test_actions_layer.py` |
| TC-302 | 「各處工具清單更新、數量不得減少」；D1(c) | 功能 | 本次修改完成 | 跑 `test_mcp.py`、`test_oauth_mcp.py`、`test_pat.py`、`test_human_channel.py`、`test_guidance.py` | 每份清單都含 `read_task_log`；每份清單的工具數量比修改前多一個、沒有任何一份變少；這些檔案通過 | 自動：上述五個檔案 |
| TC-303 | D1(c) | 功能 | 本次修改完成 | 看 `test_actions_layer.py` 的 `BASELINE` 與 tca10 | `BASELINE` 新增 `read_task_log` 並換上 `get_run` 的新說明；其餘五個既有工具的名稱、說明、參數格式與修改前逐字相同；比對仍是逐字比對 | 自動：`test_actions_layer.py` |
| TC-304 | 「每個新增／擴充的工具：新的 get_run 說明」 | 功能 | 啟動 MCP 伺服器 | 讀 `get_run` 的說明 | 說明提到失敗任務會附 `workdir`（若有）和 `cancel_requested_at`（若確認過取消） | 自動 |
| TC-305 | D1(a) | 功能 | 本次修改完成 | 跑 `test_followup3.py` 的 tcf3_03 | 對 `fail_run`、`nf2510_fail`、`nf2510_retry` 三個，失敗任務的欄位集合變成 `{name, exit_code, error_message, workdir}`；同一個測試裡其他斷言（狀態、原因文字等）一字不改；`ledger.md` 有對應的紀錄 | 自動：`test_followup3.py` |
| TC-306 | D1(b) | 功能 | 本次修改完成 | 跑 `test_nextflow_e2e.py` | 有一個具名的 `_NOT_REBUILT = {"workdir"}`；「重建出來的 run」只在 `workdir` 這一個欄位上被豁免（因為重建只讀 trace 檔，沒有完整 workdir）；`_COMPARED` 其他所有項目仍照舊逐項比對，沒有放寬；重建出的 run 的失敗任務沒有 `workdir` | 自動：`test_nextflow_e2e.py` |
| TC-307 | D1「每個改動的舊測試都登記」 | 功能 | 本次修改完成 | 讀 `specs/run-diag-tools/ledger.md` | 對 D1 列的 (a)(b)(c) 每一個被改動的舊測試，都有「舊預期／新預期／理由」三項；沒有被登記卻被改動的舊測試；diff 中沒有被刪除而無替代的斷言 | 手動（驗收審查者對照 `git diff main...HEAD` 與 `ledger.md`；見總覽疑問 3） |
| TC-308 | 「列為 web 欠的項目（ledger）」 | 功能 | 本次修改完成 | 讀 `ledger.md` | 明列「`read_task_log`、`get_run` 的 `workdir`、`get_run` 的 `cancel_requested_at` 在 web 上尚欠」 | 手動（同上） |
| TC-309 | 範圍內的文件：`docs/PLATFORM.md` 工具清單那幾行 | 功能 | 本次修改完成 | 讀 `docs/PLATFORM.md` 列工具的那幾行 | 列出 `read_task_log`，並說明它是唯讀、請代理人讀任務資料夾、有 200 行／64 KB 上限；`get_run` 那行提到 `workdir` 與 `cancel_requested_at`；文件裡的工具數量字句與實際一致 | 自動（讀文件的測試，放在 `test_run_diag_tools.py`） |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-401 | 不在範圍：`skills/`（PR #136 之後再改） | 不在範圍 | 本次修改完成 | 比對本分支與 main 的差異 | `skills/` 底下沒有任何檔案被改 | 手動（驗收審查者讀 `git diff main...HEAD --stat`；見總覽疑問 3） |
| TC-402 | 不在範圍：web | 不在範圍 | 本次修改完成 | 列出 `abf-platform web` 的所有網址路由；讀 `web.py` | 沒有任何路由或頁面提到 `read_task_log`，`web.py` 沒有為這三項新增功能；這些項目只出現在 ledger 的「web 欠」清單 | 自動 |
| TC-403 | 不在範圍：`CHANGELOG.md` 與 `docs/PLATFORM.md` 以外的文件 | 不在範圍 | 本次修改完成 | 比對本分支與 main 的差異 | `CHANGELOG.md` 沒有改；除 `docs/PLATFORM.md` 工具清單那幾行外，其他文件（含 `docs/TESTING.md`）沒有被改 | 手動（同 TC-401） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-501 | 原則 2：不得另存一份 run 狀態（計畫：`workdir` 存在失敗任務上，不另開狀態） | 功能 | 本次修改完成 | 跑 `tests/no_second_run_state_test.sh` | 通過；沒有新增任何第二份 run 狀態、狀態機或常駐監看程式 | 自動：`tests/no_second_run_state_test.sh` |
| TC-502 | 原則 2：唯一的送出路徑；安全網「送出前要確認」 | 功能 | 本次修改完成 | 同一支檢查的送出掃描涵蓋 `platform/abf_platform` 與 `platform/abf_station`；另看 `read_task_log` 的處理程式 | 掃描通過，`LAUNCH_ALLOW` 沒變多；`read_task_log` 與其處理程式不送出任何東西、不寫入站台、不刪除，只讀一個檔案 | 自動：`tests/no_second_run_state_test.sh` 與 `test_run_diag_tools.py` |
| TC-503 | 原則 3：沒有寫死的路徑 | 功能 | 本次修改完成 | 跑 `tests/no_hardcoded_paths.sh` | 通過；新程式碼裡沒有個人或叢集的寫死路徑 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-504 | 原則 4：指令層不得點名排程器 | 功能 | 本次修改完成 | 跑 `tests/command_layer_is_site_neutral.sh` | 通過 | 自動：`tests/command_layer_is_site_neutral.sh` |
| TC-505 | 「每階段全綠、不得放寬舊測試」 | 功能 | 本次修改完成 | 跑 `tests/platform_test.sh`（WSL／CI） | 整套平台測試通過；除 D1 列的三處外，沒有舊測試的斷言被移除、放寬、跳過或把預期值改成配合新輸出 | 自動：`tests/platform_test.sh`（CI） |
