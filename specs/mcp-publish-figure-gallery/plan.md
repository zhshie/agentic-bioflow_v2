---
id: mcp-publish-figure-gallery
title: publish_figure（第 2 片）：完成頁私有圖庫預覽、勾選打包、刪除（僅網頁、僅限擁有者），打包後才進交付包
tier: B
kinds: ui, backend
risk: M
serves: S2-GALLERY
lane: L-mcp-publish-figure-gallery
branch: feat/mcp-publish-figure-gallery
base: v3
blocked_on: mcp-publish-figure, web-result-viewer
source: 維護者 2026-11-07 方向裁示、2026-11-12 選 B（見「裁決」段）；DESIGN.md 第 9 畫面（第 75 行，M2-016b）；docs/ROADMAP.md M2-016b；platform/abf_platform/{web.py,web_finished.py,web_board.py,actions/figures.py}
---

# mcp-publish-figure-gallery

> 風險分級：M（網頁畫面另附截圖）。不動 `confirm.py`、`store.py`、`jobs`、憲法、`platform/abf_station/`、`.github/`、`hooks/`、`plugin.json`；需要動時立即停手回報、升 L。
> 本片依賴第 1 片 `mcp-publish-figure`（確認通道、遷移、寫入、`list_figures`、`index.json` 格式、`figures_root`）已落地；以及 `web-result-viewer`（圖片預覽路由）。第 1 片先上。

## 目標
第 1 片已讓使用者在確認頁按「送出」後，把圖寫進該分析的私有圖庫（預設不進交付包）。本片在完成頁顯示這個圖庫：預覽、標示來源、檢視程式碼與參數、勾選、刪除，並讓使用者按「打包」才把所選的圖放進交付包。對使用者的意義：圖由使用者與自己的 LLM 討論、經本人確認存入；打包什麼完全由使用者在網頁上決定，平台不替使用者挑圖。

## 維護者原話（verifier 出題用）
1. 「改成根據pipline的內容，透過使用者自己串接的LLM討論生成圖片或統計分析，直到使用者點選打包之後才往最後一關走」→ 測試：未按「打包」前，完成階段（交付包與 finish 所見）不含任何圖；按「打包」後才含所選的圖；平台不預寫任何腳本。
2. 「具體打包什麼都是使用者跟LLM討論」→ 測試：打包內容完全等於使用者勾選的集合（0 張、部分、全部三態）；平台無預設勾選（圖庫中的圖一律預設**未**勾選）；平台不替使用者挑圖。
3. 「目前我到底能不能夠用MCP請lab-agent跑完分析並顯示在網頁上? 這是我最基本的要求」→ 測試走完整條：呼叫 `publish_figure`（回待確認申請）→ 本人在確認頁按「送出」→ 完成頁看到該圖的預覽 `<img>`；未按「送出」前完成頁無圖。
4. DESIGN.md 第 9 畫面（維護者 10-18）：「只要讓使用者能操作裡面的R，或是透過AI agent及時修蓋程式碼，然後能看得到圖片產生，最後要能夠打包圖片往下一步」→ 看得到圖、可打包往下一步；同段設計原文 “each with an ‘Include in package’ checkbox … the script goes into the package too” → 每張圖有勾選框，程式碼隨圖存放並在打包時一併進包。
5. 維護者 2026-11-05：Studio 跑在使用者自己的電腦、平台看不到圖（ADR 0010 Decided 第 3 點）→ 圖只來自使用者端 LLM 經第 1 片送入的內容，平台不去站台找。
6. 維護者 2026-10-27 用字裁示：「一樣要注意中文的顯示不能口語」→ 新增中文字串為正式書面語，英文版無中日韓字元。
7. 維護者 2026-11-12 回「好」＝選 B（見「裁決」段）→ 測試：圖庫只含經確認通道寫入者；打包與刪除不產生任何 MCP 寫入工具，也不繞過人。

## 範圍：檔案
只准改這些檔：
- `platform/abf_platform/actions/figures.py`（第 1 片已建）：加 `read_figure`、`delete_figure`、`pack_figures`。純檔案儲存，只寫 `figures_root/<user>/<run_id>/`。
- `platform/abf_platform/web.py`：新路由 `GET /run/figure`、`POST /run/figure/delete`、`POST /run/figures/pack`；完成頁傳參；新標頭 `FIGURE_HEADERS`。
- `platform/abf_platform/web_finished.py`：圖庫區塊、`_package`「圖」列；字串進 `STRINGS`（zh／en 同鍵）。
- `platform/abf_platform/web_board.py`：只加傳參與必要字串；**不改 `STYLE`**；不得多加對 web_finished 的 import。
- `docs/PLATFORM.md`（新路由、打包語意、finish 介面）、`docs/TESTING.md`（手動步驟）、`CHANGELOG.md`。
- 新測試：`platform/tests/test_web_figures.py`；`test_publish_figure.py` 追加 pack／delete 的動作層測試。
- 既有測試必須同步改（只增不減）：`platform/tests/test_web_finished.py` 91、173、250 行 `pack_rows`（「圖」列預期值改為無圖／有圖未打包／已打包三態；`下載交付包 之後開放`、`Coming later` 斷言**不動**）；`test_actions_layer.py` 713 行一帶「只從網頁寫入、無 MCP 工具」的清單加 `delete_figure`、`pack_figures`（先 `git grep -n "PAGE_WRITE" origin/v3 -- platform/tests` 確認名稱）。
- **不得改動也不得放寬**的測試：
  - `test_results_files.py:698`、`test_web_guided_launch_preview.py:414`（`STYLE`／`CSS_SHA256` `719ce2ab…`）→ 不新增或改任何 CSS，只用既有 class；圖寬用 `<img width>` 屬性。
  - `test_web_guided_launch_2d.py:685-707`（`test_tc049_other_pages_are_as_before`）：`/`、`/settings`、`/usage`、`/c/<rid>` 的 CSP 必須仍等於 `base_csp()`；`img-src 'self'` **只加在完成階段（`stage=finished`）的回應與 `/run/figure`**。
  - `test_web_guided_launch_2d.py:670-671、951`、`test_web_guided_launch_2.py:590`、`test_web_guided_launch_preview.py:361`：`/launch` 的 CSP 字串原樣。
  - `test_settings_pick_installed.py:688`、`test_web_resume_edit.py:543`：`web._HEADERS["Content-Security-Policy"]` 不得改（新標頭另建）。
  - `test_web_wording_sweep.py`、`test_fs12_web_board_touches_are_minimal`、`test_web_board.py::test_tcl42_string_table`、`test_tcl44_no_external_url_script_or_style_attribute`、`test_web_parity.py`、`test_mcp_contract_tools.py`（工具數維持第 1 片的 23，本片不新增 MCP 工具）。
- 與 `web-result-viewer` 同碰 `web.py` 路由表與 CSP 區、`web_finished.py`、`web_board.py`；落地前 `git merge origin/v3`，衝突時保留對方行為、只重放本片新增。

## 作法
1. **完成頁圖庫區塊**（`stage=finished`、run 為 succeeded、擁有者）：每張圖一個 `<figure>`：`<img src="/run/figure?run=&name=" alt="<說明或檔名>" width="240" loading="lazy">`、檔名、說明、大小、標籤「使用者與 LLM 產生」（每張都標）、「檢視程式碼與參數」（`<details>` 內 `<pre>`）、「下載」連結、勾選框（`name="fig"`，**預設不勾**）、刪除按鈕（POST `/run/figure/delete`）。區塊最下方一個「打包所選的圖」按鈕（POST `/run/figures/pack`，帶勾選的 `fig` 值；不用 JavaScript）。無圖時顯示一行提示：圖庫為空，可請自己的 LLM 以 MCP 工具 publish_figure 提出，經本人在確認頁按「送出」後存入。有待確認申請時，區塊上方一行提示並連到 `/c/<rid>`。頁面不輪詢、不自動重整。`code`、`params`、`caption` 一律當純文字 `html.escape`，放 `<pre>`／文字節點。
2. **`GET /run/figure?run=&name=[&download=1]` 與 CSP**：要登入 cookie；run 須為自己的；`name` 須在 `index.json` 內（絕不依使用者字串組路徑）；`Content-Type` 由伺服器依副檔名決定；標頭含 `X-Content-Type-Options: nosniff`、`Cache-Control: private, no-store`、`Content-Security-Policy: sandbox; default-src 'none'; style-src 'unsafe-inline'`（SVG 做法照 `launch_diagram`，web.py 約 966 行）；`download=1` 加 `Content-Disposition: attachment`。找不到一律 404 純文字一行。若 `web-result-viewer` 已提供可重用的圖片預覽標頭／輔助函式則重用。僅 `stage=finished` 的回應與 `/run/figure` 使用含 `img-src 'self'` 的新標頭（照 `LAUNCH_HEADERS`，web.py 約 96–98 行）；`_HEADERS` 原樣。圖庫一律私有，沒有分享功能。
3. **打包與刪除的 POST 範圍（逐項決定）**：`POST /run/figures/pack` 與 `POST /run/figure/delete` 都是**網頁專屬、僅限擁有者、以人按按鈕為確認**：（a）只認登入 cookie 的工作階段，**不收 Bearer／MCP token**，AI 沒有任何工具能到達它們（不新增 MCP 工具）；（b）CSRF token（綁工作階段與 run）＋同源檢查，照 `POST /c/{rid}`；（c）動作層（`pack_figures`、`delete_figure`）依工作階段使用者過濾，只能動自己 run 的圖，他人的與不存在的同一個 404／拒絕；（d）名稱以 `index.json` 白名單比對，不在內者拒絕且不改任何檔；（e）刪除表單於按鈕前有一句說明「會一併移出交付包」，這就是該次寫入的人工確認（先例：`POST /upload`、設定頁寫入）；兩者只寫 `figures_root/<user>/<run_id>/`，不建立 `confirmations` 列。維護者問題預設：不另開獨立確認頁。
4. **打包語意**：`pack_figures(run, names)`：對所選的圖設 `packed=true`、`packed_at`，**未選的圖設回 false**（打包結果＝本次勾選的集合）；0 張亦合法（清空）。交付包「圖」列依 `packed` 顯示：無圖庫「無」、有圖未打包「n 張在圖庫，尚未打包」、已打包「已打包 m 張」並列檔名；打包的圖連同其 `code`／`params` 文字為交付包內容。**finish 只收 `packed=true` 的圖**：凡讀取「交付包中的圖」之處一律走 `list_figures(run, packed_only=True)`；本任務不改 `finish` 的 MCP prompt 與腳本，僅在 PLATFORM.md 寫明介面。整包壓縮下載仍為「之後開放」。同名覆蓋清除已打包旗標（第 1 片已實作，本片只測交付包列隨之變化）。
5. 不新增依賴、不經 jobs、不經 agent、不接觸站台；不改 CSS。
6. 字串：zh 為正式書面語，en 無中日韓字元，zh／en 同鍵進 `STRINGS`；按鈕、符號、導向沿用 DESIGN.md 與既有頁面寫法，不自創，採用的選擇記進 ledger；與禁用字表衝突以禁用字表為準。

## 失敗先行測試
`platform/tests/test_publish_figure.py`（追加）：`test_pack_figures_whitelist_and_set_semantics`、`test_delete_figure_removes_files_and_pack_state`、`test_pack_resets_on_same_name_overwrite`。

`platform/tests/test_web_figures.py`：
- `test_figure_route_needs_login`；別人的 run 與不存在的圖同一個 404 一行；`test_figure_route_headers`（`nosniff`、`no-store`、SVG CSP 含 `sandbox`、不含 `script-src`）；`test_download_flag_sends_attachment`；`test_route_cannot_reach_other_files`（`name=../../platform.db`、`index.json`、`x.code.txt`、`%2e%2e%2f…` 皆 404）。
- `test_finished_page_gallery_has_img_label_checkbox_delete`：zh 與 en；`<img` 指向 `/run/figure`、每張「使用者與 LLM 產生」、`name="fig"` 且無 `checked`；輸出已逸出（含 `<script>` 的 code／說明）；`test_finished_gallery_empty_line`、`test_package_row_three_states`。
- `test_pack_and_delete_post_scope`：無 CSRF、錯 CSRF、他人 run、Bearer token（無 cookie）、`Origin` 不同源——皆拒且不改 `index.json` 與檔案；名稱不在白名單拒；MCP 工具清單中**沒有**打包或刪除工具；兩者皆不建立 `confirmations` 列。
- `test_nothing_in_package_until_pack_pressed`（原話 1）：確認存入 3 張→交付包「圖」列為未打包、`packed_only` 為空；勾 2 張按「打包」→恰為該 2 張，再勾 0 張→清空（原話 2）。
- `test_end_to_end_publish_confirm_preview`（原話 3）：呼叫→確認頁按送出→完成頁有 `<img>`；未按送出前完成頁無圖。
- `test_finished_csp_gets_img_src_but_other_pages_do_not`、`test_style_untouched`（`719ce2ab…`）、`test_no_refresh_and_no_poll_on_finished`、`test_no_inline_style_or_script_in_gallery`、`test_strings_table_parity_and_wording`。

## 完成標準（done when）
- 新測試全綠；「必須同步改」的既有測試綠；「不得改動」的測試未改且綠；整個 `platform/tests` 套件綠（`test_tc047_tc051_other_docs_untouched` 單獨紅視同綠）。
- 手動走通（ledger 附輸出）：用第 1 片送兩張圖並確認 → 完成頁看到兩張預覽與標籤 → 勾一張按「打包」，交付包「圖」列變為已打包 1 張 → 刪除一張；他人帳號看不到、直接請求 `/run/figure` 得 404。
- 截圖（UI 守則）：`scripts/ui_check.py` 若存在即跑，1440 與 390 寬 × zh／en 共 4 張完成頁，axe 無 serious／critical；另補「圖庫為空」「有 ≥ 3 張（含一張 SVG）未打包」「已打包」；若 `ui_check.py` 不存在，用 Playwright 經 `with_server.py` 拍同樣的圖並標 axe 為 UNVERIFIED。截圖不存進 Drive 工作區。
- `git diff --stat` 只含「範圍」所列的檔。

## 環境事實
- 第 1 片落地後的介面：`actions/figures.py` 的 `list_figures(run, packed_only=False)`、`index.json` 格式 `{"version":1,"figures":{"<name>":{"size","type","caption","code_file","params_file","created","packed","packed_at","request_id"}}}`、`store.figures_root`（`ABF_PLATFORM_FIGURES` 或 platform.db 旁的 `figures`）、檔案 0600／資料夾 0700。
- 完成頁「圖」列目前固定「之後開放」，整包下載也「之後開放」；`finish` 是 MCP prompt／技能（使用者端），平台沒有 `finish` 或 `build_package` 動作。
- DESIGN.md 在 repo 根目錄；第 9 畫面（約 75 行）原寫 “live list of `analysis/figures/` … ‘Include in package’ checkbox … the script goes into the package too”，本案是其替代設計（合併 M2-016b）。
- 圖像傳遞先例：`GET /launch/diagram`（`web.py` 約 943–968）；`LAUNCH_HEADERS`（約 96–98）；寫入型網頁表單先例：`POST /launch`、`POST /c/{rid}`、`POST /upload`（CSRF）。全站標頭 `_HEADERS`（`web.py` 85–89）含 `nosniff`、`default-src 'none'`；不加 `img-src` 就看不到圖。
- **依賴 `web-result-viewer`（圖片預覽路由）**：該計畫檔目前不在 `memory/dev-plans/`；排程時須確認 id 與落地狀態。其預覽路由／標頭輔助函式若已在 v3，重用；若尚未落地，本片自帶 `/run/figure`，不得預先佔用它計畫的路由名；不得為通過合併而放寬任何被釘住的測試。
- PITFALLS 已查（docs/PITFALLS.md；`docs/solutions/` 不存在）。與本片相符項：「兩支腳本預設寫同一個 `analysis/figures`，後跑的蓋掉前一個」（PITFALLS.md:1550、1569-1572）→ 同名覆蓋是既定行為，覆蓋時清除已打包旗標，交付包列隨之更新。其餘關鍵字（confirm.py、store.py、platform.db）本片不碰，PITFALLS 已查，無相符項。
- 風險備註：平台第一次對外服務使用者上傳位元組。安全線＝擁有權與私有預設＋名稱白名單（`index.json`）＋`<img>` 載入＋`sandbox` CSP＋`attachment` 下載＋純文字逸出＋POST 的 CSRF，逐條有測試。

## 不做
- **裁決（維護者 11-07，寫於此以供閱卷）**：（1）本案**合併 M2-016b 圖片清單設計**（DESIGN.md 第 9 畫面約 75 行的 “Figures produced” 清單），以「私有圖庫＋勾選＋打包」取代其「即時列出 `analysis/figures/`（JS）」；（2）**作廢 `memory/dev-plans/studios-figures.md` 與本案矛盾之處**：該案「圖來自站台結果資料夾 `run_outputs`」「勾選只存查詢字串 `fig`」「完成頁只列檔名與下載連結、不內嵌預覽」「不宣稱已打包」均以本案為準；該案不得與本案同時進行，其餘未矛盾部分（Studio 區塊提示）由 developer-agent 於佇列處理，不在本案。
- 不修憲法、不改 `confirm.py`／`store.py`／`jobs` 表；不新增 MCP 工具；不新增確認通道。
- 不做整包壓縮下載（交付包「下載」仍「之後開放」）；不改 `finish` 的 MCP prompt／使用者端腳本。
- 不做 MCP 端刪圖或打包；不做圖的分享、跨 run 圖庫、重新排序、縮圖產生；不做確認頁的圖像預覽。
- 不做「依 pipeline 預先寫好 R／分析腳本」：圖與統計由使用者自己的 LLM 與使用者討論產生，平台不預寫腳本、不推薦分析。
- 不做每位使用者總量上限、不做自動過期（後續切片）。
- 不改 `platform/abf_station/`、站台協定、jobs 種類；不改 CSS；不改 `/launch`、看板、設定、費用頁的 CSP。

## 裁決（lead，2026-11-07，回應計畫撰寫者的四點）
1. 依賴計畫 id 是 `web-result-viewer`（尚未落地）。本案排在它之後，重用它的預覽路由；落地前 merge origin/v3，檔案衝突處理照「環境事實」。
2. finish 沒有平台動作屬實，接受以 `index.json` 的 `packed` 旗標＋`list_figures(packed_only=True)` 當介面，本次不改 finish。
3. 打包用網頁 POST＋CSRF；刪除只在網頁、MCP 不開放刪除與打包；forget 分析時不連動刪圖庫——三點接受（偏保守；維護者說過「使用者按打包才是確認」）。
4. 同名覆蓋會清除已打包旗標——接受。

## 裁決（lead，11-12，維護者回『好』＝選 B）
**publish_figure 不得無確認寫入，不修憲法 7.0.0。** 改走既有四條確認通道之一（沿用 mcp-chat-confirm 的做法）：圖表發布前產生待確認項，維護者在確認頁按一次才真正寫檔；未確認不寫、不重試。UI 措辭、符號、導向等未決問題：一律沿用 DESIGN.md 與既有確認頁的現成寫法（不新創），採用的選擇記進 ledger；有衝突以禁用字表為準。合約與計畫中與此矛盾的條目由 verifier 重出（fix-contract-regrade-push）。

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
- **「需要人看的事」**：偵測器的其他發現（對比、常見字型等）與品味問題。這些不判 FAIL（範本味例外，見文末補充：判 FAIL）。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
- 注意：「看起來好不好」的最終判斷屬於維護者，靠 developer-agent 附在 PR 的截圖（B 級）決定，verifier 不替他下結論。
- **實際跑起來看（ACCEPTANCE，2026-11-03 加）**：用 `webapp-testing` 的 `with_server.py` 把真正的應用程式起起來，再用 Playwright 驗。腳本路徑 `G:/我的雲端硬碟/謝馬爾/.claude/skills/webapp-testing/scripts/with_server.py`，**先跑 `--help`** 看用法（把它當黑盒子用，不要先讀原始碼）；啟動指令與通訊埠寫在計畫裡。
  - repo 已有 `scripts/ui_check.py` 就直接跑它：1440／390 寬 × zh／en 共 4 張截圖，加 axe-core 無障礙掃描；**axe 出現 serious 或 critical 一律 FAIL**。
  - repo 還沒有 `ui_check.py`：verifier 自己用 Playwright（經 `with_server.py`）拍同樣 4 張截圖；axe 沒跑就標 **axe：UNVERIFIED**，並寫明缺什麼。
  - 截圖只能存到 repo 之外或 `.gitignore` 排除的資料夾，**絕不存進 Drive 工作區**；報告只貼路徑與張數。
  - 起不了應用程式（缺依賴、埠被占）標 UNVERIFIED 並寫明需要什麼，不改以靜態 HTML 當作通過。
- **範本味（制式 AI 樣板感）（2026-11-10 加）**：實作要避免千篇一律的預設樣式（預設字型加預設配色、無意義漸層與卡片堆疊、裝飾性圖示）；一切視覺決定以 DESIGN.md 為準。
- **與核可草稿比對（2026-11-10 加）**：若計畫附有維護者已核可的設計草稿或截圖（design 類任務的產出），實作畫面必須與它一致；不一致處寫進報告，不自行取捨。
- **文字檢查（2026-11-10 加）**：改過的頁面渲染成 HTML 後，自己先跑 impeccable 偵測器並處理其發現，再交付。

### verifier 補充（2026-11-10）

- **FAIL**：畫面有範本味（制式 AI 樣板感）；截圖與維護者核可的草稿不一致且報告未說明；impeccable 偵測器的違規未處理。以上三條原本列為「需要人看的事」的範本味，改為判 FAIL。
- 計畫附有核可草稿時，逐畫面把實跑截圖與草稿並列比對，不一致處逐條列出；沒有草稿可比對則標 UNVERIFIED 並寫明缺什麼。
- 出題（CONTRACT）加：每個畫面一條「與核可草稿一致」的 TC，一條「通過 impeccable 文字檢查」的 TC。

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

## 裁決（lead，2026-11-12 夜，回應 verifier P1–P9）

P1 至 P8：照 verifier 的建議答案。執行者把 P1、P8 的採用記進 ledger。
P9：接受。打包與刪除以「登入 cookie、CSRF、同源、本人按按鈕」為人的確認，不建 `confirmations` 列、不是 MCP 工具（計畫裁決 3、`POST /upload` 先例）。此點列入給維護者的晨報，請他留一句話；他若不接受，重開 TC-050 至 058、TC-062。
另：`/run/figure` 的回應標頭在 `web.py` 自建（TC-041），不沿用 `web_preview.image_headers`。axe 沒跑成就標 UNVERIFIED，不當成通過。

## 裁決（lead，2026-11-13 凌晨，對抗審之後的修正輪；等第 1 片修正輪併入後才開工）

對抗審：沒有腳本執行、跨使用者、CSRF、路徑穿越的問題。要修：
G1 `index.json` 讀改寫沒有鎖（`actions/figures.py` 的 `pack_figures`、`delete_figure`、第 1 片的 `write_confirmed`）：同時進行會遺失更新、已刪的項目復活、已確認存入的圖沒被列入。三處都用同一把每個圖庫資料夾一個的檔案鎖，從讀到替換全程持有。測試要用真的並行（或在讀與寫之間插入另一個操作）重現後才修。這一項會動第 1 片的 `write_confirmed`，是 lead 點名允許的。
G2 `index.json` 損毀時：完成頁要顯示圖庫出錯的提示（不是當成空圖庫）；打包與刪除先檢查損毀再檢查名稱，回同一句明確的話，不是 500。依此，TC-009 的預期由「當作空圖庫」改為「顯示圖庫暫時無法讀取的提示，回 200，不露出路徑」——這是 lead 對合約的修訂，列入晨報。
G3 `/run/figure` 回應的 CSP 補回 `form-action 'none'; base-uri 'none'; frame-ancestors 'none'`；SVG 在被當成文件直接開啟時（`Sec-Fetch-Dest: document`）一律以附件下載。
G4 `_write_index` 寫到一半失敗不得留下暫存檔。
G5 完成頁上每張圖的程式碼與參數只內嵌前 200 行（或 20 KB，先到者為準），其餘以一句話說明並請使用者下載；不改變存檔內容。這修訂 TC-004 的「完整、不截斷」為「前段完整、其餘可下載」，列入晨報。需要一條下載程式碼／參數原文的路徑：沿用 `/run/figure` 並加 `part=code|params`，只回純文字附件。
另：圖庫為空時保留完成頁既有的 15 秒重整（v3 上本來就有，被 `test_fs11` 釘住）；是否拿掉留給維護者。
