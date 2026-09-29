# Bug Fix: safety-net-bypass

- **Slug**: safety-net-bypass
- **Fixed**: 2026-09-29
- **Assessment**: `assessment.md` (decisions Q1 yes, Q2 deferred to #33)

## Test-first

42 cases added (`tests/confirm_cleanup_test.sh` 23, `tests/confirm_launch_test.sh` 23 lines marked `#29`, incl. matcher checks). Before the fix, in WSL: 14 cleanup + 13 launch cases FAILED, i.e. every bypass in the assessment — including the five that were only inferred — was reproduced. Read-only regressions (`grep` with the verb in a quoted regex, `cat > f <<EOF` mentioning a delete or a launch, `tw pipelines list`, `nextflow log`, `--dry-run`) passed before and after.

## Changes

| File | Change | Assessment item |
|---|---|---|
| `hooks/confirm_cleanup.sh` | Separators inside quotes are masked instead of the quoted text deleted; the verb is detected on a quote-free copy, targets read with quotes kept; `bash -c`/`eval`/`… \| bash` payloads scanned like ssh ones | 1 |
| `hooks/confirm_cleanup.sh` | `Remove-Item`/`rd`/`del`/`erase` as delete verbs (case-insensitive); backslash paths normalised; no-jq raw scan also knows `Remove-Item`, `rmtree` | 4 |
| `hooks/confirm_cleanup.sh` | Variable targets are still judged by their literal part (`"$X/results"` → deny) and otherwise `ask`; `xargs` deletes and delete calls in code (`shutil.rmtree(`, `os.remove(`, `unlink(`, `file.remove(`, `fs.rm(`) → `ask` | 6, 2 |
| `hooks/strip_heredocs.awk` | Body kept when an executor reads it: command word `bash/sh/zsh/dash/ksh/ssh/on_site.sh/python/python3/Rscript/R/perl/node/ruby`, or the line pipes into a shell | 2 |
| `hooks/launch_trigger.sh` | Any tokens between `tw` and `launch`/`runs relaunch`, and between `nextflow` and `run`; `relaunch_with_override.sh … --confirm` is a launch; a pipe into a shell is a nested shell and its quoted text is judged as its own segment | 3 |
| `hooks/confirm_launch.sh` | Seqera/Tower MCP tools: launch-named (`launch`, `relaunch`, `submit`, `run_workflow`, `run_pipeline`, `start_run`) → `ask`; other Seqera tools are queries | 5 |
| `hooks/hooks.json` | New PreToolUse entry `mcp__.*([Ss]eqera|[Tt]ower).*` → `confirm_launch.sh` only (the deletion guard's raw scan would pause ordinary MCP queries) | 5 |
| `commands/runs.md:191` | "proceeds without asking first" → the size needs no question, the relaunch still waits for confirmation | 7 |
| `docs/PITFALLS.md` | Entry 37 | — |

## Verification by the author

- WSL `bash tests/run_all.sh`: 73/73 green (before the PITFALLS/runs.md edits; rerun before PR).
- `commands/` and `skills/` contain no `rm`, here-doc or `| bash` step, so no routine step of the plugin's own flow starts asking.

## Not done here

- `mv` of protected directories (Q2 → #33).
- Manual half of `docs/TESTING.md` (hooks changed): the maintainer, after restarting Claude Code with this branch installed.
- Independent acceptance (`/speckit-bug-test` by the read-only `verifier` agent) — next.

## Round 2 (after independent acceptance said FAIL, 2026-09-29)

The first acceptance review (read-only verifier, fresh context) failed the fix on remediation items 1, 2 and 4 and found more bypasses plus new false alarms. Every finding was reproduced, written as a test first (35 new cases, all red), then fixed:

- `hooks/split_segments.awk` (new, shared by both gates): quote-aware splitting on `; | & && ||`, newlines and subshell parentheses; `>&`/`&>` are redirects; `# comments` dropped; contents of `$(...)`, backticks, `<(...)` emitted as commands; quoted strings re-read by `bash/sh -c`, `eval`, `ssh`, `on_site.sh`, `powershell/pwsh`, `python/perl/ruby/node/Rscript -c|-e`, or a pipe into a shell are split as commands; code calls (`system(`, `subprocess.run([...])`, …) emit their strings one by one and joined; third column = command word (past sudo/env/timeout and options, VAR=, quote characters, `\`, a directory). Replaces the two gates' separate sed splits, so they cannot drift (remediation item 1's "same helper").
- `hooks/confirm_cleanup.sh`: the verb is the command word only (`grep del results/` no longer denies); `unlink`, `truncate`, `ri`, `find -exec rm` are deletes; every quote character is dropped from targets (`'…/rawdata'/`, `res"ults"`); brace lists expanded for matching; a glob that could match a protected name → ask; a variable/substitution command word (`$(which rm)`, `$R`) on a protected path → ask; a delete with no target on the line (`… | Remove-Item`) → ask; in-code deletes judged on the quote-free copy (searching for `os.remove(` no longer asks); `::Delete(` added.
- `hooks/strip_heredocs.awk`: any word of the opening segment may be the executor (`sudo -u bob bash`, `timeout 60 bash`, `srun bash`).
- `hooks/launch_trigger.sh`: uses the shared splitter; a quoted program (`"tw" launch`) is read when the command word is a launcher.
- `hooks/hooks.json`: every safety gate's timeout 5-10 s → 30 s. A PreToolUse hook past its timeout is cancelled and the tool call proceeds (code.claude.com/docs/en/hooks-guide); the deletion guard measured 4.4-4.8 s on this Windows laptop against its 5 s limit, i.e. the gate could vanish under load with nothing printed. Pre-existing on main, fixed here because it is a bypass of the same kind. `tests/confirm_launch_test.sh` now fails if any gate drops below 30 s; `tests/guard_plugin_files_test.sh` updated from 5 to 30.
- Tests: `MSYS2_ARG_CONV_EXCL='*'` in the cleanup test (Git Bash rewrote `/bin/…` arguments to Windows paths before python saw them); `tr -d '\r'` for jq.exe output in the matcher checks.

Verification: WSL `tests/run_all.sh` 73/73; native Git Bash `confirm_launch_test` all new cases pass (only the pre-existing D3 MSYS case fails, #30); timing new vs main, native Git Bash: cleanup 4.4 s vs 4.8 s, launch 3.4 s vs 3.8 s (not slower). The gates being ~4 s per shell call on Windows is itself a problem → separate issue.
