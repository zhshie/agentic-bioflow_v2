---
id: nfcore-catalogue
title: 站台代理的 pipeline_files 工作多讀一種公開檔：nf-co.re/pipelines.json（全部 nf-core 管線清單）；動作層新增 nfcore_catalogue 給引導式送出的「搜尋全部 nf-core 管線」
tier: B
kinds: backend
lane: L-release
after: release-lookup-job
base: origin/v3 @ ad1ee18（Merge PR #236 release-lookup-job；行號都是這個版本，動手前以函式名重新 grep）
source: 維護者 2026-10-26「都ok」（答「要不要放行讀 nf-core 官網的公開清單 nf-co.re/pipelines.json」）；release-lookup-job 裁決二第 1 條（當時撤回、現在放行）、裁決三第 7–8 條（快取邊界、部分失敗重用）、裁決四第 11 條（種類接在最後、不寫死總數）；developer-agent 2026-10-26 讀碼查證＋實抓一次 nf-co.re/pipelines.json
---

# nfcore-catalogue

> **給前端 session（guided-launch-2）的呼叫名稱，先看這裡：**
> - `actions.nfcore_catalogue(platform_path, *, compute_env=None, caller=None, enqueue=True)` → dict，`state: loading|ready|error`；`ready` 時 `pipelines` 是**全部** nf-core 管線（今天 159 條）依名稱排序的清單，每條 `{"name", "repo", "description", "archived", "latest"}`。**搜尋過濾在網頁做**（名稱或描述含關鍵字、不分大小寫、最多 30 筆——guided-launch-2 計畫第 47 行的規則），動作層不收 `query`（裁決 6）。
> - 同步、不等待（比照 `pipeline_files`／`latest_release`，`actions/__init__.py:548,596`）；`loading` 時頁面每 15 秒重整再問一次。**不加 MCP 工具、不加網頁路由**，登記在 `test_web_parity.py` 的 `WEB_ONLY`。
> - 工作種類**沒有新增**：仍是 `pipeline_files`，多一個 part `catalogue`（裁決 1）。

## 目標
站台代理已合併的唯讀工作 `pipeline_files`（#236）多讀**第五種公開檔**：`https://nf-co.re/pipelines.json`（nf-core 官網公開的全部管線清單，不需帳號、GET、不跟隨轉址），把每條管線的名稱、描述、是否封存、release tag 名稱整理成小清單交回平台；平台（自己不連網，`test_scope.py:187` TC-061）排工作、收結果、用 `releases.pick_latest`（`releases.py:39`）算出每條的最新可啟動版本，並以同一筆已完成工作當 24 小時的答案。對使用者的意義：引導式送出的「新管線」步驟能真的**搜尋全部 nf-core 管線**（guided-launch-1 把它標成「搜尋全部 nf-core 之後開放」，`guided-launch-1.md:51`），不必自己記管線名字，選到的管線直接帶出 `nf-core/<name>` 與最新版本號給下一步 `pipeline_files`／`latest_release`。

## 維護者原話（verifier 出題用）
- 「都ok」（2026-10-26，答「要不要放行讀 nf-core 官網的公開清單 nf-co.re/pipelines.json」）→ 放寬的範圍就是**這一個網址、這一個主機**，不多不少：CS-02（第四主機只准 `nf-co.re`，且只有這一個路徑會被組出來）、CS-10（仍是唯讀、GET、無憑證、不跟轉址）、CS-11（`catalogue` 不能與其他 part 同一筆、也不能帶 repo／revision——它不是某條管線的檔）。
- 「好，放寬」（2026-10-25，release-lookup-job 的核可：站台代理新增唯讀工作讀公開檔）→ 本片是同一條放寬的延伸，沿用同一個工作種類與同一套守門：CS-01（`JOB_KINDS` 不變、`ARG_KEYS["pipeline_files"]` 不變）、CQ-01（`jobs` 表 CHECK 不變、**沒有 migration**）。
- 「Pin an exact pipeline revision, never a branch … never cached here」（repo `CLAUDE.md` Working conventions）→ 清單不是某個 revision 的檔，而是「現在有哪些管線、最新到哪一版」這種會變的答案，和 `latest_release` 同類，所以**只重用 24 小時**（CA-08、CA-09）；平台不另存檔案（CA-13）。
- 憲法原則 2＋TC-061：平台不連網 → CA-14、CQ-08（新增程式不得出現 `urllib.request`、`socket`、字面 `station`；連網只在 `abf_station/pipeline_files.py`）。
- 「每個寫入要本人答應」（憲法 6）→ 本片**唯讀、不需確認**：`jobs.CONFIRMED`（`jobs.py:58`）仍剛好三項、`store.py:254` 的 CHECK 不動（CQ-02）。

## 範圍：檔案（只准改這些）
新增：
- `platform/tests/test_nfcore_catalogue.py`（新；檔首 `# Nothing existing: …` ≥15 字；三節：站台、排隊／清洗、動作層；autouse fixture 把 `pipeline_files.OPEN` 換成「一呼叫就失敗」的函式，比照 `test_station_pipeline_files.py:69-73`）
- `platform/tests/fixtures/catalogue/pipelines-small.json`（新；從真檔剪下 6 條、保留真實鍵名與多餘鍵，見環境事實「fixture 內容」）
- `specs/nfcore-catalogue/ledger.md`

修改（只限所列之處）：
- `platform/abf_station/pipeline_files.py`：`PARTS`（:27）尾端加 `"catalogue"`；`HOSTS`（:28）尾端加 `"nf-co.re"`；新常數 `CATALOGUE_URL`、`CATALOGUE_LIMIT = 8000000`、`CATALOGUE_ENTRIES_LIMIT = 1000`、`_PIPELINE_NAME`；`_problem`（:99-121）改成先驗 `parts`、再依「只有 `catalogue`」／「只有 `tags`」／其餘三種情形驗 `repo`／`revision`；新函式 `_catalogue(fetcher)`、`_catalogue_entries(data)`；`run_fetch`（:325-359）的分派多一個 `elif name == "catalogue"` 分支，且 `repo`／`revision` 為 `None` 時結果照樣帶 `"repo": None, "revision": None`；模組說明（:1,5,7）與 `allowed` 的說明（:57）由「四種／三個主機」改為「五種／四個主機」。不動 `OPEN`、`_fetch_once`、`_Fetcher`、`_judge`、`_text_part`、圖與 tag 的函式。
- `platform/abf_station/handlers.py`：只改 :7 的說明句（「four kinds」→「five kinds, the fifth being nf-core's own list of pipelines」）。`JOB_KINDS`、`ARG_KEYS`、`handle` 不動。
- `platform/abf_platform/jobs.py`：`PF_PARTS`（:47）尾端加 `"catalogue"`；新常數 `CATALOGUE_CACHE_SECONDS = 24 * 3600`、`PF_PIPELINE_NAME`、`PF_TAG_NAME`、`PF_CATALOGUE_ENTRIES = 1000`、`PF_CATALOGUE_TAGS = 500`、`PF_DESCRIPTION_LIMIT = 400`（全部放頂層、`NAME = 數字(*數字)` 形）；`pf_arguments`（:251-272）加「只有 `catalogue` 時 `repo` 與 `revision` 都必須是 `None`；`catalogue` 與其他 part 同列 → 拒絕」；`_clean_pf_part`（:841-872）加 `catalogue` 分支（白名單見作法 4）；模組說明 :4 補一句。`DEADLINE_SECONDS`、`KINDS`、`CONFIRMED`、`_target`、`pick_environment`、`enqueue_pipeline_files`、`latest_pipeline_files`、`clean_result` 本體不動（`clean_result` :892-900 已依 `PF_PARTS` 迴圈，加常數即涵蓋）。
- `platform/abf_platform/store.py`：**不動**（沒有新種類、沒有新欄、沒有 migration——見裁決 1）。
- `platform/abf_platform/actions/__init__.py`：在 `# ---- release-lookup-job: end`（:659）之後新開一段 `# ---- nfcore-catalogue: begin` … `# ---- nfcore-catalogue: end`，內含公開函式 `nfcore_catalogue` 與底線開頭的輔助（`_CAT_KEYS`、`_CAT_REASONS`、`_cat_blank`、`_cat_error`、`_cat_entries`）。**公開名稱只准這一個**，否則 `test_web_parity.py` 聯集檢查會紅。可呼叫既有私有輔助 `_pf_job_state`（:498）、`_pf_code`（:535）、`_pf_queue`（:539）、`_caller_id`（:746）。
- 允許更新的既有測試（只改所列斷言，逐條「舊→新＋理由」寫進 ledger）：`platform/tests/test_station_pipeline_files.py`、`platform/tests/test_pipeline_files_queue.py`、`platform/tests/test_pipeline_files_action.py`、`platform/tests/test_web_parity.py`；清單見「會改斷言的既有測試」。
- `docs/PLATFORM.md`（三處，作法 7）、`docs/TESTING.md`（新增一節手動步驟，完成標準）。

**不准動**：`platform/abf_platform/{store,schema,releases,mcp_server,guidance,chat_tools,web,web_board,web_launch,cli,confirm,compute_envs,receiver}.py`、`abf_station/{agent,launch,cancel,clean,fetch,readlog,site,rules,cli,put_upload,common}.py`、`abf_launch/*`、`pyproject.toml`（fixture 在 tests 底下，不入套件；`platform/tests/fixtures/schema/` 先例）、`tests/*.sh`、`platform/tests/station_harness.py`、`test_actions_layer.py`、`test_chat_tools.py`、`test_guidance.py`、`test_pat.py`、`test_oauth_mcp.py`、`test_byte_channel_{a,b}.py`、`test_cleanup_confirm.py`、`test_cleanup_store.py`、`test_cloud_cost.py`、`test_launch_platform.py`、`test_resume_scope.py`、`test_station_clean.py`、`test_station_platform.py`、`test_http_site_samplesheet.py`（這些釘的是工作種類清單與工具數，本片兩者都不變）。

## 作法（決定）
### 1. 工作的形狀：`pipeline_files` 多一個 part，不加種類（逐字）
- `PARTS`／`PF_PARTS` 變成 `("schema", "schema_input", "diagram", "image", "tags", "catalogue")`——`catalogue` **接在最後**（裁決四第 11 條的通則）。
- `catalogue` **只能單獨出現**：`parts == ["catalogue"]` 時 `repo` 與 `revision` **都必須是 `None`**；`catalogue` 與任何其他 part 同列 → 拒絕（它不屬於任何一條管線）。其餘規則不變（`tags` 單獨時 `revision` 為 `None`；檔案類 part 要 `repo` owner/name 與精確版本）。
- 工作 `args` 恰為 `{"repo": None, "revision": None, "parts": ["catalogue"]}`；`ARGS`／`ARG_KEYS` 不變，`handlers.handle` 的多餘鍵檢查（:48-50）照常。
- `jobs.latest_pipeline_files(state_path, None, None, ["catalogue"], caller_id)` 用既有比對（`args.get("repo") == repo` 等，:468-472）即可找到這種工作，**不改該函式**。
- 排隊仍走 `enqueue_pipeline_files`（唯一入口，`jobs.py:177-178`）；`pick_environment`（:275）照常挑呼叫者自己在線的環境（Google Batch 已放行，:103）；`deadline_seconds("pipeline_files")` 仍 90。

### 2. 站台代理怎麼抓（`abf_station/pipeline_files.py`）
- 主機白名單加第 4 個：`HOSTS = ("github.com", "raw.githubusercontent.com", "api.github.com", "nf-co.re")`；`allowed()` 邏輯不變（https、hostname 逐字相等、無帳密、無埠、不跟隨轉址——`_NoRedirect` :51-53）。
- 唯一網址 `CATALOGUE_URL = "https://nf-co.re/pipelines.json"`（常數，不由參數組成——沒有參數可組）；`Accept: application/json`；其餘標頭、逾時（10 秒）、總預算（45 秒）、`OPEN` 注入點全部沿用（:29-30,:136-138）。
- **上限 `CATALOGUE_LIMIT = 8_000_000` 位元組**（`read(limit + 1)` 判斷；超過 → `too_large`，一個位元組都不交回）。為什麼不是 4 MB：真檔今天 3,138,916 位元組（環境事實），4 MB 只剩 27% 餘裕、每多一條管線約 +19.7 KB，約 200 條就會爆；8 MB 可容約 400 條，仍遠小於 `urllib` 讀進記憶體的合理範圍。
- 讀到 200 後：`json.loads(body.decode("utf-8"))`；不是 UTF-8、不是合法 JSON、頂層不是 dict、`remote_workflows` 不是 list → `bad_response`（與目錄清單 `_listing` :212-217 同一種處理；**站台不新增狀態字樣**，`PF_STATUSES` 不變）。
- **整理（`_catalogue_entries(data)`，確定性）**：逐條 `remote_workflows[i]`，取：
  - `name`：必須是 str 且符合 `_PIPELINE_NAME = ^[A-Za-z0-9][A-Za-z0-9_.-]{0,60}\Z`，不符**跳過該條**（不整份失敗）；
  - `description`：str 原樣（最多 400 字元，多的切掉）；`None`／缺少／非 str → `""`；
  - `archived`：`bool`；缺少或非 bool → `False`；
  - `tags`：`releases[]` 內每筆 dict 的 `tag_name`（str 且符合既有 `_TAG_NAME` :38），順序照原檔（原檔新的在前）；`releases` 缺少或非 list → `[]`。**代理不挑最新版**，交平台用 `releases.pick_latest`。
  - 依 `name` 排序；同名只留第一條。
- 整理後 0 條 → `bad_response`（nf-core 的清單不會是空的）；超過 `CATALOGUE_ENTRIES_LIMIT`（1000）條 → `too_large`。
- part 結果：`{"status": "ok", "pipelines": [{"name": "ampliseq", "description": "Amplicon sequencing analysis workflow using DADA2 and QIIME2", "archived": false, "tags": ["3.0.0", "2.18.0", "2.17.0", …, "dev"]}, …]}`；失敗 `{"status": "not_found" | "too_large" | "bad_response" | "rate_limited", "message": "<_words()>"}`（`_judge` :158-166 的既有對照：404→not_found、429 或 403+remaining 0→rate_limited、其他含 3xx→bad_response）。連線層失敗照舊整個工作 `("error", {"ok": False, "error": "network", …})`（`_network_result` :92-94，**文字不改**，平台不會把它顯示給使用者，見裁決 9）。
- `run_fetch` 回 `("done", {"ok": True, "repo": None, "revision": None, "parts": {"catalogue": …}, "message": "read 1 part(s) from GitHub (已從 GitHub 讀取)"})`——`message` 沿用既有字串（不顯示給人；不為它多開分支）。
- 解析 JSON 來整理清單是允許的：release-lookup-job 裁決四第 14 條已准代理解析目錄清單 JSON；本片同類。代理仍不解析 schema／schema_input（TC-046 不變）。

### 3. 平台：參數再驗一次（`jobs.pf_arguments`）
- 先驗 `parts`（既有規則：非空、不重複、都在 `PF_PARTS`），排成標準順序 `ordered`。
- `ordered == ["catalogue"]`：`repo is not None or revision is not None` → `JobRefused("the pipeline list takes no repository and no revision (查全部管線清單不給 repo 與版本)")`；回 `(None, None, ["catalogue"])`。
- `"catalogue" in ordered and len(ordered) > 1` → `JobRefused("the pipeline list is read on its own (全部管線清單要單獨查)")`。
- 其餘路徑逐字不變（`tags` 單獨→revision None；檔案類→repo owner/name＋精確版本）。
- 訊息不得含字面 `station`（TC-091 掃整檔）。

### 4. 平台：清洗白名單（`jobs._clean_pf_part("catalogue", part)`）
- `status` 不在 `PF_STATUSES` → `{"status": "bad_response"}`（既有）；非 `ok` → 只留 `status`＋`message`（≤300）。
- `ok`：`pipelines` 必須是 list，否則 `{"status": "bad_response"}`；最多取前 `PF_CATALOGUE_ENTRIES`（1000）條；每條必須是 dict 且 `name` 為 str 且符合 `PF_PIPELINE_NAME`（與站台同一個正規式），否則**丟掉該條**；`description` 非 str → `""`，超過 `PF_DESCRIPTION_LIMIT`（400）切掉；`archived` 非 bool → `False`；`tags` 非 list → `[]`，只留 str 且符合 `PF_TAG_NAME`（`^[A-Za-z0-9][A-Za-z0-9._+-]{0,200}\Z`）者、最多 `PF_CATALOGUE_TAGS`（500）個；每條**只留這四個鍵**（`html_url`、`stargazers_count`、`topics`……全部丟掉）。清洗後 0 條 → `{"status": "bad_response"}`。
- 不新增頂層鍵：`clean_result` 的 `repo`（非 str 就不帶）、`revision`（None 照帶）邏輯不動。

### 5. 動作層：`nfcore_catalogue`（`actions/__init__.py`，新 marker 區塊內）
一般函式（非 async）、永遠回 dict、不丟例外、不 `wait_for_result`。簽章固定：`nfcore_catalogue(platform_path, *, compute_env=None, caller=None, enqueue=True)`。狀態機：
1. `answer = _cat_blank()`（`loading`，各鍵齊全）。`caller_id = _caller_id(caller)`；`now = status.now()`。
2. `job = jobs.latest_pipeline_files(platform_path, None, None, ["catalogue"], caller_id)`。
3. 有工作 → `kind, info, since = _pf_job_state(job, now)`：
   - `loading` → 回 `answer`。
   - `failed` → `now - since < jobs.PF_RETRY_SECONDS`（60）→ `_cat_error(answer, info, checked_at=job["finished_at"])`；否則視同沒有這筆（往 4）。
   - `done`：`since > now - jobs.CATALOGUE_CACHE_SECONDS`（**嚴格大於**，與 `latest_release` :630 的 `since > now - ttl` 同一邊界；剛好 86400 秒＝過期）→ 取 `info["parts"]["catalogue"]`：
     - `status == "ok"` → `_cat_entries(part["pipelines"])`：每條 `{"name": e["name"], "repo": _releases.repo_of(e["name"]), "description": e["description"], "archived": e["archived"], "latest": _releases.pick_latest(e["tags"])}`（`repo_of` 丟 `ValueError` 的條目跳過；`latest` 可為 `None`）；依 `name` 排序；0 條 → `_cat_error(answer, "bad_response", checked_at=since)`；否則 `answer.update(state="ready", checked_at=job["finished_at"], count=len(list), pipelines=list)`。
     - 其他狀態 → 失敗碼 `_pf_code(status)`；60 秒內 → `_cat_error`；超過 → 往 4。
   - `done` 但超過 24 小時 → 往 4（排新的；**沒有 stale 退路**，見裁決 5）。
4. `enqueue` 為假 → 回 `answer`（`loading`，什麼都不排）。否則 `refusal = _pf_queue(platform_path, None, None, ["catalogue"], compute_env, caller_id)`；有 → `_cat_error(answer, "no_agent", refusal)`；沒有 → `answer`（`loading`）。
- `_CAT_REASONS`（本片自己的固定句，中英並陳，不轉貼代理訊息）：`no_agent` 用 `_pf_queue` 回的句子；`no_answer`、`refused` 沿用 `_PF_REASONS` 的字；`network`：「代理連不到 nf-co.re，請檢查那台機器的網路 (the agent could not reach nf-co.re; check that machine's network)」；`not_found`：「nf-co.re 上找不到管線清單 (nf-co.re has no pipeline list at the known address)」；`too_large`：「nf-co.re 的管線清單太大，沒有讀 (the pipeline list on nf-co.re is too large to read)」；`rate_limited`：「nf-co.re 暫時限制了請求，請一分鐘後再試 (nf-co.re is limiting requests for now; try again in a minute)」；`bad_response`：「nf-co.re 回的清單不能用，請稍後再試 (nf-co.re gave a list that cannot be used; try again later)」。
- 區塊內不得出現 `urllib`、`socket`、`subprocess`、`open(`、字面 `station`（TC-061、TC-133 同款掃描，CA-14 另釘本區塊）。

### 6. 回傳形狀（固定；`json.dumps` 得過；鍵永遠都在）
```
{"state": "loading" | "ready" | "error",
 "checked_at": 1760000000.0 | None,        # 工作 finished_at；loading 為 None
 "count": 159 | None,                      # ready 時 len(pipelines)；其餘 None
 "error": None | "no_agent" | "no_answer" | "network" | "rate_limited" | "not_found" | "too_large" | "bad_response" | "refused",
 "reason": None | "<一句白話，中英並陳；state == error 時必有>",
 "pipelines": None | [                     # ready 時非空、依 name 排序；其餘 None
   {"name": "ampliseq", "repo": "nf-core/ampliseq",
    "description": "Amplicon sequencing analysis workflow using DADA2 and QIIME2",
    "archived": false, "latest": "3.0.0"},
   {"name": "abotyper", "repo": "nf-core/abotyper", "description": "A pipeline for …", "archived": false, "latest": null},   # 只有 dev
   …]}
```
鍵集合 `_CAT_KEYS = {"state", "checked_at", "count", "error", "reason", "pipelines"}`。**沒有 `bad_input`**（這個動作沒有輸入）。失敗範例（逐字）：網路不通 → `{"state": "error", "checked_at": <finished_at>, "count": None, "error": "network", "reason": "代理連不到 nf-co.re，請檢查那台機器的網路 (the agent could not reach nf-co.re; check that machine's network)", "pipelines": None}`；沒有在線代理 → `error: "no_agent"`、資料庫零新列。

### 7. 文件（`docs/PLATFORM.md`）
- :132 `pipeline_files` 那一條：「read four kinds of public file from GitHub」→ 「read five kinds of public file」，清單末加「and nf-core's own list of all pipelines (`https://nf-co.re/pipelines.json`: names, descriptions, whether archived, release tags; the platform works out each newest release with `releases.py` and reuses the answer for 24 hours from the job row)」；「queued by `actions.pipeline_files` and `actions.latest_release`」→ 加 `actions.nfcore_catalogue`。
- :137 「it asks only `github.com`, `raw.githubusercontent.com` and `api.github.com`」→ 加「and `nf-co.re` (one fixed address, the pipeline list)」；其餘句子不動。
- :554 Action layer：「Two actions read public GitHub files」→ 「Three actions read public files」，補一句 `actions.nfcore_catalogue(platform_path, *, compute_env, caller, enqueue)` returns every nf-core pipeline with its newest launchable release, for the guided launch page's search; the page filters.
- 「What the platform stores」表**不加列**：沒有新檔案、沒有新表；答案就在 `jobs` 那列（7 天）。`tests/platform_storage_doc_test.sh` TC-004／TC-009 因此不受影響。
- `docs/TESTING.md`：新增一節（完成標準）。

### 8. 其餘
- **migration：不需要**。`jobs` 表的 CHECK（`store.py:242`）列的是種類，本片不加種類；`args_json` 是自由 JSON，`repo: null` 本來就寫得進去（`tags` 工作的 `revision: null` 是先例，`test_pipeline_files_queue.py:264-266`）。
- **確認：不需要**（裁決 7）。
- **憲法掃描**：平台新增行不得出現字面 `station`、`ssh`、`sbatch`、`urllib.request`、`import socket`、`socket.`、`subprocess`、`threading`、`while True`（`test_scope.py:189-191`、TC-071）。站台新增程式不得出現 `open(`、`.write(`、`os.remove`、`shutil`、`subprocess`、`socket`、`ctx.site`、`site.call`、`Authorization`、`sbatch`、`rm -rf`（TC-042 掃整檔 `pipeline_files.py`）。`abf_station/` 內含 `urllib.request` 的檔仍只有 `agent.py`、`pipeline_files.py`（TC-041）。

## 失敗先行測試
全部寫在新檔 `platform/tests/test_nfcore_catalogue.py`（三節），現在都會紅（`PARTS` 沒有 `catalogue`、`HOSTS` 沒有 `nf-co.re`、`actions.nfcore_catalogue` 不存在）。executor 先跑一次貼紅輸出。站台節的假網路沿用 `test_station_pipeline_files.py` 的 `Net` 寫法（可 import 該模組的 `Net`、`job`、`ctx`，或複製；**不得**改那個檔的 helper）。

### 站台 CS（同行程，注入 `OPEN`）
| 編號 | 案例 | 預期 |
|---|---|---|
| CS-01 | `handlers.JOB_KINDS`、`ARG_KEYS`、`pipeline_files.PARTS` | `JOB_KINDS` 逐字等於現行九種（不變）；`ARG_KEYS["pipeline_files"] == {"repo","revision","parts"}`；`PARTS[-1] == "catalogue"`、`PARTS[:5]` 逐字等於舊五個；`jobs.PF_PARTS == PARTS` |
| CS-02 | `allowed(url)`：`https://nf-co.re/pipelines.json` → True；`http://nf-co.re/pipelines.json`、`https://nf-co.re.evil.com/pipelines.json`、`https://evil.com/nf-co.re/pipelines.json`、`https://nf-co.re@evil.com/x`、`https://nf-co.re:8443/pipelines.json`、`https://www.nf-co.re/pipelines.json` → False，且 False 的情形 `OPEN` 零次呼叫 | 如左；`HOSTS == ("github.com","raw.githubusercontent.com","api.github.com","nf-co.re")` |
| CS-03 | `job(["catalogue"], repo=None, revision=None)`，假 `OPEN` 回 fixture `pipelines-small.json`（200、`Content-Type: application/json`） | 請求**恰一個**，網址逐字 `https://nf-co.re/pipelines.json`、`limit == 8000000`、`Accept == "application/json"`、方法 GET、標頭沒有 `Authorization`／`Cookie`；結果 `("done", {"ok": True, "repo": None, "revision": None, "parts": {"catalogue": {"status": "ok", "pipelines": [...]}}, "message": …})`；`pipelines` 恰 6 條、依 name 排序、每條鍵集合恰 `{"name","description","archived","tags"}`；`ampliseq` 的 `tags == ["3.0.0","2.18.0","dev"]`（fixture 順序）、`description` 逐字等於 fixture、`archived False`；`exoseq.archived True`；`cellpainting.description == ""`（原檔 null）；`abotyper.tags == ["dev"]`；fixture 裡的 `stargazers_count`、`topics`、`html_url`、`releases[].tag_sha` 都不在輸出的任何地方（`json.dumps` 後字串比對） |
| CS-04 | 壞條目被跳過、壞整體是 `bad_response`：fixture 加一條 `name: "../evil"`、一條 `name: 5`、一條沒有 `releases`、一條 `releases: "x"`、一條 `description: 7` | 前兩條不在輸出；後三條在，`tags == []`／`[]`／`description == ""`；頂層 `{"remote_workflows": {}}`、`[]`、`"x"`、非 UTF-8 位元組、`{"remote_workflows": []}`、全部條目名稱都壞 → `{"status":"bad_response","message":…}`（`message` ≤300、中英並陳） |
| CS-05 | 上限：body 8,000,001 位元組；1001 條合格條目 | `too_large`／`too_large`；前者假 `OPEN` 沒被要求讀超過 `limit + 1`；都沒有 `pipelines` 鍵 |
| CS-06 | 404／429／403+`X-RateLimit-Remaining: 0`／500／301 | `not_found`／`rate_limited`／`rate_limited`／`bad_response`／`bad_response`（不跟隨轉址） |
| CS-07 | 連線失敗（`OSError`）；總預算超過（注入 `CLOCK`） | `("error", {"ok": False, "error": "network", "message": …})`；`OPEN` 恰 1／0 次 |
| CS-08 | 拒收壞參數（零請求）：`job(["catalogue"])`（預設 repo／revision）、`job(["catalogue"], repo=None)`（revision 仍 2.18.0）、`job(["catalogue"], revision=None)`（repo 仍給）、`job(["catalogue","schema"], repo=None, revision=None)`、`job(["catalogue","tags"], repo=None, revision=None)`、`job(["schema"], repo=None, revision=None)`（repo None 只對 catalogue 合法）、`job(["catalogue","catalogue"], repo=None, revision=None)` | 每筆 `refused`、`OPEN` 零次 |
| CS-09 | 既有五 part 的工作（`all_ok`，`["schema","schema_input","diagram","image","tags"]`） | 仍恰 5 個請求、網址都不在 `nf-co.re`（既有 TC-048 不變且綠；這裡再釘「`catalogue` 不加進去就不會碰 nf-co.re」） |
| CS-10 | 原始碼：`pipeline_files.py` 含 `"https://nf-co.re/pipelines.json"` 恰一次、不含 `nf-co.re/` 的其他路徑；TC-041、TC-042 的掃描在本檔重跑一次仍無命中 | 如左 |
| CS-11 | 守門：不注入 `OPEN` 直接 `run_fetch(job(["catalogue"], repo=None, revision=None), ctx)` | `AssertionError`（autouse 守門生效） |

### 平台：排隊與清洗 CQ
| 編號 | 案例 | 預期 |
|---|---|---|
| CQ-01 | 新建 `platform.db` 的 `jobs` CHECK 清單；`jobs.KINDS`；`store._jobs_kinds_current` 對新表 | 逐字與 base 相同（`pipeline_files` 仍最後、沒有新字樣）；開兩次不重建（`_migration_step` 零次） |
| CQ-02 | `jobs.CONFIRMED`；不帶 `confirmation_id` 排 `catalogue` 工作 | 仍剛好三項；成功 |
| CQ-03 | `pf_arguments(None, None, ["catalogue"])` | 回 `(None, None, ["catalogue"])` |
| CQ-04 | `pf_arguments` 壞值：`("nf-core/ampliseq", None, ["catalogue"])`、`(None, "2.18.0", ["catalogue"])`、`(None, None, ["catalogue","schema"])`、`(None, None, ["tags","catalogue"])`、`(None, None, ["schema"])`、`(None, None, ["tags"])`、`(None, None, ["catalogue","catalogue"])` | 每筆 `JobRefused`，訊息中英並陳、不含 `station` |
| CQ-05 | `enqueue_pipeline_files(db, None, None, ["catalogue"], clock=clock, caller_user_id=1)`（alice 有在線環境） | 回 id；該列 `kind='pipeline_files'`、`confirmation_id IS NULL`、`deadline_at == now + 90`、`args_json == {"repo": null, "revision": null, "parts": ["catalogue"]}`；`latest_pipeline_files(db, None, None, ["catalogue"], 1)` 找到它、`(db, None, None, ["tags"], 1)` 與 `(db, "nf-core/ampliseq", None, ["tags"], 1)` 找不到；bob（`caller_user_id=2`）找不到 |
| CQ-06 | `clean_result("pipeline_files", …)` 白名單表：合格結果（6 條）原樣；條目多給 `html_url`、`topics`、`stargazers_count`、`token` → 全不在輸出；`name` 為 `"../x"`／`5`／缺少 → 該條丟掉；`description` 401 字 → 切成 400；`description` 非 str → `""`；`archived` 為 `"yes"` → `False`；`tags` 含非 str、含 `"../x"`、501 個 → 丟掉壞的、最多 500；`pipelines` 1001 條 → 只留前 1000；`pipelines` 不是 list／清洗後 0 條 → `{"status":"bad_response"}`；`status` 為 `too_large` 帶 `pipelines` → 只留 `status`、`message` | 如左；也不產生 `entries`（TC-084 的最後 `else` 不被碰到） |
| CQ-07 | `take_result` 走一遍（領取→回合格 `catalogue` 結果） | `result_json` 是清洗後的；`claim` 給代理的 `out["args"] == {"repo": None, "revision": None, "parts": ["catalogue"]}`、沒有 `confirmation`／`run_token` |
| CQ-08 | 原始碼：`jobs.py` 新增常數 `CATALOGUE_CACHE_SECONDS == 86400`、`PF_CATALOGUE_ENTRIES == 1000`、`PF_CATALOGUE_TAGS == 500`、`PF_DESCRIPTION_LIMIT == 400`；`PF_PIPELINE_NAME.match("ampliseq")`、`("Ampliseq_2")`、`("a.b")` 真、`("../x")`、`(".")`、`("")`、`("a b")`、`("a/b")` 假；`PF_TAG_NAME` 同站台 `_TAG_NAME.pattern`；`jobs.py`、`store.py` 整檔無 `station`（TC-091 同款） | 如左 |

### 平台：動作層 CA（資料庫＋假時鐘＋`take_result` 代替代理答覆；沿用 `test_pipeline_files_action.py` 的 `world`／`serve`／`tick` 寫法）
| 編號 | 案例 | 預期 |
|---|---|---|
| CA-01 | 簽章 | 一般函式（非 coroutine）；參數序 `["platform_path", "compute_env", "caller", "enqueue"]`，第一個 POSITIONAL_OR_KEYWORD、其餘 KEYWORD_ONLY；預設 `None`／`None`／`True` |
| CA-02 | parity：`"nfcore_catalogue"` 在 `WEB_ONLY`；`test_web_parity` 的聯集檢查綠；`mcp_server.build_server` 工具名單不含它（工具數不變） | 如左 |
| CA-03 | 第一次呼叫（alice 有在線環境） | `{"state":"loading","checked_at":None,"count":None,"error":None,"reason":None,"pipelines":None}`；資料庫恰一筆 `pipeline_files` 工作、`args == {"repo": None, "revision": None, "parts": ["catalogue"]}`；再呼叫仍 `loading` 且仍一筆 |
| CA-04 | 代理答覆（`serve` 寫入 CS-03 那種 6 條結果）後再呼叫 | `state "ready"`、`count == 6`、`checked_at == finished_at`、`pipelines` 依 name 排序、每條鍵集合恰 `{"name","repo","description","archived","latest"}`；`ampliseq` → `repo "nf-core/ampliseq"`、`latest "3.0.0"`（`pick_latest(["3.0.0","2.18.0","dev"])`）；`abotyper.latest is None`；`exoseq.archived is True`；`cellpainting.description == ""`；整體 `json.dumps` 得過；回傳裡沒有 `tags` 字樣 |
| CA-05 | `latest` 的定義：代理答覆 `tags == ["dev","3.0.0dev","1.0.0-rc1","v2.0.0","2.0.0","1.9.0"]` | `latest == "2.0.0"`（`pick_latest` 的規則：純數字、同版本不帶 v 優先，`releases.py:39-54`）；`tags == ["dev"]` → `None` |
| CA-06 | 部分條目壞（`repo_of` 丟例外的名字由 `_cat_entries` 跳過；此處用 monkeypatch 讓 `releases.repo_of` 對 `"x"` 丟 `ValueError`） | 該條不在清單、其餘照常、`count` 隨之減少 |
| CA-07 | 代理回 `catalogue` 部分 `too_large`／`bad_response`／`rate_limited`／`not_found`；代理回整體 `network`；代理回 `refused`；工作 `queued` 過期沒人領 | `state "error"`、`error` 分別 `too_large`／`bad_response`／`rate_limited`／`not_found`／`network`／`refused`／`no_answer`；`reason` 中英並陳，`network`／`not_found`／`too_large`／`rate_limited`／`bad_response` 的 `reason` 含 `nf-co.re`、不含 `GitHub`；`refused` 的 `reason` 提到更新代理；`pipelines None`、`count None` |
| CA-08 | 失敗後 60 秒內再問 → 同樣的錯誤、**不排新工作**；`now` 推進 61 秒再問 → `loading`、新增一筆 | 如左 |
| CA-09 | 24 小時快取邊界：`ready` 後推進 3600 秒再問 → 仍 `ready`、同一 `checked_at`、**資料庫沒有新工作**；推進到 `finished_at + 86400` 整（含）再問 → `loading`、新增一筆；之後新工作答覆 → `ready` 且 `checked_at` 換成新的 | 如左（嚴格大於＝裁決三第 7 條） |
| CA-10 | 快取過期、新工作失敗（`network`） | `state "error"`、`error "network"`（**沒有 stale 退路**，裁決 5）；60 秒後再問 → `loading` |
| CA-11 | 沒有在線代理 | `error "no_agent"`、`reason` 含「沒有在線的代理」、資料庫零新列；`enqueue=False` → `loading`、零新列 |
| CA-12 | 跨使用者：alice 的 `catalogue` 工作已 `ready`；bob（自己有在線環境）呼叫 | bob `loading`、排自己的一筆、看不到 alice 的清單；bob 沒環境 → `no_agent`；`compute_env` 指 alice 的環境 → 措辭同「找不到」 |
| CA-13 | 不另存檔案：`ready` 前後 `platform.db` 同資料夾 `listdir` 不變（`release-tags.json` 不出現；本測試不呼叫 `latest_release`） | 如左 |
| CA-14 | 原始碼：`actions/__init__.py` 有 `# ---- nfcore-catalogue: begin` … `end` 區塊，區塊內不含 `urllib`、`socket`、`subprocess`、`open(`、`station`；release-lookup-job 區塊（TC-133）仍存在且 >80 行；新區塊內以 `def ` 開頭且名字不以 `_` 起頭的**只有** `nfcore_catalogue`（其餘公開名稱由 CA-02 的 parity 聯集釘住） | 如左 |
| CA-15 | 所有回傳 `json.dumps` 得過；`reason` 不含 `Traceback`、`sqlite`、`args_json`、`deadline_at`、`result_json`、`SELECT`；`state == "error"` 時 `reason` 非空；鍵集合永遠是 `_CAT_KEYS` | 如左 |
| CA-16 | `pipeline_files(world, parts=["catalogue"])` 與 `parts=["schema","catalogue"]` | 仍 `bad_input`（`_PF_ASKABLE` 不收 `catalogue`；清單只能走 `nfcore_catalogue`）、資料庫零新列 |
| CA-17 | 只寫 `jobs`：呼叫前後 `confirmations`、`launches`、`compute_envs`、`agents` 列數不變；`SELECT DISTINCT kind FROM jobs` 只有 `pipeline_files` | 如左 |

**現在會紅**：CS-01～CS-11、CQ-01（`PF_PARTS` 斷言部分）、CQ-03～CQ-08、CA-01～CA-17 全部；CQ-01 的 CHECK 部分與 CQ-02 現在就綠（釘「不變」）。

### 會改斷言的既有測試（PRECHECK 第 3 項；只改所列斷言，其餘不動；逐條舊→新＋理由寫進 ledger）
| 檔案：行 | 現在的斷言 | 改成 | 理由 |
|---|---|---|---|
| `test_station_pipeline_files.py:145-148`（TC-004 `the_three_hosts_are_allowed`） | 迴圈三個網址 | 測試名改 `the_four_hosts_are_allowed`；迴圈加 `"https://nf-co.re/pipelines.json"` | 第四主機放行 |
| `test_station_pipeline_files.py:151-153`（`BAD_URLS`，TC-005／TC-006 共用） | 含 `"https://nf-co.re/pipelines.json"` | **刪掉**那一個；加 `"http://nf-co.re/pipelines.json"`、`"https://nf-co.re.evil.com/pipelines.json"`、`"https://www.nf-co.re/pipelines.json"` | 它現在是合法網址，留著會讓 TC-005 紅；補的三個釘住「只有逐字 nf-co.re」 |
| `test_station_pipeline_files.py:559-563`（TC-047 `there_is_no_way_to_read_other_files`） | `refused(ctx, net, job(["catalogue"]))` | 改成 `refused(ctx, net, job(["catalogue"]))` 加註解「catalogue takes no repo／revision (CS-08)」**並**加一行 `refused(ctx, net, job(["schema", "catalogue"], repo=None, revision=None))`；`readme` 兩行不動 | 這一行現在仍紅→綠（repo 有給所以拒），但它的意思從「沒有 catalogue 這種東西」變成「catalogue 不跟管線一起問」，必須寫明；正面案例在 CS-03 |
| `test_station_pipeline_files.py:2`（檔首 docstring） | 「four kinds of public GitHub file and nothing else」 | 「five kinds of public file（the fifth is nf-core's own pipeline list, test_nfcore_catalogue.py）」 | 文字對上程式 |
| `test_pipeline_files_queue.py:269-276`（`BAD_ARGS`，TC-066） | 19 筆壞參數 | **只加不刪**：`(None, None, ["schema"])`、`("nf-core/ampliseq", None, ["catalogue"])`、`(None, "2.18.0", ["catalogue"])`、`(None, None, ["catalogue", "schema"])` | 新規則的反例也要在 enqueue 端釘住（CQ-04 另有直接呼叫 `pf_arguments` 的版本） |
| `test_pipeline_files_action.py:449-453`（TC-159 `nothing_for_the_whole_nf_core_catalogue`） | `assert not hasattr(actions, "nfcore_catalogue")`；`pipeline_files` 簽章沒有 `catalogue` | **翻轉**：改名 `the_catalogue_is_its_own_action`；`assert callable(actions.nfcore_catalogue)`；`pipeline_files` 簽章仍沒有 `catalogue` 參數（不動）；加 `pf(world, parts=["catalogue"])["error"] == "bad_input"`（需加 `world` fixture） | 維護者 10-26 放行；清單走獨立動作，不塞進 `pipeline_files` |
| `test_pipeline_files_action.py:441-446`（TC-135 `no_mcp_tool_for_the_two_actions`） | `{"pipeline_files", "latest_release"} & names` 為空 | 集合加 `"nfcore_catalogue"`；測試名「two」→「three」 | 第三個無 MCP 工具的動作 |
| `test_web_parity.py:23-32`（`WEB_ONLY`） | 兩列 release-lookup-job | 加 `"nfcore_catalogue": "guided launch searches every nf-core pipeline through the agent (nfcore-catalogue); the page filters; no MCP tool yet"` | 動作層多一個公開名稱 |

**確認沒有牽動（已查，不改）**：種類清單類——`test_byte_channel_a.py`、`test_byte_channel_b.py`、`test_cleanup_confirm.py`、`test_cleanup_store.py`、`test_cloud_cost.py`、`test_launch_platform.py`、`test_resume_scope.py`、`test_station_clean.py`、`test_station_platform.py`、`test_pipeline_files_queue.py` TC-049／TC-060、`test_station_pipeline_files.py` TC-001（`JOB_KINDS` 不變）；工具數類——`test_actions_layer.py`、`test_chat_tools.py`、`test_guidance.py`、`test_pat.py`、`test_oauth_mcp.py`、`test_estimate_su.py`（不加工具）；`test_station_pipeline_files.py` TC-038／TC-040／TC-048（五 part 工作不含 `catalogue`，請求數與上限清單不變）、TC-029～TC-032（`repo=None` 配 `["schema"]` 仍拒、`parts` 壞值仍拒）、TC-041／TC-042（連網檔仍兩個；站台新碼不含禁字）、TC-046（代理仍不解析 schema）；`test_pipeline_files_action.py` TC-093（兩個既有簽章不變）、TC-097（`["tags"]` 等仍 `bad_input`）、TC-132（不呼叫新動作）、TC-133（舊 marker 區塊原樣）、TC-180（仍兩筆工作）；`test_pipeline_files_queue.py` TC-084（`PF_PARTS` 多一項不影響 `evil` 被丟）、TC-091（新增訊息不含 `station`）；`docs/PLATFORM.md:6,357` 工具數句子不動；`tests/platform_storage_doc_test.sh`（儲存表不加列）；`tests/methods_text_fetch_test.sh:221`（那是插件端的 `cache/pipeline_files/` 目錄，同名不同物）。

## 完成標準（done when）
- 自動：CS-01～CS-11、CQ-01～CQ-08、CA-01～CA-17 全綠；上表 7 處既有斷言更新後 `test_station_pipeline_files.py`、`test_pipeline_files_queue.py`、`test_pipeline_files_action.py`、`test_web_parity.py` 全綠；整個 `bash tests/run_all.sh`（WSL）綠，含 `test_scope.py`（TC-061、TC-070、TC-071）、`tests/platform_storage_doc_test.sh`、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`；MCP 工具數不變（斷言測試沒被改）；`git diff --name-only` 只有「範圍：檔案」所列；上表以外的既有測試零改動（`git diff --stat` 貼進 ledger，verifier 核對並重跑）；**測試全程不連真網路**（CS-11 守門）。
- 已知環境紅（通例）：`test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 只剩這一條紅視同綠；計時類偶發紅依 release-lookup-job 裁決五第 17 條。
- 手動（寫進 `docs/TESTING.md` 新增一節「nfcore-catalogue：真的讀一次 nf-co.re (read nf-co.re for real, once)」，**executor 不執行**，developer-agent／維護者合併後在有網路的機器做）：
  1. 平台＋一個代理＋一個指向它的環境（同 release-lookup-job 手動步驟 1）。
  2. 一行 Python 呼叫 `actions.nfcore_catalogue(<platform.db 路徑>)`，每 5 秒再呼叫直到不是 `loading`（最多約 1 分鐘）。**預期**：`state "ready"`；`count ≥ 150`（2026-10-26 實抓 159）；`[p for p in pipelines if p["name"] == "ampliseq"][0]` 的 `repo == "nf-core/ampliseq"`、`latest` 是最新純數字 tag（2026-10-26 是 `3.0.0`；以當天 nf-co.re 為準）、`archived False`；`exoseq` 的 `archived True`；`abotyper` 的 `latest None`（只有 `dev`）；清單依 `name` 排序；`platform.db` 旁沒有新檔案。
  3. 立刻再呼叫 → 同一個 `checked_at`，`jobs` 表沒有新的 `pipeline_files` 列；代理那邊的日誌只看到**一次**對 `nf-co.re` 的請求。
  4. 拔掉代理機器的網路，把那筆工作列刪掉（或等 24 小時）再呼叫：**預期** 約 1 分內 `state "error"`、`error "network"`、`reason` 提到 nf-co.re 與檢查網路。
  5. 輸出貼進 `specs/nfcore-catalogue/ledger.md`。
- 文件：作法 7 的三處 `docs/PLATFORM.md`＋`docs/TESTING.md` 一節；`handlers.py:7`、`pipeline_files.py:1,5,7,57` 的說明句對上程式。

## 環境事實
（行號為 origin/v3 @ ad1ee18；動手前以函式名重新 grep。我只讀碼、沒有改任何 repo 檔。）
- **已合併的 release-lookup-job（#236）**：站台 `abf_station/pipeline_files.py`——`ARGS`:26、`PARTS`:27、`HOSTS`:28、上限常數 :31-35、`_TAG_NAME`:38、`allowed`:56-67、`_fetch_once`:70-86、`OPEN`:89、`_network_result`:92-94、`_problem`:99-121（現在**先**驗 repo 再驗 parts，所以 repo None 一律拒；本片要把順序調成先 parts）、`_Fetcher.get`:130-142（`allowed` 不過就 `rules.Refusal`、預算用 `CLOCK`）、`_words`:145-151、`_judge`:158-166、`_listing`:201-218（解析目錄清單 JSON 的先例）、`run_fetch`:325-359。`handlers.py`:19 `JOB_KINDS` 九種、:22 `ARG_KEYS["pipeline_files"] = pipeline_files.ARGS`、:64-65 分派。平台 `jobs.py`——`PF_PARTS`:47、`PF_STATUSES`:48、`PF_RETRY_SECONDS`:49、`TAGS_CACHE_SECONDS`:50、`PF_REVISION`:52、`PF_TEXT_LIMIT = 1000000`:54、`CONFIRMED`:58、`_target` Google Batch 放行清單含 `pipeline_files`:103、`_enqueue` 拒直接排 `pipeline_files`:177-178、`pf_arguments`:251-272、`pick_environment`:275-291、`enqueue_pipeline_files`:294-306、`latest_pipeline_files`:455-476（比對 `repo`、`revision`、`parts` 三者相等；`None == None` 成立）、`_clean_pf_part`:841-872、`clean_result` 的 `pipeline_files` 分支 :892-900（依 `PF_PARTS` 迴圈）。`store.py`:242 CHECK 九種、:254 確認 CHECK 三種、:410-411 `_jobs_kinds_current`。動作層 `actions/__init__.py`:445-659 marker 區塊：`_PF_ASKABLE`:451（不含 `tags`，本片也不加 `catalogue`）、`_PF_REASONS`:461-472、`_pf_job_state`:498-511、`_pf_code`:535、`_pf_queue`:539-545、`pipeline_files`:548、`latest_release`:596（:630 `since > now - ttl` 的嚴格邊界）、`_caller_id`:746。`releases.py`：`repo_of`:16-27（`ampliseq` → `nf-core/ampliseq`）、`usable`:30、`pick_latest`:39-54。
- **既有測試的釘子**：`test_station_pipeline_files.py` TC-004:145、`BAD_URLS`:151-153（含 nf-co.re）、TC-038:483-492（五 part 鍵集合）、TC-040:505-510（上限清單 `[1000000,1000000,1000000,2000000,4000000]`）、TC-041:515-518、TC-042:521-525、TC-043 守門:528-533、TC-046:552-556、TC-047:559-563（`job(["catalogue"])` 被拒）、TC-048:566-578（五種網址形）。`test_pipeline_files_queue.py` `BAD_ARGS`:269-276、`good_result`:390-396、TC-084:471-478、TC-091:567-575。`test_pipeline_files_action.py` `PF_KEYS`／`LR_KEYS`:29-32、TC-093:145-156、TC-132:392-427、TC-133:430-438（marker 掃描）、TC-135:441-446、TC-159:449-453、TC-180:573-579。`test_web_parity.py` `WEB_ONLY`:23-32、`public_names`:49-51。`test_scope.py` TC-061:187-198 禁字清單。
- **文件現況**：`docs/PLATFORM.md`:128（「the first three for the site, the fourth for public GitHub files」）、:132（`pipeline_files` 條目）、:137（三主機句）、:554（Two actions）、:650（儲存表 `release-tags.json` 列）、:677（`ABF_PLATFORM_DEADLINE_PIPELINE_FILES`）；`docs/TESTING.md`:690-698 release-lookup-job 手動節（本片新節接在它後面）。`tests/platform_storage_doc_test.sh`:68-106：Where 欄反引號名字要在 `platform/` 程式碼、「N hours」要對上 `abf_platform/*.py` 頂層常數——本片不加列所以不觸發。
- **我 2026-10-26 實抓一次 `https://nf-co.re/pipelines.json`**（curl、GET、不帶 `Accept-Encoding`、`--max-redirs 0`、匿名；檔存在我的 scratchpad，sha256 前 16 位 `75b620f48561dac0`）：
  - 回 `HTTP/1.1 200`、`Content-Type: application/json`、`Content-Length: 3138916`（**3,138,916 位元組**，未壓縮；`Server: Netlify`、`Cache-Control: public,max-age=0,must-revalidate`、`Vary: Accept-Encoding`——`urllib` 預設不送 `Accept-Encoding`，拿到的就是這份未壓縮本文）。沒有轉址。
  - 頂層**只有一個鍵** `remote_workflows`（list，**159** 條）。每條是 GitHub repo 物件加 nf-core 自己的欄位，共 95 個鍵（`name`、`full_name`、`description`、`archived`、`releases`、`topics`、`stargazers_count`、`html_url`……）；本片只取 `name`、`description`、`archived`、`releases[].tag_name`。
  - `name`：159 條全部符合 `^[a-z0-9][a-z0-9_-]{0,60}\Z`、最長 25 字；`full_name` 159 條**全部**等於 `"nf-core/" + name`（所以平台用 `releases.repo_of(name)` 組 repo 不會錯）；清單原本就依 `name` 排序。
  - `description`：str 或 `null`（`cellpainting`、`moleculardynamics` 兩條是 `null`）；最長 331 字元；沒有換行；1 條含非 ASCII。
  - `archived`：bool；14 條為 true（`crisprvar`、`ddamsproteomics`、`deepvariant`、`denovohybrid`、`exoseq`、`genomeannotator`、`liverctanalysis`、`neutronstar`、`proteomicslfq`、`quantms`、`scflow`、`smartseq2`、`ssds`、`vipr`）。
  - `releases`：每條都有（0 條缺）、list、**新的在前**（159 條全部依 `published_at` 降序），每筆鍵 `tag_name`、`tag_sha`、`published_at`、`has_schema`、`nextflow_version`、`nf_core_version`、`components`、`doc_files`、`plugins`、`co2footprint_files`；`tag_name` 全是 str、最長 14 字；每條最多 42 筆（`rnaseq` 42、`mag` 39、`sarek` 37）；全部 960 筆 tag 中不符 `^v?[0-9]+(\.[0-9]+){1,3}$` 的只有 `dev`、`1.0.3dev`、`1.0.3dev-alpha`、`0.1.0-alpha`、`1.0.0-rc1`、`3.0.1b`（`pick_latest` 會略過它們）。**50 條管線沒有任何可用的純數字 tag**（只有 `dev`，例 `abotyper`、`alleleexpression`），所以 `latest` 必須允許 `None`。
  - `ampliseq`：`description` 「Amplicon sequencing analysis workflow using DADA2 and QIIME2」、`archived false`、tags 由新到舊 `3.0.0`（2026-10-09）、`2.18.0`、`2.17.0`、`2.16.1`、`2.16.0`…；`pick_latest` → `3.0.0`（與 release-lookup-job 手動步驟 3 的 GitHub 答案一致）。
  - 整理後的清單（name＋description＋archived＋tags）序列化 **35,259 字元**——遠小於 `PF_TEXT_LIMIT`（1,000,000）與 SQLite 一列的合理大小；整份原檔 3.1 MB 則**超過** `PF_TEXT_LIMIT`，所以不能原樣交回（裁決 3）。
- **fixture 內容（`platform/tests/fixtures/catalogue/pipelines-small.json`）**：從真檔剪 6 條——`abotyper`（只有 `dev`）、`airrflow`（`5.1.2`、`5.1.1`、`dev`）、`ampliseq`（只留 `3.0.0`、`2.18.0`、`dev` 三筆 release）、`cellpainting`（`description: null`）、`exoseq`（`archived: true`）、`rnaseq`（留 `3.27.0`、`3.26.0`、`dev`）；每條保留真檔的 `full_name`、`html_url`（真檔是 `null`，照留）、`topics`、`stargazers_count` 等多餘鍵、`releases[]` 保留 `tag_sha`／`published_at`，證明會被丟掉。檔案 ≤ 60 KB。寫入 fixture 的值由 executor 從上面列的實抓結果照抄（不連網）。
- **查不到、不要猜**：nf-co.re（Netlify）對匿名 GET 有沒有速率限制——文件沒寫；萬一回 429 代理回 `rate_limited`，平台 60 秒後重試。

## 不做
- 不加工作種類、不改 `store.py`、沒有 migration（裁決 1）。
- 不加 MCP 工具、不加網頁路由、不改 `web*.py`／`guidance.py`／`chat_tools.py`；「搜尋全部 nf-core」步驟的接線與過濾是 guided-launch-2 的事（裁決 6）。
- 不收 `query`／`limit` 參數；不在平台做模糊比對、不做排名。
- 不讀 nf-co.re 的其他路徑（只有 `/pipelines.json`），不讀 GitHub 以外與 nf-co.re 以外的任何主機；不帶憑證；不跟隨轉址。
- 不另存檔案快取（沒有 `nfcore-catalogue.json`）；不改 `release-tags.json` 的用途；不改 `releases.py`（`pick_latest` 只呼叫）。
- 代理不挑最新版、不過濾 `dev`、不解析 `description` 以外的文字；不把 `topics`、星數、網址交回平台。
- 沒有 stale 退路：24 小時過期後新工作失敗就是 `error`（裁決 5）。
- 不改既有五個 part 的任何行為、訊息、上限；不改 `_network_result`／`_words` 的字（裁決 9）。
- 不改 `pipeline_files`／`latest_release` 的簽章與回傳形狀；`_PF_ASKABLE` 不加 `catalogue`。

## 裁決（2026-10-26，developer-agent）
1. **多一個 part，不加種類**。新種類要動 `store.py` 的 CHECK＋migration（`store.py:242,410-424`）、`DEADLINE_SECONDS`、`_target` 放行清單、`handlers.JOB_KINDS`，並翻掉所有「`pipeline_files` 排最後」的斷言（station TC-001、queue TC-049／TC-060、`test_byte_channel_{a,b}`、`test_cleanup_confirm` TC-033、`test_resume_scope`、`test_launch_platform`、`test_cloud_cost`、`test_station_platform`、`test_cleanup_store`、`test_station_clean`）。多一個 part 只動 `PARTS`／`PF_PARTS` 兩個 tuple，排隊、領取、清洗、環境選擇、期限全部重用。代價是 `repo`／`revision` 對這個 part 是 `None`——`tags` 的 `revision: None` 已是先例。
2. **第四主機只准 `nf-co.re`，網址是常數**。沒有參數可組，所以 `allowed()` 之外再釘「`pipeline_files.py` 裡 `nf-co.re/` 只出現在 `CATALOGUE_URL`」（CS-10）。`www.nf-co.re` 不放行（我沒有查證它是否存在，寧可不放）。
3. **代理整理、平台算最新版**。原檔 3.1 MB 超過 `PF_TEXT_LIMIT`（1,000,000）且 95 個鍵裡只需要 4 個，原樣交回既塞不進也沒道理；代理解析目錄清單 JSON 來挑圖是已核可的先例（release-lookup-job 裁決四第 14 條），本片同類。但「哪個是最新版」仍由平台用 `releases.pick_latest` 判定——與 `latest_release` 同一個答案來源，兩邊不會打架。
4. **上限 8 MB**（作法 2）：真檔已是 4 MB 的 78%，照 nf-core 每年新增十幾條管線的速度，4 MB 兩年內會爆；8 MB 留一倍以上餘裕，記憶體上無虞。dev-queue.json 那行「<=4 MB」是草案數字，以本裁決為準。
5. **快取＝已完成的工作列重用 24 小時，不另存檔、不做 stale 退路**。`latest_release` 之所以寫 `release-tags.json` 是因為 `releases.lookup` 本來就帶這個快取而且只存一個版本號；清單沒有現成的純模組寫檔，動作層又不得 `open(`（TC-133），為它新開寫檔器不值得。工作列保留 7 天（`PRUNE_AFTER_SECONDS`），24 小時內重用它就是快取；過期後排新工作、新工作失敗就顯示錯誤——頁面上「新管線」步驟本來就保留手填 `pipeline`／`revision` 欄位（guided-launch-1），清單拿不到不會卡死使用者。若維護者要 stale 退路，另開一件：要改 `latest_pipeline_files` 或加一個「最近一筆成功」的查詢。
6. **過濾在網頁，不收 `query`**。清單只有約 35 KB、159 條，過濾是純字串比對；若動作層收 `query`，每個關鍵字都是不同的動作呼叫但同一筆工作，等於把快取邏輯和搜尋邏輯綁在一起，而 guided-launch-2 計畫（第 47 行）早已把過濾規則寫在前端。動作層回全表、依 name 排序，前端照它的規則切。
7. **不需確認**。`jobs.CONFIRMED`（`jobs.py:58`）與 `store.py:254` 的 CHECK 只列會寫站台的三種；`pipeline_files` 整個種類本來就不在裡面，多一個 part 不改變「唯讀、不送使用者資料」的性質（請求裡連 repo 名都沒有）。
8. **每個使用者各自一筆工作**（沿用 `latest_pipeline_files` 的擁有者過濾）。清單雖是公開資料，但工作掛在使用者自己的環境與代理上；跨使用者共用結果要另設查詢，也會讓「別人的工作永遠看不到」（A-13／TC-124）出現例外。一天一人一次 3 MB，不值得破例。
9. **站台的既有字句不改**。`_network_result`、`_words` 的訊息提到 GitHub，但平台從不把代理的 `message` 顯示給使用者（`_PF_REASONS` 自備句子），本片的 `_CAT_REASONS` 自己寫 nf-co.re 的句子；改站台字句只會動到 TC-036 之類與本片無關的測試。
10. **站台不新增狀態字樣**：壞 JSON／壞形狀一律 `bad_response`（與 `_listing` 一致），`PF_STATUSES` 不變；動作層不需要 `bad_json`（沒有平台端再解析的文字）。
11. **`archived` 與 `repo` 一併回傳**：14 條封存管線不該被搜尋到就送去啟動，前端需要這個欄位才能灰掉或排除；`repo` 讓前端不必自己拼 `nf-core/`。這是在 release-lookup-job 裁決二 `{name, description, latest}` 之上加兩個鍵，形狀仍固定。

6. **（10-27）既有測試 `platform/tests/test_catalogue.py::test_no_tool_route_or_action_mentions_the_catalogue`（TC-070/071，管 nf-core「模組」目錄 `catalogue.py` 不准接進工具／路由／動作層）准許最小修改**：只對 `actions/__init__.py` 先刪掉 `# ---- nfcore-catalogue: begin` 到 `# ---- nfcore-catalogue: end` 的整個區塊、再去掉識別字 `nfcore_catalogue`，剩下的文字照舊不得含 `catalogue`；其他檔（mcp_server.py、web.py、web_board.py、其餘 actions/*.py）完全不放寬。理由：兩個 catalogue 是不同的東西（本任務讀官網「管線」清單，舊測試管的是「模組」目錄），舊測試的本意不變；這一處列為第 9 處既有斷言更新，舊到新寫進 ledger。另外：完成標準的「7 處」以「會改斷言」表的實際列數為準（8 列＋本條＝9 處）；手動步驟 3 的「代理日誌只看到一次請求」做不到（站台沒有這種日誌），改成只驗同一個 checked_at、jobs 表沒有新的 pipeline_files 列。

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
