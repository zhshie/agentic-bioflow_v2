#!/bin/bash
# The constitution's own promise, checked: "each keeps its original invariant
# number and names the check that holds it: a principle with no check is a
# slogan" (constitution, preamble).
#
# That promise was kept in form and not in fact. Principles 2, 5, 7 and 8 and
# the Safety Net's credentials rule carried either no "Check:" or a sentence
# describing a check nobody had written (audit 2026-09-29, issue #30; bug:
# constitution-checks). A sentence is not a check. So for each of the thirteen
# numbered principles and the credentials rule, the text of its bullet must
#
#   1. contain a "*Check:*" marker, and
#   2. cite at least one thing that can be run or followed:
#        - a file under tests/ (which must exist), or
#        - a "Procedure P<n>" in docs/TESTING.md (whose heading must exist), and
#   3. every tests/ file and every Procedure it cites must exist.
#
# CONSTITUTION_FILE and TESTING_FILE point the check at a scratch copy, which is
# how the self-tests at the bottom prove the rule can go red.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
CONST="${CONSTITUTION_FILE:-$ROOT/.specify/memory/constitution.md}"
TESTING="${TESTING_FILE:-$ROOT/docs/TESTING.md}"

[ -r "$CONST" ] || { echo "FAIL: cannot read $CONST"; exit 1; }
[ -r "$TESTING" ] || { echo "FAIL: cannot read $TESTING"; exit 1; }

# Split the constitution into one record per rule: a numbered principle bullet
# ("- **N.**") or the credentials bullet. A record ends at the next bullet or
# the first blank line.
records=$(awk '
    function flush() { if (name != "") { gsub(/\n/, " ", body); print name "\t" body } name = ""; body = "" }
    /^- \*\*[0-9]+\.\*\*/ { flush(); match($0, /[0-9]+/); name = "invariant " substr($0, RSTART, RLENGTH); body = $0; next }
    /^- Credentials and personal details live only/ { flush(); name = "safety-net credentials rule"; body = $0; next }
    /^- / { flush(); next }
    /^[[:space:]]*$/ { flush(); next }
    /^#/ { flush(); next }
    name != "" { body = body "\n" $0 }
    END { flush() }
' "$CONST")

fails=0
count=0
while IFS=$'\t' read -r name body; do
    [ -n "$name" ] || continue
    count=$((count + 1))
    if ! grep -qF '*Check:*' <<<"$body"; then
        echo "NO CHECK  $name has no '*Check:*' marker"
        fails=$((fails + 1)); continue
    fi
    cited=0
    # tests/<file> citations
    for tf in $(grep -oE 'tests/[A-Za-z0-9_./-]+[.](sh|py)' <<<"$body" | sort -u); do
        cited=$((cited + 1))
        [ -e "$ROOT/$tf" ] || { echo "DANGLING $name cites $tf, which does not exist"; fails=$((fails + 1)); }
    done
    # Procedure P<n> citations
    for pn in $(grep -oE 'Procedure P[0-9]+' <<<"$body" | sort -u | sed 's/Procedure //'); do
        cited=$((cited + 1))
        grep -qE "^#+ +Procedure $pn([^0-9]|$)" "$TESTING" \
            || { echo "DANGLING $name cites Procedure $pn, which docs/TESTING.md has no heading for"; fails=$((fails + 1)); }
    done
    if [ "$cited" -eq 0 ]; then
        echo "SENTENCE  $name: its Check cites no tests/ file and no 'Procedure P<n>' - a description is not a check"
        fails=$((fails + 1))
    fi
done <<<"$records"

# Fourteen rules: 13 numbered + the credentials rule. A parser that quietly
# found none would pass everything.
if [ "$count" -lt 14 ] && [ -z "${CONSTITUTION_FILE:-}" ]; then
    echo "FAIL: found only $count rules in the constitution, expected 14 (13 principles + credentials)"
    exit 1
fi

if [ "$fails" -gt 0 ]; then
    echo
    echo "FAIL: $fails problem(s) across $count rules"
    exit 1
fi

# ---------------------------------------------------------------------------
# Self-tests: the rule must go red on the shapes it exists for.
if [ -z "${CONSTITUTION_FILE:-}" ]; then
    S=$(mktemp -d); trap 'rm -rf "$S"' EXIT
    selffails=0
    printf '### Procedure P7: x\n' > "$S/testing.md"
    run() { CONSTITUTION_FILE="$S/c.md" TESTING_FILE="$S/testing.md" bash "${BASH_SOURCE[0]}" >/dev/null 2>&1; }
    expect() { run; rc=$?; [ "$rc" = "$1" ] || { echo "SELFTEST FAIL: $2 (rc $rc, wanted $1)"; selffails=$((selffails + 1)); }; }

    printf -- '- **1.** a rule. *Check:* `tests/constitution_checks_exist_test.sh`.\n' > "$S/c.md"
    expect 0 "a rule citing an existing test passes"
    printf -- '- **1.** a rule. *Check:* the system still works.\n' > "$S/c.md"
    expect 1 "a Check that is only a sentence fails"
    printf -- '- **1.** a rule with no marker at all.\n' > "$S/c.md"
    expect 1 "a rule with no Check fails"
    printf -- '- **1.** a rule. *Check:* `tests/does_not_exist.sh`.\n' > "$S/c.md"
    expect 1 "a Check citing a missing test fails"
    printf -- '- **1.** a rule. *Check:* Procedure P7 in docs/TESTING.md.\n' > "$S/c.md"
    expect 0 "a Check citing an existing Procedure passes"
    printf -- '- **1.** a rule. *Check:* Procedure P9 in docs/TESTING.md.\n' > "$S/c.md"
    expect 1 "a Check citing a missing Procedure fails"
    [ "$selffails" -gt 0 ] && { echo "FAIL: $selffails self-test(s) failed"; exit 1; }
fi

echo "OK: all $count rules (13 principles + the credentials rule) name a Check that exists"
