#!/bin/bash
# Stop: while a command's flow is active, the model's final message must end
# with a next step - so the user is never left not knowing what to do next
# (U7, plan section 六).
#
# "Flow active" is a fact about the transcript, not about the model's memory:
# it starts the moment a Bash tool_use actually runs `scripts/intro.sh
# <command>`, and ends the moment a matching `scripts/intro.sh --end
# <command>` runs after it. Both are real tool calls the model issued, never
# something it merely claims - the same "evidence in the transcript" standard
# confirm_walkthrough.sh already holds itself to. A conversation that never
# ran intro.sh at all - including every conversation that has nothing to do
# with this plugin, since this hook fires on every Stop in every session
# where the plugin is installed - never enters a flow and this hook does
# nothing, fast: a cheap grep for "intro.sh" on the transcript tail comes back
# empty and the hook exits before ever calling jq.
#
# T4 (2.16): `intro.sh <cmd>` was the ONLY door, and skills/operational/
# SKILL.md is reachable by natural language precisely so a typed slash
# command is never required (PRINCIPLES.md, "the skill is the heart"). A
# conversation that loaded the skill and started working without ever
# running intro.sh - plausible, since nothing forced the call before T5 made
# it the skill's own first step - left this hook believing no flow was open
# at all. A `Skill` tool_use naming `agentic-bioflow:<one of the five
# commands>` now opens that command's flow exactly the way running its
# intro.sh does. `agentic-bioflow:operational` itself is excluded on
# purpose: it is the router, not one of the five, and which flow it becomes
# is only known once it goes on to call intro.sh <cmd> - which T5 now
# requires as literally its first action, so that call still opens things
# the original way moments later. The cheap pre-filter below has to widen
# with it: a transcript that opened a flow purely by loading the skill,
# with intro.sh never once typed, contains no "intro.sh" substring at all -
# exactly the gap this half of the card exists to close - so grepping for
# only that string would skip the fast path around the very case T4 adds.
# It now also passes on a bare mention of "agentic-bioflow:", which every
# Skill tool_use naming this plugin's skills carries in its own JSON.
#
# T25 (2.18, right after T4): a single ACTIVE scalar was already wrong the
# day a member ran two commands side by side - `runs` to check on one
# delivery while `launch` starts the next - which this cluster's own
# multi-hour, multi-run sessions make ordinary rather than exotic. Opening a
# second flow used to silently forget the first was open at all, so a
# next-step reminder about `runs` disappeared the moment `launch` was
# touched, and the escaped flow got no reminder ever again. Flows now open
# and close INDEPENDENTLY, as a set: each `intro.sh <cmd>` or matching Skill
# load opens its own entry, each `intro.sh --end <cmd>` closes only that
# one, and nothing about one flow's bookkeeping touches another's. With more
# than one open, naming a next step is not enough on its own - see the
# multi-flow branch below, where the reply also has to say which one it is
# talking about, or "next step: confirm it" is ambiguous between two runs
# that both need confirming.
#
# Deliberately fail OPEN, unlike the three safety-net hooks beside it
# (PITFALLS 28's fix for THOSE is fail-closed). A Stop hook is not a
# permission gate: refusing to let the model stop because jq is missing, or
# because the transcript could not be read, would not "refuse an action" the
# way confirm_launch/cleanup/walkthrough do - it would trap the conversation
# in a loop the user cannot break out of from their side. Missing the
# reminder costs one nudge; blocking Stop unconditionally costs the whole
# conversation. So every failure mode below ends in exit 0, not exit 2.
#
# `stop_hook_active` is checked FIRST, before any file is even opened: it is
# true precisely when the model is already continuing because THIS hook
# blocked last time, and re-running the same check on the same transcript can
# only produce the same block - an infinite loop with nothing new to add.
# Claude Code's own 8-consecutive-blocks override is a backstop, not a
# substitute for this check.
set -uo pipefail
exec 2>/dev/null

INPUT=$(cat)

STOP_ACTIVE=$(jq -r '.stop_hook_active // false' <<<"$INPUT" 2>/dev/null)
[ "$STOP_ACTIVE" = true ] && exit 0

TP=$(jq -r '.transcript_path // ""' <<<"$INPUT" 2>/dev/null)
[ -n "$TP" ] && [ -r "$TP" ] || exit 0

MAXLINES=4000   # bounds the cost on a long conversation, same figure
                # confirm_walkthrough.sh uses for the same reason

# Fast path for the overwhelming majority of Stop events: no mention of
# intro.sh AND no mention of this plugin's own skills anywhere recent means
# no flow was ever started, and the jq/awk work below is not worth paying on
# every single assistant turn in every conversation. T4 widened the second
# half of that test - see this file's own T4 paragraph above for why a
# skill-opened flow can carry no "intro.sh" substring at all.
tail -n "$MAXLINES" "$TP" 2>/dev/null | grep -qE 'intro\.sh|agentic-bioflow:' || exit 0

KNOWN='setup|launch|runs|downstream|finish'

# Every Bash tool_use command string AND every Skill tool_use's skill name
# this hook's window can see, oldest first, one per line, tagged so the
# replay below can tell the two apart without a second jq pass. tojson keeps
# an embedded real newline from masquerading as a record boundary, the same
# reason it was already used for the Bash half.
CALLS=$(tail -n "$MAXLINES" "$TP" 2>/dev/null | jq -r '
    select(.type=="assistant")
    | (.message.content // [])[]?
    | select(.type=="tool_use")
    | if .name=="Bash" then "B\t" + ((.input.command // "") | tojson)
      elif .name=="Skill" then "S\t" + ((.input.skill // "") | tojson)
      else empty end' 2>/dev/null)

# Replay the calls in order: each `intro.sh <cmd>` opens that command's flow,
# each matching `intro.sh --end <cmd>` closes it, and (T4) each Skill load of
# `agentic-bioflow:<one of the five>` opens that flow too - `operational`
# itself never does, see this file's own header. T25: OPEN_NAMES is a SET,
# not a single value - opening one flow never closes or forgets another, and
# --end only ever removes the ONE name it names.
#
# A space-padded STRING, not a bash array: this file's siblings deliberately
# avoid depending on anything beyond the shell itself (see PITFALLS 28's
# "inline their own few lines instead" for confirm_cleanup.sh's WARN
# accumulator, the same shape), and an empty bash array's interaction with
# `set -u` is version-dependent - measured on this box's bash 4.4.20,
# `"${arr[@]:-}"` over a truly empty array does not fall back to nothing the
# way a scalar `${x:-}` does; it iterates ONCE with an empty string, which
# would have planted a phantom entry into a "closed" set. `case ... in *"
# $name "*)` has no such trap and is the same technique this file's own
# language check and the confirm_* hooks already use for exactly this kind
# of membership test. Order is kept (append on open) only so an
# earlier-opened flow lists first in a message; nothing below reads the
# order as meaning "current" - T25 retired that idea on purpose.
OPEN_NAMES=" "

is_open()   { case "$OPEN_NAMES" in *" $1 "*) return 0 ;; esac; return 1; }
open_flow() { is_open "$1" || OPEN_NAMES="${OPEN_NAMES}$1 "; }   # idempotent
close_flow(){ OPEN_NAMES="${OPEN_NAMES// $1 / }"; }              # no-op if absent

while IFS= read -r LINE; do
    [ -n "$LINE" ] || continue
    KIND=${LINE%%$'\t'*}
    REST=${LINE#*$'\t'}
    case "$KIND" in
    B)
        case "$REST" in
            *intro.sh*) ;;
            *) continue ;;
        esac
        TAIL=$(printf '%s' "$REST" | sed -E 's/.*intro\.sh//')
        if printf '%s' "$TAIL" | grep -qE "^[[:space:]]+--end[[:space:]]+($KNOWN)\\b"; then
            ENDCMD=$(printf '%s' "$TAIL" | sed -nE "s/^[[:space:]]+--end[[:space:]]+($KNOWN)\\b.*/\\1/p")
            [ -n "$ENDCMD" ] && close_flow "$ENDCMD"
        elif printf '%s' "$TAIL" | grep -qE "^[[:space:]]+($KNOWN)\\b"; then
            OPENCMD=$(printf '%s' "$TAIL" | sed -nE "s/^[[:space:]]+($KNOWN)\\b.*/\\1/p")
            [ -n "$OPENCMD" ] && open_flow "$OPENCMD"
        fi
        ;;
    S)
        # REST is the tojson'd skill name, quotes and all - anchored on both
        # ends so "agentic-bioflow:launch-extra" cannot slip through as
        # "launch", and "operational" (not in $KNOWN) never matches at all.
        SKILLNAME=$(printf '%s' "$REST" | sed -nE "s/^\"agentic-bioflow:($KNOWN)\"\$/\\1/p")
        [ -n "$SKILLNAME" ] && open_flow "$SKILLNAME"
        ;;
    esac
done <<< "$CALLS"

[ -n "${OPEN_NAMES# }" ] || exit 0   # outside any flow: this hook has nothing to say

# Word-split the padded set into positional params - safe here because every
# member is one of the five fixed, space-free command names in $KNOWN, never
# arbitrary text, so default IFS splitting cannot misparse anything.
set -- $OPEN_NAMES
OPEN_COUNT=$#

# Which word to look for depends on the deployment's language, read the same
# way intro.sh itself reads it - as a subprocess, never sourced, so a broken
# settings.sh degrades to the same zh-TW default intro.sh falls back to
# rather than taking this hook down with it.
LANGKEY="$(bash "$(cd "$(dirname "$0")/.." && pwd)/scripts/settings.sh" language 2>/dev/null)"
[ -n "$LANGKEY" ] || LANGKEY=zh-TW
case "$LANGKEY" in
    en) NEEDLE="Next step" ;;
    *)  NEEDLE="下一步" ;;
esac

# The model's own last message: the final assistant record's text blocks only
# (tool_use/thinking excluded - what matters here is what the user actually
# read). tojson keeps a multi-line message on one line so a plain substring
# check below cannot be fooled by where real newlines happen to fall.
LASTMSG=$(tail -n "$MAXLINES" "$TP" 2>/dev/null | jq -r '
    select(.type=="assistant")
    | ((.message.content // []) | map(select(.type=="text") | .text) | join("\n"))
    | tojson' 2>/dev/null | tail -1)

HAS_NEEDLE=0
printf '%s' "$LASTMSG" | grep -qF "$NEEDLE" && HAS_NEEDLE=1

# Only one flow open: unchanged from T4 other than reading it off the
# positional params $1 (the set's one member) instead of a scalar $ACTIVE.
if [ "$OPEN_COUNT" -le 1 ]; then
    [ "$HAS_NEEDLE" = 1 ] && exit 0
    CMD="${1:-}"
    # T4: the block message used to ask for "one concrete next step" and stop
    # there, which a reply could satisfy with an entire bulleted menu of
    # options as long as one line used the needle word - technically a next
    # step was named, but the user is handed a decision to make instead of
    # being told what happens next. The reason now asks for exactly ONE LINE
    # naming exactly ONE action, not a menu.
    jq -n --arg needle "$NEEDLE" --arg cmd "$CMD" '
      {decision: "block",
       reason: ("This reply is inside the /agentic-bioflow:" + $cmd + " flow, and it does not end with a next step (\"" + $needle + "\"). End it with exactly ONE line naming ONE concrete next action - the single command to run, or the single decision to make - not a list of options.")}'
    exit 0
fi

# T25: more than one flow is open. A next step alone is not enough here -
# "confirm it" does not say WHICH run or project "it" is, so the reply also
# has to NAME at least one of the open flows. Checked the same way G1-G6
# check evidence elsewhere in this plugin: a literal mention in the text the
# user actually read (not a claim about what the model meant), so this is
# satisfied by writing "the launch run" or "/agentic-bioflow:runs" - any
# text containing the flow's own command word - never by intent alone.
NAMED=0
for n in "$@"; do
    printf '%s' "$LASTMSG" | grep -qF "$n" && NAMED=1
done
[ "$HAS_NEEDLE" = 1 ] && [ "$NAMED" = 1 ] && exit 0

OPEN_LIST=$(printf '%s' "$OPEN_NAMES" | sed -E 's/^ +//; s/ +$//; s/ +/, /g')
jq -n --arg needle "$NEEDLE" --arg list "$OPEN_LIST" '
  {decision: "block",
   reason: ("More than one agentic-bioflow flow is open at once (" + $list + "). End this reply with exactly ONE line that NAMES which flow it is about (its command word, e.g. \"launch\" or \"runs\") and gives ONE concrete next action for it - not a list covering all of them, and not left ambiguous between the open flows. A next step alone (\"" + $needle + "\") is not enough while more than one is open, because it does not say which one it answers for.")}'
exit 0
