# Plan 012b: write actions from the web — launch, resume, re-run, cancel — each through the confirmation page

- Branch `feat/012b-web-actions`, base v3 AFTER 011b merges (same files). Tier B. kind: ui + backend.
- Maintainer 2026-10-19 (via UI/UX session): 「function first: the full analysis flow working end-to-end; visual style later」. DESIGN.md screens 5 (launch stage), 6 (confirmation pages), 7 (Resume / Re-run buttons).
- The action layer already has everything: `request_launch`, `request_cancel`, `request_resume`, `request_relaunch` (they only ASK and create a pending request), `approve` (the PAGE channel at `/c/<id>` already exists and is the human gate, ADR 0006). This slice adds web routes that call the request_* actions for the logged-in caller and redirect to the existing `/c/<id>` confirmation page. The web never confirms by itself; the person presses 送出 on `/c/<id>` as today.

## Scope
W1 Resume / Re-run / Cancel buttons on the running page and on 待處理 notices become real `POST` forms (CSRF token as the login form uses; same-origin check as 009i) → `request_resume` / `request_relaunch` / `request_cancel` → 303 to `/c/<id>`. Refusals from the action (not yours, still running, forgotten, etc.) show on the page as a plain line, nothing queued.
W2 Launch (minimal, functional): a `/launch` page with a plain form: pipeline (text, nf-core name), revision (text, required — pinned), run name, samplesheet (choose from the caller's uploaded samplesheets the platform already confines: `confined_samplesheet` / the uploads area; no new upload here — that is 012c), compute environment (select from `list_compute_envs` for the caller), params (optional textarea of `key: value` lines, parsed server-side, rejected if not simple scalars). Submit → `request_launch` → 303 `/c/<id>`. ⚡ Quick launch from a previous run of this user: prefill the form from that run's confirmed bundle when it is still kept (keep-submissions), else say it is not kept.
W3 Parity: these routes move `launch`, `cancel`, `resume`/`relaunch` (and their request_* targets) from OWED to WEB_ROUTES; the parity test pins the new sets; OWED only shrinks.
W4 Wording: replace every 「要你處理」/「需要處理」 with 「待處理」 (maintainer banned 「要你處理」); level pill becomes 「待處理」/"Pending". Status words: Running / 待處理 / Failed / Done shown as a small coloured square + word; no glyph symbols in new markup (existing glyphs may stay where tests pin them; list them in the ledger for the later visual pass).
W5 Zero JS, single stylesheet, no style=, owner rule, ?lang=en (all new strings zh/en), Asia/Taipei times — as 011a.

## Tests first
Each POST without a session → 303 login; with another user's run → the same not-found as get_run; with a valid run → a pending request exists and the response is 303 to `/c/<that id>`; nothing is queued for an agent until `/c/<id>` is approved (assert the jobs table unchanged); CSRF missing/wrong → 403; cross-origin → refused as 009i; launch form validation (missing revision, unknown compute env, samplesheet outside the caller's area, non-scalar params) → error line, no request created; parity sets updated; 「要你處理」 and 「需要處理」 appear nowhere in platform/.

## Out of scope
Upload and samplesheet creation (012c), the 7-step guided launch with schema-driven parameter groups and workflow diagram (012b-2, later), cost page (012d), results (011c), chat, JS.

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
