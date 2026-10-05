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

# The directory this file is in, with no process (#34: `cd`, `dirname` and a
# subshell for it cost three). It is only ever used to find the .awk files beside
# it, so a relative spelling is as good as an absolute one; it is made absolute
# against $PWD in case the caller changes directory later.
LAUNCH_TRIGGER_DIR="${BASH_SOURCE[0]%/*}"
[ "$LAUNCH_TRIGGER_DIR" = "${BASH_SOURCE[0]}" ] && LAUNCH_TRIGGER_DIR=.
case "$LAUNCH_TRIGGER_DIR" in /*|[A-Za-z]:*) ;; *) LAUNCH_TRIGGER_DIR="$PWD/$LAUNCH_TRIGGER_DIR" ;; esac

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
#
# launch-shapes-unconfirmed: three more verbs that start a run - `tw actions
# trigger` (a Platform action launches its pipeline), `nextflow kuberun`, and
# nf-core's launcher (`nf-core launch`, `nf-core pipelines launch`: its wizard
# ends in `nextflow run`).
LAUNCH_TRIGGER_RE='(^|[^[:alnum:]_.-])(tw(\.exe)?([[:space:]]+[^[:space:]]+)*[[:space:]]+(launch|runs[[:space:]]+relaunch|actions[[:space:]]+trigger)|sbatch|nextflow(\.exe)?([[:space:]]+[^[:space:]]+)*[[:space:]]+(run|kuberun)|nf-core(\.exe)?([[:space:]]+[^[:space:]]+)*[[:space:]]+launch|relaunch_with_override\.sh([[:space:]]+[^[:space:]]+)*[[:space:]]+--confirm)([[:space:]]|$)'
# The program in a variable (`$T launch x`, `"$TW" runs relaunch`), used only
# when the command word itself is a variable.
LAUNCH_VARPROG_RE='^[^[:space:]]+([[:space:]]+-[^[:space:]]+)*[[:space:]]+(launch|runs[[:space:]]+relaunch|actions[[:space:]]+trigger|run|kuberun)([[:space:]]|$)'

# seqerakit runs `tw` for every resource in the YAML it is given, launches
# included. A run of it with a YAML file (or `-`, stdin) starts whatever that
# file says; `--dryrun` / `-d` only prints the commands (seqerakit's cli.py).
LAUNCH_SEQERAKIT_RE='(^|[^[:alnum:]_.-])seqerakit(\.exe)?([[:space:]]+[^[:space:]]+)*[[:space:]]+([^[:space:]]*\.[Yy][Aa]?[Mm][Ll]|-)([[:space:]]|$)'
LAUNCH_SEQERAKIT_WORD_RE='(^|[^[:alnum:]_.-])seqerakit(\.exe)?([[:space:]]|$)'
LAUNCH_SEQERAKIT_DRY_RE='(^|[[:space:]])(--dryrun|-d)([[:space:]]|$)'

# The Platform API's own launch endpoint: POST /workflow/launch, and POST
# /actions/<id>/launch for an action. An HTTP client or a code call outside
# quotes, a path ending in /launch (read with quotes dropped - a URL is usually
# quoted), and a POST: the word itself in any case (-X POST, --post-data,
# requests.post(, method="POST", -Method Post) or a body flag that makes curl
# POST. A GET of /workflow/<id>/launch only describes a launch and stays quiet.
LAUNCH_HTTP_CLIENT_RE='(^|[^[:alnum:]_.-])(curl|wget|http|https|xh|xhs|httpie|[Ii]nvoke-[Ww]eb[Rr]equest|[Ii][Ww][Rr]|[Ii]nvoke-[Rr]est[Mm]ethod|[Ii][Rr][Mm])(\.exe)?([[:space:]]|$)|\.(post|request)[[:space:]]*\(|(^|[^[:alnum:]_.])(fetch|urlopen|Request)[[:space:]]*\('
LAUNCH_HTTP_PATH_RE='/launch([^[:alnum:]_-]|$)'
LAUNCH_HTTP_POST_RE='(^|[^[:alnum:]_])[Pp][Oo][Ss][Tt]([^[:alnum:]_]|$)|(^|[[:space:]])(-d|--data[^[:space:]]*|--json|-F|--form[^[:space:]]*)([^[:alpha:]-]|$)'

# A nested shell anywhere on the line. main's rule, kept as a floor (#29,
# round 4): when a shell re-reads part of this line, quoted text inside it is
# a command, even when it is handed on again to something the splitter does
# not know runs commands - `ssh h "tmux new -d 'nextflow run …'"`,
# `su -c '…'`, `flock l -c '…'`.
LAUNCH_NESTED_SHELL_RE='(^|[[:space:]])(bash|sh|zsh|ksh|dash)([[:space:]]+-[^[:space:]]+)*[[:space:]]+-[[:alpha:]]*c([[:space:]]|$)|(^|[[:space:]])eval([[:space:]]|$)|(^|[[:space:]])([^[:space:]]*/)?(ssh|on_site\.sh)[[:space:]]|\|&?[[:space:]]*([^[:space:]|]*/)?(bash|sh|zsh|dash|ksh)([[:space:]]|$)'

# Commands that can only read. A segment naming a launch verb under one of
# these is a search or a page of documentation, not a submission.
LAUNCH_READONLY_RE='^[[:space:]]*(cat|less|more|head|tail|grep|rg|wc|chmod|shellcheck|ls|stat|file|diff|cp|vim|nano|echo)([[:space:]]|$)|^[[:space:]]*(bash|sh)[[:space:]]+-n([[:space:]]|$)'

is_launch_command() {
    local CMD="$1" STRIPPED SEGS S V US
    US=$'\037'

    [ -n "$CMD" ] || return 1

    # Drop here-doc bodies first: a document that MENTIONS `tw launch` is not a
    # launch, and the segment scan below would otherwise treat prose as
    # commands. A body read by a shell or interpreter is kept - there it IS
    # the command (#29). If awk is missing this yields nothing and CMD is left
    # as-is.
    # #34: with no `<<` there is no here-doc, and the stripper then prints every
    # line unchanged - so the process is not started for it.
    # #62: a caller that already stripped and split exactly this command
    # (confirm_launch.sh's allowlist check) leaves the result here, so a big
    # command is not run through both awk passes twice.
    if [ -n "${ABF_SPLIT_SEGS-}" ] && [ "${ABF_SPLIT_FOR-}" = "$1" ]; then
        [ -n "${ABF_SPLIT_STRIPPED-}" ] && CMD=$ABF_SPLIT_STRIPPED
        SEGS=$ABF_SPLIT_SEGS
    else
        if [[ $CMD == *'<<'* ]]; then
            STRIPPED=$(awk -f "$LAUNCH_TRIGGER_DIR/strip_heredocs.awk" <<<"$CMD" 2>/dev/null)
            [ -n "$STRIPPED" ] && CMD="$STRIPPED"
        fi

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
        SEGS=$(awk -f "$LAUNCH_TRIGGER_DIR/split_segments.awk" <<<"$CMD" 2>/dev/null)
        # Kept for a caller that has to read the same segments of the same command
        # next (confirm_launch.sh's D3), so the splitter is started once per call
        # rather than once per question (#34). Only the splitter's own answer is kept,
        # never the fallback below.
        ABF_SPLIT_FOR="$1"; ABF_SPLIT_SEGS="$SEGS"; ABF_SPLIT_STRIPPED="$CMD"
    fi
    if [ -z "$SEGS" ]; then
        SEGS=$(sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g" <<<"$CMD" | sed -E 's/(\|\||&&|[;&|])/\n/g' \
               | while IFS= read -r l; do printf '%s%s%s\n' "$l" "$US" "$l"; done)
    fi

    # #62: a big command (a here-doc body python reads is thousands of segments)
    # is first cut down by one awk pass to the segments the loop below could act
    # on: the same test as the loop's own first one, on the same two texts. Under
    # Git Bash a shell `read` loop over thousands of lines is superlinear and ran
    # past the hook's timeout; awk is linear. If awk cannot run, every segment
    # goes through the loop as before.
    local CAND
    if [ "${#SEGS}" -gt 16384 ]; then
        CAND=$(awk -F"$US" '$3 == "__too_deep__" { print; next }
            { s = $1; gsub(/["\047]/, "", s); t = s "\037" $2
              if (index(t, "launch") || index(t, "sbatch") || index(t, "run") || index(t, "--confirm") || index(t, "trigger") || index(t, "seqerakit")) print }' \
            <<<"$SEGS" 2>/dev/null) && SEGS=$CAND
    fi

    # Decided per segment, never for the whole line: `cat notes.txt && tw launch ...`
    # must still hit the gate.
    # In-shell matching only ([[ =~ ]]): a process per segment made this gate
    # take a minute on a long script under Git Bash, past its timeout, and a
    # timed-out hook lets the command run (#29, round 3).
    local SQ SQP SQW HIT NESTED=-1
    while IFS="$US" read -r S V W; do
        # A command nested too deeply to read is treated as one that might
        # launch - noisy, and correct for a gate that could not judge.
        [ "$W" = "__too_deep__" ] && return 0
        # #62: a segment with none of the words any launch spelling needs cannot be
        # one (every form of LAUNCH_TRIGGER_RE / LAUNCH_VARPROG_RE holds `launch`,
        # `sbatch`, `run`, `trigger` or `--confirm`, the seqerakit and HTTP checks
        # `seqerakit` and `/launch`), and the regexes below are the costly part
        # on Git Bash: thousands of here-doc lines ran past the hook's timeout.
        # Looked for in the quote-free column and in the segment with its quote
        # characters dropped, the two texts the checks below read: `s"b"atch` has
        # the word only in the second.
        SQ=${S//[\"\']/}
        case "$SQ$US$V" in
            *launch*|*sbatch*|*run*|*--confirm*|*trigger*|*seqerakit*) ;;
            *) continue ;;
        esac
        if ! [[ $V =~ $LAUNCH_TRIGGER_RE ]]; then
            # `"tw" launch x` quotes the program itself, so the quote-free copy
            # has lost it. When the command word IS a launcher, read the
            # segment with only the quote characters dropped. Only then: a
            # commit message quoting "tw launch" is still not a launch.
            HIT=0
            case "$W" in
                tw|nextflow|sbatch|nf-core|relaunch_with_override.sh)
                    [[ $SQ =~ $LAUNCH_TRIGGER_RE ]] && HIT=1 ;;
                # `T=tw; $T launch x`: the program is a variable, and its first
                # argument is a launch verb.
                '$'*)
                    [[ $SQ =~ $LAUNCH_VARPROG_RE ]] && HIT=1 ;;
                # PowerShell `Start-Process nextflow -ArgumentList 'run x'`
                # (#35): the program and its arguments are separate words with
                # parameter names between them. Read the segment with the
                # `-Name` words and the commas dropped, as one command line.
                start-process|saps)
                    SQP=""
                    set -f
                    for SQW in ${SQ//,/ }; do
                        case "$SQW" in -*) ;; *) SQP="$SQP $SQW" ;; esac
                    done
                    set +f
                    [[ " $SQP " =~ $LAUNCH_TRIGGER_RE ]] && HIT=1 ;;
                # The wrapper itself (`ssh h '…'`) is judged through its
                # payload segments, which the splitter emits separately.
                ssh|eval|bash|sh|zsh|ksh|dash|on_site.sh) ;;
                *)
                    # #62: the nested-shell test reads the whole command, so it is
                    # made once, and only when a segment gets this far.
                    if [ "$NESTED" = -1 ]; then
                        NESTED=0; [[ $CMD =~ $LAUNCH_NESTED_SHELL_RE ]] && NESTED=1
                    fi
                    [ "$NESTED" = 1 ] && [[ $SQ =~ $LAUNCH_TRIGGER_RE ]] && HIT=1 ;;
            esac
            # launch-shapes-unconfirmed: seqerakit given a YAML file, and a POST
            # to the Platform API's launch endpoint. The program has to be on the
            # quote-free column (or be the command word), so a commit message or
            # an echo that only quotes one is not a launch.
            if [ "$HIT" = 0 ]; then
                if [[ $SQ =~ $LAUNCH_SEQERAKIT_RE ]] \
                   && { [[ $V =~ $LAUNCH_SEQERAKIT_WORD_RE ]] || [ "$W" = seqerakit ]; } \
                   && ! [[ $SQ =~ $LAUNCH_SEQERAKIT_DRY_RE ]]; then
                    HIT=1
                elif [[ $SQ =~ $LAUNCH_HTTP_PATH_RE ]] && [[ $V =~ $LAUNCH_HTTP_CLIENT_RE ]] \
                   && [[ $SQ =~ $LAUNCH_HTTP_POST_RE ]]; then
                    HIT=1
                fi
            fi
            [ "$HIT" = 1 ] || continue
        fi
        [[ $V =~ $LAUNCH_READONLY_RE ]] && continue
        return 0
    done <<< "$SEGS"

    return 1
}
