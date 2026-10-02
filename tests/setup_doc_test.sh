#!/bin/bash
# Feature 004 (specs/004-onboarding-proof), TC-012..TC-014: commands/setup.md
# is the instruction the model follows, so the new routing has to be IN it:
#   TC-012  T27 paragraph: setup_verify.sh exit 3 -> straight to step 8, then
#           steps 9 and 10, without redoing steps 1-7
#   TC-013  Repair: before finishing, run setup_proof.sh --check; no record ->
#           step 8, then step 9
#   TC-014  step 8 ends with setup_proof.sh --record <run-id>; step 9 only
#           after that succeeded
# Each section is cut out of the file and flattened to one line first, so a
# phrase is only credited if it sits in the section it belongs to (a mention in
# some other part of the file does not satisfy it).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/commands/setup.md"
fails=0

# section <start-regex> <stop-regex>: the lines from the first start match up
# to (not including) the next stop match, joined into one line.
section() {
    S_RE="$1" E_RE="$2" awk '
        BEGIN { s = ENVIRON["S_RE"]; e = ENVIRON["E_RE"] }
        !on && $0 ~ s { on = 1; print; next }
        on && $0 ~ e  { exit }
        on            { print }' "$DOC" | tr '\n' ' ' | sed 's/  */ /g'
}
# ok <label> <section-text> <ERE>
ok() {
    printf '%-72s ' "$1"
    if [ -z "$2" ]; then echo "FAIL: section not found in commands/setup.md"; fails=$((fails+1)); return; fi
    if grep -qE -- "$3" <<<"$2"; then echo ok; else echo "FAIL: no match for /$3/"; fails=$((fails+1)); fi
}

T27=$(section '^\*\*T27: run' '^Read the deployment settings')
REPAIR=$(section '^## Repair' '^## ')
S8=$(section '^\*\*8\. Prove it' '^\*\*9\. ')
S9=$(section '^\*\*9\. Only now' '^\*\*10\. ')

# TC-012
ok "TC-012 T27: exit 3 is named"  "$T27"  'Exit 3'
ok "TC-012 T27: exit 3 sends to step 8, then steps 9 and 10"  "$T27"  'Exit 3[^.]*step 8[^.]*steps? 9 and 10'
ok "TC-012 T27: steps 1-7 are not redone"  "$T27"  '(not|never|without)[^.]*(redo|repeat|re-run)[^.]*steps 1.{1,3}7'

# TC-013
ok "TC-013 Repair: runs setup_proof.sh --check"  "$REPAIR"  'setup_proof\.sh --check'
ok "TC-013 Repair: no record -> step 8 then step 9"  "$REPAIR"  'setup_proof\.sh --check[^.]*\.[^.]*step 8[^.]*step 9'

# TC-014
ok "TC-014 step 8: ends by recording the run with --record <run-id>"  "$S8"  'setup_proof\.sh --record <run-id>'
ok "TC-014 step 9: only after --record succeeded"  "$S9"  '[Oo]nly[^.]*setup_proof\.sh --record[^.]*succe'

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
