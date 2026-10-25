---
id: release-lookup-job
title: 站台代理新增唯讀工作 pipeline_files：替平台去 GitHub 讀公開檔（參數表、樣本表欄位、流程圖、release tag 清單），平台只排工作、收文字、用既有純模組解析
tier: B
kinds: backend
lane: L-release
after: cloud-cleanup-c
base: v3 在 cloud-cleanup-c 合併之後（我讀的是 worktree `C:/Users/marvi/Desktop/agentic-bioflow/wt/cloud-cleanup-c`，分支 feat/cloud-cleanup-c @ ab4d4e8，它已含 origin/v3 @ 6dc879a；行號都是該版本，動手前以函式名重新 grep）
source: developer-agent 讀碼查證（2026-10-25）；維護者 10-25 經前端 session 的提問選「好，放寬」；release-tag-pick 裁決 1（走 (a)）；schema-reader（#214）、release-tag-pick（#207）已建好的純模組；guided-launch-2 被擋（BLOCKED(contract)）要等這片
---

# release-lookup-job

> **給前端 session（guided-launch-2）的呼叫名稱，先看這裡：**
> - `actions.pipeline_files(platform_path, pipeline, revision, *, parts=None, compute_env=None, caller=None, enqueue=True)` → dict（參數表、樣本表欄位、流程圖清單、流程圖圖檔）
> - `actions.latest_release(platform_path, pipeline, *, compute_env=None, caller=None, enqueue=True)` → dict（該 pipeline 的最新可啟動版本）
> - 兩個都是**同步、不等待**的函式（比照 `run_outputs`，`actions/__init__.py:334`），回 `state: loading|ready|error`；`loading` 時頁面照 run 頁的做法每 15 秒重整再問一次。**這片不加 MCP 工具、不加網頁路由**（見裁決 3）。回傳形狀見「作法」第 8 節，逐字固定。
> - 工作種類（站台代理與 `platform.db` 的 `jobs.kind`）叫 **`pipeline_files`**。
>
> 順序：本任務 `after: cloud-cleanup-c`。理由：兩者都改 `abf_station/handlers.py` 的 `JOB_KINDS`／`ARG_KEYS`／分派。**另外它也要改 `store.py`、`jobs.py`**，所以不能與 `byte-channel-a`（lane L-byte，同樣改這兩檔、也加一個工作種類）平行；誰後合併誰 rebase，種類**一律接在清單最後**（見作法 3 與「會改斷言的既有測試」的通則）。

## 目標
站台代理（跑在使用者那邊、能連網）新增一種**唯讀**工作 `pipeline_files`：替平台去 GitHub 公開 repo 讀某個 nf-core pipeline 在**釘死版本**的 `nextflow_schema.json`、`assets/schema_input.json`、`docs/images` 目錄清單與其中一張流程圖，以及 release tag 清單，把文字／位元組交回平台。平台進程自己不連網（`test_scope.py:187` TC-061 掃整個 `abf_platform/`）：它只排工作、收結果、用既有純模組 `schema.py`（#214）解析參數表與樣本表欄位、用 `releases.py`（#207）挑最新版並做 24 小時快取。對使用者的意義：引導式送出的頁面能秀出這條管線的流程圖、參數分組表、樣本表欄位，新專案能預填「最新版並寫死成版本號」，而不必使用者自己去 GitHub 查。

## 維護者原話（verifier 出題用）
- 「好，放寬」（2026-10-25，他在前端 session 的提問中選的選項；內容是：讓站台代理新增唯讀工作種類，讀公開 GitHub 檔——`nextflow_schema.json`、`assets/schema_input.json`、`docs/images`、最新 release tag）→ F-01～F-14（站台端抓取）、Q-01～Q-12（排隊與回傳）、A-01～A-20（動作層）。放寬的範圍就是這四類公開檔，**不多不少**→ S-02（主機白名單）、S-12（只讀、不寫、不帶憑證）、S-13（拒收其他路徑／分支名）。
- 「Pin an exact pipeline revision, never a branch, when launching or reading a pipeline's schema/README/diagrams — those are all read live from the pipeline's repo at that revision, never cached here」（repo `CLAUDE.md` Working conventions）→ S-12b（revision 必須是精確 tag 或 40 位 sha，分支名一律拒絕）、A-14（檔案內容平台**不另存快取檔**；只有「最新版」這個答案走 24 小時快取，見裁決 2）。
- 「新專案預設最新版並釘住」「launch 表單與 MCP 預填＝該 pipeline 最新 release tag」（replan 第 28、172 行，引自 `release-tag-pick.md`）→ A-15～A-19（`latest_release` 回具體版本號，不是 `latest`／分支名）。
- 憲法原則 2＋任務交辦：「平台不連網」（TC-061）→ S-17、Q-14（平台原始碼不得出現連網字樣；連網只在 `abf_station/pipeline_files.py`）。
- 「每個寫入要本人答應」（憲法 6／ADR 0006）→ 本工作**唯讀**，不需要確認（裁決 1）→ Q-02（不帶 `confirmation_id` 能排進去）、Q-03（`jobs.CONFIRMED` 仍剛好三項）。

## 範圍：檔案（只准改這些）
新增：
- `platform/abf_station/pipeline_files.py`（新；檔首 `# Nothing existing: …` ≥15 字，`test_scope.py:76` TC-070 檢查 `abf_station/` 也要）：主機白名單、`allowed(url)`、`OPEN`（可注入的抓取函式）、各部分的抓取與上限、git 智慧型 HTTP 清單轉 ls-remote 文字、挑流程圖、`run_fetch(job, ctx)`。
- `platform/tests/test_station_pipeline_files.py`（新；檔首同上）
- `platform/tests/test_pipeline_files_queue.py`（新；檔首同上）：`store.py` 放行與遷移、`jobs.py` 排隊／領取／清洗／讀取。
- `platform/tests/test_pipeline_files_action.py`（新；檔首同上）：動作層。
- `specs/release-lookup-job/ledger.md`

修改（只限所列之處）：
- `platform/abf_station/handlers.py`：頂部 import（:14 加 `pipeline_files`）、`JOB_KINDS`（:17）**接在 `clean_work` 後面**加 `"pipeline_files"`、`ARG_KEYS`（:18-20）加 `"pipeline_files": pipeline_files.ARGS`、`handle()` 分派（:49-51 `clean_work` 那行之後）加一行 `if kind == "pipeline_files": return pipeline_files.run_fetch(job, ctx)`、模組說明（:2-5）補一句。不動其他種類。
- `platform/abf_platform/store.py`：`_JOBS_TABLE` 的 `kind` CHECK（:240）清單尾端加 `'pipeline_files'`；`_jobs_kinds_current`（:408-409）改為三個字樣（`read_task_log`、`clean_work`、`pipeline_files`）都在才算已遷移；`_migrate_jobs_kinds` 說明文字（:413）補一句。`confirmation_id` 那條 CHECK（:252）**不動**。
- `platform/abf_platform/jobs.py`：`DEADLINE_SECONDS`（:26）尾端加 `"pipeline_files": 90`、`_DEADLINE_ENV`（:28-34）加 `"pipeline_files": "ABF_PLATFORM_DEADLINE_PIPELINE_FILES"`；新常數 `PF_PARTS`、`PF_STATUSES`、`PF_RETRY_SECONDS = 60`、`TAGS_CACHE_SECONDS = 24 * 3600`、`TAGS_CACHE_FILE = "release-tags.json"`；`_target`（:87）的 Google Batch 放行清單加 `"pipeline_files"`；新函式 `pick_environment`、`enqueue_pipeline_files`、`latest_pipeline_files`；`clean_result`（:683，**不得落入最後的 `else`**）加 `pipeline_files` 分支。`CONFIRMED`（:42）不動。
- `platform/abf_platform/actions/__init__.py`：新增 `pipeline_files`、`latest_release` 兩個公開函式與若干底線開頭的私有輔助（**公開名稱只准這兩個**，常數與輔助一律 `_` 開頭，否則 `test_web_parity.py` 的聯集檢查會紅，見下）。
- 允許更新的既有測試（只改所列斷言，逐條「舊→新＋理由」寫進 ledger）：`platform/tests/test_web_parity.py`（`WEB_ONLY` 表）、`test_cleanup_store.py`、`test_station_platform.py`、`test_cloud_cost.py`、`test_launch_platform.py`、`test_resume_scope.py`、`test_cleanup_confirm.py`、`test_station_clean.py`；清單見「會改斷言的既有測試」。
- `docs/PLATFORM.md`（四處，見作法 10）、`docs/TESTING.md`（一個手動步驟，見完成標準）。

**不准動**：`platform/abf_platform/schema.py`、`releases.py`（只呼叫，不改；`releases.repo_of` 對 `./x` 這種「單點段」會放行，站台端自己補檢查，見作法 2）、`mcp_server.py`、`guidance.py`、`chat_tools.py`、`web.py`、`web_board.py`、`web_launch.py`、`cli.py`、`confirm.py`、`compute_envs.py`、`receiver.py`、`abf_station/{launch,cancel,clean,fetch,readlog,site,rules,agent,cli}.py`、`abf_launch/*`、`tests/no_second_run_state_test.sh`、`platform/tests/station_harness.py`（不需要新的假站台功能；本工作不碰站台）、`pyproject.toml`（沒有新資料檔）、`test_actions_layer.py`、`test_chat_tools.py`、`test_guidance.py`、`test_estimate_su.py`、`test_pat.py`、`test_oauth_mcp.py`（MCP 工具數不變）。

## 作法（決定）
### 1. 工作的形狀（平台與代理共同遵守，逐字）
- 種類 `pipeline_files`。工作的 `args` 鍵集合恰為 `ARGS = {"repo", "revision", "parts"}`：
  - `repo`：`"nf-core/ampliseq"` 形（owner/name）。
  - `revision`：`"2.18.0"`、`"v3.0.0"` 或 40 位小寫十六進位 sha；**`parts` 只有 `["tags"]` 時必須是 `null`**，其餘必須是字串。
  - `parts`：非空 list，元素取自 `["schema", "schema_input", "diagram", "image", "tags"]`，不重複，**平台一律以這個順序排**。`image` 蘊含 `diagram`（要先看目錄清單才知道抓哪一張），結果裡兩者都有。
- **工作 `args` 不帶 `ce` 快照**（和別的種類不同）：這個工作不碰站台，代理不需要環境設定。工作列的 `compute_env`、`agent` 欄仍照常填（`_insert_job`，`jobs.py:108`），只是用來找「哪個代理去做」。
- 領取／回報走既有通道（`claim` :626、`take_result` :769），沒有新路由、沒有新資料表、沒有新欄位。

### 2. 站台代理怎麼抓（`abf_station/pipeline_files.py`）
- **抓取方式**：標準函式庫 `urllib.request`（代理已用它連平台，`agent.py:12-14`；這是 `abf_station/` 裡**第二個**會連網的檔案，其餘站台檔案不得出現 `urllib.request`，S-17 掃描釘住）。不用 `git`、不用 `subprocess`（代理在 WSL／Linux，不保證裝了 git；`ls-remote` 的資料用 git 的智慧型 HTTP 協議自己讀，見下）。
- **主機白名單**（唯一三個，`allowed(url)` 檢查，每次請求前都檢查，不通過連 `OPEN` 都不呼叫）：`github.com`（只用於 tag 清單）、`raw.githubusercontent.com`（檔案與圖）、`api.github.com`（只用於 `docs/images` 目錄清單）。條件：scheme 恰為 `https`、`hostname` 與清單逐字相等（不分大小寫比對前先轉小寫）、沒有帳密（`@`）、沒有埠號。**不跟隨轉址**（自訂 `HTTPRedirectHandler` 回 `None`）；收到 3xx 該部分記 `bad_response`。使用系統代理設定（預設行為，使用者的網路環境可能需要）。
- **所有請求**：`GET`；標頭只有 `User-Agent: abf-station/<__version__>` 與 `Accept`（API 用 `application/vnd.github+json`，其餘 `*/*`）；**不帶 Authorization、Cookie 或任何憑證**（S-12）。單次請求逾時 10 秒；整個工作總預算 45 秒（`time.monotonic()`，可注入 `CLOCK`）；超過即視為網路失敗。
- **網址**（repo 與 revision 驗過才組，值只含 `[A-Za-z0-9._/-]`，不做 URL 編碼的必要）：
  - schema：`https://raw.githubusercontent.com/<repo>/<revision>/nextflow_schema.json`
  - schema_input：`https://raw.githubusercontent.com/<repo>/<revision>/assets/schema_input.json`
  - diagram 清單：`https://api.github.com/repos/<repo>/contents/docs/images?ref=<revision>`
  - image：`https://raw.githubusercontent.com/<repo>/<revision>/docs/images/<name>`，`<name>` 是從清單挑出且符合 `^[A-Za-z0-9][A-Za-z0-9._-]{0,100}\.(png|svg)\Z`
  - tags：`https://github.com/<repo>.git/info/refs?service=git-upload-pack`（git 智慧型 HTTP 的 v0 公告，與 `git ls-remote` 同源同資料，**不吃 GitHub API 的每小時 60 次匿名額度**——release-tag-pick 的環境事實 T9 就是為這個設計的）。
- **上限（超過一律不整份讀進來，用 `read(上限+1)` 判斷）**：schema、schema_input 各 1,000,000 位元組；目錄清單 1,000,000；image 2,000,000（PNG 魔術字 `\x89PNG\r\n\x1a\n`；SVG 要能以 UTF-8 解碼且前 4096 字內有 `<svg`；不符 → `bad_response`）；tag 公告 4,000,000，轉出的文字最多 1,000,000 字元。
- **repo／revision 驗證（代理自己再驗一次，不信平台）**：repo 用 `releases.repo_of`（`from abf_platform import releases`；`launch.py:26`、`rules.py:10` 已有從平台套件 import 的先例），**另加**每一段不得全由點組成（擋 `./x`、`x/.`）；revision 用 `launch.REVISION`（`launch.py:54`，精確 tag 或 40 位 sha，**分支名一律不過**）；`parts` 規則見 1。任何一項不符 → `rules.Refusal`（`handlers.handle` 轉成 `refused`），**一個請求都不發**。
- **各部分狀態**（每個要求的部分各有 `status`）：`ok`、`not_found`（404）、`too_large`、`bad_response`（其他 4xx／5xx、3xx、內容不合格）、`rate_limited`（429，或 403 且 `X-RateLimit-Remaining: 0`）、`none`（只用於 `diagram`：沒有目錄或沒有候選圖）。任何一次請求出現**連線層失敗**（`URLError`、`OSError`、逾時、超過總預算）→ **整個工作**回 `("error", {"ok": False, "error": "network", "message": …})`，後面的部分不再試（失敗快速返回，避免 4 × 10 秒）。
- **挑流程圖（確定性）**：目錄清單中 `type == "file"`、名稱符合上面的 `.png|.svg` 形、小寫後含 `metro` 或 `workflow` 者為候選；排序鍵 `(含 metro 者在前, png 在 svg 前, 名稱短者在前, 名稱字母序)`；依序取第一個 `size`（清單給的整數；缺少視為未知、交給讀取上限）≤ 2,000,000 者；有候選但全超過 → `too_large`；沒有候選 → `none`。實例：ampliseq 2.18.0 的清單有 `ampliseq_workflow.png`（753,702）、`ampliseq_workflow.svg`（348,755）、`ampliseq_workflow_multiplesequencingruns.png`（189,695）、`ampliseq_workflow_multiplesequencingruns.svg`（228,700）→ 選 `ampliseq_workflow.png`。
- **tag 清單轉文字**：解 pkt-line（每筆 4 位十六進位長度＋內容，`0000` 為 flush）；略過 `# service=…` 那筆；第一筆 ref 行 NUL 之後是能力清單，要切掉；只留 `refs/tags/<名>` 且名字不以 `^{}` 結尾者，輸出每行 `<sha>\trefs/tags/<名>\n`（即 `git ls-remote --tags --refs` 的格式，平台用 `releases.parse_ls_remote` 解）。`Content-Type` 不是 `application/x-git-upload-pack-advertisement` 或長度欄壞掉 → `bad_response`。
- **回給平台的永遠是代理自己的短句與整理過的欄位**，不轉貼 GitHub 的原始標頭或錯誤頁。`message` ≤ 300 字，中英並陳。
- **可注入的抓取點（測試用，一律不連真網路）**：模組層級 `OPEN(url, headers, timeout, limit) -> (status:int, headers:dict, body:bytes)`，預設為真的 `urllib` 實作；網路失敗丟 `OSError`。測試用 `monkeypatch.setattr(pipeline_files, "OPEN", fake)`，並以 autouse fixture 把預設 `OPEN` 換成「一呼叫就讓測試失敗」的函式，確保沒有任何測試漏網連到真的 GitHub。測試**直接呼叫** `handlers.handle(job, ctx)`（同行程，`ctx` 用 `abf_station.agent.Context(None, settings_file, "", "a1")`；本工作不用 `ctx.site`），另有一條走真的代理行程＋`FakePlatform` 的調度測試（只送會被拒絕的壞參數，所以也不需要網路）。

### 3. 平台：資料庫放行與排隊（`store.py`、`jobs.py`）
- `store.py`：`_JOBS_TABLE` 的 CHECK 清單變成 `… 'read_task_log', 'clean_work', 'pipeline_files'`；`_jobs_kinds_current` 要求三個字樣都在 `sql_text` 裡，舊表會被 `_migrate_jobs_kinds` 一次升到最新（既有的重建流程：一個交易、依共同欄位名複製、保留 id 與 AUTOINCREMENT 計數、失敗全部回滾，`store.py:412-445`）。**這是資料結構變動，所以有 migration**；PR 說明寫：只重建 `jobs` 表（放寬一個 CHECK），不碰其他表。`connect_state` 呼叫順序不變。
- **種類順序規則（和 byte-channel-a 並存）**：`pipeline_files` 一律**接在清單最後**（`DEADLINE_SECONDS` 字典尾端、CHECK 清單尾端）。測試不寫死「總共幾種」，改為：`KINDS` 中 `pipeline_files` 出現恰一次，且在 `clean_work` 之後；既有七種彼此的相對順序不變。若 byte-channel-a 先合併，`put_upload` 已在尾端，本片接在它後面；反之亦然。誰後合併誰 rebase，`_jobs_kinds_current` 要求的字樣取兩者聯集。
- `jobs.py` 新函式（簽章固定）：
  - `pick_environment(con, caller_user_id, compute_env, now, offline_after)` → CE 的列（`sqlite3.Row`）。`compute_env` 有給 → 只用它（過 `_target`，擁有者不符時用 `_not_found` 的措辭）。沒給 → 候選＝該使用者**自己**的環境（`owner_user_id == caller_user_id`；`caller_user_id is None`＝本機終端機，所有環境都算），依名稱排序，逐一過 `_target(con, name, "pipeline_files", …)`，取第一個通過者；**不要求狀態是 `available`**（這個工作不碰站台，剛建立、還沒預檢的環境也能查 GitHub；`_target` 的 :101 本來就只對 `list_site_files`／`launch_nextflow` 要求）。`disabled`、`unsupported` 照 `_target` 擋。**Google Batch 環境放行**（:87 的清單加這個種類）：雲端使用者的代理在平台主機上，同樣能連網，他們也需要引導式送出。全部沒有 → `JobRefused("no online agent of yours (沒有在線的代理): …")`（句中不得出現字面 `station`、`ssh`，TC-061）。
  - `enqueue_pipeline_files(state_path, repo, revision, parts, *, compute_env=None, clock=time.time, deadline_seconds=None, offline_after=None, caller_user_id=None)` → 工作 id。一個交易內：`pick_environment` → `_insert_job(con, row, "pipeline_files", {"repo", "revision", "parts"}, now, seconds)`，`confirmation_id` 為 NULL。`repo`／`revision`／`parts` 在這裡**再驗一次**（形狀同 1；不合 → `JobRefused`，什麼都不排）。**這是唯一能排這個種類的入口。**
  - `latest_pipeline_files(state_path, repo, revision, parts, caller_user_id)` → `{"id", "state", "deadline_at", "finished_at", "result"}` 或 `None`。唯讀（`store.open_readonly`）。取該使用者擁有的環境上、`kind = 'pipeline_files'` 的最新 200 筆（`JOIN compute_envs ON name`，`caller_user_id is None` 時不限擁有者），第一筆 `args` 完全相等（`repo`、`revision`、`parts` 皆同）者；比照 `latest_listing`（:303）。別人的工作永遠看不到。
- `deadline_seconds("pipeline_files")` 預設 90（比 `cancel_run` 同；代理一次只做一件事，可能正在做別的工作），可由 `ABF_PLATFORM_DEADLINE_PIPELINE_FILES` 覆寫，壞值（`abc`、`0`、`-5`）回 90（沿用 `deadline_seconds` :44 的邏輯）。
- `clean_result("pipeline_files", result)` 白名單（代理無法讓平台存更多）：沿用頂端對 `ok`／`message`／`error`／`note` 的處理；再加 `repo`（str ≤ 140）、`revision`（str ≤ 40 或 None）、`parts`（dict，鍵只留 `PF_PARTS` 內的）。每個部分：`status` 必須在 `PF_STATUSES`，否則整個部分改成 `{"status": "bad_response"}`；`message` ≤ 300；`text`（只有 `schema`、`schema_input`、`tags`）str ≤ 1,000,000 字元，超過 → 該部分改成 `{"status": "too_large"}`；`diagram`／`image` 的 `name` 須符合上述名稱形、`type` 只能是 `image/png` 或 `image/svg+xml`、`size` 用 `_int`；`image.data_b64` ≤ 2,800,000 字元且只含 base64 字元，否則該部分 `bad_response`。**任何其他鍵一律丟掉**（`headers`、`url`、`token`、`stdout`、`entries`……）。
- 工作列保留期不變：完成後 7 天，在下一次排任何工作時清掉（`jobs.py:25` `PRUNE_AFTER_SECONDS`、:109 的 DELETE）。這代表 `result_json` 會暫存最多 7 天的公開檔內容（含最多約 2.8 MB 的圖）；這是傳輸紀錄，不是快取（見裁決 2）。

### 4. 要不要確認（唯讀，不需要）
`jobs.CONFIRMED`（:42）只有 `launch_nextflow`、`cancel_run`、`clean_work` 三項會寫東西；`_JOBS_TABLE` 的第二條 CHECK（`store.py:252`）也只對這三種要求 `confirmation_id`。唯讀種類全不需要：`enqueue_fetch` 與 `enqueue_task_log` 的說明寫明 "It only reads, so it needs no confirmation"（`jobs.py:182`、:204）；`_enqueue` 的說明寫 "The kinds that need no confirmation"（:156）。`pipeline_files` 屬同類：不寫站台、不寫使用者資料、不花錢、不送出任何使用者內容（請求裡只有公開 repo 名與版本），所以**不加入 `CONFIRMED`、不新增確認種類、不碰 `confirmations` 表**。

### 5. 動作層：兩個同步讀取（`actions/__init__.py`）
都回 dict、永遠不丟例外、不阻塞（不呼叫 `wait_for_result`）。`caller` 為 `None`＝本機終端機。`platform_path` 是 `platform.db` 的路徑（同 `run_outputs`／`list_site_files`）。
**`pipeline_files` 的狀態機**（`parts` 預設 `("schema", "schema_input", "diagram")`；`enqueue=False` 時只看不排）：
1. 驗證：`releases.repo_of(pipeline)`（ValueError → `bad_input`）；`revision` 必須是字串且符合 `^(v?[0-9]+(\.[0-9]+){1,3}|[0-9a-f]{40})\Z`（同 `launch.REVISION`；平台端自己一份，不 import `abf_station`）；`parts` 取自 `("schema","schema_input","diagram","image")`（**`tags` 在這個函式不收**，那是 `latest_release` 的）、不重複、非空，否則 `bad_input`。`bad_input` 時什麼都不排。
2. `job = jobs.latest_pipeline_files(…)`。
3. 沒有 → `enqueue` 為真就 `jobs.enqueue_pipeline_files(…)`（`JobRefused` → `state:"error"`、`error:"no_agent"`，`reason` 用它的訊息）→ `loading`；`enqueue=False` → `loading`（什麼都沒排）。
4. 工作還在 `queued`／`claimed` 且 `status.now() <= deadline_at` → `loading`。超過期限仍在 → 當作失敗 `no_answer`（沒有人在等所以沒人把它標成 expired，比照 `run_outputs` :373-375）。
5. 工作 `done` 且 `result.ok` → 解析：`schema` 部分 `status ok` → `schema.load(text)`＋`schema.parameter_groups`＋`schema.required_without_default`；`schema_input` 部分 → `schema.load`＋`schema.samplesheet_columns`；`ValueError` → 該部分改成 `{"status": "bad_json", "message": …}`。其餘部分原樣帶出。若**所有被要求的部分都不是 `ok`／`none`** → 整體當失敗，`error` 取它們共同的狀態（不同則取第一個，順序依 `parts`），`reason` 白話；否則 `state:"ready"`（部分失敗不擋，例如沒有 `schema_input.json` 的 pipeline 照樣 ready，那個部分帶 `not_found`）。
6. 工作失敗（`refused`／`error`／`expired`，或 4 的過期）→ `state:"error"`：`error` 是 `refused`（`reason` 說代理版本可能太舊、請更新 abf-station，因為舊代理對未知種類回「不支援」，`handlers.py:41`）、`network`（結果的 `error` 欄）、`no_answer`。**失敗顯示 `PF_RETRY_SECONDS`（60）秒**（從 `finished_at`，沒有就從 `deadline_at` 起算）；超過就視同沒有這筆工作、重新走 3（會排新工作，`loading`）。
7. **平台不另存檔案快取**。已完成的工作列本身是 7 天內的紀錄，同一組 `(repo, revision, parts)` 在這段時間重複問，**重用同一筆已完成工作，不再排新的**（釘死版本的內容不會變）；工作列被清掉後才會再排。這不是給「最新版」用的（最新版會變，見 `latest_release`）。
**`latest_release` 的狀態機**：
1. 驗證：`releases.repo_of`（失敗 → `bad_input`）。
2. 快取檔路徑＝`platform.db` 同資料夾的 `jobs.TAGS_CACHE_FILE`（`release-tags.json`；用 `os.path.dirname(os.path.abspath(platform_path))`，不寫死位置，比照 `store.uploads_root` :307）。先 `releases.lookup(pipeline, _no_fetch, cache_path=…, clock=status.now, ttl=jobs.TAGS_CACHE_SECONDS)`，`_no_fetch` 一律丟例外：若 `source == "cache"` → 直接 `ready`，**不排工作**。回來是 `stale-cache` 的先記著當退路。
3. 沒有新鮮快取 → `jobs.latest_pipeline_files(plat, repo, None, ("tags",), caller_id)`：沒有／失敗已超過 60 秒 → 排新工作（`enqueue` 為真時）→ `loading`；進行中 → `loading`；`done` 且 `finished_at >= now - TAGS_CACHE_SECONDS` → 取 `result.parts.tags.text` → `releases.parse_ls_remote` → `releases.lookup(pipeline, lambda repo: tags, cache_path=…, clock=status.now, ttl=…)`（這一步寫入快取），回 `ready`（`source: "fetched"`）；`lookup` 回沒有可用版本（`revision None`）→ `error`／`no_release`。
4. 工作失敗：有退路（stale-cache）→ `ready`、`source:"stale-cache"`、`why` 說明失敗原因；沒有 → `error`（`error` 同 pipeline_files 的對照）。**失敗不寫快取**（`releases.lookup` 的既有行為，T16）。
5. 輸出永遠含 `pipeline`（正規化後 `owner/name`；`bad_input` 時是原輸入的字串或 `None`）。

### 6. 回傳形狀（固定；`json.dumps` 得過；鍵永遠都在）
**`pipeline_files`**：
```
{"state": "loading" | "ready" | "error",
 "pipeline": "nf-core/ampliseq",            # repo_of 之後；bad_input 時是原輸入（str 或 None）
 "revision": "2.18.0",
 "parts": ["schema", "schema_input", "diagram"],     # 實際被問的，標準順序
 "checked_at": 1760000000.0 | None,         # 工作 finished_at；loading 為 None
 "error": None | "bad_input" | "no_agent" | "no_answer" | "network" | "rate_limited" | "not_found" | "too_large" | "bad_response" | "refused",
 "reason": None | "<一句白話，中英並陳；state == error 時必有>",
 "schema":       None | {"status": "ok", "groups": [<schema.parameter_groups 的元素>], "required_without_default": ["outdir"]}
                      | {"status": "not_found" | "too_large" | "bad_json" | "bad_response" | "rate_limited", "message": "…"},
 "schema_input": None | {"status": "ok", "columns": [<schema.samplesheet_columns 的元素>]} | {"status": …, "message": "…"},
 "diagram":      None | {"status": "ok", "name": "ampliseq_workflow.png", "type": "image/png", "size": 753702}
                      | {"status": "none"} | {"status": "too_large" | "not_found" | "bad_response" | "rate_limited", "message": "…"},
 "image":        None | {"status": "ok", "name": "…", "type": "image/png" | "image/svg+xml", "size": 753702, "data_b64": "…"}
                      | {"status": …, "message": "…"}}
```
沒被要求的部分是 `None`；`loading` 時四個部分全是 `None`。`error` 時各部分也是 `None`（整體失敗不夾帶殘缺資料）。`image.data_b64` 只在 `parts` 含 `"image"` 時有；前端 `/launch/diagram` 路由用 `parts=("image",)` 呼叫，自己 base64 解碼並依 `type` 設 `Content-Type`（SVG 的安全標頭是前端的事，guided-launch-2 裁決 3）。
**`latest_release`**：
```
{"state": "loading" | "ready" | "error",
 "pipeline": "nf-core/ampliseq",
 "revision": "3.0.0" | None,                 # ready 時必為能直接送去啟動的版本字串（通過 REVISION）
 "source": "fetched" | "cache" | "stale-cache" | "none",
 "checked_at": 1760000000.0 | None,
 "why": None | "<原因一句>",                  # ready 但 stale-cache、或 error 時有
 "error": None | "bad_input" | "no_agent" | "no_answer" | "network" | "rate_limited" | "not_found" | "no_release" | "refused"}
```
前五個鍵與 `releases.lookup` 的回傳同名同義，另加 `state`、`error`。
**失敗形狀範例（逐字）**：網路不通 → `{"state": "error", "pipeline": "nf-core/ampliseq", "revision": "2.18.0", "parts": ["schema","schema_input","diagram"], "checked_at": <finished_at>, "error": "network", "reason": "代理連不到 GitHub，請檢查那台機器的網路 (the agent could not reach GitHub; check that machine's network)", "schema": None, "schema_input": None, "diagram": None, "image": None}`；`schema_input.json` 404 → `state:"ready"` 且 `"schema_input": {"status": "not_found", "message": "這個版本沒有 assets/schema_input.json (this revision has no assets/schema_input.json)"}`；檔案過大 → 該部分 `{"status":"too_large", …}`；名稱不合（如 `"../x"`）→ `{"state":"error","error":"bad_input","reason":"pipeline 名稱不合格 …", …}` 且資料庫沒有新工作列。

### 7. 為什麼不新增 MCP 工具、不新增網頁路由
前端需要的是動作層的名字（本檔頂端）。加 MCP 工具會牽動一長串釘死工具數／名單的測試與文件（`test_actions_layer.py:27,35`（含整段 `BASELINE`）、`test_chat_tools.py:15`、`test_guidance.py:26`、`test_estimate_su.py:297`、`test_gcb_ce.py:776`、`test_gcb_launch.py:1069`、`test_http_site_samplesheet.py:562`、`test_human_channel.py:159`、`test_keep_submissions.py:705`、`test_launch_e2e.py:185`、`test_web_parity.py` 的 `OWED`、`docs/PLATFORM.md:6,357` 的工具數句子、`guidance.py` 的工具數句、`test_pat.py`／`test_oauth_mcp.py` 的 `len(tools) == 12`），而這片沒有任何人需要它。所以：**本片兩個函式登記在 `test_web_parity.py` 的 `WEB_ONLY` 表**（「有動作、有網頁用、沒有 MCP 工具」的合法位置），說明寫「guided launch reads pipeline files and the newest release through the agent (release-lookup-job); no MCP tool yet」。前端之後若要 MCP 對等，把它們從 `WEB_ONLY` 搬進 `WEB_ROUTES` 並加工具，那時再一次改上面那串；不在本片。

### 8. 其餘
- **migration**：需要，見 3。
- **失敗訊息**：全部白話、中英並陳、不露出堆疊、路徑、SQL（沿用 `_INTERNAL_WORDS` 的思路，`actions/__init__.py:322`；`reason` 一律是本片自己的固定句，不轉貼代理傳來的 `message`，除非它通過同一個過濾——沿用 `_outputs_reason`）。
- **憲法掃描**：平台新增的程式不得出現字面 `station`、`ssh`、`sbatch`、`scancel`、`tw `、`site agent`、`urllib.request`、`import socket`、`socket.`、`threading`、`subprocess`、`while True`（`test_scope.py:99,186`）；也不得出現 `watchdog`、`POLICY`（`test_cloud_cost.py:743`）。「代理」一律寫 agent。站台新檔不得出現 `sbatch`／`srun`／`nextflow run` 開頭的字串（`tests/no_second_run_state_test.sh` scan 1）、不得有 `rm -rf`（cloud-cleanup-c 的 `clean.py` 才准）、不得有 `/home/…/`、`/work/…/` 形的路徑（`tests/no_hardcoded_paths.sh:28`）。
- **文件（`docs/PLATFORM.md`）**：①第 6 節（:126）的「三件唯讀的事」清單補一項 `pipeline_files`，並把 :134 的「The agent never opens a connection of its own」限定為「toward the site」，另加一句：這是代理唯一會連到網際網路的工作，只問 `github.com`、`raw.githubusercontent.com`、`api.github.com` 三個主機上的公開檔，不帶任何憑證、不寫入、不跟隨轉址；②「What the platform stores」表（:626）加一列：`Newest release of a pipeline | release-tags.json (next to platform.db) | 24 hours`（`tests/platform_storage_doc_test.sh` TC-004 要求 Where 欄的名字出現在程式碼、TC-009 要求「24 hours」對得上 `abf_platform/*.py` 裡的常數，所以常數寫成 `TAGS_CACHE_SECONDS = 24 * 3600`，**放在 `jobs.py` 頂層**）；③設定一節（:658）補 `ABF_PLATFORM_DEADLINE_PIPELINE_FILES`（90）；④「Action layer」節（:546）補 `pipeline_files` 與 `latest_release` 各一句。

## 失敗先行測試
全部現在會紅（新模組、新種類、新函式都不存在）。executor 先跑一次貼紅輸出。每個新測試檔首行 `# Nothing existing: …` ≥15 字。

### 站台端：`test_station_pipeline_files.py`（同行程，注入 `OPEN`）
| 編號 | 案例 | 預期 |
|---|---|---|
| S-01 | `handlers.JOB_KINDS`、`ARG_KEYS` | `"pipeline_files"` 在 `JOB_KINDS` 且位於 `"clean_work"` 之後；既有種類彼此相對順序不變；`ARG_KEYS["pipeline_files"] == {"repo","revision","parts"}`；`set(JOB_KINDS) == set(ARG_KEYS)`；對未知種類的拒絕訊息含 `pipeline_files` |
| S-02 | `allowed(url)` 表：三個主機的 https 網址；`http://`、`https://github.com.evil.com/x`、`https://evil.com/github.com`、`https://raw.githubusercontent.com@evil.com/x`、`https://raw.githubusercontent.com:8443/x`、`ftp://…`、`https://nf-co.re/pipelines.json`、空字串 | 前者 True，其餘全 False；False 的情形 `OPEN` 零次呼叫 |
| S-03 | ampliseq 2.18.0、`parts` = schema＋schema_input＋diagram，假 `OPEN` 回 fixture（`platform/tests/fixtures/schema/ampliseq-2.18.0.nextflow_schema.json`、`tests/fixtures/schema_input/ampliseq-2.18.0.json`、上面四筆目錄清單） | 請求依序恰為 raw schema、raw schema_input、api contents 三個網址；結果 `("done", {"ok": True, …})`，`parts.schema.status == "ok"` 且 `text` 逐字等於 fixture；`parts.diagram == {"status":"ok","name":"ampliseq_workflow.png","type":"image/png","size":753702}`；`parts` 的鍵剛好是被要求的三個 |
| S-04 | 挑圖排序表（參數化）：有 `metro` 的 svg 與無 metro 的 png → 選 metro；同為 workflow → png 優先；同為 png → 名稱短者；第一候選 `size` 2,000,001、第二 100 → 選第二；全超過 → `too_large`；無候選／目錄 404 → `{"status":"none"}`；名稱含空白、`../`、`.gif` → 不是候選 | 如左 |
| S-05 | `parts` = `["image"]`，假回 PNG 位元組（開頭是 PNG 魔術字） | 請求 = 目錄清單＋`raw…/docs/images/ampliseq_workflow.png`；`parts.image.data_b64` 解碼後逐位元組等於假回的位元組；`type "image/png"`；結果同時有 `diagram` |
| S-06 | 同上但位元組不是 PNG／SVG 沒有 `<svg`／超過 2,000,000 | 該部分 `bad_response`／`bad_response`／`too_large`；假 `OPEN` 沒被要求讀超過 `limit` |
| S-07 | `parts` = `["tags"]`、`revision None`，假回 git 公告（pkt-line：服務行、flush、HEAD 行含 NUL 能力、`refs/heads/main`、`refs/pull/1/head`、`refs/tags/2.18.0`、`refs/tags/2.18.0^{}`、`refs/tags/3.0.0`、`refs/tags/3.0.0dev`） | 請求只有 `https://github.com/nf-core/ampliseq.git/info/refs?service=git-upload-pack`；`parts.tags.text` 恰為 `<sha>\trefs/tags/2.18.0\n<sha>\trefs/tags/3.0.0\n<sha>\trefs/tags/3.0.0dev\n`；`releases.parse_ls_remote(text)` → `["2.18.0","3.0.0","3.0.0dev"]`；`releases.pick_latest` → `"3.0.0"` |
| S-08 | tag 公告的 `Content-Type` 錯、長度欄不是十六進位、被截斷、超過 4,000,000 | `bad_response`／`bad_response`／`bad_response`／`too_large` |
| S-09 | `schema_input.json` 回 404，其餘 200 | 該部分 `not_found`，其餘 `ok`；整體仍 `done`、`ok True` |
| S-10 | schema 回 1,000,001 位元組 | `too_large`；沒有 `text` 鍵 |
| S-11 | 速率限制：api 回 403＋`X-RateLimit-Remaining: 0`；回 429；回 403 但 remaining 非 0；回 500；回 301 | `rate_limited`／`rate_limited`／`bad_response`／`bad_response`／`bad_response`（轉址不跟隨）；raw 的部分不受 api 的影響 |
| S-12 | **唯讀、無憑證**：成功路徑記下每個請求的方法與標頭 | 全是 `GET`；標頭鍵集合恰為 `{User-Agent, Accept}`（可再多 `Accept-Encoding` 之類 urllib 自動加的，測試只斷言**沒有** `Authorization`、`Cookie`、`X-` 開頭者）；`User-Agent` 以 `abf-station/` 開頭 |
| S-12b | **拒收壞參數（零請求）**：`repo` 為 `""`、`../x`、`a/b/c`、`./x`、`x/.`、`nf core/x`、`nf-core/ampliseq?x=1`、`nf-core/ampliseq#a`、換行、`%2e%2e/x`、`evil.com:80/x`、非字串；`revision` 為 `master`、`main`、`dev`、`3.0.0dev`、`2.18.0/../x`、39 位 hex、大寫 sha、`""`、`None`（有檔案部分時）、`2.18.0`（`parts` 只有 tags 時）；`parts` 為 `[]`、`["x"]`、重複、非 list、`"schema"`（字串） | 每筆 `refused`（`("refused", {"ok": False, "message": …})`），`OPEN` 零次呼叫 |
| S-13 | `revision` 為精確 tag `v3.0.0`、`3.0`、`1.2.3.4`、40 位小寫 sha | 全部放行並發出請求 |
| S-14 | 連線失敗：第一個請求丟 `OSError`／`URLError`／逾時；中途第二個請求才失敗 | `("error", {"ok": False, "error": "network", "message": …})`；`OPEN` 呼叫次數＝失敗那一次（不再試後面的部分）；`message` ≤ 300 字、含中英、**不含完整網址以外的內部字樣**、不含 `Traceback` |
| S-15 | 總預算：注入 `CLOCK`，第 N 個請求前已超過 45 秒 | 同 S-14（`network`），其後無請求 |
| S-16 | 回給平台的內容：成功結果的鍵集合；不含 GitHub 的標頭、錯誤頁內文 | 只有 `ok`、`repo`、`revision`、`parts`、`message`；`parts` 內只有 2 節規定的欄位 |
| S-17 | 原始碼掃描：`abf_station/*.py` 中 `urllib.request` 只出現在 `agent.py` 與 `pipeline_files.py`；`pipeline_files.py` 不含 `open(`、`.write(`、`os.remove`、`shutil`、`subprocess`、`socket`、`ctx.site`、`site.call`、`Authorization`、`sbatch`、`rm -rf` | 無命中 |
| S-18 | 沒有測試漏網：autouse 守門把預設 `OPEN` 換成會失敗的函式；另一條測試不注入就呼叫 `run_fetch` | 守門生效（該測試預期失敗被捕捉為 `AssertionError`，用 `pytest.raises`） |
| S-19 | 真的代理行程＋`FakePlatform`：`push("pipeline_files", {"repo":"../x","revision":"2.18.0","parts":["schema"]})`；`push("pipeline_files", {"repo":"nf-core/x","revision":"2.18.0","parts":["schema"],"extra":1})` | 兩筆都回 `refused`（第二筆是「不收這個參數」）；代理仍存活；沒有連網（參數在發請求前就被擋） |

### 平台：資料庫與排隊 `test_pipeline_files_queue.py`
| 編號 | 案例 | 預期 |
|---|---|---|
| Q-01 | 新建 `platform.db`：`jobs` 的 CHECK 清單 | 恰以 `'clean_work', 'pipeline_files'` 結尾，其餘順序同前；`'pipeline_file'`、`'pipeline_files '`、`'PIPELINE_FILES'`、`'tags'`、`''` 各 `IntegrityError` |
| Q-02 | 不帶 `confirmation_id` 插入 `pipeline_files` | 成功；`launch_nextflow`／`cancel_run`／`clean_work` 不帶仍 `IntegrityError`（第二條 CHECK 不動） |
| Q-03 | `jobs.CONFIRMED` | 仍剛好 `{"launch_nextflow":"launch","cancel_run":"cancel","clean_work":"clean_work"}` |
| Q-04 | 舊表（把 `, 'pipeline_files'` 從新 DDL 剪掉，仿 `test_cleanup_store.py:44`）含三筆舊資料與 `MAX(id)` | `connect_state` 後欄位逐欄不變、id 不變、AUTOINCREMENT 續接、能寫新種類、`rm`／`launch`／`""` 仍拒；只重建一次（再開一次不重建，用 `_migration_step` 計數） |
| Q-05 | 遷移中途失敗（`monkeypatch` `store._migration_step` 丟例外） | 舊表原樣、列數不變；再次 `connect_state` 成功遷移 |
| Q-06 | 更舊的表（連 `clean_work` 也沒有的，用 `test_cleanup_store.py` 的 `old_jobs()`） | 一次開啟直接升到最新（不多一次重建），新種類可寫 |
| Q-07 | `jobs.KINDS` | `pipeline_files` 恰一次、在 `clean_work` 之後；`KINDS` 中其餘七種的相對順序與現行相同；**測試不寫死總數** |
| Q-08 | `deadline_seconds("pipeline_files")` | 預設 90；`ABF_PLATFORM_DEADLINE_PIPELINE_FILES=7` → 7；`abc`／`0`／`-5` → 90；`TAGS_CACHE_SECONDS == 86400`、`TAGS_CACHE_FILE == "release-tags.json"` |
| Q-09 | `enqueue_pipeline_files` 成功 | 回工作 id；該列 `kind='pipeline_files'`、`state='queued'`、`confirmation_id IS NULL`、`deadline_at = now+90`；`args_json` 的鍵集合**剛好** `{repo, revision, parts}`（沒有 `ce`） |
| Q-10 | 壞輸入：repo／revision／parts 各種壞值（同 S-12b 的子集）、`parts` 有 `tags` 但 `revision` 非 None | `JobRefused`、資料庫沒有新列 |
| Q-11 | 選環境（alice 有 `ce-a`（代理離線）、`ce-b`（在線、available）、`ce-c`（在線、**creating**）、`ce-d`（disabled）；bob 有在線的 `ce-x`） | alice 沒給環境 → 選 `ce-b`（依名稱第一個通過者；`ce-c` 因名稱在後而不選，但把 `ce-b` 離線後改選 `ce-c`，證明不要求 available）；絕不選 `ce-x`；`caller_user_id=None` 時所有環境都算；全不通過 → `JobRefused`，訊息含 `no online agent` 與中文「沒有在線的代理」 |
| Q-12 | 給 `compute_env="ce-x"`（bob 的）而 alice 呼叫 | `JobRefused`，措辭與環境不存在相同（不洩漏有這個環境） |
| Q-13 | Google Batch 環境（`platform="googlebatch-platform"`）在線 | 可排；`list_site_files`／`fetch_run_records`／`read_task_log` 對它仍被擋（既有 `test_gcb_ce.py:726`、`test_gcb_launch.py:980` 不改且仍綠） |
| Q-14 | `claim` | 代理領到 `out["kind"] == "pipeline_files"`、**沒有** `confirmation`、**沒有** `run_token` 鍵；`remaining ≤ 90`；工作變 `claimed`；別的代理領不到 |
| Q-15 | `clean_result("pipeline_files", …)` 白名單表：正常結果原樣；多給 `headers`、`url`、`token`、`stdout`、`entries`、`private_key`、`text`（在頂層）→ 全不在輸出；`status` 不在清單 → 該部分 `bad_response`；`text` 1,000,001 字元 → `too_large` 且無 `text`；`data_b64` 含非 base64 字元或 2,800,001 字元 → `bad_response`；`name` 為 `../x.png` → 該部分 `bad_response`；`type` 為 `text/html` → 丟掉整個圖部分；`parts` 有 `evil` 鍵 → 丟掉 | 如左；也不落入最後的 `else`（不產生 `entries`） |
| Q-16 | `take_result` 走一遍：領取後回 `done`＋合格結果 → `result_json` 是清洗後的；重複回 → 409；別的代理回 → 403；逾期回 → `late`、工作 `expired` | 與其他種類一致 |
| Q-17 | `latest_pipeline_files`：多筆工作、相同 args 取最新；`parts` 不同視為不同；alice 看不到 bob 環境上的工作；沒有 → `None`；唯讀（呼叫前後資料庫位元組不變） | 如左 |
| Q-18 | 原始碼：`jobs.py`、`store.py` 新增行不含小寫 `station`（`test_scope.py` TC-061 已掃整個目錄；這裡只對新增行再釘一次，不得拆字湊） | 無命中 |

### 平台：動作層 `test_pipeline_files_action.py`（資料庫＋假時鐘＋`take_result` 代替代理答覆；比照 `test_cleanup_confirm.py` 的 `add_agent`／`add_ce` 假資料寫法）
| 編號 | 案例 | 預期 |
|---|---|---|
| A-01 | 簽章與型態 | 兩個都是**一般函式**（`inspect.iscoroutinefunction` 為 False）；第一個參數 `platform_path`；`pipeline_files` 的參數序 `(platform_path, pipeline, revision, *, parts, compute_env, caller, enqueue)`；`latest_release` 同理無 `revision`／`parts` |
| A-02 | `test_web_parity`：兩名稱在 `WEB_ONLY`，聯集檢查綠；`mcp_server.build_server` 的工具名單**不含**它們（MCP 工具數不變） | 如左 |
| A-03 | 壞輸入表（pipeline：`""`、`"../x"`、`"a/b/c"`、`None`、`123`；revision：`"master"`、`None`、`""`、`"3.0.0dev"`；parts：`["tags"]`、`[]`、`["x"]`、重複） | `state:"error"`、`error:"bad_input"`、`reason` 中英並陳；`jobs` 表零新列 |
| A-04 | 第一次呼叫（有 alice 的在線環境） | `state:"loading"`、`parts` 預設三項、四個部分全 `None`、`checked_at None`；資料庫恰一筆新工作，`args` 為 `{"repo":"nf-core/ampliseq","revision":"2.18.0","parts":["schema","schema_input","diagram"]}`；第二次呼叫仍 `loading` 且**仍只有一筆**（不重複排） |
| A-05 | 代理答覆（`take_result` 寫入含 ampliseq fixtures 的 `parts`）後再呼叫 | `state:"ready"`；`schema.groups == schema.parameter_groups(schema.load(fixture))`（16 組）；`schema.required_without_default == ["outdir"]`；`schema_input.columns == schema.samplesheet_columns(schema.load(fixture))`；`diagram` 同代理答覆；`checked_at == finished_at`；`json.dumps` 得過；鍵集合剛好是 6 節列的 |
| A-06 | 部分失敗：`schema_input` 部分是 `not_found` | `state:"ready"`；該部分 `{"status":"not_found","message":…}`；其他照常 |
| A-07 | `schema` 部分 `text` 是壞 JSON（`"not json"`） | 該部分 `{"status":"bad_json","message":…}`（不丟例外）；其他部分照常 |
| A-08 | 全部部分都失敗（皆 `not_found`；或 `rate_limited`、`too_large` 混合） | `state:"error"`、`error` 為共同狀態（混合時取依 `parts` 順序第一個）；各部分 `None` |
| A-09 | 代理回整體 `error`／`network` | `state:"error"`、`error:"network"`、`reason` 含「GitHub」與中文建議；60 秒內再問 → 仍是這個錯誤、**不排新工作**；`now` 推進 61 秒再問 → `loading` 且新增一筆工作 |
| A-10 | 代理對舊版回 `refused`（「不支援」） | `error:"refused"`；`reason` 提到更新 abf-station |
| A-11 | 工作 `queued` 超過 `deadline_at` 仍沒人領 | `error:"no_answer"`；之後（60 秒過）重新排 |
| A-12 | 沒有任何在線代理 | `state:"error"`、`error:"no_agent"`、資料庫零新列；`enqueue=False` 時（沒有工作）→ `loading`、零新列 |
| A-13 | 跨使用者：alice 的工作已完成；bob（自己有在線環境）以相同參數呼叫 | bob 看到 `loading`（排自己的工作），**看不到** alice 的結果；bob 沒有環境 → `no_agent`；`compute_env` 指向 alice 的環境 → 措辭同「找不到」 |
| A-14 | **不另存檔案快取**：工作完成後，`platform.db` 同資料夾沒有新增任何檔案（前後 `listdir` 比對，`release-tags.json` 除外且此測試不呼叫 `latest_release`）；相同參數再呼叫兩次 → 仍是同一筆工作、不新增；把工作列刪掉（模擬 7 天清除）再呼叫 → `loading` 且新增一筆 | 如左 |
| A-15 | `parts=("image",)`：代理答覆含 `image.data_b64` | `image == {"status":"ok","name":…,"type":"image/png","size":…,"data_b64":…}`；預設 `parts`（不含 image）時整個回傳**不含** `data_b64` 字樣 |
| A-16 | `latest_release("ampliseq", …)`，快取空、無工作 | `pipeline:"nf-core/ampliseq"`、`state:"loading"`、`revision None`、`source:"none"`；新增一筆工作，`args == {"repo":"nf-core/ampliseq","revision":None,"parts":["tags"]}` |
| A-17 | 代理答覆 tags 文字（含 `2.18.0`、`3.0.0`、`3.0.0dev`、`dev` 四種 ref）後再呼叫 | `state:"ready"`、`revision:"3.0.0"`、`source:"fetched"`、`checked_at` 為假時鐘；`platform.db` 旁的 `release-tags.json` 是合法 JSON，內容 `{"nf-core/ampliseq": {"revision":"3.0.0","checked_at":…}}`；`revision` 通過 `^(v?[0-9]+(\.[0-9]+){1,3}|[0-9a-f]{40})\Z` |
| A-18 | 再呼叫（3600 秒後）→ `source:"cache"`、**資料庫沒有新工作**；剛好 86400 秒後 → `loading` 並新增一筆工作（邊界＝過期） | 如左 |
| A-19 | 快取過期＋代理失敗：先有 `2.18.0` 的快取，過期後問、代理回 `network` | `state:"ready"`、`revision:"2.18.0"`、`source:"stale-cache"`、`why` 非空；快取檔內容未變；沒有舊快取時 → `state:"error"`、`error:"network"`、`revision None`、`source:"none"`；之後代理恢復，下一次（超過 60 秒）會再試（失敗沒被快取） |
| A-20 | tags 全不可用（只有 `dev`、`3.0.0dev`） | `error:"no_release"`、`why` 點名「沒有可用的 release tag」；沒寫快取 |
| A-21 | 所有回傳形狀 `json.dumps` 得過；`reason`／`why`／`message` 不含 `Traceback`、`sqlite`、`args_json`、`deadline_at`、`result_json`、`SELECT` | 如左 |
| A-22 | `actions/__init__.py` 新增行不含 `urllib`、`socket`、`subprocess`、`open(`（動作層不碰網路與檔案，快取檔由 `releases.lookup` 寫） | 無命中 |

**現在會紅**：S-01～S-19、Q-01～Q-18、A-01～A-22 全部。

### 會改斷言的既有測試（PRECHECK 第 3 項；只改所列斷言，其餘不動；逐條舊→新＋理由寫進 ledger）
通則：**只在清單尾端加 `"pipeline_files"`；斷言若是對整份清單／整個 tuple／整個 set 的逐字相等，就加這一項；若同時有 byte-channel-a 的 `put_upload`，兩者都在、`pipeline_files` 在最後。** 不把任何斷言改成「放寬到不檢查順序」。
| 檔案：行 | 現在的斷言 | 改成 | 理由 |
|---|---|---|---|
| `test_cloud_cost.py:746-747` | `store.py` 的 `CHECK (kind IN (…))` 解析結果逐字等於七個種類 | 清單尾端加 `"pipeline_files"` | CHECK 多一種 |
| `test_launch_platform.py:606` | `set(jobs.KINDS) == {…七個…}` | 集合加 `"pipeline_files"`，註解「release-lookup-job: plus pipeline_files」 | `KINDS` 多一種 |
| `test_resume_scope.py:70` | `jobs.KINDS == (…七個，含順序…)` | tuple 尾端加 `"pipeline_files"` | 同上；順序＝加在最後 |
| `test_cleanup_confirm.py:342`（TC-033） | 同上；測試名「kinds are seven」 | tuple 尾端加；測試名與註解的「seven」改成「the seven before pipeline_files, then pipeline_files last」並仍斷言 `CONFIRMED` 三項不變（:343） | 同上 |
| `test_station_platform.py:319-330` | 插入七種的迴圈與 `declared` 集合逐字等於七個 | 迴圈加 `("pipeline_files", None)`；集合加 `"pipeline_files"` | CHECK 多一種；該種不需確認 |
| `test_cleanup_store.py:173-174`（TC-003） | `declared_kinds(check_of(con, "jobs")) ==` 七個 | 尾端加 `"pipeline_files"`；**同檔 :179 的「四種不需確認」迴圈與 `n + 4` 不改**（仍是那四種，不影響） | CHECK 多一種 |
| `test_cleanup_store.py:44-45`（`old_jobs()`） | 把新 DDL 的 `, 'clean_work'` 剪掉當「舊表」 | 先剪 `, 'pipeline_files'` 再剪 `, 'clean_work'`（`read_task_log=False` 時再剪 `, 'read_task_log'`） | 否則「舊表」會夾著不該有的 `pipeline_files`，測不準「連 clean_work 都沒有」的升級 |
| `test_cleanup_store.py:137`（`KINDS` 探測表） | 探測哪些字串被 CHECK 接受 | **不改**（遷移前後結構比對，新舊兩邊同步變）；若 executor 想加 `"pipeline_files"` 到探測表，可加並在 ledger 說明 | 非必要 |
| `test_station_clean.py:288-292`（TC-028，cloud-cleanup-c 新增） | `JOB_KINDS[:6]` 與 `JOB_KINDS[6:] == ("clean_work",)`；`ARG_KEYS` 去掉 `clean_work` 後逐字等於舊六個 | `JOB_KINDS[:6]` 不改；`[6:]` 改成 `JOB_KINDS[6] == "clean_work"`；`ARG_KEYS` 排除 `{"clean_work", "pipeline_files"}` 後等於舊六個；測試名中的「six」不動 | 站台種類多一種（本計畫 `after: cloud-cleanup-c`，所以此檔一定已在 base） |
| `test_web_parity.py:23-30`（`WEB_ONLY`） | 聯集必須等於 `actions` 的公開名稱（`test_tch16a`） | `WEB_ONLY` 加 `"pipeline_files"`、`"latest_release"` 兩列（說明如作法 7）；`test_tcs07`、`OWED` 不動 | 動作層多兩個公開名稱，它們有網頁用途但目前沒有 MCP 工具 |

**確認沒有牽動（已查，不改）**：`test_actions_layer.py:27,35,153,221,236`、`test_chat_tools.py:15`、`test_guidance.py:26`、`test_estimate_su.py:297`、`test_gcb_ce.py:726,776`、`test_gcb_launch.py:980,1069`、`test_http_site_samplesheet.py:562`、`test_human_channel.py:159`、`test_keep_submissions.py:705,773-774`（那是 confirmations 的 CHECK，不是 jobs 的）、`test_launch_e2e.py:185`、`test_launch_platform.py:122`（六種的子集插入）、`test_run_diag_tools.py:294,466`、`test_cloud_cost.py:748`（confirmations 的 CHECK）——MCP 工具名單與工具數都不變、`DEADLINE_SECONDS`／`KINDS` 只有 `in` 或子集式用法者不受影響。`docs/PLATFORM.md:6,357` 的「九個唯讀工具／十四個工具」句子不動（沒有加工具）。

## 完成標準（done when）
- 自動：S-01～S-19、Q-01～Q-18、A-01～A-22 全綠；整個 `bash tests/run_all.sh`（WSL）綠，含 `tests/platform_test.sh`、`tests/no_second_run_state_test.sh`（`LAUNCH_ALLOW` 仍一筆）、`tests/credentials_stay_in_settings_test.sh`、`tests/platform_storage_doc_test.sh`（新增那一列要過 TC-004、TC-009）、`test_scope.py`（TC-061、TC-070、TC-071、TC-072）；MCP 工具數仍是現行數字（不寫死，斷言測試沒被改）；`git diff --name-only` 只有「範圍：檔案」所列；上表以外的既有測試零改動（依 dev-plans 通例，`git diff --stat` 貼進 ledger，verifier 核對並重跑）；**測試全程不連真網路**（S-18 守門）。
- 已知環境紅（通例）：`test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 在 onboarding-test-pinned-base 合併前只剩這一條紅視同綠。
- 手動（寫進 `docs/TESTING.md` 新增一節「release-lookup-job：真的連 GitHub 讀一次」，**executor 不執行**——對網際網路的唯讀請求不在 executor 的權限內，由 developer-agent／維護者做；`CLAUDE.md`「Never run」只禁站台與 HPC，但本計畫保守留給人）：
  1. 在有網路的機器啟動平台與一個代理（`docs/PLATFORM.md` 第 1、6 節），建一個該代理的環境（不必預檢）。
  2. 用一行 Python 呼叫 `actions.pipeline_files(<platform.db 路徑>, "nf-core/ampliseq", "2.18.0")`，每 5 秒再呼叫，直到不是 `loading`（最多約 1 分鐘，代理每 25 秒輪詢一次）。**預期**：`state "ready"`；`schema.groups` 16 組、參數共 170 個（schema-reader T1、T2 的值）；`schema.required_without_default == ["outdir"]`；`schema_input.columns` 首欄 `sampleID`（以 ampliseq 2.18.0 實檔為準）；`diagram.name == "ampliseq_workflow.png"`、`size == 753702`。再以 `parts=("image",)` 呼叫，`len(base64.b64decode(data_b64)) == 753702` 且開頭是 PNG 魔術字。
  3. `actions.latest_release(<路徑>, "nf-core/ampliseq")` 同樣輪詢；**預期**：最新的純數字 tag（2026-10-25 實測是 `3.0.0`；以當時 GitHub 為準）、`source "fetched"`，`release-tags.json` 出現在 `platform.db` 旁；立刻再呼叫 → `source "cache"` 且資料庫沒有新工作。
  4. 拔掉網路（或把代理的網路關掉）後呼叫一個沒問過的 `("nf-core/rnaseq","3.27.0")`：**預期** 約 1 分內 `state "error"`、`error "network"`、`reason` 白話。
  5. 驗收結果（輸出貼進 ledger）。
- 文件：作法 8 的四處 `docs/PLATFORM.md` 更新＋`docs/TESTING.md` 一節。

## 環境事實
（行號為 worktree `feat/cloud-cleanup-c` @ ab4d4e8；動手前以函式名重新 grep。我只讀碼、沒有改任何 repo 檔。）
- **站台代理現況**：`abf_station/handlers.py:17` `JOB_KINDS` 七種（`preflight`、`list_site_files`、`launch_nextflow`、`cancel_run`、`fetch_run_records`、`read_task_log`、`clean_work`）、:18-20 `ARG_KEYS`、:34 `handle()`（:41 未知種類的拒絕訊息、:44 多餘參數的拒絕、:49-51 分派）；`handle` 的 `ctx` 是 `agent.Context`（`agent.py:195`，有 `site`、`settings_file`、`platform_url`、`agent_name`）。代理已連網的檔案只有 `agent.py:12-14`（連平台）與 `cli.py:13`（解析網址）；`abf_station/` 內沒有任何 `github`、`ls-remote` 字樣（grep 過）。代理一次只做一件工作（`agent.py` 的主迴圈），輪詢間隔預設 25 秒（`common.py:97`）。
- **平台排隊現況**：`jobs.py:26-27` `DEADLINE_SECONDS`、`:42` `CONFIRMED`、`:72` `_target`（:87 Google Batch 只放行四種、:101 只對 `list_site_files`／`launch_nextflow` 要求 available）、`:108` `_insert_job`、`:155` `_enqueue`、`:303` `latest_listing`、`:626` `claim`、`:683` `clean_result`（:722 的最後 `else` 是 `list_site_files` 的形狀，新種類若不加分支會被套到它）、`:769` `take_result`。`jobs` 表 `compute_env`、`agent` 兩欄 NOT NULL（`store.py:238-239`），所以每個工作都必須指向一個環境與一個代理——這就是 `pick_environment` 存在的原因。上一次加種類（`clean_work`，cloud-cleanup-a）做過同樣的遷移：`store.py:412` `_migrate_jobs_kinds`、`connect_state` 的呼叫順序見 :654-669。
- **平台不連網**：`test_scope.py:187` TC-061 禁 `urllib.request`、`import socket`、`socket.`、`ssh`、`sbatch`、字面 `station` 等（掃 `abf_platform/` 全部 .py）；:99 TC-071 禁 `subprocess`、`threading`、`while True`。`jobs.py:37` 為此把一個含 station 的句子拆字拼接（`NO_AGENT_KNOWN`）——本片用不含該字的句子，不必拆字。
- **動作層慣例**：`list_site_files`（:293）與 `read_task_log`（:390）是 `async`、會 `await jobs.wait_for_result`（最久等到期限）；`run_outputs`（:334）是同步、不等、回 `loading|ready|error`，註解寫明原因（頁面每 15 秒重整）。web 路由是 async 的（`web.py:443,600` `await actions.…`），但只有後一種模式適合引導式送出頁（冷呼叫要等代理輪詢最多約 25 秒）。
- **已建好的純模組（在 base 裡）**：`schema.py`：`load`（:13，`MAX_CHARS = 2000000`）、`parameter_groups`（:77）、`required_without_default`（:110）、`samplesheet_columns`（:124）；`releases.py`：`repo_of`（:16）、`usable`（:30）、`pick_latest`（:39）、`parse_ls_remote`（:57）、`lookup`（:110，`ttl=86400.0`、失敗不寫快取、壞快取當沒有）。fixtures：`platform/tests/fixtures/schema/ampliseq-2.18.0.nextflow_schema.json`（95,707 位元組）、`old-definitions.json`；`tests/fixtures/schema_input/{ampliseq-2.18.0,bacass-2.6.1,mag-5.5.0,rnaseq-3.27.0,taxprofiler-2.0.1}.json`。
- **parity 守門**：`test_web_parity.py` 的 `test_tch16a_h16b_union_is_the_public_names` 要求 `WEB_ROUTES ∪ WEB_ONLY ∪ OWED ∪ INTERNAL` **恰等於** `actions` 的公開名稱（非底線開頭、非模組）；`WEB_ROUTES` 內的名字必須有同名 MCP 工具（`test_tch16c`）——所以沒有 MCP 工具的新函式只能進 `WEB_ONLY`。
- **文件守門**：`tests/platform_storage_doc_test.sh`（:68-96）檢查儲存表每列「Where」裡的反引號名字出現在 `platform/` 程式碼、每個「N hours/days」對得上 `platform/abf_platform/*.py` 頂層一個 `NAME = 數字(*數字)` 常數（正規式在 :95-101 附近）；`jobs.py:25` 的 `PRUNE_AFTER_SECONDS = 7 * 86400` 是「Job rows」那列的來源。
- **我 2026-10-25 實測 GitHub（匿名，我的機器，唯讀）**：
  - `api.github.com` 回 `X-RateLimit-Limit: 60`（每小時 60 次，同 release-tag-pick 的環境事實）。
  - `GET https://github.com/nf-core/rnaseq.git/info/refs?service=git-upload-pack`：200、`Content-Type: application/x-git-upload-pack-advertisement`、79,508 位元組、以 `001e# service=git-upload-pack\n0000` 開頭、第一個 ref 行（`HEAD`）NUL 之後是能力清單；內含 46 筆 `refs/tags/…`，另有 1127 行 `refs/pull/…`（所以必須在代理端過濾，不能整份丟給平台）。不帶 `Git-Protocol` 標頭時回的是 v0 公告（有 ref 列表）。
  - `GET …/repos/nf-core/ampliseq/contents/docs/images?ref=2.18.0`：含 `ampliseq_workflow.png`（753,702）、`ampliseq_workflow.svg`（348,755）、`ampliseq_workflow_multiplesequencingruns.png`（189,695）、`ampliseq_workflow_multiplesequencingruns.svg`（228,700）。
  - `raw.githubusercontent.com/nf-core/ampliseq/2.18.0/assets/schema_input.json` 200、4,607 位元組；不存在的路徑 404。
  - `GET …/repos/nf-core/{ampliseq,rnaseq}/tags?per_page=100` 分別 33、46 筆，最新在最前（本片不用這個端點，列出來是為了說明為什麼不需要分頁）。
- **查不到、不要猜**：GitHub 對匿名 `info/refs` 有沒有獨立的速率限制（文件沒寫）；萬一被限，代理回 `rate_limited`（429）或 `bad_response`，平台顯示錯誤並在 60 秒後重試，不會卡死。

## 不做
- 不做 nf-core **全部管線搜尋**（guided-launch-2 的 `search_pipelines`，來源 `nf-co.re/pipelines.json`）：`nf-co.re` 不在這次放行的三個主機裡；要做必須另問維護者放寬（列為給維護者的問題）。
- 不加 MCP 工具、不加網頁路由、不改 `guidance.py`／`chat_tools.py`／`web*.py`（作法 7）；不接線 `request_launch`／`launch_prefill`／啟動表單的版本預填（release-tag-pick 裁決 2：站台已安裝的版本優先，「最新版」只當提示——接線任務才決定）。
- 不讀 README 或其他檔案（只有這四類公開檔）；不讀私有 repo、不帶任何憑證；不跟隨轉址；不寫任何檔案到代理那台機器；不快取檔案內容到平台（作法 5-7、裁決 2）。
- 不加資料表、不加欄位（只放寬 `jobs` 的 CHECK，有 migration）；不改 `confirmations`；不新增確認種類。
- 不改 `schema.py`、`releases.py`；不在代理裡解析 JSON（解析只有 `schema.py` 一處）；不推論樣本欄角色（那是 `scripts/utils/schema_roles.py` 的事，前端自己 import）。
- 不新增設定鍵（除了測試用的 `ABF_PLATFORM_DEADLINE_PIPELINE_FILES`）；不加背景執行緒、迴圈、重試（重試是「60 秒後使用者重新整理頁面時再排一次」，不是程式裡的迴圈）。

## 裁決（2026-10-25，developer-agent）
1. **唯讀、不需確認**：`CONFIRMED`（`jobs.py:42`）與 `_JOBS_TABLE` 第二條 CHECK（`store.py:252`）都只列寫入類的三種；`fetch_run_records`、`read_task_log` 同為唯讀且不需確認（`jobs.py:182,204`）。請求內容只有公開 repo 名與版本，不含任何使用者資料，所以不是「送出使用者內容」類。放寬由維護者 10-25 核可，範圍限這四類公開檔。
2. **快取分兩種，只有一種是檔案**：repo `CLAUDE.md` 說 schema／README／圖「never cached here」，所以平台**不另存**檔案內容的快取檔；釘死版本的內容靠「已完成的工作列」在 7 天保留期內重用（那是傳輸紀錄，工作列清掉就再抓）。而「最新版」會變，release-tag-pick 的設計就是 24 小時快取，所以 `latest_release` 用 `releases.lookup(cache_path=…)` 寫 `release-tags.json`（檔案放在 `platform.db` 旁、不是資料表，所以**不需要 store.py 為它做 migration**；store.py 的 migration 只為了放寬 `jobs` 的 CHECK）。若維護者認為「7 天內的工作列重用」也算快取，要改成每次都排新工作——代價是每次開頁面最久等 25 秒；列為給維護者的問題，預設維持本計畫。
3. **不加 MCP 工具**（作法 7）：前端要的是動作層名字；工具數／名單牽動十幾處釘死斷言，沒有人需要。`WEB_ONLY` 登記是合法位置。
4. **同步不等待而非 async 等待**：沿用 `run_outputs` 的模式（:334），因為代理輪詢間隔 25 秒（`common.py:97`），async 等待會讓引導式送出頁每次載入卡住最久約半分鐘。
5. **tag 清單走 git 智慧型 HTTP 而非 GitHub API**：不吃每小時 60 次匿名額度（同一台機器／同一個公司出口可能被別人用掉）；資料與 `git ls-remote` 同源，正好餵 `releases.parse_ls_remote`。代價是代理自己解一小段 pkt-line（約 15 行），由 S-07、S-08 釘住。目錄清單仍必須用 API（raw 不能列目錄），額度不足時只讓 `diagram` 部分顯示 `rate_limited`，不影響 schema 與樣本表欄位。
6. **環境選擇**：沒指定時用呼叫者自己的第一個在線、非停用的環境，不要求 `available`（這個工作不碰站台）；Google Batch 環境放行。這不是安全決定，只是「找哪個代理去做」，所以不暴露成使用者要填的欄位（`compute_env` 是選用參數，給進階呼叫者）。
7. **站台自己補「單點段」檢查**：`releases.repo_of` 放行 `./x`（只擋 `..`），本片不改該模組（A 級純模組已合併），代理端與 `enqueue_pipeline_files` 各加一條「每段不得全由點組成」；若維護者想把它補進 `repo_of`，另開小任務。
8. **版本號不動**：不改 `abf_station.__version__`。舊版代理遇到新種類會回「不支援」，動作層把它轉成「請更新 abf-station」的白話（A-10）。

## 裁決二（2026-10-25，developer-agent 回應規劃者的五個問題）
1. **nf-core 搜尋一起做**：放行主機加第 4 個 `nf-co.re`（只讀 `https://nf-co.re/pipelines.json`，上限 4 MB），`parts` 多一個 `catalogue`；動作層加 `actions.nfcore_catalogue(platform_path, *, compute_env=None, caller=None, enqueue=True)`，回傳形狀比照 `pipeline_files`（state loading|ready|error），ready 時帶 `pipelines: [{name, description, latest}]`，同樣登記在 `WEB_ONLY`。理由：維護者核可的就是讓引導送出讀得到公開管線資訊，搜尋是 guided-launch-2 的一部分；仍是唯讀、公開、無憑證。
2. 已完成的工作列 7 天內重用**不算**違反「never cached here」：讀的是釘死 revision 的檔，內容不會變；`nfcore_catalogue` 與 `latest_release` 照 `releases.lookup` 24 小時。
3. 排程順序：`after: cloud-cleanup-c,byte-channel-a`（三者都改 handlers／store／jobs）；種類接在最後、斷言相對順序。
4. `repo_of` 放行 `./x` 另開 A 級小任務 `repo-of-dot-segment`；本片照計畫在代理端與 enqueue 端各補檢查。
5. 匿名 info/refs 被限速時回 `rate_limited`，頁面 60 秒後重試：接受。

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
