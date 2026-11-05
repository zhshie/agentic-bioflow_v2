# 測試案例：下游階段 Studios 開新分頁版（studios-new-tab）

**規格**：`specs/studios-new-tab/plan.md`（本任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「成功分析」指狀態為成功（succeeded）的分析；「下游頁」指 `/?run=<id>&stage=downstream`；「占位」指灰字「之後開放」（英文 Coming later）。
全部「自動」案例的測試寫在 `platform/tests/test_web_downstream.py`（沿用 `test_web_bugs_a.py` 的 `w`、`seed`、`login`、`pane` 輔助），每個測試在註解寫上它的 TC 編號。
條數依計畫「裁決 3」限制在 20 條以內，所以同一頁上的幾項檢查合併在同一列；驗收時逐項都要成立，缺一項該列即不通過。

## User Story 1 — 成功的分析進入下游階段，看得到可用內容（優先度 P1）

維護者原話 1：「如果都可以，要把下游分析放下一個目標進度了」→ 成功的分析進入下游階段要看得到內容，不再是「之後開放」。
維護者原話 2、3：Studio 只在使用者自己的電腦或雲端環境執行，不在 NCHC 登入節點（決定 11 選項 A；ADR 0010）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 1、2、3；作法 2（畫面）；失敗先行測試 1 | 功能 | 已登入的使用者 ann 有一個成功分析；網址不帶 `studio` 參數（空欄位狀態）；中文介面 | 開 `/?run=<id>&stage=downstream` | 中欄是一張 `<section class="card">`，標題「下游」；**不含** `<span class="later">`；有一句說明「下游分析於使用者自己的電腦或雲端環境進行，平台不代為執行，也不在 NCHC 登入節點啟動」（正式書面語）；有一句說明 `http://localhost` 只在瀏覽器與 Studio 在同一台電腦時才連得上；有一個 `method="get" action="/"` 的表單，含隱藏欄位 `run`（值為該分析 id）與 `stage=downstream`，以及一個 `type="url"`、`name="studio"`、預設空白的欄位與按鈕「開啟連結」；表單不含 CSRF 欄位；欄位空白或只有空白字元時，頁面沒有 `role="alert"` 句、沒有 `target="_blank"` 連結 | 自動：`test_downstream_succeeded_shows_section_not_placeholder` |
| TC-002 | 原話 5；作法 2、5 | 功能 | 同 TC-001，改用 `?lang=en` | 開同一頁 | 版面結構與 TC-001 相同（同樣的表單、欄位、按鈕、兩段指令）；表單多一個隱藏欄位 `lang=en`；整頁中欄文字無任何中日韓字元；沒有「之後開放」也沒有 `Coming later` | 自動：同上（英文版斷言，含 `no_cjk`） |
| TC-003 | 作法 2（兩段可複製指令） | 功能 | 同 TC-001 | 看下游頁中的指令區（`<pre class="reason">`） | 有兩段字面文字：Jupyter 指令含 `jupyter lab --notebook-dir "<本機結果資料夾>"`；RStudio 指令含 `docker run --rm -p 127.0.0.1:8787:8787 -e DISABLE_AUTH=true -v "<本機結果資料夾>":/home/rstudio/results rocker/rstudio`；RStudio 只綁 `127.0.0.1`（沒有 `0.0.0.0`，也沒有只寫 `-p 8787:8787`）；`<本機結果資料夾>` 保持為使用者要自己填的佔位文字，不是平台的路徑 | 自動：同上 |
| TC-004 | 作法 2（結果資料夾，讀得到） | 功能 | 成功分析，其輸出資料夾讀得到（測試用既有 fixture，與 `finished` 階段相同的讀法） | 開下游頁 | 「結果資料夾」處顯示站台上的該資料夾路徑；並有一句說明「先把這個資料夾複製到自己的電腦或雲端環境」；頁面讀取輸出時不排隊任何工作（只看不排隊） | 自動：`test_downstream_succeeded_shows_section_not_placeholder`（路徑斷言）；不排隊由 TC-011 的資料庫不變證明 |
| TC-005 | 作法 2（結果資料夾，讀不到） | 例外 | 成功分析，其輸出資料夾讀不到 | 開下游頁 | 回應 200、不報錯；「結果資料夾」處顯示「尚未讀取輸出」，並有連到既有「查看輸出」（`results`／`outputs` 分頁）的連結；表單與指令照常出現 | 自動：`test_downstream_succeeded_shows_section_not_placeholder`（讀不到的案例） |
| TC-006 | 作法 2（非成功仍占位）；「不做」：不動非成功分析的占位文字；失敗先行測試 2 | 不在範圍 | 一個失敗分析、一個執行中分析 | 各開其下游頁，中文與英文各一次 | 仍是 `<span class="later">之後開放</span>`（英文 `Coming later`）；頁面沒有 `name="studio"` 欄位、沒有指令區 | 自動：`test_downstream_nonsucceeded_keeps_placeholder` |

## User Story 2 — 貼上自己 Studio 的網址，在新分頁開啟（優先度 P1）

維護者原話 3（ADR 0010 Decided 第 3 點）：「Studio screen: option A, with the new-tab button as the fallback. … If it fails, the Studio opens in a new tab.」→ 連結為 `target="_blank"`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | 原話 3；作法 2（通過驗證）、3（長度 ≤ 300）；失敗先行測試 3 | 功能 | 成功分析的下游頁 | 分別帶 `&studio=http://localhost:8787/`、`&studio=https://rstudio.example.org/s/abc`、一個剛好 300 字元的 `https://` 網址 | 每次頁面都恰有一個 `<a href="<該網址>" target="_blank" rel="noopener noreferrer">在新分頁開啟 Studio</a>`；同時以純文字再印出該網址；並有一句「此網址由使用者自行提供，平台不儲存、不檢查其內容。」；欄位內預填或不預填均可，但連結的 `href` 必須與貼入的網址完全相同 | 自動：`test_studio_link_opens_new_tab` |
| TC-008 | 計畫前端限制（作法 6、7）；失敗先行測試 3、9、10 | 功能 | 同 TC-007，並另測不帶 `studio` 的成功分析下游頁 | 開帶合法網址的下游頁與空欄位的下游頁，檢查原始 HTML 與回應標頭 | 整頁沒有 `<script`、`<iframe`、`style=`；除使用者貼的那一個 `<a>` 外，沒有任何外部（`http://`、`https://`、`//`）的 `href`／`src`；成功分析下游頁沒有任何 `<meta http-equiv="refresh">`（兩種狀態都沒有，因為重新整理會丟掉正在輸入的欄位）；回應的 CSP 標頭與首頁逐字相同（`default-src 'none'; form-action 'self'; frame-ancestors 'none'`）；`web_board.STYLE` 的 sha256 等於 `test_results_files.py` 的 `STYLE_SHA256` | 自動：`test_studio_link_opens_new_tab`、`test_no_refresh_on_succeeded_downstream`、`test_style_untouched_and_csp_same` |
| TC-009 | 作法 2（未通過驗證）、3（驗證規則）；失敗先行測試 4 | 例外 | 成功分析的下游頁，中文與英文各測 | 逐一帶入這些 `studio` 值：`javascript:alert(1)`、`JaVaScRiPt:alert(1)`、`data:text/html,x`、`file:///etc/passwd`、`ftp://x`、`//evil.example`、`http://user:pw@host/`、`http://h/?token=abc`、`http://h/?PASSWORD=x`、`http://h/?key=abc`、`http://h/?secret=abc`、301 字元網址、含空白的網址、含換行的網址、`http://`（無主機） | 每一個都：頁面**沒有** `target="_blank"` 連結；有一個 `<p class="bad" role="alert">`，內含符號 `✗`（不只靠顏色）與一句話，說明原因與處理方式（例：「請輸入以 http:// 或 https:// 開頭的網址。」「網址不得含帳號、密碼或 token；請改貼不含這些內容的位址。」）；回應 HTML 與伺服器日誌都不回印被拒絕網址中的 `token=`／密碼等值；英文版句子無中日韓字元 | 自動：`test_studio_url_rejected_cases`（參數化） |
| TC-010 | 作法 3（輸出一律跳脫、`href` 只放通過驗證者）；失敗先行測試 5 | 例外 | 成功分析的下游頁 | 帶入 `http://h/?a="><script>alert(1)</script>`，以及另一個含 `&` 與 `'` 的網址 | 輸出沒有未跳脫的 `<script`；`"` 呈現為 `&quot;`；網址內容不會讓任何屬性被提前結束（不破出 `href`）；該網址無論被接受或被拒絕皆可，但被拒絕時不產生連結 | 自動：`test_studio_url_is_escaped` |

## User Story 3 — 不儲存、不新增、不擴大範圍（優先度 P1）

維護者原話 4（ADR 0008／DESIGN.md 第 9 畫面）：「不需要建議分析，下面那兩張圖也完全不需要。只要讓使用者能操作裡面的R……」→ 本頁不放建議分析、不放預設圖。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 作法 1（不儲存）；「不做」：不存 Studio 網址；失敗先行測試 6 | 不在範圍 | 已登入使用者、成功分析；先記下 `platform.db`、`tokens.db` 各表的結構（`sqlite_master`）與逐表列數／內容雜湊 | 開下游頁（空欄位、合法網址、被拒絕網址各一次），再重新取得資料庫狀態 | 兩個資料庫的結構與各表內容與呼叫前完全相同（登入本身寫的 `web_sessions` 除外，且僅此一處）；`PREF_DEFAULTS` 的鍵仍只有兩個（`step_mode`、`dev_mode`）；`caplog` 中沒有任何 `studio=` 後面的值 | 自動：`test_nothing_is_stored` |
| TC-012 | 作法 4；「不做」：不新增路由、動作、資料表；完成標準 diff 範圍；失敗先行測試 8 | 不在範圍 | 完成後的程式碼與 v3 基準 | 列出 `web.create_app(...)` 的 (path, methods) 集合與 `actions` 公開函式集合，並看 `git diff --stat <base>...HEAD` | 路由集合與動作集合與 v3 基準（寫成測試內常數）完全相同；`store.py`、`actions/`、`mcp_*` 零改動；沒有 migration；有改動的檔案只在範圍內（`web_downstream.py`、`test_web_downstream.py`、`web_board.py`、`web.py`、`test_web_bugs_a.py`，以及必要時 `test_web_wording_sweep.py` 只增不減） | 自動：`test_no_new_route_no_new_action`；diff 範圍由驗收者讀 `git diff --stat` |
| TC-013 | 作法 4（擁有者規則）；失敗先行測試 7 | 例外 | ann 有一個成功分析；bob 另一位使用者 | bob 開 ann 的分析下游頁（含 `&studio=https://rstudio.example.org/s/abc`）；ann 開一個不存在的 id 的下游頁（同樣帶 `studio`） | 兩者都回 404（與既有行為相同，不因 `studio` 參數改變）；回應頁面不含該網址；沒有任何新的寫入路徑（以 TC-012 的路由集合不變證明） | 自動：`test_other_user_and_missing_run_unchanged` |
| TC-014 | 原話 4；「不做」：不用 iframe、不做 Studio 啟動／停止、不做主機白名單與連線檢查、不放建議分析與預設圖、不做「終端機 · 本機」切換、不處理「完成」階段 | 不在範圍 | 成功分析的下游頁 | 看空欄位與合法網址兩種狀態的 HTML；另帶 `&studio=http://192.168.1.5:8888/lab` 與 `&studio=http://no-such-host.invalid/` | 頁面沒有 `<iframe`、沒有 `<img`／圖片、沒有建議分析區塊、沒有「啟動」「停止」按鈕或表單、沒有「終端機」切換；區網與不存在的主機位址都照樣被接受並產生連結（沒有白名單、沒有連線檢查，回應不因主機不可達而延遲或失敗）；「完成」階段頁（`stage=finished`）內容與 v3 相同 | 自動：`test_studio_link_opens_new_tab`（區網與不可達主機案例）、`test_downstream_succeeded_shows_section_not_placeholder`（無 iframe／img／終端機）；`finished` 不變由既有 `test_web_finished.py` 為證 |
| TC-015 | 作法 8；範圍：被釘住不得改動的測試；「不做」：不改 STYLE／CSP、不動 PLACEHOLDER；失敗先行測試 9、12 | 不在範圍 | 完成後的程式碼與 v3 基準 | 比對 `web_board.py` 與被釘住的測試檔 | `web_board.py` 恰有一行 `from . import web_downstream`；`PLACEHOLDER` 仍是 `("launch", "downstream")`；`web_board.STRINGS` 的鍵集合與 v3 相同（沒有新增）；`render_board`／`_run_page`／`_stage_card` 的 `studio` 參數預設 `None`，既有呼叫不受影響；既有測試只改一處：`test_web_bugs_a.py::test_stage_placeholder_launch_downstream` 的參數縮成 `["launch"]`（`test_web_wording_sweep.py` 若有改只准增不減）；`test_web_board.py`（含第 547 行占位斷言與 `test_tcl42_string_table`、`test_tcl44_*`）、`test_results_files.py`、`test_web_guided_launch_preview.py`、`test_web_finished.py`、`test_web_parity.py`、`test_actions_layer.py`、`test_web_actions.py` 零改動且全綠 | 自動：`test_board_touches_are_minimal`；被釘住測試未改由驗收者對 base 做 diff 確認 |

## User Story 4 — 文字與畫面符合設計守則（優先度 P2）

維護者原話 5（DESIGN.md「用字」，2026-10-27）：「一樣要注意中文的顯示不能口語」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 原話 5；作法 5；失敗先行測試 11 | 功能 | `web_downstream.STRINGS` | 檢查字串表，並跑 `test_web_wording_sweep.py` | `zh` 與 `en` 鍵集合相同、全部有值；`en` 無中日韓字元；`zh` 為正式書面語、不含 DESIGN.md「用字」的禁用詞（若 sweep 依模組列舉字串表，本模組已加入，只增不減）；沒有任何字串含 `012b`、`016`；沒有 AI 之類內部術語；錯誤句說發生什麼事與下一步 | 自動：`test_strings_table_parity_and_wording`、`test_web_wording_sweep.py` |
| TC-017 | 專長守則（ui）：實際跑起來看、手機寬度、鍵盤焦點、axe；DESIGN.md 的狀態都要做出來 | 功能 | 用 `with_server.py` 把真正的應用程式起起來，成功分析、失敗分析各一 | 以 Playwright 在 1440 與 390 寬、中文與英文，看下游頁的四種狀態（空欄位、合法網址連結、被拒絕網址錯誤句、非成功分析占位），用鍵盤 Tab 走一遍表單，跑 axe | 四種狀態都做出來；錯誤狀態同時有符號 `✗`、文字與顏色，轉成黑白仍看得出；390 寬時一欄、`document.documentElement.scrollWidth` 不大於視窗寬、按鈕與欄位點得到；Tab 時欄位與按鈕的焦點外框看得見；axe 沒有 serious 或 critical；實際點擊合法網址連結會開新分頁（瀏覽器行為，非內嵌） | 手動：驗收者以 Playwright 實跑（`docs/TESTING.md` 尚無此步，見總覽疑問 1） |
| TC-018 | 完成標準：risk M 的截圖 | 功能 | 同 TC-017 | 產出三種狀態、中英各一，共 6 張截圖：成功分析下游頁（空欄位）、貼入合法網址後的連結、貼入被拒絕網址後的錯誤句 | 6 張截圖都存在（存放在 repo 之外或被 `.gitignore` 排除處）；中文截圖全是中文、英文截圖全是英文（分析名稱除外）；沒有新增顏色、字型、間距（只用既有 class）；「好不好看」交維護者判斷 | 手動：同 TC-017 |

## 憲法與安全網

本任務觸碰的規則：憲法第 1 條（第二點，不得另存一份分析狀態；除既有的一條送出路徑外沒有別的送出）、Safety Net「平台不存放經手的憑證」、Safety Net「寫入動作需要人確認」（本任務不新增任何寫入動作）。「平台不執行任何腳本、不在 NCHC 登入節點執行」來自決定 11 選項 A，併在此處證明。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | Safety Net：憑證只在使用者自己處，平台不經手、不印出；決定 11 A（不在 NCHC 登入節點、平台不執行） | 不在範圍 | 成功分析的下游頁（中英） | 取出指令區文字與整頁文字 | 指令文字不含 `password`、`token`、`AKIA`、`sk-`（憑證形狀）；整頁沒有 `nchc`、`ln01` 等登入節點字樣，也沒有 `sbatch`、`srun`；頁面沒有任何會由平台執行指令的按鈕或表單（唯一表單是 GET 到 `/` 的網址欄位）；含 `token=`／帳號密碼的網址被拒絕且不回印（見 TC-009） | 自動：`test_wording_in_command_block`（含 TC-009 的不回印斷言） |
| TC-020 | 憲法第 1 條（無第二份狀態、除既有一條外無送出路徑）；Safety Net：新寫入動作須有拒絕測試（本任務無新寫入動作） | 功能 | 完成後的程式碼 | 跑 `tests/no_second_run_state_test.sh`（含其送出掃描，涵蓋 `platform/`）與 `platform/tests/test_actions_layer.py` | 兩者仍綠、其白名單與清單未被改動或放寬；`web_downstream.py` 是純函式模組（不碰資料庫、檔案、網路），不在送出白名單內也不需要在 | 自動：`tests/no_second_run_state_test.sh`、`platform/tests/test_actions_layer.py`；純函式性由驗收者讀 `web_downstream.py` 的 import 確認 |
