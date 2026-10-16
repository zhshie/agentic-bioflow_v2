# Ledger: 078-cleanup-unknown-cwd


- [x] RED: TC-078-01..29 added to tests/confirm_cleanup_test.sh after TC-043; the ask cases failed on the unchanged hook (pass or deny).
- [x] GREEN: `CWD_LOST` + `lost_rel` in hooks/confirm_cleanup.sh (cd/pushd `-`/none/quoted backslash, popd, Pop-Location; cleared by an absolute cd); asks at delete targets, find roots, mv sources.
- [x] Shapes flipped pass -> ask, reason "lost cwd now asks" (30 lines of tests/confirm_cleanup_shapes.txt): 2 3 6 7 8 9 11 13 14 16 (popd/pushd-popd), 74 (cd -), 75 (bare cd), 139 141 143-150 157 166-168 184 293 (popd), 153 183 (bare pushd). Measured over shapes.txt: 30 changed lines, all pass->ask, none deny/ask changed. shapes_main.txt untouched (its verdicts are deny/ask only; unchanged).
- NOTE for reviewer: TC-078-05, 06, 07, 13 as written expect ask, but main already DENIES them (cd "res\ults" adds candidate results/; `cd -` keeps candidate P, so `rm -rf results` denies). Turning deny into ask would loosen, against plan section "no deny weakened" and TC-078-33. Those four are pinned as deny, and the quoted-backslash mechanism is tested with `tm\p` (TC-078-05/06/07 "mech" lines, ask).
- No CHANGELOG.md exists in the repo; no entry added. PRINCIPLES.md does not describe unknown-cwd; not changed.
- [x] Fix: popd added to CW_HANDLED (large-input filter dropped popd segments; behind-heredoc test caught it).
