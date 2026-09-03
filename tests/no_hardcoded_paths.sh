#!/bin/bash
# Invariant 3: anyone can install this.
#
# A path like /home/alice/bin/tool.jar or /work/alice/runs is one person's
# machine baked into a file everyone shares. It is not merely untidy: on a
# typical cluster a home directory is mode 700, so the second member cannot
# read it at all, and the failure arrives as "missing or unreadable" rather
# than as "this was never yours to read".
#
# Locations must come from a deployment variable instead - $LAB_RUNS_DIR and
# the deployment's own settings file.
#
# docs/ is deliberately not scanned: PITFALLS quotes real paths as evidence of
# real failures, and that is what makes those entries checkable.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# A per-user root followed by an owned subtree. Deliberately NOT filtered by
# "does this line mention a variable": the worst form of this is
#
#   JAVA="${TW_AGENT_JAVA:-/home/alice/bin/java}"
#
# which looks configurable and is not, because the default is one person's
# machine. A line-level exemption for $VAR would step straight past it.
# Nothing written correctly can match: $LAB_RUNS_DIR/_relay and ~/bin do not
# begin with one of these roots.
PATTERN='(/home|/work|/scratch|/staging|/lustre)/[A-Za-z][A-Za-z0-9_.-]*/'

hits=0
while IFS= read -r line; do
    printf '%s\n' "$line"
    hits=$((hits + 1))
done < <(
    grep -rInE "$PATTERN" "$ROOT/scripts" "$ROOT/commands" "$ROOT/configs" 2>/dev/null \
      | sed "s|^$ROOT/||"
)

if [ "$hits" -gt 0 ]; then
    echo
    echo "FAIL: $hits hardcoded path(s). Read these from the deployment settings instead."
    exit 1
fi
echo "OK: no hardcoded personal or cluster paths in scripts/, commands/, configs/"
