# Fix: jq-broken-later-line

- **Branch**: `fix/gates-audit2` (RED 298ac9b, GREEN 1cd7634)
- **Changed**: `hooks/confirm_launch.sh` (`looks_launch_shaped`), `hooks/confirm_walkthrough.sh` (`looks_managed_write_shaped`); `tests/gate_output_failclosed_test.sh` (jq-broken-gates section, 16 cases).

## What changed

Ported from `looks_delete_shaped` (jq-broken-cleanup): the JSON escapes `\n`, `\t`, `\r` are separators, and if `sed`/`tr` cannot run (empty result from a non-empty input) the text counts as shaped.

## Evidence (WSL)

`echo ok` + newline + `tw launch nf-core/rnaseq`:

| jq | confirm_launch before / after | confirm_walkthrough before / after |
|---|---|---|
| exits 127 | pass / BLOCKED | pass / BLOCKED |
| exits 3 | pass / BLOCKED | pass / BLOCKED |
| prints `{}` | pass / BLOCKED | pass / BLOCKED |
| prints text | pass / BLOCKED | pass / BLOCKED |

`echo ok` + newline + `ls -la` stays quiet in all eight. RED: 8 failures; GREEN: all passed. The acceptance probe (`abf_accept_A/jq_probe.sh`, column ln:tw2) now shows BLOCK for missing/empty/text/fail3.
