---
id: studios-new-tab
title: 下游階段：成功的分析顯示「自己啟動 RStudio／Jupyter」說明與「在新分頁開啟」連結（不內嵌、不存檔、平台不執行）
tier: B
kinds: ui
risk: M
lane: L-studios-new-tab
branch: feat/studios-new-tab
base: v3
source: 維護者 2026-11-05 裁示（決定 11 選項 A、決定 12 選項 A）；docs/adr/0010-chat-keys-byte-channel-studio-embedding.md「Decided」第 3 點與「Question 3」選項 B（新分頁為既定的退路）；docs/adr/0008 第 3 點；DESIGN.md 第 9 畫面（下游階段）；memory/PLAN-abf-v3-replan-2026-10.md Milestone 2 的 016a／016b
---

# studios-new-tab

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/studios-new-tab/plan.md`。**只處理本任務**。

## 目標
成功分析的「下游」階段目前只有灰字「之後開放」。改成最小可用的 Studios：頁面說明使用者如何在**自己的電腦或雲端環境**用該分析的結果資料夾啟動 RStudio 或 Jupyter（可複製的指令），並提供一個欄位讓使用者貼上自己 Studio 的網址，按下後以連結在**新瀏覽器分頁**開啟。平台不內嵌（不用 iframe）、不代為啟動、不執行任何腳本、不儲存任何網址。這是 ADR 0010 已寫明的退路；之後再升級成內嵌（另開任務）。

## 維護者原話（verifier 出題用）
1. 「如果都可以，要把下游分析放下一個目標進度了」（2026-11-05）→ 下游階段從占位變成可用；成功的分析進入下游階段要看得到內容，不再是「之後開放」。
2. 「11A 12A都照你建議」（2026-11-05）→ 決定 11 選項 A：v3.0.0 平台自己不執行腳本、Studio 只在使用者自己的電腦或雲端環境執行、不在 NCHC 登入節點；決定 12 選項 A：先做開新分頁版，之後再升級成嵌入。
3. ADR 0010 Decided 第 3 點（維護者 2026-10-17）：「Studio screen: option A, with the new-tab button as the fallback. … If it fails, the Studio opens in a new tab.」與「No Studio on NCHC in v3.0.0. Studios run on the person's own computer or a cloud compute environment.」→ 說明文字不得教使用者在 NCHC 登入節點啟動 Studio；連結為 `target="_blank"`。
4. ADR 0008 原話（2026-10-17）：「Studio也要，不然怎麼做downstream這步?」→ 下游是人自己寫分析，不提供預設分析。DESIGN.md 第 9 畫面（維護者 10-18）：「不需要建議分析，下面那兩張圖也完全不需要。只要讓使用者能操作裡面的R……」→ 本頁不放建議分析、不放預設圖。
5. 維護者 2026-10-27 的用字裁示（DESIGN.md「用字」）：「一樣要注意中文的顯示不能口語」→ 全部中文為正式書面語，英文版（`?lang=en`）無任何中日韓字元。

## 範圍：檔案
**同車道、排在 web-bugs-b 之後**（本任務一定要動 `web.py` 與 `web_board.py`，與 web-bugs-a／web-bugs-b 的檔案相交；supervise 須依序，不得並行）。
- 新模組：`platform/abf_platform/web_downstream.py`（純函式，仿 `web_finished.py`：不碰資料庫、檔案、網路；字串表 zh／en 同鍵）。
- 新測試：`platform/tests/test_web_downstream.py`。
- `platform/abf_platform/web_board.py`：只加一行 `from . import web_downstream`、`render_board`／`_run_page`／`_stage_card` 各加一個 `studio=None` 參數往下傳、`_stage_card` 開頭加一個分支（`stage == "downstream" and run["status"] == "succeeded"` → `web_downstream.render_downstream(...)`）。`PLACEHOLDER` 元組**不改**（非成功的分析仍走占位）。成功分析的下游頁不產生 15 秒自動重新整理（見作法 6）。
- `platform/abf_platform/web.py`：只改 `board`／`board_page` 讀 `request.query_params.get("studio")` 往下傳；下游階段時比照 `read_outputs_look` 讀一次輸出資料夾（`enqueue=False`，只看不排隊）。不新增路由。
- 既有測試必須改的（改的是占位的預期，且只准在這兩處）：`platform/tests/test_web_bugs_a.py` 的 `test_stage_placeholder_launch_downstream`（約 245 行起；`downstream` 不再對成功分析顯示占位，參數化只留 `launch`，另在新測試檔對「失敗／執行中的分析」保留占位斷言）。
- 被釘住、**不得改動也不得放寬**的測試（用 `git -C <repo> grep -n -E "之後開放|PLACEHOLDER|STYLE_SHA256|CSS_SHA256|STRINGS" origin/v3 -- platform/tests` 再列一次）：
  - `test_web_board.py` 第 547 行（`("downstream", "之後開放")`，該分析為非成功狀態 → 本計畫保留占位，故不需改）；第 1122 行 `test_tcl42_string_table`（`web_board.STRINGS` zh／en 同鍵、無空值、en 無 CJK；本計畫**不往 `web_board.STRINGS` 加鍵**，字串放 `web_downstream.STRINGS`）。
  - `test_results_files.py` 約 695～708 行：`STYLE` 的 sha256 與 CSP 的 `style-src 'sha256-…'`；`test_web_guided_launch_preview.py` 第 411～418 行 `CSS_SHA256`（`<style>` 文字雜湊）。→ **不得新增或改任何 CSS**，只用既有 class（`card`、`kv`、`muted`、`later`、`off`、`bad`、`reason`）。若雜湊測試紅，代表動到了 `STYLE`，退回去改，不是重新釘。
  - `test_web_finished.py` 第 280～290 行 `test_fs12_web_board_touches_are_minimal`（`from . import web_finished` 恰一行、`finished` 不在 `PLACEHOLDER`）。
  - `test_web_board.py` 的 `test_tcl44_no_external_url_script_or_style_attribute`（頁面不得有外部 URL、script、style 屬性；其案例不帶 `studio` 參數，故仍成立；本任務的新測試另證「只有使用者貼的那一個 `<a>`」）。
  - `test_web_wording_sweep.py`（所有中文字串不得含禁用詞）、`test_web_parity.py` 與 `test_actions_layer.py`（動作與路由清單；本任務不新增動作、不新增路由，預期不動）。
  - `test_web_actions.py` 第 592 行附近的資料表欄位清單：不動資料表，所以不動。

## 作法
1. **儲存：選「不儲存」**。理由：`store.py` 現有的個人設定只有 `users.step_mode`、`users.dev_mode` 兩個布林（`PREF_DEFAULTS` 只接受這兩個鍵，約 755、991 行）；存網址要新增欄位或資料表＋migration＋新動作＋更新動作／路由釘住的清單，風險升 L。維護者要的是最簡版，所以網址只在**這一次請求的查詢字串**裡存在（`GET /?run=…&stage=downstream&studio=<網址>`），頁面把它畫成連結；重新整理頁面或書籤能還原。平台不寫入任何資料表、不寫日誌內容。若之後要「每個分析記住 Studio 網址」，另開任務（需 migration、risk L），列在「不做」。
2. **畫面（只給 `status == "succeeded"` 的分析；非成功仍是占位「之後開放」）**：一個 `<section class="card">`，標題沿用 `stage_downstream`（「下游」）。內容依序：
   - 一句說明：下游分析在使用者自己的電腦或雲端環境進行；平台不代為執行，也不在 NCHC 登入節點啟動。
   - 「結果資料夾」：若讀得到該分析的輸出資料夾（`run_outputs(..., enqueue=False)` 的回傳，executor 以實際鍵名為準，不得為此新增動作），顯示站台上的路徑；讀不到則顯示「尚未讀取輸出」並連到既有的「查看輸出」（`results`／`outputs` 分頁），不報錯。說明「先把這個資料夾複製到自己的電腦或雲端環境」。
   - 兩段可複製指令（`<pre class="reason">` 內，字面文字、不含任何密碼或 token）：Jupyter：`jupyter lab --notebook-dir "<本機結果資料夾>"`；RStudio：`docker run --rm -p 127.0.0.1:8787:8787 -e DISABLE_AUTH=true -v "<本機結果資料夾>":/home/rstudio/results rocker/rstudio`（只綁 127.0.0.1）。`<本機結果資料夾>` 是使用者自己填的佔位，不是平台值。
   - 一個 **GET** 表單（`method="get" action="/"`，隱藏欄位 `run`、`stage=downstream`，英文版加 `lang=en`；不需 CSRF，因為不寫入任何東西），一個 `type="url"` 的文字欄位 `studio`（預設空白）與按鈕「開啟連結」。
   - 若 `studio` 通過驗證：在表單下方顯示 `<a href="<網址>" target="_blank" rel="noopener noreferrer">在新分頁開啟 Studio</a>`，並以純文字再印出該網址；另一句「此網址由使用者自行提供，平台不儲存、不檢查其內容。」
   - 若 `studio` 非空但未通過驗證：`<p class="bad" role="alert">` 一句話說明原因與處理方式（見 3）。
3. **網址驗證（`web_downstream.studio_url(raw) -> (ok_url | None, reason_key | None)`，純函式）**：去頭尾空白；長度 ≤ 300；開頭必須是 `http://` 或 `https://`（拒絕 `javascript:`、`data:`、`file:` 等，大小寫不拘）；有主機名；**不得含帳號密碼**（`user:pass@`）；**不得含 `token=`、`password=`、`key=`、`secret=` 查詢參數**（不分大小寫）——理由：本頁是 GET，網址會進伺服器存取紀錄，且憑證規則（docs/PLATFORM.md §7）不准平台經手憑證；訊息教使用者改貼不含 token 的位址（Jupyter 可在新分頁內自行輸入 token）。不含控制字元與空白。輸出一律 `html.escape(..., quote=True)`；`href` 只放通過驗證者。不做主機白名單（可為 localhost、區網或雲端位址；`http://localhost` 只在瀏覽器就在同一台電腦時才連得上，說明裡寫一句）。
4. **不新增動作、不新增路由、不新增資料表**：沿用 `GET /`。擁有者規則：`selected` 仍由 `read_run(run_id, caller)` 取得，他人的分析與不存在的 id 照舊回 404（既有行為），不因為 `studio` 參數而改變。
5. **字串**：`web_downstream.STRINGS = {"zh": {...}, "en": {...}}` 同鍵、全有值、en 無中日韓字元。中文正式書面語（例：「下游分析於使用者自己的電腦或雲端環境進行，平台不代為執行。」「請輸入以 http:// 或 https:// 開頭的網址。」「網址不得含帳號、密碼或 token；請改貼不含這些內容的位址。」）。不出現 AI、012b、016 等內部編號；不得含 DESIGN.md「用字」禁用詞（先跑 `test_web_wording_sweep.py`，若它依模組列舉字串表，把本模組表加進它的列舉，只增不減）。
6. **自動重新整理**：`render_board` 對頁面有 15 秒重新整理（約 874～890 行）。成功分析的下游頁不再需要重新整理（狀態已終結），且重新整理會丟掉使用者正在輸入的欄位 → 此頁**不產生**重新整理；測試要證明頁面不含指向缺少 `studio` 的 `refresh`。
7. **安全標頭**：既有 CSP `default-src 'none'; form-action 'self'; frame-ancestors 'none'` 不動；連結導覽與 GET 表單送到自己都不違反。不用 JavaScript、不用 iframe、不載入任何外部資源。
8. **版本／相容**：`render_board` 新增的 `studio` 預設 `None`，所有既有呼叫與純元件測試不受影響。

## 失敗先行測試（`platform/tests/test_web_downstream.py`，沿用 `test_web_bugs_a.py` 的 `w`、`seed`、`login`、`pane` 輔助）
先寫、現在會紅（v3 下游頁只有占位）：
1. `test_downstream_succeeded_shows_section_not_placeholder`：成功分析 `/?run=…&stage=downstream` 的中欄含「在新分頁開啟」所屬表單（`name="studio"` 的 `type="url"` 欄位、`method="get"`）、含 `jupyter lab --notebook-dir` 與 `rocker/rstudio`，**不含** `<span class="later">`；英文版同結構且 `no_cjk`。
2. `test_downstream_nonsucceeded_keeps_placeholder`：失敗、執行中的分析下游頁仍為 `<span class="later">之後開放</span>`（英文 `Coming later`），無 `name="studio"` 欄位。
3. `test_studio_link_opens_new_tab`：帶 `&studio=http://localhost:8787/` → 頁面恰有一個 `<a href="http://localhost:8787/" target="_blank" rel="noopener noreferrer">`；頁面其餘部分沒有新增外部 `href`／`src`、沒有 `<script`、`<iframe`、`style=`。`https://rstudio.example.org/s/abc` 亦然。
4. `test_studio_url_rejected_cases`（參數化）：`javascript:alert(1)`、`JaVaScRiPt:…`、`data:text/html,…`、`file:///etc/passwd`、`ftp://x`、`//evil.example`、`http://user:pw@host/`、`http://h/?token=abc`、`http://h/?PASSWORD=x`、301 字元網址、含空白或換行、`http://`（無主機）→ 頁面**無** `target="_blank"` 連結、有 `role="alert"` 一句含原因與處理方式；回應不回印被拒絕網址中的 `token=`／密碼值。
5. `test_studio_url_is_escaped`：`http://h/?a="><script>alert(1)</script>` 與含 `&`、`'` 的網址 → 輸出無未跳脫的 `<script`，`"` 為 `&quot;`；仍通過或被拒絕皆可，但不得破出屬性。
6. `test_nothing_is_stored`：呼叫前後對 `platform.db`、`tokens.db` 各表（`sqlite_master` 與逐表列數／內容雜湊）完全相同；`web_sessions` 之外沒有寫入；`PREF_DEFAULTS` 鍵仍只有兩個；伺服器日誌（`caplog`）不含 `studio=` 的值。
7. `test_other_user_and_missing_run_unchanged`：bob 開 ann 的分析下游頁（含 `&studio=…`）→ 404 且頁面不含該網址；不存在的 id 同樣 404（讀的跨使用者案例）；無寫入案例見 6（本任務沒有寫入動作，所以「寫」的跨使用者案例以「沒有任何新寫入路徑」證明：檢查 `app.routes` 路徑集合與 v3 相同）。
8. `test_no_new_route_no_new_action`：`web.create_app(...).routes` 的 (path, methods) 集合等於 v3 基準集合；`actions` 公開函式集合不變（把基準寫成測試內常數，來源是 `git show origin/v3` 當下列舉；見「環境事實」的重新釘住法）。
9. `test_style_untouched_and_csp_same`：`web_board.STYLE` 的 sha256 等於 `test_results_files.py` 的 `STYLE_SHA256`；下游頁的 CSP 與首頁相同。
10. `test_no_refresh_on_succeeded_downstream`：成功分析下游頁沒有指向無 `studio` 位址的 `<meta http-equiv="refresh">`（作法 6）。
11. `test_strings_table_parity_and_wording`：`web_downstream.STRINGS` zh／en 同鍵、全有值、en 無 CJK、zh 無禁用詞；零個字串含 `012b`、`016`。
12. `test_board_touches_are_minimal`：`web_board.py` 恰一行 `from . import web_downstream`；`PLACEHOLDER` 仍為 `("launch", "downstream")`；`web_board.STRINGS` 鍵集合與 v3 相同（不新增）。
13. `test_wording_in_command_block`：指令文字不含 `password`、`token`、`AKIA`、`sk-`（憑證形狀），不含 `nchc`／`ln01` 等登入節點字樣，也不含 `sbatch`／`srun`。
另：把 `test_web_bugs_a.py::test_stage_placeholder_launch_downstream` 的參數縮成 `["launch"]`（見範圍）。

## 完成標準（done when）
- 上面每條測試存在並綠；`tests/run_all.sh --timeout 900` 全綠（環境紅依 README 通例）；`STYLE`／CSP 雜湊測試未動且綠。
- 網頁畫面另附截圖（risk M）：成功分析下游頁（空欄位）、貼入合法網址後的連結、貼入被拒絕網址後的錯誤句；中英各一。
- `git diff --stat` 貼進 ledger：改動僅限範圍內的 6 個檔（`web_downstream.py`、`test_web_downstream.py`、`web_board.py`、`web.py`、`test_web_bugs_a.py`，及必要時 `test_web_wording_sweep.py` 只增不減）；`store.py`、`actions/`、`mcp_*` 零改動（證明沒有儲存、沒有新動作）。
- 若發現必須新增欄位、資料表或動作才能做到：**停下來**，在 ledger 標 **risk L** 並回報 developer-agent，不要自行擴大。
- 專長守則檢查一行寫進報告。

## 環境事實
- 現況（origin/v3）：`web_board.py` 第 21～22 行 `STAGES`、`PLACEHOLDER = ("launch", "downstream")`；`_stage_card`（約 494 行）對 `PLACEHOLDER` 輸出 `— 之後開放`；`finished` 已有同型作法（`web_finished.render_finished`，`web.py` 約 557～589 行讀 `launch_prefill` 與 `run_outputs(enqueue=False)` 後傳入）。本任務照這個模式做，但只讀輸出資料夾，不讀 `launch_prefill`。
- `render_board` 簽章（約 874 行）目前有 `outputs`、`finished` 兩個傳入；`board_page`（`web.py` 約 569 行）已是 `run_in_threadpool` 讀取模式。
- 內部約束來自 ADR 0010 Question 3 選項 B（新分頁、沒有框架政策要設）與 ADR 0010「Decided」第 3 點；內嵌（iframe）要先有三瀏覽器試驗（Jupyter `frame-ancestors`、Chromium 本機網路閘、混合內容），**不在本任務**。
- 目前資料庫沒有個人設定表可放網址（只有 `users.step_mode`、`users.dev_mode`）；因此選擇不存。
- **重新釘住法**（只在 developer-agent 明確要求變更清單時才用）：本任務預期**不需要重新釘住**任何數量；若動作清單、路由清單、`web_board.STRINGS` 或 `STYLE` 雜湊測試紅，是 bug，回頭修；不可為了讓測試過而改釘住值。若維護者之後決定存網址：動作清單測試（`test_actions_layer.py`、`test_web_parity.py`）與資料表欄位清單（`test_web_actions.py` 約 592 行）要在同一個提交同步更新，並附 migration。
- PITFALLS 已查（`docs/PITFALLS.md`，無 `docs/solutions/`）：與 `web_board`、`STYLE`、CSP、`web.py` 查詢參數相關的條目 grep 無相符項；僅有與本任務無關的 Jupyter 連線檔條目（約 1375、1629 行：`jupyter_client`／連線檔含 HMAC key，任何人讀到即可附著）——相關的教訓套用於本計畫：不在頁面、指令、日誌放 token／金鑰（作法 3、測試 13）。結論：「PITFALLS 已查，無直接相符項；以上一條作旁證」。
- 與其他任務的碰撞：`web-bugs-a`（`web.py`、`web_board.py`、`test_web_bugs_a.py`，含 #339 占位階段）、`web-bugs-b`、`web_cost.py` 任務。本任務與前兩者**必然相交**（同檔、且改同一個測試），須同車道、排在 web-bugs-b 合併之後，落地前 `git merge origin/v3`；與 `web_cost.py` 不相交。

## 不做
- 不用 iframe 內嵌、不做 Studio 啟動／停止的動作、不做 MCP 工具、不新增路由、不新增資料表或欄位、不存 Studio 網址（之後若要「每個分析記住網址」另開任務，需 migration、risk L）。
- 平台不執行任何腳本，不經由站台代理或啟動 Studio，不在 NCHC 登入節點執行（決定 11 A、ADR 0008／0010）。
- 不做主機白名單、不檢查網址能否連線、不做 Studio 狀態偵測（那屬內嵌版）。
- 不放建議分析、不放預設圖（DESIGN.md 第 9 畫面）；不做「終端機 · 本機」切換（另案）。
- 不改 `STYLE`／CSP、不動 `PLACEHOLDER` 的 `launch` 項與非成功分析的占位文字。
- 不處理「完成」階段、不碰 `web_cost.py`。

## 裁決
1. 儲存選「不儲存」（GET 查詢字串＋即時渲染連結）；若 executor 認為非存不可，不得自行做，須停下回報並標 risk L。
2. 非成功的分析下游頁維持占位「之後開放」，以免動到 `test_web_board.py` 第 547 行的釘住斷言。
3. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值，條數 ≤ 20。
4. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`；worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明。

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
