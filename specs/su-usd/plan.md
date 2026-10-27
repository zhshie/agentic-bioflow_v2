---
id: su-usd
title: 國網 SU 旁並列「約 US$」：SU × 每 SU 新台幣價 ÷ 設定檔裡的匯率
tier: B
kinds: ui, backend
lane: L7-web-redesign
base: v3
source: 維護者 2026-10-25「SU能否直接換成美元?」→ 選「做成『SU（約 US$）』並列」
---

# su-usd

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/su-usd/plan.md`。**只處理本任務**。

## 目標
網頁上每個顯示國網 SU 的數字，旁邊多一個「約 US$」：例如「51.50 SU（約 US$0.16）」。SU 照舊是主數字（國網餘額用 SU 對帳）；美元只是讓人跟雲端費用放在一起比。

## 維護者原話（verifier 出題用）
1. 「SU能否直接換成美元?」（2026-10-25）
2. 選項「做成『SU（約 US$）』並列」（2026-10-25）

## 範圍：檔案
- `configs/sites/su_rates.json`（加兩個鍵，見作法 1）
- `platform/abf_platform/su.py`（新函式 `usd_of(su, site, rates)`；不改既有函式行為）
- `platform/abf_platform/actions/__init__.py`（`my_usage` 的 `su` 與每列、`get_run` 的 `su` 各加 `usd_approx`）
- `platform/abf_platform/web_cost.py`、`platform/abf_platform/web_board.py`（只限顯示 SU 的地方：抬頭、run 頁「費用」卡、費用頁 SU 卡與表格）
- 釘住 SU 顯示字串、`my_usage`／`get_run` 回傳鍵集合、MCP BASELINE 描述的既有測試：只准加項，ledger 逐條列
- 新測試檔 `platform/tests/test_su_usd.py`
- `docs/PLATFORM.md`（一段：怎麼算、匯率在哪改、多久改一次）

## 作法
1. `su_rates.json` 頂層加：
   - `"su_plan_type": "nstc"`（`nstc`／`academic`／`industry` 之一；維護者的計畫 mst109178 是國科會計畫）
   - `"usd_twd": {"rate": 32.0, "as_of": "2026-10-13", "source": "https://moneyexchangerate.org/currencyexchange/twd/usd/40400", "note": "1 USD = rate TWD；每月手動更新一次"}`
2. `su.usd_of(su, site, rates)`：每 SU 新台幣價＝該站 `twd_per_su[plan_type]`（站台沒寫就用頂層 `<plan_type>_twd_per_su`）；`usd = su × 價 ÷ rate`。任一項缺（SU 為 None、價為 null、匯率缺或 ≤0、plan_type 不在三者內）→ None。不四捨五入內部值。
3. 回傳：`my_usage` 的 `su` 多 `usd_approx`（數字或 None）與 `usd_rate_as_of`（字串）；每列 `usd_approx`（國網列才有數字，雲端列 None）。`get_run` 的 `su` 多 `usd_approx`。MCP 工具描述各補一句「usd_approx 是依設定檔匯率的約略換算」。
4. 顯示：`<SU 數字> SU（約 US$<兩位小數>）`；英文 `<SU> SU (≈ US$<x.xx>)`。`usd_approx` 為 None → 只顯示 SU，不出現「約 US$」。小於 0.01 顯示「約 US$0.01 以下」／「≈ under US$0.01」。費用頁註腳那句之後加一句：「SU 換美元依 <as_of> 匯率約略換算，不是帳單。」（英文對應）。抬頭目前不顯示數字（保持不變）。
5. 平台不連網、不抓匯率；匯率只來自設定檔。零 JS、無 `style=`、單一樣式表、英文版無中文、390 px 無橫捲。

## 失敗先行測試
- `test_su01_usd_of`：nano4、nstc、rate 32 → 51.5 SU → 51.5×0.1÷32；缺價／缺匯率／rate 0／plan_type 錯 → None。
- `test_su02_my_usage_has_usd_approx_and_mcp_same`：國網＋雲端各一筆；`su.usd_approx` 正確；雲端列 None；MCP 與動作層相同。
- `test_su03_cost_page_shows_su_with_usd`：卡片與國網列顯示「SU（約 US$…）」；雲端列不出現「約 US$」重複；註腳句含 as_of 日期。
- `test_su04_run_page_cost_card`：run 頁費用卡同格式；SU 未知時只有「—」。
- `test_su05_tiny_amount`、`test_su06_english`、`test_su07_constraints`（無 script、無 style=、CSP、英文無中文）。

## 完成標準
上列測試綠；GREEN at HEAD、CI 綠；ledger 列出每個改寫的既有斷言。截圖由 developer-agent 補。B 級畫面：維護者已裁示要這個樣子，verifier 通過＋CI 綠＋截圖給他看，他回好才合。

## 不做
不自動抓匯率、不把 SU 換成新台幣顯示、不改雲端費用、不改抬頭、不加設定頁輸入欄。

## 裁決
1. 已知只在 ext4 鏡像環境紅、可接受：test_station_packaging、test_su_packaged、Nextflow e2e 的 ERROR（需第二支 Nextflow）、test_cli tc035、test_guidance tc404、test_station_envs 兩條（打包或 starlette）。
2. 測試請用 `wsl.exe -d Ubuntu -- bash -lc '~/.local/bin/abf-fast-suite <wt 的 /mnt 路徑> --pytest tests/<file>.py'`；不要直接在 /mnt/c 跑 pytest。
3. `test_su_packaged` 會檢查 `su_rates.json` 有沒有被包進 wheel；新增的鍵不影響。

4. （10-25，解 BLOCKED）run 頁「費用」卡**這次開始顯示真實 SU**：讀 web 已拿到的 `get_run` 結果的 `su`（不得另開讀取路徑）。有數字 → `<SU> SU（約 US$x.xx）`；SU 未知（None）→ 保持既有的「SU —」原字，既有斷言不動。種子 run 因此有了真實 SU 而讓既有斷言變紅的，只准把期望字串換成新顯示，ledger 逐條列。
5. SU 為 0 → 只顯示「0.00 SU」，不加「約 US$」（美元 0 視同不顯示）。0 < 美元 < 0.01 → 「約 US$0.01 以下」。
6. 設定檔缺 `usd_twd` 或 `rate`／`as_of` → `usd_approx` 與 `usd_rate_as_of` 都是 None，頁面不出現「約 US$」，註腳那句也不出現。
7. 不動資料表、不存任何新資料，所以不需要 migration（PR 說明寫明）。
8. `docs/TESTING.md` 加入範圍：新增一節「SU 約 US$」手動步驟（390 px、中英、註腳日期）。
9. 「雲端列不重複」＝雲端卡片與雲端列沿用原本 US$ 顯示，不加「約 US$」。
10. 範例 `0.16`／`US$0.16` 等只是示意，測試以公式計算值為準。

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
