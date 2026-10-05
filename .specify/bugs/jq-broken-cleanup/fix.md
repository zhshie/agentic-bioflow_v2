# Fix: jq-broken-cleanup

- **Branch**: `fix/gates-audit2` (RED bb93e07, GREEN 2f0f3ea)
- **Changed**: `hooks/confirm_cleanup.sh`; `tests/confirm_cleanup_test.sh` ("no jq" section: "jq present but broken in other ways", 21 cases).

## What changed

- **The one-call read proves jq computed it.** The `jq -js` program also returns a token jq has to build (`"abf-" + "jq-ok"`); the answer is trusted only when the token, both fields, their two separators and nothing else came back. Otherwise the old path: a probe, then one jq per field.
- **The probe asks for an answer, not an exit status.** `jq -e .abf -r <<<'{"abf":"jq-ok"}'` must print `jq-ok` (it keeps the `jq -e .` that `tests/principle_13_test.sh` looks for). A jq that prints `{}`, a line of text or nothing now fails it.
- **An answer that contradicts the input is a broken jq.** No command read from a Bash input whose raw text carries a non-empty command field (a per-field read that failed, or an empty answer) goes to the raw-text path.
- **One raw-text path for all of them** (`jq_refuse`): a deletion-shaped command is refused with exit 2 and the install commands, as with no jq; the first line names what is wrong ("missing, cannot run here, or does not compute correctly" / "runs here but read no command from an input that has one"); anything else passes, as before.
- **`abf_emit` checks what jq built**: printed only when it carries `hookSpecificOutput`, `hookEventName: PreToolUse` and the decision it was asked for (and `additionalContext` when one was given); otherwise the fixed minimal ask. Before, anything starting with `{` was printed, `{}` included, which carries no decision and lets the call proceed.
- **The raw-text scan sees later lines**: the JSON escapes `\n`, `\t`, `\r` are separators (`rm` on line 2 was `\nrm`, glued to the `n`), it fails closed if `sed`/`tr` cannot run, and it knows `truncate`, `unlink`, `rclone`, `--remove-files`, `nextflow … clean`, `git … clean`, and the code deletes (`rmSync`, `rm_rf`, `os.remove`, `FileUtils.rm`, ...).

## Evidence (WSL)

| jq on PATH | delete, line 1 | delete, line 2 | `ls -la` |
|---|---|---|---|
| prints `{}` | `{}` -> BLOCKED (exit 2) | pass -> BLOCKED | pass |
| prints a line of text | ask -> BLOCKED | pass -> BLOCKED | pass |
| prints nothing | ask -> BLOCKED | pass -> BLOCKED | pass |
| empty command in the one-call read | pass -> deny (per-field path) | pass -> deny | pass |
| fails on the command field only | pass -> BLOCKED ("read no command") | pass -> BLOCKED | pass |
| builds `{}` as the verdict | `{}` -> ask (fixed) | `{}` -> ask | pass |
| exits 127 (already covered) | BLOCKED | pass -> BLOCKED | pass |
| none (already covered) | BLOCKED | pass -> BLOCKED | pass |

No jq: `truncate -s 0 …/results/x.tsv` and `unlink …/results/x.tsv` pass -> BLOCKED.

- RED bb93e07: 13 failures. GREEN 2f0f3ea: all pass; `gate_output_failclosed_test.sh`, `gate_process_count_test.sh` (no extra program: the token rides on the same jq call), `principle_13_test.sh`, `confirm_cleanup_behind_heredoc_test.sh` green.
- **Already covered before, kept**: `tests/gate_output_failclosed_test.sh` (jq that cannot build the answer: ask), the "no jq" and "broken jq (exit 127)" cases of `tests/confirm_cleanup_test.sh`.
- **Not changed**: the other three gates have the same shape (`printf '{}' | jq -e .` as the probe, `[[ $o == '{'* ]]` as the output check, the same raw scan); another branch owns them. A jq that answers a plausible but wrong command is not detected (only an adversary does that).
