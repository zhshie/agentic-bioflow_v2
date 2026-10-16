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
