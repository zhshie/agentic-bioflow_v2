# Fix: gate-fail-open-big-output

- **Branch**: `fix/gates-audit2` (commits d0f9e14 RED, c018c15 GREEN)
- **Changed**: `hooks/confirm_launch.sh`, `hooks/confirm_cleanup.sh`, `hooks/confirm_walkthrough.sh`, `hooks/guard_plugin_files.sh`; new `tests/gate_output_failclosed_test.sh`; `tests/gate_big_input_test.sh` asserts the large launch verdict.
- **Approach**: every gate builds its output through one function, `abf_emit`. It bounds what is displayed (the first and last 3000 characters, with a line saying how many were left out; the verdict itself was already reached on the whole text), so `jq --arg` never meets the argv limit. If `jq` still fails, or prints something that is not a JSON object, a fixed minimal `ask` is printed instead of nothing, so the call waits for a person.
- **Red -> green**: `tests/gate_output_failclosed_test.sh` failed 7 cases on main (a jq that cannot build output made every gate silent; a 70 KB launch and a 70 KB delete printed nothing); `tests/gate_big_input_test.sh` "128 KB here-doc then tw launch (launch gate)" got `none` instead of `ask` (at 32 KB on native Git Bash, at 128 KB on Linux). Both green after c018c15.
- **Not changed**: what the gates decide, and the text of any message shorter than the display bound.
- **Follow-up on this branch**: `.specify/bugs/jq-broken-cleanup/` tightens the "not a JSON object" check for the deletion guard (a jq that prints `{}` passed it).
