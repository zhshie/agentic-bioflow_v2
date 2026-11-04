# 設定頁第一片：個人逐步模式與開發模式、憑證已設定狀態 progress ledger

- [x] RED：`platform/tests/test_web_settings_personal.py`（33 個測試，涵蓋 TC-001..061 的自動項目），commit 6f1f080a
- [x] GREEN：store 兩欄（step_mode、dev_mode，INTEGER，舊庫由 `_migrate_tokens` 補欄，NULL＝預設）、`actions.get_my_settings` / `set_my_setting`（PAGE 通道）、`POST /settings/personal`、全頁橫幅（`web_devmode.py` 的 contextvar，`user_of` 每次請求重設）、憑證區「已設定／未設定」
- [x] 既有測試改動（預期內，只放寬允許的表單／路由）：`test_web_settings.py`（st08 兩處表單集合加 `/settings/personal`）、`test_web_board.py`（表單 regex 三處、路由表加一條）、`test_web_parity.py`（WEB_ONLY 加兩個動作）。沒有刪除、略過或放鬆任何斷言。
- [x] 橫幅字串放 `web_devmode.py` 而不放 `web_board.py`：`test_tcs03_s04` 禁止 web_board.py 出現 NCHC，而 TC 規定的英文橫幅含 NCHC。
- [x] 驗證：五支相關測試檔 137 通過（含 personal 33）。
- 全套測試結果見下方（執行後補）。
- [x] 全套第一輪失敗 6 項已修：新字串移出被釘住的 web_settings.STRINGS（改放 web_devmode 函式內表）；既有釘住測試只更新預期（schema 兩欄、路由 /settings/personal、NO_TOOL 兩動作、web.py store 用法、STYLE_SHA256 含兩條新 CSS）。
