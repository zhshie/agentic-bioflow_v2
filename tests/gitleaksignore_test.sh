#!/bin/bash
# The .gitleaksignore list is a reviewed, closed set: the 34 gitleaks findings (25 distinct
# fingerprints, because a line with two hits has one fingerprint) the maintainer examined on
# 2026-11-12 and judged false positives, plus one more fingerprint (a made-up test token in
# platform/tests/test_studio_remote.py, commit 1b6dcaae) added after that report: 26 in all. Growing the list, or loosening .gitleaks.toml, must turn
# this red so that it is a deliberate act. Change EXPECTED_COUNT / TOML_SHA256 / IGNORE_SET_SHA256 only in a reviewed PR.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IG="$ROOT/.gitleaksignore"
GL="$ROOT/.gitleaks.toml"
EXPECTED_COUNT=26
TOML_SHA256="14e9fabc1e4f6c76b5fe06d40302f1fdd57aa5bb2745d9410d946a14846417a5"
IGNORE_SET_SHA256="8c1fc259b5a82670b8e8554a83ccdeaf6127490a816811b2f1432d01977469a1"
FAILS=0
ok()   { echo "ok   $1"; }
fail() { echo "FAIL $1"; FAILS=$((FAILS+1)); }
check() { if "$1"; then ok "$1"; else fail "$1"; fi; }
entries() { grep -Ev '^[[:space:]]*(#|$)' "$IG"; }

test_ignore_file_exists() { [ -f "$IG" ]; }
test_every_entry_is_a_well_formed_fingerprint() {
  [ -f "$IG" ] || return 1
  local bad
  bad="$(entries | grep -Ev '^[0-9a-f]{40}:[A-Za-z0-9_./-]+:[a-z0-9-]+:[0-9]+$' || true)"
  [ -z "$bad" ]
}
test_no_wildcards() {
  [ -f "$IG" ] || return 1
  ! grep -Eq "[*?[]" < <(entries)
}
test_exact_count() { [ -f "$IG" ] && [ "$(entries | wc -l | tr -d ' ')" = "$EXPECTED_COUNT" ]; }
test_no_duplicates() { [ -f "$IG" ] && [ -z "$(entries | sort | uniq -d)" ]; }
test_every_entry_has_a_comment_group_above() {
  [ -f "$IG" ] || return 1
  awk '/^[[:space:]]*$/{next} /^#/{c=1;next} {if(!c)bad=1} END{exit bad}' "$IG"
}
test_ignore_set_unchanged() {
  [ -f "$IG" ] || return 1
  # TC: contents pin; comment/blank edits do not matter, any change to the fingerprint set does.
  local got; got="$(entries | LC_ALL=C sort | sha256sum | cut -d' ' -f1)"
  [ "$got" = "$IGNORE_SET_SHA256" ]
}
test_gitleaks_toml_unchanged_and_has_no_allowlist() {
  [ -f "$GL" ] || return 1
  ! grep -Eq 'allowlist|^\[\[rules\]\]|disabledRules|paths *=|regexes *=|commits *=' <(grep -v '^[[:space:]]*#' "$GL") || return 1
  local got; got="$(sha256sum "$GL" | cut -d' ' -f1)"
  [ "$got" = "$TOML_SHA256" ]
}

check test_ignore_file_exists
check test_every_entry_is_a_well_formed_fingerprint
check test_no_wildcards
check test_exact_count
check test_no_duplicates
check test_every_entry_has_a_comment_group_above
check test_ignore_set_unchanged
check test_gitleaks_toml_unchanged_and_has_no_allowlist
[ "$FAILS" = 0 ]
