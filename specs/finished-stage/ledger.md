# 完成階段第一刀：來源紀錄＋交付包清單 progress ledger

- [x] RED：`platform/tests/test_web_finished.py`（fs01–fs13，對應 TC 見檔內註解）
- [x] GREEN：`platform/abf_platform/web_finished.py`（新）、`web_board.py`（裁決 4 三處＋階段列＋STYLE）、`web.py`（`board_page` 內讀取）
- [x] docs：`docs/TESTING.md`「完成階段」、`docs/PLATFORM.md`「Finished stage」

## 改寫的既有斷言（裁決 6）

- `platform/tests/test_web_board.py:541`（`test_tch21_stage_bodies`）：舊 = 失敗 run 的 finished 階段顯示「013b」佔位；新 = 顯示「這個 run 還沒到這個階段。」。理由：`PLACEHOLDER` 拿掉 `finished`，未成功的 run 本來就是 not_reached。

## 偏離／備註

- 計畫寫「`web_board.py` 只准三處」，實作另有三處必要的小改：(1) STYLE 加 `.prov`／`.pack` 規則（計畫寫 `static/*.css`，但本專案樣式表就是 `web_board.STYLE`）；(2) 階段列：未成功 run 的「完成」不再是連結（TC-046）；(3) `_run_page` 傳 `finished`／`user_name`。
- `render_finished(lang, run, provenance, outputs, user_name)`：不收 `t`／`now`（字串表在該模組自己的表裡，時間用 web_board 的 helper，函式內延遲 import 避免循環）。
- TC-012（不是從平台送出）：擁有者規則由 launches 列決定，沒有 launches 列的 run 看不到，所以測試用 monkeypatch `launch_prefill` 回 `found: False`。
