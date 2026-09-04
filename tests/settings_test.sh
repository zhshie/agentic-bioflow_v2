#!/bin/bash
# `settings.sh --set` exists for one situation: a script that ran on the site
# discovered where it put things, and the settings file that matters is on
# another machine. Its set_setting could only ever write to the file it can see.
#
# The comment-preserving behaviour is not cosmetic - the comments in a settings
# file are usually the only record of why a value is what it is.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/settings.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
F="$TMP/env.yaml"
fails=0
t() { printf '%-56s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

run() { LAB_SETTINGS_FILE="$F" bash "$S" "$@"; }

run --set tw_bin /work/_bin/tw >/dev/null
t "--set writes a key that was not there"  "$(run tw_bin)"  "/work/_bin/tw"
t "and creates the file mode 600"          "$(stat -c %a "$F")" "600"

printf 'workspace_id: 111  # the one value a lab shares\n' >> "$F"
run --set workspace_id 222 >/dev/null
t "--set replaces an existing value"       "$(run workspace_id)" "222"
t "and keeps the comment saying why"       "$(grep -c 'the one value a lab shares' "$F")" "1"

t "a missing key still returns its default" "$(run nope fallback)" "fallback"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
