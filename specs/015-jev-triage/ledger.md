# Ledger: 015-jev-triage


- [x] Spec folder carried over (spec, tasks, labels.json hash unchanged, merged plan) with plan points 1,2,5,7(c),8 applied: commit 3de08d6
- [x] RED: tests/jev_test.sh, tests/fixtures/jev/, credentials net extended (.typesafe_key, TYPESAFE_API_KEY/JEV_KEY)
- [x] T001/T002 ADR 0007 and POSITIONING line (Jev is now optional, off by default, disclosed)
- [x] T003 settings.sh: jev_key_file(), jev_setting(), `--jev`; .gitignore adds .typesafe_key
- [x] T004-T007 fixtures, scripts/jev.sh, jev_test.sh, credentials test
- [x] T008/T009 skills/runs/SKILL.md Jev step + six category routes; skills/operational/SKILL.md order
- [x] T010 golden: FAILED-flow scripts and hooks untouched and do not mention jev (checked in jev_test.sh, TC-020/021/027/075)
- [x] T011/T012 all 42 items through jev.sh under JEV_DRY_RUN; scripts/dev/jev_replay.sh (offline and real)
- [x] T013 SETTINGS.md Jev section, TESTING.md on/off walkthrough, CHANGELOG one line (plugin.json unchanged)
- [x] T014 full suite 105/105 green in WSL; claude plugin validate passes (README warning predates this work); the real-key replay is the maintainer's manual step
- [x] Fix (CI-only failure, run 38887221932): TC-044 asserted `git status --porcelain` was empty, so any untracked file left by earlier run_all tests failed it (reproduced: dummy untracked file -> FAIL). Now snapshots the same pathspec at script start (REPO_BEFORE) and compares after the triage calls; equal passes. With a dummy file present it passes; a file the script wrote into the repo mid-run would change the status and fail. Audited other repo-state checks (TC-057 and the refs/rec scans use `git ls-files`, tracked files only): not affected, unchanged.
- [x] Fix (CI-only failure, TC-064 32/37): jev_replay.sh ran `"$JEV" triage` directly, but scripts/jev.sh is committed as mode 100644 (repo convention: scripts are run via bash). On /mnt/c every file looks executable so it passed; in a fresh clone/CI every triage call got "Permission denied" -> 0/37. Now `bash "$JEV" triage`. Reproduced in a fresh clone (0/37), fixed, re-verified in a fresh clone.
