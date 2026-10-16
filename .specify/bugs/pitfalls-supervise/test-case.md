# 測試案例：把平行開發的四個坑寫進 docs/PITFALLS.md

**規格**：`.specify/bugs/pitfalls-supervise/plan.md`（chore，沒有 spec.md；以計畫的「四個坑」「Changes」「Out of scope」「維護者的例子」為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：缺東西、被誤刪時，系統怎麼反應（測試要變紅）。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

驗證方式說明：「自動」＝跑 `bash tests/pitfalls_supervise_test.sh`（計畫要求新增的小測試，只檢查關鍵字有沒有出現）。「手動」＝驗收者直接讀 `docs/PITFALLS.md` 或 `git diff` 對照計畫；關鍵字測試看不出內容對不對，所以內容類案例不能只靠它。

## User Story 1：下次有人在 worktree 跑測試全紅，翻 PITFALLS 就找得到答案（優先度 P1）

維護者的原話：「下次有人在 worktree 跑測試全紅，翻 PITFALLS 就要找得到 `--relative-paths`。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 維護者例子 1；坑 1；Changes 1 | 功能 | `docs/PITFALLS.md` 已加入新條目 | 在 `docs/PITFALLS.md` 搜尋 `--relative-paths`（逐字、當成普通文字，不是指令選項） | 找得到，而且出現在講「WSL 讀不到 Windows git 建的 worktree」的那一條裡 | 自動：`tests/pitfalls_supervise_test.sh` |
| TC-002 | 坑 2；Changes 1 | 功能 | 同上 | 搜尋 `auto mode classifier`（逐字） | 找得到，出現在講「子 agent 開 PR／merge 被擋」的那一條裡 | 自動：`tests/pitfalls_supervise_test.sh` |
| TC-003 | 坑 3；Changes 1 | 功能 | 同上 | 搜尋 `UNVERIFIED`（逐字、大小寫相同） | 找得到，出現在講「全是人工判讀的測試案例讓修正迴圈空轉」的那一條裡 | 自動：`tests/pitfalls_supervise_test.sh` |
| TC-004 | 坑 4；Changes 1 | 功能 | 同上 | 搜尋 `maxParallel`（逐字） | 找得到，出現在講「筆電同時跑兩套 WSL 全套測試記憶體吃緊」的那一條裡 | 自動：`tests/pitfalls_supervise_test.sh` |
| TC-005 | 坑 1 內容 | 功能 | 同上 | 讀坑 1 的條目 | 症狀：Windows 的 git 在 worktree 的 `.git` 檔寫絕對路徑 `gitdir: C:/Users/...`，WSL 裡的 git 回 `fatal: not a git repository`，要做暫存 clone 的測試在 WSL 全套會紅。解法：建立時用 `git worktree add --relative-paths`、事後用 `git worktree repair --relative-paths`，兩邊 git 都 ≥ 2.48 | 手動：驗收者對照計畫「坑 1」讀 `docs/PITFALLS.md` |
| TC-006 | 坑 2 內容 | 功能 | 同上 | 讀坑 2 的條目 | 症狀：subagent 收到的指令不算使用者的要求，`gh pr create` 被判為「Unrequested Commit in a Connected App」、`gh pr merge` 被判為「Merge Without Review」。解法：push 交給子 agent，開 PR 與 merge 由主 session（developer-agent）做，並在工作區權限規則裡明確允許 | 手動：驗收者對照計畫「坑 2」讀 `docs/PITFALLS.md` |
| TC-007 | 坑 3 內容 | 功能 | 同上 | 讀坑 3 的條目 | 症狀：verifier 回 UNVERIFIED，但沒有任何 FAIL、弱化測試、空殼，再派 executor 修也不會變，只是重跑全套。解法：這種結果直接退給人判，不進修正輪 | 手動：驗收者對照計畫「坑 3」讀 `docs/PITFALLS.md` |
| TC-008 | 坑 4 內容 | 功能 | 同上 | 讀坑 4 的條目 | 症狀：筆電同時跑兩套 WSL 全套測試加多個 agent 時記憶體吃緊，背景指令曾被系統以低記憶體為由終止。解法：筆電平行上限維持 2，常開桌機再升 | 手動：驗收者對照計畫「坑 4」讀 `docs/PITFALLS.md` |
| TC-009 | Changes 1（「各含 症狀→原因→解法」） | 功能 | 同上 | 逐條檢查四個新條目 | 每一條都依序交代症狀、原因、解法，三樣都在，且用英文寫（跟檔案其他條目一致） | 手動：驗收者讀 `docs/PITFALLS.md` |
| TC-010 | Changes 1（「照檔案現有的編號與格式加在最後」） | 功能 | 檔案原本最後一條是 45 | 看新條目的位置與標題 | 四條接在 45 之後，依序編為 46、47、48、49，標題格式與既有條目相同（`**N. 標題。**`），不插在中間、不重編舊號 | 手動：驗收者讀 `docs/PITFALLS.md` 與 `git diff` |

## User Story 2：有一支小測試，免得這四條以後被誤刪（優先度 P1）

維護者的原話：「`bash tests/pitfalls_supervise_test.sh` 要綠。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 維護者例子 2；Changes 2 | 功能 | 四個條目已加入 | 執行 `bash tests/pitfalls_supervise_test.sh` | 結束碼 0（綠） | 自動：`tests/pitfalls_supervise_test.sh` |
| TC-012 | Changes 2（「結束碼判斷成敗，TC 編號寫在註解」） | 功能 | 測試檔已建立 | 讀 `tests/pitfalls_supervise_test.sh` | 以結束碼表示成敗（跟 `tests/` 其他測試一樣，`tests/run_all.sh` 會自動收進去跑）；註解標出對應的 TC 編號；四個關鍵字各自一項檢查 | 手動：驗收者讀測試檔 |
| TC-013 | Changes 2（「改動前是紅的」） | 例外 | 把 `docs/PITFALLS.md` 換回改動前的版本（`main` 上的那份） | 對這份舊檔執行同一支測試 | 結束碼不為 0（紅），並指出缺的是哪些關鍵字；也就是測試不是永遠綠 | 手動：驗收者在 `main` 的檔案上跑測試 |
| TC-014 | Changes 2（「每條檢查一個關鍵字」） | 例外 | 新版 `docs/PITFALLS.md` 的暫存複本 | 每次從複本刪掉一個關鍵字（共四次，各刪 `--relative-paths`、`auto mode classifier`、`UNVERIFIED`、`maxParallel` 之一），對複本跑測試 | 四次都變紅，且各自點名被刪的那一個；刪一個不會被另外三個蓋過 | 手動：驗收者用暫存複本重現（不動原檔） |

## 不在範圍

計畫的「Out of scope」：任何其他文件、憲法、executor.md／verifier.md。另外「加在最後」代表舊的 1～45 條不動。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 不在範圍：其他文件 | 不在範圍 | 改動已完成 | 看 `git diff main...HEAD --stat` | 動到的檔案只有 `docs/PITFALLS.md`、`tests/pitfalls_supervise_test.sh`，以及 `.specify/bugs/pitfalls-supervise/` 底下的流程紀錄；`docs/TESTING.md`、`README`、`docs/PRINCIPLES.md` 等其他文件一個字都沒變 | 手動：驗收者讀 diff |
| TC-016 | 不在範圍：憲法 | 不在範圍 | 同上 | 看 diff 有沒有碰 `.specify/memory/constitution.md` | 沒有任何改動 | 手動：驗收者讀 diff |
| TC-017 | 不在範圍：executor／verifier | 不在範圍 | 同上 | 看 diff 有沒有碰 `.claude/agents/executor.md`、`.claude/agents/verifier.md` | 沒有任何改動（四個坑只記在 PITFALLS，沒有順手改這兩個角色的規則） | 手動：驗收者讀 diff |
| TC-018 | 「加在最後」；不改舊條目 | 不在範圍 | 同上 | 看 `docs/PITFALLS.md` 的 diff | 只有新增行，且全在檔案最後；舊的 1～45 條沒有任何刪除或修改 | 手動：驗收者讀 diff |

## 憲法與安全網

這次只動文件與一支只讀文字的測試，不碰 Safety Net 與任何 hook；唯一牽涉的是第 8 條（證據先於主張：PITFALLS 的每一條都要對應真實發生過的失敗）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | IV.8（Procedure P2） | 功能 | 四個新條目已加入 | 依 `docs/TESTING.md` 的 Procedure P2 逐條檢查 | 每條都指向一個真實看到的失敗（具體指令或訊息，如 `fatal: not a git repository`、`gh pr create` 被判的名稱、背景指令被低記憶體終止），而不是「我們認為會…」的推測；內容與計畫的 developer-agent 2026-10-14 實跑紀錄一致，沒有計畫以外的新主張 | 手動：`docs/TESTING.md` Procedure P2 |
