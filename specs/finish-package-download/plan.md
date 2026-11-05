---
id: finish-package-download
title: 完成頁加「下載結果檔」連結（沿用既有 25 MB 單檔下載）；「建交付包」動作留作下一刀
tier: B
kinds: backend, ui
risk: M
lane: L6-web-finished-download
branch: feat/finish-package-download
base: v3
source: 維護者 11-05 提問（見下）；memory/PLAN-abf-v3-replan-2026-10.md 第 149 行（013b）；platform/abf_platform/web_finished.py 檔頭「Nothing here downloads」；docs/ROADMAP.md 第 3 階段
---

# finish-package-download

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/finish-package-download/plan.md`。**只處理本任務這一刀**（見「不做」：`build_package` 動作是第二刀，風險 L，另開任務）。

## 目標
已成功的分析，在網頁「完成」階段的交付包區塊下，直接列出可下載的結果檔（走既有 `/run/file`，單檔 ≤ 25 MB），並把 MultiQC 報告連到下載；同事不必先切到「結果 → 輸出」分頁才找得到檔案。完成頁不新增動作、不新增站台工作、不新增路由、不寫任何檔案，所以不需要確認流程，也不需要 migration。「建出整包交付包再下載」仍標「之後開放」，因為後端 `scripts/build_package.sh` 需要下游分析產生的 `analysis/analysis.md`，網頁流程目前沒有（見「環境事實」第 4 點）。

## 維護者原話（verifier 出題用）
1. 11-05：「跑完到pipline都有在網站上顯示及時狀態嗎? 能在上面下載結果黨嗎?」「如果都可以，要把下游分析放下一個目標進度了」→ 完成頁要能直接點到結果檔下載（至少 MultiQC 與頂層檔案）；已存在的「結果 → 輸出」分頁下載行為不得退步。
2. DESIGN.md 畫面 10（逐字）：「**Finished stage**: delivery package (edited report, tables, MultiQC, figures, methods with versions, samplesheet), provenance, Download.」→ 完成頁仍是這六列交付包＋來源紀錄＋下載；本刀補上「結果檔下載」，整包下載列仍「之後開放」。
3. ROADMAP.md 第 3 階段驗收（逐字）：「A person with no AI tool completes setup → launch → running → results → downstream (in a Studio) → finished from the web alone」→ 完成頁不得需要 AI 工具或終端機才能拿到檔案。
4. DESIGN.md「用字」（10-27 裁示，沿用）：「一樣要注意中文的顯示不能口語」→ 新增的中文字串為正式書面語，且須通過 `test_web_wording_sweep.py`。

## 範圍：檔案
- `platform/abf_platform/web_finished.py`（STRINGS 兩種語言同鍵新增；`_package` 之後加一個 `_downloads` 區塊；檔頭說明「Nothing here downloads」改成「只產生指向既有 `/run/file` 的連結，本身不下載」）。
- `platform/tests/test_web_finished.py`（新增測試；既有案例只准增加斷言，不刪不放寬）。
- `docs/PLATFORM.md` 第 823 行附近（完成頁一段：「the download line, are "coming later"」改寫為「結果檔下載連結已有；整包下載仍 coming later」）。
- `docs/TESTING.md` 第 785～790 行附近（完成頁手動步驟加一步：點結果檔連結）。
- **不改**：`platform/abf_platform/web.py`、`web_board.py`（連結用 `board._url(lang, run_id, path="/run/file", sub=<相對路徑>)`，與 `web_board._report_cell` 同一做法，不複製邏輯）、`actions/`、`jobs.py`、`store.py`、`platform/abf_station/`、`.github/`。若實作發現非改不可，停下來回報，風險改判 L。

## 作法
決定（介面、鍵名、預期值；executor 以實際程式為準確認）：
1. **資料來源不變**：`render_finished(lang, run, provenance, outputs, user_name)` 的 `outputs` 就是 `run_outputs(enqueue=False)` 的答案，頁面不排任何列表（`test_fs07` 釘住）。`outputs["files"]` 每筆已帶 `name`、`type`、`download`（可下載檔的相對路徑，否則 None）、`too_large`。
2. 新增 `_downloads(t, lang, run, outputs, board)`，接在 `_package` 的 `<ul class="pack">…</ul>` 與 `<p class="off">下載交付包…</p>` 之間或之後（位置以不破壞 `pack_rows` 正則為準）：
   - 僅在 `ready` 且至少有一個可下載項時輸出；否則整塊不輸出（維持現況，不加空標題）。
   - 標題 `<p>` 字串：zh「下載結果檔」、en「Download result files」（鍵 `dl_head`）。
   - 項目：頂層 `type=="file"` 且 `download` 非 None 且非 `too_large` → `<li><a href="{board._url(lang, run_id, path='/run/file', sub=download)}">{name}</a> <span class="muted">{大小}</span></li>`；`too_large` → 純文字「{name} 大於 25 MB」（zh 鍵 `dl_big`：「大於 25 MB」，en「Over 25 MB」），不放連結；資料夾不列。大小格式沿用 `web_board` 既有的大小格式化函式（executor 查；沒有就用 KB／MB 一位小數，兩語言同格式）。
   - MultiQC：`has_qc`（頂層有名為 `multiqc` 的資料夾，與 `_package` 同一判斷）時加一項，連到 `multiqc/multiqc_report.html`，字樣沿用既有 STRINGS 的「MultiQC 報告」，規則與 `web_board._report_cell`（資料夾在頂層就連）一致。
   - 最多 20 項；超過時末尾一行 zh「其餘檔案請至「查看輸出」。」（鍵 `dl_more`；en 同義），「查看輸出」連結沿用既有的 `see_outputs` 連結。
   - **不得**改動 `_package` 六列的值：`test_fs06` 逐字釘住 `rows["結果表格"] == "✓ 在輸出資料夾"` 與 `rows["MultiQC 報告"] == "✓ 在輸出資料夾"`。新區塊的 `<li>` 用 `<li><a …>` 開頭，不得用 `<li><span>`（`pack_rows` 的正則會誤抓）。
3. 「下載交付包」那一行**原樣保留**（`<p class="off">下載交付包 <span class="later">之後開放</span></p>`，`test_fs08` 與 `test_fs10` 釘住），因為整包尚未可下載。
4. 不新增 `<form>`、`<button>`、內嵌 `style=`、`href="/download`（`test_fs01`、`test_fs08`、`test_fs10`、`test_fs11` 釘住）。連結是純 GET；真正讀檔仍由既有 `/run/file` 路由走 `run_file` → `read_run_file` 工作 → 站台代理，擁有者規則與 25 MB 上限都在那一層，這一刀不碰。
5. 英文頁不得出現中日韓字（`no_cjk`）；檔名為 ASCII 的測資下新區塊也須通過。
6. 錯誤路徑：點連結後的 `loading`／`error` 頁是既有 `/run/file` 的行為，不在本刀範圍；測試只驗證連結指向正確。
7. 不需要 migration：沒有資料表或欄位變動，沒有新的站台工作種類。

## 失敗先行測試（`platform/tests/test_web_finished.py`，沿用 `world`、`read_outputs`、`finish`、`ENTRIES` 這幾個輔助）
先寫、現在會紅（頁面上目前沒有任何 `/run/file` 連結）：
1. `test_fs12_finished_lists_download_links_for_top_level_files`：`read_outputs` 之後（`ENTRIES` 有頂層檔案），完成頁交付包區塊含 `href="/run/file?run=<rid>&amp;path=<檔名>"`，每個非資料夾、非過大的頂層檔一條；資料夾無連結；標題「下載結果檔」出現一次。
2. `test_fs13_multiqc_links_to_the_report_file`：頂層有 `multiqc` 資料夾 → 有連到 `multiqc/multiqc_report.html` 的連結；把 `multiqc` 換成同名「檔案」或移除 → 無該連結（對映 `test_fs06` 既有的負例）。
3. `test_fs14_too_large_file_is_text_not_a_link`：一個 `too_large=True` 的頂層檔 → 顯示「大於 25 MB」、其檔名沒有 `href`。
4. `test_fs15_no_block_before_outputs_are_read`：尚未讀取輸出、讀取失敗、空列表三種情況，頁面不含「下載結果檔」，且 `listings(w) == []`（仍不排列表）。
5. `test_fs16_other_users_run_gives_no_links`：bob 開 ann 的完成頁 → 與既有一致的 404，不含任何 `/run/file` 連結（跨使用者讀）；另用 bob 的 cookie 直接 `GET` ann 的 `/run/file?...` → 同一個 404／拒絕頁、`jobs` 表不增加 `read_run_file`（跨使用者寫的對應：不得替別人排站台工作）。
6. `test_fs17_more_than_twenty_files_are_capped`：25 個頂層檔 → 恰 20 個連結＋一行「其餘檔案請至「查看輸出」。」並連到輸出分頁。
7. `test_fs18_english_download_block`：`&lang=en` 下標題「Download result files」、「Over 25 MB」皆為英文且 `no_cjk`；連結帶 `lang=en`。
8. `test_fs19_download_block_changes_nothing_else`：同一頁的 `pack_rows` 六列值與 `test_fs06` 一致；`<form`、`<button`、`style=`、`href="/download` 皆無；`jobs` 的 `kind` 清單在 GET 前後相同。
9. 檢查既有 `test_fs07` 的原始碼斷言（`web_finished.py` 不得 import socket、urllib、subprocess 等）仍綠：新增程式不引入任何這類 import；`html`、`urllib.parse` 以外不加（`urllib` 開頭的 import 會被該正則擋下，連結一律用 `board._url`，不自己 `urllib.parse.quote`）。

## 完成標準（done when）
- 上列新測試先紅、實作後綠；`tests/run_all.sh --timeout 900` 全綠（環境紅依 README 通例）。
- 下列既有被釘住的測試**未被刪、未被放寬**（`git diff` 只新增）：
  - `platform/tests/test_web_finished.py`：`test_fs01`（六列、`class="steps"` 一個、`013b` 不出現）、`test_fs06`（交付包列值逐字）、`test_fs07`（不排列表、不 import 網路模組）、`test_fs08_download_is_coming_later`（第 221 行）、`test_fs10_english`（第 253 行「Download delivery package」「Coming later」、`<a` 存在、`href="/download` 不存在）、`test_fs11`。
  - `platform/tests/test_results_files.py` 第 588 行、`platform/tests/test_results_summary_loading.py` 第 19～45 行（結果頁報告格；本刀不碰 `web_board.py`，只確認仍綠）。
  - `platform/tests/test_web_wording_sweep.py`（新中文字串不得含禁用詞）、`test_web_parity.py`（不增動作、不增路由）。
  - 列出全部：`git -C <repo> grep -n -E "下載交付包|Download delivery|下載結果檔|之後開放|class=\"off\"|render_finished" origin/v3 -- platform/tests docs`。
- **動作數與路由數釘住的測試一律不變**（本刀不新增動作）：`test_k8s_launch.py::test_the_user_visible_actions_are_those_of_the_base`（`len(names) == 54` 與 digest、網頁路由 `len(got) == 30` 與 digest）、`test_actions_layer.py`（`ROUTES_V3`、`READ_NAMES`）、`test_owner_guard.py`、`test_web_parity.py`、MCP 的 `EXPECTED`。executor 在 ledger 貼上「這些測試未改、仍綠」。
- `docs/PLATFORM.md`、`docs/TESTING.md` 已同步；網頁畫面另附截圖（M 級）：完成頁（有連結、過大檔、英文各一張）。
- 專長守則檢查一行寫進報告。

## 環境事實
1. 動作層現有 54 個函式（`platform/abf_platform/actions/` 公開函式，釘在 `test_k8s_launch.py` 第 1435～1437 行）；**沒有 `build_package`**：`git grep build_package origin/v3 -- platform` 在程式裡無結果，只有 `docs/ROADMAP.md` 第 2 階段列為 009 的 MCP 寫入工具之一，與 `memory/PLAN-abf-v3-replan-2026-10.md` 第 149 行（013b）。MCP 工具現為 22 個（`test_mcp_contract_tools.py::EXPECTED_TOOLS`），不含 `build_package`、`run_downstream`。
2. 單檔下載現況：`actions.run_file`（`actions/__init__.py` 約 530 行）排一個 `read_run_file` 站台工作（`jobs.RUN_FILE_MAX_BYTES = 26214400`，站台 `platform/abf_station/readfile.py` 另寫同一數字），只讀 `<run folder>/results/` 下的一般檔；路徑不得含隱藏部分（以點開頭）。網頁路由 `/run/file`（`web_board.py` 約 1226 行有 `download_headers`）。結果頁已有同一做法：`web_board._report_cell`（約 650～661 行）資料夾在頂層就連到 `/run/file`。
3. `web_finished.py` 檔頭與 `docs/PLATFORM.md` 第 823 行都寫「不下載、下載列之後開放」；`test_fs08` 把「下載交付包」列釘為「之後開放」。
4. **`scripts/build_package.sh` 的前提**：參數是「專案資料夾」，沒有 `analysis/analysis.md` 即 `exit 2`（「no analysis plan … Run /downstream first」）；每筆計畫項目必須 `status: accepted`；輸出寫到 `<project>/submission/`（一個目錄，不是單一檔）；需要 `scripts/` 下的 `collect_provenance.py`、`methods_text.py`、`report_facts.py`、`cite.sh`、`package_crate.py` 與 Python。站台代理只拿得到 `on_site.sh`（`abf_station/cli.py` 第 95 行的 `--plugin-root`），沒有這些腳本與專案資料夾的概念；`readfile` 只能讀 `results/` 下 ≤ 25 MB 的單一檔案。因此「網頁上建出整包」現在做不出可用的東西，需要先有下游階段（畫面 9）。
5. 已查到的相關 PITFALLS：`docs/PITFALLS.md` 約第 2543～2548 行，「`read_run_file` 與 `list_site_files` 在站台共用連線過期時回答『路徑被拒』」——症狀：ssh 255 被當成輸入錯誤；檢查：連線失效必須回 `site_unreachable`，測試 `platform/tests/test_station_realpath_down.py`。本刀不改站台讀檔，但新連結會把更多使用者導向 `/run/file`，故不得改動該錯誤分流。其餘（web_finished、完成頁、動作數釘住）PITFALLS 已查，無相符項。
6. 測試輔助：`world(w)`、`read_outputs(w, rid, c, entries)`、`finish(w, id, entries=…)`、`listings(w)`、`pack_rows`、`section`、`no_cjk`（皆在 `test_web_finished.py` 開頭）。
7. 與其他網頁任務的檔案相交：本刀只動 `web_finished.py`／`test_web_finished.py`／兩份 docs；若 web-bugs-a／b 的範圍含這幾個檔案才會相交（本計畫作者未見其範圍，由 developer-agent 比對）。

## 不做
- **不做 `build_package` 動作層包裝**（第二刀，另開任務，風險 **L**）。理由與規格見下，不在本刀：
  - 需要新的站台工作種類 `build_package`：改 `platform/abf_platform/store.py`（`jobs.kind` 的 CHECK，約第 242 行，並附 migration，約第 411～415 行的升級函式）、`jobs.py`（`KINDS`、期限、`enqueue_build_package`、結果驗證）、`platform/abf_station/handlers.py`（`JOB_KINDS`、處理函式）與新的站台模組——碰 `platform/abf_station/` ⇒ **L**。
  - 需要確認流程（它在站台寫檔）：沿用 `confirm.py` 的 pending／`/c/<id>` 與 `actions.TERMINAL` 同一套；MCP 工具 `build_package` 隨動作一起加（ADR 0006：一個動作、四個入口、對等性測試）。
  - 動作數釘住的測試要一併重新釘住，同一個 commit：`test_k8s_launch.py` 的 `len(names) == 54` 與 digest（改為 55、重算 digest）；若加網頁確認路由，另改 `len(got) == 30` 與 digest；`test_mcp_contract_tools.py::EXPECTED_TOOLS`、`platform/tests/mcp/snapshots/tools.json`、`test_mcp_server_doc.py::EXPECTED`、`test_mcp_contract_writes.py`、`test_aws_ce.py`／`test_aws_launch.py`／`test_aws_upload.py`／`test_azure_ce.py`／`test_azure_launch.py`／`test_azure_upload.py` 內的工具名集合、`test_actions_layer.py`（`READ_NAMES`／寫入名單與 `ROUTES_V3`）、`test_owner_guard.py`、`test_web_parity.py`、`test_byte_channel_a.py`（`jobs.KINDS[-3:]`、CHECK 清單）、`test_byte_channel_b.py`（`handlers.JOB_KINDS`）、`tests/no_second_run_state_test.sh` 的允許清單。executor 以 `git grep -n -E "read_run_file|\b54\b|EXPECTED" origin/v3 -- platform/tests` 逐一找出。
  - **先決問題要維護者決定**：（a）整包要由哪裡的哪個專案資料夾建（網頁流程沒有 `analysis.md`）；（b）輸出須壓成單一檔並放進 `results/` 下不以點開頭的路徑，才走得進現有 ≤ 25 MB 的 `read_run_file`；（c）若超過 25 MB 怎麼辦。建議等「下游分析」（畫面 9，維護者 11-05 說下一個目標）落地、有 `analysis.md` 之後再做。
- 不新增網頁路由、不新增站台工作種類、不改 `platform/abf_station/`、`.github/`、`web.py`、`web_board.py`。
- 不改 25 MB 上限，不做多檔打包、不做整個資料夾下載。
- 不改結果頁（輸出分頁）既有的下載行為與字串。
- 不動 `dev-queue.json`。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
2. 合約規則：計畫未明寫的細節（大小格式、項目順序，以「站台給的順序」為準）由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值，條數 ≤ 20。
3. 本刀判定為 M（不碰 `platform/abf_station/`、`.github/`、憲章）；若 executor 發現必須改這些路徑，立刻停下回報，由 developer-agent 改判 L。
4. 落地前 `git merge origin/v3`；worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明。

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
