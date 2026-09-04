#!/bin/bash
# One-shot readiness check. Used by :setup to decide what to fix and by :launch
# to refuse to submit into a broken environment. What "ready" means for a given
# site comes from its adapter - see docs/SITE_ADAPTER.md.
#
# Exit 0 = ready. Exit 1 = something listed as FAIL.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
. "$HERE/settings.sh"

REACH="$(setting reach local)"
WS="${TOWER_WORKSPACE_ID:-$(setting workspace_id)}"
CE="${SEQERA_COMPUTE_ENV:-$(setting compute_env)}"
TW="${TW_BIN:-$(setting tw_bin)}"
[ -n "$TW" ] || TW="$(command -v tw 2>/dev/null)"

# The token lives in a mode-600 file beside the settings file. Deriving it from
# the settings file rather than from LAB_RUNS_DIR is what lets the pair travel
# to a laptop together when the site is reached over ssh - LAB_RUNS_DIR is then
# a path on the far side. Without this the compute-env check below SKIPs in any
# shell that did not already export the token, and SKIP is not FAIL: preflight
# then exits 0 having never asked the one question that decides whether a
# launch can land.
TOKEN_FILE="${SEQERA_TOKEN_FILE:-$(dirname "$SETTINGS_FILE")/.seqera_token}"
if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && [ -r "$TOKEN_FILE" ]; then
  TOWER_ACCESS_TOKEN="$(cat "$TOKEN_FILE")"
  export TOWER_ACCESS_TOKEN
fi
fail=0
say() { printf "%-10s %-14s %s\n" "$1" "$2" "$3"; [ "$1" = FAIL ] && fail=1; return 0; }

# A repair instruction has to be runnable from where the user is standing.
fix() { [ "$REACH" = ssh ] && echo "scripts/on_site.sh --script scripts/$1" || echo "scripts/$1"; }

# --- Can the site be reached at all? -----------------------------------------
# Everything below the first group depends on the answer, so ask it first. The
# ssh case is the one that must be loud: with the master connection down, every
# later check would sit waiting for a one-time code that Claude cannot supply.
SITE=0
case "$REACH" in
  none)  say OK   "reach" "none - Platform manages this site; there is nothing to reach" ;;
  local) say OK   "reach" "local - this deployment runs on the site"; SITE=1 ;;
  ssh)
    if out=$(bash "$HERE/on_site.sh" --check-reach 2>&1); then
      say OK "reach" "ssh $(setting site_host) - the master connection is up"; SITE=1
    else
      say FAIL "reach" "the master connection to $(setting site_host) is down"
      printf '%s\n' "$out"
    fi ;;
  *) say FAIL "reach" "unknown value '$REACH' - must be none, local or ssh (docs/SITE_ADAPTER.md)" ;;
esac

# --- Where runs live ---------------------------------------------------------
if [ "$REACH" = local ]; then
  [ -n "${LAB_RUNS_DIR:-}" ] \
    && say OK   "run-area" "$LAB_RUNS_DIR" \
    || say FAIL "run-area" "LAB_RUNS_DIR is not set - this deployment's own state cannot be found without it; run setup"
else
  sr="$(setting storage_root)"
  [ -n "$sr" ] \
    && say OK   "run-area" "$sr (on the site)" \
    || say FAIL "run-area" "no 'storage_root' in the deployment settings - run setup"
fi

# --- What only the site can answer -------------------------------------------
# Skipped entirely, not failed, when there is no site to ask. A Platform-managed
# compute environment has no relay, no outputs reader and no scheduler of its
# own; reporting those as FAIL would make a healthy cloud site look broken.
if [ "$SITE" = 1 ]; then
  out=$(bash "$HERE/on_site.sh" --script "$HERE/egress_ctl.sh" status 2>&1) \
    && say OK "egress" "$out" \
    || say FAIL "egress" "the site's egress channel is down ($(fix egress_ctl.sh) start)"
  grep -q WARNING <<<"$out" && say FAIL "egress-host" "started somewhere else; the compute environment now points at the wrong address"

  out=$(bash "$HERE/on_site.sh" --script "$HERE/agent_ctl.sh" status 2>&1) \
    && say OK "agent" "$out" \
    || say FAIL "agent" "not running - Platform will show no outputs ($(fix agent_ctl.sh) start)"

  out=$(bash "$HERE/on_site.sh" --script "$HERE/check_resource_contract.sh" 2>&1) \
    && say OK "resources" "the resource contract matches this site" \
    || say FAIL "resources" "$(head -1 <<<"$out")"
fi

# --- Platform, which is reached the same way from anywhere -------------------
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
