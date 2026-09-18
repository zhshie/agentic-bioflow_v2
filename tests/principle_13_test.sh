#!/bin/bash
# Invariant 13 (docs/PRINCIPLES.md, section F): when the safety net cannot do
# its job, it must say so - never quietly do nothing (PITFALLS 28's original
# failure), and never refuse everything either (issue #15's failure, fixed by
# T1's scoped fail-closed). This does not re-test the no-jq behaviour in
# depth - tests/confirm_launch_test.sh, tests/confirm_cleanup_test.sh,
# tests/confirm_walkthrough_test.sh and tests/plugin_intro_test.sh already do
# that case by case - it asserts the mechanism is still present in every file
# that needs it, the same structural-check shape tests/principle_9_test.sh
# and tests/principle_12_test.sh already use.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0
need() { # need <file> <pattern> <what it protects>
  printf '%-70s ' "$3"
  if grep -qE -- "$2" "$ROOT/$1"; then echo ok
  else echo "FAIL: $1 no longer contains /$2/"; fails=$((fails+1)); fi
}

# The three safety-net gates: each still probes jq by actually running it
# (not `command -v jq`, which only proves a file exists - PITFALLS 28's own
# lesson), still refuses (exit 2) rather than silently continuing, and still
# names the fix for every platform this deployment runs on.
for f in hooks/confirm_launch.sh hooks/confirm_cleanup.sh hooks/confirm_walkthrough.sh; do
    need "$f" "jq -e \." \
         "$f still probes jq by running it, not just looking for it"
    need "$f" 'exit 2' \
         "$f still refuses rather than continuing silently"
    need "$f" 'winget install jqlang\.jq' \
         "$f still names the Windows install fix"
done

# T1: the refusal is scoped, not blanket - each gate can tell "nothing here
# looks risky" from "this looks risky", even without jq.
need hooks/confirm_launch.sh      'looks_launch_shaped' \
     "confirm_launch.sh still scopes its no-jq refusal instead of blocking everything"
need hooks/confirm_cleanup.sh     'looks_delete_shaped' \
     "confirm_cleanup.sh still scopes its no-jq refusal instead of blocking everything"
need hooks/confirm_walkthrough.sh 'looks_managed_write_shaped' \
     "confirm_walkthrough.sh still scopes its no-jq refusal instead of blocking everything"

# T3: the one hook that is NOT a gate speaks up instead of going silent when
# jq is missing - the exact hole issue #15 fell into with nothing to notice.
need hooks/plugin_intro.sh 'jq is missing or cannot run here' \
     "plugin_intro.sh still warns when jq is missing, instead of going silent"
need hooks/plugin_intro.sh 'systemMessage' \
     "plugin_intro.sh's jq warning still reaches the user, not just the model"

echo
[ "$fails" = 0 ] && echo "OK: invariant 13 is still enforced where it is written" \
  || { echo "$fails failed"; exit 1; }
