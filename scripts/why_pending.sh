#!/bin/bash
# Why has this task not started? (NCHC site adapter - see docs/SITE_ADAPTER.md)
#
# A task can sit unstarted indefinitely while Seqera Platform reports the run
# as RUNNING and nothing anywhere records an error. The distinction that
# matters is not "how long has it waited" but "will it EVER start": a request
# below a partition's QOS floor is refused forever, and looks exactly like a
# busy queue.
#
#   why_pending.sh            all of this user's pending jobs
#   why_pending.sh <jobid>    one job, with its full request
#
# Exit 3 means the scheduler's controller is down: no answer is available yet,
# which is not the same as "waiting" and not the same as "NEVER".
set -uo pipefail

# The controller first, because it is the one question that is both instant and
# disqualifying. A slurmctld that has stopped answering does not make `squeue`
# fail - it makes it sit for tens of seconds on a reply that is not coming, and
# a site that appears to be thinking looks exactly like a site that is busy.
# `scontrol ping` answers either way in about 20 ms and names the controller's
# state outright, so the fast diagnosis comes before the slow one rather than
# after it. runs.md sends people here to ask whether a task will ever start; a
# controller that is down is a real answer to that, and a different one.
if ! command -v scontrol >/dev/null 2>&1; then
    echo "scontrol not found: this is not the site this adapter describes." >&2
    echo "See docs/SITE_ADAPTER.md - 'why has this not started' is a per-site question." >&2
    exit 2
fi
ping_out=$(timeout 10 scontrol ping 2>&1); ping_rc=$?
if [ "$ping_rc" != 0 ] || ! grep -q 'is UP' <<<"$ping_out"; then
    printf '%s\n' "$ping_out" >&2
    echo "-> the scheduler's controller is not answering, so nothing below can be" >&2
    echo "   established: squeue would hang rather than say so. A run that looks" >&2
    echo "   stuck right now is stuck on the site, not on its own request." >&2
    echo "   Queued jobs survive this. Wait for the controller and ask again." >&2
    exit 3
fi

explain() {
    case "$1" in
        QOSMin*)            echo "NEVER - the request is below this partition's floor. Fix the config, not the wait." ;;
        QOSMax*|AssocMax*)  echo "waiting - you are at a submission limit; it will start as earlier jobs finish." ;;
        Resources)          echo "waiting - the partition is full." ;;
        Priority)           echo "waiting - other jobs are ahead." ;;
        PartitionTimeLimit) echo "NEVER - the time requested exceeds this partition's limit." ;;
        ReqNodeNotAvail*)   echo "NEVER (usually) - the nodes asked for are down or reserved." ;;
        *)                  echo "" ;;
    esac
}

if [ $# -ge 1 ]; then
    scontrol show job "$1" 2>/dev/null | tr ' ' '\n' \
        | grep -E '^(JobId|JobName|Partition|JobState|Reason|ReqTRES|TimeLimit)=' \
        || { echo "no such job: $1" >&2; exit 1; }
    r=$(scontrol show job "$1" 2>/dev/null | tr ' ' '\n' | sed -n 's/^Reason=//p')
    [ -n "$r" ] && { e=$(explain "$r"); [ -n "$e" ] && echo "-> $e"; }
    exit 0
fi

found=0
while read -r id reason name; do
    found=1
    printf '%s  %-28s %s\n' "$id" "$reason" "$name"
    e=$(explain "$reason"); [ -n "$e" ] && printf '   -> %s\n' "$e"
done < <(squeue -u "$USER" -h -t PENDING -o "%i %r %j" 2>/dev/null)

[ "$found" = 0 ] && echo "nothing pending for $USER"
exit 0
