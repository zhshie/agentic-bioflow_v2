---
id: byte-channel-a
title: 位元組通道（上）平台側：新工作種類 put_upload——排隊、驗證、遷移、回報（代理怎麼寫進 bucket 在 byte-channel-b）
tier: B
kinds: backend
lane: L-byte（byte-channel-a 先、byte-channel-b 後，同一車道依序；碰 `jobs.py`／`store.py`，不可與任何改這兩檔的任務平行）
base: v3（cloud-upload／PR #192 已在 v3；本任務從 origin/v3 開分支）
source: memory/dev-plans/cloud-upload.md 待裁決 1、裁決二 1–2；docs/adr/0010-chat-keys-byte-channel-studio-embedding.md 第 2 點與 Decided 2。因「檔案 ≤10 個、測試 ≤60 條」的上限拆成 -a／-b 兩份。
---

# byte-channel-a

> 本檔由 developer-agent 助理起草（2026-10-24）。**byte-channel 拆兩半**：-a（本檔）＝平台程序這一側（工作種類、資料庫、排隊檢查、結果清洗、遷移）；-b＝代理這一側（真的讀檔、`gcloud storage cp -` 餵 stdin、再檢查一次、回報）。拆的理由：合起來要動 12 個檔、約 55 條測試，超過「≤10 檔、≤60 條」。-a 單獨合併後，平台能排隊、但沒有代理認得這種工作（代理會照 `handlers.py:39–41` 回「不支援」），所以**沒有任何使用者可見的變化**；-b 接上後才端到端。B 級（後端行為與資料結構改變）→ verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
平台能排一種新工作 `put_upload`：「請平台主機上的代理，把使用者在 `uploads/<他的名字>/` 裡的某一個檔，寫到 `gs://<workDir 的 bucket>/uploads/<他的名字>/<檔名>`」。工作只帶**檔案的參照**（擁有者名、單層檔名、大小、目的地網址），不帶位元組、不帶本機路徑、不帶金鑰；排隊前先在平台側把能擋的都擋掉（不是自己的環境、不是 Google Batch 環境、檔案不在、超過 2 GB…）；結果只收「寫了幾個位元組、寫到哪個 gs:// 位置」。

為什麼這樣切：
1. cloud-upload 已把位置語言與串流核心放進 `cloud_store.py`（`upload_prefix`:67、`object_url`:75、`inside_prefix`:80、`stream_into`:111），並明寫位元組要走「平台主機上的代理」（cloud-upload 裁決二 1）。這一步補上「平台怎麼把要求交給代理」。
2. 工作佇列是現成的（`jobs.py`、`/agent/poll`、`/agent/result`，`receiver.py` 不認工作種類、不必改），所以新種類只需要：資料庫的 CHECK 清單＋遷移、`jobs.py` 的種類表與排隊函式、`clean_result` 的一個分支。
3. 平台程序不碰位元組、不啟動程式（憲法原則 2，`test_scope.py` TC-071）：本任務的程式碼裡沒有讀內容的 `open(`、沒有 gcloud。

## 維護者原話（verifier 出題用）
- ADR 0010 Decided 2（2026-10-17，逐字）：「**Byte channel:** option A. Loopback when the browser is on the agent's machine, otherwise a relay through the platform that writes nothing to disk. The agent gets its first loopback listener and its first write (into the person's upload folder, each time confirmed by a person).」→ ①代理是寫入者；②每次寫入要有人確認（見裁決 4：本任務如何處理）；③與本任務派工的差別：本任務依 developer-agent 的派工，走「平台主機上已有 uploads/ 資料夾裡的檔」這條路，不是 ADR 的記憶體轉送；差別列在裁決 7。
- replan 第 16 點（`memory/PLAN-abf-v3-replan-2026-10.md`，逐字）：「雲端上傳＝**平台代傳**到使用者自己的 bucket、不落地（ADR 0010 規則），大檔給 `gsutil` 指令」→ 目的地只能是呼叫者自己的前綴；2 GB 以上不收、回指令。
- 10-18 裁示（引自 `cloud-upload.md`）：「上傳 >2 GB 改給指令」→ 2,000,000,000 位元組仍收、多一個位元組就不收（`datasets.py` 的 `WEB_UPLOAD_LIMIT`）。
- 憲法原則 2（`test_scope.py` TC-071）：平台程序不啟動任何程式；TC-061：平台來源不得出現「station」這個字（不准拆字）。
- 派工指令（2026-10-24）：「工作只帶 uploads/ 裡那份檔的參照，不把位元組放進工作的 JSON；大小上限 2 GB；只准寫 `gs://<workDir bucket>/uploads/<owner>/`；結果回報寫了幾個位元組與 gs:// 路徑；不得動 hooks/*、tests/run_all.sh、.github/*、actions/__init__.py、abf_launch/build.py、abf_station/launch.py；接到網頁／MCP 的線不在本任務（cloud-upload-wire）」。

## 範圍：檔案（只准改這些；共 8 個）
1. `platform/abf_platform/jobs.py`
2. `platform/abf_platform/store.py`
3. `platform/abf_platform/cloud_store.py`（只加一個常數 `UPLOAD_LIMIT`，見作法 C）
4. `platform/tests/test_byte_channel_a.py`（新）
5. `platform/tests/test_launch_platform.py`（只改 :606 一行）
6. `platform/tests/test_resume_scope.py`（只改 :70 一行）
7. `platform/tests/test_station_platform.py`（只改 :319–:329 的種類清單）
8. `platform/tests/test_cloud_cost.py`（只改 :746–:747 的種類清單）

**不准動**：`hooks/*`、`tests/run_all.sh`、`.github/*`、`platform/abf_platform/actions/__init__.py`、`platform/abf_launch/build.py`、`platform/abf_station/launch.py`；以及 `receiver.py`、`web.py`、`mcp_server.py`、`confirm.py`、`actions/datasets.py`、`pyproject.toml`、`constraints.txt`、整個 `abf_station/`（-b 的）。

## 作法
（全部是決定，不是程式碼。行號是 origin/v3 的；開工前 `git -C <repo> fetch -q origin` 再核對。）

**A. `store.py`——資料庫放行新種類，並替舊檔遷移**
1. `_JOBS_TABLE` 的 `kind` CHECK（:236）清單尾端加 `'put_upload'`（順序＝現有六個＋它；`test_cloud_cost.py:746` 釘順序）。`confirmation_id` 那條 CHECK（:248）**不動**：`put_upload` 不需要確認憑證（裁決 4）。
2. 第 174 行上方的註解「exactly six job kinds」改成七個、並說明第七個沒有確認。
3. `_migrate_jobs_kinds`（:402–434）的「是否已遷移」判斷（:407、:413）由「`read_task_log` 在表 SQL 裡」改成「`read_task_log` **且** `put_upload` 都在表 SQL 裡」。理由：既有測試 `test_run_diag_tools.py:294` 把 `, 'read_task_log'` 從 SQL 剪掉來造舊表（剪完 `put_upload` 仍在），判斷若只看 `put_upload` 會讓那個舊表不遷移而紅；兩個都看則舊表照遷、也涵蓋「六種的表」。函式名、複製欄位的方式（取新舊表共有欄位）、`sqlite_sequence` 保留、單一交易、`_migration_step("copied")` 測試鉤子，全部不變。
4. **這是資料結構變動，所以有 migration**（上一項）；`connect_state`（:583）的呼叫順序不變。PR 說明寫：遷移只重建 `jobs` 表（放寬一個 CHECK），不碰 `confirmations`、`launches`、`compute_envs`；舊的 id 與 AUTOINCREMENT 計數保留。

**B. `jobs.py`——新種類 `put_upload`**
1. 種類表：`DEADLINE_SECONDS`（:26）尾端加 `"put_upload": 3600`（一小時：2 GB 以 5 MB/s 約 400 秒，留餘裕）；`_DEADLINE_ENV`（:28）加 `"put_upload": "ABF_PLATFORM_DEADLINE_PUT_UPLOAD"`。`KINDS`（:39）由 `tuple(DEADLINE_SECONDS)` 自動得到，順序＝六個＋`put_upload`。**不放進 `CONFIRMED`（:41）**，`claim`（:608）因此不會帶確認憑證、也不發 run token（:626、:636 只對 CONFIRMED 的種類）。
2. `_target`（:71）三處增修，其餘不變：
   - :86 的「Google Batch 環境只准這些種類」清單加 `put_upload`（變成 `preflight`、`launch_nextflow`、`cancel_run`、`put_upload`）。
   - 新增反向檢查（放在 :86 附近）：`kind == "put_upload"` 且環境不是 `PLATFORM_HOST_TYPES` → `JobRefused`，白話：「只有 Google Batch 環境能放雲端資料（only a Google Batch environment can hold cloud data）」。擁有者檢查在它之前（:79 已先回「找不到」），所以不洩漏別人的環境存在與否。
   - :100 的「必須 `available`」清單加 `put_upload`；訊息裡 `"list files" if … else "run an analysis"` 改成三向，`put_upload` 用 `"store a file"`（原兩個種類的字不變）。理由：cloud-upload 裁決二 5 說「傳輸時才檢查」；`available` 代表預檢過（金鑰、bucket 可達）。
3. 新函式 `enqueue_put_upload(state_path, tokens_path, ce_name, owner_name, filename, uploads_dir, caller_user_id, clock=time.time, deadline_seconds=None, offline_after=None, stat=os.lstat)` → 工作 id。**這是唯一能排 `put_upload` 的入口**（`_enqueue` 的泛用路徑不接這個種類）。依序檢查，任何一項不過就 `JobRefused` 加白話訊息，且**什麼都沒排**：
   1. `caller_user_id` 必須是整數（終端機的 `None` 一律拒：沒有使用者就沒有「他自己的前綴」）。
   2. `owner_name` 必須就是 `caller_user_id` 的名字：`store.user_id_of(tokens_path, owner_name) == caller_user_id`，否則用「找不到計算環境」同一句拒（不說名字不符）。理由：前綴由名字組成，名字若能由呼叫者自填，就能寫進別人的前綴（跨使用者寫入）。
   3. `filename` 與 `owner_name` 經 `cloud_store.object_url(...)` 驗證（單層、無 `/`、`\`、`..`、NUL、長度 1–255）；`CloudPathError` 轉成 `JobRefused`（訊息是該錯誤的白話句，不回顯輸入原文）。目的地 `dest` 由 `object_url(compute_envs.view(row), owner_name, filename)` 在交易裡算出，**不接受呼叫者傳入的網址**。
   4. 檔案：`path = uploads_dir / owner_name / filename`，用注入的 `stat`（預設 `os.lstat`，不跟隨符號連結）取資訊：必須存在、是一般檔案（不是資料夾、不是符號連結）；`path` 的 `realpath` 必須仍在 `uploads_dir / owner_name` 之內；`st_size` 必須 1 ≤ size ≤ `cloud_store.UPLOAD_LIMIT`（0 位元組＝「空檔案，沒有東西可存」；超過＝白話句加 `cloud_store.big_file_command(ce, owner_name)` 的那一行指令，與 012c 的 `check_web_upload` 同口氣）。**平台在這裡只 `lstat`，不打開、不讀內容、不算雜湊。**
   5. `_target(con, ce_name, "put_upload", now, offline_after, caller_user_id)`（擁有者、代理在線、狀態）。
   6. 排入 `args = {"ce": compute_envs.snapshot(row), "owner": owner_name, "name": filename, "size": <st_size>, "dest": <dest>}`；**這五個鍵剛好，不多**。`_insert_job`（:107）不傳 `confirmation_id`。
4. `clean_result`（:665）加 `put_upload` 分支（**不得落入最後的 `else`**——那個分支會把 `entries` 等列表欄位留下）：只保留 `ok`、`message`／`error`／`note`（既有的 2000／300 字上限）、`bytes`（`_int`，0 ≤ n ≤ `UPLOAD_LIMIT`；布林、負數、字串一律丟掉）、`path`（字串，≤1100 字）。**其他任何鍵（例如 `stdout`、`key`、`text`）丟掉。** 若 `ok` 為真但沒有合格的 `bytes` 或 `path`，把 `ok` 改成 `False`（成功必須有數字與位置）。
5. `take_result`（:743）不改。`wait_for_result` 不改。

**C. `cloud_store.py`——一個常數**
- 加 `UPLOAD_LIMIT = 2_000_000_000`（位元組，十進位），註解說「與 `actions/datasets.py` 的 `WEB_UPLOAD_LIMIT` 相同；兩邊各存一份，因為 `datasets.py` 會 import `abf_launch.build`（:18），代理與佇列不該為了一個數字拖進它；由測試保證兩者相等」。不改 `stream_into` 與其他函式。檔首 `# Nothing existing:` 行不動。

**D. 為什麼不加確認憑證種類（含查證）**
- 「第三種確認」會動：`confirmations` 表的 CHECK（`store.py:206`）與其遷移（外鍵參照 `jobs.confirmation_id`，重建要先關外鍵）、`confirm.py:27` 的 `JOB_KIND`、`actions/__init__.py`（禁區）的確認頻道，以及四處明文釘住「只有兩種」的測試（`test_resume_scope.py:68–71` 與 `test_tc161`、`test_cloud_cost.py:748`、`test_keep_submissions.py:773–774`）。那是比本任務大、且碰禁區的設計；見裁決 4 與開放問題。

## 失敗先行測試（`platform/tests/test_byte_channel_a.py`；用 `tmp_path` 當平台資料夾，沿用 `test_gcb_ce.py` 的 `ip`／`_available_gcb`／`set_status`／`jobs_count` 與 `test_gcb_launch.py` 的 `gce()` 造環境（`import` 它們，不複製）；假 `stat`；不連網、不啟動程式、不讀任何金鑰檔）
編號是本計畫內的 BA-nn；verifier 轉成正式 TC。

資料庫與遷移
- BA-01 新建的 `platform.db`：`INSERT INTO jobs (…kind…) VALUES (…'put_upload'…)` 不帶 `confirmation_id` 成功；`'put'`、`'upload'`、`'put_uploads'`、`''` 仍 `IntegrityError`。
- BA-02 `store.STATE_SCHEMA` 的 `jobs` CHECK 清單剛好是七個且順序為 preflight, list_site_files, launch_nextflow, cancel_run, fetch_run_records, read_task_log, put_upload。
- BA-03 六種的舊表（造法：把 `, 'put_upload'` 從 `jobs` 的 SQL 剪掉，仿 `test_run_diag_tools.py:285–330`）→ `connect_state` 後三筆舊資料欄位逐欄不變、id 不變、`MAX(id)` 續接、新種類可寫、`rm`／`launch`／空字串仍拒。
- BA-04 遷移途中失敗（在 `store._migration_step` 鉤子丟例外）→ 舊表原樣、列數不變；再次 `connect_state`（不丟例外）成功遷移。
- BA-05 已是七種的表再 `connect_state` 兩次＝不重建（`sqlite_master` 的 SQL 與 rowid 不變）。
- BA-06 更舊（連 `read_task_log` 也沒有）的表一次遷到七種：舊三筆資料保留（`test_run_diag_tools.py:285` 那條測試原封不動仍綠，即證）。

種類表
- BA-07 `jobs.KINDS` 的末項是 `put_upload`；`jobs.CONFIRMED` 仍剛好 `{"launch_nextflow": "launch", "cancel_run": "cancel"}`。
- BA-08 `jobs.deadline_seconds("put_upload") == 3600`；`ABF_PLATFORM_DEADLINE_PUT_UPLOAD=7` → 7；壞值（`abc`、`-1`、`0`）→ 3600。
- BA-09 `cloud_store.UPLOAD_LIMIT == 2_000_000_000`，且 `== actions.datasets.WEB_UPLOAD_LIMIT`。

排隊（好的一條）
- BA-10 使用者 alice 的可用 Google Batch 環境 `gcb1`、`<uploads>/alice/reads.fastq.gz`（500 位元組）→ 回工作 id；資料庫該列 `kind='put_upload'`、`state='queued'`、`confirmation_id IS NULL`、`deadline_at = now+3600`；`args_json` 的鍵集合**剛好** `{ce, owner, name, size, dest}`；`size==500`；`dest == "gs://<workDir 的 bucket>/uploads/alice/reads.fastq.gz"`；`ce` 是 `compute_envs.snapshot` 的形狀（含 `workDir`、不含金鑰檔路徑）。
- BA-11 `args_json` 與整列字串裡**找不到** `uploads_dir` 的本機路徑、`gcp-sa`、`private_key`、`/home`。
- BA-12 `claim`（agent 名＝該環境的代理）取到這個工作：`out["kind"]=="put_upload"`、**沒有** `confirmation` 鍵、**沒有** `run_token` 鍵；`remaining` ≤ 3600；工作變 `claimed`。

排隊（被擋的）——每一條都要斷言 `jobs_count` 不變、訊息是白話且不含原始輸入
- BA-13 `caller_user_id=None` → 拒。
- BA-14 `owner_name` 是別人的名字（bob 的名字配 alice 的 id）→ 拒，訊息＝「找不到計算環境」那句，與環境真的不存在時字面相同。
- BA-15 alice 對 bob 的環境排工作 → 同一句「找不到」；對不存在的環境 → 同一句。
- BA-16 環境是 Slurm 型（`platform != googlebatch-platform`）→ 拒，訊息含「Google Batch」。
- BA-17 環境狀態 `unsupported`／`disabled`／`unchecked`（未預檢）／`unavailable` → 各拒一次；`available` 才過（`set_status` 逐一切換）。
- BA-18 代理離線（`last_seen_at` 超過 `offline_after`）→ 拒，訊息含代理名。
- BA-19 檔名壞：`""`、`"a/b"`、`"a\\b"`、`".."`、`"."`、含 NUL、256 字元、含換行 → 全拒；訊息不回顯原文。
- BA-20 檔案問題：不存在、是資料夾、是符號連結（posix；Windows 以注入的 `stat` 回「符號連結」模式代替）、`realpath` 跑出 `uploads/alice`（用注入的 `stat` 與 `tmp_path` 內的捷徑檔造）→ 各拒一次。
- BA-21 大小邊界（用注入的 `stat` 回假大小，不真的造 2 GB 檔）：0 → 拒（「空檔案」）；1 → 過；2,000,000,000 → 過；2,000,000,001 → 拒，訊息含 `cloud_store.big_file_command(...)` 那一行，且該行是 `gcloud storage cp <你電腦上的資料夾>/* gs://<bucket>/uploads/alice/rawdata/`。
- BA-22 同一個檔案連續排兩次 → 兩個工作都成功（覆寫同名物件是允許的，見裁決 5）；不做「進行中就拒」。

結果清洗
- BA-23 `clean_result("put_upload", {"ok": True, "bytes": 500, "path": "gs://b/uploads/alice/x"})` → 原樣三鍵；多給 `stdout`、`key`、`text`、`entries`、`private_key` → 這些鍵全不在輸出。
- BA-24 `ok: True` 但缺 `bytes`、或 `bytes` 是 `True`／`-1`／`"500"`／`2_000_000_001`、或 `path` 不是字串 → 輸出的 `ok` 變 `False`。
- BA-25 `path` 超過 1100 字、`message` 超過 2000 字 → 被截；`error`／`note` 超過 300 字 → 被截。
- BA-26 `take_result` 走一遍：代理對一個 `claimed` 的 `put_upload` 回 `done`＋合格結果 → 資料庫 `result_json` 是清洗後的；重複回 → 409；別的代理回 → 403；逾期回 → `late`、工作變 `expired`（與其他種類一致）。

不變性（防回歸）
- BA-27 Google Batch 環境排 `list_site_files`、`fetch_run_records`、`read_task_log` 仍被「尚未支援」擋下（既有 `test_gcb_ce.py:718–735`、`test_gcb_launch.py:972–986` 原封不動仍綠）。
- BA-28 `launch_nextflow` 在 Slurm 環境的 `available` 檢查訊息仍含 "run an analysis"；`list_site_files` 仍含 "list files"（三向訊息沒弄壞舊的兩向）。
- BA-29 原始碼掃描：`jobs.py`、`store.py` 全文不含 `gcloud`、`subprocess`；`jobs.py` 新增的行（`git diff` 的 `+` 行）不含小寫 `station`（`test_scope.py` TC-061 已自動涵蓋整個目錄；這裡只對新增行再釘一次，且不得用拆字；既有 :36 的歷史拆字不動）。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
| 檔:行 | 以前 | 以後 | 理由 |
|---|---|---|---|
| `platform/tests/test_launch_platform.py:606` | `set(jobs.KINDS) == {…六個…}` | 加 `"put_upload"`，註解「byte-channel-a: plus put_upload」 | 工作種類由六個變七個 |
| `platform/tests/test_resume_scope.py:70` | `jobs.KINDS == (…六個…)`（逐字、含順序） | 末尾加 `"put_upload"` | 同上 |
| `platform/tests/test_station_platform.py:319–329` | 資料庫 CHECK 的種類集合＝六個；迴圈插入六種 | 集合加 `put_upload`；插入迴圈加 `("put_upload", None)`；註解「a seventh, put_upload, that needs no confirmation」 | 同上；`("rm","launch","scancel","write_file","")` 的拒絕清單**不動** |
| `platform/tests/test_cloud_cost.py:746–747` | 用 regex 取出 CHECK 清單並逐項比對（六個） | 清單末尾加 `"put_upload"` | 同上；:748 的 `confirmations` 兩種 CHECK 斷言**不動** |

**逐條核對過「不需要改」的（PR 說明要列「沒動」）**
- `test_launch_platform.py:122`（舊表遷移後插入六種）：能過、不改；BA-03 補七種。
- `test_keep_submissions.py`：全檔找不到工作種類清單（:701–705 是 MCP 工具名單）；不改。
- `test_gcb_ce.py:726`、`test_gcb_launch.py:980`（Google Batch 環境被擋的種類迴圈）：`put_upload` 對 Google Batch 環境是**放行**的，所以它不在「被擋」迴圈裡；不改。放行端由 BA-10 與 BA-16 釘住。
- `test_gcb_ce.py:805`（禁字 `buckets create|services enable|service-accounts create|storage rm`）：本任務不寫這些字；不改。
- `test_cloud_upload.py:739`（`storage cp` 只在 `cloud_store.py`）：本任務不新增含它的來源；-b 的代理用 argv 清單（見 -b 裁決 2），不產生這串字；不改。
- `test_run_diag_tools.py:285–330`（舊表遷移）：靠作法 A-3 的「兩個種類都看」仍綠；不改。
- `test_keep_submissions.py:773–774`、`test_resume_scope.py:68–71`／`test_tc161`、`test_cloud_cost.py:748`（確認憑證只有兩種）：本任務不加第三種；不改。
- `test_actions_layer.py` 的 BASELINE／`READ_TOOLS`、各處工具個數、`UNSUPPORTED` 長度：本任務不碰 MCP；不改。
- `test_scope.py` TC-070（新 `.py` 前 40 行要有 `# Nothing existing:` ≥15 字）：新測試檔 `test_byte_channel_a.py` 必須符合——這是新檔的義務，不是更新斷言。

## 完成標準（done when）
- BA-01～BA-29 全綠；`platform/tests/` 全套綠（含上表四處更新、`test_run_diag_tools.py`、`test_cloud_upload.py`、`test_scope.py`、`test_gcb_ce.py`、`test_gcb_launch.py` 原封不動全綠）；`tests/platform_test.sh` 與倉庫既有 CI 綠。
- `git diff --name-only <base>` 只含「範圍：檔案」列的 8 個檔。
- `store.py` 只動 `_JOBS_TABLE` 的一行 CHECK、第 174 行附近註解、`_migrate_jobs_kinds` 的兩處判斷；`jobs.py` 的既有函式只動 `_target`、`clean_result` 與三個常數表，其餘是新增。
- 沒有新依賴；`pyproject.toml`、`constraints.txt` 與基準相同。
- PR 說明含：「需要 migration，理由與範圍」「沒動的既有斷言清單」「與 ADR 0010 的差別（裁決 7）」「確認憑證決定與替代方案（裁決 4）」。
- 回報（bundle）、資料庫、日誌、測試輸出、PR 說明裡搜不到金鑰片段（`grep -r private_key`、站台金鑰檔名）。

## 環境事實
（行號是 origin/v3 的，2026-10-24 讀；`git -C C:\Users\marvi\Desktop\agentic-bioflow\agentic-bioflow_v2 fetch -q origin` 後以 `MSYS_NO_PATHCONV=1 git show origin/v3:<path>` 讀。）
- `platform/abf_platform/jobs.py`：`DEADLINE_SECONDS`:26–27、`_DEADLINE_ENV`:28–33、`KINDS`:39、`CONFIRMED`:41、`_target`:71–104（Google Batch 只准三種的檢查在 :86；`available` 檢查在 :100）、`_insert_job`:107、`_enqueue`:154（只給 preflight／list_site_files 用）、`enqueue_confirmed`:553、`claim`:608–650、`clean_result`:665–717（`else` 分支 :700–716 會保留 `entries`／`path`／`count`）、`take_result`:743–802。第 36 行為了 TC-061 把那個字拆成兩段字串——**本任務不學它**，訊息寫「the agent on the platform host」。
- `platform/abf_platform/store.py`：`_JOBS_TABLE`:232–249（CHECK 在 :236、確認憑證的 CHECK 在 :248）、`STATE_SCHEMA`:176 與 :270、`uploads_root`:301–307（`ABF_PLATFORM_UPLOADS`，預設 `platform.db` 旁的 `uploads`）、`_migrate_jobs_kinds`:402–434、`connect_state`:583–603、`user_id_of`:773。
- `platform/abf_platform/cloud_store.py`（已在 v3）：`parse_gs`:24、`workdir_bucket`:47、`_single`:61（私有）、`upload_prefix`:67、`object_url`:75、`inside_prefix`:80、`big_file_command`:92、`stream_into`:111。
- `platform/abf_platform/compute_envs.py`：`PLATFORM_HOST_TYPES`:35、`snapshot`:687（Google Batch 型只帶 project／location／workDir／serviceAccountEmail／credentialsId）、`view()` 的 `config` 已解析成 dict。
- `receiver.py` 不含任何工作種類字串，`/agent/poll`、`/agent/result/{jid}` 對新種類不必改（`test_run_diag_tools.py:283` 釘路由清單）。
- 使用者上傳的檔放在 `<uploads_root>/<使用者名>/`（`actions/__init__.py:497–510` 的 `caller_area`）；本任務的 `uploads_dir` 參數就是 `store.uploads_root(platform_path)`，由呼叫端（cloud-upload-wire）傳入。
- 憲法掃描：`test_scope.py` TC-061（來源不得含「station」、`ssh`、`sbatch`…）、TC-070、TC-071；`tests/no_second_run_state_test.sh` 另有一條只准 `abf_station/launch.py` 含送出字樣的掃描——本任務不含。
- 查不到：ADR 0010 第 2 點與 Decided 2 都沒有寫「每次確認」的畫面或資料結構（只說 ADR 0006 的確認路徑），所以「確認長什麼樣」沒有現成規格；裁決 4 因此採保守的最小做法並列為開放問題。

## 不做
- 代理端的任何事（讀檔、gcloud、再檢查、回報）→ byte-channel-b。
- 接到網頁／MCP／HTTP 路由／上傳畫面、`actions/__init__.py` 與 `mcp_server.py` 的任何改動 → cloud-upload-wire。
- 第三種確認憑證、`confirmations` 表遷移、`confirm.py` 改動（見裁決 4）。
- 把上傳完的本機檔刪掉或搬走（見裁決 7）；結果保留 30 天提醒、刪 work。
- 校驗和、完整性雜湊、續傳、多檔批次（一個工作＝一個檔）。
- 新依賴；改 `pyproject.toml`／`constraints.txt`；為了過 TC-061 拆字。
- 預檢加「寫入探測」（cloud-upload 待裁決 3：會花一點點錢，要他點頭）。

## 通例：閱卷看 diff 的手動案例（2026-10-24，照 dev-plans/README）
「改動範圍只有上列 8 個檔」「`store.py`／`jobs.py` 既有函式沒被順手改」「既有測試除上表四處外沒動」這類只能看 diff 的案例，不寫進 `docs/TESTING.md`：executor 把 `git diff --stat` 與 `git diff --name-only` 貼進 ledger.md，verifier 依 ledger 並自己重跑核對。verifier 不以「TESTING.md 沒有步驟」退回。

## 裁決（2026-10-24 developer-agent 助理起草；與上文衝突時以本段為準）
1. **新種類叫 `put_upload`，工作只帶參照。** 鍵固定為 `ce`、`owner`、`name`、`size`、`dest`；位元組、本機路徑、金鑰、網址原文都不在裡面。理由：派工指令要求；工作 JSON 會進資料庫與日誌，放位元組或路徑等於把使用者資料與主機佈局寫進去。
2. **`dest` 由平台算、代理再算一次比對，不接受呼叫者傳網址。** 理由：「只准寫 `gs://<workDir bucket>/uploads/<owner>/`」要在兩邊各檢查一次（平台＝`object_url`；代理＝-b 的 `inside_prefix`）。
3. **唯一入口 `enqueue_put_upload`，且必須有 `caller_user_id`，名字必須屬於該 id。** 終端機（`None`）不能排。理由：前綴由名字組成；名字不屬於呼叫者就能寫進別人的前綴。
4. **不加確認憑證種類；使用者「自己在已登入的頁面上選檔、選環境、按上傳」就是這次寫入的那個人的 yes。** 這偏離 ADR 0010 的字面「each time confirmed by a person」與 backend 守則「每個寫入動作都必須經過人工確認管道」，所以列為最高優先的開放問題。理由：①第三種確認要動 `confirmations` 表（外鍵重建）、`confirm.py`、禁區 `actions/__init__.py` 與四處釘住「只有兩種」的測試，遠超本任務；②寫入範圍被三道牆夾住（自己的環境、自己的前綴、自己上傳過的檔、≤2 GB）；③與日後加確認相容：加了也只是在 `enqueue_put_upload` 前面多一道 `_check_confirmation`，鍵不變。**若維護者要求照字面，改法＝另開 byte-channel-c（確認憑證種類、遷移、改四處測試、接頻道），工作量約等於本任務的一半。** verifier 若按守則判 FAIL，請改回報 UNVERIFIED 並引用本裁決，交 developer-agent 決定。
5. **覆寫同名物件允許。** 同一人對同一檔名再傳一次＝取代自己前綴裡的那個物件。理由：①不加 `--no-clobber`（物件已存在時它略過並回傳 0，會讓「寫了幾個位元組」說謊，見 -b）；②範圍只在自己前綴。
6. **平台只 `lstat`，不打開檔案。** 理由：憲法（平台不處理位元組）與 `datasets.py` 的 TC-059 精神一致；大小是「排隊時的快照」，代理開檔時再比一次，不一致就拒（-b）。
7. **與 ADR 0010 Decided 2 的差別（要讓維護者知道）：** ADR 選的是「平台記憶體轉送、完全不落地」；本任務依派工，走「檔案已在平台主機的 `uploads/` 裡」。後果：①平台主機磁碟上暫存著使用者的檔，傳完**不自動刪**（刪除屬 cloud-upload-wire 或清理任務）；②不需要「瀏覽器→平台→代理」的串流端點，也沒有「兩端要同時在線」的限制；③「不落地」這句原話（replan 第 16 點）對這條路不成立。
8. **工作期限預設 3600 秒。** 理由：2 GB 在 5 MB/s 約 400 秒，留 9 倍餘裕；仍可用環境變數縮短。

## 裁決（2026-10-25 01:00，維護者回覆）
維護者原話：「1.會慢半天就不用 2.照你建議」。
A. **確認**：採 -a 裁決 4——使用者在已登入的頁面自己選檔、選環境、按上傳，就是這次寫入的 yes；**不加**確認憑證種類、不開 byte-channel-c。verifier 不因 backend 守則「每個寫入要確認」判 FAIL（維護者已明示接受此偏離）。
B. **暫存**：允許檔案先放在平台主機 `uploads/` 再傳；**傳完且雲端物件大小與本機相同就刪掉本機那份**（取代 -a 裁決 7 ①的「傳完不自動刪」）；大小不符或傳輸失敗則保留並回報。
C. **ADR 0010 同步**：在本系列的 -b 片修改 `docs/adr/0010-chat-keys-byte-channel-studio-embedding.md`，加一段「2026-10-25 修正」：①按上傳即為確認；②允許在平台主機暫存，傳完核對大小後刪除。附維護者原話。
D. 前置：本系列動 `store.py`／`jobs.py` 的 CHECK 清單，與 cloud-cleanup-a/b 重疊，排在 cloud-cleanup-b 之後；開工前依當時 v3 的 CHECK 清單重算（不釘「剛好七個」）。

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
