---
id: 017c2a-validate-lint
title: 驗證組合的第二道：經站台代理對組合出來的專案跑 nf-core 的 lint（只做 lint；空跑 -stub-run 與 nf-test 不在這張）
tier: B
kinds: backend
lane: L44-validate-lint
branch: feat/017c2a-validate-lint
base: v3
source: 017c-validate.md 裁決 2、11（動態檢查延後為「站台側另一張票」）；developer-agent 2026-11-03 裁決（本檔「## 裁決」）。維護者沒有針對 lint 的逐字原話
---

# 017c2a-validate-lint

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/017c2a-validate-lint/plan.md`。**只處理本任務**。
> **前置**：PR #178（017c-validate）、#173（017b-compose）、#288（pipeline-export-zip）已在 v3。`validate.py` 的靜態檢查**一個字都不改**。

## 目標
使用者（或 Claude）驗證一個已存的組合時，可以選擇再叫站台代理對「這個版本組出來的專案檔」跑一次 `nf-core pipelines lint`，結果（通過／未通過／沒裝工具／出錯，加報告）存在這個版本的驗證紀錄裡，之後 `get_validation` 讀得到。預設不跑，現有行為與測試不變。

## 維護者原話（verifier 出題用）
- 維護者**沒有**針對 lint 說過逐字原話。以下是 developer-agent 的指示與總表引文，不得當成「維護者已確認」。
- 總表 017c 原文（replan 第 157 行，經 017c-validate.md 第 23 行引用）：「done：三閘門結果顯示在版本頁；lint 失敗的版本不能 launch。」→ 本任務只交出「lint 結果的資料」；**不改 launch 的擋法**（`pipeline_launch.prepare` 仍只看靜態檢查），「lint 失敗不能 launch」與版本頁顯示留給後續票（見不做）。
- 常設（10-23）：「跟Seqera platform一樣的模式，不要自己定義」→ 沿用既有「平台排工作給站台代理、不等待、之後再讀」的路（同 `pipeline_files`、`read_run_file`），不自創傳輸。

## 範圍：檔案
平台側
- `platform/abf_platform/jobs.py`：`DEADLINE_SECONDS["lint_pipeline"] = 300`、`_DEADLINE_ENV["lint_pipeline"] = "ABF_PLATFORM_DEADLINE_LINT_PIPELINE"`；docstring「Ten kinds exist」改 eleven 並用反引號點名 `lint_pipeline`（`test_job_kinds_docs` 逐個檢查）；`_enqueue` 對 `lint_pipeline` 照 `pipeline_files` 拒絕（只能走專用入口）；新增 `enqueue_lint_pipeline(state_path, name, version, project, *, compute_env=None, clock=time.time, deadline_seconds=None, offline_after=None, caller_user_id=None)`；`pick_environment` 加關鍵字參數 `kind="pipeline_files"`（預設行為不變）；`clean_result` 加 `lint_pipeline` 分支（作法 4）。
- `platform/abf_platform/store.py`：`_JOBS_TABLE` 的 CHECK 加 `'lint_pipeline'`；`_jobs_kinds_current` 名單加 `"lint_pipeline"`（舊 platform.db 由 `_migrate_jobs_kinds` 重建表）；第 176 行註解「exactly ten job kinds」→ eleven（`test_store_comment_counts_the_job_kinds`）；`_migrate_jobs_kinds` docstring 補名字。
- `platform/abf_platform/pipeline_lint.py`（新檔，檔頭 `# Nothing existing: …`，TC-070）：`request(...)`、`collect(con, row)`、`ensure_columns(con)`。**不 import subprocess、不啟動任何程式**（TC-071）。
- `platform/abf_platform/actions/pipelines.py`：`validate_pipeline(..., lint=False, compute_env=None)`；`_table` 結尾呼叫 `pipeline_lint.ensure_columns`；`get_validation` 讀取時呼叫 `pipeline_lint.collect`；把匯出 zip 組檔案那段（#288 `export`）抽成私有 `_project_files(...)` 讓 lint 共用，**匯出輸出一個位元組都不變**。`CREATE TABLE IF NOT EXISTS pipeline_validations` 文字**不改**（新欄位只靠 ALTER）。
站台側
- `platform/abf_station/lint.py`（新檔，檔頭 `# Nothing existing: …`）：`ARGS = {"name", "version", "project"}`、`run_lint(job, ctx)`。
- `platform/abf_station/handlers.py`：`JOB_KINDS` 末尾加 `"lint_pipeline"`、`ARG_KEYS`、分派；第 1 行註解「ten job kinds」→ eleven（`test_handlers_header`）。
測試與文件
- 新測試：`platform/tests/test_pipeline_lint.py`、`platform/tests/test_station_lint.py`。
- `docs/PLATFORM.md`（工作種類表、`### Validation` 補「可選的 lint」、環境變數 `ABF_PLATFORM_DEADLINE_LINT_PIPELINE` 補在第 906 行那段）、`docs/TESTING.md`（末尾新增手動一節）。
- **不碰**：`web.py`、`web_board.py`、`mcp_server.py`、`chat_tools.py`、`guidance.py`、`compute_envs.py`。

## 作法
1. **觸發**：`validate_pipeline(platform_path, pipeline_id, version=None, *, caller=None, data=None, clock=time.time, lint=False, compute_env=None)`。`lint` 必須是 `True`／`False`，其他型別回 `_no(...)` 且什麼都不做。`lint=False` 時回傳與寫入與現在逐位元相同。`lint=True`：先照舊做靜態檢查並存下，再呼叫 `pipeline_lint.request`。回傳多一個鍵 `lint`：排入＝`{"state": "queued", "job_id": <int>}`；被拒（無在線代理、專案檔過大等）＝`{"state": "refused", "message": <白話原因含處理方式>}`，**靜態結果照存、外層 `ok` 仍為 True**。目前沒有 MCP 工具或網頁會傳 `lint`：**本片只到動作層**。
2. **工作內容**：`enqueue_lint_pipeline` 的 args 為 `{"name", "version", "project": {相對路徑: 文字}}`。專案檔用 `_project_files` 組（與匯出 zip 同一份），總位元組 ≤ `pipeline_launch.MAX_BYTES`、檔數 ≤ `MAX_FILES`，超過＝`refused`。選環境：`compute_env` 有給＝只試它；沒給＝呼叫者名下第一個可用的（`pick_environment(..., kind="lint_pipeline")`，同 `pipeline_files`）。工作不需確認（唯讀、不花錢）。
3. **結果存放（裁決 b）**：`pipeline_validations` 加四個可為 NULL 的欄：`lint_status TEXT`（`queued`／`passed`／`failed`／`unavailable`／`error`／`expired`）、`lint_report TEXT`（≤ 8000 字元）、`lint_job_id INTEGER`、`lint_at REAL`。此表**不在 `STATE_SCHEMA`**（由 `_table` 隨用隨建），沒有 store migration 可套：`ensure_columns(con)` 用 `PRAGMA table_info` 找缺欄再 `ALTER TABLE … ADD COLUMN`，可重複呼叫、舊列不動（NULL＝沒跑過）。**既有 `INSERT OR REPLACE` 會洗掉 lint 四欄**：改成「列已存在就只 UPDATE 原本六欄，不存在才 INSERT」。
4. **收結果（不等待）**：無背景程式。`get_validation` 讀到 `lint_job_id` 非 NULL 且 `lint_status == "queued"` 時，`collect` 查該 `jobs` 列：`queued`／`claimed`＝維持；`done`＝取 `clean_result` 清過的結果寫進四欄；`refused`／`error`＝`error`（`lint_report` 放白話原因）；`expired`＝`expired`。之後不再查。回傳的 `validation` 只在 `lint_job_id` 非 NULL 時多鍵 `lint`：`{"status", "report", "linted_at"}`；沒跑過＝**沒有這個鍵**（既有 `validation == v` 比對不變）。`clean_result` 的 `lint_pipeline` 分支只留 `status`（五值之一，其他＝`error`）、`reason`（≤ 200）、`report`（≤ 8000）、`counts`（`passed`／`warned`／`failed`，0 到 100000 整數）。
5. **站台 `lint.run_lint`**：(a) 驗 `project` 每個路徑：相對、無 `..`、無開頭 `/`、無 NUL、≤ 512 字元，總量與檔數不超上限；不合＝`refused`。(b) `WHICH("nf-core")`（模組層 `WHICH = shutil.which`，測試可換）找不到＝`done` 加 `{"ok": False, "status": "unavailable", "reason": "這台站台沒有安裝 nf-core tools，所以沒有執行 lint；本系統不會自動安裝 (nf-core tools is not installed on this station; nothing is installed for you)"}`，**不安裝、不下載、不開網路**。(c) 檔案寫進 `tempfile.TemporaryDirectory()` 下新資料夾（0700），用模組層 `RUN = subprocess.run` 跑 `["nf-core", "pipelines", "lint", "--dir", <dir>, "--json", <dir 外的 json 檔>]`，`timeout=240`、`shell=False`、環境只留 `PATH`、`HOME`、`LANG`。**在代理自己的主機上直接跑，不經 sbatch／srun／ssh**。(d) 逾時或崩潰＝`error` 加白話 `reason`（不含堆疊與暫存路徑）；JSON 讀得出＝`failed` 數 0 → `passed`，否則 `failed`，`report` 為前 50 條「檢查名：訊息」，`counts` 三個數字；JSON 讀不出＝回傳碼 0 → `passed`，非 0 → `error`（視同崩潰），`report` 放標準輸出末 40 行（截到 8000 字元）。(e) 離開前暫存資料夾必刪（含例外）。
6. **不加進雲端清單**：`CLOUD_JOB_KINDS` 不加 `lint_pipeline`，雲端類環境代理被 `_target` 拒絕（`pick_environment` 跳過），只有 Slurm 型（nano4）接。理由：不動 `test_azure_launch.py:985`、`test_k8s_launch.py:805`、`test_k8s_ce.py:733`；日後放寬是加法。
7. **不改**：`validate.py`、`pipeline_launch.py`、`compose.py`、`catalogue.py`、launch 擋法、任何 MCP 工具或網頁路由、`CHAT_SYSTEM_PROMPT`。`validate()` 回的 `checks`（`["static"]`）不變。

## 失敗先行測試（先寫、現在會紅）
夾具：平台側沿用 `test_pipelines_validation.py`、`test_pipeline_files_queue.py`；站台側沿用 `test_station_pipeline_files.py` 的 `station_harness.FakePlatform`／`FakeSite`、`test_station_fakeplatform.agent_on`。**不跑真 nf-core、不連真站台**；`lint.RUN`、`lint.WHICH` 一律換假的，autouse 守門：忘了換就失敗。
`test_pipeline_lint.py`
- `test_lint_off_changes_nothing`：不傳 `lint` 時回傳、`jobs` 列數、`pipeline_validations` 欄位（除新增四欄）與先前相同；`validation` 無 `lint` 鍵。
- `test_lint_true_queues_exactly_one_job`：恰多一列 `lint_pipeline`，args 的 `project` 與匯出 zip 檔案集合相同，`lint_job_id` 等於該列 id，`lint_status == "queued"`，靜態結果已存。
- `test_lint_flag_must_be_a_bool`：`"yes"`、`1`、`None` 都 `ok: False`，不排工作。
- `test_no_agent_online_is_a_refusal_not_an_error`：`lint.state == "refused"`、`message` 含「代理」，外層 `ok` True，靜態已存，jobs 不增。
- `test_cloud_environment_is_skipped`：只有 GCB 環境＝`refused`；GCB 加在線 Slurm 型＝排到 Slurm 型。
- `test_compute_env_of_somebody_else_is_not_found`：別人的 `compute_env` 與不存在同一句，不排工作。
- `test_someone_elses_pipeline_is_not_found_and_nothing_queued`：他人組合與不存在同一句，jobs 與 validations 不變。
- `test_too_big_project_is_refused`：縮小 `MAX_BYTES` 測，`refused`、不排工作。
- `test_result_is_collected_lazily`：`queued`／`claimed` 時讀到 `queued`；假站台完成後（`failed`、`report`、`counts`）再讀＝四欄已寫；再讀不再查 jobs（計數器）。
- `test_each_terminal_state`：`unavailable`、`error`、`refused`、`expired` 各對應 `lint.status`，`report` 白話。
- `test_clean_result_bounds`：超長 `report`（20000）、`counts` 帶字串或負數、多餘鍵、不合法 `status`＝截斷／丟棄／`error`。
- `test_revalidate_keeps_lint`：已有結果後再呼叫不帶 `lint` 的 `validate_pipeline`，結果仍在。
- `test_old_table_gets_the_columns`：先建六欄舊表並塞一列，`get_validation` 後多四欄、舊列無 `lint` 鍵、資料不變；呼叫兩次不報錯。
- `test_old_jobs_table_is_migrated`：沒有 `lint_pipeline` 的舊 `jobs` 表（仿 `test_nfcore_catalogue.py:323`），開啟後可排；列與 id 不變。
- `test_lint_pipeline_cannot_be_queued_by_the_generic_door`：`jobs.enqueue(..., "lint_pipeline", …)` 拒絕並指向專用入口。
- `test_no_web_or_mcp_surface_got_a_lint_argument`：`mcp_server.py`、`web.py` 原始碼不含 `lint`；MCP 工具名單與數量不變。
- `test_platform_modules_start_no_program`：`pipeline_lint.py`、`pipelines.py` 不含 `subprocess`、`os.system`、`sbatch`、`nextflow`、`stub`。
- 回應與日誌不含 token／密鑰／`platform.db`／堆疊（沿用既有洩漏掃描）。
`test_station_lint.py`
- `test_not_installed_is_unavailable`：`WHICH` 回 None＝`unavailable`，`reason` 含「不會自動安裝」，`RUN` 零次呼叫。
- `test_passed_and_failed_from_json`：`failed: 0`＝`passed`；有失敗＝`failed`，`counts` 正確，`report` 最多 50 條。
- `test_command_is_exact`：argv 恰為 `["nf-core", "pipelines", "lint", "--dir", <暫存>, "--json", <檔>]`，`shell` 非 True，`timeout <= 240`，`env` 只有 `PATH`、`HOME`、`LANG`；argv 不含 `sbatch`、`srun`、`ssh`、`nextflow`。
- `test_timeout_and_crash_are_errors`：`TimeoutExpired`、`OSError`、非 0 且 JSON 讀不出，依作法 5(d)；訊息不含暫存路徑與堆疊。
- `test_files_written_and_removed`：內容與 `project` 相同；跑完（含例外）暫存資料夾不存在。
- `test_bad_paths_are_refused`：`../x`、`/etc/passwd`、`a\x00b`、513 字元、超量＝`refused`，`RUN` 未呼叫。
- `test_handlers_register_the_kind`：`JOB_KINDS[-1] == "lint_pipeline"`、`ARG_KEYS["lint_pipeline"] == {"name", "version", "project"}`、多餘參數被拒；與 `jobs.KINDS` 集合相同。
- `test_station_source_has_no_cluster_submission`：`abf_station/lint.py` 不含 `sbatch`、`srun`、`ssh`、`pip`、`conda`、`install`、`urllib`、`requests`。
- 端到端（假平台）：`agent.run_once` 領到工作並回報＝`jobs` 列 `done`，之後 `get_validation` 讀得到。

## 被釘住的既有測試（`git grep` against origin/v3；改動只限下列、斷言語意只增不減）
- **工作種類名單與順序**（末位加 `lint_pipeline`，切片位置順延）：`test_byte_channel_b.py:183-184`、`test_nfcore_catalogue.py:81` 與 `:323`、`test_station_clean.py:292-293`、`test_station_pipeline_files.py:127-134`、`test_byte_channel_a.py`（開工先 `git grep -n "DEADLINE\|KINDS" platform/tests/test_byte_channel_a.py` 確認）。
- **數量與文字類**：`test_job_kinds_docs.py`（不改測試；靠 `jobs.__doc__`、store 註解「exactly eleven job kinds」、CHECK 清單三者一致）、`test_handlers_header.py`（靠第 1 行註解）、`test_env_vars_documented.py`、`test_launch_docs.py`（環境變數寫進 `docs/PLATFORM.md`）。
- **驗證類**：`test_pipelines_validation.py:78`（欄位清單加四個新欄名）、`:208-212`（`test_no_program_is_started_by_validation`：掃 DDL 段加 `def validate_pipeline` 到檔尾，`lint` 參數會命中；**只把 `"lint"` 從字單拿掉**，`subprocess`、`os.system`、`sbatch`、`nextflow`、`stub` 照舊）。`test_validate.py:449` 掃 `validate.py`，不碰。
- **跑一次確認，不應需改**：`test_pipeline_export.py:217`、`test_mcp_canvas_read.py:138`（傾印 `pipeline_validations`；若有逐欄名斷言再列入 ledger）、`test_pipeline_launch.py:508-533`、`test_azure_launch.py:985`／`test_k8s_launch.py:805`／`test_k8s_ce.py:733`（因作法 6 不應變）、`test_scope.py`（TC-061、TC-071）、`test_aws_upload.py:684`／`test_azure_upload.py:757`（migration 名單）。
- 開工前再跑：`git -C <repo> grep -n "read_run_file\|pipeline_files" origin/v3 -- platform/tests | grep -i "KINDS\|DEADLINE\|\[-\|\[:"`，補列遺漏的名單／順序／數量類釘子。

## 完成標準（done when）
- 新測試與所有被釘住的既有測試（只做上列修改）全綠；`tests/run_all.sh --timeout 900` 綠。
- 舊 platform.db（無 `lint_pipeline`、`pipeline_validations` 無 lint 欄）開啟後自動升級，既有列與 id 不變（測試證明）。
- `docs/PLATFORM.md`、`docs/TESTING.md` 更新；ledger 逐條列被改的既有斷言與 `git diff --stat`；PR 說明寫明：無 UI 變更、無 MCP／網頁新參數、為何沒有 store migration（表不在 `STATE_SCHEMA`，用 `ensure_columns`）、`jobs` 表 CHECK 有 migration、與總表 017c 的差異（lint 不擋 launch）。
- 手動（`docs/TESTING.md` 新一節「組合的 lint (017c2a)」，維護者自己做，ledger 記「未驗證」直到他做）：在 nano4 代理主機確認 `nf-core --version`；對一個存好的組合在 Python 呼叫 `validate_pipeline(..., lint=True)`，等站台跑完再 `get_validation` 看 `lint.status` 與 `report`；再把 `nf-core` 移出 `PATH` 重做，確認得到 `unavailable` 而不是安裝動作。

## 環境事實
- 目前無任何 lint 程式碼；站台檢查外部工具的慣例是模組層 `shutil.which`（`gcb_preflight.py:114`、`k8s_launch.py:81`、`put_upload.py:192`）。
- 工作種類現有十種（`jobs.KINDS = tuple(DEADLINE_SECONDS)`）；新種類要同時改 `DEADLINE_SECONDS`、`_DEADLINE_ENV`、`store._JOBS_TABLE`、`store._jobs_kinds_current`、`handlers.JOB_KINDS`／`ARG_KEYS`。最近範本：`jobs.enqueue_pipeline_files`、`pick_environment`、`clean_result` 的 `pipeline_files` 分支、`abf_station/pipeline_files.py`、`test_station_pipeline_files.py`。
- `pipeline_validations` 由 `actions/pipelines._table(con)` 以 `CREATE TABLE IF NOT EXISTS` 建立；`test_pipelines_validation.py:172-177` 證明它不在 `store.STATE_SCHEMA`，表被刪後會重建。
- 匯出 zip 檔案組裝在 `actions/pipelines.py` 約第 240-262 行；上限 `pipeline_launch.MAX_BYTES = 2 MiB`、`MAX_FILES = 2000`。
- 本機工具：JSON 只用 `node` 與 `jq`；`python3` 是商店空殼。

## 不做
- `-stub-run`、nf-test（後續票 `017c2b-validate-stubrun`，需先決定能否在代理主機跑 nextflow）。
- 「lint 失敗的版本不能 launch」（`pipeline_launch.prepare`）、版本頁顯示 lint 結果（017e，要動 `web.py`）、MCP／網頁上的 `lint` 參數或新工具。
- 自動安裝 nf-core tools、雲端類環境代理跑 lint、把 lint 放進 `validate()` 的 `checks`。
- 通知使用者、背景輪詢（只在 `get_validation` 讀取時收）、修剪舊 lint 結果。

## 待確認（給 developer-agent；都不擋開工）
1. **「cached checkout」不存在**：v3 上組合只有 `compose.render` 組出的檔案。本計畫改為「平台把專案檔放進工作 args，站台寫進暫存資料夾跑、跑完刪」。
2. **「擁有組合的計算環境」不存在**：組合表無環境欄。本計畫用「呼叫者名下、代理在線的環境，可由 `compute_env` 指定」，並排除雲端類（作法 6）。
3. `nf-core pipelines lint` 對組合出的專案多半不會全過（檢查 nf-core 範本檔），`failed` 可能是常態、報告雜訊多；本片只存，不依它擋任何事。
4. `lint` 結果鍵只在跑過時出現（不是 `lint: None`），以免破壞既有 `validation` 相等比對；若要明確「沒跑過」，會牽動 `test_pipelines_validation.py` 與 fixtures。
5. `get_validation` 讀取時會寫入（收結果），原本純讀；寫的是平台自己的資料庫，無新權限，請閱卷留意。
6. 多了 `lint_job_id`、`lint_at` 兩欄（裁決只列狀態與報告），收結果需要。

## 裁決
2026-11-03，developer-agent（原文照錄）：
(a) Job kind name `lint_pipeline`. Trigger: the existing 017c validate action gains an opt-in `lint` flag (default off, so current behaviour and tests are unchanged); when set, the platform enqueues one `lint_pipeline` station job for that pipeline. No web UI change in this slice (MCP/CLI reach it through the existing validate path only if that path already exposes options; otherwise action layer only).
(b) Results go into the existing `pipeline_validations` table: add nullable columns for lint status and lint report (follow the repo's existing migration pattern; old rows read as "not linted").
(c) Runs on the station that owns the pipeline's compute environment, as a short job on the agent host itself (never sbatch / never a cluster submission). Command `nf-core pipelines lint` against the pipeline's cached checkout. If nf-core tools is not present in the station environment, the job finishes with status `unavailable` and a reason string — it never installs anything.
Tests must use the repo's fake station / fake job runner; no real HPC. Keep files out of web.py and web_board.py.
（與文字有出入之處見「## 待確認」1、2、4：這張表不在 `STATE_SCHEMA`，沒有現成 migration 模式可套，改用 `ensure_columns`。）

2026-11-03 developer-agent 追加（看過「待確認」後）：
1. 「待確認」1～6 全部照計畫的作法，視為定案，verifier 依此出題、不以這幾點退回。
2. `docs/TESTING.md` 同時被 L33（resume-edit-web）改：本件只在相關段落**末尾新增**行、不改既有行；push 前 `git merge origin/v3`，衝突兩邊新增都留。


2026-11-03 developer-agent 追加（回應 verifier 出題時的疑問）：
3. 回傳碼非 0 且 JSON 讀不出＝`error`（已改作法 5(d)）；回傳碼 0 且 JSON 讀不出＝`passed`。
4. `counts` 不另存欄位、不另加回傳鍵：平台寫 `lint_report` 時，第一行固定為「通過 X／警告 Y／失敗 Z (passed X / warned Y / failed Z)」，其後才是逐條訊息；所以使用者從 `report` 讀得到數字。`test_result_is_collected_lazily` 的「四欄」指 lint_status、lint_report、lint_job_id、lint_at。
5. 同一版本再送一次 `lint=True`：以最新一次為準——覆寫 `lint_job_id`、`lint_status` 回 `queued`、清空 `lint_report`；舊工作的結果之後不再讀（不取消舊工作）。
6. lint 工作不需人工確認、`get_validation` 會寫平台自己的資料庫：我確認可以（只讀管線檔、在代理主機跑、不花錢、不送 HPC）。verifier 照此出題，不以專長守則字面退回。

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
