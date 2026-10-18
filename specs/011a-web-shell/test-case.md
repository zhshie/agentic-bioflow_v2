# 測試案例：011a 網頁外殼（Galaxy 三欄、唯讀）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
This is the contract REOPENED for layout B (plan section "Layout redo: option B", L1-L9, rulings B1-B6 and C1-C6, 2026-10-18).
There is no spec.md for 011a: the plan's section 「給維護者」 (three numbered points, point 2 as rewritten by ruling B1) is the maintainer's own statement,
and the plan's TC-H01 to TC-H19 are the base. Nothing here invents behaviour the plan does not state.
IDs: TC-H01 to TC-H22 keep the plan's numbers. A struck-through row (~~ ~~) is superseded by layout B and keeps its row; the row that replaces it is named in its last cell.
New rows: TC-L01 to TC-L44 (layout B and language), TC-H12d, TC-V06 to TC-V10, TC-D10, TC-D11, TC-N08 to TC-N11.
Language: 繁體中文; identifiers (TC-, H, L, FR) and file paths stay as they are.
-->

**規格**：`specs/011a-web-shell/plan.md`（無獨立 spec.md；「給維護者」三點即維護者的原話）　**總覽**：`test-case-overview.md`

「給維護者」三點（點 2 依裁定 B1 改寫），下面簡稱「維護者 1／2／3」：

1. 登入網頁後看到三欄畫面：左邊是你的 run 清單，專案功能還沒做，頁面會照實寫出來；中間是選到的那個 run 的五階段板；右邊是你所有 run 的進度，照階段分組、用顏色加文字標狀態。
2. 右欄最上面一行「本月 SU — · 雲端 —」。
3. 整頁只能看，沒有會改東西的按鈕。每人只看到自己送出的 run；沒記錄送出者的舊 run 不顯示，只能在本機終端機查。

維護者在 2026-10-18 看過第二輪版面後否決，改選 B（Galaxy 式三欄工作台）。後端（路由、只看自己的 run、parity 表、100 筆上限、404、符號、費用標籤）不變；版面與樣式表重做，並加上中英切換。

名詞：

- 「階段」= launch（送出）、running（執行中）、results（結果）、downstream（下游）、finished（完成）五個，網址用 `?stage=` 選。階段條的中文名取自裁定 B5 的群組名。
- 「群組」= 右欄依階段分的區塊。依裁定 B5／C1，現在只有「執行中」（running、failed、lost）與「結果」（succeeded）兩個真群組，外加一塊灰色「之後開放」。
- 「項目」= 右欄裡一個 run 的整塊（序號與名稱／符號、狀態字、重點）。
- 「CSP」= 網頁回應附帶的安全標頭，限制頁面能載入什麼。
- 「CJK 字元」= 中日韓文字。英文版的測試用純 ASCII 的 run 名稱與使用者名稱，才能證明「畫面上的字」全部換成英文。
- 「六條路由」依裁定 C3 = 合併 v3 後的既有路由（含 009i 的 OAuth／同意頁）加上 GET `/`。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 登入後看到三欄畫面（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H01a | 維護者 1；H01 | 例外 | 沒有登入（請求沒帶 cookie） | GET `/` | 回 303，轉到 `/login`；回應內容沒有任何 run 資料 | 自動 |
| ~~TC-H01b~~ | ~~維護者 1；H01~~ | ~~功能~~ | ~~已登入（帶有效 cookie）~~ | ~~GET `/`~~ | ~~回 200；同一頁有三欄：左「我的 run」、中、右「本月費用」~~ | 已取代：TC-L02（右欄不再有「本月費用」標題，裁定 B1） |
| TC-H02a | H02 | 功能 | 有網頁密碼的使用者；登入表單沒有 next | 送出正確姓名與密碼 | 回 303 轉到 `/`；不再出現「已登入…請回到 AI…」那個沒有下一步的頁面 | 自動 |
| TC-H02b | H02 | 功能 | 登入表單帶 `next=/c/<32 位十六進位>` | 送出正確姓名與密碼 | 仍轉到那個 `/c/...` 確認頁（既有行為不變） | 自動 |
| TC-H02c | H02 | 例外 | 登入表單帶 `next=//evil` | 送出正確姓名與密碼 | next 被忽略，轉到 `/`，不轉去 `//evil` | 自動 |
| TC-H20a | 維護者 1；決策 6 | 功能 | 使用者有 3 個自己的 run，開始時間各不同 | GET `/` | 左欄 run 清單由新到舊排列 | 自動 |
| ~~TC-H20b~~ | ~~維護者 1；決策 6~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~左欄有「專案與分析（011b）尚未開放」這句~~ | 已取代：TC-L05（裁定 B4：一律改成灰字「之後開放」） |
| ~~TC-H20c~~ | ~~決策 6~~ | ~~功能~~ | ~~以姓名 X 登入~~ | ~~GET `/`~~ | ~~左欄底部顯示姓名 X~~ | 已取代：TC-L01（使用者名稱移到頂欄右側，L1） |
| ~~TC-H20d~~ | ~~決策 6~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~左欄底部有「設定（尚未開放）」~~ | 已取代：TC-L06（裁定 B4） |
| TC-H21a | 決策 6 | 功能 | 已登入，網址沒有 `?run=` | GET `/` | 中欄寫「選一個 run」 | 自動 |
| ~~TC-H21b~~ | ~~維護者 1；決策 6~~ | ~~功能~~ | ~~已登入，有一個自己的 run~~ | ~~GET `/?run=<id>`~~ | ~~中欄有五階段條，階段之間有箭頭~~ | 已取代：TC-L07 至 TC-L13（L3：階段條用 is-done／is-current／is-later，不再有階段間箭頭） |
| TC-H21c | 決策 6 | 功能 | 一個 run，已知開始時間、結束時間，以及各狀態的工作數（各不相同） | GET `/?run=<id>` | 中欄階段內容顯示：狀態；開始時間與結束時間各自出現（測試寫死一個已知時間對應的顯示字串，不得只檢查「有時間」）；每個狀態的工作數，各自的數字都出現且與對應狀態配對正確（不得只出現其中一個數字） | 自動 |
| TC-H21d | 決策 6 | 功能 | 一個失敗的 run，`failure_reason` 有文字 | GET `/?run=<id>` | 中欄顯示該失敗原因（Nextflow 的原文） | 自動 |
| TC-H21e | 裁定 3 | 功能 | 選一個 run | GET `/?run=<id>&stage=launch` | 該階段內容顯示「—」與「012b」 | 自動 |
| TC-H21f | 裁定 3 | 功能 | 選一個 run | GET `/?run=<id>&stage=downstream` | 該階段內容顯示「—」與「016」 | 自動 |
| TC-H21g | 裁定 3 | 功能 | 選一個 run | GET `/?run=<id>&stage=finished` | 該階段內容顯示「—」與「013b」 | 自動 |
| ~~TC-H22a~~ | ~~維護者 1；決策 6~~ | ~~功能~~ | ~~已登入，有自己的 run~~ | ~~GET `/`~~ | ~~右欄有五個階段群組~~ | 已取代：TC-L19（裁定 B5：兩個真群組加一塊灰色「之後開放」） |
| TC-H22b | 維護者 1；決策 6；裁定 4；C1 | 功能 | 使用者自己的 run：running 2、lost 1、failed 1、succeeded 3 | GET `/` | 「執行中」群組標題總數 4（running、lost、failed 都算在 running 階段）；「結果」群組標題總數 3 | 自動 |
| TC-H06a | H06；決策 4 | 功能 | 純函數 `stage_of` 對照表 | 用 running、lost、failed、succeeded 各呼叫一次 | running、lost、failed 都得 running；succeeded 得 results | 自動 |
| TC-H06b | H06；決策 4 | 功能 | 一個 succeeded 的 run | GET `/?run=<id>`（不帶 `stage`） | 中欄預設顯示 results 階段 | 自動 |
| TC-H06c | H06；決策 4 | 功能 | 一個 failed 的 run | GET `/?run=<id>`（不帶 `stage`） | 中欄預設顯示 running 階段（失敗屬於 running） | 自動 |
| TC-H08a | 維護者 1；H08；決策 5；L5 | 功能 | 一個 running 的 run | GET `/` | 該 run 帶 running 專屬 class 與文字「執行中」 | 自動 |
| TC-H08b | 維護者 1；H08；決策 5；L5 | 功能 | 一個 succeeded 的 run | GET `/` | 該 run 帶 succeeded 專屬 class 與文字「成功」 | 自動 |
| TC-H08c | 維護者 1；H08；決策 5；L5 | 功能 | 一個 failed 的 run | GET `/` | 該 run 帶 failed 專屬 class 與文字「失敗」 | 自動 |
| TC-H08d | 維護者 1；H08；決策 5；L5 | 功能 | 一個 lost 的 run | GET `/` | 該 run 帶 lost 專屬 class 與文字「失聯/暫停」 | 自動 |
| TC-H08e | H08；決策 5 | 功能 | 四種狀態的 run 各一 | GET `/` | 四個狀態的 class 兩兩不同（只靠顏色以外也分得出來） | 自動 |
| TC-H08f | H08；決策 5 | 功能 | 一個 run：succeeded 6、cached 2、total 10 | GET `/?run=<id>` | 進度是原生 `<progress>`，value 為 8、max 為 10 | 自動 |
| TC-H08g | H08；決策 5 | 例外 | 一個 run 的 total 為 0 | GET `/?run=<id>` | `<progress>` 沒有 value 屬性（不顯示成 0% 或 100%） | 自動 |
| TC-H10a | H10；決策 2 | 功能 | 選一個 run | 分別用 `?stage=launch`、`running`、`results`、`downstream`、`finished` | 五個都被接受，回 200，中欄顯示對應階段（所選階段的格子帶 `aria-current="step"`，見 TC-L12） | 自動 |
| TC-H10b | H10；決策 2 | 例外 | 選一個 run，其階段為 results | 用 `?stage=evil`、`?stage=`（空）、`?stage=<script>`、`?stage=RUNNING` | 一律退回該 run 自己的階段（results），回 200，不是 500 | 自動 |
| TC-H10c | H10；裁定 2；L3 | 功能 | 選一個 run，`stage=running` | GET | 上一階段、下一階段是連結：往前連到 launch、往後連到 results | 自動 |
| TC-H10d | H10；裁定 2；L3 | 功能 | 選一個 run，`stage=launch` | GET | 沒有往前的連結（launch 沒有上一階段），有往後的 | 自動 |
| TC-H10e | H10；裁定 2；L3 | 功能 | 選一個 run，`stage=finished` | GET | 沒有往後的連結（finished 沒有下一階段），有往前的 | 自動 |
| TC-H14a | H14；決策 2 | 功能 | 已登入 | GET `/` | 回應有 `<meta http-equiv="refresh" content="15">` | 自動 |
| TC-H14b | H14；決策 2 | 功能 | 登入頁、確認頁 `/c/<id>`、404 頁 | 各 GET 一次 | 都沒有 meta refresh（只有 `/` 有） | 自動 |
| TC-H18a | H18 | 例外 | 使用者沒有任何 run | GET `/` | 回 200，有空狀態說明，不是 500 | 自動 |
| TC-H18b | H18 | 例外 | `index.db` 是空檔（0 位元組） | GET `/` | 回 200，有空狀態頁，不是 500 | 自動 |
| TC-H18c | H18 | 例外 | `index.db` 不存在 | GET `/` | 回 200，有空狀態頁，不是 500 | 自動 |
| TC-H19a | H19；決策 6 | 功能 | 使用者有 250 個 run | GET `/` | 左欄只列 100 筆，下面寫「還有 150 筆」 | 自動 |
| TC-H19b | H19；裁定 4 | 功能 | 使用者有 250 個 succeeded 的 run | GET `/` | 「結果」群組標題總數 250，只列 100 筆，下面寫「還有 150 筆」 | 自動 |

## User Story 2 — 右邊最上面一行「本月 SU — · 雲端 —」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| ~~TC-H09a~~ | ~~維護者 2；H09~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~右欄最上面是「本月費用」標題~~ | 已取代：TC-L17（裁定 B1：沒有標題，只有一行） |
| ~~TC-H09b~~ | ~~維護者 2；H09~~ | ~~功能~~ | ~~已登入~~ | ~~GET `/`~~ | ~~費用分兩行：「SU —」、「雲端 —」~~ | 已取代：TC-L18（裁定 B1：一行，不釘行數） |
| TC-H09c | 維護者 2；H09 | 功能 | 已登入 | GET `/` | 費用區塊裡沒有任何數字、也沒有連結 | 自動 |
| TC-L17 | 維護者 2；L4；B1 | 功能 | 已登入，有 run | GET `/` | 右欄最上面（在任何群組之前）是一行，文字（去掉標籤與多餘空白後）正好是「本月 SU — · 雲端 —」 | 自動 |
| TC-L18 | 維護者 2；B1；option B | 功能 | 已登入 | GET `/`，並讀 `web_board.py` 原始碼 | 頁面沒有「本月費用」標題；頁面與 `web_board.py` 都不出現站名「NCHC」（標籤是不帶站名的「SU」，程式維持與站台無關） | 自動 |

## User Story 3 — 整頁只能看，每人只看到自己的 run（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H03a | 維護者 3；H03 | 例外 | 使用者 A、B 各送出一個 run，名稱不同 | 以 A 登入 GET `/` | 整份 HTML 任何地方都沒有 B 的 run 名稱 | 自動 |
| TC-H03b | 維護者 3；H03 | 例外 | 同上，A 有 1 個 run、B 有 5 個 | 以 A 登入 GET `/` | 各群組標題總數與計數只算 A 的，沒有算進 B 的 | 自動 |
| TC-H04a | 維護者 3；H04 | 例外 | 有一個 run 在 `launches` 完全沒有記錄 | 分別以 A、B 登入 GET `/` | 兩人都看不到，左欄、右欄、計數都沒有它 | 自動 |
| TC-H04b | 維護者 3；H04 | 例外 | 有一個 run 的 `launches` 紀錄使用者欄是 NULL | 分別以 A、B 登入 GET `/` | 兩人都看不到，左欄、右欄、計數都沒有它 | 自動 |
| TC-H04c | 維護者 3；H04 | 功能 | 同 H04a、H04b 的兩個 run | 以本機終端機路徑（`caller=None`）呼叫 `list_runs` | 這兩個 run 都列得出來（只能在本機終端機查） | 自動 |
| TC-H05a | H05；決策 8 | 例外 | A、B 各有 run | 以 A 登入 GET `/?run=<B 的 run id>` | 回 404 頁，不是 B 的 run 內容 | 自動 |
| TC-H05b | H05；決策 8 | 例外 | 已登入 | GET `/?run=<不存在的 id>` | 回 404 頁 | 自動 |
| TC-H05c | H05；裁定 5 | 例外 | 同 H05a、H05b | 比較「別人的 run」與「不存在的 id」兩份回應 | 兩份 404 頁逐位元組相同（看不出差別） | 自動 |
| TC-H05d | 裁定 5 | 例外 | 已登入 | GET `/?run=<一段獨特字串>` | 404 頁內容不含這段字串（不回顯使用者輸入的 id） | 自動 |
| TC-H15 | H15 | 例外 | 沒有 cookie，但帶 `Authorization: Bearer <有效的 token>` | GET `/` | 一樣回 303 轉登入，Bearer 不算登入 | 自動 |
| TC-H11a | 維護者 3；H11 | 功能 | 已登入，選一個 run | GET `/`、`/?run=<id>` | 整頁唯一的 `<form>` 是登出；沒有其他按鈕或表單 | 自動 |
| TC-H11b | H11 | 功能 | 同上 | GET `/` | 登出表單帶 CSRF 欄位（防跨站偽造的一次性記號） | 自動 |
| TC-H11c | H11 | 例外 | 已登入 | POST `/` | 回 405 | 自動 |
| TC-H11d | H11；裁定 C3 | 功能 | 網頁 app | 列出全部路由 | 路由集合正好等於 v3 合併後的既有路由（含 009i 的 OAuth／同意頁）加上 GET `/`（與 HEAD）；多一條或少一條都不過 | 自動 |
| TC-H11e | H11 | 功能 | 記下 `index.db`、`platform.db`、`tokens.db`、簽章金鑰的雜湊值 | GET `/`、`/?run=<id>`、`/?stage=running`、`/?lang=en` 各一次 | 所有資料庫檔的雜湊值都沒變（GET 什麼都沒寫） | 自動 |
| TC-H12a | H12 | 例外 | run 名稱含 `<script>alert(1)</script>` 與 `"><b>` | GET `/` | 這些字被轉義，HTML 裡沒有可執行的標籤 | 自動 |
| TC-H12b | H12 | 例外 | `failure_reason` 含 `<img src=x onerror=1>` | GET `/?run=<id>` | 轉義後顯示，沒有真的 `<img>` 標籤 | 自動 |
| TC-H12c | H12 | 例外 | run 的 id 含引號等特殊字元 | GET `/` 與 `/?lang=en` | 連結裡的 id 放在引號內且已轉義，`href` 不會被截斷 | 自動 |
| TC-H12d | H12；C4 | 例外 | 一個 failed 的 run，`failure_reason` 第一行是 `<img src=x onerror=1>` | GET `/`（不選 run，只看右欄項目的重點） | 右欄項目裡的重點是轉義後的文字，頁面沒有真的 `<img>` 標籤 | 自動 |
| TC-H13a | H13；決策 7 | 功能 | 任一頁 | GET `/` | CSP 標頭沒有 `script-src` | 自動 |
| TC-H13b | H13；決策 7 | 功能 | 任一頁 | GET `/` | CSP 標頭沒有 `'unsafe-inline'` | 自動 |
| TC-H13c | H13；決策 7；L6 | 功能 | 已登入 | GET `/`、`/?lang=en` | CSP 的 `style-src` 是 sha256 雜湊，且與該頁內嵌樣式表（新版面的那一份）的雜湊一致 | 自動 |
| TC-H13d | H13；決策 7 | 功能 | 登入頁、確認頁、404 頁 | 各 GET 一次 | 每一頁的 CSP 雜湊都與該頁內嵌樣式表一致（改了 CSP 沒弄壞舊頁面） | 自動 |
| TC-H13e | H13；L6 | 功能 | 已登入，有 run | GET `/`、`/?run=<id>` | HTML 沒有 `<script>` | 自動 |
| TC-H13f | H13；決策 5；L6 | 功能 | 同上 | 同上 | HTML 沒有任何 `style=` 屬性（含 `<progress>`） | 自動 |
| TC-H13g | H13 | 功能 | 同上 | 同上 | HTML 沒有 `onclick=` 之類的 `on*=` 屬性 | 自動 |
| TC-H13h | H13 | 功能 | 同上 | 同上 | HTML 沒有指向外部主機的資源或連結 | 自動 |
| TC-H13i | 決策 7；L6 | 功能 | 任一頁 | GET `/` | CSP 其餘部分不變：`default-src 'none'`、`form-action 'self'`、`frame-ancestors 'none'`、`base-uri 'none'` | 自動 |
| TC-H17 | H17；決策 8 | 功能 | 程式碼靜態檢查（AST，即讀語法樹） | 掃 `web.py`、`web_board.py` 裡每個對 `list_runs`、`get_run` 的呼叫（含右欄為失敗項目呼叫的 `get_run`） | 每個呼叫都有 `caller=`，且值不是 None | 自動 |

## User Story 4 — 網頁與 MCP 工具一一對照（優先度 P2）

對應 `docs/ROADMAP.md` 的「owed parity」一列；測試檔 `platform/tests/test_web_parity.py`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H16a | H16；裁定 1 | 功能 | 目前這個分支 | 跑 `test_web_parity.py` | 全部通過 | 自動：`platform/tests/test_web_parity.py` |
| TC-H16b | H16；裁定 1(a) | 功能 | 四張表 `WEB_ROUTES`、`WEB_ONLY`、`OWED`、`INTERNAL` | 比對四表聯集與 `actions` 的公開名稱 | 兩邊完全相等，每個名稱剛好在一張表 | 自動 |
| TC-H16c | H16；裁定 1(b) | 功能 | `WEB_ROUTES`（`list_runs`、`get_run`） | 對照 MCP 伺服器的工具清單 | 每個名稱都有同名 MCP 工具 | 自動 |
| TC-H16d | H16；裁定 1 | 功能 | `OWED` 表 | 讀它的內容 | 正好六個：`list_compute_envs`、`get_compute_env`、`list_agents`、`list_site_files`、`launch`、`cancel`；多一個或少一個都不過 | 自動 |
| TC-H16e | H16；裁定 1(c) | 功能 | `OWED` 表與網頁路由 | 檢查是否有網頁路由呼叫 `OWED` 的名稱 | 沒有任何 `OWED` 名稱被網頁路由呼叫 | 自動 |
| TC-H16f1 | H16；決策 9；裁定 1(d) | 功能 | `web.py`、`web_board.py` | AST 掃描它們呼叫的 `actions` 名稱 | 都在 `WEB_ROUTES`、`WEB_ONLY`、`INTERNAL` 內 | 自動 |
| TC-H16f2 | H16；決策 9 | 功能 | 同上 | AST 掃描 import | 沒有 import `confirm`、`jobs`、`compute_envs`、`agents`、`status` | 自動 |
| TC-H16g | H16；裁定 1 | 例外 | 測試內示範：在 `actions` 加一個四表都沒有的公開函式 | 對它跑「聯集等於公開名稱」的檢查 | 檢查失敗（紅）；證明它真的會擋 | 自動 |
| TC-H16h | H16；裁定 1 | 例外 | 測試內示範：讓網頁路由呼叫一個 `OWED` 名稱 | 對它跑「`OWED` 不被網頁呼叫」的檢查 | 檢查失敗（紅）；證明它真的會擋 | 自動 |

## User Story 5 — 文件、被改寫的舊測試、人工檢視（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-D01 | 計畫「Pins to rewrite」 | 功能 | `specs/011a-web-shell/ledger.md` | 讀 ledger | 009c 的 TC-G04（路由集合）改為多一條 GET `/`，ledger 寫有舊值、新值、理由 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D02 | 同上 | 功能 | 同上 | 讀 ledger | 登入後那頁「已登入…請回到 AI…」的舊斷言改寫，ledger 寫有舊值、新值、理由 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D03 | 同上 | 功能 | 同上 | 讀 ledger | CSP 字串的舊斷言（若有被釘住）改寫，ledger 有舊新理由；若原本沒被釘住，ledger 明寫「沒有」 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D04 | 同上 | 功能 | 同上 | 讀 ledger | `PLATFORM.md` 文字釘子改寫，ledger 有舊新理由 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D05 | 憲法「弱化測試」 | 例外 | 本分支對 v3 的 diff | 逐個比對動到的測試檔 | 除 ledger 列名的幾處外，沒有任何舊斷言被刪掉、放寬、跳過或改成配合新輸出 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D06 | 決策 10 | 功能 | `docs/PLATFORM.md` | 讀第 8、372、424 行附近與 CSP 那一行 | 網頁路由的敘述包含 GET `/`；不再說「只有登入頁與確認頁」；CSP 描述（樣式表雜湊）與新標頭一致 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D07 | 決策 10 | 功能 | `CHANGELOG` | 讀 | 有 011a 的一則紀錄 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D08 | 決策 10 | 功能 | `web.py` 開頭說明文字 | 讀 | 說明已改成包含 GET `/` 的三欄唯讀畫面 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D09 | 裁定 7 | 功能 | `docs/TESTING.md` | 讀 | 有「視覺檢查」與「ledger 檢視」兩組具體步驟，照著做得出來 | 手動：`docs/TESTING.md` |
| TC-D10 | L8；憲法「弱化測試」 | 功能 | `specs/011a-web-shell/ledger.md` 與本分支對上一版的測試 diff | 對照「釘住舊版面標記」的測試與 ledger | 每一條為新版面改過的斷言，ledger 都寫有舊斷言、新斷言、理由；沒有任何斷言被刪掉而沒有替代 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D11 | 計畫「Ruling after acceptance round 2」 | 功能 | `platform/tests/test_launch_static.py` | 與 v3 比對 | tc069、tc070 與 v3 逐字相同，沒有任何為「NCHC SU」加的豁免 | 手動：`docs/TESTING.md`（ledger 檢視） |
| ~~TC-V01~~ | ~~Tier B 視覺檢查；維護者 1~~ | ~~功能~~ | ~~本機啟動 `abf-platform web`，灌入 e2e 假 run~~ | ~~登入後開 `/`，截圖~~ | ~~看得到三欄、右欄「本月費用」與五個群組~~ | 已取代：TC-V06（新版面） |
| TC-V02 | Tier B 視覺檢查 | 功能 | 本機啟動 `abf-platform web`，灌入 e2e 假 run，有一個 succeeded 的 run | 選該 run，截圖 | 截圖附在 PR；中欄五階段板的「結果」是目前階段，看得到狀態、時間、進度條 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V03 | Tier B 視覺檢查 | 功能 | 同上，有一個 failed 的 run | 選該 run，截圖 | 截圖附在 PR；中欄看得到失敗狀態與失敗原因 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V04 | 維護者 1；裁定 6；L5 | 功能 | 本機頁面的截圖 | 用肉眼看（可轉成黑白） | 四種狀態各有文字與符號（▶ ✓ ✗ ⏸），不靠顏色也分得出來 | 手動：`docs/TESTING.md`（視覺檢查） |
| ~~TC-V05~~ | ~~決策 6~~ | ~~功能~~ | ~~本機頁面~~ | ~~縮到約 900 px 以下，截圖~~ | ~~三欄改成上下堆疊~~ | 已取代：TC-V07（堆疊順序已指定） |
| TC-V06 | 維護者 1；L9 | 功能 | 本機啟動 `abf-platform web`，灌入 e2e 假 run（含 running、failed、lost、succeeded） | 登入後以寬螢幕開 `/`（中文），截圖 | 截圖附在 PR；看得到深色細頂欄（左 `agentic-bioflow`、右使用者名與 `中｜EN`）、左欄 232px 的 run 清單與灰字「之後開放」、右欄最上面一行「本月 SU — · 雲端 —」、其下「執行中」「結果」兩群組與有底色的整塊項目 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V07 | L6；L9 | 功能 | 同上 | 把視窗縮到 900 px 以下（中文），截圖 | 截圖附在 PR；三欄改成上下堆疊，順序為中欄、右欄、左欄；內容沒被切掉 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V08 | L7；L9 | 功能 | 同上 | 開 `/?lang=en` 並選一個 run，寬螢幕截圖 | 截圖附在 PR；畫面上的介面文字全是英文，run 名稱維持原樣 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V09 | L6；L7；L9 | 功能 | 同上 | 開 `/?lang=en`，縮到 900 px 以下，截圖 | 截圖附在 PR；英文版同樣堆疊成中欄、右欄、左欄，內容沒被切掉 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V10 | 維護者選 B；L3；L4 | 功能 | TC-V06 的截圖與 `specs/011a-web-shell/layoutB-reference.html` | 並排比對 | 版面骨架與參考稿一致：階段條用實線（已完成、目前）與虛線（之後）區分、右欄項目是整塊上色、被選的 run 有外框；與參考稿不同之處只限計畫列為「之後」的功能 | 手動：`docs/TESTING.md`（視覺檢查） |

## User Story 6 — 這次不做的事（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| ~~TC-N01~~ | ~~不做：專案與分析（011b）~~ | ~~不在範圍~~ | ~~已登入~~ | ~~GET `/` 並列出路由~~ | ~~左欄只有「尚未開放」說明~~ | 已取代：TC-N11（裁定 B4 的新字樣） |
| TC-N02 | 不做：run 詳情、log、失敗一句話、resume／restart（011c、011e） | 不在範圍 | 已登入，有 failed run | GET `/?run=<id>` 與 GET `/runs/<id>`、`/logs`、`/resume`、`/restart` | 頁面沒有 log、resume、restart 的連結或按鈕；那幾個路徑回 404（或 405）；失敗只顯示 `failure_reason` 原文 | 自動 |
| TC-N03 | 不做：費用數字（011d） | 不在範圍 | 灌入有工作數的 run | GET `/` | 費用那一行仍是「—」，頁面任何地方沒有算出來的費用數字 | 自動 |
| TC-N04 | 不做：設定、送出表單、上傳、結果、Studios、聊天（012 至 014、016） | 不在範圍 | 已登入 | 對 `/runs`、`/ce`、`/compute-envs`、`/oauth/token`、`/oauth/authorize`、`/admin`、`/launch`、`/submit`、`/upload`、`/password`、`/passwd`、`/settings`、`/api/launch` GET 與 POST | GET 都 404；POST 都 404 或 405 | 自動 |
| TC-N05 | 不做：`get_board` 或任何新 MCP 工具 | 不在範圍 | MCP 伺服器與 `actions` | 讀 MCP 工具清單與 `actions` 公開名稱 | 與 v3 相比沒有新增工具、沒有新增 action，也沒有 `get_board` | 自動 |
| TC-N06 | 不做：JavaScript、即時推送 | 不在範圍 | 網頁 app | 列出路由與回應 | 沒有 WebSocket 或事件串流（SSE，伺服器持續推資料）路由；更新只靠 15 秒的 meta refresh | 自動 |
| TC-N07 | 不做：所有權程式（#116）與角色（010） | 不在範圍 | 本分支對 v3 的 diff | 看 `actions/`、`jobs.py`、`mcp_server.py` 與 `store.py` 的變動 | 沒有為本功能改所有權判斷，也沒有新增角色或「看全實驗室」的檢視 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-N08 | 不做：登入頁與確認頁的翻譯（裁定 B6，後續切片） | 不在範圍 | 已登入，並有一筆待確認申請 | GET `/login?lang=en` 與 `/c/<id>?lang=en` | 兩頁仍是中文原樣，沒有被翻成英文；`lang` 對它們沒有作用 | 自動 |
| TC-N09 | 不做：cookie 或 JavaScript 記住語言（L7） | 不在範圍 | 已登入 | GET `/?lang=en`，再 GET `/`（不帶 lang） | 第一個回應沒有任何 `Set-Cookie`；第二個回應是中文（不記得上一次的選擇）；切換只靠兩個普通連結 | 自動 |
| TC-N10 | 不做：聊天框、分頁、上傳、Studios、專案頁（設計稿裡屬於 011b 以後與 012 至 016 的部分） | 不在範圍 | 已登入，選一個 run | GET `/` 與 `/?run=<id>` | 沒有 `<textarea>`；除登出表單的 CSRF 隱藏欄位外沒有 `<input>`；沒有 `<details>` 與分頁用的 radio；頁面上所有 `<a>` 的目標都只指向 `/`（可帶 `run`、`stage`、`lang` 查詢參數） | 自動 |
| TC-N11 | 不做：專案與分析（011b）；裁定 B4 | 不在範圍 | 已登入 | GET `/`，並列出路由 | 左欄沒有專案或分析的連結、清單或表單；尚未做的項目只是灰字「之後開放」，不在連結內；路由仍是 v3 既有路由加 GET `/`（同 TC-H11d） | 自動 |

## User Story 7 — 版面 B：Galaxy 三欄工作台，與中英切換（優先度 P1）

對應計畫「Layout redo: option B」L1 至 L9 與裁定 B1 至 B6、C1 至 C6。維護者否決了第二輪版面、選了 B。

### 框架（L1 至 L6）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-L01 | L1 | 功能 | 以純 ASCII 姓名 X 登入 | GET `/` | 頁面最上方有一條頂欄，在三欄之前；左邊是 `agentic-bioflow`；右邊有姓名 X 與「中｜EN」切換 | 自動 |
| TC-L02 | 維護者 1；L2 至 L4 | 功能 | 已登入，有 run | GET `/` | 回 200；同一頁有左、中、右三個區塊：左欄含標題「我的 run」，中欄是「選一個 run」或階段板，右欄含費用行與群組 | 自動 |
| TC-L03 | L2；L4；L8 | 功能 | 取出頁面內嵌的那份樣式表 | 讀樣式表 | 三欄格線：左欄寬 232px、右欄寬 272px、中欄取剩下的寬度 | 自動 |
| TC-L04 | L6；L8 | 功能 | 同上 | 讀樣式表 | 有寬度 900px 以下的媒體查詢（寬度小於 900px 改成單欄） | 自動 |
| TC-L05 | 維護者 1；L2；B4 | 功能 | 已登入，有 3 個 run | GET `/` | 左欄標題「我的 run」之下，每個 run 是一個連到 `/?run=<id>` 的連結；沒有專案或分析的樹狀項目可點；尚未做的項目是灰字「之後開放」，且這些字不在任何連結內 | 自動 |
| TC-L06 | L2；B4 | 功能 | 已登入 | GET `/` | 左欄底部有「設定」並標灰字「之後開放」，不是連結、不是表單；同處有「登出」，它是整頁唯一的表單（見 TC-H11a） | 自動 |

### 中欄：階段條與階段內容（L3，B2，C6）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-L07 | L3；B5 | 功能 | 已登入，選一個 run | GET `/?run=<id>` | 階段條依序有五格：送出、執行中、結果、下游、完成 | 自動 |
| TC-L08 | L3；B2 | 功能 | 一個 running 的 run | GET `/?run=<id>` | 「送出」帶 `is-done`；「執行中」帶 `is-current`；「結果」「下游」「完成」帶 `is-later`；`is-current` 只有一格 | 自動 |
| TC-L09 | L3；B2 | 功能 | 一個 succeeded 的 run | GET `/?run=<id>` | 「送出」「執行中」帶 `is-done`；「結果」帶 `is-current`；「下游」「完成」帶 `is-later` | 自動 |
| TC-L10 | L3；B2；C1 | 功能 | 一個 failed 的 run | GET `/?run=<id>` | 與 running 相同：「送出」`is-done`、「執行中」`is-current`、其餘三格 `is-later` | 自動 |
| TC-L11 | L3；B2；C1 | 功能 | 一個 lost 的 run | GET `/?run=<id>` | 與 running 相同：「送出」`is-done`、「執行中」`is-current`、其餘三格 `is-later` | 自動 |
| TC-L12 | B2 | 功能 | 一個 running 的 run | GET `/?run=<id>&stage=results` | 各格的 `is-done`／`is-current`／`is-later` 與 TC-L08 完全一樣（選階段不改它們）；只有「結果」格帶 `aria-current="step"`，其他格沒有 | 自動 |
| TC-L13 | B2；決策 2 | 功能 | 一個 succeeded 的 run、一個 failed 的 run | 各 GET `/?run=<id>`（不帶 `stage`） | succeeded 的 run 由「結果」格帶 `aria-current="step"`；failed 的 run 由「執行中」格帶 | 自動 |
| TC-L14 | L3；L5 | 功能 | 一個 failed 的 run | GET `/?run=<id>` | 中欄上方有該 run 的名稱，旁邊是狀態徽章：符號「✗」、文字「失敗」、failed 專屬 class | 自動 |
| TC-L15 | L3；C6 | 功能 | 一個 run，七種工作數各不相同（成功 11、快取 12、失敗 13、中止 14、執行中 15、等待 16、已送出 17） | GET `/?run=<id>` | 階段內容卡有七格，依序是「成功」「快取」「失敗」「中止」「執行中」「等待」「已送出」，每格的標籤與數字配對正確（成功 11、快取 12 …） | 自動 |
| TC-L16 | L3；裁定 2 | 功能 | 選一個 run，`stage=running` | GET | 有兩個連結，文字為「← 上一階段」與「下一階段 →」，分別連到 `stage=launch` 與 `stage=results`，且保留同一個 `run` | 自動 |

### 右欄：群組與項目（L4，B3，B5，C1，C4，C5）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-L19 | 維護者 1；L4；B5 | 功能 | 已登入，有四種狀態的 run | GET `/` | 右欄在費用行之後依序是：「執行中（n）」群組、「結果（n）」群組、一塊灰色「之後開放」（代表送出、下游、完成）；沒有「送出」「下游」「完成」各自的群組標題或計數 | 自動 |
| TC-L20 | 維護者 1；B5；C1 | 功能 | running 1、failed 1、lost 1、succeeded 1，名稱各不同 | GET `/` | running、failed、lost 三個項目都在「執行中」群組內；succeeded 的項目在「結果」群組內；failed 與 lost 不在「結果」群組 | 自動 |
| TC-L21 | L4；L5 | 功能 | 一個 running 的 run | GET `/` | 右欄該項目是一整塊：含「序號 名稱」與「▶ 執行中 · 重點」，整塊在同一個連到 `/?run=<id>` 的連結內，並帶 running 專屬 class | 自動 |
| TC-L22 | B3 | 功能 | 使用者有 3 個 run，開始時間依序為 t1、t2、t3（t1 最早） | GET `/` | 右欄同一群組內由上到下序號為 3、2、1（最新在上），序號 1 是 t1 那個 run | 自動 |
| TC-L23 | B3；C5 | 功能 | 一個 running 的 run：succeeded 6、cached 2、total 10 | GET `/` | 該項目的重點是「8/10」（完成數 = 成功 + 快取） | 自動 |
| TC-L24 | B3；C5 | 功能 | 一個 succeeded 的 run，已知結束時間 | GET `/` 與 `/?run=<id>` | 右欄項目的重點是結束時間，其字串與中欄顯示的結束時間逐字相同；測試寫死已知時間對應的顯示字串 | 自動 |
| TC-L25 | B3 | 功能 | 一個 failed 的 run，`failure_reason` 第一行有 120 個字元，其後還有第二行 | GET `/` | 項目的重點是第一行，最多 80 個字元：第 81 個字元之後與第二行的內容都不出現；第一行不超過 80 字時完整顯示 | 自動 |
| TC-L26 | C4 | 例外 | 一個 failed 的 run，`failure_reason` 缺少；另一個 failed 的 run，`failure_reason` 是空字串 | GET `/` | 兩個項目的重點都是「原因未記錄」，頁面不是 500 | 自動 |
| TC-L27 | B3 | 功能 | 一個 lost 的 run | GET `/` | 該項目的重點是「—」 | 自動 |
| TC-L28 | L4 | 功能 | 3 個 run | GET `/?run=<其中第二個>`，再 GET `/`（不選 run） | 前者：只有被選的那個項目帶「被選取」標記，且樣式表對該標記設了外框（outline）；後者：沒有任何項目帶該標記 | 自動 |
| TC-L29 | C4；決策 3 | 功能 | 使用者有 250 個 failed 的 run；測試記錄 `get_run` 的呼叫 | GET `/`（不選 run） | 右欄「執行中」群組只列 100 個項目；右欄為失敗項目呼叫 `get_run` 的次數不超過 100，且每次都帶登入者的 `caller` | 自動 |
| TC-L30 | B3；裁定 4 | 功能 | 使用者有 250 個 succeeded 的 run，開始時間各不同 | GET `/` | 「結果」群組標題 250，只列 100 個；最上面項目序號 250，第 100 個項目序號 151（序號是在全部 250 個 run 裡算的，不是在顯示的 100 個裡算） | 自動 |

### 語言（L7，B6）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-L31 | L7 | 功能 | 已登入，有 run | GET `/`（不帶 `lang`） | 介面文字是中文（例如「執行中」「之後開放」「登出」）；沒有出現英文的七格標籤「Cached」「Aborted」「Pending」「Submitted」 | 自動 |
| TC-L32 | L7；L8 | 功能 | 純 ASCII 的使用者名與 run 名稱，有 running、failed、succeeded 的 run，選一個 run | GET `/?run=<id>&lang=en` | 整份 HTML 除了切換器上的語言名「中」之外，沒有任何 CJK 字元（所有介面文字都換成英文） | 自動 |
| TC-L33 | L7；C6 | 功能 | 一個 run，七種工作數各不相同 | GET `/?run=<id>&lang=en` | 七格標籤依序是 Succeeded、Cached、Failed、Aborted、Running、Pending、Submitted（不分大小寫），每格與其數字配對正確 | 自動 |
| TC-L34 | C4；L7 | 例外 | 純 ASCII 名稱、failed 且 `failure_reason` 缺少的 run | GET `/?lang=en` | 該項目的重點是「reason not recorded」 | 自動 |
| TC-L35 | L7 | 功能 | 已登入，選一個 run 並選階段 | GET `/?run=<id>&stage=results` | 頂欄有「中」與「EN」兩個普通連結（不是表單、不是按鈕）；「EN」連到同一路徑，帶相同的 `run`、`stage`，再加 `lang=en`；「中」連到同一路徑，帶相同的 `run`、`stage`，不帶 `lang=en` | 自動 |
| TC-L36 | B6 | 功能 | 已登入，有 run，選一個 run 並選階段 | GET `/?run=<id>&stage=running&lang=en` | 頁面上所有指向看板的連結（左欄與右欄的 run 連結、上一階段與下一階段、各群組項目）都帶 `lang=en`；唯一例外是切換器的「中」連結 | 自動 |
| TC-L37 | B6；L7 | 功能 | 同上 | GET `/?run=<id>&stage=running`（中文） | 所有連結都不帶 `lang=en`；唯一例外是切換器的「EN」連結 | 自動 |
| TC-L38 | L7 | 功能 | 一個 run，名稱是「大豆根腐」，failed 且 `failure_reason` 是中文句子 | GET `/?lang=en` 與 `/?run=<id>&lang=en` | run 名稱與失敗原因的中文逐字原樣出現（資料不翻譯） | 自動 |
| TC-L39 | B6 | 例外 | 已登入 | GET `/?run=<不存在的 id>&lang=en` | 回 404 頁，內容為英文：除切換器的「中」外沒有任何 CJK 字元 | 自動 |
| TC-L40 | B6；裁定 5 | 例外 | A、B 各有 run | 以 A 登入，分別 GET `/?run=<B 的 run id>&lang=en` 與 `/?run=<不存在的 id>&lang=en` | 兩份英文 404 頁逐位元組相同，也不回顯所請求的 id | 自動 |
| TC-L41 | L7 | 例外 | 已登入 | 分別 GET `/?lang=fr`、`/?lang=`、`/?lang=<script>` | 都回 200，頁面是預設的中文，沒有真的 `<script>` 標籤，不是 500 | 自動 |
| TC-L42 | L7；L8 | 功能 | 看板的字串表（全部介面文字的唯一來源） | 讀表 | `zh` 與 `en` 兩份鍵完全相同、沒有空值；`en` 的值沒有 CJK 字元（語言名「中」除外） | 自動 |
| TC-L43 | L7；H18 | 例外 | 純 ASCII 使用者名，沒有任何 run | GET `/?lang=en` | 回 200，空狀態說明為英文：除切換器的「中」外沒有任何 CJK 字元 | 自動 |
| TC-L44 | L6；L8 | 功能 | 已登入，有 run | GET `/`、`/?run=<id>`、`/?run=<id>&stage=running`、`?lang=en` 的各版本、404 頁、空狀態頁 | 每份 HTML 都不含 `http` 開頭的網址；沒有 `<script`、沒有 `style=` | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-K1 | 原則 I.2（確認只能由人在指定管道做） | 功能 | 記下 `launches`、`jobs`、待確認申請的筆數 | GET `/` 與 `/?run=<id>` 數次（含 `lang=en`） | 筆數都沒變；網頁讀取不會建立任何申請或工作 | 自動 |
| TC-K2 | 原則 I.2（未確認的送出被拒） | 例外 | 既有的 `test_tch09_*`（`test_human_channel.py`）與 `test_tch09_b_c_*`（`test_confirm_page.py`） | 跑 `tests/platform_test.sh` | 兩組仍全過，內容未被放寬 | 自動 |
| TC-H07a | 原則 I.2（不存第二份 run 狀態）；H07 | 功能 | 本分支的資料庫結構與 `web_board.py` | 檢查資料表欄位與程式 | 沒有儲存「階段」的欄位或檔案；階段與序號每次由狀態與開始時間算出，沒有存下來 | 自動 |
| TC-H07b | 原則 I.2；H07 | 功能 | 本分支 | 跑 `tests/no_second_run_state_test.sh` | 通過 | 自動：`tests/no_second_run_state_test.sh` |
| TC-K5 | 安全網（不得放寬） | 功能 | 本分支對 v3 的 diff | 看 `hooks/`、`.claude/`、deny 規則是否被動到 | 沒有任何 hook 或 deny 被改動 | 手動：`docs/TESTING.md`（ledger 檢視） |
