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
#
# "Today" is the real UTC date; there is no way to override it. Dates in the
# fixtures are built as today+N with pure bash day arithmetic below. If the UTC
# day changes while this file runs, it runs once more from the start.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_ROOT="$(cd "$HERE/.." && pwd)"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0
SR="$TMP/sr"; CNT="$TMP/cnt"; TMPD="$TMP/tmpd"
UNAME_DIR="$TMP/uname"; mkdir -p "$UNAME_DIR"
printf '#!/bin/sh\necho Linux\n' > "$UNAME_DIR/uname"; chmod +x "$UNAME_DIR/uname"
MSYS_DIR="$TMP/uname_msys"; mkdir -p "$MSYS_DIR"
printf '#!/bin/sh\necho MINGW64_NT-10.0\n' > "$MSYS_DIR/uname"; chmod +x "$MSYS_DIR/uname"

# ---- dates: today (UTC) +/- N, pure bash ----------------------------------
T0=$(date -u +%F)
TN=$(( $(date -u +%s) / 86400 ))
n2d() { # days since 1970-01-01 -> YYYY-MM-DD
  local z=$(( $1 + 719468 )) era doe yoe y doy mp d m
  era=$(( (z >= 0 ? z : z - 146096) / 146097 ))
  doe=$(( z - era * 146097 ))
  yoe=$(( (doe - doe/1460 + doe/36524 - doe/146096) / 365 ))
  y=$(( yoe + era * 400 ))
  doy=$(( doe - (365*yoe + yoe/4 - yoe/100) ))
  mp=$(( (5*doy + 2) / 153 ))
  d=$(( doy - (153*mp + 2)/5 + 1 ))
  m=$(( mp < 10 ? mp + 3 : mp - 9 ))
  [ "$m" -le 2 ] && y=$(( y + 1 ))
  printf '%04d-%02d-%02d' "$y" "$m" "$d"
}
dplus() { n2d $(( TN + $1 )); }
[ "$(n2d "$TN")" = "$T0" ] || { echo "test helper disagrees with date: $(n2d "$TN") vs $T0"; exit 1; }

t() { local l=$1; shift; printf '%-70s ' "$l"; if "$@"; then echo ok; else echo FAIL; fails=$((fails+1)); fi; }
rc_is()   { [ "$RC" = "$1" ]; }
rc_nz()   { [ "$RC" != 0 ]; }
out_has() { grep -qF -- "$1" <<<"$OUT"; }
out_no()  { ! grep -qF -- "$1" <<<"$OUT"; }
out_re()  { grep -qE -- "$1" <<<"$OUT"; }
err_has() { grep -qF -- "$1" <<<"$ERR"; }
err_no_flaky_start() { ! grep -q '^FLAKY ' <<<"$ERR"; }
cnt_is()  { local n=0; [ -f "$CNT/c.$1" ] && n=$(wc -l < "$CNT/c.$1" | tr -d ' '); [ "$n" = "$2" ]; }
no_cnt()  { [ -z "$(ls "$CNT" 2>/dev/null)" ]; }

reset() {
  command rm -rf "$SR" "$CNT" "$TMPD"
  mkdir -p "$SR/tests" "$SR/scripts/utils" "$CNT" "$TMPD"
  cp "$HERE/run_all.sh" "$SR/tests/run_all.sh"
  cp "$REAL_ROOT/scripts/utils/portable.sh" "$SR/scripts/utils/portable.sh"
  printf '# empty list\n' > "$SR/tests/quarantine.txt"
}
mk_ok() { printf '#!/bin/bash\necho x >> "%s/c.%s"\nexit 0\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
mk_flaky() {
  printf '#!/bin/bash\nf="%s/c.%s"; n=0; [ -f "$f" ] && n=$(( $(wc -l < "$f") )); echo x >> "$f"\n[ "$n" -ge 1 ]\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
mk_flaky_marker() {
  printf '#!/bin/bash\nf="%s/c.%s"; n=0; [ -f "$f" ] && n=$(( $(wc -l < "$f") )); echo x >> "$f"\n[ "$n" -ge 1 ] && echo retry-run-marker\n[ "$n" -ge 1 ]\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
mk_bad() {
  printf '#!/bin/bash\nf="%s/c.%s"; n=0; [ -f "$f" ] && n=$(( $(wc -l < "$f") )); echo x >> "$f"\nif [ "$n" -ge 1 ]; then echo second-run-marker; else echo first-run-marker; fi\nexit 1\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
mk_slow() {
  printf '#!/bin/bash\nf="%s/c.%s"; n=0; [ -f "$f" ] && n=$(( $(wc -l < "$f") )); echo x >> "$f"\n[ "$n" -ge 1 ] || sleep 3\nexit 0\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
mk_slow_always() { printf '#!/bin/bash\necho x >> "%s/c.%s"\nsleep 3\nexit 0\n' "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
setq() { printf '%s\n' "$@" > "$SR/tests/quarantine.txt"; }

# run <args...>: the sandbox runner; sets OUT, ERR, RC.
# Knobs: ENVX="A=1 B=2" extra environment; EXTRAPATH shim dir; UNAMEDIR fake
# uname dir; RAW=1 keep the missing-tools note; NOAMT=1 leave out
# --allow-missing-tools.
run() {
  local amt=--allow-missing-tools
  [ -n "${NOAMT:-}" ] && amt=
  OUT=$(env $ENVX TMPDIR="$TMPD" PATH="${EXTRAPATH:+$EXTRAPATH:}${UNAMEDIR:-$UNAME_DIR}:$PATH" \
        bash "$SR/tests/run_all.sh" $amt "$@" 2>"$TMP/err"); RC=$?
  ERR=$(cat "$TMP/err")
  if [ -z "${RAW:-}" ]; then
    OUT=$(sed -E "s/ - run with --allow-missing-tools, .* missing//" <<<"$OUT")
    ERR=$(sed -E "s/ - run with --allow-missing-tools, .* missing//" <<<"$ERR")
  fi
}
ENVX=""; NOAMT=""; RAW=""; EXTRAPATH=""; UNAMEDIR=""
normalize() { sed -E 's/ - run with --allow-missing-tools, .* missing//; s/ +[0-9]+s$//; s/^root:.*/root: X/; /^logs:/d'; }

F=--retry-failed-once
D3=$(dplus 3)

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

# ---- C. retry and FLAKY -------------------------------------------------
reset; mk_ok ok_test.sh; mk_flaky flaky_test.sh; run $F
t "TC-014 unquarantined flaky: exit 1" rc_is 1
t "TC-014 FLAKY line at line start, NOT in list" out_re '^FLAKY flaky_test\.sh +NOT in tests/quarantine\.txt'
t "TC-015 stderr names the file" err_has "flaky_test.sh"
t "TC-015 stderr: Fix the test" err_has "Fix the test"
t "TC-015 stderr: names the list file" err_has "tests/quarantine.txt"
t "TC-015 stderr: format hint" err_has "tests/<name>.sh <issue> <YYYY-MM-DD> (at most 14 days out)"
t "TC-015 stderr: no line starts with FLAKY " err_no_flaky_start
t "TC-077 unquarantined flaky never green" out_no "green after retry"

reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; mk_flaky flaky_test.sh; setq '# c' "tests/flaky_test.sh #12 $D3"; run $F
t "TC-016 quarantined flaky: exit 0" rc_is 0
t "TC-016 FLAKY line with issue and date" out_re "^FLAKY flaky_test\\.sh +quarantined #12 until $D3"
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

reset; mk_bad bad_test.sh; setq "tests/bad_test.sh #12 $D3"; run $F
t "TC-025 quarantined bad still exit 1" rc_is 1
t "TC-025 still FAILED bad_test.sh" out_has "FAILED bad_test.sh"

# TC-026/027/028: a timed-out file is not retried and is a plain failure.
reset; mk_ok ok_test.sh; mk_slow slow_test.sh; run $F --timeout 1
t "TC-026 timeout: exit 1" rc_is 1
t "TC-026 timeout: ran once, not retried" cnt_is slow_test 1
t "TC-026 timeout: no FLAKY line" out_no "FLAKY slow_test.sh"
t "TC-026 first round still shows the timeout" out_re '^slow_test\.sh +TIMEOUT'
reset; mk_ok ok_test.sh; mk_slow slow_test.sh; setq "tests/slow_test.sh #12 $D3"; run $F --timeout 1
t "TC-027 quarantine cannot save a timeout: exit 1" rc_is 1
t "TC-027 ran once" cnt_is slow_test 1
t "TC-027 no FLAKY line" out_no "FLAKY slow_test.sh"
reset; mk_slow_always slow_always_test.sh; run $F --timeout 1
t "TC-028 always-timeout: exit 1" rc_is 1
t "TC-028 ran once (no retry)" cnt_is slow_always_test 1
t "TC-028 no 'retry <name>' line" bash -c '! grep -q "^retry slow_always_test" <<<"$0"' "$OUT"
t "TC-028 no FLAKY" out_no "FLAKY"

reset; mk_flaky a_flaky_test.sh; mk_flaky b_flaky_test.sh; setq "tests/a_flaky_test.sh #12 $D3"; run $F
t "TC-029 one quarantined, one not: exit 1" rc_is 1
t "TC-029 error names the unquarantined one" err_has "b_flaky_test.sh"
t "TC-029 error does not name the quarantined one" bash -c '! grep -qF a_flaky_test.sh <<<"$0"' "$ERR"

reset; mk_flaky flaky_test.sh; mk_bad bad_test.sh; setq "tests/flaky_test.sh #12 $D3"; run $F
t "TC-030 quarantined flaky + real red: exit 1" rc_is 1

reset; mk_ok ok_test.sh; mk_flaky flaky_test.sh; setq "tests/flaky_test.sh #12 $D3"; run $F --only flaky
t "TC-031 --only flaky: ok_test not run" cnt_is ok_test 0
t "TC-031 --only flaky: flaky ran and retried" cnt_is flaky_test 2

reset; mk_ok ok_test.sh; mk_flaky flaky_test.sh; run --list; plain="$OUT"; prc=$RC
run $F --list
t "TC-032 --list identical with the flag" test "$OUT" = "$plain"
t "TC-032 --list exit 0 both ways" test "$RC" = 0 -a "$prc" = 0

# TC-078: the list file is gone -> fail before any test.
reset; mk_ok ok_test.sh; command rm -f "$SR/tests/quarantine.txt"; run $F
t "TC-078 missing list + flag: non-zero" rc_nz
t "TC-078 no test ran" no_cnt
t "TC-078 message names tests/quarantine.txt" bash -c 'grep -qF tests/quarantine.txt <<<"$0$1"' "$OUT" "$ERR"

# TC-079: flaky is retried, timeout is not; the heading counts only retried files.
reset; mk_flaky flaky_test.sh; mk_slow slow_test.sh; setq "tests/flaky_test.sh #12 $D3"; run $F --timeout 1
t "TC-079 flaky ran twice" cnt_is flaky_test 2
t "TC-079 slow ran once" cnt_is slow_test 1
t "TC-079 heading counts one file" out_has "== retry: re-running 1 file(s) once =="
t "TC-079 exit 1 (timeout is still a failure)" rc_is 1

# TC-080/081: --verbose prints the retry output too.
reset; mk_flaky_marker flaky_test.sh; setq "tests/flaky_test.sh #12 $D3"; run --verbose $F
t "TC-080 verbose: retry output on screen" out_has "retry-run-marker"
t "TC-080 verbose: exit 0" rc_is 0
reset; mk_flaky_marker flaky_test.sh; setq "tests/flaky_test.sh #12 $D3"; run $F
t "TC-081 quiet: retry output not on screen" out_no "retry-run-marker"
t "TC-081 quiet: exit 0" rc_is 0

# TC-082/083: the missing-tools note is repeated in the conclusion.
mkdir -p "$TMP/nojq"; printf '#!/bin/sh\nexit 1\n' > "$TMP/nojq/jq"; chmod +x "$TMP/nojq/jq"
note_count() { local c; c=$( { printf '%s\n' "$OUT"; printf '%s\n' "$ERR"; } | grep -cF 'run with --allow-missing-tools'); [ "$c" -ge 2 ]; }
reset; mk_flaky flaky_test.sh; setq "tests/flaky_test.sh #12 $D3"; EXTRAPATH="$TMP/nojq" RAW=1 run $F
t "TC-082 registered flaky: exit 0" rc_is 0
t "TC-082 green after retry present" out_has "green after retry"
t "TC-082 note appears at least twice" note_count
t "TC-082 note is on the green-after-retry line" bash -c 'grep "green after retry" <<<"$0" | grep -qF "run with --allow-missing-tools"' "$OUT"
reset; mk_flaky flaky_test.sh; EXTRAPATH="$TMP/nojq" RAW=1 run $F
t "TC-083 unregistered flaky: exit 1" rc_is 1
t "TC-083 note appears at least twice" note_count
EXTRAPATH=""; RAW=""

# ---- D. list validation -------------------------------------------------
reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; setq '# header' "tests/ok_test.sh #12 $(dplus -1)"; run $F
t "TC-034 expired: exit 1" rc_is 1
t "TC-034 stderr has file:line" err_has "quarantine: tests/quarantine.txt:2:"
t "TC-034 mentions expired" err_has "expired"
t "TC-035 no test ran before validation" no_cnt
t "TC-047 expired but all tests green: still exit 1" rc_is 1

chk_valid() { # chk_valid <label> <line>  -> expects exit 0
  reset; mk_ok ok_test.sh; setq "$2"; run $F; t "$1" rc_is 0; }
chk_bad() {   # chk_bad <label> <line> [needle] -> expects exit 1
  reset; mk_ok ok_test.sh; setq "$2"; run $F; t "$1" rc_is 1
  [ -n "${3:-}" ] && t "$1 (message)" err_has "$3"; return 0; }
chk_valid "TC-036 expiry today is valid" "tests/ok_test.sh #12 $(dplus 0)"
chk_valid "TC-037 today+14 is valid" "tests/ok_test.sh #12 $(dplus 14)"
chk_bad   "TC-038 today+15 is rejected" "tests/ok_test.sh #12 $(dplus 15)" "14 days"
chk_bad   "TC-039 missing issue column" "tests/ok_test.sh $D3" "quarantine: tests/quarantine.txt:1:"
chk_valid "TC-040 issue #12" "tests/ok_test.sh #12 $D3"
chk_valid "TC-040 issue URL" "tests/ok_test.sh https://github.com/zhshie/agentic-bioflow/issues/12 $D3"
for bad in 12 '#' 'https://example.com/x'; do chk_bad "TC-041 issue '$bad'" "tests/ok_test.sh $bad $D3"; done
for bad in 2026-13-40 2026-2-3 not-a-date; do chk_bad "TC-042 date '$bad'" "tests/ok_test.sh #12 $bad"; done
for bad in tests/nope_test.sh ../x.sh tests/a.txt; do chk_bad "TC-043 path '$bad'" "$bad #12 $D3"; done
reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $D3" "tests/ok_test.sh #13 $(dplus 4)"; run $F
t "TC-044 same path twice: exit 1" rc_is 1
chk_bad   "TC-045 fourth column rejected" "tests/ok_test.sh #12 $D3 extra"
reset; mk_ok ok_test.sh; printf '# note\r\n\r\ntests/ok_test.sh #12 %s\r\n' "$D3" > "$SR/tests/quarantine.txt"; run $F
t "TC-046 comments, blank lines and CRLF tolerated" rc_is 0

reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; setq "tests/ok_test.sh #12 $D3"; run --check-quarantine
t "TC-050 --check-quarantine valid: exit 0" rc_is 0
t "TC-050 ran no test" no_cnt
t "TC-050 made no log dir" bash -c '[ -z "$(ls "$0" 2>/dev/null)" ]' "$TMPD"
setq "tests/ok_test.sh #12 $(dplus -1)"; run --check-quarantine
t "TC-051 --check-quarantine invalid: exit 1" rc_is 1
t "TC-051 prints the line message" err_has "quarantine: tests/quarantine.txt:1:"

OUT=$(env PATH="$UNAME_DIR:$PATH" bash "$HERE/run_all.sh" --allow-missing-tools --check-quarantine 2>&1); RC=$?
t "TC-052 real tree: --check-quarantine exit 0" rc_is 0

reset; mk_ok platform_test.sh; setq "tests/platform_test.sh #12 $D3"; run $F
t "TC-053 platform_test.sh may not be quarantined (exit 1)" rc_is 1
t "TC-053 message names line" err_has "quarantine: tests/quarantine.txt:1:"
t "TC-053 message says platform_test.sh" err_has "platform_test.sh"

reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $(dplus -1)" "tests/ok_test.sh x $D3"; run $F
t "TC-054 one message per bad line (line 1)" err_has "quarantine: tests/quarantine.txt:1:"
t "TC-054 one message per bad line (line 2)" err_has "quarantine: tests/quarantine.txt:2:"
t "TC-054 exit 1" rc_is 1

# TC-055: the day is the UTC day, whatever the local zone says.
for tz in UTC-14 UTC+12; do
  for pair in "-1:1" "0:0" "14:0" "15:1"; do
    off=${pair%%:*}; want=${pair##*:}
    reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $(dplus "$off")"; ENVX="TZ=$tz" run $F
    t "TC-055 TZ=$tz expiry today+($off): exit $want" rc_is "$want"
  done
done
ENVX=""

# TC-091 (and TC-056 below, with python3 absent and a failing relative date):
# swept offsets around the 14-day window.
sweep() { # sweep <label-prefix>
  local d want
  for d in -3 -2 -1 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18; do
    reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $(dplus "$d")"; run $F
    if [ "$d" -ge 0 ] && [ "$d" -le 14 ]; then want=0; else want=1; fi
    t "$1 offset $d: exit $want" rc_is "$want"
    if [ "$d" -lt 0 ]; then t "$1 offset $d: expired" err_has "expired"; fi
    if [ "$d" -gt 14 ]; then t "$1 offset $d: 14 days" err_has "14 days"; fi
  done
}
sweep "TC-091"
mkdir -p "$TMP/shim"
printf '#!/bin/sh\ncase "$*" in *"print(1)"*) exit 127;; esac\necho called > "%s/python-called"\nexit 127\n' "$TMP" > "$TMP/shim/python3"
REALDATE=$(command -v date)
printf '#!/bin/sh\nfor a in "$@"; do case "$a" in -d|--date*) echo called > "%s/date-rel-called"; exit 1;; esac; done\nexec "%s" "$@"\n' "$TMP" "$REALDATE" > "$TMP/shim/date"
chmod +x "$TMP/shim/python3" "$TMP/shim/date"
EXTRAPATH="$TMP/shim"
sweep "TC-056 shimmed"
t "TC-056 neither python3 nor a relative date was used" bash -c '[ ! -e "$0/python-called" ] && [ ! -e "$0/date-rel-called" ]' "$TMP"
EXTRAPATH=""

t "TC-057 real quarantine.txt exists, no valid entries" bash -c '[ -f "$0/quarantine.txt" ] && ! grep -vE "^[[:space:]]*(#|\$)" "$0/quarantine.txt" | grep -q .' "$HERE"

# TC-084: trailing # comment, with and without CRLF.
reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh
printf 'tests/ok_test.sh #12 %s # tracked in the issue\r\ntests/ok_two_test.sh #13 %s\n' "$D3" "$D3" > "$SR/tests/quarantine.txt"; run $F
t "TC-084 trailing comment, CRLF, and plain line all valid" rc_is 0
t "TC-084 no quarantine: message" bash -c '! grep -q "quarantine:" <<<"$0$1"' "$OUT" "$ERR"
reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $D3 # note"; run $F
t "TC-084 trailing comment alone is valid" rc_is 0

# TC-085: --check-quarantine with the file gone.
reset; mk_ok ok_test.sh; command rm -f "$SR/tests/quarantine.txt"; run --check-quarantine
t "TC-085 missing list: non-zero" rc_nz
t "TC-085 message has tests/quarantine.txt" bash -c 'grep -qF tests/quarantine.txt <<<"$0$1"' "$OUT" "$ERR"
t "TC-085 message says missing" bash -c 'grep -qi missing <<<"$0$1"' "$OUT" "$ERR"
t "TC-085 no test ran" no_cnt

# TC-086: native Git Bash (MSYS) does not block --check-quarantine.
reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $D3"; UNAMEDIR="$MSYS_DIR" run --check-quarantine
t "TC-086 MSYS + valid list: exit 0" rc_is 0
t "TC-086 no banner" out_no "version:"
t "TC-086 no test ran" no_cnt
setq "tests/ok_test.sh #12 $(dplus -1)"; UNAMEDIR="$MSYS_DIR" run --check-quarantine
t "TC-086 MSYS + bad list: exit 1" rc_is 1
t "TC-086 MSYS + bad list: quarantine: line" err_has "quarantine: tests/quarantine.txt:1:"
UNAMEDIR=""

# TC-087: --only that matches nothing does not matter.
reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $D3"; run --check-quarantine --only zzz-no-match
t "TC-087 --only no match + valid: exit 0" rc_is 0
setq "tests/ok_test.sh #12 $(dplus -1)"; run --check-quarantine --only zzz-no-match
t "TC-087 --only no match + bad: exit 1" rc_is 1
t "TC-087 bad list message" err_has "quarantine: tests/quarantine.txt:1:"

# TC-088: neither jq nor python3 works, no --allow-missing-tools.
mkdir -p "$TMP/notools"
printf '#!/bin/sh\nexit 127\n' > "$TMP/notools/jq"; printf '#!/bin/sh\nexit 127\n' > "$TMP/notools/python3"
chmod +x "$TMP/notools/jq" "$TMP/notools/python3"
reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $D3"; EXTRAPATH="$TMP/notools" NOAMT=1 run --check-quarantine
t "TC-088 no tools + valid: exit 0" rc_is 0
t "TC-088 no test ran" no_cnt
setq "tests/ok_test.sh #12 $(dplus -1)"; EXTRAPATH="$TMP/notools" NOAMT=1 run --check-quarantine
t "TC-088 no tools + bad: exit 1" rc_is 1
t "TC-088 bad list message" err_has "quarantine: tests/quarantine.txt:1:"
EXTRAPATH=""; NOAMT=""

# TC-089: platform_clock_test.sh may not be quarantined either.
reset; mk_ok platform_clock_test.sh; setq "tests/platform_clock_test.sh #12 $D3"; run $F
t "TC-089 platform_clock_test.sh: exit 1" rc_is 1
t "TC-089 message names line" err_has "quarantine: tests/quarantine.txt:1:"
t "TC-089 message says platform_clock_test.sh" err_has "platform_clock_test.sh"

# TC-090: RUN_ALL_TODAY is not a back door any more.
reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $D3"; ENVX="RUN_ALL_TODAY=2000-01-01" run $F
t "TC-090a RUN_ALL_TODAY=2000-01-01, expiry today+3: valid" rc_is 0
setq "tests/ok_test.sh #12 2000-01-05"; ENVX="RUN_ALL_TODAY=2000-01-01" run $F
t "TC-090b same override, expiry 2000-01-05: expired" rc_is 1
t "TC-090b says expired" err_has "expired"
setq "tests/ok_test.sh #12 $D3"; ENVX="RUN_ALL_TODAY=2099-01-01" run $F
t "TC-090c RUN_ALL_TODAY=2099-01-01, expiry today+3: valid" rc_is 0
ENVX=""

echo
# If the UTC day changed while this ran, the date-based cases may have straddled
# midnight: run once more (guarded so it cannot loop).
if [ "$(date -u +%F)" != "$T0" ] && [ -z "${ABF_RR_AGAIN:-}" ]; then
  exec env ABF_RR_AGAIN=1 bash "$0"
fi
[ "$fails" = 0 ] && { echo "all run_all_retry cases ok"; exit 0; }
echo "$fails case(s) FAILED"; exit 1
