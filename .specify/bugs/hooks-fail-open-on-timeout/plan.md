# Fix plan: hooks-fail-open-on-timeout (issue #80)

Tier A (Safety Net stricter). Touches `hooks/hooks.json` (protected path) → `/code-review` before merge.

## What changes

1. `hooks/hooks.json`: add `"onFailure": "block"` to every PreToolUse gate entry (confirm_launch.sh in all three matchers, confirm_cleanup.sh, guard_plugin_files.sh in both matchers, confirm_walkthrough.sh). Not to SessionStart / Stop / UserPromptSubmit / PostToolUse hooks (intro, next-step): a failure there must not block the session.
2. Audit every gate hook for paths that would now count as a failure and block ordinary commands: exit codes other than 0/2, stdout JSON that is malformed or fails Claude Code's schema, a missing interpreter. Each such path found is either fixed (exit 0 with no output where "not my business" is meant) or listed in fix.md as intended (refusal). The jq-missing path already exits 2 by design.
3. Minimum version: state in README/docs (where the plugin's requirements are listed) that the gates fail closed only on Claude Code ≥ 2.1.295, and have `hooks/session_start.sh` print one line when the running Claude Code is older, if the version is available to it (check what SessionStart receives; if not available, docs only). No behaviour change for older versions beyond the message.
4. Test `tests/hooks_fail_closed_test.sh`: parse hooks.json (python3 or jq — run_all already requires both) and assert (a) every PreToolUse command entry has onFailure "block", (b) no non-PreToolUse entry has it, (c) every PreToolUse command entry still has a timeout. Add to constitution checks only if the constitution names such a check (do not amend the constitution here).
5. Per-segment bounding of confirm_cleanup.sh (so the hook answers before 30 s instead of being blocked) is out of scope — with onFailure block a timeout is a block, which is safe; usability of 100 KB commands is not a priority. Note it in fix.md.

## Tests (RED first)

- `tests/hooks_fail_closed_test.sh` fails on main (no onFailure), passes after.
- Full suite green.

## Out of scope

- Bounding confirm_cleanup.sh's per-segment cost (follow-up if ever needed).
- Constitution text.
- Non-gate hooks.

## Done when

All PreToolUse gate entries carry onFailure "block"; audit finds no ordinary command that a gate fails on; version note in docs; test green; CI green; verifier ACCEPT; `/code-review` clean.
