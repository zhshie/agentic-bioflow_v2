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
