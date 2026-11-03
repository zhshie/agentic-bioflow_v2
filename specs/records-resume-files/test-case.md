# 測試案例：平台端 records.name_ok 也拒收續跑檔（records-resume-files）

**規格**：`specs/records-resume-files/plan.md`（本件是 A 級小修正，沒有 spec.md，計畫即規格；沒有 FR 編號，「對應需求」欄指計畫的段落）　**總覽**：`test-case-overview.md`

名詞：「續跑檔」＝續跑（resume）時 launch 在 run 資料夾寫下的 `head-N.sh`、`params-N.yaml`、`extra-N.config`（N 是數字），可能含密鑰。「平台端那道鎖」＝`platform/abf_platform/records.py` 的 `name_ok`，決定平台收不收某個檔名。「站台端那道鎖」＝`platform/abf_station/fetch.py` 的 `_RESUME_FILE`，已經拒收續跑檔。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、不該收的東西進來時，系統怎麼反應（拒絕、不寫入）。
- **不在範圍**：計畫明講這次不做的事；確認真的沒做。

## User Story 1 — 平台端拒收三種續跑檔（優先度 P1）

維護者的話（計畫「維護者原話」）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」；`records.py:5` 檔頭「Only the names Nextflow writes for these records are accepted.」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「失敗先行測試」第 1 點；目標 | 例外 | 修改後的 `records.py` | 問平台端那道鎖：`records.name_ok("head-1.sh")` | 回答 False（不收） | 自動：`platform/tests/test_records_names.py` |
| TC-002 | 同上 | 例外 | 同上 | `records.name_ok("params-2.yaml")` | 回答 False | 自動：同上 |
| TC-003 | 同上 | 例外 | 同上 | `records.name_ok("extra-10.config")` | 回答 False | 自動：同上 |
| TC-004 | 同上 | 例外 | 同上 | `records.name_ok("head-123.sh")`（多位數字） | 回答 False | 自動：同上 |
| TC-005 | 計畫「失敗先行測試」第 2 點 | 例外 | 一個空的暫存資料夾；檔案內容是 `SECRET_RESUME` 的 base64 | `store_files(暫存資料夾, "run-one", [{"name": "head-1.sh", "data": …}])` | 回傳的 `files` 是空的；`refused` 剛好一項；硬碟上 `run-one/head-1.sh` 不存在 | 自動：同上 |
| TC-006 | 同上 | 例外 | 同上 | 同上，檔名 `params-2.yaml` | 同 TC-005：`files == []`、`refused` 一項、硬碟上沒有該檔 | 自動：同上 |
| TC-007 | 同上 | 例外 | 同上 | 同上，檔名 `extra-10.config` | 同 TC-005 | 自動：同上 |
| TC-008 | 同上 | 例外 | 同上 | 同上，檔名 `head-123.sh` | 同 TC-005 | 自動：同上 |
| TC-009 | 計畫「失敗先行測試」第 2 點；專長守則（錯誤訊息與日誌不洩密） | 例外 | 同 TC-005，四個檔名各做一次 | 看 `store_files` 的整個回傳內容 | 回傳裡找不到 `SECRET_RESUME`（內容沒有被回送） | 自動：同上 |
| TC-010 | 計畫「決定」：不新增拒絕訊息，走既有「not a record of Nextflow」 | 例外 | 同 TC-005 | 看 `refused` 那一項的文字 | 含檔名與既有的 `not a record of Nextflow`（沒有新增別種訊息） | 自動：同上 |

## User Story 2 — 真正的紀錄與合法輸入完全不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 計畫「失敗先行測試」第 3 點（對照組）；目標「真正的 Nextflow 紀錄結果不變」 | 功能 | 修改後的 `records.py` | `records.name_ok("head.log")` | 回答 True（仍收） | 自動：`platform/tests/test_records_names.py` |
| TC-012 | 同上 | 功能 | 同上 | `records.name_ok("params.txt")` | True | 自動：同上 |
| TC-013 | 同上 | 功能 | 同上 | `records.name_ok("trace-1.txt")` | True | 自動：同上 |
| TC-014 | 同上 | 功能 | 同上 | `records.name_ok(".nextflow.log.2")` | True | 自動：同上 |
| TC-015 | 同上（證明樣式沒有過寬） | 功能 | 同上 | `records.name_ok("head-1.sh.txt")`（只是長得像，結尾多了 `.txt`） | True | 自動：同上 |
| TC-016 | 同上（證明樣式沒有過寬） | 功能 | 同上 | `records.name_ok("params-x.yaml")`（N 不是數字） | True | 自動：同上 |
| TC-017 | 同上（證明樣式沒有過寬） | 功能 | 同上 | `records.name_ok("extra-1.json")`（副檔名不是 sh/yaml/config） | True | 自動：同上 |
| TC-018 | 計畫「失敗先行測試」第 3 點：原有被擋的八個名字仍為 False | 例外 | 同上 | 對 `tower.token`、`params.yaml`、`head.sh`、`nextflow.config`、`samplesheet.csv`、`gcb.config`、`aws.config`、`azure.config` 逐一問 `name_ok` | 八個都回答 False，沒有一個被放寬 | 自動：同上（既有測試 `test_the_old_five_are_still_refused`、`test_the_platform_refuses_every_file_the_launch_writes_that_is_not_a_record` 與新增者都要過） |
| TC-019 | 計畫「失敗先行測試」第 3 點：#266 的既有測試全綠；「範圍」：不改既有斷言 | 功能 | 修改後的分支 | 跑 `test_records_names.py`，其中 #266 留下的既有測試（含「名單剛好八個」`_NOT_RECORDS == 八個名字`、`_NOT_RECORDS` 為站台端子集） | 全部通過，且這些既有測試的內容與 `origin/v3` 相同 | 自動：同上 |
| TC-020 | 計畫「失敗先行測試」第 5 點；A 級前提「合法輸入行為不變」 | 功能 | 修改後的分支 | 跑 `platform/tests/test_launch_bundle.py`（含第 531 行：結尾帶換行的名字被拒） | 全部通過，結果與 `origin/v3` 相同 | 自動：`platform/tests/test_launch_bundle.py` |

## User Story 3 — 平台端與站台端兩道鎖拒收同一批檔（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 計畫「失敗先行測試」第 4 點；「裁決 1」（以一致性測試防漂移） | 功能 | 測試裡同時取得 `records._RESUME_FILE` 與 `fetch._RESUME_FILE` | 把這組名字各丟給兩個樣式：`head-1.sh`、`params-2.yaml`、`extra-10.config`、`head-123.sh`、`head.log`、`params.txt`、`trace-1.txt`、`.nextflow.log.2`、`head-1.sh.txt`、`params-x.yaml`、`extra-1.json` | 每個名字兩邊「配對／不配對」的結果逐一相同（前四個兩邊都配對，後七個兩邊都不配對） | 自動：`platform/tests/test_records_names.py` |
| TC-022 | 計畫「決定」與「不做」：不 import 站台端，兩道鎖各自寫；不把兩邊合成共用常數 | 不在範圍 | 修改後的 `platform/abf_platform/records.py` | 閱卷者讀該檔的 import 與常數 | `records.py` 沒有 import `abf_station`，`_RESUME_FILE` 是平台端自己寫的一份；`fetch.py` 沒有被改 | 手動：閱卷者讀 `git diff origin/v3...HEAD`（不是 `docs/TESTING.md` 的步驟，見總覽疑問 1） |

## User Story 4 — 改動範圍只有這一點，流程證據齊全（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 計畫「範圍：檔案」；「完成標準」第 3 點 | 不在範圍 | 修改後的分支 | 看 `git diff --stat origin/v3...HEAD`（扣掉 `specs/records-resume-files/` 下的計畫與 ledger） | 只有 `platform/abf_platform/records.py` 與 `platform/tests/test_records_names.py` 兩個檔；`fetch.py`、`launch.py`、`web/`、`cloud_store.py`、`rules.py`、`compose.py`、`actions/` 都沒動 | 手動：閱卷者讀 diff |
| TC-024 | 計畫「範圍：檔案」「不做」：只多一行常數＋一個條件 | 不在範圍 | 同上 | 讀 `records.py` 的 diff | 只多一行 `_RESUME_FILE = re.compile(r"^(head\|params\|extra)-[0-9]+\.(sh\|yaml\|config)\Z")`，以及 `name_ok` 最後 return 多一個 `and not _RESUME_FILE.match(name)`；`_NOT_RECORDS`、`_TRACE`、`_LOG`、`MAX_BYTES`、`store_files` 流程一字未動 | 手動：閱卷者讀 diff |
| TC-025 | 計畫「範圍：檔案」：只新增測試函式、不改既有斷言；專案規則（不得弱化既有測試） | 不在範圍 | 同上 | 讀 `test_records_names.py` 對 `origin/v3` 的 diff | 只有新增行；既有斷言沒有被刪除、放寬、跳過或改期望值；`test_launch_bundle.py` 沒被改 | 手動：閱卷者讀 diff |
| TC-026 | 計畫「不做」：不刪已存在 `records/` 底下的舊檔、不需要 migration | 不在範圍 | 同上 | 讀 diff，找有沒有刪檔、搬檔、資料結構或資料庫變動的程式 | 沒有；`store_files` 仍然「Nothing is deleted」；改動沒有任何資料遷移 | 手動：閱卷者讀 diff |
| TC-027 | 計畫「失敗先行測試」開頭：先寫、改程式前跑一次確認紅、紅的輸出貼進 ledger | 功能 | `specs/records-resume-files/ledger.md` | 閱卷者讀 ledger | ledger 貼有「改程式前」新測試的失敗輸出（TC-001 至 TC-009 這類在改前失敗），而不是只有綠的輸出 | 手動：閱卷者讀 ledger，並在 `origin/v3` 上跑新測試檔確認那些測試確實紅 |
| TC-028 | 計畫「失敗先行測試」第 5 點（兩分支比對）；專案 CLAUDE.md 的 Calibration failures | 功能 | 兩個分支：`origin/v3`、本分支 | 在兩邊各跑 `test_records_names.py` 與 `test_launch_bundle.py`，ledger 貼輸出，閱卷者再各跑一次 | 本分支比 `origin/v3` 只多了新增測試且全過；`test_launch_bundle.py` 與原有的 `test_records_names.py` 測試兩邊結果相同，沒有任何一個變紅 | 手動：ledger 的輸出加閱卷者重跑；單檔指令見計畫「環境事實」 |
| TC-029 | 計畫「完成標準」第 2 點 | 功能 | 修改後的分支，工作樹乾淨 | 看完成記號：`executor-status` 是否等於 `GREEN <HEAD sha>`（代表整個 `platform/tests` 套件在 HEAD 全綠；已知環境紅依 dev-plans README「通例」） | 記號與 HEAD 相符 | 自動：完成記號（全套件）；閱卷者不重跑全套 |

## 憲法與安全網

涉及的規則：Safety Net「平台絕不把收到的憑證存進它的資料庫或資料夾」（`.specify/memory/constitution.md` 第 208–213 行，檢查 `platform/tests/test_secrets.py`）。續跑檔可能含密鑰，不拒收就會被寫進 `records/`。本件只收緊，不放寬。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | Safety Net：平台不存收到的憑證；`test_secrets.py` 這條檢查仍涵蓋改過的程式 | 例外 | 修改後的分支 | 跑 `platform/tests/test_secrets.py`；並確認 TC-005 至 TC-009 證明續跑檔內容沒進入資料夾也沒出現在回傳 | `test_secrets.py` 全過，結果與 `origin/v3` 相同；續跑檔的內容既不在硬碟上、也不在回傳裡 | 自動：`platform/tests/test_secrets.py`＋`platform/tests/test_records_names.py` |

<!--
專長守則（backend）對照：對等性 TC、跨使用者 TC、確認管道 TC、migration 可套用 TC，本件沒有新增動作、沒有新增寫入動作、沒有資料結構變動，不適用（TC-026 載明不需要 migration）。「錯誤訊息與日誌不洩密」對應 TC-009、TC-010。
-->
