---
id: settings-register-pipeline
title: 設定頁可以在自己的運算環境登記／移除管線版本（模組名＋管線資料夾變數），送出後自動排一次使用前檢查
tier: B
kinds: ui, backend
lane: L8-web-settings
base: v3
source: 維護者 2026-10-28「登記管線要做，畢竟是裝在使用者自己租的伺服器或國網」；PR #240 Needs human 第 2 點
---

# settings-register-pipeline

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/settings-register-pipeline/plan.md`。**只處理本任務**。

## 目標
使用者在自己租的伺服器或國網上用 `module` 裝好某個 nf-core 管線版本後，能在「設定」頁的那個運算環境底下把它登記上去（或移除），不必找管理者打指令。登記後 `/launch` 第 3 步就不再顯示「尚未登記」，平台並自動排一次使用前檢查，確認站台真的載得到那個模組。

## 維護者原話（verifier 出題用）
1. 「登記管線要做，畢竟是裝在使用者自己租的伺服器或國網。」（2026-10-28）
2. 「先把功能做起來吧，以後再改美觀」（10-23，仍適用）
3. 「跟Seqera platform一樣的模式，不要自己定義」（10-23 常設方向；Seqera 的對應是 compute environment 設定裡由使用者自己填）

## 範圍：檔案
- `platform/abf_platform/actions/__init__.py`（新增兩個寫入動作，見作法 1）
- `platform/abf_platform/compute_envs.py`（只准加一個小 helper；驗證規則 :263-300 不准放寬）
- `platform/abf_platform/web.py`（兩條新 POST 路由與註冊行，見作法 2）
- `platform/abf_platform/web_settings.py`（環境列加表單與移除按鈕）
- `platform/abf_platform/web_board.py`（只限 STRINGS 新字串，以及 `/launch` 未登記訊息改句）
- `platform/abf_platform/mcp_server.py`（登記同名兩個工具，見作法 4）
- `platform/tests/test_web_settings_register.py`（新檔）
- 被逐字釘住、必須更新的既有測試（只加新項，不刪既有斷言；ledger 逐條列）：`test_dataset_cli.py:183`、`test_cleanup_offer.py:815`、`test_confirm_page.py:313`、`test_web_board.py:820`、`test_owner_binding.py:824`、`test_temp_password.py:290`、`test_web_parity.py:16`、`test_actions_layer.py`（工具清單）、`test_web_settings.py::test_st08_still_read_only`（見裁決 1）、`/launch` 未登記句相關測試
- `docs/PLATFORM.md`（:608「設定頁唯讀」一段改寫）、`docs/SETTINGS.md`（:325 附近加「從網頁登記」一句）、`docs/TESTING.md`（新增手動一節）

## 作法
1. **動作層**：`register_site_pipeline(platform_path, *, ce, pipeline, revision, module, home, caller)` 與 `remove_site_pipeline(platform_path, *, ce, pipeline, revision, caller)`。
   - 先 `compute_envs.get(..., owner=caller.user_id)`；不是自己的環境＝「找不到」（與既有讀取一致，不洩漏他人環境存在）。
   - 讀出現有 `sitePipelines` 清單 → 新增（同一 pipeline＋revision 已存在＝取代該筆）或移除 → `compute_envs.update(state, ce, {"config": {"sitePipelines": 新清單}})`，驗證照舊由 `clean()` 做；驗證錯誤原樣回給使用者（說哪一欄錯）。
   - 成功後排一次使用前檢查（重用 `cli.py` 的 `_queue_first_preflight` 同一路徑，把它搬成可共用 helper 亦可，但 CLI 行為不變）。
   - pipeline 只收 `nf-core/<名>` 形式（與 `/launch` 同一判斷）；revision 規則沿用（release 或 40 位 commit，拒分支名）。
2. **網頁**：`POST /settings/pipelines`（新增）與 `POST /settings/pipelines/remove`。照 `launch_post` 的順序：`same_origin` → `user_of` → CSRF（purpose `settings-pipeline`）。成功 303 回 `/settings#ce-<名>`；錯誤 400 重畫設定頁並保留已填的值、在該環境列上方顯示錯誤句。臨時密碼登入者照既有規則被導到 `/welcome`。CSP 不變（`form-action 'self'` 已夠）。
3. **畫面**（設定頁每個運算環境列，在現有「已登記管線」清單下方）：
   - 每筆已登記管線旁一個「移除」按鈕（小表單，按了直接送出，不另開確認頁）。
   - 「登記管線」表單四欄，標籤正式用語：「管線（例 nf-core/ampliseq）」「版本（例 2.18.0）」「模組名稱（站台 `module load` 用的名字，例 biology/nf-core-ampliseq/2.18.0）」「管線資料夾變數（模組設定的環境變數名，例 NFCORE_AMPLISEQ_HOME）」；四欄皆必填，紅色 `*`；一個按鈕「登記」。
   - 登記成功後該列顯示「已排入使用前檢查」，檢查結果沿用既有狀態顯示。
   - 只用現有 class 與 DESIGN.md token；中英字串都要有。
4. **MCP**：登記同名兩個工具（寫入），讓 Claude Desktop 使用者也能用；parity 表加兩項。
5. **`/launch` 未登記句**改成「此管線版本尚未在所選運算環境登記，請先至設定頁登記。」（設定頁連結保留），撤掉 2d 裁決 4 的暫用句。

## 失敗先行測試
`test_web_settings_register.py`：新增成功（資料庫清單多一筆、303、排了一次檢查）；同 pipeline＋revision 再登記＝取代不重複；移除成功；他人環境＝找不到且資料庫不變；缺 CSRF／跨來源＝403 且不變；module 含 `..`、home 小寫、revision 是分支名＝400 帶欄位錯誤句且已填值保留；非 nf-core 名稱＝400；登記後 `/launch?pipeline=…&revision=…` 不再出現未登記句；GET /settings 不改資料庫；390 px 不橫捲（字串層檢查表單沒有固定寬度）。

## 完成標準（done when）
上列測試全綠；整套 `tests/run_all.sh --timeout 900` 綠；既有釘死測試只「加項」；ledger 列出每條被改的釘死斷言與理由。

## 環境事實
- `sitePipelines` 每筆鍵＝`{pipeline, revision, module, home}`，驗證在 `compute_envs.py:263-300`、站台端重驗在 `abf_station/rules.py:112-128`；使用前檢查 `site_pipeline` 在 `abf_station/handlers.py:233`（載模組、看 `$HOME_VAR/main.nf`、比對 manifest 版本）。
- 範例：`configs/sites/nchc-nano4-ce.json:6`。
- 平台本身不得開網路連線（憲法原則 2）；本任務不需要任何連線。

## 不做
- 不做新增／刪除運算環境本身（另案）。
- 不幫使用者在站台安裝模組；不從網路查模組清單。
- 不改驗證規則、不放寬任何安全標頭。

## 裁決
1. `test_st08_still_read_only` 原本釘「設定頁中欄沒有任何表單」。本任務是維護者 10-28 明確要求的寫入功能，改成：中欄只允許本任務的兩種表單（purpose `settings-pipeline`），其餘斷言（沒有權杖清單 action、GET 不改資料庫）不動。
2. 移除不另開確認頁：只影響使用者自己的登記資料、可以立刻再登記回來（可逆），照「先把功能做起來」。

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
