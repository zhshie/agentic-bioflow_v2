# 測試案例：settings-page 設定頁第一刀（使用前檢查＋運算環境＋憑證，唯讀）

<!--
Written by the verifier (CONTRACT mode). Source: specs/settings-page/plan.md (this task has no spec.md; the plan's 作法, 失敗先行測試, 不能放掉的限制, 不做 and 裁決 are the requirements, and the maintainer's words quoted in the plan are the examples).
-->

**規格**：`specs/settings-page/plan.md`（沒有 spec.md；需求以計畫的「作法」「不能放掉的限制」「不做」「裁決」為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「設定頁」就是網址 `/settings`，只看中欄。「使用前檢查」是設定頁最上面的四項清單。「存取權杖」是同事給 Claude 連平台用的鑰匙（PAT）；頁面上只准顯示它的標籤和時間，絕不顯示鑰匙本身或它的雜湊（雜湊＝鑰匙算出來的指紋，也不准露）。「站台代理」是跑在叢集那一端、替平台做事的小程式，有「在線／離線」兩種狀態。「ann、bob」是兩位各自登入的使用者，bob 看不到 ann 的任何東西，反過來也一樣。「中欄」是頁面中間那一欄。「狀態三件套」指符號＋文字＋樣式（class）三樣都在，不能只靠顏色。

維護者的原話（出自計畫，逐字用在測試裡）：
1. 「**Settings**: compute environments, credentials (token, 12 h), Secrets (AI model key, Jev key optional; browser only), Personal (step-by-step mode, development mode); Operator panel and Roles as dashed "coming later".」→ TC-001、TC-019、TC-034、TC-048、TC-049、TC-056
2. 「**First use / Setup** (`#setup`): numbered disclosure steps: account ✓, access token ✓, compute environment (required: environment, site agent status, cluster account), AI key + Jev key (optional, browser only), create first project.」→ TC-001、TC-002、TC-004、TC-009 到 TC-014、TC-018
3. 「系統設定先。然後右側有對話框，直接對話系統就會引導使用者快速上手建專案，選pipline條參數等等」→ 設定頁本身是第一步（TC-001）；對話框不在這一刀（TC-073）
4. 「不需要Jev "開關"，只要在設定讓使用者可以放金鑰。」→ 沒有任何開關（TC-057）；放金鑰的輸入欄這一刀不做（TC-071）；④ 顯示「之後開放」（TC-014）
5. 「先把功能做起來吧，以後再改美觀」→ 只用既有 class 與 token（TC-060、TC-054）；功能先通（全部功能 TC）

## User Story 1 — 使用前檢查：打開設定頁就知道還缺哪一步（區塊 0，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法「區塊順序固定」；失敗先行 st01；原話 1、2、3 | 功能 | ann 登入 | 開 `/settings`，取中欄所有 h2 | h2 依序恰為「使用前檢查、運算環境、憑證、密碼與金鑰、個人、營運者後台、角色（老師／學生）」；中欄有 `id="setup"` 的 `<section>`，且它是第一個區塊，其 h2 是「使用前檢查」 | 自動：`platform/tests/test_web_settings.py`（st01） |
| TC-002 | 作法區塊 0；原話 2「numbered」 | 功能 | ann 登入 | 看 `#setup` 區塊裡的清單 | 是有序清單 `<ol>`，恰四項，順序為「帳號、存取權杖、運算環境、AI 金鑰」 | 自動 |
| TC-003 | 作法區塊 0 ① | 功能 | ann 登入（任何其他條件） | 看第 ① 項 | 一律「✓ 完成」（符號、文字都在） | 自動 |
| TC-004 | 作法區塊 0；失敗先行 st02；原話 2 | 功能 | ann 登入；ann 沒有任何權杖、沒有任何運算環境 | 開 `/settings` | ① 為「✓ 完成」；② 為「✗ 未完成」；③ 為「✗ 未完成」且說明是「沒有運算環境。」；④ 為「— 之後開放」 | 自動（st02） |
| TC-005 | 作法區塊 0 ② | 功能 | ann 有一把沒被撤銷的權杖 | 開 `/settings` | ② 為「✓ 完成」 | 自動 |
| TC-006 | 作法區塊 0 ② | 例外 | ann 只有一把已撤銷的權杖 | 開 `/settings` | ② 為「✗ 未完成」（已撤銷的不算） | 自動 |
| TC-007 | 作法區塊 0 ②；擁有者規則 | 例外 | ann 沒有權杖；bob 有一把有效權杖 | ann 開 `/settings` | ann 的 ② 為「✗ 未完成」（別人的權杖不算） | 自動 |
| TC-008 | 作法區塊 0 ②；憲法第 7 條 | 功能 | ann 沒有有效權杖 | 看 ② 的說明 | 說明句告訴他在終端機用 `abf-platform` 的指令建立，指令名與 `docs/PLATFORM.md` 一致（`abf-platform token new`），沒有新造的指令名 | 自動 |
| TC-009 | 作法區塊 0 ③；失敗先行 st03；原話 2 | 功能 | ann 有一個環境，是主要環境，status 為可用（available），其 `agent` 欄指到 ann 看得到、狀態為 online 的代理 | 開 `/settings` | ③ 為「✓ 完成」 | 自動（st03） |
| TC-010 | 作法區塊 0 ③；st03 | 例外 | ann 的主要環境 status 不是可用，message 為「某段說明」 | 開 `/settings` | ③ 為「✗ 未完成」，說明恰為「主要運算環境無法使用：某段說明」（後半就是該環境的 message） | 自動 |
| TC-011 | 作法區塊 0 ③；st03；原話 2「site agent status」 | 例外 | ann 的主要環境可用，但其代理狀態為 offline | 開 `/settings` | ③ 為「✗ 未完成」，說明恰為「站台代理離線。」 | 自動 |
| TC-012 | 作法區塊 0 ③ | 例外 | ann 的主要環境可用，但其 `agent` 欄指到的代理不在 ann 的代理清單裡（或該欄沒有代理） | 開 `/settings` | ③ 為「✗ 未完成」，說明是三句制式句裡的「站台代理離線。」（不是 ✓） | 自動 |
| TC-013 | 作法區塊 0 ③；擁有者規則 | 例外 | ann 沒有環境；bob 有一個完全健康的主要環境與在線代理 | ann 開 `/settings` | ann 的 ③ 為「✗ 未完成」，說明「沒有運算環境。」（bob 的環境不算） | 自動 |
| TC-014 | 作法區塊 0 ④；原話 2、4 | 功能 | ann 登入 | 看第 ④ 項 | 為「— 之後開放」，不是 ✓ 也不是 ✗；沒有輸入欄 | 自動 |
| TC-015 | 作法區塊 0「狀態三件套」；專長守則 ui | 功能 | 以上 ✓、✗、— 三種狀態各至少出現一次 | 看每一項的 HTML | 每一項同一個元素裡同時有符號（✓／✗／—）、文字（完成／未完成／之後開放）與狀態樣式 class；不是只靠 class | 自動 |
| TC-016 | 作法區塊 0 英文；st09 | 功能 | 同 TC-004 的資料，網址 `/settings?lang=en` | 看 `#setup` | h2 為「Before you start」；三種狀態文字分別為「Done」「Missing」「Coming later」；符號不變 | 自動（st09） |
| TC-017 | 零 JavaScript 限制 | 例外 | ann 的主要環境不可用，message 內含 `<script>alert(1)</script>` | 開 `/settings` | ③ 的說明把它當純文字顯示（被轉義）；頁面沒有任何 `<script` 標籤 | 自動 |
| TC-018 | 作法「『建立專案』不列」；原話 2「create first project」 | 不在範圍 | ann 登入 | 搜 `#setup` 與整個中欄 | 清單只有 TC-002 的四項；沒有「建立專案」「建立第一個專案」字樣 | 自動 |

## User Story 2 — 運算環境：看見環境、代理、已登記管線（區塊 1，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 作法區塊 1；原話 1「compute environments」 | 功能 | ann 有至少一個環境 | 看「運算環境」h2 下的表格 | 是 `<table>`，欄依序為「名稱、平台、狀態、站台代理、已登記管線、上次使用時間」；一個環境一列 | 自動（st04） |
| TC-020 | 作法區塊 1；st04 | 功能 | ann 有兩個環境，其中一個是主要 | 開 `/settings` | 兩列；只有主要那一列的名稱旁有「主要」標記，另一列沒有 | 自動（st04） |
| TC-021 | 作法區塊 1 狀態；st04 | 功能 | 環境 status 為 `available` | 看狀態欄 | 顯示「✓ 可用」 | 自動 |
| TC-022 | 作法區塊 1、裁決 8 | 例外 | 環境 status 依序為 `compute_envs.py` 實際會出現的每個值（creating、available、invalid、unsupported、disabled） | 看各自狀態欄 | 只有 `available` 顯示 ✓；其餘每個值都照 ledger 的對照表顯示「✗ 無法使用」（後面接該環境的 message）或「— 未檢查」；對照表裡每個值都有一列 | 自動，閱卷者另核對 ledger |
| TC-023 | 裁決 8「未知值不得歸 ✓」 | 例外 | 環境 status 為一個程式沒列到的值（例如 `weird`） | 看狀態欄 | 顯示「— 未檢查」；絕不是 ✓ | 自動 |
| TC-024 | 作法區塊 1 站台代理；原話 2「site agent status」 | 功能 | 一個環境的代理在線、另一個離線，各有最後聯絡時間 | 看站台代理欄 | 在線者為「代理名稱＋在線＋最後聯絡時間」，離線者為「代理名稱＋離線＋最後聯絡時間」，符號與文字都在 | 自動（st04） |
| TC-025 | 作法區塊 1 已登記管線；st04 | 功能 | 環境的 `config.sitePipelines` 有 `pipeline: nf-core/ampliseq`、`revision: 2.18.0` 與另一項 | 看已登記管線欄 | 每個項目各占一行，格式「pipeline revision」，其中一行恰為 `nf-core/ampliseq 2.18.0` | 自動（st04） |
| TC-026 | 作法區塊 1；st04 | 功能 | 環境的 config 沒有 `sitePipelines` 這個鍵 | 看已登記管線欄 | 顯示「—」 | 自動（st04） |
| TC-027 | 作法區塊 1、裁決 7 | 功能 | 一個環境有上次使用時間、另一個沒有；有一個代理沒有最後聯絡時間 | 看「上次使用時間」與代理的最後聯絡時間 | 有值的用頁面既有的時間格式（與其他頁相同）；沒有值的顯示「—」 | 自動 |
| TC-028 | 作法區塊 1 空狀態；st02 | 例外 | ann 沒有任何環境 | 看「運算環境」區 | 顯示制式通知「沒有運算環境。」；沒有資料列 | 自動 |
| TC-029 | 作法區塊 1「表下灰字」 | 功能 | 同 TC-019 | 看表格下方 | 有灰字「新增或修改運算環境 之後開放」；它不是連結、按鈕或輸入 | 自動 |
| TC-030 | 作法區塊 1「只顯示自己的」；st05 | 例外 | bob 有環境與代理（名稱、代理名、管線都有獨特字串）；ann 有自己的 | ann 開 `/settings` | 頁面原文找不到 bob 的環境名、代理名、管線字串；使用前檢查也不受 bob 的資料影響 | 自動（st05） |
| TC-031 | 零 JavaScript 限制；擁有者資料不可變標籤 | 例外 | 環境名稱、message 內含 `<script>` 與 `"><img src=x>` | 開 `/settings` | 全部被轉義成純文字；頁面沒有 `<script`、沒有多出來的標籤 | 自動 |
| TC-032 | 作法區塊 1「狀態三件套」；專長守則 ui | 功能 | 表格裡 ✓ 可用、✗ 無法使用、— 未檢查，代理在線、離線都出現 | 看各格 HTML | 每一格同時有符號、文字與狀態樣式 class；不是只靠 class | 自動 |
| TC-033 | 英文版 | 功能 | 同 TC-032，`?lang=en` | 看區塊 1 | h2 為「Compute environments」；欄名與狀態字都是英文；沒有中日韓字 | 自動（st09） |

## User Story 3 — 憑證：看見自己有幾把存取權杖，絕不露出鑰匙（區塊 2 與新 read，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | 作法區塊 2；原話 1「credentials」 | 功能 | ann 有權杖 | 看「憑證」h2 下的表格 | 是 `<table>`，欄依序為「標籤、建立時間、狀態」；一把權杖一列 | 自動（st06） |
| TC-035 | 作法區塊 2；st06 | 功能 | ann 兩把權杖（一把已撤銷，有撤銷時間），bob 一把 | ann 開 `/settings` | 恰兩列；有效者狀態為「✓ 有效」；已撤銷者為「✗ 已撤銷」並附撤銷時間；建立時間用頁面既有時間格式 | 自動（st06） |
| TC-036 | 作法區塊 2 | 功能 | ann 有一把沒有標籤的權杖 | 看標籤欄 | 顯示「—」 | 自動 |
| TC-037 | 作法區塊 2 空狀態 | 例外 | ann 沒有任何權杖（含權杖檔根本不存在） | 看「憑證」區 | 顯示「沒有存取權杖。」；沒有資料列；頁面正常 200 | 自動 |
| TC-038 | 作法區塊 2「絕不顯示權杖值或雜湊」；st06；專長守則 backend | 例外 | ann 兩把權杖，已知它們的原始值與其 sha256 | 取 `/settings` 與 `/settings?lang=en` 的完整回應原文 | 原文裡找不到任何一把權杖的原始值，也找不到其 sha256（含大小寫與前綴 `abf_` 開頭的字串） | 自動（st06） |
| TC-039 | 擁有者規則；st06 | 例外 | bob 有一把權杖，標籤為獨特字串 | ann 開 `/settings` | 頁面原文找不到 bob 的標籤、建立時間；ann 的列數不含 bob 的 | 自動（st06） |
| TC-040 | 作法區塊 2「灰字」 | 功能 | 同 TC-034 | 看表格下方 | 有灰字「建立或撤銷權杖 之後開放」；它不是連結、按鈕或輸入 | 自動 |
| TC-041 | 新 read `list_my_tokens`；st07 | 功能 | ann 兩把、bob 一把（id 不依序建立） | 以 ann 呼叫 `list_my_tokens(tokens_path, caller=ann)`；再以 bob 呼叫 | ann 的結果是 `{"tokens": [...]}`，恰兩項，只屬於 ann，依 id 排序；每項的欄位恰為 `id、label、created_at、revoked_at` 四個；bob 的結果只有他那一把 | 自動（st07） |
| TC-042 | 新 read「絕不含權杖值、雜湊、別人的權杖」；st07 | 例外 | 同 TC-041，已知原始值與 sha256 | 把回傳整個轉成文字搜尋 | 沒有原始值、沒有雜湊、沒有 `user`／`value`／`hash` 之類欄位、沒有別人的 id 或標籤 | 自動（st07） |
| TC-043 | 新 read；store 行為 | 例外 | 權杖檔不存在 | 呼叫 `list_my_tokens` | 回 `{"tokens": []}`，不丟錯誤 | 自動 |
| TC-044 | 專長守則 backend「對等性」；st07 | 功能 | 動作清單與 MCP 工具清單 | 對等性測試同時列舉兩邊 | `list_my_tokens` 在動作層清單出現；若平行測試要求，MCP 有同名工具且結果與動作層相同；兩邊一一對應，缺一邊測試就失敗；所有釘死的「工具清單／工具數」斷言只多了這一項 | 自動（`test_web_parity.py`、`test_actions_layer.py`、st07） |
| TC-045 | 專長守則 backend「路由裡不得有第二份邏輯」；st11 | 功能 | `web_settings.py`、`web.py` 設定頁處理函式 | 檢查設定頁取資料的路徑 | 權杖資料經動作層 `list_my_tokens` 取得，設定頁模組沒有自己讀 tokens 資料庫；環境與代理經 `list_compute_envs`、`list_agents` | 自動（st11） |
| TC-046 | 專長守則 backend「日誌與回應不含密鑰」 | 例外 | 已知 ann 的權杖原始值與雜湊；擷取應用程式日誌與標準輸出入 | 開 `/settings` 與 `list_my_tokens` | 日誌與輸出都找不到權杖原始值與雜湊 | 自動 |
| TC-047 | 英文版 | 功能 | ann 有權杖，`?lang=en` | 看區塊 2 | h2 為「Credentials」；欄名與狀態字（有效、已撤銷的英文）都是英文；沒有中日韓字 | 自動（st09） |

## User Story 4 — 其餘區塊維持現狀、整頁唯讀、不能放掉的限制（區塊 3 到 6 與限制，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-048 | 作法區塊 3；原話 1「Secrets」；裁決 5 | 功能 | ann 登入 | 看「密碼與金鑰」區 | 仍有「AI 模型金鑰」並標「之後開放」；多一行制式說明「金鑰只存在你的瀏覽器，不會送到平台。」；沒有輸入欄 | 自動 |
| TC-049 | 作法區塊 4 到 6；原話 1「Personal…Operator panel and Roles as dashed "coming later"」 | 功能 | ann 登入 | 看「個人」「營運者後台」「角色（老師／學生）」三區 | 「個人」仍列「逐步模式」「開發模式」；三區都標「之後開放」；沒有表單、輸入或可按的東西 | 自動 |
| TC-050 | 作法「左欄維持 here 標記、右欄維持現狀」 | 功能 | ann 登入 | 開 `/settings` | 左欄「設定」維持 here 標記；左欄、右欄的內容與 base 相同（既有 `test_web_board` 左欄 here 斷言仍過） | 自動 |
| TC-051 | 不能放掉的限制「整頁只有登出一個 form」；st08 | 例外 | ann 登入，頁面上有環境、權杖資料 | 數整頁的 `<form>`，並搜中欄 | 整頁恰一個 form（登出）；中欄沒有 `<form>`、`<input>`、`<select>`、`<textarea>`、`<button>` | 自動（st08） |
| TC-052 | 不做「任何寫入」；st08 | 例外 | ann 登入 | 對 `/settings` 送 POST | 回 405 | 自動（st08） |
| TC-053 | 不做「不改登入」 | 例外 | 沒有登入 | 開 `/settings` | 與 base 相同導向登入頁；回應不含任何環境、權杖資料 | 自動 |
| TC-054 | 限制：零 JS、無 style=、單一樣式表、CSP；st10；原話 5 | 例外 | ann 登入，頁面資料齊全 | 取 `/settings` 與 `?lang=en` | 沒有 `<script`；沒有 `style=`；恰一個 `<style>`；回應標頭的 CSP 雜湊與該樣式表相符 | 自動（st10） |
| TC-055 | 限制：`/settings` 無 refresh | 例外 | ann 登入 | 取 `/settings` 與 `?lang=en` | 沒有 `http-equiv="refresh"`（既有 `test_web_running` 該條仍過） | 自動 |
| TC-056 | 限制：禁字；原話 1「12 h」「Jev」 | 例外 | ann 登入，資料齊全 | 取兩種語言的 `/settings` | 全文（不分大小寫）不含 J＋ev；不含「12 小時」「12 h」「12 hours」；不含「歡迎使用」「第一次使用」「建立第一個專案」 | 自動（st10；既有禁字斷言全數保留） |
| TC-057 | 原話 4「不需要Jev "開關"」 | 例外 | ann 登入 | 搜整頁與「密碼與金鑰」區 | 沒有任何開關、勾選框或第二把金鑰的名稱；頁面沒有 Jev 字樣 | 自動 |
| TC-058 | 不做「不加路由」 | 例外 | 路由集合既有斷言 | 跑 `test_owner_binding`、`test_confirm_page` 的路由集合測試 | 全過，未被改寫；路由表沒有新增項 | 自動 |
| TC-059 | 限制：英文版每個字都有；st09 | 例外 | 頁面資料完整（有環境、有代理、有權杖、有撤銷） | 取 `?lang=en` 的中欄 | 中欄沒有任何中日韓字；狀態字全為英文 | 自動（st09） |
| TC-060 | 裁決 6；原話 5 | 功能 | CSS 的 diff | 閱卷者看 `static/*.css` 相對 base 的變動 | 只新增表格欄寬與換行（`overflow-wrap:anywhere`）、三種狀態符號的樣式；沒有新的顏色或間距數值，只用既有 token | 手動：閱卷者讀 diff；`docs/TESTING.md` 設定頁一節 |
| TC-061 | 裁決 3（平行車道） | 功能 | `web.py`、`web_board.py` 的 diff | 閱卷者看變動行 | `web.py` 只動 `settings` 處理函式內部與一行 import；`web_board.py` 只刪 `SETTINGS`／`_settings_page`／`render_settings` 與其專用字串鍵，或原封不動；ledger 寫明選哪一條 | 手動：閱卷者讀 diff 與 ledger |
| TC-062 | 裁決 4 | 功能 | `test_web_board.py` 的 diff | 閱卷者看被改的斷言 | 只改 `test_tcs39_s40_s41_s42_settings` 的「h2 清單」「之後開放 ≥6」「中欄無 `<a`」三條，ledger 逐條寫「file:line、舊→新＋理由」；「中欄無 form／input／select／textarea／button」與所有禁字斷言沒有被放寬；其他既有斷言沒有被改 | 手動：閱卷者讀 diff 與 ledger |
| TC-063 | 裁決 8 | 功能 | ledger | 閱卷者看狀態對照表 | 對照表列出 `compute_envs.py` 實際出現的每個 status 值與其顯示（✓／✗／—）；未知值歸「— 未檢查」；顯示與 TC-022 的結果一致 | 手動：閱卷者讀 ledger |
| TC-064 | 範圍：`docs/PLATFORM.md` | 功能 | 文件 diff | 閱卷者讀新增段落 | 一段說明設定頁每一區讀什麼資料（使用前檢查、運算環境、憑證各從哪個動作讀），內容與程式一致 | 手動：閱卷者讀文件 |
| TC-065 | 範圍：`docs/TESTING.md` | 功能 | 文件 diff | 閱卷者讀新增一節 | 有「設定頁（settings-page）」一節，手動步驟含：390 px 無橫捲、Tab 焦點外框、中英各看一次 | 手動：閱卷者讀文件 |
| TC-066 | 專長守則 ui「手機寬度可用」 | 功能 | 390 px 寬的視窗 | 開 `/settings`，兩種語言 | 沒有橫向捲動；表格內容會換行，不被截掉 | 手動：`docs/TESTING.md` 設定頁一節 |
| TC-067 | 專長守則 ui「鍵盤焦點外框可見」 | 功能 | 桌面瀏覽器 | 在設定頁按 Tab 逐個走 | 每個可聚焦的東西都有看得見的焦點外框 | 手動：`docs/TESTING.md` 設定頁一節 |
| TC-068 | 專長守則 ui；制式句不口語 | 功能 | 中文與英文各開一次 | 讀完整頁文字 | 句子是制式句，說明發生什麼事；沒有內部術語、錯誤代碼或程式名詞 | 手動：`docs/TESTING.md` 設定頁一節 |
| TC-069 | 專長守則 backend；st11 | 功能 | `web_settings.py` 與 `test_web_actions.py` 的 tc060 | 跑 tc060 | tc060 的檢查清單已加入 `web_settings.py`（只會變嚴）；`web_settings.py` 不 import confirm／jobs／compute_envs／agents／status，也不呼叫任何寫入動作 | 自動（st11、tc060） |
| TC-070 | 完成標準 | 功能 | 實作完成 | 在 WSL 跑全套 `tests/run_all.sh` | 全綠；唯一可接受的紅是已知環境題 `init_workspace_test.sh`「site side with no run area known fails clearly」，且 base 上也紅（裁決 1）；新測試檔 `test_web_settings.py` 全過 | 自動：`tests/run_all.sh` |
| TC-071 | 不做；裁決 5；原話 4「讓使用者可以放金鑰」 | 不在範圍 | ann 登入 | 看「密碼與金鑰」區與整頁 | 沒有任何放 AI 金鑰的輸入欄，也沒有儲存按鈕；「AI 模型金鑰」只標「之後開放」，並說明金鑰只存在瀏覽器 | 自動 |
| TC-072 | 不做「任何寫入」 | 不在範圍 | 記下環境表與權杖表的內容 | 對 `/settings` 做 GET、POST；試圖用網頁新增環境、建立或撤銷權杖、切換個人模式 | 沒有任何這些操作的入口；POST 被擋；環境表與權杖表前後完全相同 | 自動 |
| TC-073 | 不做「不改右欄」；原話 3「右側有對話框」 | 不在範圍 | ann 登入 | 比較 `/settings` 的右欄與 base | 右欄與 base 完全相同，沒有新增對話或引導 | 自動 |
| TC-074 | 不做「不加資料表或欄位」 | 不在範圍 | 資料庫結構 | 比較 base 與本分支的資料表與欄位 | 沒有新增資料表或欄位，沒有 migration；ledger 或 PLATFORM 文件寫明「不需要 migration」 | 自動 |
| TC-075 | 環境事實「平台程式不連網」 | 不在範圍 | ann 登入 | 搜設定頁 HTML 的外部網址，並看 `web_settings.py` 的 import | 沒有 `src`／`href`／`action` 指到外部 `http(s)://`；模組沒有 import 任何網路函式庫 | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-076 | 安全網「平台的每個寫入工具要人確認」 | 功能 | `test_actions_layer.py` 的寫入工具清單（launch、cancel、resume、relaunch、forget） | 跑 `test_tcb04_*` 到 `test_tcb08_*` | 全過；寫入工具清單沒有變；新增的 `list_my_tokens` 是讀取，不在寫入工具之列 | 自動：`platform/tests/test_actions_layer.py` |
| TC-077 | 安全網「憑證不得被印出」 | 例外 | 已知權杖原始值與雜湊、環境 message | 取 `/settings`（中、英）與 `list_my_tokens` 回傳，並看錯誤情形的回應 | 任何輸出都不含權杖原始值與雜湊，錯誤頁也不露內部路徑或堆疊 | 自動（st06、st07） |
| TC-078 | 安全網「平台不另存收到的憑證」 | 例外 | 資料夾前後快照 | 開 `/settings` 多次 | 資料夾與資料庫沒有新增檔案、沒有新寫入（唯讀頁） | 自動 |
| TC-079 | 憲法第 7 條「每一步說明要做什麼，不需要找維護者」 | 功能 | 使用前檢查有 ✗ 的項目 | 看每個 ✗ 項的說明 | 每個 ✗ 項都有一句說明缺什麼或下一步做什麼（② 指令、③ 三選一制式句），不是只有 ✗ | 自動 |
