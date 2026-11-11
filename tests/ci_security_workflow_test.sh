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
cg() { grep "$@" < <(code); }   # no pipe into grep, so pipefail cannot hide a match

test_security_workflow_exists_and_is_separate() { # TC-001
  [ -f "$WF" ] && [ -f "$TY" ] && [ "$WF" != "$TY" ] || return 1
  grep -q '^name: security$' "$WF" || return 1
  cg -Eq '^  gitleaks:' && cg -Eq '^  pip-audit:'
}
test_job_names_do_not_collide_with_required_check() { # TC-002
  [ -f "$WF" ] || return 1
  ! cg -Eq '^  (run_all|shard):|^[[:space:]]+name:[[:space:]]*"?(run_all|shard)"?[[:space:]]*$'
}
test_triggers() { # TC-003, TC-004
  [ -f "$WF" ] || return 1
  local p; for p in pull_request push schedule workflow_dispatch; do
    cg -Eq "^  $p:" || return 1
  done
  cg -Eq 'cron:' || return 1
  cg -Eq 'branches: \[(v3, main|main, v3)\]' || return 1
  ! cg -q 'merge_group'
}
test_permissions_are_read_only_and_no_pull_request_target() { # TC-005..008
  [ -f "$WF" ] || return 1
  cg -Eq '^permissions:' || return 1
  local body
  body="$(code | awk '/^permissions:/{f=1;next} f&&/^[^ ]/{exit} f&&NF{print}')"
  [ "$body" = "  contents: read" ] || return 1
  # TC-006: no permissions block inside a job
  [ "$(code | grep -Ec '^[[:space:]]*permissions:')" = 1 ] || return 1
  ! cg -q 'pull_request_target' && ! cg -q 'secrets\.'
}
test_every_uses_is_pinned_to_full_sha() { # TC-009
  [ -f "$WF" ] || return 1
  local n bad
  n="$(cg -c 'uses:')"; [ "$n" -ge 2 ] || return 1
  bad="$(code | grep 'uses:' | grep -Ev 'uses: [A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}  # v[0-9]+\.[0-9]+\.[0-9]+' || true)"
  [ -z "$bad" ] || return 1
  ! { cg 'uses:' | grep -E '@v[0-9]|@main|@master' >/dev/null; }
}
test_no_way_to_turn_checks_off() { # TC-011
  [ -f "$WF" ] || return 1
  ! cg -Eq 'continue-on-error|\|\| true|--no-fail|if: false'
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
  ! cg -q 'gitleaks/gitleaks-action' || return 1
  cg -Eq 'GITLEAKS_VERSION: *"?[0-9]+\.[0-9]+\.[0-9]+"?' || return 1
  ! cg -qi 'latest' || return 1
  cg -Eq 'sha256sum -c' && cg -Eq '[0-9a-f]{64}'
}
test_gitleaks_scans() { # TC-023..026
  [ -f "$WF" ] || return 1
  cg -Eq 'fetch-depth: 0' || return 1
  cg -Fq 'gitleaks git --redact --no-banner --config .gitleaks.toml' || return 1
  cg -Fq -- '--log-opts "origin/${{ github.base_ref }}..HEAD"' || return 1
  cg -Eq "if: github.event_name == 'pull_request'"
}
test_gitleaks_uses_redact() { # TC-027
  [ -f "$WF" ] || return 1
  local n r
  n="$(cg -c 'gitleaks git ')"
  r="$(code | grep 'gitleaks git ' | grep -c -- '--redact')"
  [ "$n" -ge 2 ] && [ "$n" = "$r" ]
}
test_existing_tests_yml_untouched() { # TC-012, TC-013, TC-044
  # origin/v3 can be stale in mirrors, so measure from the first commit of this task (its plan commit).
  local plan
  plan="$(git -C "$ROOT" log --format=%H --grep='^chore(ci-secrets-deps): plan from developer-agent' -1 2>/dev/null)"
  if [ -z "$plan" ]; then
    echo "skipped test_existing_tests_yml_untouched (no task history)"; return 0
  fi
  [ -z "$(git -C "$ROOT" diff "${plan}^" HEAD -- .github/workflows/tests.yml)" ]
}
test_pip_audit_targets_both_files() { # TC-032..036
  [ -f "$WF" ] || return 1
  cg -Fq 'pip-audit -r platform/constraints.txt --no-deps --disable-pip' || return 1
  cg -Eq 'pip-audit .*(\./platform|platform/pyproject\.toml)' || return 1
  cg -Eq 'python-version: *"?3\.12"?' || return 1
  cg -Eq 'pip install pip-audit==[0-9]+\.[0-9]+' || return 1
  cg -q -- '--ignore-vuln' || return 1
  cg -q 'platform/pip-audit-ignore.txt' || return 1
  ! cg -Eq -- '--ignore-vuln +[A-Za-z]'
}

# ---- gitleaks-classify: JSON report, redacted, uploaded as artifact ----
scan_line() { code | grep -A1 -F 'name: Scan full history' | grep 'run:' | head -1; }
report_path() { scan_line | sed -n 's/.*--report-path[[:space:]]\{1,\}\([^[:space:]]\{1,\}\).*/\1/p'; }
upload_block() { # the upload-artifact step, from its "- uses" line to the next "- " step
  code | awk '/^      - /{inb=0} /uses: actions\/upload-artifact@/{inb=1} inb{print}'
}
test_gitleaks_full_scan_writes_json_report() { # TC-001, TC-002
  local l p; l="$(scan_line)"
  [ -n "$l" ] || return 1
  grep -Fq -- '--report-format json' <<<"$l" || return 1
  p="$(report_path)"
  [ "$p" = "gitleaks-report.json" ]
}
test_gitleaks_report_stays_redacted() { # TC-004, TC-005
  local n r
  n="$(cg -c 'gitleaks git ')"
  r="$(code | grep 'gitleaks git ' | grep -c -- '--redact')"
  [ "$n" -ge 2 ] && [ "$n" = "$r" ] || return 1
  ! cg -q -- '--no-redact'
}
test_report_is_uploaded_always_as_artifact() { # TC-006, TC-008..TC-014
  local b p order; b="$(upload_block)"
  [ -n "$b" ] || return 1
  grep -Eq 'uses: actions/upload-artifact@[0-9a-f]{40}  # v[0-9]+\.[0-9]+\.[0-9]+' <<<"$b" || return 1
  grep -Eq '^        if: always\(\)$' <<<"$b" || return 1
  p="$(report_path)"
  [ -n "$p" ] && grep -Eq "^          path: $p\$" <<<"$b" || return 1
  grep -Eq '^          name: gitleaks-report$' <<<"$b" || return 1       # TC-011
  grep -Eq '^          if-no-files-found: ignore$' <<<"$b" || return 1   # TC-012
  grep -Eq '^          retention-days: 14$' <<<"$b" || return 1          # TC-013
  grep -Eq 'upload-artifact@[0-9a-f]{40}  # v4\.' <<<"$b" || return 1   # TC-008
  # TC-014: order scan -> upload -> PR scan, all inside the gitleaks job
  order="$(code | awk '/^  pip-audit:/{exit} /name: Scan full history/{print "S"} /actions\/upload-artifact@/{print "U"} /name: Scan this PR/{print "P"}' | tr -d '\n')"
  [ "$order" = "SUP" ]
}
test_upload_artifact_is_sha_pinned() { # TC-007
  local l; l="$(cg 'uses: actions/upload-artifact@')"
  [ -n "$l" ] || return 1
  grep -Eq '^[[:space:]]*- uses: actions/upload-artifact@[0-9a-f]{40}  # v[0-9]+\.[0-9]+\.[0-9]+$' <<<"$l" || return 1
  ! grep -Eq '@v[0-9]|@main|@master' <<<"$l"
}
test_permissions_stay_read_only_after_report() { # TC-026, TC-027
  [ "$(cg -c '^[[:space:]]*permissions:')" = 1 ] || return 1
  cg -Eq '^permissions:$' || return 1
  [ "$(code | awk '/^permissions:/{f=1;next} f&&/^[^ ]/{exit} f&&NF{print}')" = "  contents: read" ] || return 1
  ! cg -q 'secrets\.' && ! cg -q 'pull_request_target'
}
test_pr_scan_has_no_report() { # TC-025
  local l; l="$(code | grep -A3 -F "name: Scan this PR's commits")"
  grep -Fq "if: github.event_name == 'pull_request'" <<<"$l" || return 1
  local pr; pr="$(code | grep -F -- '--log-opts')"
  ! grep -Eq -- '--report-(format|path)' <<<"$pr"
}
test_gitleaks_toml_has_no_new_allowlist() { # TC-021 (origin/v3 baseline: 0 entries)
  [ "$(grep -c '^\[\[allowlists\]\]' "$GL")" = 0 ]
}
test_pip_audit_job_unchanged() { # TC-023
  local cur base
  base="$(MSYS_NO_PATHCONV=1 git -C "$ROOT" show "origin/v3:.github/workflows/security.yml" 2>/dev/null)" || base=""
  if [ -z "$base" ]; then echo "skipped test_pip_audit_job_unchanged (no origin/v3)"; return 0; fi
  cur="$(awk '/^  pip-audit:/{f=1} f' "$WF")"
  [ "$cur" = "$(awk '/^  pip-audit:/{f=1} f' <<<"$base")" ]
}
test_pip_audit_project_line_has_no_no_deps() { # TC-001..004: --no-deps only works with -r
  [ -f "$WF" ] || return 1
  local line
  line=$(cg -E 'pip-audit .*(\./platform|platform/pyproject\.toml)')
  [ -n "$line" ] || return 1
  ! grep -q -- '--no-deps' <<<"$line"
}

for t in test_security_workflow_exists_and_is_separate \
         test_job_names_do_not_collide_with_required_check test_triggers \
         test_permissions_are_read_only_and_no_pull_request_target \
         test_every_uses_is_pinned_to_full_sha test_no_way_to_turn_checks_off \
         test_allowlist_entries_have_reason_and_are_not_blanket \
         test_gitleaks_download_is_verified test_gitleaks_scans test_gitleaks_uses_redact \
         test_existing_tests_yml_untouched test_pip_audit_targets_both_files \
         test_gitleaks_full_scan_writes_json_report test_gitleaks_report_stays_redacted \
         test_report_is_uploaded_always_as_artifact test_upload_artifact_is_sha_pinned \
         test_permissions_stay_read_only_after_report test_pr_scan_has_no_report \
         test_gitleaks_toml_has_no_new_allowlist test_pip_audit_job_unchanged \
         test_pip_audit_project_line_has_no_no_deps; do
  check "$t"
done
[ "$FAILS" = 0 ] || { echo "$FAILS check(s) failed"; exit 1; }
echo "all ci_security_workflow checks passed"
