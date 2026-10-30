# 測試案例：雲端計算環境可設單一 task 的記憶體上限（maxMemoryGB），平台寫的 resourceLimits 不再吃掉使用者自己設的鍵

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
這一件沒有 spec.md，計畫（plan.md）就是規格；維護者沒有逐字原話，來源是 2026-10-29 AWS Batch 真實試跑的失敗，
計畫把那次的設定檔當作真實案例。下面的「試跑原案」「試跑真實失敗」兩類 TC 用的就是那次的實際內容。
-->

**規格**：`specs/cloud-ce-memory-cap/plan.md`（本件無 spec.md）　**總覽**：`test-case-overview.md`

名詞先講白：
- **resourceLimits**：Nextflow 的「單一 task 資源天花板」設定，寫法像 `process.resourceLimits = [cpus: 4, memory: 6.GB]`。管線要求超過天花板時，Nextflow 會把要求壓到天花板，task 才排得上機器。
- **平台寫的設定檔**：送出時平台自己產生的 `aws.config`／`gcb.config`／`azure.config`，在使用者的 `nextflow.config` 之後讀，所以後者被它蓋過。
- **使用者的 nextflowConfig**：使用者在計算環境裡自己寫的 Nextflow 設定文字，原文會整份進 `nextflow.config`。
- **合併**：平台要寫的上限與使用者自己寫的上限逐鍵比較，同一個鍵取較小的，只有使用者設的鍵保留。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、寫法讀不懂、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白拒絕而不是悄悄亂做。

三種雲端 = AWS Batch、Google Batch（gcb）、Azure Batch。標「三種」的列，三種雲端各要有一個測試，缺一種就算沒做到。

## User Story 1 — 計算環境可以設「單一 task 的記憶體上限」maxMemoryGB（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 決定一；失敗先行測試（環境驗證） | 功能 | 一個合法的 AWS Batch 環境設定 | 建立環境時加上 `maxMemoryGB` = 10000 | 建立成功；讀回的環境設定裡 `maxMemoryGB` 等於 10000 | 自動：`platform/tests/test_aws_ce.py`（`test_max_memory_gb_rules`） |
| TC-002 | 決定一；失敗先行測試（環境驗證） | 功能 | 一個合法的 Google Batch 環境設定 | 建立環境時加上 `maxMemoryGB` = 10000 | 建立成功；讀回的 `maxMemoryGB` 等於 10000 | 自動：`platform/tests/test_gcb_ce.py` |
| TC-003 | 決定一；失敗先行測試（環境驗證） | 功能 | 一個合法的 Azure Batch 環境設定 | 建立環境時加上 `maxMemoryGB` = 10000 | 建立成功；讀回的 `maxMemoryGB` 等於 10000 | 自動：`platform/tests/test_azure_ce.py` |
| TC-004 | 決定一（整數 1 到 10000） | 功能 | 三種雲端各一個合法環境設定 | 各自建立環境，`maxMemoryGB` = 1（下限） | 三種都建立成功，讀回 `maxMemoryGB` 等於 1 | 自動：三個 `test_*_ce.py` |
| TC-005 | 決定二；作法「不需要 migration 的理由」 | 功能 | 三種雲端各一個**沒有** `maxMemoryGB` 的環境設定（等同舊環境） | 建立環境並讀回 | 建立成功；讀回的設定裡沒有 `maxMemoryGB` 這個鍵（等於沒設，沒有被補上預設值） | 自動：三個 `test_*_ce.py` |
| TC-006 | 決定一；失敗先行測試（環境驗證） | 例外 | AWS Batch 環境設定 | 分別把 `maxMemoryGB` 設成 0、10001、true、文字 "8"、小數 1.5 並建立 | 五個值都被拒絕，訊息都含 `maxMemoryGB must be a whole number from 1 to 10000`（不是 "unknown setting"） | 自動：`platform/tests/test_aws_ce.py` |
| TC-007 | 決定一；失敗先行測試（環境驗證） | 例外 | Google Batch 環境設定 | 同 TC-006 的五個值 | 五個值都被拒絕，訊息都含 `maxMemoryGB must be a whole number from 1 to 10000` | 自動：`platform/tests/test_gcb_ce.py` |
| TC-008 | 決定一；失敗先行測試（環境驗證） | 例外 | Azure Batch 環境設定 | 同 TC-006 的五個值 | 五個值都被拒絕，訊息都含 `maxMemoryGB must be a whole number from 1 to 10000` | 自動：`platform/tests/test_azure_ce.py` |

## User Story 2 — 設了記憶體上限，送出時平台寫的那一行就帶著它（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-009 | 失敗先行測試（送出內容 1，試跑原案） | 功能 | AWS 環境 `maxvCpus`=4、`maxMemoryGB`=6；使用者的 nextflowConfig 沒有 resourceLimits | 產生送出內容 | `aws.config` 的 `process.resourceLimits` 等於 `[cpus: 4, memory: 6.GB]` | 自動：`platform/tests/test_aws_launch.py` |
| TC-010 | 同上（Google Batch） | 功能 | Google 環境 `maxvCpus`=4、`maxMemoryGB`=6；使用者沒寫 resourceLimits | 產生送出內容 | `gcb.config` 的 `process.resourceLimits` 等於 `[cpus: 4, memory: 6.GB]` | 自動：`platform/tests/test_gcb_launch.py` |
| TC-011 | 同上（Azure） | 功能 | Azure 環境 `maxvCpus`=4、`maxMemoryGB`=6；使用者沒寫 resourceLimits | 產生送出內容 | `azure.config` 的 `process.resourceLimits` 等於 `[cpus: 4, memory: 6.GB]` | 自動：`platform/tests/test_azure_launch.py` |
| TC-012 | 失敗先行測試（送出內容 3） | 功能 | AWS 環境只設 `maxMemoryGB`=6，不設 `maxvCpus`；使用者沒寫 resourceLimits | 產生送出內容 | `process.resourceLimits` 等於 `[memory: 6.GB]`（只含有設的鍵） | 自動：`platform/tests/test_aws_launch.py` |
| TC-013 | 同上（Google Batch） | 功能 | Google 環境只設 `maxMemoryGB`=6 | 產生送出內容 | `process.resourceLimits` 等於 `[memory: 6.GB]` | 自動：`platform/tests/test_gcb_launch.py` |
| TC-014 | 同上（Azure） | 功能 | Azure 環境只設 `maxMemoryGB`=6 | 產生送出內容 | `process.resourceLimits` 等於 `[memory: 6.GB]` | 自動：`platform/tests/test_azure_launch.py` |
| TC-015 | 決定二 | 功能 | 三種雲端各一個設了 `maxMemoryGB`=6 的環境 | 產生送出內容 | 送出內容的 `ce` 裡有 `maxMemoryGB` 且等於 6 | 自動：三個 `test_*_launch.py` |
| TC-016 | 決定二；對照組（鍵集合不變） | 功能 | 三種雲端各一個**沒設** `maxMemoryGB` 的環境 | 產生送出內容 | 送出內容的 `ce` 裡**沒有** `maxMemoryGB` 這個鍵；AWS 的鍵集合仍是 name、platform、region、workDir、jobQueue、spot、maxvCpus、environment、nextflowConfig（既有斷言不動） | 自動：三個 `test_*_launch.py` |
| TC-017 | 決定二（`snapshot_ce`） | 功能 | 三種雲端各兩個環境：一個有設 `maxMemoryGB`，一個沒設 | 用 `launch.snapshot_ce` 轉成送出用的資料 | 有設的：結果含 `maxMemoryGB` 且值相同；沒設的：結果**沒有**這個鍵 | 自動：三個 `test_*_launch.py` |
| TC-018 | 決定二（`_check_*_ce` 驗證） | 例外 | 三種雲端各一個環境，送出用資料的 `maxMemoryGB` 為 0、10001、true、"8"、1.5 | 產生送出內容 | 都被拒絕（送出前的錯誤），訊息指名 `maxMemoryGB`；沒有建立任何 run 資料夾 | 自動：三個 `test_*_launch.py` |
| TC-019 | 對照組（只設 maxvCpus） | 功能 | 三種雲端各一個環境 `maxvCpus`=16、沒設 `maxMemoryGB`、使用者沒寫 resourceLimits | 產生送出內容 | 平台設定檔的 `process.resourceLimits` 仍等於 `[cpus: 16]`（既有斷言不動） | 自動：三個 `test_*_launch.py` |
| TC-020 | 決定三 1（兩個都沒設） | 功能 | AWS 環境 `maxvCpus` 與 `maxMemoryGB` 都沒設；使用者沒寫 resourceLimits | 產生送出內容 | `aws.config` 只有 executor、queue、region、workDir 四個設定，沒有 `process.resourceLimits`（既有斷言不動） | 自動：`platform/tests/test_aws_launch.py` |

## User Story 3 — 使用者自己寫了 resourceLimits，平台逐鍵合併、不丟他的鍵（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 失敗先行測試（送出內容 2，試跑真實失敗）；決定三 3 | 功能 | AWS 環境 `maxvCpus`=4，沒設 `maxMemoryGB`；使用者的 nextflowConfig 是 `process.resourceLimits = [cpus: 4, memory: 6.GB]` | 產生送出內容 | `aws.config` 的 `process.resourceLimits` 等於 `[cpus: 4, memory: 6.GB]`（使用者的記憶體上限保留，不再變成 `[cpus: 4]`） | 自動：`platform/tests/test_aws_launch.py` |
| TC-022 | 同上（Google Batch） | 功能 | Google 環境 `maxvCpus`=4，沒設 `maxMemoryGB`；使用者寫 `process.resourceLimits = [cpus: 4, memory: 6.GB]` | 產生送出內容 | `gcb.config` 的那一行等於 `[cpus: 4, memory: 6.GB]` | 自動：`platform/tests/test_gcb_launch.py` |
| TC-023 | 同上（Azure） | 功能 | Azure 環境 `maxvCpus`=4，沒設 `maxMemoryGB`；使用者寫 `process.resourceLimits = [cpus: 4, memory: 6.GB]` | 產生送出內容 | `azure.config` 的那一行等於 `[cpus: 4, memory: 6.GB]` | 自動：`platform/tests/test_azure_launch.py` |
| TC-024 | 失敗先行測試（送出內容 4）；決定三 3 | 功能 | AWS 環境 `maxvCpus`=4；使用者寫 `[cpus: 64]` | 產生送出內容 | 那一行是 `[cpus: 4]`（平台是天花板，使用者不能放寬） | 自動：`platform/tests/test_aws_launch.py` |
| TC-025 | 失敗先行測試（送出內容 4） | 功能 | AWS 環境 `maxvCpus`=4；使用者寫 `[cpus: 2]` | 產生送出內容 | 那一行是 `[cpus: 2]`（使用者要更低可以） | 自動：`platform/tests/test_aws_launch.py` |
| TC-026 | 失敗先行測試（送出內容 4） | 功能 | AWS 環境只設 `maxMemoryGB`=6；使用者寫 `[memory: 32.GB]` | 產生送出內容 | 那一行是 `[memory: 6.GB]` | 自動：`platform/tests/test_aws_launch.py` |
| TC-027 | 失敗先行測試（送出內容 4） | 功能 | AWS 環境只設 `maxMemoryGB`=6；使用者寫 `[memory: 4.GB]` | 產生送出內容 | 那一行是 `[memory: 4.GB]`（保留使用者較小的值） | 自動：`platform/tests/test_aws_launch.py` |
| TC-028 | 失敗先行測試（送出內容 4）；決定三 3 | 功能 | AWS 環境只設 `maxvCpus`=4；使用者寫 `[time: 48.h]` | 產生送出內容 | 那一行是 `[cpus: 4, time: 48.h]`（保留他的 time 原文，鍵序 cpus 在前 time 在後） | 自動：`platform/tests/test_aws_launch.py` |
| TC-029 | 決定三 3 | 功能 | AWS 環境只設 `maxvCpus`=4；使用者寫 `[disk: 200.GB]` | 產生送出內容 | 那一行是 `[cpus: 4, disk: 200.GB]`（disk 原文保留） | 自動：`platform/tests/test_aws_launch.py` |
| TC-030 | 決定三 3（固定鍵序） | 功能 | AWS 環境 `maxvCpus`=4、`maxMemoryGB`=6；使用者寫的鍵順序故意顛倒：`[time: 48.h, disk: 200.GB, memory: 32.GB, cpus: 64]` | 產生送出內容 | 那一行是 `[cpus: 4, memory: 6.GB, disk: 200.GB, time: 48.h]`（鍵序固定 cpus、memory、disk、time） | 自動：`platform/tests/test_aws_launch.py` |
| TC-031 | 失敗先行測試（送出內容 4：`'6 GB'` 也能比大小） | 功能 | AWS 環境只設 `maxMemoryGB`=6；使用者寫 `[memory: '32 GB']` | 產生送出內容 | 那一行是 `[memory: 6.GB]`（引號加空格的寫法也能與平台值比大小） | 自動：`platform/tests/test_aws_launch.py` |
| TC-032 | 失敗先行測試（送出內容 4：MB 也能比大小） | 功能 | AWS 環境只設 `maxMemoryGB`=6；使用者寫 `[memory: 32768.MB]` | 產生送出內容 | 那一行是 `[memory: 6.GB]`（MB 寫法也能與平台值比大小） | 自動：`platform/tests/test_aws_launch.py` |
| TC-033 | 決定三 3（使用者較小的寫法） | 功能 | AWS 環境 `maxvCpus`=4、`maxMemoryGB`=6；使用者分別寫 `[memory: '2 GB']` 與 `[memory: 512.MB]` | 各產生一次送出內容 | 兩次的記憶體都仍是使用者的值（不是 `6.GB`），cpus 是 4；寫法可以原樣保留或換成等值寫法，計畫沒規定寫法 | 自動：`platform/tests/test_aws_launch.py` |
| TC-034 | 決定三 3（只有使用者設的鍵保留） | 功能 | AWS 環境只設 `maxMemoryGB`=6；使用者寫 `[cpus: 8]` | 產生送出內容 | 那一行是 `[cpus: 8, memory: 6.GB]`（使用者的 cpus 不被丟掉） | 自動：`platform/tests/test_aws_launch.py` |
| TC-035 | 決定三 4（兩種行的寫法） | 功能 | AWS 環境 `maxvCpus`=4、`maxMemoryGB`=6；使用者寫的是不帶 `process.` 的 `resourceLimits = [cpus: 64, memory: 32.GB]` | 產生送出內容 | `aws.config` 的 `process.resourceLimits` 等於 `[cpus: 4, memory: 6.GB]`，且是單獨一行 | 自動：`platform/tests/test_aws_launch.py` |
| TC-036 | 決定三 4（被 `//` 註解掉的行不算） | 功能 | AWS 環境 `maxvCpus`=4；使用者的 nextflowConfig 只有一行 `// process.resourceLimits = [cpus: 2]`（被註解掉） | 產生送出內容 | 不報錯；`aws.config` 的那一行是 `[cpus: 4]`（當作使用者沒寫） | 自動：`platform/tests/test_aws_launch.py` |
| TC-037 | 完成標準（合併函式只有一份）；範圍（launch.py 新增一個共用小函式） | 功能 | 本分支的程式碼 | 閱卷人看 diff | 組出 resourceLimits 那一行的邏輯只有一份，`_gcb_config`、`_aws_config`、`_azure_config` 都呼叫它，沒有三份複製 | 手動：閱卷看 diff（計畫明寫不進 `docs/TESTING.md`） |
| TC-038 | 決定三 6；對照組（原文逐字不變） | 功能 | 兩個 AWS 環境：一個使用者有寫 resourceLimits（走合併），一個沒寫 | 各產生送出內容 | 兩者的 `nextflow.config` 都以使用者的 nextflowConfig 原文逐字開頭，沒有被改動 | 自動：`platform/tests/test_aws_launch.py` |
| TC-039 | 對照組（沒設任何上限、使用者有 resourceLimits） | 功能 | 三種雲端各一個環境：`maxvCpus`、`maxMemoryGB` 都沒設；使用者寫 `process.resourceLimits = [cpus: 2, memory: 4.GB]` | 產生送出內容 | 平台設定檔裡**沒有** resourceLimits；`nextflow.config` 含使用者那一行原文（維持現狀） | 自動：三個 `test_*_launch.py` |
| TC-040 | 決定三 1 與 5 的交界 | 功能 | AWS 環境 `maxvCpus`、`maxMemoryGB` 都沒設；使用者的 resourceLimits 寫成讀不懂的跨行寫法 | 產生送出內容 | **不報錯**，照常產生；平台設定檔沒有 resourceLimits，使用者原文完全不碰 | 自動：`platform/tests/test_aws_launch.py` |

## User Story 4 — 讀不懂使用者寫的 resourceLimits，就在送出前拒絕並說清楚怎麼改（優先度 P1）

下列各列的共同前置：環境 `maxvCpus`=4（平台有值要寫）；使用者的 nextflowConfig 另含一行獨特的記號文字（例如 `// MY-MARKER-LINE`），用來確認訊息沒有貼出他的設定檔內容。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | 失敗先行測試（送出內容 5a）；決定三 5 | 例外 | AWS 環境；使用者寫跨行：`resourceLimits = [` 換行 `cpus: 4` 換行 `]` | 產生送出內容 | 被拒絕（送出前的錯誤）；訊息含 `resourceLimits` 與怎麼改 | 自動：`platform/tests/test_aws_launch.py` |
| TC-042 | 失敗先行測試（送出內容 5b） | 例外 | AWS 環境；使用者的 resourceLimits 行出現兩次（兩行都沒被註解掉） | 產生送出內容 | 被拒絕；訊息含 `resourceLimits` 與怎麼改 | 自動：`platform/tests/test_aws_launch.py` |
| TC-043 | 失敗先行測試（送出內容 5c） | 例外 | AWS 環境；使用者寫區塊寫法 `process { resourceLimits { cpus = 4 } }` | 產生送出內容 | 被拒絕；訊息含 `resourceLimits` 與怎麼改 | 自動：`platform/tests/test_aws_launch.py` |
| TC-044 | 失敗先行測試（送出內容 5d） | 例外 | AWS 環境；使用者寫 `resourceLimits = [cpus: params.c]`（用變數） | 產生送出內容 | 被拒絕；訊息含 `resourceLimits` 與怎麼改 | 自動：`platform/tests/test_aws_launch.py` |
| TC-045 | 失敗先行測試（送出內容 5e） | 例外 | AWS 環境；使用者寫 `resourceLimits = [cpus: 4, gpus: 1]`（未知鍵 gpus） | 產生送出內容 | 被拒絕；訊息含 `resourceLimits` 與怎麼改 | 自動：`platform/tests/test_aws_launch.py` |
| TC-046 | 失敗先行測試（送出內容 5，Google Batch 寫 1、2、3、5） | 例外 | Google 環境；使用者分別寫上面 TC-041 到 TC-045 的五種寫法 | 各產生一次送出內容 | 五種都被拒絕；訊息含 `resourceLimits` 與怎麼改 | 自動：`platform/tests/test_gcb_launch.py` |
| TC-047 | 失敗先行測試（送出內容 5，Azure） | 例外 | Azure 環境；使用者分別寫上面 TC-041 到 TC-045 的五種寫法 | 各產生一次送出內容 | 五種都被拒絕；訊息含 `resourceLimits` 與怎麼改 | 自動：`platform/tests/test_azure_launch.py` |
| TC-048 | 決定三 5（訊息要含環境、發生什麼事、怎麼辦） | 例外 | AWS 環境名稱 `aws1`；使用者寫跨行 resourceLimits | 產生送出內容 | 訊息指名環境 `aws1`，說明平台讀不懂它的 resourceLimits 寫法、不能安全合併，並給兩個修法：改成單行寫法，或刪掉它、改設環境的 `maxvCpus`／`maxMemoryGB`；中英對照 | 自動：`platform/tests/test_aws_launch.py` |
| TC-049 | 決定三 5（不得貼出設定檔全文） | 例外 | 同 TC-041 到 TC-045 各情況，設定檔另含記號行 | 產生送出內容 | 訊息**不含**記號行，也不含使用者那一行 resourceLimits 的整行原文（最多帶鍵名，例如 gpus） | 自動：`platform/tests/test_aws_launch.py` |
| TC-050 | 決定三 5（不寫任何檔）；失敗先行測試（送出內容 5） | 例外 | 同 TC-041 到 TC-045 各情況 | 產生送出內容 | 拒絕之後沒有啟動任何東西（`box.started` 為空）、沒有 run 資料夾 | 自動：`platform/tests/test_aws_launch.py` |
| TC-051 | 決定三 4（值要合規則） | 例外 | AWS 環境；使用者分別寫 `cpus: 4.5`、`cpus: '4'`、`memory: 6`（沒單位）、`memory: 6.TB`（不收的單位） | 各產生一次送出內容 | 四種都被拒絕（讀不懂） | 自動：`platform/tests/test_aws_launch.py` |
| TC-052 | 決定三 4（disk、time 的字元與長度）；作法「不變」 | 例外 | AWS 環境；使用者分別寫 `disk: 'a;b'`、`time: '$(x)'`、一個超過 40 字的 `time` 值 | 各產生一次送出內容 | 三種都被拒絕；使用者的 disk、time 只有過了字元與長度限制才可能進平台寫的檔 | 自動：`platform/tests/test_aws_launch.py` |
| TC-053 | 決定三 4（不含巢狀方括號） | 例外 | AWS 環境；使用者寫 `resourceLimits = [cpus: 4, time: [1]]` | 產生送出內容 | 被拒絕 | 自動：`platform/tests/test_aws_launch.py` |
| TC-054 | 決定三 5（只要平台有值要寫就拒絕） | 例外 | AWS 環境**只設** `maxMemoryGB`=6（不設 maxvCpus）；使用者寫跨行 resourceLimits | 產生送出內容 | 被拒絕，訊息含 `resourceLimits` 與怎麼改 | 自動：`platform/tests/test_aws_launch.py` |
| TC-055 | 決定三 4（整行才算）；作法「不變」（使用者文字不得未經檢查進平台檔） | 例外 | AWS 環境 `maxvCpus`=4；使用者寫 `resourceLimits = [cpus: 4] ; process.executor = 'local'`（方括號後面還有東西） | 產生送出內容 | 被拒絕；任何情況下平台寫的 `aws.config` 都不含 `process.executor = 'local'` | 自動：`platform/tests/test_aws_launch.py` |

## User Story 5 — 送出確認畫面與文件跟得上（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-056 | 決定四；失敗先行測試（送出內容 6） | 功能 | 三種雲端各一個設了 `maxMemoryGB`=6 的環境 | 產生送出確認畫面 | 畫面文字含 `單一 task 的記憶體上限` 與值 6；原有的「單一 task 的 cpus 上限」列仍在 | 自動：三個 `test_*_launch.py` |
| TC-057 | 決定四；對照組（沒設就不出現） | 功能 | 三種雲端各一個**沒設** `maxMemoryGB` 的環境 | 產生送出確認畫面 | 畫面文字不含 `記憶體上限` 字樣 | 自動：三個 `test_*_launch.py` |
| TC-058 | 決定四（合併後的那一行本來就會顯示） | 功能 | AWS 環境 `maxvCpus`=4，使用者寫 `process.resourceLimits = [cpus: 4, memory: 6.GB]` | 產生送出確認畫面 | 畫面上 `aws.config` 區塊顯示的是合併後的實際那一行 `process.resourceLimits = [cpus: 4, memory: 6.GB]` | 自動：`platform/tests/test_aws_launch.py` |
| TC-059 | 範圍（`docs/PLATFORM.md` 六處） | 功能 | 本分支的 `docs/PLATFORM.md` | 閱卷人對照 diff，看原本提到 `maxvCpus` 與 `process.resourceLimits` 的六處表格列 | 這六處都加了 `maxMemoryGB`，並寫明合併規則（同鍵取較小、使用者設的鍵保留、讀不懂就拒絕）；文件裡沒有與程式不符的說法 | 手動：閱卷看 diff |

## User Story 6 — 範圍與計畫明講不做的事（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 決定一（Slurm 不加）；不做第 3 條 | 不在範圍 | Slurm 環境設定 | 建立環境時加上 `maxMemoryGB` | 被拒絕，訊息是 `unknown setting for a Slurm environment`（跟現在 `maxvCpus` 在 Slurm 的下場一樣）；Slurm 沒有新鍵 | 自動：既有 Slurm 環境測試檔（新增一條） |
| TC-061 | 不做第 1、2 條（不做總量、不加 maxDiskGB／maxTime） | 不在範圍 | 三種雲端各一個合法環境設定 | 各自加上 `maxDiskGB`、`maxTime`、`maxTotalMemoryGB` 建立 | 三個鍵在三種雲端都仍被拒絕為 "unknown setting"；`maxMemoryGB` 以外沒有新鍵被收 | 自動：三個 `test_*_ce.py` |
| TC-062 | 不做第 3 條（不改 `snapshot()`）；決定二 | 不在範圍 | 一個設了 `maxMemoryGB`=6 的 AWS 環境 | 建立後看送給代理做預檢的資料欄位 | 欄位集合仍是 name、platform、credentialsId、region、workDir、jobQueue、spot、maxvCpus（既有斷言不動）；沒有多出 `maxMemoryGB` | 自動：`platform/tests/test_aws_ce.py` |
| TC-063 | 範圍（只准改的檔、不准碰的檔）；不做第 3、6 條 | 不在範圍 | 本分支相對 base 的 diff | 閱卷人看 `git diff --stat` | 只含計畫「範圍」列的檔（compute_envs.py、launch.py、build.py、`docs/PLATFORM.md`、六個測試檔，加上本件 ledger）；沒有動 `web/`、`.github/`、`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`、`docs/TESTING.md`、Slurm 路徑、`snapshot()` | 手動：閱卷看 diff |
| TC-064 | 範圍（只新增測試、不改既有斷言） | 不在範圍 | 六個測試檔的 diff | 閱卷人逐檔比對 base | 只有新增的測試函式與輔助；既有斷言沒有被刪、放寬、跳過或改預期值 | 手動：閱卷看 diff |
| TC-065 | 不做第 4 條（不解析整份 Groovy） | 不在範圍 | AWS 環境 `maxvCpus`=4；使用者的 nextflowConfig 有別的設定行（`process.cpus = 2`、`process.memory = { 4.GB * task.attempt }`）但沒有 resourceLimits | 產生送出內容 | 不報錯；那一行是 `[cpus: 4]`；那些別的行原文原樣留在 `nextflow.config`，平台沒有讀它們、也沒有改它們 | 自動：`platform/tests/test_aws_launch.py` |
| TC-066 | 不做第 5 條（不刪既有環境的任何鍵） | 不在範圍 | 一個舊式 AWS 環境：有 spot、environment 變數清單、nextflowConfig，沒有 `maxMemoryGB` | 產生送出內容 | 送出內容的 `ce` 保留這些原有的鍵與值，只是沒有 `maxMemoryGB`；環境沒有任何鍵被刪或被改 | 自動：`platform/tests/test_aws_launch.py` |

## 憲法與安全網

涉及的條目：憲法第 2 條（送出一定先讓人看到完整內容並確認）、原則 VI「Nothing Goes Quiet」（不可悄悄丟掉使用者設的鍵，也不可悄悄換掉）、專長守則（錯誤訊息、migration、動作層）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-067 | 憲法第 2 條 | 功能 | 本分支 | 跑確認管道既有測試（`test_tch09_*`、`test_tch09_b_c_*`） | 未經確認的送出仍被拒絕，測試與 base 同樣通過；本件沒有新增繞過確認的寫入路徑；確認畫面顯示的就是會被寫的內容（見 TC-056、TC-058） | 自動：`platform/tests/test_human_channel.py`、`test_confirm_page.py` |
| TC-068 | 原則 VI；目標（絕不默默丟掉使用者設的鍵） | 功能 | AWS 環境 `maxvCpus`=4、`maxMemoryGB`=6；使用者分別寫只含 cpus、只含 memory、只含 disk、只含 time、四個鍵都有的 resourceLimits（都是讀得懂的寫法） | 各產生一次送出內容 | 每一種結果裡，使用者寫過的每一個鍵都還在；平台有設的鍵取較小值；沒有任何一次是使用者的鍵憑空消失 | 自動：`platform/tests/test_aws_launch.py` |
| TC-069 | 專長守則（錯誤訊息：原因＋處理方式、不露堆疊／內部路徑／密鑰） | 例外 | 任一 TC-041 到 TC-045 的拒絕；以及 TC-006 到 TC-008 的拒絕 | 看訊息全文 | 訊息說明發生什麼事與該怎麼辦；不含 Traceback、測試用的本機目錄路徑、憑證檔內容或金鑰 | 自動：`test_aws_launch.py`、`test_aws_ce.py` |
| TC-070 | 兩分支比對（專案 CLAUDE.md「Calibration failures」；完成標準） | 功能 | base（`origin/v3`）與本分支 | 兩邊各跑 `test_aws_launch.py`、`test_gcb_launch.py`、`test_azure_launch.py`、`test_aws_ce.py`、`test_gcb_ce.py`、`test_azure_ce.py` | 本分支除了新增的測試之外，通過／失敗名單與 base 一致；整個 `platform/tests` 全綠（已知環境紅除外）；輸出貼在 ledger | 手動：閱卷看 ledger 並自己跑單檔 |
| TC-071 | 專長守則（對等性；不新增動作入口） | 不在範圍 | 本分支的 diff | 看 diff | 沒有新增或改動任何網頁路由、MCP 工具或指令；`maxMemoryGB` 只經過既有的建立環境與送出動作；沒有新資料表或新欄位（不需 migration，理由見 TC-005） | 手動：閱卷看 diff |
