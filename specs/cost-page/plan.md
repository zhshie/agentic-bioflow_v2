---
id: cost-page
title: 費用頁第一刀：/usage 一頁（國網 SU 本月、雲端本月已用／上限／剩餘、每個分析一列），抬頭費用字樣改成連到這頁；雲端一律美元不換算
tier: B
kinds: ui, backend
lane: L9-web-cost
base: v3
source: DESIGN.md v2 畫面 11；總表 012d；維護者 10-18 裁示（雲端顯示自己的幣別、不換算、上限由管理者設）；維護者 10-25「把開發速度拉到最大」
---

# cost-page

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/cost-page/plan.md`。**只處理本任務**。可與 guided-launch-1（L7）同時跑：本任務的頁面放在新模組，`web.py` 只加路由行、`web_board.py` 只動抬頭（見裁決 7）。
> 維護者 10-23：「先把功能做起來吧，以後再改美觀」——只用現有 class 與 DESIGN.md token。

## 目標
同事點抬頭的費用字樣，就看到「這個月我用了多少」：國網 SU 多少、雲端用了幾美元、上限多少、還剩多少，以及每個分析各花多少、這個數字是估算還是還在跑。不必問管理者、不必登入國網或 Google 帳單。

## 維護者原話（verifier 出題用）
1. DESIGN.md 畫面 11（英文原文照抄進測試案例）：「**Cost** (`#cost`, from the masthead meter): cards NCHC SU / Cloud used / cap / remaining; "never converted" line; Action-needed notice when a launch would exceed the cloud cap (use NCHC / wait for reset); per-analysis table with status Running / Reconciled / Estimate, bill pending.」
2. 10-18 裁示（總表第 10 條）：「雲端費用照 10-18 裁示：顯示雲端自己的幣別（美元）、不換算、每人每月上限由管理者開帳號時設」
3. 「先把功能做起來吧，以後再改美觀」（DESIGN.md 原話 15）
4. 「做成產品英文版面是必須的」（原話 5）

## 範圍：檔案
- `platform/abf_platform/web_cost.py`（新檔：這一頁的 HTML 組裝）
- `platform/abf_platform/web.py`（只加 `GET /usage` 一條路由與它的處理函式，其他行不動）
- `platform/abf_platform/web_board.py`（只限 `_mast` 與兩個字串鍵 `cost_su`／`cost_cloud`，見裁決 7）
- `platform/abf_platform/actions/__init__.py`（新增一個 read：`my_usage`）
- `platform/abf_platform/mcp_server.py`（同名 read tool，parity 要求）
- `platform/abf_platform/static/*.css`（只限裁決 5）
- `platform/tests/test_web_cost.py`（新檔）
- `platform/tests/test_web_parity.py`、`platform/tests/test_actions_layer.py` 及其他「工具清單／工具數」釘死斷言（只加 `my_usage` 一項，ledger 逐條列）
- 抬頭字樣相關的既有斷言（只限裁決 4 點名的）
- `docs/PLATFORM.md`（一段：費用頁每個數字從哪來）
- `docs/TESTING.md`（新增一節「費用頁」手動步驟：390 px 無橫捲、Tab 焦點外框、中英各看一次）

## 作法
**路由＝`GET /usage`**（不是 `/cost`，見裁決 2）。`?lang=en` 英文；`?month=YYYY-MM` 看別的月份（預設本月，台北時間）；格式錯 → 當作本月並顯示制式通知「月份格式不對，顯示本月。」。須登入；未登入同其他頁轉到登入。

**新 read `my_usage(index_path, platform_path, *, caller, month=None, tokens_path=None)`**（動作層唯一入口，網頁與 MCP 共用；只算 caller 自己的分析）。回傳：
```
{"month": "YYYY-MM",
 "su": {"total": float|None, "unknown_reasons": [...], "site": str|None},
 "cloud": {"used_usd": float, "unknown_runs": int, "cap_usd": float|None, "remaining_usd": float|None, "currency": "USD"},
 "runs": [{"name", "started_at", "where": "nchc"|"cloud"|None, "state": "running"|"estimate", "su": float|None, "usd": float|None, "unknown_reasons": [...]}]}
```
- `su.total`＝`su.month_total(...)`（站台＝費率檔的 `default_site`；任何一個分析算不出 → None 並帶原因，不給部分和）。
- `cloud.used_usd`／`unknown_runs`＝`cloud_cost.month_used(...)`；`cap_usd`＝`store.cloud_cap(tokens_path, user_id)`（沒設 → None）；`remaining_usd`＝`max(0, cap − used)`，沒上限 → None。
- `runs`：caller 這個月開始的分析（`status.list_runs` × `jobs.owned_run_names`），最新在前，最多 50 筆。`where` 由該分析最新一次 launch 的運算環境決定（雲端＝Google Batch 環境，`cloud_cost._launch_facts`；不是平台送出的 → None）。`state`：分析狀態是 running／lost → `running`（數字一律 None，原因「run 還沒結束」）；其他 → `estimate`。國網的分析填 `su`（`_su_of_run` 同一套），雲端的填 `usd`（`cloud_cost.run_tasks_cost`）。
- 不新增資料表、不需 migration。

**頁面**（`web_cost.py` 組裝，沿用三欄骨架的抬頭與左欄；中欄內容如下；右欄維持現狀）：
1. 標題「費用」／「Cost」＋月份（`2026-10`）＋上一月／下一月連結（下一月不超過本月）。
2. 四張卡（沿用執行階段卡片元件）：
   - 「國網 SU（本月）」：數字取兩位小數；None → 「—」＋卡內小字原因第一條。
   - 「雲端已用（本月）」：`US$ 12.34`；`unknown_runs > 0` → 加小字「另有 n 個分析算不出」。
   - 「雲端上限」：`US$ 50.00`；None → 「未設定」＋小字「由管理者設定」。
   - 「雲端剩餘」：`US$ 37.66`；None → 「—」。剩餘為 0 → 卡片用既有「需處理」樣式＋右欄**不**加通知（本任務只在本頁顯示）。
3. 一行固定說明：「雲端費用以美元顯示，不換算新台幣；國網以 SU 計。數字是依執行紀錄估算，略低於實際帳單。」（英文對應句）。
4. 每個分析一列的表：欄＝分析名稱（連到 `/?run=<id>`）、開始時間、在哪裡跑（國網／雲端／—）、用量（`12.30 SU` 或 `US$ 1.20` 或「—」）、狀態。狀態只有兩種：`⟳ 執行中`／`≈ 估算・帳單未到`（英文 `Running`／`Estimate · bill pending`）。沒有分析 → 「— 這個月還沒有分析」。
5. 不做「Reconciled（已對帳）」：沒有帳單資料來源（見裁決 3）。

**抬頭**：`_mast` 兩個費用字樣包成一個連到 `/usage`（保留 `lang`）的連結；字串 `cost_cloud` 由「雲端 NT$ —」改成「雲端 US$ —」，英文「Cloud US$ —」（10-18 裁示：美元不換算）。數字本任務不填（仍是 —），見裁決 7。

**不能放掉的限制**：零 JavaScript、無 `style=`、單一樣式表（CSP 雜湊）、每人只看自己的、390 px 無橫向捲動、英文版每個字都有、制式通知。既有 `test_web_actions.py` 的 tc046–048、tc051、tc060、tc063、tc040 全部要繼續綠。

## 失敗先行測試
`platform/tests/test_web_cost.py`（用 `test_web_board` 的 World／seed；費率檔與雲端上限用既有測試 fixture 的作法注入）：
- `test_co01_page_has_four_cards_note_and_table`：`GET /usage` 200、四張卡標題、固定說明句、表頭五欄。
- `test_co02_su_total_and_unknown`：兩個國網分析可算 → 總和；其中一個算不出 → 「—」＋原因。
- `test_co03_cloud_used_cap_remaining`：上限 50、用 12.34 → 已用 US$ 12.34、上限 US$ 50.00、剩餘 US$ 37.66；全頁不出現「NT$」。
- `test_co04_no_cap`：沒設上限 → 「未設定」、剩餘「—」。
- `test_co05_over_cap_is_zero_remaining`：用量超過上限 → 剩餘 US$ 0.00、卡片用需處理樣式。
- `test_co06_rows_states`：running 的分析狀態「執行中」用量「—」；結束的「估算・帳單未到」；別人的分析不出現；上個月的不出現。
- `test_co07_month_param`：`?month=2026-09` 只列 9 月；`?month=abc` → 本月＋制式通知；下一月連結不超過本月。
- `test_co08_masthead_links_to_usage_and_says_usd`：任一頁抬頭的費用字樣是連到 `/usage` 的連結；英文頁連結帶 `lang=en`；抬頭不再有 `NT$`。
- `test_co09_english`、`test_co10_constraints_hold`（無 `<script`、無 `style=`、CSP 雜湊、無口語句、路由路徑不含 `cost`）。
- `test_co11_my_usage_action_and_mcp_match`：動作層與 MCP 回同樣內容；bob 看不到 ann 的分析，`runs` 只含自己的。
- `test_co12_login_required`：未登入 → 轉登入，不洩漏數字。

## 完成標準（done when）
上列測試綠；全套綠（環境紅見裁決 1）；改寫的既有斷言在 ledger 逐條「舊→新＋理由」。截圖由 developer-agent 補（1440／390 × zh／en）。

## 環境事實
- SU：`platform/abf_platform/su.py`（`load_rates`、`site_of_run`、`run_su`、`month_total` 165：任何一個算不出就回 None）。`actions._su_of_run`（actions/__init__.py:112）是 get_run 的 `su` 部分；`actions.estimate_su`（134）。
- 雲端：`platform/abf_platform/cloud_cost.py`（`CURRENCY = "USD"` 20、`run_tasks_cost` 126、`_launch_facts` 149、`month_used` 191、`cap_problem` 240）。上限：`store.cloud_cap(tokens_path, user_id)`（store.py:761），表 `tokens.cloud_caps(user_id, cap_usd, set_at)`。
- 目前沒有任何 action 暴露 `month_total`／`month_used`／`cloud_cap`——所以本任務加 `my_usage`。
- 抬頭：`web_board.py::_mast`（約 340 行）；字串 `cost_su`「SU —」、`cost_cloud`「雲端 NT$ —」（約 37、78 行）；執行／結果階段的「費用」卡用 `t["cost_su"]`（約 523、538 行）——那兩張卡本任務不改。
- 守門測試（`test_web_actions.py`）：tc051（約 492）路由路徑不得匹配 `upload|cost|chat|forget|samplesheet|delete`，且 `/cost` 必須 404；tc060（535）web.py／web_board.py 不得 import `confirm, jobs, compute_envs, agents, status`、不得呼叫 `actions.launch/cancel/forget/...`——`web_cost.py` 同樣只經 `actions` 取資料；tc063 不得新增表或欄。
- 平台程式完全不連網；本任務維持不連網。

## 不做
- 不做「已對帳 Reconciled」、不接 Google 帳單或國網帳務 API。
- 不做「送出會超過上限」的需處理通知（那在送出流程的 `cap_problem`，已存在；右欄通知留給後續）。
- 不改執行／結果階段的「費用」卡、不在抬頭填數字、不換算幣別、不改確認頁、不加 JS、不加資料表、不改管理者設定上限的 CLI。

## 裁決
1. 已知環境紅 `tests/init_workspace_test.sh`「site side with no run area known fails clearly」（桌機 WSL `/work` 權限，CI 綠、base 也紅）不算本任務的紅。
2. 路由固定 `GET /usage`。DESIGN 的 `#cost` 只是畫面代號；守門測試 tc051 禁止路徑含 `cost` 且要求 `/cost` 404——**不得放寬 tc051**（放寬安全網＝C 級）。
3. 狀態只有 `running` 與 `estimate` 兩種；Reconciled 沒有資料來源，本任務不顯示、不佔位。
4. 可改寫的既有斷言：只限斷言抬頭字串「雲端 NT$ —」／「Cloud NT$ —」或抬頭費用字樣「不是連結」的那幾條；executor 先列 file:line 寫進 ledger 再改。另允許「工具清單／工具數」斷言加一項 `my_usage`。其他既有斷言變紅 → BLOCKED。
5. 可新增的 CSS 只限：費用表的數字欄靠右、狀態符號；沿用既有顏色與間距 token，不得新增數值。
6. 新 read 名稱固定 `my_usage`；回傳形狀如「作法」；金額一律保留兩位小數顯示、計算不四捨五入。
7. 平行開發邊界：本任務與 guided-launch-1 同時進行。`web.py` 只新增 `/usage` 路由與其處理函式（放在檔案末端的路由登記區，不重排既有行）；`web_board.py` 只動 `_mast` 與 `cost_su`／`cost_cloud` 兩個字串鍵，不碰 `render_launch` 與其他函式；頁面 HTML 全部放 `web_cost.py`。
8. 月份以台北時間計（與 `su._taipei_month` 一致）；分析歸屬月份以開始時間計。
9. 抬頭這次只改幣別與連結，不填數字（DESIGN Open：費用行未在 10-23 重新確認）。
10. 國網 SU 總數這次用費率檔 `default_site` 計；頁面不另加說明。目前只有 nano4 一個站台，多站台加總留後續。
11. `mcp_server.py` 與「工具清單／工具數」斷言若與其他車道同時加工具：照本計畫只加 `my_usage` 一項；合併衝突由 developer-agent 解，executor 不預先算入別的車道的工具。

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
