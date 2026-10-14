# Plan: executor works inside the worktree the dispatcher names

- **Slug**: executor-worktree
- **Created**: 2026-10-13
- **Why**: the new `supervise` workflow (workspace `.claude/workflows/supervise.js`) runs several executors in parallel, each in its own `git worktree` under a path the dispatcher passes in the prompt. `executor.md` today assumes the main checkout: it says "check out the branch" and gives the WSL test command with `/mnt/c/<path to repo>`. Nothing is wrong when there is one checkout, but with worktrees an executor that `cd`s to the main checkout would edit the wrong tree and trip the "two runs on the same checkout" corruption the file itself warns about.

## 給維護者

1. 以後 executor 可能被叫到「repo 的某一份工作副本（worktree）」裡做事，不一定是主副本。要在它的說明裡加兩句：派工訊息若給了 worktree 路徑，第一步就 `cd` 過去，之後所有 git 與測試指令都在那裡跑；WSL 的全套測試指令也用那個路徑。
2. 加一條測試，確認 executor.md 真的寫了這件事（跟現有 `tests/dev_workflow_test.sh` 其他條目同一個樣式）。
3. 不改 executor 的其他規則（Stop 關卡、不准派 agent、不准弱化測試都原樣）。

## 維護者的例子（原文）

- 「我派工時寫『worktree 在 C:/…/wt/foo』，executor 要在那個資料夾裡改、在那個資料夾裡跑測試，不要跑回主副本。」
- 「`bash tests/dev_workflow_test.sh` 要多一行 ok，寫 executor 會到指定的 worktree 工作。」

## Changes

1. `.claude/agents/executor.md`, section "What you are given": add a bullet — *optionally, a worktree path: if given, `cd` there first; every git and test command below runs in that path, and you never touch the main checkout.* Section "Running the full suite": say the `/mnt/c/<path>` is the worktree's path when one was given. Keep the frontmatter unchanged (the test checks it).
2. `tests/dev_workflow_test.sh`: add `has "executor: works in the worktree the dispatcher names" "$EX" "worktree"` next to the other executor checks. It must fail on current main (the word `worktree` does not appear in executor.md) and pass after change 1.

## Out of scope

- verifier.md, the constitution, the Stop hook script, run_all.sh.
