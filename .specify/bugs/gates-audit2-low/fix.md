# Fix: gates-audit2-low

- **Branch**: `fix/gates-audit2` (RED 298ac9b, GREEN 1cd7634; RED 4af06f0, GREEN e6c2c32 for the backslash inside a word)
- **Changed**: `tests/confirm_cleanup_test.sh`, `tests/gate_output_failclosed_test.sh` (comment), `hooks/launch_trigger.sh`, `tests/confirm_launch_test.sh`.

## What changed

- **`srun tar --remove-files ... results` behind a big here-doc**: a case in `tests/confirm_cleanup_test.sh`, which `tests/confirm_cleanup_behind_heredoc_test.sh` reruns behind a 40 KB here-doc. It passes today (the behaviour was right); it was checked to fail under mutation M3b (`($RE_TAR_RM)` removed from `RE_TRIGGER`): "srun tar --remove-files of results/ FAIL: expected deny, got pass".
- **Stale comment** at the top of `tests/gate_output_failclosed_test.sh` now names the "no jq" sections of the three gate tests and the jq-broken sections.
- **`tw l\aunch`, `s\batch`** (optional item, done): `is_launch_command` adds, for each segment holding a backslash, a copy with the backslashes dropped (one awk pass, only when the command has a backslash). The original segment is still judged, so a Windows path keeps its verdict.

## Evidence (WSL)

| Command | confirm_launch before / after |
|---|---|
| `tw l\aunch nf-core/rnaseq` | pass / ask |
| `s\batch job.sh` | pass / ask |
| `srun s\batch job.sh` | pass / ask |
| `echo s\batch` | pass / pass |
| `ls C:\Users\x\sbatch_notes` | pass / pass |

RED: 3 failures plus their #62 big-input reruns; GREEN: all passed. `gate_process_count_test.sh` green.

Speed (native Git Bash, 300 KB here-doc, median of 3, measured while the WSL suite ran): confirm_launch 2.4-2.9 s before and after (base 41d8f9b 2.3-3.1 s), confirm_cleanup 1.6-2.7 s both.
