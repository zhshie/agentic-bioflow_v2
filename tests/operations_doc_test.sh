#!/bin/bash
# docs/OPERATIONS.md (issue #119 item 4, specs/ops-doc): the operator's manual has its six
# sections, names only abf-platform subcommands that exist, and only repo files that exist.
# Document checks only. Test cases: specs/ops-doc/test-case.md (TC ids in the labels).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT" || exit 1
fails=0
DOC=docs/OPERATIONS.md
CLI=platform/abf_platform/cli.py

ok() { printf '%-86s ok\n' "$1"; }
bad() { printf '%-86s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }

if [ -f "$DOC" ]; then ok "TC-001 $DOC exists"; else bad "TC-001 $DOC exists" "file not found"; fi
doc=$(tr -d '\r' < "$DOC" 2>/dev/null)

# TC-001/TC-020: six second-level headings, in order, the last one 'Not built yet'
mapfile -t heads < <(printf '%s\n' "$doc" | grep -E '^## ')
if [ "${#heads[@]}" -eq 6 ]; then ok "TC-001 six '## ' headings"; else bad "TC-001 six '## ' headings" "found ${#heads[@]}"; fi
for i in 1 2 3 4 5 6; do
  case $i in
    1) pat='[Pp]rocess' ;; 2) pat='[Hh]ost|TLS' ;; 3) pat='[Rr]unning' ;;
    4) pat='[Bb]ack' ;; 5) pat='[Aa]dmin' ;; 6) pat='Not built yet' ;;
  esac
  if printf '%s\n' "${heads[$((i-1))]:-}" | grep -qE -- "$pat"; then ok "TC-001/020 heading $i matches /$pat/"; else bad "TC-001/020 heading $i matches /$pat/" "got '${heads[$((i-1))]:-}'"; fi
done

# TC-021/TC-022: every `abf-platform <word>` names a real top-level subcommand of cli.py
subs=$(grep -oE 'sub\.add_parser\("[a-z-]+"' "$CLI" | sed -E 's/.*\("//; s/"$//')
n=0
while IFS= read -r w; do
  [ -z "$w" ] && continue
  n=$((n+1))
  if printf '%s\n' "$subs" | grep -qx -- "$w"; then ok "TC-021 abf-platform $w exists"; else bad "TC-021 abf-platform $w exists" "no such subcommand in $CLI"; fi
done < <(printf '%s\n' "$doc" | grep -oE 'abf-platform +[a-z][a-z-]*' | awk '{print $2}' | sort -u)
[ "$n" -gt 0 ] || bad "TC-022 doc names at least one abf-platform subcommand"

# TC-023/TC-024: backticked repo paths (top-level repo dir, has an extension) exist
m=0
while IFS= read -r p; do
  [ -z "$p" ] && continue
  m=$((m+1))
  if [ -e "$p" ]; then ok "TC-023 path $p exists"; else bad "TC-023 path $p exists" "not in the repo"; fi
done < <(printf '%s\n' "$doc" | grep -oE '`(docs|platform|tests|scripts|skills|hooks|specs|configs|extensions)/[^` ]*\.[A-Za-z0-9]+`' | tr -d '`' | sort -u)
[ "$m" -gt 0 ] || bad "TC-024 doc names at least one repo file"

[ "$fails" -eq 0 ]
