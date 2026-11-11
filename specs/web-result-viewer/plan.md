---
id: web-result-viewer
title: 網頁結果檢視：完成頁／輸出頁列出結果檔，PNG／SVG 用 <img> 預覽，pipeline 自產 HTML 報告（MultiQC、summary_report）用沙盒 iframe 預覽，全站安全標頭不放寬
tier: B
kinds: ui
risk: L
serves: S1-VIEW
lane: L6-web
base: v3
review: maintainer
source: 維護者 11-07 定案（Q1）；DESIGN.md 畫面 8（Results）、9（Downstream）、10（Finished）與 Constraints；docs/PLATFORM.md:805（下載一律 attachment）；PITFALLS 已查（見「環境事實」）
---

# web-result-viewer

> 本檔由 developer-agent 寫，`/supervise` 複製進 worktree 的 `specs/web-result-viewer/plan.md`。同一計畫分兩步、兩個提交：**步驟 A 圖片預覽先做、步驟 B 沙盒 iframe 後做**。B 開始前 A 必須已綠。risk L：閱卷要多交爆炸半徑證明（見完成標準），PASS 後再跑一次 Opus 對抗審。

## 目標
同事在完成頁與輸出頁看到 run 的結果檔清單，能下載；PNG／SVG 在網站內直接預覽；pipeline 自己產的 HTML 報告（MultiQC、ampliseq 的 summary_report）在沙盒 iframe 內預覽，報告內的程式碼無法讀 cookie、無法呼叫本站 API、無法送出表單。其餘頁面的安全標頭一個字都不放寬。

## 維護者原話（verifier 出題用）
1. 「Q1: (C)也要，在R studio介面要能看，網站上要能檢視」（11-07；網站這一半由本任務做，R Studio 介面那一半是畫面 9 既有的 iframe，不在本任務）
2. 11-07 定案（維護者轉述，逐項各至少一條測試）：
   - 完成頁列出 run 結果檔並可下載；
   - PNG／SVG 以 `<img>` 預覽，**SVG 不內嵌進頁面**；
   - HTML 報告用沙盒 iframe：sandbox **不含 allow-same-origin**、不能提交表單、不能存取網站資料；**專用路由與專用 CSP，不放寬其他頁**；
   - 圖片預覽先做、iframe 後做（同一計畫分步）；
   - 必須有安全測試：報告內 script 無法讀 cookie／呼叫網站 API、非允許副檔名不預覽、超過 25MB 顯示 too_large、既有 tc049 類測試（其他頁不得有 img-src）不得被改弱；
   - UI 要附 1440／390 × zh／en 截圖。
3. DESIGN.md Constraints：「Single stylesheet, no inline style, no external resources」「JS only where marked」——預覽頁本身不得有 `<script>`、`style=`。

## 範圍：檔案
- `platform/abf_platform/web_preview.py`（**新檔**：預覽頁渲染、副檔名／魔術位元組判斷、三組專用標頭、中英字串）
- `platform/abf_platform/web.py`（只新增：`GET /run/preview`、`GET /run/image`、`GET /run/report` 三條 handler 與註冊行；不改 `_HEADERS`、`LAUNCH_HEADERS`、`add_headers`、既有 handler）
- `platform/abf_platform/web_board.py`（只限：輸出頁下載格旁加「預覽」連結——`_download_cell`；新增 STRINGS；`download_headers` 不動）
- `platform/abf_platform/web_finished.py`（只限：`_downloads` 清單每個可預覽檔後加「預覽」連結；必要字串）
- `platform/tests/test_web_result_viewer.py`（**新檔**，全部新測試）
- 被逐字釘住、**只准加項不准刪改**的既有測試（ledger 逐條列）：路由清單類 `test_dataset_cli.py:183`、`test_cleanup_offer.py:822`、`test_confirm_page.py:312-315`、`test_web_board.py:828`、`test_owner_binding.py:826`、`test_web_downstream.py:25`（再 grep `'/run/file'` 確認有無遺漏）
- `docs/PLATFORM.md`（第 805 行附近「下載一律 attachment」補：預覽是另外三條路由，下載路由不變）、`docs/TESTING.md`（新增手動一節：真 MultiQC／summary_report 預覽＋截圖）、`DESIGN.md`（畫面 8 的「Reports (MultiQC embedded, JS)」一句改成與本實作一致）
- 不得改：`jobs.py`、`actions/__init__.py`、`abf_station/*`（25 MB 上限與讀檔邏輯沿用）

## 作法

### 共通決定
- 檔案內容一律走既有 `actions.run_file(index_path, platform_path, run, path, caller=caller)`（擁有者規則、路徑檢查、25 MB 上限、站台讀檔都已在裡面）。新路由**不自己讀檔、不新增 job 種類**。
- 預覽可否判斷集中在 `web_preview.kind_of(path)`，傳回 `"png" | "svg" | "html" | None`：
  - `png`：副檔名 `.png`（不分大小寫）**且**位元組開頭是 `\x89PNG\r\n\x1a\n`，否則視為不可預覽。
  - `svg`：副檔名 `.svg` **且**去掉前導空白／BOM／XML 宣告／註解後有 `<svg`。
  - `html`：副檔名 `.html` 且檔名（basename，不分大小寫）在白名單 `{multiqc_report.html, summary_report.html}`。**其他 .html 一律不預覽**（只能下載）。
  - `.jpg/.gif/.pdf/.htm` 與其餘一律 None（此版不做；列「不做」）。
- 路徑只判斷名稱／副檔名，不信任 `Content-Type` 或使用者參數；`/run/image` 與 `/run/report` 不接受任何指定 MIME 的參數。
- 預覽入口一律是**純連結**（`<a href="/run/preview?run=&path=&lang=">`），輸出頁、完成頁不得因此多出 `<img>`、`<iframe>`、`<script>`、`<form>`、`<button>`。可預覽才出現「預覽」連結（只看副檔名／白名單，不讀檔）；其他檔維持原樣。
- 下載路由 `/run/file` **一個字都不改**（仍 attachment＋octet-stream）。

### 步驟 A：圖片預覽（先做，獨立提交）
1. `GET /run/preview?run=&path=`：登入、擁有者規則同 `/run/file`（別人的 run → 同一個 404 頁 `render_not_found`）。`kind_of` 為 None → 200 頁，文字說明「此檔類型不提供預覽」＋下載連結＋返回連結。呼叫 `actions.run_file`：`loading` → 重用既有「等待」頁行為（`render_file_page`，自動 15 秒重整）；`too_large` 或 error → 重用 `render_file_page` 的對應句（too_large 要顯示 `too_large` 句，不渲染圖片）；`ready` 且 `kind_of` 對 → 頁面主欄放 `<img src="/run/image?run=&path=" alt="檔名">`，下方「下載」連結（指向 `/run/file`）與返回連結。
2. 預覽頁 CSP 只准這一頁：`default-src 'none'; img-src 'self'; style-src <同全站雜湊>; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`（即 `LAUNCH_HEADERS` 同形）。X-Frame-Options 維持 DENY。**img-src 只出現在 `/run/preview` 回應**。
3. `GET /run/image?run=&path=`：同樣擁有者規則；只對 `png`／`svg` 且 `ready` 回 200，否則回 404 純文字空內容（不渲染頁面、不洩漏原因）。標頭：`Content-Type` 由 `kind_of` 決定（`image/png`／`image/svg+xml`，不由檔案決定）、`X-Content-Type-Options: nosniff`、`Cache-Control: private, no-store`、`Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; sandbox`（SVG 被直接開啟時不得執行指令稿；比 `/launch/diagram` 多一個 `sandbox`）、`X-Frame-Options: DENY`。不加 `Content-Disposition`（要下載走 `/run/file`）。
4. **SVG 不內嵌進頁面**：只能經 `<img src>`；頁面 HTML 內不得出現 SVG 原文（測試要斷言頁面不含 `<svg`）。
5. 輸出頁 `_download_cell` 與完成頁 `_downloads`：可預覽檔在既有「下載」後面多一個「預覽」連結；既有 `fs12`／`ro03` 釘住的連結與格式（見失敗先行測試）逐字保持，新連結只加在其後。
6. 中文用字照 DESIGN.md「用字」：書面語、不含禁用詞表（這個、這份、一下…）、中文頁不得有獨立的拉丁字 `run`。

### 步驟 B：沙盒 iframe（後做，獨立提交）
1. `/run/preview` 對 `html` 且 `ready`：頁面主欄放 `<iframe sandbox="allow-scripts" src="/run/report?run=&path=" title="檔名" referrerpolicy="no-referrer"></iframe>`。**sandbox 屬性值恰為 `allow-scripts`**：不含 `allow-same-origin`、`allow-forms`、`allow-popups`、`allow-top-navigation*`、`allow-modals`、`allow-downloads`。下方一行說明（報告在隔離框內顯示，其中的程式不能讀取本站資料）、下載連結、返回連結。
2. 此 HTML 預覽頁的 CSP（只在 `kind=html` 且 ready 的 `/run/preview` 回應）：全站基礎 CSP 加 `frame-src 'self'`，其餘不變（不得有 `img-src`、`script-src`、`unsafe-*`）。其他類型的 `/run/preview`（含步驟 A 的圖片頁）不得有 `frame-src`。
3. `GET /run/report?run=&path=`：擁有者規則同上；只對白名單 `html` 且 `ready` 回 200，否則 404 空內容。bytes 原樣回傳。標頭：
   - `Content-Type: text/html; charset=utf-8`、`X-Content-Type-Options: nosniff`、`Cache-Control: private, no-store`、`Referrer-Policy: no-referrer`
   - `X-Frame-Options: SAMEORIGIN`（**必須明寫**：`add_headers` 用 setdefault 補 DENY，路由有寫就不會被覆蓋；同時 `frame-ancestors 'self'`）
   - `Content-Security-Policy: sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' blob:; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; frame-src 'none'; frame-ancestors 'self'; base-uri 'none'; worker-src blob:`（`sandbox` 指令不含 `allow-same-origin`：就算有人在新分頁直接開 `/run/report`，文件也是不透明來源，讀不到 cookie；`connect-src 'none'` 與無 cookie 的不透明來源雙層擋 API 呼叫）。
   - 以上 CSP 為起點；executor 用真的 MultiQC 報告（`multiqc_report.html`，約 2.5–4 MB）在瀏覽器實測，若圖表因 CSP 載不出來，**只准放寬這條路由**（例如加 `data:` 到 `script-src`／`font-src`），並把放寬的字與原因記入 ledger；絕不放寬 `sandbox`、`connect-src`、`form-action`、`frame-ancestors`，也絕不動其他頁。
4. 報告內的外部連結不處理（`default-src 'none'` 與 sandbox 無 `allow-popups`／`allow-top-navigation` 下點了沒有作用，屬預期；說明句不承諾可點）。
5. 報告頁（iframe 內）高度：iframe 用 CSS 類別（外部樣式表單一份，無 inline style）設 `width:100%` 與固定高（約 80vh）；樣式新增進 `web_board.STYLE` 會改全站樣式雜湊——**不准**。改法：把預覽頁需要的 class 寫進 `STYLE` 前，先確認 `test_results_files.py:707`（全站同一雜湊）與 `test_web_board.py:876-888`（逐頁雜湊）以新雜湊重算後仍成立；若改 STYLE 會連動 `STYLE_SHA256` 常數的測試，則改為在預覽頁用 `iframe` 的 HTML 屬性 `width`／`height`（非 inline style）解決，**不動 STYLE**。executor 擇一並記入 ledger。

## 失敗先行測試
全部寫在 `platform/tests/test_web_result_viewer.py`，用 `test_web_finished.py`、`test_results_files.py` 的 `world()`／`open_file()`／`read_outputs()` 夾具（照抄其做法，不改夾具檔）。步驟 A 與 B 各一組，A 的紅燈在 A 提交前、B 的在 B 提交前。

步驟 A
- `test_va01_png_preview_page_has_img_not_inline`：`/run/preview` 對 PNG 回 200，主欄含 `<img src="/run/image?run=…&amp;path=…"`；CSP 含 `img-src 'self'`、不含 `script-src`、`frame-src`；X-Frame-Options＝DENY；頁面不含 `<script`、`style=`。
- `test_va02_image_route_headers`：`/run/image` PNG：200、`image/png`、nosniff、`private, no-store`、CSP 以 `default-src 'none'` 開頭且含 `sandbox`；bytes 與來源逐位元組相同（含 0xFF 位元組的 PNG，對應 PITFALLS 0xFF 條目）。
- `test_va03_svg_only_through_img`：SVG 檔含 `<script>alert(1)</script>`：預覽頁含 `<img` 指向 `/run/image`，頁面文字**不含** `<svg`、不含 `alert(1)`；`/run/image` 回 `image/svg+xml` 且 CSP 含 `sandbox` 與 `default-src 'none'`、不含 `script-src`。
- `test_va04_not_allowed_extension_no_preview`：`.txt`、`.tsv`、`.bam`、`.pdf`、`.htm`、`.jpg`、`.html`（非白名單名稱）、偽裝檔（`.png` 但內容是 HTML／文字、`.svg` 但內容無 `<svg`）：`/run/preview` 回「不提供預覽」頁、沒有 `<img`／`<iframe`；`/run/image`、`/run/report` 回 404 空內容；輸出頁與完成頁清單**沒有**「預覽」連結。
- `test_va05_too_large_shows_too_large`：站台列表 size＞25 MB（26214401）的 PNG：輸出頁／完成頁不出現預覽連結（維持「大於 25 MB」文字）；直接開 `/run/preview?…` 顯示 too_large 那句（沿用 `render_file_page`），無 `<img`；`/run/image` 404。
- `test_va06_owner_rule`：別人的 run 開三條路由全部 404（`/run/preview` 為 `render_not_found` 頁，另兩條空 404）；未登入照 `/run/file` 的 `unauth` 行為；不排任何 job。
- `test_va07_loading_and_error_states`：沒有讀檔答案時 `/run/preview` 為等待頁（含 15 秒重整），不含 `<img`；`/run/image` 404。
- `test_va08_other_pages_unchanged_csp`：輸出頁、完成頁、`/`、`/settings`、`/usage`、`/run/file` 的 CSP 與標頭與 base 逐字相同（沿用 `test_results_files.py:707` 的 policy 算法），**不含 `img-src`、`frame-src`**；`/run/file` 仍 attachment＋octet-stream（既有 `test_results_files.py:299-301` 不動）。
- `test_va09_route_list_pins_only_grew`：三條新路由的 methods 為 `("GET","HEAD")`，且在各路由清單釘死的測試裡已加項。
- `test_va10_english_and_wording`：`?lang=en` 預覽頁為英文；中文字串通過 `test_web_wording_sweep.py` 的 `banned_in`（把 `web_preview` 的字串表與兩個新頁加進該掃描的方式：**只新增在本檔內自己呼叫 `banned_in`**，不改 sweep 檔）。
- `test_va11_listing_has_preview_link_after_download`：完成頁、輸出頁對 PNG 檔：既有「下載」連結逐字仍在，其後有 `href="/run/preview?run=…&amp;path=…"`；沒有 `<img`。

步驟 B
- `test_vb01_iframe_sandbox_exact`：白名單 HTML 的 `/run/preview`：含恰一個 `<iframe`，`sandbox="allow-scripts"` 完全相等；屬性中不含 `allow-same-origin`、`allow-forms`、`allow-popups`、`allow-top-navigation`、`allow-modals`、`allow-downloads`；`src` 指向 `/run/report`；CSP 含 `frame-src 'self'`、不含 `img-src`、`script-src`、`unsafe-`。
- `test_vb02_report_route_headers`：`/run/report`：200、`text/html; charset=utf-8`、nosniff、`private, no-store`、`X-Frame-Options: SAMEORIGIN`；CSP 含 `sandbox allow-scripts`、**不含 `allow-same-origin`**、含 `connect-src 'none'`、`form-action 'none'`、`default-src 'none'`、`frame-ancestors 'self'`；bytes 與來源相同。
- `test_vb03_report_script_cannot_reach_site`（安全測試核心）：報告內容含 `<script>` 試圖 `document.cookie`、`fetch('/settings')`、`fetch('/run/file?…')`、`window.parent.document`、`form.submit()`。HTTP 層斷言：回應 CSP 的 `sandbox` 值不含 `allow-same-origin`；`connect-src 'none'`；`form-action 'none'`。**瀏覽器層**（`playwright` 可用則跑，不可用則 `pytest.skip("no browser")` 並由 ledger 貼手動結果）：登入後開預覽頁，報告 script 把 `document.cookie` 的結果（會丟 SecurityError 或為空）、`fetch` 結果（被 CSP 擋）寫進報告自己的 DOM；斷言讀不到 `abf_web` cookie 值、站台日誌沒有收到來自報告的 `/settings`／`/run/file` 請求。
- `test_vb04_report_requires_whitelist_and_ready`：非白名單 HTML、副檔名偽裝（`multiqc_report.html` 但在 `x/` 之外仍通過——白名單看 basename，故另測 `evil.html`、`multiqc_report.html.txt`、`multiqc_report.htm`）→ `/run/report` 404；loading／error → 404。
- `test_vb05_report_too_large`：25 MB＋1 的 `multiqc_report.html`：`/run/preview` 顯示 too_large 句、無 `<iframe`；`/run/report` 404。
- `test_vb06_report_framing_only_same_origin`：`/run/report` 為 SAMEORIGIN／`frame-ancestors 'self'`；`/run/preview`、`/`、`/settings`、輸出頁、完成頁、`/run/image` 仍 `X-Frame-Options: DENY` 且 `frame-ancestors 'none'`（`test_web_chrome_origin.py` 的既有斷言不動）。
- `test_vb07_tc049_still_holds`：原樣呼叫（或複製其斷言）`test_web_guided_launch_2d.py::test_tc049_other_pages_are_as_before` 的內容於含預覽連結的頁面上：`/`、`/settings`、`/usage`、`/c/<rid>`、完成頁、輸出頁、`/login`、`/run/file` 的 CSP 都**無 `img-src`、無 `frame-src`**；`LAUNCH_HEADERS` 內容不變。
- `test_vb08_no_new_job_kind_no_write`：三條新路由不新增 job 種類、不寫資料庫（比照 `test_web_results_outputs.py::test_ro12_nothing_else_is_written` 的做法）。
- `test_vb09_sandbox_attribute_is_not_user_controlled`：`path` 參數含引號、`<`、`>`、`"allow-same-origin"` 的值，頁面內輸出皆被跳脫，iframe 屬性仍恰為 `sandbox="allow-scripts"`。

## 完成標準（done when）
1. 上列測試全綠；`platform/tests` 全套（除通例已知環境紅）綠。
2. 既有測試**沒有被改弱**：`git diff --stat` 貼進 ledger；對 `platform/tests/` 既有檔只有「路由清單加項」類新增行，無刪行、無改斷言（`test_web_guided_launch_2d.py::test_tc049_other_pages_are_as_before`、`test_results_files.py:299-301,707`、`test_web_chrome_origin.py:68`、`test_web_board.py:876-888`、`test_web_finished.py` fs08／fs11／fs12／fs14 都不得改）。
3. **爆炸半徑證明**（risk L）：ledger 貼出 (a) `git diff origin/v3 -- platform/abf_platform/web.py` 證明 `_HEADERS`、`LAUNCH_HEADERS`、`add_headers` 零改動；(b) 逐路由的實際回應標頭表（所有既有頁＋三條新路由，貼 `curl -sI` 或測試輸出），說明只有三條新路由與 HTML 預覽頁的標頭與 v3 不同；(c) 一段話說明 sandbox 為何擋得住 cookie／API／表單（不透明來源＋connect-src／form-action）。
4. 手動（寫進 `docs/TESTING.md` 並由 executor 實跑，截圖存檔名貼 ledger）：在 1440 與 390 寬、中文與英文四種組合，各截：完成頁含「預覽」連結的清單、PNG 預覽頁、（步驟 B）MultiQC 報告預覽頁、too_large 預覽頁——共 16 張（步驟 A 先交其中 3 類 12 張）。另以真 MultiQC 報告與一份 ampliseq `summary_report.html` 驗證圖表能顯示、點擊無法離開頁面。
5. 步驟 A、B 為兩個提交；A 提交時 `/run/report` 與 iframe 都不存在。

## 環境事實
- 現況（origin/v3，已查證）：所有結果檔走 `/run/file`（`web.py:run_file_get`），`web_board.download_headers`（web_board.py:1322）一律 `attachment`＋`application/octet-stream`＋nosniff＋`private, no-store`；全站 `_HEADERS`（web.py:85-89）CSP＝`default-src 'none'; style-src <STYLE 雜湊>; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`，X-Frame-Options＝DENY；只有 `/launch` 的 `LAUNCH_HEADERS`（web.py:96-98）多 `img-src 'self'`；`/launch/diagram` 用 `default-src 'none'; style-src 'unsafe-inline'`（web.py:967）。
- `add_headers` 中介層（web.py 檔尾）對所有回應 `setdefault` 全站標頭——路由自己設的標頭（如 SAMEORIGIN）不會被覆蓋。
- 讀檔上限 `jobs.RUN_FILE_MAX_BYTES = 26214400`（jobs.py:51），代理端 `abf_station/readfile.py:MAX_BYTES` 另寫同數；超過 → `actions.run_file` 回 `too_large`，不傳 bytes。讀到的答案存在 job 列 `RUN_FILE_CACHE_SECONDS`＝600 秒，同檔再問不重排 job——預覽頁與其後的 `/run/image`／`/run/report` 因此通常讀同一份答案；快取過期時後兩者回 404 屬可接受（頁面重整即恢復）。
- `web_finished._downloads` 已列出第一層檔的下載連結（最多 20 項、MultiQC 報告優先），測試 fs12–fs19 釘住其格式；交付包的其他列（報告、圖、方法段落）仍是「之後開放」，**不在本任務**。
- 既有被釘的格式（新連結只能加在其後）：`test_web_finished.py:301-311`（`>zeta.txt</a> <span class="muted">2.0 KB</span>`）、`:314-324`（MultiQC 連結 `…path=multiqc/multiqc_report.html">MultiQC 報告</a>`）、`:327-332`（too_large 無連結）、`:216-225`（fs08：交付包區無 `<form`、`<button`、`href="/download`）、`:262-278`（fs11：無 `<script`、`style=`、單一 `<style>`、`style-src` 雜湊）。
- PITFALLS（docs/PITFALLS.md）已查，相符項：
  - 「Tower Agent 傳輸刪除每個 0xFF 位元組，圖片／PDF 經 Platform 損毀，HTML／TSV／日誌無恙」（Symptom: images and PDFs served by Platform through the Tower Agent are corrupt…；Check: none automated，Touches 含 multiqc_report.html）。本任務走自家站台代理（base64 讀檔，`readfile.py` 比對大小），不經 Tower Agent，但 PNG 預覽仍須一條含 0xFF 位元組的逐位元組相等測試（va02）。
  - 第 58 條「`read_run_file`、`list_site_files` 在 ControlMaster 過期時誤報路徑被拒」（Check: `platform/tests/test_station_realpath_down.py`）：預覽頁遇 `site_unreachable` 要走既有 `render_file_page` 的「站台連不上」句，不得改寫成「路徑錯誤」。
  - 其餘（CSP／iframe／sandbox／web_board／web_finished）無相符條目。
- 瀏覽器層安全測試需要 Playwright；若執行環境沒有，va／vb03 的瀏覽器段改為 `skip`，ledger 貼手動結果與截圖，verifier 以 ledger 為準。

## 不做
- 下載路由 `/run/file` 的任何改動；不把下載改成 inline。
- JPG／GIF／PDF／TSV／文字檔預覽、非白名單的 HTML 預覽、`.htm`。
- 「全部下載／交付包 zip」、交付包其他列（報告、圖、方法段落）的開放；R Studio 介面看圖（畫面 9 既有，維護者原話後半）。
- 放寬任何其他頁的 CSP、`_HEADERS`、`LAUNCH_HEADERS`；在 `/run/preview` 以外任何頁加 `img-src` 或 `frame-src`。
- 新 job 種類、站台代理（`abf_station`）改動、25 MB 上限調整、串流／分段讀取大檔。
- 把報告內容改寫、消毒或抽取（原樣回傳，靠沙盒隔離）。

## 裁決（lead，2026-11-07，回應計畫撰寫者的六點）
1. HTML 預覽白名單先收 `multiqc_report.html` 與 `summary_report.html`；其他報告等認證方案目錄落地後逐一加入，不得在本件放寬成任意 .html。
2. `/run/report` 的 CSP 起點接受（沙盒不含 allow-same-origin，所以 script 即使 unsafe-eval 也碰不到網站）；真 MultiQC 報告載不出圖表時，只准放寬該路由並記入 ledger。
3. 瀏覽器層安全測試（報告 script 讀不到 cookie、打不到網站 API）**必須真的跑**：閱卷者用 `scripts/ui_check.py`／`webapp-testing`（Playwright）。真的跑不出來標 UNVERIFIED、不得 skip 當通過；本件 L 級，對抗審須自行跑一次該測試，通過前不掛自動合併。
4. 不動 STYLE 雜湊，改用 iframe 的 width／height 屬性——接受。
5. 「RStudio 介面要能看」由 `cli-fetch-publish-figure` 負責，本件不做。
6. 交付包其他列維持「之後開放」，圖庫相關由 `mcp-publish-figure` 處理——接受。

## 裁決（自動補，2026-11-07）
1. va04 與「不讀檔」矛盾：採選項一。清單（輸出頁、完成頁）只看副檔名／白名單、不讀檔，所以偽裝檔（`.png` 內容是 HTML、`.svg` 無 `<svg`）在清單**照樣出現**「預覽」連結；點進 `/run/preview` 才由 `kind_of` 讀位元組判斷，回「此檔類型不提供預覽」頁，`/run/image`、`/run/report` 對偽裝檔回 404。va04 的「清單沒有預覽連結」只適用副檔名不符或非白名單的檔（`.txt .tsv .bam .pdf .htm .jpg`、非白名單 `.html`）；偽裝檔只斷言預覽頁與 `/run/image`、`/run/report`。不採選項二（會增加站台讀取量）。
2. `kind_of` 簽名：兩段式。`kind_of(path)` 只看名稱，傳回候選類型（`png|svg|html|None`），供清單用；`kind_of(path, data)` 傳入位元組時再驗魔術位元組／`<svg`，不符傳回 None，供三條路由用。TC 只驗行為。
3. `/run/preview` 的 CSP：只有 PNG／SVG ready 頁帶 `img-src 'self'`；不提供預覽、等待、too_large、錯誤、站台連不上頁一律用不含 `img-src`、`frame-src`、`script-src` 的基礎 CSP。HTML ready 頁加 `frame-src 'self'`、無 `img-src`。TC 只斷言「無 frame-src、無 script-src」，不釘 img-src 有無。
4. vb04 語意更正：白名單看 basename，`multiqc/multiqc_report.html` 等子目錄下的白名單檔名**應通過**（TC-052 照此）；應 404 的是 `evil.html`、`multiqc_report.html.txt`、`multiqc_report.htm`。刪去原句「在 `x/` 之外仍通過」。
5. 作法 B-5：以上方「裁決（lead）4」為準，不動 STYLE、`STYLE_SHA256` 不變，iframe 用 `width`／`height` 屬性、無 `style=`；B-5 的「擇一」作廢。
6. 步驟歸屬與 skip：`va06`、`va09` 中涉及 `/run/report` 的斷言移到步驟 B（擁有者規則、未登入行為隨路由在步驟 B 驗）；步驟 A 只驗 `/run/preview`、`/run/image`。瀏覽器層 vb03（TC-053 至 TC-057）依 lead 裁決 3：不得 skip 當通過，沒真的跑出來標 UNVERIFIED。
7. 維護者原話第 1 條後半（R Studio 介面看圖）：依 lead 裁決 5 由 `cli-fetch-publish-figure` 負責，本件不做，列為不在範圍（TC-039）。lead 已裁決，視為同意。

## 裁決（lead，2026-11-08）
上次唯一失敗是環境：	est_no_schema_change 的鏡像 origin/v3 過舊（#381 已合併修好）與 	est_aws_ce 偶發。不改計畫，在 WSL 鏡像重抓 origin/v3 後原樣重跑；	est_aws_ce 若再偶發，單檔重跑確認綠即可，不得改測試。

## 裁決（lead，2026-11-08 14:30，回應 verifier FAIL：TC-078／086／099／095–098）
1. **核可三處既有測試的調整**（路由清單多 `/run/preview` 類新路由、路由表摘要值隨之更新、wording sweep 的表數 9→10 並納入 `web_preview.STRINGS`）：限「只因新增路由或新字串表而改」，斷言本身不得變弱；任何其他既有斷言被改一律退回。ledger 要逐處列出「改前→改後」讓 verifier 對照。
2. **TC-099 的 meta-refresh（自動重整）**：基準就有、不是本件造成，本件豁免；新增的預覽頁必須維持 0 個 serious／critical。lead 另開維護任務處理既有自動重整，不在本件做。
3. **TC-095–098（真 MultiQC 報告與圖片要人眼驗）**：改為合併後由 lead 以操作者身分用真實 run 驗，不是合併條件；verifier 標 UNVERIFIED(operator) 不算 FAIL，其餘條全 PASS 即可過關。
4. 推送、開 PR：網頁畫面 B 級，附 1440／390 × zh／en 四張截圖，掛自動合併（既有規則）。

## 裁決（dev-resolver，2026-11-11）
- **動作：needs-lead（category: hooks）**。帳本回覆 exit 3「ruling refused (never automatic: hooks); left with the lead」，即交給 lead；本件不會自動重派。
- **失敗不是偶發，重跑不會綠**。PR #384（head `6e7563e1`，與 worktree HEAD 相同）的必要檢查 `run_all` 紅，來源是 `shard 3/4`（run 42866919635 第 2 次嘗試，job 130017885374）。該分片輸出逐字為：`854 passed, 1 skipped, 1 warning`、`pytest exit code of each shard, in order:  0 0 0 0`、`platform tests: pytest exit 0, 1 skipped`、`FAIL (CI=true): 1 test(s) were skipped, and nothing may be skipped on CI`；`--retry-failed-once` 重跑同樣結果，`== FAILED twice ==`／`FAILED platform_shard_6_test.sh`。其餘 shard 1、2、4 皆 SUCCESS。
- **被跳過的那一條**：`SKIPPED [1] tests/test_web_result_viewer.py:636: UNVERIFIED: no Python with playwright (set ABF_PLAYWRIGHT_PYTHON)`，即 `test_tc053_054_055_056_057_the_report_cannot_reach_the_site`（TC-053 至 TC-057 瀏覽器層安全測試）。擋下它的規則在 `tests/platform_test.sh:444-446`（CI 模式下 skipped 不為 0 即 exit 1）。`.github/workflows/*.yml` 內搜尋 playwright／chromium 無任何結果，CI 上沒有瀏覽器。
- **測試案例本身沒有錯，所以不是 fix-contract**：test-case.md TC-053 寫「不得以 skip 當通過；沒真的跑出來閱卷標 UNVERIFIED」，與本計畫「裁決（lead，2026-11-07）」第 3 點「必須真的跑…不得 skip 當通過」一致；測試照此在沒有瀏覽器時 skip 並標 UNVERIFIED。衝突在「計畫要求瀏覽器測試留在測試套件」對上「CI 不准有任何 skip 而 CI 沒有瀏覽器」。
- **為何不能判 retry**：要讓 `run_all` 綠只有幾條路，每條都不是 resolver 能裁的：(1) 在 CI 工作流程裝 Playwright 與 Chromium 並設 `ABF_PLAYWRIGHT_PYTHON`，要改 `.github/workflows/`（受保護路徑）；(2) 改 `tests/platform_test.sh` 的不准 skip 規則（閘門檔，且屬放寬門檻，禁止）；(3) 把瀏覽器測試移出 CI 會跑的套件，等於改掉 lead 11-07 裁決第 3 點的方向。resolver 不得以跳過案例或放寬門檻把紅變綠。
- **工作本身的狀態**：ledger 記載 TC-053 至 TC-057 已在本機以 Playwright＋Chromium 真的跑過並通過；CI 上該分片其餘 854 條全過。lead 11-08 14:30 裁決第 1–4 點（三處既有測試調整、TC-099 豁免、TC-095–098 改合併後由操作者驗）不受本裁決影響。
- **另外看到、未調查**：同一 PR 的 `gitleaks` 與 `pip-audit`（security 工作流程）也是 FAILURE；`fail_reason` 只點名 `run_all`，是否為必要檢查、是否基準既有，本輪沒有證據，請 lead 一併確認。
- **下一輪要做什麼（由 lead 決定後才重派）**：lead 在上述 (1) 與 (3) 之間擇一並寫成新的裁決段。選 (1)：由有權限者改 CI 工作流程，之後原樣重跑檢查，不需重新實作、不改 `test_web_result_viewer.py`。選 (3)：須明寫瀏覽器測試改在哪裡跑、由誰驗，並由獨立 verifier 重新閱卷；斷言不得變弱。兩者都不得改動 `platform_test.sh` 的不准 skip 規則。

## 裁決（dev-resolver，2026-11-11，第二則：lead 11-11 裁決未被執行）
- **動作：retry**（帳本回覆 exit 0：`ruling 1/2 registered (retry); task is ready again`）。本則不取代上一則 dev-resolver 裁決的事實部分；上一則留給 lead 的二選一，lead 已在本檔最末段「裁決（lead，2026-11-11，回應 PR #384 CI 紅燈）」N～N+2 選定做法，本則只處理「該裁決沒有被做」。
- **證據一（紅燈原因與上次完全相同）**：PR #384 現在的 head 是 `424fea5c`，tests 工作流程 run 42981074537 的 `shard 1/4` 輸出逐字為 `SKIPPED [1] tests/test_web_result_viewer.py:636: UNVERIFIED: no Python with playwright (set ABF_PLAYWRIGHT_PYTHON)`、`724 passed, 1 skipped, 1 warning`、`FAIL (CI=true): 1 test(s) were skipped, and nothing may be skipped on CI`、`== FAILED twice ==`／`FAILED platform_shard_8_test.sh`；`run_all` 因此印 `not every shard succeeded`。shard 2、3、4 皆 SUCCESS。
- **證據二（lead 的做法一行都沒進分支）**：`origin/feat/web-result-viewer` 的 `platform/tests/test_web_result_viewer.py:633-636` 仍是 `py = os.environ.get("ABF_PLAYWRIGHT_PYTHON") or shutil.which("python3")` 接 `pytest.skip("UNVERIFIED: no Python with playwright (set ABF_PLAYWRIGHT_PYTHON)")`；分支上沒有 `scripts/dev/check_result_viewer_sandbox.py`（`scripts/dev/` 下只有 `check_settings_mobile.py`）。`6e7563e1` 之後分支新增的只有三個「Merge branch 'v3' into feat/web-result-viewer」（`9359d1c2`、`126dce67`、`424fea5c`），沒有任何針對本件的提交。
- **證據三（執行端看不到該裁決）**：worktree 內的計畫副本 `specs/web-result-viewer/plan.md` 只有四個裁決段（lead 11-07、自動補 11-07、lead 11-08、lead 11-08 14:30），沒有任何 11-11 的段落；worktree 停在 `6e7563e1`，落後遠端 47 個提交。佇列顯示 lead 於 11-11 12:25 與 14:55 兩次 retry 皆標 done，任務卻在 15:25 被重新掛回等待合併（`armed_at`），隨後同一條檢查再紅。另：lead 11-11 裁決段寫在「專長守則」之後，不在帳本慣例的位置（專長守則之前）。
- **為何判 retry**：實作本身沒有新問題（該分片其餘 724 條全過、另三個分片全綠），失敗是「已寫好的裁決沒有送到執行端」的流程問題；lead 選的做法不需要動 CI 工作流程，也不需要動 `tests/platform_test.sh` 的不准 skip 規則，所以上一則的 hooks 類別不再適用。
- **下一輪必須做的事（與前兩次重派不同之處）**：
  1. 開工前把 worktree 快轉到 `origin/feat/web-result-viewer`（只准 fast-forward 或一般 merge，不改寫歷史），並把本檔最新內容重新複製成 `specs/web-result-viewer/plan.md`；確認副本內看得到 lead 11-11 的 N～N+2 才往下做。
  2. 照 lead 11-11 裁決 N+1 的 (a)～(d) 實作，以該段文字為準：瀏覽器部分搬到 `scripts/dev/check_result_viewer_sandbox.py` 並在 `docs/TESTING.md` 補手動驗收一節；pytest 內保留不需瀏覽器的等價斷言（沿用原測試的攻擊樣本）；pytest 內不得留任何 `skip`／`skipif`；既有斷言一條都不得放寬。
  3. 推送前在本機以 `CI=true` 跑 `tests/run_all.sh`，確認輸出是 0 skipped 且全綠，把該輸出貼進 ledger。
  4. 推同一分支（不 force、不開新 PR）。**只要 `test_web_result_viewer.py` 還有 skip，或沒有新的實作提交，就不得回報為已掛自動合併**；做不到就回報失敗並寫明卡在哪裡。
  5. 改動後由獨立 verifier 重新閱卷（測試檔被改寫，不能沿用舊的 PASS）；瀏覽器內才能驗的幾條依 lead 裁決 (d) 標為待實機驗，列在 PR 內文。
- **界線**：不得新增或修改 `.github/workflows/*`、`tests/platform_test.sh` 或其他 `tests/*.sh` 閘門檔；lead 裁決提到的 `tests/check_settings_mobile_smoke_test.sh` 只是參考範例。若執行中發現非動這些檔不可，停下來回報失敗交 lead，不自行處理。
- **另外看到、未調查**：同一 PR 的 `gitleaks`（security 工作流程）仍是 FAILURE，`pip-audit` 已 SUCCESS；`fail_reason` 只點名 `run_all`。`gitleaks` 是否會擋合併、是否基準既有，本輪沒有證據，請 lead 確認。
- 這是本件帳本上的第 1 則裁決（上限 2）。若下一輪仍以同一原因失敗，下一則只能是 needs-lead。

## 裁決（dev-resolver，2026-11-11，第三則：開工前就被既有 worktree 擋下）
- **動作：needs-lead**（無類別；帳本回覆 exit 0：`web-result-viewer: handed to the lead by the resolver`）。本件不會自動重派。
- **失敗內容**（`fail_reason` 逐字）：`BLOCKED(setup): branch feat/web-result-viewer is already checked out in worktree wt/web-result-viewer-fix, so supervise cannot create wt/web-result-viewer`。
- **證據一（屬實）**：`git worktree list --porcelain` 顯示 `worktree …/wt/web-result-viewer-fix`／`HEAD 6e7563e147b4…`／`branch refs/heads/feat/web-result-viewer`；`wt/web-result-viewer` 這個目錄不存在。同一分支不能同時被兩個 worktree 取出，所以 supervise 建不出新的 worktree。
- **證據二（那個 worktree 裡沒有未保存的東西）**：`git status --short --branch` 只印 `## feat/web-result-viewer...origin/feat/web-result-viewer [behind 47]`，沒有任何已改或未追蹤的檔；`git log origin/feat/web-result-viewer..HEAD` 為空（0 個未推送的提交）；`git stash list` 為空。本機 HEAD `6e7563e1`，遠端 head `424fea5c`。
- **證據三（工作本身自上一則裁決後沒有前進）**：`origin/feat/web-result-viewer` 的 `platform/tests/test_web_result_viewer.py:636` 仍是 `pytest.skip("UNVERIFIED: no Python with playwright (set ABF_PLAYWRIGHT_PYTHON)")`；`scripts/dev/` 下只有 `check_chrome_login.py` 與 `check_settings_mobile.py`，沒有 `check_result_viewer_sandbox.py`；`6e7563e1..origin` 之間沒有任何非合併提交。也就是上一則 dev-resolver 裁決（第二則）的步驟 1–5 一步都還沒做，因為這一輪在建 worktree 時就停了。
- **為何不判 retry**：這次停在 supervise 的準備階段，還沒讀到計畫，所以在計畫裡再寫一則裁決改變不了下一輪的結果；本件已用掉 1 則 retry，第二則若再以同樣原因失敗就沒有額度了。「下一輪能否自行處理這個 worktree」沒有證據，不能憑猜測裁。移除或改用既有 worktree 是對 lead 自己建的工作目錄動手，resolver 不做。
- **不是 fix-contract、也不是 unverified-operator**：沒有任何測試案例被指為有錯；機器端也不是全綠（CI 的 `run_all` 仍會因上述 skip 而紅）。
- **請 lead 做的事（擇一，做完再重派）**：
  1. 釋放分支：把 `wt/web-result-viewer-fix` 從 worktree 清單移除（依證據二，裡面沒有未推送或未提交的內容），讓 supervise 能照常建立 `wt/web-result-viewer`；或
  2. 沿用既有 worktree：讓佇列／supervise 指向 `wt/web-result-viewer-fix`，並先把它快轉到 `origin/feat/web-result-viewer`（只准 fast-forward，不改寫歷史）。
- **重派後下一輪要做什麼**：原樣執行上一則 dev-resolver 裁決（第二則）的步驟 1–5 與其界線，依據是本檔最末段「裁決（lead，2026-11-11）」N～N+2；不需重新設計，也不得放寬任何斷言。
- **提醒**：本件帳本上已有 1 則裁決（上限 2）。lead 重派時請確認重派檔沒有 BOM，且 worktree 內的 `specs/web-result-viewer/plan.md` 是本檔最新內容。

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

## 裁決（lead，2026-11-11，回應 PR #384 CI 紅燈：瀏覽器測試在 CI 被跳過）
N. **事實**：PR #384 的 CI 分片 1 紅，原因只有一個——`platform/tests/test_web_result_viewer.py:636` 的 Playwright 測試在 CI 因「沒有裝 Playwright 的 Python」而 `pytest.skip`，而 CI 規定「任何測試都不准被跳過」（724 過、1 跳過 → 失敗）。其餘分片綠。PR 與基底的衝突 lead 已解（commit 6e7563e1）。
N+1. **做法（照 repo 既有慣例：需要真瀏覽器的檢查放 `scripts/dev/check_*.py`，不放 pytest，參考 `scripts/dev/check_settings_mobile.py` 與 `tests/check_settings_mobile_smoke_test.sh`）**：
  (a) 把該 Playwright 測試的瀏覽器部分搬成 `scripts/dev/check_result_viewer_sandbox.py`（用 `ABF_PLAYWRIGHT_PYTHON`，沒有就印明確訊息並非零結束），並在 `docs/TESTING.md` 補一節手動驗收步驟（標示為實機／瀏覽器驗，【實機驗】）；
  (b) 在 pytest 內保留**不需瀏覽器、CI 一定能跑**的等價斷言：回應標頭與頁面 HTML 層面驗證沙盒 iframe（`sandbox` 屬性不含 `allow-same-origin`、CSP、不可執行腳本的內容型別等，沿用原測試的攻擊樣本 `ATTACK`）；不得只刪除不補；
  (c) pytest 中不得再有任何 `skip`／`skipif`；全套 `tests/run_all.sh` 在 CI 條件下（`CI=true`）要 0 跳過、全綠。
  (d) 不得放寬任何既有斷言；原本瀏覽器內才能驗的那幾條，在 (a) 的腳本與 TESTING.md 中仍保留，並在 PR 內文列為「待實機驗」（UNVERIFIED-OPERATOR）。
N+2. PR #384 已存在並掛自動合併：直接推同一分支 `feat/web-result-viewer`（不 force、不開新 PR）。分批 commit＋push。