#!/bin/bash
# A command that names `scripts/preflight.sh` has told the agent to run a path
# that does not exist. Installed as a plugin there is no checkout, and the cwd
# is wherever the user happened to be - which for `setup` is guaranteed to be
# arbitrary, because its own first step is choosing where work will live.
#
# The fix is not to rewrite every path: read straight from a repository is a
# supported way to use this, and `${CLAUDE_PLUGIN_ROOT}` is empty there. It is
# to say once, per file, which root the paths are relative to - the wording
# skills/operational/SKILL.md already uses.
#
# So: any command file naming a bare scripts/ or docs/ path must also say where
# that root is. Crude, and it catches the case that actually happens.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

. "$HERE/lib/flow_skills.sh"
fail=0
read_n=0
for f in $(flow_skill_files); do
    rel="${f#"$ROOT"/}"
    [ -r "$f" ] && read_n=$((read_n+1))
    grep -qE '(^|[^A-Za-z0-9_/.-])(scripts|docs|configs)/[A-Za-z0-9_./-]+' "$f" || continue
    if ! grep -q 'CLAUDE_PLUGIN_ROOT' "$f"; then
        echo "$rel: names its own files but never says which root they are under"
        fail=1
    fi
done

if [ "$read_n" -ne 5 ]; then
    echo "FAIL: read $read_n flow skill files, expected 5 - nothing was really checked."
    exit 1
fi
if [ "$fail" = 1 ]; then
    echo
    echo "FAIL: a plugin user has no checkout - these paths resolve to nothing."
    exit 1
fi
echo "OK: every command naming scripts/ or docs/ says where that root is"
