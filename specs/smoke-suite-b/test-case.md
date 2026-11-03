# 測試案例：部署後煙霧測試（smoke-suite-b）

**規格**：`specs/smoke-suite-b/plan.md`（本任務沒有獨立 spec.md；維護者原話逐字引在 plan 的「維護者原話」，下表以「原話 1～7」指它們）　**總覽**：`test-case-overview.md`

名詞：「假站台」＝測試自己在本機 127.0.0.1 臨時埠起的小網站，回應照 plan「探測」表的樣子；所有測試只連它，絕不連外。「煙霧測試」＝升版後確認站台活著的唯讀檢查。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

原話對照：1「Add tests/smoke/ with @pytest.mark.smoke tests … and scripts/smoke.sh」→ TC-014；2「unset = skip, never default to production」→ TC-001、002、003；3「Read-only checks only … No secrets in output」→ TC-004～013；4「smoke.sh runs `pytest -m smoke` … prints a rollback hint」→ TC-015～017；5「Verify the real endpoint names」→ TC-005、TC-020；6「Files allowed … No .github/, no abf_station changes」→ TC-020；7「default test run (tests/run_all.sh) still skips smoke when the env var is unset」→ TC-019。

驗證用的測試檔都放在 `tests/smoke/`（如 `test_smoke_skips_by_default.py`、`test_smoke.py`，探測函式與假站台在 `tests/smoke/smoke_support.py`）。放進 `tests/smoke/` 的「自證測試」（驗證跳過、smoke.sh、標記的那幾條）本身不得帶 `smoke` 標記、不得因 `SMOKE_BASE_URL` 未設而被跳過，且它們啟動的子 pytest 一律用 `-m smoke`，因此不會再選到自證測試（不遞迴）。

## User Story 1 — 沒給網址就整組跳過，絕不預設正式站（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 2；plan 失敗先行 1、2；專長守則「未設變數整體 skip」 | 功能 | 子行程環境裡移除 `SMOKE_BASE_URL`（另一次設成只有空白 `"  "`） | 跑 `python -m pytest -m smoke tests/smoke -rs` | 兩種情形都：退出碼 0；輸出有 `skipped`（探測測試至少 5 條全被跳過）；跳過原因含 `SMOKE_BASE_URL is not set`；輸出沒有 `passed`、`failed`、`error`；沒有任何連線送出。直接跑 `python -m pytest tests/smoke`（變數未設）時，探測測試跳過、自證測試通過 | 自動：`tests/smoke/test_smoke_skips_by_default.py` |
| TC-002 | 原話 2「never default to production」；plan 失敗先行 3 | 功能 | 無 | 讀 `tests/smoke/*.py` 與 `scripts/smoke.sh` 的原始碼，找 `http://`、`https://` 後面的主機字面值 | 除 `127.0.0.1`、`localhost`、`example.invalid` 外，沒有任何寫死的網址或主機名稱；沒有預設網址常數 | 自動：`tests/smoke/test_smoke_skips_by_default.py` |
| TC-003 | plan「跳過」：有設時的網址規則；失敗先行 5 | 例外 | 假環境 `SMOKE_BASE_URL=http://u:p@127.0.0.1:1`（帶帳密）；另一次 `SMOKE_BASE_URL=ftp://127.0.0.1:1`（不是 http/https） | 跑 `python -m pytest -m smoke tests/smoke` | 兩次都整組失敗（不是跳過、不是通過）、不連線；帶帳密那次訊息只說「網址不可含帳密」，輸出完全不含 `u:p`；輸出沒有回顯該網址 | 自動：`tests/smoke/test_smoke_skips_by_default.py` |

## User Story 2 — 唯讀探測：首頁、健康、MCP、安全標頭（優先度 P1）

假站台的回應照 plan「探測」表與「環境事實」。「綠」＝假站台回對的內容。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-004 | 原話 3「home page 200」；plan 探測表「首頁」 | 功能 | 綠假站台：`GET /` 回 303、`Location: /login`；`GET /login` 回 200。另一次 `Location: /welcome` 且 `/welcome` 回 200。再一次 `GET /` 直接回 200 | 帶 `SMOKE_BASE_URL=假站台` 跑首頁檢查 | 三種情形都通過；檢查不跟隨轉址去 `/`（看到的是 303 本身）；轉向 `/login` 或 `/welcome` 以外的位置則不通過 | 自動：`tests/smoke/test_smoke.py` |
| TC-005 | 原話 3「healthcheck endpoint」、原話 5；plan 探測表「健康檢查」（v3 沒有專用 health 路由） | 功能 | 綠假站台：`GET /login` 回 200 且本文含 `<form`；`GET /.well-known/oauth-authorization-server` 回 200、JSON、含 `issuer` | 跑 web 活著檢查與授權伺服器活著檢查 | 兩項都通過；失敗時只說哪一項、期望什麼、拿到的狀態碼，不貼回應本文；檢查只打這兩個既有路徑，沒有 `/health`、`/healthz` | 自動：`tests/smoke/test_smoke.py` |
| TC-006 | 原話 3「MCP endpoint reachable」；plan 失敗先行 6 | 功能 | 綠假站台：`POST /mcp` 回 401，`WWW-Authenticate` 以 `Bearer` 開頭，本文 JSON 含 `"error": "unauthorized"` | 跑 MCP 可達檢查 | 通過；檢查送出的 `POST /mcp` 沒有 `Authorization` 標頭、本文是 `{}` | 自動：`tests/smoke/test_smoke.py` |
| TC-007 | plan 探測表「MCP 可達」第二項 | 功能 | 兩種假站台：(a) `GET /.well-known/oauth-protected-resource/mcp` 回 200 JSON；(b) 同路徑回 404（站台沒設 `--public-url`） | 各跑一次該檢查 | (a) 通過；(b) 該項是「跳過」並說明原因（沒設 `--public-url`），不是失敗，整體退出碼不因此變非 0 | 自動：`tests/smoke/test_smoke.py` |
| TC-008 | 原話 3「required response headers (CSP)」；plan 探測表「標頭」 | 功能 | 綠假站台：`GET /login` 的回應有 CSP（含 `default-src 'none'` 與 `frame-ancestors 'none'`）、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、`Cache-Control: no-store` | 跑標頭檢查 | 通過；四項標頭缺任何一項或值不符，該檢查就不通過 | 自動：`tests/smoke/test_smoke.py` |
| TC-009 | plan 探測表「404 也帶標頭」 | 功能 | 綠假站台：`GET /_smoke_no_such_path` 回 404 並帶同樣的 CSP | 跑 404 檢查 | 通過；回的不是 404，或 404 沒有 CSP，則不通過 | 自動：`tests/smoke/test_smoke.py` |
| TC-010 | plan「環境事實」PITFALLS 20e（標頭名不分大小寫） | 功能 | 假站台把所有標頭名寫成全小寫（`content-security-policy`、`www-authenticate`、`location`…），其餘內容與綠站台相同 | 跑全部探測 | 全部通過，標頭檢查沒有因大小寫而靜默略過或誤判 | 自動：`tests/smoke/test_smoke.py` |
| TC-011 | plan 失敗先行 6 的反例 | 例外 | 三種壞假站台：(a) `/login` 的回應缺 CSP；(b) `POST /mcp` 沒帶憑證卻回 200；(c) `GET /` 回 500 | 各跑對應檢查 | (a) 標頭檢查失敗；(b) MCP 檢查失敗；(c) 首頁檢查失敗；失敗訊息指出哪一項、期望什麼、拿到的狀態碼或缺的標頭名 | 自動：`tests/smoke/test_smoke.py` |

## User Story 3 — 唯讀、不洩漏（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 原話 3「Read-only checks only」；plan「絕不送 Authorization…」；專長守則「唯讀：後端沒有任何寫入呼叫」；環境變數另設 `SMOKE_TOKEN=TOKEN456` | 功能 | 假站台記下收到的每個請求（方法、路徑、標頭） | 整組探測跑完 | 收到的請求只有 GET，加上一次無憑證的 `POST /mcp`；沒有 `POST /login`、`POST /register`、`POST /launch`，沒有 PUT／DELETE／PATCH；任何請求都沒有 `Authorization` 標頭；也沒有帶出 `TOKEN456` | 自動：`tests/smoke/test_smoke.py` |
| TC-013 | 原話 3「No secrets in output」；plan 失敗先行 7；專長守則「輸出不含密鑰」 | 例外 | 假站台在回應標頭放 `Set-Cookie: session=SECRET123`、在回應本文放 `SECRET123`，並讓一項檢查失敗（例如缺 CSP）；`SMOKE_BASE_URL` 帶路徑與查詢字串 `?k=QUERY789` | 跑含 `-rs` 的 pytest | 失敗輸出與 `-rs` 摘要都不含 `SECRET123`、`QUERY789`、也不含回應本文；網址只以主機名稱出現 | 自動：`tests/smoke/test_smoke.py` |

## User Story 4 — 標記與 `scripts/smoke.sh`（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 原話 1；plan 裁決 0③④；專長守則「`-m smoke` 未登記標記」 | 功能 | repo 內沒有新增 `pytest.ini`、`conftest.py`、`pyproject.toml`（plan 裁決 0）；`tests/smoke/` 與 `scripts/smoke.sh` 存在 | 帶 `-o "markers=smoke: read-only checks against a deployed site; need SMOKE_BASE_URL"` 跑 `python -m pytest --strict-markers -m smoke tests/smoke --collect-only`；再跑 `bash scripts/smoke.sh`（假站台綠） | 前者退出碼 0；兩者輸出都沒有 `Unknown pytest.mark.smoke`／`PytestUnknownMarkWarning`；`tests/smoke/test_*.py` 的探測測試都帶 `smoke` 標記。（plan 已接受：不帶 `-o` 直接跑 `pytest -m smoke` 會多一則未註冊警告，不算本條失敗，但必須記在 ledger） | 自動：`tests/smoke/test_smoke_skips_by_default.py` |
| TC-015 | 原話 2、4；plan smoke.sh 第 2 點 | 例外 | 環境沒有 `SMOKE_BASE_URL` | 跑 `bash scripts/smoke.sh`（`SMOKE_PYTHON` 指向目前的 python） | 退出碼 2（不是 0）；輸出含 `SMOKE_BASE_URL is not set: nothing was checked.` 與用法；不假裝通過 | 自動：`tests/smoke/test_smoke_skips_by_default.py` |
| TC-016 | 原話 4「runs `pytest -m smoke`」；plan smoke.sh 第 3、4 點 | 功能 | 綠假站台，`SMOKE_BASE_URL` 指向它 | 跑 `bash scripts/smoke.sh` | 退出碼 0；輸出含 `passed` 與 `Smoke checks passed.`；腳本不寫死使用者路徑，從別的目錄呼叫也能找到 repo 根 | 自動：`tests/smoke/test_smoke_skips_by_default.py` |
| TC-017 | 原話 4「prints a rollback hint」；專長守則「回滾備註」 | 例外 | 假站台缺 CSP（檢查會失敗） | 跑 `bash scripts/smoke.sh` | 退出碼非 0（與 pytest 相同、不被吞掉）；輸出的回復提示三行內，含 `deploy/backup.sh`、`pip install ./platform`、`docs/OPERATIONS.md`；提示只描述步驟，沒有自動執行任何回復動作 | 自動：`tests/smoke/test_smoke_skips_by_default.py` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 第 3 條（沒有個人路徑、寫死位置）；plan 失敗先行 9、環境事實的靜態掃描清單 | 功能 | 新增的 `scripts/smoke.sh` 已就位 | 跑 `bash -n scripts/smoke.sh`，以及 `tests/portable_userland.sh`、`credentials_stay_in_settings_test.sh`、`works_without_host_test.sh`、`no_second_run_state_test.sh`、`bash32_arrays_test.sh`、`bsd_userland_test.sh`、`no_hardcoded_paths.sh`、`flow_skills_layout_test.sh` | 全部仍綠；`smoke.sh` 沒有 `set -x`、沒有 echo 任何 token 變數、沒有 GNU 專用寫法與 bash 4 關聯陣列 | 自動：上列各 `tests/*.sh` |

## User Story 5 — 範圍邊界：預設測試不受影響、沒做不該做的事

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 原話 7；plan「不做」：不把 smoke 併進 `tests/run_all.sh` | 不在範圍 | `SMOKE_BASE_URL` 未設 | 跑 `bash tests/run_all.sh --list`，與 base（`v3`）的輸出比 | 清單裡沒有 `smoke` 或 `tests/smoke`；條目數與 base 相同；`tests/run_all.sh` 沒被改；預設測試因此不會執行任何煙霧探測 | 自動：`bash tests/run_all.sh --list`（驗收時與 base 比對） |
| TC-020 | 原話 6；plan「範圍：檔案」與「不做」 | 不在範圍 | 已提交的分支 | `git diff --name-only <base>...HEAD`（計畫與 test-case 檔不算實作改動） | 只出現：`tests/smoke/` 下的新檔（含 `smoke_support.py`）與 `scripts/smoke.sh`；`.github/`、`platform/`（含 `abf_station`、`abf_platform`、`platform/tests`）、`deploy/`、`docs/`、`tests/run_all.sh`、`tests/*.sh` 沒有改動；沒有新增 `/health` 之類的路由；沒有 `pytest.ini`、`conftest.py`、`pyproject.toml` | 自動：閱卷時以 `git diff --name-only` 核對 |
