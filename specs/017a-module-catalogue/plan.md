---
id: 017a-module-catalogue
title: nf-core 模組目錄快照與查詢（畫布的積木清單）
tier: A
kinds: backend
lane: L5
base: v3
---

# 017a-module-catalogue

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/017a-module-catalogue/plan.md`。**只處理本任務**。用剩餘平行額度跑；不在本週必達清單。

## 目標
把全部 nf-core 模組（約 1,500 個）的 `meta.yml` 做成一份提交在 repo 的 JSON 快照，平台能搜尋與描述模組——這是日後拖拉畫布的積木清單，也讓 MCP 使用者能問「有沒有 fastqc 模組、輸入輸出是什麼」。

## 維護者原話（verifier 出題用）
- 「積木＝nf-core 模組，全部約 1,500 個；pipeline 與 module 都要相容所有 nf-core 既有的。」（裁示 5）
- 「不自建工具庫」（不做清單）——只讀 nf-core/modules，不自己維護模組。

## 範圍：檔案
- `scripts/snapshot_modules.py`（新）
- `configs/nf-core/modules.json`（新，提交產物）
- `platform/abf_platform/catalogue.py`（新）
- `platform/abf_platform/actions/catalogue.py`（新）
- `platform/tests/test_catalogue.py`（新）
- `platform/tests/test_web_parity.py`、`platform/tests/test_actions_layer.py`（parity 表＋BASELINE）

## 作法
- `snapshot_modules.py --sha <sha>`：淺 clone `nf-core/modules` 到暫存目錄（固定 sha），讀 `modules/nf-core/**/meta.yml`，輸出 `modules.json`：`{sha, generated_at, modules:[{name, path, description, keywords, tools:[{name, homepage, licence}], inputs:[{name, type, pattern}], outputs:[...], container}]}`，排序穩定（name），讓 diff 可讀。測試不連網：用 fixture 目錄模擬三個模組。
- `catalogue.py`：`load()`（快取）、`search(q)`（name／keywords／description 子字串，回前 50）、`describe(name)`。
- `actions/catalogue.py`：read tools `find_module(q)`、`describe_module(name)`（經動作層；無寫入）。
- parity 表加兩個 read 名；`test_actions_layer` BASELINE 更新（PR 說明寫明有意）。
- 更新快照＝一個 A 級 PR（在 `docs/PLATFORM.md` 或 ledger 寫明流程，不新增文件任務）。

## 失敗先行測試
- `test_snapshot_reads_meta_yml_into_stable_json`（fixture 三模組，輸出與 golden 相等）。
- `test_find_module_fastqc_returns_name_sha_and_channel_types`。
- `test_describe_unknown_module_is_a_clean_not_found`。

## 完成標準
MCP `find_module("fastqc")` 回 name／sha／輸入輸出型別；快照檔提交；全套綠。

## 不做
- 不做組裝（017b）、驗證（017c）、UI（017e）；不在平台主機跑 `nf-core modules install`。

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

## 裁決（2026-10-22，developer-agent，回應 verifier 出題退回的 8 點）
1. **快照位置**：不放 `configs/`（憲法檢查 `tests/no_per_pipeline_config.sh` 規定 configs/ 只放站台設定，該檢查不動）。改放套件內 `platform/abf_platform/data/nf-core-modules.json`，`platform/pyproject.toml` 的 `package-data` 加 `"data/*.json"`，程式以 `importlib.resources` 讀，安裝成套件後也找得到。CLAUDE.md「pipeline 內容讀上游、不快取」指的是 pipeline 的程式與設定；這份是模組**目錄索引**（名稱、輸入輸出型別，附 upstream sha），維護者 10-21 裁示 5 已定「積木＝全部 nf-core 模組的快照」，不衝突。範圍檔新增：`platform/pyproject.toml`。
2. **檔案範圍補齊**：`platform/abf_platform/mcp_server.py`（註冊兩個 read 工具，函式名＝動作名）、`platform/abf_platform/actions/__init__.py`（公開 `find_module`、`describe_module`，簽名照既有 read 動作：`(index_path, q, *, caller=None, platform_path=None)`）。
3. **會被牽動的既有測試與文字，全部點名、允許只做對應的數字／名單更新（每處寫進 ledger）**：`platform/tests/test_mcp.py` 工具名單＋2；`platform/tests/test_pat.py:751` `len(tools) == 7` → 9（read 工具數）；`platform/tests/test_guidance.py` `READ_TOOLS` ＋2；`platform/abf_platform/guidance.py` `FIXED_SENTENCE` "Seven tools" → "Nine tools"；`platform/tests/test_chat_tools.py` `READ_ONLY` ＋2；`docs/PLATFORM.md` 第 275 行附近 "Twelve tools. Seven are read-only" → "Fourteen tools. Nine are read-only"，並在工具表加兩列。除此之外不改任何既有斷言。
4. **parity 表**：兩個動作進 `OWED`，欠的網頁路由標 `"017e"`（畫布的 `/api/modules?q=`）。`test_tcs07` 的「OWED ⊂ OWED_BEFORE_012B」斷言改成「OWED − {find_module, describe_module} ⊂ OWED_BEFORE_012B」並在 ledger 記 old／new／理由（R2 流程：計畫在此點名）。不進 WEB_ONLY、不進 INTERNAL。
5. **手動 TC**：`docs/TESTING.md` 加一節「Module catalogue (017a)」：對照 upstream `modules/nf-core/` 目錄數與快照 `modules` 長度相等（允許差 0）。範圍檔新增 `docs/TESTING.md`。
6. **不需要 migration**：沒有資料庫結構或內容變動；快照是套件內唯讀檔，`platform.db` 不碰。
7. **細節定案**：
   - 快照不含 `generated_at`（只有 `sha` 與 `modules`），輸出才能與 golden 逐字相等；更新時間由 git 記錄。
   - `name` 取 `meta.yml` 的 `name`；`path` 是相對 `modules/nf-core/` 的目錄路徑（如 `fastqc`、`samtools/sort`）。
   - `meta.yml` 讀不出（YAML 壞、缺 name）→ 不中斷，記進快照頂層 `errors:[{path, reason}]`，stderr 各印一行；測試 fixture 放一個壞檔驗這條。
   - `search(q)`：不分大小寫，比對 name、keywords、description 子字串；依 name 排序回前 50。
   - 找不到：`catalogue.describe` 回 `None`；動作 `describe_module` 回 `{"found": false, "name": <q>}`；MCP 工具文字 "No nf-core module named <q>."（白話、不露路徑）。
   - 兩個動作都帶 `caller`（照既有 read 動作），但不做擁有者過濾——目錄是公開資料，計畫在此明寫理由；verifier 的跨使用者 TC 對這兩個動作改為「兩位使用者看到相同結果」。
8. **規格來源**：本任務以本計畫為規格，不另立 spec.md（A 級新增能力、無既有行為修改）。
