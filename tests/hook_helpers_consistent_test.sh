#!/bin/bash
# The safety-net hooks each carry their own copy of a few small helpers, on
# purpose: a gate that sources a shared helper vanishes when the helper is
# missing (see CLAUDE.md, "The two safety-net hooks deliberately do not source
# it"). The price of copying is drift: fix a bug in one copy and the other
# copies keep it. This test is the substitute for the shared file - it pulls
# the body of each helper out of every hooks/*.sh that defines it, drops
# comments and blank lines, and requires the same-named copies to be identical.
#
# Helpers compared: abf_emit, abf_cap, abf_jq_works, deny, ask.
#
# What "identical" means here:
#   - the function header's trailing `# comment` is dropped, whole-line comments
#     are dropped, blank lines are dropped, trailing blanks are trimmed;
#   - indentation and everything else is kept, so a changed jq filter, a changed
#     fallback message or a changed test bracket is a difference.
#   Known limit: a blank line INSIDE a quoted multi-line string (abf_cap's
#   truncation marker) is removed with the others; a change that only adds or
#   removes such a blank line is not seen here.
#
# Differences that exist today are explicit exceptions below, each with its
# reason and each pinned to its exact text, so an exception cannot quietly grow
# into a real divergence, and an exception that stops being a difference fails
# too (it should then be deleted from here).
#
# The set of files that define each helper is pinned as well: a new copy of a
# helper in another hook fails until it is added to the table, which is what
# brings it under comparison.
#
# hooks/ is read-only here; nothing is executed from it.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
HD="$ROOT/hooks"
fails=0

ok()  { printf '%-78s ok\n' "$1"; }
bad() { printf '%-78s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

# body_of <file> <name>: the helper's definition, normalised as described above.
body_of() {
    awk -v n="$2" '
        BEGIN { inb = 0; re = "^[ \t]*" n "[ \t]*\\(\\)[ \t]*\\{" }
        !inb && $0 ~ re {
            line = $0
            sub(/\{[ \t]+#.*$/, "{", line)
            sub(/[ \t]+$/, "", line)
            print line
            if (line !~ /\}$/) inb = 1
            next
        }
        inb {
            if ($0 ~ /^[ \t]*#/ || $0 ~ /^[ \t]*$/) next
            sub(/[ \t]+$/, "", $0)
            print
            if ($0 == "}") inb = 0
        }' "$1"
}

# flat_of <text>: the statements of a one-line or multi-line definition, one per
# line, with the `name() {` and `}` framing removed. Two definitions that differ
# only in layout (`a; b` on one line vs. one statement per line) flatten alike.
flat_of() {
    printf '%s\n' "$1" | sed -E '1s/^[^{]*\{[ \t]*//; s/[ \t]*\}[ \t]*$//' |
        tr ';' '\n' | sed -E 's/^[ \t]+//; s/[ \t]+$//' | grep -v '^$'
}

# defining_files <name>: basenames of hooks/*.sh that start a definition of it.
defining_files() {
    local f
    for f in "$HD"/*.sh; do
        grep -qE "^[[:space:]]*$1[[:space:]]*\(\)" "$f" && basename "$f"
    done | sort | tr '\n' ' ' | sed 's/ $//'
}

check_files() { # check_files <name> <expected files, space separated>
    local got; got=$(defining_files "$1")
    if [ "$got" = "$2" ]; then ok "$1: defined in exactly: $2"
    else bad "$1: files that define it" "expected [$2], found [$got] - add a new copy to this table so it is compared"; fi
    local f c
    for f in $2; do
        c=$(grep -cE "^[[:space:]]*$1[[:space:]]*\(\)" "$HD/$f")
        [ "$c" = 1 ] || bad "$1: $f defines it once" "found $c definitions"
        [ -n "$(body_of "$HD/$f" "$1")" ] || bad "$1: $f body extracted" "empty - extractor no longer matches this file's layout"
    done
}

check_same() { # check_same <name> <reference file> <other files...>
    local name=$1 ref=$2 f; shift 2
    local want; want=$(body_of "$HD/$ref" "$name")
    for f in "$@"; do
        if [ "$(body_of "$HD/$f" "$name")" = "$want" ]; then
            ok "$name: $f is identical to $ref"
        else
            bad "$name: $f is identical to $ref" "bodies differ: diff <(body $ref) <(body $f) ->$(diff <(printf '%s\n' "$want") <(printf '%s\n' "$(body_of "$HD/$f" "$name")") | head -8 | tr '\n' '|')"
        fi
    done
}

# ---- same-named copies that must be identical ------------------------------
echo "== helpers that are copies of one another =="
check_files abf_cap        "confirm_cleanup.sh confirm_launch.sh confirm_walkthrough.sh guard_plugin_files.sh"
check_same  abf_cap        confirm_cleanup.sh confirm_launch.sh confirm_walkthrough.sh guard_plugin_files.sh

check_files abf_emit       "confirm_cleanup.sh confirm_launch.sh confirm_walkthrough.sh guard_plugin_files.sh"
check_same  abf_emit       confirm_cleanup.sh confirm_launch.sh confirm_walkthrough.sh guard_plugin_files.sh

check_files abf_jq_works   "confirm_launch.sh confirm_walkthrough.sh plugin_intro.sh"
check_same  abf_jq_works   confirm_launch.sh confirm_walkthrough.sh plugin_intro.sh

# ---- deny -------------------------------------------------------------------
# confirm_cleanup.sh and guard_plugin_files.sh spell it over four lines and must
# match each other exactly. EXCEPTION confirm_walkthrough.sh: the same two
# statements on one line, next to its one-line allow()/warn() siblings. Pinned to
# that exact text, and required to flatten to the same statements as the others,
# so the exception covers layout only, never behaviour.
echo "== deny =="
check_files deny           "confirm_cleanup.sh confirm_walkthrough.sh guard_plugin_files.sh"
check_same  deny           confirm_cleanup.sh guard_plugin_files.sh
DENY_REF=$(body_of "$HD/confirm_cleanup.sh" deny)
DENY_WT=$(body_of "$HD/confirm_walkthrough.sh" deny)
DENY_WT_PIN='deny()  { abf_emit deny "$1" -; exit 0; }'
if [ "$DENY_WT" = "$DENY_WT_PIN" ]; then ok "deny: confirm_walkthrough.sh is the pinned one-line form"
else bad "deny: confirm_walkthrough.sh is the pinned one-line form" "got: $DENY_WT"; fi
if [ "$DENY_WT" = "$DENY_REF" ]; then
    bad "deny: exception for confirm_walkthrough.sh still needed" "it now equals the multi-line form; delete the exception"
elif [ "$(flat_of "$DENY_WT")" = "$(flat_of "$DENY_REF")" ] && [ -n "$(flat_of "$DENY_REF")" ]; then
    ok "deny: confirm_walkthrough.sh differs from the others in layout only"
else
    bad "deny: confirm_walkthrough.sh differs from the others in layout only" "statements differ: [$(flat_of "$DENY_WT" | tr '\n' '|')] vs [$(flat_of "$DENY_REF" | tr '\n' '|')]"
fi

# ---- ask --------------------------------------------------------------------
# EXCEPTION, both copies: the two ask() functions answer different questions and
# are not interchangeable. confirm_cleanup.sh takes ONE message and shows it as
# both the permission reason and the additional context (R2: the work/ and
# .nextflow/cache/ delete ask); confirm_launch.sh takes the context as $1 and a
# separate permission reason as $2 (R2/D3: the launch and transport asks). Each is
# pinned to its exact text; they must also still differ from one another.
echo "== ask =="
check_files ask            "confirm_cleanup.sh confirm_launch.sh"
ASK_CL=$(body_of "$HD/confirm_cleanup.sh" ask)
ASK_LA=$(body_of "$HD/confirm_launch.sh" ask)
ASK_CL_PIN=$'ask() {\n    abf_emit ask "$1" "$1"\n    exit 0\n}'
ASK_LA_PIN=$'ask() {\n    abf_emit ask "$2" "$1"\n    exit 0\n}'
[ "$ASK_CL" = "$ASK_CL_PIN" ] && ok "ask: confirm_cleanup.sh is the pinned one-message form (reason = context = \$1)" \
    || bad "ask: confirm_cleanup.sh is the pinned one-message form" "got: $(printf '%s' "$ASK_CL" | tr '\n' '|')"
[ "$ASK_LA" = "$ASK_LA_PIN" ] && ok "ask: confirm_launch.sh is the pinned two-argument form (context \$1, reason \$2)" \
    || bad "ask: confirm_launch.sh is the pinned two-argument form" "got: $(printf '%s' "$ASK_LA" | tr '\n' '|')"
if [ "$ASK_CL" = "$ASK_LA" ]; then
    bad "ask: the two copies still differ" "they are now identical; delete this exception and compare them with check_same"
else
    ok "ask: the two copies still differ (so the exception is still needed)"
fi

echo
if [ "$fails" -eq 0 ]; then echo "hook_helpers_consistent_test: all passed"; exit 0
else echo "hook_helpers_consistent_test: $fails FAILED"; exit 1; fi
