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
# Today is fixed by a date shim in the sandbox (the shim answers the runner's
# date question with the day this file started on); the runner has no override
# point of its own. Dates in the fixtures are built as today+N with pure bash
# day arithmetic below, so a run cannot flip at UTC midnight.
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
# TC-126: n2d is checked against two fixed known values, not against another date call.
[ "$(n2d 0)" = 1970-01-01 ] && [ "$(n2d 19723)" = 2024-01-01 ] || { echo "test helper n2d is wrong: $(n2d 0) $(n2d 19723)"; exit 1; }
# Ask the clock once; everything else derives from this one reading.
NOW=$(date -u +%s)
TN=$(( NOW / 86400 ))
T0=$(n2d "$TN")
dplus() { n2d $(( TN + $1 )); }
qline() { printf 'tests/%s %s %s %s' "$1" "$2" "$3" "${4:-$T0}"; } # qline <file> <issue> <expiry> [since]

# The date shim: the only thing in the sandbox that decides what "today" is.
# -u +%F -> the day in $TMP/today; +%F without -u -> a sentinel day; -d/--date
# -> marker file and failure; anything else -> the real date.
DATE_DIR="$TMP/dateshim"; mkdir -p "$DATE_DIR"
command -v date > "$DATE_DIR/realdate"
echo "$T0" > "$TMP/today"
cat > "$DATE_DIR/date" <<'SHIM'
#!/bin/sh
D=$(dirname "$0")
for a in "$@"; do case "$a" in -d|--date*) echo called > "$D/../date-rel-called"; exit 1;; esac; done
case "$*" in
  "-u +%F") cat "$D/../today"; exit 0 ;;
  *+%F*) echo 1999-12-31; exit 0 ;;
esac
exec "$(cat "$D/realdate")" "$@"
SHIM
chmod +x "$DATE_DIR/date"

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
  OUT=$(env $ENVX TMPDIR="$TMPD" PATH="$DATE_DIR:${EXTRAPATH:+$EXTRAPATH:}${UNAMEDIR:-$UNAME_DIR}:$PATH" \
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

t "TC-007 header has no hard-coded number >= 10" bash -c '! head -20 "$0" | grep -E "(^|[^[:alnum:]])[0-9]{2,}([^[:alnum:]]|\$)" >/dev/null' "$HERE/run_all.sh"
t "TC-007 header still says run time" bash -c 'head -20 "$0" | grep -iE "run ?time" >/dev/null' "$HERE/run_all.sh"

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
t "TC-015 stderr: format hint" err_has "tests/<name>.sh <issue> <expiry YYYY-MM-DD> <since YYYY-MM-DD>"
t "TC-015 stderr: no line starts with FLAKY " err_no_flaky_start
t "TC-077 unquarantined flaky never green" out_no "green after retry"

reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; mk_flaky flaky_test.sh; setq '# c' "$(qline flaky_test.sh '#12' $D3)"; run $F
t "TC-016 quarantined flaky: exit 0" rc_is 0
t "TC-016 FLAKY line with issue and date" out_re "^FLAKY flaky_test\\.sh +quarantined #12 until $D3"
t "TC-017 last line says green after retry: 1" bash -c 'tail -1 <<<"$0" | grep -F "green after retry: 1" >/dev/null' "$OUT"
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

reset; mk_bad bad_test.sh; setq "$(qline bad_test.sh '#12' $D3)"; run $F
t "TC-025 quarantined bad still exit 1" rc_is 1
t "TC-025 still FAILED bad_test.sh" out_has "FAILED bad_test.sh"

# TC-026/027/028: a timed-out file is not retried and is a plain failure.
reset; mk_ok ok_test.sh; mk_slow slow_test.sh; run $F --timeout 1
t "TC-026 timeout: exit 1" rc_is 1
t "TC-026 timeout: ran once, not retried" cnt_is slow_test 1
t "TC-026 timeout: no FLAKY line" out_no "FLAKY slow_test.sh"
t "TC-026 first round still shows the timeout" out_re '^slow_test\.sh +TIMEOUT'
reset; mk_ok ok_test.sh; mk_slow slow_test.sh; setq "$(qline slow_test.sh '#12' $D3)"; run $F --timeout 1
t "TC-027 quarantine cannot save a timeout: exit 1" rc_is 1
t "TC-027 ran once" cnt_is slow_test 1
t "TC-027 no FLAKY line" out_no "FLAKY slow_test.sh"
reset; mk_slow_always slow_always_test.sh; run $F --timeout 1
t "TC-028 always-timeout: exit 1" rc_is 1
t "TC-028 ran once (no retry)" cnt_is slow_always_test 1
t "TC-028 no 'retry <name>' line" bash -c '! grep -q "^retry slow_always_test" <<<"$0"' "$OUT"
t "TC-028 no FLAKY" out_no "FLAKY"

reset; mk_flaky a_flaky_test.sh; mk_flaky b_flaky_test.sh; setq "$(qline a_flaky_test.sh '#12' $D3)"; run $F
t "TC-029 one quarantined, one not: exit 1" rc_is 1
t "TC-029 error names the unquarantined one" err_has "b_flaky_test.sh"
t "TC-029 error does not name the quarantined one" bash -c '! grep -qF a_flaky_test.sh <<<"$0"' "$ERR"

reset; mk_flaky flaky_test.sh; mk_bad bad_test.sh; setq "$(qline flaky_test.sh '#12' $D3)"; run $F
t "TC-030 quarantined flaky + real red: exit 1" rc_is 1

reset; mk_ok ok_test.sh; mk_flaky flaky_test.sh; setq "$(qline flaky_test.sh '#12' $D3)"; run $F --only flaky
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
reset; mk_flaky flaky_test.sh; mk_slow slow_test.sh; setq "$(qline flaky_test.sh '#12' $D3)"; run $F --timeout 1
t "TC-079 flaky ran twice" cnt_is flaky_test 2
t "TC-079 slow ran once" cnt_is slow_test 1
t "TC-079 heading counts one file" out_has "== retry: re-running 1 file(s) once =="
t "TC-079 exit 1 (timeout is still a failure)" rc_is 1

# TC-080/081: --verbose prints the retry output too.
reset; mk_flaky_marker flaky_test.sh; setq "$(qline flaky_test.sh '#12' $D3)"; run --verbose $F
t "TC-080 verbose: retry output on screen" out_has "retry-run-marker"
t "TC-080 verbose: exit 0" rc_is 0
reset; mk_flaky_marker flaky_test.sh; setq "$(qline flaky_test.sh '#12' $D3)"; run $F
t "TC-081 quiet: retry output not on screen" out_no "retry-run-marker"
t "TC-081 quiet: exit 0" rc_is 0

# TC-082/083: the missing-tools note is repeated in the conclusion.
mkdir -p "$TMP/nojq"; printf '#!/bin/sh\nexit 1\n' > "$TMP/nojq/jq"; chmod +x "$TMP/nojq/jq"
note_count() { local c; c=$( { printf '%s\n' "$OUT"; printf '%s\n' "$ERR"; } | grep -cF 'run with --allow-missing-tools'); [ "$c" -ge 2 ]; }
reset; mk_flaky flaky_test.sh; setq "$(qline flaky_test.sh '#12' $D3)"; EXTRAPATH="$TMP/nojq" RAW=1 run $F
t "TC-082 registered flaky: exit 0" rc_is 0
t "TC-082 green after retry present" out_has "green after retry"
t "TC-082 note appears at least twice" note_count
t "TC-082 note is on the green-after-retry line" bash -c 'grep "green after retry" <<<"$0" | grep -F "run with --allow-missing-tools" >/dev/null' "$OUT"
reset; mk_flaky flaky_test.sh; EXTRAPATH="$TMP/nojq" RAW=1 run $F
t "TC-083 unregistered flaky: exit 1" rc_is 1
t "TC-083 note appears at least twice" note_count
EXTRAPATH=""; RAW=""

# ---- D. list validation -------------------------------------------------
reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; setq '# header' "$(qline ok_test.sh '#12' $(dplus -1))"; run $F
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
chk_valid "TC-036 expiry today is valid" "$(qline ok_test.sh '#12' $(dplus 0))"
chk_valid "TC-037 today+14 is valid" "$(qline ok_test.sh '#12' $(dplus 14))"
chk_bad   "TC-038 today+15 is rejected" "$(qline ok_test.sh '#12' $(dplus 15))" "14 days"
chk_bad   "TC-039 missing issue column" "tests/ok_test.sh $D3 $T0" "quarantine: tests/quarantine.txt:1:"
chk_valid "TC-040 issue #12" "$(qline ok_test.sh '#12' $D3)"
chk_valid "TC-040 issue URL" "tests/ok_test.sh https://github.com/zhshie/agentic-bioflow/issues/12 $D3 $T0"
for bad in 12 '#' 'https://example.com/x'; do chk_bad "TC-041 issue '$bad'" "tests/ok_test.sh $bad $D3 $T0"; done
for bad in 2026-13-40 2026-2-3 not-a-date; do chk_bad "TC-042 date '$bad'" "tests/ok_test.sh #12 $bad $T0"; done
for bad in tests/nope_test.sh ../x.sh tests/a.txt; do chk_bad "TC-043 path '$bad'" "$bad #12 $D3 $T0"; done
reset; mk_ok ok_test.sh; setq "$(qline ok_test.sh '#12' $D3)" "$(qline ok_test.sh '#13' $(dplus 4))"; run $F
t "TC-044 same path twice: exit 1" rc_is 1
chk_bad   "TC-045 fifth column rejected" "tests/ok_test.sh #12 $D3 $T0 extra"
reset; mk_ok ok_test.sh; printf '# note\r\n\r\ntests/ok_test.sh #12 %s %s\r\n' "$D3" "$T0" > "$SR/tests/quarantine.txt"; run $F
t "TC-046 comments, blank lines and CRLF tolerated" rc_is 0

reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh; setq "$(qline ok_test.sh '#12' $D3)"; run --check-quarantine
t "TC-050 --check-quarantine valid: exit 0" rc_is 0
t "TC-050 ran no test" no_cnt
t "TC-050 made no log dir" bash -c '[ -z "$(ls "$0" 2>/dev/null)" ]' "$TMPD"
setq "$(qline ok_test.sh '#12' $(dplus -1))"; run --check-quarantine
t "TC-051 --check-quarantine invalid: exit 1" rc_is 1
t "TC-051 prints the line message" err_has "quarantine: tests/quarantine.txt:1:"

OUT=$(env PATH="$UNAME_DIR:$PATH" bash "$HERE/run_all.sh" --allow-missing-tools --check-quarantine 2>&1); RC=$?
t "TC-052 real tree: --check-quarantine exit 0" rc_is 0

reset; mk_ok platform_test.sh; setq "$(qline platform_test.sh '#12' $D3)"; run $F
t "TC-053 platform_test.sh may not be quarantined (exit 1)" rc_is 1
t "TC-053 message names line" err_has "quarantine: tests/quarantine.txt:1:"
t "TC-053 message says platform_test.sh" err_has "platform_test.sh"

reset; mk_ok ok_test.sh; setq "$(qline ok_test.sh '#12' $(dplus -1))" "$(qline ok_test.sh 'x' $D3)"; run $F
t "TC-054 one message per bad line (line 1)" err_has "quarantine: tests/quarantine.txt:1:"
t "TC-054 one message per bad line (line 2)" err_has "quarantine: tests/quarantine.txt:2:"
t "TC-054 exit 1" rc_is 1

# TC-055: the day is the UTC day, whatever the local zone says.
for tz in UTC-14 UTC+12; do
  for pair in "-1:1" "0:0" "14:0" "15:1"; do
    off=${pair%%:*}; want=${pair##*:}
    reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $(dplus "$off") $T0"; ENVX="TZ=$tz" run $F
    t "TC-055 TZ=$tz expiry today+($off): exit $want" rc_is "$want"
  done
done
ENVX=""

# TC-091 (and TC-056 below, with python3 absent and a failing relative date):
# swept offsets around the 14-day window.
sweep() { # sweep <label-prefix>
  local d want
  for d in -3 -2 -1 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18; do
    reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $(dplus "$d") $T0"; run $F
    if [ "$d" -ge 0 ] && [ "$d" -le 14 ]; then want=0; else want=1; fi
    t "$1 offset $d: exit $want" rc_is "$want"
    if [ "$d" -lt 0 ]; then t "$1 offset $d: expired" err_has "expired"; fi
    if [ "$d" -gt 14 ]; then t "$1 offset $d: 14 days" err_has "14 days"; fi
  done
}
sweep "TC-091"
mkdir -p "$TMP/shim"
printf '#!/bin/sh\ncase "$*" in *"print(1)"*) exit 127;; esac\necho called > "%s/python-called"\nexit 127\n' "$TMP" > "$TMP/shim/python3"
chmod +x "$TMP/shim/python3"
EXTRAPATH="$TMP/shim"
sweep "TC-056 shimmed"
t "TC-056 neither python3 nor a relative date was used" bash -c '[ ! -e "$0/python-called" ] && [ ! -e "$0/date-rel-called" ]' "$TMP"
EXTRAPATH=""

t "TC-057 real quarantine.txt exists, no valid entries" bash -c '[ -f "$0/quarantine.txt" ] && ! grep -vE "^[[:space:]]*(#|\$)" "$0/quarantine.txt" | grep . >/dev/null' "$HERE"

# TC-084: trailing # comment, with and without CRLF.
reset; mk_ok ok_test.sh; mk_ok ok_two_test.sh
printf 'tests/ok_test.sh #12 %s %s # tracked in the issue\r\ntests/ok_two_test.sh #13 %s %s\n' "$D3" "$T0" "$D3" "$T0" > "$SR/tests/quarantine.txt"; run $F
t "TC-084 trailing comment, CRLF, and plain line all valid" rc_is 0
t "TC-084 no quarantine: message" bash -c '! grep -q "quarantine:" <<<"$0$1"' "$OUT" "$ERR"
reset; mk_ok ok_test.sh; setq "tests/ok_test.sh #12 $D3 $T0 # note"; run $F
t "TC-084 trailing comment alone is valid" rc_is 0

# TC-085: --check-quarantine with the file gone.
reset; mk_ok ok_test.sh; command rm -f "$SR/tests/quarantine.txt"; run --check-quarantine
t "TC-085 missing list: non-zero" rc_nz
t "TC-085 message has tests/quarantine.txt" bash -c 'grep -qF tests/quarantine.txt <<<"$0$1"' "$OUT" "$ERR"
t "TC-085 message says missing" bash -c 'grep -qi missing <<<"$0$1"' "$OUT" "$ERR"
t "TC-085 no test ran" no_cnt

# TC-086: native Git Bash (MSYS) does not block --check-quarantine.
reset; mk_ok ok_test.sh; setq "$(qline ok_test.sh '#12' $D3)"; UNAMEDIR="$MSYS_DIR" run --check-quarantine
t "TC-086 MSYS + valid list: exit 0" rc_is 0
t "TC-086 no banner" out_no "version:"
t "TC-086 no test ran" no_cnt
setq "$(qline ok_test.sh '#12' $(dplus -1))"; UNAMEDIR="$MSYS_DIR" run --check-quarantine
t "TC-086 MSYS + bad list: exit 1" rc_is 1
t "TC-086 MSYS + bad list: quarantine: line" err_has "quarantine: tests/quarantine.txt:1:"
UNAMEDIR=""

# TC-087: --only that matches nothing does not matter.
reset; mk_ok ok_test.sh; setq "$(qline ok_test.sh '#12' $D3)"; run --check-quarantine --only zzz-no-match
t "TC-087 --only no match + valid: exit 0" rc_is 0
setq "$(qline ok_test.sh '#12' $(dplus -1))"; run --check-quarantine --only zzz-no-match
t "TC-087 --only no match + bad: exit 1" rc_is 1
t "TC-087 bad list message" err_has "quarantine: tests/quarantine.txt:1:"

# TC-088: neither jq nor python3 works, no --allow-missing-tools.
mkdir -p "$TMP/notools"
printf '#!/bin/sh\nexit 127\n' > "$TMP/notools/jq"; printf '#!/bin/sh\nexit 127\n' > "$TMP/notools/python3"
chmod +x "$TMP/notools/jq" "$TMP/notools/python3"
reset; mk_ok ok_test.sh; setq "$(qline ok_test.sh '#12' $D3)"; EXTRAPATH="$TMP/notools" NOAMT=1 run --check-quarantine
t "TC-088 no tools + valid: exit 0" rc_is 0
t "TC-088 no test ran" no_cnt
setq "$(qline ok_test.sh '#12' $(dplus -1))"; EXTRAPATH="$TMP/notools" NOAMT=1 run --check-quarantine
t "TC-088 no tools + bad: exit 1" rc_is 1
t "TC-088 bad list message" err_has "quarantine: tests/quarantine.txt:1:"
EXTRAPATH=""; NOAMT=""

# TC-089: platform_clock_test.sh may not be quarantined either.
reset; mk_ok platform_clock_test.sh; setq "$(qline platform_clock_test.sh '#12' $D3)"; run $F
t "TC-089 platform_clock_test.sh: exit 1" rc_is 1
t "TC-089 message names line" err_has "quarantine: tests/quarantine.txt:1:"
t "TC-089 message says platform_clock_test.sh" err_has "platform_clock_test.sh"

# PS-18 to PS-25 (platform-test-shards): every entry that wraps the platform pytest suite is refused, by its name.
reset; mk_ok platform_shard_2_test.sh; setq "$(qline platform_shard_2_test.sh '#12' $D3)"; run $F
t "PS-18 platform_shard_2_test.sh may not be quarantined (exit 1)" rc_is 1
t "PS-18 message names line" err_has "quarantine: tests/quarantine.txt:1:"
t "PS-18 message says platform_shard_2_test.sh" err_has "platform_shard_2_test.sh"
t "PS-44 message keeps the sentence" err_has "platform_shard_2_test.sh may not be quarantined: it wraps the platform pytest suite, so quarantining it would let any platform test failure through"
reset; mk_ok platform_shard_3_test.sh; setq "$(qline platform_shard_3_test.sh '#12' $D3)"; run $F
t "PS-19 platform_shard_3_test.sh: exit 1" rc_is 1
t "PS-19 message names line" err_has "quarantine: tests/quarantine.txt:1:"
t "PS-19 message says platform_shard_3_test.sh" err_has "platform_shard_3_test.sh"
reset; mk_ok platform_shard_9_test.sh; setq "$(qline platform_shard_9_test.sh '#12' $D3)"; run $F
t "PS-20 a made-up platform_shard_9_test.sh: exit 1 (a pattern, not two names)" rc_is 1
t "PS-20 message names line" err_has "quarantine: tests/quarantine.txt:1:"
t "PS-20 message says platform_shard_9_test.sh" err_has "platform_shard_9_test.sh"
reset; mk_ok platform_storage_doc_test.sh; mk_ok platform_direction_docs_test.sh
setq "$(qline platform_storage_doc_test.sh '#12' $D3)" "$(qline platform_direction_docs_test.sh '#12' $D3)"; run $F
t "PS-21 the two document checks can still be quarantined (exit 0)" rc_is 0
reset; mk_ok platform_test.sh; mk_ok platform_clock_test.sh; setq "$(qline platform_test.sh '#12' $D3)" "$(qline platform_clock_test.sh '#12' $D3)"; run $F
t "PS-22 platform_test.sh and platform_clock_test.sh still refused (exit 1)" rc_is 1
t "PS-22 both lines named" bash -c 'grep -qF "quarantine.txt:1:" <<<"$0" && grep -qF "quarantine.txt:2:" <<<"$0"' "$ERR"
OUT=$(env PATH="$UNAME_DIR:$PATH" bash "$HERE/run_all.sh" --allow-missing-tools --check-quarantine 2>&1); RC=$?
t "PS-23 real tree: --check-quarantine exit 0" rc_is 0
t "PS-24 quarantine.txt line 12 names the four entries" bash -c 'l=$(sed -n 12p "$0/quarantine.txt"); for n in platform_test.sh platform_shard_2_test.sh platform_shard_3_test.sh platform_clock_test.sh; do grep -qF "$n" <<<"$l" || exit 1; done' "$HERE"
reset; mk_ok platform_x_test.sh; echo '# ABF_PLATFORM_PART=2' >> "$SR/tests/platform_x_test.sh"; setq "$(qline platform_x_test.sh '#12' $D3)"; run $F
t "PS-25 the rule is the name, not the content (exit 0)" rc_is 0

# SS-10, SS-32, SS-33, SS-35, SS-71 (suite-speed): the rule is a name pattern, so every platform_shard_<n>_test.sh is refused.
reset; mk_ok platform_shard_8_test.sh; setq "$(qline platform_shard_8_test.sh '#12' $D3)"; run $F
t "SS-10 platform_shard_8_test.sh may not be quarantined (exit 1)" rc_is 1
t "SS-10 message says may not be quarantined" err_has "may not be quarantined"
reset; mk_ok platform_shard_12_test.sh; setq "$(qline platform_shard_12_test.sh '#12' $D3)"; run $F
t "SS-32 a made-up platform_shard_12_test.sh: exit 1 (a pattern, not eight names)" rc_is 1
t "SS-32 message says may not be quarantined" err_has "may not be quarantined"
reset; mk_ok platform_storage_doc_test.sh
setq "$(qline platform_storage_doc_test.sh '#12' $D3)"; run $F
t "SS-33 platform_storage_doc_test.sh can still be quarantined (exit 0)" rc_is 0
reset; mk_ok platform_direction_docs_test.sh
setq "$(qline platform_direction_docs_test.sh '#12' $D3)"; run $F
t "SS-33 platform_direction_docs_test.sh can still be quarantined (exit 0)" rc_is 0
t "SS-35 quarantine.txt line 12 covers every platform_shard_<n>_test.sh and no longer says four" bash -c 'l=$(sed -n 12p "$0/quarantine.txt"); grep -qF "platform_shard_<n>_test.sh" <<<"$l" && ! grep -qiE "four|四個" <<<"$l"' "$HERE"
for n in platform_test.sh platform_shard_2_test.sh platform_shard_3_test.sh platform_shard_4_test.sh platform_shard_5_test.sh platform_shard_6_test.sh platform_shard_7_test.sh platform_shard_8_test.sh platform_clock_test.sh; do
    reset; mk_ok "$n"; setq "$(qline "$n" '#12' $D3)"; run $F
    t "SS-71 $n may not be quarantined (exit 1)" rc_is 1
    t "SS-71 $n message says may not be quarantined" err_has "may not be quarantined"
done

# TC-090: RUN_ALL_TODAY is not a back door any more.
reset; mk_ok ok_test.sh; setq "$(qline ok_test.sh '#12' $D3)"; ENVX="RUN_ALL_TODAY=2000-01-01" run $F
t "TC-090a RUN_ALL_TODAY=2000-01-01, expiry today+3: valid" rc_is 0
setq "$(qline ok_test.sh '#12' 2000-01-05 2000-01-01)"; ENVX="RUN_ALL_TODAY=2000-01-01" run $F
t "TC-090b same override, expiry 2000-01-05: expired" rc_is 1
t "TC-090b says expired" err_has "expired"
setq "$(qline ok_test.sh '#12' $D3)"; ENVX="RUN_ALL_TODAY=2099-01-01" run $F
t "TC-090c RUN_ALL_TODAY=2099-01-01, expiry today+3: valid" rc_is 0
ENVX=""

# ---- E. quarantine-followups: the since column (TC-101 ... TC-115) -------------
# chk <label> <want-rc> <needle-or-empty> <line...>: one list, --check-quarantine.
chk() {
  local label=$1 want=$2 needle=$3; shift 3
  reset; mk_ok ok_test.sh; setq "$@"; run --check-quarantine
  t "$label: exit $want" rc_is "$want"
  [ -n "$needle" ] && t "$label: says '$needle'" err_has "$needle"
  return 0
}
chk "TC-101 old three-column line (found 3)" 1 "found 3" "tests/ok_test.sh #12 $D3"
t "TC-101 names the file:line" err_has "quarantine: tests/quarantine.txt:1:"
t "TC-101 tells what to add" err_has "add the date this file was first quarantined"
chk "TC-102a since 2026-13-40" 1 "quarantine: tests/quarantine.txt:1:" "tests/ok_test.sh #12 $D3 2026-13-40"
chk "TC-102b since not-a-date" 1 "quarantine: tests/quarantine.txt:1:" "tests/ok_test.sh #12 $D3 not-a-date"
chk "TC-103 since in the future" 1 "in the future" "$(qline ok_test.sh '#12' $D3 "$(dplus 1)")"
chk "TC-104 since today, expiry today+14" 0 "" "$(qline ok_test.sh '#12' "$(dplus 14)" "$(dplus 0)")"
chk "TC-105 since-14, expiry today+14 (= since+28)" 0 "" "$(qline ok_test.sh '#12' "$(dplus 14)" "$(dplus -14)")"
chk "TC-106 since-15, expiry today+13 (= since+28)" 0 "" "$(qline ok_test.sh '#12' "$(dplus 13)" "$(dplus -15)")"
chk "TC-107 since-15, expiry today+14 (= since+29)" 1 "28 days" "$(qline ok_test.sh '#12' "$(dplus 14)" "$(dplus -15)")"
t "TC-107 prints the since date" err_has "$(dplus -15)"
t "TC-107b prints how many days ago (15)" err_has "15 days"
chk "TC-108a since-28, expiry today (last day)" 0 "" "$(qline ok_test.sh '#12' "$(dplus 0)" "$(dplus -28)")"
chk "TC-108b since-29, expiry today" 1 "28 days" "$(qline ok_test.sh '#12' "$(dplus 0)" "$(dplus -29)")"
chk "TC-109 expired and since very old" 1 "expired" "$(qline ok_test.sh '#12' "$(dplus -1)" "$(dplus -40)")"
t "TC-109 does not say 28 days" bash -c '! grep -qF "28 days" <<<"$0"' "$ERR"
chk "TC-110 expiry today+15, since today" 1 "14 days" "$(qline ok_test.sh '#12' "$(dplus 15)" "$(dplus 0)")"
chk "TC-110b since-10, expiry today+15 (allowed by since+28 but not by 14)" 1 "14 days" "$(qline ok_test.sh '#12' "$(dplus 15)" "$(dplus -10)")"
# TC-111: the FLAKY line prints the expiry, not the since date.
reset; mk_flaky flaky_test.sh; setq "$(qline flaky_test.sh '#12' "$(dplus 9)" "$(dplus -5)")"; run $F
t "TC-111 FLAKY line prints the expiry" out_re "^FLAKY flaky_test\\.sh +quarantined #12 until $(dplus 9)\$"
t "TC-111 exit 0" rc_is 0
# TC-112: --check-quarantine with the four-column list runs nothing.
reset; mk_ok ok_test.sh; setq "$(qline ok_test.sh '#12' $D3)"; run --check-quarantine
t "TC-112a four columns valid: exit 0" rc_is 0
t "TC-112a ran no test" no_cnt
setq "$(qline ok_test.sh '#12' "$(dplus -1)")"; run --check-quarantine
t "TC-112b four columns invalid: exit 1" rc_is 1
t "TC-112b ran no test" no_cnt
# TC-113: the real list's header.
QH=$(grep '^#' "$HERE/quarantine.txt")
t "TC-113 real header has the four-column line" grep -qF 'tests/<name>.sh <issue> <expiry YYYY-MM-DD> <since YYYY-MM-DD>' <<<"$QH"
t "TC-113 real header mentions since" grep -qi 'since' <<<"$QH"
t "TC-113 real list still has no valid entry" bash -c '! grep -vE "^[[:space:]]*(#|\$)" "$0/quarantine.txt" | grep . >/dev/null' "$HERE"
t "TC-113b since defined: first quarantined, do not change on renewal" bash -c 'grep -qi "first quarantined" <<<"$0" && grep -qi "do not change" <<<"$0"' "$QH"
t "TC-113c rule: 14 days per term, 28 days total, renew once" bash -c 'grep -qF "14 days" <<<"$0" && grep -qF "28 days" <<<"$0" && grep -qi "once" <<<"$0"' "$QH"
t "TC-113d old per-day sentence is gone" bash -c '! grep -qF "expiry at most 14 days from the day it is checked" <<<"$0"' "$QH"
t "TC-113e honest limit: typed by hand, cannot be proven" bash -c 'grep -qi "typed by hand" <<<"$0" && grep -qi "cannot prove\|nothing can prove" <<<"$0"' "$QH"
reset; mk_ok ok_test.sh; run --help
t "TC-114a --help says first-quarantined" err_has "first-quarantined"
t "TC-114b --help says --retry-failed-once" err_has "--retry-failed-once"
# TC-115: no look at git history.
mkdir -p "$TMP/fakegit"
printf '#!/bin/sh\necho called > "%s/git-called"\nexit 1\n' "$TMP" > "$TMP/fakegit/git"; chmod +x "$TMP/fakegit/git"
command rm -f "$TMP/git-called"
reset; mk_ok ok_test.sh; setq "$(qline ok_test.sh '#12' $D3)"; EXTRAPATH="$TMP/fakegit" run --check-quarantine
t "TC-115 valid list: exit 0" rc_is 0
t "TC-115 git was never called" bash -c '[ ! -e "$0/git-called" ]' "$TMP"
EXTRAPATH=""

# ---- F. fixed today (TC-120 ... TC-129) ---------------------------------------
t "TC-120 run_all.sh asks the date once ('date -u' appears once)" bash -c '[ "$(grep -c "date -u" "$0")" = 1 ]' "$HERE/run_all.sh"
t "TC-120 no RUN_ALL_TODAY, no TODAY= override" bash -c '! grep -qE "RUN_ALL_TODAY|(^|[^A-Za-z_])TODAY=" "$0"' "$HERE/run_all.sh"
shim_day() { echo "$1" > "$TMP/today"; }
shim_day 2030-02-28
chk "TC-121a shim 2030-02-28, expiry +14" 0 "" "tests/ok_test.sh #12 2030-03-14 2030-02-28"
chk "TC-121b shim 2030-02-28, expiry +15" 1 "14 days" "tests/ok_test.sh #12 2030-03-15 2030-02-28"
shim_day 2028-02-27
chk "TC-122a leap year, expiry +14 (through 02-29)" 0 "" "tests/ok_test.sh #12 2028-03-12 2028-02-27"
chk "TC-122b leap year, expiry +15" 1 "14 days" "tests/ok_test.sh #12 2028-03-13 2028-02-27"
shim_day 2026-12-31
chk "TC-123a shim 2026-12-31, expiry 2027-01-14" 0 "" "tests/ok_test.sh #12 2027-01-14 2026-12-31"
chk "TC-123b shim 2026-12-31, expiry 2027-01-15" 1 "14 days" "tests/ok_test.sh #12 2027-01-15 2026-12-31"
shim_day "$T0"
# TC-124: a runner copy that forgets -u must turn red for certain.
reset; mk_ok ok_test.sh; setq "$(qline ok_test.sh '#12' $D3)"
sed -i 's/date -u +%F/date +%F/' "$SR/tests/run_all.sh"
run --check-quarantine
t "TC-124 runner without -u: exit 1" rc_is 1
reset
# TC-125 .. TC-129: the shim itself.
command rm -f "$TMP/date-rel-called"
"$DATE_DIR/date" -d tomorrow >/dev/null 2>&1; rc125=$?
t "TC-125 shim: date -d fails" test "$rc125" = 1
t "TC-125 shim: leaves the marker" test -e "$TMP/date-rel-called"
command rm -f "$TMP/date-rel-called"
t "TC-127 shim: date -u +%F prints the fixed day" test "$("$DATE_DIR/date" -u +%F)" = "$T0"
t "TC-128 shim: date +%F without -u prints the sentinel" test "$("$DATE_DIR/date" +%F)" = 1999-12-31
t "TC-129 shim: other arguments reach the real date" bash -c '[[ "$("$0/date" -u +%s)" =~ ^[0-9]+$ ]]' "$DATE_DIR"

# ---- G. clean temp dir for the retry (TC-130 ... TC-138) ----------------------
# A test that leaves a file in $TMPDIR on the first run and fails if it sees it on the second.
mk_leftover() {
  printf '#!/bin/bash\nf="%s/c.%s"; n=0; [ -f "$f" ] && n=$(( $(wc -l < "$f") )); echo x >> "$f"\necho "$TMPDIR" >> "%s/tmpdir.%s"\nif [ "$n" -ge 1 ]; then echo second-run; [ ! -e "$TMPDIR/leftover" ]; exit $?; fi\necho first-run\ntouch "$TMPDIR/leftover"\nexit 1\n' "$CNT" "${1%.sh}" "$CNT" "${1%.sh}" > "$SR/tests/$1"; }
reset; mk_leftover left_test.sh; setq "$(qline left_test.sh '#12' $D3)"; run $F
t "TC-130 retry does not see the first run's leftover: exit 0" rc_is 0
t "TC-130 green after retry: 1" out_has "green after retry: 1"
t "TC-131a first run saw the sandbox TMPDIR" bash -c '[ "$(sed -n 1p "$0/tmpdir.left_test")" = "$1" ]' "$CNT" "$TMPD"
t "TC-131b retry saw a different TMPDIR ending in tmp.<name>.retry" bash -c 'l=$(sed -n 2p "$0/tmpdir.left_test"); [ -n "$l" ] && [ "$l" != "$1" ] && [[ "$l" == */tmp.left_test.sh.retry ]]' "$CNT" "$TMPD"
t "TC-132 the first run's leftover is still there" test -e "$TMPD/leftover"
LOGS=$(sed -n 's/^logs: *//p' <<<"$OUT" | head -1)
t "TC-133 both logs exist" bash -c '[ -f "$0/left_test.sh.log" ] && [ -f "$0/left_test.sh.retry.log" ]' "$LOGS"
t "TC-133 the two logs differ" bash -c '! cmp -s "$0/left_test.sh.log" "$0/left_test.sh.retry.log"' "$LOGS"
t "TC-138 retry line text unchanged, no path in it" bash -c 'l=$(grep "^retry left_test.sh" <<<"$0"); [ "$l" = "retry left_test.sh ... ok" ]' "$OUT"
reset; mk_leftover left_test.sh; run
t "TC-134 no flag: test fails once" rc_is 1
t "TC-134 no flag: ran once" cnt_is left_test 1
t "TC-134 no flag: the test saw the sandbox TMPDIR" bash -c '[ "$(sed -n 1p "$0/tmpdir.left_test")" = "$1" ]' "$CNT" "$TMPD"
reset; mk_leftover left_test.sh; setq "$(qline left_test.sh '#12' $D3)"; run --verbose $F
t "TC-135 verbose retry is clean too: exit 0" rc_is 0
t "TC-135 green after retry: 1" out_has "green after retry: 1"
# TC-137: the retry dir cannot be made -> that retry is a failure, no fallback to the shared TMPDIR.
mkdir -p "$TMP/badmkdir"
printf '#!/bin/sh\ncase "$*" in *tmp.*.retry*) exit 1;; esac\nexec "%s" "$@"\n' "$(command -v mkdir)" > "$TMP/badmkdir/mkdir"; chmod +x "$TMP/badmkdir/mkdir"
reset; mk_leftover left_test.sh; setq "$(qline left_test.sh '#12' $D3)"; EXTRAPATH="$TMP/badmkdir" run $F
t "TC-137 mkdir fails: exit non-zero" rc_nz
t "TC-137 not green after retry" out_no "green after retry"
t "TC-137 test file was not re-run on the shared TMPDIR" cnt_is left_test 1
EXTRAPATH=""


echo
[ "$fails" = 0 ] && { echo "all run_all_retry cases ok"; exit 0; }
echo "$fails case(s) FAILED"; exit 1
