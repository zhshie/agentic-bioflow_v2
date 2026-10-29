---
id: settings-ce-table-mobile
title: 設定頁「計算環境」表格在手機寬度（≤640px）改成一列一張卡片，每個欄位帶自己的標籤，不再把字切成「Nam/e」「Av/aila/ble」
tier: B
kinds: ui
lane: L27-ce-table-mobile
branch: fix/settings-ce-table-mobile
base: origin/v3@68de6de04fc57c06515521a53ca14531959fb313
source: 維護者每日簡報（見下）；截圖 shots-1029/settings-register-390-en.png、-zh.png
---

# settings-ce-table-mobile

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/settings-ce-table-mobile/plan.md`。**只處理本任務**。純 CSS＋最少的樣板標記，不改行為、不改資料、不改任何字串。

## 目標
390 px 寬的手機上，設定頁「運算環境」表格的六欄各只剩約 40 px，字被硬切（截圖：「Nam/e」「Av/aila/ble」「Regis/tered/pipeli/nes」）。改成：≤640 px 時每個環境一張卡片，六個欄位上下排列、各自帶標籤；整頁沒有橫向捲動；1440 px 的畫面看起來與現在一樣。

## 維護者原話（verifier 出題用）
1. 「發現一個問題：手機寬度下「計算環境」表格太窄，字被切成「Nam/e」「Av/aila/ble」，看得到但難讀。我會開一件 B 級修正（手機改成上下排的卡片）」（每日簡報）
2. 「先把功能做起來吧，以後再改美觀」（10-23，仍適用：只修可讀性，不重新設計）

## 範圍：檔案
可改（只這兩個產品檔＋一個測試檔＋一份文件）：
- `platform/abf_platform/web_settings.py`——只改兩處標記：`_ce_row`（:159-160 的 `<td>` 加 `data-label`，標籤取自既有的 `t["th_*"]`，**不新增任何字串**）與 `_compute`（:212 的 `<table class="tbl">` 加一個 class `ce`）。
- `platform/abf_platform/web_board.py`——只在 CSS 字串 `STYLE`（:132 起）加一段 `@media (max-width:640px){…}`，放在既有 `.ptbl` 手機規則（:246-247）旁。**不碰 `STRINGS`（:35 起）。**
- `platform/tests/test_web_settings_ce_mobile.py`（新檔）
- `platform/tests/test_web_settings.py`——只准把 `:201` 與 `:224` 兩行的 `"<td>" in r` 改成 `"<td" in r`（原因見作法 4；不准改其他斷言，ledger 逐行列出 diff）
- `docs/TESTING.md`——新增一小節手動步驟（Playwright 四張截圖＋溢出檢查，見失敗先行測試 C）
- 可選：`scripts/dev/check_settings_mobile.py`（新檔，Playwright 檢查腳本，仿 `scripts/dev/check_chrome_login.py`）

**不准碰**：
- `platform/abf_platform/web_upload.py`、`web_launch.py`、`web_cost.py`、`web_finished.py`、`web.py`
- 任何 `STRINGS` 字典與任何中文／英文用詞（`web_settings.py:26-58`、`web_board.py:35-130` 的字串一字不動）
- `.tbl` 的既有規則（`web_board.py:224-225`）：它還被執行頁（web_board.py:629、:661）與費用頁（web_cost.py:136）使用，**不能改**，只能用新 class `ce` 圈定
- 其他頁面的表格、`.ptbl` 規則、DESIGN.md／PRODUCT.md、動作層、資料庫

**與 web-wording-sweep 車道的衝突面**：該車道正在改 web 樣板與 `web.py` 的中文用詞。`web_settings.py` 與 `web_board.py` 兩個檔它也會改，所以**會有檔案層級的相交**；但本任務的改動是**僅限標記與 CSS**（`_ce_row` 一行、`_compute` 一行、`STYLE` 尾端一段），與它改的 `STRINGS` 字典是不同的行段，預期只在 rebase 時需要手動合並相鄰行，不會有語意衝突。若該車道先併入，本分支 rebase 後要重新核對 `data-label` 取的 `t["th_*"]` 鍵名沒被改掉。

## 作法
1. **標記**（`web_settings.py`）：
   - `_compute` :212 改成 `<table class="tbl ce">`。
   - `_ce_row` :159 的六個 `<td>` 依序加 `data-label`，值＝`esc(t["th_name"])`、`th_platform`、`th_status`、`th_agent`、`th_pipes`、`th_used`（與 :211 表頭同一組鍵，故中英自動一致，零新字串）。`<th>` 不動。
2. **CSS**（`web_board.py` `STYLE` 尾端，`@media (max-width:640px)`；全部選擇器以 `.tbl.ce` 開頭，基礎規則一條也不加，因此 >640 px 零影響）：
   - `.tbl.ce,.tbl.ce tbody{display:block}`；`.tbl.ce thead{display:none}`（沿用 `.ptbl` 在 :246 的做法；表頭標籤改由每格 `::before` 顯示，螢幕閱讀器仍讀得到 `data-label`）。
   - `.tbl.ce tr{display:block;background:var(--raised);border:1px solid var(--line);border-radius:6px;padding:8px 12px;margin:0 0 12px}`。
   - `.tbl.ce td{display:grid;grid-template-columns:minmax(6em,8em) minmax(0,1fr);gap:8px;border-bottom:0;padding:4px 0}`；`.tbl.ce td::before{content:attr(data-label);color:var(--muted);font-size:12px}`。
   - 配色只用既有變數（`--raised`、`--line`、`--muted`），自動跟著深色模式。
   - 不加 `word-break`；既有 `overflow-wrap:anywhere`（:225）只在真的放不下的長字串（站台代理名）才折，標籤與狀態詞因欄寬足夠不再被切。
3. 斷點取 640（維護者要求「約 640」；`.main` 已在 900 以下單欄，:248）。
4. **為何要動兩行既有測試**：`test_web_settings.py:201` 用 `"<td>" in r` 找資料列、`:224` 用 `split("</td>")` 取格；`<td>` 一旦帶屬性，`:201` 會找不到任何列而變紅（證據：`origin/v3:platform/tests/test_web_settings.py:201,224`）。標籤放屬性是唯一不改格內文字的做法（放 `<span>` 會讓 :224 的 `startswith` 斷言失敗），所以改成 `"<td" in r`，語意不變。
5. 不新增路由、不碰資料與動作。

## 失敗先行測試
先寫、現在會紅的；用專案自己的指令，在 `platform/` 下 `python -m pytest tests/test_web_settings_ce_mobile.py`（完整 gate：`bash tests/platform_test.sh`，在 WSL 跑，見 CLAUDE.md「Running tests」）。

**A. 渲染頁測試**（新檔，沿用 `test_web_settings.py` 的 `w`／`page`／`rows_of` fixture 與 `two_envs`）：
- `test_ce01_table_has_ce_class`：`GET /settings` 的運算環境區含 `<table class="tbl ce">`；現在是 `class="tbl"`，紅。
- `test_ce02_every_cell_labelled`：兩個環境的每一資料列有 6 個 `<td data-label="…">`，標籤依序等於該頁語言的 `th_name…th_used`；中英各跑一次（`?lang=en` 為「Name、Platform、Status、Site agent、Registered pipelines、Last used」）。
- `test_ce03_mobile_rule_present`：回應的 CSS 含 `@media (max-width:640px)`，且其中出現 `.tbl.ce`、`attr(data-label)`、`thead{display:none}`。
- `test_ce04_no_base_rule_leak`：把 CSS 中所有 `.tbl.ce` 規則取出，確認每一條都在 `@media (max-width:640px)` 區塊內（1440 px 不受影響的靜態證據）。
- `test_ce05_other_tables_untouched`：執行頁與費用頁的表格仍是 `<table class="tbl">`、`<td>` 不帶 `data-label`。
- `test_ce06_no_new_strings`：`web_settings.STRINGS` 與 `web_board.STRINGS` 的鍵集合與值，與 base 相同（用 base 快照寫死鍵數，或 diff 證據貼 ledger）。

**B. 既有測試不變的對照**：`test_web_settings.py`、`test_web_settings_register.py`、`test_web_parity.py`、`test_web_board.py` 全綠；`git diff origin/v3...HEAD -- platform/tests` 除新檔外只有 `test_web_settings.py` 兩行（:201、:224）。依 README 通例，這類「只能看 diff」的案例由 executor 貼證據到 ledger.md，verifier 自行重跑核對。

**C. Playwright 截圖與溢出（手動／腳本，不進 CI，CI 沒有 Playwright）**：
- 在 1440 與 390（`is_mobile=True`，用裝置模擬、不是拉視窗）× 中文與 `?lang=en`，共 4 張，存進 `specs/settings-ce-table-mobile/screenshots/`；環境用有兩個運算環境、其一有已登記管線的資料（同 `shots-1029` 的 gcb1／gcb3）。
- 斷言 1：四種組合都 `document.documentElement.scrollWidth <= document.documentElement.clientWidth`（數字寫進 PR）。
- 斷言 2（可行，盡力）：390 下對 `.tbl.ce td` 內每個文字節點用 Range 取 `getClientRects()`，同一個「詞」（以空白切）若跨多個矩形且該詞長度 ≤ 20 字元（英文詞、中文以整個標籤計），判為「詞中折行」。預期長字串（如 `nf-core/rnaseq 3.14.0`）可在 `/` 折，不算失敗。此斷言啟發式，若 Playwright 取不到穩定結果，退成人工看 4 張圖並於 ledger 註明（verifier 不以此退回，但「欄位標籤被切」仍判 FAIL）。
- 斷言 3：1440 版與 base 分支同資料的截圖逐像素比對相同（或差異 0）。

## 完成標準（done when）
- A 組六條全綠；B 組全綠；`bash tests/platform_test.sh` 在 WSL 全綠（已知環境紅依 README 通例處理）。
- 390 px 中英各一張截圖：每個環境一張卡、六個欄位各有標籤、沒有「Nam/e」式斷字；scrollWidth ≤ clientWidth。
- 1440 px 截圖與 base 相同。
- diff 範圍只含「範圍」列出的檔；`git diff` 中 `STRINGS` 相關行為零。
- ledger 附：diff stat、四張截圖路徑、兩組 scrollWidth 數字。

## 環境事實
- base：`origin/v3` 在 `68de6de04fc57c06515521a53ca14531959fb313`（2026-10-29 量測）。
- 表格產生處：`origin/v3:platform/abf_platform/web_settings.py:147-160`（`_ce_row`）、`:207-215`（`_compute`；:211 表頭六個 `th_*` 鍵，:212 `<table class="tbl">`）。表頭文字：中 `web_settings.py:26`、英 `:57-58`。
- CSS 在 `origin/v3:platform/abf_platform/web_board.py` 的 `STYLE`（:132 起）：`.tbl{width:100%;table-layout:fixed;…}` :224；`.tbl th,.tbl td{…overflow-wrap:anywhere}` :225（這就是 390 px 下六等分、字被逐字切的原因）；既有手機堆疊先例 `@media (max-width:600px){.ptbl …}` :246-247；`.wb` 單欄斷點 900 :248。
- `.tbl` 另被 `web_board.py:629,661`、`web_cost.py:136` 使用，所以只能加 `.ce` 圈定。
- 檔案層級相交：web-wording-sweep 也改 `web_settings.py`／`web_board.py` 的字串，見「範圍」。
- 手動檢查先例：`docs/TESTING.md:378`（scrollWidth === clientWidth）、`:374`（CDP 或 Playwright `is_mobile` 取 390）、`:582`（參數列堆疊）；Playwright 驅動先例 `scripts/dev/check_chrome_login.py`。
- 專案設計文件：DESIGN.md 規定的變數與深色模式沿用 `STYLE` 既有 token，不另加顏色。

## 不做
- 不改任何字串、翻譯、標籤用詞（那是 web-wording-sweep 車道）。
- 不改 `web_upload.py` 及其他頁面的表格；不改 `.tbl` 既有規則；不把全站表格一起做響應式。
- 不改資料、動作、路由、登記管線表單（`_env_block`）。
- 不重新設計卡片外觀（10-23「以後再改美觀」）；不加新顏色、新圖示、新斷點。
- 不新增 JS。

## 裁決
1. **要不要動兩行既有測試（`test_web_settings.py:201,224`）？** 建議：要，只改 `"<td>"` → `"<td"`，語意不變；不動則 `:201` 會變紅，沒有更小的替代方案（替代：用 `<span>` 放標籤會壞 :224）。
2. **斷點 640 還是沿用既有的 600？** 建議 640（維護者原話「約 640」，且 `.main` 的 24 px 邊距在 600–640 之間表格仍偏窄）；代價是與 `.ptbl` 的 600 不一致，可接受。


### developer-agent 預檢裁決（2026-10-29）
- A. **test_web_settings.py:201、:224 比對字面 `<td>`**：加 data-label 後會失配。**定案：准把這兩行的 `"<td>"` 改成 `"<td"`**（只改比對前綴、斷言意圖不變，不算放寬）；其他既有斷言一字不動。
- B. **斷點**：**定案 640px**（390 寬手機與 600 附近的小平板都要卡片化）。
- C. **派工時機**：與 web-wording-sweep 改同兩個檔（web_settings.py、web_board.py），**等 web-wording-sweep 合併後才派**，base 用那時的 origin/v3；hunk 若撞到以 v3 的文字為準。
- D. **字中斷行的自動檢查**做不到可靠時，改成截圖人工看，不算 FAIL。

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

### 補充裁決 13（2026-10-30 02:1x，executor BLOCKED 後）
- **准重釘樣式表雜湊**：`platform/tests/test_web_settings_register.py` 的 `BASE_STYLE_SHA`（:18）與 `platform/tests/test_clean_page.py` 的 `BASE_STYLE`（:162）加入可改範圍，**只准改常數值**成新 STYLE 的 sha256（clean_page 用前 16 字元）；斷言本身、比對方式、其他行一律不動。`test_settings_pick_installed.py` 只 import 該常數，不准改。
- 理由：這些雜湊是「STYLE 有沒有被意外改動」的快照釘；本任務就是有意改 STYLE，`test_clean_page.py:153-156` 註解顯示每次改 STYLE 都重釘，不算放寬安全網。重釘前 executor 要在 ledger 貼 `git diff` 證明 STYLE 只多了 `@media (max-width:640px)` 那一段。
- 行號以函式名定位（web-wording-sweep 已併入，起點 2552583b）。ce07 改嚴後要重跑。
