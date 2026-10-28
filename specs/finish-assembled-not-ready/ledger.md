# build_package.sh 成功時說明還有幾處 Results 佔位、Discussion 未寫 progress ledger

- [x] scripts/build_package.sh: `note` line after the `wrote manuscript.qmd` line; K = `grep -c` on the written qmd; K=0 prints the Discussion-only note.
- [x] tests/build_package_test.sh: TC-N01..N12, N16, N17, N19, N20 added; TC-G23 REVERSED (was "new wording must not appear", now "must appear") - the only existing assertion changed, per plan step 4.
- [x] docs/FINISH.md: new section "The success message says assembled, not ready (issue #12)".
- TC-N17 made with a grep shim in PATH (K=0 reproduced). Note: tests and code were committed together (no separate RED commit) because the tool run applied both edits in one step.
