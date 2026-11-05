# 測試案例：CI 新增 gitleaks 與 pip-audit 掃描（獨立 workflow）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Language: 繁體中文; identifiers and file paths stay as they are.
-->

**規格**：`specs/ci-secrets-deps/plan.md`（此任務沒有 spec.md，計畫即規格來源）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、有命中、不該發生的事發生時，系統怎麼反應（停下、不放行、不放寬）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

標記說明：

- 「†」＝計畫的「失敗先行測試」清單沒有對應函式，但計畫「作法」明確寫了這個行為；executor 須在同一個測試檔補上檢查。
- 「手動」＝ `docs/TESTING.md` 新節「CI security checks」的步驟，或計畫「完成標準」要求寫進 ledger 的證據（連結、指令輸出）；驗收者看 ledger 與 diff。
- 「維護者條件 1–5」＝計畫「維護者原話」下的五條。他的原話是 2026-11-03「按照你的建議改CI」，建議內容就是只加 gitleaks 加 pip-audit。

## User Story 1 — 新增獨立的 security workflow，不動既有 CI（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；維護者條件 1 | 功能 | 實作完成 | 看 `.github/workflows/` | 有新檔 `security.yml`，`name: security`，內含兩個 job：`gitleaks` 與 `pip-audit`；它和 `tests.yml` 是不同的檔案 | 自動：`tests/ci_security_workflow_test.sh`（test_security_workflow_exists_and_is_separate） |
| TC-002 | 作法「檔名與 job 名」 | 功能 | 同上 | 看 `security.yml` 的每個 job id 與 name | 沒有任何一個叫 `run_all` 或 `shard`（`run_all` 是分支保護的必過檢查名稱，不能重名） | 自動：`tests/ci_security_workflow_test.sh`（test_job_names_do_not_collide_with_required_check） |
| TC-003 | 作法「觸發」 | 功能 | 同上 | 看 `security.yml` 的觸發條件 | 有 `pull_request`、`push`（分支限 `v3` 與 `main`）、`schedule`（每週一次）、`workflow_dispatch` 四種 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-004 | 作法「觸發」：不加 `merge_group` | 不在範圍 | 同上 | 搜尋 `security.yml` 有沒有 `merge_group` | 完全沒有 `merge_group` | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-005 | 作法「權限」 | 功能 | 同上 | 看 `security.yml` 最上層的 `permissions` | 有 `permissions:`，而且只有 `contents: read` 一項 | 自動：`tests/ci_security_workflow_test.sh`（test_permissions_are_read_only_and_no_pull_request_target） |
| TC-006 | 作法「權限」：兩個 job 不再加權限 | 功能 | 同上 | 看 `gitleaks` 與 `pip-audit` 兩個 job 內部 | job 內沒有自己的 `permissions` 區段 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-007 | 作法「權限」：不用 `pull_request_target` | 功能 | 同上 | 搜尋 `security.yml` | 沒有 `pull_request_target`（這種觸發會讓外來 PR 拿到寫入權限） | 自動：`tests/ci_security_workflow_test.sh`（同上函式） |
| TC-008 | 作法「權限」：不用任何 secret | 功能 | 同上 | 搜尋 `security.yml` | 沒有 `secrets.` 字樣 | 自動：`tests/ci_security_workflow_test.sh`（同上函式） |
| TC-009 | 維護者條件 4 | 功能 | 同上 | 看 `security.yml` 每一行 `uses:` | 每一行都是 `owner/repo@<40 字元十六進位 commit sha>  # vX.Y.Z`；沒有 `@v4` 這類版本標籤、沒有 `@main`、`@master` | 自動：`tests/ci_security_workflow_test.sh`（test_every_uses_is_pinned_to_full_sha） |
| TC-010 | 維護者條件 4；作法「釘 sha」 | 功能 | 同上 | 看 ledger | 每個 `uses:` 都附「tag 對應 sha」的查證指令（`gh api repos/<owner>/<repo>/git/ref/tags/<tag>`，必要時解開 annotated tag）與其輸出，且輸出的 sha 與 workflow 內寫的一致 | 手動：ledger |
| TC-011 | 作法「忽略清單」；PITFALLS 第 45 條 | 功能 | 同上 | 搜尋 `security.yml` | 不含 `continue-on-error`、`\|\| true`、`--no-fail`、`if: false`（沒有任何讓檢查變成「紅了也當沒事」的後門） | 自動：`tests/ci_security_workflow_test.sh`（test_no_way_to_turn_checks_off） |
| TC-012 | 維護者條件 1；範圍「不准碰 tests.yml」 | 功能 | 在有 git 歷史的 clone 上 | 比對 `tests.yml` 與 `origin/v3` | `git diff origin/v3 -- .github/workflows/tests.yml` 完全沒有輸出 | 自動：`tests/ci_security_workflow_test.sh`（test_existing_tests_yml_untouched） |
| TC-013 | 不做：「不改既有 tests.yml，包含把其 `@v4` 改釘 sha」 | 不在範圍 | 同上 | 看 `tests.yml` 的 `uses:` | `actions/checkout@v4`、`actions/cache@v4` 原樣保留（沒有被順手改成 sha） | 自動：`tests/ci_security_workflow_test.sh`（同 TC-012 函式：diff 為空即成立） |
| TC-014 | 維護者條件 1、5；不做：「不改 ruleset、分支保護、必過檢查清單」 | 不在範圍 | 實作完成 | 看 diff 與 `security.yml`，並看 ledger | 沒有任何呼叫 GitHub API 修改 ruleset／分支保護的程式或步驟；`security.yml` 與測試檔都沒有這類指令；ledger 沒有記錄做過這類操作 | 手動：ledger 與 diff |
| TC-015 | 維護者條件 5；作法「不設必過」；裁決 1 | 功能 | 實作完成 | 看 ledger | 寫明「兩個 job 目前不是必過檢查」，並把「要不要設為必過」列為給維護者的方向題 | 手動：ledger |
| TC-016 | 範圍「不准碰」清單 | 不在範圍 | 實作完成 | 看 `git diff --stat origin/v3` | 變更的檔案只有範圍內的：`.github/workflows/security.yml`、`.gitleaks.toml`、`platform/pip-audit-ignore.txt`、`tests/ci_security_workflow_test.sh`、`docs/TESTING.md`；沒有動 `tests/quarantine.txt`、憲法、`spec.md`、`test-case*.md`、dev-queue.json、`docs/ROADMAP.md`、`.claude-plugin/plugin.json` | 手動：ledger 與 diff |
| TC-017 | 不做：「不加 Dependabot、zizmor、ruff、release-please、Playwright、MCP conformance」「不做 pre-commit hook 或本機 gitleaks 整合」 | 不在範圍 | 實作完成 | 看 diff | 沒有新增 `dependabot.yml`、上述任一工具的設定或步驟，也沒有 pre-commit hook 或本機 gitleaks 整合 | 手動：ledger 與 diff |
| TC-018 | 不做：「不清除或改寫 git 歷史」 | 不在範圍 | 實作完成 | 看分支與 `origin/v3` 的關係 | `origin/v3@8322ee62`（或開工時重查的 base）仍是分支的祖先，沒有被改寫的提交；分支沒有 force-push 的痕跡 | 手動：ledger 與 `git log` |
| TC-019 | 專長守則（backend）；計畫範圍 | 不在範圍 | 實作完成 | 看 diff | 沒有動 `platform/abf_platform/`、`platform/abf_station/`、`hooks/`、`commands/`、`skills/` 任何程式（所以沒有新的網頁／API／聊天動作、寫入動作或使用者紀錄，專長守則的對等性、跨使用者、確認管道項目不適用） | 手動：ledger 與 diff |

## User Story 2 — gitleaks 掃機密外洩（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 作法「gitleaks job」；裁決 2 | 功能 | 實作完成 | 搜尋 `security.yml` | 沒有使用 `gitleaks/gitleaks-action`（組織帳號需要授權金鑰）；改用在 runner 下載官方 release 壓縮檔 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-021 | 作法「gitleaks job」：釘版本 | 功能 | 同上 | 看下載 gitleaks 的步驟 | gitleaks 版本字串是明確版本號，不是 `latest` | 自動：`tests/ci_security_workflow_test.sh`（test_gitleaks_download_is_verified） |
| TC-022 | 作法「gitleaks job」：sha256 驗證 | 功能 | 同上 | 看下載之後、執行之前的步驟 | 有 `sha256sum -c`（或同義的雜湊比對），使用寫死在檔內的 sha256；比對失敗時不會繼續執行 gitleaks | 自動：`tests/ci_security_workflow_test.sh`（同上函式） |
| TC-023 | 作法「gitleaks job」 | 功能 | 同上 | 看 `gitleaks` job 的 `actions/checkout` 步驟 | 設了 `fetch-depth: 0`（拿到完整歷史，否則掃不到舊提交） | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-024 | 維護者條件 2；作法 (a) | 功能 | 同上 | 看全 repo 歷史那一步的指令 | 指令是 `gitleaks git --redact --no-banner --config .gitleaks.toml`（掃整個 repo 歷史），任何事件觸發都會跑 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-025 | 維護者條件 2；作法 (b) | 功能 | 同上 | 看 PR diff 那一步的指令 | 指令帶 `--log-opts "origin/${{ github.base_ref }}..HEAD"`，只掃這個 PR 新增的提交 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-026 | 作法 (b)：只在 `pull_request` 事件跑 | 功能 | 同上 | 看 PR diff 那一步的條件 | 這一步限定只在 `pull_request` 事件執行（push、排程、手動觸發時不跑，因為沒有 base_ref） | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-027 | 作法「一律加 `--redact`」；PITFALLS 第 40 條 | 功能 | 同上 | 看 `security.yml` 內每一個 gitleaks **掃描**指令 | 每一個都含 `--redact`（日誌不會出現疑似機密原文） | 自動：`tests/ci_security_workflow_test.sh`（test_gitleaks_uses_redact） |
| TC-028 | 作法「`.gitleaks.toml` 只放 allowlist」；維護者條件 3「不准整個關掉」 | 功能 | 同上 | 看 `.gitleaks.toml` | 設定檔存在於 repo 根，且沒有任何設定會讓 gitleaks 的預設偵測規則失效或被取代（沿用預設規則，例如 `[extend] useDefault = true`；不含停用規則、不含自訂規則取代預設）。否則 gitleaks 會「掃了但沒有規則，永遠綠」 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-029 | 作法「allowlist 每條上方一行註解寫理由」；PITFALLS 第 19 條 | 功能 | `.gitleaks.toml` 有 allowlist 條目時（沒有條目時此條自動成立） | 看每個 `[[allowlists]]` 及其 `regexes`／`paths` 條目的上一行 | 上一行都是 `#` 開頭、寫了理由的註解 | 自動：`tests/ci_security_workflow_test.sh`（test_allowlist_entries_have_reason_and_are_not_blanket） |
| TC-030 | 作法「不得用整個目錄或萬用 `.*`」；維護者條件 3 | 例外 | 同上 | 搜尋 `.gitleaks.toml` | 不含 `regexes = ['.*']`，也不含單獨的 `paths = ['.*']`（不能用一條萬用條目把掃描整個放掉） | 自動：`tests/ci_security_workflow_test.sh`（同上函式） |
| TC-031 | 作法「精準條目」 | 功能 | 同上 | 看每個 allowlist 條目 | 每條都指定 `commit`、`paths`、`regexes` 其中之一，且範圍精準（指到特定檔案或提交，不是整個目錄） | 自動：`tests/ci_security_workflow_test.sh` † |

## User Story 3 — pip-audit 掃相依漏洞（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 作法「pip-audit job」 | 功能 | 實作完成 | 看 `pip-audit` job 的 Python 設定 | 使用 `actions/setup-python`（已釘 sha，見 TC-009），Python 版本 3.12 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-033 | 作法「釘版本 `pip install pip-audit==<版本>`」 | 功能 | 同上 | 看安裝 pip-audit 的指令 | 是 `pip install pip-audit==<明確版本號>`，不是未指定版本 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-034 | 維護者條件 2；作法 | 功能 | 同上 | 看掃描 constraints 的指令 | 指令含 `pip-audit -r platform/constraints.txt --no-deps --disable-pip` | 自動：`tests/ci_security_workflow_test.sh`（test_pip_audit_targets_both_files） |
| TC-035 | 維護者條件 2；作法 | 功能 | 同上 | 看掃描 pyproject 的指令 | 另有一個指令掃 `./platform`（或 `platform/pyproject.toml`），用來看 `mcp>=2.3,<3` 這類未釘版本實際解出什麼 | 自動：`tests/ci_security_workflow_test.sh`（同上函式） |
| TC-036 | 作法「忽略清單只能由 `--ignore-vuln` 讀自 `platform/pip-audit-ignore.txt`」 | 功能 | 同上 | 看 `pip-audit` 指令怎麼處理要忽略的漏洞 | 要忽略的漏洞 ID 只來自 `platform/pip-audit-ignore.txt`，經 `--ignore-vuln` 傳入；workflow 內沒有直接寫死的 `--ignore-vuln <ID>` 或其他忽略機制 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-037 | 範圍「`pip-audit-ignore.txt`」 | 功能 | 同上 | 看 `platform/pip-audit-ignore.txt` | 檔案存在；若首跑沒有任何要忽略的，檔案仍存在、只含說明註解 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-038 | 範圍：每行 `<漏洞ID>  # 理由與到期日`；PITFALLS 第 19 條 | 功能 | 檔內有非註解行時（沒有時自動成立） | 看每個非註解行 | 每行都含漏洞 ID、`#` 與理由、一個日期 | 自動：`tests/ci_security_workflow_test.sh`（test_allowlist_entries_have_reason_and_are_not_blanket） |
| TC-039 | 作法「複查日（≤90 天）」；裁決 5 | 功能 | 檔內有非註解行時 | 比對每行的複查日與該行加入的日期 | 複查日不晚於加入日後 90 天 | 手動：ledger 與 diff |
| TC-040 | 維護者條件 3；裁決 5 | 例外 | 首跑 pip-audit 有命中，且不升級套件就無法修復 | 看處置 | 漏洞 ID 寫進 `pip-audit-ignore.txt` 並附理由與複查日；job 本身沒有被放寬（沒有 `\|\| true`、`continue-on-error`、`--no-fail`）；ledger 把「升級相依」列為後續片 | 手動：ledger 與 diff |
| TC-041 | 不做：「不升級 `constraints.txt` 內任何套件」；範圍「不准碰」 | 不在範圍 | 實作完成 | 比對 `platform/constraints.txt` 與 `platform/pyproject.toml` | 兩個檔都與 `origin/v3` 完全相同 | 手動：ledger 與 `git diff origin/v3 -- platform/constraints.txt platform/pyproject.toml` |

## User Story 4 — 先在分支上跑一次、留下手動驗證步驟（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-042 | 「失敗先行測試」 | 功能 | 測試檔寫好、`security.yml` 還沒建 | 跑 `bash tests/ci_security_workflow_test.sh` | 結果為紅（`FAIL`，結束碼非 0），這段紅輸出貼進 ledger；之後實作完成再跑為綠 | 手動：ledger |
| TC-043 | 「失敗先行測試」：只用 grep／awk | 功能 | 沒有網路、沒有 PyYAML 的環境 | 跑 `bash tests/ci_security_workflow_test.sh` | 每個檢查輸出 `ok` 或 `FAIL`，結束碼代表整體結果，不需要網路或 PyYAML | 自動：`tests/ci_security_workflow_test.sh` |
| TC-044 | 「失敗先行測試」：test_existing_tests_yml_untouched | 功能 | 在沒有 git 歷史的環境（例如部署複本） | 跑同一個測試 | 該檢查印出 `skipped`，不算失敗 | 自動：`tests/ci_security_workflow_test.sh` † |
| TC-045 | 維護者條件 3；作法「首跑與處置」 | 功能 | 分支已 push | 讓 `gitleaks` 與 `pip-audit` 兩個 job 各跑一次 | ledger 記有兩個 job 各自的 run 連結、結果（綠或紅）與命中筆數 | 手動：ledger |
| TC-046 | 維護者條件 3：誤報要修或寫進 allowlist 附理由 | 功能 | 首跑 gitleaks 有命中，且判定為誤報（最可能在 `platform/tests/fixtures/`） | 看 `.gitleaks.toml` 與 ledger | 每個誤報都有一條精準的 allowlist 條目（指向特定檔案或提交），上方註解寫理由，ledger 逐條說明；若首跑零命中，ledger 寫「零命中」 | 手動：ledger 與 diff |
| TC-047 | 作法「真機密 → 停下回報」；裁決 4 | 例外 | 首跑 gitleaks 命中的是真機密 | 看 executor 的處置 | 停下並回報 BLOCKED（屬安全事件）；沒有把它寫進 allowlist，沒有改寫 git 歷史；回報建議由維護者輪替金鑰 | 手動：ledger |
| TC-048 | 範圍：`docs/TESTING.md` 末尾新增一節 | 功能 | 實作完成 | 比對 `docs/TESTING.md` 與 base | 只在檔案末尾新增一節「CI security checks」，既有段落一個字都沒改（diff 只有新增行，且在檔尾） | 手動：ledger 與 diff |
| TC-049 | 完成標準「手動案例」 | 功能 | 同上 | 讀 `docs/TESTING.md` 新節 | 寫有 (a) 假機密、(b) `run_all` 不受影響、(c) 假機密不進最終歷史 三個案例，每個都具體到可照做 | 手動：`docs/TESTING.md` |
| TC-050 | 完成標準 (a)：「AKIA 格式假金鑰」 | 功能 | 在暫時分支（draft PR）提交一個**假**的 AKIA 格式金鑰 | 看 `gitleaks` job | `gitleaks` job 變紅（證明預設規則有生效，且自訂設定沒有把掃描放空）；run 連結記進 ledger | 手動：`docs/TESTING.md` 新節 (a) |
| TC-051 | 完成標準 (a)：日誌已遮蔽 | 功能 | 同 TC-050 | 看 `gitleaks` job 的日誌 | 日誌裡看不到假金鑰原文（以 `REDACTED` 取代） | 手動：`docs/TESTING.md` 新節 (a) |
| TC-052 | 完成標準 (b)；維護者條件 1 | 功能 | 同 TC-050 | 看同一個 PR 的 `run_all` 狀態 | `run_all` 的狀態與 job 組成沒有因為新 workflow 而改變（假機密不影響它；security 紅燈不會變成 `run_all` 紅燈） | 手動：`docs/TESTING.md` 新節 (b) |
| TC-053 | 完成標準 (c) | 功能 | 暫時分支驗證結束 | 看 `feat/ci-secrets-deps` 分支與暫時分支 | 暫時分支已刪除；假機密提交不在 `feat/ci-secrets-deps` 的歷史，也不會進最終合併歷史；feat 分支沒有留下痕跡 | 手動：`docs/TESTING.md` 新節 (c) |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-054 | 安全網「Credentials … never in git; never printed」 | 功能 | 實作完成 | 跑 `bash tests/credentials_stay_in_settings_test.sh` | 維持綠；新檔沒有讓它變紅 | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-055 | 憲法不得被本片改動；Development Workflow（`tests.yml` 被憲法點名） | 功能 | 實作完成 | 跑 `bash tests/charter_v4_workflow_test.sh`，並看 diff | TC-018 維持綠（憲法仍含 `.github/workflows/tests.yml` 字樣）；憲法檔在 diff 中沒有變動 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-056 | 必過檢查 `run_all` 的結構不變 | 功能 | 實作完成 | 跑 `bash tests/run_all_shard_test.sh` | TC-006 維持綠（`tests.yml` 仍有 `--shard 1..4/4`、`^  run_all:`、`merge_group:`） | 自動：`tests/run_all_shard_test.sh` |
| TC-057 | Development Workflow：碰受保護路徑 `.github/` 須附影響證明（風險 L） | 功能 | 實作完成 | 看 ledger | 有爆炸半徑證明，四項齊全：(1) 新 workflow 的觸發事件與權限；(2) 與 `tests.yml` 的共用物（應為「無」）；(3) 它不是必過檢查，最壞情況是新 job 紅而 PR 仍可合併、不會擋住 `run_all`；(4) 失敗時整檔移除的方式（刪 `security.yml` 一個檔） | 手動：ledger |
| TC-058 | 同上：共用物為「無」 | 功能 | 實作完成 | 比對 `security.yml` 與 `tests.yml` | 沒有同名 job、沒有相同的 cache key、沒有相同的 concurrency 群組名；`security.yml` 不使用 `actions/cache` | 手動：ledger 與 diff（驗收者用 grep 實測） |
| TC-059 | 計畫「允許的斷言變動：本片不改任何既有測試」 | 不在範圍 | 實作完成 | 看 diff 中 `tests/` 與 `platform/tests/` | 除了新增 `tests/ci_security_workflow_test.sh`，沒有任何既有測試檔被修改、放寬、跳過；`tests/quarantine.txt` 沒動 | 手動：ledger 與 diff |
| TC-060 | Development Workflow「Green at every stage」；完成標準 | 功能 | 實作完成 | 看完成記號並跑新測試 | `executor-status` 為 `GREEN <HEAD sha>` 且工作樹乾淨；`tests/run_all.sh` 自動收進新測試（它在 `tests/*.sh` 內）；沒有未解釋的紅 | 自動：`tests/run_all.sh`（由 gate 記號證明）與 `tests/ci_security_workflow_test.sh` |
| TC-061 | 專長守則「資料結構變動須附 migration 或寫明不需要」；裁決 3 | 功能 | 實作完成 | 看 diff | 沒有動任何資料表或 JSON 鍵；計畫已寫明「不需要 migration」，diff 與之相符 | 手動：ledger 與 diff |
