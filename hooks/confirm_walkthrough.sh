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
#   G1  samplesheet work   requires  the diagram was shown
#   G2  writing params     requires  the schema was read and the user answered
#   G3  launch / relaunch  requires  both  (backstop)
#
# Unlike confirm_launch.sh beside it, this one DENIES. That is a departure and
# it is bounded: doing the missing step puts the evidence in the transcript and
# the retry passes, so a denial is a detour and never a wall. A user who wants
# out says the escape phrase below and is never asked again.
#
# It keeps no state (PRINCIPLES.md, invariant 2). The conversation itself is
# the record, read fresh each time from transcript_path.
set -uo pipefail

ESCAPE='略過導覽'      # said by the user, this gate stands down
MAXLINES=4000          # transcript tail scanned; bounds the cost on a long one

INPUT=$(cat)
TOOL=$(jq -r '.tool_name // ""'            <<<"$INPUT" 2>/dev/null)
CMD=$(jq  -r '.tool_input.command // ""'   <<<"$INPUT" 2>/dev/null)
FILE=$(jq -r '.tool_input.file_path // ""' <<<"$INPUT" 2>/dev/null)
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

[ "$G1$G2$G3" = "000" ] && allow

# ---- what the conversation shows already happened -------------------------
# Reading the transcript is what makes this checkable rather than advisory. It
# is also why nothing is written down: the conversation already records what
# was said, and a second copy would be the thing invariant 2 forbids.
[ -n "$TP" ] && [ -r "$TP" ] || warn \
"The walkthrough gate could not read this conversation's transcript, so it could not check whether the pipeline was shown to the user before this step. Proceeding unchecked. Confirm by hand that the diagram and stage list were shown, and that the parameter choices were put to the user rather than decided for them."

# Each record flattened to one line: 'a' assistant, 'h' a human turn, 'u' the
# machinery. tojson rather than tostring - tostring leaves a plain-string
# content unquoted, its newlines split one record across several lines, and the
# ordering below silently stops meaning anything.
EV=$(tail -n "$MAXLINES" "$TP" 2>/dev/null | jq -r '
      select(.type=="assistant" or .type=="user")
      | (if .type=="assistant" then "a"
         elif ((.message.content|type)=="string")
              or ((.message.content|type)=="array"
                  and ([.message.content[].type]|index("text")))
         then "h" else "u" end)
        + "\t" + ((.message.content // "") | tojson)' 2>/dev/null \
  | awk -F'\t' 'BEGIN{OFS="\t"}
      # Injected turns arrive shaped exactly like a person typing. Left as "h"
      # they would answer the question "did the user reply", so waiting for a
      # subagent would satisfy a gate about consent.
      $1=="h" && ($2 ~ /<task-notification/ || $2 ~ /<system-reminder/ \
                 || $2 ~ /<command-name/ || $2 ~ /<local-command/ \
                 || $2 ~ /This session is being continued/) { $1="u" }
      { print }' \
  | awk -F'\t' '
      $1=="h" && index($2,"'"$ESCAPE"'")            { esc=1 }
      # A URL, not a mention. Typing the words "docs/images/" while discussing
      # this gate is not showing anyone a diagram, and an evidence test that
      # its own design conversation satisfies is not a test.
      $1=="a" && $2 ~ /https?:\/\/[^ "]*docs\/images\//        { diag=1 }
      $1=="a" && $2 ~ /https?:\/\/[^ "]*nextflow_schema\.json/  { schema=NR }
      # Two ways the user can have answered, and the first needs no blocklist
      # to be trusted: an AskUserQuestion carries the choice the user made.
      $1=="a" && schema && NR>schema && index($2,"AskUserQuestion") { ans=1 }
      $1=="h" && schema && NR>schema                { ans=1 }
      END { printf "%d %d %d %d\n", esc+0, diag+0, (schema>0)?1:0, ans+0 }')
read -r ESC DIAG SCHEMA ANS <<<"${EV:-0 0 0 0}"

[ "$ESC" = 1 ] && allow

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
    [ "$DIAG" != 1 ] && deny \
"This starts a run, and step 2 never happened: the pipeline's workflow diagram was not shown to the user.

$DIAGRAM_FIX

$ESC_NOTE"
    { [ "$SCHEMA" != 1 ] || [ "$ANS" != 1 ]; } && deny \
"This starts a run, and step 5 never finished: the parameters were not put to the user as a choice.

$MENU_FIX

$ESC_NOTE"
fi

allow
