# 測試案例：取消的分析不再記錄「Report file already exists」（abort-report-overwrite）

**規格**：`.specify/bugs/abort-report-overwrite/assessment.md`（這是 bug，沒有 spec.md；計畫就是 assessment.md 的 Proposed Remediation）　**總覽**：`test-case-overview.md`

名詞先講白：「config」＝平台替每次分析產生的 `nextflow.config` 設定檔；「區塊」＝這次要加在設定檔最後面、帶註解的那幾行；「離線真 Nextflow」＝測試裡啟動釘定版本（26.04.7）的真 Nextflow，不連 Seqera、不連叢集（做法同 `platform/tests/test_nextflow_e2e.py`）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

維護者的兩句話（原文）：

- 「取消的分析，記錄裡不要再出現 Report file already exists。」→ TC-001～TC-012
- 「正常跑完的分析，報告照舊產生。」→ TC-013、TC-014

## User Story 1 — 取消的分析，記錄裡不要再出現 Report file already exists（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 修法：config 末尾加兩個設定；維護者例 1 | 功能 | 運算環境（CE）有自己的 Nextflow 設定文字 | 平台為一次分析產生 `nextflow.config` | 檔案最後面有 `report.overwrite = true` 與 `timeline.overwrite = true` 兩行，且這兩行在使用者設定文字之後 | 自動：`platform/tests/test_station_launch.py` |
| TC-002 | 修法：使用者的設定文字在前、原封不動 | 功能 | CE 設定文字有多行、結尾有換行 | 同上 | 產生的檔案開頭逐字等於 CE 設定文字，中間沒被改、沒被插入、沒被重排 | 自動：`platform/tests/test_station_launch.py` |
| TC-003 | 修法：使用者的設定文字在前、原封不動 | 功能 | CE 設定文字結尾沒有換行 | 同上 | 檔案開頭仍是該文字，且區塊從新的一行開始（文字與區塊沒有黏在同一行）；文字本身沒被改 | 自動：`platform/tests/test_station_launch.py` |
| TC-004 | 修法：「一律」加上 | 功能 | CE 完全沒有 Nextflow 設定文字 | 同上 | 檔案仍有原本那行說明「沒有設定」的 `//` 註解，後面同樣接著兩行 overwrite 設定（既有的 `test_launch_bundle.py` 「以 `//` 開頭、以換行結尾」那一條仍成立） | 自動：`platform/tests/test_station_launch.py` |
| TC-005 | 修法：「一個清楚註解的區塊」 | 功能 | 同 TC-001 | 讀區塊（使用者文字之後的全部內容） | 兩行設定之前有註解行（`//` 開頭），說明為什麼加（取消時報告會被寫兩次）；人只看這個區塊就知道它是平台加的 | 自動：`platform/tests/test_station_launch.py` |
| TC-006 | 修法：「only these two; not trace/dag」 | 功能 | 同 TC-001 | 取區塊中所有不是註解、不是空白的行 | 恰好兩行：`report.overwrite = true` 與 `timeline.overwrite = true`；沒有別的設定（包括沒有 `report.enabled`、`timeline.enabled`、`report.file`） | 自動：`platform/tests/test_station_launch.py` |
| TC-007 | 修法：「區塊是使用者看到的 bundle 的一部分」 | 功能 | 使用者用終端機指令發起一次分析 | 指令把要送出的內容全部顯示出來，等待 y/N | 顯示的 `nextflow.config` 段落包含區塊（兩行設定與註解），使用者在回答 y 之前就看得到 | 自動：`platform/tests/test_launch_cli.py` |
| TC-008 | 修法：「區塊是 bundle 雜湊的一部分」 | 例外 | 使用者已回答 y，確認紀錄綁著當時內容的雜湊 | 在送出前，把 bundle 裡 `nextflow.config` 的區塊拿掉再交給代理人 | 代理人拒絕，不送出、不寫任何檔案（跟「確認後被改過的 bundle 會被拒」同一種拒絕，見 `test_tc007_a_bundle_changed_after_the_yes_is_refused`） | 自動：`platform/tests/test_station_launch.py` |
| TC-009 | 修法：區塊是送出內容的一部分 | 功能 | 使用者已確認一次分析 | 代理人完成送出 | 叢集上 run 資料夾裡的 `nextflow.config`，逐位元組等於使用者確認的那份（含區塊）；代理人用自己的設定重建 bundle 得到的結果與確認的一致，沒有因為多了區塊而被拒 | 自動：`platform/tests/test_station_launch.py` |
| TC-010 | 維護者例 1：「取消的分析，記錄裡不要再出現 Report file already exists。」（離線，若做得到） | 功能 | 離線真 Nextflow；用平台產生的 `nextflow.config`（含區塊），另外讓測試用的 run 開啟報告與時間軸；一個跑得夠久的最小流程 | 啟動分析，在它跑到一半時取消（中止） | run 結束後，該 run 的 `.nextflow.log` 裡找不到「already exists」，也找不到「report.overwrite」「timeline.overwrite」這兩個提示字樣 | 自動：`platform/tests/test_nextflow_e2e.py` |
| TC-011 | 紅燈先行：證明 TC-010 會失敗 | 功能 | 同 TC-010，但設定檔不含區塊（只有使用者文字） | 同樣啟動、同樣取消 | `.nextflow.log` 裡出現「Report file already exists」（或時間軸同類句子）。這一條存在，才證明 TC-010 的「找不到」不是因為取消根本沒走到寫報告的地方 | 自動：`platform/tests/test_nextflow_e2e.py` |
| TC-012 | 維護者例 1，真實叢集 | 功能 | 國網 NCHC，用修好的版本發起一個跑幾分鐘的小分析 | 照 `docs/TESTING.md` 的「取消小 run」步驟取消，之後打開該 run 的 `.nextflow.log` | 記錄裡沒有「Report file already exists」，也沒有「Timeline file already exists」。若 `fix.md` 記錄了 TC-010／TC-011 離線做不到的原因，則這一條就是取消案例唯一的證據，必須在維護者的 NCHC 複驗（`specs/007b-launch/acceptance-nchc.md`）裡留下結果 | 手動：`docs/TESTING.md`（取消小 run，TC-048 步驟）與 NCHC 複驗紀錄 |

## User Story 2 — 正常跑完的分析，報告照舊產生（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 維護者例 2：「正常跑完的分析，報告照舊產生。」（離線） | 功能 | 離線真 Nextflow；用平台產生的 `nextflow.config`（含區塊），測試用的 run 開啟報告與時間軸；流程會正常結束 | 啟動分析並等它跑完 | run 以成功結束；`pipeline_info`（報告位置）裡有一份報告 html 與一份時間軸 html，檔案非空；`.nextflow.log` 沒有關於這兩份檔案的 ERROR。這同時證明帶區塊的設定檔 Nextflow 讀得懂 | 自動：`platform/tests/test_nextflow_e2e.py` |
| TC-014 | 維護者例 2，真實叢集 | 功能 | 國網 NCHC，用修好的版本發起一個正常會跑完的小分析 | 等它成功結束，看 run 的 `results/pipeline_info/` | 裡面照舊有執行報告與時間軸，數量與沒修之前的正常 run 一樣（不多、不少） | 手動：NCHC 複驗（維護者）；步驟寫入 `docs/TESTING.md` 發起／取消那一段時順帶檢查 |

## User Story 3 — 既有檢查不被削弱，範圍不外溢，文件說清楚（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 計畫：「Update any hash/golden expectations only where the new block is the sole difference, and list each in the ledger」 | 功能 | 修好之後，原本逐字比對整份 config 的測試（例如 `test_launch_bundle.py` 的 `== "process.executor = 'slurm'\n"`、`test_launch_cli.py` 的 `config == ["process.executor = 'slurm'"]`）必須改 | 比對這些測試修改前後 | 每一處改動只是把期望值多接上區塊，仍斷言「使用者文字逐字在前」；沒有改成「包含即可」之類較鬆的寫法、沒有被跳過；每一處都列在 `fix.md` | 自動：`platform/tests/test_launch_bundle.py`、`platform/tests/test_launch_cli.py`（驗收者對照 diff 與 `fix.md`） |
| TC-016 | 計畫：「`launch.py` 是唯一允許產生 bundle 的檔」 | 功能 | 修好之後的程式碼 | 在 `platform/` 的非測試程式裡找 `report.overwrite`、`timeline.overwrite` | 只出現在 `platform/abf_station/launch.py`，別的檔案沒有複製一份 | 自動：`platform/tests/test_station_launch.py` |
| TC-017 | 計畫：「First search upstream … cite what you find in the ledger」 | 功能 | 修好之後 | 讀 `.specify/bugs/abort-report-overwrite/fix.md` | 有一段寫了搜過 nextflow-io/nextflow 的 issue／PR、找到什麼（附連結或編號），並明說「有／沒有已釋出的版本修了這個重複渲染」；即使有，也說明仍為釘定的 26.04.7 套用設定修法；找不到就明寫「查不到」，不是留白 | 手動：驗收者讀 `fix.md` |
| TC-018 | 計畫：「Docs: PITFALLS entry」 | 功能 | 修好之後 | 讀 `docs/PITFALLS.md` 最後新增的條目（編號接在 45 之後） | 條目寫了：看到什麼（NCHC 複驗 run `fu3-cancel` 記錄的兩行錯誤）、原因（取消時完成事件跑兩次，來源是已讀的 Nextflow 原始碼，與 43 條同源）、怎麼修、離線證明了什麼與還沒證明什麼（若 TC-010 做不到要寫明）。不寫沒讀過的東西 | 手動：憲法第 8 條 Procedure P2（`docs/TESTING.md`） |
| TC-019 | 計畫：「note in docs/PLATFORM.md where the rendered config is described」 | 功能 | 修好之後 | 讀 `docs/PLATFORM.md` 描述送出時顯示與寫入 `nextflow.config` 的那段（約第 305～309 行） | 該段說明平台會在 config 最後面加一個區塊、內容是 `report.overwrite`／`timeline.overwrite`、為什麼加、使用者的設定文字仍在前面 | 自動：`platform/tests/test_launch_docs.py` |
| TC-020 | 不在範圍：trace／dag 的 overwrite | 不在範圍 | 同 TC-001 | 在整份產生的 config 裡找 `trace.overwrite`、`dag.overwrite` | 找不到；config 沒有為 trace 或 dag 加任何設定 | 自動：`platform/tests/test_station_launch.py` |
| TC-021 | 不在範圍：「the double `complete` itself」 | 不在範圍 | 修好之後的 diff | 看接收端（receiver）與訊息處理程式，以及它的既有測試（如 `test_receiver_nf2510.py` 的寬限期測試） | 接收端程式與其測試沒有任何改動，且測試仍全綠；沒有人去改「完成事件送兩次」這件事 | 自動：既有 `platform/tests/test_receiver*.py` 不改、全綠（驗收者核對 diff） |
| TC-022 | 不在範圍：CI config | 不在範圍 | 修好之後的 diff | 看 diff 是否碰 `.github/` | 沒有任何檔案在 `.github/` 底下被改 | 手動：驗收者核對 diff |
| TC-023 | 不在範圍：`plugin/` | 不在範圍 | 修好之後的 diff | 看 diff 是否碰 `plugin/`（含 `hooks/`、`.claude-plugin/`） | 沒有任何檔案在 `plugin/`、`hooks/`、`.claude-plugin/` 底下被改 | 手動：驗收者核對 diff |

## 憲法與安全網

這次改的是平台唯一的送出路徑（原則 2）所產生的檔案內容，碰到「送出前完整顯示並等確認」（安全網）、原則 2、原則 3、原則 8。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | 安全網：送出前完整顯示並等待確認 | 例外 | 沒有確認紀錄就叫代理人送出 | 照既有 `test_unconfirmed_launch_is_refused` 與 `test_tc008_*` 的做法送出 | 仍被拒絕，沒有 sbatch、沒有建資料夾；這些既有測試沒被改動、沒被跳過 | 自動：`platform/tests/test_station_launch.py` |
| TC-025 | 原則 2：只有一條自己的送出路徑，不留第二份 run 狀態 | 功能 | 修好之後 | 跑 `tests/no_second_run_state_test.sh` | 通過；`LAUNCH_ALLOW` 仍只有原本那一條、沒新增、沒過期；這次沒有新的送出動作，也沒有任何檔案紀錄 run 的狀態 | 自動：`tests/no_second_run_state_test.sh` |
| TC-026 | 原則 3：不寫死個人／叢集路徑 | 功能 | 修好之後 | 跑 `tests/no_hardcoded_paths.sh`，並讀區塊內容 | 通過；區塊裡沒有任何路徑、帳號、叢集名稱 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-027 | 原則 8：量過或讀過原始碼才下結論，結果記在 PITFALLS | 功能 | 修好之後 | 對照 PITFALLS 新條目的每個論斷 | 每個論斷都對應一次真的失敗（NCHC 的兩行錯誤）或真的讀過的原始碼；沒有憑記憶補的句子 | 手動：Procedure P2（`docs/TESTING.md`） |
