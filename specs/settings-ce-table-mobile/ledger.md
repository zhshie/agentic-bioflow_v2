# 設定頁「計算環境」表格在手機寬度改成一列一張卡片，欄位帶標籤 progress ledger

## 重釘雜湊（裁決 13、14）
證明：暫時刪掉 web_board.py 的 `@media (max-width:640px)` 四行（即新 STYLE 換回舊 STYLE），跑 `test_clean_page.py` 與 `test_web_settings_register.py`：test_clean_page 全過（五個頁面雜湊回到原值，只有 STYLE 不同）；register 只剩 ce 類別檢查失敗（因 `.ce` 規則被拿掉，預期）。隨後還原。
STYLE diff：只多一段 `@media (max-width:640px){.tbl.ce…}`（4 行）。第二輪修正（TC-008）後 STYLE 雜湊再變，五組頁面雜湊與 BASE_STYLE_SHA 依裁決 13、14 再重釘一次（只改常數值）。
只改常數值：test_clean_page.py :157-162（BASE_CONFIRM/EXPIRED/POST/BOARD/STYLE）、test_web_settings_register.py :18（BASE_STYLE_SHA）。
test_web_settings.py :201、:224：`"<td>" in r` -> `"<td" in r`。

## 截圖與溢出檢查（TC-009、TC-023）
指令：`scripts/dev/check_settings_mobile.py`（見 docs/TESTING.md 新小節）。截圖：`specs/settings-ce-table-mobile/screenshots/settings-ce-{1440,390}-{zh,en}.png`。
scrollWidth / clientWidth：1440 zh 1440/1440、1440 en 1440/1440、390 zh 390/390、390 en 390/390（無橫向捲動）。390 en、390 zh 截圖目視：兩張卡片、六列各帶標籤、無詞中斷行；「主要/Primary」徽章與「Broken thing/broken thing」訊息緊跟在自己的值旁邊。

## 第二輪修正（verifier：TC-008、TC-023）
TC-008：原 `.tbl.ce td{display:grid;…}` 讓格內文字節點、徽章、訊息各成一個網格項目，被排到標籤欄底下。改為 `.tbl.ce td{display:flow-root;border-bottom:0;padding:4px 0 4px 96px}` + `::before{float:left;width:88px;margin-left:-96px;…}`：格內內容照一般行內流動，標籤浮在左側。新增 test_ce08（格子規則不得是 grid／flex）。截圖已重拍並目視確認（390 zh／en）。scrollWidth／clientWidth 重跑：1440 zh 1440/1440、1440 en 1440/1440、390 zh 390/390、390 en 390/390。

## TC-023 diff stat（base = merge-base 2552583b，不含截圖與 specs）
```
 docs/TESTING.md                               |   8 ++
 platform/abf_platform/web_board.py            |   4 +
 platform/abf_platform/web_settings.py         |   7 +-
 platform/tests/test_clean_page.py             |  10 +-
 platform/tests/test_web_settings.py           |   4 +-
 platform/tests/test_web_settings_ce_mobile.py | 126 +++++++
 platform/tests/test_web_settings_register.py  |   2 +-
 scripts/dev/check_settings_mobile.py          |  86 +++++
```
截圖：`specs/settings-ce-table-mobile/screenshots/settings-ce-{1440,390}-{zh,en}.png`。

## TC-018/021/022/027/029/030/031 diff 證據（platform/abf_platform，-U0）
```
web_board.py（只新增，`.ptbl` 規則未動，無新顏色／斷點／JS）：
+    "@media (max-width:640px){.tbl.ce,.tbl.ce tbody{display:block}.tbl.ce thead{display:none}"
+    ".tbl.ce tr{display:block;background:var(--raised);border:1px solid var(--line);border-radius:6px;padding:8px 12px;margin:0 0 12px}"
+    ".tbl.ce td{display:flow-root;border-bottom:0;padding:4px 0 4px 96px}"
+    ".tbl.ce td::before{content:attr(data-label);float:left;width:88px;margin-left:-96px;color:var(--muted);font-size:12px}}"
web_settings.py（_ce_row 與表格 class）：
-    return ("<tr><td>%s</td>…六格…</tr>" % (…))
+    cells = (name, esc(platform or "—"), status, who, pipes or "—", esc(_when_iso(lastUsed)))
+    keys = ("th_name", "th_platform", "th_status", "th_agent", "th_pipes", "th_used")
+    return "<tr>" + "".join('<td data-label="%s">%s</td>' % (esc(t[k]), c) for k, c in zip(keys, cells)) + "</tr>"
-        body = '<table class="tbl">…'
+        body = '<table class="tbl ce">…'
```
測試檔常數變動：test_clean_page.py :157-162、test_web_settings_register.py :18（只改常數值）；test_web_settings.py :201、:224（`"<td>"` -> `"<td"`）。
