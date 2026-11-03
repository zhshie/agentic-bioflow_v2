---
id: results-summary-loading
title: 結果頁摘要卡：輸出列表讀取中時顯示「讀取中」，不再寫「之後開放」
tier: B
kinds: ui
lane: L33-web-resume-edit
branch: fix/results-summary-loading
base: v3
source: 前端 session 2026-11-01 在上線的平台實測發現；是 results-files（已合併）TC-026 的後續修正
---

# results-summary-loading

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/results-summary-loading/plan.md`。**只處理本任務**。

## 目標
同事開結果頁時，輸出資料夾列表還在向站台讀取，摘要卡下方的「報告」「MultiQC 報告」兩格現在寫「之後開放」，會讓人以為功能還沒做。改成「讀取中」（英文 `Reading`），讀完再變成下載連結或「此管線沒有產生」。只修這一個狀態，不改版面。

## 維護者原話（verifier 出題用）
無直接原話；依 results-files TC-026 字面行為。

results-files `specs/results-files/test-case.md` 第 58 行，逐字：

> | TC-026 | 作法 5（依字面）；六項必填 2 | 例外 | 輸出列表還在讀取，或讀取失敗 | 開結果階段 | 兩格沒有下載連結，也不寫「此管線沒有產生」（因為尚不知道有沒有） | 自動 |

對應計畫（results-files 作法 5）：有 `multiqc/`／`summary_report/` ＝下載連結；列表已讀到卻沒有該資料夾＝「此管線沒有產生」；「指標」「全部下載」不變（維持「之後開放」）。TC-026 沒有規定「讀取中」時要寫什麼字，也沒有說要寫「之後開放」；本計畫補上：讀取中寫「讀取中」。

## 範圍：檔案
- `platform/abf_platform/web_board.py`：只改 `_report_cell`（約 :639）及其兩個呼叫處所在的 `_results_body`（約 :708），不新增字串（用既有 `o_loading`＝「讀取中」／`Reading`）。
- 新測試：`platform/tests/test_results_summary_loading.py`。
- 被釘住、需要同步修改的既有測試（只改下面兩處的預期，不刪案例，ledger 逐條列）：`platform/tests/test_web_results_outputs.py`：`test_ro01_results_stage_has_cards_and_tabs`（:94，現釘四格皆「之後開放」）與 `test_ro10_english`（:346，英文版同理）。這兩條開的是「輸出分頁、第一次載入」＝讀取中，預期要改成「報告」「MultiQC 報告」兩格為讀取中、「指標」「全部下載」仍為「之後開放」。

**不需要 `platform/abf_platform/web.py`，也不需要 `platform/abf_platform/actions/__init__.py`。**`web_board.py` 要改，但只動 `_report_cell`／`_results_body` 兩個函式；另一任務（resume 編輯頁）同時改 `web.py`、`web_board.py`，所以與它的車道在 `web_board.py` 相交，落地前 `git merge origin/v3`，衝突只保留雙方新增。

已核對不受影響、不必改的既有測試：`test_results_files.py` 的 `test_tc025_*`（列表已讀到）、`test_tc026_unknown_means_no_link_and_no_claim`（斷言「無連結、無『此管線沒有產生』」，新行為仍成立，但新測試要補「讀取中」字樣）、`test_tc037_the_cards_keep_two_greyed_words_and_the_tabs_stay`（列表已讀到）；`test_web_board.py` :317、`test_web_upload.py` :1017 是左欄的「之後開放」，與本任務無關。

## 作法
**哪個狀態錯了、為什麼**：`_report_cell` 只看 `outputs["top"]`（第一層資料夾名）是否為 `None`，`None` 一律當成「之後開放」。但 `actions.run_outputs` 在三種情況都回 `top: None`：(a) 列表還在讀（`state == "loading"`）、(b) 讀取失敗或逾時（`state == "error"`）、(c) 沒有送出紀錄／不是自己的 run（`unavailable`）。(a) 才是「正在讀」，卻與 (b)(c) 顯示同一句，所以讀取中看到「之後開放」。

決定：
1. `_report_cell` 多收一個「是否讀取中」的判斷。讀取中＝同時成立：`outputs.get("state") == "loading"`、目前分頁是輸出分頁（`tab == "outputs"`）、`outputs.get("sub")` 為空（看的是 results 第一層，`top` 就是這次要讀的列表）。
2. 讀取中時該格輸出 `<span class="off">%s <span class="ostat state-running">⟳ 讀取中</span></span>`：標籤字（報告／MultiQC 報告）＋符號 ⟳＋文字 `t["o_loading"]`，沿用輸出分頁讀取中那一行已用的符號與 class（`state-running`），不新增 class、不用 inline style。不放連結。
3. 讀取失敗（`error`）、不可用（`unavailable`）維持現狀＝「之後開放」（TC-026 的「讀取失敗」那半不變）。
4. **為什麼限定輸出分頁、且在第一層**：其他分頁（執行資訊、任務、日誌）呼叫 `run_outputs(enqueue=False)`（web.py :499），沒有排工作，也不會自動更新；那裡回 `loading` 只是「還沒人去讀」，寫「讀取中」會永遠不變，是說謊。子資料夾頁（`sub` 非空）的 `top` 只取已快取的第一層、不排工作，同理不能寫讀取中。這兩種維持「之後開放」。
5. 中英：中文「讀取中」、英文 `Reading`（皆既有字串）；英文頁不得出現中文字。
6. 輸出分頁讀取中時頁面本來就每 15 秒自動更新（既有行為），不改；讀完後下一次更新自然變成連結或「此管線沒有產生」。

## 六項必填檢核（ui 計畫固定段）
1. 確認頁規則：純顯示，無寫入、無表單，不經確認頁。
2. 失敗狀態：讀取失敗、他人／無紀錄的 run 維持「之後開放」（不變，見作法 3）。
3. 提示句位置：兩格原位，就在摘要卡下方那一行，不新增段落。
4. 要改的舊測試：見「範圍：檔案」（ro01、ro10 兩處預期）。
5. 手機寬度：兩格是行內短字，與原本同寬度級，不新增橫向捲動。
6. 空狀態：不涉及（列表為空是另一個狀態，不變）。

## 失敗先行測試
新檔 `test_results_summary_loading.py`，沿用 `test_results_files.py` 的 `world`、`outputs_url`、`card_cells`、`plain`、`hrefs`、`finish_listing` 輔助（`from test_results_files import ...`，寫法照 `test_mcp_run_file_live_fixes.py` 開頭）。先寫、在未修的 `v3` 上會紅：
- `test_loading_cells_say_reading`：`world(w)`、直接開輸出分頁（列表剛排、未完成）→ `card_cells` 的「報告」「MultiQC 報告」兩格各含 `⟳` 與「讀取中」，不含「之後開放」，不含「此管線沒有產生」，沒有指向 `/run/file` 的連結（與 TC-026 一致）；「指標」「全部下載」兩格仍是 `<span class="off">… <span class="later">之後開放</span></span>`。
- `test_loading_cells_english`：同上加 `&lang=en` → 兩格含 `Reading`、不含 `Coming later`；「Metrics」「Download all」仍 `Coming later`；`mid()` 內不含中文字。
- `test_failed_listing_keeps_later_words`：開輸出分頁、`finish_listing(w, RESULTS, None, ok=False, error="not_found", message="no")`、再開 → 兩格仍是「之後開放」，不含「讀取中」、不含「此管線沒有產生」、無連結（保護作法 3）。
- `test_other_tabs_do_not_claim_reading`：`world(w)` 後直接開 `?run=<id>&stage=results&tab=tasks`（沒排過列表）→ 兩格是「之後開放」，不是「讀取中」；且 `listings(w) == []`（沒有因此排工作）。
- `test_subfolder_page_does_not_claim_reading`：開 `outputs_url(rid, "multiqc")`（第一層未讀）→ 兩格不含「讀取中」。
- `test_ready_listing_still_gives_links_or_none`：列表讀完（`top_entries()`）→ 兩格是下載連結；讀完但沒有那兩個資料夾 → 「此管線沒有產生」（TC-025 不退步）。
- 狀態表達：讀取中格的 HTML 同時含符號 `⟳` 與文字，不只靠 class；整頁無 `style=`。
既有測試同步：`test_ro01…`、`test_ro10_english` 如「範圍」所述改預期，這兩條在未修前仍綠，修後必須配合更新，所以在 ledger 註明「先改預期（紅）→ 再修（綠）」。

## 完成標準（done when）
新測試全綠；`test_ro01`、`test_ro10` 改後綠；整套 `tests/run_all.sh --timeout 900` 綠（背景跑＋等待）；`git diff --stat` 只有「範圍：檔案」列的檔；ledger 貼 diff stat 與逐條被改的既有斷言；PR 附結果頁讀取中狀態的截圖（B 級）。

## 環境事實
- 摘要卡兩格：`web_board._report_cell`（:639）由 `_results_body`（:708）呼叫；`top` 由 `actions.run_outputs`（`platform/abf_platform/actions/__init__.py` :418–500）填：開頭預設 `None`，只有「第一層列表 done 且 ok」才填成資料夾名單。
- `web.py` :494–511 `read_outputs`：只有輸出分頁 `enqueue=True`；其他分頁只看。
- 讀取中的既有文字與符號：`web_board._outputs_body` 的 `state == "loading"` 分支（`⟳` ＋ `o_loading`）。
- 2026-11-01 前端 session 在上線平台目擊；不需要真站台即可用假站台重現（`test_results_files.py` 的 `world`）。

## 不做
- 不改 `web.py`、`actions/__init__.py`、其他分頁、左欄、完成階段（`web_finished.py`）的任何字。
- 不給 `run_outputs` 新增「已排工作」旗標（因此其他分頁在列表其實正在讀時仍寫「之後開放」；若要「所有分頁都準確」，是另一個動 `actions` 的後續）。
- 不改讀取失敗的字、不新增字串、不動 STYLE／CSP。

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
