#!/bin/bash
# Guards tests/run_all.sh against a stale hard-coded file count in its header.
# TC-001 no standalone integer >= 10 in lines 1-20; TC-002 header says the count
# is taken at run time; TC-004 --list line count == real *.sh files minus run_all.sh;
# TC-005 this file is itself listed.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/tests/run_all.sh"
fail=0
bad() { echo "FAIL: $1"; fail=1; }

# TC-001
hits=$(head -20 "$RUNNER" | grep -nE '(^|[^[:alnum:]])[0-9]{2,}([^[:alnum:]]|$)')
[ -z "$hits" ] || bad "TC-001 header has a hard-coded number: $hits"

# TC-002
head -20 "$RUNNER" | grep -qiE 'run ?time' || bad "TC-002 header does not say the count is taken at run time"

# TC-004 / TC-005
listed=$(bash "$RUNNER" --list)
n_list=$(printf '%s\n' "$listed" | grep -c .)
n_real=$(ls "$ROOT"/tests/*.sh | grep -vc '/run_all\.sh$')
[ "$n_list" -eq "$n_real" ] || bad "TC-004 --list shows $n_list, tests/ has $n_real"
printf '%s\n' "$listed" | grep -q 'run_all_count_test\.sh' || bad "TC-005 run_all_count_test.sh not listed"

[ "$fail" -eq 0 ] && echo "ok"
exit "$fail"
