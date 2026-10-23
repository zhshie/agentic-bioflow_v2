---
id: estimate-su-mcp
title: 接收器記下每個 task 的用量，get_run 帶出 SU 與台幣（Claude Desktop 看得到）
tier: B
kinds: backend
lane: L7-run-facts
base: v3
---

# estimate-su-mcp

> 本檔由 developer-agent 寫（2026-10-23，筆電）、`/supervise` 複製進 worktree 的 `specs/estimate-su-mcp/plan.md`。**只處理本任務**。B 級（使用者看得到的數字）、網頁畫面以外 → verifier 通過＋CI 綠由 developer-agent 自合。
> 與 `failure-cause` 同車道（兩件都改 `actions.get_run` 與 `get_run` 的工具說明），本件先做。

## 目標
讓 Claude Desktop 問一個 run 時，直接看到它用掉多少 SU、約多少台幣——不必再到 WSL 敲 Python。

為什麼不是「新增一個 `estimate_su` MCP 工具」：①現在 `estimate_su` 對任何真實 run 都回「未知」，因為接收器沒存每個 task 的 cpus／realtime／分區（`su.run_tasks` 永遠回 None，`specs/estimate-su/ledger.md` 第 11 行）；只加工具等於做一個永遠回「—」的工具。②新工具沒有網頁路由，會讓 parity 表 OWED 變長，而 OWED 規則是「只准變短」（`docs/ROADMAP.md:96`、`test_web_parity.py::test_tcs07`），放寬它是 C 級。把 SU 放進 `get_run`（網頁與 MCP 共用的那個動作）兩個問題都避開：數字是真的、parity 不動、工具數不變。

## 維護者原話（verifier 出題用）
- 「nano4 開發測試用計畫 mst109178：我自己跑驗收不用再問，但每次先估 SU、跑完記 SU 到驗收表」（10-21 裁示，`developer-agent.md` 決定權三級）——SU 要能從平台查到，不是手算。
- 費用摘要寫法「約 120 SU」（10-18 裁示，`memory/handoff/2026-10-18-web-012-014-answers.md`）——數字是估算，不是帳單。
- 「不要猜」：憲法 IV.9 缺口要明白寫出來（`specs/estimate-su/test-case.md` TC-012）——缺任何一個 task 的欄位，整個 run 的 SU 是 null 並說原因，不是 0。

## 範圍：檔案（最終版，只准改這些）
- `platform/abf_platform/store.py`（index 的 `SCHEMA` 加一張表 `task_usage`）
- `platform/abf_platform/receiver.py`（`apply_progress` 寫入 `task_usage`）
- `platform/abf_platform/su.py`（`run_tasks` 改讀 `task_usage`；新增 `site_of_run`）
- `platform/abf_platform/compute_envs.py`（CE 新鍵 `suSite` 的驗證與 snapshot）
- `platform/abf_platform/actions/__init__.py`（`get_run` 加 `su` 欄；`estimate_su` 改用 `site_of_run`）
- `platform/abf_platform/mcp_server.py`（只改 `get_run` 工具的 description 一句）
- `configs/sites/nchc-nano4-ce.json`（加 `"suSite": "nano4"`）
- `platform/tests/test_su_in_get_run.py`（新）
- `platform/tests/test_actions_layer.py`（只更新 `BASELINE` 裡 `get_run` 的 description，見「允許更新的既有斷言」）
- `platform/tests/test_station_envs.py`（只加 `suSite` 的驗證測試；既有斷言不動）
- `docs/PLATFORM.md`（`get_run` 說明處加一句 `su`；CE 鍵表加 `suSite`）
- `docs/TESTING.md`（TC-048n 第 1 步改成在 Claude Desktop 問 `get_run`，見作法 7）
- `specs/007b-launch/acceptance-nano4.md`（第 44 行那格的說明改成「Claude Desktop 問 get_run 前一次同設定 run 的 su」）
- `specs/estimate-su/ledger.md`（第 11、12 行的「欠」改成已補，寫本任務 id）
- `specs/estimate-su-mcp/ledger.md`（新，executor 的進度帳本）

## 作法
1. **新表**（加在 `store.SCHEMA`，`CREATE TABLE IF NOT EXISTS`）：
   `task_usage (run_id TEXT NOT NULL, task_key TEXT NOT NULL, name TEXT NOT NULL, status TEXT, cpus INTEGER, realtime_ms INTEGER, queue TEXT, PRIMARY KEY (run_id, task_key))`。
   `task_key` 與 `failed_tasks` 同規則：`"%s:%s" % (taskId, attempt)`。
2. **receiver**：`apply_progress` 對 `listed` 裡每個 task，status 是 `COMPLETED` 或 `FAILED` 時 upsert 一列（`ON CONFLICT(run_id, task_key) DO UPDATE` 全欄覆寫）；其他 status（`SUBMITTED`、`RUNNING`、`CACHED`、`ABORTED`…）不寫、也不刪既有列。**每個 attempt 各一列、不因重試刪掉前一次**（前一次也花了 SU；這點與 `failed_tasks` 刻意不同，寫在註解）。`cpus`、`realtime`（毫秒）、`queue` 原樣存；不是數字就存 NULL（用既有 `_int(..., None)`）；`queue` 非字串存 NULL。
3. **su.run_tasks(index_path, run_name)**：唯讀開 index，找 `runs.run_name == run_name` 的 run（同名多個取 `started_at` 最新的，與 `status.find_run` 同規則——直接呼叫 `status.find_run` 取 id），讀它的 `task_usage` 回 `[{name, cpus, realtime, queue}]`（鍵名照 `su_of_tasks` 現在吃的 `cpus`／`realtime`／`queue`）。
   - 表不存在（舊 index 唯讀開時沒有這張表）或該 run 沒有任何列 → 回 `None`（沿用 `NOT_STORED` 原因）。
   - 有列 → 回清單（即使只有部分 task 有列，也回清單；缺欄的 task 由 `su_of_tasks` 判 unknown）。
4. **site 從哪來**：新函式 `su.site_of_run(platform_path, run_name, rates)`：
   - 從 platform.db 的 launches 找該 run 最新一筆的 `ce`，讀該 CE 的 config `suSite`；有 → 回它。
   - 沒有 launch 紀錄、CE 不在、或 CE 沒設 `suSite` → 回 `rates["default_site"]`（現行行為）。
   - `actions.estimate_su` 在 `site is None` 時改呼叫 `site_of_run`（取代直接讀 `default_site`）。呼叫者明給 `site` 時照用（現行 `test_estimate_su.py` 不變）。
5. **CE 鍵 `suSite`**：`compute_envs.py` 第 145 行那組已知鍵加 `"suSite"`；值必須是 `su_rates.json` 的 `sites` 裡有的名字，否則驗證錯誤（一次列出全部錯誤的既有寫法），訊息：`suSite: 費率檔沒有站點 %s；可用的有 %s (no such site in configs/sites/su_rates.json)`。沒給就不出現在 snapshot（與 `modules` 等三鍵同規則）。`configs/sites/nchc-nano4-ce.json` 加 `"suSite": "nano4"`。
6. **get_run 帶 su**：`actions.get_run` 找到 run 且通過擁有者檢查後，加
   `view["su"] = estimate_su(index_path, view["name"], caller=caller, platform_path=platform_path)` 的結果，但只留五個鍵：
   `{"su": float|None, "twd_nstc": float|None, "twd_academic": float|None, "twd": {...}（站點有 twd_per_su 才有）, "unknown_reasons": [str], "site": str}`。
   - 範例（nano4，兩個 task：cpus 2、realtime 1,800,000 ms、queue `ngs92G`；cpus 1、3,600,000、`ngs92G`）：`{"su": 2.0, "twd_nstc": 0.2, "twd_academic": 0.4, "twd": {"nstc": 0.2, "academic": 0.4, "industry": 0.74}, "unknown_reasons": [], "site": "nano4"}`（浮點比較用 `pytest.approx`）。
   - 舊 run（沒有列）：`{"su": None, "twd_nstc": None, "twd_academic": None, "unknown_reasons": ["這個 run 的紀錄沒有保存每個 task 的 cpus、realtime 與分區 …"], "site": "taiwania3"}`。
   - 找不到 run 的回傳形狀**不變**（沒有 `su` 鍵）。
   - running 的 run 也帶（到目前為止已結束的 task 的合計）；不另加「進行中」字樣。
7. **工具說明**：`mcp_server.py` 的 `get_run` description 末尾加一句（英文，照現有文風）：
   `It also has su: the SU the run's finished tasks used and what that costs (an estimate from Nextflow's task records; null with the reasons when a record lacks what the formula needs).`
   `test_actions_layer.py::BASELINE` 的 get_run description 同步改成新字串（**這是有意的更新**，PR 說明寫明）。
8. **文件**：`docs/PLATFORM.md` 在 `get_run` 說明（第 88 行附近的段落與工具清單處）加一句 su；CE 鍵說明加 `suSite`。`docs/TESTING.md` TC-048n 第 1 步改成：「在 Claude Desktop 問 `get_run ampliseq-mt-0920-r2`（或最近一次同設定、由本平台送出的 run），把回答裡的 `su` 整段貼進表格；`su` 是 null 就寫 unknown 加 `unknown_reasons`」，並刪掉「它不是 MCP 工具…在 WSL 用 python -c」那段。
9. **不需要 migration**：只新增一張 `CREATE TABLE IF NOT EXISTS` 表，`store.connect` 每次開檔都執行 SCHEMA，既有 index 下次被接收器打開時自動有這張表；唯讀路徑（status／su）碰到沒有這張表的舊檔回 None（作法 3）。舊 run 不回補（沒有資料可補）。

## 失敗先行測試（`platform/tests/test_su_in_get_run.py`，現在都會紅）
- `test_receiver_keeps_cpus_realtime_queue_of_finished_tasks`：送一個 progress，tasks 有 COMPLETED／FAILED／RUNNING／CACHED 各一 → `task_usage` 只有前兩列，欄位值正確。
- `test_a_retry_keeps_both_attempts`：同一 taskId attempt 1 FAILED、attempt 2 COMPLETED → 兩列。
- `test_get_run_has_su_for_a_nano4_run`：CE `suSite: nano4`，兩個 task（作法 6 範例）→ `get_run(...)["su"]` 等於範例。
- `test_get_run_su_is_null_with_reason_for_an_old_run`：run 沒有任何 `task_usage` 列 → `su` 為 None、`unknown_reasons` 非空、沒有 0。
- `test_old_index_without_the_table_reads_as_unknown`：手建一個沒有 `task_usage` 表的 index（唯讀開）→ `get_run` 不崩、`su.su is None`。
- `test_site_falls_back_to_default_without_suSite`：CE 沒設 `suSite` → `su.site == "taiwania3"`（rates 的 default_site）。
- `test_suSite_must_name_a_site_in_the_rates_file`：`suSite: "nowhere"` → CE 驗證錯誤，訊息含 `suSite` 與可用站點清單。
- `test_another_users_run_has_no_su`：B 呼叫 A 的 run → 與現在一樣是 not found 形狀、沒有 `su` 鍵。
- `test_tool_list_unchanged`：MCP 工具名集合仍是 12 個（與 `test_estimate_su.py::test_tc029` 同一組）。

## 允許更新的既有斷言（其他一律不准動）
- `platform/tests/test_actions_layer.py:34` `BASELINE`：只改 `get_run` 那一筆的 `description` 字串為作法 7 的新字串。
- 確認**不會**變紅、不准改：`test_estimate_su.py`（TC-029 工具集合、TC-030 沒有 su 網頁路由）、`test_pat.py:383/751`、`test_oauth_mcp.py:44`（工具數 12／7 不變）、`test_web_parity.py`（沒有新的公開動作名；`site_of_run` 放在 `su.py`，不放 actions）、`tests/platform_storage_doc_test.sh:140-142`（「seven read-only tools」「Twelve tools.」字樣保留）。

## 完成標準（done when）
- Claude Desktop 問 `get_run <nano4 上由平台送出、已結束的 run>` → 回答有 `su` 數字與三種台幣（手動，TESTING.md TC-048n 第 1 步）。
- 自動：上面九個測試綠；全套綠；工具數仍 12。

## 環境事實
- Nextflow 的 task 事件帶 `cpus`、`realtime`（毫秒）、`queue`（Slurm 分區；本機執行是 null）——見 `platform/tests/fixtures/payloads/*.json`。
- nano4 費率：`configs/sites/su_rates.json` 的 `sites.nano4`（`ngs*` 係數 1、`big-mem*` 係數 7；台幣 0.1／0.2／0.37）。
- `status.py` 以唯讀開 index（`_open_readonly`），不能在唯讀路徑建表。
- `actions/__init__.py:96` 現有 `estimate_su` 簽名不變。

## 不做
- 不新增 MCP 工具、不加網頁路由或畫面（012d 費用頁再接）；不改 `list_runs`。
- 不改 `rebuild.py`（`trace.txt` 預設欄位沒有 cpus／queue，重建的 run 照舊回 unknown）。
- 不做月總計的畫面；`month_total` 不改。
- 不做雲端費用。

## 裁決（2026-10-23，預檢後；與上文衝突時以本段為準）
1. **避免循環 import**：`su.py` 在模組層 import `jobs`，`jobs` import `compute_envs`。所以 `compute_envs.py` 驗證 `suSite` 時**在函式內**才 `from . import su` 並呼叫 `su.load_rates()`（不在模組層 import）。費率檔讀不到時，`suSite` 驗證錯誤訊息改成 `suSite: 費率檔讀不到，無法確認站點 %s (the rates file cannot be read)`。
2. **`suSite` 不進 snapshot**（站台代理用不到）；範圍裡 compute_envs 那行只指「驗證」。`compute_envs.py:575-584` 的 snapshot 不動。
3. **`specs/007b-launch/acceptance-nano4.md` 第 44 行**：表頭字樣「launch 前預估 SU」必須保留（`tests/docs_nano4_acceptance.sh:27` 的 TC-013 釘住），只改它後面括號裡的說明文字。「允許更新的既有斷言」不變（不改那支測試）。
4. **形狀**：`get_run` 的 `su` 有五個固定鍵＋一個條件鍵：固定 `su`、`twd_nstc`、`twd_academic`、`unknown_reasons`、`site`；`twd` 只在站點有 `twd_per_su` 時才有。`site` 型別是 `str | None`（費率檔讀不到時 None，同時 `unknown_reasons` 說明費率檔讀不到）。
5. **platform_path**：`su.site_of_run` 由 `actions.estimate_su` 呼叫時傳 `platform_path_for(index_path, platform_path)`（與 `get_run` 現有寫法相同）；platform.db 不存在或打不開 → 回 `rates["default_site"]`，不丟例外。
6. **還沒結束的 run 不給數字**（「不要猜」）：status 是 `running` 或 `lost` → `su` 三個數字為 None，`unknown_reasons == ["run 還沒結束，SU 等它結束後再算 (the run has not ended)"]`。已結束的 run：`task_usage` 裡 status `COMPLETED` 的列數少於 `view["tasks"]["succeeded"]` → 數字為 None，原因 `"有 %d 個成功的 task 沒有用量紀錄 (%d succeeded tasks have no usage record)"`。作法 6「running 也帶合計」一句作廢。新增測試 `test_running_run_has_no_su_number` 與 `test_missing_usage_rows_make_su_unknown`。
7. 「舊 run」範例的 `site: "taiwania3"` 只在該 run 沒有 launch 紀錄時成立；有 nano4 launch 的舊 run 回 `nano4`（測試照此寫）。
8. 新測試與文件不得出現 `/work/<真實帳號>/` 形式的路徑（`tests/no_hardcoded_paths.sh`），用 `<site_user>`。

## 裁決補充（2026-10-23）：新檔的檔首標頭
新的 `.py` 檔（含測試檔）前 40 行內要有 `# Nothing existing: <理由，≥15 字>`（`platform/tests/test_scope.py:75-80` TC-070），否則全套會紅。

## 裁決（2026-10-24 01:40，developer-agent，回應 executor BLOCKED）
- 核可修改 `platform/tests/test_failures.py:193`（#166 合併進 v3 的既有斷言）一行：`if k != "failure"` 改成 `if k not in ("failure", "su")`。理由：本計畫 TC-010 讓 get_run 多一個 `su` 鍵，該斷言的本意是「get_run 只比 status.get_run 多出動作層補的欄位」，`su` 屬於同類。ledger 記「以前／以後／理由」。範圍檔清單加 `platform/tests/test_failures.py`（只限這一行）。
- 全套只剩 `tests/init_workspace_test.sh` 的「site side with no run area known」一條紅且 base 同紅時，視同全綠（另案 init-workspace-hermetic 修）。

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
