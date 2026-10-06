# Fix: intro-marker-timeout

- **Branch**: `fix/gates-audit2-launch` (RED 9b7a00c, GREEN: the commit carrying this file)
- **Changed**: `hooks/plugin_intro.sh`, `hooks/hooks.json` (both plugin_intro.sh entries 5 s -> 20 s), `tests/plugin_intro_test.sh` (7 cases; the two intro.sh stubs now accept `--lang` like the real script)
- **Approach**:
  - The marker first. Stdin is read without `cat`; the doors are decided on the raw text with bash regexes - a UserPromptSubmit naming `agentic-bioflow:` anywhere (as before), a Skill input whose own `skill` field starts with `agentic-bioflow:` (its arguments do not count) - and the marker is written before any program starts. The natural-language door folds the prompt in the shell when it is under 8 KB (one `tr` above that), then marks.
  - `mark_in_use` does nothing when the marker exists, makes the folder only when it is missing, and sweeps month-old markers only when it has just written a new one (after the write).
  - Faster: no `cat`, no `tr` for an ordinary prompt, no subshell for the plugin root, and the language is asked of `settings.sh` once and passed to both intro.sh calls (`--lang`), instead of each intro.sh asking again.
  - hooks.json: 20 s, measured need 3.5-6.6 s under load (audit) - the timeout is now a backstop, not the expected running time.
- **Red -> green**: with jq/cat/tr/sed/grep/awk/find each sleeping 20 s and the hook killed at 3 s, no marker for a typed command, a skill load or the natural-language door on 0e5e838 (3 red); written now. A slow intro.sh (killed at 3 s) leaves the marker for a typed command and a skill load (both doors). Another plugin's skill whose arguments name this one leaves none. hooks.json check red (5 s) -> green.
- **Native Git Bash, 5 runs each interleaved, median** (`g2b_tintro2.sh`; noisy machine): typed command 1.6 s -> 1.5 s, skill load 1.6 s -> 1.1 s. The marker is now written before the first external program, so the time to the marker is bash's own start-up plus reading stdin.
- **Also green**: `in_use_test.sh` (TC-007/TC-008 marker cases), `principle_12_test.sh`, `principle_13_test.sh`, `constitution_scope_test.sh`, `intro_test.sh`, `intro_languages_test.sh`.
- **Not changed**: when the overview is shown, its text, once per session, the jq check of the event before showing it.
