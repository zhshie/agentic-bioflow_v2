#!/bin/bash
# docs/INSTALL.md (issue #93 item 7, docs part): the connection guide cannot drift from the code.
#   TC-001 file exists; TC-002 six headings in order; TC-003 every `abf-platform <sub>` exists in cli.py;
#   TC-005 every backticked tool-looking name (with an underscore, or one of the write tools) is a tool in mcp_server.py;
#   TC-007 every backticked file-looking repo path exists; TC-009 no literal PAT value;
#   TC-013 names `abf-platform pat new`.
# INSTALL_DOC=<file> checks another copy (used to prove the checks catch a fake).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DOC="${INSTALL_DOC:-$ROOT/docs/INSTALL.md}"
fails=0
ok()   { printf '%-70s ok\n' "$1"; }
fail() { printf '%-70s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

# TC-001
if [ -r "$DOC" ]; then ok "TC-001 INSTALL.md exists"; else fail "TC-001 INSTALL.md exists" "$DOC is missing"; echo "FAILED: 1"; exit 1; fi

# TC-002
expect=("What you need" "Claude Code" "Claude Desktop" "Codex" "Check it works" "Not built yet")
mapfile -t got < <(grep -E '^## ' "$DOC" | sed -E 's/^## +([0-9]+\. *)?//')
if [ "${#got[@]}" -ne 6 ]; then
    fail "TC-002 six headings" "found ${#got[@]} '## ' headings, want 6"
else
    bad=0
    for i in 0 1 2 3 4 5; do
        case "${got[$i]}" in "${expect[$i]}"*) ;; *) bad=1; fail "TC-002 heading $((i+1))" "got '${got[$i]}', want '${expect[$i]}...'";; esac
    done
    [ "$bad" -eq 0 ] && ok "TC-002 six headings in order"
fi

# TC-003
CLI="$ROOT/platform/abf_platform/cli.py"
subs=$(grep -oE 'abf-platform +[a-z][a-z-]*( +[a-z][a-z-]*)?' "$DOC" | sort -u)
bad=0; n=0
while IFS= read -r line; do
    [ -z "$line" ] && continue
    set -- $line; w1="${2:-}"; w2="${3:-}"; n=$((n+1))
    if ! grep -qE "add_parser\(\"$w1\"" "$CLI"; then fail "TC-003 abf-platform $w1" "no such command in cli.py"; bad=1; continue; fi
    case "$w1" in token|agent-token|user|pat|oauth|ce|runs)
        if [ -n "$w2" ] && ! grep -qE "add_parser\(\"$w2\"" "$CLI"; then fail "TC-003 abf-platform $w1 $w2" "no such subcommand in cli.py"; bad=1; fi;;
    esac
done <<< "$subs"
[ "$n" -eq 0 ] && { fail "TC-003 abf-platform commands" "the doc names none"; bad=1; }
[ "$bad" -eq 0 ] && ok "TC-003 every abf-platform command named exists"
grep -qF 'abf-platform pat new' "$DOC" && ok "TC-013 names 'abf-platform pat new'" || fail "TC-013 pat new" "not named"

# TC-005
MCP="$ROOT/platform/abf_platform/mcp_server.py"
ticks=$(grep -oE '`[^`]+`' "$DOC" | tr -d '`' | sort -u)
bad=0; n=0
for t in $ticks; do
    if [[ "$t" =~ ^[a-z]+(_[a-z]+)+$ ]] || [[ "$t" =~ ^(launch|cancel|resume|relaunch)$ ]]; then
        n=$((n+1))
        grep -qE "name=\"$t\"" "$MCP" || { fail "TC-005 tool \`$t\`" "not a tool in mcp_server.py"; bad=1; }
    fi
done
[ "$n" -eq 0 ] && { fail "TC-005 tool names" "the doc names none"; bad=1; }
[ "$bad" -eq 0 ] && ok "TC-005 every MCP tool named exists"

# TC-007
bad=0
for t in $ticks; do
    case "$t" in *"<"*|*">"*|http*|/*|*" "*) continue;; esac
    if [[ "$t" == */* && "$t" =~ \.[A-Za-z0-9]+$ ]]; then
        [ -e "$ROOT/$t" ] || { fail "TC-007 path \`$t\`" "not in the repository"; bad=1; }
    fi
done
[ "$bad" -eq 0 ] && ok "TC-007 every repo path named exists"

# TC-009
if grep -qE 'abf_pat_[A-Za-z0-9]{8,}' "$DOC"; then fail "TC-009 no literal token" "a PAT-looking value is in the doc"; else ok "TC-009 no literal token"; fi

[ "$fails" -eq 0 ] && { echo "all ok"; exit 0; }
echo "FAILED: $fails"; exit 1
