#!/bin/bash
# cd-target-backslash (#76, #75): the cleanup guard keeps a set of candidate folders
# (CANDS) and judges every relative word against each. On a long command that must stay
# close to what main costs: the guard has its own 20 s deadline (#62), and past it the
# verdict is `ask`, which is weaker than the `deny` main reaches.
#
# Two commands the security review found: 40 Set-Location (or `cd dN\x`) segments, then
# 50 `rm -f` of five names each, then the one real delete of results/. The verdict must
# be deny, as on main, and well inside the deadline. A chain of 25 Set-Location and a
# delete (TC-064) must stay a pass.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
H="$HERE/../hooks/confirm_cleanup.sh"
command -v jq >/dev/null 2>&1 || { echo "jq is required for this test"; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "python is required for this test"; exit 1; }
export MSYS2_ARG_CONV_EXCL='*'
D=$(printf '\x72\x6d')
U=/work/u/lab_runs/x
fails=0
ms_now() { "$PY" -c 'import time;print(int(time.time()*1000))'; }
check() { # check <label> <command> <want verdict> <limit ms>
  local out got t0 t1 ms
  t0=$(ms_now)
  out=$("$PY" -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$2" | bash "$H")
  t1=$(ms_now); ms=$((t1 - t0))
  if [ -z "$out" ]; then got=pass; else got=$(jq -r '.hookSpecificOutput.permissionDecision // "warn"' <<<"$out"); fi
  printf '%-60s %6s ms  ' "$1" "$ms"
  if [ "$got" = "$3" ] && [ "$ms" -le "$4" ]; then echo "ok ($got)"; else
    echo "FAIL: want $3 within $4 ms, got $got in $ms ms"; fails=$((fails + 1)); fi
}
c1="cd $U;"; for i in $(seq 1 40); do c1="$c1 Set-Location d$i;"; done
c2="cd $U;"; for i in $(seq 1 40); do c2="$c2 cd d$i\\x;"; done
tail50=""; for i in $(seq 1 50); do tail50="$tail50 $D -f f$i.txt a$i b$i c$i d$i;"; done
c3="cd $U;"; for i in $(seq 1 25); do c3="$c3 sl d$i;"; done
# TC-064 / TC-065 of the bug's test cases are in confirm_cleanup_test.sh; here the cost.
check "40 Set-Location, 50 rm -f, rm -rf results (deny)"   "$c1$tail50 $D -rf $U/results" deny 10000
check "40 cd dN\\x, 50 rm -f, rm -rf results (deny)"        "$c2$tail50 $D -rf $U/results" deny 10000
check "TC-064 25 chained Set-Location, then rm -rf x (pass)" "$c3 $D -rf x" pass 10000
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
