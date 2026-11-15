# ledger pitfalls-seed-r4
- [x] RED: tests/test_pitfalls_seed.py, 6 failed before the entries were added (commit RED:).
- [x] GREEN: docs/PITFALLS.md entries 62-64 appended; tests/pitfalls_format_test.sh count 97 -> 100 (ruling a); 64 Touches "synced drive (e.g. Google Drive)" (ruling b).
- T5 uses a hardcoded sha256 of the first 2572 lines (origin/v3 aebb7a59), since origin/v3 will later contain the entries.
- 62 Check cites tests/run_all_test.sh (already covers exit 3 on MINGW64). Source line numbers re-checked: CLAUDE.md 222-227, TESTING.md 23-24; entries cite files, not line numbers.
- 63: `wsl_ssh.sh` is not at the repo root or scripts/, so it is not in backticks.
- TC-024 (real Windows run) not done.
