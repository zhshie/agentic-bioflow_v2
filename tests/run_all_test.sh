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
# Real test files run only where named (intro_languages_test, a pure fast one;
# gates_without_jq_test, which needs no jq). The pass-through cases use --only with a name
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
  PATH="$d:${RUNPATH:-$PATH}" bash "${SUT:-$HERE/run_all.sh}" "$@" 2>&1
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
out=$(run MINGW64_NT-10.0 --allow-msys --allow-missing-tools --only intro_languages_test); rc=$?
check "--allow-msys verdict flags the known MSYS gap"               "$(grep -q 'Git Bash/MSYS' <<<"$out" && grep -q '20c' <<<"$out"; echo $?)"
out=$(run Linux --allow-missing-tools --only intro_languages_test); rc=$?
check "Linux verdict carries no MSYS note"                          "$(! grep -q 'MSYS' <<<"$out"; echo $?)"

out=$(run MINGW64_NT-10.0 --help); rc=$?
check "usage documents --allow-msys"                                "$(grep -q -- '--allow-msys' <<<"$out"; echo $?)"

# ---- Missing jq / python3 (issue #70) -------------------------------------
# On a machine without jq, 22 files went red and read like a broken Safety Net;
# the gates were fine, the tests could not build their inputs. The runner now
# checks the two tools before running anything, like it does for MSYS.
. "$HERE/lib/nojq_path.sh"
NOJQ_PATH=$(nojq_path "$TMP") || { echo "cannot build a PATH without jq"; exit 1; }
stub() { # stub <dir> <name> <script body>  -> a command that "exists" but behaves as told
  mkdir -p "$1"; printf '#!/bin/sh\n%s\n' "$3" > "$1/$2"; chmod +x "$1/$2"
}
stub "$TMP/goodjq"  jq      "printf '[1]\\n'"                  # answers the probe
stub "$TMP/crjq"    jq      "printf '[1]\\r\\n'"               # Windows jq.exe style
stub "$TMP/silentjq" jq     "exit 0"                           # exists, prints nothing
stub "$TMP/silentpy" python3 "exit 0"                          # the Windows Store stub
GOOD="$TMP/goodjq:$PATH"
runp() { # runp <PATH> <uname> <args...>
  local p="$1"; shift; RUNPATH="$p" run "$@"
}

# A throwaway root with two harmless test files, so a regression in the check
# (a missing tool no longer stopping the run) cannot start the real suite - which
# contains this very file - from inside this test.
SR="$TMP/sandbox"; mkdir -p "$SR/tests" "$SR/scripts/utils"
cp "$HERE/run_all.sh" "$SR/tests/"; cp "$HERE/../scripts/utils/portable.sh" "$SR/scripts/utils/"
printf "#!/bin/bash
exit 0
" > "$SR/tests/ok_test.sh"
cp "$SR/tests/ok_test.sh" "$SR/tests/gates_without_jq_test.sh"
SANDBOX="$SR/tests/run_all.sh"

# TC-015/016/017/038: no jq -> exit 3, one message, nothing run, nothing installed
stub "$TMP/spy" apt-get 'echo called >> '"$TMP/spy.log"; stub "$TMP/spy" brew 'echo called >> '"$TMP/spy.log"
mkdir -p "$TMP/tmpd"
out=$(SUT="$SANDBOX" TMPDIR="$TMP/tmpd" runp "$TMP/spy:$NOJQ_PATH" Linux); rc=$?
check "TC-015 no jq: exit 3"                                  "$([ "$rc" = 3 ]; echo $?)"
check "TC-016 names jq"                                       "$(grep -q 'jq' <<<"$out"; echo $?)"
check "TC-016 says the gates still refuse"                    "$(grep -qi 'still refuse' <<<"$out"; echo $?)"
check "TC-016 points at gates_without_jq_test.sh"             "$(grep -q 'tests/gates_without_jq_test.sh' <<<"$out"; echo $?)"
check "TC-016 gives the apt and brew lines"                   "$(grep -q 'sudo apt install jq' <<<"$out" && grep -q 'brew install jq' <<<"$out"; echo $?)"
check "TC-016 is not the MSYS message (no WSL)"               "$(! grep -q WSL <<<"$out"; echo $?)"
check "TC-017 no pass count"                                  "$(! grep -qE '[0-9]+/[0-9]+ passed' <<<"$out"; echo $?)"
check "TC-017 no log directory created"                       "$([ -z "$(ls "$TMP/tmpd")" ]; echo $?)"
check "TC-038 nothing was installed for the user"             "$([ ! -e "$TMP/spy.log" ]; echo $?)"

# TC-018: python3 that runs but prints nothing, jq fine
out=$(SUT="$SANDBOX" RUNPATH="$TMP/silentpy:$GOOD" run Linux); rc=$?
check "TC-018 silent python3: exit 3"                         "$([ "$rc" = 3 ]; echo $?)"
check "TC-018 names python3, not jq"                          "$(grep -q python3 <<<"$out" && ! grep -q jq <<<"$out"; echo $?)"

# TC-019: both
out=$(SUT="$SANDBOX" RUNPATH="$TMP/silentpy:$NOJQ_PATH" run Linux); rc=$?
check "TC-019 both missing: exit 3, names both"               "$([ "$rc" = 3 ] && grep -q python3 <<<"$out" && grep -q jq <<<"$out"; echo $?)"

# TC-020: a file called jq that prints nothing is not a jq
out=$(SUT="$SANDBOX" RUNPATH="$TMP/silentjq:$PATH" run Linux); rc=$?
check "TC-020 jq that prints nothing: exit 3, names jq"       "$([ "$rc" = 3 ] && grep -q jq <<<"$out"; echo $?)"

# TC-021: trailing CR is allowed, as in the hooks
out=$(RUNPATH="$TMP/crjq:$PATH" run Linux --only intro_languages_test); rc=$?
check "TC-021 jq answering with a trailing CR is accepted"    "$(! grep -qi 'missing' <<<"$out" && grep -qE '[0-9]+/[0-9]+ passed' <<<"$out"; echo $?)"

# TC-022/023: --allow-missing-tools runs anyway and the verdict names the tool
out=$(RUNPATH="$NOJQ_PATH" run Linux --allow-missing-tools --only intro_languages_test); rc=$?
check "TC-022 --allow-missing-tools runs the file"            "$(grep -q 'intro_languages_test.sh' <<<"$out" && grep -qE '[0-9]+/[0-9]+ passed' <<<"$out"; echo $?)"
check "TC-023 verdict names jq"                               "$(tail -4 <<<"$out" | grep -q jq; echo $?)"

# TC-024: --list needs no tools
out=$(RUNPATH="$NOJQ_PATH" run Linux --list); rc=$?
check "TC-024 --list works without jq"                        "$([ "$rc" = 0 ] && grep -q 'run_all_test.sh' <<<"$out"; echo $?)"

# TC-025: the one file that proves the gates needs no jq, so it runs without
out=$(RUNPATH="$NOJQ_PATH" run Linux --only gates_without_jq); rc=$?
check "TC-025 --only gates_without_jq runs without jq"        "$([ "$rc" = 0 ] && grep -q 'gates_without_jq_test.sh' <<<"$out" && grep -q 'all green' <<<"$out"; echo $?)"

# TC-026: the exemption is for that one file only (a selection that also
# contains any other file keeps the check; "_test" selects every file, and the
# stop comes before any of them runs)
out=$(SUT="$SANDBOX" RUNPATH="$NOJQ_PATH" run Linux --only _test); rc=$?
check "TC-026 a wider selection still stops (exit 3)"         "$([ "$rc" = 3 ] && ! grep -qE '[0-9]+/[0-9]+ passed' <<<"$out"; echo $?)"

# TC-027
out=$(run Linux --help)
check "TC-027 usage documents --allow-missing-tools"          "$(grep -q -- '--allow-missing-tools' <<<"$out"; echo $?)"

# TC-028: tools fine -> no change
out=$(RUNPATH="$GOOD" run Linux --only intro_languages_test); rc=$?
check "TC-028 tools present: no missing-tool text, exit 0"    "$([ "$rc" = 0 ] && ! grep -qi 'missing' <<<"$out"; echo $?)"

# TC-029: a bad --only is reported first, with or without jq
out=$(RUNPATH="$NOJQ_PATH" run Linux $NOMATCH); rc=$?
check "TC-029 no match beats the tool check (exit 2)"         "$([ "$rc" = 2 ] && grep -q 'no test files matched' <<<"$out"; echo $?)"

# TC-030: MSYS stop is untouched and still comes first
out=$(RUNPATH="$GOOD" run MINGW64_NT-10.0); rc=$?
check "TC-030 MSYS: still exit 3 naming WSL and 20c"          "$([ "$rc" = 3 ] && grep -q WSL <<<"$out" && grep -q 20c <<<"$out"; echo $?)"

# --allow-msys also skips the python3 check (the Store stub is the known MSYS
# gap, PITFALLS 20c) but not jq
out=$(RUNPATH="$TMP/silentpy:$GOOD" run MINGW64_NT-10.0 --allow-msys $NOMATCH); rc=$?
check "--allow-msys: a silent python3 does not stop the run"  "$([ "$rc" = 2 ] && grep -q 'no test files matched' <<<"$out"; echo $?)"
out=$(RUNPATH="$NOJQ_PATH" run MINGW64_NT-10.0 --allow-msys --only intro_languages_test); rc=$?
check "--allow-msys: a missing jq still stops (exit 3)"       "$([ "$rc" = 3 ] && grep -q jq <<<"$out"; echo $?)"

# TC-033: a real failure is still a failure (exit 1, no "all green")
FR="$TMP/failroot"; mkdir -p "$FR/tests" "$FR/scripts/utils"
cp "$HERE/run_all.sh" "$FR/tests/"; cp "$HERE/../scripts/utils/portable.sh" "$FR/scripts/utils/"
printf '#!/bin/bash\nexit 1\n' > "$FR/tests/zz_fails_test.sh"
out=$(PATH="$GOOD" bash "$FR/tests/run_all.sh" 2>&1); rc=$?
check "TC-033 a failing test: exit 1, 'failed', no all green" "$([ "$rc" = 1 ] && grep -q 'failed' <<<"$out" && ! grep -q 'all green' <<<"$out"; echo $?)"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
