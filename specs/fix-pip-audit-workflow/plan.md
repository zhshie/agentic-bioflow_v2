---
id: fix-pip-audit-workflow
title: 修 security 工作流 pip-audit 工作最後一行（--no-deps 只能搭 -r，v3 上每次紅燈）
tier: A
kinds: backend
lane: L-fix-pip-audit
base: v3
risk: L
review: self
serves: maintenance
---

# fix-pip-audit-workflow

## 目標
`.github/workflows/security.yml` 的 `pip-audit` 工作在 v3 每次 push 都紅（最近 5 次全紅），原因是最後一行 `pip-audit ./platform --no-deps --disable-pip $IGNORES` 的旗標組合 pip-audit 不接受。只修這一行讓它能跑，**不放寬掃描**。
意義：紅燈一直亮會讓人習慣忽略 security 工作；修好之後，依賴出現真漏洞時它才會是有意義的訊號。

## 維護者原話（verifier 出題用）
> 「要我回答的是我能決定的嗎? 我看不懂，你決定」（2026-11-08）

意思：維護者授權 developer-agent 自行決定如何修這條 pip-audit 紅燈（本件雖碰 `.github/`，屬 A 級，但已授權；review: self）。對應測試：TC-1（修好那行不含 `--no-deps`）、TC-2（掃描沒有被放寬：仍有兩條 pip-audit 指令、仍掃 constraints.txt 與專案、沒有新增 `--ignore-vuln <具體ID>`、`pip-audit-ignore.txt` 沒動）。

## 裁決
1. 只准修 pip-audit 工作的**最後一行**。不得放寬掃描，不得新增任何 `--ignore-vuln <ID>`（`$IGNORES` 迴圈照舊，`platform/pip-audit-ignore.txt` 不動、仍是空的）。
2. 不得動 `gitleaks` 工作（PR #380 在改它）、不得改 `tests.yml`、不得加 `continue-on-error`／`|| true`。
3. 第一行 `pip-audit -r platform/constraints.txt --no-deps --disable-pip $IGNORES` 完全不動（它是「釘死版本」的掃描，已綠：`No known vulnerabilities found`）。

## 範圍：檔案
只准改：
- `.github/workflows/security.yml`（只動 pip-audit 工作的最後一行）
- `tests/ci_security_workflow_test.sh`（只新增一個檢查函式並登進最後的迴圈；既有函式不改弱）
- `specs/fix-pip-audit-workflow/ledger.md`（證據）

其餘一律不動（尤其 `platform/pip-audit-ignore.txt`、`platform/constraints.txt`、`platform/pyproject.toml`、`.gitleaks.toml`、`tests.yml`）。

## 作法
1. 決定的修法（方案 C）：最後一行改成
   `pip-audit ./platform $IGNORES`
   即同時拿掉 `--no-deps` 與 `--disable-pip`。理由見「環境事實」：專案目錄模式一定要讓 pip 解析依賴，這兩個旗標本來就只對 `-r` 有效；拿掉後等於「專案宣告的依賴（`pyproject.toml` 的 `mcp>=2.3,<3`、`python-multipart`）解析出最新版再掃」，與第一行「掃釘死版本」互補，**掃描範圍只增不減**。
2. 若方案 C 在 CI 上因建置失敗而紅（`setup.py` 的 build hook 會複製 `<repo>/skills`；runner 上有整個 checkout，應可；若仍失敗，貼日誌回報 lead，不要自己換成放寬的做法）。**不得**退而求其次把該行刪掉或改成只掃 constraints.txt（那就是放寬，且會讓下方既有守護測試轉紅）。
3. 在 `tests/ci_security_workflow_test.sh` 新增 `test_pip_audit_project_line_has_no_no_deps`：從 `code`（去掉註解的 workflow）取出符合 `pip-audit .*(\./platform|platform/pyproject\.toml)` 的行，斷言該行**不含** `--no-deps`（pip-audit 規定 `--no-deps` 只能搭 `-r`），並登進檔尾的 `for t in ...` 清單。
4. 驗證在 CI 做：推分支後到 Actions 手動跑 `security` 的 `workflow_dispatch`（或看 PR 上的 run），pip-audit 工作要綠。ledger 貼 run 連結與該工作最後幾行輸出。若 pip-audit 真的回報漏洞，**那是真訊號**：照 `platform/pip-audit-ignore.txt` 的格式需要維護者決定，回報 lead，不要自己加 ignore。

## 失敗先行測試
- `bash tests/ci_security_workflow_test.sh`：新增的 `test_pip_audit_project_line_has_no_no_deps` 在修之前 FAIL（行裡有 `--no-deps`），修之後 `ok`。
- 既有檢查全維持 ok，特別是下列釘住本件會碰到的句子的斷言（改行時不能讓它們轉紅）：
  - `test_pip_audit_targets_both_files`：要有 `pip-audit -r platform/constraints.txt --no-deps --disable-pip`（原字串）；要有符合 `pip-audit .*(\./platform|platform/pyproject\.toml)` 的行（所以新行必須保留 `./platform`）；`python-version: "3.12"`；`pip install pip-audit==N.N`；有 `--ignore-vuln`；有 `platform/pip-audit-ignore.txt`；沒有 `--ignore-vuln <字母開頭>`（不得寫死 ID）。
  - `test_no_way_to_turn_checks_off`：不得出現 `continue-on-error`、`|| true`、`--no-fail`、`if: false`。
  - `test_every_uses_is_pinned_to_full_sha`、`test_permissions_are_read_only_and_no_pull_request_target`、`test_triggers`、`test_security_workflow_exists_and_is_separate`、`test_job_names_do_not_collide_with_required_check`：不要碰到這些結構。
  - `test_existing_tests_yml_untouched`：`tests.yml` 零差異。
  - `test_allowlist_entries_have_reason_and_are_not_blanket`：`pip-audit-ignore.txt` 不動。
- 另有 `platform/tests/test_certifi_pin.py` 讀 `pip-audit-ignore.txt`（要求空清單）與 `constraints.txt` 的 certifi 行；這兩個檔不動就不會受影響。
- 以上用 `git grep -n "pip-audit\|security.yml\|ci_security_workflow" origin/v3` 查過；`docs/TESTING.md` 第 1063 行只描述兩個工作與「不是必要檢查」，沒釘旗標，不必改。

## 完成標準（done when）
- `git diff origin/v3 --stat` 只有範圍內三個檔；`security.yml` 的 diff 只有 pip-audit 最後一行（1 行刪 1 行加）。
- `bash tests/ci_security_workflow_test.sh` 全 ok（含新增那條）。
- CI 上 `security` 的 `pip-audit` 工作綠（ledger 貼 run 連結）。`gitleaks` 工作仍紅屬已知（PR #380 處理），不因它退回。
- diff 裡沒有新增 `--ignore-vuln <ID>`，`pip-audit-ignore.txt` 零差異，`tests.yml` 零差異。

## 環境事實
- 失敗證據：`gh run view 42391821250 --repo zhshie/agentic-bioflow_v2 --log-failed`（security 工作流，v3，PR #382 合併後的 push，2026-11-07）。pip-audit 工作最後幾行：
  - 第一行 `pip-audit -r platform/constraints.txt --no-deps --disable-pip` 輸出 `No known vulnerabilities found`（綠）。
  - 第二行 `pip-audit ./platform --no-deps --disable-pip` 印出 usage 後 `pip-audit: error: The --no-deps flag can only be used with --requirement (-r)`，`Process completed with exit code 2`。
- **真正原因**：pip-audit 2.10.1 規定 `--no-deps` 只能搭 `-r`；專案目錄（`./platform`）模式不接受。與 `./platform` 能不能被解析無關（`platform/` 有 `pyproject.toml`＋`setup.py`，結構正常）。這不是 PR 引入的退步：`gh run list --workflow security --branch v3` 最近 5 筆（42162000283、42173491693、42186060052、42387971767、42391821250）全 failure，這行從 workflow 建立起就沒跑成過。
- `--disable-pip` 的限制同理（只允許搭 `--no-deps` 或 `--require-hashes`），所以不能只拿掉 `--no-deps` 而留 `--disable-pip`；兩個都拿掉，專案模式才會讓 pip 解析依賴（pip-audit 在暫時 venv 裡解析）。此為依 pip-audit 說明與日誌推定，最終以 CI 實跑為準（作法第 4 點）。
- `platform/` 內容：`pyproject.toml`（dependencies `mcp>=2.3,<3`、`python-multipart`；extras `test`）、`setup.py`（build hook 複製 `<repo>/skills`）、`constraints.txt`（全部釘死）、`pip-audit-ignore.txt`（只有註解，空）。repo 沒有 `requirements*.txt`，所以改成 `-r` 檔的做法需要新增檔案，不採用。
- 同一個 workflow run 的 `gitleaks` 工作也紅（`leaks found: 34`），是另一件事，PR #380 處理；本件不碰。
- Git Bash 查 `git show origin/v3:.github/...` 會被路徑轉換搞壞，需先 `export MSYS_NO_PATHCONV=1`。
- 學習紀錄檢查：repo 的 `origin/v3` 上沒有 `PITFALLS.md`，也沒有 `docs/solutions/`；PITFALLS 已查，無相符項。
- 專長守則：`.claude/dev-profiles/` 沒有 `ci.md`，用 `backend.md`（下方由 `build-dev-plans.py` 貼上；其中擁有者／確認管道等條目與本件無關，閱卷寫「不適用：只改 CI 設定」即可）。

## 不做
- 不放寬掃描：不加 `--ignore-vuln <ID>`、不刪那行、不加 `continue-on-error`／`|| true`、不改 `pip-audit-ignore.txt`。
- 不動 `gitleaks` 工作與 `.gitleaks.toml`（PR #380）、不改 `tests.yml`。
- 不升級 pip-audit 版本、不改 `constraints.txt`、不新增 requirements 檔。
- 不把 security 設成必要檢查（`docs/TESTING.md` 寫它仍在觀察期）。

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
