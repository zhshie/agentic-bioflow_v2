# Bug Assessment: scratch clones inherit a main ref when the suite runs on main

- **Slug**: scratch-clone-main
- **Created**: 2026-10-15
- **Source**: CI run 38411212391 (push to main after #87): `constitution_scope_test.sh` 100/101, failing case "scratch clone really has no main ref". PR runs are green.
- **Verdict**: valid
- **Severity**: medium (main's CI is red on every push, which hides real regressions)

## 給維護者

1. main 每次合併後的 CI 都會紅一條，但不是程式壞了，是測試本身的假設錯了。
2. 那條測試要做一個「沒有 main 分支」的暫存副本來檢查 issue #71；可是當 CI 就是在 main 上跑時，`git clone` 會自動帶出 main 分支，於是「確認沒有 main」必敗。在 PR 上跑時不是 main，所以 PR 都綠。
3. 修法：做完暫存副本後，如果副本裡有 main 分支（而這次不要 main），就先切成「不在任何分支上」再把 main 刪掉。另一支 `platform_direction_docs_test.sh` 用同一個做副本的寫法，一起修。

## 維護者的例子（原文）

- 「main 合併完，CI 要綠；不能因為在 main 上跑就紅。」
- 「在 PR 上跑，結果跟現在一樣綠。」

## Reproduction

In any checkout whose current branch is `main`: `bash tests/constitution_scope_test.sh` → `scratch clone really has no main ref  FAIL`. Cause: `mkclone()` (tests/constitution_scope_test.sh:156-163) runs `git clone -q --depth 1 --no-local "file://$ROOT"`; the clone checks out the source's HEAD branch, so when that branch is `main` the clone has `refs/heads/main`.

## Root Cause (high confidence)

`mkclone` assumes the clone has no `main` ref unless `withmain` is passed. That holds only when the source checkout is not on `main` (PR merge refs are detached in CI).

## Proposed Remediation

- In `mkclone` of `tests/constitution_scope_test.sh`: after the clone, when `withmain` is NOT requested, run `git -C "$d" checkout -q --detach` and then delete `refs/heads/main` if it exists (`git -C "$d" branch -D main` guarded by `show-ref`). When `withmain` IS requested, keep today's behaviour (create `main` at HEAD if missing).
- Apply the same guard to the equivalent clone helper in `tests/platform_direction_docs_test.sh` (around line 107) if it relies on the absence of `main`; if it does not, leave its behaviour unchanged and say so in the ledger.
- Red first: reproduce by running the test from a scratch checkout whose branch is named `main` (e.g. clone the repo to a temp dir, `git checkout -B main`, run the test there) and record the FAIL in the ledger; then the fix turns it green. Do not weaken or delete any assertion.
- Out of scope: the fingerprint logic, PINNED_SN_SHA256, the constitution itself, CI configuration.
