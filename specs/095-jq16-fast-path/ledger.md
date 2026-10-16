# Ledger: 095-jq16-fast-path


## Red (before hook change), WSL, tests/jq_versions_test.sh
```
FAIL: hooks/confirm_cleanup.sh does not carry the regex-free strip (def t / map(t + ...))
FAIL: hooks/confirm_launch.sh does not carry the regex-free strip (def t / map(t + ...))
FAIL: hooks/confirm_walkthrough.sh does not carry the regex-free strip (def t / map(t + ...))
FAIL: hooks/guard_plugin_files.sh does not carry the regex-free strip (def t / map(t + ...))
--- jq 1.6: jq-1.6 at /usr/bin/jq
launch gate on a 60-line here-doc [confirm_launch: 6, budget 3]            FAIL: started: jq jq jq jq awk awk 
deletion guard on a 60-line here-doc [confirm_cleanup: 6, budget 3]        FAIL: started: jq jq jq jq awk awk 

21 failed
FAIL: gate_process_count_test.sh under jq 1.6
--- jq 1.7: jq-1.7.1 at /usr/local/bin/jq
launch gate on a 60-line here-doc [confirm_launch: 3, budget 3]            ok
deletion guard on a 60-line here-doc [confirm_cleanup: 3, budget 3]        ok

all passed
5 failed
```

## Green
- [x] Hooks (4): only change is `contains("\u0000")` -> `test("\u0000")`. The real cause on 1.6 was `contains("\u0000")` (C-string compare, true for every string). Review fix round: confirmed on WSL jq 1.6 (/usr/bin/jq) and 1.7.1 that the original `sub("\\n+\\z"; "")` gives identical output (trailing newlines stripped, all-newline body -> empty, interior kept), so the `def t` recursion from the first GREEN was reverted (O(newlines x length): ~100 s for 1 MB + 20,000 newlines). This deviates from plan "Design decisions" (not edited here); PITFALLS 51 names the real cause.
- [x] `tests/jq_versions_test.sh` new; `tests/gate_process_count_test.sh` +1 line (prints jq version).
- [x] `docs/PITFALLS.md` entry 51. `CHANGELOG.md` does not exist in the repo: not created, nothing to add.
- [x] WSL `tests/run_all.sh` with jq 1.6 first on PATH: 104/104 passed. With jq 1.7.1 first: 104/104 passed. `jq_versions_test.sh` on WSL: both halves ran, all passed.

## Review fix round (WSL, after reverting `def t`)
- `tests/jq_versions_test.sh` rewritten: extracts the program from each of the four hooks; NUL / 0x1f / mixed / non-string cases (empty on both versions), newline shapes, 1 MB body + 20,000 trailing newlines (< 2 s); asserts non-empty output (or expected empty), jq exit code, empty stderr; versions 1.6 / 1.7.x / 1.8.x discovered and labelled by real `--version`, shim version asserted; fails if no version ran; static check that HEAD/GUARD/TAIL text is identical in all four hooks.
- Mutation check: `contains("\u0000")` put back in confirm_launch.sh -> 21 FAIL; restored.
- WSL `tests/run_all.sh`: jq 1.6 first on PATH 104/104; jq 1.7.1 first 104/104. `bash tests/jq_versions_test.sh`: 197 PASS, both versions, all passed.
