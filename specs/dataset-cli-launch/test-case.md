# 測試案例：資料集接上線（終端機 abf-platform dataset 指令＋launch 可指定資料集）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
Source: specs/dataset-cli-launch/plan.md only (no spec.md exists for this B-tier task; the plan holds the goal, the maintainer quotes, the failing-test tables T1-T16 / C1-C10 and the rulings).
IDs in this file are TC-0xx; the plan's own T1-T16 / C1-C10 are cited in 對應需求.
Language: 繁體中文; identifiers and file paths stay as they are.
-->

**規格**：`specs/dataset-cli-launch/plan.md`（本任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞（一句話）：「資料集」＝管理者替某位使用者登記的一份「名稱＋版本＋樣本表（CSV）＋檔案位置清單」，平台只記名字，不讀檔案。「待確認申請」＝AI 呼叫 launch 後平台寫下的一張申請，要本人按送出才會真的有工作。「bundle」＝這張申請裡裝的送出內容包。

測試檔：`platform/tests/test_dataset_cli.py`（終端機，US1）、`platform/tests/test_dataset_launch.py`（動作層與 MCP，US2）、`platform/tests/test_datasets.py`（只改 TC-064 一個函式）。每條測試在註解寫出自己的 TC 編號。

## User Story 1 — 管理者在終端機登記、列出、查看資料集（優先度 P1）

維護者原話對應：「雲端第一個真實使用者＝他自己的自費帳號」→ 沒有任何帳號的終端機也能登記（TC-001、TC-022）。「登記放終端機而不是 AI 工具」→ 見 TC-023 至 TC-026。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | C1；作法 3 register | 功能 | 平台上沒有任何使用者；有檔案 s.csv（樣本表） | 執行 `dataset register --name proj --version v1 --samplesheet s.csv --file a_R1.fastq.gz --file a_R2.fastq.gz` | 結束碼 0，並印出 `已登記資料集 proj 版本 v1（2 個檔案）(registered)` | 自動：`platform/tests/test_dataset_cli.py` |
| TC-002 | C1；作法 3 list | 功能 | TC-001 之後 | 執行 `dataset list` | 結束碼 0；輸出恰好一行，含名稱 proj、版本 v1、檔案數 2、時間 | 自動 |
| TC-003 | C1；作法 3 show | 功能 | TC-001 之後 | 執行 `dataset show proj` | 結束碼 0；輸出是 JSON（縮排 2、鍵排序、中文不跳脫），含 s.csv 的全文（samplesheet）與 a_R1.fastq.gz、a_R2.fastq.gz 兩個 path | 自動 |
| TC-004 | 作法 3 show --version | 功能 | proj 有 v1、v2 兩個版本 | 執行 `dataset show proj --version v1` | 結束碼 0；JSON 的版本是 v1 | 自動 |
| TC-005 | C2 | 例外 | proj／v1 已登記 | 再用同一個名稱與版本登記一次 | 結束碼 1；訊息含「已存在」；資料集總數不變 | 自動 |
| TC-006 | C3 | 例外 | 平台上已有使用者 alice | 執行 `dataset register …` 但沒給 `--user` | 結束碼 1；訊息逐字就是 `abf_launch.cli._account` 的那句（「要用 --user 名字 指明這次送出是誰的…」）；沒有登記任何資料集 | 自動 |
| TC-007 | 作法 3 身分（對 list 一視同仁） | 例外 | 平台上已有使用者 alice | 執行 `dataset list` 但沒給 `--user` | 結束碼 1；訊息與 TC-006 同一句 | 自動 |
| TC-008 | 作法 3 身分（對 show 一視同仁） | 例外 | 平台上已有使用者 alice | 執行 `dataset show proj` 但沒給 `--user` | 結束碼 1；訊息與 TC-006 同一句 | 自動 |
| TC-009 | 作法 3 身分 | 例外 | 平台上已有使用者 alice | 執行 `dataset register … --user nobody` | 結束碼 1；訊息是 `_account` 的「沒有這個帳號：nobody」；沒有登記 | 自動 |
| TC-010 | C4 | 功能 | 有使用者 alice；有 Google Batch 環境 gcb1；兩個檔案在 `gs://<bucket>/uploads/alice/…` | 執行 `dataset register … --user alice --destination gcb1 --file gs://…alice… --file gs://…alice…` | 結束碼 0 | 自動 |
| TC-011 | C4 | 功能 | TC-010 之後 | 執行 `dataset list --user alice` | 列表裡有這份資料集，屬於 alice | 自動 |
| TC-012 | C5 | 例外 | 同 TC-010，但檔案在 bob 的前綴 `gs://<bucket>/uploads/bob/…` | 執行同樣的登記（`--user alice`） | 結束碼 1；訊息只說「要在 alice 自己的前綴下」，不洩漏 bob 的任何資訊 | 自動 |
| TC-013 | C5（寫入側的跨使用者） | 例外 | 同 TC-012 | 執行同樣的登記後，列出所有資料集 | alice 沒有因此多出任何資料集（總數不變） | 自動 |
| TC-014 | C6 | 例外 | `--samplesheet` 指向不存在的檔案 | 執行 register | 結束碼 1；白話訊息；沒有登記；輸出不含 `Traceback` | 自動 |
| TC-015 | C6 | 例外 | `--samplesheet` 檔案大於 1 MiB | 執行 register | 結束碼 1；白話訊息；沒有登記；輸出不含 `Traceback` | 自動 |
| TC-016 | C6 | 例外 | `--samplesheet` 檔案內含 NUL 字元 | 執行 register | 結束碼 1；白話訊息；沒有登記；輸出不含 `Traceback` | 自動 |
| TC-017 | C6 | 例外 | `--samplesheet` 檔案不是 UTF-8 | 執行 register | 結束碼 1；白話訊息；沒有登記；輸出不含 `Traceback` | 自動 |
| TC-018 | C7 | 例外 | alice、bob 各有一份資料集 | 執行 `dataset list --user alice` | 輸出沒有 bob 的那一份 | 自動 |
| TC-019 | C7（讀取側的跨使用者） | 例外 | bob 有資料集 bobset；alice 沒有 | 執行 `dataset show bobset --user alice`，再執行 `dataset show nosuchset --user alice` | 前者結束碼 1，訊息與後者「不存在」的訊息一字不差（只有名字不同） | 自動 |
| TC-020 | 作法 3 show 找不到 | 例外 | 沒有叫 nosuchset 的資料集 | 執行 `dataset show nosuchset` | 結束碼 1；訊息含「找不到資料集」 | 自動 |
| TC-021 | C8 | 例外 | 無 | 執行 `dataset register --name proj --version v1 --samplesheet s.csv`（沒給任何 `--file`） | argparse 用法錯誤，結束碼 2；沒有登記 | 自動 |
| TC-022 | C9 | 功能 | 沒有使用者；`--file` 指向一個根本不存在的路徑 | 執行 register | 結束碼 0 且登記成功（證明平台沒有讀、也沒有 stat 那個檔案） | 自動 |
| TC-023 | C10 | 不在範圍 | 無 | 掃描 `build_parser()` 整棵樹（比照 `test_launch_platform.py` 的 TC-061 走法） | 相對 base 新增的名字只有 `dataset register list show` 與選項 `name version samplesheet file user destination`；且不含 retry、confirm、yes、y、force、assume-yes、no-confirm | 自動 |
| TC-024 | C10；作法 3 | 不在範圍 | 無 | 讀 `cli.ADOPTING` | 仍恰為 `("serve", "web", "mcp", "ce")`，`dataset` 沒有加進去 | 自動 |
| TC-025 | C10；「不做網頁入口」 | 不在範圍 | 無 | 比對 `web.py` 的路由表與 base | 完全相同；本任務沒有新增任何網頁路由，`web.py`、`web_board.py` 沒被改 | 自動 |
| TC-026 | 「不改 abf-platform launch」 | 不在範圍 | 無 | 看終端機 `launch` 指令的選項 | 仍只收 `--samplesheet`，沒有 `--dataset`、`--dataset-version` | 自動 |

## User Story 2 — AI 用既有的 launch 工具，以資料集名稱當輸入（優先度 P1）

維護者原話對應：「使用者用自己的 AI 走 MCP，不用 AI 的人走網頁」→ 入口是既有 `launch`，不另開工具（TC-054、TC-058）。「每個寫入要本人答應（憲法 6／ADR 0006）」→ 只產生待確認申請，本人按送出才有工作（TC-036、TC-037、TC-051、TC-052、TC-059）。「雲端上傳＝平台代傳到使用者自己的 bucket、不落地」→ 雲端資料集只認自己前綴的 `gs://` 位置，本任務不新增寫 bucket 的碼（TC-045 至 TC-049、TC-066）。「雲端第一個真實使用者＝他自己的自費帳號」→ 無帳號的 stdio 也能用（TC-062）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | T1 | 功能 | alice 登記了本機資料集 proj／v1（檔案在她的上傳資料夾） | alice 呼叫 `request_launch(dataset="proj", …)` | 產生恰好 1 張待確認申請 | 自動：`platform/tests/test_dataset_launch.py` |
| TC-031 | T1 | 功能 | TC-030 的申請；另用同一份 CSV 以 `samplesheet_text` 送出一張 | 比較兩張申請的 bundle | 逐個鍵完全相同（run_name 若本來就不同則除外） | 自動 |
| TC-032 | T2 | 功能 | 同名 proj 有 v1、v2 兩個版本 | 呼叫 `request_launch(dataset="proj", …)`，不給版本 | 用的是 v2（最新）的樣本表 | 自動 |
| TC-033 | T2 | 功能 | 同 TC-032 | 呼叫時給 `dataset_version="v1"` | 用的是 v1 的樣本表 | 自動 |
| TC-034 | T3 | 例外 | proj 存在 | 同時給 `dataset` 和 `samplesheet` | 未送出；訊息為「未送出：dataset 與 samplesheet／samplesheet_text 只能給一個 (give dataset, or a samplesheet, not both)」 | 自動 |
| TC-035 | T4 | 例外 | proj 存在 | 同時給 `dataset` 和 `samplesheet_text` | 未送出；訊息同 TC-034 | 自動 |
| TC-036 | T3 | 例外 | 記下呼叫前 `confirmations`、`jobs`、`launches` 的列數 | 做 TC-034 的呼叫 | 三張表列數都沒變動 | 自動 |
| TC-037 | T4 | 例外 | 記下呼叫前三張表的列數 | 做 TC-035 的呼叫 | 三張表列數都沒變動 | 自動 |
| TC-038 | T5 | 例外 | 無 | 只給 `dataset_version="v1"`，沒給 `dataset` | 未送出；訊息含 `dataset_version needs dataset` | 自動 |
| TC-039 | T6 | 例外 | 無 | `dataset=""` | 未送出、白話訊息、不丟例外 | 自動 |
| TC-040 | T6 | 例外 | 無 | `dataset=7`（不是文字） | 未送出、白話訊息、不丟例外 | 自動 |
| TC-041 | T6 | 例外 | proj 存在 | `dataset="proj"`、`dataset_version=""` | 未送出、白話訊息、不丟例外 | 自動 |
| TC-042 | 作法 1（dataset_version 也必須是非空文字） | 例外 | proj 存在 | `dataset="proj"`、`dataset_version=7` | 未送出、白話訊息、不丟例外 | 自動 |
| TC-043 | T7 | 例外 | 沒有叫 nosuchset 的資料集 | `request_launch(dataset="nosuchset", …)` | 未送出；訊息含 `dataset not found` | 自動 |
| TC-044 | T8（讀取側的跨使用者） | 例外 | bob 有資料集 bobset；alice 沒有 | alice 呼叫 `dataset="bobset"`；另呼叫 `dataset="nosuchset"` | 兩句訊息一字不差（只有名字不同），看不出 bobset 存在 | 自動 |
| TC-045 | T9 | 功能 | Google Batch 環境 gcb1；alice 以 `destination="gcb1"` 登記雲端資料集（兩個 `gs://<bucket>/uploads/alice/…`） | alice 用 `dataset=` 送出到 gcb1 | 產生恰好 1 張待確認申請 | 自動 |
| TC-046 | T9 | 功能 | 同 TC-045 | 看該申請的 bundle | 樣本表的檔案儲存格就是那兩個 `gs://` 位置，沒有別的 | 自動 |
| TC-047 | T9 | 功能 | 同 TC-045；另以 `samplesheet_text` 送出同一份 CSV 到 gcb1 | 看兩張確認畫面 | 資料集那張有費用行，且和 `samplesheet_text` 那張一致 | 自動 |
| TC-048 | T10 | 例外 | 同一份雲端資料集；目標是 Slurm 環境 | alice 用 `dataset=` 送出 | 未送出，訊息就是現有的路徑拒絕訊息（不是新造的句子） | 自動 |
| TC-049 | T10 | 例外 | 同 TC-048 | 看三張表 | 沒有任何新申請 | 自動 |
| TC-050 | T11 | 功能 | 完全不給 dataset、dataset_version、samplesheet、samplesheet_text | 呼叫 `request_launch` | 訊息逐字等於今天的「未送出：samplesheet 與 samplesheet_text 只能給一個 (give exactly one of samplesheet and samplesheet_text)」 | 自動 |
| TC-051 | T12 | 功能 | proj 存在；MCP 客戶端沒有表單答案 | 呼叫 MCP `launch(dataset="proj", …)` | 回「待確認」與確認網址 | 自動 |
| TC-052 | T12 | 例外 | 同 TC-051 | 看 `jobs` 表 | 0 列（沒有人按送出就沒有工作） | 自動 |
| TC-053 | 作法 2「原樣傳進」 | 功能 | proj 有 v1、v2 | 呼叫 MCP `launch(dataset="proj", dataset_version="v1", …)` | 申請用的是 v1 的樣本表 | 自動 |
| TC-054 | T13 | 功能 | 無 | 讀 MCP `launch` 的屬性集合 | 恰為今天的集合加上 `dataset`、`dataset_version`，不多不少 | 自動 |
| TC-055 | T13 | 功能 | 無 | 讀 MCP `launch` 的 `required` | 仍恰為 `[pipeline, revision, run_name]` | 自動 |
| TC-056 | T13；作法 2 | 例外 | 無 | 用 `confirm|approve|yes|send|force|skip|accept|送出|void` 掃 `launch` 的所有屬性名 | 沒有任何一個命中 | 自動 |
| TC-057 | 作法 2 描述 | 功能 | 無 | 讀 `launch` 的 description | 含這一句：「Or name a dataset of yours (dataset, optionally dataset_version): its samplesheet is used.」 | 自動 |
| TC-058 | T14；「不新增 MCP 工具」 | 不在範圍 | 無 | 列 MCP 工具清單 | 仍恰為 13 個，名字與 base 完全相同，沒有任何資料集工具 | 自動 |
| TC-059 | T15 | 功能 | 同 TC-051；本人按送出（`form_answer()`） | 再呼叫一次同樣的 `launch` | 恰好有 1 個 `launch_nextflow` 工作 | 自動 |
| TC-060 | T15 | 功能 | 同 TC-059；另用 `samplesheet_text` 送出同一份 CSV | 比較兩邊 `launches` 紀錄 | 欄位形狀相同 | 自動 |
| TC-061 | T15；作法 1 | 功能 | 同 TC-059 | 看送出時的 bundle | 沒有 `dataset` 鍵、也沒有 `dataset_version` 鍵 | 自動 |
| TC-062 | T16 | 功能 | stdio（`caller=None`），平台沒有任何使用者；終端機登記了 owner 為空的 proj | 用 `dataset="proj"` 送出 | 產生待確認申請，可用 | 自動 |
| TC-063 | 「不做」：不在核可畫面或 bundle 記資料集名稱 | 不在範圍 | 資料集名稱取一個樣本表和檔名裡都沒有的獨特字串 | 用它送出，看確認畫面與 bundle | 兩處都找不到這個資料集名稱 | 自動 |
| TC-064 | 作法 4「不需要 migration」 | 不在範圍 | 無 | 比對 `datasets` 表欄位與 base；看有沒有新增 migration | 欄位完全相同；沒有新 migration；`store.py` 沒被改 | 自動 |
| TC-065 | 範圍「不准動 datasets.py」；作法 5 | 不在範圍 | 無 | 列 `actions/datasets.py` 的公開函式（`test_cloud_upload.py` TC-077、`test_datasets.py` TC-063 的檢查） | 仍恰為 `check_web_upload, draft_samplesheet, get_dataset, list_datasets, pair_fastq, register_dataset`；檔案本身沒被改 | 自動 |
| TC-066 | 維護者原話「平台代傳、不落地」；完成標準「沒有連網、沒有啟動程式、沒有讀 FASTQ」 | 不在範圍 | 無 | 跑 `test_scope.py` 的 TC-061／TC-071 對 `abf_platform/` 的掃描；執行 register 時 `--file` 指向的檔案不被開啟（TC-022） | 掃描全綠：新增程式碼不含 `ssh`、`sbatch`、`scancel`、`tw `、`station`、`socket`、`subprocess`；本任務沒有任何寫 bucket、連網、啟動程式、讀 FASTQ 的新程式 | 自動 |

## 憲法與安全網

本任務碰到：憲法第 1 條（新增檔案要說明為何自己寫）、第 2 條（唯一的送出路徑、未經本人確認不得送出、不得有第二份執行狀態）。另外含 backend 專長守則的對應。

專長守則對應（沒有另外開新行的，直接指向已有的 TC）：

- 跨使用者「讀」：TC-019（終端機）、TC-044（launch）；「寫」：TC-012、TC-013（alice 不能把資料集登記到 bob 的前綴下）。
- 確認管道：TC-036、TC-037、TC-052、TC-059（沒按送出就不改變 `jobs`／`confirmations`／`launches`）。
- migration：TC-064（不需要 migration 且表結構不變）。
- 錯誤訊息：TC-014 至 TC-017、TC-034、TC-038、TC-043 要求白話原因；是否夠白話見總覽「需要人看」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 第 2 條（唯一送出路徑） | 功能 | 無 | 跑 `tests/no_second_run_state_test.sh`（其送出掃描涵蓋 `platform/`）與 `test_tch09_*`、`test_tch09_b_c_*`（未確認的 launch 被 MCP 與網頁路由拒絕） | 全綠；沒有新增任何會送出的檔案 | 自動：`tests/no_second_run_state_test.sh` |
| TC-081 | 第 1 條（新檔要說明為何自己寫） | 功能 | 無 | 跑 `tests/scripts_name_their_alternative.sh`，涵蓋新增的 `test_dataset_launch.py`、`test_dataset_cli.py` | 兩個檔案開頭 40 行內都有 `# Nothing existing: …`，理由至少 15 個字，且腳本通過 | 自動：`tests/scripts_name_their_alternative.sh` |
| TC-082 | 2026-10-27 裁決 3 | 功能 | 修改後的 `test_tc064_other_sessions_files_are_untouched` | 用 AST 找 `actions/__init__.py` 裡 `request_launch` 的函式本體，數 `get_dataset` | 在該函式本體內恰好出現 1 次，而且是直接呼叫 `datasets.get_dataset(…)` | 自動：`platform/tests/test_datasets.py` |
| TC-083 | 2026-10-27 裁決 3 | 不在範圍 | 同 TC-082 | 數 `get_dataset` 在 `actions/__init__.py` 函式本體以外的出現次數 | 0 次 | 自動 |
| TC-084 | 2026-10-27 裁決 3 | 不在範圍 | 同 TC-082 | 在 `actions/__init__.py` 整個檔案找 `register_dataset`、`list_datasets`、`draft_samplesheet`、`check_web_upload`、`pair_fastq`、`actions.datasets` | 一個都不出現（整檔照舊全禁） | 自動 |
| TC-085 | 2026-10-27 裁決 3、4 | 不在範圍 | 同 TC-082 | 在 `mcp_server.py`、`web.py`、`web_board.py`、`store.py` 找原本七個禁字（含 `get_dataset`）；並看 `mcp_server.py` 是否 import datasets 模組 | 全部一個都不出現；`mcp_server.py` 沒有 import datasets | 自動 |
| TC-086 | 2026-10-27 裁決 3（只准這樣改那條測試；不准躲過） | 不在範圍 | 比對 `platform/tests/test_datasets.py` 與 base | 看 diff | 只動了 `test_tc064_other_sessions_files_are_untouched` 一個函式，其他測試一字未動；改法是 AST 數法，沒有用 `getattr`、字串拼接或別名繞過；PR 說明有「以前／以後／理由」 | 手動：閱卷者以 `git diff origin/v3...HEAD -- platform/tests/test_datasets.py` 核對（分支範圍檢查，非永久性質） |
| TC-087 | 計畫「必須維持綠且不改」清單 | 功能 | 無 | 跑清單中的測試檔：`test_http_site_samplesheet.py`（:22、:458-460、:528）、`test_datasets.py`（除 TC-064 外全部）、`test_cloud_upload.py`、`test_launch_platform.py`（:722-742）、`test_confirm_page.py`（:319-333）、`test_chat_tools.py`（:57-86）、`test_pat.py`（:283、:383）、`test_oauth_mcp.py`（:329-334）、`test_web_parity.py`（:113-118）、`test_scope.py` | 全綠；除 TC-086 那一處外，這些檔案相對 base 沒有刪、跳過或放寬任何斷言 | 自動：上述各檔（`bash tests/run_all.sh` 於 WSL） |
| TC-088 | 範圍：不准動清單；完成標準 | 不在範圍 | 比對 worktree 與 `origin/v3` | `git diff --name-only origin/v3...HEAD`（扣掉 `specs/dataset-cli-launch/` 的計畫與合約檔） | 只含：`platform/abf_platform/actions/__init__.py`、`platform/abf_platform/mcp_server.py`、`platform/abf_platform/cli.py`、`platform/tests/test_dataset_launch.py`、`platform/tests/test_dataset_cli.py`、`platform/tests/test_datasets.py`（僅 TC-064）、`specs/dataset-cli-launch/ledger.md`；沒有 `datasets.py`、`abf_launch/*`、`web.py`、`web_board.py`、`pipeline_launch.py`、`store.py`、`jobs.py`、`confirm.py`、`guidance.py`、`chat_tools.py`、`abf_station/*`、`docs/*`、`spec`、`test-case*.md` | 手動：閱卷者以 `git diff --name-only` 核對（分支範圍檢查，非永久性質） |
| TC-089 | 完成標準「新增測試 ≤ 30 條；未刪、未跳過」 | 不在範圍 | 無 | 數 `test_dataset_launch.py`、`test_dataset_cli.py` 的新增測試，並查有無 skip／xfail | 合計不超過 30 條；沒有 skip／xfail；現有測試條數沒減少 | 手動：閱卷者以 `git diff` 與 `pytest --collect-only` 核對 |
| TC-090 | 專長守則：對等性 | 功能 | 無 | 同時列出兩邊：使用者可見的資料集動作（終端機 `dataset register`／`list`／`show`、MCP `launch` 的 `dataset` 參數）與動作層函式（`register_dataset`、`list_datasets`、`get_dataset`、`request_launch`） | 一一對應：每個終端機子指令各呼叫對應的動作層函式、`launch` 的 `dataset` 走 `request_launch`；指令處理函式裡沒有第二份邏輯；`test_web_parity.py` 仍綠（`request_launch` 仍是 INTERNAL 名稱） | 自動：`platform/tests/test_dataset_cli.py`、`platform/tests/test_web_parity.py` |
| TC-091 | 專長守則：錯誤訊息與日誌 | 例外 | 測試用一組已知的假 token 與密碼 | 觸發 TC-005、TC-012、TC-014 至 TC-017、TC-034、TC-043、TC-044 的失敗，收集所有輸出、回應與日誌 | 不含 `Traceback`、SQL 字樣（如 `SELECT`、`sqlite`）、內部絕對路徑，也不含那組 token／密碼 | 自動 |
