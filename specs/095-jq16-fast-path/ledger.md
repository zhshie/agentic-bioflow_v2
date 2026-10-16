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
- [x] Hooks (4): `sub("\n+\z"; "")` -> `def t` / `map(t + ...)`, as planned. Plan deviation: the real cause on 1.6 was `contains("\u0000")` (C-string compare, true for every string); with only that fixed the old `sub` already worked on 1.6. NUL check is now `test("\u0000")` in the four hooks; the `t` swap is kept as planned.
- [x] `tests/jq_versions_test.sh` new; `tests/gate_process_count_test.sh` +1 line (prints jq version).
- [x] `docs/PITFALLS.md` entry 51. `CHANGELOG.md` does not exist in the repo: not created, nothing to add.
- [x] WSL `tests/run_all.sh` with jq 1.6 first on PATH: 104/104 passed. With jq 1.7.1 first: 104/104 passed. `jq_versions_test.sh` on WSL: both halves ran, all passed.
