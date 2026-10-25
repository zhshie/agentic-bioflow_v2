---
id: web-change-password
title: 臨時密碼登入後的「設定自己的密碼」頁（/welcome）：只能改密碼，改完同一個登入直接進看板
tier: B
kinds: ui
lane: L7-web-redesign
base: v3
after: temp-password
source: 維護者 2026-10-25「照你建議」（遠端同事拿管理者發的一次性臨時密碼，第一次網頁登入必須改成自己的）
---

# web-change-password

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/web-change-password/plan.md`。**只處理本任務**。後端（`store.check_web_password`／`web_session_user`／`change_web_password`、`temp_until` 欄位、`user passwd --temporary`）已由 `temp-password`（PR #230）做好，**本任務不改 `store.py`**。介面以 `memory/dev-plans/temp-password.md` 作法 10「前端合約」與裁決三為準。

## 目標
遠端同事用管理者私下給的臨時密碼登入網頁後，只會看到一頁「設定你自己的密碼」：輸入臨時密碼、新密碼兩次，按下去就改好，並直接進入看板（不用重新登入）。用臨時密碼登入的人看不到任何 run、不能按送出。

## 維護者原話（verifier 出題用）
1. 「照你建議」（2026-10-25，回應：遠端同事沒辦法到平台主機的終端機打密碼；由管理者發一次性臨時密碼，第一次網頁登入必須改成自己的）
2. 憲法 6.1.0（他 2026-10-25 合併）：「a session that logged in with it reaches only the page that changes the password; it cannot see runs or press send」

## 範圍：檔案
- `platform/abf_platform/web.py`（新路由 `/welcome` GET／POST、登入導向、未登入導向；登入頁說明句；檔頭路由清單 docstring）
- `platform/tests/test_web_welcome.py`（新）
- `platform/tests/test_owner_binding.py`：`test_tc068_no_new_way_to_log_in` 的路由集合加 `"/welcome"`、`store.*` 名稱集合加 `"change_web_password"`（只准加這兩項，ledger 寫明理由）
- 其他把登入頁說明句或路由集合逐字釘住的既有測試：只准跟著改那一句／那一項，ledger 逐條列
- `docs/TESTING.md`（手動驗收一節：發臨時密碼 → 登入 → 改密碼 → 進看板；見完成標準）
- `docs/PLATFORM.md`（網頁路由表若有列路由，加一行 `/welcome`）
- **不准動**：`store.py`、`actions/`、`mcp_server.py`、`oauth.py`、`http_auth.py`、`cli.py`、憲法、ADR、`web_settings.py`（設定頁的入口不在本任務，見「不做」）

## 作法
1. **路由名稱＝`/welcome`**（GET＋POST）。路徑不得含 `reset|forgot|passwd|password`，`/account` 維持 404——`test_tch05`（`test_oauth_mcp.py:402-407`）**一字不改**、必須照舊通過；`web.py` 原始碼仍不得出現 `forgot`、`reset_password`、`resetpassword`、`google`、`github`、`openid`、`oidc`、`saml`、`idp`（同檔 :395-400 的字詞檢查，注意 `idp` 是子字串比對，變數名別含它）。
2. **登入 POST**（`login_post`）：`who = store.check_web_password(...)` 成功後照舊建 session、設 cookie；`who["must_change"]` 為 True → 303 到 `/welcome`，**忽略 `next`**；否則照舊 `next or HOME`。
3. **其他需要登入的路由不改判斷**：`store.web_session_user(...)` 預設對臨時密碼 session 回 None。但被導去哪裡要改：原本未登入一律 303 `/login`；改成——cookie 的 session 用 `allow_must_change=True` 查得到且 `must_change` 為 True → 303 `/welcome`；否則照舊 303 `/login`。做成一個共用小函式，所有原本 `RedirectResponse("/login", ...)` 的「未登入」分支都改用它（`logout_post` 結尾那個不算，照舊去 `/login`）。`/c/{rid}`、`/consent/{rid}` 同樣適用：臨時密碼 session 不能確認送出、不能同意 OAuth。
4. **GET `/welcome`**：
   - 沒有 cookie／session 無效 → 303 `/login`。
   - session 是一般登入（`must_change` False）→ 303 `HOME`（一般使用者改密碼仍走終端機，見「不做」）。
   - 臨時密碼 session → 200，用 `_page`（與登入頁同一個外框與樣式表）顯示：標題「設定你自己的密碼 (set your own password)」；一句說明「你用的是管理者給的臨時密碼，它 72 小時內有效、只能用來設定你自己的密碼。設好之後就用新密碼登入。」（英文對應句）；表單三欄：目前的臨時密碼（`autocomplete="current-password"`）、新密碼、再輸入一次新密碼（兩者 `autocomplete="new-password"`）；欄位旁顯示長度限制（同登入頁的 `MIN_PASSWORD_CHARS`～`MAX_PASSWORD_CHARS` 句）；隱藏欄 `csrf`＝`csrf(sid, "welcome")`；一顆按鈕「設定密碼 (set password)」；另附登出表單（沿用 `csrf(sid, "logout")`），讓拿錯人的可以離開。頁面上不出現使用者的任何 run、專案、費用。
5. **POST `/welcome`**，順序固定：
   1. `same_origin` 不符 → `foreign(request)`（同登入）。
   2. session 不是臨時密碼 session → 同 GET 的導向。
   3. `csrf` 不符 → 403，不改任何東西、不計失敗次數。
   4. 失敗次數：**沿用登入頁同一組 `by_name`／`by_ip` 與同一套 `recent`／`no_room`／`FAIL_LIMIT`／`IP_FAIL_LIMIT`**（名字用 session 的 `name`）；超過 → 429，訊息同登入頁「登入失敗太頻繁，請一分鐘後再試 (too many tries, wait a minute)」。
   5. 兩次新密碼不同 → 400「兩次輸入的新密碼不一樣 (the two new passwords differ)」，不呼叫 store、不計失敗。
   6. `old` 超過 `store.MAX_PASSWORD_CHARS` → 400，訊息比照登入頁 `too_long`，**計一次失敗**、不呼叫 store。
   7. 先計失敗（與登入同一步、無 await 間隔，理由同 :247-248 註解），再 `await run_in_threadpool(store.change_web_password, tokens_path, name, old, new, keep_sid=sid)`。
   8. `ValueError` → 400（「目前的密碼不對」那一種用 401），頁面重畫、訊息原樣顯示（store 保證雙語、不含密碼）；只有「目前的密碼不對」維持計入失敗，其他種類（長度、新舊相同、剛被改過）把剛計的那次拿回（同登入成功時的拿回寫法）。
   9. 成功 → 拿回剛計的那次 → 303 `HOME`，**cookie 不動**（`keep_sid` 讓同一個 session 繼續有效且不再是臨時的）。
   - 任何回應、日誌、例外訊息都不得含 `old`／`new`／`confirm` 的值（重畫表單時三個密碼欄一律留空）。
6. **登入頁說明句**（`_login_form`）改成：「請用你的姓名與網頁密碼登入（網頁密碼不是 AI 用的權杖；它在平台主機的終端機用 `abf-platform user passwd` 設定，或用管理者給你的一次性臨時密碼）。」——英文版若另有對應句一起改。
7. 零 JS、無 `style=`、單一樣式表、390 px 無橫捲、`Cache-Control: no-store`（沿用 `_HEADERS`）。

## 失敗先行測試（新檔 `platform/tests/test_web_welcome.py`，現在全紅）
用既有的 web 測試夾具（`w.web()`、`w.login(...)` 一類；臨時密碼用 `store.issue_temporary_password`，時間用 `clock` 參數移動）：
- W1 臨時密碼登入 → 303 `/welcome`；帶 `next=/usage` 仍是 `/welcome`。一般密碼登入照舊（`next` 有效）。
- W2 臨時密碼 session 打 `/`、`/settings`、`/usage`、`/launch`、`/c/<rid>`（GET 與 POST）、`/act/<verb>`、`/consent/<rid>` → 全部 303 `/welcome`，不洩出任何 run 名稱；沒 cookie 打同一批 → 303 `/login`（原行為）。
- W3 GET `/welcome`：臨時 session 200、含三個密碼欄與 csrf；一般 session 303 `HOME`；無 session 303 `/login`。頁面不含任何 run 名稱。
- W4 POST 成功 → 303 `HOME`；同一個 cookie 接著打 `/` 回 200 看到自己的 run；舊臨時密碼再登入失敗、新密碼登入成功且 `must_change` False。
- W5 錯誤分支各一：兩次新密碼不同（400、store 未被呼叫、未計失敗）；目前密碼錯（401、計失敗）；新舊相同、新密碼太短（400、訊息為 store 的雙語句、未計失敗）；`old` 太長（400、計失敗）；csrf 錯（403、密碼未變）；跨來源（同登入的 foreign 回應）。
- W6 連續錯 `FAIL_LIMIT` 次後 → 429；且與登入頁共用計數（先在 `/login` 錯 N 次，再在 `/welcome` 錯，總數到上限即 429）。
- W7 臨時密碼過期（clock 移過 72 小時）→ 帶著那個 session 打 `/welcome` 回 303 `/login`。
- W8 任何回應本文、`Location`、設下的 cookie 與 caplog 都不含三個密碼欄的值。
- W9 `test_tch05` 原封通過；`/welcome` 不含禁字；`web.py` 原始碼字詞檢查照舊通過。
- W10 登出表單在 `/welcome` 可用（臨時 session 能登出，之後 `/welcome` 303 `/login`）。

## 完成標準
- 全套測試綠（含 `test_tch05`、`test_tc068` 只加兩項）。
- `docs/TESTING.md` 新一節手動驗收：①終端機 `abf-platform user passwd <name> --temporary` 記下密碼 ②瀏覽器登入 → 落在 `/welcome` ③直接打 `/` 會被帶回 `/welcome` ④設新密碼 → 進看板 ⑤登出再用新密碼登入成功、臨時密碼失敗。
- 截圖（developer-agent 拍）：`/welcome` 1440／390 各一張，外加一張錯誤狀態（兩次新密碼不同）。

## 不做
- **設定頁的「改密碼」入口**（一般使用者在網頁改自己的密碼）：憲法 6.1.0 寫的是「web password is still set only at a real terminal」，網頁上只開放臨時密碼的那一次。要開放一般使用者在網頁改，是憲法層級的決定，另案問維護者。設定頁不動。
- 忘記密碼、寄信重設、管理者在網頁發臨時密碼：都不做。
- 不改 `store.py` 與 CLI。

## 裁決
（尚無）

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
