---
id: mcp-publish-figure
title: MCP 工具 publish_figure（第 1 片）：使用者的 LLM 提出圖＋程式碼＋參數，經既有確認通道由本人按一次才存進該分析的私有圖庫（確認通道、遷移、寫入、確認頁）
tier: B
slice: 1 of 2
kinds: ui, backend
risk: L
serves: S2-GALLERY
lane: L-mcp-publish-figure
branch: feat/mcp-publish-figure
base: v3
source: 維護者 2026-11-07 方向裁示、2026-11-12 選 B（見「裁決」段）；DESIGN.md 第 9 畫面（第 75 行，M2-016b）；docs/ROADMAP.md M2-016b；佇列決策 studios-figures-source；platform/abf_platform/{mcp_server.py,confirm.py,store.py,actions/__init__.py,web.py,web_finished.py}；憲法 .specify/memory/constitution.md 7.0.0 安全網第 191-195 行
---

# mcp-publish-figure

> 風險分級：**L**（動 `confirm.py` 與 `store.py` 的確認表 kind CHECK 遷移＝確認通道本身）。L 的要求：閱卷多交爆炸半徑證明，PASS 後再跑一次 Opus 對抗審。
> 若實作需要動 `platform/abf_station/`、`.github/`、`hooks/`、`.specify/memory/constitution.md`、`plugin.json`、`jobs.py` 的 kind 表，或新增資料表：立即停手回報（本案只改 `confirmations` 的 kind CHECK，不新增表、不動 `jobs` 表）。
> 本版依維護者 11-12 選 B 重寫：publish_figure **不得無確認寫入**，走既有確認通道；取代前一版「直接寫入、不走確認頁」的設計。

## 目標
新增 MCP 工具 `publish_figure(run_id, figures, request_id?, user_confirmed?)`：使用者自己串接的 LLM 與使用者討論後，提出一批「圖＋產生它的程式碼＋參數＋說明」。平台**先不寫檔**，建立一筆待確認申請（新 kind `publish_figure`）；使用者在既有確認通道（MCP 表單、確認頁 `/c/<rid>`、或聊天中本人自己的回答）按一次「送出」，圖才寫進該分析的**私有圖庫**（預設只有擁有者看得到，不進交付包）。（本片止於寫入私有圖庫；完成頁預覽、勾選、打包、刪除在第 2 片 `mcp-publish-figure-gallery`。）對使用者的意義：圖與統計怎麼畫、畫什麼，全由使用者與自己的 LLM 討論決定；AI 不能自己把東西寫進平台，平台也不替使用者挑圖。

## 維護者原話（verifier 出題用）
1. 「改成根據pipline的內容，透過使用者自己串接的LLM討論生成圖片或統計分析，直到使用者點選打包之後才往最後一關走」→ 測試：未按「打包」前，完成階段（交付包與 finish 所見）不含任何圖；按「打包」後才含所選的圖；平台不預寫任何腳本。
2. 「具體打包什麼都是使用者跟LLM討論」→ 測試：打包內容完全等於使用者勾選的集合（0 張、部分、全部三態）；平台無預設勾選（圖庫中的圖一律預設**未**勾選）；平台不替使用者挑圖。
3. 「目前我到底能不能夠用MCP請lab-agent跑完分析並顯示在網頁上? 這是我最基本的要求」（11-07 前一版）→ 本片測試：呼叫 `publish_figure`（回待確認申請）→ 本人在確認頁按「送出」→ 圖寫入私有圖庫；未按「送出」前圖庫仍為空。完成頁 `<img>` 預覽的測試屬第 2 片。
4. DESIGN.md 第 9 畫面（維護者 10-18）：「只要讓使用者能操作裡面的R，或是透過AI agent及時修蓋程式碼，然後能看得到圖片產生，最後要能夠打包圖片往下一步」→ 看得到圖、可打包往下一步；同段設計原文 “each with an ‘Include in package’ checkbox … the script goes into the package too” → 每張圖有勾選框，程式碼隨圖存放並在打包時一併進包。
5. 維護者 2026-11-05：Studio 跑在使用者自己的電腦、平台看不到圖（ADR 0010 Decided 第 3 點）→ 圖必須由使用者端的 LLM 主動送進平台，平台不去站台找。
6. 維護者 2026-10-27 用字裁示：「一樣要注意中文的顯示不能口語」→ 新增中文字串為正式書面語，英文版無中日韓字元。
7. 維護者 2026-11-12 回「好」＝選 B（見「裁決」段）→ 測試：未經確認的 publish_figure 不寫任何檔、不改圖庫；憲法不修；UI 措辭沿用 DESIGN.md 與既有確認頁。

## 範圍：檔案
只准改這些檔：
- `platform/abf_platform/confirm.py`：新增 kind `publish_figure` 的**無工作（無 job）**核准路徑：常數 `NO_JOB_KINDS = ("publish_figure",)`（`JOB_KIND` 字典**不動**，`jobs.CONFIRMED` 不動）；`approve()` 對此 kind 只把申請翻成 confirmed、記通道與時間，並在同一交易內呼叫由動作層傳入的寫檔函式（寫檔失敗＝該申請作廢並記原因，同既有「佇列拒絕」的處理），回 `(rid, None)`；`facts()` 加此 kind。其餘既有 kind 的行為逐位元不變。
- `platform/abf_platform/store.py`：`_CONFIRMATIONS_TABLE` 的 `kind CHECK` 加 `'publish_figure'`；`_confirmations_current` 改為 `'clean_work'` 與 `'publish_figure'` 都在才算新；沿用既有 `_migrate_confirmation_kinds` 重建流程（外鍵關閉、單一交易、複製、`foreign_key_check`、失敗回滾）。另加 `figures_root(platform_path, env)`，照 `uploads_root`：`ABF_PLATFORM_FIGURES`，否則 platform.db 旁的 `figures` 資料夾。**不新增資料表；`jobs` 表與其 CHECK 不動。**
- `platform/abf_platform/actions/figures.py`（新檔）：`request_publish_figure`（驗證、建申請）、供 `confirm.approve` 呼叫的寫檔函式、`list_figures(run, packed_only=False)`（唯讀，供測試與第 2 片使用）。純檔案儲存，不碰 jobs、不碰站台。`read_figure`、`delete_figure`、`pack_figures` 屬第 2 片。
- `platform/abf_platform/actions/__init__.py`：匯出；`_ask` 加可選參數（成功訊息、「核准後無 job」），**重用 `_ask`，不複製它**；`approve`、`request_facts` 對新 kind 可用。既有動作行為不變。
- `platform/abf_platform/mcp_server.py`：只註冊 `publish_figure` 一個新工具（帶 `request_id`、`user_confirmed`，照 `launch` 的 `_REQUEST_ID_DOC`；刪除與打包不開放給 MCP）。
- `platform/abf_platform/web.py`：**只動確認頁**：`state_page`／`confirm_post` 對新 kind 的標題、說明、按鈕、成功頁（無工作編號、連到該分析頁）；`_PLAIN` 兩語言各加此 kind 一行。不加路由、不動任何標頭或 CSP。
- `docs/PLATFORM.md`（工具數 22→23、publish_figure 走確認通道、新 kind、新路由、儲存位置與 index.json 格式、限制）、`docs/TESTING.md`（手動步驟）、`CHANGELOG.md`。
- 新測試：`platform/tests/test_publish_figure.py`、`platform/tests/test_publish_figure_confirm.py`（憲法要求的「新寫入工具自己的拒絕測試」，含確認頁測試）。
- 既有測試必須同步改（只增不減，逐條說明於 ledger）：
  - `platform/tests/mcp/test_mcp_contract_tools.py`：`EXPECTED_TOOLS` 加 `publish_figure`；`mcp/snapshots/tools.json` 以 `ABF_UPDATE_MCP_SNAPSHOT=1` 重生；描述長度上限不得超。
  - `platform/tests/mcp/test_mcp_contract_writes.py`：`WRITE_TOOLS` 加 `publish_figure`（以 readOnlyHint 推導並比對，必須相等）；「未確認一次呼叫零副作用」的參數化會自動涵蓋新工具，須綠。
  - `platform/tests/test_actions_layer.py`：27-29 行 `WRITE_NAMES` 加 `publish_figure`（154、160、631、634 行的動作對應：160 行以 `request_` + 名稱推導，故動作名為 `request_publish_figure`）；`test_pat.py:384`（22→23）。
  - `platform/tests/test_chat_tools.py`：`REQUESTS` 集合與聊天工具集——publish_figure 夾帶圖檔位元組，**不進瀏覽器聊天工具集**，測試加此排除斷言。
  - `platform/tests/test_cleanup_store.py:157`：新資料庫的 confirmations CHECK 宣告由 `["launch","cancel","clean_work"]` 改為加 `"publish_figure"`；`_CONF_COLS`（15 行）與「仍拒絕」的 kind 測試同步；新增「只有 clean_work 的舊庫遷移後多收 `publish_figure`、舊列與 jobs 外鍵不變」測試（418、444、485 行是更舊庫的遷移前狀態，預期不變，須綠，並加斷言：遷移後也收 `publish_figure`）。
  - 內嵌完整工具名清單者：`test_aws_ce.py`、`test_aws_launch.py`、`test_azure_ce.py`、`test_azure_launch.py`、`test_azure_upload.py`，先 `git grep -n '"read_run_file"' origin/v3 -- platform/tests` 逐檔判斷，只在完整清單加 `publish_figure`。
  - `platform/tests/test_web_confirm_plain.py`、`test_confirm_page.py`、`test_clean_page.py`：若斷言 `_PLAIN` 鍵集合或確認頁標題集合，只增新 kind，不改既有三 kind 的字句；先 `git grep -n "_PLAIN" origin/v3 -- platform/tests` 判斷。
- 被釘住、**不得改動也不得放寬**的測試：
  - `test_cleanup_confirm.py:121`（`confirm.JOB_KIND` 完全相等）、`:130`、`:658`、`test_pending_confirm_restart.py:268`（`PENDING_SECONDS == 600`）、`test_keep_submissions.py:215`（`KEEP_UNSENT_SECONDS`）、`test_byte_channel_a.py:233`、`test_cleanup_confirm.py:343`（`jobs.CONFIRMED`）→ 這些常數與字典本案一律不改。
  - `tests/constitution_6_test.sh:33`（逐字比對安全網「Every write tool of the platform…」那條 RULE2）→ **憲法不編輯**，此測試不得變紅。
  - `test_web_wording_sweep.py`、`test_web_parity.py`：確認頁新字串須通過。`web.py` 的 `_HEADERS`、`LAUNCH_HEADERS`、CSP 本片一律不改。
- 依賴與檔案衝突：本片不碰 `web_finished.py`、`web_board.py`，與 `web-result-viewer` 僅可能在 `web.py` 確認頁一帶相鄰；落地前 `git merge origin/v3`。

## 作法
1. **工具簽章**：`publish_figure(run_id: str, figures: list[{filename, content_base64, code?, params?, caption?}], request_id: str | None = None, user_confirmed: bool = False)`。**一次呼叫＝一筆確認申請，涵蓋整份圖清單**（不是每張圖一筆）；清單 1–10 張（`MAX_FIGURES_PER_CALL = 10`）。回 `{state: "pending"|"ok"|"refused", request_id, url, count, reason?}`；`pending` 時 `url` 為 `/c/<rid>`。標註 `read_only_hint=False`、`destructive_hint=False`、`idempotent_hint=True`、`open_world_hint=False`。說明文字須寫明：圖由使用者與 LLM 討論後以任何程式產生；**必須經本人確認才會寫入**，AI 自己不能確認、不得自行帶 `user_confirmed`；存入私有圖庫、不進交付包；只收 png、svg、jpg；同名覆蓋；上限；內容視為不受信任。
2. **走既有確認通道（維護者裁決選 B，不修憲法）**：與 `resume`／`relaunch` 同一個流程 `_ask`：MCP 表單（ELICITED）、確認頁（PAGE）、聊天中本人自己的回答（CHAT，需 `request_id` 與 `user_confirmed=true`，內容與種類雜湊須相符）。沒有人可按時（本機 stdio 無表單）回「無法確認」並不寫入。未確認＝不寫檔、不改 `index.json`、不重試。確認通道紀錄為 ELICITED／PAGE／CHAT，不會是 TERMINAL。
3. **申請內容與完整性**：`bundle = {"run_name", "run_id", "figures": [{"name","type","size","sha256","caption","code","params","content_base64"}]}`；`common.bundle_sha256(bundle)` 為雜湊，`approve` 驗證雜湊不符即作廢（既有行為）。`screen_text` 逐張列：檔名、類型、大小、說明、`code` 前 20 行與總行數、`params`、「覆蓋既有同名圖」標記（若 `index.json` 已有同名）。**確認頁不預覽圖像**：未確認的位元組不對外提供。核准後的圖要到第 2 片才在完成頁顯示；本片核准後只確認「已寫入」。
4. **驗證在建立申請之前**：擁有權、檔名、大小、魔術位元組、SVG、說明／code／params 長度全在 `request_publish_figure` 內檢查，任何一張不合格＝整批 `refused` 並說出是哪一張、什麼原因，**不建立申請列**（不佔用 10 筆額度）。寫檔函式在核准當下**重驗一次**（圖庫張數、檔名保留名），不合則該申請作廢並記原因。
5. **擁有權**：`run_id` 須為呼叫者自己的 run，與 `read_run_file` 同一個檢查；別人的與不存在的同一句回答。任何狀態皆可提出。確認者必須是提出者本人（`approve` 既有規則 `caller_user_id`）。圖庫**預設私有**：只有 run 擁有者能經 `/run/figure`、完成頁、`list_figures` 看到；沒有分享功能。
6. **檔名安全**：`^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$`，副檔名（小寫比對）只准 `.png`、`.svg`、`.jpg`、`.jpeg`；拒絕 `..`、`/`、`\`、NUL、空白、前導 `.`；保留名 `index.json`、`*.code.txt`、`*.params.txt` 與暫存名拒絕；同一批內不得重名；解析後路徑須在 `figures_root/<user>/<run_id>/` 內（縱深防禦）。
7. **大小與數量（逐項決定）**：（a）**整份申請序列化後的 `bundle_json` 上限 5 MiB**（`MAX_BUNDLE_BYTES = 5 * 1024 * 1024`，以 `len(json.dumps(bundle).encode())` 計；因 base64 膨脹，實際圖檔合計約 3.7 MB）；先用 `content_base64` 長度估算，超過即拒絕，訊息為「這次送入的圖合計超過 5 MB 上限（目前 X MB），請分次或縮小圖檔 (the figures together exceed the 5 MB limit; send fewer per call or smaller files)」；（b）每份清單 ≤ 10 張；（c）每個 run 圖庫 ≤ 30 張（`MAX_PER_RUN`，覆蓋同名不重複計數，已滿再送新名字則拒絕）；（d）`caption` ≤ 200 字元、`code` ≤ 100 KB（UTF-8，無 NUL）、`params` ≤ 10 KB（純文字，不解析）；（e）base64 以 `validate=True` 嚴格解碼。**既有確認額度原樣適用、不新增例外**：每位呼叫者同時最多 10 筆待確認（`MAX_OPEN_PENDING`，新 kind 落在「非 clean_work」那一組，計入；超過時回既有「未送出：…」訊息）；待確認 600 秒（`PENDING_SECONDS`）逾時即作廢、不寫；同一人於 60 秒以上剩餘時間內重複送出同內容沿用同一申請（既有 `create_pending` 去重）。逾時或作廢後須由 LLM 重新呼叫；核准成功後再送同內容＝再問一次（冪等覆蓋）。
8. **內容檢查（上傳內容視為不受信任）**：魔術位元組須與副檔名一致（PNG `\x89PNG\r\n\x1a\n`、JPEG `\xff\xd8\xff`）；SVG 須能以 UTF-8 解碼，且（不分大小寫）不含 `<script`、`<foreignObject`、`<!DOCTYPE`、`<!ENTITY`、`javascript:`、`on…=` 事件屬性、`<iframe`、`<embed`、`<object`、指向 `http(s)://` 之外部資源的 `href`／`src`；任一命中即拒絕並說原因，不改寫。平台**從不執行或解析成 HTML**：圖只在 `<img>` 載入；`code`、`params`、`caption` 一律當純文字，輸出時 `html.escape`，放在 `<pre>`／文字節點。
9. **儲存（檔案＋ index.json，不新增資料表）**：`figures_root/<user_id>/<run_id>/<name>` 與同資料夾 `index.json`，格式 `{"version":1,"figures":{"<name>":{"size","type","caption","code_file","params_file","created","packed":false,"packed_at":null,"request_id"}}}`；程式碼與參數另存 `<name>.code.txt`、`<name>.params.txt`。寫入先寫暫存檔再 `os.replace`（`index.json` 最後更新）；檔案 0600、資料夾 0700。`index.json` 損毀時視為空圖庫並回明確錯誤，不拋例外。同名覆蓋時**清除已打包旗標**。
10. **`bundle_json` 保留（沿用既有，不新創）**：待確認列與作廢列照既有 `KEEP_UNSENT_SECONDS`（7 天）後清空內容；**已確認列的 `bundle_json`（含圖的 base64）照既有規則保留到擁有者 `forget` 該分析**（`confirm.forget_content` 以 `run_name` 比對，須新增測試證明 publish_figure 列也被它清除，且清除後圖庫檔案不受影響）。因保留，才有 5 MiB 上限（作法 7a）。圖庫內刪圖**不會**清掉已確認列的 base64 副本（那是「本人當時同意了什麼」的稽核紀錄），PLATFORM.md 明寫。
15. **確認頁措辭（沿用既有，不新創；採用的選擇記進 ledger；與禁用字表衝突以禁用字表為準）**：標題「存入圖庫確認」／en "Confirm adding figures"；說明「以下為將存入圖庫的全部內容。確認無誤後，請按「送出」；按下後才會寫入圖庫。」／en 對應一句；按鈕沿用「送出」／"Send"；成功頁「已存入圖庫 N 張。」（無工作編號，連到該分析頁）；逾時、作廢兩句沿用既有確認頁寫法。符號與導向沿用 DESIGN.md 確認頁；DESIGN.md 未決之處寫進報告，不自創。
16. **憲法與安全網清單：不編輯（已讀憲法確認）**：`.specify/memory/constitution.md` 7.0.0 安全網第 191-195 行寫「Every write tool of the platform (**today** `launch`, `launch_pipeline`, `cancel`, `resume`, `relaunch` and `forget`) refuses until a person has answered on one of those four channels … **A new write tool joins this rule with its own refusal test before it ships.**」——括號是「今日」的例示，規則本身已涵蓋新寫入工具，且既有確認 kind `clean_work` 同樣不在括號內。故新 kind 只是另一種確認 kind，落在既有人工通道規則之下，**不新增例外、不改清單**；義務是附自己的拒絕測試（`test_publish_figure_confirm.py`）。該條被 `tests/constitution_6_test.sh:33` 逐字比對，編輯憲法反而會使它變紅，且憲法屬保護路徑。若 verifier 認為括號清單必須列入 `publish_figure`：那是需維護者明確同意的憲法修訂，不由本案決定，列為「要問維護者的事」。
17. **不新增依賴**（不引入 PIL、defusedxml）；不經 jobs、不經 agent、不接觸站台。
18. **文件**：PLATFORM.md「Twenty-two tools」改 23；寫明 publish_figure 是確認通道寫入工具（不是例外）、新 kind、`bundle_json` 保留、無 job、`index.json` 格式；TESTING.md 加手動步驟（呼叫 → 確認頁按「送出」→ 檔案寫入；含 script 的 SVG 被拒；不按送出等 10 分鐘＝不寫）。

## 失敗先行測試
`platform/tests/test_publish_figure_confirm.py`（憲法要求的拒絕測試，確認通道）：
- `test_unconfirmed_publish_writes_nothing`：呼叫後只有 `pending` 申請列；`figures_root` 無新檔、無 `index.json`；`list_figures` 為空。
- `test_model_cannot_confirm_itself`：只帶 `user_confirmed=true` 不帶 `request_id`、帶別人的 `request_id`、帶內容已改的 `request_id`（`changed`）、帶 token——皆拒且不寫。
- `test_confirm_through_each_channel_writes_exactly_the_requested_figures`：ELICITED、PAGE、CHAT 各一，寫入的檔與 `index.json` 恰等於申請內容；`confirmations` 列為 confirmed 且 `channel` 正確、無對應 `jobs` 列。
- `test_one_request_covers_the_whole_list`：3 張→1 筆申請、確認一次全寫入；清單中任一張不合格→整批拒、無申請列。
- `test_pending_limit_and_expiry_are_the_existing_ones`：第 11 筆待確認被拒（訊息同既有）；`clean_work` 不佔此額度；`PENDING_SECONDS` 後核准→`expired`、不寫；重複送同內容沿用同一申請。
- `test_expired_or_void_request_never_writes_even_if_retried`、`test_decline_in_form_voids_and_writes_nothing`。
- `test_write_failure_voids_the_request`：寫檔函式拋例外（如唯讀資料夾）→ 申請作廢、記原因、無殘檔；訊息與「輸入被拒」不同。
- `test_bundle_size_cap_and_message`：剛好 5 MiB 收、多 1 位元組拒，訊息含上限與目前大小；`test_confirmed_row_keeps_bundle_until_forget`：核准後 `bundle_json` 仍在；擁有者 `forget` 後被清空，圖庫檔案仍在。
- `test_confirmations_check_migration`：只有 clean_work 的舊庫開啟後 CHECK 含 `publish_figure`；舊列與 `jobs.confirmation_id` 外鍵完整；中途失敗回滾；新庫可插入此 kind，仍拒 `resume`、空字串；`jobs` 表 CHECK 前後相同。
- `test_existing_kinds_unchanged`：`JOB_KIND`、`jobs.CONFIRMED`、`approve()` 對 launch／cancel／clean_work 的回傳不變。
- `test_confirm_page_for_publish_figure`：zh／en 標題、說明、「送出」按鈕、CSRF；列出檔名、大小、說明、code 前 20 行；`<script>` 已逸出；成功頁無工作編號、有「已存入圖庫 N 張」；他人開啟 403；逾時 410；`_HEADERS` 與 `/c/<rid>` 的 CSP 不變；`CSS_SHA256` 不變。
- `test_constitution_untouched`：`.specify/memory/constitution.md` 與 `origin/v3` 相同。

`platform/tests/test_publish_figure.py`（驗證與儲存）：
- `test_valid_png_request_is_pending_not_stored`、`test_private_and_not_packed_after_confirm`（新圖 `packed=false`，`packed_only` 為空，另一帳號看不到）。
- `test_same_name_overwrites_resets_packed_and_counts_once`（確認文字含「覆蓋」標記）。
- `test_other_users_run_and_unknown_run_get_the_same_answer`。
- `test_bad_names_refused`（參數化）：`../x.png`、`a/b.png`、`a\\b.png`、`.hidden.png`、`x.exe`、`x.png.exe`、`x.html`、`index.json`、`a.code.txt`、空字串、81 字元、含空白、含 NUL、同批重名；檔案系統與 `confirmations` 皆無新增。
- `test_extension_must_match_magic_bytes`、`test_count_limits`（單次 11 張拒、圖庫第 31 張新名拒、覆蓋收）、`test_bad_base64_refused`、`test_caption_code_params_limits`。
- `test_svg_with_script_or_event_or_external_ref_refused` 與 `test_plain_svg_accepted`。
- `test_delete_figure_removes_files_and_pack_state` 與 `test_pack_figures_*` 屬第 2 片，不在此。`test_corrupt_index_json_is_empty_gallery_not_crash`、`test_nothing_written_outside_figures_root`（`sqlite_master` 除 CHECK 文字外前後相同）、`test_write_leaves_no_temp_files`。
- `test_publish_figure_goes_through_the_confirm_channel`（取代舊的「無確認頁」斷言）：`readOnlyHint` False、`destructiveHint` False；呼叫後 `confirmations` 有一列；不進聊天工具集；工具 23 個、描述未超限。

## 完成標準（done when）
- 新測試全綠；「必須同步改」的既有測試綠；「被釘住」的測試未改且綠（含 `tests/constitution_6_test.sh`）。
- 整個 `platform/tests` 套件綠（`test_tc047_tc051_other_docs_untouched` 單獨紅視同綠）。
- 手動走通（ledger 附輸出）：本機起平台，以 MCP 客戶端呼叫 `publish_figure` 送兩張圖（PNG 附 code、params，另一張 SVG）→ 取得確認頁網址 → 先不按，確認 `figures_root` 無檔 → 登入按「送出」→ 確認檔案與 `index.json` 寫入、`packed=false`；再送一批後等逾時，確認未寫入。
- 截圖（UI 守則）：只拍「確認頁（待確認）」「確認成功頁」，1440 與 390 寬 × zh／en；`scripts/ui_check.py` 若存在即跑，axe 無 serious／critical；不存在則用 Playwright 並標 UNVERIFIED。截圖不存進 Drive 工作區。完成頁圖庫畫面屬第 2 片。
- **L 級爆炸半徑證明（ledger）**：（a）`git diff --stat` 只含「範圍」所列的檔，不含 `platform/abf_station/`、`.github/`、`hooks/`、`.specify/memory/constitution.md`、`plugin.json`、`jobs.py`；（b）`confirm.py` 的 diff 只新增，既有 launch／cancel／clean_work 路徑的行逐行未改（附被改動的既有行清單，應為空或僅 `approve` 內新增分支）；（c）舊庫遷移前後 `confirmations`、`jobs` 列數與外鍵檢查輸出；（d）列出所有讀寫 `confirmations.kind` 的程式位置並逐一說明新 kind 是否影響；（e）`sqlite_master` 前後比對。
- ledger 另貼：新增常數、`index.json` 範例、確認頁採用的措辭與來源。

## 環境事實
- 現況（origin/v3）：MCP 22 個工具（PLATFORM.md 439 行）；確認 kind 為 `launch`、`cancel`、`clean_work`（`store.py:215-229`；`confirm.JOB_KIND` 把每個 kind 對到一種 job）；`approve()` 一定 `enqueue_confirmed` 排一個 job，本案的無 job 分支是新增；`_ask`（`actions/__init__.py` 約 1519 行）是 MCP 表單／確認頁／聊天三通道的共用函式；`POST /c/{rid}`（`web.py` 約 515 行）目前成功頁一律印工作編號。
- `confirmations` 表由 `_migrate_confirmation_kinds`（`store.py` 約 600 行）在 CHECK 過舊時重建；`_confirmations_current` 目前只看 `'clean_work'`。
- `read_run_file` 只回文字，二進位只給 `/run/file` 連結；完成頁「圖」列固定「之後開放」，整包下載也「之後開放」；`finish` 是 MCP prompt／技能（使用者端），平台沒有 `finish` 或 `build_package` 動作。
- 憲法 7.0.0（`.specify/memory/constitution.md` 第 29-51、191-200 行）：人工確認的四條通道＝終端機、MCP 表單、確認頁、聊天中本人自己的回答；寫入工具清單前綴 “today”；新寫入工具須附自己的拒絕測試。憲法屬保護路徑，本案不動。
- 決策背景：ADR 0010 Decided 第 3 點；佇列決策 `studios-figures-source`。**本案分兩片**：第 1 片＝本檔；第 2 片 `mcp-publish-figure-gallery`（完成頁圖庫、`/run/figure`、打包與刪除）依賴第 1 片。
- PITFALLS 已查（docs/PITFALLS.md；`docs/solutions/` 不存在）。針對 `confirm.py`、`store.py`、確認 kind、`platform.db` 遷移、`bundle_json`：PITFALLS 已查，無相符項。其他相符項：
  - 「`read_run_file` 與 `list_site_files` 在共用連線過期後誤答路徑被拒」（PITFALLS.md:2543-2548；症狀：第一步 ssh 失敗被當成輸入錯誤）→ 本案不經站台；但「輸入被拒」與「寫檔失敗／系統不可用」須分開回答，已列測試。
  - 「兩支腳本預設寫同一個 `analysis/figures`，後跑的蓋掉前一個」（PITFALLS.md:1550、1569-1572）→ 同名覆蓋是既定行為；確認頁明列「覆蓋既有同名圖」，覆蓋時清除已打包旗標。
- 風險備註：這是平台第一次持有使用者上傳位元組並對外服務，且第一次新增確認 kind 時不排 job。安全線＝確認通道（AI 不能自行確認）＋擁有權與私有預設＋檔名白名單＋魔術位元組＋SVG 拒絕清單＋`<img>` 載入＋`sandbox` CSP＋`attachment` 下載＋純文字逸出＋POST 的 CSRF，逐條有測試。磁碟：每 run 30 張、每份申請 ≤ 5 MiB 且已確認列保留到 `forget`；無跨 run 總量上限（後續切片）。

## 不做
- **裁決（維護者 11-07，寫於此以供閱卷）**：（1）本案**合併 M2-016b 圖片清單設計**（DESIGN.md 第 9 畫面約 75 行的 “Figures produced” 清單），以「私有圖庫＋勾選＋打包」取代其「即時列出 `analysis/figures/`（JS）」；（2）**作廢 `memory/dev-plans/studios-figures.md` 與本案矛盾之處**：該案「圖來自站台結果資料夾 `run_outputs`」「勾選只存查詢字串 `fig`」「完成頁只列檔名與下載連結、不內嵌預覽」「不宣稱已打包」均以本案為準；該案不得與本案同時進行，其餘未矛盾部分（Studio 區塊提示）由 developer-agent 於佇列處理，不在本案。
- 不修憲法、不新增憲法例外、不改安全網清單；不新增確認通道；不改 `jobs` 表、`jobs.CONFIRMED`、`confirm.JOB_KIND`。
- 不做整包壓縮下載（交付包「下載」仍「之後開放」）；不改 `finish` 的 MCP prompt／使用者端腳本。
- 不做 MCP 端刪圖或打包；不做圖的分享、跨 run 圖庫、重新排序、縮圖產生；不做確認頁的圖像預覽。
- 不做「依 pipeline 預先寫好 R／分析腳本」：圖與統計由使用者自己的 LLM 與使用者討論產生，平台不預寫腳本、不推薦分析。
- 不做每位使用者總量上限、不做自動過期（後續切片）；不做「核准後丟棄 `bundle_json` 內的圖位元組」（沿用既有保留規則，列為後續）。
- 不改 `platform/abf_station/`、站台協定、jobs 種類；不新增依賴；不改 CSS；不改 `/launch`、看板、設定、費用頁的 CSP。
- 不執行或解析上傳內容；不做 SVG 改寫式消毒（只拒絕）。

## 第 2 片（後續，另檔）
`mcp-publish-figure-gallery`：完成頁圖庫區塊（預覽、標籤、勾選、程式碼檢視）、`GET /run/figure`（含 CSP、`img-src` 只加在完成階段）、`POST /run/figures/pack`、`POST /run/figure/delete`（網頁專屬、僅限擁有者）、交付包「圖」列三態、`web_finished.py`／`web_board.py` 與其測試。依賴本片落地與 `web-result-viewer`。

## 要問維護者的事（只有維護者能答；不阻擋開工，預設如下）
1. 憲法安全網括號清單「today `launch`, … `forget`」是否要在下一次修憲時順手列入 `publish_figure`？預設：**不列**（規則已涵蓋新寫入工具，`clean_work` 先例亦未列）。
2. 圖庫的「刪除」與「打包」是否要再多一道獨立確認頁？預設：**不要**，以登入工作階段＋CSRF＋人按按鈕為確認（第 2 片作法）。
3. 已確認申請內的圖 base64 副本保留到 `forget`（沿用既有規則）是否可接受，或要在寫入成功後丟棄位元組只留雜湊？預設：**沿用既有保留**。

## 裁決（lead，2026-11-07，回應計畫撰寫者的四點）
1. 依賴計畫 id 是 `web-result-viewer`（尚未落地）。本案排在它之後，重用它的預覽路由；落地前 merge origin/v3，檔案衝突處理照「環境事實」。
2. finish 沒有平台動作屬實，接受以 `index.json` 的 `packed` 旗標＋`list_figures(packed_only=True)` 當介面，本次不改 finish。
3. 打包用網頁 POST＋CSRF；刪除只在網頁、MCP 不開放刪除與打包；forget 分析時不連動刪圖庫——三點接受（偏保守；維護者說過「使用者按打包才是確認」）。
4. 同名覆蓋會清除已打包旗標——接受。

## 裁決（lead，11-12，維護者回『好』＝選 B）
**publish_figure 不得無確認寫入，不修憲法 7.0.0。** 改走既有四條確認通道之一（沿用 mcp-chat-confirm 的做法）：圖表發布前產生待確認項，維護者在確認頁按一次才真正寫檔；未確認不寫、不重試。UI 措辭、符號、導向等未決問題：一律沿用 DESIGN.md 與既有確認頁的現成寫法（不新創），採用的選擇記進 ledger；有衝突以禁用字表為準。合約與計畫中與此矛盾的條目由 verifier 重出（fix-contract-regrade-push）。

## 裁決（dev-resolver，2026-11-12）
- 動作：`retry`（第 1／2 次裁決）。這次失敗是流程對不上，不是合約過期，也不是實作有問題。
- 證據 1（沒有可重新閱卷或推送的實作）：`git diff --stat origin/v3...HEAD` 只有 4 個檔，全在 `specs/mcp-publish-figure/`（`ledger.md`、`plan.md`、`test-case-overview.md`、`test-case.md`）；`ledger.md` 只有標題一行。`fix-contract-regrade-push` 的前提是「已有實作」，本案不成立。
- 證據 2（合約不是舊的）：`test-case.md` 只有一筆提交 `2d997282`（11-12 11:31:16，"test cases from verifier"），晚於計畫改寫的提交 `d9d9fe74`（11:26:01）；worktree 的 `plan.md` 與本檔內容相同。合約標題為「第 1 片：經確認通道存入私有圖庫」，共 98 條；`TC-001` 寫「回 `state: "pending"` … 圖庫資料夾沒有任何新檔」、`TC-089` 寫「`git diff origin/v3 -- .specify/memory/constitution.md` … diff 為空」，與 11-12 lead 裁決（選 B）一致。失敗原因所稱的「stale test-case.md」在 worktree 找不到對應。
- 下一輪要做的事（與前兩輪不同之處）：以**一般完整流程**執行，不走 `fix-contract-regrade-push`。沿用現有合約 `2d997282`，不整份重出、不刪除 `test-case.md`；executor 依本計畫第 1 片實作，verifier 依該合約閱卷，通過後照 L 級要求（爆炸半徑證明、對抗審）再推送。
- 若執行中發現某一條案例與本計畫或 lead 裁決矛盾：回報時必須寫出案例編號並引用計畫原文與案例原文，不得只寫「整份合約需重出」；不得放寬、刪除或跳過任何案例。
- 本裁決不變更計畫範圍；憲法、保護路徑、被釘住的測試一律照本檔原有規定不動。

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

## 裁決（lead，2026-11-12 深夜，驗收不通過與對抗審之後的修正輪）

驗收（新 context 的 verifier）：REJECT。對抗審：確認通道守住，另有 7 項。以下為修正輪範圍，每項先寫會失敗的測試。

F1 既有測試退步（v3 綠、本分支紅，共 10 條）要同步到綠，只增不減：`test_keep_submissions.py`（tc040、tc073、tc083、tc094/095/104）、`test_mcp.py::test_tc024`、`test_su_usd.py::test_tc033`、`test_mcp_canvas_read.py::test_registration`、`test_mcp_launch_pipeline.py`（`test_tool_count_and_no_extra_tools`、`test_no_schema_change`）、`test_guidance.py::test_tc501_six_read_only_tools_remain`。同步＝把新工具與新 kind 加進釘住的清單；不得刪或放寬任何斷言。
F2 補齊合約指定但不存在或太弱的測試（verifier 的 B 類清單）：TC-008、011、012、013、014、021、022、023（15 種檔名全測）、024、025、026、027、028、030、031、032、033、036、037、038、054（改成真的會失敗的斷言）、061、062、063、084、086、095、096。測試函式的 TC 註解要用已確認合約的編號。`test_constitution_untouched` 與 `test_page_headers_and_css_are_unchanged` 在拿不到 `origin/v3` 時不得靜默通過，要明確失敗或明確標示略過原因。
F3 ledger 補 TC-092（遷移前後列數與 `PRAGMA foreign_key_check` 的實際輸出）、TC-093（`confirmations.kind` 每個讀寫位置的清單）。補一條「遷移連跑兩次結果相同」的測試。
F4 資料庫膨脹（對抗審 1，改掉計畫第 10 條「base64 保留到 forget」）：`publish_figure` 的申請一旦 confirmed 且已寫入、或被作廢、或逾期，該列的 `content_base64` 要清掉，只留檔名、大小、sha256、說明；逾期列的清理在同一使用者下一次提出申請時順手做即可，不加背景工作。另加「每位使用者待確認的 `publish_figure` 內容總量上限」常數（20 MiB），超過就拒絕並說明。`test_confirmed_row_keeps_bundle_until_forget` 依此改寫為「confirmed 後內容已清、中繼資料還在、圖庫檔案不受影響」，這是 lead 點名的改動。重放同一個已完成的 `user_confirmed` 呼叫要回「已完成」，不是「內容不同」（對抗審 7）。
F5 覆蓋寫入失敗要能還原（對抗審 3）：寫入任何一步失敗時，被覆蓋的舊圖、舊程式碼檔、舊參數檔與 `index.json` 都回到寫入前的位元組，訊息才可以說「沒有任何圖被存入」。
F6 核准時重新檢查（對抗審 4）：`write_confirmed` 重做大小寫不分的檔名衝突檢查；實際會被取代的集合若與畫面上顯示的 `replaces` 不同，拒絕並說明，什麼都不寫。
F7 說明文字（對抗審 5、6）：caption 含換行或控制字元一律拒絕；caption、code、params 含孤立代理字元在申請時就明確拒絕。確認畫面每張圖多顯示 sha256 的前 12 碼。
F8 `docs/TESTING.md` 補「不按、等 10 分鐘就不寫」那一步。

不在本輪：SVG 內容過濾可被繞過（對抗審 2）由第 2 片送圖時的標頭把關（該片 TC-042、TC-043）；Windows 保留檔名；forget 時圖庫檔案保留（列入晨報請維護者看）。
限制不變：不碰 `.github/`、`hooks/`、憲法、`plugin.json`、`platform/abf_station/`、`jobs.py`、CSS。
