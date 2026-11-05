# 網頁 bug 二批（#338 #341 #342 #343） progress ledger

- [x] #338 費用頁：`web_cost.py` `_reason` 去掉 `task X: ` 前綴、取第一段、中文去結尾括號；非本月卡片標題與空表句帶月份；`action` 只在本月。
- [x] #341 標題列 `.head .meta` 資訊行與資訊分頁四列；`web.py` `read_run` 以 `launch_prefill`（kept）加入 pipeline／revision，站台 `compute_env` 無則 `ce_name`。
- [x] #342 右欄 360／300（DESIGN.md 為準；維護者若要 320／288，改回兩個數字與測試並改 DESIGN.md）。
- [x] #343 ≤900 px：可點區 24 px 規則、`.otbl` 水平捲動、檔名不斷字。24 px 只套 ≤900 px 待維護者確認。
- [x] `docs/TESTING.md` 加「390 px 手動檢查」。
- [ ] 瀏覽器手動項目（TC-030、035、041、046-049、055、056）：本輪沒有瀏覽器，未做，留給驗收者以 `ui_check.py --start` 做。

## 既有測試預期改動（舊 -> 新與理由）
- `test_web_board.py:211-212` 320px／288px -> 360px／300px（#342）。
- `test_web_cost.py:226` 「本月尚無分析」 -> 「2099-01 尚無分析」且「本月」不在中欄（計畫 1.3）。
- STYLE 長度 11475 -> 11742（`test_web_nano4_path.py`）；STYLE sha256 `0b5b317c...ae00` -> `719ce2abf9783006813e34889d8180ef2123d266168ed70e0969f8532ea1f59a`（`test_results_files.py` STYLE_SHA256、`test_web_settings_register.py` BASE_STYLE_SHA（`test_settings_pick_installed` 由此匯入）、`test_web_resume_edit.py`），`test_clean_page.py` BASE_STYLE 前 16 碼 -> `719ce2abf9783006`。重算：`hashlib.sha256(web_board.STYLE.encode()).hexdigest()`。
- `test_clean_page.py` BASE_CONFIRM／BASE_EXPIRED／BASE_POST／BASE_BOARD 頁面雜湊全部重釘（只有樣式表與 run 頁多了 meta 行不同）；`test_web_nano4_path.py` tc016 `/upload` 雜湊 `5e8e02ce8346a5d1`／`da0c912702e6f1bc` -> `dcd29dacdc236b61`／`78fb7defb00e675c`（同理，只因樣式表）。
- 計畫未列、但必須動：`test_web_results_outputs.py:401` 釘 `.otbl code{overflow-wrap:anywhere}` -> `.otbl code{overflow-wrap:normal;word-break:keep-all}`（#343 4.2 本意）。
- 計畫未列、但必須動：`test_su_usd.py:416` 假的 `my_usage` 預設月份寫死 `"2026-10"`，今天（2026-11）起它與目前月份不符、會被當成過去月份；改為預設 `web_cost.current_month(time.time())`（加 `import time`）。斷言 `— 本月尚無分析` 一字未動。

## 紅綠
改前 `test_web_bugs_b.py` 13 紅 3 綠（commit `RED:`），改後 16 綠（commit `GREEN:`）。

## 交接（全套 149/150）
- 唯一失敗：tests/platform_upgrade_test.sh TC-U28（`git diff --name-only $(merge-base origin/v3 HEAD) -- platform` 必須為空）。任何改 platform/ 的分支都會失敗（web-bugs-a #368 也改了 platform，同樣會踩到）；不在計畫列的檔案內，執行者不改。
- 需要 developer-agent 決定：放寬 TC-U28（如 TC-U26 改成看現況），或確認 CI 不跑此檢查。
- 其餘全綠；已重釘 test_web_finished fs02/fs07、ce08 字串雜湊、guided_launch_preview CSS 雜湊（均不在計畫列表，見 decisions.tsv）。
