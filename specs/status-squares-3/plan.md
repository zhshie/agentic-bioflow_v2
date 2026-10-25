---
id: status-squares-3
title: 網頁的分析狀態一律「色塊＋詞」、只有三種（執行中／失敗／完成）；取代 ▶ ✓ ✗ 符號（#158 的新版重做）
tier: B
kinds: ui
lane: L7-web-redesign
base: v3
source: 維護者 2026-10-25 對 #158 的裁示
---

# status-squares-3

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/status-squares-3/plan.md`。**只處理本任務**。#158（舊版版面上的四狀態色塊）不合併，改在現在的新版上重做本任務。

## 目標
網頁上每個顯示「分析狀態」的地方，都用同一個樣子：一個小色塊緊接一個詞，而且只有三種：執行中、失敗、完成。不再出現 ▶ ✓ ✗ 這類符號。平台跟分析失去聯絡（lost）也顯示成「失敗」；點進那個分析後，頁面照既有內容說明實際情況。

## 維護者原話（verifier 出題用）
1. 「改成#158，但用3種就好，少掉待處理，failed的點進去之後再根據實際情況處理，不要符號用色塊」（2026-10-25）
2. 10-19（#158 計畫）：「好的按照你的建議」——色塊＋詞，英文已完成的分析一律叫 Done。

## 範圍：檔案
- `platform/abf_platform/web_board.py`（`SYMBOLS`、`_sym` 的所有呼叫點、狀態字串鍵、`STYLE` 中 `.sq` 與 `state-*` 色彩規則）
- 其他會顯示**分析狀態**的網頁模組（`web_results.py`、`web_finished.py`、`web_cost.py`、`web_launch.py` 若有）：只限把分析狀態符號換成色塊
- 釘住 ▶ ✓ ✗ 或「Succeeded／成功／失聯」狀態字樣的既有測試：只准換字串，ledger 逐條「舊→新＋理由」
- 新測試檔 `platform/tests/test_web_status_squares_3.py`
- `DESIGN.md`（States 一句：「分析狀態＝色塊＋詞，三種；顏色從不單獨表意」，其他不動）、`docs/TESTING.md`（一節手動步驟）

## 作法
- 已有元件：`_chip`（web_board.py:489-491）＝`<span class="chip state-X"><span class="sq"></span> 詞</span>`。所有分析狀態顯示（左欄清單、run 頁標題徽章、資訊表「狀態」列、右欄卡片、階段列、費用表狀態欄的「執行中」）都改用這個元件或同一套 `sq`＋`state-*` class。
- 三種狀態與用詞：running→執行中／Running；succeeded→完成／Done；failed 與 lost→失敗／Failed。其他未知值→灰色塊＋未知／Unknown。`chip_lost`「失聯／Lost」、`chip_succeeded`「成功」不再出現在畫面上。
- 刪掉 `SYMBOLS` 與 `_sym`（或改成不回符號）；畫面上的分析狀態不得再出現 ▶ ✓ ✗ ⏸ ⟳ ?。
- **不在範圍**（這些不是「分析狀態」，照舊）：引導式送出的步驟狀態（✓ ● ○）、設定頁運算環境狀態（✓ 可用／✗ 無法使用／— 未檢查）、費用表的「≈ 估算・帳單未到」、Nextflow 的任務計數字樣（完成／快取／失敗／中止…，僅「成功」改為「完成」以與狀態一致）、確認頁。
- lost 點進去：run 頁既有的失聯說明（通知與 failure 欄位）原樣保留，不新增文字。
- 零 JS、無 `style=`、單一樣式表（CSP 雜湊照既有測試更新）、英文版無中文、390 px 無橫捲；顏色從不單獨表意（色塊旁一定有詞）。

## 失敗先行測試
- `test_ss01_no_state_glyphs`：以 World seed 四個分析（running、succeeded、failed、lost），渲染 `/`、`/?run=<各>`（各階段）、`/usage`，zh 與 en：分析狀態區域內不出現 ▶ ✓ ✗ ⏸ ⟳；（引導式送出與設定頁的步驟／環境符號不受此限，測試只掃分析狀態元素與左欄、右欄、標題、資訊表）。
- `test_ss02_three_words_with_square`：四個分析各自顯示 `sq` 元素＋正確的詞；lost 顯示「失敗／Failed」；頁面不含「失聯」「Lost」「成功」「Succeeded」狀態字。
- `test_ss03_unknown_status_grey`：未知狀態→灰色 class＋未知／Unknown，無「?」。
- `test_ss04_lost_detail_kept`：lost 分析的 run 頁仍有既有的失聯說明文字。
- `test_ss05_constraints`：無 script、無 style=、CSP 雜湊、英文無中文。

## 完成標準
上列測試綠；全套綠（GREEN at HEAD，CI 綠才合）；改寫的既有斷言在 ledger 逐條列。截圖由 developer-agent 補（1440／390 × zh／en），交維護者看（他回好才合）。

## 不做
不改版面、不加「待處理」狀態、不改通知區（「待處理」等級字樣是通知等級，不是分析狀態，保留）、不改確認頁、不動 CSS 以外的樣式。

## 裁決
1. 已知只在本機環境紅、可接受：`tests/init_workspace_test.sh` 的「site side with no run area known fails clearly」。
2. 主開發的 cloud-cleanup-e 也會改 `web_board.py`（通知區）；合併衝突由 developer-agent 解，executor 不預先處理。
3. 測試請用 `abf-fast-suite <wt> --pytest tests/<file>.py` 跑單檔，不要直接在 /mnt/c 跑 pytest。

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
