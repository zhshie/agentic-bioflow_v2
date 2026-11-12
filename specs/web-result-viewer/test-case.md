# 測試案例：網頁結果檢視（圖片預覽與沙盒 iframe 報告預覽）

**規格**：`specs/web-result-viewer/plan.md`（本任務沒有獨立 spec.md，計畫即規格，含維護者 11-07 定案原話與兩段裁決）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「站台」是平台連到的運算站台；「預覽頁」是 `/run/preview`；「圖片路由」是 `/run/image`；「報告路由」是 `/run/report`；「下載路由」是既有的 `/run/file`；「基礎標頭」是 v3 目前全站頁面的安全標頭（`_HEADERS`）；CSP 是網頁安全政策標頭，決定頁面能載入什麼。「偽裝檔」指副檔名是 .png／.svg 但內容不是圖的檔案。自動測試全部寫在 `platform/tests/test_web_result_viewer.py`，每條測試的註解寫明 TC 編號。

維護者原話對照：
- 「Q1: (C)也要，在R studio介面要能看，網站上要能檢視」：網站這一半 = TC-003、TC-013、TC-040；R Studio 那一半 = TC-039（不在範圍）。
- 11-07 定案六項：完成頁列出並可下載 = TC-001、TC-002、TC-012；PNG／SVG 用 img、SVG 不內嵌 = TC-013、TC-018、TC-019；HTML 沙盒 iframe、不含 allow-same-origin、不能提交表單、不能存取網站資料、專用路由與專用 CSP = TC-040 至 TC-050、TC-057、TC-070 至 TC-075；圖片先做、iframe 後做 = TC-085；安全測試 = TC-053 至 TC-057、TC-059、TC-061、TC-062、TC-078；截圖 = TC-091 至 TC-094。
- DESIGN.md 限制「預覽頁不得有 script、style=」= TC-007、TC-015、TC-044、TC-077。

## User Story 1 — 完成頁與輸出頁列出結果檔、可下載、可預覽的檔多一個「預覽」連結（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話：完成頁列出 run 結果檔並可下載 | 功能 | 登入者本人已完成的 run，站台第一層有 `zeta.txt`（2.0 KB）與 `multiqc/multiqc_report.html` | 開完成頁 | 清單列出這些檔；`zeta.txt` 一列逐字仍是 `>zeta.txt</a> <span class="muted">2.0 KB</span>`，MultiQC 連結逐字仍是 `…path=multiqc/multiqc_report.html">MultiQC 報告</a>`（既有 fs12 釘住的格式不變） | 自動：`test_web_result_viewer.py` |
| TC-002 | 輸出頁下載格不變 | 功能 | 同上，開輸出頁（Outputs） | 看 `zeta.txt` 的下載格 | 既有「下載」連結逐字仍在，仍指向 `/run/file?run=…&path=…` | 自動 |
| TC-003 | 作法 A-5；va11 | 功能 | 完成頁清單中有 `plot.png` | 看 `plot.png` 那一列 | 既有「下載」連結逐字仍在，其後多一個連結 `href="/run/preview?run=…&amp;path=…"`（文字為「預覽」，英文頁為對應英文） | 自動 |
| TC-004 | 作法 A-5；va11 | 功能 | 輸出頁中有 `plot.png` | 看 `plot.png` 的下載格 | 既有「下載」連結逐字仍在，其後有同形的預覽連結 | 自動 |
| TC-005 | 作法 A-5 | 功能 | 兩頁都有 `fig.svg` | 看該列 | 兩頁都在「下載」後有預覽連結 | 自動 |
| TC-006 | 作法 共通決定、裁決 1 | 功能 | 兩頁都有 `multiqc_report.html` 與 `summary_report.html`（也含大寫 `PLOT.PNG`） | 看這些列 | 每個都在「下載」後有預覽連結 | 自動 |
| TC-007 | 共通決定；DESIGN.md「no inline style」 | 功能 | 兩頁都含可預覽檔 | 檢查整頁 HTML | 沒有因預覽而多出 `<img`、`<iframe`、`<script`、`<form`、`<button`、`style=`；預覽入口只是 `<a href>` 純連結；既有 fs08（交付包區無 form／button／`href="/download`）與 fs11（無 script、style=，單一 `<style>`）仍成立 | 自動 |
| TC-008 | 不做：JPG／GIF／PDF／TSV／文字檔預覽、`.htm` | 不在範圍 | 兩頁都有 `a.txt`、`b.tsv`、`c.bam`、`d.pdf`、`e.htm`、`f.jpg`、`g.gif` | 看這些列 | 這些列沒有預覽連結，格式與原來完全一樣，仍可下載 | 自動 |
| TC-009 | 不做：非白名單 HTML 預覽；裁決 1 | 不在範圍 | 兩頁都有 `evil.html` | 看該列 | 沒有預覽連結，仍可下載 | 自動 |
| TC-010 | 裁決（自動補）1 | 功能 | 兩頁都有 `fake.png`（內容其實是 HTML）與 `fake.svg`（內容無 `<svg`） | 看這兩列；清單不讀檔 | 清單只看副檔名，所以這兩列照樣出現預覽連結；本 TC 不要求清單攔下它們（攔截在 TC-022、TC-023） | 自動 |
| TC-011 | va05；原話：超過 25MB 顯示 too_large | 例外 | 站台列表中 `big.png` 大小 26214401 位元組 | 開輸出頁與完成頁 | 兩頁都沒有 `big.png` 的預覽連結，仍顯示「大於 25 MB」文字（完成頁維持既有 too_large 無連結格式） | 自動 |
| TC-012 | 共通決定：下載路由不改；原話：可下載 | 功能 | 可下載的 `plot.png` | 開 `/run/file?run=…&path=plot.png` | 回應仍是 attachment＋`application/octet-stream`＋nosniff＋`private, no-store`，內容原樣，不是 inline | 自動 |

## User Story 2 — PNG／SVG 以 img 預覽（步驟 A，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 步驟 A-1；va01 | 功能 | 本人 run 的 `plot.png` 是真 PNG（開頭 `\x89PNG\r\n\x1a\n`），讀檔答案已就緒 | 開 `/run/preview?run=…&path=plot.png` | 200；主欄含 `<img src="/run/image?run=…&amp;path=plot.png"`，alt 為檔名 | 自動 |
| TC-014 | 步驟 A-2；va01；裁決 3 | 功能 | 同 TC-013 | 看預覽頁回應標頭 | CSP 含 `img-src 'self'`、`default-src 'none'`、`form-action 'self'`、`frame-ancestors 'none'`、`base-uri 'none'`，不含 `script-src`、`frame-src`；X-Frame-Options 為 DENY | 自動 |
| TC-015 | 步驟 A-2；DESIGN.md | 功能 | 同 TC-013 | 檢查預覽頁 HTML | 不含 `<script`、不含 `style=`，只有單一 `<style>` | 自動 |
| TC-016 | 步驟 A-3；va02 | 功能 | 同 TC-013 | 開 `/run/image?run=…&path=plot.png` | 200；Content-Type `image/png`；`X-Content-Type-Options: nosniff`；`Cache-Control: private, no-store`；CSP 以 `default-src 'none'` 開頭且含 `sandbox`；X-Frame-Options DENY；沒有 `Content-Disposition` | 自動 |
| TC-017 | va02；PITFALLS 0xFF 條目 | 功能 | PNG 內容含多個 0xFF 位元組 | 取 `/run/image` 回應本文 | 與來源檔逐位元組完全相同（一個位元組都不能少） | 自動 |
| TC-018 | 原話：SVG 不內嵌進頁面；va03 | 功能 | `fig.svg` 內含 `<svg …><script>alert(1)</script></svg>`，已就緒 | 開預覽頁 | 頁面有 `<img` 指向 `/run/image`；頁面文字不含 `<svg`，也不含 `alert(1)` | 自動 |
| TC-019 | 步驟 A-3；va03 | 功能 | 同 TC-018 | 開 `/run/image` | Content-Type `image/svg+xml`；CSP 含 `sandbox` 與 `default-src 'none'`，不含 `script-src`；同樣有 nosniff 與 `private, no-store` | 自動 |
| TC-020 | 共通決定：不接受指定 MIME 的參數 | 例外 | 同 TC-013 | 開 `/run/image?run=…&path=plot.png&type=text/html`（及 `content_type=`、`mime=`） | Content-Type 仍是 `image/png`，額外參數沒有效果 | 自動 |
| TC-021 | 共通決定：副檔名不分大小寫 | 功能 | 真 PNG 檔名為 `PLOT.PNG` | 開預覽頁 | 與 TC-013 同：有 `<img` 預覽 | 自動 |
| TC-022 | 共通決定；va04；裁決（自動補）1 | 例外 | `fake.png` 內容是 HTML 文字 | 開預覽頁 | 200，顯示「此檔類型不提供預覽」＋下載連結＋返回連結；沒有 `<img`、`<iframe` | 自動 |
| TC-023 | va04 | 例外 | `fake.svg` 內容無 `<svg`（純文字） | 開預覽頁 | 同 TC-022：不提供預覽頁，無 `<img`、`<iframe` | 自動 |
| TC-024 | va04；步驟 A-3 | 例外 | `fake.png`、`fake.svg` | 開 `/run/image` | 404，本文為空，不渲染頁面、不說原因 | 自動 |
| TC-025 | va04；原話：非允許副檔名不預覽 | 例外 | 檔案 `a.txt`、`b.tsv`、`c.bam`、`d.pdf`、`e.htm`、`f.jpg`、`evil.html` 各自就緒 | 逐一開預覽頁 | 每個都是 200「此檔類型不提供預覽」頁，有下載與返回連結，沒有 `<img`、`<iframe` | 自動 |
| TC-026 | va04 | 例外 | 同 TC-025 的檔 | 逐一開 `/run/image` | 全部 404、本文為空 | 自動 |
| TC-027 | va05；原話：超過 25MB 顯示 too_large | 例外 | 站台列表 `big.png` 大小 26214401，讀檔答案為 too_large | 直接開預覽頁 | 顯示 too_large 那句（「檔案大小 …，大於網頁下載上限 25 MB。請於站台取得：…」），沒有 `<img` | 自動 |
| TC-028 | va05 | 例外 | 同 TC-027 | 開 `/run/image` | 404、本文為空 | 自動 |
| TC-029 | va07 | 例外 | 尚無讀檔答案（loading） | 開預覽頁 | 等待頁：有「◌」符號與等待文字，含 15 秒自動重整，沒有 `<img` | 自動 |
| TC-030 | va07 | 例外 | 同 TC-029 | 開 `/run/image` | 404、本文為空 | 自動 |
| TC-031 | PITFALLS 58 | 例外 | 讀檔答案為 `site_unreachable` | 開預覽頁 | 顯示既有的「站台連不上」那句，不是「路徑錯誤」；沒有 `<img` | 自動 |
| TC-032 | 步驟 A-1（error） | 例外 | 讀檔答案為其他錯誤（例如 failed、no_answer） | 開預覽頁 | 顯示對應的既有錯誤句；若有「重試」連結，指向 `/run/preview`（不是 `/run/file` 下載）；沒有 `<img` | 自動 |
| TC-033 | va06；原話：擁有者規則 | 例外 | 登入者 A，開別人（B）的 run 的預覽頁 | 開 `/run/preview?run=<B 的 run>&path=plot.png` | 回 404 的「找不到」頁（與 `/run/file` 對別人 run 的同一個 404 頁，不重複請求的 id）；沒有排任何讀檔 job | 自動 |
| TC-034 | va06 | 例外 | 同 TC-033 | 開 `/run/image` | 404、本文為空 | 自動 |
| TC-035 | va06 | 例外 | 未登入 | 開 `/run/preview` 與 `/run/image` | 與未登入開 `/run/file` 的回應相同（同狀態碼、同導向），沒有任何檔案內容 | 自動 |
| TC-036 | 步驟 A-1 | 功能 | 同 TC-013 | 看預覽頁主欄下方 | 有「下載」連結指向 `/run/file?run=…&path=…`，與返回連結 | 自動 |
| TC-037 | 步驟 A-1；plan 說明（等待頁重用） | 例外 | 讀檔答案為 loading | 看等待頁的自動重整目標 | 重整目標是同一個 `/run/preview?run=…&path=…`，不是 `/run/file`（否則等一次就變成下載）；就緒後重整即看到圖 | 自動 |
| TC-038 | va10；DESIGN.md 每畫面有英文 | 功能 | 同 TC-013 | 開 `/run/preview?…&lang=en` | 頁面文字為英文，無中文殘留；連結帶 `lang=en`；`<html lang>` 為英文 | 自動 |
| TC-039 | 原話第 1 條後半：R Studio 介面看圖；裁決 5、（自動補）7 | 不在範圍 | 看這次的所有變更 | 檢查變更清單與畫面 9（Downstream）的程式 | 沒有改動 R Studio／下游畫面（畫面 9）任何程式或字串；此事由 `cli-fetch-publish-figure` 負責，本件不做 | 手動：閱卷者讀 `git diff`（`docs/TESTING.md` 新增手動一節列出此檢查） |

## User Story 3 — 白名單 HTML 報告以沙盒 iframe 預覽（步驟 B，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 步驟 B-1；vb01；原話：沙盒 iframe | 功能 | 本人 run 的 `multiqc_report.html` 已就緒 | 開預覽頁 | 恰好一個 `<iframe`，其 `sandbox` 屬性值完全等於 `allow-scripts` | 自動 |
| TC-041 | 原話：sandbox 不含 allow-same-origin | 功能 | 同 TC-040 | 檢查 iframe 屬性與整頁 | 整頁都找不到 `allow-same-origin` | 自動 |
| TC-042 | 原話：不能提交表單；步驟 B-1 | 功能 | 同 TC-040 | 檢查 iframe 屬性 | 不含 `allow-forms`、`allow-popups`、`allow-top-navigation`（含 `-by-user-activation`）、`allow-modals`、`allow-downloads` | 自動 |
| TC-043 | 步驟 B-1 | 功能 | 同 TC-040 | 檢查 iframe 其他屬性 | `src` 指向 `/run/report?run=…&path=…`；`title` 為檔名；`referrerpolicy="no-referrer"` | 自動 |
| TC-044 | 步驟 B-1、B-5；裁決（lead）4 | 功能 | 同 TC-040 | 檢查頁面 | 有一句說明（報告在隔離框內顯示，其中的程式不能讀取本站資料；不承諾連結可點）、下載連結、返回連結；iframe 以 `width`／`height` 屬性定大小，頁面無 `style=`、無 `<script`；單一 `<style>` | 自動 |
| TC-045 | 步驟 B-2；vb01 | 功能 | 同 TC-040 | 看 HTML 預覽頁回應標頭 | CSP 為基礎 CSP 加 `frame-src 'self'`；不含 `img-src`、`script-src`、任何 `unsafe-` | 自動 |
| TC-046 | 步驟 B-2；裁決 3 | 例外 | PNG 預覽頁、「不提供預覽」頁、等待頁、too_large 頁、錯誤頁 | 看這些頁的回應標頭 | 全部沒有 `frame-src`，也沒有 `script-src` | 自動 |
| TC-047 | 步驟 B-3；vb02 | 功能 | 同 TC-040 | 開 `/run/report?run=…&path=multiqc_report.html` | 200；`Content-Type: text/html; charset=utf-8`；nosniff；`Cache-Control: private, no-store`；`Referrer-Policy: no-referrer` | 自動 |
| TC-048 | 步驟 B-3；vb06 | 功能 | 同 TC-047 | 看框架嵌入相關標頭 | `X-Frame-Options: SAMEORIGIN`（不被預設 DENY 蓋掉）且 CSP 含 `frame-ancestors 'self'` | 自動 |
| TC-049 | 步驟 B-3；vb02；原話：不含 allow-same-origin | 功能 | 同 TC-047 | 看報告路由的 CSP | 含 `sandbox allow-scripts`，整個 CSP 不含 `allow-same-origin`（直接在新分頁開也是不透明來源，讀不到 cookie） | 自動 |
| TC-050 | 步驟 B-3；vb02；原話：不能提交表單、不能存取網站資料 | 功能 | 同 TC-047 | 看報告路由的 CSP | 含 `connect-src 'none'`、`form-action 'none'`、`default-src 'none'`、`frame-src 'none'`、`base-uri 'none'` | 自動 |
| TC-051 | 裁決 1 | 功能 | 本人 run 的 `summary_report.html` 已就緒 | 開預覽頁與報告路由 | 預覽頁有 iframe（sandbox 同 TC-040）；報告路由 200 | 自動 |
| TC-052 | 裁決（自動補）4 | 功能 | 本人 run 的 `multiqc/multiqc_report.html`（子目錄下的白名單檔名）已就緒 | 開預覽頁與報告路由 | 白名單看檔名，子目錄不影響：預覽頁有 iframe，報告路由 200 | 自動 |
| TC-053 | 原話：安全測試，報告內 script 無法讀 cookie；vb03 瀏覽器層；裁決 3 | 功能 | 用真瀏覽器（Playwright）登入；報告內有 script 試讀 `document.cookie` 並把結果寫進報告自己的 DOM | 開預覽頁，等報告跑完 | 報告 DOM 顯示的是 SecurityError 或空字串；任何位置都讀不到 `abf_web` cookie 的值。不得以 skip 當通過；沒真的跑出來閱卷標 UNVERIFIED | 自動：Playwright |
| TC-054 | 原話：無法呼叫網站 API；vb03 | 功能 | 同 TC-053；報告 script 執行 `fetch('/settings')` 並把結果寫進 DOM | 開預覽頁 | 結果為被擋（錯誤），拿不到 `/settings` 內容；站台日誌沒有收到來自報告的 `/settings` 請求 | 自動：Playwright |
| TC-055 | 原話：無法呼叫網站 API；vb03 | 功能 | 同 TC-053；報告 script 執行 `fetch('/run/file?…')` | 開預覽頁 | 同 TC-054：被擋，拿不到檔案，日誌沒有該請求 | 自動：Playwright |
| TC-056 | 原話：不能存取網站資料；vb03 | 功能 | 同 TC-053；報告 script 讀 `window.parent.document` | 開預覽頁 | 丟出跨來源錯誤，讀不到外層頁面任何內容 | 自動：Playwright |
| TC-057 | 原話：不能提交表單；vb03 | 功能 | 同 TC-053；報告 script 建立指向本站的表單並 `form.submit()` | 開預覽頁 | 沒有任何請求送到本站（日誌無紀錄）；外層預覽頁仍留在原頁、沒有被導走 | 自動：Playwright |
| TC-058 | 不做：報告內容改寫、消毒或抽取 | 不在範圍 | 報告含自己的 script、樣式、特殊位元組（含 0xFF） | 取報告路由本文 | 與來源逐位元組相同，沒有被改寫或刪減 | 自動 |
| TC-059 | vb04；原話：非允許副檔名不預覽；裁決（自動補）4 | 例外 | 檔案 `evil.html`、`multiqc_report.html.txt`、`multiqc_report.htm` 各自就緒 | 逐一開報告路由 | 全部 404、本文為空 | 自動 |
| TC-060 | vb04 | 例外 | 白名單 `multiqc_report.html` 但讀檔答案為 loading，或為錯誤 | 開報告路由 | 404、本文為空 | 自動 |
| TC-061 | vb05；原話：超過 25MB 顯示 too_large | 例外 | `multiqc_report.html` 大小 26214401，答案為 too_large | 開預覽頁 | 顯示 too_large 那句，沒有 `<iframe` | 自動 |
| TC-062 | vb05 | 例外 | 同 TC-061 | 開報告路由 | 404、本文為空 | 自動 |
| TC-063 | va06／vb；擁有者規則 | 例外 | 登入者 A，開別人 run 的白名單報告 | 開預覽頁與報告路由 | 預覽頁為「找不到」404 頁；報告路由為空本文 404；沒有排任何 job | 自動 |
| TC-064 | va06 | 例外 | 未登入 | 開報告路由 | 與未登入開 `/run/file` 的回應相同，沒有檔案內容 | 自動 |
| TC-065 | vb09 | 例外 | `path` 參數含引號、`<`、`>`、`"allow-same-origin"` | 開預覽頁 | 頁面內輸出全部被跳脫；iframe 的 sandbox 仍恰為 `allow-scripts`；整頁無 `allow-same-origin` | 自動 |
| TC-066 | 共通決定：不接受指定 MIME 的參數 | 例外 | 白名單報告就緒 | 開 `/run/report?…&type=text/plain`（及其他 MIME 參數） | Content-Type 仍是 `text/html; charset=utf-8`，參數無效果 | 自動 |
| TC-067 | va10 | 功能 | 同 TC-040 | 開 `?lang=en` 的 HTML 預覽頁 | 說明句、連結為英文，iframe 規則不變 | 自動 |
| TC-068 | 步驟 B；va07 | 例外 | 白名單報告的讀檔答案為 loading | 開預覽頁 | 等待頁（有符號與文字、15 秒重整回到預覽頁），沒有 `<iframe` | 自動 |
| TC-069 | 步驟 B-3 末條；裁決 2 | 例外 | 實作者若因真 MultiQC 載不出圖表而放寬報告路由的 CSP | 讀 ledger 與 `git diff` | ledger 記下放寬的字與原因；放寬只出現在報告路由；`sandbox`（不含 allow-same-origin）、`connect-src 'none'`、`form-action 'none'`、`frame-ancestors 'self'` 四項未變；沒放寬就寫「未放寬」 | 手動：閱卷者讀 ledger 與 diff |

## User Story 4 — 其他頁面一個字都不放寬、版面與文件、手動驗證（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | va08；不做：放寬其他頁 | 不在範圍 | 輸出頁、完成頁（含預覽連結） | 比對回應標頭與基礎標頭 | CSP 與所有標頭逐字與基礎相同；不含 `img-src`、`frame-src` | 自動 |
| TC-071 | va08、vb07 | 不在範圍 | `/`、`/settings`、`/usage`、`/login`、`/c/<rid>` | 比對標頭 | 與基礎逐字相同，不含 `img-src`、`frame-src` | 自動 |
| TC-072 | va08；不做：下載路由改動、改 inline | 不在範圍 | 任一可下載檔 | 開 `/run/file` | 標頭不變：attachment＋`application/octet-stream`；不含 `img-src`；既有 `test_results_files.py:299-301` 的斷言不動且仍過 | 自動 |
| TC-073 | vb07；不做：放寬 LAUNCH_HEADERS | 不在範圍 | `/launch` 與常數 `LAUNCH_HEADERS` | 比對與 v3 | 內容完全不變；`/launch` 仍是它自己既有的標頭 | 自動 |
| TC-074 | 計畫：img-src 只出現在 /run/preview | 不在範圍 | 全站所有頁面與新路由 | 掃描各回應 CSP | `img-src` 只出現在既有 `/launch`，與 PNG／SVG 就緒的 `/run/preview`；`frame-src` 只出現在 HTML 就緒的 `/run/preview`；其餘新舊頁都沒有 | 自動 |
| TC-075 | vb06 | 功能 | 預覽頁、`/`、`/settings`、輸出頁、完成頁、`/run/image` | 看標頭 | 全部 `X-Frame-Options: DENY` 且 CSP 含 `frame-ancestors 'none'`（只有報告路由例外，見 TC-048） | 自動 |
| TC-076 | 範圍：web.py 只新增；完成標準 3(a) | 不在範圍 | `git diff v3...HEAD -- platform/abf_platform/web.py` | 讀差異 | `_HEADERS`、`LAUNCH_HEADERS`、`add_headers` 與既有 handler 零改動；差異只有三條新 handler 與其註冊行 | 手動：閱卷者讀 diff |
| TC-077 | 裁決（lead）4；DESIGN.md「Single stylesheet」 | 功能 | 預覽頁各狀態 | 比對樣式 | `web_board.STYLE` 與 `STYLE_SHA256` 不變；預覽頁只有單一 `<style>`，其雜湊與全站相同；`test_results_files.py:707`、`test_web_board.py:876-888` 不改且仍過 | 自動 |
| TC-078 | 完成標準 2；原話：tc049 類測試不得被改弱 | 功能 | `git diff v3...HEAD -- platform/tests/` | 逐檔讀差異 | `test_web_guided_launch_2d.py::test_tc049_other_pages_are_as_before`、`test_results_files.py:299-301,707`、`test_web_chrome_origin.py:68`、`test_web_board.py:876-888`、`test_web_finished.py` fs08／fs11／fs12／fs14 沒有任何刪行或改動的斷言；其他既有測試檔只有新增行 | 手動：閱卷者讀 diff |
| TC-079 | 範圍：路由清單釘死測試只准加項；va09 | 功能 | `test_dataset_cli.py`、`test_cleanup_offer.py`、`test_confirm_page.py`、`test_web_board.py`、`test_owner_binding.py`、`test_web_downstream.py` 的路由清單 | 讀差異並 grep `/run/file` 確認有無遺漏 | 每個清單都已加入三條新路由（步驟 A 時 preview、image；步驟 B 加 report），只有新增行、無刪改；沒有漏掉的清單 | 手動：閱卷者讀 diff 與 grep |
| TC-080 | va09 | 功能 | 三條新路由 | 檢查路由表 | 每條 methods 恰為 `("GET","HEAD")` | 自動 |
| TC-081 | vb08；不做：新 job 種類 | 不在範圍 | 資料庫與 job 種類清單 | 開三條新路由前後比對（比照 `test_ro12_nothing_else_is_written`） | 沒有新增 job 種類，除既有讀檔 job 外沒有寫入任何資料 | 自動 |
| TC-082 | 範圍：不得改；不做：abf_station、25 MB 上限 | 不在範圍 | `git diff v3...HEAD` | 檢查 `jobs.py`、`actions/__init__.py`、`abf_station/*` | 三者差異為空；`RUN_FILE_MAX_BYTES = 26214400` 與 `readfile.py:MAX_BYTES` 未變；沒有串流或分段讀取 | 手動：閱卷者讀 diff |
| TC-083 | 不做：全部下載／交付包 zip、交付包其他列 | 不在範圍 | 完成頁 | 檢查頁面 | 沒有「全部下載」或 zip 連結；交付包其他列（報告、圖、方法段落）仍是「之後開放」 | 自動 |
| TC-084 | 完成標準 3（risk L 爆炸半徑證明） | 功能 | `specs/web-result-viewer/ledger.md` | 讀 ledger | 有 (a) web.py 差異證明、(b) 所有既有頁加三條新路由的實際回應標頭表，且只有新路由與 HTML 預覽頁的標頭與 v3 不同、(c) 一段說明為何 sandbox 擋得住 cookie／API／表單 | 手動：閱卷者讀 ledger 並自行重跑標頭比對 |
| TC-085 | 完成標準 5；原話：圖片先做、iframe 後做 | 功能 | git 提交歷史 | 讀兩個提交 | 步驟 A、B 為兩個提交且 A 在前；A 提交時 `/run/report` 路由與任何 `<iframe` 都不存在；A 提交時全部步驟 A 測試為綠 | 手動：閱卷者用 `git show` 檢查 |
| TC-086 | va10；DESIGN.md「用字」 | 功能 | `web_preview` 的中文字串與兩個新頁 | 在本測試檔內呼叫 `banned_in` | 不含禁用詞表（這個、這份、一下…）；中文頁沒有獨立的拉丁字 `run`；不改 `test_web_wording_sweep.py` | 自動 |
| TC-087 | 專長守則：狀態不只靠顏色 | 功能 | 預覽頁的 不提供預覽、等待、too_large、錯誤、站台連不上 各狀態 | 檢查每個狀態的 HTML | 每個狀態同時有符號（如 ◌、✕）與文字，不只靠 class 顏色；文字是使用者看得懂的白話，不露出錯誤代碼 | 自動 |
| TC-088 | 範圍：docs/PLATFORM.md | 功能 | `docs/PLATFORM.md` 第 805 行附近 | 讀該段 | 「下載一律 attachment」旁補明：預覽是另外三條路由，下載路由不變 | 手動：閱卷者讀文件 |
| TC-089 | 範圍：docs/TESTING.md | 功能 | `docs/TESTING.md` | 讀新增的手動一節 | 有真 MultiQC／summary_report 預覽與截圖的具體步驟，且包含 TC-039、TC-069、TC-082、TC-085 所需的檢查說明，照做得出結果 | 手動：閱卷者讀文件 |
| TC-090 | 範圍：DESIGN.md | 功能 | `DESIGN.md` 畫面 8 的「Reports (MultiQC embedded, JS)」 | 讀該句 | 已改成與本實作一致（沙盒 iframe 預覽，頁面本身無 JS），沒有與實作矛盾的敘述 | 手動：閱卷者讀文件 |
| TC-091 | 完成標準 4；原話：UI 附 1440／390 × zh／en 截圖 | 功能 | 完成頁含「預覽」連結的清單 | 1440 與 390 寬、中文與英文各截一張 | 共 4 張，檔名貼在 ledger；連結可見、不被截斷 | 手動：`docs/TESTING.md` 新增手動一節 |
| TC-092 | 同上 | 功能 | PNG 預覽頁 | 四種組合各截一張 | 共 4 張；圖顯示、下載與返回連結可見 | 手動 |
| TC-093 | 同上 | 功能 | too_large 預覽頁 | 四種組合各截一張 | 共 4 張；顯示 too_large 句與符號，沒有圖 | 手動 |
| TC-094 | 同上（步驟 B） | 功能 | MultiQC 報告預覽頁 | 四種組合各截一張 | 共 4 張；報告在隔離框內顯示；加前三類共 16 張，步驟 A 先交 12 張 | 手動 |
| TC-095 | 完成標準 4；裁決 2 | 功能 | 真 MultiQC 報告 `multiqc_report.html`（約 2.5–4 MB） | 在瀏覽器開預覽頁 | 圖表能顯示（若因 CSP 載不出，依 TC-069 處理） | 手動 |
| TC-096 | 完成標準 4 | 功能 | 一份真的 ampliseq `summary_report.html` | 在瀏覽器開預覽頁 | 報告內容與圖表能顯示 | 手動 |
| TC-097 | 完成標準 4；步驟 B-4 | 功能 | 真報告內有外部連結 | 在預覽頁點報告內的連結 | 點了沒有作用，無法離開預覽頁，頁面沒被導走 | 手動 |
| TC-098 | 專長守則：手機可用、焦點可見 | 功能 | 390 寬的預覽頁與清單頁 | 檢視並以鍵盤 Tab 操作 | 不橫向捲動；「預覽」「下載」「返回」點擊目標夠大；鍵盤焦點外框可見 | 手動 |
| TC-099 | 專長守則：axe 無障礙掃描 | 功能 | 預覽頁各狀態與兩個清單頁 | 跑 `scripts/ui_check.py`（axe-core） | 沒有 serious 或 critical 項；跑不起來標 UNVERIFIED 並寫明缺什麼 | 手動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-100 | 安全網：憑證與個人資料不被印出、不外洩 | 功能 | 登入狀態，報告內含試圖讀取 cookie 的程式（真瀏覽器見 TC-053） | 檢查預覽頁與三條新路由的回應 | 回應本文與標頭都不含登入 cookie 值或 CSRF 令牌；與 TC-053 一起證明報告內的程式拿不到登入憑證 | 自動 |
| TC-101 | 安全網：寫入類工具須先經人確認；新路由不得成為寫入入口 | 例外 | 三條新路由 | 以 POST 呼叫 | 被拒絕（方法不被允許），不改變任何資料、不排 job；三條路由只讀檔（見 TC-080、TC-081） | 自動 |
