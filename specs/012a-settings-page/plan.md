---
id: 012a-settings-page
title: 設定頁補完（第一片）：個人（逐步模式、開發模式）可存可改，醒目標示，憑證只顯示「已設定」
tier: B
kinds: ui
lane: L6-web
branch: feat/012a-settings-page
base: v3
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 2 第 145 行；DESIGN.md 畫面 2、12；docs/ROADMAP.md 第 3 階段 012a
---

# 012a-settings-page

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/012a-settings-page/plan.md`。**只處理本任務（第一片）**。
> 2026-11-04 查 origin/v3（069c50e0）：`GET /settings` 與 `platform/abf_platform/web_settings.py` 已存在（settings-page、settings-register-pipeline、settings-pick-installed、PR #290 settings-ce-table-mobile）：運算環境表、登記管線、使用前檢查都做完了；`specs/` 下沒有 `012a-*`；「個人」「AI 模型金鑰」「憑證」三段仍是灰字「之後開放」。所以 012a 不是整頁重做，只補這三段。

## 目標
設定頁的「個人」段讓使用者自己開關兩個旗標：逐步模式、開發模式，存在平台（每人一份），開著開發模式時整個畫面頂端有醒目標示；「憑證」段只顯示權杖「已設定／未設定」（不顯示值、不顯示雜湊）。使用者看得到自己現在是什麼模式，012b-2（逐步引導）與 012d（費用頁，開發模式國網不限 SU）才有東西可讀。

## 維護者原話（verifier 出題用）
DESIGN.md「Maintainer's words」第 9 點，逐字：

> 「不需要Jev "開關"，只要在設定讓使用者可以放金鑰。」

DESIGN.md 第 2 點：

> 「系統設定先。然後右側有對話框，直接對話系統就會引導使用者快速上手建專案，選pipline條參數等等」

DESIGN.md 畫面 12 逐字：

> **Settings**: compute environments, credentials (token, 12 h), Secrets (AI model key, Jev key optional; browser only), Personal (step-by-step mode, development mode); Operator panel and Roles as dashed "coming later".

總表（PLAN 第 145 行）逐字：

> **012a `settings-page`**：運算環境／憑證（只顯示「已設定」）／個人（逐步模式、開發模式＝國網不限 SU、畫面醒目標示）／模型金鑰只存瀏覽器。DESIGN.md 畫面 2、12。

ROADMAP 012：`no NCHC SU cap in dev mode`。本片只存旗標與標示，不做「不限 SU」的判斷（012d）。

## 範圍：檔案
- `platform/abf_platform/web_settings.py`：新 `_personal(t, ...)`（取代 `_rest` 裡的「個人」那一段）、`_credentials` 改為「已設定／未設定」，新增中英字串、表單。
- `platform/abf_platform/web_board.py`：只動兩處——`SETTINGS` 常數（:32，「個人」的 `set_step`、`set_dev` 兩個灰字項目拿掉）與 `_frame`（:846）的頂端標示（開發模式醒目條）。
- `platform/abf_platform/web.py`：**要改**。新增 `POST /settings/personal`（兩個開關各一個表單欄，CSRF 用新 purpose `settings-personal`，同 `inventory_post` 的寫法）、`settings_page` 把旗標交給 render、`Route` 表加一行、檔頭註解的路由清單加一行。只動 /settings 一帶（:1103–1230 與 :1323–1326 的 Route 表）；與其他 web.py 任務（resume 編輯、其他 L6 車道）相交，落地前 `git merge origin/v3`，衝突只保留雙方新增。
- `platform/abf_platform/store.py`：`users` 表加兩欄 `step_mode INTEGER`、`dev_mode INTEGER`（用 :337 一帶既有 `ALTER TABLE … ADD COLUMN` 的遷移寫法），加 `user_prefs(tokens_path, user_id)` 與 `set_user_pref(tokens_path, user_id, key, on)`，鍵只收 `step_mode`、`dev_mode`。
- `platform/abf_platform/actions/__init__.py`：加讀取動作 `get_my_settings` 與寫入動作 `set_my_setting`（寫入走 PAGE 通道，不是 MCP 工具，仿 `register_site_pipeline`）。
- `platform/tests/test_web_parity.py`：`WEB_ONLY` 補 `set_my_setting`（理由寫「網頁專用，個人旗標，無 MCP 工具」）、`get_my_settings`；`OWED` 不動。
- `platform/tests/test_actions_layer.py`：:707 的 `PAGE_WRITE_NAMES` 補 `set_my_setting`（該測試要求頁面寫入動作無頻道時拒絕）。
- 新測試：`platform/tests/test_web_settings_personal.py`。
- 被釘住、需同步修改預期的既有測試（只改預期，不刪案例，ledger 逐條列）：
  - `platform/tests/test_web_settings.py`：:296（「逐步模式」「開發模式」仍須出現，但不再是灰字；改成斷言為開關）、:266（憑證段現釘 `建立或撤銷權杖 之後開放`，該灰行**保留**，所以只加「已設定／未設定」斷言，不刪）、:105／:172（`使用前檢查` 第 4 項 AI 金鑰仍 `—`＋「之後開放」，**不變**）、:89（`<h2>` 順序七段**不變**，不得增減段）、:330（無 `<script`、無 `style=`、只有一個 `<style>`）。
  - `platform/tests/test_web_board.py`:962（`<h2>` 七段順序不變）、:317（左欄 `之後開放` 是左欄項目，不受影響）。
  - `platform/tests/test_web_v2_skeleton.py`:202（左欄「設定」連結與「之後開放」）、:404（全頁無 `<script`、無 `style=`、單一 `<style>`）。
- 若新增 CSS：只加進既有那一個 `<style>`（`web.py` 的 style-src 是它的 sha256，改 CSS 會變雜湊，測試會自動算；不得另開 `<style>` 或 inline style）。
- 不碰：`web_launch.py`、`web_cost.py`、`web_finished.py`、`web_upload.py`、`static/*`、其他計畫檔。

## 作法
1. **個人段（資料）**：每人兩個布林，預設 `step_mode = 1`（逐步，新手預設）、`dev_mode = 0`。`get_my_settings` 回 `{"step_mode": bool, "dev_mode": bool}`；只讀自己。`set_my_setting(key, on)` 只准這兩個鍵，其他鍵拒絕並回一句白話；無頻道（非 PAGE）拒絕，同 `register_site_pipeline` 的 K01 寫法。
2. **個人段（畫面）**：「個人」`<h2>` 下兩列，每列＝標籤＋狀態字（`開`／`關`，英文 `On`／`Off`）＋符號（開 `✓`、關 `—`）＋一個按鈕（`開啟`／`關閉`，英文 `Turn on`／`Turn off`）。每列一個 `<form method="post" action="/settings/personal">`，隱藏欄 `csrf`、`key`、`on`、`lang`；伺服端重導回 `/settings?notice=personal-saved`（沿用既有 `notice` 機制與 `make_flash` 的 `NOTICES`），成功句寫「已儲存。」。不用 JS（CSP `default-src 'none'`，頁面禁止 script）。
3. **確認頁規則**：旗標是使用者自己的偏好，不影響他人、不啟動工作、不花錢，一鍵即存，**不經確認頁**。唯一例外見裁決 B：開發模式。
4. **開發模式的醒目標示**：`dev_mode` 開著時，`_frame` 在 masthead 下方畫一條橫幅，文字「開發模式已開啟：國網運算不限制 SU」（英文 `Development mode is on: NCHC compute has no SU limit`），符號 `!`、文字、顏色三者並用；只用 DESIGN.md tokens，不新增顏色（沿用既有警示 token），不用左側色條（Impeccable side-tab）。橫幅出現在**每一頁**（`_frame` 共用），因為「畫面醒目標示」。本片只標示，不改任何 SU 判斷。
5. **憑證段**：標題不變。沿用現有 `abf-platform token new` 提示句與灰行「建立或撤銷權杖／之後開放」。新增一行：`存取權杖：已設定`／`未設定`（符號 `✓`／`—`＋文字），依 `store` 內該使用者是否有未撤銷的權杖。**不讀、不顯示權杖值與雜湊**（ledger 證明頁面 HTML 內無權杖字串，沿用 test_web_settings.py :257 TC-034 的檢查）。
6. **AI 模型金鑰（本片不做輸入）**：段落與灰行維持；因為「只存瀏覽器」要 JS／localStorage，而 /settings 的 CSP 禁止 script，見裁決 A。本片這段**一個字都不改**。
7. 中英：所有新字進 `STRINGS["zh"]`、`STRINGS["en"]` 兩邊；英文頁不得出現中文字。
8. 左欄、右欄不動；使用前檢查四步不動。

## 裁決（維護者）
**A. 模型金鑰「只存瀏覽器」要 JS，與 CSP 衝突。** 現況 `/settings` 的 CSP 是 `default-src 'none'; style-src <hash>; form-action 'self'`，頁面測試釘死「無 `<script`」（test_web_settings.py :330、test_web_v2_skeleton.py :404）。選項：(1) 本片不做，另開 012a-2 在 `/settings` 放寬成「一個 hash 的 script」並改測試；(2) 本片一併做（範圍加 `web.py` 的 header、`static`，風險升 L）。**預設：選 (1)**，本片金鑰段不動。
**B. 開發模式要不要確認頁。** 預設不要（見作法 3）；若要，是兩步（勾選→確認頁→存），仿 `/settings/pipelines/confirm`，範圍多一個 render_confirm，測試案例加倍。預設不要。
**C. `get_compute_env`、`list_agents` 兩個 OWED（test_web_parity.py :48 標 012a）。** 預設**不在本片**（見「不做」，012a-2）；若要一起做，`web.py` 要多兩個唯讀路由、`OWED` 縮小（測試 `test_tcs07_owed_is_written_out` 要改）。
**D. 逐步模式現在影響什麼。** 本片只存旗標、只顯示；012b-2 才讀它。預設 `step_mode` 開。

（以上若維護者無異議，executor 依預設做；任何一條改答案要重跑本任務 `reuseContract:false`。）

## 六項必填檢核（ui 計畫固定段）
1. 確認頁規則：個人旗標與憑證顯示不經確認頁（作法 3、裁決 B）。
2. 失敗狀態：寫入被拒（鍵不認得、CSRF 錯、未登入、無頻道）→ 頁內一句白話，欄位值不丟；寫入失敗回 400，同 `fail` flash。
3. 提示句位置：成功／失敗句在頁面頂端 flash 區（`_flash(t, flash, None)` 既有位置），不新增段落。
4. 要改的舊測試：見「範圍：檔案」。
5. 手機寬度：兩列用 `.card.sec` 內的簡單列，按鈕點擊目標 ≥ 既有按鈕高度，不新增橫向捲動；`scripts/dev/check_settings_mobile.py` 存在就要跑。
6. 空狀態：新使用者（兩欄 NULL）= 預設值；沒有權杖 = 「未設定」。

## 失敗先行測試
新檔 `test_web_settings_personal.py`，沿用 `test_web_settings.py` 的 `pane`、登入與假站台輔助。先寫、在未修的 `v3` 上會紅：
- `test_personal_section_has_two_switches`：`GET /settings` → 「個人」段含「逐步模式」「開發模式」，各有符號＋「開／關」＋按鈕；不再有灰字 `之後開放`；`<h2>` 順序仍是七段。
- `test_defaults_step_on_dev_off`：新使用者 → 逐步＝開、開發＝關。
- `test_turn_dev_on_persists_and_shows_banner`：POST `/settings/personal`（key=dev_mode,on=1，合法 csrf）→ 302 到 `/settings?notice=personal-saved`；再 GET → 開發模式為開；**任一頁**（`/`、`/settings`、某 run 頁）含橫幅「開發模式已開啟：國網運算不限制 SU」與 `!`。
- `test_banner_not_shown_when_off`。
- `test_banner_is_per_person`：兩個使用者，A 開、B 的頁面沒有橫幅。
- `test_post_refused_cases`：錯 csrf／未登入／key=`role`（未知鍵）／on=`maybe` → 都不寫入；回 400／重導且旗標不變。
- `test_set_my_setting_refuses_without_page_channel`：從非 PAGE 頻道呼叫動作 → 拒絕（併入 test_actions_layer 的 `PAGE_WRITE_NAMES`）。
- `test_english`：`?lang=en` → `On`／`Off`／`Turn on`／`Development mode is on: NCHC compute has no SU limit`；`mid()` 不含中文字。
- `test_credentials_say_set_or_not`：有權杖 → `已設定`；無 → `未設定`；頁面不含權杖值或其雜湊；灰行「建立或撤銷權杖 之後開放」仍在（TC-034 不退步）。
- `test_ai_key_section_unchanged`：「AI 模型金鑰」灰行與「金鑰僅儲存於您的瀏覽器，不會傳送至平台。」原樣。
- `test_no_script_no_inline_style`：整頁無 `<script`、無 `style=`、只有一個 `<style>`、CSP 標頭不變。
- `test_state_not_by_colour_alone`：開／關列、橫幅的 HTML 同時含符號與文字。
- parity：`test_web_parity.py` 全套仍綠（新動作在 `WEB_ONLY`；`OWED` 集合不變）。

## 完成標準（done when）
新測試全綠；上列既有測試改預期後綠；整套 `tests/run_all.sh --timeout 900` 綠（背景跑＋等待）；`git diff --stat` 只有「範圍：檔案」列的檔；ledger 貼 diff stat、逐條被改的既有斷言、`store.py` 遷移對舊資料庫仍可開的證明（舊 `users` 表→新欄 NULL→預設值）；PR 附設定頁與開發模式橫幅（1440／390 × zh／en）截圖（B 級，由維護者看）。

## 環境事實
- 已有：`web_settings.render`（:343）／`render_middle`（:334）、`_rest`（:303，個人／營運者後台／角色三段，用 `web_board.SETTINGS[3:]`）、`_credentials`（:293）、`_keys`（:298）；`web.py` `settings_page`（:1103）、`settings`（:1114）、Route 表 :1323–1326。
- `web.py` 的 CSP：`default-src 'none'; style-src <sha256>; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`（:86–88）。
- `users` 表：`id, name, lab, created_at, disabled_at, password_hash, temp_until`（store.py :100）；遷移寫法 :337–352。
- 磁碟事實：本機 `git fetch` 對 `refs/remotes/origin/v3` 有 lock 錯（2026-11-04），本計畫以 `origin/v3`＝069c50e0 為準；開工前先 `git fetch` 成功再 `git merge origin/v3`。
- PITFALLS 已查（`docs/PITFALLS.md`，origin/v3）：條目 Touches 欄沒有 `web.py`／`web_board.py`／`web_settings.py`／`test_web_*` 的相符項；提到 settings 的條目都是 `settings.sh` 與 env.yaml（`tests/settings_test.sh`），與網頁設定頁無關，無相符項。`docs/solutions/` 不存在。

## 不做
- 不做模型金鑰輸入框與 localStorage（裁決 A，012a-2）；使用前檢查的 AI 金鑰第 4 步維持「之後開放」。
- 不做 `get_compute_env`、`list_agents` 的網頁路由（裁決 C，012a-2；`OWED` 不縮）。
- 不做開發模式的「不限 SU」判斷與費用顯示（012d）；不做逐步模式的實際行為（012b-2）。
- 不做權杖建立／撤銷、運算環境新增／修改、營運者後台、角色（維持灰字）。
- 不動左欄、右欄、使用前檢查、登記管線表單、CSP。

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
- **實際跑起來看（ACCEPTANCE，2026-11-03 加）**：用 `webapp-testing` 的 `with_server.py` 把真正的應用程式起起來，再用 Playwright 驗。腳本路徑 `G:/我的雲端硬碟/謝馬爾/.claude/skills/webapp-testing/scripts/with_server.py`，**先跑 `--help`** 看用法（把它當黑盒子用，不要先讀原始碼）；啟動指令與通訊埠寫在計畫裡。
  - repo 已有 `scripts/ui_check.py` 就直接跑它：1440／390 寬 × zh／en 共 4 張截圖，加 axe-core 無障礙掃描；**axe 出現 serious 或 critical 一律 FAIL**。
  - repo 還沒有 `ui_check.py`：verifier 自己用 Playwright（經 `with_server.py`）拍同樣 4 張截圖；axe 沒跑就標 **axe：UNVERIFIED**，並寫明缺什麼。
  - 截圖只能存到 repo 之外或 `.gitignore` 排除的資料夾，**絕不存進 Drive 工作區**；報告只貼路徑與張數。
  - 起不了應用程式（缺依賴、埠被占）標 UNVERIFIED 並寫明需要什麼，不改以靜態 HTML 當作通過。
