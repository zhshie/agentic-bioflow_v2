#!/bin/bash
# The two memory helpers used to share one name, `to_gb`, with different signatures and different
# meanings (PITFALLS-style trap: paste one over the other and every figure is silently wrong):
#   tune_resources.sh  mem_to_gb       "4GB" / "512M" / "1.5"  ->  decimal GB, bare number = GB
#   why_pending.sh     mem_to_gb_ceil  <number> <unit>         ->  integer GB rounded UP, bare = MB
# One table per function. The expected values were captured by running the functions on the
# unrenamed base (origin/v3 62c91293) before this file or the rename existed, so the rename is
# proven behaviour-preserving rather than assumed. The scripts run their main flow when sourced,
# so each function is extracted by name instead.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0

# extract <script> <function>: the function's text, from "name() {" to the first "}" in column 0.
extract() { sed -n "/^$2() {/,/^}/p" "$ROOT/scripts/$1"; }

check() {   # check <label> <got> <want>
    printf '%-58s ' "$1"
    [ "$2" = "$3" ] && echo ok || { echo "FAIL: got <<$2>> want <<$3>>"; fails=$((fails+1)); }
}

defn=$(extract tune_resources.sh mem_to_gb)
printf '%-58s ' "tune_resources.sh defines mem_to_gb"
[ -n "$defn" ] && echo ok || { echo "FAIL: no mem_to_gb() in tune_resources.sh"; fails=$((fails+1)); }
eval "$defn"
if declare -F mem_to_gb >/dev/null; then
    check "mem_to_gb (no argument)" "$(mem_to_gb)" "0"
    while IFS='|' read -r in want; do
        check "mem_to_gb [$in]" "$(mem_to_gb "$in")" "$want"
    done <<'TABLE'
|0
4GB|4.0000
4 GB|4.0000
4G|4.0000
4|4.0000
0|0.0000
0.5|0.5000
1.5GB|1.5000
512MB|0.5000
512M|0.5000
1536mb|1.5000
2TB|2048.0000
1t|1024.0000
1T|1024.0000
1048576KB|1.000000
100K|0.000095
1kb|0.000001
abc|0.0000
.5GB|0.5000
3.14159MB|0.0031
7.9999G|7.9999
 12 gb |12.0000
12gb|12.0000
TABLE
fi

defn=$(extract why_pending.sh mem_to_gb_ceil)
printf '%-58s ' "why_pending.sh defines mem_to_gb_ceil"
[ -n "$defn" ] && echo ok || { echo "FAIL: no mem_to_gb_ceil() in why_pending.sh"; fails=$((fails+1)); }
eval "$defn"
if declare -F mem_to_gb_ceil >/dev/null; then
    while IFS='|' read -r num unit want; do
        check "mem_to_gb_ceil [$num|$unit]" "$(mem_to_gb_ceil "$num" "$unit")" "$want"
    done <<'TABLE'
53|G|53
53|g|53
1|T|1024
2|t|2048
0|G|0
1|K|1
1|k|1
1048576|K|1
1048577|K|2
1|M|1
1024|M|1
1025|M|2
53248|M|52
53249||53
1||1
0||0
1023||1
1024||1
1025||2
100|X|1
TABLE
fi

# The old shared name must be gone from both files, definitions and call sites alike, so the
# two cannot drift back into one name.
for f in tune_resources.sh why_pending.sh; do
    printf '%-58s ' "$f no longer mentions bare to_gb"
    if grep -nE '(^|[^_[:alnum:]])to_gb([^_[:alnum:]]|$)' "$ROOT/scripts/$f" >/dev/null; then
        echo "FAIL: $(grep -nE '(^|[^_[:alnum:]])to_gb([^_[:alnum:]]|$)' "$ROOT/scripts/$f" | head -1)"
        fails=$((fails+1))
    else echo ok; fi
done

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
