#!/bin/bash
# Docs check for the nano4 acceptance (task acceptance-nano4): TC-001, TC-012, TC-013, TC-022..024.
# Usage: docs_nano4_acceptance.sh [TESTING.md [acceptance-nano4.md]]  (defaults: the repo's own files)
# With file arguments it checks those copies instead (used by the self-test below).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="${1:-$ROOT/docs/TESTING.md}"
A="${2:-$ROOT/specs/007b-launch/acceptance-nano4.md}"

check() {   # check <testing> <table> ; prints FAIL lines, returns 1 on any
  local t="$1" a="$2" bad=0
  # TC-001: one section "nano4 acceptance" holding the five IDs
  local n; n=$(grep -c '^#.*nano4 acceptance' "$t" 2>/dev/null)
  [ "$n" = "1" ] || { echo "FAIL TC-001: want exactly one heading with 'nano4 acceptance' in $t, found ${n:-0}"; bad=1; }
  local sec; sec=$(awk '/^#.*nano4 acceptance/{f=1;next} f&&/^#+ /{f=0} f' "$t" 2>/dev/null)
  local i; for i in 047n 048n 049n 050n 051n; do
    printf '%s\n' "$sec" | grep -q "TC-$i" || { echo "FAIL TC-001: TC-$i missing from the nano4 acceptance section"; bad=1; }
  done
  for i in 047 048 049 050 052 053; do
    grep -q "TC-$i[^n0-9]" "$t" 2>/dev/null || { echo "FAIL TC-001: original TC-$i gone from $t"; bad=1; }
  done
  # TC-012: required strings in the table
  if [ ! -f "$a" ]; then echo "FAIL TC-012: $a does not exist"; return 1; fi
  local s; for s in wallet squeue X-ABF-Platform; do
    grep -q -- "$s" "$a" || { echo "FAIL TC-012: '$s' missing from acceptance table"; bad=1; }
  done
  # TC-013: required columns
  for s in '日期' '走哪條路' 'launch 前預估 SU' 'preflight' 'head.sh' 'trace 行數' 'grep -c token' 'wallet 前' 'wallet 後' '差額' '截圖檔名' '備註'; do
    grep -q -- "$s" "$a" || { echo "FAIL TC-013: column '$s' missing from acceptance table"; bad=1; }
  done
  return $bad
}

if [ -n "$SELFTEST_INNER" ]; then check "$T" "$A"; exit $?; fi

check "$T" "$A"; rc=$?

# TC-023/024 self-test: damaged copies must go red (only when checking the real files)
if [ -z "$1" ] && [ "$rc" -eq 0 ]; then
  tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
  expect_red() {   # expect_red <label> <testing> <table>
    if SELFTEST_INNER=1 bash "${BASH_SOURCE[0]}" "$2" "$3" >/dev/null 2>&1; then echo "FAIL TC-023/024: damaged copy ($1) still passes"; rc=1; fi
  }
  sed 's/TC-049n/TC-049x/g' "$T" > "$tmp/t1.md"; expect_red "no TC-049n" "$tmp/t1.md" "$A"
  sed 's/nano4 acceptance/nano4 other/g' "$T" > "$tmp/t2.md"; expect_red "no section" "$tmp/t2.md" "$A"
  for s in wallet squeue X-ABF-Platform '走哪條路' '差額'; do
    sed "s/$s/XXX/g" "$A" > "$tmp/a.md"; expect_red "table without $s" "$T" "$tmp/a.md"
  done
fi
[ "$rc" -eq 0 ] && echo "ok"
exit "$rc"
