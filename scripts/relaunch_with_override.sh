#!/bin/bash
# Give one process a smaller box and relaunch onto the cache.
#
#   relaunch_with_override.sh [--dry-run] [--confirm] <run-id> <process> <cpus> <mem-gb>
#
# An nf-core process asks for the box its LABEL names, not the box its data
# needs: process_high is 8 cpu / 53 GB, and a 6.5 Mb bacterial assembly does not
# need it. Here a partition is a fixed-size box (docs/PITFALLS.md 6), and every
# ngs partition is the same 46-node pool (6b), so an oversized request does not
# get better hardware - it just needs more of one node free at once, and queues
# behind everyone else's big jobs.
#
# The obvious fix is to resize the queued job. That is not available here:
# `scontrol update` is refused outright for an ordinary user, even for a rename
# (docs/PITFALLS.md 6c). So the only route is cancel + relaunch, and the cost is
# one more spell in the queue rather than the pipeline over again - `tw runs
# relaunch` resumes by default and the finished tasks come back from cache.
#
# What this script does NOT do is decide the numbers. How far a task can shrink
# is a fact about the tool and the data, and a number that is too low is an OOM
# rather than a slow job. `scripts/why_pending.sh <jobid>` prints the ladder;
# the human picks the rung. This script is only steps 2-4 of what was being
# done by hand: write the config, cancel, relaunch.
#
#   --confirm   actually cancel and relaunch. Without it this prints the plan
#               and exits non-zero, having touched no run. That is the same
#               gate the launch hook asks 確認執行 for.
#   --dry-run   print every command it would run and execute none. Writes
#               nothing at all.
#
# Environment (all optional; each overrides the deployment setting):
#   TW_BIN, TOWER_WORKSPACE_ID, TOWER_ACCESS_TOKEN, SEQERA_TOKEN_FILE,
#   RELAUNCH_OVERRIDE_DIR, NCHC_SITE_CONFIG
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
. "$HERE/settings.sh"
# The box table, from the config that is its only copy - never retyped here.
. "$HERE/utils/boxes.sh"

usage() {
    # Read out of the header above rather than restated, so the two cannot
    # disagree - and matched on its text, not on a line number, because a line
    # number silently starts printing the blank comment beside it.
    grep -m1 -o 'relaunch_with_override\.sh \[--dry-run\].*' "${BASH_SOURCE[0]}" \
        | sed 's/^/usage: /'
    echo "  --confirm   cancel and relaunch for real"
    echo "  --dry-run   print the commands, run none, write nothing"
}

DRY=0; CONFIRM=0
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY=1; shift ;;
        --confirm) CONFIRM=1; shift ;;
        -h|--help) usage; exit 0 ;;
        --) shift; break ;;
        -*) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
        *)  break ;;
    esac
done
[ $# -eq 4 ] || { usage >&2; exit 2; }
RUN="$1"; PROC="$2"; CPUS="$3"; MEM="$4"

[[ $CPUS =~ ^[0-9]+$ ]] && [ "$CPUS" -gt 0 ] \
    || { echo "cpus must be a positive whole number, got '$CPUS'" >&2; exit 2; }
[[ $MEM =~ ^[0-9]+$ ]] && [ "$MEM" -gt 0 ] \
    || { echo "mem-gb must be a positive whole number of GB, got '$MEM'" >&2; exit 2; }
# The name goes inside a single-quoted Nextflow selector, so a quote in it would
# not merely fail - it would produce a config that parses as something else.
case "$PROC" in
    *"'"*|*'\'*|"") echo "process name cannot contain a quote or backslash: '$PROC'" >&2; exit 2 ;;
esac

SITE_CONFIG="${NCHC_SITE_CONFIG:-$ROOT/configs/sites/nchc.config}"
TW="${TW_BIN:-$(setting tw_bin)}"; [ -n "$TW" ] || TW="$(command -v tw 2>/dev/null)"
WS="${TOWER_WORKSPACE_ID:-$(setting workspace_id)}"
TOKEN_FILE="$(token_file)"

# --- where the plan is kept --------------------------------------------------
# In the run area, never /tmp: this file is the record of what was changed and
# why, and someone has to be able to read it next week next to the run it
# belongs to. Named for the run, the process and the numbers, with a timestamp,
# so a second attempt at the same process does not erase the first.
OVERRIDE_DIR="${RELAUNCH_OVERRIDE_DIR:-${LAB_RUNS_DIR:+${LAB_RUNS_DIR%/}/_overrides}}"
if [ -z "$OVERRIDE_DIR" ]; then
    echo "LAB_RUNS_DIR is not set, so there is nowhere in the run area to keep" >&2
    echo "the override. Set it (see commands/setup.md) or point" >&2
    echo "RELAUNCH_OVERRIDE_DIR at the run area by hand." >&2
    exit 1
fi
SAFE_PROC="$(printf '%s' "$PROC" | tr -c 'A-Za-z0-9_.-' '_')"
CFG="$OVERRIDE_DIR/${RUN}-${SAFE_PROC}-${CPUS}c${MEM}G-$(date +%Y%m%dT%H%M%S).config"

# --- which box do these numbers land in? -------------------------------------
# The same rule the config's own nchcBox closure applies: the smallest box that
# covers both. Time is left out - this changes cpus and memory only, so whatever
# time the process asks for is unchanged and cannot start binding now.
BOX_Q=""; BOX_C=""; BOX_M=""
while IFS=$'\t' read -r _q _c _m _h; do
    if [ "$_c" -ge "$CPUS" ] && [ "$_m" -ge "$MEM" ]; then
        BOX_Q="$_q"; BOX_C="$_c"; BOX_M="$_m"; break
    fi
done < <(nchc_boxes "$SITE_CONFIG" 2>/dev/null)
if [ -n "$BOX_Q" ]; then
    BOX_NOTE="lands in $BOX_Q ($BOX_C cpu / $BOX_M GB)"
else
    BOX_NOTE="box unknown: the table in $SITE_CONFIG could not be read"
fi

# --- the config ---------------------------------------------------------------
# Why a withName block is enough to move the box: `tw launch --config` is
# ADDITIVE. Platform appends this file after the compute environment's own
# config (docs/PITFALLS.md 5), so `withName:'PROC'` here outranks whatever
# withLabel the pipeline gave that process. The site config's `withName: '.*'`
# closures then re-derive queue and clusterOptions from task.cpus/task.memory -
# which are now these values. Set the two numbers and the partition follows;
# there is deliberately nothing to say about the queue here.
read -r -d '' CFG_TEXT <<EOF
// Resource override for run $RUN, written $(date '+%Y-%m-%d %H:%M:%S %z')
// by scripts/relaunch_with_override.sh.
//
// $PROC asks for the box its nf-core label names, which is bigger than this
// data needs. On this site a partition is a fixed-size box, so the oversized
// request queues behind everyone else's big jobs (docs/PITFALLS.md 6, 6b).
//
// This is enough to move it because \`tw launch --config\` is additive: Platform
// appends this file AFTER the compute environment's own config (PITFALLS 5), so
// this withName block outranks the pipeline's withLabel, and the site config's
// \`withName: '.*'\` closures then re-derive queue and clusterOptions from these
// values. Do not set queue or clusterOptions here - they follow from the two
// numbers below.
//
// $BOX_NOTE
process {
    withName: '$PROC' {
        cpus   = $CPUS
        memory = ${MEM}.GB
    }
}
EOF

echo "run:       $RUN"
echo "process:   $PROC"
echo "override:  $CPUS cpu / $MEM GB"
if [ -n "$BOX_Q" ]; then
    echo "lands in:  $BOX_Q ($BOX_C cpu / $BOX_M GB)"
    if [ "$BOX_C" != "$CPUS" ] || [ "$BOX_M" != "$MEM" ]; then
        echo "           note: a box is fixed-size, so SLURM is asked for the box's own"
        echo "           $BOX_C cpu / $BOX_M GB. The process still sees task.cpus = $CPUS."
    fi
else
    echo "lands in:  UNKNOWN - could not read the box table from"
    echo "           $SITE_CONFIG"
    echo "           The numbers below are unchecked against this site's partitions."
fi
echo "config:    $CFG"
echo
printf '%s\n' "$CFG_TEXT"
echo

# --- the warning this repo's config earns ------------------------------------
# Quoted from the config itself rather than restated, so the day that intent
# changes this stops saying it. If the file cannot be read, say plainly that the
# warning could not be quoted - never paraphrase it from memory.
echo "Before you confirm - a retry will NOT get more memory than this:"
echo
QUOTE=$(sed -n '/Deliberately no task.attempt multiplier/,/^[[:space:]]*[^\/[:space:]]/p' "$SITE_CONFIG" 2>/dev/null \
        | sed -n 's|^[[:space:]]*//|  |p')
if [ -n "$QUOTE" ]; then
    printf '%s\n' "$QUOTE"
else
    # An empty quote means the comment moved, was reworded, or - worst - the
    # multiplier came back. Any of those makes the sentence below wrong, so say
    # so rather than assert it from memory.
    echo "  (could not quote $SITE_CONFIG - check by hand that it still carries"
    echo "   no task.attempt multiplier on cpus/memory before relying on a retry.)"
fi
echo
echo "   So if $CPUS cpu / $MEM GB is too small, the task OOMs and the retry dies"
echo "   the same way. Too small costs two failures; too big only costs queue time."
echo

# --- do it -------------------------------------------------------------------
say_cmd() { printf '   %s\n' "$*"; }

if [ "$DRY" = 1 ]; then
    echo "--dry-run: nothing was written and nothing was called. Would run:"
    say_cmd "write $CFG"
    say_cmd "$TW runs view -i $RUN ${WS:+-w $WS}"
    say_cmd "$TW runs cancel -i $RUN ${WS:+-w $WS}      # only if RUNNING or SUBMITTED"
    say_cmd "$TW runs relaunch -i $RUN ${WS:+-w $WS} --config $CFG"
    echo "   (the token is passed through the environment, never as an argument)"
    exit 0
fi

mkdir -p "$OVERRIDE_DIR" || exit 1
printf '%s\n' "$CFG_TEXT" > "$CFG" || exit 1

if [ "$CONFIRM" != 1 ]; then
    echo "Nothing has been cancelled or relaunched. The plan above is saved at"
    echo "   $CFG"
    echo
    echo "Show it to the user - the numbers are a judgement call and this script"
    echo "cannot make it - and only then run again with --confirm:"
    echo
    say_cmd "scripts/relaunch_with_override.sh --confirm $RUN $PROC $CPUS $MEM"
    exit 1
fi

[ -n "$TW" ] && [ -x "$TW" ] || { echo "no usable tw: '$TW' (set tw_bin or TW_BIN)" >&2; exit 1; }
if [ -n "${TOWER_ACCESS_TOKEN:-}" ]; then
    TOKEN="$TOWER_ACCESS_TOKEN"
elif [ -r "$TOKEN_FILE" ]; then
    TOKEN="$(cat "$TOKEN_FILE")"
else
    echo "no Seqera token: looked at $TOKEN_FILE" >&2; exit 1
fi

# The token goes through the environment only - never on the command line, where
# `ps` would show it to every user on a shared login node.
tw_do() { TOWER_ACCESS_TOKEN="$TOKEN" "$TW" "$@"; }

# Ask what state the run is in BEFORE touching it. `tw runs cancel` on a run
# that is already CANCELLED (or finished) is an error, and that is the normal
# case here: a stalled run is usually cancelled by hand first, then diagnosed.
echo "asking Platform what state this run is in:"
say_cmd "$TW runs view -i $RUN ${WS:+-w $WS}"
view=$(tw_do runs view -i "$RUN" ${WS:+-w "$WS"} 2>&1); view_rc=$?
STATUS=$(sed -n 's/.*Status[^A-Za-z]*\([A-Z_]\{3,\}\).*/\1/p' <<<"$view" | head -1)
if [ "$view_rc" != 0 ] || [ -z "$STATUS" ]; then
    printf '%s\n' "$view" >&2
    echo "-> could not read the run's status, so it is not known whether cancelling" >&2
    echo "   is required or an error. Relaunching blind would leave two runs" >&2
    echo "   competing for the same queue. Check the run in Platform first." >&2
    exit 1
fi
echo "status:    $STATUS"

case "$STATUS" in
    RUNNING|SUBMITTED)
        echo "-> $STATUS, so it holds a place in the queue under the old request; cancelling first."
        say_cmd "$TW runs cancel -i $RUN ${WS:+-w $WS}"
        tw_do runs cancel -i "$RUN" ${WS:+-w "$WS"} || {
            echo "cancel failed; not relaunching on top of a run that may still be live." >&2
            exit 1; }
        ;;
    *)
        echo "-> already $STATUS, so there is nothing to cancel; cancelling it again is an error."
        ;;
esac

# resume is the default and is the whole point: the finished tasks come back
# from cache, so this costs one spell in the queue, not the pipeline again.
echo
say_cmd "$TW runs relaunch -i $RUN ${WS:+-w $WS} --config $CFG"
out=$(tw_do runs relaunch -i "$RUN" ${WS:+-w "$WS"} --config "$CFG" 2>&1); rc=$?
printf '%s\n' "$out"
[ "$rc" = 0 ] || { echo "relaunch failed (exit $rc)." >&2; exit 1; }

url=$(grep -Eo 'https?://[^[:space:]]+' <<<"$out" | head -1)
new=$(sed -n 's/.*[Ww]orkflow[^A-Za-z0-9]*\([A-Za-z0-9]\{10,\}\).*/\1/p' <<<"$out" | head -1)
[ -n "$new" ] || new="${url##*/}"
echo
if [ -n "$new" ]; then echo "new run:   $new"; fi
if [ -n "$url" ]; then echo "watch:     $url"; fi
if [ -z "$new" ] && [ -z "$url" ]; then
    echo "relaunched, but tw printed no run id or URL - see its output above."
fi
echo
echo "It resumed, so the finished tasks come back from cache. If $PROC still"
echo "sits pending, ask why with scripts/why_pending.sh <jobid> before shrinking again."
