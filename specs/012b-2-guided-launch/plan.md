---
id: 012b-2-guided-launch
title: 引導式送出收尾（第一片）：第 4 步「樣本表預覽與欄位角色」做成真的（取代「預覽與欄位角色（尚未開放）」）
tier: B
kinds: ui
risk: M
lane: L6-web
branch: feat/012b-2-guided-launch
base: v3
review: maintainer
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 2 第 146 行；DESIGN.md 畫面 5 第 4 步；specs/guided-launch-1／2／2b／2d（origin/v3）
---

# 012b-2-guided-launch

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/012b-2-guided-launch/plan.md`。**只處理第一片**，其餘列在「不做」。
> **2026-11-04 查 origin/v3（2735e423，已先 `git fetch`）——總表 012b-2 的大部分已經做完，不是從零開始：**
> - 已合併：`guided-launch-1`（七步編號引導，#210）、`guided-launch-2`（#240：參數表預檢、最新版本、流程圖、樣本表欄位、參數分組表）、`2b`（單一送出鍵、預設值直接在格子裡、紅星、正式用字）、`2c`、`2d`（重排成六步：分析名稱→運算環境→管線→樣本表→參數→確認；只列 `available` 的運算環境；版本只選一次；流程圖直接顯示；拿掉前置檢查）。`platform/abf_platform/schema.py` 與 `web_launch.py`（457 行）已在。`specs/guided-launch-2d/` 有 plan／test-case，沒有 ledger（2d 實作已在 v3：67480287、7720c224）。
> - **沒做完、仍寫著「（尚未開放）」的只剩**：(a) 第 3 步「搜尋全部 nf-core」（`web_board.py` `g_search`，:962／:993、:1138）；(b) 第 4 步「預覽與欄位角色」（`g_preview`，:963／:994、:1155）；(c) 逐步模式（012a 的旗標，012a 尚未合併）；(d) 版本政策「專案記住版本、不自動升、新版只提示」（PLAN 第 172 行）。
> - **(a) 不在本任務**：`memory/dev-plans/guided-launch-search.md` 已有計畫；注意 `dev-queue.json` 的 cleanup 清單把它記成「pr 284 merged」，但 #284 實際是 `web-wording-sweep`，v3 上 `web_board.py` 仍是「搜尋全部 nf-core（尚未開放）」、測試仍釘 `'type="search"' not in new`（test_web_guided_launch.py:168）。佇列記錄疑似誤植，請 developer-agent 核對（見回報）。
> - 本片選 (b)：不依賴未合併的 012a、不碰 `/settings`、不需要維護者新裁示（DESIGN.md 畫面 5 第 4 步已寫「column roles, preview, n/n paired」）。

## 目標
使用者在第 4 步選了樣本表，頁面就在選單下方直接顯示：樣本表的前幾列內容、每一欄在這個管線裡的角色（必填／選填／管線沒有這一欄）、缺哪些必填欄、以及已配對的樣本數（n/n）。送出前就看得出「樣本表欄位對不上管線」，不必等到執行失敗。送出的東西仍是同一個 `request_launch`。

## 維護者原話（verifier 出題用）
DESIGN.md「Maintainer's words」第 7 點，逐字：

> 「在送出的介面就要有之前abf-v2那些引導的事情，包括選擇pipline (之前設定的 or 新開的)、pipline的流程圖、pipline的參數等等。介面上不要有AI太口語化的回覆，要有制式化的通知呈現 ("樣本表少了 reverseReads 欄，AI 改不了。"這種不行)」

DESIGN.md 第 1 點：

> 「開啟一個專案、上傳rawdata之後，馬上就看到選pipline的階段，系統直接一個個引導使用者。」

guided-launch-2 維護者 10-23：

> 「先把功能做起來吧，以後再改美觀」（只用現有 class 與 DESIGN.md token）

guided-launch-2b 維護者 10-27：

> 「另外一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」

guided-launch-2d 維護者 10-28：

> 「分析名稱要放在第1個順位，前置檢查一律在設定那邊做好，沒做好就不跑……」（本片不得把「前置檢查」放回 /launch）

DESIGN.md 畫面 5 第 4 步（英文原文照抄進測試案例）：

> 4 Samplesheet (column roles, preview, n/n paired; with none uploaded: "No samplesheet has been uploaded. Please upload one first." and a link)

## 範圍：檔案
- `platform/abf_platform/web_launch.py`：新 `preview_block(t, lang, rows_info, files)`（純函式，仿 `samplesheet_block` :271）。
- `platform/abf_platform/web_board.py`：**只動兩處**——`STRINGS` 的 `g_preview`（zh :963、en :994）及新增 `g_pv_*` 字串；`render_launch` 第 4 步 :1155 那一行（`four += '<p class="off">…g_preview…'`）換成呼叫 `preview_block`。**不碰 `_report_cell`／結果頁摘要卡**（另一車道剛改完）、不碰 `SETTINGS` 常數與 `_frame`（012a 車道）。
- `platform/abf_platform/web.py`：**只動 `/launch` GET 的 guide 組裝**（:740–890 一帶，`launch_reads`、`guide = {...}`），把選到的樣本表預覽結果放進 `guide["preview"]`。**不碰 /settings 一帶（:1103–1330，012a 在改）、Route 表不加行**（不新增路由）。落地前 `git merge origin/v3`，衝突只保留雙方新增。
- `platform/abf_platform/actions/__init__.py`：新增唯讀動作 `preview_samplesheet(platform_path, caller, samplesheet, *, limit=5)`：用既有 `read_confined_samplesheet`（:1374，限呼叫者自己的上傳夾、不跟隨連結）讀位元組，回 `{"columns": [...], "rows": [[...]], "total": n, "truncated": bool}`；超過既有 `_MAX_SAMPLESHEET_TEXT`（1 MiB）、含 NUL、不是 UTF-8 → `build.Refusal` 一句白話。不新增 MCP 工具。
- `platform/tests/test_web_parity.py`：`WEB_ONLY` 補 `preview_samplesheet`（理由「網頁專用，樣本表預覽，無 MCP 工具」）；`OWED` 不動。
- `platform/tests/test_owner_guard.py`（:150 一帶，「呼叫者只能讀自己的資料」掃描）：新動作若被掃描要求列名，補一行；不放寬任何既有斷言。
- 新測試：`platform/tests/test_web_guided_launch_preview.py`。
- 被釘住、需同步修改預期的既有測試（只改預期，不刪案例，ledger 逐條列舊→新與理由）：
  - `platform/tests/test_web_guided_launch_2.py:398`（`assert "預覽與欄位角色（尚未開放）" in plain_text(four)`）。
  - `platform/tests/test_web_guided_launch_2b.py:616`（「no pipeline」狀態的 `預覽與欄位角色（尚未開放）` 與 `尚未選擇`）。
  - `platform/tests/test_web_guided_launch.py:363`（第 4 步 `尚未開放` 仍在——該行指的是別的字串時保留；若它依賴 g_preview 才改）。
  - **不變、必須仍綠**：test_web_guided_launch.py:168、test_web_guided_launch_2.py:210、_2b.py:658（皆釘「搜尋全部 nf-core（尚未開放）」，本片不碰 g_search）；test_web_guided_launch_2.py:455（第 5 步無「之後開放」）。
  - `platform/tests/test_web_wording_sweep.py`：不改、必須綠；所有新增中文字串先對照其禁字表（這個、一下、還沒有、用過的……）。
  - 全頁無 `<script`、無 `style=`、單一 `<style>`、`/launch` 的 CSP 不變（`img-src` 只因流程圖已放寬，維持 2d 的樣子）：沿用既有 launch 頁測試；**不新增 CSS**——只用既有 `.tbl`、`.muted`、`.off`、`.bad`、`.csym` class，免得頁面雜湊變動。若不得不加 CSS，只加進既有那一個 `<style>`，並在 ledger 說明雜湊重釘。
- 不碰：`web_settings.py`、`store.py`、`jobs.py`、`schema.py`（只讀其回傳）、`mcp_server.py`、站台代理、`static/*`、其他計畫檔。

## 作法
1. **資料**：選了樣本表（`values["samplesheet"]` 有值且在 `list_samplesheets` 的清單內）才呼叫 `preview_samplesheet`；沒選、清單為空 → 不預覽，第 4 步維持既有「尚未上傳樣本表，請先上傳。」與連結（DESIGN.md 原文，不改）。讀取失敗（Refusal）→ 頁內一句白話＋`✗`，不丟 500，送出鍵行為不變（預覽只是資訊，不阻擋送出）。
2. **預覽表**：最多 5 列、欄位照檔內順序；儲存格內容一律 `esc`；單格超過 60 字元截斷並加 `…`；表下一行「共 N 列」（`truncated` 時寫「僅顯示前 5 列」）。中文 `樣本表預覽`；英文 `Samplesheet preview`。
3. **欄位角色**：拿預覽的欄名對 `schema.samplesheet_columns` 已解析的 `si["columns"]`（`web_launch._part(files,"schema_input")`）：每個檔內欄位一列，角色三種，符號＋文字並用——`✓ 必填`／`✓ 選填`（管線有這欄）、`— 管線無此欄`（檔有、管線沒有）；管線必填而檔內沒有的欄另列 `✗ 缺少必填欄`。schema_input 還在讀（`loading`）→ 沿用 `reading(t, quiet)`；讀取錯誤 → 沿用 `_failure`；沒有 schema_input → 只顯示預覽表、不列角色，不報錯。
4. **n/n 配對**：只在 schema_input 同時有 `fastq_1` 與 `fastq_2` 欄，且檔內也有這兩欄時顯示 `已配對 n／N`（兩欄皆非空的列數／總列數；N 用 `total`，不是預覽的 5 列，因此 `preview_samplesheet` 要回逐列的配對計數 `paired`）；其他情況不顯示這句，不猜。
5. **用字**：全部制式化、無口語句（維護者第 7 點）。字串進 `STRINGS["zh"]`、`STRINGS["en"]` 兩邊；英文頁 `mid()` 不得含中文字。英文：`Samplesheet preview`、`Required`、`Optional`、`Not in this pipeline`、`Missing required column`、`Paired n/N`。
6. **不新增視覺決策**：不新顏色、不側邊色條；狀態不只靠顏色（符號＋文字＋既有 class）。
7. 動作層：`preview_samplesheet` 與 `read_confined_samplesheet` 同樣只准呼叫者自己的上傳夾（owner guard）；不接受任意路徑。

## 六項必填檢核（ui 計畫固定段）
1. 確認頁規則：預覽是唯讀資訊，不寫入、不花錢，不經確認頁；送出仍走既有 `POST /launch` → 確認頁。
2. 失敗狀態：檔讀不到／太大／不是 UTF-8／schema_input 讀取失敗 → 頁內一句白話（`✗`＋文字），其餘步驟與送出鍵不受影響。
3. 提示句位置：放在第 4 步區塊內、樣本表選單下方，不新增 flash。
4. 要改的舊測試：見「範圍：檔案」。
5. 手機寬度：預覽表用既有 `.tbl`（640px 以下已有卡片式 CSS，`data-label` 與否依既有寫法），不新增橫向捲動；`scripts/dev/ui_check.py` 存在就跑（1440／390 × zh／en）。
6. 空狀態：沒有樣本表 = 既有提示；樣本表只有標頭 = 「共 0 列」；沒有 schema_input = 只有預覽表。

## 失敗先行測試
新檔 `test_web_guided_launch_preview.py`，沿用 `test_web_guided_launch_2.py` 的登入、假站台、`steps()`／`plain_text()` 輔助。先寫、在未修的 v3 上會紅：
- `test_preview_replaces_not_yet_open`：選了樣本表 → 第 4 步含 `樣本表預覽` 與預覽表；不含 `預覽與欄位角色（尚未開放）`。
- `test_preview_first_five_rows_and_total`：8 列的 CSV → 表內 5 列、`共 8 列`＋`僅顯示前 5 列`。
- `test_column_roles_symbol_and_text`：每個欄位列同時有符號與文字（`✓ 必填`、`— 管線無此欄`）；管線必填而檔內缺 → `✗ 缺少必填欄`＋欄名。
- `test_paired_count_when_both_fastq_columns`：`已配對 3／4`；schema 無 fastq_2 或檔內無該欄 → 不出現這句。
- `test_cell_content_is_escaped`：儲存格含 `<script>` → 輸出為 `&lt;script&gt;`；整頁無 `<script`。
- `test_unreadable_sheet_says_so_and_send_still_works`：大於 1 MiB／含 NUL／非 UTF-8 → `✗` 一句白話、頁面 200、送出鍵仍在。
- `test_schema_loading_and_missing_cases`：schema_input 讀取中 → 顯示「讀取中」不列角色；無 schema_input → 只有預覽表。
- `test_no_sheet_selected_no_preview`：無樣本表 → 既有提示與 `/upload` 連結原樣。
- `test_only_own_uploads`：他人上傳夾的檔名、`../` 路徑 → 拒絕、不洩漏內容（同 `read_confined_samplesheet` 的拒絕）。
- `test_english`：`?lang=en` → 英文字詞；`mid()` 不含中文字。
- `test_no_script_no_inline_style_csp_unchanged`：無 `<script`、無 `style=`、單一 `<style>`、CSP 標頭同 2d。
- parity：`test_web_parity.py` 全套綠（`preview_samplesheet` 在 `WEB_ONLY`、`OWED` 不變）。
- 其他：g_search 相關三條既有斷言仍綠（證明本片沒動搜尋）。

## 完成標準（done when）
新測試全綠；上列既有測試改預期後綠；整套 `tests/run_all.sh --timeout 900` 綠（背景跑＋等待；已知環境紅見 README 通例）；`git diff --stat` 只有「範圍：檔案」列的檔，且 `web.py` 的 diff 不含 /settings 一帶、`web_board.py` 的 diff 不含 `_report_cell`／`SETTINGS`／`_frame`；ledger 貼 diff stat、逐條被改的既有斷言；PR 附 /launch 第 4 步（有預覽、缺必填欄、讀取失敗三種狀態，1440／390 × zh／en）截圖（B 級，維護者看）。

## 環境事實
- origin/v3＝2735e423（2026-11-04 `git fetch` 成功）。`web_board.render_launch` 第 4 步 :1141–1155；`web_launch.samplesheet_block` :271；`schema.samplesheet_columns` schema.py:124；`read_confined_samplesheet` actions/__init__.py:1374；`_MAX_SAMPLESHEET_TEXT`＝1 MiB（:1389 一帶）。
- 012a（`feat/012a-settings-personal`，worktree `wt/012a-settings-page`）正在改 `web.py` /settings 一帶、`web_board.py` 的 `SETTINGS`／`_frame`、`store.py`、`web_settings.py`；結果頁摘要卡（`web_board.py` `_report_cell`）剛改完。**本片與兩者的交集只剩 `web.py`、`web_board.py` 兩檔的不同區段**；兩邊都落地前 `git merge origin/v3`。
- 逐步模式（`step_mode`）旗標由 012a 提供，**未合併前本片不讀它**。
- PITFALLS 已查（`docs/PITFALLS.md`，origin/v3；`docs/solutions/` 不存在）：條目 Touches 欄裡的 `launch` 全是 `tw launch`／`prepare_launch.sh`／`commands/launch.md`（plugin 與 Seqera 路徑，例如 :196、:2522 `/launch` 指前置檢查腳本），沒有 `web.py`／`web_board.py`／`web_launch.py`／`test_web_*`／samplesheet 預覽的相符項：無相符項。

## 不做
- **第 3 步「搜尋全部 nf-core」**：另案 `guided-launch-search`（計畫已在 `memory/dev-plans/guided-launch-search.md`；先核對佇列誤記，見上）。
- **逐步模式的實際行為**（「每階段停等『下一步』」，handoff 2026-10-18 Q3）：等 012a 合併；且與 2b 維護者要求「只要確認送出鍵就好」可能衝突，需維護者先裁示怎麼呈現（見回報「需裁決」）。
- **版本政策**（專案記住版本、不自動升、新版只提示；PLAN 第 172 行）：另片。
- 不改樣本表的內容、不建立樣本表（012c-web／web-upload-page 範圍）；不做依 schema 建表。
- 不動第 1、2、3、5、6 步；不把「前置檢查」放回 /launch；不新增 MCP 工具、路由、CSP 變更；不改 DESIGN.md（第 4 步本來就寫了 column roles、preview、n/n paired）。

## 裁決（維護者；預設值，無異議 executor 照做）
A. **預覽列數**：預設 5 列。要改回答數字，重跑 `reuseContract:false`。
B. **預覽用新讀取動作還是頁內直接讀**：預設新增唯讀動作 `preview_samplesheet`（網頁專用，登進 `WEB_ONLY`）；若維護者要 MCP 也能預覽，改為 `OWED` 或新工具，範圍加 `mcp_server.py`。
C. **缺必填欄是否阻擋送出**：預設**不阻擋**，只標 `✗ 缺少必填欄`（預覽是資訊；既有送出前確認頁與管線自己的驗證仍會擋）。若要阻擋，送出鍵邏輯要改，測試加倍，風險升。
D. **012b-2 剩餘片的順序**：預設 (b) 本片 →（核對後）guided-launch-search →（012a 合併後）逐步模式行為 → 版本政策。

## 裁決（自動補，2026-11-04）

針對 verifier 退回的 planIssues 逐條裁定；與前文衝突時以本節為準。

1. **CLAUDE.md 沒有「For the executor and verifier」一節**：確認屬實，本片不改 CLAUDE.md。對應位置改指：測試指令見 CLAUDE.md「Running tests」（全套 `bash tests/run_all.sh`，單類 `bash tests/run_all.sh --only <字串>`；平台測試檔 `platform/tests/test_web_guided_launch_preview.py` 以該檔自己的方式單跑）；不變式與安全網見 `.specify/memory/constitution.md`；角色與閘門見 CLAUDE.md「Invariants, safety net, and how changes are made」與 `.claude/agents/verifier.md`／`executor.md`；手動驗收步驟見 `docs/TESTING.md`。「禁止執行的指令」以 constitution Safety Net 為準。注意：worktree 的 HEAD 落後，`platform/` 與 `scripts/dev/` 要先 `git merge origin/v3` 才看得到；verifier 與 executor 都要先合併再讀。
2. **沒選管線時第 4 步的預期**：`test_web_guided_launch_2b.py:616` 的 `"no pipeline"` 清單改為 `["尚未選擇", "分析名稱", "送出（前往確認頁）"]`，只刪 `預覽與欄位角色（尚未開放）`。`尚未選擇`（`g_s_unset`，web_board.py:973）屬第 5 步參數狀態，保留。第 4 步在沒選管線時：有樣本表清單就照常顯示選單；無 schema_input 故不列角色；有選樣本表才顯示預覽表，沒選則顯示下一條的提示句。
3. **有清單但沒選樣本表**：不得顯示「尚未上傳」。改顯示 `<p class="muted">`：zh `選定樣本表後顯示預覽。` en `The preview appears once a samplesheet is selected.`（字串 `g_pv_pick`）。「尚未上傳」只在清單為空時出現（沿用 v3 現行 `g_no_sheet`「尚無已上傳的樣本表，請先上傳。」與 `/upload` 連結；前文作法 1 的舊句作廢）。TC：清單有、未選 → 有 `g_pv_pick`、無預覽表、無 `g_no_sheet`、頁面 200。
4. **schema_input 讀取中**：預覽表照常顯示（預覽只依樣本表檔，與 schema 無關），其下顯示 `reading(t, quiet)` 的既有「讀取中」，不列角色、不列配對。
5. **`preview_samplesheet` 回傳鍵名**：定為 `{"columns": [...], "rows": [[...]], "total": n, "truncated": bool, "paired": n}`。「範圍：檔案」那個四鍵版本作廢。`paired` 恆存在；檔內欄位不含 fastq_1 與 fastq_2 時為 `None`，頁面端另依 schema 與檔內欄名決定是否顯示 `已配對`。
6. **手動／截圖 TC**：`scripts/dev/ui_check.py`、`tests/ui_check_script_test.sh`、`docs/TESTING.md` 在 origin/v3 都存在（合併後可見）。ui_check.py 改為「必跑」（1440／390 × zh／en＋axe）；`docs/TESTING.md` 加入範圍檔案，只新增第 4 步三種狀態（有預覽、缺必填欄、讀取失敗）的手動檢查條目，不改既有條目。合併前找不到腳本時 verifier 才標 UNVERIFIED 並寫明。
7. **確切字串**（進 `STRINGS` zh／en 兩邊，須過 `test_web_wording_sweep.py` 禁字表）：
   - 讀取失敗，各一句，前綴 `<span class="csym">✗</span>`，class `bad`，不含檔案內容、路徑、Traceback：太大 zh `樣本表超過 1 MiB，無法預覽。` en `The samplesheet is larger than 1 MiB and cannot be previewed.`；含 NUL 或非 UTF-8 zh `樣本表不是 UTF-8 文字檔，無法預覽。` en `The samplesheet is not a UTF-8 text file and cannot be previewed.`；讀不到或不屬於呼叫者 zh `無法讀取所選樣本表，請重新上傳。` en `The selected samplesheet cannot be read. Please upload it again.`
   - 列數：zh `共 N 列`、`僅顯示前 5 列`；en `N rows in total`（1 列時 `1 row in total`）、`Showing the first 5 rows`。
   - 讀取中沿用既有 `reading()` 字串，不新增。
   - 角色：zh `✓ 必填`、`✓ 選填`、`— 管線無此欄`、`✗ 缺少必填欄`、`已配對 n／N`；en `✓ Required`、`✓ Optional`、`— Not in this pipeline`、`✗ Missing required column`、`Paired n/N`。
8. **欄名 escape**：欄名（預覽表標頭與角色列）與儲存格同樣一律 `esc`；加 TC：標頭含 `<b>x</b>` 與 `"` 時輸出為 `&lt;b&gt;`／`&quot;`，整頁無 `<script`。
9. **完全空檔（0 位元組）**：視為讀取失敗，`✗` 一句：zh `樣本表是空的，沒有標頭列。` en `The samplesheet is empty and has no header row.`；不顯示預覽表與角色。「只有標頭」維持「共 0 列」。`preview_samplesheet` 對空檔拋 `Refusal`，頁面端轉成上句。
10. **單格截斷**：超過 60 字元者取前 60 字元再加 `…`（結果 61 字元）；恰 60 字元不截斷；截斷時原文後段不得出現在 HTML。以 Python 字元（code point）計，不以位元組計。

## 裁決 R（11-05 developer-agent，回應 BLOCKED(executor)）
1. **TC-308 用字**：合約改為「樣本表大於 1 MiB，無法預覽。」（措辭掃描禁「超」）；程式 `g_pv_big` 現行文字正確，不必改。已 commit a52d3685。
2. **plan.md「補充裁決」七行**已還原（commit 3f8255c4 誤刪），執行者不要再動 `specs/012b-2-guided-launch/plan.md`。
3. 兩處 pin 摘要測試更新（`test_k8s_launch.py:1437`、`test_web_settings_ce_mobile.py:101`）核准：新增動作與 web_board 字串必然改變摘要。
4. TC-315／TC-312／TC-604 的詮釋照 executor 報告，核准。
5. 不要再因這幾點 BLOCKED；直接跑全套交閱卷。

## 裁決 R2（11-05，developer-agent，回應閱卷 UNVERIFIED：0 FAIL／27 條缺斷言）
閱卷結論不是程式錯，是「test-case 標自動、新測試沒真的斷言」。**這輪要補測試，不改行為**（若補出斷言發現程式真有錯才改程式）：
- TC-015：GET /launch 不產生待確認請求（斷言待確認佇列沒增加）。
- TC-112：讀取失敗時顯示失敗訊息本身（斷言訊息文字）。
- TC-313：失敗句不含檔案內容與路徑（放入帶金絲雀字串的檔案，斷言回應不含它）。
- TC-403（連結檔）、406、407、408：直接呼叫 `preview_samplesheet` 的測試（符號連結、越界檔名、他人檔名、不存在檔）。
- TC-411：MCP 工具清單不變（比對現行工具名稱集合）。
- TC-511、512、513、514、517、518：英文版「無樣本表」、大於 1 MiB、非 UTF-8、讀不到。
- TC-605：比對 `<style>` 內容不只個數（與 base 相同）。
- TC-608、610、613、614、616、803、804：依 test-case.md 各自寫最小斷言；有哪條確實無法自動測，在 decisions.tsv 寫明原因，不要假裝補了。
- TC-701～705（畫面、axe）**不要做**，由我之後起應用程式拍截圖。
- TC-312 的 monkeypatch 太弱：改成真的建立一個讀不到的檔（例如把檔刪掉或權限不足，擇可在 WSL 穩定重現者）；做不到就保留並寫進 decisions.tsv。
補完跑全套再交閱卷；修正輪必須有新 commit。

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
