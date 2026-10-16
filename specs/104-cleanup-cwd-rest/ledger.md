# Ledger 104-cleanup-cwd-rest

- 2026-10-17 plan written by the developer-agent.
- 2026-10-17 executor: RED commit first. Before the fix, `bash tests/confirm_cleanup_test.sh` failed 35 cases (TC-104-01..07, 09, 11, 12, 13, 22, 23, 24, 28..31, the 5 flipped pass lines, and the new shapes rows). TC-104-14 and 15 already asked on main (the `if` form hides the cd from the loop; `cd $d` after `cd -` never cleared), kept as controls.
- Done (hooks/confirm_cleanup.sh): design 1 (unnameable cd target sets CWD_LOST), 2 (`cd_uncond`: an absolute cd clears only if every command line that holds it has no `&`/`|`/`(`/backtick/`||`/if/while/until/case/for/select/eval/ssh/-c; `{ cd /abs; }` is unwrapped so it clears), 3 (relative `>` target asks under lost_rel; large-input trigger added for it), 4 (only `~` and `~/..` exempt), 5 (PowerShell bare `sl`/`Set-Location`/`sl -`/quoted-backslash target set CWD_LOST, Bash untouched; backslash test is on the cd target, not the segment), 6 (popd untouched), 7 (`lost_ask` helper for all consumers). The `{` command word is added to CW_HANDLED so the large-input filter keeps it.
- Design 7 flips no shape today: the find-root check already ran for every find that removes (RE_FIND_DEL); `find -exec mv` already asked on main through the mv-source check (TC-104-37 is a control). The helper is a drift guard.
- Pinned lines flipped pass->ask, reason "lost cwd now asks (#104)": TC-041, TC-042, `#35 cd to a variable`, TC-078-24, TC-078-27, shapes.txt line 32. No deny/ask line changed.
- Shapes measurement (branch vs the base commit 1e08568 hook, over all 311 rows of confirm_cleanup_shapes.txt, no transcripts): 11 rows pass->ask, 0 loosened. The 11 are: shapes line 32 (`cd ~`) plus the 10 new rows (cd ~/x, cd $HOME/.., cd $(..), ~s1, (cd /tmp), `&`, `||`, `: > s1`, `echo hi > s1`, PowerShell `sl -`). Comparing with confirm_cleanup_shapes_main.txt directly is not meaningful: that file predates #75/#76/#78 and differs in ~110 rows already landed. New shapes rows were appended at the end so the line pairing with shapes_main.txt (300 lines) stays aligned.
- Timing test (main vs branch, ms): T1 420 vs 1543, T2 689 vs 1982, TC-064 60 vs 128, 16 KB 100 vs 115, 32 KB 146 vs 169; all within the test's budget. (The T1/T2 gap is the existing candidate work run under WSL on /mnt/c, not this change: cd_uncond only runs for an absolute cd while the folder is lost.)
- Known gaps (follow-up issue): `tar --remove-files`, `zip -m`, `rclone move` relative sources still pass after `cd -`; aliases (TC-043); a cd wrapped in `bash -c` is only caught by the `-c`/eval/ssh word on its line; a PowerShell location cmdlet inside `pwsh -c "..."` under the Bash tool; an absolute cd to a folder that does not exist still clears.

## Fix round 2 (2026-10-17): the brace loosening

- Finding: `cd -; { cd /tmp; }; rm -rf s1` and `cd -; false && { cd /tmp; }; rm -rf s1` were ask on main and pass on the branch. Cause: the `{ cd /abs; }` unwrap (plus `[{]` in CW_HANDLED). Both removed; a cd inside `{ }` is now handled exactly as main handles it (never clears CWD_LOST). `cd /abs && ...` at top level still clears; the replay below shows no ask on main turning into pass.
- Ruling record: TC-104-18's brace half ("`{ cd /abs; }` clears, pass") is SUPERSEDED by the developer-agent ruling of 2026-10-17 (test-case.md is not edited). tests/confirm_cleanup_test.sh now pins TC-104-18 (`cd -; { cd /tmp; }; rm -rf s1`) and TC-104-18b (`cd -; false && { cd /tmp; }; rm -rf s1`) as ask; both are also appended to confirm_cleanup_shapes.txt as ask rows.
- Zero-loosening proof: every hook input of a whole `tests/confirm_cleanup_test.sh` run (all tc/tcp/tps/t cases, the rows of confirm_cleanup_shapes.txt, the new cases and the brace shapes) plus a second run with confirm_cleanup_shapes_main.txt as the shapes file, logged by a shim: 824 distinct inputs, each replayed through origin/main's hook (94a1c30; hooks/ identical to the merge-base 83c40bd) and through the branch hook, WSL, jq 1.7.1. Verdicts differ on 29 inputs, all pass -> ask. ask -> pass: 0. deny -> ask or pass: 0. Extra brace probes (`f() { cd /tmp; }; f`, `{ cd /tmp; rm -rf s1; }`, multi-line `{`, `true && { cd /tmp; } && rm -rf s1`): identical to main (ask).
- Every changed input (29 inputs = 17 distinct commands, some seen under more than one tool or cwd; @P = the run folder). All are pass on main, ask on the branch:

| # | cwd | tool | command |
|---|---|---|---|
| 1 | /tmp | Bash | `cd -; cd /tmp & rm -rf s1` |
| 2 | /tmp | Bash | `cd -; echo hi > s1` |
| 3 | /tmp | Bash | `cd -; true \|\| cd /tmp; rm -rf s1` |
| 4 | /tmp | Bash | `cd @P/rawdata; cd -; (cd /tmp); rm -rf s1` |
| 5 | /tmp | Bash | `cd @P/rawdata; cd -; : > s1` |
| 6 | /tmp | Bash | `cd @P/rawdata; cd -; rm -rf ~s1` |
| 7 | /tmp | Bash | `cd @P/rawdata; cd ~/x; rm -rf s1` |
| 8 | /tmp | Bash | `cd @P/results; cd ~; rm -rf x` (shapes.txt line 32) |
| 9 | /tmp | Bash | `cd $(echo /tmp); rm -rf s1` |
| 10 | /tmp | Bash | `cd $HOME/rawdata; rm -rf s1` |
| 11 | /tmp | Bash | `cd @P; cd $(printf results); rm -rf x` (TC-042) |
| 12 | /tmp | Bash | `cd @P; cd $d; rm -rf x` (TC-041, TC-078-24) |
| 13 | /tmp | Bash | `cd @P; cd ~; rm -rf x` (TC-078-27) |
| 14 | @P | Bash | `cd $HOME && rm -rf x` (#35 control) |
| 15 | any | PowerShell | `cd @P; sl -; Remove-Item -Recurse x` |
| 16 | any | PowerShell | `cd @P; sl; ...` and `cd @P; Set-Location; ...` |
| 17 | any | PowerShell | `cd @P; Set-Location 'tm\p'; Remove-Item -Recurse x` |

  The two brace shapes are not in the table: unchanged from main (ask).
- Known gap (no code): multi-line forms where `if` / `(` / `{` and the `cd` are on different lines are treated as before (same as main, not stricter). Earlier gaps stand.
- docs/TESTING.md steps for TC-104-40/43/45/51/52/53 are not required; per the developer-agent ruling these ledger records are accepted instead.
