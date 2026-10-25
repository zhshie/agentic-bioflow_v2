# 測試案例：samplesheet 輸出資料夾不存在時自動建立

**規格**：`specs/samplesheet-output-dir/plan.md`（這個任務沒有 spec.md，計畫即規格；維護者無逐字裁示，等價要求見計畫「維護者原話」）　**總覽**：`test-case-overview.md`

名詞：「離開碼」＝程式結束時回報的數字（0 成功、1 沒找到樣本或驗證失敗、2 用法或寫檔問題、3 需要操作者決定）。「樣本表」＝`generate_samplesheet.py` 產生的 CSV。「上層資料夾」＝`-o` 路徑裡檔名之前的那一段。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

「計畫 T1」等＝計畫「失敗先行測試」表的編號。TC-001 至 TC-013 在 base（`origin/v3` @ 50f696b）上必須是紅的（現況是 traceback、離開碼 1），executor 先貼出紅的輸出再動手；TC-001 在 base 上若是綠的，回報 BLOCKED。

## User Story 1 — 文件範例照做就該成功：`-o` 指到還不存在的資料夾（優先度 P1）

等價要求：「文件範例照做就該成功」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 T1；目標；作法 1 | 功能 | 輸入資料夾有三組配對的 FASTQ（S1、S2、S3 各有 R1、R2）；`$TMP/new/sub/` 兩層都不存在 | 執行 `generate_samplesheet.py <輸入> --columns sample,fastq_1,fastq_2 --roles sample=sample,read1=fastq_1,read2=fastq_2 -o $TMP/new/sub/sheet.csv` | 離開碼是 0，且 `$TMP/new/sub/sheet.csv` 存在 | 自動：`tests/generate_samplesheet_test.sh` |
| TC-002 | 計畫 T1 | 功能 | 同 TC-001 | 同 TC-001 | 樣本表第 1 行是 `sample,fastq_1,fastq_2` | 自動：`tests/generate_samplesheet_test.sh` |
| TC-003 | 計畫 T1 | 功能 | 同 TC-001 | 同 TC-001 | 樣本表的資料列恰好 3 列（標題行之外） | 自動：`tests/generate_samplesheet_test.sh` |
| TC-004 | 計畫 T2；文件範例 `-o metadata/samplesheet.csv`（`generate_samplesheet.py` 檔頭用法、`skills/launch/SKILL.md`） | 功能 | 同 TC-001 的輸入；先 `cd` 到一個空的暫存資料夾，`metadata/` 不存在 | 用相對路徑 `-o metadata/samplesheet.csv`，其餘參數同 TC-001 | 離開碼是 0，且暫存資料夾下 `metadata/samplesheet.csv` 存在 | 自動：`tests/generate_samplesheet_test.sh` |

## User Story 2 — 失敗要說人話、不要 traceback（優先度 P1）

等價要求：「失敗要說人話、不要 traceback」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-005 | 計畫 T3；作法 2 | 例外 | `$TMP/afile` 是一個一般檔案（不是資料夾）；輸入同 TC-001 | `-o $TMP/afile/sheet.csv` | 離開碼是 2（不是 1，因為 1 專指「沒有樣本」） | 自動：`tests/generate_samplesheet_test.sh` |
| TC-006 | 計畫 T3 | 例外 | 同 TC-005 | 同 TC-005 | 錯誤輸出含 `ERROR: cannot write` | 自動：`tests/generate_samplesheet_test.sh` |
| TC-007 | 計畫 T3；目標「絕不丟 traceback」 | 例外 | 同 TC-005 | 同 TC-005 | 錯誤輸出不含 `Traceback` | 自動：`tests/generate_samplesheet_test.sh` |
| TC-008 | 計畫 T4；作法 2「stderr 恰一行」 | 例外 | 同 TC-005 | 同 TC-005 | 錯誤輸出恰好一行，且這一行以 `ERROR: cannot write` 開頭 | 自動：`tests/generate_samplesheet_test.sh` |
| TC-009 | 計畫 T4「帶出輸出路徑」；作法 2 | 例外 | 同 TC-005 | 同 TC-005 | 那一行含使用者給的 `-o` 路徑（原樣） | 自動：`tests/generate_samplesheet_test.sh` |
| TC-010 | 目標「寫不進去時 … exit 2」（由目標推得，不在計畫的 T 表內，見總覽疑問 3） | 例外 | `-o` 指到一個已存在的資料夾（例如 `$TMP` 本身）；輸入同 TC-001 | 執行 `-o $TMP` | 離開碼是 2 | 自動：`tests/generate_samplesheet_test.sh` |
| TC-011 | 同 TC-010 | 例外 | 同 TC-010 | 同 TC-010 | 錯誤輸出含 `ERROR: cannot write` | 自動：`tests/generate_samplesheet_test.sh` |
| TC-012 | 同 TC-010 | 例外 | 同 TC-010 | 同 TC-010 | 錯誤輸出不含 `Traceback` | 自動：`tests/generate_samplesheet_test.sh` |
| TC-013 | 計畫「失敗不留半成品」；目標「什麼都不留下」 | 例外 | 同 TC-005 | 同 TC-005 | `$TMP/afile/sheet.csv` 不存在，且 `afile` 仍是原本那個一般檔案、內容沒變 | 自動：`tests/generate_samplesheet_test.sh` |

## User Story 3 — 失敗不留半成品：驗證在前、建資料夾在後（優先度 P2）

等價要求：「失敗不留半成品」。順序必須維持：先驗證有沒有樣本，確定有才建資料夾、開檔。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 計畫 T5；「驗證在前、開檔在後」 | 例外 | 輸入同 TC-001；ampliseq schema、只要一組欄位（`--columns sampleID,forwardReads,reverseReads`，形狀同 `tests/generate_samplesheet_test.sh` 既有 TC-002）；`$TMP/never` 不存在 | `-o $TMP/never/x.csv` | 離開碼是 3 | 自動：`tests/generate_samplesheet_test.sh` |
| TC-015 | 計畫 T5 | 例外 | 同 TC-014 | 同 TC-014 | `$TMP/never` 資料夾不存在（沒有因為這次呼叫被建出來） | 自動：`tests/generate_samplesheet_test.sh` |
| TC-016 | 計畫 T6 | 例外 | 輸入資料夾 `$TMP/solo` 只有 `S1_R1_001.fastq.gz`（沒有 R2），不給 `--single-end`；`$TMP/never2` 不存在 | `-o $TMP/never2/x.csv`（欄位與 roles 同 TC-001） | 離開碼是 1 | 自動：`tests/generate_samplesheet_test.sh` |
| TC-017 | 計畫 T6 | 例外 | 同 TC-016 | 同 TC-016 | `$TMP/never2` 資料夾不存在 | 自動：`tests/generate_samplesheet_test.sh` |

## User Story 4 — 其餘行為一字不變（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 計畫 T7；作法 3；目標「CSV 位元組、警告文字、結束碼一字不變」 | 功能 | 上層資料夾已存在（既有所有案例的形狀） | 跑既有 feature 003 的 golden 比對（rnaseq 的 CSV 與 warnings＋summary 的 cksum） | 既有 golden 比對全部照舊通過，golden 檔沒有被改 | 自動：`tests/generate_samplesheet_test.sh`（既有斷言） |
| TC-019 | 計畫 T8 | 功能 | 輸入同 TC-001；不給 `-o` | 執行並讀標準輸出 | 離開碼 0，CSV 從 stdout 出來（首行 `sample,fastq_1,fastq_2`，3 列資料） | 自動：`tests/generate_samplesheet_test.sh` |
| TC-020 | 計畫 T8「不建任何資料夾」 | 功能 | 同 TC-019；先 `cd` 到一個全空的暫存資料夾 | 執行（不給 `-o`） | 執行完該暫存資料夾仍然是空的（沒有任何新資料夾或檔案） | 自動：`tests/generate_samplesheet_test.sh` |
| TC-021 | 計畫 T9；作法 5「不加 `--force`／不覆蓋保護」 | 不在範圍 | `-o` 指到已存在的檔案，裡面是舊內容 | 執行（輸入同 TC-001） | 離開碼 0，沒有詢問也沒有拒絕，檔案被新 CSV 覆蓋（舊內容不見） | 自動：`tests/generate_samplesheet_test.sh` |
| TC-022 | 計畫 T10 | 功能 | 同 TC-001（成功寫入新資料夾） | 同 TC-001 | stderr 的最後一行是 `wrote 3 samples (3 paired, 0 single) -> <使用者給的 -o 路徑>` | 自動：`tests/generate_samplesheet_test.sh` |
| TC-023 | 計畫「會改斷言的既有測試：無」 | 功能 | 工作已完成 | 以 `git diff <base>...HEAD -- tests/generate_samplesheet_test.sh` 逐行看 | 只有新增的行，放在檔尾 `echo`／結論行之前；既有斷言行零刪除、零修改 | 手動：驗收者比對 diff |
| TC-024 | 作法 4；範圍「檔頭 :33-35 的結束碼說明一句」 | 功能 | 工作已完成 | 讀 `scripts/generate_samplesheet.py` 檔頭 | 結束碼說明寫成 `2 bad usage (including no schema and no --roles, or an output path that cannot be written)`，其餘結束碼說明不變 | 手動：驗收者比對 diff |
| TC-025 | 計畫完成標準 | 功能 | 工作已完成 | 各別跑 `tests/generate_samplesheet_test.sh`、`tests/confirm_walkthrough_test.sh`、`tests/no_per_pipeline_config.sh`、`tests/path_shapes_test.sh` | 四個都通過（後三個不用改一個字） | 自動：上述四個檔案 |
| TC-026 | 計畫完成標準 | 功能 | 工作已完成，在 WSL | 跑 `bash tests/run_all.sh` | 整套綠 | 自動：`tests/run_all.sh` |

## 不在範圍（計畫明講不做）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-027 | 計畫「不做」：不加新旗標 | 不在範圍 | 工作已完成 | 比對 base 與 HEAD 的 `generate_samplesheet.py --help` 或 `add_argument` 清單 | 旗標清單完全相同，沒有新旗標 | 手動：驗收者比對 diff |
| TC-028 | 計畫「不做」：不改配對邏輯、角色推斷、警告文字；範圍「只改 :216 前後的寫檔段與檔頭」 | 不在範圍 | 工作已完成 | 看 `scripts/generate_samplesheet.py` 的 diff | 只有寫檔段與檔頭那一句有變；`build_rows`、角色推斷、各 `WARNING:`／`ERROR:` 既有文字零改動 | 手動：驗收者比對 diff |
| TC-029 | 計畫範圍「只准改 3 個檔」；「不做」：不改 `prepare_launch.sh` 草稿路徑 | 不在範圍 | 工作已完成 | `git diff --name-only <base>...HEAD` | 只含 `scripts/generate_samplesheet.py`、`tests/generate_samplesheet_test.sh`、`specs/samplesheet-output-dir/ledger.md`；`scripts/utils/*`、`scripts/prepare_launch.sh`、`tests/fixtures/samplesheet_golden/*`、`skills/`、`platform/**` 都不在內 | 手動：驗收者比對 diff；證據貼在 ledger |
| TC-030 | 計畫範圍「不准動 `hooks/`」；完成標準「`hooks/` 零改動」 | 不在範圍 | 工作已完成 | `git diff --name-only <base>...HEAD -- hooks/` | 沒有任何輸出 | 手動：驗收者比對 diff；證據貼在 ledger |
| TC-031 | 計畫「不需要 migration」 | 不在範圍 | 工作已完成 | 看 diff 有沒有資料表、JSON 欄位、fixtures 的變動 | 沒有（只動上列 3 個檔，且沒有資料結構變動） | 手動：驗收者比對 diff |
| TC-032 | 計畫完成標準「新增案例 ≤ 12 條」 | 不在範圍 | 工作已完成 | 數 `tests/generate_samplesheet_test.sh` 新增的案例區塊（以計畫 T 編號為單位） | 不超過 12 條 | 手動：驗收者比對 diff |

## 憲法與安全網

本任務碰到：不變條款 1（每支腳本檔頭要寫它不是哪個現成工具）與 Safety Net 對「寫樣本表」指令的 walkthrough 閘門（`hooks/confirm_walkthrough.sh` 把含 `generate_samplesheet` 的指令視為寫樣本表）。閘門本任務不改。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-033 | 不變條款 1（檢查：`tests/scripts_name_their_alternative.sh`） | 功能 | 工作已完成，檔頭說明被改過一句 | 跑 `tests/scripts_name_their_alternative.sh`，並看 `generate_samplesheet_test.sh` 既有 TC-018 的「前 40 行內有 `# Not …:` 或 `# Nothing existing:`」 | 兩者仍通過（檔頭那句 Not／Nothing existing 沒被擠掉或改掉） | 自動：`tests/scripts_name_their_alternative.sh`、`tests/generate_samplesheet_test.sh` |
| TC-034 | Safety Net（對寫樣本表指令的 walkthrough 閘門；不變條款 12 的檢查 `tests/confirm_walkthrough_test.sh`） | 功能 | 工作已完成 | 跑 `tests/confirm_walkthrough_test.sh`（不改一字），並確認 `hooks/` 無 diff（TC-030） | 通過；含 `generate_samplesheet` 的指令仍被視為寫樣本表、仍要先走 walkthrough；腳本內自動建資料夾沒有繞過它 | 自動：`tests/confirm_walkthrough_test.sh` |

<!--
後端專長守則對照：
- 對等性 TC（動作清單 vs 動作層函式）：本任務沒有網頁／API／聊天指令動作，不適用。
- 跨使用者 TC：沒有使用者帳號與紀錄，不適用。
- 確認管道 TC：寫入動作的確認由既有 walkthrough 閘門負責，本任務不改它 → TC-030、TC-034。
- 錯誤訊息與日誌 TC：TC-006/007/008/009/011/012（含原因 `<strerror>`、無堆疊）；訊息只含使用者自己給的路徑，不含密鑰。用詞是否夠白話歸「需要人看的事」。
- migration TC：計畫明寫「不需要 migration」→ TC-031。
-->
