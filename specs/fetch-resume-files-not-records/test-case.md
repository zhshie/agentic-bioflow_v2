# 測試案例：站台 fetch 不准把續跑檔當紀錄讀回（fetch-resume-files-not-records）

**規格**：`specs/fetch-resume-files-not-records/plan.md`（本件為 A 級，沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

名詞先說白：
- **站台代理的 fetch**：使用者打「把這次跑的紀錄抓回來」時，站台上的小程式去專屬資料夾讀 Nextflow 自己寫的日誌，再依日誌裡寫的「trace 檔名」去讀那個檔，送回平台。
- **續跑檔**：使用者續跑（resume）一次，平台會在同一個專屬資料夾再寫 `head-N.sh`（含送出指令）、`params-N.yaml`（完整參數）、`extra-N.config`（額外設定）。N 是第幾次續跑。這些是平台寫的，不是 Nextflow 的紀錄，不該被讀回。
- **trace 檔名來自日誌**：日誌是站台上的檔，內容不可信；若日誌被寫成「trace 檔叫 params-2.yaml」，現在程式會真的去讀它。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、不該出現的東西出現時，系統怎麼反應（拒絕、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

自動項的測試檔：新測試在 `platform/tests/test_station_cancel.py`（計畫命名 `test_tc036_a_trace_name_that_is_a_file_the_platform_wrote_for_a_resume_is_refused`）；跑法 `ABF_PYTEST_TARGETS=tests/test_station_cancel.py bash tests/platform_test.sh`（在 `platform/` 下）。每個自動項的測試要在註解寫出本檔的 TC 編號。

## User Story 1 — 續跑會寫的三種檔不被當成紀錄讀回（優先度 P1）

共同前置（TC-001～TC-009 通用，除非另寫）：站台上有一個平台建的專屬資料夾，裡面是 `make_records` 做出的平常紀錄（`.nextflow.log`、`.nextflow.log.1`、`.nextflow/history`、`trace-1.txt`、`tower.token`、`params.yaml`）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「目標」「失敗先行測試」；證據一 | 例外 | 資料夾裡多一個檔 `params-2.yaml`，內容 `SECRET_RESUME_VALUE`；`.nextflow.log` 改成含一行 `Workflow started -- trace file: params-2.yaml` | 對這個專屬資料夾跑 fetch_run_records | 工作狀態是 `done`；讀回的檔案清單裡**沒有** `params-2.yaml` | 自動：`platform/tests/test_station_cancel.py`（參數化 `params-2.yaml`） |
| TC-002 | 同上 | 例外 | 同 TC-001，但檔名是 `extra-2.config`，日誌那行寫 `extra-2.config` | 同上 | 工作狀態 `done`；讀回的檔案清單裡**沒有** `extra-2.config` | 自動：同檔（參數化 `extra-2.config`） |
| TC-003 | 同上 | 例外 | 同 TC-001，但檔名是 `head-2.sh`，日誌那行寫 `head-2.sh` | 同上 | 工作狀態 `done`；讀回的檔案清單裡**沒有** `head-2.sh` | 自動：同檔（參數化 `head-2.sh`） |
| TC-004 | 同上（拒絕要說出來） | 例外 | 同 TC-001／002／003 三種情況各一次 | 同上 | 回應的「已拒絕」清單中，至少有一項點名該檔名（`params-2.yaml`／`extra-2.config`／`head-2.sh`） | 自動：同檔 |
| TC-005 | 計畫「作法・決定」：樣式 `[0-9]+` 涵蓋多位數 | 例外 | 同 TC-001，但檔名依序換成 `params-10.yaml`、`extra-10.config`、`head-10.sh`（內容 `SECRET_RESUME_VALUE`） | 同上 | 三者都不在讀回清單，且「已拒絕」清單點名該檔名 | 自動：同檔 |
| TC-006 | 計畫「作法」：拒絕訊息沿用現句；「不做」：不新增使用者可見錯誤文字 | 例外 | 同 TC-001 | 同上，看拒絕清單那一項的文字 | 文字與現有拒絕句同一格式：`trace 檔 '<檔名>' 不在專屬資料夾內或名稱不合，已拒絕`，沒有新增的句子 | 自動：同檔 |
| TC-007 | 檔頭承諾「Nothing is written」 | 功能 | 同 TC-001 | 跑 fetch 前後各拍一次資料夾快照，並看站台收到的指令 | 資料夾前後完全相同；沒有任何刪除類或危險指令被送到站台 | 自動：同檔（比照 `test_tc034`） |
| TC-008 | 計畫「對照組」 | 功能 | 日誌指向 `trace-1.txt`（再另測 `trace-2026-10-29_1.txt`，兩者都先寫成有內容的真檔） | 跑 fetch | 兩個名字各自被讀回，讀回內容與站台上檔案的位元組完全相同 | 自動：同檔 |
| TC-009 | 計畫「作法」：不改讀日誌與 history 的路徑 | 功能 | 同 TC-001（日誌只指向被擋的名字） | 跑 fetch | 讀回清單仍包含 `.nextflow.log`、`.nextflow.log.1`、`.nextflow/history`（被擋的只有那個 trace 名字） | 自動：同檔 |

## User Story 2 — 合法輸入與既有保證不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 計畫「完成標準」「對照組」：既有 `test_tc034`、`test_tc035` 不改、保持綠 | 功能 | 本分支改完 | 跑整個 `test_station_cancel.py` | 原有的每一個測試都通過；新測試也通過 | 自動：`platform/tests/test_station_cancel.py` |
| TC-011 | 計畫「不做」：不動 `_NOT_RECORDS` 既有成員 | 例外 | 日誌的 trace 名依序寫成首次送出的固定檔名：`tower.token`、`params.yaml`、`head.sh`、`nextflow.config`、`samplesheet.csv`、`gcb.config`、`aws.config`（各自在資料夾裡有一個有內容的檔） | 跑 fetch | 每一個都不在讀回清單，且內容不在回應中，與改動前一樣 | 自動：`platform/tests/test_station_cancel.py` |
| TC-012 | 計畫「作法」：第 80 行其餘條件不變 | 例外 | 日誌的 trace 名依序寫成 `slurm-123.out`、`.nextflow.config`（各自有內容的檔） | 跑 fetch | 都不在讀回清單，與改動前一樣 | 自動：`platform/tests/test_station_cancel.py` |
| TC-013 | 計畫「作法」：`_NOT_RECORDS` 集合保留；環境事實：三個測試檔以 `in fetch._NOT_RECORDS` 斷言 | 功能 | 本分支改完 | 跑 `test_aws_launch.py:644`、`test_azure_launch.py:627`、`test_gcb_launch.py:1056` 那三條斷言所在的測試 | 三條都通過（`aws.config`、Azure 設定檔名、`gcb.config` 仍在 `fetch._NOT_RECORDS` 裡） | 自動：`platform/tests/test_aws_launch.py`、`test_azure_launch.py`、`test_gcb_launch.py` |
| TC-014 | 計畫「兩分支比對」；專案校準失敗 #1 | 功能 | 兩個分支：`origin/v3` 與本分支 | 在兩邊各跑同一份（舊版內容的）`test_station_cancel.py` | 舊有測試在兩邊結果相同（通過／失敗名單一致）；唯一差別是新增的測試 | 自動：`platform/tests/test_station_cancel.py`（兩分支各跑） |
| TC-015 | 計畫「失敗先行測試」：改程式前先確認紅 | 功能 | 新測試放進 `origin/v3` 的程式碼上（程式未改） | 跑新測試 | 在未改程式的 base 上，TC-001／002／003 對應的參數案例失敗（該檔名出現在讀回清單、內容被送回）；在本分支上通過 | 自動：`platform/tests/test_station_cancel.py` |

## User Story 3 — 這次明講不做的事（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 裁決 1：不改成白名單（使用者可用 `-with-trace` 任意命名） | 不在範圍 | 日誌的 trace 名依序寫成 `trace.txt`、`trace-3.txt`（各自有內容的真檔） | 在 `origin/v3` 與本分支各跑一次 fetch | 兩個名字在兩邊都被讀回，內容相同；兩分支結果一致 | 自動：`platform/tests/test_station_cancel.py`（兩分支各跑） |
| TC-017 | 裁決 2：樣式不擴大，只補三種 | 不在範圍 | 日誌的 trace 名依序寫成 `params.txt`、`head.log`（像但不符樣式；有內容的真檔） | 跑 fetch | 兩個名字都被讀回，內容相同 | 自動：`platform/tests/test_station_cancel.py` |
| TC-018 | 計畫「範圍：檔案」「不准碰」 | 不在範圍 | 本分支相對 `origin/v3` 的差異 | `git diff --stat origin/v3...HEAD`（含未提交的 `git diff`） | 只列 `platform/abf_station/fetch.py`、`platform/tests/test_station_cancel.py`（以及本任務資料夾下的 ledger）；沒有 `launch.py`、`gcb_launch.py`、`aws_launch.py`、`azure_launch.py`、`platform/abf_platform/web*.py`、`cloud_store.py`、`records.py`、k8s／計算環境類型相關檔 | 手動：閱卷者看 git diff（本件不改文件，故無 `docs/TESTING.md` 條目） |
| TC-019 | 計畫「範圍」「不做」：`fetch.py` 只動一個常數與一個條件 | 不在範圍 | 同 TC-018 | 看 `fetch.py` 的 diff | 只新增一個模組層常數與第 80 行的條件多一個 `or`；`_TRACE`、`_LOG`、`LIMIT`、`_NOT_RECORDS` 的既有成員、讀日誌與 history 的路徑一行都沒動；程式碼沒有新增小寫單字 `azure` | 手動：閱卷者看 git diff；`test_station_static.py` 自動把關小寫 azure |
| TC-020 | 計畫「完成標準」：沒有既有測試被改弱；環境事實「不准改」清單 | 不在範圍 | 同 TC-018 | 看所有被動到的測試檔的 diff，並看 `spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` 的 diff | 既有測試沒有被刪、跳過、放寬或改期望值（只有新增）；那些禁改檔的 diff 為空 | 手動：閱卷者看 git diff |
| TC-021 | 計畫「不做」：不新增使用者可見錯誤文字、不改文件、不需要 migration | 不在範圍 | 同 TC-018 | 看 diff 有無文件、migration、資料結構檔 | 沒有文件變動、沒有 migration、沒有資料結構或資料內容變動；拒絕文字與 TC-006 相同 | 手動：閱卷者看 git diff |

## 憲法與安全網

涉及的規則：憲法中「機密不隨回應外洩」（`.specify/memory/constitution.md` 約 198–213 行，續跑檔 `head-N.sh` 含送出指令、`params-N.yaml` 含完整參數）；專案校準失敗 #1（修閘門時閘門變窄、舊的被擋形狀被放過）；backend 專長守則「密鑰不得出現在日誌或任何回應中」「錯誤訊息不露內部路徑」。本件不加路由、不寫入、不涉及擁有者與資料結構，所以專長守則其餘幾條（動作層對等、跨使用者、確認管道、migration）不適用，TC-021 已涵蓋「不需要 migration」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 機密不隨回應外洩；backend 守則：密鑰不得出現在任何回應 | 例外 | 同 TC-001／002／003／005 的各種續跑檔，內容都是 `SECRET_RESUME_VALUE` | 跑 fetch，把整份回應轉成文字 | `SECRET_RESUME_VALUE` 不出現在整份回應的任何位置（含讀回清單、已拒絕清單、訊息）；拒絕清單裡的檔名不超過 80 字、不帶站台內部完整路徑 | 自動：`platform/tests/test_station_cancel.py` |
| TC-023 | 專案校準失敗 #1：修閘門不得讓舊的被擋形狀通過 | 例外 | 日誌的 trace 名寫成改動前就被擋的形狀：站台外的絕對路徑、`../other.txt`、TC-011 的固定檔名、TC-012 的 `slurm-`／`.nextflow` 開頭、`.nextflow.log.2` 符號連結 | 在 `origin/v3` 與本分支各跑一次 | 每一種在兩邊都被拒絕，拒絕數量與內容一致；本分支沒有任何一種變成被讀回 | 自動：`platform/tests/test_station_cancel.py`（兩分支各跑；含既有 `test_tc035_a_link_a_trace_outside...`） |
