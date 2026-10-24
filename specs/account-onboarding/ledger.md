# 同事開帳號與安裝站台代理的說明頁 progress ledger

- [x] RED: `platform/tests/test_onboarding_doc.py` 先提交；實作前 40 failed, 1 passed（TC-044：沒有 `docs/ONBOARDING.md`，T1–T12 皆紅）。
- [x] GREEN: 新增 `docs/ONBOARDING.md`（五節）、`README.md` 在 `docs/PITFALLS.md` 段前加一段指標；`test_onboarding_doc.py` 41 passed。
- [x] 全套（abf-fast-suite）124/124 通過。
- [x] 範圍：只動 `docs/ONBOARDING.md`、`README.md`、`platform/tests/test_onboarding_doc.py`、本檔；INSTALL／OPERATIONS／PLATFORM／TESTING 與程式碼零差異（`test_tc047_tc051_other_docs_untouched` 鎖住）。
- 待維護者確認：`user passwd` 遠端同事如何設密碼（文件已標一句）。
