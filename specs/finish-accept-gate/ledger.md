# finish-accept-gate progress ledger

- [x] build_package.sh refuses entries not `accepted`/`done` (exit 2, before any write); status now parsed in block form; one parser run in `check` then `results` mode (TC-G01..G27 in tests/build_package_test.sh; RED run showed 20 failures, then green).
- [x] skills/finish/SKILL.md step 1 and docs/FINISH.md each gained one sentence naming `status: accepted` (TC-G15).
- TC-G21 (WSL, v3 base 54900a2 vs this branch, fixtures: table with fig1/fig1_b prefix clash, empty-id row, csv-only id, plus block form): `diff -r` of submission/ differs only in the build timestamp and the temp directory name embedded in README.md; manuscript.qmd, report.md, methods.md identical.
- Full suite (abf-fast-suite, WSL): 118/118 passed.
