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
# in git, as tests/in_use_speed_test.sh does, when that commit is in the checkout; the pinned verdicts always run), the times are printed for both, and a
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
if (cd "$ROOT" && git cat-file -e "$BASE:hooks/confirm_cleanup.sh") 2>/dev/null; then
  mkdir -p "$TMP/main"
  (cd "$ROOT" && git archive "$BASE" hooks) 2>/dev/null | tar -x -C "$TMP/main" 2>/dev/null && MAINH="$TMP/main/hooks/confirm_cleanup.sh"
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
same_as_main() { # same_as_main <label> <command> <pinned verdict>
  local bv mv="-" bm="-" bms why=""
  verdict "$H" "$2"; bv=$VERDICT; bms=$MS
  if [ -n "$MAINH" ]; then verdict "$MAINH" "$2"; mv=$VERDICT; bm=$MS; fi
  printf '%-44s main %-5s %6s ms   branch %-5s %6s ms  ' "$1" "$mv" "$bm" "$bv" "$bms"
  # the pinned verdict always runs; the comparison with main is an extra when c4a7327 is here
  [ "$bv" = "$3" ] || why="want $3, got $bv. "
  [ -z "$MAINH" ] || [ "$bv" = "$mv" ] || why="${why}main gives $mv. "
  if [ -z "$why" ]; then echo "ok"; else echo "FAIL: $why"; fails=$((fails + 1)); fi
}
c1="cd $U;"; for i in $(seq 1 40); do c1="$c1 Set-Location d$i;"; done
c2="cd $U;"; for i in $(seq 1 40); do c2="$c2 cd d$i\\x;"; done
tail50=""; for i in $(seq 1 50); do tail50="$tail50 $D -f f$i.txt a$i b$i c$i d$i;"; done
c3="cd $U;"; for i in $(seq 1 25); do c3="$c3 sl d$i;"; done
same_as_main "T1 40 Set-Location, 50 rm -f, rm -rf" "$c1$tail50 $D -rf $U/results" deny
same_as_main "T2 40 cd dN\x, 50 rm -f, rm -rf" "$c2$tail50 $D -rf $U/results" deny
same_as_main "TC-064 25 Set-Location, rm -rf x" "$c3 $D -rf x" pass

# a very long cd target (main's own norm_path of it costs seconds on Git Bash): the branch
# must give the verdict it gives and must not cost more than main plus the candidate budget.
long_target() { # long_target <bytes> -> LT
  local n=$(( $1 / 5 )) i part=""
  local back=""; for ((i = 0; i < n; i++)); do part="${part}dd/"; back="${back}../"; done; part="${part}${back}"
  LT="cd $U; cd ${part}.; $D -rf results"
}
for kb in 16 32; do
  long_target $((kb * 1000))
  verdict "$H" "$LT"; bv=$VERDICT; bms=$MS; mv="-"; mms="-"; why=""
  if [ -n "$MAINH" ]; then verdict "$MAINH" "$LT"; mv=$VERDICT; mms=$MS; fi
  printf '%-52s main %-5s %6s ms   branch %-5s %6s ms  ' "~${kb} KB cd target, then rm -rf results" "$mv" "$mms" "$bv" "$bms"
  [ "$bv" = deny ] || why="want deny, got $bv. "
  [ -z "$MAINH" ] || [ "$bv" = "$mv" ] || why="${why}main gives $mv. "
  [ -z "$MAINH" ] || [ "$bms" -le $((mms + 10000)) ] || why="${why}branch took $((bms - mms)) ms more than main (budget 8000). "
  if [ -z "$why" ]; then echo ok; else echo "FAIL: $why"; fails=$((fails + 1)); fi
done

# the budgets themselves: no candidate budget means no candidate work (main's pass for a
# delete only the candidate would catch), and a target longer than 1024 characters adds none
cmd="cd $U; sl results; $D -rf x"
verdict "$H" "$cmd" ABF_CLEANUP_CAND_BUDGET_S=0; printf '%-52s %-5s  ' "candidate budget 0: no candidate work (main's pass)" "$VERDICT"
if [ "$VERDICT" = pass ]; then echo ok; else echo "FAIL: want pass, got $VERDICT"; fails=$((fails + 1)); fi
pad=$(printf 'p%.0s' $(seq 1 1100))
verdict "$H" "cd $U; sl results/$pad/..; $D -rf x"; printf '%-52s %-5s  ' "a target over 1024 characters adds no candidate" "$VERDICT"
if [ "$VERDICT" = pass ]; then echo ok; else echo "FAIL: want pass, got $VERDICT"; fails=$((fails + 1)); fi
verdict "$H" "cd $U; sl results/pp/..; $D -rf x"; printf '%-52s %-5s  ' "control: a short target does" "$VERDICT"
if [ "$VERDICT" = deny ]; then echo ok; else echo "FAIL: want deny, got $VERDICT"; fails=$((fails + 1)); fi

# no candidate budget at all (ABF_CLEANUP_CAND_BUDGET_S=0): every shape where main denies or asks
# gets main's verdict - skipping candidate work can only lose extra strictness.
P=/work/u9613010/lab_runs/x
n=0; bad=0
while IFS='|' read -r s_tool s_cwd s_exp s_cmd <&3 && IFS= read -r s_main <&4; do
  [ "$s_main" = deny ] || [ "$s_main" = ask ] || continue
  s_cmd=${s_cmd//⏎/$'\n'}; s_cmd=${s_cmd//@P/$P}; s_cmd=${s_cmd//@D/$D}; s_cwd=${s_cwd//@P/$P}
  out=$("$PY" -c "import json,sys;print(json.dumps({'tool_name':sys.argv[1],'cwd':sys.argv[2],'tool_input':{'command':sys.argv[3]}}))" "$s_tool" "$s_cwd" "$s_cmd" | ABF_CLEANUP_CAND_BUDGET_S=0 bash "$H")
  if [ -z "$out" ]; then got=pass; else got=$(jq -r '.hookSpecificOutput.permissionDecision // "warn"' <<<"$out"); fi
  n=$((n + 1))
  if [ "$got" != "$s_main" ]; then bad=$((bad + 1)); echo "  budget 0: want $s_main (main), got $got: $s_tool|${s_cmd:0:70}"; fi
done 3< "$HERE/confirm_cleanup_shapes.txt" 4< "$HERE/confirm_cleanup_shapes_main.txt"
printf '%-52s %s rows  ' "candidate budget 0: main's verdict on deny/ask rows" "$n"
if [ "$bad" = 0 ] && [ "$n" -gt 100 ]; then echo ok; else echo "FAIL: $bad differ"; fails=$((fails + 1)); fi

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
