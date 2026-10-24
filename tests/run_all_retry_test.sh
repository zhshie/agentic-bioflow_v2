#!/bin/bash
# Tests for tests/run_all.sh --retry-failed-once and the quarantine list
# (tests/quarantine.txt). Task ci-quarantine; TC ids are those of the task's
# contract file.
#
# Every run goes through a throw-away copy of run_all.sh in a sandbox root that
# holds only tiny fake test files, so this file never runs the real suite (that
# would recurse). A fake `uname` answering Linux lets it run on Git Bash too.
# The only runs against the real tree are --check-quarantine and --list, which
# execute no test.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_ROOT="$(cd "$HERE/.." && pwd)"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0
SR="$TMP/sr"; CNT="$TMP/cnt"; TMPD="$TMP/tmpd"
UNAME_DIR="$TMP/uname"; mkdir -p "$UNAME_DIR"
printf '#!/bin/sh\necho Linux\n' > "$UNAME_DIR/uname"; chmod +x "$UNAME_DIR/uname"
BASE_TODAY=2026-10-24

t() { local l=$1; shift; printf '%-70s ' "$l"; if "$@"; then echo ok; else echo FAIL; fails=$((fails+1)); fi; }
rc_is()   { [ "$RC" = "$1" ]; }
out_has() { grep -qF -- "$1" <<<"$OUT"; }
out_no()  { ! grep -qF -- "$1" <<<"$OUT"; }
out_re()  { grep -qE -- "$1" <<<"$OUT"; }
err_has() { grep -qF -- "$1" <<<"$ERR"; }
cnt_is()  { local n=0; [ -f "$CNT/c.$1" ] && n=$(wc -l < "$CNT/c.$1" | tr -d ' '); [ "$n" = "$2" ]; }
no_cnt()  { [ -z "$(ls "$CNT" 2>/dev/null)" ]; }

reset() {
  command rm -rf "$SR" "$CNT" "$TMPD"
  mkdir -p "$SR/tests" "$SR/scripts/utils" "$CNT" "$TMPD"
  cp "$HERE/run_all.sh" "$SR/tests/run_all.sh"
  cp "$REAL_ROOT/scripts/utils/portable.sh" "$SR/scripts/utils/portable.sh"
}
mk_ok() { printf '#!/bin/bash\necho x >> "%s/c.%s"\nexit 0\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
mk_flaky() {
  printf '#!/bin/bash\nf="%s/c.%s"; n=0; [ -f "$f" ] && n=$(( $(wc -l < "$f") )); echo x >> "$f"\n[ "$n" -ge 1 ]\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
mk_bad() {
  printf '#!/bin/bash\nf="%s/c.%s"; n=0; [ -f "$f" ] && n=$(( $(wc -l < "$f") )); echo x >> "$f"\nif [ "$n" -ge 1 ]; then echo second-run-marker; else echo first-run-marker; fi\nexit 1\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
mk_slow() {
  printf '#!/bin/bash\nf="%s/c.%s"; n=0; [ -f "$f" ] && n=$(( $(wc -l < "$f") )); echo x >> "$f"\n[ "$n" -ge 1 ] || sleep 3\nexit 0\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
mk_slow_always() { printf '#!/bin/bash\necho x >> "%s/c.%s"\nsleep 3\nexit 0\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
setq() { printf '%s\n' "$@" > "$SR/tests/quarantine.txt"; }

# run <args...>: the sandbox runner; sets OUT, ERR, RC.
run() {
  local today_env="RUN_ALL_TODAY=${TODAY:-$BASE_TODAY}"
  [ -n "${NOTODAY:-}" ] && today_env="NOTODAY_PLACEHOLDER=1"
  OUT=$(env ${NOTODAY:+-u RUN_ALL_TODAY} "$today_env" \
        TMPDIR="$TMPD" PATH="${EXTRAPATH:+$EXTRAPATH:}$UNAME_DIR:$PATH" \
        bash "$SR/tests/run_all.sh" --allow-missing-tools "$@" 2>"$TMP/err"); RC=$?
  OUT=$(sed -E "s/ - run with --allow-missing-tools, .* missing//" <<<"$OUT")
  ERR=$(cat "$TMP/err")
}
normalize() { sed -E 's/ - run with --allow-missing-tools, .* missing//; s/ +[0-9]+s$//; s/^root:.*/root: X/; /^logs:/d'; }

F=--retry-failed-once

# ---- A. no flag = today's behaviour -------------------------------------
reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; run
norm=$(normalize <<<"$OUT")
exp="$(printf 'root: X\nversion: unknown\n\n%-46s ok\n%-46s ok\n\n2/2 passed\nall green' ok_test.sh ok_two_test.sh)"
t "TC-001 no flag: output identical to today's text" test "$norm" = "$exp"
t "TC-001 no flag: exit 0" rc_is 0

reset; mk_ok ok_test.sh; mk_bad bad_test.sh; run
t "TC-002 no flag + bad: exit 1" rc_is 1
t "TC-002 summary 1/2 passed, 1 failed" out_has "1/2 passed, 1 failed"
t "TC-002 bad ran once" cnt_is bad_test 1
t "TC-002 no FLAKY in output" out_no "FLAKY"
t "TC-002 no retry in output" out_no "retry"

reset; mk_flaky flaky_test.sh; run
t "TC-003 no flag + flaky: exit 1" rc_is 1
t "TC-003 ran once (strict single run)" cnt_is flaky_test 1
t "TC-075 same: no auto retry on the local run" out_no "retry"

reset; mk_ok ok_test.sh; setq 'garbage ((( line' 'tests/nope.sh x y z w'; run
t "TC-004 no flag: garbage list is never read (exit 0)" rc_is 0
t "TC-004 no quarantine message at all" bash -c '! grep -q "quarantine:" <<<"$0$1"' "$OUT" "$ERR"

reset; mk_ok ok_test.sh; run --help
t "TC-005 --help mentions --retry-failed-once" err_has "--retry-failed-once"
t "TC-005 --help mentions --check-quarantine" err_has "--check-quarantine"

reset; mk_ok ok_test.sh; run --no-such-flag
t "TC-006 unknown flag: exit 2" rc_is 2
t "TC-006 unknown flag: says unknown option" err_has "unknown option"
run $F --no-such-flag
t "TC-006 unknown flag with retry flag: exit 2" rc_is 2
t "TC-006 nothing was run" no_cnt

t "TC-007 header has no hard-coded number >= 10" bash -c '! head -20 "$0" | grep -qE "(^|[^[:alnum:]])[0-9]{2,}([^[:alnum:]]|\$)"' "$HERE/run_all.sh"
t "TC-007 header still says run time" bash -c 'head -20 "$0" | grep -qiE "run ?time"' "$HERE/run_all.sh"

listed=$(bash "$HERE/run_all.sh" --list); n_list=$(printf '%s\n' "$listed" | grep -c .)
n_real=$(ls "$HERE"/*.sh | grep -vc '/run_all\.sh$')
t "TC-008 --list count equals tests/*.sh minus run_all.sh" test "$n_list" = "$n_real"
t "TC-008 --list includes run_all_retry_test.sh" grep -q 'run_all_retry_test\.sh' <<<"$listed"

# ---- B. flag, nothing fails ---------------------------------------------
reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; run $F
t "TC-011 all green + flag: exit 0" rc_is 0
t "TC-011 says all green" out_has "all green"
t "TC-011 no FLAKY" out_no "FLAKY"
t "TC-011 no retry heading" out_no "== retry"
t "TC-011 each ran once" bash -c '[ "$(wc -l < "$0/c.ok_test")" = 1 ] && [ "$(wc -l < "$0/c.ok_two_test")" = 1 ]' "$CNT"
reset; mk_ok ok_test.sh; : > "$SR/tests/quarantine.txt"; run $F
t "TC-012 empty list: exit 0" rc_is 0
t "TC-012 empty list: all green" out_has "all green"
reset; mk_ok ok_test.sh; run $F
t "TC-013 no list file: exit 0" rc_is 0
t "TC-013 no list file: all green" out_has "all green"

# ---- C. retry and FLAKY -------------------------------------------------
reset; mk_ok ok_test.sh; mk_flaky flaky_test.sh; run $F
t "TC-014 unquarantined flaky: exit 1" rc_is 1
t "TC-014 FLAKY line at line start, NOT in list" out_re '^FLAKY flaky_test\.sh +NOT in tests/quarantine\.txt'
t "TC-015 stderr: FLAKY not quarantined: flaky_test.sh" err_has "FLAKY not quarantined: flaky_test.sh"
t "TC-015 stderr: Fix the test" err_has "Fix the test"
t "TC-015 stderr: names the list file" err_has "tests/quarantine.txt"
t "TC-015 stderr: format hint" err_has "tests/<name>.sh <issue> <YYYY-MM-DD> (at most 14 days out)"
t "TC-077 unquarantined flaky never green" out_no "green after retry"

reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; mk_flaky flaky_test.sh; setq '# c' 'tests/flaky_test.sh #12 2026-11-01'; run $F
t "TC-016 quarantined flaky: exit 0" rc_is 0
t "TC-016 FLAKY line with issue and date" out_re '^FLAKY flaky_test\.sh +quarantined #12 until 2026-11-01'
t "TC-017 last line says green after retry: 1" bash -c 'tail -1 <<<"$0" | grep -qF "green after retry: 1"' "$OUT"
t "TC-017 never says all green" out_no "all green"
t "TC-018 summary stays first-round: 2/3 passed, 1 failed" out_has "2/3 passed, 1 failed"
sumln=$(grep -n 'passed' <<<"$OUT" | head -1 | cut -d: -f1)
hdrln=$(grep -n '^== FLAKY (failed the first run, passed the retry) ==$' <<<"$OUT" | head -1 | cut -d: -f1)
flkln=$(grep -n '^FLAKY flaky_test.sh' <<<"$OUT" | head -1 | cut -d: -f1)
t "TC-019 FLAKY heading is after the summary line" test -n "$hdrln" -a "${hdrln:-0}" -gt "${sumln:-99999}"
t "TC-019 FLAKY line is under the heading" test -n "$flkln" -a "${flkln:-0}" -gt "${hdrln:-99999}"
t "TC-020 red still shown: output heading" out_has "== output of what did not pass =="
t "TC-020 red still shown: --- flaky_test.sh ---" out_has "--- flaky_test.sh ---"
t "TC-021 ok ran once" cnt_is ok_test 1
t "TC-021 flaky ran exactly twice" cnt_is flaky_test 2

reset; mk_flaky a_flaky_test.sh; mk_flaky b_flaky_test.sh; run $F
t "TC-022 retry heading names the count" out_has "== retry: re-running 2 file(s) once =="
la=$(grep -n '^retry a_flaky_test.sh \.\.\. ok' <<<"$OUT" | cut -d: -f1)
lb=$(grep -n '^retry b_flaky_test.sh \.\.\. ok' <<<"$OUT" | cut -d: -f1)
t "TC-022 retried in first-round order" test -n "$la" -a -n "$lb" -a "${la:-9}" -lt "${lb:-0}"

reset; mk_bad bad_test.sh; run $F
t "TC-023 bad twice: exit 1" rc_is 1
t "TC-023 ran twice" cnt_is bad_test 2
t "TC-023 FAILED twice block" out_has "== FAILED twice =="
t "TC-023 FAILED bad_test.sh" out_has "FAILED bad_test.sh"
t "TC-023 retry line FAIL" out_re '^retry bad_test\.sh \.\.\. FAIL'
t "TC-024 not reported as FLAKY" out_no "FLAKY bad_test.sh"
t "TC-024 shows the retry log tail (second-run-marker)" out_has "second-run-marker"
t "TC-076 never green after retry" out_no "green after retry"

reset; mk_bad bad_test.sh; setq 'tests/bad_test.sh #12 2026-11-01'; run $F
t "TC-025 quarantined bad still exit 1" rc_is 1
t "TC-025 still FAILED bad_test.sh" out_has "FAILED bad_test.sh"

reset; mk_ok ok_test.sh; mk_slow slow_test.sh; run $F --timeout 1
t "TC-026 timeout then pass = FLAKY, not listed" out_re '^FLAKY slow_test\.sh +NOT in tests/quarantine\.txt'
t "TC-026 exit 1" rc_is 1
reset; mk_ok ok_test.sh; mk_slow slow_test.sh; setq 'tests/slow_test.sh #12 2026-11-01'; run $F --timeout 1
t "TC-027 quarantined slow flaky: exit 0" rc_is 0
t "TC-027 FLAKY line with issue" out_re '^FLAKY slow_test\.sh +quarantined #12'

reset; mk_slow_always slow_always_test.sh; run $F --timeout 1
t "TC-028 retry line TIMEOUT" out_re '^retry slow_always_test\.sh \.\.\. TIMEOUT'
t "TC-028 in FAILED twice" out_has "FAILED slow_always_test.sh"
t "TC-028 exit 1" rc_is 1
t "TC-028 no FLAKY" out_no "FLAKY"

reset; mk_flaky a_flaky_test.sh; mk_flaky b_flaky_test.sh; setq 'tests/a_flaky_test.sh #12 2026-11-01'; run $F
t "TC-029 one quarantined, one not: exit 1" rc_is 1
t "TC-029 error names the unquarantined one" err_has "FLAKY not quarantined: b_flaky_test.sh."
t "TC-029 error does not name the quarantined one" bash -c '! grep "^FLAKY not quarantined" <<<"$0" | grep -qF a_flaky_test.sh' "$ERR"

reset; mk_flaky flaky_test.sh; mk_bad bad_test.sh; setq 'tests/flaky_test.sh #12 2026-11-01'; run $F
t "TC-030 quarantined flaky + real red: exit 1" rc_is 1

reset; mk_ok ok_test.sh; mk_flaky flaky_test.sh; setq 'tests/flaky_test.sh #12 2026-11-01'; run $F --only flaky
t "TC-031 --only flaky: ok_test not run" cnt_is ok_test 0
t "TC-031 --only flaky: flaky ran and retried" cnt_is flaky_test 2

reset; mk_ok ok_test.sh; mk_flaky flaky_test.sh; run --list; plain="$OUT"; prc=$RC
run $F --list
t "TC-032 --list identical with the flag" test "$OUT" = "$plain"
t "TC-032 --list exit 0 both ways" test "$RC" = 0 -a "$prc" = 0

# ---- D. list validation -------------------------------------------------
reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; setq '# header' 'tests/ok_test.sh #12 2026-10-23'; run $F
t "TC-034 expired: exit 1" rc_is 1
t "TC-034 stderr has file:line" err_has "quarantine: tests/quarantine.txt:2:"
t "TC-034 mentions expired" err_has "expired"
t "TC-035 no test ran before validation" no_cnt
setq 'tests/ok_test.sh #12 2026-10-23'; run $F
t "TC-047 expired but all tests green: still exit 1" rc_is 1

chk_valid() { # chk_valid <label> <line> [today]  -> expects exit 0
  reset; mk_ok ok_test.sh; setq "$2"; TODAY=${3:-$BASE_TODAY} run $F; t "$1" rc_is 0; }
chk_bad() {   # chk_bad <label> <line> [today] [needle] -> expects exit 1
  reset; mk_ok ok_test.sh; setq "$2"; TODAY=${3:-$BASE_TODAY} run $F; t "$1" rc_is 1
  [ -n "${4:-}" ] && t "$1 (message)" err_has "$4"; return 0; }
chk_valid "TC-036 expiry today is valid" 'tests/ok_test.sh #12 2026-10-24'
chk_valid "TC-037 today+14 is valid" 'tests/ok_test.sh #12 2026-11-07'
chk_bad   "TC-038 today+15 is rejected" 'tests/ok_test.sh #12 2026-11-08' "" "14 days"
chk_bad   "TC-039 missing issue column" 'tests/ok_test.sh 2026-11-01' "" "quarantine: tests/quarantine.txt:1:"
chk_valid "TC-040 issue #12" 'tests/ok_test.sh #12 2026-11-01'
chk_valid "TC-040 issue URL" 'tests/ok_test.sh https://github.com/zhshie/agentic-bioflow/issues/12 2026-11-01'
for bad in 12 '#' 'https://example.com/x'; do chk_bad "TC-041 issue '$bad'" "tests/ok_test.sh $bad 2026-11-01"; done
for bad in 2026-13-40 2026-2-3 not-a-date; do chk_bad "TC-042 date '$bad'" "tests/ok_test.sh #12 $bad"; done
for bad in tests/nope_test.sh ../x.sh tests/a.txt; do chk_bad "TC-043 path '$bad'" "$bad #12 2026-11-01"; done
reset; mk_ok ok_test.sh; setq 'tests/ok_test.sh #12 2026-11-01' 'tests/ok_test.sh #13 2026-11-02'; run $F
t "TC-044 same path twice: exit 1" rc_is 1
chk_bad   "TC-045 fourth column rejected" 'tests/ok_test.sh #12 2026-11-01 extra'
reset; mk_ok ok_test.sh; printf '# note\r\n\r\ntests/ok_test.sh #12 2026-11-01\r\n' > "$SR/tests/quarantine.txt"; run $F
t "TC-046 comments, blank lines and CRLF tolerated" rc_is 0
chk_valid "TC-048 leap year edge valid"   'tests/ok_test.sh #12 2028-03-05' 2028-02-20
chk_bad   "TC-048 leap year edge +1 bad"  'tests/ok_test.sh #12 2028-03-06' 2028-02-20
chk_valid "TC-049 new year edge valid"    'tests/ok_test.sh #12 2027-01-08' 2026-12-25
chk_bad   "TC-049 new year edge +1 bad"   'tests/ok_test.sh #12 2027-01-09' 2026-12-25

reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; setq 'tests/ok_test.sh #12 2026-11-01'; run --check-quarantine
t "TC-050 --check-quarantine valid: exit 0" rc_is 0
t "TC-050 ran no test" no_cnt
t "TC-050 made no log dir" bash -c '[ -z "$(ls "$0" 2>/dev/null)" ]' "$TMPD"
setq 'tests/ok_test.sh #12 2026-10-23'; run --check-quarantine
t "TC-051 --check-quarantine invalid: exit 1" rc_is 1
t "TC-051 prints the line message" err_has "quarantine: tests/quarantine.txt:1:"

OUT=$(env PATH="$UNAME_DIR:$PATH" bash "$HERE/run_all.sh" --allow-missing-tools --check-quarantine 2>&1); RC=$?
t "TC-052 real tree: --check-quarantine exit 0" rc_is 0

reset; mk_ok platform_test.sh; setq 'tests/platform_test.sh #12 2026-11-01'; run $F
t "TC-053 platform_test.sh may not be quarantined (exit 1)" rc_is 1
t "TC-053 message names line" err_has "quarantine: tests/quarantine.txt:1:"
t "TC-053 message says platform_test.sh" err_has "platform_test.sh"

reset; mk_ok ok_test.sh; setq 'tests/ok_test.sh #12 2026-10-23' 'tests/ok_test.sh x 2026-11-01'; run $F
t "TC-054 one message per bad line (line 1)" err_has "quarantine: tests/quarantine.txt:1:"
t "TC-054 one message per bad line (line 2)" err_has "quarantine: tests/quarantine.txt:2:"
t "TC-054 exit 1" rc_is 1

reset; mk_ok ok_test.sh; setq 'tests/ok_test.sh #12 2000-01-01'; NOTODAY=1 run $F
t "TC-055 system date: 2000-01-01 is expired (exit 1)" rc_is 1
t "TC-055 system date: says expired" err_has "expired"
setq "tests/ok_test.sh #12 $(date +%F)"; NOTODAY=1 run $F
t "TC-055 expiry = system today is valid" rc_is 0
NOTODAY=

# TC-056: no python3, and a date that fails when asked for a relative date.
mkdir -p "$TMP/shim"
printf '#!/bin/sh\ncase "$*" in *"print(1)"*) exit 127;; esac\necho called > "%s/python-called"\nexit 127\n' "$TMP" > "$TMP/shim/python3"
REALDATE=$(command -v date)
printf '#!/bin/sh\nfor a in "$@"; do case "$a" in -d|--date*) echo called > "%s/date-rel-called"; exit 1;; esac; done\nexec "%s" "$@"\n' "$TMP" "$REALDATE" > "$TMP/shim/date"
chmod +x "$TMP/shim/python3" "$TMP/shim/date"
EXTRAPATH="$TMP/shim"
chk_valid "TC-056 shimmed: leap edge valid"  'tests/ok_test.sh #12 2028-03-05' 2028-02-20
chk_bad   "TC-056 shimmed: leap edge bad"    'tests/ok_test.sh #12 2028-03-06' 2028-02-20
chk_valid "TC-056 shimmed: year edge valid"  'tests/ok_test.sh #12 2027-01-08' 2026-12-25
chk_bad   "TC-056 shimmed: year edge bad"    'tests/ok_test.sh #12 2027-01-09' 2026-12-25
t "TC-056 neither python3 nor a relative date was used" bash -c '[ ! -e "$0/python-called" ] && [ ! -e "$0/date-rel-called" ]' "$TMP"
EXTRAPATH=

t "TC-057 real quarantine.txt exists, no valid entries" bash -c '[ -f "$0/quarantine.txt" ] && ! grep -vE "^[[:space:]]*(#|\$)" "$0/quarantine.txt" | grep -q .' "$HERE"

echo
[ "$fails" = 0 ] && { echo "all run_all_retry cases ok"; exit 0; }
echo "$fails case(s) FAILED"; exit 1
