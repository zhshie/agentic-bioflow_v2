# 網頁 v2 第一批修正：標題列按鈕收進選單、失敗 run 階段條與目前步驟、左欄長名稱換行 progress ledger

- [x] 新測試 `platform/tests/test_web_fixes_1.py`（f01～f08＋f03b，TC 編號在註解）：RED 後 GREEN
- [x] 標題列 `<details class="menu">`（更多／More），三個 form 與「再啟動一次」連結原樣收進去（`web_board.py` `_run_page`）
- [x] failed／lost 的階段條「執行」格改「✗ 執行／✗ Run」，class `is-current is-failed`（succeeded 不變）
- [x] failed／lost 的第一張卡片改「停在／Stopped at」＝第一個失敗 task 名，沒有則 `—`
- [x] `.r2` 加 `overflow-wrap: anywhere`；CSS 另只加 `.menu > summary`（含 `min-height:44px`）與 `.steps .is-failed a`

## 改寫的既有斷言（舊 → 新）

1. `test_web_board.py::test_tcl07_to_l13_stage_strip`：failed／lost 種子的執行格 class 舊＝單一 `is-current` → 新＝`is-current` 加 `is-failed`（裁決 7）；running／succeeded 不變。
2. `test_web_running.py::test_r40_r44_title_and_cards`：標題列舊＝在 `<div class="head">` 內找三個 form／button → 新＝在 `<details class="menu"><summary>更多</summary>…</details>` 內找（仍是 3 form、3 button）。
3. 同測試：failed run 的第一張卡片舊＝「目前步驟／Current step」內容 `—` → 新＝「停在／Stopped at」內容 `FASTQC (sample2)`（該種子的第一個失敗 task）。
4. `test_web_board.py::test_tn10_n13_n17_n19_n20_nothing_beyond_the_plan`（計畫沒點名，但新選單讓它變紅，必須改；請閱卷者確認）：`<details` 總數須等於右欄 open details 數 → 新＝先扣掉 `<details class="menu">` 的數量，意圖（不多出別的折疊區）不變。
5. `test_web_board.py:703`、`:807`、`test_web_running.py:187` 的「整頁 3 顆按鈕」類斷言：整頁仍是 3 顆（在 details 內），不改也綠；:187 依 (2) 改了範圍。

## 備註

- `test_web_running.py::test_r30_r36_attention_card_uses_the_component` 有既存的偶發紅：它斷言右欄不含 "f1"，但按鈕 csrf 十六進位 token 有時剛好含 "f1"（檔內註解已知）。與本任務無關，重跑即綠。
- 全套已知環境紅（裁決 1）：`tests/init_workspace_test.sh` 「site side with no run area known fails clearly」。
