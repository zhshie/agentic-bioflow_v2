# 設定頁「計算環境」表格在手機寬度改成一列一張卡片，欄位帶標籤 progress ledger

## 重釘雜湊（裁決 13、14）
證明：暫時刪掉 web_board.py 的 `@media (max-width:640px)` 四行（即新 STYLE 換回舊 STYLE），跑 `test_clean_page.py` 與 `test_web_settings_register.py`：test_clean_page 全過（五個頁面雜湊回到原值，只有 STYLE 不同）；register 只剩 ce 類別檢查失敗（因 `.ce` 規則被拿掉，預期）。隨後還原。
STYLE diff：只多一段 `@media (max-width:640px){.tbl.ce…}`（4 行，見 commit）。
只改常數值：test_clean_page.py :157-162（BASE_CONFIRM/EXPIRED/POST/BOARD/STYLE）、test_web_settings_register.py :18（BASE_STYLE_SHA）。
test_web_settings.py :201、:224：`"<td>" in r` -> `"<td" in r`。

## 截圖與溢出檢查（TC-009、TC-023）
指令：`scripts/dev/check_settings_mobile.py`（見 docs/TESTING.md 新小節）。截圖：`specs/settings-ce-table-mobile/screenshots/settings-ce-{1440,390}-{zh,en}.png`。
scrollWidth / clientWidth：1440 zh 1440/1440、1440 en 1440/1440、390 zh 390/390、390 en 390/390（無橫向捲動）。390 en 截圖目視：兩張卡片、六列各帶標籤、無詞中斷行。
