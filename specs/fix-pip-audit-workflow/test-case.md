# 測試案例：修 security.yml 的 pip-audit 紅燈（專案目錄模式不接受 --no-deps）

**規格**：`specs/fix-pip-audit-workflow/plan.md`（本件無 spec.md，以 plan 為準）　**總覽**：`test-case-overview.md`

維護者原話（2026-11-08）：「要我回答的是我能決定的嗎? 我看不懂，你決定」。意思是授權 developer-agent 自己決定怎麼修這條紅燈，條件是「不放寬掃描」。plan 把這句話對應到 TC-001（修好那行不含 `--no-deps`）與 TC-002～TC-013（掃描沒有被放寬）。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

名詞：「專案行」＝ `.github/workflows/security.yml` 裡 pip-audit 工作的最後一行（原本是 `pip-audit ./platform --no-deps --disable-pip $IGNORES`）；「第一行」＝ 倒數第二行 `pip-audit -r platform/constraints.txt --no-deps --disable-pip $IGNORES`。「`code`」＝ 測試腳本把註解去掉後的 workflow 內容。

## User Story 1 — pip-audit 工作的最後一行能被 pip-audit 接受，紅燈變綠（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 維護者原話「你決定」；裁決 1；作法 3；完成標準 2 | 功能 | 修好的 `security.yml` | 從去掉註解的 workflow 取出符合 `pip-audit .*(\./platform|platform/pyproject\.toml)` 的那一行 | 找得到這一行，且該行**不含** `--no-deps`（pip-audit 規定 `--no-deps` 只能搭 `-r`） | 自動：`tests/ci_security_workflow_test.sh`（`test_pip_audit_project_line_has_no_no_deps`） |
| TC-002 | 作法 1（方案 C）；完成標準 1 | 功能 | 修好的 `security.yml` | 看 pip-audit 工作的最後一行 | 那一行就是 `pip-audit ./platform $IGNORES`：`--no-deps` 與 `--disable-pip` 兩個都拿掉（`--disable-pip` 只能搭 `--no-deps` 或 `--require-hashes`，不能留） | 手動：驗收者對 `git diff origin/v3 -- .github/workflows/security.yml` 逐字比對 |
| TC-003 | 作法 3；失敗先行測試（`test_pip_audit_targets_both_files`） | 功能 | 修好的 `security.yml` | 看專案行 | 專案行仍保留 `./platform`（掃專案本身）與 `$IGNORES`（排除清單照舊套用） | 自動：`tests/ci_security_workflow_test.sh`（`test_pip_audit_targets_both_files`） |
| TC-004 | 作法 3；失敗先行測試 | 功能 | 新增的 `test_pip_audit_project_line_has_no_no_deps` 已寫入測試檔 | 把該函式登進檔尾 `for t in ...` 清單；在**未修**的 `security.yml`（base）上跑 `bash tests/ci_security_workflow_test.sh`，再在修好的版本上跑 | 該函式有登進迴圈；在 base 上它 FAIL（行裡有 `--no-deps`）；修好後它 `ok` | 自動：`tests/ci_security_workflow_test.sh` |
| TC-005 | 目標；作法 4；完成標準 3 | 功能 | 分支已推上 GitHub | 到 Actions 手動跑 `security` 的 `workflow_dispatch`（或看 PR 上的 run） | `pip-audit` 工作綠；`ledger.md` 貼了 run 連結與該工作最後幾行輸出（`gitleaks` 工作仍紅屬已知，由 PR #380 處理，不因它退回） | 手動：看 `specs/fix-pip-audit-workflow/ledger.md` 的連結與日誌 |
| TC-006 | 作法 2、作法 4 | 例外 | CI 上 pip-audit 工作紅：原因是建置失敗，或 pip-audit 真的回報漏洞 | 看 ledger 與 diff | 日誌貼進 ledger 並回報 lead；diff 裡**沒有**為了變綠而加 `--ignore-vuln <ID>`、刪掉那行、改成只掃 `constraints.txt`、或改 `pip-audit-ignore.txt`（真漏洞是真訊號，要維護者決定） | 手動：看 ledger 與 `git diff origin/v3` |

## User Story 2 — 掃描沒有被放寬（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | 裁決 3 | 功能 | 修好的 `security.yml` | 看第一行 | 第一行原字串 `pip-audit -r platform/constraints.txt --no-deps --disable-pip` 仍在，一個字沒動 | 自動：`tests/ci_security_workflow_test.sh`（`test_pip_audit_targets_both_files`） |
| TC-008 | 目標「不放寬掃描」；測試先行 | 功能 | 修好的 `security.yml` | 數 pip-audit 工作裡的 pip-audit 掃描指令 | 仍有兩條：一條掃 `constraints.txt`（釘死版本），一條掃專案 `./platform`（專案宣告的依賴） | 自動：`tests/ci_security_workflow_test.sh`（`test_pip_audit_targets_both_files`） |
| TC-009 | 裁決 1；失敗先行測試 | 功能 | 修好的 `security.yml` | 找 `--ignore-vuln` 與 `platform/pip-audit-ignore.txt` | 迴圈仍讀 `platform/pip-audit-ignore.txt` 並用 `--ignore-vuln`；沒有任何 `--ignore-vuln <字母開頭的具體 ID>`（不得寫死 ID）；diff 沒有新增 `--ignore-vuln <ID>` | 自動：`tests/ci_security_workflow_test.sh`（`test_pip_audit_targets_both_files`） |
| TC-010 | 裁決 1；完成標準 4；環境事實 | 功能 | 修好的分支 | 比較 `platform/pip-audit-ignore.txt` 與 base；跑 certifi 釘版測試 | `pip-audit-ignore.txt` 零差異、仍只有註解（空清單）；`platform/tests/test_certifi_pin.py` 不受影響 | 自動：`tests/ci_security_workflow_test.sh`（`test_allowlist_entries_have_reason_and_are_not_blanket`）與 `platform/tests/test_certifi_pin.py` |
| TC-011 | 裁決 2；失敗先行測試 | 例外 | 修好的 `security.yml` | 在去掉註解的 workflow 裡找關掉檢查的寫法 | 完全沒有 `continue-on-error`、`\|\| true`、`--no-fail`、`if: false` | 自動：`tests/ci_security_workflow_test.sh`（`test_no_way_to_turn_checks_off`） |
| TC-012 | 範圍：測試檔「既有函式不改弱」；完成標準 2 | 功能 | 修好的分支 | 比較測試檔與 base；跑 `bash tests/ci_security_workflow_test.sh` | 測試檔的 diff 只有新增（一個函式＋登進迴圈清單），既有函式沒被刪、放寬或略過；全部檢查 `ok`（含 `test_every_uses_is_pinned_to_full_sha`、`test_permissions_are_read_only_and_no_pull_request_target`、`test_triggers`、`test_security_workflow_exists_and_is_separate`、`test_job_names_do_not_collide_with_required_check`） | 自動：`tests/ci_security_workflow_test.sh` |
| TC-013 | 範圍：檔案；完成標準 1 | 功能 | 修好的分支 | `git diff origin/v3 --stat`，並看 `security.yml` 的 diff | 只有三個檔案被改：`.github/workflows/security.yml`、`tests/ci_security_workflow_test.sh`、`specs/fix-pip-audit-workflow/ledger.md`；`security.yml` 只有 pip-audit 最後一行（1 行刪、1 行加） | 手動：驗收者執行 `git diff origin/v3 --stat` 與 `git diff origin/v3 -- .github/workflows/security.yml` |

## User Story 3 — 不在範圍：這次不做的事確實沒做（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 不做：不動 `gitleaks` 工作與 `.gitleaks.toml`（PR #380） | 不在範圍 | 修好的分支 | 比較 `security.yml` 的 gitleaks 工作與 `.gitleaks.toml` 和 base | `gitleaks` 工作零差異、`.gitleaks.toml` 零差異 | 手動：驗收者 `git diff origin/v3 -- .gitleaks.toml .github/workflows/security.yml` |
| TC-015 | 不做：不改 `tests.yml` | 不在範圍 | 修好的分支 | 比較 `.github/workflows/tests.yml` 與 base | 零差異 | 自動：`tests/ci_security_workflow_test.sh`（`test_existing_tests_yml_untouched`） |
| TC-016 | 不做：不改 `constraints.txt`、不新增 requirements 檔；範圍：`pyproject.toml` 不動 | 不在範圍 | 修好的分支 | `git diff origin/v3 --stat` | `platform/constraints.txt`、`platform/pyproject.toml` 零差異；沒有新增任何 `requirements*.txt` | 手動：驗收者 `git diff origin/v3 --stat` |
| TC-017 | 不做：不升級 pip-audit 版本 | 不在範圍 | 修好的分支 | 看安裝步驟 `pip install pip-audit==...` 與 base 的差異 | 仍是 `pip-audit==2.10.1`，該行零差異 | 手動：驗收者 `git diff origin/v3 -- .github/workflows/security.yml` |
| TC-018 | 不做：不刪那行、不改成只掃 `constraints.txt` | 不在範圍 | 修好的 `security.yml` | 在去掉註解的 workflow 找專案行 | 專案行仍在且指向 `./platform`（不是被刪掉，也不是被改成只掃 `constraints.txt`） | 自動：`tests/ci_security_workflow_test.sh`（`test_pip_audit_targets_both_files`、`test_pip_audit_project_line_has_no_no_deps`） |
| TC-019 | 不做：不把 security 設成必要檢查 | 不在範圍 | 修好的分支 | 比較 `docs/TESTING.md` 與 base；看工作名稱 | `docs/TESTING.md` 零差異（它寫 security 仍在觀察期）；工作名稱沒有與必要檢查撞名 | 手動：驗收者 `git diff origin/v3 -- docs/TESTING.md`；另 `tests/ci_security_workflow_test.sh`（`test_job_names_do_not_collide_with_required_check`）仍 `ok` |

## 憲法與安全網

<!-- 觸及：Development Workflow 與 Governance 的「受保護路徑」規則（constitution 約第 252 行、第 692 行）：改 `.github/` 要附「還會影響什麼」的證明，並經第二次對抗式審查才合併；以及「放寬 Safety Net 要維護者明確說好」——本件只增不減，不屬放寬。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | Governance：變更觸及受保護路徑 `.github/`，須附影響範圍證明且不放寬 Safety Net | 功能 | 修好的分支；本件風險等級 L | 驗收者列出這次變更**唯一**能影響的東西並實際跑一次證明（工作流觸發條件、權限、釘死的第三方 action、其他工作、`tests.yml` 都沒變）；比較掃描範圍與 base | 驗收報告的 `blastRadius` 有「只動 pip-audit 最後一行」的證明與指令輸出，不是 `unproven`；掃描範圍相對 base 只增不減（仍掃釘死版本，另外多掃專案宣告的依賴） | 手動：驗收者的 `blastRadius` 欄位；結構面由 `tests/ci_security_workflow_test.sh` 全部既有檢查 `ok` 佐證 |
