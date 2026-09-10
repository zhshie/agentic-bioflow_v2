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
#   WHY_PENDING_SCONTROL_BIN  override the scontrol binary (tests)
#   WHY_PENDING_SQUEUE_BIN    override the squeue binary (tests)
#
# Exit 3 means the scheduler's controller is down: no answer is available yet,
# which is not the same as "waiting" and not the same as "NEVER".
# GNU-ok-file: every path in here calls scontrol/squeue, so it only ever runs
# where SLURM is - a Linux site, reached through on_site.sh --script. It is
# never one of the scripts that runs on the user's own machine.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The box table, from the config that is its only copy - never retyped here.
. "$HERE/utils/boxes.sh"

SCONTROL="${WHY_PENDING_SCONTROL_BIN:-scontrol}"
SQUEUE="${WHY_PENDING_SQUEUE_BIN:-squeue}"

# The controller first, because it is the one question that is both instant and
# disqualifying. A slurmctld that has stopped answering does not make `squeue`
# fail - it makes it sit for tens of seconds on a reply that is not coming, and
# a site that appears to be thinking looks exactly like a site that is busy.
# `scontrol ping` answers either way in about 20 ms and names the controller's
# state outright, so the fast diagnosis comes before the slow one rather than
# after it. runs.md sends people here to ask whether a task will ever start; a
# controller that is down is a real answer to that, and a different one.
if ! command -v "$SCONTROL" >/dev/null 2>&1; then
    echo "scontrol not found: this is not the site this adapter describes." >&2
    echo "See docs/SITE_ADAPTER.md - 'why has this not started' is a per-site question." >&2
    exit 2
fi
ping_out=$(timeout 10 "$SCONTROL" ping 2>&1); ping_rc=$?
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
        DependencyNeverSatisfied*)
                            echo "NEVER - another job it was submitted to follow will not finish successfully." ;;
        Dependency*)        echo "waiting - held until another job it was submitted to follow finishes." ;;
        QOSGrp*|AssocGrp*)  echo "waiting - the whole account is at its cap, so what is ahead of this job is other work billed to the same account, not the partition." ;;
        QOSMax*|AssocMax*)  echo "waiting - you are at a submission limit; it will start as earlier jobs finish." ;;
        Resources)          echo "waiting - the partition is full." ;;
        Priority)           echo "waiting - other jobs are ahead." ;;
        PartitionTimeLimit) echo "NEVER - the time requested exceeds this partition's limit." ;;
        ReqNodeNotAvail*)   echo "NEVER (usually) - the nodes asked for are down or reserved." ;;
        # A reason with no rule is the one a reader most needs to see. The
        # empty string this used to return printed the job's fields with no
        # verdict under them, which reads exactly like a job that was looked
        # at and found fine. Measured 2026-09-09: 102 of 353 jobs pending
        # across the cluster sat on reasons that landed here.
        *)                  echo "no rule here for '$1' - this adapter has not seen that reason. It is the scheduler's own word: ask the site what it means, and see docs/SITE_ADAPTER.md for why this file is the only place that could know." ;;
    esac
}

# GB, rounded UP. Rounding a 53G request down by one would land it in the box
# below and read as advice to shrink into a floor it does not clear.
to_gb() {
    case "$2" in
        T|t) echo $(( $1 * 1024 )) ;;
        G|g) echo "$1" ;;
        K|k) echo $(( ($1 + 1048575) / 1048576 )) ;;
        *)   echo $(( ($1 + 1023) / 1024 )) ;;   # SLURM reports bare mem in MB
    esac
}

# Facts, deliberately not a recommendation.
#
# When a job is merely queued, the only lever that makes it start sooner is
# asking for a smaller box - the ngs partitions are one node pool wearing seven
# QOS-sized labels (docs/PITFALLS.md 6b), so "move to a quieter queue" is not a
# thing that exists here. But how far a given task can shrink is a fact about
# the tool and the data, and this script knows neither. Naming a number here
# would be guessing, and a guess that is low is an OOM rather than a slow job -
# so this prints the ladder and stops.
ladder() {   # ladder <ReqTRES> <partition>
    local req="$1" part="${2:-}" cpu=1 memgb=1 i pick=-1
    local -a qs cs ms hs
    [[ $req =~ (^|,)cpu=([0-9]+) ]]            && cpu="${BASH_REMATCH[2]}"
    [[ $req =~ (^|,)mem=([0-9]+)([KMGTkmgt]?) ]] && memgb=$(to_gb "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}")

    local q c m h
    while IFS=$'\t' read -r q c m h; do
        qs+=("$q"); cs+=("$c"); ms+=("$m"); hs+=("$h")
    done < <(nchc_boxes) || return 0
    [ "${#qs[@]}" -gt 0 ] || return 0

    # The ladder is a list of THIS site's boxes, so it answers only for a job
    # that is in one of them. Run against a job in another partition family it
    # named a box anyway - the same failure as PITFALLS 18b, where evidence was
    # counted without ever checking what it was evidence of. Another family has
    # its own floors and its own hardware, and none of that is written here.
    local known=0
    for i in "${!qs[@]}"; do [ "${qs[$i]}" = "$part" ] && { known=1; break; }; done
    if [ "$known" = 0 ]; then
        echo
        printf "   this job will start, but '%s' is not in this site's box table,\n" "$part"
        echo "   so there is no ladder here to offer it. The table covers one node pool"
        echo "   (docs/PITFALLS.md entry 6b); another partition family has its own floors"
        echo "   and its own hardware, and this adapter has measured neither."
        return 0
    fi

    # Same rule the config's nchcBox closure applies: smallest box that covers
    # both. Time is left out on purpose - a job already at Resources/Priority
    # has cleared the partition's time limit, so it cannot be what is binding.
    for i in "${!qs[@]}"; do
        if [ "${cs[$i]}" -ge "$cpu" ] && [ "${ms[$i]}" -ge "$memgb" ]; then pick=$i; break; fi
    done
    # No fallback to the largest box. This used to answer with it as the box
    # the job "lands in", which is not true of a request that overflows it -
    # and a wrong box number costs a whole queue wait to disprove.
    if [ "$pick" -lt 0 ]; then
        echo
        printf '   no box here holds cpu=%s / %s GB - the request is above the largest.\n' "$cpu" "$memgb"
        echo "   Nothing below can be offered, because nothing above it exists to shrink"
        echo "   from. What this task actually needs is a question about the tool and the"
        echo "   data; apply an answer with scripts/relaunch_with_override.sh."
        return 0
    fi

    echo
    echo "   this job will start; the only lever that makes it start sooner is a smaller box."
    echo "   ReqTRES: $req"
    printf '   lands in: %s (%s cpu / %s GB)\n' "${qs[$pick]}" "${cs[$pick]}" "${ms[$pick]}"
    if [ "$pick" = 0 ]; then
        printf '   %s is already the smallest box here - there is nothing below it.\n' "${qs[$pick]}"
    else
        echo "   boxes below it:"
        for (( i = pick - 1; i >= 0; i-- )); do
            if [ "${hs[$i]}" = 0 ]; then
                printf '     %-8s %2s cpu / %3s GB   no time limit\n' "${qs[$i]}" "${cs[$i]}" "${ms[$i]}"
            else
                printf '     %-8s %2s cpu / %3s GB   max %s h\n' "${qs[$i]}" "${cs[$i]}" "${ms[$i]}" "${hs[$i]}"
            fi
        done
    fi
    echo "   Every ngs partition is backed by the same node pool, so a smaller box is not"
    echo "   a quieter queue: more of them fit per node, so one starts sooner. See"
    echo "   docs/PITFALLS.md entry 6b."
    echo "   How far THIS task can shrink depends on the tool and the data, which this"
    echo "   script cannot know - and a request that is too small is an OOM, not a slow"
    echo "   job. Pick the size yourself, then apply it with scripts/relaunch_with_override.sh."
}

if [ $# -ge 1 ]; then
    # Fetched once and parsed from the variable: the old form asked the
    # controller twice for the same job, and the two answers could disagree.
    job=$("$SCONTROL" show job "$1" 2>/dev/null)
    [ -n "$job" ] || { echo "no such job: $1" >&2; exit 1; }
    fields=$(printf '%s\n' "$job" | tr ' ' '\n')
    grep -E '^(JobId|JobName|Partition|JobState|Reason|ReqTRES|TimeLimit)=' <<<"$fields" \
        || { echo "no such job: $1" >&2; exit 1; }

    r=$(sed -n 's/^Reason=//p' <<<"$fields" | head -1)
    [ -n "$r" ] && { e=$(explain "$r"); [ -n "$e" ] && echo "-> $e"; }

    # Only for the reasons that mean "eventually". A QOSMin* job is stranded
    # BELOW a floor, so offering it smaller boxes would point the wrong way
    # down the ladder and strand it harder.
    case "$r" in
        Resources|Priority|QOSGrp*|AssocGrp*)
            ladder "$(sed -n 's/^ReqTRES=//p' <<<"$fields" | head -1)" \
                   "$(sed -n 's/^Partition=//p' <<<"$fields" | head -1)" ;;
    esac
    exit 0
fi

found=0
while read -r id reason name; do
    found=1
    printf '%s  %-28s %s\n' "$id" "$reason" "$name"
    e=$(explain "$reason"); [ -n "$e" ] && printf '   -> %s\n' "$e"
done < <("$SQUEUE" -u "$USER" -h -t PENDING -o "%i %r %j" 2>/dev/null)

[ "$found" = 0 ] && echo "nothing pending for $USER"
exit 0
