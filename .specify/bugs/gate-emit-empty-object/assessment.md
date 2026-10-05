# Bug Assessment: a jq that builds `{}` as the verdict turns three gates permissive

- **Slug**: gate-emit-empty-object
- **Created**: 2026-10-05
- **Source**: independent acceptance of `fix/gates-audit2` (item 4)
- **Verdict**: valid
- **Severity**: high (a launch, a samplesheet write and a write into the plugin pass; Claude Code reads `{}` as "no decision")

## 給維護者

1. 每道關卡最後都用 jq 組出「要問使用者／拒絕」的回覆。如果 jq 讀得懂輸入、但組回覆時只吐出 `{}`，關卡就把 `{}` 原樣印出去——`{}` 沒有任何決定，等於放行。
2. 刪除關卡在這個分支已經改成「回覆裡要有該有的欄位才印，否則印固定的『請確認』」；送出關卡、導覽關卡、外掛檔案保護這三道還沒改。
3. 另外，刪除關卡的這個檢查目前沒有測試真正釘住：把它改回舊的寬鬆寫法，測試仍全綠。這次補一個會抓到的測試。

## Reproduction (WSL, 41d8f9b; jq shim that prints `{}` whenever `-n` is among its arguments, real jq otherwise)

| Gate, call | Verdict | Should be |
|---|---|---|
| confirm_launch, `tw launch nf-core/rnaseq` | `{}` (proceeds) | ask |
| confirm_walkthrough, Write `analysis/de.R` | `{}` (proceeds) | the gate's verdict or the fixed ask |
| guard_plugin_files, Write into the plugin's hooks/ | `{}` (proceeds) | ask or deny |
| confirm_cleanup, `rm -rf …/results` | ask (fixed) | ask |

A shim that prints `{"x":1}` gives the same.

Constitution: invariant 13 ("never silently permissive"); Safety Net (launch confirmation).

## Root Cause (high confidence)

`abf_emit` in `hooks/confirm_launch.sh`, `hooks/confirm_walkthrough.sh` and `hooks/guard_plugin_files.sh` accepts jq's output when it starts with `{`. `hooks/confirm_cleanup.sh` requires `hookSpecificOutput`, `hookEventName: PreToolUse`, the decision asked for and the context when one was given.

## Proposed Remediation

- Port cleanup's check to the three `abf_emit`s.
- Tests first in `tests/gate_output_failclosed_test.sh`: the `{}` shim and a shim that builds a verdict without `hookSpecificOutput` (it carries the decision at the top level, which Claude Code ignores), for all four gates. The second shim is what pins cleanup's `hookSpecificOutput` check: with only the decision check left, `{}` was still caught, so reverting the first line of the check left every test green.
