# Fix: gate-emit-empty-object

- **Branch**: `fix/gates-audit2` (RED 298ac9b, GREEN 1cd7634)
- **Changed**: `abf_emit` in `hooks/confirm_launch.sh`, `hooks/confirm_walkthrough.sh`, `hooks/guard_plugin_files.sh`; `tests/gate_output_failclosed_test.sh` (8 cases).

## What changed

The three `abf_emit`s take `hooks/confirm_cleanup.sh`'s check: jq's output is printed only when it carries `hookSpecificOutput`, `hookEventName` `PreToolUse`, the decision asked for, and `additionalContext` when one was given; otherwise the fixed minimal ask.

## Evidence (WSL)

| jq shim (on `-n`) | launch | cleanup | walkthrough | plugin-file guard |
|---|---|---|---|---|
| prints `{}` | `{}` -> ask | ask -> ask | `{}` -> ask | `{}` -> ask |
| prints a flat verdict, no `hookSpecificOutput` | none -> ask | ask -> ask | none -> ask | none -> ask |

RED: 6 failures; GREEN: all passed.

**Pinning cleanup's check**: mutation M8 of the acceptance (`abf_accept_A/mutate.py`: the first line of cleanup's check back to `[[ $o == '{'* ]]`) now fails `gate_output_failclosed_test.sh` ("jq builds 'flat': deletion guard", got none). Before, `{}` was still caught by the decision line, so the mutation left every test green; the flat shim carries a decision but no `hookSpecificOutput`.
