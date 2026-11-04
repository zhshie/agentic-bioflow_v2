---
id: pipe-reg-store
title: 管線登記紀錄表與狀態機（動作層，先不接檢查與測試）
tier: B
kinds: backend
risk: M
lane: L-pipereg-core
branch: feat/pipe-reg-store
base: origin/v3@e7a2991c；開工前 `git fetch` 並重查行號
depends: launch-test-profile 合併進 v3（同改 `actions/__init__.py`，避免衝突）
source: 維護者 2026-11-04 新需求；設計 `memory/handoff/2026-11-04-pipeline-registration-design.md`
---

# pipe-reg-store

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/pipe-reg-store/plan.md`。**只處理本任務**。草稿（dev-planner 2026-11-04），登進佇列前由 developer-agent 核對。

## 目標
新增一張「管線登記紀錄」表與一組動作層函式，記下「哪個運算環境、哪條管線、哪個版本、目前在登記流程的哪一步」。對使用者的意義：nano4 與雲端的「新增管線」從此是同一筆紀錄、同一組狀態，之後的檢查、測試、畫面都掛在它上面。

## 維護者原話（verifier 出題用）
- 2026-11-04：「在我的平台中，『新增管線』在 nano4 與雲端伺服器的概念我希望都一樣，不管各自是不是要預先下載還是不用，登記就是從 nf-core 裡面選所有的 pipeline，有些可能是 nano4 有預先安裝，有些可能沒有。後面經過安裝、test sample 跑過等等流程之後才顯示登記成功，可以在跑 pipeline 時選擇。」
- 2026-11-04：「我要已安裝的管線都是有經過你使用內建測試資料測試過的，這邊只是額外顯示讓使用者做額外測試。」
- 既有裁示（前端 session 11-04）：雲端與 nano4 的新增表單相同，只差運算環境下拉選單；表單三欄：運算環境、管線、版本。
- 專案安全底線（ADR 0006）：每個寫入都經人工確認管道；未確認不改變資料。

## 範圍：檔案（只准改這些）
- 新檔 `platform/abf_platform/actions/registrations.py`（資料表、狀態推導、函式本體）
- `platform/abf_platform/actions/__init__.py`（只加匯出與薄包裝，仿 `actions/pipelines.py` 的接法）
- 新檔 `platform/tests/test_pipeline_registrations.py`
- 既有「動作清單」測試只准加新名稱（見「允許的斷言變動」）
- **不准碰**：`compute_envs.py`、`store.py`、`abf_station/`、`web*.py`、`mcp_server.py`、`cli.py`、`jobs.py`。

## 作法
- **資料表** `pipeline_registrations`，放平台狀態資料庫（與 `compute_envs`、`jobs` 同檔），首次使用時 `CREATE TABLE IF NOT EXISTS`（先例：`actions/pipelines.py` l.5、l.21，不放進 `store.STATE_SCHEMA`）。表名不得用 `pipelines`／`pipeline_versions`／`pipeline_validations`（組合管線已用）。
  - 欄位：`id INTEGER PRIMARY KEY`、`owner TEXT NOT NULL`、`compute_env TEXT NOT NULL`、`pipeline TEXT NOT NULL`、`revision TEXT NOT NULL`、`source TEXT NOT NULL CHECK (source IN ('site-module','site-fetch','remote'))`、`stage TEXT NOT NULL CHECK (stage IN ('checking','preparing','awaiting_test','testing','failed','removed'))`、`check_job INTEGER`、`test_run TEXT`、`failed_step TEXT CHECK (failed_step IS NULL OR failed_step IN ('check','prepare','test'))`、`reason TEXT`、`created_at REAL NOT NULL`、`updated_at REAL NOT NULL`、`tested_at REAL`；`UNIQUE (owner, compute_env, pipeline, revision)`。
- **對外狀態** `state`（推導，不存）：`checking`／`preparing`／`awaiting_test`／`testing`／`registered`／`failed`。本片 `testing` 一律原樣回傳（測試結果推導在 `pipe-reg-test-run`）；預留函式 `_state(row, run_status)`，`run_status` 為 None 時回 `stage`。
- **名稱與版本驗證**：沿用 `_SP_NAME`（`^nf-core/[a-z0-9][a-z0-9-]{0,63}\Z`）與 `compute_envs` 的版本規則；壞值回 `{"ok": False, "field", "message"}`，訊息點名欄位。
- **`source`**：計算環境為 slurm-platform → 先記 `site-module`（`pipe-reg-check` 發現無模組時改 `site-fetch`）；其餘（googlebatch／aws／azure／k8s）→ `remote`。`preparing`／`site-fetch` 本片只進 CHECK 與狀態清單，行為在 `pipe-reg-nano4-fetch`（維護者 11-04 題 3 定案：nano4 無模組的管線由平台自己取得）。
- **函式**（簽名照抄，全部依 `caller` 篩擁有者，別人的環境一律當不存在，沿用 `_SP_NOT_FOUND`）：
  - `list_pipeline_registrations(platform_path, *, ce=None, caller=None)` → `{"ok": True, "items": [...]}`；每筆 `{compute_env, pipeline, revision, source, state, reason, failed_step, test_run, tested_at, updated_at}`。**舊資料合併**：呼叫者 slurm 環境 `sitePipelines` 裡有、表裡沒有的項目，以 `state="awaiting_test"`、`source="site-module"`、`legacy=True` 一併回傳（只讀時合併，不寫表）。`removed` 不回傳。
  - `propose_pipeline_registration(platform_path, *, ce, pipeline, revision, confirmed_by=None, caller=None)`：`_require_human(confirmed_by)` 先行；建紀錄 `stage='checking'`。已存在且非 `removed` → `{"ok": True, "changed": False, "state": ...}`；`removed` → 改回 `checking`。本片**不排檢查**，留掛點 `_start_check(env, row)`（本片為空函式，回 `None`）。
  - `remove_pipeline_registration(platform_path, *, ce, pipeline, revision, confirmed_by=None, caller=None)`：標 `removed`；本片不碰 `sitePipelines`（nano4 同步移除在 `pipe-reg-check`）。
  - `list_registered_pipelines(platform_path, *, ce, caller=None)` → 只回 `state=="registered"`。本片永遠回空清單（`legacy` 項目不算已登記）。
- **不需要 migration**：新表首次使用時建立、不改既有表；舊的 `sitePipelines` 以讀時合併呈現，不搬資料。理由寫進 ledger。
- 錯誤訊息白話、雙語（仿 `_SP_NOT_FOUND` 的「中文 (english)」格式）。

## 失敗先行測試
新檔 `platform/tests/test_pipeline_registrations.py`（用既有 `w` 夾具與兩位使用者 token），先寫、改前確認紅、紅輸出貼 ledger：
- `test_propose_creates_checking_row`：確認後回 `ok`，清單一筆 `state=="checking"`、`source=="site-module"`（slurm 環境）。
- `test_propose_on_cloud_env_is_remote`：googlebatch 環境 → `source=="remote"`。
- `test_unconfirmed_propose_and_remove_change_nothing`：`confirmed_by=None` 拋出且表行數不變（確認管道）。
- `test_second_user_cannot_read_or_write`：第二位使用者讀清單看不到、提出與移除都回「找不到此運算環境」（讀寫各一）。
- `test_duplicate_propose_is_not_doubled`、`test_removed_then_proposed_again_returns_to_checking`。
- `test_bad_name_or_revision_names_the_field`：`nf-core/A B`、`../x`、空版本。
- `test_legacy_site_pipelines_show_as_awaiting_test`：nano4 形狀 CE 含 4 筆 `sitePipelines`、表為空 → 清單 4 筆 `awaiting_test`、`legacy=True`；表沒有新增任何行。
- `test_registered_list_excludes_legacy_and_checking`。
- `test_table_is_created_on_first_use_and_old_db_still_opens`：舊狀態資料庫（無此表）可讀可寫（migration TC）。
- 對等性：新函式名出現在動作清單測試的列舉中（見下）。

### 允許的斷言變動（既有測試釘住的東西）
只准**加入新函式名**，不准刪、放寬或改其他期望值：
- `platform/tests/test_actions_layer.py`（l.30 `CANVAS_NAMES` 旁的各名單、l.707 `PAGE_WRITE_NAMES`）：新寫入函式歸類依其確認管道。
- `platform/tests/test_owner_guard.py`（l.154 起的名單）：每個新函式給一句擁有者說明。
- `platform/tests/test_web_parity.py`（l.19、l.41 的對照表）：本片無網頁入口，若該測試要求每個動作都有入口，標「`pipe-reg-settings-ui` 接上」的暫列方式依該檔既有慣例處理；不得放寬既有條目。
- `platform/tests/test_station_envs.py` l.585-640（NANO4 `sitePipelines`）：本片不得改其輸出。
- `platform/tests/test_web_settings_register.py`、`test_settings_pick_installed.py`：本片不得改其任何斷言（設定頁行為不變）。

## 完成標準（done when）
- 新測試改前紅、改後綠；`tests/run_all.sh` 全綠（已知環境紅見 dev-plans README）。
- ledger 記：`git diff --stat` 只含範圍內檔；「不需要 migration」理由；未確認前後表行數比對。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」；單檔測試 `python -m pytest platform/tests/test_pipeline_registrations.py`（Python：`C:/Users/marvi/AppData/Local/Programs/Python/Python312/python.exe`）；全套在 WSL `tests/run_all.sh`。
- 既有動作：`check_site_pipeline_change`、`site_pipeline_inventory`、`reload_site_inventory`、`register_site_pipeline`、`remove_site_pipeline`（`actions/__init__.py` 約 l.1036-1170，#259／#278）；`_require_human` 約 l.1008。
- 計算環境依擁有者讀：`compute_envs.get(platform_path, ce, owner=_caller_id(caller))`；`config_json` 整份 JSON 儲存。
- `jobs` 表的工作種類有 CHECK 限制（`store.py` l.242，十種），本設計不新增種類。
- nano4 CE 現有 4 筆 `sitePipelines`：ampliseq 2.18.0、rnaseq 3.26.0、sarek 3.9.0、scrnaseq 4.2.0。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- **PITFALLS 已查（`docs/PITFALLS.md`；`docs/solutions/` 不存在），相符項**：
  - 第 55 條「A registered launchpad entry is bound to a compute environment, and reusing it by short name silently runs there」——Symptom：已登記的條目綁在正式運算環境，用短名送出就跑到錯的環境。→ 唯一鍵必含 `compute_env`，所有查詢以 (環境, 管線, 版本) 三者比對，不以管線短名比對。

## 不做
- 排檢查、寫 `sitePipelines`（`pipe-reg-check`）。
- 送出測試、推導已登記（`pipe-reg-test-run`）。
- MCP、指令列（`pipe-reg-mcp-cli`）；網頁（`pipe-reg-settings-ui`、`pipe-reg-launch-filter`）。
- 改既有 `register_site_pipeline`／`remove_site_pipeline` 行為。

## 裁決
1. **舊 `sitePipelines` 要不要寫入新表？** 建議：不寫，讀時合併（`legacy=True`）。理由：不需 migration，且 `pipe-reg-check` 對它重檢時才建正式紀錄。
2. **`registered` 要不要存成 stage？** 建議：不存，由測試分析狀態推導。理由：避免背景程序與新工作種類；分析狀態是唯一真相。

## 裁決（自動補，2026-11-05）
依 verifier 退回的 planIssues 逐條定案；依據為本 repo `actions/__init__.py`（`_sp_no`、`_SP_NAME`、`_SP_NOT_FOUND`）與 `compute_envs._REVISION`。

1. **範圍補 `docs/TESTING.md`（阻擋）**：範圍檔案加入 `docs/TESTING.md`，只准**加**兩步手動核對：(a) `git diff --stat origin/v3...HEAD` 只列範圍內檔案（TC-029）；(b) `git diff` 對三個既有名單測試（`test_actions_layer.py`、`test_owner_guard.py`、`test_web_parity.py`）只有新增行、無刪除或修改行（TC-041）。不得改 TESTING.md 其他段落。
2. **已 `removed` 的列與 legacy 合併**：合併判斷以「表裡有該 (環境, 管線, 版本) 的任何列，含 `removed`」為準，即 `removed` 列**算作有**，該項目不再以 legacy 回傳（否則使用者移除後項目又冒出來）。`removed` 列本身仍不回傳，所以該項目在清單中消失。新增 TC：`test_removed_row_suppresses_legacy_entry`。
3. **`remove_pipeline_registration` 對不存在紀錄**：表裡無此 (環境, 管線, 版本) 列（含僅存在於 legacy `sitePipelines` 者）回 `{"ok": False, "field": None, "message": "找不到此登記紀錄 (registration not found)"}`，不寫表、不碰 `sitePipelines`；legacy 項目的移除仍走既有 `remove_site_pipeline`（本片不改）。已是 `removed` 的列再移除回 `{"ok": True, "changed": False, "state": "removed"}`（冪等）。環境找不到仍回 `_SP_NOT_FOUND`。順序：`_require_human` 先行。新增 TC：`test_remove_unknown_registration_is_refused`、`test_remove_legacy_only_is_refused`、`test_remove_twice_is_noop`。
4. **第二位使用者以第一位環境名讀清單**：`list_pipeline_registrations(ce=…)` 對非自己的環境回 `{"ok": False, "field": None, "message": _SP_NOT_FOUND}`，與完全不存在的環境名逐字相同（不透露環境存在）；`ce=None` 時只列呼叫者自己環境的紀錄。TC-032 補斷言：兩種回應相等。
5. **驗證失敗的 `field` 與版本規則**：`field` 字面值為 `"ce"`、`"pipeline"`、`"revision"`（仿 `_sp_plan`）；空或非字串 → 「`<field>` 必須填寫 (`<field>` is required)」；管線不符 `_SP_NAME` → field `"pipeline"`，沿用 `_sp_plan` 既有句。版本規則即 `compute_envs._REVISION`＝`^(v?[0-9]+(\.[0-9]+){1,3}|[0-9a-f]{40})\Z`，直接引用該常數、不複製。驗證順序：`_require_human` → ce → pipeline → revision。`test_bad_name_or_revision_names_the_field` 補壞版本 `main`、`1`、`v1.`、`1.2.3 `（尾空白）、39 位十六進位；好版本 `3.26.0`、`v2.1`、40 位小寫十六進位。
6. **`test_web_parity`（提醒）**：執行者先讀該檔既有慣例；若要求每個動作有入口，用該檔現有的暫列方式並註明 `pipe-reg-settings-ui` 接上；若無此要求則不動該檔。無論哪種，該檔 diff 只能有新增行（見第 1 條 (b)）。

本節無需維護者另行決定。

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
