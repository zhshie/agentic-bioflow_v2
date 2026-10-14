# Bug Assessment: run_all.sh header comment hard-codes a stale test-file count

- **Slug**: run-all-count
- **Created**: 2026-10-13
- **Source**: developer-agent, found while auditing tests/ for the supervise workflow
- **Verdict**: valid
- **Severity**: low (documentation only; the verdict logic already counts files at run time via `expected=$(grep -c . <<<"$FILES")`)

## 給維護者

1. `tests/run_all.sh` 開頭的說明寫「there are 39 test files」「verified across all 39」「"39 passed" means nothing…」，但現在 `bash tests/run_all.sh --list` 列出 94 支。數字寫死在註解裡，每加一支測試就過時一次。
2. 這只是文件錯，跑測試的判定沒有錯（它每次都重新數）。
3. 修法：註解不要寫數字，改成「every `*.sh` test file in this directory, counted at run time」；並加一支小測試，確認 `run_all.sh --list` 列出來的檔案數等於 `tests/` 底下除了 `run_all.sh` 以外的 `.sh` 檔實際數量，而且註解裡不再出現寫死的數字。

## 維護者的例子（原文）

- 「我打開 tests/run_all.sh，開頭不該告訴我一個錯的數字；要嘛寫對、要嘛不寫數字。」
- 「我跑 `bash tests/run_all.sh --list | wc -l`，數字要跟 `ls tests/*.sh | grep -v run_all.sh | wc -l` 一樣。」

## Reproduction

```
$ grep -n '39' tests/run_all.sh | head
4:# Why this exists: there are 39 test files ...
11:# ... "39 passed" means nothing ...
15:# all 39), so the verdict rests on that ...
$ bash tests/run_all.sh --list | wc -l
94
```

## Root Cause (high confidence)

The header comment was written when the suite had 39 files and was never updated; nothing checks it.

## Proposed Remediation

- Rewrite the header lines (the leading comment block, before `set -uo pipefail`) so they describe the mechanism ("every `.sh` here except run_all.sh, counted at run time; the banner prints the count") with no literal file count in lines 1–20 of the file. The historical remark about the native Git Bash run ("23 of 40 files failed") sits below line 20 and may be left as is.
- Add `tests/run_all_count_test.sh` (pass/fail by exit code like every other test, with the TC ID in a comment) that asserts: (a) `bash tests/run_all.sh --list` prints exactly as many lines as there are `tests/*.sh` files other than `run_all.sh`; (b) lines 1–20 of `tests/run_all.sh` contain no standalone integer ≥ 10. (b) must be red on current main before the fix; (a) may already pass today — say so in the ledger.
- Out of scope: run_all.sh behaviour or exit codes; other test files.
- Note for the executor: `tests/run_all.sh --list` works in Git Bash as well as WSL; the full suite still runs only in WSL.
