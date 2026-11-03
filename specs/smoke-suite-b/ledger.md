# 部署後煙霧測試（唯讀、未設 SMOKE_BASE_URL 就跳過） progress ledger

- [x] tests/smoke/smoke_support.py：探測函式、跳過標記、假站台（取代 conftest，依裁決 0）
- [x] tests/smoke/test_smoke.py：7 條真探測（帶 smoke 標記）＋假站台自證（TC-004～013、018）
- [x] tests/smoke/test_smoke_skips_by_default.py：TC-001、002、003、014～017
- [x] scripts/smoke.sh（可執行位元已設）
- [x] 靜態掃描 8 支 tests/*.sh 在 WSL 皆綠；tests/smoke 在 WSL：32 passed, 7 skipped

## 註記
- 標記沒有寫檔註冊（裁決 0）：scripts/smoke.sh 與子行程帶 `-o markers=...`；從別處直接跑 `pytest -m smoke` 只多一則 PytestUnknownMarkWarning。建議維護者之後另開任務在 platform/pyproject 或根目錄 pytest.ini 註冊。
- v3 沒有專用 health 路由：以 `GET /login`（200 且含 `<form`）加 OAuth 中繼資料代替。
- 真探測與假站台自證同放 test_smoke.py：真探測逐條用 `@smoke`（標記＋未設即 skip），自證測試不帶標記，故模組層級 pytestmark 改為逐函式裝飾。
- WSL 內 `constitution_scope_test.sh` 紅＝worktree 由 Windows git 建立的環境問題（PITFALLS 46），以 CI 為準。落地前需 `git merge origin/v3`。
- pytest 的 rm_rf 警告是 WSL 掛載盤的環境噪音。
