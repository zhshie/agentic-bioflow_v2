#!/bin/bash
# Invariant 12 (docs/PRINCIPLES.md, section F): a request carrying action
# intent must reach the formal flow and see its walkthrough - not just get
# an answer. This does not re-test hooks/plugin_intro.sh's or
# hooks/confirm_walkthrough.sh's behaviour in depth - tests/plugin_intro_test.sh
# and tests/confirm_walkthrough_test.sh already do that - it asserts the
# three mechanisms that together enforce the invariant are still present, the
# same structural-check shape tests/principle_9_test.sh already uses for a
# different invariant. A refactor that quietly removed one of these would
# leave those other suites green (they test behaviour that still exists for
# what remains) while this goes red.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0
need() { # need <file> <pattern> <what it protects>
  printf '%-70s ' "$3"
  if grep -qE -- "$2" "$ROOT/$1"; then echo ok
  else echo "FAIL: $1 no longer contains /$2/"; fails=$((fails+1)); fi
}

# The natural-language door (T3): a topic AND an action both have to match
# before anything is routed - the function names themselves, not their
# regex bodies (which tests/plugin_intro_test.sh already exercises case by
# case), so this survives the vocabulary being edited.
need hooks/plugin_intro.sh 'has_topic\(\)' \
     "plugin_intro.sh still checks for a pipeline topic"
need hooks/plugin_intro.sh 'has_action\(\)' \
     "plugin_intro.sh still checks for an action verb"
need hooks/plugin_intro.sh 'IS_NL=1' \
     "the two conditions still combine into one routing decision"
need hooks/plugin_intro.sh 'operational' \
     "the routing hint still points at the operational skill"

# The skill's own first-action requirement (T5): the same script name every
# commands/*.md file already requires of a typed command.
need skills/operational/SKILL.md 'scripts/intro\.sh <command>' \
     "SKILL.md still names intro.sh as the first action"

# The walkthrough gate's own enforcement (G6, pre-existing but load-bearing
# for this invariant): denies the first gated action of a command whose
# opening card was never shown.
need hooks/confirm_walkthrough.sh 'G6=1' \
     "confirm_walkthrough.sh still has a gate for the opening card"
need hooks/confirm_walkthrough.sh 'scripts/intro\.sh \$\{G6_CMD\}' \
     "the G6 denial still names the exact command to run"

echo
[ "$fails" = 0 ] && echo "OK: invariant 12 is still enforced where it is written" \
  || { echo "$fails failed"; exit 1; }
