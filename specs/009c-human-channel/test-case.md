# 測試案例：009c 人的確認通道——送出前先出現摘要頁，只有本人能按「送出」

**規格**：無 `spec.md`（依維護者指示一律以 `specs/009c-human-channel/plan.md` 為準，含其「Decided 2026-10-17 (round 2)」與 developer-agent 對合約審查第 2 至 5 點的裁決；plan 的「給維護者」三句是他看得懂的承諾）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、有人想繞過時，系統怎麼反應（拒絕、停下、狀態不變）。
- **不在範圍**：計畫「Not in this PR」明講這次不做的事；測試確認它真的沒做。

維護者的話（逐字）：

> 「正式上線後：不管用 Claude Desktop、Claude Code、Codex 還是平台網頁，送出前都跳出摘要頁（管線、樣本、跑在哪、結果放哪），我按「送出」才跑；按的必須是我本人、AI 不能代按；別人打開同一連結不能送出。」

我把這句拆成六個要求，每個都對到下面的 TC：

- E1 送出前跳出摘要，含管線、樣本、跑在哪、結果放哪：TC-A01、TC-A16、TC-D13。
- E2 我按「送出」才跑：TC-A03、TC-C01、TC-D01。
- E3 按的必須是我本人：TC-B14、TC-D05、TC-D22、TC-B08。
- E4 AI 不能代按：TC-B14、TC-B15、TC-C07、TC-D17、TC-B03。
- E5 別人打開同一連結不能送出：TC-D05、TC-D22、TC-E05。
- E6 Claude Desktop／Claude Code／Codex／平台網頁都適用：TC-C14、TC-D21、TC-C10；網頁入口見總覽疑問 1。

另一句承諾（plan「Round 2」，維護者答「好的」）：網頁登入用「姓名＋獨立的網頁密碼」；密碼只能在真正的終端機用 `abf-platform user passwd` 設定，只存單向雜湊；個人存取權杖（PAT）永遠不能用來登入網頁；`Authorization: Bearer` 永遠不會讓人登入網頁。對應 TC-B01 至 TC-B25。

名詞：
- **MCP**＝AI 客戶端（Claude Desktop、Claude Code、Codex）跟平台講話的管道。
- **表單詢問（elicitation）**＝AI 客戶端在對話裡跳出一個要人回答的表單，答案來自客戶端的畫面，不是模型自己填。
- **等待中（pending）**＝已準備好摘要、但還沒有人按「送出」的送出申請，此時不算確認、不會排進任何工作。
- **TTY**＝真正的終端機（有人坐在鍵盤前能打字的視窗），管線、腳本、AI 工具的背景執行都不算。
- **雜湊（hash）**＝單向轉換後的指紋，看不出原值。
- **scrypt**＝專門設計成「算得慢」的密碼雜湊法，讓猜密碼很貴。
- **CSRF 記號**＝網頁表單裡附的一次性暗號，沒有它的 POST 會被拒，防別的網站偷偷代你按按鈕。
- **canary 掃描**＝先造一個已知的假值，再把整個資料目錄逐位元組找這個值，找到就算洩漏。
- **ELICITED／PAGE／TERMINAL**＝記錄「是誰（哪種通道）按下確認」的三個固定標記。
- **void**＝這筆申請作廢，不能再被確認。
- 「前後一樣」的基準＝計畫起點 `v3`（009d 合併之後）的行為。

## User Story 1 — AI 要送出時，先建立「等待中」的申請並出現摘要，沒有人按就不會跑（優先度 P1）

維護者原話：「送出前都跳出摘要頁（管線、樣本、跑在哪、結果放哪），我按「送出」才跑」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-A01 | 維護者例子 E1；設計 2、4 | 功能 | 一個可用的環境、已回報資料的代理、一份有 2 筆樣本的 samplesheet | AI 透過 MCP 呼叫 `launch`（管線、版本、samplesheet 路徑、環境、run 名稱） | 摘要文字裡看得到：管線與版本、跑在哪（環境與代理）、結果放哪（專屬資料夾）、兩筆樣本的列、`params.yaml`／`nextflow.config`／`head.sh` 內容；沒有任何一項只是「略」 | 自動：`platform/tests/test_human_channel.py` |
| TC-A02 | 設計 2（「和終端機同一份 screen」）；Round 2 裁決「畫面建構搬進 actions，輸出不變」 | 功能 | 同一組輸入 | 分別用終端機 `abf-launch` 與 MCP `launch` 產生摘要文字 | 兩者除了 `terminal.PREFIX` 這個行首標記外逐字相同；搬家前後（對 `v3`）終端機畫面逐字不變 | 自動：`test_human_channel.py`；`platform/tests/test_launch_cli.py` 全綠 |
| TC-A03 | 維護者例子 E2；設計 2 | 功能 | 佇列裡 0 個工作 | MCP `launch` 建立等待中申請後，沒有任何人按 | `confirmations` 多一列 `state=pending`；`jobs` 仍是 0 個；回覆明說「還沒送出」 | 自動 |
| TC-A04 | 設計 2：「等待中不是確認」 | 例外 | 一筆 `state=pending` 的申請 | 直接拿它的 id 與雜湊去排工作（`jobs.enqueue_confirmed` 或 `_check_confirmation`） | 被拒絕，佇列仍 0 個工作 | 自動 |
| TC-A05 | 設計 2（cancel 與 launch 對稱） | 功能 | 一個正在跑的 run | MCP `cancel` | 同樣只建立 `kind=cancel` 的等待中申請與摘要，沒有 `cancel_run` 工作；工具標示為具破壞性 | 自動 |
| TC-A06 | Round 2 裁決「MCP launch 與終端機同樣的選項」 | 功能 | 同一組選項：管線、版本、samplesheet 路徑、params、ce_name、run 名稱 | 終端機與 MCP 各準備一次 | 兩邊算出的 bundle（要送出的完整內容）雜湊相同 | 自動 |
| TC-A07 | 設計 3（建構失敗不留申請） | 例外 | 環境不存在、代理沒回報資料、run 名稱已被用、samplesheet 讀不到，各一次 | MCP `launch` | 每種都被拒絕，理由與終端機同一類；`confirmations` 沒有新增列 | 自動 |
| TC-A15 | 設計 2（沿用終端機 TC-006 的防線） | 例外 | samplesheet 或 params 含會改寫畫面的控制字元 | MCP `launch` | 在建立申請與顯示任何東西之前就拒絕；沒有申請列 | 自動 |
| TC-A08 | 設計 2、Plan 的 tce 改寫 | 功能 | 列出 MCP 工具 | 取得工具清單 | 剛好 8 個：原本 6 個唯讀工具加 `launch`、`cancel`；`launch` 的 `read_only_hint=False`，`cancel` 另有 `destructive_hint=True`；沒有任何名叫 approve／confirm／passwd／login 的工具；`launch`、`cancel` 的參數裡沒有 `yes`、`confirm`、`confirmed`、`approve` 之類能表示「已同意」的欄位 | 自動：`platform/tests/test_mcp.py` |
| TC-A09 | Round 2 裁決「confirmations 加欄位」 | 功能 | 建立一筆等待中申請 | 讀該列 | 有完整 `bundle_json`、`ce_name`、`kind`、`sha256`、`caller_user_id`、`state=pending`、`expires_at`＝建立時間＋10 分鐘、`channel` 與 `confirmed_at` 為空 | 自動 |
| TC-A10 | Round 2 裁決「既有列升級為 confirmed／TERMINAL」 | 功能 | 一個 009d 版本做出的 platform.db，裡面有已用與未用的舊確認列 | 用新版開啟 | 欄位補齊；舊列 `state=confirmed`、`channel=TERMINAL`；未用的舊列仍然能被站台檢查通過（行為與 `v3` 相同） | 自動 |
| TC-A11 | Round 2 裁決「`_check_confirmation` 另要求 state=confirmed」 | 例外 | 三筆列：`pending`、`void`、`confirmed`（雜湊與種類都對、未用過） | 對每筆呼叫 `jobs._check_confirmation` | `pending`、`void` 被拒，`confirmed` 通過；原本的檢查（id、種類、未用、單次、雜湊相符）一項不少 | 自動 |
| TC-A12 | 設計 6、009d 沿用 | 例外 | `serve` 的 HTTP MCP | 不帶 `Authorization: Bearer` 呼叫 `launch` | 401；沒有申請列 | 自動 |
| TC-A13 | 設計 2、7 | 功能 | 用某位使用者的 PAT 呼叫 HTTP MCP `launch` | 建立等待中申請 | `caller_user_id` 記為該使用者；此身分只被記錄，不構成確認 | 自動 |
| TC-A14 | 設計 6：stdio 沒有呼叫者 | 例外 | 本機 stdio MCP，客戶端不支援表單詢問 | `launch` | 被拒絕，訊息明說「請用終端機指令，或用帶權杖的 HTTP」；沒有申請列、沒有工作 | 自動 |
| TC-A16 | 維護者例子 E1；設計 4、Round 2「等待中保留完整 bundle」 | 功能 | 一筆等待中申請 | 比對：摘要所用的 bundle、`bundle_json`、`sha256` | 三者是同一份內容；摘要顯示的就是將被雜湊與排隊的內容，沒有第二份 | 自動 |

## User Story 2 — 網頁登入：姓名＋獨立的網頁密碼，密碼只能在終端機設定（優先度 P1）

維護者原話（Round 2，答「好的」）：網頁登入用「姓名＋獨立的網頁密碼」，密碼只在真正的終端機設定，永遠不是個人存取權杖。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-B01 | Round 2·密碼 | 功能 | 已有使用者 `ann`；在真正的 TTY 裡 | 執行 `abf-platform user passwd ann`，輸入兩次相同密碼（不顯示在螢幕上） | 成功結束；之後 `ann` 能用這個密碼登入網頁；輸出不含密碼本身 | 自動：`platform/tests/test_web_login.py`（用偽終端機 pty） |
| TC-B02 | Round 2·密碼：「needs a real TTY」 | 例外 | stdin 是管線或檔案（沒有 TTY），例如 `echo pw \| abf-platform user passwd ann` | 執行 | 被拒絕並說明「要在真正的終端機輸入」；資料庫沒有任何密碼被寫入或改動 | 自動 |
| TC-B03 | 維護者例子 E4；Round 2·密碼 | 例外 | 嘗試用 `--password`、`--password-file`、環境變數（如 `ABF_WEB_PASSWORD`）、命令列參數把密碼帶進去 | 執行 `user passwd` | 沒有任何旗標或環境變數能代替鍵盤輸入：未知旗標被拒，環境變數被忽略；密碼沒有被設定 | 自動 |
| TC-B04 | Round 2·密碼 | 例外 | TTY；兩次輸入不一致 | 執行 `user passwd ann` | 被拒絕，沒有改動，原密碼仍有效 | 自動 |
| TC-B05 | Round 2·密碼 | 例外 | TTY；使用者不存在 | `user passwd nobody` | 被拒絕並說明沒有這個使用者；沒有建立使用者 | 自動 |
| TC-B06 | Round 2·密碼：「slow hash (scrypt)」；「only a slow hash」 | 功能 | 兩位使用者設定了完全相同的密碼；放一個 canary 密碼 | 對整個平台資料目錄做逐位元組 canary 掃描，並讀 `password_hash` 欄 | 找不到密碼原文；欄位是 scrypt 格式（含參數與鹽）；兩位使用者的雜湊不同（各有各的鹽）；輸入密碼不會出現在 stdout／stderr／日誌 | 自動 |
| TC-B07 | Round 2·密碼 | 功能 | `ann` 已有密碼 | 再次 `user passwd ann` 改成新密碼 | 新密碼能登入，舊密碼不能登入 | 自動 |
| TC-B08 | 維護者例子 E3；Round 2·密碼 | 功能 | `ann` 已設密碼，網頁服務執行中 | 在登入頁用 `ann`＋正確密碼登入 | 成功；回傳 session cookie；`web_sessions` 多一列，屬於 `ann`；之後 `ann` 開確認頁被認得是 `ann` | 自動 |
| TC-B09 | Round 2 裁決「HttpOnly、SameSite=Strict」 | 功能 | loopback（127.0.0.1）網址登入成功 | 看 `Set-Cookie` | 有 `HttpOnly`、`SameSite=Strict`；loopback 時沒有 `Secure`；存活 12 小時 | 自動 |
| TC-B10 | Round 2 裁決「Secure when not loopback」 | 功能 | `--public-url` 指向非 loopback 的 https 位址 | 登入成功後看 `Set-Cookie` | 多了 `Secure` | 自動 |
| TC-B11 | Round 2·密碼 | 例外 | `ann` 已設密碼 | 用錯誤密碼登入 | 被拒、沒有 cookie、沒有 `web_sessions` 列；回應不含輸入的密碼 | 自動 |
| TC-B12 | Round 2·密碼 | 例外 | 沒有叫 `ghost` 的使用者 | 用 `ghost`＋任意密碼登入 | 被拒、沒有 cookie | 自動 |
| TC-B13 | Round 2·密碼：「name + this password」 | 例外 | 使用者 `bob` 存在，但從未設定網頁密碼 | 用 `bob`＋空字串、`bob`＋任意字串登入 | 都被拒，不因為「沒設密碼」而放行 | 自動 |
| TC-B14 | 維護者例子 E3、E4；Round 2：「`Authorization: Bearer` never logs into the web (TC-B14)」 | 例外 | `ann` 有有效 PAT（用於 MCP） | 在網頁的登入頁、確認頁 GET、確認頁 POST 都帶 `Authorization: Bearer <ann 的 PAT>`，姓名與密碼欄留空或亂填 | 每一個請求都沒有登入、沒有 cookie、沒有 `web_sessions` 列；確認頁仍要求登入；沒有任何狀態改變 | 自動 |
| TC-B15 | Round 2：「never a PAT」 | 例外 | `ann` 有有效 PAT | 在登入頁以 `ann`＋PAT 字串當密碼登入 | 被拒、沒有 cookie | 自動 |
| TC-B16 | Round 2 裁決：登入失敗每分鐘最多 5 次 | 例外 | `ann` 已設密碼；時鐘可控 | 60 秒內用錯密碼登入 5 次，再用「正確密碼」登入第 6 次 | 第 6 次也被拒，並說明太頻繁、稍後再試；沒有 cookie | 自動 |
| TC-B17 | Round 2 裁決：每個姓名各自計算 | 功能 | 同上，`ann` 已被限制 | (a) 用 `bob` 與其正確密碼登入；(b) 把時鐘撥過 60 秒後 `ann` 用正確密碼登入 | 兩者都成功：限制只跟那個姓名、那個時間窗有關 | 自動 |
| TC-B18 | Round 2：「web_sessions (id_hash, user_id, created_at, expires_at)」「only its hash is stored」 | 功能 | 登入成功，拿到 cookie 值 | 讀 `web_sessions` 並對整個資料目錄做 canary 掃描（cookie 值、cookie 內的隨機 id） | 欄位剛好是 `id_hash`、`user_id`、`created_at`、`expires_at`；找不到 cookie 的原始 id；`expires_at`＝建立時間＋12 小時 | 自動 |
| TC-B19 | Round 2：cookie 12 小時 | 例外 | 登入成功；時鐘可控 | 時間撥到 12 小時又 1 秒後帶著 cookie 開確認頁並 POST | 視同未登入，被拒；不改任何狀態 | 自動 |
| TC-B24 | Round 2：cookie 12 小時 | 功能 | 同上 | 時間撥到 11 小時 59 分後開確認頁 | 仍然是登入狀態 | 自動 |
| TC-B20 | Round 2：signed cookie | 例外 | 登入成功 | 把 cookie 內容改一個字元、換成別人的 session id、或只填 `web_sessions` 裡的雜湊 | 都視同未登入 | 自動 |
| TC-B21 | Round 2 裁決「signing key kept in the platform data dir (mode 600)」 | 功能 | 第一次啟動網頁服務 | 看資料目錄 | 簽章金鑰檔存在、只有擁有者可讀寫（Windows 上驗收審查者依 `docs/TESTING.md` 手動看權限）；金鑰不在 git、不在任何輸出；重啟後原本的 cookie 仍有效 | 自動（POSIX）；Windows：手動 `docs/TESTING.md` |
| TC-B22 | Round 2：網頁身分不開別的門 | 例外 | 登入成功拿到 cookie | 帶這個 cookie（沒有 Bearer）去打 MCP 伺服器與接收器（receiver）的各路由 | 都是 401／404，沒有任何一個因為 cookie 而放行 | 自動 |
| TC-B23 | 憲法安全網「憑證不被印出」 | 例外 | 登入失敗、登入成功、`user passwd` 各一次，開啟日誌 | 搜尋 stdout、stderr、伺服器日誌、回應 HTML | 密碼與 cookie 值都不出現 | 自動 |
| TC-B25 | 009d 的 `disabled_at` 語意（計畫未明寫，見總覽疑問 2） | 例外 | `ann` 被停用（`disabled_at` 有值），原本有密碼 | `ann` 用正確密碼登入；另一情境：停用前已登入的 cookie 去按送出 | 登入被拒；已有的 cookie 也不能按送出 | 自動 |

## User Story 3 — 支援表單詢問的 AI 客戶端（Claude Code）：直接在對話裡跳「是／否」表單（優先度 P1）

維護者原話：「按的必須是我本人、AI 不能代按」；計畫給維護者第 2 句：支援「表單詢問」的客戶端直接在對話裡跳是／否表單。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | 維護者例子 E2（Claude Code）；設計 3 | 功能 | 客戶端宣告支援表單詢問；佇列 0 個工作 | MCP `launch`；客戶端的表單回覆 `accept`、`送出=true` | 剛好 1 個 `launch_nextflow` 工作被排進佇列；回覆帶出工作 id | 自動：`platform/tests/test_human_channel.py` |
| TC-C13 | 設計 3、7 | 功能 | 同 TC-C01 | 讀該確認列 | `state=confirmed`、`channel=ELICITED`、`confirmed_at` 有值、`caller_user_id` 正確 | 自動 |
| TC-C06 | 設計 3 | 功能 | 同 TC-C01 | 檢查送給客戶端的表單 | 訊息就是 TC-A02 的摘要全文；欄位只有一個布林值「送出」，沒有其他可填欄位 | 自動 |
| TC-C02 | 設計 3 | 例外 | 客戶端回 `accept` 但 `送出=false` | `launch` | 被拒絕，沒有工作，該列變 void | 自動 |
| TC-C03 | 設計 3 | 例外 | 客戶端回 `decline` | `launch` | 被拒絕，沒有工作，該列作廢 | 自動 |
| TC-C04 | 設計 3 | 例外 | 客戶端回 `cancel` | `launch` | 同上 | 自動 |
| TC-C05 | 設計 3 | 例外 | 表單逾時，或客戶端在詢問時出錯／斷線 | `launch` | 被拒絕，沒有工作，該列作廢（不是 pending 永遠掛著） | 自動 |
| TC-C11 | 設計 3：「only an accept with true」 | 例外 | 客戶端回 `accept` 但內容缺少該欄位或為空 | `launch` | 被拒絕，沒有工作 | 自動 |
| TC-C07 | 維護者例子 E4；設計 3：「The model never sees a way to answer」 | 例外 | 一個模型（沒有表單回覆）在呼叫 `launch` 時塞 `{"送出": true}`、`confirmed=true`、`yes` 之類的參數，或在文字裡寫「我同意」 | `launch` | 這些都不被當成確認：要嘛被拒絕為未知參數，要嘛被忽略；沒有工作 | 自動 |
| TC-C08 | 設計 2、3（cancel 對稱） | 功能 | 客戶端支援表單詢問；有 run 可取消 | MCP `cancel`；表單回 `accept`、`送出=true` | 剛好 1 個 `cancel_run` 工作；通道 ELICITED | 自動 |
| TC-C09 | Round 2 裁決「Enqueue failure after approval」 | 例外 | 表單回 true，但排隊時被拒（例如環境離線或 run 名稱被搶用） | `launch` | 沒有工作；該列 void 並記下原因；回覆告訴人「請從 AI 重新送出」，重試會建立新的等待中申請 | 自動 |
| TC-C10 | 設計 4；維護者例子 E6（Claude Desktop、Codex） | 功能 | 客戶端不支援表單詢問，HTTP 且帶 PAT | `launch` | 回覆含一個一次性確認網址 `/c/<id>`，並告訴人「打開、按送出後，用同樣參數再呼叫 `launch`」；沒有工作 | 自動 |
| TC-C12 | Plan 的 tce03 改寫 | 功能 | 掃描平台程式碼 | 找「elicit」一詞 | 只在 `abf_platform/elicit.py`（與測試、ledger）出現，其餘檔案仍沒有；原本「整個平台都沒有 elicitation」的測試改成這條，ledger 記舊預期、新預期、理由 | 自動：`platform/tests/test_actions_layer.py` |
| TC-C14 | 維護者例子 E6（Claude Code 實機） | 功能 | 真的 Claude Code 連上平台 | 要它送一個管線 | 對話裡跳出摘要與是／否表單；按「是」才有工作；按「否」沒有；模型自己無法替我按 | 手動：`docs/TESTING.md`（新增段落） |

## User Story 4 — 其他客戶端：拿到網址，在瀏覽器登入後按「送出」，只有本人能按（優先度 P1）

維護者原話：「按的必須是我本人、AI 不能代按；別人打開同一連結不能送出。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-D01 | 維護者例子 E2、E3；設計 4 | 功能 | `ann` 有密碼；MCP 用 `ann` 的 PAT 建立了等待中申請，拿到網址 | `ann` 在瀏覽器登入，打開 `/c/<id>`，看到摘要，按「送出」（帶正確 CSRF 記號） | 剛好 1 個工作被排進佇列；頁面顯示已送出與工作 id | 自動：`platform/tests/test_confirm_page.py` |
| TC-D20 | 設計 4、7 | 功能 | 同 TC-D01 | 讀該確認列 | `state=confirmed`、`channel=PAGE`、`confirmed_at` 有值、`caller_user_id`＝`ann` | 自動 |
| TC-D02 | Round 2 裁決「`--public-url` 設定 MCP 回覆所用的網址基底」 | 功能 | 以 `--public-url https://abf.example` 啟動網頁服務 | MCP `launch` 的回覆 | 網址以 `https://abf.example/c/` 開頭，並附「再呼叫一次 `launch`」的說明；未設定時用 loopback 位址 | 自動 |
| TC-D03 | 設計 4：「GET never changes anything」 | 例外 | `ann` 已登入；有等待中申請 | 多次 GET `/c/<id>` | 資料庫逐表比對沒有任何變化（含頁面被打開多次），沒有工作 | 自動 |
| TC-D04 | 設計 4 | 例外 | 沒有登入 | 打開 `/c/<id>` | 看到的是「需要登入」，沒有「送出」按鈕；申請與佇列不變 | 自動 |
| TC-D05 | 維護者例子 E3、E5：「別人打開同一連結不能送出」 | 例外 | `ann` 的申請；`bob` 已登入（有自己的密碼與 cookie） | `bob` 打開同一個 `/c/<id>` | 看到「不是你的申請」，沒有「送出」按鈕；申請與佇列不變 | 自動 |
| TC-D22 | 維護者例子 E3、E5 | 例外 | 同上 | `bob` 以自己有效的 CSRF 記號直接 POST 送出 | 被拒絕；申請仍為 pending；沒有工作 | 自動 |
| TC-D06 | 設計 4：CSRF | 例外 | `ann` 已登入 | POST 送出但不帶 CSRF 記號 | 被拒；沒有工作；申請仍可由本人正常按 | 自動 |
| TC-D07 | 設計 4：CSRF | 例外 | 同上 | POST 帶錯誤的記號 | 同上 | 自動 |
| TC-D08 | 設計 4：CSRF | 例外 | `ann` 有兩個等待中申請 | 拿申請 1 頁面上的記號去 POST 申請 2；拿別人 session 的記號去 POST | 都被拒；沒有工作 | 自動 |
| TC-D09 | 設計 4：「single use」 | 例外 | 申請已按過一次送出 | 再 POST 一次 | 被拒；仍然只有 1 個工作 | 自動 |
| TC-D10 | 設計 2、4：10 分鐘到期 | 例外 | 時鐘撥到建立後 10 分鐘又 1 秒 | 本人 GET 與 POST | 頁面說已逾時，POST 被拒；沒有工作 | 自動 |
| TC-D11 | 設計 4 | 例外 | 隨機編造的 id | GET／POST `/c/<亂數>` | 404，不透露任何申請是否存在 | 自動 |
| TC-D12 | 設計 4：一次性網址 | 功能 | 建立 20 筆申請 | 看 id | 全是 32 個十六進位字元（128 位元隨機），彼此不重複 | 自動 |
| TC-D13 | 維護者例子 E1；設計 4 | 功能 | 一筆摘要裡的 samplesheet 樣本名稱含 `<script>alert(1)</script>` 與 `&` | 本人打開確認頁 | 頁面顯示的是 TC-A02 的摘要全文；樣本名稱被轉義成文字，不被當成網頁程式碼執行；管線、樣本、環境、專屬資料夾都看得到 | 自動 |
| TC-D14 | 設計 4、Round 2「pending row keeps the full bundle」 | 例外 | 本人 POST 時多帶 `pipeline=…`、`bundle=…`、`ce_name=…` 等額外欄位 | 按送出 | 額外欄位被忽略；排進佇列的內容雜湊與 pending 列相同 | 自動 |
| TC-D15 | 設計 2、4（cancel） | 功能 | `ann` 的 cancel 等待中申請 | 本人登入、按送出 | 頁面標明是「取消」並顯示取消摘要；剛好 1 個 `cancel_run` 工作 | 自動 |
| TC-D16 | Round 2：網頁是獨立 app；receiver 路由不變 | 功能 | 啟動 `abf-platform web`、MCP 伺服器、接收器 | 在三者各打 `/login`、`/c/x`、`/mcp`、`/runs` 之類路徑 | 網頁 app 不提供 MCP 與接收器路由；MCP 與接收器不提供 `/login`、`/c/…`；接收器的 `ROUTES_V3` 與 `v3` 逐項相同 | 自動 |
| TC-D17 | 維護者例子 E4：「AI 不能代按」 | 例外 | 一個只握有 `ann` 的 PAT 的 AI（沒有網頁密碼、沒有 cookie）；它透過 MCP 建立了等待中申請並知道網址 | AI 用 Bearer 對 `/c/<id>` 做 GET 與 POST，嘗試登入，嘗試不帶 CSRF 或自造 CSRF | 全部沒有效果：沒有登入、沒有確認、沒有工作；申請仍為 pending | 自動 |
| TC-D18 | Round 2 裁決「`abf-platform web`：獨立行程、loopback、自己的埠」 | 功能 | 執行 `abf-platform web` | 看 `--help` 與監聽位址 | 預設只聽 127.0.0.1；埠與 MCP／接收器不同；有 `--public-url` 選項；網頁不是嵌在 `serve` 的 `BearerAuth` 之內 | 自動 |
| TC-D19 | 設計 2、3、Round 2 void | 例外 | 一筆 `state=void` 的申請（被拒或逾時） | 本人 GET 與 POST | 頁面說這筆申請已作廢；POST 被拒；沒有工作 | 自動 |
| TC-D21 | 維護者例子 E6（Claude Desktop、Codex、平台網頁） | 功能 | 真的 Claude Desktop 與 Codex 各連上 HTTP 平台；維護者已用 `user passwd` 設好網頁密碼 | 各要它送一個管線 | 兩者都給出網址；在瀏覽器登入、看到摘要、按「送出」才有工作；不按就沒有；AI 拿 PAT 試著替我按沒有用 | 手動：`docs/TESTING.md`（新增段落） |

## User Story 5 — 一次確認只跑一次，換了內容就不能沿用（優先度 P1）

計畫「Tests」：Accepted 那兩條與 Refused 的重放、過期、內容改變。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-E01 | 設計 4：「The repeated MCP call finds the flipped row…」 | 功能 | `ann` 已按過網頁送出 | `ann` 的 AI 用相同參數再呼叫 `launch` | 回覆工作 id（就是網頁按出來的那個）；佇列仍只有 1 個工作 | 自動：`test_human_channel.py` |
| TC-E02 | 計畫「Tests」：第三次呼叫同一 id | 功能 | 同上 | 第三次呼叫 `launch` | 仍回同一個 id；佇列仍是 1 個 | 自動 |
| TC-E03 | 設計 4 | 例外 | 還沒有人按送出 | AI 重複呼叫 `launch`（相同參數） | 沒有工作；告訴人還在等；不會產生一個 pending 就多一個工作 | 自動 |
| TC-E04 | 計畫「changed bundle after approval (hash mismatch)」 | 例外 | 申請已被本人核准 | AI 換一個參數（例如換 samplesheet 或版本）再呼叫 `launch` | 不沿用舊核准：沒有工作，改建新的等待中申請（新雜湊）；舊核准列不會被拿去排這個新內容 | 自動 |
| TC-E05 | 維護者例子 E5；計畫「approved by another user」 | 例外 | `ann` 的申請已被核准（或僅 pending） | `bob` 的 AI 用相同參數呼叫 `launch` | `bob` 找不到可沿用的核准，得到他自己的新 pending；沒有因 `ann` 的核准而排出 `bob` 的工作 | 自動 |
| TC-E06 | 計畫「an expired row」 | 例外 | 已核准但還沒被拿去排的列，時間過了 10 分鐘 | 再次呼叫 `launch` | 不沿用，要重新確認；沒有工作 | 自動 |
| TC-E07 | 計畫「a replayed row」 | 例外 | 一筆已用過（used_at 有值）的確認 | 拿同一 id 與雜湊再排一個工作 | 被拒（單次使用）；工作數不變 | 自動 |
| TC-E08 | Round 2 裁決「the person retries from the AI (new pending)」 | 功能 | 排隊失敗而作廢的列 | 排除原因後 AI 再呼叫 `launch` | 建立全新的 pending；舊列保持 void；本人核准新的那筆後成功 1 個工作 | 自動 |
| TC-E09 | 設計 4：交易只排一次 | 例外 | 本人同時（兩個執行緒）送出兩個 POST | 同時打 | 剛好 1 個工作；另一個得到「已送出」 | 自動 |
| TC-E10 | Round 2 裁決 `find_approved` | 功能 | 同一人、同一雜湊、`state=confirmed`、未用過的列 | 呼叫 `find_approved` | 只有「同一個 caller＋同一雜湊＋已 confirmed＋未過期」才找得到；缺任何一項都找不到 | 自動 |
| TC-E12 | 設計 2、Round 2 void | 例外 | 一筆 void 的列 | 之後想把它改成 confirmed（網頁 POST、表單、直接呼叫 `approve`） | 全部被拒；void 不可復活 | 自動 |

## User Story 6 — 終端機路徑與既有防線不變，被釘住的測試只是改寫、不是放寬（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-F01 | 計畫「Terminal path unchanged」 | 功能 | 終端機路徑的既有測試（tcb13、tcb18、TC-061） | 執行 | 全綠，且這些測試本身一字沒改 | 自動：`platform/tests/test_actions_layer.py`、`test_launch_cli.py` |
| TC-F02 | 計畫 Facts：「These stay as they are」 | 功能 | 對 `v3` 比較 `abf_station/launch.py` | 讀 diff | `abf_station/launch.py` 的確認檢查（id、種類、未用、單次、雜湊相符）完全沒改；站台代理仍是唯一的提交者 | 手動：驗收審查者讀 diff |
| TC-F03 | Round 2 裁決 | 功能 | 對 `v3` 比較 `jobs._check_confirmation` | 讀 diff 並執行 | 只多一個條件 `state = confirmed`；其餘檢查沒變、沒被放寬 | 自動：`test_human_channel.py`（見 TC-A11） |
| TC-F04 | 計畫 Facts：LAUNCH_ALLOW 不動 | 功能 | `tests/no_second_run_state_test.sh` | 在兩個分支各執行一次 | 兩邊都通過，允許清單沒有新增檔案；MCP 與網頁只排隊，不提交 | 自動：`tests/no_second_run_state_test.sh` |
| TC-F05 | 計畫「Terminal path unchanged」 | 功能 | `test_launch_platform.py` TC-061 | 執行 | 通過且未被改 | 自動 |
| TC-F06 | 計畫 Facts：「rewritten, not loosened」 | 功能 | 對 `v3` 比較全部被改的測試 | 驗收審查者讀 diff 與 `ledger.md` | 被改寫的只有計畫列出的：`test_launch_platform.py` TC-010 與六個唯讀工具那條、`test_mcp.py` tc024、`test_actions_layer.py` 的 tca02、tcb04／08／09／10、tcc02、tce01、tce03、tce04、tce07、`test_station_envs.py` tc086；每一條在 ledger 有舊預期、新預期、理由；沒有刪除、放寬或跳過任何斷言；沒有任何 deny 比新規則更弱 | 手動：驗收審查者讀 diff 與 `ledger.md` |
| TC-F07 | 設計 1；tcb04 擴充 | 例外 | 以字串、布林、`None`、長得像標記的字串（`"ELICITED"`、`"PAGE"`）、複製出來的標記物件、另一個類別的實例當作 `confirmed_by` | 呼叫 `launch`／`cancel` | 全部被拒；只有 `TERMINAL`、`ELICITED`、`PAGE` 這三個單例通過 | 自動 |
| TC-F08 | 設計 1 | 功能 | 三個單例 | 比較 | 彼此是不同物件；MCP 工具與網頁路徑排隊時用的是 `ELICITED`／`PAGE`，絕不會冒用 `TERMINAL`；`TERMINAL` 仍只有 `abf_launch/cli.py` 使用 | 自動 |
| TC-F09 | 計畫 Facts（tce04）：「signatures unchanged」 | 功能 | `actions.launch`、`actions.cancel` | 檢查簽名 | 參數清單與 `v3` 完全相同（`confirmed_by` 等仍是只能用關鍵字） | 自動 |
| TC-F10 | Round 2·tc086 的單一例外 | 功能 | 對 `v3` 比較 tc086 | 讀 diff 並執行 | 例外只新增：`web_sessions` 表（`id_hash`、`user_id`、`created_at`、`expires_at`）與 `password_hash` 這一欄，且各自精確到「哪個資料庫的哪張表的哪個欄位」（寫法比照 index.db 的 `runs.session_id`），不是在全域允許清單加字；其餘（對 `/`、`/login`、`/confirm`、`/confirmation` 等路徑的 404 檢查）一字未動；測試通過 | 自動：`test_station_envs.py` tc086；手動：讀 diff |
| TC-F11 | 同上 | 例外 | 暫時在 tokens.db、platform.db、index.db 各加一個名為 `role`、`cookie`、`session_id`（非豁免處）的欄位，或在 `web_sessions` 加第五欄 | 執行 tc086 | 測試失敗（掃描仍抓得到）；豁免沒有被放寬到其他欄位 | 手動：驗收審查者暫時造欄位試跑；自動：tc086 |
| TC-F13 | 計畫 Facts：接收器 ROUTES_V3 不動 | 功能 | 對 `v3` 比較 `receiver.py` | 讀 diff 並執行 tce02 | `ROUTES_V3` 與釘住它的測試都不變 | 自動 |
| TC-F14 | 計畫「Terminal path unchanged」 | 功能 | 整個 `platform/tests/` | 在 WSL 或 CI 執行 | 全綠 | 自動：CI |

## 不在範圍（計畫「Not in this PR」，以及本輪明確排除的事）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-G01 | 不做 resume／relaunch（009e） | 不在範圍 | 檢查動作層與 MCP 工具 | 找名字含 resume／retry／relaunch 的動作或工具 | 沒有（tce05 照舊通過） | 自動 |
| TC-G02 | 不做開發模式（009f） | 不在範圍 | 檢查設定與旗標 | 找能關掉確認的旗標、環境變數或「dev」開關 | 沒有；沒有任何方式能略過確認 | 自動 |
| TC-G03 | 不做公開 HTTPS（009h） | 不在範圍 | `abf-platform web --public-url https://…` | 看它做什麼 | 只用來決定網址文字與 `Secure` 屬性；網頁服務本身仍是 http，沒有憑證、沒有 TLS 設定 | 自動 |
| TC-G04 | 不做其他網頁（011 至 013） | 不在範圍 | 網頁 app 路由全集 | 對 `/`、`/runs`、`/ce`、`/compute-envs`、`/oauth/*`、`/admin` 等做 GET | 404；路由只有 ledger 列出的：登入、確認頁、確認頁的 POST（與必要的登出，如有則必須在 ledger 列出） | 自動 |
| TC-G05 | 維護者例子 E6（「平台網頁」送出入口屬 011 至 013） | 不在範圍 | 網頁 app | 試著用網頁 POST 建立新的送出申請、或選管線／上傳樣本 | 沒有這樣的路由；網頁只能核准「已存在、屬於自己」的等待中申請 | 自動 |
| TC-G06 | 本輪：網頁密碼只在終端機 | 不在範圍 | 網頁與 MCP | 找設定／修改網頁密碼的網頁路由或 MCP 工具 | 沒有；只有終端機指令 `user passwd` | 自動 |
| TC-G07 | 角色／組織屬 010 | 不在範圍 | 資料庫與介面 | 找 role／org／team 欄位或指令 | 沒有（tc086 照舊禁止） | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H01 | 治理：MAJOR 修訂（設計 8） | 功能 | 對 `v3` 比較 `.specify/memory/constitution.md` | 驗收審查者讀 diff | 版本 5.0.0，附 Sync Impact Report、破壞性評估（現有部署沒有人使用 HTTP 寫入）、被引用文件（PRINCIPLES、ADR 0006、`docs/PLATFORM.md` 等）都在同一個 PR 內同步更新；維護者自己合併 | 手動：驗收審查者讀 diff |
| TC-H02 | I.2：「confirmed it」的新定義 | 功能 | 同上 | 讀 I.2 與其「Check」 | I.2 寫成「透過人操作的通道確認：終端機、MCP 表單、或以同一位登入者身分使用平台確認頁」；並新增檢查「未確認的送出，MCP 工具與網頁路由都拒絕」，且該檢查指向存在、會執行的測試（TC-H09） | 自動：`tests/constitution_checks_test.sh` 之類既有的憲法檢查；手動：讀文字 |
| TC-H03 | 安全網「送出前完整顯示並等待確認」 | 功能 | 對 `v3` 比較安全網那一行（約第 170 行） | 讀 diff | 同時點名 `hooks/confirm_launch.sh`（Claude Code 套件）與動作層的閘門；原本的 hook 仍列著，沒有被拿掉 | 手動：驗收審查者讀 diff |
| TC-H04 | 維護者例子 E4 的誠實邊界 | 功能 | 讀憲法與 `docs/PLATFORM.md` | 找邊界說明 | 兩處都明寫：能在本人電腦上執行指令的 AI，能做本人能做的事；這道閘擋的是「只透過 MCP 到達平台」的 AI 客戶端 | 手動：驗收審查者讀文字 |
| TC-H05 | 設計 9（ADR 0006） | 功能 | Claude Code 套件設定 | 看 `mcp__abf-platform__launch`、`mcp__abf-platform__cancel` | 各有一條 `ask` 規則，文件寫明這是第二層、不是閘門 | 手動：驗收審查者讀設定與文件 |
| TC-H06 | 設計 9：套件規則不是閘門 | 例外 | 假設把那兩條 `ask` 規則拿掉 | 直接呼叫 MCP `launch`／`cancel`（無人按） | 仍然沒有工作：閘門在平台，不在客戶端設定 | 自動 |
| TC-H07 | 安全網 hooks／`hooks/confirm_launch.sh` | 功能 | 其測試檔 | 在 `v3` 與本分支各跑一次 | 結果相同；本 PR 沒改 hook 本身的行為 | 自動：`tests/confirm_launch_test.sh`（檔名依 repo 實際為準） |
| TC-H08 | 安全網「憑證不印出、不入 git、僅擁有者可讀」 | 功能 | 密碼、cookie 值、簽章金鑰 | 搜尋 git 追蹤檔、輸出、日誌 | 都不出現；金鑰檔僅擁有者可讀寫（見 TC-B06、B21、B23） | 自動 |
| TC-H09 | I.2 新檢查：「未確認的送出，MCP 工具與網頁路由都拒絕」 | 例外 | 只有 pending 申請，沒有任何人確認 | (a) 透過 MCP `launch`／`cancel` 的所有參數組合；(b) 對網頁所有路由用所有方法打；(c) 用 PAT／Bearer／偽造 cookie／錯 CSRF 打 | 每一種都沒有工作；佇列恆為 0 | 自動 |
