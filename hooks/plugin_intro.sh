#!/bin/bash
# UserPromptSubmit + PostToolUse(Skill): show the overview the first time this
# plugin is actually used in a session, not at every session start.
#
# It used to be a SessionStart hook, which meant every conversation in every
# project opened with it - including the many that have nothing to do with
# pipelines. The overview is worth reading exactly once, at the moment the user
# reaches for the plugin. Two events are that moment, and both are measured,
# not assumed (2026-09-13):
#   - the user types a command: UserPromptSubmit's `prompt` is the raw text,
#     e.g. "/agentic-bioflow:runs check something".
#   - the model loads one of the plugin's skills for a natural-language
#     request: the Skill tool's input is {"skill": "agentic-bioflow:<name>"}.
#     PostToolUse, not PreToolUse, so a refused or failed load shows nothing.
# A typed command may go on to load the skill as well; the once-per-session
# marker makes the second event a no-op.
#
# Not a gate. It fails open everywhere and always exits 0: a missing jq, an
# unwritable state directory or a broken intro.sh costs the user the overview,
# never their prompt.
set -uo pipefail
exec 2>/dev/null

INPUT=$(cat)

# UserPromptSubmit fires on every prompt of every conversation. Nearly all of
# them never mention the plugin, and they leave here before paying for jq.
case "$INPUT" in *agentic-bioflow:*) ;; *) exit 0 ;; esac
command -v jq >/dev/null || exit 0

EVENT=$(jq -r '
    if .tool_name == "Skill" then
        (if ((.tool_input.skill // "") | startswith("agentic-bioflow:")) then "PostToolUse" else "" end)
    elif ((.prompt // "") | test("^\\s*/agentic-bioflow:")) then "UserPromptSubmit"
    else "" end' <<<"$INPUT") || exit 0
[ -n "$EVENT" ] || exit 0

# The session id names a file, so it is reduced to characters that cannot
# climb out of the state directory. With no id at all there is nothing to key
# on, and the overview is shown rather than risk never showing it.
SID=$(jq -r '.session_id // ""' <<<"$INPUT" | tr -cd 'A-Za-z0-9_-')
STATE="${AGENTIC_BIOFLOW_STATE_DIR:-${XDG_STATE_HOME:-${HOME:-}/.local/state}/agentic-bioflow}"
MARKS="$STATE/intro-shown"
[ -n "$SID" ] && [ -e "$MARKS/$SID" ] && exit 0

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INTRO="$(bash "$ROOT/scripts/intro.sh")" || exit 0
[ -n "$INTRO" ] || exit 0

# Claude Code caps hook output at 10,000 characters and swaps anything longer
# for a file preview; trimming here keeps it readable.
[ "${#INTRO}" -gt 9000 ] && INTRO="${INTRO:0:9000}

[truncated - run scripts/intro.sh for the full text]"

# systemMessage is shown to the user as-is; additionalContext gives the model
# the same text, so its next step matches what the user just read.
jq -n --arg m "$INTRO" --arg e "$EVENT" \
  '{systemMessage: $m, hookSpecificOutput: {hookEventName: $e, additionalContext: $m}}' || exit 0

# Marked only after the overview went out, so a failure above leaves the next
# use free to try again. Markers are a few bytes each; a month is long past any
# session anyone resumes.
if [ -n "$SID" ] && mkdir -p "$MARKS"; then
    : > "$MARKS/$SID"
    find "$MARKS" -type f -mtime +30 -exec rm -f {} + 2>/dev/null
fi
exit 0
