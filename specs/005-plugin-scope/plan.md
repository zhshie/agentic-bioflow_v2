# Implementation Plan: plugin scope (005, #48)

**Branch**: `005-plugin-scope` | **Spec**: `spec.md` | **Test cases**: `test-case.md`, approved on 2026-10-02

## Summary

Add one sourced helper, `hooks/in_use.sh`, that answers "is agentic-bioflow in use for this call?" Every hook asks it first and exits 0 silently when the answer is no. `plugin_intro.sh` writes the per-session "in use" marker. `confirm_launch.sh`'s D3 branch no longer asks about ssh run through WSL or with `BatchMode=yes`. The constitution moves to 2.0.0, with every citing document updated in the same PR.

## Facts this rests on

- PreToolUse and PostToolUse fire for subagents with the parent's `session_id`, plus `agent_id`/`agent_type` (code.claude.com/docs/en/hooks.md, checked 2026-10-02). A marker keyed by `session_id` therefore covers a session's subagents.
- Today's hook test inputs carry no `session_id`. Under FR-005 a missing session id counts as in use, so every existing gate test keeps exercising the gates unchanged (TC-016, TC-024).
- `plugin_intro.sh` already decides when the user "reaches for the plugin": a literal `/agentic-bioflow:` prompt, a Skill load, or a natural-language match. It already keeps per-session markers under `$STATE`.

## Design

### `hooks/in_use.sh` (sourced; no external process on the not-in-use path)

`abf_in_use <raw-input-json> <command-text> <tool-name>` returns 0 (in use) or 1 (not in use). It checks, in order:

1. **Seqera MCP tool.** If `tool_name` matches `mcp__.*([Ss]eqera|[Tt]ower)`, return 0 (condition ③).
2. **Session id.** Extract `session_id` with a bash regex, not sed or jq, so no fork. If it is missing or empty, return 0 (FR-005).
3. **Marker.** Set `STATE=${AGENTIC_BIOFLOW_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/agentic-bioflow}`. If `$STATE/in-use/<sanitised sid>` exists, return 0 (condition ①). If `$STATE` exists but cannot be read, return 0 (FR-005).
4. **Command text** (condition ③). Return 0 if any of these holds:
   - it contains this plugin's root path (`$CLAUDE_PLUGIN_ROOT`, or the directory above `hooks/`);
   - it names one of the plugin's own scripts as `scripts/<name>` with `<name>` from a bash glob of `$ROOT/scripts/*.sh` and `*.py`;
   - it has `tw` as a command word (regex `(^|[;&|(]|[[:space:]])tw[[:space:]]`).
5. **Deployment** (condition ②).
   - Find the root: `LAB_SETTINGS_FILE`, or the root pointer file at `${XDG_CONFIG_HOME:-$HOME/.config}/agentic-bioflow/root`, read with the `read` builtin.
   - If there is no settings file at all, return 1. Nothing is deployed, so the answer is known (TC-019).
   - Take `cwd` from the input's `.cwd` (bash regex), or `$PWD`.
   - Return 0 if cwd is under the root, or under `storage_root` (read from env.yaml with a `while read` loop, no fork).
6. Otherwise return 1.

Any unexpected state while evaluating returns 0, failing safe toward "in use".

### Hooks

Each hook gets one early line after it has read INPUT (and CMD, where it has one): `abf_in_use "$INPUT" "$CMD" "$TOOL" || exit 0`.

- `confirm_launch.sh` and `confirm_cleanup.sh`: before jq and the splitter, so the not-in-use path stays fast (FR-007). The hook already reads the raw bytes before jq for the T1 no-jq path. That raw text is passed as `<command-text>`: over-including only means "in use", which is the safe direction.
- `confirm_walkthrough.sh`, `guard_plugin_files.sh`: same.
- `next_step.sh` (Stop): `abf_in_use "$INPUT" "" ""`. It has no command, so only conditions ①, ② and FR-005 can make it in use.
- `session_start.sh`: no marker can exist yet at session start, so it speaks only when cwd is in a deployment (condition ②). Otherwise it says nothing. The overview still appears through `plugin_intro.sh` the moment the plugin is used.
- `plugin_intro.sh`: on IS_LITERAL or IS_NL, `touch $STATE/in-use/<sid>`. This happens before its own once-per-session exit, so the marker is written even when the overview was already shown. It is not gated itself, because it is the thing that turns scope on.

### D3 (FR-006)

In the MSYS transport loop, skip a segment when either holds:

- its command word is `wsl` or `wsl.exe` (the third splitter column);
- its quote-free text matches `-o[[:space:]]*BatchMode=yes` (case-insensitive on the value).

`echo wsl; ssh …` is two segments, so the second is still judged (TC-015).

### Constitution 2.0.0 (FR-008)

- Safety Net preamble: these rules govern any session in which agentic-bioflow is in use, defined by the three conditions plus the fail-safe rule. Outside such a session the plugin stays silent.
- Amendment note: the rationale (#48), what it breaks (a non-abf session outside a deployment is no longer protected), and the version and date.
- Same PR: `docs/PRINCIPLES.md`, root `CLAUDE.md` (Key invariants / Safety net), `docs/SITE_ADAPTER.md` contract 6 where it says "only sanctioned route", `README.md` if it claims always-on protection, and the hook file headers. Find them with `grep -rn "Safety [Nn]et\|safety net" docs CLAUDE.md README.md hooks`.

## Constitution check

This change is itself a MAJOR amendment (Governance). Approved direction: the maintainer chose "全部關掉" on 2026-10-02 with the risk stated. Principles 3 and 4 are unaffected. The tests for principle 5 still hold, because the hooks degrade but docs and scripts stay usable.

## Tests

- New `tests/in_use_test.sh`: TC-001 to TC-006 and TC-017 to TC-020 against each hook, using a fake HOME/STATE/settings. It also covers TC-007 and TC-008 by running `plugin_intro.sh` first with the same sid.
- `tests/confirm_launch_test.sh` gains TC-014 and TC-015, the D3 exceptions, using in-use input (no sid).
- New `tests/constitution_scope_test.sh`: TC-021 and TC-022, as doc greps.
- New `tests/in_use_speed_test.sh`: TC-023. Run main's `confirm_launch.sh` (extracted with `git show main:hooks/confirm_launch.sh`) against the new one, 20 calls each, not-in-use input. Pass when new ≤ main × 1.1. Skip with a note if `git` or main is not available, for example in a CI shallow clone. Check how CI checks out first.
- TC-016 and TC-024 run the full suite.

## Complexity and risk

- **Medium.** Six hooks are touched, plus one new helper and a constitution amendment.
- **Risk 1: false "not in use" means a gate does not fire.** Mitigations:
  - Fail-safe to "in use" on a missing sid or an unreadable state directory.
  - The existing gate tests keep running in use.
  - Independent acceptance will be asked specifically to hunt for an in-use call that is judged "not in use".
- **Risk 2: the session-start context disappears for sessions that start outside a deployment.** That context is the bridge and WSL note we see at every session start. Accepted: `plugin_intro.sh` shows the overview when the plugin is first used.
- **Risk 3: the speed test is flaky under load.** It compares against main on the same machine in the same run, with a 10% margin.
