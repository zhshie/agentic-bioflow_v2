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
set -uo pipefail

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
