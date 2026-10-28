#!/bin/bash
# Guards tests/run_all.sh --shard I/N, which the CI matrix (.github/workflows/tests.yml)
# depends on: if the parts overlap or miss a file, a test either runs twice or - worse -
# never runs and CI stays green. Uses --list only, so no test is run from in here.
# TC-001 for N in 1..6 the parts are disjoint and together equal the full list
# TC-002 with N=4 the platform wrappers are spread: the parts differ by at most one, and together they are all of them (SS-36, SS-37)
# SS-11 the list has the nine platform wrappers
# TC-003 the split is deterministic (twice the same)
# TC-004 --shard combined with --only splits only the matching files
# TC-005 bad values (0/4, 5/4, 1/0, x, 2) are refused with exit 2
# TC-006 tests.yml names every part 1..4 of 4 and keeps the aggregate job "run_all"
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
R="$ROOT/tests/run_all.sh"
fails=0
ok()  { printf '%-62s ok\n' "$1"; }
bad() { printf '%-62s FAIL\n' "$1"; fails=$((fails + 1)); }

all="$(bash "$R" --list | LC_ALL=C sort)"
for n in 1 2 3 4 5 6; do
    parts=""
    i=1
    while [ "$i" -le "$n" ]; do
        parts="$parts$(bash "$R" --shard "$i/$n" --list)
"
        i=$((i + 1))
    done
    got="$(printf '%s' "$parts" | grep . | LC_ALL=C sort)"
    if [ "$got" = "$all" ]; then ok "TC-001 N=$n covers every file exactly once"; else bad "TC-001 N=$n covers every file exactly once"; fi
done

# platform_spread "<count> <count> ..." <expected total>: true when the counts differ by at most 1 and add up to the total
platform_spread() {
    local min=999 max=0 sum=0 c
    for c in $1; do
        [ "$c" -lt "$min" ] && min=$c
        [ "$c" -gt "$max" ] && max=$c
        sum=$((sum + c))
    done
    [ $((max - min)) -le 1 ] && [ "$sum" -eq "$2" ]
}
wrappers_on_disk="$(ls "$ROOT"/tests/ | grep -cE '^platform_(test|clock_test|shard_[0-9]+_test)\.sh$')"
plat=""
for i in 1 2 3 4; do
    c="$(bash "$R" --shard "$i/4" --list | grep -cE '^platform_(test|clock_test|shard_[0-9]+_test)\.sh$')"
    plat="$plat$c "
done
listed_names="$(bash "$R" --list --allow-msys)"
missing=""
for n in platform_test.sh platform_shard_2_test.sh platform_shard_3_test.sh platform_shard_4_test.sh platform_shard_5_test.sh platform_shard_6_test.sh platform_shard_7_test.sh platform_shard_8_test.sh platform_clock_test.sh; do
    printf '%s
' "$listed_names" | grep -qx "$n" || missing="$missing $n"
done
[ -z "$missing" ] && [ "$wrappers_on_disk" = 9 ] && ok "SS-11 the list has the nine platform wrappers" || bad "SS-11 nine platform wrappers (missing:$missing, on disk: $wrappers_on_disk)"
platform_spread "$plat" "$wrappers_on_disk" && ok "TC-002 platform wrappers spread over the parts (N=4)" || bad "TC-002 platform wrappers per part: $plat"
platform_spread "$plat" 9 && ok "SS-36 the four parts hold 9 platform wrappers, differing by at most one" || bad "SS-36 platform wrappers per part: $plat"
# SS-37: the check must be able to fail. All wrappers in one part, and a lost wrapper, are both red.
platform_spread "9 0 0 0" 9 && bad "SS-37 all wrappers in one part is judged green" || ok "SS-37 all wrappers in one part is judged red"
platform_spread "2 2 2 2" 9 && bad "SS-37 a lost wrapper is judged green" || ok "SS-37 counts that do not add up are judged red"

[ "$(bash "$R" --shard 2/4 --list)" = "$(bash "$R" --shard 2/4 --list)" ] && ok "TC-003 deterministic" || bad "TC-003 deterministic"

a="$(bash "$R" --only platform_ --shard 1/2 --list; bash "$R" --only platform_ --shard 2/2 --list)"
b="$(bash "$R" --only platform_ --list)"
[ "$(printf '%s\n' "$a" | LC_ALL=C sort)" = "$(printf '%s\n' "$b" | LC_ALL=C sort)" ] && ok "TC-004 --only + --shard" || bad "TC-004 --only + --shard"

for v in 0/4 5/4 1/0 x 2 1/x; do
    bash "$R" --shard "$v" --list >/dev/null 2>&1; rc=$?
    [ "$rc" = 2 ] && ok "TC-005 --shard $v refused" || bad "TC-005 --shard $v refused (rc=$rc)"
done

Y="$ROOT/.github/workflows/tests.yml"
if [ -f "$Y" ]; then
    for i in 1 2 3 4; do grep -q -- "--shard $i/4\|shard: \[1, 2, 3, 4\]" "$Y" && continue; bad "TC-006 tests.yml mentions shard $i/4"; done
    grep -qE '^  run_all:' "$Y" && grep -q 'merge_group:' "$Y" && ok "TC-006 tests.yml: job run_all and merge_group" || bad "TC-006 tests.yml: job run_all and merge_group"
else
    ok "TC-006 tests.yml absent (deployed copy), skipped"
fi

[ "$fails" -eq 0 ] && echo "ALL OK" || { echo "$fails FAILED"; exit 1; }
