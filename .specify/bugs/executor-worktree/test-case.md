# 測試案例：executor 到派工訊息指定的 worktree 裡工作（executor-worktree）

<!--
Written by the verifier (CONTRACT mode). Chore, no spec.md: the ground truth is the two
maintainer examples quoted verbatim in .specify/bugs/executor-worktree/plan.md
(section "維護者的例子（原文）"). No expected behaviour here goes beyond what that plan states.
-->

**規格**：`.specify/bugs/executor-worktree/plan.md`（沒有 spec.md，這是例行維護）　**總覽**：`test-case-overview.md`

名詞：worktree＝同一個 repo 的另一份工作資料夾（和主副本各自一份檔案、各自一個分支），派工訊息會給它的路徑。主副本＝`C:/Users/ACER/Desktop/agentic-bioflow/agentic-bioflow_v2`。`executor.md`＝`.claude/agents/executor.md`，executor 的工作說明。

維護者的兩個例子（原文，下面的 TC 直接用）：

- 例 1：「我派工時寫『worktree 在 C:/…/wt/foo』，executor 要在那個資料夾裡改、在那個資料夾裡跑測試，不要跑回主副本。」
- 例 2：「`bash tests/dev_workflow_test.sh` 要多一行 ok，寫 executor 會到指定的 worktree 工作。」

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

說明：這次改的是一份說明文件和一條「文件裡有沒有這個字」的檢查，所以 US1 的內容是否寫對，由驗收者讀 `executor.md` 判斷（見總覽「不確定的地方」第 1 點）；US2 才是會自動跑的檢查。

## User Story 1 — executor 的說明寫明：派工給了 worktree 路徑就在那裡工作（優先度 P1）

對應 plan「Changes」第 1 點與維護者例 1。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | plan Changes 1（「What you are given」加一條）；例 1 | 功能 | 改完後的 `executor.md` | 讀「What you are given」一節 | 派工訊息會給的東西清單裡多了一條，寫明「可以另外給一個 worktree 路徑」，且是選填（沒給也成立） | 手動：驗收者讀 `.claude/agents/executor.md` 與 `git diff` |
| TC-002 | plan Changes 1；例 1「在那個資料夾裡改」 | 功能 | 同上 | 讀那一條 | 寫明：給了 worktree 路徑，第一步就 `cd` 到那裡 | 手動：同上 |
| TC-003 | plan Changes 1；例 1「在那個資料夾裡改、在那個資料夾裡跑測試」 | 功能 | 同上 | 讀那一條 | 寫明：之後所有 git 指令和測試指令都在那個路徑裡跑 | 手動：同上 |
| TC-004 | plan Changes 1；例 1「不要跑回主副本」 | 功能 | 同上 | 讀那一條 | 寫明：絕不碰主副本 | 手動：同上 |
| TC-005 | plan Changes 1（「Running the full suite」）；例 1「在那個資料夾裡跑測試」 | 功能 | 同上 | 讀「Running the full suite」裡 WSL 的全套測試指令 | 寫明：給了 worktree 時，指令裡的 `/mnt/c/<path>` 就是那個 worktree 的路徑（不是主副本路徑） | 手動：同上 |
| TC-006 | plan「Nothing is wrong when there is one checkout」；Changes 1 的「optionally」 | 例外 | 派工訊息沒給 worktree 路徑 | 讀改完後的 `executor.md` | 原本的做法照舊寫著：檢查出指定分支、WSL 指令用 `/mnt/c/<path to repo>`；新增的是「選填」，沒有把原本只有一份工作副本的情況改掉 | 手動：驗收者讀 `git diff`，原有那幾行只被補充、沒被刪 |

## User Story 2 — 有一條測試守住這件事（優先度 P1）

對應 plan「Changes」第 2 點與維護者例 2。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | plan Changes 2；例 2 | 功能 | 改完後的分支 | 跑 `bash tests/dev_workflow_test.sh` | 輸出裡多出一行 `executor: works in the worktree the dispatcher names ... ok`，最後印 `all passed`，結束碼 0 | 自動：`tests/dev_workflow_test.sh` |
| TC-008 | 例 2「要多一行 ok」 | 功能 | main 與改完後的分支各跑一次 `bash tests/dev_workflow_test.sh` | 數輸出裡的 `ok` 行 | 分支的 ok 行數＝main 的 ok 行數 + 1，main 上原有的每一行在分支上仍是 ok | 自動：`tests/dev_workflow_test.sh` |
| TC-009 | plan Changes 2「It must fail on current main」 | 例外 | `executor.md` 還是 main 的版本（沒有 `worktree` 這個字），測試檔已加上新那一行 | 跑 `bash tests/dev_workflow_test.sh` | 新那一行印 `FAIL: ... lacks 'worktree'`，整份測試結束碼 1；也就是這條測試在沒有改文件時會紅（commit 紀錄要有 `RED:` 在前、`GREEN:` 在後） | 自動：`tests/dev_workflow_test.sh`（驗收者在 main 的 `executor.md` 上重跑一次，並看 commit 順序） |
| TC-010 | plan「Never weaken a test」；Changes 2 只「add」一行 | 例外 | 改完後的分支 | 比對 `tests/dev_workflow_test.sh` 與 main 的差異 | 只新增那一行（`has "executor: works in the worktree the dispatcher names" "$EX" "worktree"`）；沒有刪、改、跳過或放寬任何既有檢查 | 手動：驗收者讀 `git diff main...HEAD -- tests/dev_workflow_test.sh` |

## 憲法與安全網

涉及的規則：憲法 Development Workflow 的「Green at every stage」與「Roles」（executor 不收工直到全套綠燈、不能派別的 agent）。plan 說這些「原樣」不動。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | plan「Keep the frontmatter unchanged」；executor 的 Stop 關卡與不能派 agent | 例外 | 改完後的分支 | 跑 `bash tests/dev_workflow_test.sh`，看三條既有的 executor 檢查 | `executor: has a Stop gate in frontmatter`、`executor: cannot dispatch agents`、`executor: gate holds on a repeated stop attempt`、`executor: never weakens a test` 四行都是 ok；`executor.md` 開頭兩條 `---` 之間的內容與 main 逐字相同 | 自動：`tests/dev_workflow_test.sh`；frontmatter 相同由驗收者讀 diff |
| TC-012 | plan「不改 executor 的其他規則」 | 例外 | 改完後的分支 | 讀 `git diff main...HEAD -- .claude/agents/executor.md` | 改動只落在「What you are given」與「Running the full suite」兩節；「How to work」「You must never」「Finishing」「Report format」的文字與 main 逐字相同 | 手動：驗收者讀 diff |
| TC-013 | Green at every stage | 功能 | 全部改動已 commit | 在 WSL 或 Linux 跑 `bash tests/run_all.sh` | 全部通過，沒有任何一支變紅（原本綠的仍然綠） | 自動：`tests/run_all.sh`（驗收者看 executor 報告的 commit 與 CI 結果相符） |

## 不在範圍

plan「Out of scope」：verifier.md、憲法、Stop hook 腳本、run_all.sh。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | plan Out of scope：verifier.md | 不在範圍 | 改完後的分支 | `git diff main...HEAD --stat` | 沒有 `.claude/agents/verifier.md` | 手動：驗收者看 diff |
| TC-015 | plan Out of scope：the constitution | 不在範圍 | 同上 | 同上 | 沒有 `.specify/memory/constitution.md` | 手動：同上 |
| TC-016 | plan Out of scope：the Stop hook script | 不在範圍 | 同上 | 看 `executor.md` 的 diff | `hooks:` 下 Stop 那段指令（含 `exit 2` 與 `executor-status` 判斷）沒有任何改動 | 手動：同上 |
| TC-017 | plan Out of scope：run_all.sh | 不在範圍 | 同上 | `git diff main...HEAD --stat` | 沒有 `tests/run_all.sh` | 手動：同上 |
| TC-018 | plan「Changes」只列兩個檔 | 不在範圍 | 同上 | `git diff main...HEAD --stat` | 動到的檔只有 `.claude/agents/executor.md`、`tests/dev_workflow_test.sh`，加上 `.specify/bugs/executor-worktree/` 底下的紀錄檔；沒有其他檔，且 `spec.md`、`test-case*.md` 在實作期間沒被改 | 手動：同上 |
