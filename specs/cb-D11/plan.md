# cb-D11 plan: shell helper duplicate ratchet

- Goal: a test that counts same-named shell functions defined in more than one script under
  scripts/**/*.sh, records today's set as a baseline, and fails on any new duplicate.
- Source: cloud-burn tasks.json D11.
- Files: tests/shell_helper_dupes_test.sh, tests/shell_helper_dupes_baseline.txt (plus this plan and ledger.md).
- Approach: extract `name()` / `function name` lines per file (sorted unique per file), keep names found
  in 2+ files, compare "<name><TAB><file>" pairs against the baseline. A pair not in the baseline fails
  (new duplicate or new copy of an old one); a baseline line that is no longer a duplicate also fails
  (baseline only shrinks). Bash 3.2 safe, static, no network. A fixture inside the test proves the
  detector and the ratchet logic so a broken scanner cannot go green.
- RED tests: with no baseline file the test fails (first commit); mutation proof after the baseline
  exists: add a duplicate helper to a script, test fails, revert.
- Done: test green on unchanged tree, mutation fails, scope guard passes, full run_all green.
- Environment: /tmp/cb/venv with platform installed; Linux GNU userland.
- Not doing: de-duplicating any helper, editing any script, touching run_all.sh.
