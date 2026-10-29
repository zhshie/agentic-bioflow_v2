# 設定頁「計算環境」表格在手機寬度改成一列一張卡片，欄位帶標籤 progress ledger

## 重釘雜湊（裁決 13、14）
證明：暫時刪掉 web_board.py 的 `@media (max-width:640px)` 四行（即新 STYLE 換回舊 STYLE），跑 `test_clean_page.py` 與 `test_web_settings_register.py`：test_clean_page 全過（五個頁面雜湊回到原值，只有 STYLE 不同）；register 只剩 ce 類別檢查失敗（因 `.ce` 規則被拿掉，預期）。隨後還原。
STYLE diff：只多一段 `@media (max-width:640px){.tbl.ce…}`（4 行，見 commit）。
只改常數值：test_clean_page.py :157-162（BASE_CONFIRM/EXPIRED/POST/BOARD/STYLE）、test_web_settings_register.py :18（BASE_STYLE_SHA）。
test_web_settings.py :201、:224：`"<td>" in r` -> `"<td" in r`。
