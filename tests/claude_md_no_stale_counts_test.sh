#!/bin/bash
# Root CLAUDE.md must not carry numbers that go stale the day a test file or a
# branch is added: a test count ("all 73"), a "<n> tests" total, or a CI
# trigger that names only `main`. The command's own output (run_all.sh prints
# "N/M passed") and .github/workflows/tests.yml are the source of those facts.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
CM="$ROOT/CLAUDE.md"
fails=0

lacks() {
  printf '%-60s ' "$1"
  if [ ! -r "$CM" ]; then echo "FAIL: CLAUDE.md missing"; fails=$((fails+1)); return; fi
  local hit
  hit=$(grep -nE -- "$2" "$CM" | head -3)
  if [ -z "$hit" ]; then echo ok; else echo "FAIL: CLAUDE.md matches '$2': $hit"; fails=$((fails+1)); fi
}

lacks "CLAUDE.md has no 'all <number>'"                 'all [0-9]+'
lacks "CLAUDE.md has no '<number> tests'"               '[0-9]+ tests'
lacks "CLAUDE.md CI trigger does not name only main"    'every push to `main`'

[ "$fails" = 0 ] && echo "OK: CLAUDE.md carries no stale counts" || { echo "$fails failure(s)"; exit 1; }
