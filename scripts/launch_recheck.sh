#!/bin/bash
# Just-in-time re-check, run right before `tw launch` (issue #7).
# Nothing existing: preflight.sh asks these two questions only once, at step 0 of the launch skill, and no other script asks them again right before submitting.
#
# preflight.sh asks whether the site's two daemons are alive once, at step 0 of
# the launch skill. A parameter walkthrough can take as long as the user needs,
# and the outputs reader can die in that time ("No Tower Agent is online" only
# shows after the submit). This asks the same two questions again, nothing else:
# no resource contract, no compute-env status, no token. Read-only; it never
# starts anything and never caches - every call asks the site afresh.
#
# Exit 0 = both alive (or nothing to ask). Exit 1 = something listed as FAIL.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

REACH="$(setting reach local)"
fail=0
say() { printf "%-10s %-14s %s\n" "$1" "$2" "$3"; [ "$1" = FAIL ] && fail=1; return 0; }
fix() { [ "$REACH" = ssh ] && echo "scripts/on_site.sh --script scripts/$1" || echo "scripts/$1"; }

case "$REACH" in
  none)
    say OK reach "none - Platform manages this site; no relay or outputs reader to re-check"
    exit 0 ;;
  local) ;;
  ssh)
    # With the master down every later call would wait on a one-time code that
    # Claude cannot supply, so stop here and show the line the user pastes.
    if ! out=$(bash "$HERE/on_site.sh" --check-reach 2>&1); then
      say FAIL reach "the master connection to $(setting site_host) is down"
      printf '%s\n' "$out"
      exit 1
    fi ;;
  *)
    say FAIL reach "unknown value '$REACH' - must be none, local or ssh (docs/SITE_ADAPTER.md)"
    exit 1 ;;
esac

out=$(bash "$HERE/on_site.sh" --script "$HERE/egress_ctl.sh" status 2>&1) \
  && say OK egress "$out" \
  || say FAIL egress "the site's egress channel is down ($(fix egress_ctl.sh) start)"
grep -q WARNING <<<"$out" && say FAIL egress-host "started somewhere else; the compute environment now points at the wrong address"

out=$(bash "$HERE/on_site.sh" --script "$HERE/agent_ctl.sh" status 2>&1) \
  && say OK agent "$out" \
  || say FAIL agent "not running - Platform will show no outputs ($(fix agent_ctl.sh) start)"

exit $fail
