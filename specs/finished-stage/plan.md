---
id: finished-stage
title: 完成階段第一刀：成功的 run 在「完成」階段看到來源紀錄（管線、版本、參數、運算環境、送出時間）與交付包內容清單；下載與方法段落標之後開放
tier: B
kinds: ui
lane: L10-web-finished
base: v3
source: DESIGN.md v2 畫面 10；總表 013b；維護者 10-25「把開發速度拉到最大，今晚完成」（與 guided-launch-1 平行開工，故獨立模組）
---

# finished-stage

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/finished-stage/plan.md`。**只處理本任務**。前置：results-outputs（#191）已合併（`run_outputs` read 已在）。
> 013b 的第一部分。後續（finished-stage-2）做：真正的交付包下載、方法段落（含各工具版本與引用，需讀站台上的 `pipeline_info/software_versions.yml`）、可編輯報告、圖表。本任務**不新增 action、不讀站台檔案內容、不連網**。
> 與 `guided-launch-1`（L7）**同時**在做：那邊會改 `actions/__init__.py`、`mcp_server.py`、`/launch`。本任務刻意不碰那些檔案，渲染放新模組，降低合併衝突。
> 維護者 10-23：「先把功能做起來吧，以後再改美觀」——只用現有 class 與 DESIGN.md token。

## 目標
一個成功跑完的分析，點進「完成」階段，就能看到「這次是怎麼跑的」（哪條管線、哪個版本、改了哪些參數、在哪個運算環境、什麼時候送出）以及「交付包會有哪些東西、哪些已經有了」。這是把結果交給別人之前的最後一頁；今天這頁只有一行「013b」佔位。

## 維護者原話（verifier 出題用）
1. DESIGN.md 畫面 10（英文原文照抄進測試案例）：「**Finished stage**: delivery package (edited report, tables, MultiQC, figures, methods with versions, samplesheet), provenance, Download.」
2. 「下載、看結果甚麼的點進去看就好了。」（10-23，R16）
3. 「介面上不要有AI太口語化的回覆，要有制式化的通知呈現」（R7）
4. 「先把功能做起來吧，以後再改美觀」（10-23，R15）

## 範圍：檔案
- `platform/abf_platform/web_finished.py`（新檔：完成階段的全部渲染）
- `platform/abf_platform/web_board.py`（**只限裁決 4 列的三處**）
- `platform/abf_platform/web.py`（只在 `board_page` 裡：stage=finished 且 run 成功時，多讀 `actions.launch_prefill` 與 `actions.run_outputs(..., enqueue=False)` 並傳給 `render_board`；不加新路由）
- `platform/abf_platform/static/*.css`（只限裁決 5）
- `platform/tests/test_web_finished.py`（新檔）
- `platform/tests/test_web_board.py`、`platform/tests/test_web_v2_skeleton.py`（只限裁決 6 點名的斷言）
- `docs/TESTING.md`（新增一節「完成階段」手動步驟：390 px 無橫捲、Tab 鍵焦點外框、成功 run 點進完成階段）
- `docs/PLATFORM.md`（一段：完成階段的每一列從哪裡讀）

## 作法
**頁面**＝`?run=<id>&stage=finished`。
- 成功（`succeeded`）的 run：完成階段可以點進去（不再顯示「這個 run 還沒到這個階段。」，也不再顯示「013b」佔位）。
- 其他狀態的 run：維持「這個 run 還沒到這個階段。」。
- 步驟列與上一階段／下一階段連結沿用現有元件。

**區塊一：來源紀錄**（標題「來源紀錄」／英文「Provenance」，定義表 `<dl>`）：
| 列 | 中文標籤 | 英文 | 來源 |
|---|---|---|---|
| 管線 | 管線 | Pipeline | `launch_prefill(...)["pipeline"]` |
| 版本 | 版本 | Revision | `launch_prefill(...)["revision"]` |
| 參數 | 改過的參數 | Changed parameters | `launch_prefill(...)["params"]`，每行 `名稱: 值`（等寬字）；空 → 「— 全部用預設值」 |
| 運算環境 | 運算環境 | Compute environment | `launch_prefill(...)["ce_name"]` |
| 送出時間 | 送出時間 | Launched | `launch_prefill(...)["launched_at"]`，格式同頁面其他時間 |
| 完成時間 | 完成時間 | Finished | `get_run` 的 `ended_at` |
| 送出者 | 送出者 | Launched by | 登入者名稱（擁有者規則：只有本人看得到自己的 run） |
| 樣本表 | 樣本表 | Samplesheet | 灰字「之後開放」（見「待問」1） |

`launch_prefill` 的三種結果 → 三種狀態（符號＋文字＋樣式）：
- `kept: True` → 上表照填；
- `found: True, kept: False`（遺忘或已清理）→ 只填送出時間與完成時間，其餘列「— 內容已不保留」，表上方制式通知「這次送出的內容已不保留。」；
- `found: False`（不是從平台送出的 run）→ 整個來源紀錄只顯示「— 不是從平台送出的分析，沒有來源紀錄。」。

**區塊二：交付包內容**（標題「交付包」／「Delivery package」）：固定六列清單，順序與 DESIGN.md 一致，每列一個狀態：
| 項目 | 中文 | 英文 | 狀態規則 |
|---|---|---|---|
| 報告 | 報告 | Report | 永遠「之後開放」 |
| 表格 | 結果表格 | Tables | `run_outputs` 為 `ready` 且有檔案 → 「✓ 在輸出資料夾」；`ready` 但空 → 「— 沒有檔案」；其他 → 「— 尚未讀取輸出」（附連結到結果階段的「輸出」分頁） |
| MultiQC | MultiQC 報告 | MultiQC report | `run_outputs` 為 `ready` 且有名為 `multiqc` 的資料夾 → 「✓ 在輸出資料夾」；`ready` 但沒有 → 「— 這次沒有產生」；其他 → 「— 尚未讀取輸出」 |
| 圖 | 圖 | Figures | 永遠「之後開放」（來自下游階段） |
| 方法 | 方法段落（含版本） | Methods with versions | 永遠「之後開放」 |
| 樣本表 | 樣本表 | Samplesheet | 永遠「之後開放」 |

- `run_outputs` 在本頁一律用 `enqueue=False`（只看、不向站台送新的列表工作）；所以沒讀過輸出時顯示「尚未讀取輸出」＋連結，不自動排工作。
- 清單下方：「下載交付包」灰字「之後開放」（不是連結、不是按鈕）。

**不能放掉的限制**：零 JavaScript、無 `style=`、單一樣式表（CSP 雜湊）、15 秒 refresh、每人只看自己的 run、390 px 無橫向捲動（參數值與長名稱在欄內換行）、英文版每個字都有、制式通知（不口語、不用「我」「你可以試試」）。既有 `test_web_actions.py` 的 tc040、tc046–048、tc051、tc060、tc063 全部要繼續綠。

## 失敗先行測試
`platform/tests/test_web_finished.py`（用 `test_web_results_outputs.py` 的 `world`／`launch_to`／`finish`／`listings` 一類種子；必要時自己寫一份有 confirmations bundle 的 launch 種子）：
- `test_fs01_succeeded_run_opens_finished_stage`：成功 run 的 `stage=finished` 有「來源紀錄」與「交付包」兩個區塊、沒有「013b」、沒有「還沒到這個階段」。
- `test_fs02_other_states_not_reached`：running／failed／lost 的 run → 「這個 run 還沒到這個階段。」，不呼叫 `launch_prefill`。
- `test_fs03_provenance_kept`：管線、版本、參數（多行、等寬）、運算環境、送出時間、完成時間、送出者都在；參數空 → 「全部用預設值」。
- `test_fs04_provenance_not_kept`：遺忘後 → 制式通知＋其餘列「內容已不保留」。
- `test_fs05_not_from_platform`：沒有 launch 紀錄 → 「不是從平台送出的分析，沒有來源紀錄。」。
- `test_fs06_package_rows_follow_outputs`：`run_outputs` ready＋有 multiqc 資料夾 → 表格 ✓、MultiQC ✓；ready 沒 multiqc → 「這次沒有產生」；ready 空 → 「沒有檔案」；沒讀過 → 「尚未讀取輸出」＋連結到 `stage=results&tab=outputs`。
- `test_fs07_finished_page_never_queues_a_listing`：GET 完成階段任意次 → jobs 表沒有新的 `list_site_files`。
- `test_fs08_download_is_coming_later`：「下載交付包」＋「之後開放」，頁面沒有任何 `href="/download` 也沒有新的 `<form`。
- `test_fs09_owner_rule`：bob 用 ann 的 run id → 404，不呼叫 `launch_prefill`。
- `test_fs10_english`（`?lang=en` 沒有中文字、所有標籤英文）、`test_fs11_constraints_hold`（無 `<script`、無 `style=`、CSP 雜湊相符、有 15 秒 refresh、無口語句）。
- `test_fs12_web_board_touches_are_minimal`：`web_board.py` 只 import `web_finished` 一次，`PLACEHOLDER` 不再有 `finished`。

## 完成標準（done when）
上列測試綠；全套綠（環境紅見裁決 1）；改寫的既有斷言在 ledger 逐條「舊→新＋理由」。截圖由 developer-agent 補（1440／390 × zh／en），developer-agent 驗過後自己合併（10-24 維護者規則）。

## 環境事實
- 階段：`web_board.py:18` `STAGES = ("launch", "running", "results", "downstream", "finished")`；`:19` `PLACEHOLDER = {"launch": "012b", "downstream": "016", "finished": "013b"}`；`_stage_card`（`:417`）在 `stage in PLACEHOLDER` 時顯示佔位、`stage_of(run["status"]) != stage` 時顯示 `not_reached`。`render_board`（`:706`）已有 `outputs=` 參數（results-outputs 加的）。行號以 origin/v3 為準，executor 先自己確認。
- `web.py::board_page`（約 `:374`）：成功 run 且 stage=results 時呼叫 `read_outputs`；本任務仿照它加 stage=finished 的分支。
- `actions.launch_prefill(platform_path, run_name, *, caller)`（`actions/__init__.py:191`）回 `{"found", "kept", "launched_at", "pipeline", "revision", "ce_name", "params"}`；明寫「the samples are never part of it」，所以樣本表不從它拿。
- `actions.run_outputs(index_path, platform_path, run_id, *, caller, relist=False, enqueue=True)`（`:289`）；`enqueue=False` 只看不送工作。
- `actions.get_run` 的 view 有 `name`、`status`、`started_at`、`ended_at`、`tasks`、`project`。
- 方法段落與工具版本：plugin 端 `scripts/methods_text.py`、`scripts/collect_provenance.py`、`scripts/build_package.sh` 會讀結果資料夾裡的檔案並連網；平台端沒有對應的 read。本任務不搬它們。
- bundle 裡的 `samplesheet` 是解析後的整份列資料（`platform/abf_launch/build.py:135` 起），不是檔名。

## 不做
- 不做下載、不做打包、不讀站台檔案內容、不連網、不新增 action 或 MCP tool、不新增資料表或欄位。
- 不改 `actions/__init__.py`、`mcp_server.py`、`/launch`、確認頁、右欄、站台程式。
- 不改步驟列的「下游」階段（016）。

## 裁決
1. 已知環境紅 `tests/init_workspace_test.sh`「site side with no run area known fails clearly」（桌機 WSL `/work` 權限，CI 綠、base 也紅）不算本任務的紅。
2. 渲染全部放在新模組 `platform/abf_platform/web_finished.py`，對外一個函式（建議 `render_finished(t, lang, run, provenance, outputs, user_name, now)`，回 HTML 字串）；翻譯字串也放在該模組自己的表裡（中英各一套），不加進 `web_board.py` 的大字串表。
3. 不新增 action：只用既有的 `launch_prefill`、`run_outputs(enqueue=False)`、`get_run`。
4. `web_board.py` 只准三處改動：(a) `PLACEHOLDER` 拿掉 `finished`；(b) `_stage_card` 在 stage=="finished" 且 run 成功時呼叫 `web_finished.render_finished(...)`，其他狀態維持 `not_reached`；(c) `render_board` 加一個關鍵字參數（建議 `finished=None`）把 web.py 讀到的 provenance 往下傳。其他改動 → BLOCKED。
5. 可新增的 CSS 只限：`<dl>` 來源紀錄的欄寬與換行（`overflow-wrap:anywhere`）、交付包清單的狀態欄。沿用既有顏色與間距 token，不得新增數值。
6. 可改寫的既有斷言：只限斷言「finished 階段顯示 013b 佔位／`PLACEHOLDER` 含 finished／成功 run 的 finished 階段是 not_reached」的那幾條；executor 先列 file:line 寫進 ledger 再改。其他既有斷言變紅 → BLOCKED。
7. 若 executor 發現 `guided-launch-1` 已先合併到 v3、造成 `web.py`／`web_board.py` 衝突：以 v3 為準 rebase，保留雙方行為；不得回退對方的改動。

8. （developer-agent 10-25）樣本表那列這次顯示「之後開放」，不改 `launch_prefill`。
9. （developer-agent 10-25）成功的 run 在階段列上「完成」改成可點的連結（`?run=&stage=finished`）；這是 `web_board.py` 允許的第四處改動，其他未成功的 run 維持「之後」。

## 待問（不阻擋）
1. 樣本表要不要出現在來源紀錄：bundle 有整份樣本表內容，但 `launch_prefill` 刻意不回樣本。要顯示（例：列數與欄位名）需要改 action，留給第二刀並問維護者。

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
