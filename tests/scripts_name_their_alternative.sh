#!/bin/bash
# Invariant 1 (docs/PRINCIPLES.md): before adding anything, say out loud what
# Seqera, nf-core or any other maintained tool already does the job. That was
# a spoken check, easy to skip under a deadline - this makes it mechanical.
#
# Every file under scripts/ (and scripts/utils/) must carry, in its first 40
# lines, exactly one line of the form
#
#   # Not <tool>: <reason>
#   # Nothing existing: <why>
#
# "Not <tool>" needs a capital N - lowercase "not" appears all over these
# headers in ordinary prose ("does not", "is not") and would make the check
# fire on sentences that were never meant as this line. Python files use the
# same '#' comment - not a docstring, which a later comment-only diff check
# cannot tell apart from code.
#
# ROOT is parameterised via SCRIPTS_NAME_ALT_ROOT so a mutation test can point
# this at a scratch copy of the tree instead of the real one.
set -uo pipefail
DEFAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${SCRIPTS_NAME_ALT_ROOT:-$DEFAULT_ROOT}"

[ -d "$ROOT/scripts" ] || { echo "FAIL: no scripts/ under $ROOT"; exit 1; }

PATTERN='^#[[:space:]]*(Not[[:space:]]+.+:|Nothing existing:)'

missing=0
short=0
count=0

check_file() {
    local f="$1" hit ln text reason
    hit=$(sed -n '1,40p' "$f" | grep -nE "$PATTERN" | head -1)
    if [ -z "$hit" ]; then
        echo "MISSING  ${f#"$ROOT"/}: no '# Not <tool>: ...' or '# Nothing existing: ...' line in the first 40 lines"
        missing=$((missing + 1))
        return
    fi
    ln="${hit%%:*}"
    text="${hit#*:}"          # strip "N:" (the grep line-number prefix)
    reason="${text#*:}"       # strip "# Not <tool>:" or "# Nothing existing:"
    reason="$(printf '%s' "$reason" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    if [ "${#reason}" -lt 15 ]; then
        echo "SHORT    ${f#"$ROOT"/}:$ln reason is only ${#reason} chars: '${reason}'"
        short=$((short + 1))
    fi
}

files=$(
    {
        find "$ROOT/scripts" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \)
        find "$ROOT/scripts/utils" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) 2>/dev/null
    } | sort
)

while IFS= read -r f; do
    [ -n "$f" ] || continue
    count=$((count + 1))
    check_file "$f"
done <<< "$files"

echo
if [ "$missing" -gt 0 ] || [ "$short" -gt 0 ]; then
    echo "FAIL: $missing missing, $short with a too-short reason (of $count scripts checked)"
    exit 1
fi
echo "OK: all $count scripts under scripts/ name their alternative"
