---
id: dataset-cli-launch
title: 資料集接上線：終端機指令 abf-platform dataset（登記／列出／看）＋ MCP launch 與 request_launch 可以用「資料集名稱＋版本」當輸入（含雲端 gs:// 資料集）
tier: B
kinds: backend
lane: L-dataset
base: v3（`origin/v3` @ 2385f97；所有行號都是該版本）。要等 cloud-cleanup-f 合併（它改 `actions/__init__.py`）才能開。
source: developer-agent 讀碼查證（2026-10-24）。cloud-upload.md「待 developer-agent 裁決」第 2、5 項（誰把 destination 接進入口；gs:// 位置如何進送出流程）；byte-channel-b.md 開頭（端到端還差「誰呼叫」）
---

# dataset-cli-launch

> 查證發現：`platform/abf_platform/actions/datasets.py` 的 `register_dataset`／`list_datasets`／`get_dataset`／`draft_samplesheet`／`check_web_upload`（含 cloud-upload 的 `destination`）**目前沒有任何入口呼叫**——`git grep "datasets" origin/v3 -- platform/abf_platform platform/abf_launch platform/abf_station` 除了 `datasets.py` 自己與 `actions/pipelines.py:1` 的一句註解，沒有命中；沒有 MCP 工具、沒有網頁路由、沒有終端機指令。012c 的網頁上傳頁（前端 session）會是網頁入口。本任務補**不碰網頁的兩個入口**：終端機登記，以及用資料集送出。**不新增 MCP 工具**（工具清單被十幾個測試逐字釘住，且 cloud-cleanup 系列也在動），只給既有的 `launch` 多兩個參數。B 級（後端行為改變、無畫面）：verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
①管理者在終端機用 `abf-platform dataset register …` 為某位使用者登記一份資料集（本機路徑或雲端 `gs://`）；②該使用者的 AI 呼叫 MCP `launch` 時，可以只說 `dataset="proj"`（可加 `dataset_version="v1"`）而不必貼樣本表；平台取出該資料集的樣本表，走和 `samplesheet_text` 完全相同的路徑與確認流程。對使用者的意義：雲端的第一個真實使用者（維護者自己）能把 `gcloud storage cp` 放好的檔案登記成可重用的輸入，不必每次手貼 CSV。

## 維護者原話（verifier 出題用）
- 「**雲端上傳＝平台代傳到使用者自己的 bucket、不落地（ADR 0010 規則），大檔給 `gsutil` 指令**」（`PLAN-abf-v3-replan-2026-10.md` 裁示 16，第 58 行；cloud-upload 裁決 3 已改用 `gcloud storage cp`）→ T9、T10：雲端資料集只認自己前綴下的 `gs://` 位置，登記時已由 `register_dataset` 擋；本任務不新增「寫入 bucket」的任何碼。
- 「**使用者用自己的 AI 走 MCP，不用 AI 的人走網頁**」（第 1 條，replan 第 37 行）→ T13、T14：AI 入口是既有的 `launch`，不另開工具。
- 「每個寫入要本人答應」（憲法 6／ADR 0006）→ T12、T15：用資料集送出仍然只產生待確認申請，本人在表單或確認頁按送出才有工作。
- 「**雲端第一個真實使用者＝他自己的自費帳號**」（10-21 拷問，replan 第 50 行（第 12 條））→ T16：沒有帳號的終端機／stdio 也能用（`caller=None`）。
- 「網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」（裁示 14）→ 本任務不得動 `web.py`／`web_board.py`（前端 session 擁有）。

## 範圍：檔案
- `platform/abf_platform/actions/__init__.py`：`request_launch`（:563）加關鍵字參數 `dataset=None, dataset_version=None`（接在 `path_columns` 之後）。
- `platform/abf_platform/mcp_server.py`：`launch_tool`（:117-124）加兩個參數並傳進去；`description`（:106-116）補一句。
- `platform/abf_platform/cli.py`：新增 `dataset` 指令群（`register`、`list`、`show`）。
- `platform/tests/test_dataset_launch.py`（新；檔首 `# Nothing existing: …` ≥15 字，TC-070）
- `platform/tests/test_dataset_cli.py`（新；同上）
- `specs/dataset-cli-launch/ledger.md`
- **不准動**：`actions/datasets.py`（`test_cloud_upload.py:603-610` TC-077 釘著它的公開函式清單恰為 `check_web_upload, draft_samplesheet, get_dataset, list_datasets, pair_fastq, register_dataset`，不新增任何公開函式）、`abf_launch/*`、`web.py`、`web_board.py`、`pipeline_launch.py`、`store.py`、`jobs.py`、`confirm.py`、`guidance.py`、`actions/chat_tools.py`、`abf_station/*`、`docs/*`（文件由 `cloud-upload-docs` 接手，不在本任務）。

## 作法（決定，不是程式碼）
1. **`request_launch` 的資料集分支**（函式一開頭、`_samplesheet_text_problem` 之前）：
   - `dataset is None and dataset_version is None`：整個函式與今天**位元不變**（含 `_samplesheet_text_problem` 的訊息 "samplesheet 與 samplesheet_text 只能給一個"，`test_http_site_samplesheet.py:22` 釘著）。
   - `dataset_version` 給了但 `dataset` 沒給 → `_no("未送出：dataset_version 要和 dataset 一起給 (dataset_version needs dataset)")`。
   - `dataset` 給了：`dataset` 與 `dataset_version`（若給）必須是非空 `str`，否則 `_no("未送出：dataset 必須是資料集的名稱 …")`；同時給了 `samplesheet` 或 `samplesheet_text` → `_no("未送出：dataset 與 samplesheet／samplesheet_text 只能給一個 (give dataset, or a samplesheet, not both)")`。
   - 取資料：函式內 `from . import datasets`（避免匯入循環，`datasets.py:153` 已有 `from . import caller_area` 的先例），呼叫 `datasets.get_dataset(platform_path, dataset, dataset_version, caller=caller)`（`datasets.py:377`）。`found` 為假 → `_no("未送出：找不到資料集 %s (dataset not found)")`，**別人的資料集與不存在的資料集同一句話**（`get_dataset` 已按擁有者篩選，`datasets.py:356-367`）。
   - 取到：`samplesheet_text = got["samplesheet"]`，然後**走原本的路**（`_samplesheet_text_problem` → `_sheet_and_area` → `build.prepare_launch` → `_finish_launch`）。不複製樣本表處理邏輯、不寫檔、不新增資料表欄位；內容包（bundle）不帶 `dataset` 鍵，所以核可雜湊、紀錄、續跑都與用 `samplesheet_text` 送出的一樣。
2. **MCP `launch`**：新增 `dataset: str | None = None`、`dataset_version: str | None = None`，原樣傳進 `actions.request_launch`；`required` 欄位仍是 `pipeline, revision, run_name`。描述補一句：「Or name a dataset of yours (dataset, optionally dataset_version): its samplesheet is used.」。屬性名不得含 `confirm|approve|yes|send|force|skip|accept|送出`（`test_http_site_samplesheet.py:459-460`）、`void`（`test_chat_tools.py:14`）。
3. **終端機 `abf-platform dataset`**（`cli.py` 的 `build_parser`，:529；模樣仿 `ce` 群 :597-621）：
   - `register --name N --version V --samplesheet FILE --file PATH [--file PATH …] [--user NAME] [--destination CE]`：讀 `FILE`（UTF-8，> 1 MiB、含 NUL、讀不到、不是 UTF-8 → exit 1，白話，什麼都不登記）；`--file` 至少一個（argparse `required`，缺 → argparse 的 exit 2）；呼叫 `datasets.register_dataset(state, name=…, version=…, samplesheet=<text>, files=[{"path": p}, …], caller=<Caller 或 None>, destination=…)`；回 `ok` → exit 0 並印 `已登記資料集 N 版本 V（K 個檔案）(registered)`；否則印該函式的 `message`、exit 1。**不讀、不 stat `--file` 的檔案**（平台只記名字，`datasets.py` 檔首原則）。
   - `list [--user NAME]`、`show NAME [--version V] [--user NAME]`：呼叫 `list_datasets`／`get_dataset`；`list` 每行 `名稱 版本 檔案數 時間`；`show` 印 JSON（`indent=2, sort_keys=True, ensure_ascii=False`，仿 `cmd_ce_show` :376）；找不到 → exit 1。
   - 身分：`--user` 解析**重用** `abf_launch.cli._account(name)`（`abf_launch/cli.py:62-76`；平台 `cli.py:647` 已匯入該模組為 `launch_cli`）：已有使用者卻沒給 `--user` → 該函式的白話拒絕、exit 1；沒有任何使用者 → `caller=None`（終端機看到全部）。
   - 這些指令**不加進** `ADOPTING`（`cli.py:649`）。選項名只用 `name version samplesheet file user destination`，不得觸到 `test_launch_platform.py:722-742` 的禁字集合。
4. **migration**：不需要（沒有動資料表；`datasets` 表與 `files_json` 內容不變）。
5. **不新增 MCP 工具、不新增網頁路由、不新增 `actions` 的公開函式**（`request_launch` 是既有的 INTERNAL 名稱，`test_web_parity.py:36`）。

## 失敗先行測試
`test_dataset_launch.py`（動作層與 MCP；夾具樣板：Slurm 側 `platform/tests/owner_harness.py:92-110`，雲端側 `platform/tests/test_cloud_wire.py:70-90` 的 `Wire`；複製所需部分，不改那兩個檔）
| # | 情境 | 期望 |
|---|---|---|
| T1 | alice 登記本機資料集 `proj`/`v1`（檔案在她的上傳資料夾），`request_launch(dataset="proj", …)` | 待確認申請 1 張；其 bundle 與同一份 CSV 用 `samplesheet_text` 送出的 bundle 逐鍵相同（除 run_name 若不同） |
| T2 | 同名兩個版本 `v1`、`v2`；不給版本／給 `dataset_version="v1"` | 前者用 v2（最新），後者用 v1 |
| T3 | `dataset` + `samplesheet` | 未送出、白話、`confirmations`／`jobs`／`launches` 皆 0 列變動 |
| T4 | `dataset` + `samplesheet_text` | 同 T3 |
| T5 | `dataset_version` 沒有 `dataset` | 未送出，訊息含 `dataset_version needs dataset` |
| T6 | `dataset=""`、`dataset=7`、`dataset_version=""` | 各自未送出、不丟例外 |
| T7 | 不存在的資料集 | 未送出，含 `dataset not found` |
| T8 | bob 的資料集，alice 呼叫 | 訊息與 T7 一字不差（只有名字不同）、不洩漏存在與否 |
| T9 | Google Batch 環境 `gcb1`，alice 登記雲端資料集（`destination="gcb1"`，兩個 `gs://<bucket>/uploads/alice/…`）後用它送出 | 待確認申請 1 張；bundle 的樣本表儲存格就是那兩個 `gs://` 位置；確認畫面有費用行（與 `samplesheet_text` 送出一致） |
| T10 | 同一份雲端資料集送到 Slurm 環境 | 未送出（現有的路徑拒絕訊息），沒有任何申請 |
| T11 | 兩個參數都不給（也不給樣本表） | 訊息逐字等於今天的 "samplesheet 與 samplesheet_text 只能給一個" |
| T12 | 用 MCP 呼叫 `launch(dataset=…)`，無表單答案 | 回「待確認」與確認網址、`jobs` 0 列 |
| T13 | MCP `launch` 的屬性集合 | 恰為今天的集合 ∪ {`dataset`, `dataset_version`}；`required` 仍是 `[pipeline, revision, run_name]`；無任何屬性命中 `confirm|approve|yes|send|force|skip|accept|送出|void` |
| T14 | 工具清單 | 仍恰為 13 個、名字不變（`test_pat.py:383`、`test_oauth_mcp.py:329` 不動） |
| T15 | 用 T12 的呼叫並由人按送出（`form_answer()`） | 有 1 個 `launch_nextflow` 工作；`launches` 紀錄與用 `samplesheet_text` 送出的欄位形狀相同；bundle 無 `dataset` 鍵 |
| T16 | stdio（`caller=None`），無使用者的平台，終端機登記的 `owner=None` 資料集 | 可用 `dataset=` 送出 |
`test_dataset_cli.py`（用 `ip.run(...)`，樣板 `test_owner_gaps.py:331-360`）
| # | 情境 | 期望 |
|---|---|---|
| C1 | 無使用者：`dataset register --name proj --version v1 --samplesheet s.csv --file a_R1.fastq.gz --file a_R2.fastq.gz`，再 `list`、`show proj` | exit 0／0／0；`list` 有一行；`show` 的 JSON 含 `samplesheet` 與兩個 `path` |
| C2 | 同 (名稱,版本) 再登記一次 | exit 1，訊息含「已存在」，資料集數不變 |
| C3 | 有使用者卻沒給 `--user` | exit 1，訊息是 `_account` 的那句，不登記 |
| C4 | `--user alice --destination gcb1`，檔案是 alice 前綴下的 `gs://` | exit 0；列表顯示 alice 的 |
| C5 | 同 C4 但檔案在 bob 的前綴 | exit 1，訊息只說 alice 自己的前綴，不登記 |
| C6 | `--samplesheet` 檔不存在／超過 1 MiB／含 NUL／非 UTF-8 | 各 exit 1，白話，不登記，輸出無 `Traceback` |
| C7 | `list --user alice` 不含 bob 的；`show` bob 的資料集（`--user alice`） | 前者沒有；後者 exit 1 且與「不存在」同一句 |
| C8 | 不給 `--file` | argparse 的用法錯誤（exit 2），不登記 |
| C9 | `--file` 是不存在的路徑（無使用者） | 仍登記成功，證明沒有讀檔 |
| C10 | `build_parser()` 整棵掃描（比照 TC-061）與 `ADOPTING` | 新增的名字只有 `dataset register list show` 與上列選項；`ADOPTING` 內容不變；`web.py` 路由表與 base 相同 |

**現在會紅**：全部（參數、指令都不存在；T11、T14 的現況斷言是綠的，用來鎖住）。
**會改斷言的既有測試：無。** 已核對必須維持綠且不改：`test_http_site_samplesheet.py:22,458-460,528`、`test_datasets.py`（全部）、`test_cloud_upload.py:603-610`、`test_launch_platform.py:722-742`、`test_confirm_page.py:319-333`、`test_chat_tools.py:57-86`、`test_pat.py:283,383`、`test_oauth_mcp.py:329-334`、`test_web_parity.py:113-118`、`test_scope.py` 的 TC-061／TC-071（掃 `abf_platform/` 原始碼，新字串不得含 `ssh`、`sbatch`、`scancel`、`tw `、`station`、`socket`、`subprocess`）。

## 完成標準（done when）
- T1–T16、C1–C10 全綠；WSL `bash tests/run_all.sh` 綠。
- `git diff --name-only` 只含上列 6 個檔；新增測試 ≤ 30 條；既有測試未刪、未跳過、未放寬。
- 沒有連網、沒有啟動程式、沒有讀任何 FASTQ。

## 環境事實
- 全套測試在 WSL／Linux 跑；worktree 不可在同步磁碟（repo `CLAUDE.md`「For the executor and verifier」）。
- 資料集擁有者規則：`get_dataset` 在 `caller` 非空時只回該人的列（`datasets.py:356-367`）；`caller=None` 看到全部（終端機）。
- 雲端資料集登記時已驗證「bucket＝該環境 workDir 的 bucket、位置在呼叫者自己的前綴」（`datasets.py:115-145,257-353`）；送出時 Google Batch 的 `render_gcb_bundle` 還會再驗一次每個路徑儲存格（`abf_station/launch.py:669-693`）。本任務不重做這些。

## 不做
- 不做網頁入口（012c-web 上傳頁，前端 session）、不做 MCP 的資料集工具、不做位元組通道（byte-channel-a／b）。
- 不在核可畫面或 bundle 記資料集名稱（需要時另開任務，會動 bundle 與核可雜湊）。
- 不改 `abf-platform launch`（終端機送出）；它仍只收 `--samplesheet`。

## 裁決
1. **為什麼不新增 MCP 工具**：新工具牽動至少 13 個釘著工具清單或數量的測試（`test_mcp.py:63,96`、`test_pat.py:383,751`、`test_oauth_mcp.py:329`、`test_human_channel.py:159`、`test_guidance.py:26`、`test_chat_tools.py:15`…），且 cloud-cleanup 系列同期也在動；登記資料集是管理者的終端機動作，AI 只需要「用」。若維護者要 AI 也能列出自己的資料集，另開唯讀任務並由該任務負責更新那批測試。
2. **登記放終端機而不是 AI 工具**：登記雲端資料集等於宣告「這些 gs:// 位置是我的」，由持有終端機的管理者代為登記，與 `runs assign`（`cli.py:448`）同一種信任模型；使用者自己上傳的路徑是 012c-web 的事。
3. **重用 `_account`**：同一條規則（有使用者就必須指名）在兩個指令群一致，不寫第二份。

## 裁決（2026-10-25，developer-agent）
1. 管理者從終端機登記資料集、AI 只透過既有 launch 工具的 `dataset`／`dataset_version` 兩個參數使用：接受。網頁上傳頁留給前端 session。
2. 資料集名稱不進 bundle 與核可雜湊：接受（samplesheet 內容已在雜湊裡）。

## 裁決（2026-10-27，developer-agent；派工前預檢結果，優先於上文）
3. **撞到 `platform/tests/test_datasets.py` TC-064（第 444-455 行）**：它禁止 `actions/__init__.py` 與 `mcp_server.py` 出現 `get_dataset`、`actions.datasets` 等字。作法 1 在 `request_launch` 呼叫 `datasets.get_dataset(...)` 一定會讓它變紅。准許、且只准這樣改那條測試：對 `platform/abf_platform/actions/__init__.py`，用 AST 找到 `request_launch` 的函式本體，`get_dataset` 在**該本體內恰好出現 1 次**、在**本體以外出現 0 次**；其餘禁字（`register_dataset`、`list_datasets`、`draft_samplesheet`、`check_web_upload`、`pair_fastq`、`actions.datasets`）對整個檔照舊全禁；`mcp_server.py`、`web.py`、`web_board.py`、`store.py` 照舊全禁。列入「必須更新的既有斷言」，PR 說明寫「以前／以後／理由：本任務就是把資料集接進 launch，只開這一個呼叫點」。不准用 `getattr`、字串拼接或別名等方式躲過這條測試。
4. `mcp_server.py` 只加兩個參數並原樣傳遞，不得 import datasets 模組、不得出現上述禁字。
5. 本任務在 cloud-cleanup-backfill 合併後才開（兩者都改 `cli.py` 與 `actions/__init__.py`）；開工先核對合併後的 `runs` 群、`offer_cleanups` 與 `ADOPTING`。

6. **（2026-10-27 21:50 補）`platform/tests/test_pipeline_launch.py` 第 490 行把 `request_launch` 的參數清單逐字釘死**：准許、且只准把該清單在 `path_columns` 之後加入 `"dataset", "dataset_version"`，其他元素與順序不動；列入「必須更新的既有斷言」，PR 說明寫以前／以後／理由。這是本任務第二處（也是最後一處）准改的既有測試。

7. **（2026-10-27 22:20 補）頂層指令清單有兩處逐字釘住，新增 `dataset` 群一定會撞**：`platform/tests/test_cleanup_offer.py` 的 `COMMANDS`（約 818 行，排序清單，`'dataset'` 放在 `'ce'` 與 `'fetch-records'` 之間）與 `platform/tests/test_station_envs.py` 的 `top_level` 集合（約 432 行，加入 `"dataset"`，行尾註解補「dataset-cli-launch: plus `dataset`」）。准許、且只准各加這一個字；兩個檔其餘內容不動。developer-agent 已 grep 過其他頂層指令釘（`test_launch_platform.py:742` 是子集合檢查、`test_onboarding_doc.py` 只檢查文件），不需要改。本任務准改的既有測試至此共四處：TC-064、test_pipeline_launch.py:490、這兩處。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
