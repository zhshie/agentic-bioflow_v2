# 續跑可改參數與資源（d） progress ledger

- [x] PLATFORM.md「Resume and relaunch (spec 009e)」一節、actions 後那句改成新說法；TESTING.md 第 2 點改字、新增第 5 點「改參數的續跑沿用快取（not yet done）」（原 5、6 順延為 6、7，文字未動）。
- [x] 新測試 platform/tests/test_resume_edit_params_docs.py（7 個測試）。
- 未驗證：改參數後續跑沿用其餘快取，只用假站台檢查過，沒有在 Taiwania-3 實測（TESTING.md 第 5 點仍標 not yet done）。
- 備註：test_failures.py::test_docs_and_ledger 要求 PLATFORM.md 該段仍含 resume-edit-params 一詞，所以 actions 後那句保留 spec 名稱（不再說 the gap is）。

`git diff --stat 924fa52..HEAD`（含本檔 commit 前）：
```
 docs/PLATFORM.md                               |  15 +--
 docs/TESTING.md                                |   7 +-
 platform/tests/test_resume_edit_params_docs.py | 127 +++++++++++++++++++++++++
 3 files changed, 140 insertions(+), 9 deletions(-)
```
