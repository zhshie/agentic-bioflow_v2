# Bug Assessment: with jq missing or broken, the launch and walkthrough gates miss a launch on a later line

- **Slug**: jq-broken-later-line
- **Created**: 2026-10-05
- **Source**: independent acceptance of `fix/gates-audit2` (item 3)
- **Verdict**: valid
- **Severity**: high (a `tw launch` passes with nothing printed)

## 給維護者

1. 沒有 jq（或 jq 壞掉）時，送出分析的關卡只能看原始文字，看起來像 `tw launch` 就擋。
2. 但多行指令在原始文字裡，換行是寫成兩個字元 `\n`，第二行的 `tw` 前面黏著一個 `n`，變成 `ntw`，於是第二行以後的送出完全看不到、直接放行。
3. 刪除關卡在這個分支已經修過同一個洞（jq-broken-cleanup）；這次把同樣的修法搬到送出關卡與導覽關卡。

## Reproduction (WSL, 41d8f9b)

Bash command `echo ok` + newline + `tw launch nf-core/rnaseq`, with a jq first on PATH that:

| jq | confirm_launch | Should be |
|---|---|---|
| exits 127 | pass | BLOCKED (exit 2) |
| prints `{}` | pass | BLOCKED |
| prints a line of text | pass | BLOCKED |
| exits 3 | pass | BLOCKED |

The same command on one line is BLOCKED in all four. `hooks/confirm_walkthrough.sh` has the same raw scan.

Constitution: invariant 13 ("With jq missing or broken, the gates refuse what they cannot rule out from the raw text"); Safety Net, "A launch command ... waits for explicit confirmation".

## Root Cause (high confidence)

`looks_launch_shaped` (`hooks/confirm_launch.sh`) and `looks_managed_write_shaped` (`hooks/confirm_walkthrough.sh`) fold real line breaks and JSON punctuation to spaces, but not the JSON escapes `\n`, `\t`, `\r`, which is how a line break appears in the raw input.

## Proposed Remediation

- As in `looks_delete_shaped`: the escapes `\n`, `\t`, `\r` are separators, and if `sed`/`tr` cannot run the text counts as shaped (fail closed).
- Tests first in the jq-broken-gates section of `tests/gate_output_failclosed_test.sh`: the two-line launch through each of the four jq shims, for both gates; an unrelated two-line command still passes.
