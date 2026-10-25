#!/bin/bash
# Guard (pipefail-grep-q-sweep, follows #231): a test script that has `set -o pipefail`
# must not feed a pipe into `grep -q`. grep -q quits at its first match; the command
# in front of it (printf, cat) is still writing, gets "Broken pipe", and pipefail then
# marks the whole pipeline failed - so text that IS there is reported as missing, now
# and then. #231 proved this was the cause of constitution_scope_test flaking (24000
# runs: 10 false failures with the old form, 0 with the fix). The fix is to drop the q
# and send grep's output to /dev/null so grep reads everything. grep -q on a file
# (no pipe) is fine and not flagged.
# TC-003..TC-018 of specs/pipefail-grep-q-sweep.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF="$(basename "${BASH_SOURCE[0]}")"
fails=0
ok() { printf '%-70s ok\n' "$1"; }
bad() { printf '%-70s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }

# a single `|` (not `||`), then grep, optional separate flag groups, then a flag group containing q
PAT='(^|[^|])\|[[:space:]]*grep([[:space:]]+-[A-Za-z]+)*[[:space:]]+-[A-Za-z]*q'

# violates <file>: true when the file has pipefail and a pipe into grep -q (comment lines ignored)
violates() {
  grep -q 'pipefail' "$1" || return 1
  grep -v '^[[:space:]]*#' "$1" | grep -E "$PAT" >/dev/null
}
# scan <dir>: print each violating file name, return 1 if any
scan() {
  local f rc=0
  for f in "$1"/*.sh; do
    [ "$(basename "$f")" = "$SELF" ] && continue
    violates "$f" && { echo "$f"; rc=1; }
  done
  return $rc
}

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
# case_ <name> <expect: bad|clean> <content...>
case_() {
  local name="$1" want="$2" body="$3" f="$T/c.sh" got
  printf '%s\n' "$body" > "$f"
  if violates "$f"; then got=bad; else got=clean; fi
  if [ "$got" = "$want" ]; then ok "$name"; else bad "$name" "wanted $want, got $got"; fi
}
P='set -o pipefail'
case_ "TC-004 grep -q"       bad   "$P
printf x | grep -q x"
case_ "TC-005 grep -qF"      bad   "$P
printf x | grep -qF x"
case_ "TC-006 grep -iq"      bad   "$P
printf x | grep -iq x"
case_ "TC-007 grep -F -q"    bad   "$P
printf x | grep -F -q x"
case_ "TC-008 grep -E -q"    bad   "$P
printf x | grep -E -q x"
case_ "TC-009 grep -vqE"     bad   "$P
printf x | grep -vqE x"
case_ "TC-010 grep -qvx"     bad   "$P
printf x | grep -oE x | grep -qvx y"
case_ "TC-011 continuation line" bad "$P
printf x \
  | grep -qE \"x\""
case_ "TC-012 clean form"    clean "$P
printf x | grep -F x >/dev/null"
case_ "TC-013 no pipefail"   clean "printf x | grep -q x"
case_ "TC-014 file, no pipe" clean "$P
grep -q x \"\$FILE\""
case_ "TC-015 || is not a pipe" clean "$P
[ \"\$a\" = \"-\" ] || grep -qE x \"\$f\""
case_ "TC-016 q after &&"    clean "$P
a | grep 'FAIL' >/dev/null && grep -qE x \"\$f\""

# TC-018: a directory with one bad and one clean file names only the bad one
mkdir "$T/d"
printf '%s\nprintf x | grep -q x\n' "$P" > "$T/d/bad.sh"
printf '%s\nprintf x | grep x >/dev/null\n' "$P" > "$T/d/good.sh"
out="$(scan "$T/d")"; rc=$?
if [ "$rc" -ne 0 ] && [[ "$out" == *bad.sh* ]] && [[ "$out" != *good.sh* ]]; then ok "TC-018 names only the offender"; else bad "TC-018 names only the offender" "rc=$rc out=$out"; fi

# TC-003 / TC-017: the real tests/ tree (this file is skipped)
out="$(scan "$HERE")"; rc=$?
if [ "$rc" -eq 0 ]; then ok "TC-003 tests/*.sh has no pipefail + pipe into grep -q"; else bad "TC-003 tests/*.sh has no pipefail + pipe into grep -q" "$(echo "$out" | tr '\n' ' ')"; fi

[ "$fails" -eq 0 ] && { echo "no_pipefail_grep_q_test: all passed"; exit 0; }
echo "no_pipefail_grep_q_test: $fails failed" >&2; exit 1
