# Fix plan: backslash-inside-delete-word (issue #66)

Tier A (makes the Safety Net stricter). Touches `hooks/` (protected path): a `/code-review` security pass runs before merge.

## What changes

1. `hooks/confirm_cleanup.sh`: after the command is split into segments, every segment that holds a backslash is added a second time with its backslashes dropped (port of `hooks/launch_trigger.sh:135-145`). The segment as written is still judged (Windows paths use `\`). A segment's verdict is the strictest of its copies.
2. The large-input path (`RE_TRIGGER` prefilter, `tests/confirm_cleanup_behind_heredoc_test.sh`) sees the dropped-backslash copy too, so the same commands are caught behind a big here-doc.
3. The no-jq fallback (raw-text deletion pattern) also matches with backslashes dropped, so `r\m -rf results` without jq is BLOCKED, not let through.

## Tests (RED first)

- `tests/confirm_cleanup_test.sh`, end of the SN1 section: the four commands of the assessment, each expecting the verdict of the same command without `\`; plus `rm -rf res\ults` stays deny, `\rm -rf results` stays deny.
- Controls stay pass: `printf 'a\nb'`, `grep -E "a\sb" file`, `sed 's/a\/b/c/' f`, `echo C:\Users\x`, `ls C:\work\results` (read-only, must not ask).
- `tests/confirm_cleanup_behind_heredoc_test.sh` reruns the four behind a large here-doc.
- `tests/gates_without_jq_test.sh` gains `r\m -rf results` -> exit 2 BLOCKED.
- Timing: the existing 300 KB timing test stays under its limit (~3 s).

## Out of scope

- Other quoting tricks (`r''m`, `$'\x72'm`, variables, aliases) unless already caught.
- confirm_launch.sh / confirm_walkthrough.sh / guard_plugin_files.sh changes.
- Issue #71.

## Done when

The four commands get deny/ask with jq, BLOCKED without jq; controls stay pass; CI green; verifier ACCEPT; `/code-review` has no high-confidence finding.
