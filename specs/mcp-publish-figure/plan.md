---
id: mcp-publish-figure
title: MCP 工具 publish_figure：使用者的 LLM 把圖＋程式碼＋參數存進該分析的私有圖庫，完成頁預覽、勾選、打包後才進交付包
tier: B
kinds: ui, backend
risk: M
serves: S2-GALLERY
lane: L-mcp-publish-figure
branch: feat/mcp-publish-figure
base: v3
source: 維護者 2026-11-07 方向裁示（見下）；DESIGN.md 第 9 畫面（第 75 行，M2-016b）；docs/ROADMAP.md M2-016b；佇列決策 studios-figures-source；platform/abf_platform/{mcp_server.py,actions/__init__.py,web.py,web_finished.py,store.py}
---

# mcp-publish-figure

> 風險分級：M。若實作需要動 `platform/abf_station/`、`.github/`、`hooks/`、憲法、`plugin.json`，或需要新資料表／遷移：立即停手，風險升 L 並回報。
> 本版取代前一版草稿（平台收圖、勾選只存查詢字串）。方向已由維護者 11-07 定案，下方「裁決」段記載。

## 目標
新增 MCP 工具 `publish_figure(run_id, filename, content_base64, code, params, caption)`：使用者自己串接的 LLM 依該分析的 pipeline 內容與使用者討論，產生圖或統計結果，把「圖＋產生它的程式碼＋參數＋說明」存進該分析的**私有圖庫**（預設只有該分析的擁有者看得到，不進交付包）。完成頁新增圖庫區塊：可預覽、可刪除、可勾選；使用者勾選並按「打包」之後，所選的圖才寫入交付包並往最後一關走。對使用者的意義：圖與統計怎麼畫、畫什麼，全由使用者與自己的 LLM 討論決定；平台只保管並在使用者確認後打包。

## 維護者原話（verifier 出題用）
1. 「改成根據pipline的內容，透過使用者自己串接的LLM討論生成圖片或統計分析，直到使用者點選打包之後才往最後一關走」→ 測試：未按「打包」前，完成階段（交付包與 finish 所見）不含任何圖；按「打包」後才含所選的圖；平台不預寫任何腳本。
2. 「具體打包什麼都是使用者跟LLM討論」→ 測試：打包內容完全等於使用者勾選的集合（0 張、部分、全部三態）；平台無預設勾選（圖庫中的圖一律預設**未**勾選）；平台不替使用者挑圖。
3. 「目前我到底能不能夠用MCP請lab-agent跑完分析並顯示在網頁上? 這是我最基本的要求」（11-07 前一版）→ 測試走完整條：呼叫 `publish_figure` → 完成頁看到該圖的預覽 `<img>`。
4. DESIGN.md 第 9 畫面（維護者 10-18）：「只要讓使用者能操作裡面的R，或是透過AI agent及時修蓋程式碼，然後能看得到圖片產生，最後要能夠打包圖片往下一步」→ 看得到圖、可打包往下一步；同段設計原文 “each with an ‘Include in package’ checkbox … the script goes into the package too” → 每張圖有勾選框，程式碼隨圖存放並在打包時一併進包。
5. 維護者 2026-11-05：Studio 跑在使用者自己的電腦、平台看不到圖（ADR 0010 Decided 第 3 點）→ 圖必須由使用者端的 LLM 主動送進平台，平台不去站台找。
6. 維護者 2026-10-27 用字裁示：「一樣要注意中文的顯示不能口語」→ 新增中文字串為正式書面語，英文版無中日韓字元。

## 範圍：檔案
只准改這些檔：
- `platform/abf_platform/actions/figures.py`（新檔）：動作 `publish_figure`、`list_figures`、`delete_figure`、`pack_figures`、`read_figure`。純檔案儲存，不碰 jobs、不碰站台。
- `platform/abf_platform/actions/__init__.py`：只加匯出，不改既有動作。
- `platform/abf_platform/mcp_server.py`：只註冊 `publish_figure` 一個新工具（刪除與打包不開放給 MCP，見「不做」）。
- `platform/abf_platform/store.py`：只加 `figures_root(platform_path, env)`，照 `uploads_root`（309 行）：`ABF_PLATFORM_FIGURES`，否則 platform.db 旁的 `figures` 資料夾。**不新增資料表**，`platform.db` schema 不動。
- `platform/abf_platform/web.py`：新路由 `GET /run/figure`、`POST /run/figure/delete`、`POST /run/figures/pack`（CSRF 與擁有權照 `POST /c/{rid}`、`POST /launch` 的既有做法）；完成頁傳參；新標頭（見作法 9）。
- `platform/abf_platform/web_finished.py`：圖庫區塊、`_package`「圖」列；字串進 `STRINGS`（zh／en 同鍵）。
- `platform/abf_platform/web_board.py`：只加傳參與必要字串；**不改 `STYLE`**；不得多加對 web_finished 的 import。
- `docs/PLATFORM.md`（工具數 22→23、新路由、儲存位置與 index.json 格式、限制、**明寫「publish_figure 直接寫入、不走確認頁」的例外**）、`docs/TESTING.md`（手動步驟）、`CHANGELOG.md`。
- 新測試：`platform/tests/test_publish_figure.py`、`platform/tests/test_web_figures.py`。
- 既有測試必須同步改（只增不減）：
  - `platform/tests/mcp/test_mcp_contract_tools.py`：`EXPECTED_TOOLS`（16 行）加 `publish_figure`；`mcp/snapshots/tools.json` 以 `ABF_UPDATE_MCP_SNAPSHOT=1` 重生；描述長度上限（214 行附近）不得超。
  - `platform/tests/mcp/test_mcp_contract_writes.py`：`WRITE_TOOLS`（29 行）與 112、138 行的無此 run 表。
  - `platform/tests/test_pat.py:384`（`len(tools) == 22`→23）、`test_actions_layer.py:28、225、634`、`test_chat_tools.py:15、45`（新工具非唯讀，不進唯讀集合，不進聊天工具集）。
  - `test_aws_ce.py:804-810`、`test_aws_launch.py:1155-1161`、`test_azure_ce.py:917-923`、`test_azure_launch.py:1114-1119`、`test_azure_upload.py:826-830` 及其他內嵌完整工具名清單者：先 `git grep -n '"read_run_file"' origin/v3 -- platform/tests` 逐檔判斷，只在完整清單加 `publish_figure`。
  - `platform/tests/test_web_finished.py`：91、173、250 行 `pack_rows`（「圖」列預期值，從「之後開放」改為無圖／有圖未打包／已打包三態）；216、221、253、394 行的 `下載交付包 之後開放`、`Coming later` 斷言**不動**（整包壓縮下載本任務不做）。
- 被釘住、**不得改動也不得放寬**的測試：
  - `test_results_files.py:698`、`test_web_guided_launch_preview.py:414`（`STYLE`／`CSS_SHA256` `719ce2ab…`）→ 不新增或改任何 CSS，只用既有 class；圖寬用 `<img width>` 屬性，不用 style 屬性。
  - `test_web_guided_launch_2d.py:685-707`（`test_tc049_other_pages_are_as_before`）：`/`、`/settings`、`/usage`、`/c/<rid>` 的 CSP 必須仍等於 `base_csp()`。`img-src 'self'` **只加在完成階段（`stage=finished`）的回應與 `/run/figure`**。
  - `test_web_guided_launch_2d.py:670-671、951`、`test_web_guided_launch_2.py:590`、`test_web_guided_launch_preview.py:361`：`/launch` 的 CSP 字串原樣。
  - `test_settings_pick_installed.py:688`、`test_web_resume_edit.py:543`：`web._HEADERS["Content-Security-Policy"]` 不得改（新標頭另建，如 `FIGURE_HEADERS`）。
  - `test_web_wording_sweep.py`：新增中文字串須通過禁用詞。
  - `test_web_finished.py:280-290` 一帶 `test_fs12_web_board_touches_are_minimal`。
  - 其餘 `web_board.STRINGS` 鍵集合、`test_web_board.py::test_tcl42_string_table`、`test_tcl44_no_external_url_script_or_style_attribute`、`test_web_parity.py`：新增的字串與頁面須通過。
- 依賴與檔案衝突（見「環境事實」）：與 `web-result-viewer` 計畫同碰 `web.py`、`web_finished.py`、`web_board.py`；本案排在其後，落地前 `git merge origin/v3`。

## 作法
1. **工具簽章**：`publish_figure(run_id: str, filename: str, content_base64: str, code: str = "", params: str = "", caption: str = "")`，回 `{state: "ok"|"refused", name, size, type, url, reason?}`。標註 `read_only_hint=False`、`destructive_hint=False`、`idempotent_hint=True`、`open_world_hint=False`。說明文字須寫明：圖由使用者與 LLM 討論後以任何程式（R、Python）產生；存入**私有圖庫**，不進交付包，使用者在完成頁勾選並按「打包」才會進包；只收 png、svg、jpg；上限；同名覆蓋；內容視為不受信任；建議以含腳本識別的檔名避免互相覆蓋。
2. **直接寫入、不走確認頁（維護者裁決）**：工具直接寫入，不建 `confirmations` 列。理由：只存使用者自己的圖到私有圖庫、不啟動／停止／刪除任何分析、可覆蓋可刪除、不進交付包。PLATFORM.md 現寫「寫入類工具都只詢問」，須明寫此為例外，並寫出理由。
3. **擁有權**：`run_id` 須為呼叫者自己的 run，與 `read_run_file` 同一個檢查；別人的與不存在的同一句回答。任何狀態皆可收圖。圖庫**預設私有**：只有 run 擁有者（同一個登入帳號）能經 `/run/figure`、完成頁、`list_figures` 看到；沒有分享功能。
4. **檔名安全**：`^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$`，副檔名（小寫比對）只准 `.png`、`.svg`、`.jpg`、`.jpeg`；拒絕 `..`、`/`、`\`、NUL、空白、前導 `.`；保留名 `index.json` 與暫存名拒絕；解析後路徑須在 `figures_root/<user>/<run_id>/` 內（縱深防禦）。
5. **大小與數量**：解碼後單檔 ≤ 5 MB（`figures.MAX_BYTES`）；每個 run ≤ 30 張（`MAX_PER_RUN`）；`caption` ≤ 200 字元；`code` ≤ 100 KB（UTF-8，無 NUL）；`params` ≤ 10 KB（純文字，建議為 JSON 字串，平台不解析）；base64 以 `validate=True` 嚴格解碼，超長字串於解碼前依長度估算拒絕。常數放模組頂端，測試中可由 `ABF_PLATFORM_…` 環境變數調小。同名視為覆蓋（不重複計數，並**清除該圖的已打包旗標**，使用者須重新確認）；已滿再送新名字則拒絕。
6. **內容檢查（上傳內容視為不受信任）**：魔術位元組須與副檔名一致（PNG `\x89PNG\r\n\x1a\n`、JPEG `\xff\xd8\xff`）；SVG 須能以 UTF-8 解碼，且（不分大小寫）不含 `<script`、`<foreignObject`、`<!DOCTYPE`、`<!ENTITY`、`javascript:`、`on…=` 事件屬性、`<iframe`、`<embed`、`<object`、指向 `http(s)://` 或 `data:` 以外外部資源的 `href`／`src`；任一命中即**拒絕並說原因**，不改寫。平台**從不執行或解析成 HTML**：圖只在 `<img>` 載入；`code`、`params`、`caption` 一律當純文字，輸出時 `html.escape`，放在 `<pre>`／文字節點，不當連結、不當標記。
7. **儲存（檔案＋ index.json，不新增資料表）**：`figures_root/<user_id>/<run_id>/<name>` 與同資料夾 `index.json`。`index.json` 為 `{"version":1,"figures":{"<name>":{"size","type","caption","code_file","params_file","created","packed":false,"packed_at":null}}}`；程式碼與參數另存 `<name>.code.txt`、`<name>.params.txt`（純文字，不經 HTTP 以原型別服務）。寫入先寫暫存檔再 `os.replace`（`index.json` 一律最後更新）；檔案 0600、資料夾 0700。數量以 `index.json` 重算，不另存計數。`index.json` 損毀時視為空圖庫並回明確錯誤，不拋例外、不覆寫他人資料。
8. **完成頁圖庫區塊**（`stage=finished`、run 為 succeeded、擁有者）：每張圖一個 `<figure>`：`<img src="/run/figure?run=&name=" alt="<說明或檔名>" width="240" loading="lazy">`、檔名、說明、大小、標籤「使用者與 LLM 產生」（zh／en 字串，每張都標）、「檢視程式碼與參數」（`<details>` 內 `<pre>`）、「下載」連結、勾選框（`name="fig"`，**預設不勾**）、刪除按鈕（POST `/run/figure/delete`，CSRF）。區塊最下方一個「打包所選的圖」按鈕（POST `/run/figures/pack`，CSRF，帶勾選的 `fig` 值；不用 JavaScript）。無圖時顯示一行提示：圖庫為空，可請自己的 LLM 以 MCP 工具 publish_figure 送入。頁面不輪詢、不自動重整。
9. **打包語意**：`pack_figures(run, names)` 以白名單（必須在 `index.json` 內）比對；對所選的圖設 `packed=true`、`packed_at`，**未選的圖設回 false**（打包結果＝本次勾選的集合）；0 張亦合法（清空）。交付包「圖」列依 `packed` 顯示：無圖庫「無」、有圖未打包「n 張在圖庫，尚未打包」、已打包「已打包 m 張」並列檔名；打包的圖連同其 `code`／`params` 文字列為交付包內容（圖與程式碼同進包，對應 DESIGN.md「the script goes into the package too」）。**finish 只收 `packed=true` 的圖**：實作上，凡讀取「交付包中的圖」之處一律走 `list_figures(run, packed_only=True)`；本任務不改 `finish` 的 MCP prompt 與腳本（它在使用者端），僅在 PLATFORM.md 寫明介面：`list_figures`／`/run/figure` 與 `packed` 旗標是它的來源。整包壓縮下載仍為「之後開放」。
10. **`GET /run/figure?run=&name=[&download=1]`**：要登入 cookie；run 須為自己的；`name` 須在 `index.json` 內（絕不依使用者字串組路徑）；`Content-Type` 由伺服器依副檔名決定；標頭含 `X-Content-Type-Options: nosniff`、`Cache-Control: private, no-store`、`Content-Security-Policy: sandbox; default-src 'none'; style-src 'unsafe-inline'`（SVG 做法照 `launch_diagram`，web.py 約 966 行）；`download=1` 加 `Content-Disposition: attachment; filename="<name>"`。找不到一律 404 純文字一行。**依賴 web-result-viewer 的圖片預覽路由**：若該計畫已落地並提供可重用的圖片預覽標頭／輔助函式，則重用而不複製；本路由只負責「圖庫的圖」（`figures_root`），不負責站台結果檔。
11. **CSP**：僅 `stage=finished` 的回應與 `/run/figure` 使用含 `img-src 'self'` 的新標頭（照 `LAUNCH_HEADERS`，web.py 約 96–98 行）；`_HEADERS` 原樣；`/`、`/settings`、`/usage`、`/c/<rid>` 不變。若完成階段與看板同一處理函式，只在該階段改標頭。
12. **保存與刪除**：圖與交付包保存到使用者手動刪除，平台不設自動過期、不做背景清理。刪除僅有完成頁按鈕（刪圖檔、其 code／params、其 index 項；已打包的圖被刪除即自交付包移除，頁面刪除前有一句說明）。使用者刪除分析（`forget`）時圖庫是否一併刪除：**不連動**（維護者說保存到手動刪除），PLATFORM.md 寫明。
13. **不新增依賴**（不引入 PIL、defusedxml）；不經 jobs、不經 agent、不接觸站台。
14. **文件**：PLATFORM.md「Twenty-two tools」改 23、「Fifteen read-only」維持 15；TESTING.md 加手動步驟（呼叫 publish_figure、完成頁看到預覽與「使用者與 LLM 產生」標籤、勾選並打包、刪除、試傳含 script 的 SVG 被拒）。

## 失敗先行測試
`platform/tests/test_publish_figure.py`（動作層與 MCP 層）：
- `test_publish_png_is_stored_and_listed`：送最小 PNG→`ok`；`list_figures` 回大小、類型、說明；`code`／`params` 存為同資料夾純文字檔。
- `test_new_figure_is_private_and_not_packed`：新圖 `packed=false`；`list_figures(packed_only=True)` 為空；另一帳號 `list_figures` 與 `read_figure` 皆不得見。
- `test_same_name_overwrites_resets_packed_and_counts_once`。
- `test_other_users_run_and_unknown_run_get_the_same_answer`。
- `test_bad_names_refused`（參數化）：`../x.png`、`a/b.png`、`a\\b.png`、`.hidden.png`、`x.exe`、`x.png.exe`、`x.html`、`index.json`、空字串、81 字元、含空白、含 NUL；檔案系統不得出現任何新檔。
- `test_extension_must_match_magic_bytes`、`test_size_limit`（5 MB＋1 拒、剛好收）、`test_count_limit`（第 31 張新名拒、覆蓋收）、`test_bad_base64_refused`、`test_caption_code_params_limits`。
- `test_svg_with_script_or_event_or_external_ref_refused`（`<script>`、`onload=`、`<foreignObject>`、`<!DOCTYPE`／`<!ENTITY`、`href="http://…"`、`javascript:`、大小寫混寫）與 `test_plain_svg_accepted`。
- `test_pack_figures_whitelist_and_set_semantics`：不在 `index.json` 的名字被拒；打包 {a,b} 後再打包 {b}→a 回到未打包；打包 {} 合法。
- `test_delete_figure_removes_files_and_pack_state`、`test_corrupt_index_json_is_empty_gallery_not_crash`。
- `test_nothing_written_outside_figures_root`：`figures_root` 之外無新檔；`platform.db` 的 `sqlite_master` 前後相同。
- `test_publish_figure_is_a_write_tool_without_a_yes_page`：`readOnlyHint` 為 False、`destructiveHint` 為 False；不建立任何 `confirmations` 列；不進聊天工具集。
- `test_tool_count_and_snapshot`：工具 23 個，描述未超限。
- `test_input_refusal_and_system_unavailable_are_distinct`（PITFALLS 對應）：輸入被拒與儲存不可寫各有不同回答。

`platform/tests/test_web_figures.py`（網頁層）：
- `test_figure_route_needs_login`；別人的 run 與不存在的圖同一個 404 一行。
- `test_figure_route_headers`：`nosniff`、`no-store`、SVG 的 CSP 含 `sandbox`、`default-src 'none'`、不含 `script-src`；`Content-Type` 依副檔名。
- `test_download_flag_sends_attachment`、`test_route_cannot_reach_other_files`（`name=../../platform.db`、`index.json`、`x.code.txt`、`%2e%2e%2f…` 皆 404）。
- `test_finished_page_gallery_has_img_label_checkbox_delete`：zh 與 en；有 `<img` 指向 `/run/figure`、每張有「使用者與 LLM 產生」、`name="fig"` 且**無 `checked`**、刪除表單帶 CSRF；說明、程式碼、參數含 `<script>` 時輸出已逸出。
- `test_finished_gallery_empty_line`、`test_package_row_three_states`（無圖／有圖未打包／已打包）。
- `test_pack_post_requires_csrf_and_owner`：無 token、錯 token、他人 run 皆拒，且不改 `index.json`。
- `test_nothing_in_package_until_pack_pressed`（原話 1）：發佈 3 張→交付包「圖」列為未打包、`packed_only` 為空；勾 2 張按「打包」→恰為該 2 張（原話 2）。
- `test_delete_post_requires_csrf_and_owner`。
- `test_finished_csp_gets_img_src_but_other_pages_do_not`：完成階段含 `img-src 'self'`；`/`、`/settings`、`/usage`、`/c/<rid>` 仍等於 `base_csp()`。
- `test_style_untouched`（`719ce2ab…`）、`test_no_refresh_and_no_poll_on_finished`、`test_no_inline_style_or_script_in_gallery`。
- `test_strings_table_parity_and_wording`：zh／en 同鍵；en 無中日韓字元；zh 無禁用詞。

## 完成標準（done when）
- 新測試全綠；「必須同步改」的既有測試綠；「被釘住」的測試未改且綠。
- 整個 `platform/tests` 套件綠（`test_tc047_tc051_other_docs_untouched` 單獨紅視同綠）。
- 手動走通（ledger 附輸出）：本機起平台，以 MCP 客戶端呼叫 `publish_figure` 送一張 matplotlib PNG（附 code、params），完成頁看到預覽與標籤，勾選並打包，交付包「圖」列變為已打包；再刪除一張。
- 截圖（risk M、UI 守則）：`scripts/ui_check.py` 若存在即跑，1440 與 390 寬 × zh／en 共 4 張完成頁，axe 無 serious／critical；另補「圖庫為空」「有 ≥ 3 張（含一張 SVG）未打包」「已打包」三態；若 `ui_check.py` 不存在，用 Playwright 經 `with_server.py` 拍同樣的圖並標 axe 為 UNVERIFIED。截圖不存進 Drive 工作區。
- `git diff --stat` 不含 `platform/abf_station/`、`.github/`、`hooks/`、憲法、`plugin.json`（含則升 L 並回報）。
- ledger 貼：新增常數、`index.json` 範例、`sqlite_master` 前後比對、`git diff --stat`。

## 環境事實
- 現況（origin/v3）：MCP 22 個工具（PLATFORM.md 439 行）；`read_run_file` 只回文字，二進位只給 `/run/file` 連結；完成頁「圖」列固定「之後開放」，整包下載也「之後開放」；`finish` 是 MCP prompt／技能（使用者端），平台沒有 `finish` 或 `build_package` 動作。
- DESIGN.md 在 repo 根目錄（非 docs/）；第 9 畫面（約 75 行）原寫 “live list of `analysis/figures/` … ‘Include in package’ checkbox … the script goes into the package too”，本案是其替代設計（合併 M2-016b）。
- 圖像傳遞先例：`GET /launch/diagram`（`web.py` 約 943–968）；`LAUNCH_HEADERS`（約 96–98）是「只此頁允許 `img-src 'self'`」先例；檔案儲存先例：`store.uploads_root`（309 行）與 `actions/uploads.py`。
- 寫入型網頁表單先例：`POST /launch`、`POST /c/{rid}`、`POST /upload`（web.py 檔頭註解 15–36 行）皆以每次登入的 CSRF token 保護；`POST /upload` 示範「人按下按鈕即是同意，無確認頁」。
- 全站標頭 `_HEADERS`（`web.py` 85–89）含 `nosniff`、`default-src 'none'`、`frame-ancestors 'none'`；不加 `img-src` 就看不到圖。
- **依賴 `web-result-viewer`（圖片預覽路由）**：該計畫檔目前不在 `memory/dev-plans/`（相近的是 `results-files.md`、`results-outputs.md`、`011c-results-page.md`），developer-agent 排程時須確認其 id 與落地狀態。處理：（a）本案排在它之後；（b）它新增的預覽路由／標頭輔助函式若已在 v3，重用；（c）兩案同碰 `web.py` 的路由表與 CSP 區、`web_finished.py` 的完成頁，落地前 `git merge origin/v3` 並以合併後的檔案為準，衝突時保留對方的行為、只重放本案的新增；（d）不得為通過合併而放寬任何被釘住的測試。若它尚未落地，本案自帶 `/run/figure`，且不得預先佔用它計畫的路由名。
- 決策背景：ADR 0010 Decided 第 3 點；佇列決策 `studios-figures-source`。
- PITFALLS 已查（docs/PITFALLS.md；`docs/solutions/` 不存在），相符項：
  - 「`read_run_file` 與 `list_site_files` 在共用連線過期後誤答路徑被拒」（PITFALLS.md:2543-2548；症狀：第一步 ssh 失敗被當成輸入錯誤）→ 本案不經站台；但錯誤須區分「輸入拒絕」與「系統不可用」，已列測試。
  - 「兩支腳本預設寫同一個 `analysis/figures`，後跑的蓋掉前一個」（PITFALLS.md:1550、1569-1572）→ 同名覆蓋是既定行為；說明文字建議含腳本識別的檔名，覆蓋時清除已打包旗標。
  - 其餘條目與本案無關。
- 風險備註：這是平台第一次持有使用者上傳位元組並對外服務；安全線＝擁有權＋私有預設、檔名白名單、魔術位元組、SVG 拒絕清單、`<img>` 載入、`sandbox` CSP、`attachment` 下載、純文字輸出逸出、POST 的 CSRF，逐條有測試。磁碟：每 run 30×5 MB＝150 MB，無跨 run 總量上限且保存到手動刪除（列為後續）。

## 不做
- **裁決（維護者 11-07，寫於此以供閱卷）**：（1）本案**合併 M2-016b 圖片清單設計**（DESIGN.md 第 9 畫面約 75 行的 “Figures produced” 清單），以「私有圖庫＋勾選＋打包」取代其「即時列出 `analysis/figures/`（JS）」；（2）**作廢 `memory/dev-plans/studios-figures.md` 與本案矛盾之處**：該案「圖來自站台結果資料夾 `run_outputs`」「勾選只存查詢字串 `fig`」「完成頁只列檔名與下載連結、不內嵌預覽」「不宣稱已打包」均以本案為準；該案不得與本案同時進行，其餘未矛盾部分（Studio 區塊提示）由 developer-agent 於佇列處理，不在本案。
- 不做整包壓縮下載（交付包「下載」仍「之後開放」）；不改 `finish` 的 MCP prompt／使用者端腳本（僅提供介面，見作法 9）。
- 不做 MCP 端刪圖或打包（打包是使用者在網頁上的決定，刪除只在網頁）；不做圖的分享、跨 run 圖庫、重新排序、縮圖產生。
- 不做「依 pipeline 預先寫好 R／分析腳本」：圖與統計由使用者自己的 LLM 與使用者討論產生，平台不預寫腳本、不推薦分析。
- 不做每位使用者總量上限、不做自動過期（後續切片）。
- 不改 `platform/abf_station/`、站台協定、jobs 種類、platform.db schema；不新增依賴；不改 CSS；不改 `/launch`、看板、設定、費用頁的 CSP。
- 不執行或解析上傳內容；不做 SVG 改寫式消毒（只拒絕）。

## 裁決（lead，2026-11-07，回應計畫撰寫者的四點）
1. 依賴計畫 id 是 `web-result-viewer`（尚未落地）。本案排在它之後，重用它的預覽路由；落地前 merge origin/v3，檔案衝突處理照「環境事實」。
2. finish 沒有平台動作屬實，接受以 `index.json` 的 `packed` 旗標＋`list_figures(packed_only=True)` 當介面，本次不改 finish。
3. 打包用網頁 POST＋CSRF；刪除只在網頁、MCP 不開放刪除與打包；forget 分析時不連動刪圖庫——三點接受（偏保守；維護者說過「使用者按打包才是確認」）。
4. 同名覆蓋會清除已打包旗標——接受。

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
