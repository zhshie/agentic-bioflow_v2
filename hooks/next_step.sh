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
# intro.sh anywhere recent means no flow was ever started, and the jq/awk
# work below is not worth paying on every single assistant turn in every
# conversation.
tail -n "$MAXLINES" "$TP" 2>/dev/null | grep -q 'intro\.sh' || exit 0

KNOWN='setup|launch|runs|downstream|finish'

# Every Bash tool_use command string this hook's window can see, oldest
# first, one per line (tojson so an embedded real newline in the command
# cannot masquerade as a record boundary).
CALLS=$(tail -n "$MAXLINES" "$TP" 2>/dev/null | jq -r '
    select(.type=="assistant")
    | (.message.content // [])[]?
    | select(.type=="tool_use" and .name=="Bash")
    | (.input.command // "") | tojson' 2>/dev/null)

# Replay the calls in order: each `intro.sh <cmd>` opens that command's flow,
# each matching `intro.sh --end <cmd>` closes it. Whatever is open at the end
# of the transcript is "current" - a conversation moving from one command to
# the next without ever sending --end for the first one just means the new
# command's flow is what is open now, which costs nothing worse than asking
# for a next step a little more often (the plan's own accepted trade-off).
ACTIVE=""
while IFS= read -r RAWCMD; do
    case "$RAWCMD" in
        *intro.sh*) ;;
        *) continue ;;
    esac
    TAIL=$(printf '%s' "$RAWCMD" | sed -E 's/.*intro\.sh//')
    if printf '%s' "$TAIL" | grep -qE "^[[:space:]]+--end[[:space:]]+($KNOWN)\\b"; then
        ENDCMD=$(printf '%s' "$TAIL" | sed -nE "s/^[[:space:]]+--end[[:space:]]+($KNOWN)\\b.*/\\1/p")
        [ "$ENDCMD" = "$ACTIVE" ] && ACTIVE=""
    elif printf '%s' "$TAIL" | grep -qE "^[[:space:]]+($KNOWN)\\b"; then
        ACTIVE=$(printf '%s' "$TAIL" | sed -nE "s/^[[:space:]]+($KNOWN)\\b.*/\\1/p")
    fi
done <<< "$CALLS"

[ -n "$ACTIVE" ] || exit 0   # outside any flow: this hook has nothing to say

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

printf '%s' "$LASTMSG" | grep -qF "$NEEDLE" && exit 0

jq -n --arg needle "$NEEDLE" --arg cmd "$ACTIVE" '
  {decision: "block",
   reason: ("This reply is inside the /agentic-bioflow:" + $cmd + " flow, and it does not end with a next step (\"" + $needle + "\"). Add one concrete next step - which command, or which decision is next - before finishing.")}'
exit 0
