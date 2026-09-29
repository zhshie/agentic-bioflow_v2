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
#
# #29: options may sit between the program and its verb - `tw -o json launch`,
# `tw --url=... runs relaunch`, `nextflow -bg run`, `nextflow -c x run` - and
# the first version required the verb to follow immediately, so each of those
# passed silently. Any tokens may now come between. And
# scripts/relaunch_with_override.sh --confirm runs `tw runs cancel` + `tw runs
# relaunch` itself, where this gate cannot see them, so the wrapper's own
# --confirm is the launch; without --confirm it only prints its plan.
LAUNCH_TRIGGER_RE='(^|[^[:alnum:]_.-])(tw(\.exe)?([[:space:]]+[^[:space:]]+)*[[:space:]]+(launch|runs[[:space:]]+relaunch)|sbatch|nextflow(\.exe)?([[:space:]]+[^[:space:]]+)*[[:space:]]+run|relaunch_with_override\.sh([[:space:]]+[^[:space:]]+)*[[:space:]]+--confirm)([[:space:]]|$)'
# The program in a variable (`$T launch x`, `"$TW" runs relaunch`), used only
# when the command word itself is a variable.
LAUNCH_VARPROG_RE='^[^[:space:]]+([[:space:]]+-[^[:space:]]+)*[[:space:]]+(launch|runs[[:space:]]+relaunch|run)([[:space:]]|$)'

# Commands that can only read. A segment naming a launch verb under one of
# these is a search or a page of documentation, not a submission.
LAUNCH_READONLY_RE='^[[:space:]]*(cat|less|more|head|tail|grep|rg|wc|chmod|shellcheck|ls|stat|file|diff|cp|vim|nano|echo)([[:space:]]|$)|^[[:space:]]*(bash|sh)[[:space:]]+-n([[:space:]]|$)'

is_launch_command() {
    local CMD="$1" STRIPPED SEGS S V US
    US=$(printf '\037')

    [ -n "$CMD" ] || return 1

    # Drop here-doc bodies first: a document that MENTIONS `tw launch` is not a
    # launch, and the segment scan below would otherwise treat prose as
    # commands. A body read by a shell or interpreter is kept - there it IS
    # the command (#29). If awk is missing this yields nothing and CMD is left
    # as-is.
    STRIPPED=$(printf '%s\n' "$CMD" | awk -f "$LAUNCH_TRIGGER_DIR/strip_heredocs.awk" 2>/dev/null)
    [ -n "$STRIPPED" ] && CMD="$STRIPPED"

    # What the command runs is decided by split_segments.awk, shared with
    # confirm_cleanup.sh (#29). Each line is `<segment>\037<segment without
    # quoted text>`. A quoted string is data - `grep -E 'a|sbatch|b' file` once
    # tripped this gate - so the verb is looked for in the quote-free copy. But
    # a string a shell re-reads (`bash -c "..."`, `ssh host '...'`,
    # `on_site.sh '...'`, `echo '...' | bash`, `python3 -c "os.system('...')"`)
    # and the inside of $(...), backticks and <(...) come back as segments of
    # their own, so a launch cannot hide in any of them - each of those shapes
    # once passed this gate with nothing printed (PITFALLS 37).
    #
    # If awk cannot run, the old rule applies: split on separators, strip
    # quotes. Weaker, but a gate rather than none.
    SEGS=$(printf '%s\n' "$CMD" | awk -f "$LAUNCH_TRIGGER_DIR/split_segments.awk" 2>/dev/null)
    if [ -z "$SEGS" ]; then
        SEGS=$(sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g" <<<"$CMD" | sed -E 's/(\|\||&&|[;&|])/\n/g' \
               | while IFS= read -r l; do printf '%s%s%s\n' "$l" "$US" "$l"; done)
    fi

    # Decided per segment, never for the whole line: `cat notes.txt && tw launch ...`
    # must still hit the gate.
    # In-shell matching only ([[ =~ ]]): a process per segment made this gate
    # take a minute on a long script under Git Bash, past its timeout, and a
    # timed-out hook lets the command run (#29, round 3).
    local SQ
    while IFS="$US" read -r S V W; do
        # A command nested too deeply to read is treated as one that might
        # launch - noisy, and correct for a gate that could not judge.
        [ "$W" = "__too_deep__" ] && return 0
        if ! [[ $V =~ $LAUNCH_TRIGGER_RE ]]; then
            # `"tw" launch x` quotes the program itself, so the quote-free copy
            # has lost it. When the command word IS a launcher, read the
            # segment with only the quote characters dropped. Only then: a
            # commit message quoting "tw launch" is still not a launch.
            SQ=${S//\"/}; SQ=${SQ//\'/}
            case "$W" in
                tw|nextflow|sbatch|relaunch_with_override.sh)
                    [[ $SQ =~ $LAUNCH_TRIGGER_RE ]] || continue ;;
                # `T=tw; $T launch x`: the program is a variable, and its first
                # argument is a launch verb.
                '$'*)
                    [[ $SQ =~ $LAUNCH_VARPROG_RE ]] || continue ;;
                *) continue ;;
            esac
        fi
        [[ $V =~ $LAUNCH_READONLY_RE ]] && continue
        return 0
    done <<< "$SEGS"

    return 1
}
