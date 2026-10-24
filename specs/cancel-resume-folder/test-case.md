# 測試案例：取消／讀紀錄時，資料夾核對要認得「續跑沿用原 run 的資料夾」（cancel-resume-folder）

**規格**：`specs/cancel-resume-folder/plan.md`（本任務沒有獨立的 spec.md；規格就是這份計畫，維護者的兩句話引用在計畫「維護者原話」）　**總覽**：`test-case-overview.md`

白話背景：「續跑」是把一個卡住或失敗的分析接著跑，它會換一個新名字（原名後面加 `-a2`、`-a3`……），但刻意沿用原本那個資料夾。現在站台取消時會要求「資料夾名必須等於 run 名」，所以續跑中的分析永遠被誤拒。修好後，只有「平台自己會造出來的那種名字＋資料夾組合」才放行；其他一律照舊拒絕。

下表的測試都寫在 `platform/tests/test_station_cancel.py`，只用現成的假站台（`FakeSite`，不碰真的 Slurm／HPC）。「run-a」「run-b」是測試裡兩個不同的 run；`folder(site,"run-a")` 是 run-a 的專屬資料夾。表中 T1～T11 是計畫「失敗先行測試」表的編號，對照用。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 取消續跑中的 run（優先度 P1）

維護者原話一：「取消續跑中的 run 不該被拒」（計畫 T1、T2、T8）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 維護者原話一；T1 | 功能 | run-a 已送出；排程器裡有一個工作 `4243\|nf-run-a-a2\|tester\|<run-a 的資料夾>`（續跑的 head job：名稱是續跑名、資料夾是原資料夾） | 送出一個已確認的取消：`run_name="run-a-a2"`、`run_folder=folder(site,"run-a")`、`slurm_job_id=4243` | 結果狀態是 `done`；對排程器送出的取消指令恰好是 `["scancel 4243"]` | 自動：`platform/tests/test_station_cancel.py` |
| TC-002 | 維護者原話一；T2 | 功能 | 原 run 名稱 64 個字（`root`）；續跑第 10 次，名字依平台命名規則被截斷成 `root[:60] + "-a10"`；排程器裡有 `<號碼>\|nf-<該續跑名>\|tester\|<root 的資料夾>` | 送出已確認的取消：`run_name=<截斷後的續跑名>`、`run_folder=<root 的資料夾>` | 結果狀態是 `done`；`scancel` 恰好送出一次、號碼就是該工作 | 自動：同上 |
| TC-003 | 計畫「裁決」第 3 點（名稱核對不放寬）；T8 | 例外 | 取消的內容包是續跑名 `run-a-a2` ＋ run-a 的資料夾（兩者都對）；但排程器裡該號碼的名稱是 `nf-run-a`，不是 `nf-run-a-a2` | 送出已確認的取消 | 被拒絕（`refused`），原因是名稱不符；沒有送出任何 `scancel` | 自動：同上 |
| TC-004 | 計畫「作法」第 3 點、「裁決」第 3 點（擁有者核對不放寬） | 例外 | 續跑的取消（`run-a-a2` ＋ run-a 資料夾，名稱、資料夾都對）；排程器回報這個工作的擁有者是別人（不是部署設定的 site_user） | 送出已確認的取消 | 被拒絕；沒有送出任何 `scancel` | 自動：同上 |
| TC-005 | 計畫「作法」第 3 點（排程器回報的工作目錄核對不放寬） | 例外 | 續跑的取消（`run-a-a2` ＋ run-a 資料夾）；排程器回報這個工作的工作目錄不是 run-a 的資料夾（例如 run-b 的資料夾） | 送出已確認的取消 | 被拒絕（目錄不符）；沒有送出任何 `scancel` | 自動：同上 |
| TC-006 | 計畫「作法」第 1 點第 1 條（首次送出、重跑行為不變） | 功能 | run-a 是首次送出的 run（名字沒有 `-aN`）；排程器有 `4242\|nf-run-a\|tester\|<run-a 的資料夾>` | 送出已確認的取消：`run_name="run-a"`、資料夾是 run-a 的資料夾 | 結果狀態是 `done`、`scancel 4242` 送出一次（既有測試 `test_tc040_…` 不改、仍綠） | 自動：同上（既有 `test_tc040_a_confirmed_cancel_asks_the_scheduler_once_and_stops_that_one_job`） |

## User Story 2 — 不是這個 run 的資料夾，取消仍然被拒（優先度 P1）

維護者原話二：「其他不是這個 run 的資料夾仍要拒絕，不放寬安全檢查」（計畫 T3～T7）。以下每一條，結果都是被拒絕（`refused`）且沒有送出任何 `scancel`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | 維護者原話二；T3 | 例外 | run-a、run-b 各有自己的資料夾 | 送出已確認的取消：`run_name="run-a-a2"`、`run_folder=folder(site,"run-b")`（別人的資料夾） | 被拒絕；沒有 `scancel` | 自動：同上 |
| TC-008 | 維護者原話二；T4 | 例外 | 同上 | 取消：`run_name="run-a-a1"`、資料夾是 run-a 的（續跑從 `-a2` 起算，`-a1` 不是平台會造的名字） | 被拒絕；沒有 `scancel` | 自動：同上 |
| TC-009 | 維護者原話二；T5 | 例外 | 同上 | 取消：`run_name="run-a-a02"`、資料夾是 run-a 的（數字有前導零，不是平台造的名字） | 被拒絕；沒有 `scancel` | 自動：同上 |
| TC-010 | 維護者原話二；T6 | 例外 | 同上 | 取消：`run_name="run-b"`、資料夾是 run-a 的（名字沒有 `-aN` 尾巴，也不等於資料夾） | 被拒絕；沒有 `scancel` | 自動：同上 |
| TC-011 | 維護者原話二；T7 | 例外 | 同上 | 取消：`run_name="run-a-a2"`、`run_folder="<工作根目錄>/runs/run-a/.."` | 被拒絕；沒有 `scancel` | 自動：同上 |
| TC-012 | 維護者原話二；T7 | 例外 | 同上 | 取消：`run_name="run-a-a2"`、`run_folder="<工作根目錄>/runs/../x"` | 被拒絕；沒有 `scancel` | 自動：同上 |
| TC-013 | 計畫「完成標準」＋已核對的既有釘子 `test_station_cancel.py:138` | 例外 | 一個已確認的取消 | 分別把資料夾改成 `/etc`、把 run 名改成 `../x` | 兩者都仍被拒絕；既有測試 `test_the_agent_cancels_nothing_for_a_bundle_of_another_agent_or_another_folder` 不改、仍綠 | 自動：同上（既有測試） |

## User Story 3 — 讀續跑 run 的紀錄（優先度 P2）

計畫「裁決」第 1 點：`fetch.py` 同一個錯一起修（T9、T10）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 計畫「查證結果」fetch.py:42；T9 | 功能 | 已用 `make_records(site)` 在 run-a 的資料夾造好 `.nextflow.log` 等紀錄 | 讀紀錄：`fetch_job(site, run="run-a-a2", run_folder=folder(site,"run-a"))` | 成功（狀態 `done`），回傳的 `files` 含 `.nextflow.log` | 自動：同上 |
| TC-015 | T10 | 例外 | run-a、run-b 都造好紀錄 | 讀紀錄：`run_name="run-a-a2"` ＋ run-b 的資料夾 | 被拒絕（`refused`） | 自動：同上 |
| TC-016 | 計畫「完成標準」＋既有釘子 `test_station_cancel.py:204-206` | 例外 | run-a、run-b 都造好紀錄 | 分別讀：資料夾 `/etc`、run 名 `../x`、run 名 `run-b`（資料夾是 run-a）、資料夾 `<根>/runs/run-a/..`、多帶一個多餘欄位 | 每一種都仍被拒絕；既有測試 `test_tc035_a_folder_that_is_not_this_runs_launch_folder_is_refused` 不改、仍綠 | 自動：同上（既有測試） |

## User Story 4 — 共用判斷函式 `launch.run_folder_ok(work, run, folder)` 的單元行為（優先度 P1）

計畫 T11。這是純判斷（只比對字串，不碰檔案系統），回傳 True／False。以下 `work` 用一個任意的工作根目錄字串。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 作法 1 第 1 條；T11 | 功能 | `launch.run_folder_ok` 存在 | 呼叫 `(work, "run-a", work + "/runs/run-a")` | 回傳 True | 自動：同上 |
| TC-018 | 作法 1 第 2 條；T11 | 功能 | 同上 | 呼叫 `(work, "run-a-a2", work + "/runs/run-a")` 與 `(work, "run-a-a10", work + "/runs/run-a")` | 兩者都回傳 True | 自動：同上 |
| TC-019 | 作法 1 第 2 條（反推 `attempt_name`）；T2、T11 | 功能 | 原 run 名稱 64 個字（`root`） | 呼叫 `(work, root[:60] + "-a10", work + "/runs/" + root)`；再呼叫 `(work, root[:61] + "-a2", work + "/runs/" + root)` | 兩者都回傳 True（截斷後的續跑名依平台命名規則造） | 自動：同上 |
| TC-020 | 作法 1 第 2 條（反推而非去尾巴）；T11 | 例外 | 原 run 名稱 64 個字（`root`） | 呼叫 `(work, root[:60] + "-a2", work + "/runs/" + root)`（截斷長度不是平台會造的） | 回傳 False | 自動：同上 |
| TC-021 | 作法 1 第 3 條；T4、T5、T11 | 例外 | 同上 | 呼叫 `(work, "run-a-a0", …/run-a)`、`(work, "run-a-a1", …/run-a)`、`(work, "run-a-a02", …/run-a)` | 三者都回傳 False | 自動：同上 |
| TC-022 | 計畫「裁決」（去尾巴會放過 `x-a2` 指向任意以 `x` 開頭的資料夾）；T11 | 例外 | 同上 | 呼叫 `(work, "x-a2", work + "/runs/xy")`；`(work, "run-b", work + "/runs/run-a")`（無 `-aN` 尾巴且名稱≠資料夾） | 兩者都回傳 False | 自動：同上 |
| TC-023 | 作法 1 第 2 條（root 須符合 RUN_NAME，因此沒有 `/`、`..`）；T7、T11 | 例外 | 同上 | 呼叫 `(work, "run-a-a2", work + "/runs/run-a/..")`、`(work, "run-a-a2", work + "/runs/../x")` | 兩者都回傳 False | 自動：同上 |
| TC-024 | 作法 1 第 2 條（folder 須在 `work/runs/` 底下）；T11 | 例外 | 同上 | 呼叫 `(work, "run-a-a2", "/etc")`；`(work, "run-a-a2", "/other-work/runs/run-a")` | 兩者都回傳 False | 自動：同上 |
| TC-025 | T11（work 結尾斜線）；字面規則，見總覽疑問 1 | 例外 | `work = "/w/"`（結尾有斜線） | 呼叫 `("/w/", "run-a", "/w/runs/run-a")` | 回傳 False（規則是字面的 `work + "/runs/" + …`，不做路徑正規化，得到的前綴是 `/w//runs/`） | 自動：同上 |
| TC-026 | T11（空字串） | 例外 | 同上 | 呼叫 `(work, "run-a-a2", "")` 與 `(work, "run-a", "")` | 兩者都回傳 False | 自動：同上 |
| TC-027 | T11（非字串 folder） | 例外 | 同上 | 呼叫 `(work, "run-a-a2", None)`、`(work, "run-a-a2", 5)`、`(work, "run-a-a2", ["x"])` | 都回傳 False，不丟例外 | 自動：同上 |

## 不在範圍（計畫「不做」「不准動」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-028 | 不做：不處理 Google Batch 的取消 | 不在範圍 | 既有測試 `test_gcb_launch.py:845-853` | 跑 Google Batch 的取消測試 | 全綠且測試內容未改（Google Batch 的取消不走新函式） | 自動：`platform/tests/test_gcb_launch.py` |
| TC-029 | 不做：不改錯誤訊息文字 | 不在範圍 | 同 TC-007（別人的資料夾） | 送出該取消，讀回拒絕訊息 | 訊息仍含原文「run 名稱或專屬資料夾不對」；讀紀錄被拒時仍含「run 名稱或專屬資料夾不對」 | 自動：同上 |
| TC-030 | 不做：不改續跑內容包與平台記錄的組法（`launch.py:903-904`、`jobs.py`、`build.py:303`） | 不在範圍 | 既有測試 `test_resume_render.py:94`、`test_resume_lineage.py:298`、`test_station_resume.py` | 跑這些測試 | 全綠且斷言未改（續跑仍是 `run_name=<root>-aN`、`run_folder=原資料夾`） | 自動：`platform/tests/` 下對應檔案 |
| TC-031 | 範圍：只准改 5 個檔；「不准動」清單零命中 | 不在範圍 | 實作完成後 | 閱卷者以 `git diff --name-only <base>...HEAD` 核對 | 只含 `platform/abf_station/launch.py`、`cancel.py`、`fetch.py`、`platform/tests/test_station_cancel.py`、`specs/cancel-resume-folder/ledger.md`；`platform/abf_platform/**`、`platform/abf_launch/**`、`gcb_launch.py`、`hooks/`、`.claude-plugin/plugin.json`、`spec.md`、`test-case*.md`、`.github/`、憲法零改動；`launch.py` 只多了 `run_folder_ok`、`cancel.py` 只改資料夾比對那一行、`fetch.py` 只改資料夾比對那一行 | 手動：閱卷者核對 git 差異（不是 `docs/TESTING.md` 的步驟，見總覽疑問 3） |
| TC-032 | 不做：不需要 migration、不新增設定鍵 | 不在範圍 | 實作完成後 | 閱卷者檢查差異 | 沒有 migration 檔、沒有資料表或 JSON 欄位內容的改動、沒有新設定鍵（`cancel.py:55`、`:59` 的名稱與工作目錄核對原樣未動） | 手動：閱卷者核對 git 差異 |

## 完成標準（計畫「done when」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-033 | 完成標準第 1 條；環境事實（T1 須先紅） | 功能 | 實作前的 base 上 | 先只加測試、執行 T1、T2、T9、T11 | 這四個在 base 上是紅的（T1 若在 base 上就綠，代表計畫前提錯，回報 BLOCKED）；修好後 T1～T11 全綠 | 自動：`platform/tests/test_station_cancel.py` |
| TC-034 | 完成標準第 1 條 | 功能 | 實作完成後 | 在 WSL 跑整套 `bash tests/run_all.sh` | 全綠 | 自動：`tests/run_all.sh` |
| TC-035 | 完成標準第 3 條 | 功能 | 實作完成後 | 閱卷者對照 base 比對 `test_station_cancel.py` 與其他被動到的測試檔 | 既有斷言沒有被刪、跳過、放寬或改期望值；新增測試（含參數化展開）不超過 20 條 | 手動：閱卷者核對 git 差異 |
| TC-036 | 完成標準第 4 條 | 功能 | 實作完成後 | 閱卷者讀新增測試 | 只用現成的 `FakeSite`／假平台，沒有任何連 Slurm／HPC 的呼叫 | 手動：閱卷者讀測試碼 |

## 憲法與安全網

安全網規則（憲法 Safety Net）：每個平台的寫入工具（`launch`、`cancel`、`resume`、`relaunch`、`forget`）沒有確認就拒絕；取消只停「確認過的那一個 head job」。這次改動動到取消的資料夾核對，所以要證明這兩點沒鬆。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | Safety Net：寫入工具無確認即拒；專長守則「確認管道」 | 例外 | 續跑的取消內容包（`run-a-a2` ＋ run-a 資料夾，其餘都對） | 拿掉確認、或改動內容包任一欄位、或多加一個欄位後送出 | 全部被拒絕，沒有送出 `scancel`；既有測試 `test_tc043_a_cancel_without_a_confirmation_or_with_a_changed_content_is_refused` 不改、仍綠 | 自動：`platform/tests/test_station_cancel.py` |
| TC-038 | Safety Net：取消只停確認過的那一個工作 | 功能 | 排程器裡除了續跑的 head job `4243\|nf-run-a-a2\|tester\|<run-a 資料夾>`，還有別的工作 `999\|someone-else\|other\|/elsewhere` | 送出續跑的取消 | 問排程器恰好一次（`squeue -h -j 4243 -o …`）；`scancel` 只有 `scancel 4243` 一次；佇列裡其他工作原封不動 | 自動：同上 |
