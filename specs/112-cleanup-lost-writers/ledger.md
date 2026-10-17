# cleanup gate: writers that still pass after a lost folder (#112) progress ledger

## Done (executor)
- [x] RED `e37e53f`: probes TC-112-01..65 (the automatic ones) added to `tests/confirm_cleanup_test.sh`; 40 failed on the base, as expected.
- [x] GREEN: `hooks/confirm_cleanup.sh`:
  - one redirect scanner `lost_redirects` (the quote-blind `lost_redirects_blind` is gone); a plain `>` is read as the shell reads it, a quoted or escaped `>` is read blind as on main (items 1, 3, 8);
  - `lost_target` treats `-name` as a file name and a quoted `~` as a relative folder (items 1, 3);
  - `lost_writers` rewritten on a quote-aware word list (`lw_tokens`, `lw_cmd`): `--` ends options (item 2); new writers install, ln, shuf, split, curl, wget, perl -i, awk/gawk -i inplace (item 4); `{`, then, do, else, elif, if, while, until in front of a command are skipped (item 7); `xargs` and `find -exec/-execdir/-ok/-okdir` ask when the inner command writes (item 7);
  - `>(...)` and `<(...)`: the splitter already emits the inner command as a segment of its own, so each is scanned as a command (item 5); pinned by TC-112-39/40/41;
  - `cd /abs` clears the lost state only if `[ -d ]` holds at check time (item 6);
  - `lost_ask` prints a reason once (item 8);
  - the large-input filter (CW_HANDLED, RE_TRIGGER) keeps the new command words, the `-exec` forms and the block keywords, so the behind-heredoc run gets the same verdicts.

## Existing expectations changed (all named in the plan)
| Test | Old | New | Reason |
|---|---|---|---|
| TC-110-66 `cd -; cd /no/such/dir;` then a delete of `s1` | pass | ask | item 6: a missing absolute folder keeps the state lost |
| TC-078-19 `cd -; cd $P;` then a delete of `x` | pass | pass, command now `cd $EXD` (a `mktemp -d` folder) | `$P` does not exist on the test machine, so it no longer clears; the meaning "an absolute cd to a real folder recovers" is kept |
| TC-104-19 same shape | pass | pass, command now `cd $EXD` | same |

No other existing expectation was edited (`confirm_cleanup_shapes*.txt` untouched; `shapes.txt:237` is still pass).

## Probes that already asked on main ("ask on main, ask here")
TC-112-39 `echo x > >(tee s1)`, TC-112-40 `cat <(tee s1)`, TC-112-48 `( cp a s1 )`.

## Replay (specs/110-cleanup-gate-rest/replay.tsv, 2132 rows, branch hook vs its base 5b3bf22, hook text only)
- ask/deny to pass: **0**.
- pass to ask: 37, all inside plan items.
  - item 6: `cd -; cd /no/such/dir;` + delete, `cd -; cd /work/u9613010/lab_runs/x;` + delete, and 6 rows of `<lost>; cd '/tmp;' ;` + delete (a folder that does not exist);
  - item 7: for each of the 6 lost states (`cd -`, `cd $(pwd)`, `cd "$d"`, `cd ~`, `cd`, `popd`): `echo x | xargs tee s1`, `find . -exec cp a s1 \;`, `find . -exec tee s1 \;`, `if true; then tee s1; fi`, `{ tee s1; }`.
- Note: the local `main` branch is behind origin/main (it lacks #110/#111), so the comparison base is the branch point 5b3bf22.

## Not in this PR
- #112 item 7 (performance of the large-input filter) is left as is; it is already fail-closed. `tests/confirm_cleanup_candidates_timing_test.sh` is not edited.

## Fix round (verifier finding on TC-112-66: wrapper words)
- Finding: the rewritten `lost_writers` did not see through `sudo|env|command|builtin|exec|nohup|time|nice|stdbuf|timeout`, so `cd -; sudo cp a s1` asked on main and passed on the branch (ask to pass, a #29-type regression). The replay file has no such rows, so "ask/deny to pass: 0" above held only for it.
- RED `tests/confirm_cleanup_test.sh`: 19 probes labelled `TC-112-66w` (the verifier's shapes, plus `sudo nice -n 5 timeout 5 cp`, `timeout -k 1 5 cp`, `nohup xargs tee`, and one control: `sudo cp a /tmp/s1` passes); 18 failed before the fix.
- GREEN `hooks/confirm_cleanup.sh` `lost_writers`: after a wrapper word, every word that could be the command (past options, numbers/durations, VAR=, the value word of an option) is tried until the first known writer. This is fail closed: `sudo -u x cp`, `sudo -n cp`, `nice -n 5 cp`, `env -i cp`, `timeout -k 1 5 cp` all ask. With no wrapper the old path is unchanged.
- Differential, main vs branch, cwd=/tmp: 4 lost states x 19 wrapper forms x 14 commands (cp, tee, tee -a, sort -o, sed -i, dd of=, mv, install, ln, curl -o, xargs tee, `>` redirect, rm, touch) = 1064 sentences. Ask/deny to pass: **0**. Every difference is pass to ask, and all are the new writers of plan item 4/7 (install, ln, curl, xargs) or a wrapped writer main did not see either way.
- No existing expectation was edited in this round.
- Second part of the fix (found by the full suite at the first GREEN: `confirm_cleanup_behind_heredoc_test.sh` failed `TC-112-66w timeout -k`): behind a large here-doc the large-input filter dropped `timeout -k 1 5 cp a s1` and `sudo -n cp a s1`, because `cmdword()` reads `1` / `a` as their command word (same on main). RED added 3 probes (`sudo -n cp`, `sudo -n tee`, `env -i tee`); GREEN: `RE_TRIGGER` keeps any segment that starts with a wrapper word. Tighter only (more segments kept).

## Fix round 2 (verifier finding on TC-112-66: backslash-escaped writer operands)
- Finding: after a lost folder main asked and the branch passed for `cp a \-x`, `tee \-x`, `sed -i p \-x`, `dd of=\~ if=a`, `sed -i p \~`, `cp --target-directory=\~ a`, and a lone trailing backslash (`cp a \`, `tee \`, `sort -o \`, `dd of=\`, `cp a \ `). Cause: `lw_tokens` dropped the backslash, so `\-x` looked like an option, `of=\~` / `--target-directory=\~` lost the "quoted tilde" mark (it only covered a word that starts with `~`), and a lone `\` became an empty word.
- Main reads the raw text cut at every space (no quote or escape awareness), so every word that is not literally `/...` is relative to it. The differential found more of the same family, all fixed here:
  - `\/tmp/x`, `-t\/tmp/x`, `--target-directory=\/tmp/x`, `sort -o\/tmp/x`, `of=\/tmp/x`: an escaped `/` now adds `./` in front, so it is relative;
  - quoted names with a space (`tee "/tmp/my file"`, `cp a '/tmp/x y'`) and a single operand with a space (`cp "a b"`, `cp \ a`): new `lw_target` also checks every piece cut at a space (tighter than main only where main passed);
  - a sed script with a space (`sed -i 's/a b/c/' /tmp/x`, `sed -i '1 d' f`, `sed -i -e 'a b' f`): the words after the first space of the script are file candidates again (main asks for them, as a false positive);
  - an empty quoted name (`cp -t '' a`) is `./`.
- `lw_tokens` now: every `~` in a word that had a quote or backslash becomes `./~`; a word whose first raw char is a backslash and that cooks to `-...` gets `./` in front; a backslash at the end of the text is the file name `\`; an escaped `/` gets `./` in front; an empty quoted word is `./`.
- RED (tests/confirm_cleanup_test.sh, labels `TC-112-66e`, 34 probes; 33 asks failed before, the 3 controls passed): `4c24618`, then the two later RED commits. GREEN: `fb8231e` and the commit after the last RED.
- Differential, main vs branch, cwd=/tmp, `cd -` and 3 more lost states, 6845 + 1280 sentences (37 writer forms x escaped / quoted / spaced / empty operands): ask/deny to pass **0** (the remaining differences are pass to ask, mostly the new writers of plan item 4/7).
- Replay (specs/110-cleanup-gate-rest/replay.tsv, 2132 rows, main vs branch): ask/deny to pass **0**, pass to ask 37 (as before).
- Known and left (main passes too, so not a regression): `xargs env tee`, `xargs timeout 5 cp a s1`, `find . -exec nohup cp a s1 \;`, `find . -fprint s1`, `curl -D s1`, `awk -iinplace`.
- No existing expectation was edited in this round.
