# 網頁結果檢視：圖片預覽與沙盒 iframe 報告預覽 progress ledger

## 步驟 A（圖片預覽）完成
- /run/preview、/run/image、web_preview.py、列表預覽連結；28 個新測試通過；七個既有的路由清單測試只加不改。
- 此 commit 無 /run/report、無 <iframe。

## 步驟 B（沙盒 iframe 報告）完成
- /run/report、預覽頁的 iframe（`sandbox="allow-scripts"`、width／height 屬性、無 inline style）、HTML 就緒預覽頁的 `frame-src 'self'`、報告路由專用標頭。
- 真瀏覽器測試（TC-053 至 TC-057）：`test_tc053_054_055_056_057_*` 用 Playwright＋Chromium 真的跑過並通過（報告內 script 讀 cookie、`window.parent.document`、fetch `/settings`、fetch `/run/file`、`form.submit()` 全被擋，站台日誌沒有那些請求）。
- 路由清單釘死測試（八處）只加 `/run/report`，沒刪改。

## git diff --stat（對照步驟 A 之前的基準 d4dd182e）
DESIGN.md、docs/PLATFORM.md、docs/TESTING.md、web.py、web_board.py、web_finished.py、web_preview.py（新）、七個既有測試檔各改一行（只加路由）、test_web_result_viewer.py（新）、specs。`jobs.py`、`actions/__init__.py`、`abf_station/*` 差異為空。

## 爆炸半徑證明（TC-084）
(a) web.py 對基準的差異：只有三條新 handler（`run_preview_get`、`run_image_get`、`run_report_get`）、兩個共用輔助函式、三行路由註冊、檔頭文件；唯一被「刪」的一行是 import 行，加上 `web_preview`。`_HEADERS`、`LAUNCH_HEADERS`、`add_headers` 與既有 handler 零改動。
(b) 既有頁加上三條新路由後的回應標頭：`/`、`/settings`、`/usage`、輸出頁、完成頁、`/run/file` 的 CSP 與基礎逐字相同、`X-Frame-Options: DENY`、無 `img-src`／`frame-src`（`test_tc070_071_074_075_*`、`test_tc074_075_report_headers_*` 斷言）。與基準不同的只有：PNG／SVG 就緒的 `/run/preview`（加 `img-src 'self'`）、HTML 就緒的 `/run/preview`（加 `; frame-src 'self'`）、`/run/image`、`/run/report`（各有專用標頭）。
(c) 為何擋得住：報告所在的 iframe 為 `sandbox="allow-scripts"` 且報告路由的 CSP 也以 `sandbox allow-scripts` 開頭，兩者都不含 `allow-same-origin`，所以報告是不透明來源：讀不到本站 cookie、`window.parent.document` 丟跨來源錯誤；`connect-src 'none'` 擋 fetch／XHR／WebSocket；沒有 `allow-forms` 且 `form-action 'none'` 擋表單；沒有 `allow-top-navigation`、`allow-popups` 擋導走與開窗；`frame-ancestors 'self'` 加 `X-Frame-Options: SAMEORIGIN` 只讓本站框它；預覽頁本身無 script。

## STYLE 決定
`web_board.STYLE` 與 `STYLE_SHA256` 未動；圖用 `width="100%"`，iframe 用 `width="100%" height="800"` 屬性，頁面無 `style=`。

## CSP 放寬（TC-069）
未放寬。報告路由 CSP 即計畫所寫的字。真 MultiQC 圖表是否載得出（TC-095、TC-096）、截圖（TC-091 至 TC-094）、axe 掃描（TC-099）：UNVERIFIED，這個環境沒有真報告與瀏覽器截圖流程，步驟寫在 docs/TESTING.md 新增的手動一節。

## 與計畫的差異
- `web_board.render_file_page` 加了 `route` 參數（預設不變），讓預覽頁的重試／刷新回到 /run/preview。
- TC-065：路徑中的 `"allow-same-origin"` 以跳脫或百分比編碼出現，測試斷言它不以獨立帶引號的字出現、也不在 sandbox 屬性內。

## 全套後補
- test_web_wording_sweep 表清單加 web_preview.STRINGS（9→10）、test_k8s_launch 路由釘住 30→33（只加項）。
- test_mcp_launch_pipeline::test_no_schema_change 對 mirror 的 origin/v3 比 store.py 有差，本分支 store.py 對基準 d4dd182e 零差異，屬環境（基準漂移）；test_aws_ce 為偶發，單跑通過。

## 第二輪全套（鏡像 origin/v3 已更新到 fcb26614）
- test_no_schema_change 與 test_aws_ce 這次綠。新出現兩個紅：test_scope tc070（web_preview.py 缺 `# Nothing existing:` 標頭，已補）、test_web_guided_launch_preview:450（路由名過濾 `preview|sheet` 撞上計畫指定的 /run/preview；過濾式加排除 `/run/preview`，其餘斷言不動，超出計畫列的「只加項」範圍，請審閱者知悉）。

## 修正輪（2026-11-08）
- 截圖重拍為真預覽頁（PNG、iframe 報告、輸出分頁、完成頁）共 16 張；舊的 results/board 同圖已刪。
- axe：新預覽頁 0 違規；meta-refresh 是基準 d4dd182e 就有（screenshots/base-summary.md），非本任務新增。
- 無程式碼改動；在新 HEAD 重跑全套。

## 修正輪二（2026-11-08，回應 TC-078／086／093／099）
- TC-093：補拍 too_large 預覽頁 4 張，另補 none、site-unreachable、waiting 各 4 張（共 +16 張）。見 screenshots/summary.md。
- TC-099：預覽頁全部狀態都已掃描。serious／critical 只有既有的 meta-refresh（等待頁、輸出頁、完成頁），基準 d4dd182e 就有；本任務新增的 PNG／報告預覽頁為 0。不改既有自動重整（超出計畫範圍），是否另開任務由維護者決定。
- TC-078／TC-086：下列三處既有測試的改動是新增路由與新字串表的必然結果，我不能自行核可，請 lead／維護者補核可。沒有任何斷言被弱化成讓錯誤結果通過：
  1. test_web_guided_launch_preview.py:450，過濾式排除 `/run/preview`（計畫指定該路由名；此測試本意是向導不得新增「樣本表預覽」路由，排除值只此一條）。
  2. test_web_wording_sweep.py：`web_preview.STRINGS` 加入 tables()、9 改 10。`test_every_zh_table_is_covered` 掃描 `web*.py` 全部中文表，與 tables() 做集合相等比較，新檔 `web_preview.py` 依計畫命名就一定使這個測試紅，不改它就不可能綠。TC-086 的措辭檢查本身已在 test_web_result_viewer.py（`test_tc086_087_wording_and_states`）自己呼叫 `banned_in`，不依賴 sweep 檔。
  3. test_k8s_launch.py:1434，路由數 30 改 33、換雜湊（新增 /run/preview、/run/image、/run/report 三條路由）。
- 無程式碼改動。

## 修正輪三（2026-11-10，依 lead 11-08 14:30 裁決）
三處既有測試調整已由 lead 核可，改前→改後逐處：
1. test_k8s_launch.py:1434：`len(got)==30` 與雜湊 e182004a… → `len(got)==33` 與雜湊 67f6aa6d…（三條新路由）。
2. test_web_guided_launch_preview.py:450：路由過濾 `preview|sheet` → 同式加 `and m != "/run/preview"`。
3. test_web_wording_sweep.py：tables() 加 `web_preview.STRINGS`；`len(found)==9` → `==10`。
TC-095–098 為 UNVERIFIED(operator)，合併後由 lead 驗。TC-099 meta-refresh 為基準既有，豁免。無程式碼改動。

修正輪四（ADVERSARY ReDoS）：web_preview.py 的 SVG 檔頭檢查由回溯正則改為線性掃描 _svg_head（行為同：BOM、空白、<?xml?>、註解、DOCTYPE 後接 <svg）；新增 test_svg_head_check_is_linear_time。無既有測試被改。

修正輪五（ADVERSARY）：(1) web_preview.image_headers 的 CSP 補回 frame-ancestors 'none'（TC-075，圖片路由與其他路由同，只有報告路由例外）；(2) 新增 _doctype_end，DOCTYPE 內部子集 [ ... ] 與引號、子集註解內的 > 不再提早結束，Illustrator 匯出的真 SVG 可預覽；仍為單趟線性。測試：test_web_result_viewer.py 的 test_tc070_071_074_075 補圖片路由 frame-ancestors 斷言，新增 test_svg_with_internal_dtd_subset_and_image_csp。

## 修正輪六（2026-11-11，依 lead 11-11 裁決 N+1 (a)–(d)：瀏覽器測試在 CI 被跳過）
- [x] (a) 瀏覽器部分搬到 `scripts/dev/check_result_viewer_sandbox.py`（DRIVER 與五條斷言原樣搬過去，攻擊樣本直接 import 測試檔的 `ATTACK`）；沒有 Playwright 或沒有瀏覽器時印 `UNVERIFIED: …` 並以 77 結束，不印 PASS。`docs/TESTING.md` web-result-viewer 一節加第 0 步【實機驗】。
- [x] (b) pytest 保留不需瀏覽器的等價斷言：`test_tc053_054_055_056_057_the_attacking_report_is_served_sandboxed`（同一個 `ATTACK`）：外層頁恰一個 iframe、`sandbox` 屬性值恰為 `"allow-scripts"`、無 srcdoc、頁面無 script、報告原文不在外層頁；`/run/report` 位元組相同，CSP 逐指令解析後 `sandbox` 恰為 `allow-scripts`、`connect-src`／`form-action`／`default-src`／`frame-src`／`base-uri` 皆 `'none'`、沒有任何指令允許網路來源、無 Set-Cookie／CORS 標頭；登入 cookie 值不在本文與標頭；同一份位元組經 `/run/image` 為 404、經 `/run/file` 為 attachment＋octet-stream＋nosniff；改名 `evil.html` 則 404；三條路由不接受 POST。
- [x] (c) `test_web_result_viewer.py` 內沒有任何 skip／skipif／xfail；`test_tc053_057_browser_check_is_a_manual_script_and_nothing_here_is_skipped` 釘住這一點，並釘住腳本存在、用同一個 ATTACK、保留原五條斷言、沒有 Playwright 時結束碼 77 且不印 PASS、TESTING.md 有【實機驗】一節。
- [x] (d) 既有斷言沒有放寬：本輪只動 `test_web_result_viewer.py` 的瀏覽器測試那一段（刪去的是 Playwright 測試本體，其五條斷言逐條移到腳本），其他測試檔零改動；CI 工作流程與 shell 閘門檔零改動（腳本的 smoke 檢查因此放在 pytest，不新增 shell 測試檔）。
- 實機結果（2026-11-11，WSL，平台 venv 的 Python＋系統 python3 的 Playwright／Chromium，`cd platform && python ../scripts/dev/check_result_viewer_sandbox.py`，結束碼 0）：
  ```
  the report's script wrote: {"cookie":"ERR:SecurityError","parent":"ERR:SecurityError","form":"called","settings":"ERR:TypeError","file":"ERR:TypeError"}
  the site received: [('GET', '/run/preview?run=id-ann-done&path=multiqc_report.html'), ('GET', '/run/report?run=id-ann-done&path=multiqc_report.html')]
  ok   TC-053 the report cannot read the login cookie
  ok   TC-054 fetch of /settings is blocked and never reaches the site
  ok   TC-055 fetch of /run/file is blocked and never reaches the site
  ok   TC-056 window.parent.document throws
  ok   TC-057 the form sends nothing and the outer page stays
  check_result_viewer_sandbox: PASS
  ```
  這是 executor 自己跑的，不是獨立驗收；TC-053 至 TC-057 的瀏覽器層在 PR 內文仍列「待實機驗」（UNVERIFIED-OPERATOR），由 verifier／lead 重跑該腳本。
- 單檔：`tests/test_web_result_viewer.py` 49 過、0 跳過。
- [x] 全套（CI 條件）：2026-11-11 在 `ad6f1ade` 以 `CI=true ~/.local/bin/abf-fast-suite <worktree> --retry-failed-once` 跑（即 `CI=true bash tests/run_all.sh --retry-failed-once`，在 WSL 鏡像上）。輸出：
  ```
  abf-fast-suite: worktree …/wt/web-result-viewer at ad6f1ade9609ba08f1afb00837158c4f6703497f, mirror …/abf-mirror/web-result-viewer
  platform_shard_1_test.sh … platform_shard_8_test.sh   ok（八個分片全 ok，沒有重跑）
  151/151 passed
  all green
  ```
  `tests/platform_test.sh` 在 `CI=true` 下只要有任何 skipped 就讓該分片失敗；八個分片皆 ok 即 0 skipped。上一輪讓 CI 紅的 `platform_shard_8_test.sh`（當時 `1 skipped`）這次 ok。
- 本輪（rerun 20261111-1956）沒有新的程式或測試改動：(a)–(d) 已在 `8b3c928c`（RED）、`ad6f1ade`（GREEN）完成，本輪只做全套驗證並補這段紀錄。尚未推送，由 lander 推同一分支。
