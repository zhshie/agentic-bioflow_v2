---
id: settings-pick-installed
title: 設定頁登記管線改成「從站台已安裝清單挑選」；雲端環境不顯示登記
tier: B
kinds: ui, backend
lane: L32-web-settings-v2
branch: feat/settings-pick-installed
base: v3（#270 合併後開分支；它只改 handlers.py 檔頭註解）
source: 維護者 2026-10-29 看 #259 截圖後：「我不太清楚登記管線哪邊o不ok，不知道怎麼填」「同意，而且nano4有裝好管線的情況與自己租的伺服器狀況也不一樣」
---

# settings-pick-installed

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/settings-pick-installed/plan.md`。**只處理本任務**。

## 目標
#259 的登記表單要人自己打四格，其中「模組名稱」「管線資料夾變數」只有懂叢集的人填得出來，維護者本人看不懂。改成：叢集環境（slurm）由站台代理讀出站台已安裝的 nf-core 模組，設定頁給下拉選單，人只選「哪個管線、哪一版」，其餘兩格由平台從讀到的清單帶入；雲端環境（Google Batch／AWS／Azure）每次都直接取用 nf-core 官方版本，設定頁不顯示登記表單，只說一句這件事。手動四格保留在「進階」裡給管理者。

## 維護者原話（verifier 出題用）
1. 「我不太清楚登記管線哪邊o不ok，不知道怎麼填」（10-29）→ 一般人不必知道模組名稱與環境變數就能完成登記。
2. 「同意，而且nano4有裝好管線的情況與自己租的伺服器狀況也不一樣」（10-29）→ 叢集與雲端分開處理；叢集上沒有模組系統或沒裝任何 nf-core 模組時，要說清楚並照常可送出（取用官方版本）。
3. 「登記管線要做，畢竟是裝在使用者自己租的伺服器或國網。」（10-28，仍適用）
4. 「先把功能做起來吧，以後再改美觀」（10-23，仍適用）

## 範圍：檔案
- `platform/abf_station/handlers.py`：preflight 對 slurm 環境多做一步只讀的「站台已安裝管線」盤點（作法 1）。
- `platform/abf_platform/actions/__init__.py`：新增只讀 `site_pipeline_inventory(...)`；`register_site_pipeline` 新增「依清單挑選」路徑（作法 2）。
- `platform/abf_platform/web.py`：`POST /settings/pipelines` 接受新欄位 `pick`；新增「重新讀取站台清單」按鈕的路由（排一次 preflight）。
- `platform/abf_platform/web_settings.py`：環境區塊依類型分三種畫面（作法 3）。
- `platform/abf_platform/web_board.py`：只限 STRINGS 新字串。
- 新測試檔：`platform/tests/test_settings_pick_installed.py`、`platform/tests/test_station_site_inventory.py`（或併入既有 station preflight 測試檔，ledger 註明）。
- 被逐字釘住、必須跟著改的既有測試：只加不刪、ledger 逐條列（#259 的 `test_web_settings_register.py` 預期會有幾條要改：表單結構從四格變成下拉＋進階）。
- `docs/SETTINGS.md`（:329「Register from the web page」段改寫）、`docs/TESTING.md`（手動一節：nano4 真站台按「重新讀取」後下拉出現 `nf-core/ampliseq 2.18.0`，選它登記，確認頁顯示 `biology/nf-core-ampliseq/2.18.0` 與 `NFCORE_AMPLISEQ_HOME`）。

## 作法
1. **站台盤點（只讀）**：只在 slurm 環境、`connect` 通過後執行，一次 ssh 呼叫，指令固定、不含任何使用者輸入：
   列出 `module -t avail` 中名稱符合 `(^|/)nf-core-[a-z0-9-]+/[0-9A-Za-z._-]+$` 的模組（最多 200 筆），對每筆執行 `module show <模組>`，抓出它設定的 `NFCORE_[A-Z0-9_]+_HOME` 變數名。
   - 結果放進 preflight 回傳的**獨立欄位** `site_inventory`（不是 `checks` 的一項，不影響 preflight 的通過與否）：
     `{"status": "ok"|"no_module_system"|"error", "items": [{"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "module": "biology/nf-core-ampliseq/2.18.0", "home": "NFCORE_AMPLISEQ_HOME", "home_source": "module"|"guessed"}], "read_at": <時間>}`。
   - `pipeline`＝`nf-core/` ＋ 模組名中 `nf-core-` 後、`/` 前那段；`revision`＝最後一段。
   - `module show` 沒找到變數名時用規則推算：`NFCORE_` ＋ 名稱轉大寫、`-` 換 `_` ＋ `_HOME`，`home_source="guessed"`。
   - `module` 指令不存在＝`no_module_system`、`items: []`。
   - 每筆都先過 `rules.clean_environment` 同一套欄位驗證，過不了的那筆丟掉（不是整份失敗）。
   - 雲端類型不跑盤點、沒有這個欄位。
2. **動作層**：
   - `site_pipeline_inventory(platform_path, *, ce, caller)`：只讀，回該環境**最近一次**有 `site_inventory` 的 preflight 結果（沒有＝`{"status": "none"}`）；不是自己的環境＝找不到。
   - `register_site_pipeline` 的 module／home 由呼叫端傳入的方式保留（進階表單、CLI 用）；網頁「挑選」路徑在 web.py 依 `pick`（＝`pipeline` ＋ 空白 ＋ `revision`）**在伺服器端**從最新清單查出 module 與 home 再呼叫，不信任瀏覽器送來的 module／home。清單裡找不到那筆＝400「站台清單中沒有這個版本，請按「重新讀取站台清單」。」。
   - 「重新讀取站台清單」＝排一次 preflight（沿用 #259 的共用 helper 與 notice 對應：`added_*` 之外新增 `inv_queued`／`inv_no_agent`）。這是寫入 jobs 表的動作，走與 #259 相同的 CSRF＋same-origin；不需確認頁（只讀檢查，不改設定）。
3. **畫面**（每個環境區塊）：
   - **雲端類型**（`compute_envs.PLATFORM_HOST_TYPES`）：不顯示已登記清單與任何表單，只一句「此環境每次送出都直接取用 nf-core 官方版本，不需登記管線。」。若資料庫裡該環境意外有 `sitePipelines`，照列並保留「移除」（不讓資料卡住）。
   - **slurm，清單 `ok` 且有項目**：已登記清單（同 #259）＋「登記管線」：一個必填下拉「站台已安裝的管線版本」，選項文字 `nf-core/ampliseq 2.18.0`，已登記的那幾筆不列；`home_source="guessed"` 的選項後加「（變數名稱為推算）」；下方灰字「清單讀取於 <時間>」＋按鈕「重新讀取站台清單」；按「登記」→ 沿用 #259 確認頁（顯示六項，含帶入的模組名稱與變數）。
   - **slurm，尚未讀過（`none`）**：一句「尚未讀取此站台已安裝的管線。」＋「重新讀取站台清單」按鈕。
   - **slurm，`no_module_system` 或清單空**：「此站台沒有找到已安裝的 nf-core 模組：送出時直接取用 nf-core 官方版本。若管線裝在模組以外的位置，請使用下方「進階：手動填寫」。」
   - **slurm，`error`**：「✕ 未能讀取站台清單：<原因>」＋「重新讀取站台清單」。
   - 所有 slurm 狀態底部都有收合的 `<details>`「進階：手動填寫（管理者用）」，內容＝#259 原本四格表單，行為不變。
   - 只用現有 class 與 DESIGN.md token；不改 STYLE（D13 釘 sha256）。
4. **字串**（中英皆正式書面語，不含 DESIGN.md 禁用字；英文對應句由 verifier 依既有慣例訂）。
5. 不新增 MCP 工具；parity 表把 `site_pipeline_inventory` 列為網頁專用唯讀輔助。

## 失敗先行測試
- 站台：假 site 回 `module -t avail` 含 `biology/nf-core-ampliseq/2.18.0`、`biology/nf-core-rnaseq/3.14.0`、`biology/Nextflow/26.10.0`、`foo/nf-core-bad;rm/1` → items 只有前兩筆；`module show` 有 `setenv NFCORE_AMPLISEQ_HOME` → `home_source=module`；rnaseq 沒有 → `NFCORE_RNASEQ_HOME`、`guessed`；`module: command not found` → `no_module_system`；盤點失敗不改變 preflight 的 verdict；雲端環境的 preflight 沒有 `site_inventory`；指令字串裡不含任何來自 env 設定的值。
- 網頁：雲端環境區塊沒有 `<form` 登記表單、有那一句；slurm 四種狀態各自的句子與按鈕；下拉不列已登記的版本；`pick` 送出後確認頁顯示伺服器查出的 module／home；瀏覽器另外夾帶 `module=evil` 被忽略；`pick` 不在清單＝400 且不寫；「重新讀取」排了一次 preflight、跨來源或缺 CSRF＝403；進階表單行為與 #259 相同；GET /settings 不改資料庫。

## 完成標準（done when）
上列全綠；整套 `tests/run_all.sh --timeout 900` 綠（在背景跑並等待，見裁決）；被改的既有斷言在 ledger 逐條列理由；1440／390 × zh／en 四種狀態畫面沒有橫向捲動。

## 環境事實
- nano4 實測（`memory/reference/nchc-nano4-probe-2026-10-20.md`，10-20、10-23）：Lmod；非互動 ssh 裡 `module` 可用；`module spider nf-core` 看得到 `biology/nf-core-ampliseq/2.18.0`、`nf-core-atacseq/2.1.2` 等；`module load biology/nf-core-ampliseq/2.18.0` 會設 `NFCORE_AMPLISEQ_HOME`。`module avail` 輸出很長（只看前 100 行會漏）。
- 既有 sitePipelines 形狀與驗證：`compute_envs.py:263-300`、`abf_station/rules.py:112-128`、`configs/sites/nchc-nano4-ce.json:7`。
- 站台 preflight：`abf_station/handlers.py:264` 起；`_module_chain`、`_site_pipeline_command` 可參考寫法。
- jobs 表的 kind 有 CHECK 限制，所以不新增 job kind，盤點掛在 preflight 裡（避免 migration）。
- 平台不開對外連線；本任務只透過站台代理讀叢集。

## 不做
- 不新增 job kind、不做 migration；不幫使用者裝模組；不改 `sitePipelines` 驗證規則；不改安全標頭與 STYLE；不做 MCP 工具；不處理「模組以外位置」的自動偵測（留進階手填）。

## 裁決
1. 整套測試一律 `run_in_background` ＋等待迴圈跑 `tests/run_all.sh --timeout 900`（桌機前景 10 分鐘上限會砍掉）。
2. 測試字串不寫完整金鑰樣式（憑證掃描會擋）；需要時用字串相接組出。
3. `platform/pyproject.toml` executor 不能改；需要改就寫進報告退回。
4. 合約規則同 settings-register-pipeline 裁決 14：計畫未明寫的細節由 verifier 依專長守則與既有慣例訂預期值，不以「計畫未寫」退回。
5. worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 會因讀不到 git 而紅＝環境問題，以 CI 為準，ledger 註明即可。

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
