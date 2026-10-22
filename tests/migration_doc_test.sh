#!/bin/bash
# docs/MIGRATION.md (issue #119 item 7): the v2 -> v3 guide cannot drift from the code.
#   TC-001 the file exists; TC-002 seven headings in the planned order;
#   TC-003 every settings-key-looking name in backticks in sections 2 and 3 is in
#          docs/SETTINGS.md or scripts/settings.sh (so it cannot invent keys);
#   TC-005/TC-009 every `abf-platform <subcommand>` the doc names exists in cli.py
#          (a second word is checked too when the first is a command group).
# MIGRATION_DOC=<file> checks another copy (used to prove the checks catch a fake).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DOC="${MIGRATION_DOC:-$ROOT/docs/MIGRATION.md}"
fails=0
ok()   { printf '%-70s ok\n' "$1"; }
fail() { printf '%-70s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

# TC-001
if [ -r "$DOC" ]; then ok "TC-001 MIGRATION.md exists"; else fail "TC-001 MIGRATION.md exists" "$DOC is missing"; echo "FAILED: 1"; exit 1; fi

# TC-002: the "## " headings, in order
expect=("Who this is for and what changes" "Step by step" "Seqera fields" "Existing runs and project folders" "Going back to v2" "Not built yet" "From the v2 \`tw\` flow")
mapfile -t got < <(grep -E '^## ' "$DOC" | sed -E 's/^## +([0-9]+\. *)?//')
if [ "${#got[@]}" -ne 7 ]; then
    fail "TC-002 seven headings" "found ${#got[@]} '## ' headings, want 7"
else
    bad=0
    for i in 0 1 2 3 4 5 6; do
        case "${got[$i]}" in "${expect[$i]}"*) ;; *) bad=1; fail "TC-002 heading $((i+1))" "got '${got[$i]}', want '${expect[$i]}...'";; esac
    done
    [ "$bad" -eq 0 ] && ok "TC-002 seven headings in order"
fi

section() { awk -v n="$1" '/^## /{c++} c==n' "$DOC"; }

# TC-003: key-looking names (lower-case words joined by underscores, or .seqera_token)
keys=$( { section 2; section 3; } | grep -oE '`[^`]+`' | tr -d '`' | grep -E '^(\.?[a-z]+(_[a-z]+)+)$' | sort -u)
bad=0
for k in $keys; do
    if ! grep -qF -- "$k" "$ROOT/docs/SETTINGS.md" "$ROOT/scripts/settings.sh"; then
        fail "TC-003 key \`$k\`" "in neither docs/SETTINGS.md nor scripts/settings.sh"; bad=1
    fi
done
[ "$bad" -eq 0 ] && ok "TC-003 every key named in sections 2-3 is real"

# TC-005 / TC-009
CLI="$ROOT/platform/abf_platform/cli.py"
CLI_LAUNCH="$ROOT/platform/abf_launch/cli.py"   # the launch subcommand of abf-platform is registered here
subs=$(grep -oE 'abf-platform +[a-z][a-z-]*( +[a-z][a-z-]*)?' "$DOC" | sort -u)
bad=0; n=0
while IFS= read -r line; do
    [ -z "$line" ] && continue
    set -- $line; w1="${2:-}"; w2="${3:-}"; n=$((n+1))
    if ! grep -qE "add_parser\(\"$w1\"" "$CLI" "$CLI_LAUNCH"; then fail "TC-005 abf-platform $w1" "no such command in cli.py"; bad=1; continue; fi
    case "$w1" in token|agent-token|user|pat|oauth|ce|runs)
        if [ -n "$w2" ] && ! grep -qE "add_parser\(\"$w2\"" "$CLI"; then fail "TC-005 abf-platform $w1 $w2" "no such subcommand in cli.py"; bad=1; fi;;
    esac
done <<< "$subs"
[ "$n" -eq 0 ] && { fail "TC-005 abf-platform commands" "the doc names none"; bad=1; }
[ "$bad" -eq 0 ] && ok "TC-005 every abf-platform command named exists"
grep -qF 'abf-platform pat new' "$DOC" && ok "TC-009 section names 'abf-platform pat new'" || fail "TC-009 pat new" "not named"

[ "$fails" -eq 0 ] && { echo "all ok"; exit 0; }
echo "FAILED: $fails"; exit 1
