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
#   STUCK: <the why_pending lines for THIS run's own jobs>
#   STUCK: ... no pending job carries one of this run's process names ...
#          - the account is shared, so other members' waiting jobs are not
#            evidence about this run (PITFALLS 18b)
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

# Which SLURM jobs could be this run's? Nextflow names a task's job
# nf-<process, with ':' replaced by '_'>_<tag>. Measured on this site:
#
#   process  NFCORE_AMPLISEQ:AMPLISEQ:BARRNAP
#   job      nf-NFCORE_AMPLISEQ_AMPLISEQ_BARRNAP__ASV_seqs.fasta_
#
# This matters because why_pending.sh's no-argument form is `squeue -u $USER`,
# and $USER here is one Unix account shared by every lab member - a second
# Seqera user is active in this same workspace today. Printing whatever it
# returns as this run's reason attributes someone else's queue position to a
# run it has nothing to do with, in the one line a background watch trusts.
# That is PITFALLS 18b: evidence whose subject was never checked.
#
# The narrowing is by pipeline process, not by run, and that is as far as the
# evidence goes: two concurrent runs of the same pipeline share these names.
# Said here rather than implied, so nobody reads more precision into it.
prefixes=$(awk -F'|' 'NF > 3 {
        p = $2; gsub(/^[ \t]+|[ \t]+$/, "", p)
        if (p != "" && p != "process" && p !~ /^-+$/) { gsub(/:/, "_", p); print "nf-" p }
    }' <<<"$out" | sort -u)

# The pattern, not the wait: nothing running while something waits is what
# `tw runs view --status` alone cannot distinguish from ordinary progress.
if [ "$pending" -gt 0 ] && [ "$running" -eq 0 ]; then
    why=$(timeout 40 bash "$HERE/on_site.sh" --script "$HERE/why_pending.sh" 2>&1)
    # why_pending prints "<id>  <reason>  <name>" and may follow it with an
    # indented "-> verdict" line, which belongs to the job above it.
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
        echo "STUCK: $mine"
    elif [ -n "$why" ]; then
        echo "STUCK: $pending queued, none running, and no pending job on the site" \
             "carries one of this run's process names. The account is shared, so the" \
             "other jobs waiting there are not evidence about this run - check whether" \
             "its tasks have been submitted at all."
    else
        echo "STUCK (why_pending unreachable: timed out or gave no reason)"
    fi
else
    echo "OK: $running running, $pending queued"
fi
