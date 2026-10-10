# Fix: hooks-fail-open-on-timeout

- **Branch**: `fix/80-hooks-fail-closed` (contract 1d81ca7, RED e20aebe, GREEN below)
- **Changed**: `hooks/hooks.json`; new `tests/hooks_fail_closed_test.sh` (TC-001..007), `tests/gate_exit_contract_test.sh` (TC-010..015, TC-C02); `README.md` (Requirements); `docs/TESTING.md` (steps for TC-008, 009, 019, 020, 023..025, C01).
- **Not changed**: the constitution, any existing test. `hooks/confirm_launch.sh`, `hooks/confirm_cleanup.sh`, `hooks/in_use.sh` changed only for the review-round array guards below.

## What changed

- All seven PreToolUse command entries (`confirm_launch.sh` x3 matchers, `confirm_cleanup.sh`, `guard_plugin_files.sh` x2, `confirm_walkthrough.sh`) carry `"onFailure": "block"`. Timeouts stay 30. SessionStart, Stop, UserPromptSubmit and PostToolUse entries are untouched.
- README "Requirements" says fail-closed needs Claude Code 2.1.295 or later and that older versions are undocumented and unverified.

## Audit: gate paths that exit other than 0 or 2

None found, so no `hooks/*.sh` changed. The new contract test runs the four gates over 7 ordinary calls, 18 odd inputs (empty, `{}`, no `tool_input`, no `session_id`, no `cwd`, non-JSON, `tool_input` a number / null / array, `command` a number, `file_path` null, no `tool_name`, `session_id` a number, a missing cwd, a missing transcript, top-level array / null), a 28 KB not-in-use `cd`+`rm ../..` command, a 1 MB Write and a 37 KB harmless command, with a python3 stub that exits 9009 first on PATH. All exit 0, stdout empty or valid hook JSON. The test passes on main as well as on the branch; only `hooks_fail_closed_test.sh` was red before the change. An ad-hoc run of about 60 command shapes (deletes, launches, heredocs, unbalanced quotes, `eval`, PowerShell verbs) through all four gates, as Bash and as Write, with and without an environment (`env -i`), also found no exit 1.
The `set -u` lines named in the task (`confirm_walkthrough.sh:48`, `guard_plugin_files.sh:58`) did not produce an unbound-variable exit on any input tried.


`confirm_walkthrough.sh` prints `hookSpecificOutput` with only `additionalContext` (no `permissionDecision`) for a launch it lets through. That is valid hook output; the contract test accepts it.

## SessionStart version line (TC-021, TC-022): not added

The docs (https://code.claude.com/docs/en/hooks, read 2026-10-10) list SessionStart input as the common fields (`session_id`, `transcript_path`, `cwd`, ...) plus `source`, and optionally `model`, `agent_type`, `session_title`. No Claude Code version. So `hooks/session_start.sh` cannot know it is running under an old Claude Code; docs only. `hooks/session_start.sh` is unchanged, so its output is identical to main.

## Known costs

1. **A broken install or a hook that cannot start now blocks Bash, Write and Edit in every project.** Claude Code runs the plugin's gates in every session, including ones that never use the plugin. Before, a gate that crashed let the command through; now a crash, a missing interpreter, a bad exit code or unreadable output stops the call. The escape is disabling or repairing the plugin.
2. **Delete shapes that make `confirm_cleanup.sh` slow now time out into a block.** A ~32 KB command in an in-use session (long `cd` target plus a long `../`-heavy `rm` target) ran past 100 s on main. It is no longer let through at 30 s; it is blocked. Not-in-use sessions answer in well under a second, so other projects are not affected (TC-014).
3. **Older Claude Code**: below 2.1.295 the behaviour is unverified. The gates may keep failing open, or the unknown field may be ignored or rejected. Documented in the README; not tested.
4. **Plugin `hooks.json` honouring `onFailure`** is not stated by the docs (same handler schema, no exception listed). The manual steps TC-009 / C01 in `docs/TESTING.md` check it on the installed plugin. Not done by the executor.

## Follow-up (out of scope, TC-023)

Bound `confirm_cleanup.sh`'s per-segment cost so a 32 KB delete shape is judged within 30 s instead of being blocked by the timeout. No length or depth cap was added here.

## RED / GREEN

RED e20aebe: `tests/hooks_fail_closed_test.sh` fails 4 checks (TC-001..004); `tests/gate_exit_contract_test.sh` passes (no exit-1 path exists). GREEN: `hooks/hooks.json` plus docs; both pass.

## Review round 1: empty arrays under `set -u` (bash 3.2 / before 4.4)

The security review found that on macOS `/bin/bash` 3.2 (and bash before 4.4) `"${a[@]}"` over an EMPTY array under `set -u` is a fatal "unbound variable", exit 1. With `onFailure: block` that would block every ordinary call on a Mac. The first contract test never reached the path (no deployment, so `in_use.sh` returned early); my earlier "no exit 1 found" was only for bash 5 and is corrected here.

Fixed, each now `${a[@]+"${a[@]}"}` (the form the code already used elsewhere; same behaviour on bash 4.4+):
- `hooks/in_use.sh`: 393 `cwds`, 394 `bases`, 410 `bases`, 416 `cwds`, 417 `bases`, 434 `bases`
- `hooks/confirm_cleanup.sh`: 479 `keep`, 506 `CANDS`, 819 `alts`, 835 `SP`, 842 `BRACE_OUT`, 847 `X`, 1394 `XR`, 1401 `XA`
- `hooks/confirm_launch.sh`: 854 `W`

Tests: `tests/bash32_arrays_test.sh` (static: no unguarded `${name[@]}` in the four gates, `in_use.sh`, `launch_trigger.sh`; the scanner is itself checked) was RED on those 15 lines. `tests/gate_exit_contract_test.sh` now also runs through a fixture deployment (cwd inside, outside), with HOME and OSTYPE unset; it passes on bash 5, so it did not catch this itself.

I did not run a real bash 3.2 (none on the test machine: WSL has bash 5, Git Bash 5). The static test and the guard form are the evidence; a Mac run of `tests/gate_exit_contract_test.sh` would confirm it. Unguarded expansions of `${name[*]}`, or array slices, were also searched for: none.
