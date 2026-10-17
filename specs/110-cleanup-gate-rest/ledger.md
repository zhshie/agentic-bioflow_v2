# Ledger 110-cleanup-gate-rest

- 2026-10-17 plan written by the developer-agent.

## TC-110-74 red first (honest record)
- RED commit `f343b3f` (tests only). Run against the pre-change hook, 33 cases failed, all for the stated reason: Part 1 asks that were passes (TC-110-01..15, 22..27, 32..36) and Part 2 spurious asks (TC-110-44, 45, 46, 47, 48, 49, 51). GREEN commits: `21ec62d`, `db3cb2a`, and the fix round below.
- Plan wording error, recorded as found: the plan said TC-110-50 (`cd /tmp # a | b` from a known folder) would fail before the fix. It does not; origin/main already passes it when the folder is known. The real red for the comment case is TC-110-49 (`cd -; cd /tmp # a | b`).

## Fix round 2026-10-17 (acceptance round 1, developer-agent ruling)
- Part 2 relief is limited: a quoted `>` is text only when the segment's command word is one of echo, printf, git, grep, egrep, fgrep, rg, jq. Any other command word (awk, gawk, perl, python, sed, sh -c, env, xargs, ...) still gets the #104 quote-blind scan, so a quoted `>` there asks as on main. Accepted cost: `awk '$1>3' f` asks (TC-110-45 expectation changed to ask in tests and shapes; the plan carries the ruling).
- `[ a > s1 ]` (single bracket) is a redirect and asks; only `[[ ... > ... ]]` and `[ a \> b ]` are comparisons. The backslash-stripped copy row the splitter adds is no longer scanned for redirects (it would read `\>` as `>`).
- Shapes file: added rows for TC-110-27, 47, the controls (`ls > s1` known folder, `cd -; sort s1`, `tee /tmp/s1`, `cd /tmp; echo x > "$F"`, plain cd controls, quoted-target forms) and the four probes as ask.

## TC-110-72 / 73 replay (hooks run over every input of tests/confirm_cleanup_test.sh and tests/confirm_cleanup_shapes.txt; 995 verdicts each)
confirm_cleanup_shapes_main.txt holds main's verdicts for the shapes file (the expected-value column the timing test reads), not extra inputs. Full per-input table: `replay.tsv` (input, 94a1c30, origin/main, branch).
- Branch vs 94a1c30: 104 changed, all pass->ask. Ask->pass: 0. Deny weakened: 0.
- Branch vs origin/main: 64 changed. 52 pass->ask (Part 1 closes lost-folder bypasses; plus the new probes). 12 ask->pass, listed:
  - TC-110-44 `echo "x>y"`; TC-066 `cd -; echo "x>y"` (quoted `>` in echo: text)
  - TC-110-46 `[[ a > b ]]`; TC-066 same (comparison)
  - TC-110-47 `[ a \> b ]`; TC-066 same (escaped `>`, comparison)
  - TC-110-48 `git log --format='a->b'`; TC-066 same (quoted, git)
  - TC-110-49 `cd -; cd /tmp # a | b` plus a relative delete after; TC-066 same input (comment text; the cd really clears)
  - TC-110-51 `cd -; cd /tmp; echo "a&b"` plus a relative delete after; TC-066 same input (quoted `&` is text; the cd really clears)
  None writes a file. The two with a following relative delete act only inside the folder the cd really set, the same pass verdict as 94a1c30 and as `cd /tmp` followed by that delete already gets; they are listed because they contain a delete verb.
- The four probes through all three hooks: `cd -; awk 'BEGIN{print "x" > "s1"}'`, `cd -; gawk '{print > FILENAME".bak"}' f`, `cd -; perl -e 'open(F,">s1")'`, `cd -; [ a > s1 ]`: 94a1c30 pass, origin/main ask, branch ask.

## Fix round 3 (acceptance round 2 + review on #111, 2026-10-17) - supersedes the Part 2 entries above
- PART 2 DROPPED (developer-agent ruling after /code-review on #111). Removed: the quoted-`>` relief for any command (including the earlier echo/printf/git/grep/rg/jq list), the `[[ a > b ]]` / `[ a \> b ]` comparison relief, `strip_quoted` in the cd condition (comment/quote-aware), and the IS_COPYROW redirect skip. The #104 quote-blind redirect scan now runs unchanged on every segment (copy rows included); the new quote-aware scan only adds. The large-input filter keeps every segment whose quote-kept text holds a `>`.
- Test expectations reverted to main's (ask), labelled "Part 2 dropped 2026-10-17 (review on #111)": TC-110-44, 46, 47, 49, 51 (and their TC-066 shapes rows). TC-110-48 (`git log --format='a->b'`) is superseded to ask (git is no longer text-only); TC-110-45 was already ask. test-case.md not edited.
- Part 1 kept, plus round-3 additions: cd after a line ending in `&&`/`||`/`|` does not clear (comment-only lines skipped); `&>` / `&>>` to a relative target ask; `<>` asks; `sed -i` with an attached script (`-es/a/b/`, `-nes/a/b/`, `-ni -e..`) still checks the file operand; writer targets with `$` / `$(...)` / backticks (`tee $F`, `cp a $F`, `sort -o "$F"`, `dd of=$(x)`) ask under a lost folder (absolute targets still pass); `sort --o=`/`--ou=`/`--out=`/... and `--out FILE` prefixes.
- Red/green: RED commit holds the tests for git/rg probes, continuation lines, `&>` (20 failed on the old hook); the later tests (writer targets, sed clusters, sort abbreviations, `<>`, `echo "echo hi > f" | bash`, PowerShell `\>`) were added together with the hook change in the GREEN commit (not run red separately - recorded honestly).
- KNOWN GAPS (go to the ledger, not fixed): writers nested or wrapped so the lost-folder scan does not see their target as a word of its own segment: `( cp a s1 )`, `{ tee s1; }`, `if ..; then tee s1; fi`, `xargs tee s1`, `find . -exec cp a s1 \;`. Also: `>>` append stays as on main; a relative delete through a variable.
- Replay (three trees: 94a1c30, origin/main, branch; replay.tsv now has columns tool, cwd, input, 94a1c30, origin/main, branch): 2132 inputs = the 1063 inputs the confirm_cleanup test and shapes file feed the hook (captured through a recording shim) + 1009 reconstructed probes (the verifier's four plus ~170 command bodies across git/rg/awk/perl/python/sh -c/eval/xargs/find -exec/tee/cp/sort/sed/dd/redirect forms/cd-condition forms, each under six lost-folder prefixes and bare) + 143 of them behind a 600-line heredoc (large-input path). The verifier's own 166 probes were not available to me, so this set is a reconstruction.
  - Branch vs origin/main: 467 pass->ask, 0 ask->pass, 0 deny weakened, 0 other changes.
  - Branch vs 94a1c30: 922 pass->ask, 0 ask->pass, 0 deny weakened.
