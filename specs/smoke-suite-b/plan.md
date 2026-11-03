---
id: smoke-suite-b
title: 部署後煙霧測試（tests/smoke + scripts/smoke.sh）：只讀、網址由環境變數給、未設就跳過
tier: C
kinds: deploy
risk: M
lane: L44-smoke-suite
branch: test/smoke-suite-b
base: v3
source: 維護者派工說明（developer-agent 簡報，2026-11-03）
---

# smoke-suite

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/smoke-suite-b/plan.md`。**只處理本任務**。

## 目標
桌機升版（`deploy/platform-upgrade.sh`）之後，一行指令就能確認正式站「活著」：首頁能開、MCP 端點有回應、安全標頭（CSP）在。全部唯讀、不碰資料、不印任何祕密；沒有給網址就整組跳過，絕不預設打正式站。出事時印出回復提示。

## 維護者原話（verifier 出題用）
逐字取自 developer-agent 的簡報（維護者要求）：
1. 「Add tests/smoke/ with @pytest.mark.smoke tests (register the marker, check how markers are registered today) and scripts/smoke.sh.」→ 測試檔在 `tests/smoke/`，帶 `smoke` 標記，標記有註冊；`scripts/smoke.sh` 存在。
2. 「Base URL from env (SMOKE_BASE_URL); unset = skip, never default to production.」→ 未設或空字串＝整組 skip（不是 fail、不是預設值）。
3. 「Read-only checks only: home page 200, healthcheck endpoint, MCP endpoint reachable, required response headers (CSP). No secrets in output.」→ 只送 GET／無內容 POST 探測；輸出不含 token、cookie、金鑰。
4. 「scripts/smoke.sh runs `pytest -m smoke` after a deploy on the desktop host and prints a rollback hint.」
5. 「Verify the real endpoint names from the platform code before specifying them.」→ 見「環境事實」：v3 沒有專用 health 路由，見「作法」的處理。
6. 「Files allowed: new tests/smoke/**, scripts/smoke.sh, marker registration file only. No .github/, no abf_station changes.」
7. 「Also ensure the default test run (tests/run_all.sh) still skips smoke when the env var is unset.」

## 範圍：檔案
只准動：
- 新增 `tests/smoke/__init__.py`（不需要則省略）、`tests/smoke/conftest.py`、`tests/smoke/test_smoke.py`、`tests/smoke/test_smoke_skips_by_default.py`。
- 新增 `scripts/smoke.sh`（可執行位元：`git update-index --chmod=+x`）。
- 標記註冊檔：目前 **沒有任何標記被註冊**（v3 唯一的 pytest 設定是 `platform/pyproject.toml` 的 `[tool.pytest.ini_options] testpaths = ["tests"]`，沒有 `markers`；`platform/tests/conftest.py` 也沒有 `addinivalue_line`）。作法見下；**只准選一處**：新增 repo 根目錄 `pytest.ini`（只含 `[pytest]` 與 `markers`）。不改 `platform/pyproject.toml`（平台套件檔，且其 `testpaths` 指向 platform/tests，不涵蓋 repo 根的 tests/smoke）。
- 禁止：`.github/`、`platform/abf_station/`、`platform/abf_platform/`、`platform/tests/`、`tests/*.sh`、`tests/run_all.sh`、`deploy/`、`docs/`（含 PITFALLS／OPERATIONS／TESTING 文字；若認為該補文件，列為後續）。

## 作法
**標記**：根目錄 `pytest.ini`：`[pytest]` 下 `markers =` 一行 `smoke: read-only checks against a deployed site; need SMOKE_BASE_URL`，另加 `testpaths = tests/smoke`？——**不加** testpaths（避免改變任何人從根目錄手動跑 pytest 的行為）；smoke.sh 明確指定 `tests/smoke`。同時在 `tests/smoke/conftest.py` 用 `pytest_configure` 的 `config.addinivalue_line("markers", ...)` 不重複註冊（單一來源＝pytest.ini）；conftest 只做「跳過」邏輯。

**跳過（核心）**：`tests/smoke/conftest.py` 的 `pytest_collection_modifyitems` 對每個帶 `smoke` 標記的項目：`SMOKE_BASE_URL` 未設或去空白後為空 → 加 `pytest.mark.skip(reason="SMOKE_BASE_URL is not set; smoke tests never default to a real site")`。有設時：必須是 `http://` 或 `https://` 開頭、無使用者資訊（`user:pass@` → 整組 fail，訊息只說「網址不可含帳密」，不回顯該網址）、尾端 `/` 去掉。`tests/smoke/test_*.py` 全部加 `pytestmark = pytest.mark.smoke`。**沒有任何預設網址常數**。

**探測（只用標準函式庫 `urllib.request`，不新增相依；逾時 10 秒；不跟隨轉址除非下表註明）**——端點名稱已對 v3 程式核對：
| 檢查 | 請求 | 預期 | 依據 |
|---|---|---|---|
| 首頁 | `GET /`（不跟轉址） | 303，`Location: /login`（未登入的 `unauth()`）或 200；再 `GET /login` | 200 | `web.py` `board()`→`unauth()`→`RedirectResponse("/login", 303)`；`login_form` |
| 健康檢查 | 沒有專用路由（`grep -i health platform/abf_platform` 只在無關資料裡有字） | 以 `GET /login` 200 且本文含 `<form` 代表 web 行程活著；`GET /.well-known/oauth-authorization-server` 200 且為 JSON（含 `issuer`）代表授權伺服器活著 | `web.py` auth_routes；**不得為此新增路由**（禁改 abf_platform）|
| MCP 可達 | `POST /mcp`（無 Authorization、本文 `{}`）；`GET /.well-known/oauth-protected-resource/mcp` | 前者 401，`WWW-Authenticate` 以 `Bearer` 開頭、本文 JSON 含 `"error": "unauthorized"`；後者 200 JSON（僅在站台設了 `--public-url` 時存在，否則 skip 並說明原因，不 fail） | `http_auth._refuse`、`BearerAuth.discovery` |
| 標頭 | 對 `GET /login` 的回應 | `Content-Security-Policy` 含 `default-src 'none'` 與 `frame-ancestors 'none'`；`X-Frame-Options: DENY`；`X-Content-Type-Options: nosniff`；`Cache-Control: no-store` | `web.py` `_HEADERS`（約 86～89 行）；標頭名比對一律不分大小寫（PITFALLS 20e） |
| 404 也帶標頭 | `GET /_smoke_no_such_path` | 404 且同樣有 CSP | `add_headers` middleware |

- 若 caddy 把 `/mcp*` 與其餘分給兩個行程（OPERATIONS.md 第 2 節對照表），上面各檢查本來就走同一個 `SMOKE_BASE_URL`，不需第二個變數。
- 絕不送 `Authorization`、不 `POST /login`、不 `POST /register`（會建立資料）；`POST /mcp` 無憑證只會得到 401。測試內不讀 `SMOKE_TOKEN` 之類變數。
- 失敗訊息只寫「哪一項、期望什麼、拿到什麼狀態碼／標頭名」，**不印回應本文**（以免洩漏）、不印 `SMOKE_BASE_URL` 完整值以外的任何環境變數；網址只印主機名稱（`urlsplit(...).hostname`）。

**scripts/smoke.sh**（bash 3.2 相容、`set -uo pipefail`）：
1. 解析自己的 repo 根（`$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)`），不寫死使用者路徑。
2. `SMOKE_BASE_URL` 未設 → 印 `SMOKE_BASE_URL is not set: nothing was checked.` 與用法，**exit 2**（手動執行時不得假裝通過；與 pytest 的 skip 區隔）。
3. 選 python：`${SMOKE_PYTHON:-python3}`；`"$PY" -m pytest -m smoke tests/smoke -rs -p no:cacheprovider`；pytest 不在 → 印提示 exit 3。
4. 退出碼透傳；非 0 時印回復提示（三行內）：`Smoke checks failed. To go back: restore the data folder from the latest backup (deploy/backup.sh), check out the previous release in the platform checkout, reinstall (pip install ./platform), restart the three services; see docs/OPERATIONS.md section 4 (Upgrade).` 成功時印 `Smoke checks passed.`。
5. 不用 `set -x`／`bash -x`、不 echo 任何 token 變數、不用 `date -d`／`grep -P`／`xargs -r`／`find -printf`、不用 bash 4 關聯陣列、不用 `nohup`（既有靜態掃描會抓，見下）。

**預設測試不受影響**：`tests/run_all.sh` 只收 `tests/*.sh`（第 340 行），不會碰 `tests/smoke/*.py`；平台套件從 `platform/` 跑 `tests/`（platform/tests），也不收。故預設 `run_all.sh` 與 CI 根本不會執行 smoke；為了讓「未設變數就跳過」有一條能自證的測試，加 `tests/smoke/test_smoke_skips_by_default.py`（見下）。

## 失敗先行測試
（檔案在 `tests/smoke/`；現在這些檔不存在，故全紅。測試自己不連外：以 `http.server` 在 127.0.0.1 臨時埠起一個假站台，或用 `subprocess` 跑子 pytest。）
1. `test_skip_when_env_unset`：子行程 `python -m pytest -m smoke tests/smoke -rs`（環境移除 `SMOKE_BASE_URL`）→ 退出碼 0，輸出含 `skipped`，不含 `passed`（探測測試數 ≥ 5 全 skipped）。
2. `test_skip_when_env_blank`：`SMOKE_BASE_URL="  "` 同上。
3. `test_no_default_url_in_sources`：讀 `tests/smoke/*.py` 與 `scripts/smoke.sh` 原始碼，不得出現 `https?://` 後接非 `127.0.0.1`／`localhost`／`example.invalid` 的主機字面值（防止寫死正式網址）。
4. `test_marker_registered`：根目錄 `pytest.ini` 含 `smoke:`；子行程 `pytest --strict-markers -m smoke tests/smoke --collect-only` 退出碼 0。
5. `test_rejects_credentials_in_url`：`SMOKE_BASE_URL=http://u:p@127.0.0.1:1` → 失敗，輸出不含 `u:p`。
6. 對假站台（回應與上表一致）：`test_home_redirects_to_login_then_200`、`test_login_page_alive`、`test_oauth_metadata_json`、`test_mcp_unauthenticated_is_401_with_bearer`、`test_security_headers_present`、`test_404_carries_csp`——假站台回正確內容時綠；另各有一條反例（缺 CSP、MCP 回 200、首頁 500）→ 對應檢查紅（用子 pytest 或直接呼叫檢查函式，擇一，函式放 `tests/smoke/conftest.py` 的 helper）。
7. `test_output_has_no_secrets`：假站台在回應本文與標頭塞 `Set-Cookie: session=SECRET123`、本文含 `SECRET123`；失敗輸出與 `-rs` 摘要都不得含 `SECRET123`。
8. `test_smoke_sh`（以 `bash scripts/smoke.sh` 執行，`SMOKE_PYTHON` 指向當前 python）：未設變數 → exit 2、含 `not set`；假站台綠 → exit 0、含 `passed`；假站台缺 CSP → 非 0 且輸出含 `deploy/backup.sh`（回復提示）。
9. 靜態：`bash -n scripts/smoke.sh`；`bash tests/portable_userland.sh`、`bash tests/credentials_stay_in_settings_test.sh`、`bash tests/works_without_host_test.sh`、`bash tests/no_second_run_state_test.sh`、`bash tests/bash32_arrays_test.sh`、`bash tests/bsd_userland_test.sh`、`bash tests/no_hardcoded_paths.sh`、`bash tests/flow_skills_layout_test.sh` 仍綠（這些會掃 `scripts/*.sh`，見下）。

## 完成標準（done when）
- 上列測試存在並綠（`python -m pytest tests/smoke -q` 與 `bash scripts/smoke.sh` 於假站台情境）；`SMOKE_BASE_URL` 未設時 `python -m pytest -m smoke tests/smoke` 全 skipped、退出碼 0。
- `bash tests/run_all.sh --timeout 900` 全綠（環境紅依 README 通例；WSL 的 `constitution_scope_test.sh` 見 PITFALLS 46，以 CI 為準並註明）；`bash tests/run_all.sh --list` 的檔數與改動前相同。
- `git diff --stat origin/v3` 只出現「範圍」列的檔案（閱卷看 diff，證據貼 ledger）；`.github/`、`platform/` 沒有改動。
- 沒有任何正式網址、token、cookie 出現在新檔、測試輸出或 ledger。
- 專長守則檢查一行寫進報告。

## 環境事實
- 反向代理：一個主機名稱對三個行程（`docs/OPERATIONS.md` 第 2 節）：`/mcp*`、`/.well-known/oauth-protected-resource*` → mcp 8788；`/trace/*`、`/user-info`、`/agent/*` → serve 8787；其餘（含 `/`、`/login`、OAuth 路由）→ web 8789。
- web 回應標頭（`web.py` `_HEADERS`）：`Cache-Control: no-store`、`X-Frame-Options: DENY`、`Referrer-Policy: same-origin`、`X-Content-Type-Options: nosniff`、CSP（`default-src 'none'; style-src <sha>; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`）；`add_headers` middleware 讓框架自己的 404／405 也有。`/launch` 的 CSP 多 `img-src 'self'`，煙霧測試不碰。
- 未登入的 `/` 回 303 → `/login`（`unauth`；有暫時密碼登入時 `to_welcome` 可能轉 `/welcome`——測試接受 `/login` 或 `/welcome`，兩者之一且最終 200）。
- MCP：`mcp_server.build_http_app` 包在 `http_auth.BearerAuth`；無有效 token → 401＋`WWW-Authenticate: Bearer`（有 `--public-url` 與 `web_base_url` 時帶 `resource_metadata="…"`）。
- 升版腳本：`deploy/platform-upgrade.sh`「never rolls back」，備份是 `deploy/backup.sh`；回復提示只描述步驟，不自動執行任何回復。
- v3 沒有 `/health`、`/healthz` 路由，也沒有 smoke 相關字樣（`git grep -i -E "smoke|healthz" origin/v3` 除 PITFALLS 外無相符）。
- pytest 現況：標記未註冊；`platform/pyproject.toml` 有 `testpaths = ["tests"]`；`platform_test.sh` 在 platform/ 下跑 pytest 並用 `-p no:cacheprovider`。
- 靜態掃描會讀新增的 `scripts/smoke.sh`：`tests/portable_userland.sh`（GNU 專用寫法）、`credentials_stay_in_settings_test.sh`（印 token 變數／`set -x`）、`works_without_host_test.sh`（`bash -n`、引用 `hooks/`）、`no_second_run_state_test.sh`（`nohup`）、`wsl_bridge_test.sh`、`bash32_arrays_test.sh`、`bsd_userland_test.sh`、`no_hardcoded_paths.sh`、`flow_skills_layout_test.sh`（`tests/` 內不得出現 `commands/(setup|launch|…).md` 與 `$ROOT/commands`）。
- PITFALLS（`docs/PITFALLS.md`，`docs/solutions/` 不存在）已查，相符項：
  - **20e「kcserver sends its HTTP headers lowercase…」**——症狀：依 RFC 大小寫比對標頭會靜默停用分支；檢查：標頭名一律不分大小寫比對（`urllib` 的 `Message.get` 本身不分大小寫，不要自己 `dict` 化後用大小寫比對）。
  - **16b「On Windows, only WSL can multiplex」／20c「Two Windows-specific traps…」**——症狀：Git Bash 上的行為與 Linux 不同、東西「明明在卻找不到」；檢查：`smoke.sh` 在桌機 WSL／Linux 跑，Git Bash 上的失敗不當回歸；測試內不用 named pipe、不依賴 MSYS 路徑改寫。
  - **46「Tests that make a temporary clone go all red when run in WSL from a Windows-made worktree」**——症狀：WSL 跑全套件時 clone 類測試全紅；檢查：worktree 用 `--relative-paths`，不是本任務的回歸。
  - 其餘條目（agent、relay、tw、Nextflow 類）與本任務無關。

## 不做
- 不新增 `/health` 路由、不改 `platform/abf_platform/`、不動 `platform/abf_station/`、不動 `.github/`（CI 不跑煙霧測試；若要在 CI 或排程加，另開任務）。
- 不做任何寫入或需登入的檢查（不 POST /login、/register、/launch；不用 token）。
- 不把 smoke 併進 `tests/run_all.sh`、不改 `deploy/platform-upgrade.sh`（讓升版腳本結尾自動呼叫 smoke.sh 是後續）。
- 不改 `docs/`（OPERATIONS／TESTING 補一段「升版後跑 scripts/smoke.sh」是後續文件任務）。
- 不自動回復、不印正式網址、不預設任何網址。
- 後續（本片不做）：health 專用路由、升版腳本串接、文件、CI 排程。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
2. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值，條數 ≤ 20。
3. 標記註冊只准用根目錄 `pytest.ini`（一處）；若 executor 發現 `pytest.ini` 與 `platform/pyproject.toml` 在從 `platform/` 目錄跑時互相覆蓋（pytest 以最近的 rootdir 設定檔為準），不得改 pyproject，回報給 developer-agent。
0. **【最高優先，覆蓋本檔其他處】executor 的寫入守衛（pretool_executor_write_guard.py）一律擋 `pytest.ini`、`conftest.py`、`pyproject.toml`、`setup.cfg`、`constraints.txt`，11-03 前一版因此 BLOCKED。本計畫一律不建這些檔**：①把本檔所有「`pytest.ini`」「`tests/smoke/conftest.py`」改讀為 `tests/smoke/smoke_support.py`（一般模組，放探測函式、假站台、fixtures；測試檔 `from smoke_support import ...` 或用 `tests/smoke/` 的 rootdir 匯入，擇一能跑的）。②跳過邏輯改在 smoke_support 提供 `pytestmark` 清單：`pytest.mark.smoke` ＋ `pytest.mark.skipif(not os.environ.get("SMOKE_BASE_URL","").strip(), reason="SMOKE_BASE_URL is not set; smoke tests never default to a real site")`；各測試檔 `pytestmark = SMOKE_MARKS`。③標記註冊不寫檔：`scripts/smoke.sh` 與測試內的子行程一律帶 `-o "markers=smoke: read-only checks against a deployed site; need SMOKE_BASE_URL"`；repo 沒有 --strict-markers，從別處直接跑只會多一則未註冊警告，可接受，ledger 註明並建議維護者之後另開任務在 pyproject 註冊。④計畫「失敗先行測試」第 4 項 `test_marker_registered` 改為：帶上述 `-o markers=` 時 `--strict-markers --collect-only` 退出碼 0。⑤不得用 shell 或 python 繞過守衛。
4. 健康檢查沒有專用路由是已核對的事實；以 `/login`＋OAuth 中繼資料代替，並在 ledger 寫明。
5. worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明；落地前 `git merge origin/v3`。

## 專長守則（deploy）

### executor

- 提供上線後煙霧測試（smoke）：測試放在專案指定的目錄、標記 `@pytest.mark.smoke`，只用 `pytest -m smoke` 執行；目標網址從環境變數讀（例如 `SMOKE_BASE_URL`），沒設就 skip 並說明，不預設指向正式環境。
- 煙霧測試只做唯讀：首頁可達、健康檢查端點回 200、關鍵頁面不報錯、必要的回應標頭存在。不建立資料、不花錢、不觸發寫入。
- 要有健康檢查端點（healthcheck），只回「活著／相依服務是否可達」，不含版本以外的內部細節。
- 輸出與日誌不得含密鑰、token、完整連線字串；失敗訊息只印網址與狀態碼。
- 每次上線的說明要有回滾（rollback）備註：回到哪個版本／標籤、怎麼回、資料結構變動是否可逆。沒有備註不算完成。
- 煙霧測試要能在上線前先對本機或暫存環境跑通，再對正式環境跑。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 未設環境變數時 `pytest -m smoke` 整體 skip 而非失敗或連到預設主機。
- 健康檢查 TC：回 200 且不洩漏內部細節。
- 唯讀 TC：煙霧測試期間後端沒有任何寫入呼叫。
- 輸出不含密鑰的 TC（對測試輸出與日誌做字串檢查）。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：煙霧測試會寫入或花錢；網址寫死；輸出含密鑰；沒有回滾備註；`-m smoke` 未登記標記（出現 unknown marker 警告）。
- **UNVERIFIED**：對真實正式環境的煙霧測試結果（verifier 不連正式環境，除非計畫明寫）；需 developer-agent 上線後補跑並附結果。
- **「需要人看的事」**：回滾步驟是否他人照著能做、健康檢查是否過於簡略。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
