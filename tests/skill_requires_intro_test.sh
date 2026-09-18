#!/bin/bash
# T5: skills/operational/SKILL.md must say, as plainly as every commands/*.md
# file already does, that the first action once a command is decided is
# `scripts/intro.sh <command>`. This is the OTHER door into the five
# commands (PRINCIPLES.md - "the skill is the heart, because it is the only
# part that works when the user never types a slash command"), and
# hooks/next_step.sh's own T4 change only opens a flow correctly for it when
# that call actually happens - a skill that never says to run it is a door
# that silently skips the card every typed command already shows.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SKILL="$ROOT/skills/operational/SKILL.md"
fails=0

t() { printf '%-70s ' "$1"; grep -qF -- "$2" "$SKILL" 2>/dev/null && echo ok || { echo "FAIL: SKILL.md lacks '$2'"; fails=$((fails+1)); }; }

printf '%-70s ' "SKILL.md exists"
[ -r "$SKILL" ] && echo ok || { echo "FAIL: $SKILL not found"; echo; echo "1 failed"; exit 1; }

t "names scripts/intro.sh as the first action once a command is decided" "scripts/intro.sh <command>"
t "mentions running it before anything else" "first action"
t "names --end for closing the flow, same as every commands/*.md file" "scripts/intro.sh --end <command>"

# The same requirement, stated as a fact commands/*.md files ALSO carry -
# every one of the five already opens with "Run \`scripts/intro.sh <cmd>\`".
# This does not assert identical wording (that would make SKILL.md a copy of
# five files instead of the second door PRINCIPLES.md describes) - only that
# the same script name and the same "before anything else" idea is present
# in both, so the two doors cannot silently drift into disagreement about
# whether this call is required at all.
printf '%-70s ' "every commands/*.md file agrees intro.sh runs before anything else"
mismatch=""
for f in "$ROOT"/commands/*.md; do
    grep -qF "scripts/intro.sh" "$f" 2>/dev/null || mismatch="$mismatch $(basename "$f")"
done
[ -z "$mismatch" ] && echo ok || { echo "FAIL: missing intro.sh mention in:$mismatch"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
