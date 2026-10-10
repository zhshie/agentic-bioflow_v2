#!/bin/bash
# #80 follow-up: with "onFailure": "block" a gate that dies with exit 1 blocks
# every ordinary Bash/Write/Edit call. On bash 3.2 (macOS /bin/bash) and on bash
# before 4.4, expanding an EMPTY array as "${a[@]}" under `set -u` is a fatal
# "unbound variable" error, which is exactly such an exit 1. So every array
# expansion in the gates and the files they source must use the guarded form
#   ${a[@]+"${a[@]}"}
# (or sit behind a length check, which this static test cannot see: use the
# guarded form anyway). ${#a[@]} and ${!a[@]} are fine.
#
# Static on purpose: no bash 3.2 is available on the test machines.
# Test cases: .specify/bugs/hooks-fail-open-on-timeout (review round 1).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
fails=0
FILES="confirm_launch confirm_cleanup guard_plugin_files confirm_walkthrough in_use launch_trigger"

scan() { # scan <file>  -> prints "line:text" of each unguarded expansion
  sed -E 's/\$\{([A-Za-z_][A-Za-z_0-9]*)\[[@*]\]\+"\$\{\1\[[@*]\]\}"\}//g' "$1" \
    | grep -nE '\$\{[A-Za-z_][A-Za-z_0-9]*\[[@*]\]' \
    | grep -vE '^[0-9]+:[[:space:]]*#' || true
}

for f in $FILES; do
  hits=$(scan "$ROOT/hooks/$f.sh")
  if [ -z "$hits" ]; then printf '%-40s ok\n' "hooks/$f.sh: no unguarded array expansion"
  else printf '%-40s FAIL\n%s\n' "hooks/$f.sh" "$hits"; fails=$((fails+1)); fi
done

# the scanner itself: it must flag an unguarded expansion and pass a guarded one
T=$(mktemp -d); trap 'command rm -rf "$T"' EXIT
printf 'for x in "${a[@]}"; do :; done\n' > "$T/bad.sh"
printf 'for x in ${a[@]+"${a[@]}"}; do :; done\nn=${#a[@]}\n# "${a[@]}"\n' > "$T/good.sh"
[ -n "$(scan "$T/bad.sh")" ] && echo "scanner flags an unguarded expansion          ok" || { echo "scanner misses an unguarded expansion FAIL"; fails=$((fails+1)); }
[ -z "$(scan "$T/good.sh")" ] && echo "scanner passes guarded, length and comment    ok" || { echo "scanner flags a guarded expansion FAIL"; fails=$((fails+1)); }

[ "$fails" -eq 0 ] && echo "ALL OK" || { echo "$fails FAILED"; exit 1; }
