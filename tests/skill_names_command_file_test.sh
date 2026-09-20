#!/bin/bash
# The skill has to name the command file, not just allude to it.
#
# Typing `/launch` makes the runtime put commands/launch.md in front of the
# model; arriving through this skill does not. Until 2.16 the skill said only
# "Read the command file and follow it" - no path, no requirement to read it
# before acting - so the natural-language door could walk the whole flow on
# the skill's one-line summary of it. The 2.15.0 Windows verification is what
# this is measured against: that walk looked up `tw launch --help` and asked
# its decisions one at a time, both already settled in commands/launch.md.
#
# Checks the shape, not the prose: a path spelling that resolves, the "before
# anything else" requirement, and that the five names the table routes to are
# really files - so a renamed command file cannot leave the skill pointing at
# nothing.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SKILL="$ROOT/skills/operational/SKILL.md"
fails=0
t() { printf '%-70s ' "$1"; grep -qF -- "$2" "$SKILL" 2>/dev/null && echo ok || { echo "FAIL: SKILL.md lacks '$2'"; fails=$((fails+1)); }; }

printf '%-70s ' "SKILL.md exists"
[ -r "$SKILL" ] && echo ok || { echo "FAIL: $SKILL not found"; echo; echo "1 failed"; exit 1; }

t "names the command file by path, not just 'the command file'" 'commands/<command>.md'
t "gives the installed-plugin spelling of that path" '${CLAUDE_PLUGIN_ROOT}/commands/<command>.md'
t "requires reading it before acting" 'in full before doing anything else'
t "says why: a typed slash command gets the file, this door does not" '/launch'

# The table routes to five names; each has to be a real file, or the
# instruction above points at nothing.
printf '%-70s ' "every command the skill routes to has a file to read"
missing=""
for c in setup launch runs downstream finish; do
    [ -r "$ROOT/commands/$c.md" ] || missing="$missing $c"
done
[ -z "$missing" ] && echo ok || { echo "FAIL: no command file for:$missing"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
