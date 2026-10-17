# 測試案例：011a 網頁外殼（三欄、唯讀）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
There is no spec.md for 011a: the plan's section 「給維護者」 (three numbered points) is the maintainer's own statement of what he wants,
and the plan's TC-H01 to TC-H19 are the base. Nothing here invents behaviour the plan does not state.
IDs: TC-H01 to TC-H19 keep the plan's numbers; a letter (a, b, ...) splits one plan item into one expectation per row.
TC-H20 to TC-H22 cover the layout of decision 6 and ruling 3, which the plan lists but gives no H-number.
Language: 繁體中文; identifiers (TC-, H, FR) and file paths stay as they are.
-->

**規格**：`specs/011a-web-shell/plan.md`（無獨立 spec.md；「給維護者」三點即維護者的原話）　**總覽**：`test-case-overview.md`

「給維護者」三點，下面簡稱「維護者 1／2／3」：

1. 登入網頁後看到三欄畫面：左邊是你的 run 清單，專案功能還沒做，頁面會照實寫出來；中間是選到的那個 run 的五階段板；右邊是你所有 run 的進度，照階段分組、用顏色加文字標狀態。
2. 右邊最上面寫「本月費用」，現在顯示「—」。國網 SU 和雲端費用分兩行。
3. 整頁只能看，沒有會改東西的按鈕。每人只看到自己送出的 run；沒記錄送出者的舊 run 不顯示，只能在本機終端機查。

名詞：「階段」= launch、running、results、downstream、finished 五個，網址用 `?stage=` 選。「群組」= 右欄依階段分的區塊。「CSP」= 網頁回應附帶的安全標頭，限制頁面能載入什麼。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 登入後看到三欄畫面（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H01a | 維護者 1；H01 | 例外 | 沒有登入（請求沒帶 cookie） | GET `/` | 回 303，轉到 `/login`；回應內容沒有任何 run 資料 | 自動 |
| TC-H01b | 維護者 1；H01 | 功能 | 已登入（帶有效 cookie） | GET `/` | 回 200；同一頁有三欄：左「我的 run」、中（「選一個 run」或五階段板）、右「本月費用」 | 自動 |
| TC-H02a | H02 | 功能 | 有網頁密碼的使用者；登入表單沒有 next | 送出正確姓名與密碼 | 回 303 轉到 `/`；不再出現「已登入…請回到 AI…」那個沒有下一步的頁面 | 自動 |
| TC-H02b | H02 | 功能 | 登入表單帶 `next=/c/<32 位十六進位>` | 送出正確姓名與密碼 | 仍轉到那個 `/c/...` 確認頁（既有行為不變） | 自動 |
| TC-H02c | H02 | 例外 | 登入表單帶 `next=//evil` | 送出正確姓名與密碼 | next 被忽略，轉到 `/`，不轉去 `//evil` | 自動 |
| TC-H20a | 維護者 1；決策 6 | 功能 | 使用者有 3 個自己的 run，開始時間各不同 | GET `/` | 左欄「我的 run」由新到舊排列 | 自動 |
| TC-H20b | 維護者 1；決策 6 | 功能 | 已登入 | GET `/` | 左欄有「專案與分析（011b）尚未開放」這句，沒有專案清單 | 自動 |
| TC-H20c | 決策 6 | 功能 | 以姓名 X 登入 | GET `/` | 左欄底部顯示姓名 X | 自動 |
| TC-H20d | 決策 6 | 功能 | 已登入 | GET `/` | 左欄底部有「設定（尚未開放）」字樣，且沒有通往設定功能的連結或表單 | 自動 |
| TC-H21a | 決策 6 | 功能 | 已登入，網址沒有 `?run=` | GET `/` | 中欄寫「選一個 run」 | 自動 |
| TC-H21b | 維護者 1；決策 6 | 功能 | 已登入，有一個自己的 run | GET `/?run=<該 run 的 id>` | 中欄有五階段條，順序為 launch、running、results、downstream、finished，階段之間有箭頭 | 自動 |
| TC-H21c | 決策 6 | 功能 | 一個 run，已知開始時間、結束時間，以及各狀態的工作數（例如已完成 3、執行中 2、失敗 1，各不相同） | GET `/?run=<id>` | 中欄階段內容顯示：狀態；開始時間與結束時間，兩個時間值都逐字出現；每個狀態的工作數，各自的數字都逐字出現且與對應狀態配對正確（不得只出現其中一個數字） | 自動 |
| TC-H21d | 決策 6 | 功能 | 一個失敗的 run，`failure_reason` 有文字 | GET `/?run=<id>` | 中欄顯示該失敗原因（Nextflow 的原文） | 自動 |
| TC-H21e | 裁定 3 | 功能 | 選一個 run | GET `/?run=<id>&stage=launch` | 該階段內容顯示「—」與「012b」 | 自動 |
| TC-H21f | 裁定 3 | 功能 | 選一個 run | GET `/?run=<id>&stage=downstream` | 該階段內容顯示「—」與「016」 | 自動 |
| TC-H21g | 裁定 3 | 功能 | 選一個 run | GET `/?run=<id>&stage=finished` | 該階段內容顯示「—」與「013b」 | 自動 |
| TC-H22a | 維護者 1；決策 6 | 功能 | 已登入，有自己的 run | GET `/` | 右欄有五個階段群組，順序為 launch、running、results、downstream、finished | 自動 |
| TC-H22b | 維護者 1；決策 6；裁定 4 | 功能 | 使用者自己的 run：running 2、lost 1、failed 1、succeeded 3 | GET `/` | running 群組標題總數 4；results 群組標題總數 3 | 自動 |
| TC-H06a | H06；決策 4 | 功能 | 純函數 `stage_of` 對照表 | 用 running、lost、failed、succeeded 各呼叫一次 | running、lost、failed 都得 running；succeeded 得 results | 自動 |
| TC-H06b | H06；決策 4 | 功能 | 一個 succeeded 的 run | GET `/?run=<id>`（不帶 `stage`） | 中欄預設顯示 results 階段 | 自動 |
| TC-H06c | H06；決策 4 | 功能 | 一個 failed 的 run | GET `/?run=<id>`（不帶 `stage`） | 中欄預設顯示 running 階段（失敗屬於 running） | 自動 |
| TC-H08a | 維護者 1；H08；決策 5 | 功能 | 一個 running 的 run | GET `/` | 該 run 帶 running 專屬 class 與文字「執行中」 | 自動 |
| TC-H08b | 維護者 1；H08；決策 5 | 功能 | 一個 succeeded 的 run | GET `/` | 該 run 帶 succeeded 專屬 class 與文字「成功」 | 自動 |
| TC-H08c | 維護者 1；H08；決策 5 | 功能 | 一個 failed 的 run | GET `/` | 該 run 帶 failed 專屬 class 與文字「失敗」 | 自動 |
| TC-H08d | 維護者 1；H08；決策 5 | 功能 | 一個 lost 的 run | GET `/` | 該 run 帶 lost 專屬 class 與文字「失聯/暫停」 | 自動 |
| TC-H08e | H08；決策 5 | 功能 | 四種狀態的 run 各一 | GET `/` | 四個狀態的 class 兩兩不同（只靠顏色以外也分得出來） | 自動 |
| TC-H08f | H08；決策 5 | 功能 | 一個 run：succeeded 6、cached 2、total 10 | GET `/?run=<id>` | 進度是原生 `<progress>`，value 為 8、max 為 10 | 自動 |
| TC-H08g | H08；決策 5 | 例外 | 一個 run 的 total 為 0 | GET `/?run=<id>` | `<progress>` 沒有 value 屬性（不顯示成 0% 或 100%） | 自動 |
| TC-H10a | H10；決策 2 | 功能 | 選一個 run | 分別用 `?stage=launch`、`running`、`results`、`downstream`、`finished` | 五個都被接受，中欄顯示對應階段 | 自動 |
| TC-H10b | H10；決策 2 | 例外 | 選一個 run，其階段為 results | 用 `?stage=evil`、`?stage=`（空）、`?stage=<script>`、`?stage=RUNNING` | 一律退回該 run 自己的階段（results），回 200，不是 500 | 自動 |
| TC-H10c | H10；裁定 2 | 功能 | 選一個 run，`stage=running` | GET | 箭頭是連結：往前連到 launch、往後連到 results | 自動 |
| TC-H10d | H10；裁定 2 | 功能 | 選一個 run，`stage=launch` | GET | 沒有往前的箭頭（launch 沒有上一階段），有往後的 | 自動 |
| TC-H10e | H10；裁定 2 | 功能 | 選一個 run，`stage=finished` | GET | 沒有往後的箭頭（finished 沒有下一階段），有往前的 | 自動 |
| TC-H14a | H14；決策 2 | 功能 | 已登入 | GET `/` | 回應有 `<meta http-equiv="refresh" content="15">` | 自動 |
| TC-H14b | H14；決策 2 | 功能 | 登入頁、確認頁 `/c/<id>`、404 頁 | 各 GET 一次 | 都沒有 meta refresh（只有 `/` 有） | 自動 |
| TC-H18a | H18 | 例外 | 使用者沒有任何 run | GET `/` | 回 200，有空狀態說明，不是 500 | 自動 |
| TC-H18b | H18 | 例外 | `index.db` 是空檔（0 位元組） | GET `/` | 回 200，有空狀態頁，不是 500 | 自動 |
| TC-H18c | H18 | 例外 | `index.db` 不存在 | GET `/` | 回 200，有空狀態頁，不是 500 | 自動 |
| TC-H19a | H19；決策 6 | 功能 | 使用者有 250 個 run | GET `/` | 左欄只列 100 筆，下面寫「還有 150 筆」 | 自動 |
| TC-H19b | H19；裁定 4 | 功能 | 使用者有 250 個 succeeded 的 run | GET `/` | results 群組標題總數 250，只列 100 筆，下面寫「還有 150 筆」 | 自動 |

## User Story 2 — 右邊最上面是「本月費用」，現在顯示「—」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H09a | 維護者 2；H09 | 功能 | 已登入 | GET `/` | 右欄最上面是「本月費用」，在五個階段群組之前 | 自動 |
| TC-H09b | 維護者 2；H09 | 功能 | 已登入 | GET `/` | 費用分兩行：一行「SU —」、一行「雲端 —」；頁面與程式碼都不出現站名「NCHC」 | 自動 |
| TC-H09c | 維護者 2；H09 | 功能 | 已登入 | GET `/` | 費用區塊裡沒有任何數字、也沒有連結 | 自動 |

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
| TC-H11d | H11 | 功能 | 網頁 app | 列出全部路由 | 正好六條：既有五條加 GET `/` | 自動 |
| TC-H11e | H11 | 功能 | 記下 `index.db`、`platform.db`、`tokens.db`、簽章金鑰的雜湊值 | GET `/`、`/?run=<id>`、`/?stage=running` 各一次 | 所有資料庫檔的雜湊值都沒變（GET 什麼都沒寫） | 自動 |
| TC-H12a | H12 | 例外 | run 名稱含 `<script>alert(1)</script>` 與 `"><b>` | GET `/` | 這些字被轉義，HTML 裡沒有可執行的標籤 | 自動 |
| TC-H12b | H12 | 例外 | `failure_reason` 含 `<img src=x onerror=1>` | GET `/?run=<id>` | 轉義後顯示，沒有真的 `<img>` 標籤 | 自動 |
| TC-H12c | H12 | 例外 | run 的 id 含引號等特殊字元 | GET `/` | 連結裡的 id 放在引號內且已轉義，`href` 不會被截斷 | 自動 |
| TC-H13a | H13；決策 7 | 功能 | 任一頁 | GET `/` | CSP 標頭沒有 `script-src` | 自動 |
| TC-H13b | H13；決策 7 | 功能 | 任一頁 | GET `/` | CSP 標頭沒有 `'unsafe-inline'` | 自動 |
| TC-H13c | H13；決策 7 | 功能 | 已登入 | GET `/` | CSP 的 `style-src` 是 sha256 雜湊，且與該頁內嵌樣式表的雜湊一致 | 自動 |
| TC-H13d | H13；決策 7 | 功能 | 登入頁、確認頁、404 頁 | 各 GET 一次 | 每一頁的 CSP 雜湊都與該頁內嵌樣式表一致（改了 CSP 沒弄壞舊頁面） | 自動 |
| TC-H13e | H13 | 功能 | 已登入，有 run | GET `/`、`/?run=<id>` | HTML 沒有 `<script>` | 自動 |
| TC-H13f | H13；決策 5 | 功能 | 同上 | 同上 | HTML 沒有任何 `style=` 屬性（含 `<progress>`） | 自動 |
| TC-H13g | H13 | 功能 | 同上 | 同上 | HTML 沒有 `onclick=` 之類的 `on*=` 屬性 | 自動 |
| TC-H13h | H13 | 功能 | 同上 | 同上 | HTML 沒有指向外部主機的資源或連結 | 自動 |
| TC-H13i | 決策 7 | 功能 | 任一頁 | GET `/` | CSP 其餘部分不變：`default-src 'none'`、`form-action 'self'`、`frame-ancestors 'none'`、`base-uri 'none'` | 自動 |
| TC-H17 | H17；決策 8 | 功能 | 程式碼靜態檢查（AST，即讀語法樹） | 掃 `web.py`、`web_board.py` 裡每個對 `list_runs`、`get_run` 的呼叫 | 每個呼叫都有 `caller=`，且值不是 None | 自動 |

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
| TC-D01 | 計畫「Pins to rewrite」 | 功能 | `specs/011a-web-shell/ledger.md` | 讀 ledger | 009c 的 TC-G04（五條路由）改為六條，ledger 寫有舊值、新值、理由 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D02 | 同上 | 功能 | 同上 | 讀 ledger | 登入後那頁「已登入…請回到 AI…」的舊斷言改寫，ledger 寫有舊值、新值、理由 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D03 | 同上 | 功能 | 同上 | 讀 ledger | CSP 字串的舊斷言（若有被釘住）改寫，ledger 有舊新理由；若原本沒被釘住，ledger 明寫「沒有」 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D04 | 同上 | 功能 | 同上 | 讀 ledger | `PLATFORM.md` 文字釘子改寫，ledger 有舊新理由 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D05 | 憲法「弱化測試」 | 例外 | 本分支對 v3 的 diff | 逐個比對動到的測試檔 | 除 ledger 列名的幾處外，沒有任何舊斷言被刪掉、放寬、跳過或改成配合新輸出 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D06 | 決策 10 | 功能 | `docs/PLATFORM.md` | 讀第 8、372、424 行附近與 CSP 那一行 | 網頁路由改成六條；不再說「只有登入頁與確認頁」；CSP 描述與新標頭一致 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D07 | 決策 10 | 功能 | `CHANGELOG` | 讀 | 有 011a 的一則紀錄 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D08 | 決策 10 | 功能 | `web.py` 開頭說明文字 | 讀 | 說明已改成包含 GET `/` 的三欄唯讀畫面 | 手動：`docs/TESTING.md`（ledger 檢視） |
| TC-D09 | 裁定 7 | 功能 | `docs/TESTING.md` | 讀 | 有「視覺檢查」與「ledger 檢視」兩組具體步驟，照著做得出來 | 手動：`docs/TESTING.md` |
| TC-V01 | Tier B 視覺檢查；維護者 1 | 功能 | 驗收者在本機迴圈位址啟動 `abf-platform web`，灌入 e2e 假 run | 登入後開 `/`，截圖 | 截圖附在 PR；看得到三欄、左欄 run 清單、右欄「本月費用」與五個群組 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V02 | Tier B 視覺檢查 | 功能 | 同上，有一個 succeeded 的 run | 選該 run，截圖 | 截圖附在 PR；中欄五階段板停在 results，看得到狀態、時間、進度條 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V03 | Tier B 視覺檢查 | 功能 | 同上，有一個 failed 的 run | 選該 run，截圖 | 截圖附在 PR；中欄看得到失敗狀態與失敗原因 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V04 | 維護者 1；裁定 6 | 功能 | V01 的截圖 | 用肉眼看（可轉成黑白） | 四種狀態各有文字與符號（▶ ✓ ✗ ⏸），不靠顏色也分得出來 | 手動：`docs/TESTING.md`（視覺檢查） |
| TC-V05 | 決策 6 | 功能 | 本機頁面 | 把視窗縮到約 900 px 以下，截圖 | 三欄改成上下堆疊，內容沒被切掉 | 手動：`docs/TESTING.md`（視覺檢查） |

## User Story 6 — 這次不做的事（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-N01 | 不做：專案與分析（011b） | 不在範圍 | 已登入 | GET `/` 並列出路由 | 左欄只有「尚未開放」說明；沒有專案或分析的路由、清單、表單（路由仍是六條） | 自動 |
| TC-N02 | 不做：run 詳情、log、失敗一句話、resume／restart（011c、011e） | 不在範圍 | 已登入，有 failed run | GET `/?run=<id>` 與 GET `/runs/<id>`、`/logs`、`/resume`、`/restart` | 頁面沒有 log、resume、restart 的連結或按鈕；那幾個路徑回 404（或 405）；失敗只顯示 `failure_reason` 原文 | 自動 |
| TC-N03 | 不做：費用數字（011d） | 不在範圍 | 灌入有工作數的 run | GET `/` | 兩行費用仍是「—」，頁面任何地方沒有算出來的費用數字 | 自動 |
| TC-N04 | 不做：設定、送出表單、上傳、結果、Studios、聊天（012 至 014、016） | 不在範圍 | 已登入 | 對 `/runs`、`/ce`、`/compute-envs`、`/oauth/token`、`/oauth/authorize`、`/admin`、`/launch`、`/submit`、`/upload`、`/password`、`/passwd`、`/settings`、`/api/launch` GET 與 POST | GET 都 404；POST 都 404 或 405 | 自動 |
| TC-N05 | 不做：`get_board` 或任何新 MCP 工具 | 不在範圍 | MCP 伺服器與 `actions` | 讀 MCP 工具清單與 `actions` 公開名稱 | 與 v3 相比沒有新增工具、沒有新增 action，也沒有 `get_board` | 自動 |
| TC-N06 | 不做：JavaScript、即時推送 | 不在範圍 | 網頁 app | 列出路由與回應 | 沒有 WebSocket 或事件串流（SSE，伺服器持續推資料）路由；更新只靠 15 秒的 meta refresh | 自動 |
| TC-N07 | 不做：所有權程式（#116）與角色（010） | 不在範圍 | 本分支對 v3 的 diff | 看 `actions/`、`jobs.py`、`mcp_server.py` 與 `store.py` 的變動 | 沒有為本功能改所有權判斷，也沒有新增角色或「看全實驗室」的檢視 | 手動：`docs/TESTING.md`（ledger 檢視） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-K1 | 原則 I.2（確認只能由人在指定管道做） | 功能 | 記下 `launches`、`jobs`、待確認申請的筆數 | GET `/` 與 `/?run=<id>` 數次 | 筆數都沒變；網頁讀取不會建立任何申請或工作 | 自動 |
| TC-K2 | 原則 I.2（未確認的送出被拒） | 例外 | 既有的 `test_tch09_*`（`test_human_channel.py`）與 `test_tch09_b_c_*`（`test_confirm_page.py`） | 跑 `tests/platform_test.sh` | 兩組仍全過，內容未被放寬 | 自動 |
| TC-H07a | 原則 I.2（不存第二份 run 狀態）；H07 | 功能 | 本分支的資料庫結構與 `web_board.py` | 檢查資料表欄位與程式 | 沒有儲存「階段」的欄位或檔案；階段每次由狀態算出 | 自動 |
| TC-H07b | 原則 I.2；H07 | 功能 | 本分支 | 跑 `tests/no_second_run_state_test.sh` | 通過 | 自動：`tests/no_second_run_state_test.sh` |
| TC-K5 | 安全網（不得放寬） | 功能 | 本分支對 v3 的 diff | 看 `hooks/`、`.claude/`、deny 規則是否被動到 | 沒有任何 hook 或 deny 被改動 | 手動：`docs/TESTING.md`（ledger 檢視） |
