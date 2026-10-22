#!/bin/bash
# settings-nano4 (M1-06): the nano4 docs carry the agreed keys, the site-table row and two pitfalls.
# Text greps only; no network, no ssh. Test cases: specs/settings-nano4/test-case.md (TC ids in labels).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
fails=0
ok()  { printf '%-78s ok\n' "$1"; }
bad() { printf '%-78s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }
has() { # label file extended-regex
  # read the file first: `grep -q` closing a pipe early makes `tr` fail under pipefail on big files
  local txt; txt=$(tr -d '\r' < "$2")
  if grep -qE -- "$3" <<<"$txt"; then ok "$1"; else bad "$1" "no /$3/ in $2"; fi
}
S=docs/SETTINGS.md; A=docs/SITE_ADAPTER.md; P=docs/PITFALLS.md; O=docs/OPERATIONS.md

# TC-009/TC-033: the six key names, whole-word, in backticks
for k in way_back platform_public_url site_profile modules siteConfigVars sitePipelines; do
  has "TC-033 SETTINGS has \`$k\`" "$S" "\`$k\`"
done
# TC-001..TC-008
has "TC-001 way_back values forward and direct" "$S" 'way_back.*forward.*direct|way_back.*direct.*forward'
has "TC-002 way_back default forward under reach ssh" "$S" 'default.*forward|forward.*default'
has "TC-003 direct needs platform_public_url" "$S" 'needs.*platform_public_url'
has "TC-004 platform_public_url https" "$S" 'https'
has "TC-004 loopback exception" "$S" '[Ll]oopback'
has "TC-005 site_profile values" "$S" 'taiwania3.*nano4'
has "TC-006 site_profile reserved, not read" "$S" '[Rr]eserved'
has "TC-008 example file path" "$S" 'configs/sites/nchc-nano4-ce\.json'
# TC-012..TC-019
has "TC-012 SITE_ADAPTER nano4 row" "$A" '^\| *nano4'
has "TC-013 NFCORE_SITE_CONFIG" "$A" 'NFCORE_SITE_CONFIG'
has "TC-013 selectQueue" "$A" 'selectQueue'
has "TC-013 fallback config" "$A" 'configs/sites/nchc-nano4\.config'
has "TC-015 with-tower" "$A" '\-with-tower'
has "TC-016 storage" "$A" '/work/u9613010'
has "TC-017 ControlMaster" "$A" 'ControlMaster'
has "TC-019 LIBRARYDIR in SITE_ADAPTER" "$A" 'NXF_SINGULARITY_LIBRARYDIR'
# TC-021..TC-024
has "TC-021 pitfall 52 title" "$P" '^\*\*52\. .*read-only.*\*\*'
has "TC-021 LIBRARYDIR in PITFALLS" "$P" 'NXF_SINGULARITY_LIBRARYDIR'
has "TC-022 CACHEDIR in PITFALLS" "$P" 'NXF_SINGULARITY_CACHEDIR'
has "TC-023 pitfall 53 title" "$P" '^\*\*53\. .*-r.*\*\*'
# TC-026..TC-029
has "TC-026 OPERATIONS public URL section" "$O" '^###+ .*([Pp]ublic URL|公開網址)'
has "TC-028 Tailscale Funnel" "$O" 'Tailscale Funnel'
has "TC-029 user-info" "$O" 'user-info'
has "TC-029 401" "$O" '401'
has "TC-029 header" "$O" 'X-ABF-Platform'
[ "$fails" -eq 0 ]
