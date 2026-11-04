#!/bin/bash
# Static checks for .github/workflows/security.yml (gitleaks + pip-audit), .gitleaks.toml and
# platform/pip-audit-ignore.txt. grep/awk only: no network, no PyYAML.
# TC-001 separate workflow with both jobs   TC-002 no run_all/shard name   TC-003 triggers
# TC-004 no merge_group   TC-005..008 permissions/secrets   TC-009 pinned shas   TC-011 no off switch
# TC-012/013 tests.yml untouched   TC-020..028 gitleaks job   TC-029..031 allowlist
# TC-032..037 pip-audit job   TC-038 ignore-file lines   TC-043 ok/FAIL output   TC-044 skipped
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WF="$ROOT/.github/workflows/security.yml"
TY="$ROOT/.github/workflows/tests.yml"
GL="$ROOT/.gitleaks.toml"
IG="$ROOT/platform/pip-audit-ignore.txt"
FAILS=0
ok()   { echo "ok   $1"; }
fail() { echo "FAIL $1"; FAILS=$((FAILS+1)); }
check() { # name
  if "$1"; then ok "$1"; else fail "$1"; fi
}
code() { grep -v '^[[:space:]]*#' "$WF"; }   # workflow without comment lines

test_security_workflow_exists_and_is_separate() { # TC-001
  [ -f "$WF" ] && [ -f "$TY" ] && [ "$WF" != "$TY" ] || return 1
  grep -q '^name: security$' "$WF" || return 1
  code | grep -Eq '^  gitleaks:' && code | grep -Eq '^  pip-audit:'
}
test_job_names_do_not_collide_with_required_check() { # TC-002
  [ -f "$WF" ] || return 1
  ! code | grep -Eq '^  (run_all|shard):|^[[:space:]]+name:[[:space:]]*"?(run_all|shard)"?[[:space:]]*$'
}
test_triggers() { # TC-003, TC-004
  [ -f "$WF" ] || return 1
  local p; for p in pull_request push schedule workflow_dispatch; do
    code | grep -Eq "^  $p:" || return 1
  done
  code | grep -Eq 'cron:' || return 1
  code | grep -Eq 'branches: \[(v3, main|main, v3)\]' || return 1
  ! code | grep -q 'merge_group'
}
test_permissions_are_read_only_and_no_pull_request_target() { # TC-005..008
  [ -f "$WF" ] || return 1
  code | grep -Eq '^permissions:' || return 1
  local body
  body="$(code | awk '/^permissions:/{f=1;next} f&&/^[^ ]/{exit} f&&NF{print}')"
  [ "$body" = "  contents: read" ] || return 1
  # TC-006: no permissions block inside a job
  [ "$(code | grep -Ec '^[[:space:]]*permissions:')" = 1 ] || return 1
  ! code | grep -q 'pull_request_target' && ! code | grep -q 'secrets\.'
}
test_every_uses_is_pinned_to_full_sha() { # TC-009
  [ -f "$WF" ] || return 1
  local n bad
  n="$(code | grep -c 'uses:')"; [ "$n" -ge 2 ] || return 1
  bad="$(code | grep 'uses:' | grep -Ev 'uses: [A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}  # v[0-9]+\.[0-9]+\.[0-9]+' || true)"
  [ -z "$bad" ] || return 1
  ! code | grep 'uses:' | grep -Eq '@v[0-9]|@main|@master'
}
test_no_way_to_turn_checks_off() { # TC-011
  [ -f "$WF" ] || return 1
  ! code | grep -Eq 'continue-on-error|\|\| true|--no-fail|if: false'
}
test_allowlist_entries_have_reason_and_are_not_blanket() { # TC-028..031, TC-038
  [ -f "$GL" ] && [ -f "$IG" ] || return 1
  grep -Eq '^useDefault *= *true' "$GL" || return 1               # TC-028 keep default rules
  ! grep -Eq '^\[\[rules\]\]|^disabledRules' "$GL" || return 1
  ! grep -Eq "regexes *= *\[ *['\"]\.\*['\"]|paths *= *\[ *['\"]\.\*['\"] *\]" "$GL" || return 1
  # every allowlist header / commits / paths / regexes line has a comment line above it
  awk '
    /^\[\[allowlists\]\]/ || /^[[:space:]]*(commits|paths|regexes)[[:space:]]*=/ {
      if (prev !~ /^[[:space:]]*#/) bad=1
    }
    { if ($0 !~ /^[[:space:]]*$/) prev=$0 }
    END { exit bad }' "$GL" || return 1
  # TC-031: each entry names commits, paths or regexes
  local h c; h="$(grep -c '^\[\[allowlists\]\]' "$GL")"
  c="$(grep -Ec '^[[:space:]]*(commits|paths|regexes)[[:space:]]*=' "$GL")"
  [ "$c" -ge "$h" ] || return 1
  # pip-audit-ignore: each non-comment line has id, '#', reason and a date
  local bad
  bad="$(grep -Ev '^[[:space:]]*(#|$)' "$IG" | grep -Ev '^[A-Za-z0-9-]+  # .*[0-9]{4}-[0-9]{2}-[0-9]{2}' || true)"
  [ -z "$bad" ]
}
test_gitleaks_download_is_verified() { # TC-020..022
  [ -f "$WF" ] || return 1
  ! code | grep -q 'gitleaks/gitleaks-action' || return 1
  code | grep -Eq 'GITLEAKS_VERSION: *"?[0-9]+\.[0-9]+\.[0-9]+"?' || return 1
  ! code | grep -qi 'latest' || return 1
  code | grep -Eq 'sha256sum -c' && code | grep -Eq '[0-9a-f]{64}'
}
test_gitleaks_scans() { # TC-023..026
  [ -f "$WF" ] || return 1
  code | grep -Eq 'fetch-depth: 0' || return 1
  code | grep -Fq 'gitleaks git --redact --no-banner --config .gitleaks.toml' || return 1
  code | grep -Fq -- '--log-opts "origin/${{ github.base_ref }}..HEAD"' || return 1
  code | grep -Eq "if: github.event_name == 'pull_request'"
}
test_gitleaks_uses_redact() { # TC-027
  [ -f "$WF" ] || return 1
  local n r
  n="$(code | grep -c 'gitleaks git ')"
  r="$(code | grep 'gitleaks git ' | grep -c -- '--redact')"
  [ "$n" -ge 2 ] && [ "$n" = "$r" ]
}
test_existing_tests_yml_untouched() { # TC-012, TC-013, TC-044
  if ! git -C "$ROOT" rev-parse --verify -q origin/v3 >/dev/null 2>&1; then
    echo "skipped test_existing_tests_yml_untouched (no origin/v3 history)"; return 0
  fi
  [ -z "$(git -C "$ROOT" diff origin/v3 -- .github/workflows/tests.yml)" ]
}
test_pip_audit_targets_both_files() { # TC-032..036
  [ -f "$WF" ] || return 1
  code | grep -Fq 'pip-audit -r platform/constraints.txt --no-deps --disable-pip' || return 1
  code | grep -Eq 'pip-audit .*(\./platform|platform/pyproject\.toml)' || return 1
  code | grep -Eq 'python-version: *"?3\.12"?' || return 1
  code | grep -Eq 'pip install pip-audit==[0-9]+\.[0-9]+' || return 1
  code | grep -q -- '--ignore-vuln' || return 1
  code | grep -q 'platform/pip-audit-ignore.txt' || return 1
  ! code | grep -Eq -- '--ignore-vuln +[A-Za-z]'
}

for t in test_security_workflow_exists_and_is_separate \
         test_job_names_do_not_collide_with_required_check test_triggers \
         test_permissions_are_read_only_and_no_pull_request_target \
         test_every_uses_is_pinned_to_full_sha test_no_way_to_turn_checks_off \
         test_allowlist_entries_have_reason_and_are_not_blanket \
         test_gitleaks_download_is_verified test_gitleaks_scans test_gitleaks_uses_redact \
         test_existing_tests_yml_untouched test_pip_audit_targets_both_files; do
  check "$t"
done
[ "$FAILS" = 0 ] || { echo "$FAILS check(s) failed"; exit 1; }
echo "all ci_security_workflow checks passed"
