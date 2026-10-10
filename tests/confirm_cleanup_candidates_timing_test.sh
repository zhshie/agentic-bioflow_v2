#!/bin/bash
# cd-target-backslash (#76, #75): the cleanup guard keeps a set of candidate folders
# (CANDS) and judges every relative word against each. That must never make a long
# command slower than main on main's own work: the guard has its own 20 s deadline (#62),
# and past it the verdict is `ask`, which is weaker than the `deny` main reaches.
#
# So the segment loop judges every word against the trunk only, as main does, and the
# extra checks the candidates imply are recorded and run after the loop, while time
# remains (defer_run). Past the deadline they stop and the verdict stands as it is.
#
# Here: two long commands (40 Set-Location or `cd dN\x`, 50 `rm -f` of five names, then the
# one real delete of results/) must get the verdict main gives (read from main's own hook
# in git, as tests/in_use_speed_test.sh does), the times are printed for both, and a
# deferred phase that is out of time (ABF_CLEANUP_DEFER_DEADLINE_S=0) leaves main's verdict
# - not an ask - while the same command with time left finds the candidate-only delete.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
H="$ROOT/hooks/confirm_cleanup.sh"
command -v jq >/dev/null 2>&1 || { echo "jq is required for this test"; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "python is required for this test"; exit 1; }
export MSYS2_ARG_CONV_EXCL='*'
D=$(printf '\x72\x6d')
U=/work/u/lab_runs/x
BASE=c4a7327
TMP=$(mktemp -d); trap 'command rm -rf "$TMP"' EXIT
MAINH=""
if git -C "$ROOT" cat-file -e "$BASE:hooks/confirm_cleanup.sh" 2>/dev/null; then
  mkdir -p "$TMP/main"
  git -C "$ROOT" archive "$BASE" hooks 2>/dev/null | tar -x -C "$TMP/main" 2>/dev/null && MAINH="$TMP/main/hooks/confirm_cleanup.sh"
fi
fails=0
ms_now() { "$PY" -c 'import time;print(int(time.time()*1000))'; }
verdict() { # verdict <hook> <command> [ENV=val] -> VERDICT, MS
  local out t0 t1
  t0=$(ms_now)
  out=$("$PY" -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[2]}}))" "$H" "$2" | env ${3:+"$3"} bash "$1")
  t1=$(ms_now); MS=$((t1 - t0))
  if [ -z "$out" ]; then VERDICT=pass; else VERDICT=$(jq -r '.hookSpecificOutput.permissionDecision // "warn"' <<<"$out"); fi
}
same_as_main() { # same_as_main <label> <command>
  local bv bm="-" mv="-"
  verdict "$H" "$2"; bv=$VERDICT; local bms=$MS
  if [ -n "$MAINH" ]; then verdict "$MAINH" "$2"; mv=$VERDICT; bm=$MS; fi
  printf '%-52s main %-5s %6s ms   branch %-5s %6s ms  ' "$1" "$mv" "$bm" "$bv" "$bms"
  if [ -z "$MAINH" ]; then echo "(no $BASE here: main not compared)"; return; fi
  if [ "$bv" = "$mv" ]; then echo "ok"; else echo "FAIL: branch $bv, main $mv"; fails=$((fails + 1)); fi
}
c1="cd $U;"; for i in $(seq 1 40); do c1="$c1 Set-Location d$i;"; done
c2="cd $U;"; for i in $(seq 1 40); do c2="$c2 cd d$i\\x;"; done
tail50=""; for i in $(seq 1 50); do tail50="$tail50 $D -f f$i.txt a$i b$i c$i d$i;"; done
c3="cd $U;"; for i in $(seq 1 25); do c3="$c3 sl d$i;"; done
same_as_main "T1 40 Set-Location, 50 rm -f, rm -rf results"  "$c1$tail50 $D -rf $U/results"
same_as_main "T2 40 cd dN\\x, 50 rm -f, rm -rf results"       "$c2$tail50 $D -rf $U/results"
same_as_main "TC-064 25 chained Set-Location, rm -rf x"       "$c3 $D -rf x"

# the deferred phase out of time: main's verdict stands, no ask
cmd="cd $U; sl results; $D -rf x"
verdict "$H" "$cmd"; printf '%-52s %-5s  ' "candidate-only delete, time left" "$VERDICT"
if [ "$VERDICT" = deny ]; then echo ok; else echo "FAIL: want deny"; fails=$((fails + 1)); fi
verdict "$H" "$cmd" ABF_CLEANUP_DEFER_DEADLINE_S=0; printf '%-52s %-5s  ' "...deferred phase out of time (main's verdict)" "$VERDICT"
if [ "$VERDICT" = pass ]; then echo ok; else echo "FAIL: want pass (main's verdict), got $VERDICT"; fails=$((fails + 1)); fi
verdict "$H" "$c2$tail50 $D -rf $U/results" ABF_CLEANUP_DEFER_DEADLINE_S=0; printf '%-52s %-5s  ' "T2 with the deferred phase out of time" "$VERDICT"
if [ "$VERDICT" = deny ]; then echo ok; else echo "FAIL: want deny, got $VERDICT"; fails=$((fails + 1)); fi
verdict "$H" "$cmd" ABF_CLEANUP_DEADLINE_S=0; printf '%-52s %-5s  ' "the loop itself out of time (unchanged: ask)" "$VERDICT"
if [ "$VERDICT" = ask ]; then echo ok; else echo "FAIL: want ask, got $VERDICT"; fails=$((fails + 1)); fi
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
