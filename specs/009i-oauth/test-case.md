# 測試案例：009i 最小 OAuth——讓 Claude Desktop 自訂連接器連上 HTTP MCP 伺服器（#117）

**規格**：無 `spec.md`（依慣例以 `specs/009i-oauth/plan.md` 為準；plan 的「給維護者」三句是他看得懂的承諾）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、有人想繞過時，系統怎麼反應（拒絕、停下、狀態不變）。
- **不在範圍**：計畫「Not in this PR」明講這次不做的事；測試確認它真的沒做。

維護者的話（plan「給維護者」，逐字）：

> 「Claude Desktop 的「自訂連接器」可以用網頁登入連平台：跳出瀏覽器頁面，你用名字＋網頁密碼登入、按「允許」，之後它以你的身分連線，不必貼權杖。」
> 「允許連接器不等於同意送出分析；每次送出、取消仍要你本人按「送出」。授權頁只收網頁密碼，絕不收權杖。」
> 「Claude Desktop 從雲端連進來，要等平台有公開 https 網址（009h）才能端到端實測；在那之前用本機測試代替。」

我把這三句拆成七個要求，每個都對到下面的 TC：

- E1 用名字＋網頁密碼在瀏覽器登入、按「允許」：TC-C03、TC-C05、TC-C06、TC-C14。
- E2 之後它以我的身分連線：TC-D01、TC-E01、TC-E02。
- E3 不必貼權杖：TC-A01、TC-A02、TC-A03、TC-B01、TC-D01（自動發現、自動註冊、自動換權杖）。
- E4 允許連接器不等於同意送出，每次仍要我本人按「送出」：TC-F01 至 TC-F09、TC-C05（授權頁上的說明）。
- E5 授權頁只收網頁密碼，絕不收權杖：TC-C04、TC-D11、TC-E11。
- E6 公開 https 網址之前用本機測試代替：TC-A07、TC-I06、TC-H01。
- E7 PAT 繼續照舊能用：TC-E03、TC-D14。

名詞：
- **OAuth**＝讓一個程式（這裡是 Claude Desktop 的連接器）在你登入並按「允許」之後，拿到一把短效的鑰匙去代你連線的標準流程。
- **連接器（connector）／客戶端（client）**＝要連進平台的那個程式。**動態註冊（DCR）**＝它第一次來時自己向平台登記一個身分。
- **授權碼（code）**＝按「允許」後給連接器的一次性短碼，再拿去換權杖。**PKCE**＝換權杖時要出示的暗號，只有發起授權的那一方有，別人偷到授權碼也換不了。
- **access token／refresh token**＝OAuth 的存取權杖（1 小時）／更新權杖（30 天，用過就換新）。
- **PAT**＝009d 的個人存取權杖。**CSRF 記號**＝網頁表單裡的一次性暗號，防別的網站偷偷代你按按鈕。
- **canary 掃描**＝先造一個已知的假值，再把整個資料目錄逐位元組找這個值，找到就算洩漏。
- **ELICITED／PAGE／TERMINAL**＝記錄「是誰（哪種通道）按下確認」的三個固定標記。
- **pending**＝已準備好摘要但還沒有人按「送出」的申請，不算確認、不會排進任何工作。
- 「前後一樣」的基準＝計畫起點 `v3`（含 009c）的行為。
- #116（擁有者綁定）可能已合併也可能還沒。凡是「看得到什麼資料」的 TC，一律寫成「OAuth token 與同一人的 PAT 看到的完全一樣」，所以有沒有 #116 都成立。

## User Story 1 — 平台把自己公開成可被自動發現的 OAuth 資源與授權伺服器（優先度 P1）

維護者原話：「不必貼權杖」。連接器只知道 `/mcp` 的網址，其餘要靠 401 挑戰與兩份 metadata 找到。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-A01 | E3；設計 3：「MCP process serves the resource metadata」 | 功能 | 以 `mcp --http --public-url https://mcp.example` 啟動；網頁服務已設自己的 `--public-url` | 不帶任何 `Authorization`，GET 401 挑戰裡 `resource_metadata` 所指的網址 | 200 JSON；`resource` 是 MCP 的公開網址；`authorization_servers` 含網頁服務的公開網址（MCP 行程以何種方式得知不限）；沒有任何祕密或使用者資料 | 自動：`platform/tests/test_oauth.py` |
| TC-A02 | E3；設計 3、Tests「The 401 carries resource_metadata」 | 功能 | 同上 | 不帶權杖 POST `/mcp` | 401；`WWW-Authenticate` 為 `Bearer resource_metadata="<TC-A01 那個網址>"`；body 不回顯任何收到的東西 | 自動 |
| TC-A03 | E3；設計 2、3、Tests「authorization-server metadata with S256 only」 | 功能 | 網頁服務以 `--public-url` 啟動 | GET 授權伺服器 metadata（`/.well-known/oauth-authorization-server`） | 200 JSON；`issuer` 是該公開網址；`authorization_endpoint`、`token_endpoint`、`registration_endpoint`、`revocation_endpoint` 都在其下；`code_challenge_methods_supported` 剛好是 `["S256"]`；`response_types_supported` 只有 `code`；`grant_types_supported` 只有 `authorization_code`、`refresh_token` | 自動 |
| TC-A04 | 設計 3：「BearerAuth lets exactly that GET through」 | 例外 | MCP 行程，不帶權杖 | 對其他所有路徑與方法（`/mcp` 的 GET／POST／DELETE、`/`、`/authorize`、`/token`、`/register`、`/revoke`、`/.well-known/oauth-authorization-server`、`/.well-known/` 底下其他名稱）發請求；另對 TC-A01 的網址做 POST、PUT、DELETE | 全部 401（或 404/405，但絕不是 2xx）；唯一不帶權杖得到 200 的是 TC-A01 那個 GET；MCP 行程不提供任何授權伺服器路由 | 自動 |
| TC-A05 | 設計 3（`--public-url` 之外的行為，計畫未明寫，見總覽疑問 1） | 例外 | `mcp --http` 沒給 `--public-url` | 不帶權杖與帶錯權杖 POST `/mcp` | 仍是 401、方案為 `Bearer`、body 不回顯收到的東西；PAT 仍可用 | 自動 |
| TC-A06 | 設計 3：「The receiver is untouched」；Unchanged pins | 例外 | 接收器與平台（`serve`）行程 | GET／POST `/.well-known/*`、`/authorize`、`/token`、`/register`、`/revoke`、`/oauth/*` | 全部 404（或 401），沒有任何 OAuth 路由；接收器 `ROUTES_V3` 與 `v3` 逐項相同 | 自動：`test_oauth.py`；`test_receiver.py`、`test_station_envs.py` 不改仍通過 |
| TC-A07 | E6；設計 3：「issuer requires https except on loopback」 | 例外 | `abf-platform web --public-url http://abf.example`（非 loopback 的 http） | 啟動 | 被拒絕並說明要 https（009c 既有行為不退步）；而 `--public-url http://127.0.0.1:PORT` 或不給時，授權伺服器 metadata 以 loopback 位址為 issuer 並可用，供本機測試 | 自動 |

## User Story 2 — 動態註冊：連接器自己登記，但登記本身什麼都不給（優先度 P1）

維護者原話：「不必貼權杖」。設計 7：「it grants nothing without a login plus consent」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-B01 | E3；設計 7 | 功能 | 授權伺服器在跑 | POST `/register`，redirect 為 `https://claude.example/cb`，公開客戶端（`token_endpoint_auth_method=none`） | 成功；回 `client_id`；`oauth_clients` 多一列；不需要 client secret；PKCE 客戶端被接受 | 自動 |
| TC-B02 | 設計 7：「https, or loopback」 | 功能 | 同上 | 註冊 redirect 為 `http://127.0.0.1:8765/cb`、`http://localhost:1/cb`、`http://[::1]:9/cb` | 三種都成功（本機測試用） | 自動 |
| TC-B03 | 設計 7、Tests「Registration refuses a redirect that is neither https nor loopback」 | 例外 | 同上 | 註冊 `http://evil.example/cb`、`javascript:alert(1)`、`file:///x`、`ftp://h/x`、沒有 scheme 的字串；另一次在多個 redirect 中夾一個壞的 | 每種都被拒；`oauth_clients` 沒有新增列；夾壞的那次整筆被拒，不是只收好的 | 自動 |
| TC-B04 | 設計 7：「at most 200 clients」；Tests「refuses once the cap is reached」 | 例外 | 已有 200 個客戶端 | 再註冊第 201 個 | 被拒；前 200 個不受影響；仍可為既有客戶端走完授權 | 自動 |
| TC-B05 | 設計 7：「a rate cap per address」 | 例外 | 同一位址在短時間內連續註冊（超過程式裡的上限常數；該常數寫進 `docs/PLATFORM.md`，見總覽疑問 6） | 持續送 | 超過上限後被拒（如 429）；來自另一個位址的註冊不受影響；上限在達到 200 個客戶端之前就會擋下 | 自動 |
| TC-B06 | 設計 7：「unused clients expire after 30 days」 | 功能 | 時鐘可控；客戶端 X 註冊後 30 天又 1 秒沒被用過；客戶端 Y 在第 29 天曾走過授權 | 用 X、Y 各發一次 `/authorize` | X 視為不存在（`invalid_client` 類錯誤）且那一列已清掉，名額釋出；Y 仍可用 | 自動 |
| TC-B07 | 設計 7：「grants nothing」；設計 8 | 例外 | 剛註冊完一個客戶端，沒有人登入過 | 檢查：該 `client_id` 能否換出任何權杖、MCP 是否仍 401、`oauth_codes`／`tokens`／`users`／`confirmations`／`jobs` | 都沒變；沒有碼、沒有權杖、沒有使用者、沒有確認、沒有工作 | 自動 |
| TC-B08 | 設計 7；SDK 的 metadata 只宣告兩種授權 | 例外 | 註冊時宣告 `grant_types` 為 `implicit`、`client_credentials`、`password`，或 `response_types=token` | 註冊與之後在 `/token` 用這些授權方式 | 註冊被拒（或被忽略成只有 authorization_code／refresh_token）；`/token` 對這些 grant_type 一律回 `unsupported_grant_type` 類錯誤；沒有權杖 | 自動 |

## User Story 3 — 授權與同意：只有用網頁密碼登入的本人按「允許」才發碼（優先度 P1）

維護者原話：「你用名字＋網頁密碼登入、按「允許」」；「授權頁只收網頁密碼，絕不收權杖」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | E1；設計 5：「authorize() stores the request and redirects to the consent page」 | 功能 | 已註冊的客戶端；合法參數（`response_type=code`、S256 的 `code_challenge`、已註冊的 `redirect_uri`、`state`） | GET `/authorize` | 302 導向網頁服務上的同意頁；`oauth_requests` 多一列（10 分鐘）；此時沒有碼、沒有權杖 | 自動 |
| TC-C02 | 設計 5；SDK 驗證 | 例外 | 同上 | `/authorize` 帶：不認得的 `client_id`；與註冊不完全相同的 `redirect_uri`（多一個路徑字元、換 host、換 scheme）；缺 `code_challenge`；`code_challenge_method=plain`；`response_type=token` | 全部被拒；`client_id` 或 `redirect_uri` 有問題時不導向那個 `redirect_uri`（顯示錯誤頁，避免被當成開放轉址）；沒有 `oauth_requests` 列、沒有碼 | 自動 |
| TC-C03 | E1、E5；設計 5：「needs the 009c login」 | 例外 | 沒有登入；有一筆同意申請 | 打開同意頁 | 看到的是登入表單（名字＋網頁密碼），沒有「允許」按鈕；沒有碼；登入成功後回到同一個同意頁 | 自動 |
| TC-C04 | E5：「授權頁只收網頁密碼，絕不收權杖」；設計 5、8 | 例外 | 使用者 `ann` 有 PAT 與有效的 OAuth access token，但沒登入網頁 | 在同意頁與登入頁：帶 `Authorization: Bearer <PAT>`、帶 `Bearer <OAuth access token>`、把 PAT 填成密碼、把 OAuth 權杖填成密碼，各試一次，包括直接 POST「允許」 | 每種都沒登入、沒有 cookie、沒有 `web_sessions` 列、沒有碼；頁面仍要求登入 | 自動 |
| TC-C05 | E1、E4；設計 5：「The page shows the connector name, the redirect host…」 | 功能 | `ann` 已登入；客戶端名稱 `Claude <b>Desktop</b>&`，redirect 為 `https://claude.example/cb` | 打開同意頁 | 顯示連接器名稱（HTML 被轉義成文字）、redirect 的主機 `claude.example`、一句白話說明「可以讀你的 runs、可以請求送出；不能送出分析，每次仍要你按送出」，以及「允許」「拒絕」兩個按鈕；沒有任何輸入權杖的欄位 | 自動；字句是否看得懂見「需要人看」 |
| TC-C06 | E1、E2；設計 5：「Allow mints the code」 | 功能 | `ann` 已登入，同意頁開著 | 按「允許」（帶正確 CSRF） | 302 導向註冊的 `redirect_uri`，帶 `code` 與原本的 `state`；`oauth_codes` 多一列：只存雜湊，綁定該客戶端、該 redirect、該 PKCE challenge、使用者 `ann`，5 分鐘到期、單次 | 自動 |
| TC-C07 | 設計 5：「Deny redirects with access_denied」；Tests | 例外 | 同上 | 按「拒絕」 | 302 導向註冊的 `redirect_uri`，帶 `error=access_denied` 與原 `state`；沒有 `oauth_codes` 列、沒有權杖；該申請之後不能再按「允許」 | 自動 |
| TC-C08 | 設計 5：「POST needs CSRF」；Tests | 例外 | `ann` 已登入；有兩筆同意申請 | 按「允許」但：不帶 CSRF；帶錯記號；拿申請 1 的記號 POST 申請 2；拿別人 session 的記號 | 全部被拒；沒有碼；申請仍是待決，本人用正確記號仍可按 | 自動 |
| TC-C09 | 設計 5：「GET never changes anything」；Tests「a GET that would mint a code」 | 例外 | `ann` 已登入 | 多次 GET `/authorize` 與同意頁，包含帶 `?allow=1`、`?approve=true`、`?code=…` 之類查詢參數 | `oauth_codes`、`tokens`、`oauth_requests`（除第一次建立外）逐表比對沒有任何變化；沒有碼 | 自動 |
| TC-C10 | 沿用 009c 的同源檢查 | 例外 | `ann` 已登入，正確 CSRF 記號 | 按「允許」但 `Origin` 是 `https://evil.example` | 被拒（403）；沒有碼 | 自動 |
| TC-C11 | 設計 5（一個申請只能決定一次） | 例外 | 一筆申請已被「允許」過一次 | 再按一次「允許」；另一情境：已「拒絕」後再按「允許」；另一情境：兩個執行緒同時按「允許」 | 第二次被拒、沒有第二個碼；拒絕後不能允許；同時按剛好 1 個碼 | 自動 |
| TC-C12 | 設計 4：申請 10 分鐘 | 例外 | 時鐘撥到申請建立後 10 分鐘又 1 秒 | 本人 GET 同意頁與 POST「允許」 | 頁面說已逾時；POST 被拒；沒有碼 | 自動 |
| TC-C13 | 設計 6：停用的使用者；009d 語意 | 例外 | `ann` 被停用；另一情境：`ann` 登入後、按「允許」前被停用 | 登入；按「允許」 | 登入被拒；已有的 cookie 也不能按「允許」；沒有碼 | 自動 |
| TC-C14 | E1、E2；設計 5、6：身分＝登入的人 | 功能 | `ann` 與 `bob` 各有網頁密碼；同一筆申請 | `bob` 登入並按「允許」，完成換權杖 | 碼與之後的權杖屬於 `bob`（`user_id`＝bob），不是 `ann`；MCP 以 `bob` 身分看到資料 | 自動 |
| TC-C15 | 沿用 009c 的 404 規則 | 例外 | 隨機編造的申請 id | GET／POST 同意頁 | 404，不透露任何申請是否存在 | 自動 |
| TC-C16 | 設計 5、8：碼綁的是儲存的申請，不是 POST 的內容 | 例外 | `ann` 已登入 | 按「允許」時多帶 `client_id`、`redirect_uri`、`user_id`、`code_challenge`、`scope` 等欄位 | 額外欄位被忽略；碼綁的仍是 `oauth_requests` 裡存的值 | 自動 |
| TC-C17 | 沿用 009c 登入限制（每分鐘 5 次） | 例外 | `ann` 已設密碼；時鐘可控 | 經由同意頁的登入表單，60 秒內用錯密碼 5 次，再用正確密碼第 6 次 | 第 6 次也被拒；沒有 cookie；沒有碼 | 自動 |

## User Story 4 — 換權杖：授權碼與更新權杖都只能用一次、只給對的人（優先度 P1）

維護者原話：「之後它以你的身分連線，不必貼權杖」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-D01 | E2、E3；設計 4、6 | 功能 | `ann` 剛按了「允許」，拿到碼 | `/token`：`grant_type=authorization_code`、碼、正確 `code_verifier`、同一客戶端、同一 `redirect_uri` | 200；`access_token`（`expires_in` 3600）與 `refresh_token`；`tokens` 多兩列：`kind` 為 `oauth_access`／`oauth_refresh`，`user_id`＝ann，`label`＝client_id，`expires_at` 分別為 1 小時／30 天後，只存雜湊 | 自動 |
| TC-D02 | 設計 Tests「a wrong PKCE verifier」 | 例外 | 同 TC-D01 | 用錯的 `code_verifier`；另一次不帶 | 被拒（`invalid_grant`）；沒有權杖 | 自動 |
| TC-D03 | Tests「a reused code」 | 例外 | 碼已換過一次 | 同一個碼再換一次（verifier 正確） | 被拒；沒有新權杖（第一次發出的權杖是否一併作廢，見總覽疑問 2，此處不斷言） | 自動 |
| TC-D04 | Tests「a code presented by another client」 | 例外 | 客戶端 X 取得的碼；客戶端 Y 也已註冊 | Y 帶著 X 的碼與正確 verifier | 被拒；沒有權杖；X 之後仍可（不被連累地）換 | 自動 |
| TC-D05 | Tests「or with another redirect」 | 例外 | 同 TC-D01 | 換權杖時 `redirect_uri` 與授權時不同（即使也是該客戶端註冊過的另一個） | 被拒；沒有權杖 | 自動 |
| TC-D06 | Tests「an expired code」；設計 4：5 分鐘 | 例外 | 時鐘撥到碼建立後 5 分鐘又 1 秒 | 用正確參數換 | 被拒；沒有權杖 | 自動 |
| TC-D07 | 設計 6：「The refresh token… rotates」 | 功能 | 已有一組權杖 | 用 `refresh_token` 換 | 200；新的 access 與新的 refresh；舊的 refresh 立即失效；新 refresh 的到期重新算 30 天 | 自動 |
| TC-D08 | Tests「a replayed refresh token」 | 例外 | 一個 refresh 已被換過 | 再用舊的 refresh 換 | 被拒；沒有新權杖 | 自動 |
| TC-D09 | 設計 6 | 例外 | 另一客戶端、已過 30 天、已被撤銷的 refresh 各一個 | 各換一次 | 全部被拒；沒有權杖 | 自動 |
| TC-D10 | 設計 6：「A disabled user fails」，延伸到 refresh（見總覽疑問 4） | 例外 | `ann` 有有效 refresh；之後 `ann` 被停用 | 用 refresh 換 | 被拒；沒有新權杖 | 自動 |
| TC-D11 | E5：「絕不收權杖」；Tests「A web password is never accepted at /token」 | 例外 | `ann` 有網頁密碼與 PAT | `/token` 帶：`grant_type=password` 加網頁密碼；網頁密碼當 `client_secret` 或當 `code`；PAT 當 `code` 或 `refresh_token`；`client_credentials` | 全部被拒；沒有權杖 | 自動 |
| TC-D12 | 設計 6：「can be revoked」 | 功能 | 一組有效權杖 | POST `/revoke` 撤銷 access；另一組撤銷 refresh | 被撤銷的那個立即失效：access 在 MCP 回 401，refresh 不能再換；撤銷未知的值不報任何可探測的差異（回應與成功相同） | 自動 |
| TC-D13 | 設計 6 | 例外 | 客戶端 Y 嘗試撤銷客戶端 X 的權杖 | POST `/revoke` | X 的權杖仍有效 | 自動 |
| TC-D14 | 設計 4：既有 `tokens` 表重用，不影響 PAT 管理 | 功能 | `ann` 有 PAT 也有 OAuth 權杖 | `abf-platform pat list`、`pat revoke <OAuth 權杖列的 id>` | `pat list` 只列 PAT，不列 OAuth 權杖；用 OAuth 權杖列的 id 去 `pat revoke` 回 0 筆、OAuth 權杖仍有效（`store.py:601`、`613` 的 `kind='pat'` 限制仍在） | 自動 |

## User Story 5 — 用 OAuth 權杖連 MCP：身分和 PAT 一模一樣，其餘門仍關（優先度 P1）

維護者原話：「之後它以你的身分連線」。設計 6：「`BearerAuth` tries the PAT first, then `oauth_access`. Both give the same Caller」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-E01 | E2；設計 6 | 功能 | `ann` 的 OAuth access token | 用它對 HTTP MCP 開 session、列工具、呼叫 `list_runs` | 成功；呼叫者是 `ann`（`user_id`、name、lab 與用 `ann` 的 PAT 時相同）；`launch` 建立的 pending 的 `caller_user_id`＝ann | 自動 |
| TC-E02 | 設計 6：「the same Caller, so the owner filters apply unchanged」；Tests「see the same data」 | 功能 | `ann` 同時有 PAT 與 OAuth 權杖；`bob` 也有 PAT；資料庫裡有 ann 與 bob 各自發起的 runs | 兩種權杖各呼叫 `list_runs`、`get_run`、`list_agents`；`bob` 的 PAT 也呼叫 | `ann` 的兩種權杖看到的結果逐項相同；OAuth 權杖沒有比 `ann` 的 PAT 多看到、少看到任何東西。有 #116 時兩者都受擁有者過濾，沒有時都看到全部，本 TC 都成立 | 自動 |
| TC-E03 | E7；設計 6：「PAT first」；Tests「A PAT keeps working unchanged」 | 功能 | 只有 PAT、沒有任何 OAuth 設定 | 跑 `test_pat.py` 中未被改寫的案例 | 全部通過；PAT 行為不變，包含撤銷後立即 401、停用使用者 401 | 自動：`test_pat.py` |
| TC-E04 | 設計 6：1 小時；Tests「expired token gets 401」 | 例外 | 時鐘撥到 access 發出後 1 小時又 1 秒 | 用它呼叫 MCP | 401（挑戰帶 `resource_metadata`）；用 refresh 換新的 access 後恢復 | 自動 |
| TC-E05 | 設計 6：「`abf-platform oauth revoke USER` revokes」 | 功能 | `ann` 有 OAuth access＋refresh，且有 PAT；`bob` 也有 OAuth 權杖 | `abf-platform oauth revoke ann`（不重啟服務） | `ann` 的 access 與 refresh 立即失效；`bob` 的 OAuth 權杖不受影響；`ann` 的 PAT 不受影響（此指令只管 OAuth，見總覽疑問 3）；輸出不含任何權杖值 | 自動 |
| TC-E06 | 設計 6：「A disabled user… gets 401」；Tests | 例外 | `ann` 有效的 OAuth access；之後 `ann` 被停用 | 用該 access 呼叫 MCP（不重啟） | 立即 401 | 自動 |
| TC-E07 | 設計 6：「Run and agent tokens still get 401 on MCP」 | 例外 | 一個 run token、一個 agent token、一個 OAuth refresh token（不是 access）、一個已撤銷的 OAuth access | 各自當 Bearer 呼叫 MCP | 全部 401（refresh 權杖不能當存取權杖用） | 自動：`test_pat.py` 的 tcc03／c04 不改仍通過，另加 OAuth 類別 |
| TC-E08 | 設計 3：「The receiver is untouched」 | 例外 | `ann` 的 OAuth access 與 refresh | 當 Bearer 打接收器與代理的所有端點 | 全部 401（`receiver.py:43`、`agents.py:107` 只收 `run`／`agent`）；沒有任何狀態改變 | 自動 |
| TC-E09 | 沿用 009d 的 session 綁定 | 例外 | `ann` 用 OAuth 權杖開了 MCP session | `bob` 的權杖（PAT 或 OAuth）帶同一個 `Mcp-Session-Id` | 403；`ann` 自己的 PAT 或 OAuth 權杖帶該 session 則可（同一個人） | 自動 |
| TC-E10 | 設計 Tests「the header text」；沿用 tcb01–b07 | 例外 | 各種壞的 `Authorization`（缺、空、`Basic`、`Bearer` 後面空白、亂字串、被撤銷的 OAuth 權杖） | POST `/mcp` | 全部 401，`WWW-Authenticate` 方案為 `Bearer`；body 絕不回顯收到的東西；狀態不變 | 自動：`test_pat.py` tcb01–b07（只改標頭文字斷言） |
| TC-E11 | E5：「絕不收權杖」的另一半；Tests「A web password is never accepted… on MCP」 | 例外 | `ann` 有網頁密碼與網頁 cookie | 把網頁密碼當 Bearer、把 cookie 值當 Bearer、帶 cookie 但不帶 Bearer，呼叫 MCP | 全部 401 | 自動 |

## User Story 6 — 閘門不變：OAuth 只證明「是誰」，不代表「同意送出」（優先度 P1）

維護者原話：「允許連接器不等於同意送出分析；每次送出、取消仍要你本人按「送出」」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-F01 | E4；設計 8；Tests「A launch over an OAuth token queues no job until a person says yes」 | 例外 | `ann` 的 OAuth access；客戶端不支援表單；佇列 0 個工作 | MCP `launch`、`cancel` | 只建立 pending 申請並回一次性確認網址；`jobs` 仍是 0；`confirmations` 為 `state=pending` | 自動 |
| TC-F02 | E4；設計 8：「Consent writes no confirmations row」 | 例外 | 空的資料庫 | 走完整個流程：註冊、授權、登入、按「允許」、換權杖、用權杖連 MCP 讀資料 | `confirmations` 逐列比對沒有任何變化；`jobs` 為 0；按「允許」本身沒有留下任何 `ELICITED`／`PAGE`／`TERMINAL` 紀錄 | 自動 |
| TC-F03 | E4；設計 8：「`/c/<id>` with either kind of Bearer gives the login form」 | 例外 | `ann` 有 pending 申請與 OAuth 權杖（也有 PAT） | 用 OAuth access、OAuth refresh、PAT 當 Bearer，對 `/c/<id>` 做 GET 與 POST（含自造或不帶 CSRF） | 都只看到登入表單或被拒；沒有登入、沒有確認、沒有工作；申請仍 pending | 自動 |
| TC-F04 | E4；設計 8；沿用 009c TC-C01 至 C07 | 功能 | 客戶端宣告支援表單詢問，以 OAuth 權杖連線 | `launch`；表單回 `accept` 且 `送出=true`；另一次表單回 `decline`／`送出=false` | 前者剛好 1 個 `launch_nextflow` 工作、通道 `ELICITED`、`caller_user_id`＝ann；後者沒有工作；行為與 PAT 呼叫時一致；模型自己塞的 `confirmed=true` 之類參數仍無效 | 自動 |
| TC-F05 | E4；設計 8 | 功能 | `ann` 透過 OAuth 權杖建立了 pending；`ann` 用網頁密碼登入 | 打開 `/c/<id>`、按「送出」 | 剛好 1 個工作、通道 `PAGE`；`bob`（也有 OAuth 權杖與網頁密碼）打開同一網址看到「不是你的申請」、不能送 | 自動 |
| TC-F06 | 設計 8；同意流程與確認流程互不相通 | 例外 | 一筆 OAuth 同意申請 id 與一筆確認 pending id | 把同意申請 id 拿去打 `/c/<id>`；把確認 id 拿去打同意頁；用同意頁的 CSRF 記號按確認 | 全部 404 或被拒；沒有碼、沒有工作 | 自動 |
| TC-F07 | 設計 8：「launch/cancel only make a pending request」 | 功能 | 列出 MCP 工具 | 取得工具清單與 `launch`、`cancel` 的參數 | 與 `v3` 相同：8 個工具；沒有任何 approve／confirm／oauth／login 名稱的工具；參數沒有表示「已同意」的欄位 | 自動：`test_mcp.py` 不改仍通過 |
| TC-F08 | E4；009c TC-H09 的 OAuth 版 | 例外 | 只有 pending 申請，沒有人確認 | 用 OAuth 權杖、OAuth refresh、PAT、偽造 cookie、錯 CSRF，對 MCP 與網頁服務所有路由與方法組合發請求 | 每一種都沒有工作；佇列恆為 0 | 自動：沿用 009c 的 H09 矩陣並加入 OAuth 權杖 |
| TC-F09 | 設計 8：「`_require_human`, the three singletons, `confirm.py` and the jobs checks are untouched」 | 功能 | 對 `v3` 比較 `abf_platform/actions/`、`confirm.py`、`jobs.py` 的 `_check_confirmation`、`abf_station/launch.py` | 讀 diff | 閘門相關程式完全沒改（若有改，必須只是讓檢查更嚴，並在 ledger 說明）；沒有新增任何可傳入 `confirmed_by` 的呼叫點 | 手動：驗收審查者讀 diff |

## User Story 7 — 被釘住的舊測試只是改寫、不是放寬（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-G01 | Pins to rewrite：tcf01 | 功能 | 對 `v3` 比較 `test_pat.py` 的 tcf01 | 讀 diff 並執行 | 改寫後仍斷言：授權伺服器 metadata 不在 MCP 行程；`AuthSettings` 不在 `mcp_server.py`（原有的原始碼斷言保留）；新增斷言 TC-A01、A02 的 metadata 與挑戰；ledger 有舊預期、新預期、理由 | 自動：`test_pat.py`；手動：讀 ledger |
| TC-G02 | Pins to rewrite：tcf02 | 功能 | 對 `v3` 比較 tcf02 | 讀 diff 並執行 | `run_http` 簽名只多 `public_url`；`mcp --help` 仍不出現 ssl、cert、tls（只放行 `public`）；ledger 有紀錄 | 自動；手動：讀 ledger |
| TC-G03 | Pins to rewrite：`test_confirm_page.py` 的 `/oauth/*`（第 307 行附近） | 例外 | 網頁服務路由全集 | 對舊清單（`/`、`/runs`、`/ce`、`/compute-envs`、`/admin`、`/launch`、`/submit`、`/oauth/*` 等）與任意未列路徑 GET／POST | 只有 ledger 列出的路徑存在（009c 的登入、登出、`/c/{rid}` 加 OAuth 的 metadata、`/authorize`、`/token`、`/register`、`/revoke` 與同意頁）；其餘一律 404；舊清單裡沒被列入的仍是 404 | 自動 |
| TC-G04 | Pins to rewrite：tcb01–b07 | 功能 | 對 `v3` 比較 tcb01–b07 | 讀 diff 並執行 | 只改標頭文字斷言；狀態碼 401、「絕不回顯」等斷言一條不少 | 自動；手動：讀 diff |
| TC-G05 | Unchanged pins；憲法安全網 | 功能 | `test_receiver.py`、`test_station_envs.py`（tc086）、`test_human_channel.py` 的 tcf10_f11、`test_pat.py` tcc03／c04 | 執行（tc086、receiver、tcf10_f11、tcc03／c04 內容不改；test_station_envs.py 只准 tc063、tc084 依 plan「Ruling after acceptance round 1」改寫） | 全綠；新增的 `oauth_*` 表與欄位不含禁字（`user` 只以 `user_id`，不含 session／login／password／email／org／team／member／cookie／role）；`EXEMPT` 一字未動 | 自動 |
| TC-G06 | 驗收規則：弱化測試 | 功能 | 對 `v3` 比較全部被改的測試檔、`spec`／`test-case*.md` | 驗收審查者讀 diff 與 `ledger.md` | 被改寫的只有計畫列出的 tcf01、tcf02、`test_confirm_page.py` 路徑清單、tcb01–b07、文件／版本釘，以及 plan「Ruling after acceptance round 1」點名的 tc068、tc063、tc084；每條有舊、新、理由；沒有刪除、跳過、放寬；實作期間沒有編輯本合約 | 手動：驗收審查者讀 diff |
| TC-G07 | Pins to rewrite：Docs and version pins | 功能 | 文件與版本釘的測試 | 執行 | 通過，且改動只是新版本號與新文件段落 | 自動 |

## 不在範圍（計畫「Not in this PR」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H01 | 不做公開 https 託管（009h）；E6 | 不在範圍 | 檢查網頁服務與 MCP 的程式與選項 | 找 TLS、憑證、證書路徑的設定或旗標 | 沒有；網頁服務仍是 loopback 的 http，`--public-url` 只決定 issuer／網址文字與 `Secure`；本機測試用 loopback 取代 | 自動 |
| TC-H02 | 不做多於一種的 scope | 不在範圍 | metadata 與註冊 | 檢查 `scopes_supported`；要求 scope 為 `admin`、`launch`、`read write` | metadata 至多宣告一種 scope；其他 scope 被拒或被忽略成那一種；沒有分級權限 | 自動 |
| TC-H03 | 不做接收器或代理的 OAuth | 不在範圍 | 接收器與代理 | 找 OAuth 路由，並用 OAuth 權杖打 | 沒有 OAuth 路由；OAuth 權杖被拒（見 TC-A06、E08） | 自動 |
| TC-H04 | 不做第三方身分提供者 | 不在範圍 | 授權頁與設定 | 找 Google／GitHub 登入、外部 IdP 旗標或欄位 | 沒有；授權頁唯一的登入方式是名字＋網頁密碼 | 自動 |
| TC-H05 | 不做密碼重設 | 不在範圍 | 網頁、OAuth 路由與 MCP | 找重設、忘記密碼、改密碼的路由或工具 | 沒有；`user passwd` 仍只能在真正的終端機（009c 不變） | 自動 |
| TC-H06 | 不做「記住每個連接器的同意」 | 不在範圍 | `ann` 已對客戶端 X 按過「允許」並換過權杖 | X 再次 `/authorize` | 又出現同意頁，必須再按一次「允許」才發碼；沒有「記住」選項、沒有跳過同意的路徑 | 自動 |
| TC-H07 | 不改確認通道 | 不在範圍 | `confirmations.channel` 與動作層 | 找 `OAUTH` 之類新通道值、新單例；跑完整 OAuth 流程後看 `channel` | 只有 `TERMINAL`、`ELICITED`、`PAGE` 三種；沒有新增；OAuth 流程不產生任何通道值 | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-I01 | 治理：計畫寫「no amendment」；I.2 仍是 tier A | 功能 | 對 `v3` 比較 `.specify/memory/constitution.md` | 讀 diff | 憲法一字未改；I.2 的三個通道仍是唯一的確認通道 | 手動：驗收審查者讀 diff |
| TC-I02 | I.2 檢查：`tests/no_second_run_state_test.sh` | 功能 | 兩個分支 | 各跑一次 | 都通過；`LAUNCH_ALLOW` 沒有新增檔案；OAuth 程式不提交工作 | 自動：`tests/no_second_run_state_test.sh` |
| TC-I03 | 安全網「憑證僅存設定區、不印出」；V/VI：只存雜湊；計畫「canary 掃描延伸到 OAuth 權杖」 | 功能 | 走完整個流程，取得授權碼、access、refresh、client_id | 對整個平台資料目錄逐位元組 canary 掃描授權碼、access、refresh 的原值 | 找不到原值；`tokens`、`oauth_codes` 只有 sha256 雜湊；`oauth_requests` 不存碼 | 自動：`platform/tests/test_secrets.py` 擴充 |
| TC-I04 | 安全網「不印出」 | 例外 | 登入、授權、換權杖、撤銷、錯誤各走一次，收集 stdout、stderr、伺服器日誌、回應 HTML、`abf-platform oauth revoke` 的輸出 | 搜尋授權碼、access、refresh、網頁密碼、cookie 值 | 都不出現 | 自動 |
| TC-I05 | 計畫「Update `docs/PLATFORM.md`, `docs/TESTING.md` and CHANGELOG」；設計 9 | 功能 | 對 `v3` 比較三份文件 | 讀 diff | `docs/PLATFORM.md` 有誠實邊界：握有 OAuth 權杖的 AI 客戶端能以該使用者身分做事，唯獨不能替本人說「是」；強度與 PAT 相同、只是壽命較短；`docs/TESTING.md` 有「Claude Desktop custom connector (#117)」段落；CHANGELOG 有一條 | 手動：驗收審查者讀文字 |
| TC-I06 | E6；設計 1；計畫 3 | 功能 | 一個本機的 OAuth 測試客戶端（或不經雲端的 Claude Desktop 以外的程式）與 loopback 網頁服務 | 照 `docs/TESTING.md` 新段落走：註冊、瀏覽器登入、按「允許」、拿權杖、連 `/mcp` | 步驟具體到不懂程式的人也能照做；不依賴公開 https；文件明寫「Claude Desktop 端到端要等 009h」，且不宣稱已實測 | 手動：`docs/TESTING.md`（新增段落） |
| TC-I07 | 設計 1：「Record whether it can send a custom `Authorization: Bearer` header, the redirect URI it registers, and the client version」 | 功能 | 同上 | 讀文件新段落 | 段落要求記錄三件事（能否送自訂 Bearer 標頭、註冊的 redirect URI、客戶端版本）；允許的 redirect URI 清單（https 或 loopback）有出處，來源是這次手動檢查而不是猜的 | 手動：驗收審查者讀文字 |
| TC-I08 | 安全網「送出前完整顯示並等待確認」；hooks | 功能 | `tests/confirm_launch_test.sh`、`tests/confirm_cleanup_test.sh` | 在 `v3` 與本分支各跑一次 | 結果相同；本 PR 沒改 hook | 自動（Windows 經 WSL，見 `docs/TESTING.md`） |
| TC-I09 | 憲法 I.1：先用現成的 | 功能 | 讀 `abf_platform/oauth.py` | 找 PKCE、授權碼、metadata、註冊的實作 | 用 `mcp==2.3.0` 的 `OAuthAuthorizationServerProvider` 與 `create_auth_routes`／`create_protected_resource_routes`，檔頭寫明替代方案；沒有手寫的 PKCE 比對或自製 metadata 格式 | 手動：驗收審查者讀程式 |
| TC-I10 | 綠燈 | 功能 | 整個 `platform/tests/` | 在 WSL 或 CI 執行 | 全綠 | 自動：CI |
