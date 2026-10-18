# 測試案例：011a 網頁外殼（web design v1：三欄框架、「現在」首頁、設定頁、唯讀）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
This is the contract REOPENED for web design v1 (plan section "REDO per web design v1": G0-G11, rulings R1-R7, 2026-10-18 night).
It replaces the layout-B contract (confirmed 2026-10-18 earlier). Kind: ui + backend; both specialist rules (專長守則) apply.
There is no spec.md for 011a. The maintainer's own words are in three places: the plan's section 「給維護者」 (3 points, point 2 as ruled by R1),
the ten verbatim quotes in DESIGN.md ("Maintainer's words"), and the plan's TC-H01 to TC-H19 base.
Nothing here invents behaviour the plan, DESIGN.md or the reference demo does not state; the places where the plan is silent are listed in the overview under "我（撰寫者）不確定的地方".
IDs: TC-H, TC-L, TC-D, TC-V, TC-N, TC-K keep their old numbers. A struck-through row (~~ ~~) is superseded and keeps its row; the row that replaces it is named in its last cell.
New rows: TC-S01 to TC-S49, TC-D12, TC-V11 to TC-V18, TC-N12 to TC-N20.
Language: 繁體中文; identifiers (TC-, H, L, S, G, R) and file paths stay as they are.
-->

**規格**：`specs/011a-web-shell/plan.md`（含「REDO per web design v1」與其後的裁定 R1 至 R7）、根目錄 `DESIGN.md`、`PRODUCT.md`、參考稿 `specs/011a-web-shell/design-v1-demo.html`（DESIGN.md 與參考稿不同時以 DESIGN.md 為準）　**總覽**：`test-case-overview.md`

「給維護者」三點（點 2 依裁定 R1 改為頂欄），下面簡稱「維護者 1／2／3」：

1. 登入網頁後看到三欄畫面：左邊是你的 run 清單，專案功能還沒做，頁面會照實寫出來；中間是選到的那個 run 的五階段板；右邊是你所有 run 的進度，照階段分組、用顏色加文字標狀態。
2. 費用讀數「SU —」「雲端 NT$ —」（原文寫「右欄最上面一行『本月 SU — · 雲端 —』」，設計稿 v1 與裁定 R1 把它移到頂欄兩行）。
3. 整頁只能看，沒有會改東西的按鈕。每人只看到自己送出的 run；沒記錄送出者的舊 run 不顯示，只能在本機終端機查。

`DESIGN.md` 裡維護者的十句原話（逐字），下面簡稱「設計原話 1 至 10」：

1. 「進來之後馬上可以看到各個run的狀態與進度 (右側會顯示各個run的進度到哪個步驟)，只有需要使用者決定的才會通知使用者。開啟一個專案、上傳rawdata之後，馬上就看到選pipline的階段，系統直接一個個引導使用者。」
2. 「系統設定先。然後右側有對話框，直接對話系統就會引導使用者快速上手建專案，選pipline條參數等等」
3. 「AI一律先除錯，不是使用者能決定的事情一律直接處理」
4. 「同時跑5-10個」
5. 「做成產品英文版面是必須的」
6. 「Seqera功能太多學習成本高」
7. 「在送出的介面就要有之前abf-v2那些引導的事情，包括選擇pipline (之前設定的 or 新開的)、pipline的流程圖、pipline的參數等等。介面上不要有AI太口語化的回覆，要有制式化的通知呈現 ("樣本表少了 reverseReads 欄，AI 改不了。"這種不行)」
8. 「版面我完全不滿意，請你直接參考 Seqera 以及 Galaxy 的網頁」
9. 「不需要Jev "開關"，只要在設定讓使用者可以放金鑰。」
10. 網頁裡的終端機：維護者已取消。

名詞：

- 「階段」= launch（送出）、running（執行中）、results（結果）、downstream（下游）、finished（完成）五個，網址用 `?stage=` 選。
- 「現在」頁 = 沒選 run 時 `/` 的中欄（設計稿第 1 畫面），有「正在跑」「需要注意」兩張卡。
- 「卡」= 「現在」頁上的一個區塊，裡面一行一個 run。
- 「群組」= 右欄依階段分的區塊。現在只有「執行中」（running、failed、lost）與「結果」（succeeded）兩個真群組，外加一塊灰色「之後開放」。
- 「項目」= 右欄裡一個 run 的整塊（序號與名稱、符號、狀態字、done/total）。
- 「頂欄」= 頁面最上面那條深色細欄（設計稿的 masthead）。
- 「token」= 設計稿規定的顏色、字級、間距、圓角那一組固定數值。
- 「CSP」= 網頁回應附帶的安全標頭，限制頁面能載入什麼。
- 「CJK 字元」= 中日韓文字。英文版的測試用純 ASCII 的 run 名稱與使用者名稱，才能證明「畫面上的字」全部換成英文。
- 「路由集合」= 合併 v3 後的既有路由（含 009i 的 OAuth／同意頁）加上 GET `/` 與 GET `/settings`。
- 「被選取標記」= 同一種標記（執行者自選名稱，如 `aria-current` 加 class），TC-L28 規定樣式表要對它設外框。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 登入後看到三欄畫面與「現在」首頁（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H01a | 維護者 1；H01 | 例外 | 沒有登入（請求沒帶 cookie） | GET `/` | 回 303，轉到 `/login`；回應內容沒有任何 run 資料 | 自動 |
| ~~TC-H01b~~ | ~~維護者 1；H01~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~三欄：左「我的 run」、中、右「本月費用」~~ | 已取代：TC-S10、TC-S11、TC-S19（費用移到頂欄，裁定 R1） |
| TC-H02a | H02 | 功能 | 有網頁密碼的使用者；登入表單沒有 next | 送出正確姓名與密碼 | 回 303 轉到 `/`；不再出現「已登入…請回到 AI…」那個沒有下一步的頁面 | 自動 |
| TC-H02b | H02 | 功能 | 登入表單帶 `next=/c/<32 位十六進位>` | 送出正確姓名與密碼 | 仍轉到那個 `/c/...` 確認頁（既有行為不變） | 自動 |
| TC-H02c | H02 | 例外 | 登入表單帶 `next=//evil` | 送出正確姓名與密碼 | next 被忽略，轉到 `/`，不轉去 `//evil` | 自動 |
| TC-H20a | 維護者 1；決策 6 | 功能 | 使用者有 3 個自己的 run，開始時間各不同 | GET `/` | 左欄 run 清單由新到舊排列 | 自動 |
| ~~TC-H20b~~ | ~~決策 6~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~左欄有「專案與分析（011b）尚未開放」~~ | 已取代：TC-S21（一律灰字「之後開放」，裁定 B4／R7） |
| ~~TC-H20c~~ | ~~決策 6~~ | ~~功能~~ | ~~以姓名 X 登入~~ | ~~GET `/`~~ | ~~左欄底部顯示姓名 X~~ | 已取代：TC-S10（姓名在頂欄右側） |
| ~~TC-H20d~~ | ~~決策 6~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~左欄底部有「設定（尚未開放）」~~ | 已取代：TC-S22（設定頁已存在，裁定 R4） |
| ~~TC-H21a~~ | ~~決策 6~~ | ~~功能~~ | ~~已登入，網址沒有 `?run=`~~ | ~~GET `/`~~ | ~~中欄寫「選一個 run」~~ | 已取代：TC-S32（沒選 run 時中欄是「現在」頁，G4） |
| ~~TC-H21b~~ | ~~維護者 1；決策 6~~ | ~~功能~~ | ~~有一個自己的 run~~ | ~~GET `/?run=<id>`~~ | ~~五階段條，階段之間有箭頭~~ | 已取代：TC-L07 至 TC-L13、TC-S29 |
| TC-H21c | 決策 6；R7 | 功能 | 一個 run：開始 2026-10-17 20:30 UTC、結束 2026-10-18 01:12 UTC，七種工作數各不相同；另一個 run 開始 2026-10-18 01:05 UTC | GET `/?run=<id>`（兩個 run 各一次） | 中欄階段內容顯示：狀態；開始時間「10-18 04:30」與結束時間「10-18 09:12」各自出現（亞洲/台北時區、`MM-DD HH:mm`）；第二個 run 的開始時間顯示「10-18 09:05」（補零）；每個狀態的工作數，各自的數字都出現且與對應狀態配對正確（不得只出現其中一個數字） | 自動 |
| TC-H21d | 決策 6 | 功能 | 一個失敗的 run，`failure_reason` 有文字 | GET `/?run=<id>` | 中欄顯示該失敗原因（Nextflow 的原文） | 自動 |
| TC-H21e | 裁定 3 | 功能 | 選一個 run | GET `/?run=<id>&stage=launch` | 該階段內容顯示「—」與「012b」 | 自動 |
| TC-H21f | 裁定 3 | 功能 | 選一個 run | GET `/?run=<id>&stage=downstream` | 該階段內容顯示「—」與「016」 | 自動 |
| TC-H21g | 裁定 3 | 功能 | 選一個 run | GET `/?run=<id>&stage=finished` | 該階段內容顯示「—」與「013b」 | 自動 |
| ~~TC-H22a~~ | ~~維護者 1；決策 6~~ | ~~功能~~ | ~~已登入，有自己的 run~~ | ~~GET `/`~~ | ~~右欄有五個階段群組~~ | 已取代：TC-L19（兩個真群組加一塊灰色「之後開放」） |
| TC-H22b | 維護者 1；決策 6；裁定 4；C1 | 功能 | 使用者自己的 run：running 2、lost 1、failed 1、succeeded 3 | GET `/` | 右欄「執行中」群組標題寫成「執行中（4）」（running、lost、failed 都算在 running 階段）；「結果」群組標題寫成「結果（3）」 | 自動 |
| TC-H06a | H06；決策 4 | 功能 | 純函數 `stage_of` 對照表 | 用 running、lost、failed、succeeded 各呼叫一次 | running、lost、failed 都得 running；succeeded 得 results | 自動 |
| TC-H06b | H06；決策 4 | 功能 | 一個 succeeded 的 run | GET `/?run=<id>`（不帶 `stage`） | 中欄預設顯示 results 階段 | 自動 |
| TC-H06c | H06；決策 4 | 功能 | 一個 failed 的 run | GET `/?run=<id>`（不帶 `stage`） | 中欄預設顯示 running 階段（失敗屬於 running） | 自動 |
| TC-H08a | 維護者 1；H08；決策 5 | 功能 | 一個 running 的 run | GET `/` | 右欄該 run 帶 running 專屬 class 與文字「執行中」 | 自動 |
| TC-H08b | 維護者 1；H08；決策 5 | 功能 | 一個 succeeded 的 run | GET `/` | 右欄該 run 帶 succeeded 專屬 class 與文字「成功」 | 自動 |
| TC-H08c | 維護者 1；H08；決策 5 | 功能 | 一個 failed 的 run | GET `/` | 右欄該 run 帶 failed 專屬 class 與文字「失敗」 | 自動 |
| TC-H08d | 維護者 1；H08；決策 5 | 功能 | 一個 lost 的 run | GET `/` | 右欄該 run 帶 lost 專屬 class 與文字「失聯/暫停」 | 自動 |
| TC-H08e | H08；決策 5 | 功能 | 四種狀態的 run 各一 | GET `/` | 四個狀態的 class 兩兩不同 | 自動 |
| TC-H08f | H08；決策 5 | 功能 | 一個 run：succeeded 6、cached 2、total 10 | GET `/?run=<id>` | 中欄進度是原生 `<progress>`，value 為 8、max 為 10 | 自動 |
| TC-H08g | H08；決策 5 | 例外 | 一個 run 的 total 為 0 | GET `/?run=<id>` | `<progress>` 沒有 value 屬性（不顯示成 0% 或 100%） | 自動 |
| TC-H10a | H10；決策 2 | 功能 | 選一個 run | 分別用 `?stage=launch`、`running`、`results`、`downstream`、`finished` | 五個都被接受，回 200，中欄顯示對應階段（所選階段的格子帶 `aria-current="step"`，見 TC-L12） | 自動 |
| TC-H10b | H10；決策 2 | 例外 | 選一個 run，其階段為 results | 用 `?stage=evil`、`?stage=`（空）、`?stage=<script>`、`?stage=RUNNING` | 一律退回該 run 自己的階段（results），回 200，不是 500 | 自動 |
| TC-H10c | H10；裁定 2 | 功能 | 選一個 run，`stage=running` | GET | 上一階段、下一階段是連結（含 ← → 符號）：往前連到 launch、往後連到 results | 自動 |
| TC-H10d | H10；裁定 2 | 功能 | 選一個 run，`stage=launch` | GET | 沒有往前的連結（launch 沒有上一階段），有往後的 | 自動 |
| TC-H10e | H10；裁定 2 | 功能 | 選一個 run，`stage=finished` | GET | 沒有往後的連結（finished 沒有下一階段），有往前的 | 自動 |
| TC-H14a | H14；決策 2 | 功能 | 已登入 | GET `/`、`/?run=<id>` | 兩者都有 `<meta http-equiv="refresh" content="15">`（取代設計稿裡「現在」頁與進度欄的即時更新，見 TC-S09） | 自動 |
| TC-H14b | H14；決策 2 | 功能 | 登入頁、確認頁 `/c/<id>`、404 頁、設定頁 `/settings` | 各 GET 一次 | 都沒有 meta refresh（只有 `/` 有） | 自動 |
| TC-H18a | H18 | 例外 | 使用者沒有任何 run | GET `/` | 回 200，「現在」頁有一句說明目前還沒有 run 的空狀態文字，兩張卡的數字都是 0；左欄與右欄也有空狀態說明；不是 500 | 自動 |
| TC-H18b | H18 | 例外 | `index.db` 是空檔（0 位元組） | GET `/` | 回 200，有空狀態頁，不是 500 | 自動 |
| TC-H18c | H18 | 例外 | `index.db` 不存在 | GET `/` | 回 200，有空狀態頁，不是 500 | 自動 |
| TC-H19a | H19；決策 6 | 功能 | 使用者有 250 個 run | GET `/` | 左欄只列 100 筆，下面寫「還有 150 筆」 | 自動 |
| TC-H19b | H19；裁定 4 | 功能 | 使用者有 250 個 succeeded 的 run | GET `/` | 右欄「結果」群組標題總數 250，只列 100 筆，下面寫「還有 150 筆」 | 自動 |
| TC-S01 | 設計原話 4「同時跑5-10個」 | 功能 | 使用者自己有 10 個 run 同時存在：running 4、failed 2、lost 1、succeeded 3，名稱各不相同 | GET `/` | 10 個名稱都出現在左欄與右欄，沒有一個被截掉或被「還有 N 筆」吃掉；右欄群組標題「執行中（7）」「結果（3）」；計數列 ▶ 4、! 3、✓ 3；「現在」兩張卡的數字是 4 與 3 | 自動 |
| TC-S02 | H10；決策 2 | 例外 | 已登入 | GET `/?stage=running`（沒有 `run`） | 回 200，是「現在」頁，`stage` 被忽略；不是 500 | 自動 |

## User Story 2 — 頂欄的費用讀數（優先度 P1）

維護者原本寫的是「右邊最上面一行」；設計稿 v1 把費用放在頂欄，裁定 R1 照設計稿改為頂欄兩行純文字。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| ~~TC-H09a~~ | ~~維護者 2；H09~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~右欄最上面是「本月費用」標題~~ | 已取代：TC-S03 |
| ~~TC-H09b~~ | ~~維護者 2；H09~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~費用分兩行：「SU —」「雲端 —」~~ | 已取代：TC-S03 |
| TC-H09c | 維護者 2；H09 | 功能 | 已登入，有 run | GET `/` | 費用讀數裡沒有任何數字、也沒有連結、沒有進度條 | 自動 |
| ~~TC-L17~~ | ~~維護者 2；B1~~ | ~~功能~~ | ~~已登入，有 run~~ | ~~GET `/`~~ | ~~右欄最上面一行「本月 SU — · 雲端 —」~~ | 已取代：TC-S03（裁定 R1：移到頂欄） |
| TC-L18 | 維護者 2；option B；R1 | 功能 | 已登入 | GET `/`，並讀 `web_board.py` 原始碼 | 頁面沒有「本月費用」標題；頁面與 `web_board.py` 都不出現站名「NCHC」（標籤是不帶站名的「SU」，程式維持與站台無關） | 自動 |
| TC-S03 | 維護者 2；R1；G1 | 功能 | 已登入，有 run | GET `/` | 頂欄（在三欄之前）有兩個分開的純文字行，各自一個元素，文字（去掉標籤與多餘空白後）正好是「SU —」與「雲端 NT$ —」；兩行都不在連結內，頂欄裡沒有 `<progress>`；右欄沒有第二份費用行 | 自動 |
| TC-S04 | R1；設計原話 5 | 功能 | 已登入 | GET `/?lang=en` | 頂欄兩行純文字正好是「SU —」與「Cloud NT$ —」，同樣不是連結、沒有進度條 | 自動 |

## User Story 3 — 整頁只能看，每人只看到自己的 run（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H03a | 維護者 3；H03 | 例外 | 使用者 A、B 各送出一個 run，名稱不同 | 以 A 登入 GET `/`、`/settings` | 整份 HTML 任何地方都沒有 B 的 run 名稱 | 自動 |
| TC-H03b | 維護者 3；H03 | 例外 | A 有 1 個 run、B 有 5 個 | 以 A 登入 GET `/` | 各群組標題總數、計數列、「現在」兩張卡的數字只算 A 的，沒有算進 B 的 | 自動 |
| TC-H04a | 維護者 3；H04 | 例外 | 有一個 run 在 `launches` 完全沒有記錄 | 分別以 A、B 登入 GET `/` | 兩人都看不到，左欄、右欄、計數列、「現在」的卡都沒有它 | 自動 |
| TC-H04b | 維護者 3；H04 | 例外 | 有一個 run 的 `launches` 紀錄使用者欄是 NULL | 分別以 A、B 登入 GET `/` | 兩人都看不到，左欄、右欄、計數列、「現在」的卡都沒有它 | 自動 |
| TC-H04c | 維護者 3；H04 | 功能 | 同 H04a、H04b 的兩個 run | 以本機終端機路徑（`caller=None`）呼叫 `list_runs` | 這兩個 run 都列得出來（只能在本機終端機查） | 自動 |
| TC-H05a | H05；決策 8 | 例外 | A、B 各有 run | 以 A 登入 GET `/?run=<B 的 run id>` | 回 404 頁，不是 B 的 run 內容 | 自動 |
| TC-H05b | H05；決策 8 | 例外 | 已登入 | GET `/?run=<不存在的 id>` | 回 404 頁 | 自動 |
| TC-H05c | H05；裁定 5 | 例外 | 同 H05a、H05b | 比較「別人的 run」與「不存在的 id」兩份回應 | 兩份 404 頁逐位元組相同（看不出差別） | 自動 |
| TC-H05d | 裁定 5 | 例外 | 已登入 | GET `/?run=<一段獨特字串>` | 404 頁內容不含這段字串（不回顯使用者輸入的 id） | 自動 |
| TC-H15 | H15 | 例外 | 沒有 cookie，但帶 `Authorization: Bearer <有效的 token>` | GET `/`、GET `/settings` | 一樣回 303 轉登入，Bearer 不算登入 | 自動 |
| TC-H11a | 維護者 3；H11 | 功能 | 已登入，選一個 run | GET `/`、`/?run=<id>`、`/settings` | 每一頁唯一的 `<form>` 是登出；除登出表單內的按鈕外沒有 `<button>`；沒有其他表單 | 自動 |
| TC-H11b | H11 | 功能 | 同上 | GET `/`、`/settings` | 登出表單帶 CSRF 欄位（防跨站偽造的一次性記號） | 自動 |
| TC-H11c | H11 | 例外 | 已登入 | POST `/`、POST `/settings` | 都回 405 | 自動 |
| TC-H11d | H11；裁定 C3、R4 | 功能 | 網頁 app | 列出全部路由 | 路由集合正好等於 v3 合併後的既有路由（含 009i 的 OAuth／同意頁）加上 GET `/` 與 GET `/settings`（含 HEAD）；多一條或少一條都不過 | 自動 |
| TC-H11e | H11 | 功能 | 記下 `index.db`、`platform.db`、`tokens.db`、簽章金鑰的雜湊值 | GET `/`、`/?run=<id>`、`/?stage=running`、`/?lang=en`、`/settings`、`/settings?lang=en` 各一次 | 所有資料庫檔的雜湊值都沒變（GET 什麼都沒寫） | 自動 |
| TC-H12a | H12 | 例外 | run 名稱含 `<script>alert(1)</script>` 與 `"><b>` | GET `/`、`/?run=<id>` | 這些字在左欄、右欄、「現在」的卡、中欄都被轉義，HTML 裡沒有可執行的標籤 | 自動 |
| TC-H12b | H12 | 例外 | `failure_reason` 含 `<img src=x onerror=1>` | GET `/?run=<id>` | 轉義後顯示，沒有真的 `<img>` 標籤 | 自動 |
| TC-H12c | H12 | 例外 | run 的 id 含引號等特殊字元 | GET `/` 與 `/?lang=en` | 連結裡的 id 放在引號內且已轉義，`href` 不會被截斷 | 自動 |
| TC-H12d | H12；C4；R3 | 例外 | 一個 failed 的 run，`failure_reason` 第一行是 `<img src=x onerror=1>` | GET `/`（不選 run） | 右欄項目與「現在」卡裡的重點都是轉義後的文字，頁面沒有真的 `<img>` 標籤 | 自動 |
| TC-H13a | H13；決策 7 | 功能 | 任一頁 | GET `/`、`/settings` | CSP 標頭沒有 `script-src` | 自動 |
| TC-H13b | H13；決策 7 | 功能 | 任一頁 | GET `/`、`/settings` | CSP 標頭沒有 `'unsafe-inline'` | 自動 |
| TC-H13c | H13；決策 7；L6 | 功能 | 已登入 | GET `/`、`/?lang=en`、`/settings` | CSP 的 `style-src` 是 sha256 雜湊，且與該頁內嵌樣式表的雜湊一致 | 自動 |
| TC-H13d | H13；決策 7；R5 | 功能 | 登入頁、確認頁、同意頁、404 頁、設定頁 | 各 GET 一次 | 每一頁的 CSP 雜湊都與該頁內嵌樣式表一致 | 自動 |
| TC-H13e | H13；G9 | 功能 | 已登入，有 run | GET `/`、`/?run=<id>`、`/settings`、`/login` | HTML 沒有 `<script>` | 自動 |
| TC-H13f | H13；決策 5；G9 | 功能 | 同上 | 同上 | HTML 沒有任何 `style=` 屬性（含 `<progress>`） | 自動 |
| TC-H13g | H13 | 功能 | 同上 | 同上 | HTML 沒有 `onclick=` 之類的 `on*=` 屬性 | 自動 |
| TC-H13h | H13；G9 | 功能 | 同上 | 同上 | HTML 沒有指向外部主機的資源或連結（沒有 `http://`、`https://`、`//host`） | 自動 |
| TC-H13i | 決策 7；L6 | 功能 | 任一頁 | GET `/` | CSP 其餘部分不變：`default-src 'none'`、`form-action 'self'`、`frame-ancestors 'none'`、`base-uri 'none'` | 自動 |
| TC-H17 | H17；決策 8 | 功能 | 程式碼靜態檢查（AST，即讀語法樹） | 掃 `web.py`、`web_board.py` 裡每個對 `list_runs`、`get_run` 的呼叫（含右欄與「現在」卡為失敗項目呼叫的 `get_run`、設定頁若有的讀取） | 每個呼叫都有 `caller=`，且值不是 None | 自動 |
| TC-S05 | 後端守則（錯誤訊息與日誌不洩漏） | 例外 | 已登入的使用者；分別造出：別人的 run（404 頁）、空檔 `index.db`、不存在的 `index.db`、登入失敗 401、登入太頻繁 429 | 各取回應內容，並取測試期間的伺服器日誌 | 回應內容都不含 `Traceback`、`sqlite`、`.db`、`web_signing`、任何 cookie 值、剛輸入的密碼；日誌也不含該密碼與 cookie 值；每一頁都說得出發生什麼事 | 自動 |

## User Story 4 — 網頁與 MCP 工具一一對照（優先度 P2）

對應 `docs/ROADMAP.md` 的「owed parity」一列；測試檔 `platform/tests/test_web_parity.py`。合併 v3 之後，MCP 多了 `forget`、`resume`、`relaunch` 三個寫入工具（它們呼叫 `request_*` 這類動作），OWED 的內容依裁定 R2 重算。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H16a | H16；裁定 1 | 功能 | 目前這個分支 | 跑 `test_web_parity.py` | 全部通過 | 自動：`platform/tests/test_web_parity.py` |
| TC-H16b | H16；裁定 1(a) | 功能 | 四張表 `WEB_ROUTES`、`WEB_ONLY`、`OWED`、`INTERNAL` | 比對四表聯集與 `actions` 的公開名稱 | 兩邊完全相等，每個名稱剛好在一張表 | 自動 |
| TC-H16c | H16；裁定 1(b) | 功能 | `WEB_ROUTES`（`list_runs`、`get_run`） | 對照 MCP 伺服器的工具清單 | 每個名稱都有同名 MCP 工具 | 自動 |
| ~~TC-H16d~~ | ~~H16；裁定 1~~ | ~~功能~~ | ~~`OWED` 表~~ | ~~讀它的內容~~ | ~~正好六個名稱~~ | 已取代：TC-S06（裁定 R2：不再釘「正好六個」） |
| TC-H16e | H16；裁定 1(c) | 功能 | `OWED` 表與網頁路由 | 檢查是否有網頁路由呼叫 `OWED` 的名稱 | 沒有任何 `OWED` 名稱被網頁路由呼叫 | 自動 |
| TC-H16f1 | H16；決策 9；裁定 1(d) | 功能 | `web.py`、`web_board.py` | AST 掃描它們呼叫的 `actions` 名稱 | 都在 `WEB_ROUTES`、`WEB_ONLY`、`INTERNAL` 內 | 自動 |
| TC-H16f2 | H16；決策 9 | 功能 | 同上 | AST 掃描 import | 沒有 import `confirm`、`jobs`、`compute_envs`、`agents`、`status` | 自動 |
| TC-H16g | H16；裁定 1 | 例外 | 測試內示範：在 `actions` 加一個四表都沒有的公開函式 | 對它跑「聯集等於公開名稱」的檢查 | 檢查失敗（紅）；證明它真的會擋 | 自動 |
| TC-H16h | H16；裁定 1 | 例外 | 測試內示範：讓網頁路由呼叫一個 `OWED` 名稱 | 對它跑「`OWED` 不被網頁呼叫」的檢查 | 檢查失敗（紅）；證明它真的會擋 | 自動 |
| TC-S06 | R2 | 功能 | 合併 v3 後的 `actions` 與 MCP 伺服器 | 測試用 AST 掃 `mcp_server.py` 的工具處理函式呼叫了哪些 `actions` 名稱，並讀 MCP 工具清單 | (a) `list_compute_envs`、`get_compute_env`、`list_agents`、`list_site_files` 四個有同名工具的讀取動作在 `OWED`；(b) 工具處理函式呼叫的每個 `actions` 名稱，都剛好落在 `WEB_ROUTES`、`OWED`、`INTERNAL` 其中一張（不會憑空不在任何表）；(c) 網頁路由呼叫的名稱都不在 `OWED`；(d) `forget_check`、`keep_screen` 在 `INTERNAL` | 自動 |
| TC-S07 | R2 | 功能 | 本分支的 `test_web_parity.py` 與 `specs/011a-web-shell/ledger.md` | 比對測試檔裡寫死的 `OWED` 名單與 ledger 記的名單 | 兩份名單逐字相同；名單是直接寫出的字面清單（不是程式算出來的），所以之後多一個名字就得改測試與計畫 | 手動：`docs/TESTING.md`（ledger 檢視） |

## User Story 5 — 文件、被改寫的舊測試、合併、人工檢視（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-D01 | 計畫「Pins to rewrite」 | 功能 | `specs/011a-web-shell/ledger.md` | 讀 ledger | 009c 的 TC-G04（路由集合）改為多 GET `/` 與 GET `/settings`，ledger 寫有舊值、新值、理由 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D02 | 同上 | 功能 | 同上 | 讀 ledger | 登入後那頁「已登入…請回到 AI…」的舊斷言改寫，ledger 寫有舊值、新值、理由 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D03 | 同上 | 功能 | 同上 | 讀 ledger | CSP 字串的舊斷言（若有被釘住）改寫，ledger 有舊新理由；若原本沒被釘住，ledger 明寫「沒有」 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D04 | 同上 | 功能 | 同上 | 讀 ledger | `PLATFORM.md` 文字釘子改寫，ledger 有舊新理由 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D05 | 憲法「弱化測試」 | 例外 | 本分支對 v3 的 diff | 逐個比對動到的測試檔 | 除 ledger 列名的幾處外，沒有任何舊斷言被刪掉、放寬、跳過或改成配合新輸出 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D06 | 決策 10；R4 | 功能 | `docs/PLATFORM.md` | 讀第 8、372、424 行附近與 CSP 那一行 | 網頁路由的敘述包含 GET `/` 與 GET `/settings`；不再說「只有登入頁與確認頁」；CSP 描述（樣式表雜湊）與新標頭一致 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D07 | 決策 10 | 功能 | `CHANGELOG` | 讀 | 有 011a 的一則紀錄，提到設計稿 v1 的框架 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D08 | 決策 10 | 功能 | `web.py` 開頭說明文字 | 讀 | 說明已改成包含 GET `/`（現在頁與看板）與 GET `/settings` 的唯讀畫面 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D09 | 裁定 7（contract-review） | 功能 | `docs/TESTING.md` | 讀 | 有「視覺檢查」（TC-V11 至 TC-V18）與「ledger 檢視」兩組具體步驟，照著做得出來 | 手動：`docs/TESTING.md` |
| TC-D10 | G9；憲法「弱化測試」 | 功能 | `specs/011a-web-shell/ledger.md` 與本分支對 layout B 版（commit 13daa79）的測試 diff | 對照「釘住舊版面標記」的測試與 ledger | 每一條為設計稿 v1 改過的斷言，ledger 都寫有舊斷言、新斷言、理由；沒有任何斷言被刪掉而沒有替代 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D11 | 計畫「Ruling after acceptance round 2」 | 功能 | `platform/tests/test_launch_static.py` | 與 v3 比對 | tc069、tc070 與 v3 逐字相同，沒有任何為站名加的豁免 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D12 | 專長守則（ui）；憲法「驗收期間不得改規格」 | 功能 | commit 637dc7c 的 `DESIGN.md`、`PRODUCT.md` | `git diff 637dc7c HEAD -- DESIGN.md PRODUCT.md specs/011a-web-shell/plan.md` | 沒有任何差異（執行者沒有改設計稿、產品說明與計畫；計畫的更動由 developer-agent 另開提交） | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-S08 | G0 | 功能 | 本分支的 git 歷史 | `git log --merges --first-parent` 與 `git merge-base --is-ancestor 0d36bcf HEAD` | 有一個單獨的合併提交（把 `origin/v3` 併進來，提交裡只有解衝突的內容，沒有別的功能改動）；合併前的提交（0d36bcf 之前的歷史）仍是祖先，歷史沒有被 rebase 或強推改寫；衝突處 `docs/PLATFORM.md`、`test_confirm_page.py`、`test_review_fixes_2.py` 兩邊的內容都留著（v3 新增的 keep-submissions、resume/relaunch、013a 等測試與文件仍在） | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-S09 | G8 | 功能 | 設計稿 `DESIGN.md` 與 `specs/011a-web-shell/design-v1-demo.html` 裡標了「JS」的地方（「現在」頁的即時更新、右欄進度的即時更新） | 讀 ledger | ledger 列出這幾處 JS 位置，並說明 011a 改用 15 秒 meta refresh、沒有加任何 JS（頁面實際沒有 `<script>`，見 TC-H13e） | 手動：`docs/TESTING.md`（ledger 檢視） |
| ~~TC-V01~~ | ~~Tier B 視覺檢查；維護者 1~~ | ~~功能~~ | ~~本機啟動 `abf-platform web`，灌入 e2e 假 run~~ | ~~登入後開 `/`，截圖~~ | ~~三欄、右欄「本月費用」與五個群組~~ | 已取代：TC-V11 |
| TC-V02 | Tier B 視覺檢查 | 功能 | 本機啟動 `abf-platform web`，灌入 e2e 假 run，有一個 succeeded 的 run | 選該 run，截圖 | 截圖附在 PR；中欄五階段板的「結果」是目前階段，看得到狀態、時間（`MM-DD HH:mm`）、進度條 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V03 | Tier B 視覺檢查 | 功能 | 同上，有一個 failed 的 run | 選該 run，截圖 | 截圖附在 PR；中欄看得到失敗狀態與失敗原因 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V04 | 維護者 1；裁定 6 | 功能 | 本機頁面的截圖 | 用肉眼看（可轉成黑白） | 四種狀態各有文字與符號（▶ ✓ ✗ ⏸），不靠顏色也分得出來 | 手動：`docs/TESTING.md`（視覺檢查） |
| ~~TC-V05~~ | ~~決策 6~~ | ~~功能~~ | ~~本機頁面~~ | ~~縮到約 900 px 以下，截圖~~ | ~~三欄改成上下堆疊~~ | 已取代：TC-V12 |
| ~~TC-V06~~ | ~~L9~~ | ~~功能~~ | ~~layout B 寬螢幕截圖~~ | ~~截圖~~ | ~~layout B 的頂欄、232px 左欄、右欄費用行~~ | 已取代：TC-V11 |
| ~~TC-V07~~ | ~~L6；L9~~ | ~~功能~~ | ~~layout B 窄螢幕~~ | ~~截圖~~ | ~~中、右、左堆疊~~ | 已取代：TC-V12 |
| ~~TC-V08~~ | ~~L7；L9~~ | ~~功能~~ | ~~layout B 英文寬螢幕~~ | ~~截圖~~ | ~~英文介面~~ | 已取代：TC-V13 |
| ~~TC-V09~~ | ~~L6；L7；L9~~ | ~~功能~~ | ~~layout B 英文窄螢幕~~ | ~~截圖~~ | ~~英文堆疊~~ | 已取代：TC-V14 |
| ~~TC-V10~~ | ~~維護者選 B；L3；L4~~ | ~~功能~~ | ~~對照 layoutB-reference.html~~ | ~~並排比對~~ | ~~與參考稿一致~~ | 已取代：TC-V15（參考稿改為 design-v1-demo.html） |
| TC-V11 | G10；設計原話 1、8 | 功能 | 本機啟動 `abf-platform web`（loopback），灌入 e2e 假 run（含 running、failed、lost、succeeded）；另備一個沒有 run 的使用者 | 用 Playwright 以寬螢幕（中文）截五張圖：「現在」、選到一個失敗 run、空狀態（沒有 run 的使用者）、設定頁、登入頁 | 五張截圖附在 PR；看得到深色細頂欄（左 `agentic-bioflow`，右費用兩行、中｜EN、姓名）、左欄、中欄、右欄；「現在」頁有「正在跑」「需要注意」兩張卡；設定頁每一節灰字「之後開放」；登入頁只有姓名與密碼 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V12 | G10；L6 | 功能 | 同上 | 用 Playwright 以手機寬度（390 px，中文）截同樣五張圖 | 五張截圖附在 PR；單欄，由上到下是中欄、右欄、左欄；頂欄不顯示費用；內容沒被切掉 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V13 | G10；設計原話 5 | 功能 | 同上 | 用 Playwright 以寬螢幕開 `?lang=en`，截四張圖：「現在」、選到一個失敗 run、空狀態、設定頁 | 四張截圖附在 PR；介面文字全是英文，run 名稱維持原樣 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V14 | G10；設計原話 5 | 功能 | 同上 | 同 TC-V13，以手機寬度（390 px） | 四張截圖附在 PR；英文版同樣單欄堆疊，內容沒被切掉 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V15 | 設計原話 8；G5；專長守則（ui） | 功能 | TC-V11 的截圖與 `specs/011a-web-shell/design-v1-demo.html` | 並排比對 | 骨架與設計稿一致：深色頂欄、左欄、中欄、右欄；階段條用實線（已完成、目前）與虛線（之後）區分，目前那一格看得出是目前；右欄項目整塊上色、被選的 run 有外框；「現在」卡是設計稿的樣子；與設計稿不同之處只限本計畫列為「之後開放」或省略的功能 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V16 | 專長守則（ui） | 功能 | 把「現在」、選到的 run、設定頁、登入頁、空狀態各存成 HTML 檔 | `sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>`（唯讀） | 偵測器的每項發現都記在驗收報告（不判 FAIL，列入「需要人看的事」） | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V17 | 專長守則（ui） | 功能 | 同 TC-V12 | 在 Playwright 量手機寬度（390 px）下五張畫面的 `scrollWidth` 與視窗寬 | 每一張 `scrollWidth` 不大於視窗寬（不橫向捲動）；可點的項目看起來夠大（交給維護者看截圖判斷） | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V18 | 專長守則（ui） | 功能 | 本機頁面 | 只用鍵盤的 Tab 鍵走過「現在」頁 | 每個可點的連結獲得焦點時都看得到外框，沒有焦點掉到看不見的元素上 | 手動：`docs/TESTING.md`（視覺檢查） |

## User Story 6 — 這次不做的事（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| ~~TC-N01~~ | ~~不做：專案與分析（011b）~~ | ~~不在範圍~~ | ~~已登入~~ | ~~GET `/` 並列出路由~~ | ~~左欄只有「尚未開放」說明~~ | 已取代：TC-N11 |
| TC-N02 | 不做：run 詳情、log、失敗一句話、resume／restart（011c、011e） | 不在範圍 | 已登入，有 failed run | GET `/?run=<id>` 與 GET `/runs/<id>`、`/logs`、`/resume`、`/restart` | 頁面沒有 log、resume、restart 的連結或按鈕；那幾個路徑回 404（或 405）；失敗只顯示 `failure_reason` 原文 | 自動 |
| TC-N03 | 不做：費用數字（011d） | 不在範圍 | 灌入有工作數的 run | GET `/` | 頂欄費用仍是「SU —」「雲端 NT$ —」，頁面任何地方沒有算出來的費用數字 | 自動 |
| TC-N04 | 不做：送出表單、上傳、結果、Studios、聊天（012 至 014、016）、費用頁、首次設定頁 | 不在範圍 | 已登入 | 對 `/runs`、`/ce`、`/compute-envs`、`/oauth/token`、`/oauth/authorize`、`/admin`、`/launch`、`/submit`、`/upload`、`/password`、`/passwd`、`/cost`、`/setup`、`/api/launch` GET 與 POST | GET 都 404；POST 都 404 或 405（`/settings` 已是本次新增的路由，不在這張清單） | 自動 |
| TC-N05 | 不做：`get_board` 或任何新 MCP 工具 | 不在範圍 | MCP 伺服器與 `actions` | 讀 MCP 工具清單與 `actions` 公開名稱 | 與合併後的 v3 相比沒有新增工具、沒有新增 action，也沒有 `get_board` | 自動 |
| TC-N06 | 不做：JavaScript、即時推送（G8） | 不在範圍 | 網頁 app | 列出路由與回應 | 沒有 WebSocket 或事件串流（SSE，伺服器持續推資料）路由；更新只靠 15 秒的 meta refresh；沒有 `<script>` | 自動 |
| TC-N07 | 不做：所有權程式（#116）與角色（010）；資料結構變動 | 不在範圍 | 本分支對 v3 的 diff | 看 `actions/`、`jobs.py`、`mcp_server.py` 與 `store.py` 的變動 | 沒有為本功能改所有權判斷，也沒有新增角色或「看全實驗室」的檢視；資料表結構沒有任何變動（所以不需要 migration，ledger 寫明此點） | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-N08 | 不做：登入頁與確認頁的翻譯（裁定 B6、R5） | 不在範圍 | 已登入，並有一筆待確認申請 | GET `/login?lang=en` 與 `/c/<id>?lang=en` | 兩頁仍是中文，沒有被翻成英文；`lang` 對它們沒有作用 | 自動 |
| TC-N09 | 不做：cookie 或 JavaScript 記住語言（L7） | 不在範圍 | 已登入 | GET `/?lang=en`，再 GET `/`（不帶 lang） | 第一個回應沒有任何 `Set-Cookie`；第二個回應是中文；切換只靠兩個普通連結 | 自動 |
| TC-N10 | 不做：聊天框、上傳、搜尋、輸入欄（設計稿裡屬於 012 至 016 的部分） | 不在範圍 | 已登入，選一個 run | GET `/`、`/?run=<id>`、`/settings` | 沒有 `<textarea>`、`<select>`、`<iframe>`；除登出表單的 CSRF 隱藏欄外沒有 `<input>`；沒有 radio 與 checkbox；`<details>` 只出現在右欄群組；頁面上所有 `<a>` 的目標都只指向 `/` 或 `/settings`（可帶 `run`、`stage`、`lang` 查詢參數） | 自動 |
| TC-N11 | 不做：專案與分析（011b）；裁定 B4、R7 | 不在範圍 | 已登入 | GET `/`，並列出路由 | 左欄沒有專案或分析的連結、清單或表單；尚未做的項目只是灰字「之後開放」，不在連結內；路由集合同 TC-H11d | 自動 |
| TC-N12 | 不做：費用頁、首次使用設定（設計稿第 2、11 畫面；R7、R1） | 不在範圍 | 已登入 | GET `/`、`/settings` | 費用讀數不是連結（沒有 `#cost` 或費用頁網址）；沒有「歡迎使用」「第一次使用」「建立第一個專案」之類的步驟畫面 | 自動 |
| TC-N13 | 不做：「系統自動處理紀錄」表與「待你決定」計數（R3） | 不在範圍 | 已登入，有各種狀態的 run | GET `/` | 「現在」頁沒有「系統自動處理紀錄」表、沒有「待你決定」「Awaiting you」字樣、沒有 `<table>` | 自動 |
| TC-N14 | 不做：金鑰輸入、Jev 開關（R4；設計原話 9） | 不在範圍 | 已登入 | GET `/settings` | 「AI 模型金鑰」「Jev 金鑰（選填）」只是灰字加「之後開放」，沒有任何輸入欄；整頁沒有「Jev 開」「Jev 關」之類的切換 | 自動 |
| TC-N15 | 不做：登入頁的權杖欄位與「記住 12 小時」（R5；憲法 5.0.0） | 不在範圍 | 未登入 | GET `/login` | 表單欄位只有姓名與密碼（加選用的隱藏 `next`）；沒有 checkbox、沒有權杖欄位、沒有「記住 12 小時」「Remember 12 h」字樣 | 自動 |
| TC-N16 | 不做：聊天（014）；設計原話 2 的對話框 | 不在範圍 | 已登入 | GET `/` | 右欄「聊天」只是灰字加「之後開放」，沒有未讀數字、沒有訊息輸入框、不是連結、不是按鈕 | 自動 |
| TC-N17 | 不做：網頁終端機（設計原話 10 已取消） | 不在範圍 | 已登入 | GET `/`、`/?run=<id>`、`/settings` | 頁面沒有終端機或指令輸入元件（沒有 `<iframe>`、`<textarea>`、指令輸入欄、「終端機」「Terminal」字樣） | 自動 |
| TC-N18 | 不做：Seqera 式的一堆頂層頁面（設計原話 6；PRODUCT） | 不在範圍 | 已登入 | GET `/`，列出左欄與頂欄所有項目 | 沒有 Launchpad、Runs、Datasets、Studios 這類頂層入口；「資料瀏覽」「儀表板」只是灰字「之後開放」，不是連結 | 自動 |
| TC-N19 | 不做：目前步驟與四張摘要卡（R6；設計稿第 7 畫面） | 不在範圍 | 已登入，有 running 的 run | GET `/`、`/?run=<id>` | 右欄項目與「現在」卡沒有「目前步驟」（process 名稱）；中欄沒有「目前步驟／已執行／運算環境／費用」四張摘要卡 | 自動 |
| TC-N20 | 不做：設計稿第 3 至 10 畫面的內容（上傳、送出導引、確認摘要頁、各分頁、下游 IDE、交付包） | 不在範圍 | 已登入，選一個 run，逐一用 `stage=launch`、`running`、`results`、`downstream`、`finished` | GET | 中欄只有狀態、時間、七格工作數、失敗原因，與其他階段的「—」加功能編號；沒有拖放區、管線選擇、參數表、Tasks／Logs／Run info／Configuration／Metrics／Report／Outputs 分頁、MultiQC、`<iframe>`、交付包下載 | 自動 |

## User Story 7 — 設計稿 v1 的框架：頂欄、三欄、左欄、右欄、階段條（優先度 P1）

對應計畫「REDO per web design v1」G1 至 G3、G5、G6 與裁定 R1、R6、R7，以及 `DESIGN.md` 的骨架、token、狀態表。layout B 版的 TC-L01 至 TC-L06 由本節的 TC-S 列取代；L07 起的階段條與右欄項目列保留或改寫。

### 頂欄與整體格線

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| ~~TC-L01~~ | ~~L1~~ | ~~功能~~ | ~~以姓名 X 登入~~ | ~~GET `/`~~ | ~~頂欄左 `agentic-bioflow`，右姓名與「中｜EN」~~ | 已取代：TC-S10 |
| ~~TC-L02~~ | ~~維護者 1；L2 至 L4~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~左欄含「我的 run」，右欄含費用行~~ | 已取代：TC-S19 至 TC-S28 |
| ~~TC-L03~~ | ~~L2；L4；L8~~ | ~~功能~~ | ~~樣式表~~ | ~~讀~~ | ~~232px／272px 兩側欄~~ | 已取代：TC-S11 |
| ~~TC-L04~~ | ~~L6；L8~~ | ~~功能~~ | ~~樣式表~~ | ~~讀~~ | ~~900px 媒體查詢~~ | 已取代：TC-S12、TC-S13 |
| ~~TC-L05~~ | ~~維護者 1；L2；B4~~ | ~~功能~~ | ~~3 個 run~~ | ~~GET `/`~~ | ~~左欄「我的 run」下每個 run 是連結~~ | 已取代：TC-S19、TC-S20 |
| ~~TC-L06~~ | ~~L2；B4~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~左欄底部「設定」灰字「之後開放」~~ | 已取代：TC-S22 |
| TC-S10 | G1；DESIGN 骨架 | 功能 | 以純 ASCII 姓名 X 登入 | GET `/` | 頁面最上方有一條深色細頂欄，在三欄之前，樣式表裡它的高度是 40px；左邊是 `agentic-bioflow`；右邊依序是：費用讀數（TC-S03）、「中」「EN」切換、姓名 X；登出不在頂欄 | 自動 |
| TC-S11 | DESIGN 骨架；G6 | 功能 | 取出頁面內嵌的那份樣式表 | 讀樣式表 | 寬螢幕的三欄格線是 `272px minmax(0,1fr) 320px`（左欄 272px、右欄 320px、中欄取剩下的寬度） | 自動 |
| TC-S12 | DESIGN 骨架 | 功能 | 同上 | 讀樣式表 | 有 `max-width:1200px` 的媒體查詢，三欄改為 `232px minmax(0,1fr) 288px` | 自動 |
| TC-S13 | DESIGN 骨架；G6 | 功能 | 同上 | 讀樣式表，並用頁面的欄位順序 | 有 `max-width:900px` 的媒體查詢，三欄改為單欄；視覺順序為中欄、右欄、左欄；頂欄的費用讀數在這個寬度下被隱藏（`display:none`） | 自動 |

### 設計稿的 token、字型、焦點

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-S14 | R7；DESIGN tokens | 功能 | 取出頁面內嵌的那份樣式表 | 讀樣式表的 `:root` 與 `prefers-color-scheme: dark` 區塊 | 淺色區塊含這些值：#f6f5f2、#ffffff、#ecebe6、#1f2328、#575e66、#d6d3cc、#8f8b82、#1c5d8a、#e2edf5，狀態色 #0b5aa8／#e3edf9、#1b6837／#e2f0e6、#b0261d／#fae6e3、#865700／#f7edd6；深色區塊含這些值：#15171a、#1e2125、#101214、#e9e7e2、#a2a8b0、#33373d、#646a73、#7db8e2、#1a2c3a、#9cccf0，狀態色 #80b6f2／#15263a、#78c792／#14291c、#f28b81／#3a1916、#e2b35e／#33270e | 自動 |
| TC-S15 | R7；專長守則（ui）「不自創顏色」 | 功能 | 同上 | 掃樣式表裡所有十六進位顏色 | 每一個都在 TC-S14 列的值之內；沒有 `rgb()`、`rgba()`、`hsl()` | 自動 |
| TC-S16 | R7；DESIGN type／spacing／radius | 功能 | 同上 | 掃樣式表的 `font-family`、`font-size`、`border-radius`、`padding`、`margin`、`gap` | `font-family` 只有兩組：系統 sans（含 Noto Sans TC 與 Microsoft JhengHei）與 mono（以 ui-monospace 開頭）；`font-size` 只有 12px、13px、15px、16px、22px（或 inherit）；`border-radius` 只有 0、4px、6px、999px；`padding`／`margin`／`gap` 的 px 值只有 0、4、8、12、16、24 | 自動 |
| TC-S17 | G9；DESIGN 限制 | 功能 | 已登入；登入頁 | GET `/`、`/settings`、`/login` | 每一頁只有一個 `<style>`，沒有 `<link rel="stylesheet">`；樣式表沒有 `@import`、`@font-face`、`url(` | 自動 |
| TC-S18 | 專長守則（ui）「焦點外框可見」 | 功能 | 同上 | 讀樣式表 | 連結與 `<summary>` 都有 `:focus-visible` 的 outline，寬度至少 2px，顏色用焦點色（淺色 #1c5d8a、深色 #9cccf0） | 自動 |

### 左欄

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-S19 | 維護者 1；G2；決策 6 | 功能 | 已登入，有 3 個 run | GET `/` | 左欄第一項是「現在」（連到 `/`）；其下有標題「我的 run」，標題之下是 run 清單；「設定」「登出」等底部項目在清單之後；中欄、右欄是另外兩個區塊 | 自動 |
| TC-S20 | G2；DESIGN 左欄 | 功能 | 四種狀態的 run 各一，其中 succeeded 與 running 的 run 名稱很長 | GET `/` | 左欄每個 run 是一個連到 `/?run=<id>` 的連結，內含：狀態符號（▶ ✓ ✗ ⏸）、run 名稱、目前階段名（running、failed、lost 寫「執行中」，succeeded 寫「結果」）、該狀態的專屬 class；名稱放在可截斷顯示的元素裡 | 自動 |
| TC-S21 | G2；R7；B4 | 功能 | 已登入 | GET `/` | 左欄的「＋ 新專案」「搜尋專案或分析」「↑ 上傳資料」各是灰字，旁邊或其中寫「之後開放」；它們不在 `<a>`、`<form>`、`<input>` 內 | 自動 |
| TC-S22 | G2；R4 | 功能 | 已登入 | GET `/` | 左欄底部：「設定」是連到 `/settings` 的連結；「資料瀏覽」「儀表板」是灰字加「之後開放」、不是連結；「登出」是整頁唯一的表單（見 TC-H11a） | 自動 |
| TC-S23 | G2；DESIGN 左欄 | 功能 | 已登入，有 run | 分別 GET `/`、`/?run=<id>`、`/settings` | `/`：「現在」帶被選取標記；`/?run=<id>`：左欄與右欄那個 run 的項目帶被選取標記（同 TC-L28 的標記），「現在」不帶；`/settings`：「設定」帶被選取標記，「現在」不帶 | 自動 |

### 右欄

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-S24 | G3；DESIGN 右欄 | 功能 | 已登入 | GET `/` | 右欄最上面是兩個分頁名：「分析進度」（目前這個）與「聊天」；「聊天」是灰字加「之後開放」，沒有未讀數字，不是連結、不是按鈕、不是 radio | 自動 |
| TC-S25 | R7；DESIGN 右欄 | 功能 | 已登入 | GET `/` | 右欄有標題「全部分析」與說明「只顯示你的」；搜尋是灰字「之後開放」，不是輸入欄 | 自動 |
| TC-S26 | R6 | 功能 | running 3、failed 1、lost 2、succeeded 4 | GET `/` | 計數列只有三項：「▶ 3」「! 3」「✓ 4」（! = 失敗加失聯，3 = 1 + 2）；沒有 ⟳、?、… 這些項目 | 自動 |
| TC-L19 | 維護者 1；R6；B5 | 功能 | 已登入，有四種狀態的 run | GET `/` | 右欄在計數列之後依序是：「執行中（n）」群組、「結果（n）」群組（各是展開的 `<details open>`，標題在 `<summary>`）、一塊灰色「之後開放」（代表送出、下游、完成）；沒有「送出」「下游」「完成」各自的群組標題或計數；右欄沒有費用行 | 自動 |
| TC-L20 | 維護者 1；B5；C1 | 功能 | running 1、failed 1、lost 1、succeeded 1，名稱各不同 | GET `/` | running、failed、lost 三個項目都在「執行中」群組內；succeeded 的項目在「結果」群組內；failed 與 lost 不在「結果」群組 | 自動 |
| TC-L21 | 維護者 1；L4；L5 | 功能 | 一個 running 的 run | GET `/` | 右欄該項目是一整塊，整塊在同一個連到 `/?run=<id>` 的連結內，並帶 running 專屬 class | 自動 |
| TC-L22 | B3；R6 | 功能 | 使用者有 3 個 run，開始時間依序為 t1、t2、t3（t1 最早） | GET `/` | 右欄同一群組內由上到下標成「3: 名稱」「2: 名稱」「1: 名稱」（最新在上），序號 1 是 t1 那個 run | 自動 |
| TC-L23 | B3；C5 | 功能 | 一個 running 的 run：succeeded 6、cached 2、total 10 | GET `/` | 該項目的 done/total 是「8/10」（完成數 = 成功 + 快取） | 自動 |
| ~~TC-L24~~ | ~~B3；C5~~ | ~~功能~~ | ~~succeeded 的 run，已知結束時間~~ | ~~GET `/`~~ | ~~右欄項目重點是結束時間~~ | 已取代：TC-S27（裁定 R6：第二行是符號、狀態字、done/total） |
| TC-L25 | B3；C4 | 功能 | 一個 failed 的 run，`failure_reason` 第一行有 120 個字元，其後還有第二行 | GET `/` | 項目與「現在」卡裡的重點是第一行，最多 80 個字元：第 81 個字元之後與第二行的內容都不出現；第一行不超過 80 字時完整顯示 | 自動 |
| TC-L26 | C4 | 例外 | 一個 failed 的 run，`failure_reason` 缺少；另一個 failed 的 run，`failure_reason` 是空字串 | GET `/` | 兩者的重點都是「原因未記錄」，頁面不是 500 | 自動 |
| ~~TC-L27~~ | ~~B3~~ | ~~功能~~ | ~~一個 lost 的 run~~ | ~~GET `/`~~ | ~~重點是「—」~~ | 已取代：TC-S27 |
| TC-L28 | L4；R6 | 功能 | 3 個 run | GET `/?run=<其中第二個>`，再 GET `/`（不選 run） | 前者：右欄只有被選的那個項目帶「被選取」標記，且樣式表對該標記設了外框（outline）；後者：右欄沒有任何項目帶該標記 | 自動 |
| TC-L29 | C4；決策 3；R3 | 功能 | 使用者有 250 個 failed 的 run；測試記錄 `actions` 的呼叫 | GET `/`（不選 run） | 整頁（右欄加「現在」卡）呼叫的 action 只有 `list_runs` 與 `get_run`；`get_run` 涉及的不同 run 不超過 100 個，每次都帶登入者的 `caller`；「執行中」群組只列 100 個項目 | 自動 |
| TC-L30 | B3；裁定 4 | 功能 | 使用者有 250 個 succeeded 的 run，開始時間各不同 | GET `/` | 「結果」群組標題 250，只列 100 個；最上面項目序號 250，第 100 個項目序號 151（序號是在全部 250 個 run 裡算的） | 自動 |
| TC-S27 | R6；設計稿右欄項目 | 功能 | running（成功 6、快取 2、total 10）、failed（成功 1、total 10）、lost（成功 4、total 10）、succeeded（成功 10、total 10）各一 | GET `/` | 每個項目的文字依序含：「序號:」、run 名稱、狀態符號、狀態字、done/total：「▶ 執行中 8/10」「✗ 失敗 1/10」「⏸ 失聯/暫停 4/10」「✓ 成功 10/10」；failed 項目另含失敗原因第一行（TC-L25） | 自動 |
| TC-S28 | R6；DESIGN 右欄 | 功能 | 同上，再加一個 total 為 0 的 run | GET `/` | 每個項目都有細的原生 `<progress>`，value 等於 done、max 等於 total；total 為 0 的那個沒有 value 屬性；沒有 `style=` | 自動 |

### 階段條

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-L07 | G5；B5 | 功能 | 已登入，選一個 run | GET `/?run=<id>` | 階段條依序有五格：送出、執行中、結果、下游（文字含「下游」，可寫「下游分析」）、完成 | 自動 |
| TC-L08 | G5；B2 | 功能 | 一個 running 的 run | GET `/?run=<id>` | 「送出」帶 `is-done`；「執行中」帶 `is-current`；「結果」「下游」「完成」帶 `is-later`；`is-current` 只有一格 | 自動 |
| TC-L09 | G5；B2 | 功能 | 一個 succeeded 的 run | GET `/?run=<id>` | 「送出」「執行中」帶 `is-done`；「結果」帶 `is-current`；「下游」「完成」帶 `is-later` | 自動 |
| TC-L10 | G5；B2；C1 | 功能 | 一個 failed 的 run | GET `/?run=<id>` | 「送出」`is-done`、「執行中」`is-current`、其餘三格 `is-later` | 自動 |
| TC-L11 | G5；B2；C1 | 功能 | 一個 lost 的 run | GET `/?run=<id>` | 「送出」`is-done`、「執行中」`is-current`、其餘三格 `is-later` | 自動 |
| TC-L12 | B2 | 功能 | 一個 running 的 run | GET `/?run=<id>&stage=results` | 各格的 `is-done`／`is-current`／`is-later` 與 TC-L08 完全一樣（選階段不改它們）；只有「結果」格帶 `aria-current="step"`，其他格沒有 | 自動 |
| TC-L13 | B2；決策 2 | 功能 | 一個 succeeded 的 run、一個 failed 的 run | 各 GET `/?run=<id>`（不帶 `stage`） | succeeded 的 run 由「結果」格帶 `aria-current="step"`；failed 的 run 由「執行中」格帶 | 自動 |
| TC-L14 | G5；L5 | 功能 | 一個 failed 的 run | GET `/?run=<id>` | 中欄上方有該 run 的名稱，旁邊是狀態徽章：符號「✗」、文字「失敗」、failed 專屬 class | 自動 |
| TC-L15 | C6 | 功能 | 一個 run，七種工作數各不相同（成功 11、快取 12、失敗 13、中止 14、執行中 15、等待 16、已送出 17） | GET `/?run=<id>` | 階段內容卡有七格，依序是「成功」「快取」「失敗」「中止」「執行中」「等待」「已送出」，每格的標籤與數字配對正確 | 自動 |
| TC-L16 | G5；裁定 2 | 功能 | 選一個 run，`stage=running` | GET | 有兩個連結：一個含「←」、連到 `stage=launch`；一個含「→」、連到 `stage=results`；都保留同一個 `run` | 自動 |
| TC-S29 | G5；DESIGN 階段條 | 功能 | 取出樣式表，並取一個 running 的 run 的階段條 | 讀樣式表與階段條 | 樣式表裡：`is-done` 格的上緣用 succeeded 色、`is-current` 格的上緣用 accent 色且 3px、`is-later` 格的上緣是 `dashed`（虛線）；階段條裡已完成（`is-done`）的格子文字含「✓」 | 自動 |
| TC-S30 | 專長守則（ui）「狀態絕不只靠顏色」；DESIGN 狀態表 | 功能 | 四種狀態的 run 各一 | GET `/` 與各 `/?run=<id>` | 每個出現狀態的地方都同時有符號與狀態專屬 class：左欄項目、右欄項目、「現在」卡的每一行；右欄項目、「現在」卡的每一行與中欄徽章另外有狀態字；四個符號是 ▶（執行中）✓（成功）✗（失敗）⏸（失聯/暫停） | 自動 |
| TC-S31 | DESIGN 限制（ADR 0004） | 功能 | 已登入，有 run | GET `/`、`/settings`，並讀樣式表 | 頁面與樣式表都沒有 Seqera、Galaxy、Tower 的名稱（不分大小寫） | 自動 |

## User Story 8 — 「現在」首頁與通知卡（優先度 P1）

對應 G4 與裁定 R3、設計稿第 1 畫面、設計原話 1「進來之後馬上可以看到各個run的狀態與進度…只有需要使用者決定的才會通知使用者」、設計原話 3「AI一律先除錯，不是使用者能決定的事情一律直接處理」。011a 只讀、只有 `list_runs`：「需要注意」＝失敗與失聯的 run；其他一律不通知。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-S32 | G4；R3；設計原話 1 | 功能 | 使用者自己的 run：running 2、failed 1、lost 1、succeeded 3 | GET `/`（沒有 `run`） | 中欄是「現在」頁：標題「現在」；有兩張卡「正在跑」與「需要注意」；「正在跑」的數字是 2，「需要注意」的數字是 2（= 卡裡項目的個數） | 自動 |
| TC-S33 | R3 | 功能 | 同上 | GET `/` | 「正在跑」卡裡每個 running 的 run 一行：含 ▶、「執行中」、run 名稱，整行連到 `/?run=<id>`；卡裡只有 running 的 run | 自動 |
| TC-S34 | R3；C4 | 功能 | 同上；failed 的 `failure_reason` 第一行有文字；另備一個 failed 的 run 沒有 `failure_reason` | GET `/` | 「需要注意」卡裡 failed 與 lost 的 run 各一行：failed 行含 ✗、「失敗」、名稱、失敗原因第一行（最多 80 字元，缺少時寫「原因未記錄」）；lost 行含 ⏸、「失聯/暫停」、名稱，沒有失敗原因；整行連到 `/?run=<id>` | 自動 |
| TC-S35 | R3；設計原話 1、3 | 功能 | 只有 succeeded 的 run；另一次是沒有 running 的 run | GET `/` | succeeded 的 run 不出現在任何一張卡（成功不通知）；沒有 running 時「正在跑」卡仍在、數字是 0；沒有 failed 與 lost 時「需要注意」卡仍在、數字是 0 | 自動 |
| TC-S36 | R3；G8 | 功能 | 有 failed 與 running 的 run | GET `/` | 兩張卡裡沒有 `<button>`、沒有表單、沒有指向 `/?run=<id>` 與 `/settings` 以外的連結；沒有「重跑」「續跑」「上傳」「確認」之類的動作字樣 | 自動 |
| TC-S37 | 決策 6（清單上限）；H19 | 功能 | 使用者有 250 個 failed 的 run | GET `/` | 「需要注意」卡的數字是 250，只列 100 行，下面寫「還有 150 筆」 | 自動 |

## User Story 9 — 設定頁與登入頁（優先度 P1）

對應 G6、裁定 R4（設定頁，全部灰字）、R5（登入頁只改樣式）、設計稿第 12、13 畫面、設計原話 2「系統設定先」、設計原話 9「不需要Jev "開關"，只要在設定讓使用者可以放金鑰」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-S38 | R4；H01 | 例外 | 沒有登入；另一次只帶 Bearer | GET `/settings` | 回 303 轉到 `/login`，回應內容沒有設定頁內容 | 自動 |
| TC-S39 | R4；設計原話 2、9 | 功能 | 已登入 | GET `/settings` | 回 200；中欄標題「設定」，依序有六節：運算環境、憑證、密碼與金鑰、個人、營運者後台、角色（老師／學生）；「密碼與金鑰」裡列出「AI 模型金鑰」與「Jev 金鑰（選填）」；「個人」裡列出「逐步模式」與「開發模式」；每一節（或每一項）旁寫灰字「之後開放」；沒有任何一項是連結、表單或輸入欄 | 自動 |
| TC-S40 | R4；G8；設計原話 9 | 功能 | 已登入 | GET `/settings` | 整頁唯一的表單是登出；沒有 `<input>`（登出的 CSRF 隱藏欄除外）、`<select>`、`<textarea>`、checkbox、除登出按鈕外的 `<button>`；沒有 Jev 的開／關切換；GET 之後資料庫雜湊不變（同 TC-H11e） | 自動 |
| TC-S41 | R4；G6 | 功能 | 已登入 | GET `/settings` | 設定頁有和 `/` 一樣的頂欄、左欄、右欄（含右欄進度）；左欄「設定」帶被選取標記（TC-S23）；中欄是設定內容 | 自動 |
| TC-S42 | R5；憲法 5.0.0 | 功能 | 已登入 | GET `/settings`、`/settings?lang=en` | 頁面不出現「12 小時」「12 h」「12 hours」（網頁登入不用權杖，也沒有 12 小時免登入） | 自動 |
| TC-S43 | G6；R5 | 功能 | 未登入 | GET `/login` | 回 200；用同一份唯一樣式表（CSP 雜湊相符、整頁一個 `<style>`）；表單只有「姓名」「密碼」兩個欄位與送出鈕（帶 `next` 時多一個隱藏欄）；頁面是中文；沒有 `<script>`、`style=`、外部網址 | 自動 |
| TC-S44 | G6；設計稿「錯誤」狀態 | 例外 | 未登入；一次填錯誤密碼、一次填不存在的姓名、一次短時間內連續失敗超過上限 | POST `/login` | 前兩次都回 401，同一版型，說明「姓名或密碼不對」，兩種錯誤的訊息相同（看不出姓名存不存在），表單仍在可重試；超過上限回 429 並說明「登入失敗太頻繁」；兩種頁面都沒有 cookie | 自動 |
| TC-S45 | R5 | 功能 | 一筆待確認申請與一筆同意請求 | GET `/c/<id>`、`/consent/<id>`（已登入） | 兩頁用同一份唯一樣式表（CSP 雜湊相符）；頁面仍是中文；既有的行為不變：按鈕、CSRF、同一人檢查、`form-action` 含連接器來源（既有測試 `test_tch09_b_c_*` 等原樣通過） | 自動 |

## User Story 10 — 中英切換、時間格式、連結與 404（優先度 P1）

對應 G6、G7、G9、裁定 B6、R7、設計原話 5「做成產品英文版面是必須的」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-L31 | L7；設計原話 5 | 功能 | 已登入，有 run | GET `/`（不帶 `lang`） | 介面文字是中文（例如「現在」「執行中」「之後開放」「登出」）；沒有出現英文的七格標籤「Cached」「Aborted」「Pending」「Submitted」 | 自動 |
| TC-L32 | L7；G9；設計原話 5 | 功能 | 純 ASCII 的使用者名與 run 名稱，有 running、failed、lost、succeeded 的 run | GET `/?lang=en`（現在頁）、`/?run=<id>&lang=en`、`/settings?lang=en` | 這三份 HTML 除了切換器上的語言名「中」之外，沒有任何 CJK 字元（所有介面文字都換成英文，包含「現在」頁的兩張卡、計數列、右欄、設定頁各節） | 自動 |
| TC-L33 | L7；C6 | 功能 | 一個 run，七種工作數各不相同 | GET `/?run=<id>&lang=en` | 七格標籤依序是 Succeeded、Cached、Failed、Aborted、Running、Pending、Submitted（不分大小寫），每格與其數字配對正確 | 自動 |
| TC-L34 | C4；L7 | 例外 | 純 ASCII 名稱、failed 且 `failure_reason` 缺少的 run | GET `/?lang=en` | 右欄項目與「現在」卡的重點是「reason not recorded」 | 自動 |
| TC-L35 | L7 | 功能 | 已登入，選一個 run 並選階段；另測 `/` 與 `/settings` | GET `/?run=<id>&stage=results`、GET `/`、GET `/settings` | 頂欄有「中」與「EN」兩個普通連結（不是表單、不是按鈕）；「EN」連到同一路徑，帶相同的 `run`、`stage`，再加 `lang=en`；「中」連到同一路徑，帶相同的 `run`、`stage`，不帶 `lang=en` | 自動 |
| TC-L36 | B6；G6 | 功能 | 已登入，有 run，選一個 run 並選階段 | GET `/?run=<id>&stage=running&lang=en`，以及 `/settings?lang=en` | 頁面上所有指向看板的連結（左欄與右欄的 run 連結、「現在」、「設定」、「現在」卡的連結、上一階段與下一階段、各群組項目）都帶 `lang=en`；唯一例外是切換器的「中」連結 | 自動 |
| TC-L37 | B6；L7 | 功能 | 同上 | GET `/?run=<id>&stage=running`（中文） | 所有連結都不帶 `lang=en`；唯一例外是切換器的「EN」連結 | 自動 |
| TC-L38 | L7 | 功能 | 一個 run，名稱是「大豆根腐」，failed 且 `failure_reason` 是中文句子 | GET `/?lang=en` 與 `/?run=<id>&lang=en` | run 名稱與失敗原因的中文逐字原樣出現（資料不翻譯） | 自動 |
| TC-L39 | B6 | 例外 | 已登入 | GET `/?run=<不存在的 id>&lang=en` | 回 404 頁，內容為英文：除切換器的「中」外沒有任何 CJK 字元 | 自動 |
| TC-L40 | B6；裁定 5 | 例外 | A、B 各有 run | 以 A 登入，分別 GET `/?run=<B 的 run id>&lang=en` 與 `/?run=<不存在的 id>&lang=en` | 兩份英文 404 頁逐位元組相同，也不回顯所請求的 id | 自動 |
| TC-L41 | L7 | 例外 | 已登入 | 分別 GET `/?lang=fr`、`/?lang=`、`/?lang=<script>` | 都回 200，頁面是預設的中文，沒有真的 `<script>` 標籤，不是 500 | 自動 |
| TC-L42 | L7；L8 | 功能 | 看板的字串表（全部介面文字的唯一來源） | 讀表 | `zh` 與 `en` 兩份鍵完全相同、沒有空值；`en` 的值沒有 CJK 字元（語言名「中」除外） | 自動 |
| TC-L43 | L7；H18 | 例外 | 純 ASCII 使用者名，沒有任何 run | GET `/?lang=en` | 回 200，空狀態說明為英文：除切換器的「中」外沒有任何 CJK 字元 | 自動 |
| TC-L44 | L6；L8；G9 | 功能 | 已登入，有 run | GET `/`、`/?run=<id>`、`/?run=<id>&stage=running`、`/settings`、`?lang=en` 的各版本、404 頁、空狀態頁 | 每份 HTML 都不含 `http` 開頭的網址；沒有 `<script`、沒有 `style=` | 自動 |
| TC-S46 | G7；R7 | 功能 | 一個 run 開始 2026-10-17 20:30 UTC、結束 2026-10-18 01:12 UTC | GET `/?run=<id>` 與 `/?run=<id>&lang=en` | 中、英文頁都顯示「10-18 04:30」與「10-18 09:12」（亞洲/台北時區、`MM-DD HH:mm`，時間格式不翻譯）；時間跨日的換算正確 | 自動 |
| TC-S47 | G7 | 例外 | 一個有開始與結束時間的 run | GET `/`、`/?run=<id>`、`/settings`、404 頁 | 任何一頁都沒有原始 ISO 時間字串（沒有 `T` 連接的日期時間如 `2026-10-18T01:12`、沒有結尾 `Z` 或 `+00:00`） | 自動 |
| TC-S48 | G9「沒有死連結」 | 功能 | 已登入，有四種狀態的 run；另有一個沒有 run 的使用者 | 在「現在」、選到的 run（含各 `stage`）、設定頁、空狀態頁、404 頁，取出每個 `<a href>` 並實際 GET | 每個 `href` 都是 `/` 開頭的本站路徑（沒有只有 `#` 的、`javascript:` 的、外部的）；每個 GET 都回 200；連到 `/?run=<id>` 的 id 都是這位使用者自己的 run | 自動 |
| TC-S49 | 專長守則（ui）「錯誤訊息說發生什麼事與下一步」 | 例外 | 已登入 | GET `/?run=<不存在的 id>`（中文與 `lang=en`） | 404 頁用同一份樣式表；文字說明找不到這個 run 或它不是你的（不分哪一種）；有一個連回 `/` 的連結（英文頁連到 `/?lang=en`）；頁面不含所請求的 id | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-K1 | 原則 I.2（確認只能由人在指定管道做） | 功能 | 記下 `launches`、`jobs`、待確認申請的筆數 | GET `/`、`/?run=<id>`、`/settings` 數次（含 `lang=en`） | 筆數都沒變；網頁讀取不會建立任何申請或工作 | 自動 |
| TC-K2 | 原則 I.2（未確認的送出被拒） | 例外 | 既有的 `test_tch09_*`（`test_human_channel.py`）與 `test_tch09_b_c_*`（`test_confirm_page.py`） | 跑 `tests/platform_test.sh` | 兩組仍全過，內容未被放寬 | 自動 |
| TC-K3 | 開發流程「每階段全綠」；G9 | 功能 | 合併 v3 之後的本分支 | 在 WSL 或 CI 跑 `bash tests/run_all.sh` | 全部通過；v3 帶進來的測試（keep-submissions、resume/relaunch、013a 等）一併在內且都綠 | 自動：`tests/run_all.sh` |
| TC-H07a | 原則 I.2（不存第二份 run 狀態）；H07 | 功能 | 本分支的資料庫結構與 `web_board.py` | 檢查資料表欄位與程式 | 沒有儲存「階段」的欄位或檔案；階段、序號、計數、通知卡每次由狀態與開始時間算出，沒有存下來 | 自動 |
| TC-H07b | 原則 I.2；H07 | 功能 | 本分支 | 跑 `tests/no_second_run_state_test.sh` | 通過 | 自動：`tests/no_second_run_state_test.sh` |
| TC-K5 | 安全網（不得放寬） | 功能 | 本分支對 v3 的 diff | 看 `hooks/`、`.claude/`、deny 規則是否被動到 | 沒有任何 hook 或 deny 被改動 | 手動：`docs/TESTING.md`（ledger 檢視） |
