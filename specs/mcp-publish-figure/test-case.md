# 測試案例：MCP 工具 publish_figure（第 1 片：經確認通道存入私有圖庫）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
來源只有 `specs/mcp-publish-figure/plan.md`（本案沒有獨立 spec.md；計畫的「目標、作法、失敗先行測試、完成標準、不做」即規格）。
-->

**規格**：`specs/mcp-publish-figure/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者（或 AI）做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

編號格內的標記表示誰能判定：機器可驗＝在本機或 CI 用指令、測試或讀 diff 即可判定；實機驗＝要真實瀏覽器與人按按鈕或維護者親自看。

維護者原話編號沿用計畫「維護者原話」七條（原話 1 至 7）。原話 1、2、4 的「打包勾選三態、完成頁看得到圖」屬第 2 片，本片只驗到「新圖預設未打包、未確認不寫入」，其餘列為不在範圍並確認沒有偷做。

## User Story 1 — 提出申請、本人確認後才寫入私有圖庫（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 【機器可驗】 | 原話 3、7；目標；作法 2 | 功能 | 使用者有一個自己的分析；圖庫為空 | LLM 呼叫 `publish_figure`，帶一張合格 PNG，不帶 `user_confirmed` | 回 `state: "pending"`、`request_id`、`url` 為 `/c/<rid>`、`count: 1`。`confirmations` 只多一列 kind 為 `publish_figure`、狀態待確認。圖庫資料夾沒有任何新檔、沒有 `index.json`；`list_figures` 為空（未按「送出」前圖庫仍為空） | 自動：`platform/tests/test_publish_figure_confirm.py::test_unconfirmed_publish_writes_nothing`、`test_publish_figure.py::test_valid_png_request_is_pending_not_stored` |
| TC-002 【機器可驗】 | 原話 3；作法 2 | 功能 | TC-001 的待確認申請（兩張圖） | 本人在確認頁（PAGE 通道）按「送出」 | 圖庫寫入的檔案與 `index.json` 恰等於申請內容（檔名、位元組、說明、程式碼、參數）；`confirmations` 列為已確認、`channel` 為 PAGE；沒有對應的 `jobs` 列 | 自動：`test_publish_figure_confirm.py::test_confirm_through_each_channel_writes_exactly_the_requested_figures` |
| TC-003 【機器可驗】 | 作法 2 | 功能 | 同 TC-002 | 本人在 MCP 表單（ELICITED 通道）回答同意 | 同 TC-002，`channel` 為 ELICITED | 自動：同上（ELICITED 參數） |
| TC-004 【機器可驗】 | 作法 2 | 功能 | 待確認申請存在；本人在聊天中自己回答同意 | LLM 以該 `request_id` 加 `user_confirmed=true` 再呼叫，內容與種類雜湊相符 | 寫入內容恰等於申請內容；`channel` 為 CHAT | 自動：同上（CHAT 參數） |
| TC-005 【機器可驗】 | 作法 2；憲法安全網 | 例外 | 無待確認申請 | LLM 只帶 `user_confirmed=true`、不帶 `request_id` 呼叫 | 拒絕並說明需要本人確認；不寫檔、不改 `index.json`、不建立可直接核准的申請 | 自動：`test_publish_figure_confirm.py::test_model_cannot_confirm_itself` |
| TC-006 【機器可驗】 | 作法 2、5 | 例外 | 使用者甲有待確認申請；使用者乙登入 | 乙帶甲的 `request_id` 加 `user_confirmed=true` 呼叫 | 拒絕；不寫檔 | 自動：同上 |
| TC-007 【機器可驗】 | 作法 2、3 | 例外 | 待確認申請存在 | LLM 改動圖清單內容後，帶原 `request_id` 與 `user_confirmed=true` 呼叫（內容已改，回報 `changed`） | 拒絕；不寫檔；原申請不因此被核准 | 自動：同上 |
| TC-008 【機器可驗】 | 作法 2 | 例外 | 待確認申請存在 | LLM 帶 token（確認用憑證以外的任何 token 形式）呼叫想略過確認 | 拒絕；不寫檔 | 自動：同上 |
| TC-009 【機器可驗】 | 作法 2 | 例外 | 本機 stdio、沒有表單、沒有人可按 | 呼叫 `publish_figure` | 回「無法確認」（不是成功）；不寫檔；確認通道紀錄不會是 TERMINAL | 自動：`test_publish_figure_confirm.py`（無人可按案例） |
| TC-010 【機器可驗】 | 作法 1 | 功能 | 一次呼叫帶 3 張合格圖 | 呼叫後本人按一次「送出」 | `confirmations` 只有 1 筆申請（不是 3 筆）；按一次後 3 張全部寫入 | 自動：`test_publish_figure_confirm.py::test_one_request_covers_the_whole_list` |
| TC-011 【機器可驗】 | 原話 1、2；作法 9 | 功能 | 本人已確認一批圖 | 查 `index.json` 與 `list_figures(packed_only=True)`、並以另一帳號查 | 每張新圖 `packed` 為 false、`packed_at` 為 null；`packed_only` 結果為空（平台沒有預設勾選、沒有替使用者挑圖）；另一帳號看不到任何圖 | 自動：`test_publish_figure.py::test_private_and_not_packed_after_confirm` |
| TC-012 【機器可驗】 | 原話 4；作法 9 | 功能 | 申請含一張 PNG（附程式碼與參數）與一張 SVG | 核准後讀圖庫資料夾 | `<name>`、`<name>.code.txt`、`<name>.params.txt` 與 `index.json` 存在；`index.json` 為 `{"version":1,"figures":{"<name>":{"size","type","caption","code_file","params_file","created","packed":false,"packed_at":null,"request_id"}}}`，欄位齊全；程式碼隨圖存放（供第 2 片打包時一併進包） | 自動：`test_publish_figure.py`（儲存格式案例） |
| TC-013 【機器可驗】 | 作法 9 | 功能 | 在 POSIX 檔案系統上核准一批圖 | 查寫入結果的權限 | 檔案為 0600、資料夾為 0700（Windows 本機跳過，CI／WSL 必須跑） | 自動：`test_publish_figure.py`（權限案例） |
| TC-014 【機器可驗】 | 作法 3、9；PITFALLS 同名覆蓋 | 功能 | 圖庫已有 `a.png`，且已被標為已打包 | 再提出一份含 `a.png` 的申請 | 確認文字含「覆蓋」標記；核准後 `a.png` 內容被取代、`packed` 回到 false；圖庫張數不增加（覆蓋不重複計數） | 自動：`test_publish_figure.py::test_same_name_overwrites_resets_packed_and_counts_once` |
| TC-015 【機器可驗】 | 作法 7 | 功能 | 一份申請已核准成功 | 再送完全相同的內容 | 視為新的一次詢問（再產生待確認申請）；核准後冪等覆蓋，內容不變、不出錯 | 自動：`test_publish_figure_confirm.py`（核准後重送案例） |
| TC-016 【機器可驗】 | 作法 1；完成標準 | 功能 | MCP 伺服器啟動 | 讀工具清單與 `tools.json` 快照 | 有 `publish_figure`，參數為 `run_id`、`figures`、`request_id`、`user_confirmed`；`readOnlyHint` 與 `destructiveHint` 為 false、`idempotentHint` 為 true、`openWorldHint` 為 false；工具共 23 個；描述未超長度上限；描述寫明：必須經本人確認才會寫入、AI 不能自行確認也不得自行帶 `user_confirmed`、存入私有圖庫不進交付包、只收 png／svg／jpg、同名覆蓋、上限、內容視為不受信任 | 自動：`platform/tests/mcp/test_mcp_contract_tools.py`、`test_publish_figure.py::test_publish_figure_goes_through_the_confirm_channel` |
| TC-017 【機器可驗】 | 範圍：`test_chat_tools.py` | 功能 | 瀏覽器聊天工具集 | 列舉聊天可用工具 | `publish_figure` 不在其中（因夾帶圖檔位元組） | 自動：`platform/tests/test_chat_tools.py` |
| TC-018 【機器可驗】 | 作法 2；PITFALLS「輸入被拒」與「系統不可用」要分開 | 例外 | 申請已核准的瞬間，寫檔函式拋例外（如唯讀資料夾） | 本人按「送出」 | 該申請作廢並記下原因；圖庫無殘檔、`index.json` 不變；回給使用者的訊息與「輸入被拒」不同（說的是寫入失敗與下一步） | 自動：`test_publish_figure_confirm.py::test_write_failure_voids_the_request` |
| TC-019 【機器可驗】 | 作法 4 | 例外 | 申請建立後、核准前，圖庫已被填滿，或檔名變成保留名 | 本人按「送出」 | 核准當下重驗不合：該申請作廢、記原因、不寫入 | 自動：`test_publish_figure_confirm.py`（核准時重驗案例） |
| TC-020 【機器可驗】 | 作法 9 | 例外 | 核准一批圖 | 查圖庫資料夾 | 沒有任何暫存檔殘留；`index.json` 最後才更新（寫到一半失敗時 `index.json` 仍是舊內容） | 自動：`test_publish_figure.py::test_write_leaves_no_temp_files` |
| TC-021 【機器可驗】 | 作法 9 | 例外 | `index.json` 內容損毀 | 呼叫 `list_figures` 與新的提出申請 | 視為空圖庫並回明確錯誤，不拋例外、不當機 | 自動：`test_publish_figure.py::test_corrupt_index_json_is_empty_gallery_not_crash` |
| TC-022 【機器可驗】 | 範圍：`store.py` `figures_root` | 功能 | 一次設 `ABF_PLATFORM_FIGURES`、一次不設 | 取 `figures_root(platform_path, env)` | 有設時用該路徑；沒設時為 platform.db 旁的 `figures` 資料夾（照 `uploads_root`） | 自動：`test_publish_figure.py`（路徑案例） |

## User Story 2 — 建立申請之前的驗證（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 【機器可驗】 | 作法 6 | 例外 | 自己的分析 | 分別送檔名 `../x.png`、`a/b.png`、`a\b.png`、`.hidden.png`、`x.exe`、`x.png.exe`、`x.html`、`index.json`、`a.code.txt`、`a.params.txt`、空字串、81 字元、含空白、含 NUL、同一批內兩張同名 | 每一種都整批 `refused`；檔案系統沒有新檔、`confirmations` 沒有新列 | 自動：`test_publish_figure.py::test_bad_names_refused`（參數化） |
| TC-024 【機器可驗】 | 作法 6 | 功能 | 自己的分析 | 送檔名 `ok-1_a.b.png`、`X.PNG`、`y.jpeg`、剛好 80 字元的 `.png` | 全部通過檔名檢查（副檔名小寫比對，只准 `.png`、`.svg`、`.jpg`、`.jpeg`） | 自動：`test_publish_figure.py`（合法檔名案例） |
| TC-025 【機器可驗】 | 作法 8 | 例外 | 自己的分析 | 送內容是 PNG 但副檔名 `.jpg`、內容是 JPEG 但副檔名 `.png`、內容是任意文字但副檔名 `.png` | 皆拒；魔術位元組（PNG `\x89PNG\r\n\x1a\n`、JPEG `\xff\xd8\xff`）須與副檔名一致 | 自動：`test_publish_figure.py::test_extension_must_match_magic_bytes` |
| TC-026 【機器可驗】 | 作法 1、8 | 功能 | 自己的分析 | 各送一張合法 PNG、JPEG、SVG | 三種都成功建立待確認申請 | 自動：`test_publish_figure.py`（三格式案例） |
| TC-027 【機器可驗】 | 作法 1、7b | 例外 | 自己的分析 | 單次送 11 張；另送空清單 | 皆整批拒；沒有申請列 | 自動：`test_publish_figure.py::test_count_limits` |
| TC-028 【機器可驗】 | 作法 7b、7c | 功能 | 自己的分析 | 單次送 10 張；圖庫已滿 30 張時送一張「同名覆蓋」 | 兩者皆收（清單 1 至 10 張；覆蓋同名不重複計數） | 自動：同上 |
| TC-029 【機器可驗】 | 作法 7c | 例外 | 圖庫已有 30 張 | 再送一張新檔名 | 拒絕並說圖庫已滿 | 自動：同上（圖庫第 31 張） |
| TC-030 【機器可驗】 | 作法 7e | 例外 | 自己的分析 | 送 `content_base64` 含非法字元、或缺填充的字串 | 拒絕（以 `validate=True` 嚴格解碼）並說明哪一張 | 自動：`test_publish_figure.py::test_bad_base64_refused` |
| TC-031 【機器可驗】 | 作法 7d | 例外 | 自己的分析 | 送 `caption` 201 字元、`code` 超過 100 KB、`code` 含 NUL、`params` 超過 10 KB | 各自拒絕並說明哪一欄超過 | 自動：`test_publish_figure.py::test_caption_code_params_limits` |
| TC-032 【機器可驗】 | 作法 7d | 功能 | 自己的分析 | 送 `caption` 剛好 200 字元、`code` 剛好 100 KB、`params` 剛好 10 KB | 全部收 | 自動：同上（邊界） |
| TC-033 【機器可驗】 | 作法 8 | 例外 | 自己的分析 | 分別送 SVG 含 `<script`、`<SCRIPT`（大小寫）、`<foreignObject`、`<!DOCTYPE`、`<!ENTITY`、`javascript:`、`onload=` 之類事件屬性、`<iframe`、`<embed`、`<object` | 每一種皆拒並說原因；被拒的 SVG 不被改寫後放行（不做消毒改寫） | 自動：`test_publish_figure.py::test_svg_with_script_or_event_or_external_ref_refused` |
| TC-034 【機器可驗】 | 作法 8 | 例外 | 自己的分析 | 送 SVG 的 `href` 或 `src` 指向 `http://` 或 `https://` 外部資源 | 拒並說原因 | 自動：同上 |
| TC-035 【機器可驗】 | 作法 8 | 功能 | 自己的分析 | 送只含形狀與文字的單純 SVG | 收（建立待確認申請） | 自動：`test_publish_figure.py::test_plain_svg_accepted` |
| TC-036 【機器可驗】 | 作法 8 | 例外 | 自己的分析 | 送副檔名 `.svg` 但內容不是合法 UTF-8 | 拒 | 自動：`test_publish_figure.py`（SVG 編碼案例） |
| TC-037 【機器可驗】 | 作法 7a | 例外 | 自己的分析 | 送使 `len(json.dumps(bundle).encode())` 比 5 MiB（5 242 880 位元組）多 1 位元組的一份申請 | 拒；訊息含上限 5 MB 與目前大小 X MB，並含「這次送入的圖合計超過 5 MB 上限（目前 X MB），請分次或縮小圖檔」與其英文對照 | 自動：`test_publish_figure_confirm.py::test_bundle_size_cap_and_message` |
| TC-038 【機器可驗】 | 作法 7a | 功能 | 自己的分析 | 送使序列化後 `bundle_json` 剛好 5 MiB 的一份申請 | 收（建立待確認申請） | 自動：同上 |
| TC-039 【機器可驗】 | 作法 4、7 | 例外 | 使用者先送 10 份不合格申請 | 再送一份合格申請 | 10 份不合格都沒有申請列、不佔 10 筆待確認額度；第 11 份合格的仍成功 pending | 自動：`test_publish_figure.py`（拒絕不佔額度案例） |
| TC-040 【機器可驗】 | 作法 4；專長守則 backend | 例外 | 一批中第 2 張不合格 | 呼叫 | 整批拒；訊息說出是第幾張／哪個檔名、什麼原因，並說下一步怎麼做；不含堆疊、內部檔案路徑、SQL | 自動：`test_publish_figure_confirm.py::test_one_request_covers_the_whole_list`（任一張不合格案例） |

## User Story 3 — 確認頁（既有 /c/<rid> 增加新種類）（優先度 P1）

DESIGN.md 沒有為這個新種類另畫確認頁線稿（只有第 13 畫面「登入後確認」與既有確認頁）。本案一律沿用既有確認頁的版面與狀態；沒有決定的事不自創。新種類在確認頁的狀態：待確認、成功、逾時、已作廢／已處理、寫入失敗、他人開啟、CSRF 不符。清單不會是空的（1 至 10 張，空清單在建立前就被拒，見 TC-027），故沒有「空狀態」與「載入中」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 【機器可驗】 | 作法 15；原話 7 | 功能 | 本人有待確認的 `publish_figure` 申請；語言為中文 | 開 `/c/<rid>` | 標題「存入圖庫確認」；說明「以下為將存入圖庫的全部內容。確認無誤後，請按「送出」；按下後才會寫入圖庫。」；按鈕「送出」；表單帶 CSRF 欄位 | 自動：`test_publish_figure_confirm.py::test_confirm_page_for_publish_figure` |
| TC-042 【機器可驗】 | 作法 15；原話 6 | 功能 | 同上；語言為英文 | 開 `/c/<rid>` | 標題 "Confirm adding figures"；有對應的英文說明一句；按鈕 "Send"；整頁英文版不含任何中日韓字元 | 自動：同上 |
| TC-043 【機器可驗】 | 作法 3 | 功能 | 申請含兩張圖，其中一張附 30 行程式碼與參數，另一張與既有同名 | 開確認頁 | 逐張列出檔名、類型、大小、說明；程式碼只顯示前 20 行並標總行數（30）；列出參數；同名者有「覆蓋既有同名圖」標記 | 自動：同上 |
| TC-044 【機器可驗】 | 作法 8 | 例外 | 申請的說明、程式碼、參數內含 `<script>alert(1)</script>` | 開確認頁 | 以純文字逸出顯示（`&lt;script&gt;`），原始 `<script>` 不出現在 HTML 中 | 自動：同上 |
| TC-045 【機器可驗】 | 作法 3；不做：確認頁預覽 | 功能 | 待確認申請 | 開確認頁並檢查 HTML 與可對外取得的路徑 | 頁面沒有 `<img>`、沒有 `data:` 圖像；未確認的圖位元組沒有任何網址可取得 | 自動：同上 |
| TC-046 【機器可驗】 | 作法 15 | 功能 | 本人在確認頁按「送出」且寫入成功（N 張） | 看成功頁（中、英） | 中文「已存入圖庫 N 張。」；有連到該分析頁的連結；不出現工作編號；英文版有對應一句且無中日韓字元 | 自動：同上 |
| TC-047 【機器可驗】 | 作法 5；專長守則 backend | 例外 | 使用者甲的待確認申請；使用者乙已登入 | 乙開 `/c/<rid>` 並嘗試送出 | 403；不寫檔 | 自動：同上 |
| TC-048 【機器可驗】 | 作法 7 | 例外 | 申請已超過 600 秒 | 本人開頁並按「送出」 | 410，顯示既有的逾時寫法；不寫檔 | 自動：同上 |
| TC-049 【機器可驗】 | 作法 15 | 例外 | 申請已作廢或已處理過 | 開頁／再按「送出」 | 沿用既有確認頁「作廢」「已處理」寫法；不寫檔、不重複寫 | 自動：`test_publish_figure_confirm.py::test_expired_or_void_request_never_writes_even_if_retried` |
| TC-050 【機器可驗】 | 作法 4；PITFALLS | 例外 | 核准當下寫檔失敗 | 本人按「送出」 | 頁面說明寫入失敗與下一步（請重新提出），與「輸入被拒」「逾時」措辭不同；不寫檔；不洩漏內部路徑 | 自動：`test_publish_figure_confirm.py::test_write_failure_voids_the_request`（頁面部分） |
| TC-051 【機器可驗】 | 作法 15；專長守則 backend | 例外 | 待確認申請 | POST `/c/<rid>` 不帶 CSRF、或帶錯的 CSRF | 拒；不寫檔、申請狀態不變 | 自動：`test_publish_figure_confirm.py::test_confirm_page_for_publish_figure` |
| TC-052 【機器可驗】 | 範圍：`web.py`；專長守則 ui 前端限制 | 功能 | 新舊程式各渲染 `/c/<rid>` | 比對標頭、CSP、`CSS_SHA256`、路由表 | `_HEADERS`、`LAUNCH_HEADERS`、`/c/<rid>` 的 CSP、`CSS_SHA256` 完全不變；沒有新增路由；CSS 檔不變 | 自動：同上；加讀 diff |
| TC-053 【機器可驗】 | 專長守則 ui 前端限制 | 功能 | 渲染新種類的待確認頁與成功頁（中、英） | 檢查 HTML | 沒有 inline `style` 屬性或標籤；沒有請求任何外部網址（`http(s)://` 資源、外部字型或腳本） | 自動：新增測試掃描渲染結果 |
| TC-054 【機器可驗】 | 專長守則 ui：狀態表達 | 功能 | 渲染新種類的待確認、成功、逾時、寫入失敗頁 | 檢查 HTML | 每個狀態同時含符號與文字（與既有三種確認種類同一寫法），不得只靠 class 顏色 | 自動：新增測試掃描渲染結果 |
| TC-055 【機器可驗】 | 原話 6；範圍：用字掃描與對等性 | 功能 | `_PLAIN` 兩語言各加新種類一行 | 跑 `test_web_wording_sweep.py`、`test_web_parity.py`、`test_web_confirm_plain.py`、`test_confirm_page.py`、`test_clean_page.py` | 全綠；新增中文為正式書面語、無禁用口語字；英文版無中日韓字元；既有 launch、cancel、clean_work 三種的字句逐字不變（這些測試只增不減） | 自動：上列測試檔 |
| TC-056 【機器可驗】 | 專長守則 ui：文字檢查 | 功能 | 把新種類的待確認頁與成功頁（中、英）渲染成 HTML 檔 | 跑 `sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>` | 沒有未處理的違規；其他發現列入報告供人判斷 | 自動：閱卷時以偵測器執行 |
| TC-057 【機器可驗】 | 專長守則 ui：實際跑起來看 | 功能 | 本機以 `with_server.py` 起平台 | 有 `scripts/ui_check.py` 就跑它，否則用 Playwright：拍「待確認頁」「成功頁」各 1440 與 390 寬 × 中、英；跑 axe | 無橫向捲動；axe 無 serious 或 critical；截圖存在 repo 之外或被忽略的資料夾；沒有 ui_check.py 且沒跑 axe 時標 UNVERIFIED 並寫明缺什麼 | 自動：閱卷時執行並記錄路徑與張數 |
| TC-058 【實機驗】 | 專長守則 ui：與核可草稿比對；範本味 | 功能 | 計畫沒有附維護者核可的設計草稿；PR 附 TC-057 的截圖 | 維護者看「確認頁（待確認）」與「確認成功頁」截圖與實際頁面 | 維護者回覆這兩個畫面是他要的、沒有範本味；沒有草稿可比對的部分標 UNVERIFIED，操作者記下他的原話 | 手動：`docs/TESTING.md`（維護者看截圖） |

## User Story 4 — 擁有權與私有圖庫（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-059 【機器可驗】 | 作法 5 | 例外 | 使用者甲有分析 R；乙有自己的分析 | 乙對甲的 R、以及對一個不存在的 run 各呼叫 `publish_figure` | 兩次回同一句答覆（不洩漏哪個存在）；沒有申請列、不寫檔 | 自動：`test_publish_figure.py::test_other_users_run_and_unknown_run_get_the_same_answer` |
| TC-060 【機器可驗】 | 專長守則 backend：跨使用者（寫） | 例外 | 甲有待確認申請 | 乙在動作層以乙的身分對甲的申請呼叫 `approve`（以及用乙的 token 呼叫） | 被拒（確認者必須是提出者本人）；不寫檔 | 自動：`test_publish_figure_confirm.py::test_model_cannot_confirm_itself`（含他人案例） |
| TC-061 【機器可驗】 | 專長守則 backend：跨使用者（讀）；作法 5 | 例外 | 甲圖庫已有圖 | 乙以乙的身分呼叫 `list_figures`（甲的 run） | 看不到甲的任何圖（被拒或為空，與不存在同一答覆） | 自動：`test_publish_figure.py::test_private_and_not_packed_after_confirm` |
| TC-062 【機器可驗】 | 作法 5 | 功能 | 自己的分析分別處於執行中、失敗、完成 | 各提出一份申請 | 任何狀態皆可提出 | 自動：`test_publish_figure.py`（各狀態案例） |
| TC-063 【機器可驗】 | 作法 6、9 | 例外 | 嘗試各種路徑跳脫檔名並核准合法申請 | 檢查整個檔案系統 | 所有寫入都在 `figures_root/<user_id>/<run_id>/` 內；資料夾外沒有新檔；`sqlite_master` 除 CHECK 文字外前後相同 | 自動：`test_publish_figure.py::test_nothing_written_outside_figures_root` |
| TC-064 【機器可驗】 | 專長守則 backend：對等性 | 功能 | 動作層函式清單、MCP 工具清單、網頁動作清單 | 對等性測試同時列舉各邊 | `request_publish_figure` 與 `publish_figure` 一一對應；`WRITE_NAMES` 含 `publish_figure`；確認頁走既有 `approve`／`request_facts`，路由處理函式沒有第二份邏輯；缺一邊就失敗 | 自動：`platform/tests/test_actions_layer.py`、`test_web_parity.py` |

## User Story 5 — 確認額度、逾時、作廢與保留（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-065 【機器可驗】 | 作法 7 | 例外 | 同一使用者已有 10 筆待確認 | 再送第 11 筆 `publish_figure` | 拒，訊息為既有的「未送出：…」；不新增列 | 自動：`test_publish_figure_confirm.py::test_pending_limit_and_expiry_are_the_existing_ones` |
| TC-066 【機器可驗】 | 作法 7 | 功能 | 使用者有大量 `clean_work` 待確認 | 再送 `publish_figure` | `clean_work` 不佔 `publish_figure` 所在那一組額度 | 自動：同上 |
| TC-067 【機器可驗】 | 作法 7 | 例外 | 申請已超過 `PENDING_SECONDS`（600 秒） | 核准 | 狀態為逾時（expired）；不寫檔 | 自動：同上 |
| TC-068 【機器可驗】 | 作法 2、7 | 例外 | 申請已逾時或已作廢 | 重試核准／以 `request_id` 重呼叫 | 仍不寫檔；須由 LLM 重新呼叫產生新申請；不自動重試 | 自動：`test_publish_figure_confirm.py::test_expired_or_void_request_never_writes_even_if_retried` |
| TC-069 【機器可驗】 | 作法 2 | 例外 | 本人在 MCP 表單回答拒絕 | 完成表單 | 申請作廢；不寫檔；不改 `index.json` | 自動：`test_publish_figure_confirm.py::test_decline_in_form_voids_and_writes_nothing` |
| TC-070 【機器可驗】 | 作法 7 | 功能 | 同一人在剩餘 60 秒以上時重複送出同內容 | 兩次呼叫 | 沿用同一筆申請（同一 `request_id`），不新增列 | 自動：`test_publish_figure_confirm.py::test_pending_limit_and_expiry_are_the_existing_ones` |
| TC-071 【機器可驗】 | 作法 10 | 功能 | 申請已核准、圖已寫入 | 查 `bundle_json`；擁有者 `forget` 該分析後再查 | 核准後 `bundle_json`（含圖 base64）仍在；`forget` 後被清空；圖庫檔案不受影響；圖庫內刪圖不清已確認列的副本（文件已寫明） | 自動：`test_publish_figure_confirm.py::test_confirmed_row_keeps_bundle_until_forget` |
| TC-072 【機器可驗】 | 作法 10 | 功能 | `publish_figure` 的待確認列與作廢列超過 `KEEP_UNSENT_SECONDS`（7 天） | 跑既有清理流程 | 內容被清空，與既有種類相同；不另立規則 | 自動：`test_publish_figure_confirm.py`（保留期案例） |

## User Story 6 — 資料庫遷移與既有行為不變（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-073 【機器可驗】 | 範圍：`store.py`；專長守則 backend：migration | 功能 | 只有 `clean_work` 的舊 platform.db，內有舊 confirmations 列與有外鍵指向它的 jobs 列 | 開啟資料庫 | `confirmations` 的 kind CHECK 含 `publish_figure`；舊列數不變、`jobs.confirmation_id` 外鍵完整（`foreign_key_check` 無輸出）；`_confirmations_current` 要兩者都在才算新 | 自動：`test_publish_figure_confirm.py::test_confirmations_check_migration`、`test_cleanup_store.py`（新增遷移測試） |
| TC-074 【機器可驗】 | 作法 / 範圍：store.py | 例外 | 遷移中途故意失敗 | 開啟資料庫 | 回滾；舊表、舊列、外鍵完全保留；不留半成品 | 自動：同上 |
| TC-075 【機器可驗】 | 範圍：store.py | 功能 | 全新資料庫 | 插入 kind 為 `publish_figure`、`resume`、空字串的列 | `publish_figure` 收；`resume` 與空字串仍被拒 | 自動：同上；`test_cleanup_store.py`（CHECK 宣告與「仍拒絕」測試） |
| TC-076 【機器可驗】 | 範圍：store.py；L 級證明 (e) | 功能 | 遷移前後各取 `sqlite_master` | 比對 | 除 `confirmations` 的 CHECK 文字外完全相同；沒有新表；`jobs` 表與其 CHECK 前後逐字相同 | 自動：同上 |
| TC-077 【機器可驗】 | 範圍：`test_cleanup_store.py` 418、444、485 行 | 功能 | 更舊版本的資料庫（遷移前狀態） | 開啟 | 仍能遷移成功，且遷移後也收 `publish_figure`（新增斷言）；原有斷言不變 | 自動：`platform/tests/test_cleanup_store.py` |
| TC-078 【機器可驗】 | 作法 / 範圍：confirm.py；`test_existing_kinds_unchanged` | 功能 | 既有 launch、cancel、clean_work 流程 | 核准各一筆 | `confirm.JOB_KIND` 與 `jobs.CONFIRMED` 與基準相同；`approve()` 對三種的回傳與基準相同（仍排一個 job）；`NO_JOB_KINDS` 只含 `publish_figure` | 自動：`test_publish_figure_confirm.py::test_existing_kinds_unchanged` |
| TC-079 【機器可驗】 | 範圍：confirm.py | 功能 | 一筆 `publish_figure` 申請 | 核准 | `approve()` 回 `(rid, None)`；只把申請翻成已確認並記通道與時間；`jobs` 表沒有新列；寫檔在同一交易內由動作層傳入的函式完成 | 自動：`test_publish_figure_confirm.py::test_confirm_through_each_channel_writes_exactly_the_requested_figures` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 【機器可驗】 | 不做：MCP 端刪圖、打包；第 2 片 | 不在範圍 | 讀工具清單、動作層、路由表 | 找 `read_figure`、`delete_figure`、`pack_figures`、`GET /run/figure`、`POST /run/figures/pack`、`POST /run/figure/delete` | 全都不存在；MCP 只新增 `publish_figure` 一個工具（22 變 23，不是 24） | 自動：`test_mcp_contract_tools.py`；讀 diff |
| TC-081 【機器可驗】 | 原話 1、2、4（第 2 片部分）；不做：完成頁預覽 | 不在範圍 | 一個已有核准圖的分析 | 開完成頁、看交付包與 finish 所見 | 完成頁「圖」列仍為「之後開放」、沒有勾選框、沒有圖預覽；`web_finished.py`、`web_board.py` 未被修改；打包勾選 0 張／部分／全部三態不在本片 | 自動：讀 diff 與既有完成頁測試 |
| TC-082 【機器可驗】 | 不做：分享、跨 run 圖庫、重新排序、縮圖 | 不在範圍 | 讀工具描述與程式碼 | 找分享、跨 run、排序、縮圖功能 | 都不存在；圖庫只有擁有者可見 | 自動：讀 diff |
| TC-083 【機器可驗】 | 不做：每位使用者總量上限、自動過期、核准後丟棄位元組 | 不在範圍 | 核准一批圖 | 查總量檢查、過期機制與 `bundle_json` | 沒有每位使用者總量上限與自動過期；已確認列的 `bundle_json` 仍保留圖位元組到 `forget`（沿用既有規則） | 自動：`test_publish_figure_confirm.py::test_confirmed_row_keeps_bundle_until_forget`；讀 diff |
| TC-084 【機器可驗】 | 原話 1；不做：預先寫好腳本、不推薦分析 | 不在範圍 | 一個分析，LLM 尚未送任何圖 | 呼叫與核准 `publish_figure` 一次 | 圖庫與平台沒有任何預寫的 R 或分析腳本，除了使用者送入的內容外不產生任何檔案；工具與確認頁沒有推薦分析的文字 | 自動：`test_publish_figure.py::test_nothing_written_outside_figures_root` |
| TC-085 【機器可驗】 | 不做：整包壓縮下載；不改 `finish` | 不在範圍 | 讀 diff | 找壓縮下載與 `finish` 提示、技能、使用者端腳本的改動 | 沒有；交付包「下載」仍「之後開放」 | 自動：讀 diff |
| TC-086 【機器可驗】 | 不做：執行或解析上傳內容、SVG 改寫式消毒 | 不在範圍 | 核准一張合格 SVG；另送一張含 `<script` 的 SVG | 比對寫入位元組；看拒絕結果 | 合格 SVG 寫入的位元組與送入的逐位元相同；含 script 者被拒而非改寫；平台沒有把任何內容當 HTML 執行或解析 | 自動：`test_publish_figure.py::test_plain_svg_accepted`、`test_svg_with_script_or_event_or_external_ref_refused` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-087 【機器可驗】 | 安全網（憲法 191-195 行）：寫入工具未經人確認一律拒絕，新寫入工具附自己的拒絕測試；原話 7 | 例外 | 未經確認的 `publish_figure` 呼叫（任何形式） | 跑 `test_mcp_contract_writes.py` 的「未確認一次呼叫零副作用」參數化與 `test_publish_figure_confirm.py` | 新工具被參數化涵蓋且綠；零副作用（無檔案、無 `index.json`、無 job）；`test_publish_figure_confirm.py` 存在並含拒絕測試 | 自動：`platform/tests/mcp/test_mcp_contract_writes.py`、`test_publish_figure_confirm.py` |
| TC-088 【機器可驗】 | 安全網：寫入工具判定 | 功能 | `WRITE_TOOLS` 由 `readOnlyHint` 推導並比對 | 跑 `test_mcp_contract_writes.py`、`test_mcp_contract_tools.py`、`test_pat.py` | `publish_figure` 被判為寫入工具且推導結果與手寫清單相等；`EXPECTED_TOOLS` 含它；快照以 `ABF_UPDATE_MCP_SNAPSHOT=1` 重生；`test_pat.py` 的 22 改 23 | 自動：上列測試檔 |
| TC-089 【機器可驗】 | 憲法 7.0.0 不編輯；原話 7 | 功能 | 實作完成後 | `git diff origin/v3 -- .specify/memory/constitution.md`；跑 `bash tests/constitution_6_test.sh` | diff 為空；測試綠（第 33 行逐字比對安全網該條） | 自動：`test_publish_figure_confirm.py::test_constitution_untouched`、`tests/constitution_6_test.sh` |
| TC-090 【機器可驗】 | L 級爆炸半徑 (a) | 功能 | 實作完成後 | `git diff --stat <base>...HEAD` | 只含計畫「範圍」所列的檔；不含 `platform/abf_station/`、`.github/`、`hooks/`、`.specify/memory/constitution.md`、`plugin.json`、`jobs.py`；不新增資料表 | 自動：讀 diff |
| TC-091 【機器可驗】 | L 級爆炸半徑 (b) | 功能 | 實作完成後 | 檢查 `confirm.py` 的 diff | 只新增；既有 launch、cancel、clean_work 路徑的行逐行未改；被改動的既有行為空或僅 `approve` 內新增分支（附清單） | 自動：讀 diff |
| TC-092 【機器可驗】 | L 級爆炸半徑 (c) | 功能 | 舊庫（只有 clean_work） | 遷移前後各列 `confirmations`、`jobs` 列數與 `foreign_key_check` 輸出 | 列數前後相同、外鍵檢查無輸出；輸出附在 ledger | 自動：`test_confirmations_check_migration`；ledger 輸出 |
| TC-093 【機器可驗】 | L 級爆炸半徑 (d) | 功能 | 實作完成後 | 全程式 grep 所有讀寫 `confirmations.kind` 的位置 | 每個位置都在 ledger 清單中，並逐一說明新 kind 是否影響；未列出的位置視為缺漏 | 自動：讀 diff 與 grep |
| TC-094 【機器可驗】 | 被釘住的既有測試 | 功能 | 計畫列出的被釘住測試 | 比對 diff 與跑測試 | `test_cleanup_confirm.py:121`、`:130`、`:658`、`test_pending_confirm_restart.py:268`（`PENDING_SECONDS == 600`）、`test_keep_submissions.py:215`、`test_byte_channel_a.py:233`、`test_cleanup_confirm.py:343` 未改且綠；其他必須同步改的既有測試只增不減（無刪除或放寬斷言、期望值只加 `publish_figure`） | 自動：讀 diff 與上列測試 |
| TC-095 【機器可驗】 | 專長守則 backend：錯誤與日誌 | 例外 | 觸發拒絕、逾時、寫入失敗各一次，並抓日誌 | 檢查回應與日誌 | 錯誤回應含原因與處理方式；日誌與回應不含 token、CSRF 值或其他密鑰；不露出堆疊、內部路徑、SQL | 自動：`test_publish_figure_confirm.py`（日誌與回應掃描） |
| TC-096 【機器可驗】 | 計畫「文件」 | 功能 | 實作完成後 | 讀 `docs/PLATFORM.md`、`docs/TESTING.md`、`CHANGELOG.md` | PLATFORM.md「工具數」由 22 改 23；寫明 publish_figure 是確認通道寫入工具（不是例外）、新 kind、無 job、儲存位置與 `index.json` 格式、`bundle_json` 保留與「刪圖不清稽核副本」、限制；TESTING.md 有手動步驟（呼叫、確認頁按「送出」、檔案寫入；含 script 的 SVG 被拒；不按等 10 分鐘＝不寫）；CHANGELOG 有條目 | 自動：讀文件 |
| TC-097 【機器可驗】 | 原話 5；作法 17 | 功能 | 實作完成後 | 檢查 `figures.py` 與依賴檔 | 不引入新依賴（無 PIL、defusedxml）；不呼叫 jobs、agent、ssh 或任何站台程式；圖只由 LLM 主動送入，平台不去站台找 | 自動：讀 diff 與 grep |

## 實機走通

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-098 【實機驗】 | 原話 3；完成標準手動走通 | 功能 | 本機起平台；MCP 客戶端已連上；使用者有一個分析 | 1. 以 MCP 客戶端呼叫 `publish_figure` 送兩張圖（PNG 附 code、params，另一張 SVG）。2. 取得確認頁網址，先不按，檢查圖庫資料夾。3. 登入後在確認頁按「送出」。4. 檢查圖庫資料夾與 `index.json`。5. 再送一批，不按，等超過 10 分鐘後嘗試核准 | 第 2 步圖庫資料夾沒有任何檔；第 4 步兩張圖與 code、params 檔、`index.json` 都寫入且 `packed` 為 false；第 5 步逾時後未寫入。操作者貼出每步的輸出到 ledger | 手動：`docs/TESTING.md`（本案新增手動步驟） |
