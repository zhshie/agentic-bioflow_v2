#!/bin/bash
# PreToolUse/Bash|Write|Edit: make the walkthrough steps happen before the steps
# that depend on them.
#
# commands/launch.md has said for two versions that the pipeline's diagram and
# stage list must be shown before anyone is asked to configure it, and that the
# parameter choices must be put to the user rather than decided for them. Both
# were skipped anyway, by a model that had read the file. Step 2's own comment
# predicted it: "this step was skipped once with nothing to notice: the output
# looked right."
#
# That is the whole mechanism. Steps 2 and 5 produce no artifact, so doing them
# and skipping them leave the run looking identical. Prose cannot fix that,
# because nothing contradicts prose that was ignored.
#
# So the gate is placed on the FIRST action that depends on each step, not on
# the launch at the end. Denying at `tw launch` would be too late to matter:
# by then the samplesheet is built and the parameters chosen, and showing the
# diagram afterwards is a formality. A gate belongs before the next step, not
# before the last one.
#
#   G1  samplesheet work      requires  the diagram was shown
#   G2  writing params        requires  the schema was read and the user answered
#   G3  launch / relaunch     requires  both  (backstop)
#   G4  writing analysis or   requires  an analysis plan the user answered
#       plotting code
#   G5  an outdir              requires  it to be inside a project
#
# Unlike confirm_launch.sh beside it, this one DENIES. That is a departure and
# it is bounded: doing the missing step puts the evidence in the transcript and
# the retry passes, so a denial is a detour and never a wall. A user who wants
# out says the escape phrase below and is never asked again.
#
# It keeps no state (PRINCIPLES.md, invariant 2). The conversation itself is
# the record, read fresh each time from transcript_path.
set -uo pipefail

# Two escape phrases, not one, because this hook re-reads the whole
# conversation every time. A single phrase said in the morning to skip a
# pipeline walkthrough would silently stand the afternoon's analysis gate down
# as well, hours later, with nothing to notice. Different steps, far apart,
# different words.
ESCAPE='略過導覽'      # said by the user, G1/G2/G3 stand down
ESCAPE4='略過計畫'     # said by the user, G4 stands down
MAXLINES=4000          # transcript tail scanned; bounds the cost on a long one

INPUT=$(cat)
TOOL=$(jq -r '.tool_name // ""'            <<<"$INPUT" 2>/dev/null)
CMD=$(jq  -r '.tool_input.command // ""'   <<<"$INPUT" 2>/dev/null)
# notebook_path as well as file_path: MultiEdit and NotebookEdit reach the
# same files by a different key, and a gate that cannot see the tool name
# a write arrives under is a gate with a spelling for a hole.
FILE=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // ""' <<<"$INPUT" 2>/dev/null)
CONTENT=$(jq -r '.tool_input.content // ""' <<<"$INPUT" 2>/dev/null)
TP=$(jq   -r '.transcript_path // ""'      <<<"$INPUT" 2>/dev/null)

allow() { exit 0; }
deny()  { jq -n --arg m "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse",
            permissionDecision: "deny", permissionDecisionReason: $m}}'; exit 0; }
warn()  { jq -n --arg m "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse",
            additionalContext: $m}}'; exit 0; }

# ---- which gate, if any, does this call belong to -------------------------
# Named by what the action IS, not by which script performs it: the samplesheet
# can be built by the shipped generator, by the pipeline's own, or by writing
# the csv directly, and all three are the same step.
G1=0; G2=0; G3=0
[ "$TOOL" = Bash ] && {
    grep -qE 'tw[[:space:]]+datasets[[:space:]]+add|generate_samplesheet\.py|fastq_dir_to_samplesheet' <<<"$CMD" && G1=1
    grep -qE '>[[:space:]]*[^[:space:]]*params[^[:space:]]*\.ya?ml|params[^[:space:]]*\.ya?ml[[:space:]]*<<' <<<"$CMD" && G2=1
}
case "$FILE" in
    *samplesheet*.csv|*samplesheet*.tsv) G1=1 ;;
esac
case "$FILE" in
    *params*.yml|*params*.yaml) G2=1 ;;
esac

# G4: writing analysis or plotting code into a project's analysis/ directory.
#
# The extension list is a whitelist on purpose. analysis/ also holds the plan
# itself, the figures and any notes, and none of those are the step this gate
# is about. confirm_cleanup.sh's reason for not firing on writes into
# analysis/ applies here too: crying wolf on the normal path teaches people to
# click through.
#
# It does not fire on RUNNING code. This file's own rule is that a gate goes
# before the first action that depends on the missing step, and that action is
# writing the script - anything reachable by --file got there through a write
# this gate already saw. Firing on the run as well would fire on every
# iteration of downstream's run/describe/revise loop.
G4=0
ANALYSIS_TARGET=""
is_analysis_code() {
    case "$1" in
        */analysis/*.R|*/analysis/*.r|*/analysis/*.py|*/analysis/*.Rmd|*/analysis/*.qmd) return 0 ;;
        analysis/*.R|analysis/*.r|analysis/*.py|analysis/*.Rmd|analysis/*.qmd) return 0 ;;
    esac
    return 1
}
if [ "$TOOL" != Bash ] && [ -n "$FILE" ] && is_analysis_code "$FILE"; then
    G4=1; ANALYSIS_TARGET="$FILE"
fi
if [ "$TOOL" = Bash ]; then
    # Heredoc bodies first: strip_heredocs.awk keeps the introducing line, so
    # `cat > analysis/x.R <<'EOF'` is still seen while a body line that merely
    # mentions such a path is not.
    CMD_NB=$(printf '%s\n' "$CMD" | awk -f "$(dirname "$0")/strip_heredocs.awk" 2>/dev/null)
    [ -n "$CMD_NB" ] || CMD_NB="$CMD"
    cand=$(grep -oE '(>>?|[[:space:]]tee([[:space:]]+-a)?)[[:space:]]*[^[:space:];|&<>]*analysis/[^[:space:];|&<>]+' \
           <<<"$CMD_NB" | sed -E 's/^[^[:alnum:]_./~$-]*//; s/^(tee|-a)[[:space:]]+//g' | head -1)
    cand=$(printf '%s' "$cand" | sed -E 's/^[[:space:]>]*//')
    if [ -n "$cand" ] && is_analysis_code "$cand"; then
        G4=1; ANALYSIS_TARGET="$cand"
    fi
fi

# The launch verbs are one judgement shared with confirm_launch.sh, loaded
# fail-closed for the reason spelled out there: a helper that goes missing must
# not take the gate with it silently.
if [ "$TOOL" = Bash ]; then
    if . "$(dirname "$0")/launch_trigger.sh" 2>/dev/null \
       && declare -F is_launch_command >/dev/null 2>&1; then
        is_launch_command "$CMD" && G3=1
    else
        warn "GATE NOT WORKING: hooks/launch_trigger.sh could not be loaded, so the walkthrough gate cannot tell whether this command starts a run. Repair the plugin; until then check by hand that the pipeline was shown to the user and its parameters chosen by them."
    fi
fi

# G5: a run's output has to land inside a project.
#
# Everything a piece of work produces is collected under one project -
# rawdata, runs, analysis, the package - and a run whose outdir points
# somewhere else is not in any of them. The choice of project is a question
# `launch.md` asks before anything starts; this is the check that it was asked.
#
# Where to look is decided by where the value actually lives. outdir is a
# pipeline parameter, so it is in params.yaml and not on the command line -
# checking `tw launch`'s argv for it would be a rule that never fires. Three
# places carry it, and all three are read here: a heredoc writing the file, a
# Write tool's content, and the file a launch names with --params-file.
#
# When no outdir can be found the constraint is left off rather than guessed
# at, the same way G1 leaves the pipeline constraint off for a Launchpad name
# that reveals no repo. A rule that fires on what it cannot see is worse than
# one that admits the gap.
G5=0
OUTDIR=""
outdir_from() { sed -nE 's/^[[:space:]]*(-{1,2})?outdir[:=][[:space:]]*["'"'"']?([^"'"'"'[:space:]]+).*/\2/p' "$1" 2>/dev/null | head -1; }
if [ "$G2" = 1 ]; then
    OUTDIR=$( { printf '%s\n' "$CMD"; printf '%s\n' "$CONTENT"; } | outdir_from /dev/stdin )
fi
if [ "$G3" = 1 ]; then
    pf=$(sed -nE 's/.*(-{1,2})params-file[= ]+([^[:space:]]+).*/\2/p' <<<"$CMD" | head -1)
    [ -n "$pf" ] && [ -r "$pf" ] && OUTDIR=$(outdir_from "$pf")
fi
if [ -n "$OUTDIR" ]; then
    case "$OUTDIR" in
        */projects/*/runs/*) ;;
        *) G5=1 ;;
    esac
fi

[ "$G1$G2$G3$G4$G5" = "00000" ] && allow

# ---- which pipeline is this call about ------------------------------------
# A diagram is evidence about one pipeline, and conversations switch pipelines.
# The previous one's figure stays in the transcript and used to go on answering
# for the next one. Only a command that actually names a repo can be checked -
# a Launchpad entry is a name of the user's choosing and says nothing about the
# repo behind it, so it leaves the constraint off rather than guessing.
# -w/--workspace takes an org/name pair too; drop it before looking.
WANT=$(sed -E 's/(^| )(-w|--workspace)[= ][^ ]*/ /g' <<<"$CMD" \
       | grep -oE '(nf-core|github\.com/[A-Za-z0-9_.-]+)/[A-Za-z0-9_.-]+' \
       | head -1 | sed -E 's#.*/##')

# ---- what the conversation shows already happened -------------------------
# Reading the transcript is what makes this checkable rather than advisory. It
# is also why nothing is written down: the conversation already records what
# was said, and a second copy would be the thing invariant 2 forbids.
[ -n "$TP" ] && [ -r "$TP" ] || warn \
"The walkthrough gate could not read this conversation's transcript, so it could not check whether the pipeline was shown to the user before this step. Proceeding unchecked. Confirm by hand that the diagram and stage list were shown, and that the parameter choices were put to the user rather than decided for them."

# Where the analysis plan for THIS piece of work lives. Walk up from the file
# being written rather than parsing its path, because the answer is a fact
# about the filesystem: the plan sits in the project's analysis/ directory and
# the script is written beside or below it. That makes the subject checkable
# however the path is spelled - PITFALLS 18b's "evidence has a subject" is
# closed here in a way it could not be for a pipeline diagram, where the only
# subject available was a string in a command.
plan_file_for() {
    local d; d=$(dirname "$1")
    case "$d" in /*) ;; *) d="$PWD/$d" ;; esac
    local i=0
    while [ "$i" -lt 6 ] && [ "$d" != / ] && [ -n "$d" ]; do
        [ -f "$d/analysis.md" ] && { printf '%s\n' "$d/analysis.md"; return 0; }
        d=$(dirname "$d"); i=$((i+1))
    done
    return 1
}

# A subagent's transcript is its own file, every record marked (PITFALLS 22).
# It cannot contain the parent's plan, and a subagent cannot put the missing
# step in front of a user and try again - so denying it would be a wall rather
# than a detour, which is the one thing this file's departure was bounded by.
# G4 warns there instead. G1/G2/G3 keep denying: their remedy is not starting a
# run, and an unattended agent starting one is exactly what they are for.
SIDECHAIN=0
tail -n 200 "$TP" 2>/dev/null | jq -r '.isSidechain // false' 2>/dev/null \
    | grep -qx true && SIDECHAIN=1

# One line per content block: 'x' assistant text - the only thing the user
# actually read - 'a' the assistant's other blocks (tool_use, thinking), 'h' a
# human turn, 'u' the machinery. Splitting text from tool_use is what stops a
# URL the model typed into a command from counting as a URL it showed anyone.
# tojson rather than tostring - tostring leaves a plain-string content
# unquoted, its newlines split one record across several lines, and the
# ordering below silently stops meaning anything.
EV=$(tail -n "$MAXLINES" "$TP" 2>/dev/null | jq -r '
      select(.type=="assistant" or .type=="user")
      | if .type=="assistant" then
          (if (.message.content|type)=="array"
           then .message.content[]
                | (if .type=="text" then "x" else "a" end) + "\t" + tojson
           else "x\t" + (.message.content|tojson) end)
        else
          (if ((.message.content|type)=="string")
              or ((.message.content|type)=="array"
                  and ([.message.content[].type]|index("text")))
           then "h" else "u" end)
          + "\t" + ((.message.content // "") | tojson)
        end' 2>/dev/null \
  | awk -F'\t' 'BEGIN{OFS="\t"}
      # Injected turns arrive shaped exactly like a person typing. Left as "h"
      # they would answer the question "did the user reply", so waiting for a
      # subagent would satisfy a gate about consent.
      $1=="h" && ($2 ~ /<task-notification/ || $2 ~ /<system-reminder/ \
                 || $2 ~ /<command-name/ || $2 ~ /<local-command/ \
                 || $2 ~ /This session is being continued/) { $1="u" }
      { print }' \
  | awk -F'\t' -v want="$WANT" '
      $1=="h" && index($2,"'"$ESCAPE"'")            { esc=1 }
      # A URL the user was handed, in text. Not a mention - typing the words
      # "docs/images/" while discussing this gate is not showing anyone a
      # diagram - and not a URL inside a command either. Both looser forms were
      # tried and both were satisfied by the conversation that wrote this file:
      # the second by the heredoc that created its test fixtures. Step 2 asks
      # for the raw URL to be put in front of the user, and a terminal renders
      # no image, so text is exactly the right and only evidence.
      $1=="x" && $2 ~ /https?:\/\/[^ "]*docs\/images\// {
          any=1
          if (want=="" || index($2, "/" want "/")) diag=1
      }
      # The schema is different: it has to be READ, not displayed, so a fetch
      # counts. The command must actually fetch it - naming the URL inside a
      # file being written is the same nothing as above.
      $1=="x" && $2 ~ /https?:\/\/[^ "]*nextflow_schema\.json/  { schema=NR }
      $1=="a" && $2 ~ /https?:\/\/[^ "]*nextflow_schema\.json/ \
              && $2 ~ /curl|wget|WebFetch|http\.get|urlopen/     { schema=NR }
      # Two ways the user can have answered, and the first needs no blocklist
      # to be trusted: an AskUserQuestion carries the choice the user made.
      $1=="a" && schema && NR>schema && index($2,"AskUserQuestion") { ans=1 }
      $1=="h" && schema && NR>schema                { ans=1 }
      $1=="h" && index($2,"'"$ESCAPE4"'")           { esc4=1 }
      # An analysis plan, as something a person was actually shown. A whole
      # text block is one record here, so its newlines are the two characters
      # backslash-n; split on those and count the lines that pair a thing to
      # make with the file it would be made from. Two, not one: a plan is
      # plural, and the one-line form is what ordinary prose about plotting
      # produces by accident.
      #
      # 'x' only, never 'a'. The schema rule above accepts a tool_use because
      # the schema has to be READ; a plan has no value unless a person saw it,
      # so it follows the diagram rule instead. Accepting 'a' here would let
      # `cat > analysis/analysis.md <<EOF ... EOF` satisfy the gate that
      # exists to stop exactly that - PITFALLS 18, reopened.
      # A plan, as something a person was shown. Two conditions on one text
      # block, and neither alone would do:
      #
      #   it names analysis.md      - the block is about the plan, not about
      #                               the data. Step 2 prints an inventory
      #                               listing dozens of files; without this,
      #                               that printout would satisfy this gate.
      #   two lines read real files - a plan is plural and says what each item
      #                               is made from. One line is what ordinary
      #                               prose about plotting produces by accident.
      #
      # An earlier version instead required each line to carry a word like
      # "plot" or "figure". That is guessing at vocabulary: a real plan line
      # reads "ASV richness by group, from dada2/ASV_table.tsv" and contains
      # no such word. The file reference is the half that carries weight.
      #
      # 'x' only, never 'a'. The schema rule above accepts a tool_use because
      # the schema has to be READ; a plan has no value unless a person saw it.
      # Accepting 'a' would let `cat > analysis.md <<EOF ... EOF` satisfy the
      # gate that exists to stop exactly that - PITFALLS 18, reopened.
      $1=="x" && $2 ~ /analysis\.md/ {
          nl = split($2, L, /\\n/); c = 0
          for (i = 1; i <= nl; i++)
              if (L[i] ~ /[A-Za-z0-9_.\/-]+\.(tsv|csv|txt|tab|json|ya?ml|rds|RDS|RData|biom|qza|mtx|h5)([^A-Za-z0-9]|$)/)
                  c++
          if (c >= 2) plan = NR
      }
      $1=="a" && plan && NR>plan && index($2,"AskUserQuestion") { pans=1 }
      $1=="h" && plan && NR>plan                    { pans=1 }
      END { printf "%d %d %d %d %d %d %d %d\n", esc+0, diag+0, (schema>0)?1:0, ans+0, any+0, \
                   esc4+0, (plan>0)?1:0, pans+0 }')
read -r ESC DIAG SCHEMA ANS DIAGANY ESC4 PLAN PANS <<<"${EV:-0 0 0 0 0 0 0 0}"

# Stand the walkthrough gates down, not every gate. `allow` here would exit
# before G4 is considered, so one phrase said hours earlier for a different
# step would silently disable the analysis gate too - which is exactly what
# having two phrases is for. G4 has its own, checked in its own block.
[ "$ESC" = 1 ] && { G1=0; G2=0; G3=0; G5=0; }
[ "$G1$G2$G3$G4$G5" = "00000" ] && allow

DIAGRAM_FIX="Show it first: list docs/images/ in the pipeline at the pinned revision, hand the user the raw URL of the workflow figure, and give the stage list from the README in words - a terminal renders no image. Read the directory rather than guessing the filename; the pipelines used here name that figure four different ways. Then run this again."
MENU_FIX="Do step 5 first: fetch nextflow_schema.json at the pinned revision, then put three choices to the user - reuse the parameters from a previous run, take the pipeline's defaults, or go through the adjustable ones. \"All defaults\" is a complete answer from them; it is not an answer you can give on their behalf. Then run this again."
ESC_NOTE="If this really should go ahead without it, the user - not you - can say $ESCAPE."

[ "$G1" = 1 ] && [ "$DIAG" != 1 ] && deny \
"Step 2 has not happened: nothing in this conversation shows the pipeline's workflow diagram was shown to the user, and the samplesheet is where configuring it begins.

$DIAGRAM_FIX

$ESC_NOTE"

if [ "$G2" = 1 ] && { [ "$SCHEMA" != 1 ] || [ "$ANS" != 1 ]; }; then
    [ "$SCHEMA" != 1 ] \
      && deny "Step 5 has not happened: nothing shows nextflow_schema.json was read, and it is the authority on what this pipeline can be asked to do. Writing params.yaml without it means the values came from somewhere else.

$MENU_FIX

$ESC_NOTE"
    deny "Step 5 is unfinished: the schema was read, but no answer came back from the user afterwards. Parameters chosen quietly produce a params.yaml indistinguishable from one they approved, which is how this step was satisfied without ever reaching a person.

$MENU_FIX

$ESC_NOTE"
fi

if [ "$G3" = 1 ]; then
    if [ "$DIAG" != 1 ]; then
        [ "$DIAGANY" = 1 ] && deny \
"This starts a run of ${WANT:-this pipeline}, and the only workflow diagram in this conversation belongs to a different pipeline. Whatever was shown earlier described something else; nobody has seen what this run will do.

$DIAGRAM_FIX

$ESC_NOTE"
        deny \
"This starts a run, and step 2 never happened: the pipeline's workflow diagram was not shown to the user.

$DIAGRAM_FIX

$ESC_NOTE"
    fi
    { [ "$SCHEMA" != 1 ] || [ "$ANS" != 1 ]; } && deny \
"This starts a run, and step 5 never finished: the parameters were not put to the user as a choice.

$MENU_FIX

$ESC_NOTE"
fi

if [ "$G4" = 1 ] && [ "$ESC4" != 1 ]; then
    PLANFILE=$(plan_file_for "$ANALYSIS_TARGET" 2>/dev/null) || PLANFILE=""
    G4_FIX="Do the planning step first: put an analysis plan in front of the user - what to compute and what to draw, each one saying which question it answers and which file and columns it reads - let them answer, and write it to analysis.md beside the code. \"All of them, go ahead\" is a complete answer from them; it is not one you can give on their behalf. Then run this again."

    G4_WHY=""
    if [ -z "$PLANFILE" ]; then
        G4_WHY="there is no analysis.md beside or above $ANALYSIS_TARGET, so nothing says what this code is meant to produce or why."
    elif [ "$PLAN" != 1 ]; then
        # The file exists and no one has been shown a plan. This is the case
        # the whole gate is for: writing the plan into a file is the natural
        # move here, far more natural than the heredoc that caught G1, and a
        # plan nobody read is not a plan that was agreed.
        G4_WHY="$PLANFILE exists, but nothing in this conversation put a plan in front of the user - only a file was written. A plan nobody was shown is not a plan anybody agreed to."
    elif [ "$PANS" != 1 ]; then
        G4_WHY="a plan was put to the user and no answer came back afterwards. Analysis chosen quietly produces code indistinguishable from code they asked for, which is how this step gets satisfied without ever reaching a person."
    fi

    if [ -n "$G4_WHY" ]; then
        if [ "$SIDECHAIN" = 1 ]; then
            # See the note beside SIDECHAIN above: the remedy is unavailable
            # here, so this reports instead of refusing.
            warn "The analysis plan could not be checked: this is a subagent, and its conversation is a separate transcript that cannot contain the parent's plan (PITFALLS 22). Proceeding unchecked. Confirm by hand that $ANALYSIS_TARGET implements a plan the user agreed to."
        fi
        deny "Step 3 has not happened: $G4_WHY

$G4_FIX

If this really should go ahead without it, the user - not you - can say $ESCAPE4."
    fi
fi

if [ "$G5" = 1 ]; then
    deny "This run's outdir is '$OUTDIR', which is not inside a project.

Everything one piece of work produces belongs together - the raw data, every run made from it, the analysis, and the package built from the analysis. Ask the user which project this run is part of, or whether to start a new one, and put the outdir under it:

    <storage_root>/<seqera_user>/projects/<project>/runs/<pipeline>_<label>_<YYYYMMDD>/results

scripts/init_workspace.sh site --user <u> --project <p> --run <name> creates it. Then run this again.

If this really should go ahead without it, the user - not you - can say $ESCAPE."
fi

allow
