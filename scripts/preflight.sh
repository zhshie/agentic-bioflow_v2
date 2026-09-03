#!/bin/bash
# One-shot readiness check. Used by :setup to decide what to fix and by :launch
# to refuse to submit into a broken environment. What counts as ready depends on
# the site - see docs/SITE_ADAPTER.md. What "ready" means for a
# given site comes from its adapter - see docs/SITE_ADAPTER.md.
# to refuse to submit into a broken environment.
#
# Exit 0 = ready. Exit 1 = something listed as FAIL.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
. "$HERE/settings.sh"
WS="${TOWER_WORKSPACE_ID:-$(setting workspace_id)}"
CE="${SEQERA_COMPUTE_ENV:-$(setting compute_env)}"
TW="${TW_BIN:-$(setting tw_bin)}"
[ -n "$TW" ] || TW="$(command -v tw 2>/dev/null)"
fail=0
say() { printf "%-10s %-14s %s\n" "$1" "$2" "$3"; [ "$1" = FAIL ] && fail=1; return 0; }

[ -n "${LAB_RUNS_DIR:-}" ] \
  && say OK   "LAB_RUNS_DIR" "$LAB_RUNS_DIR" \
  || say FAIL "LAB_RUNS_DIR" "not set - this deployment's own state cannot be found without it; run setup"

if [ -n "${LAB_RUNS_DIR:-}" ]; then
  out=$(bash "$HERE/egress_ctl.sh" status 2>&1) \
    && say OK "egress" "$out" \
    || say FAIL "egress" "the site's egress channel is down ($HERE/egress_ctl.sh start)"
  grep -q WARNING <<<"$out" && say FAIL "egress-host" "started somewhere else; the compute environment now points at the wrong address"

  out=$(bash "$HERE/agent_ctl.sh" status 2>&1) \
    && say OK "agent" "$out" \
    || say FAIL "agent" "not running - Platform will show no outputs ($HERE/agent_ctl.sh start)"
fi

out=$(bash "$HERE/check_resource_contract.sh" "$ROOT/configs/sites/nchc.config" 2>&1) \
  && say OK "resources" "the resource contract matches this site" \
  || say FAIL "resources" "$(head -1 <<<"$out")"

if [ -x "$TW" ] && [ -n "${TOWER_ACCESS_TOKEN:-}" ]; then
  # `compute-envs list` prints the workspace name in its header, which also
  # contains the CE name here - parse the detail view instead.
  st=$("$TW" compute-envs view -n "$CE" ${WS:+-w "$WS"} 2>/dev/null \
        | awk -F'|' '$1 ~ /^ *Status/ {gsub(/[ \t]/,"",$2); print $2; exit}')
  [ "$st" = "AVAILABLE" ] \
    && say OK "compute-env" "$CE AVAILABLE" \
    || say FAIL "compute-env" "$CE is '${st:-unreachable}'"
else
  if [ -z "$CE" ]; then
    say FAIL "compute-env" "no compute_env in the deployment settings - run setup"
  else
    say SKIP "compute-env" "tw or a token is unavailable in this shell"
  fi
fi

exit $fail
