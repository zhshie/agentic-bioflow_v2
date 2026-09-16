#!/bin/bash
# Regression tests for tests/run_all.sh's environment check (issue #1).
#
# On native Windows Git Bash the suite produced 17/40 passed, 23 failed - every
# failure a known MSYS gap (PITFALLS 16b: no multiplexed ssh; USER unset;
# hostname.exe has no -s), none a regression. A red suite that reads like a
# broken release is worse than no suite. The runner now says "wrong shell, use
# WSL" once and stops, unless told to run anyway, in which case its verdict
# says the failures are that known gap.
#
# Never runs a real test file: the pass-through cases use --only with a name
# that matches nothing, which exits 2 only after the environment check - so
# this file cannot recurse into the suite it belongs to.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0

mkuname() { # mkuname <uname -s answer>
  local d="$TMP/uname-$1"; mkdir -p "$d"
  printf '#!/bin/sh\necho %s\n' "$1" > "$d/uname"; chmod +x "$d/uname"
  echo "$d"
}
run() { # run <uname -s> <args...>
  local d; d=$(mkuname "$1"); shift
  PATH="$d:$PATH" bash "$HERE/run_all.sh" "$@" 2>&1
}
check() { # check <label> <condition-exit>
  printf '%-62s ' "$1"; [ "$2" = 0 ] && echo ok || { echo FAIL; fails=$((fails+1)); }
}
NOMATCH="--only zz-no-such-test-zz"

for u in MINGW64_NT-10.0-22631 MSYS_NT-10.0 CYGWIN_NT-10.0; do
  out=$(run "$u" $NOMATCH); rc=$?
  check "$u: stops with its own exit code (3)"       "$([ "$rc" = 3 ]; echo $?)"
  check "$u: names WSL"                                "$(grep -q WSL <<<"$out"; echo $?)"
  check "$u: points at PITFALLS 20c"                   "$(grep -q '20c' <<<"$out"; echo $?)"
  check "$u: does not claim a pass/fail count"         "$(! grep -qE '[0-9]+/[0-9]+ passed' <<<"$out"; echo $?)"
done

out=$(run Linux $NOMATCH); rc=$?
check "Linux: passes the check (reaches 'no test files matched')"  "$([ "$rc" = 2 ] && grep -q 'no test files matched' <<<"$out"; echo $?)"
check "Linux: says nothing about WSL"                               "$(! grep -q WSL <<<"$out"; echo $?)"
out=$(run Darwin $NOMATCH); rc=$?
check "macOS: passes the check"                                     "$([ "$rc" = 2 ]; echo $?)"

out=$(run MINGW64_NT-10.0 --allow-msys $NOMATCH); rc=$?
check "--allow-msys on Git Bash: runs anyway"                       "$([ "$rc" = 2 ] && grep -q 'no test files matched' <<<"$out"; echo $?)"

# The verdict under --allow-msys: exercised on one real, fast, pure file.
out=$(run MINGW64_NT-10.0 --allow-msys --only intro_languages_test); rc=$?
check "--allow-msys verdict flags the known MSYS gap"               "$(grep -q 'Git Bash/MSYS' <<<"$out" && grep -q '20c' <<<"$out"; echo $?)"
out=$(run Linux --only intro_languages_test); rc=$?
check "Linux verdict carries no MSYS note"                          "$(! grep -q 'MSYS' <<<"$out"; echo $?)"

out=$(run MINGW64_NT-10.0 --help); rc=$?
check "usage documents --allow-msys"                                "$(grep -q -- '--allow-msys' <<<"$out"; echo $?)"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
