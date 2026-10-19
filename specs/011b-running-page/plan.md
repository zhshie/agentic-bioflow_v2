# Plan 011b: running stage page + formal notice component (read-only)

- Branch `feat/011b-running-page`, base v3 (011a #127 merged). Tier B (new screens). kind: ui + backend.
- Authority: `DESIGN.md` / `PRODUCT.md` at the repo root — screen 7 (Running stage), "Formal notices", "States". Maintainer 2026-10-19 on 011a: 「網頁外框可暫定這版 但可以更好」.

## Scope
N1 Formal notice component (DESIGN.md "Formal notices"): box with level pill (symbol + text), analysis name (mono), time at right; one-line title; a definition list of fields (問題／原因／可選動作); buttons area. In this slice buttons render greyed 「之後開放」 (writes come with 012/011c). Replace the one-line items in 「現在」's 需要注意 card with this component: failed run → level "! 需要處理 / Action needed", fields 問題 = failed step name (first failed task name from get_run), 原因 = failure_reason first line (… cut rule from R10 stays), 可選動作 = 「續跑／重跑（之後開放）」; lost run → same level, 問題 = 失聯, 原因 = 三次心跳沒有回應 (or the platform's own wording if it has one). No error codes in titles, no coloured side stripes.
N2 Running stage page (screen 7) for the selected run, read-only: title row (name + state badge; Resume / Re-run shown greyed 之後開放); four summary cards: current step (latest running process name from get_run if present, else —), duration (Asia/Taipei start → now or end, human format), compute (compute environment name if get_run has it, else —), cost (`SU —`); Tasks bar + legend (the seven COUNT_FIELDS with zh/en labels as 011a C6); this run's notices (N1 component); tabs Tasks / Logs / Run info / Configuration / Metrics as server-side links (`?tab=`), zero JS:
  - Tasks: failed tasks table (name, exit code, error message first line, workdir if present).
  - Run info: fields get_run returns (id, name, status, start, end, launch facts it already exposes such as cancel_requested_at if present).
  - Logs, Configuration, Metrics: grey 「之後開放」 panel (Logs arrives when read_task_log, PR #138, lands; do not depend on it).
N3 Owner rule, 404 rule, parity tables, CSP single stylesheet, no style=, no script, no external URL, ?lang=en with links keeping lang — all as 011a. New route only if needed (prefer query params on existing `/`); if a route is added, add it to the pinned route set and parity WEB_ROUTES with its read action.
N4 Tests first: component renders the exact fields for a failed and a lost run (zh and en); 需要注意 card uses the component; running page shows the four cards, tasks bar with seven labelled counts, tabs links keep `lang`; greyed buttons are not forms/links; no write route added; nothing stored (no new table/column). Existing 011a tests stay green; any changed pin logged in the ledger (old/new/reason).
N5 Manual: screenshots desktop 1440 and phone 390 (CDP device emulation, scrollWidth == clientWidth), zh and en, of 「現在」 and a failed run's running page.

## Out of scope
Any write action from the web, upload, launch, results stage (011c), cost page (012d), chat (014), JS.

## 專長守則（ui）

# 專長守則：ui（改畫面的任務）

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

# 專長守則：backend（動作層、資料、權限）

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
