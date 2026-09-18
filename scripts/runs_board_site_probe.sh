#!/bin/bash
# T24's own site query, spun out as its own independently-runnable piece so
# the runs board never opens more than one on_site.sh session no matter how
# many runs it is showing - PITFALLS.md 16e's session cap is easy to reach
# exactly this way: one background watch per in-flight run, all polling
# on_site.sh in the same work session (docs/LAB_AGENTS.md, section 6).
#
# Not `task_health.sh`, called once per run: that already solves this
# correctly for ONE run (its own header explains why), but calling it N
# times for N runs opens N sessions on the same shared master - the thing
# this file exists to avoid. The trick generalises cleanly because
# `why_pending.sh`'s own no-argument form already answers for every pending
# job on the account in ONE round trip; this fetches that ONE snapshot and
# matches it against every run's own process-name prefixes locally, the
# same attribution rule PITFALLS.md 18b already established for a single
# run (a job on a shared account is not evidence about a run unless its own
# name says so).
#
# Not `scripts/on_site.sh --script`'s own future batching (perf/latency is
# adding a way to run a whole GROUP of checks in one round trip - see that
# branch's work on scripts/on_site.sh): until that lands, this file already
# gets to "one round trip for N runs" on its own, by making exactly one
# on_site.sh call regardless of how many run ids are passed in. Once the
# batching exists, this file's one call is a natural candidate to fold into
# whatever group `on_site.sh --script` runs for a work session - only the
# one call at the bottom of this file would need to move; nothing about its
# interface (a list of run ids in, one status line per id out) has to
# change first. Do not edit on_site.sh from here to anticipate that -
# that work belongs to the branch already doing it.
#
#   runs_board_site_probe.sh <workspace> <run-id> [<run-id> ...]
#
# Exactly one line per run id given, in the order given - why_pending.sh's
# own multi-line "reason / -> verdict" pair is collapsed onto that one line,
# so a caller (scripts/runs_board.sh) can pair a line back to the run it is
# about with a plain read loop instead of a paragraph parser:
#   <run-id> OK
#   <run-id> STUCK: <why_pending's own reason line> layer=scheduler
#   <run-id> STUCK: unattributed - queued, no pending job on the site names
#            this run's own process layer=env
#   <run-id> STUCK: why_pending unreachable layer=env
#   <run-id> ?                      (no tasks reported, or tw could not answer)
#
# Always exits 0: this reports a status per run, the same contract
# task_health.sh already keeps - a caller building a board must not have the
# whole board fail because one site-side check could not be made.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

WS="${1:?usage: runs_board_site_probe.sh <workspace> <run-id> [<run-id> ...]}"
shift
if [ $# -lt 1 ]; then
    echo "usage: runs_board_site_probe.sh <workspace> <run-id> [<run-id> ...]" >&2
    exit 2
fi

TW="$(setting tw_bin tw)"
TOKEN_FILE="${SEQERA_TOKEN_FILE:-$(dirname "$SETTINGS_FILE")/.seqera_token}"
if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && [ -r "$TOKEN_FILE" ]; then
    TOWER_ACCESS_TOKEN="$(cat "$TOKEN_FILE")"
    export TOWER_ACCESS_TOKEN
fi

# One snapshot of the WHOLE account's pending jobs, exactly once, regardless
# of how many run ids follow - this single call is the thing this file
# exists to make true.
why=$(clocked 40 bash "$HERE/on_site.sh" --script "$HERE/why_pending.sh" 2>&1)

for RUN_ID in "$@"; do
    tasks=$("$TW" -o json runs view -i "$RUN_ID" --workspace "$WS" tasks 2>/dev/null)
    if [ -z "$tasks" ]; then
        echo "$RUN_ID ?"
        continue
    fi

    running=$(jq -r '[.[] | select(.status == "RUNNING")] | length' <<<"$tasks" 2>/dev/null)
    pending=$(jq -r '[.[] | select(.status == "PENDING" or .status == "SUBMITTED")] | length' <<<"$tasks" 2>/dev/null)
    case "$running" in ''|*[!0-9]*) running=0 ;; esac
    case "$pending" in ''|*[!0-9]*) pending=0 ;; esac

    if [ "$pending" -gt 0 ] && [ "$running" -eq 0 ]; then
        prefixes=$(jq -r '.[].process | select(. != null and . != "") | "nf-" + gsub(":";"_")' \
            <<<"$tasks" 2>/dev/null | sort -u)
        mine=$(awk -v pre="$prefixes" '
            BEGIN { n = split(pre, a, "\n") }
            /^[[:space:]]*->/ { if (keep) print; next }
            {
                keep = 0
                for (i = 1; i <= n; i++)
                    if (a[i] != "" && index($0, a[i]) > 0) { keep = 1; break }
                if (keep) print
            }' <<<"$why")
        if [ -n "$mine" ]; then
            mine_oneline=$(tr '\n' ' ' <<<"$mine" | tr -s '[:space:]' ' ' | sed -e 's/^ *//' -e 's/ *$//')
            echo "$RUN_ID STUCK: $mine_oneline layer=scheduler"
        elif [ -n "$why" ]; then
            echo "$RUN_ID STUCK: unattributed - queued, no pending job on the site names this run's own process layer=env"
        else
            echo "$RUN_ID STUCK: why_pending unreachable layer=env"
        fi
    else
        echo "$RUN_ID OK"
    fi
done
