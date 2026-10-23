---
id: open-input-required
title: 畫布檢查：必填輸入沒接改成錯誤，可省略的仍是警告
tier: A
kinds: backend
lane: L5
base: v3
---

# open-input-required

> 本檔由 developer-agent 寫（2026-10-24），`/supervise` 複製進 worktree。**只處理本任務**。

## 目標
PR #176 讓模組目錄的每筆輸入記錄帶 `optional`（布林）。PR #178（017c）的 `validate.py` 目前對所有沒接的輸入一律給 `OPEN_INPUT` 警告。改成：輸入通道裡**只要有一筆記錄 `optional: false`**（也就是這個通道是必填）而沒接 → `OPEN_INPUT` 為 **error**；通道所有記錄都是 `optional: true` → 仍是 warning。入口節點（沒有任何進邊的節點）的必填輸入**仍是 warning**，訊息照舊說「送出時要由樣本表或參數供應」——因為入口的資料本來就從樣本表來。

## 維護者原話（verifier 出題用）
- 無原話；來源是 017c 計畫的待決事項與 PR #178 說明「unconnected inputs are warnings until the catalogue's optional is used to raise required ones to errors」。

## 範圍：檔案
- `platform/abf_platform/validate.py`
- `platform/tests/test_validate.py`
- `platform/tests/fixtures/validate/*.expected.json`（只在 severity 因本規則改變時更新；每一處變動寫進 ledger 並說明是哪條規則造成）
- `docs/PLATFORM.md`（Validation 小節一句）
- `specs/open-input-required/ledger.md`

## 失敗先行測試
- `test_required_open_input_on_a_non_entry_node_is_an_error`：合成目錄，節點 b 有進邊、但它的另一個必填輸入沒接 → OPEN_INPUT、severity error、`ok` 為 False。
- `test_optional_open_input_stays_a_warning`：同上但該通道所有記錄 optional true → warning、`ok` 不受影響。
- `test_entry_node_required_input_is_still_a_warning`：沒有任何進邊的節點，必填輸入沒接 → warning（訊息不變）。
- `test_real_catalogue_golden_still_ok`：017c 的黃金圖（fastqc → multiqc）在真目錄下 `ok` 仍為 True。
- 若 twins 等既有 expected 檔的 severity 因此改變：先在 ledger 手推一次為什麼變，再更新，不可用程式輸出回填。

## 完成標準
全套綠。

## 不做
- 不改其他 code 的規則；不改儲存格式；不改 017b。

## 裁決（2026-10-24，developer-agent）
1. 不需要 migration（只改判定，存的結果是同一張表、同一形狀）。

## 裁決二（2026-10-24 06:25，回應 verifier；取代「目標」裡的判定句）
2. **必填的判定只看非 meta 記錄**：通道裡 type 為 `map` 的記錄（meta）不算。其餘記錄中**有任一筆 `optional` 明確為 `false`** → 通道必填；其餘記錄全是 `optional: true`、或**沒有 `optional` 欄位**、或通道只有 meta 記錄 → 不算必填（維持 warning）。例：samtools_sort 輸入 1（meta2 false、fasta true、fai true）→ 非 meta 都 true → warning；輸入 2（index_format false）→ 必填。
3. 合成目錄沒有 optional 欄 ＝ 不算必填，所以 `bad_edges.expected.json` 預期不必改；若改了要在 ledger 手推說明。
4. 允許更新既有 `test_validate.py::test_open_inputs_are_warnings_never_errors_and_entry_nodes_say_so`（約 282 行）：改名並改成新規則（非入口＋必填 → error；可省略／入口 → warning）；`mod()` 輔助函式可加 optional 參數，預設不帶欄位。其他既有斷言不動。
5. 錯誤訊息沿用現有「少了一個輸入…」措辭（中英並列、節點、輸入號、輸入名），只改 severity。

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
