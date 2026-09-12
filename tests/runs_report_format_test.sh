#!/bin/bash
# U5: every status branch in commands/runs.md reports through the same four
# labelled lines - Status / Layer / (I will handle or You decide) / Next step
# - so a person reading a diagnosis always finds the same four questions
# answered in the same order, and "layer" is always one of the five values
# the site adapter diagnoses against (docs/SITE_ADAPTER.md, contract 5; the
# 2.7 plan's appendix fixes this exact shape and its English labels).
#
# Checked per branch, not once for the whole file: the shared "Reporting
# format" section only states the contract, it is not itself a branch a run
# can be in, and a section that dropped its own worked instance of the labels
# would still pass a whole-file check while failing the thing the format is
# for - someone reading just that one branch never sees the shared section at
# all.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
FILE="$ROOT/commands/runs.md"

BRANCHES="SUBMITTED RUNNING FAILED SUCCEEDED CANCELLED UNKNOWN"

# One branch's own text: from its "## NAME" heading up to (not including) the
# next top-level heading. awk rather than a fixed line range, because branch
# lengths here differ a great deal and a line count would silently start
# checking the wrong branch the moment any of them is edited.
section() {
    awk -v want="## $1" '
        $0 == want { grab=1; next }
        grab && /^## / { exit }
        grab { print }
    ' "$FILE"
}

fail=0
for b in $BRANCHES; do
    body="$(section "$b")"
    if [ -z "$body" ]; then
        echo "FAIL: commands/runs.md has no '## $b' branch"
        fail=1
        continue
    fi
    missing=""
    grep -q 'Status:'                       <<<"$body" || missing="$missing Status:"
    grep -q 'Layer:'                        <<<"$body" || missing="$missing Layer:"
    grep -qE 'I will handle:|You decide:'   <<<"$body" || missing="$missing I-will-handle:/You-decide:"
    grep -q 'Next step:'                    <<<"$body" || missing="$missing Next-step:"
    if [ -n "$missing" ]; then
        echo "FAIL: '## $b' is missing:$missing"
        fail=1
    else
        echo "ok: '## $b' carries all four labels"
    fi
done

if [ "$fail" = 1 ]; then
    echo
    echo "FAIL: not every branch in runs.md reports through the fixed four-line format."
    exit 1
fi
echo "OK: every branch in commands/runs.md (${BRANCHES// /, }) carries all four report labels"
