#!/bin/bash
# The four parallel-worktree pitfalls (46-49) must stay in docs/PITFALLS.md.
# One keyword per pitfall, so deleting one is never hidden by the others.
F="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docs/PITFALLS.md"
fails=0
check() {  # $1 = TC id, $2 = keyword
  if grep -qF -- "$2" "$F"; then printf '%-8s %-24s ok\n' "$1" "$2"
  else printf '%-8s %-24s FAIL: missing from docs/PITFALLS.md\n' "$1" "$2"; fails=$((fails+1)); fi
}
check TC-001 '--relative-paths'
check TC-002 'auto mode classifier'
check TC-003 'UNVERIFIED'
check TC-004 'maxParallel'
[ "$fails" -eq 0 ]
