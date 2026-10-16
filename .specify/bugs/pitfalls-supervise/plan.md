# Plan: record the parallel-worktree pitfalls in docs/PITFALLS.md

- **Slug**: pitfalls-supervise
- **Created**: 2026-10-15
- **Why**: on 2026-10-14 the developer-agent ran two executors in parallel git worktrees for the first time (PRs #88, #89). Four things went wrong that the next person will hit again.

## 給維護者

1. 把這次平行開發踩到的四個坑寫進 `docs/PITFALLS.md`，照檔案現有的編號與格式加在最後。
2. 加一支小測試確認這四條真的寫進去了（每條檢查一個關鍵字），免得以後被誤刪。

## 四個坑（內容來源：developer-agent 2026-10-14 實跑紀錄）

1. **WSL 讀不到 Windows git 建的 worktree**：Windows 的 git 在 worktree 的 `.git` 檔裡寫絕對路徑 `gitdir: C:/Users/...`，WSL 裡的 git 讀不懂（`fatal: not a git repository`），所以要做暫存 clone 的測試在 WSL 全套裡會紅。解法：`git worktree add --relative-paths`（建立時）或 `git worktree repair --relative-paths`（事後），兩邊 git 都 ≥ 2.48 即可。關鍵字：`--relative-paths`。
2. **子 agent 開 PR／merge 會被 Claude Code 的 auto 模式分類器擋**：subagent 收到的指令不算使用者的要求，`gh pr create` 被判為「Unrequested Commit in a Connected App」、`gh pr merge` 被判為「Merge Without Review」。解法：push 交給子 agent，開 PR 與 merge 由主 session（developer-agent）做，並在工作區權限規則裡明確允許。關鍵字：`auto mode classifier`。
3. **全是人工判讀的測試案例會讓修正迴圈空轉**：verifier 回 UNVERIFIED 但沒有任何 FAIL／弱化測試／空殼時，再派 executor 修也不會變，只是重跑全套。解法：這種結果直接退給人判，不進修正輪。關鍵字：`UNVERIFIED`。
4. **筆電同時跑兩套 WSL 全套測試＋多個 agent 會記憶體吃緊**：背景指令曾被系統以低記憶體為由終止。筆電平行上限維持 2，常開桌機再升。關鍵字：`maxParallel`。

## 維護者的例子（原文）

- 「下次有人在 worktree 跑測試全紅，翻 PITFALLS 就要找得到 `--relative-paths`。」
- 「`bash tests/pitfalls_supervise_test.sh` 要綠。」

## Changes

1. `docs/PITFALLS.md`: append the four entries in the file's existing style and numbering, in English like the rest of the file, each with symptom → cause → fix, and each containing its keyword above.
2. `tests/pitfalls_supervise_test.sh` (exit-code pass/fail like the other tests, TC IDs in comments): asserts each of the four keywords appears in `docs/PITFALLS.md`. Red before change 1, green after.

## Out of scope

- Any other doc; the constitution; executor.md / verifier.md.
