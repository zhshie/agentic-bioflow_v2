# Bug Assessment: a gate hook that times out or crashes lets the command run

- **Slug**: hooks-fail-open-on-timeout
- **Created**: 2026-10-10
- **Source**: issue #80 (security review of PR #79)
- **Verdict**: valid
- **Severity**: high (the whole Safety Net is skipped for that one command, silently)

## 給維護者

1. 安全關卡是 Claude Code 在執行指令前先跑的小程式。Claude Code 給它 30 秒。
2. 官方文件寫明：關卡如果超時、當掉、或回了看不懂的東西，Claude Code 預設「照樣執行指令」，不擋也不問。
3. 平常關卡不到一秒就答，但一條超長的指令在 main 上實測可以讓刪除關卡跑超過 100 秒——超時，指令就直接執行。
4. 修法：每個關卡加一個官方開關 `onFailure: "block"`：關卡出事時改成「擋下」。需要 Claude Code 2.1.295 以上（這台是 2.1.296）。

## Evidence

- Official docs, https://code.claude.com/docs/en/hooks (read 2026-10-10):
  - Timeouts: "A timed-out `command`, `http`, or `mcp_tool` hook doesn't block the tool call. The call continues through the normal permission flow, so don't count on a stalled hook to act as a gate. To block the call when a `command` or `http` hook times out, set `onFailure: "block"`."
  - "On most events, when a hook fails or times out, Claude Code still carries out the action ... To block the action instead, set `"onFailure": "block"` on a `command` or `http` hook. The default value is `"continue"`. Requires Claude Code v2.1.295 or later."
  - Failures: can't start; exit code other than 0 or 2; timeout; invalid output (JSON that can't be parsed or fails schema validation). Plain-text stdout is not a failure.
  - Not stated: behaviour on Claude Code < 2.1.295, and whether plugin hooks.json honours the field (same handler schema, no exception listed).
- `hooks/hooks.json` (main d1f2a1c): every PreToolUse entry (confirm_launch.sh ×3 matchers, confirm_cleanup.sh, guard_plugin_files.sh ×2, confirm_walkthrough.sh) has `"timeout": 30` and no `onFailure`.
- Security review of #79 (2026-10-10, native Git Bash): a ~32 KB command (long `cd` target + long `../`-heavy `rm` target) did not finish within 100 s on main's confirm_cleanup.sh.
- `grep -nE "exit [13-9]" hooks/*.sh`: no hook exits with a code other than 0 or 2 on purpose.

## Root Cause

The plugin relied on each hook answering in time; Claude Code's default for a hook that does not answer is to proceed.
