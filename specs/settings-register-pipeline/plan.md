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
- `platform/abf_platform/compute_envs.py`（只准加小 helper；驗證規則 :263-300 不准放寬）
- `platform/abf_platform/cli.py`（只限把 `_queue_first_preflight` 搬成共用 helper 時的呼叫點；CLI 輸出逐字不變）
- `platform/abf_platform/web.py`（新增路由與註冊行，見作法 2）
- `platform/abf_platform/web_settings.py`（環境列的表單、移除按鈕、確認頁渲染）
- `platform/abf_platform/web_board.py`（只限 STRINGS 新字串，以及 `g_reg_bad` 改句）
- `platform/tests/test_web_settings_register.py`（新檔）
- 被逐字釘住、必須加項的既有測試（只加不刪，ledger 逐條列）：`test_dataset_cli.py:183`、`test_cleanup_offer.py:815`、`test_confirm_page.py:313`、`test_web_board.py:820`、`test_owner_binding.py:824`、`test_temp_password.py:290`、`test_web_parity.py:16`、`test_actions_layer.py`、`test_web_settings.py::test_st08_still_read_only`（見裁決 1）、`g_reg_bad` 相關斷言
- `docs/PLATFORM.md`（:608「設定頁唯讀」一段改寫）、`docs/SETTINGS.md`（:325 附近加「從網頁登記」）、`docs/TESTING.md`（新增手動一節：390 px 無橫捲、Tab 焦點外框、中英各看一次、真站台登記一次看使用前檢查結果）

## 作法
（10-28 第三版，取代前兩版。）
1. **動作層**（寫入，只在人確認後）：
   - `register_site_pipeline(platform_path, *, ce, pipeline, revision, module, home, confirmed_by, caller)` 與 `remove_site_pipeline(platform_path, *, ce, pipeline, revision, confirmed_by, caller)`。
   - 第一行 `_require_human(confirmed_by)`（與 `launch`／`cancel` 同一個檢查；不是 TERMINAL／ELICITED／PAGE 就拒絕，資料庫完全不碰）。
   - 再 `compute_envs.get(..., owner=caller.user_id)`；不是自己的環境＝「找不到」。
   - 讀現有 `sitePipelines` → 新增（同 pipeline＋revision 已存在＝取代該筆）或移除 → `compute_envs.update(state, ce, {"config": {"sitePipelines": 新清單}})`；驗證照舊由 `clean()` 做，錯誤原樣回傳（說哪一欄錯）。
   - 移除清單裡沒有的一筆＝不改資料，回 `{"ok": True, "changed": False}`。
   - 新增成功後排一次使用前檢查（把 `cli.py:388-402` 的 `_queue_first_preflight` 搬成共用 helper 或直接呼叫；CLI 輸出逐字不變），回傳值帶 `preflight: "queued" | "no_agent" | "not_checkable"`（依 helper 的實際分支對應）。移除不排檢查。
   - pipeline 名稱判斷 `^nf-core/[a-z0-9][a-z0-9-]{0,63}\Z`。
2. **網頁兩步驟（不用資料庫存待確認請求，所以不需要 migration）**：
   - 第一步 `POST /settings/pipelines`（欄位：`op`＝add｜remove、ce、pipeline、revision、module、home）：`same_origin` → `user_of` → CSRF（purpose `settings-pipeline`）→ 先做「不寫入」的檢查（環境是自己的、欄位格式；移除時那筆是否還在）。不通過＝400 重畫設定頁，保留已填值、在該環境列上方顯示錯誤句；移除已不存在的一筆＝303 回 `/settings?notice=gone#ce-<名>`，顯示「此管線版本已不在清單中。」。通過＝回 200 **確認頁**（不寫任何東西）。
   - 確認頁列出：動作（新增／移除）、環境、管線、版本、模組名稱、管線資料夾變數；「登記第一筆」或「移除最後一筆」時加裁決 5 那句。表單把同樣欄位放 hidden，另帶確認用 CSRF：purpose ＝ `settings-pipeline-confirm:` ＋ 這組欄位（op、ce、pipeline、revision、module、home 依序以 `
` 串接）的 sha256。按鈕「確認」與「返回」（返回＝連回 `/settings`，不送出）。
   - 第二步 `POST /settings/pipelines/confirm`：`same_origin` → `user_of` → 用收到的欄位重算 purpose 驗 CSRF（欄位被改＝403、不寫）→ 呼叫動作層並帶 `confirmed_by=actions.PAGE`、`caller=<登入者>` → 303 回 `/settings?notice=<結果>#ce-<名>`。
   - `notice` 只接受白名單值（`added_queued`、`added_no_agent`、`added_not_checkable`、`removed`、`gone`），其他值忽略；設定頁在該環境列上方顯示對應句。
   - 臨時密碼登入者照既有規則被導到 `/welcome`。CSP 不變。
3. **畫面**（設定頁每個運算環境列，在「已登記管線」清單下方）：每筆旁一個「移除」小表單（送到第一步、op=remove）；「登記管線」表單四欄必填、紅色 `*`、按鈕「登記」。只用現有 class 與 DESIGN.md token。
4. **字串**（中／英，皆為正式書面語，新增字串不得含 DESIGN.md「用字」禁用字）：
   - 標籤：「管線（例 nf-core/ampliseq）」／"Pipeline (e.g. nf-core/ampliseq)"；「版本（例 2.18.0）」／"Version (e.g. 2.18.0)"；「模組名稱（站台 module load 使用的名稱，例 biology/nf-core-ampliseq/2.18.0）」／"Module name (the name used by module load on the site, e.g. biology/nf-core-ampliseq/2.18.0)"；「管線資料夾變數（模組設定的環境變數名稱，例 NFCORE_AMPLISEQ_HOME）」／"Pipeline folder variable (the environment variable the module sets, e.g. NFCORE_AMPLISEQ_HOME)"；按鈕「登記」／"Register"、「移除」／"Remove"、「確認」／"Confirm"、「返回」／"Back"。
   - notice：`added_queued`「已登記，並已排入使用前檢查。」／"Registered. A pre-use check has been queued."；`added_no_agent`「已登記。站台代理目前離線，使用前檢查將於代理上線後執行。」／"Registered. The site agent is offline; the pre-use check will run when it connects."；`added_not_checkable`「已登記。此運算環境類型不執行使用前檢查。」／"Registered. This type of compute environment has no pre-use check."；`removed`「已移除。」／"Removed."；`gone`「此管線版本已不在清單中。」／"This pipeline version is no longer registered."
   - `g_reg_bad`（`/launch` 第 3 步提示）改為「此管線版本尚未在所選運算環境登記，請先至設定頁登記。」／"This pipeline version is not registered on the selected compute environment. Register it on the Settings page first."（設定頁連結保留）。`e_reg`（POST 被拒的錯誤句）不動。
5. **不新增 MCP 工具**；parity 表把兩個動作列為 WEB_ONLY，理由「寫入需在網頁確認頁確認」。

## 失敗先行測試
`test_web_settings_register.py`：
- 動作層：`confirmed_by` 缺少或不是三個管道之一＝拒絕且資料庫不變；新增成功（清單多一筆、排了一次檢查、回傳 preflight 值）；同 pipeline＋revision 再登記＝取代；移除成功且不排檢查；移除不存在＝changed False；他人環境＝找不到且不變。
- 網頁：第一步不寫資料庫、回確認頁且列出六項；確認後才寫、303 帶正確 notice；hidden 欄位被改＝403 不寫；缺 CSRF／跨來源＝403；欄位錯（module 含 `..`、home 小寫、revision 是分支名、`acme/rnaseq`、`NF-CORE/x`）＝400 帶欄位錯誤句且保留已填值；`gone` 情況；未知 notice 值不顯示；代理離線時顯示 `added_no_agent` 句。
- 空清單語意：空清單環境登記第一筆後，同環境另一個未登記版本在 `/launch` 出現 `g_reg_bad`；有一筆的環境登記第二筆後那筆不再出現 `g_reg_bad`；移除最後一筆後回到不需登記；設定頁與確認頁在這兩種時機顯示裁決 5 的句子。
- GET /settings 不改資料庫；用 base 版建出的舊資料庫可完整登記（無 migration）；新增中文字串不含禁用字；英文字串齊全。

## 完成標準（done when）
上列全綠；整套 `tests/run_all.sh --timeout 900` 綠；既有釘死測試只加項；ledger 列出每條被改的釘死斷言與理由。

## 環境事實
- `sitePipelines` 每筆 `{pipeline, revision, module, home}`，驗證 `compute_envs.py:263-300`、站台端重驗 `abf_station/rules.py:112-128`；使用前檢查 `site_pipeline` 在 `abf_station/handlers.py:233`。範例 `configs/sites/nchc-nano4-ce.json:6`。
- 寫入必經人工管道：`actions/__init__.py` 的 `_require_human`、`TERMINAL／ELICITED／PAGE`。
- 平台不開對外連線（`docs/PLATFORM.md` :323、:382）；本任務不需要任何連線。

## 不做
- 不新增／刪除運算環境本身；不幫使用者裝模組；不從網路查模組清單；不改驗證規則、不放寬安全標頭；不做 MCP 工具；不動 `e_reg`。

## 裁決
1. `test_st08_still_read_only` 原釘「中欄沒有任何表單」。本任務是維護者 10-28 明確要求的寫入功能：改成中欄只允許本任務的表單（purpose `settings-pipeline`），其餘斷言（沒有權杖清單 action、GET 不改資料庫）不動。
2. 確認頁用「欄位雜湊綁進 CSRF」的無狀態做法，因為既有 `confirmations` 表的 `kind` 有 CHECK 限制且 `approve` 會排 job，套用需要 migration；登記是改設定、可逆、可重做（取代／移除不存在皆無副作用），不需要「只能用一次」。
3. 不做 MCP 工具：避免新增 AI 可呼叫的寫入工具（憲法要求每個寫入工具附拒絕測試與確認管道），網頁先行。
4. 確認頁沿用 ADR 0006「每個寫入都經人確認」。
5. 空清單＝送出時直接取用 nf-core 官方版本是既有行為（`web_board.py:959-965`），不改；設定頁在空清單環境表單上方顯示：「此環境目前未登記管線：送出時直接取用 nf-core 官方版本。登記第一筆後，只能送出已登記的管線版本。」（en: "No pipelines are registered here: runs use the nf-core release directly. Once you register one, only registered pipeline versions can be run here."）

6. （10-28 第三次合約退回後）**notice 帶環境名**：303 改為 `/settings?notice=<值>&ce=<名>#ce-<名>`；`ce` 只在是登入者自己的環境時採用，否則 notice 顯示在頁面頂端。
7. **第二步失敗**：動作層回錯誤（環境已不是自己的或已不存在、`clean()` 退回、其他拒絕）＝回 400 重畫設定頁，在該環境列上方（不是自己的環境則頁首）顯示「✕ 未能完成：<動作層回的原因>」（en: "✕ Not completed: <reason>"）；不寫入。
8. 第二步移除回 `changed: False`＝notice `gone`。
9. 使用前檢查的對應：helper 回傳改成結構化值（CLI 仍印原句，輸出逐字不變）——成功排入＝`added_queued`；代理離線／沒有代理＝`added_no_agent`；環境類型不檢查＝`added_not_checkable`；其他拒絕＝新增 notice `added_check_refused`，句子「✓ 已登記。使用前檢查未能排入，請稍後於設定頁重新登記以再次檢查。」（en: "✓ Registered. The pre-use check could not be queued; register it again later on the Settings page to retry."）。notice 白名單加入此值。
10. 第一步的不寫入檢查放在動作層第三個公開函式 `check_site_pipeline_change(...)`（只讀），parity 表列在 INTERNAL（或該表既有的「網頁專用的唯讀輔助」類），理由「網頁兩步驟的第一步」。
11. 表單上方放圖例「* 必填」／"* Required"，照 DESIGN.md「用字」第 4 條。
12. 每個 notice 與錯誤句前加符號：成功 `✓`、已不在 `○`、失敗 `✕`（沿用設定頁既有 `_chip` 寫法）。
13. 同時兩個登記互相覆蓋：不處理（單人單頁，風險低）。
14. **合約規則**：本計畫已涵蓋的範圍外，未明寫的細節由 verifier 依專長守則與既有畫面慣例自行決定預期值並寫進 TC，不再以「計畫未寫」退回；只有「照計畫字面無法實作」或「與憲法／ADR 衝突」才算阻擋。

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
