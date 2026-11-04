#!/usr/bin/env bash
# cloud-burn scope guard: fail if <worktree>'s diff vs origin/v3 (committed + staged + unstaged + untracked)
# touches a path outside the allowed list, or any FORBIDDEN/HOT path (RULES.md §3, plus /tmp/cb/hot_dynamic.txt).
# usage: check_scope.sh <worktree> <allowed path or prefix ending in / or glob>...
set -u
wt=${1:?worktree}; shift
[ $# -gt 0 ] || { echo "check_scope: no allowed paths given" >&2; exit 2; }
cd "$wt" || exit 2
changed=$( { git diff --name-only origin/v3...HEAD; git diff --name-only HEAD; git diff --name-only --cached; git ls-files --others --exclude-standard; } | sort -u | sed '/^$/d')
forbidden_re='^(\.specify/|\.github/|hooks/|\.claude-plugin/plugin\.json$|extensions/claude-code-kit/settings\.json$|platform/abf_station/|docs/ROADMAP\.md$|tests/run_all\.sh$|pytest\.ini$|platform/pyproject\.toml$|platform/setup\.py$|platform/tests/conftest\.py$|\.claude/|cloud-burn/)|(^|/)spec\.md$|(^|/)test-case[^/]*\.md$|\.egg-info/|(^|/)build/'
hot_re='^platform/abf_platform/(web[^/]*\.py|jobs\.py|store\.py|mcp_server\.py|cli\.py|cliout\.py|confirm\.py|failures\.py|guidance\.py|pipeline_lint\.py|actions/)|^platform/abf_launch/|^platform/tests/([^/]*_harness\.py|__golden__/|mcp/|fake_slurm\.py|test_web_|test_results_|test_pipeline_lint\.py|test_station_lint\.py|test_launch_profiles\.py|test_head_nodefail\.py|test_station_head_state\.py|test_cli_|test_fake_slurm_shim\.py|test_su_job_states\.py|test_actions_layer\.py|test_mcp)|^tests/(smoke/|constitution_scope_test\.sh|platform_direction_docs_test\.sh|pitfalls_format_test\.sh)|^docs/(PLATFORM|TESTING|PITFALLS)\.md$|^(PRODUCT|DESIGN|CONTEXT)\.md$'
bad=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if printf '%s\n' "$f" | grep -Eq "$forbidden_re"; then echo "FORBIDDEN: $f"; bad=1; continue; fi
  if printf '%s\n' "$f" | grep -Eq "$hot_re"; then echo "HOT: $f"; bad=1; continue; fi
  if [ -s /tmp/cb/hot_dynamic.txt ] && grep -Fxq "$f" /tmp/cb/hot_dynamic.txt; then echo "HOT(dynamic): $f"; bad=1; continue; fi
  ok=0
  for a in "$@"; do
    case "$a" in
      */) case "$f" in "$a"*) ok=1;; esac;;
      *) case "$f" in $a) ok=1;; esac;;
    esac
  done
  [ $ok = 1 ] || { echo "OUT-OF-SCOPE: $f"; bad=1; }
done <<< "$changed"
[ $bad = 0 ] && echo "check_scope: OK ($(printf '%s\n' "$changed" | sed '/^$/d' | wc -l) files)"
exit $bad
