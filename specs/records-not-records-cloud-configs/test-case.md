# 測試案例：平台端「不當紀錄收」名單補上三個雲端設定檔

**規格**：`specs/records-not-records-cloud-configs/plan.md`（A 級小任務，沒有獨立 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

白話說明：站台代理從雲端回傳一批檔案給平台，平台收下前會用 `records.name_ok` 檢查檔名，只有「Nextflow（執行分析流程的工具）自己寫的紀錄」才收。目前平台只擋五個非紀錄的名字，站台端擋八個；缺的三個是雲端部署時寫進同一個資料夾的設定檔（`gcb.config`、`aws.config`、Azure 設定檔，內含 bucket、專案、資源群組等部署資訊）。這次把三個補上，讓兩道鎖擋同一批檔；真正的紀錄檔從不叫這些名字，所以正常使用者看不到任何變化。

維護者原話（計畫引用）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」；程式檔頭承諾「Only the names Nextflow writes for these records are accepted.」本檔所有輸入與預期結果都取自計畫「失敗先行測試」一節的範例，沒有另外發明。

說明：Azure 那個檔名在測試與程式裡一律用兩段寫法 `"az" "ure.config"`（站台套件有掃描禁止裸的小寫單字），文中稱「Azure 設定檔」。測試檔為 `platform/tests/test_records_names.py`（新檔，不連網、不開資料庫）。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 平台不收那三個雲端設定檔（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「目標」；失敗先行測試 1 | 功能 | 平台程式載入 `records` | 用檔名 `gcb.config` 問 `records.name_ok` | 回傳 False（不是紀錄，不收）。改程式前這條是紅的（現在回傳 True） | 自動：`platform/tests/test_records_names.py` |
| TC-002 | 計畫「目標」；失敗先行測試 1 | 功能 | 同上 | 用檔名 `aws.config` 問 `records.name_ok` | 回傳 False | 自動：`platform/tests/test_records_names.py` |
| TC-003 | 計畫「目標」；失敗先行測試 1 | 功能 | 同上 | 用檔名 Azure 設定檔（`"az" "ure.config"`）問 `records.name_ok` | 回傳 False | 自動：`platform/tests/test_records_names.py` |
| TC-004 | 失敗先行測試 2 | 功能 | 一個空的暫存資料夾；站台送來一批檔案，只有一個檔，檔名依序為 `gcb.config`、`aws.config`、Azure 設定檔，內容都是 `b"SECRET_CONFIG"` | 對每個名字各呼叫一次 `records.store_files(暫存資料夾, "run-one", [該檔])` | 每次結果的 `files` 都是空清單（一個檔都沒收） | 自動：`platform/tests/test_records_names.py` |
| TC-005 | 失敗先行測試 2 | 功能 | 同 TC-004 | 同 TC-004 | 暫存資料夾的 `run-one` 底下找不到該檔（硬碟上沒有被寫出去）。改程式前這條是紅的（檔被寫入） | 自動：`platform/tests/test_records_names.py` |
| TC-006 | 失敗先行測試 2；「作法」最後一條（走既有拒絕訊息） | 例外 | 同 TC-004 | 同 TC-004 | 結果的 `refused` 清單有一項含該檔名，且用的是既有的「not a record of Nextflow」那句；沒有新增任何新的拒絕文字 | 自動：`platform/tests/test_records_names.py` |
| TC-007 | 專長守則（backend）：回應不含密鑰 | 例外 | 同 TC-004，檔案內容為 `SECRET_CONFIG` | 同 TC-004 | 回傳結果（`files` 與 `refused` 全部文字）裡找不到 `SECRET_CONFIG` | 自動：`platform/tests/test_records_names.py` |

## User Story 2 — 合法檔名完全不受影響，原本擋的照樣擋（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-008 | 失敗先行測試「對照組」；A 級前提（合法輸入行為不變） | 功能 | 平台程式載入 `records` | 用 `.nextflow.log`、`.nextflow.log.3` 問 `name_ok` | 兩個都回傳 True | 自動：`platform/tests/test_records_names.py` |
| TC-009 | 同上 | 功能 | 同上 | 用 `.nextflow/history` 問 `name_ok` | 回傳 True | 自動：`platform/tests/test_records_names.py` |
| TC-010 | 同上 | 功能 | 同上 | 用 `trace-1.txt`、`trace-2026-10-29_1.txt` 問 `name_ok` | 兩個都回傳 True | 自動：`platform/tests/test_records_names.py` |
| TC-011 | 同上 | 功能 | 同上 | 用 `params.txt`、`head.log` 問 `name_ok` | 兩個都回傳 True（只擋精確名稱，名字相近的不誤擋） | 自動：`platform/tests/test_records_names.py` |
| TC-012 | 同上 | 功能 | 同上 | 用 `aws.config.txt` 問 `name_ok` | 回傳 True（只擋 `aws.config` 本名，不擋有後綴的另一個名字） | 自動：`platform/tests/test_records_names.py` |
| TC-013 | 同上；「絕不放寬安全網」 | 例外 | 同上 | 用原本就擋的五個名字 `tower.token`、`params.yaml`、`head.sh`、`nextflow.config`、`samplesheet.csv` 問 `name_ok` | 五個都仍回傳 False | 自動：`platform/tests/test_records_names.py` |
| TC-014 | 失敗先行測試「兩分支比對」 | 功能 | 同上 | 用 `trace.txt`、`trace-3.txt`、`.nextflow.log.12` 問 `name_ok` | 三個都回傳 True（閱卷時會在 `origin/v3` 與本分支各跑一次，結果必須相同，見 TC-020） | 自動：`platform/tests/test_records_names.py` |
| TC-015 | 失敗先行測試「對照組」 | 功能 | 既有測試 `test_launch_bundle.py::test_security_f4_the_other_validators_too` 沒有被修改 | 執行該測試 | 維持綠燈；檔案中該測試的斷言與 base 相同（沒有被削弱） | 自動：`platform/tests/test_launch_bundle.py` |

## User Story 3 — 兩道鎖擋的名單一致，不再漂移（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 失敗先行測試「兩邊一致性」；裁決 2 | 功能 | 同時載入平台端 `records` 與站台端 `fetch` | 比對 `records._NOT_RECORDS` 與 `fetch._NOT_RECORDS` | 平台端每一個名字都在站台端名單裡（站台端可以更多）。這是為了防止兩份名單日後再各改各的 | 自動：`platform/tests/test_records_names.py` |

## 不在範圍（計畫「不做」與裁決）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 「不做」：不動既有成員；裁決 1（續跑檔 `head-N.sh` 等本件不擋，另開一件） | 不在範圍 | 平台程式載入 `records` | 讀 `records._NOT_RECORDS` | 內容剛好是八個名字：原有五個加 `gcb.config`、`aws.config`、Azure 設定檔；沒有多出任何其他名字或樣式（續跑檔沒有被順手擋掉） | 自動：`platform/tests/test_records_names.py` |
| TC-018 | 「範圍：檔案」；「不做」：不動 `_TRACE`、`_LOG`、`MAX_BYTES`、`store_files` 流程 | 不在範圍 | 本分支相對 `origin/v3` 的變更 | 看 `git diff --stat` 與 `records.py` 的差異 | 只有 `platform/abf_platform/records.py` 與新檔 `platform/tests/test_records_names.py` 兩個檔有變動；`records.py` 只有 `_NOT_RECORDS` 那一行不同；`fetch.py`、`launch.py`、`*_launch.py`、`web*.py`、`cloud_store.py` 沒動；新測試檔前 40 行內有 `# Nothing existing:` 註解且超過 15 個字 | 手動：閱卷者檢查 diff 與 ledger（計畫要求 ledger 記錄；`docs/TESTING.md` 無對應條目，見總覽疑問 1） |
| TC-019 | 「不做」：不新增使用者可見文字、不改文件、不需要 migration、舊檔不刪不改 | 不在範圍 | 同 TC-018 | 看 diff | 沒有 migration 檔、沒有文件變動、沒有新增的使用者可見文字；任何既有測試都沒有被刪除、跳過或放寬斷言 | 手動：閱卷者檢查 diff 與 ledger |

## 憲法與安全網

這次動的是「第二道鎖」的名單，碰到原則 2（Nextflow 自己的紀錄才是真相，不是紀錄的檔不能被當紀錄讀進來），以及維護者派工指示的「絕不放寬安全網」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 原則 2；派工指示「絕不放寬安全網」；CLAUDE.md 校準失敗 #1（動閘門要兩分支比對） | 功能 | `origin/v3` 與本分支各自可跑 | 在兩個分支各跑 `test_launch_bundle.py` 與新測試檔，並用 `trace.txt`、`trace-3.txt`、`.nextflow.log.12` 以及原有五個被擋名字逐一問 `name_ok` | 兩分支對這些名字的結果完全相同；唯一的差別只有 `gcb.config`、`aws.config`、Azure 設定檔從 True 變 False；沒有任何原本被擋的名字變成放行，也沒有任何原本放行的合法名字變成被擋 | 手動：閱卷者在兩分支各跑一次並比對輸出（單檔指令 `ABF_PYTEST_TARGETS=tests/test_records_names.py bash tests/platform_test.sh`，相對於 `platform/`） |

<!--
Rules for the writer:
- Every acceptance scenario and every FR in spec.md maps to at least one TC. Every
  "out of scope" item in spec.md maps to at least one 不在範圍 TC.
- A TC tests one thing. Two expectations = two rows.
- 驗證方式 is 自動 or 手動. Nothing else.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
