---
id: pending-confirm-restart
title: 平台重啟後，等待中的送出確認連結要仍可使用（先用測試查證，不先改程式）
tier: C
kinds: backend
risk: M
lane: L43-pending-confirm-restart
branch: fix/pending-confirm-restart
base: v3
source: memory/handoff/2026-11-01-2104.md 第 20、24 行；memory/daily/2026-10-31.desktop-7j5l5bj.md 第 24 行 backlog「重啟後 pending 確認失效（未驗證）」；11-01 ampliseq r7 確認連結在重啟後失效、需重新產生
---

# pending-confirm-restart

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/pending-confirm-restart/plan.md`。**只處理本任務**。懷疑中的 bug 尚未驗證：先寫測試，測試的結果決定要不要改程式。

## 目標
平台升版或重啟（serve、web、mcp 行程重開）時，同事手上等待中的送出確認連結（`/c/<id>`），只要仍在 10 分鐘有效期內、由同一位使用者開啟，就必須照常顯示並可按「送出」；超過有效期則顯示一句明確、正式書面語的逾時說明。目前無法確定 11-01 的失效是真的 bug（重啟弄丟了簽章金鑰或待確認紀錄），還是重啟花了超過 10 分鐘而依設計逾時，所以本任務先用測試分辨，再決定要不要改。

## 維護者原話（verifier 出題用）
本任務的依據是維護者在派工說明裡的要求與 11-01 的實際現象，逐字如下（前端 session 記錄，見 handoff）：
1. 「平台重啟後 pending 確認連結失效（未驗證，先寫測試確認）。」（handoff 2026-11-01-2104 第 20 行）→ 每條案例都要先證明現象存在與否；不得未經測試就改程式。
2. 「ampliseq r7：他還沒回要不要重送；要的話請 lab-agent 重新產生確認連結（舊連結因重啟失效）。」（同檔第 24 行）→ 重啟後同一位使用者、仍在有效期內的連結要可用。
3. 「MCP launch 確認連結 10 分鐘過期，必須他本人按；同參數再呼叫一次 launch 才拿到 job_id。」（同檔第 30 行）→ 10 分鐘有效期是設計，不改；過期後要有明確說明與補救（重新送出）。
4. 維護者 2026-10-27 的用字裁示（DESIGN.md「用字」）：「一樣要注意中文的顯示不能口語」→ 逾時句為正式書面語，只陳述狀態與補救。

## 範圍：檔案
- 新測試：`platform/tests/test_pending_confirm_restart.py`（唯一必改的檔案；沿用 `human_harness.World` 的 `w.web()`、`w.login()`、`w.launch(caller=...)`，見 `test_web_login.py` 的 `w` fixture 與 `pending_for`）。
- 僅當測試證明確有 bug 時才可動：
  - `platform/abf_platform/web.py`（`_signing_key`、`create_app`、`state_page`、`confirm_get`、`confirm_post`）。
  - `platform/abf_platform/confirm.py`（`create_pending`、`approve`）。
  - `platform/abf_platform/store.py`（`web_session_user`、`create_web_session`）。
  - `platform/abf_platform/cli.py`（`serve`／`mcp` 取得資料資料夾與金鑰位置的那幾行，第 55～74、525～533 行附近）。
  - 若有資料結構變動：`platform/abf_platform/store.py` 的 migration 與其測試；本計畫預期**不需要 migration**（金鑰是資料夾中的檔案，待確認紀錄本來就在 SQLite）。
- 被釘住的既有測試（只准增加、不刪不放寬；改到任何一句字串前先確認）：
  - `platform/tests/test_web_nano4_path.py` 第 396 行（`"10 分鐘"`、`"請重新送出。"`、`"回到 AI"` 不得出現）與第 396～398 行的 410／409 狀態碼斷言。
  - `platform/tests/test_clean_page.py` 第 125～126 行（`"該申請已逾時（7 天），不會自動重新提出。"`，且頁面不得含 `"10 分鐘"`）。
  - `platform/tests/test_web_confirm_plain.py` 的 `test_tc019_tc020_expired_and_void_pages_have_neither`（逾時頁沒有 `<details`、沒有 `<button`）。
  - `platform/tests/test_web_login.py` 的 `test_tcb21_the_signing_key_is_in_the_data_folder_owner_only_and_survives_a_restart`（金鑰在資料夾、僅擁有者可讀、重啟後 cookie 仍有效、不在 git）。
  - `platform/tests/test_web_wording_sweep.py`（所有中文字串不得含 DESIGN.md「用字」的禁用詞）。
  - 列出全部：`git -C <repo> grep -n -E "已逾時|10 分鐘|申請已逾時|has expired" origin/v3 -- platform/tests docs`。

## 作法
已讀的 v3 事實（executor 以實際程式為準重新確認）：
- 簽章金鑰（簽 cookie 與 CSRF token）**已經是持久的**：`web._signing_key(folder)` 在 `Path(platform_path).parent`（與資料庫同一資料夾）寫入 `web_signing.key`，只建立一次、`0600`、不印出；不是每個行程隨機。所以「每行程隨機密鑰」這個假設在 v3 上預期不成立。
- 登入 session 在 `tokens.db` 的 `web_sessions`（存雜湊，12 小時），待確認紀錄在 `platform.db` 的 `confirmations`（`state='pending'`、`expires_at = created_at + 600`）。兩者都在資料夾裡，行程重啟不影響。
- 因此重啟後連結失效，只剩這幾種可能，測試要逐一分辨：
  1. 重啟花了超過 10 分鐘，依設計逾時（頁面該顯示「該申請已逾時（10 分鐘）。請重新送出。」）。
  2. 升版腳本讓新行程指向**不同的資料資料夾或不同的 `--state`／`--tokens` 路徑**（於是新金鑰、新資料庫、找不到申請）。這屬部署問題；若測試證明程式在「同一資料夾」下沒問題，就只在回報裡寫出這個推論，不改程式。
  3. 瀏覽器端：cookie 為 `SameSite=Strict`，從別的網站（Claude Desktop）點連結時不帶 cookie，會先顯示登入頁（這是既有設計，登入後以 `next` 回到 `/c/<id>`）；測試要確認「重啟後無 cookie、重新登入」這條路也能到達並送出。
  4. MCP 端：重啟後同樣內容再呼叫 launch，`create_pending` 在剩餘時間多於 `REUSE_MIN_SECONDS`（60 秒）時回傳同一個申請；否則開新的。測試確認兩種都正確。
- 若測試證明真有 bug（例如金鑰檔在某種啟動方式下沒寫進資料夾、或啟動時重新產生金鑰）：修成「金鑰存放在部署的設定／資料區（僅擁有者可讀、不印出、不進 git，見 Safety Net 的憑證規則）」，沿用 `_signing_key` 的原子寫入；不得把金鑰寫進日誌、回應、測試輸出或 git。
- 逾時句：v3 已有「該申請已逾時（10 分鐘）。請重新送出。」且被上列測試釘住，語氣已是正式書面語、有狀態與補救，**不改句子**。若維護者要求改成「此確認已過期，請重新送出。」之類，須同步改上列被釘住的測試，這屬另一個任務（見「不做」與回報中的問題）。
- 不改 10 分鐘（`confirm.PENDING_SECONDS = 600`）、不動 dev mode。

## 失敗先行測試（`platform/tests/test_pending_confirm_restart.py`）
「重啟」＝以同一組資料夾與檔案（`w.ip.index`、`w.ip.tokens`、`w.ip.state_db`）再呼叫一次 `w.web()`（新的 app 實例），舊實例丟棄。這些案例在 v3 上可能已綠；已綠的案例就是回歸測試，仍要留下。
1. `test_restart_keeps_pending_and_cookie`：ann 建立 pending（`w.launch(caller=ann)`）並登入；重啟後用**同一個 cookie** `GET /c/<id>` → 200、有 `name="csrf"` 的送出表單；`POST /c/<id>`（用重啟後頁面上的 csrf）→ 200「已送出。工作編號」，`jobs` 恰有一筆 launch_nextflow、`confirmations.channel='PAGE'`。
2. `test_restart_then_fresh_login_can_confirm`：同上，但重啟後用**全新、沒有 cookie 的 client** 先 `GET /c/<id>` 得到登入頁（含 `next=/c/<id>`），登入後 `GET /c/<id>` 有表單，可送出。
3. `test_restart_keeps_the_signing_key`：重啟前後 `web_signing.key` 內容相同、資料夾裡仍只有一個金鑰檔、重啟前取得的 CSRF token 在重啟後的 POST 仍被接受；金鑰字串不出現在任何回應文字、頁面或 pytest 輸出。
4. `test_restart_other_user_still_refused`：bob 登入後開 ann 的 `/c/<id>` → 403，重啟前後都是；`POST` 也是 403 且 `jobs` 仍為空（跨使用者，讀與寫各一條）。
5. `test_expired_after_restart_says_so`：把 `w.clock.t` 往前移 `confirm.PENDING_SECONDS + 1` 秒（重啟後的 app 用同一個 clock）；`GET` 顯示「該申請已逾時（10 分鐘）。請重新送出。」且沒有 `<button`；`POST` 回 410、含「未送出：」與「請重新送出。」，`jobs` 仍為空；該列 `state='void'`、`void_reason='expired (逾時)'`。邊界：剛好 599 秒仍可送出。
6. `test_same_request_again_after_restart_reuses_or_renews`：重啟後以相同參數再呼叫一次 launch——剩餘時間多於 60 秒時回同一個 id；少於 60 秒時是新 id（舊的仍在、到期後作廢）。
7. `test_restart_pointing_elsewhere_is_the_symptom`（只描述現象、不修）：用**另一個空資料夾**建立新 app，開舊連結 → 404「無此申請」（以及無有效 cookie）；測試名與註解寫明這是「資料夾不同」的部署問題，不是程式 bug；斷言錯誤頁不含堆疊、內部路徑或金鑰。
8. `test_no_secret_in_logs_or_pages`：案例 1～5 的頁面與 `caplog` 都不含金鑰檔內容與 cookie 簽章。

## 完成標準（done when）
- 上面每條測試存在並綠；`tests/run_all.sh --timeout 900` 全綠（環境紅依 README 通例）。
- **結果有兩種，擇一寫進 ledger**：
  - 若案例 1～6 在 v3 就已綠：結論是「v3 沒有重啟失效的 bug」，**只保留回歸測試**，不改任何程式；ledger 寫出推論（超過 10 分鐘依設計逾時，或升版時資料夾／路徑不同），並請 developer-agent 到正式機核對升版腳本實際使用的資料資料夾（不讀金鑰內容）。
  - 若有案例紅：只做最小修正讓它綠；金鑰持久化於部署的設定／資料區、僅擁有者可讀、不印出、不進 git；`git diff --stat` 貼進 ledger；有資料結構變動才附 migration。
- 既有被釘住的字串與測試沒有被改動（diff 只新增）。
- 專長守則檢查一行寫進報告。

## 環境事實
- `PENDING_SECONDS = 600`（confirm.py:23）；`approve` 的逾時回傳 `expired` 並把該列作廢（confirm.py:146～148）；網頁逾時頁在 web.py 的 `state_page`（約 452～454 行）。
- 簽章金鑰：web.py `KEY_FILE = "web_signing.key"`、`_signing_key`（約 105～133 行）、`create_app` 取 `Path(platform_path).parent`（約 182 行）。
- cookie 為 `SameSite=Strict`、`httponly`，12 小時（`store.WEB_SESSION_SECONDS`）。
- 連結來源：`actions/__init__.py` 約 1315 行以 `web_base_url`（存在資料庫 meta，由 `web.create_app(public_url=...)` 寫入）組成 `/c/<id>`；重啟後只要 web 行程以同一資料庫帶 `--public-url` 啟動，連結位址不變。
- 既有重啟案例：`test_web_login.py::test_tcb21_...`（金鑰與 cookie）；本任務補上「待確認紀錄」與「逾時」。
- 11-01 實際現象只有紀錄、沒有 log；executor 不必讀正式機。

## 不做
- 不改 10 分鐘有效期（`PENDING_SECONDS`）、不改 clean_work 的 7 天。
- 不動 dev mode。
- 不改網頁逾時句子（已被既有測試釘住；若要改成「此確認已過期，請重新送出。」須另開任務並同步改測試）。
- 不新增「重啟後自動延長有效期」之類的機制。
- 不讀、不印、不提交任何金鑰或 cookie 值。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
2. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值，條數 ≤ 20。
3. 先證明再修：未有紅的測試不得改 `platform/abf_platform/` 下任何檔案；閱卷以 `git diff --stat` 核對。
4. worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明；落地前 `git merge origin/v3`。

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
