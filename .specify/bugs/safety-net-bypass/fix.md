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
