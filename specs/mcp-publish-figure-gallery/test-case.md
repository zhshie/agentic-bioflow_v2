# 測試案例：publish_figure 第 2 片（完成頁私有圖庫：預覽、勾選打包、刪除）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
來源只有 `specs/mcp-publish-figure-gallery/plan.md`（本案沒有獨立 spec.md；計畫的「目標、作法、失敗先行測試、完成標準、不做」即規格）。
未決問題 P1 至 P9 見 test-case-overview.md；本檔按其「建議答案」出題，標 (P#) 者答案不同時須重開。
-->

**規格**：`specs/mcp-publish-figure-gallery/plan.md`　**總覽**：`test-case-overview.md`
**前一片**：`specs/mcp-publish-figure/`（TC-001 至 TC-098）。第 1 片的行為（確認通道、檔名與內容驗證、`index.json` 格式、上限）本片不重測，只驗本片不破壞它們。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者（或 AI、他人）做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

編號格內的標記表示誰能判定：【機器可驗】＝在本機或 CI 用指令、測試或讀 diff 即可判定；【實機驗】＝要維護者親自看或親手操作。

維護者原話編號沿用計畫「維護者原話」七條（原話 1 至 7）：

1. 「改成根據pipline的內容，透過使用者自己串接的LLM討論生成圖片或統計分析，直到使用者點選打包之後才往最後一關走」
2. 「具體打包什麼都是使用者跟LLM討論」
3. 「目前我到底能不能夠用MCP請lab-agent跑完分析並顯示在網頁上? 這是我最基本的要求」
4. DESIGN.md 第 9 畫面：「只要讓使用者能操作裡面的R，或是透過AI agent及時修蓋程式碼，然後能看得到圖片產生，最後要能夠打包圖片往下一步」；設計原文 “each with an ‘Include in package’ checkbox … the script goes into the package too”
5. 「Studio 跑在使用者自己的電腦、平台看不到圖」（圖只來自使用者端 LLM 經第 1 片送入的內容）
6. 「一樣要注意中文的顯示不能口語」
7. 維護者回「好」＝選 B（圖庫只含經確認通道寫入者；打包與刪除不產生任何 MCP 寫入工具，也不繞過人）

測試檔：除標明者外，「自動」指新測試檔 `platform/tests/test_web_figures.py`（函式名由執行者命名，須在註解標出 TC 編號）。

## User Story 1 — 在完成頁看到自己的圖庫（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 【機器可驗】 | 原話 3；作法 1 | 功能 | 使用者有一個已成功（succeeded）的分析；圖庫為空 | 1. LLM 呼叫 `publish_figure`，回待確認申請。2. 在本人確認頁（`/c/<rid>`）按「送出」之前，開該分析的完成頁。3. 按「送出」後再開完成頁 | 第 2 步完成頁沒有任何 `<img>`；第 3 步完成頁有一個 `<img>`，`src` 指向 `/run/figure?run=…&name=…`，且該網址能取得那張圖 | 自動：`test_end_to_end_publish_confirm_preview` |
| TC-002 【機器可驗】 | 作法 1；原話 4 | 功能 | 圖庫已有 3 張圖（PNG、SVG、JPG 各一，說明各不同）；語言為中文 | 開完成頁 | 每張圖一個 `<figure>`：`<img>` 的 `src` 指向 `/run/figure`、`alt` 為說明（無說明時為檔名）、`width="240"`、`loading="lazy"`；顯示檔名、說明、大小；每張都有標籤「使用者與 LLM 產生」（3 張共 3 個）；有「下載」連結，網址含 `download=1` | 自動：`test_finished_page_gallery_has_img_label_checkbox_delete`（中文） |
| TC-003 【機器可驗】 | 作法 1；原話 6 | 功能 | 同 TC-002；語言為英文，說明與檔名皆為 ASCII | 開完成頁 | 與 TC-002 同結構；所有介面文字為英文；整頁不含任何中日韓字元 | 自動：同上（英文） |
| TC-004 【機器可驗】 | 原話 4；作法 1 | 功能 | 一張圖附程式碼（多行）與參數 | 開完成頁，看「檢視程式碼與參數」 | 有 `<details>`，內有 `<pre>`，裡面是送入時的程式碼與參數原文（完整，不截斷、不改寫），以純文字呈現；沒有任何腳本執行程式碼 | 自動：同上 |
| TC-005 【機器可驗】 | 作法 1；風險備註（純文字逸出） | 例外 | 一張圖的說明、程式碼、參數、檔名（檔名限制字元內可含的部分）各含 `<script>alert(1)</script>` 與 `"><img src=x onerror=alert(1)>` | 開完成頁（中、英） | 這些內容以 `&lt;script&gt;` 之類逸出形式顯示；頁面中除平台自己放的標籤外，不出現使用者提供的 `<script`、`onerror=` 活的標記；逐欄各測一次 | 自動：同上（逸出案例） |
| TC-006 【機器可驗】 | 作法 1；空狀態 (P3) | 功能 | 成功的分析；圖庫為空（尚未存入任何圖） | 開完成頁（中、英） | 圖庫區塊顯示一行提示：圖庫為空，可請自己的 LLM 以 MCP 工具 `publish_figure` 提出，經本人在確認頁按「送出」後存入；沒有勾選框、沒有「打包所選的圖」按鈕、沒有 `<img>`；英文版有對應一句且無中日韓字元 | 自動：`test_finished_gallery_empty_line` |
| TC-007 【機器可驗】 | 作法 1 | 功能 | 本分析有一筆待確認的 `publish_figure` 申請（本人尚未按送出） | 開完成頁 | 圖庫區塊上方有一行提示並連到 `/c/<rid>`；申請內的圖不在頁面上（沒有它們的 `<img>`、檔名可不列） | 自動：新增測試 |
| TC-008 【機器可驗】 | 範圍：一個沒有圖的 run；空狀態 | 例外 | 成功的分析，圖庫資料夾與 `index.json` 都不存在（從沒存過圖） | 開完成頁 | 回 200，顯示與 TC-006 相同的空圖庫提示；頁面其餘部分（交付包、其他列）與無圖庫功能時相同；沒有錯誤訊息、沒有堆疊 | 自動：新增測試 |
| TC-009 【機器可驗】 | 空狀態；第 1 片 TC-021 | 例外 | `index.json` 內容損毀 | 開完成頁 | 當作空圖庫（同 TC-006 的提示），回 200；不露出堆疊、內部路徑 | 自動：新增測試 |
| TC-010 【機器可驗】 | 作法 1 (P6) | 例外 | 分析處於執行中或失敗，且圖庫有圖（第 1 片允許任何狀態提出圖） | 開該分析的完成階段頁與其他階段頁 | 圖庫區塊只出現在「succeeded 的分析的完成階段」；其他狀態與其他階段頁都沒有圖庫區塊；圖檔仍在磁碟上不被刪除；擁有者仍可直接以 `/run/figure` 取自己這個 run 的圖 | 自動：新增測試 |
| TC-011 【機器可驗】 | 作法 1；不做：即時清單（JS） | 功能 | 完成頁有圖庫 | 檢查 HTML | 沒有 `<meta http-equiv="refresh">`、沒有輪詢、沒有任何 `<script>` 或 JS 事件屬性；頁面不自動重整 | 自動：`test_no_refresh_and_no_poll_on_finished` |
| TC-012 【機器可驗】 | 作法 1 (P7) | 功能 | 圖庫 3 張，`created` 時間不同 | 開完成頁 | 依 `created` 由新到舊排列；沒有為「最新」另加醒目樣式（沒有新增 CSS class） | 自動：新增測試 |
| TC-013 【機器可驗】 | 原話 5；範圍：不去站台找 | 功能 | 分析的站台結果資料夾（或測試用的假結果目錄）內有 PNG，但使用者從未經 `publish_figure` 存入 | 開完成頁 | 圖庫為空（TC-006 的提示）；站台結果的 PNG 沒有出現在圖庫；平台沒有為此呼叫任何站台、agent 或 ssh | 自動：新增測試 |
| TC-014 【機器可驗】 | 作法 1 (P5) | 例外 | 一張圖沒附程式碼、沒附參數；另一張只附其中之一 | 開完成頁 | 兩者皆沒有者不顯示「檢視程式碼與參數」；只有其一者只顯示有的那一項；沒有空的 `<pre>`、沒有「None／null」字樣 | 自動：新增測試 |

## User Story 2 — 勾選與打包：使用者按下「打包」之前，交付包不含任何圖（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 【機器可驗】 | 原話 2、4；作法 1 | 功能 | 圖庫 3 張圖，包括曾經打包過的 | 開完成頁，看勾選框與按鈕 | 每張圖一個勾選框：`name="fig"`、`value` 為檔名、**沒有 `checked`**（包括先前已打包的圖，P1）；勾選框在一個 `method="post"`、`action="/run/figures/pack"` 的表單內，帶 CSRF 欄位；區塊最下方有一個「打包所選的圖」按鈕（英文有對應按鈕） | 自動：`test_finished_page_gallery_has_img_label_checkbox_delete` |
| TC-016 【機器可驗】 | 作法 4；原話 2 (P1) | 功能 | 圖庫 3 張，其中 1 張已打包 | 開完成頁（中、英） | 每張圖都標出目前狀態，已打包者與未打包者的標示不同，且同時有符號與文字；「打包所選的圖」鈕旁有一句說明：交付包將以本次勾選的圖為準，未勾選者會移出交付包（英文有對應句、無中日韓字元） | 自動：新增測試 |
| TC-017 【機器可驗】 | 原話 1；作法 4 | 功能 | 本人確認存入 3 張圖，之後什麼都沒按 | 看交付包「圖」列，並呼叫 `list_figures(run, packed_only=True)` | 「圖」列為「3 張在圖庫，尚未打包」；`packed_only` 結果為空；`index.json` 中 3 張 `packed` 皆為 false。平台沒有預先替使用者勾選或挑選任何圖 | 自動：`test_nothing_in_package_until_pack_pressed` |
| TC-018 【機器可驗】 | 原話 1、2；作法 4 | 功能 | 圖庫 3 張圖（a、b、c） | 勾 a、b，按「打包所選的圖」 | `a`、`b` 的 `packed` 為 true、`packed_at` 有值；`c` 為 false；`packed_only` 恰為 a、b；交付包「圖」列為「已打包 2 張」並列出 a、b 的檔名 | 自動：同上 |
| TC-019 【機器可驗】 | 原話 2；作法 4 (P3) | 功能 | TC-018 之後 | 一張都不勾，按「打包所選的圖」 | 合法、不報錯；3 張 `packed` 全為 false；`packed_only` 為空；交付包「圖」列回到「3 張在圖庫，尚未打包」 | 自動：同上 |
| TC-020 【機器可驗】 | 原話 2；作法 4 | 功能 | 圖庫 3 張 | 全勾，按「打包所選的圖」 | 3 張全為 packed；「圖」列為「已打包 3 張」並列出 3 個檔名；三態（0 張、部分、全部）都已被 TC-017 至 TC-020 驗過 | 自動：同上 |
| TC-021 【機器可驗】 | 作法 4；既有測試同步修改 | 功能 | 渲染三種完成頁：無圖庫；有圖未打包；已打包（中文） | 讀交付包列 | 「圖」列分別為「無」「n 張在圖庫，尚未打包」「已打包 m 張」；其他列（報告、結果表格、MultiQC 報告、方法段落、樣本表）與「下載交付包 之後開放」「Coming later」的文字與先前逐字相同；`test_web_finished.py` 的 `pack_rows` 三處預期只增不減 | 自動：`platform/tests/test_web_finished.py`（91、173、250 行一帶）、`test_package_row_three_states` |
| TC-022 【機器可驗】 | 原話 4；作法 4 | 功能 | 圖 a 附程式碼與參數並已打包；圖 b 附程式碼但未打包 | 讀「交付包中的圖」（`list_figures(run, packed_only=True)` 與其指向的檔案） | 結果含 a、以及 a 的程式碼與參數文字（與送入時逐字相同）；不含 b 與 b 的程式碼；「程式碼隨圖進包」成立 | 自動：新增測試 |
| TC-023 【機器可驗】 | 作法 4 | 功能 | 動作層直接呼叫：`pack_figures(run, ["a"])`，再 `pack_figures(run, ["b"])` | 讀 `index.json` | 第二次後只有 b 為 packed；a 回到 false（打包結果＝最近一次的勾選集合）；`packed_at` 只在被選者上有值 | 自動：`test_publish_figure.py::test_pack_figures_whitelist_and_set_semantics` |
| TC-024 【機器可驗】 | 作法 3(d)、4 (P4) | 例外 | 圖庫有 a、b；送出的名單為 [a, 不存在的 z] | 動作層與網頁 POST 各一次 | 整個請求拒絕，說明哪個名稱不在圖庫；`index.json` 與所有檔案一個位元組都不變（a 也沒有被打包）；不做部分成功 | 自動：同上、`test_pack_and_delete_post_scope` |
| TC-025 【機器可驗】 | 作法 4 (P4) | 例外 | 同一請求中 `fig` 出現同一名稱兩次 | POST 打包 | 視為一張；交付包「圖」列為「已打包 1 張」（不是 2 張）；不報錯 | 自動：新增測試 |
| TC-026 【機器可驗】 | 作法 4 (P3) | 例外 | 圖庫為空，直接 POST `/run/figures/pack`（不帶任何 `fig`） | POST | 不改任何檔、不拋例外；回應為導回完成頁或明確的無變更提示，不是 500 | 自動：新增測試 |
| TC-027 【機器可驗】 | 作法 3 (P2) | 功能 | 本人按下「打包所選的圖」成功 | 看回應，再重新整理瀏覽器 | 回應為 303 導回同一個分析的完成頁（交付包「圖」列已更新）；重新整理不會再送出一次打包 | 自動：新增測試 |
| TC-028 【機器可驗】 | 作法 4；第 1 片 TC-014 | 功能 | 圖 `a.png` 已打包；LLM 再提出同名 `a.png`，本人按送出 | 看交付包「圖」列 | `a.png` 的 `packed` 回到 false；「圖」列由「已打包 1 張」變為「1 張在圖庫，尚未打包」；圖庫張數不增加 | 自動：`test_publish_figure.py::test_pack_resets_on_same_name_overwrite` |
| TC-029 【機器可驗】 | 作法 4：finish 只收 packed | 功能 | 讀 diff 與 `docs/PLATFORM.md` | 找所有讀取「交付包中的圖」的程式碼與文件 | 一律走 `list_figures(run, packed_only=True)`；PLATFORM.md 寫明 finish 介面（以 `packed` 旗標為準）；`finish` 的 MCP prompt 與腳本沒有被改 | 自動：讀 diff 與 grep |
| TC-030 【機器可驗】 | 作法 4 | 功能 | 圖庫 3 張，記下每個檔案的位元組與權限 | 打包 2 張，再打包 0 張 | 圖檔、`.code.txt`、`.params.txt` 的位元組與（POSIX 上）權限 0600／資料夾 0700 不變；只有 `index.json` 的旗標變動 | 自動：新增測試 |
| TC-031 【機器可驗】 | 作法 3；專長守則 backend：錯誤訊息 | 例外 | 寫入 `index.json` 時失敗（如唯讀資料夾） | POST 打包 | 回應說明未能打包與下一步（請稍後重試或回報）；`index.json` 保持舊內容；不洩漏內部路徑、堆疊 | 自動：新增測試 |

## User Story 3 — 刪除圖庫中的圖（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 【機器可驗】 | 作法 3 | 功能 | 圖庫 a、b，各有 `.code.txt` 與 `.params.txt` | 刪除 a | a 的圖檔、a 的 `.code.txt`、`.params.txt` 都已消失；`index.json` 不再有 a；b 的所有檔與記錄一個位元組都不變 | 自動：`test_publish_figure.py::test_delete_figure_removes_files_and_pack_state` |
| TC-033 【機器可驗】 | 作法 3、4 | 功能 | a 已打包 | 刪除 a | `packed_only` 不再含 a；交付包「圖」列隨之更新（已打包張數減少） | 自動：同上 |
| TC-034 【機器可驗】 | 作法 3(e) | 功能 | 圖庫有圖；語言中、英各一次 | 看每張圖的刪除表單 | 刪除鈕為 POST `/run/figure/delete`，帶 CSRF 欄位；鈕前有一句說明（中文含「會一併移出交付包」，英文有對應句）；沒有 JavaScript 對話框；刪除鈕所在的表單不在打包表單之內 | 自動：`test_finished_page_gallery_has_img_label_checkbox_delete` |
| TC-035 【機器可驗】 | 作法 3(c)(d) | 例外 | 刪除的名稱：不在 `index.json` 的、`../x.png`、`index.json`、`a.code.txt`、他人 run 的圖 | 逐一 POST 刪除 | 全部拒絕；不刪任何檔（`index.json`、`platform.db` 都在）；他人的與不存在的同一種拒絕回應 | 自動：`test_pack_and_delete_post_scope` |
| TC-036 【機器可驗】 | 作法 3、1 | 功能 | 圖庫只剩一張，已打包 | 刪除它 | 完成頁顯示空圖庫提示（TC-006）；交付包「圖」列為「無」 | 自動：新增測試 |
| TC-037 【機器可驗】 | 作法 3；第 1 片 TC-029 | 功能 | 圖庫已滿 30 張 | 刪除 1 張後再提出一張新檔名並確認 | 刪除後第 30 張的名額釋出，新圖可存入；刪除前同樣的請求被拒（圖庫已滿） | 自動：新增測試 |
| TC-038 【機器可驗】 | 作法 3 | 例外 | `index.json` 有 a，但磁碟上 a 的圖檔已不存在 | 刪除 a | 不拋例外；`index.json` 移除 a；回應不是 500、不露出路徑 | 自動：新增測試 |

## User Story 4 — 圖片路由：誰能看、送出什麼內容、帶什麼標頭（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 【機器可驗】 | 作法 2；原話：圖庫私有 | 例外 | 圖庫有圖；請求不帶登入 cookie | GET `/run/figure?run=…&name=…` | 不回圖的位元組（導向登入或拒絕，與其他需登入路由一致）；沒有分享用的公開網址 | 自動：`test_figure_route_needs_login` |
| TC-040 【機器可驗】 | 作法 2；專長守則 backend：跨使用者（讀） | 例外 | 使用者甲的 run 有圖 a；乙已登入 | 乙請求甲的 run 的 a；乙再請求自己 run 裡不存在的圖 | 兩個回應是同一個 404、純文字一行（狀態、本文、標頭都相同）；不重複請求中的 run 或檔名，不洩漏哪個存在 | 自動：同上 |
| TC-041 【機器可驗】 | 作法 2；範圍：標頭自建 | 功能 | 擁有者，圖庫有 `a.png`、`b.svg`、`c.jpg`、`d.jpeg` | 各 GET 一次 | 回應位元組與存入時逐位元相同；`Content-Type` 由伺服器依副檔名決定：png→`image/png`、svg→`image/svg+xml`、jpg 與 jpeg→`image/jpeg`；jpg 不得被標成 `image/svg+xml`（不可原樣沿用只分 png／svg 兩種的既有輔助函式） | 自動：新增測試 |
| TC-042 【機器可驗】 | 作法 2；「不得讓上傳檔在頁面中執行程式」 | 功能 | 同 TC-041 | 看三種圖的回應標頭 | 含 `X-Content-Type-Options: nosniff`、`Cache-Control: private, no-store`；`Content-Security-Policy` 含 `sandbox` 與 `default-src 'none'`，**不含** `script-src`、`allow-scripts`；仍保留全站的 `X-Frame-Options: DENY`；沒有 `Content-Type: text/html` | 自動：`test_figure_route_headers` |
| TC-043 【機器可驗】 | 作法 2：縱深防禦 | 例外 | 測試中直接把磁碟上一個圖檔改成內含 HTML 與 `<script>`（模擬被竄改，第 1 片本不會收） | GET 該圖 | 仍以依副檔名決定的圖片 `Content-Type` 回應，並帶 TC-042 的全部標頭；回應不是 `text/html`，瀏覽器不會把它當頁面執行 | 自動：新增測試 |
| TC-044 【機器可驗】 | 作法 2 | 功能 | 圖庫有 `a.png` | GET `…&download=1`；再 GET 不帶 `download` | 帶 `download=1` 時有 `Content-Disposition: attachment`（檔名為該圖名）；不帶時沒有 attachment；兩者都帶 TC-042 的標頭 | 自動：`test_download_flag_sends_attachment` |
| TC-045 【機器可驗】 | 作法 2：名稱白名單 | 例外 | 擁有者，圖庫有 a | `name` 分別為 `../../platform.db`、`index.json`、`a.code.txt`、`a.params.txt`、`%2e%2e%2f%2e%2e%2fplatform.db`、`..\..\x`、絕對路徑、含 NUL、空字串、整個缺少 `name`；`run` 為 `../` 或缺少 | GET | 每一種都是同一個 404 純文字一行；`platform.db`、`index.json`、程式碼檔與參數檔的內容都沒有被回傳 | 自動：`test_route_cannot_reach_other_files` |
| TC-046 【機器可驗】 | 作法 2 | 例外 | `index.json` 列有 a，磁碟上檔案不存在 | GET a | 404 純文字一行，不是 500，不露出路徑 | 自動：新增測試 |
| TC-047 【機器可驗】 | 作法 3(a) | 例外 | 帶有效 Bearer／MCP token、不帶登入 cookie | GET `/run/figure` | 拒絕；不回圖 | 自動：`test_pack_and_delete_post_scope`（含 GET 案例）或新增 |
| TC-048 【機器可驗】 | 作法 2 | 例外 | 登入的擁有者 | 對 `/run/figure` 送 POST、PUT、DELETE | 回 405（或同類的方法不允許），圖庫不變 | 自動：新增測試 |
| TC-049 【機器可驗】 | 作法 2；範圍：`test_tc049_other_pages_are_as_before` | 功能 | 各頁的回應標頭 | 比對 `/`、`/settings`、`/usage`、`/c/<rid>`、`/launch`、非完成階段的分析頁、完成階段的分析頁 | 只有「完成階段」的分析頁與 `/run/figure` 的 CSP 含 `img-src 'self'`；完成階段頁的 CSP 與既有全站 CSP 相比只多這一項（保留 `form-action 'self'`；沒有 `script-src`、沒有 `data:`／`https:` 的 `img-src`）；其他頁的 CSP 逐字等於 `base_csp()`；`web._HEADERS["Content-Security-Policy"]` 與 `LAUNCH_HEADERS` 的字串原樣 | 自動：`test_finished_csp_gets_img_src_but_other_pages_do_not`；既有 `test_web_guided_launch_2d.py:685-707`、`:670-671`、`:951`、`test_web_guided_launch_2.py:590`、`test_web_guided_launch_preview.py:361`、`test_settings_pick_installed.py:688`、`test_web_resume_edit.py:543` 不改且綠 |

## User Story 5 — 打包與刪除只能由本人在網頁上按，AI 與他人到不了（優先度 P1）

此範圍依計畫「作法 3」與維護者裁決 3：以「登入 cookie、CSRF、同源、人按按鈕」為確認，不建立 `confirmations` 列、不開 MCP 工具（P9，請維護者留一句話）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 【機器可驗】 | 作法 3(b) | 例外 | 擁有者已登入，圖庫有圖 | POST `/run/figures/pack` 與 `/run/figure/delete`，不帶 CSRF | 兩者皆拒；`index.json` 與所有檔案位元組不變 | 自動：`test_pack_and_delete_post_scope` |
| TC-051 【機器可驗】 | 作法 3(b) | 例外 | 同上 | 帶錯的 CSRF：他人工作階段的、別的 run 的、別的用途的（例如拿 logout 的 token） | 全部拒；不改檔 | 自動：同上 |
| TC-052 【機器可驗】 | 作法 3(c)；專長守則 backend：跨使用者（寫） | 例外 | 甲的 run 有圖；乙已登入且 CSRF 有效（乙自己的） | 乙對甲的 run 與圖 POST 打包與刪除；再對不存在的 run POST | 乙對甲的與對不存在的得到同一個拒絕（404）；甲的圖與 `index.json` 一個位元組都不變 | 自動：同上 |
| TC-053 【機器可驗】 | 作法 3(c)；專長守則 backend：跨使用者（寫） | 例外 | 動作層直接呼叫 | 以乙的身分呼叫 `pack_figures`、`delete_figure`，對象是甲的 run | 被拒絕（與不存在同一種答覆）；不改任何檔 | 自動：`test_publish_figure.py`（動作層案例） |
| TC-054 【機器可驗】 | 作法 3(a)；原話 7 | 例外 | 使用者的 Bearer／MCP token，不帶登入 cookie | POST 打包與刪除 | 兩者都拒絕；不改檔 | 自動：同 TC-050 |
| TC-055 【機器可驗】 | 作法 3(b)：同源檢查 | 例外 | 登入的擁有者、有效 CSRF | POST 時 `Origin` 為不同源 | 拒；不改檔；（對照：同源且 CSRF 有效時成功，做法與 `POST /c/{rid}` 一致） | 自動：同上 |
| TC-056 【機器可驗】 | 作法 3 | 例外 | 登入的擁有者 | 對 `/run/figures/pack` 與 `/run/figure/delete` 送 GET | 405；不改任何東西（狀態只能由 POST 改變） | 自動：新增測試 |
| TC-057 【機器可驗】 | 原話 7；作法 3(a)；不新增 MCP 工具 | 功能 | MCP 伺服器啟動；瀏覽器聊天工具集 | 列舉 MCP 工具與聊天工具 | 沒有名為打包、刪除、`pack_figures`、`delete_figure`、`read_figure` 的工具；工具數仍為 23；`tools.json` 快照不變；AI 沒有任何工具能到達這兩條 POST | 自動：`platform/tests/mcp/test_mcp_contract_tools.py`、`test_chat_tools.py`、`test_pack_and_delete_post_scope` |
| TC-058 【機器可驗】 | 作法 3 | 功能 | 記下 `confirmations` 與 `jobs` 的列數 | 成功執行一次打包與一次刪除 | 兩個表的列數前後不變；沒有 job 被排入 | 自動：同上 |
| TC-059 【機器可驗】 | 專長守則 backend：對等性；憲法 | 功能 | 測試同時列舉兩邊 | 列出完成頁可見的寫入動作（打包、刪除）與動作層函式（`pack_figures`、`delete_figure`），並讀路由處理函式 | 兩邊一一對應，缺一邊就失敗；路由處理函式只呼叫動作層，沒有第二份邏輯；`test_actions_layer.py` 的只從網頁寫入清單（`PAGE_WRITE_NAMES`）加入 `delete_figure`、`pack_figures`，且它們不在 MCP 工具名單中 | 自動：`platform/tests/test_actions_layer.py`（約 713 至 742 行）、`test_web_parity.py` |
| TC-060 【機器可驗】 | 專長守則 backend：錯誤訊息與日誌 | 例外 | 觸發 TC-050 至 TC-052、TC-055 的拒絕各一次，並抓日誌 | 檢查回應與日誌 | 拒絕訊息說明發生什麼事與下一步；不含堆疊、內部檔案路徑、SQL；回應與日誌不含 cookie、token、CSRF 值 | 自動：新增測試 |

## User Story 6 — 限制與邊界（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-061 【機器可驗】 | 作法 1；第 1 片上限 | 功能 | 圖庫已滿 30 張（含 PNG、SVG、JPG；其中數張程式碼接近 100 KB、檔名 80 字元） | 開完成頁，全勾打包，再開完成頁 | 頁面回 200，30 個 `<figure>` 都在；打包 30 張成功；「圖」列為「已打包 30 張」並列出；中途沒有逾時或 500 | 自動：新增測試 |
| TC-062 【機器可驗】 | 作法 3(d) | 例外 | 打包請求帶超過 30 個名稱、或單一名稱超過 80 字元、或含控制字元 | POST 打包 | 拒絕；不改檔；說明原因 | 自動：`test_pack_and_delete_post_scope` |
| TC-063 【機器可驗】 | 第 1 片上限不退步 | 功能 | 第 1 片的上限測試 | 跑第 1 片的 `test_publish_figure.py`、`test_publish_figure_confirm.py` | 單次 10 張、每個 run 30 張、整批 5 MiB、說明 200 字、程式碼 100 KB、參數 10 KB 的測試仍綠且未被改動 | 自動：上列兩檔 |

## User Story 7 — 畫面、狀態、無障礙、字串（優先度 P1）

專長守則（ui）：DESIGN.md 沒有為「完成頁私有圖庫」另畫線稿；第 9 畫面原稿被維護者 11-07 裁決以本案取代。所以沒有可比對的核可草稿，TC-075 由維護者看實跑截圖拍板。圖庫的狀態：空、有圖未打包、已打包、有待確認申請、打包或刪除被拒、寫入失敗；沒有「載入中」畫面（頁面不輪詢，圖片 `loading="lazy"` 屬瀏覽器行為）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-064 【機器可驗】 | 專長守則 ui：前端限制 | 功能 | 渲染完成頁（空、有圖、已打包；中、英） | 掃描 HTML | 沒有 inline `style` 屬性或標籤；沒有 `<script>`；沒有 `http(s)://` 外部資源；圖寬只用 `<img width>` 屬性 | 自動：`test_no_inline_style_or_script_in_gallery` |
| TC-065 【機器可驗】 | 範圍：不改 CSS | 功能 | 實作完成 | 比對 `STYLE` 與 `CSS_SHA256` | 雜湊仍為 `719ce2ab…`；`web_board.py` 的 `STYLE` 沒有改；`test_results_files.py:698`、`test_web_guided_launch_preview.py:414` 不改且綠；圖庫只用既有 class | 自動：`test_style_untouched` |
| TC-066 【機器可驗】 | 原話 6；作法 6 | 功能 | 新增字串 | 跑用字檢查 | `STRINGS` 中 zh、en 同鍵；中文為正式書面語，不含禁用口語字；英文版不含中日韓字元；既有字句逐字不變；`test_web_wording_sweep.py`、`test_web_board.py::test_tcl42_string_table`、`test_tcl44_no_external_url_script_or_style_attribute`、`test_fs12_web_board_touches_are_minimal`、`test_web_parity.py` 綠 | 自動：`test_strings_table_parity_and_wording` 與上列既有測試 |
| TC-067 【機器可驗】 | 專長守則 ui：狀態表達 | 功能 | 渲染各狀態：圖已打包與未打包的標示、交付包「圖」列三態、待確認提示、空圖庫提示、被拒與寫入失敗頁 | 檢查 HTML | 每個狀態同時含符號與文字，不得只靠 class 顏色 | 自動：新增測試 |
| TC-068 【機器可驗】 | 專長守則 ui：無障礙 | 功能 | 圖庫有說明與無說明的圖 | 檢查每個 `<img>` | 都有非空 `alt`（說明或檔名，已逸出） | 自動：新增測試 |
| TC-069 【機器可驗】 | 專長守則 ui：無障礙 | 功能 | 圖庫有 3 張 | 檢查每個勾選框 | 每個勾選框有關聯的 `<label>`，文字含該圖檔名；可用鍵盤勾選 | 自動：新增測試 |
| TC-070 【機器可驗】 | 專長守則 ui：無障礙 | 功能 | 圖庫有 3 張 | 檢查每個刪除鈕 | 每個刪除鈕的可讀名稱包含該圖檔名（不是 3 個都只叫「刪除」） | 自動：新增測試 |
| TC-071 【機器可驗】 | 作法 1、3 | 功能 | 完成頁有圖庫 | 解析 HTML | 沒有巢狀 `<form>`；刪除表單在打包表單之外（或以 `form=` 屬性關聯）；「檢視程式碼與參數」是 `<details>` 且含 `<summary>`，可用鍵盤開合 | 自動：新增測試 |
| TC-072 【機器可驗】 | 專長守則 ui：實際跑起來看；無障礙檢查 | 功能 | 以 `with_server.py` 起真實平台 | 完成頁 1440 與 390 寬 × 中、英共 4 張；另補「圖庫為空」「≥3 張（含一張 SVG）未打包」「已打包」各一；跑 axe | axe 無 serious 或 critical。`scripts/ui_check.py` 目前不存在：改用 Playwright 補拍；axe 沒跑成就標 UNVERIFIED 並寫明缺什麼；截圖存於 repo 之外或被忽略的資料夾，不存進 Drive 工作區 | 自動：閱卷時執行並記路徑與張數 |
| TC-073 【機器可驗】 | 專長守則 ui：手機寬度 | 功能 | 圖庫 3 張，其中一張檔名 80 字元、程式碼很長 | 390 寬開完成頁 | 沒有橫向捲動（頁面寬度不超過視窗）；按鈕與勾選框可點 | 自動：閱卷時以 Playwright 執行 |
| TC-074 【機器可驗】 | 專長守則 ui：文字檢查 | 功能 | 把有圖庫的完成頁（空、有圖、已打包；中、英）渲染成 HTML 檔 | 跑 `sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>` | 沒有未處理的違規；其他發現列入報告供人判斷 | 自動：閱卷時以偵測器執行 |
| TC-075 【實機驗】 | 專長守則 ui：與核可草稿比對；範本味 | 功能 | PR 附 TC-072 的截圖；沒有維護者核可的草稿 | 維護者看「圖庫為空」「有圖未打包」「已打包」的截圖與實際頁面 | 維護者回覆這幾個畫面是他要的、沒有範本味；無草稿可比對處標 UNVERIFIED，操作者記下他的原話 | 手動：`docs/TESTING.md`（維護者看截圖） |
| TC-076 【實機驗】 | 原話 2；原話 6；P1、P3 | 功能 | 同上 | 維護者讀頁面上的用字：圖庫為空提示、「打包所選的圖」、打包鈕旁「以本次勾選為準」那句、刪除前「會一併移出交付包」那句 | 維護者回覆用字正式、看得懂，且「勾選＝交付包內容、未勾的會移出」符合他的意思；操作者記下原話 | 手動：`docs/TESTING.md` |
| TC-077 【機器可驗】 | 專長守則 ui：每個畫面每個狀態 | 功能 | 列出本案的狀態：空圖庫、有圖未打包、已打包、有待確認申請提示、打包被拒、刪除被拒、寫入失敗 | 逐一渲染中、英 HTML | 每個狀態都做出來（沒有缺）；被拒與失敗頁說明發生什麼事與下一步，且含符號與文字；沒有「載入中」畫面是因頁面不輪詢 | 自動：新增測試，與 TC-067 共用渲染結果 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-078 【機器可驗】 | 不做：MCP 端刪圖或打包；不新增 MCP 工具 | 不在範圍 | 讀工具清單與 `tools.json` | 找 `read_figure`、`delete_figure`、`pack_figures` 或任何打包、刪除工具 | 都不存在；MCP 工具仍為 23 個（本片不新增）；打包與刪除只有網頁路由 | 自動：`test_mcp_contract_tools.py`；讀 diff |
| TC-079 【機器可驗】 | 不做：整包壓縮下載 | 不在範圍 | 完成頁 | 看交付包「下載」與路由表 | 「下載交付包」仍為「之後開放」（英文 "Coming later"）；沒有產生壓縮檔的路由或程式 | 自動：`test_web_finished.py`（該斷言不動）；讀 diff |
| TC-080 【機器可驗】 | 不做：不改 `finish` | 不在範圍 | 讀 diff | 找 `finish` 的 MCP prompt、技能與使用者端腳本的改動 | 沒有；只在 PLATFORM.md 寫明介面 | 自動：讀 diff |
| TC-081 【機器可驗】 | 不做：分享、跨 run 圖庫、重新排序、縮圖產生；確認頁圖像預覽 | 不在範圍 | 讀頁面與路由 | 找分享連結、跨 run 的圖庫頁、排序控制、縮圖檔；開 `/c/<rid>` 待確認頁 | 都不存在；縮圖只靠 `<img width>` 屬性；確認頁沒有 `<img>`、沒有 `data:` 圖像 | 自動：讀 diff；確認頁沿用第 1 片 TC-045 |
| TC-082 【機器可驗】 | 原話 1；不做：預先寫好腳本、推薦分析 | 不在範圍 | 完成頁、打包動作、文件字串 | 找平台自己產生的 R 或分析腳本、推薦分析的文字 | 沒有；平台只存使用者送入的程式碼，不預寫、不推薦 | 自動：讀 diff 與 grep |
| TC-083 【機器可驗】 | 不做：每位使用者總量上限、自動過期；裁決 3：forget 不連動刪圖庫 | 不在範圍 | 圖庫有圖；擁有者 `forget` 該分析 | `forget` 之後查圖庫資料夾 | 沒有新增的總量上限或過期機制；`forget` 不刪圖庫的任何檔案 | 自動：新增測試；讀 diff |
| TC-084 【機器可驗】 | 原話 5；作法 5：不經 jobs、agent、站台；不新增依賴 | 不在範圍 | 讀 diff 與依賴檔 | 找 jobs、agent、ssh、站台呼叫、新依賴 | 沒有；圖只來自使用者端 LLM 經第 1 片送入的內容；`figures.py` 的新函式只讀寫 `figures_root/<user>/<run_id>/` | 自動：讀 diff 與 grep |
| TC-085 【機器可驗】 | 不做：DESIGN.md 的即時清單（JS）；裁決：作廢 `studios-figures` 與本案矛盾處 | 不在範圍 | 讀 diff 與完成頁 | 找 `analysis/figures/` 的即時列出、勾選只存在查詢字串 `fig` 的作法 | 沒有；勾選以表單 POST 進動作層，沒有 JS、沒有輪詢，也不去站台結果資料夾列圖 | 自動：讀 diff；TC-011、TC-013 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-086 【機器可驗】 | 安全網（憲法 191-195 行）：寫入工具未經人確認一律拒絕；原話 7 | 例外 | 未經確認的 `publish_figure` 呼叫（任何形式） | 跑 `test_mcp_contract_writes.py`、`test_publish_figure_confirm.py` | 仍零副作用（沒有檔案、沒有 `index.json`、沒有 job）；打包、刪除不是工具，因而不構成未經確認的 MCP 寫入路徑；第 1 片的拒絕測試不變且綠 | 自動：`platform/tests/mcp/test_mcp_contract_writes.py`、`test_publish_figure_confirm.py` |
| TC-087 【機器可驗】 | 安全網（憲法 183 行）：不刪使用者原始資料 | 例外 | 在測試的假目錄放哨兵檔：`rawdata/x`、`results/x`、`analysis/x`、`platform.db`，另有與圖庫圖同名的檔 | 執行刪除（含 `../`、絕對路徑名稱的嘗試） | 所有哨兵檔位元組不變；刪除只動 `figures_root/<user>/<run_id>/` 內該圖的三個檔與 `index.json` 的一筆 | 自動：`test_pack_and_delete_post_scope`；`test_publish_figure.py::test_nothing_written_outside_figures_root` |
| TC-088 【機器可驗】 | 憲法 7.0.0 不編輯；原話 7 | 功能 | 實作完成後 | `git diff <base>...HEAD -- .specify/memory/constitution.md`；跑 `bash tests/constitution_6_test.sh` | diff 為空；測試綠 | 自動：`tests/constitution_6_test.sh`；讀 diff |
| TC-089 【機器可驗】 | 被釘住的既有測試；weakened tests | 功能 | 計畫「不得改動也不得放寬」所列測試與「必須同步改」所列測試 | 比對 diff | 不得改動者（`test_results_files.py:698`、`test_web_guided_launch_preview.py:414`、`test_web_guided_launch_2d.py:685-707`、`:670-671`、`:951`、`test_web_guided_launch_2.py:590`、`test_web_guided_launch_preview.py:361`、`test_settings_pick_installed.py:688`、`test_web_resume_edit.py:543`、`test_web_wording_sweep.py`、`test_web_parity.py`、`test_mcp_contract_tools.py` 的工具數 23）未改且綠；必須同步改者（`test_web_finished.py`、`test_actions_layer.py`）只增不減：沒有刪除或放寬斷言，「下載交付包 之後開放」「Coming later」斷言原樣 | 自動：讀 diff 與上列測試 |
| TC-090 【機器可驗】 | 範圍；爆炸半徑 | 功能 | 實作完成後 | `git diff --stat <base>...HEAD` | 只含計畫「範圍」所列的檔；不含 `platform/abf_station/`、`.github/`、`hooks/`、`.specify/memory/constitution.md`、`plugin.json`、`confirm.py`、`store.py`、`jobs.py`；`web_board.py` 只有傳參與必要字串、不改 `STYLE`、沒有新增對 `web_finished` 的 import | 自動：讀 diff |
| TC-091 【機器可驗】 | 範圍：不改資料結構 | 功能 | 實作前後各取 `sqlite_master` | 比對 | 完全相同；沒有新表、沒有 migration；`index.json` 格式不變（仍為第 1 片的欄位） | 自動：新增測試；讀 diff |
| TC-092 【機器可驗】 | 計畫「文件」；完成標準 | 功能 | 實作完成後 | 讀 `docs/PLATFORM.md`、`docs/TESTING.md`、`CHANGELOG.md` | PLATFORM.md 寫明新路由、打包語意（結果＝本次勾選集合）、finish 介面（`packed_only`）、打包與刪除不是 MCP 工具；TESTING.md 有手動步驟；CHANGELOG 有條目 | 自動：讀文件 |
| TC-093 【機器可驗】 | 完成標準：整個套件綠 | 功能 | 實作完成後 | 跑整個 `platform/tests`（Windows 用 WSL，或看 CI） | 全綠（`test_tc047_tc051_other_docs_untouched` 單獨紅視同綠）；新測試每條標出 TC 編號 | 自動：全套件 |

## 實機走通

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-094 【實機驗】 | 原話 3：「目前我到底能不能夠用MCP請lab-agent跑完分析並顯示在網頁上? 這是我最基本的要求」；原話 1、2；完成標準手動走通 | 功能 | 本機起平台；MCP 客戶端已連上；一個已成功的分析 | 1. 用第 1 片送兩張圖並按「送出」確認。2. 開完成頁，看兩張預覽與「使用者與 LLM 產生」標籤。3. 勾一張，按「打包所選的圖」，看「圖」列。4. 刪除另一張。5. 確認完成頁在第 3 步之前交付包沒有圖 | 完成頁看得到兩張圖與標籤；「圖」列變為「已打包 1 張」；刪除後圖消失；操作者把每步輸出貼進 ledger；維護者回答「能」或指出哪裡不是他要的 | 手動：`docs/TESTING.md`（本案新增手動步驟） |
| TC-095 【實機驗】 | 作法 2：圖庫私有 | 例外 | 另一個使用者帳號；知道前一個帳號的圖的網址 | 該帳號登入後直接開 `/run/figure?run=…&name=…`，再開對方的完成頁 | 得到 404（不是圖）；完成頁看不到對方的圖；操作者貼出輸出 | 手動：`docs/TESTING.md` |
