#!/bin/bash
# One-shot readiness check. Used by :setup to decide what to fix and by :launch
# to refuse to submit into a broken environment.
#
# Exit 0 = ready. Exit 1 = something listed as FAIL.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
WS="${TOWER_WORKSPACE_ID:-}"
CE="${NCHC_COMPUTE_ENV:-nchc-taiwania3}"
TW="${TW_BIN:-$HOME/bin/tw}"
fail=0
say() { printf "%-10s %-14s %s\n" "$1" "$2" "$3"; [ "$1" = FAIL ] && fail=1; return 0; }

[ -n "${LAB_RUNS_DIR:-}" ] \
  && say OK   "LAB_RUNS_DIR" "$LAB_RUNS_DIR" \
  || say FAIL "LAB_RUNS_DIR" "not set - nothing below can be checked"

if [ -n "${LAB_RUNS_DIR:-}" ]; then
  out=$(bash "$HERE/relay_ctl.sh" status 2>&1) \
    && say OK "relay" "$out" \
    || say FAIL "relay" "not running - compute nodes have no route out ($HERE/relay_ctl.sh start)"
  grep -q WARNING <<<"$out" && say FAIL "relay-host" "started on a different login node; update the CE proxy variables"

  out=$(bash "$HERE/agent_ctl.sh" status 2>&1) \
    && say OK "agent" "$out" \
    || say FAIL "agent" "not running - Platform will show no outputs ($HERE/agent_ctl.sh start)"
fi

out=$(bash "$HERE/check_partitions.sh" "$ROOT/configs/nchc.config" 2>&1) \
  && say OK "partitions" "config matches the live QOS table" \
  || say FAIL "partitions" "$(head -1 <<<"$out")"

if [ -x "$TW" ] && [ -n "${TOWER_ACCESS_TOKEN:-}" ]; then
  # `compute-envs list` prints the workspace name in its header, which also
  # contains the CE name here - parse the detail view instead.
  st=$("$TW" compute-envs view -n "$CE" ${WS:+-w "$WS"} 2>/dev/null \
        | awk -F'|' '$1 ~ /^ *Status/ {gsub(/[ \t]/,"",$2); print $2; exit}')
  [ "$st" = "AVAILABLE" ] \
    && say OK "compute-env" "$CE AVAILABLE" \
    || say FAIL "compute-env" "$CE is '${st:-unreachable}'"
else
  say SKIP "compute-env" "tw or TOWER_ACCESS_TOKEN unavailable in this shell"
fi

exit $fail
