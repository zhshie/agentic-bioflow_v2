# 測試案例：記下第一次 nano4 端到端 16S 驗收（r5）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/acceptance-nano4-record/plan.md`（本任務沒有 spec.md，計畫即規格；「維護者原話」「作法」「失敗先行測試」「完成標準」「不做」是依據）　**總覽**：`test-case-overview.md`

本任務只寫文件：把 2026-10-24 在 nano4 跑成的第一次 16S（nf-core/ampliseq 2.18.0）端到端，照空白驗收表的欄位填成一份存檔 `specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md`，另有進度帳 `specs/acceptance-nano4-record/ledger.md`。不跑真機、不改程式、不改測試。

名詞：
- 「新複本」＝ `specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md`。
- 「空白表」＝ `specs/007b-launch/acceptance-nano4.md`（檔頭寫明它永遠保持空白）。
- 「右欄」＝表格每一列最右邊要填的那一格。
- 「手動（閱卷）」＝閱卷者讀新複本、ledger 或用 grep／awk／`git diff` 對照預期結果（計畫「失敗先行測試」寫明這些由 verifier 驗）。
- 本任務所有數字與事實的唯一來源是計畫「作法」一節（它們來自 developer-agent 自己 2026-10-24 的 run 紀錄）。

類型只有三種：

- **功能**：計畫說要做到的事，做到了。
- **例外**：缺值、不該出現的東西出現時，必須被擋下或根本不存在。
- **不在範圍**：計畫明講不做的事，確認真的沒做。

## 維護者原話對照

| 維護者原話（計畫「維護者原話」節） | 對應 TC |
|---|---|
| 「第一里程碑＝16S（nf-core/ampliseq 2.18.0）在 nano4 端到端：Claude Desktop 或網頁 → 不經 Seqera → 啟動 → 結果頁。」 | TC-009、TC-013、TC-018 |
| 「每次先估 SU、記帳。」（本次 wallet 沒讀，SU 以 `sacct` 實測值代替並明寫是代替） | TC-014、TC-015、TC-022 |
| 派工明確要求：「沒做的格子寫『未記錄』並在備註說明」（空格不可，因為空格分不出「沒做」和「忘了填」） | TC-019～TC-029 |

## User Story 1 — 新複本是空白表的完整複本，空白表不動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 失敗先行測試第 1 條；作法首段（欄名與 `wallet`／`squeue`／`X-ABF-Platform` 都在） | 功能 | 新複本已存在於 `specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md` | 執行 `bash tests/docs_nano4_acceptance.sh docs/TESTING.md specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md` | 印出 `ok`、結束碼 0。作為對照：檔案不存在時同一指令印 `FAIL TC-012: … does not exist` 並非 0 結束（ledger 要有這個紅的輸出，見 TC-042） | 自動：`tests/docs_nano4_acceptance.sh`（帶參數） |
| TC-002 | 失敗先行測試第 2 條 | 功能 | 同上 | 執行不帶參數的 `bash tests/docs_nano4_acceptance.sh` | 仍印 `ok`、結束碼 0（空白表沒被弄壞） | 自動：`tests/docs_nano4_acceptance.sh` |
| TC-003 | 作法首段「九節標題……一字不改」 | 功能 | 新複本與空白表並排 | 把兩份檔裡九個編號小節標題（`## 1. Run` 到 `## 9. 備註`）逐行比對 | 九個標題文字、順序完全相同，沒有少、沒有多、沒有改字 | 手動（閱卷）：grep `^## ` 兩檔後 diff |
| TC-004 | 作法首段「表格欄位名一字不改」 | 功能 | 同上 | 比對兩份檔每個表格的左欄文字（欄位名／項目名，含 `日期`、`走哪條路`、`launch 前預估 SU`、`wallet 前`、`wallet 後`、`差額`、`head.sh`、`trace 行數`、`grep -c token`、`截圖檔名`、`備註`，以及 Preflight 十一個項目名） | 左欄文字與空白表逐字相同；只有右欄不同 | 手動（閱卷） |
| TC-005 | 「不得出現」節：說明列的 `/work/u9613010` 改寫成 `/work/<site_user>` | 功能 | 空白表第 1 節的「說明」列含 `/work/u9613010` | 讀新複本第 1 節「說明」列 | 該列路徑寫成 `/work/<site_user>`，該列其餘文字與空白表相同，沒有照抄 `u9613010` | 手動（閱卷） |
| TC-006 | 範圍「空白表……不動」；失敗先行測試第 2 條 | 不在範圍 | 分支已完成 | 執行 `git diff origin/v3...HEAD -- specs/007b-launch/acceptance-nano4.md` | 輸出為空；空白表一個字都沒變（包含檔頭 "Leave a cell empty" 那句） | 手動（閱卷） |

## User Story 2 — 這次實測到的值，照欄位填進去（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | 作法 §1「日期」 | 功能 | 新複本 | 讀第 1 節「日期」右欄 | 為 `2026-10-24` | 手動（閱卷） |
| TC-008 | 作法 §1「填表人」 | 功能 | 新複本 | 讀第 1 節「填表人」右欄 | 為 `developer-agent（依自己的 run 紀錄代填）；啟動確認人 zhshie（2026-10-24 11:14:20 在確認頁按下）` | 手動（閱卷） |
| TC-009 | 作法 §4 第一點；維護者原話 1 | 功能 | 新複本 | 讀第 4 節「run 名稱與 `<rid>`」右欄 | 含 `ampliseq_day5_nano4_r5`、`ae0d52e5e5fe5a98`，且 `ae0d52e5e5fe5a98` 被註明是「平台 run id」；另寫明 nf-core/ampliseq 2.18.0、計算環境 `nano4`、由 Claude Desktop 經平台 MCP 連接器送出 | 手動（閱卷）：grep 這四個字串 |
| TC-010 | 作法 §4；裁決二第 4 點 | 功能 | 新複本 | 讀同一格中關於確認頁網址 `/c/<rid>` 與平台 run id 是否為同一個值的句子 | 該句的答案是 `未記錄`；沒有寫「相同」或「不同」 | 手動（閱卷） |
| TC-011 | 作法 §4 第三點 | 功能 | 新複本 | 讀第 4 節「`squeue` 輸出」右欄 | 為 `未記錄（整段輸出）`，並僅記載 Slurm head 作業 `606916` 在 partition `ngsconsole`；沒有編造任何 squeue 輸出行或子作業 | 手動（閱卷）：grep `606916`、`ngsconsole` |
| TC-012 | 作法 §6 | 功能 | 新複本 | 讀第 6 節「trace 行數」右欄 | 為 `未記錄`（並註明 `trace.txt` 行數沒數），另有一句事實：平台收到了 Nextflow trace 事件；沒有任何行數數字 | 手動（閱卷） |
| TC-013 | 作法 §9 第一條；維護者原話 1 | 功能 | 新複本 | 讀第 9 節備註的「完成」那一條 | 含：Nextflow log 「Pipeline completed successfully」`12:00:31`；WorkflowStats `succeededCount=71`、`failedCount=1`（一個 task OUT_OF_MEMORY，自動重試後成功）；head 作業 `606916` 狀態 COMPLETED、耗時 `00:46:06` | 手動（閱卷）：grep `12:00:31`、`71`、`00:46:06`、`606916` |
| TC-014 | 作法 §9 第二條；維護者原話 2 | 功能 | 新複本 | 讀第 9 節備註的「SU 實測」那一條 | 標明是「代替 wallet 差額」；含 11:10–12:05、73 個 Slurm 作業、合計 `3.288` 核心小時；分區 ngs125g 0.800、ngs62g 1.174、ngsconsole 0.768、ngs16g 0.411、ngs8g 0.135；ngs 每核心小時 1 SU、約 3.3 SU；站台費率 `nano4.twd_per_su.nstc = 0.1`、約 NT$0.33；量法 `sacct -X` 的 ElapsedRaw × AllocCPUS。五個分區數字加總等於 3.288 | 手動（閱卷）：grep `3.288`、`0.33`，並手算加總 |
| TC-015 | 作法 §3 第三點；失敗先行測試末條 | 功能 | 新複本 | 在檔內搜尋 `3.288` 與 `0.33` | 這兩個數字只出現在第 9 節備註列；第 3 節的 wallet 前／後／差額三格裡沒有這兩個數字 | 手動（閱卷）：grep -n 看行號所屬小節 |
| TC-016 | 作法 §9 第三條 | 功能 | 新複本 | 讀第 9 節備註的「結果資料夾內容」那一條 | 列出 12 項：barrnap、cutadapt、dada2、fastqc、input、multiqc、overall_summary.tsv、phyloseq、pipeline_info、qiime2、summary_report、treesummarizedexperiment；不多不少 | 手動（閱卷） |
| TC-017 | 作法 §9 第四條；作法 §2 | 功能 | 新複本 | 讀第 9 節備註的「前史」那一條 | 含：r1–r3（2026-10-23／24）因四個站台問題失敗（nf-tower 插件目錄、NFCORE_SITE_REFERENCES、ref_taxonomy_storage、站台 singularity 映像壞），已由 PR #181 修；r4 因共用 ssh 連線過期，在 preflight 被拒、未建立任何東西 | 手動（閱卷） |
| TC-018 | 作法 §9 第五條；範圍界線「網頁路徑留 M2」 | 功能 | 新複本 | 讀第 9 節備註最後一條 | 寫明：未做／未記錄的步驟照各節標「未記錄」；第一次驗收只走 Claude Desktop，網頁路徑留 M2 | 手動（閱卷） |

## User Story 3 — 沒量到的欄位誠實寫「未記錄」，不補猜（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 作法 §1「走哪條路」 | 功能 | 新複本 | 讀第 1 節「走哪條路」右欄 | 為 `未記錄`（說明紀錄只寫計算環境 nano4）；沒有寫「國網模組」或「自裝 Nextflow」當答案 | 手動（閱卷） |
| TC-020 | 作法 §2 | 功能 | 新複本 | 讀第 2 節 Preflight 十一項（`connect`、`work_dir`、`sbatch`、`squeue`、`sinfo`、`java`、`nextflow`、`head_queue`、`modules`、`site_pipeline`、`library`）的右欄 | 十一格每一格都是 `未記錄`；沒有 `pass`、`fail`、`unchecked` 或其他結果 | 手動（閱卷） |
| TC-021 | 作法 §2「備註交代」 | 功能 | 新複本 | 讀 Preflight 節（各格或節內說明）與第 9 節備註 | 其中寫明：r4 因共用 ssh 連線過期在 preflight 被拒、什麼都沒建立；r5 沒留逐項輸出 | 手動（閱卷） |
| TC-022 | 作法 §3；維護者原話 2 | 功能 | 新複本 | 讀第 3 節四格：launch 前預估 SU、wallet 前、wallet 後、差額 | 四格都是 `未記錄`（wallet 沒讀）；沒有任何 SU 數字或「unknown」 | 手動（閱卷） |
| TC-023 | 作法 §4 第二點 | 功能 | 新複本 | 讀第 4 節「`head.sh` 全文」右欄 | 為 `未記錄`；沒有貼任何 head.sh 內容 | 手動（閱卷） |
| TC-024 | 作法 §5 | 功能 | 新複本 | 讀第 5 節三格（計算節點 curl 輸出、`way_back`、`ss -ltnp`） | 三格全是 `未記錄`；沒有寫 401、`direct`、0 | 手動（閱卷） |
| TC-025 | 作法 §6 第二點 | 功能 | 新複本 | 讀第 6 節「結果頁截圖檔名」右欄 | 為 `未記錄`；沒有編造檔名 | 手動（閱卷） |
| TC-026 | 作法 §7 | 功能 | 新複本 | 讀第 7 節兩格（`grep -c token` 對 head.sh、對 slurm-<jobid>.out） | 兩格都是 `未記錄`；沒有寫 0（沒查過，不能寫通過） | 手動（閱卷） |
| TC-027 | 作法 §8 | 功能 | 新複本 | 讀第 8 節 Fallback 一格 | 為 `未記錄`，並說明本次沒做 TC-051n；沒有 revision 或 `nextflow run … -r …` 內容 | 手動（閱卷） |
| TC-028 | 派工要求「空格不可」；失敗先行測試第 3 條 | 例外 | 新複本 | 掃描所有表格資料列（排除 `|---|` 分隔列），檢查每列最後一格 | 沒有任何一列的最後一格是空的（含只有空白的）；表頭那張「網頁路徑：M2」表的右欄也不是空的 | 手動（閱卷）：awk 掃表格列 |
| TC-029 | 作法 §9「逐字用這些事實，不加別的」；失敗先行測試末條 | 例外 | 新複本 | 把新複本中所有非從空白表複製來的文字、數字與事實，逐項對照計畫「作法」各節 | 每一個數字、時間、作業編號、狀態、結論都能在「作法」找到；多出的任何數字或事實（含從 Slack、對話或記憶補的）一律不合格；「未記錄」的格子裡沒有猜測值 | 手動（閱卷）：逐項比對 |

## User Story 4 — 不得外洩帳號、路徑、token（優先度 P1）

以下 TC 同時檢查新複本與 `specs/acceptance-nano4-record/ledger.md` 兩個檔。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 「不得出現」；失敗先行測試第 3 條 | 例外 | 兩個新檔 | `grep -n u9613010` 於兩檔 | 無任何命中 | 手動（閱卷）：grep |
| TC-031 | 同上 | 例外 | 兩個新檔 | `grep -n /home/` 於兩檔 | 無任何命中 | 手動（閱卷）：grep |
| TC-032 | 同上 | 例外 | 兩個新檔 | `grep -n -o '/work/[^ ]*'` 於兩檔 | 每個命中的 `/work/` 後面緊接 `<`（例如 `/work/<site_user>`）；沒有 `/work/` 後面接真實帳號 | 手動（閱卷）：grep |
| TC-033 | 「不得出現……任何 token」；維護者要求 "never paste a token" | 例外 | 兩個新檔 | 搜尋 `token`（不分大小寫）、`Bearer`、`tw_`、`eyJ`、`ghp_`，並找 20 字元以上的英數長字串 | 「token」只出現在欄位名、章節標題、檔頭說明與 `未記錄` 旁；沒有 Bearer／金鑰樣式字串；除計畫列出的 `ampliseq_day5_nano4_r5` 與 `ae0d52e5e5fe5a98`（皆非機密）外，沒有可疑長字串 | 手動（閱卷）：grep |
| TC-034 | 「`zhshie` 是 GitHub 帳號……可以寫在填表人欄」 | 例外 | 新複本 | `grep -n zhshie` 於新複本 | 只出現在第 1 節「填表人」那一格，其他位置沒有 | 手動（閱卷）：grep |
| TC-035 | 範圍：檔名 `<name>` 用角色詞 `maintainer`，不用真實帳號 | 功能 | 分支已完成 | 看新複本的檔名與路徑 | 路徑恰為 `specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md` | 手動（閱卷）：ls |

## User Story 5 — 範圍界線：計畫說不做的事沒有做（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-036 | 範圍：檔案；完成標準第 1 條 | 不在範圍 | 分支已完成 | 執行 `git diff --name-only origin/v3...HEAD` | 恰好三個檔：`specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md`、`specs/acceptance-nano4-record/ledger.md`、`specs/acceptance-nano4-record/plan.md`（plan.md 是派工時已進分支的計畫）；沒有第四個檔 | 手動（閱卷）：git diff |
| TC-037 | 範圍：不碰 `docs/TESTING.md`、`docs/SETTINGS.md` | 不在範圍 | 分支已完成 | `git diff origin/v3...HEAD -- docs/TESTING.md docs/SETTINGS.md` | 輸出為空 | 手動（閱卷）：git diff |
| TC-038 | 範圍：不碰 `scripts/`、`platform/`、`deploy/`、`tests/`；「不為這份存檔另外新增測試或腳本」 | 不在範圍 | 分支已完成 | `git diff origin/v3...HEAD -- scripts platform deploy tests` | 輸出為空；也沒有新增任何測試檔或腳本 | 手動（閱卷）：git diff |
| TC-039 | 範圍：網頁路徑留 M2；不補沒做的步驟 | 不在範圍 | 新複本 | 讀檔頭表格「網頁路徑：M2」那一列，並找整份檔有沒有任何網頁路徑的實測結果 | 該列文字與空白表相同（"Not checked now. Left for milestone M2…"）；全檔沒有網頁路徑已驗收的紀錄 | 手動（閱卷） |
| TC-040 | 待裁決 2、3：另案處理，本任務不做 | 不在範圍 | 分支已完成 | 讀空白表檔頭（"Leave a cell empty…"）與 `docs/TESTING.md` TC-047n 第 4 點 | 空白表檔頭那句沒變；`docs/TESTING.md` 仍寫 `image_library`、空白表仍寫 `library`（沒有順手對齊）；`library` 與 `image_library` 的不一致只記在 ledger，沒有動別的檔 | 手動（閱卷） |

## 完成標準

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | 完成標準第 2 條 | 功能 | 在 WSL 或 Linux 的本地磁碟 worktree | 執行 `bash tests/run_all.sh` | 全套綠；結果附在 ledger | 自動：`tests/run_all.sh` |
| TC-042 | 完成標準第 3 條「ledger 記每個步驟與紅綠輸出」 | 功能 | `specs/acceptance-nano4-record/ledger.md` | 讀 ledger | 記了每個步驟；含檔案不存在時 `FAIL TC-012: … does not exist` 的紅輸出，與完成後 `ok` 的綠輸出（帶參數與不帶參數各一）；有 `run_all.sh` 的結果；有記 `image_library`／`library` 名稱不一致 | 手動（閱卷） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-043 | 不變條件 3（任何人都能裝：不把個人機器路徑寫死）；其檢查 `tests/no_hardcoded_paths.sh` | 功能 | 分支已完成 | 執行 `bash tests/no_hardcoded_paths.sh` | 通過（`specs/` 不在它的掃描範圍，所以 TC-030～TC-032 的人工 grep 才是對新檔的實際把關） | 自動：`tests/no_hardcoded_paths.sh` |
| TC-044 | 安全網「憑證只放設定區，不印、不進 git」；其檢查 `tests/credentials_stay_in_settings_test.sh` | 功能 | 分支已完成 | 執行 `bash tests/credentials_stay_in_settings_test.sh` | 通過；新增的兩個檔沒有讓它變紅 | 自動：`tests/credentials_stay_in_settings_test.sh` |
