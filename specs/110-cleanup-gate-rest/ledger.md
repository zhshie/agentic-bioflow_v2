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
