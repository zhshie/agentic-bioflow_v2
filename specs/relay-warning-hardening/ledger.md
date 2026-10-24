# relay-warning-hardening progress ledger (third version: the simple route, ruling 5)

- [x] RED: tests/confirm_launch_test.sh, the old TC block (segment-tokenizer design) replaced by TC-001..064 rows (`envw`, `envbig`); 101 rows FAIL on the previous hook.
- [x] GREEN: hooks/confirm_launch.sh. The `relay_env_*` tokenizer and the `RELAY_ENV_RE_*` regexes are gone; one helper `relay_env_warn <VAR> <closing sentence>` (41 lines) after `ask()`, before the `#45` Write/Edit block. EXTRA is called first, PEER second. No on_site.sh exemption.
- Helper as built: first a `case` substring test (no `<VAR>=` -> return at once). Count: `${x//"$V="/}` on 8 KB windows (a window reaches `${#V}` characters into the next, so each match is counted once) with `LC_ALL=C` for the loop only (restored right after). First three: `${x%%"$V="*}` three times at most; last: one `${CMD%"$V="*}`. Each shown text is cut at space or `; & |`, then at 120 characters. Over 64 KB: header and count only. Header text is fixed; EXTRA closes with the old "overrides this deployment's list" sentence, PEER with the wording of the previous task plus the relay's own startup line ("peers :"). PEER also gets the empty-value sentence (word for word) when a listed text is empty.
- Deviation from the plan text (TC-047 c): the plan names one `${CMD//"$V="/}` for the count and `${x#*"$V="}` / `${CMD##*"$V="}` for the texts. Measured in WSL on 1 MB with 8000 mentions: the whole-string `//` took 3.0 s, and `#*` / `##*` are quadratic too (TC-048 at 60 KB took 1.3 s). TC-051 needs < 1 s, so the helper uses the windowed `//` and suffix removals described above (`%%` / `%`, which stop at the first letter that cannot match). No loop strips prefixes one match at a time. Result: TC-048 ~140 ms, TC-049 ~90, TC-050 ~90, TC-051 ~610-650 ms (limits 0.5 / 0.5 / 1.5 / 1 s).
- Interface of the helper: sets `RELAY_ENV_HEAD` (the whole warning: header, "Text after each V= as written (first 3 and last 1 of them): [a] [b]; N mentions in total.", closing sentence) and `RELAY_ENV_EMPTY`.

## Evidence (done-when)
- TC-034: `grep -c 'cpn,gpn,bgm,lgn,localhost' hooks/confirm_launch.sh` = 0.
- TC-037: the PEER closing sentence is the 2nd argument of `relay_env_warn NF_RELAY_PEER_PREFIXES` in the relay block: "...the relay's startup line (\"peers :\") shows the list it really uses. Show the user the prefixes it names." Test: TC-037 row.
- TC-042/063 (WSL): 60 commands (every new TC command shape for both variables, on_site.sh forms, stop/status/restart, agent_ctl start, NF_RELAY_PORT, NF_RELAY_EXTRA_NOTE, `ls`, a 70 KB command with and without the variable) through the base hook (`git archive origin/v3`) and the new one: `same_decision=60 ask_to_allow=0 warnings_lost=0` (every command whose base ask said `THIS COMMAND ALSO SETS V` has `THIS COMMAND ALSO MENTIONS V=` now). Allowed on both sides: `status`, `ls`, `cat`, an `echo`-only command.
- TC-043: `bash tests/confirm_launch_test.sh` on this branch: all passed, 0 FAIL (WSL). The lines that differ from the base are the ones listed under TC-044 plus new rows.
- TC-044: existing assertions changed (only the lines `git diff origin/v3...HEAD -- tests/confirm_launch_test.sh` shows as removed):
  - helper `envq`: header string `THIS COMMAND ALSO SETS NF_RELAY_PEER_PREFIXES` -> `THIS COMMAND ALSO MENTIONS NF_RELAY_PEER_PREFIXES=`; `PW_SETS` likewise.
  - PEER-3 text: `${PW_SETS}25a-cpn, which changes` -> `Text after each NF_RELAY_PEER_PREFIXES= as written (first 3 and last 1 of them): [25a-cpn]; 1 mention in total.`
  - PEER-4 text: `${PW_SETS}, which changes` -> `...: []; 1 mention in total.`
  - PEER-7 value: `${PW_SETS}25a-cpn,25a-lgn, which changes` -> `...: [25a-cpn,25a-lgn]; 1 mention in total.`
  - PEER-7 which hosts: `which changes which hosts may connect to the relay` -> `for the hosts that may connect, instead of the deployment's setting`; PEER-7 default list: `instead of the deployment's setting (default cpn,gpn,bgm,lgn,localhost)` -> `falls back to the built-in one`.
  - PEER-9: `lacks` -> `has`, label "it is named too" (ruling 5 point 2).
  No `idg` row, no `envp` row, and no other has/lacks expectation changed.
- TC-045: the new rows against the previous hook (hook of commit 000198f, at the RED commit): 101 rows FAIL, among them the TC-001 rows (header wording), TC-002, TC-004, TC-022..TC-029 and the PEER text rows.
- TC-046/047: `sed -n '/^relay_env_warn() {/,/^}/p' hooks/confirm_launch.sh` = 41 lines, the only helper; `grep -n 'relay_env_word\|relay_env_seg\|relay_env_exempt\|RELAY_ENV_RE_'` = 0 hits in hook and tests. In the helper the only `$(` hits are `$((` arithmetic; no backtick, grep, jq, python, sed, awk, tr, mktemp, eval, on_site; no `=~` at all; first step is the `case` substring test; no tokenizer, quote handling or exemption.
- TC-052/053 (WSL, ms, one run): ~100 KB without either variable: base 78, new 91. ~100 KB with 25 mentions and 3 starts (over 64 KB): base 75, new 94. Hook timeout 30 s.
- TC-054/055: `git diff --name-only origin/v3...HEAD` = hooks/confirm_launch.sh, tests/confirm_launch_test.sh, this ledger, plus plan.md / test-case*.md (given). `git diff origin/v3...HEAD -- scripts/ platform/ docs/ skills/ deploy/ commands/ hooks/hooks.json` = empty.
- TC-056: in the hook only the old EXTRA / PEER warning blocks were replaced (plus the helper block). `ask()`, `RELAY_START_RE`, `RESIDENT_RE`, `RELAY_DOMS`, the final `ask "GATE: ..."` call are untouched; no new `allow`, `exit` or `ask` call.
- TC-059: `relay_env_warn` is called twice, with NF_RELAY_EXTRA_DOMAINS and NF_RELAY_PEER_PREFIXES; rows TC-059 show NF_RELAY_PORT / NF_RELAY_EXTRA_NOTE are not named.
- TC-060: indirect assignment (`export $V=...`, `printf -v`, `env -S`) is not handled and stays unhandled: another task. The command `P=NF_RELAY_PEER_PREFIXES; export $P=evilval; bash scripts/egress_ctl.sh start` has no `V=` text, so no new header; the gate still asks (the start is a resident-process ask).
- TC-061: no validity check of prefixes, no eval, no expansion of `$VAR` / `$(...)`, no quote removal, no "computed at run time" logic.

## TC-062: the 14 review points
Round one (8) and round two (6), and what answers each:
1. (r1-1) empty-alternative regex does not compile -> not applicable: the helper has no regex at all (`=~` count 0); TC-001..TC-007 run every shape.
2. (r1-2) a decoy after the start changed the header -> not applicable: no "which one is the start" logic; TC-004.
3. (r1-3) dead code quote pattern -> not applicable: no quote handling; TC-010.
4. (r1-4) on_site.sh as a mere argument exempted / only one of two starts read -> not applicable: no exemption; TC-022..TC-029.
5. (r1-5) no left word boundary / `"a"b` shown wrong -> by design: any `V=` warns, text copied as written; TC-020, TC-010.
6. (r1-6) backtracking could time out -> TC-048, TC-049, TC-051 (timed).
7. (r1-7) single-quoted value mislabeled -> not applicable: no judgement of quoting; TC-010 (single-quoted row).
8. (r1-8) no test caught a regex compile failure -> not applicable: no regex; the whole file runs against the hook.
9. (r2-1) counting loop quadratic at 60 KB -> TC-049 / TC-051 (windowed count, see the deviation note).
10. (r2-2) `on_site.sh env V=evil egress_ctl.sh start` bypass -> TC-024.
11. (r2-3) last value is not always the one that takes effect -> TC-001 / TC-002 (no claim which value takes effect; every mention shown).
12. (r2-4) escaped quote makes the value eat the rest of the line -> TC-010 (third row).
13. (r2-5) `nohup` / `sudo` wrappers not recognised -> TC-007.
14. (r2-6) the plan lists only five second-round points (see the question in the overview); the sixth was not given. Covered in general by the fact that nothing is parsed: the answer to anything not named is "the text is there, so the warning is there".
