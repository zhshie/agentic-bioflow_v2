#!/bin/bash
# The check a background watch (launch.md step 9) is missing if it only polls
# the run's aggregate status. Platform reports RUNNING for the whole time a
# single task sits unstarted - runs.md already says to catch this by hand
# with `tw runs view tasks` + why_pending.sh; this is that same check as one
# command, so a Monitor loop (or anyone re-running it) gets the escalation
# automatically instead of only on request.
#
#   task_health.sh <run-id> [workspace]
#
# Prints one line and always exits 0 (this reports a status, it does not
# pass/fail):
#   OK: <n> running, <n> queued
#   STUCK: <reason from why_pending.sh>
#   STUCK (why_pending unreachable: <detail>)     - still worth surfacing;
#                                                    on_site.sh sessions can
#                                                    themselves be exhausted
#                                                    (PITFALLS 16e)
# Exit 2 only for a usage or settings error - nothing about the run itself.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

RUN_ID="${1:?usage: task_health.sh <run-id> [workspace]}"
WS="${2:-}"
if [ -z "$WS" ]; then
    WS="$(setting workspace_id --required)" || exit 2
fi
TW="$(setting tw_bin tw)"

TOKEN_FILE="${SEQERA_TOKEN_FILE:-$(dirname "$SETTINGS_FILE")/.seqera_token}"
if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && [ -r "$TOKEN_FILE" ]; then
    TOWER_ACCESS_TOKEN="$(cat "$TOKEN_FILE")"
    export TOWER_ACCESS_TOKEN
fi

out=$("$TW" runs view -i "$RUN_ID" --workspace "$WS" tasks 2>&1) \
    || { echo "ERROR: could not read tasks - $out" >&2; exit 2; }

running=0 pending=0
while IFS='|' read -r _ _ _ status; do
    case "$(xargs <<<"${status:-}")" in
        RUNNING)             running=$((running + 1)) ;;
        PENDING|SUBMITTED)   pending=$((pending + 1)) ;;
    esac
done <<<"$out"

# The pattern, not the wait: nothing running while something waits is what
# `tw runs view --status` alone cannot distinguish from ordinary progress.
if [ "$pending" -gt 0 ] && [ "$running" -eq 0 ]; then
    why=$(timeout 40 bash "$HERE/on_site.sh" --script "$HERE/why_pending.sh" 2>&1)
    if [ -n "$why" ]; then
        echo "STUCK: $why"
    else
        echo "STUCK (why_pending unreachable: timed out or gave no reason)"
    fi
else
    echo "OK: $running running, $pending queued"
fi
