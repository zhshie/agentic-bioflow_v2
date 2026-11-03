#!/bin/bash
# docs/PITFALLS.md: every entry ends with Symptom / Root cause / Check / Touches; PLATFORM.md tier wording.
# Plan: specs/pitfalls-frontmatter/plan.md. Test cases: specs/pitfalls-frontmatter/test-case.md (TC ids in labels).
# Text checks only; no network, no ssh.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
fails=0
ok()  { printf '%-78s ok\n' "$1"; }
bad() { printf '%-78s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }
hasf() { # label file fixed-string
  local txt; txt=$(tr -d '\r' < "$2")
  if grep -qF -- "$3" <<<"$txt"; then ok "$1"; else bad "$1" "no '$3' in $2"; fi
}
P=docs/PITFALLS.md; L=docs/PLATFORM.md

# TC-001 header section
txt=$(tr -d '\r' < "$P")
h=$(grep -n '^## How an entry is written$' <<<"$txt" | head -1 | cut -d: -f1)
s=$(grep -n '^## Setting up the agent$' <<<"$txt" | head -1 | cut -d: -f1)
if [ -z "$h" ]; then bad "TC-001 header present" "no '## How an entry is written'"
elif [ -z "$s" ] || [ "$h" -ge "$s" ]; then bad "TC-001 header present" "header not before '## Setting up the agent'"
else
  sec=$(sed -n "$((h+1)),$((s-1))p" <<<"$txt")
  miss=""; for t in 'Symptom:' 'Root cause:' 'Check:' 'Touches:'; do grep -qF "$t" <<<"$sec" || miss="$miss $t"; done
  for g in "grep -n '^Touches:.*prepare_launch' docs/PITFALLS.md" "grep -n '^Check: none automated' docs/PITFALLS.md"; do
    grep -qF "$g" <<<"$sec" || miss="$miss [$g]"; done
  if [ -n "$miss" ]; then bad "TC-001 header present" "missing:$miss"; else ok "TC-001 header present"; fi
fi

# Parse entries. Heading = ^**<n>. or ^**<n>.** ; entry ends at next heading, '## ' or EOF.
parsed=$(tr -d '\r' < "$P" | awk '
function flush(   i,lbl,n,k,items,j,it,c,t,sp) {
  if (id == "") return
  split("Symptom|Root cause|Check|Touches", lbl, "|")
  for (i = 1; i <= 4; i++) {
    n = cnt[i] + 0
    if (n != 1) printf "ERR\t%s\t%s: count=%d (want 1)\n", id, lbl[i], n
    else if (txt[i] ~ /^[ \t]*$/) printf "ERR\t%s\t%s: empty\n", id, lbl[i]
  }
  if (cnt[1]==1 && cnt[2]==1 && cnt[3]==1 && cnt[4]==1) {
    if (!(ln[1] < ln[2] && ln[2] < ln[3] && ln[3] < ln[4])) printf "ERR\t%s\tfields out of order\n", id
    else if (ln[4]-ln[1] != 3) printf "ERR\t%s\tfour lines not consecutive\n", id
    if (ln[4] != last) printf "ERR\t%s\tfields not at entry end\n", id
  }
  if (cnt[3]==1) {
    c = txt[3]
    if (c !~ /^none automated:/ && c !~ /`[^`]+`/) printf "ERR\t%s\tCheck has neither backticks nor none automated:\n", id
    t = c
    while (match(t, /`[^`]+`/)) {
      sp = substr(t, RSTART+1, RLENGTH-2); t = substr(t, RSTART+RLENGTH)
      if (sp ~ /^(tests\/|platform\/tests\/|scripts\/)/) { sub(/[ \t:].*$/, "", sp); printf "PATH\t%s\t%s\n", id, sp }
    }
  }
  if (cnt[4]==1) {
    k = split(txt[4], items, /, */)
    for (j = 1; j <= k; j++) {
      it = items[j]; gsub(/^[ \t]+|[ \t]+$/, "", it)
      if (it == "") { printf "ERR\t%s\tTouches has empty item\n", id; continue }
      if (index(body_all, it) == 0) printf "ERR\t%s\tTouches item not in entry text: %s\n", id, it
    }
  }
  if ((txt[1] txt[2] txt[3] txt[4]) ~ /abf_pat_|mst1[0-9][0-9][0-9][0-9][0-9]|u9[0-9][0-9][0-9][0-9][0-9][0-9][0-9]/) printf "SECRET\t%s\tsecret-like text in fields\n", id
  printf "ENTRY\t%s\n", id
  id = ""
}
{
  if ($0 ~ /^\*\*[0-9]+[a-z0-9]*\.( |\*\*)/) {
    flush(); match($0, /^\*\*[0-9]+[a-z0-9]*\./); id = substr($0, 3, RLENGTH-3)
    delete cnt; delete txt; delete ln; body_all = $0; last = 0; nr = 0; next
  }
  if ($0 ~ /^## /) { flush(); next }
  if (id == "") next
  nr++
  if ($0 ~ /[^ \t]/) last = nr
  i = 0
  if ($0 ~ /^Symptom: /) i = 1; else if ($0 ~ /^Root cause: /) i = 2; else if ($0 ~ /^Check: /) i = 3; else if ($0 ~ /^Touches: /) i = 4
  if (i > 0) { cnt[i]++; ln[i] = nr; txt[i] = $0; sub(/^[A-Za-z ]+: /, "", txt[i]) }
  else body_all = body_all "\n" $0
}
END { flush() }
')
n_entries=$(grep -c '^ENTRY' <<<"$parsed")
errs=$(grep '^ERR' <<<"$parsed")

# TC-002 / TC-008 four fields, each exactly once, in order, at the end; failure names the entry and the field
e2=$(grep -v 'Touches item' <<<"$errs" | grep -v 'Check has neither')
if [ -z "$e2" ]; then ok "TC-002 every entry has the four fields"
else bad "TC-002 every entry has the four fields" "$(wc -l <<<"$e2") problems"; cut -f2- <<<"$e2" | tr '\t' ' ' | sed 's/^/    entry /' | head -n 40; fi

# TC-003 entry count
miss=""; for i in $(seq 1 58); do grep -q "^ENTRY	$i[a-z0-9]*$" <<<"$parsed" || miss="$miss $i"; done
if [ "$n_entries" -eq 94 ] && [ -z "$miss" ]; then ok "TC-003 entry count 94, numbers 1..58 present"
else bad "TC-003 entry count" "entries=$n_entries (want 94), missing numbers:$miss"; fi

# TC-004 Check honest
e4=$(grep 'Check has neither' <<<"$errs")
pm=""; while IFS=$'\t' read -r _ id p; do [ -e "$p" ] || pm="$pm [$id: $p]"; done < <(grep '^PATH' <<<"$parsed")
if [ -z "$e4" ] && [ -z "$pm" ]; then ok "TC-004 check field is honest"
else bad "TC-004 check field is honest" "${e4//$'\n'/ }$pm"; fi

# TC-005 touches greppable
nt=$(tr -d '\r' < "$P" | grep -c '^Touches: *[^ ]')
if [ "$nt" -eq "$n_entries" ] && [ "$n_entries" -eq 94 ]; then ok "TC-005 Touches lines = entries = 94"
else bad "TC-005 Touches lines = entries" "touches=$nt entries=$n_entries"; fi
if tr -d '\r' < "$P" | grep -q '^Touches:.*prepare_launch'; then ok "TC-005 grep prepare_launch finds an entry"; else bad "TC-005 grep prepare_launch finds an entry"; fi

# TC-006 touches items come from the entry text
e6=$(grep 'Touches item' <<<"$errs")
if [ -z "$e6" ]; then ok "TC-006 every Touches item appears in its entry"
else bad "TC-006 every Touches item appears in its entry"; cut -f2- <<<"$e6" | tr '\t' ' ' | sed 's/^/    entry /' | head -n 40; fi

# TC-010 pinned strings survive
for k in '--relative-paths' 'auto mode classifier' 'UNVERIFIED' 'maxParallel' 'NXF_SINGULARITY_LIBRARYDIR' 'NXF_SINGULARITY_CACHEDIR' \
  'GatewayPorts off on NCHC: reverse forward is loopback-only (measured 2026-10-11)' 'Seqera launcher scripts hold the token in a 755 file'; do
  hasf "TC-010 pinned: $k" "$P" "$k"
done
for r in '^\*\*52\. .*read-only.*\*\*' '^\*\*53\. .*-r.*\*\*'; do
  c=$(tr -d '\r' < "$P" | grep -cE "$r")
  if [ "$c" -eq 1 ]; then ok "TC-010 heading /$r/ once"; else bad "TC-010 heading /$r/ once" "found $c"; fi
done

# TC-013 no secrets in the new fields
sec=$(grep '^SECRET' <<<"$parsed")
if [ -z "$sec" ]; then ok "TC-013 no secret-like text in fields"; else bad "TC-013 no secret-like text in fields" "$sec"; fi

# TC-014 platform tier wording
if tr -d '\r' < "$L" | grep -q 'one tier A PR'; then bad "TC-014 PLATFORM no 'one tier A PR'"; else ok "TC-014 PLATFORM no 'one tier A PR'"; fi
hasf "TC-014 PLATFORM tier C sentence" "$L" 'A new snapshot is one tier C PR: the changed file, plus the new sha here and in the test.'

if [ "$fails" -eq 0 ]; then echo "pitfalls_format_test: all ok"; else echo "pitfalls_format_test: $fails failed"; exit 1; fi
