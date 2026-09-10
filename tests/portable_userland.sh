#!/bin/bash
# Everything in scripts/ and hooks/ may run on the user's own machine, and that
# machine is a Mac as often as a Linux box. macOS ships a BSD userland and bash
# 3.2, so a handful of spellings that are ordinary here are either a different
# flag there or absent entirely.
#
# This is a static check rather than nine individual fixes, because nine fixes
# leave the tenth to be discovered by whoever installs on a Mac next. The first
# time it ran it found nine, and four of those failed *silently* - a token
# whose mode is never checked, a hook that reports no runs in flight, a delete
# guard that stops resolving symlinks, an upload that displays 0 B. A silent
# failure on someone else's machine is the exact shape this repo keeps writing
# PITFALLS entries about.
#
# Two escape hatches, both explicit and both greppable:
#   # GNU-ok-file: <reason>   on any line of a file that only ever runs on the
#                             site, where the userland is known to be GNU
#   # GNU-ok: <reason>        at the end of one line
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
fails=0

# pattern<TAB>what breaks. Only spellings measured or documented as divergent -
# a check that guesses would be worked around rather than obeyed.
RULES=$(cat <<'R'
(^|[^a-zA-Z-])stat[[:space:]]+-[a-zA-Z]*c	stat -c is GNU; BSD stat spells it -f
(^|[^a-zA-Z-])readlink[[:space:]]+-[a-zA-Z]*f	readlink -f is absent on older macOS
(^|[^a-zA-Z-])grep[[:space:]]+-[a-zA-Z]*P	grep -P needs PCRE; BSD grep has none
(^|[^a-zA-Z-])du[[:space:]]+-[a-zA-Z]*b	du -b is GNU; BSD du has no byte mode
(^|[;|&(]|[[:space:]])timeout[[:space:]]+[-"'$0-9]	timeout is GNU coreutils, absent on stock macOS
(declare|local|typeset)[[:space:]]+-[a-zA-Z]*A[[:space:]]	associative arrays need bash 4; macOS ships 3.2
(^|[^a-zA-Z_])(mapfile|readarray)[[:space:]]	mapfile/readarray need bash 4
\$\{[A-Za-z_][A-Za-z0-9_]*(\^\^|,,)	case conversion needs bash 4
(^|[^a-zA-Z-])sed[[:space:]]+-i[[:space:]]+-	sed -i takes a mandatory argument on BSD
(^|[^a-zA-Z-])date[[:space:]]+-d[[:space:]]	date -d is GNU; BSD date uses -j -f
(^|[^a-zA-Z-])base64[[:space:]]+-[a-zA-Z]*w	base64 -w is GNU
-printf[[:space:]]	find -printf is GNU
(^|[^a-zA-Z-])xargs[[:space:]]+-[a-zA-Z]*r	xargs -r is GNU
R
)

for f in scripts/*.sh scripts/utils/*.sh hooks/*.sh; do
    [ -r "$f" ] || continue
    grep -q 'GNU-ok-file:' "$f" && continue
    while IFS=$'\t' read -r pat why; do
        [ -n "$pat" ] || continue
        # Whole-line comments are prose: PITFALLS quotes these spellings on
        # purpose, and a check that cannot tell an explanation from a call
        # would make every explanation unwritable.
        while IFS=: read -r ln text; do
            [ -n "$ln" ] || continue
            case "$text" in \#*|'') continue ;; esac
            case "$text" in *"GNU-ok:"*) continue ;; esac
            echo "FAIL  $f:$ln  $why"
            echo "      ${text:0:96}"
            fails=$((fails+1))
        done < <(grep -nE -- "$pat" "$f" | sed 's/^\([0-9]*\):[[:space:]]*/\1:/')
    done <<< "$RULES"
done

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails unportable spellings"; exit 1; }
