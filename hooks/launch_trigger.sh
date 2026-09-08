# Sourceable helper: does this command string start a pipeline run?
#
#   . "$(dirname "$0")/launch_trigger.sh"
#   is_launch_command "$CMD" && ...      # 0 = yes, 1 = no
#
# This lives in its own file rather than inside confirm_launch.sh because more
# than one hook has to reach the same verdict, and the judgement is not one
# regex - it is a regex plus here-doc stripping, plus a quote rule with a
# deliberate exception, plus segment splitting, plus a read-only exemption. Two
# copies of that would agree on the day they were written and not much longer.
# This repo has already paid for that lesson once: scripts/on_site.sh used to
# carry a hand-written list of another script's dependencies, and the list went
# stale twice - silently, because nothing reminds you to update a copy kept in
# a different file from the thing it describes. So there is one copy here.
#
# The cost of getting this wrong runs in both directions. A miss means a real
# run starts unannounced; a false positive means the gate fires on `grep`, and
# a gate that cries wolf is one people learn to click through.

LAUNCH_TRIGGER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The verbs that start a run. `tw runs relaunch` is here for the same reason
# the other three are: it submits work to the cluster. It was missing for a
# while, and nothing reported the gap - a gate that does not fire prints
# nothing, so the hole looked exactly like a command that was correctly
# judged harmless.
#
# The leading boundary is any non-word character, not `^` or `/`. Anchoring to
# the start of a segment looked right and was not: splitting on `&&` leaves the
# leading space in place, so `cat notes.txt && tw launch ...` - the exact case
# this gate was written for - sailed through. A quoted `bash -c "tw launch ..."`
# missed for the same reason.
LAUNCH_TRIGGER_RE='(^|[^[:alnum:]_.-])(tw[[:space:]]+launch|tw[[:space:]]+runs[[:space:]]+relaunch|sbatch)([[:space:]]|$)|nextflow[[:space:]]+run'

# Commands that can only read. A segment naming a launch verb under one of
# these is a search or a page of documentation, not a submission.
LAUNCH_READONLY_RE='^[[:space:]]*(cat|less|more|head|tail|grep|rg|wc|chmod|shellcheck|ls|stat|file|diff|cp|vim|nano|echo)([[:space:]]|$)|^[[:space:]]*(bash|sh)[[:space:]]+-n([[:space:]]|$)'

# A nested shell re-interprets what it was handed, so quotes there are not a
# wrapper around data - they are a wrapper around a command line.
LAUNCH_NESTED_SHELL_RE='(^|[[:space:]])(bash|sh|zsh|ksh)[[:space:]]+-c([[:space:]]|$)|(^|[[:space:]])eval([[:space:]]|$)|(^|[[:space:]])([^[:space:]]*/)?(ssh|on_site\.sh)[[:space:]]'

is_launch_command() {
    local CMD="$1" STRIPPED SEGSRC S

    [ -n "$CMD" ] || return 1

    # Drop here-doc bodies first: a document that MENTIONS `tw launch` is not a
    # launch, and the segment scan below would otherwise treat prose as
    # commands. If awk is missing this yields nothing and CMD is left as-is.
    STRIPPED=$(printf '%s\n' "$CMD" | awk -f "$LAUNCH_TRIGGER_DIR/strip_heredocs.awk" 2>/dev/null)
    [ -n "$STRIPPED" ] && CMD="$STRIPPED"

    # A quoted string is data, not a command. `grep -E 'a|sbatch|b' file` used
    # to trip this gate: splitting on `|` turned the middle of a regex into a
    # segment that read exactly like a submission. Strip quoted content before
    # segmenting - but NOT where a shell is asked to re-interpret it, because
    # `bash -c "tw launch ..."` really does launch and the quotes would become
    # a hiding place.
    #
    # `ssh <host> '<payload>'` is the same thing across a network: a shell on
    # the far side re-interprets the quoted payload, so it belongs in that list
    # rather than in a separate unwrapping step. Without it the gate reads
    # `ssh host 'tw launch ...'` as `ssh host ` and lets a real launch through -
    # silently, and precisely when the deployment moves off the login node.
    # `on_site.sh` is this project's own sanctioned wrapper for the same thing.
    SEGSRC="$CMD"
    if ! grep -qE "$LAUNCH_NESTED_SHELL_RE" <<<"$CMD"; then
        SEGSRC=$(sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g" <<<"$CMD")
    fi

    # Decided per segment, never for the whole line: `cat notes.txt && tw launch ...`
    # must still hit the gate.
    while IFS= read -r S; do
        echo "$S" | grep -qE "$LAUNCH_TRIGGER_RE" || continue
        echo "$S" | grep -qE "$LAUNCH_READONLY_RE" && continue
        return 0
    done <<< "$(echo "$SEGSRC" | sed -E 's/(\|\||&&|[;&|])/\n/g')"

    return 1
}
