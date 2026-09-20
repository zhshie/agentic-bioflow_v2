#!/bin/bash
# PITFALLS 35, second half: six scripts align their output with runs of
# spaces, which a terminal renders as columns and a GUI surface (the Claude
# app) collapses into one run-on line. The fix is a rule the model follows -
# relay that output inside a fenced code block - and a rule nobody can check
# is a rule that rots.
#
# So this asserts two things, and the second is the one that matters:
#   1. every commands/*.md file and skills/operational/SKILL.md state the rule
#   2. the list of scripts they name is exactly the set that actually aligns
#      output today, measured by scanning for printf '%-<n>s'
#
# (2) is what stops the sentence from going stale: a seventh script that
# starts printing columns turns this red on the commit that adds it, instead
# of quietly being the one output nobody wraps.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0

check() { printf '%-62s ' "$1"; shift; if "$@"; then echo ok; else echo FAIL; fails=$((fails+1)); fi; }

DOCS=("$ROOT"/commands/*.md "$ROOT/skills/operational/SKILL.md")

for f in "${DOCS[@]}"; do
    rel="${f#$ROOT/}"
    printf '%-62s ' "$rel states the code-block relay rule"
    if grep -qF 'fenced code block' "$f" && grep -qF 'PITFALLS 35' "$f"; then
        echo ok
    else
        echo "FAIL: no code-block relay rule"; fails=$((fails+1))
    fi
done

# The measured set: scripts that print at least one space-padded field.
MEASURED=$(grep -rlP "printf.*%-[0-9]+s" "$ROOT/scripts/" 2>/dev/null \
           | xargs -r -n1 basename | sort -u)

printf '%-62s ' "something in scripts/ actually aligns output"
[ -n "$MEASURED" ] && echo ok || { echo "FAIL: nothing matched - has the scan broken?"; fails=$((fails+1)); }

for f in "${DOCS[@]}"; do
    rel="${f#$ROOT/}"
    for s in $MEASURED; do
        printf '%-62s ' "$rel names $s"
        grep -qF "$s" "$f" && echo ok || { echo "FAIL: not named in the rule"; fails=$((fails+1)); }
    done
done

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failures"; exit 1; }
