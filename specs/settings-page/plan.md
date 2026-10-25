---
id: settings-page
title: 設定頁第一刀：運算環境（含站台代理連線與已登記管線）、憑證（自己的存取權杖清單）、使用前檢查；密碼與金鑰、個人、營運者後台、角色維持「之後開放」
tier: B
kinds: ui, backend
lane: L8-web-settings
base: v3
source: DESIGN.md v2 畫面 12（Settings）＋畫面 2（First use / Setup）的唯讀部分；總表 012a；維護者 10-25「把開發速度拉到最大，今晚完成」
---

# settings-page

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/settings-page/plan.md`。**只處理本任務**。
> 與 L7（guided-launch-1，改 `/launch`）**同時跑**：新畫面全部寫在新模組 `web_settings.py`，`web.py`／`web_board.py` 只准動裁決 3 列的幾行，以免兩條車道互撞。
> 維護者 10-23：「先把功能做起來吧，以後再改美觀」——只用現有 class 與 DESIGN.md token。

## 目標
同事打開「設定」，不再看到一整頁灰字，而是能**看見自己的環境狀態**：有哪些運算環境、哪個是主要、站台代理連得上嗎、這個環境登記了哪些管線、自己有幾把存取權杖（給 Claude 連平台用的）還有效。頁首一個「使用前檢查」清單告訴他還缺哪一步。本任務全部**唯讀**：新增／修改／撤銷都是寫入動作，要走確認頁，留給後續任務。

## 維護者原話（verifier 出題用）
1. DESIGN.md 畫面 12（英文原文照抄進測試案例）：「**Settings**: compute environments, credentials (token, 12 h), Secrets (AI model key, Jev key optional; browser only), Personal (step-by-step mode, development mode); Operator panel and Roles as dashed "coming later".」
2. DESIGN.md 畫面 2：「**First use / Setup** (`#setup`): numbered disclosure steps: account ✓, access token ✓, compute environment (required: environment, site agent status, cluster account), AI key + Jev key (optional, browser only), create first project.」
3. 「系統設定先。然後右側有對話框，直接對話系統就會引導使用者快速上手建專案，選pipline條參數等等」（原話 2）
4. 「不需要Jev "開關"，只要在設定讓使用者可以放金鑰。」（原話 9）
5. 「先把功能做起來吧，以後再改美觀」（原話 15）

## 範圍：檔案
- `platform/abf_platform/web_settings.py`（**新檔**：設定頁的全部渲染與中英字串）
- `platform/abf_platform/web.py`（只限裁決 3 列的行）
- `platform/abf_platform/web_board.py`（只限裁決 3 列的行）
- `platform/abf_platform/actions/__init__.py`（新增一個 read：`list_my_tokens`）
- `platform/abf_platform/mcp_server.py`（只在 parity 測試要求時登記同名 read tool）
- `platform/abf_platform/static/*.css`（只限裁決 6）
- `platform/tests/test_web_settings.py`（**新檔**）
- `platform/tests/test_web_board.py`（只限裁決 4 點名的 `test_tcs39_s40_s41_s42_settings`）
- `platform/tests/test_web_actions.py`（只限 tc060 把 `web_settings.py` 加進檢查清單——只會變嚴）
- `platform/tests/test_web_parity.py`、`platform/tests/test_actions_layer.py` 及其他「工具清單／工具數」釘死斷言（只加 `list_my_tokens` 一項，ledger 逐條列）
- `docs/PLATFORM.md`（一段：設定頁每一區讀什麼）
- `docs/TESTING.md`（新增一節「設定頁（settings-page）」手動步驟：390 px 無橫捲、Tab 焦點外框、中英各看一次）

## 作法
**`GET /settings`**（路由已存在，`web.py:517`；左欄「設定」維持 here 標記、右欄維持現狀、無 refresh）中欄由 `web_settings.render_middle(...)` 產生，區塊順序固定：

0. **使用前檢查**（`<section id="setup">`，h2「使用前檢查」／英文「Before you start」）：有序清單四項，每項是三種狀態之一（符號＋文字＋樣式，三者都要有）：
   - `✓ 完成`（Done）／`✗ 未完成`（Missing）／`— 之後開放`（Coming later）。
   - ① 帳號：已登入 → 永遠 ✓。
   - ② 存取權杖：`list_my_tokens` 有至少一把 `revoked_at` 為空 → ✓，否則 ✗＋說明「在終端機用 abf-platform 建立」的既有說明句（沿用 docs/PLATFORM.md 的指令名，不新造）。
   - ③ 運算環境：同時滿足「至少一個環境」＋「主要環境的 status 為可用」＋「該環境的站台代理（`agent` 欄）在 `list_agents` 中為 online」→ ✓；任一不滿足 → ✗，說明欄寫出是哪一條（制式句，三選一：「沒有運算環境。」「主要運算環境無法使用：<message>」「站台代理離線。」）。
   - ④ AI 金鑰：`— 之後開放`。
   - 「建立專案」**不列**（專案概念尚未存在；且 `test_web_board` 禁止「建立第一個專案」字樣）。
1. **運算環境**（h2 沿用「運算環境」）：表格，一環境一列，欄＝名稱（主要者加「主要」標記）、平台、狀態（符號＋文字：`✓ 可用`／`✗ 無法使用`＋message／`— 未檢查`；對應 status 值由 executor 從 `compute_envs.py` 實際值整理成對照表寫進 ledger，未列到的值一律歸「— 未檢查」）、站台代理（名稱＋`在線`／`離線`＋最後聯絡時間）、已登記管線（`config.sitePipelines` 的 `pipeline revision` 逐行；沒有此鍵 → `—`）、上次使用時間。沒有環境 → 制式通知「沒有運算環境。」。表下灰字「新增或修改運算環境 之後開放」。只顯示 caller 自己的（`list_compute_envs`／`list_agents` 已帶 owner 規則）。
2. **憑證**（h2 沿用「憑證」）：自己的存取權杖表格：標籤（無標籤 → `—`）、建立時間、狀態（`✓ 有效`／`✗ 已撤銷`＋撤銷時間）。**絕不顯示權杖值或雜湊**。沒有 → 「沒有存取權杖。」。灰字「建立或撤銷權杖 之後開放」。
3. **密碼與金鑰**：維持現狀（「AI 模型金鑰」灰字之後開放）＋一行制式說明「金鑰只存在你的瀏覽器，不會送到平台。」（ADR 0010）。**不放輸入欄**（見裁決 5）。
4. **個人**、5. **營運者後台**、6. **角色（老師／學生）**：維持現狀（之後開放）。

**新 read `list_my_tokens(tokens_path, *, caller)`**（動作層唯一入口）：
- 用 `store.list_pats(tokens_path)`，只留 `user == caller.name` 的；回傳 `{"tokens": [{"id", "label", "created_at", "revoked_at"}]}`，依 id 排序。
- 回傳裡絕不含權杖值、雜湊、別人的權杖。
- 網頁要用 tokens_path（`create_app` 已有）。

**不能放掉的限制**：零 JavaScript、無 `style=`、單一樣式表（CSP 雜湊）、`/settings` 無 refresh、中欄沒有 `<form>`／`<input>`／`<select>`／`<textarea>`／`<button>`（整頁仍只有登出那一個 form）、390 px 無橫捲、英文版每個字都有、不出現「J"+"ev」、「12 小時／12 h／12 hours」、「歡迎使用」「第一次使用」「建立第一個專案」（既有 test_web_board 的禁字）、制式句不口語。

## 失敗先行測試
`platform/tests/test_web_settings.py`（用 `test_web_board` 的 World／seed／pane／plain；環境與代理用既有 harness 的建立方式）：
- `test_st01_sections_in_order`：中欄 h2 依序為「使用前檢查、運算環境、憑證、密碼與金鑰、個人、營運者後台、角色（老師／學生）」；`id="setup"` 存在。
- `test_st02_setup_all_missing`：沒權杖、沒環境 → ① ✓、② ✗、③ ✗「沒有運算環境。」、④ —。
- `test_st03_setup_ce_reasons`：主要環境不可用 → ③ ✗ 帶 message；環境可用但代理離線 → ③ ✗「站台代理離線。」；都好 → ✓。
- `test_st04_ce_table`：兩個環境（一主要）→ 兩列、主要標記、狀態符號＋文字、代理在線／離線、sitePipelines 列出 `nf-core/ampliseq 2.18.0`、沒有 sitePipelines → `—`。
- `test_st05_ce_owner_rule`：bob 的環境與代理不出現在 ann 的頁。
- `test_st06_tokens_table_and_secret_never_shown`：ann 兩把（一把撤銷）、bob 一把 → ann 頁兩列、狀態正確；頁面原文不含任何權杖值或其 sha256。
- `test_st07_list_my_tokens_action`：只回自己的、欄位恰為四個、不含 value／hash；MCP 同名工具結果相同（若 parity 要求）。
- `test_st08_still_read_only`：整頁 form 只有登出一個；中欄無 input／select／textarea／button；POST /settings 仍 405。
- `test_st09_english`：`?lang=en` 中欄無中日韓字；狀態字英文。
- `test_st10_constraints`：無 `<script`、無 `style=`、CSP 雜湊相符、無 refresh、禁字全不出現。
- `test_st11_web_settings_obeys_tc060`：（或直接在 tc060 加檔）`web_settings.py` 不 import confirm／jobs／compute_envs／agents／status，不呼叫寫入動作。

## 完成標準（done when）
上列測試綠；全套綠（環境紅見裁決 1）；改寫的既有斷言在 ledger 逐條「舊→新＋理由」。截圖由 developer-agent 補（1440／390 × zh／en）。

## 環境事實
- `/settings` 路由已存在：`web.py:517`（`settings` handler，呼叫 `web_board.render_settings`）、`web.py:603` 路由表；`web_board.py:30` `SETTINGS` 常數、`:656` `_settings_page`、`:838` `render_settings`（用 `_frame`）。
- 既有設定頁測試：`test_web_board.py:942` `test_tcs39_s40_s41_s42_settings`（斷言 h2 清單、「之後開放」≥6、中欄無 a/form/input…、禁字 J-ev、12 小時、歡迎使用等）；`:335` 左欄 here＝設定；`:806` 設定頁只有一個 form；`test_web_running.py:356` 設定頁無 refresh；`test_owner_binding.py:822`、`test_confirm_page.py:311` 路由集合（本任務不加路由，不受影響）。
- 讀取：`actions.list_compute_envs`（:151，`compute_envs.view` 欄位 name／platform／agent／status／message／primary／lastUsed／config）、`actions.list_agents`（:163，`agents.view`：name／version／status online|offline／last_contact_at）、`store.list_pats`（store.py:871：id／user／label／created_at／revoked_at，不含值）。
- `WEB_SESSION_SECONDS = 12 * 3600`（store.py:156）——但頁面**不得**寫出 12 小時（既有禁字）；DESIGN 的「12 h」本刀不顯示。
- tc060（`test_web_actions.py:535`）只檢查 web.py、web_board.py；本任務把 web_settings.py 加進去。
- 平台程式不連網；本任務維持不連網。

## 不做
- 任何寫入：新增／修改運算環境、建立／撤銷權杖、存金鑰、切換個人模式（全部要確認頁或 JS，後續任務）。
- 不加 JS、不加路由、不加資料表或欄位、不改右欄、不改登入。
- 不做專案、不做營運者後台與角色。

## 裁決
1. 已知環境紅 `tests/init_workspace_test.sh`「site side with no run area known fails clearly」（桌機 WSL `/work` 權限，CI 綠、base 也紅）不算本任務的紅。
2. 新 read 名稱固定 `list_my_tokens`；回傳形狀如「作法」。
3. **平行車道規則**：`web.py` 只准改 `settings` handler 內部（改呼叫 `web_settings`、多讀 tokens／環境／代理）＋一行 import；`web_board.py` 只准 (a) 刪掉 `SETTINGS`、`_settings_page`、`render_settings` 與它們專用的字串鍵，或 (b) 原封不動、由 web_settings 直接用 `web_board._frame`。二選一寫進 ledger。其他行一律不碰（L7 同時在改 `/launch`）。
4. 可改寫的既有斷言：只限 `test_web_board.py::test_tcs39_s40_s41_s42_settings` 中「h2 清單」「之後開放 ≥6」「中欄無 `<a`」三條（中欄現在有表格與灰字，但仍無 form／input／select／textarea／button——這一部分不得放寬）；禁字斷言一律保留。executor 先列 file:line 寫進 ledger 再改。另允許「工具清單／工具數」斷言加一項 `list_my_tokens`、tc060 加檔。其他既有斷言變紅 → BLOCKED。
5. 「密碼與金鑰」本刀**不放輸入欄**：ADR 0010 規定金鑰只存瀏覽器，需要 JS，而 DESIGN 的 JS 白名單沒有設定頁；等對話框（014b）一起做。本刀只加一行制式說明。
6. 可新增的 CSS 只限：設定頁表格的欄寬與換行（`overflow-wrap:anywhere`）、三種狀態符號的樣式；沿用既有顏色與間距 token，不得新增數值。
7. 時間一律用頁面既有的時間格式函式；沒有值顯示 `—`。
8. 狀態值對照（compute env status → ✓／✗／—）由 executor 依 `compute_envs.py` 實際出現的值整理，寫進 ledger；verifier 依 ledger 對照驗收。未知值歸「— 未檢查」，不得歸 ✓。

## 專長守則（ui）

### executor

- 先讀專案根目錄的 `PRODUCT.md`（給誰用、要解決什麼）與 `DESIGN.md`（版面線框、tokens、每個畫面與狀態、維護者的原話例子）。讀不到就 BLOCKED，不自己發明設計。
- 只准用 `DESIGN.md` 定義的 tokens（色彩、字型、字級、間距、圓角）與版面。不新增任何視覺決策：不自創顏色、字型、間距數值，不順手「美化」。
- `DESIGN.md` 沒決定的事，一律寫進報告的「卡住的原因／要問的問題」，不猜。
- `DESIGN.md` 列出的每個畫面、每個狀態都必須做出來，包含空狀態、載入中、錯誤、失敗。少一個就不算完成。
- 遵守計畫寫明的前端限制（例如 CSP、禁用 inline style、不載外部資源、只在允許處使用 JS）。限制與設計衝突時停下來問，不自行取捨。
- 狀態絕不只靠顏色：一律「符號＋文字＋顏色」三者並用。
- 手機寬度可用（不橫向捲動、點擊目標夠大），鍵盤操作時焦點外框可見。
- 介面文字用使用者視角的白話，不露出內部術語、錯誤代碼或程式名詞；錯誤訊息說發生什麼事與下一步。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- `DESIGN.md` 的每個畫面、每個狀態都至少對應 1 個 TC（含空、載入、錯誤、失敗）。
- 維護者的原話例子逐字對應到 TC。
- 計畫列的前端限制各對應 TC（例如頁面不得含 inline style、不得請求外部網址、CSP 標頭存在）。
- 狀態表達 TC：每個狀態輸出的 HTML 同時含符號、文字，不得只靠 class 顏色。

**ACCEPTANCE（閱卷）必須檢查：**
- 把每個有改動的頁面渲染成 HTML 檔（用專案的 test client，或計畫指名的 fixture）。做不到就標 UNVERIFIED，並寫明需要什麼才能驗。
- 對渲染出的 HTML 跑 Impeccable 偵測器（唯讀）：`sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>`。
- **FAIL**：違反 `DESIGN.md` 的 tokens／畫面／狀態；違反計畫寫明的前端限制；狀態只靠顏色；缺少 DESIGN.md 列出的畫面或狀態。
- **「需要人看的事」**：偵測器的其他發現（對比、常見字型、AI 範本味等）與品味問題。這些不判 FAIL。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
- 注意：「看起來好不好」的最終判斷屬於維護者，靠 developer-agent 附在 PR 的截圖（B 級）決定，verifier 不替他下結論。

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
