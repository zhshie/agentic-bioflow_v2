---
id: ci-secrets-deps
title: CI 加兩道獨立檢查：gitleaks（機密外洩）與 pip-audit（相依漏洞），不動既有 run_all 與 ruleset
tier: A
kinds: backend
risk: L
lane: L50-ci-security
branch: feat/ci-secrets-deps
base: origin/v3@8322ee62；開工前 `git fetch` 並重查
source: 維護者 2026-11-03 核可（見下）；來源是 dev-queue backlog.ready 該項 note
---

# ci-secrets-deps

> 只有計畫、沒有程式。A 級＋碰受保護路徑 `.github/`，風險 L：閱卷多交爆炸半徑證明，PASS 後跑 /code-review 與 Opus 對抗審。

## 目標
在 `.github/workflows/` 新增**一個獨立 workflow** `security.yml`，內含兩個 job：`gitleaks`（掃 PR diff，並對整個 repo 歷史掃一次）與 `pip-audit`（掃 `platform/constraints.txt` 與 `platform/pyproject.toml` 的相依）。對使用者的意義：機密或有已知漏洞的套件進 v3 之前會被擋下或至少亮紅，而發佈流程（`run_all` 必過檢查）完全不受影響。

## 維護者原話（verifier 出題用）
- 2026-11-03：「按照你的建議改CI」。建議內容＝只加 gitleaks＋pip-audit（backlog note 記載）。
- 同 note 的條件（維護者核可範圍，逐條要有測試或 ledger 證據）：
  1. 新增獨立 workflow，不改既有 `run_all` job，不改 ruleset／分支保護（那屬 repo 設定，要另問）。
  2. gitleaks 掃 PR diff＋全 repo 一次；pip-audit 掃 requirements／pyproject 相依。
  3. 先在分支上跑一次看現況：既有漏洞或誤報要嘛修、要嘛寫進 allowlist 並附理由，不准整個關掉。
  4. action 版本釘 commit sha。
  5. 新 job 先不設為必過檢查（要不要設成必過另列方向題）。

## 範圍：檔案（只准改這些）
- 新檔 `.github/workflows/security.yml`
- 新檔 `.gitleaks.toml`（repo 根；只放 allowlist，每條上方一行註解寫理由）
- 新檔 `platform/pip-audit-ignore.txt`（每行 `<漏洞ID>  # 理由與到期日`；若首跑沒有任何要忽略的，檔案仍建立、只含說明註解）
- 新檔 `tests/ci_security_workflow_test.sh`（bash 靜態檢查，`tests/run_all.sh` 會自動收進 `tests/*.sh`）
- `docs/TESTING.md`：只在末尾新增一節「CI security checks」，寫手動案例（見完成標準）；不改既有段落
- **不准碰**：`.github/workflows/tests.yml`（一個字都不能動；`tests/run_all_shard_test.sh` TC-006 與 `charter_v4_workflow_test.sh` TC-018 釘住它）、`platform/constraints.txt` 與 `pyproject.toml`（相依升級是另案，會牽動全套測試）、`tests/quarantine.txt`、ruleset／分支保護設定（本機與 API 都不碰）、憲法、`spec.md`、`test-case*.md`、dev-queue.json。

## 作法
- **檔名與 job 名**：workflow `name: security`；job id 與 name 為 `gitleaks`、`pip-audit`。**不得**叫 `run_all` 或 `shard`（tests.yml 註解：`run_all` 是 ruleset 的 status-check context，不得重名）。
- **觸發**：`pull_request`、`push` 到 `v3` 與 `main`、`schedule`（每週一次，pip-audit 會因新公告而變紅）、`workflow_dispatch`。不加 `merge_group`（避免和必過檢查混淆；要不要進合併佇列屬後續方向題）。
- **權限**：頂層 `permissions: contents: read`，兩個 job 不再加權限；不用任何 secret；不用 `pull_request_target`。
- **釘 sha**：每個 `uses:` 都寫 `owner/repo@<40 字元 commit sha>  # vX.Y.Z`。executor 開工時用 `gh api repos/<owner>/<repo>/git/ref/tags/<tag>`（必要時解 annotated tag）查出真實 sha，不得憑記憶填、不得用分支名或 `@v4`。既有 tests.yml 用 `@v4` 不在本片處理（見不做）。
- **gitleaks job**：不用 `gitleaks/gitleaks-action`（組織帳號需授權金鑰）；改為在 runner 下載**釘版本**的 gitleaks 官方 release 壓縮檔，用寫死的 sha256 驗證後執行。`actions/checkout` 設 `fetch-depth: 0`。兩步：(a) 全 repo 歷史一次：`gitleaks git --redact --no-banner --config .gitleaks.toml`；(b) PR 時另掃 diff：`--log-opts "origin/${{ github.base_ref }}..HEAD"`（只在 `pull_request` 事件跑）。一律加 `--redact`，日誌不得出現疑似機密原文。
- **pip-audit job**：`actions/setup-python`（釘 sha，Python 3.12）→ 以釘版本 `pip install pip-audit==<版本>` → `pip-audit -r platform/constraints.txt --no-deps --disable-pip`，再對 `platform/pyproject.toml` 的 `dependencies` 解析結果掃一次（`pip-audit ./platform`，會解析 `mcp>=2.3,<3`、`python-multipart`；與 constraints 的差異即為「新版本未被釘住」的訊號）。忽略清單只能由 `--ignore-vuln` 讀自 `platform/pip-audit-ignore.txt`，不准用 `|| true`、`continue-on-error`、`--no-fail`。
- **首跑與處置**（維護者條件 3）：executor 在分支 push 後讓兩個 job 各跑一次，把結果（綠或紅、發現幾筆）貼進 ledger。
  - gitleaks 有命中：先判真偽。真機密 → 停下回報（BLOCKED，屬安全事件，不得自行改寫歷史），不寫進 allowlist。誤報 → 在 `.gitleaks.toml` 以 `[[allowlists]]` 加**精準**條目（指定 `commit`／`paths`／`regexes` 其一，不得用整個目錄或萬用 `.*`），上方註解寫理由。
  - pip-audit 有命中：能在不動 `constraints.txt` 下解決的才解；否則把漏洞 ID 寫進 `pip-audit-ignore.txt` 並附理由與複查日期（≤90 天）。升級相依另列為後續片。
- **不設必過**：不呼叫 GitHub API 改 ruleset。ledger 寫明「兩個 job 目前不是必過檢查」，並列出方向題（見裁決 1）。
- **結構性防呆測試**（`tests/ci_security_workflow_test.sh`，只用 grep／awk，不需網路與 PyYAML）見下節。

## 失敗先行測試
新檔 `tests/ci_security_workflow_test.sh`，輸出 `ok`／`FAIL`，以結束碼表示結果；先寫、改前確認紅（檔案尚不存在），紅輸出貼進 ledger。
- `test_security_workflow_exists_and_is_separate`：`.github/workflows/security.yml` 存在，含 `gitleaks` 與 `pip-audit` 兩個 job，且 `tests.yml` 與它是不同檔。**現在紅**。
- `test_job_names_do_not_collide_with_required_check`：security.yml 沒有名為 `run_all` 或 `shard` 的 job id 或 name。
- `test_every_uses_is_pinned_to_full_sha`：security.yml 每個 `uses:` 行都符合 `@[0-9a-f]{40}`；沒有 `@v\d`、`@main`、`@master`。
- `test_permissions_are_read_only_and_no_pull_request_target`：頂層有 `permissions:` 且只有 `contents: read`；無 `pull_request_target`、無 `secrets.`。
- `test_no_way_to_turn_checks_off`：security.yml 不含 `continue-on-error`、`|| true`、`--no-fail`、`if: false`。
- `test_allowlist_entries_have_reason_and_are_not_blanket`：`.gitleaks.toml` 每個 `[[allowlists]]` 或其 `regexes`／`paths` 條目上一行是 `#` 註解；不含 `regexes = ['.*']` 或單獨的 `paths = ['.*']`；`pip-audit-ignore.txt` 每個非註解行含 `#` 與日期。
- `test_gitleaks_download_is_verified`：security.yml 有 `sha256sum -c`（或同義）且 gitleaks 版本字串被釘（不是 `latest`）。
- `test_gitleaks_uses_redact`：每個 `gitleaks` 掃描指令都含 `--redact`。
- `test_existing_tests_yml_untouched`：`git diff origin/v3 -- .github/workflows/tests.yml` 為空（在 clone 上；若無 git 歷史則略過並印 skipped，仿 run_all_shard_test 的 deployed copy 處理）。
- `test_pip_audit_targets_both_files`：命令列含 `platform/constraints.txt` 與 `./platform`（或 `platform/pyproject.toml`）。

### 允許的斷言變動（既有測試釘住的東西，全列出）
本片不改任何既有測試。以下既有測試讀到 `.github/` 或 `tests/*.sh`，必須維持綠且不得改動：
- `tests/run_all_shard_test.sh` l.76-81（TC-006）：讀 `.github/workflows/tests.yml`，要有 `--shard 1..4/4`、`^  run_all:`、`merge_group:`。本片不動該檔，故不受影響。
- `tests/charter_v4_workflow_test.sh` l.61（TC-018）：憲法文字含 `.github/workflows/tests.yml`；與本片無關，不得改憲法。
- `tests/run_all.sh` l.340 `for f in "$ROOT"/tests/*.sh`：新測試檔會被自動收入；`run_all.sh` 開頭的總數（CLAUDE.md 寫 "all 73"）若有測試釘住檔案數，executor 要 `git grep -n "all 7[0-9]\|tests/\*\.sh"` 確認後在 ledger 說明（本計畫查到的只有說明文字，無斷言）。
- `docs/TESTING.md` l.57（提到 tests.yml 裝 jq）、l.177（`git diff main...HEAD --stat -- … .github …` 的歷史驗收句）：不改；新增一節放末尾。
- 分片：新測試約數秒，進哪一片由 run_all 自動分配，不需改 tests.yml 的矩陣。

## 完成標準（done when）
- 新測試改前紅、改後綠；`tests/run_all.sh` 全綠（已知環境紅見 dev-plans README）。
- ledger 記：`git diff --stat origin/v3` 只含範圍內檔；`git diff origin/v3 -- .github/workflows/tests.yml` 為空；兩個 job 在分支上的首跑結果（連結＋命中筆數）與處置（誤報逐條理由、或「零命中」）；每個 `uses:` 的 tag→sha 查證指令與輸出。
- 手動案例（寫進 TESTING.md 新節，閱卷依 README 通例看 ledger）：(a) 在分支故意提交一個**假**機密字串（如 gitleaks 測試用的 `AKIA` 格式假金鑰，提交後在同一 PR 內以 revert 清掉前先截圖／記下 run 連結），確認 `gitleaks` job 變紅且日誌已遮蔽；(b) 確認 `run_all` 的狀態不受影響；(c) 假機密 commit 不得進入最終合併歷史（用 squash 前先以 draft PR 的暫時分支做，結束即刪分支）。此案例由 developer-agent 在暫時分支做，不在 feat 分支上留痕。
- L 級爆炸半徑證明：列出 (1) 新 workflow 的觸發事件與權限；(2) 它與 `tests.yml` 的共用物（同名 job？同 cache key？）——應為「無」；(3) 它不是必過檢查，所以最壞情況是新 job 紅而 PR 仍可合併，不會擋住 `run_all`；(4) 失敗時如何整檔移除（刪 `security.yml` 一個檔即回復）。
- 不連真實服務、不改 repo 設定；不在本機跑 CI。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」；全套測試需 Linux／WSL（`tests/run_all.sh` 拒絕原生 Git Bash）。新測試是純 bash，可在 WSL 單跑：`bash tests/ci_security_workflow_test.sh`。
- 既有 CI：`.github/workflows/tests.yml` 是唯一 workflow；四個 shard job＋聚合 job `run_all`（ruleset 的 status-check context）；uses 為 `actions/checkout@v4`、`actions/cache@v4`（未釘 sha）。
- 相依檔：`platform/pyproject.toml`（`mcp>=2.3,<3`、`python-multipart`；test 額外 `pytest`、`httpx`）、`platform/constraints.txt`（Python 3.10.6 解出的完整釘版，含 `mcp==2.3.0`；`test_guidance.py:462` 釘住 `mcp==2.3.0`）。repo 沒有 `requirements*.txt`、`.gitleaks.toml`、`dependabot.yml`、`CODEOWNERS`。
- 提交假機密與測試資料時，repo 內既有的 fixtures（如 `platform/tests/fixtures/`）可能含 token 樣貌的字串，首跑誤報最可能出在這裡；allowlist 要用 `paths` 精準指向 fixtures 檔，並附理由。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`。`.github/` 為受保護路徑，只准新增檔案（維護者已核可）。
- **PITFALLS 已查（`docs/PITFALLS.md`；`docs/solutions/` 不存在），相符項**：
  - 第 45 條「The rebuild time check flaked on CI with a 2-second gap」：Check 為不得以 retry／xfail 掩蓋；對應本片「不准 `continue-on-error`／`|| true`」。
  - 第 19 條「A reason for not checking something is itself a claim, and it expires」：allowlist／ignore 的理由必須可驗證且有到期日；對應 `pip-audit-ignore.txt` 的日期要求與 allowlist 註解測試。
  - 第 40 條「Seqera launcher scripts hold the token in a 755 file」與一般 token 條目：機密不得進日誌；對應 `--redact` 與不使用 secrets。
  - 其餘條目（CI 時序、nano4、launch）與本片檔案無關。

## 不做
- 不改 ruleset、分支保護、必過檢查清單（裁決 1）。
- 不改既有 `tests.yml`，包含把其 `@v4` 改釘 sha（可另案）。
- 不升級 `constraints.txt` 內任何套件；漏洞修補以升級為解的另開片。
- 不加 Dependabot、zizmor、ruff、release-please、Playwright、MCP conformance（backlog `ci-hardening` 未點頭項目）。
- 不做 pre-commit hook 或本機 gitleaks 整合。
- 不清除或改寫 git 歷史；歷史中若找到真機密，回報由維護者處理（輪替金鑰優先）。

## 裁決
1. **要不要設為必過檢查？（方向題，維護者）** 建議：先觀察兩週再決定；設定屬 ruleset，不在本片。需要維護者答覆，本片不阻擋。
2. **gitleaks 用 binary 而非官方 action？** 建議：是（組織授權金鑰問題；binary 可釘版本與 sha256）。若維護者偏好官方 action，改成釘 sha 的 action 亦可，測試中的 `sha256sum -c` 案例改為只檢查 uses 釘 sha。
3. **資料結構**：不需要 migration（只新增 CI 與設定檔，不碰資料表或 JSON 鍵）。
4. **首跑發現真機密**：停下回報，不寫 allowlist，不改寫歷史（見作法）。
5. **pip-audit 命中且無法不升級修復**：寫入 `pip-audit-ignore.txt` 附理由與 ≤90 天複查日，並在 ledger 列為後續片；不放寬 job。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
