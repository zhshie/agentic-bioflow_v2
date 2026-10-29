---
id: canvas-mcp-read
title: 畫布後端的五個唯讀動作開給 MCP：找模組、看模組、列我的 pipeline、看某版、看驗證結果
tier: B
kinds: backend
lane: L44-canvas-mcp
branch: feat/canvas-mcp-read
base: origin/v3@108bfdff（executor 開工前用 `git show origin/v3:<檔>` 重查行號）
source: PLAN-abf-v3-replan-2026-10.md 017a done 句「MCP `find_module("fastqc")` 回 name/sha/輸入輸出型別」＋017e「MCP 鏡像」；017a–d 的 spec 都刻意寫「不加 MCP 工具、不加網頁路由」，把露出留給 017e
---

# canvas-mcp-read

> 只有計畫、沒有程式。B 級 backend → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
畫布後端（目錄、組裝、驗證、送出）已在 v3，但從 MCP 完全摸不到：使用者的 AI 不能問「有沒有 fastqc 模組」、「我有哪些 pipeline」。這一片只開**唯讀**的五個 MCP 工具，不開任何寫入、不加網頁路由。

## 維護者原話（verifier 出題用）
- 017a：「done：MCP `find_module("fastqc")` 回 name/sha/輸入輸出型別。」
- 017a：「`actions/catalogue.py`：`find_module(q)`、`describe_module(name)`；… parity 表加兩個 read 名；BASELINE 更新。」
- 017e：「MCP 鏡像：`find_module`、`describe_module`（read）；… parity 表全列。」
- 裁示 1：「使用者用自己的 AI 走 MCP」。
- 裁示 5：v1 畫布＝「拖模組、連線、填參數、驗證、送去跑、匯出 zip、版本紀錄與分享」。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/mcp_server.py`（加五個 `@mcp.tool` 讀取工具、標 `_READ_ONLY`；檔頭 docstring 的工具數字更新）
- `platform/abf_platform/actions/catalogue.py`（新檔，薄包裝：`find_module(q, *, data=None)` 呼叫 `catalogue.search`、`describe_module(name, *, data=None)` 呼叫 `catalogue.describe`；公開名稱即計畫寫的兩個）
- ~~`platform/abf_platform/actions/__init__.py`~~（13-3：不准改）
- 新檔 `platform/tests/test_mcp_canvas_read.py`
- 釘住「MCP 工具名單」的既有測試，只改名單與計數（見作法）：`test_mcp_server_doc.py`、`test_chat_tools.py`、`test_actions_layer.py`、`test_web_parity.py`、`test_mcp.py`、`test_owner_guard.py` 及 `git grep -l '"my_usage"' platform/tests` 列出的其餘檔
- **不准碰**：`web.py`、`web_board.py`、`static/`、`docs/PLATFORM.md`（env-vars-documented 進行中）、`actions/pipelines.py`（只呼叫、不改）、`compute_envs` 相關（k8s-launch 進行中）、`deploy/`、dev-queue.json。

## 作法
- **證據**（origin/v3@108bfdff）：
  - `catalogue.py` search 約 l.145、describe 約 l.170 已存在；`data/nf-core-modules.json` 已提交。
  - `mcp_server.py` 現有工具 l.40（list_runs）…l.105（read_task_log）都是讀取；`git grep -n "find_module\|describe_module" platform docs` 無結果＝缺。
  - `actions/pipelines.py`：`list_pipelines` l.153、`get_pipeline` l.172、`get_validation` l.234，皆收 `caller=`，他人的 pipeline 回「找不到」。
  - `mcp_server.py` 現有讀取工具用 `caller=_caller(ctx)`（l.220 的 helper）；照同樣寫法。
  - 工具名單被約 30 個測試檔釘住（`git grep -l '"my_usage"' platform/tests`）；`test_mcp_server_doc.py:14` EXPECTED、`:40` 計數 15、`:41` 唯讀 10。
- **新增工具與歸屬**：
  - `find_module(q)`、`describe_module(name)`：目錄是公開資料，不做擁有者篩選。
  - `list_pipelines()`、`get_pipeline(pipeline_id, version=None)`、`get_validation(pipeline_id, version=None)`：一律傳 `caller=_caller(ctx)`，擁有者規則在動作層，不在工具層。
- **`actions.pipelines` 是子模組，不是 `actions` 的公開名稱**：`test_pipelines_store.py:308` 釘「actions 套件裡沒有這些名稱」。工具用 `import abf_platform.actions.pipelines as pipeline_actions`（13-3），不要把它們再匯出到 `actions/__init__`。
- **parity 表**（`test_web_parity.py` 的四張表）：兩個目錄名放 `WEB_ONLY` 以外的對應表前先看該表語意；網頁路由尚不存在（017e），所以這兩個名字要進 `OWED`（欠的）以外的「僅 MCP」類別時需 executor 讀表決定，**OWED 只准縮、不准長**；做不到就在 ledger 寫明並回報，不要放寬測試。

## 失敗先行測試
`platform/tests/test_mcp_canvas_read.py`，先寫、改程式前跑確認紅，紅的輸出貼進 ledger。
- `find_module("fastqc")` 經 MCP 呼叫回 name、sha、輸入與輸出的型別（對應 017a done）。**現在紅**（工具不存在）。
- `find_module("沒有這個模組xyz")` 回空清單與一句怎麼辦，不丟例外。
- `describe_module` 對不存在的名稱回 `found: false` 並點名輸入。
- 跨使用者：甲建一個 pipeline，乙用自己的 token 呼叫 `get_pipeline`、`get_validation`、`list_pipelines`，看不到甲的（讀各一條）。
- 五個工具皆標 `_READ_ONLY`；`/chat/spec` 仍能啟動（`classify_check` 不丟 ValueError）。
- 工具名單的所有釘住測試更新後全綠；工具總數與唯讀數與 docstring 一致。

## 完成標準（done when）
- 新測試改前紅、改後綠；全套 `tests/run_all.sh` 全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含範圍內的檔；既有斷言除「工具名單與計數」外沒被刪或放寬；OWED 沒變大。
- MCP 呼叫 `find_module("fastqc")` 的實際回傳貼進 ledger。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」。
- 單檔測試：repo 根目錄 `python -m pytest platform/tests/test_mcp_canvas_read.py`（WSL）。全套見 `upgrade-hint-followup.md`「環境事實」寫法。
- `test_web_board.py`、`test_web_cost.py` 也釘工具名單，而 web 任務在飛：若 rebase 衝突只解名單那幾行，不碰別的。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不開 `create_pipeline`／`update_pipeline`／`export_pipeline`／`validate_pipeline`／`launch_pipeline`（寫入或會留紀錄，另案）。
- 不加網頁路由、不改 `docs/PLATFORM.md` 的「nine read-only tools」字樣（文件檔在飛，併回後另開 A 級）。

## 裁決
1. **`/chat` 系統提示要不要加一行說明新工具？** 建議：加一行，只講「查模組、查自己的 pipeline」，不用 `approve|confirm|confirmed_by|void|yes`（`chat_tools.BANNED_WORDS` 會擋）。理由：不加則聊天助理不知道有這些工具。
2. **MCP 的取版本工具叫 `get_pipeline` 還是計畫寫的 `get_pipeline_version`？** 建議：`get_pipeline`，與動作函式同名，parity 表省一層對照。
3. **文件的工具數字誰更新？** 建議：本片只改 `mcp_server.py` 檔頭 docstring；`docs/PLATFORM.md:6` 等 env-vars-documented 合併後另開 A 級跟上。

### developer-agent 確認（2026-10-29 22:1x）
證據已抽查（origin/v3 無 find_module／export_pipeline；mcp_server.py 未呼叫 request_pipeline_launch）。上列裁決一律照「建議」定案。

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

## 補充裁決 13-1…13-6（2026-10-29 22:4x，回應出題 BLOCKED(contract)）
- **13-1 範圍加一檔**：`platform/abf_platform/actions/chat_tools.py` 只准在 `CHAT_SYSTEM_PROMPT` 加一行（裁決 1）；`test_chat_tools.py` 除名單與計數外，可加「提示含這一行、且不含 BANNED_WORDS」的斷言，其餘斷言不准改。
- **13-2 find_module 回傳形狀**：回 `{"sha": <目錄快照 sha>, "count": n, "modules": [...]}`；每筆＝`catalogue.search` 的 name／path／description，再從同一份資料併入該模組的 `inputs`、`outputs`（照資料檔原欄位，不改名）。sha 放最外層（全目錄同一個 sha），不逐筆重複。查無結果回 `{"sha": …, "count": 0, "modules": [], "hint": "<一句：換關鍵字或用工具名、例如 fastqc>"}`；有結果時沒有 `hint` 鍵。測試「`find_module("fastqc")` 回 name、sha、輸入輸出型別」照此形狀斷言（sha 讀最外層）。
- **13-3 import 寫法與 parity 表**：比照 `actions.pipelines` 的先例（test_pipelines_store.py:308，子模組不是 actions 的公開名稱）。新檔 `actions/catalogue.py` **不**匯出到 `actions/__init__.py`（該檔不准改，從範圍刪除）。`mcp_server.py` 一律用 `import abf_platform.actions.catalogue as catalogue_actions`、`import abf_platform.actions.pipelines as pipeline_actions`（`import ... as`，不用 `from ... import`，`called_actions` 不會把它們算成取用名字）。結果：四張 parity 表**一字不改**，OWED 仍是原本五個；TC-030～033 以「`test_web_parity.py` 不改任何內容仍全綠」驗收。
- **13-4 數字詞表**：`test_mcp_server_doc.py` 的 NUMBERS 字典與正規式可擴充到 fifteen（加 thirteen、fourteen、fifteen），算「計數」的一部分；其餘斷言不准放寬。`mcp_server.py` 第 1 行註解的工具數字一併更新。
- **13-5 migration**：不需要 migration——本片沒有任何資料表或資料內容變動（只讀既有目錄檔與既有 pipeline 表）。
- **13-6 describe_module 找不到時的訊息**：包裝層自己回 `{"found": False, "name": name, "message": "找不到模組 <name>；用 find_module 找相近的名字 (no module named <name>; use find_module to find a similar name)"}`，不改 `catalogue.py`。測試驗 found:false、點名輸入、訊息含 `find_module`。
