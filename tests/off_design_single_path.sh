#!/bin/bash
# Invariant 10 (2.8 plan, 四): a state nothing here was designed for gets
# handled by ONE procedure, not by each command file improvising its own
# "diagnose it fully". Two things prove that:
#
#   1. skills/operational/SKILL.md carries exactly one copy of the section
#      that spells the procedure out - not zero (nowhere to point to), not
#      two (which one is the real one).
#   2. No command file has an "Anything else"-style catch-all bullet left
#      that does not point straight at that section. The patterns matched
#      are the exact styles PITFALLS' read-through found (`**Anything
#      else.**`, `Diagnose it fully`) - not the bare words "anything else",
#      which also appear in ordinary prose here ("run --check before
#      anything else" in downstream.md) and would be a false positive.
#
# setup.md is owned by another agent in this wave and is read-only from
# here; if it ever trips this check the failure is reported, not patched -
# see the final report this test's runner writes.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SKILL="$ROOT/skills/operational/SKILL.md"
HEADING='## Off-design: when nothing here covers it'
fails=0

printf '%-70s ' "SKILL.md exists"
[ -r "$SKILL" ] && echo ok || { echo "FAIL: $SKILL not found"; echo; echo "0 passed, 1 failed"; exit 1; }

count=$(grep -Fxc "$HEADING" "$SKILL")
printf '%-70s ' "SKILL.md carries the off-design heading exactly once"
[ "$count" = 1 ] && echo ok || { echo "FAIL: found $count occurrences"; fails=$((fails+1)); }

# Every blank-line-delimited block in a command file that contains one of the
# catch-all phrases must also mention the off-design section within the same
# block - awk's paragraph mode (RS='') is the portable way to group text this
# way without a GNU-only flag (tests/portable_userland.sh forbids those).
check_file() {
    local f="$1" name bad
    name=$(basename "$f")
    bad=$(awk -v RS='' '
        /\*\*Anything else\.|Diagnose it fully/ {
            if ($0 !~ /skills\/operational\/SKILL\.md/ && $0 !~ /Off-design: when nothing here covers it/) {
                print "----- offending block -----"
                print $0
            }
        }
    ' "$f")
    printf '%-70s ' "$name: no catch-all without a pointer to the off-design section"
    if [ -z "$bad" ]; then
        echo ok
        return 0
    fi
    if [ "$name" = "setup.md" ]; then
        echo "FAIL (setup.md - owned by another agent, noted below, not edited here)"
        printf '%s\n' "$bad"
        return 0
    fi
    echo "FAIL"
    printf '%s\n' "$bad"
    return 1
}

for f in "$ROOT"/commands/*.md; do
    check_file "$f" || fails=$((fails+1))
done

# Positive control: runs.md's FAILED branch is exactly the case this file
# exists to police (it used to read "Anything else. Diagnose it fully."),
# so it must still point at the off-design section by path - the main loop
# above would silently pass on an empty commands/ directory too.
printf '%-70s ' "commands/runs.md's catch-all points at skills/operational/SKILL.md"
grep -qF "skills/operational/SKILL.md" "$ROOT/commands/runs.md" && echo ok || { echo "FAIL"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
